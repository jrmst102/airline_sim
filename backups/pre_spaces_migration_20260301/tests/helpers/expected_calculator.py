"""
Expected Calculator – independent re-computation of round results.
===================================================================
Uses the simulation engine's *pure* functions (``compute_round_results``)
so that "expected" values follow exactly the same algebra as production.
The inputs are loaded directly from CSV files — NOT from the CSV results
written by ``move_next_round`` — giving a true independent cross-check.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from app.core.simulation_engine import (
    RoundComputationResult,
    SimulationParameters,
    TeamDecisionInput,
    build_parameters_from_csv,
    compute_round_results,
)
from app.modules.setup_simulation import load_parameters


# ── Formatting helpers (mirror move_next_round._fmt_number) ────────────
def _fmt(value: float, decimals: int) -> str:
    """Reproduce the exact formatting used by move_next_round."""
    return f"{value:.{decimals}f}"


@dataclass
class ExpectedTeamResult:
    """Integer-comparable expected values for one team."""
    team_id: str
    passengers: int
    revenue: str          # formatted to 2dp (string match)
    variable_cost: str
    fixed_cost: str
    branding_cost: str
    product_cost: str
    total_cost: str
    profit: str
    market_share_volume: str   # 6dp
    market_share_profit: str   # 6dp
    load_factor: str           # 4dp
    avg_revenue_per_flight: str
    avg_cost_per_flight: str
    avg_profit_per_flight: str
    price_business: str
    price_leisure: str


@dataclass
class ExpectedMarketResult:
    total_demand: int
    total_passengers: int
    total_revenue: str
    total_cost: str
    total_profit: str


@dataclass
class ExpectedResults:
    team_results: dict[str, ExpectedTeamResult] = field(default_factory=dict)
    market_result: ExpectedMarketResult | None = None


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _as_int(v: str, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _as_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_expected(
    sim_path: Path,
    round_number: int,
) -> ExpectedResults:
    """Re-compute expected round results from CSV inputs.

    Reads:
      - parameters.csv
      - teams.csv       (variable_cost_per_passenger)
      - decisions.csv   (for *round_number*)

    Calls ``compute_round_results`` — the engine's pure function —
    then formats outputs identically to ``move_next_round``.

    Returns an ``ExpectedResults`` object whose fields are formatted
    strings so that comparison with CSV actuals is a straight ``==``.
    """
    # ── Load parameters ────────────────────────────────────────────
    params_dict = load_parameters(sim_path / "parameters.csv")
    engine_params: SimulationParameters = build_parameters_from_csv(params_dict)

    # ── Load variable costs from teams.csv ─────────────────────────
    team_rows = _load_csv_rows(sim_path / "teams.csv")
    var_cost_map: dict[str, float] = {}
    for row in team_rows:
        if row.get("is_active", "0") == "1":
            var_cost_map[row["team_id"]] = _as_float(
                row.get("variable_cost_per_passenger", "0")
            )

    # ── Load decisions for the round ───────────────────────────────
    all_decisions = _load_csv_rows(sim_path / "decisions.csv")
    round_decisions = [
        r for r in all_decisions
        if _as_int(r.get("round_number", "0")) == round_number
    ]

    engine_decisions: list[TeamDecisionInput] = []
    for row in round_decisions:
        tid = row.get("team_id", "")
        engine_decisions.append(TeamDecisionInput(
            team_id=tid,
            flights_per_day=_as_int(row.get("flights_per_day", "0")),
            price_business=_as_float(row.get("price_business", "360")),
            price_leisure=_as_float(row.get("price_leisure", "180")),
            branding_level=row.get("branding_level", "Low"),
            product_strategy=row.get("product_strategy", "None"),
            variable_cost_per_passenger=var_cost_map.get(tid, 0.0),
        ))

    # ── Run engine ─────────────────────────────────────────────────
    result: RoundComputationResult = compute_round_results(
        decisions=engine_decisions,
        parameters=engine_params,
    )

    # ── Format into ExpectedResults (same formatting as move_next_round)
    expected = ExpectedResults()
    for tr in result.team_results:
        expected.team_results[tr.team_id] = ExpectedTeamResult(
            team_id=tr.team_id,
            passengers=tr.passengers,
            revenue=_fmt(tr.revenue, 2),
            variable_cost=_fmt(tr.variable_cost, 2),
            fixed_cost=_fmt(tr.fixed_cost, 2),
            branding_cost=_fmt(tr.branding_cost, 2),
            product_cost=_fmt(tr.product_cost, 2),
            total_cost=_fmt(tr.total_cost, 2),
            profit=_fmt(tr.profit, 2),
            market_share_volume=_fmt(tr.market_share_volume, 6),
            market_share_profit=_fmt(tr.market_share_profit, 6),
            load_factor=_fmt(tr.load_factor, 4),
            avg_revenue_per_flight=_fmt(tr.avg_revenue_per_flight, 2),
            avg_cost_per_flight=_fmt(tr.avg_cost_per_flight, 2),
            avg_profit_per_flight=_fmt(tr.avg_profit_per_flight, 2),
            price_business=_fmt(tr.price_business, 2),
            price_leisure=_fmt(tr.price_leisure, 2),
        )

    mr = result.market_result
    expected.market_result = ExpectedMarketResult(
        total_demand=mr.total_demand,
        total_passengers=mr.total_passengers,
        total_revenue=_fmt(mr.total_revenue, 2),
        total_cost=_fmt(mr.total_cost, 2),
        total_profit=_fmt(mr.total_profit, 2),
    )

    return expected
