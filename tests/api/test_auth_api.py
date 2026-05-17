"""API tests for /api/auth endpoints — login, refresh, user management."""

import pytest


@pytest.mark.api
class TestLoginEndpoint:
    def test_login_missing_fields(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_credentials(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "noone@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_response_schema(self, client):
        """If login succeeds, response must contain token fields."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password"},
        )
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"


@pytest.mark.api
class TestRefreshEndpoint:
    def test_refresh_missing_token(self, client):
        response = client.post("/api/auth/refresh", json={})
        assert response.status_code == 422

    def test_refresh_invalid_token(self, client):
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401


@pytest.mark.api
class TestMeEndpoint:
    def test_me_without_auth(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token(self, client):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


@pytest.mark.api
class TestChangePassword:
    def test_change_password_no_auth(self, client):
        response = client.post(
            "/api/auth/change-password",
            json={"current_password": "old", "new_password": "NewPass123!"},
        )
        assert response.status_code == 401
