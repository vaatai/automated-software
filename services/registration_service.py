"""Registration orchestration service with daily limit enforcement,
overflow queuing, cooldown checks, and priority routing.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.daily_limit import DailyLimit
from models.registration import Registration, RegistrationStatus
from models.website import Website, WebsiteStatus
from services.daily_limit_service import DailyLimitService
from workers.registration_worker import (
    execute_registration,
    execute_registration_high,
    execute_registration_low,
)

logger = logging.getLogger(__name__)


class RegistrationService:
    """Orchestrates registration queuing with daily-limit enforcement."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.limit_svc = DailyLimitService(db)

    async def _daily_count(self, website_id: int) -> int:
        row = await self.db.execute(
            select(DailyLimit).where(
                DailyLimit.website_id == website_id,
                DailyLimit.date == date.today(),
            )
        )
        daily = row.scalar_one_or_none()
        return daily.registration_count if daily else 0

    async def check_daily_limit(
        self, website_id: int, requested: int = 1
    ) -> tuple[bool, int]:
        website = (
            await self.db.execute(select(Website).where(Website.id == website_id))
        ).scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")

        remaining = website.max_registrations_per_day - await self._daily_count(website_id)
        return remaining >= requested, max(0, remaining)

    async def queue_registrations(
        self,
        website_id: int,
        count: int = 1,
        custom_data: dict | None = None,
        priority: str = "normal",
        queue_overflow: bool = True,
        cooldown_seconds: int = 30,
    ) -> dict:
        """Queue registrations with limit enforcement, overflow, and cooldown.

        Args:
            website_id: Target website ID
            count: Number of registrations to queue
            priority: Task priority (high/normal/low)
            queue_overflow: If True, overflow tasks are saved for next-day processing
            cooldown_seconds: Minimum seconds between registration batches
        """
        website = (
            await self.db.execute(select(Website).where(Website.id == website_id))
        ).scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")

        # Check if website is paused
        if website.status == WebsiteStatus.PAUSED:
            return {
                "total_requested": count,
                "total_queued": 0,
                "total_rejected": count,
                "total_overflow": 0,
                "reason": "Website is paused — registrations are not accepted",
                "task_ids": [],
                "overflow_ids": [],
                "priority": priority,
            }

        # Check cooldown
        cooldown = await self.limit_svc.check_cooldown(website_id, cooldown_seconds)
        if not cooldown["ready"]:
            return {
                "total_requested": count,
                "total_queued": 0,
                "total_rejected": count,
                "total_overflow": 0,
                "reason": f"Cooldown active — wait {cooldown['wait_seconds']}s",
                "task_ids": [],
                "overflow_ids": [],
                "priority": priority,
                "cooldown_wait_seconds": cooldown["wait_seconds"],
            }

        # Check daily limit
        limit_check = await self.limit_svc.check_limit(website_id, count)
        actual = limit_check["can_queue"]
        overflow_count = limit_check["overflow_count"]

        if actual == 0 and not queue_overflow:
            return {
                "total_requested": count,
                "total_queued": 0,
                "total_rejected": count,
                "total_overflow": 0,
                "reason": "Daily registration limit reached",
                "task_ids": [],
                "overflow_ids": [],
                "priority": priority,
                "daily_limit": limit_check["limit"],
                "daily_used": limit_check["used"],
            }

        # Select task function based on priority
        task_fn = {
            "high": execute_registration_high,
            "normal": execute_registration,
            "low": execute_registration_low,
        }.get(priority, execute_registration)

        # Queue what fits within limit
        task_ids: list[str] = []
        if actual > 0:
            registrations: list[Registration] = []
            for _ in range(actual):
                reg = Registration(website_id=website_id, status=RegistrationStatus.PENDING)
                self.db.add(reg)
                await self.db.flush()
                registrations.append(reg)

            await self.db.commit()

            for reg in registrations:
                task = task_fn.delay(reg.id, website_id)
                reg.celery_task_id = task.id
                task_ids.append(task.id)

            await self.db.commit()

        # Handle overflow
        overflow_ids: list[int] = []
        if overflow_count > 0 and queue_overflow:
            overflow_ids = await self.limit_svc.create_overflow_registrations(
                website_id, overflow_count, priority
            )

        rejected = count - actual - len(overflow_ids)

        return {
            "total_requested": count,
            "total_queued": actual,
            "total_rejected": max(0, rejected),
            "total_overflow": len(overflow_ids),
            "reason": self._build_reason(actual, count, overflow_ids),
            "task_ids": task_ids,
            "overflow_ids": overflow_ids,
            "priority": priority,
            "daily_limit": limit_check["limit"],
            "daily_used": limit_check["used"],
            "daily_remaining": limit_check["remaining"],
        }

    def _build_reason(
        self, actual: int, requested: int, overflow_ids: list[int]
    ) -> str | None:
        if actual == requested:
            return None
        parts = []
        if actual < requested:
            parts.append("Daily limit partially reached")
        if overflow_ids:
            parts.append(f"{len(overflow_ids)} queued for next day")
        return " — ".join(parts) if parts else None

    async def get_registration(self, registration_id: int) -> Registration | None:
        row = await self.db.execute(
            select(Registration).where(Registration.id == registration_id)
        )
        return row.scalar_one_or_none()

    async def list_registrations(
        self,
        website_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Registration]:
        q = select(Registration).order_by(Registration.created_at.desc())
        if website_id:
            q = q.where(Registration.website_id == website_id)
        if status:
            q = q.where(Registration.status == status)
        q = q.limit(limit).offset(offset)
        return list((await self.db.execute(q)).scalars().all())

    async def get_stats(self, website_id: int) -> dict:
        website = (
            await self.db.execute(select(Website).where(Website.id == website_id))
        ).scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")

        row = await self.db.execute(
            select(DailyLimit).where(
                DailyLimit.website_id == website_id,
                DailyLimit.date == date.today(),
            )
        )
        daily = row.scalar_one_or_none()
        total = daily.registration_count if daily else 0
        success = daily.success_count if daily else 0
        failed = daily.failure_count if daily else 0

        overflow = await self.limit_svc.count_overflow(website_id)

        return {
            "website_id": website_id,
            "website_name": website.name,
            "today_total": total,
            "today_success": success,
            "today_failed": failed,
            "daily_limit": website.max_registrations_per_day,
            "remaining": max(0, website.max_registrations_per_day - total),
            "overflow_queued": overflow,
        }
