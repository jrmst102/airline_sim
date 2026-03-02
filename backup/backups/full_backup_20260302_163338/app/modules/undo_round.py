from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.round_manager import undo_latest_round_transition
from app.core.state_machine import can_undo_round, validate_simulation_state
from app.data.csv_manager import load_csv, write_csv
from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class UndoRoundResult:
	simulation_id: str
	reopened_round: int
	rolled_back_open_round: int | None
	simulation_status: str
	event_at_utc: str


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _as_int(value: str, default: int = 0) -> int:
	try:
		return int(float(value))
	except (TypeError, ValueError):
		return default


def _next_event_id(admin_action_rows: list[dict[str, str]]) -> str:
	max_suffix = 0
	for row in admin_action_rows:
		event_id = row.get("event_id", "")
		if event_id.startswith("E"):
			suffix = event_id.removeprefix("E")
			if suffix.isdigit():
				max_suffix = max(max_suffix, int(suffix))
	return f"E{max_suffix + 1}"


def undo_round(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulation/simulations"),
) -> UndoRoundResult:
	sim_fieldnames, sim_rows = load_csv(simulation_id, "simulation.csv")
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in simulation.csv")
	sim_row = sim_rows[0]
	status = sim_row.get("status", "")
	validate_simulation_state(status)
	if not can_undo_round(status):
		raise ValueError(f"Simulation must be STARTED or ENDED to undo round (found '{status}')")

	round_fieldnames, round_rows = load_csv(simulation_id, "rounds.csv")
	if not round_rows:
		raise ValueError("No rounds configured")

	undo_result = undo_latest_round_transition(round_rows, simulation_status=status)
	round_rows = undo_result.updated_round_rows
	reopened_round = undo_result.reopened_round
	rolled_back_open_round = undo_result.rolled_back_open_round
	new_status = undo_result.simulation_status
	sim_row["current_round"] = str(undo_result.current_round)
	sim_row["status"] = new_status

	now = _utc_now()
	sim_row["updated_at_utc"] = now

	team_result_fieldnames, team_result_rows = load_csv(simulation_id, "round_results_team.csv")
	team_result_rows = [
		row for row in team_result_rows if _as_int(row.get("round_number", "0")) != reopened_round
	]

	market_result_fieldnames, market_result_rows = load_csv(simulation_id, "round_results_market.csv")
	market_result_rows = [
		row for row in market_result_rows if _as_int(row.get("round_number", "0")) != reopened_round
	]

	if rolled_back_open_round is not None:
		decision_fieldnames, decision_rows = load_csv(simulation_id, "decisions.csv")
		decision_rows = [
			row
			for row in decision_rows
			if _as_int(row.get("round_number", "0")) != rolled_back_open_round
		]
		write_csv(simulation_id, "decisions.csv", decision_fieldnames, decision_rows)

	admin_fieldnames, admin_rows = load_csv(simulation_id, "admin_actions.csv")
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "UNDO_ROUND",
			"details": (
				f"reopened_round={reopened_round}; rolled_back_open_round={rolled_back_open_round}; "
				f"status={new_status}"
			),
			"event_at_utc": now,
		}
	)

	write_csv(simulation_id, "round_results_team.csv", team_result_fieldnames, team_result_rows)
	write_csv(simulation_id, "round_results_market.csv", market_result_fieldnames, market_result_rows)
	write_csv(simulation_id, "rounds.csv", round_fieldnames, round_rows)
	write_csv(simulation_id, "simulation.csv", sim_fieldnames, sim_rows)
	write_csv(simulation_id, "admin_actions.csv", admin_fieldnames, admin_rows)
	append_log_event(
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="UNDO_ROUND",
		details=(
			f"reopened_round={reopened_round}; rolled_back_open_round={rolled_back_open_round}; "
			f"status={new_status}"
		),
		event_at_utc=now,
	)

	return UndoRoundResult(
		simulation_id=simulation_id,
		reopened_round=reopened_round,
		rolled_back_open_round=rolled_back_open_round,
		simulation_status=new_status,
		event_at_utc=now,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Undo the most recent closed round and restore it to OPEN")
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
	result = undo_round(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
	)
	print(
		f"Undid round for {result.simulation_id}: reopened_round={result.reopened_round}, "
		f"rolled_back_open_round={result.rolled_back_open_round}, status={result.simulation_status}"
	)


if __name__ == "__main__":
	main()
