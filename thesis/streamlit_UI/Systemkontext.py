import streamlit as st
from thesis.streamlit_UI.ui_components.auth import require_auth
from thesis.dirty_crm_data_generator import run_pipeline
from erlib.db import (
    engine,
    get_latest_run_id,
    initialize_database, 
    reset_matching_tables,
    initialize_database
    )
from thesis.streamlit_UI.content.system_context import SYSTEM_CONTEXT_TEXT, SYSTEM_IDEA_TEXT, NAVIGATION_TEXT
from thesis.streamlit_UI.ui_components.constants import STANDARD_SCHEMA
from thesis.streamlit_UI.ui_components.theme import apply_theme
import pandas as pd
from thesis.streamlit_UI.ui_components.upload_processing import process_uploaded_files, suggest_mapping
from thesis.streamlit_UI.ui_components.views import render_global_sidebar

def main():
    st.set_page_config(page_title="System Context & Scope", layout="wide")

    initialize_database(engine)
    apply_theme()
    require_auth()

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

            st.subheader("📊 Datenvorschau")

            # 👉 Dateien einmal einlesen (Performance)
            dfs = []
            for f in uploaded_files:
                try:
                    f.seek(0)
                    dfs.append(pd.read_csv(f))
                except:
                    st.warning(f"{f.name} konnte nicht geladen werden")

            n_rows = st.slider("Anzahl angezeigter Zeilen", 1, 20, 5)

            # 👉 Fall 1: Nur eine Datei
            if len(dfs) == 1:
                df = dfs[0]
                file = uploaded_files[0]

                st.markdown(f"**{file.name}**")
                st.dataframe(df.head(n_rows), width='stretch')

                st.caption("Einzelne Datenquelle – Mapping erfolgt auf Basis dieser Struktur.")

            # 👉 Fall 2: Mehrere Dateien → Vergleich
            else:
                st.subheader("🔍 Vergleich unterschiedlicher Quellschemata")

                st.info(
                    "Die Datenquellen weisen unterschiedliche Strukturen auf "
                    "(z. B. aggregierte vs. atomare Attribute). "
                    "Diese werden im nächsten Schritt harmonisiert."
                )

                # Tabs mit Dateinamen
                tabs = st.tabs([file.name for file in uploaded_files])

                for tab, df, file in zip(tabs, dfs, uploaded_files):
                    with tab:
                        st.dataframe(df.head(n_rows), width='stretch')

                        st.write("**Spaltenstruktur:**")
                        st.write(", ".join(df.columns))

                if len(dfs) > 1:
                    schema_diff = [set(df.columns) for df in dfs]

                    common = set.intersection(*schema_diff)
                    all_cols = set.union(*schema_diff)

                    st.markdown("**Gemeinsame Spalten:**")
                    st.write(", ".join(sorted(common)))

                    st.markdown("**Unterschiedliche Spalten:**")
                    st.write(", ".join(sorted(all_cols - common)))

            st.success(f"{len(uploaded_files)} Datenquelle(n) erkannt")
                        
        if uploaded_files:
            st.session_state.run_id = None

            # 👉 Vorschau: erste Datei
            if not dfs:
                st.error("Keine gültigen Daten geladen")
                st.stop()

            preview_df = dfs[0]
            st.markdown("---")
            st.subheader("🧩 Harmonisierung der Datenschemata")

            st.info(
                "Die unterschiedlichen Quellstrukturen werden nun in ein einheitliches Zielschema überführt."
            )

            st.subheader("🧩 Spalten-Mapping")

            st.caption(
                "Die Zuordnung erfolgt pro Datenquelle, da unterschiedliche Schemas vorliegen können."
            )

            mapping = {}

            for std_col in STANDARD_SCHEMA:
                st.markdown(f"### {std_col}")

                mapping[std_col] = {}

                for i, file in enumerate(uploaded_files):
                    df = dfs[i]

                    options = ["-- nicht vorhanden --"] + list(df.columns)

                    default = suggest_mapping(std_col, df.columns)

                    if default != "-- nicht vorhanden --":
                        index = options.index(default)
                    else:
                        index = 0

                    selected = st.selectbox(
                        f"Quelle {i+1} ({file.name})",
                        options=options,
                        index=index,
                        key=f"{std_col}_{i}"
                    )

                    mapping[std_col][i] = selected

            st.info("Das System erkennt und korrigiert typische Formatabweichungen automatisch.")

            # 👉 EIN Button
            if st.button("➡️ Daten harmonisieren"):

                mapping_per_file = {}

                for std_col, file_map in mapping.items():
                    for file_idx, selected_col in file_map.items():

                        if selected_col == "-- nicht vorhanden --":
                            continue

                        if file_idx not in mapping_per_file:
                            mapping_per_file[file_idx] = {}

                        mapping_per_file[file_idx][selected_col] = std_col

                if not mapping_per_file:
                    st.error("Bitte mindestens eine Spalte zuordnen.")
                    st.stop()

                st.session_state.mapping_per_file = mapping_per_file

                df_harmonized = process_uploaded_files(uploaded_files, mapping_per_file)

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

                TECH_COLS = ["entity_id", "source", "cluster_id", "is_duplicated"]

                all_columns = set()
                
                for df in dfs:
                    all_columns.update(df.columns)

                options = ["-- nicht vorhanden --"] + sorted(all_columns)

                mapping_per_file = st.session_state.get("mapping_per_file", {})

                used_cols = set()
                for file_map in mapping_per_file.values():
                    used_cols.update(file_map.keys())

                unused_cols = [c for c in all_columns if c not in used_cols]

                if unused_cols:
                    st.info(f"Ignorierte Spalten: {', '.join(unused_cols)}")
                
                # missing = [col for col in STANDARD_SCHEMA if col not in rename_dict.values()]

                # if missing:
                #     st.warning(f"Fehlende Felder: {', '.join(missing)}")

        if uploaded_files:
            st.info(f"{len(uploaded_files)} Datenquellen integriert")

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

if __name__ == "__main__":
    main()


# TODO:
# reset_matching_tables aktuell global.
# später optional machen (z.B. "Reset vorherige Runs" Checkbox)

# TODO (Generalisierung):
# Blocking-Strategie aktuell fest auf bestimmte Attribute (z. B. Vorname, PLZ) ausgelegt.
# Zukünftig konfigurierbar machen (z. B. über UI oder Config),
# um unterschiedliche Datenschemata und Anwendungsfälle flexibel zu unterstützen.