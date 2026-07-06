"""
Tests for purchase-order API endpoints.
"""
import pytest

from mock_data import purchase_orders


@pytest.fixture(autouse=True)
def clean_purchase_orders():
    """Keep the in-memory purchase-order list isolated per test."""
    snapshot = list(purchase_orders)
    purchase_orders.clear()
    purchase_orders.extend(snapshot)
    yield
    purchase_orders.clear()
    purchase_orders.extend(snapshot)


def valid_po_payload(backlog_item_id="1"):
    return {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "FilterMax Inc",
        "quantity": 350,
        "unit_cost": 5.5,
        "expected_delivery_date": "2026-07-20",
        "notes": "Expedite if possible"
    }


class TestPurchaseOrderEndpoints:
    """Test suite for purchase-order-related endpoints."""

    def test_create_purchase_order(self, client):
        """Test creating a purchase order for a backlog item."""
        response = client.post("/api/purchase-orders", json=valid_po_payload())
        assert response.status_code == 201

        po = response.json()
        assert po["id"].startswith("PO-")
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "FilterMax Inc"
        assert po["quantity"] == 350
        assert abs(po["unit_cost"] - 5.5) < 0.01
        assert po["status"] == "Ordered"
        assert "created_date" in po

    def test_create_po_sets_backlog_flag(self, client):
        """Test that the backlog item reports has_purchase_order after creation."""
        backlog = client.get("/api/backlog").json()
        target = backlog[0]
        assert target["has_purchase_order"] is False

        client.post("/api/purchase-orders", json=valid_po_payload(target["id"]))

        backlog = client.get("/api/backlog").json()
        flagged = next(item for item in backlog if item["id"] == target["id"])
        assert flagged["has_purchase_order"] is True

    def test_create_po_unknown_backlog_item(self, client):
        """Test creating a PO for a backlog item that doesn't exist."""
        response = client.post(
            "/api/purchase-orders", json=valid_po_payload("nonexistent-999")
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_po_duplicate_rejected(self, client):
        """Test that a second PO for the same backlog item is rejected."""
        first = client.post("/api/purchase-orders", json=valid_po_payload("2"))
        assert first.status_code == 201

        second = client.post("/api/purchase-orders", json=valid_po_payload("2"))
        assert second.status_code == 409
        assert "already has" in second.json()["detail"].lower()

    def test_create_po_invalid_payload(self, client):
        """Test validation errors for bad purchase-order payloads."""
        # Quantity below 1
        payload = valid_po_payload()
        payload["quantity"] = 0
        assert client.post("/api/purchase-orders", json=payload).status_code == 400

        # Negative unit cost
        payload = valid_po_payload()
        payload["unit_cost"] = -1
        assert client.post("/api/purchase-orders", json=payload).status_code == 400

        # Blank supplier name
        payload = valid_po_payload()
        payload["supplier_name"] = "   "
        assert client.post("/api/purchase-orders", json=payload).status_code == 400

        # Malformed delivery date
        payload = valid_po_payload()
        payload["expected_delivery_date"] = "soon"
        assert client.post("/api/purchase-orders", json=payload).status_code == 400

        # Datetime instead of a plain date
        payload = valid_po_payload()
        payload["expected_delivery_date"] = "2026-07-20T15:30:00"
        assert client.post("/api/purchase-orders", json=payload).status_code == 400

    def test_get_po_by_backlog_item(self, client):
        """Test fetching the purchase order for a backlog item."""
        created = client.post(
            "/api/purchase-orders", json=valid_po_payload("3")
        ).json()

        response = client.get("/api/purchase-orders/3")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_po_for_backlog_item_without_po(self, client):
        """Test fetching a PO for a backlog item that has none."""
        response = client.get("/api/purchase-orders/4")
        assert response.status_code == 404
        assert "detail" in response.json()
