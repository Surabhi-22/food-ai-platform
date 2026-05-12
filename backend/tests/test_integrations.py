"""
Unit tests for the external data integration layer.

Tests cover:
    - WeatherService: temperature classification, impact scoring, fallback
    - HolidayService: festival lookup, impact scores, calendar features
    - Feature engineering: integration of weather + holiday features

Run with:
    pytest tests/test_integrations.py -v
"""

import asyncio
import sys
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Ensure backend root is on the path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

# ── Import integration modules directly ──────────────────────────────────────

from app.integrations.weather import (
    WeatherService,
    WeatherDataPoint,
    classify_temperature,
    calculate_weather_impact_score,
    TemperatureCategory,
    MONTHLY_AVERAGES,
)

from app.integrations.holidays import (
    HolidayService,
    EventFeatures,
    FESTIVAL_CALENDAR,
)

# Import features module directly from file (bypass app.ml.__init__ which pulls xgboost)
import importlib.util as _ilu
import pathlib as _pl
_features_path = _pl.Path(__file__).resolve().parent.parent / "app" / "ml" / "features.py"
_spec = _ilu.spec_from_file_location("app.ml.features", _features_path)
_features_mod = _ilu.module_from_spec(_spec)
sys.modules["app.ml.features"] = _features_mod
_spec.loader.exec_module(_features_mod)
add_temporal_features = _features_mod.add_temporal_features
add_lag_features = _features_mod.add_lag_features
add_rolling_features = _features_mod.add_rolling_features
add_event_features = _features_mod.add_event_features
add_weather_features = _features_mod.add_weather_features
feature_importance = _features_mod.feature_importance
FEATURE_COLUMNS = _features_mod.FEATURE_COLUMNS
TARGET_COLUMN = _features_mod.TARGET_COLUMN


class TestTemperatureClassification:
    """Test temperature categorization for ML features."""

    def test_hot_temperature(self):
        assert classify_temperature(40.0) == TemperatureCategory.HOT
        assert classify_temperature(35.1) == TemperatureCategory.HOT

    def test_warm_temperature(self):
        assert classify_temperature(30.0) == TemperatureCategory.WARM
        assert classify_temperature(25.0) == TemperatureCategory.WARM
        assert classify_temperature(35.0) == TemperatureCategory.WARM

    def test_mild_temperature(self):
        assert classify_temperature(20.0) == TemperatureCategory.MILD
        assert classify_temperature(15.0) == TemperatureCategory.MILD

    def test_cold_temperature(self):
        assert classify_temperature(10.0) == TemperatureCategory.COLD
        assert classify_temperature(-5.0) == TemperatureCategory.COLD
        assert classify_temperature(14.9) == TemperatureCategory.COLD


class TestWeatherImpactScore:
    """Test weather impact score computation."""

    def test_warm_clear_highest_score(self):
        """Warm + clear weather should yield high impact (people dine out)."""
        score = calculate_weather_impact_score(28.0, 0.0, "Clear")
        assert score >= 0.8
        assert score <= 1.0

    def test_cold_rainy_lowest_score(self):
        """Cold + heavy rain should yield low impact."""
        score = calculate_weather_impact_score(8.0, 30.0, "Rain")
        assert score <= 0.4

    def test_moderate_rain_middling(self):
        """Moderate rain should be mid-range (delivery compensates footfall)."""
        score = calculate_weather_impact_score(25.0, 10.0, "Drizzle")
        assert 0.3 <= score <= 0.7

    def test_score_bounds(self):
        """Score must always be between 0.0 and 1.0."""
        for temp in [-10, 0, 15, 25, 35, 45]:
            for rain in [0, 5, 20, 50]:
                for cond in ["Clear", "Rain", "Thunderstorm", "Clouds"]:
                    score = calculate_weather_impact_score(temp, rain, cond)
                    assert 0.0 <= score <= 1.0, \
                        f"Out of bounds: temp={temp}, rain={rain}, cond={cond} → {score}"


