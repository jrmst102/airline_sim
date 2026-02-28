from __future__ import annotations

from pathlib import Path

from app.ui.components import (
	ACTION_CHECK_SIMULATION_STATUS,
	ACTION_DISPLAY_MARKET_RESULTS,
	DASHBOARD_VIEW_CAPTION,
	DASHBOARD_VIEW_OPTIONS,
	DASHBOARD_VIEW_SWITCH_LABEL,
	get_streamlit,
	SIDEBAR_CHECK_STATUS_BUTTON,
	SIDEBAR_QUICK_CHECKS_HEADER,
	SIDEBAR_QUICK_MARKET_RESULTS_BUTTON,
	SIDEBAR_SIMULATION_ID_LABEL,
	SIDEBAR_SIMULATIONS_ROOT_LABEL,
	SIMULATION_TITLE,
	render_branding,
	render_simulation_header,
	run_action,
)
from app.modules.check_simulation_status import check_simulation_status
from app.modules.display_results import display_results
from app.ui.admin_view import render_admin_view
from app.ui.team_view import render_team_view


def render_dashboard() -> None:
	st = get_streamlit()
	st.set_page_config(page_title=SIMULATION_TITLE, layout="wide")
	render_branding(st, in_sidebar=False, show_caption=False)
	render_simulation_header(st)
	st.caption(DASHBOARD_VIEW_CAPTION)

	with st.sidebar:
		render_branding(st, in_sidebar=True)
		st.header(SIDEBAR_QUICK_CHECKS_HEADER)
		simulation_id = st.text_input(SIDEBAR_SIMULATION_ID_LABEL, value="sim_001")
		root_dir = Path(st.text_input(SIDEBAR_SIMULATIONS_ROOT_LABEL, value="simulations"))

		if st.button(SIDEBAR_CHECK_STATUS_BUTTON, use_container_width=True):
			run_action(
				st,
				ACTION_CHECK_SIMULATION_STATUS,
				lambda: check_simulation_status(simulation_id=simulation_id, root_dir=root_dir),
			)

		if st.button(SIDEBAR_QUICK_MARKET_RESULTS_BUTTON, use_container_width=True):
			run_action(
				st,
				ACTION_DISPLAY_MARKET_RESULTS,
				lambda: display_results(
					simulation_id=simulation_id,
					section="market",
					root_dir=root_dir,
				),
			)

	mode = st.radio(DASHBOARD_VIEW_SWITCH_LABEL, options=DASHBOARD_VIEW_OPTIONS, horizontal=True)
	admin_mode = DASHBOARD_VIEW_OPTIONS[0]

	if mode == admin_mode:
		render_admin_view()
	else:
		render_team_view()


def main() -> None:
	render_dashboard()


if __name__ == "__main__":
	main()
