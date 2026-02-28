from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class ChangeParametersResult:
	simulation_id: str
	new_version: int
	changed_fields: list[str]
	created_at_utc: str


PARAMETER_FIELDS = [
	"days_per_round",
	"base_demand_business",
	"base_demand_leisure",
	"base_fuel_cost_per_flight",
	"base_fixed_cost_per_round",
	"base_variable_cost_per_pax",
	"brand_effectiveness",
]


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


def _validate_updates(updates: dict[str, float | int]) -> None:
	if "days_per_round" in updates and int(updates["days_per_round"]) < 1:
		raise ValueError("days_per_round must be >= 1")
	for non_negative_key in [
		"base_demand_business",
		"base_demand_leisure",
		"base_fuel_cost_per_flight",
		"base_fixed_cost_per_round",
		"base_variable_cost_per_pax",
		"brand_effectiveness",
	]:
		if non_negative_key in updates and float(updates[non_negative_key]) < 0:
			raise ValueError(f"{non_negative_key} must be >= 0")


def change_parameters_live(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulations"),
	*,
	days_per_round: int | None = None,
	base_demand_business: float | None = None,
	base_demand_leisure: float | None = None,
	base_fuel_cost_per_flight: float | None = None,
	base_fixed_cost_per_round: float | None = None,
	base_variable_cost_per_pax: float | None = None,
	brand_effectiveness: float | None = None,
) -> ChangeParametersResult:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	simulation_csv = simulation_dir / "simulation.csv"
	parameters_csv = simulation_dir / "parameters.csv"
	admin_actions_csv = simulation_dir / "admin_actions.csv"

	sim_fieldnames, sim_rows = _load_csv(simulation_csv)
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in {simulation_csv}")
	sim_row = sim_rows[0]
	status = sim_row.get("status", "")
	if status not in {"CREATED", "STARTED"}:
		raise ValueError(f"Parameters can only be changed when simulation is CREATED or STARTED (found '{status}')")

	updates_raw: dict[str, float | int | None] = {
		"days_per_round": days_per_round,
		"base_demand_business": base_demand_business,
		"base_demand_leisure": base_demand_leisure,
		"base_fuel_cost_per_flight": base_fuel_cost_per_flight,
		"base_fixed_cost_per_round": base_fixed_cost_per_round,
		"base_variable_cost_per_pax": base_variable_cost_per_pax,
		"brand_effectiveness": brand_effectiveness,
	}
	updates = {key: value for key, value in updates_raw.items() if value is not None}
	if not updates:
		raise ValueError("At least one parameter value must be provided")

	_validate_updates(updates)

	parameter_fieldnames, parameter_rows = _load_csv(parameters_csv)
	if not parameter_rows:
		raise ValueError("No parameter versions found in parameters.csv")

	latest = parameter_rows[-1]
	new_version = max(_as_int(row.get("version", "0")) for row in parameter_rows) + 1
	now = _utc_now()

	new_row: dict[str, str] = {
		"simulation_id": simulation_id,
		"version": str(new_version),
		"created_at_utc": now,
	}
	for field_name in PARAMETER_FIELDS:
		if field_name in updates:
			new_row[field_name] = str(updates[field_name])
		else:
			new_row[field_name] = latest.get(field_name, "")

	parameter_rows.append(new_row)

	admin_fieldnames, admin_rows = _load_csv(admin_actions_csv)
	changed_fields = sorted(updates.keys())
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "CHANGE_PARAMETERS_LIVE",
			"details": f"version={new_version}; changed_fields={','.join(changed_fields)}",
			"event_at_utc": now,
		}
	)

	sim_row["updated_at_utc"] = now

	_write_csv(parameters_csv, parameter_fieldnames, parameter_rows)
	_write_csv(admin_actions_csv, admin_fieldnames, admin_rows)
	_write_csv(simulation_csv, sim_fieldnames, sim_rows)
	append_log_event(
		simulation_dir=simulation_dir,
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="CHANGE_PARAMETERS_LIVE",
		details=f"version={new_version}; changed_fields={','.join(changed_fields)}",
		event_at_utc=now,
	)

	return ChangeParametersResult(
		simulation_id=simulation_id,
		new_version=new_version,
		changed_fields=changed_fields,
		created_at_utc=now,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Create a new live parameter version for a simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument("--days-per-round", type=int)
	parser.add_argument("--base-demand-business", type=float)
	parser.add_argument("--base-demand-leisure", type=float)
	parser.add_argument("--base-fuel-cost-per-flight", type=float)
	parser.add_argument("--base-fixed-cost-per-round", type=float)
	parser.add_argument("--base-variable-cost-per-pax", type=float)
	parser.add_argument("--brand-effectiveness", type=float)
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
	result = change_parameters_live(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
		days_per_round=args.days_per_round,
		base_demand_business=args.base_demand_business,
		base_demand_leisure=args.base_demand_leisure,
		base_fuel_cost_per_flight=args.base_fuel_cost_per_flight,
		base_fixed_cost_per_round=args.base_fixed_cost_per_round,
		base_variable_cost_per_pax=args.base_variable_cost_per_pax,
		brand_effectiveness=args.brand_effectiveness,
	)
	print(
		f"Updated parameters for {result.simulation_id}: new_version={result.new_version}, "
		f"changed_fields={','.join(result.changed_fields)}"
	)


if __name__ == "__main__":
	main()
