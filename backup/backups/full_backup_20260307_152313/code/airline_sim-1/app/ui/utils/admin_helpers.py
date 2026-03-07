# filepath: /workspaces/airline_sim/app/ui/utils/admin_helpers.py

def get_admin_username_passwords(csv_file_path):
    """Reads the CSV file containing admin usernames and passwords."""
    import csv
    admin_credentials = {}
    with open(csv_file_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            username, password = row
            admin_credentials[username] = password
    return admin_credentials

def is_valid_admin(username, password, admin_credentials):
    """Validates the admin username and password."""
    return admin_credentials.get(username) == password

def log_admin_action(action, username):
    """Logs the actions performed by the admin."""
    import logging
    logging.basicConfig(filename='admin_actions.log', level=logging.INFO)
    logging.info(f'Admin {username} performed action: {action}')