import pandas as pd

def extract_system_record(row, suffix, rename_map):
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]

    cols = [c for c in row.index if c.endswith(suffix)]

    data = {
        rename_map.get(c.replace(suffix, ""), c.replace(suffix, "")): row[c]
        for c in cols
    }

    return pd.DataFrame([data])
