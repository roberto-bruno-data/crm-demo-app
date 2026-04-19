import json
from datetime import datetime
from sqlalchemy import text
from thesis.logic.helpers import convert_value
from collections import Counter
from thesis.logic.cluster_metrics import compute_cluster_score
from thesis.config.preferences import load_preferences
import pandas as pd

def build_golden_record(values, locks):
    return {
        attr: values.get(attr)
        for attr in values
        if locks.get(attr, False)
    }

def save_golden_record(
    run_id,
    cluster_id,
    golden_record,
    model_info,
    sf_snapshot,
    ns_snapshot,
    cluster_entities_df,
    engine,
    threshold,
    cluster_pairs
):

    # --- Entities bauen ---
    EXCLUDE_COLS = {"entity_id", "run_id", "cluster_id", "cluster_size"}

    cluster_entities = []

    for _, row in cluster_entities_df.iterrows():
        entity = {
            "entity_id": int(row["entity_id"]),
            "source": str(row.get("source") or "unknown"),
            "data": {
                col: convert_value(row[col])
                for col in cluster_entities_df.columns
                if col not in EXCLUDE_COLS
            }
        }
        cluster_entities.append(entity)

    # --- Audit bauen ---
    # audit_entry = {
    #     "cluster_id": int(cluster_id),
    #     "timestamp": datetime.utcnow().isoformat() + "Z",
    #     "source_records": {
    #         "salesforce": sf_snapshot,
    #         "netsuite": ns_snapshot
    #     },
    #     "cluster_entities": cluster_entities,
    #     "model": {
    #         "probability": float(model_info["prob"]),
    #         "category": model_info["match_category"],
    #         "explanation": model_info["similarity_sentence"],
    #         "top_features": model_info["top_features"],
    #         "detailed_explanation": model_info["detailed_explanation"],
    #         "version": "v0.1"
    #     },
    #     "golden_record": golden_record
    # }

    audit_entry = build_audit_payload(run_id, cluster_id, cluster_entities, cluster_pairs, model_info, golden_record, threshold)


    audit_entry = convert_value(audit_entry)
    golden_record = convert_value(golden_record)

    # --- DB Write ---
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO golden_records (run_id, cluster_id, num_entities, golden_record, audit)
                VALUES (:run_id, :cluster_id, :num_entities, :golden_record, :audit)
                ON CONFLICT DO NOTHING
            """),
            {
                "run_id": run_id,
                "cluster_id": int(cluster_id),
                "num_entities": len(cluster_entities_df),
                "golden_record": json.dumps(golden_record),
                "audit": json.dumps(audit_entry)
            }
        )

def resolve_attribute(values):
    values = [v for v in values if v not in [None, ""]]

    if not values:
        return None, False

    counts = Counter(values)
    most_common = counts.most_common()

    top_value, top_count = most_common[0]

    # Prüfe Gleichstand
    ties = [v for v, c in most_common if c == top_count]

    if len(ties) > 1:
        return top_value, False  # unsicher
    else:
        return top_value, True   # eindeutig
    
def build_audit_payload(
    run_id,
    cluster_id,
    cluster_entities,
    cluster_pairs,
    model_info,
    golden_record,
    threshold
):
    metrics = compute_cluster_score(cluster_pairs, len(cluster_entities))

    cluster_metrics = {
        "score": metrics["score"],
        "harmonic": metrics["harmonic"],
        "mean": metrics["mean"],
        "min": metrics["min"],
        "coverage": metrics["coverage"],
    }

    if cluster_pairs.empty:
        pair_evidence = {"strongest": [], "weakest": []}
    else:
        top_pairs = cluster_pairs.nlargest(3, "prob")
        weakest_pair = cluster_pairs.nsmallest(1, "prob")

        pair_evidence = {
            "strongest": extract_pair_info(top_pairs),
            "weakest": extract_pair_info(weakest_pair),
        }

    merge_decision = {
        "threshold": float(threshold),
        "score": float(cluster_metrics["score"]),
        "auto_merged": float(cluster_metrics["score"]) >= float(threshold)
    }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "cluster_id": cluster_id,

        "cluster_entities": cluster_entities,
        "cluster_metrics": cluster_metrics,
        "pair_evidence": pair_evidence,

        "model": {
            "probability": float(model_info.get("prob", 0)),
            "category": model_info.get("match_category"),
            "explanation": model_info.get("similarity_sentence"),
            "top_features": model_info.get("top_features"),
            "detailed_explanation": model_info.get("detailed_explanation"),
            #"feature_contributions": convert_value(model_info.get("feature_contributions")),
            "version": "v0.1"
        },
        "entity_explanations": build_entity_explanations(cluster_pairs),

        "golden_record": golden_record,
        "merge_decision": merge_decision,

        "pair_stats": {
            "total_pairs": len(cluster_pairs)
        }
    }


def extract_pair_info(df):
    records = []

    for _, row in df.iterrows():
        records.append({
            "entity_id_a": row["entity_id_a"],
            "entity_id_b": row["entity_id_b"],
            "prob": float(row["prob"]),
            "top_features": row.get("top_features"),
            "similarity_sentence": row.get("similarity_sentence"),
            #"feature_contributions": convert_value(row.get("feature_contributions"))
        })

    return records

def build_entity_explanations(cluster_pairs):
    explanations = {}
    if cluster_pairs.empty:
        return {}
    # stack both directions so every entity appears
    df = pd.concat([
        cluster_pairs.rename(columns={
            "entity_id_a": "entity_id",
            "entity_id_b": "other_entity"
        }),
        cluster_pairs.rename(columns={
            "entity_id_b": "entity_id",
            "entity_id_a": "other_entity"
        })
    ])

    # for each entity → pick strongest link
    idx = df.groupby("entity_id")["prob"].idxmax()
    best_links = df.loc[idx]

    best_links = df.loc[idx].sort_values("prob", ascending=False)

    for _, row in best_links.iterrows():
        explanations[row["entity_id"]] = {
            "connected_to": row["other_entity"],
            "prob": float(row["prob"]),
            "explanation": row.get("similarity_sentence"),
            "top_features": row.get("top_features"),
            #"feature_contributions": row.get("feature_contributions")
        }

    return explanations