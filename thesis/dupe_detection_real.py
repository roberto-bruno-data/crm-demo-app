# Imports

from itertools import combinations
from tqdm import tqdm
import pandas as pd
import numpy as np
import random
import re
from rapidfuzz.distance import Levenshtein, JaroWinkler
import jellyfish
from metaphone import doublemetaphone
from sklearn.model_selection import train_test_split, GroupKFold, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    average_precision_score,
    matthews_corrcoef,
    roc_curve,
    precision_recall_curve,
    ConfusionMatrixDisplay
)
import matplotlib.pyplot as plt
import shap
from typing import cast
from scipy.sparse import csr_matrix
import awswrangler as wr # pyright: ignore[reportMissingImports]

# Alle random*-Funktionen nutzen den globalen SEED
# => Konstante zur Sicherstellung reproduzierbarer Ergebnisse
# Im Falle einer Sensitivitätsanalyse den SEED ändern
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Aktiviert die Visualisierungskomponente für SHAP (lokale Erklärungen)
shap.initjs()

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
    sim = JaroWinkler.similarity(a, b)
    return sim if sim <= 1 else sim / 100.0

# Einmalig initialisieren
_vect = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4))

def cosine_sim(a, b, vect=_vect):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    try:
        tfidf = cast(csr_matrix, vect.fit_transform([a, b]))
        return cosine_similarity(tfidf[0], tfidf[1])[0, 0]
    except ValueError:
        return 0.0  # falls beide Strings nur 1 Zeichen haben o.Ä.

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
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


TEXT_COLS = ["name","billingstreet","billingcity","billingstate","billingcountry","billingstatecode","billingcountrycode"]

NUM_COLS = ["billingpostalcode"] 

def calculate_features_all(df):
    """
    Berechnet eine Vielzahl an Ähnlichkeitsmaßen für jedes Attribut eines Paar-Datensatzes.
    
    Verwendete Techniken:
    - Levenshtein, Jaro-Winkler, Cosine Similarity
    - Phonetisch: Soundex, Metaphone, Double Metaphone
    - Für numerische Felder: einfache Gleichheit
    """
    df = df.copy()

    for col in TEXT_COLS:
        col1 = df[f"{col}_1"].astype(str).map(normalize_name)
        col2 = df[f"{col}_2"].astype(str).map(normalize_name)
        df[f"{col}_1_norm"], df[f"{col}_2_norm"] = col1, col2

        df[f"sim_{col}_lev"] = [lev_similarity(a, b) for a, b in zip(col1, col2)]
        df[f"sim_{col}_jw"]  = [jaro_winkler_similarity(a, b) for a, b in zip(col1, col2)]
        df[f"sim_{col}_cos"] = [cosine_sim(a, b) for a, b in zip(col1, col2)]
        df[f"sim_{col}_soundex"] = [soundex_similarity(a, b) for a, b in zip(col1, col2)]
        df[f"sim_{col}_metaphone"] = [metaphone_similarity(a, b) for a, b in zip(col1, col2)]
        df[f"sim_{col}_dmetaphone"] = [double_metaphone_similarity(a, b) for a, b in zip(col1, col2)]


    # Numerische Spalten
    for col in NUM_COLS:
        # Robustere Konvertierung zu Integern
        df[f"{col}_1_num"] = pd.to_numeric(df[f"{col}_1"], errors="coerce").fillna(-1)
        df[f"{col}_2_num"] = pd.to_numeric(df[f"{col}_2"], errors="coerce").fillna(-1)
        
        # Einfache binäre Übereinstimmung
        df[f"sim_{col}_eq"] = (df[f"{col}_1_num"] == df[f"{col}_2_num"]).astype(int)

    return df

# Datensplitting
#_________________________________________________________________________

