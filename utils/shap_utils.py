import pandas as pd
import numpy as np

def normalize_shap_output(shap_values_raw):
    if isinstance(shap_values_raw, list):
        return shap_values_raw[1]
    if isinstance(shap_values_raw, np.ndarray) and shap_values_raw.ndim == 3:
        return shap_values_raw[:, :, 1]
    return shap_values_raw

def similarity_to_text(value, is_binary=False):
    if pd.isna(value):
        return None

    if is_binary:
        return "identisch" if value == 1 else None

    if value >= 0.98:
        return "identisch"
    elif value >= 0.85:
        return "sehr ähnlich"
    elif value >= 0.5:
        return "leicht ähnlich"
    else:
        return None
