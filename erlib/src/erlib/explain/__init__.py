from erlib.explain import xAI_production
from .xAI_production import DEFAULT_FEATURE_GROUPS
from erlib.explain.scoring import score_records, add_probability_explanations
from erlib.explain.feature_level import add_top_features
from erlib.explain.similarity_sentence import (
    build_similarity_sentence,
    aggregate_group_shap,
    build_detailed_explanation
)
from erlib.explain.explain_results import run_explanation_pipeline

__all__ = [
    "xAI_production",
    "score_records",
    "add_probability_explanations",
    "add_top_features",
    "build_similarity_sentence",
    "aggregate_group_shap",
    "build_detailed_explanation",
    "run_explanation_pipeline",
    "DEFAULT_FEATURE_GROUPS"
]