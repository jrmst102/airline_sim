# airline_sim

Airlines simulation for the Competitive Strategy course.

## Overview

This repository provides:

- CSV-backed simulation state and lifecycle modules
- Core round/state/market computation models
- Streamlit UI views for admin and team workflows (page-based navigation)
- Standalone FastAPI web dashboard with Plotly.js charts
- DigitalOcean Spaces cloud storage with local filesystem fallback
- Centralised CSV manager routed through the storage abstraction layer
- 32-scenario test suite with dual-layer verification (engine + independent calculator)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then choose how to run:

```bash
# Streamlit admin dashboard (page-based UI)
python run_admin_dashboard.py

# Standalone web dashboard (FastAPI + Plotly.js)
python run_dashboard.py
```

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: `bcrypt`, `boto3`, `gspread`, `google-auth`, `python-dotenv`.

### DigitalOcean Spaces (optional)

For cloud storage, copy `.env.example` to `.env` and fill in your Spaces credentials:

```bash
cp .env.example .env
```

Required environment variables (only when Spaces is enabled):

| Variable | Default |
| --- | --- |
| `SPACES_ACCESS_KEY_ID` | *(required)* |
| `SPACES_SECRET_ACCESS_KEY` | *(required)* |
| `SPACES_REGION` | `sfo3` |
| `SPACES_BUCKET` | `airlines-sim` |
| `SPACES_ENDPOINT` | `https://sfo3.digitaloceanspaces.com` |

If `SPACES_ACCESS_KEY_ID` is **not** set, the system falls back to local filesystem I/O — no cloud dependency is required for development.

## Decision Variables

Each team submits five decisions per round:

| Variable | Values |
| --- | --- |
| `flights_per_day` | `0–5` |
| `price_business` | `$50–$1000` |
| `price_leisure` | `$50–$1000` |
| `branding_level` | `Low`, `Medium`, `High` |
| `product_strategy` | `High`, `Medium`, `Low` |

### Product Strategy Costs (per month)

| Level | Cost |
| --- | --- |
| High | $4,000,000 |
| Medium | $3,000,000 |
| Low | $2,000,000 |

### Branding Costs (per month)

| Level | Cost |
| --- | --- |
| Low | $1,000,000 |
| Medium | $3,000,000 |
| High | $5,000,000 |

## Run the Simulation

Choose one of the following approaches.

### Option 1: CLI only

Use the module CLIs directly for full simulation lifecycle control.

1. **Initialize a simulation**

```bash
python -m app.modules.setup_simulation sim_001 --name "Airline Simulation" --rounds 8 --teams "Team Alpha" "Team Bravo"
```

2. **Start the simulation**

```bash
python -m app.modules.start_simulation sim_001 --admin-user-id U_ADMIN
```

3. **Enter decisions for each team (repeat as needed)**

```bash
python -m app.modules.enter_decisions sim_001 --team-id T1 --flights-per-day 4 --price-business 360 --price-leisure 180 --branding-level Medium --product-strategy High
python -m app.modules.enter_decisions sim_001 --team-id T2 --flights-per-day 3 --price-business 290 --price-leisure 140 --branding-level Low --product-strategy Low
```

4. **Advance to next round**

```bash
python -m app.modules.move_next_round sim_001 --admin-user-id U_ADMIN
```

5. **Inspect status and results**

```bash
python -m app.modules.check_simulation_status sim_001
python -m app.modules.display_results sim_001 --section both
```

6. **End the simulation when finished**

```bash
python -m app.modules.end_simulation sim_001 --admin-user-id U_ADMIN
```

7. **(Optional) Import decision batch from CSV or Google Sheets**

CSV input:

```bash
python -m app.modules.import_decisions_batch sim_001 --input-type csv --csv-path decisions_input.csv
```

Google Sheets input (service account credentials required):

```bash
python -m app.modules.import_decisions_batch sim_001 --input-type google-sheet --spreadsheet-id-or-url "<sheet-id-or-url>" --worksheet Decisions --credentials-json /path/to/service_account.json
```

Expected decision columns: `team_id`, `flights_per_day`, `price_business`, `price_leisure`, `branding_level`, `product_strategy`, optional `round_number`.

8. **(Optional) Export results to CSV or Google Sheets**

CSV output:

```bash
python -m app.modules.export_results_batch sim_001 --section both --output-type csv --output-dir exports
```

Google Sheets output:

