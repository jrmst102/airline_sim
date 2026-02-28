from __future__ import annotations

from pathlib import Path

from app.ui.components import (
	ACTION_BACKUP_SIMULATION,
	ACTION_CHANGE_PARAMETERS_LIVE,
	ACTION_CHECK_SIMULATION_STATUS,
	ACTION_CREATE_USER,
	ACTION_DESTROY_SIMULATION,
	ACTION_DISPLAY_LOG,
	ACTION_DISPLAY_RESULTS,
	ACTION_END_SIMULATION,
	ACTION_HISTORICAL_DECISIONS,
	ACTION_LIST_USERS,
	ACTION_LOCK_USER,
	ACTION_MOVE_NEXT_ROUND,
	ACTION_RESTORE_SIMULATION,
	ACTION_SETUP_SIMULATION,
	ACTION_START_SIMULATION,
	ACTION_UNDO_ROUND,
	ACTION_UNLOCK_USER,
	ADMIN_BUTTON_CHECK_STATUS,
	ADMIN_BUTTON_CREATE_BACKUP,
	ADMIN_BUTTON_DESTROY_SIMULATION,
	ADMIN_BUTTON_DISPLAY_LOG,
	ADMIN_BUTTON_DISPLAY_RESULTS,
	ADMIN_BUTTON_END,
	ADMIN_BUTTON_HISTORICAL_DECISIONS,
	ADMIN_BUTTON_LIST_USERS,
	ADMIN_BUTTON_LOCK,
	ADMIN_BUTTON_MOVE_NEXT,
	ADMIN_BUTTON_REFRESH_STATUS,
	ADMIN_BUTTON_RESTORE_BACKUP,
	ADMIN_BUTTON_START,
	ADMIN_BUTTON_UNDO,
	ADMIN_BUTTON_UNLOCK,
	ADMIN_DESTROY_MODE_OPTIONS,
	ADMIN_FORM_SUBMIT_CREATE_USER,
	ADMIN_FORM_SUBMIT_PARAMETERS,
	ADMIN_FORM_SUBMIT_SETUP,
	ADMIN_LABEL_BACKUP_ZIP_PATH,
	ADMIN_LABEL_BASE_DEMAND_BUSINESS,
	ADMIN_LABEL_BASE_DEMAND_LEISURE,
	ADMIN_LABEL_BASE_FIXED_COST_PER_ROUND,
	ADMIN_LABEL_BASE_FUEL_COST_PER_FLIGHT,
	ADMIN_LABEL_BASE_VARIABLE_COST_PER_PAX,
	ADMIN_LABEL_BRAND_EFFECTIVENESS,
	ADMIN_LABEL_DAYS_PER_ROUND,
	ADMIN_LABEL_DESTROY_MODE,
	ADMIN_LABEL_OVERWRITE_SIMULATION,
	ADMIN_LABEL_OVERWRITE_TARGET,
	ADMIN_LABEL_PASSWORD,
	ADMIN_LABEL_RESTORE_AS_SIMULATION_ID,
	ADMIN_LABEL_RESULTS_SECTION,
	ADMIN_LABEL_ROLE,
	ADMIN_LABEL_ROUND_FILTER,
	ADMIN_LABEL_SIMULATION_NAME,
	ADMIN_LABEL_TARGET_USERNAME,
	ADMIN_LABEL_TEAM_FILTER,
	ADMIN_LABEL_TEAM_ID_FOR_ROLE,
	ADMIN_LABEL_TEAM_NAMES,
	ADMIN_LABEL_TOTAL_ROUNDS,
	ADMIN_LABEL_USERNAME,
	ADMIN_RESULTS_SECTION_OPTIONS,
	ADMIN_ROLE_OPTIONS,
	ADMIN_QUICK_LIFECYCLE_ACTIONS_LABEL,
	ADMIN_SECTION_BACKUP,
	ADMIN_SECTION_CREATE_USER,
	ADMIN_SECTION_DESTROY,
	ADMIN_SECTION_LOCK_UNLOCK_USER,
	ADMIN_SECTION_RESTORE,
	ADMIN_SUBHEADER_BACKUP,
	ADMIN_SUBHEADER_PARAMETERS,
	ADMIN_SUBHEADER_REPORTS,
	ADMIN_SUBHEADER_SETUP,
	ADMIN_SUBHEADER_USERS,
	ADMIN_TABS,
	ADMIN_VIEW_CAPTION,
	apply_streamlit_theme,
	build_ui_snapshot,
	get_streamlit,
	parse_csv_list,
	parse_optional_int,
	render_card,
	render_basic_context_sidebar,
	render_right_insight_panel,
	render_sidebar_navigation,
	render_top_header_bar,
	run_action,
)
from app.modules.backup_simulation import backup_simulation
from app.modules.change_parameters_live import change_parameters_live
from app.modules.check_simulation_status import check_simulation_status
from app.modules.destroy_simulation import destroy_simulation
from app.modules.display_log import display_log
from app.modules.display_results import display_results
from app.modules.end_simulation import end_simulation
from app.modules.historical_decisions_team import display_historical_decisions_team
from app.modules.move_next_round import move_next_round
from app.modules.restore_simulation import restore_simulation
from app.modules.setup_simulation import setup_simulation
from app.modules.start_simulation import start_simulation
from app.modules.undo_round import undo_round
from app.modules.user_management import create_user, list_users, set_user_lock


