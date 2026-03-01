from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.data.csv_manager import load_csv, write_csv
from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class BackupSimulationResult:
	simulation_id: str
	backup_zip_path: Path
	event_at_utc: str


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _safe_timestamp_for_filename(iso_timestamp: str) -> str:
	return iso_timestamp.replace(":", "-")


def _next_event_id(admin_action_rows: list[dict[str, str]]) -> str:
	max_suffix = 0
	for row in admin_action_rows:
		event_id = row.get("event_id", "")
		if event_id.startswith("E"):
			suffix = event_id.removeprefix("E")
			if suffix.isdigit():
				max_suffix = max(max_suffix, int(suffix))
	return f"E{max_suffix + 1}"


def _create_backup_zip(simulation_dir: Path, backups_dir: Path, timestamp: str) -> Path:
	backups_dir.mkdir(parents=True, exist_ok=True)
	archive_base = backups_dir / f"{simulation_dir.name}_{_safe_timestamp_for_filename(timestamp)}"
	created_zip = shutil.make_archive(
		base_name=str(archive_base),
		format="zip",
		root_dir=str(simulation_dir.parent),
		base_dir=simulation_dir.name,
	)
	return Path(created_zip)


def backup_simulation(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulations"),
	backups_dir: Path | str = Path("backups"),
) -> BackupSimulationResult:
	simulation_dir = Path(root_dir) / simulation_id
	if not simulation_dir.exists() or not simulation_dir.is_dir():
		raise FileNotFoundError(f"Simulation directory not found: {simulation_dir}")

	admin_actions_csv = simulation_dir / "admin_actions.csv"
	timestamp = _utc_now()
	backup_zip_path = _create_backup_zip(
		simulation_dir=simulation_dir,
		backups_dir=Path(backups_dir),
		timestamp=timestamp,
	)

	admin_fieldnames, admin_rows = load_csv(simulation_id, "admin_actions.csv")
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": "BACKUP_SIMULATION",
			"details": f"backup_zip={backup_zip_path}; simulation_path={simulation_dir}",
			"event_at_utc": timestamp,
		}
	)
	write_csv(simulation_id, "admin_actions.csv", admin_fieldnames, admin_rows)
	append_log_event(
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action="BACKUP_SIMULATION",
		details=f"backup_zip={backup_zip_path}; simulation_path={simulation_dir}",
		event_at_utc=timestamp,
	)

	return BackupSimulationResult(
		simulation_id=simulation_id,
		backup_zip_path=backup_zip_path,
		event_at_utc=timestamp,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Create a zipped backup of a simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)
	parser.add_argument(
		"--backups-dir",
		type=Path,
		default=Path("backups"),
		help="Directory where backup zip files are stored",
	)
	parser.add_argument(
		"--admin-user-id",
		default="U_ADMIN",
		help="Admin user ID to record in admin_actions log",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	result = backup_simulation(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
		backups_dir=args.backups_dir,
	)
	print(f"Backup created for {result.simulation_id}: {result.backup_zip_path}")


if __name__ == "__main__":
	main()
