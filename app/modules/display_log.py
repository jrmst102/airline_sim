from __future__ import annotations

import argparse
from pathlib import Path


def _simulation_path(root_dir: Path | str, simulation_id: str) -> Path:
	return Path(root_dir) / simulation_id


def display_log(
	simulation_id: str,
	root_dir: Path | str = Path("simulations"),
) -> str:
	log_csv = _simulation_path(root_dir, simulation_id) / "log.csv"
	if not log_csv.exists():
		raise FileNotFoundError(f"Required file not found: {log_csv}")
	return log_csv.read_text(encoding="utf-8")


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Display log.csv contents for a simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	print(display_log(simulation_id=args.simulation_id, root_dir=args.root), end="")


if __name__ == "__main__":
	main()
