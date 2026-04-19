import pandas as pd


def harmonise(df_crm1, df_crm2):

    df1 = df_crm1.copy()
    df2 = df_crm2.copy()

    mapping = {
        "vorname": ["sf_vorname", "ns_vorname"],
        "nachname": ["sf_nachname", "ns_nachname"],
        "email": ["sf_email", "ns_email"],
        "telefon": ["sf_telefon", "ns_telefon"],
        "strasse": ["sf_strasse", "ns_strasse"],
        "hausnr": ["sf_hausnr", "ns_hausnr"],
        "plz": ["sf_plz", "ns_plz"],
        "stadt": ["sf_stadt", "ns_stadt"],
        "land": ["sf_land", "ns_land"]
    }

    def rename_columns(df):

        new_cols = []

        for col in df.columns:

            new_name = next(
                (canonical for canonical, keys in mapping.items()
                 if any(k in col.lower() for k in keys)),
                col
            )

            new_cols.append(new_name)

        df.columns = new_cols

        return df


    df1 = rename_columns(df1)
    df2 = rename_columns(df2)

    combined = pd.concat([df1, df2], ignore_index=True)

    combined["entity_id"] = range(1, len(combined) + 1)

    return combined