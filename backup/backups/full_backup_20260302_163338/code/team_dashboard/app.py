"""
Team Dashboard – FastAPI backend for team-facing simulation UI.
================================================================
Provides login, decision entry (save / undo), past-decisions view,
and performance display.  All data I/O goes through the Spaces-backed
CSV manager.

Session management uses ``itsdangerous`` signed cookies – no external
session store is needed.

Run with::

    python run_team_dashboard.py                # default http://0.0.0.0:8081
    python run_team_dashboard.py --port 8082    # custom port
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

from team_dashboard.services.team_auth import login as auth_login
from team_dashboard.services.team_decisions import (
    get_decision_defaults,
    get_past_decisions,
    get_simulation_state,
    save_decision,
    undo_decision,
)
from team_dashboard.services.team_performance import (
    get_team_name,
    get_team_performance,
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

# ── Session ────────────────────────────────────────────────────────────
SESSION_SECRET = os.environ.get("SESSION_SECRET", "airline-sim-dev-secret")
_signer = URLSafeSerializer(SESSION_SECRET, salt="team-session")
COOKIE_NAME = "team_session"

# ── FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(title="Airlines Team Dashboard", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

DEFAULT_SIM_ID = "sim_001"


# ── Session helpers ────────────────────────────────────────────────────

def _set_session(response: RedirectResponse, data: dict) -> RedirectResponse:
    """Attach a signed session cookie."""
    value = _signer.dumps(data)
    response.set_cookie(
        COOKIE_NAME,
        value,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
    )
    return response


def _get_session(request: Request) -> dict | None:
    """Read and verify the signed session cookie."""
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        return _signer.loads(raw)
    except Exception:
        return None


def _clear_session(response: RedirectResponse) -> RedirectResponse:
    """Delete the session cookie."""
    response.delete_cookie(COOKIE_NAME)
    return response


# ── Redirect helper ───────────────────────────────────────────────────

def _redirect_team(msg: str = "", ok: bool = True) -> RedirectResponse:
    """Redirect to /team with optional banner params."""
    if msg:
        params = urlencode({"msg": msg, "ok": "1" if ok else "0"})
        return RedirectResponse(url=f"/team?{params}", status_code=303)
    return RedirectResponse(url="/team", status_code=303)


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Lightweight health check for App Platform / load balancers."""
    return {"status": "ok"}


@app.get("/team/state")
async def team_state(request: Request):
    """Lightweight JSON endpoint for client-side polling.

    Returns the current simulation state so the browser can detect
    changes (e.g. simulation started, round advanced) and auto-refresh.
    Requires a valid session cookie.
    """
    session = _get_session(request)
    if not session:
        return {"error": "unauthenticated"}
    sim_id = session.get("sim_id", DEFAULT_SIM_ID)
    state = get_simulation_state(sim_id)
    return {
        "status": state["status"],
        "current_round": state["current_round"],
        "is_started": state["is_started"],
        "is_ended": state["is_ended"],
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/team/login", status_code=302)


# ── Login ──────────────────────────────────────────────────────────────

@app.get("/team/login", response_class=HTMLResponse)
async def login_page(request: Request, msg: str = "", ok: str = "1"):
    """Render the login form."""
    # If already logged in, redirect to /team
    session = _get_session(request)
    if session:
        return RedirectResponse(url="/team", status_code=302)
    template = _jinja_env.get_template("team_login.html")
    html = template.render(msg=msg, ok=(ok == "1"))
    return HTMLResponse(content=html)


@app.post("/team/login")
async def login_submit(
    username: str = Form(...),
    password: str = Form(...),
):
    """Validate credentials and set session cookie."""
    result = auth_login(
        simulation_id=DEFAULT_SIM_ID,
        username=username,
        password=password,
    )
    if not result["success"]:
        params = urlencode({"msg": result["message"], "ok": "0"})
        return RedirectResponse(url=f"/team/login?{params}", status_code=303)

    user = result["user"]
    session_data = {
        "username": user.username,
        "team_id": user.team_id,
        "role": user.role,
        "sim_id": DEFAULT_SIM_ID,
    }

    # Route by role: admin → /admin, team → /team
    if user.role == "admin":
        dest = "/admin"
    else:
        dest = "/team"

    resp = RedirectResponse(url=dest, status_code=303)
    return _set_session(resp, session_data)


# ── Logout ─────────────────────────────────────────────────────────────

@app.get("/team/logout")
async def logout():
    resp = RedirectResponse(url="/team/login", status_code=302)
    return _clear_session(resp)


# ── Team Home (protected) ─────────────────────────────────────────────

@app.get("/team", response_class=HTMLResponse)
async def team_home(request: Request, msg: str = "", ok: str = "1"):
    """Main team page: status, decision form, past decisions, performance."""
    session = _get_session(request)
    if not session:
        return RedirectResponse(url="/team/login", status_code=302)

    sim_id = session.get("sim_id", DEFAULT_SIM_ID)
    team_id = session.get("team_id", "")
    username = session.get("username", "")

    # Gather data
    sim_state = get_simulation_state(sim_id)
    team_name = get_team_name(sim_id, team_id)
    defaults = get_decision_defaults(
        sim_id, team_id,
        sim_state["current_round"],
        sim_state["is_started"],
    )
    past = get_past_decisions(
        sim_id, team_id,
        sim_state["current_round"],
        sim_state["is_started"],
    )
    perf = get_team_performance(sim_id, team_id)

    template = _jinja_env.get_template("team_home.html")
    html = template.render(
        username=username,
        team_id=team_id,
        team_name=team_name,
        sim_state=sim_state,
        defaults=defaults,
        past_decisions=past,
        perf=perf,
        msg=msg,
        ok=(ok == "1"),
    )
    return HTMLResponse(content=html)


# ── Save decision ─────────────────────────────────────────────────────

@app.post("/team/save")
async def team_save(
    request: Request,
    flights_per_day: int = Form(...),
    price_business: float = Form(...),
    price_leisure: float = Form(...),
    branding_level: str = Form(...),
    product_strategy: str = Form(...),
):
    session = _get_session(request)
    if not session:
        return RedirectResponse(url="/team/login", status_code=302)

    sim_id = session.get("sim_id", DEFAULT_SIM_ID)
    team_id = session.get("team_id", "")

    result = save_decision(
        simulation_id=sim_id,
        team_id=team_id,
        flights_per_day=flights_per_day,
        price_business=price_business,
        price_leisure=price_leisure,
        branding_level=branding_level,
        product_strategy=product_strategy,
    )
    return _redirect_team(result["message"], result["success"])


# ── Undo decision ─────────────────────────────────────────────────────

@app.post("/team/undo")
async def team_undo(request: Request):
    session = _get_session(request)
    if not session:
        return RedirectResponse(url="/team/login", status_code=302)

    sim_id = session.get("sim_id", DEFAULT_SIM_ID)
    team_id = session.get("team_id", "")

    result = undo_decision(simulation_id=sim_id, team_id=team_id)
    return _redirect_team(result["message"], result["success"])


# ── Logo ───────────────────────────────────────────────────────────────

@app.get("/logo.png")
async def logo():
    if _LOGO_PATH.exists():
        return FileResponse(str(_LOGO_PATH), media_type="image/png")
    return HTMLResponse(content="", status_code=404)
