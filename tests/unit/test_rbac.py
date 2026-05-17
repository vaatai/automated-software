"""Unit tests for security/rbac.py — roles, permissions, hierarchy."""

import pytest

from models.user import UserRole
from security.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    has_minimum_role,
    has_permission,
)


@pytest.mark.unit
class TestRolePermissions:
    def test_viewer_has_view_permissions(self):
        assert has_permission(UserRole.VIEWER, Permission.WEBSITE_VIEW)
        assert has_permission(UserRole.VIEWER, Permission.REGISTRATION_VIEW)
        assert has_permission(UserRole.VIEWER, Permission.MONITORING_VIEW)

    def test_viewer_cannot_create(self):
        assert not has_permission(UserRole.VIEWER, Permission.WEBSITE_CREATE)
        assert not has_permission(UserRole.VIEWER, Permission.REGISTRATION_CREATE)
        assert not has_permission(UserRole.VIEWER, Permission.USER_CREATE)

    def test_operator_can_create_registrations(self):
        assert has_permission(UserRole.OPERATOR, Permission.REGISTRATION_CREATE)
        assert has_permission(UserRole.OPERATOR, Permission.REGISTRATION_CANCEL)

    def test_operator_cannot_manage_websites(self):
        assert not has_permission(UserRole.OPERATOR, Permission.WEBSITE_CREATE)
        assert not has_permission(UserRole.OPERATOR, Permission.WEBSITE_DELETE)

    def test_admin_has_website_crud(self):
        assert has_permission(UserRole.ADMIN, Permission.WEBSITE_CREATE)
        assert has_permission(UserRole.ADMIN, Permission.WEBSITE_UPDATE)
        assert has_permission(UserRole.ADMIN, Permission.WEBSITE_DELETE)

    def test_admin_has_user_management(self):
        assert has_permission(UserRole.ADMIN, Permission.USER_VIEW)
        assert has_permission(UserRole.ADMIN, Permission.USER_CREATE)
        assert has_permission(UserRole.ADMIN, Permission.USER_UPDATE)

    def test_admin_cannot_delete_users(self):
        assert not has_permission(UserRole.ADMIN, Permission.USER_DELETE)

    def test_super_admin_has_all_permissions(self):
        for perm in Permission:
            assert has_permission(UserRole.SUPER_ADMIN, perm), f"super_admin missing {perm}"

    def test_super_admin_has_system_settings(self):
        assert has_permission(UserRole.SUPER_ADMIN, Permission.SYSTEM_SETTINGS)
        assert has_permission(UserRole.SUPER_ADMIN, Permission.USER_DELETE)


@pytest.mark.unit
class TestRoleHierarchy:
    def test_viewer_meets_viewer(self):
        assert has_minimum_role(UserRole.VIEWER, UserRole.VIEWER)

    def test_viewer_below_operator(self):
        assert not has_minimum_role(UserRole.VIEWER, UserRole.OPERATOR)

    def test_admin_meets_operator(self):
        assert has_minimum_role(UserRole.ADMIN, UserRole.OPERATOR)

    def test_super_admin_meets_all(self):
        for role in UserRole:
            assert has_minimum_role(UserRole.SUPER_ADMIN, role)

    def test_operator_below_admin(self):
        assert not has_minimum_role(UserRole.OPERATOR, UserRole.ADMIN)


@pytest.mark.unit
class TestPermissionCompleteness:
    def test_all_roles_have_entries(self):
        for role in UserRole:
            assert role in ROLE_PERMISSIONS, f"{role} missing from ROLE_PERMISSIONS"

    def test_higher_roles_have_more_permissions(self):
        roles = [UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        for i in range(len(roles) - 1):
            lower = ROLE_PERMISSIONS[roles[i]]
            upper = ROLE_PERMISSIONS[roles[i + 1]]
            assert lower.issubset(upper), (
                f"{roles[i]} perms not subset of {roles[i + 1]}"
            )
