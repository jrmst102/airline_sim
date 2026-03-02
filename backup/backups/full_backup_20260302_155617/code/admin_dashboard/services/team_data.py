"""
Team Data – reads team CSV data from Spaces for the admin dashboard.
=====================================================================
Uses ``round_results_team.csv`` as the canonical team-state file,
which contains per-round per-team financials (revenue, cost, profit,
market share, CSI, OEI, etc.).

Also reads ``simulation.csv`` for status metadata and ``teams.csv``
for team display names.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.data.csv_manager import csv_exists, load_csv, read_csv_rows


DEFAULT_SIM_ID = "sim_001"


def get_decision_status(simulation_id: str = DEFAULT_SIM_ID) -> dict:
    """Return per-team decision submission status for the current round.

    Only counts decisions that were **manually submitted** by a team user.
    Seeded baseline decisions (created during setup) are ignored — they
    have the same ``submitted_at_utc`` as the simulation's ``created_at_utc``.

    Returns a dict with:
      - ``current_round`` (int)
      - ``teams`` — dict mapping team_id → bool (True = submitted)
    """
    status = get_simulation_status(simulation_id)
    current_round = status["current_round"]

    # Get the simulation creation timestamp so we can filter out seeded defaults
    seed_timestamp = ""
    if csv_exists(simulation_id, "simulation.csv"):
        _, sim_rows = load_csv(simulation_id, "simulation.csv")
        if sim_rows:
            seed_timestamp = sim_rows[0].get("created_at_utc", "")

    # Read all active teams
    team_ids: list[str] = []
    if csv_exists(simulation_id, "teams.csv"):
        for row in read_csv_rows(simulation_id, "teams.csv"):
            if row.get("is_active", "0") == "1":
                team_ids.append(row.get("team_id", ""))

    # Read decisions for the current round — skip seeded defaults
    submitted: dict[str, bool] = {tid: False for tid in team_ids}
    if csv_exists(simulation_id, "decisions.csv") and current_round > 0:
        for row in read_csv_rows(simulation_id, "decisions.csv"):
            rn = 0
            try:
                rn = int(float(row.get("round_number", "0")))
            except (TypeError, ValueError):
                pass
            if rn == current_round:
                tid = row.get("team_id", "")
                sub_ts = row.get("submitted_at_utc", "")
                # Skip if this is a seeded baseline decision
                if seed_timestamp and sub_ts == seed_timestamp:
                    continue
                if tid in submitted:
                    submitted[tid] = True

    return {"current_round": current_round, "teams": submitted}


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


def get_simulation_status(simulation_id: str = DEFAULT_SIM_ID) -> dict:
    """Return a dict describing the current simulation state.

    Keys: ``status``, ``current_round``, ``total_rounds``, ``name``,
    ``updated_at_utc``.
    """
    if not csv_exists(simulation_id, "simulation.csv"):
        return {
            "status": "NOT FOUND",
            "current_round": 0,
            "total_rounds": 0,
            "name": "",
            "updated_at_utc": "",
        }

    _, rows = load_csv(simulation_id, "simulation.csv")
    if not rows:
        return {
            "status": "CORRUPT",
            "current_round": 0,
            "total_rounds": 0,
            "name": "",
            "updated_at_utc": "",
        }

    row = rows[0]
    return {
        "status": row.get("status", "UNKNOWN"),
        "current_round": _int(row.get("current_round", "0")),
        "total_rounds": _int(row.get("total_rounds", "0")),
        "name": row.get("name", ""),
        "updated_at_utc": row.get("updated_at_utc", ""),
    }


def get_team_table(simulation_id: str = DEFAULT_SIM_ID) -> dict:
    """Build the team-data table payload for the admin dashboard.

    Reads ``round_results_team.csv`` and filters to the latest round.
    Also enriches with team display names from ``teams.csv``.

    Returns a dict with keys:
        ``round`` (int), ``as_of`` (str), ``teams`` (list of row dicts).
    """
    # ── Team names lookup ──────────────────────────────────────────
    team_names: dict[str, str] = {}
    if csv_exists(simulation_id, "teams.csv"):
        for row in read_csv_rows(simulation_id, "teams.csv"):
            tid = row.get("team_id", "")
            name = row.get("team_name", f"Airline {tid}")
            team_names[tid] = name

    # ── Results data ───────────────────────────────────────────────
    if not csv_exists(simulation_id, "round_results_team.csv"):
        return {
            "round": 0,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "teams": [],
        }

    results = read_csv_rows(simulation_id, "round_results_team.csv")
    if not results:
        return {
            "round": 0,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "teams": [],
        }

    # Latest round
    max_round = max(_int(r.get("round_number", "0")) for r in results)
    latest = [r for r in results if _int(r.get("round_number", "0")) == max_round]

    teams: list[dict] = []
    for row in latest:
        tid = row.get("team_id", "")
        teams.append({
            "team_id": tid,
            "team_name": team_names.get(tid, f"Airline {tid}"),
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
            "price_business": _int(row.get("price_business", "0")),
            "price_leisure": _int(row.get("price_leisure", "0")),
            "csi": _int(row.get("csi", "0")),
            "oei": _int(row.get("oei", "0")),
        })

    # Compute market_share_revenue from raw revenue values
    total_revenue = sum(t["revenue"] for t in teams)
    for t in teams:
        t["market_share_revenue"] = (
            t["revenue"] / total_revenue if total_revenue > 0 else 0.0
        )

    # Sort by profit descending
    teams.sort(key=lambda t: t["profit"], reverse=True)

    return {
        "round": max_round,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "teams": teams,
    }


def get_team_history(simulation_id: str = DEFAULT_SIM_ID) -> dict:
    """Return per-round per-team metrics for all completed rounds.

    Returns a dict with:
      - ``rounds`` — sorted list of round numbers
      - ``teams``  — dict mapping team_id → {name, revenue[], profit[],
                     total_cost[], price_business[], price_leisure[]}
    """
    # Team names lookup
    team_names: dict[str, str] = {}
    if csv_exists(simulation_id, "teams.csv"):
        for row in read_csv_rows(simulation_id, "teams.csv"):
            tid = row.get("team_id", "")
            team_names[tid] = row.get("team_name", f"Airline {tid}")

    if not csv_exists(simulation_id, "round_results_team.csv"):
        return {"rounds": [], "teams": {}}

    results = read_csv_rows(simulation_id, "round_results_team.csv")
    if not results:
        return {"rounds": [], "teams": {}}

    # Collect all rounds and all team IDs
    round_set: set[int] = set()
    team_set: set[str] = set()
    for r in results:
        round_set.add(_int(r.get("round_number", "0")))
        team_set.add(r.get("team_id", ""))

    rounds_sorted = sorted(round_set)

    # Build per-team per-round lookup
    lookup: dict[tuple[str, int], dict] = {}
    for r in results:
        tid = r.get("team_id", "")
        rn = _int(r.get("round_number", "0"))
        lookup[(tid, rn)] = r

    teams: dict[str, dict] = {}
    for tid in sorted(team_set):
        teams[tid] = {
            "name": team_names.get(tid, f"Airline {tid}"),
            "revenue": [_float(lookup.get((tid, rn), {}).get("revenue", "0")) for rn in rounds_sorted],
            "profit": [_float(lookup.get((tid, rn), {}).get("profit", "0")) for rn in rounds_sorted],
            "total_cost": [_float(lookup.get((tid, rn), {}).get("total_cost", "0")) for rn in rounds_sorted],
            "price_business": [_int(lookup.get((tid, rn), {}).get("price_business", "0")) for rn in rounds_sorted],
            "price_leisure": [_int(lookup.get((tid, rn), {}).get("price_leisure", "0")) for rn in rounds_sorted],
        }

    return {"rounds": rounds_sorted, "teams": teams}


def get_report_data(simulation_id: str = DEFAULT_SIM_ID) -> dict:
    """Gather all data needed for the final simulation report.

    Returns a dict with:
      - ``simulation`` — simulation status metadata
      - ``final_results`` — latest-round team table (sorted by profit)
      - ``decisions_history`` — per-round per-team decisions
      - ``performance_history`` — per-round per-team results
      - ``rounds`` — sorted list of round numbers
      - ``team_names`` — dict mapping team_id → display name
    """
    sim_status = get_simulation_status(simulation_id)

    # Team names lookup
    team_names: dict[str, str] = {}
    if csv_exists(simulation_id, "teams.csv"):
        for row in read_csv_rows(simulation_id, "teams.csv"):
            tid = row.get("team_id", "")
            team_names[tid] = row.get("team_name", f"Airline {tid}")

    # Final results (latest round)
    final_results = get_team_table(simulation_id)

    # ── Decisions history ──────────────────────────────────────────
    decisions_by_round: dict[int, list[dict]] = {}
    if csv_exists(simulation_id, "decisions.csv"):
        for row in read_csv_rows(simulation_id, "decisions.csv"):
            rn = _int(row.get("round_number", "0"))
            tid = row.get("team_id", "")
            decisions_by_round.setdefault(rn, []).append({
                "team_id": tid,
                "team_name": team_names.get(tid, f"Airline {tid}"),
                "flights_per_day": _int(row.get("flights_per_day", "0")),
                "price_business": _float(row.get("price_business", "0")),
                "price_leisure": _float(row.get("price_leisure", "0")),
                "branding_level": row.get("branding_level", ""),
                "product_strategy": row.get("product_strategy", ""),
            })
    # Sort each round's decisions by team_id
    for rn in decisions_by_round:
        decisions_by_round[rn].sort(key=lambda d: d["team_id"])

    # ── Performance history ────────────────────────────────────────
    perf_by_round: dict[int, list[dict]] = {}
    if csv_exists(simulation_id, "round_results_team.csv"):
        for row in read_csv_rows(simulation_id, "round_results_team.csv"):
            rn = _int(row.get("round_number", "0"))
            tid = row.get("team_id", "")
            perf_by_round.setdefault(rn, []).append({
                "team_id": tid,
                "team_name": team_names.get(tid, f"Airline {tid}"),
                "passengers": _int(row.get("passengers", "0")),
                "revenue": _float(row.get("revenue", "0")),
                "total_cost": _float(row.get("total_cost", "0")),
                "profit": _float(row.get("profit", "0")),
                "market_share_volume": _float(row.get("market_share_volume", "0")),
                "load_factor": _float(row.get("load_factor", "0")),
                "csi": _int(row.get("csi", "0")),
                "oei": _int(row.get("oei", "0")),
            })
    for rn in perf_by_round:
        perf_by_round[rn].sort(key=lambda d: d["team_id"])

    all_rounds = sorted(set(list(decisions_by_round.keys()) + list(perf_by_round.keys())))

    return {
        "simulation": sim_status,
        "final_results": final_results,
        "decisions_history": decisions_by_round,
        "performance_history": perf_by_round,
        "rounds": all_rounds,
        "team_names": team_names,
    }
