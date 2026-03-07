"""
Admin Dashboard – FastAPI backend for the Airline Simulation admin panel.
==========================================================================
Provides admin actions (Setup, Start, End, Undo) and a live team-data
table.  All data I/O goes through the centralised storage layer
(DigitalOcean Spaces or local filesystem fallback).

Run with::

    python run_admin_dashboard.py                # default http://0.0.0.0:8080
    python run_admin_dashboard.py --port 8090    # custom port
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer
from jinja2 import Environment, FileSystemLoader

from admin_dashboard.services.admin_actions import (
    action_end,
    action_move_next_round,
    action_setup,
    action_start,
    action_undo,
)
from admin_dashboard.services.team_data import (
    get_decision_status,
    get_report_data,
    get_simulation_status,
    get_team_table,
    get_team_history,
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
app = FastAPI(title="Airlines Admin Dashboard", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ── Session ────────────────────────────────────────────────────────────
SESSION_SECRET = os.environ.get("SESSION_SECRET", "airline-sim-dev-secret")
_signer = URLSafeSerializer(SESSION_SECRET, salt="team-session")
COOKIE_NAME = "team_session"


def _get_session(request: Request) -> dict | None:
    """Read and verify the signed session cookie."""
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        return _signer.loads(raw)
    except Exception:
        return None


def _sim_id_from(request: Request) -> str:
    """Extract sim_id from the session; raises if no session."""
    session = _get_session(request)
    if session:
        sid = session.get("sim_id", "")
        if sid:
            return sid
    raise ValueError("No simulation selected — please log in.")


# ── Helpers ────────────────────────────────────────────────────────────

def _redirect_with_banner(success: bool, message: str) -> RedirectResponse:
    """Redirect to /admin with a flash-style banner via query params."""
    params = urlencode({"msg": message, "ok": "1" if success else "0"})
    return RedirectResponse(url=f"/admin?{params}", status_code=303)


def _render_admin(request: Request, msg: str = "", ok: bool = True) -> HTMLResponse:
    """Render the admin home page with optional banner."""
    sim_id = _sim_id_from(request)
    session = _get_session(request)
    sim_ids = session.get("sim_ids", [sim_id]) if session else [sim_id]
    sim_status = get_simulation_status(sim_id)
    team_data = get_team_table(sim_id)
    decision_status = get_decision_status(sim_id)
    team_history = get_team_history(sim_id)
    template = _jinja_env.get_template("admin_home.html")
    html = template.render(
        sim_status=sim_status,
        team_data=team_data,
        decision_status=decision_status,
        team_history=team_history,
        msg=msg,
        ok=ok,
        sim_id=sim_id,
        sim_ids=sim_ids,
    )
    return HTMLResponse(content=html)


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect root to /admin."""
    return RedirectResponse(url="/admin", status_code=302)


@app.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request, msg: str = "", ok: str = "1"):
    """Render the admin dashboard page."""
    return _render_admin(request, msg=msg, ok=(ok == "1"))


@app.post("/admin/setup")
async def admin_setup(
    request: Request,
    sim_name: str = Form("Airline Simulation"),
    total_rounds: int = Form(3),
):
    """Set up (initialise) the simulation."""
    sim_id = _sim_id_from(request)
    result = action_setup(
        simulation_id=sim_id,
        simulation_name=sim_name,
        total_rounds=total_rounds,
    )
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/start")
async def admin_start(request: Request):
    """Start the simulation."""
    sim_id = _sim_id_from(request)
    result = action_start(simulation_id=sim_id)
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/end")
async def admin_end(request: Request):
    """End the simulation."""
    sim_id = _sim_id_from(request)
    result = action_end(simulation_id=sim_id)
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/next-round")
async def admin_next_round(request: Request):
    """Process current round and advance to the next."""
    sim_id = _sim_id_from(request)
    result = action_move_next_round(simulation_id=sim_id)
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/undo")
async def admin_undo(request: Request):
    """Undo the last round transition."""
    sim_id = _sim_id_from(request)
    result = action_undo(simulation_id=sim_id)
    return _redirect_with_banner(result["success"], result["message"])


