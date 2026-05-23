"""
scripts/tools/scraper_test.py
Standalone tool to test the RSI player and org scraper workers.
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import setup_logging
from src.services.scraper_player import PlayerScraperWorker
from src.services.scraper_org import OrgScraperWorker, OrgSearchWorker

def test_player_scraper(handle: str):
    print(f"--- Testing Player Scraper: {handle} ---")
    loop = QEventLoop()
    
    worker = PlayerScraperWorker(handle, "SCDossier/1.0", 0)
    
    def on_success(data):
        import json
        print("Success!")
        print(json.dumps(data, indent=2))
        loop.quit()
        
    def on_error(msg):
        print(f"Error: {msg}")
        loop.quit()
        
    worker.finished_success.connect(on_success)
    worker.finished_error.connect(on_error)
    worker.start()
    
    loop.exec()


def test_org_scraper(sid: str):
    print(f"--- Testing Org Scraper: {sid} ---")
    loop = QEventLoop()
    
    worker = OrgScraperWorker(sid, "SCDossier/1.0")
    
    def on_success(data):
        import json
        print("Success!")
        print(json.dumps(data, indent=2))
        loop.quit()
        
    def on_error(msg):
        print(f"Error: {msg}")
        loop.quit()
        
    worker.finished_success.connect(on_success)
    worker.finished_error.connect(on_error)
    worker.start()
    
    loop.exec()

if __name__ == "__main__":
    from src.core.paths import PathManager
    pm = PathManager.instance()
    setup_logging(pm.logs_dir / "app.log")
    
    if len(sys.argv) < 3:
        print("Usage: python scraper_test.py [player|org] [handle|sid]")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    target = sys.argv[2]
    
    # We must have a QApplication to use QThread safely in PyQt6
    if not QApplication.instance():
        app = QApplication(sys.argv)
        
    if mode == "player":
        test_player_scraper(target)
    elif mode == "org":
        test_org_scraper(target)
    else:
        print("Invalid mode. Use 'player' or 'org'.")
