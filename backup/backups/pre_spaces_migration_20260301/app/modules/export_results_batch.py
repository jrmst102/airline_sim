from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from app.modules.display_results import get_market_results, get_team_results
from app.modules.google_sheets_adapter import write_dict_rows_to_worksheet


@dataclass(frozen=True)
class ExportSummary:
	market_rows: int
	team_rows: int
	output_type: str


def _csv_headers(rows: list[dict[str, str]]) -> list[str]:
	if not rows:
		return []
	headers: list[str] = []
	for row in rows:
		for key in row.keys():
			if key not in headers:
				headers.append(key)
	return headers


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
	headers = _csv_headers(rows)
	with path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=headers or ["no_data"])
		writer.writeheader()
		if headers:
			writer.writerows(rows)


def export_results_batch(
	*,
	simulation_id: str,
	root_dir: Path,
	section: str = "both",
	round_number: int | None = None,
	team_id: str | None = None,
	output_type: str,
	output_dir: Path | None = None,
	spreadsheet_id_or_url: str | None = None,
	worksheet_prefix: str = "SimResults",
	credentials_json_path: str | None = None,
) -> ExportSummary:
	normalized_section = section.lower()
	if normalized_section not in {"both", "market", "team"}:
		raise ValueError("section must be one of: both, market, team")
	if output_type not in {"csv", "google-sheet"}:
		raise ValueError("output_type must be one of: csv, google-sheet")

	market_rows: list[dict[str, str]] = []
	team_rows: list[dict[str, str]] = []

	if normalized_section in {"both", "market"}:
		market_rows = get_market_results(
			simulation_id=simulation_id,
			round_number=round_number,
			root_dir=root_dir,
		)

	if normalized_section in {"both", "team"}:
		team_rows = get_team_results(
			simulation_id=simulation_id,
			round_number=round_number,
			team_id=team_id,
			root_dir=root_dir,
		)

	if output_type == "csv":
		if output_dir is None:
			raise ValueError("output_dir is required when output_type=csv")
		output_dir.mkdir(parents=True, exist_ok=True)
		if normalized_section in {"both", "market"}:
			_write_csv(output_dir / f"{simulation_id}_market_results.csv", market_rows)
		if normalized_section in {"both", "team"}:
			_write_csv(output_dir / f"{simulation_id}_team_results.csv", team_rows)
	else:
		if not spreadsheet_id_or_url:
			raise ValueError("spreadsheet_id_or_url is required when output_type=google-sheet")
		if not credentials_json_path:
			raise ValueError("credentials_json_path is required when output_type=google-sheet")

		if normalized_section in {"both", "market"}:
			write_dict_rows_to_worksheet(
				spreadsheet_id_or_url=spreadsheet_id_or_url,
				worksheet_name=f"{worksheet_prefix}_Market",
				headers=_csv_headers(market_rows),
				rows=market_rows,
				credentials_json_path=credentials_json_path,
			)

		if normalized_section in {"both", "team"}:
			write_dict_rows_to_worksheet(
				spreadsheet_id_or_url=spreadsheet_id_or_url,
				worksheet_name=f"{worksheet_prefix}_Team",
				headers=_csv_headers(team_rows),
				rows=team_rows,
				credentials_json_path=credentials_json_path,
			)

	return ExportSummary(
		market_rows=len(market_rows),
		team_rows=len(team_rows),
		output_type=output_type,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Export simulation results to CSV files or Google Sheets",
	)
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--section",
		choices=["both", "market", "team"],
		default="both",
		help="Which result section to export",
	)
	parser.add_argument(
		"--round",
		type=int,
		dest="round_number",
		default=None,
		help="Optional round filter",
	)
	parser.add_argument(
		"--team-id",
		default=None,
		help="Optional team filter for team results",
	)
	parser.add_argument(
		"--output-type",
		choices=["csv", "google-sheet"],
		default="csv",
		help="Where to export results",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=Path("exports"),
		help="Output directory for CSV export",
	)
	parser.add_argument(
		"--spreadsheet-id-or-url",
		default=None,
		help="Target Google spreadsheet ID or URL",
	)
	parser.add_argument(
		"--worksheet-prefix",
		default="SimResults",
		help="Worksheet name prefix for Google Sheets export",
	)
	parser.add_argument(
		"--credentials-json",
		default=None,
		help="Path to Google service-account credentials JSON",
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

	summary = export_results_batch(
		simulation_id=args.simulation_id,
		root_dir=args.root,
		section=args.section,
		round_number=args.round_number,
		team_id=args.team_id,
		output_type=args.output_type,
		output_dir=args.output_dir,
		spreadsheet_id_or_url=args.spreadsheet_id_or_url,
		worksheet_prefix=args.worksheet_prefix,
		credentials_json_path=args.credentials_json,
	)

	print(
		f"Export completed ({summary.output_type}): "
		f"market_rows={summary.market_rows}, team_rows={summary.team_rows}"
	)


if __name__ == "__main__":
	main()
