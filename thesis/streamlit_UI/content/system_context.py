SYSTEM_CONTEXT_TEXT = """
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

"""

SYSTEM_IDEA_TEXT = """
### Systemidee
1. Dubletten erkennen  
2. Dubletten erklären  
3. Entscheiden
"""

NAVIGATION_TEXT = """
### Navigation
- Overview → Dashboard mit Dublettenstatus
- Review Queue → Entscheidungsunterstützung
- Golden Records → Getätigte Konsolidierungen
- Audit Exports → Audit-Trail der Entscheidungen
"""