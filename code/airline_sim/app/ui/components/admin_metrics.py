from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.admin_service import AdminService
from app.utils.auth import login_required

admin_metrics_bp = Blueprint('admin_metrics', __name__)

@admin_metrics_bp.route('/admin/metrics', methods=['GET'])
@login_required
def metrics():
    metrics_data = AdminService.get_metrics()
    return render_template('admin_metrics.html', metrics=metrics_data)

@admin_metrics_bp.route('/admin/metrics/update', methods=['POST'])
@login_required
def update_metrics():
    new_metrics = request.form.get('metrics')
    if AdminService.update_metrics(new_metrics):
        flash('Metrics updated successfully!', 'success')
    else:
        flash('Failed to update metrics.', 'danger')
    return redirect(url_for('admin_metrics.metrics'))