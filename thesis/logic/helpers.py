import numpy as np
import pandas as pd
import streamlit as st
from collections import Counter

def convert_value(val):

    if val is None:
        return None

    if isinstance(val, dict):
        return {k: convert_value(v) for k, v in val.items()}

    if isinstance(val, (list, tuple, set)):
        return [convert_value(v) for v in val]

    if isinstance(val, np.ndarray):
        return [convert_value(v) for v in val.tolist()]

    if isinstance(val, pd.Series):
        return [convert_value(v) for v in val.tolist()]

    if isinstance(val, (np.integer,)):
        return int(val)

    if isinstance(val, (np.floating,)):
        return float(val)

    if isinstance(val, (np.bool_,)):
        return bool(val)

    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass

    return val

def format_cluster_label(cluster_with_names, cid):
    subset = cluster_with_names[cluster_with_names["cluster_id"] == cid]

    names = subset["full_name"].dropna().unique().tolist()
    size = len(subset)

    if not names:
        return f"Cluster {cid} — {size} Datensätze"

    display_names = names[:2]

    return f"{' / '.join(display_names)} — {size} Datensätze"

def render_divider():
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

def is_attr_locked(cluster, attr, cluster_entities_df):
    values = (
        cluster_entities_df[attr]
        .dropna()
        .astype(str)
        .str.strip()
    )
    value_counts = Counter(values)

    cluster_size = len(cluster_entities_df)
    is_unique = (
        len(value_counts) == 1
        and sum(value_counts.values()) == cluster_size
    )

    user_locked = st.session_state.get(f"user_lock__{cluster}__{attr}", False)

    return user_locked or is_unique

def extract_system_record(row, suffix, rename_map):
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]

    cols = [c for c in row.index if c.endswith(suffix)]

    data = {
        rename_map.get(c.replace(suffix, ""), c.replace(suffix, "")): row[c]
        for c in cols
    }

    return pd.DataFrame([data])