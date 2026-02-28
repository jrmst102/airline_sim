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

7. **(Optional) Import decision batch from CSV or Google Sheets**

CSV input:

```bash
.venv/bin/python -m app.modules.import_decisions_batch sim_001 --input-type csv --csv-path decisions_input.csv
```

Google Sheets input (service account credentials required):

```bash
.venv/bin/python -m app.modules.import_decisions_batch sim_001 --input-type google-sheet --spreadsheet-id-or-url "<sheet-id-or-url>" --worksheet Decisions --credentials-json /path/to/service_account.json
```

Expected decision columns: `team_id`, `flights_per_day`, `price_premium`, `price_economy`, `brand_investment`, optional `round_number`.

8. **(Optional) Export results to CSV or Google Sheets**

CSV output:

```bash
.venv/bin/python -m app.modules.export_results_batch sim_001 --section both --output-type csv --output-dir exports
```

Google Sheets output:

```bash
.venv/bin/python -m app.modules.export_results_batch sim_001 --section both --output-type google-sheet --spreadsheet-id-or-url "<sheet-id-or-url>" --worksheet-prefix SimResults --credentials-json /path/to/service_account.json
```

This writes results to worksheets named `SimResults_Market` and `SimResults_Team`.

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

You can run the simulation in two CLI styles:

- **Command router (`main.py`)** for a small set of convenience commands.
- **Module CLIs (`python -m app.modules.<module>`)** for full lifecycle, batch import, and export workflows.

### Router Commands (`main.py`)

Show available router commands:

```bash
.venv/bin/python main.py --help
```

Examples:

```bash
.venv/bin/python main.py display-log sim_001
.venv/bin/python main.py historical-decisions-team sim_001
```

### Module CLI Commands (current)

| Task | Command |
| --- | --- |
| Setup simulation | `.venv/bin/python -m app.modules.setup_simulation sim_001 --name "Airline Simulation" --rounds 8 --teams "Team Alpha" "Team Bravo"` |
| Start simulation | `.venv/bin/python -m app.modules.start_simulation sim_001 --admin-user-id U_ADMIN` |
| Enter decision | `.venv/bin/python -m app.modules.enter_decisions sim_001 --team-id T1 --flights-per-day 6 --price-premium 220 --price-economy 160 --brand-investment 1000` |
| Move to next round | `.venv/bin/python -m app.modules.move_next_round sim_001 --admin-user-id U_ADMIN` |
| Check status | `.venv/bin/python -m app.modules.check_simulation_status sim_001` |
| Display results | `.venv/bin/python -m app.modules.display_results sim_001 --section both` |
| End simulation | `.venv/bin/python -m app.modules.end_simulation sim_001 --admin-user-id U_ADMIN` |
| Import decisions batch (CSV) | `.venv/bin/python -m app.modules.import_decisions_batch sim_001 --input-type csv --csv-path decisions_input.csv` |
| Import decisions batch (Google Sheets) | `.venv/bin/python -m app.modules.import_decisions_batch sim_001 --input-type google-sheet --spreadsheet-id-or-url "<sheet-id-or-url>" --worksheet Decisions --credentials-json /path/to/service_account.json` |
| Export results batch (CSV) | `.venv/bin/python -m app.modules.export_results_batch sim_001 --section both --output-type csv --output-dir exports` |
| Export results batch (Google Sheets) | `.venv/bin/python -m app.modules.export_results_batch sim_001 --section both --output-type google-sheet --spreadsheet-id-or-url "<sheet-id-or-url>" --worksheet-prefix SimResults --credentials-json /path/to/service_account.json` |

### Notes for Google Sheets

- Install dependencies from `requirements.txt` (includes `gspread` and `google-auth`).
- Use a Google service-account JSON key via `--credentials-json`.
- Share the target spreadsheet with the service-account email so it can read/write.


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
