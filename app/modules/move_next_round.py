from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class MoveNextRoundResult:
	simulation_id: str
	closed_round: int
	opened_round: int | None
	simulation_status: str
	processed_team_count: int
	event_at_utc: str


@dataclass(frozen=True)
class _TeamComputation:
	team_id: str
	capacity: float
	carried_business: float
	carried_leisure: float
	revenue: float
	cost: float
	profit: float
	market_share_volume: float
	market_share_profit: float
	price_premium: float
	price_economy: float


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


def _require_started(simulation_row: dict[str, str]) -> None:
	status = simulation_row.get("status", "")
	if status != "STARTED":
		raise ValueError(f"Simulation must be STARTED to move rounds (found '{status}')")


def _active_team_ids(teams_rows: list[dict[str, str]]) -> list[str]:
	return [row["team_id"] for row in teams_rows if row.get("is_active", "0") == "1"]


def _resolve_open_round(round_rows: list[dict[str, str]], expected_round: int) -> tuple[int, int]:
	open_indices = [index for index, row in enumerate(round_rows) if row.get("status", "") == "OPEN"]
	if len(open_indices) != 1:
		raise ValueError(f"Expected exactly one OPEN round, found {len(open_indices)}")

	open_index = open_indices[0]
	open_round = _as_int(round_rows[open_index].get("round_number", "0"))
	if open_round != expected_round:
		raise ValueError(
			f"Simulation current_round={expected_round} does not match OPEN round={open_round}"
		)
	return open_index, open_round