@app.get("/api/admin/status")
async def api_status(request: Request):
    """JSON endpoint for simulation status (for AJAX refresh)."""
    sim_id = _sim_id_from(request)
    return get_simulation_status(sim_id)


@app.get("/api/admin/teams")
async def api_teams(request: Request):
    """JSON endpoint for team data table (for AJAX refresh)."""
    sim_id = _sim_id_from(request)
    return get_team_table(sim_id)


@app.get("/api/admin/decisions")
async def api_decisions(request: Request):
    """JSON endpoint for decision submission status (for AJAX polling)."""
    sim_id = _sim_id_from(request)
    data = get_decision_status(sim_id)
    return JSONResponse(
        content=data,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/logo.png")
async def logo():
    """Serve the simulation logo."""
    if _LOGO_PATH.exists():
        return FileResponse(str(_LOGO_PATH), media_type="image/png")
    # 1×1 transparent pixel fallback
    return HTMLResponse(content="", status_code=404)


# ── Simulation picker & switcher ───────────────────────────────────────

def _set_session(response, data: dict):
    """Attach a signed session cookie (mirrors team_dashboard helper)."""
    value = _signer.dumps(data)
    response.set_cookie(
        COOKIE_NAME, value, httponly=True, samesite="lax", max_age=86400,
    )
    return response


@app.get("/admin/select-sim", response_class=HTMLResponse)
async def select_sim_page(request: Request):
    """Show a simulation picker when the admin belongs to multiple sims."""
    session = _get_session(request)
    if not session:
        return RedirectResponse(url="/team/login", status_code=302)
    sim_ids = session.get("sim_ids", [])
    if len(sim_ids) <= 1:
        return RedirectResponse(url="/admin", status_code=302)

    # Fetch display info for each sim
    from app.auth.login_manager import get_all_simulations
    all_sims = {s["simulation_id"]: s for s in get_all_simulations()}
    sims = []
    for sid in sim_ids:
        info = all_sims.get(sid, {})
        sims.append({
            "id": sid,
            "name": info.get("name", sid),
            "status": info.get("status", ""),
        })

    template = _jinja_env.get_template("select_sim.html")
    html = template.render(sims=sims)
    return HTMLResponse(content=html)


@app.post("/admin/switch-sim")
async def switch_sim(request: Request, sim_id: str = Form(...)):
    """Switch the admin's active simulation (updates the session cookie)."""
    session = _get_session(request)
    if not session:
        return RedirectResponse(url="/team/login", status_code=302)

    allowed = session.get("sim_ids", [])
    if sim_id not in allowed:
        return _redirect_with_banner(False, f"You don't have access to '{sim_id}'.")

    session["sim_id"] = sim_id
    resp = RedirectResponse(url="/admin", status_code=303)
    return _set_session(resp, session)


@app.get("/admin/report", response_class=HTMLResponse)
async def admin_report(request: Request):
    """Render a printable final results report in a new window."""
    from datetime import datetime, timezone

    sim_id = _sim_id_from(request)
    data = get_report_data(sim_id)
    template = _jinja_env.get_template("report.html")
    html = template.render(
        simulation=data["simulation"],
        final_results=data["final_results"],
        decisions_history=data["decisions_history"],
        performance_history=data["performance_history"],
        rounds=data["rounds"],
        team_names=data["team_names"],
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    return HTMLResponse(content=html)


# ── Simulation Management ──────────────────────────────────────────────

@app.get("/admin/simulations", response_class=HTMLResponse)
async def admin_simulations(request: Request, msg: str = "", ok: str = "1"):
    """List all simulations with management controls."""
    from app.modules.simulation_management import list_simulations

    session = _get_session(request)
    sims = list_simulations()
    template = _jinja_env.get_template("simulations.html")
    html = template.render(
        sims=sims,
        sim_id=_sim_id_from(request),
        sim_ids=session.get("sim_ids", []) if session else [],
        msg=msg,
        ok=(ok == "1"),
    )
    return HTMLResponse(content=html)


@app.post("/admin/simulations/create")
async def admin_create_sim(
    request: Request,
    sim_id: str = Form(...),
    sim_name: str = Form(...),
    total_rounds: int = Form(3),
    admin_user: str = Form(""),
    admin_pass: str = Form(""),
):
    """Create a new simulation with user accounts."""
    from app.modules.simulation_management import create_simulation

    try:
        result = create_simulation(
            simulation_id=sim_id,
            name=sim_name,
            total_rounds=total_rounds,
            admin_username=admin_user or "",
            admin_password=admin_pass or "",
            auto_create_teams=True,
        )
        # Add the new sim to the admin's session
        session = _get_session(request)
        if session:
            sim_ids = session.get("sim_ids", [])
            if result.simulation_id not in sim_ids:
                sim_ids.append(result.simulation_id)
                session["sim_ids"] = sim_ids
            # Switch to the new sim
            session["sim_id"] = result.simulation_id
            params = urlencode({
                "msg": f"Simulation '{result.simulation_id}' created.",
                "ok": "1",
            })
            resp = RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)
            return _set_session(resp, session)

        params = urlencode({
            "msg": f"Simulation '{result.simulation_id}' created.",
            "ok": "1",
        })
        return RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)
    except Exception as exc:
        logger.exception("Create simulation failed")
        params = urlencode({"msg": f"Create failed: {exc}", "ok": "0"})
        return RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)


