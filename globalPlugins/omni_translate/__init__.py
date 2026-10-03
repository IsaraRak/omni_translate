# -*- coding: utf-8 -*-
# OmniTranslate for NVDA - Main Entry Point & Gesture Router
# Author: Isara Watthanawirojkul

import globalPluginHandler
import globalVars
import ui
import api
import textInfos
import threading
import time
import ctypes
import json
import os
import re
import urllib.request
import urllib.parse
import html
import wx
import gui
from gui.settingsDialogs import NVDASettingsDialog
import logHandler
import tones
import addonHandler
import inputCore
import keyboardHandler
import controlTypes
import speech
from . import docHandler
from . import offlineEngine
from . import settingsDialogs
from . import updateChecker

addonHandler.initTranslation()

# Ensure backward compatibility alias for installAddonBundle
if hasattr(addonHandler, "installAddonBundle") and not hasattr(addonHandler, "installAddonPackage"):
    try:
        addonHandler.installAddonPackage = addonHandler.installAddonBundle
    except Exception:
        pass


def is_secure_mode():
    """Checks if NVDA is running in secure mode (lock screen, UAC, logon screen, or --secure flag)."""
    return bool(
        getattr(globalVars.appArgs, "secure", False)
        or getattr(globalVars.appArgs, "secureMode", False)
    )


def normalize_lang(code):
    if isinstance(code, list):
        code = code[0] if code else ""
    if not code or not isinstance(code, str):
        return ""
    code = code.lower().strip()
    if code in ("zh-cn", "zh-hans", "zh"):
        return "zh-cn"
    if code in ("zh-tw", "zh-hant"):
        return "zh-tw"
    if code in ("iw", "he"):
        return "he"
    return code.split("-")[0]


def is_html_error_response(content):
    """Detects Google Front End / Anti-Abuse infrastructure error pages (HTTP 500 / 429 HTML).
    Specifically targets internal error signatures while ensuring zero false positives for user text
    containing normal words like 'Error', 'Error 500', or programming error messages.
    """
    if not content or not isinstance(content, str):
        return False
    lower = content.lower()
    if any(sig in lower for sig in (
        "id=\"af-error-page\"",
        "id='af-error-page'",
        "id=\"af-error-container\"",
        "id='af-error-container'",
        '<!-- "> \'> -->',
        "<title>error 500 (server error)!!1</title>",
        "<title>error 429",
        "<title>error 403",
        "//www.google.com/images/errors/robot.png",
        "images/errors/robot.png",
    )):
        return True
    stripped = content.strip().lower()
    if (stripped.startswith("<!doctype") or stripped.startswith("<html")) and ("#af-error" in stripped or "robot.png" in stripped):
        return True
    return False


