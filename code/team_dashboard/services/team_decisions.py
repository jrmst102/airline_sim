"""
Team Decisions – load defaults, save/upsert, and undo decisions.
==================================================================
Reads and writes ``decisions.csv`` through the Spaces-backed CSV
manager.  All writes are team-scoped: only the logged-in team's row
for the current round is touched; other teams are never overwritten.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.data.csv_manager import csv_exists, load_csv, read_csv_rows, write_csv

logger = logging.getLogger(__name__)

# Valid decision enums (must match enter_decisions.py)
VALID_BRANDING = ("Low", "Medium", "High")
VALID_PRODUCTS = ("High", "Medium", "Low")
MIN_PRICE = 50.0
MAX_PRICE = 1000.0


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Simulation state ──────────────────────────────────────────────────

def get_simulation_state(simulation_id: str) -> dict:
    """Return simulation state: is_created, is_started, is_ended, etc."""
    if not csv_exists(simulation_id, "simulation.csv"):
        return {
            "is_created": False,
            "is_started": False,
            "is_ended": False,
            "current_round": 0,
            "total_rounds": 0,
            "status": "NOT FOUND",
            "name": "",
            "updated_at_utc": "",
        }

    _, rows = load_csv(simulation_id, "simulation.csv")
    if not rows:
        return {
            "is_created": False,
            "is_started": False,
            "is_ended": False,
            "current_round": 0,
            "total_rounds": 0,
            "status": "CORRUPT",
            "name": "",
            "updated_at_utc": "",
        }

    row = rows[0]
    status = row.get("status", "UNKNOWN")
    return {
        "is_created": status in ("CREATED", "STARTED", "ENDED"),
        "is_started": status in ("STARTED", "ENDED"),
        "is_ended": status == "ENDED",
        "current_round": _int(row.get("current_round", "0")),
        "total_rounds": _int(row.get("total_rounds", "0")),
        "status": status,
        "name": row.get("name", ""),
        "updated_at_utc": row.get("updated_at_utc", ""),
    }


# ── Decision defaults ────────────────────────────────────────────────

def get_decision_defaults(
    simulation_id: str,
    team_id: str,
    current_round: int,
    is_started: bool,
) -> dict:
    """Return the decision form default values for a team.

    Logic:
      - If started and current_round > 1: use previous round's decisions.
      - Else: use round-1 baseline decisions (seeded by setup).
      - If the team already has a saved decision for the current round,
        use that instead (so refreshing doesn't lose work).
    """
    defaults = {
        "flights_per_day": 3,
        "price_business": 360,
        "price_leisure": 180,
        "branding_level": "Medium",
        "product_strategy": "Medium",
    }

    if not csv_exists(simulation_id, "decisions.csv"):
        return defaults

    all_decisions = read_csv_rows(simulation_id, "decisions.csv")
    team_decisions = [
        r for r in all_decisions if r.get("team_id") == team_id
    ]

    if not team_decisions:
        return defaults

    # Check if there's already a saved decision for the current round
    current_saved = [
        r for r in team_decisions
        if _int(r.get("round_number", "0")) == current_round
    ]
    if current_saved:
        row = current_saved[-1]
        return {
            "flights_per_day": _int(row.get("flights_per_day", "3")),
            "price_business": _float(row.get("price_business", "360")),
            "price_leisure": _float(row.get("price_leisure", "180")),
            "branding_level": row.get("branding_level", "Medium"),
            "product_strategy": row.get("product_strategy", "Medium"),
        }

    # If started and round > 1, use previous round
    if is_started and current_round > 1:
        prev_round = current_round - 1
        prev_decisions = [
            r for r in team_decisions
            if _int(r.get("round_number", "0")) == prev_round
        ]
        if prev_decisions:
            row = prev_decisions[-1]
            return {
                "flights_per_day": _int(row.get("flights_per_day", "3")),
                "price_business": _float(row.get("price_business", "360")),
                "price_leisure": _float(row.get("price_leisure", "180")),
                "branding_level": row.get("branding_level", "Medium"),
                "product_strategy": row.get("product_strategy", "Medium"),
            }

    # Fall back to round 1 (initial/baseline) decisions
    r1_decisions = [
        r for r in team_decisions
        if _int(r.get("round_number", "0")) == 1
    ]
    if r1_decisions:
        row = r1_decisions[-1]
        return {
            "flights_per_day": _int(row.get("flights_per_day", "3")),
            "price_business": _float(row.get("price_business", "360")),
            "price_leisure": _float(row.get("price_leisure", "180")),
            "branding_level": row.get("branding_level", "Medium"),
            "product_strategy": row.get("product_strategy", "Medium"),
        }

    return defaults


# ── Save (upsert) ────────────────────────────────────────────────────

def save_decision(
    simulation_id: str,
    team_id: str,
    flights_per_day: int,
    price_business: float,
    price_leisure: float,
    branding_level: str,
    product_strategy: str,
) -> dict:
    """Save (upsert) a team's decision for the current open round.

    Validates simulation state, input ranges, and writes atomically.
    Only the logged-in team's row is touched.
    """
    # Validate simulation state
    state = get_simulation_state(simulation_id)
    if not state["is_created"]:
        return {"success": False, "message": "Simulation not created yet."}
    if state["is_ended"]:
        return {"success": False, "message": "Simulation has ended. Cannot save decisions."}
    if not state["is_started"]:
        return {"success": False, "message": "Simulation not started yet. Cannot save decisions."}

    current_round = state["current_round"]

    # Validate inputs
    errors = []
    if flights_per_day < 0 or flights_per_day > 5:
        errors.append("Flights per day must be 0–5.")
    if price_business < MIN_PRICE or price_business > MAX_PRICE:
        errors.append(f"Business price must be ${MIN_PRICE:.0f}–${MAX_PRICE:.0f}.")
    if price_leisure < MIN_PRICE or price_leisure > MAX_PRICE:
        errors.append(f"Leisure price must be ${MIN_PRICE:.0f}–${MAX_PRICE:.0f}.")
    if branding_level not in VALID_BRANDING:
        errors.append(f"Branding must be one of: {', '.join(VALID_BRANDING)}.")
    if product_strategy not in VALID_PRODUCTS:
        errors.append(f"Product strategy must be one of: {', '.join(VALID_PRODUCTS)}.")
    if errors:
        return {"success": False, "message": " ".join(errors)}

    try:
        fieldnames, rows = load_csv(simulation_id, "decisions.csv")
    except FileNotFoundError:
        return {"success": False, "message": "Decisions file not found."}

    now = _utc_now()
    new_row = {
        "simulation_id": simulation_id,
        "round_number": str(current_round),
        "team_id": team_id,
        "flights_per_day": str(flights_per_day),
        "price_business": str(price_business),
        "price_leisure": str(price_leisure),
        "branding_level": branding_level,
        "product_strategy": product_strategy,
        "submitted_at_utc": now,
    }

    # Upsert: find existing row for this team + round
    target_idx = -1
    for i, row in enumerate(rows):
        if (
            row.get("team_id") == team_id
            and _int(row.get("round_number", "0")) == current_round
        ):
            target_idx = i
            break

    was_update = target_idx >= 0
    if was_update:
        rows[target_idx] = new_row
    else:
        rows.append(new_row)

    try:
        write_csv(simulation_id, "decisions.csv", fieldnames, rows)
    except Exception as exc:
        logger.exception("Failed to write decisions")
        return {"success": False, "message": f"Save failed: {exc}"}

    return {
        "success": True,
        "message": f"Decisions saved for Round {current_round}.",
        "round": current_round,
    }


# ── Undo ─────────────────────────────────────────────────────────────

def undo_decision(
    simulation_id: str,
    team_id: str,
) -> dict:
    """Remove the logged-in team's decision for the current round.

    After undo, the form will revert to previous-round defaults
    (or initial defaults for round 1).
    """
    state = get_simulation_state(simulation_id)
    if not state["is_created"]:
        return {"success": False, "message": "Simulation not created yet."}
    if state["is_ended"]:
        return {"success": False, "message": "Simulation has ended. Cannot undo."}
    if not state["is_started"]:
        return {"success": False, "message": "Simulation not started yet. Cannot undo."}

    current_round = state["current_round"]

    try:
        fieldnames, rows = load_csv(simulation_id, "decisions.csv")
    except FileNotFoundError:
        return {"success": False, "message": "Decisions file not found."}

    # Find and remove this team's decision for the current round
    original_len = len(rows)
    rows = [
        row for row in rows
        if not (
            row.get("team_id") == team_id
            and _int(row.get("round_number", "0")) == current_round
        )
    ]

    if len(rows) == original_len:
        return {"success": False, "message": "No saved decision to undo for this round."}

    try:
        write_csv(simulation_id, "decisions.csv", fieldnames, rows)
    except Exception as exc:
        logger.exception("Failed to write decisions after undo")
        return {"success": False, "message": f"Undo failed: {exc}"}

    return {
        "success": True,
        "message": f"Decision for Round {current_round} undone. Form reset to defaults.",
    }


# ── Past decisions ───────────────────────────────────────────────────

def get_past_decisions(
    simulation_id: str,
    team_id: str,
    current_round: int,
    is_started: bool,
) -> list[dict]:
    """Return the team's historical decisions for completed rounds.

    Only returns data if simulation is started and current_round > 1.
    Decisions for the current round are excluded (those are "in progress").
    """
    if not is_started or current_round <= 1:
        return []

    if not csv_exists(simulation_id, "decisions.csv"):
        return []

    all_decisions = read_csv_rows(simulation_id, "decisions.csv")
    past = [
        {
            "round_number": _int(r.get("round_number", "0")),
            "flights_per_day": _int(r.get("flights_per_day", "0")),
            "price_business": _float(r.get("price_business", "0")),
            "price_leisure": _float(r.get("price_leisure", "0")),
            "branding_level": r.get("branding_level", ""),
            "product_strategy": r.get("product_strategy", ""),
        }
        for r in all_decisions
        if r.get("team_id") == team_id
        and _int(r.get("round_number", "0")) < current_round
    ]

    return sorted(past, key=lambda d: d["round_number"])
