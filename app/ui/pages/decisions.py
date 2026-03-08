from pathlib import Path

from app.modules.enter_decisions import enter_decision
from app.ui.components import (
	ACTION_ENTER_DECISION,
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

	root_dir = Path("simulation/simulations")
	snapshot = build_ui_snapshot(simulation_id=sim_id, root_dir=root_dir, team_id=team_id)
	render_standard_header(simulation_id=sim_id, snapshot=snapshot)
	render_sidebar_navigation(st, active_item="Enter Decisions")

	def main_renderer() -> None:
		card("Decision Entry", f"Team {team_id} decision input")
		with st.form("page_decision_form"):
			round_raw = st.text_input("Round (optional, must be OPEN)", value="")
			flights_per_day = st.number_input("Flights per Day", min_value=0, max_value=5, value=3, step=1)
			price_business = st.number_input(
				"Business Seat Price ($)", min_value=100.0, max_value=5000.0,
				value=360.0, step=10.0, format="%.0f",
				help="Reference: Premium $450 · Match $360 · Discount $290",
			)
			price_leisure = st.number_input(
				"Leisure Seat Price ($)", min_value=100.0, max_value=5000.0,
				value=180.0, step=10.0, format="%.0f",
				help="Reference: Premium $220 · Match $180 · Discount $140",
			)
			branding_level = st.selectbox("Branding Level", options=["Low", "Medium", "High"], index=1)
			product_strategy = st.selectbox("Product Strategy", options=["High", "Medium", "Low"], index=2)
			submit = st.form_submit_button("Submit Decision")

		if submit:
			def _run_enter_decision():
				round_number = parse_optional_int(round_raw, field_name="round")
				return enter_decision(
					simulation_id=sim_id,
					team_id=team_id,
					flights_per_day=int(flights_per_day),
					price_business=float(price_business),
					price_leisure=float(price_leisure),
					branding_level=branding_level,
					product_strategy=product_strategy,
					round_number=round_number,
					root_dir=root_dir,
				)

			run_action(st, ACTION_ENTER_DECISION, _run_enter_decision)

		card_end()

	def insight_renderer() -> None:
		render_right_insight_panel(st, snapshot=snapshot)

	shell(main_renderer, insight_renderer)


def main() -> None:
	render("sim_001")


if __name__ == "__main__":
	main()
