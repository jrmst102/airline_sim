"""
Launch the Airline Simulation dashboard from the project root.

Usage:
    python run_dashboard.py              # default: host=0.0.0.0 port=8000
    python run_dashboard.py --port 8050  # custom port
"""

import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Airline Simulation dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "dashboard_web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
