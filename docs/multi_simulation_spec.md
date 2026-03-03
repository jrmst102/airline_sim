# Multi-Simulation Support — Specification

**Project:** airline_sim  
**Author:** GitHub Copilot  
**Date:** March 3, 2026  
**Status:** Draft  

---

## 1. Executive Summary

This specification describes the changes required to support **multiple concurrent simulations** within the airline_sim platform. Today the system is hardcoded to a single simulation (`sim_001`). The goal is to allow an administrator to create and run several independent simulations simultaneously, each with its own teams, rounds, and data — while ensuring that every user is automatically routed to the correct simulation upon login.

The spec also defines:
- A **demo simulation** with pre-provisioned demo accounts for testing and onboarding.
- A **Simulation Management** module for creating, locking/unlocking, and removing simulations.
- A **User Management** module for full user CRUD, role changes, simulation assignment, and extended profile fields.

---

## 2. Current State (As-Is)

### 2.1 Hardcoded Simulation ID

The constant `DEFAULT_SIM_ID = "sim_001"` is hardcoded in three critical locations:

| File | Usage |
|------|-------|
| `code/team_dashboard/app.py` | Written into the session cookie at login; used as fallback when reading session |
| `code/admin_dashboard/app.py` | Passed as a literal to every admin action (setup, start, end, undo) and every API endpoint |
| `code/team_dashboard/services/team_auth.py` | Declared but unused |

### 2.2 Credential Store

Authentication uses a flat CSV file (`code/team_dashboard/usernames.csv`) with no simulation affinity:

```
Admin,RoadRunner1
Team1,MrGreen3
Team2,CrazyLizzard4
...
Team6,CrazyCat7
```

- **No `simulation_id` column** — every user is implicitly assigned to `sim_001`.
- A hardcoded `_TEAM_ID_MAP` in `team_auth.py` maps usernames to team letters (`Team1→A`, …, `Team6→F`).
- The same team names (`Team1`–`Team6`) cannot be reused across simulations.

### 2.3 Per-Simulation Users (Existing but Unused for Login)

Each simulation already has a `{sim_id}/users.csv` in the storage layer with hashed passwords and role/team assignments. This file is managed by `app/modules/user_management.py` and supports `create_user`, `authenticate_user`, `lock/unlock`. **However, the web login flow does not use it** — it reads from the flat `usernames.csv` instead.

### 2.4 Storage Layer (Already Multi-Sim Ready)

The storage layer (`app/storage/spaces_store.py` + `app/data/csv_manager.py`) already namespaces all data by simulation ID:

```
sim_001/simulation.csv
sim_001/teams.csv
sim_001/decisions.csv
sim_002/simulation.csv    ← would work today if referenced
sim_002/teams.csv
```

**No changes are needed in the storage layer.**

### 2.5 Session Cookie

The session cookie (`team_session`) already carries a `sim_id` field:

```python
{
    "username": "Team1",
    "team_id": "A",
    "role": "team",
    "sim_id": "sim_001",    # ← already present
}
```

The value is always set to `DEFAULT_SIM_ID` at login time. Downstream team routes already read `sim_id` from the session. **The admin dashboard ignores the session entirely and uses the hardcoded constant.**

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | The system shall support multiple simulations running concurrently, each identified by a unique `simulation_id` (e.g. `sim_001`, `sim_002`, `sim_mba_spring26`). |
| FR-2 | Each simulation shall have its own independent set of teams, users, decisions, rounds, and results. |
| FR-3 | When a user logs in, the system shall automatically determine which simulation the user belongs to and route them to the correct simulation context — **no manual simulation selector required at login**. |
| FR-4 | A Professor, TA, or Admin may be assigned to one or more simulations. After login, if the user has access to more than one simulation, the admin dashboard shall display a simulation picker. |
| FR-5 | A User (team member) shall belong to exactly one simulation. The system shall reject login if the user's simulation cannot be determined. |
| FR-6 | Admin/Professor/TA operations shall operate on the simulation currently selected in the session, not a hardcoded constant. |
| FR-13 | The system shall support four roles: **User**, **Professor**, **Teaching Assistant (TA)**, and **Admin**, each with distinct permission levels (see Section 4.9.3). |
| FR-7 | The system shall support creating new simulations via the admin dashboard (in addition to the existing CLI). |
| FR-8 | All existing CLI commands (`setup_simulation`, `start_simulation`, `enter_decisions`, etc.) shall continue to work unchanged — they already accept `simulation_id` as an argument. |
| FR-9 | A built-in **demo simulation** (`sim_demo`) shall always exist with a demo admin and six demo team users (see Section 4.7). |
| FR-10 | The system shall provide a **Simulation Management** module allowing admins to create, lock/unlock, and remove simulations (see Section 4.8). |
| FR-11 | The system shall provide a **User Management** module allowing admins to create, edit, remove, lock/unlock, change passwords, change roles, and assign users to simulations (see Section 4.9). |
| FR-12 | Each user record shall include extended profile fields: first name, last name, email, role, simulation ID, school ID, and course ID (see Section 5.2). |

