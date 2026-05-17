"""Deep coverage tests for model classes."""

import pytest


@pytest.mark.unit
class TestWebsiteModel:
    def test_website_str(self):
        from models.website import Website, WebsiteStatus

        w = Website()
        w.id = 1
        w.name = "Test Site"
        w.status = WebsiteStatus.ACTIVE
        s = repr(w)
        assert isinstance(s, str)
        assert "Test Site" in s

    def test_website_status_enum(self):
        from models.website import WebsiteStatus

        assert WebsiteStatus.ACTIVE is not None
        assert WebsiteStatus.PAUSED is not None
        assert WebsiteStatus.INACTIVE is not None


@pytest.mark.unit
class TestProxyModel:
    def test_proxy_status_enum(self):
        from models.proxy import ProxyStatus

        assert ProxyStatus.ACTIVE is not None
        assert ProxyStatus.BANNED is not None
        assert ProxyStatus.INACTIVE is not None
        assert ProxyStatus.RATE_LIMITED is not None

    def test_proxy_protocol_enum(self):
        from models.proxy import ProxyProtocol

        assert ProxyProtocol.HTTP is not None
        assert ProxyProtocol.SOCKS5 is not None

    def test_proxy_str(self):
        from models.proxy import Proxy, ProxyStatus

        p = Proxy()
        p.id = 1
        p.host = "1.2.3.4"
        p.port = 8080
        p.status = ProxyStatus.ACTIVE
        s = repr(p)
        assert isinstance(s, str)


@pytest.mark.unit
class TestRegistrationModel:
    def test_registration_status_enum(self):
        from models.registration import RegistrationStatus

        assert RegistrationStatus.PENDING is not None
        assert RegistrationStatus.IN_PROGRESS is not None
        assert RegistrationStatus.COMPLETED is not None
        assert RegistrationStatus.FAILED is not None
        assert RegistrationStatus.CANCELLED is not None

    def test_registration_str(self):
        from models.registration import Registration, RegistrationStatus

        r = Registration()
        r.id = 42
        r.status = RegistrationStatus.PENDING
        s = repr(r)
        assert isinstance(s, str)


@pytest.mark.unit
class TestTaskLogModel:
    def test_log_level_enum(self):
        from models.task_log import LogLevel

        assert LogLevel.INFO is not None
        assert LogLevel.WARNING is not None
        assert LogLevel.ERROR is not None

    def test_task_log_str(self):
        from models.task_log import LogLevel, TaskLog

        t = TaskLog()
        t.id = 1
        t.level = LogLevel.INFO
        t.step = "test"
        s = repr(t)
        assert isinstance(s, str)


@pytest.mark.unit
class TestUserModel:
    def test_user_role_enum(self):
        from models.user import UserRole

        assert UserRole.VIEWER is not None
        assert UserRole.OPERATOR is not None
        assert UserRole.ADMIN is not None
        assert UserRole.SUPER_ADMIN is not None

    def test_user_str(self):
        from models.user import User, UserRole

        u = User()
        u.id = 1
        u.email = "test@example.com"
        u.role = UserRole.ADMIN
        s = repr(u)
        assert isinstance(s, str)


@pytest.mark.unit
class TestDailyLimitModel:
    def test_daily_limit_str(self):
        from models.daily_limit import DailyLimit

        d = DailyLimit()
        d.id = 1
        s = repr(d)
        assert isinstance(s, str)


@pytest.mark.unit
class TestOTPConfigModel:
    def test_otp_type_enum(self):
        from models.otp_config import OTPType

        assert OTPType.EMAIL is not None
        assert OTPType.SMS is not None

    def test_otp_provider_enum(self):
        from models.otp_config import OTPProvider

        assert OTPProvider.MAILSLURP is not None
        assert OTPProvider.FIVESIM is not None


@pytest.mark.unit
class TestRentalNumberModel:
    def test_rental_status_enum(self):
        from models.rental_number import RentalStatus

        assert RentalStatus.RENTED is not None
        assert RentalStatus.OTP_RECEIVED is not None
        assert RentalStatus.FINISHED is not None
        assert RentalStatus.CANCELLED is not None
        assert RentalStatus.EXPIRED is not None


@pytest.mark.unit
class TestAuditLogModel:
    def test_audit_log_import(self):
        from security.audit import AuditLog

        assert AuditLog is not None

    def test_audit_log_str(self):
        from security.audit import AuditAction, AuditLog

        a = AuditLog()
        a.id = 1
        a.action = AuditAction.LOGIN_SUCCESS
        a.user_id = 42
        s = repr(a)
        assert isinstance(s, str)
        assert "login_success" in s
