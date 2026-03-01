from __future__ import annotations

import argparse
import csv
from io import StringIO
from pathlib import Path


def _simulation_path(root_dir: Path | str, simulation_id: str) -> Path:
	return Path(root_dir) / simulation_id


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
	if not csv_path.exists():
		return []
	with csv_path.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		return list(reader)


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


def _build_legacy_log_text(simulation_dir: Path) -> str:
	admin_actions_csv = simulation_dir / "admin_actions.csv"
	login_log_csv = simulation_dir / "login_log.csv"

	normalized_rows: list[dict[str, str]] = []

	for row in _read_csv_rows(admin_actions_csv):
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

	for row in _read_csv_rows(login_log_csv):
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
	root_dir: Path | str = Path("simulations"),
) -> str:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	log_csv = simulation_dir / "log.csv"
	if not log_csv.exists():
		legacy_admin = simulation_dir / "admin_actions.csv"
		legacy_login = simulation_dir / "login_log.csv"
		if legacy_admin.exists() or legacy_login.exists():
			return _build_legacy_log_text(simulation_dir)
		raise FileNotFoundError(f"Required file not found: {log_csv}")
	return log_csv.read_text(encoding="utf-8")


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Display log.csv contents for a simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	print(display_log(simulation_id=args.simulation_id, root_dir=args.root), end="")


if __name__ == "__main__":
	main()