### 3.2 Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NF-1 | No changes to the storage layer (`spaces_store.py`, `csv_manager.py`). |
| NF-2 | Backward-compatible: existing `sim_001` data and credentials shall continue to work without migration. |
| NF-3 | The flat `usernames.csv` file shall be retired in favor of the per-simulation `users.csv` (which already supports hashed passwords). |
| NF-4 | No database — all state remains in CSV files routed through the storage layer. |

---

## 4. Design

### 4.1 Global Simulation Registry

A new CSV file stored in the bucket at the **root level** (not inside any simulation prefix):

**Key:** `admin/simulations.csv`

| Column | Type | Description |
|--------|------|-------------|
| `simulation_id` | string | Unique ID (e.g. `sim_001`) |
| `name` | string | Display name (e.g. "MBA Spring 2026") |
| `status` | string | `CREATED`, `STARTED`, `ENDED`, `LOCKED` |
| `is_locked` | string | `0` or `1` — locked simulations reject all team logins and decision submissions |
| `school_id` | string | Optional school/institution identifier |
| `course_id` | string | Optional course identifier |
| `created_at_utc` | ISO 8601 | When the simulation was created |
| `updated_at_utc` | ISO 8601 | Last status change timestamp |

This file is the **authoritative index** of all simulations in the system. It is updated whenever a simulation is set up, started, ended, locked, or removed.

### 4.2 Unified Authentication via Per-Simulation `users.csv`

Each simulation's `{sim_id}/users.csv` becomes the **sole credential source**. The schema is extended with profile fields:

```
simulation_id, user_id, username, first_name, last_name, email, role, team_id, school_id, course_id, password_hash, is_locked, created_at_utc, updated_at_utc
```

#### Login Flow (Revised)

1. User submits **username** and **password** on the login page (no simulation selector).
2. The system reads the global simulation registry (`admin/simulations.csv`) to get the list of active simulations (status = `CREATED` or `STARTED`).
3. For each active simulation, the system checks `{sim_id}/users.csv` for a matching username.
4. If exactly **one** simulation contains the username → authenticate against that simulation's `users.csv` and set `sim_id` in the session.
5. If the username exists in **multiple** simulations (expected for Professor, TA, or Admin users) → authenticate, then present a simulation picker on the dashboard.
6. If **no** simulation contains the username → reject login.
7. After authentication, the system checks the user's **role** to determine routing:
   - `USER` → Team Dashboard (`/team`)
   - `PROFESSOR`, `TA`, `ADMIN` → Admin Dashboard (`/admin`)

> **Performance note:** With a small number of simulations (typically 1–5), scanning each `users.csv` is fast. If scale grows, a global `admin/users_index.csv` mapping `username → simulation_id` can be introduced as an optimization.

#### Retirement of `usernames.csv`

- The flat file `code/team_dashboard/usernames.csv` will be **removed**.
- The hardcoded `_TEAM_ID_MAP` in `team_auth.py` will be **removed** — the `team_id` is already stored in `users.csv`.
- A **one-time migration script** will create `users.csv` entries (with hashed passwords) for the existing teams in `sim_001`.

### 4.3 Session Cookie (Updated Payload)

```python
{
    "username": "Team1",
    "team_id": "A",
    "role": "USER",            # "USER", "PROFESSOR", "TA", or "ADMIN"
    "sim_id": "sim_001",      # dynamically set at login
}
```

The `role` field now carries one of four values. Routing logic uses the role to determine dashboard access (see Section 4.9.3).

### 4.4 Admin Dashboard Changes

