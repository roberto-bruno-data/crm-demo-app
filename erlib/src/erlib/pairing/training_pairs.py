import random
from itertools import combinations
import pandas as pd
from rapidfuzz.distance import Levenshtein

# Einbauen „harter“ Negativbeispiele
#_________________________________________________________________________

def build_pairs_with_hard_negatives(df: pd.DataFrame, n_random_neg=1.0, n_hard_neg=1.0):
    """
    Erstellt Trainingspaare für Dublettenerkennung durch Kombination:
    - Positiver Paare (echte Duplikate, d.h. aus demselben Cluster)
    - Zufälliger negativer Paare (verschiedene Cluster, zufällig)
    - "Harte" negative Paare (verschiedene Cluster, aber absichtlich ähnlich)

    Parameter:
    ----------
    df : pd.DataFrame
        Input-Daten mit Spalte `cluster_id` zur Gruppierung.
    n_random_neg : float
        Verhältnis zufälliger negativer Paare zu positiven (Standard: 1.0).
    n_hard_neg : float
        Verhältnis harter negativer Paare zu positiven (Standard: 1.0).

    Rückgabe:
    ---------
    pd.DataFrame mit strukturierten Paaren, Labels (1 = Dublette, 0 = Nicht-Dublette) und Meta-Infos.
    """
    
    pairs = []
    cols = [c for c in df.columns if c != "cluster_id"]

    # 1) Positive Paare: Alle Kombinationen innerhalb eines Clusters
    for cid, group in df.groupby("cluster_id"):
        idx = group.index.tolist()
        for i, j in combinations(idx, 2):
            row_i, row_j = df.loc[i], df.loc[j]
            pair = {f"{col}_1": row_i[col] for col in cols}
            pair.update({f"{col}_2": row_j[col] for col in cols})
            pair.update({
                "id_1": i, "id_2": j,
                "cluster_id_1": row_i["cluster_id"],
                "cluster_id_2": row_j["cluster_id"],
                "is_duplicate_pair": 1
            })
            pairs.append(pair)

    n_pos = len(pairs)  # Merke Anzahl positiver Paare

    # 2) Zufällige Negative: Zwei beliebige Personen aus verschiedenen Clustern
    n_rand = int(n_pos * n_random_neg)
    all_idx = df.index.tolist()

    for _ in range(n_rand):
        i, j = random.sample(all_idx, 2)
        while df.at[i, "cluster_id"] == df.at[j, "cluster_id"]:
            j = random.choice(all_idx)  # sicherstellen, dass Cluster unterschiedlich
        row_i, row_j = df.loc[i], df.loc[j]
        pair = {f"{col}_1": row_i[col] for col in cols}
        pair.update({f"{col}_2": row_j[col] for col in cols})
        pair.update({
            "id_1": i, "id_2": j,
            "cluster_id_1": row_i["cluster_id"],
            "cluster_id_2": row_j["cluster_id"],
            "is_duplicate_pair": 0
        })
        pairs.append(pair)

    # 3) Harte Negative: Ähnliche, aber nicht-identische Personen (aus anderen Clustern)
    n_hard = int(n_pos * n_hard_neg)
    candidates = []

    for i, row in df.iterrows():
        pot = df[df["cluster_id"] != row["cluster_id"]]  # nur andere Cluster

        # Ähnlichkeitslogik (Feldweise oder kombiniert)
        same_last = pot["nachname"].apply(
            lambda x: Levenshtein.distance(str(x), str(row["nachname"])) <= 3
        )
        same_zip = pot["plz"].astype(str) == str(row.get("plz", ""))
        same_city = pot["stadt"].astype(str).str.lower() == str(row.get("stadt", "")).lower()
        same_domain = pot["email"].apply(
            lambda x: str(x).split("@")[-1] if pd.notna(x) else ""
        ) == str(row.get("email", "")).split("@")[-1]
        same_land = pot["land"].astype(str).str.lower() == str(row.get("land", "")).lower()

        # Kombinationen: schwerer unterscheidbare Nicht-Dubletten durch Gleichheit mancher Felder
        combo1 = same_last & same_zip
        combo2 = same_last & same_city
        combo3 = same_domain & same_city
        combo4 = same_land & same_zip

        hard = pot[
            same_last | same_zip | same_city | same_domain | same_land |
            combo1 | combo2 | combo3 | combo4
        ]

        for j in hard.index:
            candidates.append((i, j))

    # Kandidaten mischen & beschränken
    random.shuffle(candidates)
    candidates = candidates[:n_hard]

    # Hinzufügen "harter" Negativ-Paare
    for i, j in candidates:
        row_i, row_j = df.loc[i], df.loc[j]
        pair = {f"{col}_1": row_i[col] for col in cols}
        pair.update({f"{col}_2": row_j[col] for col in cols})
        pair.update({
            "id_1": i, "id_2": j,
            "cluster_id_1": row_i["cluster_id"],
            "cluster_id_2": row_j["cluster_id"],
            "is_duplicate_pair": 0
        })
        pairs.append(pair)

    print(f"Gesamt: {len(pairs)} Paare (Positiv: {n_pos}, Negativ: {len(pairs) - n_pos})")
    return pd.DataFrame(pairs)

# Datenproportionierung
#_________________________________________________________________________

def ratio_duplicates(base_df, duplicate_multiple=2, SEED=42):
    """
    Balanciert den Datensatz durch Downsampling der Negativbeispiele.

    Ziel:
    - Für jedes Duplikatpaar (is_duplicate_pair == 1) sollen 'duplicate_multiple' 
      Nicht-Duplikatpaare (is_duplicate_pair == 0) vorhanden sein.
    - Verhindert ein zu starkes Klassenungleichgewicht beim Training.

    Parameter:
    - base_df: DataFrame mit Paaren (enthält Spalte 'is_duplicate_pair')
    - duplicate_multiple: Verhältnis von negativen zu positiven Beispielen

    Rückgabe:
    - Ein balanced DataFrame mit positiven und n_neg negativen Paaren
    """
    # Alle positiven und negativen Paare trennen
    pos = base_df[base_df["is_duplicate_pair"] == 1]
    neg = base_df[base_df["is_duplicate_pair"] == 0]

    # Zielanzahl an negativen Paaren berechnen
    n_neg = int(len(pos) * duplicate_multiple)
    n_neg = min(n_neg, len(neg))  # nicht mehr als verfügbar

    # Zufällige Auswahl der negativen Paare
    neg_sample = neg.sample(n=n_neg, random_state=SEED)

    # Kombination von positiven und ausgewählten negativen Paaren
    balanced = pd.concat([pos, neg_sample]).reset_index(drop=True)
    
    return balanced