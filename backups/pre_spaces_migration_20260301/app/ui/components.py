from __future__ import annotations

import csv
import html
import importlib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.ui.layout import load_css, render_header


APP_DIR = Path(__file__).resolve().parents[1]
IMAGES_DIR = APP_DIR / "images"
NYU_LOGO_PATH = IMAGES_DIR / "nyu_logo.png"
SIM_LOGO_PATH = IMAGES_DIR / "sim_logo.png"

SIMULATION_TITLE = "Airlines"
SIMULATION_SUBTITLE = "Competitive Strategy Simulation"
SIMULATION_COPYRIGHT = "Copyright 2026 by Dr. Jose Mendoza"

ADMIN_VIEW_CAPTION = "Admin operations for setup, lifecycle, backups, restore, results, logs, and users"
DASHBOARD_VIEW_CAPTION = "Unified entry point for Admin and Team operations"
TEAM_VIEW_CAPTION = "Team decision entry and results tracking"

DASHBOARD_VIEW_OPTIONS = ["Admin", "Team"]
DASHBOARD_VIEW_SWITCH_LABEL = "View"

SIDEBAR_CONTEXT_HEADER = "Context"
SIDEBAR_ADMIN_USER_ID_LABEL = "Admin User ID"
SIDEBAR_ARCHIVE_ROOT_LABEL = "Archive Root"
SIDEBAR_BACKUPS_ROOT_LABEL = "Backups Root"
SIDEBAR_CHECK_STATUS_BUTTON = "Check Status"
SIDEBAR_QUICK_CHECKS_HEADER = "Quick Checks"
SIDEBAR_QUICK_MARKET_RESULTS_BUTTON = "Quick Market Results"
SIDEBAR_SIMULATION_ID_LABEL = "Simulation ID"
SIDEBAR_SIMULATIONS_ROOT_LABEL = "Simulations Root"
SIDEBAR_TEAM_ID_LABEL = "Team ID"

ADMIN_BUTTON_CHECK_STATUS = "Check Status"
ADMIN_BUTTON_CREATE_BACKUP = "Create Backup"
ADMIN_BUTTON_DESTROY_SIMULATION = "Destroy Simulation"
ADMIN_BUTTON_DISPLAY_LOG = "Display Log"
ADMIN_BUTTON_DISPLAY_RESULTS = "Display Results"
ADMIN_BUTTON_END = "End"
ADMIN_BUTTON_HISTORICAL_DECISIONS = "Historical Decisions"
ADMIN_BUTTON_LIST_USERS = "List Users"
ADMIN_BUTTON_LOCK = "Lock"
ADMIN_BUTTON_MOVE_NEXT = "Move Next"
ADMIN_BUTTON_REFRESH_STATUS = "Refresh Status"
ADMIN_BUTTON_RESTORE_BACKUP = "Restore Backup"
ADMIN_BUTTON_START = "Start"
ADMIN_BUTTON_UNDO = "Undo"
ADMIN_BUTTON_UNLOCK = "Unlock"

ADMIN_DESTROY_MODE_OPTIONS = ["archive", "delete"]
ADMIN_FORM_SUBMIT_CREATE_USER = "Create User"
ADMIN_FORM_SUBMIT_PARAMETERS = "Apply Parameter Version"
ADMIN_FORM_SUBMIT_SETUP = "Run Setup"

ADMIN_LABEL_BACKUP_ZIP_PATH = "Backup zip path"
ADMIN_LABEL_DESTROY_MODE = "Destroy mode"
ADMIN_LABEL_OVERWRITE_SIMULATION = "Overwrite if simulation folder exists"
ADMIN_LABEL_OVERWRITE_TARGET = "Overwrite target if exists"
ADMIN_LABEL_PASSWORD = "Password"
ADMIN_LABEL_RESTORE_AS_SIMULATION_ID = "Restore as simulation_id (optional)"
ADMIN_LABEL_RESULTS_SECTION = "Results Section"
ADMIN_LABEL_ROLE = "Role"
ADMIN_LABEL_ROUND_FILTER = "Round filter (optional)"
ADMIN_LABEL_SIMULATION_NAME = "Simulation Name"
ADMIN_LABEL_TARGET_USERNAME = "Target username"
ADMIN_LABEL_TEAM_FILTER = "Team filter (optional)"
ADMIN_LABEL_TEAM_ID_FOR_ROLE = "Team ID (for TEAM_* roles)"
ADMIN_LABEL_TEAM_NAMES = "Team Names (comma-separated)"
ADMIN_LABEL_TOTAL_ROUNDS = "Total Rounds"
ADMIN_LABEL_USERNAME = "Username"

