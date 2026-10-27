# -*- coding: utf-8 -*-
# OmniTranslate - Automatic Background Update Checker
# Author: Isara Watthanawirojkul

import os
import sys
import json
import hashlib
import zipfile
import configparser
import urllib.request
import urllib.parse
import tempfile
import threading
import re
import wx
import gui
import ui
import globalVars
import logHandler
import addonHandler

addonHandler.initTranslation()

GITHUB_REPO = "IsaraRak/omni_translate"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ALLOWED_UPDATE_HOSTS = (
    "github.com",
    "githubusercontent.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "raw.githubusercontent.com"
)


# Ensure backward compatibility alias for installAddonBundle
if hasattr(addonHandler, "installAddonBundle") and not hasattr(addonHandler, "installAddonPackage"):
    try:
        addonHandler.installAddonPackage = addonHandler.installAddonBundle
    except Exception:
        pass


def parse_version(v_str):
    """Extracts tuple of integers from version string (e.g., '2026.4' -> (2026, 4))."""
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
            return cur_addon.manifest.get("version", "2026.6")
    except Exception:
        pass
    return "2026.6"


def is_safe_download_url(url):
    """Validates that download URL uses HTTPS and points to trusted GitHub domains."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() != "https":
            return False
        host = (parsed.hostname or "").lower()
        return any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_UPDATE_HOSTS)
    except Exception:
        return False


# Update Integrity Verification
# GitHub publishes a SHA-256 digest for every release asset ("digest": "sha256:<hex>").
# An update is offered only when its asset carries a digest, and is installed only if the downloaded
# file matches it exactly, is a valid add-on bundle and declares this add-on's name.
ADDON_NAME = "omni_translate"
MAX_UPDATE_SIZE_BYTES = 400 * 1024 * 1024
_SHA256_DIGEST_RE = re.compile(r'^sha256:([0-9a-f]{64})$')


class UpdateVerificationError(Exception):
    """The downloaded update failed integrity or bundle validation."""


def parse_asset_sha256(asset):
    """Returns the lowercase hex SHA-256 from a GitHub release asset's 'digest' field, or None."""
    match = _SHA256_DIGEST_RE.match(str((asset or {}).get("digest") or "").strip().lower())
    return match.group(1) if match else None


def validate_addon_bundle(path):
    """Checks that the file is a zip bundle whose manifest.ini declares this add-on's name."""
    if not zipfile.is_zipfile(path):
        raise UpdateVerificationError("Downloaded file is not a valid add-on bundle")
    with zipfile.ZipFile(path) as bundle:
        for member in bundle.namelist():
            normalized = member.replace("\\", "/")
            if normalized.startswith("/") or ".." in normalized.split("/") or ":" in normalized:
                raise UpdateVerificationError(f"Unsafe path in add-on bundle: {member}")
        try:
            manifest_text = bundle.read("manifest.ini").decode("utf-8-sig", errors="replace")
        except KeyError:
            raise UpdateVerificationError("Add-on bundle has no manifest.ini")
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read_string("[manifest]\n" + manifest_text)
    name = parser.get("manifest", "name", fallback="").strip().strip('"')
    if name != ADDON_NAME:
        raise UpdateVerificationError(f"Add-on bundle is for '{name}', not '{ADDON_NAME}'")


def check_for_updates_background():
    """Runs in a background thread to check GitHub for the latest release."""
    if getattr(globalVars.appArgs, "secure", False) or getattr(globalVars.appArgs, "secureMode", False):
        return

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
            expected_sha256 = None
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".nvda-addon"):
                    candidate_url = asset.get("browser_download_url")
                    candidate_sha256 = parse_asset_sha256(asset)
                    if candidate_url and is_safe_download_url(candidate_url) and candidate_sha256:
                        download_url = candidate_url
                        expected_sha256 = candidate_sha256
                        break

            if download_url and expected_sha256:
                wx.CallAfter(_prompt_user_to_update, latest_tag, download_url, expected_sha256)
            else:
                logHandler.log.info(f"OmniTranslate: Update {latest_tag} found but its asset has no verifiable SHA-256 digest; not offered.")
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: Auto-update check skipped/failed: {e}")


def _prompt_user_to_update(latest_version, download_url, expected_sha256=None):
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
                args=(download_url, latest_version, expected_sha256),
                daemon=True
            ).start()
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Error displaying update dialog: {e}")


