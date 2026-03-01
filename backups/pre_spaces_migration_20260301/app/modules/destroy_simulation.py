from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class DestroySimulationResult:
	simulation_id: str
	mode: str
	backup_zip_path: Path
	destroyed_path: Path
	event_at_utc: str


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _safe_timestamp_for_filename(iso_timestamp: str) -> str:
	return iso_timestamp.replace(":", "-")


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


def _archive_simulation(simulation_dir: Path, archive_dir: Path, timestamp: str) -> Path:
	archive_dir.mkdir(parents=True, exist_ok=True)
	target = archive_dir / f"{simulation_dir.name}_{_safe_timestamp_for_filename(timestamp)}"
	if target.exists():
		raise FileExistsError(f"Archive target already exists: {target}")
	shutil.move(str(simulation_dir), str(target))
	return target


def destroy_simulation(
	simulation_id: str,
	admin_user_id: str = "U_ADMIN",
	mode: str = "archive",
	root_dir: Path | str = Path("simulations"),
	backups_dir: Path | str = Path("backups"),
	archive_dir: Path | str = Path("archive"),
) -> DestroySimulationResult:
	normalized_mode = mode.lower()
	if normalized_mode not in {"archive", "delete"}:
		raise ValueError("mode must be one of: archive, delete")

	simulation_dir = Path(root_dir) / simulation_id
	if not simulation_dir.exists() or not simulation_dir.is_dir():
		raise FileNotFoundError(f"Simulation directory not found: {simulation_dir}")

	admin_actions_csv = simulation_dir / "admin_actions.csv"
	if not admin_actions_csv.exists():
		raise FileNotFoundError(f"Required file not found: {admin_actions_csv}")

	timestamp = _utc_now()
	backup_zip_path = _create_backup_zip(
		simulation_dir=simulation_dir,
		backups_dir=Path(backups_dir),
		timestamp=timestamp,
	)

	admin_fieldnames, admin_rows = _load_csv(admin_actions_csv)
	action = "DESTROY_SIMULATION_ARCHIVE" if normalized_mode == "archive" else "DESTROY_SIMULATION_DELETE"
	details = (
		f"mode={normalized_mode}; "
		f"backup_zip={backup_zip_path}; "
		f"simulation_path={simulation_dir}"
	)
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": simulation_id,
			"admin_user_id": admin_user_id,
			"action": action,
			"details": details,
			"event_at_utc": timestamp,
		}
	)
	_write_csv(admin_actions_csv, admin_fieldnames, admin_rows)
	append_log_event(
		simulation_dir=simulation_dir,
		simulation_id=simulation_id,
		actor_user_id=admin_user_id,
		action=action,
		details=details,
		event_at_utc=timestamp,
	)

	if normalized_mode == "archive":
		destroyed_path = _archive_simulation(
			simulation_dir=simulation_dir,
			archive_dir=Path(archive_dir),
			timestamp=timestamp,
		)
	else:
		shutil.rmtree(simulation_dir)
		destroyed_path = simulation_dir

	return DestroySimulationResult(
		simulation_id=simulation_id,
		mode=normalized_mode,
		backup_zip_path=backup_zip_path,
		destroyed_path=destroyed_path,
		event_at_utc=timestamp,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Backup and destroy a simulation (archive or permanent delete)"
	)
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--mode",
		choices=["archive", "delete"],
		default="archive",
		help="archive moves simulation into archive/ after backup; delete removes it permanently after backup",
	)
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
		"--archive-dir",
		type=Path,
		default=Path("archive"),
		help="Directory where destroyed simulations are archived when mode=archive",
	)
	parser.add_argument(
		"--admin-user-id",
		default="U_ADMIN",
		help="Admin user ID to record in admin_actions log",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	result = destroy_simulation(
		simulation_id=args.simulation_id,
		admin_user_id=args.admin_user_id,
		mode=args.mode,
		root_dir=args.root,
		backups_dir=args.backups_dir,
		archive_dir=args.archive_dir,
	)
	print(
		f"Destroyed simulation {result.simulation_id} using mode={result.mode}. "
		f"Backup: {result.backup_zip_path} | Target: {result.destroyed_path}"
	)


if __name__ == "__main__":
	main()
