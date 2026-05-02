import streamlit as st
from thesis.streamlit_UI.ui_components.auth import require_auth
from erlib.db import engine, get_latest_run_id, get_golden_records
from thesis.streamlit_UI.ui_components.views import (
    setup_cluster_data,
    render_global_sidebar,
    render_review_queue,
    render_cluster_context,
    load_base_data,
    compute_cluster_scores,
    filter_pairs,
    filter_clusters,
    enrich_cluster_with_names,
    render_pair_selector,
    get_selected_pair,
    render_model_section,
    render_divider,
    get_cluster_status,
    get_all_review_data
)
from thesis.logic.golden_record_service import set_cluster_status 
from thesis.streamlit_UI.ui_components.theme import apply_theme
from thesis.logic.cluster_service import render_cluster_metrics_and_merge_section, get_cluster_progress
import pandas as pd
from thesis.streamlit_UI.ui_components.record_preparation import prepare_records, build_model_info
from thesis.logic.cluster_service import render_cluster_view

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

@st.cache_data(show_spinner=False)
def filter_pairs_cached(review_df, threshold):
    return filter_pairs(review_df, threshold)

def apply_threshold(review_df, cluster_scores_df, threshold):
    review_df_filtered = filter_pairs_cached(review_df, threshold)
    cluster_scores_filtered = filter_clusters(cluster_scores_df, threshold)
    return review_df_filtered, cluster_scores_filtered

@st.cache_data(show_spinner=False)
def load_full_data(run_id):
    review_df, cluster_df, entities_df = load_base_data(run_id, engine)
    cluster_scores_df = compute_cluster_scores(cluster_df, review_df, run_id, engine)
    return review_df, cluster_df, entities_df, cluster_scores_df

@st.cache_data(show_spinner=False)
def load_cluster_data(run_id, demo_mode):
    return setup_cluster_data(run_id, engine, demo_mode)

def main():
    all_review_data = get_all_review_data(get_latest_run_id(engine))
    _, _, progress = get_cluster_progress(all_review_data)
    reverse_progress = 1 - progress
    require_auth()
    apply_theme()

    st.title("Dublettenerkennung")
    st.caption("Review von Entity-Clustern")

    tab_open, tab_reviewed = st.tabs(["🟢 Offene Cluster ({:.1%})".format(reverse_progress), "✅ Geprüfte Cluster ({:.1%})".format(progress)])

    run_id = get_latest_run_id(engine)
    effective_threshold, auto_merge_threshold = render_global_sidebar()

    review_df, cluster_df, entities_df, cluster_scores_df = load_full_data(
        run_id
    )

    review_df, cluster_scores_df = apply_threshold(
        review_df,
        cluster_scores_df,
        effective_threshold
    )

    cluster_with_names = enrich_cluster_with_names(cluster_df, entities_df)

    if cluster_scores_df is None or cluster_scores_df.empty:
        st.info("Keine Cluster für die aktuelle Einstellung vorhanden.")
        st.stop()

    with tab_open:
        selected_cluster = render_cluster_context(
            cluster_scores_df,
            cluster_with_names,
            run_id
        )

        st.write("---")

        st.markdown(f"### 🔗 Cluster #{selected_cluster}")

        cluster_pairs, cluster_entities_df, score = render_cluster_metrics_and_merge_section(
            selected_cluster,
            run_id,
            engine,
            review_df,
            cluster_df,
            cluster_scores_df
        )

        st.markdown("### 🧾 Review & Entscheidung")
        render_review_queue(
            run_id=run_id,
            cluster_pairs=cluster_pairs,
            selected_cluster=selected_cluster,
            cluster_entities_df=cluster_entities_df,
            effective_threshold=effective_threshold,   # 👈 THIS is the correct variable,
            auto_merge_threshold=auto_merge_threshold,
            score = score,
            cluster_df=cluster_df
        )
    
    with tab_reviewed:
        selected_cluster = render_cluster_context(
            cluster_scores_df,
            cluster_with_names,
            run_id,
            show_reviewed=True
        )

        render_cluster_metrics_and_merge_section(
            selected_cluster,
            run_id,
            engine,
            review_df,
            cluster_df,
            cluster_scores_df
        )

        if not selected_cluster:
            st.info("Keine geprüften Cluster vorhanden.")
            st.stop()

        st.markdown("### 🔎 Pair auswählen")
        selected_pair_id = render_pair_selector(
            cluster_pairs,
            key_suffix=f"{selected_cluster}_{len(cluster_pairs)}"
        )

        if selected_pair_id is None:
            st.info("Keine Paare im Cluster vorhanden.")
            return

        selected_row = get_selected_pair(cluster_pairs, selected_pair_id)
        st.markdown("### 🤖 Modellbewertung")

        _, _, sf_snapshot, ns_snapshot, _ = prepare_records(selected_row)
        model_info = build_model_info(selected_row)

        render_model_section(model_info, selected_row)

        render_divider()

        if run_id:
            golden_records = get_golden_records(run_id, engine)
            golden_record = golden_records[golden_records["cluster_id"] == selected_cluster]
            if not golden_record.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    golden_record = golden_record.iloc[0]
                    st.markdown("### 🏆 Golden Record")
                    gr_df = pd.DataFrame(golden_record["golden_record"], index=["Golden Record"]).T
                    st.dataframe(gr_df)
                with col2:
                    st.markdown("### 🔄 Status ändern")
                    render_status_toggle(run_id, selected_cluster)
            else:
                st.info("Für diesen Cluster wurde noch kein Golden Record erstellt.")

