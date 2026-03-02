"""
Team Auth – authenticate team users against usernames.csv.
==================================================================
Reads plain-text credentials from ``usernames.csv`` located in the
team_dashboard package directory.  The file format is::

    Admin,RoadRunner1
    Team1,MrGreen3
    Team2,CrazyLizzard4
    ...

Username matching is case-insensitive.  Team users (``Team1`` … ``Team6``)
are mapped to simulation team IDs (``A`` … ``F``).  The ``Admin`` row is
ignored — admin users log in through the admin dashboard.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SIM_ID = "sim_001"

# Location of the credentials file (same directory as the team_dashboard package)
_CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "usernames.csv"

# Map usernames from usernames.csv → simulation team_id
# Team1 → A, Team2 → B, … Team6 → F
_TEAM_ID_MAP = {
    "team1": "A",
    "team2": "B",
    "team3": "C",
    "team4": "D",
    "team5": "E",
    "team6": "F",
}


@dataclass(frozen=True)
class AuthUser:
    """Lightweight user record returned on successful login."""
    username: str
    team_id: str
    role: str


def _load_credentials() -> dict[str, str]:
    """Read usernames.csv and return {lowercase_username: password}."""
    creds: dict[str, str] = {}
    try:
        with open(_CREDENTIALS_PATH, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) >= 2:
                    creds[row[0].strip().lower()] = row[1].strip()
    except FileNotFoundError:
        logger.error("Credentials file not found: %s", _CREDENTIALS_PATH)
    return creds


def login(
    simulation_id: str,
    username: str,
    password: str,
) -> dict:
    """Validate credentials and return a result dict.

    Returns::

        {"success": True,  "user": AuthUser, "message": "..."}
        {"success": False, "user": None,     "message": "..."}
    """
    creds = _load_credentials()
    key = username.strip().lower()

    if key not in creds:
        return {
            "success": False,
            "user": None,
            "message": "Invalid username or password",
        }

    if creds[key] != password:
        return {
            "success": False,
            "user": None,
            "message": "Invalid username or password",
        }

    # Admin users should not log in here
    if key == "admin":
        return {
            "success": False,
            "user": None,
            "message": "Admin users should use the Admin Dashboard.",
        }

    team_id = _TEAM_ID_MAP.get(key, "")
    if not team_id:
        return {
            "success": False,
            "user": None,
            "message": "No team mapping found for this user.",
        }

    user = AuthUser(username=username.strip(), team_id=team_id, role="team")
    return {
        "success": True,
        "user": user,
        "message": f"Welcome, {user.username}",
    }
