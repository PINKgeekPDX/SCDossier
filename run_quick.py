#!/usr/bin/env python
"""Quick launcher for SC Dossier"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set platform for headless testing if needed
os.environ['QT_QPA_PLATFORM'] = 'windows'  # Use native Windows backend

from src.main import main

if __name__ == "__main__":
    main()