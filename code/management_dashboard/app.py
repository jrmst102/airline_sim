"""
Management Dashboard – standalone FastAPI app for simulation & user management.
================================================================================
Provides a self-contained interface (separate from the admin game dashboard)
for creating/removing simulations and managing user accounts across all
simulations on the platform.

Has its own login gate (accepts any ADMIN-role user from any active simulation).

Run with::

    python run_management_dashboard.py               # default http://0.0.0.0:8090
    python run_management_dashboard.py --port 9000   # custom port
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer
from jinja2 import Environment, FileSystemLoader

from app.auth.password_manager import verify_password
from app.modules.simulation_management import (
    create_simulation,
    list_simulations,
    lock_simulation,
    unlock_simulation,
    remove_simulation,
)
from app.modules.user_management import (
    list_users,
    create_user,
    change_password,
    change_role,
    set_user_lock,
    remove_user,
)

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_LOGO_PATH = _PROJECT_ROOT / "app" / "images" / "sim_logo.png"
_TEMPLATES_DIR = _THIS_DIR / "templates"
_STATIC_DIR = _THIS_DIR / "static"

# ── Jinja2 ─────────────────────────────────────────────────────────────
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
)

# ── FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(title="Airlines Management Dashboard", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ── Session ────────────────────────────────────────────────────────────
SESSION_SECRET = os.environ.get("SESSION_SECRET", "airline-sim-dev-secret")
_signer = URLSafeSerializer(SESSION_SECRET, salt="mgmt-session")
COOKIE_NAME = "mgmt_session"

# ── Superadmin credentials ─────────────────────────────────────────────
SUPERADMIN_USERNAME = "admin"
SUPERADMIN_HASH = "$2b$12$QMJY0eV/s0FogV39dGlVpuWnbkmeWAohiedRsGiNBQ/TEmcCRo03."


def _get_session(request: Request) -> dict | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        return _signer.loads(raw)
    except Exception:
        return None


def _set_session(response, data: dict):
    value = _signer.dumps(data)
    response.set_cookie(
        COOKIE_NAME, value, httponly=True, samesite="lax", max_age=86400,
    )
    return response


def _require_admin(request: Request) -> dict | None:
    """Return session dict if user is the superadmin, else None."""
    session = _get_session(request)
    if session and session.get("role") == "SUPERADMIN":
        return session
    return None


# ── Helpers ────────────────────────────────────────────────────────────

def _redirect_login():
    return RedirectResponse(url="/mgmt/login", status_code=302)


def _redirect_sims(success: bool, message: str):
    params = urlencode({"msg": message, "ok": "1" if success else "0"})
    return RedirectResponse(url=f"/mgmt/simulations?{params}", status_code=303)


def _redirect_users(sim_id: str, success: bool, message: str):
    params = urlencode({"msg": message, "ok": "1" if success else "0"})
    return RedirectResponse(url=f"/mgmt/users/{sim_id}?{params}", status_code=303)


# ── Logo ───────────────────────────────────────────────────────────────

@app.get("/logo.png")
async def logo():
    if _LOGO_PATH.exists():
        return FileResponse(str(_LOGO_PATH), media_type="image/png")
    return HTMLResponse(content="", status_code=404)


# ── Login ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/mgmt/simulations", status_code=302)


@app.get("/mgmt/login", response_class=HTMLResponse)
async def login_page(request: Request, msg: str = "", ok: str = "1"):
    session = _get_session(request)
    if session and session.get("role") == "SUPERADMIN":
        return RedirectResponse(url="/mgmt/simulations", status_code=302)
    template = _jinja_env.get_template("mgmt_login.html")
    html = template.render(msg=msg, ok=(ok == "1"))
    return HTMLResponse(content=html)


@app.post("/mgmt/login")
async def login_submit(
    username: str = Form(...),
    password: str = Form(...),
):
    if username.strip().lower() != SUPERADMIN_USERNAME or not verify_password(password, SUPERADMIN_HASH):
        params = urlencode({"msg": "Invalid username or password.", "ok": "0"})
        return RedirectResponse(url=f"/mgmt/login?{params}", status_code=303)

    session_data = {
        "username": SUPERADMIN_USERNAME,
        "role": "SUPERADMIN",
    }
    resp = RedirectResponse(url="/mgmt/simulations", status_code=303)
    return _set_session(resp, session_data)


@app.get("/mgmt/logout")
async def logout():
    resp = RedirectResponse(url="/mgmt/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ── Simulations ────────────────────────────────────────────────────────

@app.get("/mgmt/simulations", response_class=HTMLResponse)
async def simulations_page(request: Request, msg: str = "", ok: str = "1"):
    session = _require_admin(request)
    if not session:
        return _redirect_login()

    sims = list_simulations()
    template = _jinja_env.get_template("mgmt_simulations.html")
    html = template.render(
        sims=sims,
        username=session.get("username", ""),
        msg=msg,
        ok=(ok == "1"),
    )
    return HTMLResponse(content=html)


@app.post("/mgmt/simulations/create")
async def create_sim(
    request: Request,
    sim_id: str = Form(...),
    sim_name: str = Form(...),
    total_rounds: int = Form(3),
    num_teams: int = Form(5),
    admin_user: str = Form(""),
    admin_pass: str = Form(""),
):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    try:
        result = create_simulation(
            simulation_id=sim_id,
            name=sim_name,
            total_rounds=total_rounds,
            num_teams=num_teams,
            admin_username=admin_user or "",
            admin_password=admin_pass or "",
            auto_create_teams=True,
        )
        cred_lines = [f"{c.role}: {c.username} / {c.password}" for c in result.credentials]
        message = f"Simulation '{result.simulation_id}' created. Credentials: " + " | ".join(cred_lines)
        return _redirect_sims(True, message)
    except Exception as exc:
        logger.exception("Create simulation failed")
        return _redirect_sims(False, f"Create failed: {exc}")


@app.post("/mgmt/simulations/lock")
async def lock_sim(request: Request, sim_id: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    result = lock_simulation(sim_id)
    return _redirect_sims(result["success"], result["message"])


@app.post("/mgmt/simulations/unlock")
async def unlock_sim(request: Request, sim_id: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    result = unlock_simulation(sim_id)
    return _redirect_sims(result["success"], result["message"])


@app.post("/mgmt/simulations/remove")
async def remove_sim(request: Request, sim_id: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    result = remove_simulation(sim_id)
    return _redirect_sims(result["success"], result["message"])


# ── Users ──────────────────────────────────────────────────────────────

@app.get("/mgmt/users/{sim_id}", response_class=HTMLResponse)
async def users_page(request: Request, sim_id: str, msg: str = "", ok: str = "1"):
    session = _require_admin(request)
    if not session:
        return _redirect_login()

    users = list_users(sim_id)
    template = _jinja_env.get_template("mgmt_users.html")
    html = template.render(
        users=users,
        sim_id=sim_id,
        username=session.get("username", ""),
        msg=msg,
        ok=(ok == "1"),
    )
    return HTMLResponse(content=html)


@app.post("/mgmt/users/{sim_id}/create")
async def create_user_route(
    request: Request,
    sim_id: str,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("USER"),
    team_id: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    try:
        create_user(
            simulation_id=sim_id,
            username=username,
            password=password,
            role=role,
            team_id=team_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        return _redirect_users(sim_id, True, f"User '{username}' created.")
    except Exception as exc:
        return _redirect_users(sim_id, False, f"Create failed: {exc}")


@app.post("/mgmt/users/{sim_id}/change-password")
async def change_password_route(
    request: Request,
    sim_id: str,
    username: str = Form(...),
    new_password: str = Form(...),
):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    try:
        change_password(simulation_id=sim_id, username=username, new_password=new_password)
        return _redirect_users(sim_id, True, f"Password changed for '{username}'.")
    except Exception as exc:
        return _redirect_users(sim_id, False, f"Password change failed: {exc}")


@app.post("/mgmt/users/{sim_id}/change-role")
async def change_role_route(
    request: Request,
    sim_id: str,
    username: str = Form(...),
    new_role: str = Form(...),
    new_team_id: str = Form(""),
):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    try:
        change_role(
            simulation_id=sim_id,
            username=username,
            new_role=new_role,
            new_team_id=new_team_id,
        )
        return _redirect_users(sim_id, True, f"Role changed for '{username}' to {new_role}.")
    except Exception as exc:
        return _redirect_users(sim_id, False, f"Role change failed: {exc}")


@app.post("/mgmt/users/{sim_id}/lock")
async def lock_user_route(request: Request, sim_id: str, username: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    try:
        set_user_lock(simulation_id=sim_id, username=username, is_locked=True)
        return _redirect_users(sim_id, True, f"User '{username}' locked.")
    except Exception as exc:
        return _redirect_users(sim_id, False, f"Lock failed: {exc}")


@app.post("/mgmt/users/{sim_id}/unlock")
async def unlock_user_route(request: Request, sim_id: str, username: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    try:
        set_user_lock(simulation_id=sim_id, username=username, is_locked=False)
        return _redirect_users(sim_id, True, f"User '{username}' unlocked.")
    except Exception as exc:
        return _redirect_users(sim_id, False, f"Unlock failed: {exc}")


@app.post("/mgmt/users/{sim_id}/remove")
async def remove_user_route(request: Request, sim_id: str, username: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return _redirect_login()
    result = remove_user(simulation_id=sim_id, username=username)
    return _redirect_users(sim_id, result["success"], result["message"])
