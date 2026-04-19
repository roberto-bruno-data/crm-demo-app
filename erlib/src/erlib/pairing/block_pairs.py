import pandas as pd

def block_by_first_letter(df, name_col="name", postal_col="billingpostalcode"):
    df = df.copy()

    df["block_key"] = (
        df[name_col]
        .fillna("X")
        .astype(str)
        .str.strip()
        .str.upper()
        .str[0]
    )

    if postal_col in df.columns:
        df["block_key"] += (
            df[postal_col]
            .fillna("0")
            .astype(str)
            .str.strip()
            .str[0]
        )

    return df

def build_block_pairs(df, max_block_size=80):

    if len(df) < 2:
        return pd.DataFrame()

    if len(df) > max_block_size:
        df = df.sample(max_block_size, random_state=42)

    pairs = []

    sources = df["source"].unique()

    # 👇 MULTI-SOURCE
    if len(sources) > 1:

        for i, s1 in enumerate(sources):
            for s2 in sources[i+1:]:

                left = df[df["source"] == s1]
                right = df[df["source"] == s2]

                for _, row_i in left.iterrows():
                    for _, row_j in right.iterrows():
                        pairs.append({
                            "entity_id_a": row_i["entity_id"],
                            "entity_id_b": row_j["entity_id"],
                            "block_key": row_i["block_key"]
                        })

    # 👇 SINGLE-SOURCE (dein Upload!)
    else:
        rows = df.to_dict("records")

        for i in range(len(rows)):
            for j in range(i+1, len(rows)):
                pairs.append({
                    "entity_id_a": rows[i]["entity_id"],
                    "entity_id_b": rows[j]["entity_id"],
                    "block_key": rows[i]["block_key"]
                })

    return pd.DataFrame(pairs)