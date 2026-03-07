"""
Independent Calculator – from-scratch formula reimplementation.
================================================================
Reimplements *every* simulation formula (capacity, demand allocation,
revenue, cost, profit, market shares, per-flight metrics) **without**
importing anything from ``app.core.simulation_engine``.

The purpose is to catch formula-level bugs in the engine: if the engine
miscalculates revenue, cost, or demand, the engine-based expected
calculator would produce the *same* wrong answer.  This module uses only
raw CSV reads and plain arithmetic.

Formulas come from the Case Appendix:
  "Airlines Competitive Game – Turbulence at 30,000 Feet:
   Competition on the JFK–Boston Corridor" (Spring 2026)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Result data structures  (mirror expected_calculator.py for easy diffing)
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(value: float, decimals: int) -> str:
    """Format float to fixed decimal places – mirrors move_next_round."""
    return f"{value:.{decimals}f}"


@dataclass
class IndependentTeamResult:
    """One team's independently-computed results (formatted strings)."""
    team_id: str
    passengers: int
    revenue: str
    variable_cost: str
    fixed_cost: str
    branding_cost: str
    product_cost: str
    total_cost: str
    profit: str
    market_share_volume: str
    market_share_profit: str
    load_factor: str
    avg_revenue_per_flight: str
    avg_cost_per_flight: str
    avg_profit_per_flight: str
    price_business: str
    price_leisure: str


@dataclass
class IndependentMarketResult:
    total_demand: int
    total_passengers: int
    total_revenue: str
    total_cost: str
    total_profit: str


@dataclass
class IndependentResults:
    team_results: dict[str, IndependentTeamResult] = field(default_factory=dict)
    market_result: IndependentMarketResult | None = None


# ═══════════════════════════════════════════════════════════════════════════
# Raw CSV helpers – NO imports from app.*
# ═══════════════════════════════════════════════════════════════════════════

def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_key_value_csv(path: Path) -> dict[str, str]:
    """Load a key-value CSV (columns: key, value, [notes])."""
    rows = _load_csv_rows(path)
    return {r["key"]: r["value"] for r in rows}


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


# ═══════════════════════════════════════════════════════════════════════════
# Independent computation – implements every formula from scratch
# ═══════════════════════════════════════════════════════════════════════════