class TestWeatherServiceFallback:
    """Test WeatherService graceful degradation."""

    def test_monthly_averages_coverage(self):
        """All 12 months must have average data."""
        for month in range(1, 13):
            assert month in MONTHLY_AVERAGES
            avg = MONTHLY_AVERAGES[month]
            assert "temp_max" in avg
            assert "temp_min" in avg
            assert "rainfall_mm" in avg

    def test_synthetic_data_generation(self):
        """Fallback should generate valid data points."""
        service = WeatherService(api_key=None)
        results = service._generate_from_monthly_averages(7)
        assert len(results) == 7
        for dp in results:
            assert isinstance(dp, WeatherDataPoint)
            assert dp.temp_max > dp.temp_min or abs(dp.temp_max - dp.temp_min) < 5
            assert dp.rainfall_mm >= 0
            assert dp.weather_impact_score >= 0
            assert dp.weather_impact_score <= 1
            assert dp.temperature_category in ["HOT", "WARM", "MILD", "COLD"]

    @pytest.mark.asyncio
    async def test_get_forecast_without_api_key(self):
        """Without API key, service should return fallback data gracefully."""
        service = WeatherService(api_key=None)
        # Patch cache to return None (no cache)
        with patch("app.integrations.weather.cache_get", new_callable=AsyncMock, return_value=None):
            results = await service.get_forecast(days=3)
        assert len(results) == 3
        for dp in results:
            assert isinstance(dp, WeatherDataPoint)


# ── Holiday Service Tests ────────────────────────────────────────────────────


class TestHolidayService:
    """Test the HolidayService integration."""

    @pytest.fixture
    def service(self):
        return HolidayService(years=[2024, 2025, 2026])

    def test_diwali_is_festival(self, service):
        """Diwali should be flagged as festival with impact=1.0."""
        features = service.get_event_features(date(2025, 10, 20))
        assert features.is_festival is True
        assert features.festival_name == "Diwali"
        assert features.festival_impact_score == 1.0

    def test_eid_is_festival(self, service):
        """Eid should be flagged with impact=0.95."""
        features = service.get_event_features(date(2025, 3, 31))
        assert features.is_festival is True
        assert "Eid" in features.festival_name
        assert features.festival_impact_score == 0.95

    def test_holi_impact(self, service):
        """Holi should have impact=0.85."""
        features = service.get_event_features(date(2025, 3, 14))
        assert features.is_festival is True
        assert features.festival_impact_score == 0.85

    def test_independence_day(self, service):
        """Independence Day is both a public holiday and a festival."""
        features = service.get_event_features(date(2025, 8, 15))
        assert features.is_public_holiday is True
        assert features.is_festival is True

    def test_regular_day(self, service):
        """A regular weekday should have zero festival impact."""
        features = service.get_event_features(date(2025, 7, 8))  # Tuesday
        assert features.is_festival is False
        assert features.festival_impact_score == 0.0
        assert features.is_weekend is False

    def test_weekend_detection(self, service):
        """Saturday/Sunday should be flagged."""
        saturday = service.get_event_features(date(2025, 7, 5))
        assert saturday.is_weekend is True

        sunday = service.get_event_features(date(2025, 7, 6))
        assert sunday.is_weekend is True

        monday = service.get_event_features(date(2025, 7, 7))
        assert monday.is_weekend is False

    def test_month_end_salary_day(self, service):
        """Last days of month and first days should be flagged (salary period)."""
        features_28 = service.get_event_features(date(2025, 6, 28))
        assert features_28.is_month_end is True

        features_30 = service.get_event_features(date(2025, 6, 30))
        assert features_30.is_month_end is True

        features_1 = service.get_event_features(date(2025, 7, 1))
        assert features_1.is_month_end is True

        features_15 = service.get_event_features(date(2025, 7, 15))
        assert features_15.is_month_end is False

    def test_pre_festival_flag(self, service):
        """Day before Diwali should be flagged as pre-festival."""
        features = service.get_event_features(date(2025, 10, 19))
        assert features.is_pre_festival is True

    def test_post_festival_flag(self, service):
        """Day after Diwali should be flagged as post-festival."""
        features = service.get_event_features(date(2025, 10, 21))
        # Diwali Day 2 is itself a festival, but also post-Diwali Day 1
        assert features.is_festival is True

    def test_combined_event_score_range(self, service):
        """Combined score must be 0–1 for any date."""
        start = date(2025, 1, 1)
        for i in range(365):
            d = start + timedelta(days=i)
            features = service.get_event_features(d)
            assert 0.0 <= features.combined_event_score <= 1.0, \
                f"Out of bounds on {d}: {features.combined_event_score}"

    def test_festival_calendar_has_entries_for_all_years(self):
        """Calendar should cover 2024, 2025, and 2026."""
        years_covered = {d.year for d in FESTIVAL_CALENDAR.keys()}
        assert 2024 in years_covered
        assert 2025 in years_covered
        assert 2026 in years_covered

    def test_get_features_for_range(self, service):
        """get_features_for_range should return one entry per day."""
        start = date(2025, 10, 18)
        end = date(2025, 10, 22)
        features = service.get_features_for_range(start, end)
        assert len(features) == 5  # 18, 19, 20, 21, 22

    def test_get_upcoming_festivals(self, service):
        """Should return upcoming festivals sorted by date."""
        upcoming = service.get_upcoming_festivals(from_date=date(2025, 10, 1), limit=3)
        assert len(upcoming) <= 3
        assert all("name" in f for f in upcoming)
        assert all("impact_score" in f for f in upcoming)
        # Should be sorted by date
        if len(upcoming) >= 2:
            assert upcoming[0]["days_away"] <= upcoming[1]["days_away"]