| Area | Current | Proposed |
|------|---------|----------|
| Simulation context | Hardcoded `DEFAULT_SIM_ID` | Read `sim_id` from session cookie |
| Admin routes | All use literal `"sim_001"` | All read `sim_id` from session; reject if missing |
| Simulation picker | N/A | New UI element: dropdown in the admin header showing available simulations (from `admin/simulations.csv`) filtered to those the user has access to |
| Create simulation | CLI only (`setup_simulation`) | New admin route `POST /admin/create-simulation` wrapping the existing `setup_simulation` module |
| `AdminGuardMiddleware` | Checks `role == "admin"` | Checks `role` is `PROFESSOR`, `TA`, or `ADMIN`. Also validates that `sim_id` is present in session. Enforces per-role action restrictions (see Section 4.9.3). |

#### Simulation Picker Behavior

- On login, if a Professor, TA, or Admin has access to multiple simulations, redirect to `/admin/select-simulation`.
- The picker page lists all simulations from `admin/simulations.csv` filtered by the user's access.
- Selecting a simulation sets `sim_id` in the session and redirects to `/admin`.
- A "Switch Simulation" link in the admin header allows changing context at any time.

### 4.5 Team Dashboard Changes

| Area | Current | Proposed |
|------|---------|----------|
| Login handler | Calls `team_auth.login()` with flat CSV | Calls revised login flow (Section 4.2) |
| Session `sim_id` | Always `"sim_001"` | Dynamically set from the matched simulation |
| Team routes | Already read `sim_id` from session | No change needed |
| Streamlit team view (`team_view.py`) | Hardcoded `SIM_ID = "sim_001"` | Read from session or environment |

### 4.6 Setup Simulation — User Provisioning

When `setup_simulation` is called (CLI or admin dashboard), it shall:

1. Create all CSV files under `{sim_id}/` (existing behavior).
2. Create team users in `{sim_id}/users.csv` with auto-generated or admin-specified passwords.
3. Create an admin user entry in `{sim_id}/users.csv`.
4. Register the simulation in `admin/simulations.csv`.

The `setup_simulation` module already creates detailed `teams.csv` and `users.csv` — it only needs to be extended to include team-user credentials and the registry update.

### 4.7 Demo Simulation

A built-in demo simulation (`sim_demo`) shall be **automatically provisioned** on first startup if it does not already exist. It provides a ready-to-use sandbox for testing and onboarding.

#### Demo Accounts

| Username | Password | Role | Team | Purpose |
|----------|----------|------|------|---------|
| `demoadmin` | `DemoAdmin2026!` | ADMIN | — | Demo administrator (full platform access) |
| `demoprof` | `DemoProf2026!` | PROFESSOR | — | Demo professor (can create/start/stop sims, advance rounds) |
| `demota` | `DemoTA2026!` | TA | — | Demo teaching assistant (can advance rounds, read-only admin) |
| `demouser1` | `DemoUser1!` | USER | A | Demo team A |
| `demouser2` | `DemoUser2!` | USER | B | Demo team B |
| `demouser3` | `DemoUser3!` | USER | C | Demo team C |
| `demouser4` | `DemoUser4!` | USER | D | Demo team D |
| `demouser5` | `DemoUser5!` | USER | E | Demo team E |
| `demouser6` | `DemoUser6!` | USER | F | Demo team F |

#### Demo Simulation Behavior

- `simulation_id`: `sim_demo`
- Name: "Demo Simulation"
- Automatically registered in `admin/simulations.csv` with status `CREATED`.
- Total rounds: 3 (small for quick walkthroughs).
- All baseline data is seeded identically to a normal simulation.
- The demo simulation can be started, played, ended, and re-setup just like any other simulation.
- Demo accounts use well-known passwords — this is intentional for onboarding. Instructors should **not** use the demo simulation for graded coursework.

#### Provisioning Logic

On application startup (`code/team_dashboard/main.py`):
1. Check if `sim_demo` exists in `admin/simulations.csv`.
2. If not → run `setup_simulation(simulation_id="sim_demo", ...)` and create all ten demo users (1 admin, 1 professor, 1 TA, 6 team users).
3. If yes → skip (no-op).

This ensures the demo simulation is always available without manual intervention.

### 4.8 Simulation Management Module

A new **Simulation Management** module (`app/modules/simulation_management.py`) provides administrative operations on simulations as a whole. This is distinct from the existing `setup_simulation` / `start_simulation` / `end_simulation` modules, which manage the *lifecycle* of a single simulation's rounds.

#### 4.8.1 Operations

