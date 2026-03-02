"""
Team Performance – read round_results_team.csv for a single team.
================================================================
Provides the latest-round snapshot and full round history for
display in the team dashboard.
"""

from __future__ import annotations

import logging

from app.data.csv_manager import csv_exists, read_csv_rows

logger = logging.getLogger(__name__)

DEFAULT_SIM_ID = "sim_001"


def _int(v: str, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_result_row(row: dict) -> dict:
    """Normalise a raw CSV row into typed values."""
    return {
        "round_number": _int(row.get("round_number", "0")),
        "passengers": _int(row.get("passengers", "0")),
        "revenue": _float(row.get("revenue", "0")),
        "variable_cost": _float(row.get("variable_cost", "0")),
        "fixed_cost": _float(row.get("fixed_cost", "0")),
        "branding_cost": _float(row.get("branding_cost", "0")),
        "product_cost": _float(row.get("product_cost", "0")),
        "total_cost": _float(row.get("total_cost", "0")),
        "profit": _float(row.get("profit", "0")),
        "market_share_volume": _float(row.get("market_share_volume", "0")),
        "market_share_profit": _float(row.get("market_share_profit", "0")),
        "load_factor": _float(row.get("load_factor", "0")),
        "avg_revenue_per_flight": _float(row.get("avg_revenue_per_flight", "0")),
        "avg_cost_per_flight": _float(row.get("avg_cost_per_flight", "0")),
        "avg_profit_per_flight": _float(row.get("avg_profit_per_flight", "0")),
        "price_business": _float(row.get("price_business", "0")),
        "price_leisure": _float(row.get("price_leisure", "0")),
        "csi": _float(row.get("csi", "0")),
        "oei": _float(row.get("oei", "0")),
    }


def get_team_performance(
    simulation_id: str,
    team_id: str,
) -> dict:
    """Return the team's performance data.

    Returns a dict with:
      - ``has_data`` (bool)
      - ``latest`` (dict | None): most recent completed-round results
      - ``history`` (list[dict]): all completed-round results ascending
    """
    if not csv_exists(simulation_id, "round_results_team.csv"):
        return {"has_data": False, "latest": None, "history": []}

    rows = read_csv_rows(simulation_id, "round_results_team.csv")
    team_rows = [r for r in rows if r.get("team_id") == team_id]

    if not team_rows:
        return {"has_data": False, "latest": None, "history": []}

    parsed = sorted(
        [_parse_result_row(r) for r in team_rows],
        key=lambda d: d["round_number"],
    )

    return {
        "has_data": True,
        "latest": parsed[-1],
        "history": parsed,
    }


def get_team_name(simulation_id: str, team_id: str) -> str:
    """Return the team display name, or the team_id as fallback."""
    if not csv_exists(simulation_id, "teams.csv"):
        return team_id
    rows = read_csv_rows(simulation_id, "teams.csv")
    for row in rows:
        if row.get("team_id") == team_id:
            return row.get("team_name", team_id)
    return team_id
