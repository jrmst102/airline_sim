from __future__ import annotations

from pathlib import Path

from app.ui.components import (
	ACTION_CHECK_SIMULATION_STATUS,
	ACTION_DISPLAY_RESULTS,
	ACTION_DISPLAY_TEAM_RESULTS,
	ACTION_ENTER_DECISION,
	ACTION_TEAM_DECISION_HISTORY,
	build_ui_snapshot,
	card,
	card_end,
	configure_page,
	render_card,
	TEAM_BUTTON_CHECK_SIMULATION_STATUS,
	TEAM_BUTTON_DISPLAY_RESULTS,
	TEAM_BUTTON_SHOW_TEAM_DECISION_HISTORY,
	TEAM_BUTTON_SHOW_TEAM_RESULTS,
	TEAM_FORM_SUBMIT_DECISION,
	TEAM_LABEL_BRAND_INVESTMENT,
	TEAM_LABEL_FLIGHTS_PER_DAY,
	TEAM_LABEL_PRICE_ECONOMY,
	TEAM_LABEL_PRICE_PREMIUM,
	TEAM_LABEL_ROUND_FILTER,
	TEAM_LABEL_ROUND_OPTIONAL_OPEN,
	TEAM_LABEL_SECTION,
	TEAM_SECTION_OPTIONS,
	TEAM_SUBHEADER_DECISION_HISTORY,
	TEAM_SUBHEADER_ENTER_DECISION,
	TEAM_SUBHEADER_RESULTS,
	TEAM_TABS,
	TEAM_VIEW_CAPTION,
	get_streamlit,
	parse_optional_int,
	render_basic_context_sidebar,
	render_right_insight_panel,
	render_sidebar_navigation,
	render_standard_header,
	run_action,
)
from app.modules.check_simulation_status import check_simulation_status
from app.modules.display_results import display_results
from app.modules.enter_decisions import enter_decision
from app.modules.historical_decisions_team import get_historical_decisions_team
from app.ui.layout import load_css, shell


def render_team_view() -> None:
	st = get_streamlit()
	configure_page(st)
	load_css()

	context = render_basic_context_sidebar(
		st,
		default_simulation_id="sim_001",
		default_root_dir="simulations",
		key_prefix="team_context",
		include_team_field=True,
	)
	simulation_id = context.simulation_id
	team_id = context.team_id or "T1"
	root_dir = context.root_dir
	snapshot = build_ui_snapshot(simulation_id=simulation_id, root_dir=root_dir, team_id=team_id)
	render_standard_header(simulation_id=simulation_id, snapshot=snapshot)

	with st.sidebar:
		render_sidebar_navigation(st, active_item="Enter Decisions")

	def main_renderer() -> None:
		card("Team Actions", TEAM_VIEW_CAPTION)
		status_col, report_col = st.columns([1, 1])
		with status_col:
			if st.button(TEAM_BUTTON_CHECK_SIMULATION_STATUS, use_container_width=True):
				run_action(
					st,
					ACTION_CHECK_SIMULATION_STATUS,
					lambda: check_simulation_status(simulation_id=simulation_id, root_dir=root_dir),
				)
		with report_col:
			if st.button(TEAM_BUTTON_SHOW_TEAM_RESULTS, use_container_width=True):
				run_action(
					st,
					ACTION_DISPLAY_TEAM_RESULTS,
					lambda: display_results(
						simulation_id=simulation_id,
						team_id=team_id,
						section="team",
						root_dir=root_dir,
					),
				)
		card_end()

		tab_decisions, tab_results, tab_history = st.tabs(TEAM_TABS)

		with tab_decisions:
			with render_card(st, TEAM_SUBHEADER_ENTER_DECISION):
				with st.form("team_decision_form"):
					round_raw = st.text_input(TEAM_LABEL_ROUND_OPTIONAL_OPEN, value="")
					flights_per_day = st.number_input(TEAM_LABEL_FLIGHTS_PER_DAY, min_value=1, value=6, step=1)
					price_premium = st.number_input(TEAM_LABEL_PRICE_PREMIUM, min_value=0.01, value=220.0)
					price_economy = st.number_input(TEAM_LABEL_PRICE_ECONOMY, min_value=0.01, value=160.0)
					brand_investment = st.number_input(TEAM_LABEL_BRAND_INVESTMENT, min_value=0.0, value=1000.0)
					submit_decision = st.form_submit_button(TEAM_FORM_SUBMIT_DECISION)

				if submit_decision:
					def _run_enter_decision():
						round_number = parse_optional_int(round_raw, field_name="round")
						return enter_decision(
							simulation_id=simulation_id,
							team_id=team_id,
							flights_per_day=int(flights_per_day),
							price_premium=float(price_premium),
							price_economy=float(price_economy),
							brand_investment=float(brand_investment),
							round_number=round_number,
							root_dir=root_dir,
						)

					run_action(st, ACTION_ENTER_DECISION, _run_enter_decision)

		with tab_results:
			with render_card(st, TEAM_SUBHEADER_RESULTS):
				results_section = st.selectbox(TEAM_LABEL_SECTION, options=TEAM_SECTION_OPTIONS, index=0)
				round_filter_raw = st.text_input(TEAM_LABEL_ROUND_FILTER, value="")
				if st.button(TEAM_BUTTON_DISPLAY_RESULTS, use_container_width=True):
					def _run_display_results():
						round_number = parse_optional_int(round_filter_raw, field_name="round")
						return display_results(
							simulation_id=simulation_id,
							round_number=round_number,
							team_id=team_id if results_section in {"team", "both"} else None,
							section=results_section,
							root_dir=root_dir,
						)

					run_action(st, ACTION_DISPLAY_RESULTS, _run_display_results)

		with tab_history:
			with render_card(st, TEAM_SUBHEADER_DECISION_HISTORY):
				if st.button(TEAM_BUTTON_SHOW_TEAM_DECISION_HISTORY, use_container_width=True):
					def _run_history():
						summaries = get_historical_decisions_team(simulation_id=simulation_id, root_dir=root_dir)
						for summary in summaries:
							if summary.team_id == team_id:
								return {
									"team_id": summary.team_id,
									"decision_events": summary.decision_events,
									"created_decisions": summary.created_decisions,
									"updated_decisions": summary.updated_decisions,
									"distinct_rounds": summary.distinct_rounds,
									"last_event_at_utc": summary.last_event_at_utc,
								}
						return f"No decision history found for team {team_id}."

					run_action(st, ACTION_TEAM_DECISION_HISTORY, _run_history)

	def insight_renderer() -> None:
		render_right_insight_panel(st, snapshot=snapshot)

	shell(main_renderer, insight_renderer)


def main() -> None:
	render_team_view()


if __name__ == "__main__":
	main()
