from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.admin_service import AdminService
from app.utils.auth import is_authenticated

admin_controls_bp = Blueprint('admin_controls', __name__)

@admin_controls_bp.route('/admin/setup', methods=['POST'])
def setup_simulation():
    if not is_authenticated():
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('admin_view.login'))
    
    AdminService.setup_simulation()
    flash('Simulation setup completed successfully.', 'success')
    return redirect(url_for('admin_dashboard.index'))

@admin_controls_bp.route('/admin/start', methods=['POST'])
def start_simulation():
    if not is_authenticated():
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('admin_view.login'))
    
    AdminService.start_simulation()
    flash('Simulation started successfully.', 'success')
    return redirect(url_for('admin_dashboard.index'))

@admin_controls_bp.route('/admin/end', methods=['POST'])
def end_simulation():
    if not is_authenticated():
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('admin_view.login'))
    
    AdminService.end_simulation()
    flash('Simulation ended successfully.', 'success')
    return redirect(url_for('admin_dashboard.index'))

@admin_controls_bp.route('/admin/undo', methods=['POST'])
def undo_last_period():
    if not is_authenticated():
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('admin_view.login'))
    
    AdminService.undo_last_period()
    flash('Last period undone successfully.', 'success')
    return redirect(url_for('admin_dashboard.index'))