def render_status_toggle(run_id, cluster_id):
    status_df = get_cluster_status(run_id, engine)

    match = status_df[status_df["cluster_id"] == cluster_id]

    is_done = not match.empty and match.iloc[0]["status"] == "reviewed"

    label = "↩️ Als offen markieren" if is_done else "✅ Als geprüft markieren"

    if st.button(
        label,
        key=f"status_btn_reviewed_tab__{cluster_id}",
        width='stretch'
    ):
        new_status = "open" if is_done else "reviewed"

        set_cluster_status(run_id, cluster_id, new_status, engine)

        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
    
# TODO: pairwise xAI anzeigen (SHAP Werte pro Attribut)
# TODO (Cluster-Progress):
# Fortschritt aktuell entfernt, da noch pair-basiert gedacht.
# Neu implementieren auf Cluster-Ebene:
# - total_clusters = Anzahl aller Cluster
# - resolved_clusters = Anzahl Cluster mit Golden Record
# - progress = resolved_clusters / total_clusters
# Optional:
# - Anzeige als Metric + Progress Bar
# - evtl. Ø Clustergröße ergänzen
# TODO: prepare_records splitten (Snapshots vs. Comparison Data)
# TODO (State-Handling):
# Session-State Keys aktuell manuell gebaut:
#   value__{cluster_id}__{attr}
#   user_lock__{cluster_id}__{attr}
#
# Später zentralisieren in Helper/Service, z. B.:
#   - get_attr_value(cluster_id, attr)
#   - is_attr_locked(cluster_id, attr)
#   - oder State-Wrapper-Klasse
#
# Ziel:
# - keine String-Duplikation
# - konsistenter Zugriff
# - weniger Bug-Risiko bei Refactoring
# TODO (Cluster-Status):
# total_clusters aktuell nur basierend auf offenen Clustern.
# Später erweitern um Status-Konzept:
# - total_clusters = alle Cluster im Run
# - resolved_clusters = Cluster mit Golden Record
# - open_clusters = Cluster ohne Golden Record
#
# Ziel:
# - Fortschritt auf Cluster-Ebene berechnen
# - UI: "x von y Clustern abgeschlossen"
# - optional: Status-Spalte (open/resolved) in DB/Service
# TODO (Auto-Merge Logik erweitern):
# Aktuell erfolgt die automatische Dublettenbereinigung auf Clusterebene
# basierend auf einer aggregierten Cluster-Confidence.
#
# TODO (Auto-Merge Erweiterung – Integration mit bestehendem Pair-Workflow):
#
# Aktuell erfolgt die Dublettenprüfung entweder:
# - manuell auf Paarebene (Pair Review UI)
# - oder geplant automatisiert auf Clusterebene
#
# Problem:
# Cluster können durch transitive Beziehungen auch schwache oder widersprüchliche
# Verbindungen enthalten (z. B. A-B hoch, A-C niedrig).
# Ein vollständiger Cluster-Auto-Merge ist in solchen Fällen nicht sinnvoll.
#
# Erweiterung:
# Ergänzung einer Pair-Auto-Merge-Logik basierend auf bestehendem Pair-Review:
# - Sehr hoch bewertete Paare (z. B. prob >= Threshold) können automatisch
#   wie im manuellen Pair-Review zusammengeführt werden.
# - Cluster-Auto-Merge erfolgt nur bei hoher globaler Konsistenz.
#
# Integration:
# - Nutzung der bestehenden Golden-Record-Logik (build_golden_record)
# - Automatisches Setzen von Locks / Entscheidungen im State/DB
#
# Ziel:
# Kombination aus:
# - manuellem Pair-Review (bestehendes UI)
# - automatischem Pair-Merge (für sichere Fälle)
# - Cluster-Auto-Merge (für konsistente Gruppen)

