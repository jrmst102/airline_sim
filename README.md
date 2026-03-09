# airline_sim

**Version: v1.12**

Airlines simulation for the Competitive Strategy course.

## Overview

This repository provides:

- **Unified web application** — single FastAPI app serving both Admin and Team dashboards behind a shared login page
- CSV-backed simulation state and lifecycle modules
- Core round/state/market computation models
- Admin dashboard with simulation controls, live team table, interactive charts (pie, bar, line), and printable final report
- Team dashboard with login, decision entry, performance view, and auto-refresh
- Standalone FastAPI web dashboard with Plotly.js charts
- DigitalOcean Spaces cloud storage with local filesystem fallback
- Centralised CSV manager routed through the storage abstraction layer
- 32-scenario test suite with dual-layer verification (engine + independent calculator)
- Ready to deploy on DigitalOcean App Platform

## Quick Start

See [docs/QUICK_START.md](docs/QUICK_START.md) for a step-by-step guide for new administrators.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then run the unified application:

```bash
# Unified app (Admin + Team dashboards with shared login)
python run_admin_dashboard.py              # default: http://0.0.0.0:8080

# Or equivalently:
python run_team_dashboard.py               # default: http://0.0.0.0:8081

# Standalone web dashboard (FastAPI + Plotly.js)
python run_dashboard.py                    # default: http://0.0.0.0:8000
```

Both `run_admin_dashboard.py` and `run_team_dashboard.py` launch the same unified app. The login page at `/` routes users to the correct dashboard based on their credentials:
- **Admin** credentials → Admin Dashboard (`/admin`)
- **Team** credentials → Team Dashboard (`/team`)

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: `bcrypt`, `boto3`, `fastapi`, `gspread`, `google-auth`, `itsdangerous`, `jinja2`, `python-dotenv`, `python-multipart`, `uvicorn`.

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
| `price_business` | `$100–$5,000` |
| `price_leisure` | `$100–$5,000` |
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

## Simulation Management

Manage simulation lifecycle via the CLI module:

```bash
python -m app.modules.simulation_management <command>
```

### Commands

| Command | Description |
| --- | --- |
| `create` | Create a new simulation with admin + 5 team accounts |
| `list` | List all registered simulations |
| `lock <sim_id>` | Lock a simulation (reject team logins and decisions) |
| `unlock <sim_id>` | Unlock a simulation |
| `remove <sim_id> --confirm <sim_id>` | Delete a simulation and all its data |

### Create a Simulation

```bash
python -m app.modules.simulation_management create \
  --sim-id sim_001 \
  --name "Competitive Strategy" \
  --rounds 5 \
  --admin-user professor \
  --admin-pass Secret123!
```

| Argument | Default | Description |
| --- | --- | --- |
| `--sim-id` | *(required)* | Unique simulation identifier (alphanumeric + underscores) |
| `--name` | *(required)* | Display name for the simulation |
| `--rounds` | `3` | Number of rounds |
| `--admin-user` | *(auto-generated)* | Admin username |
| `--admin-pass` | *(auto-generated)* | Admin password |
| `--school-id` | `""` | Optional school identifier |
| `--course-id` | `""` | Optional course identifier |
| `--no-teams` | *(flag)* | Skip creation of the 5 default team accounts |

Passwords are bcrypt-hashed and stored in `{sim_id}/users.csv`. Five team accounts (Teams A–E) are created automatically unless `--no-teams` is specified.

> **Note:** Re-setting up an existing simulation preserves existing user passwords. New passwords are only generated for newly created accounts.

### List Simulations

```bash
python -m app.modules.simulation_management list
```

Prints a table with simulation ID, status, name, and lock state.

### Lock / Unlock / Remove

```bash
python -m app.modules.simulation_management lock sim_001
python -m app.modules.simulation_management unlock sim_001
python -m app.modules.simulation_management remove sim_001 --confirm sim_001
```

The demo simulation (`sim_demo`) cannot be removed.

## User Management

Manage users within a specific simulation:

```bash
python -m app.modules.user_management <simulation_id> <command>
```

