"""
Login Manager — centralised multi-simulation authentication.
==============================================================
Scans active simulations, finds the user, authenticates via bcrypt,
and returns the simulation context.

Usage::

    from app.auth.login_manager import login

    result = login(username="Team1", password="MrGreen3")
    if result.success:
        print(result.sim_ids, result.user)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.auth.password_manager import verify_password
from app.auth.permissions import normalize_role, role_dashboard
from app.data.csv_manager import read_csv_rows, csv_exists, store_exists

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────
SIMULATIONS_REGISTRY_KEY = "admin/simulations.csv"


# ── Data classes ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuthUser:
    """Authenticated user record returned on successful login."""

    username: str
    user_id: str
    team_id: str
    role: str           # normalised: USER, PROFESSOR, TA, ADMIN
    sim_id: str         # primary simulation (first match or selected)
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    dashboard: str = ""  # "team" or "admin"


@dataclass
class LoginResult:
    """Outcome of a login attempt."""

    success: bool
    user: AuthUser | None = None
    sim_ids: list[str] = field(default_factory=list)
    needs_sim_picker: bool = False
    message: str = ""


# ── Helpers ────────────────────────────────────────────────────────────

def _load_simulation_registry() -> list[dict[str, str]]:
    """Return all rows from ``admin/simulations.csv``, or [] if missing."""
    from app.data.csv_manager import get_store
    store = get_store()
    if not store.exists(SIMULATIONS_REGISTRY_KEY):
        return []
    import csv, io
    text = store.read_text(SIMULATIONS_REGISTRY_KEY)
    return list(csv.DictReader(io.StringIO(text)))


def get_active_simulation_ids() -> list[str]:
    """Return simulation IDs whose status is CREATED or STARTED."""
    rows = _load_simulation_registry()
    active = []
    for r in rows:
        status = r.get("status", "").upper()
        if status in ("CREATED", "STARTED"):
            active.append(r.get("simulation_id", ""))
    return [s for s in active if s]


def get_all_simulations() -> list[dict[str, str]]:
    """Return every row from the simulation registry."""
    return _load_simulation_registry()


def get_simulations_for_user(username: str) -> list[str]:
    """Return all simulation IDs that contain *username* in their users.csv."""
    active_ids = get_active_simulation_ids()
    matched: list[str] = []
    key_lower = username.strip().lower()
    for sim_id in active_ids:
        if not csv_exists(sim_id, "users.csv"):
            continue
        rows = read_csv_rows(sim_id, "users.csv")
        for row in rows:
            if row.get("username", "").strip().lower() == key_lower:
                matched.append(sim_id)
                break
    return matched


# ── Public API ─────────────────────────────────────────────────────────

def login(username: str, password: str) -> LoginResult:
    """Authenticate *username* / *password* across all active simulations.

    1. Scan every active simulation's ``users.csv`` for a matching username.
    2. If found in exactly one simulation → authenticate and return.
    3. If found in N > 1 simulations → authenticate against the first
       match and flag ``needs_sim_picker = True``.
    4. If not found → return failure.
    """
    if not username or not password:
        return LoginResult(success=False, message="Username and password are required.")

    key_lower = username.strip().lower()

    # Gather all active simulation IDs
    active_ids = get_active_simulation_ids()
    if not active_ids:
        return LoginResult(
            success=False,
            message="No active simulations available. Contact your administrator.",
        )

    # Scan each simulation for the username
    matches: list[tuple[str, dict[str, str]]] = []  # (sim_id, user_row)
    for sim_id in active_ids:
        if not csv_exists(sim_id, "users.csv"):
            print(f"[LOGIN-DIAG] sim {sim_id}: users.csv NOT FOUND", flush=True)
            continue
        rows = read_csv_rows(sim_id, "users.csv")
        unames = [r.get('username', '?') for r in rows]
        print(f"[LOGIN-DIAG] sim {sim_id}: {len(rows)} users, usernames={unames}", flush=True)
        for row in rows:
            if row.get("username", "").strip().lower() == key_lower:
                matches.append((sim_id, row))
                break

    if not matches:
        print(f"[LOGIN-DIAG] no matches for {key_lower!r} across {len(active_ids)} active sims", flush=True)
        return LoginResult(success=False, message="Invalid username or password.")

    # Check if the simulation is locked (reject team users)
    registry = {r["simulation_id"]: r for r in _load_simulation_registry()}

    # Authenticate against the first matching simulation
    sim_id, user_row = matches[0]

    # Check user lock
    if user_row.get("is_locked", "0") == "1":
        return LoginResult(success=False, message="Your account is locked. Contact your instructor.")

    # Check password
    password_hash = user_row.get("password_hash", "")
    print(f"[LOGIN-DIAG] matched sim={sim_id} user={user_row.get('username')} hash_len={len(password_hash)}", flush=True)
    if not verify_password(password, password_hash):
        print(f"[LOGIN-DIAG] password verification FAILED for {user_row.get('username')}", flush=True)
        return LoginResult(success=False, message="Invalid username or password.")

    # Normalise role
    raw_role = user_row.get("role", "USER")
    try:
        role = normalize_role(raw_role)
    except ValueError:
        role = "USER"

    # For team users, check if the simulation is locked
    sim_ids = [m[0] for m in matches]
    if role == "USER":
        sim_info = registry.get(sim_id, {})
        if sim_info.get("is_locked", "0") == "1":
            return LoginResult(
                success=False,
                message="This simulation is currently locked. Contact your instructor.",
            )

    dashboard = role_dashboard(role)

    user = AuthUser(
        username=user_row.get("username", username),
        user_id=user_row.get("user_id", ""),
        team_id=user_row.get("team_id", ""),
        role=role,
        sim_id=sim_id,
        first_name=user_row.get("first_name", ""),
        last_name=user_row.get("last_name", ""),
        email=user_row.get("email", ""),
        dashboard=dashboard,
    )

    needs_picker = len(sim_ids) > 1 and dashboard == "admin"

    return LoginResult(
        success=True,
        user=user,
        sim_ids=sim_ids,
        needs_sim_picker=needs_picker,
        message=f"Welcome, {user.username}",
    )
