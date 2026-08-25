# -*- coding: utf-8 -*-
import globalPluginHandler
import ui
import scriptHandler
import api
import textInfos
import threading
import json
import os
import urllib.request
import urllib.parse
import html
import wx
import gui
from . import docHandler
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "omni_translate_config.json")
# In-memory session history and last translated text (Cleared on NVDA restart)
SESSION_HISTORY = []
LAST_TRANSLATION = ""
AVAILABLE_LANGUAGES = {
    "auto": "Auto Detect", "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic",
    "hy": "Armenian", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian", "bn": "Bengali",
    "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan", "ceb": "Cebuano", "ny": "Chichewa",
    "zh-CN": "Chinese (Simplified)", "zh-TW": "Chinese (Traditional)", "co": "Corsican", "hr": "Croatian",
    "cs": "Czech", "da": "Danish", "nl": "Dutch", "en": "English", "eo": "Esperanto",
    "et": "Estonian", "tl": "Filipino", "fi": "Finnish", "fr": "French", "fy": "Frisian",
    "gl": "Galician", "ka": "Georgian", "de": "German", "el": "Greek", "gu": "Gujarati",
    "ht": "Haitian Creole", "ha": "Hausa", "haw": "Hawaiian", "iw": "Hebrew", "hi": "Hindi",
    "hmn": "Hmong", "hu": "Hungarian", "is": "Icelandic", "ig": "Igbo", "id": "Indonesian",
    "ga": "Irish", "it": "Italian", "ja": "Japanese", "jw": "Javanese", "kn": "Kannada",
    "kk": "Kazakh", "km": "Khmer", "rw": "Kinyarwanda", "ko": "Korean", "ku": "Kurdish (Kurmanji)",
    "ky": "Kyrgyz", "lo": "Lao", "la": "Latin", "lv": "Latvian", "lt": "Lithuanian",
    "lb": "Luxembourgish", "mk": "Macedonian", "mg": "Malagasy", "ms": "Malay", "ml": "Malayalam",
    "mt": "Maltese", "mi": "Maori", "mr": "Marathi", "mn": "Mongolian", "my": "Myanmar (Burmese)",
    "ne": "Nepali", "no": "Norwegian", "or": "Odia (Oriya)", "ps": "Pashto", "fa": "Persian",
    "pl": "Polish", "pt": "Portuguese", "pa": "Punjabi", "ro": "Romanian", "ru": "Russian",
    "sm": "Samoan", "gd": "Scots Gaelic", "sr": "Serbian", "st": "Sesotho", "sn": "Shona",
    "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali",
    "es": "Spanish", "su": "Sundanese", "sw": "Swahili", "sv": "Swedish", "tg": "Tajik",
    "ta": "Tamil", "tt": "Tatar", "te": "Telugu", "th": "Thai", "tr": "Turkish",
    "tk": "Turkmen", "uk": "Ukrainian", "ur": "Urdu", "ug": "Uyghur", "uz": "Uzbek",
    "vi": "Vietnamese", "cy": "Welsh", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba", "zu": "Zulu"
}
DEFAULT_CONFIG = {
    "sourceLang": "en",
    "targetLang": "th",
    "autoDetect": True,
    "copyToClipboard": False,
    "speakResult": True,
    "quickSlot1": "th",
    "quickSlot2": "en",
    "quickSlot3": "ja",
    "quickSlot4": "zh-CN",
    "quickSlot5": "ko"
}
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                res = DEFAULT_CONFIG.copy()
                res.update(cfg)
                return res
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()
def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def add_session_history(entry):
    global SESSION_HISTORY
    SESSION_HISTORY.insert(0, entry)
    SESSION_HISTORY = SESSION_HISTORY[:10]
def get_session_history():
    return SESSION_HISTORY
def normalize_lang(code):
    if not code:
        return ""
    code = code.lower().strip()
    if code in ("zh-cn", "zh-hans", "zh"):
        return "zh-CN"
    if code in ("zh-tw", "zh-hant"):
        return "zh-TW"
    return code.split("-")[0]
def query_google_api(text, sl, tl):
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&ie=UTF-8&oe=UTF-8&q={encoded_text}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as response:
        raw_data = response.read().decode('utf-8')
        data = json.loads(raw_data)
        translated_text = "".join([part[0] for part in data[0] if part and part[0]])
        detected_src = ""
        if len(data) > 2 and data[2]:
            detected_src = data[2]
        elif len(data) > 8 and data[8] and len(data[8]) > 0 and len(data[8][0]) > 0:
            detected_src = data[8][0][0]
        return translated_text, detected_src
def query_google_web(text, sl, tl):
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.google.com/m?sl={sl}&tl={tl}&hl=en&q={encoded_text}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as response:
        html_content = response.read().decode('utf-8', errors='ignore')
        import re
        match = re.search(r'<div class="result-container">(.*?)</div>', html_content, re.DOTALL)
        if match:
            return html.unescape(match.group(1).strip()), sl
        raise Exception("Web fallback failed")