@app.post("/admin/simulations/lock")
async def admin_lock_sim(request: Request, sim_id: str = Form(...)):
    """Lock a simulation."""
    from app.modules.simulation_management import lock_simulation

    result = lock_simulation(sim_id)
    params = urlencode({"msg": result["message"], "ok": "1" if result["success"] else "0"})
    return RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)


@app.post("/admin/simulations/unlock")
async def admin_unlock_sim(request: Request, sim_id: str = Form(...)):
    """Unlock a simulation."""
    from app.modules.simulation_management import unlock_simulation

    result = unlock_simulation(sim_id)
    params = urlencode({"msg": result["message"], "ok": "1" if result["success"] else "0"})
    return RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)


@app.post("/admin/simulations/remove")
async def admin_remove_sim(request: Request, sim_id: str = Form(...)):
    """Remove a simulation permanently."""
    from app.modules.simulation_management import remove_simulation

    result = remove_simulation(sim_id)
    if result["success"]:
        # Remove from session's sim_ids
        session = _get_session(request)
        if session:
            sim_ids = session.get("sim_ids", [])
            if sim_id in sim_ids:
                sim_ids.remove(sim_id)
                session["sim_ids"] = sim_ids
            # If we removed the active sim, switch to first remaining
            if session.get("sim_id") == sim_id and sim_ids:
                session["sim_id"] = sim_ids[0]
            params = urlencode({"msg": result["message"], "ok": "1"})
            resp = RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)
            return _set_session(resp, session)

    params = urlencode({"msg": result["message"], "ok": "1" if result["success"] else "0"})
    return RedirectResponse(url=f"/admin/simulations?{params}", status_code=303)


# ── User Management ───────────────────────────────────────────────────

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, msg: str = "", ok: str = "1"):
    """List all users in the current simulation."""
    from app.modules.user_management import list_users

    session = _get_session(request)
    if not session:
        return RedirectResponse(url="/team/login", status_code=302)
    sim_id = _sim_id_from(request)

    users = list_users(sim_id)
    template = _jinja_env.get_template("manage_users.html")
    html = template.render(
        users=users,
        sim_id=sim_id,
        sim_ids=session.get("sim_ids", []),
        msg=msg,
        ok=(ok == "1"),
        role=session.get("role", ""),
    )
    return HTMLResponse(content=html)