def _compute_team_results(
	decision_rows: list[dict[str, str]],
	active_team_ids: list[str],
	days_per_round: int,
	seats_per_flight: int,
	base_demand_business: float,
	base_demand_leisure: float,
	base_fuel_cost_per_flight: float,
	base_fixed_cost_per_round: float,
	base_variable_cost_per_pax: float,
	brand_effectiveness: float,
) -> list[_TeamComputation]:
	decision_by_team = {row["team_id"]: row for row in decision_rows}
	missing = [team_id for team_id in active_team_ids if team_id not in decision_by_team]
	if missing:
		raise ValueError(f"Missing decisions for active team(s): {', '.join(missing)}")

	team_ids = [team_id for team_id in active_team_ids]
	brand_factors: dict[str, float] = {}
	biz_scores: dict[str, float] = {}
	lei_scores: dict[str, float] = {}
	capacities: dict[str, float] = {}
	prices_prem: dict[str, float] = {}
	prices_econ: dict[str, float] = {}

	for team_id in team_ids:
		decision = decision_by_team[team_id]
		flights_per_day = _as_int(decision.get("flights_per_day", "0"))
		price_premium = _as_float(decision.get("price_premium", "0"))
		price_economy = _as_float(decision.get("price_economy", "0"))
		brand_investment = _as_float(decision.get("brand_investment", "0"))

		if flights_per_day < 0 or price_premium <= 0 or price_economy <= 0 or brand_investment < 0:
			raise ValueError(f"Invalid decision values for team '{team_id}'")

		brand_factor = 1.0 + (brand_investment * brand_effectiveness)
		capacity = flights_per_day * days_per_round * seats_per_flight
		biz_score = brand_factor / price_premium
		lei_score = brand_factor / price_economy

		brand_factors[team_id] = brand_factor
		capacities[team_id] = capacity
		biz_scores[team_id] = biz_score
		lei_scores[team_id] = lei_score
		prices_prem[team_id] = price_premium
		prices_econ[team_id] = price_economy

	total_biz_score = sum(biz_scores.values())
	total_lei_score = sum(lei_scores.values())

	computed_rows: list[_TeamComputation] = []
	for team_id in team_ids:
		capacity = capacities[team_id]

		if total_biz_score > 0:
			demand_business = base_demand_business * (biz_scores[team_id] / total_biz_score)
		else:
			demand_business = 0.0

		if total_lei_score > 0:
			demand_leisure = base_demand_leisure * (lei_scores[team_id] / total_lei_score)
		else:
			demand_leisure = 0.0

		carried_business = min(capacity, demand_business)
		remaining_capacity = max(0.0, capacity - carried_business)
		carried_leisure = min(remaining_capacity, demand_leisure)
		carried_total = carried_business + carried_leisure

		revenue = (carried_business * prices_prem[team_id]) + (carried_leisure * prices_econ[team_id])
		fuel_cost = _as_int(decision_by_team[team_id].get("flights_per_day", "0")) * days_per_round * base_fuel_cost_per_flight
		fixed_cost = base_fixed_cost_per_round
		variable_cost = carried_total * base_variable_cost_per_pax
		brand_cost = _as_float(decision_by_team[team_id].get("brand_investment", "0"))
		cost = fuel_cost + fixed_cost + variable_cost + brand_cost
		profit = revenue - cost

		computed_rows.append(
			_TeamComputation(
				team_id=team_id,
				capacity=capacity,
				carried_business=carried_business,
				carried_leisure=carried_leisure,
				revenue=revenue,
				cost=cost,
				profit=profit,
				market_share_volume=0.0,
				market_share_profit=0.0,
				price_premium=prices_prem[team_id],
				price_economy=prices_econ[team_id],
			)
		)

	total_carried = sum(row.carried_business + row.carried_leisure for row in computed_rows)
	total_positive_profit = sum(max(row.profit, 0.0) for row in computed_rows)

	with_shares: list[_TeamComputation] = []
	for row in computed_rows:
		carried_total = row.carried_business + row.carried_leisure
		ms_volume = (carried_total / total_carried) if total_carried > 0 else 0.0
		ms_profit = (max(row.profit, 0.0) / total_positive_profit) if total_positive_profit > 0 else 0.0
		with_shares.append(
			_TeamComputation(
				team_id=row.team_id,
				capacity=row.capacity,
				carried_business=row.carried_business,
				carried_leisure=row.carried_leisure,
				revenue=row.revenue,
				cost=row.cost,
				profit=row.profit,
				market_share_volume=ms_volume,
				market_share_profit=ms_profit,
				price_premium=row.price_premium,
				price_economy=row.price_economy,
			)
		)

	return with_shares


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
	airplane_types_csv = simulation_dir / "airplane_types.csv"
	decisions_csv = simulation_dir / "decisions.csv"
	round_results_team_csv = simulation_dir / "round_results_team.csv"
	round_results_market_csv = simulation_dir / "round_results_market.csv"
	admin_actions_csv = simulation_dir / "admin_actions.csv"

	sim_fieldnames, sim_rows = _load_csv(simulation_csv)
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")
	sim_row = sim_rows[0]
	_require_started(sim_row)

	current_round = _as_int(sim_row.get("current_round", "0"))
	if current_round < 1:
		raise ValueError("Simulation current_round must be >= 1 before moving to next round")

	_, parameter_rows = _load_csv(parameters_csv)
	if not parameter_rows:
		raise ValueError("No parameters configured")
	latest_parameters = parameter_rows[-1]

	_, team_rows = _load_csv(teams_csv)
	active_team_ids = _active_team_ids(team_rows)
	if not active_team_ids:
		raise ValueError("No active teams found")

	round_fieldnames, round_rows = _load_csv(rounds_csv)
	open_round_index, open_round_number = _resolve_open_round(round_rows, expected_round=current_round)

	_, airplane_rows = _load_csv(airplane_types_csv)
	if not airplane_rows:
		raise ValueError("No airplane types configured")
	seats_per_flight = max(_as_int(row.get("seats_per_flight", "0")) for row in airplane_rows)
	if seats_per_flight < 1:
		raise ValueError("Invalid seats_per_flight configuration")

	_, decision_rows_all = _load_csv(decisions_csv)
	round_decisions = [
		row
		for row in decision_rows_all
		if row.get("simulation_id") == simulation_id
		and _as_int(row.get("round_number", "0")) == open_round_number
	]

	computed = _compute_team_results(
		decision_rows=round_decisions,
		active_team_ids=active_team_ids,
		days_per_round=_as_int(latest_parameters.get("days_per_round", "0")),
		seats_per_flight=seats_per_flight,
		base_demand_business=_as_float(latest_parameters.get("base_demand_business", "0")),
		base_demand_leisure=_as_float(latest_parameters.get("base_demand_leisure", "0")),
		base_fuel_cost_per_flight=_as_float(latest_parameters.get("base_fuel_cost_per_flight", "0")),
		base_fixed_cost_per_round=_as_float(latest_parameters.get("base_fixed_cost_per_round", "0")),
		base_variable_cost_per_pax=_as_float(latest_parameters.get("base_variable_cost_per_pax", "0")),
		brand_effectiveness=_as_float(latest_parameters.get("brand_effectiveness", "0")),
	)

	now = _utc_now()

	team_result_fieldnames, team_result_rows = _load_csv(round_results_team_csv)
	team_result_rows = [
		row for row in team_result_rows if _as_int(row.get("round_number", "0")) != open_round_number
	]
	for row in computed:
		team_result_rows.append(
			{
				"simulation_id": simulation_id,
				"round_number": str(open_round_number),
				"team_id": row.team_id,
				"capacity": _fmt_number(row.capacity, 2),
				"carried_business": _fmt_number(row.carried_business, 2),
				"carried_leisure": _fmt_number(row.carried_leisure, 2),
				"revenue": _fmt_number(row.revenue, 2),
				"cost": _fmt_number(row.cost, 2),
				"profit": _fmt_number(row.profit, 2),
				"market_share_volume": _fmt_number(row.market_share_volume, 6),
				"market_share_profit": _fmt_number(row.market_share_profit, 6),
				"created_at_utc": now,
			}
		)

	total_capacity = sum(row.capacity for row in computed)
	total_carried = sum(row.carried_business + row.carried_leisure for row in computed)
	total_revenue = sum(row.revenue for row in computed)
	total_cost = sum(row.cost for row in computed)
	total_profit = sum(row.profit for row in computed)
	avg_price_premium = sum(row.price_premium for row in computed) / len(computed)
	avg_price_economy = sum(row.price_economy for row in computed) / len(computed)

	market_result_fieldnames, market_result_rows = _load_csv(round_results_market_csv)
	market_result_rows = [
		row for row in market_result_rows if _as_int(row.get("round_number", "0")) != open_round_number
	]
	market_result_rows.append(
		{
			"simulation_id": simulation_id,
			"round_number": str(open_round_number),
			"total_capacity": _fmt_number(total_capacity, 2),
			"total_carried": _fmt_number(total_carried, 2),
			"avg_price_premium": _fmt_number(avg_price_premium, 2),
			"avg_price_economy": _fmt_number(avg_price_economy, 2),
			"total_revenue": _fmt_number(total_revenue, 2),
			"total_cost": _fmt_number(total_cost, 2),
			"total_profit": _fmt_number(total_profit, 2),
			"created_at_utc": now,
		}
	)

	closed_round = open_round_number
	round_rows[open_round_index]["status"] = "CLOSED"
	round_rows[open_round_index]["closed_at_utc"] = now

	next_round = open_round_number + 1
	next_round_index = next(
		(
			index
			for index, row in enumerate(round_rows)
			if _as_int(row.get("round_number", "0")) == next_round
		),
		None,
	)

	opened_round: int | None = None
	new_status = "STARTED"
	if next_round_index is not None:
		if round_rows[next_round_index].get("status", "") != "PLANNED":
			raise ValueError(
				f"Next round {next_round} must be PLANNED to open (found '{round_rows[next_round_index].get('status', '')}')"
			)
		round_rows[next_round_index]["status"] = "OPEN"
		round_rows[next_round_index]["opened_at_utc"] = now
		round_rows[next_round_index]["closed_at_utc"] = ""
		sim_row["current_round"] = str(next_round)
		opened_round = next_round
	else:
		sim_row["current_round"] = str(closed_round)
		new_status = "ENDED"

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