```bash
python -m app.modules.export_results_batch sim_001 --section both --output-type google-sheet --spreadsheet-id-or-url "<sheet-id-or-url>" --worksheet-prefix SimResults --credentials-json /path/to/service_account.json
```

This writes results to worksheets named `SimResults_Market` and `SimResults_Team`.

### Option 2: Streamlit GUI (Admin Dashboard)

1. **Launch the admin dashboard**

```bash
python run_admin_dashboard.py              # default: http://0.0.0.0:8501
python run_admin_dashboard.py --port 8502   # custom port
```

2. **Open the local URL shown by Streamlit** (usually `http://localhost:8501`).

3. **Navigate through the page-based UI**
	- **Home** — Choose Admin or Team view.
	- **Setup** — Initialize simulation/team data.
	- **Decisions** — Submit team decisions.
	- **Results** — Review round outcomes and insights.

UI pages live in `app/ui/pages/` (Home, Setup, Decisions, Results).

### Option 3: Web Dashboard (FastAPI)

A standalone web dashboard for viewing simulation results. Uses FastAPI on the backend and Plotly.js for interactive charts. No Streamlit required.

```bash
# From the project root:
python run_dashboard.py                # default: http://0.0.0.0:8000
python run_dashboard.py --port 8050    # custom port
python run_dashboard.py --reload       # auto-reload for development
```

The dashboard displays:
- Current round number and rankings table
- Horizontal bar charts for Revenue, Profit, Load Factor, Market Share, CSI, and OEI
- Auto-refreshes every 60 seconds (or click Refresh manually)
- NYU-themed styling

Dashboard files live in `code/dashboard_web/`:

| File | Purpose |
| --- | --- |
| `code/dashboard_web/app.py` | FastAPI application, routes |
| `code/dashboard_web/dashboard_data.py` | CSV reader, server-side calculations |
| `code/dashboard_web/templates/index.html` | Single-page HTML with Plotly.js |
| `code/dashboard_web/static/styles.css` | NYU-themed CSS |

## CLI Usage

You can run the simulation in two CLI styles:

- **Command router (`main.py`)** for a small set of convenience commands.
- **Module CLIs (`python -m app.modules.<module>`)** for full lifecycle, batch import, and export workflows.

### Router Commands (`main.py`)

Show available router commands:

```bash
python main.py --help
```

Examples:

```bash
python main.py display-log sim_001
python main.py historical-decisions-team sim_001
```

### Module CLI Commands

| Task | Command |
| --- | --- |
| Setup simulation | `python -m app.modules.setup_simulation sim_001 --name "Airline Simulation" --rounds 8 --teams "Team Alpha" "Team Bravo"` |
| Start simulation | `python -m app.modules.start_simulation sim_001 --admin-user-id U_ADMIN` |
| Enter decision | `python -m app.modules.enter_decisions sim_001 --team-id T1 --flights-per-day 4 --price-business 360 --price-leisure 180 --branding-level Medium --product-strategy High` |
| Move to next round | `python -m app.modules.move_next_round sim_001 --admin-user-id U_ADMIN` |
| Check status | `python -m app.modules.check_simulation_status sim_001` |
| Display results | `python -m app.modules.display_results sim_001 --section both` |
| End simulation | `python -m app.modules.end_simulation sim_001 --admin-user-id U_ADMIN` |
| Import decisions (CSV) | `python -m app.modules.import_decisions_batch sim_001 --input-type csv --csv-path decisions_input.csv` |
| Import decisions (Google Sheets) | `python -m app.modules.import_decisions_batch sim_001 --input-type google-sheet --spreadsheet-id-or-url "<id>" --worksheet Decisions --credentials-json creds.json` |
| Export results (CSV) | `python -m app.modules.export_results_batch sim_001 --section both --output-type csv --output-dir exports` |
| Export results (Google Sheets) | `python -m app.modules.export_results_batch sim_001 --section both --output-type google-sheet --spreadsheet-id-or-url "<id>" --worksheet-prefix SimResults --credentials-json creds.json` |

### Notes for Google Sheets

- Install dependencies from `requirements.txt` (includes `gspread` and `google-auth`).
- Use a Google service-account JSON key via `--credentials-json`.
- Share the target spreadsheet with the service-account email so it can read/write.

## UI Usage (Streamlit)

Launch the admin dashboard:

```bash
python run_admin_dashboard.py
```