| Operation | Description | Route (Admin Dashboard) | CLI |
|-----------|-------------|------------------------|-----|
| **Create simulation** | Creates a new simulation with all CSV files, admin account, and team user accounts. Registers it in `admin/simulations.csv`. | `POST /admin/simulations/create` | `python -m app.modules.simulation_management create ...` |
| **Lock simulation** | Sets `is_locked = 1` in the registry. A locked simulation rejects team logins and decision submissions. The admin can still access it read-only. | `POST /admin/simulations/{sim_id}/lock` | `python -m app.modules.simulation_management lock {sim_id}` |
| **Unlock simulation** | Sets `is_locked = 0` in the registry. | `POST /admin/simulations/{sim_id}/unlock` | `python -m app.modules.simulation_management unlock {sim_id}` |
| **Remove simulation** | Deletes all data under `{sim_id}/` in storage and removes the row from `admin/simulations.csv`. **Irreversible.** Requires confirmation. The demo simulation (`sim_demo`) cannot be removed. | `POST /admin/simulations/{sim_id}/remove` | `python -m app.modules.simulation_management remove {sim_id}` |

#### 4.8.2 Create Simulation — Input Fields

| Field | Required | Description |
|-------|----------|-------------|
| `simulation_id` | Yes | Unique alphanumeric ID (e.g. `sim_mba_spring26`). Validated: `^[a-zA-Z0-9_]+$`. |
| `name` | Yes | Display name (e.g. "MBA Spring 2026"). |
| `total_rounds` | Yes | Number of rounds (1–20). |
| `admin_username` | Yes | Username for the simulation admin. |
| `admin_password` | Yes | Password for the simulation admin (min 8 chars). |
| `school_id` | No | Optional school/institution identifier. |
| `course_id` | No | Optional course identifier. |
| `auto_create_teams` | No | If true (default), auto-creates 6 team-user accounts with generated passwords. |

#### 4.8.3 Create Simulation — Output

After creation, the module returns a **credentials report** containing all generated usernames and passwords. The admin dashboard displays this in a printable format so the instructor can distribute credentials to students.

#### 4.8.4 Lock/Unlock Behavior

- When a simulation is **locked**:
  - Users (team members) attempting to log in see: "This simulation is currently locked. Contact your instructor."
  - Decision submission endpoints return an error.
  - Professors, TAs, and Admins can still log in and view data (read-only).
  - The admin dashboard shows a "LOCKED" badge next to the simulation name.
- When a simulation is **unlocked**, normal behavior resumes.

#### 4.8.5 Remove Simulation — Safety

- Requires explicit confirmation (admin must type the `simulation_id` to confirm).
- The demo simulation (`sim_demo`) is protected and cannot be removed.
- A backup of the simulation data is optionally created before deletion.

### 4.9 User Management Module

A new **User Management** module (`app/modules/user_management.py` — extending the existing file) provides full CRUD operations on user accounts. The admin dashboard exposes these via a **User Management** page.

#### 4.9.1 Operations

| Operation | Description | Route (Admin Dashboard) |
|-----------|-------------|------------------------|
| **Create user** | Creates a new user in a simulation's `users.csv`. | `POST /admin/users/create` |
| **Edit user** | Updates profile fields (first name, last name, email, school ID, course ID). | `POST /admin/users/{user_id}/edit` |
| **Remove user** | Removes a user from a simulation's `users.csv`. Cannot remove the last admin of a simulation. | `POST /admin/users/{user_id}/remove` |
| **Lock user** | Sets `is_locked = 1`. User cannot log in. | `POST /admin/users/{user_id}/lock` |
| **Unlock user** | Sets `is_locked = 0`. | `POST /admin/users/{user_id}/unlock` |
| **Change password** | Sets a new password (bcrypt-hashed). | `POST /admin/users/{user_id}/change-password` |
| **Change role** | Changes role among `USER`, `PROFESSOR`, `TA`, and `ADMIN`. | `POST /admin/users/{user_id}/change-role` |
| **Assign to simulation** | Moves or copies a user to a different simulation's `users.csv`. | `POST /admin/users/{user_id}/assign` |

