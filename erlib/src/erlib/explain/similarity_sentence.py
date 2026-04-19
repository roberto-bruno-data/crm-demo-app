import pandas as pd
import numpy as np

from erlib.utils.shap_utils import similarity_to_text

def build_similarity_sentence(
    row_data,
    feature_groups,
    prob=None,
    ident_ratio_threshold=0.8,
):
    """
    Baut eine menschenlesbare Similarity-Erklärung auf Gruppenebene.

    Garantien:
    - gibt NIE None / "" zurück
    - nennt immer konkrete Gruppen
    - starke Aussagen ("Alle Werte identisch") nur bei hohem prob
    """

    SUMMARY_LABEL = "Alle Vergleichsattribute"

    group_results = {}

    # --- 1. Pro Gruppe immer einen Text bestimmen ---
    for label, feats in feature_groups.items():
        sims = [row_data.get(f, np.nan) for f in feats]
        valid = [s for s in sims if not pd.isna(s)]

        if not valid:
            continue

        max_sim = max(valid)
        is_binary = any(f.endswith("_eq") for f in feats)

        sim_text = similarity_to_text(max_sim, is_binary=is_binary)

        # Fallback: niemals leer
        if sim_text is None:
            sim_text = "unterschiedlich"

        group_results[label] = sim_text

    if not group_results:
        return "Keine relevanten Vergleichsmerkmale"

    # --- 2. Aggregationen ---
    identical = [g for g, t in group_results.items() if t == "identisch"]
    different = [g for g in group_results if g not in identical]

    n_diff = len(different)

    # --- 3. Sprachliche Verdichtung ---
    MAX_DIFF_FOR_SUMMARY = 3
    # MAX_SAME_FOR_REVERSE = 2

    if n_diff == 0 and len(group_results) >= 3:
        return f"{SUMMARY_LABEL} identisch"

    if 0 < n_diff <= MAX_DIFF_FOR_SUMMARY:
        return (
            f"{SUMMARY_LABEL} identisch außer "
            + " und "
            .join(different)
        )

    # --- 3b. Reverse Summary: fast alles unterschiedlich ---
    identical = [
        g for g, t in group_results.items()
        if t == "identisch"
    ]

    if n_diff > MAX_DIFF_FOR_SUMMARY and len(identical) > 0:
        return (
            f"{SUMMARY_LABEL} unterschiedlich außer "
            + " und ".join(identical)
        )
    
    if n_diff == len(group_results):
        return f"{SUMMARY_LABEL} unterschiedlich"

    # --- 4. Normale, erklärende Aufzählung ---
    parts = []
    for group, text in group_results.items():
        if text == "unterschiedlich":
            parts.append(f"{group} unterschiedlich")
        else:
            parts.append(f"{text}e {group}")

    return ", ".join(parts)

FEATURE_TO_ATTR = {
    "sim_vorname_": "Vorname",
    "sim_nachname_": "Nachname",
    "sim_strasse_": "Straße",
    "sim_plz_": "PLZ",
    "sim_stadt_": "Stadt",
    "sim_land_": "Land",
    "sim_email_": "E-Mail",
    "sim_telefon_": "Telefon",
}
    
def aggregate_shap_by_attribute(shap_row, feature_cols):
    attr_scores = {}

    for f, val in zip(feature_cols, shap_row):
        for prefix, attr in FEATURE_TO_ATTR.items():
            if f.startswith(prefix):
                attr_scores[attr] = attr_scores.get(attr, 0) + val

    positives = [a for a, v in attr_scores.items() if v > 0]
    negatives = [a for a, v in attr_scores.items() if v < 0]

    return positives, negatives

def build_detailed_explanation(
    match_category,
    row,
    shap_row,
    feature_groups,
    feature_cols,
    shap_q50,
    shap_q80,
):
    
    positive_attrs, negative_attrs = split_shap_effects(
        shap_row, feature_cols
    )

    low_similarity_attrs = derive_low_similarity_attrs(row, feature_groups)

    rationale = build_model_rationale(
        match_category=match_category,
        positive_attrs=positive_attrs,
    )

    negative_text = build_negative_rationale(
        low_similarity_attrs=low_similarity_attrs,
        negative_but_identical_attrs = [
            a for a in negative_attrs
            if a not in low_similarity_attrs
            and a in feature_groups
        ],
    )

    evidence = build_attribute_evidence(
        match_category=match_category,
        feature_cols=feature_cols,
        feature_groups=feature_groups,
        row=row,
        shap_row=shap_row,
        shap_q50=shap_q50,
        shap_q80=shap_q80,
        )


    governance = (
        "Die Einschätzung stellt eine modellbasierte Empfehlung dar "
        "und ersetzt keine fachliche Entscheidung."
    )

    parts = [
        "**Modellbasierte Einschätzung**\n\n" + rationale
    ]

    if negative_text:
        parts.append(negative_text)

    parts.append("**Attributbasierte Evidenz**\n\n" + evidence)
    parts.append("**Governance-Hinweis**\n\n" + governance)

    return "\n\n".join(parts)

def aggregate_group_shap(shap_row, feature_groups, feature_cols):
    """
    shap_row: np.ndarray (1D)
    feature_cols: List[str]
    """

    shap_map = dict(zip(feature_cols, shap_row))

    group_shap = {}
    for group, feats in feature_groups.items():
        group_shap[group] = sum(
            abs(shap_map.get(f, 0.0)) for f in feats
        )

    return group_shap


