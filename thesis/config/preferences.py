from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "preferences.yaml"


def load_preferences():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_preferences(config):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f)