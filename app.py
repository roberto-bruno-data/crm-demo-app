import sys
import os

ROOT = os.path.dirname(__file__)

# Make repo root importable
sys.path.insert(0, ROOT)

# Make erlib (src layout) importable
sys.path.insert(0, os.path.join(ROOT, "erlib", "src"))

from thesis.streamlit_UI.Systemkontext import main

main()
