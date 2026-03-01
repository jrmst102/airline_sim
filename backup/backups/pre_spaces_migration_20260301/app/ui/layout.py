import pathlib
import streamlit as st

CSS_PATH = pathlib.Path(__file__).with_name("theme.css")

def load_css():
    css = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def render_header(sim_id: str, round_label: str, phase: str, kpis: dict):
    # kpis: {"Cash": "$—", "Mkt Share": "—", "Net Profit": "—", "Alerts": "0"}
    pills = "".join(
        f"""<div class="kpi-pill"><b>{k}</b><span>{v}</span></div>"""
        for k, v in kpis.items()
    )
    st.markdown(
        f"""
        <div class="air-header">
          <div>
            <div class="title">Competitive Strategy Simulation</div>
            <div class="sub">Simulation: <b>{sim_id}</b> • {round_label} • <b>{phase}</b></div>
          </div>
          <div class="air-kpis">{pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def shell(main_renderer, insight_renderer=None):
    """
    main_renderer: callable that renders the page main content
    insight_renderer: callable that renders right column cards (optional)
    """
    # Main + Insight column widths (approx)
    # Using ratios because Streamlit columns are fractional; CSS controls the feel.
    col_main, col_insight = st.columns([5, 1], gap="large")

    with col_main:
        st.markdown('<div class="air-main">', unsafe_allow_html=True)
        main_renderer()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_insight:
        st.markdown('<div class="air-insight sticky">', unsafe_allow_html=True)
        if insight_renderer:
            insight_renderer()
        st.markdown("</div>", unsafe_allow_html=True)