"""
src/services/scraper_org.py
OrgScraper — background worker for scraping RSI organization dossiers.
Handles both SID resolution (searching by name) and direct SID lookup.
Includes retry with exponential backoff.
"""

import logging
import time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal

from src.app.constants import RSI_ORG_URL, RSI_ORG_LISTING_URL

log = logging.getLogger(__name__)


def _fetch_with_retry(url: str, headers: dict, max_attempts: int = 3) -> requests.Response | None:
    """
    Fetch a URL with exponential backoff retry.
    Delays: 1s, 2s, 4s between attempts.
    Returns None if all attempts fail.
    """
    delays = [1, 2, 4]
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 403:
                log.warning("Attempt %d: RSI blocked request (403) for %s", attempt + 1, url)
                if attempt < max_attempts - 1:
                    time.sleep(delays[min(attempt, len(delays) - 1)])
                    continue
                return resp
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            log.warning("Attempt %d failed for %s: %s", attempt + 1, url, e)
            if attempt < max_attempts - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                log.info("Retrying in %ds...", delay)
                time.sleep(delay)
            else:
                log.error("All %d attempts failed for %s", max_attempts, url)
                raise
    return None


class OrgSearchWorker(QThread):
    """
    Looks up an org by name (or partial SID).
    Emits a list of candidates: [{"name": str, "sid": str, "logo_url": str}]
    """
    
    candidates_found = pyqtSignal(list)
    finished_error = pyqtSignal(str)
    
    def __init__(self, query: str, user_agent: str) -> None:
        super().__init__()
        self.query = query
        self.user_agent = user_agent

    def run(self) -> None:
        headers = {"User-Agent": self.user_agent}
        url = f"{RSI_ORG_LISTING_URL}?search={self.query}"
        
        try:
            resp = _fetch_with_retry(url, headers)
            
            if resp is None:
                self.finished_error.emit("Failed to fetch org listing after 3 attempts.")
                return
            
            if resp.status_code == 403:
                self.finished_error.emit("RSI WEBSITE BLOCKED REQUEST — TRY AGAIN LATER")
                return
            
            soup = BeautifulSoup(resp.text, "lxml")
            candidates = []

            # Listing page selectors (verified via live HTML inspection)
            org_cards = soup.select("div.listing-wrapper > ul.orgs-listing.search > div.org-cell > a.trans-03s.clearfix")
            for card in org_cards:
                sid_elem = card.select_one("span.symbol")
                name_elem = card.select_one("h3.name")
                img_elem = card.select_one("span.thumb img")

                if sid_elem and name_elem:
                    sid = sid_elem.text.strip()
                    name = name_elem.text.strip()
                    
                    logo = ""
                    if img_elem and img_elem.has_attr("src"):
                        logo = img_elem["src"]
                        if not logo.startswith("http"):
                            logo = "https://robertsspaceindustries.com" + logo
                            
                    candidates.append({
                        "sid": sid,
                        "name": name,
                        "logo_url": logo
                    })
                    
            self.candidates_found.emit(candidates)
            
        except Exception as e:
            log.exception("Org search failed")
            self.finished_error.emit(f"Org search failed: {str(e)}")


class OrgScraperWorker(QThread):
    """
    Scrapes a specific org page by SID.
    """

    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, sid: str, user_agent: str) -> None:
        super().__init__()
        self.sid = sid.upper()
        self.user_agent = user_agent

    def run(self) -> None:
        headers = {"User-Agent": self.user_agent}
        data = {
            "sid": self.sid,
            "page_url": RSI_ORG_URL.format(sid=self.sid),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "name": self.sid,
            "logo_url": "",
            "logo_local": "",
            "banner_url": None,
            "banner_local": None,
            "archetype": None,
            "language": None,
            "commitment": None,
            "recruiting": False,
            "roleplay": False,
            "member_count": 0,
            "description": None,
            "focus_primary": None,
            "focus_secondary": None,
        }

        try:
            self.progress.emit(0.3)
            resp = _fetch_with_retry(data["page_url"], headers)
            
            if resp is None:
                self.finished_error.emit(f"Failed to fetch org '{self.sid}' after 3 attempts.")
                return
            
            if resp.status_code == 404:
                self.finished_error.emit(f"Organization '{self.sid}' not found (404).")
                return
            
            if resp.status_code == 403:
                self.finished_error.emit("RSI WEBSITE BLOCKED REQUEST — TRY AGAIN LATER")
                return
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Name: div.heading h1, split before "/"
            name_elem = soup.select_one("div.heading h1")
            data["name"] = name_elem.text.split('/')[0].strip() if name_elem else self.sid
            
            # Logo: div.logo.noshadow img (has both 'logo' and 'noshadow' classes)
            logo_elem = soup.select_one("div.logo.noshadow img")
            if logo_elem and logo_elem.has_attr("src"):
                logo = logo_elem["src"]
                if not logo.startswith("http"):
                    logo = "https://robertsspaceindustries.com" + logo
                data["logo_url"] = logo
            
            # Banner: div.heading div.banner img
            banner_elem = soup.select_one("div.heading div.banner img")
            if banner_elem and banner_elem.has_attr("src"):
                banner = banner_elem["src"]
                if not banner.startswith("http"):
                    banner = "https://robertsspaceindustries.com" + banner
                data["banner_url"] = banner
            else:
                data["banner_url"] = None
            
            # Archetype / commitment / language / recruiting / roleplay from tags list
            for li in soup.select("div.heading ul.tags li"):
                label_elem = li.select_one("label")
                value_elem = li.select_one("span.value")
                if label_elem and value_elem:
                    label_text = label_elem.text.strip().lower()
                    val = value_elem.text.strip()
                    if "archetype" in label_text:
                        data["archetype"] = val
                    elif "lang" in label_text:
                        data["language"] = val
                    elif "commitment" in label_text:
                        data["commitment"] = val
                    elif "recruiting" in label_text:
                        data["recruiting"] = (val.lower() in ("yes", "true", "recruiting", "open"))
                    elif "roleplay" in label_text:
                        data["roleplay"] = (val.lower() in ("yes", "true", "roleplay", "enforced"))
            
            # Member count: div.logo span.count → text digits
            count_elem = soup.select_one("div.logo span.count")
            if count_elem:
                text = count_elem.text.strip()
                digits = ''.join(c for c in text if c.isdigit())
                data["member_count"] = int(digits) if digits else 0
            
            # Description: active description markitup-text
            desc_elem = soup.select_one("div.content.block.description div.markitup-text.active")
            if not desc_elem:
                desc_elem = soup.select_one("div.content.block.description div.markitup-text")
            data["description"] = desc_elem.text.strip() if desc_elem else None
            
            # Focus: primary and secondary focus images alt-text
            focus_primary_elem = soup.select_one("div.heading ul.focus li.primary img")
            focus_secondary_elem = soup.select_one("div.heading ul.focus li.secondary img")
            data["focus_primary"] = focus_primary_elem["alt"].strip() if focus_primary_elem and focus_primary_elem.has_attr("alt") else None
            data["focus_secondary"] = focus_secondary_elem["alt"].strip() if focus_secondary_elem and focus_secondary_elem.has_attr("alt") else None

            self.progress.emit(1.0)
            self.finished_success.emit(data)

        except requests.RequestException as e:
            log.error("Org Scraper HTTP Error: %s", e)
            self.finished_error.emit(f"Network error: {str(e)}")
        except Exception as e:
            log.exception("Org Scraping failed")
            self.finished_error.emit(f"Scraper error: {str(e)}")