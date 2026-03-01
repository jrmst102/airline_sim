"""
Enter Decisions – Airlines Competitive Strategy Simulation
===========================================================
Record or update a team's monthly decisions for an OPEN round.

Decision variables (Case Appendix):
  1. flights_per_day  : int 0–5
  2. price_business   : float – business seat price ($)
  3. price_leisure    : float – leisure seat price ($)
  4. branding_level   : Low | Medium | High
  5. product_strategy : High | Medium | Low
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.state_machine import can_enter_decisions, validate_round_state, validate_simulation_state
from app.data.csv_manager import load_csv, write_csv, csv_exists
from app.data.log_manager import append_log_event


# ── Valid decision choices (Case Appendix) ─────────────────────────────
VALID_BRANDING = ("Low", "Medium", "High")
VALID_PRODUCTS = ("High", "Medium", "Low")

# Price floor / ceiling for sanity checks
MIN_PRICE = 50.0
MAX_PRICE = 1000.0


@dataclass(frozen=True)
class EnterDecisionResult:
	simulation_id: str
	round_number: int
	team_id: str
	flights_per_day: int
	price_business: float
	price_leisure: float
	branding_level: str
	product_strategy: str
	submitted_at_utc: str
	was_update: bool


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _as_int(value: str, default: int = 0) -> int:
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def _validate_inputs(
	flights_per_day: int,
	price_business: float,
	price_leisure: float,
	branding_level: str,
	product_strategy: str,
) -> None:
	if flights_per_day < 0 or flights_per_day > 5:
		raise ValueError(f"flights_per_day must be 0–5 (got {flights_per_day})")
	if price_business < MIN_PRICE or price_business > MAX_PRICE:
		raise ValueError(
			f"price_business must be between {MIN_PRICE} and {MAX_PRICE} (got {price_business})"
		)
	if price_leisure < MIN_PRICE or price_leisure > MAX_PRICE:
		raise ValueError(
			f"price_leisure must be between {MIN_PRICE} and {MAX_PRICE} (got {price_leisure})"
		)
	if branding_level not in VALID_BRANDING:
		raise ValueError(
			f"branding_level must be one of {VALID_BRANDING} (got '{branding_level}')"
		)
	if product_strategy not in VALID_PRODUCTS:
		raise ValueError(
			f"product_strategy must be one of {VALID_PRODUCTS} (got '{product_strategy}')"
		)


def _ensure_simulation_started(simulation_id: str) -> None:
	_, sim_rows = load_csv(simulation_id, "simulation.csv")
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row")
	status = sim_rows[0].get("status", "")
	validate_simulation_state(status)
	if status != "STARTED":
		raise ValueError(f"Simulation must be STARTED to enter decisions (found '{status}')")


def _ensure_team_active(simulation_id: str, team_id: str) -> None:
	_, team_rows = load_csv(simulation_id, "teams.csv")
	matched = next((row for row in team_rows if row.get("team_id") == team_id), None)
	if matched is None:
		raise ValueError(f"Unknown team_id '{team_id}'")
	if matched.get("is_active", "0") != "1":
		raise ValueError(f"Team '{team_id}' is not active")


def _max_flights_per_day(simulation_id: str) -> int:
	_, plane_rows = load_csv(simulation_id, "airplane_types.csv")
	if not plane_rows:
		raise ValueError("No airplane types configured")
	max_flights = max(_as_int(row.get("max_flights_per_day", "0")) for row in plane_rows)
	if max_flights < 1:
		raise ValueError("Invalid max_flights_per_day configuration")
	return max_flights


def _resolve_open_round(simulation_id: str, requested_round: int | None) -> int:
	_, round_rows = load_csv(simulation_id, "rounds.csv")
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
		round_status = matched.get("status", "")
		validate_round_state(round_status)
		if not can_enter_decisions("STARTED", round_status):
			raise ValueError(
				f"Round {requested_round} is not OPEN (status='{round_status}')"
			)
		return requested_round

	open_rounds = [
		_as_int(row.get("round_number", "0"))
		for row in round_rows
		if can_enter_decisions("STARTED", row.get("status", ""))
	]
	if not open_rounds:
		raise ValueError("No OPEN round available for decision entry")
	return min(open_rounds)


def enter_decision(
	simulation_id: str,
	team_id: str,
	flights_per_day: int,
	price_business: float,
	price_leisure: float,
	branding_level: str,
	product_strategy: str,
	round_number: int | None = None,
	root_dir: Path | str = Path("simulations"),
) -> EnterDecisionResult:
	"""Record or update one team's decision for the current OPEN round."""
	_validate_inputs(
		flights_per_day=flights_per_day,
		price_business=price_business,
		price_leisure=price_leisure,
		branding_level=branding_level,
		product_strategy=product_strategy,
	)

	_ensure_simulation_started(simulation_id)
	_ensure_team_active(simulation_id, team_id)

	max_flights = _max_flights_per_day(simulation_id)
	if flights_per_day > max_flights:
		raise ValueError(
			f"flights_per_day cannot exceed configured max_flights_per_day ({max_flights})"
		)

	effective_round = _resolve_open_round(simulation_id, requested_round=round_number)

	fieldnames, rows = load_csv(simulation_id, "decisions.csv")
	submitted_at_utc = _utc_now()

	new_row = {
		"simulation_id": simulation_id,
		"round_number": str(effective_round),
		"team_id": team_id,
		"flights_per_day": str(flights_per_day),
		"price_business": str(price_business),
		"price_leisure": str(price_leisure),
		"branding_level": branding_level,
		"product_strategy": product_strategy,
		"submitted_at_utc": submitted_at_utc,
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

	_write_csv_result = write_csv(simulation_id, "decisions.csv", fieldnames, rows)
	append_log_event(
		simulation_id=simulation_id,
		actor_user_id=team_id,
		action="UPDATE_DECISION" if was_update else "ENTER_DECISION",
		details=(
			f"round={effective_round}; team_id={team_id}; flights_per_day={flights_per_day}; "
			f"price_business={price_business}; price_leisure={price_leisure}; "
			f"branding_level={branding_level}; product_strategy={product_strategy}"
		),
		event_at_utc=submitted_at_utc,
	)

	return EnterDecisionResult(
		simulation_id=simulation_id,
		round_number=effective_round,
		team_id=team_id,
		flights_per_day=flights_per_day,
		price_business=price_business,
		price_leisure=price_leisure,
		branding_level=branding_level,
		product_strategy=product_strategy,
		submitted_at_utc=submitted_at_utc,
		was_update=was_update,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Enter or update team decisions for the OPEN round")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument("--team-id", required=True, help="Team identifier (A–F)")
	parser.add_argument("--flights-per-day", required=True, type=int, help="0–5")
	parser.add_argument(
		"--price-business", required=True, type=float,
		help="Business seat price ($)",
	)
	parser.add_argument(
		"--price-leisure", required=True, type=float,
		help="Leisure seat price ($)",
	)
	parser.add_argument(
		"--branding-level", required=True,
		choices=list(VALID_BRANDING),
		help="Low | Medium | High",
	)
	parser.add_argument(
		"--product-strategy", required=True,
		choices=list(VALID_PRODUCTS),
		help="High | Medium | Low",
	)
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
		price_business=args.price_business,
		price_leisure=args.price_leisure,
		branding_level=args.branding_level,
		product_strategy=args.product_strategy,
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
