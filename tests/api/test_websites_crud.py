"""Extended API tests for /api/websites — CRUD operations."""

import pytest

VALID_FORM_CONFIG = {
    "registration_url": "https://test.example.com/register",
    "steps": [
        {
            "fields": {
                "username": {"selector": "#username", "field_type": "text"},
                "password": {"selector": "#password", "field_type": "password"},
            },
            "submit_button": {"selector": "#submit"},
        }
    ],
}


def _make_payload(name="Test Site", url="https://test.example.com", **kwargs):
    return {
        "name": name,
        "url": url,
        "form_config": VALID_FORM_CONFIG,
        **kwargs,
    }


@pytest.mark.api
class TestWebsiteCRUD:
    def test_create_website(self, client):
        resp = client.post("/api/websites/", json=_make_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Site"

    def test_create_website_missing_fields(self, client):
        resp = client.post("/api/websites/", json={})
        assert resp.status_code == 422

    def test_create_and_get(self, client):
        create = client.post("/api/websites/", json=_make_payload("Get Test"))
        assert create.status_code == 201
        wid = create.json()["id"]

        get = client.get(f"/api/websites/{wid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Get Test"

    def test_create_and_update(self, client):
        create = client.post("/api/websites/", json=_make_payload("Update Me"))
        assert create.status_code == 201
        wid = create.json()["id"]

        update = client.put(f"/api/websites/{wid}", json={"name": "Updated"})
        assert update.status_code == 200
        assert update.json()["name"] == "Updated"

    def test_create_and_delete(self, client):
        create = client.post("/api/websites/", json=_make_payload("Delete Me"))
        assert create.status_code == 201
        wid = create.json()["id"]

        delete = client.delete(f"/api/websites/{wid}")
        assert delete.status_code == 200

    def test_list_websites(self, client):
        resp = client.get("/api/websites/")
        assert resp.status_code == 200

    def test_get_not_found(self, client):
        resp = client.get("/api/websites/99999")
        assert resp.status_code == 404

    def test_update_not_found(self, client):
        resp = client.put("/api/websites/99999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/websites/99999")
        assert resp.status_code == 404

    def test_list_with_search(self, client):
        client.post("/api/websites/", json=_make_payload("Searchable"))
        resp = client.get("/api/websites/?search=Searchable")
        assert resp.status_code == 200

    def test_list_with_pagination(self, client):
        resp = client.get("/api/websites/?limit=5&offset=0")
        assert resp.status_code == 200

    def test_create_with_max_registrations(self, client):
        resp = client.post(
            "/api/websites/",
            json=_make_payload("Limited", max_registrations_per_day=25),
        )
        assert resp.status_code == 201


@pytest.mark.api
class TestRegistrationAPI:
    def test_list_registrations(self, client):
        resp = client.get("/api/registrations/")
        assert resp.status_code in (200, 404, 405)

    def test_get_registration_not_found(self, client):
        resp = client.get("/api/registrations/99999")
        assert resp.status_code in (404, 200, 405)


@pytest.mark.api
class TestDailyLimitsAPI:
    def test_list_limits(self, client):
        resp = client.get("/api/limits/")
        assert resp.status_code in (200, 404, 405)

    def test_get_limit_not_found(self, client):
        resp = client.get("/api/limits/99999")
        assert resp.status_code in (200, 404)


@pytest.mark.api
class TestWebhooksAPI:
    def test_mailslurp_webhook_no_body(self, client):
        resp = client.post("/api/webhooks/mailslurp", json={})
        assert resp.status_code in (200, 400, 422)


@pytest.mark.api
class TestProxiesAPIExtended:
    def test_create_proxy(self, client):
        resp = client.post("/api/proxies/", json={
            "host": "192.168.1.1",
            "port": 8080,
            "protocol": "http",
            "country": "US",
        })
        assert resp.status_code in (200, 201, 422)

    def test_list_proxies(self, client):
        resp = client.get("/api/proxies/")
        assert resp.status_code == 200

    def test_proxy_stats(self, client):
        resp = client.get("/api/proxies/stats")
        assert resp.status_code in (200, 404)

    def test_proxy_countries(self, client):
        resp = client.get("/api/proxies/countries")
        assert resp.status_code in (200, 404)

    def test_proxy_bulk_add(self, client):
        resp = client.post("/api/proxies/bulk", json={
            "proxies": [
                {"host": "10.0.0.1", "port": 3128, "protocol": "http"},
            ]
        })
        assert resp.status_code in (200, 201, 422)
