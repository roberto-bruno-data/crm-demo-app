import joblib
import logging
from pathlib import Path

def load_er_model(model_path: str | Path):
    logging.info(f"Loading model from {model_path}")

    bundle = joblib.load(model_path)

    return bundle["model"], bundle["feature_cols"]