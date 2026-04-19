import pandas as pd
from pathlib import Path
import yaml
import streamlit as st
from thesis.streamlit_UI.ui_components.constants import UI_RENAME
from erlib.db import engine, get_latest_run_id, get_harmonized_entities, get_review_queue, get_resolved_count, load_pairs_from_db, get_resolved_cluster_ids
from thesis.logic.cluster_service import get_cluster_entities_df, get_clusters, format_cluster_with_names
from thesis.logic.cluster_metrics import compute_cluster_score
from thesis.logic.helpers import render_divider, is_attr_locked
from thesis.streamlit_UI.ui_components.pair_selectors import render_cluster_attribute, render_pair_selector, get_selected_pair
from thesis.streamlit_UI.ui_components.record_preparation import prepare_records, build_model_info
from erlib.utils.constants import ATTRIBUTES
from thesis.logic.golden_record_service import build_golden_record
from thesis.streamlit_UI.ui_components.golden_record import render_golden_record_panel
from thesis.config.preferences import load_preferences, save_preferences

@st.cache_data
def load_data(run_id, _engine, include_resolved):
    review_df = get_review_queue(run_id, _engine)

    cluster_df = get_clusters(run_id, _engine)

    if not include_resolved:
        resolved_clusters = get_resolved_cluster_ids(run_id, _engine)
        cluster_df = cluster_df[
            ~cluster_df["cluster_id"].isin(resolved_clusters)
        ]

    valid_entity_ids = set(cluster_df["entity_id"])

    valid_cluster_ids = set(cluster_df["cluster_id"])

    review_df = review_df[
        review_df["cluster_id"].isin(valid_cluster_ids)
    ]

    return {
        "review_df": review_df,
        "resolved_count": get_resolved_count(run_id, _engine),
        "total_candidates": len(load_pairs_from_db(run_id, _engine))
    }

def load_config():
    config_path = Path(__file__).resolve().parents[1] / "ui_components" / "preferences.yaml"

    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_default_source(attr, settings):
    return settings.get(attr)

def render_model_section(model_info):
    st.markdown("---")
    st.subheader("Modellbasierte Einschätzung")

    c1, c2, c3 = st.columns([1,1,2])

    with c1:
        st.metric("Wahrscheinlichkeit", f"{model_info['prob']:.2f}")

    with c2:
        st.metric("Kategorie", model_info["match_category"])

    with c3:
        st.markdown("**Kurzbegründung**")
        st.write(model_info["similarity_sentence"])

    with st.expander("🔍 Modell-Details & Erklärungen"):
        st.write(model_info["detailed_explanation"])

