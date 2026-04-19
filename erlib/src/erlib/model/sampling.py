import pandas as pd

# Downsampling
#_________________________________________________________________________

def balance(df, multiple=2, SEED = 42):
    """
    Balanciert einen unbalancierten Trainingsdatensatz.

    Ziel:
    - Es wird ein Verhältnis von 1 : multiple (Positiv : Negativ) hergestellt.
    - Damit wird verhindert, dass das Modell zu stark auf die Mehrheitsklasse fokussiert.

    Parameter:
    - df: DataFrame mit Spalte 'is_duplicate_pair' (1 = positiv, 0 = negativ)
    - multiple: gewünschter Negativ-Faktor (z. B. 2 → doppelt so viele negative wie positive)

    Rückgabe:
    - DataFrame mit ausbalancierten und zufällig neu gemischten Daten
    """
    # Positive und negative Paare extrahieren
    pos = df[df["is_duplicate_pair"] == 1]
    neg = df[df["is_duplicate_pair"] == 0]

    # Maximal n_neg erlauben (z. B. doppelt so viele wie Positivfälle)
    n_neg = min(len(neg), len(pos) * multiple)

    # Zufällige Stichprobe der Negativpaare ziehen
    neg_sample = neg.sample(n=n_neg, random_state=SEED)

    # Kombinieren und Reihenfolge mischen
    balanced_df = pd.concat([pos, neg_sample]).sample(frac=1, random_state=SEED).reset_index(drop=True)

    return balanced_df
