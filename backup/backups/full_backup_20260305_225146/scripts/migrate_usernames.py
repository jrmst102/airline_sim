#!/usr/bin/env python3
"""
migrate_usernames.py — One-time migration from legacy usernames.csv
====================================================================
Reads ``code/team_dashboard/usernames.csv`` (plain-text username,password),
creates bcrypt-hashed entries in ``sim_001/users.csv`` with the extended
profile schema, and registers ``sim_001`` in ``admin/simulations.csv``.

Usage::

    python scripts/migrate_usernames.py          # dry-run (default)
    python scripts/migrate_usernames.py --apply  # actually write
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from app.auth.password_manager import hash_password
from app.data.csv_manager import csv_exists, write_csv, load_csv
from app.modules.user_management import USERS_CSV_FIELDS
from app.modules.simulation_management import register_simulation

# ── Constants ──────────────────────────────────────────────────────────
SIM_ID = "sim_001"
LEGACY_CSV = _PROJECT_ROOT / "code" / "team_dashboard" / "usernames.csv"

_TEAM_ID_MAP = {
    "Team1": "A",
    "Team2": "B",
    "Team3": "C",
    "Team4": "D",
    "Team5": "E",
    "Team6": "F",
}


def _read_legacy(path: Path) -> list[tuple[str, str]]:
    """Read (username, password) pairs from the legacy CSV."""
    entries: list[tuple[str, str]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if len(row) >= 2:
                entries.append((row[0].strip(), row[1].strip()))
    return entries


def migrate(*, apply: bool = False) -> None:
    if not LEGACY_CSV.exists():
        print(f"Legacy CSV not found at {LEGACY_CSV}. Nothing to migrate.")
        return

    entries = _read_legacy(LEGACY_CSV)
    if not entries:
        print("Legacy CSV is empty. Nothing to migrate.")
        return

    now = datetime.now(timezone.utc).isoformat()

    # Load existing users.csv if present (preserve existing entries)
    existing_usernames: set[str] = set()
    existing_rows: list[dict] = []
    if csv_exists(SIM_ID, "users.csv"):
        _, existing_rows = load_csv(SIM_ID, "users.csv")
        existing_usernames = {r.get("username", "").casefold() for r in existing_rows}

    new_rows: list[dict] = []
    user_counter = len(existing_rows)

    for username, password in entries:
        if username.casefold() in existing_usernames:
            print(f"  SKIP: '{username}' already exists in {SIM_ID}/users.csv")
            continue

        user_counter += 1
        team_id = _TEAM_ID_MAP.get(username, "")
        role = "ADMIN" if username.casefold() == "admin" else "USER"

        row = {
            "simulation_id": SIM_ID,
            "user_id": f"U{user_counter:03d}",
            "username": username,
            "first_name": username,
            "last_name": "",
            "email": "",
            "role": role,
            "team_id": team_id,
            "school_id": "",
            "course_id": "",
            "password_hash": hash_password(password),
            "is_locked": "0",
            "created_at_utc": now,
            "updated_at_utc": now,
        }
        new_rows.append(row)
        label = f"Team {team_id}" if team_id else role
        print(f"  ADD: {username} ({label})")

    if not new_rows:
        print("No new users to migrate.")
        return

    if not apply:
        print(f"\nDRY RUN — {len(new_rows)} user(s) would be written to {SIM_ID}/users.csv")
        print("Re-run with --apply to perform the migration.")
        return

    all_rows = existing_rows + new_rows
    write_csv(SIM_ID, "users.csv", USERS_CSV_FIELDS, all_rows)
    print(f"\n✓ Wrote {len(new_rows)} new user(s) to {SIM_ID}/users.csv")

    # Register sim_001 in admin/simulations.csv if not already there
    register_simulation(
        simulation_id=SIM_ID,
        name="Airline Simulation",
        status="CREATED",
    )
    print(f"✓ Registered '{SIM_ID}' in admin/simulations.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy usernames.csv to sim_001/users.csv")
    parser.add_argument("--apply", action="store_true", help="Actually write (default is dry-run)")
    args = parser.parse_args()
    migrate(apply=args.apply)


if __name__ == "__main__":
    main()
