"""Monitoring & dashboard API — production-ready endpoints for registration stats,
success metrics, OTP status, worker/queue monitoring, error logs, daily usage,
metrics aggregation, and screenshot retrieval.

All list endpoints support pagination (limit/offset) and filtering.

Endpoints:
  GET  /api/monitoring/overview           — aggregate dashboard stats
  GET  /api/monitoring/active             — active/pending registrations
  GET  /api/monitoring/failed             — failed registrations (searchable)
  GET  /api/monitoring/success-metrics    — success/failure rates over time
  GET  /api/monitoring/otp-status         — OTP verification stats
  GET  /api/monitoring/daily-usage        — daily registration usage + utilization
  GET  /api/monitoring/workers            — Celery worker status
  GET  /api/monitoring/queues             — queue depths
  GET  /api/monitoring/logs               — paginated, filterable task/error logs
  GET  /api/monitoring/registrations/{id}/timeline — event timeline for one registration
  GET  /api/monitoring/screenshots        — list registrations with screenshots
  GET  /api/monitoring/screenshots/{id}   — get screenshot path for a registration
  GET  /api/monitoring/metrics/hourly     — hourly metrics aggregation
  GET  /api/monitoring/metrics/weekly     — weekly metrics aggregation
  GET  /api/monitoring/metrics/rankings   — website rankings by volume/success
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ── response schemas ────────────────────────────────────────

class OverviewResponse(BaseModel):
    total_registrations: int
    completed: int
    failed: int
    in_progress: int
    pending: int
    cancelled: int
    daily_limit_reached: int
    success_rate_pct: float
    active_websites: int
    active_proxies: int


class PaginatedRegistrations(BaseModel):
    total: int
    items: list[dict]


class SuccessMetricsResponse(BaseModel):
    period_days: int
    overall_success_rate_pct: float
    total_success: int
    total_failure: int
    daily: list[dict]


class OTPStatusResponse(BaseModel):
    total_registrations: int
    email_otp_verified: int
    mobile_otp_verified: int
    email_otp_pending: int
    mobile_otp_pending: int
    email_verification_rate_pct: float
    mobile_verification_rate_pct: float


class DailyUsageResponse(BaseModel):
    period_days: int
    items: list[dict]


class WorkerStatusResponse(BaseModel):
    worker_count: int
    workers: list[dict]


class RegistrationTimelineResponse(BaseModel):
    registration: dict
    timeline: list[dict]


class ScreenshotListResponse(BaseModel):
    total: int
    items: list[dict]


class ScreenshotPathResponse(BaseModel):
    registration_id: int
    screenshot_path: str | None


# ── endpoints ───────────────────────────────────────────────

@router.get("/overview", response_model=OverviewResponse)
async def overview(db: AsyncSession = Depends(get_db)):
    """Aggregate dashboard overview: counts, success rate, active resources."""
    svc = DashboardService(db)
    return OverviewResponse(**await svc.get_overview())


@router.get("/active", response_model=PaginatedRegistrations)
async def active_registrations(
    website_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List currently active (in-progress/pending) registrations."""
    svc = DashboardService(db)
    return PaginatedRegistrations(
        **await svc.get_active_registrations(website_id, limit, offset)
    )


@router.get("/failed", response_model=PaginatedRegistrations)
async def failed_registrations(
    website_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List failed registrations. Search on error_message."""
    svc = DashboardService(db)
    return PaginatedRegistrations(
        **await svc.get_failed_registrations(website_id, search, limit, offset)
    )


@router.get("/success-metrics", response_model=SuccessMetricsResponse)
async def success_metrics(
    website_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Success/failure metrics with daily breakdown."""
    svc = DashboardService(db)
    return SuccessMetricsResponse(
        **await svc.get_success_metrics(website_id, days)
    )


@router.get("/otp-status", response_model=OTPStatusResponse)
async def otp_status(
    website_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """OTP verification stats: verified/pending counts and rates."""
    svc = DashboardService(db)
    return OTPStatusResponse(**await svc.get_otp_status(website_id))


@router.get("/daily-usage", response_model=DailyUsageResponse)
async def daily_usage(
    website_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Daily registration usage with limit utilization per website."""
    svc = DashboardService(db)
    return DailyUsageResponse(**await svc.get_daily_usage(website_id, days))


@router.get("/workers", response_model=WorkerStatusResponse)
async def worker_status(db: AsyncSession = Depends(get_db)):
    """Celery worker status: active tasks, pool info, uptime."""
    svc = DashboardService(db)
    return WorkerStatusResponse(**await svc.get_worker_status())


@router.get("/queues")
async def queue_depths(db: AsyncSession = Depends(get_db)):
    """Current queue sizes (registrations.high, registrations, registrations.low, dead_letter, monitoring)."""
    svc = DashboardService(db)
    return await svc.get_queue_depths()


@router.get("/logs", response_model=PaginatedRegistrations)
async def error_logs(
    registration_id: int | None = Query(default=None),
    website_id: int | None = Query(default=None),
    level: str | None = Query(default=None),
    step: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated task/error logs with filtering and search."""
    svc = DashboardService(db)
    return PaginatedRegistrations(
        **await svc.get_error_logs(
            registration_id=registration_id,
            website_id=website_id,
            level=level,
            step=step,
            search=search,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/registrations/{registration_id}/timeline",
    response_model=RegistrationTimelineResponse,
)
async def registration_timeline(
    registration_id: int, db: AsyncSession = Depends(get_db)
):
    """Full event timeline for a single registration."""
    svc = DashboardService(db)
    try:
        return RegistrationTimelineResponse(
            **await svc.get_registration_timeline(registration_id)
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/screenshots", response_model=ScreenshotListResponse)
async def list_screenshots(
    website_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List registrations that have failure screenshots."""
    svc = DashboardService(db)
    return ScreenshotListResponse(
        **await svc.list_screenshots(website_id, limit, offset)
    )


@router.get("/screenshots/{registration_id}")
async def get_screenshot(
    registration_id: int, db: AsyncSession = Depends(get_db)
):
    """Get screenshot for a specific registration. Returns file if exists."""
    svc = DashboardService(db)
    try:
        path = await svc.get_screenshot_path(registration_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

    if not path:
        raise HTTPException(404, "No screenshot available for this registration")

    import os
    if not os.path.exists(path):
        return ScreenshotPathResponse(
            registration_id=registration_id,
            screenshot_path=path,
        )

    return FileResponse(path, media_type="image/png")


@router.get("/metrics/hourly")
async def hourly_metrics(
    website_id: int | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Registration counts aggregated by hour."""
    svc = DashboardService(db)
    return await svc.get_hourly_metrics(website_id, hours)


@router.get("/metrics/weekly")
async def weekly_metrics(
    website_id: int | None = Query(default=None),
    weeks: int = Query(default=12, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
):
    """Registration counts aggregated by week."""
    svc = DashboardService(db)
    return await svc.get_weekly_metrics(website_id, weeks)


@router.get("/metrics/rankings")
async def website_rankings(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Rank websites by registration volume and success rate."""
    svc = DashboardService(db)
    return await svc.get_website_rankings(days)
