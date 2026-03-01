"""
Launch the Airline Simulation dashboard from the project root.

Usage:
    python run_dashboard.py              # default: host=0.0.0.0 port=8000
    python run_dashboard.py --port 8050  # custom port
"""

import argparse
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Airline Simulation dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    code_root = project_root / "code"
    if str(code_root) not in sys.path:
        sys.path.insert(0, str(code_root))

    uvicorn.run(
        "dashboard_web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
