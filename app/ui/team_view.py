"""
Airlines – Competitive Strategy Simulation · Team Dashboard
=============================================================
Single-page Streamlit team view for entering decisions and viewing results.

Run with:
    streamlit run app/ui/team_view.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so `from app.…` imports work
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
ROOT_DIR = Path("simulations")
ADMIN_USER_ID = "U_ADMIN"

TEAM_OPTIONS = ["A", "B", "C", "D", "E", "F"]
TEAM_LABELS = {t: f"Airline {t}" for t in TEAM_OPTIONS}

BRANDING_OPTIONS = ["Low", "Medium", "High"]
PRODUCT_OPTIONS = ["Premium Cabin", "Basic Economy", "Digital/Loyalty", "None"]

# Default prices – "Match" level from case appendix
DEFAULT_PRICE_BUSINESS = 360.0
DEFAULT_PRICE_LEISURE = 180.0

_LOGO_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "images" / "sim_logo.png",
    Path("./assets/logo.png"),
]


def _data_root() -> Path:
    return Path(os.environ.get("DATA_ROOT", "."))


def _sim_dir() -> Path:
    return _data_root() / "simulations" / SIM_ID


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
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return None


def normalize_status(value: str) -> str:
    s = str(value).strip().upper()
    mapping = {
        "RUNNING": "STARTED",
        "SETUP": "CREATED",
        "ARCHIVED": "COMPLETED",
        "ENDED": "COMPLETED",
    }
    return mapping.get(s, s)


def _determine_status(sim_path: Path) -> str:
    if not sim_path.exists():
        return "NOT_FOUND"
    sim_df = _read_csv_safe(sim_path / "simulation.csv")
    if sim_df is not None and not sim_df.empty:
        status_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "status"), None
        )
        if status_col is not None:
            return normalize_status(sim_df.iloc[-1][status_col])
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
            vals = pd.to_numeric(
                pd.Series([sim_df.iloc[-1][tr_col]]), errors="coerce"
            ).dropna()
            if not vals.empty:
                total_rounds = int(vals.iloc[0])

    # Prefer current_round from simulation.csv if available
    cr_from_sim: int | None = None
    if sim_df is not None and not sim_df.empty:
        cr_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "current_round"), None
        )
        if cr_col is not None:
            vals = pd.to_numeric(
                pd.Series([sim_df.iloc[-1][cr_col]]), errors="coerce"
            ).dropna()
            if not vals.empty:
                cr_from_sim = int(vals.iloc[0])

    rounds_df = _read_csv_safe(sim_path / "rounds.csv")
    if rounds_df is None or rounds_df.empty:
        return cr_from_sim or 0, "NONE", total_rounds

    rn_col = next(
        (c for c in rounds_df.columns if c.strip().lower() == "round_number"), None
    )
    st_col = next(
        (c for c in rounds_df.columns if c.strip().lower() == "status"), None
    )
    if rn_col is None:
        return cr_from_sim or 0, "NONE", total_rounds

    rounds_df = rounds_df.copy()
    rounds_df["_rn"] = pd.to_numeric(rounds_df[rn_col], errors="coerce")
    rounds_df = rounds_df.dropna(subset=["_rn"])
    if rounds_df.empty:
        return cr_from_sim or 0, "NONE", total_rounds

    # Find the OPEN round first; fall back to CLOSED with highest number;
    # only use PLANNED as last resort.
    if st_col is not None:
        open_rows = rounds_df[rounds_df[st_col].str.strip().str.upper() == "OPEN"]
        if not open_rows.empty:
            idx = open_rows["_rn"].idxmax()
            return int(open_rows.loc[idx, "_rn"]), "OPEN", total_rounds

        closed_rows = rounds_df[rounds_df[st_col].str.strip().str.upper() == "CLOSED"]
        if not closed_rows.empty:
            idx = closed_rows["_rn"].idxmax()
            return int(closed_rows.loc[idx, "_rn"]), "CLOSED", total_rounds

    # Fallback: use current_round from simulation.csv or max round_number
    if cr_from_sim is not None:
        match = rounds_df[rounds_df["_rn"] == cr_from_sim]
        if not match.empty:
            status = str(match.iloc[0][st_col]).strip().upper() if st_col else "NONE"
            return cr_from_sim, status, total_rounds

    idx = rounds_df["_rn"].idxmax()
    rn = int(rounds_df.loc[idx, "_rn"])
    status = str(rounds_df.loc[idx, st_col]).strip().upper() if st_col else "NONE"
    return rn, status, total_rounds


def _get_existing_decision(
    sim_path: Path, team_id: str, round_number: int
) -> dict[str, Any] | None:
    """Load the current decision for a team in a round, if it exists."""
    decisions_df = _read_csv_safe(sim_path / "decisions.csv")
    if decisions_df is None or decisions_df.empty:
        return None
    tid_col = next(
        (c for c in decisions_df.columns if c.strip().lower() == "team_id"), None
    )
    rn_col = next(
        (c for c in decisions_df.columns if c.strip().lower() == "round_number"), None
    )
    if tid_col is None or rn_col is None:
        return None
    match = decisions_df[
        (decisions_df[tid_col] == team_id)
        & (pd.to_numeric(decisions_df[rn_col], errors="coerce") == round_number)
    ]
    if match.empty:
        return None
    row = match.iloc[-1]
    return {
        "flights_per_day": int(float(row.get("flights_per_day", 3))),
        "price_business": float(row.get("price_business", DEFAULT_PRICE_BUSINESS)),
        "price_leisure": float(row.get("price_leisure", DEFAULT_PRICE_LEISURE)),
        "branding_level": str(row.get("branding_level", "Medium")),
        "product_strategy": str(row.get("product_strategy", "None")),
    }


def _get_all_decisions_for_round(
    sim_path: Path, round_number: int
) -> pd.DataFrame | None:
    """Load all team decisions submitted for a given round."""
    decisions_df = _read_csv_safe(sim_path / "decisions.csv")
    if decisions_df is None or decisions_df.empty:
        return None
    rn_col = next(
        (c for c in decisions_df.columns if c.strip().lower() == "round_number"), None
    )
    if rn_col is None:
        return None
    match = decisions_df[
        pd.to_numeric(decisions_df[rn_col], errors="coerce") == round_number
    ]
    return match if not match.empty else None


# ---------------------------------------------------------------------------
# Team stats table (matching admin/dashboard style)
# ---------------------------------------------------------------------------
def _build_team_table(sim_path: Path, latest_round: int) -> pd.DataFrame:
    """Build a display-ready team stats table."""
    results_df = _read_csv_safe(sim_path / "round_results_team.csv")
    teams_df = _read_csv_safe(sim_path / "teams.csv")

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

    if results_df is not None and not results_df.empty:
        rn_col = next(
            (c for c in results_df.columns if c.strip().lower() == "round_number"), None
        )
        if rn_col:
            filtered = results_df[
                pd.to_numeric(results_df[rn_col], errors="coerce") == latest_round
            ]
            if not filtered.empty:
                results_df = filtered
            else:
                fallback = results_df[
                    pd.to_numeric(results_df[rn_col], errors="coerce") == 0
                ]
                if not fallback.empty:
                    results_df = fallback.copy()
                    results_df[rn_col] = str(latest_round)

        # Merge team names
        if (
            teams_df is not None
            and "team_id" in results_df.columns
            and "team_id" in teams_df.columns
        ):
            merge_cols = ["team_id"]
            if "team_name" not in results_df.columns and "team_name" in teams_df.columns:
                merge_cols.append("team_name")
            if len(merge_cols) > 1:
                results_df = results_df.merge(
                    teams_df[merge_cols].drop_duplicates(),
                    on="team_id", how="left",
                )

        out: dict[str, str] = {}
        for src, dst in desired.items():
            m = next((c for c in results_df.columns if c.strip().lower() == src), None)
            if m is not None:
                out[m] = dst
        table = results_df[list(out.keys())].rename(columns=out) if out else results_df.copy()

        # Sort by profit descending (before formatting)
        if "Profit" in table.columns:
            table["_sort"] = pd.to_numeric(table["Profit"], errors="coerce")
            table = table.sort_values("_sort", ascending=False).drop(columns=["_sort"])

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
    st.caption("Team Dashboard")

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

    # ── Team selector ──────────────────────────────────────────────
    selected_team = st.selectbox(
        "Select Your Team",
        options=TEAM_OPTIONS,
        format_func=lambda t: TEAM_LABELS[t],
        index=0,
        key="team_selector",
    )

    st.markdown("---")

    # ── Enter / Update Decision ────────────────────────────────────
    st.subheader(f"Enter Decision \u2014 {TEAM_LABELS[selected_team]}")

    can_enter = status == "STARTED" and round_status == "OPEN"

    if not can_enter:
        st.warning(
            "Decisions can only be entered when the simulation is **STARTED** "
            "and a round is **OPEN**."
        )

    # Load existing decision to pre-populate form
    existing = _get_existing_decision(sim_path, selected_team, current_round) if can_enter else None
    defaults = existing or {
        "flights_per_day": 3,
        "price_business": DEFAULT_PRICE_BUSINESS,
        "price_leisure": DEFAULT_PRICE_LEISURE,
        "branding_level": "Medium",
        "product_strategy": "None",
    }

    if existing:
        st.info(
            f"Decision already submitted for Round {current_round}. "
            "You can update it below."
        )

    with st.form("decision_form"):
        flights_per_day = st.number_input(
            "Flights per Day (0\u20135)",
            min_value=0, max_value=5,
            value=defaults["flights_per_day"],
            step=1,
        )
        price_col1, price_col2 = st.columns(2)
        with price_col1:
            price_business = st.number_input(
                "Business Seat Price ($)",
                min_value=50.0, max_value=1000.0,
                value=float(defaults["price_business"]),
                step=10.0,
                format="%.0f",
                help="Reference: Premium $450 · Match $360 · Discount $290",
            )
        with price_col2:
            price_leisure = st.number_input(
                "Leisure Seat Price ($)",
                min_value=50.0, max_value=1000.0,
                value=float(defaults["price_leisure"]),
                step=10.0,
                format="%.0f",
                help="Reference: Premium $220 · Match $180 · Discount $140",
            )
        branding_level = st.selectbox(
            "Branding Level",
            options=BRANDING_OPTIONS,
            index=BRANDING_OPTIONS.index(defaults["branding_level"]),
        )
        product_strategy = st.selectbox(
            "Product Strategy",
            options=PRODUCT_OPTIONS,
            index=PRODUCT_OPTIONS.index(defaults["product_strategy"]),
        )

        save_col, move_col = st.columns(2)
        with save_col:
            save_clicked = st.form_submit_button(
                "\U0001F4BE Save Decision",
                use_container_width=True,
                disabled=not can_enter,
            )
        with move_col:
            move_clicked = st.form_submit_button(
                "\u23E9 Move to Next Round",
                use_container_width=True,
                disabled=not can_enter,
            )

    # ── Handle Save Decision ──────────────────────────────────────
    if save_clicked and can_enter:
        try:
            from app.modules.enter_decisions import enter_decision

            result = enter_decision(
                simulation_id=SIM_ID,
                team_id=selected_team,
                flights_per_day=int(flights_per_day),
                price_business=float(price_business),
                price_leisure=float(price_leisure),
                branding_level=branding_level,
                product_strategy=product_strategy,
                round_number=current_round,
                root_dir=ROOT_DIR,
            )
            action = "updated" if result.was_update else "saved"
            st.success(
                f"Decision **{action}** for {TEAM_LABELS[selected_team]}, "
                f"Round {result.round_number}."
            )
        except Exception as exc:
            st.error(f"Save failed: {exc}")

    # ── Handle Move to Next Round ─────────────────────────────────
    if move_clicked and can_enter:
        # First, save the current decision so data isn't lost
        try:
            from app.modules.enter_decisions import enter_decision

            enter_decision(
                simulation_id=SIM_ID,
                team_id=selected_team,
                flights_per_day=int(flights_per_day),
                price_business=float(price_business),
                price_leisure=float(price_leisure),
                branding_level=branding_level,
                product_strategy=product_strategy,
                round_number=current_round,
                root_dir=ROOT_DIR,
            )
        except Exception as exc:
            st.error(f"Failed to save decision before advancing: {exc}")

        # Then advance the round
        try:
            from app.modules.move_next_round import move_next_round

            mnr_result = move_next_round(
                simulation_id=SIM_ID,
                admin_user_id=ADMIN_USER_ID,
                root_dir=ROOT_DIR,
            )
            if mnr_result.opened_round is not None:
                st.success(
                    f"Round {mnr_result.closed_round} closed. "
                    f"Round {mnr_result.opened_round} is now open."
                )
            else:
                st.success(
                    f"Round {mnr_result.closed_round} closed. "
                    f"Simulation is now **{mnr_result.simulation_status}**."
                )
            st.rerun()
        except Exception as exc:
            st.error(f"Move to next round failed: {exc}")

    st.markdown("---")

    # ── Decisions submitted this round ─────────────────────────────
    if current_round > 0:
        st.subheader(f"Decisions Submitted \u2014 Round {current_round}")
        round_decisions = _get_all_decisions_for_round(sim_path, current_round)
        if round_decisions is not None:
            teams_df = _read_csv_safe(sim_path / "teams.csv")
            display_df = round_decisions.copy()

            # Merge team names
            if teams_df is not None and "team_id" in display_df.columns and "team_id" in teams_df.columns:
                if "team_name" in teams_df.columns:
                    display_df = display_df.merge(
                        teams_df[["team_id", "team_name"]].drop_duplicates(),
                        on="team_id", how="left",
                    )

            show_cols = []
            for c in ["team_name", "team_id", "flights_per_day", "price_business",
                       "price_leisure", "branding_level", "product_strategy", "submitted_at_utc"]:
                m = next((col for col in display_df.columns if col.strip().lower() == c), None)
                if m is not None:
                    show_cols.append(m)

            if show_cols:
                rename_map = {
                    "team_name": "Team",
                    "team_id": "ID",
                    "flights_per_day": "Flights/Day",
                    "price_business": "Biz Price",
                    "price_leisure": "Lei Price",
                    "branding_level": "Branding",
                    "product_strategy": "Product",
                    "submitted_at_utc": "Submitted",
                }
                tbl = display_df[show_cols].rename(columns=rename_map)
                st.dataframe(tbl, use_container_width=True, hide_index=True)
            else:
                st.dataframe(display_df, use_container_width=True, hide_index=True)

            submitted_teams = set(round_decisions["team_id"].unique()) if "team_id" in round_decisions.columns else set()
            missing = [t for t in TEAM_OPTIONS if t not in submitted_teams]
            if missing:
                st.warning(f"Awaiting decisions from: {', '.join(TEAM_LABELS[t] for t in missing)}")
            else:
                st.success("All teams have submitted decisions.")
        else:
            st.info("No decisions submitted yet for this round.")

    st.markdown("---")

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

    # ── Refresh button ─────────────────────────────────────────────
    st.markdown("")
    if st.button("\U0001f504 Refresh", type="primary"):
        st.rerun()

    # ── Footer ─────────────────────────────────────────────────────
    st.markdown(f'<div class="footer">{COPYRIGHT}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
