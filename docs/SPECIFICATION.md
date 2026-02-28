# Airline Simulation System Specification

## Project: airline_sim

**Repository:** https://github.com/jrmst102/airline_sim\
**Backend:** Python\
**Frontend:** Streamlit (preferred) or Simple React\
**Persistence:** Local CSV Files\
**Environment:** Local development (no database)

------------------------------------------------------------------------

# 1. Executive Overview

The Airline Simulation System is a multi-round, multi-player competitive
strategy simulation focused on airline pricing competition on a single
route (JFK--BOS).

The system must:

-   Support configurable multi-round simulations
-   Allow role-based access (Admin, Team Lead, Team Member)
-   Persist all state using local CSV files
-   Support manual round advancement by Admin
-   Compute economic outcomes deterministically
-   Support undo, backup, restore, and destroy operations
-   Maintain complete auditability via append-only CSV logs

The architecture must be modular, testable, and deterministic.

------------------------------------------------------------------------

# 2. System Architecture

## 2.1 Architectural Layers

Frontend (Streamlit UI)\
↓\
Application Layer (Controllers / Modules)\
↓\
Simulation Engine (Pure Calculation Layer)\
↓\
CSV Persistence Layer (File-based Data Manager)

## 2.2 Design Principles

-   Deterministic calculations\
-   No database usage\
-   Append-only logs for auditability\
-   Idempotent round computation\
-   Clear separation of concerns\
-   Pure calculation functions (no I/O inside engine)\
-   Versionable parameters\
-   Full state recoverability via backups

------------------------------------------------------------------------

# 3. Repository Structure

    airline_sim/
    │
    ├── app/
    │   ├── main.py
    │   ├── config.py
    │   ├── core/
    │   │   ├── simulation_engine.py
    │   │   ├── demand_model.py
    │   │   ├── pricing_model.py
    │   │   ├── cost_model.py
    │   │   ├── indices_model.py
    │   │   ├── round_manager.py
    │   │   └── state_machine.py
    │   ├── data/
    │   │   ├── csv_manager.py
    │   │   ├── file_structure.py
    │   │   ├── schema_validator.py
    │   │   └── backup_manager.py
    │   ├── modules/
    │   │   ├── setup_simulation.py
    │   │   ├── start_simulation.py
    │   │   ├── move_next_round.py
    │   │   ├── undo_round.py
    │   │   ├── end_simulation.py
    │   │   ├── enter_decisions.py
    │   │   ├── display_results.py
    │   │   ├── change_parameters_live.py
    │   │   ├── backup_simulation.py
    │   │   ├── restore_simulation.py
    │   │   ├── destroy_simulation.py
    │   │   └── user_management.py
    │   ├── auth/
    │   │   ├── login_manager.py
    │   │   ├── password_manager.py
    │   │   └── permissions.py
    │   └── ui/
    │       ├── admin_view.py
    │       ├── team_view.py
    │       ├── dashboard.py
    │       └── components.py
    │
    ├── simulations/
    ├── backups/
    ├── archive/
    │
    ├── tests/
    ├── requirements.txt
    └── README.md

------------------------------------------------------------------------

# 4. CSV Data Model

Each simulation is stored in:

simulations/{simulation_id}/

Required CSV files:

-   simulation.csv\
-   parameters.csv\
-   teams.csv\
-   users.csv\
-   routes.csv\
-   airplane_types.csv\
-   rounds.csv\
-   decisions.csv\
-   round_results_team.csv\
-   round_results_market.csv\
-   login_log.csv\
-   admin_actions.csv

------------------------------------------------------------------------

# 5. Core Functional Modules

## Setup_simulation

Creates simulation folder, CSV files, headers, parameters, teams, and
rounds.

## Start_simulation

Sets simulation to STARTED and opens Round 1.

## Enter_decisions

Allows Team Lead to submit flights, prices, and branding investment for
OPEN round.

## Move_next_round

Closes current round, runs simulation engine, writes results, and opens
next round.

## Undo_round

Reverts most recent CLOSED round and restores it to OPEN.

## End_simulation

Locks all rounds and prevents new decisions.

## Backup_simulation

Creates zipped snapshot of simulation folder.

## Restore_simulation

Restores from backup (in-place or new ID).

## Destroy_simulation

Backs up first, then archives or deletes simulation.

------------------------------------------------------------------------

# 6. Simulation Engine

## Capacity

Cap_i = FlightsPerDay_i × Days × SeatsPerFlight

## Revenue

Revenue_i = (CarriedB_i × Pprem_i) + (CarriedL_i × Pecon_i)

## Cost

Cost_i = FuelCost_i + FixedCost_i + VarCost_i + BrandCost_i

## Profit

Profit_i = Revenue_i − Cost_i

## Market Share

MS_vol_i = Carried_i / Σ Carried_j\
MS_profit_i = max(Profit_i,0) / Σ max(Profit_j,0)

------------------------------------------------------------------------

# 7. Security

-   bcrypt password hashing\
-   Login logs\
-   Admin action logs\
-   Account lock/unlock\
-   CSV access via application layer only

------------------------------------------------------------------------

# 8. Testing

-   Demand allocation validation\
-   Capacity constraint enforcement\
-   Revenue and cost consistency\
-   Undo integrity\
-   Backup/restore validation

------------------------------------------------------------------------

# 9. Future Scalability

-   Multiple routes\
-   Multiple aircraft types\
-   Stochastic demand\
-   Multi-market expansion\
-   Real-time multiplayer

------------------------------------------------------------------------

# 10. Development Order

1.  CSV schema + setup\
2.  Decision entry + rounds\
3.  Simulation engine\
4.  Results display\
5.  Undo\
6.  Backup/restore\
7.  Admin UI\
8.  Authentication
