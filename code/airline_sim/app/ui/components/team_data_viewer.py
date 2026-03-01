from flask import render_template, Blueprint
from app.services.team_data_service import TeamDataService

team_data_viewer = Blueprint('team_data_viewer', __name__)

@team_data_viewer.route('/team-data')
def view_team_data():
    team_data = TeamDataService.get_team_data()
    return render_template('team_data_viewer.html', team_data=team_data)