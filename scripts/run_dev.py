"""
scripts/run_dev.py
Development runner for SC Dossier.
Adds the project root to the python path and launches the app.

Set SCDOSSIER_DEBUG=1 environment variable to auto-attach x64dbg.
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

X64DBG_PATH = r"C:\Users\Administrator\Downloads\snapshot_2025-08-19_19-40\release\x64\x64dbg.exe"


def _attach_x64dbg():
    time.sleep(2)
    pid = os.getpid()
    print(f"[SCDossier] Attaching x64dbg to PID {pid}...")
    subprocess.Popen([X64DBG_PATH, "-p", str(pid)])


# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    if os.environ.get("SCDOSSIER_DEBUG"):
        threading.Thread(target=_attach_x64dbg, daemon=True).start()

    from src.main import main
    main()
