"""
Simulation Management — create, lock/unlock, and remove simulations.
=====================================================================
Manages the global simulation registry (``admin/simulations.csv``)
and provides administrative operations on simulations as a whole.

CLI usage::

    python -m app.modules.simulation_management create \\
        --sim-id sim_002 --name "MBA Spring 2026" --rounds 5 \\
        --admin-user profmendoza --admin-pass Secret123!

    python -m app.modules.simulation_management lock sim_002
    python -m app.modules.simulation_management unlock sim_002
    python -m app.modules.simulation_management remove sim_002
    python -m app.modules.simulation_management list
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import re
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.auth.password_manager import hash_password
from app.data.csv_manager import (
    csv_exists,
    list_keys,
    read_csv_rows,
    store_exists,
    write_csv,
)
from app.storage.spaces_store import get_store

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────
REGISTRY_KEY = "admin/simulations.csv"

REGISTRY_FIELDS = [
    "simulation_id",
    "name",
    "status",
    "is_locked",
    "school_id",
    "course_id",
    "created_at_utc",
    "updated_at_utc",
]

USERS_CSV_FIELDS = [
    "simulation_id",
    "user_id",
    "username",
    "first_name",
    "last_name",
    "email",
    "role",
    "team_id",
    "school_id",
    "course_id",
    "password_hash",
    "is_locked",
    "created_at_utc",
    "updated_at_utc",
]

SIM_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")

DEMO_SIM_ID = "sim_demo"

# Imported at function level to avoid circular imports; use
# setup_simulation.TEAM_LETTERS for the full A–J set.
_ALL_TEAM_LETTERS = list("ABCDEFGHIJ")


# ── Data classes ───────────────────────────────────────────────────────

@dataclass
class CredentialEntry:
    username: str
    password: str
    role: str
    team_id: str


@dataclass
class CreateSimResult:
    simulation_id: str
    name: str
    credentials: list[CredentialEntry] = field(default_factory=list)


# ── Helpers ────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_password(length: int = 12) -> str:
    """Generate a random password with letters, digits, and one special char."""
    alphabet = string.ascii_letters + string.digits
    pwd = [secrets.choice(alphabet) for _ in range(length - 1)]
    pwd.append(secrets.choice("!@#$%&"))
    # Shuffle to avoid the special char always being last
    combined = list(pwd)
    secrets.SystemRandom().shuffle(combined)
    return "".join(combined)


def _load_registry() -> list[dict[str, str]]:
    """Load the global simulation registry, returning [] if missing."""
    store = get_store()
    if not store.exists(REGISTRY_KEY):
        return []
    text = store.read_text(REGISTRY_KEY)
    return list(csv.DictReader(io.StringIO(text)))


def _save_registry(rows: list[dict[str, str]]) -> None:
    """Write the global simulation registry."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    get_store().write_text(REGISTRY_KEY, buf.getvalue(), content_type="text/csv")


def _ensure_registry() -> None:
    """Create the registry file if it doesn't exist yet."""
    store = get_store()
    if not store.exists(REGISTRY_KEY):
        _save_registry([])


# ── Public API ─────────────────────────────────────────────────────────

def list_simulations() -> list[dict[str, str]]:
    """Return all simulation entries from the registry."""
    return _load_registry()


def get_simulation(simulation_id: str) -> dict[str, str] | None:
    """Return a single simulation entry or ``None``."""
    for row in _load_registry():
        if row.get("simulation_id") == simulation_id:
            return row
    return None


def register_simulation(
    simulation_id: str,
    name: str,
    status: str = "CREATED",
    school_id: str = "",
    course_id: str = "",
) -> None:
    """Add or update a simulation in the global registry."""
    _ensure_registry()
    rows = _load_registry()
    now = _utc_now()

    # Check if already exists — update
    for row in rows:
        if row.get("simulation_id") == simulation_id:
            row["name"] = name
            row["status"] = status
            row["school_id"] = school_id
            row["course_id"] = course_id
            row["updated_at_utc"] = now
            _save_registry(rows)
            return

    # New entry
    rows.append({
        "simulation_id": simulation_id,
        "name": name,
        "status": status,
        "is_locked": "0",
        "school_id": school_id,
        "course_id": course_id,
        "created_at_utc": now,
        "updated_at_utc": now,
    })
    _save_registry(rows)


