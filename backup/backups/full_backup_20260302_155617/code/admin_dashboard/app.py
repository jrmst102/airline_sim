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
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

DEFAULT_SIM_ID = "sim_001"


# ── Helpers ────────────────────────────────────────────────────────────

def _redirect_with_banner(success: bool, message: str) -> RedirectResponse:
    """Redirect to /admin with a flash-style banner via query params."""
    params = urlencode({"msg": message, "ok": "1" if success else "0"})
    return RedirectResponse(url=f"/admin?{params}", status_code=303)


def _render_admin(request: Request, msg: str = "", ok: bool = True) -> HTMLResponse:
    """Render the admin home page with optional banner."""
    sim_status = get_simulation_status(DEFAULT_SIM_ID)
    team_data = get_team_table(DEFAULT_SIM_ID)
    decision_status = get_decision_status(DEFAULT_SIM_ID)
    team_history = get_team_history(DEFAULT_SIM_ID)
    template = _jinja_env.get_template("admin_home.html")
    html = template.render(
        sim_status=sim_status,
        team_data=team_data,
        decision_status=decision_status,
        team_history=team_history,
        msg=msg,
        ok=ok,
        sim_id=DEFAULT_SIM_ID,
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
    sim_name: str = Form("Airline Simulation"),
    total_rounds: int = Form(3),
):
    """Set up (initialise) the simulation."""
    result = action_setup(
        simulation_id=DEFAULT_SIM_ID,
        simulation_name=sim_name,
        total_rounds=total_rounds,
    )
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/start")
async def admin_start():
    """Start the simulation."""
    result = action_start(simulation_id=DEFAULT_SIM_ID)
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/end")
async def admin_end():
    """End the simulation."""
    result = action_end(simulation_id=DEFAULT_SIM_ID)
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/next-round")
async def admin_next_round():
    """Process current round and advance to the next."""
    result = action_move_next_round(simulation_id=DEFAULT_SIM_ID)
    return _redirect_with_banner(result["success"], result["message"])


@app.post("/admin/undo")
async def admin_undo():
    """Undo the last round transition."""
    result = action_undo(simulation_id=DEFAULT_SIM_ID)
    return _redirect_with_banner(result["success"], result["message"])


@app.get("/api/admin/status")
async def api_status():
    """JSON endpoint for simulation status (for AJAX refresh)."""
    return get_simulation_status(DEFAULT_SIM_ID)


@app.get("/api/admin/teams")
async def api_teams():
    """JSON endpoint for team data table (for AJAX refresh)."""
    return get_team_table(DEFAULT_SIM_ID)


@app.get("/api/admin/decisions")
async def api_decisions():
    """JSON endpoint for decision submission status (for AJAX polling)."""
    data = get_decision_status(DEFAULT_SIM_ID)
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


@app.get("/admin/report", response_class=HTMLResponse)
async def admin_report():
    """Render a printable final results report in a new window."""
    from datetime import datetime, timezone

    data = get_report_data(DEFAULT_SIM_ID)
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
