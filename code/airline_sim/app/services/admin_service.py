# filepath: /workspaces/airline_sim/app/services/admin_service.py

class AdminService:
    def __init__(self, simulation_service, team_data_service):
        self.simulation_service = simulation_service
        self.team_data_service = team_data_service

    def start_simulation(self):
        return self.simulation_service.start()

    def end_simulation(self):
        return self.simulation_service.end()

    def setup_simulation(self, config):
        return self.simulation_service.setup(config)

    def undo_last_period(self):
        return self.simulation_service.undo_last_period()

    def get_team_data(self):
        return self.team_data_service.get_all_team_data()

    def update_team_data(self, team_id, data):
        return self.team_data_service.update_team_data(team_id, data)

    def get_admin_metrics(self):
        # Placeholder for metrics retrieval logic
        return {
            "active_teams": self.team_data_service.get_active_team_count(),
            "simulation_status": self.simulation_service.get_status(),
        }