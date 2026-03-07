from __future__ import annotations

import argparse
import csv
from io import StringIO
from pathlib import Path

from app.data.csv_manager import csv_exists, read_csv_rows, read_text, sim_key


def _render_log_csv(rows: list[dict[str, str]]) -> str:
	buffer = StringIO()
	writer = csv.DictWriter(
		buffer,
		fieldnames=["event_id", "simulation_id", "actor_user_id", "action", "details", "event_at_utc"],
	)
	writer.writeheader()
	if rows:
		writer.writerows(rows)
	return buffer.getvalue()


def _build_legacy_log_text(simulation_id: str) -> str:
	normalized_rows: list[dict[str, str]] = []

	for row in read_csv_rows(simulation_id, "admin_actions.csv"):
		normalized_rows.append(
			{
				"event_id": row.get("event_id", ""),
				"simulation_id": row.get("simulation_id", ""),
				"actor_user_id": row.get("admin_user_id", ""),
				"action": row.get("action", ""),
				"details": row.get("details", ""),
				"event_at_utc": row.get("event_at_utc", ""),
			}
		)

	for row in read_csv_rows(simulation_id, "login_log.csv"):
		username = row.get("username", "")
		details = f"username={username}" if username else ""
		normalized_rows.append(
			{
				"event_id": row.get("event_id", ""),
				"simulation_id": row.get("simulation_id", ""),
				"actor_user_id": row.get("user_id", ""),
				"action": row.get("event_type", ""),
				"details": details,
				"event_at_utc": row.get("event_at_utc", ""),
			}
		)

	normalized_rows.sort(key=lambda item: item.get("event_at_utc", ""))
	return _render_log_csv(normalized_rows)


def display_log(
	simulation_id: str,
	root_dir: Path | str = Path("simulation/simulations"),
) -> str:
	if not csv_exists(simulation_id, "log.csv"):
		if csv_exists(simulation_id, "admin_actions.csv") or csv_exists(simulation_id, "login_log.csv"):
			return _build_legacy_log_text(simulation_id)
		raise FileNotFoundError(f"Required file not found: {sim_key(simulation_id, 'log.csv')}")
	return read_text(sim_key(simulation_id, "log.csv"))


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Display log.csv contents for a simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulation/simulations"),
		help="Root simulations directory",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	print(display_log(simulation_id=args.simulation_id, root_dir=args.root), end="")


if __name__ == "__main__":
	main()