def train_validate_test_split_by_cluster(df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    """
    Führt ein stratifiziertes Splitten der Daten durch, basierend auf 'cluster_id'.

    Warum wichtig:
    - Dubletten (bzw. Gruppen gleicher Entitäten) sollen nicht auf mehrere Splits verteilt werden.
    - So wird Daten-Leakage zwischen Training und Test/Validierung verhindert.

    Parameter:
    - df: DataFrame mit 'cluster_id' als Gruppierungseinheit
    - train_ratio: Anteil für Trainingsdaten (z. B. 0.7)
    - val_ratio: Anteil für Validierungsdaten (z. B. 0.15)
    - test_ratio: Anteil für Testdaten (z. B. 0.15)

    Rückgabe:
    - train_df, val_df, test_df: drei DataFrames mit nicht-überlappenden Clustern
    """

    # Schritt 1: Einzigartige Cluster-IDs extrahieren
    all_clusters = df["cluster_id"].unique()

    # Schritt 2: Zuerst Training vom Rest trennen
    train_ids, temp_ids = train_test_split(
        all_clusters, train_size=train_ratio, random_state=SEED
    )

    # Schritt 3: Den Rest (val + test) anhand Verhältnis aufteilen
    val_rel = val_ratio / (1 - train_ratio)  # Anteil relativ zum Rest
    val_ids, test_ids = train_test_split(
        temp_ids, train_size=val_rel, random_state=SEED
    )

    # Schritt 4: Cluster-Zuordnung auf Zeilenebene anwenden
    def assign_split(cid):
        if cid in train_ids:
            return "train"
        if cid in val_ids:
            return "val"
        if cid in test_ids:
            return "test"
        return "drop"

    df = df.copy()
    df["split"] = df["cluster_id"].apply(assign_split)

    # Schritt 5: Drei separate DataFrames extrahieren
    train_df = df[df["split"] == "train"].drop(columns="split")
    val_df   = df[df["split"] == "val"].drop(columns="split")
    test_df  = df[df["split"] == "test"].drop(columns="split")

    return train_df, val_df, test_df

# Markieren von Positivpaaren
#_________________________________________________________________________
def build_positive_pairs(df):
    pairs = []
    grouped = df.groupby("cluster_id")

    for cid, group in grouped:
        if len(group) < 2:
            continue  # Cluster mit nur einem Element überspringen

        # alle möglichen Paare im Cluster
        for (_, row1), (_, row2) in combinations(group.iterrows(), 2):
            pair = {
                "cluster_id": cid,
                "id_1": row1.get("netsuitecustomernumber", ""),
                "id_2": row2.get("netsuitecustomernumber", ""),
                "label": 1
            }

            for col in TEXT_COLS:
                pair[f"{col}_1"] = row1.get(col, "")
                pair[f"{col}_2"] = row2.get(col, "")

            for col in NUM_COLS:
                pair[f"{col}_1"] = row1.get(col, np.nan)
                pair[f"{col}_2"] = row2.get(col, np.nan)

            pairs.append(pair)

    return pd.DataFrame(pairs)

# Einbauen von zufälligen und „harten“ Negativbeispielen
#_________________________________________________________________________

def build_pairs_with_hard_negatives(df: pd.DataFrame, n_random_neg=1.0, n_hard_neg=10.0):
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
    # Beseitigen doppelter Indexwerte
    df = df.copy().reset_index(drop=True)

    # Doppelte Spalten (z. B. bei rename oder concat) entfernen
    df = df.loc[:, ~df.columns.duplicated()]

    pairs = []
    cols = [c for c in df.columns if c != "cluster_id"]

    # Positive Paare
    for cid, group in df.groupby("cluster_id"):
        idx = group.index.tolist()
        for i, j in combinations(idx, 2):
            row_i, row_j = df.loc[i], df.loc[j]
            pair = {f"{col}_1": row_i[col] for col in cols}
            pair.update({f"{col}_2": row_j[col] for col in cols})
            pair.update({
                "id_1": row_i.get("id", i),
                "id_2": row_j.get("id", j),
                "cluster_id_1": row_i["cluster_id"],
                "cluster_id_2": row_j["cluster_id"],
                "is_duplicate_pair": 1
            })
            pairs.append(pair)

    n_pos = len(pairs)

    # Zufällige Negative
    n_rand = int(n_pos * n_random_neg)
    all_idx = df.index.tolist()

    for _ in range(n_rand):
        i, j = random.sample(all_idx, 2)
        while df.at[i, "cluster_id"] == df.at[j, "cluster_id"]:
            j = random.choice(all_idx)
        row_i, row_j = df.loc[i], df.loc[j]
        pair = {f"{col}_1": row_i[col] for col in cols}
        pair.update({f"{col}_2": row_j[col] for col in cols})
        pair.update({
            "id_1": row_i.get("id", i),
            "id_2": row_j.get("id", j),
            "cluster_id_1": row_i["cluster_id"],
            "cluster_id_2": row_j["cluster_id"],
            "is_duplicate_pair": 0
        })
        pairs.append(pair)

    # Harte Negative 
    n_hard_target = int(n_pos * n_hard_neg)
    candidates = []

    for i, row in df.iterrows():
        pot = df[df["cluster_id"] != row["cluster_id"]]
        if pot.empty:
            continue

        same_name = pot["name"].apply(lambda x: Levenshtein.distance(str(x), str(row["name"])) <= 3)
        same_zip = pot["billingpostalcode"].astype(str) == str(row.get("billingpostalcode", ""))
        if "billingcity" in pot.columns and not isinstance(pot["billingcity"], pd.DataFrame):
            same_city = pot["billingcity"].astype(str).str.lower() == str(row.get("billingcity", "")).lower()
        else:
            same_city = pd.Series([False] * len(pot), index=pot.index)        
        same_state = pot["billingstatecode"].astype(str).str.lower() == str(row.get("billingstatecode", "")).lower()

        # Kombinationen (etwas "lockerer" für kleine Splits)
        hard = pot[
            same_name | same_zip | same_city |
            (same_name & same_zip) | (same_name & same_city) |
            (same_name & same_state) 
        ]

        # Falls keine Kandidaten, fallback: zufällige
        if hard.empty:
            hard = pot.sample(n=min(3, len(pot)), random_state=42)

        for j in hard.index:
            candidates.append((i, j))
            if len(candidates) >= n_hard_target:
                break
        if len(candidates) >= n_hard_target:
            break

    # Hinzufügen zum Dataset
    for i, j in candidates:
        row_i, row_j = df.loc[i], df.loc[j]
        pair = {f"{col}_1": row_i[col] for col in cols}
        pair.update({f"{col}_2": row_j[col] for col in cols})
        pair.update({
            "id_1": row_i.get("id", i),
            "id_2": row_j.get("id", j),
            "cluster_id_1": row_i["cluster_id"],
            "cluster_id_2": row_j["cluster_id"],
            "is_duplicate_pair": 0
        })
        pairs.append(pair)

    return pd.DataFrame(pairs)

# Sauberes Mergen von Positiv- und Negativbeispielen
#_________________________________________________________________________
def merge_positive_and_hardneg(pos_df, neg_df):
    """
    Vereinheitlicht und kombiniert positive Paare mit Hard Negatives.
    Stellt sicher:
    - Spaltenkonsistenz (label-Spalte, keine NAs)
    - Keine Duplikate
    - Korrekte Größenstatistik

    Parameter:
    ----------
    pos_df : pd.DataFrame
        Input-Daten mit Positivbeispielen
    neg_df : pd.DataFrame
        Input-Daten mit Negativbeispielen

    Rückgabe:
    ---------
    pd.DataFrame mit sauber verbundenen Paaren
    """
    neg_df = neg_df.rename(columns={"is_duplicate_pair": "label"})
    pos_df["label"] = 1


    shared_cols = sorted(set(pos_df.columns) | set(neg_df.columns))
    pos_df = pos_df.reindex(columns=shared_cols, fill_value=np.nan)
    neg_df = neg_df.reindex(columns=shared_cols, fill_value=np.nan)

    merged = pd.concat([pos_df, neg_df], ignore_index=True)

    merged["id_1"] = merged["id_1"].astype(str).str.strip()
    merged["id_2"] = merged["id_2"].astype(str).str.strip()

    # Deduplizieren
    merged = merged.drop_duplicates(subset=["id_1", "id_2"], keep="first")

    return merged

# Ausführung
#_________________________________________________________________________

# Laden der vorher erstellten Ground Truth
ground_truth = pd.read_csv("validated_clusters.csv")
ground_truth.columns = (
    ground_truth.columns
    .str.lower()
    .str.replace(" ", "", regex=False)
)

positive_pairs = build_positive_pairs(ground_truth)

train_df_positive, val_df_positive, test_df_positive = train_validate_test_split_by_cluster(positive_pairs)

# Athena-Partition einlesen
athena_df_partitioned = pd.read_csv("athena_result_newest.csv")
athena_df_partitioned.columns = (
    athena_df_partitioned.columns
    .str.lower()
    .str.replace(" ", "")
    .str.replace("_", "")
)

# Dummy-Cluster-ID hinzufügen, falls sie fehlt
if "cluster_id" not in athena_df_partitioned.columns:
    athena_df_partitioned["cluster_id"] = [
    f"U{i:07d}" for i in range(len(athena_df_partitioned))
]
athena_df_partitioned["cluster_id"] = athena_df_partitioned["cluster_id"].astype(str)

# Relevante Spalten aus beiden Datenquellen angleichen

rename_map = {
    "accountname": "name",
    "netsuitecustomernumber": "id"
}

ground_truth = ground_truth.rename(columns=rename_map)

train_pairs = build_pairs_with_hard_negatives(ground_truth, n_random_neg=2.0, n_hard_neg=10.0)
val_pairs = build_pairs_with_hard_negatives(ground_truth, n_random_neg=2.0, n_hard_neg=15.0)
test_pairs =build_pairs_with_hard_negatives(ground_truth, n_random_neg=2.0, n_hard_neg=15.0)

# Label-Fixierungen
for df_split in [train_df_positive, val_df_positive, test_df_positive]:
    df_split["cluster_id_1"] = df_split["cluster_id"]
    df_split["cluster_id_2"] = df_split["cluster_id"]
    df_split["label"] = 1

for df_split in [train_pairs, val_pairs, test_pairs]:
    df_split["label"] = df_split.get("is_duplicate_pair", 0)
    df_split.drop(columns=["is_duplicate_pair"], errors="ignore", inplace=True)

# Doppelte Spalten entfernen (können durch Zufall auftreten)
for name, df_obj in [("train_pairs", train_pairs), ("val_pairs", val_pairs), ("test_pairs", test_pairs)]:
    dupes = df_obj.columns[df_obj.columns.duplicated()]
    if len(dupes) > 0:
        df_obj = df_obj.loc[:, ~df_obj.columns.duplicated()]
    if name == "train_pairs": 
        train_pairs = df_obj
    elif name == "val_pairs": 
        val_pairs = df_obj
    else: 
        test_pairs = df_obj

# Zusammenführen mit robuster Merge-Funktion
train_df = merge_positive_and_hardneg(train_df_positive, train_pairs)
val_df   = merge_positive_and_hardneg(val_df_positive, val_pairs)
test_df  = merge_positive_and_hardneg(test_df_positive, test_pairs)

# Nur Feature-relevante Spalten behalten
keep_cols = [
    c for c in train_df.columns
    if any(s in c for s in ["_1", "_2", "id_1", "id_2", "cluster_id_1", "cluster_id_2", "label"])
]

for df in [train_df, val_df, test_df]:
    if "label" not in df.columns:
        if "is_duplicate_pair" in df.columns:
            df["label"] = df["is_duplicate_pair"]
        else:
            raise ValueError("Keine Label-Spalte (label oder is_duplicate_pair) im Datensatz gefunden!")

train_df_clean = train_df[keep_cols].copy()
val_df_clean   = val_df[keep_cols].copy()
test_df_clean  = test_df[keep_cols].copy()

# Berechnen der Metriken
train_feat = calculate_features_all(train_df_clean)
val_feat   = calculate_features_all(val_df_clean)
test_feat  = calculate_features_all(test_df_clean)

# Vorbereitung für das Modelltraining
#_________________________________________________________________________

# Relevante Feature-Spalten extrahieren
# Nur Spalten, die mit "sim_" beginnen (d. h. berechnete Ähnlichkeitsmetriken)

feature_cols = [c for c in train_feat.columns if c.startswith("sim_")]
label_col = "label"


X_train, y_train = train_feat[feature_cols], train_feat[label_col]
X_val, y_val     = val_feat[feature_cols], val_feat[label_col]
X_test, y_test   = test_feat[feature_cols], test_feat[label_col]

#Hyperparameteroptimierung
#_________________________________________________________________________

# Gruppen für K-Fold: Cluster-ID, um Leaks zu val_feat
groups = train_df["cluster_id"].fillna(train_df["id_1"]).astype(str)

# Hyperparameter-Suchraum definieren
param_dist = {
    "n_estimators": [100, 200, 500],
    "max_depth": [None, 10, 20, 30],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "max_features": ["sqrt", "log2", None]
}

# Cross-Validation Setup
cv = GroupKFold(n_splits=5)

# Random Forest mit Randomized SearchCV
rf = RandomForestClassifier(class_weight="balanced", random_state=SEED)

search = RandomizedSearchCV(
    estimator=rf,
    param_distributions=param_dist,
    n_iter=50,
    cv=cv,
    scoring="average_precision", # PR-AUC
    n_jobs=-1,                   # Nutzt alle verfügbaren Prozessoren. Anmerkung: Kann je nach Maschine Reproduzierbarkeit beeinflussen.
    verbose=2,
    random_state=SEED
)

# Suche starten
search.fit(X_train, y_train, groups=groups)

print(f"\nOptimale gefundene Parameter: {search.best_params_}")
print(f"Bestes CV-Score (PR-AUC): {search.best_score_:.4f}")

# Evaluation
#_________________________________________________________________________
best_rf = cast(RandomForestClassifier, search.best_estimator_)

# Validation
y_val_prob = best_rf.predict_proba(X_val)[:, 1]
y_val_pred = (y_val_prob >= 0.5).astype(int)

# Test
y_test_prob = best_rf.predict_proba(X_test)[:, 1]
y_test_pred = (y_test_prob >= 0.5).astype(int)

# Confusion Matrix
ConfusionMatrixDisplay.from_estimator(best_rf, X_test, y_test, cmap="Blues")
plt.title("Confusion Matrix (Test)")
plt.show()

# Validation Performance
print("Validation Report:")
print(classification_report(y_val, y_val_pred))

# Test Performance
y_test_pred = best_rf.predict(X_test)
print("Test Report:")
print(classification_report(y_test, y_test_pred))

# Wahrscheinlichkeiten für ROC/PR
y_val_prob = best_rf.predict_proba(X_val)[:, 1]
y_test_prob = best_rf.predict_proba(X_test)[:, 1]

# Metriken: Validation
print("Validation ROC-AUC:", roc_auc_score(y_val, y_val_prob))
print("Validation PR-AUC :", average_precision_score(y_val, y_val_prob))
print("Validation MCC    :", matthews_corrcoef(y_val, y_val_pred))

# Metriken: Test
print("Test ROC-AUC:", roc_auc_score(y_test, y_test_prob))
print("Test PR-AUC :", average_precision_score(y_test, y_test_prob))
print("Test MCC    :", matthews_corrcoef(y_test, y_test_pred))

# ROC- und PR-Kurven für Test-Set
fpr, tpr, _ = roc_curve(y_test, y_test_prob)
prec, rec, _ = precision_recall_curve(y_test, y_test_prob)

fig, ax = plt.subplots(1, 2, figsize=(12, 5))

# ROC
ax[0].plot(fpr, tpr, label=f"ROC AUC = {roc_auc_score(y_test, y_test_prob):.2f}")
ax[0].plot([0, 1], [0, 1], 'k--', alpha=0.6)
ax[0].set_xlabel("False Positive Rate")
ax[0].set_ylabel("True Positive Rate")
ax[0].set_title("ROC Curve (Test)")
ax[0].legend(loc="lower right")

# PR
ax[1].plot(rec, prec, label=f"PR AUC = {average_precision_score(y_test, y_test_prob):.2f}")
ax[1].set_xlabel("Recall")
ax[1].set_ylabel("Precision")
ax[1].set_title("Precision-Recall Curve (Test)")
ax[1].legend(loc="lower left")

plt.tight_layout()
plt.show()

# xAI-Komponente
#_________________________________________________________________________

explainer = shap.TreeExplainer(best_rf, feature_perturbation="tree_path_dependent", model_output="raw")
shap_values_raw = explainer.shap_values(X_val)

# Einheitliches SHAP-Format herstellen (positive Klasse = Index 1)
if isinstance(shap_values_raw, list):
    shap_values = shap_values_raw[1]
elif isinstance(shap_values_raw, np.ndarray) and shap_values_raw.ndim == 3:
    shap_values = shap_values_raw[:, :, 1]
else:
    shap_values = shap_values_raw

# Plotting
shap.summary_plot(shap_values, X_val, feature_names=feature_cols)

# Athena-Abfrage ausführen und Ergebnis in ein Pandas DataFrame laden (anonymisiert)
athena_df = wr.athena.read_sql_query(
    sql="SELECT ... FROM <tabelle> WHERE extraction_date=CURRENT_DATE;",
    database="<datenbank>"
)

athena_df.to_csv("athena_result_newest_today.csv", index=False)

# Blocking-Funktionen bleiben unverändert
def block_by_first_letter(df, name_col="name", postal_col="billingpostalcode"):
    df = df.copy()
    df["block_key"] = (
        df[name_col]
        .astype(str).str.strip().str.upper().str[0].fillna("X")
    )
    if postal_col in df.columns:
        df["block_key"] += (
            df[postal_col]
            .astype(str).str.strip().str[0].fillna("0")
        )
    return df

def build_block_pairs(df, max_block_size=80):
    """Baut alle möglichen Paare innerhalb eines Blocks.
    Achtung: Blockgröße wird limitiert, um Explosion zu vermeiden!
    """
    if len(df) < 2:
        return pd.DataFrame()
    if len(df) > max_block_size:
        df = df.sample(max_block_size, random_state=42)
    pairs = []
    for i, j in combinations(df.index, 2):
        row_i, row_j = df.loc[i], df.loc[j]
        pair = {f"{col}_1": row_i[col] for col in df.columns}
        pair.update({f"{col}_2": row_j[col] for col in df.columns})
        pairs.append(pair)
    return pd.DataFrame(pairs)

# Anwendung Blocking
athena_df_blocked = block_by_first_letter(athena_df)

# Cluster-ID hinzufügen
athena_df_blocked["cluster_id"] = [f"C{i:07d}" for i in range(len(athena_df_blocked))]

crm_pairs = []

# Parallelisierung: Paare bauen
for block_key, block in tqdm(athena_df_blocked.groupby("block_key"), desc="Building block pairs"):
    df_block_pairs = build_block_pairs(block, max_block_size=80)
    if not df_block_pairs.empty:
        crm_pairs.append(df_block_pairs)

crm_pairs = pd.concat(crm_pairs, ignore_index=True)
crm_pairs.to_csv("pairs_blocked.csv", index=False)

# Feature-Berechnung
crm_feat = calculate_features_all(crm_pairs)

# Vorhersage
crm_feat["prob"] = best_rf.predict_proba(
    crm_feat[[c for c in crm_feat.columns if c.startswith("sim_")]]
)[:, 1]

# Mapping IDs nach Bedarf
if "id_1" not in crm_feat.columns and "netsuitecustomernumber_1" in crm_feat.columns:
    crm_feat = crm_feat.rename(columns={
        "netsuitecustomernumber_1": "id_1",
        "netsuitecustomernumber_2": "id_2"
    })

before = len(crm_feat)
crm_feat.columns.tolist()[:20]

# Symmetrische Paare deduplizieren
crm_feat["pair_key"] = crm_feat.apply(
    lambda r: "_".join(sorted([str(r["id_1"]), str(r["id_2"])])), axis=1
)

crm_feat = crm_feat.drop_duplicates(subset="pair_key", keep="first").drop(columns="pair_key")

after = len(crm_feat)

# Klassifikation
def classify_match(prob):
    if prob >= 0.9:
        return "Sichere Dublette"
    elif prob >= 0.5:
        return "Wahrscheinliche Dublette"
    else:
        return "Unklare Dublette"

crm_feat["match_category"] = crm_feat["prob"].apply(classify_match)

# Textliche Erklärung zur Wahrscheinlichkeit
def explanation_from_prob(prob):
    if prob >= 0.9:
        return "Sehr hohe Ähnlichkeit in mehreren Feldern, fast sicher identisch."
    elif prob >= 0.5:
        return "Mehrere Attribute ähnlich, mögliche Dublette – bitte prüfen."
    else:
        return "Geringe Ähnlichkeit, eventuell verschiedene Unternehmen."

crm_feat["prob_explanation"] = crm_feat["prob"].apply(explanation_from_prob)

# SHAP-DataFrame
shap_df = pd.DataFrame(shap_values, columns=feature_cols)

# Top-Features pro Zeile
def top_features_for_row(shap_row, features, top_n=3):
    shap_series = pd.Series(shap_row, index=features).abs().sort_values(ascending=False)
    return ", ".join(shap_series.head(top_n).index)

crm_feat["top_features"] = [
    top_features_for_row(shap_values[i], feature_cols)
    for i in range(len(crm_feat))
]

crm_feat.to_csv("crm_results_with_shap.csv", index=False)

# Ähnlichkeitsgruppen definieren
feature_groups = {
    "Name": ["sim_name_lev", "sim_name_jw", "sim_name_cos", "sim_name_soundex"],
    "Straße": ["sim_billingstreet_lev", "sim_billingstreet_jw", "sim_billingstreet_cos"],
    "Stadt": ["sim_billingcity_lev", "sim_billingcity_jw", "sim_billingcity_cos"],
    "PLZ": ["sim_billingpostalcode_eq"],
    "Land": ["sim_billingcountrycode_eq"],
}

def similarity_to_text(value):
    if pd.isna(value):
        return "unbekannt"
    if value >= 0.98:
        return "identisch"
    elif value >= 0.85:
        return "sehr ähnlich"
    elif value >= 0.5:
        return "leicht ähnlich"
    else:
        return "unterschiedlich"

def explain_instance_grouped(shap_row, feature_cols, row_data=None, top_n=3):
    explanations = []
    shap_series = pd.Series(shap_row, index=feature_cols)

    for label, feats in feature_groups.items():
        feats_existing = [f for f in feats if f in shap_series.index]
        if not feats_existing:
            continue

        relevant = shap_series[feats_existing].dropna()
        if relevant.empty:
            continue

        mean_importance = abs(relevant).mean()

        if row_data is not None:
            sims = [row_data.get(f, np.nan) for f in feats_existing]
            avg_score = np.nanmean(sims)
            desc = similarity_to_text(avg_score)
        else:
            desc = "relevant"

        explanations.append((mean_importance, f"{label} {desc}"))

    explanations = sorted(explanations, key=lambda x: x[0], reverse=True)[:top_n]

    seen = set()
    unique_expl = []
    for _, e in explanations:
        key = e.split()[0]
        if key not in seen:
            seen.add(key)
            unique_expl.append(e)

    return "; ".join(unique_expl) if unique_expl else "Keine dominante Ähnlichkeit erkennbar"

crm_feat["nuanced_explanation"] = [
    explain_instance_grouped(shap_values[i], feature_cols, row_data=crm_feat.iloc[i])
    for i in range(len(crm_feat))
]

crm_feat.to_csv("crm_results_with_nuanced_shap.csv", index=False)

# Spalten bereinigen für Tableau
drop_cols = [
    c for c in crm_feat.columns
    if any(x in c for x in ["_norm", "_num", "block_key", "Unnamed"])
] + ["top_features", "prob_category"]

crm_feat_for_tableau = crm_feat.drop(columns=drop_cols, errors="ignore")

# Sinnvolle Spaltenreihenfolge
preferred_order = [
    "id_1", "name_1", "billingstreet_1", "billingcity_1", "billingpostalcode_1", "billingcountry_1",
    "id_2", "name_2", "billingstreet_2", "billingcity_2", "billingpostalcode_2", "billingcountry_2",
    "prob", "match_category", "prob_explanation", "nuanced_explanation"
]

existing_cols = [c for c in preferred_order if c in crm_feat_for_tableau.columns]
remaining_cols = [c for c in crm_feat_for_tableau.columns if c not in existing_cols]

crm_feat_for_tableau = crm_feat_for_tableau[existing_cols + remaining_cols]

# Sortieren
crm_feat_for_tableau = crm_feat_for_tableau.sort_values("prob", ascending=False).reset_index(drop=True)

# Finaler Export für Tableau
crm_feat_for_tableau.to_csv("crm_results_for_tableau_final.csv", index=False, encoding="utf-8-sig")