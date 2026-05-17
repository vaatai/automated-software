"""Unit tests for security/rate_limiter.py — rate limiter config and profiles."""

import pytest

from security.rate_limiter import RateLimiter


@pytest.mark.unit
class TestRateLimiterInit:
    def test_default_init(self):
        limiter = RateLimiter()
        assert limiter._prefix == "ratelimit"
        assert limiter._redis is None

    def test_custom_prefix(self):
        limiter = RateLimiter(prefix="test-limit")
        assert limiter._prefix == "test-limit"

    def test_custom_redis_url(self):
        limiter = RateLimiter(redis_url="redis://custom:6379/0")
        assert limiter._redis_url == "redis://custom:6379/0"

    def test_check_method_exists(self):
        limiter = RateLimiter()
        assert hasattr(limiter, "check")
        assert callable(limiter.check)
