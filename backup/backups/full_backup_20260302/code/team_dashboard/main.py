"""
Entry point for DigitalOcean App Platform (and local ``uvicorn`` usage).
========================================================================
Ensures ``code/`` and the project root are on ``sys.path`` so both
``team_dashboard.*`` and ``app.*`` imports resolve correctly, then
re-exports the FastAPI ``app`` object.

Run command (App Platform / Procfile)::

    uvicorn code.team_dashboard.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
# code/team_dashboard/main.py  →  code/  →  repo root
_THIS_DIR = Path(__file__).resolve().parent          # code/team_dashboard/
_CODE_DIR = _THIS_DIR.parent                         # code/
_PROJECT_ROOT = _CODE_DIR.parent                     # repo root

for p in (_CODE_DIR, _PROJECT_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# ── Re-export the FastAPI app ──────────────────────────────────────────
from team_dashboard.app import app  # noqa: E402, F401

__all__ = ["app"]
