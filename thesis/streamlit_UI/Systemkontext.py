import streamlit as st
from thesis.streamlit_UI.ui_components.auth import require_auth
from thesis.dirty_crm_data_generator import run_pipeline
from erlib.db import (
    engine,
    get_latest_run_id,
    initialize_database, 
    reset_matching_tables
    )
from thesis.streamlit_UI.content.system_context import SYSTEM_CONTEXT_TEXT, SYSTEM_IDEA_TEXT, NAVIGATION_TEXT
from thesis.streamlit_UI.ui_components.constants import STANDARD_SCHEMA
from thesis.streamlit_UI.ui_components.theme import apply_theme
import pandas as pd
from thesis.streamlit_UI.ui_components.upload_processing import process_uploaded_files, suggest_mapping
from thesis.streamlit_UI.ui_components.views import render_global_sidebar

def main():
    st.set_page_config(page_title="System Context & Scope", layout="wide")

    apply_theme()
    #require_auth()

    @st.cache_data
    def load_latest_run(_engine):
        return get_latest_run_id(_engine)

    st.title("🔎 Erklärbare Dublettenerkennung")

    st.subheader("Systemkontext & Evaluationsrahmen")

    render_global_sidebar()

    col1, col2 = st.columns([1, 2])
        
    with col1:
        st.markdown(
            """
            <div style="
                min-height: 29px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            ">
            """,
            unsafe_allow_html=True
        )
        if st.button("🚀 Demo starten"):
            st.session_state.df_harmonized = None
            
            with st.spinner("Pipeline läuft..."):
                st.session_state.run_id = run_pipeline(engine, reset=True)

            st.cache_data.clear()

            run_id = load_latest_run(engine)

            if run_id:
                st.success(f"Run abgeschlossen: {run_id[:8]}")

            st.rerun()
        st.caption("")
        st.caption("Daten generieren")

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        uploaded_files = st.file_uploader(
            " ",
            type=["csv"],
            accept_multiple_files=True
        )
        st.caption("Max. 200 MB pro Datei • CSV-Format")
        st.caption("Unterstützt mehrere CSV-Dateien aus unterschiedlichen Systemen")
        
        if uploaded_files:
            st.session_state.run_id = None

            # 👉 Vorschau: erste Datei
            preview_df = pd.read_csv(uploaded_files[0])

            st.subheader("🔍 Vorschau (erste Datei)")
            st.caption("Mapping basiert auf erster Datei – alle Dateien sollten ähnliche Struktur haben.")
            st.dataframe(preview_df.head(), width='stretch')

            st.subheader("🧩 Spalten-Mapping")

            mapping = {}

            for col in STANDARD_SCHEMA:
                options = ["-- nicht vorhanden --"] + list(preview_df.columns)
                default = suggest_mapping(col, preview_df.columns)

                mapping[col] = st.selectbox(
                    f"{col}",
                    options=options,
                    index=options.index(default) if default in options else 0,
                    key=f"map_{col}"
                )

            st.info("Das System erkennt und korrigiert typische Formatabweichungen automatisch.")

            # 👉 EIN Button
            if st.button("➡️ Daten harmonisieren"):

                rename_dict = {
                    v: k for k, v in mapping.items()
                    if v != "-- nicht vorhanden --"
                }

                if not rename_dict:
                    st.error("Bitte mindestens eine Spalte zuordnen.")
                    st.stop()

                st.session_state.rename_dict = rename_dict

                df_harmonized = process_uploaded_files(uploaded_files, rename_dict)

                # fehlende Spalten ergänzen
                for col in STANDARD_SCHEMA:
                    if col not in df_harmonized.columns:
                        df_harmonized[col] = None

                st.session_state.df_harmonized = df_harmonized

                st.success(f"{len(uploaded_files)} Dateien kombiniert")

            # 👉 Vorschau nach Mapping
            if "df_harmonized" in st.session_state:
                st.subheader("🔍 Harmonisiert")
                if st.session_state.df_harmonized is not None:
                    st.dataframe(st.session_state.df_harmonized.head(), width='stretch')

                if st.button("🚀 Pipeline starten"):
                    with st.spinner("Pipeline läuft..."):
                        st.session_state.run_id = run_pipeline(
                            engine,
                            input_df=st.session_state.df_harmonized,
                            reset=True
                        )

                    st.success(f"Run abgeschlossen: {st.session_state.run_id[:8]}")

                rename_dict = st.session_state.get("rename_dict", {})

                mapped_cols = list(rename_dict.values())
                TECH_COLS = ["entity_id", "source", "cluster_id", "is_duplicated"]

                all_columns = set()
                for f in uploaded_files:
                    f.seek(0)
                    all_columns.update(pd.read_csv(f, nrows=0).columns)

                options = ["-- nicht vorhanden --"] + sorted(all_columns)

                unused_cols = [
                    c for c in all_columns
                    if c not in rename_dict.keys()
                ]

                if unused_cols:
                    st.info(f"Ignorierte Spalten: {', '.join(unused_cols)}")
                
                missing = [col for col in STANDARD_SCHEMA if col not in rename_dict.values()]

                if missing:
                    st.warning(f"Fehlende Felder: {', '.join(missing)}")

        if uploaded_files:
            st.info(f"{len(uploaded_files)} Datenquellen integriert")
            st.rerun()

    if st.button("Existierende Daten löschen"):
        st.session_state.run_id = None
        reset_matching_tables(engine)
        initialize_database(engine)
        st.rerun()

    st.markdown("---")

    st.markdown(SYSTEM_CONTEXT_TEXT)

    st.markdown(SYSTEM_IDEA_TEXT)

    st.markdown(NAVIGATION_TEXT)

    st.caption(
        "Hinweis: Dieses System dient ausschließlich der konzeptionellen Evaluation."
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([3, 2, 3])

    with col2:
        if st.button("Overview →"):
            st.switch_page("pages/1_Overview.py")


# TODO:
# reset_matching_tables aktuell global.
# später optional machen (z.B. "Reset vorherige Runs" Checkbox)

# TODO (Generalisierung):
# Blocking-Strategie aktuell fest auf bestimmte Attribute (z. B. Vorname, PLZ) ausgelegt.
# Zukünftig konfigurierbar machen (z. B. über UI oder Config),
# um unterschiedliche Datenschemata und Anwendungsfälle flexibel zu unterstützen.