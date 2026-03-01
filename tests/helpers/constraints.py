"""
Constraints – read allowable decision values from simulation config.
====================================================================
All ranges and enumerations are derived from the simulation's own
data files (parameters.csv, airplane_types.csv, enter_decisions module).
Nothing is hard-coded here.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Constraints:
    """Permissible decision values for a simulation."""

    # Integer ranges
    min_flights_per_day: int
    max_flights_per_day: int
    min_price: int          # floor (integer)
    max_price: int          # ceiling (integer)

    # Categorical enumerations (order preserved for deterministic picking)
    branding_levels: tuple[str, ...]
    product_strategies: tuple[str, ...]

    # Fare matrix from parameters  {posture -> {segment -> fare}}
    fare_matrix: dict[str, dict[str, int]] = field(default_factory=dict)


def get_constraints(sim_path: Path) -> Constraints:
    """Build constraints by reading the simulation's own config files.

    Reads:
      - airplane_types.csv  → max_flights_per_day
      - parameters.csv      → fare matrix (to know valid fare values)
      - enter_decisions module constants → price floor/ceiling,
        branding / product enumerations
    """
    # ── max flights from airplane_types.csv ────────────────────────
    airplane_csv = sim_path / "airplane_types.csv"
    max_fpd = 5  # fallback
    if airplane_csv.exists():
        with airplane_csv.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                val = row.get("max_flights_per_day", "5")
                try:
                    max_fpd = max(max_fpd, int(val))
                except ValueError:
                    pass

    # ── Price bounds from enter_decisions module ───────────────────
    from app.modules.enter_decisions import MIN_PRICE, MAX_PRICE

    # ── Categorical enums from enter_decisions ─────────────────────
    from app.modules.enter_decisions import VALID_BRANDING, VALID_PRODUCTS

    # ── Fare matrix from parameters.csv ────────────────────────────
    fare_matrix: dict[str, dict[str, int]] = {}
    params_csv = sim_path / "parameters.csv"
    if params_csv.exists():
        params: dict[str, str] = {}
        with params_csv.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                k = row.get("key", "").strip()
                v = row.get("value", "").strip()
                if k:
                    params[k] = v
        for posture in ("Premium", "Match", "Discount"):
            biz_key = f"fare_business_{posture.lower()}"
            lei_key = f"fare_leisure_{posture.lower()}"
            if biz_key in params and lei_key in params:
                fare_matrix[posture] = {
                    "business": int(float(params[biz_key])),
                    "leisure": int(float(params[lei_key])),
                }

    return Constraints(
        min_flights_per_day=0,
        max_flights_per_day=max_fpd,
        min_price=int(MIN_PRICE),
        max_price=int(MAX_PRICE),
        branding_levels=tuple(VALID_BRANDING),
        product_strategies=tuple(VALID_PRODUCTS),
        fare_matrix=fare_matrix,
    )


def clamp_to_constraints(value: int, lo: int, hi: int) -> int:
    """Clamp *value* into [lo, hi]."""
    return max(lo, min(hi, value))
