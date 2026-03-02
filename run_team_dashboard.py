#!/usr/bin/env python3
"""Launch the Team Dashboard (FastAPI + Jinja2, no Streamlit).

Usage:
    python run_team_dashboard.py                # default: http://0.0.0.0:8081
    python run_team_dashboard.py --port 8082    # custom port
    python run_team_dashboard.py --reload       # auto-reload for development

Environment variables:
    SESSION_SECRET   – signing key for session cookies (required in production)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Team Dashboard (FastAPI, no Streamlit)."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8081, help="Port (default: 8081)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    code_root = project_root / "code"
    if str(code_root) not in sys.path:
        sys.path.insert(0, str(code_root))

    uvicorn.run(
        "team_dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
