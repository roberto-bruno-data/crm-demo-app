def classify_match(prob):
    if prob >= 0.9:
        return "Sichere Dublette"
    elif prob >= 0.5:
        return "Wahrscheinliche Dublette"
    else:
        return "Unklare Dublette"
    
def score_records(df, model, feature_cols):
    df = df.copy()
    df["prob"] = model.predict_proba(df[feature_cols])[:, 1]
    return df
    
def add_probability_explanations(df):
    df = df.copy()
    df["match_category"] = df["prob"].apply(classify_match)

    df["prob_explanation"] = df["prob"].apply(
        lambda p: (
            "Sehr hohe Ähnlichkeit in mehreren Feldern, fast sicher identisch."
            if p >= 0.9 else
            "Mehrere Attribute ähnlich, mögliche Dublette; bitte prüfen."
            if p >= 0.5 else
            "Geringe Ähnlichkeit, eventuell verschiedene Unternehmen."
        )
    )
    return df