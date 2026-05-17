"""Authentication API — login, token refresh, user management.

Endpoints:
  POST /api/auth/login       — authenticate with email/password, returns JWT pair
  POST /api/auth/refresh     — exchange refresh token for new access token
  POST /api/auth/logout      — (audit log only, client discards tokens)
  GET  /api/auth/me          — current user profile
  POST /api/auth/users       — create user (admin only)
  GET  /api/auth/users       — list users (admin only)
  PUT  /api/auth/users/{id}  — update user (admin only)
  DELETE /api/auth/users/{id} — deactivate user (super_admin only)
  POST /api/auth/change-password — change own password
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from models.user import User, UserRole
from security.audit import AuditAction, AuditLogger
from security.jwt_auth import (
    create_token_pair,
    decode_token,
    get_current_user,
)
from security.password import hash_password, verify_password
from security.rate_limiter import rate_limit_auth
from security.rbac import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── request/response schemas ────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: str | None

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ── endpoints ───────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password."""
    audit = AuditLogger(db)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        await audit.log_from_request(
            AuditAction.LOGIN_FAILED,
            request,
            details={"email": body.email, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        await audit.log_from_request(
            AuditAction.LOGIN_FAILED,
            request,
            user=user,
            details={"reason": "account_disabled"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last login
    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )

    tokens = create_token_pair(user.id, user.role.value)
    await audit.log_from_request(AuditAction.LOGIN_SUCCESS, request, user=user)

    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a refresh token for a new access token pair."""
    token_data = decode_token(body.refresh_token)

    if token_data.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type — refresh token required",
        )

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    audit = AuditLogger(db)
    await audit.log_from_request(AuditAction.TOKEN_REFRESH, request, user=user)

    tokens = create_token_pair(user.id, user.role.value)
    return TokenResponse(**tokens)


@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Log out (audit trail only — client should discard tokens)."""
    audit = AuditLogger(db)
    await audit.log_from_request(AuditAction.LOGOUT, request, user=user)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user profile."""
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.post(
    "/change-password",
    dependencies=[Depends(rate_limit_auth)],
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the current user's password."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hash = hash_password(body.new_password)
    await db.execute(update(User).where(User.id == user.id).values(password_hash=new_hash))

    audit = AuditLogger(db)
    await audit.log_from_request(AuditAction.PASSWORD_CHANGE, request, user=user)

    return {"message": "Password changed successfully"}


# ── admin user management ───────────────────────────────────
@router.post(
    "/users",
    response_model=UserResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: UserCreate,
    request: Request,
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user (admin only)."""
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    # Prevent non-super-admins from creating super_admin accounts
    if body.role == UserRole.SUPER_ADMIN and admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can create super_admin accounts",
        )

    user = User(
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()

    audit = AuditLogger(db)
    await audit.log_from_request(
        AuditAction.USER_CREATED,
        request,
        user=admin,
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": user.role.value},
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login_at=None,
    )


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_users(db: AsyncSession = Depends(get_db)) -> list[UserResponse]:
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            username=u.username,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent non-super-admins from modifying super_admin accounts
    if target.role == UserRole.SUPER_ADMIN and admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can modify super_admin accounts",
        )

    # Prevent role escalation beyond admin's own role
    if body.role and body.role == UserRole.SUPER_ADMIN and admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign super_admin role",
        )

    changes = {}
    if body.email is not None:
        target.email = body.email
        changes["email"] = body.email
    if body.username is not None:
        target.username = body.username
        changes["username"] = body.username
    if body.role is not None:
        old_role = target.role.value
        target.role = body.role
        changes["role"] = {"from": old_role, "to": body.role.value}
    if body.is_active is not None:
        target.is_active = body.is_active
        changes["is_active"] = body.is_active

    audit = AuditLogger(db)
    await audit.log_from_request(
        AuditAction.USER_UPDATED,
        request,
        user=admin,
        resource_type="user",
        resource_id=user_id,
        details=changes,
    )

    return UserResponse(
        id=target.id,
        email=target.email,
        username=target.username,
        role=target.role.value,
        is_active=target.is_active,
        created_at=target.created_at.isoformat(),
        last_login_at=target.last_login_at.isoformat() if target.last_login_at else None,
    )


@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))],
)
async def deactivate_user(
    user_id: int,
    request: Request,
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a user (super_admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    target.is_active = False

    audit = AuditLogger(db)
    await audit.log_from_request(
        AuditAction.USER_DISABLED,
        request,
        user=admin,
        resource_type="user",
        resource_id=user_id,
    )

    return {"message": f"User {target.email} deactivated"}
