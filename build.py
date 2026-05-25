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

# Ensure src can be imported
sys.path.insert(0, os.path.abspath("."))
try:
    from src.app.constants import APP_VERSION
except ImportError:
    APP_VERSION = "unknown"

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
        "--onefile",      # Required for auto-updater replacement logic
        "--noconfirm",    # Overwrite output without asking
        "--clean",
        "--exclude-module=PyQt5",  # Prevent conflict with PyQt6
        "--exclude-module=torch",
        "--exclude-module=torchvision",
        "--exclude-module=torchaudio",
        "--exclude-module=scipy",
        "--exclude-module=pandas",
        "--exclude-module=pygame",
        "--exclude-module=matplotlib",
        "--icon=src/assets/appicon.ico",  # Add the app icon to the executable
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
        
        # Package into a zip file for distribution / auto-updater
        import zipfile
        
        sys_name = platform.system().lower()
        if sys_name == "darwin":
            sys_name = "mac"
            
        zip_name = f"SCDossier-{sys_name}-v{APP_VERSION}.zip"
        zip_path = Path("dist") / zip_name
        
        exe_name = "SCDossier.exe" if sys_name == "windows" else "SCDossier"
        exe_path = Path("dist") / exe_name
        
        if exe_path.exists():
            print(f"Zipping output to {zip_path} ...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(exe_path, arcname=exe_name)
            print(f"Archive created: {zip_path}")
        else:
            print(f"Error: Executable '{exe_name}' not found in dist/")
    else:
        print("\nBuild failed.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    print("Starting SC Dossier Build Process...")
    clean_build_dirs()
    build_executable()