def update_simulation_status(simulation_id: str, status: str) -> None:
    """Update the status field of a simulation in the registry."""
    rows = _load_registry()
    now = _utc_now()
    for row in rows:
        if row.get("simulation_id") == simulation_id:
            row["status"] = status
            row["updated_at_utc"] = now
            _save_registry(rows)
            return
    raise ValueError(f"Simulation '{simulation_id}' not found in registry.")


def lock_simulation(simulation_id: str) -> dict:
    """Lock a simulation — team logins and decision submissions are rejected."""
    rows = _load_registry()
    now = _utc_now()
    for row in rows:
        if row.get("simulation_id") == simulation_id:
            row["is_locked"] = "1"
            row["updated_at_utc"] = now
            _save_registry(rows)
            return {"success": True, "message": f"Simulation '{simulation_id}' locked."}
    return {"success": False, "message": f"Simulation '{simulation_id}' not found."}


def unlock_simulation(simulation_id: str) -> dict:
    """Unlock a simulation — normal operations resume."""
    rows = _load_registry()
    now = _utc_now()
    for row in rows:
        if row.get("simulation_id") == simulation_id:
            row["is_locked"] = "0"
            row["updated_at_utc"] = now
            _save_registry(rows)
            return {"success": True, "message": f"Simulation '{simulation_id}' unlocked."}
    return {"success": False, "message": f"Simulation '{simulation_id}' not found."}


def remove_simulation(simulation_id: str) -> dict:
    """Remove a simulation — deletes all data and the registry entry.

    The demo simulation cannot be removed.
    """
    if simulation_id == DEMO_SIM_ID:
        return {"success": False, "message": "The demo simulation cannot be removed."}

    rows = _load_registry()
    new_rows = [r for r in rows if r.get("simulation_id") != simulation_id]
    if len(new_rows) == len(rows):
        return {"success": False, "message": f"Simulation '{simulation_id}' not found."}

    # Delete all data under the simulation prefix
    store = get_store()
    keys = store.list_keys(f"{simulation_id}/")
    for key in keys:
        try:
            store.delete(key)
        except Exception:
            logger.warning("Failed to delete key: %s", key)

    _save_registry(new_rows)
    return {"success": True, "message": f"Simulation '{simulation_id}' removed."}


def create_simulation(
    simulation_id: str,
    name: str,
    total_rounds: int = 3,
    num_teams: int = 5,
    admin_username: str = "",
    admin_password: str = "",
    school_id: str = "",
    course_id: str = "",
    auto_create_teams: bool = True,
) -> CreateSimResult:
    """Create a new simulation with all data files and user accounts.

    Wraps ``setup_simulation`` and additionally:
    - Registers the simulation in ``admin/simulations.csv``.
    - Creates admin + team user accounts in ``{sim_id}/users.csv``
      with the extended profile schema (with bcrypt-hashed passwords).
    - Returns a credentials report.
    """
    # Validate simulation_id
    if not SIM_ID_PATTERN.match(simulation_id):
        raise ValueError(
            f"Invalid simulation_id '{simulation_id}'. "
            "Use only letters, digits, and underscores."
        )

    # Check if already exists
    existing = get_simulation(simulation_id)
    if existing:
        raise ValueError(f"Simulation '{simulation_id}' already exists.")

    if not admin_username:
        admin_username = f"admin_{simulation_id}"
    if not admin_password:
        admin_password = _generate_password()

    # 1. Run the standard setup to create all CSV data files
    from app.modules.setup_simulation import setup_simulation

    setup_simulation(
        simulation_id=simulation_id,
        simulation_name=name,
        total_rounds=total_rounds,
        num_teams=num_teams,
        overwrite=True,
    )

    # 2. Register in the global simulation registry
    register_simulation(
        simulation_id=simulation_id,
        name=name,
        status="CREATED",
        school_id=school_id,
        course_id=course_id,
    )

    # 3. Create user accounts with the extended schema
    credentials: list[CredentialEntry] = []
    now = _utc_now()
    users: list[dict[str, str]] = []
    user_counter = 1

    # Admin user
    users.append({
        "simulation_id": simulation_id,
        "user_id": f"U{user_counter:03d}",
        "username": admin_username,
        "first_name": "Admin",
        "last_name": "",
        "email": "",
        "role": "ADMIN",
        "team_id": "",
        "school_id": school_id,
        "course_id": course_id,
        "password_hash": hash_password(admin_password),
        "is_locked": "0",
        "created_at_utc": now,
        "updated_at_utc": now,
    })
    credentials.append(CredentialEntry(
        username=admin_username,
        password=admin_password,
        role="ADMIN",
        team_id="",
    ))
    user_counter += 1

    # Team users
    team_letters = _ALL_TEAM_LETTERS[:num_teams]
    if auto_create_teams:
        for letter in team_letters:
            team_username = f"team{letter.lower()}_{simulation_id}"
            team_password = _generate_password()
            users.append({
                "simulation_id": simulation_id,
                "user_id": f"U{user_counter:03d}",
                "username": team_username,
                "first_name": f"Team {letter}",
                "last_name": "",
                "email": "",
                "role": "USER",
                "team_id": letter,
                "school_id": school_id,
                "course_id": course_id,
                "password_hash": hash_password(team_password),
                "is_locked": "0",
                "created_at_utc": now,
                "updated_at_utc": now,
            })
            credentials.append(CredentialEntry(
                username=team_username,
                password=team_password,
                role="USER",
                team_id=letter,
            ))
            user_counter += 1

    # Write the extended users.csv (overwrite the one created by setup_simulation)
    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, users)

    return CreateSimResult(
        simulation_id=simulation_id,
        name=name,
        credentials=credentials,
    )


