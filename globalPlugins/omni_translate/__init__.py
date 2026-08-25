import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import wx
import api
import globalPluginHandler
import scriptHandler
import textInfos
import ui
import gui
import globalVars
import queueHandler
CONFIG_FILE = os.path.join(globalVars.appArgs.configPath, "omni_translate_conf.json")
HISTORY_FILE = os.path.join(globalVars.appArgs.configPath, "omni_translate_history.json")
DEFAULT_CONFIG = {
    "sourceLang": "en",
    "targetLang": "th",
    "quickSlot1": "th",
    "quickSlot2": "en",
    "quickSlot3": "ja",
    "quickSlot4": "zh-CN",
    "quickSlot5": "ko",
    "autoDetectMode": True,
    "copyToClipboard": False,
    "speakTranslation": True
}
AVAILABLE_LANGUAGES = [
    ("en", "English"),
    ("th", "Thai - ภาษาไทย"),
    ("ko", "Korean - 한국어 (Hangugeo)"),
    ("ja", "Japanese - 日本語 (Nihongo)"),
    ("zh-CN", "Chinese Simplified - 简体中文"),
    ("zh-TW", "Chinese Traditional - 繁體中文"),
    ("de", "German - Deutsch"),
    ("fr", "French - Français"),
    ("es", "Spanish - Español"),
    ("ru", "Russian - Русский"),
    ("it", "Italian - Italiano"),
    ("pt", "Portuguese - Português"),
    ("vi", "Vietnamese - Tiếng Việt"),
    ("id", "Indonesian - Bahasa Indonesia"),
    ("ar", "Arabic - العربية"),
    ("hi", "Hindi - हिन्दी"),
    ("af", "Afrikaans"),
    ("sq", "Albanian - Shqip"),
    ("am", "Amharic - አማርኛ"),
    ("hy", "Armenian - Հայերեն"),
    ("az", "Azerbaijani - Azərbaycan"),
    ("eu", "Basque - Euskara"),
    ("be", "Belarusian - Беларуская"),
    ("bn", "Bengali - বাংলা"),
    ("bs", "Bosnian - Bosanski"),
    ("bg", "Bulgarian - Български"),
    ("ca", "Catalan - Català"),
    ("ceb", "Cebuano - Sinugboanon"),
    ("co", "Corsican - Corsu"),
    ("hr", "Croatian - Hrvatski"),
    ("cs", "Czech - Čeština"),
    ("da", "Danish - Dansk"),
    ("nl", "Dutch - Nederlands"),
    ("eo", "Esperanto"),
    ("et", "Estonian - Eesti"),
    ("fil", "Filipino (Tagalog) - Wikang Filipino"),
    ("fi", "Finnish - Suomi"),
    ("fy", "Frisian - Frysk"),
    ("gl", "Galician - Galego"),
    ("ka", "Georgian - ქართული"),
    ("el", "Greek - Ελληνικά"),
    ("gu", "Gujarati - ગુજરાતી"),
    ("ht", "Haitian Creole - Kreyòl Ayisyen"),
    ("ha", "Hausa"),
    ("haw", "Hawaiian - ʻŌlelo Hawaiʻi"),
    ("he", "Hebrew - עברית"),
    ("hmn", "Hmong - Hmoob"),
    ("hu", "Hungarian - Magyar"),
    ("is", "Icelandic - Íslenska"),
    ("ig", "Igbo - Asụsụ Igbo"),
    ("ga", "Irish - Gaeilge"),
    ("jv", "Javanese - Basa Jawa (ชวา)"),
    ("kn", "Kannada - ಕನ್ನಡ"),
    ("kk", "Kazakh - Қазақชา"),
    ("km", "Khmer - ភាសាខ្មែរ"),
    ("rw", "Kinyarwanda - Ikinyarwanda"),
    ("ku", "Kurdish - Kurdî"),
    ("ky", "Kyrgyz - Кыргызча"),
    ("lo", "Lao - ພາສາລາວ"),
    ("la", "Latin - Latina"),
    ("lv", "Latvian - Latviešu"),
    ("lt", "Lithuanian - Lietuvių"),
    ("lb", "Luxembourgish - Lëtzebuergesch"),
    ("mk", "Macedonian - Македонски"),
    ("mg", "Malagasy"),
    ("ms", "Malay - Bahasa Melayu"),
    ("ml", "Malayalam - മലയാളം"),
    ("mt", "Maltese - Malti"),
    ("mi", "Maori - Te Reo Māori"),
    ("mr", "Marathi - मराठी"),
    ("mn", "Mongolian - Монгол"),
    ("my", "Myanmar (Burmese) - မြန်မာစာ"),
    ("ne", "Nepali - Nepali"),
    ("no", "Norwegian - Norsk"),
    ("ny", "Nyanja (Chichewa) - Chichewa"),
    ("or", "Odia (Oriya) - ଓଡ଼ିଆ"),
    ("ps", "Pashto - پښتو"),
    ("fa", "Persian - فارسی"),
    ("pl", "Polish - Polski"),
    ("pa", "Punjabi - ਪੰਜਾਬੀ"),
    ("ro", "Romanian - Română"),
    ("sm", "Samoan - Gagana Samoa"),
    ("gd", "Scots Gaelic - Gàidhlig"),
    ("sr", "Serbian - Српски"),
    ("st", "Sesotho"),
    ("sn", "Shona - ChiShona"),
    ("sd", "Sindhi - سنڌي"),
    ("si", "Sinhala - Sinhala"),
    ("sk", "Slovak - Slovenčina"),
    ("sl", "Slovenian - Slovenščina"),
    ("so", "Somali - Soomaali"),
    ("su", "Sundanese - Basa Sunda"),
    ("sw", "Swahili - Kiswahili"),
    ("sv", "Swedish - Svenska"),
    ("tg", "Tajik - Тоҷикӣ"),
    ("ta", "Tamil - தமிழ்"),
    ("tt", "Tatar - Татарча"),
    ("te", "Telugu - తెలుగు"),
    ("tr", "Turkish - Türkçe"),
    ("tk", "Turkmen - Türkmençe"),
    ("uk", "Ukrainian - Українська"),
    ("ur", "Urdu - اردو"),
    ("ug", "Uyghur - ئۇيغۇرچە"),
    ("uz", "Uzbek - Oʻzbek"),
    ("cy", "Welsh - Cymraeg"),
    ("xh", "Xhosa - isiXhosa"),
    ("yi", "Yiddish - Yiddish"),
    ("yo", "Yoruba - Èdè Yorùbá"),
    ("zu", "Zulu - isiZulu"),
]
QUICK_SLOT_CHOICES = [("none", "-- None (Disabled) --")] + AVAILABLE_LANGUAGES
def load_conf():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()
def save_conf(conf):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []
def add_to_history(original, translated):
    history = load_history()
    entry = {"original": original, "translated": translated, "time": time.strftime("%H:%M:%S")}
    history.insert(0, entry)
    history = history[:10]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def get_lang_name(code):
    for c, name in AVAILABLE_LANGUAGES:
        if c == code:
            return name
    return code
