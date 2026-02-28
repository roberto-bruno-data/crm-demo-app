def build_pair_label(row):
    return (
        row["nachname_1"] + ", "
        + row["vorname_1"]
        + " ↔ "
        + row["nachname_2"] + ", "
        + row["vorname_2"]
        + " | p=" + str(round(row["prob"], 2))
    )