def render_comparison_table(
    salesforce_df,
    netsuite_df,
    selected_pair_id,
    settings,
    show_identical,
    display_attrs
):
    def comparison_columns():
        return st.columns([0.25, 2, 3, 3, 1, 3, 1])
    
    def status_bar(col, locked, golden=False):
        if golden:
            color = "#fbbc04"   # gold
        else:
            color = "#34a853" if locked else "#ea4335"

        col.markdown(
            f"""
            <div style="
                height: 2.2rem;
                background-color: {color};
                border-radius: 4px;
            "></div>
            """,
            unsafe_allow_html=True
        )

    def render_attribute_row(attr, index, val_sf, val_ns, pair_id):
        col_bar, col_attr, col_sf, col_ns, col_status, col_decision, col_lock = comparison_columns()

        row_id = f"{pair_id}__{attr}"
        lock_key  = f"lock__{row_id}"
        value_key = f"value__{row_id}"

        identical = val_sf == val_ns

        # ---- INITIALISIERUNG (nur einmal!) ----
        
        if lock_key not in st.session_state:
            st.session_state[lock_key] = identical

        if value_key not in st.session_state:
            if identical:
                st.session_state[value_key] = val_sf
            else:
                preferred = get_default_source(attr, settings)

                if preferred == "salesforce":
                    st.session_state[value_key] = val_sf
                elif preferred == "netsuite":
                    st.session_state[value_key] = val_ns
                else:
                    st.session_state[value_key] = None

        locked = st.session_state[lock_key]

        # ---- CONTENT ----
        col_attr.write(f"{index}. {attr}")
        col_sf.write(val_sf)
        col_ns.write(val_ns)

        if identical:
            col_status.write("✅")
        else:
            col_status.write("🔒" if locked else "❌")

        # ---- DECISION ----
        if locked:
            col_decision.write(st.session_state[value_key] or "—")

        else:
            reverse_map = {v: k for k, v in UI_RENAME.items()}
            technical_attr = reverse_map.get(attr)
            preferred = get_default_source(technical_attr, settings)

            sf_label = f"Salesforce: {val_sf}"
            ns_label = f"NetSuite: {val_ns}"

            if preferred == "salesforce":
                sf_label = f"Salesforce ⭐: {val_sf}"
            elif preferred == "netsuite":
                ns_label = f"NetSuite ⭐: {val_ns}"

            options = [
                sf_label,
                ns_label,
                "Eigener Wert …"
            ]

            current_value = st.session_state.get(value_key)

            if current_value == val_sf:
                default_index = 0

            elif current_value == val_ns:
                default_index = 1

            elif preferred == "salesforce":
                default_index = 0

            elif preferred == "netsuite":
                default_index = 1

            elif current_value:
                default_index = 2

            else:
                default_index = 0

            choice = col_decision.selectbox(
                "Quelle",
                options,
                index=default_index,
                key=f"select__{row_id}",
                label_visibility="collapsed"
            )
        

            if choice == "Eigener Wert …":
                st.session_state[value_key] = col_decision.text_input(
                    "",
                    key=f"manual__{row_id}",
                    placeholder="Manuell eingeben"
                )
            else:
                st.session_state[value_key] = (
                    val_sf if choice.startswith("Salesforce") else val_ns
                )

        # ---- LOCK ----
        col_lock.checkbox(
            "Lock",
            key=lock_key,
            label_visibility="collapsed"
        )


    if "gr_state" not in st.session_state:
        st.session_state["gr_state"] = {}

    if selected_pair_id not in st.session_state["gr_state"]:
        st.session_state["gr_state"][selected_pair_id] = {}

    #render_comparison_header()
    st.divider()

    # 1) sichtbare Attribute bestimmen (für saubere Nummerierung)
    visible_attrs = []

    for attr in display_attrs:
        val_sf = str(salesforce_df.iloc[0][attr])
        val_ns = str(netsuite_df.iloc[0][attr])

        if not show_identical and val_sf == val_ns:
            continue

        visible_attrs.append(attr)

    for i, attr in enumerate(visible_attrs, start=1):
        val_sf = str(salesforce_df.iloc[0][attr])
        val_ns = str(netsuite_df.iloc[0][attr])

        render_attribute_row(
            attr=attr,
            index=i,
            val_sf=val_sf,
            val_ns=val_ns,
            pair_id=selected_pair_id
        )
    
    return visible_attrs

def load_base_data(run_id, engine, include_resolved):
    data = load_data(run_id, engine, include_resolved)

    review_df = data["review_df"]
    cluster_df = get_clusters(run_id, engine)
    entities_df = get_harmonized_entities(run_id, engine)

    return review_df, cluster_df, entities_df

def enrich_cluster_with_names(cluster_df, entities_df):
    df = cluster_df.merge(
        entities_df[["entity_id", "vorname", "nachname"]],
        on="entity_id",
        how="left"
    )

    df["full_name"] = (
        df["vorname"].fillna("") + " " +
        df["nachname"].fillna("")
    ).str.strip()

    return df

def compute_cluster_scores(cluster_df, review_df, run_id, engine):
    cluster_ids = cluster_df["cluster_id"].unique().tolist()

    scores = []

    for cid in cluster_ids:
        entity_ids = cluster_df.loc[
            cluster_df["cluster_id"] == cid, "entity_id"
        ].tolist()

        cluster_pairs = review_df[
            review_df["entity_id_a"].isin(entity_ids) &
            review_df["entity_id_b"].isin(entity_ids)
        ]

        metrics = compute_cluster_score(cluster_pairs, len(entity_ids))

        scores.append({
            "cluster_id": cid,
            "size": len(entity_ids),
            "score": metrics["score"]
        })

    return pd.DataFrame(scores)

