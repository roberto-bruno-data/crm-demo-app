import pandas as pd
from pathlib import Path

def clean_csv(file_path):
    path = Path(file_path)

    # Read CSV
    df = pd.read_csv(path)

    # Columns to remove
    cols_to_drop = ["is_duplicated", "source", "cluster_id", "entity_id"]

    # Drop only if they exist (prevents errors)
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # Build new filename
    new_path = path.with_name(f"{path.stem}_new{path.suffix}")

    # Save
    df.to_csv(new_path, index=False)

    print(f"Saved cleaned file to: {new_path}")


# 👉 Example usage
if __name__ == "__main__":
    clean_csv("data/results/crm_demo_schema_diff.csv")