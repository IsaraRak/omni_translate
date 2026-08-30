import os
import languageHandler
def getDocFilePath(fileName):
    lang = languageHandler.getLanguage()
    baseDir = os.path.join(os.path.dirname(__file__), "..", "..", "doc")
    langDir = os.path.join(baseDir, lang)
    if os.path.exists(os.path.join(langDir, fileName)):
        return os.path.join(langDir, fileName)
    return os.path.join(baseDir, "en", fileName)


def openDoc():
    docFile = getDocFilePath("readme.html")
    if not os.path.isfile(docFile):
        docFile = getDocFilePath("readme.md")
    if os.path.isfile(docFile):
        os.startfile(docFile)
    else:
        rootDoc = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")
        if os.path.isfile(rootDoc):
            os.startfile(rootDoc)