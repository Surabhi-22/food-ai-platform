"""
XGBoost demand forecasting model.

Trains a gradient-boosted tree regressor per vendor with
TimeSeriesSplit cross-validation for temporally valid evaluation.

Academic Reference:
    - XGBoost: A Scalable Tree Boosting System (Chen & Guestrin, 2016)
    - TimeSeriesSplit for temporal validation (Bergmeir & Benítez, 2012)
"""

import logging
import pickle
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error

from app.ml.features import FEATURE_COLUMNS, TARGET_COLUMN

logger = logging.getLogger(__name__)

# Model artifact directory
MODEL_DIR = Path(__file__).parent / "artifacts" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── Default Hyperparameters ──────────────────────────────────────────────────

XGBOOST_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
}


def _model_path(vendor_id: UUID) -> Path:
    """Return the file path for a vendor's XGBoost model."""
    return MODEL_DIR / f"xgboost_{vendor_id}.pkl"


def save_model(vendor_id: UUID, model: xgb.XGBRegressor) -> None:
    """Persist a trained XGBoost model to disk."""
    path = _model_path(vendor_id)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info("Saved XGBoost model for vendor %s", vendor_id)


def load_model(vendor_id: UUID) -> xgb.XGBRegressor | None:
    """Load a previously trained XGBoost model. Returns None if not found."""
    path = _model_path(vendor_id)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Percentage Error.

    Handles zero values by excluding them from the calculation
    to avoid division by zero.
    """
    mask = y_true != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train_xgboost(
    df: pd.DataFrame,
    vendor_id: UUID,
    n_splits: int = 5,
    params: dict | None = None,
) -> dict:
    """
    Train an XGBoost regressor with TimeSeriesSplit cross-validation.

    The model is trained on all engineered features to predict daily
    demand quantity per menu item.

    Args:
        df: Feature-engineered DataFrame with FEATURE_COLUMNS and TARGET_COLUMN.
        vendor_id: UUID of the vendor.
        n_splits: Number of TimeSeriesSplit folds.
        params: Optional override for XGBoost hyperparameters.

    Returns:
        Dictionary containing:
            - model: Trained XGBRegressor
            - metrics: {rmse, mae, mape} averaged across CV folds
            - feature_importance: {feature_name: importance_score}
            - cv_results: List of per-fold metrics
    """
    if params is None:
        params = XGBOOST_PARAMS.copy()

    # Prepare feature matrix and target
    available_features = [f for f in FEATURE_COLUMNS if f in df.columns]
    X = df[available_features].values
    y = df[TARGET_COLUMN].values.astype(float)

    if len(X) < n_splits + 1:
        logger.warning(
            "Insufficient data for %d-fold CV (%d samples), training on full data",
            n_splits, len(X),
        )
        model = xgb.XGBRegressor(**params)
        model.fit(X, y)
        y_pred = model.predict(X)

        metrics = {
            "rmse": float(np.sqrt(mean_squared_error(np.asarray(y), np.asarray(y_pred)))),
            "mae": float(mean_absolute_error(np.asarray(y), np.asarray(y_pred))),
            "mape": calculate_mape(np.asarray(y), np.asarray(y_pred)),
        }

        save_model(vendor_id, model)

        return {
            "model": model,
            "metrics": metrics,
            "feature_importance": dict(zip(available_features, model.feature_importances_)),
            "cv_results": [metrics],
        }

    # TimeSeriesSplit cross-validation
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_results = []
    fold_predictions = np.zeros_like(y, dtype=float)
    fold_counts = np.zeros_like(y, dtype=float)

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        y_pred = model.predict(X_val)

        # Clip negative predictions to zero (demand cannot be negative)
        y_pred = np.maximum(y_pred, 0)

        fold_rmse = float(np.sqrt(mean_squared_error(np.asarray(y_val), np.asarray(y_pred))))
        fold_mae = float(mean_absolute_error(np.asarray(y_val), np.asarray(y_pred)))
        fold_mape = calculate_mape(np.asarray(y_val), np.asarray(y_pred))

        cv_results.append({
            "fold": fold + 1,
            "rmse": fold_rmse,
            "mae": fold_mae,
            "mape": fold_mape,
            "train_size": len(train_idx),
            "val_size": len(val_idx),
        })

        fold_predictions[val_idx] += y_pred
        fold_counts[val_idx] += 1

        logger.info(
            "Fold %d/%d — RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%",
            fold + 1, n_splits, fold_rmse, fold_mae, fold_mape,
        )

    # Train final model on all data
    final_model = xgb.XGBRegressor(**params)
    final_model.fit(X, y, verbose=False)
    save_model(vendor_id, final_model)

    # Aggregate CV metrics
    avg_metrics = {
        "rmse": float(np.mean([r["rmse"] for r in cv_results])),
        "mae": float(np.mean([r["mae"] for r in cv_results])),
        "mape": float(np.mean([r["mape"] for r in cv_results])),
    }

    # Feature importance from final model
    importance = dict(zip(available_features, final_model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    logger.info(
        "XGBoost training complete — Avg RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%",
        avg_metrics["rmse"], avg_metrics["mae"], avg_metrics["mape"],
    )
    logger.info("Top 5 features: %s", list(importance.items())[:5])

    return {
        "model": final_model,
        "metrics": avg_metrics,
        "feature_importance": importance,
        "cv_results": cv_results,
    }


def predict_xgboost(
    vendor_id: UUID,
    X: np.ndarray | pd.DataFrame,
) -> np.ndarray:
    """
    Generate predictions using a trained XGBoost model.

    Args:
        vendor_id: UUID of the vendor.
        X: Feature matrix (numpy array or DataFrame).

    Returns:
        Array of predicted demand quantities (clipped to >= 0).
    """
    model = load_model(vendor_id)
    if model is None:
        raise FileNotFoundError(f"No trained XGBoost model found for vendor {vendor_id}")

    if isinstance(X, pd.DataFrame):
        available_features = [f for f in FEATURE_COLUMNS if f in X.columns]
        X_arr: np.ndarray = X[available_features].values
        X = X_arr

    predictions = model.predict(X)
    return np.maximum(predictions, 0)  # Demand cannot be negative
