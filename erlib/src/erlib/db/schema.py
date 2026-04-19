from sqlalchemy import text
from erlib.utils.features_config import get_feature_cols

def initialize_database(engine):

    feature_cols = get_feature_cols()
    feature_sql = ",\n        ".join([f"{col} FLOAT" for col in feature_cols])

    create_harmonized_entities = """
    CREATE TABLE IF NOT EXISTS harmonized_entities (
        entity_id INTEGER PRIMARY KEY,
        run_id TEXT,
        source TEXT,
        vorname TEXT,
        nachname TEXT,
        email TEXT,
        telefon TEXT,
        strasse TEXT,
        hausnr TEXT,
        plz TEXT,
        stadt TEXT,
        land TEXT,
        run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_candidate_pairs = """
    CREATE TABLE IF NOT EXISTS candidate_pairs (
        pair_id SERIAL PRIMARY KEY,
        run_id TEXT,
        entity_id_a INTEGER,
        entity_id_b INTEGER,
        block_key TEXT,
        run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_pair_features = f"""
    CREATE TABLE IF NOT EXISTS pair_features (
        pair_id INTEGER,
        run_id TEXT NOT NULL,
        entity_id_a INTEGER,
        entity_id_b INTEGER, 

        {feature_sql},

        prob FLOAT,
        match_category TEXT,
        top_features TEXT,
        prob_explanation TEXT,
        nuanced_explanation TEXT,
        similarity_sentence TEXT,
        detailed_explanation TEXT,
        feature_contributions JSONB,

        run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        PRIMARY KEY (run_id, pair_id)
    );
    """

    create_review_queue = """
    CREATE VIEW vw_review_queue AS
    SELECT
    pf.pair_id,
    pf.run_id,
    pf.prob,
    pf.match_category,
    pf.top_features,
    pf.entity_id_a,
    pf.entity_id_b, 

    -- entity A
    e1.vorname AS vorname_1,
    e1.nachname AS nachname_1,
    e1.email AS email_1,
    e1.telefon AS telefon_1,
    e1.strasse AS strasse_1,
    e1.hausnr AS hausnr_1,
    e1.plz AS plz_1,
    e1.stadt AS stadt_1,
    e1.land AS land_1,

    -- entity B
    e2.vorname AS vorname_2,
    e2.nachname AS nachname_2,
    e2.email AS email_2,
    e2.telefon AS telefon_2,
    e2.strasse AS strasse_2,
    e2.hausnr AS hausnr_2,
    e2.plz AS plz_2,
    e2.stadt AS stadt_2,
    e2.land AS land_2,

    -- explanations
    pf.similarity_sentence,
    pf.detailed_explanation,
    pf.feature_contributions

    FROM pair_features pf
    JOIN candidate_pairs cp 
        ON pf.pair_id = cp.pair_id AND pf.run_id = cp.run_id
    JOIN harmonized_entities e1 
        ON cp.entity_id_a = e1.entity_id AND cp.run_id = e1.run_id
    JOIN harmonized_entities e2 
        ON cp.entity_id_b = e2.entity_id AND cp.run_id = e2.run_id;

    """

    golden_records = """
    CREATE TABLE golden_records (
    id SERIAL PRIMARY KEY,
    run_id TEXT,
    cluster_id INTEGER,
    num_entities INTEGER,
    golden_record JSONB,
    audit JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    entity_clusters = """
    CREATE TABLE entity_clusters (
        PRIMARY KEY (run_id, entity_id),
        run_id TEXT,
        entity_id INTEGER,
        cluster_id INTEGER,
        cluster_size INTEGER
    );
    """

    with engine.begin() as conn:
        conn.execute(text(create_harmonized_entities))
        conn.execute(text(create_candidate_pairs))
        conn.execute(text(create_pair_features))
        conn.execute(text(entity_clusters))
        conn.execute(text(create_review_queue))
        conn.execute(text(golden_records))