#### 4.9.2 User Profile Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Auto | System-generated (e.g. `U001`). |
| `username` | string | Yes | Login username. Globally unique across all simulations. |
| `first_name` | string | Yes | User's first name. |
| `last_name` | string | Yes | User's last name. |
| `email` | string | Yes | User's email address. |
| `role` | string | Yes | `USER`, `PROFESSOR`, `TA`, or `ADMIN`. |
| `team_id` | string | Conditional | Required for `USER` role. Team letter (`A`–`F`). Not applicable for other roles. |
| `simulation_id` | string | Yes | The simulation this user belongs to. |
| `school_id` | string | No | School or institution identifier (e.g. "UNIV_001"). |
| `course_id` | string | No | Course identifier (e.g. "MBA_STRATEGY_S26"). |
| `password_hash` | string | Auto | bcrypt hash. Never displayed. |
| `is_locked` | string | Auto | `0` (unlocked) or `1` (locked). |
| `created_at_utc` | ISO 8601 | Auto | Account creation timestamp. |
| `updated_at_utc` | ISO 8601 | Auto | Last modification timestamp. |

#### 4.9.3 Role Definitions

| Role | Dashboard | Permissions |
|------|-----------|-------------|
| `USER` | Team Dashboard | Can submit decisions for their assigned team. Can view their own team's results. Cannot access the admin dashboard. |
| `PROFESSOR` | Admin Dashboard | Can view all team data. Can **create**, **start**, and **stop** simulations. Can **advance to the next round**. Can view simulation management and user lists. Cannot delete simulations or manage platform-wide settings. |
| `TA` | Admin Dashboard | Can view all team data. Can **advance to the next round** and **undo rounds**. **Cannot** create, start, or stop simulations. Cannot manage users or simulations. Read-only access to admin dashboard except round advancement and undo. |
| `ADMIN` | Admin Dashboard | Full platform access. Can create, start, stop, lock, unlock, and delete simulations. Can create, edit, remove, lock, unlock, and reassign users. Can change user roles. Can advance rounds. |

> **Note:** The existing `TEAM_LEAD` and `TEAM_MEMBER` roles from `user_management.py` are consolidated into `USER`. The old `ADMIN` role is split into three tiers: `PROFESSOR`, `TA`, and `ADMIN`.

#### 4.9.3.1 Permission Matrix

| Action | USER | TA | PROFESSOR | ADMIN |
|--------|------|-----|-----------|-------|
| Access Team Dashboard | ✅ | — | — | — |
| Submit decisions | ✅ | — | — | — |
| Access Admin Dashboard | — | ✅ | ✅ | ✅ |
| View all team data | — | ✅ | ✅ | ✅ |
| Advance to next round | — | ✅ | ✅ | ✅ |
| Create simulation | — | — | ✅ | ✅ |
| Start simulation | — | — | ✅ | ✅ |
| Stop/End simulation | — | — | ✅ | ✅ |
| Lock/Unlock simulation | — | — | — | ✅ |
| Delete simulation | — | — | — | ✅ |
| Create user | — | — | — | ✅ |
| Edit user | — | — | — | ✅ |
| Remove user | — | — | — | ✅ |
| Lock/Unlock user | — | — | — | ✅ |
| Change user password | — | — | — | ✅ |
| Change user role | — | — | — | ✅ |
| Assign user to simulation | — | — | — | ✅ |
| Undo round | — | ✅ | ✅ | ✅ |

#### 4.9.4 Admin Dashboard — User Management Page

Accessible at `/admin/users`. Provides:

- **User list table** showing all users in the current simulation with columns: username, first name, last name, email, role, team, status (locked/unlocked).
- **Action buttons** per row: Edit, Lock/Unlock, Change Password, Change Role, Remove. (Visible only to `ADMIN` users.)
- **Create User** form at the top. (Visible only to `ADMIN` users.)
- **Search/filter** by username, name, role, or team.
- `PROFESSOR` and `TA` users can view the user list but cannot modify users.

---

## 5. Data Model Changes

### 5.1 New File: `admin/simulations.csv`

```csv
simulation_id,name,status,is_locked,school_id,course_id,created_at_utc,updated_at_utc
sim_demo,Demo Simulation,CREATED,0,,,2026-03-01T10:00:00+00:00,2026-03-01T10:00:00+00:00
sim_001,Airline Simulation,STARTED,0,UNIV_001,MBA_STRAT_S26,2026-03-01T10:00:00+00:00,2026-03-01T12:00:00+00:00
sim_002,MBA Spring 2026,CREATED,0,UNIV_001,MBA_STRAT_S26,2026-03-03T14:00:00+00:00,2026-03-03T14:00:00+00:00
```

### 5.2 Extended: `{sim_id}/users.csv`

