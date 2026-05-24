"""Rental number service — manages 24hr phone number rentals with multi-OTP reuse."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.rental_number import (
    RENTAL_DURATION_HOURS,
    RentalNumber,
    RentalProvider,
    RentalStatus,
)
from otp.fivesim_service import FiveSimService
from otp.pvapins_service import PVAPinsService
from otp.sms_provider import NumberUnavailableError

logger = logging.getLogger(__name__)


class RentalService:
    """Manages the lifecycle of rented phone numbers with 24hr duration."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.fivesim = FiveSimService()
        self.pvapins = PVAPinsService()

    async def list_active(self, country: str | None = None) -> list[RentalNumber]:
        """List all active (non-expired) rental numbers."""
        now = datetime.now(timezone.utc)
        q = (
            select(RentalNumber)
            .where(
                RentalNumber.status.in_([RentalStatus.RENTED, RentalStatus.OTP_RECEIVED]),
                RentalNumber.deleted_at.is_(None),
                (RentalNumber.expires_at.is_(None)) | (RentalNumber.expires_at > now),
            )
            .order_by(RentalNumber.rented_at.desc())
        )
        if country:
            q = q.where(RentalNumber.country == country.upper())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def list_all(self, limit: int = 50, offset: int = 0) -> tuple[list[RentalNumber], int]:
        """List all rental numbers with pagination."""
        count_q = select(RentalNumber).where(RentalNumber.deleted_at.is_(None))
        count_result = await self.db.execute(count_q)
        total = len(count_result.scalars().all())

        q = (
            select(RentalNumber)
            .where(RentalNumber.deleted_at.is_(None))
            .order_by(RentalNumber.rented_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def find_reusable(self, country: str) -> RentalNumber | None:
        """Find an active rental for the given country that can be reused."""
        now = datetime.now(timezone.utc)
        q = (
            select(RentalNumber)
            .where(
                RentalNumber.country == country.upper(),
                RentalNumber.status.in_([RentalStatus.RENTED, RentalStatus.OTP_RECEIVED]),
                RentalNumber.deleted_at.is_(None),
                RentalNumber.expires_at > now,
            )
            .order_by(RentalNumber.rented_at.desc())
            .limit(1)
        )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def rent_number(
        self,
        country: str = "US",
        label: str | None = None,
        duration_hours: float = RENTAL_DURATION_HOURS,
    ) -> RentalNumber:
        """Rent a new phone number for the specified duration.

        Tries 5SIM first, falls back to PVAPins.
        """
        rental_result = None
        provider_name = None

        try:
            rental_result = await self.fivesim.rent_number(country=country)
            provider_name = "5sim"
        except Exception:
            try:
                rental_result = await self.pvapins.rent_number(country=country)
                provider_name = "pvapins"
            except Exception as exc:
                raise NumberUnavailableError("all_providers", country, "any") from exc

        now = datetime.now(timezone.utc)
        rental = RentalNumber(
            provider=RentalProvider(provider_name),
            status=RentalStatus.RENTED,
            order_id=rental_result.order_id,
            phone_number=rental_result.phone_number,
            country=country.upper(),
            expires_at=now + timedelta(hours=duration_hours),
            label=label,
        )
        self.db.add(rental)
        await self.db.commit()
        await self.db.refresh(rental)

        logger.info(
            "Rented number %s from %s for country=%s, expires=%s",
            rental.phone_number,
            provider_name,
            country,
            rental.expires_at,
        )
        return rental

    async def record_otp(
        self,
        rental_id: int,
        otp_code: str,
        raw_sms: str | None = None,
    ) -> RentalNumber | None:
        """Record an OTP received on a rented number."""
        rental = await self.db.get(RentalNumber, rental_id)
        if not rental or rental.is_deleted:
            return None

        rental.otp_code = otp_code
        rental.raw_sms = raw_sms
        rental.otp_count = (rental.otp_count or 0) + 1
        rental.otp_received_at = datetime.now(timezone.utc)
        rental.status = RentalStatus.OTP_RECEIVED
        await self.db.commit()
        await self.db.refresh(rental)
        return rental

    async def release_number(self, rental_id: int) -> RentalNumber | None:
        """Manually release a rented number."""
        rental = await self.db.get(RentalNumber, rental_id)
        if not rental or rental.is_deleted:
            return None

        # Release from provider
        try:
            if rental.provider == RentalProvider.FIVESIM:
                await self.fivesim.release_number(rental.order_id, success=True)
            else:
                await self.pvapins.release_number(rental.order_id, success=True)
        except Exception as exc:
            logger.warning("Failed to release from provider: %s", exc)

        rental.status = RentalStatus.FINISHED
        rental.released_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(rental)
        return rental

    async def expire_old_rentals(self) -> int:
        """Mark expired rentals. Returns count of newly expired."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(RentalNumber)
            .where(
                RentalNumber.status.in_([RentalStatus.RENTED, RentalStatus.OTP_RECEIVED]),
                RentalNumber.expires_at.isnot(None),
                RentalNumber.expires_at <= now,
            )
            .values(status=RentalStatus.EXPIRED, released_at=now)
        )
        await self.db.commit()
        return result.rowcount

    async def get_rental(self, rental_id: int) -> RentalNumber | None:
        rental = await self.db.get(RentalNumber, rental_id)
        if rental and rental.is_deleted:
            return None
        return rental
