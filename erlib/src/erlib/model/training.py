from sklearn.model_selection import GroupKFold, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier

def train_model(train_bal, X_train, y_train, SEED = 42):
    # Hyperparameteroptimierung
    #_________________________________________________________________________

    # Gruppen für K-Fold: Cluster-ID, um Leaks zu vermeiden
    groups = train_bal["cluster_id_1"]

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

    # Bestes Modell übernehmen und final trainieren
    best_rf = search.best_estimator_
    return best_rf.fit(X_train, y_train)