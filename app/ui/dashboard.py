from __future__ import annotations

import importlib
from pathlib import Path

from app.modules.check_simulation_status import check_simulation_status
from app.modules.display_results import display_results
from app.ui.admin_view import render_admin_view
from app.ui.team_view import render_team_view


def _get_streamlit():
	try:
		return importlib.import_module("streamlit")
	except ModuleNotFoundError as exc:  # pragma: no cover
		raise ModuleNotFoundError(
			"streamlit is required for dashboard.py. Install it with: pip install streamlit"
		) from exc


def _handle_action(st, action_name: str, callback) -> None:
	try:
		result = callback()
		st.success(f"{action_name} completed")
		st.write(result)
	except Exception as error:
		st.error(f"{action_name} failed: {error}")


def render_dashboard() -> None:
	st = _get_streamlit()
	st.set_page_config(page_title="Airline Simulation Dashboard", layout="wide")
	st.title("Airline Simulation Dashboard")
	st.caption("Unified entry point for Admin and Team operations")

	with st.sidebar:
		st.header("Quick Checks")
		simulation_id = st.text_input("Simulation ID", value="sim_001")
		root_dir = Path(st.text_input("Simulations Root", value="simulations"))

		if st.button("Check Status", use_container_width=True):
			_handle_action(
				st,
				"Check Simulation Status",
				lambda: check_simulation_status(simulation_id=simulation_id, root_dir=root_dir),
			)

		if st.button("Quick Market Results", use_container_width=True):
			_handle_action(
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
