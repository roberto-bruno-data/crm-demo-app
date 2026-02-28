import streamlit as st
from Systemkontext import ns_records, sf_records, total_records, total_pairs, total_suspected, category_counts
from auth import require_auth

require_auth()

st.title("System Overview")

st.subheader("Datenbasis")
st.caption("Salesforce & NetSuite (synthetischer Datensatz)")

col1, col2, col3 = st.columns(3)

col1.metric("Harmonisierte Records (gesamt)", total_records)

col1.caption(
    f"{ns_records} aus NetSuite + {sf_records} aus Salesforce"
)

col2.metric("Kandidatenpaare", 1020) #todo with real pairs
col3.metric("Dublettenvorschläge", total_suspected)

st.subheader("Verteilung der Dublettenkategorien")

st.caption(
    "Die Kategorisierung basiert auf modellbasierten Wahrscheinlichkeiten "
    "und definierten Schwellenwerten. Unklare Fälle erfordern manuelle Prüfung."
)

col1, col2, col3 = st.columns(3)

col1.metric("Sichere Dubletten", category_counts["Sichere Dublette"])
col2.metric("Wahrscheinliche Dubletten", category_counts["Wahrscheinliche Dublette"])
col3.metric("Unklare Dubletten", category_counts["Unklare Dublette"])

st.bar_chart(category_counts)

if category_counts["Unklare Dublette"] > 0:
    st.info(
        f"{category_counts['Unklare Dublette']} Fälle sind als *unklar* "
        "klassifiziert und sollten manuell geprüft werden."
    )
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("Zur Review Queue →"):
            st.switch_page("pages/2_Review_Queue.py")

# TODO: Data basis: Salesforce + NetSuite (synthetic)
# Records: 12 483 | Pairs evaluated: 31 902
