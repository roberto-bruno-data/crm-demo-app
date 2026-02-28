import streamlit as st
import json
from auth import require_auth
require_auth()
st.title("Audit Trail: Golden Record Entscheidungen")

# ✅ immer initialisieren
if "audit_log" not in st.session_state:
    st.session_state["audit_log"] = []

if not st.session_state["audit_log"]:
    st.info("Noch keine Entscheidungen vorhanden.")
else:
    for entry in st.session_state["audit_log"]:
        with st.expander(
            f"Pair {entry['pair_id']} – {entry['timestamp']}"
        ):
            st.markdown("### Originaldaten")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Salesforce**")
                st.json(entry["source_records"]["salesforce"])
            with c2:
                st.markdown("**NetSuite**")
                st.json(entry["source_records"]["netsuite"])

            st.markdown("### Modell-Evidenz")
            st.json(entry["model"])

            st.markdown("### Golden Record")
            st.json(entry["golden_record"])

    st.download_button(
        "⬇️ Audit Trail herunterladen (JSON)",
        data=json.dumps(
            st.session_state["audit_log"],
            indent=2,
            ensure_ascii=False
        ),
        file_name="golden_record_audit_log.json",
        mime="application/json"
    )
