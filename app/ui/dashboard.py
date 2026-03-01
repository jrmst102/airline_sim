from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

AUTO_REFRESH_SECONDS = 60


def load_css_local() -> None:
    """
    Loads theme.css and styles.css from the SAME folder as this dashboard.py file.
    """
    here = Path(__file__).resolve().parent
    css_files = [here / "theme.css", here / "styles.css"]

    css_chunks: list[str] = []
    for css_path in css_files:
        if css_path.exists():
            css_chunks.append(css_path.read_text(encoding="utf-8"))

    if css_chunks:
        st.markdown(f"<style>{'\n'.join(css_chunks)}</style>", unsafe_allow_html=True)


def auto_refresh() -> None:
    """
    Simple browser refresh every N seconds.
    """
    st.markdown(
        f"<meta http-equiv='refresh' content='{AUTO_REFRESH_SECONDS}'>",
        unsafe_allow_html=True,
    )


def get_simulation_root() -> Path:
    """
    Resolve the simulation folder:
      - SIMULATIONS_ROOT (default: ./simulations)
      - SIMULATION_ID (default: sim_001)
    """
    sims_root = Path(os.getenv("SIMULATIONS_ROOT", "simulations")).resolve()
    sim_id = os.getenv("SIMULATION_ID", "sim_001")
    return sims_root / sim_id


def read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        return df
    except Exception:
        return None


def infer_status(sim_dir: Path) -> dict:
    """
    Infers status from common files in the simulation directory.
    Minimal and robust: if files don't exist, we still show folder + timestamps.
    """
    status: dict = {
        "simulation_dir": str(sim_dir),
        "exists": sim_dir.exists(),
        "current_round": None,
        "phase": None,
        "last_modified": None,
        "files_found": [],
    }

    if not sim_dir.exists():
        return status

    # Folder last modified
    try:
        status["last_modified"] = datetime.fromtimestamp(sim_dir.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        pass

    # Candidate files (safe guesses)
    candidate_json = [
        sim_dir / "state.json",
        sim_dir / "status.json",
        sim_dir / "simulation.json",
        sim_dir / "meta.json",
    ]
    candidate_csv = [
        sim_dir / "state.csv",
        sim_dir / "status.csv",
        sim_dir / "rounds.csv",
    ]

    for p in candidate_json + candidate_csv:
        if p.exists():
            status["files_found"].append(p.name)

    # Prefer JSON state if present
    state = read_json_if_exists(sim_dir / "state.json") or read_json_if_exists(sim_dir / "status.json")
    if isinstance(state, dict):
        # Try common field names
        for k in ["round", "current_round", "round_number"]:
            if k in state and state[k] is not None:
                status["current_round"] = state[k]
                break
        for k in ["phase", "state", "stage"]:
            if k in state and state[k] is not None:
                status["phase"] = state[k]
                break

    # Fallback: CSV status/state
    if status["current_round"] is None:
        df = read_csv_if_exists(sim_dir / "state.csv") or read_csv_if_exists(sim_dir / "status.csv")
        if df is not None and not df.empty:
            for col in df.columns:
                if col.strip().lower() in ["round", "current_round", "round_number"]:
                    vals = pd.to_numeric(df[col], errors="coerce").dropna()
                    if not vals.empty:
                        status["current_round"] = int(vals.max())
                        break

            if status["phase"] is None:
                for col in df.columns:
                    if col.strip().lower() in ["phase", "state", "stage", "status"]:
                        v = df[col].dropna()
                        if not v.empty:
                            status["phase"] = str(v.iloc[-1])
                            break

    # Fallback: rounds.csv (infer round)
    if status["current_round"] is None:
        rounds = read_csv_if_exists(sim_dir / "rounds.csv")
        if rounds is not None and not rounds.empty:
            cols = {c.strip().lower(): c for c in rounds.columns}
            if "round" in cols:
                vals = pd.to_numeric(rounds[cols["round"]], errors="coerce").dropna()
                if not vals.empty:
                    status["current_round"] = int(vals.max())
            if status["phase"] is None and "status" in cols:
                v = rounds[cols["status"]].dropna()
                if not v.empty:
                    status["phase"] = str(v.iloc[-1])

    return status


def main() -> None:
    st.set_page_config(page_title="Airline Simulation Dashboard", layout="wide")

    load_css_local()
    auto_refresh()

    # Header (uses your CSS if present; otherwise still works)
    st.markdown(
        """
        <div class="air-header">
          <div>
            <div class="title">Airline Simulation Dashboard</div>
            <div class="sub">Read-only status view • Auto-refresh every 60s</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Controls row: only Refresh button + timestamp
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Refresh", type="primary", use_container_width=True):
            st.rerun()
    with c2:
        st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

    sim_dir = get_simulation_root()
    status = infer_status(sim_dir)

    # KPI row (minimal)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Simulation Folder", "FOUND" if status["exists"] else "NOT FOUND")
    with k2:
        st.metric("Simulation ID", sim_dir.name)
    with k3:
        st.metric("Current Round", "-" if status["current_round"] is None else str(status["current_round"]))
    with k4:
        st.metric("Phase", "-" if status["phase"] is None else str(status["phase"]))

    st.divider()

    if not status["exists"]:
        st.error(f"No simulation folder found. Expected: {sim_dir}")
        st.info("Fix: create that folder, or set env vars SIMULATIONS_ROOT and SIMULATION_ID.")
        st.code(
            "export SIMULATIONS_ROOT=simulations\nexport SIMULATION_ID=sim_001\nstreamlit run dashboard.py",
            language="bash",
        )
    else:
        # Minimal status detail
        st.subheader("Simulation Status")
        st.write(f"**Path:** `{status['simulation_dir']}`")
        st.write(f"**Folder last modified:** `{status['last_modified'] or '-'}`")
        st.write(f"**Files detected:** {', '.join(status['files_found']) if status['files_found'] else '-'}")

    # Footer copyright
    st.divider()
    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:18px;
            padding:12px 0;
            font-size:12px;
            color:#6b7280;
            opacity:0.85;">
            © 2026 by Dr. Jose Mendoza
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()