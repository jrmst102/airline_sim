from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from app.data.csv_manager import load_csv, write_csv, csv_exists


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
	simulation_id: str,
	actor_user_id: str,
	action: str,
	details: str,
	event_at_utc: str | None = None,
	# Legacy parameter — accepted but ignored when using storage layer
	simulation_dir=None,
) -> None:
	rows: list[dict[str, str]] = []

	if csv_exists(simulation_id, "log.csv"):
		_, rows = load_csv(simulation_id, "log.csv")

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

	write_csv(simulation_id, "log.csv", LOG_HEADERS, rows)
