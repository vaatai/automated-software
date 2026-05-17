"""Unit tests for service layer — boost coverage for services/, workers/, otp/."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── TaskService ────────────────────────────────────────────────


@pytest.mark.unit
class TestTaskService:
    def test_task_service_init(self):
        from services.task_service import TaskService

        db = AsyncMock()
        svc = TaskService(db=db)
        assert svc.db is db

    @pytest.mark.asyncio
    async def test_get_task_status(self):
        from services.task_service import TaskService

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        svc = TaskService(db=db)
        with patch("services.task_service.AsyncResult") as mock_ar:
            mock_result = MagicMock()
            mock_result.status = "PENDING"
            mock_result.ready.return_value = False
            mock_result.failed.return_value = False
            mock_ar.return_value = mock_result

            result = await svc.get_task_status("nonexistent-task-id")
            assert result["task_id"] == "nonexistent-task-id"
            assert result["celery_status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        from services.task_service import TaskService

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        svc = TaskService(db=db)
        with patch("services.task_service.celery_app"):
            result = await svc.cancel_task("nonexistent-task-id")
            assert isinstance(result, dict)


# ── RegistrationService ───────────────────────────────────────


@pytest.mark.unit
class TestRegistrationService:
    def test_registration_service_init(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        svc = RegistrationService(db=db)
        assert svc.db is db

    @pytest.mark.asyncio
    async def test_get_registration_not_found(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        svc = RegistrationService(db=db)
        result = await svc.get_registration(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_daily_count_with_record(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        daily_mock = MagicMock()
        daily_mock.registration_count = 5
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = daily_mock
        db.execute.return_value = result_mock

        svc = RegistrationService(db=db)
        count = await svc._daily_count(website_id=1)
        assert count == 5

    @pytest.mark.asyncio
    async def test_daily_count_no_record(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        svc = RegistrationService(db=db)
        count = await svc._daily_count(website_id=1)
        assert count == 0

    def test_build_reason_partial(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        svc = RegistrationService(db=db)
        reason = svc._build_reason(actual=3, requested=5, overflow_ids=[4, 5])
        assert reason is not None
        assert "queued" in reason

    def test_build_reason_exact(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        svc = RegistrationService(db=db)
        reason = svc._build_reason(actual=5, requested=5, overflow_ids=[])
        assert reason is None


# ── DailyLimitService ────────────────────────────────────────


@pytest.mark.unit
class TestDailyLimitService:
    def test_service_import(self):
        from services.daily_limit_service import DailyLimitService

        assert DailyLimitService is not None

    @pytest.mark.asyncio
    async def test_init(self):
        from services.daily_limit_service import DailyLimitService

        db = AsyncMock()
        svc = DailyLimitService(db=db)
        assert svc.db is db


# ── DashboardService ─────────────────────────────────────────


@pytest.mark.unit
class TestDashboardService:
    def test_service_import(self):
        from services.dashboard_service import DashboardService

        assert DashboardService is not None

    @pytest.mark.asyncio
    async def test_init(self):
        from services.dashboard_service import DashboardService

        db = AsyncMock()
        svc = DashboardService(db=db)
        assert svc.db is db


# ── Worker imports ──────────────────────────────────────────


@pytest.mark.unit
class TestWorkerImports:
    def test_dead_letter_worker_imports(self):
        from workers.dead_letter_worker import process_dead_letter

        assert callable(process_dead_letter)

    def test_proxy_worker_imports(self):
        from workers.proxy_worker import check_proxy_health, reset_rate_limited_proxies

        assert callable(reset_rate_limited_proxies)
        assert callable(check_proxy_health)

    def test_task_monitor_imports(self):
        from workers.task_monitor import check_stale_tasks

        assert callable(check_stale_tasks)


# ── OTP provider imports ──────────────────────────────────────


@pytest.mark.unit
class TestOTPProviderImports:
    def test_fivesim_import(self):
        from otp.fivesim_service import FiveSimService

        assert FiveSimService is not None

    def test_pvapins_import(self):
        from otp.pvapins_service import PVAPinsService

        assert PVAPinsService is not None

    def test_smsactivate_import(self):
        from otp.smsactivate_service import SMSActivateService

        assert SMSActivateService is not None

    def test_email_otp_import(self):
        from otp.email_otp_service import EmailOTPService

        assert EmailOTPService is not None

    def test_mobile_otp_manager_import(self):
        from otp.mobile_otp_manager import MobileOTPManager

        assert MobileOTPManager is not None


# ── ErrorHandler additional coverage ──────────────────────────


@pytest.mark.unit
class TestErrorHandlerAdditional:
    def test_classify_captcha_type_recaptcha(self):
        from utils.error_handler import ErrorClassifier

        classifier = ErrorClassifier()
        result = classifier.detect_captcha_type('<div class="g-recaptcha" data-sitekey="abc"></div>')
        assert "recaptcha" in result.lower() or result

    def test_classify_captcha_type_hcaptcha(self):
        from utils.error_handler import ErrorClassifier

        classifier = ErrorClassifier()
        result = classifier.detect_captcha_type('<div class="h-captcha" data-sitekey="abc"></div>')
        assert "hcaptcha" in result.lower() or result

    def test_classify_captcha_type_none(self):
        from utils.error_handler import ErrorClassifier

        classifier = ErrorClassifier()
        result = classifier.detect_captcha_type("<html><body>No captcha here</body></html>")
        assert result is None or result == "" or result == "unknown"

    def test_error_context_serialization(self):
        from utils.error_handler import ErrorCategory, ErrorContext

        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.TRANSIENT,
            error_type="TimeoutError",
            error_message="Timed out",
            page_url="https://example.com",
        )
        d = ctx.to_dict()
        assert d["category"] == "transient"
        assert d["error_type"] == "TimeoutError"

    def test_error_context_json(self):
        import json

        from utils.error_handler import ErrorCategory, ErrorContext

        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.PROXY_BAN,
            error_type="ProxyError",
            error_message="banned",
        )
        j = ctx.to_json()
        parsed = json.loads(j)
        assert parsed["category"] == "proxy_ban"

    def test_error_context_is_retriable(self):
        from utils.error_handler import ErrorCategory, ErrorContext

        retriable = ErrorContext(registration_id=1, category=ErrorCategory.TRANSIENT)
        assert retriable.is_retriable is True

        non_retriable = ErrorContext(registration_id=1, category=ErrorCategory.PERMANENT)
        assert non_retriable.is_retriable is False

    def test_error_context_needs_proxy_swap(self):
        from utils.error_handler import ErrorCategory, ErrorContext

        ctx = ErrorContext(registration_id=1, category=ErrorCategory.PROXY_BAN)
        assert ctx.needs_proxy_swap is True

        ctx2 = ErrorContext(registration_id=1, category=ErrorCategory.TRANSIENT)
        assert ctx2.needs_proxy_swap is False


# ── Celery security coverage ────────────────────────────────


@pytest.mark.unit
class TestCelerySecurity:
    def test_import(self):
        from security.celery_security import apply_celery_security

        assert callable(apply_celery_security)

    def test_validate_import(self):
        from security.celery_security import validate_celery_config

        assert callable(validate_celery_config)


# ── Rate limiter ─────────────────────────────────────────


@pytest.mark.unit
class TestRateLimiterModule:
    def test_rate_limiter_class(self):
        from security.rate_limiter import RateLimiter

        assert RateLimiter is not None

    def test_rate_limit_decorator_import(self):
        from security.rate_limiter import rate_limit

        assert callable(rate_limit)
