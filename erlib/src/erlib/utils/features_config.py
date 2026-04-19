TEXT_COLS = ["vorname", "nachname", "strasse", "stadt", "land", "email", "telefon"]
NUM_COLS = ["plz"]

TEXT_METRICS = [
    "lev",
    "jw",
    "cos",
    "soundex",
    "metaphone",
    "dmetaphone"
]

NUM_METRICS = ["eq"]


def get_feature_cols():
    feature_cols = []

    for col in TEXT_COLS:
        for metric in TEXT_METRICS:
            feature_cols.append(f"sim_{col}_{metric}")

    for col in NUM_COLS:
        for metric in NUM_METRICS:
            feature_cols.append(f"sim_{col}_{metric}")

    return feature_cols