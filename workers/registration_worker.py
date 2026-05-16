import asyncio
import logging
from datetime import date, datetime

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from configs.celery_app import celery_app
from configs.settings import settings
from models.daily_limit import DailyLimit
from models.registration import Registration, RegistrationStatus
from models.website import Website
from playwright_bot.registration_bot import RegistrationBot

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)


def _get_db() -> Session:
    return SyncSession()


def _update_daily_count(db: Session, website_id: int, *, success: bool) -> None:
    today = date.today()
    daily = db.execute(
        select(DailyLimit).where(
            DailyLimit.website_id == website_id,
            DailyLimit.date == today,
        )
    ).scalar_one_or_none()

    if daily:
        daily.registration_count += 1
        if success:
            daily.success_count += 1
        else:
            daily.failure_count += 1
    else:
        db.add(
            DailyLimit(
                website_id=website_id,
                date=today,
                registration_count=1,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
            )
        )


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def execute_registration(self, registration_id: int, website_id: int) -> dict:
    """Run a single registration inside its own browser context."""
    db = _get_db()
    try:
        website = db.execute(
            select(Website).where(Website.id == website_id)
        ).scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")

        db.execute(
            update(Registration)
            .where(Registration.id == registration_id)
            .values(status=RegistrationStatus.IN_PROGRESS, celery_task_id=self.request.id)
        )
        db.commit()

        bot = RegistrationBot()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                bot.register(
                    website_config={"url": website.url, "form_config": website.form_config},
                    registration_id=registration_id,
                    requires_email_otp=website.requires_email_otp,
                    requires_mobile_otp=website.requires_mobile_otp,
                )
            )
        finally:
            loop.close()

        ok = result["status"] == "completed"
        values: dict = {
            "status": RegistrationStatus.COMPLETED if ok else RegistrationStatus.FAILED,
            "email_used": result.get("email_used"),
            "phone_used": result.get("phone_used"),
            "username": result.get("username"),
            "email_otp_verified": result.get("email_otp_verified", False),
            "mobile_otp_verified": result.get("mobile_otp_verified", False),
            "error_message": result.get("error"),
            "screenshot_path": result.get("screenshot"),
        }
        if ok:
            values["completed_at"] = datetime.utcnow()

        db.execute(update(Registration).where(Registration.id == registration_id).values(**values))
        _update_daily_count(db, website_id, success=ok)
        db.commit()
        return result

    except Exception as exc:
        retries_exhausted = self.request.retries >= self.max_retries
        if retries_exhausted:
            db.execute(
                update(Registration)
                .where(Registration.id == registration_id)
                .values(status=RegistrationStatus.FAILED, error_message=str(exc))
            )
            _update_daily_count(db, website_id, success=False)
            db.commit()
            logger.exception("Registration %d permanently failed", registration_id)
            raise
        db.commit()
        logger.warning("Registration %d failed (retry %d/%d)", registration_id, self.request.retries + 1, self.max_retries)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task
def reset_daily_counters() -> None:
    logger.info("Daily counters auto-reset via date-based tracking")
