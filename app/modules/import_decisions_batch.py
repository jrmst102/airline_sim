from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from app.modules.enter_decisions import enter_decision
from app.modules.google_sheets_adapter import read_worksheet_as_dicts


REQUIRED_COLUMNS = [
	"team_id",
	"flights_per_day",
	"pricing_posture",
	"branding_level",
	"product_strategy",
]


@dataclass(frozen=True)
class ImportFailure:
	line_number: int
	team_id: str
	reason: str


@dataclass(frozen=True)
class ImportSummary:
	total_rows: int
	successful_rows: int
	failed_rows: int
	failures: list[ImportFailure]


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
	if not csv_path.exists():
		raise FileNotFoundError(f"CSV file not found: {csv_path}")
	with csv_path.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		if not reader.fieldnames:
			raise ValueError(f"CSV missing header row: {csv_path}")
		return [dict(row) for row in reader]


def _read_google_sheet_rows(
	*,
	spreadsheet_id_or_url: str,
	worksheet_name: str,
	credentials_json_path: str,
) -> list[dict[str, str]]:
	worksheet_data = read_worksheet_as_dicts(
		spreadsheet_id_or_url=spreadsheet_id_or_url,
		worksheet_name=worksheet_name,
		credentials_json_path=credentials_json_path,
	)
	return worksheet_data.rows


def _parse_int(raw_value: str, field_name: str) -> int:
	try:
		return int(str(raw_value).strip())
	except (TypeError, ValueError) as exc:
		raise ValueError(f"invalid {field_name}='{raw_value}'") from exc


def _parse_float(raw_value: str, field_name: str) -> float:
	try:
		return float(str(raw_value).strip())
	except (TypeError, ValueError) as exc:
		raise ValueError(f"invalid {field_name}='{raw_value}'") from exc


def _parse_optional_int(raw_value: str | None) -> int | None:
	if raw_value is None:
		return None
	raw = str(raw_value).strip()
	if not raw:
		return None
	return _parse_int(raw, "round")


def _validate_columns(rows: list[dict[str, str]]) -> None:
	if not rows:
		return
	available = {key for key in rows[0].keys()}
	missing = [column for column in REQUIRED_COLUMNS if column not in available]
	if missing:
		raise ValueError(f"Missing required columns: {', '.join(missing)}")


def import_decisions_batch(
	*,
	simulation_id: str,
	root_dir: Path,
	rows: list[dict[str, str]],
	strict: bool = False,
) -> ImportSummary:
	_validate_columns(rows)
	failures: list[ImportFailure] = []
	successful_rows = 0

	for index, row in enumerate(rows, start=2):
		team_id = str(row.get("team_id", "")).strip()
		try:
			enter_decision(
				simulation_id=simulation_id,
				team_id=team_id,
				flights_per_day=_parse_int(row.get("flights_per_day", ""), "flights_per_day"),
				pricing_posture=str(row.get("pricing_posture", "")).strip(),
				branding_level=str(row.get("branding_level", "")).strip(),
				product_strategy=str(row.get("product_strategy", "")).strip(),
				round_number=_parse_optional_int(row.get("round_number")),
				root_dir=root_dir,
			)
			successful_rows += 1
		except Exception as exc:
			failure = ImportFailure(line_number=index, team_id=team_id or "<missing>", reason=str(exc))
			failures.append(failure)
			if strict:
				break

	return ImportSummary(
		total_rows=len(rows),
		successful_rows=successful_rows,
		failed_rows=len(failures),
		failures=failures,
	)


def _parse_cli_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Import decisions in batch from CSV or Google Sheets",
	)
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--input-type",
		choices=["csv", "google-sheet"],
		default="csv",
		help="Input source type",
	)
	parser.add_argument("--csv-path", type=Path, default=None, help="Path to decisions CSV")
	parser.add_argument(
		"--spreadsheet-id-or-url",
		default=None,
		help="Google spreadsheet ID or URL",
	)
	parser.add_argument(
		"--worksheet",
		default="Decisions",
		help="Worksheet name for Google Sheets input",
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
	parser.add_argument(
		"--strict",
		action="store_true",
		help="Stop on first failed row",
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_cli_args()

	if args.input_type == "csv":
		if args.csv_path is None:
			raise ValueError("--csv-path is required when --input-type=csv")
		rows = _read_csv_rows(args.csv_path)
	else:
		if not args.spreadsheet_id_or_url:
			raise ValueError("--spreadsheet-id-or-url is required when --input-type=google-sheet")
		if not args.credentials_json:
			raise ValueError("--credentials-json is required when --input-type=google-sheet")
		rows = _read_google_sheet_rows(
			spreadsheet_id_or_url=args.spreadsheet_id_or_url,
			worksheet_name=args.worksheet,
			credentials_json_path=args.credentials_json,
		)

	summary = import_decisions_batch(
		simulation_id=args.simulation_id,
		root_dir=args.root,
		rows=rows,
		strict=args.strict,
	)

	print(
		f"Imported decisions for simulation={args.simulation_id}: "
		f"total={summary.total_rows}, success={summary.successful_rows}, failed={summary.failed_rows}"
	)
	for failure in summary.failures:
		print(f"  line={failure.line_number} team={failure.team_id} error={failure.reason}")


if __name__ == "__main__":
	main()
