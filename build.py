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

    # Collect all data files, binaries, and hidden imports for these packages
    collect_all_modules = [
        "rapidocr_onnxruntime",
        "onnxruntime",
        "numpy"
    ]
    for mod in collect_all_modules:
        cmd.append(f"--collect-all={mod}")

    # Entry point
    cmd.append("src/main.py")

    print(f"Running PyInstaller: {' '.join(cmd)}")
    
    # Execute
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print("\nBuild completed successfully!")
        
        import zipfile
        sys_name = platform.system().lower()
        if sys_name == "darwin":
            sys_name = "mac"
            
        zip_name = f"SCDossier-{sys_name}-v{APP_VERSION}.zip"
        zip_path = Path("dist") / zip_name
        
        if sys_name == "windows":
            # Check for Inno Setup
            inno_paths = [
                r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                r"C:\Program Files\Inno Setup 6\ISCC.exe"
            ]
            iscc_exe = next((p for p in inno_paths if os.path.exists(p)), None)
            
            if iscc_exe:
                print(f"Found Inno Setup at {iscc_exe}. Compiling installer...")
                iscc_cmd = [iscc_exe, f"/dMyAppVersion={APP_VERSION}", "installer.iss"]
                iscc_result = subprocess.run(iscc_cmd, capture_output=False, text=True)
                
                if iscc_result.returncode == 0:
                    setup_exe = Path("Output") / "SCDossier-Setup.exe"
                    if setup_exe.exists():
                        print(f"Zipping installer to {zip_path} ...")
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                            zf.write(setup_exe, arcname="SCDossier-Setup.exe")
                        print(f"Archive created: {zip_path}")
                    else:
                        print("Error: Installer 'SCDossier-Setup.exe' not found in Output/")
                else:
                    print("\nInno Setup compilation failed.")
                    sys.exit(iscc_result.returncode)
            else:
                print("Inno Setup not found. Cannot build Windows installer.")
                print("Please install Inno Setup 6 from https://jrsoftware.org/isinfo.php")
        else:
            # For non-Windows, zip the dist/SCDossier directory
            build_dir = Path("dist") / "SCDossier"
            if build_dir.exists():
                print(f"Zipping output directory to {zip_path} ...")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(build_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, Path("dist"))
                            zf.write(file_path, arcname=arcname)
                print(f"Archive created: {zip_path}")
            else:
                print(f"Error: Directory '{build_dir}' not found in dist/")
    else:
        print("\nBuild failed.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    print("Starting SC Dossier Build Process...")
    clean_build_dirs()
    build_executable()
