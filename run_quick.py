#!/usr/bin/env python
"""Quick launcher for SC Dossier with UAC elevation support on Windows"""
import sys
import os
import ctypes

def elevate_if_not_admin():
    """Relaunch the script with Administrator privileges if not already elevated."""
    if sys.platform != 'win32':
        return
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except Exception:
        # Fallback if admin check fails
        return

    # Relaunch elevated via UAC prompt
    script = os.path.abspath(__file__)
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    
    print("Requesting Administrator privileges to bypass UIPI hotkey blocks...")
    ret = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{script}" {params}',
        os.path.dirname(script),
        1  # SW_SHOWNORMAL
    )
    
    # If UAC prompt was accepted (returns > 32), exit the non-elevated parent process
    if int(ret) > 32:
        sys.exit(0)
    else:
        print("Elevation declined or failed. Global hotkeys may not work when Star Citizen is focused.")
        sys.exit(1)

# Elevate if on Windows before running anything else
if __name__ == "__main__":
    elevate_if_not_admin()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set platform for headless testing if needed
os.environ['QT_QPA_PLATFORM'] = 'windows'  # Use native Windows backend

from src.main import main

if __name__ == "__main__":
    main()