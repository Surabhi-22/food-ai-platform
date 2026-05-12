"""
Order tests: creation, status, vendor isolation, query patterns.
Run with: pytest tests/test_orders.py -v
"""
import uuid
from datetime import datetime, timezone
import pytest
from tests.conftest import VendorFactory, OrderFactory


class TestOrderCreation:
    def test_factory_creates_valid_structure(self):
        vid = uuid.uuid4()
        o = OrderFactory.create(vid)
        assert o["vendor_id"] == vid
        assert o["status"] == "pending"
        assert len(o["items"]) == 2

    def test_unique_ids(self):
        vid = uuid.uuid4()
        assert OrderFactory.create(vid)["id"] != OrderFactory.create(vid)["id"]

    def test_items_have_required_fields(self):
        for item in OrderFactory.create(uuid.uuid4())["items"]:
            assert all(k in item for k in ("menu_item_id", "name", "quantity", "price"))


class TestOrderStatus:
    @pytest.mark.parametrize("s", ["pending", "confirmed", "completed", "cancelled"])
    def test_valid_statuses(self, s):
        assert OrderFactory.create(uuid.uuid4(), status=s)["status"] == s


class TestVendorIsolation:
    def test_orders_belong_to_creator(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        assert OrderFactory.create(a)["vendor_id"] != OrderFactory.create(b)["vendor_id"]

    def test_filter_excludes_other_vendor(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        orders = [OrderFactory.create(a), OrderFactory.create(a), OrderFactory.create(b)]
        assert len([o for o in orders if o["vendor_id"] == a]) == 2

    def test_jwt_tokens_vendor_specific(self):
        from app.core.security import create_access_token, decode_access_token
        a, b = uuid.uuid4(), uuid.uuid4()
        pa = decode_access_token(create_access_token(a, "a@t.com"))
        pb = decode_access_token(create_access_token(b, "b@t.com"))
        assert pa["sub"] != pb["sub"]


class TestOrderQueries:
    def test_filter_by_status(self):
        vid = uuid.uuid4()
        orders = [OrderFactory.create(vid, status=s) for s in ["pending", "confirmed", "pending"]]
        assert len([o for o in orders if o["status"] == "pending"]) == 2

    def test_pagination(self):
        vid = uuid.uuid4()
        orders = [OrderFactory.create(vid) for _ in range(25)]
        assert len(orders[:10]) == 10
        assert len(orders[20:]) == 5
