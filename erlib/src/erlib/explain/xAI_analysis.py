import shap
import pandas as pd
from IPython.display import display
import numpy as np

def explain_model(best_rf, X_val, feature_cols, val_bal, val_pairs, val_feat):
    # Aktiviert die Visualisierungskomponente für SHAP (lokale Erklärungen)
    shap.initjs()
    base_fields = ["vorname", "nachname", "strasse", "stadt", "land", "email", "telefon", "plz"]

    # xAI-Komponente
    #_________________________________________________________________________

    # Initialisierung von TreeSHAP
    explainer = shap.TreeExplainer(best_rf)
    shap_values = explainer.shap_values(X_val)

    # Robust bestimmen, was geplottet werden soll
    if isinstance(shap_values, list) and len(shap_values) == 2:
        # klassischer Output bei alter SHAP-Version
        shap_to_plot = shap_values[1]        # Werte für Klasse 1
    else:
        # neuer Output: direkt 2D-Array (samples x features)
        shap_to_plot = shap_values

    shap_matrix = shap_to_plot

    # Feature-Namen sicherstellen (sollten zu X_val passen)
    assert shap_to_plot.shape[1] == X_val.shape[1], \
        f"Mismatch: shap_values hat {shap_to_plot.shape[1]} Features, X_val {X_val.shape[1]}"

    # Globale Feature-Importanzen
    shap.summary_plot(shap_to_plot, X_val, feature_names=feature_cols)

    # ---------------------------------------------
    # Ziel-Paar festlegen für ein anschauliches Beispiel
    target_idx = 6
    # ---------------------------------------------

    if target_idx not in val_bal.index:
        print(f"Paar {target_idx} wurde beim Balancing NICHT übernommen.")
        pos_in_Xval = None
    else:
        pos_in_Xval = val_bal.index.get_loc(target_idx)
        print(f"Paar {target_idx} ist im Balanced-Set an Position {pos_in_Xval}")
    
    if pos_in_Xval is None:
        return

    # ---- Rohdaten & Featurewerte ----
    row_raw  = val_pairs.loc[target_idx]      # Original + verzerrt
    shap_row = shap_matrix[pos_in_Xval]    # SHAP-Werte für dieses Paar

    rows_orig = []

    for field in base_fields:
        rows_orig.append({
            "Feld": field,
            "Original Faker 1": row_raw.get(f"{field}_1_orig", ""),
            "Original Faker 2": row_raw.get(f"{field}_2_orig", ""),
            "Verzerrt 1": row_raw.get(f"{field}_1", ""),
            "Verzerrt 2": row_raw.get(f"{field}_2", ""),
        })

    table_orig = pd.DataFrame(rows_orig)
    display(table_orig)

    # ---- Tabelle bauen für das gewählte Beispiel ----
    rows = []
    for feat, shap_val in zip(feature_cols, shap_row):

        shap_val = np.asarray(shap_val)
        if shap_val.ndim > 0:
            shap_val = shap_val[-1]
        shap_val = float(shap_val)

        field = feat.replace("sim_", "").split("_")[0]
        rows.append({
            "Feld": field,
            "Original Faker 1": row_raw.get(f"{field}_1_orig", ""),
            "Original Faker 2": row_raw.get(f"{field}_2_orig", ""),
            "Verzerrt 1": row_raw.get(f"{field}_1", ""),
            "Verzerrt 2": row_raw.get(f"{field}_2", ""),
            "Feature": feat,
            "Feature-Wert": X_val.iloc[pos_in_Xval][feat],
            "TreeSHAP-Impact": shap_val
        })

    table = pd.DataFrame(rows)

    # sortieren nach absolutem SHAP-Wert
    table = table.reindex(table["TreeSHAP-Impact"].abs().sort_values(ascending=False).index)

    display(table)

    # Lokale Feature-Importanzen
    shap.decision_plot(
        explainer.expected_value[1],
        table["TreeSHAP-Impact"].values,                 # exakt sortierte SHAP-Werte
        table["Feature-Wert"].values,      # Modellinput in derselben Reihenfolge
        feature_names=table["Feature"].values,
        show=True
    )
