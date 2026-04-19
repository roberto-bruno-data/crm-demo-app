import streamlit as st
from thesis.streamlit_UI.ui_components.record_preparation import prepare_records, build_model_info
from thesis.streamlit_UI.ui_components.views import load_config, render_comparison_table, render_model_section
from thesis.streamlit_UI.ui_components.auth import require_auth
from erlib.db import engine, get_latest_run_id, get_review_queue, get_resolved_count, load_pairs_from_db
from thesis.streamlit_UI.ui_components.review_selection import select_pair
from thesis.streamlit_UI.ui_components.golden_record import render_golden_record_panel, build_golden_record

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

#@st.cache_data
def load_data(run_id, _engine, include_resolved):
    return {
        "review_df": get_review_queue(run_id, _engine, include_resolved),
        "resolved_count": get_resolved_count(run_id, _engine),
        "total_candidates": len(load_pairs_from_db(run_id, _engine))
    }

require_auth()

def main():

    st.title("Dublettenerkennung: Review")
    
    run_id = get_latest_run_id(engine)
    st.caption(f"Run ID: {run_id[:8]}…")
    include_resolved = st.checkbox("Bereits verarbeitete Paare anzeigen")

    data = load_data(run_id, engine, include_resolved)

    review_df = data["review_df"]
    resolved_count = data["resolved_count"]
    total_candidates = data["total_candidates"]

    if include_resolved:
        open_count = total_candidates - resolved_count
    else:
        open_count = len(review_df)

    col1, col2, col3 = st.columns(3)

    progress = resolved_count / total_candidates if total_candidates > 0 else 0
    col1.metric("Offene Fälle", open_count)
    col2.metric("Bereits entschieden", resolved_count)
    col3.metric("Gesamtpaare", total_candidates)

    st.metric("Fortschritt", f"{progress:.1%}")
    st.progress(progress)

    render_review_queue(review_df, include_resolved, run_id)

def render_review_queue(review_df, include_resolved, run_id):

    selected_row = select_pair(review_df)

    salesforce_df, netsuite_df, sf_snapshot, ns_snapshot, DISPLAY_ATTRS = prepare_records(selected_row)

    model_info = build_model_info(selected_row)
    selected_pair_id = selected_row["pair_id"]

    config = load_config()
    settings = config.get("attribute_priority", {})

    render_model_section(model_info)

    st.markdown("---")
    st.subheader("Systemvergleich & Golden Record")

    show_identical = st.checkbox(
        "Auch identische Attribute anzeigen",
        value=True
    )
    if include_resolved:
        st.caption("Zeigt alle Paare (inkl. bereits entschiedene)")
    else:
        st.caption("Zeigt nur offene Fälle")
    st.caption("⭐ = präferierte Quelle")

    visible_attrs = render_comparison_table(salesforce_df, netsuite_df, selected_pair_id, settings,
                                                                      show_identical, DISPLAY_ATTRS)
        
    all_locked = all(
        st.session_state.get(f"lock__{selected_pair_id}__{a}", False)
        for a in visible_attrs
    )

    if all_locked:
        st.success("✨ Golden Record vollständig bestätigt")
    else:
        st.info("🔍 Noch offene Attribute")

    # 3) Golden Record NACH dem Rendern berechnen (state ist dann aktuell)
    golden_record = build_golden_record(selected_pair_id, visible_attrs)

    st.markdown("---")

    render_golden_record_panel(golden_record, selected_pair_id, run_id,
                               model_info, sf_snapshot, ns_snapshot, engine)

main()