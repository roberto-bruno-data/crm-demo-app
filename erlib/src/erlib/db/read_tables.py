import pandas as pd
from sqlalchemy import text

def get_table_by_run_id(table_name, run_id, engine):
    query = f"SELECT * FROM {table_name} WHERE run_id = %s"
    return pd.read_sql(query, engine, params=(run_id,))

def get_harmonized_entities(run_id, engine):
    query = f"""
        SELECT
            entity_id,
            vorname,
            nachname,
            email,
            telefon,
            strasse,
            hausnr,
            plz,
            stadt,
            land
        FROM harmonized_entities
        WHERE run_id = %s
        """
    return pd.read_sql(query, engine, params=(run_id,))

def get_review_queue(run_id, engine):

    base_query = """
        SELECT rq.*, ec_a.cluster_id
        FROM vw_review_queue rq

        JOIN entity_clusters ec_a
            ON rq.entity_id_a = ec_a.entity_id
            AND rq.run_id = ec_a.run_id

        JOIN entity_clusters ec_b
            ON rq.entity_id_b = ec_b.entity_id
            AND rq.run_id = ec_b.run_id

        WHERE rq.run_id = :run_id
        AND ec_a.cluster_id = ec_b.cluster_id
    """

    return pd.read_sql(
        text(base_query),
        engine,
        params={"run_id": run_id}
    )

def get_record_counts(run_id: str, engine):
    query = text("""
        SELECT source, COUNT(*) as cnt
        FROM harmonized_entities
        WHERE run_id = :run_id
        GROUP BY source
        """)
    
    df = pd.read_sql(query, engine, params={"run_id": run_id})
    
    counts = dict(zip(df["source"], df["cnt"]))
    
    return {
        "salesforce": counts.get("salesforce", 0),
        "netsuite": counts.get("netsuite", 0),
        "total": sum(counts.values())
    }

def load_pairs_from_db(run_id: str, engine):
    query = """
        SELECT *
        FROM candidate_pairs
        WHERE run_id = %s
        """
    return pd.read_sql(query, engine, params=(run_id,))

def get_pair_features(run_id: str, engine):
    query = """
        SELECT *
        FROM pair_features
        WHERE run_id = %s
        """
    return pd.read_sql(query, engine, params=(run_id,))

def get_latest_run_id(engine):
    query = """
    SELECT run_id
    FROM pair_features
    ORDER BY run_id DESC
    LIMIT 1
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        return None

    return df["run_id"].iloc[0]
    

def get_resolved_cluster_ids(run_id: str, engine):
    query = text("""
        SELECT cluster_id
        FROM golden_records
        WHERE run_id = :run_id
    """)

    df = pd.read_sql(query, engine, params={"run_id": run_id})
    return df["cluster_id"].tolist()

def get_resolved_count(run_id: str, engine):
    query = text("""
        SELECT COUNT(*) as cnt
        FROM golden_records
        WHERE run_id = :run_id
    """)

    df = pd.read_sql(query, engine, params={"run_id": run_id})
    return int(df.iloc[0]["cnt"])

def get_golden_records(run_id: str, engine):
    query = text("""
        SELECT *
        FROM golden_records
        WHERE run_id = :run_id
        """)
    return pd.read_sql(query, engine, params={"run_id": run_id})

def get_audit_logs(run_id: str, engine):
    query = text("""
        SELECT cluster_id, audit, created_at
        FROM golden_records
        WHERE run_id = :run_id
        ORDER BY created_at DESC
    """)
    return pd.read_sql(query, engine, params={"run_id": run_id})

def load_pairs_with_prob(run_id: str, engine):
    query = text("""
        SELECT 
            c.entity_id_a,
            c.entity_id_b,
            p.prob
        FROM candidate_pairs c
        JOIN pair_features p 
            ON p.pair_id = c.pair_id 
            AND p.run_id = c.run_id
        WHERE c.run_id = :run_id
    """)
    return pd.read_sql(query, engine, params={"run_id": run_id})

def get_cluster_stats(run_id, engine):
    query = """
        SELECT cluster_id, COUNT(*) as size
        FROM entity_clusters
        WHERE run_id = %s
        GROUP BY cluster_id
    """
    df = pd.read_sql(query, engine, params=(run_id,))
    return df

def get_clusters(run_id, engine):
    query = """
        SELECT cluster_id, entity_id, cluster_size
        FROM entity_clusters
        WHERE run_id = %s
    """
    return pd.read_sql(query, engine, params=(run_id,))

def get_resolved_clusters(run_id, engine):
    query = text("""
            SELECT DISTINCT cluster_id
            FROM golden_records
            WHERE run_id = :run_id
        """)
    
    return pd.read_sql(query, engine, params={"run_id": run_id})["cluster_id"].tolist()

def get_cluster_status(run_id, engine):
    query = """
        SELECT *
        FROM cluster_status
        WHERE run_id = %s
        GROUP BY run_id, cluster_id
    """
    df = pd.read_sql(query, engine, params=(run_id,))
    return df

def get_all_data(run_id, engine):
    return {
        "review_df": get_review_queue(run_id, engine),
        "counts": get_record_counts(run_id, engine),
        "pair_features": get_pair_features(run_id, engine),
        "candidates": load_pairs_from_db(run_id, engine),
    }
