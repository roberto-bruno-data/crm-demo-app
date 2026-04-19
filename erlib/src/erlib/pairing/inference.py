import pandas as pd
from tqdm import tqdm
from .block_pairs import block_by_first_letter, build_block_pairs

def assert_entity_df(df):
    bad = [c for c in df.columns if c.endswith("_1") or c.endswith("_2")]
    assert not bad, f"Pair columns leaked into entity DF: {bad}"
    assert df.columns.is_unique, "Duplicate columns in entity DF"

def build_candidate_pairs(
    entity_df: pd.DataFrame,
    name_col="vorname",
    postal_col="plz",
    max_block_size=1000,
    persist=False
):
    """
    Baut Kandidatenpaare (Salesforce ↔ Netsuite) aus harmonisierten Entities.
    """

    assert_entity_df(entity_df)

    blocked = block_by_first_letter(entity_df, name_col, postal_col)
    pairs = []

    for _, block in tqdm(blocked.groupby("block_key"), desc="Building block pairs"):
        assert_entity_df(block)

        df_block_pairs = build_block_pairs(block, max_block_size=max_block_size)

        if not df_block_pairs.empty:
            pairs.append(df_block_pairs)

    if not pairs:
        return pd.DataFrame()
    
    if persist:
        df_block_pairs.to_csv("CSVs/pairs_blocked.csv", index=False)

    return pd.concat(pairs, ignore_index=True)
