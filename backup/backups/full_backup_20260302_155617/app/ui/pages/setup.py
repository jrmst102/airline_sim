from pathlib import Path

from app.modules.setup_simulation import setup_simulation
from app.ui.components import (
	ACTION_SETUP_SIMULATION,
	build_ui_snapshot,
	card,
	card_end,
	configure_page,
	get_streamlit,
	parse_csv_list,
	render_right_insight_panel,
	render_sidebar_navigation,
	render_standard_header,
	run_action,
)
from app.ui.layout import load_css, shell


def render(sim_id: str) -> None:
	st = get_streamlit()
	configure_page(st)
	load_css()

	root_dir = Path("simulation/simulations")
	snapshot = build_ui_snapshot(simulation_id=sim_id, root_dir=root_dir)
	render_standard_header(simulation_id=sim_id, snapshot=snapshot)
	render_sidebar_navigation(st, active_item="Home")

	def main_renderer() -> None:
		card("Setup Simulation", "Create or overwrite a simulation workspace")
		with st.form("page_setup_form"):
			simulation_name = st.text_input("Simulation Name", value="Airline Simulation")
			total_rounds = st.number_input("Total Rounds", min_value=1, value=8, step=1)
			raw_team_names = st.text_input("Team Names (comma-separated)", value="Team Alpha, Team Bravo")
			overwrite = st.checkbox("Overwrite if simulation folder exists", value=False)
			submitted = st.form_submit_button("Run Setup")

		if submitted:
			team_names = parse_csv_list(raw_team_names)
			run_action(
				st,
				ACTION_SETUP_SIMULATION,
				lambda: setup_simulation(
					simulation_id=sim_id,
					simulation_name=simulation_name,
					total_rounds=int(total_rounds),
					team_names=team_names,
					root_dir=root_dir,
					overwrite=overwrite,
				),
			)

		card_end()

	def insight_renderer() -> None:
		render_right_insight_panel(st, snapshot=snapshot)

	shell(main_renderer, insight_renderer)


def main() -> None:
	render("sim_001")


if __name__ == "__main__":
	main()
