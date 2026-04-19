import pandas as pd

def has_relevant_difference(row, fields):
    for field in fields:
        a, b = row[f"{field}_1"], row[f"{field}_2"]

        if pd.isna(a) and pd.isna(b):
            continue
        if a != b:
            return True
    return False

def filter_identical_pairs(df, fields):
    mask = df.apply(has_relevant_difference, axis=1, fields=fields)
    return df[mask], df[~mask]

def filter_side_bar(df, st):
    st.sidebar.header("Filtermodus")
    
    filtered_df = df.copy()

    CATEGORY_ORDER = [
        "Sichere Dublette",
        "Wahrscheinliche Dublette",
        "Unklare Dublette"
    ]
    available_categories = [
        c for c in CATEGORY_ORDER
        if c in df["match_category"].dropna().unique()
    ]

    filter_mode = st.sidebar.radio(
        "Wie möchtest du filtern?",
        [
            "Explorativ (keine Filterung)",
            "Governance-Modus (Kategorien)",
            "Analyse-Modus (Wahrscheinlichkeit)"
        ],
        index=0
    )

    if filter_mode == "Explorativ (keine Filterung)":
        st.sidebar.caption(
            "Alle Dublettenpaare werden angezeigt. "
            "Weitere Filter sind deaktiviert."
        )

    elif filter_mode == "Governance-Modus (Kategorien)":
        category = st.sidebar.selectbox(
            "Match-Kategorie",
            available_categories
        )
        filtered_df = filtered_df[filtered_df["match_category"] == category]

        st.sidebar.caption(
            "Governance-Modus zeigt entscheidungsrelevante "
            "Fälle basierend auf fachlichen Kategorien."
        )

    elif filter_mode == "Analyse-Modus (Wahrscheinlichkeit)":
        min_prob, max_prob = st.sidebar.slider(
            "Wahrscheinlichkeitsbereich",
            min_value=0.0,
            max_value=1.0,
            value=(0.5, 0.99),
            step=0.05
        )
        filtered_df = filtered_df[
            (filtered_df["prob"] >= min_prob) &
            (filtered_df["prob"] <= max_prob)
        ]

    st.sidebar.caption(
        "Hinweis: Fälle mit 100 % Übereinstimmung "
        "werden nicht angezeigt, da sie keine manuelle Entscheidung erfordern."
    )
    
    if filter_mode == "Explorativ (keine Filterung)":
        st.caption(
            f"Explorativer Modus · "
            f"Alle Paare sichtbar · "
            f"{len(filtered_df)} von {len(df)} Paaren"
        )

    elif filter_mode == "Governance-Modus (Kategorien)":
        st.caption(
            f"Governance-Modus · "
            f"Kategorie: {category} · "
            f"{len(filtered_df)} von {len(df)} Paaren"
        )

    elif filter_mode == "Analyse-Modus (Wahrscheinlichkeit)":
        st.caption(
            f"Analyse-Modus · "
            f"Wahrscheinlichkeit {min_prob:.0%}–{max_prob:.0%} · "
            f"{len(filtered_df)} von {len(df)} Paaren"
        )

    st.caption(
        f"Explorativer Modus · "
        f"Ø Wahrscheinlichkeit: {filtered_df['prob'].mean():.2f} · "
        f"{len(filtered_df)} Paare"
    )

    return filtered_df