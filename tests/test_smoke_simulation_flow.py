"""
Smoke test – full simulation lifecycle
=======================================
Uses the 5-airline default setup (team IDs A–E) with numeric price
decisions (price_business, price_leisure, branding_level, product_strategy).
"""

import csv
import tempfile
import unittest
from pathlib import Path

from app.modules.end_simulation import end_simulation
from app.modules.enter_decisions import enter_decision
from app.modules.move_next_round import move_next_round
from app.modules.setup_simulation import setup_simulation
from app.modules.start_simulation import start_simulation
from app.modules.undo_round import undo_round


TEAM_NAMES = [
    "Airline A",
    "Airline B",
    "Airline C",
    "Airline D",
    "Airline E",
]
TEAM_IDS = ["A", "B", "C", "D", "E"]


def _read_single_row(path: Path) -> dict[str, str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _enter_round_decisions(
    simulation_id: str,
    root: Path,
    prices: list[tuple[float, float]] | None = None,
) -> None:
    """Enter one decision per active team. Uses sensible defaults."""
    if prices is None:
        # Default to Match-level prices for all teams
        prices = [(360.0, 180.0)] * len(TEAM_IDS)
    for tid, (biz_price, lei_price) in zip(TEAM_IDS, prices):
        enter_decision(
            simulation_id=simulation_id,
            team_id=tid,
            flights_per_day=3,
            price_business=biz_price,
            price_leisure=lei_price,
            branding_level="Medium",
            product_strategy="Low",
            root_dir=root,
        )


class SmokeSimulationFlowTest(unittest.TestCase):
    def test_smoke_simulation_lifecycle_flow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="airline_smoke_") as tmp_dir:
            root = Path(tmp_dir)
            simulation_id = "sim_smoke"

            # ── Setup ─────────────────────────────────────────────
            setup_simulation(
                simulation_id=simulation_id,
                simulation_name="Smoke Test",
                total_rounds=3,
                num_teams=len(TEAM_IDS),
                team_names=TEAM_NAMES,
                root_dir=root,
                overwrite=False,
            )

            # ── Start ─────────────────────────────────────────────
            start_result = start_simulation(
                simulation_id=simulation_id, root_dir=root,
            )

            # ── Round 1 decisions & advance ───────────────────────
            _enter_round_decisions(simulation_id, root)
            move_result_round_1 = move_next_round(
                simulation_id=simulation_id, root_dir=root,
            )

            # ── Round 2 decisions & advance ───────────────────────
            _enter_round_decisions(
                simulation_id,
                root,
                prices=[
                    (450.0, 220.0),   # A – Premium level
                    (360.0, 180.0),   # B – Match level
                    (290.0, 140.0),   # C – Discount level
                    (360.0, 180.0),   # D – Match level
                    (290.0, 140.0),   # E – Discount level
                ],
            )
            move_result_round_2 = move_next_round(
                simulation_id=simulation_id, root_dir=root,
            )

            # ── Undo round 2, then end ────────────────────────────
            undo_result = undo_round(
                simulation_id=simulation_id, root_dir=root,
            )
            end_result = end_simulation(
                simulation_id=simulation_id, root_dir=root,
            )

            # ── Assertions ────────────────────────────────────────
            simulation_dir = root / simulation_id
            simulation_row = _read_single_row(simulation_dir / "simulation.csv")
            rounds_rows = _read_rows(simulation_dir / "rounds.csv")
            team_results_rows = _read_rows(simulation_dir / "round_results_team.csv")
            market_results_rows = _read_rows(simulation_dir / "round_results_market.csv")
            admin_actions_rows = _read_rows(simulation_dir / "admin_actions.csv")
            log_rows = _read_rows(simulation_dir / "log.csv")

            open_rounds = [
                row for row in rounds_rows if row.get("status") == "OPEN"
            ]

            self.assertEqual(start_result.status, "STARTED")
            self.assertEqual(move_result_round_1.closed_round, 1)
            self.assertEqual(move_result_round_2.closed_round, 2)
            self.assertEqual(undo_result.reopened_round, 2)
            self.assertEqual(end_result.status, "ENDED")

            self.assertEqual(simulation_row["status"], "ENDED")
            self.assertEqual(simulation_row["current_round"], "2")
            self.assertEqual(len(open_rounds), 0)

            # After undo of round 2, remaining results:
            #   round 0 baseline (5 teams) + round 1 (5 teams) = 10
            self.assertEqual(len(team_results_rows), len(TEAM_IDS) * 2)
            # market: round 0 baseline + round 1 = 2
            self.assertEqual(len(market_results_rows), 2)

            # Verify new column names exist in team results
            for tr_row in team_results_rows:
                self.assertIn("passengers", tr_row)
                self.assertIn("revenue", tr_row)
                self.assertIn("total_cost", tr_row)
                self.assertIn("profit", tr_row)
                self.assertIn("load_factor", tr_row)
                self.assertIn("market_share_volume", tr_row)

            # Verify new column names in market results
            for mr_row in market_results_rows:
                self.assertIn("total_demand", mr_row)
                self.assertIn("total_passengers", mr_row)
                self.assertIn("total_revenue", mr_row)
                self.assertIn("total_profit", mr_row)

            self.assertGreaterEqual(len(admin_actions_rows), 6)
            self.assertGreaterEqual(len(log_rows), 6)


if __name__ == "__main__":
    unittest.main()
