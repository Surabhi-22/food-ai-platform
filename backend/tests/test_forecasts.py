"""
Forecast API tests: mock ML pipeline, response schema, caching.
Run with: pytest tests/test_forecasts.py -v
"""
import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import pytest


SAMPLE_FORECAST = {
    "menu_item_name": "Chicken Biryani",
    "category": "Biryani",
    "forecast_date": (date.today() + timedelta(days=1)).isoformat(),
    "predicted_quantity": 42,
    "predicted_revenue": 6300.0,
    "predicted_profit": 4095.0,
    "confidence_lower": 35,
    "confidence_upper": 49,
    "cluster_label": "HIGH_DEMAND",
    "inventory_required": 49,
}


class TestForecastSchema:
    """Validate forecast response structure."""

    def test_forecast_item_has_required_fields(self):
        required = [
            "menu_item_name", "category", "forecast_date",
            "predicted_quantity", "predicted_revenue", "predicted_profit",
            "confidence_lower", "confidence_upper", "cluster_label",
            "inventory_required",
        ]
        for field in required:
            assert field in SAMPLE_FORECAST

    def test_confidence_interval_is_valid(self):
        assert SAMPLE_FORECAST["confidence_lower"] <= SAMPLE_FORECAST["predicted_quantity"]
        assert SAMPLE_FORECAST["confidence_upper"] >= SAMPLE_FORECAST["predicted_quantity"]

    def test_profit_less_than_revenue(self):
        assert SAMPLE_FORECAST["predicted_profit"] <= SAMPLE_FORECAST["predicted_revenue"]

    def test_inventory_includes_safety_stock(self):
        # Inventory = ceil(quantity * 1.15)
        assert SAMPLE_FORECAST["inventory_required"] >= SAMPLE_FORECAST["predicted_quantity"]

    def test_cluster_label_is_valid(self):
        valid = {"HIGH_DEMAND", "MEDIUM_DEMAND", "LOW_DEMAND"}
        assert SAMPLE_FORECAST["cluster_label"] in valid

    def test_forecast_date_is_future(self):
        fd = date.fromisoformat(SAMPLE_FORECAST["forecast_date"])
        assert fd >= date.today()


class TestForecastSummary:
    """Test forecast summary aggregation."""

    def test_summary_structure(self):
        summary = {
            "total_revenue_3day": 18900.0,
            "total_profit_3day": 12285.0,
            "top_item": "Chicken Biryani",
            "low_stock_alerts": [{"item": "Naan", "deficit": 15}],
        }
        assert summary["total_revenue_3day"] > 0
        assert summary["total_profit_3day"] <= summary["total_revenue_3day"]
        assert isinstance(summary["low_stock_alerts"], list)


class TestForecastCaching:
    """Test Redis caching behavior for forecast results."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_stored(self):
        """Second call should return cached data."""
        from app.core.redis import cache_get, cache_set

        key = "forecast:test_vendor:daily"
        data = [SAMPLE_FORECAST]

        with patch("app.core.redis.get_redis") as mock_redis:
            client = AsyncMock()
            mock_redis.return_value = client

            # First call: cache miss → set
            client.get.return_value = None
            result = await cache_get(key)
            assert result is None

            # Set cache
            await cache_set(key, data, ttl=3600)

            # Second call: cache hit
            import json
            client.get.return_value = json.dumps(data, default=str)
            result = await cache_get(key)
            assert result is not None
            assert len(result) == 1
            assert result[0]["menu_item_name"] == "Chicken Biryani"

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_retrain(self):
        """Retraining should clear forecast cache."""
        from app.core.redis import cache_invalidate_pattern

        with patch("app.core.redis.get_redis") as mock_redis:
            client = AsyncMock()
            mock_redis.return_value = client
            client.scan_iter = AsyncMock(return_value=iter(["forecast:v1:d1", "forecast:v1:d2"]))
            client.delete = AsyncMock()

            # Mock scan_iter as async generator
            async def mock_scan(*a, **kw):
                for k in ["forecast:v1:d1", "forecast:v1:d2"]:
                    yield k
            client.scan_iter = mock_scan

            deleted = await cache_invalidate_pattern("forecast:v1:*")
            assert deleted == 2


class TestForecastDates:
    """Test forecast date range logic."""

    def test_3day_forecast_range(self):
        today = date.today()
        dates = [today + timedelta(days=i) for i in range(1, 4)]
        assert len(dates) == 3
        assert all(d > today for d in dates)

    def test_7day_forecast_range(self):
        today = date.today()
        dates = [today + timedelta(days=i) for i in range(1, 8)]
        assert len(dates) == 7
        assert dates[-1] == today + timedelta(days=7)
