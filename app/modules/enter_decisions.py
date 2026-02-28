from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class EnterDecisionResult:
	simulation_id: str
	round_number: int
	team_id: str
	flights_per_day: int
	price_premium: float
	price_economy: float
	brand_investment: float
	submitted_at_utc: str
	was_update: bool


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
		return int(value)
	except (TypeError, ValueError):
		return default


def _validate_inputs(
	flights_per_day: int,
	price_premium: float,
	price_economy: float,
	brand_investment: float,
) -> None:
	if flights_per_day < 1:
		raise ValueError("flights_per_day must be >= 1")
	if price_premium <= 0:
		raise ValueError("price_premium must be > 0")
	if price_economy <= 0:
		raise ValueError("price_economy must be > 0")
	if price_premium < price_economy:
		raise ValueError("price_premium must be >= price_economy")
	if brand_investment < 0:
		raise ValueError("brand_investment must be >= 0")


def _ensure_simulation_started(simulation_csv: Path) -> None:
	_, sim_rows = _load_csv(simulation_csv)
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")
	status = sim_rows[0].get("status", "")
	if status != "STARTED":
		raise ValueError(f"Simulation must be STARTED to enter decisions (found '{status}')")


def _ensure_team_active(teams_csv: Path, team_id: str) -> None:
	_, team_rows = _load_csv(teams_csv)
	matched = next((row for row in team_rows if row.get("team_id") == team_id), None)
	if matched is None:
		raise ValueError(f"Unknown team_id '{team_id}'")
	if matched.get("is_active", "0") != "1":
		raise ValueError(f"Team '{team_id}' is not active")


def _max_flights_per_day(airplane_types_csv: Path) -> int:
	_, plane_rows = _load_csv(airplane_types_csv)
	if not plane_rows:
		raise ValueError("No airplane types configured")
	max_flights = max(_as_int(row.get("max_flights_per_day", "0")) for row in plane_rows)
	if max_flights < 1:
		raise ValueError("Invalid max_flights_per_day configuration")
	return max_flights


def _resolve_open_round(rounds_csv: Path, requested_round: int | None) -> int:
	_, round_rows = _load_csv(rounds_csv)
	if not round_rows:
		raise ValueError("No rounds configured")

	if requested_round is not None:
		matched = next(
			(
				row
				for row in round_rows
				if _as_int(row.get("round_number", "0")) == requested_round
			),
			None,
		)
		if matched is None:
			raise ValueError(f"Round {requested_round} not found")
		if matched.get("status", "") != "OPEN":
			raise ValueError(
				f"Round {requested_round} is not OPEN (status='{matched.get('status', '')}')"
			)
		return requested_round

	open_rounds = [
		_as_int(row.get("round_number", "0"))
		for row in round_rows
		if row.get("status", "") == "OPEN"
	]
	if not open_rounds:
		raise ValueError("No OPEN round available for decision entry")
	return min(open_rounds)


def enter_decision(
	simulation_id: str,
	team_id: str,
	flights_per_day: int,
	price_premium: float,
	price_economy: float,
	brand_investment: float,
	round_number: int | None = None,
	root_dir: Path | str = Path("simulations"),
) -> EnterDecisionResult:
	_validate_inputs(
		flights_per_day=flights_per_day,
		price_premium=price_premium,
		price_economy=price_economy,
		brand_investment=brand_investment,
	)

	simulation_dir = _simulation_path(root_dir, simulation_id)
	simulation_csv = simulation_dir / "simulation.csv"
	rounds_csv = simulation_dir / "rounds.csv"
	teams_csv = simulation_dir / "teams.csv"
	airplane_types_csv = simulation_dir / "airplane_types.csv"
	decisions_csv = simulation_dir / "decisions.csv"

	_ensure_simulation_started(simulation_csv)
	_ensure_team_active(teams_csv, team_id)

	max_flights = _max_flights_per_day(airplane_types_csv)
	if flights_per_day > max_flights:
		raise ValueError(
			f"flights_per_day cannot exceed configured max_flights_per_day ({max_flights})"
		)

	effective_round = _resolve_open_round(rounds_csv, requested_round=round_number)

	fieldnames, rows = _load_csv(decisions_csv)
	submitted_at_utc = _utc_now()

	new_row = {
		"simulation_id": simulation_id,
		"round_number": str(effective_round),
		"team_id": team_id,
		"submitted_at_utc": submitted_at_utc,
		"flights_per_day": str(flights_per_day),
		"price_premium": str(price_premium),
		"price_economy": str(price_economy),
		"brand_investment": str(brand_investment),
	}

	target_index = -1
	for index, row in enumerate(rows):
		if (
			row.get("simulation_id") == simulation_id
			and _as_int(row.get("round_number", "0")) == effective_round
			and row.get("team_id") == team_id
		):
			target_index = index
			break

	was_update = target_index >= 0
	if was_update:
		rows[target_index] = new_row
	else:
		rows.append(new_row)

	_write_csv(decisions_csv, fieldnames, rows)
	append_log_event(
		simulation_dir=simulation_dir,
		simulation_id=simulation_id,
		actor_user_id=team_id,
		action="UPDATE_DECISION" if was_update else "ENTER_DECISION",
		details=(
			f"round={effective_round}; team_id={team_id}; flights_per_day={flights_per_day}; "
			f"price_premium={price_premium}; price_economy={price_economy}; brand_investment={brand_investment}"
		),
		event_at_utc=submitted_at_utc,
	)

	return EnterDecisionResult(
		simulation_id=simulation_id,
		round_number=effective_round,
		team_id=team_id,
		flights_per_day=flights_per_day,
		price_premium=price_premium,
		price_economy=price_economy,
		brand_investment=brand_investment,
		submitted_at_utc=submitted_at_utc,
		was_update=was_update,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Enter or update team decisions for the OPEN round")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument("--team-id", required=True, help="Team identifier")
	parser.add_argument("--flights-per-day", required=True, type=int)
	parser.add_argument("--price-premium", required=True, type=float)
	parser.add_argument("--price-economy", required=True, type=float)
	parser.add_argument("--brand-investment", required=True, type=float)
	parser.add_argument(
		"--round",
		type=int,
		dest="round_number",
		default=None,
		help="Optional round number. Must be OPEN if provided.",
	)
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	result = enter_decision(
		simulation_id=args.simulation_id,
		team_id=args.team_id,
		flights_per_day=args.flights_per_day,
		price_premium=args.price_premium,
		price_economy=args.price_economy,
		brand_investment=args.brand_investment,
		round_number=args.round_number,
		root_dir=args.root,
	)
	action = "UPDATED" if result.was_update else "CREATED"
	print(
		f"{action} decision for simulation={result.simulation_id} round={result.round_number} "
		f"team={result.team_id} at {result.submitted_at_utc}"
	)


if __name__ == "__main__":
	main()