def classify_shap_strength(value, q50, q80):
    if value >= q80:
        return "sehr hoher Einfluss"
    if value >= q50:
        return "merklicher Einfluss"
    return "geringer Einfluss"

def explain_group(group, sim_text, shap_strength):
    if sim_text == "identisch":
        return f"{group}: vollständig identisch ({shap_strength})"

    if "ähnlich" in sim_text:
        return f"{group}: {sim_text} ({shap_strength})"

    return f"{group}: unterschiedlich ({shap_strength})"

def build_model_rationale(
    match_category: str,
    positive_attrs: list[str],
):
    parts = [
        f"Das Modell stuft dieses Datensatzpaar als **{match_category}** ein."
    ]

    if positive_attrs:
        parts.append(
            "Die Entscheidung wird insbesondere durch Übereinstimmungen bei "
            + ", ".join(sorted(set(positive_attrs)))
            + " gestützt, die einen positiven Einfluss auf die Modellbewertung haben."
        )

    return "\n\n".join(parts)


def build_attribute_evidence(
    match_category,
    feature_cols,
    feature_groups,
    row,
    shap_row,
    shap_q50,
    shap_q80,
):
    # --- Row robust in dict umwandeln (itertuples -> namedtuple) ---
    if hasattr(row, "_asdict"):          # namedtuple von itertuples()
        row = row._asdict()
    elif isinstance(row, pd.Series):     # Series
        row = row.to_dict()
    elif not isinstance(row, dict):      # irgendein anderes Objekt
        row = dict(row)

    confirming = []
    strong = []
    deviations = []

    group_shap = aggregate_group_shap(shap_row, feature_groups, feature_cols)

    for group, feats in feature_groups.items():
        # Wichtig: nicht "if f in row" (das bricht bei namedtuple/tuple-Logik)
        sims = [row.get(f, None) for f in feats]
        sims = [s for s in sims if s is not None and not pd.isna(s)]

        if not sims:
            continue

        max_sim = max(sims)
        is_binary = any(f.endswith("_eq") for f in feats)
        sim_text = similarity_to_text(max_sim, is_binary=is_binary) or "unterschiedlich"

        shap_strength = classify_shap_strength(
            group_shap.get(group, 0.0),
            shap_q50,
            shap_q80
        )

        sentence = explain_group(group, sim_text, shap_strength)

        # Routing (erst Similarity, dann Einfluss)
        if sim_text == "identisch":
            confirming.append(f"{group}: identisch")
        elif shap_strength in ["sehr hoher Einfluss", "merklicher Einfluss"]:
            strong.append(sentence)
        else:
            deviations.append(sentence)

    parts = []

    if strong:
        parts.append("**Stark entscheidungsrelevant:**\n- " + "\n- ".join(strong))

    if confirming and match_category != "Unklare Dublette":
        parts.append("**Bestätigende Übereinstimmungen:**\n- " + "\n- ".join(confirming))

    if deviations:
        parts.append("**Abweichungen:**\n- " + "\n- ".join(deviations))

    # Wenn alles identisch ist, soll es nie leer bleiben
    if not parts and confirming:
        return "**Konsistente Übereinstimmungen:**\n- " + "\n- ".join(confirming)

    # Letzter Fallback (wirklich keine Daten)
    if not parts:
        return "Keine ausreichenden Vergleichsdaten zur Evidenzbildung verfügbar."

    return "\n\n".join(parts)

def split_shap_effects(shap_row, feature_cols):
    effects = {}

    for f, val in zip(feature_cols, shap_row):
        for prefix, attr in FEATURE_TO_ATTR.items():
            if f.startswith(prefix):
                effects.setdefault(attr, 0.0)
                effects[attr] += val

    positive = [a for a, v in effects.items() if v > 0]
    negative = [a for a, v in effects.items() if v < 0]

    return positive, negative

def build_negative_rationale(
    low_similarity_attrs: list[str],
    negative_but_identical_attrs: list[str],
) -> str:
    """
    Baut den negativen/dämpfenden Teil der Modellrationale
    sprachlich konsistent zu Similarity + SHAP.
    """

    parts = []

    # --- Echte Abweichungen (Similarity niedrig) ---
    if low_similarity_attrs:
        parts.append(
            "Abweichungen bei "
            + ", ".join(sorted(set(low_similarity_attrs)))
            + " wirken dämpfend auf die Modellbewertung."
        )

    # --- Formal identisch, aber geringer / negativer Einfluss ---
    if negative_but_identical_attrs:
        parts.append(
            "Weitere Merkmale wie "
            + ", ".join(sorted(set(negative_but_identical_attrs)))
            + " sind zwar formal identisch, "
            "tragen jedoch nur begrenzt zur Entscheidungsfindung bei."
        )

    return "\n\n".join(parts)

def derive_low_similarity_attrs(row, feature_groups, threshold=0.8):
    if hasattr(row, "_asdict"):
        row = row._asdict()
    elif isinstance(row, pd.Series):
        row = row.to_dict()

    low = []

    for group, feats in feature_groups.items():
        sims = [row.get(f) for f in feats if f in row]
        sims = [s for s in sims if s is not None and not pd.isna(s)]

        if sims and max(sims) < threshold:
            low.append(group)

    return low
