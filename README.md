# airline_sim
Airlines simulation for the Competitive Strategy course.

## Overview

This repository provides:

- CSV-backed simulation state and lifecycle modules
- Core round/state/market computation models
- Streamlit UI views for admin, team, and dashboard workflows

## Setup

From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

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
| Check simulation status | `.venv/bin/python main.py check-status sim_001` |
| Start simulation | `.venv/bin/python main.py start-simulation sim_001 U_ADMIN` |
| Move to next round | `.venv/bin/python main.py move-next-round sim_001 U_ADMIN` |
| Undo current round | `.venv/bin/python main.py undo-round sim_001 U_ADMIN` |
| End simulation | `.venv/bin/python main.py end-simulation sim_001 U_ADMIN` |
| Display results | `.venv/bin/python main.py display-results sim_001` |
| Display log | `.venv/bin/python main.py display-log sim_001` |

## UI Usage (Streamlit)

Launch the dashboard UI:

```bash
streamlit run app/ui/dashboard.py
```

The UI also includes dedicated views in:

- `app/ui/admin_view.py`
- `app/ui/team_view.py`

## UI Messaging Standard

UI text is centralized in `app/ui/components.py`.

- Simulation title: **Airlines**
- Simulation subtitle: **Competitive Strategy Simulation**
- Copyright notice: **Copyright 2026 by Dr. Jose Mendoza**
