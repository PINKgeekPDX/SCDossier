"""
End-to-end test: scrape THEKVLT members, cache JSON, check results.
Run from project root: python scripts/test_members_api.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import re
import json
import time
from bs4 import BeautifulSoup

# Use the fixed parser directly
from src.services.scraper_org import _parse_member_items, _fetch_org_members

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
SID = "THEKVLT"
headers = {"User-Agent": UA}

print("=" * 60)
print(f"Testing _fetch_org_members for {SID}")
print("=" * 60)

members = _fetch_org_members(SID, headers)

print(f"\nTotal visible members fetched: {len(members)}")
print()
for i, m in enumerate(members):
    print(f"  [{i+1:2d}] handle={m['handle']!r:20s}  moniker={m['moniker']!r:20s}  "
          f"rank={m['rank']!r:15s}  role={m['role']!r:15s}  "
          f"avatar={'YES' if m['avatar_url'] else 'no'}")

print()
print("Sample JSON (first member):")
if members:
    print(json.dumps(members[0], indent=2))
