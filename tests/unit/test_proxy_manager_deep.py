"""Deep proxy manager tests — synchronous methods with mock DB."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestDetectBan:
    def test_detect_ban_403(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(403) is True

    def test_detect_ban_407(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(407) is True

    def test_detect_ban_429(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(429) is True

    def test_detect_ban_body_blocked(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(200, body="Access Denied") is True

    def test_detect_ban_body_banned(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(200, body="Your IP has been banned") is True

    def test_detect_ban_body_captcha(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(200, body="Please complete the captcha") is True

    def test_detect_ban_body_clean(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(200, body="Welcome to our website") is False

    def test_detect_ban_200_empty(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_ban_from_response(200) is False


@pytest.mark.unit
class TestDetectRateLimit:
    def test_detect_rate_limit_429(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_rate_limit(429) is True

    def test_detect_rate_limit_headers_zero(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_rate_limit(200, headers={"x-ratelimit-remaining": "0"}) is True

    def test_detect_rate_limit_headers_nonzero(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_rate_limit(200, headers={"x-ratelimit-remaining": "50"}) is False

    def test_detect_rate_limit_no_headers(self):
        from services.proxy_manager import ProxyManager

        pm = ProxyManager(db=MagicMock())
        assert pm.detect_rate_limit(200) is False


@pytest.mark.unit
class TestAddProxy:
    def test_add_proxy_basic(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        pm = ProxyManager(db=db)
        proxy = pm.add_proxy(host="1.2.3.4", port=8080)
        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert proxy is not None

    def test_add_proxy_with_auth(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        pm = ProxyManager(db=db)
        pm.add_proxy(host="1.2.3.4", port=8080, username="user", password="pass")
        db.add.assert_called_once()

    def test_add_proxy_socks5(self):
        from models.proxy import ProxyProtocol
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        pm = ProxyManager(db=db)
        proxy = pm.add_proxy(host="1.2.3.4", port=1080, protocol=ProxyProtocol.SOCKS5)
        assert proxy is not None


@pytest.mark.unit
class TestRecordSuccessDeep:
    def test_record_success_with_avg(self):
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock()
        mock_proxy.success_count = 5
        mock_proxy.avg_response_ms = 100

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        pm.record_success(proxy_id=1, response_ms=200)
        assert mock_proxy.success_count == 6
        # EMA: 100*0.7 + 200*0.3 = 130
        assert mock_proxy.avg_response_ms == 130

    def test_record_success_first_response(self):
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock()
        mock_proxy.success_count = 0
        mock_proxy.avg_response_ms = None

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        pm.record_success(proxy_id=1, response_ms=150)
        assert mock_proxy.avg_response_ms == 150

    def test_record_success_no_response_ms(self):
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock()
        mock_proxy.success_count = 3
        mock_proxy.avg_response_ms = 100

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        pm.record_success(proxy_id=1)
        assert mock_proxy.success_count == 4
        # avg_response_ms should not change
        assert mock_proxy.avg_response_ms == 100


@pytest.mark.unit
class TestRecordFailureDeep:
    def test_record_failure_rate_limit(self):
        from models.proxy import ProxyStatus
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock()
        mock_proxy.fail_count = 1
        mock_proxy.host = "1.2.3.4"
        mock_proxy.port = 8080

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        result = pm.record_failure(proxy_id=1, is_rate_limit=True)
        assert result == ProxyStatus.RATE_LIMITED

    def test_record_failure_auto_ban(self):
        from unittest.mock import patch

        from models.proxy import ProxyStatus
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock()
        mock_proxy.fail_count = 4  # Will be incremented to 5
        mock_proxy.success_count = 0
        mock_proxy.host = "1.2.3.4"
        mock_proxy.port = 8080
        mock_proxy.status = ProxyStatus.ACTIVE

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        with patch("services.proxy_manager.settings") as mock_settings:
            mock_settings.PROXY_BAN_THRESHOLD = 5
            mock_settings.PROXY_MAX_FAIL_RATE_PCT = 50
            pm.record_failure(proxy_id=1)
        assert mock_proxy.status == ProxyStatus.BANNED

    def test_record_failure_high_fail_rate(self):
        from unittest.mock import patch

        from models.proxy import ProxyStatus
        from services.proxy_manager import ProxyManager

        mock_proxy = MagicMock()
        mock_proxy.fail_count = 8  # Will become 9
        mock_proxy.success_count = 2  # 9/11 = 82% fail rate
        mock_proxy.host = "1.2.3.4"
        mock_proxy.port = 8080
        mock_proxy.status = ProxyStatus.ACTIVE

        db = MagicMock()
        db.get = MagicMock(return_value=mock_proxy)

        pm = ProxyManager(db=db)
        with patch("services.proxy_manager.settings") as mock_settings:
            mock_settings.PROXY_BAN_THRESHOLD = 20
            mock_settings.PROXY_MAX_FAIL_RATE_PCT = 50
            pm.record_failure(proxy_id=1)
        assert mock_proxy.status == ProxyStatus.INACTIVE


@pytest.mark.unit
class TestBulkAddProxies:
    def test_bulk_add(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        pm = ProxyManager(db=db)
        proxies_data = [
            {"host": "1.1.1.1", "port": 8080},
            {"host": "2.2.2.2", "port": 8081},
            {"host": "3.3.3.3", "port": 8082},
        ]
        result = pm.bulk_add_proxies(proxies_data)
        assert len(result) == 3


@pytest.mark.unit
class TestGetStats:
    def test_get_pool_stats(self):
        from services.proxy_manager import ProxyManager

        db = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = MagicMock(return_value=result_mock)

        pm = ProxyManager(db=db)
        stats = pm.get_pool_stats()
        assert isinstance(stats, dict)
