"""
Unit tests for the ML pipeline.

Tests cover preprocessing, feature engineering, clustering,
XGBoost training, LSTM training, ensemble forecasting, and evaluation.

Run with: pytest backend/tests/test_ml.py -v
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ============================================================================
# Test Data Fixtures
# ============================================================================


def make_sample_df(n_days: int = 30, n_items: int = 3) -> pd.DataFrame:
    """Generate a sample preprocessed DataFrame for testing."""
    np.random.seed(42)
    rows = []
    base_date = datetime(2026, 4, 1)

    for item_idx in range(n_items):
        item_id = str(uuid.uuid4())
        for day in range(n_days):
            d = base_date + timedelta(days=day)
            # Simulate realistic demand with weekly seasonality
            base_demand = 20 + item_idx * 10
            weekly_effect = 5 * np.sin(2 * np.pi * d.weekday() / 7)
            noise = np.random.normal(0, 3)
            quantity = max(1, int(base_demand + weekly_effect + noise))
            price = 100 + item_idx * 50

            rows.append({
                "date": d,
                "menu_item_id": item_id,
                "quantity": quantity,
                "revenue": quantity * price,
            })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def make_feature_df(n_days: int = 30, n_items: int = 3) -> pd.DataFrame:
    """Generate a sample feature-engineered DataFrame."""
    df = make_sample_df(n_days, n_items)

    # Add temporal features
    df["day_of_week"] = df["date"].dt.dayofweek
    df["hour_of_day"] = 12
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["month"] = df["date"].dt.month
    df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    df["day_of_month"] = df["date"].dt.day
    df["quarter"] = df["date"].dt.quarter

    # Add lag features
    for lag in [1, 7, 14]:
        df[f"lag_{lag}"] = df.groupby("menu_item_id")["quantity"].shift(lag).fillna(0)

    # Add rolling features
    for stat in ["mean", "std", "max", "min"]:
        col = f"rolling_{stat}_7"
        df[col] = (
            df.groupby("menu_item_id")["quantity"]
            .transform(lambda x: x.rolling(7, min_periods=1).agg(stat))
        )

    # Add weather and event features
    df["temperature"] = list(25 + np.random.normal(0, 3, len(df)))
    df["rainfall"] = list(np.random.exponential(2, len(df)))
    df["is_festival"] = 0
    df["days_to_next_festival"] = 15

    df = df.fillna(0)
    return df


# ============================================================================
# Preprocessing Tests
# ============================================================================


class TestPreprocessing:
    """Tests for the preprocessing module."""

    def test_fill_time_gaps_no_gaps(self):
        """Verify no rows are added when there are no gaps."""
        from app.ml.preprocessing import fill_time_gaps

        df = make_sample_df(n_days=10, n_items=1)
        filled = fill_time_gaps(df)
        assert len(filled) == len(df)

    def test_fill_time_gaps_with_gaps(self):
        """Verify missing dates are filled with forward-fill."""
        from app.ml.preprocessing import fill_time_gaps

        df = make_sample_df(n_days=10, n_items=1)
        # Remove some dates to create gaps
        df = df.drop(index=[3, 4, 7]).reset_index(drop=True)
        filled = fill_time_gaps(df)

        # Should have all 10 days restored
        dates = filled["date"].dt.date.unique()
        assert len(dates) == 10

    def test_fill_time_gaps_empty_df(self):
        """Verify empty DataFrame is handled gracefully."""
        from app.ml.preprocessing import fill_time_gaps

        df = pd.DataFrame(columns=["date", "menu_item_id", "quantity", "revenue"])
        filled = fill_time_gaps(df)
        assert filled.empty

    def test_normalize_quantity_fit(self):
        """Verify MinMax normalization produces values in [0, 1]."""
        from app.ml.preprocessing import normalize_quantity

        df = make_sample_df(n_days=20, n_items=1)
        vendor_id = uuid.uuid4()

        df_normalized, scaler = normalize_quantity(df, vendor_id, fit=True)

        assert "quantity_normalized" in df_normalized.columns
        assert df_normalized["quantity_normalized"].min() >= 0.0
        assert df_normalized["quantity_normalized"].max() <= 1.0

    def test_normalize_quantity_load_existing(self):
        """Verify scaler persistence and reload."""
        from app.ml.preprocessing import normalize_quantity, load_scaler

        df = make_sample_df(n_days=20, n_items=1)
        vendor_id = uuid.uuid4()

        # Fit and save
        _, scaler_orig = normalize_quantity(df, vendor_id, fit=True)

        # Load and transform
        df2, scaler_loaded = normalize_quantity(df, vendor_id, fit=False)

        assert scaler_loaded is not None
        np.testing.assert_array_almost_equal(
            list(scaler_orig.data_min_), list(scaler_loaded.data_min_)
        )


# ============================================================================
# Feature Engineering Tests
# ============================================================================


class TestFeatures:
    """Tests for the feature engineering module."""

    def test_temporal_features(self):
        """Verify all temporal features are added correctly."""
        from app.ml.features import add_temporal_features

        df = make_sample_df(n_days=7, n_items=1)
        result = add_temporal_features(df)

        assert "day_of_week" in result.columns
        assert "is_weekend" in result.columns
        assert "week_of_year" in result.columns
        assert "month" in result.columns
        assert "quarter" in result.columns
        assert result["day_of_week"].min() >= 0
        assert result["day_of_week"].max() <= 6

    def test_lag_features(self):
        """Verify lag features are computed correctly."""
        from app.ml.features import add_lag_features

        df = make_sample_df(n_days=20, n_items=1)
        result = add_lag_features(df, lags=[1, 7])

        assert "lag_1" in result.columns
        assert "lag_7" in result.columns
        # First row's lag_1 should be 0 (filled NaN)
        assert result["lag_1"].iloc[0] == 0

    def test_rolling_features(self):
        """Verify rolling statistics are computed correctly."""
        from app.ml.features import add_rolling_features

        df = make_sample_df(n_days=20, n_items=1)
        result = add_rolling_features(df, window=7)

        assert "rolling_mean_7" in result.columns
        assert "rolling_std_7" in result.columns
        assert "rolling_max_7" in result.columns
        assert "rolling_min_7" in result.columns
        # Rolling mean should be between min and max
        assert (result["rolling_mean_7"] >= result["rolling_min_7"]).all()
        assert (result["rolling_mean_7"] <= result["rolling_max_7"]).all()

    def test_event_features(self):
        """Verify festival detection works."""
        from app.ml.features import add_event_features, is_festival

        # Test known festival
        assert is_festival(date(2026, 1, 26)) is True  # Republic Day
        assert is_festival(date(2026, 3, 3)) is True    # Holi

        # Test non-festival
        assert is_festival(date(2026, 6, 15)) is False

        df = make_sample_df(n_days=10, n_items=1)
        result = add_event_features(df)
        assert "is_festival" in result.columns
        assert "days_to_next_festival" in result.columns

    def test_weather_synthetic(self):
        """Verify synthetic weather data generation."""
        from app.ml.features import _generate_synthetic_weather

        weather = _generate_synthetic_weather(30)
        assert len(weather) == 30
        assert "temperature" in weather.columns
        assert "rainfall" in weather.columns
        assert weather["rainfall"].min() >= 0

    def test_feature_columns_defined(self):
        """Verify FEATURE_COLUMNS constant matches expected features."""
        from app.ml.features import FEATURE_COLUMNS

        expected = [
            "day_of_week", "hour_of_day", "week_of_year", "month",
            "is_weekend", "day_of_month", "quarter",
            "lag_1", "lag_7", "lag_14",
            "rolling_mean_7", "rolling_std_7", "rolling_max_7", "rolling_min_7",
            "temperature", "rainfall", "is_rainy", "weather_impact_score", "temp_category_encoded",
            "is_festival", "is_public_holiday", "festival_impact_score", "is_month_end",
            "is_pre_festival", "is_post_festival", "combined_event_score", "days_to_next_festival",
        ]
        assert FEATURE_COLUMNS == expected


# ============================================================================
# Clustering Tests
# ============================================================================


class TestClustering:
    """Tests for the K-Means clustering module."""

    def test_compute_item_features(self):
        """Verify aggregated item features are computed."""
        from app.ml.clustering import compute_item_features

        df = make_sample_df(n_days=30, n_items=3)
        features = compute_item_features(df)

        assert len(features) == 3
        assert "total_quantity" in features.columns
        assert "mean_daily_quantity" in features.columns
        assert "cv" in features.columns
        assert (features["total_quantity"] > 0).all()

    def test_train_clusters_k3(self):
        """Verify K-Means produces 3 demand clusters."""
        from app.ml.clustering import train_clusters, DemandCluster

        df = make_sample_df(n_days=30, n_items=5)
        vendor_id = uuid.uuid4()

        result = train_clusters(df, vendor_id, n_clusters=3)

        assert "demand_cluster" in result.columns
        valid_clusters = {c.value for c in DemandCluster}
        assert set(result["demand_cluster"].unique()).issubset(valid_clusters)

    def test_train_clusters_insufficient_items(self):
        """Verify graceful fallback when too few items for clustering."""
        from app.ml.clustering import train_clusters, DemandCluster

        df = make_sample_df(n_days=30, n_items=2)  # Less than k=3
        vendor_id = uuid.uuid4()

        result = train_clusters(df, vendor_id, n_clusters=3)

        # Should fallback to all MEDIUM_DEMAND
        assert (result["demand_cluster"] == DemandCluster.MEDIUM_DEMAND.value).all()

    def test_cluster_model_persistence(self):
        """Verify cluster model save and load."""
        from app.ml.clustering import train_clusters, load_cluster_model

        df = make_sample_df(n_days=30, n_items=5)
        vendor_id = uuid.uuid4()

        train_clusters(df, vendor_id, n_clusters=3)
        loaded = load_cluster_model(vendor_id)

        assert loaded is not None
        assert "kmeans" in loaded
        assert "scaler" in loaded
        assert "label_mapping" in loaded


# ============================================================================
# XGBoost Tests
# ============================================================================


class TestXGBoost:
    """Tests for the XGBoost model module."""

    def test_train_xgboost_basic(self):
        """Verify XGBoost training completes and returns metrics."""
        from app.ml.xgboost_model import train_xgboost

        df = make_feature_df(n_days=60, n_items=1)
        vendor_id = uuid.uuid4()

        results = train_xgboost(df, vendor_id, n_splits=3)

        assert "model" in results
        assert "metrics" in results
        assert "feature_importance" in results
        assert results["model"] is not None
        assert results["metrics"]["rmse"] >= 0
        assert results["metrics"]["mae"] >= 0
        assert results["metrics"]["mape"] >= 0

    def test_train_xgboost_cv_results(self):
        """Verify TimeSeriesSplit cross-validation produces per-fold results."""
        from app.ml.xgboost_model import train_xgboost

        df = make_feature_df(n_days=60, n_items=1)
        vendor_id = uuid.uuid4()

        results = train_xgboost(df, vendor_id, n_splits=3)

        assert "cv_results" in results
        assert len(results["cv_results"]) == 3
        for fold in results["cv_results"]:
            assert "rmse" in fold
            assert "mae" in fold
            assert "mape" in fold

    def test_predict_xgboost(self):
        """Verify XGBoost predictions are non-negative."""
        from app.ml.xgboost_model import train_xgboost, predict_xgboost
        from app.ml.features import FEATURE_COLUMNS

        df = make_feature_df(n_days=60, n_items=1)
        vendor_id = uuid.uuid4()

        train_xgboost(df, vendor_id, n_splits=3)

        available = [f for f in FEATURE_COLUMNS if f in df.columns]
        X: np.ndarray = df[available].values[:5]
        preds = predict_xgboost(vendor_id, X)

        assert len(preds) == 5
        assert (preds >= 0).all()

    def test_calculate_mape(self):
        """Verify MAPE calculation handles edge cases."""
        from app.ml.xgboost_model import calculate_mape

        y_true = np.array([10, 20, 30, 0, 50])
        y_pred = np.array([12, 18, 35, 5, 48])

        mape = calculate_mape(y_true, y_pred)
        assert mape > 0
        assert mape < 100

        # All zeros should return 0
        assert calculate_mape(np.zeros(5), np.ones(5)) == 0.0

    def test_xgboost_model_persistence(self):
        """Verify XGBoost model save and load."""
        from app.ml.xgboost_model import train_xgboost, load_model

        df = make_feature_df(n_days=60, n_items=1)
        vendor_id = uuid.uuid4()

        train_xgboost(df, vendor_id, n_splits=3)
        model = load_model(vendor_id)

        assert model is not None


# ============================================================================
# LSTM Tests
# ============================================================================


class TestLSTM:
    """Tests for the LSTM model module."""

    def test_create_sequences(self):
        """Verify sequence creation produces correct shapes."""
        from app.ml.lstm_model import create_sequences

        n_timesteps = 50
        n_features = 18
        seq_length = 14

        data = np.random.randn(n_timesteps, n_features).astype(np.float32)
        target = np.random.randn(n_timesteps).astype(np.float32)

        X, y = create_sequences(data, target, seq_length)

        assert X.shape == (n_timesteps - seq_length, seq_length, n_features)
        assert y.shape == (n_timesteps - seq_length,)

    def test_create_sequences_short_data(self):
        """Verify empty sequences for data shorter than sequence length."""
        from app.ml.lstm_model import create_sequences

        data = np.random.randn(10, 5).astype(np.float32)
        target = np.random.randn(10).astype(np.float32)

        X, y = create_sequences(data, target, sequence_length=15)
        assert len(X) == 0

    def test_build_lstm_model(self):
        """Verify LSTM model architecture is built correctly."""
        from app.ml.lstm_model import build_lstm_model

        model = build_lstm_model(n_features=18, sequence_length=14)

        assert model is not None
        # Input shape: (batch, 14, 18)
        assert model.input_shape == (None, 14, 18)
        # Output shape: (batch, 1)
        assert model.output_shape == (None, 1)
        # Should have >0 trainable parameters
        assert model.count_params() > 0

    def test_train_lstm_basic(self):
        """Verify LSTM training completes with metrics."""
        from app.ml.lstm_model import train_lstm

        df = make_feature_df(n_days=60, n_items=1)
        vendor_id = uuid.uuid4()

        # Use fast params for testing
        params = {
            "sequence_length": 7,
            "lstm_units_1": 16,
            "lstm_units_2": 8,
            "dropout_rate": 0.1,
            "dense_units": 8,
            "learning_rate": 0.01,
            "batch_size": 16,
            "epochs": 5,
            "patience": 3,
        }

        results = train_lstm(df, vendor_id, params=params)

        assert "metrics" in results
        assert results["metrics"]["rmse"] >= 0

    def test_train_lstm_insufficient_data(self):
        """Verify graceful handling of too-short data."""
        from app.ml.lstm_model import train_lstm

        df = make_feature_df(n_days=5, n_items=1)  # Too short for seq_length=14
        vendor_id = uuid.uuid4()

        results = train_lstm(df, vendor_id)

        assert results["model"] is None
        assert results["metrics"]["rmse"] == float("inf")


# ============================================================================
# Evaluator Tests
# ============================================================================


class TestEvaluator:
    """Tests for the evaluation module."""

    def test_calculate_rmse(self):
        """Verify RMSE calculation."""
        from app.ml.evaluator import calculate_rmse

        y_true = np.array([10, 20, 30])
        y_pred = np.array([12, 18, 32])
        rmse = calculate_rmse(y_true, y_pred)

        expected = np.sqrt(np.mean((y_true - y_pred) ** 2))
        np.testing.assert_almost_equal(rmse, expected, decimal=4)

    def test_calculate_mae(self):
        """Verify MAE calculation."""
        from app.ml.evaluator import calculate_mae

        y_true = np.array([10, 20, 30])
        y_pred = np.array([12, 18, 32])
        mae = calculate_mae(y_true, y_pred)

        expected = np.mean(np.abs(y_true - y_pred))
        np.testing.assert_almost_equal(mae, expected, decimal=4)

    def test_calculate_mape(self):
        """Verify MAPE calculation with zero handling."""
        from app.ml.evaluator import calculate_mape

        y_true = np.array([10, 20, 0, 30])
        y_pred = np.array([12, 18, 5, 28])

        mape = calculate_mape(y_true, y_pred)
        assert mape > 0
        # Should exclude the zero in y_true
        assert mape < 100

    def test_calculate_smape(self):
        """Verify symmetric MAPE calculation."""
        from app.ml.evaluator import calculate_smape

        y_true = np.array([10, 20, 30])
        y_pred = np.array([12, 18, 32])

        smape = calculate_smape(y_true, y_pred)
        assert 0 <= smape <= 200

    def test_calculate_r_squared(self):
        """Verify R² calculation."""
        from app.ml.evaluator import calculate_r_squared

        # Perfect prediction
        y_true = np.array([10, 20, 30])
        r2 = calculate_r_squared(y_true, y_true)
        np.testing.assert_almost_equal(r2, 1.0, decimal=4)

        # Worst prediction
        y_pred = np.array([30, 10, 20])
        r2_bad = calculate_r_squared(y_true, y_pred)
        assert r2_bad < 1.0


# ============================================================================
# Integration / Ensemble Tests
# ============================================================================


class TestEnsembleForecaster:
    """Tests for the ensemble forecaster configuration."""

    def test_ensemble_weights_sum_to_one(self):
        """Verify ensemble weights are valid."""
        from app.ml.forecaster import XGBOOST_WEIGHT, LSTM_WEIGHT

        assert abs(XGBOOST_WEIGHT + LSTM_WEIGHT - 1.0) < 1e-10

    def test_safety_stock_multiplier(self):
        """Verify safety stock buffer is 15%."""
        from app.ml.forecaster import SAFETY_STOCK_MULTIPLIER

        assert SAFETY_STOCK_MULTIPLIER == 1.15

    def test_confidence_z_score(self):
        """Verify 95% confidence interval Z-score."""
        from app.ml.forecaster import CONFIDENCE_Z_SCORE

        assert abs(CONFIDENCE_Z_SCORE - 1.96) < 0.01

    def test_create_future_features(self):
        """Verify future feature vector creation."""
        from app.ml.forecaster import _create_future_features
        from app.ml.features import FEATURE_COLUMNS

        df = make_feature_df(n_days=30, n_items=1)
        available = [f for f in FEATURE_COLUMNS if f in df.columns]

        future_date = date(2026, 5, 15)
        features = _create_future_features(df, available, future_date, day_offset=1)

        assert features.shape[1] == len(available)
        assert not np.isnan(features).any()

    def test_ensemble_prediction_logic(self):
        """Verify ensemble weighting produces expected output."""
        from app.ml.forecaster import XGBOOST_WEIGHT, LSTM_WEIGHT

        xgb_pred = 100.0
        lstm_pred = 80.0
        ensemble = XGBOOST_WEIGHT * xgb_pred + LSTM_WEIGHT * lstm_pred

        expected = 0.60 * 100 + 0.40 * 80  # = 92.0
        assert abs(ensemble - expected) < 1e-10


# ============================================================================
# Run with: pytest backend/tests/test_ml.py -v --tb=short
# ============================================================================
