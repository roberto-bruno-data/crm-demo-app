MATCH_CATEGORIES = [
    "Sichere Dublette",
    "Wahrscheinliche Dublette",
    "Unklare Dublette"
]

MATCH_CATEGORY_ORDER = MATCH_CATEGORIES

MATCH_CATEGORY_COLORS = {
    "Sichere Dublette": "green",
    "Wahrscheinliche Dublette": "orange",
    "Unklare Dublette": "red",
}

MATCH_CATEGORY_META = {
    "Sichere Dublette": {"color": "green", "threshold": 0.9},
    "Wahrscheinliche Dublette": {"color": "orange", "threshold": 0.7},
    "Unklare Dublette": {"color": "red", "threshold": 0.5},
}

ATTRIBUTES = ["vorname", "nachname", "email", "telefon", "strasse", "hausnr", "plz", "stadt", "land"]