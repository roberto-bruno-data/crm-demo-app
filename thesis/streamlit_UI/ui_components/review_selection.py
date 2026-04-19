import pandas as pd
import streamlit as st
from thesis.streamlit_UI.ui_components.constants import COMPARE_FIELDS, SEARCH_FIELDS
from thesis.streamlit_UI.ui_components.pair_selectors import build_pair_label
from thesis.streamlit_UI.ui_components.filters import filter_side_bar, filter_identical_pairs

def select_pair(review_df):
    filtered_df = filter_side_bar(review_df.copy(), st)

    filtered_df, identical_df = filter_identical_pairs(
        filtered_df, COMPARE_FIELDS
    )
    
    if filtered_df.empty:
        st.warning("Keine Paare nach aktueller Suche / Filterung.")
        st.stop()

    st.caption(
        f"{len(identical_df)} vollständig identische Paare automatisch ausgeschlossen."
    )

    search_term = st.text_input(
        "🔎 Suche (Name, E-Mail, ID, …)",
        placeholder="z. B. Rörricht, ehendriks@example.net, 83"
    )

    if search_term:
        search_cols = [
            col for col in SEARCH_FIELDS
            if col in filtered_df.columns
        ]

        mask = filtered_df[search_cols].astype(str).apply(
            lambda col: col.str.contains(search_term, case=False, na=False)
        ).any(axis=1)

        filtered_df = filtered_df[mask].copy()

    filtered_df["pair_label"] = filtered_df.apply(build_pair_label, axis=1)
    pair_map = dict(zip(filtered_df["pair_id"], filtered_df["pair_label"]))

    selected_pair_id = st.selectbox(
        "Dublettenpaar auswählen",
        options=filtered_df["pair_id"],
        format_func=lambda x: pair_map.get(x, x)
    )

    selected_rows = filtered_df.loc[
        filtered_df["pair_id"] == selected_pair_id
    ]

    if selected_rows.empty:
        st.error("Ausgewähltes Paar nicht gefunden.")
        st.stop()

    return selected_rows.iloc[0]

def select_pair_within_cluster(cluster_pairs):
    cluster_pairs = cluster_pairs.copy()
    cluster_pairs.loc[:, "pair_label"]  = cluster_pairs.apply(build_pair_label, axis=1)

    pair_map = dict(zip(cluster_pairs["pair_id"], cluster_pairs["pair_label"]))

    selected_pair_id = st.selectbox(
        "Pair im Cluster anzeigen",
        options=cluster_pairs["pair_id"],
        format_func=lambda x: pair_map.get(x, x)
    )

    selected_row = cluster_pairs.loc[
        cluster_pairs["pair_id"] == selected_pair_id
    ]

    return selected_row.iloc[0]