def execute_translation(text, sl, tl):
    cfg = load_config()
    target_lang = tl
    secondary_lang = cfg.get("sourceLang", "en")
    is_auto = cfg.get("autoDetect", True)
    src_query = "auto" if is_auto else sl
    try:
        # Step 1: Query API targeting Primary Target first
        trans_res, detected_src = query_google_api(text, src_query, target_lang)
        norm_det = normalize_lang(detected_src)
        norm_tgt = normalize_lang(target_lang)
        norm_sec = normalize_lang(secondary_lang)
        # Step 2: Check if detected input is already the Primary Target language
        # If input == Primary Target, we must translate to Secondary Swap language
        if is_auto and norm_tgt != norm_sec:
            if norm_det == norm_tgt or (trans_res.strip().lower() == text.strip().lower() and len(text.strip()) > 1):
                swap_res, swap_det = query_google_api(text, "auto", secondary_lang)
                return swap_res, (swap_det or detected_src or target_lang), secondary_lang
        return trans_res, (detected_src or "auto"), target_lang
    except Exception:
        pass
    # Web Fallback Engine
    try:
        trans_res, det = query_google_web(text, src_query, target_lang)
        if is_auto and target_lang != secondary_lang and trans_res.strip().lower() == text.strip().lower() and len(text.strip()) > 1:
            swap_res, _ = query_google_web(text, "auto", secondary_lang)
            return swap_res, target_lang, secondary_lang
        return trans_res, det, target_lang
    except Exception as e:
        raise Exception(f"Translation service unavailable: {str(e)}")