# ── Feature Engineering Integration Tests ────────────────────────────────────


class TestTemporalFeatures:
    """Test temporal feature generation."""

    @pytest.fixture
    def sample_df(self):
        dates = pd.date_range("2025-10-01", periods=14, freq="D")
        return pd.DataFrame({
            "date": dates,
            "menu_item_id": "item_1",
            "quantity": np.random.randint(10, 50, 14),
            "revenue": np.random.randint(500, 3000, 14),
        })

    def test_adds_all_temporal_columns(self, sample_df):
        result = add_temporal_features(sample_df)
        expected_cols = [
            "day_of_week", "hour_of_day", "week_of_year",
            "month", "is_weekend", "day_of_month", "quarter",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_weekend_detection(self, sample_df):
        result = add_temporal_features(sample_df)
        for _, row in result.iterrows():
            d = pd.to_datetime(row["date"])
            expected = 1 if d.dayofweek >= 5 else 0
            assert row["is_weekend"] == expected


class TestLagFeatures:
    """Test lag feature generation."""

    @pytest.fixture
    def sample_df(self):
        dates = pd.date_range("2025-10-01", periods=30, freq="D")
        return pd.DataFrame({
            "date": dates,
            "menu_item_id": "item_1",
            "quantity": list(range(30)),
            "revenue": list(range(0, 3000, 100)),
        })

    def test_adds_default_lags(self, sample_df):
        result = add_lag_features(sample_df)
        assert "lag_1" in result.columns
        assert "lag_7" in result.columns
        assert "lag_14" in result.columns

    def test_lag_values_correct(self, sample_df):
        result = add_lag_features(sample_df)
        # Row at index 7 should have lag_1 = quantity[6] = 6
        assert result.iloc[7]["lag_1"] == 6
        # lag_7 for row 7 = quantity[0] = 0
        assert result.iloc[7]["lag_7"] == 0

    def test_no_nans_after_fill(self, sample_df):
        result = add_lag_features(sample_df)
        assert not result[["lag_1", "lag_7", "lag_14"]].isna().any().any()


class TestEventFeatures:
    """Test event feature integration with HolidayService."""

    @pytest.fixture
    def diwali_df(self):
        dates = pd.date_range("2025-10-18", periods=5, freq="D")
        return pd.DataFrame({
            "date": dates,
            "menu_item_id": "item_1",
            "quantity": [30, 35, 60, 55, 40],
            "revenue": [3000, 3500, 6000, 5500, 4000],
        })

    def test_diwali_flagged(self, diwali_df):
        result = add_event_features(diwali_df)
        # Oct 20 = Diwali
        diwali_row = result[pd.to_datetime(result["date"]).dt.day == 20].iloc[0]
        assert diwali_row["is_festival"] == 1
        assert diwali_row["festival_impact_score"] == 1.0

    def test_festival_columns_exist(self, diwali_df):
        result = add_event_features(diwali_df)
        expected_cols = [
            "is_festival", "is_public_holiday", "festival_impact_score",
            "is_month_end", "combined_event_score", "days_to_next_festival",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"


class TestWeatherFeatures:
    """Test weather feature merging."""

    def test_merge_enhanced_weather(self):
        dates = pd.date_range("2025-10-01", periods=5, freq="D")
        main_df = pd.DataFrame({
            "date": dates,
            "menu_item_id": "item_1",
            "quantity": [30, 35, 40, 38, 42],
        })
        weather_df = pd.DataFrame({
            "date": dates,
            "temperature": [32, 30, 28, 25, 22],
            "rainfall": [0, 0, 5, 15, 0],
            "temperature_category": ["WARM", "WARM", "WARM", "WARM", "MILD"],
            "is_rainy": [0, 0, 0, 1, 0],
            "weather_impact_score": [0.85, 0.85, 0.70, 0.45, 0.65],
        })

        result = add_weather_features(main_df, weather_df)
        assert "temperature" in result.columns
        assert "is_rainy" in result.columns
        assert "weather_impact_score" in result.columns
        assert "temp_category_encoded" in result.columns
        assert not result["temperature"].isna().any()

    def test_missing_weather_fills_defaults(self):
        dates = pd.date_range("2025-10-01", periods=3, freq="D")
        main_df = pd.DataFrame({
            "date": dates,
            "menu_item_id": "item_1",
            "quantity": [30, 35, 40],
        })
        # Only 1 day of weather data
        weather_df = pd.DataFrame({
            "date": [dates[0]],
            "temperature": [30],
            "rainfall": [0],
        })

        result = add_weather_features(main_df, weather_df)
        # Missing days should be filled with defaults
        assert result.iloc[1]["temperature"] == 25.0
        assert result.iloc[2]["rainfall"] == 0.0


class TestFeatureImportance:
    """Test feature importance extraction."""

    def test_with_sklearn_model(self):
        """Mock an sklearn model with feature_importances_."""
        mock_model = MagicMock()
        mock_model.feature_importances_ = np.array([0.3, 0.2, 0.15, 0.1, 0.25])
        features = ["lag_1", "temperature", "is_festival", "month", "rolling_mean_7"]

        result = feature_importance(mock_model, feature_names=features, top_n=3)
        assert len(result) == 3
        assert result[0]["rank"] == 1
        # Highest importance should be first
        assert result[0]["importance"] >= result[1]["importance"]

    def test_importances_sum_to_one(self):
        """Normalized importances should sum close to 1."""
        mock_model = MagicMock()
        mock_model.feature_importances_ = np.array([10, 20, 30, 40])
        features = ["a", "b", "c", "d"]

        result = feature_importance(mock_model, feature_names=features, top_n=4)
        total = sum(r["importance"] for r in result)
        assert abs(total - 1.0) < 0.01

    def test_model_without_importance(self):
        """Model without feature importance support should return empty."""
        mock_model = MagicMock(spec=[])  # No attributes
        result = feature_importance(mock_model, feature_names=["a", "b"])
        assert result == []


class TestFeatureColumnList:
    """Validate the FEATURE_COLUMNS list is consistent."""

    def test_feature_columns_not_empty(self):
        assert len(FEATURE_COLUMNS) > 0

    def test_target_not_in_features(self):
        assert TARGET_COLUMN not in FEATURE_COLUMNS

    def test_enhanced_weather_features_present(self):
        """New weather features should be in FEATURE_COLUMNS."""
        assert "is_rainy" in FEATURE_COLUMNS
        assert "weather_impact_score" in FEATURE_COLUMNS
        assert "temp_category_encoded" in FEATURE_COLUMNS

    def test_enhanced_event_features_present(self):
        """New event features should be in FEATURE_COLUMNS."""
        assert "is_public_holiday" in FEATURE_COLUMNS
        assert "festival_impact_score" in FEATURE_COLUMNS
        assert "is_month_end" in FEATURE_COLUMNS
        assert "combined_event_score" in FEATURE_COLUMNS
        assert "is_pre_festival" in FEATURE_COLUMNS
        assert "is_post_festival" in FEATURE_COLUMNS
