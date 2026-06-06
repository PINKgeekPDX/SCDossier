import logging
import re
import time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal

from src.app.constants import RSI_CITIZEN_URL, RSI_CITIZEN_ORGS_URL

log = logging.getLogger(__name__)


def _fetch_with_retry(url: str, headers: dict, max_attempts: int = 3,
                      timeout_sec: int = 10, proxy: str | None = None) -> requests.Response | None:
    delays = [1, 2, 4]
    proxies = {"http": proxy, "https": proxy} if proxy else None
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout_sec, proxies=proxies)
            if resp.status_code == 404:
                return resp
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


class PlayerScraperWorker(QThread):

    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, handle: str, user_agent: str, delay_ms: int,
                 timeout_sec: int = 10, proxy: str | None = None) -> None:
        super().__init__()
        self.handle = handle
        self.user_agent = user_agent
        self.delay_ms = delay_ms
        self.timeout_sec = timeout_sec
        self.proxy = proxy

    def run(self) -> None:
        headers = {"User-Agent": self.user_agent}
        data = {
            "handle": self.handle,
            "page_url": RSI_CITIZEN_URL.format(handle=self.handle),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "moniker": self.handle,
            "enlisted": None,
            "location": None,
            "fluency": [],
            "bio": None,
            "avatar_url": "",
            "badges": [],
            "orgs": [],
        }

        try:
            self.progress.emit(0.1)

            url_main = data["page_url"]
            resp = _fetch_with_retry(url_main, headers, timeout_sec=self.timeout_sec, proxy=self.proxy)

            if resp is None:
                self.finished_error.emit(f"Failed to fetch profile for '{self.handle}' after 3 attempts.")
                return

            if resp.status_code == 404:
                self.finished_error.emit(f"Player '{self.handle}' not found (404).")
                return

            if resp.status_code == 403:
                self.finished_error.emit("RSI WEBSITE BLOCKED REQUEST - TRY AGAIN LATER")
                return

            soup = BeautifulSoup(resp.text, "lxml")

            info_entries = soup.select("div.profile.left-col div.info > p.entry")
            if info_entries:
                moniker_raw = info_entries[0].get_text(strip=True)
                if moniker_raw:
                    data["moniker"] = moniker_raw

                for entry in info_entries:
                    label_elem = entry.select_one("span.label")
                    icon_span = entry.select_one("span.icon")

                    if label_elem:
                        label_text = label_elem.get_text(strip=True).lower()
                        value_elem = entry.select_one("strong.value") or entry.select_one("a.value")
                        if value_elem:
                            val = value_elem.get_text(strip=True)
                            if "handle" in label_text:
                                data["handle"] = val
                    elif icon_span:
                        img_elem = icon_span.select_one("img")
                        val_elem = entry.select_one("span.value") or entry.select_one("strong.value") or entry.select_one("a.value")
                        if img_elem and img_elem.has_attr("src") and val_elem:
                            badge_name = val_elem.get_text(strip=True)
                            badge_url = img_elem["src"]
                            if not badge_url.startswith("http"):
                                badge_url = "https://robertsspaceindustries.com" + badge_url
                            data["badges"].append({
                                "name": badge_name,
                                "image_url": badge_url,
                                "image_local": ""
                            })

            avatar_img = soup.select_one("div.profile.left-col div.thumb img")
            if avatar_img and avatar_img.has_attr("src"):
                src = avatar_img["src"]
                if not src.startswith("http"):
                    src = "https://robertsspaceindustries.com" + src
                data["avatar_url"] = src

            for entry in soup.select("div.left-col div.inner p.entry"):
                label_elem = entry.select_one("span.label")
                if not label_elem:
                    continue
                label_text = label_elem.get_text(strip=True).lower()
                val_elem = entry.select_one("strong.value") or entry.select_one("a.value")
                if not val_elem:
                    continue
                val = val_elem.get_text(strip=True)
                if "enlisted" in label_text:
                    data["enlisted"] = val
                elif "location" in label_text:
                    data["location"] = val.replace(" , ", ", ")
                elif "fluency" in label_text:
                    data["fluency"] = [f.strip() for f in val.split(",") if f.strip()]

            bio_elem = soup.select_one("div.right-col div.inner div.entry.bio div.value")
            if bio_elem:
                data["bio"] = bio_elem.get_text(strip=True)

            self.progress.emit(0.5)

            main_org_elem = soup.select_one("div.main-org.right-col")
            if main_org_elem:
                _parse_org_entries(main_org_elem, data["orgs"], is_main=True)

            self.progress.emit(0.7)

            time.sleep(self.delay_ms / 1000.0)

            try:
                url_orgs = RSI_CITIZEN_ORGS_URL.format(handle=data["handle"])
                resp_orgs = _fetch_with_retry(url_orgs, headers, timeout_sec=self.timeout_sec, proxy=self.proxy)

                if resp_orgs and resp_orgs.status_code == 200:
                    soup_orgs = BeautifulSoup(resp_orgs.text, "lxml")
                    _parse_secondary_orgs(soup_orgs, data["orgs"])
            except Exception as e:
                log.warning("Orgs tab scrape failed for %s: %s", data["handle"], e)

            self.progress.emit(1.0)
            self.finished_success.emit(data)

        except requests.RequestException as e:
            log.error("Scraper HTTP Error: %s", e)
            self.finished_error.emit(f"Network error: {str(e)}")
        except Exception as e:
            log.exception("Scraping failed")
            self.finished_error.emit(f"Scraper error: {str(e)}")


