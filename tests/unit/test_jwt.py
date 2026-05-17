"""Unit tests for security/jwt_auth.py — token creation, validation, expiry."""

from datetime import timedelta

import jwt as pyjwt
import pytest

from security.jwt_auth import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
)


@pytest.mark.unit
class TestTokenCreation:
    def test_create_access_token(self):
        token = create_access_token(user_id=1, role="admin")
        assert isinstance(token, str)
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == "1"  # sub stored as string
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        token = create_refresh_token(user_id=42, role="viewer")
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_create_token_pair(self):
        pair = create_token_pair(user_id=1, role="operator")
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert "expires_in" in pair
        assert pair["token_type"] == "bearer"

    def test_access_token_has_expiry(self):
        token = create_access_token(user_id=1, role="admin")
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]


@pytest.mark.unit
class TestTokenDecoding:
    def test_decode_valid_access_token(self):
        token = create_access_token(user_id=5, role="admin")
        data = decode_token(token)
        assert data.sub == 5
        assert data.role == "admin"
        assert data.token_type == "access"

    def test_decode_valid_refresh_token(self):
        token = create_refresh_token(user_id=10, role="viewer")
        data = decode_token(token)
        assert data.sub == 10
        assert data.token_type == "refresh"

    def test_decode_invalid_token_raises(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("not-a-valid-token")
        assert exc_info.value.status_code == 401

    def test_decode_expired_token_raises(self):
        from fastapi import HTTPException

        token = create_access_token(
            user_id=1, role="admin", expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_tampered_token_raises(self):
        from fastapi import HTTPException

        token = create_access_token(user_id=1, role="admin")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_token(tampered)