def get_selected_text_fast():
    try:
        obj = api.getFocusObject()
        treeInterceptor = getattr(obj, "treeInterceptor", None)
        if treeInterceptor and hasattr(treeInterceptor, "makeTextInfo"):
            info = treeInterceptor.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and info.text and info.text.strip():
                return info.text.strip()
    except Exception:
        pass
    try:
        obj = api.getFocusObject()
        if hasattr(obj, "makeTextInfo"):
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and info.text and info.text.strip():
                return info.text.strip()
    except Exception:
        pass
    try:
        clip = api.getClipData()
        if clip and clip.strip():
            return clip.strip()
    except Exception:
        pass
    return ""
def execute_translation(text, source_lang, target_lang, auto_mode=True):
    sl = "auto" if auto_mode else source_lang
    tl = target_lang
    try:
        query_params = {
            "client": "gtx",
            "sl": sl,
            "tl": tl,
            "dt": "t",
            "ie": "UTF-8",
            "oe": "UTF-8",
            "q": text
        }
        encoded_url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(query_params, encoding="utf-8")
        req = urllib.request.Request(
            encoded_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Charset": "utf-8"
            }
        )
        with urllib.request.urlopen(req, timeout=3.5) as res:
            charset = res.headers.get_content_charset() or "utf-8"
            raw_data = res.read().decode(charset, errors="replace")
            data = json.loads(raw_data)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                parts = [str(item[0]) for item in data[0] if item and len(item) > 0 and item[0]]
                if parts:
                    return "".join(parts)
    except Exception:
        pass
    try:
        m_params = {
            "sl": sl,
            "tl": tl,
            "ie": "UTF-8",
            "q": text
        }
        m_url = "https://translate.google.com/m?" + urllib.parse.urlencode(m_params, encoding="utf-8")
        m_req = urllib.request.Request(
            m_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Android; Mobile; rv:40.0) Gecko/40.0 Firefox/40.0",
                "Accept-Charset": "utf-8"
            }
        )
        with urllib.request.urlopen(m_req, timeout=3.5) as m_res:
            m_charset = m_res.headers.get_content_charset() or "utf-8"
            html = m_res.read().decode(m_charset, errors="replace")
            match = re.search(r'class="result-container">([^<]+)<', html)
            if match:
                import html as html_lib
                return html_lib.unescape(match.group(1))
    except Exception:
        pass
    return ""
