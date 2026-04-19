from rapidfuzz.distance import Levenshtein, JaroWinkler
import jellyfish
from metaphone import doublemetaphone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import pandas as pd

# Featureengineering und Preprocessing
#_________________________________________________________________________

def lev_similarity(a, b):
    """
    Normalisierte Levenshtein-Ähnlichkeit: 
    Gibt eine Ähnlichkeit von 0 (komplett verschieden) bis 1 (identisch) zurück.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 1.0 - Levenshtein.distance(a, b) / max(len(a), len(b))

def jaro_winkler_similarity(a, b):
    """
    Jaro-Winkler-Ähnlichkeit: Betont Übereinstimmungen am Anfang eines Strings.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return JaroWinkler.similarity(a, b)

# def cosine_sim(a, b, vectorizer):
#     """
#     Cosine-Similarity auf n-Gramm-Basis mit TF-IDF-Vektoren.
#     Robuster gegen kleinere Verschiebungen oder Schreibvarianten.
#     """
#     if not a and not b:
#         return 1.0
#     if not a or not b:
#         return 0.0

#     vecs = vectorizer.transform([a, b])
#     v1 = vecs[0]
#     v2 = vecs[1]

#     return cosine_similarity(v1, v2)[0, 0]

def soundex_similarity(a, b):
    """Phonetischer Vergleich: Gibt 1 zurück, wenn Soundex-Codes übereinstimmen, sonst 0."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 1.0 if jellyfish.soundex(a) == jellyfish.soundex(b) else 0.0

def metaphone_similarity(a, b):
    """Phonetische Ähnlichkeit basierend auf Metaphone-Algorithmen: Gibt 1 zurück, wenn Soundex-Codes übereinstimmen, sonst 0."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 1.0 if jellyfish.metaphone(a) == jellyfish.metaphone(b) else 0.0

def double_metaphone_similarity(a, b):
    """
    Doppelte Metaphone-Analyse:
    Betrachtet sowohl primäre als auch sekundäre phonetische Repräsentationen.
    Liefert 1.0, wenn eine Übereinstimmung besteht.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    da1, da2 = doublemetaphone(a)
    db1, db2 = doublemetaphone(b)
    codes_a = {c for c in [da1, da2] if c}
    codes_b = {c for c in [db1, db2] if c}
    return 1.0 if codes_a.intersection(codes_b) else 0.0

def normalize_name(s):
    """
    Standardisiert Strings zur besseren Vergleichbarkeit:
    - Kleinbuchstaben
    - Entfernt Sonderzeichen (nur a-z und 0-9 bleiben)
    """
    if pd.isna(s):
        return ""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

TEXT_COLS = ["vorname", "nachname", "strasse", "stadt", "land", 
             "email", "telefon"]

NUM_COLS = ["plz"]  # 'dhausnr' wurde entfernt, da Verzerrungsmöglichkeiten minimal und somit zu einfach für das Modell sind

def calculate_features_all(df, persist=False):
    """
    Berechnet eine Vielzahl an Ähnlichkeitsmaßen für jedes Attribut eines Paar-Datensatzes.
    
    Verwendete Techniken:
    - Levenshtein, Jaro-Winkler, Cosine Similarity
    - Phonetisch: Soundex, Metaphone, Double Metaphone
    - Für numerische Felder: einfache Gleichheit
    """
    df = df.copy().reset_index(drop=True)

    # Text-Spalten
    for col in TEXT_COLS:
        # Vorverarbeitung / Normalisierung
        df[f"{col}_1_norm"] = df[f"{col}_1"].fillna("").map(normalize_name)
        df[f"{col}_2_norm"] = df[f"{col}_2"].fillna("").map(normalize_name)

    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4))

    all_texts = []
    for col in TEXT_COLS:
        all_texts.extend(df[f"{col}_1_norm"])
        all_texts.extend(df[f"{col}_2_norm"])

    vectorizer.fit(all_texts)

    for col in TEXT_COLS:
        col1 = df[f"{col}_1_norm"]
        col2 = df[f"{col}_2_norm"]

        assert len(col1) == len(df)
        assert len(col2) == len(df)

        # Cosine
        vec_1 = vectorizer.transform(col1)
        vec_2 = vectorizer.transform(col2)
        df[f"sim_{col}_cos"] = cosine_similarity(vec_1, vec_2).diagonal()

        # klassische Similarities
        df[f"sim_{col}_lev"] = list(map(lev_similarity, col1, col2))
        df[f"sim_{col}_jw"] = list(map(jaro_winkler_similarity, col1, col2))
        df[f"sim_{col}_soundex"] = list(map(soundex_similarity, col1, col2))
        df[f"sim_{col}_metaphone"] = list(map(metaphone_similarity, col1, col2))
        df[f"sim_{col}_dmetaphone"] = list(map(double_metaphone_similarity, col1, col2))

    # --- 4. Numerische Features ---
    for col in NUM_COLS:
        c1 = pd.to_numeric(df[f"{col}_1"], errors="coerce").fillna(-1)
        c2 = pd.to_numeric(df[f"{col}_2"], errors="coerce").fillna(-1)
        df[f"sim_{col}_eq"] = (c1 == c2).astype(int)

    # --- Cleanup ---
    df = df.drop(columns=[c for c in df.columns if c.endswith("_norm")])

    return df