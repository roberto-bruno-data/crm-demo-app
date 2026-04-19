import pandas as pd
import random
from pathlib import Path

STANDARD_SCHEMA = {
    "vorname": [
        "vorname", "firstname", "first_name", "fname", "givenname", "given_name"
    ],
    "nachname": [
        "nachname", "lastname", "last_name", "surname", "lname", "familyname", "family_name"
    ],
    "email": [
        "email", "e-mail", "mail", "email_address", "emailaddress"
    ],
    "telefon": [
        "telefon", "phone", "phone_number", "phonenumber", "tel", "mobile", "mobil", "handy"
    ],
    "strasse": [
        "straße", "strasse", "street", "street_name"
    ],
    "hausnr": [
        "hausnummer", "hausnr", "house_number", "housenumber", "addr_number"
    ],
    "plz": [
        "plz", "zip", "zipcode", "zip_code", "postalcode", "postal_code"
    ],
    "stadt": [
        "stadt", "city", "town", "ort"
    ],
    "land": [
        "land", "country", "nation"
    ]
}


def randomize_schema(file_path):
    path = Path(file_path)

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    rename_map = {}

    for col in df.columns:
        col_lower = col.lower()

        # find matching standard column
        for std_col, synonyms in STANDARD_SCHEMA.items():
            if col_lower == std_col or col_lower in synonyms:
                new_name = random.choice(synonyms)
                rename_map[col] = new_name
                break

    df = df.rename(columns=rename_map)

    new_path = path.with_name(f"{path.stem}_new{path.suffix}")
    df.to_csv(new_path, index=False)

    print("Renamed columns:")
    for k, v in rename_map.items():
        print(f"{k} → {v}")

    print(f"\nSaved to: {new_path}")


# 👉 Example usage
if __name__ == "__main__":
    randomize_schema("data/results/crm_demo_altx_new.csv")