"""
Permissions — role definitions and permission matrix.
======================================================
Defines the four system roles (USER, PROFESSOR, TA, ADMIN) and a
permission matrix that guards every privileged action.

Usage::

    from app.auth.permissions import can, Role

    if can(role, "create_simulation"):
        ...
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """System roles — ordered from least to most privileged."""

    USER = "USER"
    TA = "TA"
    PROFESSOR = "PROFESSOR"
    ADMIN = "ADMIN"


# Roles that use the Admin Dashboard
ADMIN_ROLES = {Role.TA, Role.PROFESSOR, Role.ADMIN}

# Roles that use the Team Dashboard
TEAM_ROLES = {Role.USER}

# ── Permission matrix ──────────────────────────────────────────────────
# Maps action → set of roles allowed to perform it.

_PERMISSIONS: dict[str, set[Role]] = {
    # Team Dashboard
    "access_team_dashboard":    {Role.USER},
    "submit_decisions":         {Role.USER},

    # Admin Dashboard — view
    "access_admin_dashboard":   {Role.TA, Role.PROFESSOR, Role.ADMIN},
    "view_team_data":           {Role.TA, Role.PROFESSOR, Role.ADMIN},

    # Round management
    "advance_round":            {Role.TA, Role.PROFESSOR, Role.ADMIN},
    "undo_round":               {Role.TA, Role.PROFESSOR, Role.ADMIN},

    # Simulation lifecycle
    "create_simulation":        {Role.PROFESSOR, Role.ADMIN},
    "start_simulation":         {Role.PROFESSOR, Role.ADMIN},
    "stop_simulation":          {Role.PROFESSOR, Role.ADMIN},
    "lock_simulation":          {Role.ADMIN},
    "unlock_simulation":        {Role.ADMIN},
    "delete_simulation":        {Role.ADMIN},

    # User management
    "create_user":              {Role.ADMIN},
    "edit_user":                {Role.ADMIN},
    "remove_user":              {Role.ADMIN},
    "lock_user":                {Role.ADMIN},
    "unlock_user":              {Role.ADMIN},
    "change_user_password":     {Role.ADMIN},
    "change_user_role":         {Role.ADMIN},
    "assign_user_simulation":   {Role.ADMIN},
}


def can(role: str | Role, action: str) -> bool:
    """Return ``True`` if *role* is allowed to perform *action*."""
    if isinstance(role, str):
        try:
            role = Role(role.upper())
        except ValueError:
            return False
    allowed = _PERMISSIONS.get(action)
    if allowed is None:
        return False
    return role in allowed


def role_dashboard(role: str | Role) -> str:
    """Return ``'team'`` or ``'admin'`` depending on the role."""
    if isinstance(role, str):
        try:
            role = Role(role.upper())
        except ValueError:
            return "team"
    return "admin" if role in ADMIN_ROLES else "team"


def normalize_role(raw: str) -> str:
    """Normalize a role string, raising ``ValueError`` for unknown roles."""
    upper = raw.strip().upper()
    # Legacy mapping
    if upper in ("TEAM_LEAD", "TEAM_MEMBER", "TEAM"):
        return Role.USER.value
    if upper in ("PROF",):
        return Role.PROFESSOR.value
    try:
        return Role(upper).value
    except ValueError:
        raise ValueError(
            f"Unknown role '{raw}'. Valid roles: {[r.value for r in Role]}"
        )
