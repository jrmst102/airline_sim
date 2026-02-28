from __future__ import annotations

from pathlib import Path

from app.ui.components import (
	DASHBOARD_VIEW_CAPTION,
	get_streamlit,
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
		st.header("Quick Checks")
		simulation_id = st.text_input("Simulation ID", value="sim_001")
		root_dir = Path(st.text_input("Simulations Root", value="simulations"))

		if st.button("Check Status", use_container_width=True):
			run_action(
				st,
				"Check Simulation Status",
				lambda: check_simulation_status(simulation_id=simulation_id, root_dir=root_dir),
			)

		if st.button("Quick Market Results", use_container_width=True):
			run_action(
				st,
				"Display Market Results",
				lambda: display_results(
					simulation_id=simulation_id,
					section="market",
					root_dir=root_dir,
				),
			)

	mode = st.radio("View", options=["Admin", "Team"], horizontal=True)

	if mode == "Admin":
		render_admin_view()
	else:
		render_team_view()


def main() -> None:
	render_dashboard()


if __name__ == "__main__":
	main()
