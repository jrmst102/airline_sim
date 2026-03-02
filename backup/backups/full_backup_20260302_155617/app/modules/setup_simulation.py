"""
Setup Simulation – Airlines Competitive Strategy Simulation
============================================================
Seeds all CSV files with baseline values from the case:
"Airlines Competitive Game – Turbulence at 30,000 Feet:
 Competition on the JFK–Boston Corridor" (Spring 2026).

All numeric constants are taken verbatim from the Case Appendix
and are clearly annotated.  Run standalone:

    python -m app.modules.setup_simulation sim_001 --overwrite
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.csv_manager import write_csv as _cm_write_csv


# ═══════════════════════════════════════════════════════════════════════════
# Case Appendix – Baseline Constants
# ═══════════════════════════════════════════════════════════════════════════
_NUM_TEAMS = 6  # Airlines A–F

# ── Market demand (monthly passengers) ─────────────────────────────────
TOTAL_DEMAND     = 120_000   # Case Appendix
BUSINESS_DEMAND  = 48_000    # 40 % of total (Case Appendix)
LEISURE_DEMAND   = 72_000    # 60 % of total (Case Appendix)

# ── Capacity & flight costs ───────────────────────────────────────────
SEATS_PER_FLIGHT       = 200     # Case Appendix
FIXED_COST_PER_FLIGHT  = 18_000  # $ per flight (Case Appendix)
DAYS_PER_MONTH         = 30      # Monthly rounds

# ── Discount-penalty rule (Case Appendix) ──────────────────────────────
DISCOUNT_PENALTY_THRESHOLD = 3   # min airlines choosing Discount
DISCOUNT_PENALTY_RATE      = 0.08
# ── Fare multiplier (Case Appendix) ────────────────────────────
# JFK–BOS is a high-frequency shuttle corridor.  Each passenger
# purchases an average of ~3 tickets per month, so monthly revenue
# per passenger = fare × fare_multiplier.
FARE_MULTIPLIER = 3.0
# ── Pricing matrix (fare by posture, Case Appendix) ───────────────────
FARES: dict[str, dict[str, int]] = {
    "Premium":  {"business": 450, "leisure": 220},
    "Match":    {"business": 360, "leisure": 180},
    "Discount": {"business": 290, "leisure": 140},
}

# ── Branding costs per month (Case Appendix) ──────────────────────────
BRANDING_COSTS: dict[str, int] = {
    "Low":    1_000_000,
    "Medium": 3_000_000,
    "High":   5_000_000,
}

# ── Product-strategy costs per month (Case Appendix) ──────────────────
PRODUCT_COSTS: dict[str, int] = {
    "High":   4_000_000,
    "Medium": 3_000_000,
    "Low":    2_000_000,
}

# ── Per-team baseline data, keyed by letter A–F (Case Appendix) ───────
# Strategic Baseline (Round 0 Positioning) — each airline starts with
# a distinct archetype defining capacity, pricing, branding, product
# strategy, and customer / operating indices.

# Valid enum values (for baseline consistency enforcement)
VALID_PRICING_POSTURES  = ("Premium", "Match", "Discount")
VALID_BRANDING_LEVELS   = ("Low", "Medium", "High")
VALID_PRODUCT_STRATEGIES = ("High", "Medium", "Low")

TEAM_BASELINES: dict[str, dict[str, Any]] = {
    "A": {  # Premium Leader
        "baseline_passengers":      26_400,
        "baseline_volume_share":    0.22,
        "baseline_profit_millions": 6.5,
        "baseline_profit_share":    0.26,
        "variable_cost_per_pax":    155,
        "baseline_flights_per_day": 5,
        "baseline_pricing_posture": "Premium",
        "baseline_branding":        "High",
        "baseline_product":         "High",
        "baseline_csi":             88,
        "baseline_oei":             78,
    },
    "B": {  # Strong Full-Service Carrier
        "baseline_passengers":      22_800,
        "baseline_volume_share":    0.19,
        "baseline_profit_millions": 4.8,
        "baseline_profit_share":    0.19,
        "variable_cost_per_pax":    170,
        "baseline_flights_per_day": 4,
        "baseline_pricing_posture": "Match",
        "baseline_branding":        "Medium",
        "baseline_product":         "Low",
        "baseline_csi":             82,
        "baseline_oei":             72,
    },
    "C": {  # Balanced Competitor
        "baseline_passengers":      21_600,
        "baseline_volume_share":    0.18,
        "baseline_profit_millions": 4.2,
        "baseline_profit_share":    0.17,
        "variable_cost_per_pax":    160,
        "baseline_flights_per_day": 4,
        "baseline_pricing_posture": "Match",
        "baseline_branding":        "Medium",
        "baseline_product":         "Medium",
        "baseline_csi":             76,
        "baseline_oei":             74,
    },
    "D": {  # Efficient Value Carrier
        "baseline_passengers":      19_200,
        "baseline_volume_share":    0.16,
        "baseline_profit_millions": 4.5,
        "baseline_profit_share":    0.18,
        "variable_cost_per_pax":    130,
        "baseline_flights_per_day": 4,
        "baseline_pricing_posture": "Discount",
        "baseline_branding":        "Low",
        "baseline_product":         "Low",
        "baseline_csi":             68,
        "baseline_oei":             86,
    },
    "E": {  # Ultra Low-Cost Challenger
        "baseline_passengers":      15_600,
        "baseline_volume_share":    0.13,
        "baseline_profit_millions": 2.0,
        "baseline_profit_share":    0.08,
        "variable_cost_per_pax":    110,
        "baseline_flights_per_day": 3,
        "baseline_pricing_posture": "Discount",
        "baseline_branding":        "Low",
        "baseline_product":         "Medium",
        "baseline_csi":             62,
        "baseline_oei":             90,
    },
    "F": {  # Niche Quality/Value Carrier
        "baseline_passengers":      14_400,
        "baseline_volume_share":    0.12,
        "baseline_profit_millions": 3.0,
        "baseline_profit_share":    0.12,
        "variable_cost_per_pax":    145,
        "baseline_flights_per_day": 3,
        "baseline_pricing_posture": "Premium",
        "baseline_branding":        "Medium",
        "baseline_product":         "Low",
        "baseline_csi":             80,
        "baseline_oei":             76,
    },
}
TEAM_LETTERS = list(TEAM_BASELINES.keys())  # ["A", "B", … "F"]


def _validate_baseline_enums() -> None:
    """Enforce consistent enum values in TEAM_BASELINES at import time."""
    for tid, bl in TEAM_BASELINES.items():
        assert bl["baseline_pricing_posture"] in VALID_PRICING_POSTURES, \
            f"Team {tid}: invalid pricing_posture '{bl['baseline_pricing_posture']}'"
        assert bl["baseline_branding"] in VALID_BRANDING_LEVELS, \
            f"Team {tid}: invalid branding_level '{bl['baseline_branding']}'"
        assert bl["baseline_product"] in VALID_PRODUCT_STRATEGIES, \
            f"Team {tid}: invalid product_strategy '{bl['baseline_product']}'"


_validate_baseline_enums()


# ═══════════════════════════════════════════════════════════════════════════
# CSV Schemas – column definitions for each file
# ═══════════════════════════════════════════════════════════════════════════
CSV_SCHEMAS: dict[str, list[str]] = {
    "simulation.csv": [
        "simulation_id",
        "name",
        "status",
        "current_round",
        "total_rounds",
        "created_at_utc",
        "updated_at_utc",
    ],
    "parameters.csv": [                 # key-value format
        "key",
        "value",
        "notes",
    ],
    "teams.csv": [
        "simulation_id",
        "team_id",
        "team_name",
        "is_active",
        "baseline_passengers",
        "baseline_volume_share",
        "baseline_profit_millions",
        "baseline_profit_share",
        "variable_cost_per_passenger",
        "baseline_flights_per_day",
        "baseline_pricing_posture",
        "baseline_branding_level",
        "baseline_product_strategy",
        "baseline_csi",
        "baseline_oei",
        "created_at_utc",
    ],
    "users.csv": [
        "simulation_id",
        "user_id",
        "username",
        "role",
        "team_id",
        "password_hash",
        "is_locked",
        "created_at_utc",
    ],
    "routes.csv": [
        "simulation_id",
        "route_id",
        "origin",
        "destination",
        "distance_miles",
        "is_active",
        "created_at_utc",
    ],
    "airplane_types.csv": [
        "simulation_id",
        "airplane_type_id",
        "name",
        "seats_per_flight",
        "max_flights_per_day",
        "created_at_utc",
    ],
    "rounds.csv": [
        "simulation_id",
        "round_number",
        "status",
        "opened_at_utc",
        "closed_at_utc",
    ],
    "decisions.csv": [
        "simulation_id",
        "round_number",
        "team_id",
        "flights_per_day",
        "price_business",
        "price_leisure",
        "branding_level",
        "product_strategy",
        "submitted_at_utc",
    ],
    "round_results_team.csv": [
        "simulation_id",
        "round_number",
        "team_id",
        "passengers",
        "revenue",
        "variable_cost",
        "fixed_cost",
        "branding_cost",
        "product_cost",
        "total_cost",
        "profit",
        "market_share_volume",
        "market_share_profit",
        "load_factor",
        "avg_revenue_per_flight",
        "avg_cost_per_flight",
        "avg_profit_per_flight",
        "price_business",
        "price_leisure",
        "csi",
        "oei",
        "created_at_utc",
    ],
    "round_results_market.csv": [
        "simulation_id",
        "round_number",
        "total_demand",
        "total_passengers",
        "total_revenue",
        "total_cost",
        "total_profit",
        "created_at_utc",
    ],
    "login_log.csv": [
        "event_id",
        "simulation_id",
        "user_id",
        "username",
        "event_type",
        "event_at_utc",
    ],
    "admin_actions.csv": [
        "event_id",
        "simulation_id",
        "admin_user_id",
        "action",
        "details",
        "event_at_utc",
    ],
    "log.csv": [
        "event_id",
        "simulation_id",
        "actor_user_id",
        "action",
        "details",
        "event_at_utc",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_csv(
    path: Path, headers: list[str], rows: list[dict[str, Any]]
) -> None:
    """Write CSV atomically: write to .tmp then rename."""
    tmp_path = path.with_suffix(".csv.tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    tmp_path.replace(path)  # atomic on POSIX


# ---------------------------------------------------------------------------
# Parameter-file helpers (key-value format)
# ---------------------------------------------------------------------------

def load_parameters(parameters_csv: Path) -> dict[str, str]:
    """Parse a key-value parameters.csv into a lookup dict.

    Expected CSV format:  key,value,notes
    Returns ``{key: value, …}``.
    """
    if not parameters_csv.exists():
        raise FileNotFoundError(f"Parameters file not found: {parameters_csv}")
    result: dict[str, str] = {}
    with parameters_csv.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            k = row.get("key", "").strip()
            v = row.get("value", "").strip()
            if k:
                result[k] = v
    return result


def get_parameter_float(
    params: dict[str, str], key: str, default: float = 0.0
) -> float:
    """Get a float parameter value from a key-value dict."""
    try:
        return float(params.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def get_parameter_int(
    params: dict[str, str], key: str, default: int = 0
) -> int:
    """Get an int parameter value from a key-value dict."""
    try:
        return int(float(params.get(key, str(default))))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Build parameters.csv rows from Case Appendix constants
# ---------------------------------------------------------------------------

def _build_parameter_rows() -> list[dict[str, str]]:
    """Return key-value rows for parameters.csv."""
    entries: list[tuple[str, str, str]] = [
        # ── Market demand (Case Appendix) ──
        ("total_demand_passengers", str(TOTAL_DEMAND),
         "Total monthly demand in passengers"),
        ("business_demand",         str(BUSINESS_DEMAND),
         "40% of total – business segment"),
        ("leisure_demand",          str(LEISURE_DEMAND),
         "60% of total – leisure segment"),
        # ── Capacity & flight costs (Case Appendix) ──
        ("seats_per_flight",        str(SEATS_PER_FLIGHT),
         "Seat capacity per flight"),
        ("fixed_cost_per_flight",   str(FIXED_COST_PER_FLIGHT),
         "Fixed cost per flight ($)"),
        ("days_per_month",          str(DAYS_PER_MONTH),
         "Days in one monthly round"),
        # ── Discount penalty rule (Case Appendix) ──
        ("discount_penalty_threshold", str(DISCOUNT_PENALTY_THRESHOLD),
         "Min airlines choosing Discount to trigger penalty"),
        ("discount_penalty_rate",      str(DISCOUNT_PENALTY_RATE),
         "Revenue penalty rate when threshold met"),
        # ── Pricing matrix – business fares (Case Appendix) ──
        ("fare_business_premium",  str(FARES["Premium"]["business"]),
         "Business fare – Premium posture"),
        ("fare_business_match",    str(FARES["Match"]["business"]),
         "Business fare – Match posture"),
        ("fare_business_discount", str(FARES["Discount"]["business"]),
         "Business fare – Discount posture"),
        # ── Pricing matrix – leisure fares (Case Appendix) ──
        ("fare_leisure_premium",   str(FARES["Premium"]["leisure"]),
         "Leisure fare – Premium posture"),
        ("fare_leisure_match",     str(FARES["Match"]["leisure"]),
         "Leisure fare – Match posture"),
        ("fare_leisure_discount",  str(FARES["Discount"]["leisure"]),
         "Leisure fare – Discount posture"),
        # ── Branding costs (Case Appendix) ──
        ("branding_cost_low",    str(BRANDING_COSTS["Low"]),
         "Monthly branding cost – Low"),
        ("branding_cost_medium", str(BRANDING_COSTS["Medium"]),
         "Monthly branding cost – Medium"),
        ("branding_cost_high",   str(BRANDING_COSTS["High"]),
         "Monthly branding cost – High"),
        # ── Product strategy costs (Case Appendix) ──
        ("product_cost_high",   str(PRODUCT_COSTS["High"]),
         "Monthly cost – High"),
        ("product_cost_medium", str(PRODUCT_COSTS["Medium"]),
         "Monthly cost – Medium"),
        ("product_cost_low",    str(PRODUCT_COSTS["Low"]),
         "Monthly cost – Low"),
        # ── Fare multiplier (Case Appendix) ──
        ("fare_multiplier",              str(FARE_MULTIPLIER),
         "Avg monthly trips per passenger (JFK–BOS shuttle corridor)"),
    ]
    return [{"key": k, "value": v, "notes": n} for k, v, n in entries]


# ═══════════════════════════════════════════════════════════════════════════
# Main setup function
# ═══════════════════════════════════════════════════════════════════════════

def setup_simulation(
    simulation_id: str,
    simulation_name: str,
    total_rounds: int = 3,
    team_names: list[str] | None = None,
    root_dir: Path | str = Path("simulation/simulations"),
    overwrite: bool = False,
) -> Path:
    """Create / overwrite a simulation folder and seed all CSVs.

    Parameters
    ----------
    simulation_id : str
        Unique identifier (e.g. ``"sim_001"``).
    simulation_name : str
        Human-readable display name.
    total_rounds : int
        Number of monthly rounds (default 3 per case).
    team_names : list[str] | None
        Display names for the 6 airlines.  Must contain exactly 6
        entries.  Defaults to ``["Airline A", …, "Airline F"]``.
    root_dir : Path | str
        Parent directory that holds simulation folders.
    overwrite : bool
        If *True*, recreates the folder and all files.

    Returns
    -------
    Path
        Path to the created simulation directory.
    """
    # ── Validation ─────────────────────────────────────────────────
    if total_rounds < 1:
        raise ValueError("total_rounds must be >= 1")

    if team_names is None:
        team_names = [f"Airline {L}" for L in TEAM_LETTERS]

    if len(team_names) != _NUM_TEAMS:
        raise ValueError(
            f"Exactly {_NUM_TEAMS} team names are required (got {len(team_names)}). "
            f"The case defines {_NUM_TEAMS} airlines (A–F)."
        )

    root = Path(root_dir)
    sim_dir = root / simulation_id

    if sim_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Simulation '{simulation_id}' already exists at {sim_dir}"
        )

    sim_dir.mkdir(parents=True, exist_ok=True)
    now = _utc_now()

    # ── 1) simulation.csv ──────────────────────────────────────────
    simulation_rows = [
        {
            "simulation_id": simulation_id,
            "name": simulation_name,
            "status": "CREATED",
            "current_round": "0",
            "total_rounds": str(total_rounds),
            "created_at_utc": now,
            "updated_at_utc": now,
        }
    ]

    # ── 2) parameters.csv  (key-value, Case Appendix) ─────────────
    parameter_rows = _build_parameter_rows()

    # ── 3) teams.csv  (6 airlines with baselines, Case Appendix) ──
    #   Strategic Baseline (Round 0 Positioning) — differentiated per team.
    team_rows: list[dict[str, Any]] = []
    for i, letter in enumerate(TEAM_LETTERS):
        bl = TEAM_BASELINES[letter]
        team_rows.append({
            "simulation_id":            simulation_id,
            "team_id":                  letter,
            "team_name":                team_names[i],
            "is_active":                "1",
            "baseline_passengers":      str(bl["baseline_passengers"]),
            "baseline_volume_share":    str(bl["baseline_volume_share"]),
            "baseline_profit_millions": str(bl["baseline_profit_millions"]),
            "baseline_profit_share":    str(bl["baseline_profit_share"]),
            "variable_cost_per_passenger": str(bl["variable_cost_per_pax"]),
            "baseline_flights_per_day": str(bl["baseline_flights_per_day"]),
            "baseline_pricing_posture": bl["baseline_pricing_posture"],
            "baseline_branding_level":  bl["baseline_branding"],
            "baseline_product_strategy": bl["baseline_product"],
            "baseline_csi":             str(bl["baseline_csi"]),
            "baseline_oei":             str(bl["baseline_oei"]),
            "created_at_utc":           now,
        })

    # ── users.csv  (admin account) ─────────────────────────────────
    user_rows = [
        {
            "simulation_id": simulation_id,
            "user_id":       "U_ADMIN",
            "username":      "admin",
            "role":          "ADMIN",
            "team_id":       "",
            "password_hash": "",
            "is_locked":     "0",
            "created_at_utc": now,
        }
    ]

    # ── routes.csv (JFK–BOS corridor, case narrative) ──────────────
    route_rows = [
        {
            "simulation_id": simulation_id,
            "route_id":      "R1",
            "origin":        "JFK",
            "destination":   "BOS",
            "distance_miles": "187",
            "is_active":     "1",
            "created_at_utc": now,
        }
    ]

    # ── airplane_types.csv  (single type per case) ─────────────────
    airplane_rows = [
        {
            "simulation_id":   simulation_id,
            "airplane_type_id": "A1",
            "name":            "Standard",
            "seats_per_flight": str(SEATS_PER_FLIGHT),   # Case Appendix: 200
            "max_flights_per_day": "5",                  # Case Appendix: 0–5
            "created_at_utc":  now,
        }
    ]

    # ── 4) rounds.csv  (all rounds as PLANNED) ────────────────────
    round_rows = [
        {
            "simulation_id": simulation_id,
            "round_number":  str(rn),
            "status":        "PLANNED",
            "opened_at_utc": "",
            "closed_at_utc": "",
        }
        for rn in range(1, total_rounds + 1)
    ]

    # ── 5) decisions.csv  (Round 1 baseline decisions) ─────────────
    #   Strategic Baseline (Round 0 Positioning) — pre-populate round 1
    #   with each team's archetype decisions so the Team View starts
    #   pre-filled and the simulation begins with strategic asymmetry.
    decision_rows: list[dict[str, Any]] = []
    for letter in TEAM_LETTERS:
        bl = TEAM_BASELINES[letter]
        posture = bl["baseline_pricing_posture"]
        decision_rows.append({
            "simulation_id":   simulation_id,
            "round_number":    "1",
            "team_id":         letter,
            "flights_per_day": str(bl["baseline_flights_per_day"]),
            "price_business":  str(FARES[posture]["business"]),
            "price_leisure":   str(FARES[posture]["leisure"]),
            "branding_level":  bl["baseline_branding"],
            "product_strategy": bl["baseline_product"],
            "submitted_at_utc": now,
        })

    # ── 6) round_results_team.csv  (Round 0 baseline snapshot) ─────
    #   Passengers & profit match Case Appendix exactly.
    #   Costs are derived from baseline data; revenue = profit + total_cost.
    #   CSI & OEI start at 100.0 (neutral index baseline).
    baseline_team_results: list[dict[str, Any]] = []
    for letter in TEAM_LETTERS:
        bl = TEAM_BASELINES[letter]
        pax           = bl["baseline_passengers"]
        profit        = bl["baseline_profit_millions"] * 1_000_000
        vcpp          = bl["variable_cost_per_pax"]
        fpd           = bl["baseline_flights_per_day"]

        monthly_flights = fpd * DAYS_PER_MONTH
        capacity        = monthly_flights * SEATS_PER_FLIGHT

        var_cost      = pax * vcpp
        fix_cost      = monthly_flights * FIXED_COST_PER_FLIGHT
        brand_cost    = BRANDING_COSTS[bl["baseline_branding"]]
        prod_cost     = PRODUCT_COSTS[bl["baseline_product"]]
        total_cost    = var_cost + fix_cost + brand_cost + prod_cost
        revenue       = profit + total_cost   # derive to stay consistent

        load_factor   = pax / capacity if capacity > 0 else 0.0
        avg_rev       = revenue / monthly_flights if monthly_flights else 0.0
        avg_cost      = total_cost / monthly_flights if monthly_flights else 0.0
        avg_prof      = profit / monthly_flights if monthly_flights else 0.0

        baseline_team_results.append({
            "simulation_id":        simulation_id,
            "round_number":         "0",
            "team_id":              letter,
            "passengers":           str(pax),
            "revenue":              str(round(revenue, 2)),
            "variable_cost":        str(round(var_cost, 2)),
            "fixed_cost":           str(round(fix_cost, 2)),
            "branding_cost":        str(round(brand_cost, 2)),
            "product_cost":         str(round(prod_cost, 2)),
            "total_cost":           str(round(total_cost, 2)),
            "profit":               str(int(profit)),
            "market_share_volume":  str(bl["baseline_volume_share"]),
            "market_share_profit":  str(bl["baseline_profit_share"]),
            "load_factor":          str(round(load_factor, 4)),
            "avg_revenue_per_flight": str(round(avg_rev, 2)),
            "avg_cost_per_flight":  str(round(avg_cost, 2)),
            "avg_profit_per_flight": str(round(avg_prof, 2)),
            "price_business":       str(FARES[bl["baseline_pricing_posture"]]["business"]),
            "price_leisure":        str(FARES[bl["baseline_pricing_posture"]]["leisure"]),
            "csi":                  str(bl["baseline_csi"]),
            "oei":                  str(bl["baseline_oei"]),
            "created_at_utc":       now,
        })

    # ── 7) round_results_market.csv  (Round 0 baseline) ───────────
    mkt_total_rev  = sum(float(r["revenue"])     for r in baseline_team_results)
    mkt_total_cost = sum(float(r["total_cost"])  for r in baseline_team_results)
    mkt_total_prof = sum(float(r["profit"])      for r in baseline_team_results)
    baseline_market_results = [
        {
            "simulation_id":   simulation_id,
            "round_number":    "0",
            "total_demand":    str(TOTAL_DEMAND),
            "total_passengers": str(TOTAL_DEMAND),   # baseline: all demand served
            "total_revenue":   str(round(mkt_total_rev, 2)),
            "total_cost":      str(round(mkt_total_cost, 2)),
            "total_profit":    str(round(mkt_total_prof, 2)),
            "created_at_utc":  now,
        }
    ]

    # ── admin_actions.csv / log.csv ────────────────────────────────
    detail_msg = (
        f"Created simulation '{simulation_name}' "
        f"with {_NUM_TEAMS} airlines and {total_rounds} rounds"
    )
    admin_rows = [
        {
            "event_id":       "E1",
            "simulation_id":  simulation_id,
            "admin_user_id":  "U_ADMIN",
            "action":         "SETUP_SIMULATION",
            "details":        detail_msg,
            "event_at_utc":   now,
        }
    ]
    log_rows = [
        {
            "event_id":       "E1",
            "simulation_id":  simulation_id,
            "actor_user_id":  "U_ADMIN",
            "action":         "SETUP_SIMULATION",
            "details":        detail_msg,
            "event_at_utc":   now,
        }
    ]

    # ── Assemble seed data ─────────────────────────────────────────
    seed_data: dict[str, list[dict[str, Any]]] = {
        "simulation.csv":          simulation_rows,
        "parameters.csv":          parameter_rows,
        "teams.csv":               team_rows,
        "users.csv":               user_rows,
        "routes.csv":              route_rows,
        "airplane_types.csv":      airplane_rows,
        "rounds.csv":              round_rows,
        "decisions.csv":           decision_rows,
        "round_results_team.csv":  baseline_team_results,
        "round_results_market.csv": baseline_market_results,
        "login_log.csv":           [],
        "admin_actions.csv":       admin_rows,
        "log.csv":                 log_rows,
    }

    # ── Write all CSVs through csv_manager (storage-agnostic) ────
    for csv_name, headers in CSV_SCHEMAS.items():
        _cm_write_csv(
            simulation_id,
            csv_name,
            fieldnames=headers,
            rows=seed_data.get(csv_name, []),
        )

    return sim_dir


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize airline simulation with Case Appendix data"
    )
    parser.add_argument("simulation_id", help="Unique simulation identifier")
    parser.add_argument(
        "--name",
        default="Airline Simulation",
        help="Simulation display name",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Total number of monthly rounds (default: 3)",
    )
    parser.add_argument(
        "--teams",
        nargs="+",
        default=[f"Airline {L}" for L in "ABCDEF"],
        help="List of 6 team display names",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("simulation/simulations"),
        help="Root simulations directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing simulation folder",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_cli_args()
    simulation_path = setup_simulation(
        simulation_id=args.simulation_id,
        simulation_name=args.name,
        total_rounds=args.rounds,
        team_names=args.teams,
        root_dir=args.root,
        overwrite=args.overwrite,
    )
    print(f"Simulation initialized at: {simulation_path}")


if __name__ == "__main__":
    main()
