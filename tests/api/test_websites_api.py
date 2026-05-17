"""API tests for /api/websites endpoints."""

import pytest


@pytest.mark.api
class TestWebsitesAPI:
    def test_list_websites(self, client):
        response = client.get("/api/websites")
        assert response.status_code == 200

    def test_list_websites_pagination(self, client):
        response = client.get("/api/websites?limit=5&offset=0")
        assert response.status_code == 200

    def test_get_website_not_found(self, client):
        response = client.get("/api/websites/99999")
        assert response.status_code == 404

    def test_create_website_missing_fields(self, client):
        response = client.post("/api/websites", json={})
        assert response.status_code == 422

    def test_delete_website_not_found(self, client):
        response = client.delete("/api/websites/99999")
        assert response.status_code == 404

    def test_update_website_not_found(self, client):
        response = client.put("/api/websites/99999", json={"name": "Updated"})
        assert response.status_code in (404, 422)
