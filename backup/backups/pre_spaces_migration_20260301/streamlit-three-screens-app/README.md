# Streamlit Three Screens App

This project is a simple Streamlit application that implements a user interface with exactly three screens: Login screen, Team View screen, and Admin View screen. The application is designed to demonstrate user authentication and role-based access control.

## Project Structure

```
streamlit-three-screens-app
├── app.py               # Main Streamlit application file
├── requirements.txt     # List of dependencies
└── README.md            # Project documentation
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd streamlit-three-screens-app
   ```

2. **Install Dependencies**
   It is recommended to use a virtual environment. You can create one using `venv` or `conda`. After activating your environment, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage Guidelines

1. **Run the Application**
   To start the Streamlit application, run the following command:
   ```bash
   streamlit run app.py
   ```

2. **Accessing the Application**
   Open your web browser and navigate to the URL provided in the terminal (usually `http://localhost:8501`).

## Application Functionality

- **Login Screen**: Users can log in by entering their credentials. The application checks the authentication status and user role.
  
- **Team View Screen**: Accessible to users with the "team" role. This screen allows team members to enter decisions, view current decisions, and see results.

- **Admin View Screen**: Accessible to users with the "admin" role. This screen provides admin lifecycle actions such as setting up the simulation, starting or ending the simulation, and managing backups.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.