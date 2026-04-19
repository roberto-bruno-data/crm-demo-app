# data_access.py
import pandas as pd
import streamlit as st

@st.cache_data
def load_pairs(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def filter_by_probability(df, min_prob=None, max_prob=None):
    if min_prob is None or max_prob is None:
        return df
    return df[(df["prob"] >= min_prob) & (df["prob"] <= max_prob)]

def filter_by_category(df, category=None):
    if not category:
        return df
    return df[df["match_category"] == category]

def apply_search(df, search_term, search_fields):
    if not search_term:
        return df

    mask = False
    for col in search_fields:
        if col in df.columns:
            mask |= df[col].astype(str).str.contains(
                search_term, case=False, na=False
            )
    return df[mask]
