# filepath: /workspaces/airline_sim/app/ui/admin_view.py

from flask import Blueprint, render_template
from .components.admin_controls import AdminControls
from .components.team_data_viewer import TeamDataViewer
from .components.simulation_controls import SimulationControls
from .components.admin_metrics import AdminMetrics

admin_view = Blueprint('admin_view', __name__)

@admin_view.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html', 
                           admin_controls=AdminControls(),
                           team_data_viewer=TeamDataViewer(),
                           simulation_controls=SimulationControls(),
                           admin_metrics=AdminMetrics())