class ResultViewerDialog(gui.SettingsDialog):
    title = "OmniTranslate - Translation Result"
    def __init__(self, parent, result_text):
        self.result_text = result_text
        super(ResultViewerDialog, self).__init__(parent)
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.resultEdit = sHelper.addLabeledControl("Translated text:", wx.TextCtrl, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.resultEdit.SetValue(self.result_text)
        self.resultEdit.SetFocus()
    def postInit(self):
        super(ResultViewerDialog, self).postInit()
        self.copyBtn = wx.Button(self, label="Copy to Clipboard")
        self.copyBtn.Bind(wx.EVT_BUTTON, self.onCopy)
        self.ButtonSizer.Insert(0, self.copyBtn, flag=wx.RIGHT, border=5)
    def onCopy(self, evt):
        if api.copyToClip(self.result_text):
            ui.message("Copied to clipboard")
        self.Close()
class HistoryDialog(gui.SettingsDialog):
    title = "OmniTranslate - History"
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.history = get_session_history()
        choices = [f"[{h.get('from','?') }->{h.get('to','?')}] {h.get('original','')[:25]}... -> {h.get('translated','')[:25]}..." for h in self.history]
        if not choices:
            choices = ["No translation history available for this session."]
        self.historyList = sHelper.addLabeledControl("Recent Translations (10 max):", wx.ListBox, choices=choices)
        self.historyList.SetSelection(0)
        self.historyList.SetFocus()
    def postInit(self):
        super(HistoryDialog, self).postInit()
        self.viewBtn = wx.Button(self, label="View Translation")
        self.viewBtn.Bind(wx.EVT_BUTTON, self.onView)
        self.ButtonSizer.Insert(0, self.viewBtn, flag=wx.RIGHT, border=5)
    def onView(self, evt):
        sel = self.historyList.GetSelection()
        if sel != wx.NOT_FOUND and self.history:
            entry = self.history[sel]
            full_text = f"Source [{entry.get('from','?')}]:\n{entry.get('original','')}\n\nTranslation [{entry.get('to','?')}]:\n{entry.get('translated','')}"
            gui.mainFrame.prePopup()
            d = ResultViewerDialog(gui.mainFrame, full_text)
            d.Show()
            gui.mainFrame.postPopup()
        self.Close()
class SettingsDialog(gui.SettingsDialog):
    title = "OmniTranslate Settings"
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.cfg = load_config()
        self.lang_keys = list(AVAILABLE_LANGUAGES.keys())
        self.lang_names = list(AVAILABLE_LANGUAGES.values())
        # 1. Primary target language
        tgt_choices = [AVAILABLE_LANGUAGES[k] for k in self.lang_keys if k != "auto"]
        tgt_keys = [k for k in self.lang_keys if k != "auto"]
        tgt_idx = tgt_keys.index(self.cfg.get("targetLang", "th")) if self.cfg.get("targetLang", "th") in tgt_keys else 0
        self.tgtChoice = sHelper.addLabeledControl("Primary target language:", wx.Choice, choices=tgt_choices)
        self.tgtChoice.SetSelection(tgt_idx)
        self.tgt_keys = tgt_keys
        # 2. Secondary swap language
        src_choices = [AVAILABLE_LANGUAGES[k] for k in self.lang_keys if k != "auto"]
        src_keys = [k for k in self.lang_keys if k != "auto"]
        src_idx = src_keys.index(self.cfg.get("sourceLang", "en")) if self.cfg.get("sourceLang", "en") in src_keys else 0
        self.srcChoice = sHelper.addLabeledControl("Secondary swap language:", wx.Choice, choices=src_choices)
        self.srcChoice.SetSelection(src_idx)
        self.src_keys = src_keys
        # 3. Quick Cycle Slots 1 - 5
        self.slotControls = []
        for i in range(1, 6):
            slot_key = f"quickSlot{i}"
            cur_lang = self.cfg.get(slot_key, "en")
            s_idx = tgt_keys.index(cur_lang) if cur_lang in tgt_keys else 0
            ctrl = sHelper.addLabeledControl(f"Quick Cycle Slot {i}:", wx.Choice, choices=tgt_choices)
            ctrl.SetSelection(s_idx)
            self.slotControls.append(ctrl)
        # 4. Checkboxes
        self.autoDetectCheck = sHelper.addItem(wx.CheckBox(self, label="Auto-detect input language"))
        self.autoDetectCheck.SetValue(self.cfg.get("autoDetect", True))
        self.copyCheck = sHelper.addItem(wx.CheckBox(self, label="Automatically copy translation to clipboard"))
        self.copyCheck.SetValue(self.cfg.get("copyToClipboard", False))
        self.speakCheck = sHelper.addItem(wx.CheckBox(self, label="Speak translation automatically"))
        self.speakCheck.SetValue(self.cfg.get("speakResult", True))
    def onOk(self, evt):
        self.cfg["targetLang"] = self.tgt_keys[self.tgtChoice.GetSelection()]
        self.cfg["sourceLang"] = self.src_keys[self.srcChoice.GetSelection()]
        for i, ctrl in enumerate(self.slotControls, 1):
            self.cfg[f"quickSlot{i}"] = self.tgt_keys[ctrl.GetSelection()]
        self.cfg["autoDetect"] = self.autoDetectCheck.GetValue()
        self.cfg["copyToClipboard"] = self.copyCheck.GetValue()
        self.cfg["speakResult"] = self.speakCheck.GetValue()
        save_config(self.cfg)
        super(SettingsDialog, self).onOk(evt)
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "OmniTranslate"
    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self.current_slot_index = 0
        self.settings_item = None
        self.help_item = None
        if hasattr(gui, "mainFrame") and hasattr(gui.mainFrame, "sysTrayIcon"):
            try:
                tools_menu = gui.mainFrame.sysTrayIcon.toolsMenu
                self.settings_item = tools_menu.Append(wx.ID_ANY, "OmniTranslate Settings...", "Configure OmniTranslate preferences")
                gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSettingsMenu, self.settings_item)
            except Exception:
                pass
            try:
                help_menu = gui.mainFrame.sysTrayIcon.helpMenu
                self.help_item = help_menu.Append(wx.ID_ANY, "OmniTranslate Documentation", "View OmniTranslate user documentation")
                gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onHelpMenu, self.help_item)
            except Exception:
                pass
    def terminate(self):
        if hasattr(gui, "mainFrame") and hasattr(gui.mainFrame, "sysTrayIcon"):
            try:
                if self.settings_item:
                    gui.mainFrame.sysTrayIcon.toolsMenu.RemoveItem(self.settings_item)
                if self.help_item:
                    gui.mainFrame.sysTrayIcon.helpMenu.RemoveItem(self.help_item)
            except Exception:
                pass
        super(GlobalPlugin, self).terminate()
    def onSettingsMenu(self, evt):
        gui.mainFrame.prePopup()
        d = SettingsDialog(gui.mainFrame)
        d.Show()
        gui.mainFrame.postPopup()
    def onHelpMenu(self, evt):
        docHandler.openDoc()
    def get_selected_or_clipboard_text(self):
        try:
            focus = api.getFocusObject()
            treeInterceptor = focus.treeInterceptor
            if treeInterceptor and hasattr(treeInterceptor, 'makeTextInfo'):
                info = treeInterceptor.makeTextInfo(textInfos.POSITION_SELECTION)
                if info and not info.isCollapsed:
                    text = info.text.strip()
                    if text:
                        return text
            if hasattr(focus, 'makeTextInfo'):
                info = focus.makeTextInfo(textInfos.POSITION_SELECTION)
                if info and not info.isCollapsed:
                    text = info.text.strip()
                    if text:
                        return text
        except Exception:
            pass
        try:
            clip = api.getClipData()
            if clip and clip.strip():
                return clip.strip()
        except Exception:
            pass
        return None
    def _async_translate(self, text, sl, tl):
        global LAST_TRANSLATION
        try:
            ui.message("Translating...")
            result, actual_src, actual_tgt = execute_translation(text, sl, tl)
            LAST_TRANSLATION = result
            cfg = load_config()
            if cfg.get("copyToClipboard", False):
                api.copyToClip(result)
            if cfg.get("speakResult", True):
                ui.message(result)
            add_session_history({
                "original": text,
                "translated": result,
                "from": actual_src,
                "to": actual_tgt
            })
        except Exception as e:
            ui.message(f"Translation Error: {str(e)}")
    def script_translate(self, gesture):
        text = self.get_selected_or_clipboard_text()
        if not text:
            ui.message("No text selected or found in clipboard.")
            return
        cfg = load_config()
        sl = "auto" if cfg.get("autoDetect", True) else cfg.get("sourceLang", "en")
        tl = cfg.get("targetLang", "th")
        threading.Thread(target=self._async_translate, args=(text, sl, tl), daemon=True).start()
    script_translate.__doc__ = "Translates selected text or clipboard content using OmniTranslate."
    def script_swapLanguages(self, gesture):
        cfg = load_config()
        src = cfg.get("sourceLang", "en")
        tgt = cfg.get("targetLang", "th")
        cfg["sourceLang"] = tgt
        cfg["targetLang"] = src
        save_config(cfg)
        src_name = AVAILABLE_LANGUAGES.get(tgt, tgt)
        tgt_name = AVAILABLE_LANGUAGES.get(src, src)
        ui.message(f"Languages swapped: Secondary {src_name}, Target {tgt_name}")
    script_swapLanguages.__doc__ = "Swaps primary source and target languages."
    def script_quickSwitch(self, gesture):
        cfg = load_config()
        slots = [cfg.get(f"quickSlot{i}", "en") for i in range(1, 6)]
        self.current_slot_index = (self.current_slot_index + 1) % len(slots)
        next_lang = slots[self.current_slot_index]
        cfg["targetLang"] = next_lang
        save_config(cfg)
        lang_name = AVAILABLE_LANGUAGES.get(next_lang, next_lang)
        ui.message(f"Target: Slot {self.current_slot_index + 1} ({lang_name})")
    script_quickSwitch.__doc__ = "Cycles through 5 configured quick-switch target language slots."
    def script_openViewer(self, gesture):
        global LAST_TRANSLATION
        if not LAST_TRANSLATION:
            ui.message("No translation available to view.")
            return
        gui.mainFrame.prePopup()
        d = ResultViewerDialog(gui.mainFrame, LAST_TRANSLATION)
        d.Show()
        gui.mainFrame.postPopup()
    script_openViewer.__doc__ = "Opens accessible Result Viewer dialog."
    def script_openHistory(self, gesture):
        gui.mainFrame.prePopup()
        d = HistoryDialog(gui.mainFrame)
        d.Show()
        gui.mainFrame.postPopup()
    script_openHistory.__doc__ = "Opens translation history dialog."
    def script_toggleSpeech(self, gesture):
        cfg = load_config()
        cfg["speakResult"] = not cfg.get("speakResult", True)
        save_config(cfg)
        state = "enabled" if cfg["speakResult"] else "disabled"
        ui.message(f"Speech output {state}")
    script_toggleSpeech.__doc__ = "Toggles automatic speech output."
    def script_repeatLast(self, gesture):
        global LAST_TRANSLATION
        if LAST_TRANSLATION:
            ui.message(LAST_TRANSLATION)
        else:
            ui.message("No recent translation.")
    script_repeatLast.__doc__ = "Repeats the last translated result."
    def script_copyLast(self, gesture):
        global LAST_TRANSLATION
        if LAST_TRANSLATION:
            if api.copyToClip(LAST_TRANSLATION):
                ui.message("Last result copied to clipboard.")
        else:
            ui.message("No recent translation.")
    script_copyLast.__doc__ = "Copies the last translated result to clipboard."
    def script_openSettings(self, gesture):
        gui.mainFrame.prePopup()
        d = SettingsDialog(gui.mainFrame)
        d.Show()
        gui.mainFrame.postPopup()
    script_openSettings.__doc__ = "Opens OmniTranslate configuration dialog."
    __gestures = {
        "kb:NVDA+shift+t": "translate",
        "kb:NVDA+shift+s": "swapLanguages",
        "kb:NVDA+shift+j": "quickSwitch",
        "kb:NVDA+shift+v": "openViewer",
        "kb:NVDA+shift+h": "openHistory",
        "kb:NVDA+shift+m": "toggleSpeech",
        "kb:NVDA+shift+z": "repeatLast",
        "kb:NVDA+shift+c": "copyLast",
        "kb:NVDA+shift+o": "openSettings",
    }