ADMIN_QUICK_LIFECYCLE_ACTIONS_LABEL = "Quick lifecycle actions"
ADMIN_RESULTS_SECTION_OPTIONS = ["both", "market", "team"]
ADMIN_ROLE_OPTIONS = ["ADMIN", "TEAM_LEAD", "TEAM_MEMBER"]

ADMIN_SECTION_BACKUP = "Backup"
ADMIN_SECTION_CREATE_USER = "Create User"
ADMIN_SECTION_DESTROY = "Destroy"
ADMIN_SECTION_LOCK_UNLOCK_USER = "Lock / Unlock User"
ADMIN_SECTION_RESTORE = "Restore"

ADMIN_SUBHEADER_BACKUP = "Backup / Restore / Destroy"
ADMIN_SUBHEADER_PARAMETERS = "Change Parameters (New Version)"
ADMIN_SUBHEADER_REPORTS = "Reports"
ADMIN_SUBHEADER_SETUP = "Setup Simulation"
ADMIN_SUBHEADER_USERS = "User Management"

ADMIN_TABS = ["Setup", "Parameters", "Backup / Restore / Destroy", "Reporting", "Users"]

TEAM_BUTTON_CHECK_SIMULATION_STATUS = "Check Simulation Status"
TEAM_BUTTON_DISPLAY_RESULTS = "Display Results"
TEAM_BUTTON_SHOW_TEAM_DECISION_HISTORY = "Show Team Decision History"
TEAM_BUTTON_SHOW_TEAM_RESULTS = "Show Team Results"

TEAM_FORM_SUBMIT_DECISION = "Submit Decision"
TEAM_LABEL_FLIGHTS_PER_DAY = "Flights per Day (0–5)"
TEAM_LABEL_PRICE_BUSINESS = "Business Seat Price ($)"
TEAM_LABEL_PRICE_LEISURE = "Leisure Seat Price ($)"
TEAM_LABEL_BRANDING_LEVEL = "Branding Level"
TEAM_LABEL_PRODUCT_STRATEGY = "Product Strategy"
TEAM_LABEL_ROUND_FILTER = "Round filter (optional)"
TEAM_LABEL_ROUND_OPTIONAL_OPEN = "Round (optional, must be OPEN)"
TEAM_LABEL_SECTION = "Section"
TEAM_SECTION_OPTIONS = ["team", "market", "both"]

TEAM_SUBHEADER_DECISION_HISTORY = "Decision History"
TEAM_SUBHEADER_ENTER_DECISION = "Enter / Update Decision"
TEAM_SUBHEADER_RESULTS = "Results"
TEAM_TABS = ["Enter Decision", "Results", "History"]

PRIMARY_ACCENT = "#2563EB"
SUCCESS_COLOR = "#16A34A"
WARNING_COLOR = "#F59E0B"
DANGER_COLOR = "#DC2626"
NEUTRAL_BG = "#F3F4F6"
HEADER_BG = "#1F2937"

PRIMARY_NAV_ITEMS = [
	"Home",
	"Enter Decisions",
	"Display Current Decisions",
	"Move to Next Round",
	"Display Round Results",
	"Display End Results",
	"Industry Report",
	"Change Parameters (Live)",
	"Backup Simulation",
	"Restore Simulation",
	"End Simulation",
	"Destroy Simulation",
]

ACTION_CHECK_SIMULATION_STATUS = "Check Simulation Status"
ACTION_BACKUP_SIMULATION = "Backup Simulation"
ACTION_CHANGE_PARAMETERS_LIVE = "Change Parameters Live"
ACTION_CREATE_USER = "Create User"
ACTION_DESTROY_SIMULATION = "Destroy Simulation"
ACTION_DISPLAY_LOG = "Display Log"
ACTION_DISPLAY_MARKET_RESULTS = "Display Market Results"
ACTION_DISPLAY_RESULTS = "Display Results"
ACTION_DISPLAY_TEAM_RESULTS = "Display Team Results"
ACTION_END_SIMULATION = "End Simulation"
ACTION_ENTER_DECISION = "Enter Decision"
ACTION_HISTORICAL_DECISIONS = "Historical Decisions"
ACTION_LIST_USERS = "List Users"
ACTION_LOCK_USER = "Lock User"
ACTION_MOVE_NEXT_ROUND = "Move Next Round"
ACTION_RESTORE_SIMULATION = "Restore Simulation"
ACTION_SETUP_SIMULATION = "Setup Simulation"
ACTION_START_SIMULATION = "Start Simulation"
ACTION_TEAM_DECISION_HISTORY = "Team Decision History"
ACTION_UNDO_ROUND = "Undo Round"
ACTION_UNLOCK_USER = "Unlock User"


