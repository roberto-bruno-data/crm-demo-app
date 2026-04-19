import sys
import os

ROOT = os.path.dirname(__file__)

# Make repo root importable
sys.path.insert(0, ROOT)

# Make erlib (src layout) importable
sys.path.insert(0, os.path.join(ROOT, "erlib", "src"))

from thesis.streamlit_UI.Systemkontext import main

import streamlit as st
from sqlalchemy import create_engine
from erlib.db.schema import initialize_database

st.set_page_config(page_title="Systemkontext", layout="wide")

DATABASE_URL = st.secrets["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}
)

initialize_database(engine)

main()
