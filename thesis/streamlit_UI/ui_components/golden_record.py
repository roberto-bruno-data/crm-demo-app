import pandas as pd
import streamlit as st
from thesis.logic.golden_record_service import save_golden_record

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
    cluster_pairs
):
    gr_df = pd.DataFrame(golden_record, index=["Golden Record"]).T

    gr_col, action_col = st.columns([4, 1])

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

        if st.button(
            "➕\nZu Golden Records\nhinzufügen",
            key=f"add_gr__{context_id}",
            disabled=not all_locked,
            width='stretch'
        ):
            print("THRESHOLD:", type(threshold))
            print("CLUSTER_PAIRS:", type(cluster_pairs))
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
            st.success("✅ Hinzugefügt")


# “goldensync.io produces evidence, not outcomes.”