def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/json,*/*',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        'Referer': 'https://translate.google.com/'
    }


def request_api_endpoint(text, sl, tl, client_type="gtx"):
    params = {
        'client': client_type,
        'sl': sl,
        'tl': tl,
        'dt': 't',
        'ie': 'UTF-8',
        'oe': 'UTF-8',
        'q': text
    }
    data = urllib.parse.urlencode(params).encode('utf-8')
    url = "https://translate.googleapis.com/translate_a/single"
    req = urllib.request.Request(url, data=data, headers=get_headers())
    with urllib.request.urlopen(req, timeout=5.0) as response:
        raw_data = response.read().decode('utf-8')
        if is_html_error_response(raw_data) and not is_html_error_response(text):
            raise Exception("Google API returned infrastructure error page")
        data = json.loads(raw_data)
        translated_text = "".join([part[0] for part in data[0] if part and part[0]])
        if is_html_error_response(translated_text) and not is_html_error_response(text):
            raise Exception("Google API translation payload contains error page")
        detected_src = data[2] if (isinstance(data, list) and len(data) > 2 and isinstance(data[2], str) and data[2]) else sl
        return translated_text, detected_src


def request_clients5_endpoint(text, sl, tl):
    params = {
        'client': 'dict-chrome-ex',
        'sl': sl,
        'tl': tl,
        'q': text
    }
    url = "https://clients5.google.com/translate_a/t?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=5.0) as response:
        raw_data = response.read().decode('utf-8')
        if is_html_error_response(raw_data) and not is_html_error_response(text):
            raise Exception("Google clients5 API returned infrastructure error page")
        data = json.loads(raw_data)
        if isinstance(data, list):
            if data and isinstance(data[0], list):
                translated_text = "".join([part[0] for part in data if isinstance(part, (list, tuple)) and part and part[0]])
                detected_src = data[0][1] if len(data[0]) > 1 and isinstance(data[0][1], str) else sl
                if is_html_error_response(translated_text) and not is_html_error_response(text):
                    raise Exception("Google clients5 API translation payload contains error page")
                return translated_text, detected_src
            elif data and isinstance(data[0], str):
                translated_text = "".join(data)
                return translated_text, sl
        elif isinstance(data, str):
            return data, sl
        raise Exception("Unexpected response format from clients5 endpoint")


def request_web_fallback(text, sl, tl):
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.google.com/m?sl={sl}&tl={tl}&hl=en&q={encoded_text}"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=5.0) as response:
        html_content = response.read().decode('utf-8', errors='ignore')
        if is_html_error_response(html_content) and not is_html_error_response(text):
            raise Exception("Google Web Engine returned infrastructure error page")
        match = re.search(r'<div class="result-container">(.*?)</div>', html_content, re.DOTALL)
        if match:
            raw_html = match.group(1).replace('<br>', '\n').replace('<br/>', '\n')
            translated_text = html.unescape(raw_html.strip())
            if is_html_error_response(translated_text) and not is_html_error_response(text):
                raise Exception("Google Web Engine translation payload contains error page")
            return translated_text, sl
        raise Exception("Unable to extract translation from Web Engine")


def translate_single_chunk(text, sl, tl):
    try:
        return request_api_endpoint(text, sl, tl, "gtx")
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: gtx endpoint failed: {e}")
        try:
            return request_clients5_endpoint(text, sl, tl)
        except Exception as e2:
            logHandler.log.debug(f"OmniTranslate: clients5 endpoint failed: {e2}")
            try:
                return request_api_endpoint(text, sl, tl, "dict-chrome-ex")
            except Exception as e3:
                logHandler.log.debug(f"OmniTranslate: dict-chrome-ex endpoint failed: {e3}")
                return request_web_fallback(text, sl, tl)


def normalize_newlines(text):
    """Normalizes all platform-specific and Unicode newline variants to standard newline."""
    if not text or not isinstance(text, str):
        return ""
    return (
        text.replace('\r\n', '\n')
            .replace('\r', '\n')
            .replace('\x0b', '\n')
            .replace('\x0c', '\n')
            .replace('\u2028', '\n')
            .replace('\u2029', '\n')
    )


def translate_query(text, sl, tl):
    if not text or not isinstance(text, str) or not text.strip():
        return "", sl

    normalized = normalize_newlines(text)
    if '\n' not in normalized:
        return translate_single_chunk(normalized.strip(), sl, tl)

    # Fast path: translate entire multiline chunk directly in a single request (preserves internal line breaks)
    try:
        res, det = translate_single_chunk(normalized.strip(), sl, tl)
        if res and res.strip():
            return res, det
    except Exception as ex:
        logHandler.log.debug(f"OmniTranslate: direct multiline chunk translate failed, falling back line-by-line: {ex}")

    # Fallback: line-by-line translation
    lines = normalized.split('\n')
    translated_lines = []
    overall_detected = sl

    for line in lines:
        line_str = line.strip()
        if not line_str:
            translated_lines.append("")
            continue
        res_line, det_line = translate_single_chunk(line_str, sl, tl)
        if det_line and det_line != "auto" and overall_detected in ("auto", sl):
            overall_detected = det_line
        translated_lines.append(res_line)

    return "\r\n".join(translated_lines), overall_detected


def get_swap_language(primary_target, secondary_lang):
    """Determines the alternate swap language for Smart Bidirectional translation.
    Returns secondary_lang if distinct from primary_target; otherwise returns None
    so that translation translates strictly to primary_target without swapping.
    """
    norm_pri = normalize_lang(primary_target)
    norm_sec = normalize_lang(secondary_lang)
    if norm_sec and norm_pri != norm_sec:
        return secondary_lang
    return None


def execute_translation(text, sl, tl):
    cfg = settingsDialogs.load_config()
    mode = cfg.get("translationMode", "online")
    secondary_lang = cfg.get("sourceLang", "en")
    is_auto = cfg.get("autoDetect", True)
    primary_target = tl
    swap_target = get_swap_language(primary_target, secondary_lang)

    # 1. Offline Mode Only
    if mode == "offline":
        selected_model = cfg.get("offlineModel", "none")
        if selected_model == "none" or not selected_model:
            installed = offlineEngine.get_installed_offline_models()
            if installed:
                selected_model = installed[0]
            else:
                raise Exception(_("No offline models installed. Please install a language model in Settings."))

        supp_info = offlineEngine.get_model_supported_languages(selected_model)
        is_multilingual = supp_info.get("is_multilingual", True)

        if is_multilingual and is_auto and swap_target:
            detected_src = offlineEngine.detect_text_language(text, hint_langs=(primary_target, swap_target))
            norm_det = normalize_lang(detected_src)
            norm_pri = normalize_lang(primary_target)

            if norm_det == norm_pri:
                translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=primary_target, tgt_lang=swap_target)
                return translated_text, detected_src, swap_target

            src = detected_src if detected_src else swap_target
            translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=src, tgt_lang=primary_target)
            return translated_text, detected_src, primary_target
        elif is_multilingual and is_auto:
            detected_src = offlineEngine.detect_text_language(text, hint_langs=(primary_target,))
            translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=detected_src or primary_target, tgt_lang=primary_target)
            return translated_text, detected_src, primary_target
        else:
            src = supp_info.get("src", ["en"])[0] if not is_multilingual else (cfg.get("sourceLang", "en") if sl == "auto" else sl)
            tgt = supp_info.get("tgt", [tl])[0] if not is_multilingual else tl
            translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=src, tgt_lang=tgt)
            return translated_text, "offline", tgt

    # 2. Online Mode with Auto-Fallback (Smart Bidirectional Translation)
    # Pre-detect source language locally in 0.1ms to eliminate redundant network round-trips
    target_to_use = primary_target
    expected_src = sl
    if is_auto and swap_target:
        try:
            local_src = offlineEngine.detect_text_language(text, hint_langs=(primary_target, swap_target))
            if local_src:
                norm_local = normalize_lang(local_src)
                norm_pri = normalize_lang(primary_target)
                if norm_local == norm_pri:
                    # Input text matches target language; route directly to swap target in a single HTTP request!
                    target_to_use = swap_target
                    expected_src = primary_target
                else:
                    expected_src = local_src
        except Exception:
            pass

    src_query = "auto" if is_auto else sl

    try:
        translated_text, detected_src = translate_query(text, src_query, target_to_use)
        if is_html_error_response(translated_text) and not is_html_error_response(text):
            raise Exception("Online translation returned Google error page")
        if is_auto and swap_target:
            norm_det = normalize_lang(detected_src)
            norm_target_used = normalize_lang(target_to_use)
            norm_pri = normalize_lang(primary_target)
            norm_swap = normalize_lang(swap_target)

            # Verification 1: If target_to_use was primary_target, but input language matches primary_target:
            # Swap target and translate to swap_target!
            if norm_target_used == norm_pri and norm_det == norm_pri:
                swap_text, swap_detected = translate_query(text, "auto", swap_target)
                if is_html_error_response(swap_text) and not is_html_error_response(text):
                    raise Exception("Online translation swap returned Google error page")
                return swap_text, (swap_detected or detected_src or primary_target), swap_target

            # Verification 2: If we pre-routed to swap_target, but Google detected that input language was NOT primary_target:
            # (Pre-detection false positive): re-route and translate to primary_target!
            elif norm_target_used == norm_swap and norm_det != norm_pri and norm_det and norm_det != "auto":
                orig_text, orig_detected = translate_query(text, "auto", primary_target)
                if is_html_error_response(orig_text) and not is_html_error_response(text):
                    raise Exception("Online translation correction returned Google error page")
                return orig_text, (orig_detected or detected_src), primary_target

        return translated_text, (detected_src or expected_src), target_to_use
    except Exception as online_err:
        logHandler.log.warning(f"OmniTranslate: Online translation failed, checking offline fallback: {online_err}")
        installed = offlineEngine.get_installed_offline_models()
        if not installed:
            raise Exception(_("Online translation failed and no offline model is installed."))

        active_model = cfg.get("offlineModel", installed[0])
        if active_model not in installed:
            active_model = installed[0]

        supp_info = offlineEngine.get_model_supported_languages(active_model)
        is_multilingual = supp_info.get("is_multilingual", True)

        try:
            if is_multilingual and is_auto and swap_target:
                detected_src = offlineEngine.detect_text_language(text, hint_langs=(primary_target, swap_target))
                norm_det = normalize_lang(detected_src)
                norm_pri = normalize_lang(primary_target)

                if norm_det == norm_pri:
                    translated_text = offlineEngine.translate_offline(text, active_model, src_lang=primary_target, tgt_lang=swap_target)
                    return translated_text, "offline-fallback", swap_target

                src = detected_src if detected_src else swap_target
                translated_text = offlineEngine.translate_offline(text, active_model, src_lang=src, tgt_lang=primary_target)
                return translated_text, "offline-fallback", primary_target

            fallback_src = supp_info.get("src", ["en"])[0] if not is_multilingual else (cfg.get("sourceLang", "en") if sl == "auto" else sl)
            fallback_tgt = supp_info.get("tgt", [tl])[0] if not is_multilingual else tl
            translated_text = offlineEngine.translate_offline(text, active_model, src_lang=fallback_src, tgt_lang=fallback_tgt)
            return translated_text, "offline-fallback", fallback_tgt
        except Exception as offline_err:
            logHandler.log.warning(f"OmniTranslate: Offline fallback failed: {offline_err}")
            raise Exception(_("Online translation failed, and offline fallback failed: {err}").format(err=str(offline_err)))


def _release_modifiers():
    """Releases physical modifier keys (Shift, Ctrl, Alt, Win) if currently held to prevent keystroke distortion."""
    if is_secure_mode():
        return
    try:
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002
        for vk in (0x10, 0xA0, 0xA1, 0x11, 0xA2, 0xA3, 0x12, 0xA4, 0xA5, 0x5B, 0x5C):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def _wait_for_modifiers_released(timeout_ms=50):
    """Waits briefly for physical modifier keys to be released when a direct shortcut is used."""
    if is_secure_mode():
        return
    try:
        user32 = ctypes.windll.user32
        vks = (0x10, 0x11, 0x12, 0x5B, 0x5C)
        start = time.time()
        max_duration = timeout_ms / 1000.0
        while time.time() - start < max_duration:
            if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in vks):
                break
            time.sleep(0.005)
    except Exception:
        pass


def send_copy_message_api(target_hwnd=None):
    """Sends a direct WM_COPY (0x0301) message to the target window/control.
    Executes in microseconds via Win32 API without firing global keyboard hooks
    or triggering external clipboard announcement add-ons.
    Returns True if the message was dispatched cleanly.
    """
    if is_secure_mode():
        return False
    try:
        user32 = ctypes.windll.user32
        if not target_hwnd:
            target_hwnd = user32.GetForegroundWindow()
        if target_hwnd:
            SMTO_ABORTIFHUNG = 0x0002
            res = ctypes.c_ulong()
            user32.SendMessageTimeoutW(target_hwnd, 0x0301, 0, 0, SMTO_ABORTIFHUNG, 60, ctypes.byref(res))
            return True
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: send_copy_message_api error: {e}")
    return False


def send_paste_message_api(target_hwnd=None):
    """Sends a direct WM_PASTE (0x0302) message to the target window/control.
    Executes in microseconds via Win32 API without firing global keyboard hooks.
    Returns True if the message was dispatched cleanly.
    """
    if is_secure_mode():
        return False
    try:
        user32 = ctypes.windll.user32
        if not target_hwnd:
            target_hwnd = user32.GetForegroundWindow()
        if target_hwnd:
            SMTO_ABORTIFHUNG = 0x0002
            res = ctypes.c_ulong()
            user32.SendMessageTimeoutW(target_hwnd, 0x0302, 0, 0, SMTO_ABORTIFHUNG, 60, ctypes.byref(res))
            return True
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: send_paste_message_api error: {e}")
    return False





def send_paste_input():
    """Sends Ctrl+V to the active window safely across standard controls, games, and web chat boxes."""
    if is_secure_mode():
        return
    try:
        _release_modifiers()

        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_V = 0x56
        KEYEVENTF_KEYUP = 0x0002
        scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
        scan_v = user32.MapVirtualKeyW(VK_V, 0)

        # 1. Ctrl Down
        user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
        time.sleep(0.025)

        # 2. V Down & Up
        user32.keybd_event(VK_V, scan_v, 0, 0)
        time.sleep(0.035)
        user32.keybd_event(VK_V, scan_v, KEYEVENTF_KEYUP, 0)
        time.sleep(0.025)

        # 3. Ctrl Up
        user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: send_paste_input error: {e}")


def send_copy_input():
    """Sends Ctrl+C to the active window safely across standard controls, games, and web chat boxes."""
    if is_secure_mode():
        return
    try:
        _release_modifiers()

        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_C = 0x43
        KEYEVENTF_KEYUP = 0x0002
        scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
        scan_c = user32.MapVirtualKeyW(VK_C, 0)

        # 1. Ctrl Down
        user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
        time.sleep(0.025)

        # 2. C Down & Up
        user32.keybd_event(VK_C, scan_c, 0, 0)
        time.sleep(0.035)
        user32.keybd_event(VK_C, scan_c, KEYEVENTF_KEYUP, 0)
        time.sleep(0.025)

        # 3. Ctrl Up
        user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: send_copy_input error: {e}")


def _snapshot_clipboard():
    """Captures a byte snapshot of all global memory formats currently in the Windows clipboard.
    Preserves copied files (CF_HDROP), text, HTML, and other application formats.
    """
    snapshot = {}
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.GetClipboardData.argtypes = [ctypes.c_uint]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalSize.restype = ctypes.c_size_t
        kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

        for _attempt in range(5):
            if user32.OpenClipboard(0):
                try:
                    fmt = user32.EnumClipboardFormats(0)
                    while fmt != 0:
                        if fmt not in (2, 14):  # Skip GDI handles (CF_BITMAP, CF_ENHMETAFILE)
                            try:
                                hData = user32.GetClipboardData(fmt)
                                if hData:
                                    sz = kernel32.GlobalSize(hData)
                                    if 0 < sz < 50 * 1024 * 1024:  # Under 50MB safety ceiling
                                        pData = kernel32.GlobalLock(hData)
                                        if pData:
                                            try:
                                                snapshot[fmt] = ctypes.string_at(pData, sz)
                                            finally:
                                                kernel32.GlobalUnlock(hData)
                            except Exception:
                                pass
                        fmt = user32.EnumClipboardFormats(fmt)
                    break
                finally:
                    user32.CloseClipboard()
            time.sleep(0.01)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _snapshot_clipboard error: {e}")
    return snapshot


def _restore_clipboard(snapshot=None, initial_text=""):
    """Restores clipboard to its exact state prior to copy probe.
    If snapshot contained files (CF_HDROP), text, or rich data, restores all formats byte-for-byte.
    If snapshot was empty and initial_text was empty, cleanses the clipboard via user32.EmptyClipboard.
    """
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.restype = ctypes.c_void_p
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]

        # 1. Restore from binary snapshot (preserves CF_HDROP files, HTML, custom formats)
        if snapshot:
            for _attempt in range(5):
                if user32.OpenClipboard(0):
                    try:
                        user32.EmptyClipboard()
                        for fmt, raw_data in snapshot.items():
                            hMem = kernel32.GlobalAlloc(0x0002, len(raw_data))  # GMEM_MOVEABLE
                            if not hMem:
                                continue
                            success = False
                            pMem = kernel32.GlobalLock(hMem)
                            if pMem:
                                try:
                                    ctypes.memmove(pMem, raw_data, len(raw_data))
                                finally:
                                    kernel32.GlobalUnlock(hMem)
                                if user32.SetClipboardData(fmt, hMem):
                                    success = True
                            if not success:
                                kernel32.GlobalFree(hMem)
                        return
                    finally:
                        user32.CloseClipboard()
                time.sleep(0.01)

        # 2. Fallback to initial_text if snapshot had no binary formats
        if initial_text and initial_text.strip():
            if not set_clipboard_text(initial_text):
                try:
                    import wx
                    wx.CallAfter(api.copyToClip, initial_text)
                except Exception:
                    pass
            return

        # 3. If completely empty, ensure clipboard is cleansed
        for _attempt in range(5):
            if user32.OpenClipboard(0):
                try:
                    user32.EmptyClipboard()
                    break
                finally:
                    user32.CloseClipboard()
            time.sleep(0.01)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _restore_clipboard error: {e}")


def set_clipboard_text(text):
    """Synchronously writes unicode text directly to the Windows clipboard with retries.
    Returns True if successfully written, False otherwise.
    Safe to call from any background worker thread without depending on NVDA MainThread message loop.
    """
    if not isinstance(text, str) or not text:
        return False
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.restype = ctypes.c_void_p
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]

        raw_bytes = text.encode("utf-16le") + b"\x00\x00"
        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13

        for _attempt in range(10):
            if user32.OpenClipboard(0):
                try:
                    user32.EmptyClipboard()
                    hMem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_bytes))
                    if hMem:
                        pMem = kernel32.GlobalLock(hMem)
                        if pMem:
                            try:
                                ctypes.memmove(pMem, raw_bytes, len(raw_bytes))
                            finally:
                                kernel32.GlobalUnlock(hMem)
                            if user32.SetClipboardData(CF_UNICODETEXT, hMem):
                                return True
                        kernel32.GlobalFree(hMem)
                finally:
                    user32.CloseClipboard()
            time.sleep(0.01)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: set_clipboard_text error: {e}")
    return False


def has_translatable_text(text):
    """Checks if text contains translatable language characters (letters or numbers).
    Prevents meaningless translation and replacement of pure symbols, punctuation, or mask characters (e.g. '####', '****', '---').
    """
    if not text or not isinstance(text, str):
        return False
    return any(c.isalnum() for c in text)


MAX_CHUNK_CHARS = 3000
MAX_TOTAL_TRANSLATE_CHARS = 50000


def _split_oversized_text(text, max_chunk_size=MAX_CHUNK_CHARS):
    """Splits a single oversized paragraph into smaller (sub_content, sub_delim) units at sentence or word boundaries."""
    sub_units = []
    rem = text
    while len(rem) > max_chunk_size:
        cand = rem[:max_chunk_size]
        # 1. Sentence-ending punctuation followed by whitespace or CJK sentence-end
        matches = list(re.finditer(r'([.!?][\'"”’)]?)(\s+)|([。！？])(\s*)', cand))
        if matches and matches[-1].end() > max_chunk_size * 0.3:
            m = matches[-1]
            if m.group(1):
                sub_content = rem[:m.end(1)]
                sub_delim = m.group(2)
                rem = rem[m.end():]
            else:
                sub_content = rem[:m.end(3)]
                sub_delim = m.group(4)
                rem = rem[m.end():]
            sub_units.append((sub_content, sub_delim))
            continue

        # 2. Single newline
        nl_idx = cand.rfind('\n')
        if nl_idx > max_chunk_size * 0.3:
            sub_units.append((rem[:nl_idx], '\n'))
            rem = rem[nl_idx + 1:]
            continue

        # 3. Word boundary (space)
        sp_idx = cand.rfind(' ')
        if sp_idx > max_chunk_size * 0.3:
            sub_units.append((rem[:sp_idx], ' '))
            rem = rem[sp_idx + 1:]
            continue

        # 4. Hard cut if no natural boundary found
        sub_units.append((cand, ''))
        rem = rem[max_chunk_size:]

    if rem:
        sub_units.append((rem, ''))
    return sub_units


def create_translation_chunks(text, max_chunk_size=MAX_CHUNK_CHARS, max_total_limit=MAX_TOTAL_TRANSLATE_CHARS):
    """Segments text into natural (content, delimiter) chunks preserving paragraph breaks and layout.
    Enforces a generous safety ceiling (50,000 characters) while cleanly breaking oversized documents
    into contextual chunks (~3,000 chars) for robust online and offline translation without timeouts."""
    if not text or not isinstance(text, str):
        return [], False

    was_truncated = False
    if len(text) > max_total_limit:
        cut_cand = text[:max_total_limit]
        last_break = max(cut_cand.rfind('\n\n'), cut_cand.rfind('\n'), cut_cand.rfind('. '), cut_cand.rfind(' '))
        if last_break > max_total_limit * 0.8:
            text = text[:last_break].rstrip()
        else:
            text = cut_cand
        was_truncated = True

    # If within single chunk size, return directly
    if len(text) <= max_chunk_size:
        return [(text, "")], was_truncated

    # Split text into (content, delimiter) pairs preserving paragraph separators (\r?\n\s*\r?\n+)
    para_splits = re.split(r'(\r?\n\s*\r?\n+)', text)
    units = []
    i = 0
    while i < len(para_splits):
        content = para_splits[i]
        delim = para_splits[i + 1] if i + 1 < len(para_splits) else ""
        if content or delim:
            if len(content) > max_chunk_size:
                sub_units = _split_oversized_text(content, max_chunk_size)
                if sub_units:
                    for s_idx, (sc, sd) in enumerate(sub_units):
                        if s_idx == len(sub_units) - 1:
                            units.append((sc, delim))
                        else:
                            units.append((sc, sd))
                else:
                    units.append((content, delim))
            else:
                units.append((content, delim))
        i += 2

    chunks = []
    curr_parts = []
    curr_len = 0
    pending_delim = ""

    for content, delim in units:
        if not curr_parts:
            curr_parts.append(content)
            curr_len = len(content)
            pending_delim = delim
        else:
            if curr_len + len(pending_delim) + len(content) <= max_chunk_size:
                curr_parts.append(pending_delim)
                curr_parts.append(content)
                curr_len += len(pending_delim) + len(content)
                pending_delim = delim
            else:
                chunks.append(("".join(curr_parts), pending_delim))
                curr_parts = [content]
                curr_len = len(content)
                pending_delim = delim

    if curr_parts:
        chunks.append(("".join(curr_parts), pending_delim))

    return chunks, was_truncated


def _is_protected_object(obj):
    """Checks if an NVDA object or its ancestors represent a protected/password field."""
    if not obj:
        return False
    try:
        curr = obj
        for _depth in range(5):
            if not curr:
                break
            states = getattr(curr, "states", set())
            role = getattr(curr, "role", None)
            if controlTypes.State.PROTECTED in states:
                return True
            pw_role = getattr(controlTypes.Role, "PASSWORDEDIT", None)
            if pw_role is not None and role == pw_role:
                return True

            # Check accessible name, description, or roleText for password keywords
            name = (getattr(curr, "name", "") or "").lower()
            desc = (getattr(curr, "description", "") or "").lower()
            role_text = (getattr(curr, "roleText", "") or "").lower()
            pw_keywords = ("password", "passcode", "passwd", "pin code", "รหัสผ่าน", "secret", "pwd")
            if any(kw in name or kw in desc or kw in role_text for kw in pw_keywords):
                if _is_editable_object(curr) or role in (
                    getattr(controlTypes.Role, "EDITABLETEXT", None),
                    getattr(controlTypes.Role, "PASSWORDEDIT", None),
                    getattr(controlTypes.Role, "DOCUMENT", None),
                    getattr(controlTypes.Role, "TEXTFRAME", None),
                    getattr(controlTypes.Role, "WINDOW", None),
                ):
                    return True

            # Direct UIA IsPassword property check (30019 = UIA_IsPasswordPropertyId)
            try:
                uia_elem = getattr(curr, "UIAElement", None)
                if uia_elem and uia_elem.GetCurrentPropertyValue(30019):
                    return True
            except Exception:
                pass

            # Win32 ES_PASSWORD or EM_GETPASSWORDCHAR check
            hwnd = getattr(curr, "windowHandle", None)
            if hwnd:
                try:
                    user32 = ctypes.windll.user32
                    style = user32.GetWindowLongW(hwnd, -16)
                    if style & 0x0020:  # ES_PASSWORD
                        return True
                    if user32.SendMessageW(hwnd, 0x00D2, 0, 0) != 0:  # EM_GETPASSWORDCHAR
                        return True
                except Exception:
                    pass

            curr = getattr(curr, "parent", None)
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _is_protected_object error: {e}")
    return False


def _is_console_or_terminal(obj):
    """Checks if an NVDA object belongs to a console, terminal, or command line window."""
    if not obj:
        return False
    try:
        role = getattr(obj, "role", None)
        terminal_role = getattr(controlTypes.Role, "TERMINAL", None)
        if terminal_role is not None and role == terminal_role:
            return True

        app_name = (getattr(obj, "appModule", None) and getattr(obj.appModule, "appName", "")) or ""
        if app_name.lower() in ("cmd", "powershell", "windowsterminal", "mintty", "putty", "conhost", "wt"):
            return True

        win_class = getattr(obj, "windowClassName", "") or ""
        if win_class in ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS"):
            return True
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _is_console_or_terminal error: {e}")
    return False


def _is_copy_probe_allowed(obj):
    """Determines if Copy Probe (sending WM_COPY / Ctrl+C) is safe to execute on the active object.
    Strictly suppresses copy probing on Windows Desktop, File Explorer, Taskbar, Start Menu,
    and non-text UI elements (buttons, lists, tree views, menus) to prevent accidental
    file/shortcut copying or unwanted clipboard announcer triggers.
    """
    if not obj:
        return False
    try:
        # 1. Reject Windows Shell and Explorer processes (Desktop, File Explorer, Taskbar, Start Menu)
        app_name = (getattr(obj, "appModule", None) and getattr(obj.appModule, "appName", "")) or ""
        if not app_name:
            app_name = (getattr(obj, "processName", "") or "").lower().replace(".exe", "")
        if app_name.lower() in ("explorer", "shellexperiencehost", "searchhost", "startmenuexperiencehost"):
            return False

        # 2. Reject known Desktop, Shell, and Explorer window classes
        win_class = getattr(obj, "windowClassName", "") or ""
        if win_class in ("Progman", "WorkerW", "Shell_TrayWnd", "ShellTabWindowClass", "DirectUIHWND", "SysListView32"):
            return False

        # Affirmative bypass for messaging, chat, and communication applications
        # WhatsApp, Telegram, Discord, LINE, etc. often use Chromium/Electron/custom windows where NVDA
        # may report container roles like POPUPMENU or FRAME for the chat view.
        app_name_lower = app_name.lower()
        chat_keywords = ("whatsapp", "telegram", "discord", "line", "messenger", "slack", "teams", "skype", "wechat", "signal", "element", "viber", "kakao")
        if any(chat in app_name_lower for chat in chat_keywords):
            if win_class != "#32768":
                return True

        # 3. Reject non-text UI roles
        role = getattr(obj, "role", None)
        blocked_roles = {
            controlTypes.Role.DESKTOPPANE,
            controlTypes.Role.LIST,
            controlTypes.Role.LISTITEM,
            controlTypes.Role.TREEVIEW,
            controlTypes.Role.TREEVIEWITEM,
            controlTypes.Role.BUTTON,
            controlTypes.Role.CHECKBOX,
            controlTypes.Role.RADIOBUTTON,
            controlTypes.Role.MENUBAR,
            controlTypes.Role.MENUITEM,
            controlTypes.Role.TOOLBAR,
            controlTypes.Role.STATUSBAR,
            controlTypes.Role.SCROLLBAR,
            controlTypes.Role.PROGRESSBAR,
            controlTypes.Role.TOOLTIP,
            controlTypes.Role.TABCONTROL,
            controlTypes.Role.SLIDER,
        }
        if role in blocked_roles:
            return False

        # Reject popup menus only if it is a true Win32 context menu (#32768)
        if role == controlTypes.Role.POPUPMENU and win_class == "#32768":
            return False

        # 4. Reject read-only browse mode virtual buffers
        treeInterceptor = getattr(obj, "treeInterceptor", None)
        if treeInterceptor and not getattr(treeInterceptor, "passThrough", False):
            return False

        return True
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _is_copy_probe_allowed error: {e}")
        return False


def _is_clipboard_sensitive():
    """Checks if the system clipboard was populated by a password manager or marked sensitive."""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.GetClipboardData.argtypes = [ctypes.c_uint]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

        cf_ignore = user32.RegisterClipboardFormatW("Clipboard Viewer Ignore")
        cf_exclude = user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing")
        cf_can_history = user32.RegisterClipboardFormatW("CanIncludeInClipboardHistory")
        if user32.OpenClipboard(None):
            try:
                if cf_ignore and user32.IsClipboardFormatAvailable(cf_ignore):
                    return True
                if cf_exclude and user32.IsClipboardFormatAvailable(cf_exclude):
                    return True
                if cf_can_history and user32.IsClipboardFormatAvailable(cf_can_history):
                    hData = user32.GetClipboardData(cf_can_history)
                    if hData:
                        pData = kernel32.GlobalLock(hData)
                        if pData:
                            try:
                                val = ctypes.cast(pData, ctypes.POINTER(ctypes.c_uint32)).contents.value
                                if val == 0:
                                    return True
                            finally:
                                kernel32.GlobalUnlock(hData)
            finally:
                user32.CloseClipboard()
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _is_clipboard_sensitive error: {e}")
    return False


def _is_editable_object(obj):
    """Checks if an NVDA object is in an editable context.
    Returns True ONLY if there is affirmative evidence that the object is editable
    and not marked read-only.
    """
    if not obj:
        return False
    try:
        states = getattr(obj, "states", set())

        # 1. If marked READONLY (and not explicitly contentEditable), it is definitely NOT editable
        if controlTypes.State.READONLY in states and not getattr(obj, "isContentEditable", False):
            return False

        # 2. Affirmative editable indicators (Gecko / Chromium / Web / UIA)
        if getattr(obj, "isContentEditable", False) or getattr(obj, "isEditable", False):
            return True

        # 3. Standard NVDA State.EDITABLE
        if controlTypes.State.EDITABLE in states:
            return True

        role = getattr(obj, "role", None)

        # 4. Standard NVDA Role.EDITABLETEXT
        if role == controlTypes.Role.EDITABLETEXT:
            return True

        # 5. Check Word Processors & Office Editors (Microsoft Word, Outlook Mail, Excel, LibreOffice)
        app_name = (getattr(getattr(obj, "appModule", None), "appName", "") or "").lower()
        if not app_name:
            app_name = (getattr(obj, "processName", "") or "").lower().replace(".exe", "")

        win_class = (getattr(obj, "windowClassName", "") or "").lower()

        # Microsoft Word document canvas (_WwG), Word window frames, Outlook email editor
        if app_name in ("winword", "outlook") or win_class in ("_wwg", "_wwb", "_wwf", "opusapp"):
            if controlTypes.State.READONLY not in states:
                return True

        # LibreOffice / Apache OpenOffice Writer & Calc
        if app_name in ("soffice.bin", "soffice") and win_class in ("salframe", "vclsalframe"):
            if controlTypes.State.READONLY not in states:
                return True

        # Microsoft Excel spreadsheet / cell editing
        if app_name == "excel" or win_class.startswith("excel"):
            if controlTypes.State.READONLY not in states:
                return True

        # 6. Chat and messaging applications (WhatsApp, Telegram, Discord, LINE, Messenger, Slack, Teams, Skype, etc.)
        chat_keywords = ("whatsapp", "telegram", "discord", "line", "messenger", "slack", "teams", "skype", "wechat", "signal", "element", "viber", "kakao")
        if any(chat in app_name for chat in chat_keywords):
            if controlTypes.State.READONLY not in states and win_class != "#32768" and role != controlTypes.Role.MENUITEM:
                return True

        # 7. Standard Win32 Edit / RichEdit / Scintilla controls
        if any(cls in win_class for cls in ("edit", "richedit", "scintilla", "textarea")):
            hwnd = getattr(obj, "windowHandle", None)
            if hwnd:
                try:
                    user32 = ctypes.windll.user32
                    GWL_STYLE = -16
                    ES_READONLY = 0x0800
                    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    if style & ES_READONLY:
                        return False
                except Exception:
                    pass
            return True

        # 8. Java Swing / AWT chat, game channels, and text controls (e.g. MW SunAwtFrame / Minecraft / Java chat clients)
        if app_name == "mw" or win_class in ("sunawtframe", "sunawtdialog"):
            if role not in (controlTypes.Role.BUTTON, controlTypes.Role.MENUITEM, controlTypes.Role.SCROLLBAR, controlTypes.Role.PROGRESSBAR):
                obj_name = (getattr(obj, "name", "") or "").lower()
                if app_name == "mw" or any(k in obj_name for k in ("chat", "channel", "input", "message", "text")):
                    if controlTypes.State.READONLY not in states:
                        return True

        # 9. Default to False: read-only text, chat history, documents, labels, buttons, etc.
        # are non-editable unless proven otherwise.
        return False
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _is_editable_object error: {e}")
    return False


def _get_text_from_object_selection(obj):
    """Attempts to get selected text from an NVDA object or its immediate children."""
    if not obj:
        return None
    try:
        if hasattr(obj, "makeTextInfo"):
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and not info.isCollapsed:
                text = info.text
                if text and text.strip():
                    return text.strip()
    except Exception:
        pass

    # Check first child (e.g., Edit inside ComboBox like Windows Run dialog)
    try:
        child = getattr(obj, "firstChild", None)
        if child and child != obj and hasattr(child, "makeTextInfo"):
            info = child.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and not info.isCollapsed:
                text = info.text
                if text and text.strip():
                    return text.strip()
    except Exception:
        pass

    return None


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("OmniTranslate")

    _gestures = {
        "kb:NVDA+shift+t": "layer",
    }
    __gestures = _gestures

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        NVDASettingsDialog.categoryClasses.append(settingsDialogs.OmniTranslateGeneralSettingsPanel)
        NVDASettingsDialog.categoryClasses.append(settingsDialogs.OmniTranslateOfflineModelsPanel)
        self.current_slot_index = 0
        self._in_layer = False
        self._layer_timer = None
        self._last_translate_time = 0.0
        cfg = settingsDialogs.load_config()
        if cfg.get("translationMode", "online") == "online":
            offlineEngine.on_mode_changed("online")
        if not is_secure_mode():
            try:
                updateChecker.start_update_checker_service()
            except Exception as e:
                logHandler.log.debug(f"OmniTranslate: Error starting update checker: {e}")

    def terminate(self):
        self._exitLayer()
        try:
            offlineEngine.cancel_online_idle_timer()
            offlineEngine.unload_all_models()
        except Exception as e:
            logHandler.log.debug(f"OmniTranslate: Error unloading models on terminate: {e}")
        try:
            NVDASettingsDialog.categoryClasses.remove(settingsDialogs.OmniTranslateGeneralSettingsPanel)
        except Exception:
            pass
        try:
            NVDASettingsDialog.categoryClasses.remove(settingsDialogs.OmniTranslateOfflineModelsPanel)
        except Exception:
            pass
        super(GlobalPlugin, self).terminate()

    def _start_layer_timer(self):
        if self._layer_timer:
            try:
                self._layer_timer.Stop()
            except Exception:
                pass
        self._layer_timer = wx.CallLater(15000, self._layerTimeout)

    def _layerTimeout(self):
        if self._in_layer:
            self._exitLayer()
            tones.beep(250, 35)

    def _exitLayer(self):
        self._in_layer = False
        if self._layer_timer:
            try:
                self._layer_timer.Stop()
            except Exception:
                pass
            self._layer_timer = None

    def getScript(self, gesture):
        if not getattr(self, "_in_layer", False):
            return super(GlobalPlugin, self).getScript(gesture)

        # In layer mode:
        # Ignore modifier keys alone (Shift, Alt, Ctrl, Win, NVDA key)
        if getattr(gesture, "isModifier", False):
            return None

        idents = [i.lower() for i in getattr(gesture, "identifiers", [])]
        vk = getattr(gesture, "vkCode", None)

        is_nvda = getattr(gesture, "isNvda", False)
        is_shift = (
            getattr(gesture, "isShift", False)
            or any("shift" in ident for ident in idents)
        )

        # Check if user pressed the layer gesture again (dynamic routing, universal signal: NVDA+Shift+VK_T, or string identifier)
        is_layer_repeat = False
        try:
            if super(GlobalPlugin, self).getScript(gesture) == self.script_layer:
                is_layer_repeat = True
        except Exception:
            pass

        if not is_layer_repeat:
            if is_nvda and is_shift and vk == 0x54:
                is_layer_repeat = True
            else:
                for ident in idents:
                    if any(k in ident for k in (
                        "nvda+shift+t", "shift+nvda+t",
                        "insert+shift+t", "shift+insert+t"
                    )):
                        is_layer_repeat = True
                        break

        if is_layer_repeat:
            tones.beep(500, 35)
            self._start_layer_timer()
            return lambda g: None

        # User pressed a key in layer mode: exit layer mode
        self._exitLayer()

        # Check Escape key -> cancel layer mode with tone (universal VK_ESCAPE = 0x1B)
        if vk == 0x1B or any("escape" in i for i in idents):
            tones.beep(250, 35)
            return lambda g: None

        # Strictly exclude arrow keys and navigation keys so they NEVER trigger quick slots or translations
        # VK_LEFT (0x25), VK_UP (0x26), VK_RIGHT (0x27), VK_DOWN (0x28),
        # VK_PRIOR (0x21), VK_NEXT (0x22), VK_END (0x23), VK_HOME (0x24), VK_INSERT (0x2D), VK_DELETE (0x2E)
        is_navigation_key = (
            vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x0C)
            or any(
                any(nav in ident for nav in (
                    "up", "down", "left", "right", "uparrow", "downarrow", "leftarrow", "rightarrow",
                    "pageup", "pagedown", "home", "end", "insert", "delete"
                ))
                for ident in idents
            )
        )

        # Check Quick Slots 1 to 10 strictly by numbers 1-0 (main row and numeric keypad)
        slot_target = None
        if not is_navigation_key:
            if vk in (0x31, 0x61): slot_target = 1        # VK_1, VK_NUMPAD1
            elif vk in (0x32, 0x62): slot_target = 2      # VK_2, VK_NUMPAD2
            elif vk in (0x33, 0x63): slot_target = 3      # VK_3, VK_NUMPAD3
            elif vk in (0x34, 0x64): slot_target = 4      # VK_4, VK_NUMPAD4
            elif vk in (0x35, 0x65): slot_target = 5      # VK_5, VK_NUMPAD5
            elif vk in (0x36, 0x66): slot_target = 6      # VK_6, VK_NUMPAD6
            elif vk in (0x37, 0x67): slot_target = 7      # VK_7, VK_NUMPAD7
            elif vk in (0x38, 0x68): slot_target = 8      # VK_8, VK_NUMPAD8
            elif vk in (0x39, 0x69): slot_target = 9      # VK_9, VK_NUMPAD9
            elif vk in (0x30, 0x60): slot_target = 10     # VK_0, VK_NUMPAD0
            else:
                slot_map = {
                    "1": 1, "numpad1": 1, "!": 1, "+": 1,
                    "2": 2, "numpad2": 2, "@": 2,
                    "3": 3, "numpad3": 3, "#": 3,
                    "4": 4, "numpad4": 4, "$": 4,
                    "5": 5, "numpad5": 5, "%": 5,
                    "6": 6, "numpad6": 6, "^": 6,
                    "7": 7, "numpad7": 7, "&": 7,
                    "8": 8, "numpad8": 8, "*": 8,
                    "9": 9, "numpad9": 9, "(": 9,
                    "0": 10, "numpad0": 10, ")": 10,
                }
                # French AZERTY keyboard top-row numbers
                azerty_map = {
                    "&": 1, "é": 2, '"': 3, "'": 4, "(": 5,
                    "-": 6, "è": 7, "_": 8, "ç": 9, "à": 10
                }
                for ident in idents:
                    clean_key = ident.replace("kb:", "").replace("kb(desktop):", "").replace("kb(laptop):", "").strip()
                    base_key = clean_key.split("+")[-1]
                    if not is_shift and base_key in azerty_map:
                        slot_target = azerty_map[base_key]
                        break
                    elif base_key in slot_map:
                        slot_target = slot_map[base_key]
                        break

        if slot_target is not None:
            if is_shift:
                return getattr(self, f"script_srcSlot{slot_target}")
            else:
                return getattr(self, f"script_slot{slot_target}")

        # Check by Universal Virtual Key Code (VK) first - works on ALL keyboard layouts worldwide
        if vk == 0x54:   # VK_T
            return self.script_translate
        elif vk == 0x53: # VK_S
            return self.script_toggleMode
        elif vk == 0x56: # VK_V
            return self.script_openViewer
        elif vk == 0x48: # VK_H
            return self.script_openHistory
        elif vk == 0x4D: # VK_M
            return self.script_toggleSpeech
        elif vk == 0x52: # VK_R
            return self.script_repeatLast
        elif vk == 0x43: # VK_C
            return self.script_copyLast
        elif vk == 0x4F: # VK_O
            return self.script_openSettings
        elif vk == 0x70: # VK_F1
            return self.script_openDoc

        # String identifier fallback
        for ident in idents:
            key = ident.replace("kb:", "").replace("kb(desktop):", "").replace("kb(laptop):", "").strip()
            if key in ("t", "shift+t") or key.endswith("+t"):
                return self.script_translate
            elif key in ("s", "shift+s") or key.endswith("+s"):
                return self.script_toggleMode
            elif key in ("v", "shift+v") or key.endswith("+v"):
                return self.script_openViewer
            elif key in ("h", "shift+h") or key.endswith("+h"):
                return self.script_openHistory
            elif key in ("m", "shift+m") or key.endswith("+m"):
                return self.script_toggleSpeech
            elif key in ("r", "shift+r") or key.endswith("+r"):
                return self.script_repeatLast
            elif key in ("c", "shift+c") or key.endswith("+c"):
                return self.script_copyLast
            elif key in ("o", "shift+o") or key.endswith("+o"):
                return self.script_openSettings
            elif key in ("f1", "shift+f1") or key.endswith("+f1"):
                return self.script_openDoc

        tones.beep(250, 25)
        return super(GlobalPlugin, self).getScript(gesture)


    def get_selected_text_info(self):
        """Returns tuple of (text, is_editable, is_from_selection)."""
        try:
            focus = api.getFocusObject()
            if _is_protected_object(focus):
                return None, False, False

            treeInterceptor = getattr(focus, "treeInterceptor", None)

            # 1. Check treeInterceptor (Virtual Buffer / Browse mode vs Focus mode)
            if treeInterceptor and hasattr(treeInterceptor, "makeTextInfo"):
                try:
                    info = treeInterceptor.makeTextInfo(textInfos.POSITION_SELECTION)
                    if info and not info.isCollapsed:
                        text = info.text.strip()
                        if text:
                            is_editable = False
                            if getattr(treeInterceptor, "passThrough", False) and _is_editable_object(focus):
                                is_editable = True
                            return text, is_editable, True
                except Exception:
                    pass

            # 2. Check focus object directly or child edit control (Run dialog, Notepad, Word, etc.)
            selected_text = _get_text_from_object_selection(focus)
            if selected_text:
                is_editable = _is_editable_object(focus)
                return selected_text, is_editable, True
        except Exception as e:
            logHandler.log.debug(f"OmniTranslate: get_selected_text_info error: {e}")

        return None, False, False

    def get_selected_or_clipboard_text(self):
        focus = api.getFocusObject()
        if _is_protected_object(focus):
            return None
        text, _is_edit, _is_sel = self.get_selected_text_info()
        if not text:
            if _is_clipboard_sensitive():
                return None
            try:
                clip = api.getClipData()
                if clip and clip.strip():
                    return clip.strip()
            except Exception:
                pass
        return text

    def _prepare_translation_context(self):
        """Evaluates focus, security, and text context safely on NVDA's main STA thread.
        Returns tuple of (text, is_editable, is_from_selection, is_console) or None if aborted for security.
        """
        if is_secure_mode():
            tones.beep(200, 70)
            ui.message(_("Translation is disabled on secure screens for security."))
            return None

        focus = api.getFocusObject()
        if _is_protected_object(focus):
            tones.beep(200, 70)
            ui.message(_("Translation disabled in password fields for security."))
            return None

        is_console = _is_console_or_terminal(focus)
        text, is_editable, is_from_selection = self.get_selected_text_info()
        if text is None:
            is_editable = _is_editable_object(focus)

        # Record target window handle for direct API messaging (WM_COPY / WM_PASTE)
        target_hwnd = getattr(focus, "windowHandle", None) or ctypes.windll.user32.GetForegroundWindow()
        self._target_hwnd = target_hwnd

        # Smart fallback replacement guard for inaccessible controls / games / custom UI (e.g. MW SunAwtFrame)
        # Disallow probed replacement if in virtual buffer browse mode, explicitly read-only, or non-input roles (menus, buttons, document)
        treeInterceptor = getattr(focus, "treeInterceptor", None)
        in_browse_mode = bool(treeInterceptor and not getattr(treeInterceptor, "passThrough", False))
        states = getattr(focus, "states", set())
        role = getattr(focus, "role", None)
        win_class = getattr(focus, "windowClassName", "") or ""
        non_input_roles = {
            controlTypes.Role.DOCUMENT,
            controlTypes.Role.STATICTEXT,
            controlTypes.Role.MENUITEM,
            controlTypes.Role.BUTTON,
            controlTypes.Role.TOOLBAR,
            controlTypes.Role.STATUSBAR,
            controlTypes.Role.TOOLTIP,
            controlTypes.Role.SCROLLBAR,
            controlTypes.Role.PROGRESSBAR,
        }
        is_real_menu = (role in (controlTypes.Role.POPUPMENU, controlTypes.Role.MENUITEM) and win_class == "#32768")
        is_readonly = (controlTypes.State.READONLY in states) or is_real_menu or (role in non_input_roles and not is_editable)
        self._can_probe_replace = not is_console and not in_browse_mode and not is_readonly and not _is_protected_object(focus)
        self._can_copy_probe = _is_copy_probe_allowed(focus)

        return text, is_editable, is_from_selection, is_console

    def _async_translate(self, text, sl, tl, is_editable=False, is_from_selection=False, is_console=False, slot_prefix=None):
        copied_for_translation = False
        probe_performed = False
        clip_snapshot = None
        initial_clip = ""
        try:
            initial_clip = api.getClipData() or ""
        except Exception:
            initial_clip = ""

        try:
            cfg = settingsDialogs.load_config()

            # Always capture clipboard snapshot up front if not in secure desktop and not sensitive.
            # This guarantees we can restore the user's exact clipboard (files, HTML, text)
            # if copy probe runs OR if replaceSelection uses the clipboard temporarily.
            if not is_secure_mode() and not _is_clipboard_sensitive():
                clip_snapshot = _snapshot_clipboard()

            # 1. Safe Copy Probe for games, web chat boxes, and inaccessible custom UI
            # Suppressed on Windows Desktop, File Explorer, Taskbar, and non-text UI to prevent unwanted copy actions
            if not text and getattr(self, "_can_copy_probe", False):
                # Skip copy probe in console/terminal to prevent sending SIGINT, on secure desktop, and when clipboard has sensitive data
                if not is_console and not is_secure_mode() and not _is_clipboard_sensitive():
                    probed_clip = ""
                    clip_cleared = False
                    user32 = ctypes.windll.user32
                    initial_seq = 0
                    try:
                        initial_seq = user32.GetClipboardSequenceNumber()
                    except Exception:
                        pass

                    # Temporarily empty clipboard so we can definitively detect if Ctrl+C produced text,
                    # even when the selected text is identical to existing clipboard content.
                    try:
                        if user32.OpenClipboard(0):
                            try:
                                user32.EmptyClipboard()
                                clip_cleared = True
                            finally:
                                user32.CloseClipboard()
                    except Exception:
                        pass

                    # Send copy probe safely to capture selection in non-accessible controls (e.g. games, custom UI, chat boxes)
                    try:
                        probe_performed = True
                        target_hwnd = getattr(self, "_target_hwnd", None)

                        # Phase 1: Silent direct API WM_COPY (0x0301) to avoid triggering external clipboard add-ons
                        if target_hwnd:
                            send_copy_message_api(target_hwnd)
                            for _poll in range(5):
                                time.sleep(0.01)
                                try:
                                    cur = api.getClipData() or ""
                                    if cur and cur.strip():
                                        probed_clip = cur
                                        break
                                except Exception:
                                    pass

                        # Phase 2: If API WM_COPY was not handled by the target window, fall back to keyboard simulation
                        if not probed_clip:
                            _wait_for_modifiers_released(30)
                            send_copy_input()

                            # Poll up to 200ms (20 iterations * 10ms) for clipboard to receive copied content
                            for attempt in range(20):
                                time.sleep(0.01)
                                cur_seq = 0
                                try:
                                    cur_seq = user32.GetClipboardSequenceNumber()
                                except Exception:
                                    pass

                                if clip_cleared:
                                    try:
                                        cur = api.getClipData() or ""
                                        if cur and cur.strip():
                                            probed_clip = cur
                                            break
                                    except Exception:
                                        pass
                                elif initial_seq and cur_seq != initial_seq:
                                    try:
                                        probed_clip = api.getClipData() or ""
                                        if probed_clip:
                                            break
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        cur_clip = api.getClipData() or ""
                                        if cur_clip and cur_clip != initial_clip:
                                            probed_clip = cur_clip
                                            break
                                    except Exception:
                                        pass

                        if probed_clip and probed_clip.strip():
                            text = probed_clip.strip()
                            is_from_selection = True
                            copied_for_translation = True
                        else:
                            # If copy probe did not capture any selection, restore original clipboard content immediately
                            _restore_clipboard(clip_snapshot, initial_clip)
                    except Exception as probe_err:
                        logHandler.log.debug(f"OmniTranslate: Copy probe error: {probe_err}")
                        _restore_clipboard(clip_snapshot, initial_clip)

            # 2. Fallback to clipboard if text is still empty (copy probe skipped or captured nothing)
            if not text:
                if _is_clipboard_sensitive():
                    wx.CallAfter(tones.beep, 200, 70)
                    wx.CallAfter(ui.message, _("Clipboard contains password manager content; translation skipped for security."))
                    return
                if cfg.get("translateClipboard", True) and initial_clip and initial_clip.strip():
                    text = initial_clip.strip()
                    is_editable = False
                    is_from_selection = False

            # 3. If still no text found to translate, notify and exit
            if not text:
                if probe_performed:
                    _restore_clipboard(clip_snapshot, initial_clip)
                wx.CallAfter(tones.beep, 200, 70)
                if not cfg.get("translateClipboard", True):
                    no_text_msg = _("No text selected to translate.")
                else:
                    no_text_msg = _("No text selected or found in clipboard.")
                full_msg = f"{slot_prefix}. {no_text_msg}" if slot_prefix else no_text_msg
                wx.CallAfter(ui.message, full_msg)
                return

            if not has_translatable_text(text):
                if copied_for_translation or probe_performed:
                    _restore_clipboard(clip_snapshot, initial_clip)
                wx.CallAfter(tones.beep, 200, 70)
                msg = _("No translatable text found.")
                full_msg = f"{slot_prefix}. {msg}" if slot_prefix else msg
                wx.CallAfter(ui.message, full_msg)
                return

            # Intelligent Chunking & Delimiter Pairing Pipeline
            chunks, was_truncated = create_translation_chunks(text, max_chunk_size=MAX_CHUNK_CHARS, max_total_limit=MAX_TOTAL_TRANSLATE_CHARS)
            if was_truncated:
                wx.CallAfter(tones.beep, 350, 40)
                # Disable selection replacement if text was truncated to prevent destroying remaining unselected text
                is_editable = False

            total_chunks = len(chunks)
            if was_truncated:
                announce_msg = _("Text exceeds maximum limit of 50,000 characters; translating first {count} characters in {parts} parts...").format(
                    count=sum(len(c) + len(d) for c, d in chunks),
                    parts=total_chunks
                )
            elif total_chunks > 1:
                announce_msg = _("Translating {count} characters in {parts} parts...").format(
                    count=len(text),
                    parts=total_chunks
                )
            elif slot_prefix:
                announce_msg = f"{slot_prefix}: {_('Translating...')}"
            else:
                announce_msg = _("Translating...")

            def _announce_start():
                try:
                    speech.cancelSpeech()
                except Exception:
                    pass
                ui.message(announce_msg)

            wx.CallAfter(_announce_start)

            translated_pieces = []
            actual_src = sl
            actual_tgt = tl
            actual_mode = cfg.get("translationMode", "online")
            doc_target = tl
            target_decided = False

            for part_idx, (chunk_content, chunk_delim) in enumerate(chunks):
                if not chunk_content.strip():
                    translated_pieces.append(chunk_content + chunk_delim)
                    continue
                part_result, p_src, p_tgt = execute_translation(chunk_content, sl, doc_target)
                if not target_decided:
                    doc_target = p_tgt
                    target_decided = True
                actual_src = p_src
                actual_tgt = p_tgt
                if p_src in ("offline", "offline-fallback"):
                    actual_mode = p_src
                translated_pieces.append(part_result + chunk_delim)

            result = "".join(translated_pieces)
            if not result or not result.strip():
                if copied_for_translation or probe_performed:
                    _restore_clipboard(clip_snapshot, initial_clip)
                wx.CallAfter(tones.beep, 200, 70)
                wx.CallAfter(ui.message, _("Translation failed: Empty result received."))
                return

            settingsDialogs.SESSION_HISTORY.insert(0, {
                "original": text,
                "translated": result,
                "from": actual_src,
                "to": actual_tgt
            })
            settingsDialogs.SESSION_HISTORY = settingsDialogs.SESSION_HISTORY[:10]
            logHandler.log.info(f"OmniTranslate: Translation successful [Mode: {actual_mode}, Target: {actual_tgt}, Input: {len(text)} chars, Output: {len(result)} chars]")

            spoken_result = result

            # 1. Replace Selected Text in Editable Fields / Games / Probed Controls (if enabled and was selected or probed)
            can_replace = is_editable and not is_console
            was_selected_or_probed = is_from_selection or (copied_for_translation and is_editable and getattr(self, "_can_probe_replace", False))
            if can_replace and was_selected_or_probed and cfg.get("replaceSelection", False) and not is_secure_mode():
                if result.strip() == text.strip() or not has_translatable_text(text):
                    if copied_for_translation or probe_performed:
                        _restore_clipboard(clip_snapshot, initial_clip)
                    if cfg.get("speakResult", True):
                        wx.CallAfter(ui.message, spoken_result)
                    return
                try:
                    # Synchronously set clipboard directly in worker thread with Win32 retries (0-2ms, zero MainThread contention)
                    clip_ok = set_clipboard_text(result)
                    if not clip_ok:
                        # Fallback attempt via api.copyToClip on MainThread if Win32 direct open was blocked
                        wx.CallAfter(api.copyToClip, result)
                        for _poll_idx in range(15):
                            time.sleep(0.010)
                            try:
                                cur_clip = api.getClipData()
                                if cur_clip and (cur_clip == result or cur_clip.strip() == result.strip()):
                                    clip_ok = True
                                    break
                            except Exception:
                                pass

                    # CRITICAL SAFETY GUARD: Only paste if clipboard is verified to contain the translation!
                    # Never paste if clipboard sync failed, preventing accidental overwrites with untranslated or stale text.
                    if clip_ok:
                        try:
                            send_paste_input()
                        finally:
                            time.sleep(0.08)
                    else:
                        logHandler.log.warning("OmniTranslate: Clipboard sync failed during text replacement; paste aborted for safety.")

                    # Clipboard restoration policy: If copyToClipboard is disabled, restore the user's original clipboard
                    # so that temporary paste buffer usage does not overwrite user's clipboard contents.
                    if not cfg.get("copyToClipboard", False):
                        _restore_clipboard(clip_snapshot, initial_clip)

                    if cfg.get("speakResult", True):
                        wx.CallAfter(ui.message, spoken_result)
                except Exception as e:
                    logHandler.log.debug(f"OmniTranslate: Paste replacement error: {e}")
                    if not cfg.get("copyToClipboard", False):
                        _restore_clipboard(clip_snapshot, initial_clip)
                    if cfg.get("speakResult", True):
                        wx.CallAfter(ui.message, spoken_result)

            else:
                # 2. Automatically Copy to Clipboard (if not replaced)
                if cfg.get("copyToClipboard", False):
                    if not set_clipboard_text(result):
                        wx.CallAfter(api.copyToClip, result)
                    if not cfg.get("speakResult", True):
                        wx.CallAfter(ui.message, _("Translated and copied to clipboard."))
                else:
                    # If copyToClipboard is disabled, ensure any temporary clipboard probe is reverted
                    if copied_for_translation or probe_performed:
                        _restore_clipboard(clip_snapshot, initial_clip)

                # 3. Speech Output (when not replacing)
                if cfg.get("speakResult", True):
                    wx.CallAfter(ui.message, spoken_result)
        except Exception as e:
            if not cfg.get("copyToClipboard", False) or copied_for_translation or probe_performed:
                _restore_clipboard(clip_snapshot, initial_clip)
            logHandler.log.error(f"OmniTranslate: Translation execution error: {e}")
            err_msg = f"{_('Translation Error:')} {str(e)}"
            wx.CallAfter(tones.beep, 200, 70)
            wx.CallAfter(ui.message, err_msg)

    def script_translate(self, gesture):
        """Translates selected text or clipboard content using OmniTranslate."""
        now = time.time()
        if now - getattr(self, "_last_translate_time", 0.0) < 0.4:
            return
        self._last_translate_time = now

        tones.beep(550, 40)
        ctx = self._prepare_translation_context()
        if not ctx:
            return
        text, is_editable, is_from_selection, is_console = ctx

        cfg = settingsDialogs.load_config()
        sl = "auto" if cfg.get("autoDetect", True) else cfg.get("sourceLang", "en")
        tl = cfg.get("targetLang", "th")
        threading.Thread(
            target=self._async_translate,
            args=(text, sl, tl, is_editable, is_from_selection, is_console),
            daemon=True
        ).start()

    def script_toggleMode(self, gesture):
        """Toggles translation mode between Online and Offline."""
        if is_secure_mode():
            ui.message(_("Changing translation mode is unavailable on secure screens."))
            return
        cfg = settingsDialogs.load_config()
        cur_mode = cfg.get("translationMode", "online")
        new_mode = "offline" if cur_mode == "online" else "online"
        settingsDialogs.save_config({"translationMode": new_mode})
        offlineEngine.on_mode_changed(new_mode)
        if new_mode == "offline":
            tones.beep(400, 40)
            ui.message(_("Translation mode: Offline Only (Local Neural Engine)"))
        else:
            tones.beep(600, 40)
            ui.message(_("Translation mode: Online (with offline fallback)"))

    def _switchToSlot(self, slot_num):
        """Switches to quick slot, updates target language, and instantly executes translation."""
        now = time.time()
        if now - getattr(self, "_last_translate_time", 0.0) < 0.4:
            return
        self._last_translate_time = now

        if is_secure_mode():
            ui.message(_("Changing target language is unavailable on secure screens."))
            return

        cfg = settingsDialogs.load_config()
        slot_key = f"targetQuickSlot{slot_num}"
        target_lang = cfg.get(slot_key, cfg.get(f"quickSlot{slot_num}", "none"))

        if not target_lang or target_lang in ("none", "", "Please select a language"):
            tones.beep(200, 70)
            ui.message(_("Cannot translate: Target language slot {slot} is not configured. Please configure it in OmniTranslate settings.").format(slot=slot_num))
            return

        cfg_updates = {"targetLang": target_lang}
        settingsDialogs.save_config(cfg_updates)
        self.current_slot_index = slot_num - 1
        lang_name = settingsDialogs.AVAILABLE_LANGUAGES.get(target_lang, target_lang)

        tones.beep(550, 40)
        ctx = self._prepare_translation_context()
        if not ctx:
            return
        text, is_editable, is_from_selection, is_console = ctx

        slot_prefix = _("Slot {slot} ({lang})").format(slot=slot_num, lang=lang_name)
        sl = "auto" if cfg.get("autoDetect", True) else cfg.get("sourceLang", "en")
        threading.Thread(
            target=self._async_translate,
            args=(text, sl, target_lang, is_editable, is_from_selection, is_console, slot_prefix),
            daemon=True
        ).start()

    def _setSourceSlot(self, slot_num):
        """Switches secondary source language (sourceLang) to quick slot."""
        if is_secure_mode():
            ui.message(_("Changing source language is unavailable on secure screens."))
            return

        cfg = settingsDialogs.load_config()
        slot_key = f"sourceQuickSlot{slot_num}"
        source_lang = cfg.get(slot_key, "none")

        if not source_lang or source_lang in ("none", "", "Please select a language"):
            tones.beep(200, 70)
            ui.message(_("Cannot set source language: Source language slot {slot} is not configured. Please configure it in OmniTranslate settings.").format(slot=slot_num))
            return

        cfg_updates = {"sourceLang": source_lang}
        settingsDialogs.save_config(cfg_updates)
        lang_name = settingsDialogs.AVAILABLE_LANGUAGES.get(source_lang, source_lang)
        tones.beep(650, 40)
        ui.message(_("Source language set to Slot {slot} ({lang})").format(slot=slot_num, lang=lang_name))

    def script_slot1(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 1."""
        self._switchToSlot(1)
    def script_slot2(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 2."""
        self._switchToSlot(2)
    def script_slot3(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 3."""
        self._switchToSlot(3)
    def script_slot4(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 4."""
        self._switchToSlot(4)
    def script_slot5(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 5."""
        self._switchToSlot(5)
    def script_slot6(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 6."""
        self._switchToSlot(6)
    def script_slot7(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 7."""
        self._switchToSlot(7)
    def script_slot8(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 8."""
        self._switchToSlot(8)
    def script_slot9(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 9."""
        self._switchToSlot(9)
    def script_slot10(self, gesture):
        """Translates selected text or clipboard into language configured in Quick Slot 10."""
        self._switchToSlot(10)

    def script_srcSlot1(self, gesture):
        """Sets source language to language configured in Quick Slot 1 without translating."""
        self._setSourceSlot(1)
    def script_srcSlot2(self, gesture):
        """Sets source language to language configured in Quick Slot 2 without translating."""
        self._setSourceSlot(2)
    def script_srcSlot3(self, gesture):
        """Sets source language to language configured in Quick Slot 3 without translating."""
        self._setSourceSlot(3)
    def script_srcSlot4(self, gesture):
        """Sets source language to language configured in Quick Slot 4 without translating."""
        self._setSourceSlot(4)
    def script_srcSlot5(self, gesture):
        """Sets source language to language configured in Quick Slot 5 without translating."""
        self._setSourceSlot(5)
    def script_srcSlot6(self, gesture):
        """Sets source language to language configured in Quick Slot 6 without translating."""
        self._setSourceSlot(6)
    def script_srcSlot7(self, gesture):
        """Sets source language to language configured in Quick Slot 7 without translating."""
        self._setSourceSlot(7)
    def script_srcSlot8(self, gesture):
        """Sets source language to language configured in Quick Slot 8 without translating."""
        self._setSourceSlot(8)
    def script_srcSlot9(self, gesture):
        """Sets source language to language configured in Quick Slot 9 without translating."""
        self._setSourceSlot(9)
    def script_srcSlot10(self, gesture):
        """Sets source language to language configured in Quick Slot 10 without translating."""
        self._setSourceSlot(10)

    def script_openViewer(self, gesture):
        """Opens accessible Result Viewer dialog."""
        if is_secure_mode():
            ui.message(_("Result Viewer is unavailable on secure screens."))
            return
        if not settingsDialogs.SESSION_HISTORY:
            ui.message(_("No translation available to view."))
            return
        latest_text = settingsDialogs.SESSION_HISTORY[0]["translated"]
        def _show():
            gui.mainFrame.prePopup()
            try:
                d = settingsDialogs.ResultViewerDialog(gui.mainFrame, latest_text)
                d.ShowModal()
                d.Destroy()
            finally:
                gui.mainFrame.postPopup()
        wx.CallAfter(_show)

    def script_openHistory(self, gesture):
        """Opens translation history dialog."""
        if is_secure_mode():
            ui.message(_("Translation History is unavailable on secure screens."))
            return
        def _show():
            gui.mainFrame.prePopup()
            try:
                d = settingsDialogs.HistoryDialog(gui.mainFrame, settingsDialogs.SESSION_HISTORY)
                d.ShowModal()
                d.Destroy()
            finally:
                gui.mainFrame.postPopup()
        wx.CallAfter(_show)

    def script_toggleSpeech(self, gesture):
        """Toggles automatic speech output."""
        if is_secure_mode():
            ui.message(_("Changing speech settings is unavailable on secure screens."))
            return
        cfg = settingsDialogs.load_config()
        new_state = not cfg.get("speakResult", True)
        settingsDialogs.save_config({"speakResult": new_state})
        state = _("enabled") if new_state else _("disabled")
        if new_state:
            tones.beep(600, 40)
        else:
            tones.beep(300, 40)
        ui.message(_("Speech output {state}").format(state=state))

    def script_repeatLast(self, gesture):
        """Repeats the last translated result."""
        if is_secure_mode():
            ui.message(_("Repeat last translation is unavailable on secure screens."))
            return
        if settingsDialogs.SESSION_HISTORY:
            ui.message(settingsDialogs.SESSION_HISTORY[0]["translated"])
        else:
            ui.message(_("No recent translation."))

    def script_copyLast(self, gesture):
        """Copies the last translated result to clipboard."""
        if is_secure_mode():
            ui.message(_("Copying translation is unavailable on secure screens."))
            return
        if settingsDialogs.SESSION_HISTORY:
            latest_text = settingsDialogs.SESSION_HISTORY[0]["translated"]
            if set_clipboard_text(latest_text) or api.copyToClip(latest_text):
                ui.message(_("Last result copied to clipboard."))
            else:
                ui.message(_("Failed to copy to clipboard."))
        else:
            ui.message(_("No recent translation."))

    def script_openSettings(self, gesture):
        """Opens OmniTranslate settings panel in NVDA Settings."""
        if is_secure_mode():
            ui.message(_("Settings dialog is unavailable on secure screens."))
            return
        def _show():
            try:
                popup_fn = getattr(gui, "popupSettingsDialog", None)
                if popup_fn:
                    try:
                        popup_fn(gui.settingsDialogs.NVDASettingsDialog, settingsDialogs.OmniTranslateGeneralSettingsPanel)
                        return
                    except Exception as ex:
                        logHandler.log.debug(f"OmniTranslate: gui.popupSettingsDialog failed: {ex}")
                popupSettingsDialog = getattr(gui.mainFrame, "popupSettingsDialog", getattr(gui.mainFrame, "_popupSettingsDialog", None))
                if popupSettingsDialog:
                    try:
                        popupSettingsDialog(gui.settingsDialogs.NVDASettingsDialog, settingsDialogs.OmniTranslateGeneralSettingsPanel)
                        return
                    except Exception as ex:
                        logHandler.log.debug(f"OmniTranslate: popupSettingsDialog failed, attempting direct instantiation: {ex}")
                gui.mainFrame.prePopup()
                try:
                    d = gui.settingsDialogs.NVDASettingsDialog(gui.mainFrame, settingsDialogs.OmniTranslateGeneralSettingsPanel)
                    d.Show()
                finally:
                    gui.mainFrame.postPopup()
            except Exception as e:
                logHandler.log.error(f"OmniTranslate: Error opening settings panel: {e}")
        wx.CallAfter(_show)

    def script_openDoc(self, gesture):
        """Opens OmniTranslate user documentation."""
        docHandler.openDoc()

    def script_layer(self, gesture):
        """OmniTranslate Layer: press once then press a sub-key to execute commands."""
        tones.beep(500, 35)
        self._exitLayer()
        self._in_layer = True
        self._start_layer_timer()