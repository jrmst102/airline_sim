from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _simulation_path(root_dir: Path | str, simulation_id: str) -> Path:
	return Path(root_dir) / simulation_id


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
	if not path.exists():
		raise FileNotFoundError(f"Required file not found: {path}")
	with path.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		return list(reader)


def _as_int(value: str, default: int = 0) -> int:
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def _team_name_by_id(simulation_dir: Path) -> dict[str, str]:
	team_rows = _load_csv_rows(simulation_dir / "teams.csv")
	return {row["team_id"]: row["team_name"] for row in team_rows}


def _sorted_by_round(rows: list[dict[str, str]]) -> list[dict[str, str]]:
	return sorted(rows, key=lambda row: _as_int(row.get("round_number", "0")))


def get_team_results(
	simulation_id: str,
	round_number: int | None = None,
	team_id: str | None = None,
	root_dir: Path | str = Path("simulations"),
) -> list[dict[str, str]]:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	rows = _load_csv_rows(simulation_dir / "round_results_team.csv")

	if round_number is not None:
		rows = [row for row in rows if _as_int(row.get("round_number", "0")) == round_number]

	if team_id is not None:
		rows = [row for row in rows if row.get("team_id", "") == team_id]

	team_name_map = _team_name_by_id(simulation_dir)
	for row in rows:
		row["team_name"] = team_name_map.get(row.get("team_id", ""), "")

	return _sorted_by_round(rows)


def get_market_results(
	simulation_id: str,
	round_number: int | None = None,
	root_dir: Path | str = Path("simulations"),
) -> list[dict[str, str]]:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	rows = _load_csv_rows(simulation_dir / "round_results_market.csv")

	if round_number is not None:
		rows = [row for row in rows if _as_int(row.get("round_number", "0")) == round_number]

	return _sorted_by_round(rows)


def _render_market_results(rows: list[dict[str, str]]) -> list[str]:
	lines = ["=== Market Results ==="]
	if not rows:
		lines.append("No market results available for selected filters.")
		return lines

	for row in rows:
		lines.append(
			" | ".join(
				[
					f"Round {row['round_number']}",
					f"Total Demand={row.get('total_demand', '—')}",
					f"Total Passengers={row.get('total_passengers', '—')}",
					f"Revenue={row.get('total_revenue', '—')}",
					f"Cost={row.get('total_cost', '—')}",
					f"Profit={row.get('total_profit', '—')}",
				]
			)
		)

	return lines


def _render_team_results(rows: list[dict[str, str]]) -> list[str]:
	lines = ["=== Team Results ==="]
	if not rows:
		lines.append("No team results available for selected filters.")
		return lines

	for row in rows:
		team_label = row.get("team_name") or row["team_id"]
		lines.append(
			" | ".join(
				[
					f"Round {row['round_number']}",
					f"{team_label} ({row['team_id']})",
					f"Pax={row.get('passengers', '—')}",
					f"Revenue={row.get('revenue', '—')}",
					f"Cost={row.get('total_cost', '—')}",
					f"Profit={row.get('profit', '—')}",
					f"LF={row.get('load_factor', '—')}",
					f"MS Vol={row.get('market_share_volume', '—')}",
					f"MS Profit={row.get('market_share_profit', '—')}",
				]
			)
		)

	return lines


def display_results(
	simulation_id: str,
	round_number: int | None = None,
	team_id: str | None = None,
	section: str = "both",
	root_dir: Path | str = Path("simulations"),
) -> str:
	normalized_section = section.lower()
	if normalized_section not in {"both", "market", "team"}:
		raise ValueError("section must be one of: both, market, team")

	lines: list[str] = [f"Simulation: {simulation_id}"]
	if round_number is None:
		lines.append("Round Filter: all")
	else:
		lines.append(f"Round Filter: {round_number}")
	if team_id is not None:
		lines.append(f"Team Filter: {team_id}")

	if normalized_section in {"both", "market"}:
		lines.append("")
		lines.extend(
			_render_market_results(
				get_market_results(
					simulation_id=simulation_id,
					round_number=round_number,
					root_dir=root_dir,
				)
			)
		)

	if normalized_section in {"both", "team"}:
		lines.append("")
		lines.extend(
			_render_team_results(
				get_team_results(
					simulation_id=simulation_id,
					round_number=round_number,
					team_id=team_id,
					root_dir=root_dir,
				)
			)
		)

	return "\n".join(lines)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Display simulation results")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--round",
		type=int,
		dest="round_number",
		default=None,
		help="Filter by round number",
	)
	parser.add_argument(
		"--team-id",
		default=None,
		help="Filter team results by team ID",
	)
	parser.add_argument(
		"--section",
		choices=["both", "market", "team"],
		default="both",
		help="Which section of results to display",
	)
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()
	output = display_results(
		simulation_id=args.simulation_id,
		round_number=args.round_number,
		team_id=args.team_id,
		section=args.section,
		root_dir=args.root,
	)
	print(output)


if __name__ == "__main__":
	main()
