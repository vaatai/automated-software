from datetime import datetime

from pydantic import BaseModel

# --------------- Website Schemas ---------------

class WebsiteCreate(BaseModel):
    name: str
    url: str
    form_config: dict
    requires_email_otp: bool = False
    requires_mobile_otp: bool = False
    max_registrations_per_day: int = 100


class WebsiteUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    form_config: dict | None = None
    requires_email_otp: bool | None = None
    requires_mobile_otp: bool | None = None
    max_registrations_per_day: int | None = None
    status: str | None = None


class WebsiteResponse(BaseModel):
    id: int
    name: str
    url: str
    form_config: dict
    requires_email_otp: bool
    requires_mobile_otp: bool
    max_registrations_per_day: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --------------- Registration Schemas ---------------

class RegistrationRequest(BaseModel):
    website_id: int
    count: int = 1
    custom_data: dict | None = None


class RegistrationResponse(BaseModel):
    id: int
    website_id: int
    status: str
    username: str | None = None
    email_used: str | None = None
    phone_used: str | None = None
    email_otp_verified: bool
    mobile_otp_verified: bool
    celery_task_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class BulkRegistrationResponse(BaseModel):
    total_requested: int
    total_queued: int
    total_rejected: int
    reason: str | None = None
    task_ids: list[str] = []


class RegistrationStats(BaseModel):
    website_id: int
    website_name: str
    today_total: int
    today_success: int
    today_failed: int
    daily_limit: int
    remaining: int
