"""Proxy management service — rotation, ban detection, health tracking,
country routing, cooldown, and pool management.

Integrates with Playwright workers to provide per-task proxy assignment
with intelligent rotation, automatic ban detection, and health metrics.

Rotation strategies:
  - LRU (least-recently-used) — default, distributes load evenly
  - WEIGHTED — prefers proxies with higher success rates
  - ROUND_ROBIN — sequential rotation through pool
"""

import enum
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from configs.settings import settings
from models.proxy import Proxy, ProxyProtocol, ProxyStatus

logger = logging.getLogger(__name__)


class RotationStrategy(str, enum.Enum):
    LRU = "lru"
    WEIGHTED = "weighted"
    ROUND_ROBIN = "round_robin"


class ProxyManager:
    """Manages proxy pool with rotation, health tracking, and ban detection.

    Uses synchronous SQLAlchemy sessions (for Celery worker compatibility).
    Each Celery worker should create its own ProxyManager instance with
    a fresh DB session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── proxy assignment ────────────────────────────────────

    def assign_proxy(
        self,
        country: str | None = None,
        protocol: ProxyProtocol | None = None,
        strategy: RotationStrategy = RotationStrategy.LRU,
        exclude_ids: list[int] | None = None,
    ) -> Proxy | None:
        """Select and assign a proxy from the pool.

        Args:
            country: ISO country code filter (e.g., "US", "DE")
            protocol: Protocol filter (HTTP, HTTPS, SOCKS5)
            strategy: Rotation strategy
            exclude_ids: Proxy IDs to exclude (e.g., already failed for this task)

        Returns the assigned Proxy or None if pool is empty.
        """
        q = select(Proxy).where(
            Proxy.status == ProxyStatus.ACTIVE,
            Proxy.deleted_at.is_(None),
        )

        if country:
            q = q.where(Proxy.country == country.upper())
        if protocol:
            q = q.where(Proxy.protocol == protocol)
        if exclude_ids:
            q = q.where(Proxy.id.notin_(exclude_ids))

        # Apply cooldown filter — skip proxies used too recently after failure
        cooldown_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.PROXY_COOLDOWN_SECONDS
        )
        q = q.where(
            (Proxy.last_used_at.is_(None))
            | (Proxy.fail_count == 0)
            | (Proxy.last_used_at < cooldown_cutoff)
        )

        # Apply rotation strategy ordering
        if strategy == RotationStrategy.LRU:
            q = q.order_by(Proxy.last_used_at.asc().nulls_first())
        elif strategy == RotationStrategy.WEIGHTED:
            # Prefer proxies with better success rates
            q = q.order_by(
                (Proxy.fail_count * 1.0 / func.greatest(Proxy.success_count + Proxy.fail_count, 1)).asc(),
                Proxy.last_used_at.asc().nulls_first(),
            )
        elif strategy == RotationStrategy.ROUND_ROBIN:
            q = q.order_by(Proxy.last_used_at.asc().nulls_first(), Proxy.id.asc())

        proxy = self.db.execute(q.limit(1)).scalar_one_or_none()

        if proxy:
            proxy.last_used_at = datetime.now(timezone.utc)
            self.db.flush()
            logger.debug(
                "Assigned proxy %d (%s:%d) via %s strategy",
                proxy.id, proxy.host, proxy.port, strategy.value,
            )

        return proxy

    def assign_proxy_for_country(
        self, country: str, fallback: bool = True
    ) -> Proxy | None:
        """Assign a proxy from a specific country, with optional fallback to any."""
        proxy = self.assign_proxy(country=country)
        if not proxy and fallback:
            proxy = self.assign_proxy()
            if proxy:
                logger.info(
                    "No %s proxy available, fell back to %s:%d (%s)",
                    country, proxy.host, proxy.port, proxy.country or "unknown",
                )
        return proxy

    # ── health tracking ─────────────────────────────────────

    def record_success(self, proxy_id: int, response_ms: int | None = None) -> None:
        """Record a successful use of a proxy."""
        proxy = self.db.get(Proxy, proxy_id)
        if not proxy:
            return

        proxy.success_count += 1

        # Update rolling average response time
        if response_ms is not None:
            if proxy.avg_response_ms is not None:
                # Exponential moving average (α = 0.3)
                proxy.avg_response_ms = int(
                    proxy.avg_response_ms * 0.7 + response_ms * 0.3
                )
            else:
                proxy.avg_response_ms = response_ms

        self.db.flush()

    def record_failure(
        self,
        proxy_id: int,
        error: str | None = None,
        is_ban: bool = False,
        is_rate_limit: bool = False,
    ) -> ProxyStatus:
        """Record a failed use of a proxy and check for ban/rate-limit.

        Returns the proxy's new status after the failure.
        """
        proxy = self.db.get(Proxy, proxy_id)
        if not proxy:
            return ProxyStatus.INACTIVE

        proxy.fail_count += 1

        # Explicit ban detection
        if is_ban:
            proxy.status = ProxyStatus.BANNED
            logger.warning(
                "Proxy %d (%s:%d) marked BANNED: %s",
                proxy_id, proxy.host, proxy.port, error or "ban detected",
            )
            self.db.flush()
            return proxy.status

        # Rate-limit detection
        if is_rate_limit:
            proxy.status = ProxyStatus.RATE_LIMITED
            logger.warning(
                "Proxy %d (%s:%d) marked RATE_LIMITED: %s",
                proxy_id, proxy.host, proxy.port, error or "rate limit hit",
            )
            self.db.flush()
            return proxy.status

        # Auto-ban detection: consecutive failures exceed threshold
        if proxy.fail_count >= settings.PROXY_BAN_THRESHOLD and proxy.success_count == 0:
            proxy.status = ProxyStatus.BANNED
            logger.warning(
                "Proxy %d auto-banned: %d consecutive failures without success",
                proxy_id, proxy.fail_count,
            )
        # Auto-deactivate: failure rate too high (min 10 attempts)
        elif (proxy.success_count + proxy.fail_count) >= 10:
            total = proxy.success_count + proxy.fail_count
            fail_rate = (proxy.fail_count / total) * 100
            if fail_rate > settings.PROXY_MAX_FAIL_RATE_PCT:
                proxy.status = ProxyStatus.INACTIVE
                logger.warning(
                    "Proxy %d auto-deactivated: %.1f%% failure rate (%d/%d)",
                    proxy_id, fail_rate, proxy.fail_count, total,
                )

        self.db.flush()
        return proxy.status

    def detect_ban_from_response(self, status_code: int, body: str = "") -> bool:
        """Heuristic ban detection from HTTP response."""
        if status_code in (403, 407, 429):
            return True
        ban_indicators = [
            "access denied", "blocked", "banned", "captcha",
            "too many requests", "rate limit", "forbidden",
        ]
        body_lower = body.lower()
        return any(indicator in body_lower for indicator in ban_indicators)

    def detect_rate_limit(self, status_code: int, headers: dict | None = None) -> bool:
        """Detect rate limiting from HTTP response."""
        if status_code == 429:
            return True
        if headers:
            remaining = headers.get("x-ratelimit-remaining", "")
            if remaining == "0":
                return True
        return False

    # ── pool management ─────────────────────────────────────

    def add_proxy(
        self,
        host: str,
        port: int,
        protocol: ProxyProtocol = ProxyProtocol.HTTP,
        username: str | None = None,
        password: str | None = None,
        country: str | None = None,
        provider: str | None = None,
        label: str | None = None,
    ) -> Proxy:
        """Add a new proxy to the pool."""
        proxy = Proxy(
            host=host,
            port=port,
            protocol=protocol,
            status=ProxyStatus.ACTIVE,
            username=username,
            password=password,
            country=country.upper() if country else None,
            provider=provider,
            label=label,
        )
        self.db.add(proxy)
        self.db.flush()
        logger.info("Added proxy %d: %s:%d (%s)", proxy.id, host, port, protocol.value)
        return proxy

    def bulk_add_proxies(self, proxies: list[dict]) -> list[Proxy]:
        """Add multiple proxies at once."""
        added = []
        for p in proxies:
            proxy = self.add_proxy(**p)
            added.append(proxy)
        self.db.commit()
        return added

    def remove_proxy(self, proxy_id: int) -> bool:
        """Soft-delete a proxy."""
        proxy = self.db.get(Proxy, proxy_id)
        if not proxy:
            return False
        proxy.deleted_at = datetime.now(timezone.utc)
        proxy.status = ProxyStatus.INACTIVE
        self.db.flush()
        logger.info("Removed proxy %d (%s:%d)", proxy_id, proxy.host, proxy.port)
        return True

    def reactivate_proxy(self, proxy_id: int, reset_stats: bool = False) -> bool:
        """Reactivate a banned/rate-limited/inactive proxy."""
        proxy = self.db.get(Proxy, proxy_id)
        if not proxy:
            return False
        proxy.status = ProxyStatus.ACTIVE
        if reset_stats:
            proxy.fail_count = 0
            proxy.success_count = 0
            proxy.avg_response_ms = None
        self.db.flush()
        logger.info("Reactivated proxy %d (%s:%d)", proxy_id, proxy.host, proxy.port)
        return True

    def reset_rate_limited_proxies(self) -> int:
        """Reset all RATE_LIMITED proxies back to ACTIVE (for scheduled use)."""
        result = self.db.execute(
            update(Proxy)
            .where(Proxy.status == ProxyStatus.RATE_LIMITED)
            .values(status=ProxyStatus.ACTIVE)
        )
        count = result.rowcount
        if count:
            self.db.flush()
            logger.info("Reset %d rate-limited proxies to ACTIVE", count)
        return count

    # ── health checks ───────────────────────────────────────

    def check_proxy_health(self, proxy_id: int) -> dict:
        """Get health metrics for a single proxy."""
        proxy = self.db.get(Proxy, proxy_id)
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} not found")

        total = proxy.success_count + proxy.fail_count
        success_rate = (proxy.success_count / total * 100) if total > 0 else 0

        return {
            "proxy_id": proxy.id,
            "host": proxy.host,
            "port": proxy.port,
            "protocol": proxy.protocol.value,
            "status": proxy.status.value,
            "country": proxy.country,
            "provider": proxy.provider,
            "success_count": proxy.success_count,
            "fail_count": proxy.fail_count,
            "total_requests": total,
            "success_rate_pct": round(success_rate, 1),
            "avg_response_ms": proxy.avg_response_ms,
            "last_used_at": proxy.last_used_at.isoformat() if proxy.last_used_at else None,
            "last_checked_at": proxy.last_checked_at.isoformat() if proxy.last_checked_at else None,
        }

    def get_pool_stats(self) -> dict:
        """Get aggregate stats for the proxy pool."""
        all_proxies = self.db.execute(
            select(Proxy).where(Proxy.deleted_at.is_(None))
        ).scalars().all()

        by_status: dict[str, int] = {}
        by_country: dict[str, int] = {}
        by_protocol: dict[str, int] = {}
        total_success = 0
        total_fail = 0

        for p in all_proxies:
            by_status[p.status.value] = by_status.get(p.status.value, 0) + 1
            if p.country:
                by_country[p.country] = by_country.get(p.country, 0) + 1
            by_protocol[p.protocol.value] = by_protocol.get(p.protocol.value, 0) + 1
            total_success += p.success_count
            total_fail += p.fail_count

        total = total_success + total_fail
        overall_success_rate = (total_success / total * 100) if total > 0 else 0

        return {
            "total_proxies": len(all_proxies),
            "by_status": by_status,
            "by_country": by_country,
            "by_protocol": by_protocol,
            "total_requests": total,
            "total_success": total_success,
            "total_fail": total_fail,
            "overall_success_rate_pct": round(overall_success_rate, 1),
        }

    def get_proxies_by_country(self, country: str) -> list[dict]:
        """List proxies available in a specific country."""
        proxies = self.db.execute(
            select(Proxy).where(
                Proxy.country == country.upper(),
                Proxy.deleted_at.is_(None),
            )
        ).scalars().all()

        return [self._proxy_to_dict(p) for p in proxies]

    def get_available_countries(self) -> list[dict]:
        """List countries with available active proxies."""
        rows = self.db.execute(
            select(Proxy.country, func.count().label("count"))
            .where(
                Proxy.status == ProxyStatus.ACTIVE,
                Proxy.deleted_at.is_(None),
                Proxy.country.isnot(None),
            )
            .group_by(Proxy.country)
            .order_by(func.count().desc())
        ).all()

        return [{"country": row[0], "active_count": row[1]} for row in rows]

    def list_proxies(
        self,
        status: ProxyStatus | None = None,
        country: str | None = None,
        provider: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """List proxies with optional filters."""
        q = select(Proxy).where(Proxy.deleted_at.is_(None))

        if status:
            q = q.where(Proxy.status == status)
        if country:
            q = q.where(Proxy.country == country.upper())
        if provider:
            q = q.where(Proxy.provider == provider)

        q = q.order_by(Proxy.id.asc()).limit(limit).offset(offset)
        proxies = self.db.execute(q).scalars().all()
        return [self._proxy_to_dict(p) for p in proxies]

    # ── retry with proxy rotation ───────────────────────────

    def get_retry_proxy(
        self,
        failed_proxy_id: int,
        country: str | None = None,
        exclude_ids: list[int] | None = None,
    ) -> Proxy | None:
        """Get a different proxy after a failure (for retries).

        Excludes the failed proxy and any previously excluded ones.
        """
        all_excluded = list(exclude_ids or [])
        if failed_proxy_id not in all_excluded:
            all_excluded.append(failed_proxy_id)

        return self.assign_proxy(country=country, exclude_ids=all_excluded)

    # ── helpers ─────────────────────────────────────────────

    def _proxy_to_dict(self, proxy: Proxy) -> dict:
        total = proxy.success_count + proxy.fail_count
        success_rate = (proxy.success_count / total * 100) if total > 0 else 0

        return {
            "id": proxy.id,
            "host": proxy.host,
            "port": proxy.port,
            "protocol": proxy.protocol.value,
            "status": proxy.status.value,
            "country": proxy.country,
            "provider": proxy.provider,
            "label": proxy.label,
            "username": proxy.username,
            "success_count": proxy.success_count,
            "fail_count": proxy.fail_count,
            "success_rate_pct": round(success_rate, 1),
            "avg_response_ms": proxy.avg_response_ms,
            "last_used_at": proxy.last_used_at.isoformat() if proxy.last_used_at else None,
            "created_at": proxy.created_at.isoformat() if proxy.created_at else None,
        }
