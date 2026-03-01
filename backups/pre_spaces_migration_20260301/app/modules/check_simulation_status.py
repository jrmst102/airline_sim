from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _simulation_path(root_dir: Path | str, simulation_id: str) -> Path:
	return Path(root_dir) / simulation_id


def _load_simulation_row(simulation_csv: Path) -> dict[str, str]:
	with simulation_csv.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		rows = list(reader)
	if len(rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")
	return rows[0]


def check_simulation_status(
	simulation_id: str,
	root_dir: Path | str = Path("simulations"),
) -> str:
	simulation_csv = _simulation_path(root_dir, simulation_id) / "simulation.csv"
	if not simulation_csv.exists():
		return "Simulation not found, please Setup Simulation"

	row = _load_simulation_row(simulation_csv)
	status = row.get("status", "")
	current_round = row.get("current_round", "0")

	if status == "STARTED":
		return f"The simulation is running at cycle {current_round}"
	if status == "ENDED":
		return "The simulation ended"
	return "The simulation is stopped"


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Check simulation status")
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
	print(check_simulation_status(simulation_id=args.simulation_id, root_dir=args.root))


if __name__ == "__main__":
	main()
