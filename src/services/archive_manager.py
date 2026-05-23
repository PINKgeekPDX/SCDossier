"""
src/services/archive_manager.py
ArchiveManager — handles listing, deleting, loading, and exporting archived profiles.
"""

import os
import json
import csv
import base64
import shutil
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QObject

from src.core.paths import PathManager
from src.core.events import EventBus
from src.ui.theme import palette as P

log = logging.getLogger(__name__)


class ArchiveManager(QObject):
    """
    High-level API for archive operations.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.paths = PathManager.instance()

    def list_archived_profiles(self) -> list[dict]:
        """
        Return a list of minimal dictionaries for all archived profiles.
        """
        profiles = []
        for d in self.paths.archived_root.iterdir():
            if not d.is_dir():
                continue
            json_path = d / "profile.json"
            if not json_path.exists():
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    profiles.append({
                        "handle": data.get("handle", d.name),
                        "moniker": data.get("moniker", d.name),
                        "avatar_local": data.get("avatar_local"),
                        "archived_at": data.get("archived_at"),
                        "synced_at": data.get("synced_at"),
                    })
            except Exception as e:
                log.warning("Failed to parse archive %s: %s", d.name, e)
        return profiles

    def load_archived_profile(self, handle: str) -> dict | None:
        """Load a full archived profile dict."""
        arch_dir = self.paths.archived_dir(handle)
        json_path = arch_dir / "profile.json"
        if not json_path.exists():
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error("Failed to load archived profile %s: %s", handle, e)
            return None

    def delete_profile(self, handle: str) -> bool:
        """Permanently delete an archived profile and its folder."""
        arch_dir = self.paths.archived_dir(handle)
        if arch_dir.exists():
            try:
                shutil.rmtree(arch_dir)
                log.info("Deleted archived profile: %s", handle)
                EventBus.instance().archive_updated.emit()
                return True
            except OSError as e:
                log.error("Failed to delete archive %s: %s", handle, e)
        return False

    def export_profile(self, handle: str, output_dir: Path) -> Path | None:
        """
        Export a profile to a ZIP containing:
        - profile.json
        - All images (avatar, badges, org logos)
        - profile.txt (human-readable summary)
        - profile.csv (tabular data)
        - profile.html (standalone styled card with inline base64 images)
        """
        arch_dir = self.paths.archived_dir(handle)
        if not arch_dir.exists():
            log.error("Cannot export %s: archive does not exist.", handle)
            return None

        data = self.load_archived_profile(handle)
        if not data:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"SCDossier_{handle}_{timestamp}.zip"
        zip_path = output_dir / zip_name

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add all existing files
                for root, _, files in os.walk(arch_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(arch_dir)
                        zf.write(file_path, arcname)

                # Generate and add TXT summary
                txt_content = self._generate_txt(data)
                zf.writestr("profile.txt", txt_content)

                # Generate and add CSV
                csv_content = self._generate_csv(data)
                zf.writestr("profile.csv", csv_content)

                # Generate and add HTML card (with inline base64 images)
                html_content = self._generate_html(data)
                zf.writestr("profile.html", html_content)

            log.info("Exported profile %s to %s", handle, zip_path)
            return zip_path
        except Exception as e:
            log.exception("Failed to export profile %s to ZIP", handle)
            if zip_path.exists():
                zip_path.unlink()
            return None

    def _generate_txt(self, data: dict) -> str:
        lines = [
            "=" * 60,
            f"SC DOSSIER — {data.get('moniker', 'Unknown')} (@{data.get('handle', 'unknown')})",
            "=" * 60,
            "",
            f"Handle:    {data.get('handle', '—')}",
            f"Moniker:   {data.get('moniker', '—')}",
            f"Enlisted:  {data.get('enlisted', '—')}",
            f"Location:  {data.get('location', '—')}",
            f"Fluency:   {', '.join(data.get('fluency', [])) or '—'}",
            "",
            "BIOGRAPHY:",
            "-" * 40,
            data.get('bio', 'No biography provided.') or 'No biography provided.',
            "",
            "ACCREDITATIONS:",
            "-" * 40,
        ]
        for b in data.get("badges", []):
            lines.append(f"  \u2022 {b.get('name', 'Unknown')}")
        if not data.get("badges"):
            lines.append("  (none)")

        lines.extend(["", "ORGANIZATIONS:", "-" * 40])
        for o in data.get("orgs", []):
            main_tag = " [MAIN]" if o.get("is_main") else ""
            lines.append(f"  \u2022 {o.get('name', 'Unknown')} ({o.get('sid', '')}){main_tag}")
            lines.append(f"    Rank: {o.get('rank', '\u2014')}")
        if not data.get("orgs"):
            lines.append("  (none)")

        lines.extend([
            "",
            f"Archived: {data.get('archived_at', '\u2014')}",
            f"Synced:   {data.get('synced_at', '\u2014')}",
            "=" * 60,
        ])
        return "\n".join(lines)

    def _generate_csv(self, data: dict) -> str:
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Handle", data.get("handle", "")])
        writer.writerow(["Moniker", data.get("moniker", "")])
        writer.writerow(["Enlisted", data.get("enlisted", "")])
        writer.writerow(["Location", data.get("location", "")])
        writer.writerow(["Fluency", ", ".join(data.get("fluency", []))])
        writer.writerow(["Bio", data.get("bio", "")])
        writer.writerow(["Archived", data.get("archived_at", "")])
        writer.writerow(["Synced", data.get("synced_at", "")])
        writer.writerow([])
        writer.writerow(["Badge Name", "Image URL"])
        for b in data.get("badges", []):
            writer.writerow([b.get("name", ""), b.get("image_url", "")])
        writer.writerow([])
        writer.writerow(["Org Name", "SID", "Rank", "Logo URL", "Main"])
        for o in data.get("orgs", []):
            writer.writerow([
                o.get("name", ""), o.get("sid", ""), o.get("rank", ""),
                o.get("logo_url", ""), str(o.get("is_main", False))
            ])
        return output.getvalue()

    def _to_base64_src(self, file_path: str | None) -> str:
        """Read a local file and return a base64 data URI, or empty string."""
        if not file_path:
            return ""
        p = Path(file_path)
        if not p.exists():
            return ""
        try:
            with open(p, "rb") as f:
                data_bytes = f.read()
            ext = p.suffix.lower()[1:] if p.suffix else "png"
            if ext == "jpg":
                ext = "jpeg"
            b64_str = base64.b64encode(data_bytes).decode("ascii")
            return f"data:image/{ext};base64,{b64_str}"
        except Exception as e:
            log.warning("Failed to base64-encode %s: %s", file_path, e)
            return ""

    def _generate_html(self, data: dict) -> str:
        handle = data.get("handle", "unknown")
        moniker = data.get("moniker", handle)
        avatar_src = self._to_base64_src(data.get("avatar_local"))

        badges_html = ""
        for b in data.get("badges", []):
            img_src = self._to_base64_src(b.get("image_local", ""))
            badges_html += f'<div class="badge"><img src="{img_src}" alt="{b["name"]}"><span>{b["name"]}</span></div>'

        orgs_html = ""
        for o in data.get("orgs", []):
            logo_src = self._to_base64_src(o.get("logo_local", ""))
            main_tag = " \u2605 MAIN" if o.get("is_main") else ""
            orgs_html += f'''
            <div class="org-card">
                <img src="{logo_src}" alt="{o["name"]}" class="org-logo">
                <div class="org-info">
                    <h3>{o["name"]}{main_tag}</h3>
                    <p>{o["sid"]} \u2022 {o.get("rank", "")}</p>
                </div>
            </div>'''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SC Dossier \u2014 {moniker}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #050B0F;
    color: #D2E5F6;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 40px 20px;
  }}
  .card {{
    max-width: 700px;
    width: 100%;
    background: rgba(10, 29, 41, 0.6);
    border: 1px solid rgba(0, 170, 255, 0.2);
    border-radius: 4px;
    padding: 32px;
  }}
  .header {{ display: flex; gap: 24px; align-items: center; margin-bottom: 24px; }}
  .avatar {{ width: 120px; height: 120px; border-radius: 4px; object-fit: cover; border: 1px solid rgba(0,170,255,0.3); }}
  .header h1 {{ font-size: 28px; color: #D2E5F6; font-family: 'Sora', sans-serif; }}
  .header .handle {{ color: #00AAFF; font-size: 18px; font-family: 'JetBrains Mono', monospace; }}
  .section {{ margin-bottom: 20px; }}
  .section h2 {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;
    color: #A8B3BD; font-family: 'JetBrains Mono', monospace;
    border-bottom: 1px solid rgba(0,170,255,0.1); padding-bottom: 8px; margin-bottom: 12px;
  }}
  .data-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .data-item {{ background: rgba(0,0,0,0.2); border-radius: 4px; padding: 12px; }}
  .data-item .label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.15em; color: #A8B3BD; font-family: 'JetBrains Mono', monospace; }}
  .data-item .value {{ font-size: 14px; color: #D2E5F6; font-family: 'JetBrains Mono', monospace; margin-top: 4px; }}
  .bio {{ color: #BEC7D3; line-height: 1.6; font-size: 14px; }}
  .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .badge {{
    display: flex; align-items: center; gap: 6px;
    background: rgba(0,170,255,0.05); border: 1px solid rgba(0,170,255,0.2);
    border-radius: 18px; padding: 4px 12px 4px 4px;
  }}
  .badge img {{ width: 24px; height: 24px; border-radius: 50%; }}
  .badge span {{ font-size: 13px; font-family: 'JetBrains Mono', monospace; }}
  .org-card {{ display: flex; gap: 16px; align-items: center; padding: 12px; background: rgba(10,29,41,0.4); border: 1px solid rgba(0,170,255,0.15); border-radius: 4px; margin-bottom: 8px; }}
  .org-logo {{ width: 52px; height: 52px; border-radius: 4px; object-fit: cover; }}
  .org-info h3 {{ color: #D2E5F6; font-size: 16px; }}
  .org-info p {{ color: #A8B3BD; font-size: 13px; font-family: 'JetBrains Mono', monospace; }}
  .footer {{ text-align: center; margin-top: 24px; font-size: 11px; color: #A8B3BD; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.1em; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    {avatar_src if avatar_src else '<div class="avatar" style="background:#0F212E;display:flex;align-items:center;justify-content:center;font-size:40px;color:#A8B3BD;">\u25CE</div>'}
    <div>
      <h1>{moniker}</h1>
      <div class="handle">@{handle}</div>
    </div>
  </div>

  <div class="section">
    <h2>Profile Data</h2>
    <div class="data-grid">
      <div class="data-item"><div class="label">Enlisted</div><div class="value">{data.get('enlisted', '\u2014')}</div></div>
      <div class="data-item"><div class="label">Location</div><div class="value">{data.get('location', '\u2014')}</div></div>
      <div class="data-item"><div class="label">Fluency</div><div class="value">{', '.join(data.get('fluency', [])) or '\u2014'}</div></div>
    </div>
  </div>

  <div class="section">
    <h2>Biography</h2>
    <div class="bio">{data.get('bio', 'No biography provided.') or 'No biography provided.'}</div>
  </div>

  <div class="section">
    <h2>Accreditations & Clearances</h2>
    <div class="badges">{badges_html or '<span style="color:#A8B3BD;font-style:italic;">(none)</span>'}</div>
  </div>

  <div class="section">
    <h2>Affiliated Organizations</h2>
    {orgs_html or '<p style="color:#A8B3BD;font-style:italic;">(none)</p>'}
  </div>

  <div class="footer">
    SC DOSSIER \u2022 AEGIS LIQUID INTERFACE \u2022 {datetime.now().strftime('%Y-%m-%d')}
  </div>
</div>
</body>
</html>'''