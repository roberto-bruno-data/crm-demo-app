import streamlit as st
import json
from thesis.streamlit_UI.ui_components.auth import require_auth
from erlib.db import engine, get_audit_logs, get_latest_run_id
from thesis.streamlit_UI.ui_components.theme import apply_theme
from thesis.streamlit_UI.ui_components.views import render_global_sidebar, get_active_run_id
import pandas as pd

st.set_page_config(page_title="Audit Export", layout="wide")

def format_entity_label(entity):
    data = entity.get("data", {})

    vorname = data.get("vorname")
    nachname = data.get("nachname")
    email = data.get("email")
    stadt = data.get("stadt")
    plz = data.get("plz")

    # 1. Name
    name = " ".join(filter(None, [vorname, nachname])).strip()

    # 2. Fallbacks
    if name:
        label = f"👤 {name}"
    elif email:
        label = f"📧 {email}"
    else:
        label = f"🆔 Entity {entity.get('entity_id')}"

    # 3. Add context (optional)
    location = " ".join(filter(None, [plz, stadt])).strip()
    if location:
        label += f" • {location}"

    return label

def safe_parse(x):
    if isinstance(x, dict):
        return x
    try:
        return json.loads(x)
    except Exception:
        return None

@st.cache_data
def get_audit_data(run_id, _engine):
    return get_audit_logs(run_id, _engine)

apply_theme()

require_auth()

render_global_sidebar()

st.title("Audit Trail: Golden Record Entscheidungen")

run_id = get_active_run_id()

if run_id is None:
    st.info("Kein Run gefunden. Bitte zuerst einen Run durchführen oder CSV hochladen.")
    st.stop()

st.caption(f"Run ID: {run_id[:8]}")

audit_df = get_audit_data(run_id, engine)

if audit_df is None or audit_df.empty:
    st.info("Noch keine Entscheidungen vorhanden.")

else:
    audit_df = audit_df.sort_values("created_at", ascending=False)
    for audit_row in audit_df.itertuples():
        entry = audit_row.audit

        entry = safe_parse(entry)

        if entry is None:
            continue

        timestamp = entry.get("timestamp", "kein Timestamp")

        with st.expander(
            f"Cluster {audit_row.cluster_id} – {timestamp}"
        ):
            col1, col2 = st.columns(2)
            col1.metric("Attribute im Golden Record", len(entry.get("golden_record", {})))
            col2.metric("Entities im Cluster", len(entry.get("cluster_entities", [])))

            metrics = entry.get("cluster_metrics", {})

            if metrics:
                st.markdown("### 🧠 Cluster-Evidenz")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Score", f"{metrics.get('score', 0):.2f}")
                c2.metric("Min Pair", f"{metrics.get('min', 0):.2f}")
                c3.metric("Ø", f"{metrics.get('mean', 0):.2f}")
                c4.metric("Coverage", f"{metrics.get('coverage', 0):.2f}")

            pair_evidence = entry.get("pair_evidence", {})

            if pair_evidence:
                st.markdown("### 🔗 Pair-Evidenz")

                strongest = pair_evidence.get("strongest", [])
                weakest = pair_evidence.get("weakest", [])

                if strongest:
                    with st.expander("Stärkste Verbindung"):
                        st.dataframe(pd.DataFrame(strongest), width="stretch")

                if weakest:
                    with st.expander("Schwächste Verbindung"):
                        st.dataframe(pd.DataFrame(weakest), width="stretch")

            entity_explanations = entry.get("entity_explanations", {})

            if entity_explanations:
                st.markdown("### 👤 Warum gehört diese Entity zum Cluster?")

                for eid, info in entity_explanations.items():
                    with st.expander(f"Entity {eid} – stärkste Verbindung"):
                        st.write(f"Verbunden mit: {info.get('connected_to')}")
                        st.write(f"Score: {info.get('prob', 0):.3f}")
                        st.write(info.get("explanation"))

                        if info.get("top_features"):
                            st.caption(f"Top Features: {info['top_features']}")

                        if info.get("feature_contributions"):
                            st.json(info["feature_contributions"])

            st.markdown("### Originaldaten (Cluster)")

            for entity in entry.get("cluster_entities", []):
                label = format_entity_label(entity)

                with st.expander(label):
                    st.json(entity.get("data", {}))

            if "model" in entry:
                st.markdown("### 🤖 Modell-Evidenz (Beispiel-Paar)")
                st.json(entry["model"])

            st.markdown("### 🧩 Golden Record (Ergebnis)")

            gr = entry.get("golden_record", {})

            if gr:
                st.dataframe(
                    pd.DataFrame(gr.items(), columns=["Attribut", "Wert"]),
                    hide_index=True,
                    width="stretch"
                )
            else:
                st.caption("Kein Golden Record vorhanden.")

            with st.expander("JSON Ansicht"):
                st.json(entry["golden_record"])

    parsed_audit = []
    for a in audit_df["audit"]:
        parsed = safe_parse(a)
        if parsed is not None:
            parsed_audit.append(parsed)

    st.download_button(
        "⬇️ Audit Trail herunterladen (JSON)",
        data=json.dumps(parsed_audit, indent=2, ensure_ascii=False).encode("utf-8-sig"),
        file_name=f"audit_log_{run_id[:8]}.json" if run_id is not None else "golden_record_audit_log.json",
        mime="application/json"
    ) 

