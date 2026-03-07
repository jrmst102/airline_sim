"""
User Management — full CRUD for user accounts.
=================================================
Manages users within per-simulation ``users.csv`` files.
Supports the extended profile schema (first_name, last_name, email,
school_id, course_id) and four roles: USER, PROFESSOR, TA, ADMIN.

CLI usage::

    python -m app.modules.user_management sim_001 create \\
        --username jdoe --password Secret123! --role USER --team-id A

    python -m app.modules.user_management sim_001 list
    python -m app.modules.user_management sim_001 lock --username jdoe
    python -m app.modules.user_management sim_001 auth --username jdoe --password Secret123!
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.auth.password_manager import hash_password, verify_password
from app.data.csv_manager import load_csv, write_csv, read_csv_rows
from app.data.log_manager import append_log_event


VALID_ROLES = {"ADMIN", "PROFESSOR", "TA", "USER"}

# Extended schema for users.csv (v1.1)
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


@dataclass(frozen=True)
class UserRecord:
    simulation_id: str
    user_id: str
    username: str
    first_name: str
    last_name: str
    email: str
    role: str
    team_id: str
    school_id: str
    course_id: str
    password_hash: str
    is_locked: str
    created_at_utc: str
    updated_at_utc: str

    @property
    def locked(self) -> bool:
        return self.is_locked == "1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_numeric_suffix(existing_ids: list[str], prefix: str) -> int:
    max_suffix = 0
    for user_id in existing_ids:
        if user_id.startswith(prefix):
            suffix = user_id.removeprefix(prefix)
            if suffix.isdigit():
                max_suffix = max(max_suffix, int(suffix))
    return max_suffix + 1


def _load_users(simulation_id: str) -> tuple[list[str], list[dict[str, str]]]:
    return load_csv(simulation_id, "users.csv")


def _row_to_record(row: dict[str, str]) -> UserRecord:
    """Convert a CSV row dict to a UserRecord, handling both old and new schemas."""
    return UserRecord(
        simulation_id=row.get("simulation_id", ""),
        user_id=row.get("user_id", ""),
        username=row.get("username", ""),
        first_name=row.get("first_name", ""),
        last_name=row.get("last_name", ""),
        email=row.get("email", ""),
        role=row.get("role", ""),
        team_id=row.get("team_id", ""),
        school_id=row.get("school_id", ""),
        course_id=row.get("course_id", ""),
        password_hash=row.get("password_hash", ""),
        is_locked=row.get("is_locked", "0"),
        created_at_utc=row.get("created_at_utc", ""),
        updated_at_utc=row.get("updated_at_utc", ""),
    )


def _append_login_event(
    simulation_id: str,
    user_id: str,
    username: str,
    event_type: str,
) -> None:
    rows = read_csv_rows(simulation_id, "login_log.csv")
    next_id = f"E{len(rows) + 1}"
    now = _utc_now()
    rows.append(
        {
            "event_id": next_id,
            "simulation_id": simulation_id,
            "user_id": user_id,
            "username": username,
            "event_type": event_type,
            "event_at_utc": now,
        }
    )
    write_csv(
        simulation_id,
        "login_log.csv",
        ["event_id", "simulation_id", "user_id", "username", "event_type", "event_at_utc"],
        rows,
    )


# ── List ────────────────────────────────────────────────────────────────

def list_users(
    simulation_id: str,
    root_dir: Path | str = Path("simulation/simulations"),
) -> list[UserRecord]:
    users_rows = read_csv_rows(simulation_id, "users.csv")
    return [_row_to_record(row) for row in users_rows]


# ── Create ──────────────────────────────────────────────────────────────

def create_user(
    simulation_id: str,
    username: str,
    password: str,
    role: str,
    team_id: str = "",
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    school_id: str = "",
    course_id: str = "",
    root_dir: Path | str = Path("simulation/simulations"),
    admin_user_id: str = "U_ADMIN",
) -> UserRecord:
    normalized_role = role.upper()
    # Legacy role mapping
    if normalized_role in ("TEAM_LEAD", "TEAM_MEMBER", "TEAM"):
        normalized_role = "USER"
    if normalized_role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}")
    if not username.strip():
        raise ValueError("username cannot be empty")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if normalized_role == "USER" and not team_id.strip():
        raise ValueError("team_id is required for USER role")

    fieldnames, rows = _load_users(simulation_id)
    existing_usernames = {row["username"].casefold() for row in rows}
    if username.casefold() in existing_usernames:
        raise ValueError(f"username '{username}' already exists")

    next_num = _next_numeric_suffix([row["user_id"] for row in rows], "U")
    new_user_id = f"U{next_num:03d}"
    now = _utc_now()

    new_row = {
        "simulation_id": simulation_id,
        "user_id": new_user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "role": normalized_role,
        "team_id": team_id,
        "school_id": school_id,
        "course_id": course_id,
        "password_hash": hash_password(password),
        "is_locked": "0",
        "created_at_utc": now,
        "updated_at_utc": now,
    }
    rows.append(new_row)
    # Use the extended schema for writing
    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=admin_user_id,
        action="CREATE_USER",
        details=f"user_id={new_user_id}; username={username}; role={normalized_role}; team_id={team_id}",
        event_at_utc=now,
    )

    return _row_to_record(new_row)


# ── Edit ────────────────────────────────────────────────────────────────

def edit_user(
    simulation_id: str,
    username: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    school_id: str | None = None,
    course_id: str | None = None,
    admin_user_id: str = "U_ADMIN",
) -> UserRecord:
    """Update profile fields for an existing user."""
    fieldnames, rows = _load_users(simulation_id)

    target_index = -1
    for index, row in enumerate(rows):
        if row.get("username", "").casefold() == username.casefold():
            target_index = index
            break

    if target_index < 0:
        raise ValueError(f"username '{username}' not found")

    now = _utc_now()
    if first_name is not None:
        rows[target_index]["first_name"] = first_name
    if last_name is not None:
        rows[target_index]["last_name"] = last_name
    if email is not None:
        rows[target_index]["email"] = email
    if school_id is not None:
        rows[target_index]["school_id"] = school_id
    if course_id is not None:
        rows[target_index]["course_id"] = course_id
    rows[target_index]["updated_at_utc"] = now

    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=admin_user_id,
        action="EDIT_USER",
        details=f"username={username}",
        event_at_utc=now,
    )
    return _row_to_record(rows[target_index])


# ── Remove ──────────────────────────────────────────────────────────────

def remove_user(
    simulation_id: str,
    username: str,
    admin_user_id: str = "U_ADMIN",
) -> dict:
    """Remove a user from a simulation's users.csv.

    Cannot remove the last ADMIN of a simulation.
    """
    fieldnames, rows = _load_users(simulation_id)

    target_index = -1
    for index, row in enumerate(rows):
        if row.get("username", "").casefold() == username.casefold():
            target_index = index
            break

    if target_index < 0:
        return {"success": False, "message": f"Username '{username}' not found."}

    target_row = rows[target_index]
    # Prevent removing last admin
    if target_row.get("role", "").upper() == "ADMIN":
        admin_count = sum(1 for r in rows if r.get("role", "").upper() == "ADMIN")
        if admin_count <= 1:
            return {"success": False, "message": "Cannot remove the last admin of a simulation."}

    now = _utc_now()
    removed_id = target_row.get("user_id", "")
    rows.pop(target_index)
    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=admin_user_id,
        action="REMOVE_USER",
        details=f"user_id={removed_id}; username={username}",
        event_at_utc=now,
    )
    return {"success": True, "message": f"User '{username}' removed."}


# ── Lock / Unlock ───────────────────────────────────────────────────────

def set_user_lock(
    simulation_id: str,
    username: str,
    is_locked: bool,
    root_dir: Path | str = Path("simulation/simulations"),
    admin_user_id: str = "U_ADMIN",
) -> UserRecord:
    fieldnames, rows = _load_users(simulation_id)

    target_index = -1
    for index, row in enumerate(rows):
        if row.get("username", "").casefold() == username.casefold():
            target_index = index
            break

    if target_index < 0:
        raise ValueError(f"username '{username}' not found")

    rows[target_index]["is_locked"] = "1" if is_locked else "0"
    rows[target_index]["updated_at_utc"] = _utc_now()
    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)
    updated = _row_to_record(rows[target_index])
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=admin_user_id,
        action="LOCK_USER" if is_locked else "UNLOCK_USER",
        details=f"user_id={updated.user_id}; username={updated.username}",
        event_at_utc=_utc_now(),
    )
    return updated


# ── Change Password ─────────────────────────────────────────────────────

def change_password(
    simulation_id: str,
    username: str,
    new_password: str,
    admin_user_id: str = "U_ADMIN",
) -> UserRecord:
    """Set a new password for a user."""
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    fieldnames, rows = _load_users(simulation_id)

    target_index = -1
    for index, row in enumerate(rows):
        if row.get("username", "").casefold() == username.casefold():
            target_index = index
            break

    if target_index < 0:
        raise ValueError(f"username '{username}' not found")

    rows[target_index]["password_hash"] = hash_password(new_password)
    rows[target_index]["updated_at_utc"] = _utc_now()
    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=admin_user_id,
        action="CHANGE_PASSWORD",
        details=f"username={username}",
        event_at_utc=_utc_now(),
    )
    return _row_to_record(rows[target_index])


# ── Change Role ──────────────────────────────────────────────────────────

def change_role(
    simulation_id: str,
    username: str,
    new_role: str,
    new_team_id: str = "",
    admin_user_id: str = "U_ADMIN",
) -> UserRecord:
    """Change a user's role."""
    normalized = new_role.upper()
    if normalized not in VALID_ROLES:
        raise ValueError(f"Invalid role '{new_role}'. Must be one of: {sorted(VALID_ROLES)}")
    if normalized == "USER" and not new_team_id.strip():
        raise ValueError("team_id is required when changing to USER role.")

    fieldnames, rows = _load_users(simulation_id)

    target_index = -1
    for index, row in enumerate(rows):
        if row.get("username", "").casefold() == username.casefold():
            target_index = index
            break

    if target_index < 0:
        raise ValueError(f"username '{username}' not found")

    old_role = rows[target_index].get("role", "")
    rows[target_index]["role"] = normalized
    if normalized == "USER":
        rows[target_index]["team_id"] = new_team_id
    else:
        rows[target_index]["team_id"] = ""
    rows[target_index]["updated_at_utc"] = _utc_now()

    write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=admin_user_id,
        action="CHANGE_ROLE",
        details=f"username={username}; old_role={old_role}; new_role={normalized}",
        event_at_utc=_utc_now(),
    )
    return _row_to_record(rows[target_index])