def filter_clusters(cluster_scores_df, threshold):
    return cluster_scores_df[cluster_scores_df["score"] >= threshold]

def filter_pairs(review_df, threshold):
    return review_df[review_df["prob"] >= threshold]

def render_global_settings():
    if "include_resolved" not in st.session_state:
        st.session_state.include_resolved = False

    if "demo_mode" not in st.session_state:
        st.session_state.demo_mode = True

    st.subheader("⚙️ Einstellungen")

    st.checkbox(
        "Bereits verarbeitete Fälle anzeigen",
        key="include_resolved"
    )

    include_resolved = st.session_state.include_resolved

    st.checkbox(
        "Demo-Modus (inkl. schwache Verbindungen)",
        key="demo_mode"
    )

    demo_mode = st.session_state.demo_mode

    return include_resolved, demo_mode

def setup_cluster_data(run_id, engine, include_resolved, threshold):
    review_df, cluster_df, entities_df = load_base_data(run_id, engine, include_resolved)
    review_df = filter_pairs(review_df, threshold)

    if cluster_df.empty:
        return None, None, None, None

    valid_entity_ids = set(cluster_df["entity_id"])

    review_df = review_df[
        review_df["entity_id_a"].isin(valid_entity_ids) &
        review_df["entity_id_b"].isin(valid_entity_ids)
    ]

    cluster_scores_df = compute_cluster_scores(cluster_df, review_df, run_id, engine)

    # Keep only clusters that still have visible pairs
    visible_pairs = review_df.copy()

    # Mapping: entity_id → cluster_id
    entity_to_cluster = cluster_df.set_index("entity_id")["cluster_id"]

    # Cluster IDs für beide Seiten des Paares
    visible_pairs = visible_pairs.copy()
    visible_pairs["cluster_id_a"] = visible_pairs["entity_id_a"].map(entity_to_cluster)
    visible_pairs["cluster_id_b"] = visible_pairs["entity_id_b"].map(entity_to_cluster)

    # Nur Paare innerhalb desselben Clusters behalten
    cluster_pairs = visible_pairs[
        visible_pairs["cluster_id_a"] == visible_pairs["cluster_id_b"]
    ]

    # Alle Cluster, die mindestens ein Pair haben
    visible_cluster_ids = cluster_pairs["cluster_id_a"].dropna().unique()

    cluster_df = cluster_df[
        cluster_df["cluster_id"].isin(visible_cluster_ids)
    ]

    cluster_scores_df = cluster_scores_df[
        cluster_scores_df["cluster_id"].isin(visible_cluster_ids)
    ]

    cluster_scores_df = filter_clusters(cluster_scores_df, threshold)

    cluster_df = cluster_df[
        cluster_df["cluster_id"].isin(cluster_scores_df["cluster_id"])
    ]

    cluster_with_names = enrich_cluster_with_names(cluster_df, entities_df)

    valid_entity_ids = set(cluster_df["entity_id"])

    review_df = review_df[
        review_df["entity_id_a"].isin(valid_entity_ids) &
        review_df["entity_id_b"].isin(valid_entity_ids)
    ]

    return review_df, cluster_scores_df, cluster_with_names, cluster_df

