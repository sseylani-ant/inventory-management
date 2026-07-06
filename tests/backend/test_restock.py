"""
Tests for restocking API endpoints.
"""
import re
from datetime import datetime, timedelta

import pytest

TREND_WEIGHTS = {"increasing": 1.5, "stable": 1.0, "decreasing": 0.5}


@pytest.fixture
def restore_orders():
    """Trim any orders appended during a test; the mock_data list is module-level."""
    from mock_data import orders
    original_count = len(orders)
    yield
    del orders[original_count:]


class TestRestockRecommendationsEndpoint:
    """Test suite for the restock recommendations endpoint."""

    def test_get_recommendations_happy_path(self, client):
        """Test getting recommendations with a mid-range budget."""
        response = client.get("/api/restock/recommendations?budget=50000")
        assert response.status_code == 200

        data = response.json()
        assert data["budget"] == 50000
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

        first = data["items"][0]
        for field in ["sku", "name", "category", "warehouse", "trend",
                      "current_demand", "forecasted_demand", "demand_gap",
                      "priority_score", "recommended_quantity", "unit_cost",
                      "estimated_cost", "lead_time_days"]:
            assert field in first

    def test_recommendations_field_types(self, client):
        """Test that recommendation fields have proper types."""
        response = client.get("/api/restock/recommendations?budget=100000")
        data = response.json()

        for item in data["items"]:
            assert isinstance(item["demand_gap"], int)
            assert isinstance(item["recommended_quantity"], int)
            assert isinstance(item["unit_cost"], (int, float))
            assert isinstance(item["estimated_cost"], (int, float))
            assert isinstance(item["lead_time_days"], int)
            assert item["demand_gap"] > 0
            assert item["recommended_quantity"] >= 1

    def test_recommendations_sorted_by_priority(self, client):
        """Test that recommendations are ordered by trend-weighted demand gap."""
        response = client.get("/api/restock/recommendations?budget=100000")
        data = response.json()

        scores = [item["priority_score"] for item in data["items"]]
        assert scores == sorted(scores, reverse=True)

        for item in data["items"]:
            expected_score = item["demand_gap"] * TREND_WEIGHTS[item["trend"]]
            assert abs(item["priority_score"] - expected_score) < 0.01

    def test_recommendations_respect_budget(self, client):
        """Test that total cost never exceeds the budget for several budgets."""
        for budget in [1000, 20000, 50000, 100000]:
            response = client.get(f"/api/restock/recommendations?budget={budget}")
            data = response.json()

            assert data["total_cost"] <= budget
            assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01

            items_total = sum(item["estimated_cost"] for item in data["items"])
            assert abs(items_total - data["total_cost"]) < 0.01

    def test_recommendations_zero_budget(self, client):
        """Test that a zero budget returns no recommendations."""
        response = client.get("/api/restock/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0

    def test_recommendations_exclude_nonpositive_gap(self, client):
        """Test that items with decreasing demand below current are never recommended."""
        response = client.get("/api/restock/recommendations?budget=100000")
        data = response.json()

        skus = [item["sku"] for item in data["items"]]
        assert "MCU-401" not in skus

    def test_recommendations_budget_validation(self, client):
        """Test that missing or out-of-range budgets are rejected."""
        assert client.get("/api/restock/recommendations").status_code == 422
        assert client.get("/api/restock/recommendations?budget=-100").status_code == 422
        assert client.get("/api/restock/recommendations?budget=100001").status_code == 422

    def test_recommendations_lead_time_range(self, client):
        """Test that lead times are within range and deterministic."""
        first = client.get("/api/restock/recommendations?budget=100000").json()
        second = client.get("/api/restock/recommendations?budget=100000").json()

        for item in first["items"]:
            assert 5 <= item["lead_time_days"] <= 21

        lead_times_first = {i["sku"]: i["lead_time_days"] for i in first["items"]}
        lead_times_second = {i["sku"]: i["lead_time_days"] for i in second["items"]}
        assert lead_times_first == lead_times_second


class TestRestockOrdersEndpoint:
    """Test suite for the restock order creation endpoint."""

    def test_create_restock_order(self, client, restore_orders):
        """Test creating a restock order from recommended items."""
        recs = client.get("/api/restock/recommendations?budget=20000").json()
        payload = {
            "items": [
                {"sku": item["sku"], "quantity": item["recommended_quantity"]}
                for item in recs["items"]
            ]
        }

        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"].lower() == "submitted"
        assert order["customer"] == "Internal Restock"
        assert re.fullmatch(r"ORD-2025-\d{4}", order["order_number"])
        assert int(order["order_number"].split("-")[-1]) == int(order["id"])

        calculated_total = sum(
            item["quantity"] * item["unit_price"] for item in order["items"]
        )
        assert abs(order["total_value"] - calculated_total) < 0.01

    def test_restock_order_lead_time_calculation(self, client, restore_orders):
        """Test that order lead time is the max of item lead times and drives delivery date."""
        recs = client.get("/api/restock/recommendations?budget=20000").json()
        max_lead_time = max(item["lead_time_days"] for item in recs["items"])

        payload = {
            "items": [
                {"sku": item["sku"], "quantity": item["recommended_quantity"]}
                for item in recs["items"]
            ]
        }
        order = client.post("/api/restock-orders", json=payload).json()

        assert order["lead_time_days"] == max_lead_time

        order_date = datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.fromisoformat(order["expected_delivery"])
        assert expected_delivery - order_date == timedelta(days=order["lead_time_days"])

    def test_created_order_appears_in_orders(self, client, restore_orders):
        """Test that a created restock order is visible through the orders endpoints."""
        payload = {"items": [{"sku": "PSU-501", "quantity": 10}]}
        created = client.post("/api/restock-orders", json=payload).json()

        submitted = client.get("/api/orders?status=submitted").json()
        assert any(order["id"] == created["id"] for order in submitted)

        by_id = client.get(f"/api/orders/{created['id']}")
        assert by_id.status_code == 200
        assert by_id.json()["order_number"] == created["order_number"]

    def test_sequential_orders_increment(self, client, restore_orders):
        """Test that consecutive restock orders get incrementing ids and numbers."""
        payload = {"items": [{"sku": "PSU-501", "quantity": 1}]}
        first = client.post("/api/restock-orders", json=payload).json()
        second = client.post("/api/restock-orders", json=payload).json()

        assert int(second["id"]) == int(first["id"]) + 1
        assert int(second["order_number"].split("-")[-1]) == \
            int(first["order_number"].split("-")[-1]) + 1

    def test_create_restock_order_single_warehouse(self, client, restore_orders):
        """Test that warehouse and category are set when all items share them."""
        payload = {"items": [{"sku": "PSU-501", "quantity": 5}]}
        order = client.post("/api/restock-orders", json=payload).json()

        assert order["warehouse"] == "San Francisco"
        assert order["category"].lower() == "power supplies"

    def test_create_restock_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected with a 400."""
        response = client.post(
            "/api/restock-orders", json={"items": [{"sku": "FAKE-999", "quantity": 5}]}
        )
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "FAKE-999" in data["detail"]

    def test_create_restock_order_empty_items(self, client):
        """Test that an empty items list is rejected with a 400."""
        response = client.post("/api/restock-orders", json={"items": []})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_restock_order_invalid_quantity(self, client):
        """Test that non-positive quantities fail validation with a 422."""
        for quantity in [0, -5]:
            response = client.post(
                "/api/restock-orders",
                json={"items": [{"sku": "PSU-501", "quantity": quantity}]},
            )
            assert response.status_code == 422
