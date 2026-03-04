import pandas as pd
from pathlib import Path
import yaml

def load_config():
    base_path = Path(__file__).resolve().parents[1]
    config_path = base_path / "ui_components" / "preferences.yaml"

    with open(config_path, "r") as f:
        return yaml.safe_load(f)
    
def extract_system_record(row, suffix, rename_map):
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]

    cols = [c for c in row.index if c.endswith(suffix)]

    data = {
        rename_map.get(c.replace(suffix, ""), c.replace(suffix, "")): row[c]
        for c in cols
    }

    return pd.DataFrame([data])

def get_default_source(attr, settings):
    return settings.get(attr)