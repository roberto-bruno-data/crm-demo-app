# Standard Library
import logging
from datetime import datetime, timezone
import uuid

# Third Party
from pathlib import Path
import yaml

# Internal / Project
from thesis.data_generation.synth import generate_synthetic_crm_sources_new
from thesis.crm.harmonize_crm_schemas import harmonise
from thesis.logic.clustering import build_entity_clusters
from thesis.logic.model import load_er_model

from erlib.pairing import build_candidate_pairs
from erlib.features import calculate_features_all
from erlib.explain import run_explanation_pipeline, DEFAULT_FEATURE_GROUPS
from erlib.export import prepare_for_tableau
from erlib.db import engine, initialize_database, reset_matching_tables, write_table, attach_run_metadata, get_table_by_run_id, get_harmonized_entities, enrich_pairs_with_entities, load_pairs_with_prob, ensure_entity_id_and_source

def generate_or_load_data(input_df, data_cfg):
    if input_df is None:
        # DEMO MODE
        logging.info("Generating synthetic CRM data...")
        salesforce_df, netsuite_df = generate_synthetic_crm_sources_new(**data_cfg)
        crm_harmonized = harmonise(salesforce_df, netsuite_df)
    else:
        crm_harmonized = input_df.copy()

        # 👇 wichtig
        logging.info("Upload Mode: expecting harmonized schema")

        crm_harmonized = ensure_entity_id_and_source(crm_harmonized)
        
    # --- Data Generation ---
    
    crm_harmonized = crm_harmonized.reset_index(drop=True)
    logging.info(f"[DATA] Harmonized {len(crm_harmonized)} records")

    run_id = uuid.uuid4().hex
    logging.info(f"Run ID: {run_id}")
    run_timestamp = datetime.now(timezone.utc)
    logging.info(f"Run Timestamp (UTC): {run_timestamp}")

    return run_id, run_timestamp, crm_harmonized

def create_candidate_pairs(df, pairing_cfg, run_id, timestamp, engine):

    crm_harmonized_enriched = attach_run_metadata(
        df
        .drop(columns=["cluster_id", "is_duplicated"], errors="ignore"),
        run_id,
        timestamp
    )

    write_table(
        crm_harmonized_enriched,
        "harmonized_entities",
        engine
    )

    crm_pairs = attach_run_metadata(
        build_candidate_pairs(
            crm_harmonized_enriched,
            **pairing_cfg
        ),
        run_id,
        timestamp
    )

    write_table(
        crm_pairs,
        "candidate_pairs",
        engine
    )

    pairs = get_table_by_run_id("candidate_pairs", run_id, engine)
    entities = get_harmonized_entities(run_id, engine)
    logging.info(f"Loaded {len(pairs)} candidate pairs for run_id={run_id}")
    logging.info(f"Loaded {len(entities)} entities for run_id={run_id}")

    pairs_enriched = enrich_pairs_with_entities(pairs, entities)

    return pairs_enriched

def run_feature_engineering(pairs_enriched, run_id, timestamp):
    crm_featured = calculate_features_all(pairs_enriched)

    crm_featured = attach_run_metadata(crm_featured, run_id, timestamp)

    return crm_featured

def run_model_and_explain(df, run_id, engine):
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    model_path = PROJECT_ROOT / "models" / "er_model_v1.joblib"
    
    model, feature_cols = load_er_model(model_path)
    
    logging.info(f"Generated {len(feature_cols)} features")

    crm_featured_explained = run_explanation_pipeline(df, model, feature_cols, DEFAULT_FEATURE_GROUPS)

    # Persistieren in DB
    base_cols = ["pair_id", "run_id", "entity_id_a", "entity_id_b"]
    output_cols = [
        "prob",
        "match_category",
        "top_features", 
        "prob_explanation",
        "nuanced_explanation",
        "similarity_sentence",
        "detailed_explanation",
        "feature_contributions"
    ]

    crm_featured_explained = crm_featured_explained[
        base_cols + feature_cols + output_cols
    ]

    crm_featured_explained = crm_featured_explained.dropna(subset=["prob"])
    write_table(crm_featured_explained, "pair_features", engine)

    entities_with_prob = load_pairs_with_prob(run_id, engine)
    
    return crm_featured_explained, entities_with_prob

def cluster_entities(entities_with_prob, run_id, engine):
    cluster_df = build_entity_clusters(entities_with_prob, threshold=0.5)

    cluster_df["run_id"] = run_id

    cluster_df.to_sql("entity_clusters", engine, if_exists="append", index=False)


def run_pipeline(engine, input_df=None, reset=False):

    # --- Setup ---
    if reset:
        reset_matching_tables(engine)
        initialize_database(engine)

    CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
        data_cfg = config["data_generation"]
        pairing_cfg = config["pairing"]
    
    run_id, run_timestamp, crm_harmonized = generate_or_load_data(input_df, data_cfg)
 
    pairs_enriched = create_candidate_pairs(crm_harmonized, pairing_cfg, run_id, run_timestamp, engine)

    crm_featured = run_feature_engineering(pairs_enriched, run_id, run_timestamp)

    crm_featured_explained, entities_with_prob = run_model_and_explain(crm_featured, run_id, engine)

    cluster_entities(entities_with_prob, run_id, engine)

    # Persistieren als CSV
    crm_feat_for_tableau = prepare_for_tableau(crm_featured_explained)

    BASE_DIR  = Path(__file__).resolve().parents[1]
    OUTPUT_PATH = BASE_DIR / "data" / "results" / "crm_results_for_tableau_final.csv"

    crm_feat_for_tableau.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    logging.info("Pipeline completed successfully")

    return run_id

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    run_pipeline(engine, reset=True)