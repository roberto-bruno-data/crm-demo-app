import pandas as pd
import streamlit as st
from thesis.logic.golden_record_service import save_golden_record, set_cluster_status
from sqlalchemy import text
from erlib.db import engine

@st.cache_data
def get_cluster_status_cached(run_id):
    return get_cluster_status(run_id, engine)

def render_golden_record_panel(
    golden_record,
    context_id,
    run_id,
    model_info,
    sf_snapshot,
    ns_snapshot,
    engine,
    cluster_entities_df,
    threshold,
    cluster_pairs,
    cluster_df
):
    gr_df = pd.DataFrame(golden_record, index=["Golden Record"]).T

    gr_col, action_col = st.columns([2, 1])

    with gr_col:
        st.markdown("### 🏆 Finaler Golden Record (bestätigte Attribute)")
        st.dataframe(
            gr_df.style.set_properties(
                subset=None,
                **{
                    "font-weight": "600",
                    "background-color": "#c99700",
                    "color": "#111111"
                }
            ),
            width="stretch"
        )

    with action_col:
        
        st.markdown("### ")
        st.markdown("### ")

        all_locked = len(golden_record) > 0

        
        # --- SAVE (optional) ---
        if st.button(
            "💾\nGolden Record\nspeichern",
            key=f"save_gr__{context_id}",
            disabled=not all_locked,
            width='stretch'
        ):

            save_golden_record(
                run_id=run_id,
                cluster_id=context_id,
                golden_record=golden_record,
                model_info=model_info,
                sf_snapshot=sf_snapshot,
                ns_snapshot=ns_snapshot,
                cluster_entities_df=cluster_entities_df,
                engine=engine,
                threshold=threshold,
                cluster_pairs=cluster_pairs
            )

            st.cache_data.clear()
            st.success("✅ Gespeichert")

    
        # --- MARK AS REVIEWED (immer möglich) ---
        status_key = f"cluster_status__{context_id}"

        # default
        if status_key not in st.session_state:
            status_df = get_cluster_status_cached(run_id)
                        
            match = status_df[
                status_df["cluster_id"] == context_id
            ]

            if not match.empty:
                st.session_state[status_key] = match.iloc[0]["status"]
            else:
                st.session_state[status_key] = "open"

        is_done = st.session_state[status_key] == "reviewed"

        label = "↩️ Als offen markieren" if is_done else "✅ Als geprüft markieren"

        clicked = st.button(
            label,
            key=f"status_btn__{context_id}",
            type="primary" if is_done else "secondary",
            width='stretch'
        )

        if clicked:
            new_status = "open" if is_done else "reviewed"

            set_cluster_status(run_id, context_id, new_status, engine)

            st.cache_data.clear()
            st.rerun()

def get_cluster_status(run_id, engine):
    query = text("""
        SELECT run_id, cluster_id, status
        FROM cluster_status
        WHERE run_id = :run_id
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"run_id": run_id})
    
# “goldensync.io produces evidence, not outcomes.”