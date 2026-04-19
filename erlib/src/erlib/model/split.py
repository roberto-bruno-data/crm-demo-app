from sklearn.model_selection import train_test_split

# Datensplitting
#_________________________________________________________________________

def train_validate_test_split_by_cluster(df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, SEED = 42):
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