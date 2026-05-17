"""Role-Based Access Control (RBAC) — permission checks and FastAPI dependencies.

Role hierarchy (higher includes all lower permissions):
  super_admin > admin > operator > viewer

Permissions are defined per role and checked via ``require_role()`` and
``require_permission()`` FastAPI dependency factories.
"""

import logging
from enum import Enum

from fastapi import Depends, HTTPException, status

from models.user import User, UserRole
from security.jwt_auth import get_current_user

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Fine-grained permissions that map to API actions."""

    # Website management
    WEBSITE_VIEW = "website:view"
    WEBSITE_CREATE = "website:create"
    WEBSITE_UPDATE = "website:update"
    WEBSITE_DELETE = "website:delete"

    # Registration management
    REGISTRATION_VIEW = "registration:view"
    REGISTRATION_CREATE = "registration:create"
    REGISTRATION_CANCEL = "registration:cancel"

    # Proxy management
    PROXY_VIEW = "proxy:view"
    PROXY_CREATE = "proxy:create"
    PROXY_UPDATE = "proxy:update"
    PROXY_DELETE = "proxy:delete"

    # Daily limit management
    LIMIT_VIEW = "limit:view"
    LIMIT_UPDATE = "limit:update"

    # Monitoring & logs
    MONITORING_VIEW = "monitoring:view"
    LOGS_VIEW = "logs:view"

    # User management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # System administration
    SYSTEM_SETTINGS = "system:settings"
    AUDIT_VIEW = "audit:view"


# ── role → permission mapping ───────────────────────────────
ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.VIEWER: frozenset(
        {
            Permission.WEBSITE_VIEW,
            Permission.REGISTRATION_VIEW,
            Permission.PROXY_VIEW,
            Permission.LIMIT_VIEW,
            Permission.MONITORING_VIEW,
            Permission.LOGS_VIEW,
        }
    ),
    UserRole.OPERATOR: frozenset(
        {
            # Viewer permissions +
            Permission.WEBSITE_VIEW,
            Permission.REGISTRATION_VIEW,
            Permission.REGISTRATION_CREATE,
            Permission.REGISTRATION_CANCEL,
            Permission.PROXY_VIEW,
            Permission.LIMIT_VIEW,
            Permission.LIMIT_UPDATE,
            Permission.MONITORING_VIEW,
            Permission.LOGS_VIEW,
        }
    ),
    UserRole.ADMIN: frozenset(
        {
            # Operator permissions +
            Permission.WEBSITE_VIEW,
            Permission.WEBSITE_CREATE,
            Permission.WEBSITE_UPDATE,
            Permission.WEBSITE_DELETE,
            Permission.REGISTRATION_VIEW,
            Permission.REGISTRATION_CREATE,
            Permission.REGISTRATION_CANCEL,
            Permission.PROXY_VIEW,
            Permission.PROXY_CREATE,
            Permission.PROXY_UPDATE,
            Permission.PROXY_DELETE,
            Permission.LIMIT_VIEW,
            Permission.LIMIT_UPDATE,
            Permission.MONITORING_VIEW,
            Permission.LOGS_VIEW,
            Permission.USER_VIEW,
            Permission.AUDIT_VIEW,
        }
    ),
    UserRole.SUPER_ADMIN: frozenset({p for p in Permission}),
}

# ── role hierarchy for ordering ─────────────────────────────
_ROLE_RANK: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.OPERATOR: 1,
    UserRole.ADMIN: 2,
    UserRole.SUPER_ADMIN: 3,
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def has_minimum_role(user_role: UserRole, required_role: UserRole) -> bool:
    """Check if user_role is at least as high as required_role."""
    return _ROLE_RANK.get(user_role, -1) >= _ROLE_RANK.get(required_role, 999)


# ── FastAPI dependency factories ────────────────────────────
def require_role(minimum_role: UserRole):
    """Return a FastAPI dependency that enforces a minimum role.

    Usage::

        @router.post("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_endpoint(): ...
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not has_minimum_role(user.role, minimum_role):
            logger.warning(
                "RBAC denied: user %d (%s) needs %s",
                user.id,
                user.role.value,
                minimum_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return user

    return _check


def require_permission(permission: Permission):
    """Return a FastAPI dependency that enforces a specific permission.

    Usage::

        @router.delete("/websites/{id}", dependencies=[Depends(require_permission(Permission.WEBSITE_DELETE))])
        async def delete_website(id: int): ...
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            logger.warning(
                "RBAC denied: user %d (%s) lacks %s",
                user.id,
                user.role.value,
                permission.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return user

    return _check