### Commands

| Command | Description |
| --- | --- |
| `create` | Create a new user |
| `list` | List all users in the simulation |
| `lock --username <name>` | Lock a user account |
| `unlock --username <name>` | Unlock a user account |
| `chpass --username <name> --password <pass>` | Change a user's password |
| `chrole --username <name> --role <role>` | Change a user's role |
| `remove --username <name>` | Remove a user |
| `auth --username <name> --password <pass>` | Test authentication |

### Create a User

```bash
python -m app.modules.user_management sim_001 create \
  --username jsmith \
  --password MyPass123 \
  --role USER \
  --team-id A
```

| Argument | Default | Description |
| --- | --- | --- |
| `--username` | *(required)* | Unique username (case-insensitive) |
| `--password` | *(required)* | Password (minimum 8 characters) |
| `--role` | *(required)* | `ADMIN`, `PROFESSOR`, `TA`, or `USER` |
| `--team-id` | `""` | Required when role is `USER` |
| `--first-name` | `""` | Optional first name |
| `--last-name` | `""` | Optional last name |
| `--email` | `""` | Optional email |

### Roles

| Role | Dashboard | Description |
| --- | --- | --- |
| `ADMIN` | Admin | Full simulation control |
| `PROFESSOR` | Admin | Same privileges as Admin |
| `TA` | Admin | Same privileges as Admin |
| `USER` | Team | Team decision entry and performance view |

### Examples

```bash
# List all users
python -m app.modules.user_management sim_001 list

# Change password
python -m app.modules.user_management sim_001 chpass --username jsmith --password NewPass456

# Change role (team-id required when switching to USER)
python -m app.modules.user_management sim_001 chrole --username jsmith --role ADMIN

# Lock / unlock
python -m app.modules.user_management sim_001 lock --username jsmith
python -m app.modules.user_management sim_001 unlock --username jsmith

# Test credentials
python -m app.modules.user_management sim_001 auth --username jsmith --password NewPass456
```

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

### Option 2: Unified Dashboard (FastAPI)

A single FastAPI application serving both the Admin and Team dashboards behind a shared login page. Uses Jinja2 templates with signed session cookies — no Streamlit.

```bash
python run_admin_dashboard.py              # default: http://0.0.0.0:8080
python run_admin_dashboard.py --port 8090   # custom port
python run_admin_dashboard.py --reload      # auto-reload for development
```

#### Login

All users log in at `/` (or `/team/login`). Credentials are stored in `code/team_dashboard/usernames.csv`:
- **Admin** credentials → redirected to `/admin` (Admin Dashboard)
- **Team** credentials → redirected to `/team` (Team Dashboard)
- Admin routes (`/admin/*`) are protected by session middleware — unauthenticated users are redirected to login

#### Admin Dashboard Features

- **Status panel** — current round, simulation status (CREATED/STARTED/ENDED), last-updated timestamp
- **Decision status** — per-team icons (✔ Submitted / ✗ Pending) for the current round; auto-refreshes every 30 seconds and on tab focus
- **Admin actions** — Set Up Simulation (with confirmation warning; preserves existing passwords), Start, Move to Next Round (green button), End Simulation, Undo Last Period
- **Move to Next Round** — processes the current round (computes results for all teams) and advances; teams that did not submit decisions automatically repeat their previous round's choices
- **Team data table** — reads `round_results_team.csv` from Spaces (or local), sortable columns, AJAX refresh
- **Charts** — Pie chart (team profits), bar charts (market share by volume and revenue), and 5 line charts (Revenue, Profit, Costs, Price Business, Price Leisure per round per team) with multicolor palette
- **End Simulation report** — opens a printable report in a new window with final results, decisions history, and performance history by round
- **Logout** — link in the header returns to the login page
- **Safety** — confirm prompts on destructive actions (Setup warns about data loss), double-click protection
- NYU-themed styling consistent with `dashboard_web`

Admin action endpoints (all POST):

