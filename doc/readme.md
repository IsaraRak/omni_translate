# OmniTranslate for NVDA
OmniTranslate is an accessible translation add-on for the NVDA screen reader, supporting 100+ languages worldwide with smart bidirectional translation routing, accessible dialogs, and customizable quick-switch slots.
## Key Features
- **Smart Bidirectional Translation**: Automatically detects the input language. If text matches your primary target language, it automatically translates to your secondary language; otherwise, it translates to your primary target language.
- **Accessible UI**: Built-in Result Viewer and Session History dialogs for seamless reading and navigation.
- **In-Memory History**: Keeps the last 10 translations in session memory (RAM), automatically cleared when NVDA restarts for enhanced privacy.
- **Rate-Limit Resilience**: Multi-endpoint fallback system ensures uninterrupted translation.
## Keyboard Shortcuts
- `NVDA+Shift+T`: Translate selected text or clipboard content.
- `NVDA+Shift+S`: Swap primary target and secondary languages.
- `NVDA+Shift+J`: Cycle through 5 quick-switch language slots.
- `NVDA+Shift+V`: Open the Result Viewer dialog.
- `NVDA+Shift+H`: Open the Translation History dialog.
- `NVDA+Shift+M`: Toggle speech output on/off.
- `NVDA+Shift+Z`: Repeat the last translation.
- `NVDA+Shift+X`: Copy the last translation to the clipboard.
- `NVDA+Shift+O`: Open OmniTranslate Settings.
## Configuration
Access **OmniTranslate Settings** via the NVDA Tools menu or by pressing `NVDA+Shift+O`.
- **Primary target language**: Default language to translate into.
- **Secondary swap language**: Alternate language used when source text is in the primary language.
- **Quick Cycle Slots 1 - 5**: Pre-configured language slots for fast switching.
- **Options**: Toggle auto-detect, automatic clipboard copying, and speech output.