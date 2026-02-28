from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class UIContext:
	simulation_id: str
	root_dir: Path
	admin_user_id: str | None = None
	team_id: str | None = None
	backups_dir: Path | None = None
	archive_dir: Path | None = None


def get_streamlit():
	try:
		return importlib.import_module("streamlit")
	except ModuleNotFoundError as exc:  # pragma: no cover
		raise ModuleNotFoundError(
			"streamlit is required for UI modules. Install it with: pip install streamlit"
		) from exc


def run_action(st, action_name: str, callback: Callable[[], Any]) -> Any | None:
	try:
		result = callback()
		st.success(f"{action_name} completed")
		if result is not None:
			st.write(result)
		return result
	except Exception as error:
		st.error(f"{action_name} failed: {error}")
		return None


def parse_optional_int(raw_value: str, *, field_name: str = "value") -> int | None:
	raw = raw_value.strip()
	if not raw:
		return None
	if raw.isdigit():
		return int(raw)
	raise ValueError(f"{field_name} must be a positive integer when provided")


def parse_csv_list(raw_value: str) -> list[str]:
	return [chunk.strip() for chunk in raw_value.split(",") if chunk.strip()]


def render_basic_context_sidebar(
	st,
	*,
	default_simulation_id: str = "sim_001",
	default_root_dir: str = "simulations",
	include_admin_fields: bool = False,
	include_team_field: bool = False,
	include_storage_fields: bool = False,
) -> UIContext:
	with st.sidebar:
		st.header("Context")
		simulation_id = st.text_input("Simulation ID", value=default_simulation_id)
		root_dir = Path(st.text_input("Simulations Root", value=default_root_dir))

		admin_user_id: str | None = None
		team_id: str | None = None
		backups_dir: Path | None = None
		archive_dir: Path | None = None

		if include_admin_fields:
			admin_user_id = st.text_input("Admin User ID", value="U_ADMIN")

		if include_team_field:
			team_id = st.text_input("Team ID", value="T1")

		if include_storage_fields:
			backups_dir = Path(st.text_input("Backups Root", value="backups"))
			archive_dir = Path(st.text_input("Archive Root", value="archive"))

	return UIContext(
		simulation_id=simulation_id,
		root_dir=root_dir,
		admin_user_id=admin_user_id,
		team_id=team_id,
		backups_dir=backups_dir,
		archive_dir=archive_dir,
	)
