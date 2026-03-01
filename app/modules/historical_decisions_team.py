from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from app.data.csv_manager import read_csv_rows


DECISION_ACTIONS = {"ENTER_DECISION", "UPDATE_DECISION"}


@dataclass(frozen=True)
class TeamDecisionSummary:
	team_id: str
	decision_events: int
	created_decisions: int
	updated_decisions: int
	distinct_rounds: int
	last_event_at_utc: str


def _parse_details(details: str) -> dict[str, str]:
	parsed: dict[str, str] = {}
	for part in details.split(";"):
		chunk = part.strip()
		if not chunk or "=" not in chunk:
			continue
		key, value = chunk.split("=", 1)
		parsed[key.strip()] = value.strip()
	return parsed


def get_historical_decisions_team(
	simulation_id: str,
	root_dir: Path | str = Path("simulations"),
) -> list[TeamDecisionSummary]:
	rows = read_csv_rows(simulation_id, "log.csv")

	aggregates: dict[str, dict[str, object]] = {}

	for row in rows:
		action = row.get("action", "")
		if action not in DECISION_ACTIONS:
			continue

		details = _parse_details(row.get("details", ""))
		team_id = details.get("team_id") or row.get("actor_user_id", "")
		if not team_id:
			continue

		round_value = details.get("round", "")
		event_at = row.get("event_at_utc", "")

		if team_id not in aggregates:
			aggregates[team_id] = {
				"decision_events": 0,
				"created_decisions": 0,
				"updated_decisions": 0,
				"rounds": set(),
				"last_event_at_utc": "",
			}

		agg = aggregates[team_id]
		agg["decision_events"] = int(agg["decision_events"]) + 1
		if action == "ENTER_DECISION":
			agg["created_decisions"] = int(agg["created_decisions"]) + 1
		else:
			agg["updated_decisions"] = int(agg["updated_decisions"]) + 1

		if round_value:
			cast_rounds = agg["rounds"]
			if isinstance(cast_rounds, set):
				cast_rounds.add(round_value)

		last = str(agg["last_event_at_utc"])
		if event_at and (not last or event_at > last):
			agg["last_event_at_utc"] = event_at

	summaries: list[TeamDecisionSummary] = []
	for team_id in sorted(aggregates.keys()):
		agg = aggregates[team_id]
		rounds = agg["rounds"] if isinstance(agg["rounds"], set) else set()
		summaries.append(
			TeamDecisionSummary(
				team_id=team_id,
				decision_events=int(agg["decision_events"]),
				created_decisions=int(agg["created_decisions"]),
				updated_decisions=int(agg["updated_decisions"]),
				distinct_rounds=len(rounds),
				last_event_at_utc=str(agg["last_event_at_utc"]),
			)
		)

	return summaries


def display_historical_decisions_team(
	simulation_id: str,
	root_dir: Path | str = Path("simulations"),
) -> str:
	summaries = get_historical_decisions_team(simulation_id=simulation_id, root_dir=root_dir)
	lines = [f"Simulation: {simulation_id}", "=== Historical Decisions (Team Summary) ==="]

	if not summaries:
		lines.append("No team decision events found in log.csv.")
		return "\n".join(lines)

	for item in summaries:
		lines.append(
			" | ".join(
				[
					f"{item.team_id}",
					f"events={item.decision_events}",
					f"created={item.created_decisions}",
					f"updated={item.updated_decisions}",
					f"distinct_rounds={item.distinct_rounds}",
					f"last_event_at_utc={item.last_event_at_utc}",
				]
			)
		)

	return "\n".join(lines)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Display summary of decision events entered per team from log.csv"
	)
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
	print(display_historical_decisions_team(simulation_id=args.simulation_id, root_dir=args.root))


if __name__ == "__main__":
	main()
