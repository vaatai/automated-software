"""API tests for /api/proxies endpoints."""

import pytest


@pytest.mark.api
class TestProxiesAPI:
    def test_list_proxies(self, client):
        response = client.get("/api/proxies")
        assert response.status_code == 200

    def test_add_proxy_missing_fields(self, client):
        response = client.post("/api/proxies", json={})
        assert response.status_code == 422

    def test_get_proxy_stats(self, client):
        response = client.get("/api/proxies/stats")
        assert response.status_code == 200

    def test_get_proxy_countries(self, client):
        response = client.get("/api/proxies/countries")
        assert response.status_code == 200

    def test_delete_proxy_not_found(self, client):
        response = client.delete("/api/proxies/99999")
        assert response.status_code == 404

    def test_reactivate_proxy_not_found(self, client):
        response = client.put("/api/proxies/99999/reactivate", json={})
        assert response.status_code == 404
