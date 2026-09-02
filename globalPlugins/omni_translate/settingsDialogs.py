# -*- coding: utf-8 -*-
# OmniTranslate - Settings Panels & Dialogs with Dynamic Language Filtering
# Author: Isara Watthanawirojkul

import os
import json
import wx
import gui
from gui.settingsDialogs import SettingsPanel
import logHandler
import addonHandler
import globalVars
import api
import ui
import tones
from . import offlineEngine

addonHandler.initTranslation()

CONFIG_FILE = os.path.join(globalVars.appArgs.configPath, "omni_translate_config.json")

SESSION_HISTORY = []

AVAILABLE_LANGUAGES = {
    "auto": _("Auto Detect"),
    "ab": _("Abkhaz"),
    "ace": _("Acehnese"),
    "ace-Arab": _("Acehnese (Arabic)"),
    "ach": _("Acholi"),
    "aa": _("Afar"),
    "af": _("Afrikaans"),
    "sq": _("Albanian"),
    "alz": _("Alur"),
    "am": _("Amharic"),
    "ar": _("Arabic"),
    "hy": _("Armenian"),
    "as": _("Assamese"),
    "ast": _("Asturian"),
    "av": _("Avar"),
    "awa": _("Awadhi"),
    "ay": _("Aymara"),
    "az": _("Azerbaijani"),
    "ban": _("Balinese"),
    "bal": _("Baluchi"),
    "bm": _("Bambara"),
    "bjn-Arab": _("Banjar (Arabic)"),
    "bjn": _("Banjar (Latin)"),
    "bci": _("Baoulé"),
    "ba": _("Bashkir"),
    "eu": _("Basque"),
    "btx": _("Batak Karo"),
    "bts": _("Batak Simalungun"),
    "bbc": _("Batak Toba"),
    "be": _("Belarusian"),
    "bem": _("Bemba"),
    "bn": _("Bengali"),
    "bew": _("Betawi"),
    "bho": _("Bhojpuri"),
    "bik": _("Bikol"),
    "bs": _("Bosnian"),
    "br": _("Breton"),
    "bug": _("Buginese"),
    "bg": _("Bulgarian"),
    "bua": _("Buryat"),
    "yue": _("Cantonese"),
    "ca": _("Catalan"),
    "ceb": _("Cebuano"),
    "tzm": _("Central Atlas Tamazight"),
    "knc-Arab": _("Central Kanuri (Arabic)"),
    "knc": _("Central Kanuri (Latin)"),
    "ch": _("Chamorro"),
    "ce": _("Chechen"),
    "hne": _("Chhattisgarhi"),
    "ny": _("Chichewa"),
    "zh-CN": _("Chinese (Simplified)"),
    "zh-TW": _("Chinese (Traditional)"),
    "cjk": _("Chokwe"),
    "chk": _("Chuukese"),
    "cv": _("Chuvash"),
    "co": _("Corsican"),
    "crh": _("Crimean Tatar (Cyrillic)"),
    "crh-Latn": _("Crimean Tatar (Latin)"),
    "hr": _("Croatian"),
    "cs": _("Czech"),
    "da": _("Danish"),
    "fa-AF": _("Dari"),
    "prs": _("Dari"),
    "dv": _("Dhivehi"),
    "din": _("Dinka"),
    "dik": _("Dinka"),
    "doi": _("Dogri"),
    "dov": _("Dombe"),
    "nl": _("Dutch"),
    "dyu": _("Dyula"),
    "dz": _("Dzongkha"),
    "arz": _("Egyptian Arabic"),
    "en": _("English"),
    "eo": _("Esperanto"),
    "et": _("Estonian"),
    "ee": _("Ewe"),
    "fo": _("Faroese"),
    "fj": _("Fijian"),
    "tl": _("Filipino"),
    "fi": _("Finnish"),
    "fon": _("Fon"),
    "fr": _("French"),
    "fr-CA": _("French (Canada)"),
    "fy": _("Frisian"),
    "fur": _("Friulian"),
    "ff": _("Fulani"),
    "gaa": _("Ga"),
    "gl": _("Galician"),
    "ka": _("Georgian"),
    "de": _("German"),
    "el": _("Greek"),
    "gn": _("Guarani"),
    "gu": _("Gujarati"),
    "ht": _("Haitian Creole"),
    "cnh": _("Hakha Chin"),
    "ha": _("Hausa"),
    "haw": _("Hawaiian"),
    "iw": _("Hebrew"),
    "he": _("Hebrew"),
    "hil": _("Hiligaynon"),
    "hi": _("Hindi"),
    "hmn": _("Hmong"),
    "hu": _("Hungarian"),
    "hrx": _("Hunsrik"),
    "iba": _("Iban"),
    "is": _("Icelandic"),
    "ig": _("Igbo"),
    "ilo": _("Ilocano"),
    "id": _("Indonesian"),
    "iu-Latn": _("Inuktut (Latin)"),
    "iu": _("Inuktut (Syllabics)"),
    "ga": _("Irish"),
    "gle": _("Irish"),
    "it": _("Italian"),
    "jam": _("Jamaican Patois"),
    "ja": _("Japanese"),
    "jw": _("Javanese"),
    "kac": _("Jingpo"),
    "kbp": _("Kabiyè"),
    "kea": _("Kabuverdianu"),
    "kab": _("Kabyle"),
    "kl": _("Kalaallisut"),
    "kam": _("Kamba"),
    "kn": _("Kannada"),
    "kr": _("Kanuri"),
    "pam": _("Kapampangan"),
    "ks-Arab": _("Kashmiri (Arabic)"),
    "ks": _("Kashmiri (Devanagari)"),
    "kk": _("Kazakh"),
    "kha": _("Khasi"),
    "km": _("Khmer"),
    "cgg": _("Kiga"),
    "kg": _("Kikongo"),
    "kik": _("Kikuyu"),
    "kmb": _("Kimbundu"),
    "rw": _("Kinyarwanda"),
    "ktu": _("Kituba"),
    "trp": _("Kokborok"),
    "kv": _("Komi"),
    "gom": _("Konkani"),
    "ko": _("Korean"),
    "kri": _("Krio"),
    "ku": _("Kurdish (Kurmanji)"),
    "ckb": _("Kurdish (Sorani)"),
    "ky": _("Kyrgyz"),
    "lo": _("Lao"),
    "ltg": _("Latgalian"),
    "la": _("Latin"),
    "lv": _("Latvian"),
    "lij": _("Ligurian"),
    "li": _("Limburgish"),
    "ln": _("Lingala"),
    "lt": _("Lithuanian"),
    "lmo": _("Lombard"),
    "lg": _("Luganda"),
    "luo": _("Luo"),
    "lb": _("Luxembourgish"),
    "mk": _("Macedonian"),
    "mad": _("Madurese"),
    "mag": _("Magahi"),
    "mai": _("Maithili"),
    "mak": _("Makassar"),
    "mg": _("Malagasy"),
    "ms": _("Malay"),
    "ms-Arab": _("Malay (Jawi)"),
    "ml": _("Malayalam"),
    "mt": _("Maltese"),
    "mam": _("Mam"),
    "gv": _("Manx"),
    "mi": _("Maori"),
    "mr": _("Marathi"),
    "mh": _("Marshallese"),
    "mwr": _("Marwadi"),
    "mfe": _("Mauritian Creole"),
    "chm": _("Meadow Mari"),
    "mni-Mtei": _("Meiteilon (Manipuri)"),
    "acm": _("Mesopotamian Arabic"),
    "min": _("Minang"),
    "lus": _("Mizo"),
    "mn": _("Mongolian"),
    "ary": _("Moroccan Arabic"),
    "mos": _("Mossi"),
    "my": _("Myanmar (Burmese)"),
    "bm-Nkoo": _("NKo"),
    "nhe": _("Nahuatl (Eastern Huasteca)"),
    "ars": _("Najdi Arabic"),
    "ndc-ZW": _("Ndau"),
    "nr": _("Ndebele (South)"),
    "new": _("Nepalbhasa (Newari)"),
    "ne": _("Nepali"),
    "fuv": _("Nigerian Fulfulde"),
    "apc": _("North Levantine Arabic"),
    "no": _("Norwegian"),
    "nn": _("Norwegian Nynorsk"),
    "nus": _("Nuer"),
    "oc": _("Occitan"),
    "or": _("Odia (Oriya)"),
    "om": _("Oromo"),
    "os": _("Ossetian"),
    "pag": _("Pangasinan"),
    "pap": _("Papiamento"),
    "ps": _("Pashto"),
    "fa": _("Persian"),
    "pl": _("Polish"),
    "pt": _("Portuguese (Brazil)"),
    "pt-PT": _("Portuguese (Portugal)"),
    "pa": _("Punjabi (Gurmukhi)"),
    "pa-Arab": _("Punjabi (Shahmukhi)"),
    "qu": _("Quechua"),
    "kek": _("Qʼeqchiʼ"),
    "rom": _("Romani"),
    "ro": _("Romanian"),
    "rn": _("Rundi"),
    "ru": _("Russian"),
    "se": _("Sami (North)"),
    "sm": _("Samoan"),
    "sg": _("Sango"),
    "sa": _("Sanskrit"),
    "sat-Latn": _("Santali (Latin)"),
    "sat": _("Santali (Ol Chiki)"),
    "sc": _("Sardinian"),
    "gd": _("Scots Gaelic"),
    "nso": _("Sepedi"),
    "sr": _("Serbian"),
    "st": _("Sesotho"),
    "crs": _("Seychellois Creole"),
    "shn": _("Shan"),
    "sn": _("Shona"),
    "scn": _("Sicilian"),
    "szl": _("Silesian"),
    "sd": _("Sindhi"),
    "si": _("Sinhala"),
    "sk": _("Slovak"),
    "sl": _("Slovenian"),
    "so": _("Somali"),
    "azb": _("South Azerbaijani"),
    "ajp": _("South Levantine Arabic"),
    "es": _("Spanish"),
    "su": _("Sundanese"),
    "sus": _("Susu"),
    "sw": _("Swahili"),
    "ss": _("Swati"),
    "sv": _("Swedish"),
    "acq": _("Ta'izzi-Adeni Arabic"),
    "ty": _("Tahitian"),
    "tg": _("Tajik"),
    "taq": _("Tamasheq (Latin)"),
    "taq-Tfng": _("Tamasheq (Tifinagh)"),
    "ber-Latn": _("Tamazight"),
    "ber": _("Tamazight (Tifinagh)"),
    "ta": _("Tamil"),
    "tt": _("Tatar"),
    "te": _("Telugu"),
    "tet": _("Tetum"),
    "th": _("Thai"),
    "bo": _("Tibetan"),
    "ti": _("Tigrinya"),
    "tiv": _("Tiv"),
    "tpi": _("Tok Pisin"),
    "to": _("Tongan"),
    "lua": _("Tshiluba"),
    "ts": _("Tsonga"),
    "tn": _("Tswana"),
    "tcy": _("Tulu"),
    "tum": _("Tumbuka"),
    "aeb": _("Tunisian Arabic"),
    "tr": _("Turkish"),
    "tk": _("Turkmen"),
    "tyv": _("Tuvan"),
    "ak": _("Twi"),
    "twi": _("Twi"),
    "udm": _("Udmurt"),
    "uk": _("Ukrainian"),
    "umb": _("Umbundu"),
    "ur": _("Urdu"),
    "ug": _("Uyghur"),
    "uz": _("Uzbek"),
    "ve": _("Venda"),
    "vec": _("Venetian"),
    "vi": _("Vietnamese"),
    "war": _("Waray"),
    "cy": _("Welsh"),
    "wo": _("Wolof"),
    "xh": _("Xhosa"),
    "sah": _("Yakut"),
    "yi": _("Yiddish"),
    "yo": _("Yoruba"),
    "yua": _("Yucatec Maya"),
    "zap": _("Zapotec"),
    "zu": _("Zulu"),
}


