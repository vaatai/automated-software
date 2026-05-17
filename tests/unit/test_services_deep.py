"""Deep coverage tests for services modules via mocking."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestTaskServiceInit:
    def test_init(self):
        from services.task_service import TaskService

        db = AsyncMock()
        svc = TaskService(db=db)
        assert svc.db is db


@pytest.mark.unit
class TestTaskServiceGetStatus:
    @pytest.mark.asyncio
    async def test_get_task_status_no_registration(self):
        from services.task_service import TaskService

        db = AsyncMock()
        row_mock = MagicMock()
        row_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=row_mock)

        svc = TaskService(db=db)

        with patch("services.task_service.AsyncResult") as MockResult:
            mock_result = MagicMock()
            mock_result.status = "PENDING"
            mock_result.ready.return_value = False
            mock_result.failed.return_value = False
            MockResult.return_value = mock_result

            result = await svc.get_task_status("task-123")
            assert result["task_id"] == "task-123"
            assert result["celery_status"] == "PENDING"


@pytest.mark.unit
class TestTaskServiceCancel:
    @pytest.mark.asyncio
    async def test_cancel_task_no_registration(self):
        from services.task_service import TaskService

        db = AsyncMock()
        row_mock = MagicMock()
        row_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=row_mock)

        svc = TaskService(db=db)

        with (
            patch("services.task_service.AsyncResult"),
            patch("services.task_service.celery_app") as mock_app,
        ):
            mock_app.control = MagicMock()
            result = await svc.cancel_task("task-xyz")
            assert result["registration_id"] is None
            assert result["status"] == "revoked"


@pytest.mark.unit
class TestRegistrationServiceInit:
    def test_init(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        svc = RegistrationService(db=db)
        assert svc.db is db


@pytest.mark.unit
class TestRegistrationServiceMethods:
    @pytest.mark.asyncio
    async def test_daily_count_no_records(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        row_mock = MagicMock()
        row_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=row_mock)

        svc = RegistrationService(db=db)
        count = await svc._daily_count(website_id=1)
        assert count == 0

    @pytest.mark.asyncio
    async def test_daily_count_with_records(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        daily_mock = MagicMock()
        daily_mock.registration_count = 15
        row_mock = MagicMock()
        row_mock.scalar_one_or_none.return_value = daily_mock
        db.execute = AsyncMock(return_value=row_mock)

        svc = RegistrationService(db=db)
        count = await svc._daily_count(website_id=1)
        assert count == 15

    @pytest.mark.asyncio
    async def test_get_registration_not_found(self):
        from services.registration_service import RegistrationService

        db = AsyncMock()
        row_mock = MagicMock()
        row_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=row_mock)

        svc = RegistrationService(db=db)
        reg = await svc.get_registration(registration_id=999)
        assert reg is None

    def test_build_reason_all_queued(self):
        from services.registration_service import RegistrationService

        svc = RegistrationService.__new__(RegistrationService)
        reason = svc._build_reason(actual=5, requested=5, overflow_ids=[])
        assert reason is None

    def test_build_reason_partial(self):
        from services.registration_service import RegistrationService

        svc = RegistrationService.__new__(RegistrationService)
        reason = svc._build_reason(actual=3, requested=5, overflow_ids=[4, 5])
        assert reason is not None
        assert isinstance(reason, str)


@pytest.mark.unit
class TestProxyManagerInit:
    def test_init(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        pm = ProxyManager(db=db)
        assert pm.db is db


@pytest.mark.unit
class TestProxyManagerRecordSuccess:
    def test_record_success_no_proxy(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        db.get = MagicMock(return_value=None)
        pm = ProxyManager(db=db)
        pm.record_success(proxy_id=999)  # Should not raise

    def test_record_success_with_proxy(self):
        from models.proxy import Proxy
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock(spec=Proxy)
        mock_proxy.success_count = 5
        mock_proxy.avg_response_ms = 100

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        pm.record_success(proxy_id=1, response_ms=50)
        assert mock_proxy.success_count == 6

    def test_record_success_first_response_ms(self):
        from models.proxy import Proxy
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock(spec=Proxy)
        mock_proxy.success_count = 0
        mock_proxy.avg_response_ms = None

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        pm.record_success(proxy_id=1, response_ms=200)
        assert mock_proxy.avg_response_ms == 200


@pytest.mark.unit
class TestProxyManagerRecordFailure:
    def test_record_failure_no_proxy(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        db.get = MagicMock(return_value=None)
        pm = ProxyManager(db=db)
        pm.record_failure(proxy_id=999)

    def test_record_failure_with_proxy_ban(self):
        from models.proxy import Proxy, ProxyStatus
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock(spec=Proxy)
        mock_proxy.fail_count = 2
        mock_proxy.host = "1.2.3.4"
        mock_proxy.port = 8080

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        result = pm.record_failure(proxy_id=1, is_ban=True)
        assert result == ProxyStatus.BANNED


@pytest.mark.unit
class TestDailyLimitServiceInit:
    def test_init(self):
        from services.daily_limit_service import DailyLimitService

        db = AsyncMock()
        svc = DailyLimitService(db=db)
        assert svc.db is db


@pytest.mark.unit
class TestDashboardServiceInit:
    def test_init(self):
        from services.dashboard_service import DashboardService

        db = AsyncMock()
        svc = DashboardService(db=db)
        assert svc.db is db
