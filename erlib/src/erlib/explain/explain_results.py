from erlib import explain
from erlib.utils import normalize_shap_output

import pandas as pd
import json

def run_explanation_pipeline(df, model, feature_cols, feature_groups, top_n=3):
    df = df.copy()
    df = df.reset_index(drop=True)

    df = explain.score_records(df, model, feature_cols)
    df = explain.add_probability_explanations(df)

    explainer = explain.xAI_production.XAIExplainer(model, feature_cols, feature_groups)

    shap_values_raw = explainer.compute_shap_values(df[feature_cols])
    shap_values = normalize_shap_output(shap_values_raw)

    df = explain.add_top_features(
        df,
        shap_values,
        feature_cols,
        top_n=top_n
    )

    df["nuanced_explanation"] = [
        explainer.explain_instance(
            shap_values[i],
            row_data=df.iloc[i]
        )
        for i in range(len(df))
    ]

    df["similarity_sentence"] = df.apply(
        lambda row: explain.build_similarity_sentence(
            row,
            feature_groups,
            prob=row["prob"],
        ),
        axis=1
    )

    group_shap_df = pd.DataFrame([
        explain.aggregate_group_shap(
            shap_values[i],
            feature_groups,
            feature_cols
        )
        for i in range(len(shap_values))
    ])

    shap_q50, shap_q80 = compute_shap_quantiles(
        shap_values,
        feature_groups,
        feature_cols
    )

    assert len(df) == len(shap_values), "Mismatch between df rows and SHAP values"
    

    df["detailed_explanation"] = [
        explain.build_detailed_explanation(
            row.match_category,
            row,
            shap_values[i],
            feature_groups,
            feature_cols,
            shap_q50,
            shap_q80,
        )
        for i, row in enumerate(df.itertuples())
    ]

    df["feature_contributions"] = [
        explain.aggregate_group_shap(
            shap_values[i],
            feature_groups,
            feature_cols
        )
        for i in range(len(shap_values))
    ]

    df["feature_contributions"] = df["feature_contributions"].apply(json.dumps)

    df = df.sort_values("prob", ascending=False)

    return df

def compute_shap_quantiles(shap_values, feature_groups, feature_cols):
    group_shap_df = pd.DataFrame([
        explain.aggregate_group_shap(
            shap_values[i],
            feature_groups,
            feature_cols
        )
        for i in range(len(shap_values))
    ])

    stacked = group_shap_df.stack()
    return stacked.quantile(0.5), stacked.quantile(0.8)