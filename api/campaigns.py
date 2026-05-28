"""Campaign API — launch parallel registrations across multiple websites with
automatic country-wise phone number assignment.

A campaign takes a list of (website_id, country, count) entries and:
1. Groups entries by country
2. For each country, finds or rents a phone number (reusing active rentals)
3. Queues all registrations simultaneously with the assigned numbers
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from models.rental_number import RentalNumber, RentalStatus
from services.registration_service import RegistrationService
from services.rental_service import RentalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


# ── Schemas ────────────────────────────────────────────────

class CampaignEntry(BaseModel):
    website_id: int
    country: str = Field(min_length=2, max_length=5)
    count: int = Field(default=1, ge=1, le=100)
    priority: str = "normal"
    preferred_provider: str | None = Field(
        default=None,
        description="Preferred SMS provider: 'pvapins', '5sim', or 'sms-activate'.",
    )


class CampaignRequest(BaseModel):
    entries: list[CampaignEntry] = Field(..., min_length=1, max_length=50)
    duration_hours: float = Field(default=24, gt=0, le=720)
    preferred_provider: str | None = Field(
        default=None,
        description="Default preferred SMS provider for all entries (can be overridden per-entry).",
    )


class EntryResult(BaseModel):
    website_id: int
    country: str
    count: int
    phone_number: str | None = None
    rental_id: int | None = None
    provider: str | None = None
    queued: int = 0
    error: str | None = None


class CampaignResponse(BaseModel):
    total_entries: int
    total_queued: int
    total_failed: int
    numbers_rented: int
    numbers_reused: int
    results: list[EntryResult]
    created_at: str


# ── Endpoints ──────────────────────────────────────────────

@router.post("/launch", response_model=CampaignResponse)
async def launch_campaign(body: CampaignRequest, db: AsyncSession = Depends(get_db)):
    """Launch a campaign: auto-assign numbers by country, queue all registrations."""
    rental_svc = RentalService(db)
    reg_svc = RegistrationService(db)

    # Group entries by country to share numbers
    country_entries: dict[str, list[CampaignEntry]] = {}
    for entry in body.entries:
        country_entries.setdefault(entry.country.upper(), []).append(entry)

    # For each country, find or rent a number
    country_rentals: dict[str, RentalNumber | None] = {}
    numbers_rented = 0
    numbers_reused = 0

    # Determine per-country preferred provider from entries
    country_preferred: dict[str, str | None] = {}
    for country, c_entries in country_entries.items():
        # Use entry-level preferred_provider if set, else fall back to campaign-level
        entry_pref = next((e.preferred_provider for e in c_entries if e.preferred_provider), None)
        country_preferred[country] = entry_pref or body.preferred_provider

    for country in country_entries:
        # Try to find an existing active rental
        rental = await rental_svc.find_reusable(country)
        if rental:
            country_rentals[country] = rental
            numbers_reused += 1
            logger.info("Campaign: reusing rental %d for country %s", rental.id, country)
        else:
            # Rent a new number
            try:
                rental = await rental_svc.rent_number(
                    country=country,
                    label=f"Campaign {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                    duration_hours=body.duration_hours,
                    preferred_provider=country_preferred.get(country),
                )
                country_rentals[country] = rental
                numbers_rented += 1
                logger.info("Campaign: rented new number %s for country %s", rental.phone_number, country)
            except Exception as exc:
                logger.warning("Campaign: failed to rent number for %s: %s", country, exc)
                country_rentals[country] = None

    # Queue registrations for each entry
    results: list[EntryResult] = []
    total_queued = 0
    total_failed = 0

    for entry in body.entries:
        country = entry.country.upper()
        rental = country_rentals.get(country)
        er = EntryResult(
            website_id=entry.website_id,
            country=country,
            count=entry.count,
        )

        if rental:
            er.phone_number = rental.phone_number
            er.rental_id = rental.id
            er.provider = rental.provider.value if hasattr(rental.provider, 'value') else str(rental.provider)

        # Build custom_data for the registration
        custom_data: dict = {"phone_country": country}
        # Pass preferred_provider so registration_bot uses correct provider ordering
        pref_provider = entry.preferred_provider or body.preferred_provider
        if pref_provider:
            custom_data["preferred_provider"] = pref_provider
        if rental:
            custom_data["reuse_rental_id"] = rental.id
            custom_data["reuse_phone"] = rental.phone_number
            custom_data["reuse_provider"] = rental.provider.value if hasattr(rental.provider, 'value') else str(rental.provider)
            custom_data["reuse_order_id"] = rental.order_id
            custom_data["reuse_otp_count"] = rental.otp_count
            custom_data["reuse_last_otp"] = rental.otp_code

        try:
            result = await reg_svc.queue_registrations(
                website_id=entry.website_id,
                count=entry.count,
                custom_data=custom_data,
                priority=entry.priority,
                cooldown_seconds=0,
            )
            er.queued = result.get("total_queued", 0)
            total_queued += er.queued
            if result.get("total_rejected", 0) > 0:
                er.error = result.get("reason")
                total_failed += result["total_rejected"]
        except Exception as exc:
            er.error = str(exc)
            total_failed += entry.count
            logger.warning("Campaign: failed to queue for website %d: %s", entry.website_id, exc)

        results.append(er)

    return CampaignResponse(
        total_entries=len(body.entries),
        total_queued=total_queued,
        total_failed=total_failed,
        numbers_rented=numbers_rented,
        numbers_reused=numbers_reused,
        results=results,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