def _parse_org_entries(block, org_list: list, is_main: bool = False) -> None:
    try:
        name = None
        sid = None
        rank = None
        logo_url = ""

        for entry in block.select("p.entry"):
            label_elem = entry.select_one("span.label")
            if label_elem:
                label_text = label_elem.get_text(strip=True).lower()
            else:
                label_text = ""

            if not name and not label_elem:
                org_name_elem = entry.select_one("a.value")
                if org_name_elem:
                    name = org_name_elem.get_text(strip=True)
                    thumb_img = block.select_one("div.thumb img")
                    if thumb_img and thumb_img.has_attr("src"):
                        logo_url = thumb_img["src"]
                        if not logo_url.startswith("http"):
                            logo_url = "https://robertsspaceindustries.com" + logo_url

            elif "sid" in label_text or "spectrum" in label_text:
                sid_elem = entry.select_one("strong.value") or entry.select_one("a.value")
                if sid_elem:
                    sid = sid_elem.get_text(strip=True)
            elif "rank" in label_text:
                rank_elem = entry.select_one("strong.value")
                if rank_elem:
                    rank = rank_elem.get_text(strip=True)

        if name:
            org_list.append({
                "name": name,
                "sid": sid or "",
                "rank": rank or "",
                "logo_url": logo_url,
                "logo_local": "",
                "is_main": is_main,
                "visibility": None,
                "member_count": None,
            })
    except Exception as e:
        log.warning("Failed to parse org entries: %s", e)


def _parse_secondary_orgs(soup, org_list: list) -> None:
    try:
        for block in soup.select("div.orgs-content .org"):
            name_elem = block.select_one(".info .entry:nth-of-type(1) .value")
            sid_elem = block.select_one(".info .entry:nth-of-type(2) .value")
            rank_elem = block.select_one(".info .entry:nth-of-type(3) .value")
            img_elem = block.select_one(".thumb img")

            if name_elem and sid_elem:
                name = name_elem.get_text(strip=True)
                sid = sid_elem.get_text(strip=True)
                if sid.lower() == "redacted":
                    continue

                rank = rank_elem.get_text(strip=True) if rank_elem else ""

                logo_url = ""
                if img_elem and img_elem.has_attr("src"):
                    logo_url = img_elem["src"]
                    if not logo_url.startswith("http"):
                        logo_url = "https://robertsspaceindustries.com" + logo_url

                if any(o["sid"] == sid for o in org_list):
                    continue

                org_list.append({
                    "name": name,
                    "sid": sid,
                    "rank": rank,
                    "logo_url": logo_url,
                    "logo_local": "",
                    "is_main": False,
                    "visibility": None,
                    "member_count": None,
                })
    except Exception as e:
        log.warning("Failed to parse secondary orgs: %s", e)
