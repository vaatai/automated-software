from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator

# ────────────────────────────────────────────────────────────
# Shared / nested config schemas
# ────────────────────────────────────────────────────────────


class SelectorType(str, Enum):
    CSS = "css"
    XPATH = "xpath"


class FieldType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    PASSWORD = "password"
    TEL = "tel"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    HIDDEN = "hidden"


class CaptchaType(str, Enum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    TURNSTILE = "turnstile"


class CaptchaSolver(str, Enum):
    TWO_CAPTCHA = "2captcha"
    ANTI_CAPTCHA = "anti_captcha"
    CAPSOLVER = "capsolver"


class FormFieldSelector(BaseModel):
    """Locator for a single form field."""

    selector: str = Field(..., min_length=1, description="CSS or XPath selector string")
    selector_type: SelectorType = Field(
        default=SelectorType.CSS, description="Type of selector"
    )
    field_type: FieldType = Field(
        default=FieldType.TEXT, description="HTML input type"
    )
    required: bool = Field(default=True, description="Whether the field is required")
    default_value: str | None = Field(
        default=None, description="Static value to fill (overrides generated data)"
    )
    strip_country_code: bool = Field(
        default=False, description="Strip country code prefix from phone numbers"
    )
    country_code: str | None = Field(
        default=None, description="Country code to strip (e.g. '91' for India)"
    )
    country_code_selector: str | None = Field(
        default=None,
        description="CSS selector for custom country code dropdown trigger button",
    )


class SubmitButtonSelector(BaseModel):
    selector: str = Field(..., min_length=1)
    selector_type: SelectorType = SelectorType.CSS


class InlineOTPConfig(BaseModel):
    """Config for inline OTP verification within a form step."""

    otp_field: str = Field(..., min_length=1, description="CSS selector for OTP input")
    verify_button: str = Field(..., min_length=1, description="CSS selector for verify button")


class FormStep(BaseModel):
    """One step in a multi-step registration flow."""

    step_name: str | None = Field(default=None, description="Human-readable step label")
    url: str | None = Field(
        default=None, description="Navigation URL for this step (optional)"
    )
    fields: dict[str, FormFieldSelector] = Field(
        default_factory=dict,
        description="Map of field name → selector config",
    )
    submit_button: SubmitButtonSelector | None = Field(
        default=None, description="Submit / next-step button"
    )
    wait_after_submit_ms: int = Field(
        default=2000, ge=0, le=30000, description="Wait time after submitting this step"
    )
    inline_email_otp: InlineOTPConfig | None = Field(
        default=None, description="Inline email OTP verification after this step"
    )
    inline_phone_otp: InlineOTPConfig | None = Field(
        default=None, description="Inline phone OTP verification after this step"
    )


class OTPFieldSettings(BaseModel):
    """Selectors for OTP input fields on the verification page."""

    email_otp_field: FormFieldSelector | None = None
    email_otp_submit: SubmitButtonSelector | None = None
    phone_otp_field: FormFieldSelector | None = None
    phone_otp_submit: SubmitButtonSelector | None = None
    otp_page_url: str | None = Field(
        default=None, description="URL of the OTP verification page if separate"
    )


class CaptchaSettings(BaseModel):
    enabled: bool = False
    captcha_type: CaptchaType | None = None
    site_key: str | None = None
    solver_service: CaptchaSolver | None = None

    @field_validator("site_key")
    @classmethod
    def require_site_key_when_enabled(cls, v: str | None, info: object) -> str | None:
        data = info.data if hasattr(info, "data") else {}
        if data.get("enabled") and not v:
            msg = "site_key is required when captcha is enabled"
            raise ValueError(msg)
        return v


class SuccessIndicator(BaseModel):
    selector: str = Field(..., min_length=1)
    selector_type: SelectorType = SelectorType.CSS
    text_contains: str | None = Field(
        default=None, description="Expected text inside the element"
    )


class FormConfig(BaseModel):
    """
    Full website registration configuration.

    Supports single-step and multi-step flows, OTP verification,
    CAPTCHA solving, and custom success detection.
    """

    registration_url: str = Field(..., min_length=1, description="URL of the registration page")
    steps: list[FormStep] = Field(
        default_factory=list,
        description="Ordered registration steps (at least one required)",
    )
    otp_settings: OTPFieldSettings | None = None
    captcha_settings: CaptchaSettings | None = None
    success_indicator: SuccessIndicator | None = None
    wait_after_submit_ms: int = Field(
        default=3000, ge=0, le=30000, description="Global fallback wait time"
    )

    @field_validator("steps")
    @classmethod
    def at_least_one_step(cls, v: list[FormStep]) -> list[FormStep]:
        if not v:
            msg = "At least one form step is required"
            raise ValueError(msg)
        return v


# ────────────────────────────────────────────────────────────
# Website profile schemas
# ────────────────────────────────────────────────────────────


class WebsiteStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class WebsiteCreate(BaseModel):
    """Request body to create a new website profile."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    url: HttpUrl = Field(..., description="Base website URL")
    form_config: FormConfig = Field(..., description="Full registration flow configuration")
    requires_email_otp: bool = Field(default=False, description="Enable email OTP verification")
    requires_mobile_otp: bool = Field(default=False, description="Enable mobile OTP verification")
    registration_only_mode: bool = Field(
        default=False, description="Skip all OTP verification — registration form only"
    )
    max_registrations_per_day: int = Field(
        default=100, ge=1, le=10000, description="Daily registration limit"
    )
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def url_to_str(cls, v: HttpUrl) -> str:
        return str(v)


class WebsiteUpdate(BaseModel):
    """Request body to partially update an existing website profile."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: HttpUrl | None = None
    form_config: FormConfig | None = None
    requires_email_otp: bool | None = None
    requires_mobile_otp: bool | None = None
    registration_only_mode: bool | None = None
    max_registrations_per_day: int | None = Field(default=None, ge=1, le=10000)
    status: WebsiteStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def url_to_str(cls, v: HttpUrl | None) -> str | None:
        return str(v) if v is not None else None


class WebsiteResponse(BaseModel):
    """Response body for a single website profile."""

    id: int
    name: str
    url: str
    form_config: dict
    requires_email_otp: bool
    requires_mobile_otp: bool
    registration_only_mode: bool
    max_registrations_per_day: int
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebsiteListResponse(BaseModel):
    """Paginated list of website profiles."""

    items: list[WebsiteResponse]
    total: int
    page: int
    page_size: int
    pages: int


class WebsiteDeleteResponse(BaseModel):
    id: int
    message: str


# ────────────────────────────────────────────────────────────
# Registration schemas (unchanged)
# ────────────────────────────────────────────────────────────


class TaskPriority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class RegistrationRequest(BaseModel):
    website_id: int
    count: int = 1
    custom_data: dict | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    queue_overflow: bool = Field(
        default=True,
        description="If True, tasks exceeding daily limit are saved for next-day processing",
    )
    cooldown_seconds: int = Field(
        default=30, ge=0, le=600,
        description="Minimum seconds between registration batches for a website",
    )


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
    total_overflow: int = 0
    reason: str | None = None
    task_ids: list[str] = []
    overflow_ids: list[int] = []
    priority: str | None = None
    daily_limit: int | None = None
    daily_used: int | None = None
    daily_remaining: int | None = None
    cooldown_wait_seconds: int | None = None


class RegistrationStats(BaseModel):
    website_id: int
    website_name: str
    today_total: int
    today_success: int
    today_failed: int
    daily_limit: int
    remaining: int
    overflow_queued: int = 0