class ResultViewerDialog(wx.Dialog):
    def __init__(self, parent, text):
        super().__init__(parent, title="OmniTranslate - Result Viewer", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.text = text
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.textCtrl = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        sizer.Add(self.textCtrl, 1, wx.EXPAND | wx.ALL, 10)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        copyBtn = wx.Button(self, label="&Copy Text")
        closeBtn = wx.Button(self, wx.ID_CLOSE, label="&Close")
        copyBtn.Bind(wx.EVT_BUTTON, self.onCopy)
        closeBtn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        btnSizer.Add(copyBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(closeBtn, 0)
        sizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizer(sizer)
        self.SetSize((500, 350))
        self.CenterOnScreen()
        self.textCtrl.SetFocus()
    def onCopy(self, event):
        try:
            api.copyToClip(self.text)
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "Copied to clipboard")
        except Exception:
            pass
class HistoryDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="OmniTranslate - Translation History", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.history = load_history()
        sizer = wx.BoxSizer(wx.VERTICAL)
        items = [f"[{h.get('time', '')}] {h.get('original', '')[:30]} -> {h.get('translated', '')[:40]}" for h in self.history]
        if not items:
            items = ["No translation history recorded yet"]
        self.listBox = wx.ListBox(self, choices=items)
        if self.history:
            self.listBox.SetSelection(0)
        sizer.Add(self.listBox, 1, wx.EXPAND | wx.ALL, 10)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        viewBtn = wx.Button(self, label="&View Full")
        copyBtn = wx.Button(self, label="&Copy Translated")
        closeBtn = wx.Button(self, wx.ID_CLOSE, label="&Close")
        viewBtn.Bind(wx.EVT_BUTTON, self.onView)
        copyBtn.Bind(wx.EVT_BUTTON, self.onCopy)
        closeBtn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        btnSizer.Add(viewBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(copyBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(closeBtn, 0)
        sizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizer(sizer)
        self.SetSize((550, 400))
        self.CenterOnScreen()
    def onView(self, event):
        idx = self.listBox.GetSelection()
        if idx != wx.NOT_FOUND and self.history:
            entry = self.history[idx]
            msg = f"Original:\n{entry.get('original', '')}\n\nTranslated:\n{entry.get('translated', '')}"
            dlg = ResultViewerDialog(self, msg)
            dlg.ShowModal()
            dlg.Destroy()
    def onCopy(self, event):
        idx = self.listBox.GetSelection()
        if idx != wx.NOT_FOUND and self.history:
            entry = self.history[idx]
            api.copyToClip(entry.get('translated', ''))
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "Copied translation to clipboard")
class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="OmniTranslate Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.conf = load_conf()
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        lang_labels = [lang[1] for lang in AVAILABLE_LANGUAGES]
        lang_codes = [lang[0] for lang in AVAILABLE_LANGUAGES]
        slot_labels = [lang[1] for lang in QUICK_SLOT_CHOICES]
        slot_codes = [lang[0] for lang in QUICK_SLOT_CHOICES]
        mainSizer.Add(wx.StaticText(self, label="Source Language:"), 0, wx.ALL, 4)
        self.srcChoice = wx.Choice(self, choices=lang_labels)
        currentSrc = self.conf.get("sourceLang", "en")
        self.srcChoice.SetSelection(lang_codes.index(currentSrc) if currentSrc in lang_codes else 0)
        mainSizer.Add(self.srcChoice, 0, wx.EXPAND | wx.ALL, 4)
        mainSizer.Add(wx.StaticText(self, label="Target Language:"), 0, wx.ALL, 4)
        self.targetChoice = wx.Choice(self, choices=lang_labels)
        currentTarget = self.conf.get("targetLang", "th")
        self.targetChoice.SetSelection(lang_codes.index(currentTarget) if currentTarget in lang_codes else 1)
        mainSizer.Add(self.targetChoice, 0, wx.EXPAND | wx.ALL, 4)
        self.slotChoices = []
        for i in range(1, 6):
            key = f"quickSlot{i}"
            val = self.conf.get(key, DEFAULT_CONFIG.get(key, "none"))
            mainSizer.Add(wx.StaticText(self, label=f"Quick-Cycle Target Slot {i} (NVDA+Shift+L):"), 0, wx.ALL, 3)
            choice = wx.Choice(self, choices=slot_labels)
            choice.SetSelection(slot_codes.index(val) if val in slot_codes else 0)
            mainSizer.Add(choice, 0, wx.EXPAND | wx.ALL, 3)
            self.slotChoices.append(choice)
        self.autoDetectCheck = wx.CheckBox(
            self, 
            label="Auto-detect source language"
        )
        self.autoDetectCheck.SetValue(self.conf.get("autoDetectMode", True))
        mainSizer.Add(self.autoDetectCheck, 0, wx.ALL, 4)
        self.speakCheck = wx.CheckBox(self, label="Speak translation aloud via Screen Reader")
        self.speakCheck.SetValue(self.conf.get("speakTranslation", True))
        mainSizer.Add(self.speakCheck, 0, wx.ALL, 4)
        self.copyCheck = wx.CheckBox(self, label="Automatically copy translated text to clipboard")
        self.copyCheck.SetValue(self.conf.get("copyToClipboard", False))
        mainSizer.Add(self.copyCheck, 0, wx.ALL, 4)
        btnSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        mainSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        self.CenterOnScreen()
    def save(self):
        slot_codes = [lang[0] for lang in QUICK_SLOT_CHOICES]
        self.conf["sourceLang"] = AVAILABLE_LANGUAGES[self.srcChoice.GetSelection()][0]
        self.conf["targetLang"] = AVAILABLE_LANGUAGES[self.targetChoice.GetSelection()][0]
        for i, choice in enumerate(self.slotChoices, start=1):
            sel_code = slot_codes[choice.GetSelection()]
            self.conf[f"quickSlot{i}"] = sel_code
        self.conf["autoDetectMode"] = self.autoDetectCheck.GetValue()
        self.conf["speakTranslation"] = self.speakCheck.GetValue()
        self.conf["copyToClipboard"] = self.copyCheck.GetValue()
        save_conf(self.conf)
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.last_translated_text = ""
        self.last_original_text = ""
    def show_settings_dialog(self):
        def _show():
            try:
                dlg = SettingsDialog(gui.mainFrame)
                if dlg.ShowModal() == wx.ID_OK:
                    dlg.save()
                    queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "Settings saved")
                dlg.Destroy()
            except Exception as e:
                queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"Error: {str(e)}")
        wx.CallAfter(_show)
    def _worker(self, text, conf):
        try:
            res = execute_translation(
                text,
                source_lang=conf.get("sourceLang", "en"),
                target_lang=conf.get("targetLang", "th"),
                auto_mode=conf.get("autoDetectMode", True)
            )
            if not res or not res.strip():
                queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "No translation result")
                return
            self.last_translated_text = res
            self.last_original_text = text
            add_to_history(text, res)
            if conf.get("speakTranslation", True):
                queueHandler.queueFunction(queueHandler.eventQueue, ui.message, res)
            if conf.get("copyToClipboard", False):
                try:
                    api.copyToClip(res)
                except Exception:
                    pass
        except Exception as e:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"Translation error: {str(e)}")
    @scriptHandler.script(
        description="Translate selected text or clipboard content (NVDA+Shift+T)",
        category="OmniTranslate"
    )
    def script_translate(self, gesture):
        conf = load_conf()
        text = get_selected_text_fast()
        if not text:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "No text found to translate")
            return
        if conf.get("speakTranslation", True):
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "Translating...")
        t = threading.Thread(target=self._worker, args=(text, conf))
        t.daemon = True
        t.start()
    @scriptHandler.script(
        description="Swap source and target languages (NVDA+Shift+S)",
        category="OmniTranslate"
    )
    def script_swap(self, gesture):
        conf = load_conf()
        src = conf.get("sourceLang", "en")
        target = conf.get("targetLang", "th")
        conf["sourceLang"] = target
        conf["targetLang"] = src
        save_conf(conf)
        queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"Swapped: {get_lang_name(target)} to {get_lang_name(src)}")
    @scriptHandler.script(
        description="Quick cycle target language across the 5 configured slots (NVDA+Shift+L)",
        category="OmniTranslate"
    )
    def script_quickSwitch(self, gesture):
        conf = load_conf()
        cycle_list = []
        for i in range(1, 6):
            slot_val = conf.get(f"quickSlot{i}", "none")
            if slot_val and slot_val != "none" and slot_val not in cycle_list:
                cycle_list.append(slot_val)
        if not cycle_list:
            cycle_list = ["th", "en"]
        cur_target = conf.get("targetLang", "th")
        if cur_target in cycle_list:
            idx = (cycle_list.index(cur_target) + 1) % len(cycle_list)
            new_target = cycle_list[idx]
        else:
            new_target = cycle_list[0]
        conf["targetLang"] = new_target
        save_conf(conf)
        queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"Target: {get_lang_name(new_target)}")
    @scriptHandler.script(
        description="Toggle speech output for translations / Silent Mode (NVDA+Shift+M)",
        category="OmniTranslate"
    )
    def script_toggleSpeech(self, gesture):
        conf = load_conf()
        new_val = not conf.get("speakTranslation", True)
        conf["speakTranslation"] = new_val
        save_conf(conf)
        queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "Speech output ON" if new_val else "Silent mode ON (Speech OFF)")
    @scriptHandler.script(
        description="Open translation result viewer for detailed reading (NVDA+Shift+V)",
        category="OmniTranslate"
    )
    def script_openViewer(self, gesture):
        if not self.last_translated_text:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "No translation available to view")
            return
        def _show():
            dlg = ResultViewerDialog(gui.mainFrame, self.last_translated_text)
            dlg.ShowModal()
            dlg.Destroy()
        wx.CallAfter(_show)
    @scriptHandler.script(
        description="Open Translation History dialog (NVDA+Shift+H)",
        category="OmniTranslate"
    )
    def script_openHistory(self, gesture):
        def _show():
            dlg = HistoryDialog(gui.mainFrame)
            dlg.ShowModal()
            dlg.Destroy()
        wx.CallAfter(_show)
    @scriptHandler.script(
        description="Open OmniTranslate Settings dialog (NVDA+Shift+O)",
        category="OmniTranslate"
    )
    def script_openSettings(self, gesture):
        self.show_settings_dialog()
    @scriptHandler.script(
        description="Announce last translated text (NVDA+Shift+A)",
        category="OmniTranslate"
    )
    def script_announceLast(self, gesture):
        if self.last_translated_text:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, self.last_translated_text)
        else:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "No previous translation available")
    @scriptHandler.script(
        description="Copy last translated text to clipboard (NVDA+Shift+C)",
        category="OmniTranslate"
    )
    def script_copyLast(self, gesture):
        if self.last_translated_text:
            try:
                api.copyToClip(self.last_translated_text)
                queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "Copied last translation to clipboard")
            except Exception:
                pass
        else:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "No previous translation available")
    __gestures = {
        "kb:NVDA+shift+t": "translate",
        "kb:NVDA+shift+s": "swap",
        "kb:NVDA+shift+l": "quickSwitch",
        "kb:NVDA+shift+v": "openViewer",
        "kb:NVDA+shift+h": "openHistory",
        "kb:NVDA+shift+m": "toggleSpeech",
        "kb:NVDA+shift+o": "openSettings",
        "kb:NVDA+shift+a": "announceLast",
        "kb:NVDA+shift+c": "copyLast",
    }