Schema extended with profile fields (`first_name`, `last_name`, `email`, `school_id`, `course_id`, `updated_at_utc`). Roles are `USER`, `PROFESSOR`, `TA`, and `ADMIN`.

```csv
simulation_id,user_id,username,first_name,last_name,email,role,team_id,school_id,course_id,password_hash,is_locked,created_at_utc,updated_at_utc
sim_001,U001,profmendoza,Jose,Mendoza,jmendoza@univ.edu,PROFESSOR,,UNIV_001,MBA_STRAT_S26,<hash>,0,2026-03-01T10:00:00+00:00,2026-03-01T10:00:00+00:00
sim_001,U002,ta_garcia,Maria,Garcia,mgarcia@univ.edu,TA,,UNIV_001,MBA_STRAT_S26,<hash>,0,2026-03-01T10:00:00+00:00,2026-03-01T10:00:00+00:00
sim_001,U003,jdoe,Jane,Doe,jane.doe@univ.edu,USER,A,UNIV_001,MBA_STRAT_S26,<hash>,0,2026-03-01T10:00:00+00:00,2026-03-01T10:00:00+00:00
sim_001,U004,jsmith,John,Smith,john.smith@univ.edu,USER,B,UNIV_001,MBA_STRAT_S26,<hash>,0,2026-03-01T10:00:00+00:00,2026-03-01T10:00:00+00:00
...
```

### 5.3 Demo Simulation: `sim_demo/users.csv`

Pre-provisioned with ten accounts:

```csv
simulation_id,user_id,username,first_name,last_name,email,role,team_id,school_id,course_id,password_hash,is_locked,created_at_utc,updated_at_utc
sim_demo,U001,demoadmin,Demo,Admin,demo@example.com,ADMIN,,,,<hash>,0,...,...
sim_demo,U002,demoprof,Demo,Professor,demoprof@example.com,PROFESSOR,,,,<hash>,0,...,...
sim_demo,U003,demota,Demo,TA,demota@example.com,TA,,,,<hash>,0,...,...
sim_demo,U004,demouser1,Demo,User1,demo1@example.com,USER,A,,,<hash>,0,...,...
sim_demo,U005,demouser2,Demo,User2,demo2@example.com,USER,B,,,<hash>,0,...,...
sim_demo,U006,demouser3,Demo,User3,demo3@example.com,USER,C,,,<hash>,0,...,...
sim_demo,U007,demouser4,Demo,User4,demo4@example.com,USER,D,,,<hash>,0,...,...
sim_demo,U008,demouser5,Demo,User5,demo5@example.com,USER,E,,,<hash>,0,...,...
sim_demo,U009,demouser6,Demo,User6,demo6@example.com,USER,F,,,<hash>,0,...,...
```

### 5.4 Retired: `code/team_dashboard/usernames.csv`

Deleted after migration.

---

## 6. Files to Modify

| File | Change |
|------|--------|
| `code/team_dashboard/services/team_auth.py` | Replace flat-CSV auth with per-simulation `users.csv` lookup across active simulations. Remove `_TEAM_ID_MAP` and `_CREDENTIALS_PATH`. |
| `code/team_dashboard/app.py` | Remove `DEFAULT_SIM_ID` constant. Update login handler to use new auth flow. Add locked-simulation check. |
| `code/admin_dashboard/app.py` | Remove `DEFAULT_SIM_ID`. Read `sim_id` from session in every route. Add simulation management and user management routes. Add simulation picker. |
| `code/admin_dashboard/services/admin_actions.py` | Remove `DEFAULT_SIM_ID`. Accept `simulation_id` parameter dynamically in all action functions. |
| `code/admin_dashboard/services/team_data.py` | Remove `DEFAULT_SIM_ID`. Accept `simulation_id` parameter dynamically. |
| `code/team_dashboard/main.py` | Add demo-simulation auto-provisioning on startup. Rename `AdminGuardMiddleware` to `DashboardGuardMiddleware` to reflect multi-role access. Add `sim_id` validation and per-role action enforcement (see Section 4.9.3). |
| `app/modules/setup_simulation.py` | Add team-user credential generation with extended profile fields. Add `admin/simulations.csv` registry update. |
| `app/modules/user_management.py` | Extend with full CRUD: edit profile, remove user, change password, change role, assign to simulation. Update `users.csv` schema to include new profile fields. |
| `app/ui/team_view.py` | Replace hardcoded `SIM_ID = "sim_001"` with dynamic value. |
| `app/auth/login_manager.py` | Implement centralized multi-sim login logic (currently empty). |
| `app/auth/password_manager.py` | Implement password hashing helpers (currently empty). |

