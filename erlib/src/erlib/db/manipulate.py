import logging

def write_table(df, table_name, engine, if_exists="append"):
    try:
        logging.info(f"Writing {len(df)} rows to '{table_name}'")

        df.to_sql(
            table_name,
            engine,
            if_exists=if_exists,
            index=False,
            chunksize=1000
        )

    except Exception as e:
        logging.error(f"Failed to write to {table_name}: {e}")
        raise

def enrich_pairs_with_entities(pairs, entities):
    pairs = pairs.merge(
        entities,
        left_on="entity_id_a",
        right_on="entity_id",
        suffixes=("", "_1")
    ).drop(columns=["entity_id"])

    pairs = pairs.merge(
        entities,
        left_on="entity_id_b",
        right_on="entity_id",
        suffixes=("_1", "_2")
    ).drop(columns=["entity_id"])

    return pairs.reset_index(drop=True)