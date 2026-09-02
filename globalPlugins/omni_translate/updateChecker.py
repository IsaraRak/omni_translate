# -*- coding: utf-8 -*-
# OmniTranslate - Automatic Background Update Checker
# Author: Isara Watthanawirojkul

import os
import sys
import json
import urllib.request
import tempfile
import threading
import re
import wx
import gui
import ui
import logHandler
import addonHandler

addonHandler.initTranslation()

GITHUB_REPO = "IsaraRak/omni_translate"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(v_str):
    """Extracts tuple of integers from version string (e.g., '2026.3.1' -> (2026, 3, 1))."""
    if not v_str:
        return (0,)
    v_str = str(v_str).lower().lstrip("v").strip()
    parts = re.findall(r'\d+', v_str)
    return tuple(int(p) for p in parts) if parts else (0,)


def get_current_addon_version():
    """Gets the currently installed version of OmniTranslate."""
    try:
        cur_addon = addonHandler.getCodeAddon()
        if cur_addon and cur_addon.manifest:
            return cur_addon.manifest.get("version", "2026.3.1")
    except Exception:
        pass
    return "2026.3.1"


def check_for_updates_background():
    """Runs in a background thread to check GitHub for the latest release."""
    try:
        req = urllib.request.Request(
            API_URL,
            headers={
                "User-Agent": "OmniTranslate-AutoUpdater",
                "Accept": "application/vnd.github+json"
            }
        )
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        if not latest_tag:
            return

        cur_v = parse_version(get_current_addon_version())
        latest_v = parse_version(latest_tag)

        if latest_v > cur_v:
            # Find the .nvda-addon asset
            download_url = None
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".nvda-addon"):
                    download_url = asset.get("browser_download_url")
                    break

            if download_url:
                wx.CallAfter(_prompt_user_to_update, latest_tag, download_url)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: Auto-update check skipped/failed: {e}")


def _prompt_user_to_update(latest_version, download_url):
    """Displays accessible confirmation dialog on GUI thread."""
    try:
        parent = gui.mainFrame
        msg = _(
            "A new version of OmniTranslate ({version}) is available.\n\n"
            "Would you like to download and install the update now?"
        ).format(version=latest_version)
        title = _("OmniTranslate Update Available")

        res = gui.messageBox(msg, title, wx.YES_NO | wx.ICON_QUESTION, parent)
        if res == wx.YES:
            threading.Thread(
                target=_download_and_install,
                args=(download_url, latest_version),
                daemon=True
            ).start()
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Error displaying update dialog: {e}")


def _download_and_install(download_url, latest_version):
    """Downloads the .nvda-addon bundle and invokes NVDA addonHandler installer."""
    try:
        wx.CallAfter(ui.message, _("OmniTranslate: Downloading update..."))
        temp_dir = tempfile.gettempdir()
        temp_addon_path = os.path.join(temp_dir, f"omni_translate_{latest_version}.nvda-addon")

        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "OmniTranslate-AutoUpdater"}
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            with open(temp_addon_path, "wb") as f_out:
                f_out.write(resp.read())

        def _do_install():
            try:
                bundle = addonHandler.AddonBundle(temp_addon_path)
                addonHandler.installAddonPackage(bundle)
            except Exception as inst_err:
                logHandler.log.error(f"OmniTranslate: Installation failed: {inst_err}")
                ui.message(f"{_('OmniTranslate Update Error:')} {inst_err}")

        wx.CallAfter(_do_install)
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Failed downloading update: {e}")
        wx.CallAfter(ui.message, f"{_('OmniTranslate: Failed to download update.')} {e}")


def start_update_checker_service():
    """Initializes the background update checker with a startup delay."""
    wx.CallLater(10000, lambda: threading.Thread(target=check_for_updates_background, daemon=True).start())