| Endpoint | Action |
| --- | --- |
| `POST /admin/setup` | Initialise simulation (calls `setup_simulation`) |
| `POST /admin/start` | Start simulation (calls `start_simulation`) |
| `POST /admin/end` | End simulation (calls `end_simulation`) |
| `POST /admin/next-round` | Process current round and advance (calls `move_next_round`) |
| `POST /admin/undo` | Undo last period (calls `undo_round`) |

Dashboard files live in `code/admin_dashboard/`:

| File | Purpose |
| --- | --- |
| `code/admin_dashboard/app.py` | FastAPI application, routes, Jinja2 rendering |
| `code/admin_dashboard/services/admin_actions.py` | Thin wrappers around simulation modules |
| `code/admin_dashboard/services/team_data.py` | Reads team CSV from Spaces → table payload, chart data, report data |
| `code/admin_dashboard/templates/admin_home.html` | Admin page template (charts, decision polling, actions) |
| `code/admin_dashboard/templates/report.html` | Printable end-of-simulation report template |
| `code/admin_dashboard/static/admin.css` | NYU-themed CSS |

#### Team Dashboard Features

- **Login page** — teams authenticate with per-simulation credentials (e.g. `teama_sim_001`); usernames map to team IDs
- **Decision form** — flights per day, business/leisure prices, branding level, product strategy; pre-filled from previous round
- **Save & Undo** — upsert decisions for the current round or undo to reset to defaults
- **Auto-refresh** — polls `/team/state` every 10 seconds and reloads when the simulation status or round changes (e.g. admin starts the sim or advances the round)
- **Performance metrics** — latest-round KPIs (revenue, cost, profit, passengers, load factor, market share, CSI, OEI)
- **Performance history table** — all completed rounds in a sortable table
- **Past decisions table** — review decisions from prior rounds
- **Session cookies** — `itsdangerous`-signed cookies, 24-hour expiry
- NYU-themed styling consistent with `admin_dashboard`

Required environment variables:

| Variable | Default |
| --- | --- |
| `SESSION_SECRET` | `airline-sim-dev-secret` (override in production) |

All endpoints:

| Endpoint | Method | Action |
| --- | --- | --- |
| `/` | GET | Redirect to login |
| `/team/login` | GET | Login form |
| `/team/login` | POST | Authenticate and route to `/admin` or `/team` |
| `/team` | GET | Team home (requires team session) |
| `/team/save` | POST | Save decisions for current round |
| `/team/undo` | POST | Undo current-round decisions |
| `/team/state` | GET | JSON simulation state for auto-refresh polling |
| `/team/logout` | GET | Clear session and redirect to login |
| `/admin` | GET | Admin dashboard (requires admin session) |
| `/admin/setup` | POST | Initialise simulation |
| `/admin/start` | POST | Start simulation |
| `/admin/end` | POST | End simulation |
| `/admin/next-round` | POST | Process round and advance |
| `/admin/undo` | POST | Undo last period |
| `/admin/report` | GET | Printable final results report |
| `/api/admin/status` | GET | JSON simulation status |
| `/api/admin/teams` | GET | JSON team data |
| `/api/admin/decisions` | GET | JSON decision status (no-cache) |
| `/health` | GET | Health check (`{"status": "ok"}`) |

Dashboard files:

| File | Purpose |
| --- | --- |
| `code/team_dashboard/main.py` | Unified entry point — mounts both dashboards, session guard, static files |
| `code/team_dashboard/app.py` | Team routes, session management |
| `code/team_dashboard/services/team_auth.py` | Authentication against `usernames.csv` (admin + team users) |
| `code/team_dashboard/usernames.csv` | Credentials file (username,password per line) |
| `code/team_dashboard/services/team_decisions.py` | Decision defaults, save/upsert, undo, past decisions |
| `code/team_dashboard/services/team_performance.py` | Team performance data from `round_results_team.csv` |
| `code/team_dashboard/templates/team_login.html` | Shared login page template |
| `code/team_dashboard/templates/team_home.html` | Team home template (form + metrics + tables) |
| `code/team_dashboard/static/team.css` | Team NYU-themed CSS |
| `code/admin_dashboard/app.py` | Admin routes, Jinja2 rendering |
| `code/admin_dashboard/services/admin_actions.py` | Simulation action wrappers |
| `code/admin_dashboard/services/team_data.py` | Team table, chart data, report data |
| `code/admin_dashboard/templates/admin_home.html` | Admin page (charts, polling, actions) |
| `code/admin_dashboard/templates/report.html` | Printable report |
| `code/admin_dashboard/static/admin.css` | Admin NYU-themed CSS |

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

