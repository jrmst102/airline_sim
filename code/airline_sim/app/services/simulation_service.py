# filepath: /workspaces/airline_sim/app/services/simulation_service.py

class SimulationService:
    def __init__(self):
        self.simulation_running = False
        self.current_period = 0

    def setup_simulation(self):
        """Prepare the simulation environment."""
        self.current_period = 0
        self.simulation_running = True
        # Additional setup logic can be added here

    def start_simulation(self):
        """Start the simulation process."""
        if not self.simulation_running:
            self.simulation_running = True
            # Logic to start the simulation
            print("Simulation started.")

    def end_simulation(self):
        """End the simulation process."""
        if self.simulation_running:
            self.simulation_running = False
            # Logic to end the simulation
            print("Simulation ended.")

    def undo_last_period(self):
        """Undo the last simulation period."""
        if self.current_period > 0:
            self.current_period -= 1
            # Logic to revert the last period's changes
            print(f"Undid last period. Current period: {self.current_period}")

    def advance_period(self):
        """Advance to the next simulation period."""
        if self.simulation_running:
            self.current_period += 1
            # Logic to advance the simulation
            print(f"Advanced to period: {self.current_period}")

    def get_current_period(self):
        """Return the current simulation period."""
        return self.current_period

    def is_running(self):
        """Check if the simulation is currently running."""
        return self.simulation_running