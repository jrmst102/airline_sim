from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_SCHEMAS: dict[str, list[str]] = {
	"simulation.csv": [
		"simulation_id",
		"name",
		"status",
		"current_round",
		"total_rounds",
		"created_at_utc",
		"updated_at_utc",
	],
	"parameters.csv": [
		"simulation_id",
		"version",
		"days_per_round",
		"base_demand_business",
		"base_demand_leisure",
		"base_fuel_cost_per_flight",
		"base_fixed_cost_per_round",
		"base_variable_cost_per_pax",
		"brand_effectiveness",
		"created_at_utc",
	],
	"teams.csv": [
		"simulation_id",
		"team_id",
		"team_name",
		"is_active",
		"created_at_utc",
	],
	"users.csv": [
		"simulation_id",
		"user_id",
		"username",
		"role",
		"team_id",
		"password_hash",
		"is_locked",
		"created_at_utc",
	],
	"routes.csv": [
		"simulation_id",
		"route_id",
		"origin",
		"destination",
		"distance_miles",
		"is_active",
		"created_at_utc",
	],
	"airplane_types.csv": [
		"simulation_id",
		"airplane_type_id",
		"name",
		"seats_per_flight",
		"max_flights_per_day",
		"created_at_utc",
	],
	"rounds.csv": [
		"simulation_id",
		"round_number",
		"status",
		"opened_at_utc",
		"closed_at_utc",
	],
	"decisions.csv": [
		"simulation_id",
		"round_number",
		"team_id",
		"submitted_at_utc",
		"flights_per_day",
		"price_premium",
		"price_economy",
		"brand_investment",
	],
	"round_results_team.csv": [
		"simulation_id",
		"round_number",
		"team_id",
		"capacity",
		"carried_business",
		"carried_leisure",
		"revenue",
		"cost",
		"profit",
		"market_share_volume",
		"market_share_profit",
		"created_at_utc",
	],
	"round_results_market.csv": [
		"simulation_id",
		"round_number",
		"total_capacity",
		"total_carried",
		"avg_price_premium",
		"avg_price_economy",
		"total_revenue",
		"total_cost",
		"total_profit",
		"created_at_utc",
	],
	"login_log.csv": [
		"event_id",
		"simulation_id",
		"user_id",
		"username",
		"event_type",
		"event_at_utc",
	],
	"admin_actions.csv": [
		"event_id",
		"simulation_id",
		"admin_user_id",
		"action",
		"details",
		"event_at_utc",
	],
}


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
	with path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=headers)
		writer.writeheader()
		if rows:
			writer.writerows(rows)


def setup_simulation(
	simulation_id: str,
	simulation_name: str,
	total_rounds: int,
	team_names: list[str],
	root_dir: Path | str = Path("simulations"),
	overwrite: bool = False,
) -> Path:
	if total_rounds < 1:
		raise ValueError("total_rounds must be >= 1")
	if len(team_names) < 2:
		raise ValueError("At least 2 teams are required")

	root = Path(root_dir)
	simulation_dir = root / simulation_id

	if simulation_dir.exists() and not overwrite:
		raise FileExistsError(
			f"Simulation '{simulation_id}' already exists at {simulation_dir}"
		)

	simulation_dir.mkdir(parents=True, exist_ok=True)
	now = _utc_now()

	team_rows = [
		{
			"simulation_id": simulation_id,
			"team_id": f"T{i + 1}",
			"team_name": team_name,
			"is_active": "1",
			"created_at_utc": now,
		}
		for i, team_name in enumerate(team_names)
	]

	admin_user_rows = [
		{
			"simulation_id": simulation_id,
			"user_id": "U_ADMIN",
			"username": "admin",
			"role": "ADMIN",
			"team_id": "",
			"password_hash": "",
			"is_locked": "0",
			"created_at_utc": now,
		}
	]

	round_rows = [
		{
			"simulation_id": simulation_id,
			"round_number": str(round_num),
			"status": "PLANNED",
			"opened_at_utc": "",
			"closed_at_utc": "",
		}
		for round_num in range(1, total_rounds + 1)
	]

	seed_data: dict[str, list[dict[str, Any]]] = {
		"simulation.csv": [
			{
				"simulation_id": simulation_id,
				"name": simulation_name,
				"status": "CREATED",
				"current_round": "0",
				"total_rounds": str(total_rounds),
				"created_at_utc": now,
				"updated_at_utc": now,
			}
		],
		"parameters.csv": [
			{
				"simulation_id": simulation_id,
				"version": "1",
				"days_per_round": "30",
				"base_demand_business": "1200",
				"base_demand_leisure": "3600",
				"base_fuel_cost_per_flight": "2500",
				"base_fixed_cost_per_round": "50000",
				"base_variable_cost_per_pax": "40",
				"brand_effectiveness": "0.02",
				"created_at_utc": now,
			}
		],
		"teams.csv": team_rows,
		"users.csv": admin_user_rows,
		"routes.csv": [
			{
				"simulation_id": simulation_id,
				"route_id": "R1",
				"origin": "JFK",
				"destination": "BOS",
				"distance_miles": "187",
				"is_active": "1",
				"created_at_utc": now,
			}
		],
		"airplane_types.csv": [
			{
				"simulation_id": simulation_id,
				"airplane_type_id": "A1",
				"name": "A320",
				"seats_per_flight": "180",
				"max_flights_per_day": "20",
				"created_at_utc": now,
			}
		],
		"rounds.csv": round_rows,
		"decisions.csv": [],
		"round_results_team.csv": [],
		"round_results_market.csv": [],
		"login_log.csv": [],
		"admin_actions.csv": [
			{
				"event_id": "E1",
				"simulation_id": simulation_id,
				"admin_user_id": "U_ADMIN",
				"action": "SETUP_SIMULATION",
				"details": f"Created simulation with {len(team_names)} teams and {total_rounds} rounds",
				"event_at_utc": now,
			}
		],
	}

	for csv_name, headers in CSV_SCHEMAS.items():
		_write_csv(
			simulation_dir / csv_name,
			headers=headers,
			rows=seed_data.get(csv_name, []),
		)

	return simulation_dir


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Initialize a new airline simulation")
	parser.add_argument("simulation_id", help="Unique simulation identifier")
	parser.add_argument(
		"--name",
		default="Airline Simulation",
		help="Simulation display name",
	)
	parser.add_argument(
		"--rounds",
		type=int,
		default=8,
		help="Total number of rounds",
	)
	parser.add_argument(
		"--teams",
		nargs="+",
		default=["Team Alpha", "Team Bravo"],
		help="List of team names",
	)
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)
	parser.add_argument(
		"--overwrite",
		action="store_true",
		help="Overwrite existing simulation folder",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	simulation_path = setup_simulation(
		simulation_id=args.simulation_id,
		simulation_name=args.name,
		total_rounds=args.rounds,
		team_names=args.teams,
		root_dir=args.root,
		overwrite=args.overwrite,
	)
	print(f"Simulation initialized at: {simulation_path}")


if __name__ == "__main__":
	main()
