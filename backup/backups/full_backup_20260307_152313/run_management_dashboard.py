"""
Management Dashboard – standalone entry point.
================================================
Run with::

    python run_management_dashboard.py               # http://0.0.0.0:8090
    python run_management_dashboard.py --port 9000   # custom port
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root and code/ are on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
_CODE_DIR = _PROJECT_ROOT / "code"

for p in (_CODE_DIR, _PROJECT_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def main() -> None:
    parser = argparse.ArgumentParser(description="Management Dashboard")
    parser.add_argument("--port", type=int, default=8090, help="Port (default: 8090)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "management_dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
