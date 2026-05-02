import streamlit as st
import pandas as pd
from thesis.streamlit_UI.ui_components.constants import UI_RENAME, DISPLAY_ORDER
from thesis.streamlit_UI.ui_components.auth import require_auth
from erlib.db import engine, get_golden_records
import json
from thesis.streamlit_UI.ui_components.theme import apply_theme
from thesis.streamlit_UI.ui_components.views import render_global_sidebar, get_active_run_id

st.set_page_config(page_title="Golden Records", layout="wide")

def normalize_columns(df):
    return df.rename(columns={
        "straße": "strasse",
        "hausnummer": "hausnr",
        "e-mail": "email"
    })

SF_SCHEMA = {
    raw_name: f"sf_{raw_name}"
    for raw_name in UI_RENAME.keys()
}

NS_SCHEMA = {
    raw_name: f"ns_{raw_name}"
    for raw_name in UI_RENAME.keys()
}

apply_theme()
require_auth()

@st.cache_data
def load_data(run_id, _engine):
    return get_golden_records(run_id, _engine)

render_global_sidebar()

st.title("🏆 Golden Records")

run_id = get_active_run_id()

if run_id is None:
    st.info("Kein Run vorhanden.")
    st.stop()

golden_records = load_data(run_id, engine)

if golden_records.empty:
    st.info("Noch keine Golden Records vorhanden.")
    st.stop()

gr_df = golden_records.copy()

def safe_parse(x):
    if isinstance(x, dict):
        return x
    if not x:
        return {}
    try:
        return json.loads(x)
    except Exception:
        return {}

parsed = gr_df["golden_record"].apply(safe_parse)
gr_expanded = pd.json_normalize(parsed)
gr_expanded = normalize_columns(gr_expanded)
gr_final = pd.concat(
    [
        gr_df[["cluster_id", "created_at"]].reset_index(drop=True),
        gr_expanded.reset_index(drop=True)
    ],
    axis=1
)
st.caption("Jeder Golden Record repräsentiert eine konsolidierte Entität pro Cluster.")

col1, col2 = st.columns(2)
col1.metric("Golden Records", len(gr_final))
last_update = gr_final["created_at"].max()

if pd.notna(last_update):
    last_update = pd.to_datetime(last_update).strftime("%d.%m.%Y %H:%M")
else:
    last_update = "—"

col2.metric("Letzte Aktualisierung", last_update)
st.markdown("---")
st.subheader("Download Golden Records für NetSuite & Salesforce")

# normalize first
gr_final.columns = [c.lower() for c in gr_final.columns]
display_order = [c.lower() for c in DISPLAY_ORDER]

# THEN filter
# --- safe column ordering (drop-in) ---
base_cols = [c for c in ["cluster_id", "created_at"] if c in gr_final.columns]

display_order = [c.lower() for c in DISPLAY_ORDER]

ordered_cols = [c for c in display_order if c in gr_final.columns]

remaining_cols = [
    c for c in gr_final.columns
    if c not in base_cols + ordered_cols
]

gr_final = gr_final[base_cols + ordered_cols + remaining_cols]

gr_final = gr_final.sort_values("created_at", ascending=False)

st.caption(f"{len(gr_final)} Golden Records angezeigt (neueste zuerst)")

st.dataframe(
    gr_final,
    width="stretch",
    hide_index=True
)

# Columns based on FINAL df
sf_keys = {k.lower() for k in SF_SCHEMA.keys()}
ns_keys = {k.lower() for k in NS_SCHEMA.keys()}

ns_schema_lower = {k.lower(): v for k, v in NS_SCHEMA.items()}
sf_schema_lower = {k.lower(): v for k, v in SF_SCHEMA.items()}

sf_cols = [c for c in gr_final.columns if c in sf_keys]
ns_cols = [c for c in gr_final.columns if c in ns_keys]

missing_sf = sf_keys - set(sf_cols)
missing_ns = ns_keys - set(ns_cols)

ns_df = gr_final[ns_cols].rename(columns=ns_schema_lower)
sf_df = gr_final[sf_cols].rename(columns=sf_schema_lower)

st.caption(
    "Die Golden Records können direkt in Zielsysteme integriert werden "
    "und bilden die Grundlage für eine konsistente Kundensicht."
)

c1, c2 = st.columns(2)

with c1:
    st.download_button(
        "⬇️ Download GRs für Salesforce",
        data=sf_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"golden_records_salesforce_{run_id[:8]}.csv",
        mime="text/csv",
        width="stretch"
    )
    # if missing_sf:
    #     st.warning(f"Fehlende Salesforce-Felder: {', '.join(missing_sf)}")

with c2:
    st.download_button(
        "⬇️ Download GRs für NetSuite",
        data=ns_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"golden_records_netsuite_{run_id[:8]}.csv",
        mime="text/csv",
        width="stretch"
    )
    # if missing_ns:
    #     st.warning(f"Fehlende NetSuite-Felder: {', '.join(missing_ns)}")