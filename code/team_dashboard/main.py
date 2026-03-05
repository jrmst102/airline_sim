"""
Unified entry point for DigitalOcean App Platform.
====================================================
Creates a single FastAPI application that serves both the Team Dashboard
and the Admin Dashboard behind a shared login page.

- ``/`` and ``/team/login`` → login form (shared by admin & team users)
- Admin credentials → redirected to ``/admin``
- Team credentials  → redirected to ``/team``

Run command (App Platform / Procfile)::

    uvicorn code.team_dashboard.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent          # code/team_dashboard/
_CODE_DIR = _THIS_DIR.parent                         # code/
_PROJECT_ROOT = _CODE_DIR.parent                     # repo root

for p in (_CODE_DIR, _PROJECT_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# ── Build the unified FastAPI app ──────────────────────────────────────
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer

# Import sub-apps (their routes get mounted below)
from team_dashboard.app import app as team_app, COOKIE_NAME
from admin_dashboard.app import app as admin_app

# ── Unified app ────────────────────────────────────────────────────────
app = FastAPI(title="Airlines Simulation", docs_url=None, redoc_url=None)

# Session signer (same secret / salt as team_dashboard.app)
SESSION_SECRET = os.environ.get("SESSION_SECRET", "airline-sim-dev-secret")
_signer = URLSafeSerializer(SESSION_SECRET, salt="team-session")

# ── Static files: serve both admin and team CSS from /static/ ──────────
# Both apps reference /static/<file>.css with different filenames
# (admin.css, team.css).  Create a combined static directory so a
# single /static mount can serve both.
import shutil

_ADMIN_STATIC = _CODE_DIR / "admin_dashboard" / "static"
_TEAM_STATIC  = _CODE_DIR / "team_dashboard" / "static"
_COMBINED_STATIC = _CODE_DIR / "_combined_static"
_COMBINED_STATIC.mkdir(exist_ok=True)

for src_dir in (_ADMIN_STATIC, _TEAM_STATIC):
    if src_dir.is_dir():
        for f in src_dir.iterdir():
            if f.is_file():
                dest = _COMBINED_STATIC / f.name
                # Always refresh so edits during --reload are picked up
                shutil.copy2(f, dest)

app.mount("/static", StaticFiles(directory=str(_COMBINED_STATIC)), name="static")


def _get_session(request: Request) -> dict | None:
    """Read and verify the session cookie."""
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        return _signer.loads(raw)
    except Exception:
        return None


# ── Admin session guard ────────────────────────────────────────────────
from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware


class AdminGuardMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated / non-admin users away from /admin*."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Guard /admin routes and /api/admin routes
        if path.startswith("/admin") or path.startswith("/api/admin"):
            session = _get_session(request)
            if not session or session.get("role") != "admin":
                # For API routes return 401 JSON; for pages redirect
                if path.startswith("/api/"):
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        {"error": "unauthenticated"}, status_code=401
                    )
                return RedirectResponse(url="/team/login", status_code=302)
        return await call_next(request)


app.add_middleware(AdminGuardMiddleware)

# ── Mount all routes from both sub-apps ────────────────────────────────
# We include routes from both FastAPI apps into the unified app.
for route in team_app.routes:
    # Skip the static mount (we handle it above) and root redirect
    if hasattr(route, "path"):
        if route.path == "/static" or getattr(route, "name", "") in ("static",):
            continue
    app.routes.append(route)

for route in admin_app.routes:
    # Skip admin's static mount and logo (team already has /logo.png)
    if hasattr(route, "path"):
        if route.path == "/static" or getattr(route, "name", "") in ("static",):
            continue
        if route.path == "/logo.png":
            continue
        # Skip admin's root / redirect (team app handles /)
        if route.path == "/" and getattr(route, "name", "") == "root":
            continue
    app.routes.append(route)

__all__ = ["app"]