# ── Authenticate ─────────────────────────────────────────────────────────

def authenticate_user(
    simulation_id: str,
    username: str,
    password: str,
    root_dir: Path | str = Path("simulation/simulations"),
) -> UserRecord | None:
    users = list_users(simulation_id=simulation_id, root_dir=root_dir)

    matched = next(
        (user for user in users if user.username.casefold() == username.casefold()),
        None,
    )
    if matched is None:
        now = _utc_now()
        _append_login_event(simulation_id, "", username, "LOGIN_FAILURE_UNKNOWN_USER")
        append_log_event(
            simulation_id=simulation_id,
            actor_user_id="UNKNOWN",
            action="LOGIN_FAILURE_UNKNOWN_USER",
            details=f"username={username}",
            event_at_utc=now,
        )
        return None

    if matched.locked:
        now = _utc_now()
        _append_login_event(simulation_id, matched.user_id, matched.username, "LOGIN_FAILURE_LOCKED")
        append_log_event(
            simulation_id=simulation_id,
            actor_user_id=matched.user_id,
            action="LOGIN_FAILURE_LOCKED",
            details=f"username={matched.username}",
            event_at_utc=now,
        )
        return None

    if not matched.password_hash:
        now = _utc_now()
        _append_login_event(simulation_id, matched.user_id, matched.username, "LOGIN_FAILURE_NO_PASSWORD")
        append_log_event(
            simulation_id=simulation_id,
            actor_user_id=matched.user_id,
            action="LOGIN_FAILURE_NO_PASSWORD",
            details=f"username={matched.username}",
            event_at_utc=now,
        )
        return None

    password_ok = verify_password(password, matched.password_hash)
    if password_ok:
        now = _utc_now()
        _append_login_event(simulation_id, matched.user_id, matched.username, "LOGIN_SUCCESS")
        append_log_event(
            simulation_id=simulation_id,
            actor_user_id=matched.user_id,
            action="LOGIN_SUCCESS",
            details=f"username={matched.username}",
            event_at_utc=now,
        )
        return matched

    now = _utc_now()
    _append_login_event(simulation_id, matched.user_id, matched.username, "LOGIN_FAILURE_BAD_PASSWORD")
    append_log_event(
        simulation_id=simulation_id,
        actor_user_id=matched.user_id,
        action="LOGIN_FAILURE_BAD_PASSWORD",
        details=f"username={matched.username}",
        event_at_utc=now,
    )
    return None