@dataclass(frozen=True)
class UIContext:
	simulation_id: str
	root_dir: Path
	admin_user_id: str | None = None
	team_id: str | None = None
	backups_dir: Path | None = None
	archive_dir: Path | None = None
	compact_layout: bool = False


@dataclass(frozen=True)
class UISnapshot:
	status: str
	current_round: int
	total_rounds: int
	phase: str
	team_count: int
	market_share: float | None
	net_profit: float | None
	cash_balance: float | None
	competitor_avg_price: float | None
	demand_forecast: float | None


def get_streamlit():
	try:
		return importlib.import_module("streamlit")
	except ModuleNotFoundError as exc:  # pragma: no cover
		raise ModuleNotFoundError(
			"streamlit is required for UI modules. Install it with: pip install streamlit"
		) from exc


def configure_page(st, *, page_title: str = SIMULATION_TITLE) -> None:
	if st.session_state.get("_airline_sim_page_configured"):
		return
	st.set_page_config(page_title=page_title, layout="wide", initial_sidebar_state="expanded")
	st.session_state["_airline_sim_page_configured"] = True


def card(title: str, subtitle: str | None = None) -> None:
	st = get_streamlit()
	safe_title = html.escape(title)
	safe_subtitle = html.escape(subtitle) if subtitle is not None else None
	st.markdown('<div class="card">', unsafe_allow_html=True)
	st.markdown(f'<div class="card-title">{safe_title}</div>', unsafe_allow_html=True)
	if safe_subtitle:
		st.markdown(f'<div class="card-sub">{safe_subtitle}</div>', unsafe_allow_html=True)
	st.markdown('<div class="card-divider"></div>', unsafe_allow_html=True)


def card_end() -> None:
	st = get_streamlit()
	st.markdown("</div>", unsafe_allow_html=True)


def render_standard_header(*, simulation_id: str, snapshot: UISnapshot) -> None:
	round_label = f"Round {snapshot.current_round}/{snapshot.total_rounds}"
	kpis = {
		"Cash": _fmt_money(snapshot.cash_balance),
		"Mkt Share": _fmt_percent(snapshot.market_share),
		"Net Profit": _fmt_money(snapshot.net_profit),
		"Alerts": "0",
	}
	render_header(sim_id=simulation_id, round_label=round_label, phase=snapshot.phase, kpis=kpis)


