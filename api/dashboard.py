from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from models.registration import Registration, RegistrationStatus
from models.website import Website

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    websites = list(
        (await db.execute(select(Website).order_by(Website.created_at.desc()))).scalars().all()
    )
    registrations = list(
        (
            await db.execute(
                select(Registration).order_by(Registration.created_at.desc()).limit(50)
            )
        )
        .scalars()
        .all()
    )

    total = (await db.execute(select(func.count(Registration.id)))).scalar() or 0
    success = (
        await db.execute(
            select(func.count(Registration.id)).where(
                Registration.status == RegistrationStatus.COMPLETED
            )
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(Registration.id)).where(
                Registration.status == RegistrationStatus.FAILED
            )
        )
    ).scalar() or 0
    pending = (
        await db.execute(
            select(func.count(Registration.id)).where(
                Registration.status.in_([
                    RegistrationStatus.PENDING,
                    RegistrationStatus.IN_PROGRESS,
                ])
            )
        )
    ).scalar() or 0

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "websites": websites,
            "registrations": registrations,
            "stats": {
                "total": total,
                "success": success,
                "failed": failed,
                "pending": pending,
            },
        },
    )
