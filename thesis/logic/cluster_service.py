from erlib.db import get_clusters, get_resolved_clusters, get_harmonized_entities, engine

import streamlit as st
from thesis.logic.cluster_metrics import compute_cluster_score
from thesis.config.preferences import load_preferences

from erlib.utils.constants import ATTRIBUTES
import pandas as pd
import altair as alt


def render_cluster_metrics_and_merge_section(
    selected_cluster,
    run_id,
    engine,
    review_df,
    cluster_df,
    cluster_scores_df) -> tuple[pd.DataFrame, pd.DataFrame, float | None]:

    if selected_cluster is None:
        return pd.DataFrame(), pd.DataFrame(), None

    cluster_entities_df = get_cluster_entities_df_cached(run_id, selected_cluster)
    cluster_entities = cluster_entities_df["entity_id"].tolist()

    cluster_pairs = review_df[
        review_df["entity_id_a"].isin(cluster_entities) &
        review_df["entity_id_b"].isin(cluster_entities)
    ]

    if cluster_pairs.empty:
        st.info("Keine Verbindungen im Cluster vorhanden")
        return pd.DataFrame(), cluster_entities_df, None

    # --- Compute metrics ---
    cluster_size = cluster_entities_df.shape[0]

    prefs = load_preferences()
    threshold = prefs.get("auto_merge_threshold", 0.95)

    cluster_metrics = compute_cluster_score(cluster_pairs, cluster_size)
    score = cluster_metrics["score"]

    # --- MAIN: Cluster quality ---
    st.markdown("#### 📊 Cluster Qualität")

    col1, col2, col3 = st.columns(3)

    col1.metric("Größe", cluster_size)
    col2.metric("Cluster-Score", f"{score:.3f}")
    col3.metric("Schwächste Verbindung", f"{cluster_metrics['min']:.2f}")

    st.caption("Cluster-Score = aggregierte Match-Wahrscheinlichkeit aller Verbindungen im Cluster")

    # --- DETAILS (collapsed) ---
    with st.expander("🔬 Details (Metriken)"):
        st.caption(
            f"Harmonic: {cluster_metrics['harmonic']:.3f} | "
            f"Mean: {cluster_metrics['mean']:.3f} | "
            f"Min: {cluster_metrics['min']:.3f} | "
            f"Coverage: {cluster_metrics['coverage']:.2f}"
        )

    # --- STATUS (main signal) ---
    color, message = classify_cluster(cluster_metrics)

    if color == "green":
        st.markdown("**✅ Sehr konsistentes Cluster**")
    elif color == "yellow":
        st.warning(f"⚠️ {message}")
    else:
        st.error(f"❌ {message}")

    return cluster_pairs, cluster_entities_df, score

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

    return f"{icon} Cluster #{cid} · {row['size']} Datensätze · Score {row['score']:.2f} · {names_str}"

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

def render_cluster_view(cluster_df, all_review_df):
    st.subheader("🔗 Cluster-Analyse")

    total_clusters, reviewed_clusters, progress = get_cluster_progress(all_review_df)

    st.caption("Anzeige ggf. gefiltert; Fortschritt basiert auf allen Clustern")
    st.metric("Fortschritt", f"{progress:.1%}")
    st.progress(progress)
    st.caption(f"{reviewed_clusters} von {total_clusters} Clustern geprüft")

    num_clusters = len(cluster_df)
    avg_cluster_size = cluster_df["size"].mean() if not cluster_df.empty else 0
    max_cluster_size = cluster_df["size"].max() if not cluster_df.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Dublettengruppen", num_clusters)
    col2.metric("Ø Clustergröße", f"{avg_cluster_size:.2f}")
    col3.metric("Größtes Cluster", max_cluster_size)
    

    st.caption(
        "Cluster sind systemseitig definiert und fassen mehrere zusammengehörige Datensätze zu einer Dublettengruppe zusammen. "
        "Die Anzeige basiert auf dem aktuellen Schwellenwert und zeigt nur relevante Verbindungen."
    )

    chart_data = (
        cluster_df["size"]
        .value_counts()
        .rename_axis("cluster_size")
        .reset_index(name="cluster_count")
        .sort_values("cluster_size")
    )

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(
            "cluster_size:O",
            sort="ascending",
            title="Clustergröße",
            axis=alt.Axis(labelAngle=0)
        ),
        y=alt.Y(
            "cluster_count:Q",
            title="Anzahl Cluster"
        )
    )

    chart = chart.configure(
        background="#111827"
        ).configure_axis(
            labelColor="#e5e7eb",
            titleColor="#e5e7eb",
            gridColor="#374151"
    )

    chart = chart.properties(height=220)

    st.altair_chart(chart, width='stretch')

    return progress

def get_cluster_progress(all_review_df):
    total_clusters = all_review_df["cluster_id"].nunique()
    reviewed_clusters = all_review_df[
        all_review_df["status"] == "reviewed"
    ]["cluster_id"].nunique()
    
    progress = reviewed_clusters / total_clusters if total_clusters > 0 else 0

    return total_clusters, reviewed_clusters, progress