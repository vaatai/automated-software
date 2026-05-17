"""Deep unit tests for security.rate_limiter module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestRateLimiterClass:
    def test_init_defaults(self):
        from security.rate_limiter import RateLimiter

        rl = RateLimiter()
        assert rl._prefix == "ratelimit"
        assert rl._redis is None

    def test_init_custom(self):
        from security.rate_limiter import RateLimiter

        rl = RateLimiter(redis_url="redis://custom:6379", prefix="myprefix")
        assert rl._prefix == "myprefix"
        assert rl._redis_url == "redis://custom:6379"

    @pytest.mark.asyncio
    async def test_check_allowed(self):
        from security.rate_limiter import RateLimiter

        rl = RateLimiter()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 3, True, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        rl._redis = mock_redis

        allowed, info = await rl.check("testkey", max_requests=10, window_seconds=60)
        assert allowed is True
        assert info["limit"] == 10
        assert info["remaining"] >= 0

    @pytest.mark.asyncio
    async def test_check_denied(self):
        from security.rate_limiter import RateLimiter

        rl = RateLimiter()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 10, True, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()
        rl._redis = mock_redis

        allowed, info = await rl.check("testkey", max_requests=10, window_seconds=60)
        assert allowed is False
        assert info["remaining"] == 0

    @pytest.mark.asyncio
    async def test_close(self):
        from security.rate_limiter import RateLimiter

        rl = RateLimiter()
        mock_redis = AsyncMock()
        rl._redis = mock_redis
        await rl.close()
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_noop_when_no_redis(self):
        from security.rate_limiter import RateLimiter

        rl = RateLimiter()
        await rl.close()  # Should not raise


@pytest.mark.unit
class TestClientKeyExtraction:
    def test_ip_from_client(self):
        from security.rate_limiter import _get_client_key

        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key = _get_client_key(request)
        assert key == "ip:1.2.3.4"

    def test_ip_from_forwarded(self):
        from security.rate_limiter import _get_client_key

        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        request.client = MagicMock()

        key = _get_client_key(request)
        assert key == "ip:10.0.0.1"

    def test_user_key(self):
        from security.rate_limiter import _get_client_key

        user = MagicMock()
        user.id = 42
        request = MagicMock()
        request.state = MagicMock()
        request.state.user = user
        request.headers = {}

        key = _get_client_key(request)
        assert key == "user:42"

    def test_unknown_ip(self):
        from security.rate_limiter import _get_client_key

        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        request.client = None

        key = _get_client_key(request)
        assert key == "ip:unknown"


@pytest.mark.unit
class TestRateLimitDependency:
    def test_rate_limit_factory(self):
        from security.rate_limiter import rate_limit

        dep = rate_limit(max_requests=30, window_seconds=60, key_prefix="test")
        assert callable(dep)

    def test_prebuilt_profiles_exist(self):
        from security.rate_limiter import rate_limit_auth, rate_limit_relaxed, rate_limit_standard

        assert callable(rate_limit_auth)
        assert callable(rate_limit_standard)
        assert callable(rate_limit_relaxed)

    @pytest.mark.asyncio
    async def test_rate_limit_check_sets_headers(self):
        from security.rate_limiter import rate_limit

        dep = rate_limit(max_requests=100, window_seconds=60)

        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock()
        response.headers = {}

        with patch("security.rate_limiter._get_limiter") as mock_get:
            mock_limiter = AsyncMock()
            mock_limiter.check = AsyncMock(return_value=(True, {
                "limit": 100, "remaining": 99, "reset": 9999, "window": 60,
            }))
            mock_get.return_value = mock_limiter

            await dep(request, response)

            assert response.headers["X-RateLimit-Limit"] == "100"
            assert response.headers["X-RateLimit-Remaining"] == "99"

    @pytest.mark.asyncio
    async def test_rate_limit_denied_raises_429(self):
        from fastapi import HTTPException

        from security.rate_limiter import rate_limit

        dep = rate_limit(max_requests=1, window_seconds=60)

        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock()
        response.headers = {}

        with patch("security.rate_limiter._get_limiter") as mock_get:
            mock_limiter = AsyncMock()
            mock_limiter.check = AsyncMock(return_value=(False, {
                "limit": 1, "remaining": 0, "reset": 9999, "window": 60,
            }))
            mock_get.return_value = mock_limiter

            with pytest.raises(HTTPException) as exc_info:
                await dep(request, response)
            assert exc_info.value.status_code == 429
