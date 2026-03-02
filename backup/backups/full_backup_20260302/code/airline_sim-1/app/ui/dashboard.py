# File: /workspaces/airline_sim/app/ui/dashboard.py

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.utils.auth import is_authenticated
from app.services.team_data_service import get_team_data
from app.services.simulation_service import get_simulation_status

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    team_data = get_team_data()
    simulation_status = get_simulation_status()
    
    return render_template('dashboard.html', team_data=team_data, simulation_status=simulation_status)