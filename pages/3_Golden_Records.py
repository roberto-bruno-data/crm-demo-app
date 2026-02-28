import streamlit as st
import pandas as pd

from streamlit_UI.ui_components.constants import UI_RENAME
from auth import require_auth
require_auth()

if "final_grs" not in st.session_state:
    st.session_state["final_grs"] = []

if len(st.session_state["final_grs"]) == 0:
    st.info("Noch keine Golden Records vorhanden.")
else:
    df = pd.DataFrame(st.session_state["final_grs"]).set_index("pair_id")
    st.dataframe(df, width='stretch')

SF_SCHEMA = {
    ui_name: f"sf_{raw_name}"
    for raw_name, ui_name in UI_RENAME.items()
}

NS_SCHEMA = {
    ui_name: f"ns_{raw_name}"
    for raw_name, ui_name in UI_RENAME.items()
}

if len(st.session_state["final_grs"]) > 0:
    st.markdown("---")
    st.subheader("Download Golden Records für NetSuite & Salesforce")
    gr_df = pd.DataFrame(st.session_state["final_grs"])

    # Only keep attributes that actually exist (important for partial GRs)
    sf_cols = [c for c in SF_SCHEMA.keys() if c in gr_df.columns]
    ns_cols = [c for c in NS_SCHEMA.keys() if c in gr_df.columns]

    sf_df = gr_df[sf_cols].rename(columns=SF_SCHEMA)
    ns_df = gr_df[ns_cols].rename(columns=NS_SCHEMA)

    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "⬇️ Download GRs für Salesforce",
            data=sf_df.to_csv(index=False),
            file_name="golden_records_salesforce.csv",
            mime="text/csv",
            width="stretch"
        )

    with c2:
        st.download_button(
            "⬇️ Download GRs für NetSuite",
            data=ns_df.to_csv(index=False),
            file_name="golden_records_netsuite.csv",
            mime="text/csv",
            width="stretch"
        )
