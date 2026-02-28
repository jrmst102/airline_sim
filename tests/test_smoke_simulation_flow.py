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


def _read_single_row(path: Path) -> dict[str, str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class SmokeSimulationFlowTest(unittest.TestCase):
    def test_smoke_simulation_lifecycle_flow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="airline_smoke_") as tmp_dir:
            root = Path(tmp_dir)
            simulation_id = "sim_smoke"

            setup_simulation(
                simulation_id=simulation_id,
                simulation_name="Smoke Test",
                total_rounds=3,
                team_names=["Team Alpha", "Team Bravo"],
                root_dir=root,
                overwrite=False,
            )

            start_result = start_simulation(simulation_id=simulation_id, root_dir=root)

            enter_decision(
                simulation_id=simulation_id,
                team_id="T1",
                flights_per_day=6,
                price_premium=220,
                price_economy=160,
                brand_investment=1000,
                root_dir=root,
            )
            enter_decision(
                simulation_id=simulation_id,
                team_id="T2",
                flights_per_day=5,
                price_premium=210,
                price_economy=150,
                brand_investment=1200,
                root_dir=root,
            )

            move_result_round_1 = move_next_round(simulation_id=simulation_id, root_dir=root)

            enter_decision(
                simulation_id=simulation_id,
                team_id="T1",
                flights_per_day=7,
                price_premium=230,
                price_economy=165,
                brand_investment=1100,
                root_dir=root,
            )
            enter_decision(
                simulation_id=simulation_id,
                team_id="T2",
                flights_per_day=6,
                price_premium=215,
                price_economy=155,
                brand_investment=1300,
                root_dir=root,
            )

            move_result_round_2 = move_next_round(simulation_id=simulation_id, root_dir=root)
            undo_result = undo_round(simulation_id=simulation_id, root_dir=root)
            end_result = end_simulation(simulation_id=simulation_id, root_dir=root)

            simulation_dir = root / simulation_id
            simulation_row = _read_single_row(simulation_dir / "simulation.csv")
            rounds_rows = _read_rows(simulation_dir / "rounds.csv")
            team_results_rows = _read_rows(simulation_dir / "round_results_team.csv")
            market_results_rows = _read_rows(simulation_dir / "round_results_market.csv")
            admin_actions_rows = _read_rows(simulation_dir / "admin_actions.csv")
            log_rows = _read_rows(simulation_dir / "log.csv")

            open_rounds = [row for row in rounds_rows if row.get("status") == "OPEN"]

            self.assertEqual(start_result.status, "STARTED")
            self.assertEqual(move_result_round_1.closed_round, 1)
            self.assertEqual(move_result_round_2.closed_round, 2)
            self.assertEqual(undo_result.reopened_round, 2)
            self.assertEqual(end_result.status, "ENDED")

            self.assertEqual(simulation_row["status"], "ENDED")
            self.assertEqual(simulation_row["current_round"], "2")
            self.assertEqual(len(open_rounds), 0)

            self.assertEqual(len(team_results_rows), 2)
            self.assertEqual(len(market_results_rows), 1)
            self.assertGreaterEqual(len(admin_actions_rows), 6)
            self.assertGreaterEqual(len(log_rows), 6)


if __name__ == "__main__":
    unittest.main()
