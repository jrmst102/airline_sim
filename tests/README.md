# Airline Simulation (Streamlit)

Minimal Streamlit UI with **exactly three screens**:

1. **Login**
2. **Team View**
3. **Admin View**

## Constraints Implemented

- Single app file routing (no multipage app, no `pages/` directory)
- Routing is only via `st.session_state`:
  - Not authenticated → `render_login()`
  - Authenticated + role `team` → `render_team()`
  - Authenticated + role `admin` → `render_admin()`
- No extra navigation sections
- Sidebar collapse control hidden via CSS (no collapsible sidebar dependency)

## Project Files

- `main.py` — Streamlit app entrypoint and 3 screen renderers:
  - `render_login()`
  - `render_team()`
  - `render_admin()`
- `styles.css` — dashboard styling and sidebar-collapse hiding
- `requirements.txt` — Python dependencies

## Team View

Team screen includes only:

- Enter decisions
- View current decisions
- View results

## Admin View

Admin screen includes only lifecycle actions:

- Setup simulation
- Start / Next / Undo / End
- Backup / Restore / Destroy

## Run Locally (Ubuntu/Linux)

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:
   ```bash
   streamlit run main.py
   ```

4. Open in browser (from dev container):
   ```bash
   "$BROWSER" http://localhost:8501
   ```

## Notes

- This is intentionally minimal and scoped to the 3-screen requirement only.
- Authentication is session-based UI gating for demo workflow.