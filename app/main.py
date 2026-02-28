from __future__ import annotations

import argparse
from pathlib import Path

from app.modules.display_log import display_log
from app.modules.historical_decisions_team import display_historical_decisions_team


def _build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Airline simulation command runner")
	subparsers = parser.add_subparsers(dest="command", required=True)

	display_log_parser = subparsers.add_parser("display-log", help="Display simulation log.csv")
	display_log_parser.add_argument("simulation_id", help="Simulation identifier")
	display_log_parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)

	history_parser = subparsers.add_parser(
		"historical-decisions-team",
		help="Display team decision summary from log.csv",
	)
	history_parser.add_argument("simulation_id", help="Simulation identifier")
	history_parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)

	return parser


def main() -> None:
	parser = _build_parser()
	args = parser.parse_args()

	if args.command == "display-log":
		print(display_log(simulation_id=args.simulation_id, root_dir=args.root), end="")
		return

	if args.command == "historical-decisions-team":
		print(
			display_historical_decisions_team(
				simulation_id=args.simulation_id,
				root_dir=args.root,
			)
		)
		return

	raise RuntimeError(f"Unsupported command '{args.command}'")


if __name__ == "__main__":
	main()
