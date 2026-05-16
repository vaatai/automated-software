"""Daily limit management API — admin controls, monitoring, and overflow inspection.

Endpoints:
  GET  /api/limits/stats                — all website daily limit stats
  GET  /api/limits/{website_id}         — single website limit status
  GET  /api/limits/{website_id}/history — usage history (last N days)
  PUT  /api/limits/{website_id}         — update daily limit
  POST /api/limits/bulk-update          — batch update limits
  POST /api/limits/{website_id}/pause   — pause website registrations
  POST /api/limits/{website_id}/resume  — resume website registrations
  GET  /api/limits/overflow             — list overflow registrations
  GET  /api/limits/overflow/count       — count overflow registrations
  POST /api/limits/cleanup              — delete old daily limit records
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from services.daily_limit_service import DailyLimitService

router = APIRouter(prefix="/api/limits", tags=["daily-limits"])


# ── request/response schemas ────────────────────────────────

class LimitUpdateRequest(BaseModel):
    max_registrations_per_day: int = Field(..., ge=1, le=100000)


class BulkLimitEntry(BaseModel):
    website_id: int
    limit: int = Field(..., ge=1, le=100000)


class BulkLimitUpdateRequest(BaseModel):
    updates: list[BulkLimitEntry]


class LimitUpdateResponse(BaseModel):
    website_id: int
    old_limit: int
    new_limit: int


class WebsiteLimitStats(BaseModel):
    website_id: int
    website_name: str
    status: str
    daily_limit: int
    used_today: int
    remaining: int
    success: int
    failed: int
    overflow_queued: int
    utilization_pct: float


class DailyHistoryEntry(BaseModel):
    date: str
    registration_count: int
    success_count: int
    failure_count: int
    daily_limit: int
    utilization_pct: float


class LimitCheckResponse(BaseModel):
    allowed: bool
    can_queue: int
    remaining: int
    limit: int
    used: int
    overflow_count: int


class WebsiteStatusResponse(BaseModel):
    website_id: int
    status: str


class OverflowCountResponse(BaseModel):
    total: int
    website_id: int | None = None


class CleanupResponse(BaseModel):
    deleted_count: int
    days_kept: int


# ── endpoints ───────────────────────────────────────────────

@router.get("/stats", response_model=list[WebsiteLimitStats])
async def all_website_stats(db: AsyncSession = Depends(get_db)):
    """Get daily limit stats for all active websites."""
    svc = DailyLimitService(db)
    return [WebsiteLimitStats(**s) for s in await svc.get_all_website_stats()]


@router.get("/overflow/count", response_model=OverflowCountResponse)
async def overflow_count(
    website_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Count overflow registrations waiting for next-day processing."""
    svc = DailyLimitService(db)
    total = await svc.count_overflow(website_id)
    return OverflowCountResponse(total=total, website_id=website_id)


@router.get("/{website_id}", response_model=LimitCheckResponse)
async def check_website_limit(
    website_id: int,
    requested: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Check current daily limit status for a website."""
    svc = DailyLimitService(db)
    try:
        return LimitCheckResponse(**await svc.check_limit(website_id, requested))
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/{website_id}/history", response_model=list[DailyHistoryEntry])
async def website_history(
    website_id: int,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get daily limit usage history for a website."""
    svc = DailyLimitService(db)
    try:
        return [
            DailyHistoryEntry(**h)
            for h in await svc.get_website_history(website_id, days)
        ]
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.put("/{website_id}", response_model=LimitUpdateResponse)
async def update_limit(
    website_id: int,
    body: LimitUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update the daily registration limit for a website."""
    svc = DailyLimitService(db)
    try:
        data = await svc.update_limit(website_id, body.max_registrations_per_day)
        return LimitUpdateResponse(**data)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/bulk-update", response_model=list[LimitUpdateResponse])
async def bulk_update_limits(
    body: BulkLimitUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Batch update daily limits for multiple websites."""
    svc = DailyLimitService(db)
    entries = [{"website_id": e.website_id, "limit": e.limit} for e in body.updates]
    try:
        results = await svc.bulk_update_limits(entries)
        return [LimitUpdateResponse(**r) for r in results]
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/{website_id}/pause", response_model=WebsiteStatusResponse)
async def pause_website(
    website_id: int, db: AsyncSession = Depends(get_db)
):
    """Pause a website to stop all registrations immediately."""
    svc = DailyLimitService(db)
    try:
        data = await svc.pause_website(website_id)
        return WebsiteStatusResponse(**data)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/{website_id}/resume", response_model=WebsiteStatusResponse)
async def resume_website(
    website_id: int, db: AsyncSession = Depends(get_db)
):
    """Resume a paused website."""
    svc = DailyLimitService(db)
    try:
        data = await svc.resume_website(website_id)
        return WebsiteStatusResponse(**data)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_records(
    days_to_keep: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Delete daily limit records older than N days."""
    svc = DailyLimitService(db)
    deleted = await svc.cleanup_old_records(days_to_keep)
    return CleanupResponse(deleted_count=deleted, days_kept=days_to_keep)
