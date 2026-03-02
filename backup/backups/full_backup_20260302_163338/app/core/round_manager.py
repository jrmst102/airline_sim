from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoundOpenResolution:
	open_index: int
	open_round_number: int


@dataclass(frozen=True)
class AdvanceRoundResult:
	updated_round_rows: list[dict[str, str]]
	closed_round: int
	opened_round: int | None
	simulation_status: str
	current_round: int


@dataclass(frozen=True)
class StartRoundResult:
	updated_round_rows: list[dict[str, str]]
	opened_round: int


@dataclass(frozen=True)
class UndoRoundResult:
	updated_round_rows: list[dict[str, str]]
	reopened_round: int
	rolled_back_open_round: int | None
	simulation_status: str
	current_round: int


def _as_int(value: str, default: int = 0) -> int:
	try:
		return int(float(value))
	except (TypeError, ValueError):
		return default


def _copy_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
	return [dict(row) for row in rows]


def resolve_open_round(
	round_rows: list[dict[str, str]],
	*,
	expected_round: int,
) -> RoundOpenResolution:
	open_indices = [index for index, row in enumerate(round_rows) if row.get("status", "") == "OPEN"]
	if len(open_indices) != 1:
		raise ValueError(f"Expected exactly one OPEN round, found {len(open_indices)}")

	open_index = open_indices[0]
	open_round = _as_int(round_rows[open_index].get("round_number", "0"))
	if open_round != expected_round:
		raise ValueError(
			f"Simulation current_round={expected_round} does not match OPEN round={open_round}"
		)
	return RoundOpenResolution(open_index=open_index, open_round_number=open_round)


def open_first_round(round_rows: list[dict[str, str]], *, event_at_utc: str) -> StartRoundResult:
	updated_rows = _copy_rows(round_rows)
	first_round_index = next(
		(index for index, row in enumerate(updated_rows) if _as_int(row.get("round_number", "0")) == 1),
		None,
	)
	if first_round_index is None:
		raise ValueError("Round 1 not found")
	if updated_rows[first_round_index].get("status", "") != "PLANNED":
		raise ValueError(
			f"Round 1 must be PLANNED to start (found '{updated_rows[first_round_index].get('status', '')}')"
		)

	updated_rows[first_round_index]["status"] = "OPEN"
	updated_rows[first_round_index]["opened_at_utc"] = event_at_utc
	updated_rows[first_round_index]["closed_at_utc"] = ""

	return StartRoundResult(updated_round_rows=updated_rows, opened_round=1)


def close_open_round_and_advance(
	round_rows: list[dict[str, str]],
	*,
	current_round: int,
	event_at_utc: str,
) -> AdvanceRoundResult:
	if current_round < 1:
		raise ValueError("current_round must be >= 1")

	updated_rows = _copy_rows(round_rows)
	open_resolution = resolve_open_round(updated_rows, expected_round=current_round)
	open_index = open_resolution.open_index
	closed_round = open_resolution.open_round_number

	updated_rows[open_index]["status"] = "CLOSED"
	updated_rows[open_index]["closed_at_utc"] = event_at_utc

	next_round = closed_round + 1
	next_round_index = next(
		(
			index
			for index, row in enumerate(updated_rows)
			if _as_int(row.get("round_number", "0")) == next_round
		),
		None,
	)

	opened_round: int | None = None
	simulation_status = "STARTED"
	new_current_round = closed_round

	if next_round_index is not None:
		if updated_rows[next_round_index].get("status", "") != "PLANNED":
			raise ValueError(
				f"Next round {next_round} must be PLANNED to open (found '{updated_rows[next_round_index].get('status', '')}')"
			)
		updated_rows[next_round_index]["status"] = "OPEN"
		updated_rows[next_round_index]["opened_at_utc"] = event_at_utc
		updated_rows[next_round_index]["closed_at_utc"] = ""
		opened_round = next_round
		new_current_round = next_round
	else:
		simulation_status = "ENDED"

	return AdvanceRoundResult(
		updated_round_rows=updated_rows,
		closed_round=closed_round,
		opened_round=opened_round,
		simulation_status=simulation_status,
		current_round=new_current_round,
	)


def undo_latest_round_transition(
	round_rows: list[dict[str, str]],
	*,
	simulation_status: str,
) -> UndoRoundResult:
	if simulation_status not in {"STARTED", "ENDED"}:
		raise ValueError(
			f"Simulation must be STARTED or ENDED to undo round (found '{simulation_status}')"
		)

	updated_rows = _copy_rows(round_rows)
	open_indices = [index for index, row in enumerate(updated_rows) if row.get("status", "") == "OPEN"]
	rolled_back_open_round: int | None = None

	if simulation_status == "STARTED":
		if len(open_indices) != 1:
			raise ValueError(f"Expected exactly one OPEN round in STARTED state (found {len(open_indices)})")
		open_index = open_indices[0]
		rolled_back_open_round = _as_int(updated_rows[open_index].get("round_number", "0"))
		reopened_round = rolled_back_open_round - 1
		if reopened_round < 1:
			raise ValueError("No previous closed round available to undo")

		target_index = next(
			(
				index
				for index, row in enumerate(updated_rows)
				if _as_int(row.get("round_number", "0")) == reopened_round
			),
			None,
		)
		if target_index is None:
			raise ValueError(f"Round {reopened_round} not found")
		if updated_rows[target_index].get("status", "") != "CLOSED":
			raise ValueError(
				f"Round {reopened_round} must be CLOSED to undo (found '{updated_rows[target_index].get('status', '')}')"
			)

		updated_rows[open_index]["status"] = "PLANNED"
		updated_rows[open_index]["opened_at_utc"] = ""
		updated_rows[open_index]["closed_at_utc"] = ""
		updated_rows[target_index]["status"] = "OPEN"
		updated_rows[target_index]["closed_at_utc"] = ""

		return UndoRoundResult(
			updated_round_rows=updated_rows,
			reopened_round=reopened_round,
			rolled_back_open_round=rolled_back_open_round,
			simulation_status="STARTED",
			current_round=reopened_round,
		)

	if open_indices:
		raise ValueError("ENDED simulation cannot have OPEN rounds")

	closed_round_numbers = [
		_as_int(row.get("round_number", "0")) for row in updated_rows if row.get("status", "") == "CLOSED"
	]
	if not closed_round_numbers:
		raise ValueError("No CLOSED round available to undo")

	reopened_round = max(closed_round_numbers)
	target_index = next(
		(
			index
			for index, row in enumerate(updated_rows)
			if _as_int(row.get("round_number", "0")) == reopened_round
		),
		None,
	)
	if target_index is None:
		raise ValueError(f"Round {reopened_round} not found")

	updated_rows[target_index]["status"] = "OPEN"
	updated_rows[target_index]["closed_at_utc"] = ""

	return UndoRoundResult(
		updated_round_rows=updated_rows,
		reopened_round=reopened_round,
		rolled_back_open_round=None,
		simulation_status="STARTED",
		current_round=reopened_round,
	)


def end_simulation_rounds(round_rows: list[dict[str, str]], *, event_at_utc: str) -> list[dict[str, str]]:
	updated_rows = _copy_rows(round_rows)
	for row in updated_rows:
		status = row.get("status", "")
		if status == "OPEN":
			row["status"] = "CLOSED"
			if not row.get("closed_at_utc", ""):
				row["closed_at_utc"] = event_at_utc
		elif status == "PLANNED":
			row["status"] = "LOCKED"
			row["opened_at_utc"] = ""
			row["closed_at_utc"] = ""
	return updated_rows
