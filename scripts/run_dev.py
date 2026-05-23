"""
scripts/run_dev.py
Development runner for SC Dossier.
Adds the project root to the python path and launches the app.
"""

import os
import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from src.main import main
    main()
