"""
Feature engineering for demand forecasting.

Generates temporal, lag, rolling, weather, and event features from
preprocessed order data. Integrates with WeatherService and HolidayService
for production-grade external data.

Academic Reference:
    - Lag/rolling features for time-series (Hyndman & Athanasopoulos, 2021)
    - External features (weather) for retail demand (Fildes et al., 2019)
    - Festival effects on food demand in India (Gupta & Dash, 2023)
"""

import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.integrations.weather import (
    WeatherService,
    WeatherDataPoint,
    classify_temperature,
    calculate_weather_impact_score,
    weather_service,
)
from app.integrations.holidays import (
    HolidayService,
    EventFeatures,
    FESTIVAL_CALENDAR,
    holiday_service,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Legacy Festival Calendar (kept for backward compatibility) ────────────────

INDIAN_FESTIVALS_2025_2026 = {
    date(2025, 1, 14): "Makar Sankranti",
    date(2025, 1, 26): "Republic Day",
    date(2025, 3, 14): "Holi",
    date(2025, 3, 31): "Eid al-Fitr",
    date(2025, 4, 6):  "Ram Navami",
    date(2025, 4, 10): "Mahavir Jayanti",
    date(2025, 4, 14): "Ambedkar Jayanti",
    date(2025, 4, 18): "Good Friday",
    date(2025, 5, 12): "Buddha Purnima",
    date(2025, 6, 7):  "Eid al-Adha",
    date(2025, 8, 15): "Independence Day",
    date(2025, 8, 16): "Raksha Bandhan",
    date(2025, 8, 27): "Janmashtami",
    date(2025, 9, 5):  "Muharram",
    date(2025, 10, 2): "Gandhi Jayanti",
    date(2025, 10, 2): "Dussehra",
    date(2025, 10, 20): "Diwali",
    date(2025, 10, 21): "Diwali (Day 2)",
    date(2025, 11, 5): "Guru Nanak Jayanti",
    date(2025, 11, 15): "Chhath Puja",
    date(2025, 12, 25): "Christmas",
    date(2026, 1, 14): "Makar Sankranti",
    date(2026, 1, 26): "Republic Day",
    date(2026, 3, 3):  "Holi",
    date(2026, 3, 20): "Eid al-Fitr",
    date(2026, 4, 14): "Ambedkar Jayanti",
    date(2026, 5, 1):  "Buddha Purnima",
    date(2026, 8, 15): "Independence Day",
    date(2026, 10, 2): "Gandhi Jayanti",
    date(2026, 10, 8): "Diwali",
    date(2026, 12, 25): "Christmas",
}


def is_festival(d: date) -> bool:
    """Check if a date is an Indian festival. Also flags ±1 day proximity."""
    for delta in range(-1, 2):
        check_date = d + timedelta(days=delta)
        if check_date in INDIAN_FESTIVALS_2025_2026:
            return True
    return False


def get_festival_name(d: date) -> str:
    """Return the festival name for a date, or empty string."""
    return INDIAN_FESTIVALS_2025_2026.get(d, "")


# ── Temporal Features ────────────────────────────────────────────────────────

def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calendar-based temporal features.

    Features added:
        - day_of_week: 0 (Monday) to 6 (Sunday)
        - hour_of_day: 0-23 (defaults to 12 for daily data)
        - week_of_year: 1-52
        - month: 1-12
        - is_weekend: 1 if Saturday/Sunday, else 0
        - day_of_month: 1-31
        - quarter: 1-4
    """
    df = df.copy()
    dt = pd.to_datetime(df["date"])

    df["day_of_week"] = dt.dt.dayofweek
    df["hour_of_day"] = dt.dt.hour if dt.dt.hour.any() else 12
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    df["month"] = dt.dt.month
    df["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
    df["day_of_month"] = dt.dt.day
    df["quarter"] = dt.dt.quarter

    logger.info("Added 7 temporal features")
    return df


# ── Lag Features ─────────────────────────────────────────────────────────────

def add_lag_features(df: pd.DataFrame, lags: list[int] | None = None) -> pd.DataFrame:
    """
    Add lagged quantity features per menu item.

    Lag features capture autoregressive patterns in demand.
    Default lags: 1 day (yesterday), 7 days (same weekday last week),
    14 days (two weeks ago).

    Args:
        df: DataFrame sorted by (menu_item_id, date) with 'quantity' column.
        lags: List of lag periods in days.

    Returns:
        DataFrame with lag_1, lag_7, lag_14 columns added.
    """
    if lags is None:
        lags = [1, 7, 14]

    df = df.copy()
    for lag in lags:
        col_name = f"lag_{lag}"
        df[col_name] = df.groupby("menu_item_id")["quantity"].shift(lag)

    # Fill NaN lags with 0 (start of series)
    lag_cols = [f"lag_{lag}" for lag in lags]
    df[lag_cols] = df[lag_cols].fillna(0)

    logger.info("Added %d lag features: %s", len(lags), lag_cols)
    return df


# ── Rolling Window Features ─────────────────────────────────────────────────

def add_rolling_features(
    df: pd.DataFrame,
    window: int = 7,
) -> pd.DataFrame:
    """
    Add rolling window statistics per menu item.

    Features added (using a 7-day window by default):
        - rolling_mean_7: Moving average of quantity
        - rolling_std_7: Moving standard deviation
        - rolling_max_7: Moving maximum
        - rolling_min_7: Moving minimum

    Args:
        df: DataFrame sorted by (menu_item_id, date).
        window: Rolling window size in days.

    Returns:
        DataFrame with rolling features added.
    """
    df = df.copy()

    for col_suffix, agg_func in [
        (f"rolling_mean_{window}", "mean"),
        (f"rolling_std_{window}", "std"),
        (f"rolling_max_{window}", "max"),
        (f"rolling_min_{window}", "min"),
    ]:
        df[col_suffix] = (
            df.groupby("menu_item_id")["quantity"]
            .transform(lambda x: x.rolling(window=window, min_periods=1).agg(agg_func))
        )

    # Fill NaN from std calculation on single values
    df = df.fillna(0)

    logger.info("Added 4 rolling features with window=%d", window)
    return df


# ── Weather Features (upgraded with WeatherService) ──────────────────────────

async def fetch_weather_data(
    latitude: float = 28.6139,  # Default: New Delhi
    longitude: float = 77.2090,
    days_back: int = 7,
) -> pd.DataFrame:
    """
    Fetch historical weather data using the WeatherService.

    Returns a DataFrame compatible with add_weather_features().
    """
    try:
        data_points = await weather_service.get_historical(
            lat=latitude, lon=longitude, days_back=days_back
        )
    except Exception as e:
        logger.warning("WeatherService.get_historical failed: %s — using synthetic data", e)
        data_points = weather_service._generate_from_monthly_averages(days_back, historical=True)

    records = []
    for dp in data_points:
        records.append({
            "date": dp.date,
            "temperature": dp.temp_max,
            "rainfall": dp.rainfall_mm,
            "temp_min": dp.temp_min,
            "temperature_category": dp.temperature_category,
            "is_rainy": int(dp.is_rainy),
            "weather_impact_score": dp.weather_impact_score,
            "weather_condition": dp.weather_condition,
        })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    logger.info("Fetched weather data for %d days via WeatherService", len(df))
    return df


def _generate_synthetic_weather(days_back: int) -> pd.DataFrame:
    """
    Generate synthetic weather data for development/testing.

    Uses seasonal temperature patterns typical of North India and
    random rainfall events.
    """
    np.random.seed(42)
    dates = [datetime.now(timezone.utc).date() - timedelta(days=i) for i in range(days_back)]

    weather_data = []
    for d in dates:
        # Seasonal temperature model: sine wave with yearly period
        day_of_year = d.timetuple().tm_yday
        base_temp = 25 + 15 * np.sin(2 * np.pi * (day_of_year - 100) / 365)
        temperature = base_temp + np.random.normal(0, 3)

        # Monsoon rainfall model: higher probability June-September
        is_monsoon = d.month in [6, 7, 8, 9]
        rain_prob = 0.6 if is_monsoon else 0.1
        rainfall = np.random.exponential(10) if np.random.random() < rain_prob else 0.0

        cat = classify_temperature(temperature)
        condition = "Rain" if rainfall > 5 else ("Clouds" if rainfall > 0.5 else "Clear")
        impact = calculate_weather_impact_score(temperature, rainfall, condition)

        weather_data.append({
            "date": d,
            "temperature": round(temperature, 1),
            "rainfall": round(rainfall, 1),
            "temp_min": round(temperature - 8 + np.random.normal(0, 1), 1),
            "temperature_category": cat.value,
            "is_rainy": int(rainfall > 5),
            "weather_impact_score": impact,
            "weather_condition": condition,
        })

    df = pd.DataFrame(weather_data)
    df["date"] = pd.to_datetime(df["date"])
    return df


def add_weather_features(df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge weather features into the main DataFrame.

    Enhanced version: merges temperature, rainfall, temperature_category,
    is_rainy, and weather_impact_score.

    Args:
        df: Main DataFrame with 'date' column.
        weather_df: Weather DataFrame from fetch_weather_data().

    Returns:
        DataFrame with weather columns added.
    """
    df = df.copy()
    weather_df = weather_df.copy()

    # Ensure date columns are the same type
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    weather_df["date"] = pd.to_datetime(weather_df["date"]).dt.normalize()

    merge_cols = ["date", "temperature", "rainfall"]
    # Add enhanced columns if available
    for col in ["temperature_category", "is_rainy", "weather_impact_score"]:
        if col in weather_df.columns:
            merge_cols.append(col)

    df = df.merge(weather_df[merge_cols], on="date", how="left")

    # Fill missing weather with defaults
    df["temperature"] = df["temperature"].fillna(25.0)
    df["rainfall"] = df["rainfall"].fillna(0.0)

    # Fill enhanced features if missing
    if "temperature_category" in df.columns:
        df["temperature_category"] = df["temperature_category"].fillna("WARM")
    else:
        df["temperature_category"] = df["temperature"].apply(
            lambda t: classify_temperature(t).value
        )

    if "is_rainy" not in df.columns:
        df["is_rainy"] = (df["rainfall"] > 5).astype(int)
    else:
        df["is_rainy"] = df["is_rainy"].fillna(0).astype(int)

    if "weather_impact_score" not in df.columns:
        df["weather_impact_score"] = df.apply(
            lambda row: calculate_weather_impact_score(
                row["temperature"], row["rainfall"], "Clear"
            ),
            axis=1,
        )
    else:
        df["weather_impact_score"] = df["weather_impact_score"].fillna(0.5)

    # Encode temperature_category as numeric for models
    cat_map = {"COLD": 0, "MILD": 1, "WARM": 2, "HOT": 3}
    df["temp_category_encoded"] = df["temperature_category"].map(cat_map).fillna(2)

    logger.info("Added enhanced weather features: temperature, rainfall, "
                "temp_category, is_rainy, weather_impact_score")
    return df


# ── Event/Festival Features (upgraded with HolidayService) ───────────────────

def add_event_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Indian festival, public holiday, and calendar event features.

    Enhanced version using HolidayService for:
        - is_festival: 1 if date is on or adjacent to a festival
        - is_public_holiday: 1 if official government holiday
        - festival_name: Name of the festival
        - festival_impact_score: 0–1 demand uplift score
        - is_month_end: 1 if salary-day period
        - is_pre_festival / is_post_festival: adjacency flags
        - combined_event_score: aggregated score for ML
        - days_to_next_festival: countdown to next celebration
    """
    df = df.copy()
    dates = pd.to_datetime(df["date"]).dt.date

    # Use HolidayService for rich event features
    event_features = dates.apply(holiday_service.get_event_features)

    df["is_festival"] = event_features.apply(lambda e: int(e.is_festival))
    df["is_public_holiday"] = event_features.apply(lambda e: int(e.is_public_holiday))
    df["festival_name"] = event_features.apply(lambda e: e.festival_name)
    df["festival_impact_score"] = event_features.apply(lambda e: e.festival_impact_score)
    df["is_month_end"] = event_features.apply(lambda e: int(e.is_month_end))
    df["is_pre_festival"] = event_features.apply(lambda e: int(e.is_pre_festival))
    df["is_post_festival"] = event_features.apply(lambda e: int(e.is_post_festival))
    df["combined_event_score"] = event_features.apply(lambda e: e.combined_event_score)

    # Days to next festival
    festival_dates = sorted(FESTIVAL_CALENDAR.keys())

    def days_to_next(d: date) -> int:
        for fd in festival_dates:
            if fd >= d:
                return (fd - d).days
        return 30  # Default if no upcoming festival

    df["days_to_next_festival"] = dates.apply(days_to_next)

    logger.info(
        "Added enhanced event features: %d festival days, %d holidays found",
        df["is_festival"].sum(),
        df["is_public_holiday"].sum(),
    )
    return df


# ── Feature Importance ───────────────────────────────────────────────────────

def feature_importance(
    model,
    feature_names: Optional[list[str]] = None,
    top_n: int = 10,
) -> list[dict]:
    """
    Extract and rank the top N most important features from a trained model.

    Supports:
        - XGBoost (feature_importances_ or get_score())
        - Scikit-learn models with feature_importances_ attribute

    This is used in the final project report to demonstrate which features
    (especially temperature and festival_impact_score) improve prediction accuracy.

    Args:
        model: Trained model object (XGBoost Regressor or similar).
        feature_names: List of feature column names.
        top_n: Number of top features to return.

    Returns:
        List of dicts: [{"feature": "lag_1", "importance": 0.23, "rank": 1}, ...]

    Example output demonstrating weather + festival contribution:
        1. lag_1                  → 0.234  (autoregressive baseline)
        2. rolling_mean_7         → 0.189  (trend capture)
        3. day_of_week            → 0.142  (weekly seasonality)
        4. festival_impact_score  → 0.098  (demand spikes during festivals)
        5. temperature            → 0.076  (weather effect on demand)
        6. weather_impact_score   → 0.062  (composite weather signal)
        7. is_weekend             → 0.055  (weekend demand pattern)
        8. combined_event_score   → 0.041  (aggregated calendar effects)
        9. month                  → 0.038  (seasonal baseline)
       10. lag_7                  → 0.032  (weekly cycle)
    """
    if feature_names is None:
        feature_names = FEATURE_COLUMNS

    # Extract importances
    try:
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "get_score"):
            # XGBoost Booster object
            score = model.get_score(importance_type="weight")
            importances = np.array([
                score.get(f"f{i}", score.get(name, 0))
                for i, name in enumerate(feature_names)
            ])
        else:
            logger.warning("Model does not support feature importance extraction")
            return []
    except Exception as e:
        logger.error("Failed to extract feature importances: %s", e)
        return []

    # Normalize to sum to 1
    total = importances.sum()
    if total > 0:
        importances = importances / total

    # Pair with names, sort, and return top N
    paired = list(zip(feature_names, importances))
    paired.sort(key=lambda x: x[1], reverse=True)

    results = []
    for rank, (name, imp) in enumerate(paired[:top_n], start=1):
        results.append({
            "feature": name,
            "importance": round(float(imp), 4),
            "rank": rank,
        })

    logger.info("Top %d features: %s", top_n, [r["feature"] for r in results])
    return results


# ── Complete Feature Engineering Pipeline ────────────────────────────────────

async def build_features(
    df: pd.DataFrame,
    include_weather: bool = True,
    weather_days: int = 90,
) -> pd.DataFrame:
    """
    Complete feature engineering pipeline.

    Applies all feature transformations in sequence:
        1. Temporal features (day_of_week, is_weekend, etc.)
        2. Lag features (lag_1, lag_7, lag_14)
        3. Rolling features (mean, std, max, min over 7-day window)
        4. Weather features (temperature, rainfall, impact_score, category)
        5. Event features (festival, holiday, month_end, combined_score)

    Args:
        df: Preprocessed DataFrame with [date, menu_item_id, quantity, revenue].
        include_weather: Whether to fetch and include weather data.
        weather_days: Days of weather history to fetch.

    Returns:
        Feature-enriched DataFrame ready for model training.
    """
    if df.empty:
        logger.warning("Empty DataFrame — skipping feature engineering")
        return df

    logger.info("Starting feature engineering on %d rows", len(df))

    # 1. Temporal features
    df = add_temporal_features(df)

    # 2. Lag features
    df = add_lag_features(df)

    # 3. Rolling features
    df = add_rolling_features(df)

    # 4. Weather features (enhanced)
    if include_weather:
        weather_df = await fetch_weather_data(days_back=weather_days)
        df = add_weather_features(df, weather_df)
    else:
        df["temperature"] = 25.0
        df["rainfall"] = 0.0
        df["is_rainy"] = 0
        df["weather_impact_score"] = 0.5
        df["temp_category_encoded"] = 2  # WARM

    # 5. Event features (enhanced with HolidayService)
    df = add_event_features(df)

    # Drop non-numeric helper columns for model input
    df = df.drop(columns=["festival_name", "temperature_category"], errors="ignore")

    # Final fill for any remaining NaNs
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    feature_count = len([c for c in df.columns if c not in ["date", "menu_item_id"]])
    logger.info("Feature engineering complete: %d features generated", feature_count)

    return df


# ── Feature column list for model input (expanded) ──────────────────────────

FEATURE_COLUMNS = [
    # Temporal
    "day_of_week",
    "hour_of_day",
    "week_of_year",
    "month",
    "is_weekend",
    "day_of_month",
    "quarter",
    # Lag
    "lag_1",
    "lag_7",
    "lag_14",
    # Rolling
    "rolling_mean_7",
    "rolling_std_7",
    "rolling_max_7",
    "rolling_min_7",
    # Weather (enhanced)
    "temperature",
    "rainfall",
    "is_rainy",
    "weather_impact_score",
    "temp_category_encoded",
    # Events (enhanced)
    "is_festival",
    "is_public_holiday",
    "festival_impact_score",
    "is_month_end",
    "is_pre_festival",
    "is_post_festival",
    "combined_event_score",
    "days_to_next_festival",
]

TARGET_COLUMN = "quantity"
