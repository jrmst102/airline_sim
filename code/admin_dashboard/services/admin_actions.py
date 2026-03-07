"""
Admin Actions – thin wrappers around existing simulation modules.
==================================================================
Each function calls the corresponding simulation module and returns
a result dict with ``success`` (bool) and ``message`` (str).

All data I/O is handled by the modules themselves via the centralised
CSV manager, which routes through DigitalOcean Spaces (or local
filesystem fallback).
"""

from __future__ import annotations

import logging
import traceback

logger = logging.getLogger(__name__)


def action_setup(
    simulation_id: str,
    simulation_name: str = "Airline Simulation",
    total_rounds: int = 3,
) -> dict:
    """Set up (initialise) a simulation with full user accounts."""
    try:
        from app.modules.simulation_management import (
            create_simulation,
            get_simulation,
            remove_simulation,
        )
        from app.data.csv_manager import csv_exists, read_csv_rows

        # Preserve existing password hashes before re-setup
        existing_hashes: dict[str, str] = {}
        existing = get_simulation(simulation_id)
        if existing:
            if csv_exists(simulation_id, "users.csv"):
                for row in read_csv_rows(simulation_id, "users.csv"):
                    uname = row.get("username", "").strip()
                    phash = row.get("password_hash", "").strip()
                    if uname and phash:
                        existing_hashes[uname.lower()] = phash
            remove_simulation(simulation_id)

        result = create_simulation(
            simulation_id=simulation_id,
            name=simulation_name,
            total_rounds=total_rounds,
            auto_create_teams=True,
        )

        # Restore previously existing password hashes
        if existing_hashes and csv_exists(simulation_id, "users.csv"):
            from app.data.csv_manager import write_csv
            rows = read_csv_rows(simulation_id, "users.csv")
            changed = False
            for row in rows:
                uname = row.get("username", "").strip().lower()
                if uname in existing_hashes:
                    row["password_hash"] = existing_hashes[uname]
                    changed = True
            if changed:
                from app.modules.simulation_management import USERS_CSV_FIELDS
                write_csv(simulation_id, "users.csv", USERS_CSV_FIELDS, rows)

        return {
            "success": True,
            "message": (
                f"Setup complete \u2014 simulation '{simulation_id}' initialised "
                f"with {total_rounds} rounds."
            ),
        }
    except Exception as exc:
        logger.exception("Setup failed")
        return {"success": False, "message": f"Setup failed: {exc}"}


def action_start(
    simulation_id: str,
    admin_user_id: str = "U_ADMIN",
) -> dict:
    """Start a simulation (transition CREATED → STARTED)."""
    try:
        from app.modules.start_simulation import start_simulation

        result = start_simulation(
            simulation_id=simulation_id,
            admin_user_id=admin_user_id,
        )
        return {
            "success": True,
            "message": (
                f"Simulation started — now in round {result.current_round}."
            ),
        }
    except Exception as exc:
        logger.exception("Start failed")
        return {"success": False, "message": f"Start failed: {exc}"}


def action_end(
    simulation_id: str,
    admin_user_id: str = "U_ADMIN",
) -> dict:
    """End a simulation (transition → ENDED)."""
    try:
        from app.modules.end_simulation import end_simulation

        result = end_simulation(
            simulation_id=simulation_id,
            admin_user_id=admin_user_id,
        )
        return {
            "success": True,
            "message": (
                f"Simulation ended at round {result.current_round}. "
                f"Closed {result.closed_rounds} round(s), "
                f"locked {result.locked_rounds} round(s)."
            ),
        }
    except Exception as exc:
        logger.exception("End failed")
        return {"success": False, "message": f"End failed: {exc}"}


def action_move_next_round(
    simulation_id: str,
    admin_user_id: str = "U_ADMIN",
) -> dict:
    """Process the current round and advance to the next one."""
    try:
        from app.modules.move_next_round import move_next_round

        result = move_next_round(
            simulation_id=simulation_id,
            admin_user_id=admin_user_id,
        )
        return {
            "success": True,
            "message": (
                f"Round {result.closed_round} processed — "
                f"{result.processed_team_count} team(s) scored. "
                + (
                    f"Now in round {result.opened_round}."
                    if result.opened_round
                    else "Simulation complete."
                )
            ),
        }
    except Exception as exc:
        logger.exception("Move next round failed")
        return {"success": False, "message": f"Move next round failed: {exc}"}


def action_undo(
    simulation_id: str,
    admin_user_id: str = "U_ADMIN",
) -> dict:
    """Undo the last round transition."""
    try:
        from app.modules.undo_round import undo_round

        result = undo_round(
            simulation_id=simulation_id,
            admin_user_id=admin_user_id,
        )
        return {
            "success": True,
            "message": (
                f"Undo successful — round {result.reopened_round} reopened. "
                f"Simulation status: {result.simulation_status}."
            ),
        }
    except Exception as exc:
        logger.exception("Undo failed")
        return {"success": False, "message": f"Undo failed: {exc}"}
