from pathlib import Path

from app.ui.components import (
    build_ui_snapshot,
    card,
    card_end,
    configure_page,
    get_streamlit,
    render_right_insight_panel,
    render_sidebar_navigation,
    render_standard_header,
)
from app.ui.layout import load_css, shell

def render(sim_id: str):
    st = get_streamlit()
    configure_page(st)
    load_css()

    root_dir = Path("simulations")
    snapshot = build_ui_snapshot(simulation_id=sim_id, root_dir=root_dir)
    render_standard_header(simulation_id=sim_id, snapshot=snapshot)

    with st.sidebar:
        render_sidebar_navigation(st, active_item="Home")

    def main_renderer() -> None:
        card("Workspace", "Choose the operating view for this session.")
        view = st.radio("View", ["Admin", "Team"], horizontal=True)
        st.write(f"Selected: **{view}**")
        card_end()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        card("Lifecycle Controls", "Quick lifecycle actions")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.button("Start", type="primary", use_container_width=True)
        with c2:
            st.button("Move Next", use_container_width=True)
        with c3:
            st.button("Undo", use_container_width=True)
        with c4:
            st.button("End", use_container_width=True)
        card_end()

    def insight_renderer() -> None:
        render_right_insight_panel(st, snapshot=snapshot)

    shell(main_renderer, insight_renderer)


def main() -> None:
    render("sim_001")


if __name__ == "__main__":
    main()