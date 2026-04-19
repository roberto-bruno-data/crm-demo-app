import pandas as pd
import streamlit as st
import re
from thesis.streamlit_UI.ui_components.constants import STANDARD_SCHEMA

def process_uploaded_files(uploaded_files, rename_dict):
    dfs = []

    for file in uploaded_files:
        try:
            file.seek(0)
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()
        except pd.errors.EmptyDataError:
            st.warning(f"{file.name} konnte nicht gelesen werden")
            continue

        df_mapped = df.rename(columns=rename_dict)
        df_harmonized = harmonize_uploaded_df(df_mapped, file)

        dfs.append(df_harmonized)
        
    if not dfs:
        st.error("Keine gültigen Daten gefunden")
        st.stop()

    combined_df = pd.concat(dfs, ignore_index=True)

    # entity_id neu setzen (wichtig!)
    combined_df["entity_id"] = range(1, len(combined_df) + 1)

    return combined_df

def harmonize_uploaded_df(df, file):
    df = df.copy()

    df["source"] = file.name

    # --- Address Split ---
    if "strasse" not in df.columns and "address" in df.columns:
        split = df["address"].apply(split_address)

        df["strasse"] = split.apply(lambda x: x[0])
        df["hausnr"]  = split.apply(lambda x: x[1])
        df["plz"]     = split.apply(lambda x: x[2])
        df["stadt"]   = split.apply(lambda x: x[3])

    # --- Text Cleanup ---
    for col in ["vorname", "nachname", "stadt"]:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)

    # --- Name Split ---
    if "vorname" in df.columns and "nachname" in df.columns:
        mask = df["nachname"].isna() | (df["nachname"] == "")

        if mask.any():
            split = df.loc[mask, "vorname"].apply(split_full_name)
            df.loc[mask, "vorname"] = split.apply(lambda x: x[0])
            df.loc[mask, "nachname"] = split.apply(lambda x: x[1])

    # --- Email ---
    if "email" in df.columns:
        df["email"] = df["email"].apply(normalize_email)

    # --- Telefon ---
    if "telefon" in df.columns:
        df["telefon"] = df["telefon"].apply(normalize_phone)

    # --- Land ---
    if "land" in df.columns:
        df["land"] = df["land"].apply(normalize_country)

    return df

def normalize_text(s):
    if pd.isna(s):
        return None
    return str(s).strip().title()

def split_address(address):
    if pd.isna(address):
        return None, None, None, None

    address = str(address)

    try:
        street_part, city_part = address.split(",")

        street_part = street_part.strip()
        city_part = city_part.strip()

        # --- Straße + Hausnummer ---
        street_tokens = street_part.split()

        if len(street_tokens) > 1 and street_tokens[-1].isdigit():
            hausnr = street_tokens[-1]
            strasse = " ".join(street_tokens[:-1])
        else:
            hausnr = None
            strasse = street_part

        # --- PLZ + Stadt ---
        city_tokens = city_part.split()

        if len(city_tokens) > 0 and city_tokens[0].isdigit():
            plz = city_tokens[0]
            stadt = " ".join(city_tokens[1:]) if len(city_tokens) > 1 else None
        else:
            plz = None
            stadt = city_part

        if len(street_tokens) > 1:
            match = re.match(r"(\d+\w*)$", street_tokens[-1])

            if match:
                hausnr = match.group(1)
                strasse = " ".join(street_tokens[:-1])
            else:
                hausnr = None
                strasse = street_part

                return strasse, hausnr, plz, stadt

    except Exception:
        return address, None, None, None
    
def split_full_name(full_name):
    if pd.isna(full_name):
        return "", ""

    parts = str(full_name).split()

    if len(parts) == 1:
        return parts[0], ""

    return " ".join(parts[:-1]), parts[-1]

def normalize_phone(phone):
    if pd.isna(phone):
        return None

    phone = str(phone)

    # alles außer Zahlen entfernen
    phone = re.sub(r"\D", "", phone)

    if not phone:
        return None

    # einfache Normalisierung Deutschland
    if phone.startswith("0049"):
        phone = "0" + phone[4:]
    elif phone.startswith("49"):
        phone = "0" + phone[2:]

    return phone

def normalize_email(email):
    if pd.isna(email):
        return None

    email = str(email).strip().lower()

    # (at) → @
    email = email.replace("(at)", "@").replace("[at]", "@")

    # Leerzeichen entfernen
    email = email.replace(" ", "")

    # häufige Tippfehler bei Domains
    email = re.sub(r"gmaill\.com", "gmail.com", email)
    email = re.sub(r"gmial\.com", "gmail.com", email)

    # Mehrere @ → ungültig → None
    if email.count("@") != 1:
        return None

    return email


def normalize_country(country):
    if pd.isna(country):
        return None

    c = str(country).strip().lower()

    mapping = {
        "deutschland": "DE",
        "germany": "DE",
        "brd": "DE",
        "d": "DE",
        "de": "DE"
    }

    return mapping.get(c, c.upper())

def suggest_mapping(std_col, df_columns):
    synonyms = STANDARD_SCHEMA.get(std_col, [])

    best_match = None
    best_score = 0

    for col in df_columns:
        c = col.lower()

        if std_col.lower() == c:
            return col

        for syn in synonyms:
            if syn.lower() in c:
                score = len(syn)
                if score > best_score:
                    best_match = col
                    best_score = score

    return best_match or "-- nicht vorhanden --"