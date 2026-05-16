"""Website profile management — full CRUD with pagination, filtering, and soft delete."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    WebsiteCreate,
    WebsiteDeleteResponse,
    WebsiteListResponse,
    WebsiteResponse,
    WebsiteUpdate,
)
from configs.database import get_db
from models.website import Website, WebsiteStatus

router = APIRouter(prefix="/api/websites", tags=["websites"])


async def _get_website_or_404(
    website_id: int, db: AsyncSession
) -> Website:
    """Fetch a non-deleted website by ID or raise 404."""
    result = await db.execute(
        select(Website).where(Website.id == website_id, Website.deleted_at.is_(None))
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(status_code=404, detail=f"Website with id {website_id} not found")
    return website


@router.post(
    "/",
    response_model=WebsiteResponse,
    status_code=201,
    summary="Add website profile",
    description=(
        "Create a new website profile with registration URL, form selectors, "
        "OTP/captcha settings, and multi-step flow configuration."
    ),
)
async def create_website(
    body: WebsiteCreate, db: AsyncSession = Depends(get_db)
) -> Website:
    website = Website(
        name=body.name,
        url=str(body.url),
        form_config=body.form_config.model_dump(mode="json"),
        requires_email_otp=body.requires_email_otp,
        requires_mobile_otp=body.requires_mobile_otp,
        registration_only_mode=body.registration_only_mode,
        max_registrations_per_day=body.max_registrations_per_day,
        notes=body.notes,
    )
    db.add(website)
    await db.flush()
    await db.refresh(website)
    return website


@router.get(
    "/",
    response_model=WebsiteListResponse,
    summary="List website profiles",
    description="Paginated list of website profiles with optional status and name filters.",
)
async def list_websites(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status (active, inactive, paused, error)"),
    search: str | None = Query(None, description="Search by name (case-insensitive)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    base_query = select(Website).where(Website.deleted_at.is_(None))

    if status:
        try:
            status_enum = WebsiteStatus(status)
        except ValueError:
            valid = ", ".join(s.value for s in WebsiteStatus)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Must be one of: {valid}",
            )
        base_query = base_query.where(Website.status == status_enum)

    if search:
        base_query = base_query.where(Website.name.ilike(f"%{search}%"))

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    rows = await db.execute(
        base_query.order_by(Website.created_at.desc()).offset(offset).limit(page_size)
    )
    items = list(rows.scalars().all())
    pages = max(1, (total + page_size - 1) // page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get(
    "/{website_id}",
    response_model=WebsiteResponse,
    summary="Get website profile",
    description="Retrieve a single website profile by ID.",
)
async def get_website(
    website_id: int, db: AsyncSession = Depends(get_db)
) -> Website:
    return await _get_website_or_404(website_id, db)


@router.put(
    "/{website_id}",
    response_model=WebsiteResponse,
    summary="Update website profile",
    description="Partially update a website profile. Only provided fields are changed.",
)
async def update_website(
    website_id: int, body: WebsiteUpdate, db: AsyncSession = Depends(get_db)
) -> Website:
    website = await _get_website_or_404(website_id, db)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Convert form_config Pydantic model to dict for JSON storage
    if "form_config" in update_data and update_data["form_config"] is not None:
        update_data["form_config"] = body.form_config.model_dump(mode="json")  # type: ignore[union-attr]

    # Convert status string to enum
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = WebsiteStatus(update_data["status"])

    # Convert URL to string
    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    for key, val in update_data.items():
        if hasattr(website, key):
            setattr(website, key, val)

    await db.flush()
    await db.refresh(website)
    return website


@router.delete(
    "/{website_id}",
    response_model=WebsiteDeleteResponse,
    summary="Delete website profile",
    description="Soft-delete a website profile. The record is marked as deleted but not removed.",
)
async def delete_website(
    website_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    website = await _get_website_or_404(website_id, db)
    website.deleted_at = datetime.now(timezone.utc)
    website.status = WebsiteStatus.INACTIVE
    await db.flush()
    return {"id": website_id, "message": "Website profile deleted"}
