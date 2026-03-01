from pathlib import Path

from app.modules.display_results import display_results
from app.ui.components import (
	ACTION_DISPLAY_RESULTS,
	build_ui_snapshot,
	card,
	card_end,
	configure_page,
	get_streamlit,
	parse_optional_int,
	render_right_insight_panel,
	render_sidebar_navigation,
	render_standard_header,
	run_action,
)
from app.ui.layout import load_css, shell


def render(sim_id: str, team_id: str = "T1") -> None:
	st = get_streamlit()
	configure_page(st)
	load_css()

	root_dir = Path("simulations")
	snapshot = build_ui_snapshot(simulation_id=sim_id, root_dir=root_dir, team_id=team_id)
	render_standard_header(simulation_id=sim_id, snapshot=snapshot)

	with st.sidebar:
		render_sidebar_navigation(st, active_item="Display Round Results")

	def main_renderer() -> None:
		card("Results", "Market and team reporting")
		section = st.selectbox("Section", options=["team", "market", "both"], index=0)
		round_filter_raw = st.text_input("Round filter (optional)", value="")

		if st.button("Display Results", use_container_width=True):
			def _run_results():
				round_number = parse_optional_int(round_filter_raw, field_name="round")
				return display_results(
					simulation_id=sim_id,
					round_number=round_number,
					team_id=team_id if section in {"team", "both"} else None,
					section=section,
					root_dir=root_dir,
				)

			run_action(st, ACTION_DISPLAY_RESULTS, _run_results)

		card_end()

	def insight_renderer() -> None:
		render_right_insight_panel(st, snapshot=snapshot)

	shell(main_renderer, insight_renderer)


def main() -> None:
	render("sim_001")


if __name__ == "__main__":
	main()
