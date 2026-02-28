from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


APP_DIR = Path(__file__).resolve().parents[1]
IMAGES_DIR = APP_DIR / "images"
NYU_LOGO_PATH = IMAGES_DIR / "nyu_logo.png"
SIM_LOGO_PATH = IMAGES_DIR / "sim_logo.png"
SIMULATION_TITLE = "Airlines"
SIMULATION_SUBTITLE = "Competitive Strategy Simulation"
SIMULATION_COPYRIGHT = "Copyright 2026 by Dr. Jose Mendoza"
ADMIN_VIEW_CAPTION = "Admin operations for setup, lifecycle, backups, restore, results, logs, and users"
TEAM_VIEW_CAPTION = "Team decision entry and results tracking"
DASHBOARD_VIEW_CAPTION = "Unified entry point for Admin and Team operations"
SIDEBAR_CONTEXT_HEADER = "Context"
SIDEBAR_QUICK_CHECKS_HEADER = "Quick Checks"
SIDEBAR_SIMULATION_ID_LABEL = "Simulation ID"
SIDEBAR_SIMULATIONS_ROOT_LABEL = "Simulations Root"
SIDEBAR_ADMIN_USER_ID_LABEL = "Admin User ID"
SIDEBAR_TEAM_ID_LABEL = "Team ID"
SIDEBAR_BACKUPS_ROOT_LABEL = "Backups Root"
SIDEBAR_ARCHIVE_ROOT_LABEL = "Archive Root"
SIDEBAR_CHECK_STATUS_BUTTON = "Check Status"
SIDEBAR_QUICK_MARKET_RESULTS_BUTTON = "Quick Market Results"
ADMIN_QUICK_LIFECYCLE_ACTIONS_LABEL = "Quick lifecycle actions"
ADMIN_TABS = ["Setup", "Parameters", "Backup / Restore / Destroy", "Reporting", "Users"]
ADMIN_SUBHEADER_SETUP = "Setup Simulation"
ADMIN_SUBHEADER_PARAMETERS = "Change Parameters (New Version)"
ADMIN_SUBHEADER_BACKUP = "Backup / Restore / Destroy"
ADMIN_SUBHEADER_REPORTS = "Reports"
ADMIN_SUBHEADER_USERS = "User Management"
ADMIN_SECTION_BACKUP = "Backup"
ADMIN_SECTION_RESTORE = "Restore"
ADMIN_SECTION_DESTROY = "Destroy"
ADMIN_SECTION_CREATE_USER = "Create User"
ADMIN_SECTION_LOCK_UNLOCK_USER = "Lock / Unlock User"
TEAM_TABS = ["Enter Decision", "Results", "History"]
TEAM_SUBHEADER_ENTER_DECISION = "Enter / Update Decision"
TEAM_SUBHEADER_RESULTS = "Results"
TEAM_SUBHEADER_DECISION_HISTORY = "Decision History"
DASHBOARD_VIEW_SWITCH_LABEL = "View"
DASHBOARD_VIEW_OPTIONS = ["Admin", "Team"]


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


def get_brand_logo_paths() -> dict[str, Path]:
	return {
		"nyu": NYU_LOGO_PATH,
		"simulation": SIM_LOGO_PATH,
	}


def render_simulation_header(st) -> None:
	st.title(SIMULATION_TITLE)
	st.caption(SIMULATION_SUBTITLE)


def render_branding(st, *, in_sidebar: bool = False, show_caption: bool = False) -> None:
	target = st.sidebar if in_sidebar else st
	logo_paths = get_brand_logo_paths()

	nyu_logo = logo_paths["nyu"]
	sim_logo = logo_paths["simulation"]

	if nyu_logo.exists():
		target.image(str(nyu_logo), use_container_width=True)
	if sim_logo.exists():
		target.image(str(sim_logo), use_container_width=True)

	if show_caption:
		target.caption(SIMULATION_SUBTITLE)

	target.caption(SIMULATION_COPYRIGHT)


def render_basic_context_sidebar(
	st,
	*,
	default_simulation_id: str = "sim_001",
	default_root_dir: str = "simulations",
	include_admin_fields: bool = False,
	include_team_field: bool = False,
	include_storage_fields: bool = False,
	show_branding: bool = True,
) -> UIContext:
	with st.sidebar:
		if show_branding:
			render_branding(st, in_sidebar=True)
		st.header(SIDEBAR_CONTEXT_HEADER)
		simulation_id = st.text_input(SIDEBAR_SIMULATION_ID_LABEL, value=default_simulation_id)
		root_dir = Path(st.text_input(SIDEBAR_SIMULATIONS_ROOT_LABEL, value=default_root_dir))

		admin_user_id: str | None = None
		team_id: str | None = None
		backups_dir: Path | None = None
		archive_dir: Path | None = None

		if include_admin_fields:
			admin_user_id = st.text_input(SIDEBAR_ADMIN_USER_ID_LABEL, value="U_ADMIN")

		if include_team_field:
			team_id = st.text_input(SIDEBAR_TEAM_ID_LABEL, value="T1")

		if include_storage_fields:
			backups_dir = Path(st.text_input(SIDEBAR_BACKUPS_ROOT_LABEL, value="backups"))
			archive_dir = Path(st.text_input(SIDEBAR_ARCHIVE_ROOT_LABEL, value="archive"))

	return UIContext(
		simulation_id=simulation_id,
		root_dir=root_dir,
		admin_user_id=admin_user_id,
		team_id=team_id,
		backups_dir=backups_dir,
		archive_dir=archive_dir,
	)