def apply_streamlit_theme(st, *, compact_layout: bool = False) -> None:
	sidebar_width = 220 if compact_layout else 260
	container_max_width = 1060 if compact_layout else 1140
	card_gap = "0.45rem" if compact_layout else "0.55rem"
	st.markdown(
		f"""
		<style>
		:root {{
			--acs-primary: {PRIMARY_ACCENT};
			--acs-success: {SUCCESS_COLOR};
			--acs-warning: {WARNING_COLOR};
			--acs-danger: {DANGER_COLOR};
			--acs-neutral: {NEUTRAL_BG};
			--acs-header: {HEADER_BG};
		}}
		html, body, [class*="css"] {{
			font-family: Inter, Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
		}}
		[data-testid="stAppViewContainer"] {{
			background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
		}}
		.main .block-container {{
			max-width: {container_max_width}px;
			padding-top: 0.65rem;
			padding-bottom: 0.8rem;
			padding-left: 0.85rem;
			padding-right: 0.85rem;
		}}
		[data-testid="stSidebar"] {{
			min-width: {sidebar_width}px;
			max-width: {sidebar_width}px;
			background: #e8eefc;
			border-right: 1px solid #c9d7f4;
		}}
		div[data-testid="stVerticalBlock"] > div:has(> .acs-topbar) {{
			margin-bottom: 0.6rem;
		}}
		.acs-topbar {{
			height: 90px;
			background: linear-gradient(90deg, var(--acs-header) 0%, #1e3a8a 55%, #2563eb 100%);
			border-radius: 12px;
			padding: 0.5rem 1rem;
			color: #f8fafc;
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 0.75rem;
		}}
		.acs-topbar-title {{ font-size: 20px; font-weight: 700; line-height: 1.2; }}
		.acs-topbar-subtitle {{ font-size: 14px; color: #dbeafe; }}
		.acs-topbar-mid {{ font-size: 14px; text-align: center; color: #dbeafe; }}
		.acs-topbar-kpis {{
			display: flex;
			flex-wrap: wrap;
			justify-content: flex-end;
			gap: 0.4rem;
		}}
		.acs-kpi-chip {{
			background: rgba(255,255,255,0.14);
			border: 1px solid rgba(255,255,255,0.2);
			border-radius: 10px;
			padding: 0.25rem 0.55rem;
			font-size: 12px;
			white-space: nowrap;
		}}
		.acs-kpi-chip strong {{ font-size: 13px; color: #fff; margin-left: 0.2rem; }}
		.acs-nav-header {{
			font-size: 13px;
			font-weight: 700;
			letter-spacing: 0.03em;
			text-transform: uppercase;
			color: #334155;
			margin: 0.1rem 0 0.2rem 0;
		}}
		.acs-nav-item {{
			font-size: 14px;
			line-height: 1.4;
			padding: 0.25rem 0.35rem;
			border-radius: 8px;
			margin-bottom: 0.1rem;
		}}
		.acs-nav-item.active {{
			background: #dbeafe;
			color: #1d4ed8;
			font-weight: 600;
		}}
		.acs-card-title {{ font-size: 16px; font-weight: 700; margin-bottom: 0.2rem; }}
		.acs-divider {{ border-top: 1px solid #dbe4f6; margin: 0.2rem 0 0.7rem 0; }}
		[data-testid="stMetric"] {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.35rem 0.55rem; }}
		[data-testid="stHorizontalBlock"] {{ gap: {card_gap}; }}
		.stButton > button {{
			border-radius: 10px;
			height: 2.2rem;
			font-size: 14px;
			font-weight: 600;
			border: 1px solid #bfdbfe;
		}}
		[data-baseweb="tab-list"] button {{ font-size: 14px; }}
		[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}
		.acs-compact-text {{ font-size: 13px; color: #334155; }}
		@media (max-width: 1280px) {{
			.main .block-container {{ max-width: 980px; padding-left: 0.65rem; padding-right: 0.65rem; }}
			[data-testid="stSidebar"] {{ min-width: 220px; max-width: 220px; }}
		}}
		</style>
		""",
		unsafe_allow_html=True,
	)


def _parse_float(raw: str | None) -> float | None:
	if raw is None:
		return None
	try:
		return float(raw)
	except (TypeError, ValueError):
		return None


def _fmt_money(value: float | None) -> str:
	if value is None:
		return "--"
	return f"${value:,.0f}"


def _fmt_percent(value: float | None) -> str:
	if value is None:
		return "--"
	return f"{value:.1f}%"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
	if not path.exists():
		return []
	with path.open("r", newline="", encoding="utf-8") as handle:
		return list(csv.DictReader(handle))


def build_ui_snapshot(*, simulation_id: str, root_dir: Path, team_id: str | None = None) -> UISnapshot:
	simulation_rows = _read_csv_rows(root_dir / simulation_id / "simulation.csv")
	simulation_row = simulation_rows[0] if simulation_rows else {}
	status = simulation_row.get("status", "CREATED")
	current_round = int(simulation_row.get("current_round", "0") or 0)
	total_rounds = int(simulation_row.get("total_rounds", "0") or 0)
	phase = "Decision"
	if status == "ENDED":
		phase = "Closed"
	elif status == "STARTED":
		phase = "Results"

	teams = _read_csv_rows(root_dir / simulation_id / "teams.csv")
	team_count = len(teams)

	team_rows = _read_csv_rows(root_dir / simulation_id / "round_results_team.csv")
	if team_id:
		team_rows = [row for row in team_rows if row.get("team_id") == team_id]
	team_rows = sorted(team_rows, key=lambda row: int(row.get("round_number", "0") or 0))
	latest_team = team_rows[-1] if team_rows else {}

	market_rows = _read_csv_rows(root_dir / simulation_id / "round_results_market.csv")
	market_rows = sorted(market_rows, key=lambda row: int(row.get("round_number", "0") or 0))
	latest_market = market_rows[-1] if market_rows else {}

	profit = _parse_float(latest_team.get("profit"))
	market_share_ratio = _parse_float(latest_team.get("market_share_volume"))
	market_share = market_share_ratio * 100 if market_share_ratio is not None else None
	forecast = _parse_float(latest_market.get("total_carried"))
	avg_economy = _parse_float(latest_market.get("avg_price_economy"))
	avg_premium = _parse_float(latest_market.get("avg_price_premium"))
	competitor_avg_price = None
	if avg_economy is not None and avg_premium is not None:
		competitor_avg_price = (avg_economy + avg_premium) / 2

	return UISnapshot(
		status=status,
		current_round=current_round,
		total_rounds=total_rounds,
		phase=phase,
		team_count=team_count,
		market_share=market_share,
		net_profit=profit,
		cash_balance=profit,
		competitor_avg_price=competitor_avg_price,
		demand_forecast=forecast,
	)


