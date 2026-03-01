from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


LOG_HEADERS = [
	"event_id",
	"simulation_id",
	"actor_user_id",
	"action",
	"details",
	"event_at_utc",
]


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _next_event_id(log_rows: list[dict[str, str]]) -> str:
	max_suffix = 0
	for row in log_rows:
		event_id = row.get("event_id", "")
		if event_id.startswith("E"):
			suffix = event_id.removeprefix("E")
			if suffix.isdigit():
				max_suffix = max(max_suffix, int(suffix))
	return f"E{max_suffix + 1}"


def append_log_event(
	simulation_dir: Path,
	simulation_id: str,
	actor_user_id: str,
	action: str,
	details: str,
	event_at_utc: str | None = None,
) -> None:
	log_csv = simulation_dir / "log.csv"
	rows: list[dict[str, str]] = []

	if log_csv.exists():
		with log_csv.open("r", newline="", encoding="utf-8") as read_handle:
			reader = csv.DictReader(read_handle)
			if reader.fieldnames:
				rows = list(reader)

	timestamp = event_at_utc or _utc_now()
	rows.append(
		{
			"event_id": _next_event_id(rows),
			"simulation_id": simulation_id,
			"actor_user_id": actor_user_id,
			"action": action,
			"details": details,
			"event_at_utc": timestamp,
		}
	)

	with log_csv.open("w", newline="", encoding="utf-8") as write_handle:
		writer = csv.DictWriter(write_handle, fieldnames=LOG_HEADERS)
		writer.writeheader()
		if rows:
			writer.writerows(rows)
