"""
build.py
PyInstaller build script for SC Dossier.

Usage:
    python build.py
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path


def clean_build_dirs():
    """Remove existing build/dist directories to ensure a clean build."""
    for d in ["build", "dist"]:
        if os.path.exists(d):
            print(f"Cleaning {d}/ directory...")
            shutil.rmtree(d)


def build_executable():
    """Run PyInstaller with the required configuration."""
    
    # Base command
    cmd = [
        "pyinstaller",
        "--name=SCDossier",
        "--windowed",     # No console window
        "--noconfirm",    # Overwrite output without asking
        "--clean",
    ]

    # Handle assets/fonts data inclusion
    # Syntax is 'source_path;destination_folder' on Windows, ':' on Linux/Mac
    sep = ";" if platform.system() == "Windows" else ":"
    
    assets_dir = Path("src/assets")
    if assets_dir.exists():
        cmd.append(f"--add-data=src/assets{sep}src/assets")
        
    # Hidden imports required by dynamic loaders (rapidocr, bs4, lxml)
    hidden_imports = [
        "rapidocr_onnxruntime",
        "bs4",
        "lxml",
        "requests",
        "PIL",
        "PyQt6.sip",
        "PyQt6.QtGui",
        "PyQt6.QtCore",
        "PyQt6.QtWidgets",
    ]
    
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")

    # Entry point
    cmd.append("src/main.py")

    print(f"Running PyInstaller: {' '.join(cmd)}")
    
    # Execute
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print("\nBuild completed successfully!")
        print(f"Executable is located in the 'dist' directory.")
    else:
        print("\nBuild failed.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    print("Starting SC Dossier Build Process...")
    clean_build_dirs()
    build_executable()
