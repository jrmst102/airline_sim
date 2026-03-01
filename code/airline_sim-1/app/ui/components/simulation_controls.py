# filepath: /workspaces/airline_sim/app/ui/components/simulation_controls.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.simulation_service import SimulationService

simulation_controls_bp = Blueprint('simulation_controls', __name__)

simulation_service = SimulationService()

@simulation_controls_bp.route('/simulation/setup', methods=['POST'])
def setup_simulation():
    try:
        simulation_service.setup_simulation()
        flash('Simulation setup successfully!', 'success')
    except Exception as e:
        flash(f'Error setting up simulation: {str(e)}', 'danger')
    return redirect(url_for('admin_dashboard'))

@simulation_controls_bp.route('/simulation/start', methods=['POST'])
def start_simulation():
    try:
        simulation_service.start_simulation()
        flash('Simulation started successfully!', 'success')
    except Exception as e:
        flash(f'Error starting simulation: {str(e)}', 'danger')
    return redirect(url_for('admin_dashboard'))

@simulation_controls_bp.route('/simulation/end', methods=['POST'])
def end_simulation():
    try:
        simulation_service.end_simulation()
        flash('Simulation ended successfully!', 'success')
    except Exception as e:
        flash(f'Error ending simulation: {str(e)}', 'danger')
    return redirect(url_for('admin_dashboard'))

@simulation_controls_bp.route('/simulation/undo', methods=['POST'])
def undo_last_period():
    try:
        simulation_service.undo_last_period()
        flash('Last period undone successfully!', 'success')
    except Exception as e:
        flash(f'Error undoing last period: {str(e)}', 'danger')
    return redirect(url_for('admin_dashboard'))