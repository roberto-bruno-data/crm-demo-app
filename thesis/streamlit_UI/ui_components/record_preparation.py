import streamlit as st
from thesis.streamlit_UI.ui_components.constants import RENAME_MAP, UI_RENAME
from thesis.logic.helpers import extract_system_record

def prepare_records(selected_row):
    sf = extract_system_record(selected_row, "_1", RENAME_MAP)
    ns = extract_system_record(selected_row, "_2", RENAME_MAP)

    sf_records = sf.to_dict(orient="records")
    ns_records = ns.to_dict(orient="records")

    if not sf_records or not ns_records:
        st.error("Fehler beim Laden der Datensätze.")
        st.stop()

    sf_snapshot = sf_records[0]
    ns_snapshot = ns_records[0]

    display_attrs = list(UI_RENAME.values())

    salesforce_df = sf.rename(columns=UI_RENAME)[display_attrs]
    netsuite_df   = ns.rename(columns=UI_RENAME)[display_attrs]

    return salesforce_df, netsuite_df, sf_snapshot, ns_snapshot, display_attrs

def build_model_info(selected_row):
    return {
        "prob": selected_row["prob"],
        "match_category": selected_row["match_category"],
        "top_features": selected_row["top_features"],
        "similarity_sentence": selected_row["similarity_sentence"],
        "detailed_explanation": selected_row["detailed_explanation"]
    }