def render_global_sidebar():
    with st.sidebar:

        run_id = st.session_state.get("run_id")

        if not run_id:
            run_id = get_latest_run_id(engine)

        if run_id:
            st.markdown(f"**Run ID:** `{run_id[:8]}`")
        else:
            st.caption("Kein Run aktiv")
 
        st.subheader("⚙️ Einstellungen")

        if "include_resolved" not in st.session_state:
            prefs = load_preferences()
            st.session_state.include_resolved = prefs.get("include_resolved", False)

        if "demo_mode" not in st.session_state:
            prefs = load_preferences()
            st.session_state.demo_mode = prefs.get("demo_mode", True)

        if "last_saved_demo_mode" not in st.session_state:
            st.session_state.last_saved_demo_mode = None

        if st.session_state.demo_mode != st.session_state.last_saved_demo_mode:
            save_preferences({
                **load_preferences(),
                "demo_mode": st.session_state.demo_mode
            })
            st.session_state.last_saved_demo_mode = st.session_state.demo_mode

        include_resolved = st.checkbox(
            "Bereits verarbeitete Fälle anzeigen",
            key="include_resolved"
        )

        demo_mode = st.checkbox(
            "Demo-Modus (inkl. schwache Verbindungen)",
            key="demo_mode"
        )

        if "last_saved_demo_mode" not in st.session_state:
            st.session_state.last_saved_demo_mode = st.session_state.demo_mode

        if st.session_state.demo_mode != st.session_state.last_saved_demo_mode:
            save_preferences({
                **load_preferences(),
                "demo_mode": st.session_state.demo_mode
            })
            st.session_state.last_saved_demo_mode = st.session_state.demo_mode

        # ALWAYS first
        if "threshold_matches" not in st.session_state:
            st.session_state.threshold_matches = 0.8

        st.divider()

        # --- Preferences einmal laden ---
        if "auto_merge_threshold" not in st.session_state:
            prefs = load_preferences()
            st.session_state.auto_merge_threshold = prefs.get("auto_merge_threshold", 0.95)

        # --- Slider MIT key ---
        st.slider(
            "Auto-Merge Schwellenwert",
            min_value=0.5,
            max_value=1.0,
            step=0.01,
            key="auto_merge_threshold" 
        )

        # --- Persistieren (nachdem Streamlit den State gesetzt hat) ---
        if "last_saved_auto_merge_threshold" not in st.session_state:
            st.session_state.last_saved_auto_merge_threshold = None

        auto_merge_threshold = st.session_state.auto_merge_threshold

        if auto_merge_threshold != st.session_state.last_saved_auto_merge_threshold:
            save_preferences({
                **load_preferences(),
                "auto_merge_threshold": auto_merge_threshold
            })
            st.session_state.last_saved_auto_merge_threshold = auto_merge_threshold

        # --- UX Feedback ---
        if auto_merge_threshold > 0.9:
            st.info("Konservativ: Nur sehr sichere Cluster werden automatisch zusammengeführt")
        elif auto_merge_threshold > 0.75:
            st.info("Ausgewogen: Guter Kompromiss zwischen Präzision und Automatisierung")
        else:
            st.warning("Aggressiv: Auch unsichere Cluster werden gemerged")

        # --- slider UI ---
        if "threshold_matches_ui" not in st.session_state:
            st.session_state.threshold_matches_ui = 0.8

        if "threshold_matches_applied" not in st.session_state:
            st.session_state.threshold_matches_applied = 0.8

        with st.expander("Erweiterte Einstellungen"):
            st.slider(
                "Match-Schwellenwert",
                min_value=0.5,
                max_value=1.0,
                step=0.05,
                key="threshold_matches_ui",
                disabled=demo_mode
            )

            if demo_mode:
                st.info("Demo-Modus aktiv: Schwellenwert ist temporär auf 0.3 gesetzt (Slider bleibt gespeichert)")
            
            if st.button("Übernehmen"):
                st.session_state.threshold_matches_applied = st.session_state.threshold_matches_ui

        # ✅ NOW compute effective value
        effective_threshold = 0.3 if demo_mode else st.session_state.threshold_matches_applied

        # ✅ NOW display it
        if demo_mode:
            st.caption("Demo-Modus: Zeigt auch schwache Verbindungen (≥ 0.3)")
        else:
            st.caption(f"Aktiver Match-Schwellenwert: ≥ {effective_threshold:.2f}")

        return include_resolved, effective_threshold

def render_cluster_context(cluster_scores_df, cluster_with_names):

    st.markdown("### 🔍 Cluster auswählen")

    cluster_scores_df = cluster_scores_df.sort_values(
        by=["size", "score"],
        ascending=[False, False]
    )

    cluster_options = cluster_scores_df["cluster_id"].tolist()

    selected_cluster = st.selectbox(
        label="Cluster",
        options=cluster_options,
        format_func=lambda cid: format_cluster_with_names(
            cid, cluster_scores_df, cluster_with_names
        )
    )

    return selected_cluster

