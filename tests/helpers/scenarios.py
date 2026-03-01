"""
Scenarios – the 32 test scenarios for the airline simulation.
==============================================================
Each scenario starts from deterministic baseline decisions (seeded from the
simulation setup), then applies a minimal set of modifications as described
by the user's specification.

All "random" values are drawn from a ``random.Random(seed)`` instance so
that runs are fully reproducible.

All values obey constraints read from the simulation's own config files
(see ``tests.helpers.constraints``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

from tests.helpers.constraints import Constraints, clamp_to_constraints


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Decision:
    """One team's decision for a round."""
    team_id: str
    flights_per_day: int
    price_business: int
    price_leisure: int
    branding_level: str
    product_strategy: str


@dataclass
class ScenarioSpec:
    """Blueprint for a single test scenario."""
    id: int
    name: str
    description: str
    decision_overrides_fn: Callable[
        [list[Decision], Constraints, random.Random], list[Decision]
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Baseline decisions (from simulation setup — round 1 pre-populated rows)
# ═══════════════════════════════════════════════════════════════════════════
# These match what setup_simulation writes into decisions.csv for round 1.
# Prices come from the FARES lookup by each team's baseline_pricing_posture.

from app.modules.setup_simulation import TEAM_BASELINES, FARES, TEAM_LETTERS


def build_baseline_decisions() -> list[Decision]:
    """Construct baseline Round-1 decisions from the case appendix data."""
    decisions: list[Decision] = []
    for letter in TEAM_LETTERS:
        bl = TEAM_BASELINES[letter]
        posture = bl["baseline_pricing_posture"]
        decisions.append(Decision(
            team_id=letter,
            flights_per_day=bl["baseline_flights_per_day"],
            price_business=FARES[posture]["business"],
            price_leisure=FARES[posture]["leisure"],
            branding_level=bl["baseline_branding"],
            product_strategy=bl["baseline_product"],
        ))
    return decisions


def _copy_decisions(decisions: list[Decision]) -> list[Decision]:
    """Deep-copy the decision list."""
    return [
        Decision(
            team_id=d.team_id,
            flights_per_day=d.flights_per_day,
            price_business=d.price_business,
            price_leisure=d.price_leisure,
            branding_level=d.branding_level,
            product_strategy=d.product_strategy,
        )
        for d in decisions
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Helper functions for scenario generation
# ═══════════════════════════════════════════════════════════════════════════

def _all_prices(decisions: list[Decision]) -> list[tuple[int, int]]:
    """Return all (biz, lei) price pairs from current decisions."""
    return [(d.price_business, d.price_leisure) for d in decisions]


def pick_lowest_prices(
    constraints: Constraints,
    decisions: list[Decision],
    exclude_team: str,
) -> tuple[int, int]:
    """Prices strictly lower than all other airlines (if feasible)."""
    others_biz = [d.price_business for d in decisions if d.team_id != exclude_team]
    others_lei = [d.price_leisure for d in decisions if d.team_id != exclude_team]
    biz = clamp_to_constraints(min(others_biz) - 10, constraints.min_price, constraints.max_price)
    lei = clamp_to_constraints(min(others_lei) - 10, constraints.min_price, constraints.max_price)
    return biz, lei


def pick_highest_prices(
    constraints: Constraints,
    decisions: list[Decision],
    exclude_team: str,
) -> tuple[int, int]:
    """Prices strictly higher than all other airlines (if feasible)."""
    others_biz = [d.price_business for d in decisions if d.team_id != exclude_team]
    others_lei = [d.price_leisure for d in decisions if d.team_id != exclude_team]
    biz = clamp_to_constraints(max(others_biz) + 10, constraints.min_price, constraints.max_price)
    lei = clamp_to_constraints(max(others_lei) + 10, constraints.min_price, constraints.max_price)
    return biz, lei


def pick_mid_prices(
    constraints: Constraints,
    decisions: list[Decision],
    exclude_team: str,
    rng: random.Random,
) -> tuple[int, int]:
    """Prices strictly between min and max observed (not extremes)."""
    others_biz = sorted(set(d.price_business for d in decisions if d.team_id != exclude_team))
    others_lei = sorted(set(d.price_leisure for d in decisions if d.team_id != exclude_team))

    lo_b, hi_b = min(others_biz), max(others_biz)
    lo_l, hi_l = min(others_lei), max(others_lei)

    # Ensure there's room between extremes
    if hi_b - lo_b <= 2:
        biz = clamp_to_constraints(lo_b + 1, constraints.min_price, constraints.max_price)
    else:
        biz = rng.randint(lo_b + 1, hi_b - 1)
        biz = clamp_to_constraints(biz, constraints.min_price, constraints.max_price)

    if hi_l - lo_l <= 2:
        lei = clamp_to_constraints(lo_l + 1, constraints.min_price, constraints.max_price)
    else:
        lei = rng.randint(lo_l + 1, hi_l - 1)
        lei = clamp_to_constraints(lei, constraints.min_price, constraints.max_price)

    return biz, lei


def pick_random_prices(
    constraints: Constraints,
    decisions: list[Decision],
    exclude_team: str,
    rng: random.Random,
) -> tuple[int, int]:
    """Random prices between lowest and highest observed (inclusive)."""
    others_biz = [d.price_business for d in decisions if d.team_id != exclude_team]
    others_lei = [d.price_leisure for d in decisions if d.team_id != exclude_team]
    lo_b, hi_b = min(others_biz), max(others_biz)
    lo_l, hi_l = min(others_lei), max(others_lei)
    biz = rng.randint(lo_b, hi_b)
    lei = rng.randint(lo_l, hi_l)
    biz = clamp_to_constraints(biz, constraints.min_price, constraints.max_price)
    lei = clamp_to_constraints(lei, constraints.min_price, constraints.max_price)
    return biz, lei


def pick_random_brand(constraints: Constraints, rng: random.Random) -> str:
    """Random branding level from allowed values."""
    return rng.choice(constraints.branding_levels)


def pick_random_product(constraints: Constraints, rng: random.Random) -> str:
    """Random product strategy from allowed values."""
    return rng.choice(constraints.product_strategies)


def pick_high_brand(constraints: Constraints) -> str:
    return constraints.branding_levels[-1]  # "High"


def pick_low_brand(constraints: Constraints) -> str:
    return constraints.branding_levels[0]  # "Low"


def pick_premium_product(constraints: Constraints) -> str:
    return constraints.product_strategies[0]  # "High"


def pick_economy_product(constraints: Constraints) -> str:
    return constraints.product_strategies[1]  # "Medium"


def pick_flights_changed(
    constraints: Constraints,
    baseline_fpd: int,
    rng: random.Random,
    direction: str = "up",
) -> int:
    """An integer flights_per_day different from baseline, within range."""
    lo = constraints.min_flights_per_day
    hi = constraints.max_flights_per_day
    if direction == "up":
        target = min(baseline_fpd + 1, hi)
    elif direction == "down":
        target = max(baseline_fpd - 1, lo)
    else:  # random
        candidates = [v for v in range(lo, hi + 1) if v != baseline_fpd]
        if not candidates:
            return baseline_fpd
        target = rng.choice(candidates)
    if target == baseline_fpd and target < hi:
        target += 1
    elif target == baseline_fpd and target > lo:
        target -= 1
    return clamp_to_constraints(target, lo, hi)


# ═══════════════════════════════════════════════════════════════════════════
# The 32 scenarios
# ═══════════════════════════════════════════════════════════════════════════

def _s01_no_changes(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 1: No changes. Advance to next round."""
    return decs  # unchanged


def _s02_one_lowest_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 2: One airline lowers both prices to lowest."""
    biz, lei = pick_lowest_prices(c, decs, "A")
    decs[0].price_business = biz
    decs[0].price_leisure = lei
    return decs


def _s03_one_highest_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 3: One airline raises both prices to highest."""
    biz, lei = pick_highest_prices(c, decs, "A")
    decs[0].price_business = biz
    decs[0].price_leisure = lei
    return decs


def _s04_one_brand_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 4: One airline changes Brand and Product only."""
    decs[0].branding_level = pick_random_brand(c, rng)
    decs[0].product_strategy = pick_random_product(c, rng)
    return decs


def _s05_two_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 5: Two airlines change prices: one lowest, one highest."""
    biz_lo, lei_lo = pick_lowest_prices(c, decs, "A")
    decs[0].price_business = biz_lo
    decs[0].price_leisure = lei_lo
    biz_hi, lei_hi = pick_highest_prices(c, decs, "B")
    decs[1].price_business = biz_hi
    decs[1].price_leisure = lei_hi
    return decs


def _s06_two_brand_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 6: Two airlines change Brand+Product: High vs Low, Premium vs Economy."""
    decs[0].branding_level = pick_high_brand(c)
    decs[0].product_strategy = pick_premium_product(c)
    decs[1].branding_level = pick_low_brand(c)
    decs[1].product_strategy = pick_economy_product(c)
    return decs


def _s07_two_prices_brand_product_mid(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 7: Two airlines change prices+brand+product; mid prices, random brand/product."""
    for idx in (0, 1):
        tid = decs[idx].team_id
        biz, lei = pick_mid_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].branding_level = pick_random_brand(c, rng)
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s08_three_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 8: Three airlines change prices: highest, lowest, random."""
    biz_hi, lei_hi = pick_highest_prices(c, decs, "A")
    decs[0].price_business = biz_hi
    decs[0].price_leisure = lei_hi

    biz_lo, lei_lo = pick_lowest_prices(c, decs, "B")
    decs[1].price_business = biz_lo
    decs[1].price_leisure = lei_lo

    biz_r, lei_r = pick_random_prices(c, decs, "C", rng)
    decs[2].price_business = biz_r
    decs[2].price_leisure = lei_r
    return decs


def _s09_three_prices_brand_product_no_extremes(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 9: Three airlines change prices+brand+product; no extreme prices."""
    for idx in (0, 1, 2):
        tid = decs[idx].team_id
        biz, lei = pick_mid_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].branding_level = pick_random_brand(c, rng)
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s10_four_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 10: Four airlines change prices randomly."""
    for idx in (0, 1, 2, 3):
        tid = decs[idx].team_id
        biz, lei = pick_random_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s11_five_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 11: Five airlines change prices randomly."""
    for idx in (0, 1, 2, 3, 4):
        tid = decs[idx].team_id
        biz, lei = pick_random_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s12_five_prices_brand_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 12: Five airlines change prices + brand + product."""
    for idx in (0, 1, 2, 3, 4):
        tid = decs[idx].team_id
        biz, lei = pick_random_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].branding_level = pick_random_brand(c, rng)
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s13_all_prices_five_brand_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 13: All six change prices; five change brand+product."""
    for idx in range(6):
        tid = decs[idx].team_id
        biz, lei = pick_random_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    for idx in range(5):  # first 5 change brand+product
        decs[idx].branding_level = pick_random_brand(c, rng)
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s14_all_prices_brand_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 14: All six change prices+brand+product."""
    for idx in range(6):
        tid = decs[idx].team_id
        biz, lei = pick_random_prices(c, decs, tid, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].branding_level = pick_random_brand(c, rng)
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s15_one_flights(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 15: One airline changes flights only."""
    decs[0].flights_per_day = pick_flights_changed(c, decs[0].flights_per_day, rng, "up")
    return decs


def _s16_two_flights(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 16: Two airlines change flights only."""
    decs[0].flights_per_day = pick_flights_changed(c, decs[0].flights_per_day, rng, "up")
    decs[1].flights_per_day = pick_flights_changed(c, decs[1].flights_per_day, rng, "down")
    return decs


def _s17_three_flights(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 17: Three airlines change flights only."""
    for idx in range(3):
        decs[idx].flights_per_day = pick_flights_changed(
            c, decs[idx].flights_per_day, rng, "random"
        )
    return decs


def _s18_four_flights(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 18: Four airlines change flights only."""
    for idx in range(4):
        decs[idx].flights_per_day = pick_flights_changed(
            c, decs[idx].flights_per_day, rng, "random"
        )
    return decs


def _s19_five_flights(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 19: Five airlines change flights only."""
    for idx in range(5):
        decs[idx].flights_per_day = pick_flights_changed(
            c, decs[idx].flights_per_day, rng, "random"
        )
    return decs


def _s20_six_flights(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 20: Six airlines change flights only."""
    for idx in range(6):
        decs[idx].flights_per_day = pick_flights_changed(
            c, decs[idx].flights_per_day, rng, "random"
        )
    return decs


def _s21_one_flights_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 21: One airline changes flights and prices."""
    decs[0].flights_per_day = pick_flights_changed(c, decs[0].flights_per_day, rng, "random")
    biz, lei = pick_random_prices(c, decs, decs[0].team_id, rng)
    decs[0].price_business = biz
    decs[0].price_leisure = lei
    return decs


def _s22_two_flights_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 22: Two airlines change flights and prices."""
    for idx in range(2):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s23_three_flights_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 23: Three airlines change flights and prices."""
    for idx in range(3):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s24_four_flights_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 24: Four airlines change flights and prices."""
    for idx in range(4):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s25_five_flights_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 25: Five airlines change flights and prices."""
    for idx in range(5):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s26_all_flights_prices(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 26: All airlines change flights and prices."""
    for idx in range(6):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
    return decs


def _s27_all_flights_prices_brand_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 27: All airlines change flights, prices, brand, product."""
    for idx in range(6):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].branding_level = pick_random_brand(c, rng)
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s28_five_flights_prices_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 28: Five airlines change flights, prices, product."""
    for idx in range(5):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s29_four_flights_prices_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 29: Four airlines change flights, prices, product."""
    for idx in range(4):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s30_three_flights_prices_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 30: Three airlines change flights, prices, product."""
    for idx in range(3):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s31_two_flights_prices_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 31: Two airlines change flights, prices, product."""
    for idx in range(2):
        decs[idx].flights_per_day = pick_flights_changed(c, decs[idx].flights_per_day, rng, "random")
        biz, lei = pick_random_prices(c, decs, decs[idx].team_id, rng)
        decs[idx].price_business = biz
        decs[idx].price_leisure = lei
        decs[idx].product_strategy = pick_random_product(c, rng)
    return decs


def _s32_one_flights_prices_product(
    decs: list[Decision], c: Constraints, rng: random.Random,
) -> list[Decision]:
    """Scenario 32: One airline changes flights, prices, product."""
    decs[0].flights_per_day = pick_flights_changed(c, decs[0].flights_per_day, rng, "random")
    biz, lei = pick_random_prices(c, decs, decs[0].team_id, rng)
    decs[0].price_business = biz
    decs[0].price_leisure = lei
    decs[0].product_strategy = pick_random_product(c, rng)
    return decs


# ═══════════════════════════════════════════════════════════════════════════
# Registry of all 32 scenarios
# ═══════════════════════════════════════════════════════════════════════════

ALL_SCENARIOS: list[ScenarioSpec] = [
    ScenarioSpec(1, "No changes",
        "Advance to next round with baseline decisions unchanged.",
        _s01_no_changes),
    ScenarioSpec(2, "One airline lowest prices",
        "One airline lowers both Business & Leisure to lowest. No other changes.",
        _s02_one_lowest_prices),
    ScenarioSpec(3, "One airline highest prices",
        "One airline raises both Business & Leisure to highest. No other changes.",
        _s03_one_highest_prices),
    ScenarioSpec(4, "One airline brand+product only",
        "One airline changes Brand and Product only. Prices unchanged.",
        _s04_one_brand_product),
    ScenarioSpec(5, "Two airlines: lowest vs highest prices",
        "Two airlines change prices: one lowest, one highest. No other changes.",
        _s05_two_prices),
    ScenarioSpec(6, "Two airlines: High vs Low brand+product",
        "Two airlines change Brand+Product: High branding + Premium vs Low + Economy.",
        _s06_two_brand_product),
    ScenarioSpec(7, "Two airlines: mid prices + brand+product",
        "Two airlines change prices+brand+product; mid prices, random brand/product.",
        _s07_two_prices_brand_product_mid),
    ScenarioSpec(8, "Three airlines: highest/lowest/random prices",
        "Three airlines change prices: one highest, one lowest, one random between.",
        _s08_three_prices),
    ScenarioSpec(9, "Three airlines: prices+brand+product (no extremes)",
        "Three airlines change prices+brand+product; random but no highest/lowest prices.",
        _s09_three_prices_brand_product_no_extremes),
    ScenarioSpec(10, "Four airlines: random prices",
        "Four airlines change prices randomly between highest and lowest.",
        _s10_four_prices),
    ScenarioSpec(11, "Five airlines: random prices",
        "Five airlines change prices randomly between highest and lowest.",
        _s11_five_prices),
    ScenarioSpec(12, "Five airlines: prices+brand+product",
        "Five airlines change prices (between extremes) and brand+product random.",
        _s12_five_prices_brand_product),
    ScenarioSpec(13, "All prices; five brand+product",
        "All six change prices; only five change brand+product; all within allowable.",
        _s13_all_prices_five_brand_product),
    ScenarioSpec(14, "All prices+brand+product",
        "All six change prices+brand+product; all within allowable.",
        _s14_all_prices_brand_product),
    ScenarioSpec(15, "One airline: flights only",
        "One airline changes flights only.",
        _s15_one_flights),
    ScenarioSpec(16, "Two airlines: flights only",
        "Two airlines change flights only.",
        _s16_two_flights),
    ScenarioSpec(17, "Three airlines: flights only",
        "Three airlines change flights only.",
        _s17_three_flights),
    ScenarioSpec(18, "Four airlines: flights only",
        "Four airlines change flights only.",
        _s18_four_flights),
    ScenarioSpec(19, "Five airlines: flights only",
        "Five airlines change flights only.",
        _s19_five_flights),
    ScenarioSpec(20, "Six airlines: flights only",
        "Six airlines change flights only.",
        _s20_six_flights),
    ScenarioSpec(21, "One airline: flights+prices",
        "One airline changes flights and prices.",
        _s21_one_flights_prices),
    ScenarioSpec(22, "Two airlines: flights+prices",
        "Two airlines change flights and prices.",
        _s22_two_flights_prices),
    ScenarioSpec(23, "Three airlines: flights+prices",
        "Three airlines change flights and prices.",
        _s23_three_flights_prices),
    ScenarioSpec(24, "Four airlines: flights+prices",
        "Four airlines change flights and prices.",
        _s24_four_flights_prices),
    ScenarioSpec(25, "Five airlines: flights+prices",
        "Five airlines change flights and prices.",
        _s25_five_flights_prices),
    ScenarioSpec(26, "All airlines: flights+prices",
        "All airlines change flights and prices.",
        _s26_all_flights_prices),
    ScenarioSpec(27, "All airlines: flights+prices+brand+product",
        "All airlines change flights, prices, brand, product.",
        _s27_all_flights_prices_brand_product),
    ScenarioSpec(28, "Five airlines: flights+prices+product",
        "Only five airlines change flights, prices, product.",
        _s28_five_flights_prices_product),
    ScenarioSpec(29, "Four airlines: flights+prices+product",
        "Only four airlines change flights, prices, product.",
        _s29_four_flights_prices_product),
    ScenarioSpec(30, "Three airlines: flights+prices+product",
        "Only three airlines change flights, prices, product.",
        _s30_three_flights_prices_product),
    ScenarioSpec(31, "Two airlines: flights+prices+product",
        "Only two airlines change flights, prices, product.",
        _s31_two_flights_prices_product),
    ScenarioSpec(32, "One airline: flights+prices+product",
        "Only one airline changes flights, prices, product.",
        _s32_one_flights_prices_product),
]
