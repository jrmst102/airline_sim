from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.round_manager import open_first_round
from app.core.state_machine import validate_simulation_state
from app.data.csv_manager import load_csv, write_csv
from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class StartSimulationResult:
	simulation_id: str
	status: str
	current_round: int
	round_1_status: str
	started_at_utc: str


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _next_event_id(admin_action_rows: list[dict[str, str]]) -> str:
	max_suffix = 0
	for row in admin_action_rows:
		event_id = row.get("event_id", "")
		if event_id.startswith("E"):
			suffix = event_id.removeprefix("E")
			if suffix.isdigit():
				max_suffix = max(max_suffix, int(suffix))
	return f"E{max_suffix + 1}"


def start_simulation(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulation/simulations"),
) -> StartSimulationResult:
	sim_fieldnames, sim_rows = load_csv(simulation_id, "simulation.csv")
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")

	sim_row = sim_rows[0]
	current_status = sim_row.get("status", "")
	validate_simulation_state(current_status)
	if current_status == "STARTED":
		raise ValueError(f"Simulation '{simulation_id}' is already STARTED")
	if current_status != "CREATED":
		raise ValueError(
			f"Simulation '{simulation_id}' must be in CREATED status to start (found '{current_status}')"
		)

	round_fieldnames, round_rows = load_csv(simulation_id, "rounds.csv")
	if not round_rows:
		raise ValueError(f"No rounds found in {rounds_csv}")

	now = _utc_now()
	start_result = open_first_round(round_rows, event_at_utc=now)
	round_rows = start_result.updated_round_rows
	sim_row["status"] = "STARTED"
	sim_row["current_round"] = "1"
	sim_row["updated_at_utc"] = now

	admin_fieldnames, admin_rows = load_csv(simulation_id, "admin_actions.csv")
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "START_SIMULATION",
			"details": "Started simulation and opened round 1",
			"event_at_utc": now,
		}
	)

	write_csv(simulation_id, "simulation.csv", sim_fieldnames, sim_rows)
	write_csv(simulation_id, "rounds.csv", round_fieldnames, round_rows)
	write_csv(simulation_id, "admin_actions.csv", admin_fieldnames, admin_rows)
	append_log_event(
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="START_SIMULATION",
		details="Started simulation and opened round 1",
		event_at_utc=now,
	)

	return StartSimulationResult(
		simulation_id=simulation_id,
		status="STARTED",
		current_round=1,
		round_1_status="OPEN" if start_result.opened_round == 1 else "UNKNOWN",
		started_at_utc=now,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Start an initialized airline simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulation/simulations"),
		help="Root simulations directory",
	)
	parser.add_argument(
		"--admin-user-id",
		default="U_ADMIN",
		help="Admin user ID to record in admin_actions log",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	result = start_simulation(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
	)
	print(
		f"Simulation {result.simulation_id} started: "
		f"status={result.status} current_round={result.current_round} "
		f"round_1_status={result.round_1_status} at {result.started_at_utc}"
	)


if __name__ == "__main__":
	main()
