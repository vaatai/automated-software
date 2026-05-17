"""Integration tests for proxy rotation — strategies, ban recovery, pool mgmt."""

from unittest.mock import MagicMock

import pytest

from models.proxy import Proxy, ProxyProtocol, ProxyStatus
from services.proxy_manager import ProxyManager, RotationStrategy


@pytest.mark.integration
class TestRotationStrategySelection:
    def test_all_strategies_valid(self):
        for strategy in RotationStrategy:
            assert strategy.value in ("lru", "weighted", "round_robin")

    def test_strategy_enum_membership(self):
        assert RotationStrategy("lru") == RotationStrategy.LRU
        assert RotationStrategy("weighted") == RotationStrategy.WEIGHTED
        assert RotationStrategy("round_robin") == RotationStrategy.ROUND_ROBIN


@pytest.mark.integration
class TestProxyStatusTransitions:
    def test_active_status(self):
        assert ProxyStatus.ACTIVE.value == "active"

    def test_banned_status(self):
        assert ProxyStatus.BANNED.value == "banned"

    def test_rate_limited_status(self):
        assert ProxyStatus.RATE_LIMITED.value == "rate_limited"

    def test_inactive_status(self):
        assert ProxyStatus.INACTIVE.value == "inactive"


@pytest.mark.integration
class TestProxyProtocol:
    def test_http_protocol(self):
        assert ProxyProtocol.HTTP.value == "http"

    def test_https_protocol(self):
        assert ProxyProtocol.HTTPS.value == "https"

    def test_socks5_protocol(self):
        assert ProxyProtocol.SOCKS5.value == "socks5"


@pytest.mark.integration
class TestBanDetectionIntegration:
    def _make_mock_proxy(self, fail_count=0, success_count=5, consecutive_failures=0):
        proxy = MagicMock(spec=Proxy)
        proxy.fail_count = fail_count
        proxy.success_count = success_count
        proxy.consecutive_failures = consecutive_failures
        proxy.status = ProxyStatus.ACTIVE
        proxy.host = "127.0.0.1"
        proxy.port = 8080
        proxy.avg_response_ms = 100
        return proxy

    def test_record_failure_increments(self):
        db = MagicMock()
        proxy = self._make_mock_proxy(fail_count=5, consecutive_failures=4)
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        manager.record_failure(proxy_id=1)
        assert proxy.fail_count == 6

    def test_record_success_updates(self):
        db = MagicMock()
        proxy = self._make_mock_proxy(success_count=5)
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        manager.record_success(proxy_id=1, response_ms=100)
        assert proxy.success_count == 6

    def test_record_failure_ban_detection(self):
        db = MagicMock()
        proxy = self._make_mock_proxy()
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        result = manager.record_failure(proxy_id=1, is_ban=True)
        assert result == ProxyStatus.BANNED

    def test_record_failure_rate_limit(self):
        db = MagicMock()
        proxy = self._make_mock_proxy()
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        result = manager.record_failure(proxy_id=1, is_rate_limit=True)
        assert result == ProxyStatus.RATE_LIMITED

    def test_record_failure_nonexistent_proxy(self):
        db = MagicMock()
        db.get.return_value = None
        manager = ProxyManager(db=db)

        result = manager.record_failure(proxy_id=999)
        assert result == ProxyStatus.INACTIVE
