from __future__ import annotations

from pathlib import Path

from app.ui.components import (
	ACTION_CHECK_SIMULATION_STATUS,
	ACTION_DISPLAY_MARKET_RESULTS,
	build_ui_snapshot,
	card,
	card_end,
	configure_page,
	DASHBOARD_VIEW_CAPTION,
	DASHBOARD_VIEW_OPTIONS,
	DASHBOARD_VIEW_SWITCH_LABEL,
	get_streamlit,
	render_right_insight_panel,
	render_sidebar_navigation,
	render_standard_header,
	SIDEBAR_CHECK_STATUS_BUTTON,
	SIDEBAR_QUICK_CHECKS_HEADER,
	SIDEBAR_QUICK_MARKET_RESULTS_BUTTON,
	SIDEBAR_SIMULATION_ID_LABEL,
	SIDEBAR_SIMULATIONS_ROOT_LABEL,
	render_branding,
	run_action,
)
from app.ui.layout import load_css, shell
from app.modules.check_simulation_status import check_simulation_status
from app.modules.display_results import display_results


def render_dashboard() -> None:
	st = get_streamlit()
	configure_page(st)
	load_css()

	with st.sidebar:
		render_branding(st, in_sidebar=True)
		render_sidebar_navigation(st, active_item="Home")
		card(SIDEBAR_QUICK_CHECKS_HEADER)
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
		card_end()

	snapshot = build_ui_snapshot(simulation_id=simulation_id, root_dir=root_dir)
	render_standard_header(simulation_id=simulation_id, snapshot=snapshot)

	def main_renderer() -> None:
		card("Workspace", DASHBOARD_VIEW_CAPTION)
		st.radio(DASHBOARD_VIEW_SWITCH_LABEL, options=DASHBOARD_VIEW_OPTIONS, horizontal=True, key="dashboard_mode")
		card_end()

		card("Simulation Summary")
		kpi_1, kpi_2, kpi_3 = st.columns(3)
		kpi_1.metric("Current Round", f"{snapshot.current_round} of {snapshot.total_rounds}")
		kpi_2.metric("Phase", snapshot.phase)
		kpi_3.metric("Teams", str(snapshot.team_count))
		card_end()

	def insight_renderer() -> None:
		render_right_insight_panel(st, snapshot=snapshot)

	shell(main_renderer, insight_renderer)


def main() -> None:
	render_dashboard()


if __name__ == "__main__":
	main()
