"""Task management API — status tracking, cancellation, and queue monitoring.

Endpoints:
  GET  /api/tasks/{task_id}         — detailed task status
  POST /api/tasks/{task_id}/cancel  — cancel a single task
  POST /api/tasks/cancel/website/{website_id} — cancel all for a website
  GET  /api/tasks/queue/stats       — queue health and worker metrics
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from services.task_service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ── response schemas ────────────────────────────────────────

class TaskStatusResponse(BaseModel):
    task_id: str
    celery_status: str
    result: dict | list | str | None = None
    traceback: str | None = None
    registration_id: int | None = None
    website_id: int | None = None
    registration_status: str | None = None
    retry_count: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class CancelResponse(BaseModel):
    task_id: str
    status: str
    registration_id: int | None = None
    previous_status: str | None = None
    message: str | None = None


class BulkCancelResponse(BaseModel):
    website_id: int
    cancelled_count: int


class QueueStatsResponse(BaseModel):
    registration_counts: dict
    workers: dict


# ── endpoints ───────────────────────────────────────────────

@router.get("/queue/stats", response_model=QueueStatsResponse)
async def queue_stats(db: AsyncSession = Depends(get_db)):
    """Get queue health metrics and worker status."""
    svc = TaskService(db)
    return QueueStatsResponse(**await svc.get_queue_stats())


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed status for a specific task."""
    svc = TaskService(db)
    data = await svc.get_task_status(task_id)
    return TaskStatusResponse(**data)


@router.post("/{task_id}/cancel", response_model=CancelResponse)
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a running or pending task."""
    svc = TaskService(db)
    data = await svc.cancel_task(task_id)
    return CancelResponse(**data)


@router.post("/cancel/website/{website_id}", response_model=BulkCancelResponse)
async def cancel_website_tasks(
    website_id: int, db: AsyncSession = Depends(get_db)
):
    """Cancel all pending/in-progress tasks for a website."""
    svc = TaskService(db)
    data = await svc.cancel_all_for_website(website_id)
    return BulkCancelResponse(**data)