@app.post("/admin/users/create")
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("USER"),
    team_id: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    school_id: str = Form(""),
    course_id: str = Form(""),
):
    """Create a new user in the current simulation."""
    from app.modules.user_management import create_user

    sim_id = _sim_id_from(request)
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
            school_id=school_id,
            course_id=course_id,
        )
        params = urlencode({"msg": f"User '{username}' created.", "ok": "1"})
    except Exception as exc:
        params = urlencode({"msg": f"Create failed: {exc}", "ok": "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)


@app.post("/admin/users/edit")
async def admin_edit_user(
    request: Request,
    username: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    school_id: str = Form(""),
    course_id: str = Form(""),
):
    """Edit a user's profile fields."""
    from app.modules.user_management import edit_user

    sim_id = _sim_id_from(request)
    try:
        edit_user(
            simulation_id=sim_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            school_id=school_id,
            course_id=course_id,
        )
        params = urlencode({"msg": f"User '{username}' updated.", "ok": "1"})
    except Exception as exc:
        params = urlencode({"msg": f"Edit failed: {exc}", "ok": "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)


@app.post("/admin/users/lock")
async def admin_lock_user(request: Request, username: str = Form(...)):
    """Lock a user account."""
    from app.modules.user_management import set_user_lock

    sim_id = _sim_id_from(request)
    try:
        set_user_lock(simulation_id=sim_id, username=username, is_locked=True)
        params = urlencode({"msg": f"User '{username}' locked.", "ok": "1"})
    except Exception as exc:
        params = urlencode({"msg": f"Lock failed: {exc}", "ok": "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)


@app.post("/admin/users/unlock")
async def admin_unlock_user(request: Request, username: str = Form(...)):
    """Unlock a user account."""
    from app.modules.user_management import set_user_lock

    sim_id = _sim_id_from(request)
    try:
        set_user_lock(simulation_id=sim_id, username=username, is_locked=False)
        params = urlencode({"msg": f"User '{username}' unlocked.", "ok": "1"})
    except Exception as exc:
        params = urlencode({"msg": f"Unlock failed: {exc}", "ok": "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)


@app.post("/admin/users/change-password")
async def admin_change_password(
    request: Request,
    username: str = Form(...),
    new_password: str = Form(...),
):
    """Change a user's password."""
    from app.modules.user_management import change_password

    sim_id = _sim_id_from(request)
    try:
        change_password(simulation_id=sim_id, username=username, new_password=new_password)
        params = urlencode({"msg": f"Password changed for '{username}'.", "ok": "1"})
    except Exception as exc:
        params = urlencode({"msg": f"Password change failed: {exc}", "ok": "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)


@app.post("/admin/users/change-role")
async def admin_change_role(
    request: Request,
    username: str = Form(...),
    new_role: str = Form(...),
    new_team_id: str = Form(""),
):
    """Change a user's role."""
    from app.modules.user_management import change_role

    sim_id = _sim_id_from(request)
    try:
        change_role(
            simulation_id=sim_id,
            username=username,
            new_role=new_role,
            new_team_id=new_team_id,
        )
        params = urlencode({"msg": f"Role changed for '{username}' to {new_role}.", "ok": "1"})
    except Exception as exc:
        params = urlencode({"msg": f"Role change failed: {exc}", "ok": "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)


@app.post("/admin/users/remove")
async def admin_remove_user(request: Request, username: str = Form(...)):
    """Remove a user from the current simulation."""
    from app.modules.user_management import remove_user

    sim_id = _sim_id_from(request)
    result = remove_user(simulation_id=sim_id, username=username)
    params = urlencode({"msg": result["message"], "ok": "1" if result["success"] else "0"})
    return RedirectResponse(url=f"/admin/users?{params}", status_code=303)
