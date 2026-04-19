import shap
import pandas as pd 
import numpy as np
from erlib.utils.shap_utils import similarity_to_text


DEFAULT_FEATURE_GROUPS = {
    "Name": [
        "sim_vorname_lev", "sim_vorname_jw", "sim_vorname_cos",
        "sim_nachname_lev", "sim_nachname_jw", "sim_nachname_cos"
    ],
    "Straße": [
        "sim_strasse_lev", "sim_strasse_jw", "sim_strasse_cos"
    ],
    "PLZ": ["sim_plz_eq"],
    "Stadt": [
        "sim_stadt_lev", "sim_stadt_jw", "sim_stadt_cos"
    ],
    "Land": [
        "sim_land_lev", "sim_land_jw", "sim_land_cos"
    ],
    "E-Mail": [
        "sim_email_lev", "sim_email_jw", "sim_email_cos"
    ],
    "Telefon": [
        "sim_telefon_lev", "sim_telefon_jw", "sim_telefon_cos"
    ]
}


class XAIExplainer:
    def __init__(
        self,
        model,
        feature_cols,
        feature_groups,
        prob_thresholds=(0.5, 0.9),
        shap_kwargs=None,
    ):
        self.model = model
        self.feature_cols = feature_cols
        self.feature_groups = feature_groups
        self.prob_thresholds = prob_thresholds

        self.explainer = shap.TreeExplainer(
            model,
            **(shap_kwargs or {
                "feature_perturbation": "tree_path_dependent",
                "model_output": "raw"
            })
        )

    def compute_shap_values(self, df):
        missing = set(self.feature_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Missing features: {missing}")

        return self.explainer.shap_values(df[self.feature_cols])
    
    def _group_shap_scores(self, shap_row):
        shap_series = pd.Series(shap_row, index=self.feature_cols)

        group_scores = []
        for label, feats in self.feature_groups.items():
            feats_existing = [f for f in feats if f in shap_series.index]
            if not feats_existing:
                continue

            shap_vals = shap_series[feats_existing].dropna()
            if shap_vals.empty:
                continue

            score = np.mean(np.abs(shap_vals))
            group_scores.append((label, score, feats_existing))

        return sorted(group_scores, key=lambda x: x[1], reverse=True)
    
    def explain_instance(self, shap_row, row_data=None, top_n=3):
        
        group_scores = self._group_shap_scores(shap_row)

        explanations = []
        for label, _, feats in group_scores[:top_n]:
            if row_data is not None:
                sims = [row_data.get(f, np.nan) for f in feats]
                valid = [s for s in sims if not pd.isna(s)]
                desc = similarity_to_text(np.max(valid)) if valid else "unbekannt"
            else:
                desc = "relevant"
            explanations.append(f"{label} {desc}")

        if explanations:
            return "; ".join(explanations)

        if row_data is not None:
            strong = []
            for label, feats in self.feature_groups.items():
                sims = [row_data.get(f, np.nan) for f in feats]
                valid = [s for s in sims if not pd.isna(s)]
                if valid and np.max(valid) >= 0.9:
                    strong.append(label)

            if strong:
                return "Hohe Übereinstimmung in: " + ", ".join(strong)

        return "Mehrere Merkmale tragen gemeinsam zur Entscheidung bei"

    def compute_global_group_importance(self, shap_values, feature_cols, feature_groups):
        shap_df = pd.DataFrame(shap_values, columns=feature_cols)
        importances = {}

        for group, feats in feature_groups.items():
            existing = [f for f in feats if f in shap_df.columns]
            if not existing:
                continue
            importances[group] = shap_df[existing].abs().mean().mean()

        return importances