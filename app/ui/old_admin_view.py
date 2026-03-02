"""
Airlines – Competitive Strategy Simulation · Admin Dashboard
=============================================================
Single-page Streamlit admin dashboard.  No login, no sidebar, no nav.

Run with:
    streamlit run app/ui/admin_view.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so `from app.…` imports work
# regardless of how Streamlit is launched.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AUTO_REFRESH_SECONDS = 60
PAGE_TITLE = "Airlines - Competitive Strategy Simulation"
COPYRIGHT = "Copyright 2026 by Dr. Jose Mendoza"
SIM_ID = "sim_001"
ROOT_DIR = Path("simulation/simulations")
ADMIN_USER_ID = "U_ADMIN"

_LOGO_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "images" / "sim_logo.png",
    Path("./assets/logo.png"),
]


def _data_root() -> Path:
    return Path(os.environ.get("DATA_ROOT", "."))


def _sim_dir() -> Path:
    return _data_root() / "simulation" / "simulations" / SIM_ID


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
_CUSTOM_CSS = """
<style>
section[data-testid="stSidebar"]  { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

.main .block-container {
    max-width: 900px !important;
    padding-top: 16px !important;
    padding-bottom: 16px !important;
}

.badge {
    display: inline-block;
    padding: 5px 16px;
    border-radius: 18px;
    font-weight: 700;
    font-size: 0.95rem;
    letter-spacing: 0.4px;
}
.badge-started   { background: #16a34a; color: #fff; }
.badge-created   { background: #6b7280; color: #fff; }
.badge-stopped   { background: #dc2626; color: #fff; }
.badge-completed { background: #7c3aed; color: #fff; }
.badge-ended     { background: #7c3aed; color: #fff; }
.badge-notfound  { background: #f97316; color: #fff; }

.round-card {
    text-align: center;
    padding: 10px;
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 12px;
    background: rgba(255,255,255,0.03);
}
.round-card .label { font-size: 0.8rem; color: #9ca3af; margin-bottom: 2px; }
.round-card .value { font-size: 2rem; font-weight: 800; color: #2563eb; }

.round-state {
    text-align: center;
    font-size: 0.85rem;
    color: #9ca3af;
    margin-top: 4px;
}

.footer {
    margin-top: 24px;
    padding-top: 10px;
    border-top: 1px solid rgba(128,128,128,0.2);
    text-align: center;
    color: #9ca3af;
    font-size: 0.85rem;
}

/* Action button rows */
.stButton > button { min-height: 2.4rem; }
</style>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _auto_refresh() -> None:
    st.markdown(
        f"<meta http-equiv='refresh' content='{AUTO_REFRESH_SECONDS}'>",
        unsafe_allow_html=True,
    )


def _read_csv_safe(path: Path) -> pd.DataFrame | None:
    """Read a CSV; return None on any failure."""
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return None


def normalize_status(value: str) -> str:
    """Map raw status strings to canonical values."""
    s = str(value).strip().upper()
    mapping = {
        "RUNNING": "STARTED",
        "SETUP": "CREATED",
        "ARCHIVED": "COMPLETED",
        "ENDED": "COMPLETED",
    }
    return mapping.get(s, s)


def get_latest_round(df_rounds: pd.DataFrame) -> tuple[int, str]:
    """Return (round_number, status) of the latest round, or (0, 'NONE')."""
    if df_rounds is None or df_rounds.empty:
        return 0, "NONE"
    rn_col = next(
        (c for c in df_rounds.columns if c.strip().lower() == "round_number"), None
    )
    st_col = next(
        (c for c in df_rounds.columns if c.strip().lower() == "status"), None
    )
    if rn_col is None:
        return 0, "NONE"
    df_rounds = df_rounds.copy()
    df_rounds["_rn"] = pd.to_numeric(df_rounds[rn_col], errors="coerce")
    df_rounds = df_rounds.dropna(subset=["_rn"])
    if df_rounds.empty:
        return 0, "NONE"
    idx = df_rounds["_rn"].idxmax()
    rn = int(df_rounds.loc[idx, "_rn"])
    status = str(df_rounds.loc[idx, st_col]).strip().upper() if st_col else "NONE"
    return rn, status


def ensure_simulation_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure required columns exist in simulation DataFrame."""
    required = [
        "simulation_id", "name", "status", "current_round",
        "total_rounds", "created_at_utc", "updated_at_utc",
    ]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    return df


def ensure_rounds_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure required columns exist in rounds DataFrame."""
    required = ["simulation_id", "round_number", "status", "opened_at_utc", "closed_at_utc"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    return df


def append_system_message(
    msg: str, level: str = "info"
) -> None:
    """Show a message using the appropriate Streamlit widget."""
    if level == "success":
        st.success(msg)
    elif level == "warning":
        st.warning(msg)
    elif level == "error":
        st.error(msg)
    else:
        st.info(msg)


# ---------------------------------------------------------------------------
# Status detection (reuse dashboard logic)
# ---------------------------------------------------------------------------
def _determine_status(sim_path: Path) -> str:
    """Return one of CREATED, STARTED, STOPPED, COMPLETED, NOT_FOUND."""
    if not sim_path.exists():
        return "NOT_FOUND"
    sim_df = _read_csv_safe(sim_path / "simulation.csv")
    if sim_df is not None and not sim_df.empty:
        status_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "status"), None
        )
        if status_col is not None:
            return normalize_status(sim_df.iloc[-1][status_col])
    rounds_df = _read_csv_safe(sim_path / "rounds.csv")
    if rounds_df is not None and not rounds_df.empty:
        st_col = next(
            (c for c in rounds_df.columns if c.strip().lower() == "status"), None
        )
        if st_col is not None:
            opened = rounds_df[
                rounds_df[st_col].str.strip().str.upper().isin({"OPEN", "CLOSED"})
            ]
            if not opened.empty:
                return "STARTED"
    return "CREATED"


def _current_round_info(sim_path: Path) -> tuple[int, str, int]:
    """Return (current_round, round_status, total_rounds)."""
    total_rounds = 0
    sim_df = _read_csv_safe(sim_path / "simulation.csv")
    if sim_df is not None and not sim_df.empty:
        tr_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "total_rounds"), None
        )
        if tr_col is not None:
            vals = pd.to_numeric(pd.Series([sim_df.iloc[-1][tr_col]]), errors="coerce").dropna()
            if not vals.empty:
                total_rounds = int(vals.iloc[0])
        cr_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "current_round"), None
        )
        if cr_col is not None:
            val = pd.to_numeric(pd.Series([sim_df.iloc[-1][cr_col]]), errors="coerce").dropna()
            if not val.empty:
                current = int(val.iloc[0])
                rounds_df = _read_csv_safe(sim_path / "rounds.csv")
                _, r_status = get_latest_round(rounds_df) if rounds_df is not None else (0, "NONE")
                return current, r_status, total_rounds

    rounds_df = _read_csv_safe(sim_path / "rounds.csv")
    rn, r_status = get_latest_round(rounds_df)
    return rn, r_status, total_rounds


def _fill_baseline_estimates(show_df: pd.DataFrame, teams_df: pd.DataFrame | None) -> None:
    """Fill empty revenue/total_cost cells with estimates derived from baseline data.

    For the round-0 baseline snapshot the case appendix provides passengers
    and profit but not revenue or cost.  We can estimate:
        revenue  ≈ passengers × average_fare  (average fare ≈ $250 placeholder)
        cost     ≈ revenue − profit
    This gives meaningful numbers in the Team Stats table instead of "—".
    """
    if show_df is None or show_df.empty:
        return

    AVG_FARE_ESTIMATE = 250  # reasonable midpoint across postures/segments

    pax = pd.to_numeric(show_df.get("passengers"), errors="coerce")
    profit = pd.to_numeric(show_df.get("profit"), errors="coerce")
    rev = pd.to_numeric(show_df.get("revenue"), errors="coerce")
    cost = pd.to_numeric(show_df.get("total_cost"), errors="coerce")

    # Only fill where revenue is missing but passengers is available
    rev_missing = rev.isna() & pax.notna()
    if rev_missing.any():
        # Use variable_cost_per_passenger if available for a better estimate
        vcpp = pd.to_numeric(show_df.get("variable_cost_per_passenger"), errors="coerce")
        estimated_rev = pax * AVG_FARE_ESTIMATE
        show_df.loc[rev_missing, "revenue"] = estimated_rev[rev_missing].astype(int).astype(str)

        # Estimate cost = revenue − profit
        if profit is not None:
            estimated_cost = estimated_rev - profit
            cost_missing = cost.isna() & profit.notna()
            if cost_missing.any():
                show_df.loc[cost_missing, "total_cost"] = (
                    estimated_cost[cost_missing].astype(int).astype(str)
                )


def _build_team_table(sim_path: Path, latest_round: int) -> pd.DataFrame:
    """Build a display-ready team stats table."""
    teams_df = _read_csv_safe(sim_path / "teams.csv")
    results_df = _read_csv_safe(sim_path / "round_results_team.csv")

    # Column mapping: round_results_team → display name
    desired = {
        "team_name": "Team",
        "team_id": "ID",
        "round_number": "Round",
        "passengers": "Passengers",
        "price_business": "Biz Price",
        "price_leisure": "Lei Price",
        "revenue": "Revenue",
        "variable_cost": "Variable Cost",
        "fixed_cost": "Fixed Cost",
        "branding_cost": "Branding Cost",
        "product_cost": "Product Cost",
        "total_cost": "Total Cost",
        "profit": "Profit",
        "load_factor": "Load Factor",
        "market_share_volume": "Mkt Share (Vol)",
        "market_share_profit": "Mkt Share (Profit)",
        "csi": "CSI",
        "oei": "OEI",
    }

    # ── Try to show results for the current round ──────────────
    if results_df is not None and not results_df.empty:
        rn_col = next(
            (c for c in results_df.columns if c.strip().lower() == "round_number"), None
        )
        show_df = results_df
        if rn_col:
            filtered = results_df[
                pd.to_numeric(results_df[rn_col], errors="coerce") == latest_round
            ]
            if not filtered.empty:
                show_df = filtered
            elif latest_round > 0:
                # No results for this round yet → show baseline with current round #
                fallback = results_df[
                    pd.to_numeric(results_df[rn_col], errors="coerce") == 0
                ]
                if not fallback.empty:
                    show_df = fallback.copy()
                    show_df[rn_col] = str(latest_round)
                else:
                    show_df = None

        if show_df is not None and not show_df.empty:
            # Merge team info from teams.csv if columns are missing
            if teams_df is not None and "team_id" in show_df.columns and "team_id" in teams_df.columns:
                merge_cols = ["team_id"]
                if "team_name" not in show_df.columns and "team_name" in teams_df.columns:
                    merge_cols.append("team_name")
                if "variable_cost_per_passenger" in teams_df.columns:
                    merge_cols.append("variable_cost_per_passenger")
                if len(merge_cols) > 1:
                    show_df = show_df.merge(
                        teams_df[merge_cols].drop_duplicates(),
                        on="team_id", how="left",
                    )

            # Fill missing revenue / cost from baseline estimates
            _fill_baseline_estimates(show_df, teams_df)

            out: dict[str, str] = {}
            for src, dst in desired.items():
                m = next((c for c in show_df.columns if c.strip().lower() == src), None)
                if m is not None:
                    out[m] = dst
            table = show_df[list(out.keys())].rename(columns=out) if out else show_df.copy()

            # Sort by profit descending (before formatting)
            if "Profit" in table.columns:
                table["_sort"] = pd.to_numeric(table["Profit"], errors="coerce")
                table = table.sort_values("_sort", ascending=False).drop(columns=["_sort"])
            elif "Team" in table.columns:
                table = table.sort_values("Team")

            # Format numeric columns
            if "Passengers" in table.columns:
                table["Passengers"] = pd.to_numeric(
                    table["Passengers"], errors="coerce"
                ).apply(lambda v: f"{v:,.0f}" if pd.notna(v) else "\u2014")
            for col in ("Revenue", "Variable Cost", "Fixed Cost", "Branding Cost",
                         "Product Cost", "Total Cost", "Profit", "Biz Price", "Lei Price"):
                if col in table.columns:
                    table[col] = pd.to_numeric(table[col], errors="coerce").apply(
                        lambda v: f"${v:,.0f}" if pd.notna(v) else "\u2014"
                    )
            for col in ("Load Factor", "Mkt Share (Vol)", "Mkt Share (Profit)"):
                if col in table.columns:
                    table[col] = pd.to_numeric(table[col], errors="coerce").apply(
                        lambda v: f"{v:.1%}" if pd.notna(v) else "\u2014"
                    )
            for col in ("CSI", "OEI"):
                if col in table.columns:
                    table[col] = pd.to_numeric(table[col], errors="coerce").apply(
                        lambda v: f"{v:.1f}" if pd.notna(v) else "\u2014"
                    )
            return table.reset_index(drop=True)

    # ── Fallback: show baseline from teams.csv ─────────────────
    if teams_df is not None and not teams_df.empty:
        import math
        SEATS_PER_FLIGHT      = 200
        DAYS_PER_MONTH        = 30
        FIXED_COST_PER_FLIGHT = 18_000

        cols: dict[str, Any] = {}

        # Team info
        for src, dst in [("team_name", "Team"), ("team_id", "ID")]:
            m = next((c for c in teams_df.columns if c.strip().lower() == src), None)
            if m:
                cols[dst] = teams_df[m]

        cols["Round"] = latest_round if latest_round > 0 else "\u2014"

        pax_col    = next((c for c in teams_df.columns if c.strip().lower() == "baseline_passengers"), None)
        profit_col = next((c for c in teams_df.columns if c.strip().lower() == "baseline_profit_millions"), None)
        vcpp_col   = next((c for c in teams_df.columns if c.strip().lower() == "variable_cost_per_passenger"), None)

        pax_n    = pd.to_numeric(teams_df[pax_col], errors="coerce")    if pax_col    else pd.Series(dtype=float)
        profit_n = pd.to_numeric(teams_df[profit_col], errors="coerce") * 1_000_000 if profit_col else pd.Series(dtype=float)
        vcpp_n   = pd.to_numeric(teams_df[vcpp_col], errors="coerce")   if vcpp_col   else pd.Series(dtype=float)

        # Derive flights_per_day (ceil of passengers / capacity-at-100%-LF, capped 1–5)
        cap_per_fpd = SEATS_PER_FLIGHT * DAYS_PER_MONTH          # 6,000
        fpd = pax_n.apply(lambda p: min(max(math.ceil(p / cap_per_fpd), 1), 5) if pd.notna(p) else 0)
        monthly_flights = fpd * DAYS_PER_MONTH
        capacity        = monthly_flights * SEATS_PER_FLIGHT

        BASELINE_BRANDING_COST = 3_000_000   # Medium branding – $3M/mo
        BASELINE_PRODUCT_COST  = 2_000_000   # Low product – $2M/mo

        var_cost    = pax_n * vcpp_n
        fix_cost    = monthly_flights * FIXED_COST_PER_FLIGHT
        brand_cost  = BASELINE_BRANDING_COST
        prod_cost   = BASELINE_PRODUCT_COST
        total_cost  = var_cost + fix_cost + brand_cost + prod_cost
        revenue     = profit_n + total_cost
        load_factor = pax_n / capacity

        def fmt_int(v: float) -> str:
            return f"{v:,.0f}" if pd.notna(v) else "\u2014"
        def fmt_dollar(v: float) -> str:
            return f"${v:,.0f}" if pd.notna(v) else "\u2014"
        def fmt_pct(v: float) -> str:
            return f"{v:.1%}" if pd.notna(v) else "\u2014"

        cols["Passengers"]    = pax_n.apply(fmt_int)
        cols["Biz Price"]      = "$360"   # baseline Match price
        cols["Lei Price"]      = "$180"   # baseline Match price
        cols["Revenue"]       = revenue.apply(fmt_dollar)
        cols["Variable Cost"] = var_cost.apply(fmt_dollar)
        cols["Fixed Cost"]    = fix_cost.apply(fmt_dollar)
        cols["Branding Cost"] = f"${brand_cost:,.0f}"
        cols["Product Cost"]  = f"${prod_cost:,.0f}"
        cols["Total Cost"]    = total_cost.apply(fmt_dollar)
        cols["Profit"]        = profit_n.apply(fmt_dollar)
        cols["Load Factor"]   = load_factor.apply(fmt_pct)

        ms_col = next((c for c in teams_df.columns if c.strip().lower() == "baseline_volume_share"), None)
        if ms_col is not None:
            cols["Mkt Share (Vol)"] = pd.to_numeric(teams_df[ms_col], errors="coerce").apply(fmt_pct)
        else:
            cols["Mkt Share (Vol)"] = "\u2014"

        ps_col = next((c for c in teams_df.columns if c.strip().lower() == "baseline_profit_share"), None)
        if ps_col is not None:
            cols["Mkt Share (Profit)"] = pd.to_numeric(teams_df[ps_col], errors="coerce").apply(fmt_pct)
        else:
            cols["Mkt Share (Profit)"] = "\u2014"

        cols["CSI"] = "100.0"
        cols["OEI"] = "100.0"

        table = pd.DataFrame(cols)
        return table.reset_index(drop=True)

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Badge rendering
# ---------------------------------------------------------------------------
_BADGE_CLASS = {
    "STARTED": "badge-started",
    "CREATED": "badge-created",
    "STOPPED": "badge-stopped",
    "COMPLETED": "badge-completed",
    "ENDED": "badge-ended",
    "NOT_FOUND": "badge-notfound",
}


def _render_badge(status: str) -> str:
    cls = _BADGE_CLASS.get(status, "badge-notfound")
    return f'<span class="badge {cls}">{status}</span>'


# ---------------------------------------------------------------------------
# Safe action runner – catches all exceptions from business-logic modules
# ---------------------------------------------------------------------------
def _run_action(label: str, fn: Any) -> None:
    """Execute *fn()* and display the result or exception in System Messages."""
    try:
        result = fn()
        if result is None:
            append_system_message(f"**{label}** completed.", "success")
        elif isinstance(result, str):
            append_system_message(f"**{label}:** {result}", "success")
        else:
            append_system_message(f"**{label}** completed successfully.", "success")
            # Show dataclass / dict details
            if hasattr(result, "__dict__"):
                for k, v in vars(result).items():
                    st.write(f"  - **{k}:** {v}")
            elif isinstance(result, dict):
                for k, v in result.items():
                    st.write(f"  - **{k}:** {v}")
    except Exception as exc:
        append_system_message(f"**{label}** failed: {exc}", "error")


# ---------------------------------------------------------------------------
# Admin actions – thin wrappers around existing modules
# ---------------------------------------------------------------------------
def _action_start() -> None:
    from app.modules.start_simulation import start_simulation

    _run_action("Start Simulation", lambda: start_simulation(
        simulation_id=SIM_ID,
        admin_user_id=ADMIN_USER_ID,
        root_dir=ROOT_DIR,
    ))


def _action_stop() -> None:
    """Stop = set status to STOPPED (light-weight, CSV-only)."""
    sim_path = _sim_dir()
    csv_path = sim_path / "simulation.csv"
    df = _read_csv_safe(csv_path)
    if df is None or df.empty:
        append_system_message("Cannot stop: simulation.csv not found.", "error")
        return
    status_col = next(
        (c for c in df.columns if c.strip().lower() == "status"), None
    )
    if status_col is None:
        append_system_message("Cannot stop: no status column in simulation.csv.", "error")
        return
    current = normalize_status(df.iloc[0][status_col])
    if current != "STARTED":
        append_system_message(f"Simulation is not STARTED (current: {current}).", "warning")
        return
    df.at[0, status_col] = "STOPPED"
    upd_col = next((c for c in df.columns if c.strip().lower() == "updated_at_utc"), None)
    if upd_col:
        df.at[0, upd_col] = datetime.now(timezone.utc).isoformat()
    tmp = csv_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.rename(csv_path)
    append_system_message("Simulation **STOPPED**.", "success")


def _action_move_next_round() -> None:
    from app.modules.move_next_round import move_next_round

    _run_action("Move Next Round", lambda: move_next_round(
        simulation_id=SIM_ID,
        admin_user_id=ADMIN_USER_ID,
        root_dir=ROOT_DIR,
    ))


def _action_undo_round() -> None:
    from app.modules.undo_round import undo_round

    _run_action("Undo Round", lambda: undo_round(
        simulation_id=SIM_ID,
        admin_user_id=ADMIN_USER_ID,
        root_dir=ROOT_DIR,
    ))


def _action_end_simulation() -> None:
    from app.modules.end_simulation import end_simulation

    _run_action("End Simulation", lambda: end_simulation(
        simulation_id=SIM_ID,
        admin_user_id=ADMIN_USER_ID,
        root_dir=ROOT_DIR,
    ))


def _action_setup(
    name: str, total_rounds: int, team_names: list[str], overwrite: bool
) -> None:
    from app.modules.setup_simulation import setup_simulation

    _run_action("Setup Simulation", lambda: setup_simulation(
        simulation_id=SIM_ID,
        simulation_name=name,
        total_rounds=total_rounds,
        team_names=team_names,
        root_dir=ROOT_DIR,
        overwrite=overwrite,
    ))


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    _auto_refresh()

    # ── Logo ───────────────────────────────────────────────────────
    for logo_path in _LOGO_CANDIDATES:
        if logo_path.exists():
            st.image(str(logo_path), width=100)
            break

    # ── Title ──────────────────────────────────────────────────────
    st.title(PAGE_TITLE)
    st.caption("Admin Dashboard")

    sim_path = _sim_dir()

    # ── Status / Round / Total Rounds row ──────────────────────────
    status = _determine_status(sim_path)
    current_round, round_status, total_rounds = _current_round_info(sim_path)

    st.markdown("---")

    c_status, c_round, c_total = st.columns(3)
    with c_status:
        st.subheader("Status")
        st.markdown(_render_badge(status), unsafe_allow_html=True)
    with c_round:
        st.markdown(
            f"""<div class="round-card">
                <div class="label">Current Round</div>
                <div class="value">{current_round}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        round_state_text = (
            f"Round {current_round} is {round_status}"
            if current_round > 0 and round_status != "NONE"
            else "No active round"
        )
        st.markdown(
            f'<div class="round-state">{round_state_text}</div>',
            unsafe_allow_html=True,
        )
    with c_total:
        st.markdown(
            f"""<div class="round-card">
                <div class="label">Total Rounds</div>
                <div class="value">{total_rounds}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Action buttons ─────────────────────────────────────────────
    sim_is_completed = status in {"COMPLETED", "ENDED"}

    st.subheader("Actions")

    # Row 1: Setup, Start, Stop
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        with st.expander("Setup Simulation", expanded=False):
            with st.form("setup_form"):
                sim_name = st.text_input("Simulation Name", value="Airline Simulation")
                n_rounds = st.number_input("Total Rounds", min_value=1, value=3, step=1)
                raw_teams = st.text_input(
                    "Team Names (comma-separated)",
                    value="Airline A, Airline B, Airline C, Airline D, Airline E, Airline F",
                )
                overwrite = st.checkbox("Overwrite if exists", value=False)
                submitted = st.form_submit_button("Run Setup")
                if submitted:
                    teams = [t.strip() for t in raw_teams.split(",") if t.strip()]
                    _action_setup(sim_name, int(n_rounds), teams, overwrite)
    with r1c2:
        if st.button("\u25B6 Start Simulation", use_container_width=True,
                      disabled=sim_is_completed):
            _action_start()
    with r1c3:
        if st.button("\u23F9 Stop Simulation", use_container_width=True,
                      disabled=sim_is_completed):
            _action_stop()

    # Row 2: Undo Round, End Simulation
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        if st.button("\u21A9 Undo Round", use_container_width=True,
                      disabled=sim_is_completed):
            _action_undo_round()
    with r2c2:
        if st.button("\U0001F6D1 End Simulation", use_container_width=True,
                      disabled=sim_is_completed, type="primary"):
            _action_end_simulation()

    if sim_is_completed:
        st.warning(
            "Simulation is **COMPLETED**. Round-modifying actions are disabled. "
            "Use **Setup** with *Overwrite* to create a new simulation."
        )

    st.markdown("---")

    # ── System Messages area ───────────────────────────────────────
    # (messages are rendered inline above by _run_action / append_system_message)

    # ── Team Stats Table ───────────────────────────────────────────
    st.subheader("Team Stats")
    if status == "NOT_FOUND":
        st.warning(f"Simulation folder **{SIM_ID}** not found. Run **Setup** first.")
    else:
        table = _build_team_table(sim_path, current_round)
        if table.empty:
            st.info("No team data available yet.")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True)

    # ── Refresh button (above footer) ─────────────────────────────
    st.markdown("")
    if st.button("\U0001f504 Refresh", type="primary"):
        st.rerun()

    # ── Footer ─────────────────────────────────────────────────────
    st.markdown(f'<div class="footer">{COPYRIGHT}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
