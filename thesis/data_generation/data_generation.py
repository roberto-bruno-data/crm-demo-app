import random
import pandas as pd
import numpy as np
import re
from faker import Faker

# Datengenerierung
#_________________________________________________________________________
def random_land(rng):
    """
    Gibt ein zufälliges Land zurück.
    
    Mit 95 % Wahrscheinlichkeit wird eine deutsche Variante ausgegeben,
    um reale Fehlerquellen wie unterschiedliche Schreibweisen oder Kürzel zu simulieren.
    Die restlichen 5 % entfallen auf Nachbarländer als bewusst nicht-deutsche Werte.
    """
    if rng.random() < 0.95:
        return rng.choice(["Deutschland", "BRD", "Germany", "Deutchland", "D"])
    return rng.choice(["Österreich", "Schweiz", "Frankreich", "Niederlande", "Polen"])
    
def generate(n=1000, custom_columns=None, SEED = 42):
    """
    Generiert synthetische Personendaten mit realistischer Struktur.

    - Nutzt das Faker-Paket (de_DE) für typische Namens- und Adressdaten.
    - Jeder Datensatz erhält eine eindeutige cluster_id (z. B. für spätere Duplikaterzeugung).
    - Das Länderkürzel wird bewusst mit Mehrdeutigkeiten erzeugt (z. B. "BRD", "D", etc.).

    Parameter:
    --------
    n : int
        Anzahl der zu erzeugenden Datensätze.

    Rückgabe:
   ------
    df : pd.DataFrame
        DataFrame mit n synthetischen Personen- bzw. Adressdatensätzen.
    """
    # Initialisiere Faker mit deutschem Lokalisierungsprofil
    faker = Faker("de_DE")
    faker.seed_instance(SEED)
    rng = random.Random(SEED)

    if custom_columns is None:
        column_names=["vorname", "nachname", "email", "telefon", "strasse", "hausnr", "plz", "stadt", "land"]
    else:
        column_names = custom_columns

    rows = []

    for x in range(n):
        row = {column_names[0]: faker.first_name(), 
               column_names[1]: faker.last_name(),
               column_names[2]: faker.email(),
               column_names[3]: faker.phone_number(),
               column_names[4]: faker.street_name(),
               column_names[5]: faker.building_number(),
               column_names[6]: faker.postcode(),
               column_names[7]: faker.city(),
               column_names[8]: random_land(rng),             # Eigene Funktion zur Generierung des Landes
               "cluster_id": x                             # Eindeutige ID für spätere Duplikaterkennung
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    return df

# Datenduplizierung
#_________________________________________________________________________

def duplicate(
    base_data: pd.DataFrame,
    mean=0.15, variance=0.05,          # Anteil der Duplikate
    cluster_mean=2.2, cluster_sd=0.7,  # Ø Clustergröße (inkl. Original)
    max_cluster_size=6                 # Maximale Clustergröße
):
    """
    Erzeugt synthetische Duplikate durch Kopieren bestehender Datensätze.

    Ziel ist die Simulation realistischer Dublettengruppen (Paare, Triaden etc.), wie sie typischerweise in CRM-Systemen vorkommen.

    Parameter:
    -----------
    base_data : pd.DataFrame
        Ursprünglicher Datensatz ohne Duplikate.
    mean : float
        Erwarteter Anteil der Originale, die dupliziert werden sollen (z.B. 0.15 = 15 %).
    variance : float
        Streuung um den Mittelwert für den zu duplizierenden Anteil.
    cluster_mean : float
        Erwartete Größe eines Duplikat-Clusters (inkl. Original).
    cluster_sd : float
        Streuung der Clustergröße.
    max_cluster_size : int
        Obergrenze für die Clustergröße zur Vermeidung extremer Ausreißer.

    Rückgabe:
    ---------
    df : pd.DataFrame
        Neuer DataFrame mit zusätzlichen Duplikaten und einer booleschen Spalte `is_duplicated`.
    """

    # Kopie der Eingabedaten
    df = base_data.copy()
    n = len(df)

    # 1. Schritt: Anzahl der Originale, die dupliziert werden sollen
    factor = np.random.normal(mean, variance)
    amount_to_duplicate = int(round(n * factor))
    amount_to_duplicate = max(1, min(amount_to_duplicate, n))  # mind. 1, max. n

    chosen_ids = np.random.choice(n, size=amount_to_duplicate, replace=False)

    all_dupes = []

    for idx in chosen_ids:
        # 2. Schritt: Clustergröße normalverteilt wählen
        cluster_size = int(round(np.random.normal(cluster_mean, cluster_sd)))
        cluster_size = max(2, min(cluster_size, max_cluster_size))

        # Das Original bleibt, cluster_size-1 Kopien werden hinzugefügt
        for _ in range(cluster_size - 1):
            new_row = df.iloc[idx].copy()
            all_dupes.append(new_row)

    # Neue Duplikate anhängen und neu indexieren
    df = pd.concat([df, pd.DataFrame(all_dupes)], ignore_index=True)

    print("cluster_id dtype:", df["cluster_id"].dtype)
    print("duplicated result dtype:", df["cluster_id"].duplicated(keep=False).dtype)

    # Markieren, welche Cluster mehrfach vorkommen
    df["is_duplicated"] = df["cluster_id"].duplicated(keep=False)

    return df

# Datenverzerrung
#_________________________________________________________________________

# 1. Funktion: Ersetzt deutsche Umlaute durch Umschreibungen
def _replace_umlauts(s: str) -> str:
    UMAP = {"ä": "ae", "ö": "oe", "ü": "ue",
            "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
    return "".join(UMAP.get(c, c) for c in s)

# 2. Funktion: Zufällige Groß-/Kleinschreibung
def _random_case(s: str) -> str:
    return s.lower() if random.random() < 0.5 else s.upper()

# 3. Funktion: Ein zufälliger Tippfehler
def _random_typo(s: str) -> str:
    if not s:
        return s
    actions = ["insert", "delete", "replace"]
    act = random.choice(actions)
    pos = random.randrange(len(s))
    if act == "insert":
        return s[:pos] + random.choice("abcdefghijklmnopqrstuvwxyz") + s[pos:]
    elif act == "delete" and len(s) > 1:
        return s[:pos] + s[pos+1:]
    elif act == "replace":
        return s[:pos] + random.choice("abcdefghijklmnopqrstuvwxyz") + s[pos+1:]
    return s

# 4. Funktion: Spezifisch für Straßennamen (mit Domainwissen)
def _distort_street(s: str) -> str:
    if not s:
        return s
    if random.random() < 0.1:
        return ""  # vollständig leer
    s = s.lower() if random.random() < 0.5 else s.upper()
    s = re.sub(r"straße", "str.", s, flags=re.IGNORECASE)
    s = re.sub(r"strasse", "str.", s, flags=re.IGNORECASE)
    if random.random() < 0.3:
        s = s.replace("-", "")
    if len(s) > 2 and random.random() < 0.4:
        i = random.randrange(len(s))
        s = s[:i] + random.choice("abcdefghijklmnopqrstuvwxyz") + s[i+1:]
    if len(s) > 3 and random.random() < 0.3:
        i = random.randrange(len(s))
        s = s[:i] + s[i+1:]
    if len(s) > 3 and random.random() < 0.2:
        pos = random.randint(1, len(s)-1)
        s = s[:pos] + " " + s[pos:]
    return s

# 5. Funktion: Manchmal einfach löschen (für fehlende Werte)
def _drop_value(s: str) -> str:
    return "" if random.random() < 0.15 else s

# 6. Funktion: PLZ verzerren durch Ziffernänderung
def _distort_plz(plz: str) -> str:
    if not plz or not plz.isdigit():
        return plz
    plz_chars = list(plz)
    if random.random() < 0.3:
        idx = random.randrange(len(plz))
        plz_chars[idx] = random.choice("0123456789")
    if random.random() < 0.1 and len(plz) > 1:
        plz_chars.pop(random.randrange(len(plz)))
    return "".join(plz)

# 7. Funktion: Telefonnummern umfassend stören durch simulierte Tippfehler, verschiedene Vorwahlen etc.
def _distort_phone(phone: str) -> str:
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if digits and random.random() < 0.4:
        i = random.randrange(len(digits))
        digits = digits[:i] + random.choice("0123456789") + digits[i+1:]
    if digits and random.random() < 0.3:
        if random.random() < 0.5 and len(digits) > 2:
            idx = random.randrange(len(digits))
            digits = digits[:idx] + digits[idx+1:]
        else:
            idx = random.randrange(len(digits))
            digits = digits[:idx] + random.choice("0123456789") + digits[idx:]
    if random.random() < 0.4:
        digits = random.choice(["0049", "+49", "0", "+43", "0043"]) + digits.lstrip("0")
    if random.random() < 0.2:
        return ""
    return digits

# 8. Funktion: E-Mail-Adressen manipulieren
def _distort_email(mail):
    if not mail or "@" not in mail:
        return mail
    name, dom = mail.split("@", 1)
    if random.random() < 0.3 and len(name) > 1:
        i = random.randrange(len(name))
        name = name[:i] + random.choice("abcdefghijklmnopqrstuvwxyz") + name[i+1:]
    if random.random() < 0.2:
        dom = random.choice(["gmail.com", "gmx.de", "web.de", "yahoo.com"])
    return name + "@" + dom


# Verzerrungs-Set mit Gewichten (für Randomisierung sowie Erhöhung der Schwierigkeit)
DISTORTIONS = [
    (_replace_umlauts, 0.8),
    (_random_case, 0.7),
    (_random_typo, 0.9),
    (_distort_street, 0.55),
    (_drop_value, 0.44),
]

def distort(df, text_cols=None, only_duplicates=True, prob_apply=1.0, max_changes_per_field=6, SEED = 42):
    """
    Wendet kontrollierte Verzerrungen auf markierte Duplikate im DataFrame an.

    Parameter:
    ----------
    df : pd.DataFrame
        Eingabedaten mit Originalen und Duplikaten (inkl. Spalte `is_duplicated`).
    text_cols : List[str]
        Spalten, die verzerrt werden sollen (Standard: alle außer ID-Spalten).
    prob_apply : float
        Wahrscheinlichkeit, ob ein Feld überhaupt verzerrt wird (default: 1 = immer).
    max_changes_per_field : int
        Maximale Anzahl zufälliger Verzerrungen je Feld (1-max).

    Rückgabe:
    ---------
    df : pd.DataFrame
        Neuer DataFrame mit Verzerrungen in den Datensätzen.
    """
    random.seed(SEED)

    if text_cols is None:
        text_cols = [c for c in df.columns if c not in ["cluster_id", "id", "is_duplicated"]]
    
    df = df.copy()

    df["is_duplicated"] = df["is_duplicated"].where(
        df["is_duplicated"].notna(),
        False
    ).astype(bool)

    if only_duplicates and "is_duplicated" in df.columns:
        target_idx = df.index[df["is_duplicated"]]
    else:
        target_idx = df.index

    funcs, probs = zip(*DISTORTIONS)

    for idx in target_idx:
        for col in text_cols:
            if col not in df.columns:
                continue
            if random.random() < prob_apply:
                val = str(df.at[idx, col])

                # Spezifische Verzerrungslogik
                if "plz" in col and random.random() < 0.5:
                    val = _distort_plz(val)
                if col == "telefon":
                    val = _distort_phone(val)
                if col == "email":
                    val = _distort_email(val)
                if col == "strasse":
                    if random.random() < 0.8:
                        val = _distort_street(val)

                # Generische Verzerrzngen zufällig anwenden
                for _ in range(random.randint(1, max_changes_per_field)):
                    func = random.choices(funcs, weights=probs, k=1)[0]
                    val = func(val)

                df.at[idx, col] = val
    return df

def generate_dirty_crm_data(generation_size_dirty, generation_size_clean, dirty_seed = 0, clean_seed = 1, salesforce = True, sales_force_crazy = False):

    if(salesforce):
        df_columns = ["sf_vorname",
                "sf_nachname",
                "sf_email",
                "sf_telefon",
                "sf_strasse",
                "sf_hausnr",
                "sf_plz",
                "sf_stadt",
                "sf_land"]
    else:
        df_columns = [
            "ns_vorname",
            "ns_nachname",
            "ns_email",
            "ns_telefon",
            "ns_strasse",
            "ns_hausnr",
            "ns_plz",
            "ns_stadt",
            "ns_land"
        ]

    crm_data_pre_dirty = generate(generation_size_dirty, df_columns, dirty_seed)

    crm_data_pre_dirty = inject_hard_negative_entities(
        crm_data_pre_dirty,
        share=0.2,
        seed=dirty_seed
    )
    crm_data_pre_dirty_duplicated = duplicate(crm_data_pre_dirty)
    crm_data_dirty = distort(crm_data_pre_dirty_duplicated, df_columns, True, 1, 8, dirty_seed)

    if salesforce and sales_force_crazy:
        crm_data_dirty = transform_salesforce_schema(crm_data_dirty)
    
    crm_data_clean = generate(generation_size_clean, df_columns, clean_seed)

    if salesforce and sales_force_crazy:
        crm_data_clean = transform_salesforce_schema(crm_data_clean)
    
    crm_data_complete = pd.concat([crm_data_dirty, crm_data_clean], ignore_index=True)

    return crm_data_complete

def transform_salesforce_schema(df):
    df = df.copy()

    df["sf_fullname"] = df["sf_vorname"] + " " + df["sf_nachname"]

    df["sf_address"] = (
        df["sf_strasse"] + " " + df["sf_hausnr"] + ", " +
        df["sf_plz"] + " " + df["sf_stadt"]
    )

    df = df.drop(columns=[
        "sf_vorname", "sf_nachname",
        "sf_strasse", "sf_hausnr", "sf_plz", "sf_stadt"
    ])

    return df

def generate_synthetic_crm_sources(
    n_dirty=1000,
    n_clean=9000,
    dirty_seed=1,
    clean_seed=2,
    persist=False,
):
    """
    Erzeugt synthetische CRM-Daten für Salesforce und Netsuite
    mit identischer Struktur, aber separater Quelle.
    """

    sf = generate_dirty_crm_data(
        n_dirty, n_clean,
        dirty_seed=dirty_seed,
        clean_seed=clean_seed,
        salesforce=True
    )
    ns = generate_dirty_crm_data(
        n_dirty, n_clean,
        dirty_seed=dirty_seed,
        clean_seed=clean_seed,
        salesforce=False
    )

    sf["source"] = "salesforce"
    ns["source"] = "netsuite"

    if persist:
        sf.to_csv("dirty_salesforce.csv", index=False)
        ns.to_csv("dirty_netsuite.csv", index=False)

    return sf, ns

def inject_hard_negative_entities(df: pd.DataFrame, share=0.1, seed=42):
    rng = np.random.default_rng(seed)
    faker = Faker("de_DE")

    df = df.copy().reset_index(drop=True)
    prefix = _detect_prefix(df.columns)

    n = int(len(df) * share)
    candidates = df.sample(n, random_state=seed)

    new_rows = []

    for _, row in candidates.iterrows():
        hn = row.copy()
        mode = rng.choice(["same_household", "same_name", "killer_feature"])

        if mode == "same_household":
            hn[f"{prefix}vorname"] = faker.first_name()
            hn[f"{prefix}nachname"] = faker.last_name()
            hn[f"{prefix}email"] = faker.email()
            hn[f"{prefix}telefon"] = faker.phone_number()

        elif mode == "same_name":
            hn[f"{prefix}strasse"] = faker.street_name()
            hn[f"{prefix}plz"] = faker.postcode()
            hn[f"{prefix}stadt"] = faker.city()
            hn[f"{prefix}email"] = faker.email()

        elif mode == "killer_feature":
            hn[f"{prefix}email"] = faker.email()
            hn[f"{prefix}telefon"] = faker.phone_number()

        # neue Entität
        hn["cluster_id"] = df["cluster_id"].max() + len(new_rows) + 1
        hn["is_duplicated"] = False

        new_rows.append(hn)

    return pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

def _detect_prefix(columns):
    for p in ["sf_", "ns_"]:
        if any(c.startswith(p) for c in columns):
            return p
    raise ValueError("Unknown column prefix")