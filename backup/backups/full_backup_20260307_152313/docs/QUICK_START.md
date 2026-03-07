# Airline Simulation — Quick Start Guide

A step-by-step guide for new administrators to set up and run a simulation.

---

## 1. Start the Server

```bash
cd /workspaces/airline_sim
python run_admin_dashboard.py
```

| Option | Command |
|--------|---------|
| Custom port | `python run_admin_dashboard.py --port 9000` |
| Auto-reload (dev) | `python run_admin_dashboard.py --reload` |

The server starts at **http://localhost:8080** and serves both the Admin and Team dashboards.

---

## 2. Log In

Open **http://localhost:8080/team/login** in your browser.

If this is your first time, you'll need to create a simulation first (see Step 3). If a simulation already exists, log in with your admin credentials.

---

## 3. Create a Simulation

Navigate to **Simulations** (top-right menu) or go to `/admin/simulations`.

Fill in the **Create New Simulation** form:

| Field | Example | Notes |
|-------|---------|-------|
| Simulation ID | `sim_mba_spring26` | Letters, numbers, underscores only |
| Display Name | `MBA Spring 2026` | Friendly name shown in the UI |
| Rounds | `5` | Number of decision periods (1–20) |
| Admin User | *(leave blank)* | Auto-generated if empty |
| Admin Pass | *(leave blank)* | Auto-generated if empty |

Click **Create**. This generates:
- 1 admin account
- 6 team accounts (Team A through Team F)

> **Important:** Note down the generated usernames and passwords. You will need to distribute team credentials to your students.

---

## 4. Set Up the Simulation

Go to the **Admin Dashboard** (`/admin`).

1. Enter a **Simulation Name** and **Total Rounds** in the Setup section.
2. Click **Set Up**.

This initialises all data files for the simulation.

---

## 5. Start the Simulation

On the Admin Dashboard, click **Start Simulation**.

The simulation status changes to `STARTED` and teams can now log in and enter decisions.

---

## 6. Distribute Credentials to Teams

Share each team's login with the corresponding group of students:

| Account | Username Format | Dashboard |
|---------|----------------|-----------|
| Admin | `admin` or `admin_<sim_id>` | Admin |
| Team A | `teama_<sim_id>` | Team |
| Team B | `teamb_<sim_id>` | Team |
| Team C | `teamc_<sim_id>` | Team |
| Team D | `teamd_<sim_id>` | Team |
| Team E | `teame_<sim_id>` | Team |
| Team F | `teamf_<sim_id>` | Team |

Teams log in at the same URL: **http://localhost:8080/team/login**

---

## 7. Teams Enter Decisions

Each round, every team submits one set of decisions:

| Decision | Range |
|----------|-------|
| Flights per Day | 0–5 |
| Business Price | $50–$1,000 |
| Leisure Price | $50–$1,000 |
| Branding Level | Low / Medium / High |
| Product Strategy | Low / Medium / High |

Teams click **Save Decisions** to submit. They can also click **Undo** to revert to defaults before the round is processed.

---

## 8. Monitor & Advance Rounds

On the Admin Dashboard, the **Decision Status** card shows which teams have submitted (✔) or are still pending (✗).

Once all teams have submitted (or you're ready to proceed):

1. Click **Move to Next Round**.
2. The simulation engine processes results (revenue, market share, profit, etc.).
3. Teams can now enter decisions for the next round.

Repeat this for each round until the final round.

---

## 9. End the Simulation

After the last round has been processed, click **End Simulation**.

- The status changes to `ENDED`.
- No further decisions can be submitted.
- Click **View Report** to see a printable summary of all rounds with final standings.

---

## Key Admin Operations

| Action | How |
|--------|-----|
| **Undo Last Round** | Admin Dashboard → Undo Last Period (reverts the most recent round) |
| **Lock Simulation** | Simulations page → Lock (temporarily blocks team logins) |
| **Unlock Simulation** | Simulations page → Unlock |
| **Reset a Password** | Users page (`/admin/users`) → Change Password |
| **Lock a User** | Users page → Lock (blocks a specific user) |
| **Switch Simulations** | Use the dropdown in the top-right header, or go to Simulations page → Switch |
| **Delete a Simulation** | Simulations page → Remove (⚠️ permanent, cannot be undone) |

---

## Workflow at a Glance

```
Create Simulation → Set Up → Start
                                ↓
                    ┌──── Round Loop ────┐
                    │                    │
                    │  Teams submit      │
                    │  decisions         │
                    │       ↓            │
                    │  Admin advances    │
                    │  to next round     │
                    │                    │
                    └────────────────────┘
                                ↓
                         End Simulation
                                ↓
                          View Report
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't log in | Verify the username and password; check that the simulation is not locked |
| Teams can't see the decision form | Make sure the simulation status is `STARTED` |
| Forgot a team's password | Go to Users page → Change Password |
| Need to redo a round | Click Undo Last Period on the Admin Dashboard |
| Port already in use | Run `lsof -ti:8080 \| xargs kill -9` then restart the server |
