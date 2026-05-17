"""API tests for /health endpoint."""

import pytest


@pytest.mark.api
class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_format(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    def test_health_app_name(self, client):
        data = client.get("/health").json()
        assert isinstance(data["app"], str)
        assert len(data["app"]) > 0
