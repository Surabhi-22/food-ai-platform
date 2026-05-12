"""
Weather integration service for the demand forecasting ML pipeline.

Uses OpenWeatherMap One Call API 3.0 to fetch forecast and historical
weather data. Implements Redis caching (6-hour TTL) and graceful
fallback to cached / synthetic data.

Academic Reference:
    - Weather effects on food demand (Fildes et al., 2019)
    - Feature engineering for retail forecasting (Hyndman & Athanasopoulos, 2021)
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx
import numpy as np

from app.core.config import get_settings
from app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Constants ────────────────────────────────────────────────────────────────

WEATHER_CACHE_PREFIX = "weather"
WEATHER_CACHE_TTL = 21600  # 6 hours in seconds

# Historical monthly averages for New Delhi (fallback data)
# Source: India Meteorological Department (IMD)
MONTHLY_AVERAGES = {
    1:  {"temp_max": 20.5, "temp_min": 7.6,  "rainfall_mm": 14.5},
    2:  {"temp_max": 23.8, "temp_min": 10.1, "rainfall_mm": 17.8},
    3:  {"temp_max": 29.7, "temp_min": 15.0, "rainfall_mm": 12.2},
    4:  {"temp_max": 36.4, "temp_min": 21.5, "rainfall_mm": 7.3},
    5:  {"temp_max": 39.6, "temp_min": 26.2, "rainfall_mm": 17.5},
    6:  {"temp_max": 38.7, "temp_min": 28.3, "rainfall_mm": 53.8},
    7:  {"temp_max": 35.5, "temp_min": 27.4, "rainfall_mm": 209.8},
    8:  {"temp_max": 34.2, "temp_min": 26.5, "rainfall_mm": 228.3},
    9:  {"temp_max": 34.1, "temp_min": 24.7, "rainfall_mm": 127.8},
    10: {"temp_max": 33.7, "temp_min": 19.1, "rainfall_mm": 14.3},
    11: {"temp_max": 28.4, "temp_min": 12.4, "rainfall_mm": 4.5},
    12: {"temp_max": 22.7, "temp_min": 8.0,  "rainfall_mm": 7.8},
}

# Weather condition codes → human-readable descriptions
# https://openweathermap.org/weather-conditions
WEATHER_CONDITION_MAP = {
    range(200, 300): "Thunderstorm",
    range(300, 400): "Drizzle",
    range(500, 600): "Rain",
    range(600, 700): "Snow",
    range(700, 800): "Atmosphere",
    range(800, 801): "Clear",
    range(801, 805): "Clouds",
}


# ── Data Models ──────────────────────────────────────────────────────────────

class TemperatureCategory(str, Enum):
    """Temperature classification for ML feature engineering."""
    HOT = "HOT"       # > 35°C
    WARM = "WARM"      # 25–35°C
    MILD = "MILD"      # 15–25°C
    COLD = "COLD"      # < 15°C


@dataclass
class WeatherDataPoint:
    """Weather data for a single day."""
    date: str                   # ISO date string
    temp_max: float
    temp_min: float
    rainfall_mm: float
    weather_condition: str      # e.g., "Clear", "Rain", "Clouds"
    # Derived ML features
    temperature_category: str   # HOT, WARM, MILD, COLD
    is_rainy: bool
    weather_impact_score: float  # 0.0–1.0


# ── Helper Functions ─────────────────────────────────────────────────────────

def classify_temperature(temp_max: float) -> TemperatureCategory:
    """Classify temperature into categories for ML features."""
    if temp_max > 35:
        return TemperatureCategory.HOT
    elif temp_max >= 25:
        return TemperatureCategory.WARM
    elif temp_max >= 15:
        return TemperatureCategory.MILD
    else:
        return TemperatureCategory.COLD


def calculate_weather_impact_score(
    temp_max: float,
    rainfall_mm: float,
    condition: str,
) -> float:
    """
    Calculate a 0–1 weather impact score for food demand prediction.

    Higher scores indicate weather conditions favorable for food delivery/dining:
        - Hot + sunny = 0.8 (people order cold beverages, light meals)
        - Warm + clear = 0.9 (ideal dining weather, highest demand)
        - Cold + rainy = 0.3 (low footfall, but delivery demand spikes)
        - Extreme heat = 0.6 (reduced outdoor activity)

    The score is used as a multiplicative feature in the XGBoost model.
    """
    base_score = 0.5

    # Temperature component (inverted U-shape: moderate temps are best)
    if 25 <= temp_max <= 32:
        temp_score = 0.9
    elif 20 <= temp_max <= 35:
        temp_score = 0.7
    elif temp_max > 40 or temp_max < 5:
        temp_score = 0.4
    elif temp_max > 35:
        temp_score = 0.6
    else:
        temp_score = 0.5

    # Rainfall component
    if rainfall_mm == 0:
        rain_score = 0.8
    elif rainfall_mm < 5:
        rain_score = 0.7
    elif rainfall_mm < 20:
        rain_score = 0.5  # Moderate rain — delivery demand compensates
    else:
        rain_score = 0.3  # Heavy rain — overall demand drop

    # Condition bonus
    condition_lower = condition.lower()
    if "clear" in condition_lower:
        condition_bonus = 0.1
    elif "cloud" in condition_lower:
        condition_bonus = 0.0
    elif "rain" in condition_lower or "drizzle" in condition_lower:
        condition_bonus = -0.1
    elif "thunder" in condition_lower:
        condition_bonus = -0.15
    else:
        condition_bonus = 0.0

    score = (temp_score * 0.5 + rain_score * 0.5) + condition_bonus
    return round(max(0.0, min(1.0, score)), 2)


def _resolve_weather_condition(code: int) -> str:
    """Map OpenWeatherMap condition code to readable string."""
    for code_range, label in WEATHER_CONDITION_MAP.items():
        if code in code_range:
            return label
    return "Unknown"


# ── Weather Service ──────────────────────────────────────────────────────────

class WeatherService:
    """
    Service for fetching weather data with Redis caching and graceful fallback.

    Usage:
        service = WeatherService()
        forecast = await service.get_forecast(lat=28.6139, lon=77.2090, days=7)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENWEATHERMAP_API_KEY
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"

    async def get_forecast(
        self,
        lat: float = 28.6139,   # New Delhi default
        lon: float = 77.2090,
        days: int = 7,
    ) -> list[WeatherDataPoint]:
        """
        Get weather forecast for the next N days.

        Pipeline:
            1. Check Redis cache
            2. If miss → call OpenWeatherMap API
            3. If API fails → return last cached values
            4. If no cache → return historical monthly averages

        Args:
            lat: Latitude of the vendor's location.
            lon: Longitude.
            days: Number of forecast days (1–8).

        Returns:
            List of WeatherDataPoint objects with ML-ready features.
        """
        cache_key = f"{WEATHER_CACHE_PREFIX}:{lat:.2f}:{lon:.2f}:forecast"

        # 1. Try cache
        cached = await cache_get(cache_key)
        if cached:
            logger.info("Weather forecast cache HIT for (%s, %s)", lat, lon)
            return [WeatherDataPoint(**dp) for dp in cached[:days]]

        # 2. Try API
        if self.api_key:
            try:
                data_points = await self._fetch_from_api(lat, lon, days)
                # Cache the result
                await cache_set(
                    cache_key,
                    [asdict(dp) for dp in data_points],
                    ttl=WEATHER_CACHE_TTL,
                )
                logger.info("Weather forecast fetched from API and cached")
                return data_points
            except Exception as e:
                logger.warning("Weather API failed: %s — trying fallback", e)
        else:
            logger.warning("No OpenWeatherMap API key — using fallback data")

        # 3. Last cached values (may exist from a previous successful call)
        cached_fallback = await cache_get(cache_key)
        if cached_fallback:
            logger.info("Using stale weather cache as fallback")
            return [WeatherDataPoint(**dp) for dp in cached_fallback[:days]]

        # 4. Historical monthly averages
        logger.info("Using historical monthly averages as weather fallback")
        return self._generate_from_monthly_averages(days)

    async def get_historical(
        self,
        lat: float = 28.6139,
        lon: float = 77.2090,
        days_back: int = 30,
    ) -> list[WeatherDataPoint]:
        """
        Get historical weather data for the past N days.

        Uses the One Call API 3.0 timemachine endpoint.
        Falls back to monthly averages if API is unavailable.
        """
        cache_key = f"{WEATHER_CACHE_PREFIX}:{lat:.2f}:{lon:.2f}:history:{days_back}"

        cached = await cache_get(cache_key)
        if cached:
            return [WeatherDataPoint(**dp) for dp in cached]

        if self.api_key:
            try:
                data_points = await self._fetch_historical_from_api(lat, lon, days_back)
                await cache_set(cache_key, [asdict(dp) for dp in data_points], ttl=WEATHER_CACHE_TTL)
                return data_points
            except Exception as e:
                logger.warning("Historical weather API failed: %s", e)

        return self._generate_from_monthly_averages(days_back, historical=True)

    async def _fetch_from_api(
        self,
        lat: float,
        lon: float,
        days: int,
    ) -> list[WeatherDataPoint]:
        """Fetch forecast from OpenWeatherMap One Call API 3.0."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.base_url,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric",
                    "exclude": "minutely,hourly,alerts",
                },
            )
            response.raise_for_status()
            data = response.json()

        results = []
        daily = data.get("daily", [])[:days]

        for day in daily:
            dt = datetime.fromtimestamp(day["dt"], tz=timezone.utc).date()
            temp = day.get("temp", {})
            temp_max = temp.get("max", 30.0)
            temp_min = temp.get("min", 20.0)
            rainfall = day.get("rain", 0.0)
            weather_id = day.get("weather", [{}])[0].get("id", 800)
            condition = _resolve_weather_condition(weather_id)

            cat = classify_temperature(temp_max)
            is_rainy = rainfall > 5
            impact = calculate_weather_impact_score(temp_max, rainfall, condition)

            results.append(WeatherDataPoint(
                date=dt.isoformat(),
                temp_max=round(temp_max, 1),
                temp_min=round(temp_min, 1),
                rainfall_mm=round(rainfall, 1),
                weather_condition=condition,
                temperature_category=cat.value,
                is_rainy=is_rainy,
                weather_impact_score=impact,
            ))

        return results

    async def _fetch_historical_from_api(
        self,
        lat: float,
        lon: float,
        days_back: int,
    ) -> list[WeatherDataPoint]:
        """Fetch historical weather from OpenWeatherMap timemachine endpoint."""
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(days_back):
                dt = datetime.now(timezone.utc) - timedelta(days=i)
                timestamp = int(dt.timestamp())

                try:
                    response = await client.get(
                        f"{self.base_url}/timemachine",
                        params={
                            "lat": lat,
                            "lon": lon,
                            "dt": timestamp,
                            "appid": self.api_key,
                            "units": "metric",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    hourly = data.get("data", [])
                    if hourly:
                        temps = [h.get("temp", 25) for h in hourly]
                        rains = [
                            h.get("rain", {}).get("1h", 0)
                            if isinstance(h.get("rain"), dict) else 0
                            for h in hourly
                        ]
                        weather_id = hourly[0].get("weather", [{}])[0].get("id", 800)
                    else:
                        temps = [25.0]
                        rains = [0.0]
                        weather_id = 800

                    temp_max = max(temps)
                    temp_min = min(temps)
                    rainfall = sum(rains)
                    condition = _resolve_weather_condition(weather_id)

                except Exception as e:
                    logger.warning("Historical weather fetch failed for %s: %s", dt.date(), e)
                    avg = MONTHLY_AVERAGES[dt.month]
                    temp_max = avg["temp_max"]
                    temp_min = avg["temp_min"]
                    rainfall = avg["rainfall_mm"] / 30  # daily average
                    condition = "Unknown"

                cat = classify_temperature(temp_max)
                is_rainy = rainfall > 5
                impact = calculate_weather_impact_score(temp_max, rainfall, condition)

                results.append(WeatherDataPoint(
                    date=dt.date().isoformat(),
                    temp_max=round(temp_max, 1),
                    temp_min=round(temp_min, 1),
                    rainfall_mm=round(rainfall, 1),
                    weather_condition=condition,
                    temperature_category=cat.value,
                    is_rainy=is_rainy,
                    weather_impact_score=impact,
                ))

        return sorted(results, key=lambda x: x.date)

    def _generate_from_monthly_averages(
        self,
        days: int,
        historical: bool = False,
    ) -> list[WeatherDataPoint]:
        """
        Generate weather data from historical monthly averages.

        Used as ultimate fallback when API and cache are both unavailable.
        Adds small random perturbation for realism.
        """
        np.random.seed(42)
        results = []

        for i in range(days):
            if historical:
                target_date = date.today() - timedelta(days=i)
            else:
                target_date = date.today() + timedelta(days=i)

            avg = MONTHLY_AVERAGES[target_date.month]
            temp_max = avg["temp_max"] + np.random.normal(0, 2)
            temp_min = avg["temp_min"] + np.random.normal(0, 2)
            daily_rain = avg["rainfall_mm"] / 30  # Monthly to daily

            # Random rainfall events based on monthly probability
            is_monsoon = target_date.month in [6, 7, 8, 9]
            rain_prob = 0.6 if is_monsoon else 0.15
            rainfall = (
                np.random.exponential(daily_rain * 3) if np.random.random() < rain_prob else 0.0
            )

            condition = "Rain" if rainfall > 5 else ("Clouds" if rainfall > 0.5 else "Clear")
            cat = classify_temperature(temp_max)
            is_rainy = rainfall > 5
            impact = calculate_weather_impact_score(temp_max, rainfall, condition)

            results.append(WeatherDataPoint(
                date=target_date.isoformat(),
                temp_max=round(temp_max, 1),
                temp_min=round(temp_min, 1),
                rainfall_mm=round(rainfall, 1),
                weather_condition=condition,
                temperature_category=cat.value,
                is_rainy=is_rainy,
                weather_impact_score=impact,
            ))

        return sorted(results, key=lambda x: x.date)


# ── Module-level singleton ───────────────────────────────────────────────────

weather_service = WeatherService()