def _download_and_install(download_url, latest_version, expected_sha256=None):
    """Downloads the .nvda-addon bundle into a private temporary folder, verifies its SHA-256 digest and
    bundle manifest, then invokes the NVDA add-on installer."""
    if getattr(globalVars.appArgs, "secure", False) or getattr(globalVars.appArgs, "secureMode", False):
        return

    temp_addon_path = None
    try:
        if not is_safe_download_url(download_url):
            raise ValueError(f"Untrusted download URL: {download_url}")

        expected = str(expected_sha256 or "").strip().lower()
        if not re.match(r'^[0-9a-f]{64}$', expected):
            raise UpdateVerificationError("No SHA-256 digest is available for this update")

        wx.CallAfter(ui.message, _("OmniTranslate: Downloading update..."))
        # mkdtemp creates a folder only the current user can access, so no other process can swap
        # the bundle between verification and installation.
        temp_dir = tempfile.mkdtemp(prefix="omni_translate_update_")
        safe_version = re.sub(r'[^\w\.-]', '_', str(latest_version))
        temp_addon_path = os.path.join(temp_dir, f"omni_translate_{safe_version}.nvda-addon")

        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "OmniTranslate-AutoUpdater"}
        )
        hasher = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            if not is_safe_download_url(resp.geturl()):
                raise UpdateVerificationError(f"Update download was redirected to an untrusted address: {resp.geturl()}")
            with open(temp_addon_path, "xb") as f_out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_UPDATE_SIZE_BYTES:
                        raise UpdateVerificationError("Update file is unexpectedly large")
                    hasher.update(chunk)
                    f_out.write(chunk)

        if hasher.hexdigest() != expected:
            raise UpdateVerificationError("Update file checksum does not match the published SHA-256 digest")
        validate_addon_bundle(temp_addon_path)
        logHandler.log.info(f"OmniTranslate: Update {latest_version} verified (SHA-256 {expected[:16]}...).")

        def _do_install():
            nonlocal temp_addon_path
            try:
                installed = False

                # Priority 1: Use NVDA's official remote installer dialog
                try:
                    import gui.addonGui
                    if hasattr(gui.addonGui, "handleRemoteAddonInstall"):
                        gui.addonGui.handleRemoteAddonInstall(temp_addon_path)
                        installed = True
                        # Handed off to NVDA's modeless installer dialog; do not delete temp file
                        temp_addon_path = None
                    elif hasattr(gui.addonGui, "installAddon"):
                        gui.mainFrame.prePopup()
                        try:
                            if gui.addonGui.installAddon(gui.mainFrame, temp_addon_path):
                                promptUserForRestart = getattr(gui.addonGui, "promptUserForRestart", None)
                                if promptUserForRestart:
                                    wx.CallAfter(promptUserForRestart)
                            installed = True
                        finally:
                            gui.mainFrame.postPopup()
                except Exception as gui_err:
                    logHandler.log.debug(f"OmniTranslate: gui.addonGui installation fallback: {gui_err}")

                # Priority 2: Direct addonHandler bundle installation (headless / robust fallback)
                if not installed:
                    bundle = addonHandler.AddonBundle(temp_addon_path)
                    install_fn = getattr(addonHandler, "installAddonBundle", None) or getattr(addonHandler, "installAddonPackage", None)
                    if not install_fn:
                        raise AttributeError("Neither installAddonBundle nor installAddonPackage found in addonHandler")

                    try:
                        install_fn(bundle)
                    finally:
                        if hasattr(bundle, "close"):
                            try:
                                bundle.close()
                            except Exception:
                                pass
                        del bundle

                    # Prompt user to restart NVDA
                    try:
                        import gui.addonGui
                        promptUserForRestart = getattr(gui.addonGui, "promptUserForRestart", None)
                        if promptUserForRestart:
                            wx.CallAfter(promptUserForRestart)
                        else:
                            gui.messageBox(
                                _("OmniTranslate has been updated successfully.\nPlease restart NVDA for changes to take effect."),
                                _("OmniTranslate Update"),
                                wx.OK | wx.ICON_INFORMATION,
                                gui.mainFrame
                            )
                    except Exception:
                        ui.message(_("OmniTranslate updated. Please restart NVDA."))
                    installed = True

            except Exception as inst_err:
                logHandler.log.error(f"OmniTranslate: Installation failed: {inst_err}")
                ui.message(f"{_('OmniTranslate Update Error:')} {inst_err}")
            finally:
                try:
                    if temp_addon_path and os.path.exists(temp_addon_path):
                        os.remove(temp_addon_path)
                        os.rmdir(os.path.dirname(temp_addon_path))
                except Exception:
                    pass

        wx.CallAfter(_do_install)
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Failed downloading update: {e}")
        wx.CallAfter(ui.message, f"{_('OmniTranslate: Failed to download update.')} {e}")
        if temp_addon_path:
            try:
                if os.path.exists(temp_addon_path):
                    os.remove(temp_addon_path)
                os.rmdir(os.path.dirname(temp_addon_path))
            except Exception:
                pass


def start_update_checker_service():
    """Initializes the background update checker with a startup delay."""
    if getattr(globalVars.appArgs, "secure", False) or getattr(globalVars.appArgs, "secureMode", False):
        logHandler.log.debug("OmniTranslate: Update checker skipped on secure desktop.")
        return
    wx.CallLater(10000, lambda: threading.Thread(target=check_for_updates_background, daemon=True).start())
