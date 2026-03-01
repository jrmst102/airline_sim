# File: /streamlit-three-screens-app/streamlit-three-screens-app/app.py

import streamlit as st

# Function to render the login screen
def render_login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == "admin" and password == "admin":
            st.session_state.authenticated = True
            st.session_state.role = "admin"
        elif username == "team" and password == "team":
            st.session_state.authenticated = True
            st.session_state.role = "team"
        else:
            st.error("Invalid credentials")

# Function to render the team view screen
def render_team():
    st.title("Team View")
    st.write("Welcome to the Team View!")
    # Add team actions here
    if st.button("Enter Decisions"):
        st.write("Decisions entered.")
    if st.button("View Current Decisions"):
        st.write("Current decisions displayed.")
    if st.button("View Results"):
        st.write("Results displayed.")

# Function to render the admin view screen
def render_admin():
    st.title("Admin View")
    st.write("Welcome to the Admin View!")
    # Add admin actions here
    if st.button("Setup Simulation"):
        st.write("Simulation setup.")
    if st.button("Start Simulation"):
        st.write("Simulation started.")
    if st.button("End Simulation"):
        st.write("Simulation ended.")

# Main application logic
def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        render_login()
    else:
        if st.session_state.role == "team":
            render_team()
        elif st.session_state.role == "admin":
            render_admin()

if __name__ == "__main__":
    main()