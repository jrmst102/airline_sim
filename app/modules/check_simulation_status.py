from __future__ import annotations

import argparse
from pathlib import Path

from app.data.csv_manager import csv_exists, load_csv


def check_simulation_status(
	simulation_id: str,
	root_dir: Path | str = Path("simulation/simulations"),
) -> str:
	if not csv_exists(simulation_id, "simulation.csv"):
		return "Simulation not found, please Setup Simulation"

	_, sim_rows = load_csv(simulation_id, "simulation.csv")
	if len(sim_rows) != 1:
		return "Simulation data corrupted"
	row = sim_rows[0]
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
		default=Path("simulation/simulations"),
		help="Root simulations directory",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	print(check_simulation_status(simulation_id=args.simulation_id, root_dir=args.root))


if __name__ == "__main__":
	main()
