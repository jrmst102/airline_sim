from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.round_manager import close_open_round_and_advance, resolve_open_round
from app.core.simulation_engine import (
	TeamDecisionInput,
	build_parameters_from_csv,
	compute_round_results,
)
from app.core.state_machine import can_move_next_round, validate_simulation_state
from app.data.log_manager import append_log_event
from app.modules.setup_simulation import load_parameters


@dataclass(frozen=True)
class MoveNextRoundResult:
	simulation_id: str
	closed_round: int
	opened_round: int | None
	simulation_status: str
	processed_team_count: int
	event_at_utc: str


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


def _as_float(value: str, default: float = 0.0) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return default


def _fmt_number(value: float, decimals: int = 4) -> str:
	return f"{value:.{decimals}f}"


def _next_event_id(admin_action_rows: list[dict[str, str]]) -> str:
	max_suffix = 0
	for row in admin_action_rows:
		event_id = row.get("event_id", "")
		if event_id.startswith("E"):
			suffix = event_id.removeprefix("E")
			if suffix.isdigit():
				max_suffix = max(max_suffix, int(suffix))
	return f"E{max_suffix + 1}"


def _active_team_rows(teams_rows: list[dict[str, str]]) -> list[dict[str, str]]:
	return [row for row in teams_rows if row.get("is_active", "0") == "1"]


