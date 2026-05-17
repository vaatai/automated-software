"""Tests for services/proxy_manager.py — rotation strategies, ban detection, cooldown."""

from unittest.mock import MagicMock

import pytest

from models.proxy import Proxy, ProxyStatus
from services.proxy_manager import ProxyManager, RotationStrategy


@pytest.mark.unit
class TestRotationStrategy:
    def test_lru_is_default(self):
        assert RotationStrategy.LRU == "lru"

    def test_weighted_exists(self):
        assert RotationStrategy.WEIGHTED == "weighted"

    def test_round_robin_exists(self):
        assert RotationStrategy.ROUND_ROBIN == "round_robin"


@pytest.mark.unit
class TestProxyManagerInit:
    def test_init_with_session(self, mock_sync_db):
        manager = ProxyManager(db=mock_sync_db)
        assert manager.db is mock_sync_db


@pytest.mark.unit
class TestProxyManagerRecordResult:
    def _make_mock_proxy(self, **kwargs):
        proxy = MagicMock(spec=Proxy)
        proxy.fail_count = kwargs.get("fail_count", 0)
        proxy.success_count = kwargs.get("success_count", 0)
        proxy.consecutive_failures = kwargs.get("consecutive_failures", 0)
        proxy.status = ProxyStatus.ACTIVE
        proxy.host = "127.0.0.1"
        proxy.port = 8080
        proxy.avg_response_ms = kwargs.get("avg_response_ms", 100)
        return proxy

    def test_record_success(self):
        db = MagicMock()
        proxy = self._make_mock_proxy(success_count=5)
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        manager.record_success(proxy_id=1, response_ms=150)
        assert proxy.success_count == 6

    def test_record_failure(self):
        db = MagicMock()
        proxy = self._make_mock_proxy(fail_count=2)
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        manager.record_failure(proxy_id=1)
        assert proxy.fail_count == 3

    def test_record_failure_ban(self):
        db = MagicMock()
        proxy = self._make_mock_proxy()
        db.get.return_value = proxy
        manager = ProxyManager(db=db)

        status = manager.record_failure(proxy_id=1, is_ban=True)
        assert status == ProxyStatus.BANNED

    def test_record_failure_nonexistent(self):
        db = MagicMock()
        db.get.return_value = None
        manager = ProxyManager(db=db)

        status = manager.record_failure(proxy_id=999)
        assert status == ProxyStatus.INACTIVE


@pytest.mark.unit
class TestProxyManagerSettings:
    def test_ban_threshold_from_settings(self):
        from configs.settings import settings

        assert hasattr(settings, "PROXY_BAN_THRESHOLD")
        assert settings.PROXY_BAN_THRESHOLD > 0

    def test_cooldown_from_settings(self):
        from configs.settings import settings

        assert hasattr(settings, "PROXY_COOLDOWN_SECONDS")
        assert settings.PROXY_COOLDOWN_SECONDS >= 0
