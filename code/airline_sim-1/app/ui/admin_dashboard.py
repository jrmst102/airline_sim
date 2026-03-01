from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.utils.auth import is_authenticated
from app.services.admin_service import AdminService
from app.ui.components.admin_controls import AdminControls
from app.ui.components.team_data_viewer import TeamDataViewer
from app.ui.components.simulation_controls import SimulationControls
from app.ui.components.admin_metrics import AdminMetrics

admin_dashboard = Blueprint('admin_dashboard', __name__)

@admin_dashboard.route('/admin')
@is_authenticated
def dashboard():
    admin_service = AdminService()
    team_data = admin_service.get_team_data()
    metrics = admin_service.get_admin_metrics()
    
    return render_template('admin_dashboard.html', team_data=team_data, metrics=metrics)

@admin_dashboard.route('/admin/start_simulation', methods=['POST'])
@is_authenticated
def start_simulation():
    admin_service = AdminService()
    admin_service.start_simulation()
    flash('Simulation started successfully!', 'success')
    return redirect(url_for('admin_dashboard.dashboard'))

@admin_dashboard.route('/admin/end_simulation', methods=['POST'])
@is_authenticated
def end_simulation():
    admin_service = AdminService()
    admin_service.end_simulation()
    flash('Simulation ended successfully!', 'success')
    return redirect(url_for('admin_dashboard.dashboard'))

@admin_dashboard.route('/admin/setup_simulation', methods=['POST'])
@is_authenticated
def setup_simulation():
    admin_service = AdminService()
    admin_service.setup_simulation()
    flash('Simulation setup successfully!', 'success')
    return redirect(url_for('admin_dashboard.dashboard'))

@admin_dashboard.route('/admin/undo_last_period', methods=['POST'])
@is_authenticated
def undo_last_period():
    admin_service = AdminService()
    admin_service.undo_last_period()
    flash('Last period undone successfully!', 'success')
    return redirect(url_for('admin_dashboard.dashboard'))