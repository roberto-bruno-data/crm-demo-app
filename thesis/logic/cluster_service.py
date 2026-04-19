from erlib.db import get_clusters, get_resolved_clusters, get_harmonized_entities, engine

from thesis.logic.golden_record_service import resolve_attribute
import streamlit as st
from thesis.logic.cluster_metrics import compute_cluster_score
from thesis.config.preferences import load_preferences

from erlib.utils.constants import ATTRIBUTES
import pandas as pd


def render_cluster_metrics_and_merge_section(
    selected_cluster,
    run_id,
    engine,
    review_df,
    cluster_df,
    cluster_scores_df
) -> tuple[pd.DataFrame, pd.DataFrame]:

    if selected_cluster is None:
        return pd.DataFrame(), pd.DataFrame()

    cluster_entities_df = get_cluster_entities_df_cached(run_id, selected_cluster)
    cluster_entities = cluster_entities_df["entity_id"].tolist()

    cluster_pairs = review_df[
        review_df["entity_id_a"].isin(cluster_entities) &
        review_df["entity_id_b"].isin(cluster_entities)
    ]

    if cluster_pairs.empty:
        st.info("Keine Verbindungen im Cluster vorhanden")
        return pd.DataFrame(), cluster_entities_df

    # --- Compute metrics ---
    cluster_size = cluster_entities_df.shape[0]

    prefs = load_preferences()
    threshold = prefs.get("auto_merge_threshold", 0.95)

    cluster_metrics = compute_cluster_score(cluster_pairs, cluster_size)
    score = cluster_metrics["score"]

    # --- MAIN: Cluster quality ---
    st.markdown("#### 📊 Cluster Qualität")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Cluster-Score", f"{score:.3f}")

    with col2:
        st.metric("Größe", cluster_size)


    # --- STATUS (main signal) ---
    color, message = classify_cluster(cluster_metrics)

    if color == "green":
        st.markdown("**✅ Sehr konsistentes Cluster**")
    elif color == "yellow":
        st.warning(f"⚠️ {message}")
    else:
        st.error(f"❌ {message}")

    # --- AUTO MERGE DECISION ---
    st.markdown("#### ⚡ Auto-Merge")

    can_merge = score >= threshold

    label = f"⚡ Auto-Merge (≥ {threshold:.2f})"

    st.write("") 
    
    if st.button(
        label,
        type="primary",
        disabled=not can_merge
    ):
        auto_merge_cluster(
            selected_cluster,
            cluster_entities_df,
            ATTRIBUTES
        )
        st.success("Auto-Merge durchgeführt")
        st.rerun()

    # --- DETAILS (collapsed) ---
    with st.expander("🔬 Details (Metriken)"):
        st.caption(
            f"Harmonic: {cluster_metrics['harmonic']:.3f} | "
            f"Mean: {cluster_metrics['mean']:.3f} | "
            f"Min: {cluster_metrics['min']:.3f} | "
            f"Coverage: {cluster_metrics['coverage']:.2f}"
        )

    return cluster_pairs, cluster_entities_df

@st.cache_data(show_spinner=False)
def get_cluster_entities_df_cached(run_id: str, cluster_id: int):
    cluster_df = get_clusters(run_id, engine)
    entities_df = get_harmonized_entities(run_id, engine)

    cluster_entities = cluster_df.loc[
        cluster_df["cluster_id"] == cluster_id, "entity_id"
    ]

    return entities_df[
        entities_df["entity_id"].isin(cluster_entities)
    ]


def format_cluster_with_names(cid, cluster_scores_df, cluster_with_names):
    rows = cluster_scores_df[cluster_scores_df["cluster_id"] == cid]

    if rows.empty:
        return f"{cid}"

    row = rows.iloc[0]

    if row["score"] > 0.9:
        icon = "🟢"
    elif row["score"] > 0.75:
        icon = "🟡"
    else:
        icon = "🔴"

    names = cluster_with_names[
        cluster_with_names["cluster_id"] == cid
    ]["full_name"].dropna().unique()[:2]

    names_str = ", ".join(names) if len(names) > 0 else "–"

    return f"{icon} {row['size']} • {row['score']:.2f} • {names_str}"

def classify_cluster(metrics):
    harmonic = metrics["harmonic"]
    min_prob = metrics["min"]

    if min_prob < 0.3:
        return "red", "Kritisch: sehr schwache Verbindung"

    if harmonic > 0.9:
        return "green", "Sehr konsistentes Cluster"

    if harmonic > 0.75:
        if min_prob < 0.5:
            return "yellow", "Überwiegend konsistent, einzelne schwache Verbindungen"
        return "yellow", "Überwiegend konsistent, aber prüfen"

    return "red", "Cluster inkonsistent"

def auto_merge_cluster(cluster_id, cluster_entities_df, attributes):
    for attr in attributes:
        values = cluster_entities_df[attr].tolist()

        value, locked = resolve_attribute(values)

        # 👉 Werte in Session State setzen (dein bestehendes Schema!)
        st.session_state[f"value__{cluster_id}__{attr}"] = value

        if locked:
            st.session_state[f"user_lock__{cluster_id}__{attr}"] = True

def get_open_clusters(run_id: str, engine):
    cluster_df = get_clusters(run_id, engine)

    resolved_clusters = get_resolved_clusters(run_id, engine)

    cluster_df = cluster_df[
        ~cluster_df["cluster_id"].isin(resolved_clusters)
    ]

    cluster_df = cluster_df[cluster_df["cluster_size"] > 1]

    return cluster_df.sort_values("cluster_size", ascending=False)

def get_cluster_entities_df(run_id: str, cluster_id: int, engine):

    cluster_df = get_clusters(run_id, engine)
    entities_df = get_harmonized_entities(run_id, engine)

    cluster_entities = cluster_df.loc[
        cluster_df["cluster_id"] == cluster_id, "entity_id"
    ]

    return entities_df[
        entities_df["entity_id"].isin(cluster_entities)
    ]