import copy
from pathlib import Path

import pandas as pd
import streamlit as st


def load_styles() -> None:
    css_path = Path("styles.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    else:
        st.markdown(
            "<style>[data-testid='collapsedControl']{display:none!important;}</style>",
            unsafe_allow_html=True,
        )


def init_state() -> None:
    defaults = {
        "authenticated": False,
        "role": None,  # "team" | "admin"
        "username": "",
        "team_decisions": [],
        "team_results": [],
        "history": [],
        "backup": None,
        "simulation": {
            "configured": False,
            "started": False,
            "ended": False,
            "current_round": 0,
            "max_rounds": 10,
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def snapshot() -> None:
    st.session_state.history.append(
        {
            "team_decisions": copy.deepcopy(st.session_state.team_decisions),
            "team_results": copy.deepcopy(st.session_state.team_results),
            "simulation": copy.deepcopy(st.session_state.simulation),
        }
    )


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = ""
    st.rerun()


@st.cache_data(show_spinner=False)
def _read_csv(candidates: list[str]) -> pd.DataFrame:
    for candidate in candidates:
        p = Path(candidate)
        if p.exists() and p.is_file():
            return pd.read_csv(p)
    return pd.DataFrame()


def _find_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    col_map = {c.strip().lower(): c for c in df.columns}
    for a in aliases:
        key = a.strip().lower()
        if key in col_map:
            return col_map[key]
    return None


@st.cache_data(show_spinner=False)
def load_reference_data() -> dict:
    flights_df = _read_csv(
        ["data/flights.csv", "flights.csv", "data/routes_flights.csv", "routes_flights.csv"]
    )
    fields_df = _read_csv(
        ["data/decision_fields.csv", "decision_fields.csv", "data/team_fields.csv", "team_fields.csv"]
    )
    params_df = _read_csv(
        ["data/sim_params.csv", "sim_params.csv", "data/parameters.csv", "parameters.csv"]
    )

    # flights: route + flight
    route_to_flights: dict[str, list[str]] = {}
    if not flights_df.empty:
        route_col = _find_col(flights_df, ["route", "market", "route_code"])
        flight_col = _find_col(flights_df, ["flight", "flight_number", "flight_no", "flight_id"])
        if route_col and flight_col:
            rows = flights_df[[route_col, flight_col]].dropna()
            for _, r in rows.iterrows():
                route = str(r[route_col]).strip()
                flight = str(r[flight_col]).strip()
                if route and flight:
                    route_to_flights.setdefault(route, [])
                    if flight not in route_to_flights[route]:
                        route_to_flights[route].append(flight)

    # decision fields:
    # field,label,type,min,max,step,default,options
    decision_fields: list[dict] = []
    if not fields_df.empty:
        field_col = _find_col(fields_df, ["field", "name", "key"])
        label_col = _find_col(fields_df, ["label", "title"])
        type_col = _find_col(fields_df, ["type", "input_type", "dtype"])
        min_col = _find_col(fields_df, ["min", "min_value"])
        max_col = _find_col(fields_df, ["max", "max_value"])
        step_col = _find_col(fields_df, ["step"])
        default_col = _find_col(fields_df, ["default", "default_value"])
        options_col = _find_col(fields_df, ["options", "choices"])

        if field_col and type_col:
            for _, r in fields_df.iterrows():
                field = str(r[field_col]).strip()
                if not field:
                    continue
                decision_fields.append(
                    {
                        "field": field,
                        "label": str(r[label_col]).strip() if label_col else field.replace("_", " ").title(),
                        "type": str(r[type_col]).strip().lower(),
                        "min": None if min_col is None or pd.isna(r[min_col]) else float(r[min_col]),
                        "max": None if max_col is None or pd.isna(r[max_col]) else float(r[max_col]),
                        "step": None if step_col is None or pd.isna(r[step_col]) else float(r[step_col]),
                        "default": None if default_col is None or pd.isna(r[default_col]) else r[default_col],
                        "options": []
                        if options_col is None or pd.isna(r[options_col])
                        else [x.strip() for x in str(r[options_col]).split("|") if x.strip()],
                    }
                )

    # sim params: key,value
    sim_params: dict[str, float] = {}
    if not params_df.empty:
        key_col = _find_col(params_df, ["key", "param", "name"])
        value_col = _find_col(params_df, ["value", "val"])
        if key_col and value_col:
            for _, r in params_df.iterrows():
                key = str(r[key_col]).strip()
                if not key:
                    continue
                try:
                    sim_params[key] = float(r[value_col])
                except Exception:
                    continue

    return {
        "route_to_flights": route_to_flights,
        "decision_fields": decision_fields,
        "sim_params": sim_params,
    }


def _render_dynamic_field(spec: dict, widget_key: str):
    field_type = spec["type"]
    label = spec["label"]
    min_v = spec["min"]
    max_v = spec["max"]
    step_v = spec["step"]
    default_v = spec["default"]

    if field_type in ("int", "integer"):
        return int(
            st.number_input(
                label,
                min_value=int(min_v) if min_v is not None else 0,
                max_value=int(max_v) if max_v is not None else None,
                step=int(step_v) if step_v is not None else 1,
                value=int(default_v) if default_v is not None else 0,
                key=widget_key,
            )
        )

    if field_type in ("float", "number", "decimal"):
        return float(
            st.number_input(
                label,
                min_value=float(min_v) if min_v is not None else 0.0,
                max_value=float(max_v) if max_v is not None else None,
                step=float(step_v) if step_v is not None else 1.0,
                value=float(default_v) if default_v is not None else 0.0,
                key=widget_key,
            )
        )

    if field_type in ("select", "choice", "categorical"):
        options = spec["options"] if spec["options"] else [""]
        index = options.index(str(default_v)) if default_v is not None and str(default_v) in options else 0
        return st.selectbox(label, options, index=index, key=widget_key)

    return st.text_input(label, value="" if default_v is None else str(default_v), key=widget_key)


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
    _, c2 = st.columns([5, 1])
    with c2:
        if st.button("Logout", use_container_width=True):
            logout()

    ref = load_reference_data()
    route_to_flights = ref["route_to_flights"]
    decision_fields = ref["decision_fields"]

    # team action 1: enter decisions
    st.subheader("Enter Decisions")

    if not route_to_flights:
        st.error("Flights data not found. Add CSV with route + flight columns.")
        return

    routes = sorted(route_to_flights.keys())
    with st.form("team_decision_form"):
        route = st.selectbox("Route", routes, index=0)
        flights = route_to_flights.get(route, [])
        flight = st.selectbox("Flight", flights if flights else [""])

        decision = {
            "round": st.session_state.simulation["current_round"],
            "route": route,
            "flight": flight,
        }

        if decision_fields:
            for spec in decision_fields:
                if spec["field"] in {"route", "flight", "round"}:
                    continue
                decision[spec["field"]] = _render_dynamic_field(spec, f"team_{spec['field']}")
        else:
            # fallback if decision schema CSV is missing
            decision["planned_flights"] = st.number_input("Planned Flights", min_value=1, value=2, step=1)
            decision["seats_per_flight"] = st.number_input("Seats per Flight", min_value=1, value=120, step=1)
            decision["avg_fare"] = st.number_input("Average Fare", min_value=0.0, value=199.0, step=1.0)

        if st.form_submit_button("Save Decision", type="primary"):
            replaced = False
            for i, row in enumerate(st.session_state.team_decisions):
                if (
                    row.get("round") == decision["round"]
                    and row.get("route") == decision["route"]
                    and row.get("flight") == decision["flight"]
                ):
                    st.session_state.team_decisions[i] = decision
                    replaced = True
                    break
            if not replaced:
                st.session_state.team_decisions.append(decision)
            st.success("Decision saved.")

    # team action 2: view current decisions
    st.subheader("View Current Decisions")
    current_round = st.session_state.simulation["current_round"]
    current_rows = [d for d in st.session_state.team_decisions if d.get("round") == current_round]
    if current_rows:
        st.dataframe(current_rows, use_container_width=True)
    else:
        st.info("No decisions entered yet for this round.")

    # team action 3: view results
    st.subheader("View Results")
    if st.session_state.team_results:
        st.dataframe(st.session_state.team_results, use_container_width=True)
    else:
        st.info("No results available yet.")


def render_admin() -> None:
    st.markdown('<div class="title">Admin View</div>', unsafe_allow_html=True)
    _, c2 = st.columns([5, 1])
    with c2:
        if st.button("Logout", use_container_width=True):
            logout()

    sim = st.session_state.simulation
    ref = load_reference_data()
    params = ref["sim_params"]

    # admin action group: setup simulation
    st.subheader("Setup Simulation")
    with st.form("setup_form"):
        default_rounds = int(params.get("default_max_rounds", sim["max_rounds"]))
        max_rounds = st.number_input("Max Rounds", min_value=1, value=default_rounds, step=1)
        if st.form_submit_button("Setup", type="primary"):
            snapshot()
            sim["configured"] = True
            sim["started"] = False
            sim["ended"] = False
            sim["current_round"] = 0
            sim["max_rounds"] = int(max_rounds)
            st.success("Simulation configured.")
            st.rerun()

    # admin action group: start/next/undo/end
    st.subheader("Start / Next / Undo / End")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("Start", use_container_width=True, disabled=(not sim["configured"] or sim["ended"])):
            snapshot()
            sim["started"] = True
            if sim["current_round"] == 0:
                sim["current_round"] = 1
            st.success("Simulation started.")

    with c2:
        if st.button("Next", use_container_width=True):
            if not sim["started"] or sim["ended"]:
                st.warning("Simulation is not running.")
            elif sim["current_round"] > sim["max_rounds"]:
                st.warning("Already at final round.")
            else:
                snapshot()
                round_no = sim["current_round"]
                round_decisions = [d for d in st.session_state.team_decisions if d.get("round") == round_no]

                base_demand = float(params.get("base_demand_per_flight", 90.0))
                marketing_factor = float(params.get("marketing_factor", 0.01))
                fixed_cost_per_flight = float(params.get("fixed_cost_per_flight", 3500.0))
                seat_cost = float(params.get("seat_cost", 12.0))

                if not round_decisions:
                    st.session_state.team_results.append({"round": round_no, "status": "No decision submitted"})
                else:
                    for d in round_decisions:
                        planned_flights = float(d.get("planned_flights", 1))
                        seats_per_flight = float(d.get("seats_per_flight", d.get("seats", 0)))
                        avg_fare = float(d.get("avg_fare", d.get("fare", 0.0)))
                        bag_fee = float(d.get("bag_fee", 0.0))
                        marketing_budget = float(d.get("marketing_budget", 0.0))

                        capacity = int(planned_flights * seats_per_flight)
                        demand = int(base_demand * planned_flights + marketing_budget * marketing_factor)
                        pax = min(capacity, demand)
                        revenue = pax * (avg_fare + bag_fee)
                        cost = planned_flights * fixed_cost_per_flight + capacity * seat_cost
                        profit = revenue - cost

                        st.session_state.team_results.append(
                            {
                                "round": round_no,
                                "route": d.get("route"),
                                "flight": d.get("flight"),
                                "pax": pax,
                                "revenue": round(revenue, 2),
                                "cost": round(cost, 2),
                                "profit": round(profit, 2),
                            }
                        )

                if sim["current_round"] < sim["max_rounds"]:
                    sim["current_round"] += 1
                else:
                    sim["started"] = False
                    sim["ended"] = True

                st.success("Round processed.")

    with c3:
        if st.button("Undo", use_container_width=True):
            if not st.session_state.history:
                st.warning("Nothing to undo.")
            else:
                prev = st.session_state.history.pop()
                st.session_state.team_decisions = prev["team_decisions"]
                st.session_state.team_results = prev["team_results"]
                st.session_state.simulation = prev["simulation"]
                st.success("Last action undone.")

    with c4:
        if st.button("End", use_container_width=True):
            if not sim["started"] or sim["ended"]:
                st.warning("Simulation is not running.")
            else:
                snapshot()
                sim["started"] = False
                sim["ended"] = True
                st.success("Simulation ended.")

    # admin action group: backup/restore/destroy
    st.subheader("Backup / Restore / Destroy")
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Backup", use_container_width=True):
            st.session_state.backup = {
                "team_decisions": copy.deepcopy(st.session_state.team_decisions),
                "team_results": copy.deepcopy(st.session_state.team_results),
                "history": copy.deepcopy(st.session_state.history),
                "simulation": copy.deepcopy(st.session_state.simulation),
            }
            st.success("Backup created.")

    with b2:
        if st.button("Restore", use_container_width=True):
            if st.session_state.backup is None:
                st.warning("No backup available.")
            else:
                st.session_state.team_decisions = copy.deepcopy(st.session_state.backup["team_decisions"])
                st.session_state.team_results = copy.deepcopy(st.session_state.backup["team_results"])
                st.session_state.history = copy.deepcopy(st.session_state.backup["history"])
                st.session_state.simulation = copy.deepcopy(st.session_state.backup["simulation"])
                st.success("Backup restored.")

    with b3:
        if st.button("Destroy", use_container_width=True):
            st.session_state.team_decisions = []
            st.session_state.team_results = []
            st.session_state.history = []
            st.session_state.simulation = {
                "configured": False,
                "started": False,
                "ended": False,
                "current_round": 0,
                "max_rounds": 10,
            }
            st.success("Simulation data destroyed.")


def main() -> None:
    st.set_page_config(page_title="Airline Simulation", layout="wide")
    init_state()
    load_styles()

    # Only allowed routing: st.session_state auth + role
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