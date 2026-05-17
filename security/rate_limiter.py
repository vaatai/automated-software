"""Token-bucket rate limiting backed by Redis.

Provides:
  - ``RateLimiter``: configurable per-key rate limiter using Redis.
  - ``rate_limit()``: FastAPI dependency factory for per-endpoint rate limiting.
  - Rate limit headers (``X-RateLimit-*``) are set on responses automatically.

Rate limits can be applied per IP, per user, or per custom key.
"""

import logging
import time

from fastapi import HTTPException, Request, Response, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-backed sliding-window rate limiter.

    Uses sorted sets with timestamps to implement a sliding window.
    Each key tracks request timestamps; expired entries are pruned on check.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "ratelimit",
    ) -> None:
        self._prefix = prefix
        self._redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            from configs.settings import settings

            url = self._redis_url or settings.REDIS_URL
            self._redis = aioredis.from_url(url, decode_responses=True)
        return self._redis

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """Check if the request is within the rate limit.

        Returns:
            Tuple of (allowed: bool, info: dict) where info contains
            ``limit``, ``remaining``, ``reset`` fields for response headers.
        """
        r = await self._get_redis()
        full_key = f"{self._prefix}:{key}"
        now = time.time()
        window_start = now - window_seconds

        pipe = r.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(full_key, "-inf", window_start)
        # Count current entries
        pipe.zcard(full_key)
        # Add current request
        pipe.zadd(full_key, {str(now): now})
        # Set TTL
        pipe.expire(full_key, window_seconds + 1)
        results = await pipe.execute()

        current_count = results[1]
        allowed = current_count < max_requests
        remaining = max(0, max_requests - current_count - (1 if allowed else 0))
        reset_at = int(now + window_seconds)

        if not allowed:
            # Remove the request we just added since it's denied
            await r.zrem(full_key, str(now))

        return allowed, {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_at,
            "window": window_seconds,
        }

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()


# ── module-level singleton ──────────────────────────────────
_limiter: RateLimiter | None = None


def _get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def _get_client_key(request: Request) -> str:
    """Extract a rate-limit key from the request.

    Uses the authenticated user ID if available, otherwise falls back to IP.
    """
    # Check for user set by auth middleware
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    # Fall back to client IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


def rate_limit(
    max_requests: int = 60,
    window_seconds: int = 60,
    key_prefix: str = "",
):
    """FastAPI dependency factory for rate limiting.

    Usage::

        @router.get("/endpoint", dependencies=[Depends(rate_limit(30, 60))])
        async def my_endpoint(): ...

    Args:
        max_requests: Maximum requests allowed in the window.
        window_seconds: Window duration in seconds.
        key_prefix: Optional prefix to scope the rate limit (e.g., endpoint name).
    """

    async def _check(request: Request, response: Response) -> None:
        limiter = _get_limiter()
        client_key = _get_client_key(request)
        full_key = f"{key_prefix}:{client_key}" if key_prefix else client_key

        allowed, info = await limiter.check(full_key, max_requests, window_seconds)

        # Set rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        if not allowed:
            logger.warning(
                "Rate limit exceeded: %s (%d/%d)", full_key, info["limit"], info["window"]
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["window"]),
                },
            )

    return _check


# ── pre-built rate limit profiles ───────────────────────────
rate_limit_strict = rate_limit(max_requests=10, window_seconds=60, key_prefix="strict")
rate_limit_auth = rate_limit(max_requests=5, window_seconds=300, key_prefix="auth")
rate_limit_standard = rate_limit(max_requests=60, window_seconds=60, key_prefix="standard")
rate_limit_relaxed = rate_limit(max_requests=200, window_seconds=60, key_prefix="relaxed")
