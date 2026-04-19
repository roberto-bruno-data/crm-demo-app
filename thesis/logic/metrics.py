import pandas as pd
from erlib.utils.constants import MATCH_CATEGORIES


def assign_match_category(prob: float, effective_threshold: float) -> str | None:
    if pd.isna(prob):
        return None
    if prob >= 0.9:
        return "Sichere Dublette"
    if prob >= 0.7:
        return "Wahrscheinliche Dublette"
    if prob >= effective_threshold:
        return "Unklare Dublette"
    return None


def compute_pair_metrics(data: dict, effective_threshold: float):
    review_df = data["review_df"].copy()

    review_df["match_category"] = review_df["prob"].apply(
        lambda p: assign_match_category(p, effective_threshold)
    )

    review_df = review_df[review_df["match_category"].notna()]

    total_candidates = len(review_df)
    total_candidates_all = data["total_candidates"]
    total_candidates_filtered = len(review_df)

    total_records = len(
        pd.unique(
            review_df[["entity_id_a", "entity_id_b"]].values.ravel()
        )
    ) if not review_df.empty else 0

    chart_data = (
        review_df["match_category"]
        .value_counts()
        .reindex(MATCH_CATEGORIES, fill_value=0)
        .reset_index()
    )
    chart_data.columns = ["Kategorie", "Anzahl"]

    counts_cat = dict(zip(chart_data["Kategorie"], chart_data["Anzahl"]))

    total_confirmed = counts_cat.get("Sichere Dublette", 0)
    total_probable = counts_cat.get("Wahrscheinliche Dublette", 0)
    total_unclear = counts_cat.get("Unklare Dublette", 0)

    dup_rate_sicher = (
        total_confirmed / total_candidates if total_candidates > 0 else 0
    )
    dup_rate_unsicher = (
        total_unclear / total_candidates if total_candidates > 0 else 0
    )

    return {
        "total_records": total_records,
        "total_candidates_all": total_candidates_all,
        "total_candidates_filtered": total_candidates_filtered,
        "total_confirmed": total_confirmed,
        "total_probable": total_probable,
        "total_unclear": total_unclear,
        "dup_rate_sicher": dup_rate_sicher,
        "dup_rate_unsicher": dup_rate_unsicher,
        "counts_cat": counts_cat,
        "chart_data": chart_data
    }