### Files NOT Modified

| File | Reason |
|------|--------|
| `app/storage/spaces_store.py` | Already multi-sim capable |
| `app/storage/config.py` | No change needed |
| `app/data/csv_manager.py` | Already uses `sim_id` prefix |
| All core models (`cost_model.py`, `demand_model.py`, `pricing_model.py`, etc.) | Simulation-agnostic pure functions |
| `backup_spaces.py` | Backs up entire bucket (all simulations) |

---

## 7. New Files

| File | Purpose |
|------|---------|
| `app/auth/login_manager.py` | Centralized multi-sim login: scan active simulations, find user, authenticate, return sim context. (File exists but is currently empty.) |
| `app/auth/password_manager.py` | Password hashing/verification utilities. (File exists but is currently empty.) |
| `app/modules/simulation_management.py` | Simulation Management module: create, lock/unlock, remove simulations. Manages `admin/simulations.csv`. |
| `code/admin_dashboard/templates/select_simulation.html` | Simulation picker page for admin users with access to multiple simulations. |
| `code/admin_dashboard/templates/manage_simulations.html` | Simulation management page: list, create, lock/unlock, remove simulations. |
| `code/admin_dashboard/templates/manage_users.html` | User management page: list, create, edit, lock/unlock, remove users. |
| `scripts/migrate_usernames.py` | One-time migration script: reads `usernames.csv`, creates hashed entries in `sim_001/users.csv`, registers `sim_001` in `admin/simulations.csv`. |
| `scripts/provision_demo.py` | Standalone script to provision the demo simulation and demo accounts. Also called automatically on app startup. |

---

## 8. Migration Plan

### Step 1: Create `admin/simulations.csv`

Register the existing `sim_001` in the new global registry.

### Step 2: Populate `sim_001/users.csv` with Team Credentials

Run a migration script that:
1. Reads `code/team_dashboard/usernames.csv`.
2. For each team entry, creates a row in `sim_001/users.csv` with a bcrypt-hashed password, the correct `team_id` (from `_TEAM_ID_MAP`), and placeholder profile fields.
3. Ensures the admin user is also present.

### Step 3: Provision Demo Simulation

Run `scripts/provision_demo.py` to create `sim_demo` with all seven demo accounts.

### Step 4: Update Auth Flow

Replace `team_auth.py` login logic with the new multi-sim lookup.

### Step 5: Update Admin Dashboard

Replace all `DEFAULT_SIM_ID` references with session-based `sim_id`. Add simulation management and user management pages.

### Step 6: Remove Legacy Files

Delete `code/team_dashboard/usernames.csv` and `app/data/passwords/usernames.csv`.

### Step 7: Verify

- Demo accounts (`demoadmin`, `demouser1`–`demouser6`) can log in and are routed to `sim_demo`.
- Existing `sim_001` users can log in with unchanged passwords.
- Admin can create a new simulation (`sim_002`) from the Simulation Management page.
- Admin can create, edit, lock, unlock, and remove users from the User Management page.
- Team users in `sim_002` are automatically routed to the correct simulation upon login.
- Locked simulations reject team logins.
- CLI commands continue to work with explicit `simulation_id` argument.

---

## 9. User Experience

### 9.1 Team User Login

1. Navigate to `/` (login page).
2. Enter username and password.
3. System finds the user's simulation automatically.
4. Redirected to `/team` — the team dashboard displays data for the correct simulation.

No simulation selector is shown. No change to the login UI from the team user's perspective.

### 9.2 Professor / TA / Admin Login (Single Simulation)

1. Navigate to `/` (login page).
2. Enter credentials.
3. System finds the matching simulation.
4. Redirected to `/admin` — the admin dashboard displays data for that simulation.
5. Dashboard controls are filtered by role:
   - **TA** sees team data and the "Next Round" button only.
   - **Professor** sees team data, "Next Round", "Create Simulation", "Start", and "Stop" buttons.
   - **Admin** sees everything including user management and simulation deletion.

### 9.3 Professor / TA / Admin Login (Multiple Simulations)

1. Navigate to `/` (login page).
2. Enter credentials.
3. System finds multiple matching simulations.
4. Redirected to `/admin/select-simulation` — a picker page listing available simulations.
5. Select a simulation → redirected to `/admin`.
6. A "Switch simulation" link in the admin header allows changing context without logging out.

