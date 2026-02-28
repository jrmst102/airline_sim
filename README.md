# airline_sim
Airlines simulation for the Competitive Strategy course.

## Overview

This repository provides:

- CSV-backed simulation state and lifecycle modules
- Core round/state/market computation models
- Streamlit UI views for admin, team, and dashboard workflows

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python -m streamlit run app/ui/dashboard.py
```

Then in the UI:

1. Keep `sim_001` as the simulation ID.
2. Use **Setup** to initialize teams/rounds.
3. Use **Start** to begin.
4. Enter decisions and click **Move Next** each round.
5. Use **Display Results** and **End** when complete.

## Setup

From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run the Simulation

Choose one of the following approaches.

### Option 1: CLI only

Use the module CLIs directly for full simulation lifecycle control.

1. **Initialize a simulation**

```bash
.venv/bin/python -m app.modules.setup_simulation sim_001 --name "Airline Simulation" --rounds 8 --teams "Team Alpha" "Team Bravo"
```

2. **Start the simulation**

```bash
.venv/bin/python -m app.modules.start_simulation sim_001 --admin-user-id U_ADMIN
```

3. **Enter decisions for each team (repeat as needed)**

```bash
.venv/bin/python -m app.modules.enter_decisions sim_001 --team-id T1 --flights-per-day 6 --price-premium 220 --price-economy 160 --brand-investment 1000
.venv/bin/python -m app.modules.enter_decisions sim_001 --team-id T2 --flights-per-day 6 --price-premium 215 --price-economy 155 --brand-investment 900
```

4. **Advance to next round**

```bash
.venv/bin/python -m app.modules.move_next_round sim_001 --admin-user-id U_ADMIN
```

5. **Inspect status and results**

```bash
.venv/bin/python -m app.modules.check_simulation_status sim_001
.venv/bin/python -m app.modules.display_results sim_001 --section both
```

6. **End the simulation when finished**

```bash
.venv/bin/python -m app.modules.end_simulation sim_001 --admin-user-id U_ADMIN
```

### Option 2: GUI only

1. **Launch Streamlit dashboard**

```bash
.venv/bin/python -m streamlit run app/ui/dashboard.py
```

2. **Open the local URL shown by Streamlit** (usually `http://localhost:8501`).

3. **Run the lifecycle from the UI**
	- Use **Setup** to initialize simulation/team data.
	- Use **Start** to begin round processing.
	- Use **Enter Decision** (team workflow) to submit team decisions.
	- Use **Move Next** to compute and advance rounds.
	- Use **Display Results** / insights to review outcomes.
	- Use **End** when the simulation is complete.

## CLI Usage

Run the command router:

```bash
.venv/bin/python main.py --help
```

Example:

```bash
.venv/bin/python main.py display-log sim_001
```

### Common Commands

| Task | Command |
| --- | --- |
| Show all commands | `.venv/bin/python main.py --help` |
| Display log | `.venv/bin/python main.py display-log sim_001` |

### Team Commands

| Task | Command |
| --- | --- |
| Team decision history summary | `.venv/bin/python main.py historical-decisions-team sim_001` |
| Team decision history (custom root) | `.venv/bin/python main.py historical-decisions-team sim_001 --root simulations` |

Current CLI routes are limited to `display-log` and `historical-decisions-team`; lifecycle and decision-entry workflows are available through the Streamlit UI.

### Planned CLI Expansion

To align CLI capabilities with current UI workflows, the next commands to expose are:

| Planned command | Purpose |
| --- | --- |
| `check-status` | View simulation status and current round/state |
| `setup-simulation` | Initialize a simulation with rounds and teams |
| `start-simulation` | Move simulation from setup to active play |
| `move-next-round` | Process one round forward |
| `undo-round` | Revert the most recent round transition |
| `end-simulation` | Close simulation and finalize state |
| `display-results` | Show market/team round results |
| `enter-decision` | Submit or update team decisions for an open round |

## UI Usage (Streamlit)

Launch the dashboard UI:

```bash
.venv/bin/python -m streamlit run app/ui/dashboard.py
```

The UI also includes dedicated views in:

- `app/ui/admin_view.py`
- `app/ui/team_view.py`

## UI Messaging Standard

UI text is centralized in `app/ui/components.py`.

- Simulation title: **Airlines**
- Simulation subtitle: **Competitive Strategy Simulation**
- Copyright notice: **Copyright 2026 by Dr. Jose Mendoza**
