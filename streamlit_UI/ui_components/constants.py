#todo Systeme mappen, zb ns=NetSuite
RENAME_MAP = {
    # Salesforce
    "vorname_1": "Vorname (Salesforce)",
    "nachname_1": "Nachname (Salesforce)",
    "email_1": "E-Mail (Salesforce)",
    "telefon_1": "Telefon (Salesforce)",
    "strasse_1": "Straße (Salesforce)",
    "hausnr_1": "Hausnummer (Salesforce)",
    "plz_1": "PLZ (Salesforce)",
    "stadt_1": "Stadt (Salesforce)",
    "land_1": "Land (Salesforce)",

    # NetSuite
    "vorname_2": "Vorname (NetSuite)",
    "nachname_2": "Nachname (NetSuite)",
    "email_2": "E-Mail (NetSuite)",
    "telefon_2": "Telefon (NetSuite)",
    "strasse_2": "Straße (NetSuite)",
    "hausnr_2": "Hausnummer (NetSuite)",
    "plz_2": "PLZ (NetSuite)",
    "stadt_2": "Stadt (NetSuite)",
    "land_2": "Land (NetSuite)",

    # Modell
    "prob": "Dublett-Wahrscheinlichkeit",
    "match_score": "Match-Score",
    "match_category": "Systemeinschätzung",
    "prob_explanation": "Begründung der Einschätzung",
    "nuanced_explanation": "Erweiterte Erklärung",
    "top_features": "Einflussreichste Merkmale"
}

COMPARE_FIELDS = [
    "vorname", "nachname", "email", "telefon",
    "strasse", "hausnr", "plz", "stadt", "land"
]

DISPLAY_COLUMNS = [
    # Meta
    #"source_1", "source_2", 
    #"block_key",

    # Salesforce
    "vorname_1", "nachname_1", "email_1", "telefon_1",
    "strasse_1", "hausnr_1", "plz_1", "stadt_1", "land_1",

    # NetSuite
    "vorname_2", "nachname_2", "email_2", "telefon_2",
    "strasse_2", "hausnr_2", "plz_2", "stadt_2", "land_2",

    # Entscheidung
    "prob", "match_category" #, "prob_explanation"
]


SEARCH_FIELDS = [
    "vorname_1", "nachname_1", "email_1", "telefon_1",
    "vorname_2", "nachname_2", "email_2", "telefon_2",
    "source_1", "source_2", "cluster_id_1", "cluster_id_2"
]

UI_RENAME = {
    "vorname": "Vorname",
    "nachname": "Nachname",
    "email": "E-Mail",
    "telefon": "Telefon",
    "strasse": "Straße",
    "hausnr": "Hausnummer",
    "plz": "PLZ",
    "stadt": "Stadt",
    "land": "Land"
}