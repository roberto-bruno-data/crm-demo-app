from pathlib import Path
import streamlit as st

def apply_theme():
    css_path = Path(__file__).parent / "theme.css"
    with open(css_path) as f:
        css = f.read()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)