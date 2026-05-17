"""Unit tests for security/scrubber.py — log scrubbing, credential masking."""

import pytest

from security.scrubber import (
    scrub_dict,
    scrub_headers,
    scrub_text,
)


@pytest.mark.unit
class TestScrubText:
    def test_scrubs_jwt_token(self):
        text = "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = scrub_text(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "REDACTED" in result

    def test_scrubs_api_key_patterns(self):
        text = "api_key=sk-abc123xyz789abcdef0123 something"
        result = scrub_text(text)
        assert "sk-abc123xyz789abcdef0123" not in result

    def test_scrubs_password_in_url(self):
        text = "postgres://user:secretpassword@localhost:5432/db"
        result = scrub_text(text)
        assert "secretpassword" not in result

    def test_preserves_normal_text(self):
        text = "Registration completed successfully for user 42"
        result = scrub_text(text)
        assert result == text

    def test_empty_string(self):
        assert scrub_text("") == ""

    def test_scrubs_bearer_token(self):
        text = "Token: Bearer abcdef12345678901234567890"
        result = scrub_text(text)
        assert "abcdef12345678901234567890" not in result


@pytest.mark.unit
class TestScrubHeaders:
    def test_masks_authorization(self):
        headers = {"authorization": "Bearer my-secret-token-abcdef", "Content-Type": "application/json"}
        result = scrub_headers(headers)
        assert result["Content-Type"] == "application/json"
        assert "my-secret-token" not in result["authorization"]

    def test_masks_cookie(self):
        headers = {"cookie": "session=abc12345678901234"}
        result = scrub_headers(headers)
        assert "abc12345678901234" not in str(result.get("cookie", ""))

    def test_preserves_safe_headers(self):
        headers = {"Accept": "text/html", "Host": "example.com"}
        result = scrub_headers(headers)
        assert result["Accept"] == "text/html"
        assert result["Host"] == "example.com"

    def test_empty_dict(self):
        assert scrub_headers({}) == {}


@pytest.mark.unit
class TestScrubDict:
    def test_masks_password_keys(self):
        data = {"username": "admin", "password": "secret12345678"}
        result = scrub_dict(data)
        assert result["username"] == "admin"
        assert "secret12345678" not in str(result["password"])

    def test_masks_token_keys(self):
        data = {"access_token": "abc12345678901234", "name": "test"}
        result = scrub_dict(data)
        assert result["name"] == "test"
        assert "abc12345678901234" not in str(result["access_token"])

    def test_masks_api_key(self):
        data = {"api_key": "sk-12345678901234", "debug": True}
        result = scrub_dict(data)
        assert result["debug"] is True
        assert "sk-12345678901234" not in str(result["api_key"])

    def test_nested_dict(self):
        data = {"config": {"secret_key": "top-secret-value12345"}}
        result = scrub_dict(data)
        assert "top-secret-value12345" not in str(result)

    def test_preserves_non_sensitive_keys(self):
        data = {"name": "test", "count": 42, "enabled": True}
        result = scrub_dict(data)
        assert result == data

    def test_handles_empty_dict(self):
        assert scrub_dict({}) == {}