_CLEAN_ALL_LANGUAGES = {k: v for k, v in AVAILABLE_LANGUAGES.items() if k != "auto"}
_CLEAN_ALL_LANG_KEYS = list(_CLEAN_ALL_LANGUAGES.keys())
_CLEAN_ALL_LANG_NAMES = list(_CLEAN_ALL_LANGUAGES.values())
_NLLB_SUPPORTED_SET = set(offlineEngine.NLLB_LANG_MAP.keys())
_NLLB_LANGUAGES_MAP = {
    code: name for code, name in _CLEAN_ALL_LANGUAGES.items()
    if code.lower() in _NLLB_SUPPORTED_SET or code.lower().split("-")[0] in _NLLB_SUPPORTED_SET
}


def get_available_languages_for_mode(mode="online", model_id=None):
    """Returns a dict of language_code: language_name filtered by the active mode and selected offline model."""
    if mode == "online":
        return _CLEAN_ALL_LANGUAGES

    # Offline Mode: filter by model capability
    if not model_id or model_id == "none":
        installed = offlineEngine.get_installed_offline_models()
        model_id = installed[0] if installed else "none"

    supp_info = offlineEngine.get_model_supported_languages(model_id)
    if supp_info.get("is_multilingual", True):
        # Multilingual models (such as NLLB-200) support 200+ languages and handle token fallbacks gracefully.
        # Keeping unified language mapping prevents costly combobox repopulation and eliminates UI lag during mode switching.
        return _CLEAN_ALL_LANGUAGES

    # Bilingual Single-Pair Model (Only filter when the model strictly supports 1 specific language pair)
    bilingual_keys = set(supp_info.get("src", [])) | set(supp_info.get("tgt", []))
    filtered = {}
    for code, name in _CLEAN_ALL_LANGUAGES.items():
        if code.lower() in bilingual_keys or code.lower().split("-")[0] in bilingual_keys:
            filtered[code] = name
    return filtered if filtered else _CLEAN_ALL_LANGUAGES

