#!/usr/bin/env python3
"""Launch the unified Airline Simulation Dashboard (Admin + Team).

Usage:
    python run_admin_dashboard.py                # default: http://0.0.0.0:8080
    python run_admin_dashboard.py --port 8090    # custom port
    python run_admin_dashboard.py --reload       # auto-reload for development
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the unified Airline Simulation Dashboard."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    code_root = project_root / "code"
    if str(code_root) not in sys.path:
        sys.path.insert(0, str(code_root))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    uvicorn.run(
        "team_dashboard.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
