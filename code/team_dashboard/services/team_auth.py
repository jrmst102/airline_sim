"""
Team Auth – authenticate team users against users.csv in Spaces.
==================================================================
Uses bcrypt-hashed passwords stored in the ``password_hash`` column
of ``users.csv``.  No lockout, no expiry.

The spec requires 6 pre-populated team usernames (``Team 1`` … ``Team 6``).
These must be created via the user management module before teams can
log in.  This service only handles *authentication* — user provisioning
is done elsewhere.
"""

from __future__ import annotations

import logging

from app.modules.user_management import authenticate_user, UserRecord

logger = logging.getLogger(__name__)

DEFAULT_SIM_ID = "sim_001"


def login(
    simulation_id: str,
    username: str,
    password: str,
) -> dict:
    """Validate credentials and return a result dict.

    Returns::

        {"success": True,  "user": UserRecord, "message": "..."}
        {"success": False, "user": None,       "message": "..."}

    No lockout — repeated failures always return the same generic message.
    """
    try:
        user = authenticate_user(
            simulation_id=simulation_id,
            username=username,
            password=password,
        )
    except Exception as exc:
        logger.exception("Auth error")
        return {
            "success": False,
            "user": None,
            "message": "Authentication service unavailable. Please try again.",
        }

    if user is None:
        return {
            "success": False,
            "user": None,
            "message": "Invalid username or password",
        }

    return {
        "success": True,
        "user": user,
        "message": f"Welcome, {user.username}",
    }
