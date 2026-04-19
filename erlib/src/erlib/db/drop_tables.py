from sqlalchemy import text

def reset_matching_tables(engine):
    drop_sql = """
    DROP TABLE IF EXISTS pair_features CASCADE;
    DROP TABLE IF EXISTS candidate_pairs;
    DROP TABLE IF EXISTS harmonized_entities;
    DROP TABLE IF EXISTS entity_clusters;
    DROP TABLE IF EXISTS golden_records;
    """

    with engine.begin() as conn:
        conn.execute(text(drop_sql))