"""
K-Means clustering of menu items by demand pattern.

Segments menu items into HIGH, MEDIUM, and LOW demand clusters
based on aggregated order statistics per item.

Academic Reference:
    - K-Means for customer/product segmentation (Kanungo et al., 2002)
    - Elbow method and silhouette analysis for k selection (Rousseeuw, 1987)
"""

import enum
import logging
import pickle
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)

# Artifact persistence directory
CLUSTER_DIR = Path(__file__).parent / "artifacts" / "clusters"
CLUSTER_DIR.mkdir(parents=True, exist_ok=True)


class DemandCluster(str, enum.Enum):
    """Demand cluster labels assigned to menu items."""
    HIGH_DEMAND = "HIGH_DEMAND"
    MEDIUM_DEMAND = "MEDIUM_DEMAND"
    LOW_DEMAND = "LOW_DEMAND"


def _cluster_model_path(vendor_id: UUID) -> Path:
    """Return the file path for a vendor's cluster model."""
    return CLUSTER_DIR / f"cluster_{vendor_id}.pkl"


def save_cluster_model(
    vendor_id: UUID,
    kmeans: KMeans,
    scaler: StandardScaler,
    label_mapping: dict[int, DemandCluster],
) -> None:
    """Persist the K-Means model, scaler, and label mapping."""
    artifact = {
        "kmeans": kmeans,
        "scaler": scaler,
        "label_mapping": label_mapping,
    }
    path = _cluster_model_path(vendor_id)
    with open(path, "wb") as f:
        pickle.dump(artifact, f)
    logger.info("Saved cluster model for vendor %s", vendor_id)