def render_review_queue(include_resolved, run_id, cluster_pairs,
    selected_cluster, cluster_entities_df, threshold):

    render_divider()

    st.markdown("### 🔗 Cluster Überblick")
    st.caption(f"{len(cluster_entities_df)} Datensätze im Cluster")

    top_prob = cluster_pairs["prob"].max()
    avg_prob = cluster_pairs["prob"].mean()

    col1, col2 = st.columns(2)
    col1.metric("Max. Match-Wahrscheinlichkeit", f"{top_prob:.2f}")
    col2.metric("Ø Wahrscheinlichkeit", f"{avg_prob:.2f}")

    # ===== DATAFRAME PREP =====
    df = (
        cluster_pairs[["entity_id_a", "entity_id_b", "prob"]]
        .sort_values("prob", ascending=False)
        .copy()
    )

    # Spalten umbenennen
    df.columns = ["Entity A", "Entity B", "Match Score"]

    # Ranking hinzufügen
    df.insert(0, "Rank", range(1, len(df) + 1))

    # Werte runden (kein String!)
    df["Match Score"] = df["Match Score"].round(3)

    # ===== STYLING =====
    def highlight_prob(val):
        if val > 0.8:
            return "color: #22c55e"
        elif val > 0.5:
            return "color: #eab308"
        else:
            return "color: #ef4444"

    styled_df = (
        df.style.map(highlight_prob, subset=["Match Score"])
        .format({"Match Score": "{:.3f}"})
    )

    # ===== DISPLAY =====
    with st.expander("Verbindungen im Cluster anzeigen"):
        st.dataframe(styled_df, height=260, width='stretch')

    st.markdown("### 🔎 Pair auswählen")
    selected_pair_id = render_pair_selector(cluster_pairs)

    if selected_pair_id is None:
        st.info("Keine Paare im Cluster vorhanden.")
        return

    selected_row = get_selected_pair(cluster_pairs, selected_pair_id)
    st.markdown("### 🤖 Modellbewertung")

    _, _, sf_snapshot, ns_snapshot, _ = prepare_records(selected_row)
    model_info = build_model_info(selected_row)

    render_model_section(model_info)

    render_divider()

    st.markdown("### 🧩 Attribute auswählen")

    show_identical = st.checkbox(
        "Identische Attribute anzeigen",
        value=True
    )

    with st.expander("Hinweise"):
        st.caption("⭐ = häufigster Wert im Cluster (Empfehlung)")
        st.caption("Wählen Sie für jedes Attribut den besten Wert für den Golden Record.")

        if include_resolved:
            st.caption("Zeigt alle Paare (inkl. bereits entschiedene)")
        else:
            st.caption("Zeigt nur offene Fälle")

    all_attrs = set(ATTRIBUTES)
       
    all_locked = all(
        is_attr_locked(selected_cluster, a, cluster_entities_df)
        for a in all_attrs
    )

    if all_locked:
        st.success("✅ Golden Record vollständig")
    else:
        st.caption("Noch offene Attribute")

    render_cluster_attribute(selected_cluster, cluster_entities_df, all_locked, show_identical)

    locked_count = sum(
        st.session_state.get(f"user_lock__{selected_cluster}__{a}", False)
        for a in all_attrs
    )

    progress = locked_count / len(all_attrs) if all_attrs else 0

    st.progress(progress)
    st.caption(f"{locked_count} / {len(all_attrs)} Attribute bestätigt")

    # 3) Golden Record NACH dem Rendern berechnen (state ist dann aktuell)
    st.subheader(f"Cluster ({len(cluster_pairs)} Paare)")
    values = {
        attr: st.session_state.get(f"value__{selected_cluster}__{attr}")
        for attr in all_attrs
    }

    locks = {
        attr: st.session_state.get(f"user_lock__{selected_cluster}__{attr}", False)
        for attr in all_attrs
    }

    golden_record = build_golden_record(values, locks)

    st.markdown("---")

    context_id = selected_cluster

    render_golden_record_panel(golden_record, context_id, run_id,
                               model_info, sf_snapshot, ns_snapshot, engine, cluster_entities_df, threshold, cluster_pairs)
    
def get_active_run_id():
    return st.session_state.get("run_id") or get_latest_run_id(engine)