### Option 4: Management Dashboard (FastAPI)

A standalone web UI for platform-level administration — create/lock/remove simulations and manage users across all simulations. Superadmin access only.

```bash
python run_management_dashboard.py               # default: http://0.0.0.0:8090
python run_management_dashboard.py --port 9000    # custom port
```

#### Authentication

Login at `/mgmt/login` with the superadmin account. Session is stored as a signed `httponly` cookie with 24-hour expiry.

#### Features

- **Simulations page** (`/mgmt/simulations`) — list all simulations, create new ones (with full credential report), lock/unlock, remove
- **Users page** (`/mgmt/users/{sim_id}`) — list users for a simulation, create users, change passwords/roles, lock/unlock/remove
- Flash messages for operation feedback
- NYU-themed styling

#### Routes

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/mgmt/login` | Login page |
| `POST` | `/mgmt/login` | Authenticate |
| `GET` | `/mgmt/logout` | Log out |
| `GET` | `/mgmt/simulations` | Simulation list and creation form |
| `POST` | `/mgmt/simulations/create` | Create simulation |
| `POST` | `/mgmt/simulations/lock` | Lock simulation |
| `POST` | `/mgmt/simulations/unlock` | Unlock simulation |
| `POST` | `/mgmt/simulations/remove` | Remove simulation |
| `GET` | `/mgmt/users/{sim_id}` | User list for a simulation |
| `POST` | `/mgmt/users/{sim_id}/create` | Create user |
| `POST` | `/mgmt/users/{sim_id}/change-password` | Change password |
| `POST` | `/mgmt/users/{sim_id}/change-role` | Change role |
| `POST` | `/mgmt/users/{sim_id}/lock` | Lock user |
| `POST` | `/mgmt/users/{sim_id}/unlock` | Unlock user |
| `POST` | `/mgmt/users/{sim_id}/remove` | Remove user |

Dashboard files live in `code/management_dashboard/`:

| File | Purpose |
| --- | --- |
| `code/management_dashboard/app.py` | FastAPI application, routes, session management |
| `code/management_dashboard/templates/mgmt_login.html` | Login page template |
| `code/management_dashboard/templates/mgmt_simulations.html` | Simulation management template |
| `code/management_dashboard/templates/mgmt_users.html` | User management template |
| `code/management_dashboard/static/mgmt.css` | Management dashboard CSS |

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
| Create simulation | `python -m app.modules.simulation_management create --sim-id sim_001 --name "Airline Simulation" --rounds 5 --admin-user prof --admin-pass Secret123!` |
| List simulations | `python -m app.modules.simulation_management list` |
| Lock simulation | `python -m app.modules.simulation_management lock sim_001` |
| Remove simulation | `python -m app.modules.simulation_management remove sim_001 --confirm sim_001` |
| Create user | `python -m app.modules.user_management sim_001 create --username jdoe --password Pass1234 --role USER --team-id A` |
| List users | `python -m app.modules.user_management sim_001 list` |
| Change password | `python -m app.modules.user_management sim_001 chpass --username jdoe --password NewPass99` |
| Change role | `python -m app.modules.user_management sim_001 chrole --username jdoe --role ADMIN` |
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

## Unified Dashboard

The application is a single FastAPI server in `code/team_dashboard/main.py` that mounts both the Admin and Team dashboards. It reads and writes all data through the centralised storage layer (DigitalOcean Spaces or local fallback).

```bash
python run_admin_dashboard.py    # or: python run_team_dashboard.py
```

The login page at `/` accepts both Admin and Team credentials and routes users to the appropriate dashboard. Admin routes are protected by session middleware.

### Required environment variables

Same as the main application — see the [DigitalOcean Spaces](#digitalocean-spaces-optional) section above.

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
├── main.py                        # CLI command router
├── run_dashboard.py               # Web dashboard launcher (FastAPI, port 8000)
├── run_admin_dashboard.py         # Unified dashboard launcher (FastAPI, port 8080)
├── run_team_dashboard.py          # Unified dashboard launcher (FastAPI, port 8081)
├── run_management_dashboard.py    # Management dashboard launcher (FastAPI, port 8090)
├── kill_port.py                   # Kill process on port 8080
├── Procfile                       # App Platform run command
├── app.yaml                       # DigitalOcean App Platform spec
├── requirements.txt
├── .env.example                   # Spaces credential template
├── app/
│   ├── main.py                    # CLI entry point
│   ├── config.py
│   ├── auth/
│   │   ├── login_manager.py       # Multi-simulation authentication
│   │   ├── password_manager.py    # bcrypt hash/verify
│   │   └── permissions.py         # Role normalisation and dashboard routing
│   ├── core/                      # Simulation engine, demand/cost/pricing models
│   ├── data/                      # CSV manager, schema validation, backups
│   ├── modules/
│   │   ├── simulation_management.py   # Create/list/lock/remove simulations
│   │   ├── user_management.py         # Create/list/lock/remove/chpass/chrole users
│   │   ├── setup_simulation.py
│   │   ├── start_simulation.py
│   │   ├── enter_decisions.py
│   │   ├── move_next_round.py
│   │   ├── end_simulation.py
│   │   ├── undo_round.py
│   │   ├── check_simulation_status.py
│   │   ├── display_results.py
│   │   ├── import_decisions_batch.py
│   │   ├── export_results_batch.py
│   │   └── ...                    # Additional modules
│   ├── storage/                   # Storage abstraction (Spaces + local fallback)
│   │   ├── config.py
│   │   └── spaces_store.py
│   └── ui/                        # Streamlit views (legacy)
├── code/
│   ├── __init__.py
│   ├── admin_dashboard/           # Admin dashboard routes & templates
│   │   ├── app.py
│   │   ├── services/
│   │   │   ├── admin_actions.py
│   │   │   └── team_data.py
│   │   ├── templates/
│   │   │   ├── admin_home.html
│   │   │   ├── report.html
│   │   │   ├── simulations.html
│   │   │   └── manage_users.html
│   │   └── static/
│   ├── team_dashboard/            # Team dashboard routes & unified entry point
│   │   ├── __init__.py
│   │   ├── app.py                 # Team routes, session management
│   │   ├── main.py                # Unified entry point (mounts admin + team)
│   │   ├── services/
│   │   │   ├── team_decisions.py
│   │   │   └── team_performance.py
│   │   ├── templates/
│   │   └── static/
│   ├── management_dashboard/      # Management dashboard (superadmin)
│   │   ├── app.py                 # FastAPI application, routes
│   │   ├── templates/
│   │   │   ├── mgmt_login.html
│   │   │   ├── mgmt_simulations.html
│   │   │   └── mgmt_users.html
│   │   └── static/
│   │       └── mgmt.css
│   └── dashboard_web/             # Standalone FastAPI web dashboard
│       ├── app.py
│       ├── dashboard_data.py
│       ├── templates/
│       └── static/
├── scripts/
│   ├── provision_demo.py          # Auto-provisions demo simulation on startup
│   └── migrate_usernames.py
├── simulation/
│   └── simulations/               # Local simulation data (CSV files)
├── backup/                        # Bucket backups & pre-migration archives
├── backup_spaces.py               # DO Spaces bucket backup script
├── tests/                         # Test suite
│   ├── simulation_test_suite.py
│   └── helpers/
├── docs/
│   ├── QUICK_START.md              # Quick Start guide for new admins
│   └── SPECIFICATION.md
```

