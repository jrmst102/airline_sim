"""
Dashboard Web – FastAPI backend for the Airline Simulation dashboard.
======================================================================
Serves a single HTML page and a REST endpoint for dashboard data.

Run with:
    cd dashboard_web && uvicorn app:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from dashboard_data import get_dashboard_data

# ── Paths ──────────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
_SIM_PATH = _PROJECT_ROOT / "simulations" / "sim_001"
_LOGO_PATH = _PROJECT_ROOT / "app" / "images" / "sim_logo.png"
_TEMPLATES_DIR = _THIS_DIR / "templates"
_STATIC_DIR = _THIS_DIR / "static"

# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(title="Airlines Dashboard", docs_url=None, redoc_url=None)

# Mount static files
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard HTML page."""
    html_path = _TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/dashboard")
async def api_dashboard():
    """Return dashboard data as JSON."""
    return get_dashboard_data(sim_path=_SIM_PATH)


@app.get("/logo.png")
async def logo():
    """Serve the simulation logo."""
    if _LOGO_PATH.exists():
        return FileResponse(str(_LOGO_PATH), media_type="image/png")
    # Return a 1x1 transparent PNG if logo doesn't exist
    return FileResponse(str(_LOGO_PATH), media_type="image/png")
