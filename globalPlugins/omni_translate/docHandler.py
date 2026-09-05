import os
import languageHandler
import globalVars
import ui
import addonHandler
import logHandler
import subprocess

addonHandler.initTranslation()


def getDocFilePath(fileName):
    lang = languageHandler.getLanguage()
    baseDir = os.path.join(os.path.dirname(__file__), "..", "..", "doc")
    langDir = os.path.join(baseDir, lang)
    if os.path.exists(os.path.join(langDir, fileName)):
        return os.path.join(langDir, fileName)
    return os.path.join(baseDir, "en", fileName)


def openDoc():
    if getattr(globalVars.appArgs, "secureMode", False):
        ui.message(_("Documentation cannot be opened on secure screens."))
        return

    docFile = getDocFilePath("readme.html")
    if not os.path.isfile(docFile):
        docFile = getDocFilePath("readme.md")
    if not os.path.isfile(docFile):
        docFile = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")

    if os.path.isfile(docFile):
        try:
            os.startfile(docFile)
        except OSError as e:
            # WinError 1155: No application is associated with the specified file
            try:
                subprocess.Popen(["notepad.exe", docFile])
            except Exception as sub_err:
                logHandler.log.error(f"OmniTranslate: Failed opening documentation: {e}, fallback error: {sub_err}")
                ui.message(_("Could not open documentation file."))
    else:
        ui.message(_("Documentation file not found."))