def render_admin_view() -> None:
	st = get_streamlit()
	apply_streamlit_theme(st)

	context = render_basic_context_sidebar(
		st,
		default_simulation_id="sim_001",
		default_root_dir="simulations",
		key_prefix="admin_context",
		include_admin_fields=True,
		include_storage_fields=True,
	)
	simulation_id = context.simulation_id
	admin_user_id = context.admin_user_id or "U_ADMIN"
	root_dir = context.root_dir
	backups_dir = context.backups_dir or Path("backups")
	archive_dir = context.archive_dir or Path("archive")
	snapshot = build_ui_snapshot(simulation_id=simulation_id, root_dir=root_dir)
	render_top_header_bar(st, simulation_id=simulation_id, snapshot=snapshot)
	st.caption(ADMIN_VIEW_CAPTION)

	with st.sidebar:
		render_sidebar_navigation(st, active_item="Change Parameters (Live)")

	main_col, insight_col = st.columns([5, 1], vertical_alignment="top")
	with main_col:
		with render_card(st, "Lifecycle Controls"):
			status_col, quick_col = st.columns([1, 3])
			with status_col:
				if st.button(ADMIN_BUTTON_REFRESH_STATUS, use_container_width=True):
					run_action(
						st,
						ACTION_CHECK_SIMULATION_STATUS,
						lambda: check_simulation_status(
							simulation_id=simulation_id,
							root_dir=root_dir,
						),
					)

			with quick_col:
				st.write(ADMIN_QUICK_LIFECYCLE_ACTIONS_LABEL)
				c1, c2, c3, c4 = st.columns(4)
				with c1:
					if st.button(ADMIN_BUTTON_START, use_container_width=True):
						run_action(
							st,
							ACTION_START_SIMULATION,
							lambda: start_simulation(
								simulation_id=simulation_id,
								admin_user_id=admin_user_id,
								root_dir=root_dir,
							),
						)
				with c2:
					if st.button(ADMIN_BUTTON_MOVE_NEXT, use_container_width=True):
						run_action(
							st,
							ACTION_MOVE_NEXT_ROUND,
							lambda: move_next_round(
								simulation_id=simulation_id,
								admin_user_id=admin_user_id,
								root_dir=root_dir,
							),
						)
				with c3:
					if st.button(ADMIN_BUTTON_UNDO, use_container_width=True):
						run_action(
							st,
							ACTION_UNDO_ROUND,
							lambda: undo_round(
								simulation_id=simulation_id,
								admin_user_id=admin_user_id,
								root_dir=root_dir,
							),
						)
				with c4:
					if st.button(ADMIN_BUTTON_END, use_container_width=True):
						run_action(
							st,
							ACTION_END_SIMULATION,
							lambda: end_simulation(
								simulation_id=simulation_id,
								admin_user_id=admin_user_id,
								root_dir=root_dir,
							),
						)

	with insight_col:
		render_right_insight_panel(st, snapshot=snapshot)

	tab_setup, tab_params, tab_backup, tab_reporting, tab_users = st.tabs(ADMIN_TABS)

	with tab_setup:
		st.subheader(ADMIN_SUBHEADER_SETUP)
		with st.form("setup_form"):
			simulation_name = st.text_input(ADMIN_LABEL_SIMULATION_NAME, value="Airline Simulation")
			total_rounds = st.number_input(ADMIN_LABEL_TOTAL_ROUNDS, min_value=1, value=8, step=1)
			raw_team_names = st.text_input(ADMIN_LABEL_TEAM_NAMES, value="Team Alpha, Team Bravo")
			overwrite = st.checkbox(ADMIN_LABEL_OVERWRITE_SIMULATION, value=False)
			submitted = st.form_submit_button(ADMIN_FORM_SUBMIT_SETUP)
			if submitted:
				team_names = parse_csv_list(raw_team_names)
				run_action(
					st,
					ACTION_SETUP_SIMULATION,
					lambda: setup_simulation(
						simulation_id=simulation_id,
						simulation_name=simulation_name,
						total_rounds=int(total_rounds),
						team_names=team_names,
						root_dir=root_dir,
						overwrite=overwrite,
					),
				)

	with tab_params:
		st.subheader(ADMIN_SUBHEADER_PARAMETERS)
		with st.form("params_form"):
			days_per_round = st.number_input(ADMIN_LABEL_DAYS_PER_ROUND, min_value=1, value=30, step=1)
			base_demand_business = st.number_input(ADMIN_LABEL_BASE_DEMAND_BUSINESS, min_value=0.0, value=1200.0)
			base_demand_leisure = st.number_input(ADMIN_LABEL_BASE_DEMAND_LEISURE, min_value=0.0, value=3600.0)
			base_fuel_cost_per_flight = st.number_input(ADMIN_LABEL_BASE_FUEL_COST_PER_FLIGHT, min_value=0.0, value=2500.0)
			base_fixed_cost_per_round = st.number_input(ADMIN_LABEL_BASE_FIXED_COST_PER_ROUND, min_value=0.0, value=50000.0)
			base_variable_cost_per_pax = st.number_input(ADMIN_LABEL_BASE_VARIABLE_COST_PER_PAX, min_value=0.0, value=40.0)
			brand_effectiveness = st.number_input(ADMIN_LABEL_BRAND_EFFECTIVENESS, min_value=0.0, value=0.02)
			submit_params = st.form_submit_button(ADMIN_FORM_SUBMIT_PARAMETERS)
			if submit_params:
				run_action(
					st,
					ACTION_CHANGE_PARAMETERS_LIVE,
					lambda: change_parameters_live(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
						days_per_round=int(days_per_round),
						base_demand_business=float(base_demand_business),
						base_demand_leisure=float(base_demand_leisure),
						base_fuel_cost_per_flight=float(base_fuel_cost_per_flight),
						base_fixed_cost_per_round=float(base_fixed_cost_per_round),
						base_variable_cost_per_pax=float(base_variable_cost_per_pax),
						brand_effectiveness=float(brand_effectiveness),
					),
				)

	with tab_backup:
		st.subheader(ADMIN_SUBHEADER_BACKUP)
		c_backup, c_restore, c_destroy = st.columns(3)

		with c_backup:
			st.write(ADMIN_SECTION_BACKUP)
			if st.button(ADMIN_BUTTON_CREATE_BACKUP, use_container_width=True):
				run_action(
					st,
					ACTION_BACKUP_SIMULATION,
					lambda: backup_simulation(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
						backups_dir=backups_dir,
					),
				)

		with c_restore:
			st.write(ADMIN_SECTION_RESTORE)
			restore_backup_path = st.text_input(ADMIN_LABEL_BACKUP_ZIP_PATH, value="")
			restore_as_sim_id = st.text_input(ADMIN_LABEL_RESTORE_AS_SIMULATION_ID, value="")
			restore_overwrite = st.checkbox(ADMIN_LABEL_OVERWRITE_TARGET, value=False)
			if st.button(ADMIN_BUTTON_RESTORE_BACKUP, use_container_width=True):
				run_action(
					st,
					ACTION_RESTORE_SIMULATION,
					lambda: restore_simulation(
						backup_zip_path=Path(restore_backup_path),
						restore_as_simulation_id=restore_as_sim_id or None,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
						overwrite=restore_overwrite,
					),
				)

		with c_destroy:
			st.write(ADMIN_SECTION_DESTROY)
			destroy_mode = st.selectbox(ADMIN_LABEL_DESTROY_MODE, options=ADMIN_DESTROY_MODE_OPTIONS, index=0)
			if st.button(ADMIN_BUTTON_DESTROY_SIMULATION, use_container_width=True):
				run_action(
					st,
					ACTION_DESTROY_SIMULATION,
					lambda: destroy_simulation(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						mode=destroy_mode,
						root_dir=root_dir,
						backups_dir=backups_dir,
						archive_dir=archive_dir,
					),
				)

	with tab_reporting:
		st.subheader(ADMIN_SUBHEADER_REPORTS)
		section = st.selectbox(ADMIN_LABEL_RESULTS_SECTION, options=ADMIN_RESULTS_SECTION_OPTIONS, index=0)
		round_filter_raw = st.text_input(ADMIN_LABEL_ROUND_FILTER, value="")
		team_filter = st.text_input(ADMIN_LABEL_TEAM_FILTER, value="")

		r1, r2, r3, r4 = st.columns(4)
		with r1:
			if st.button(ADMIN_BUTTON_DISPLAY_RESULTS, use_container_width=True):
				run_action(
					st,
					ACTION_DISPLAY_RESULTS,
					lambda: display_results(
						simulation_id=simulation_id,
						round_number=parse_optional_int(round_filter_raw, field_name="round"),
						team_id=team_filter or None,
						section=section,
						root_dir=root_dir,
					),
				)
		with r2:
			if st.button(ADMIN_BUTTON_DISPLAY_LOG, use_container_width=True):
				run_action(
					st,
					ACTION_DISPLAY_LOG,
					lambda: display_log(
						simulation_id=simulation_id,
						root_dir=root_dir,
					),
				)
		with r3:
			if st.button(ADMIN_BUTTON_HISTORICAL_DECISIONS, use_container_width=True):
				run_action(
					st,
					ACTION_HISTORICAL_DECISIONS,
					lambda: display_historical_decisions_team(
						simulation_id=simulation_id,
						root_dir=root_dir,
					),
				)
		with r4:
			if st.button(ADMIN_BUTTON_CHECK_STATUS, use_container_width=True):
				run_action(
					st,
					ACTION_CHECK_SIMULATION_STATUS,
					lambda: check_simulation_status(
						simulation_id=simulation_id,
						root_dir=root_dir,
					),
				)

	with tab_users:
		st.subheader(ADMIN_SUBHEADER_USERS)
		left, right = st.columns(2)

		with left:
			with st.form("create_user_form"):
				st.write(ADMIN_SECTION_CREATE_USER)
				username = st.text_input(ADMIN_LABEL_USERNAME)
				password = st.text_input(ADMIN_LABEL_PASSWORD, type="password")
				role = st.selectbox(ADMIN_LABEL_ROLE, options=ADMIN_ROLE_OPTIONS, index=1)
				team_id = st.text_input(ADMIN_LABEL_TEAM_ID_FOR_ROLE, value="")
				submit_user = st.form_submit_button(ADMIN_FORM_SUBMIT_CREATE_USER)
				if submit_user:
					run_action(
						st,
						ACTION_CREATE_USER,
						lambda: create_user(
							simulation_id=simulation_id,
							username=username,
							password=password,
							role=role,
							team_id=team_id,
							root_dir=root_dir,
							admin_user_id=admin_user_id,
						),
					)

		with right:
			st.write(ADMIN_SECTION_LOCK_UNLOCK_USER)
			target_username = st.text_input(ADMIN_LABEL_TARGET_USERNAME)
			c_lock, c_unlock = st.columns(2)
			with c_lock:
				if st.button(ADMIN_BUTTON_LOCK, use_container_width=True):
					run_action(
						st,
						ACTION_LOCK_USER,
						lambda: set_user_lock(
							simulation_id=simulation_id,
							username=target_username,
							is_locked=True,
							root_dir=root_dir,
							admin_user_id=admin_user_id,
						),
					)
			with c_unlock:
				if st.button(ADMIN_BUTTON_UNLOCK, use_container_width=True):
					run_action(
						st,
						ACTION_UNLOCK_USER,
						lambda: set_user_lock(
							simulation_id=simulation_id,
							username=target_username,
							is_locked=False,
							root_dir=root_dir,
							admin_user_id=admin_user_id,
						),
					)

		if st.button(ADMIN_BUTTON_LIST_USERS):
			run_action(
				st,
				ACTION_LIST_USERS,
				lambda: [
					{
						"user_id": user.user_id,
						"username": user.username,
						"role": user.role,
						"team_id": user.team_id,
						"locked": user.locked,
					}
					for user in list_users(simulation_id=simulation_id, root_dir=root_dir)
				],
			)


def main() -> None:
	render_admin_view()


if __name__ == "__main__":
	main()
