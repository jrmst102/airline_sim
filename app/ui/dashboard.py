from __future__ import annotations

from pathlib import Path

from app.ui.components import (
	ACTION_CHECK_SIMULATION_STATUS,
	ACTION_DISPLAY_MARKET_RESULTS,
	apply_streamlit_theme,
	build_ui_snapshot,
	DASHBOARD_VIEW_CAPTION,
	DASHBOARD_VIEW_OPTIONS,
	DASHBOARD_VIEW_SWITCH_LABEL,
	get_streamlit,
	render_card,
	render_right_insight_panel,
	render_sidebar_navigation,
	SIDEBAR_CHECK_STATUS_BUTTON,
	SIDEBAR_QUICK_CHECKS_HEADER,
	SIDEBAR_QUICK_MARKET_RESULTS_BUTTON,
	SIDEBAR_SIMULATION_ID_LABEL,
	SIDEBAR_SIMULATIONS_ROOT_LABEL,
	SIMULATION_SUBTITLE,
	SIMULATION_TITLE,
	render_branding,
	render_top_header_bar,
	run_action,
)
from app.modules.check_simulation_status import check_simulation_status
from app.modules.display_results import display_results
from app.ui.admin_view import render_admin_view
from app.ui.team_view import render_team_view


def render_dashboard() -> None:
	st = get_streamlit()
	st.set_page_config(page_title=SIMULATION_TITLE, layout="wide")
	apply_streamlit_theme(st)

	with st.sidebar:
		render_branding(st, in_sidebar=True)
		render_sidebar_navigation(st, active_item="Home")
		st.header(SIDEBAR_QUICK_CHECKS_HEADER)
		simulation_id = st.text_input(
			SIDEBAR_SIMULATION_ID_LABEL,
			value="sim_001",
			key="dashboard_quick_simulation_id",
		)
		root_dir = Path(
			st.text_input(
				SIDEBAR_SIMULATIONS_ROOT_LABEL,
				value="simulations",
				key="dashboard_quick_root_dir",
			)
		)

		if st.button(SIDEBAR_CHECK_STATUS_BUTTON, use_container_width=True, key="dashboard_quick_check_status"):
			run_action(
				st,
				ACTION_CHECK_SIMULATION_STATUS,
				lambda: check_simulation_status(simulation_id=simulation_id, root_dir=root_dir),
			)

		if st.button(
			SIDEBAR_QUICK_MARKET_RESULTS_BUTTON,
			use_container_width=True,
			key="dashboard_quick_market_results",
		):
			run_action(
				st,
				ACTION_DISPLAY_MARKET_RESULTS,
				lambda: display_results(
					simulation_id=simulation_id,
					section="market",
					root_dir=root_dir,
				),
			)

	admin_mode = DASHBOARD_VIEW_OPTIONS[0]
	snapshot = build_ui_snapshot(simulation_id=simulation_id, root_dir=root_dir)
	render_top_header_bar(st, simulation_id=simulation_id, snapshot=snapshot)
	st.caption(f"{SIMULATION_SUBTITLE} • {DASHBOARD_VIEW_CAPTION}")

	main_col, insight_col = st.columns([5, 1], vertical_alignment="top")
	with main_col:
		kpi_1, kpi_2, kpi_3 = st.columns(3)
		kpi_1.metric("Current Round", f"{snapshot.current_round} of {snapshot.total_rounds}")
		kpi_2.metric("Phase", snapshot.phase)
		kpi_3.metric("Teams", str(snapshot.team_count))

		with render_card(st, "Workspace"):
			st.write("Choose the operating view for this session.")
			st.radio(DASHBOARD_VIEW_SWITCH_LABEL, options=DASHBOARD_VIEW_OPTIONS, horizontal=True, key="dashboard_mode")

	with insight_col:
		render_right_insight_panel(st, snapshot=snapshot)

	mode = st.session_state.get("dashboard_mode", admin_mode)

	if mode == admin_mode:
		render_admin_view()
	else:
		render_team_view()


def main() -> None:
	render_dashboard()


if __name__ == "__main__":
	main()
