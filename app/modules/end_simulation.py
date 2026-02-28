from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class EndSimulationResult:
	simulation_id: str
	status: str
	current_round: int
	closed_rounds: int
	locked_rounds: int
	ended_at_utc: str


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _simulation_path(root_dir: Path | str, simulation_id: str) -> Path:
	return Path(root_dir) / simulation_id


def _load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
	if not path.exists():
		raise FileNotFoundError(f"Required file not found: {path}")
	with path.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		fieldnames = reader.fieldnames
		if not fieldnames:
			raise ValueError(f"Missing CSV header in {path}")
		return fieldnames, list(reader)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
	with path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=fieldnames)
		writer.writeheader()
		if rows:
			writer.writerows(rows)


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


def end_simulation(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulations"),
) -> EndSimulationResult:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	simulation_csv = simulation_dir / "simulation.csv"
	rounds_csv = simulation_dir / "rounds.csv"
	admin_actions_csv = simulation_dir / "admin_actions.csv"

	sim_fieldnames, sim_rows = _load_csv(simulation_csv)
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")
	sim_row = sim_rows[0]

	current_status = sim_row.get("status", "")
	if current_status == "ENDED":
		raise ValueError(f"Simulation '{simulation_id}' is already ENDED")
	if current_status not in {"STARTED", "CREATED"}:
		raise ValueError(
			f"Simulation must be CREATED or STARTED to end (found '{current_status}')"
		)

	round_fieldnames, round_rows = _load_csv(rounds_csv)
	if not round_rows:
		raise ValueError("No rounds configured")

	now = _utc_now()
	closed_rounds = 0
	locked_rounds = 0
	current_round = _as_int(sim_row.get("current_round", "0"))

	for row in round_rows:
		status = row.get("status", "")

		if status == "OPEN":
			row["status"] = "CLOSED"
			row["closed_at_utc"] = now
			closed_rounds += 1
			continue

		if status == "PLANNED":
			row["status"] = "LOCKED"
			row["opened_at_utc"] = row.get("opened_at_utc", "")
			row["closed_at_utc"] = row.get("closed_at_utc", "")
			locked_rounds += 1
			continue

		if status == "CLOSED":
			continue

		if status == "LOCKED":
			locked_rounds += 1
			continue

		raise ValueError(f"Unsupported round status '{status}' in rounds.csv")

	sim_row["status"] = "ENDED"
	sim_row["current_round"] = str(current_round)
	sim_row["updated_at_utc"] = now

	admin_fieldnames, admin_rows = _load_csv(admin_actions_csv)
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "END_SIMULATION",
			"details": (
				f"status_before={current_status}; closed_rounds={closed_rounds}; "
				f"locked_rounds={locked_rounds}"
			),
			"event_at_utc": now,
		}
	)

	_write_csv(rounds_csv, round_fieldnames, round_rows)
	_write_csv(simulation_csv, sim_fieldnames, sim_rows)
	_write_csv(admin_actions_csv, admin_fieldnames, admin_rows)
	append_log_event(
		simulation_dir=simulation_dir,
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="END_SIMULATION",
		details=(
			f"status_before={current_status}; closed_rounds={closed_rounds}; "
			f"locked_rounds={locked_rounds}"
		),
		event_at_utc=now,
	)

	return EndSimulationResult(
		simulation_id=simulation_id,
		status="ENDED",
		current_round=_as_int(sim_row.get("current_round", "0")),
		closed_rounds=closed_rounds,
		locked_rounds=locked_rounds,
		ended_at_utc=now,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="End a simulation and lock remaining rounds")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
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
	result = end_simulation(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
	)
	print(
		f"Ended simulation {result.simulation_id}: status={result.status}, "
		f"current_round={result.current_round}, closed_rounds={result.closed_rounds}, "
		f"locked_rounds={result.locked_rounds}"
	)


if __name__ == "__main__":
	main()
