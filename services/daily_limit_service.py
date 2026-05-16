"""Daily limit management service — enforcement, overflow queuing,
cooldown tracking, and admin controls.

Prevents website bans, rate limits, and queue overload by:
  - Enforcing per-website daily registration caps
  - Queuing overflow tasks for next-day processing
  - Tracking cooldown periods between registrations
  - Providing admin APIs for dynamic limit adjustment
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.daily_limit import DailyLimit
from models.registration import Registration, RegistrationStatus
from models.website import Website

logger = logging.getLogger(__name__)


class DailyLimitService:
    """Manages daily registration limits and overflow queuing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── limit enforcement ───────────────────────────────────

    async def get_daily_record(
        self, website_id: int, target_date: date | None = None
    ) -> DailyLimit | None:
        target = target_date or date.today()
        row = await self.db.execute(
            select(DailyLimit).where(
                DailyLimit.website_id == website_id,
                DailyLimit.date == target,
            )
        )
        return row.scalar_one_or_none()

    async def get_or_create_daily_record(
        self, website_id: int, target_date: date | None = None
    ) -> DailyLimit:
        target = target_date or date.today()
        record = await self.get_daily_record(website_id, target)
        if not record:
            record = DailyLimit(
                website_id=website_id,
                date=target,
                registration_count=0,
                success_count=0,
                failure_count=0,
            )
            self.db.add(record)
            await self.db.flush()
        return record

    async def check_limit(
        self, website_id: int, requested: int = 1
    ) -> dict:
        """Check if registrations can proceed within daily limits.

        Returns dict with:
          allowed: bool
          remaining: int
          limit: int
          used: int
          overflow_count: int (how many exceed the limit)
        """
        website = await self._get_website(website_id)
        record = await self.get_or_create_daily_record(website_id)

        limit = website.max_registrations_per_day
        used = record.registration_count
        remaining = max(0, limit - used)
        can_queue = min(requested, remaining)
        overflow = requested - can_queue

        return {
            "allowed": can_queue > 0,
            "can_queue": can_queue,
            "remaining": remaining,
            "limit": limit,
            "used": used,
            "overflow_count": overflow,
        }

    async def check_cooldown(
        self, website_id: int, cooldown_seconds: int = 30
    ) -> dict:
        """Check if enough time has passed since the last registration for a website.

        Prevents rapid-fire registrations that could trigger rate limits.
        """
        row = await self.db.execute(
            select(Registration.created_at)
            .where(
                Registration.website_id == website_id,
                Registration.status.in_([
                    RegistrationStatus.PENDING,
                    RegistrationStatus.IN_PROGRESS,
                    RegistrationStatus.COMPLETED,
                ]),
            )
            .order_by(Registration.created_at.desc())
            .limit(1)
        )
        last = row.scalar_one_or_none()

        if not last:
            return {"ready": True, "wait_seconds": 0}

        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        wait = max(0, cooldown_seconds - elapsed)

        return {
            "ready": wait == 0,
            "wait_seconds": int(wait),
            "last_registration_at": last.isoformat(),
        }

    # ── overflow management ─────────────────────────────────

    async def create_overflow_registrations(
        self, website_id: int, count: int
    ) -> list[int]:
        """Create DAILY_LIMIT_REACHED registrations for overflow processing.

        These will be picked up by the next-day overflow processor.
        Overflow registrations are always re-queued at normal priority.
        """
        overflow_ids: list[int] = []
        for _ in range(count):
            reg = Registration(
                website_id=website_id,
                status=RegistrationStatus.DAILY_LIMIT_REACHED,
            )
            self.db.add(reg)
            await self.db.flush()
            overflow_ids.append(reg.id)

        await self.db.commit()
        logger.info(
            "Created %d overflow registrations for website %d",
            count, website_id,
        )
        return overflow_ids

    async def get_overflow_registrations(
        self, website_id: int | None = None, limit: int = 100
    ) -> list[Registration]:
        """Get pending overflow registrations waiting for next-day processing."""
        q = select(Registration).where(
            Registration.status == RegistrationStatus.DAILY_LIMIT_REACHED,
        ).order_by(Registration.created_at.asc()).limit(limit)

        if website_id:
            q = q.where(Registration.website_id == website_id)

        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def count_overflow(self, website_id: int | None = None) -> int:
        q = select(func.count()).select_from(Registration).where(
            Registration.status == RegistrationStatus.DAILY_LIMIT_REACHED,
        )
        if website_id:
            q = q.where(Registration.website_id == website_id)

        row = await self.db.execute(q)
        return row.scalar_one()

    # ── admin controls ──────────────────────────────────────

    async def _update_limit_no_commit(
        self, website_id: int, new_limit: int
    ) -> dict:
        """Update limit without committing — used by bulk operations."""
        website = await self._get_website(website_id)
        old_limit = website.max_registrations_per_day

        await self.db.execute(
            update(Website)
            .where(Website.id == website_id)
            .values(max_registrations_per_day=new_limit)
        )

        return {
            "website_id": website_id,
            "old_limit": old_limit,
            "new_limit": new_limit,
        }

    async def update_limit(
        self, website_id: int, new_limit: int
    ) -> dict:
        """Dynamically update the daily registration limit for a website."""
        result = await self._update_limit_no_commit(website_id, new_limit)
        await self.db.commit()

        logger.info(
            "Updated daily limit for website %d: %d → %d",
            website_id, result["old_limit"], new_limit,
        )

        return result

    async def bulk_update_limits(
        self, updates: list[dict]
    ) -> list[dict]:
        """Batch update limits for multiple websites.

        Atomic: validates all websites first, then commits all updates
        in a single transaction. If any website is not found, none are updated.

        Each entry: {"website_id": int, "limit": int}
        """
        # Validate all websites exist before making changes
        for entry in updates:
            await self._get_website(entry["website_id"])

        # All valid — apply updates in a single transaction
        results = []
        for entry in updates:
            result = await self._update_limit_no_commit(
                entry["website_id"], entry["limit"]
            )
            results.append(result)

        await self.db.commit()

        for result in results:
            logger.info(
                "Updated daily limit for website %d: %d → %d",
                result["website_id"], result["old_limit"], result["new_limit"],
            )

        return results

    async def pause_website(self, website_id: int) -> dict:
        """Pause a website to stop all registrations immediately."""
        from models.website import WebsiteStatus

        await self._get_website(website_id)
        await self.db.execute(
            update(Website)
            .where(Website.id == website_id)
            .values(status=WebsiteStatus.PAUSED)
        )
        await self.db.commit()
        logger.info("Paused website %d", website_id)
        return {"website_id": website_id, "status": "paused"}

    async def resume_website(self, website_id: int) -> dict:
        """Resume a paused website."""
        from models.website import WebsiteStatus

        await self._get_website(website_id)
        await self.db.execute(
            update(Website)
            .where(Website.id == website_id)
            .values(status=WebsiteStatus.ACTIVE)
        )
        await self.db.commit()
        logger.info("Resumed website %d", website_id)
        return {"website_id": website_id, "status": "active"}

    # ── monitoring ──────────────────────────────────────────

    async def get_all_website_stats(self) -> list[dict]:
        """Get daily limit stats for all active websites."""
        websites = await self.db.execute(
            select(Website).where(Website.deleted_at.is_(None))
        )
        stats = []
        for website in websites.scalars().all():
            record = await self.get_daily_record(website.id)
            overflow = await self.count_overflow(website.id)

            used = record.registration_count if record else 0
            success = record.success_count if record else 0
            failed = record.failure_count if record else 0
            limit = website.max_registrations_per_day
            remaining = max(0, limit - used)
            utilization = (used / limit * 100) if limit > 0 else 0

            stats.append({
                "website_id": website.id,
                "website_name": website.name,
                "status": website.status.value,
                "daily_limit": limit,
                "used_today": used,
                "remaining": remaining,
                "success": success,
                "failed": failed,
                "overflow_queued": overflow,
                "utilization_pct": round(utilization, 1),
            })

        return stats

    async def get_website_history(
        self, website_id: int, days: int = 7
    ) -> list[dict]:
        """Get daily limit usage history for a website."""
        start_date = date.today() - timedelta(days=days - 1)
        rows = await self.db.execute(
            select(DailyLimit)
            .where(
                DailyLimit.website_id == website_id,
                DailyLimit.date >= start_date,
            )
            .order_by(DailyLimit.date.desc())
        )

        website = await self._get_website(website_id)
        limit = website.max_registrations_per_day

        history = []
        for record in rows.scalars().all():
            utilization = (record.registration_count / limit * 100) if limit > 0 else 0
            history.append({
                "date": record.date.isoformat(),
                "registration_count": record.registration_count,
                "success_count": record.success_count,
                "failure_count": record.failure_count,
                "daily_limit": limit,
                "utilization_pct": round(utilization, 1),
            })

        return history

    async def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """Delete daily limit records older than N days."""
        cutoff = date.today() - timedelta(days=days_to_keep)
        result = await self.db.execute(
            delete(DailyLimit).where(DailyLimit.date < cutoff)
        )
        await self.db.commit()
        deleted = result.rowcount
        if deleted:
            logger.info("Cleaned up %d old daily limit records (before %s)", deleted, cutoff)
        return deleted

    # ── helpers ──────────────────────────────────────────────

    async def _get_website(self, website_id: int) -> Website:
        row = await self.db.execute(
            select(Website).where(Website.id == website_id)
        )
        website = row.scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")
        return website
