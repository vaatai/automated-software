"""API endpoints for managing 24hr phone number rentals."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from otp.sms_provider import NumberUnavailableError
from services.rental_service import RentalService

router = APIRouter(prefix="/api/rentals", tags=["rentals"])


# ── Schemas ────────────────────────────────────────────────

class RentNumberRequest(BaseModel):
    country: str = Field(default="US", min_length=2, max_length=5)
    label: str | None = Field(default=None, max_length=255)
    duration_hours: float = Field(default=24, gt=0, le=720)
    preferred_provider: str | None = Field(
        default=None,
        description="Preferred SMS provider: 'pvapins', '5sim', or 'sms-activate'. If set, this provider is tried first.",
    )


class RentalResponse(BaseModel):
    id: int
    provider: str
    status: str
    order_id: str
    phone_number: str
    country: str | None
    otp_code: str | None
    otp_count: int
    label: str | None
    expires_at: datetime | None
    remaining_seconds: int
    rented_at: datetime
    otp_received_at: datetime | None
    released_at: datetime | None

    model_config = {"from_attributes": True}


class RentalListResponse(BaseModel):
    items: list[RentalResponse]
    total: int


# ── Endpoints ──────────────────────────────────────────────

@router.get("/", response_model=RentalListResponse)
async def list_rentals(
    country: str | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    svc = RentalService(db)
    if active_only:
        items = await svc.list_active(country=country)
        return RentalListResponse(
            items=[_to_response(r) for r in items],
            total=len(items),
        )
    items, total = await svc.list_all(limit=limit, offset=offset)
    return RentalListResponse(
        items=[_to_response(r) for r in items],
        total=total,
    )


@router.post("/rent", response_model=RentalResponse)
async def rent_number(body: RentNumberRequest, db: AsyncSession = Depends(get_db)):
    svc = RentalService(db)
    try:
        rental = await svc.rent_number(
            country=body.country,
            label=body.label,
            duration_hours=body.duration_hours,
            preferred_provider=body.preferred_provider,
        )
        return _to_response(rental)
    except NumberUnavailableError as exc:
        raise HTTPException(503, f"No numbers available for country={body.country}. Provider details: {exc}")
    except Exception as exc:
        raise HTTPException(503, f"Failed to rent number: {exc}")


@router.get("/active", response_model=RentalListResponse)
async def list_active_rentals(
    country: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = RentalService(db)
    items = await svc.list_active(country=country)
    return RentalListResponse(
        items=[_to_response(r) for r in items],
        total=len(items),
    )


@router.get("/reusable")
async def find_reusable(country: str = "US", db: AsyncSession = Depends(get_db)):
    svc = RentalService(db)
    rental = await svc.find_reusable(country=country)
    if not rental:
        return {"found": False, "rental": None}
    return {"found": True, "rental": _to_response(rental)}


@router.post("/{rental_id}/release", response_model=RentalResponse)
async def release_rental(rental_id: int, db: AsyncSession = Depends(get_db)):
    svc = RentalService(db)
    rental = await svc.release_number(rental_id)
    if not rental:
        raise HTTPException(404, "Rental not found")
    return _to_response(rental)


@router.post("/{rental_id}/otp")
async def record_otp(
    rental_id: int,
    otp_code: str,
    raw_sms: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = RentalService(db)
    rental = await svc.record_otp(rental_id, otp_code, raw_sms)
    if not rental:
        raise HTTPException(404, "Rental not found")
    return _to_response(rental)


@router.get("/providers/status")
async def check_provider_status():
    """Check balance/availability for all SMS providers."""
    from otp.fivesim_service import FiveSimService
    from otp.pvapins_service import PVAPinsService
    from otp.smsactivate_service import SMSActivateService

    results = {}
    for name, svc in [("5sim", FiveSimService()), ("pvapins", PVAPinsService()), ("sms-activate", SMSActivateService())]:
        try:
            status = await svc.get_status()
            balance = await svc.check_balance() if hasattr(svc, "check_balance") else None
            results[name] = {"status": status.value, "balance": balance}
        except Exception as exc:
            results[name] = {"status": "error", "error": str(exc)}
    return results


@router.post("/expire")
async def expire_old_rentals(db: AsyncSession = Depends(get_db)):
    svc = RentalService(db)
    count = await svc.expire_old_rentals()
    return {"expired": count}


@router.get("/{rental_id}", response_model=RentalResponse)
async def get_rental(rental_id: int, db: AsyncSession = Depends(get_db)):
    svc = RentalService(db)
    rental = await svc.get_rental(rental_id)
    if not rental:
        raise HTTPException(404, "Rental not found")
    return _to_response(rental)


def _to_response(r) -> RentalResponse:
    return RentalResponse(
        id=r.id,
        provider=r.provider.value if hasattr(r.provider, "value") else r.provider,
        status=r.status.value if hasattr(r.status, "value") else r.status,
        order_id=r.order_id,
        phone_number=r.phone_number,
        country=r.country,
        otp_code=r.otp_code,
        otp_count=r.otp_count or 0,
        label=r.label,
        expires_at=r.expires_at,
        remaining_seconds=r.remaining_seconds,
        rented_at=r.rented_at,
        otp_received_at=r.otp_received_at,
        released_at=r.released_at,
    )
