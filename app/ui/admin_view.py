from __future__ import annotations

import importlib
from pathlib import Path

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


def _get_streamlit():
	try:
		return importlib.import_module("streamlit")
	except ModuleNotFoundError as exc:  # pragma: no cover
		raise ModuleNotFoundError(
			"streamlit is required for admin_view.py. Install it with: pip install streamlit"
		) from exc


def _handle_action(st, action_name: str, callback) -> None:
	try:
		result = callback()
		st.success(f"{action_name} completed")
		st.write(result)
	except Exception as error:
		st.error(f"{action_name} failed: {error}")


def _parse_team_names(raw_team_names: str) -> list[str]:
	teams = [name.strip() for name in raw_team_names.split(",") if name.strip()]
	return teams


def render_admin_view() -> None:
	st = _get_streamlit()
	st.title("Airline Simulation Admin")
	st.caption("Admin operations for setup, lifecycle, backups, restore, results, logs, and users")

	with st.sidebar:
		st.header("Context")
		simulation_id = st.text_input("Simulation ID", value="sim_001")
		admin_user_id = st.text_input("Admin User ID", value="U_ADMIN")
		root_dir = Path(st.text_input("Simulations Root", value="simulations"))
		backups_dir = Path(st.text_input("Backups Root", value="backups"))
		archive_dir = Path(st.text_input("Archive Root", value="archive"))

	status_col, quick_col = st.columns([1, 2])
	with status_col:
		if st.button("Refresh Status", use_container_width=True):
			_handle_action(
				st,
				"Check Status",
				lambda: check_simulation_status(
					simulation_id=simulation_id,
					root_dir=root_dir,
				),
			)

	with quick_col:
		st.write("Quick lifecycle actions")
		c1, c2, c3, c4 = st.columns(4)
		with c1:
			if st.button("Start", use_container_width=True):
				_handle_action(
					st,
					"Start Simulation",
					lambda: start_simulation(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
					),
				)
		with c2:
			if st.button("Move Next", use_container_width=True):
				_handle_action(
					st,
					"Move Next Round",
					lambda: move_next_round(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
					),
				)
		with c3:
			if st.button("Undo", use_container_width=True):
				_handle_action(
					st,
					"Undo Round",
					lambda: undo_round(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
					),
				)
		with c4:
			if st.button("End", use_container_width=True):
				_handle_action(
					st,
					"End Simulation",
					lambda: end_simulation(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
					),
				)

	tab_setup, tab_params, tab_backup, tab_reporting, tab_users = st.tabs(
		["Setup", "Parameters", "Backup / Restore / Destroy", "Reporting", "Users"]
	)

	with tab_setup:
		st.subheader("Setup Simulation")
		with st.form("setup_form"):
			simulation_name = st.text_input("Simulation Name", value="Airline Simulation")
			total_rounds = st.number_input("Total Rounds", min_value=1, value=8, step=1)
			raw_team_names = st.text_input("Team Names (comma-separated)", value="Team Alpha, Team Bravo")
			overwrite = st.checkbox("Overwrite if simulation folder exists", value=False)
			submitted = st.form_submit_button("Run Setup")
			if submitted:
				team_names = _parse_team_names(raw_team_names)
				_handle_action(
					st,
					"Setup Simulation",
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
		st.subheader("Change Parameters (New Version)")
		with st.form("params_form"):
			days_per_round = st.number_input("days_per_round", min_value=1, value=30, step=1)
			base_demand_business = st.number_input("base_demand_business", min_value=0.0, value=1200.0)
			base_demand_leisure = st.number_input("base_demand_leisure", min_value=0.0, value=3600.0)
			base_fuel_cost_per_flight = st.number_input("base_fuel_cost_per_flight", min_value=0.0, value=2500.0)
			base_fixed_cost_per_round = st.number_input("base_fixed_cost_per_round", min_value=0.0, value=50000.0)
			base_variable_cost_per_pax = st.number_input("base_variable_cost_per_pax", min_value=0.0, value=40.0)
			brand_effectiveness = st.number_input("brand_effectiveness", min_value=0.0, value=0.02)
			submit_params = st.form_submit_button("Apply Parameter Version")
			if submit_params:
				_handle_action(
					st,
					"Change Parameters Live",
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
		st.subheader("Backup / Restore / Destroy")
		c_backup, c_restore, c_destroy = st.columns(3)

		with c_backup:
			st.write("Backup")
			if st.button("Create Backup", use_container_width=True):
				_handle_action(
					st,
					"Backup Simulation",
					lambda: backup_simulation(
						simulation_id=simulation_id,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
						backups_dir=backups_dir,
					),
				)

		with c_restore:
			st.write("Restore")
			restore_backup_path = st.text_input("Backup zip path", value="")
			restore_as_sim_id = st.text_input("Restore as simulation_id (optional)", value="")
			restore_overwrite = st.checkbox("Overwrite target if exists", value=False)
			if st.button("Restore Backup", use_container_width=True):
				_handle_action(
					st,
					"Restore Simulation",
					lambda: restore_simulation(
						backup_zip_path=Path(restore_backup_path),
						restore_as_simulation_id=restore_as_sim_id or None,
						admin_user_id=admin_user_id,
						root_dir=root_dir,
						overwrite=restore_overwrite,
					),
				)

		with c_destroy:
			st.write("Destroy")
			destroy_mode = st.selectbox("Destroy mode", options=["archive", "delete"], index=0)
			if st.button("Destroy Simulation", use_container_width=True):
				_handle_action(
					st,
					"Destroy Simulation",
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
		st.subheader("Reports")
		section = st.selectbox("Results Section", options=["both", "market", "team"], index=0)
		round_filter_raw = st.text_input("Round filter (optional)", value="")
		team_filter = st.text_input("Team filter (optional)", value="")

		round_filter = int(round_filter_raw) if round_filter_raw.strip().isdigit() else None

		r1, r2, r3, r4 = st.columns(4)
		with r1:
			if st.button("Display Results", use_container_width=True):
				_handle_action(
					st,
					"Display Results",
					lambda: display_results(
						simulation_id=simulation_id,
						round_number=round_filter,
						team_id=team_filter or None,
						section=section,
						root_dir=root_dir,
					),
				)
		with r2:
			if st.button("Display Log", use_container_width=True):
				_handle_action(
					st,
					"Display Log",
					lambda: display_log(
						simulation_id=simulation_id,
						root_dir=root_dir,
					),
				)
		with r3:
			if st.button("Historical Decisions", use_container_width=True):
				_handle_action(
					st,
					"Historical Decisions",
					lambda: display_historical_decisions_team(
						simulation_id=simulation_id,
						root_dir=root_dir,
					),
				)
		with r4:
			if st.button("Check Status", use_container_width=True):
				_handle_action(
					st,
					"Check Simulation Status",
					lambda: check_simulation_status(
						simulation_id=simulation_id,
						root_dir=root_dir,
					),
				)

	with tab_users:
		st.subheader("User Management")
		left, right = st.columns(2)

		with left:
			with st.form("create_user_form"):
				st.write("Create User")
				username = st.text_input("Username")
				password = st.text_input("Password", type="password")
				role = st.selectbox("Role", options=["ADMIN", "TEAM_LEAD", "TEAM_MEMBER"], index=1)
				team_id = st.text_input("Team ID (for TEAM_* roles)", value="")
				submit_user = st.form_submit_button("Create User")
				if submit_user:
					_handle_action(
						st,
						"Create User",
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
			st.write("Lock / Unlock User")
			target_username = st.text_input("Target username")
			c_lock, c_unlock = st.columns(2)
			with c_lock:
				if st.button("Lock", use_container_width=True):
					_handle_action(
						st,
						"Lock User",
						lambda: set_user_lock(
							simulation_id=simulation_id,
							username=target_username,
							is_locked=True,
							root_dir=root_dir,
							admin_user_id=admin_user_id,
						),
					)
			with c_unlock:
				if st.button("Unlock", use_container_width=True):
					_handle_action(
						st,
						"Unlock User",
						lambda: set_user_lock(
							simulation_id=simulation_id,
							username=target_username,
							is_locked=False,
							root_dir=root_dir,
							admin_user_id=admin_user_id,
						),
					)

		if st.button("List Users"):
			_handle_action(
				st,
				"List Users",
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
