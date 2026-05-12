"""
Shared test fixtures and configuration for the backend test suite.

Provides:
    - Async test client using httpx
    - Factory functions for vendors, orders, menu items
    - JWT token generators for authenticated requests
    - Mock database session
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ── Test Settings Override ───────────────────────────────────────────────────
# Override settings before any app module imports them

import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("ENVIRONMENT", "test")


# ── JWT Helpers ──────────────────────────────────────────────────────────────

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
)


# ── Factories ────────────────────────────────────────────────────────────────

class VendorFactory:
    """Generate test vendor data."""

    @staticmethod
    def create(
        vendor_id: uuid.UUID | None = None,
        email: str = "test@vendor.com",
        password: str = "SecurePass123!",
        business_name: str = "Test Kitchen",
    ) -> dict:
        vid = vendor_id or uuid.uuid4()
        return {
            "id": vid,
            "email": email,
            "hashed_password": hash_password(password),
            "business_name": business_name,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def auth_headers(vendor_id: uuid.UUID, email: str = "test@vendor.com") -> dict:
        """Generate Authorization headers with a valid access token."""
        token = create_access_token(vendor_id, email)
        return {"Authorization": f"Bearer {token}"}


class OrderFactory:
    """Generate test order data."""

    @staticmethod
    def create(
        vendor_id: uuid.UUID,
        order_id: uuid.UUID | None = None,
        status: str = "pending",
        total_amount: float = 500.0,
    ) -> dict:
        return {
            "id": order_id or uuid.uuid4(),
            "vendor_id": vendor_id,
            "customer_name": "Test Customer",
            "status": status,
            "total_amount": total_amount,
            "items": [
                {"menu_item_id": str(uuid.uuid4()), "name": "Chicken Biryani", "quantity": 2, "price": 150},
                {"menu_item_id": str(uuid.uuid4()), "name": "Naan", "quantity": 3, "price": 30},
            ],
            "created_at": datetime.now(timezone.utc),
        }


class MenuItemFactory:
    """Generate test menu item data."""

    @staticmethod
    def create(
        vendor_id: uuid.UUID,
        name: str = "Chicken Biryani",
        category: str = "Biryani",
        price: float = 250.0,
        cost_percentage: float = 35.0,
    ) -> dict:
        return {
            "id": uuid.uuid4(),
            "vendor_id": vendor_id,
            "name": name,
            "category": category,
            "price": price,
            "cost_percentage": cost_percentage,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }


# ── Pytest Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def vendor_a():
    """Vendor A test data."""
    return VendorFactory.create(email="vendor_a@test.com", business_name="Kitchen A")


@pytest.fixture
def vendor_b():
    """Vendor B test data (for isolation tests)."""
    return VendorFactory.create(email="vendor_b@test.com", business_name="Kitchen B")


@pytest.fixture
def auth_headers_a(vendor_a):
    """Auth headers for vendor A."""
    return VendorFactory.auth_headers(vendor_a["id"], vendor_a["email"])


@pytest.fixture
def auth_headers_b(vendor_b):
    """Auth headers for vendor B."""
    return VendorFactory.auth_headers(vendor_b["id"], vendor_b["email"])