def load_cluster_model(vendor_id: UUID) -> dict | None:
    """Load a previously saved cluster model. Returns None if not found."""
    path = _cluster_model_path(vendor_id)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def compute_item_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute aggregated demand features per menu item for clustering.

    Features computed:
        - total_quantity: Total units sold
        - mean_daily_quantity: Average daily demand
        - std_daily_quantity: Demand variability
        - total_revenue: Total revenue generated
        - order_frequency: Number of days with orders
        - cv: Coefficient of variation (std/mean)

    Args:
        df: Preprocessed DataFrame with [date, menu_item_id, quantity, revenue].

    Returns:
        DataFrame with one row per menu_item_id and aggregated features.
    """
    item_features = (
        df.groupby("menu_item_id")
        .agg(
            total_quantity=("quantity", "sum"),
            mean_daily_quantity=("quantity", "mean"),
            std_daily_quantity=("quantity", "std"),
            total_revenue=("revenue", "sum"),
            order_frequency=("quantity", lambda x: (x > 0).sum()),
            max_daily_quantity=("quantity", "max"),
        )
        .reset_index()
    )

    # Fill NaN std (items with only 1 data point)
    item_features["std_daily_quantity"] = item_features["std_daily_quantity"].fillna(0)

    # Coefficient of variation — measures demand regularity
    item_features["cv"] = (item_features["std_daily_quantity"] / item_features["mean_daily_quantity"]).where(
        item_features["mean_daily_quantity"] > 0, 0.0
    )

    logger.info("Computed clustering features for %d menu items", len(item_features))
    return item_features


def train_clusters(
    df: pd.DataFrame,
    vendor_id: UUID,
    n_clusters: int = 3,
) -> pd.DataFrame:
    """
    Train K-Means clustering on menu items by demand pattern.

    Steps:
        1. Compute aggregated demand features per item
        2. Standardize features with StandardScaler
        3. Fit K-Means with k=3
        4. Assign cluster labels: HIGH, MEDIUM, LOW based on centroid means
        5. Persist model artifacts with joblib

    Args:
        df: Preprocessed DataFrame with [date, menu_item_id, quantity, revenue].
        vendor_id: UUID of the vendor.
        n_clusters: Number of clusters (default: 3).

    Returns:
        DataFrame with menu_item_id and assigned demand_cluster label.
    """
    if df.empty or df["menu_item_id"].nunique() < n_clusters:
        logger.warning(
            "Insufficient items for clustering (need >= %d, have %d)",
            n_clusters, df["menu_item_id"].nunique() if not df.empty else 0,
        )
        # Assign all items to MEDIUM_DEMAND as fallback
        if df.empty:
            return pd.DataFrame(columns=["menu_item_id", "demand_cluster"])
        items = df["menu_item_id"].unique()
        return pd.DataFrame({
            "menu_item_id": items,
            "demand_cluster": [DemandCluster.MEDIUM_DEMAND.value] * len(items),
        })

    # Step 1: Compute item-level features
    item_features = compute_item_features(df)

    # Step 2: Select and standardize clustering features
    feature_cols = [
        "total_quantity",
        "mean_daily_quantity",
        "std_daily_quantity",
        "total_revenue",
        "order_frequency",
        "cv",
    ]
    X = item_features[feature_cols].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Step 3: Fit K-Means
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10,
        max_iter=300,
        algorithm="lloyd",
    )
    cluster_labels = kmeans.fit_predict(X_scaled)

    # Compute silhouette score for model quality assessment
    if len(set(cluster_labels)) > 1:
        sil_score = silhouette_score(X_scaled, cluster_labels)
        logger.info("K-Means silhouette score: %.4f", sil_score)
    else:
        sil_score = 0.0
        logger.warning("Only one cluster found — silhouette score not meaningful")

    # Step 4: Map cluster indices to demand labels based on centroid means
    # Sort clusters by mean_daily_quantity centroid (index 1 in feature_cols)
    centroid_means = kmeans.cluster_centers_[:, 1]  # mean_daily_quantity column
    sorted_indices = centroid_means.argsort()

    demand_levels = [DemandCluster.LOW_DEMAND, DemandCluster.MEDIUM_DEMAND, DemandCluster.HIGH_DEMAND]
    label_mapping = {}
    for rank, cluster_idx in enumerate(sorted_indices):
        label_mapping[int(cluster_idx)] = demand_levels[min(rank, len(demand_levels) - 1)]

    item_features["cluster_id"] = pd.Series(cluster_labels, index=item_features.index)
    item_features["demand_cluster"] = item_features["cluster_id"].map(
        {k: v.value for k, v in label_mapping.items()}
    )

    # Step 5: Save model artifacts
    save_cluster_model(vendor_id, kmeans, scaler, label_mapping)

    # Log cluster distribution
    cluster_dist = item_features["demand_cluster"].value_counts().to_dict()
    logger.info("Cluster distribution: %s (silhouette=%.4f)", cluster_dist, sil_score)

    return item_features[["menu_item_id", "demand_cluster", "total_quantity", "mean_daily_quantity"]]


def predict_cluster(
    vendor_id: UUID,
    item_features_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Predict demand cluster for new or updated menu items using a saved model.

    Args:
        vendor_id: UUID of the vendor.
        item_features_df: DataFrame with clustering features for items.

    Returns:
        DataFrame with menu_item_id and predicted demand_cluster.
    """
    model_artifact = load_cluster_model(vendor_id)
    if model_artifact is None:
        logger.warning("No saved cluster model for vendor %s", vendor_id)
        return item_features_df.assign(demand_cluster=DemandCluster.MEDIUM_DEMAND.value)

    kmeans = model_artifact["kmeans"]
    scaler = model_artifact["scaler"]
    label_mapping = model_artifact["label_mapping"]

    feature_cols = [
        "total_quantity",
        "mean_daily_quantity",
        "std_daily_quantity",
        "total_revenue",
        "order_frequency",
        "cv",
    ]

    X = item_features_df[feature_cols].values
    X_scaled = scaler.transform(X)
    predictions = kmeans.predict(X_scaled)

    item_features_df = item_features_df.copy()
    item_features_df["demand_cluster"] = [
        label_mapping.get(int(p), DemandCluster.MEDIUM_DEMAND).value
        for p in predictions
    ]

    return item_features_df
