#!/usr/bin/env python3
"""
provision_demo.py — Provision the demo simulation (sim_demo)
=============================================================
Creates ``sim_demo`` with 9 pre-configured accounts:
1 Admin, 1 Professor, 1 TA, and 5 team Users.

Can be run standalone or called from application startup.

Usage::

    python scripts/provision_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from app.modules.simulation_management import (
    create_simulation,
    get_simulation,
)
from app.modules.user_management import create_user, list_users

# ── Demo configuration ────────────────────────────────────────────────
DEMO_SIM_ID = "sim_demo"
DEMO_SIM_NAME = "Demo Simulation"
DEMO_TOTAL_ROUNDS = 3

DEMO_ACCOUNTS = [
    # (username, password, role, team_id, first_name, last_name, email)
    ("demoadmin", "DemoAdmin2026!", "ADMIN", "", "Demo", "Admin", "demo@example.com"),
    ("demoprof", "DemoProf2026!", "PROFESSOR", "", "Demo", "Professor", "demoprof@example.com"),
    ("demota", "DemoTA2026!", "TA", "", "Demo", "TA", "demota@example.com"),
    ("demouser1", "DemoUser1!", "USER", "A", "Demo", "User1", "demo1@example.com"),
    ("demouser2", "DemoUser2!", "USER", "B", "Demo", "User2", "demo2@example.com"),
    ("demouser3", "DemoUser3!", "USER", "C", "Demo", "User3", "demo3@example.com"),
    ("demouser4", "DemoUser4!", "USER", "D", "Demo", "User4", "demo4@example.com"),
    ("demouser5", "DemoUser5!", "USER", "E", "Demo", "User5", "demo5@example.com"),
]


def provision_demo() -> bool:
    """Provision the demo simulation if it doesn't already exist.

    Returns True if the demo was created, False if it already existed.
    """
    existing = get_simulation(DEMO_SIM_ID)
    if existing:
        print(f"Demo simulation '{DEMO_SIM_ID}' already exists — skipping.")
        return False

    print(f"Creating demo simulation '{DEMO_SIM_ID}'...")

    # Create the simulation (sets up all CSV data files + registry entry)
    create_simulation(
        simulation_id=DEMO_SIM_ID,
        name=DEMO_SIM_NAME,
        total_rounds=DEMO_TOTAL_ROUNDS,
        auto_create_teams=False,  # We'll create our own named accounts
    )

    # Check which users already exist (create_simulation may have created some)
    existing_users = {u.username.casefold() for u in list_users(DEMO_SIM_ID)}

    # Create demo accounts
    for username, password, role, team_id, first_name, last_name, email in DEMO_ACCOUNTS:
        if username.casefold() in existing_users:
            print(f"  SKIP: '{username}' already exists")
            continue
        create_user(
            simulation_id=DEMO_SIM_ID,
            username=username,
            password=password,
            role=role,
            team_id=team_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        label = f"Team {team_id}" if team_id else role
        print(f"  Created: {username} ({label})")

    print(f"✓ Demo simulation '{DEMO_SIM_ID}' provisioned with {len(DEMO_ACCOUNTS)} accounts.")
    return True


def main() -> None:
    provision_demo()


if __name__ == "__main__":
    main()
