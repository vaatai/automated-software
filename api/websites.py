from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import WebsiteCreate, WebsiteResponse, WebsiteUpdate
from configs.database import get_db
from models.website import Website

router = APIRouter(prefix="/api/websites", tags=["websites"])


@router.post("/", response_model=WebsiteResponse)
async def create_website(body: WebsiteCreate, db: AsyncSession = Depends(get_db)):
    website = Website(
        name=body.name,
        url=body.url,
        form_config=body.form_config,
        requires_email_otp=body.requires_email_otp,
        requires_mobile_otp=body.requires_mobile_otp,
        max_registrations_per_day=body.max_registrations_per_day,
    )
    db.add(website)
    await db.flush()
    await db.refresh(website)
    return website


@router.get("/", response_model=list[WebsiteResponse])
async def list_websites(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Website).order_by(Website.created_at.desc()))
    return list(rows.scalars().all())


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(website_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.execute(select(Website).where(Website.id == website_id))
    website = row.scalar_one_or_none()
    if not website:
        raise HTTPException(404, "Website not found")
    return website


@router.put("/{website_id}", response_model=WebsiteResponse)
async def update_website(
    website_id: int, body: WebsiteUpdate, db: AsyncSession = Depends(get_db)
):
    row = await db.execute(select(Website).where(Website.id == website_id))
    website = row.scalar_one_or_none()
    if not website:
        raise HTTPException(404, "Website not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(website, key, val)
    await db.flush()
    await db.refresh(website)
    return website


@router.delete("/{website_id}")
async def delete_website(website_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.execute(select(Website).where(Website.id == website_id))
    website = row.scalar_one_or_none()
    if not website:
        raise HTTPException(404, "Website not found")
    await db.delete(website)
    return {"message": "Website deleted"}
