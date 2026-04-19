import sys
import os

ROOT = os.path.dirname(__file__)

# IMPORTANT: insert at position 0 (highest priority)
sys.path.insert(0, os.path.join(ROOT, "erlib", "src"))

# Optional but safe:
sys.path.insert(0, ROOT)

from thesis.streamlit_UI.Systemkontext import main

main()
