"""Deep coverage tests for security modules."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestCelerySecurity:
    def test_apply_celery_security(self):
        from security.celery_security import apply_celery_security

        app = MagicMock()
        app.conf = MagicMock()
        apply_celery_security(app)
        app.conf.update.assert_called_once()

    def test_apply_celery_security_with_ssl(self):
        from security.celery_security import apply_celery_security

        app = MagicMock()
        app.conf = MagicMock()
        apply_celery_security(app, redis_ssl=True)
        app.conf.update.assert_called_once()
        config = app.conf.update.call_args[0][0]
        assert "broker_use_ssl" in config

    def test_validate_celery_config_clean(self):
        from security.celery_security import validate_celery_config

        app = MagicMock()
        app.conf.get = MagicMock(side_effect=lambda key, *args: {
            "accept_content": ["json"],
            "task_serializer": "json",
            "result_serializer": "json",
            "task_remote_tracebacks": False,
            "broker_url": "redis://localhost:6379/0",
        }.get(key, args[0] if args else None))

        warnings = validate_celery_config(app)
        assert warnings == []

    def test_validate_celery_config_pickle_warning(self):
        from security.celery_security import validate_celery_config

        app = MagicMock()
        app.conf.get = MagicMock(side_effect=lambda key, *args: {
            "accept_content": ["json", "pickle"],
            "task_serializer": "json",
            "result_serializer": "json",
            "task_remote_tracebacks": False,
            "broker_url": "redis://localhost:6379/0",
        }.get(key, args[0] if args else None))

        warnings = validate_celery_config(app)
        assert any("pickle" in w for w in warnings)

    def test_validate_celery_config_wrong_serializer(self):
        from security.celery_security import validate_celery_config

        app = MagicMock()
        app.conf.get = MagicMock(side_effect=lambda key, *args: {
            "accept_content": ["json"],
            "task_serializer": "pickle",
            "result_serializer": "msgpack",
            "task_remote_tracebacks": True,
            "broker_url": "redis://user:pass@host:6379",
        }.get(key, args[0] if args else None))

        warnings = validate_celery_config(app)
        assert len(warnings) >= 2

    def test_validate_remote_tracebacks(self):
        from security.celery_security import validate_celery_config

        app = MagicMock()
        app.conf.get = MagicMock(side_effect=lambda key, *args: {
            "accept_content": ["json"],
            "task_serializer": "json",
            "result_serializer": "json",
            "task_remote_tracebacks": True,
            "broker_url": "redis://localhost:6379/0",
        }.get(key, args[0] if args else None))

        warnings = validate_celery_config(app)
        assert any("tracebacks" in w for w in warnings)


@pytest.mark.unit
class TestJWTAuth:
    def test_create_access_token(self):
        from security.jwt_auth import create_access_token

        token = create_access_token(user_id=1, role="admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        from security.jwt_auth import create_refresh_token

        token = create_refresh_token(user_id=1, role="admin")
        assert isinstance(token, str)

    def test_create_token_pair(self):
        from security.jwt_auth import create_token_pair

        pair = create_token_pair(user_id=42, role="admin")
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert pair["access_token"] != pair["refresh_token"]

    def test_decode_valid_access_token(self):
        from security.jwt_auth import create_access_token, decode_token

        token = create_access_token(user_id=42, role="admin")
        data = decode_token(token)
        assert data.sub == 42
        assert data.token_type == "access"

    def test_decode_refresh_token(self):
        from security.jwt_auth import create_refresh_token, decode_token

        token = create_refresh_token(user_id=7, role="operator")
        data = decode_token(token)
        assert data.sub == 7
        assert data.token_type == "refresh"

    def test_decode_invalid_token(self):
        from fastapi import HTTPException

        from security.jwt_auth import decode_token

        with pytest.raises(HTTPException):
            decode_token("invalid.token.value")

    def test_decode_tampered_token(self):
        from fastapi import HTTPException

        from security.jwt_auth import create_access_token, decode_token

        token = create_access_token(user_id=1, role="admin")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_token(tampered)

    def test_token_payload_class(self):
        import time

        from security.jwt_auth import TokenPayload

        now = time.time()
        tp = TokenPayload({"sub": "1", "role": "admin", "type": "access", "exp": now + 3600, "iat": now})
        assert tp.sub == 1
        assert tp.role == "admin"
        assert tp.token_type == "access"


@pytest.mark.unit
class TestRBACHelpers:
    def test_has_minimum_role_admin(self):
        from models.user import UserRole
        from security.rbac import has_minimum_role

        assert has_minimum_role(UserRole.ADMIN, UserRole.OPERATOR) is True
        assert has_minimum_role(UserRole.ADMIN, UserRole.ADMIN) is True
        assert has_minimum_role(UserRole.ADMIN, UserRole.SUPER_ADMIN) is False

    def test_has_minimum_role_viewer(self):
        from models.user import UserRole
        from security.rbac import has_minimum_role

        assert has_minimum_role(UserRole.VIEWER, UserRole.VIEWER) is True
        assert has_minimum_role(UserRole.VIEWER, UserRole.OPERATOR) is False

    def test_has_permission_admin(self):
        from models.user import UserRole
        from security.rbac import Permission, has_permission

        assert has_permission(UserRole.ADMIN, Permission.WEBSITE_CREATE) is True
        assert has_permission(UserRole.ADMIN, Permission.WEBSITE_DELETE) is True

    def test_has_permission_viewer(self):
        from models.user import UserRole
        from security.rbac import Permission, has_permission

        assert has_permission(UserRole.VIEWER, Permission.WEBSITE_VIEW) is True
        assert has_permission(UserRole.VIEWER, Permission.WEBSITE_DELETE) is False

    def test_role_permissions(self):
        from security.rbac import ROLE_PERMISSIONS

        assert isinstance(ROLE_PERMISSIONS, dict)
        assert len(ROLE_PERMISSIONS) >= 4

    def test_require_role_factory(self):
        from security.rbac import require_role

        dep = require_role("ADMIN")
        assert callable(dep)

    def test_require_permission_factory(self):
        from security.rbac import Permission, require_permission

        dep = require_permission(Permission.WEBSITE_CREATE)
        assert callable(dep)


@pytest.mark.unit
class TestHTTPSConfig:
    def test_security_headers_middleware_init(self):
        from security.https_config import SecurityHeadersMiddleware

        assert SecurityHeadersMiddleware is not None

    def test_get_uvicorn_ssl_config(self):
        from security.https_config import get_uvicorn_ssl_config

        config = get_uvicorn_ssl_config()
        assert "ssl_certfile" in config
        assert "ssl_keyfile" in config

    def test_get_uvicorn_ssl_config_custom_paths(self):
        from security.https_config import get_uvicorn_ssl_config

        config = get_uvicorn_ssl_config(certfile="/custom/cert", keyfile="/custom/key")
        assert config["ssl_certfile"] == "/custom/cert"
        assert config["ssl_keyfile"] == "/custom/key"


@pytest.mark.unit
class TestScrubberDeep:
    def test_scrub_text_jwt(self):
        from security.scrubber import scrub_text

        result = scrub_text("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U")
        assert "eyJhbGciOiJ" not in result

    def test_scrub_text_api_key(self):
        from security.scrubber import scrub_text

        long_key = "sk-" + "a" * 30
        result = scrub_text(f"api_key={long_key}")
        assert long_key not in result

    def test_scrub_dict_password(self):
        from security.scrubber import scrub_dict

        d = {"password": "secret", "name": "visible"}
        scrubbed = scrub_dict(d)
        assert scrubbed["name"] == "visible"
        assert scrubbed["password"] != "secret"

    def test_scrub_dict_nested(self):
        from security.scrubber import scrub_dict

        d = {"data": {"api_key": "sk-12345", "public": "hello"}}
        scrubbed = scrub_dict(d)
        assert scrubbed["data"]["public"] == "hello"

    def test_scrub_headers(self):
        from security.scrubber import scrub_headers

        headers = {"Authorization": "Bearer token123", "Content-Type": "application/json"}
        scrubbed = scrub_headers(headers)
        assert scrubbed["Content-Type"] == "application/json"
        assert scrubbed["Authorization"] != "Bearer token123"

    def test_sensitive_filter(self):
        from security.scrubber import SensitiveFilter

        f = SensitiveFilter()
        assert f is not None
