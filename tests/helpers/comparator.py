"""
Comparator – diff expected vs actual round results.
=====================================================
Compares formatted strings from the expected-calculator against
the CSV rows produced by ``move_next_round``.  Also runs structural
invariant checks (capacity, passenger sums, profit identity, shares).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from tests.helpers.expected_calculator import ExpectedResults


# ── Diff representation ───────────────────────────────────────────────

@dataclass
class Diff:
    """One field-level mismatch."""
    team_id: str       # "" for market-level diffs
    field: str
    expected: str
    actual: str


@dataclass
class InvariantResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ComparisonResult:
    diffs: list[Diff] = field(default_factory=list)
    invariants: list[InvariantResult] = field(default_factory=list)
    missing_teams: list[str] = field(default_factory=list)
    extra_teams: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            not self.diffs
            and not self.missing_teams
            and not self.extra_teams
            and all(inv.passed for inv in self.invariants)
        )


# ── CSV loaders ───────────────────────────────────────────────────────

def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _as_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── Team result comparison fields (order matches CSV schema) ──────────

_TEAM_COMPARE_FIELDS = [
    ("passengers",              "int"),
    ("revenue",                 "str"),
    ("variable_cost",           "str"),
    ("fixed_cost",              "str"),
    ("branding_cost",           "str"),
    ("product_cost",            "str"),
    ("total_cost",              "str"),
    ("profit",                  "str"),
    ("market_share_volume",     "str"),
    ("market_share_profit",     "str"),
    ("load_factor",             "str"),
    ("avg_revenue_per_flight",  "str"),
    ("avg_cost_per_flight",     "str"),
    ("avg_profit_per_flight",   "str"),
    ("price_business",          "str"),
    ("price_leisure",           "str"),
]

_MARKET_COMPARE_FIELDS = [
    ("total_demand",      "int"),
    ("total_passengers",  "int"),
    ("total_revenue",     "str"),
    ("total_cost",        "str"),
    ("total_profit",      "str"),
]


# ── Main comparison entry point ───────────────────────────────────────

def compare_expected_actual(
    expected: ExpectedResults,
    sim_path: Path,
    round_number: int,
) -> ComparisonResult:
    """Compare expected results against actual CSV outputs.

    Reads ``round_results_team.csv`` and ``round_results_market.csv``
    from *sim_path*, filters to *round_number*, and compares every
    deterministic field against *expected*.
    """
    result = ComparisonResult()

    # ── Load actual team results ───────────────────────────────────
    team_rows = _load_csv_rows(sim_path / "round_results_team.csv")
    actual_team: dict[str, dict[str, str]] = {}
    for row in team_rows:
        try:
            rn = int(float(row.get("round_number", "0")))
        except ValueError:
            continue
        if rn == round_number:
            actual_team[row["team_id"]] = row

    # ── Check for missing / extra teams ────────────────────────────
    expected_ids = set(expected.team_results.keys())
    actual_ids = set(actual_team.keys())
    result.missing_teams = sorted(expected_ids - actual_ids)
    result.extra_teams = sorted(actual_ids - expected_ids)

    # ── Field-level comparison for each team ───────────────────────
    for tid in sorted(expected_ids & actual_ids):
        exp = expected.team_results[tid]
        act = actual_team[tid]
        for field_name, field_type in _TEAM_COMPARE_FIELDS:
            exp_val = getattr(exp, field_name)
            act_val = act.get(field_name, "")
            if field_type == "int":
                # Compare as integers
                exp_str = str(exp_val)
                act_str = str(act_val).split(".")[0]  # strip trailing .0
                if exp_str != act_str:
                    result.diffs.append(Diff(tid, field_name, exp_str, act_str))
            else:
                # Compare formatted strings
                if str(exp_val) != str(act_val):
                    result.diffs.append(Diff(tid, field_name, str(exp_val), str(act_val)))

    # ── Market result comparison ───────────────────────────────────
    market_rows = _load_csv_rows(sim_path / "round_results_market.csv")
    actual_market: dict[str, str] | None = None
    for row in market_rows:
        try:
            rn = int(float(row.get("round_number", "0")))
        except ValueError:
            continue
        if rn == round_number:
            actual_market = row
            break

    if actual_market is None:
        result.diffs.append(Diff("", "market_row", "present", "missing"))
    elif expected.market_result is not None:
        em = expected.market_result
        for field_name, field_type in _MARKET_COMPARE_FIELDS:
            exp_val = getattr(em, field_name)
            act_val = actual_market.get(field_name, "")
            if field_type == "int":
                exp_str = str(exp_val)
                act_str = str(act_val).split(".")[0]
                if exp_str != act_str:
                    result.diffs.append(Diff("MARKET", field_name, exp_str, act_str))
            else:
                if str(exp_val) != str(act_val):
                    result.diffs.append(Diff("MARKET", field_name, str(exp_val), str(act_val)))

    # ── Invariant checks ──────────────────────────────────────────
    _check_invariants(result, actual_team, actual_market)

    return result


def _check_invariants(
    result: ComparisonResult,
    actual_team: dict[str, dict[str, str]],
    actual_market: dict[str, str] | None,
) -> None:
    """Run structural invariant checks on actual results."""

    # 1) carried_total <= capacity  (pax <= flights_per_day * 30 * 200)
    #    We don't have flights_per_day in results, so we check load_factor <= 1
    all_load_ok = True
    bad_load_teams: list[str] = []
    for tid, row in actual_team.items():
        lf = _as_float(row.get("load_factor", "0"))
        if lf > 1.0001:  # small epsilon
            all_load_ok = False
            bad_load_teams.append(f"{tid}(lf={lf:.4f})")
    result.invariants.append(InvariantResult(
        name="carried_total <= capacity",
        passed=all_load_ok,
        detail=", ".join(bad_load_teams) if bad_load_teams else "",
    ))

    # 2) Profit == Revenue - Total_Cost  (exact string match after formatting)
    profit_ok = True
    profit_issues: list[str] = []
    for tid, row in actual_team.items():
        rev = _as_float(row.get("revenue", "0"))
        tc = _as_float(row.get("total_cost", "0"))
        pr = _as_float(row.get("profit", "0"))
        diff = abs(rev - tc - pr)
        if diff > 0.015:  # tolerance for 2dp formatting
            profit_ok = False
            profit_issues.append(f"{tid}(rev={rev:.2f}-tc={tc:.2f}={rev-tc:.2f} vs profit={pr:.2f})")
    result.invariants.append(InvariantResult(
        name="Profit == Revenue - Cost",
        passed=profit_ok,
        detail="; ".join(profit_issues) if profit_issues else "",
    ))

    # 3) Total_cost == var + fix + brand + product
    cost_decomp_ok = True
    cost_issues: list[str] = []
    for tid, row in actual_team.items():
        vc = _as_float(row.get("variable_cost", "0"))
        fc = _as_float(row.get("fixed_cost", "0"))
        bc = _as_float(row.get("branding_cost", "0"))
        pc = _as_float(row.get("product_cost", "0"))
        tc = _as_float(row.get("total_cost", "0"))
        diff = abs(vc + fc + bc + pc - tc)
        if diff > 0.015:
            cost_decomp_ok = False
            cost_issues.append(f"{tid}(components={vc+fc+bc+pc:.2f} vs total={tc:.2f})")
    result.invariants.append(InvariantResult(
        name="Total_cost == sum(components)",
        passed=cost_decomp_ok,
        detail="; ".join(cost_issues) if cost_issues else "",
    ))

    # 4) Market share volume sums ≈ 1
    ms_vol_sum = sum(_as_float(r.get("market_share_volume", "0")) for r in actual_team.values())
    ms_vol_ok = abs(ms_vol_sum - 1.0) < 0.001
    result.invariants.append(InvariantResult(
        name="Sum(market_share_volume) ≈ 1",
        passed=ms_vol_ok,
        detail=f"sum={ms_vol_sum:.6f}" if not ms_vol_ok else "",
    ))

    # 5) Market totals match sum of teams
    if actual_market:
        mkt_pax = int(float(actual_market.get("total_passengers", "0")))
        team_pax_sum = sum(int(float(r.get("passengers", "0"))) for r in actual_team.values())
        pax_match = mkt_pax == team_pax_sum
        result.invariants.append(InvariantResult(
            name="Market total_passengers == sum(team pax)",
            passed=pax_match,
            detail=f"market={mkt_pax} vs sum={team_pax_sum}" if not pax_match else "",
        ))
