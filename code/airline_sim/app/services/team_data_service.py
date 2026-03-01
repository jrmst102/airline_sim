from typing import List, Dict
import json
import os

class TeamDataService:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path

    def read_team_data(self) -> List[Dict]:
        """Read team data from the storage."""
        if not os.path.exists(self.storage_path):
            return []
        with open(self.storage_path, 'r') as file:
            return json.load(file)

    def write_team_data(self, team_data: List[Dict]) -> None:
        """Write team data to the storage."""
        with open(self.storage_path, 'w') as file:
            json.dump(team_data, file)

    def update_team_data(self, team_id: str, new_data: Dict) -> None:
        """Update specific team data."""
        team_data = self.read_team_data()
        for team in team_data:
            if team['id'] == team_id:
                team.update(new_data)
                break
        self.write_team_data(team_data)

    def get_team_by_id(self, team_id: str) -> Dict:
        """Get team data by team ID."""
        team_data = self.read_team_data()
        for team in team_data:
            if team['id'] == team_id:
                return team
        return {}

    def add_team(self, team: Dict) -> None:
        """Add a new team to the data."""
        team_data = self.read_team_data()
        team_data.append(team)
        self.write_team_data(team_data)

    def delete_team(self, team_id: str) -> None:
        """Delete a team from the data."""
        team_data = self.read_team_data()
        team_data = [team for team in team_data if team['id'] != team_id]
        self.write_team_data(team_data)