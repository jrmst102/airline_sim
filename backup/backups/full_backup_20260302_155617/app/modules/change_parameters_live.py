"""
Change Parameters Live – Airlines Competitive Strategy Simulation
==================================================================
Update one or more key-value parameters in ``parameters.csv`` while
the simulation is CREATED or STARTED.

parameters.csv uses a key-value format (key,value,notes).  This module
reads the current values, updates the requested keys, and writes
them back.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.data.csv_manager import load_csv, write_csv
from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class ChangeParametersResult:
	simulation_id: str
	changed_keys: list[str]
	created_at_utc: str


# Keys that are allowed to be changed live  (subset of parameters.csv keys).
ALLOWED_KEYS: set[str] = {
	"total_demand_passengers",
	"business_demand",
	"leisure_demand",
	"seats_per_flight",
	"fixed_cost_per_flight",
	"days_per_month",
	"fare_business_premium",
	"fare_leisure_premium",
	"fare_business_match",
	"fare_leisure_match",
	"fare_business_discount",
	"fare_leisure_discount",
	"branding_cost_low",
	"branding_cost_medium",
	"branding_cost_high",
	"product_cost_high",
	"product_cost_medium",
	"product_cost_low",
	"discount_penalty_threshold",
	"discount_penalty_rate",
}


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


def _validate_updates(updates: dict[str, str]) -> None:
	unknown = set(updates.keys()) - ALLOWED_KEYS
	if unknown:
		raise ValueError(f"Unknown parameter key(s): {', '.join(sorted(unknown))}")
	for key, value in updates.items():
		try:
			float(value)
		except ValueError:
			raise ValueError(f"Parameter '{key}' value must be numeric (got '{value}')")


def change_parameters_live(
	simulation_id: str,
	updates: dict[str, str],
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulation/simulations"),
) -> ChangeParametersResult:
	"""Update parameter values in the key-value parameters.csv."""
	if not updates:
		raise ValueError("At least one parameter update must be provided")

	_validate_updates(updates)

	sim_fieldnames, sim_rows = load_csv(simulation_id, "simulation.csv")
	if len(sim_rows) != 1:
		raise ValueError(f"Expected exactly 1 simulation row in simulation.csv")
	sim_row = sim_rows[0]
	status = sim_row.get("status", "")
	if status not in {"CREATED", "STARTED"}:
		raise ValueError(
			f"Parameters can only be changed when simulation is CREATED or STARTED (found '{status}')"
		)

	# Read key-value parameters
	param_fieldnames, param_rows = load_csv(simulation_id, "parameters.csv")
	if not param_rows:
		raise ValueError("No parameters found in parameters.csv")

	# Apply updates
	changed_keys: list[str] = []
	for row in param_rows:
		key = row.get("key", "")
		if key in updates:
			row["value"] = updates[key]
			changed_keys.append(key)

	# Warn if any requested keys weren't found in the CSV
	missing_keys = set(updates.keys()) - set(changed_keys)
	if missing_keys:
		raise ValueError(f"Parameter key(s) not found in CSV: {', '.join(sorted(missing_keys))}")

	now = _utc_now()
	sim_row["updated_at_utc"] = now

	admin_fieldnames, admin_rows = load_csv(simulation_id, "admin_actions.csv")
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "CHANGE_PARAMETERS_LIVE",
			"details": f"changed_keys={','.join(sorted(changed_keys))}",
			"event_at_utc": now,
		}
	)

	write_csv(simulation_id, "parameters.csv", param_fieldnames, param_rows)
	write_csv(simulation_id, "admin_actions.csv", admin_fieldnames, admin_rows)
	write_csv(simulation_id, "simulation.csv", sim_fieldnames, sim_rows)
	append_log_event(
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="CHANGE_PARAMETERS_LIVE",
		details=f"changed_keys={','.join(sorted(changed_keys))}",
		event_at_utc=now,
	)

	return ChangeParametersResult(
		simulation_id=simulation_id,
		changed_keys=sorted(changed_keys),
		created_at_utc=now,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Update key-value parameters for a simulation",
	)
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--set",
		nargs=2,
		metavar=("KEY", "VALUE"),
		action="append",
		dest="param_updates",
		help="Set a parameter: --set total_demand_passengers 130000",
	)
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
	if not args.param_updates:
		raise SystemExit("At least one --set KEY VALUE is required")
	updates = {key: value for key, value in args.param_updates}
	result = change_parameters_live(
		simulation_id=args.simulation_id,
		updates=updates,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
	)
	print(
		f"Updated parameters for {result.simulation_id}: "
		f"changed_keys={','.join(result.changed_keys)}"
	)


if __name__ == "__main__":
	main()
