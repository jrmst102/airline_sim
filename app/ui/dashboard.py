from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

AUTO_REFRESH_SECONDS = 60


def _load_local_css() -> None:
    base_dir = Path(__file__).resolve().parent
    css_parts: list[str] = []

    for name in ("theme.css", "styles.css"):
        p = base_dir / name
        if p.exists():
            css_parts.append(p.read_text(encoding="utf-8"))

    css_parts.append(
        """
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }

        .air-header { left: 0 !important; }

        .main .block-container {
            max-width: 1100px !important;
            padding-top: 120px !important;
        }

        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricLabel"] label {
            color: #e5e7eb !important;
            opacity: 1 !important;
        }
        div[data-testid="stMetricValue"] { color: #ffffff !important; }

        .status-card {
            margin-top: 10px;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 12px;
            padding: 12px 14px;
            background: rgba(255,255,255,0.04);
            color: #e5e7eb;
        }
        .copyright {
            margin-top: 22px;
            text-align: center;
            color: #9ca3af;
            font-size: 0.85rem;
        }
        """
    )

    st.markdown(f"<style>{''.join(css_parts)}</style>", unsafe_allow_html=True)


def _auto_refresh() -> None:
    st.markdown(
        f"<meta http-equiv='refresh' content='{AUTO_REFRESH_SECONDS}'>",
        unsafe_allow_html=True,
    )


def _discover_csvs() -> list[Path]:
    root = Path(__file__).resolve().parents[2]
    candidates = [root / "data", root / "output", root]
    files: list[Path] = []
    for d in candidates:
        if d.exists():
            files.extend(sorted(d.glob("*.csv")))

    seen = set()
    unique = []
    for f in files:
        key = str(f.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _read_all_rows(csv_files: list[Path]) -> tuple[int, int | None, datetime | None]:
    total_rows = 0
    max_round: int | None = None
    latest_mtime: datetime | None = None

    for f in csv_files:
        try:
            df = pd.read_csv(f)
            total_rows += len(df)

            round_col = next((c for c in df.columns if c.strip().lower() == "round"), None)
            if round_col is not None:
                vals = pd.to_numeric(df[round_col], errors="coerce").dropna()
                if not vals.empty:
                    candidate = int(vals.max())
                    max_round = candidate if max_round is None else max(max_round, candidate)

            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            latest_mtime = mtime if latest_mtime is None else max(latest_mtime, mtime)
        except Exception:
            continue

    return total_rows, max_round, latest_mtime


def _to_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "started", "running"}:
        return True
    if s in {"0", "false", "no", "n", "stopped", "not_started", "idle"}:
        return False
    return None


def _simulation_started(csv_files: list[Path], detected_round: int | None) -> tuple[bool, str]:
    # Prefer explicit state file if present
    state_candidates = [
        p for p in csv_files
        if p.name.lower() in {"simulation_state.csv", "sim_state.csv", "simulation.csv"}
    ]

    state_cols_started = {"started", "is_started", "simulation_started", "running", "is_running"}
    state_cols_round = {"round", "current_round"}

    for f in state_candidates:
        try:
            df = pd.read_csv(f)
            if df.empty:
                continue
            last = df.iloc[-1]

            started_val = None
            round_val = None

            for c in df.columns:
                cl = c.strip().lower()
                if cl in state_cols_started:
                    started_val = _to_bool(last[c])
                if cl in state_cols_round:
                    num = pd.to_numeric(pd.Series([last[c]]), errors="coerce").dropna()
                    if not num.empty:
                        round_val = int(num.iloc[0])

            if started_val is True:
                return True, f"Started (from {f.name})"
            if started_val is False and (round_val is None or round_val <= 0):
                return False, f"Not started (from {f.name})"
        except Exception:
            continue

    # Fallback: infer from rounds in result-like CSVs
    if detected_round is not None and detected_round > 0:
        return True, "Started (inferred from round data)"

    return False, "Simulation has not started yet"


def main() -> None:
    st.set_page_config(page_title="Simulation Dashboard", layout="wide")
    _load_local_css()
    _auto_refresh()

    st.markdown(
        """
        <div class="air-header">
          <div class="title">Simulation Dashboard</div>
          <div class="sub">Status-only view</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Refresh", type="primary"):
        st.rerun()

    csv_files = _discover_csvs()
    total_rows, round_number, latest_mtime = _read_all_rows(csv_files)
    started, start_reason = _simulation_started(csv_files, round_number)

    # Gate: show clear waiting state until simulation starts
    if not started:
        st.info(f"{start_reason}. Click **Refresh** after admin starts the simulation.")
        st.markdown(
            f"<div class='copyright'>© {datetime.now().year} Airline Simulation</div>",
            unsafe_allow_html=True,
        )
        return

    now = datetime.now(timezone.utc)
    age_seconds = int((now - latest_mtime).total_seconds()) if latest_mtime else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Round", "-" if round_number is None else round_number)
    c2.metric("CSV Files", len(csv_files))
    c3.metric("Total Rows", total_rows)
    c4.metric("Data Age (sec)", "-" if age_seconds is None else age_seconds)

    last_refresh_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_data_local = (
        latest_mtime.astimezone().strftime("%Y-%m-%d %H:%M:%S") if latest_mtime else "N/A"
    )
    st.markdown(
        f"""
        <div class="status-card">
          <strong>Status:</strong> OK<br/>
          <strong>Start check:</strong> {start_reason}<br/>
          <strong>Last refresh:</strong> {last_refresh_local}<br/>
          <strong>Latest data timestamp:</strong> {latest_data_local}<br/>
          <strong>Auto-refresh:</strong> every {AUTO_REFRESH_SECONDS} seconds
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='copyright'>© {datetime.now().year} Airline Simulation</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()