## UI Messaging Standard

UI text is centralized in `app/ui/components.py`.

- Simulation title: **Airlines**
- Simulation subtitle: **Competitive Strategy Simulation**
- Copyright notice: **Copyright 2026 by Dr. Jose Mendoza**

## Backup DigitalOcean Spaces Bucket

`backup_spaces.py` downloads every object from the configured DO Spaces bucket into `backup/spaces_backup_YYYYMMDD_HHMMSS/`, preserving the key structure. It is **read-only** and never writes to the bucket.

```bash
# Full backup
python backup_spaces.py

# List objects without downloading
python backup_spaces.py --dry-run

# Back up only keys starting with a given prefix
python backup_spaces.py --prefix sim_001
```

The script uses the same Spaces credentials from `.env` (see [Setup — DigitalOcean Spaces](#digitalocean-spaces-optional)).

## Deploying to DigitalOcean App Platform

The unified application (Admin + Team dashboards) is ready to deploy as a single web service on [DigitalOcean App Platform](https://www.digitalocean.com/products/app-platform). The app reads/writes all CSV data through DigitalOcean Spaces — no local persistence is needed.

### Run command & module path

```
uvicorn code.team_dashboard.main:app --host 0.0.0.0 --port $PORT
```

This is defined in the `Procfile` at the repo root. The entry point `code/team_dashboard/main.py` sets up import paths and re-exports the FastAPI `app` object.

### Environment variables

Set these in the App Platform UI (mark secrets as **Encrypted**):

| Variable | Type | Value |
| --- | --- | --- |
| `SPACES_ACCESS_KEY_ID` | SECRET | *(your Spaces key)* |
| `SPACES_SECRET_ACCESS_KEY` | SECRET | *(your Spaces secret)* |
| `SPACES_REGION` | Plain | `sfo3` |
| `SPACES_BUCKET` | Plain | `airlines-sim` |
| `SPACES_ENDPOINT` | Plain | `https://sfo3.digitaloceanspaces.com` |
| `SESSION_SECRET` | SECRET | *(random string for cookie signing)* |

### App Platform setup steps

1. Go to **DigitalOcean Console → Apps → Create App**
2. Choose **GitHub** as source → select repo `jrmst102/airline_sim`
3. Select branch: `main`
4. App Platform should detect the `Procfile` and set the run command automatically. Verify it shows:
   ```
   uvicorn code.team_dashboard.main:app --host 0.0.0.0 --port $PORT
   ```
5. Set service type: **Web Service**
6. Add the environment variables listed above (mark secrets as Encrypted)
7. Choose instance size: **Basic (Starter)** — smallest is fine to start
8. Click **Deploy**

Alternatively, import `app.yaml` directly: in the App Platform creation flow, choose **Import from app spec** and point to `app.yaml` in the repo root.

### Running locally (production-like)

```bash
pip install -r requirements.txt

export SPACES_ACCESS_KEY_ID=your_key
export SPACES_SECRET_ACCESS_KEY=your_secret
export SPACES_REGION=sfo3
export SPACES_BUCKET=airlines-sim
export SPACES_ENDPOINT=https://sfo3.digitaloceanspaces.com
export SESSION_SECRET=some-random-secret

# Using the Procfile command:
uvicorn code.team_dashboard.main:app --host 0.0.0.0 --port 8080

# Or using the launcher script:
python run_admin_dashboard.py
```

### Health check

After deployment, verify:

```bash
curl https://your-app-url.ondigitalocean.app/health
# → {"status":"ok"}
```

### Smoke test checklist

After deployment, verify each item:

- `/health` returns `200` with `{"status":"ok"}`
- `/team/login` loads the shared login page
- Admin login works (e.g. `admin_sim_001` / your password) → redirected to `/admin`
- Team login works (e.g. `teama_sim_001` / your password) → redirected to `/team`
- `/admin` is protected — unauthenticated access redirects to login
- Admin dashboard shows charts, decision status, and action buttons
- Team decision page loads and shows simulation status / round indicators
- Save writes decisions to Spaces (verify by checking the updated CSV in the bucket)
- Undo works (team-scoped; does not affect other teams)
- Past decisions table shows only when simulation is started and round > 1
- Logout from either dashboard returns to the login page
