"""Tests for healthcheck endpoint."""

from fastapi.testclient import TestClient

from ai_notes_api.main import app


def test_healthcheck_success() -> None:
    """Return OK status from the healthcheck endpoint."""
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
