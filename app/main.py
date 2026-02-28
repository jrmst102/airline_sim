import copy
import streamlit as st


def load_styles() -> None:
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback to keep sidebar collapse control hidden
        st.markdown(
            """
            <style>
            [data-testid="collapsedControl"] { display: none !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )


def init_state() -> None:
    defaults = {
        "authenticated": False,
        "role": None,  # "team" | "admin"
        "username": "",
        "team_decisions": [],
        "team_results": [],
        "simulation": {
            "configured": False,
            "started": False,
            "ended": False,
            "current_round": 0,
            "max_rounds": 10,
        },
        "history": [],
        "backup": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def snapshot() -> None:
    st.session_state.history.append(
        {
            "simulation": copy.deepcopy(st.session_state.simulation),
            "team_decisions": copy.deepcopy(st.session_state.team_decisions),
            "team_results": copy.deepcopy(st.session_state.team_results),
        }
    )


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = ""
    st.rerun()


def render_login() -> None:
    st.markdown('<div class="title">Airline Simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Login</div>', unsafe_allow_html=True)

    with st.container(border=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["team", "admin"], index=0)

        if st.button("Login", type="primary", use_container_width=True):
            if username.strip() and password.strip():
                st.session_state.authenticated = True
                st.session_state.role = role
                st.session_state.username = username.strip()
                st.rerun()
            else:
                st.error("Enter username and password.")


def render_team() -> None:
    st.markdown('<div class="title">Team View</div>', unsafe_allow_html=True)
    _, c_logout = st.columns([5, 1])
    with c_logout:
        if st.button("Logout", use_container_width=True):
            logout()

    # Team actions only:
    # 1) enter decisions
    # 2) view current decisions
    # 3) view results
    st.subheader("Enter Decisions")
    with st.form("team_decision_form"):
        route = st.text_input("Route")
        seats = st.number_input("Seats", min_value=0, step=1, value=120)
        fare = st.number_input("Average Fare", min_value=0.0, step=1.0, value=199.0)
        submit = st.form_submit_button("Save Decision", type="primary")
        if submit:
            if not route.strip():
                st.error("Route is required.")
            else:
                st.session_state.team_decisions.append(
                    {
                        "round": st.session_state.simulation["current_round"],
                        "route": route.strip(),
                        "seats": int(seats),
                        "fare": float(fare),
                    }
                )
                st.success("Decision saved.")

    st.subheader("View Current Decisions")
    if st.session_state.team_decisions:
        st.dataframe(st.session_state.team_decisions, use_container_width=True)
    else:
        st.info("No decisions entered yet.")

    st.subheader("View Results")
    if st.session_state.team_results:
        st.dataframe(st.session_state.team_results, use_container_width=True)
    else:
        st.info("No results available yet.")


def render_admin() -> None:
    st.markdown('<div class="title">Admin View</div>', unsafe_allow_html=True)
    _, c_logout = st.columns([5, 1])
    with c_logout:
        if st.button("Logout", use_container_width=True):
            logout()

    sim = st.session_state.simulation

    # Admin lifecycle actions only:
    # setup simulation, start/next/undo/end, backup/restore/destroy
    st.subheader("Setup Simulation")
    with st.form("setup_form"):
        max_rounds = st.number_input("Max Rounds", min_value=1, step=1, value=int(sim["max_rounds"]))
        setup_click = st.form_submit_button("Setup", type="primary")
        if setup_click:
            snapshot()
            sim["configured"] = True
            sim["started"] = False
            sim["ended"] = False
            sim["current_round"] = 0
            sim["max_rounds"] = int(max_rounds)
            st.success("Simulation configured.")

    st.subheader("Lifecycle")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("Start", use_container_width=True):
            if sim["configured"] and not sim["ended"]:
                snapshot()
                sim["started"] = True
                if sim["current_round"] == 0:
                    sim["current_round"] = 1
                st.success("Simulation started.")
            else:
                st.warning("Configure simulation first.")

    with c2:
        if st.button("Next", use_container_width=True):
            if not sim["started"] or sim["ended"]:
                st.warning("Simulation is not running.")
            elif sim["current_round"] >= sim["max_rounds"]:
                st.warning("Already at final round.")
            else:
                snapshot()
                sim["current_round"] += 1
                st.session_state.team_results.append(
                    {"round": sim["current_round"], "status": "Processed"}
                )
                st.success("Moved to next round.")

    with c3:
        if st.button("Undo", use_container_width=True):
            if st.session_state.history:
                last = st.session_state.history.pop()
                st.session_state.simulation = last["simulation"]
                st.session_state.team_decisions = last["team_decisions"]
                st.session_state.team_results = last["team_results"]
                st.success("Last action undone.")
            else:
                st.warning("Nothing to undo.")

    with c4:
        if st.button("End", use_container_width=True):
            if sim["started"] and not sim["ended"]:
                snapshot()
                sim["started"] = False
                sim["ended"] = True
                st.success("Simulation ended.")
            else:
                st.warning("Simulation is not running.")

    st.subheader("Backup / Restore / Destroy")
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Backup", use_container_width=True):
            st.session_state.backup = {
                "simulation": copy.deepcopy(st.session_state.simulation),
                "team_decisions": copy.deepcopy(st.session_state.team_decisions),
                "team_results": copy.deepcopy(st.session_state.team_results),
                "history": copy.deepcopy(st.session_state.history),
            }
            st.success("Backup created.")

    with b2:
        if st.button("Restore", use_container_width=True):
            if st.session_state.backup is None:
                st.warning("No backup found.")
            else:
                st.session_state.simulation = copy.deepcopy(st.session_state.backup["simulation"])
                st.session_state.team_decisions = copy.deepcopy(st.session_state.backup["team_decisions"])
                st.session_state.team_results = copy.deepcopy(st.session_state.backup["team_results"])
                st.session_state.history = copy.deepcopy(st.session_state.backup["history"])
                st.success("Backup restored.")

    with b3:
        if st.button("Destroy", use_container_width=True):
            st.session_state.simulation = {
                "configured": False,
                "started": False,
                "ended": False,
                "current_round": 0,
                "max_rounds": 10,
            }
            st.session_state.team_decisions = []
            st.session_state.team_results = []
            st.session_state.history = []
            st.success("Simulation data destroyed.")


def main() -> None:
    st.set_page_config(page_title="Airline Simulation", layout="wide")
    init_state()
    load_styles()

    # Routing only through session_state (exactly three screens)
    if not st.session_state.authenticated:
        render_login()
    elif st.session_state.role == "team":
        render_team()
    elif st.session_state.role == "admin":
        render_admin()
    else:
        logout()


if __name__ == "__main__":
    main()