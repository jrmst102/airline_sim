# Airline Simulation Project

## Overview
The Airline Simulation project is designed to simulate the operations of an airline, allowing users to manage teams, control simulations, and view real-time data. This project includes an admin dashboard for instructors to oversee and control the simulation effectively.

## Project Structure
```
airline_sim
├── app
│   ├── data
│   │   └── passwords
│   │       └── usernames.csv
│   ├── ui
│   │   ├── dashboard.py
│   │   ├── admin_view.py
│   │   ├── admin_dashboard.py
│   │   ├── components
│   │   │   ├── admin_controls.py
│   │   │   ├── team_data_viewer.py
│   │   │   ├── simulation_controls.py
│   │   │   └── admin_metrics.py
│   │   ├── styles
│   │   │   └── admin_styles.py
│   │   └── utils
│   │       ├── auth.py
│   │       └── admin_helpers.py
│   ├── services
│   │   ├── admin_service.py
│   │   ├── simulation_service.py
│   │   └── team_data_service.py
│   └── routes
│       └── admin_routes.py
├── tests
│   ├── test_admin_dashboard.py
│   ├── test_admin_service.py
│   └── test_auth.py
└── README.md
```

## Features
- **Admin Authentication**: Admins can log in using credentials stored in `app/data/passwords/usernames.csv`.
- **Simulation Control**: Admins can set up, start, end, and undo simulation periods through the admin dashboard.
- **Team Data Viewing**: Real-time data for each team can be viewed and analyzed.
- **Metrics Display**: Admin metrics related to the simulation are available for review.

## Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/jrmst102/airline_sim.git
   cd airline_sim
   ```

2. **Install Dependencies**:
   Ensure you have Python and pip installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   Start the application using:
   ```bash
   python app/ui/admin_dashboard.py
   ```

## Environment Variables
- Ensure to set any necessary environment variables as specified in the project documentation.

## Deployment
For deployment instructions, refer to the deployment section in the respective service files.

## Testing
Run tests using:
```bash
pytest tests/
```

## Contribution
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.