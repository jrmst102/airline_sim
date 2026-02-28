# Tests

## Run the smoke test

From the repository root, run:

```bash
/workspaces/airline_sim/.venv/bin/python -m unittest -v tests/test_smoke_simulation_flow.py
```

## What it validates

The smoke test in `tests/test_smoke_simulation_flow.py` runs an end-to-end lifecycle in an isolated temporary directory:

1. `setup_simulation`
2. `start_simulation`
3. `enter_decision` (two teams)
4. `move_next_round` (twice)
5. `undo_round`
6. `end_simulation`

It then verifies final simulation/round states and key CSV outputs (`round_results_team.csv`, `round_results_market.csv`, `admin_actions.csv`, and `log.csv`).
