"""
Dashboard Data – reads CSV files and computes dashboard payload.
=================================================================
Pure data module with no web framework dependency.
Reads ``round_results_team.csv``, identifies the latest round,
computes market-share rankings, and returns a dict ready for JSON.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.data.csv_manager import csv_exists, read_csv_rows


# Default simulation ID
DEFAULT_SIM_ID = "sim_001"
# Keep legacy constant for backward compat
DEFAULT_SIM_PATH = Path("simulation/simulations/sim_001")


def _float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int(v: str, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def get_dashboard_data(sim_path: Path = DEFAULT_SIM_PATH) -> dict:
    """Build the full dashboard payload from CSV files.

    Returns a dict with keys:
        round, as_of, profit_ranking, volume_ranking, table
    """
    # Derive simulation_id from sim_path (e.g. simulation/simulations/sim_001 -> sim_001)
    simulation_id = sim_path.name if sim_path != DEFAULT_SIM_PATH else DEFAULT_SIM_ID

    if not csv_exists(simulation_id, "round_results_team.csv"):
        return {
            "round": 0,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "profit_ranking": [],
            "volume_ranking": [],
            "table": [],
        }

    rows = read_csv_rows(simulation_id, "round_results_team.csv")
    if not rows:
        return {
            "round": 0,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "profit_ranking": [],
            "volume_ranking": [],
            "table": [],
        }

    # ── Identify latest round ──────────────────────────────────────
    max_round = max(_int(r.get("round_number", "0")) for r in rows)

    # ── Filter to latest round ─────────────────────────────────────
    latest = [r for r in rows if _int(r.get("round_number", "0")) == max_round]

    # ── Extract team data ──────────────────────────────────────────
    teams: list[dict] = []
    for row in latest:
        teams.append({
            "team_id": row.get("team_id", ""),
            "passengers": _int(row.get("passengers", "0")),
            "profit": _float(row.get("profit", "0")),
            "revenue": _float(row.get("revenue", "0")),
            "total_cost": _float(row.get("total_cost", "0")),
            "csi": _int(row.get("csi", "0")),
            "oei": _int(row.get("oei", "0")),
        })

    # ── Compute market shares server-side ──────────────────────────
    total_passengers = sum(t["passengers"] for t in teams)
    total_positive_profit = sum(max(t["profit"], 0.0) for t in teams)

    for t in teams:
        # Volume share
        if total_passengers > 0:
            t["market_share_volume"] = t["passengers"] / total_passengers
        else:
            t["market_share_volume"] = 0.0

        # Profit share
        if total_positive_profit > 0:
            t["market_share_profit"] = max(t["profit"], 0.0) / total_positive_profit
        else:
            t["market_share_profit"] = 0.0

    # ── Profit ranking (descending by profit) ──────────────────────
    profit_sorted = sorted(teams, key=lambda t: t["profit"], reverse=True)
    profit_ranking = [
        {
            "team": f"Airline {t['team_id']}",
            "value": round(t["market_share_profit"] * 100, 1),
        }
        for t in profit_sorted
    ]

    # ── Volume ranking (descending by volume share) ────────────────
    volume_sorted = sorted(teams, key=lambda t: t["market_share_volume"], reverse=True)
    volume_ranking = [
        {
            "team": f"Airline {t['team_id']}",
            "value": round(t["market_share_volume"] * 100, 1),
        }
        for t in volume_sorted
    ]

    # ── Table data (sorted descending by profit) ───────────────────
    table_sorted = sorted(teams, key=lambda t: t["profit"], reverse=True)
    table = []
    for rank, t in enumerate(table_sorted, 1):
        table.append({
            "rank": rank,
            "team": f"Airline {t['team_id']}",
            "profit": f"${t['profit']:,.0f}",
            "market_share_profit": f"{t['market_share_profit'] * 100:.1f}%",
            "market_share_volume": f"{t['market_share_volume'] * 100:.1f}%",
            "passengers": f"{t['passengers']:,}",
            "csi": t["csi"],
            "oei": t["oei"],
        })

    return {
        "round": max_round,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "profit_ranking": profit_ranking,
        "volume_ranking": volume_ranking,
        "table": table,
    }
