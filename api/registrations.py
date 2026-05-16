from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    BulkRegistrationResponse,
    RegistrationRequest,
    RegistrationResponse,
    RegistrationStats,
)
from configs.celery_app import celery_app
from configs.database import get_db
from services.registration_service import RegistrationService

router = APIRouter(prefix="/api/registrations", tags=["registrations"])


@router.post("/", response_model=BulkRegistrationResponse)
async def queue_registration(body: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    svc = RegistrationService(db)
    try:
        data = await svc.queue_registrations(
            website_id=body.website_id, count=body.count, custom_data=body.custom_data
        )
        return BulkRegistrationResponse(**data)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/", response_model=list[RegistrationResponse])
async def list_registrations(
    website_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    svc = RegistrationService(db)
    return await svc.list_registrations(
        website_id=website_id, status=status, limit=limit, offset=offset
    )


@router.get("/stats/{website_id}", response_model=RegistrationStats)
async def registration_stats(website_id: int, db: AsyncSession = Depends(get_db)):
    svc = RegistrationService(db)
    try:
        return RegistrationStats(**await svc.get_stats(website_id))
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/{registration_id}", response_model=RegistrationResponse)
async def get_registration(registration_id: int, db: AsyncSession = Depends(get_db)):
    svc = RegistrationService(db)
    reg = await svc.get_registration(registration_id)
    if not reg:
        raise HTTPException(404, "Registration not found")
    return reg


@router.get("/task/{task_id}")
async def task_status(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    return {"task_id": task_id, "status": res.status, "result": res.result if res.ready() else None}