def compute_independent(
    sim_path: Path,
    round_number: int,
) -> IndependentResults:
    """Compute round results from raw CSV data using plain arithmetic.

    This function does NOT call ``compute_round_results`` or import
    any module from ``app.core``.  It reads parameters.csv, teams.csv,
    and decisions.csv directly and applies the Case Appendix formulas.

    Parameters
    ----------
    sim_path : Path
        Path to the simulation folder (e.g. ``simulation/simulations/sim_001``).
    round_number : int
        Which round to compute results for.

    Returns
    -------
    IndependentResults
        Formatted strings identical to what ``move_next_round`` writes,
        so comparison with CSV actuals is a straight ``==``.
    """

    # ── 1. Read parameters.csv ─────────────────────────────────────
    params = _load_key_value_csv(sim_path / "parameters.csv")

    total_demand_passengers = _int(params["total_demand_passengers"])
    business_demand         = _int(params["business_demand"])
    leisure_demand          = _int(params["leisure_demand"])
    seats_per_flight        = _int(params["seats_per_flight"])
    fixed_cost_per_flight   = _int(params["fixed_cost_per_flight"])
    days_per_month          = _int(params["days_per_month"])
    fare_multiplier         = _float(params["fare_multiplier"])

    branding_costs = {
        "Low":    _int(params["branding_cost_low"]),
        "Medium": _int(params["branding_cost_medium"]),
        "High":   _int(params["branding_cost_high"]),
    }
    product_costs = {
        "High":   _int(params["product_cost_high"]),
        "Medium": _int(params["product_cost_medium"]),
        "Low":    _int(params["product_cost_low"]),
    }

    # ── 2. Read teams.csv → variable_cost_per_passenger ────────────
    team_rows = _load_csv_rows(sim_path / "teams.csv")
    var_cost_map: dict[str, float] = {}
    for row in team_rows:
        if row.get("is_active", "0") == "1":
            var_cost_map[row["team_id"]] = _float(
                row.get("variable_cost_per_passenger", "0")
            )

    # ── 3. Read decisions.csv for the target round ─────────────────
    all_decisions = _load_csv_rows(sim_path / "decisions.csv")
    round_decisions = [
        r for r in all_decisions
        if _int(r.get("round_number", "0")) == round_number
    ]

    if not round_decisions:
        raise ValueError(
            f"No decisions found for round {round_number} in {sim_path}"
        )

    # ── 4. Parse decision fields ───────────────────────────────────
    @dataclass
    class _Dec:
        team_id: str
        flights_per_day: int
        price_business: float
        price_leisure: float
        branding_level: str
        product_strategy: str
        variable_cost_per_passenger: float

    decisions: list[_Dec] = []
    for row in round_decisions:
        tid = row.get("team_id", "")
        decisions.append(_Dec(
            team_id=tid,
            flights_per_day=_int(row.get("flights_per_day", "0")),
            price_business=_float(row.get("price_business", "360")),
            price_leisure=_float(row.get("price_leisure", "180")),
            branding_level=row.get("branding_level", "Low"),
            product_strategy=row.get("product_strategy", "None"),
            variable_cost_per_passenger=var_cost_map.get(tid, 0.0),
        ))

    n_teams = len(decisions)

    # ══════════════════════════════════════════════════════════════
    # FORMULAS – reimplemented from the Case Appendix
    # ══════════════════════════════════════════════════════════════

    # ── 5. Capacity (Case Appendix §Capacity) ─────────────────────
    #   monthly_flights = flights_per_day × days_per_month
    #   capacity        = monthly_flights × seats_per_flight
    monthly_flights: dict[str, int] = {}
    capacity: dict[str, int] = {}
    for d in decisions:
        mf = d.flights_per_day * days_per_month
        monthly_flights[d.team_id] = mf
        capacity[d.team_id] = mf * seats_per_flight

    # ── 6. Demand allocation (Case Appendix §Demand) ──────────────
    #   Score-based proportional allocation:
    #     score_i = capacity_i / fare_i   (higher cap + lower fare → more demand)
    #   Business passengers allocated first, capped at capacity.
    #   Leisure passengers fill remaining capacity.

    # 6a. Business segment
    biz_score: dict[str, float] = {}
    for d in decisions:
        cap = capacity[d.team_id]
        biz_score[d.team_id] = (cap / d.price_business) if cap > 0 else 0.0

    total_biz_score = sum(biz_score.values())

    biz_pax: dict[str, int] = {}
    for d in decisions:
        cap = capacity[d.team_id]
        if total_biz_score > 0 and cap > 0:
            raw_demand = business_demand * (biz_score[d.team_id] / total_biz_score)
        else:
            raw_demand = 0.0
        biz_pax[d.team_id] = min(int(raw_demand), cap)

    # 6b. Leisure segment (into remaining capacity)
    lei_score: dict[str, float] = {}
    for d in decisions:
        cap = capacity[d.team_id]
        lei_score[d.team_id] = (cap / d.price_leisure) if cap > 0 else 0.0

    total_lei_score = sum(lei_score.values())

    lei_pax: dict[str, int] = {}
    for d in decisions:
        remaining = capacity[d.team_id] - biz_pax[d.team_id]
        if total_lei_score > 0 and remaining > 0:
            raw_demand = leisure_demand * (lei_score[d.team_id] / total_lei_score)
        else:
            raw_demand = 0.0
        lei_pax[d.team_id] = min(int(raw_demand), remaining)

    # Total passengers
    tot_pax: dict[str, int] = {}
    for d in decisions:
        tot_pax[d.team_id] = biz_pax[d.team_id] + lei_pax[d.team_id]

    # ── 7. Revenue (Case Appendix §Revenue) ───────────────────────
    #   revenue = (biz_pax × price_business + lei_pax × price_leisure) × fare_multiplier
    revenue: dict[str, float] = {}
    for d in decisions:
        rev = float(
            biz_pax[d.team_id] * d.price_business
            + lei_pax[d.team_id] * d.price_leisure
        ) * fare_multiplier
        revenue[d.team_id] = rev

    # ── 8. Costs (Case Appendix §Costs) ───────────────────────────
    #   variable_cost  = total_pax × variable_cost_per_passenger
    #   fixed_cost     = monthly_flights × fixed_cost_per_flight
    #   branding_cost  = lookup[branding_level]
    #   product_cost   = lookup[product_strategy]
    #   total_cost     = variable + fixed + branding + product
    var_cost: dict[str, float] = {}
    fix_cost: dict[str, float] = {}
    brd_cost: dict[str, float] = {}
    prd_cost: dict[str, float] = {}
    ttl_cost: dict[str, float] = {}
    for d in decisions:
        vc = float(tot_pax[d.team_id]) * d.variable_cost_per_passenger
        fc = float(monthly_flights[d.team_id]) * fixed_cost_per_flight
        bc = float(branding_costs[d.branding_level])
        pc = float(product_costs[d.product_strategy])
        var_cost[d.team_id] = vc
        fix_cost[d.team_id] = fc
        brd_cost[d.team_id] = bc
        prd_cost[d.team_id] = pc
        ttl_cost[d.team_id] = vc + fc + bc + pc

    # ── 9. Profit (Case Appendix §Profit) ─────────────────────────
    #   profit = revenue − total_cost
    profit: dict[str, float] = {}
    for d in decisions:
        profit[d.team_id] = revenue[d.team_id] - ttl_cost[d.team_id]

    # ── 10. Market shares (Case Appendix §Market Share) ───────────
    #   ms_vol  = pax_i / Σ pax_j
    #   ms_prof = max(profit_i, 0) / Σ max(profit_j, 0)
    #   Fallback if all profits ≤ 0: proportional to raw profit.
    #   Fallback if all profits = 0: equal share.
    total_passengers = sum(tot_pax.values())
    total_positive_profit = sum(max(p, 0.0) for p in profit.values())
    total_profit = sum(profit.values())

    # ── 11. Assemble results ──────────────────────────────────────
    results = IndependentResults()

    for d in decisions:
        pax = tot_pax[d.team_id]
        cap = capacity[d.team_id]
        mf = monthly_flights[d.team_id]
        rev = revenue[d.team_id]
        tc = ttl_cost[d.team_id]
        pr = profit[d.team_id]

        # Load factor
        lf = pax / cap if cap > 0 else 0.0

        # Per-flight metrics
        avg_rev  = rev / mf if mf > 0 else 0.0
        avg_cost = tc / mf if mf > 0 else 0.0
        avg_prof = pr / mf if mf > 0 else 0.0

        # Market share – volume
        ms_vol = pax / total_passengers if total_passengers > 0 else 0.0

        # Market share – profit
        if total_positive_profit > 0:
            ms_prof = max(pr, 0.0) / total_positive_profit
        elif total_profit != 0:
            ms_prof = pr / total_profit
        else:
            ms_prof = 1.0 / n_teams

        results.team_results[d.team_id] = IndependentTeamResult(
            team_id=d.team_id,
            passengers=pax,
            revenue=_fmt(rev, 2),
            variable_cost=_fmt(var_cost[d.team_id], 2),
            fixed_cost=_fmt(fix_cost[d.team_id], 2),
            branding_cost=_fmt(brd_cost[d.team_id], 2),
            product_cost=_fmt(prd_cost[d.team_id], 2),
            total_cost=_fmt(tc, 2),
            profit=_fmt(pr, 2),
            market_share_volume=_fmt(ms_vol, 6),
            market_share_profit=_fmt(ms_prof, 6),
            load_factor=_fmt(lf, 4),
            avg_revenue_per_flight=_fmt(avg_rev, 2),
            avg_cost_per_flight=_fmt(avg_cost, 2),
            avg_profit_per_flight=_fmt(avg_prof, 2),
            price_business=_fmt(d.price_business, 2),
            price_leisure=_fmt(d.price_leisure, 2),
        )

    results.market_result = IndependentMarketResult(
        total_demand=total_demand_passengers,
        total_passengers=total_passengers,
        total_revenue=_fmt(sum(revenue.values()), 2),
        total_cost=_fmt(sum(ttl_cost.values()), 2),
        total_profit=_fmt(total_profit, 2),
    )

    return results
