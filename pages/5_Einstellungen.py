from pathlib import Path
import yaml
import streamlit_UI.ui_components.constants as constants
import streamlit as st

st.title("⚙️ Attribut-Priorisierung")

# Reverse Mapping: UI → technisch
reverse_map = {v: k for k, v in constants.UI_RENAME.items()}

# Pfad zu preferences.yaml
config_path = Path(__file__).resolve().parents[1] / "streamlit_UI" / "ui_components" / "preferences.yaml"

# Datei laden
if config_path.exists():
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

attribute_priority = config.get("attribute_priority", {})
updated_priority = {}

DISPLAY_ATTRS = list(constants.UI_RENAME.values())

for attr in DISPLAY_ATTRS:
    technical_key = reverse_map[attr]
    current_value = attribute_priority.get(technical_key)

    options = ["Keine Präferenz", "Salesforce", "NetSuite"]

    if current_value == "salesforce":
        default_index = 1
    elif current_value == "netsuite":
        default_index = 2
    else:
        default_index = 0

    choice = st.selectbox(
        attr,
        options,
        index=default_index,
        key=f"prio__{technical_key}"
    )

    if choice == "Keine Präferenz":
        updated_priority[technical_key] = None
    else:
        updated_priority[technical_key] = choice.lower()

if st.button("💾 Speichern"):
    config["attribute_priority"] = updated_priority
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f)

    st.success("Einstellungen gespeichert")