# TODO (Graph-Visualisierung von Clustern):
# Visualisierung von Entity-Clustern als Graphstruktur:
# - Knoten = Entities
# - Kanten = paarweise Verbindungen (candidate pairs)
# - Kantengewicht = Match-Wahrscheinlichkeit (prob)
#
# Ziel:
# - Transparente Darstellung der Cluster-Struktur
# - Sichtbarmachung von starken vs. schwachen Verbindungen
# - Unterstützung bei der Bewertung von Cluster-Konsistenz
#
# Erweiterung (optional / zukünftig):
# - Interaktive Visualisierung (z. B. mit pyvis oder ähnlichen Libraries)
# - Hover/Tooltip: Anzeige der Match-Wahrscheinlichkeit
# - Klick auf Kante:
#     → Anzeige der zugehörigen Pair-Details
#     → inkl. xAI-Erklärungen (SHAP, Feature Contributions)
#
# Nutzen:
# - Verbesserte Interpretierbarkeit der Dublettenerkennung
# - Bessere Nachvollziehbarkeit von Auto-Merge-Entscheidungen
# - Unterstützung für manuelle Review-Prozesse
#
# Hinweis:
# Aktuell nicht implementiert (Scope/Komplexität), aber konzeptionell vorbereitet.
# TODO (xAI – Feature Contributions UI):
# Aktuell werden modellbasierte Erklärungen rein textuell dargestellt
# (similarity_sentence, detailed_explanation).
#
# Erweiterung:
# - Nutzung der bereits berechneten SHAP-basierenden feature_contributions
#   aus der DB (pair_features.feature_contributions)
#
# Ziel:
# - Transparente, visuelle Darstellung der Feature-Einflüsse pro Pair
# - Ergänzung zur textuellen Erklärung um quantitative Evidenz
#
# Mögliche Umsetzung:
# - Parsing der feature_contributions (JSON / dict)
# - Anzeige als:
#     • sortierte Liste (Top positive / negative Features)
#     • einfache Bar-Chart (z. B. st.bar_chart)
#
# Optional:
# - Aggregation auf Attribut-Ebene (statt Feature-Level)
# - Hervorhebung:
#     • positive Treiber (Match)
#     • negative Treiber (Mismatch)
#
# Nutzen:
# - Erhöhte Nachvollziehbarkeit von Modellentscheidungen
# - Stärkere Argumentationsbasis im Fachbereich
# - Vorbereitung für Audit / Governance / Explainability-Anforderungen
#
# Hinweis:
# Bewusst zurückgestellt, da aktueller Scope Fokus auf:
# - Cluster-basierter Review
# - Golden Record Erstellung
# - textuelle xAI-Erklärungen