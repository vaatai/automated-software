"""Tests for model properties (is_deleted) and __repr__ for remaining uncovered lines."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
class TestRegistrationIsDeleted:
    def test_is_deleted_false(self):
        from models.registration import Registration

        r = Registration()
        r.deleted_at = None
        assert r.is_deleted is False

    def test_is_deleted_true(self):
        from models.registration import Registration

        r = Registration()
        r.deleted_at = datetime.now(timezone.utc)
        assert r.is_deleted is True


@pytest.mark.unit
class TestWebsiteIsDeleted:
    def test_is_deleted_false(self):
        from models.website import Website

        w = Website()
        w.deleted_at = None
        assert w.is_deleted is False

    def test_is_deleted_true(self):
        from models.website import Website

        w = Website()
        w.deleted_at = datetime.now(timezone.utc)
        assert w.is_deleted is True


@pytest.mark.unit
class TestOTPConfigIsDeleted:
    def test_is_deleted_false(self):
        from models.otp_config import OTPConfig

        o = OTPConfig()
        o.deleted_at = None
        assert o.is_deleted is False

    def test_is_deleted_true(self):
        from models.otp_config import OTPConfig

        o = OTPConfig()
        o.deleted_at = datetime.now(timezone.utc)
        assert o.is_deleted is True

    def test_repr(self):
        from models.otp_config import OTPConfig, OTPProvider, OTPType

        o = OTPConfig()
        o.id = 1
        o.provider = OTPProvider.MAILSLURP
        o.otp_type = OTPType.EMAIL
        s = repr(o)
        assert "OTPConfig" in s


@pytest.mark.unit
class TestRentalNumberIsDeleted:
    def test_is_deleted_false(self):
        from models.rental_number import RentalNumber

        r = RentalNumber()
        r.deleted_at = None
        assert r.is_deleted is False

    def test_is_deleted_true(self):
        from models.rental_number import RentalNumber

        r = RentalNumber()
        r.deleted_at = datetime.now(timezone.utc)
        assert r.is_deleted is True

    def test_repr(self):
        from models.otp_config import OTPProvider
        from models.rental_number import RentalNumber

        r = RentalNumber()
        r.id = 1
        r.phone_number = "+14155551234"
        r.provider = OTPProvider.FIVESIM
        s = repr(r)
        assert "RentalNumber" in s


@pytest.mark.unit
class TestAuditLogFromRequest:
    @pytest.mark.asyncio
    async def test_log_from_request(self):
        from security.audit import AuditAction, AuditLogger

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        logger = AuditLogger(db)
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "1.2.3.4"}
        mock_request.client = MagicMock()
        mock_request.client.host = "5.6.7.8"

        await logger.log_from_request(
            action=AuditAction.LOGIN_SUCCESS,
            request=mock_request,
            user=MagicMock(id=1),
        )
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_flush_failure(self):
        from security.audit import AuditAction, AuditLogger

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock(side_effect=Exception("db error"))

        logger = AuditLogger(db)
        await logger.log(
            action=AuditAction.LOGIN_FAILED,
            user_id=1,
            ip_address="1.2.3.4",
        )


@pytest.mark.unit
class TestProxyIsDeleted:
    def test_is_deleted_false(self):
        from models.proxy import Proxy

        p = Proxy()
        p.deleted_at = None
        assert p.is_deleted is False

    def test_is_deleted_true(self):
        from models.proxy import Proxy

        p = Proxy()
        p.deleted_at = datetime.now(timezone.utc)
        assert p.is_deleted is True

    def test_proxy_url_property(self):
        from models.proxy import Proxy, ProxyProtocol

        p = Proxy()
        p.protocol = ProxyProtocol.HTTP
        p.host = "1.2.3.4"
        p.port = 8080
        p.username = None
        p.password = None
        url = p.url
        assert "1.2.3.4" in url
        assert "8080" in url
