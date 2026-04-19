def attach_run_metadata(df, run_id, run_timestamp):
    return df.assign(
        run_id=run_id,
        run_timestamp=run_timestamp
    )

def ensure_entity_id_and_source(df):

    if "entity_id" not in df.columns:
        df["entity_id"] = range(1, len(df) + 1)

    if "source" not in df.columns:
        df["source"] = "CSV-Upload"

    return df