def render_top_header_bar(st, *, simulation_id: str, snapshot: UISnapshot) -> None:
	render_standard_header(simulation_id=simulation_id, snapshot=snapshot)


def render_sidebar_navigation(st, *, active_item: str | None = None) -> None:
	card("Navigation")
	for item in PRIMARY_NAV_ITEMS:
		prefix = "• " if item != active_item else "➤ "
		st.write(f"{prefix}{item}")
	card_end()


@contextmanager
def render_card(st, title: str):
	card(title)
	try:
		yield
	finally:
		card_end()


def render_right_insight_panel(st, *, snapshot: UISnapshot) -> None:
	card("Insight Panel")
	st.metric("Strategic Position", "Leader" if (snapshot.market_share or 0) >= 30 else "Balanced")
	st.metric("Competitor Avg Price", _fmt_money(snapshot.competitor_avg_price))
	demand_delta = None
	if snapshot.demand_forecast is not None:
		demand_delta = "Latest round"
	st.metric(
		"Demand Forecast",
		f"{int(snapshot.demand_forecast):,}" if snapshot.demand_forecast is not None else "--",
		delta=demand_delta,
	)
	st.metric("Cost Snapshot", _fmt_money(snapshot.cash_balance))
	card_end()

	card("Market Share")
	share_value = snapshot.market_share or 0.0
	st.progress(min(max(share_value / 100, 0.0), 1.0))
	st.caption(f"{_fmt_percent(snapshot.market_share)} share volume")
	card_end()


def render_insight_drawer(st, *, snapshot: UISnapshot) -> None:
	with st.expander("Insight Panel", expanded=False):
		render_right_insight_panel(st, snapshot=snapshot)


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
	load_css()
	card(SIMULATION_TITLE, SIMULATION_SUBTITLE)
	card_end()


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
	key_prefix: str = "context",
	include_admin_fields: bool = False,
	include_team_field: bool = False,
	include_storage_fields: bool = False,
	include_layout_toggle: bool = False,
	show_branding: bool = True,
) -> UIContext:
	with st.sidebar:
		compact_layout = False
		if include_layout_toggle:
			compact_layout = st.toggle(
				"Compact 1280×800 layout",
				value=False,
				key=f"{key_prefix}_compact_layout",
			)

		if show_branding:
			render_branding(st, in_sidebar=True)
		st.header(SIDEBAR_CONTEXT_HEADER)
		simulation_id = st.text_input(
			SIDEBAR_SIMULATION_ID_LABEL,
			value=default_simulation_id,
			key=f"{key_prefix}_simulation_id",
		)
		root_dir = Path(
			st.text_input(
				SIDEBAR_SIMULATIONS_ROOT_LABEL,
				value=default_root_dir,
				key=f"{key_prefix}_root_dir",
			)
		)

		admin_user_id: str | None = None
		team_id: str | None = None
		backups_dir: Path | None = None
		archive_dir: Path | None = None

		if include_admin_fields:
			admin_user_id = st.text_input(
				SIDEBAR_ADMIN_USER_ID_LABEL,
				value="U_ADMIN",
				key=f"{key_prefix}_admin_user_id",
			)

		if include_team_field:
			team_id = st.text_input(
				SIDEBAR_TEAM_ID_LABEL,
				value="T1",
				key=f"{key_prefix}_team_id",
			)

		if include_storage_fields:
			backups_dir = Path(
				st.text_input(
					SIDEBAR_BACKUPS_ROOT_LABEL,
					value="backups",
					key=f"{key_prefix}_backups_dir",
				)
			)
			archive_dir = Path(
				st.text_input(
					SIDEBAR_ARCHIVE_ROOT_LABEL,
					value="archive",
					key=f"{key_prefix}_archive_dir",
				)
			)

	return UIContext(
		simulation_id=simulation_id,
		root_dir=root_dir,
		admin_user_id=admin_user_id,
		team_id=team_id,
		backups_dir=backups_dir,
		archive_dir=archive_dir,
		compact_layout=compact_layout,
	)