def move_next_round(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulations"),
) -> MoveNextRoundResult:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	simulation_csv = simulation_dir / "simulation.csv"
	parameters_csv = simulation_dir / "parameters.csv"
	teams_csv = simulation_dir / "teams.csv"
	rounds_csv = simulation_dir / "rounds.csv"
	decisions_csv = simulation_dir / "decisions.csv"
	round_results_team_csv = simulation_dir / "round_results_team.csv"
	round_results_market_csv = simulation_dir / "round_results_market.csv"
	admin_actions_csv = simulation_dir / "admin_actions.csv"

	sim_fieldnames, sim_rows = _load_csv(simulation_csv)
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")
	sim_row = sim_rows[0]
	status = sim_row.get("status", "")
	validate_simulation_state(status)
	if not can_move_next_round(status, open_round_count=1):
		raise ValueError(f"Simulation must be STARTED to move rounds (found '{status}')")

	current_round = _as_int(sim_row.get("current_round", "0"))
	if current_round < 1:
		raise ValueError("Simulation current_round must be >= 1 before moving to next round")

	# ── Load key-value parameters ─────────────────────────────────
	params_dict = load_parameters(parameters_csv)
	engine_parameters = build_parameters_from_csv(params_dict)

	# ── Teams (need variable_cost_per_passenger) ──────────────────
	_, team_rows = _load_csv(teams_csv)
	active_teams = _active_team_rows(team_rows)
	if not active_teams:
		raise ValueError("No active teams found")
	active_team_ids = [row["team_id"] for row in active_teams]

	# Map team_id → variable_cost_per_passenger from teams.csv
	var_cost_map: dict[str, float] = {}
	for row in active_teams:
		var_cost_map[row["team_id"]] = _as_float(
			row.get("variable_cost_per_passenger", "0")
		)

	round_fieldnames, round_rows = _load_csv(rounds_csv)
	open_resolution = resolve_open_round(round_rows, expected_round=current_round)
	open_round_number = open_resolution.open_round_number

	_, decision_rows_all = _load_csv(decisions_csv)
	round_decisions = [
		row
		for row in decision_rows_all
		if row.get("simulation_id") == simulation_id
		and _as_int(row.get("round_number", "0")) == open_round_number
	]

	engine_decisions = [
		TeamDecisionInput(
			team_id=row.get("team_id", ""),
			flights_per_day=_as_int(row.get("flights_per_day", "0")),
			price_business=_as_float(row.get("price_business", "360")),
			price_leisure=_as_float(row.get("price_leisure", "180")),
			branding_level=row.get("branding_level", "Low"),
			product_strategy=row.get("product_strategy", "None"),
			variable_cost_per_passenger=var_cost_map.get(
				row.get("team_id", ""), 0.0
			),
		)
		for row in round_decisions
	]
	engine_result = compute_round_results(
		decisions=engine_decisions,
		parameters=engine_parameters,
	)
	computed = engine_result.team_results

	now = _utc_now()

	# ── Write team results ────────────────────────────────────────
	team_result_fieldnames, team_result_rows = _load_csv(round_results_team_csv)
	team_result_rows = [
		row for row in team_result_rows if _as_int(row.get("round_number", "0")) != open_round_number
	]
	for tr in computed:
		team_result_rows.append(
			{
				"simulation_id": simulation_id,
				"round_number": str(open_round_number),
				"team_id": tr.team_id,
				"passengers": str(tr.passengers),
				"revenue": _fmt_number(tr.revenue, 2),
				"variable_cost": _fmt_number(tr.variable_cost, 2),
				"fixed_cost": _fmt_number(tr.fixed_cost, 2),
				"branding_cost": _fmt_number(tr.branding_cost, 2),
				"product_cost": _fmt_number(tr.product_cost, 2),
				"total_cost": _fmt_number(tr.total_cost, 2),
				"profit": _fmt_number(tr.profit, 2),
				"market_share_volume": _fmt_number(tr.market_share_volume, 6),
				"market_share_profit": _fmt_number(tr.market_share_profit, 6),
				"load_factor": _fmt_number(tr.load_factor, 4),
				"avg_revenue_per_flight": _fmt_number(tr.avg_revenue_per_flight, 2),
				"avg_cost_per_flight": _fmt_number(tr.avg_cost_per_flight, 2),
				"avg_profit_per_flight": _fmt_number(tr.avg_profit_per_flight, 2),
				"csi": "",
				"oei": "",
				"created_at_utc": now,
			}
		)

	# ── Write market results ──────────────────────────────────────
	mr = engine_result.market_result
	market_result_fieldnames, market_result_rows = _load_csv(round_results_market_csv)
	market_result_rows = [
		row for row in market_result_rows if _as_int(row.get("round_number", "0")) != open_round_number
	]
	market_result_rows.append(
		{
			"simulation_id": simulation_id,
			"round_number": str(open_round_number),
			"total_demand": str(mr.total_demand),
			"total_passengers": str(mr.total_passengers),
			"total_revenue": _fmt_number(mr.total_revenue, 2),
			"total_cost": _fmt_number(mr.total_cost, 2),
			"total_profit": _fmt_number(mr.total_profit, 2),
			"created_at_utc": now,
		}
	)

	advance_result = close_open_round_and_advance(
		round_rows,
		current_round=current_round,
		event_at_utc=now,
	)
	round_rows = advance_result.updated_round_rows
	closed_round = advance_result.closed_round
	opened_round = advance_result.opened_round
	new_status = advance_result.simulation_status
	sim_row["current_round"] = str(advance_result.current_round)
	sim_row["status"] = new_status
	sim_row["updated_at_utc"] = now

	admin_fieldnames, admin_rows = _load_csv(admin_actions_csv)
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "MOVE_NEXT_ROUND",
			"details": (
				f"closed_round={closed_round}; opened_round={opened_round}; "
				f"status={new_status}; processed_teams={len(computed)}"
			),
			"event_at_utc": now,
		}
	)

	_write_csv(round_results_team_csv, team_result_fieldnames, team_result_rows)
	_write_csv(round_results_market_csv, market_result_fieldnames, market_result_rows)
	_write_csv(rounds_csv, round_fieldnames, round_rows)
	_write_csv(simulation_csv, sim_fieldnames, sim_rows)
	_write_csv(admin_actions_csv, admin_fieldnames, admin_rows)
	append_log_event(
		simulation_dir=simulation_dir,
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="MOVE_NEXT_ROUND",
		details=(
			f"closed_round={closed_round}; opened_round={opened_round}; "
			f"status={new_status}; processed_teams={len(computed)}"
		),
		event_at_utc=now,
	)

	return MoveNextRoundResult(
		simulation_id=simulation_id,
		closed_round=closed_round,
		opened_round=opened_round,
		simulation_status=new_status,
		processed_team_count=len(computed),
		event_at_utc=now,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Close current OPEN round, compute results, and open next round")
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
	result = move_next_round(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
	)
	print(
		f"Moved simulation {result.simulation_id}: closed_round={result.closed_round}, "
		f"opened_round={result.opened_round}, status={result.simulation_status}, "
		f"processed_teams={result.processed_team_count}"
	)


if __name__ == "__main__":
	main()
