"""
Airlines – Competitive Strategy Simulation Dashboard
=====================================================
A single-page Streamlit dashboard that reads simulation state from local CSV
files and displays simulation status, current round, and per-team stats.

Run with:
    streamlit run app/ui/dashboard.py
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AUTO_REFRESH_SECONDS = 60
PAGE_TITLE = "Airlines - Competitive Strategy Simulation"
COPYRIGHT = "Copyright 2026 by Dr. Jose Mendoza"

# Logo lives alongside other images shipped with the app.  Fall back to the
# spec-expected ./assets/logo.png path when the image isn't found there.
_LOGO_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "images" / "sim_logo.png",
    Path("./assets/logo.png"),
]


def _data_root() -> Path:
    """Return the data root directory, respecting the DATA_ROOT env var."""
    return Path(os.environ.get("DATA_ROOT", "."))


def _sim_dir(sim_id: str) -> Path:
    """Return the directory for a given simulation ID."""
    return _data_root() / "simulations" / sim_id


# ---------------------------------------------------------------------------
# CSS – hide sidebar, centre content, colour badges
# ---------------------------------------------------------------------------
_CUSTOM_CSS = """
<style>
/* ── Hide Streamlit sidebar & hamburger ────────────────────────── */
section[data-testid="stSidebar"]  { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

/* ── Centered, readable layout ─────────────────────────────────── */
.main .block-container {
    max-width: 860px !important;
    padding-top: 16px !important;
    padding-bottom: 16px !important;
}

/* ── Status badge ──────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.5px;
}
.badge-started  { background: #16a34a; color: #fff; }
.badge-created  { background: #6b7280; color: #fff; }
.badge-stopped  { background: #dc2626; color: #fff; }
.badge-notfound { background: #f97316; color: #fff; }

/* ── Round card ────────────────────────────────────────────────── */
.round-card {
    text-align: center;
    padding: 12px;
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 12px;
    background: rgba(255,255,255,0.03);
}
.round-card .label { font-size: 0.85rem; color: #9ca3af; margin-bottom: 2px; }
.round-card .value { font-size: 2.2rem; font-weight: 800; color: #2563eb; }

/* ── Footer ────────────────────────────────────────────────────── */
.footer {
    margin-top: 24px;
    padding-top: 10px;
    border-top: 1px solid rgba(128,128,128,0.2);
    text-align: center;
    color: #9ca3af;
    font-size: 0.85rem;
}
</style>
"""


# ---------------------------------------------------------------------------
# Auto-refresh (pure HTML meta-refresh – no extra dependency)
# ---------------------------------------------------------------------------
def _auto_refresh() -> None:
    st.markdown(
        f"<meta http-equiv='refresh' content='{AUTO_REFRESH_SECONDS}'>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# CSV helpers – robust reads that never crash
# ---------------------------------------------------------------------------
def _read_csv_safe(path: Path) -> pd.DataFrame | None:
    """Read a CSV file and return a DataFrame, or None on any error."""
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return None


def _determine_status(sim_path: Path) -> str:
    """Return one of CREATED, STARTED, STOPPED, NOT_FOUND."""
    if not sim_path.exists():
        return "NOT_FOUND"

    sim_df = _read_csv_safe(sim_path / "simulation.csv")
    if sim_df is not None and not sim_df.empty:
        # Look for an explicit status column
        status_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "status"), None
        )
        if status_col is not None:
            raw = str(sim_df.iloc[-1][status_col]).strip().upper()
            if raw in {"STARTED", "RUNNING"}:
                return "STARTED"
            if raw in {"STOPPED", "COMPLETED", "ARCHIVED", "ENDED"}:
                return "STOPPED"
            if raw in {"CREATED", "SETUP"}:
                return "CREATED"

    # Fallback – infer from rounds.csv
    rounds_df = _read_csv_safe(sim_path / "rounds.csv")
    if rounds_df is not None and not rounds_df.empty:
        status_col = next(
            (c for c in rounds_df.columns if c.strip().lower() == "status"), None
        )
        if status_col is not None:
            opened = rounds_df[
                rounds_df[status_col].str.strip().str.upper().isin({"OPEN", "CLOSED"})
            ]
            if not opened.empty:
                return "STARTED"

    return "CREATED"


def _current_round(sim_path: Path) -> int:
    """Return the latest round number, or 0 if unavailable."""
    # Prefer simulation.csv current_round field
    sim_df = _read_csv_safe(sim_path / "simulation.csv")
    if sim_df is not None and not sim_df.empty:
        cr_col = next(
            (c for c in sim_df.columns if c.strip().lower() == "current_round"), None
        )
        if cr_col is not None:
            val = pd.to_numeric(
                pd.Series([sim_df.iloc[-1][cr_col]]), errors="coerce"
            ).dropna()
            if not val.empty:
                return int(val.iloc[0])

    # Fallback – max round_number in rounds.csv
    rounds_df = _read_csv_safe(sim_path / "rounds.csv")
    if rounds_df is None or rounds_df.empty:
        return 0

    rn_col = next(
        (c for c in rounds_df.columns if c.strip().lower() == "round_number"), None
    )
    if rn_col is None:
        return 0

    vals = pd.to_numeric(rounds_df[rn_col], errors="coerce").dropna()
    return int(vals.max()) if not vals.empty else 0


def _fill_baseline_estimates(df: pd.DataFrame) -> None:
    """Fill empty revenue/total_cost cells with estimates for round-0 baselines.

    revenue  ≈ passengers × $250 (avg fare midpoint)
    cost     ≈ revenue − profit
    """
    if df is None or df.empty:
        return
    AVG_FARE = 250
    pax = pd.to_numeric(df.get("passengers"), errors="coerce")
    profit = pd.to_numeric(df.get("profit"), errors="coerce")
    rev = pd.to_numeric(df.get("revenue"), errors="coerce")
    cost = pd.to_numeric(df.get("total_cost"), errors="coerce")

    rev_missing = rev.isna() & pax.notna()
    if rev_missing.any():
        est_rev = pax * AVG_FARE
        df.loc[rev_missing, "revenue"] = est_rev[rev_missing].astype(int).astype(str)
        if profit is not None:
            cost_missing = cost.isna() & profit.notna()
            if cost_missing.any():
                est_cost = est_rev - profit
                df.loc[cost_missing, "total_cost"] = est_cost[cost_missing].astype(int).astype(str)


def _build_team_table(sim_path: Path, latest_round: int) -> pd.DataFrame:
    """
    Build a display-ready team stats DataFrame.

    Prefers round_results_team.csv filtered to *latest_round*.
    Falls back to teams.csv with baseline estimates.
    """
    teams_df = _read_csv_safe(sim_path / "teams.csv")
    results_df = _read_csv_safe(sim_path / "round_results_team.csv")

    # Column name mappings (source -> display)
    desired_cols = {
        "team_name": "Team Name",
        "team_id": "Team ID",
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
        # Filter to the latest round if possible
        rn_col = next(
            (c for c in results_df.columns if c.strip().lower() == "round_number"),
            None,
        )
        used_fallback_round = False
        if rn_col and latest_round > 0:
            filtered = results_df[
                pd.to_numeric(results_df[rn_col], errors="coerce") == latest_round
            ]
            if not filtered.empty:
                results_df = filtered
            else:
                # No computed results for this round yet — show baseline (round 0)
                # but display the current round number
                fallback = results_df[
                    pd.to_numeric(results_df[rn_col], errors="coerce") == 0
                ]
                if not fallback.empty:
                    results_df = fallback.copy()
                    results_df[rn_col] = str(latest_round)
                    used_fallback_round = True
        elif rn_col and latest_round == 0:
            # Show round-0 baseline rows
            filtered = results_df[
                pd.to_numeric(results_df[rn_col], errors="coerce") == 0
            ]
            if not filtered.empty:
                results_df = filtered

        # Merge team names from teams.csv if the column isn't already present
        if (
            teams_df is not None
            and "team_id" in results_df.columns
            and "team_id" in teams_df.columns
        ):
            merge_cols = ["team_id"]
            if "team_name" not in results_df.columns and "team_name" in teams_df.columns:
                merge_cols.append("team_name")
            if "variable_cost_per_passenger" in teams_df.columns:
                merge_cols.append("variable_cost_per_passenger")
            if len(merge_cols) > 1:
                results_df = results_df.merge(
                    teams_df[merge_cols].drop_duplicates(),
                    on="team_id",
                    how="left",
                )

        # Fill empty revenue / cost from baseline estimates (round 0)
        _fill_baseline_estimates(results_df)

        # Select & rename columns that exist
        out_cols: dict[str, str] = {}
        for src, dst in desired_cols.items():
            match = next(
                (c for c in results_df.columns if c.strip().lower() == src), None
            )
            if match is not None:
                out_cols[match] = dst

        if out_cols:
            table = results_df[list(out_cols.keys())].rename(columns=out_cols)
        else:
            table = results_df.copy()

        # Sort by Profit desc if available (BEFORE formatting)
        if "Profit" in table.columns:
            table["_sort"] = pd.to_numeric(table["Profit"], errors="coerce")
            table = table.sort_values("_sort", ascending=False).drop(columns=["_sort"])
        elif "Team Name" in table.columns:
            table = table.sort_values("Team Name")

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

    # Fallback: teams only, no results yet — compute estimates from teams.csv
    if teams_df is not None and not teams_df.empty:
        import math
        SEATS_PER_FLIGHT      = 200
        DAYS_PER_MONTH        = 30
        FIXED_COST_PER_FLIGHT = 18_000

        cols: dict[str, object] = {}

        for src, dst in [("team_name", "Team Name"), ("team_id", "Team ID")]:
            m = next((c for c in teams_df.columns if c.strip().lower() == src), None)
            if m:
                cols[dst] = teams_df[m]

        cols["Round"] = "\u2014"

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

        var_cost   = pax_n * vcpp_n
        fix_cost   = monthly_flights * FIXED_COST_PER_FLIGHT
        brand_cost = BASELINE_BRANDING_COST
        prod_cost  = BASELINE_PRODUCT_COST
        total_cost = var_cost + fix_cost + brand_cost + prod_cost
        revenue    = profit_n + total_cost   # derive so profit stays consistent
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

    # Hard-coded single simulation
    sim_id = "sim_001"
    sim_path = _sim_dir(sim_id)

    # ── Status & Round ─────────────────────────────────────────────
    status = _determine_status(sim_path)
    latest_round = _current_round(sim_path)

    st.markdown("---")

    col_status, col_round = st.columns(2)
    with col_status:
        st.subheader("Simulation Status")
        st.markdown(_render_badge(status), unsafe_allow_html=True)
    with col_round:
        st.markdown(
            f"""
            <div class="round-card">
                <div class="label">Current Round</div>
                <div class="value">{latest_round}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Team Stats Table ───────────────────────────────────────────
    st.subheader("Team Stats")

    if status == "NOT_FOUND":
        st.warning(
            f"Simulation folder **{sim_id}** not found under "
            f'`{_data_root() / "simulations"}`.'
        )
    else:
        table = _build_team_table(sim_path, latest_round)
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