DEFAULT_CONFIG = {
    "translationMode": "online",
    "sourceLang": "en",
    "targetLang": "th",
    "autoDetect": True,
    "copyToClipboard": False,
    "translateClipboard": True,
    "replaceSelection": False,
    "speakResult": True,
    "quickSlot1": "none",
    "quickSlot2": "none",
    "quickSlot3": "none",
    "quickSlot4": "none",
    "quickSlot5": "none",
    "offlineModel": "none"
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            res = DEFAULT_CONFIG.copy()
            res.update(cfg)
            return res
        except Exception as e:
            logHandler.log.error(f"OmniTranslate: Error loading configuration: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg_updates):
    try:
        current_cfg = load_config()
        current_cfg.update(cfg_updates)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current_cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Error saving configuration: {e}")


class ResultViewerDialog(wx.Dialog):
    def __init__(self, parent, result_text):
        super(ResultViewerDialog, self).__init__(
            parent,
            title=_("OmniTranslate - Translation Result"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.result_text = result_text
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.textCtrl = wx.TextCtrl(self, value=result_text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        sizer.Add(self.textCtrl, 1, wx.EXPAND | wx.ALL, 10)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        copyBtn = wx.Button(self, label=_("&Copy to Clipboard"))
        closeBtn = wx.Button(self, wx.ID_CLOSE, label=_("&Close"))
        copyBtn.Bind(wx.EVT_BUTTON, self.onCopy)
        closeBtn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())

        btnSizer.Add(copyBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(closeBtn, 0)
        sizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        self.SetSize((550, 380))
        self.CenterOnScreen()
        self.textCtrl.SetFocus()

    def onCopy(self, evt):
        if api.copyToClip(self.result_text):
            ui.message(_("Copied to clipboard"))
        self.Close()


class HistoryDialog(wx.Dialog):
    def __init__(self, parent, history_data=None):
        super(HistoryDialog, self).__init__(
            parent,
            title=_("OmniTranslate - History"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.history = history_data if history_data is not None else SESSION_HISTORY
        sizer = wx.BoxSizer(wx.VERTICAL)
        choices = [
            f"[{h.get('from', '?')}->{h.get('to', '?')}] {h.get('original', '')[:25]}... -> {h.get('translated', '')[:25]}..."
            for h in self.history
        ]
        if not choices:
            choices = [_("No translation history available for this session.")]

        self.listBox = wx.ListBox(self, choices=choices)
        self.listBox.SetSelection(0)
        sizer.Add(self.listBox, 1, wx.EXPAND | wx.ALL, 10)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        viewBtn = wx.Button(self, label=_("&View Full Translation"))
        closeBtn = wx.Button(self, wx.ID_CLOSE, label=_("&Close"))
        viewBtn.Bind(wx.EVT_BUTTON, self.onView)
        closeBtn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())

        btnSizer.Add(viewBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(closeBtn, 0)
        sizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        self.SetSize((580, 420))
        self.CenterOnScreen()
        self.listBox.SetFocus()

    def onView(self, evt):
        sel = self.listBox.GetSelection()
        if sel != wx.NOT_FOUND and self.history:
            entry = self.history[sel]
            full_text = f"{_('Source')} [{entry.get('from', '?')}]:\n{entry.get('original', '')}\n\n{_('Translation')} [{entry.get('to', '?')}]:\n{entry.get('translated', '')}"
            d = ResultViewerDialog(self, full_text)
            d.ShowModal()
            d.Destroy()
            self.Close()


class OmniTranslateGeneralSettingsPanel(SettingsPanel):
    title = _("OmniTranslate: General")

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.cfg = load_config()

        # 1. Translation Mode
        mode_choices = [
            _("Online Mode (with automatic offline fallback)"),
            _("Offline Mode Only (Local Neural Engine)")
        ]
        self.modeKeys = ["online", "offline"]
        cur_mode = self.cfg.get("translationMode", "online")
        self.cur_active_mode = cur_mode
        m_idx = self.modeKeys.index(cur_mode) if cur_mode in self.modeKeys else 0
        self.modeChoice = sHelper.addLabeledControl(_("Translation mode:"), wx.Choice, choices=mode_choices)
        self.modeChoice.SetSelection(m_idx)
        self.modeChoice.Bind(wx.EVT_CHOICE, self.onModeChange)

        # 2. Dynamic Language Settings
        cur_model = self.cfg.get("offlineModel", "none")
        self.lang_map = get_available_languages_for_mode(cur_mode, cur_model)
        if self.lang_map is _CLEAN_ALL_LANGUAGES:
            self.lang_keys = _CLEAN_ALL_LANG_KEYS
            self.lang_names = _CLEAN_ALL_LANG_NAMES
        else:
            self.lang_keys = list(self.lang_map.keys())
            self.lang_names = list(self.lang_map.values())

        cur_tgt = self.cfg.get("targetLang", "th")
        tgt_idx = self.lang_keys.index(cur_tgt) if cur_tgt in self.lang_keys else 0
        self.tgtChoice = sHelper.addLabeledControl(_("Primary target language:"), wx.Choice, choices=self.lang_names)
        self.tgtChoice.SetSelection(tgt_idx)

        cur_src = self.cfg.get("sourceLang", "en")
        src_idx = self.lang_keys.index(cur_src) if cur_src in self.lang_keys else 0
        self.srcChoice = sHelper.addLabeledControl(_("Secondary swap language:"), wx.Choice, choices=self.lang_names)
        self.srcChoice.SetSelection(src_idx)

        # Quick Slots 1 - 5
        self.slot_keys = ["none"] + self.lang_keys
        self.slot_names = [_("Please select a language")] + self.lang_names
        self.slotControls = []
        for i in range(1, 6):
            slot_key = f"quickSlot{i}"
            cur_slot = self.cfg.get(slot_key, "none")
            s_idx = self.slot_keys.index(cur_slot) if cur_slot in self.slot_keys else 0
            ctrl = sHelper.addLabeledControl(_(f"Quick Slot {i}:"), wx.Choice, choices=self.slot_names)
            ctrl.SetSelection(s_idx)
            self.slotControls.append(ctrl)

        # Smart Bidirectional Checkbox
        self.autoDetectCheck = sHelper.addItem(wx.CheckBox(self, label=_("Auto-detect input language (Smart Bidirectional)")))
        self.autoDetectCheck.SetValue(self.cfg.get("autoDetect", True))

        # Output & Input Preferences
        self.speakCheck = sHelper.addItem(wx.CheckBox(self, label=_("Speak translation automatically")))
        self.speakCheck.SetValue(self.cfg.get("speakResult", True))

        self.copyCheck = sHelper.addItem(wx.CheckBox(self, label=_("Automatically copy translation to clipboard")))
        self.copyCheck.SetValue(self.cfg.get("copyToClipboard", False))

        self.translateClipboardCheck = sHelper.addItem(wx.CheckBox(self, label=_("Translate text from clipboard when no text is selected")))
        self.translateClipboardCheck.SetValue(self.cfg.get("translateClipboard", True))

        self.replaceSelectionCheck = sHelper.addItem(wx.CheckBox(self, label=_("Replace selected text with translation in editable fields")))
        self.replaceSelectionCheck.SetValue(self.cfg.get("replaceSelection", False))

    def onModeChange(self, evt):
        sel_idx = self.modeChoice.GetSelection()
        if sel_idx != wx.NOT_FOUND and 0 <= sel_idx < len(self.modeKeys):
            new_mode = self.modeKeys[sel_idx]
            if new_mode == getattr(self, "cur_active_mode", None):
                return
            self.cur_active_mode = new_mode
            wx.CallAfter(self.refreshLanguageChoices, new_mode)

    def refreshLanguageChoices(self, mode):
        if not self or not bool(self):
            return
        cur_model = self.cfg.get("offlineModel", "none")
        new_lang_map = get_available_languages_for_mode(mode, cur_model)
        if new_lang_map is _CLEAN_ALL_LANGUAGES:
            new_lang_keys = _CLEAN_ALL_LANG_KEYS
            new_lang_names = _CLEAN_ALL_LANG_NAMES
        else:
            new_lang_keys = list(new_lang_map.keys())
            new_lang_names = list(new_lang_map.values())

        if hasattr(self, "lang_keys") and new_lang_keys == self.lang_keys:
            return

        tgt_sel = self.tgtChoice.GetSelection()
        prev_tgt_key = self.lang_keys[tgt_sel] if (self.lang_keys and 0 <= tgt_sel < len(self.lang_keys)) else "th"
        
        src_sel = self.srcChoice.GetSelection()
        prev_src_key = self.lang_keys[src_sel] if (self.lang_keys and 0 <= src_sel < len(self.lang_keys)) else "en"
        
        prev_slot_keys = []
        for ctrl in self.slotControls:
            sel = ctrl.GetSelection()
            prev_slot_keys.append(self.slot_keys[sel] if (hasattr(self, "slot_keys") and 0 <= sel < len(self.slot_keys)) else "none")

        self.lang_map = new_lang_map
        self.lang_keys = new_lang_keys
        self.lang_names = new_lang_names
        self.slot_keys = ["none"] + self.lang_keys
        self.slot_names = [_("Please select a language")] + self.lang_names

        all_controls = [self.tgtChoice, self.srcChoice] + self.slotControls
        for ctrl in all_controls:
            ctrl.Freeze()
        self.Freeze()
        try:
            # Update Primary Target Choice
            self.tgtChoice.Set(self.lang_names)
            new_tgt_idx = self.lang_keys.index(prev_tgt_key) if prev_tgt_key in self.lang_keys else 0
            if self.lang_names and 0 <= new_tgt_idx < len(self.lang_names):
                self.tgtChoice.SetSelection(new_tgt_idx)

            # Update Secondary Source Choice
            self.srcChoice.Set(self.lang_names)
            new_src_idx = self.lang_keys.index(prev_src_key) if prev_src_key in self.lang_keys else 0
            if self.lang_names and 0 <= new_src_idx < len(self.lang_names):
                self.srcChoice.SetSelection(new_src_idx)

            # Update Quick Slots
            for i, ctrl in enumerate(self.slotControls):
                ctrl.Set(self.slot_names)
                prev_slot = prev_slot_keys[i] if i < len(prev_slot_keys) else "none"
                new_slot_idx = self.slot_keys.index(prev_slot) if prev_slot in self.slot_keys else 0
                if self.slot_names and 0 <= new_slot_idx < len(self.slot_names):
                    ctrl.SetSelection(new_slot_idx)
        finally:
            self.Thaw()
            for ctrl in all_controls:
                ctrl.Thaw()

    def onSave(self):
        m_sel = self.modeChoice.GetSelection()
        mode_val = self.modeKeys[m_sel] if (m_sel != wx.NOT_FOUND and 0 <= m_sel < len(self.modeKeys)) else "online"
        updates = {
            "translationMode": mode_val,
            "speakResult": self.speakCheck.GetValue(),
            "copyToClipboard": self.copyCheck.GetValue(),
            "translateClipboard": self.translateClipboardCheck.GetValue(),
            "replaceSelection": self.replaceSelectionCheck.GetValue(),
            "autoDetect": self.autoDetectCheck.GetValue()
        }
        tgt_sel = self.tgtChoice.GetSelection()
        if tgt_sel != wx.NOT_FOUND and 0 <= tgt_sel < len(self.lang_keys):
            updates["targetLang"] = self.lang_keys[tgt_sel]

        src_sel = self.srcChoice.GetSelection()
        if src_sel != wx.NOT_FOUND and 0 <= src_sel < len(self.lang_keys):
            updates["sourceLang"] = self.lang_keys[src_sel]

        for i, ctrl in enumerate(self.slotControls, 1):
            s_sel = ctrl.GetSelection()
            if s_sel != wx.NOT_FOUND and 0 <= s_sel < len(self.slot_keys):
                updates[f"quickSlot{i}"] = self.slot_keys[s_sel]

        save_config(updates)


class OmniTranslateOfflineModelsPanel(SettingsPanel):
    title = _("OmniTranslate: Offline Models")

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.cfg = load_config()

        # Offline Neural Model Manager
        self.installed = offlineEngine.get_installed_offline_models()
        self.cur_model = self.cfg.get("offlineModel", self.installed[0] if self.installed else "none")
        installed_choices = self.installed if self.installed else [_("No offline models installed")]
        self.installedChoice = sHelper.addLabeledControl(_("Active offline language model:"), wx.Choice, choices=installed_choices)
        if self.installed:
            m_sel = self.installed.index(self.cur_model) if self.cur_model in self.installed else 0
            self.installedChoice.SetSelection(m_sel)
        else:
            self.installedChoice.SetSelection(0)
        self.installedChoice.Bind(wx.EVT_CHOICE, self.onModelChange)

        self.modelInfoText = sHelper.addItem(wx.StaticText(self, label=""))
        self.updateModelInfo()

        self.catalog = offlineEngine.OFFLINE_MODELS_CATALOG
        catalog_names = [m["name"] for m in self.catalog]
        self.catalogChoice = sHelper.addLabeledControl(_("Download recommended offline model:"), wx.Choice, choices=catalog_names)
        self.catalogChoice.SetSelection(0)

        # Model Action Buttons
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.downloadBtn = wx.Button(self, label=_("&Download Model"))
        self.deleteBtn = wx.Button(self, label=_("&Delete Model"))
        self.openFolderBtn = wx.Button(self, label=_("&Open Models Folder"))

        self.downloadBtn.Bind(wx.EVT_BUTTON, self.onDownload)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.onDeleteModel)
        self.openFolderBtn.Bind(wx.EVT_BUTTON, self.onOpenFolder)

        btnSizer.Add(self.downloadBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(self.deleteBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(self.openFolderBtn, 0)
        sHelper.addItem(btnSizer)

    def onModelChange(self, evt):
        if self.installed:
            sel = self.installedChoice.GetSelection()
            if sel != wx.NOT_FOUND and 0 <= sel < len(self.installed):
                self.cur_model = self.installed[sel]
                save_config({"offlineModel": self.cur_model})
                self.updateModelInfo()

    def updateModelInfo(self):
        if not self.installed or self.cur_model == "none":
            self.modelInfoText.SetLabel(_("No model selected. Download a model to use Offline Mode."))
            return
        supp_info = offlineEngine.get_model_supported_languages(self.cur_model)
        if supp_info.get("is_multilingual", True):
            self.modelInfoText.SetLabel(_("Model type: Multilingual (Supports all 100+ languages, bidirectional enabled)"))
        else:
            src = supp_info.get("src", ["?"])[0]
            tgt = supp_info.get("tgt", ["?"])[0]
            s_name = AVAILABLE_LANGUAGES.get(src, src)
            t_name = AVAILABLE_LANGUAGES.get(tgt, tgt)
            self.modelInfoText.SetLabel(_("Model type: Single Language Pair ({src} -> {tgt} only)").format(src=s_name, tgt=t_name))

    def onOpenFolder(self, evt):
        try:
            os.startfile(offlineEngine.MODELS_DIR)
        except Exception as e:
            logHandler.log.error(f"OmniTranslate: Could not open folder: {e}")

    def onDownload(self, evt):
        sel_idx = self.catalogChoice.GetSelection()
        if sel_idx != wx.NOT_FOUND and self.catalog:
            model_info = self.catalog[sel_idx]
            offlineEngine.download_model_package(model_info, on_complete=self._refreshInstalled)

    def onDeleteModel(self, evt):
        if not self.installed:
            ui.message(_("No installed models to delete."))
            return
        sel_idx = self.installedChoice.GetSelection()
        if sel_idx != wx.NOT_FOUND and 0 <= sel_idx < len(self.installed):
            chosen = self.installed[sel_idx]
            msg = _("Are you sure you want to uninstall and delete the offline model '{name}'?").format(name=chosen)
            if gui.messageBox(msg, _("Confirm Model Deletion"), wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
                if offlineEngine.delete_installed_model(chosen):
                    tones.beep(440, 40)
                    ui.message(_("Model {name} deleted successfully.").format(name=chosen))
                    self._refreshAfterDelete()

    def _refreshAfterDelete(self):
        def _update():
            if not self or not bool(self):
                return
            try:
                self.installed = offlineEngine.get_installed_offline_models()
                self.Freeze()
                try:
                    if self.installed:
                        self.installedChoice.Set(self.installed)
                        self.installedChoice.SetSelection(0)
                        self.cur_model = self.installed[0]
                        save_config({"offlineModel": self.installed[0]})
                    else:
                        self.installedChoice.Set([_("No offline models installed")])
                        self.installedChoice.SetSelection(0)
                        self.cur_model = "none"
                        save_config({"offlineModel": "none"})
                finally:
                    self.Thaw()
                self.updateModelInfo()
            except Exception as e:
                logHandler.log.debug(f"OmniTranslate: Error updating UI after delete: {e}")
        wx.CallAfter(_update)

    def _refreshInstalled(self, new_model_id):
        def _update():
            if not self or not bool(self):
                return
            try:
                self.installed = offlineEngine.get_installed_offline_models()
                self.Freeze()
                try:
                    self.installedChoice.Set(self.installed if self.installed else [_("No offline models installed")])
                    if new_model_id in self.installed:
                        self.installedChoice.SetSelection(self.installed.index(new_model_id))
                    elif self.installed:
                        self.installedChoice.SetSelection(0)
                finally:
                    self.Thaw()
                self.cur_model = new_model_id
                save_config({"offlineModel": new_model_id})
                self.updateModelInfo()
            except Exception as e:
                logHandler.log.debug(f"OmniTranslate: Error updating UI after install: {e}")
        wx.CallAfter(_update)

    def onSave(self):
        if self.installed:
            m_sel = self.installedChoice.GetSelection()
            if m_sel != wx.NOT_FOUND and 0 <= m_sel < len(self.installed):
                save_config({"offlineModel": self.installed[m_sel]})


# Backward compatibility alias
OmniTranslateSettingsPanel = OmniTranslateGeneralSettingsPanel