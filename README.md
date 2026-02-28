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
| Display log | `.venv/bin/python main.py display-log sim_001` |

### Team Commands

| Task | Command |
| --- | --- |
| Team decision history summary | `.venv/bin/python main.py historical-decisions-team sim_001` |
| Team decision history (custom root) | `.venv/bin/python main.py historical-decisions-team sim_001 --root simulations` |

Current CLI routes are limited to `display-log` and `historical-decisions-team`; lifecycle and decision-entry workflows are available through the Streamlit UI.

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
