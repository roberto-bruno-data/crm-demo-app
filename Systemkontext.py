import streamlit as st
import pandas as pd

DATA_PATH = "CSVs/crm_results_for_tableau_final.csv"

@st.cache_data
def load_data(path):
    return pd.read_csv(path)

import streamlit as st
import hmac

def require_password():
    if st.session_state.get("authenticated", False):
        return True

    st.set_page_config(page_title="Login")

    st.title("🔒 Geschützter Zugang")

    pw = st.text_input("Passwort", type="password")

    if st.button("Anmelden"):
        if hmac.compare_digest(pw, st.secrets["APP_PASSWORD"]):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Falsches Passwort")

    st.stop()

require_password()

original_df = load_data(DATA_PATH)

ns_records = len(load_data("CSVs/dirty_netsuite.csv"))
sf_records = len(load_data("CSVs/dirty_salesforce.csv"))

total_records = ns_records + sf_records

total_pairs = len(load_data("CSVs/pairs_blocked.csv"))
total_suspected = len(load_data("CSVs/crm_results_for_tableau_final.csv"))

CATEGORIES = [
    "Sichere Dublette",
    "Wahrscheinliche Dublette",
    "Unklare Dublette",
]

category_counts = {
    cat: int((original_df["match_category"] == cat).sum())
    for cat in CATEGORIES
}

st.set_page_config(page_title="System Context & Scope")

st.title("Erklärbare Dublettenerkennung: Systemkontext")

st.markdown("""
### Anleitung & Evaluationshinweise (v0.1)

Dieses System ist ein **funktionaler Prototyp** zur demonstrativen Bewertung erklärbarer Dublettenerkennung
im Multi-System-Kontext (z. B. CRM ↔ ERP).

Der Fokus liegt **nicht** auf maximaler Automatisierung oder Modelloptimierung,
sondern auf **Nachvollziehbarkeit, Entscheidungsunterstützung und Governance-Fähigkeit**.
            
Die Daten sind synthetisch erstellt worden.

Die Evaluation richtet sich primär an fachliche Anwender:innen,
Data-Verantwortliche und Personen mit Governance- oder Qualitätsverantwortung.

---

### Was dieses System zeigt

- wie systemübergreifende Dublettenvorschläge erzeugt werden,
- wie modellbasierte Einschätzungen verständlich erklärt werden,
- wie menschliche Entscheidungen explizit in den Prozess eingebunden sind,
- wie konsolidierte Golden Records **manuell und kontrolliert** entstehen können,
- wie jede Entscheidung revisionsfähig dokumentiert wird (Audit Trail).

---

### Was dieses System bewusst *nicht* tut

- ❌ keine automatische Dublettenauflösung  
- ❌ keine automatische Golden-Record-Erzeugung  
- ❌ keine Rückschreibung in Produktivsysteme  
- ❌ keine Bewertung der Modellgüte (Precision, Recall etc.)
- ❌ kein automatisierter Reimport bestätigter Golden Records    

Diese Aspekte sind **bewusst ausgeklammert**, um den Fokus auf
Transparenz, Verständlichkeit und Entscheidungslogik zu legen. 
Der Export dient ausschließlich der Veranschaulichung möglicher Anschlussfähigkeit
und ist nicht Teil des Entscheidungsprozesses.

---

### Hinweise für die Evaluation

Bei der Durchsicht des Systems ist insbesondere relevant:

- Sind die **Modellentscheidungen und Erklärungen nachvollziehbar**?
- Ist klar erkennbar, **warum** ein Paar als Dublette vorgeschlagen wird?
- Unterstützt die Oberfläche eine **fundierte manuelle Entscheidung**?
- Ist der Prozess aus fachlicher und organisatorischer Sicht **governance-tauglich**?
- Wären die bereitgestellten Informationen **ausreichend**, um eine Entscheidung zu treffen?
- Unterstützt die Nutzerführung eine **sichere, informierte Entscheidung** ohne impliziten Zwang zur Automatisierung?

Nicht relevant für die formale Bewertung sind:
- Performance-Optimierung
- Grad der Automatisierung
- visuelle Ausgestaltung im Sinne eines produktionsreifen UI-Designs

Hinweise zur Nutzerführung, Verständlichkeit oder Interaktionslogik (UX)
sind hingegen ausdrücklich willkommen und fließen als qualitative Rückmeldung ein.

---

### Ziel dieser Version

Ziel von Version **v0.1** ist es,
eine **Diskussions- und Evaluationsgrundlage** zu schaffen.

Feedback, fachliche Einschätzungen, Verbesserungsvorschläge oder Featurewünsche
sind ausdrücklich erwünscht und bilden die Grundlage für mögliche Folgeschritte.

""")

st.markdown("""
### Systemidee
1. Dubletten erkennen  
2. Dubletten erklären  
3. Entscheiden
""")

st.markdown("""
### Navigation
- Overview → Dashboard mit Dublettenstatus
- Review Queue → Entscheidungsunterstützung
- Golden Records → Getätigte Konsolidierungen
- Audit Exports → Audit-Trail der Entscheidungen
""")

st.caption(
    "Hinweis: Dieses System dient ausschließlich der konzeptionellen Evaluation."
)

st.markdown("---")

col1, col2, col3 = st.columns([3, 2, 3])

with col2:
    if st.button("Overview →"):
        st.switch_page("pages/1_Overview.py")
