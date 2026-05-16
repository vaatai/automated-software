"""Task management service — cancellation, status tracking, and queue inspection.

Provides async-safe operations for managing Celery tasks from the FastAPI layer.
"""

import logging
from datetime import datetime, timezone

from celery.result import AsyncResult
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from configs.celery_app import celery_app
from models.registration import Registration, RegistrationStatus
from models.task_log import LogLevel, TaskLog

logger = logging.getLogger(__name__)


class TaskService:
    """Manages Celery task lifecycle from the API layer."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_task_status(self, task_id: str) -> dict:
        """Get detailed status for a Celery task."""
        result = AsyncResult(task_id, app=celery_app)

        # Also load DB record for richer context
        row = await self.db.execute(
            select(Registration).where(Registration.celery_task_id == task_id)
        )
        reg = row.scalar_one_or_none()

        response: dict = {
            "task_id": task_id,
            "celery_status": result.status,
            "result": result.result if result.ready() else None,
            "traceback": str(result.traceback) if result.failed() else None,
        }

        if reg:
            response.update({
                "registration_id": reg.id,
                "website_id": reg.website_id,
                "registration_status": reg.status.value,
                "retry_count": reg.retry_count,
                "started_at": reg.started_at.isoformat() if reg.started_at else None,
                "completed_at": reg.completed_at.isoformat() if reg.completed_at else None,
                "error_message": reg.error_message,
            })

        return response

    async def cancel_task(self, task_id: str) -> dict:
        """Cancel a running or pending Celery task.

        - Revokes the task in Celery (terminates if running).
        - Updates the registration status to CANCELLED.
        - Logs the cancellation event.
        """
        result = AsyncResult(task_id, app=celery_app)

        # Revoke the task (terminate=True sends SIGTERM to running worker)
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")

        # Update DB
        row = await self.db.execute(
            select(Registration).where(Registration.celery_task_id == task_id)
        )
        reg = row.scalar_one_or_none()

        if not reg:
            return {
                "task_id": task_id,
                "status": "revoked",
                "registration_id": None,
                "message": "Task revoked but no registration found",
            }

        await self.db.execute(
            update(Registration)
            .where(Registration.id == reg.id)
            .values(
                status=RegistrationStatus.CANCELLED,
                error_message="Cancelled by user",
                completed_at=datetime.now(timezone.utc),
            )
        )

        self.db.add(
            TaskLog(
                registration_id=reg.id,
                celery_task_id=task_id,
                level=LogLevel.WARNING,
                step="task_cancelled",
                message="Task cancelled by user",
            )
        )
        await self.db.commit()

        logger.info("Task %s cancelled (registration %d)", task_id, reg.id)

        return {
            "task_id": task_id,
            "status": "cancelled",
            "registration_id": reg.id,
            "previous_status": result.status,
        }

    async def cancel_all_for_website(self, website_id: int) -> dict:
        """Cancel all pending/in-progress tasks for a website."""
        rows = await self.db.execute(
            select(Registration).where(
                Registration.website_id == website_id,
                Registration.status.in_([
                    RegistrationStatus.PENDING,
                    RegistrationStatus.IN_PROGRESS,
                ]),
            )
        )
        regs = rows.scalars().all()

        cancelled = 0
        for reg in regs:
            if reg.celery_task_id:
                celery_app.control.revoke(
                    reg.celery_task_id, terminate=True, signal="SIGTERM"
                )

            await self.db.execute(
                update(Registration)
                .where(Registration.id == reg.id)
                .values(
                    status=RegistrationStatus.CANCELLED,
                    error_message="Bulk cancellation",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            self.db.add(
                TaskLog(
                    registration_id=reg.id,
                    celery_task_id=reg.celery_task_id,
                    level=LogLevel.WARNING,
                    step="task_cancelled",
                    message="Bulk cancellation for website",
                )
            )
            cancelled += 1

        await self.db.commit()
        logger.info("Cancelled %d tasks for website %d", cancelled, website_id)

        return {
            "website_id": website_id,
            "cancelled_count": cancelled,
        }

    async def get_queue_stats(self) -> dict:
        """Get current queue statistics from the database."""
        rows = await self.db.execute(
            select(Registration.status, func.count())
            .group_by(Registration.status)
        )
        counts = {
            k.value if hasattr(k, "value") else k: v
            for k, v in rows.all()
        }

        # Active Celery worker info
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        scheduled = inspector.scheduled() or {}

        active_count = sum(len(tasks) for tasks in active.values())
        reserved_count = sum(len(tasks) for tasks in reserved.values())
        scheduled_count = sum(len(tasks) for tasks in scheduled.values())

        return {
            "registration_counts": counts,
            "workers": {
                "active_tasks": active_count,
                "reserved_tasks": reserved_count,
                "scheduled_tasks": scheduled_count,
                "worker_count": len(active),
            },
        }
