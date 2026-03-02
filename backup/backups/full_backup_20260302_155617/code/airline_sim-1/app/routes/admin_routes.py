from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from app.utils.auth import is_authenticated, authenticate
from app.services.admin_service import AdminService

admin_routes = Blueprint('admin_routes', __name__)

@admin_routes.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            session['username'] = username
            return redirect(url_for('admin_routes.admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.')
    return render_template('admin_dashboard.html')

@admin_routes.route('/admin/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('admin_routes.admin_dashboard'))

@admin_routes.route('/admin/simulation/start', methods=['POST'])
def start_simulation():
    if not is_authenticated(session):
        return redirect(url_for('admin_routes.admin_dashboard'))
    AdminService.start_simulation()
    flash('Simulation started successfully.')
    return redirect(url_for('admin_routes.admin_dashboard'))

@admin_routes.route('/admin/simulation/end', methods=['POST'])
def end_simulation():
    if not is_authenticated(session):
        return redirect(url_for('admin_routes.admin_dashboard'))
    AdminService.end_simulation()
    flash('Simulation ended successfully.')
    return redirect(url_for('admin_routes.admin_dashboard'))

@admin_routes.route('/admin/simulation/undo', methods=['POST'])
def undo_last_period():
    if not is_authenticated(session):
        return redirect(url_for('admin_routes.admin_dashboard'))
    AdminService.undo_last_period()
    flash('Last period undone successfully.')
    return redirect(url_for('admin_routes.admin_dashboard'))

@admin_routes.route('/admin/team_data')
def team_data():
    if not is_authenticated(session):
        return redirect(url_for('admin_routes.admin_dashboard'))
    data = AdminService.get_team_data()
    return render_template('team_data_viewer.html', data=data)