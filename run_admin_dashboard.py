#!/usr/bin/env python3
"""Launch the newer admin dashboard (non-legacy Streamlit app).

Usage:
    python run_admin_dashboard.py
    python run_admin_dashboard.py --port 8502
    python run_admin_dashboard.py -- --server.headless true
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the newer admin dashboard (not the legacy Streamlit admin view)."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8501, help="Port (default: 8501)")
    parser.add_argument(
        "streamlit_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments forwarded to streamlit (prefix with --)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    entrypoint = project_root / "app" / "ui" / "pages" / "home.py"

    if not entrypoint.exists():
        raise FileNotFoundError(f"Dashboard entrypoint not found: {entrypoint}")

    extra_args = args.streamlit_args
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(entrypoint),
        "--server.address",
        args.host,
        "--server.port",
        str(args.port),
        *extra_args,
    ]

    raise SystemExit(subprocess.call(cmd, cwd=str(project_root)))


if __name__ == "__main__":
    main()
