# Imports
import numpy as np
import random
from thesis.data_generation.data_generation import generate, duplicate, distort
from erlib.model import balance, train_validate_test_split_by_cluster as split_by_cluster
from erlib.pairing import build_pairs_with_hard_negatives
from erlib.features import calculate_features_all
from erlib.model import train_model
from erlib.model import evaluate_model
from erlib.explain import xAI_analysis
from erlib.utils import Split

def main():
    # Alle random*-Funktionen nutzen den globalen SEED
    # => Konstante zur Sicherstellung reproduzierbarer Ergebnisse
    # Im Falle einer Sensitivitätsanalyse den SEED ändern
    SEED = 42
    random.seed(SEED)
    np.random.seed(SEED)

    # Ausführung
    #_________________________________________________________________________

    # Rohdaten erzeugen & verzerren
    clean_df = generate(10000)

    # Füge kontrolliert Duplikate hinzu (z. B. durch Kopien mit gleichem cluster_id)
    duplicated_df = duplicate(clean_df)

    # Verzerrung der Datensätze, um Fehlerquellen zu simulieren (z. B. Tippfehler, PLZ-Abweichungen)
    distorted_df = distort(duplicated_df)

    # Aufteilung in Trainings-, Validierungs- und Testmenge auf Basis der cluster_id
    entities = Split(*split_by_cluster(distorted_df))

    # Erzeuge für jedes Splitset: positive Duplikate, zufällige Negative, sowie "Hard Negatives" (ähnliche, aber nicht gleiche)
    pairs = Split(
        build_pairs_with_hard_negatives(entities.train, n_random_neg=0.5, n_hard_neg=10),
        build_pairs_with_hard_negatives(entities.val,   n_random_neg=0.5, n_hard_neg=10),
        build_pairs_with_hard_negatives(entities.test,  n_random_neg=0.5, n_hard_neg=10),
    )

    print("Train size:", len(pairs.train))
    print("Validation size:", len(pairs.val))
    print("Test size:", len(pairs.test))

    # Berechnung von Ähnlichkeitsmaßen zwischen allen Attributen (Levenshtein, Jaro-Winkler, Cosine usw.)
    features = Split(calculate_features_all(pairs.train),
                            calculate_features_all(pairs.val),
                            calculate_features_all(pairs.test))

    # Train-Set bewusst unausgeglichen (z. B. 1:10) für realistische Modellierung
    # Val/Test ausgeglichen (1:1) für objektive Evaluation klassischer ML-Metriken
    balanced = Split(balance(features.train, multiple=10),
        balance(features.val, multiple=1),
        balance(features.test, multiple=1))

    # Verteilung prüfen
    print("Train balanced:", balanced.train['is_duplicate_pair'].value_counts())
    print("Val balanced:", balanced.val['is_duplicate_pair'].value_counts())
    print("Test balanced:", balanced.test['is_duplicate_pair'].value_counts())

    # Vorbereitung für das Modelltraining
    #_________________________________________________________________________

    # Relevante Feature-Spalten extrahieren
    # Nur Spalten, die mit "sim_" beginnen (d. h. berechnete Ähnlichkeitsmetriken)
    feature_cols = [c for c in balanced.train.columns if c.startswith("sim_")]

    # Trainingsdaten vorbereiten
    X_train = balanced.train[feature_cols]              # Merkmalsmatrix für das Training
    y_train = balanced.train["is_duplicate_pair"]       # Zielvariable (1 = Dublette, 0 = keine)

    # Validierungsdaten vorbereiten
    X_val = balanced.val[feature_cols]
    y_val = balanced.val["is_duplicate_pair"]

    # Testdaten vorbereiten
    X_test = balanced.test[feature_cols]
    y_test = balanced.test["is_duplicate_pair"]

    model = train_model(balanced.train, X_train, y_train)
    evaluate_model(model, X_val, y_val, X_test, y_test)
    xAI_analysis.explain_model(model, X_val, feature_cols, balanced.val, pairs.val, features.val)

    import joblib

    feature_cols = list(feature_cols)
    joblib.dump(
        {
            "model": model,
            "feature_cols": feature_cols,
            "threshold": 0.85,
            "trained_on": "synthetic_intrasource_v1",
            "seed": SEED,
        },
        "er_model_v1.joblib"
    )

if __name__ == "__main__":
    main()