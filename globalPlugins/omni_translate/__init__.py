# -*- coding: utf-8 -*-
# OmniTranslate for NVDA - Main Entry Point & Gesture Router
# Author: Isara Watthanawirojkul

import globalPluginHandler
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
from . import docHandler
from . import offlineEngine
from . import settingsDialogs
from . import updateChecker

addonHandler.initTranslation()


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
    with urllib.request.urlopen(req, timeout=4.0) as response:
        raw_data = response.read().decode('utf-8')
        data = json.loads(raw_data)
        translated_text = "".join([part[0] for part in data[0] if part and part[0]])
        detected_src = data[2] if (isinstance(data, list) and len(data) > 2 and isinstance(data[2], str) and data[2]) else sl
        return translated_text, detected_src


def request_web_fallback(text, sl, tl):
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.google.com/m?sl={sl}&tl={tl}&hl=en&q={encoded_text}"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=4.0) as response:
        html_content = response.read().decode('utf-8', errors='ignore')
        match = re.search(r'<div class="result-container">(.*?)</div>', html_content, re.DOTALL)
        if match:
            raw_html = match.group(1).replace('<br>', '\n').replace('<br/>', '\n')
            translated_text = html.unescape(raw_html.strip())
            return translated_text, sl
        raise Exception("Unable to extract translation from Web Engine")


def translate_single_chunk(text, sl, tl):
    try:
        return request_api_endpoint(text, sl, tl, "gtx")
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: gtx endpoint failed: {e}")
        try:
            return request_api_endpoint(text, sl, tl, "dict-chrome-ex")
        except Exception as e:
            logHandler.log.debug(f"OmniTranslate: dict-chrome-ex endpoint failed: {e}")
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


def execute_translation(text, sl, tl):
    cfg = settingsDialogs.load_config()
    mode = cfg.get("translationMode", "online")

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
        is_auto = cfg.get("autoDetect", True)
        secondary_lang = cfg.get("sourceLang", "en")
        primary_target = tl

        if is_multilingual and is_auto and primary_target != secondary_lang:
            detected_src = offlineEngine.detect_text_language(text, hint_langs=(primary_target, secondary_lang))
            norm_det = normalize_lang(detected_src)
            norm_pri = normalize_lang(primary_target)
            norm_sec = normalize_lang(secondary_lang)

            if norm_det == norm_pri:
                translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=primary_target, tgt_lang=secondary_lang)
                return translated_text, detected_src, secondary_lang

            src = detected_src if detected_src else secondary_lang
            translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=src, tgt_lang=primary_target)
            return translated_text, detected_src, primary_target
        else:
            src = supp_info.get("src", ["en"])[0] if not is_multilingual else (cfg.get("sourceLang", "en") if sl == "auto" else sl)
            tgt = supp_info.get("tgt", [tl])[0] if not is_multilingual else tl
            translated_text = offlineEngine.translate_offline(text, selected_model, src_lang=src, tgt_lang=tgt)
            return translated_text, "offline", tgt

    # 2. Online Mode with Auto-Fallback (Smart Bidirectional Translation)
    primary_target = tl
    secondary_lang = cfg.get("sourceLang", "en")
    is_auto = cfg.get("autoDetect", True)
    src_query = "auto" if is_auto else sl

    try:
        translated_text, detected_src = translate_query(text, src_query, primary_target)
        if is_auto and primary_target != secondary_lang:
            norm_det = normalize_lang(detected_src)
            norm_pri = normalize_lang(primary_target)
            norm_sec = normalize_lang(secondary_lang)

            if norm_det == norm_pri:
                swap_text, swap_detected = translate_query(text, "auto", secondary_lang)
                return swap_text, (swap_detected or detected_src or primary_target), secondary_lang

        return translated_text, detected_src, primary_target
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
            if is_multilingual and is_auto and primary_target != secondary_lang:
                detected_src = offlineEngine.detect_text_language(text, hint_langs=(primary_target, secondary_lang))
                norm_det = normalize_lang(detected_src)
                norm_pri = normalize_lang(primary_target)

                if norm_det == norm_pri:
                    translated_text = offlineEngine.translate_offline(text, active_model, src_lang=primary_target, tgt_lang=secondary_lang)
                    return translated_text, detected_src, secondary_lang

                src = detected_src if detected_src else secondary_lang
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
    """Releases modifier keys (Shift, Alt, Win, Insert, CapsLock, Ctrl) if currently held to prevent keystroke distortion."""
    try:
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002
        for vk in (0x10, 0xA0, 0xA1, 0x12, 0xA4, 0xA5, 0x5B, 0x5C, 0x2D, 0x14, 0x11, 0xA2, 0xA3):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def send_paste_input():
    """Sends Ctrl+V to the active window safely without triggering NVDA gestures."""
    try:
        _release_modifiers()
        try:
            keyboardHandler.bypassInputHook = True
        except Exception:
            pass
        try:
            gesture = keyboardHandler.KeyboardInputGesture.fromName("control+v")
            gesture.send()
        except Exception:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002
            scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
            scan_v = user32.MapVirtualKeyW(VK_V, 0)

            # 1. Ctrl Down
            user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
            time.sleep(0.02)

            # 2. V Down & Hold
            user32.keybd_event(VK_V, scan_v, 0, 0)
            time.sleep(0.03)

            # 3. V Up
            user32.keybd_event(VK_V, scan_v, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)

            # 4. Ctrl Up
            user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
        finally:
            try:
                keyboardHandler.bypassInputHook = False
            except Exception:
                pass
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: send_paste_input error: {e}")


