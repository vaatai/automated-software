from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    BulkRegistrationResponse,
    RegistrationRequest,
    RegistrationResponse,
    RegistrationStats,
)
from configs.database import get_db
from services.registration_service import RegistrationService

router = APIRouter(prefix="/api/registrations", tags=["registrations"])


@router.post("/", response_model=BulkRegistrationResponse)
async def queue_registration(body: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    svc = RegistrationService(db)
    try:
        data = await svc.queue_registrations(
            website_id=body.website_id,
            count=body.count,
            custom_data=body.custom_data,
            priority=body.priority.value,
            queue_overflow=body.queue_overflow,
            cooldown_seconds=body.cooldown_seconds,
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
