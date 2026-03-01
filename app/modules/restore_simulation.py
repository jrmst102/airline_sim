from __future__ import annotations

import argparse
import csv
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.csv_manager import load_csv, write_csv
from app.data.log_manager import append_log_event


@dataclass(frozen=True)
class RestoreSimulationResult:
	backup_zip_path: Path
	source_simulation_id: str
	restored_simulation_id: str
	restored_path: Path
	mode: str
	event_at_utc: str


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


def _backup_root_folder_name(backup_zip_path: Path) -> str:
	with zipfile.ZipFile(backup_zip_path, "r") as handle:
		folder_names = {
			name.split("/", 1)[0]
			for name in handle.namelist()
			if name and not name.startswith("/") and "/" in name
		}
	if not folder_names:
		raise ValueError(f"Backup zip has no root folder entries: {backup_zip_path}")
	if len(folder_names) > 1:
		raise ValueError(
			f"Backup zip must contain exactly one root simulation folder (found {sorted(folder_names)})"
		)
	return next(iter(folder_names))


def _rewrite_simulation_id_fields(simulation_dir: Path, simulation_id: str) -> None:
	for csv_path in simulation_dir.glob("*.csv"):
		with csv_path.open("r", newline="", encoding="utf-8") as read_handle:
			reader = csv.DictReader(read_handle)
			fieldnames = reader.fieldnames
			if not fieldnames:
				continue
			rows = list(reader)

		if "simulation_id" not in fieldnames:
			continue

		for row in rows:
			row["simulation_id"] = simulation_id

		_write_csv(csv_path, fieldnames, rows)


def restore_simulation(
	backup_zip_path: Path | str,
	restore_as_simulation_id: str | None = None,
	admin_user_id: str = "U_ADMIN",
	root_dir: Path | str = Path("simulation/simulations"),
	overwrite: bool = False,
) -> RestoreSimulationResult:
	backup_path = Path(backup_zip_path)
	if not backup_path.exists() or not backup_path.is_file():
		raise FileNotFoundError(f"Backup zip not found: {backup_path}")

	source_simulation_id = _backup_root_folder_name(backup_path)
	target_simulation_id = (restore_as_simulation_id or source_simulation_id).strip()
	if not target_simulation_id:
		raise ValueError("restore_as_simulation_id cannot be empty")

	mode = "new_id" if target_simulation_id != source_simulation_id else "in_place"
	root = Path(root_dir)
	target_dir = root / target_simulation_id

	if target_dir.exists():
		if not overwrite:
			raise FileExistsError(
				f"Restore target already exists: {target_dir}. Use overwrite=True to replace it."
			)
		shutil.rmtree(target_dir)

	with tempfile.TemporaryDirectory() as tmp_dir:
		temp_root = Path(tmp_dir)
		shutil.unpack_archive(str(backup_path), str(temp_root), format="zip")

		extracted_dir = temp_root / source_simulation_id
		if not extracted_dir.exists() or not extracted_dir.is_dir():
			raise ValueError(
				f"Expected extracted simulation folder '{source_simulation_id}' in backup {backup_path}"
			)

		root.mkdir(parents=True, exist_ok=True)

		if mode == "new_id":
			renamed_dir = temp_root / target_simulation_id
			shutil.move(str(extracted_dir), str(renamed_dir))
			extracted_dir = renamed_dir

		shutil.move(str(extracted_dir), str(target_dir))

	if mode == "new_id":
		_rewrite_simulation_id_fields(target_dir, target_simulation_id)

	timestamp = _utc_now()
	admin_fieldnames, admin_rows = load_csv(target_simulation_id, "admin_actions.csv")
	admin_rows.append(
		{
			"event_id": _next_event_id(admin_rows),
			"simulation_id": target_simulation_id,
			"admin_user_id": admin_user_id,
			"action": "RESTORE_SIMULATION",
			"details": (
				f"backup_zip={backup_path}; "
				f"source_simulation_id={source_simulation_id}; "
				f"restored_simulation_id={target_simulation_id}; "
				f"mode={mode}; overwrite={overwrite}"
			),
			"event_at_utc": timestamp,
		}
	)
	write_csv(target_simulation_id, "admin_actions.csv", admin_fieldnames, admin_rows)
	append_log_event(
		simulation_id=target_simulation_id,
		actor_user_id=admin_user_id,
		action="RESTORE_SIMULATION",
		details=(
			f"backup_zip={backup_path}; source_simulation_id={source_simulation_id}; "
			f"restored_simulation_id={target_simulation_id}; mode={mode}; overwrite={overwrite}"
		),
		event_at_utc=timestamp,
	)

	return RestoreSimulationResult(
		backup_zip_path=backup_path,
		source_simulation_id=source_simulation_id,
		restored_simulation_id=target_simulation_id,
		restored_path=target_dir,
		mode=mode,
		event_at_utc=timestamp,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Restore a simulation from a backup zip")
	parser.add_argument("backup_zip_path", type=Path, help="Path to backup zip file")
	parser.add_argument(
		"--restore-as",
		dest="restore_as_simulation_id",
		default=None,
		help="Optional new simulation ID. If omitted, restore in-place using original ID from backup",
	)
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulation/simulations"),
		help="Root simulations directory",
	)
	parser.add_argument(
		"--overwrite",
		action="store_true",
		help="Replace target simulation directory if it already exists",
	)
	parser.add_argument(
		"--admin-user-id",
		default="U_ADMIN",
		help="Admin user ID to record in admin_actions log",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	result = restore_simulation(
		backup_zip_path=args.backup_zip_path,
		restore_as_simulation_id=args.restore_as_simulation_id,
		admin_user_id=args.admin_user_id,
		root_dir=args.root,
		overwrite=args.overwrite,
	)
	print(
		f"Restored backup {result.backup_zip_path} -> {result.restored_path} "
		f"(mode={result.mode}, source={result.source_simulation_id}, restored={result.restored_simulation_id})"
	)


if __name__ == "__main__":
	main()