def send_copy_input():
    """Sends Ctrl+C to the active window safely without triggering NVDA gestures."""
    try:
        _release_modifiers()
        try:
            keyboardHandler.bypassInputHook = True
        except Exception:
            pass
        try:
            gesture = keyboardHandler.KeyboardInputGesture.fromName("control+c")
            gesture.send()
        except Exception:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_C = 0x43
            KEYEVENTF_KEYUP = 0x0002
            scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
            scan_c = user32.MapVirtualKeyW(VK_C, 0)

            # 1. Ctrl Down
            user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
            time.sleep(0.02)

            # 2. C Down & Hold
            user32.keybd_event(VK_C, scan_c, 0, 0)
            time.sleep(0.03)

            # 3. C Up
            user32.keybd_event(VK_C, scan_c, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)

            # 4. Ctrl Up
            user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
        finally:
            try:
                keyboardHandler.bypassInputHook = False
            except Exception:
                pass
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: send_copy_input error: {e}")



def _is_editable_object(obj):
    """Checks if an NVDA object is in an editable context (or non-readonly)."""
    if not obj:
        return True
    try:
        # 1. Direct attribute indicators (Gecko / Chromium / UIA)
        if getattr(obj, "isContentEditable", False) or getattr(obj, "isEditable", False):
            return True

        states = getattr(obj, "states", set())
        role = getattr(obj, "role", None)

        # 2. Known read-only documents / tooltips in browse mode
        if controlTypes.State.READONLY in states and role in (
            controlTypes.Role.DOCUMENT,
            controlTypes.Role.HELPBALLOON,
            controlTypes.Role.STATICTEXT,
            controlTypes.Role.TOOLTIP,
        ) and not getattr(obj, "isContentEditable", False) and controlTypes.State.EDITABLE not in states:
            return False

        # In all other cases (chat boxes, edit fields, Run dialog, Word, Notepad, games, terminals, etc.)
        return True
    except Exception as e:
        logHandler.log.debug(f"OmniTranslate: _is_editable_object error: {e}")
    return True


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
        self._last_translate_time = 0.0
        try:
            updateChecker.start_update_checker_service()
        except Exception as e:
            logHandler.log.debug(f"OmniTranslate: Could not start update checker: {e}")

    def terminate(self):
        self._exitLayer()
        try:
            NVDASettingsDialog.categoryClasses.remove(settingsDialogs.OmniTranslateGeneralSettingsPanel)
        except Exception:
            pass
        try:
            NVDASettingsDialog.categoryClasses.remove(settingsDialogs.OmniTranslateOfflineModelsPanel)
        except Exception:
            pass
        super(GlobalPlugin, self).terminate()

    def _exitLayer(self):
        if self._in_layer:
            self._in_layer = False
            try:
                inputCore.decide_executeGesture.unregister(self._onLayerGesture)
            except Exception:
                pass

    def _onLayerGesture(self, gesture):
        if getattr(gesture, "isModifier", False):
            return True

        idents = [i.lower() for i in getattr(gesture, "identifiers", [])]
        vk = getattr(gesture, "vkCode", None)

        # 1. Check if user pressed NVDA+Shift+T again (re-enter/keep layer mode)
        is_layer_repeat = False
        for ident in idents:
            if any(k in ident for k in (
                "nvda+shift+t", "shift+nvda+t",
                "insert+shift+t", "shift+insert+t"
            )):
                is_layer_repeat = True
                break

        if is_layer_repeat:
            tones.beep(500, 35)
            return False

        self._exitLayer()

        for ident in idents:
            key = ident.replace("kb:", "").replace("kb(desktop):", "").replace("kb(laptop):", "").strip()
            if vk == 0x54 or key in ("t", "shift+t") or key.endswith("+t"):
                self.script_translate(gesture)
                return False
            elif vk == 0x53 or key in ("s", "shift+s") or key.endswith("+s"):
                self.script_toggleMode(gesture)
                return False
            elif vk in (0x31, 0x61) or key in ("1", "numpad1", "shift+1") or key.endswith("+1") or key.endswith("+numpad1"):
                self.script_slot1(gesture)
                return False
            elif vk in (0x32, 0x62) or key in ("2", "numpad2", "shift+2") or key.endswith("+2") or key.endswith("+numpad2"):
                self.script_slot2(gesture)
                return False
            elif vk in (0x33, 0x63) or key in ("3", "numpad3", "shift+3") or key.endswith("+3") or key.endswith("+numpad3"):
                self.script_slot3(gesture)
                return False
            elif vk in (0x34, 0x64) or key in ("4", "numpad4", "shift+4") or key.endswith("+4") or key.endswith("+numpad4"):
                self.script_slot4(gesture)
                return False
            elif vk in (0x35, 0x65) or key in ("5", "numpad5", "shift+5") or key.endswith("+5") or key.endswith("+numpad5"):
                self.script_slot5(gesture)
                return False
            elif vk == 0x56 or key in ("v", "shift+v") or key.endswith("+v"):
                self.script_openViewer(gesture)
                return False
            elif vk == 0x48 or key in ("h", "shift+h") or key.endswith("+h"):
                self.script_openHistory(gesture)
                return False
            elif vk == 0x4D or key in ("m", "shift+m") or key.endswith("+m"):
                self.script_toggleSpeech(gesture)
                return False
            elif vk == 0x52 or key in ("r", "shift+r") or key.endswith("+r"):
                self.script_repeatLast(gesture)
                return False
            elif vk == 0x43 or key in ("c", "shift+c") or key.endswith("+c"):
                self.script_copyLast(gesture)
                return False
            elif vk == 0x4F or key in ("o", "shift+o") or key.endswith("+o"):
                self.script_openSettings(gesture)
                return False
            elif vk == 0x70 or key in ("f1", "shift+f1") or key.endswith("+f1"):
                self.script_openDoc(gesture)
                return False
            elif vk == 0x1B or key == "escape":
                tones.beep(250, 35)
                return False

        tones.beep(250, 25)
        return True

    def get_selected_text_info(self):
        """Returns tuple of (text, is_editable, is_from_selection)."""
        try:
            focus = api.getFocusObject()
            treeInterceptor = getattr(focus, "treeInterceptor", None)

            # 1. Check treeInterceptor (Virtual Buffer / Browse mode vs Focus mode)
            if treeInterceptor and hasattr(treeInterceptor, "makeTextInfo"):
                try:
                    info = treeInterceptor.makeTextInfo(textInfos.POSITION_SELECTION)
                    if info and not info.isCollapsed:
                        text = info.text.strip()
                        if text:
                            is_editable = False
                            if getattr(treeInterceptor, "passThrough", False) or _is_editable_object(focus):
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
        text, _, _ = self.get_selected_text_info()
        if not text:
            try:
                clip = api.getClipData()
                if clip and clip.strip():
                    return clip.strip()
            except Exception:
                pass
        return text

    def _async_translate(self, text, sl, tl, is_editable=False, is_from_selection=False, announce_translating=True):
        try:
            cfg = settingsDialogs.load_config()

            # If no selection was found via NVDA accessible text info, try safe copy probe for games / custom UI
            if not text:
                initial_clip = ""
                try:
                    initial_clip = api.getClipData() or ""
                except Exception:
                    initial_clip = ""

                initial_seq = 0
                try:
                    user32 = ctypes.windll.user32
                    initial_seq = user32.GetClipboardSequenceNumber()
                except Exception:
                    pass

                # Send copy probe safely to capture selection in non-accessible controls (e.g. games, custom UI)
                try:
                    wx.CallAfter(send_copy_input)
                    probed_clip = ""
                    # Poll up to 200ms (20 iterations * 10ms) for clipboard sequence or content update
                    for attempt in range(20):
                        time.sleep(0.01)
                        cur_seq = 0
                        try:
                            cur_seq = user32.GetClipboardSequenceNumber()
                        except Exception:
                            pass

                        if initial_seq and cur_seq != initial_seq:
                            try:
                                probed_clip = api.getClipData() or ""
                            except Exception:
                                pass
                            if probed_clip:
                                break
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
                        is_editable = True
                        is_from_selection = True
                    else:
                        if cfg.get("translateClipboard", True) and initial_clip and initial_clip.strip():
                            text = initial_clip.strip()
                            is_editable = False
                            is_from_selection = False
                except Exception as probe_err:
                    logHandler.log.debug(f"OmniTranslate: Copy probe error: {probe_err}")

            if not text:
                if not cfg.get("translateClipboard", True):
                    wx.CallAfter(ui.message, _("No text selected to translate."))
                else:
                    wx.CallAfter(ui.message, _("No text selected or found in clipboard."))
                return

            if announce_translating:
                wx.CallAfter(ui.message, _("Translating..."))

            result, actual_src, actual_tgt = execute_translation(text, sl, tl)
            settingsDialogs.SESSION_HISTORY.insert(0, {
                "original": text,
                "translated": result,
                "from": actual_src,
                "to": actual_tgt
            })
            settingsDialogs.SESSION_HISTORY = settingsDialogs.SESSION_HISTORY[:10]

            # 1. Replace Selected Text in Editable Fields / Games / Controls (if enabled and was selected)
            if is_editable and is_from_selection and cfg.get("replaceSelection", False):
                def _doReplace():
                    try:
                        api.copyToClip(result)
                        def _sendPasteAndSpeak():
                            try:
                                send_paste_input()
                            except Exception as ex:
                                logHandler.log.debug(f"OmniTranslate: Paste send error: {ex}")
                            if cfg.get("speakResult", True):
                                # Speak after paste has settled so editor deletion events do not interrupt speech
                                wx.CallLater(120, ui.message, result)
                        wx.CallLater(50, _sendPasteAndSpeak)
                    except Exception as e:
                        logHandler.log.debug(f"OmniTranslate: Paste replacement error: {e}")
                        if cfg.get("speakResult", True):
                            wx.CallAfter(ui.message, result)
                wx.CallAfter(_doReplace)

            else:
                # 2. Automatically Copy to Clipboard (if not replaced)
                if cfg.get("copyToClipboard", False):
                    wx.CallAfter(api.copyToClip, result)

                # 3. Speech Output (when not replacing)
                if cfg.get("speakResult", True):
                    wx.CallAfter(ui.message, result)
        except Exception as e:
            logHandler.log.error(f"OmniTranslate: Translation execution error: {e}")
            err_msg = f"{_('Translation Error:')} {str(e)}"
            wx.CallAfter(ui.message, err_msg)

    def script_translate(self, gesture):
        """Translates selected text or clipboard content using OmniTranslate."""
        now = time.time()
        if now - getattr(self, "_last_translate_time", 0.0) < 0.4:
            return
        self._last_translate_time = now

        cfg = settingsDialogs.load_config()
        text, is_editable, is_from_selection = self.get_selected_text_info()
        sl = "auto" if cfg.get("autoDetect", True) else cfg.get("sourceLang", "en")
        tl = cfg.get("targetLang", "th")
        threading.Thread(
            target=self._async_translate,
            args=(text, sl, tl, is_editable, is_from_selection, True),
            daemon=True
        ).start()

    def script_toggleMode(self, gesture):
        """Toggles translation mode between Online and Offline."""
        cfg = settingsDialogs.load_config()
        cur_mode = cfg.get("translationMode", "online")
        new_mode = "offline" if cur_mode == "online" else "online"
        settingsDialogs.save_config({"translationMode": new_mode})
        if new_mode == "offline":
            tones.beep(400, 40)
            ui.message(_("Translation mode: Offline Only (Local Neural Engine)"))
        else:
            tones.beep(600, 40)
            ui.message(_("Translation mode: Online (with offline fallback)"))

    def _switchToSlot(self, slot_num):
        """Switches to quick slot and instantly executes translation."""
        now = time.time()
        if now - getattr(self, "_last_translate_time", 0.0) < 0.4:
            return
        self._last_translate_time = now

        cfg = settingsDialogs.load_config()
        slot_key = f"quickSlot{slot_num}"
        target_lang = cfg.get(slot_key, "none")

        if not target_lang or target_lang in ("none", "", "Please select a language"):
            tones.beep(200, 70)
            ui.message(_("Cannot translate: Language slot {slot} is not configured. Please configure it in OmniTranslate settings.").format(slot=slot_num))
            return

        settingsDialogs.save_config({"targetLang": target_lang})
        self.current_slot_index = slot_num - 1
        lang_name = settingsDialogs.AVAILABLE_LANGUAGES.get(target_lang, target_lang)

        text, is_editable, is_from_selection = self.get_selected_text_info()
        tones.beep(550, 30)
        ui.message(_("Slot {slot} ({lang}): Translating...").format(slot=slot_num, lang=lang_name))
        sl = "auto" if cfg.get("autoDetect", True) else cfg.get("sourceLang", "en")
        threading.Thread(
            target=self._async_translate,
            args=(text, sl, target_lang, is_editable, is_from_selection, False),
            daemon=True
        ).start()

    def script_slot1(self, gesture): self._switchToSlot(1)
    def script_slot2(self, gesture): self._switchToSlot(2)
    def script_slot3(self, gesture): self._switchToSlot(3)
    def script_slot4(self, gesture): self._switchToSlot(4)
    def script_slot5(self, gesture): self._switchToSlot(5)

    def script_openViewer(self, gesture):
        """Opens accessible Result Viewer dialog."""
        if not settingsDialogs.SESSION_HISTORY:
            ui.message(_("No translation available to view."))
            return
        latest_text = settingsDialogs.SESSION_HISTORY[0]["translated"]
        def _show():
            gui.mainFrame.prePopup()
            d = settingsDialogs.ResultViewerDialog(gui.mainFrame, latest_text)
            d.ShowModal()
            d.Destroy()
            gui.mainFrame.postPopup()
        wx.CallAfter(_show)

    def script_openHistory(self, gesture):
        """Opens translation history dialog."""
        def _show():
            gui.mainFrame.prePopup()
            d = settingsDialogs.HistoryDialog(gui.mainFrame, settingsDialogs.SESSION_HISTORY)
            d.ShowModal()
            d.Destroy()
            gui.mainFrame.postPopup()
        wx.CallAfter(_show)

    def script_toggleSpeech(self, gesture):
        """Toggles automatic speech output."""
        cfg = settingsDialogs.load_config()
        new_state = not cfg.get("speakResult", True)
        settingsDialogs.save_config({"speakResult": new_state})
        state = _("enabled") if new_state else _("disabled")
        ui.message(_("Speech output {state}").format(state=state))

    def script_repeatLast(self, gesture):
        """Repeats the last translated result."""
        if settingsDialogs.SESSION_HISTORY:
            ui.message(settingsDialogs.SESSION_HISTORY[0]["translated"])
        else:
            ui.message(_("No recent translation."))

    def script_copyLast(self, gesture):
        """Copies the last translated result to clipboard."""
        if settingsDialogs.SESSION_HISTORY:
            latest_text = settingsDialogs.SESSION_HISTORY[0]["translated"]
            if api.copyToClip(latest_text):
                ui.message(_("Last result copied to clipboard."))
            else:
                ui.message(_("Failed to copy to clipboard."))
        else:
            ui.message(_("No recent translation."))

    def script_openSettings(self, gesture):
        """Opens OmniTranslate settings panel in NVDA Settings."""
        def _show():
            try:
                popupSettingsDialog = getattr(gui.mainFrame, "popupSettingsDialog", getattr(gui.mainFrame, "_popupSettingsDialog", None))
                if popupSettingsDialog:
                    popupSettingsDialog(gui.settingsDialogs.NVDASettingsDialog, settingsDialogs.OmniTranslateGeneralSettingsPanel)
                else:
                    gui.mainFrame.prePopup()
                    d = NVDASettingsDialog(gui.mainFrame, settingsDialogs.OmniTranslateGeneralSettingsPanel)
                    d.Show()
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
        inputCore.decide_executeGesture.register(self._onLayerGesture)