The UI uses a page-based navigation model with pages in `app/ui/pages/`:

| Page | File | Purpose |
| --- | --- | --- |
| Home | `app/ui/pages/home.py` | Workspace selector (Admin / Team view) |
| Setup | `app/ui/pages/setup.py` | Initialize simulation and teams |
| Decisions | `app/ui/pages/decisions.py` | Submit team decisions |
| Results | `app/ui/pages/results.py` | Display round results and insights |

Supporting UI modules:

- `app/ui/components.py` — Shared UI components, cards, headers, sidebar navigation
- `app/ui/layout.py` — CSS loading and page shell
- `app/ui/team_view.py` — Team decision entry and historical results

## Test Suite

A 32-scenario test suite verifies simulation correctness with dual-layer verification:

1. **Engine-based comparison** — re-computes expected results through the engine's pure functions and compares against actual CSV output.
2. **Independent cross-check** — reimplements all formulas from scratch in `tests/helpers/independent_calculator.py` using only `csv`, `dataclasses`, and `pathlib` (zero `app.*` imports), ensuring formula correctness independently of the engine code.

### Running Tests

```bash
# Run all 32 scenarios
python -m tests.simulation_test_suite

# Save report to file
python -m tests.simulation_test_suite --out ./tests/reports/simulation_test_report.txt

# Stop on first failure
python -m tests.simulation_test_suite --stop-on-fail

# Custom RNG seed
python -m tests.simulation_test_suite --seed 42
```

### Test Helpers

| File | Purpose |
| --- | --- |
| `tests/helpers/scenarios.py` | 32 scenario generators (pricing, branding, product, capacity variations) |
| `tests/helpers/constraints.py` | Reads valid ranges from simulation config |
| `tests/helpers/expected_calculator.py` | Engine-based expected value calculator |
| `tests/helpers/independent_calculator.py` | From-scratch formula reimplementation (no engine imports) |
| `tests/helpers/comparator.py` | Comparison logic and diff reporting |

## Storage Layer

All simulation CSV I/O is routed through a centralised storage abstraction:

| Module | Purpose |
| --- | --- |
| `app/storage/config.py` | Reads Spaces credentials from environment / `.env` |
| `app/storage/spaces_store.py` | S3-compatible client with local filesystem fallback |
| `app/data/csv_manager.py` | Centralised CSV read/write helpers via the storage layer |

The store is selected automatically at runtime:
- **Spaces mode** — when `SPACES_ACCESS_KEY_ID` is set, all reads/writes go to the configured DigitalOcean Spaces bucket.
- **Local mode** — otherwise, files are read/written relative to the project root (no cloud dependency).

## Project Structure

```
airline_sim/
├── main.py                  # CLI command router
├── run_dashboard.py         # Web dashboard launcher (FastAPI)
├── run_admin_dashboard.py   # Admin dashboard launcher (Streamlit)
├── requirements.txt
├── .env.example             # Spaces credential template
├── app/
│   ├── main.py              # CLI entry point
│   ├── config.py
│   ├── auth/                # Login, password, permissions
│   ├── core/                # Simulation engine, demand/cost/pricing models
│   ├── data/                # CSV manager, schema validation, backups
│   ├── modules/             # Lifecycle modules (setup, start, decisions, etc.)
│   ├── storage/             # Storage abstraction (Spaces + local fallback)
│   │   ├── config.py
│   │   └── spaces_store.py
│   └── ui/                  # Streamlit views
│       ├── components.py
│       ├── layout.py
│       ├── team_view.py
│       └── pages/           # Page-based navigation
│           ├── home.py
│           ├── setup.py
│           ├── decisions.py
│           └── results.py
├── code/
│   └── dashboard_web/       # Standalone FastAPI web dashboard
│       ├── app.py
│       ├── dashboard_data.py
│       ├── templates/
│       └── static/
├── simulation/
│   └── simulations/         # Simulation data (CSV files)
│       └── sim_001/
├── backup/                  # Pre-migration backups
├── tests/                   # Test suite
│   ├── simulation_test_suite.py
│   └── helpers/
└── docs/                    # Specifications
```

## UI Messaging Standard

UI text is centralized in `app/ui/components.py`.

- Simulation title: **Airlines**
- Simulation subtitle: **Competitive Strategy Simulation**
- Copyright notice: **Copyright 2026 by Dr. Jose Mendoza**
