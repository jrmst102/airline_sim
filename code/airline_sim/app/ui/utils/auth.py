# filepath: /workspaces/airline_sim/app/ui/utils/auth.py

import csv
from flask import session, redirect, url_for, flash

def load_user_credentials(filepath):
    credentials = {}
    with open(filepath, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            credentials[row[0]] = row[1]
    return credentials

def authenticate(username, password, credentials):
    if username in credentials and credentials[username] == password:
        session['username'] = username
        return True
    return False

def is_authenticated():
    return 'username' in session

def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

def require_authentication(f):
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper