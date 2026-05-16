import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.daily_limit import DailyLimit
from models.registration import Registration, RegistrationStatus
from models.website import Website
from workers.registration_worker import execute_registration

logger = logging.getLogger(__name__)


class RegistrationService:
    """Orchestrates registration queuing and daily-limit enforcement."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
        self, website_id: int, count: int = 1, custom_data: dict | None = None
    ) -> dict:
        website = (
            await self.db.execute(select(Website).where(Website.id == website_id))
        ).scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")

        _, remaining = await self.check_daily_limit(website_id, count)
        actual = min(count, remaining)

        if actual == 0:
            return {
                "total_requested": count,
                "total_queued": 0,
                "total_rejected": count,
                "reason": "Daily registration limit reached",
                "task_ids": [],
            }

        task_ids: list[str] = []
        for _ in range(actual):
            reg = Registration(website_id=website_id, status=RegistrationStatus.PENDING)
            self.db.add(reg)
            await self.db.flush()

            task = execute_registration.delay(reg.id, website_id)
            reg.celery_task_id = task.id
            task_ids.append(task.id)

        await self.db.commit()
        return {
            "total_requested": count,
            "total_queued": actual,
            "total_rejected": count - actual,
            "reason": "Partially limited" if count > actual else None,
            "task_ids": task_ids,
        }

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

        return {
            "website_id": website_id,
            "website_name": website.name,
            "today_total": total,
            "today_success": success,
            "today_failed": failed,
            "daily_limit": website.max_registrations_per_day,
            "remaining": max(0, website.max_registrations_per_day - total),
        }
