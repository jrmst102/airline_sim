from __future__ import annotations

import importlib
from pathlib import Path

from app.modules.check_simulation_status import check_simulation_status
from app.modules.display_results import display_results
from app.modules.enter_decisions import enter_decision
from app.modules.historical_decisions_team import get_historical_decisions_team


def _get_streamlit():
	try:
		return importlib.import_module("streamlit")
	except ModuleNotFoundError as exc:  # pragma: no cover
		raise ModuleNotFoundError(
			"streamlit is required for team_view.py. Install it with: pip install streamlit"
		) from exc


def _handle_action(st, action_name: str, callback) -> None:
	try:
		result = callback()
		st.success(f"{action_name} completed")
		st.write(result)
	except Exception as error:
		st.error(f"{action_name} failed: {error}")


def _to_optional_int(raw_value: str) -> int | None:
	raw = raw_value.strip()
	if not raw:
		return None
	if raw.isdigit():
		return int(raw)
	raise ValueError("Round must be a positive integer when provided")


def render_team_view() -> None:
	st = _get_streamlit()
	st.title("Airline Simulation Team View")
	st.caption("Team decision entry and results tracking")

	with st.sidebar:
		st.header("Context")
		simulation_id = st.text_input("Simulation ID", value="sim_001")
		team_id = st.text_input("Team ID", value="T1")
		root_dir = Path(st.text_input("Simulations Root", value="simulations"))

	status_col, report_col = st.columns([1, 1])
	with status_col:
		if st.button("Check Simulation Status", use_container_width=True):
			_handle_action(
				st,
				"Check Simulation Status",
				lambda: check_simulation_status(simulation_id=simulation_id, root_dir=root_dir),
			)
	with report_col:
		if st.button("Show Team Results", use_container_width=True):
			_handle_action(
				st,
				"Display Team Results",
				lambda: display_results(
					simulation_id=simulation_id,
					team_id=team_id,
					section="team",
					root_dir=root_dir,
				),
			)

	tab_decisions, tab_results, tab_history = st.tabs(["Enter Decision", "Results", "History"])

	with tab_decisions:
		st.subheader("Enter / Update Decision")
		with st.form("team_decision_form"):
			round_raw = st.text_input("Round (optional, must be OPEN)", value="")
			flights_per_day = st.number_input("flights_per_day", min_value=1, value=6, step=1)
			price_premium = st.number_input("price_premium", min_value=0.01, value=220.0)
			price_economy = st.number_input("price_economy", min_value=0.01, value=160.0)
			brand_investment = st.number_input("brand_investment", min_value=0.0, value=1000.0)
			submit_decision = st.form_submit_button("Submit Decision")

			if submit_decision:
				def _run_enter_decision():
					round_number = _to_optional_int(round_raw)
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

				_handle_action(st, "Enter Decision", _run_enter_decision)

	with tab_results:
		st.subheader("Results")
		results_section = st.selectbox("Section", options=["team", "market", "both"], index=0)
		round_filter_raw = st.text_input("Round filter (optional)", value="")
		if st.button("Display Results", use_container_width=True):
			def _run_display_results():
				round_number = _to_optional_int(round_filter_raw)
				return display_results(
					simulation_id=simulation_id,
					round_number=round_number,
					team_id=team_id if results_section in {"team", "both"} else None,
					section=results_section,
					root_dir=root_dir,
				)

			_handle_action(st, "Display Results", _run_display_results)

	with tab_history:
		st.subheader("Decision History")
		if st.button("Show Team Decision History", use_container_width=True):
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

			_handle_action(st, "Team Decision History", _run_history)


def main() -> None:
	render_team_view()


if __name__ == "__main__":
	main()