### 9.4 Creating a New Simulation (Professor or Admin)

1. From the admin dashboard, navigate to **Simulation Management**.
2. Click "Create New Simulation." *(Visible to Professor and Admin only; hidden from TA.)*
3. Enter simulation ID, name, number of rounds, admin credentials, and optional school/course IDs.
4. System calls `setup_simulation` with the new `simulation_id`.
5. Team users are created with auto-generated passwords.
6. A **credentials report** is displayed with all usernames and passwords in a printable format.

### 9.5 Managing Simulations (Admin)

1. From the admin dashboard, navigate to **Simulation Management**.
2. View a table of all simulations with status, lock state, and last update.
3. **Professors** can Start and Stop simulations they have access to.
4. **Admins** can additionally **Lock**, **Unlock**, and **Remove** simulations.
5. Removing a simulation requires typing the `simulation_id` to confirm.
6. **TAs** can view the simulation list but have no action buttons.

### 9.6 Managing Users (Admin Only)

1. From the admin dashboard, navigate to **User Management**. *(Visible to Admin only.)*
2. View all users in the current simulation in a searchable table.
3. Click **Create User** to add a new user with first name, last name, email, role, team, school ID, and course ID.
4. Use per-row action buttons:
   - **Edit** — update profile fields.
   - **Lock / Unlock** — toggle login access.
   - **Change Password** — set a new password.
   - **Change Role** — switch among User, Professor, TA, and Admin.
   - **Remove** — delete the user (with confirmation).

### 9.7 Demo Experience

1. Navigate to `/` (login page).
2. Log in as `demoadmin` / `DemoAdmin2026!` → routed to admin dashboard for `sim_demo` with full Admin access.
3. Or log in as `demoprof` / `DemoProf2026!` → routed to admin dashboard for `sim_demo` with Professor-level access.
4. Or log in as `demota` / `DemoTA2026!` → routed to admin dashboard for `sim_demo` with TA-level access (Next Round only).
5. Or log in as `demouser1` / `DemoUser1!` → routed to team dashboard for `sim_demo` as Airline A.
6. The demo simulation behaves identically to a real simulation — full round lifecycle, decisions, results.

---

## 10. Open Questions

| # | Question | Notes |
|---|----------|-------|
| 1 | Should team usernames be globally unique across all simulations, or unique only within a simulation? | Global uniqueness simplifies the login scan but limits flexibility. Per-simulation uniqueness requires disambiguation (unlikely for team users). **Recommendation: globally unique usernames.** |
| 2 | Should privileged users (Professor/TA/Admin) be shared across simulations or per-simulation? | Per-simulation accounts are more secure; shared accounts are more convenient. **Recommendation: per-simulation accounts, with the option for the same person to have accounts in multiple simulations (detected automatically at login).** |
| 3 | Should team passwords be auto-generated at setup or admin-specified? | Auto-generated is faster; admin-specified gives instructors control. **Recommendation: auto-generated with option to override, and a "credentials report" page the admin can print.** |
| 4 | Should the login page show the simulation name after login, or only on the dashboard? | Showing it on the dashboard header is sufficient. |
| 5 | Naming convention for new simulation IDs? | Options: auto-increment (`sim_002`), user-specified (e.g. `sim_mba_spring26`), or both. **Recommendation: user-specified with validation (alphanumeric + underscores).** |
| 6 | Should the demo simulation passwords be configurable via environment variables? | Hardcoded well-known passwords are convenient for demos but a security consideration if deployed publicly. **Recommendation: hardcoded defaults, documented as not for production use.** |
| 7 | Should "Assign to simulation" move the user or copy them? | Moving removes the user from the source simulation. Copying creates a duplicate with a new `user_id`. **Recommendation: move by default, with copy as an option.** |
| 8 | Should `school_id` and `course_id` be free-text or selected from a predefined list? | Free-text is simpler to implement. A predefined list avoids typos but requires maintenance. **Recommendation: free-text initially, with optional validation later.** |
| 9 | Should Professors be able to manage users within their own simulations? | Currently only Admins can manage users. Professors may need to add/remove students. **Recommendation: keep user management Admin-only initially; revisit based on instructor feedback.** |
| 10 | ~~Should TAs be able to undo rounds?~~ | **Resolved: Yes.** TAs can undo rounds, same as Professors. |
