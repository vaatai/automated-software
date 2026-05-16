"""Dashboard service — registration stats, success metrics, OTP status,
daily usage, error logs, and metrics aggregation.

Provides all data needed for the monitoring dashboard with pagination,
filtering, search, and time-series aggregation.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, cast, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.daily_limit import DailyLimit
from models.proxy import Proxy, ProxyStatus
from models.registration import Registration, RegistrationStatus
from models.task_log import LogLevel, TaskLog
from models.website import Website, WebsiteStatus

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── overview stats ──────────────────────────────────────

    async def get_overview(self) -> dict:
        """Aggregate overview: total/active/failed/pending registrations,
        success rate, active websites, active proxies.
        """
        total = await self._count_registrations()
        completed = await self._count_registrations(RegistrationStatus.COMPLETED)
        failed = await self._count_registrations(RegistrationStatus.FAILED)
        in_progress = await self._count_registrations(RegistrationStatus.IN_PROGRESS)
        pending = await self._count_registrations(RegistrationStatus.PENDING)
        cancelled = await self._count_registrations(RegistrationStatus.CANCELLED)
        daily_limit_reached = await self._count_registrations(
            RegistrationStatus.DAILY_LIMIT_REACHED
        )

        success_rate = (completed / total * 100) if total > 0 else 0

        active_websites = (await self.db.execute(
            select(func.count(Website.id)).where(
                Website.status == WebsiteStatus.ACTIVE,
                Website.deleted_at.is_(None),
            )
        )).scalar() or 0

        active_proxies = (await self.db.execute(
            select(func.count(Proxy.id)).where(
                Proxy.status == ProxyStatus.ACTIVE,
                Proxy.deleted_at.is_(None),
            )
        )).scalar() or 0

        return {
            "total_registrations": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "cancelled": cancelled,
            "daily_limit_reached": daily_limit_reached,
            "success_rate_pct": round(success_rate, 1),
            "active_websites": active_websites,
            "active_proxies": active_proxies,
        }

    # ── active registrations ────────────────────────────────

    async def get_active_registrations(
        self,
        website_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List registrations currently in progress or pending."""
        q = select(Registration).where(
            Registration.status.in_([
                RegistrationStatus.PENDING,
                RegistrationStatus.IN_PROGRESS,
                RegistrationStatus.EMAIL_OTP_PENDING,
                RegistrationStatus.MOBILE_OTP_PENDING,
            ]),
            Registration.deleted_at.is_(None),
        )
        count_q = select(func.count(Registration.id)).where(
            Registration.status.in_([
                RegistrationStatus.PENDING,
                RegistrationStatus.IN_PROGRESS,
                RegistrationStatus.EMAIL_OTP_PENDING,
                RegistrationStatus.MOBILE_OTP_PENDING,
            ]),
            Registration.deleted_at.is_(None),
        )

        if website_id:
            q = q.where(Registration.website_id == website_id)
            count_q = count_q.where(Registration.website_id == website_id)

        total = (await self.db.execute(count_q)).scalar() or 0
        rows = await self.db.execute(
            q.order_by(Registration.created_at.desc())
            .limit(limit).offset(offset)
        )

        return {
            "total": total,
            "items": [self._reg_to_dict(r) for r in rows.scalars().all()],
        }

    # ── failed registrations ────────────────────────────────

    async def get_failed_registrations(
        self,
        website_id: int | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List failed registrations with optional search on error message."""
        filters = [
            Registration.status == RegistrationStatus.FAILED,
            Registration.deleted_at.is_(None),
        ]
        if website_id:
            filters.append(Registration.website_id == website_id)
        if search:
            filters.append(
                Registration.error_message.ilike(f"%{search}%")
            )

        count_q = select(func.count(Registration.id)).where(*filters)
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(Registration)
            .where(*filters)
            .order_by(Registration.created_at.desc())
            .limit(limit).offset(offset)
        )
        rows = await self.db.execute(q)

        return {
            "total": total,
            "items": [self._reg_to_dict(r) for r in rows.scalars().all()],
        }

    # ── success metrics ─────────────────────────────────────

    async def get_success_metrics(
        self,
        website_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Success/failure rates over time, grouped by day."""
        start_date = date.today() - timedelta(days=days)

        filters = [DailyLimit.date >= start_date]
        if website_id:
            filters.append(DailyLimit.website_id == website_id)

        rows = await self.db.execute(
            select(
                DailyLimit.date,
                func.sum(DailyLimit.registration_count).label("total"),
                func.sum(DailyLimit.success_count).label("success"),
                func.sum(DailyLimit.failure_count).label("failure"),
            )
            .where(*filters)
            .group_by(DailyLimit.date)
            .order_by(DailyLimit.date.asc())
        )

        daily_data = []
        total_success = 0
        total_failure = 0
        for row in rows.all():
            t = row.total or 0
            s = row.success or 0
            f = row.failure or 0
            total_success += s
            total_failure += f
            rate = (s / t * 100) if t > 0 else 0
            daily_data.append({
                "date": row.date.isoformat(),
                "total": t,
                "success": s,
                "failure": f,
                "success_rate_pct": round(rate, 1),
            })

        grand_total = total_success + total_failure
        overall_rate = (total_success / grand_total * 100) if grand_total > 0 else 0

        return {
            "period_days": days,
            "overall_success_rate_pct": round(overall_rate, 1),
            "total_success": total_success,
            "total_failure": total_failure,
            "daily": daily_data,
        }

    # ── OTP status ──────────────────────────────────────────

    async def get_otp_status(
        self,
        website_id: int | None = None,
    ) -> dict:
        """OTP verification stats: email/mobile verified counts, pending counts."""
        filters = [Registration.deleted_at.is_(None)]
        if website_id:
            filters.append(Registration.website_id == website_id)

        total = (await self.db.execute(
            select(func.count(Registration.id)).where(*filters)
        )).scalar() or 0

        email_verified = (await self.db.execute(
            select(func.count(Registration.id)).where(
                *filters, Registration.email_otp_verified.is_(True)
            )
        )).scalar() or 0

        mobile_verified = (await self.db.execute(
            select(func.count(Registration.id)).where(
                *filters, Registration.mobile_otp_verified.is_(True)
            )
        )).scalar() or 0

        email_pending = (await self.db.execute(
            select(func.count(Registration.id)).where(
                *filters,
                Registration.status == RegistrationStatus.EMAIL_OTP_PENDING,
            )
        )).scalar() or 0

        mobile_pending = (await self.db.execute(
            select(func.count(Registration.id)).where(
                *filters,
                Registration.status == RegistrationStatus.MOBILE_OTP_PENDING,
            )
        )).scalar() or 0

        return {
            "total_registrations": total,
            "email_otp_verified": email_verified,
            "mobile_otp_verified": mobile_verified,
            "email_otp_pending": email_pending,
            "mobile_otp_pending": mobile_pending,
            "email_verification_rate_pct": round(
                (email_verified / total * 100) if total > 0 else 0, 1
            ),
            "mobile_verification_rate_pct": round(
                (mobile_verified / total * 100) if total > 0 else 0, 1
            ),
        }

    # ── daily usage ─────────────────────────────────────────

    async def get_daily_usage(
        self,
        website_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Daily registration usage with limit utilization per website."""
        start_date = date.today() - timedelta(days=days)

        q = (
            select(
                DailyLimit.date,
                DailyLimit.website_id,
                Website.name.label("website_name"),
                Website.max_registrations_per_day.label("daily_limit"),
                DailyLimit.registration_count,
                DailyLimit.success_count,
                DailyLimit.failure_count,
            )
            .join(Website, DailyLimit.website_id == Website.id)
            .where(DailyLimit.date >= start_date)
            .order_by(DailyLimit.date.desc(), DailyLimit.website_id.asc())
        )

        if website_id:
            q = q.where(DailyLimit.website_id == website_id)

        rows = await self.db.execute(q)

        items = []
        for row in rows.all():
            limit_val = row.daily_limit or 100
            utilization = (row.registration_count / limit_val * 100) if limit_val > 0 else 0
            items.append({
                "date": row.date.isoformat(),
                "website_id": row.website_id,
                "website_name": row.website_name,
                "daily_limit": limit_val,
                "registration_count": row.registration_count,
                "success_count": row.success_count,
                "failure_count": row.failure_count,
                "utilization_pct": round(utilization, 1),
            })

        return {"period_days": days, "items": items}

    # ── error logs ──────────────────────────────────────────

    async def get_error_logs(
        self,
        registration_id: int | None = None,
        website_id: int | None = None,
        level: str | None = None,
        step: str | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Paginated, filterable error/task logs with search."""
        filters: list = []

        if registration_id:
            filters.append(TaskLog.registration_id == registration_id)
        if level:
            try:
                filters.append(TaskLog.level == LogLevel(level))
            except ValueError:
                return {"total": 0, "items": []}
        if step:
            filters.append(TaskLog.step == step)
        if search:
            filters.append(
                or_(
                    TaskLog.message.ilike(f"%{search}%"),
                    TaskLog.details.ilike(f"%{search}%"),
                )
            )
        if date_from:
            filters.append(TaskLog.created_at >= datetime(
                date_from.year, date_from.month, date_from.day,
                tzinfo=timezone.utc,
            ))
        if date_to:
            next_day = date_to + timedelta(days=1)
            filters.append(TaskLog.created_at < datetime(
                next_day.year, next_day.month, next_day.day,
                tzinfo=timezone.utc,
            ))

        # If filtering by website_id, join through Registration
        if website_id:
            filters.append(TaskLog.registration_id.isnot(None))
            base_q = (
                select(TaskLog)
                .join(Registration, TaskLog.registration_id == Registration.id)
                .where(Registration.website_id == website_id, *filters)
            )
            count_q = (
                select(func.count(TaskLog.id))
                .join(Registration, TaskLog.registration_id == Registration.id)
                .where(Registration.website_id == website_id, *filters)
            )
        else:
            base_q = select(TaskLog).where(*filters) if filters else select(TaskLog)
            count_q = (
                select(func.count(TaskLog.id)).where(*filters)
                if filters
                else select(func.count(TaskLog.id))
            )

        total = (await self.db.execute(count_q)).scalar() or 0
        rows = await self.db.execute(
            base_q.order_by(TaskLog.created_at.desc())
            .limit(limit).offset(offset)
        )

        return {
            "total": total,
            "items": [self._log_to_dict(log) for log in rows.scalars().all()],
        }

    # ── per-registration logs ───────────────────────────────

    async def get_registration_timeline(self, registration_id: int) -> dict:
        """Full event timeline for a single registration."""
        reg = (await self.db.execute(
            select(Registration).where(Registration.id == registration_id)
        )).scalar_one_or_none()

        if not reg:
            raise ValueError(f"Registration {registration_id} not found")

        logs = await self.db.execute(
            select(TaskLog)
            .where(TaskLog.registration_id == registration_id)
            .order_by(TaskLog.created_at.asc())
        )

        return {
            "registration": self._reg_to_dict(reg),
            "timeline": [self._log_to_dict(log) for log in logs.scalars().all()],
        }

    # ── screenshot retrieval ────────────────────────────────

    async def get_screenshot_path(self, registration_id: int) -> str | None:
        """Get the screenshot file path for a registration."""
        reg = (await self.db.execute(
            select(Registration).where(Registration.id == registration_id)
        )).scalar_one_or_none()

        if not reg:
            raise ValueError(f"Registration {registration_id} not found")

        return reg.screenshot_path

    async def list_screenshots(
        self,
        website_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List registrations that have screenshots."""
        filters = [
            Registration.screenshot_path.isnot(None),
            Registration.deleted_at.is_(None),
        ]
        if website_id:
            filters.append(Registration.website_id == website_id)

        count_q = select(func.count(Registration.id)).where(*filters)
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(Registration)
            .where(*filters)
            .order_by(Registration.created_at.desc())
            .limit(limit).offset(offset)
        )
        rows = await self.db.execute(q)

        items = []
        for reg in rows.scalars().all():
            items.append({
                "registration_id": reg.id,
                "website_id": reg.website_id,
                "status": reg.status.value,
                "screenshot_path": reg.screenshot_path,
                "error_message": reg.error_message,
                "created_at": reg.created_at.isoformat() if reg.created_at else None,
            })

        return {"total": total, "items": items}

    # ── metrics aggregation ─────────────────────────────────

    async def get_hourly_metrics(
        self,
        website_id: int | None = None,
        hours: int = 24,
    ) -> list[dict]:
        """Registration counts aggregated by hour."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        filters = [
            Registration.created_at >= cutoff,
            Registration.deleted_at.is_(None),
        ]
        if website_id:
            filters.append(Registration.website_id == website_id)

        rows = await self.db.execute(
            select(
                extract("hour", Registration.created_at).label("hour"),
                cast(Registration.created_at, Date).label("day"),
                func.count(Registration.id).label("total"),
                func.count(Registration.id).filter(
                    Registration.status == RegistrationStatus.COMPLETED
                ).label("success"),
                func.count(Registration.id).filter(
                    Registration.status == RegistrationStatus.FAILED
                ).label("failure"),
            )
            .where(*filters)
            .group_by("day", "hour")
            .order_by("day", "hour")
        )

        return [
            {
                "date": row.day.isoformat() if row.day else None,
                "hour": int(row.hour) if row.hour is not None else None,
                "total": row.total,
                "success": row.success,
                "failure": row.failure,
            }
            for row in rows.all()
        ]

    async def get_weekly_metrics(
        self,
        website_id: int | None = None,
        weeks: int = 12,
    ) -> list[dict]:
        """Registration counts aggregated by week."""
        cutoff = date.today() - timedelta(weeks=weeks)

        filters = [DailyLimit.date >= cutoff]
        if website_id:
            filters.append(DailyLimit.website_id == website_id)

        rows = await self.db.execute(
            select(
                extract("isoyear", DailyLimit.date).label("year"),
                extract("week", DailyLimit.date).label("week"),
                func.sum(DailyLimit.registration_count).label("total"),
                func.sum(DailyLimit.success_count).label("success"),
                func.sum(DailyLimit.failure_count).label("failure"),
            )
            .where(*filters)
            .group_by("year", "week")
            .order_by("year", "week")
        )

        return [
            {
                "year": int(row.year),
                "week": int(row.week),
                "total": row.total or 0,
                "success": row.success or 0,
                "failure": row.failure or 0,
            }
            for row in rows.all()
        ]

    async def get_website_rankings(self, days: int = 7) -> list[dict]:
        """Rank websites by registration volume and success rate."""
        start_date = date.today() - timedelta(days=days)

        rows = await self.db.execute(
            select(
                DailyLimit.website_id,
                Website.name.label("website_name"),
                func.sum(DailyLimit.registration_count).label("total"),
                func.sum(DailyLimit.success_count).label("success"),
                func.sum(DailyLimit.failure_count).label("failure"),
            )
            .join(Website, DailyLimit.website_id == Website.id)
            .where(DailyLimit.date >= start_date)
            .group_by(DailyLimit.website_id, Website.name)
            .order_by(func.sum(DailyLimit.registration_count).desc())
        )

        rankings = []
        for row in rows.all():
            t = row.total or 0
            s = row.success or 0
            rate = (s / t * 100) if t > 0 else 0
            rankings.append({
                "website_id": row.website_id,
                "website_name": row.website_name,
                "total": t,
                "success": s,
                "failure": row.failure or 0,
                "success_rate_pct": round(rate, 1),
            })

        return rankings

    # ── worker status ───────────────────────────────────────

    async def get_worker_status(self) -> dict:
        """Get Celery worker and queue status via Celery inspect.

        Celery inspect calls are synchronous RPC — run them in a thread
        to avoid blocking the async event loop.
        """
        from configs.celery_app import celery_app

        def _inspect() -> tuple[dict, dict, dict]:
            i = celery_app.control.inspect(timeout=3)
            return i.active() or {}, i.reserved() or {}, i.stats() or {}

        active, reserved, stats = await asyncio.to_thread(_inspect)

        workers = []
        for worker_name, worker_stats in stats.items():
            active_tasks = active.get(worker_name, [])
            reserved_tasks = reserved.get(worker_name, [])
            pool_info = worker_stats.get("pool", {})

            workers.append({
                "name": worker_name,
                "active_tasks": len(active_tasks),
                "reserved_tasks": len(reserved_tasks),
                "total_completed": worker_stats.get("total", {}).get(
                    "workers.registration_worker.execute_registration", 0
                ),
                "pool_processes": pool_info.get("max-concurrency"),
                "uptime": worker_stats.get("uptime"),
                "active_task_details": [
                    {
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "args": t.get("args"),
                        "time_start": t.get("time_start"),
                    }
                    for t in active_tasks
                ],
            })

        return {
            "worker_count": len(stats),
            "workers": workers,
        }

    async def get_queue_depths(self) -> dict:
        """Get current queue sizes via async Redis."""
        from configs.redis import redis_client

        queues = [
            "registrations.high",
            "registrations",
            "registrations.low",
            "dead_letter",
            "monitoring",
        ]

        depths = {}
        for q_name in queues:
            depths[q_name] = await redis_client.llen(q_name) or 0

        return depths

    # ── helpers ──────────────────────────────────────────────

    async def _count_registrations(
        self, status: RegistrationStatus | None = None
    ) -> int:
        q = select(func.count(Registration.id)).where(
            Registration.deleted_at.is_(None)
        )
        if status:
            q = q.where(Registration.status == status)
        return (await self.db.execute(q)).scalar() or 0

    def _reg_to_dict(self, reg: Registration) -> dict:
        return {
            "id": reg.id,
            "website_id": reg.website_id,
            "status": reg.status.value,
            "username": reg.username,
            "email_used": reg.email_used,
            "phone_used": reg.phone_used,
            "email_otp_verified": reg.email_otp_verified,
            "mobile_otp_verified": reg.mobile_otp_verified,
            "celery_task_id": reg.celery_task_id,
            "retry_count": reg.retry_count,
            "error_message": reg.error_message,
            "screenshot_path": reg.screenshot_path,
            "proxy_id": reg.proxy_id,
            "created_at": reg.created_at.isoformat() if reg.created_at else None,
            "started_at": reg.started_at.isoformat() if reg.started_at else None,
            "completed_at": reg.completed_at.isoformat() if reg.completed_at else None,
        }

    def _log_to_dict(self, log: TaskLog) -> dict:
        return {
            "id": log.id,
            "registration_id": log.registration_id,
            "celery_task_id": log.celery_task_id,
            "level": log.level.value,
            "step": log.step,
            "message": log.message,
            "details": log.details,
            "screenshot_path": log.screenshot_path,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