# ── CLI ──────────────────────────────────────────────────────────────────

def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="User management for airline simulation")
    parser.add_argument("simulation_id", help="Simulation identifier")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("simulation/simulations"),
        help="Root simulations directory",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a user")
    create_parser.add_argument("--username", required=True)
    create_parser.add_argument("--password", required=True)
    create_parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    create_parser.add_argument("--team-id", default="")
    create_parser.add_argument("--first-name", default="")
    create_parser.add_argument("--last-name", default="")
    create_parser.add_argument("--email", default="")

    subparsers.add_parser("list", help="List users")

    lock_parser = subparsers.add_parser("lock", help="Lock a user")
    lock_parser.add_argument("--username", required=True)

    unlock_parser = subparsers.add_parser("unlock", help="Unlock a user")
    unlock_parser.add_argument("--username", required=True)

    auth_parser = subparsers.add_parser("auth", help="Authenticate user credentials")
    auth_parser.add_argument("--username", required=True)
    auth_parser.add_argument("--password", required=True)

    remove_parser = subparsers.add_parser("remove", help="Remove a user")
    remove_parser.add_argument("--username", required=True)

    chpass_parser = subparsers.add_parser("chpass", help="Change password")
    chpass_parser.add_argument("--username", required=True)
    chpass_parser.add_argument("--password", required=True)

    chrole_parser = subparsers.add_parser("chrole", help="Change role")
    chrole_parser.add_argument("--username", required=True)
    chrole_parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    chrole_parser.add_argument("--team-id", default="")

    return parser


