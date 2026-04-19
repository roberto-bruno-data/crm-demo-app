import pandas as pd

def top_features_for_row(shap_row, feature_cols, top_n=3):
    shap_series = (
        pd.Series(shap_row, index=feature_cols)
        .abs()
        .sort_values(ascending=False)
    )
    return list(shap_series.head(top_n).index)


def add_top_features(df, shap_values, feature_cols, top_n=3, col_name="top_features"):
    df = df.copy()
    df[col_name] = [
        ", ".join(top_features_for_row(shap_values[i], feature_cols, top_n))
        for i in range(len(df))
    ]
    return df
