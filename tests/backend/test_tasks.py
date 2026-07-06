"""
Tests for tasks API endpoints.
"""
import pytest

from main import api_tasks


@pytest.fixture(autouse=True)
def clean_tasks():
    """Keep the in-memory task list isolated per test."""
    api_tasks.clear()
    yield
    api_tasks.clear()


class TestTasksEndpoints:
    """Test suite for tasks-related endpoints."""

    def test_get_all_tasks_empty(self, client):
        """Test getting tasks when none exist."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client):
        """Test creating a task returns 201 with server-assigned fields."""
        response = client.post("/api/tasks", json={
            "title": "Review Q4 stock levels",
            "priority": "high",
            "dueDate": "2026-07-10"
        })
        assert response.status_code == 201

        task = response.json()
        assert "id" in task
        assert task["title"] == "Review Q4 stock levels"
        assert task["priority"] == "high"
        assert task["dueDate"] == "2026-07-10"
        assert task["status"] == "pending"

    def test_create_task_appears_in_list(self, client):
        """Test that a created task is returned by GET, newest first."""
        first = client.post("/api/tasks", json={
            "title": "First", "priority": "low", "dueDate": "2026-07-10"
        }).json()
        second = client.post("/api/tasks", json={
            "title": "Second", "priority": "medium", "dueDate": "2026-07-11"
        }).json()

        data = client.get("/api/tasks").json()
        assert [t["id"] for t in data] == [second["id"], first["id"]]

    def test_create_task_strips_title_whitespace(self, client):
        """Test that surrounding whitespace is trimmed from titles."""
        response = client.post("/api/tasks", json={
            "title": "  padded  ", "priority": "low", "dueDate": "2026-07-10"
        })
        assert response.status_code == 201
        assert response.json()["title"] == "padded"

    def test_create_task_invalid_payload(self, client):
        """Test validation errors for bad task payloads."""
        # Empty title
        response = client.post("/api/tasks", json={
            "title": "", "priority": "low", "dueDate": "2026-07-10"
        })
        assert response.status_code == 422

        # Invalid priority
        response = client.post("/api/tasks", json={
            "title": "x", "priority": "urgent", "dueDate": "2026-07-10"
        })
        assert response.status_code == 422

        # Malformed due date
        response = client.post("/api/tasks", json={
            "title": "x", "priority": "low", "dueDate": "next week"
        })
        assert response.status_code == 422

        # Calendar-impossible due date
        response = client.post("/api/tasks", json={
            "title": "x", "priority": "low", "dueDate": "2026-99-99"
        })
        assert response.status_code == 422

    def test_toggle_task(self, client):
        """Test that PATCH flips status pending <-> completed."""
        task = client.post("/api/tasks", json={
            "title": "Toggle me", "priority": "medium", "dueDate": "2026-07-10"
        }).json()

        response = client.patch(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        response = client.patch(f"/api/tasks/{task['id']}")
        assert response.json()["status"] == "pending"

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist."""
        response = client.patch("/api/tasks/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_task(self, client):
        """Test deleting a task removes it from the list."""
        task = client.post("/api/tasks", json={
            "title": "Delete me", "priority": "low", "dueDate": "2026-07-10"
        }).json()

        response = client.delete(f"/api/tasks/{task['id']}")
        assert response.status_code == 204
        assert client.get("/api/tasks").json() == []

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist."""
        response = client.delete("/api/tasks/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