def main() -> None:
    parser = _build_cli()
    args = parser.parse_args()

    if args.command == "create":
        user = create_user(
            simulation_id=args.simulation_id,
            username=args.username,
            password=args.password,
            role=args.role,
            team_id=args.team_id,
            first_name=getattr(args, "first_name", ""),
            last_name=getattr(args, "last_name", ""),
            email=getattr(args, "email", ""),
            root_dir=args.root,
        )
        print(f"Created user {user.user_id} ({user.username}, {user.role})")
        return

    if args.command == "list":
        users = list_users(simulation_id=args.simulation_id, root_dir=args.root)
        for user in users:
            fields = [
                user.user_id,
                user.username,
                user.role,
                user.team_id,
                f"locked={user.locked}",
            ]
            print(" | ".join(fields))
        return

    if args.command == "lock":
        user = set_user_lock(
            simulation_id=args.simulation_id,
            username=args.username,
            is_locked=True,
            root_dir=args.root,
        )
        print(f"Locked user {user.user_id} ({user.username})")
        return

    if args.command == "unlock":
        user = set_user_lock(
            simulation_id=args.simulation_id,
            username=args.username,
            is_locked=False,
            root_dir=args.root,
        )
        print(f"Unlocked user {user.user_id} ({user.username})")
        return

    if args.command == "auth":
        user = authenticate_user(
            simulation_id=args.simulation_id,
            username=args.username,
            password=args.password,
            root_dir=args.root,
        )
        if user:
            print(f"AUTH_SUCCESS {user.user_id} {user.username} {user.role}")
        else:
            print("AUTH_FAILURE")
        return

    if args.command == "remove":
        result = remove_user(
            simulation_id=args.simulation_id,
            username=args.username,
        )
        print(result["message"])
        return

    if args.command == "chpass":
        user = change_password(
            simulation_id=args.simulation_id,
            username=args.username,
            new_password=args.password,
        )
        print(f"Password changed for {user.username}")
        return

    if args.command == "chrole":
        user = change_role(
            simulation_id=args.simulation_id,
            username=args.username,
            new_role=args.role,
            new_team_id=args.team_id,
        )
        print(f"Role changed for {user.username} → {user.role}")
        return

    raise RuntimeError(f"Unsupported command '{args.command}'")


if __name__ == "__main__":
    main()

