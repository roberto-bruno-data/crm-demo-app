import streamlit as st
import pandas as pd
import json
from datetime import datetime

import streamlit_UI.ui_components.constants as constants
from streamlit_UI.ui_components.filters import filter_identical_pairs, filter_side_bar
from streamlit_UI.ui_components.pair_selectors import build_pair_label
from streamlit_UI.ui_components.views import extract_system_record, get_default_source, load_config
from streamlit_UI.ui_components.data_access import load_pairs

from auth import require_auth

require_auth()

def render_review_queue():

    def save_state(state):
        with open("gr_state.json", "w") as f:
            json.dump(state, f)

    st.title("Dublettenerkennung: Review")
    
    st.set_page_config(
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    df = load_pairs("CSVs/crm_results_for_tableau_final.csv")

    st.caption(f"{len(df)} Paare geladen")

    filtered_df = filter_side_bar(df.copy(), st)

    if filtered_df.empty:
        st.info("Keine Paare nach aktueller Filterung.")
        st.stop()

    filtered_df["pair_id"] = filtered_df.index
    filtered_df[["pair_id"] + constants.DISPLAY_COLUMNS].copy()

    filtered_df, identical_df = filter_identical_pairs(
        filtered_df, constants.COMPARE_FIELDS
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
        mask = False
        for col in constants.SEARCH_FIELDS:
            if col in filtered_df.columns:
                mask = mask | filtered_df[col].astype(str).str.contains(
                    search_term, case=False, na=False
                )

        filtered_df = filtered_df[mask]

    filtered_df["pair_label"] = filtered_df.apply(build_pair_label, axis=1)

    selected_pair_id = st.selectbox(
        "Dublettenpaar auswählen",
        options=filtered_df["pair_id"],
        format_func=lambda x: filtered_df.loc[
            filtered_df["pair_id"] == x, "pair_label"
        ].iloc[0]
    )

    selected_row = filtered_df.loc[
        filtered_df["pair_id"] == selected_pair_id
    ].iloc[0]

    sf = extract_system_record(selected_row, "_1", constants.RENAME_MAP)
    ns = extract_system_record(selected_row, "_2", constants.RENAME_MAP)

    sf_snapshot = sf.to_dict(orient="records")[0]
    ns_snapshot = ns.to_dict(orient="records")[0]

    DISPLAY_ATTRS = list(constants.UI_RENAME.values())

    salesforce_df = sf.rename(columns=constants.UI_RENAME)
    netsuite_df   = ns.rename(columns=constants.UI_RENAME)

    salesforce_df = salesforce_df[DISPLAY_ATTRS]
    netsuite_df   = netsuite_df[DISPLAY_ATTRS]

    comparison_df = pd.DataFrame({
        "Attribut": salesforce_df.columns.astype(str),
        "Salesforce": salesforce_df.iloc[0].astype(str).values,
        "NetSuite": netsuite_df.iloc[0].astype(str).values
    })


    # st.subheader("Systemvergleich")
    # st.dataframe(comparison_df, width="stretch")

    model_info = selected_row[[
        "prob",
        "match_category",
        #"prob_explanation",
        "top_features",
        "similarity_sentence",
        #"nuanced_explanation",
        "detailed_explanation"
    ]]

    st.markdown("---")
    st.subheader("Modellbasierte Einschätzung")

    config = load_config()
    settings = config.get("attribute_priority", {})

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

        # st.markdown("**Erweiterte Erklärung**")
        # st.write(model_info["nuanced_explanation"])

    st.markdown("---")
    st.subheader("Systemvergleich & Golden Record")

    show_identical = st.checkbox(
        "Auch identische Attribute anzeigen",
        value=True
    )
    st.caption("⭐ = präferierte Quelle")


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

        # ---- STATUS BAR ----
        status_bar(col_bar, locked=locked, golden=all_locked)

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
            reverse_map = {v: k for k, v in constants.UI_RENAME.items()}
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

    for attr in DISPLAY_ATTRS:
        val_sf = str(salesforce_df.iloc[0][attr])
        val_ns = str(netsuite_df.iloc[0][attr])

        if not show_identical and val_sf == val_ns:
            continue

        visible_attrs.append(attr)

    all_locked = all(
        st.session_state.get(f"lock__{selected_pair_id}__{a}", False)
        for a in visible_attrs
    )

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
    
    all_locked = all(
        st.session_state.get(f"lock__{selected_pair_id}__{a}", False)
        for a in visible_attrs
    )

    if all_locked:
        st.success("✨ Golden Record vollständig bestätigt")
    else:
        st.info("🔍 Noch offene Attribute")

    # 3) Golden Record NACH dem Rendern berechnen (state ist dann aktuell)
    golden_record = {
        attr: st.session_state.get(f"value__{selected_pair_id}__{attr}")
        for attr in visible_attrs
        if st.session_state.get(f"lock__{selected_pair_id}__{attr}", False)
    }

    st.markdown("---")

    gr_df = pd.DataFrame(golden_record, index=["Golden Record"]).T

    gr_col, action_col = st.columns([4, 1])

    with gr_col:
        st.markdown("### 🏆 Finaler Golden Record (bestätigte Attribute)")
        st.dataframe(
            gr_df.style.set_properties(
                subset=None,
                **{
                    "font-weight": "600",
                    "background-color": "#c99700",
                    "color": "#111111"
                }
            ),
            width="stretch"
        )

    with action_col:
        st.markdown("### ")
        st.markdown("### ")

        all_locked = len(golden_record) > 0

        if st.button(
            "➕\nZu Golden Records\nhinzufügen",
            key=f"add_gr__{selected_pair_id}",
            disabled=not all_locked,
            use_container_width=True
        ):
            if "final_grs" not in st.session_state:
                st.session_state["final_grs"] = []

            st.session_state["final_grs"].append({
                "pair_id": selected_pair_id,
                **golden_record
            })

            audit_entry = {
                # Identity
                "pair_id": selected_pair_id,
                "timestamp": datetime.utcnow().isoformat(),

                # Original data snapshot (THIS is the important part)
                "source_records": {
                    "salesforce": sf_snapshot,
                    "netsuite": ns_snapshot
                },

                # Model evidence
                "model": {
                    "probability": float(model_info["prob"]),
                    "category": model_info["match_category"],
                    "explanation": model_info["similarity_sentence"],
                    "top_features": model_info["top_features"],
                    "detailed_explanation": model_info["detailed_explanation"]
                },

                # Human decision
                "golden_record": golden_record
            }

            if "audit_log" not in st.session_state:
                st.session_state["audit_log"] = []

            st.session_state["audit_log"].append(audit_entry)

            st.success("✅ Hinzugefügt")

render_review_queue()

# “goldensync.io produces evidence, not outcomes.”
