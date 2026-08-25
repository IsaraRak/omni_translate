import os
import languageHandler
import gui
def getDocFilePath(fileName):
    lang = languageHandler.getLanguage()
    baseDir = os.path.join(os.path.dirname(__file__), "..", "..", "doc")
    langDir = os.path.join(baseDir, lang)
    if os.path.exists(os.path.join(langDir, fileName)):
        return os.path.join(langDir, fileName)
    return os.path.join(baseDir, "en", fileName)