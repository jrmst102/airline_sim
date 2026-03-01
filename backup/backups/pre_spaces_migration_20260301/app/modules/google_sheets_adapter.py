from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class WorksheetData:
	headers: list[str]
	rows: list[dict[str, str]]


def _import_gspread_deps():
	try:
		import gspread
		from google.oauth2.service_account import Credentials
	except ModuleNotFoundError as exc:
		raise ModuleNotFoundError(
			"Google Sheets support requires optional dependencies. "
			"Install with: pip install gspread google-auth"
		) from exc
	return gspread, Credentials


def normalize_spreadsheet_id(value: str) -> str:
	raw_value = value.strip()
	if not raw_value:
		raise ValueError("spreadsheet id/url cannot be empty")

	if raw_value.startswith("http://") or raw_value.startswith("https://"):
		parsed = urlparse(raw_value)
		path_parts = [segment for segment in parsed.path.split("/") if segment]
		if "d" in path_parts:
			d_index = path_parts.index("d")
			if d_index + 1 < len(path_parts):
				return path_parts[d_index + 1]

		query = parse_qs(parsed.query)
		if "id" in query and query["id"]:
			return query["id"][0]

		raise ValueError("Unable to extract spreadsheet id from URL")

	return raw_value


def _build_client(credentials_json_path: str):
	gspread, Credentials = _import_gspread_deps()
	scopes = [
		"https://www.googleapis.com/auth/spreadsheets",
		"https://www.googleapis.com/auth/drive",
	]
	credentials = Credentials.from_service_account_file(credentials_json_path, scopes=scopes)
	return gspread.authorize(credentials)


def read_worksheet_as_dicts(
	*,
	spreadsheet_id_or_url: str,
	worksheet_name: str,
	credentials_json_path: str,
) -> WorksheetData:
	client = _build_client(credentials_json_path)
	spreadsheet_id = normalize_spreadsheet_id(spreadsheet_id_or_url)
	spreadsheet = client.open_by_key(spreadsheet_id)
	worksheet = spreadsheet.worksheet(worksheet_name)

	values = worksheet.get_all_values()
	if not values:
		return WorksheetData(headers=[], rows=[])

	headers = [header.strip() for header in values[0]]
	rows: list[dict[str, str]] = []
	for raw_row in values[1:]:
		if all(not str(cell).strip() for cell in raw_row):
			continue
		row: dict[str, str] = {}
		for index, header in enumerate(headers):
			if not header:
				continue
			value = raw_row[index] if index < len(raw_row) else ""
			row[header] = str(value).strip()
		rows.append(row)

	return WorksheetData(headers=headers, rows=rows)


def write_dict_rows_to_worksheet(
	*,
	spreadsheet_id_or_url: str,
	worksheet_name: str,
	headers: list[str],
	rows: list[dict[str, Any]],
	credentials_json_path: str,
) -> None:
	client = _build_client(credentials_json_path)
	spreadsheet_id = normalize_spreadsheet_id(spreadsheet_id_or_url)
	spreadsheet = client.open_by_key(spreadsheet_id)

	try:
		worksheet = spreadsheet.worksheet(worksheet_name)
	except Exception:
		worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=max(8, len(headers) + 2))

	worksheet.clear()

	if not headers:
		worksheet.update("A1", [["No data"]])
		return

	values = [headers]
	for row in rows:
		values.append([str(row.get(header, "")) for header in headers])

	worksheet.update("A1", values)
