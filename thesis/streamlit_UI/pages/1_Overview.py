import streamlit as st
import altair as alt
from erlib.db import (
    engine,
    get_latest_run_id,
    get_review_queue,
    get_cluster_status)
from erlib.utils.constants import MATCH_CATEGORIES
from thesis.streamlit_UI.ui_components.auth import require_auth
from thesis.logic.metrics import compute_pair_metrics
from thesis.streamlit_UI.ui_components.theme import apply_theme
from thesis.streamlit_UI.ui_components.views import load_data, setup_cluster_data, render_global_sidebar, get_active_run_id, filter_pairs

apply_theme()
require_auth()

run_id = get_active_run_id()

effective_threshold, _ = render_global_sidebar()

st.title("📊 System Overview – Dublettenerkennung")

view_mode = st.radio(
    "Analysemodus",
    ["Cluster-basiert", "Pair-basiert"],
    horizontal=True
)

include_reviewed = st.checkbox(
    "Auch geprüfte Cluster einbeziehen",
    value=False,
    help="Zeigt zusätzlich Cluster an, die bereits manuell überprüft wurden."
)

def render_pair_view(data, effective_threshold):
    data["review_df"] = filter_pairs(data["review_df"], effective_threshold)
    metrics = compute_pair_metrics(data, effective_threshold)
    total_records = metrics["total_records"]
    total_candidates_all = metrics["total_candidates_all"]
    total_candidates_filtered = metrics["total_candidates_filtered"]
    dup_rate_sicher = metrics["dup_rate_sicher"]
    dup_rate_unsicher = metrics["dup_rate_unsicher"]
    counts_cat = metrics["counts_cat"]
    chart_data = metrics["chart_data"]

    unklare = counts_cat.get(MATCH_CATEGORIES[2], 0)

    st.caption(
        "Dublettenvorschläge umfassen alle Paare mit Modellwahrscheinlichkeit > 0. "
        "Sichere Dubletten entsprechen einer Wahrscheinlichkeit > 0.8."
    )

    st.subheader("📦 Datenbasis")
    st.caption("Salesforce & NetSuite (synthetischer Datensatz)")

    col1, col2, col3 = st.columns(3)

    col1.metric("Harmonisierte Records", total_records)
    col2.metric("Kandidatenpaare (gesamt)", total_candidates_all)
    col3.metric("Dublettenvorschläge (gefiltert)", total_candidates_filtered)

    st.caption(
        f"Aus {total_records} Records wurden {total_candidates_all} Kandidatenpaare generiert."
    )

    lower = effective_threshold * 100
    upper = 70

    if lower < upper:
        unclear_text = f"{lower:.0f}–{upper}%"
    else:
        unclear_text = f"keine (Schwellenwert {lower:.0f}% ≥ 70%)"

    st.caption(
        f"Schwellenwerte: Sicher ≥ 90% | "
        f"Wahrscheinlich 70–90% | "
        f"Unklar {unclear_text}. "
        f"Unklare Fälle sollten manuell geprüft werden."
    )

    cols = st.columns(len(MATCH_CATEGORIES))

    total = sum(counts_cat.values())

    for col, cat in zip(cols, MATCH_CATEGORIES):
        count = counts_cat.get(cat, 0)
        rate = count / total if total > 0 else 0
        col.metric(cat, count, f"{rate:.1%} Anteil")

    color_scale = alt.Scale(
        domain=MATCH_CATEGORIES,
        range=["#22c55e", "#eab308", "#ef4444"]  # grün, gelb, rot
    )

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(
            "Kategorie",
            sort=MATCH_CATEGORIES,
            axis=alt.Axis(labelAngle=0)
        ),
        y=alt.Y("Anzahl", title="Anzahl Paare"),
        color=alt.Color("Kategorie", scale=color_scale, legend=None)
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

    if unklare > 0:
        st.info(
            f"{unklare} (<= 50%) Fälle sind als *unklar* "
            "klassifiziert und sollten manuell geprüft werden."
        )
    
def render_cluster_view(cluster_df, all_review_df):
    st.subheader("🔗 Cluster-Analyse")

    total_clusters = all_review_df["cluster_id"].nunique()
    reviewed_clusters = all_review_df[
        all_review_df["status"] == "reviewed"
    ]["cluster_id"].nunique()
    
    progress = reviewed_clusters / total_clusters if total_clusters > 0 else 0

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

if view_mode == "Pair-basiert":
    data = load_data(run_id, engine)
    status_df = get_cluster_status(run_id, engine)

    review_df = get_review_queue(run_id, engine)

    review_df = review_df.merge(
        status_df[["cluster_id", "status"]],
        on="cluster_id",
        how="left"
    )

    review_df["status"] = review_df["status"].fillna("open")

    if not include_reviewed:
        review_df = review_df[review_df["status"] != "reviewed"]

    data["review_df"] = review_df

    data["review_df"] = filter_pairs(data["review_df"], effective_threshold)

    render_pair_view(data, effective_threshold)

elif view_mode == "Cluster-basiert":
    review_df, cluster_scores_df, cluster_with_names, cluster_df = setup_cluster_data(
        run_id, engine, effective_threshold
    )
    
    status_df = get_cluster_status(run_id, engine)

    # --- BASE: alle Daten (für Fortschritt) ---
    all_review_df = get_review_queue(run_id, engine)

    all_review_df = all_review_df.merge(
        status_df[["cluster_id", "status"]],
        on="cluster_id",
        how="left"
    )

    all_review_df["status"] = all_review_df["status"].fillna("open")

    if cluster_scores_df is not None and not cluster_scores_df.empty:
        # --- CLUSTER-LEVEL BASIS ---
        cluster_sizes = cluster_scores_df[["cluster_id", "size"]].copy()

        # --- STATUS AUF CLUSTER EBENE ---
        cluster_status = all_review_df[["cluster_id", "status"]].drop_duplicates()

        cluster_sizes = cluster_sizes.merge(
            cluster_status,
            on="cluster_id",
            how="left"
        )

        cluster_sizes["status"] = cluster_sizes["status"].fillna("open")

        # --- FILTER (Checkbox wirkt jetzt wirklich) ---
        if not include_reviewed:
            cluster_sizes = cluster_sizes[
                cluster_sizes["status"] != "reviewed"
            ]

        render_cluster_view(cluster_sizes, all_review_df)

    else:
        st.warning("Keine Cluster für den aktuellen Schwellenwert gefunden.")

col1, col2, col3 = st.columns([3, 2, 3])
with col2:
    if st.button("Zur Review Queue →"):
        st.switch_page("pages/2_Review_Queue.py")