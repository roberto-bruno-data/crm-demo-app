def prepare_for_tableau(df):
    drop_cols = [
        c for c in df.columns
        if any(x in c for x in ["_norm", "_num", "block_key", "Unnamed"])
    ] + ["nuanced_explanation", "prob_explanation"]

    df = df.drop(columns=drop_cols, errors="ignore")

    preferred_order = [
        "prob",
        "match_category",
        "similarity_sentence",
        "detailed_explanation",
        "id_1", "name_1", "billingstreet_1", "billingcity_1", "billingpostalcode_1", "billingcountry_1",
        "id_2", "name_2", "billingstreet_2", "billingcity_2", "billingpostalcode_2", "billingcountry_2"
    ]

    existing = [c for c in preferred_order if c in df.columns]
    remaining = [c for c in df.columns if c not in existing]

    assert "similarity_sentence" in df.columns
    
    return (
        df[existing + remaining]
        .sort_values("prob", ascending=False)
        .reset_index(drop=True)
    )