# ── CLI ────────────────────────────────────────────────────────────────

def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulation management for airline_sim"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_p = subparsers.add_parser("create", help="Create a new simulation")
    create_p.add_argument("--sim-id", required=True, help="Simulation ID")
    create_p.add_argument("--name", required=True, help="Display name")
    create_p.add_argument("--rounds", type=int, default=3, help="Number of rounds")
    create_p.add_argument("--num-teams", type=int, default=5, help="Number of teams (2–10, default: 5)")
    create_p.add_argument("--admin-user", default="", help="Admin username")
    create_p.add_argument("--admin-pass", default="", help="Admin password")
    create_p.add_argument("--school-id", default="")
    create_p.add_argument("--course-id", default="")
    create_p.add_argument(
        "--no-teams", action="store_true", help="Skip auto-creating team accounts"
    )

    # lock
    lock_p = subparsers.add_parser("lock", help="Lock a simulation")
    lock_p.add_argument("sim_id", help="Simulation ID to lock")

    # unlock
    unlock_p = subparsers.add_parser("unlock", help="Unlock a simulation")
    unlock_p.add_argument("sim_id", help="Simulation ID to unlock")

    # remove
    remove_p = subparsers.add_parser("remove", help="Remove a simulation")
    remove_p.add_argument("sim_id", help="Simulation ID to remove")
    remove_p.add_argument("--confirm", required=True, help="Type the sim_id to confirm")

    # list
    subparsers.add_parser("list", help="List all simulations")

    return parser


def main() -> None:
    parser = _build_cli()
    args = parser.parse_args()

    if args.command == "create":
        result = create_simulation(
            simulation_id=args.sim_id,
            name=args.name,
            total_rounds=args.rounds,
            num_teams=args.num_teams,
            admin_username=args.admin_user,
            admin_password=args.admin_pass,
            school_id=args.school_id,
            course_id=args.course_id,
            auto_create_teams=not args.no_teams,
        )
        print(f"\nSimulation '{result.simulation_id}' created: {result.name}")
        print("\n── Credentials ──")
        for cred in result.credentials:
            team_info = f"  (Team {cred.team_id})" if cred.team_id else ""
            print(f"  {cred.role:<10} {cred.username:<30} {cred.password}{team_info}")
        return

    if args.command == "lock":
        result = lock_simulation(args.sim_id)
        print(result["message"])
        return

    if args.command == "unlock":
        result = unlock_simulation(args.sim_id)
        print(result["message"])
        return

    if args.command == "remove":
        if args.confirm != args.sim_id:
            print(f"ERROR: --confirm must match sim_id ('{args.sim_id}').")
            return
        result = remove_simulation(args.sim_id)
        print(result["message"])
        return

    if args.command == "list":
        sims = list_simulations()
        if not sims:
            print("No simulations registered.")
            return
        for s in sims:
            lock = " [LOCKED]" if s.get("is_locked", "0") == "1" else ""
            print(f"  {s['simulation_id']:<20} {s.get('status', ''):<10} {s.get('name', '')}{lock}")
        return


if __name__ == "__main__":
    main()
