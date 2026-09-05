# -*- coding: utf-8 -*-
# OmniTranslate - Offline Neural Machine Translation Engine (NLLB-200 & Hybrid CTranslate2)
# Author: Isara Watthanawirojkul

import os
import sys
import re
import json
import shutil
import threading
import unicodedata
from collections import defaultdict
import urllib.request
import urllib.error
import wx
import globalVars
import logHandler
import addonHandler
import ui
import tones

addonHandler.initTranslation()

PLUGIN_DIR = os.path.dirname(__file__)
LIB_DIR = os.path.join(PLUGIN_DIR, "lib")
MODELS_DIR = os.path.join(globalVars.appArgs.configPath, "omni_translate_models")

# Ensure directories exist
for d in (LIB_DIR, MODELS_DIR):
    if not os.path.exists(d):
        try:
            os.makedirs(d)
        except Exception as e:
            logHandler.log.error(f"OmniTranslate: Failed to create directory {d}: {e}")

# Dynamic Python ABI Lib Directory (3.11 / 3.13)
py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
ARCH_LIB_DIR = os.path.join(LIB_DIR, py_ver)

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

if os.path.exists(ARCH_LIB_DIR):
    if ARCH_LIB_DIR not in sys.path:
        sys.path.insert(0, ARCH_LIB_DIR)

    # ----------------------------------------------------------------------
    # ลงทะเบียน DLL Directories สำหรับ Windows (รวมถึง numpy.libs, ctranslate2.libs)
    # ----------------------------------------------------------------------
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(ARCH_LIB_DIR)
        except Exception:
            pass

        try:
            for item in os.listdir(ARCH_LIB_DIR):
                item_path = os.path.join(ARCH_LIB_DIR, item)
                if os.path.isdir(item_path):
                    # ดักจับโฟลเดอร์ .libs (เช่น numpy.libs) และแพ็กเกจ binary
                    if item.endswith(".libs") or item in ("numpy", "ctranslate2", "sentencepiece"):
                        try:
                            os.add_dll_directory(item_path)
                        except Exception:
                            pass
        except Exception as e:
            logHandler.log.debug(f"OmniTranslate: DLL directory registration notice: {e}")

    # สำรองสำหรับ PATH บน Windows
    os.environ["PATH"] = ARCH_LIB_DIR + os.pathsep + os.environ.get("PATH", "")

_LOADED_MODELS = {}
_MODEL_LANG_CACHE = {}

LATIN_LANGS = {
    "en", "pt", "es", "fr", "de", "it", "nl", "id", "ms", "tl", "vi", "sv", "da", "fi", "no", "pl", "tr", "cs", "ro", "hu", "af", "sq", "ca", "hr", "et", "lv", "lt", "sk", "sl"
}


def normalize_unaccented(text):
    if not text:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()


RAW_VOCAB = {
    "af": {
        "aan", "aand", "aandete", "aarde", "absoluut", "af", "ag", "agter", "ain", "al", "albei", "algemeen",
        "alleen", "alles", "almal", "altyd", "amper", "ander", "anders", "antwoord", "are", "arm", "as", "asseblief",
        "baas", "baba", "baie", "bang", "beampte", "bed", "bedoel", "begin", "beheer", "behoefte", "behoeftes", "behoort",
        "bekend", "bekommer", "bekommerd", "bel", "belangrik", "belofte", "benodig", "beplan", "besig", "besigheid", "besluit", "beste",
        "bestel", "betaal", "beteken", "beter", "beweeg", "bietjie", "binne", "binnekort", "bloed", "bly", "bo", "boek",
        "breek", "bring", "broer", "brood", "buite", "bus", "by", "daar", "dae", "dag", "dame", "dames",
        "dan", "dankie", "dans", "datum", "deel", "deur", "die", "dieselfde", "ding", "dinge", "dink", "dit",
        "doen", "dogter", "dokter", "dom", "domkrag", "don", "donker", "dood", "doodmaak", "dorp", "draai", "drie",
        "drink", "droom", "duidelik", "een", "eerder", "eers", "eet", "eh", "eie", "einde", "eintlik", "ek",
        "elk", "elke", "em", "en", "ene", "enige", "enigiemand", "enigiets", "erger", "ernstig", "familie", "feit",
        "figuur", "fok", "fokken", "foon", "fout", "fyn", "gaan", "gat", "gebeur", "gebou", "gebring", "gebruik",
        "gedink", "gedoen", "gedraai", "gee", "geen", "gegaan", "gegee", "gehad", "geheim", "gehoor", "gehou", "gek",
        "gekom", "gekry", "gekyk", "geld", "gelede", "geluk", "gelukkig", "gemaak", "geneem", "genoeg", "gereed", "geroep",
        "gese", "gesien", "gesig", "geskiet", "gesterf", "gestuur", "getroud", "geval", "gevang", "gevind", "gevoel", "gevra",
        "geweer", "gewees", "geweet", "gewen", "gewerk", "gister", "glo", "god", "goed", "goeiemiddag", "goeiemore", "goeienaand",
        "goeienag", "gooi", "grappie", "gratis", "grond", "groot", "ha", "haar", "haastig", "haat", "hallo", "hand",
        "hande", "hang", "hanteer", "hard", "hardloop", "hare", "hart", "he", "heel", "heer", "hel", "helfte",
        "help", "here", "het", "heuning", "hey", "hier", "hierdie", "hmm", "hoe", "hoekom", "hoeveel", "hof",
        "hom", "homself", "hond", "hoof", "hoog", "hoop", "hoor", "hospitaal", "hotel", "hou", "huh", "huis",
        "hulle", "hulp", "hy", "idee", "iemand", "iets", "iewers", "in", "indien", "is", "isn", "ja",
        "jaar", "jammer", "jare", "jesus", "john", "jonk", "jou", "joune", "jouself", "julle", "jy", "kak",
        "kalm", "kamer", "kan", "kans", "kant", "kantoor", "kaptein", "keer", "keuse", "kies", "kind", "kinders",
        "klaarmaak", "klank", "klanke", "klas", "klein", "klop", "koel", "koffie", "kom", "kon", "koning", "koop",
        "kop", "kos", "koud", "krag", "kry", "kursus", "kyk", "laaste", "laat", "lag", "laggend", "laggie",
        "land", "langer", "lank", "later", "leef", "leer", "lees", "lekker", "lewe", "lewende", "lewendig", "lewens",
        "liedjie", "liefde", "liefgehad", "liefling", "lieg", "liewe", "lig", "liggaam", "links", "loop", "lug", "lughawe",
        "luister", "lyk", "lyn", "ma", "maak", "maande", "maar", "maatskappy", "mag", "maklik", "mal", "man",
        "manier", "mans", "meer", "meeste", "meester", "meisie", "meisies", "meneer", "mens", "mense", "met", "miljoen",
        "min", "minder", "minste", "minute", "minuut", "mis", "miskien", "mnr", "moeder", "moeg", "moeilik", "moeilikheid",
        "moet", "mooi", "moontlik", "moord", "more", "motor", "musiek", "my", "myne", "myself", "na", "naam",
        "naby", "nag", "nee", "neem", "net", "nie", "niemand", "niks", "nog", "nogal", "nommer", "nooit",
        "nou", "nuus", "nuut", "oe", "of", "oggend", "okay", "omdat", "onder", "ons", "onthou", "ontmoet",
        "oog", "ooh", "ooit", "ook", "oom", "oomblik", "oopmaak", "oor", "oorlog", "oorsaak", "op", "optree",
        "orde", "ou", "oud", "ouderdom", "ouens", "ouers", "oukei", "pa", "paartjie", "pad", "pappa", "partytjie",
        "perfek", "persoon", "plek", "polisie", "praat", "pragtig", "prentjie", "president", "presies", "pret", "probeer", "probleem",
        "prys", "puik", "punt", "pyn", "raai", "raak", "rapporteer", "red", "rede", "reeds", "reg", "regs",
        "regtig", "reguit", "rekening", "roeping", "rond", "rooi", "rus", "ry", "saak", "saam", "sal", "sam",
        "se", "sedert", "seermaak", "seker", "seks", "selfs", "ses", "seun", "seuns", "seuntjie", "siek", "sien",
        "sin", "sit", "sjoe", "skiet", "skip", "skool", "skoon", "skryf", "slaag", "slaap", "sleg", "slegs",
        "snaaks", "sny", "so", "soek", "soen", "soet", "sommige", "soms", "sonder", "soort", "sorg", "sorteer",
        "sou", "span", "speel", "speletjie", "spesiaal", "staan", "staat", "stad", "stap", "stasie", "steeds", "stel",
        "stelsel", "stem", "sterf", "sterk", "stil", "stoel", "stop", "storie", "straat", "stuk", "stuur", "sug",
        "suster", "swart", "sy", "syne", "tafel", "tee", "teef", "teen", "teken", "terug", "terugkeer", "terwyl",
        "tien", "toekoms", "toemaak", "toevlugsoord", "tot", "totsiens", "tref", "trein", "trek", "trou", "troue", "tuis",
        "tussen", "twee", "tweede", "tyd", "tydens", "tye", "uh", "uit", "uiteindelik", "um", "ure", "uur",
        "vader", "val", "van", "vanaand", "vandag", "vang", "veg", "veilig", "venster", "ver", "verander", "verdomp",
        "verduidelik", "vergadering", "vergeet", "verkeerd", "verkoop", "verlaat", "verlede", "verloor", "verlore", "vermis", "vermoor", "veronderstel",
        "versigtig", "verskoning", "verstaan", "verstand", "verstommend", "vertel", "vertrek", "vertrou", "vier", "vind", "vinnig", "vir",
        "vm", "voel", "voete", "vol", "volg", "volgende", "voor", "vorentoe", "vra", "vraag", "vrae", "vreemd",
        "vriend", "vriende", "vroeg", "vrou", "vroue", "vuur", "vyf", "waar", "waarheid", "waarskynlik", "wag", "wakker",
        "wanneer", "want", "warm", "was", "wasn", "wat", "water", "watter", "weddenskap", "week", "weer", "wees",
        "weet", "weg", "weke", "wel", "welkom", "wen", "wens", "werd", "wereld", "werk", "werklik", "wese",
        "wet", "wie", "wil", "wit", "wonder", "wonderlik", "woord", "woorde", "word", "wou", "wys",
    },
    "ca": {
        "a", "abans", "acaba", "acabar", "acabat", "aco", "aconseguir", "acord", "adeu", "adew", "adieu", "aeroport",
        "agafa", "agafar", "agent", "agrada", "agradaria", "ah", "ahir", "aigua", "aixi", "aixo", "ajuda", "ajudar",
        "al", "aleshores", "algu", "algun", "alguna", "algunes", "alguns", "alla", "alli", "allo", "als", "altesa",
        "altra", "altre", "altres", "amb", "amic", "amics", "amor", "anar", "anat", "anava", "anem", "any",
        "anys", "aquell", "aquella", "aquells", "aquest", "aquesta", "aquestes", "aquests", "aqui", "ara", "arma", "arribar",
        "arribat", "assassi", "assassinat", "aviat", "avui", "banda", "be", "ben", "bo", "bon", "bona", "bret",
        "buscar", "cada", "cadira", "cafe", "cal", "cami", "camp", "canvi", "cap", "capita", "cara", "carrer",
        "cas", "casa", "cel", "cert", "cinc", "ciutat", "clar", "col", "collons", "com", "comencar", "compte",
        "conec", "coneixer", "contra", "cop", "cor", "cos", "cosa", "coses", "costat", "cotxe", "crec", "creu",
        "creure", "creus", "culpa", "darrere", "davant", "de", "debo", "deia", "deixa", "deixar", "deixat", "del",
        "dels", "dema", "demanar", "des", "despres", "deu", "deus", "dia", "dic", "diem", "dies", "diferent",
        "dificil", "digui", "diners", "dins", "dir", "dire", "disculpi", "dit", "diu", "diuen", "dius", "doctor",
        "dolars", "dolent", "dona", "donar", "donat", "doncs", "dones", "dormir", "dos", "dreta", "dues", "dur",
        "durant", "eh", "ei", "el", "ell", "ella", "elles", "ells", "els", "em", "en", "encara",
        "endavant", "ens", "entenc", "entrar", "entre", "era", "eren", "eres", "es", "escolta", "espera", "esperar",
        "espero", "esquerra", "esta", "estacio", "estan", "estar", "estas", "estat", "estava", "estem", "esteu", "estic",
        "estimo", "estrany", "et", "ets", "exactament", "fa", "faci", "facil", "facis", "faig", "familia", "fan",
        "fara", "fare", "farem", "faria", "fas", "favor", "feia", "feina", "felic", "fem", "fent", "fer",
        "fes", "festa", "fet", "fi", "fill", "filla", "fills", "final", "finestra", "fins", "foc", "fora",
        "forca", "forma", "fort", "fos", "gaire", "gairebe", "genial", "gent", "germa", "germana", "gracies", "gran",
        "greu", "guerra", "ha", "habitacio", "hagi", "hagues", "haig", "han", "has", "haura", "hauria", "hauriem",
        "hauries", "haver", "havia", "he", "hem", "heu", "hi", "historia", "ho", "hola", "home", "homes",
        "hora", "hores", "hotel", "i", "idea", "igual", "importa", "important", "ja", "jo", "john", "jove",
        "junts", "just", "la", "les", "li", "llavors", "llit", "lloc", "llum", "lluny", "llur", "ls",
        "ma", "mai", "mal", "malament", "mama", "manera", "mans", "mare", "marit", "marxar", "massa", "matar",
        "mateix", "mateixa", "mati", "me", "mena", "menjar", "mentre", "menys", "merda", "mes", "mesos", "meu",
        "meus", "meva", "meves", "mi", "mica", "millor", "minuts", "mira", "molt", "molta", "moltes", "molts",
        "moment", "mon", "morir", "mort", "morts", "nau", "necessita", "necessitem", "necessito", "negre", "nen", "nena",
        "nens", "ni", "ningu", "nit", "no", "noi", "noia", "nois", "nom", "nomes", "nord", "nosaltres",
        "nostra", "nostre", "nostres", "nou", "nova", "ns", "o", "oh", "oi", "oliver", "on", "oportunitat",
        "ordre", "pa", "paio", "pais", "papa", "paraula", "pare", "parell", "parla", "parlant", "parlar", "parlo",
        "part", "pas", "passa", "passant", "passar", "passat", "pau", "pel", "pels", "pensa", "pensar", "pensat",
        "pensava", "penses", "penso", "per", "perdo", "perdona", "perdre", "perdut", "perill", "pero", "perque", "persona",
        "persones", "petit", "petita", "pla", "plau", "poble", "poc", "podem", "poden", "poder", "podia", "podria",
        "podriem", "podries", "pogut", "policia", "por", "porta", "portar", "portes", "posar", "possible", "pot", "pots",
        "potser", "pregunta", "prendre", "preu", "primer", "primera", "probablement", "problema", "problemes", "prop", "prou", "puc",
        "pugui", "punt", "puta", "qual", "qualsevol", "quan", "quant", "quants", "quatre", "que", "queda", "quedar",
        "quelcom", "qui", "quin", "quina", "rao", "rapid", "realitat", "realment", "recordes", "recte", "rei", "reina",
        "res", "resta", "sabem", "saber", "sabia", "salvar", "sang", "sap", "saps", "se", "segons", "seguir",
        "segur", "segura", "seguretat", "sembla", "sempre", "sense", "sent", "sentir", "sentit", "sento", "senyor", "senyora",
        "ser", "sera", "seria", "servir", "set", "setmana", "seu", "seus", "seva", "seves", "si", "sigui",
        "sigut", "sis", "sobre", "soc", "sol", "sola", "sols", "som", "son", "sopar", "sort", "sortir",
        "sota", "sou", "suposo", "tal", "tambe", "tampoc", "tan", "tant", "tard", "tarda", "taula", "te",
        "telefon", "temps", "tenen", "tenia", "tenim", "tenir", "teniu", "tens", "terra", "teu", "teus", "teva",
        "teves", "tinc", "tingut", "tipus", "torna", "tornar", "tornat", "tot", "tota", "totes", "tothom", "tots",
        "tranquil", "treball", "treballar", "tren", "tres", "tret", "treure", "trobar", "trobat", "tu", "ulls", "ultim",
        "ultima", "un", "una", "unes", "unic", "unica", "uns", "us", "va", "vaig", "val", "vam",
        "van", "vas", "ve", "vegada", "vegades", "veiem", "veig", "vell", "venim", "venir", "veritat", "ves",
        "veu", "veure", "veus", "vida", "vinc", "vine", "vinga", "vingut", "vist", "viu", "viure", "vol",
        "volem", "volen", "voler", "volia", "vols", "vos", "vosaltres", "voste", "vostra", "vostre", "vostres", "vull",
    },
    "cs": {
        "a", "aby", "abych", "abychom", "abys", "abyste", "ach", "ahoj", "ale", "ani", "ano", "asi",
        "aspon", "at", "auto", "autobus", "az", "bez", "blizko", "boze", "bratr", "brzy", "bud", "bude",
        "budeme", "budes", "budete", "budou", "budu", "by", "bych", "bychom", "byl", "byla", "byli", "bylo",
        "byly", "bys", "byste", "byt", "caj", "cas", "casu", "cele", "celou", "cely", "cem", "cena",
        "chapu", "chce", "chceme", "chces", "chcete", "chci", "chlap", "chleb", "chtel", "chtela", "chtit", "chvili",
        "cim", "cislo", "citim", "clovek", "co", "cokoliv", "coz", "coze", "ctyri", "dal", "daleko", "dalsi",
        "dam", "dat", "dej", "deje", "dejte", "dekuji", "dekuju", "dela", "delal", "delam", "delas", "delat",
        "delate", "den", "deti", "diky", "dite", "dlouho", "dnes", "dneska", "do", "dobra", "dobre", "dobrou",
        "dobry", "docela", "dokonce", "dokud", "dolu", "doma", "domu", "dost", "dostal", "dostat", "doufam", "dovnitr",
        "driv", "dum", "duvod", "dva", "dve", "dvere", "fajn", "fakt", "halo", "hej", "hele", "hned",
        "ho", "hodin", "hodne", "holka", "hotel", "hrat", "ja", "jak", "jake", "jako", "jaky", "jasne",
        "jasny", "jde", "jdeme", "jdes", "jdi", "jdu", "je", "jeden", "jedna", "jedno", "jednoho", "jednou",
        "jednu", "jeho", "jeji", "jejich", "jen", "jenom", "jeste", "jestli", "jet", "ji", "jim", "jinak",
        "jineho", "jiny", "jiste", "jisty", "jit", "jmeno", "jo", "jsem", "jsi", "jsme", "jsou", "jste",
        "kafe", "kam", "kamo", "kazdy", "kde", "kdo", "kdy", "kdyby", "kdybych", "kdyz", "ke", "koho",
        "kolem", "kolik", "konec", "konecne", "ktera", "ktere", "kteri", "kterou", "ktery", "kurva", "kvuli", "lehky",
        "lepsi", "let", "letiste", "libi", "lide", "lidi", "lito", "ma", "maji", "malo", "maly", "mam",
        "mama", "mame", "mami", "mas", "maso", "mate", "matka", "me", "meho", "mel", "mela", "meli",
        "mene", "mesto", "mezi", "mi", "miluju", "minut", "misto", "mit", "mluvim", "mluvit", "mne", "mnou",
        "moc", "moct", "mohl", "mohla", "mohli", "mohlo", "mohu", "moje", "mou", "mozna", "mu", "muj",
        "musel", "muset", "musi", "musim", "musime", "musis", "musite", "muz", "muze", "muzeme", "muzes", "muzete",
        "muzu", "my", "myslel", "myslela", "mysli", "myslim", "myslis", "myslite", "na", "nad", "nadrazi", "najit",
        "nam", "nami", "napad", "nas", "nase", "nasel", "nasi", "nasli", "ne", "nebo", "nebude", "nebudu",
        "nebyl", "nebyla", "nebylo", "nech", "nechal", "nechat", "nechces", "nechci", "nechte", "neco", "nej", "nejak",
        "nejake", "nejakou", "nejaky", "nejde", "nejlepsi", "nejsem", "nejsi", "nejsou", "nekde", "nekdo", "nekdy", "nekoho",
        "nem", "nema", "nemam", "nemame", "nemas", "nemel", "nemuze", "nemuzeme", "nemuzes", "nemuzu", "nemyslim", "neni",
        "nevim", "nez", "ni", "nic", "nich", "nikdo", "nikdy", "nim", "no", "noc", "noci", "novy",
        "nyni", "oba", "od", "odsud", "oh", "ok", "okno", "omlouvam", "on", "ona", "oni", "ono",
        "opravdu", "ostatni", "otec", "pak", "pan", "pane", "pani", "par", "penize", "pet", "po", "pocit",
        "pockat", "pockej", "pod", "podivej", "podivejte", "podle", "pohode", "pojd", "pojdme", "pojdte", "pokoj", "pokud",
        "pomoc", "pomoct", "porad", "poradku", "posledni", "poslouchej", "potom", "potrebujeme", "potrebuju", "pozde", "pozdeji", "pozor",
        "prace", "praci", "pravda", "pravdu", "prave", "prece", "pred", "predtim", "pres", "presne", "prestan", "pri",
        "prijde", "prilis", "primo", "prisel", "prisla", "pro", "problem", "proc", "promin", "prominte", "promluvit", "prosim",
        "proste", "proti", "proto", "protoze", "prvni", "pryc", "pujdu", "rad", "rada", "radsi", "rano", "rekl",
        "rekla", "rekni", "reknu", "rict", "rika", "rikal", "rikala", "rikam", "rikas", "rikat", "rok", "rovne",
        "ruce", "rychle", "s", "sakra", "sam", "sama", "samozrejme", "se", "sebe", "sebou", "sel", "sem",
        "ses", "shledanou", "si", "sis", "skoro", "skvele", "skvely", "slysel", "smrti", "snad", "sobe", "spatne",
        "spatny", "spolu", "spravne", "srdce", "stale", "stalo", "stane", "stary", "stat", "stejne", "stesti", "stul",
        "super", "sve", "sveho", "svet", "svete", "svoje", "svou", "svuj", "svym", "ta", "tady", "tahle",
        "tak", "take", "takhle", "takovy", "taky", "takze", "tam", "tata", "tati", "te", "tebe", "tebou",
        "tech", "ted", "teda", "tedy", "ten", "tenhle", "tento", "teto", "tezky", "ti", "tim", "to",
        "tobe", "tohle", "toho", "tolik", "tom", "tomu", "toto", "treba", "tri", "trochu", "tu", "tuhle",
        "tve", "tvoje", "tvuj", "ty", "tyden", "tyhle", "ucet", "udelal", "udelala", "udelam", "udelat", "ulice",
        "uplne", "urcite", "uvidime", "uz", "v", "vam", "vami", "vas", "vase", "vasi", "vazne", "vcera",
        "ve", "vec", "vecer", "veci", "vedel", "vedet", "velky", "velmi", "ven", "venku", "vi", "vic",
        "vice", "videl", "videla", "videt", "vidim", "vidis", "vim", "vime", "vis", "vite", "vlak", "vlastne",
        "vlastni", "vlevo", "voda", "vpravo", "vratit", "vse", "vsech", "vsechno", "vsechny", "vsem", "vsichni", "vubec",
        "vy", "vypada", "vzal", "vzdy", "vzdycky", "vzdyt", "vzit", "za", "zabil", "zabit", "zadna", "zadne",
        "zadny", "zase", "zatim", "zbran", "zda", "zde", "ze", "zeme", "zemi", "zena", "zidle", "zit",
        "zitra", "zivot", "zivota", "zlato", "znam", "znamena", "zni", "znovu", "zpatky", "zpet", "zrovna", "zustat",
    },
    "da": {
        "I", "ad", "af", "aften", "agent", "ah", "al", "aldrig", "alene", "alle", "allerede", "alligevel",
        "alt", "altid", "altsa", "anden", "andet", "andre", "ar", "arbejde", "arbejder", "at", "bad", "bag",
        "bange", "bare", "barn", "beder", "bedre", "bedste", "begge", "begynder", "behøver", "beklager", "ben", "besked",
        "betyder", "bil", "bilen", "blev", "blevet", "bliv", "blive", "bliver", "blod", "bor", "bord", "brod",
        "bror", "brug", "bruge", "bruger", "burde", "bus", "by", "byen", "bør", "børn", "chance", "da",
        "dag", "dage", "dagen", "darlig", "datter", "de", "del", "dem", "den", "denne", "der", "deres",
        "derfor", "det", "dette", "dig", "din", "dine", "disse", "dit", "dog", "dor", "dreng", "drenge",
        "dræbe", "dræbt", "dræbte", "du", "dø", "død", "døde", "dør", "døren", "efter", "egen", "eller",
        "ellers", "elskede", "elsker", "en", "end", "endnu", "eneste", "engang", "er", "et", "fa", "fader",
        "faet", "faktisk", "familie", "fanden", "fandt", "fantastisk", "far", "farvel", "fast", "fat", "fedt", "fejl",
        "fem", "fik", "finde", "finder", "fint", "fire", "flere", "flot", "folk", "for", "forbi", "fordi",
        "foregar", "forkert", "forsta", "forstar", "fortalt", "fortalte", "fortæl", "fortælle", "fortæller", "forældre", "fra", "frem",
        "fri", "fuld", "fundet", "fyr", "færdig", "føler", "før", "først", "første", "ga", "gade", "gaet",
        "galt", "gamle", "gammel", "gang", "gange", "gar", "gav", "gennem", "gerne", "gift", "gik", "giv",
        "give", "giver", "gjorde", "gjort", "glad", "glem", "god", "godaften", "goddag", "gode", "godmorgen", "godnat",
        "godt", "gor", "gore", "grund", "gud", "gør", "gøre", "haber", "hader", "haft", "hallo", "ham",
        "han", "hand", "handler", "hans", "har", "hardt", "havde", "have", "hedder", "hej", "hele", "heller",
        "hellere", "helst", "helt", "helvede", "hen", "hende", "hendes", "her", "herfra", "hey", "hinanden", "historie",
        "hjaelp", "hjem", "hjemme", "hjerte", "hjælp", "hjælpe", "hjælper", "hojre", "hold", "holde", "holder", "holdt",
        "hos", "hotel", "hovedet", "hr", "hun", "hurtigt", "hus", "huset", "huske", "husker", "hvad", "hvem",
        "hver", "hvert", "hvilken", "hvilket", "hvis", "hvonar", "hvor", "hvordan", "hvorfor", "hvornar", "hør", "høre",
        "hører", "hørt", "hørte", "i", "idag", "ide", "igar", "igen", "igennem", "ihjel", "ikke", "imod",
        "imorgen", "ind", "inde", "inden", "indtil", "ingen", "ingenting", "intet", "ja", "jack", "jeg", "jer",
        "jeres", "jo", "job", "john", "jorden", "kaffe", "kalder", "kan", "kaptajn", "ked", "kender", "klar",
        "klare", "klarer", "klokken", "kom", "komme", "kommer", "kommet", "kone", "kort", "kun", "kunne", "kvinde",
        "kvinder", "kæft", "kæreste", "kærlighed", "køre", "kører", "lad", "lade", "lader", "land", "lang", "langt",
        "lave", "lavede", "laver", "lavet", "leder", "leve", "lever", "lide", "lidt", "lige", "ligesom", "ligeud",
        "ligger", "ligner", "lille", "liv", "live", "livet", "lort", "lov", "lufthavn", "lyder", "læg", "længe",
        "længere", "lære", "løb", "ma", "mad", "made", "man", "mand", "maneder", "mange", "maske", "masse",
        "matte", "med", "meget", "mellem", "men", "mener", "mening", "menneske", "mennesker", "mens", "mere", "mest",
        "mig", "min", "mindre", "mine", "minutter", "mit", "mod", "moder", "mor", "morgen", "mr", "muligt",
        "mænd", "møde", "na", "nar", "nat", "navn", "ned", "nej", "nem", "new", "nogen", "nogensinde",
        "noget", "nogle", "nok", "nu", "nummer", "ny", "nye", "nyt", "næste", "næsten", "nødt", "og",
        "ogsa", "ok", "okay", "om", "omkring", "ondt", "op", "ord", "orden", "os", "over", "pa",
        "par", "pas", "passer", "penge", "pengene", "pige", "piger", "pis", "plads", "politiet", "pris", "problem",
        "problemer", "præcis", "prøv", "prøve", "prøvede", "prøver", "redde", "resten", "ret", "rigtig", "rigtige", "rigtigt",
        "ring", "ringe", "ringede", "ringer", "rolig", "rundt", "sa", "sadan", "sagde", "sagen", "sagt", "sam",
        "samme", "sammen", "sandheden", "sandt", "se", "seks", "selv", "selvfølgelig", "senere", "seng", "sent", "ser",
        "ses", "set", "sgu", "sidder", "side", "siden", "sidste", "sig", "sige", "siger", "sikker", "sikkert",
        "sin", "sine", "sir", "sit", "sjovt", "skal", "skat", "ske", "sker", "sket", "skete", "skide",
        "skidt", "skulle", "skyld", "sla", "slags", "slap", "slar", "slet", "slog", "slut", "smuk", "snakke",
        "snakker", "snart", "som", "spille", "spiller", "spise", "spørge", "spørgsmal", "sta", "stadig", "star", "sted",
        "stedet", "stille", "stol", "stop", "stoppe", "stor", "store", "stort", "svaer", "svært", "synes", "sæt",
        "sætte", "sød", "søn", "søster", "taet", "tag", "tage", "tager", "taget", "tak", "tale", "taler",
        "talt", "talte", "te", "the", "ti", "tid", "tiden", "tidligere", "til", "tilbage", "time", "timer",
        "ting", "to", "tog", "tre", "tro", "troede", "tror", "tur", "tænk", "tænke", "tænker", "tænkt",
        "tænkte", "tæt", "ud", "ude", "uden", "uge", "under", "undskyld", "vaben", "vaere", "vaerelse", "vaeret",
        "valg", "vand", "var", "ved", "vej", "vejen", "vel", "velkommen", "ven", "venner", "venstre", "vent",
        "vente", "venter", "verden", "vi", "vide", "videre", "vidste", "vil", "ville", "vindue", "virkelig", "virker",
        "vise", "vist", "vores", "væk", "vær", "være", "været", "værsgo", "øje", "øjeblik", "øjne", "ønsker",
    },
    "de": {
        "ab", "abend", "aber", "ach", "ah", "ahnung", "all", "alle", "allein", "allen", "alles", "als",
        "also", "alt", "alter", "am", "an", "andere", "anderen", "anderer", "anderes", "anders", "angst", "arbeit",
        "arbeiten", "art", "auch", "auf", "augen", "aus", "auto", "baby", "bahnhof", "bald", "bedeutet", "bei",
        "beide", "beim", "bekommen", "bereit", "besser", "beste", "bestimmt", "bett", "bevor", "bezahlen", "bin", "bis",
        "bisschen", "bist", "bitte", "bleiben", "bleibt", "brauche", "brauchen", "braucht", "bringen", "bringt", "brot", "bruder",
        "bus", "chance", "da", "dabei", "dachte", "dad", "dafur", "damit", "dank", "danke", "dann", "daran",
        "darauf", "darf", "daruber", "darum", "das", "dass", "davon", "dazu", "dein", "deine", "deinem", "deinen",
        "deiner", "dem", "den", "denen", "denke", "denken", "denkst", "denn", "der", "des", "deshalb", "dich",
        "die", "diese", "diesem", "diesen", "dieser", "dieses", "dinge", "dir", "doch", "dort", "dran", "draußen",
        "drei", "drin", "du", "durch", "durfen", "eben", "echt", "egal", "eigentlich", "ein", "eine", "einem",
        "einen", "einer", "eines", "einfach", "einmal", "eins", "einzige", "ende", "endlich", "entschuldigen", "entschuldigung", "er",
        "ernst", "erst", "erste", "ersten", "erzahlen", "erzahlt", "es", "essen", "etwa", "etwas", "euch", "euer",
        "eure", "fahren", "fall", "familie", "fast", "fenster", "fertig", "finde", "finden", "fleisch", "flughafen", "frage",
        "fragen", "frau", "frauen", "freund", "freunde", "freundin", "funf", "fur", "gab", "ganz", "ganze", "ganzen",
        "gar", "geben", "gefallen", "gefallt", "gefunden", "gegen", "geh", "gehe", "gehen", "gehort", "gehst", "geht",
        "gekommen", "geld", "gemacht", "genau", "genug", "gerade", "geradeaus", "gern", "gerne", "gesagt", "geschichte", "gesehen",
        "gestern", "getan", "getotet", "gewesen", "gib", "gibt", "ging", "glaube", "glauben", "glaubst", "gleich", "gluck",
        "gott", "gross", "große", "grund", "gut", "gute", "guten", "guter", "hab", "habe", "haben", "habt",
        "hallo", "halt", "halten", "hand", "hast", "hat", "hatte", "hatten", "hattest", "haus", "hause", "he",
        "heißt", "helfen", "her", "herr", "heute", "hey", "hi", "hier", "hilfe", "hin", "hinter", "hoch",
        "hoffe", "holen", "hor", "horen", "hort", "hotel", "ich", "idee", "ihm", "ihn", "ihnen", "ihr",
        "ihre", "ihrem", "ihren", "ihrer", "im", "immer", "in", "ins", "ist", "ja", "jahr", "jahre",
        "jahren", "je", "jeden", "jeder", "jemand", "jemanden", "jetzt", "job", "john", "junge", "jungs", "kaffee",
        "kam", "kann", "kannst", "karte", "kaufen", "kein", "keine", "keinen", "keiner", "kenne", "kennen", "kerl",
        "kind", "kinder", "klar", "klein", "kleine", "kleinen", "komm", "komme", "kommen", "kommst", "kommt", "konnen",
        "konnt", "konnte", "konnten", "kopf", "krieg", "kuche", "kurz", "land", "lang", "lange", "lass", "lassen",
        "lasst", "lauft", "leben", "leid", "lernen", "letzte", "letzten", "leute", "liebe", "lieber", "liegt", "links",
        "los", "mach", "mache", "machen", "machst", "macht", "madchen", "mag", "mal", "mama", "man", "manchmal",
        "mann", "manner", "mehr", "mein", "meine", "meinem", "meinen", "meiner", "meinst", "menschen", "mich", "minuten",
        "mir", "miss", "mit", "mochte", "mochten", "mom", "moment", "morgen", "musik", "muss", "mussen", "musst",
        "musste", "mutter", "na", "nach", "nacht", "nah", "name", "namen", "naturlich", "ne", "nehme", "nehmen",
        "nein", "nett", "neu", "neue", "nicht", "nichts", "nie", "niemals", "niemand", "nimm", "noch", "nun",
        "nur", "ob", "oben", "oder", "oh", "ohne", "ok", "okay", "ordnung", "ort", "paar", "passiert",
        "polizei", "preis", "problem", "raus", "rechnung", "recht", "rechts", "reden", "rein", "richtig", "ruhe", "ruhig",
        "runter", "sache", "sachen", "sag", "sage", "sagen", "sagst", "sagt", "sagte", "sah", "schatz", "schau",
        "scheiße", "schlecht", "schnell", "schon", "schuld", "schule", "schwer", "schwester", "sehe", "sehen", "sehr", "sei",
        "seid", "sein", "seine", "seinem", "seinen", "seiner", "seit", "seite", "selbe", "selbst", "sich", "sicher",
        "sie", "sieh", "siehst", "sieht", "sind", "sir", "so", "sofort", "sogar", "sohn", "soll", "sollen",
        "sollte", "sollten", "solltest", "sonst", "sorgen", "spat", "spater", "spaß", "spiel", "spielen", "spreche", "sprechen",
        "spricht", "stadt", "stehen", "steht", "sterben", "stimmt", "strasse", "stuhl", "stunden", "suchen", "tag", "tage",
        "taxi", "tee", "teufel", "the", "tisch", "tochter", "tod", "toll", "tot", "toten", "treffen", "trinken",
        "tschuss", "tun", "tur", "tut", "typ", "uber", "uberhaupt", "uhr", "um", "und", "uns", "unser",
        "unsere", "unserer", "unter", "vater", "verdammt", "vergessen", "verlassen", "verloren", "verruckt", "verstanden", "verstehe", "verstehen",
        "versuchen", "versucht", "verzeihung", "viel", "viele", "vielen", "vielleicht", "vier", "vom", "von", "vor", "vorbei",
        "wagen", "wahr", "wahrend", "wahrheit", "wann", "war", "ware", "waren", "warst", "warte", "warten", "warum",
        "was", "wasser", "weg", "wegen", "weil", "weiss", "weisst", "weit", "weiter", "weiß", "weißt", "welche",
        "welcher", "welches", "welt", "wenig", "weniger", "wenn", "wer", "werde", "werden", "wichtig", "wie", "wieder",
        "wiedersehen", "wieso", "wieviel", "will", "willst", "wir", "wird", "wirklich", "wirst", "wissen", "wo", "woche",
        "woher", "wohin", "wohl", "wollen", "wollt", "wollte", "wollten", "wort", "wurde", "wurden", "wurdest", "wusste",
        "zeigen", "zeit", "ziemlich", "zimmer", "zu", "zug", "zum", "zur", "zuruck", "zusammen", "zwei", "zwischen",
    },
    "en": {
        "able", "about", "above", "actually", "afraid", "after", "afternoon", "again", "against", "ago", "ah", "ahead",
        "ain", "airport", "alive", "all", "almost", "alone", "along", "already", "also", "always", "am", "an",
        "and", "another", "answer", "any", "anymore", "anyone", "anything", "anyway", "are", "aren", "around", "as",
        "ask", "asked", "at", "away", "baby", "back", "bad", "be", "beautiful", "because", "become", "bed",
        "been", "before", "behind", "being", "believe", "below", "best", "better", "between", "big", "bill", "bit",
        "black", "blood", "body", "both", "boy", "boys", "bread", "break", "bring", "brother", "brought", "bus",
        "business", "but", "buy", "by", "bye", "call", "called", "came", "can", "captain", "car", "card",
        "care", "case", "cause", "chair", "chance", "change", "check", "child", "children", "city", "clear", "close",
        "coffee", "come", "comes", "coming", "cool", "could", "couldn", "country", "couple", "course", "crazy", "cut",
        "dad", "damn", "daughter", "day", "days", "dead", "deal", "dear", "death", "did", "didn", "die",
        "died", "different", "difficult", "dinner", "do", "doctor", "does", "doesn", "dog", "doing", "don", "done",
        "door", "down", "drink", "during", "each", "easy", "eat", "either", "else", "em", "end", "enough",
        "even", "evening", "ever", "every", "everybody", "everyone", "everything", "exactly", "excuse", "eyes", "face", "fact",
        "family", "far", "father", "feel", "feeling", "few", "fight", "find", "fine", "fire", "first", "five",
        "food", "for", "forget", "found", "four", "free", "friend", "friends", "from", "front", "fuck", "fucking",
        "full", "fun", "funny", "further", "game", "gave", "get", "gets", "getting", "girl", "girls", "give",
        "go", "god", "goes", "going", "gone", "gonna", "good", "goodbye", "got", "gotta", "great", "guess",
        "gun", "guy", "guys", "had", "half", "hand", "hands", "happen", "happened", "happy", "hard", "has",
        "hate", "have", "haven", "having", "he", "head", "hear", "heard", "heart", "hell", "hello", "help",
        "her", "here", "hers", "hey", "hi", "high", "him", "his", "hit", "hold", "home", "honey",
        "hope", "hot", "hotel", "hours", "house", "how", "huh", "hurry", "hurt", "husband", "i", "idea",
        "if", "important", "in", "inside", "into", "is", "isn", "it", "its", "job", "just", "keep",
        "kid", "kids", "kill", "killed", "kind", "king", "kitchen", "knew", "know", "known", "knows", "lady",
        "large", "last", "late", "later", "least", "leave", "leaving", "left", "less", "let", "life", "light",
        "like", "line", "listen", "little", "live", "living", "long", "look", "looked", "looking", "looks", "lord",
        "lose", "lost", "lot", "love", "made", "make", "makes", "making", "man", "many", "married", "matter",
        "may", "maybe", "me", "mean", "means", "meat", "meet", "men", "met", "might", "mind", "mine",
        "minute", "minutes", "miss", "mom", "moment", "money", "months", "more", "morning", "most", "mother", "move",
        "mr", "much", "music", "must", "my", "myself", "name", "near", "need", "needed", "needs", "never",
        "new", "news", "next", "nice", "night", "no", "nobody", "nope", "nor", "not", "nothing", "now",
        "number", "of", "off", "office", "oh", "ok", "okay", "old", "on", "once", "one", "only",
        "open", "or", "order", "other", "our", "ours", "out", "outside", "over", "own", "pardon", "part",
        "party", "pay", "people", "person", "phone", "pick", "place", "plan", "play", "playing", "please", "point",
        "police", "power", "pretty", "price", "probably", "problem", "put", "question", "quite", "read", "ready", "real",
        "really", "reason", "remember", "rest", "right", "room", "run", "running", "s", "said", "same", "save",
        "saw", "say", "saying", "says", "school", "second", "see", "seems", "seen", "sees", "send", "set",
        "shall", "she", "shit", "shot", "should", "shouldn", "show", "shut", "side", "sighs", "since", "sir",
        "sister", "sit", "six", "sleep", "small", "so", "some", "somebody", "someone", "something", "sometimes", "son",
        "soon", "sorry", "sort", "speak", "spoke", "stand", "start", "started", "station", "stay", "still", "stop",
        "story", "straight", "street", "study", "stuff", "stupid", "such", "supposed", "sure", "t", "table", "take",
        "taking", "talk", "talking", "taxi", "tea", "team", "tell", "telling", "than", "thank", "thanks", "that",
        "the", "their", "theirs", "them", "then", "there", "these", "they", "thing", "things", "think", "thinking",
        "this", "those", "though", "thought", "three", "through", "time", "times", "to", "today", "together", "told",
        "tomorrow", "tonight", "too", "took", "town", "train", "tried", "trouble", "true", "trust", "truth", "try",
        "trying", "turn", "two", "uh", "um", "under", "understand", "until", "up", "us", "use", "used",
        "very", "wait", "waiting", "walk", "wanna", "want", "wanted", "wants", "war", "was", "wasn", "watch",
        "water", "way", "we", "week", "welcome", "well", "went", "were", "what", "whatever", "when", "where",
        "which", "while", "who", "whoa", "whole", "why", "wife", "will", "window", "wish", "with", "without",
        "woman", "women", "won", "word", "work", "working", "world", "worry", "would", "wouldn", "wow", "wrong",
        "yeah", "year", "years", "yep", "yes", "yesterday", "yet", "you", "young", "your", "yours", "yourself",
    },
    "eo": {
        "absolute", "aceti", "adiau", "aero", "afabla", "afero", "aferojn", "agi", "ah", "ain", "ajn", "ajna",
        "ajoj", "akiranta", "akiri", "akiris", "akvo", "al", "alia", "aliaj", "alie", "alporti", "alportis", "alta",
        "am", "ambau", "amiko", "amikoj", "amita", "amo", "amuza", "an", "ankau", "ankorau", "antau", "antaue",
        "antauen", "aren", "aro", "aspektas", "atendante", "atendu", "au", "audis", "audu", "auskultu", "auto", "azeno",
        "baldau", "batali", "batis", "bato", "bebo", "bela", "bezonas", "bezonata", "bezonoj", "bildo", "blanka", "bona",
        "bonan", "bone", "bonega", "bonsanca", "bonvenon", "bonvolu", "buso", "cambro", "car", "ce", "certe", "chambro",
        "char", "chi", "chio", "chiu", "ci", "ciam", "cio", "cirkaue", "ciu", "ciuj", "ciuokaze", "cu",
        "cxiam", "danci", "dankon", "dato", "de", "dek", "dekstre", "demandante", "demandis", "demando", "demandoj", "demandu",
        "denove", "devas", "devus", "deziras", "diable", "didn", "dio", "dirante", "diras", "diri", "diris", "diru",
        "diveni", "do", "doesn", "dolca", "domo", "don", "donante", "donis", "donita", "donu", "dormu", "du",
        "dua", "dum", "duono", "ebla", "eble", "ec", "edziginta", "edzino", "edzo", "efektive", "ekde", "ekskuzo",
        "ekstere", "eksteren", "ekzakte", "elekti", "em", "en", "espero", "estajo", "estas", "esti", "estis", "estonteco",
        "estos", "estro", "estu", "facila", "fajro", "fakto", "fali", "familio", "farante", "faras", "fari", "farigi",
        "faris", "farita", "fartas", "faru", "felica", "fenestro", "fermu", "festo", "figuro", "fikado", "fiku", "filino",
        "filo", "fine", "fino", "flanko", "fojojn", "for", "forgesu", "forirante", "foriris", "foriru", "forta", "fratino",
        "frato", "fraulino", "freneza", "fronto", "frue", "gepatroj", "gi", "gia", "gis", "goja", "granda", "grava",
        "guste", "guto", "ha", "haltu", "haroj", "havante", "havas", "havi", "havis", "hej", "hejmen", "helpo",
        "hierau", "hmm", "ho", "hodiau", "homa", "homo", "homoj", "horo", "horoj", "hospitalo", "hotelo", "huh",
        "hundino", "hundo", "iam", "ideo", "ie", "ili", "ilia", "ilin", "infano", "infanoj", "infero", "inter",
        "interkonsento", "interne", "io", "iom", "iranta", "iras", "iri", "iris", "iru", "isn", "iu", "iuj",
        "jack", "jam", "jaro", "jaroj", "jes", "jesuo", "jeti", "john", "juna", "kafo", "kaj", "kanto",
        "kapabla", "kapitano", "kapo", "kapti", "kara", "karulino", "kauzo", "kazo", "ke", "kelkfoje", "kia", "kial",
        "kialo", "kiam", "kie", "kiel", "kio", "kiom", "kiu", "klara", "klarigi", "knabino", "knabinoj", "knabo",
        "knaboj", "komenci", "komencis", "komerco", "kompanio", "kompreneble", "kompreni", "konata", "konfidi", "konservi", "kontraux", "kontroli",
        "kontrolo", "koro", "korpo", "kredu", "kulpo", "kun", "kune", "kunveno", "kuracisto", "kurante", "kuri", "kvar",
        "kvin", "la", "laborante", "laboris", "laboro", "lando", "lasta", "lasu", "legi", "lego", "lernejo", "lerni",
        "li", "lia", "libera", "libro", "lin", "linio", "lito", "loko", "longa", "ludante", "ludi", "ludo",
        "lumo", "ma", "majo", "majstro", "malamo", "malantaue", "malbona", "malbone", "maldekstre", "malfacila", "malfermita", "malfrue",
        "malgranda", "malguste", "maljuna", "malmola", "malmultaj", "malmulte", "malnova", "malpli", "malproksime", "malrica", "malsamaj", "malsana",
        "malsupren", "maltrankvilo", "malvarma", "malvarmeta", "mangajo", "mangi", "mano", "manojn", "marsi", "mateno", "matenon", "mem",
        "memoru", "menso", "mensogi", "merdo", "meti", "mi", "mia", "mielo", "miliono", "milito", "minimume", "minuto",
        "minutoj", "mirinda", "miro", "momento", "monatoj", "mondo", "mono", "montri", "morgau", "morti", "mortigi", "mortigita",
        "mortinta", "mortis", "morto", "movanta", "movi", "multaj", "multe", "multo", "murdo", "muziko", "ne", "neniam",
        "nenio", "neniu", "ni", "nia", "nigra", "nokto", "nokton", "nombro", "nomo", "nova", "novajoj", "nu",
        "nun", "nur", "oficejo", "okazas", "okazi", "okazis", "okulo", "okuloj", "ol", "on", "onklo", "ordigi",
        "ordon", "pacjo", "pafi", "pafilo", "pafis", "pagi", "panjo", "pano", "pardonu", "paro", "parolante", "parolas",
        "paroli", "parto", "pasinteco", "paso", "patrino", "patro", "peco", "pendigi", "pensante", "pensi", "pensis", "perdi",
        "perdita", "perfekta", "persono", "piedoj", "plano", "plej", "plena", "pli", "plu", "polico", "por", "pordo",
        "post", "poste", "potenco", "povas", "povi", "povis", "povus", "prefere", "prenante", "prenas", "preni", "prenis",
        "prenita", "preskau", "preta", "prezidanto", "prezo", "pri", "probable", "problemo", "proksime", "promeso", "propra", "provante",
        "provis", "provu", "punkto", "purigi", "rakontante", "rakontis", "rakonto", "rakontu", "rapida", "rapidu", "reala", "reen",
        "rego", "rekte", "renkonti", "renkontis", "respondi", "resti", "reveni", "revido", "revo", "ricevas", "ridante", "ridas",
        "rifugejo", "rigardante", "rigardi", "rigardis", "rigardu", "ripozi", "rompi", "ruga", "sajnas", "saluton", "sam", "sama",
        "sanco", "sangi", "sangita", "sangon", "savi", "scias", "scii", "sciis", "se", "sed", "sego", "sekreta",
        "sekso", "sekura", "sekva", "sekvu", "semajno", "semajnoj", "sen", "senco", "sendi", "sendis", "senti", "sentis",
        "sento", "serioze", "ses", "si", "sia", "sidi", "signifas", "signo", "sin", "sinjorino", "sinjorinoj", "sinjoro",
        "sinjoroj", "skribi", "sole", "sono", "sonoj", "sorto", "speciala", "stari", "stato", "stiri", "stranga", "strato",
        "stulta", "sub", "sufice", "super", "supozis", "supren", "supro", "sur", "suspiras", "tablo", "tago", "tagoj",
        "tagon", "tamen", "teamo", "telefono", "tempo", "teni", "teo", "tero", "tia", "tiaj", "tiam", "tie",
        "timigita", "tio", "tiri", "tiuj", "tra", "trajno", "tranci", "trankvila", "tre", "tri", "trinki", "trovi",
        "trovita", "tuj", "turni", "turnigis", "tusi", "tutaj", "tute", "uh", "ulo", "um", "unu", "unue",
        "unufoje", "urbo", "uzata", "uzi", "valoras", "varma", "venanta", "venas", "veni", "venis", "venki", "venkis",
        "venu", "vera", "vere", "verkoj", "vero", "vespermango", "vespero", "vesperon", "vetas", "vi", "via", "vidante",
        "vidas", "vidi", "vidis", "vidita", "vidu", "virino", "virinoj", "viro", "viroj", "viva", "vivanta", "vivi",
        "vivo", "vivoj", "vizago", "voco", "vojo", "vokado", "voki", "vokis", "volas", "voli", "volis", "volo",
        "volus", "vorto", "vortoj", "vundita", "whoa", "wow", "zorgema", "zorgo",
    },
    "es": {
        "abajo", "acerca", "acuerdo", "adelante", "ademas", "adios", "aeropuerto", "agua", "ah", "ahi", "ahora", "al",
        "algo", "alguien", "algun", "alguna", "algunas", "algunos", "alla", "alli", "alto", "amiga", "amigo", "amigos",
        "amo", "amor", "ano", "anos", "antes", "aqui", "arma", "arriba", "asi", "atras", "aun", "aunque",
        "auto", "autobus", "ayer", "ayuda", "ayudar", "bajo", "bano", "basta", "bastante", "bebe", "beber", "bien",
        "buen", "buena", "buenas", "bueno", "buenos", "buscando", "cabeza", "cada", "cafe", "calle", "cama", "camino",
        "capitan", "cara", "carino", "carne", "casa", "casi", "caso", "cerca", "cerveza", "chica", "chicas", "chico",
        "chicos", "cierto", "cinco", "ciudad", "claro", "clase", "coche", "cocina", "comer", "comida", "como", "comprar",
        "con", "conmigo", "conocer", "conozco", "conseguir", "contigo", "contra", "corazon", "correcto", "cosa", "cosas", "cree",
        "creer", "crees", "creo", "cual", "cualquier", "cuando", "cuanto", "cuantos", "cuatro", "cuenta", "cuerpo", "cuidado",
        "culpa", "da", "dado", "dame", "dar", "de", "debe", "debemos", "deberia", "deberiamos", "deberias", "debes",
        "debo", "decir", "deja", "dejame", "dejar", "del", "demasiado", "demonios", "dentro", "derecha", "desde", "despues",
        "di", "dia", "dias", "dice", "dicen", "dices", "dicho", "diciendo", "dificil", "diga", "digo", "dije",
        "dijiste", "dijo", "dime", "dinero", "dio", "dios", "disculpe", "doctor", "dolares", "donde", "dormir", "dos",
        "durante", "e", "eh", "el", "ella", "ellas", "ello", "ellos", "en", "encontrar", "entiendo", "entonces",
        "entrar", "entre", "equipo", "era", "eran", "eres", "es", "esa", "esas", "escucha", "escuchar", "escuela",
        "ese", "eso", "esos", "espera", "esperando", "esperar", "espero", "esposa", "esta", "estaba", "estaban", "estabas",
        "estacion", "estado", "estamos", "estan", "estar", "estara", "estas", "este", "esto", "estos", "estoy", "estudiar",
        "estuvo", "exactamente", "facil", "familia", "favor", "feliz", "fiesta", "fin", "final", "forma", "fruta", "fue",
        "fuera", "fueron", "fuerte", "fui", "genial", "gente", "gracias", "gran", "grande", "guerra", "gusta", "gustaria",
        "ha", "haber", "habia", "habitacion", "habla", "hablando", "hablar", "hablo", "habria", "hace", "hacen", "hacer",
        "hacerlo", "haces", "hacia", "haciendo", "haga", "hagas", "hago", "han", "hare", "has", "hasta", "hay",
        "haya", "he", "hecho", "hemos", "hermana", "hermano", "hey", "hice", "hiciste", "hija", "hijo", "hijos",
        "historia", "hizo", "hola", "hombre", "hombres", "hora", "horas", "hotel", "hoy", "hubiera", "iba", "idea",
        "idiota", "ido", "igual", "importa", "importante", "incluso", "ir", "ire", "izquierda", "jefe", "john", "joven",
        "juego", "juntos", "justo", "la", "lado", "las", "le", "lejos", "les", "lista", "listo", "llama",
        "llegar", "lo", "loco", "los", "luego", "lugar", "luz", "madre", "mal", "maldita", "malo", "mama",
        "manana", "manera", "mano", "manos", "marido", "mas", "matar", "mayor", "me", "medio", "mejor", "menos",
        "mesa", "meses", "mi", "miedo", "mientras", "mierda", "minutos", "mio", "mira", "mis", "misma", "mismo",
        "momento", "morir", "muchas", "mucho", "muchos", "muerte", "muerto", "mujer", "mujeres", "mundo", "murio", "musica",
        "muy", "nada", "nadie", "necesita", "necesitamos", "necesitar", "necesitas", "necesito", "ni", "nina", "ningun", "ninguna",
        "nino", "ninos", "no", "noche", "noches", "nombre", "nos", "nosotros", "nuestra", "nuestras", "nuestro", "nuestros",
        "nueva", "nuevo", "numero", "nunca", "o", "oficina", "oh", "oido", "ojos", "ok", "oportunidad", "os",
        "otra", "otro", "otros", "oye", "padre", "padres", "pagar", "pais", "palabra", "pan", "papa", "par",
        "para", "parece", "parte", "pasa", "pasado", "pasando", "pasar", "paso", "paz", "pensando", "pensar", "pense",
        "peor", "pequena", "pequeno", "perdon", "pero", "persona", "personas", "plan", "poco", "podemos", "poder", "podia",
        "podria", "podrias", "policia", "por", "porfavor", "porque", "posible", "precio", "pregunta", "preocupes", "primer", "primera",
        "primero", "probablemente", "problema", "problemas", "pronto", "pueblo", "pueda", "puede", "pueden", "puedes", "puedo", "puerta",
        "pues", "punto", "puta", "que", "queda", "querer", "queria", "quien", "quiere", "quieren", "quieres", "quiero",
        "quiza", "quizas", "rapido", "razon", "realidad", "realmente", "recto", "recuerdo", "sabe", "sabemos", "saben", "saber",
        "sabes", "sabia", "salir", "sangre", "se", "sea", "seguir", "segundo", "segura", "seguridad", "seguro", "seis",
        "semana", "senor", "senora", "sentido", "ser", "sera", "seria", "serio", "si", "sido", "siempre", "siendo",
        "siento", "significa", "sigue", "silla", "simplemente", "sin", "siquiera", "sitio", "sobre", "sola", "solo", "somos",
        "son", "soy", "su", "suerte", "suficiente", "supongo", "supuesto", "sus", "tal", "tambien", "tampoco", "tan",
        "tanto", "tarde", "tardes", "tarjeta", "taxi", "te", "telefono", "tenemos", "tener", "tenga", "tengo", "tenia",
        "tenido", "ti", "tiempo", "tiene", "tienen", "tienes", "tierra", "tio", "tipo", "toda", "todas", "todavia",
        "todo", "todos", "toma", "tomar", "trabajar", "trabajo", "trata", "tren", "tres", "tu", "tus", "tuve",
        "ultima", "ultimo", "un", "una", "unas", "unica", "unico", "uno", "unos", "usted", "ustedes", "va",
        "vale", "vamos", "van", "vas", "vaya", "ve", "veces", "ven", "venga", "vengo", "venido", "venir",
        "ventana", "veo", "ver", "verdad", "verte", "ves", "vete", "vez", "vi", "vida", "viejo", "viene",
        "vino", "visto", "vivir", "vivo", "volver", "vosotros", "voy", "vuelta", "vuestro", "y", "ya", "yo",
    },
    "et": {
        "aasta", "aastat", "abi", "aeg", "aega", "aga", "ah", "aidata", "ainult", "ainus", "aitab", "aitah",
        "aja", "ajal", "aken", "akki", "alati", "all", "alla", "alles", "anda", "andeks", "anna", "annan",
        "ara", "arge", "armas", "armastan", "aru", "arvad", "arvan", "arvasin", "asi", "asja", "asjad", "asju",
        "auto", "buss", "edasi", "eemale", "ees", "eest", "ega", "ehk", "ei", "eile", "eks", "elu",
        "elus", "ema", "enam", "end", "enda", "endale", "ennast", "enne", "eriti", "esimene", "et", "ette",
        "hakkab", "hakkama", "halb", "halvasti", "harra", "hasti", "hea", "head", "heaks", "hei", "hetk", "hiljem",
        "hind", "hoia", "hoida", "homme", "hommik", "hommikul", "hommikust", "hotell", "hr", "hull", "iga", "iganes",
        "ikka", "ilma", "ilmselt", "ilus", "inimene", "inimesed", "inimesi", "isa", "ise", "isegi", "issand", "ja",
        "jaa", "jaab", "jaada", "jaam", "jack", "jah", "jalle", "jama", "jaoks", "jarele", "jargi", "jargmine",
        "jata", "jatta", "john", "ju", "juba", "juhtub", "juhtus", "juhul", "jumal", "just", "juurde", "juures",
        "ka", "kaasa", "kadunud", "kaes", "kahju", "kaia", "kaks", "kallis", "kapten", "kas", "katte", "kaua",
        "kaugelt", "keda", "kedagi", "keegi", "kell", "kelle", "kellegi", "kena", "kes", "kiiresti", "kindel", "kindlasti",
        "kinni", "kodus", "kogu", "kohe", "koht", "kohta", "kohv", "koige", "koigest", "koik", "koike", "koiki",
        "koju", "kokku", "kolm", "koos", "kord", "korda", "korras", "kuhu", "kui", "kuid", "kuidas", "kull",
        "kullake", "kuna", "kunagi", "kuni", "kuradi", "kurat", "kus", "kust", "kuula", "kuule", "kuulnud", "kuulsin",
        "labi", "lahe", "laheb", "lahed", "lahedal", "laheme", "lahen", "lahme", "lahti", "lainud", "laks", "laps",
        "lapsed", "las", "lase", "lasta", "laud", "leib", "leida", "leidsin", "lennujaam", "lihtne", "lihtsalt", "liiga",
        "linn", "loodan", "lopeta", "lopuks", "lugu", "ma", "maa", "maailm", "maailma", "maha", "maja", "maletad",
        "me", "meeldi", "meeldib", "mees", "meest", "mehe", "mehed", "meid", "meie", "meiega", "meil", "meile",
        "mida", "midagi", "miks", "millal", "mille", "millest", "milline", "mina", "mind", "mine", "minema", "minge",
        "mingi", "mingit", "minna", "minu", "minuga", "minust", "minutit", "mis", "mitte", "moista", "molemad", "moned",
        "moni", "mooda", "mote", "motled", "motlen", "motlesin", "mu", "muidugi", "mul", "mulle", "muretse", "muud",
        "nad", "nae", "naed", "naeme", "naen", "nagemist", "nagin", "nagma", "nagu", "naha", "naine", "nainud",
        "nalja", "natuke", "need", "neetud", "neid", "neil", "neile", "neist", "neli", "nemad", "nende", "nii",
        "niimoodi", "nime", "nimi", "ning", "no", "noh", "nuud", "oelda", "oelnud", "oh", "ohtul", "ohtust",
        "oige", "oigus", "okei", "ole", "oled", "oleks", "oleksid", "oleksin", "olema", "olemas", "oleme", "olen",
        "olete", "olgu", "oli", "olid", "olin", "olla", "olnud", "oma", "on", "ongi", "oo", "ood",
        "oota", "osa", "otsa", "otse", "paar", "paev", "paeva", "paeval", "paevast", "paistab", "palju", "palun",
        "pane", "panna", "parast", "parem", "paremale", "parim", "paris", "pea", "peaaegu", "peab", "pead", "peaks",
        "peaksid", "peaksime", "peaksin", "peal", "peale", "peame", "pean", "peate", "persse", "pidanud", "pidi", "piisavalt",
        "pisut", "poeg", "poisid", "poiss", "pole", "poleks", "politsei", "polnud", "pool", "poole", "poolt", "praegu",
        "probleem", "proua", "raagi", "raagib", "raagid", "raagin", "raakida", "raakima", "raakinud", "raakis", "raha", "raske",
        "ringi", "rohkem", "rong", "sa", "saa", "saab", "saad", "saada", "saaks", "saama", "saame", "saan",
        "saanud", "sai", "said", "sain", "sama", "samuti", "seal", "sealt", "seda", "see", "seega", "sees",
        "sel", "selge", "selle", "sellega", "selleks", "sellel", "sellele", "selleparast", "selles", "sellest", "selline", "sellist",
        "sest", "siia", "siin", "siis", "siit", "sina", "sind", "sinna", "sinu", "sinuga", "sinust", "sir",
        "sisse", "sober", "sobrad", "sona", "soor", "su", "sul", "sulle", "surma", "surnud", "suuda", "suur",
        "suureparane", "ta", "taga", "tagasi", "taha", "tahab", "tahad", "tahaks", "tahan", "tahate", "tahendab", "tahtis",
        "tahtma", "tahtnud", "tahtsin", "taiesti", "tais", "tal", "talle", "tana", "tanan", "tanav", "tanu", "tappa",
        "tapselt", "te", "tea", "teab", "tead", "teada", "teadma", "teadnud", "teame", "tean", "teate", "teda",
        "tee", "teeb", "teed", "teeme", "teen", "tegelikult", "tegema", "tegi", "tegid", "tegin", "teha", "tehtud",
        "teid", "teie", "teiega", "teil", "teile", "teine", "teinud", "teise", "teised", "teist", "tema", "temaga",
        "temast", "tere", "terve", "toesti", "tohi", "toimub", "too", "tood", "tool", "toole", "tore", "tosi",
        "tosiselt", "tuba", "tudruk", "tule", "tuleb", "tuled", "tulema", "tulen", "tulevad", "tulge", "tuli", "tulid",
        "tulin", "tulla", "tundi", "tundub", "tunne", "tunned", "tunnen", "uhe", "uks", "uksi", "uldse", "ule",
        "ules", "umber", "umbes", "usna", "usu", "usun", "utle", "utleb", "utlema", "utlen", "utles", "utlesid",
        "utlesin", "uue", "uuesti", "uus", "vaadake", "vaadata", "vaata", "vabandage", "vabandust", "vaga", "vahe", "vahel",
        "vahem", "vahemalt", "vaid", "vaike", "vait", "vaja", "vajan", "valja", "valjas", "valmis", "vana", "varem",
        "varsti", "vasakule", "vastu", "veel", "veidi", "vend", "vesi", "viga", "viimane", "viis", "vist", "voi",
        "voib", "voibolla", "void", "voiks", "voimalik", "voimalus", "voime", "voin", "vota", "votan", "votke", "votta",
    },
    "fi": {
        "aamu", "ai", "aiemmin", "aika", "aikaa", "aikaan", "aina", "ainakin", "ainoa", "aiti", "aitisi", "aivan",
        "ajan", "ajattelin", "ala", "alas", "alkaa", "anna", "antaa", "anteeksi", "apua", "asia", "asiaa", "asian",
        "asiat", "asioita", "asti", "auta", "auto", "auttaa", "bussi", "dollaria", "edes", "ehka", "ei", "eika",
        "eiko", "eilen", "eivat", "elaa", "eli", "emme", "en", "enaa", "enemman", "enka", "ennen", "ensimmainen",
        "ensin", "enta", "eri", "et", "etko", "etta", "ette", "ettei", "etten", "ettet", "haloo", "halua",
        "haluaa", "haluaisin", "haluan", "haluat", "haluatko", "halunnut", "halusi", "halusin", "haluta", "han", "hanella", "hanelle",
        "hanen", "hanesta", "hanet", "hanta", "hataa", "hauska", "hauskaa", "he", "hei", "heidan", "heidat", "heille",
        "heippa", "heita", "helppo", "herra", "heti", "hetki", "hetkinen", "hieman", "hieno", "hienoa", "hiljaa", "hinta",
        "hitto", "hotelli", "hullu", "huomenna", "huomenta", "huone", "huono", "huonoa", "hyva", "hyvaa", "hyvalta", "hyvin",
        "ihan", "ihminen", "ihmiset", "ihmisia", "ikina", "ikkuna", "ilman", "iltaa", "irti", "isa", "isani", "isasi",
        "iso", "itse", "ja", "jaa", "jalkeen", "jata", "jattaa", "jo", "john", "joka", "jokin", "joku",
        "jolla", "jonka", "jonkun", "joo", "jopa", "jos", "joskus", "jossa", "jota", "jotain", "jotakin", "joten",
        "jotka", "jotta", "jumala", "juna", "juttu", "juuri", "kahvi", "kai", "kaiken", "kaikkea", "kaikki", "kaksi",
        "kanssa", "kanssaan", "kanssani", "kanssasi", "kapteeni", "katso", "katsokaa", "katu", "kauan", "kaukana", "kaunis", "kaupunki",
        "kaveri", "kavi", "kay", "kayttaa", "kello", "kerran", "kerro", "kerron", "kertaa", "kertoa", "kertoi", "kertonut",
        "ketaan", "kiinni", "kiitos", "kiltti", "kiva", "kohta", "koko", "kolme", "koska", "koskaan", "kotiin", "kotona",
        "kovin", "kuin", "kuinka", "kuitenkin", "kuka", "kukaan", "kulta", "kun", "kunnes", "kunnossa", "kuoli", "kuollut",
        "kuten", "kuule", "kuulin", "kuulla", "kuullut", "kuulostaa", "kuuluu", "kuuntele", "kylla", "kyse", "lahella", "lahtea",
        "lapi", "lapset", "lapsi", "leipa", "lentokentta", "liian", "liikaa", "lisaa", "lopeta", "loysin", "loytaa", "luoja",
        "luulen", "luulet", "luuletko", "luulin", "ma", "maa", "maailma", "maailman", "maksaa", "me", "meidan", "meidat",
        "meilla", "meille", "meista", "meita", "melkein", "mene", "menee", "menen", "meni", "menna", "mennaan", "menossa",
        "miehen", "mielta", "mies", "mihin", "mika", "mikaan", "mikset", "miksi", "milloin", "milta", "mina", "minakin",
        "minka", "minne", "minua", "minulla", "minulle", "minulta", "minun", "minusta", "minut", "minuun", "minuuttia", "missa",
        "mista", "mita", "mitaan", "miten", "muista", "muita", "mukaan", "mukana", "mukava", "mutta", "muut", "muuta",
        "muuten", "myohemmin", "myos", "nae", "naen", "nahda", "nahdaan", "nahnyt", "nain", "nainen", "nakemiin", "nama",
        "nayta", "naytat", "nayttaa", "ne", "neiti", "nelja", "new", "niin", "niinko", "niista", "niita", "nimi",
        "no", "noin", "nopeasti", "nuo", "nyt", "odota", "odottaa", "ohi", "oikea", "oikeassa", "oikeasti", "oikein",
        "okei", "ole", "olemme", "olen", "olet", "oletko", "olette", "oletteko", "olevan", "oli", "oliko", "olimme",
        "olin", "olisi", "olisin", "olisit", "olit", "olivat", "olla", "ollut", "on", "ongelma", "onko", "osa",
        "osaa", "ota", "otan", "ottaa", "ovat", "ovi", "paasta", "pahoillani", "paikka", "paitsi", "paiva", "paivaa",
        "paivan", "pakko", "palaa", "paljon", "paljonko", "paras", "parempi", "pari", "paska", "pian", "pida", "pidan",
        "pieni", "pikku", "pitaa", "pitaisi", "pitanyt", "piti", "poika", "pois", "poissa", "pojat", "poliisi", "poyta",
        "puhu", "puhua", "puhun", "puhut", "pysty", "pysy", "pyydan", "raha", "rahaa", "rahat", "rakastan", "riittaa",
        "rouva", "saa", "saada", "saamme", "saan", "saanko", "saanut", "saat", "sai", "sain", "sait", "sama",
        "samaa", "sano", "sanoa", "sanoi", "sanoin", "sanoit", "sanon", "sanonut", "sanoo", "se", "sellainen", "sellaista",
        "selva", "sen", "senkin", "siella", "sielta", "siihen", "siina", "siis", "siita", "siksi", "silla", "sille",
        "silloin", "silta", "silti", "sina", "sinne", "sinua", "sinulla", "sinulle", "sinun", "sinusta", "sinut", "sinuun",
        "sir", "sisaan", "sita", "sitten", "soita", "soittaa", "suoraan", "suuri", "taalla", "taalta", "taas", "tahan",
        "tahansa", "tai", "takaisin", "takia", "talla", "talo", "tama", "taman", "tana", "tanaan", "tanne", "tapahtui",
        "tapahtunut", "tapahtuu", "tappaa", "tarkoitat", "tarkoittaa", "tarpeeksi", "tarvitse", "tarvitsee", "tarvitsemme", "tarvitsen", "tassa", "tasta",
        "tata", "tavalla", "tavata", "taysin", "taytyy", "te", "tee", "teemme", "teen", "teet", "tehda", "tehdaan",
        "tehnyt", "teidan", "teidat", "teilla", "teille", "tein", "teit", "teita", "tekee", "teki", "terve", "tervetuloa",
        "tieda", "tiedan", "tiedat", "tiedatko", "tiennyt", "tiesin", "tietaa", "tietenkin", "tietysti", "todella", "tohtori", "toinen",
        "toisen", "toita", "toivottavasti", "toki", "tosi", "totta", "tule", "tulee", "tulen", "tuli", "tulin", "tulkaa",
        "tulla", "tullut", "tulossa", "tunne", "tunnen", "tuntia", "tuntuu", "tuo", "tuoli", "tuolla", "tuon", "tuota",
        "tyota", "tytto", "ulos", "usko", "uskoa", "uskon", "uuden", "uusi", "vaan", "vahan", "vahemman", "vai",
        "vaikea", "vaikka", "vain", "valmis", "vanha", "varma", "varmaan", "varmasti", "varten", "vasen", "vasta", "vastaan",
        "vesi", "vie", "viela", "viime", "viisi", "voi", "voida", "voimme", "voin", "voinko", "voinut", "voisi",
        "voisin", "voit", "voitko", "voitte", "vuoden", "vuoksi", "vuosi", "vuotta", "yha", "yhden", "yhdessa", "yhta",
        "yksi", "yksin", "yli", "ylos", "ymmarra", "ymmarran", "yo", "yota", "yritan", "yrittaa", "ystava", "ystavani",
    },
    "fr": {
        "a", "abord", "accord", "acheter", "addition", "adieu", "adore", "aeroport", "affaire", "affaires", "agent", "ah",
        "ai", "aide", "aider", "aime", "aimerais", "ainsi", "air", "ait", "allait", "aller", "allez", "allons",
        "alors", "ami", "amie", "amis", "amour", "annee", "annees", "ans", "appele", "appeler", "appelle", "apres",
        "argent", "arme", "arrete", "arreter", "arretez", "arrive", "arriver", "as", "assez", "attend", "attendez", "attendre",
        "attends", "attention", "au", "aucun", "aucune", "aujourdhui", "aura", "aurais", "aurait", "aussi", "autant", "autre",
        "autres", "aux", "avais", "avait", "avant", "avec", "avez", "avoir", "avons", "bas", "beau", "beaucoup",
        "bebe", "belle", "ben", "besoin", "bien", "bientot", "bizarre", "boire", "bon", "bonjour", "bonne", "bonsoir",
        "boulot", "bureau", "bus", "ca", "cafe", "calme", "capitaine", "car", "carte", "cas", "cause", "ce",
        "ceci", "cela", "celui", "ces", "cet", "cette", "ceux", "chaise", "chambre", "chance", "changer", "chaque",
        "chef", "cherche", "chercher", "cherie", "chez", "chien", "choix", "chose", "choses", "cinq", "coeur", "combien",
        "comme", "commence", "comment", "comprends", "compris", "compte", "confiance", "connais", "contre", "corps", "cote", "coup",
        "cours", "croire", "crois", "croyais", "cuisine", "daccord", "dans", "de", "dehors", "deja", "demain", "demande",
        "demander", "depuis", "dernier", "derniere", "derriere", "des", "desole", "desolee", "dessus", "deux", "devant", "devez",
        "devoir", "devrais", "devrait", "dieu", "difficile", "dirait", "dire", "dis", "disent", "disons", "dit", "dites",
        "docteur", "dois", "doit", "dollars", "donc", "donne", "donner", "dont", "dr", "droit", "droite", "drole",
        "du", "dur", "eau", "ecole", "ecoute", "ecouter", "eh", "elle", "elles", "en", "encore", "endroit",
        "enfant", "enfants", "enfin", "ensemble", "ensuite", "entendre", "entendu", "entre", "entrer", "envie", "equipe", "es",
        "espere", "essaie", "essaye", "essayer", "est", "et", "etaient", "etais", "etait", "etat", "ete", "etes",
        "etiez", "etre", "etudier", "eu", "euh", "eux", "exactement", "excusez", "facile", "facon", "faire", "fais",
        "faisait", "faisons", "fait", "faites", "famille", "faut", "faute", "femme", "femmes", "fenetre", "fera", "ferai",
        "fete", "feu", "fille", "filles", "film", "fils", "fin", "fini", "fois", "font", "fort", "fou",
        "frere", "garcon", "garde", "garder", "gare", "gars", "gauche", "genial", "genre", "gens", "grand", "grande",
        "gros", "guerre", "he", "hein", "heure", "heures", "heureux", "hey", "hier", "histoire", "homme", "hommes",
        "hotel", "ici", "idee", "ii", "il", "ils", "important", "importe", "impossible", "inquiete", "instant", "ira",
        "jamais", "je", "jeu", "jeune", "jouer", "jour", "journee", "jours", "juste", "la", "laisse", "laisser",
        "le", "les", "leur", "leurs", "lieu", "lit", "loin", "longtemps", "lui", "ma", "madame", "main",
        "mains", "maintenant", "mais", "maison", "mal", "maman", "manger", "marche", "mari", "mariage", "matin", "mauvais",
        "me", "mec", "meilleur", "meme", "merci", "merde", "mere", "mes", "mettre", "mieux", "minute", "minutes",
        "mis", "mme", "moi", "moins", "mois", "moment", "mon", "monde", "monsieur", "montrer", "mort", "morte",
        "mot", "mourir", "ne", "ni", "nom", "non", "nos", "notre", "nous", "nouveau", "nouvelle", "nuit",
        "numero", "oh", "ok", "on", "ont", "ou", "ouais", "oublie", "oui", "pain", "papa", "par",
        "parce", "pardon", "parents", "parfait", "parfois", "parle", "parler", "part", "parti", "partie", "partir", "pas",
        "passe", "passer", "payer", "pays", "peine", "pendant", "pensais", "pense", "penser", "penses", "pensez", "perdre",
        "perdu", "pere", "personne", "personnes", "petit", "petite", "peu", "peur", "peut", "peuvent", "peux", "pire",
        "place", "plaisir", "plait", "plan", "plein", "plus", "plutot", "point", "police", "porte", "pos", "possible",
        "pour", "pourquoi", "pourrais", "pourrait", "pouvais", "pouvez", "pouvoir", "pouvons", "premier", "premiere", "prend", "prendre",
        "prends", "prenez", "pres", "presque", "pret", "prie", "pris", "prison", "prix", "probleme", "propos", "propre",
        "pu", "puis", "putain", "quand", "quatre", "que", "quel", "quelle", "quelque", "quelques", "question", "qui",
        "quoi", "raison", "regarde", "regarder", "regardez", "rendre", "rentrer", "reste", "rester", "retour", "reviens", "revoir",
        "rien", "route", "rue", "sa", "sais", "sait", "salut", "sang", "sans", "savais", "savent", "savez",
        "savoir", "savons", "se", "securite", "semaine", "semble", "sens", "sera", "serai", "serais", "serait", "service",
        "ses", "seul", "seule", "seulement", "si", "sil", "soeur", "soir", "sois", "soit", "sommes", "son",
        "sont", "sorte", "sortir", "sous", "souviens", "suffit", "suis", "suite", "sujet", "super", "sur", "sure",
        "ta", "table", "tant", "tard", "taxi", "te", "telephone", "tellement", "temps", "terre", "tes", "tete",
        "the", "tiens", "toi", "tomber", "ton", "tot", "toujours", "tour", "tous", "tout", "toute", "toutes",
        "train", "travail", "travaille", "travailler", "tres", "trois", "trop", "trouve", "trouver", "truc", "tu", "tue",
        "tuer", "type", "un", "une", "va", "vais", "vas", "venez", "venir", "venu", "verite", "vers",
        "veulent", "veut", "veux", "viande", "vie", "viens", "vient", "vieux", "ville", "vite", "vivre", "voici",
        "voient", "voila", "voir", "vois", "voit", "voiture", "vont", "vos", "votre", "voudrais", "voulais", "voulait",
        "voulez", "vouloir", "voulons", "voulu", "vous", "voyez", "voyons", "vrai", "vraiment", "vu", "vue", "yeux",
    },
    "hr": {
        "ako", "ali", "auto", "autobus", "bar", "bas", "bez", "bi", "bih", "bila", "bili", "bilo",
        "bio", "bismo", "biste", "bit", "biti", "blizu", "bog", "bok", "bolje", "boze", "brat", "briga",
        "broj", "brzo", "bude", "budem", "budi", "caj", "cak", "ce", "cega", "cekaj", "cemo", "cemu",
        "ces", "cete", "cetiri", "cijeli", "cijena", "cini", "covjece", "covjek", "covjeka", "cu", "cudno", "cuo",
        "da", "daj", "dakle", "daleko", "dalje", "dan", "dana", "danas", "dao", "dati", "decki", "desno",
        "dijete", "dio", "do", "dobar", "dobio", "dobiti", "dobra", "dobro", "doci", "događa", "dogodilo", "dok",
        "dolara", "dolazi", "dolazim", "dolje", "dosao", "dosla", "dosli", "dosta", "dovidenja", "dovoljno", "dođi", "dr",
        "drago", "druge", "drugi", "drugo", "drzi", "dugo", "duso", "dva", "dvije", "evo", "ga", "gde",
        "gdje", "glavu", "gledaj", "god", "godina", "godine", "gore", "gospodine", "gotovo", "govori", "govorim", "govoriti",
        "grad", "ha", "hajde", "halo", "hej", "hoce", "hoces", "hocu", "hotel", "htio", "htjela", "hvala",
        "i", "ici", "ide", "idem", "idemo", "ides", "idi", "ih", "ikada", "ili", "im", "ima",
        "imaju", "imala", "imali", "imam", "imamo", "imao", "imas", "imate", "imati", "ime", "ipak", "istina",
        "isto", "iz", "iza", "izgleda", "između", "ja", "jako", "jasno", "je", "jedan", "jedini", "jedna",
        "jedno", "jednog", "jednom", "jednostavno", "jednu", "jer", "jesam", "jesi", "jest", "jeste", "joj", "jos",
        "ju", "jucer", "jutro", "kad", "kada", "kakav", "kako", "kao", "kasnije", "kava", "kaze", "kazem",
        "kazes", "ko", "kod", "koga", "koja", "koje", "kojeg", "koji", "koju", "koliko", "kolodvor", "kroz",
        "kruh", "kuca", "kuce", "kuci", "kucu", "kuhinja", "lak", "lako", "laku", "li", "lijepa", "lijepo",
        "lijevo", "ljude", "ljudi", "los", "lose", "luka", "ma", "majka", "mali", "malo", "mama", "manje",
        "me", "mene", "meni", "meso", "mi", "minuta", "misli", "mislila", "mislim", "mislio", "mislis", "mislite",
        "mjesto", "mnogo", "mnom", "moci", "mog", "mogao", "mogla", "mogli", "mogu", "moj", "moja", "moje",
        "moju", "molim", "mom", "mora", "moram", "moramo", "morao", "moras", "morate", "mozda", "moze", "mozemo",
        "mozes", "mozete", "mrtav", "mu", "muskarac", "na", "naci", "nacin", "nadam", "najbolje", "nakon", "nam",
        "nama", "napravio", "napraviti", "naravno", "nas", "nasa", "nasao", "nase", "natrag", "ne", "nece", "necemo",
        "neces", "necu", "nego", "neka", "neke", "neki", "neko", "nekog", "nekoga", "nekoliko", "nema", "nemam",
        "nemas", "nemoj", "nesto", "netko", "ni", "nije", "nikad", "nikada", "nisam", "nisi", "nismo", "nista",
        "niste", "nisu", "nitko", "njega", "njegov", "njegova", "njemu", "njezin", "njih", "njihov", "njim", "njima",
        "njom", "nju", "no", "noc", "noci", "nov", "novac", "novi", "obitelj", "oca", "oci", "od",
        "odavde", "odlicno", "odmah", "oh", "ok", "oko", "on", "ona", "onaj", "onda", "one", "oni",
        "ono", "opet", "oprosti", "oprostite", "osim", "osjecam", "osoba", "ostati", "otac", "otici", "otisao", "ova",
        "ovaj", "ovako", "ovamo", "ovde", "ovdje", "ove", "ovim", "ovo", "ovog", "ovoga", "ovom", "ovu",
        "ozbiljno", "pa", "par", "pet", "pitanje", "po", "pod", "pogledaj", "pomoc", "pomoci", "poput", "posao",
        "posla", "poslije", "postoji", "potpuno", "pravi", "pravo", "pravu", "preko", "prema", "prestani", "previse", "prica",
        "prijatelj", "prijatelji", "prije", "prilicno", "problem", "problema", "pronaci", "protiv", "prozor", "prvi", "prvo", "puno",
        "pusti", "put", "puta", "racun", "radi", "radim", "radio", "radis", "raditi", "ravno", "razgovarati", "razumijem",
        "reci", "redu", "rekao", "rekla", "rekli", "rijec", "ruke", "s", "sa", "sad", "sada", "sam",
        "sama", "samo", "sat", "sati", "se", "sebe", "sebi", "sestra", "si", "siguran", "sigurna", "sigurno",
        "sin", "sjajno", "slucaj", "slucaju", "slusaj", "smo", "soba", "spreman", "sranje", "srce", "sretan", "sta",
        "stalno", "stani", "star", "stari", "ste", "sto", "stol", "stolica", "strane", "stvar", "stvari", "stvarno",
        "su", "super", "sutra", "svaki", "sve", "svi", "svijet", "sviđa", "svog", "svoj", "svoje", "svojim",
        "svoju", "ta", "tada", "taj", "tako", "također", "tamo", "tata", "te", "tebe", "tebi", "tek",
        "tesko", "tezak", "ti", "tim", "tip", "tko", "to", "tobom", "tocno", "tog", "toga", "toliko",
        "tom", "tome", "treba", "trebala", "trebali", "trebalo", "trebam", "trebamo", "trebao", "trebas", "trenutak", "tri",
        "tu", "tvoj", "tvoja", "tvoje", "tvoju", "u", "ubio", "ubiti", "ucinio", "uciniti", "uh", "ulica",
        "unutra", "uopce", "upravo", "uskoro", "uvijek", "uz", "uzeti", "uzmi", "valjda", "vam", "vama", "van",
        "vas", "vasa", "vase", "vazno", "vec", "vecer", "veceras", "velik", "veliki", "veoma", "veze", "vezi",
        "vi", "vidi", "vidim", "vidimo", "vidio", "vidis", "vidjela", "vidjeli", "vidjeti", "vise", "vjerojatno", "vjerovati",
        "vjerujem", "vlak", "voda", "voli", "volim", "volio", "vrata", "vrati", "vratiti", "vremena", "vrijeme", "vrlo",
        "za", "zaista", "zajedno", "zao", "zapravo", "zar", "zasto", "zato", "zbog", "zdravo", "zele", "zeli",
        "zelim", "zelio", "zelis", "zelite", "zeljeti", "zemlja", "zena", "zene", "zenu", "zivot", "zivota", "zivotu",
        "zna", "znaci", "znala", "znam", "znamo", "znao", "znas", "znate", "znati", "zove", "zracna", "zvuci",
    },
    "hu": {
        "abba", "abban", "ablak", "add", "addig", "aggodj", "aha", "ahhoz", "ahogy", "ahol", "ajto", "akar",
        "akarja", "akarni", "akarod", "akarok", "akarom", "akarsz", "akart", "akartam", "aki", "akik", "akit", "akkor",
        "alatt", "alig", "all", "allj", "allomas", "ami", "amig", "amikor", "amint", "amit", "annak", "annyi",
        "annyira", "anya", "anyam", "apa", "apam", "ar", "arra", "arrol", "asztal", "at", "attol", "auto",
        "az", "azert", "azok", "azon", "azonnal", "azt", "aztan", "azzal", "baj", "balra", "ban", "bar",
        "baratom", "barmi", "barmit", "be", "bele", "belole", "ben", "benne", "beszel", "beszelek", "beszelni", "beszelsz",
        "biztos", "biztosan", "bocs", "bocsanat", "boldog", "busz", "csak", "csinal", "csinalni", "csinalom", "csinalsz", "de",
        "doktor", "dolgok", "dolgokat", "dolgot", "dolog", "dragam", "ebben", "ebbol", "eddig", "eg", "egesz", "egy",
        "egyaltalan", "egyedul", "egyenesen", "egyet", "egyetlen", "egyik", "egymast", "egyszer", "egyszeruen", "egyutt", "ejjel", "ejszaka",
        "ejszakat", "el", "eleg", "elet", "eletben", "eletem", "ellen", "elment", "elnezest", "elobb", "eloszor", "elott",
        "elso", "ember", "emberek", "embert", "emlekszel", "emlekszem", "en", "engem", "ennek", "ennyi", "enyem", "epp",
        "eppen", "erdekel", "erre", "errol", "ert", "erte", "erted", "ertem", "erzem", "es", "este", "estet",
        "ev", "eve", "eves", "ez", "ezek", "ezeket", "ezelott", "ezen", "ezert", "ezt", "ezzel", "fel",
        "fenebe", "ferfi", "fiam", "ficko", "figyelj", "fiu", "fiuk", "fog", "fogd", "fogja", "fognak", "fogod",
        "fogok", "fogom", "fogsz", "fogunk", "folyik", "fonok", "fontos", "francba", "furcsa", "gond", "gondolod", "gondolom",
        "gondolsz", "gondoltam", "gyere", "gyerek", "gyerunk", "gyonyoru", "gyorsan", "ha", "hadd", "hagyd", "hallo", "hallottam",
        "halott", "hamarosan", "hanem", "hangzik", "hany", "harom", "hat", "haver", "haz", "haza", "he", "hello",
        "hely", "helyes", "helyet", "helyzet", "het", "hiszed", "hiszem", "hittem", "hogy", "hogyan", "hol", "holnap",
        "honnan", "hosszu", "hova", "hozza", "hozzam", "hulye", "ide", "ideje", "ido", "idot", "igaz", "igaza",
        "igazabol", "igazad", "igazan", "igazi", "igen", "igy", "ilyen", "ilyet", "inkabb", "innen", "is", "isten",
        "istenem", "itt", "ja", "jack", "jaj", "jar", "jelent", "jelenti", "jo", "jobb", "jobban", "jobbra",
        "john", "jojjon", "jol", "jon", "jonni", "jott", "jottem", "jovok", "kapitany", "kave", "kedves", "kell",
        "kellene", "kellett", "kene", "kenyer", "kepes", "kerek", "kerem", "kerlek", "kesobb", "kesz", "keszen", "ket",
        "keves", "kevesebb", "ki", "kicsi", "kicsit", "kiraly", "kis", "komolyan", "konnyu", "korabban", "kosz", "koszi",
        "koszonom", "kovetkezo", "kozel", "kozott", "lany", "latni", "latod", "latom", "latta", "lattam", "le", "legalabb",
        "legjobb", "legy", "legyen", "lehet", "lenne", "lennek", "lenni", "lesz", "leszek", "leszel", "lett", "ma",
        "maga", "magad", "magam", "maganak", "magat", "maguk", "majd", "majdnem", "mar", "maradj", "mas", "masik",
        "mast", "meg", "meghalt", "megint", "megis", "megvan", "megy", "megyek", "megyunk", "melyik", "menj", "menjen",
        "menjunk", "mennem", "menni", "mennyi", "mennyire", "ment", "mert", "mesz", "mi", "miatt", "micsoda", "mielott",
        "mienk", "miert", "mig", "mikor", "milyen", "mind", "minden", "mindenki", "mindent", "mindig", "mindjart", "minket",
        "mint", "mintha", "miota", "mire", "mirol", "miss", "mit", "miutan", "mivel", "mond", "mondani", "mondd",
        "mondja", "mondod", "mondom", "mondott", "mondta", "mondtad", "mondtam", "most", "mr", "mrs", "mulva", "munka",
        "muszaj", "na", "nagy", "nagyon", "nagyszeru", "nap", "napot", "ne", "negy", "neha", "nehany", "nehez",
        "neked", "nekem", "neki", "nekik", "nekunk", "nelkul", "nem", "neve", "new", "nez", "nezd", "nezz",
        "nezze", "nincs", "no", "nos", "o", "oda", "oh", "ok", "oke", "oket", "olyan", "on",
        "ora", "oreg", "orszag", "orulok", "ossze", "osszes", "ot", "ota", "otlet", "ott", "otthon", "ove",
        "ovek", "par", "pedig", "penz", "penzt", "perc", "persze", "pont", "pontosan", "ra", "rad", "rajta",
        "ram", "reggel", "reggelt", "regi", "remek", "remelem", "rendben", "repuloter", "rola", "rossz", "rosszul", "sajat",
        "sajnalom", "se", "segiteni", "segitseg", "sem", "semmi", "semmit", "senki", "sikerult", "sincs", "soha", "sok",
        "sokat", "sokkal", "sose", "sosem", "sracok", "szabad", "szalloda", "szamit", "szamla", "szek", "szep", "szepen",
        "szeretem", "szeretlek", "szeretnek", "szeretnem", "szerint", "szerinted", "szerintem", "szia", "sziasztok", "szo", "szoba", "szol",
        "szoval", "szuksege", "szuksegem", "talalkozunk", "talaltam", "talan", "tart", "tavol", "te", "tea", "tedd", "teged",
        "tegnap", "tehat", "teljes", "teljesen", "tenni", "tenyleg", "termeszetesen", "tessek", "testver", "tetszik", "tett", "tette",
        "tettem", "ti", "tied", "tietek", "tiszta", "tobb", "tobbe", "tobbet", "tobbi", "tokeletes", "tole", "tolem",
        "tortenik", "tortent", "tovabb", "tud", "tudja", "tudjak", "tudjuk", "tudni", "tudod", "tudok", "tudom", "tudsz",
        "tudta", "tudtam", "tul", "tunik", "udv", "ugy", "ugyan", "ugye", "ugyhogy", "uj", "ujra", "ur",
        "uram", "utan", "utana", "utca", "utolso", "vagy", "vagyok", "vagytok", "vagyunk", "val", "valaha", "valaki",
        "valakit", "valami", "valamit", "valo", "valoban", "valojaban", "valoszinuleg", "van", "vannak", "varj", "varos", "vedd",
        "vege", "vegre", "vegul", "vel", "vele", "veled", "velem", "veluk", "velunk", "vettem", "vicces", "vilag",
        "vissza", "viszlat", "viszont", "viszontlatasra", "viz", "volna", "volt", "voltak", "voltal", "voltam", "voltunk", "vonat",
    },
    "id": {
        "ada", "adalah", "agar", "agen", "ah", "air", "akan", "akhir", "akhirnya", "aku", "alasan", "aman",
        "ambil", "amerika", "anak", "anakku", "and", "anda", "aneh", "anjing", "antara", "apa", "apakah", "apapun",
        "api", "artinya", "astaga", "atas", "atau", "awal", "ayah", "ayahku", "ayahmu", "ayo", "ayolah", "bagaimana",
        "bagi", "bagian", "bagus", "bahagia", "bahasa", "bahkan", "bahwa", "baik", "baiklah", "bajingan", "bandara", "bangun",
        "bantu", "bantuan", "banyak", "baru", "bawa", "bawah", "bayi", "beberapa", "begitu", "bekerja", "belajar", "belakang",
        "belum", "benar", "benarkah", "berada", "berakhir", "berapa", "berarti", "berbeda", "berbicara", "bercanda", "berdiri", "berdua",
        "bergerak", "berharap", "berhasil", "berhenti", "beri", "berikan", "beritahu", "berjalan", "berkata", "bermain", "berpikir", "bersama",
        "bertahan", "bertanya", "bertemu", "berubah", "beruntung", "berusaha", "besar", "besok", "biar", "biarkan", "biasa", "bicara",
        "bicarakan", "bilang", "bisa", "bisakah", "bodoh", "boleh", "brengsek", "bu", "buat", "buka", "bukan", "bukankah",
        "buku", "bulan", "bumi", "bung", "bunuh", "buruk", "bus", "butuh", "cantik", "cara", "cari", "cepat",
        "cerita", "cinta", "coba", "cukup", "cuma", "dalam", "dan", "dapat", "dapatkan", "darah", "dari", "daripada",
        "dasar", "datang", "dekat", "demi", "dengan", "denganku", "denganmu", "dengannya", "dengar", "dengarkan", "depan", "di",
        "dia", "diam", "dilakukan", "dimana", "diri", "diriku", "dirimu", "dirinya", "disana", "disini", "dokter", "dua",
        "duduk", "dulu", "dunia", "eh", "empat", "film", "fncandara", "gadis", "gila", "guru", "hai", "hal",
        "halo", "hampir", "hanya", "harga", "hari", "harus", "hati", "hebat", "hei", "hentikan", "hey", "hidup",
        "hidupku", "hilang", "hotel", "ia", "ibu", "ibuku", "ibumu", "ide", "ikut", "indah", "ingat", "ingin",
        "inginkan", "ini", "it", "itu", "itulah", "iya", "jadi", "jalan", "jam", "jangan", "janji", "jatuh",
        "jauh", "jawab", "jelas", "jendela", "jika", "john", "juga", "jumpa", "kabar", "kaki", "kalau", "kali",
        "kalian", "kamar", "kami", "kamu", "kan", "kanan", "kantor", "kapal", "kapan", "kapten", "karena", "kasih",
        "kasus", "kata", "katakan", "kau", "kawan", "ke", "kecil", "kecuali", "kedua", "kehidupan", "kehilangan", "kekuatan",
        "kelas", "keluar", "keluarga", "kemana", "kemari", "kemarin", "kematian", "kembali", "kemudian", "kenal", "kenapa", "kepada",
        "kepala", "keras", "keren", "kereta", "kerja", "kesalahan", "kesempatan", "kesini", "ketika", "khawatir", "kira", "kiri",
        "kita", "kopi", "kosong", "kota", "ku", "kuat", "kubilang", "kulakukan", "kumohon", "kupikir", "kurang", "kurasa",
        "kursi", "lagi", "lain", "lainnya", "lakukan", "lalu", "lama", "langsung", "lari", "lebih", "lepaskan", "lewat",
        "lihat", "lihatlah", "lima", "luar", "lucu", "lupa", "lurus", "maaf", "maafkan", "maka", "makan", "makanan",
        "maksudku", "maksudmu", "malam", "mana", "manusia", "marah", "mari", "masa", "masalah", "masih", "masuk", "mata",
        "mati", "mau", "meja", "melakukan", "melakukannya", "melalui", "melawan", "melihat", "melihatmu", "melihatnya", "memakai", "memang",
        "membantu", "membawa", "membayar", "memberi", "memberikan", "memberitahu", "membiarkan", "membuat", "membuatku", "membuatmu", "membuatnya", "membunuh",
        "membunuhnya", "membutuhkan", "memilih", "memiliki", "meminta", "menang", "menarik", "mencari", "mencintaimu", "mencoba", "mendapat", "mendapatkan",
        "mendengar", "menembak", "menemukan", "menemukannya", "menerima", "mengambil", "mengapa", "mengatakan", "mengerti", "menggunakan", "menghancurkan", "menikah",
        "meninggal", "meninggalkan", "menit", "menjadi", "menuju", "menunggu", "menunjukkan", "menurutmu", "menyelamatkan", "menyenangkan", "merasa", "mereka",
        "minggu", "minta", "minum", "mobil", "mu", "muda", "mudah", "mulai", "mulia", "muncul", "mungkin", "nah",
        "naik", "nak", "nama", "namanya", "namun", "nanti", "negara", "no", "nomor", "nona", "nya", "nyata",
        "of", "oh", "ok", "okay", "oke", "oleh", "omong", "orang", "pada", "padaku", "padamu", "padanya",
        "pagi", "paham", "pak", "paling", "panas", "para", "pasti", "peduli", "pekerjaan", "pembunuh", "penjara", "penting",
        "penuh", "perang", "percaya", "pergi", "pergilah", "perjalanan", "perlu", "permainan", "permisi", "pernah", "pertama", "pertanyaan",
        "perusahaan", "pesan", "pesawat", "pesta", "pikir", "pikirkan", "pilihan", "pintu", "polisi", "pria", "pulang", "pun",
        "punya", "putri", "rahasia", "raja", "rasa", "rasanya", "rencana", "roti", "ruang", "rumah", "saat", "saja",
        "sakit", "salah", "sama", "sampai", "sana", "sangat", "satu", "saya", "sayang", "sebagai", "sebaiknya", "sebelum",
        "sebelumnya", "sebenarnya", "sebentar", "sebuah", "secara", "sedang", "sedikit", "segalanya", "segera", "seharusnya", "sejak", "sekali",
        "sekarang", "sekitar", "sekolah", "selalu", "selama", "selamat", "selesai", "seluruh", "semakin", "sementara", "semoga", "sempurna",
        "semua", "semuanya", "senang", "sendiri", "sendirian", "senjata", "seorang", "sepanjang", "seperti", "sepertinya", "serius", "seseorang",
        "sesuatu", "setelah", "setiap", "setidaknya", "setuju", "si", "sial", "sialan", "siang", "siap", "siapa", "siapapun",
        "silahkan", "silakan", "sini", "soal", "sore", "stasiun", "suara", "suatu", "sudah", "suka", "sulit", "sungguh",
        "surat", "tadi", "tahu", "tahun", "tak", "takkan", "takut", "tampak", "tampaknya", "tanah", "tangan", "tanpa",
        "tapi", "tau", "teh", "telah", "telepon", "teman", "tempat", "temukan", "tenang", "tentang", "tentu", "tepat",
        "terakhir", "terbaik", "terima", "terjadi", "terlalu", "terlambat", "terlihat", "terus", "tetap", "tetapi", "the", "tiba",
        "tidak", "tidur", "tiga", "tiket", "tim", "tinggal", "tinggalkan", "tinggi", "tn", "to", "tolong", "tua",
        "tuan", "tuhan", "tunggu", "turun", "uang", "uh", "ulang", "um", "untuk", "untukku", "untukmu", "waktu",
        "waktunya", "wanita", "well", "whoa", "wow", "ya", "yah", "yakin", "yang", "yeah", "yg", "you",
    },
    "it": {
        "abbastanza", "abbia", "abbiamo", "accordo", "acqua", "ad", "adesso", "aeroporto", "agente", "ah", "ai", "aiuto",
        "al", "albergo", "alla", "alle", "allora", "almeno", "altra", "altre", "altri", "altro", "amica", "amici",
        "amico", "amo", "amore", "anche", "ancora", "andando", "andare", "andata", "andate", "andato", "andiamo", "anni",
        "anno", "appena", "arrivederci", "ascolta", "ascoltare", "aspetta", "attimo", "auto", "autobus", "avanti", "aver", "avere",
        "avessi", "avete", "aveva", "avevo", "avrebbe", "avrei", "avuto", "bagno", "bambina", "bambini", "bambino", "basta",
        "beh", "bel", "bella", "bello", "ben", "bene", "bere", "bisogno", "bravo", "buon", "buona", "buonanotte",
        "buonasera", "buongiorno", "buono", "caffe", "capire", "capisco", "capito", "capo", "carne", "carta", "casa", "caso",
        "cattivo", "cazzo", "ce", "cercando", "certo", "che", "chi", "chiama", "chiamato", "chiesto", "ci", "ciao",
        "cinque", "cio", "citta", "col", "colpa", "come", "comprare", "comunque", "con", "conosco", "conto", "contro",
        "corpo", "cosa", "cose", "cosi", "credi", "credo", "cucina", "cui", "cuore", "da", "dai", "dal",
        "dalla", "dare", "dato", "davvero", "degli", "dei", "del", "della", "delle", "dentro", "destra", "detto",
        "deve", "devi", "devo", "di", "diavolo", "dice", "dicendo", "dici", "diciamo", "dico", "dicono", "dietro",
        "difficile", "dimmi", "dio", "dire", "dispiace", "dite", "divertente", "dobbiamo", "dollari", "domanda", "domani", "donna",
        "donne", "dopo", "dottor", "dottore", "dove", "dovrebbe", "dovrei", "dovremmo", "dovresti", "dovuto", "dritto", "due",
        "e", "ecco", "ed", "eh", "ehi", "entrare", "era", "erano", "eri", "ero", "esattamente", "esatto",
        "essere", "fa", "faccia", "facciamo", "faccio", "facendo", "facile", "fai", "famiglia", "fanno", "fantastico", "far",
        "fare", "farlo", "farmi", "faro", "farti", "fate", "fatta", "fatto", "favore", "felice", "festa", "figli",
        "figlia", "figlio", "film", "fine", "finestra", "finito", "fino", "forse", "forte", "forza", "fosse", "fossi",
        "foto", "fratello", "fuori", "genere", "gente", "gia", "giorni", "giorno", "giro", "giusto", "gli", "grande",
        "grazie", "guarda", "guerra", "ha", "hai", "hanno", "ho", "idea", "ieri", "il", "importa", "importante",
        "in", "indietro", "insieme", "invece", "io", "la", "lascia", "lasciato", "lavorare", "lavoro", "le", "lei",
        "letto", "li", "lo", "lontano", "loro", "lui", "ma", "macchina", "madre", "magari", "mai", "male",
        "mamma", "mangiare", "mani", "mano", "marito", "mattina", "me", "meglio", "meno", "mentre", "merda", "mesi",
        "messo", "mezzo", "mi", "mia", "mie", "miei", "migliore", "mille", "minuti", "mio", "modo", "moglie",
        "molto", "momento", "mondo", "morire", "morte", "morto", "ne", "neanche", "nei", "nel", "nella", "nelle",
        "nemmeno", "nessun", "nessuna", "nessuno", "niente", "no", "noi", "nome", "non", "nostra", "nostri", "nostro",
        "notte", "nulla", "numero", "nuova", "nuovo", "o", "occhi", "oggi", "ogni", "oh", "ok", "okay",
        "ora", "ore", "padre", "paese", "pagare", "paio", "pane", "papa", "pare", "parla", "parlando", "parlare",
        "parlato", "parlo", "parola", "parte", "passato", "paura", "pensa", "pensare", "pensato", "pensavo", "pensi", "penso",
        "per", "perche", "perdere", "pero", "perso", "persona", "persone", "piace", "piacere", "piano", "piccola", "piccolo",
        "piedi", "piu", "po", "poco", "poi", "polizia", "porta", "portato", "possa", "possiamo", "possibile", "posso",
        "possono", "posto", "potere", "potete", "potrebbe", "potrei", "potuto", "prego", "prendere", "prendi", "preso", "presto",
        "prezzo", "prima", "primo", "probabilmente", "problema", "problemi", "pronto", "proprio", "prova", "punto", "puo", "puoi",
        "pure", "qua", "qual", "qualche", "qualcosa", "qualcuno", "quale", "qualsiasi", "quando", "quanti", "quanto", "quasi",
        "quattro", "quei", "quel", "quella", "quelle", "quelli", "quello", "questa", "queste", "questi", "questo", "qui",
        "quindi", "ragazza", "ragazze", "ragazzi", "ragazzo", "ragione", "ricordi", "ricordo", "riesco", "roba", "sa", "sacco",
        "sai", "salve", "sangue", "sanno", "sapere", "sapete", "sapevo", "sappiamo", "sara", "sarebbe", "scuola", "scusa",
        "scusi", "se", "secondo", "sedia", "sei", "sembra", "sempre", "senso", "senti", "sentire", "sentito", "sento",
        "senza", "sera", "serio", "serve", "settimana", "si", "sia", "siamo", "sicura", "sicuro", "siete", "significa",
        "signor", "signora", "signore", "signorina", "sinistra", "so", "sola", "soldi", "solo", "sono", "sorella", "sotto",
        "spero", "squadra", "sta", "stai", "stanno", "stanza", "stare", "stasera", "stata", "state", "stati", "stato",
        "stava", "stavo", "stazione", "stessa", "stesso", "stia", "stiamo", "sto", "storia", "strada", "strano", "studiare",
        "su", "sua", "subito", "succede", "successo", "sue", "sul", "sulla", "suo", "suoi", "tanto", "tardi",
        "tavolo", "taxi", "te", "telefono", "tempo", "terra", "tesoro", "testa", "ti", "tipo", "tornare", "tra",
        "traduzione", "tre", "treno", "troppo", "trovare", "trovato", "tu", "tua", "tue", "tuo", "tuoi", "tutta",
        "tutte", "tutti", "tutto", "ucciso", "ufficio", "ultima", "ultimo", "un", "una", "unica", "unico", "uno",
        "uomini", "uomo", "uscire", "va", "vado", "vai", "vanno", "vecchio", "vede", "vedere", "vedete", "vedi",
        "vediamo", "vedo", "vedono", "vengo", "vengono", "veniamo", "venire", "venite", "venuto", "veramente", "vero", "verso",
        "vi", "via", "vicino", "viene", "vieni", "vista", "visto", "vita", "vivere", "vogliamo", "voglio", "vogliono",
        "voi", "volere", "volete", "voleva", "volevo", "volta", "volte", "vorrei", "vostra", "vostro", "vuoi", "vuole",
    },
    "la": {
        "abiit", "accidit", "accipere", "accipit", "actually", "ad", "adducere", "adhuc", "admirari", "affectum", "agere", "agnus",
        "ago", "air", "album", "alii", "aliquem", "aliquid", "aliquis", "aliud", "alius", "all", "am", "amatus",
        "amicis", "amicus", "amittere", "amor", "an", "annos", "annus", "ante", "anxietas", "aperta", "aqua", "are",
        "aren", "as", "asinus", "at", "audire", "audite", "audivi", "aut", "auxilium", "avunculus", "away", "bad",
        "be", "beat", "bellum", "bene", "benignus", "bet", "bibere", "bigas", "bit", "bitch", "bonum", "bonus",
        "bulla", "by", "cacas", "cadere", "caedes", "calidum", "came", "can", "canem", "canticum", "capiens", "capillus",
        "capta", "captivitatis", "capulus", "caput", "carus", "casus", "causa", "cena", "centena", "cerritulus", "certus", "chuckles",
        "cibus", "circum", "claudere", "clausa", "clean", "coegi", "coepi", "cogitandi", "cogitare", "cogitatio", "cognovi", "colligunt",
        "conatus", "confido", "confractus", "coniectura", "consilium", "contra", "conversus", "copulabis", "cor", "corpus", "could", "cras",
        "creditis", "cubiculum", "cubile", "culpa", "cum", "cur", "cura", "currere", "currus", "cursum", "cursus", "cut",
        "dad", "damnare", "dare", "date", "datum", "de", "decem", "decies", "dedit", "deinde", "deliciae", "deorsum",
        "deus", "dicens", "dicere", "dico", "dicunt", "diebus", "dies", "difficilis", "diligenter", "discite", "diu", "diversum",
        "dixit", "do", "doctor", "does", "domina", "dominarum", "domine", "domini", "dominus", "domus", "don", "donec",
        "dude", "dulce", "dum", "duo", "durum", "dux", "duxit", "ea", "ego", "ei", "emptum", "eo",
        "eorum", "eos", "erant", "es", "esse", "essem", "est", "estis", "et", "etiam", "eum", "eundo",
        "exacte", "excusatio", "experiri", "explicare", "exspecta", "exspectans", "extra", "fabula", "facere", "faciem", "faciens", "facilis",
        "facio", "facis", "facit", "fact", "factum", "familia", "fecit", "felix", "femina", "fenestra", "fere", "fiet",
        "figura", "filia", "filius", "filtrum", "finis", "fortasse", "forte", "fortis", "fortuna", "found", "frater", "frigus",
        "front", "fucking", "fuit", "fun", "futurum", "gaudeo", "gehenna", "go", "got", "gratias", "gratis", "gravis",
        "gun", "guy", "guys", "ha", "habens", "habeo", "habere", "habes", "habet", "hac", "had", "haec",
        "has", "have", "he", "hebdomades", "hebdomadis", "hedum", "her", "heri", "heus", "hi", "hic", "his",
        "hit", "hmm", "hoc", "hodie", "home", "homines", "homo", "hora", "horae", "hospitium", "huh", "humano",
        "iam", "ianua", "ibi", "id", "idea", "idem", "iecit", "ieiunium", "ignis", "ignosce", "illae", "illi",
        "imperium", "in", "infantem", "infirmum", "ingredior", "iniuriam", "inquit", "insanire", "intelligere", "inter", "interdum", "into",
        "intus", "invenire", "ipse", "ipsum", "ire", "irrumabo", "is", "it", "ita", "iterum", "its", "iudices",
        "ius", "iustus", "iuvenes", "jack", "jesus", "job", "john", "kids", "laboravi", "laedere", "latus", "left",
        "legere", "let", "lex", "liber", "liberi", "licuit", "linea", "locus", "longe", "loquentes", "loqui", "loquor",
        "ludens", "ludere", "ludus", "lux", "ma", "magis", "magistratus", "magnus", "male", "malus", "manducare", "mane",
        "manere", "manus", "maritus", "mater", "materia", "maxime", "maximus", "may", "me", "medium", "mel", "melius",
        "memento", "mendacium", "mens", "mensa", "menses", "met", "meus", "millia", "mine", "minime", "minimus", "minus",
        "minuta", "minute", "mirabile", "mirabilis", "miss", "missus", "mittere", "modicum", "mom", "momentum", "mori", "mortem",
        "mortuus", "move", "movens", "mox", "mr", "mulier", "mulieres", "multi", "multum", "mundus", "music", "musti",
        "mutatio", "mutatum", "my", "necessitates", "negotium", "nemo", "nice", "nigrum", "nihil", "no", "nocte", "nomen",
        "non", "nos", "noster", "not", "nota", "novissime", "novus", "nox", "nullus", "numerus", "numquam", "nunc",
        "nuntium", "nuper", "nupta", "oblivisci", "occidere", "occisus", "occurrens", "occursum", "oculos", "oculus", "odium", "off",
        "officium", "oh", "ok", "omnes", "omnia", "omnino", "omnis", "on", "ones", "opera", "oppidum", "optimum",
        "opus", "or", "order", "ostende", "ostium", "our", "out", "own", "paciscor", "paenitet", "panis", "paratus",
        "parentes", "pars", "parvum", "parvus", "pater", "patet", "pauci", "pauperis", "pecunia", "pedes", "pendet", "per",
        "perditus", "perfectus", "persona", "phone", "picturam", "piece", "place", "plenus", "plus", "populus", "portum", "posse",
        "posset", "possibilis", "possum", "post", "postea", "postremo", "potentia", "potes", "potest", "praemisit", "praeses", "praeteritum",
        "pretii", "pretium", "primum", "pro", "probabiliter", "promitto", "properare", "puella", "puellarum", "puer", "pueri", "pugna",
        "pulchra", "punctum", "put", "quae", "quaesivit", "quaeso", "quaestio", "quaestiones", "quam", "quamquam", "quando", "quantus",
        "quattuor", "questus", "qui", "quia", "quid", "quidam", "quidquid", "quinque", "quis", "quisque", "quod", "quomodo",
        "quoniam", "quot", "rabidus", "ratio", "real", "recta", "red", "redditus", "reditus", "relinquens", "relinquo", "reprehendo",
        "requiem", "res", "respexit", "respondere", "retro", "rex", "ridens", "ridet", "ridiculam", "rogabat", "saltare", "salvare",
        "salve", "salvete", "sam", "sanguis", "satis", "satus", "schola", "scio", "scire", "scis", "scit", "scribe",
        "secreto", "secundo", "sed", "semel", "semper", "sensus", "sentire", "sequi", "serva", "set", "sex", "sexus",
        "shall", "she", "sic", "sicut", "significat", "signum", "silentium", "simul", "sine", "sit", "societas", "solum",
        "solus", "somewhere", "somnium", "somnum", "sonos", "sonus", "soror", "sort", "speciale", "spes", "stand", "status",
        "step", "stilla", "stipendium", "stop", "stuff", "stultus", "sum", "summus", "sumus", "sunt", "super", "supposita",
        "surculus", "suspiria", "suus", "tactus", "takes", "talis", "tata", "te", "temporibus", "temptatis", "tempus", "tenere",
        "terra", "terrebis", "the", "throw", "tibi", "timet", "to", "top", "totum", "tranquillitas", "tres", "tribulatio",
        "tu", "tulit", "tunc", "tutum", "tuum", "tuus", "ubi", "uh", "ultra", "um", "unus", "up",
        "urbs", "us", "usquam", "usus", "uterque", "uxor", "valde", "vale", "vales", "valete", "velle", "velox",
        "veniens", "venio", "venire", "venit", "vera", "verba", "verbum", "vere", "veritas", "vertere", "verum", "vesperi",
        "vester", "vetus", "via", "vici", "vide", "videns", "video", "videre", "videri", "videtur", "vigilate", "vincere",
        "vir", "vis", "vita", "vivere", "viverra", "vivit", "vivus", "vocatio", "vocatus", "vocavit", "volo", "voluit",
        "vos", "vox", "vtinam", "vult", "vultus", "want", "was", "wasn", "welcome", "will", "wow", "yeah",
        "you", "your",
    },
    "lt": {
        "abu", "aciu", "aciuk", "aha", "aisku", "ak", "akis", "ala", "alio", "anksciau", "ant", "apie",
        "ar", "arba", "arbata", "arti", "as", "ateik", "ateinu", "ateiti", "atejo", "atgal", "atleisk", "atleiskit",
        "atleiskite", "atrodai", "atrodo", "atsargiai", "atsiprasau", "atsitiko", "autobusas", "baik", "be", "beje", "bek", "bent",
        "bet", "beveik", "blogai", "blogas", "brolis", "buciau", "buk", "buna", "bus", "busi", "busiu", "but",
        "butent", "buti", "butu", "butum", "buvai", "buvau", "buvo", "cia", "dabar", "daktare", "dalis", "dalykas",
        "dar", "darai", "darau", "darba", "darbas", "darbo", "daro", "daryti", "daug", "daugiau", "dekoju", "del",
        "desine", "didelis", "diena", "dienos", "dievas", "dieve", "dievo", "dirbti", "doleriu", "draugai", "draugas", "drauge",
        "du", "duok", "duona", "duris", "durys", "dvi", "dzekai", "ei", "eik", "eiks", "eime", "eina",
        "einam", "einu", "eiti", "esame", "esate", "esi", "esu", "gaila", "gal", "galais", "galbut", "galeciau",
        "galejo", "galeti", "galetu", "galetum", "gali", "galim", "galima", "galime", "galite", "galiu", "galva", "gana",
        "gatve", "gauti", "gera", "gerai", "geras", "geriau", "geriausias", "gero", "gi", "ginkla", "girdejau", "girdi",
        "grazi", "greiciau", "greit", "greitai", "grizti", "gyvas", "gyvena", "gyvenima", "gyvenimas", "gyvenime", "gyvenimo", "gyventi",
        "i", "idomu", "iki", "ilgai", "imk", "ir", "irgi", "is", "ja", "jai", "jais", "jam",
        "jas", "jau", "jei", "jeigu", "jezau", "ji", "jie", "jiems", "jis", "jo", "jog", "jokio",
        "jokiu", "jos", "ju", "juk", "jumis", "jums", "juo", "juos", "jus", "jusu", "ka", "kad",
        "kada", "kai", "kaina", "kaip", "kaire", "kalba", "kalbeti", "kalbi", "kalbu", "kam", "kambarys", "kapitone",
        "karta", "kartais", "kartu", "kas", "kava", "kazka", "kazkas", "kazkur", "kede", "keista", "kelias", "kelio",
        "kiek", "kiekviena", "kita", "kitaip", "kitas", "kiti", "kito", "kitu", "klausau", "klausyk", "ko", "kodel",
        "koki", "kokia", "koks", "kol", "kuo", "kur", "kuri", "kuria", "kurie", "kurio", "kurios", "kuris",
        "kuriuos", "kuzia", "laba", "labai", "labanakt", "labas", "labiau", "laika", "laikas", "laiko", "langas", "lauk",
        "laukia", "leisk", "lengvas", "liaukis", "liko", "lr", "lyg", "maciau", "maiklai", "malonu", "mama", "man",
        "manai", "manau", "mane", "manes", "maniau", "manim", "manimi", "mano", "masina", "matai", "matau", "matei",
        "matyti", "mazai", "mazas", "maziau", "mergina", "merginos", "mes", "metai", "metas", "metu", "metus", "mieloji",
        "miestas", "mintis", "minuciu", "mire", "mirties", "moteris", "motina", "mumis", "mums", "mus", "musu", "myli",
        "myliu", "na", "nagi", "nakti", "naktis", "namas", "namie", "namo", "namu", "namuose", "namus", "nauja",
        "naujas", "ne", "nebus", "nebuvo", "negali", "negalima", "negalime", "negaliu", "negerai", "negi", "nei", "nemanau",
        "nenori", "nenoriu", "nepatinka", "nera", "nereikia", "nes", "nesijaudink", "nesu", "nesuprantu", "nesvarbu", "net", "neturi",
        "neturiu", "nezinau", "niekad", "niekada", "niekam", "niekas", "nieko", "niekur", "noreciau", "norejau", "norejo", "noreti",
        "nori", "norite", "noriu", "nors", "nuo", "nuostabu", "nutiko", "nuzudyti", "oho", "oro", "padare", "padarei",
        "padariau", "padaryti", "padek", "padeti", "pagal", "pagalba", "pagalbos", "pagaliau", "paklausyk", "palauk", "palaukit", "palikti",
        "pamatyti", "panele", "pas", "pasake", "pasakiau", "pasakyk", "pasakysiu", "pasakyt", "pasakyti", "pasauli", "pasaulio", "pasaulis",
        "pasaulyje", "pasikalbeti", "pasiruoses", "paskui", "paskutinis", "pat", "pati", "patiketi", "patinka", "pats", "pavyko", "paziurek",
        "per", "pinigai", "pinigu", "pinigus", "pirma", "pirmas", "pirmyn", "po", "ponai", "ponas", "pone", "ponia",
        "prasau", "prasom", "prie", "pries", "pro", "problemu", "puikiai", "puiku", "puikus", "puse", "radau", "ramiai",
        "rankas", "rasti", "reikejo", "reikes", "reikia", "reiskia", "rimtai", "rytas", "rytoj", "sakai", "sakau", "sake",
        "sakei", "sakiau", "sako", "sakyk", "sakyti", "salia", "salis", "sasa", "sau", "savaite", "save", "savo",
        "seima", "seimos", "sekasi", "senas", "seniai", "sere", "si", "sia", "siaip", "siandien", "siek", "sio",
        "sios", "sis", "sita", "sitaip", "sitas", "sito", "siuo", "stai", "stalas", "stotis", "su", "sudas",
        "sunku", "sunkus", "sunus", "supranti", "suprantu", "supratai", "supratau", "svarbu", "sveika", "sveikas", "sveiki", "ta",
        "taciau", "tad", "tada", "tai", "taigi", "taip", "tam", "tania", "tarp", "tarsi", "tas", "tau",
        "tave", "taves", "tavim", "tavimi", "tavo", "tegu", "teisingai", "teisus", "teks", "ten", "teti", "tetis",
        "tevas", "tie", "tiek", "tiesa", "tiesiai", "tiesiog", "tik", "tikiuosi", "tikra", "tikrai", "tikras", "tikriausiai",
        "to", "todel", "toki", "tokia", "tokie", "tokio", "tokiu", "toks", "toli", "toliau", "tos", "traukinys",
        "tris", "truputi", "trys", "tu", "tuo", "tuoj", "tuomet", "tuos", "turbut", "tureciau", "turejau", "turejo",
        "turetu", "turetum", "turi", "turim", "turime", "turite", "turiu", "uostas", "uz", "uzsiciaupk", "vadinasi", "vaikai",
        "vaikas", "vaikinai", "vaikinas", "vaiku", "vakar", "vakaras", "vandens", "vanduo", "vardas", "vardu", "veikia", "vel",
        "veliau", "velnias", "velniu", "vien", "viena", "vienas", "vienintelis", "vieno", "viesbutis", "vieta", "vietoje", "vietos",
        "vis", "visa", "visada", "visai", "visas", "visi", "visiems", "visiskai", "viska", "viskas", "visko", "viso",
        "visos", "visu", "visus", "vos", "vyksta", "vyrai", "vyras", "yra", "zemes", "zinai", "zinau", "zino",
        "zinoma", "zinot", "zinote", "zinoti", "ziurek", "zmogau", "zmogaus", "zmogu", "zmogus", "zmona", "zmones", "zmoniu",
    },
    "lv": {
        "abi", "acis", "aiz", "aiziet", "aizveries", "ak", "ar", "ara", "ari", "asv", "ata", "atceries",
        "atgriezies", "atkal", "atpakal", "atradu", "atrak", "atrast", "atri", "atrodas", "atvaino", "atvainojiet", "augsa", "auto",
        "autobuss", "beidz", "beidzot", "berni", "berns", "bernu", "bet", "bez", "bija", "bijam", "biji", "bijis",
        "biju", "brauc", "bus", "busi", "busim", "busu", "but", "butu", "cau", "cauri", "cela", "celu",
        "cena", "ceru", "cik", "cilveki", "cilvekiem", "cilveks", "cilveku", "cilvekus", "citadi", "cits", "citu", "dabut",
        "dala", "dara", "darba", "darbs", "darbu", "dari", "darit", "daru", "daudz", "dazas", "dazi", "del",
        "dels", "diena", "dienas", "dienu", "dieva", "dievs", "diezgan", "divas", "divi", "dod", "dolaru", "doma",
        "domaju", "doties", "draugi", "draugs", "draugu", "drikstu", "driz", "drosi", "dross", "durvis", "dzek", "dzirdeju",
        "dzive", "dzives", "dzivi", "dzivibu", "dzivo", "dzivot", "dzivs", "ei", "ej", "ejam", "ejiet", "eju",
        "es", "esam", "esat", "esi", "esmu", "fib", "forsi", "gada", "gadi", "gadiem", "gadijuma", "gads",
        "gadu", "gadus", "gaida", "gala", "galds", "galvu", "gan", "gandriz", "garam", "gatavs", "gluzi", "grib",
        "gribat", "gribeja", "gribeju", "gribet", "gribetu", "gribi", "gribu", "gruti", "gruts", "hallo", "harij", "harvij",
        "hei", "ieksa", "ieksha", "iela", "ieroci", "iesim", "iespeja", "iespejams", "iet", "ilgi", "ir", "istaba",
        "isti", "it", "izbeidz", "izdarit", "izskatas", "izskaties", "ja", "jabut", "jadara", "jaiet", "jau", "jauki",
        "jauns", "jaunu", "jautajums", "jezin", "jo", "joprojam", "jums", "jus", "jusu", "ka", "kad", "kada",
        "kadam", "kadas", "kadel", "kadi", "kadreiz", "kads", "kadu", "kafija", "kam", "kamer", "kapec", "kartiba",
        "kas", "katru", "kaut", "klajas", "klat", "klau", "klausies", "ko", "kopa", "kops", "kreisi", "kresls",
        "kundze", "kungi", "kungs", "kur", "kura", "kuras", "kuri", "kurs", "kuru", "laba", "labak", "labakais",
        "labdien", "labi", "labrit", "labs", "labu", "labvakar", "lai", "laika", "laikam", "laiks", "laiku", "laipni",
        "lauj", "lauka", "leja", "lidosta", "lidz", "lidzi", "liec", "liekas", "liela", "lieliski", "liels", "lieta",
        "lietas", "lietu", "logs", "loti", "ludzu", "luk", "maize", "maja", "majas", "mamma", "mammu", "man",
        "mana", "manas", "mani", "manis", "mans", "manu", "manuprat", "masina", "masinu", "mate", "maz", "mazais",
        "mazak", "mazliet", "mazs", "meitene", "mekle", "mes", "miera", "mieru", "mila", "milais", "milu", "minutes",
        "miris", "mums", "mus", "musu", "nac", "naciet", "nak", "nakt", "nakti", "nakts", "naku", "nauda",
        "naudas", "naudu", "nav", "naves", "ne", "nebija", "nebus", "nebutu", "nedaudz", "nedomaju", "nedrikst", "neesam",
        "neesi", "neesmu", "negribu", "neka", "nekad", "nekadas", "nekadu", "nekas", "neko", "nem", "nemaz", "nepatik",
        "nesaprotu", "nespeju", "nevajag", "nevar", "nevaram", "nevari", "nevaru", "nevienam", "neviens", "nevienu", "nevis", "nezinaju",
        "nezinu", "nil", "no", "nogalinat", "noladets", "nopietni", "nost", "noteikti", "noticis", "notiek", "notika", "notiks",
        "nozime", "nu", "oho", "otru", "pa", "pagaidi", "pagaidiet", "paldies", "palidzet", "palidzi", "palidziba", "palidzibu",
        "paliec", "paliek", "palikt", "par", "parak", "parasti", "pareizi", "pari", "paris", "pasaki", "pasaule", "pasaules",
        "pasauli", "paskaties", "pasu", "pat", "pateikt", "pati", "patiesam", "patiesiba", "patik", "pats", "pec", "pedeja",
        "pie", "piedod", "piedodiet", "pietiek", "pietiekami", "pilnigi", "pilseta", "pirma", "pirmais", "pirmo", "pirms", "piter",
        "plans", "pret", "priecajos", "prieks", "prieksa", "prieksu", "problema", "prom", "protams", "puika", "puisi", "puisis",
        "pusi", "redzejis", "redzeju", "redzesanos", "redzet", "redzi", "redzu", "reiz", "reizi", "rit", "rita", "rits",
        "rokas", "roku", "runa", "runaju", "runat", "saja", "saka", "saki", "saku", "sapratu", "saproti", "saprotu",
        "sasodits", "satikt", "sauc", "sava", "savas", "savu", "savus", "seit", "sejienes", "sen", "ser", "sev",
        "sevi", "si", "sie", "sieva", "sieviete", "sievietes", "sievu", "sim", "sirds", "sis", "skaidrs", "skaista",
        "skaties", "skiet", "slikti", "slikts", "so", "sobrid", "sodien", "sovakar", "spej", "stacija", "starp", "strada",
        "stundas", "surp", "svarigi", "sveika", "sveiki", "sveiks", "ta", "tacu", "tad", "tada", "tadas", "tadel",
        "tads", "tadu", "tagad", "tai", "taisni", "taisniba", "taja", "talak", "talu", "tam", "tapat", "tapec",
        "tas", "tatad", "tava", "tavas", "tavs", "tavu", "te", "teica", "teici", "teicu", "teikt", "teja",
        "tet", "teti", "tetis", "tev", "tevi", "tevis", "tevs", "tie", "tiek", "tiem", "tiesam", "tiesi",
        "tik", "tika", "tikai", "tikko", "tiks", "tiksimies", "tikt", "to", "tomer", "tos", "tris", "tu",
        "tulit", "tur", "tuvu", "udens", "un", "uz", "uzmanibu", "uzmanigi", "vai", "vairak", "vairs", "vajadzeja",
        "vajadzetu", "vajadziga", "vajadzigs", "vajag", "vakar", "vala", "valsts", "var", "vara", "varam", "varat", "varbut",
        "vards", "vardu", "varetu", "vari", "varu", "vecit", "vecs", "vel", "velak", "velies", "velna", "velns",
        "velos", "velreiz", "velu", "viegli", "viegls", "vien", "viena", "vienalga", "vienigais", "vienkarsi", "vienmer", "viens",
        "vienu", "viesnica", "vieta", "vietas", "vietu", "vilciens", "vina", "vinai", "vinam", "vinas", "vini", "viniem",
        "vins", "vinu", "vinus", "virietis", "virs", "visa", "visas", "visi", "visiem", "vismaz", "vispar", "viss",
        "visu", "visus", "zel", "zem", "zemes", "zina", "zinaju", "zinam", "zinas", "zinat", "zini", "zinu",
    },
    "nl": {
        "aan", "achter", "af", "agent", "al", "alle", "alleen", "allemaal", "alles", "als", "alsjeblieft", "alsof",
        "alstublieft", "altijd", "ander", "andere", "anders", "auto", "avond", "baan", "baas", "baby", "bang", "bed",
        "bedankt", "bedoel", "beetje", "begin", "beginnen", "begrepen", "begrijp", "bel", "belangrijk", "bellen", "ben", "beneden",
        "bent", "best", "beste", "betekent", "beter", "bezig", "bij", "bijna", "binnen", "blij", "blijf", "blijft",
        "blijven", "bloed", "boven", "breng", "brengen", "broer", "brood", "buiten", "bus", "buurt", "daar", "daarom",
        "dacht", "dag", "dagen", "dan", "dank", "dat", "de", "deed", "deel", "denk", "denken", "denkt",
        "deur", "deze", "dezelfde", "dicht", "dichtbij", "die", "ding", "dingen", "dit", "dochter", "doden", "doe",
        "doen", "doet", "dokter", "dollar", "dood", "door", "dr", "drie", "drinken", "druk", "duidelijk", "dus",
        "echt", "echte", "een", "eens", "eerder", "eerlijk", "eerst", "eerste", "eigen", "eigenlijk", "elkaar", "elke",
        "en", "enige", "er", "eraan", "erg", "ergens", "erop", "eruit", "ervan", "eten", "even", "familie",
        "fijn", "foto", "fout", "ga", "gaan", "gaat", "gaf", "gebeurd", "gebeuren", "gebeurt", "gebruiken", "gebruikt",
        "gedaan", "geef", "geeft", "geen", "gehad", "gehoord", "gek", "gekomen", "geld", "geleden", "gelijk", "geloof",
        "geloven", "geluk", "gelukkig", "gemaakt", "genoeg", "geval", "geven", "gevonden", "geweest", "geweldig", "gewoon", "gezegd",
        "gezicht", "gezien", "ging", "gisteren", "god", "goed", "goede", "goedemiddag", "goedemorgen", "goedenacht", "goedenavond", "graag",
        "groot", "grote", "haal", "haar", "had", "hadden", "halen", "hallo", "hand", "handen", "hart", "he",
        "heb", "hebben", "hebt", "heeft", "heel", "heen", "heet", "hele", "helemaal", "help", "helpen", "hem",
        "hen", "het", "hetzelfde", "hey", "hield", "hier", "hij", "hoe", "hoeft", "hoeveel", "hoi", "hoofd",
        "hoop", "hoor", "hoorde", "hoort", "horen", "hotel", "hou", "houd", "houden", "houdt", "huis", "hulp",
        "hun", "idee", "ie", "iedereen", "iemand", "iets", "ik", "in", "inderdaad", "is", "ja", "jaar",
        "jaren", "je", "jezelf", "jij", "john", "jongen", "jongens", "jou", "jouw", "juist", "jullie", "kaart",
        "kamer", "kan", "kans", "kant", "keer", "ken", "kennen", "kent", "keuken", "kijk", "kijken", "kind",
        "kinderen", "klaar", "klein", "kleine", "klinkt", "klopt", "koffie", "kom", "komen", "komt", "kon", "kop",
        "kreeg", "krijg", "krijgen", "krijgt", "kun", "kunnen", "kunt", "kwam", "laat", "laatste", "land", "lang",
        "langs", "laten", "later", "lekker", "leren", "leuk", "leven", "lichaam", "liefde", "liet", "liggen", "ligt",
        "lijkt", "links", "lk", "lopen", "los", "luchthaven", "luister", "maak", "maakt", "maakte", "maanden", "maar",
        "mag", "maken", "makkelijk", "mam", "mama", "man", "manier", "mannen", "me", "mee", "meer", "meisje",
        "meneer", "mens", "mensen", "met", "meteen", "mevrouw", "mezelf", "mij", "mijn", "minder", "minuten", "mis",
        "misschien", "moeder", "moeilijk", "moest", "moet", "moeten", "mogelijk", "mogen", "moment", "mond", "mooi", "mooie",
        "moord", "morgen", "mr", "mrs", "na", "naam", "naar", "nacht", "natuurlijk", "nee", "neem", "neer",
        "nemen", "net", "niemand", "niet", "niets", "nieuw", "nieuwe", "nieuws", "niks", "nodig", "nog", "nooit",
        "nou", "nu", "nummer", "ochtend", "of", "ogen", "oh", "oke", "om", "omdat", "onder", "ons",
        "onze", "ooit", "ook", "oorlog", "op", "open", "orde", "oud", "oude", "ouders", "over", "paar",
        "pak", "pakken", "papa", "pardon", "pas", "per", "pijn", "plaats", "plan", "plek", "politie", "praat",
        "praten", "precies", "prijs", "prima", "probeer", "proberen", "probleem", "problemen", "raam", "rechtdoor", "rechts", "redden",
        "reden", "rekening", "rest", "rond", "rust", "rustig", "samen", "schat", "schiet", "school", "schuld", "sinds",
        "sir", "slapen", "slecht", "snap", "snel", "soms", "soort", "sorry", "spelen", "spijt", "spreek", "spreekt",
        "spreken", "sta", "staan", "staat", "stad", "station", "steeds", "stel", "sterven", "stoel", "stond", "stop",
        "stoppen", "straat", "tafel", "te", "team", "tegen", "telefoon", "terug", "terwijl", "the", "thee", "thuis",
        "tien", "tijd", "tijdens", "toch", "toe", "toen", "tot", "trein", "tussen", "twee", "u", "uit",
        "uur", "uw", "vaak", "vader", "vallen", "van", "vanavond", "vandaag", "vast", "veel", "veilig", "ver",
        "verder", "verdomme", "vergeet", "vergeten", "verhaal", "vermoord", "vermoorden", "vertel", "verteld", "vertelde", "vertellen", "vertrouwen",
        "vier", "vijf", "vind", "vinden", "vindt", "vlees", "voel", "voelt", "vol", "volgende", "volgens", "vond",
        "voor", "voorbij", "voordat", "vooruit", "vraag", "vragen", "vriend", "vrienden", "vriendin", "vrij", "vroeg", "vrouw",
        "vrouwen", "waar", "waarheid", "waarom", "waarschijnlijk", "wacht", "wachten", "wakker", "wanneer", "want", "wapen", "waren",
        "was", "wat", "water", "we", "week", "weer", "wees", "weet", "weg", "weinig", "weken", "wel",
        "welk", "welke", "werd", "wereld", "werk", "werken", "werkt", "weten", "wie", "wij", "wil", "wilde",
        "willen", "wilt", "wist", "word", "worden", "wordt", "wou", "zaak", "zag", "zaken", "zal", "zat",
        "ze", "zeer", "zeg", "zeggen", "zegt", "zei", "zeker", "zelf", "zelfs", "zes", "zet", "zetten",
        "zich", "zie", "zien", "ziens", "ziet", "zij", "zijn", "zit", "zitten", "zo", "zoals", "zodat",
        "zoek", "zoeken", "zoiets", "zonder", "zoon", "zorg", "zorgen", "zou", "zouden", "zoveel", "zullen", "zult",
    },
    "no": {
        "akkurat", "aldri", "alene", "all", "alle", "allerede", "alltid", "alt", "an", "andre", "annen", "annet",
        "apne", "ar", "at", "av", "ba", "bak", "bare", "barn", "barna", "be", "bedre", "begge",
        "begynne", "begynner", "begynte", "beklager", "ber", "best", "beste", "betyr", "bil", "bilen", "ble", "bli",
        "blir", "blitt", "bor", "bord", "bort", "borte", "bra", "brod", "bror", "broren", "bruke", "bruker",
        "bryr", "burde", "buss", "by", "byen", "bør", "da", "dag", "dagen", "dager", "darlig", "de",
        "deg", "del", "dem", "den", "denne", "der", "dere", "deres", "derfor", "det", "dette", "di",
        "din", "dine", "disse", "dit", "ditt", "dollar", "dor", "dra", "drar", "drepe", "dreper", "drept",
        "drepte", "driver", "dro", "du", "dø", "død", "døde", "dør", "egen", "egentlig", "ei", "ekte",
        "eller", "ellers", "elsker", "en", "enda", "eneste", "engang", "enn", "enna", "er", "et", "ett",
        "etter", "fa", "faen", "faktisk", "familie", "familien", "fant", "fantastisk", "far", "faren", "fast", "fatt",
        "feil", "fem", "ferdig", "fikk", "fin", "finne", "finner", "finnes", "fins", "fint", "fire", "flere",
        "flott", "flyplass", "folk", "for", "foran", "fordi", "forsiktig", "forstar", "fort", "fortalte", "fortell", "fortelle",
        "fortsatt", "fra", "fram", "fred", "fremdeles", "fri", "full", "funnet", "fyr", "fyren", "føler", "føles",
        "før", "først", "første", "ga", "gal", "galt", "gamle", "gammel", "gang", "gangen", "ganger", "ganske",
        "gar", "gate", "gatt", "gi", "gikk", "gir", "gitt", "gjennom", "gjerne", "gjor", "gjorde", "gjore",
        "gjort", "gjør", "gjøre", "glad", "glem", "god", "gode", "godt", "greit", "grunn", "gud", "gutt",
        "gutten", "gutter", "ha", "hadde", "hallo", "ham", "han", "handler", "hans", "haper", "har", "hater",
        "hatt", "hei", "hele", "heller", "helst", "helt", "helvete", "henne", "hennes", "hente", "her", "herfra",
        "herr", "herregud", "heter", "hit", "hjelp", "hjelpe", "hjelper", "hjem", "hjemme", "hodet", "hold", "holde",
        "holder", "holdt", "hos", "hotell", "hoyre", "hun", "hus", "huset", "husker", "hva", "hvem", "hver",
        "hverandre", "hvert", "hvilken", "hvis", "hvor", "hvordan", "hvorfor", "hyggelig", "hør", "høre", "hører", "høres",
        "hørt", "hørte", "i", "idag", "igar", "igjen", "ikke", "imorgen", "imot", "ingen", "ingenting", "inn",
        "inne", "ja", "jack", "jeg", "jenta", "jente", "jo", "jobb", "jobbe", "jobben", "jobber", "jobbet",
        "john", "jævla", "jøss", "kaffe", "kaller", "kan", "kanskje", "kaptein", "kjeft", "kjenner", "kjent", "kjokken",
        "kjære", "kjøpe", "kjøre", "kjører", "klar", "klare", "klarer", "klart", "kom", "komme", "kommer", "kommet",
        "kona", "kone", "kunne", "kunnet", "kveld", "kvinne", "kvinner", "la", "lage", "laget", "land", "landet",
        "lang", "langt", "lar", "legg", "legge", "lei", "lenge", "lenger", "lett", "leve", "lever", "ligger",
        "like", "liker", "lille", "lite", "liten", "litt", "liv", "livet", "lkke", "lover", "løp", "ma",
        "mamma", "man", "maneder", "mange", "mann", "mannen", "mat", "mate", "matte", "med", "meg", "mellom",
        "men", "mener", "menn", "menneske", "mennesker", "mens", "mer", "mest", "mi", "min", "mindre", "mine",
        "minutter", "miss", "mistet", "mitt", "mor", "moren", "morgen", "mot", "mr", "mulig", "mye", "møte",
        "na", "naer", "nar", "natt", "navn", "navnet", "ned", "nede", "nei", "neste", "nesten", "nettopp",
        "new", "noe", "noen", "nok", "ny", "nye", "nytt", "og", "ogsa", "ok", "om", "opp",
        "oppe", "ord", "orden", "oss", "over", "pa", "pappa", "par", "pass", "pengene", "penger", "plass",
        "pokker", "politiet", "pris", "problem", "problemer", "prøv", "prøvde", "prøve", "prøver", "redd", "redde", "resten",
        "rett", "riktig", "ring", "ringe", "ringer", "ringte", "ro", "rolig", "rom", "rommet", "rundt", "sa",
        "sagt", "saken", "samme", "sammen", "sann", "sannheten", "sant", "satt", "se", "seg", "seks", "selv",
        "selvfølgelig", "selvsagt", "senere", "sent", "ser", "ses", "sett", "sette", "setter", "si", "side", "siden",
        "sier", "sikker", "sikkert", "sin", "sine", "sir", "siste", "sitt", "sitter", "sjanse", "skal", "skje",
        "skjedd", "skjedde", "skjer", "skjønner", "skolen", "skulle", "skyld", "sla", "slags", "slapp", "slik", "slipp",
        "slutt", "snakk", "snakke", "snakker", "snakket", "snart", "snill", "som", "spille", "spiller", "spise", "spør",
        "spørre", "spørsmal", "sta", "star", "sted", "stedet", "stemmer", "stille", "stol", "stopp", "stor", "store",
        "stort", "straks", "stund", "synes", "syns", "sønn", "sønnen", "ta", "tak", "takk", "tar", "tatt",
        "te", "tenk", "tenke", "tenker", "tenkt", "tenkte", "the", "ti", "tid", "tiden", "tidlig", "tidligere",
        "til", "tilbake", "timer", "ting", "to", "tog", "tok", "tom", "tre", "treffe", "trenger", "tro",
        "trodde", "tror", "tur", "tusen", "uansett", "uke", "under", "unna", "unnskyld", "ut", "ute", "uten",
        "utenfor", "utrolig", "vaere", "vaert", "valg", "vann", "vanskelig", "vapen", "var", "vare", "vart", "ved",
        "vei", "veien", "vekk", "vel", "veldig", "velkommen", "venn", "vennen", "venner", "venstre", "vent", "vente",
        "venter", "verden", "vet", "vi", "videre", "viktig", "vil", "ville", "villet", "vindu", "virkelig", "virker",
        "vise", "visst", "visste", "vite", "vondt", "vær", "være", "vært", "ønske", "ønsker", "øyeblikk", "øynene",
    },
    "pl": {
        "aby", "albo", "ale", "ani", "autobus", "az", "badz", "bardziej", "bardzo", "beda", "bede", "bedzie",
        "bedziemy", "bedziesz", "bez", "blisko", "bo", "boze", "brat", "bron", "brzmi", "by", "byc", "byli",
        "bym", "bys", "był", "była", "byłam", "byłem", "byłes", "było", "byłoby", "były", "cała", "całe",
        "całkiem", "cały", "cena", "chca", "chce", "chcecie", "chcemy", "chcesz", "chciał", "chciałam", "chciałbym", "chciałem",
        "chciec", "chleb", "chodz", "chodzi", "chodzmy", "cholera", "chwile", "chwili", "chyba", "ci", "ciagle", "cie",
        "ciebie", "ciesze", "co", "cokolwiek", "cos", "coz", "czas", "czasu", "czego", "czegos", "czekaj", "czemu",
        "czesc", "czlowiek", "czuje", "czujesz", "czy", "czym", "człowiek", "da", "dac", "daj", "dalej", "daleko",
        "dam", "dla", "dlaczego", "dlatego", "dni", "dnia", "do", "dobra", "dobranoc", "dobre", "dobry", "dobrywieczor",
        "dobrze", "dokad", "dokładnie", "dom", "domu", "dopiero", "dopoki", "dosc", "drogi", "drzwi", "duzo", "duzy",
        "dwa", "dwie", "dwoch", "dworzec", "działa", "dzieci", "dziecko", "dzieje", "dzieki", "dziekuje", "dzien", "dziewczyna",
        "dziewczyny", "dzis", "dzisiaj", "długo", "ego", "facet", "gdy", "gdyby", "gdybym", "gdzie", "gdzies", "go",
        "gra", "halo", "hej", "herbata", "hotel", "i", "ich", "ida", "ide", "idz", "idzie", "idziecie",
        "idziemy", "idziesz", "ile", "im", "imie", "inaczej", "inne", "innego", "inny", "innych", "isc", "ja",
        "jak", "jakby", "jaki", "jakie", "jakies", "jakis", "jako", "jasne", "je", "jeden", "jedna", "jednak",
        "jednego", "jedno", "jednym", "jego", "jej", "jesli", "jest", "jestem", "jestes", "jestescie", "jestesmy", "jeszcze",
        "jezeli", "jutro", "juz", "karta", "kawa", "kazdy", "kazdym", "kiedy", "kiedys", "kilka", "kim", "kobieta",
        "kobiety", "kocham", "kochanie", "kogo", "kogos", "koncu", "koniec", "kraj", "krzeslo", "kto", "ktora", "ktore",
        "ktorego", "ktorej", "ktory", "ktorych", "ktorym", "ktorzy", "ktos", "kuchnia", "kurwa", "lat", "lata", "latwy",
        "lepiej", "lewo", "lotnisko", "lub", "lubie", "ludzi", "ludzie", "ma", "macie", "maja", "malo", "maly",
        "mam", "mama", "mamo", "mamy", "masz", "matka", "mały", "mezczyzna", "mi", "miasto", "miał", "miała",
        "miałam", "miałem", "miec", "miedzy", "miejsca", "miejsce", "miejscu", "minut", "miło", "miłosc", "mna", "mnie",
        "mniej", "moc", "moga", "moge", "mogł", "moich", "moim", "moj", "moja", "moje", "mojego", "mojej",
        "mow", "mowi", "mowia", "mowic", "mowie", "mowisz", "mowił", "mowiłem", "moze", "mozecie", "mozemy", "mozesz",
        "mozliwe", "mozna", "mu", "musi", "musiał", "musimy", "musisz", "musze", "my", "myslałam", "myslałem", "mysle",
        "mysli", "myslisz", "na", "nad", "nadal", "nadzieje", "najpierw", "nam", "nami", "naprawde", "nas", "nasz",
        "nasza", "nasze", "naszej", "nawet", "nia", "nic", "nich", "niczego", "nie", "niech", "niego", "niej",
        "nigdy", "nikogo", "nikt", "nim", "nimi", "niz", "no", "noc", "nocy", "nowy", "numer", "och",
        "oczy", "oczywiscie", "od", "ogole", "oh", "ojca", "ojciec", "ok", "okno", "on", "ona", "one",
        "oni", "ono", "oto", "pamietam", "pamietasz", "pan", "pana", "pani", "panie", "panu", "pare", "pewien",
        "pewna", "pewnie", "pewno", "pieniadze", "pieniedzy", "pierwszy", "po", "pociag", "pod", "podczas", "podoba", "pojde",
        "pojecia", "pokoj", "pokoju", "pomoc", "pomocy", "pomysł", "poniewaz", "porozmawiac", "porzadku", "posłuchaj", "potem", "potrzebuje",
        "powaznie", "powiedz", "powiedział", "powiedziała", "powiedziałem", "powiedziałes", "powiedziec", "powiem", "powiesz", "powinienem", "powinienes", "powinnismy",
        "powodu", "poza", "poznac", "pozniej", "pozwol", "prace", "pracy", "prawda", "prawde", "prawie", "prawo", "problem",
        "prosto", "prostu", "prosze", "przeciez", "przeciwko", "przed", "przepraszam", "przestan", "przez", "przy", "przykro", "przynajmniej",
        "pytanie", "rachunek", "racje", "rano", "raz", "razem", "razie", "razy", "rece", "robi", "robia", "robic",
        "robicie", "robie", "robimy", "robisz", "rok", "roku", "rowniez", "rozumiem", "rozumiesz", "rzecz", "rzeczy", "sa",
        "sadze", "sam", "sama", "samo", "samochod", "serce", "sie", "siebie", "siostra", "sir", "skad", "skoro",
        "smierc", "smierci", "soba", "sobie", "spojrz", "spokoj", "spokojnie", "sposob", "sprawa", "sprawe", "sprawy", "stad",
        "stanie", "stary", "stało", "stol", "super", "swiat", "swiecie", "swietnie", "swoich", "swoim", "swoj", "swoja",
        "swoje", "swojego", "swojej", "szybko", "słuchaj", "słyszałem", "ta", "tak", "taka", "taki", "takie", "takiego",
        "takim", "takze", "tam", "tata", "tato", "te", "tego", "tej", "telefon", "temu", "ten", "teraz",
        "tez", "the", "to", "toba", "tobie", "troche", "trudny", "trzeba", "trzy", "trzymaj", "tu", "tutaj",
        "twoim", "twoj", "twoja", "twoje", "twojego", "twojej", "ty", "tych", "tyle", "tylko", "tym", "tłumaczenie",
        "ulica", "w", "wam", "was", "wasz", "wazne", "wciaz", "wczesniej", "wczoraj", "we", "wez", "widze",
        "widzenia", "widzi", "widziałem", "widziec", "widzisz", "wie", "wiec", "wiecej", "wiecie", "wieczor", "wiedza", "wiedział",
        "wiedziałem", "wiedziec", "wiele", "wielu", "wiem", "wiemy", "wierze", "wiesz", "wina", "witam", "woda", "wrocic",
        "wszyscy", "wszystkich", "wszystkie", "wszystkim", "wszystko", "wtedy", "wy", "wybacz", "wydaje", "wyglada", "wygladasz", "wystarczy",
        "własciwie", "własnie", "z", "za", "zabic", "zadnych", "zamknij", "zanim", "zaraz", "zawsze", "zbyt", "ze",
        "zeby", "zebym", "zebys", "zle", "znaczy", "znalezc", "znam", "znasz", "znow", "znowu", "zobaczyc", "zona",
        "zostac", "został", "zrob", "zrobic", "zrobie", "zrobił", "zrobiłem", "zrobiłes", "zycia", "zycie", "zyciu", "zyje",
    },
    "pt": {
        "acabou", "acha", "achar", "achei", "acho", "acontecendo", "acontecer", "aconteceu", "acordo", "acredito", "adeus", "aeroporto",
        "agora", "agua", "ah", "ai", "ainda", "ajuda", "ajudar", "alem", "algo", "alguem", "algum", "alguma",
        "algumas", "alguns", "ali", "amanha", "amiga", "amigo", "amigos", "amo", "amor", "ano", "anos", "antes",
        "ao", "aos", "apenas", "aquela", "aquele", "aqui", "aquilo", "arma", "as", "assim", "ate", "atras",
        "baixo", "banheiro", "bastante", "bebe", "beber", "bem", "boa", "boca", "bom", "cabeca", "cada", "cadeira",
        "cafe", "cama", "caminho", "capitao", "cara", "carne", "carro", "cartao", "casa", "casamento", "caso", "causa",
        "certa", "certeza", "certo", "cerveja", "cha", "chance", "chefe", "chega", "chegar", "chegou", "cidade", "cima",
        "cinco", "claro", "coisa", "coisas", "com", "comecar", "comer", "comida", "comigo", "como", "comprar", "conhece",
        "conhecer", "conheco", "consegue", "conseguir", "conseguiu", "consigo", "conta", "contar", "contra", "conversar", "coracao", "corpo",
        "cozinha", "crianca", "criancas", "cuidado", "culpa", "da", "daqui", "dar", "das", "de", "deixa", "deixar",
        "deixe", "deixou", "dela", "dele", "deles", "demais", "dentro", "depois", "descobrir", "desculpe", "desde", "dessa",
        "desse", "desta", "deu", "deus", "deve", "devemos", "deveria", "devia", "devo", "dia", "diabos", "dias",
        "diferente", "dificil", "diga", "digo", "dinheiro", "direita", "direito", "direto", "disse", "disso", "diz", "dizem",
        "dizendo", "dizer", "do", "dois", "dormir", "dos", "droga", "duas", "durante", "e", "ei", "ela",
        "elas", "ele", "eles", "em", "embora", "encontrar", "enquanto", "entao", "entendo", "entrar", "entre", "equipe",
        "era", "eram", "errado", "escola", "espera", "esperando", "esperar", "espere", "espero", "esposa", "esquerda", "essa",
        "essas", "esse", "esses", "esta", "estacao", "estamos", "estao", "estar", "estas", "estava", "estavam", "este",
        "esteja", "estou", "estranho", "estudar", "eu", "exatamente", "faca", "facil", "faco", "fala", "falando", "falar",
        "falo", "falou", "falta", "familia", "faria", "favor", "faz", "fazem", "fazendo", "fazer", "feito", "feliz",
        "festa", "fez", "fica", "ficar", "ficou", "filha", "filho", "filhos", "fim", "final", "fique", "fiz",
        "foi", "for", "fora", "foram", "forma", "forte", "fosse", "frente", "fruta", "fui", "garota", "garoto",
        "gente", "gosta", "gostaria", "gosto", "grande", "guerra", "ha", "havia", "historia", "hoje", "homem", "homens",
        "hora", "horas", "hotel", "houve", "ia", "ideia", "idiota", "importa", "importante", "incrivel", "indo", "ir",
        "ira", "iria", "irma", "irmao", "isso", "isto", "ja", "janela", "jantar", "jeito", "jogo", "jovem",
        "juntos", "la", "lado", "legal", "lembra", "levar", "lhe", "licenca", "logo", "longe", "lugar", "mae",
        "maior", "mais", "mal", "mamae", "maneira", "manha", "mao", "maos", "marido", "mas", "matar", "matou",
        "mau", "me", "medo", "meio", "melhor", "menina", "menino", "menos", "merda", "mesa", "meses", "mesma",
        "mesmo", "meu", "meus", "mil", "mim", "minha", "minhas", "minuto", "minutos", "momento", "morrer", "morreu",
        "morte", "morto", "mudar", "muita", "muitas", "muito", "muitos", "mulher", "mulheres", "mundo", "musica", "na",
        "nada", "nao", "nas", "nem", "nenhum", "nenhuma", "nessa", "neste", "ninguem", "nisso", "no", "noite",
        "nome", "nos", "nossa", "nossas", "nosso", "nossos", "nova", "novamente", "novo", "num", "numa", "numero",
        "nunca", "obrigada", "obrigado", "oh", "oi", "ok", "ola", "olha", "olhe", "olhos", "onde", "onibus",
        "ontem", "os", "otimo", "ou", "outra", "outras", "outro", "outros", "ouvi", "ouvir", "pagar", "pai",
        "pais", "pao", "papai", "para", "parar", "pare", "parece", "parte", "passar", "pegar", "pegue", "pela",
        "pelo", "pensando", "pensar", "pensei", "pequeno", "perder", "pergunta", "perto", "pessoa", "pessoal", "pessoas", "plano",
        "pode", "podem", "podemos", "poder", "poderia", "podia", "pois", "policia", "por", "porem", "porque", "porra",
        "porta", "possa", "possivel", "posso", "pouco", "pra", "prazer", "precisa", "precisamos", "precisar", "preciso", "preco",
        "preocupe", "primeira", "primeiro", "problema", "problemas", "procurando", "pronto", "provavelmente", "proxima", "qual", "qualquer", "quando",
        "quanto", "quantos", "quarto", "quase", "quatro", "que", "quem", "quer", "querem", "querer", "queria", "querida",
        "querido", "quero", "quis", "quiser", "rapido", "razao", "realmente", "rua", "ruim", "sabe", "sabem", "sabemos",
        "saber", "sabia", "saia", "sair", "sala", "sangue", "sao", "se", "segundo", "seguranca", "sei", "seja",
        "sem", "semana", "sempre", "sendo", "senhor", "senhora", "sentir", "ser", "sera", "seria", "serio", "seu",
        "seus", "sido", "significa", "sim", "sinto", "so", "sobre", "somos", "sorte", "sou", "sozinho", "sua",
        "suas", "suficiente", "ta", "tal", "talvez", "tambem", "tanto", "tao", "tarde", "taxi", "tchau", "te",
        "telefone", "tem", "temos", "tempo", "tenha", "tenho", "tentando", "tentar", "ter", "tera", "teria", "terra",
        "teu", "teve", "the", "tinha", "tipo", "tirar", "tive", "tivesse", "toda", "todas", "todo", "todos",
        "tomar", "trabalhar", "trabalho", "tras", "trem", "tres", "trouxe", "tu", "tua", "tudo", "ultima", "ultimo",
        "um", "uma", "unica", "unico", "uns", "usar", "va", "vai", "vamos", "vao", "ve", "veem",
        "veio", "veja", "vejo", "velho", "vem", "venha", "venho", "ver", "verdade", "vez", "vezes", "vi",
        "vida", "vindo", "vinho", "vir", "viu", "viver", "vivo", "voce", "voces", "volta", "voltar", "vou",
    },
    "ro": {
        "acasa", "acea", "aceasta", "aceea", "acel", "acelasi", "acest", "acesta", "aceste", "acestea", "acolo", "acord",
        "acum", "adevarat", "adevarul", "adica", "aduc", "aduce", "adus", "aeroport", "afara", "aflat", "ai", "aia",
        "aici", "ajunge", "ajuns", "ajut", "ajuta", "ajutor", "al", "ala", "ale", "ales", "alo", "alt",
        "alta", "altceva", "alte", "altul", "am", "amandoi", "amintesc", "an", "ani", "apa", "apoi", "aproape",
        "ar", "arata", "are", "arma", "as", "asa", "asculta", "asemenea", "asta", "astazi", "astea", "asteapta",
        "astfel", "asupra", "atat", "ati", "atunci", "au", "aud", "autobuz", "auzi", "auzit", "avea", "aveam",
        "avem", "aveti", "avut", "azi", "ba", "baieti", "bani", "banii", "barbat", "bine", "bucur", "bun",
        "buna", "bune", "buni", "ca", "cafea", "cale", "cam", "camera", "cand", "cap", "capul", "care",
        "casa", "cat", "cate", "cateva", "cati", "catre", "cauza", "caz", "cazul", "ce", "cea", "ceai",
        "ceea", "cei", "cel", "cele", "cer", "cerut", "ceva", "chestia", "chiar", "cinci", "cine", "cineva",
        "ciudat", "conteaza", "copii", "copiii", "copil", "copilul", "corect", "cred", "crede", "credeam", "crezi", "crezut",
        "cu", "cum", "cumva", "cunosc", "cunoscut", "curand", "da", "daca", "dai", "dar", "dat", "data",
        "dau", "de", "decat", "deci", "deja", "deloc", "departe", "desigur", "despre", "destul", "devreme", "dimineata",
        "din", "dintre", "dl", "dle", "doamna", "doamne", "doar", "doi", "dolari", "domnul", "domnule", "doua",
        "dr", "dracu", "draga", "dreapta", "drept", "dreptate", "drum", "drumul", "duc", "duce", "duci", "dumnezeu",
        "dumnezeule", "dupa", "dus", "dvs", "e", "ea", "ei", "el", "ele", "era", "erai", "eram",
        "erau", "este", "esti", "eu", "exact", "exista", "fa", "fac", "faca", "face", "facem", "faceti",
        "faci", "facut", "familia", "familie", "fapt", "faptul", "fara", "fata", "fel", "femeie", "fereastra", "fericit",
        "fi", "fie", "fiecare", "fii", "fiica", "fiindca", "fiu", "fiul", "foarte", "fost", "frate", "fratele",
        "frumoasa", "frumos", "gand", "gandesc", "gandit", "gara", "gasesc", "gasi", "gasit", "gata", "greu", "grija",
        "griji", "grozav", "hai", "haide", "hei", "hotel", "ia", "iar", "iau", "idee", "iei", "ieri",
        "iesi", "ii", "il", "imediat", "imi", "important", "impotriva", "impreuna", "in", "inainte", "inapoi", "inca",
        "incearca", "incepe", "inceput", "incerc", "incercat", "incredere", "inima", "inseamna", "intampla", "intamplat", "inteleg", "intelegi",
        "inteles", "intoarce", "intorc", "intors", "intotdeauna", "intrat", "intre", "intreb", "isi", "iti", "iubesc", "jack",
        "joc", "john", "jos", "jumatate", "la", "langa", "las", "lasa", "lasat", "le", "legatura", "loc",
        "locul", "lor", "lua", "luat", "lucru", "lucruri", "lucrurile", "lui", "lume", "lumea", "luni", "ma",
        "macar", "mai", "maine", "mainile", "mama", "mana", "mare", "mari", "masa", "masina", "mea", "mei",
        "mele", "mereu", "merg", "merge", "mergem", "mergi", "mers", "mersi", "meu", "mi", "mic", "mica",
        "mie", "mine", "minte", "minunat", "minute", "moarte", "mod", "moment", "mort", "motiv", "mult", "multe",
        "multi", "multumesc", "munca", "murit", "naiba", "naibii", "ne", "nebun", "nevoie", "nici", "nicio", "niciodata",
        "niciun", "nimeni", "nimic", "niste", "noapte", "noaptea", "noastra", "noastre", "noi", "noroc", "nostru", "nou",
        "noua", "nu", "numai", "numarul", "nume", "numele", "oameni", "oamenii", "ochii", "odata", "oh", "ok",
        "om", "omul", "omule", "ora", "oras", "ore", "ori", "orice", "oricum", "pa", "pace", "pai",
        "paine", "pana", "parca", "pardon", "pare", "parte", "partea", "pasa", "patru", "pe", "pentru", "perfect",
        "persoana", "peste", "pic", "pierdut", "plac", "place", "pleaca", "plec", "pleca", "plecam", "plecat", "pleci",
        "poate", "poftim", "posibil", "pot", "poti", "prea", "pret", "prieten", "prieteni", "prietenul", "prima", "primit",
        "primul", "prin", "prins", "probabil", "problema", "probleme", "prost", "pui", "pun", "pune", "pus", "putea",
        "putem", "puteti", "putin", "putut", "rahat", "ramane", "ramas", "rau", "regula", "repede", "restul", "revedere",
        "rog", "sa", "salut", "sange", "sau", "scaun", "scuze", "se", "seama", "seara", "serios", "si",
        "sigur", "sigura", "siguranta", "simplu", "simt", "simti", "singur", "singura", "singurul", "sora", "sotia", "spate",
        "spatele", "sper", "spre", "spui", "spun", "spune", "spus", "sta", "stai", "stanga", "stau", "sti",
        "stiam", "stie", "stii", "stim", "stiti", "stiu", "strada", "sub", "sun", "suna", "sunat", "sunt",
        "suntem", "sunteti", "sus", "ta", "taci", "tai", "tale", "tara", "tare", "tarziu", "tata", "tatal",
        "tau", "te", "telefon", "terminat", "timp", "timpul", "tine", "tip", "tipul", "toata", "toate", "tocmai",
        "tot", "toti", "totul", "treaba", "trebui", "trebuia", "trebuie", "trebuit", "trecut", "trei", "tren", "trimis",
        "tu", "ucis", "uh", "uita", "uitat", "uite", "ultima", "un", "una", "unde", "undeva", "unei",
        "unui", "unul", "urma", "usa", "usor", "va", "vad", "vazut", "vechi", "vede", "vedea", "vedem",
        "vei", "veni", "venit", "veti", "vezi", "viata", "vii", "vin", "vina", "vine", "vino", "voi",
        "vom", "vor", "vorba", "vorbesc", "vorbesti", "vorbi", "vorbim", "vorbit", "vostru", "vrea", "vreau", "vrei",
        "vrem", "vreme", "vreo", "vreodata", "vreti", "vrut", "zi", "zic", "zici", "zile", "zis", "ziua",
    },
    "sk": {
        "a", "aby", "ach", "ahoj", "aj", "ak", "aka", "ake", "ako", "akoby", "aky", "ale",
        "alebo", "ani", "ano", "asi", "aspon", "auto", "autobus", "az", "bez", "blizko", "boh", "bol",
        "bola", "boli", "bolo", "boze", "brat", "bud", "bude", "budem", "budeme", "budes", "budete", "budu",
        "by", "byt", "caj", "cas", "casu", "cele", "celkom", "celu", "cely", "cena", "ceste", "cestu",
        "cez", "chapem", "chce", "chcel", "chcela", "chceli", "chcem", "chces", "chcete", "chciet", "chlap", "chlapci",
        "chlapec", "chlieb", "chod", "chvilu", "ci", "cim", "cislo", "citim", "clovece", "clovek", "co", "cokolvek",
        "com", "coze", "da", "daj", "dajte", "dakujem", "dal", "dalej", "daleko", "dalsi", "dam", "dat",
        "deje", "den", "deti", "dieta", "dievca", "dlho", "dnes", "dnu", "do", "dobra", "dobre", "dobru",
        "dobry", "dokonca", "doktor", "dole", "dom", "doma", "domov", "domu", "dost", "dostal", "dostat", "dovidenia",
        "dovod", "dufam", "dva", "dvaja", "dve", "dvere", "este", "fajn", "fakt", "halo", "hej", "hned",
        "ho", "hodin", "hore", "hotel", "hovori", "hovoril", "hovorim", "hovoris", "hovorit", "iba", "ich", "ide",
        "idem", "ideme", "ides", "im", "inak", "ine", "iny", "ist", "ista", "iste", "isty", "izba",
        "ja", "jasne", "je", "jeden", "jediny", "jedna", "jedneho", "jedno", "jednu", "jeho", "jej", "ju",
        "kam", "kapitan", "kava", "kazdy", "kde", "keby", "ked", "kedy", "koho", "kolko", "konecne", "koniec",
        "krajina", "kto", "ktora", "ktore", "ktori", "ktoru", "ktory", "ku", "kurva", "kvoli", "kym", "lahky",
        "lebo", "len", "lepsie", "letisko", "ludi", "ludia", "luto", "ma", "maju", "mal", "mala", "mali",
        "malo", "maly", "mam", "mama", "mame", "mami", "mas", "maso", "mat", "mate", "matka", "medzi",
        "menej", "meno", "mesto", "mi", "mieste", "miesto", "milujem", "minut", "mna", "mne", "mnou", "moc",
        "moct", "mohla", "mohli", "mohol", "moj", "moja", "moje", "mojej", "mojho", "mojich", "mojom", "moju",
        "moze", "mozem", "mozeme", "mozes", "mozete", "mozne", "mozno", "mrtvy", "mu", "musel", "musi", "musiet",
        "musim", "musime", "musis", "musite", "muz", "my", "myslel", "myslela", "myslim", "myslis", "myslite", "na",
        "nad", "najlepsie", "najst", "nam", "nami", "naozaj", "napad", "nas", "nasa", "nase", "nasiel", "nasli",
        "nebol", "nebola", "nebolo", "nebude", "nebudem", "nech", "nechaj", "nechat", "nechcem", "nechces", "neho", "nej",
        "nejake", "nejaky", "nema", "nemal", "nemam", "nemame", "nemas", "nemoze", "nemozem", "nemozeme", "nemozes", "nemyslim",
        "neskor", "neviem", "nez", "nic", "nich", "nie", "nieco", "niekde", "niekedy", "niekoho", "niekto", "nikdy",
        "nikto", "nim", "nimi", "no", "noc", "noci", "nom", "nou", "novy", "nu", "nuz", "och",
        "oci", "od", "odist", "odtialto", "oh", "ok", "okej", "okno", "okolo", "okrem", "on", "ona",
        "oni", "ono", "ony", "otca", "otec", "paci", "pan", "pane", "pani", "par", "pekla", "pekne",
        "peniaze", "po", "pocas", "pocit", "pockaj", "pockajte", "pockat", "pocul", "pocuvaj", "pod", "podla", "podme",
        "podte", "pohode", "pojdem", "pokial", "pomoc", "pomoct", "poriadku", "potom", "potrebuje", "potrebujem", "potrebujeme", "povedal",
        "povedala", "povedali", "povedat", "povedz", "poviem", "poznam", "pozor", "pozri", "pozriet", "pozrite", "praca", "prace",
        "pracu", "pravda", "pravdu", "prave", "pre", "prec", "preco", "pred", "predsa", "predtym", "prepac", "prepacte",
        "presne", "prestan", "preto", "pretoze", "pri", "priamo", "priatel", "pride", "pridem", "prilis", "pripade", "pripraveny",
        "prisiel", "prisla", "prisli", "prist", "problem", "problemy", "prosim", "proste", "proti", "prvy", "rad", "rada",
        "radsej", "rano", "raz", "riti", "robi", "robim", "robis", "robit", "robite", "rok", "rokov", "roky",
        "rovno", "rozumiem", "ruky", "rychlo", "s", "sa", "sakra", "sam", "sama", "samozrejme", "seba", "sebe",
        "sebou", "sem", "sestra", "si", "skor", "skoro", "skutocne", "skvele", "slecna", "sme", "so", "som",
        "spat", "spolu", "sposob", "spravil", "spravit", "spravne", "stale", "stalo", "stane", "stanica", "stary", "ste",
        "stol", "stolica", "su", "super", "svet", "svete", "svoj", "svoje", "svojej", "svojho", "svoju", "syn",
        "ta", "tak", "taka", "take", "takto", "taky", "takze", "tam", "tato", "tazke", "tazky", "teba",
        "tebe", "tebou", "teda", "tej", "tejto", "telo", "ten", "tento", "teraz", "the", "ti", "tie",
        "tieto", "tiez", "to", "toho", "tohto", "tolko", "tom", "tomto", "tomu", "toto", "tri", "trochu",
        "tu", "tuto", "tvoj", "tvoja", "tvoje", "tvojej", "tvoju", "ty", "tych", "tychto", "tym", "tyzden",
        "ucet", "uh", "ulica", "uplne", "urcite", "urobil", "urobit", "uvidime", "uz", "v", "vam", "vami",
        "vas", "vasa", "vase", "vazne", "vcera", "vdaka", "vec", "vecer", "veci", "ved", "vedel", "vediet",
        "vela", "velke", "velky", "velmi", "viac", "videl", "videla", "videli", "vidiet", "vidim", "vidis", "vie",
        "viem", "vieme", "vies", "viete", "vlak", "vlastne", "vlavo", "vo", "vobec", "voda", "vola", "von",
        "vonku", "vpravo", "vratit", "vsak", "vsetci", "vsetko", "vsetky", "vsetkych", "vtedy", "vy", "vyzera", "vzdy",
        "za", "zabil", "zabit", "zajtra", "zase", "zatial", "zbran", "zda", "ze", "zena", "zeny", "ziadne",
        "ziadny", "zit", "zivot", "zivota", "zlatko", "zlato", "zle", "znamena", "znie", "znova", "znovu", "zo",
    },
    "sl": {
        "adijo", "ali", "ampak", "avto", "avtobus", "bi", "bil", "bila", "bili", "bilo", "biti", "blizu",
        "bo", "bodi", "bodo", "bog", "bolj", "bolje", "bom", "bomo", "bos", "bosta", "boste", "bova",
        "brat", "brez", "caj", "cakaj", "cas", "casa", "ce", "celo", "cem", "cena", "ceprav", "cesa",
        "cez", "cisto", "clovek", "cudno", "da", "daj", "dajmo", "dal", "dala", "dalec", "dan", "danes",
        "dekle", "del", "dela", "delal", "delam", "delas", "delati", "delo", "denar", "denarja", "desno", "dni",
        "do", "dober", "dobil", "dobila", "dobili", "dobra", "dobro", "dogaja", "dokler", "dol", "dolarjev", "dolgo",
        "doma", "domov", "dovolj", "drug", "drugace", "druge", "drugega", "drugi", "drugo", "drzava", "drzi", "dva",
        "dve", "eden", "en", "ena", "enega", "enkrat", "eno", "fant", "fanta", "fantje", "ga", "glavo",
        "glede", "glej", "gor", "gospa", "gospod", "gotovo", "govori", "govoril", "govorila", "govorim", "govoris", "govoriti",
        "gre", "grem", "gremo", "gres", "greva", "halo", "hej", "hisa", "hiso", "hitro", "hoce", "hocem",
        "hoces", "hotel", "hotela", "hudica", "hvala", "ima", "imajo", "imam", "imamo", "imas", "imate", "ime",
        "imel", "imela", "imeli", "imeti", "in", "iti", "iz", "izgleda", "izgubil", "ja", "jack", "jasno",
        "jaz", "je", "ji", "jih", "jim", "jo", "ju", "jutri", "jutro", "kaj", "kajne", "kako",
        "kaksen", "kaksna", "kaksno", "kam", "kar", "karkoli", "kateri", "kava", "kdaj", "kdo", "ker", "ki",
        "kje", "kjer", "kmalu", "ko", "koga", "koliko", "konec", "kot", "kruh", "lahek", "lahko", "le",
        "lepa", "lepo", "let", "leta", "letalisce", "leti", "leto", "levo", "ljubica", "ljubim", "ljudi", "ljudje",
        "majhen", "malce", "malo", "mama", "mami", "mamo", "manj", "mano", "mati", "me", "med", "mene",
        "meni", "mesto", "mestu", "mi", "midva", "minut", "miru", "misli", "mislil", "mislila", "mislim", "mislis",
        "mislite", "miza", "moci", "mogel", "mogoce", "moj", "moja", "mojbog", "moje", "mojega", "moji", "mojo",
        "mora", "moral", "morala", "morali", "moram", "moramo", "moras", "morate", "morava", "morda", "more", "morem",
        "mores", "moski", "moz", "mrtev", "mu", "na", "nacin", "nad", "naj", "najbolj", "najbrz", "najprej",
        "najti", "naju", "nam", "nama", "nami", "naprej", "naravnost", "naredi", "naredil", "naredila", "narediti", "narobe",
        "nas", "nasa", "nase", "nasel", "nasla", "nasli", "nasvidenje", "nato", "nazaj", "ne", "nehaj", "nekaj",
        "nekdo", "nekoga", "ni", "nic", "nicesar", "nihce", "nikoli", "nima", "nimam", "nimas", "nisem", "nisi",
        "nismo", "niso", "niste", "nisva", "niti", "njega", "njegov", "njegova", "njegovo", "njen", "njih", "njihov",
        "njim", "njo", "no", "noc", "nocem", "nocoj", "noter", "notri", "nov", "novo", "ob", "oba",
        "obstaja", "oce", "oceta", "oci", "ocitno", "ocka", "od", "odlicno", "odsel", "oh", "ok", "okno",
        "okoli", "on", "ona", "one", "oni", "ono", "oprosti", "oprostite", "orozje", "otroci", "otrok", "otroka",
        "pa", "pazi", "pet", "po", "pocakaj", "pocasi", "pocnes", "pod", "poglej", "pojdi", "poklical", "pol",
        "pomagal", "pomagam", "pomagati", "pomembno", "pomeni", "pomoc", "poslusaj", "postaja", "pot", "potem", "poti", "potrebujem",
        "povedal", "povedala", "povedati", "povej", "povem", "pozabi", "poznam", "poznas", "prav", "pravi", "pravis", "pravkar",
        "pravzaprav", "precej", "pred", "preden", "prej", "prekleto", "preprican", "prevec", "pri", "pride", "pridem", "pridi",
        "prihaja", "prijatelj", "prijatelja", "priloznost", "primer", "pripravljen", "prisel", "prisla", "prisli", "priti", "prosim", "proti",
        "prvi", "prvic", "pusti", "pustil", "rad", "rada", "radi", "raje", "ravno", "razen", "razumem", "razumes",
        "recem", "reci", "redu", "rekel", "rekla", "rekli", "res", "resnicno", "resno", "roke", "saj", "sam",
        "sama", "samo", "se", "sebi", "sedaj", "sef", "sel", "sem", "seveda", "si", "sin", "skoraj",
        "skozi", "skrbi", "skupaj", "sla", "slab", "slabo", "slisal", "slisala", "slo", "sluzbo", "smo", "smrt",
        "smrti", "so", "soba", "spet", "sploh", "spomnis", "sranje", "srce", "sreco", "sta", "star", "stari",
        "ste", "stiri", "stol", "storil", "stran", "strani", "stvar", "stvari", "super", "sva", "svet", "svetu",
        "svoj", "svoje", "svojega", "svojo", "ta", "tabo", "tak", "takega", "tako", "takoj", "takrat", "tam",
        "te", "tebe", "tebi", "teden", "tega", "teh", "tej", "tem", "temu", "tezave", "tezek", "tezko",
        "ti", "tip", "tisti", "tisto", "tja", "to", "tocno", "toda", "tole", "toliko", "torej", "treba",
        "trenutek", "tri", "tu", "tudi", "tukaj", "tvoj", "tvoja", "tvoje", "tvojega", "tvoji", "tvojo", "ubil",
        "ubiti", "ulica", "umrl", "upam", "uspelo", "v", "vaju", "vam", "vami", "vas", "vasa", "vase",
        "vcasih", "vceraj", "ve", "vec", "vecer", "vedel", "vedela", "vedeti", "vedno", "velik", "veliko", "vem",
        "vemo", "ven", "vendar", "verjamem", "verjeti", "verjetno", "ves", "veste", "vi", "videl", "videla", "videli",
        "videti", "vidim", "vidis", "vlak", "voda", "vprasanje", "vraga", "vrata", "vrnil", "vsaj", "vsak", "vse",
        "vsec", "vseeno", "vseh", "vsem", "vsi", "vzel", "vzemi", "z", "za", "zakaj", "zal", "zame",
        "zanima", "zaradi", "zate", "zato", "zdaj", "zdi", "zdravo", "ze", "zelel", "zeli", "zelim", "zelis",
        "zelo", "zena", "zenska", "zenske", "zgodilo", "zivi", "zivijo", "zivjo", "zivljenja", "zivljenje", "zjutraj", "zunaj",
    },
    "sq": {
        "aeroport", "afer", "ah", "ai", "ajo", "akoma", "alo", "ana", "apo", "aq", "ardhur", "arme",
        "arsye", "as", "asaj", "asgje", "ashtu", "askush", "asnje", "ata", "ate", "atehere", "atij", "atje",
        "ato", "aty", "atyre", "autobus", "baba", "babai", "babi", "bashke", "bashku", "be", "behet", "bej",
        "beja", "beje", "bejme", "bejne", "ben", "bene", "beni", "bera", "bere", "beri", "besh", "besoj",
        "bir", "bote", "brenda", "budalla", "buke", "bukur", "burg", "burre", "ca", "caj", "cdo", "cfare",
        "cila", "cilen", "cili", "cka", "cmendur", "cmim", "cuditshme", "dakord", "dakort", "dal", "dale", "dalim",
        "dashur", "dashuri", "degjo", "degjoj", "degjon", "degjoni", "degjuar", "dere", "deren", "deri", "derisa", "deshiron",
        "dhe", "dhene", "dhome", "dhomen", "di", "dicka", "dija", "dike", "diku", "dikush", "dil", "dime",
        "din", "dini", "disa", "dite", "diten", "djale", "djali", "djalosh", "djathtas", "dje", "djema", "do",
        "doja", "doktor", "dollare", "doni", "donte", "dore", "dot", "drejt", "drejte", "dreq", "dreqi", "dreqin",
        "dritare", "dua", "duam", "duan", "duart", "duhej", "duhen", "duhet", "duke", "dukesh", "duket", "dy",
        "dyte", "e", "ec", "edhe", "ej", "eja", "ejani", "emri", "emrin", "ende", "epo", "erdha",
        "erdhi", "eshte", "fakt", "fal", "faleminderit", "falni", "fare", "fat", "femije", "femijet", "fjale", "fjalen",
        "flas", "flasim", "flet", "folur", "forte", "frike", "fund", "fundit", "gabim", "gabuar", "gati", "gjalle",
        "gjate", "gje", "gjej", "gjeja", "gjejme", "gjera", "gjerat", "gjeta", "gjetur", "gjitha", "gjithashtu", "gjithcka",
        "gjithe", "gjithmone", "grua", "gruaja", "ha", "hajde", "hape", "hapur", "he", "hej", "here", "hotel",
        "humbur", "ia", "ide", "idiot", "ik", "iki", "ikim", "im", "ime", "imi", "intereson", "isha",
        "ishe", "ishim", "ishin", "ishte", "iu", "ja", "jam", "jane", "jap", "jashte", "jave", "je",
        "jem", "jemi", "jene", "jeni", "jep", "jepi", "jesh", "jeta", "jete", "jeten", "jetes", "jo",
        "jone", "jote", "ju", "juaj", "ka", "kafe", "kaluar", "kam", "kane", "kaq", "karrige", "kater",
        "ke", "kem", "kemi", "keni", "keq", "keqe", "kerkoj", "kerkon", "kerkuar", "kesaj", "kesh", "keshtu",
        "keta", "kete", "ketej", "keto", "ketu", "kisha", "kishe", "kishim", "kishin", "kishte", "kjo", "koha",
        "kohe", "kohen", "koken", "kthehem", "kthehet", "kthehu", "kthyer", "ku", "kujdes", "kujtohet", "kunder", "kuptoj",
        "kupton", "kuptova", "kur", "kurre", "kush", "ky", "larg", "largohu", "lart", "larte", "le", "lehte",
        "lene", "ler", "lere", "leviz", "lidhje", "lire", "lloj", "lumtur", "lutem", "ma", "madh", "madhe",
        "majtas", "makina", "makine", "makinen", "mallkuar", "mami", "marr", "marre", "marresh", "marrim", "mbaj", "mbaje",
        "mban", "mbase", "mbi", "mbrapa", "mbylle", "me", "meje", "mend", "mendoj", "mendoja", "mendon", "mendoni",
        "mendova", "menduar", "mengjes", "menjehere", "menyre", "merr", "merre", "merrni", "mes", "mi", "mia", "mik",
        "miku", "minuta", "minute", "mira", "mire", "miredita", "mirembrema", "miremengjes", "mirupafshim", "mjaft", "moment", "mora",
        "more", "mori", "mos", "mrekullueshme", "mu", "mua", "muaj", "mund", "mundem", "mundesh", "mundesi", "mundur",
        "na", "nate", "naten", "ndalo", "ndihme", "ndihmoj", "ndodh", "ndodhe", "ndodhi", "ndodhur", "ndonje", "ndonjehere",
        "ndoshta", "ndryshe", "ne", "nen", "nena", "nene", "neper", "nese", "neser", "nesh", "nevoje", "nga",
        "nje", "njeh", "njerez", "njerezit", "njerezve", "njeri", "njeriu", "njoh", "njohur", "nuk", "oh", "ok",
        "ore", "ose", "pa", "pak", "para", "parate", "pare", "pari", "pas", "pashe", "pasi", "pastaj",
        "pasur", "pelqen", "per", "perpara", "perse", "perseri", "pershendetje", "pese", "pjese", "plako", "po", "policia",
        "por", "poshte", "pra", "prandaj", "prapa", "prej", "pres", "prisni", "prit", "problem", "problemi", "pse",
        "puna", "pune", "punen", "punon", "pyes", "pyetje", "qarte", "qe", "qendro", "qene", "qete", "qetesohu",
        "qofte", "qytet", "re", "rendesi", "rendesishme", "ri", "rregull", "rreth", "rri", "rruge", "rrugen", "sa",
        "saj", "sakte", "sapo", "se", "sepse", "seriozisht", "sheh", "shihemi", "shiko", "shikoj", "shikoje", "shikon",
        "shikoni", "shkak", "shko", "shkoi", "shkoj", "shkoje", "shkojme", "shkon", "shkoni", "shkosh", "shkuar", "shoh",
        "shohesh", "shohim", "shoku", "shpejt", "shpejte", "shpirt", "shpresoj", "shtepi", "shtepia", "shtepine", "shtet", "shume",
        "si", "sic", "sigurisht", "sigurt", "sigurte", "sikur", "sime", "sjell", "sonte", "sot", "stacion", "sy",
        "syte", "ta", "tani", "tashme", "tavoline", "te", "teje", "tek", "tend", "tende", "teper", "tere",
        "tha", "thashe", "the", "them", "thene", "thjesht", "thjeshte", "thone", "thoni", "thote", "thua", "thuaj",
        "thuash", "ti", "tij", "tille", "tim", "time", "tjera", "tjere", "tjeret", "tjeter", "tona", "tone",
        "tre", "trego", "tregoj", "tren", "tu", "tua", "tuaj", "tuaja", "tung", "ty", "tyre", "uh",
        "uje", "ulu", "une", "vajza", "vajze", "vajzen", "vazhdo", "vdekur", "vdes", "vdiq", "ve", "vella",
        "vend", "vendi", "vendin", "vene", "vertet", "vertete", "vesh", "veshtire", "vete", "vetem", "veten", "vij",
        "vije", "vijne", "vish", "vit", "vite", "vjen", "vjet", "vjeter", "vogel", "vone", "vrare", "vras",
        "yne", "yni", "yt", "yti", "zemer", "zgjuar", "zonja", "zonje", "zot", "zoteri", "zoti", "zotit",
    },
    "sv": {
        "adjo", "ah", "aka", "aker", "aldrig", "all", "alla", "alls", "allt", "alltid", "alltsa", "alskar",
        "alskling", "an", "anda", "andra", "annan", "annars", "annat", "annu", "antar", "anvanda", "ar", "arg",
        "at", "ata", "att", "av", "aven", "bad", "bada", "bakom", "bara", "barn", "bast", "basta",
        "battre", "be", "behovde", "behover", "ben", "ber", "beratta", "berattade", "betala", "betyder", "bil", "bilen",
        "blev", "bli", "blir", "blivit", "blod", "bor", "bord", "borde", "borja", "borjade", "borjar", "bort",
        "borta", "bra", "brod", "bror", "bryr", "buss", "chans", "da", "dag", "dagar", "dagen", "dags",
        "dalig", "daligt", "dar", "darfor", "de", "del", "dem", "den", "denna", "deras", "dessa", "det",
        "detta", "dig", "din", "dina", "direkt", "dit", "ditt", "do", "dod", "doda", "dodade", "dodar",
        "dog", "dollar", "dom", "dor", "dorr", "dorren", "dotter", "dr", "dra", "du", "efter", "eftersom",
        "egen", "eller", "emot", "en", "enda", "ens", "ensam", "er", "era", "ert", "ett", "fa",
        "faktiskt", "fall", "familj", "fan", "fanns", "far", "fara", "fast", "fatt", "fattar", "fel", "fem",
        "fick", "fin", "finns", "fint", "fler", "flera", "flicka", "flygplats", "flytta", "folja", "foljer", "folk",
        "fonster", "for", "foraldrar", "fore", "forlat", "forsok", "forsoka", "forsoker", "forsokte", "forst", "forsta", "forstar",
        "fort", "fortfarande", "fortsatt", "forut", "fraga", "fram", "fran", "fru", "fyra", "ga", "galen", "galler",
        "gamla", "gammal", "gang", "gangen", "ganger", "ganska", "gar", "garna", "gata", "gatt", "gav", "ge",
        "genom", "ger", "gick", "gillar", "gjorde", "gjort", "glad", "glom", "god", "gor", "gora", "gott",
        "gud", "ha", "hade", "haft", "hall", "halla", "haller", "hamta", "han", "hand", "hande", "hander",
        "handlar", "hans", "hant", "har", "harifran", "hatar", "hej", "hejda", "hela", "heller", "helst", "helt",
        "helvete", "hem", "hemma", "henne", "hennes", "herr", "herregud", "heter", "hit", "hitta", "hittade", "hittar",
        "hittat", "hjalp", "hjalpa", "hjalper", "hoger", "hon", "honom", "hoppas", "hor", "hora", "horde", "hort",
        "hos", "hotell", "hur", "hus", "huset", "huvudet", "i", "ibland", "idag", "ide", "ifran", "igar",
        "igen", "igenom", "ihag", "ihop", "ikvall", "illa", "imorgon", "in", "inga", "ingen", "ingenting", "inget",
        "innan", "inne", "inte", "ivag", "ja", "jack", "jag", "jasa", "javla", "jo", "jobb", "jobba",
        "jobbar", "jobbet", "john", "ju", "just", "kaffe", "kalla", "kallar", "kan", "kande", "kanna", "kanner",
        "kanns", "kanske", "kapten", "karlek", "killar", "kille", "killen", "klar", "klara", "klarar", "klart", "klockan",
        "kok", "kolla", "kom", "komma", "kommer", "kommit", "kor", "kora", "kul", "kunde", "kunna", "kunnat",
        "kvall", "kvar", "kvinna", "kvinnor", "lagg", "lamna", "lamnade", "lamnar", "land", "lang", "lange", "langre",
        "langt", "lar", "lara", "lat", "lata", "later", "latt", "ledsen", "letar", "leva", "lever", "ligger",
        "lika", "lilla", "lita", "lite", "liten", "liv", "livet", "lovar", "lugn", "lugnt", "lyssna", "mamma",
        "man", "manader", "manga", "mannen", "manniska", "manniskor", "mar", "maste", "mat", "med", "medan", "mellan",
        "men", "menar", "mer", "mest", "mig", "min", "mina", "mindre", "minns", "minuter", "miss", "mitt",
        "mor", "morgon", "mot", "mr", "mrs", "mycket", "nagon", "nagot", "nagra", "namn", "nan", "nar",
        "nara", "nasta", "nastan", "nat", "natt", "natten", "nej", "ner", "nere", "new", "ni", "nog",
        "nu", "ny", "nya", "nytt", "och", "ocksa", "okej", "om", "onskar", "ont", "oppna", "ord",
        "oroa", "oss", "over", "pa", "pappa", "par", "pengar", "pengarna", "perfekt", "plan", "plats", "polisen",
        "prata", "pratade", "pratar", "precis", "pris", "problem", "racker", "radd", "radda", "rakt", "ratt", "reda",
        "redan", "redo", "riktigt", "ring", "ringa", "ringde", "ringer", "roligt", "roll", "ror", "rum", "runt",
        "sa", "sag", "saga", "sager", "sagt", "sak", "saker", "sakert", "samma", "san", "sanningen", "sant",
        "satt", "satta", "se", "sedan", "sen", "senare", "sent", "ser", "ses", "sett", "sex", "sidan",
        "sig", "sin", "sina", "sir", "sista", "sitt", "sitter", "sjalv", "sjalvklart", "ska", "skicka", "skit",
        "skolan", "skull", "skulle", "skynda", "sla", "slapp", "slut", "sluta", "snalla", "snart", "som", "son",
        "spela", "spelar", "sta", "stad", "stallet", "stammer", "stan", "stanna", "stannar", "star", "stol", "stoppa",
        "stor", "stora", "stort", "svar", "svart", "syster", "ta", "tack", "tag", "tagit", "tala", "talar",
        "tank", "tanka", "tanker", "tankte", "tar", "te", "the", "tid", "tiden", "tidigare", "till", "tillbaka",
        "tills", "tillsammans", "timmar", "tio", "titta", "tjej", "tog", "traffa", "tre", "trevligt", "tro", "trodde",
        "tror", "tur", "tva", "tycker", "tyst", "undan", "under", "upp", "uppe", "ur", "ursakt", "ursakta",
        "ut", "utan", "utanfor", "ute", "va", "vacker", "vad", "vada", "vag", "vagen", "val", "valdigt",
        "van", "vanner", "vanster", "vanta", "vantar", "vapen", "var", "vara", "varandra", "varfor", "varit", "varje",
        "varld", "varlden", "vart", "vatten", "velat", "vem", "verkar", "verkligen", "vet", "veta", "vi", "vid",
        "vidare", "viktigt", "vilja", "vilka", "vilken", "vilket", "vill", "ville", "visa", "visst", "visste", "vore",
    },
    "sw": {
        "acha", "afisa", "agizo", "ah", "aha", "ahadi", "aina", "ajabu", "akaenda", "akageuka", "akicheka", "akili",
        "akisema", "akizungumza", "alichukua", "alifanya", "aliiambia", "alijua", "alikufa", "alikuja", "alikutana", "alikuwa", "alisema", "alishinda",
        "alitaka", "alitoa", "aliuliza", "ama", "ambayo", "amini", "ana", "anacheka", "anajua", "anapata", "anapumua", "anasema",
        "anataka", "andika", "angalau", "angalia", "ardhi", "aren", "asali", "asante", "asubuhi", "au", "baada", "baadaye",
        "baadhi", "baba", "badala", "bado", "bahati", "bandari", "barabara", "baridi", "basi", "bei", "biashara", "bila",
        "binadamu", "binti", "bluu", "bora", "bosi", "bunduki", "bure", "busu", "busy", "bw", "bwana", "cha",
        "chagua", "chaguo", "chai", "chakula", "chama", "chini", "chochote", "chuki", "chumba", "dada", "daima", "dakika",
        "daktari", "damu", "darasa", "dau", "dhidi", "dirisha", "don", "dunia", "em", "enda", "endesha", "familia",
        "fanya", "fikiri", "fikiria", "filamu", "fulani", "funga", "furaha", "gani", "gari", "george", "giza", "ha",
        "habari", "hadithi", "hai", "haina", "haipaswi", "haiwezi", "haja", "hakika", "hakuna", "hakuwa", "hakuweza", "halisi",
        "hang", "hapa", "hapana", "hapo", "haraka", "harusi", "hasa", "hasn", "hata", "hatimaye", "hatua", "hawakuwa",
        "haya", "hewa", "hii", "hisia", "historia", "hivi", "hivyo", "hiyo", "hizo", "hmm", "hofu", "hoja",
        "hospitali", "hoteli", "huenda", "hufanya", "huja", "hujambo", "hutokea", "ijayo", "ikiwa", "ilianza", "ilifanya", "ilikuwa",
        "iliyopita", "imba", "imekuwa", "imetumwa", "imezimwa", "ina", "inachukua", "inahitajika", "inaonekana", "inaweza", "inawezekana", "inayojulikana",
        "ingawa", "ingekuwa", "ishara", "isipokuwa", "itakuwa", "jack", "jamani", "jambo", "jana", "jaribu", "jengo", "jibu",
        "jicho", "jifunze", "jimbo", "jina", "jinsi", "jioni", "john", "jua", "jumla", "juu", "kabisa", "kabla",
        "kahawa", "kaka", "kama", "kamili", "kampuni", "kamwe", "karibu", "karibuni", "kata", "kati", "katika", "kazi",
        "kesho", "kesi", "kichaa", "kichwa", "kidogo", "kifo", "kijana", "kila", "kilichotokea", "kimya", "kinywaji", "kipande",
        "kitabu", "kitanda", "kitendo", "kiti", "kitu", "kituo", "kosa", "krismasi", "kuamka", "kuamua", "kuangalia", "kuanguka",
        "kuanza", "kubwa", "kuchekesha", "kucheza", "kuchukua", "kuchukuliwa", "kudhaniwa", "kudhibiti", "kuelewa", "kueleza", "kufa", "kufanya",
        "kufanyika", "kufanywa", "kufikiri", "kufuata", "kugeuka", "kugusa", "kuhifadhiwa", "kuhisi", "kuhusu", "kuishi", "kuitwa", "kuja",
        "kujali", "kujaribu", "kujua", "kukaa", "kukamata", "kukamatwa", "kukimbia", "kukosa", "kukutana", "kula", "kulala", "kuleta",
        "kuletwa", "kulia", "kuliko", "kulipa", "kumaliza", "kumbuka", "kumi", "kumiliki", "kununua", "kuoa", "kuokoa", "kuona",
        "kuondoka", "kuonekana", "kupata", "kupatikana", "kupendwa", "kupewa", "kupigana", "kupita", "kupitia", "kupotea", "kupoteza", "kurudi",
        "kusahau", "kushinda", "kushoto", "kushuka", "kusikia", "kusimama", "kusonga", "kusubiri", "kutaka", "kutania", "kutengeneza", "kutisha",
        "kutoa", "kutoka", "kutokea", "kutosha", "kutumia", "kutumika", "kutupa", "kuua", "kuuawa", "kuuliza", "kuumiza", "kuuza",
        "kuvaa", "kuvunja", "kuwa", "kuwaambia", "kuweka", "kuzaliwa", "kuzimu", "kuzungumza", "kwa", "kwaheri", "kwanza", "kweli",
        "kwenda", "labda", "lakini", "lazima", "leo", "lini", "ma", "maalum", "maana", "mabadiliko", "macho", "mahakama",
        "mahali", "mahitaji", "maisha", "maji", "makini", "mama", "mambo", "maneno", "mapema", "mapenzi", "mapumziko", "mara",
        "marafiki", "marehemu", "masaa", "mashambulizi", "maskini", "maswali", "matumaini", "mauaji", "maumivu", "mawazo", "mbali", "mbaya",
        "mbele", "mbili", "mbwa", "mchana", "mchezo", "mdomo", "meli", "mengi", "meza", "mfalme", "mfuko", "mfumo",
        "mgonjwa", "mh", "miaka", "michael", "miezi", "miguu", "mikono", "milele", "milioni", "mimi", "miss", "mji",
        "mjinga", "mjomba", "mke", "mkono", "mkutano", "mkuu", "mlango", "mmoja", "mna", "moja", "moto", "moyo",
        "mpaka", "mpango", "mpendwa", "mpenzi", "mpya", "mrembo", "msaada", "msichana", "mstari", "mtaani", "mtoto", "mtu",
        "muda", "muhimu", "mume", "mungu", "muziki", "mwaka", "mwana", "mwanamke", "mwanaume", "mwanga", "mwenyewe", "mwezi",
        "mwili", "mwingine", "mwisho", "mwitu", "mzee", "mzima", "na", "nadhani", "nafasi", "nahodha", "nambari", "nani",
        "nchi", "ndani", "ndefu", "ndege", "ndio", "ndiyo", "ndoa", "ndogo", "ndoto", "neno", "ngapi", "ngoma",
        "ngono", "ngumu", "nguo", "nguvu", "ni", "nimepata", "nina", "nini", "ninyi", "nita", "nje", "njia",
        "njoo", "nne", "nusu", "nyakati", "nyekundu", "nyeupe", "nyeusi", "nyingi", "nyingine", "nyuma", "nyumba", "nyumbani",
        "nywele", "nzuri", "ofisi", "oh", "ona", "ongea", "onyesha", "pale", "pamoja", "panda", "pande", "pata",
        "peke", "pekee", "pengine", "pesa", "pia", "picha", "piga", "pili", "polisi", "pumzika", "punda", "rafiki",
        "rahisi", "rais", "ripoti", "risasi", "saa", "saba", "sababu", "safi", "salama", "sam", "samahani", "samehe",
        "sana", "sasa", "sauti", "saw", "sawa", "sehemu", "sema", "serious", "shaka", "sheria", "shida", "shika",
        "shule", "si", "sikia", "sikiliza", "siku", "simu", "siri", "sisi", "sita", "sivyo", "soma", "subiri",
        "swali", "tafadhali", "tafuta", "taka", "takwimu", "tamani", "tamu", "tangu", "tano", "tarajia", "tarehe", "tatizo",
        "tatu", "tayari", "tazama", "tembea", "tena", "tengeneza", "thamani", "timu", "tofauti", "treni", "tu", "tuma",
        "tuna", "tuseme", "tv", "uaminifu", "uchafu", "uchovu", "udhuru", "uh", "uhakika", "ukweli", "uliza", "um",
        "umri", "una", "unataka", "unaweza", "uongo", "upande", "upendo", "usalama", "ushahidi", "usiku", "uso", "utulivu",
        "uwanja", "uwezo", "vibaya", "vijana", "vile", "vita", "vizuri", "vuta", "wa", "wachache", "wafu", "wakati",
        "wale", "walijaribu", "walikuwa", "waliona", "wamekwenda", "wana", "wanandoa", "wanaume", "wanawake", "wao", "wapi", "wasichana",
        "wasiwasi", "watoto", "watu", "waungwana", "wavulana", "wazazi", "wazi", "wazimu", "wazo", "weka", "wengi", "wengine",
        "wetu", "wewe", "weza", "wiki", "wimbo", "wito", "wow", "ya", "yake", "yako", "yangu", "yao",
        "yenu", "yesu", "yetu", "yeye", "yeyote", "yote", "yoyote", "zaidi", "zao", "zilizopita", "zote", "zungumza",
    },
    "tl": {
        "aalis", "abala", "ah", "ain", "akin", "aking", "aklat", "ako", "alam", "alin", "alinman", "am",
        "ama", "amin", "anak", "ang", "anim", "ano", "anuman", "apat", "apoy", "araw", "asahan", "asawa",
        "aso", "asong", "astig", "asul", "at", "atake", "ate", "ating", "ay", "ayaw", "ayos", "bababa",
        "babae", "baby", "bag", "bagaman", "bagay", "bago", "bahagi", "bahay", "baka", "bakit", "balita", "baliw",
        "bansa", "baril", "barilin", "barko", "basahin", "basta", "bata", "batang", "batas", "bawat", "bayan", "beses",
        "bibig", "bilang", "bilog", "binaril", "binigay", "bintana", "bit", "boses", "boss", "break", "buhay", "buhok",
        "bukas", "bumalik", "bumili", "buo", "bus", "buwan", "chuckles", "daan", "dahil", "dahilan", "dalawa", "dalhin",
        "damit", "dapat", "darating", "dati", "dating", "deal", "deretso", "digmaan", "din", "dinala", "dito", "diyan",
        "diyos", "doktor", "don", "doon", "drop", "dugo", "dumating", "ebidensya", "edad", "eh", "eksakto", "em",
        "espesyal", "estado", "fucking", "gabi", "gagawin", "gamitin", "ganap", "ganyan", "gawin", "george", "gilid", "ginagawa",
        "ginamit", "ginang", "ginawa", "ginoo", "gising", "gulo", "gumagalaw", "gumagana", "gumagawa", "gumalaw", "gumawa", "gupitin",
        "gusali", "gusto", "guys", "ha", "habang", "hakbang", "halika", "halikan", "halip", "halos", "hanapin", "handa",
        "hang", "hanggang", "hangin", "hapon", "hapunan", "harap", "hari", "hasn", "hawakan", "hayaan", "hello", "hesus",
        "hey", "hi", "higit", "hilahin", "hiling", "hindi", "hitsura", "hmm", "honey", "hotel", "huh", "hukuman",
        "hulaan", "huli", "humawak", "huminto", "iba", "ibig", "ideya", "ikaw", "ilagay", "ilalim", "ilan", "ilang",
        "iligtas", "impiyerno", "impormasyon", "ina", "ingat", "iniisip", "iningatan", "inumin", "ipadala", "ipaliwanag", "ipinadala", "ipinanganak",
        "isa", "isang", "isara", "isip", "isipin", "istasyon", "itaas", "itakda", "itapon", "itim", "ito", "iyo",
        "iyong", "jack", "john", "ka", "kaarawan", "kahapon", "kahit", "kahulugan", "kaibigan", "kailan", "kailangan", "kailanman",
        "kakaiba", "kakaunti", "kalahati", "kalimutan", "kaliwa", "kalmado", "kalokohan", "kalooban", "kalye", "kama", "kamatayan", "kamay",
        "kami", "kamusta", "kanan", "kanilang", "kanina", "kaniya", "kanlungan", "kanta", "kanya", "kanyang", "kapangyarihan", "kapatid",
        "kape", "kapitan", "karamihan", "kasal", "kasalanan", "kasama", "kasarian", "kasaysayan", "kasi", "kasinungalingan", "kaso", "katawan",
        "katotohanan", "kaunti", "kaya", "kayo", "kaysa", "kilala", "kinabukasan", "kinuha", "kita", "klase", "ko", "kontrol",
        "kotse", "kumain", "kumanta", "kumilos", "kumpanya", "kumusta", "kung", "kunin", "kunwari", "kurso", "kwarto", "kwento",
        "laban", "labas", "lahat", "lakad", "lalaki", "lamang", "lang", "larawan", "laro", "libre", "ligtas", "likod",
        "lima", "linggo", "linya", "liwanag", "ll", "loob", "lugar", "luma", "lumaban", "lumiko", "lumingon", "lungsod",
        "lupa", "lupain", "ma", "maaari", "maaaring", "maaga", "mababa", "mabait", "mabilis", "mabuhay", "mabuti", "madali",
        "madilim", "maganda", "magandang", "magbayad", "magbenta", "magbigay", "maghintay", "maging", "magkaiba", "magkano", "magkasama", "magkita",
        "maglaro", "magmadali", "magmaneho", "magpahinga", "magpakasal", "magpatawad", "magsalita", "magsulat", "magsuot", "magtanong", "magtiwala", "magulang",
        "mahaba", "mahal", "mahalaga", "mahirap", "mahuli", "mahusay", "mainit", "maintindihan", "makinig", "makuha", "malakas", "malaki",
        "malala", "malamang", "malamig", "malapit", "malayo", "mali", "maliban", "maligayang", "maliit", "malinaw", "malinis", "mamatay",
        "mamaya", "manalo", "manatili", "mangyari", "maniwala", "marahil", "marami", "maraming", "marinig", "mas", "masama", "masaya",
        "master", "maswerte", "masyadong", "mata", "mataas", "matagal", "matalo", "matamis", "matulog", "matuto", "mawala", "may",
        "mayroon", "medyo", "meron", "mesa", "mga", "michael", "milyon", "minamahal", "minsan", "minuto", "miss", "mo",
        "mr", "mukha", "mula", "muli", "mundo", "musika", "na", "nabubuhay", "nagbago", "nagbibiro", "nagbigay", "naghahanap",
        "naghihintay", "naging", "nagkakahalaga", "nagkaroon", "naglalaro", "nagpasya", "nagpunta", "nagsasabi", "nagsasalita", "nagsimula", "nagtanong", "nagtatanong",
        "nagtatrabaho", "nagtrabaho", "nahuli", "naintindihan", "nais", "naisip", "nakakakuha", "nakakamangha", "nakakatawa", "nakaraan", "nakikita", "nakilala",
        "nakita", "nakuha", "namatay", "namin", "nanalo", "nanay", "nangyari", "nangyayari", "nanonood", "napaka", "naramdaman", "narinig",
        "nasaktan", "natagpuan", "natatakot", "natin", "natutuwa", "nawala", "nawawala", "negosyo", "ng", "ngayon", "ngayong", "ngunit",
        "nila", "ninyo", "nito", "niya", "noon", "numero", "o", "off", "oh", "ok", "okay", "oo",
        "ooh", "opisina", "opisyal", "opo", "oras", "ospital", "pa", "paa", "paalam", "paano", "paaralan", "pababa",
        "pabalik", "pagbabago", "pagbibigay", "pagdating", "paggawa", "pagiging", "pagitan", "pagkahulog", "pagkain", "pagkakamali", "pagkakaroon", "pagkakataon",
        "pagkatapos", "pagkuha", "pagod", "pagpatay", "pagpili", "pagpupulong", "pagsisinungaling", "pagtataka", "pakiramdam", "pakiusap", "palabas", "palagi",
        "paligid", "paliparan", "palusot", "pamamagitan", "pamilya", "panatilihin", "pangako", "pangalan", "pangalawa", "pangangailangan", "pangangalaga", "pangarap",
        "panginoon", "pangkalahatan", "pangkat", "panoorin", "para", "paraan", "parang", "pare", "pareho", "party", "pasensya", "pasko",
        "pataas", "patawad", "patay", "pelikula", "pera", "pero", "perpekto", "petsa", "pigura", "pinakamahusay", "pinatay", "pinto",
        "pinuno", "piraso", "pito", "plano", "poot", "posible", "presidente", "presyo", "problema", "pula", "pulis", "pumasa",
        "pumatay", "pumili", "pumunta", "puno", "punta", "punto", "pupunta", "puso", "puti", "puwet", "pwede", "rin",
        "sa", "saan", "sabagay", "sabi", "sabihin", "sagot", "sakit", "salamat", "salita", "sam", "sampu", "sandali",
        "sapat", "sarili", "sariling", "sasakyan", "sayaw", "seguridad", "seryoso", "si", "sige", "sigurado", "siguro", "sikreto",
        "sila", "silid", "simulan", "sinabi", "sinadya", "sinasabi", "sinira", "sino", "sinta", "sinubukan", "sinusubukan", "sir",
        "sistema", "siya", "sobra", "sorry", "subukan", "sumakay", "sumpain", "sumunod", "suriin", "susunod", "swerte", "tae",
        "tahimik", "takot", "talaga", "tama", "tamaan", "tanda", "tandaan", "tanga", "tanong", "tao", "taon", "tapos",
        "tapusin", "tatay", "tatlo", "tawag", "taya", "tayo", "telepono", "tinapay", "tinawag", "tingnan", "tiyak", "tiyuhin",
        "totoo", "trabaho", "tren", "tubig", "tulong", "tumakbo", "tumatagal", "tumatakbo", "tumatawa", "tumatawag", "tumayo", "tumingin",
        "tungkol", "tunog", "tuwid", "tv", "ulat", "ulo", "um", "umaga", "umalis", "umupo", "una", "unahan",
        "upuan", "uri", "usapan", "utos", "wakas", "wala", "walang", "whoa", "wow",
    },
    "tr": {
        "ac", "acaba", "acik", "acık", "adam", "adamı", "adamım", "adamın", "adı", "adım", "ah", "aksam",
        "aksamlar", "al", "aldım", "almak", "alo", "altı", "altında", "ama", "aman", "an", "ancak", "anda",
        "anladım", "anlamiyorum", "anliyorum", "anlıyorum", "anne", "annem", "aptal", "ara", "araba", "arada", "arasında", "arkadas",
        "arkadasım", "artık", "asla", "aslında", "ates", "ay", "aynı", "ayrıca", "az", "azından", "baba", "babam",
        "bak", "bakalım", "bakmak", "bakın", "bana", "baska", "basladı", "basına", "bay", "bayan", "bazen", "bazı",
        "be", "bebegim", "bebek", "bekle", "belki", "ben", "bence", "bende", "benden", "beni", "benim", "benimle",
        "beraber", "beri", "bes", "bile", "bilet", "bilgisayar", "bilirsin", "biliyor", "biliyorsun", "biliyorum", "bilmiyorum", "bin",
        "bir", "biraz", "biri", "birini", "birisi", "birkac", "birlikte", "birsey", "bitti", "biz", "bize", "bizi",
        "bizim", "bos", "boyle", "boylece", "boyunca", "bu", "bugun", "buldum", "buna", "bundan", "bunlar", "bunları",
        "bunu", "bunun", "burada", "buradan", "burası", "buraya", "butun", "buyuk", "bırak", "cabuk", "calismak", "calısıyor",
        "calısıyorum", "canım", "cay", "cevap", "ceviri", "ciddi", "cikis", "cocugu", "cocuk", "cocuklar", "cok", "cunku",
        "cıktı", "da", "daha", "dakika", "dan", "de", "dedi", "dedim", "degil", "degildi", "degilim", "degilsin",
        "demek", "den", "dersin", "devam", "diger", "dikkat", "dilerim", "dinle", "diye", "dogru", "doktor", "dolar",
        "dort", "dostum", "dun", "dunya", "dur", "durak", "durum", "durumda", "dusundum", "dusunuyorsun", "dusunuyorum", "duydum",
        "duymak", "duz", "dısarı", "eczane", "eder", "ederim", "edin", "ediyor", "ediyorum", "efendim", "eger", "ekmek",
        "elbette", "emin", "eminim", "en", "erkek", "eski", "et", "etme", "etmek", "etti", "ettim", "ev",
        "evde", "eve", "evet", "fakat", "falan", "fark", "farklı", "fazla", "fiyat", "galiba", "garip", "gec",
        "gece", "geceler", "gecen", "gel", "geldi", "geldim", "geldin", "gelecek", "gelen", "gelip", "gelir", "geliyor",
        "gelmek", "genc", "gercek", "gercekten", "gerek", "gereken", "gerekiyor", "geri", "gibi", "gidelim", "gidip", "gidiyor",
        "gidiyorum", "giris", "git", "gitmek", "gitti", "gordum", "gordun", "gore", "gormek", "gorunuyor", "gorusuruz", "goz",
        "guclu", "gun", "gunaydin", "gunler", "gunu", "guzel", "ha", "haber", "hadi", "hafta", "hakkında", "haklısın",
        "hala", "halde", "hangi", "hangisi", "hareket", "harika", "hastane", "hatta", "hava", "havaalani", "hayal", "hayat",
        "hayatta", "hayatım", "haydi", "hayir", "hayır", "hazır", "hem", "hemen", "henuz", "hep", "hepimiz", "hepsi",
        "her", "herhangi", "herkes", "hesap", "hey", "hic", "hicbir", "hos", "hoscakal", "hızlı", "iceri", "icin",
        "icinde", "ihtiyacı", "ihtiyacım", "iki", "ile", "ileri", "ilgili", "ilk", "in", "insan", "insanlar", "is",
        "ise", "isi", "isin", "iste", "istedigim", "istedim", "istemiyorum", "ister", "istiyor", "istiyorsun", "istiyorum", "iyi",
        "izin", "jack", "john", "kabul", "kac", "kadar", "kadin", "kadın", "kahretsin", "kahve", "kal", "kaldı",
        "kan", "kapali", "kapi", "karar", "kardesim", "karsı", "kendi", "kendimi", "kendine", "kendini", "kes", "kesin",
        "kesinlikle", "kez", "ki", "kim", "kimin", "kimse", "kisi", "kitap", "kolay", "kontrol", "konuda", "konusmak",
        "konusunda", "kotu", "kucuk", "kız", "la", "lanet", "lazım", "le", "lutfen", "masa", "merak", "merhaba",
        "mi", "misin", "misiniz", "miyim", "miyiz", "mu", "muhtemelen", "mukemmel", "musun", "musunuz", "mutlu", "mı",
        "mısın", "nasil", "nasilsin", "nasilsiniz", "nasıl", "ne", "neden", "nedir", "nefret", "neler", "nerede", "nereden",
        "neredeyse", "nereye", "neyse", "nicin", "nin", "niye", "nun", "nın", "o", "oda", "oglum", "ogrenmek",
        "oh", "okul", "okumak", "ol", "olabilir", "olacagım", "olacagını", "olacak", "olamaz", "olan", "olarak", "olay",
        "oldu", "oldugu", "oldugumu", "olduguna", "oldugunu", "oldukca", "oldum", "olmadan", "olmadıgını", "olmak", "olmalı", "olması",
        "olmaz", "olmus", "olsa", "olsun", "olun", "olur", "olursa", "oluyor", "on", "ona", "once", "ondan",
        "onemli", "onlar", "onlara", "onlarin", "onları", "onların", "onu", "onun", "onunla", "orada", "oraya", "ortaya",
        "otel", "otobus", "oyle", "oyleyse", "ozel", "ozur", "para", "pek", "pekala", "peki", "pencere", "polis",
        "rahat", "saat", "sabah", "sadece", "sag", "sahip", "sakin", "sakın", "sana", "sandalye", "saniye", "sanki",
        "sanmıyorum", "sanırım", "savas", "sehir", "sekilde", "selam", "sen", "sence", "sende", "senden", "seni", "senin",
        "seninle", "seviyorum", "sey", "seye", "seyi", "seyin", "seyler", "seyleri", "silah", "simdi", "siz", "size",
        "sizi", "sizin", "sol", "son", "sonra", "sonunda", "soru", "sorun", "soyle", "soyledi", "soyledim", "soylemek",
        "soyluyor", "soz", "su", "sunu", "surada", "sure", "surekli", "suru", "ta", "tabi", "tabii", "takip",
        "taksi", "tam", "tamam", "tamamen", "tane", "tanrı", "tanrım", "tarafından", "tatlım", "tek", "tekrar", "telefon",
        "terk", "tesekkur", "tesekkurler", "tren", "tum", "uc", "ulke", "umarım", "un", "ustunde", "uzak", "uzerinde",
        "uzgunum", "uzun", "var", "vardı", "vardır", "vay", "ve", "ver", "verdi", "veya", "ya", "yakın",
        "yalan", "yalnız", "yani", "yanlıs", "yanında", "yap", "yapacagım", "yapma", "yapmak", "yaptı", "yaptıgını", "yaptım",
        "yaptın", "yapıyor", "yapıyorsun", "yardim", "yardım", "yardımcı", "yarin", "yarın", "yasamak", "yazmak", "ye", "yemek",
        "yeni", "yeniden", "yer", "yerde", "yere", "yerine", "yeter", "yi", "yine", "yok", "yoksa", "yoktu",
        "yol", "yolu", "yuzden", "yuzunden", "yı", "yıl", "zaman", "zamanı", "zaten", "zor", "zorunda", "ın",
    },
    "vi": {
        "ac", "ah", "ai", "am", "an", "and", "anh", "ao", "ay", "ba", "bac", "bai",
        "ban", "bang", "banh", "bao", "bat", "bay", "be", "ben", "benh", "bi", "bien", "biet",
        "bieu", "binh", "bo", "boi", "bom", "bon", "bong", "bua", "buc", "buoc", "buoi", "buon",
        "bus", "ca", "cac", "cach", "cai", "cam", "can", "cang", "canh", "cao", "cap", "cat",
        "cau", "cay", "ch", "cha", "chac", "cham", "chan", "chang", "chao", "chap", "chat", "chau",
        "chay", "che", "chet", "chi", "chia", "chiec", "chien", "chim", "chinh", "chiu", "cho", "choi",
        "chon", "chong", "chu", "chua", "chuan", "chuc", "chung", "chuong", "chup", "chut", "chuyen", "co",
        "coi", "con", "cong", "cu", "cua", "cuc", "cung", "cuoc", "cuoi", "cuon", "cuop", "cuu",
        "da", "dai", "dam", "dan", "danh", "dat", "dau", "day", "de", "dem", "den", "di",
        "dich", "dien", "diet", "dinh", "do", "doi", "don", "du", "dung", "duoc", "duoi", "duong",
        "duy", "em", "frank", "ga", "gai", "gan", "gang", "gap", "gay", "ghe", "ghet", "ghi",
        "gi", "gia", "giac", "giai", "giam", "gian", "giao", "giau", "giay", "giet", "gio", "gioi",
        "giong", "giu", "giua", "giuong", "giup", "goi", "gui", "ha", "hai", "han", "hang", "hanh",
        "hao", "hat", "hau", "hay", "he", "hen", "het", "hey", "hi", "hiem", "hien", "hieu",
        "hinh", "ho", "hoa", "hoac", "hoach", "hoan", "hoang", "hoat", "hoc", "hoi", "hom", "hon",
        "hong", "hop", "hua", "hung", "huong", "hut", "huu", "huy", "huynh", "hy", "ich", "im",
        "in", "it", "jack", "john", "ke", "keo", "ket", "kha", "khac", "khach", "khai", "khan",
        "khap", "khau", "khi", "khien", "kho", "khoa", "khoan", "khoang", "khoe", "khoi", "khon", "khong",
        "khu", "khung", "ki", "kia", "kich", "kiem", "kien", "kiep", "kieu", "kim", "kinh", "ko",
        "ky", "la", "lac", "lai", "lam", "lan", "lang", "lanh", "lao", "lap", "lau", "lay",
        "le", "len", "lenh", "li", "lich", "lien", "lieu", "linh", "lo", "loai", "loan", "loi",
        "lon", "long", "lop", "lu", "lua", "luat", "luc", "luon", "luong", "luu", "luyen", "ly",
        "ma", "mac", "mai", "man", "mang", "manh", "mat", "mau", "may", "me", "mi", "mieng",
        "minh", "mo", "moi", "mon", "mong", "mot", "mua", "muc", "mui", "mung", "muon", "my",
        "nam", "nan", "nang", "nao", "nay", "ne", "nen", "neu", "new", "ng", "ngac", "ngai",
        "ngan", "ngay", "nghe", "nghi", "nghia", "nghiem", "nghiep", "ngo", "ngoai", "ngoc", "ngoi", "ngon",
        "ngu", "ngua", "ngung", "nguoi", "nguon", "nguy", "nguyen", "nh", "nha", "nhac", "nhan", "nhanh",
        "nhap", "nhat", "nhau", "nhay", "nhe", "nhi", "nhiem", "nhien", "nhieu", "nhin", "nho", "nhoc",
        "nhom", "nhu", "nhung", "no", "noi", "nong", "nu", "nua", "nui", "nuoc", "o", "oh",
        "oi", "ok", "okay", "on", "ong", "pha", "phai", "pham", "phan", "phap", "phat", "phe",
        "phep", "phi", "phia", "phien", "phim", "pho", "phong", "phu", "phuc", "phuong", "phut", "qua",
        "quai", "quan", "quanh", "quay", "quen", "quoc", "quy", "quyen", "quyet", "ra", "rac", "rang",
        "rat", "rieng", "ro", "roi", "ruou", "rut", "sach", "sai", "san", "sang", "sao", "sap",
        "sat", "sau", "say", "se", "sep", "si", "sieu", "sinh", "so", "soat", "soc", "som",
        "song", "sot", "su", "sua", "suc", "sung", "suot", "suy", "ta", "tac", "tai", "tam",
        "tan", "tang", "tao", "tap", "tat", "tau", "tay", "te", "ten", "th", "tha", "thai",
        "tham", "than", "thang", "thanh", "that", "thay", "the", "them", "theo", "thi", "thich", "thien",
        "thiet", "thieu", "thit", "tho", "thoa", "thoai", "thoat", "thoi", "thong", "thu", "thua", "thuan",
        "thuat", "thuc", "thue", "thuoc", "thuong", "thuy", "thuyen", "thuyet", "ti", "tich", "tiec", "tien",
        "tieng", "tiep", "tiet", "tieu", "tim", "tin", "tinh", "to", "toa", "toan", "toc", "toi",
        "ton", "tong", "tot", "tra", "trach", "trai", "tran", "trang", "tranh", "tre", "tren", "tri",
        "trieu", "trinh", "tro", "troi", "trom", "tron", "trong", "tru", "truc", "trung", "truoc", "truong",
        "truy", "truyen", "tu", "tuan", "tuc", "tui", "tung", "tuoi", "tuong", "tuyet", "ty", "uh",
        "ung", "uoc", "uong", "va", "vai", "van", "vang", "vao", "vat", "vay", "ve", "vet",
        "vi", "viec", "vien", "viet", "vo", "voi", "vong", "vu", "vua", "vuc", "vui", "vung",
        "vuong", "vuot", "xa", "xac", "xanh", "xau", "xay", "xe", "xem", "xep", "xet", "xin",
        "xinh", "xong", "xu", "xuat", "xuc", "xuong", "yeah", "yen", "yeu", "you", "đa", "đac",
        "đai", "đam", "đan", "đang", "đanh", "đao", "đap", "đat", "đau", "đay", "đe", "đem",
        "đen", "đep", "đeu", "đi", "đia", "đich", "điem", "đien", "đieu", "đinh", "đo", "đoan",
        "đoc", "đoi", "đon", "đong", "đot", "đu", "đua", "đuc", "đung", "đuoc", "đuoi", "đuong",
    },
}

VOCAB_UNACCENTED = {lang: {normalize_unaccented(w) for w in words} for lang, words in RAW_VOCAB.items()}


def detect_text_language(text, hint_langs=None):
    """Detects primary language code from text using Unicode script, diacritics, and normalized unaccented vocabulary (offline, 0ms latency)."""
    if not text or not isinstance(text, str):
        return "en"

    clean_hints = set()
    if hint_langs:
        for h in hint_langs:
            if h:
                clean_hints.add(h.lower().split('-')[0])

    counts = defaultdict(int)
    latin_char_count = 0

    # 1. Check non-Latin Unicode blocks and explicit diacritics
    for ch in text:
        code = ord(ch)
        if 0x0E00 <= code <= 0x0E7F: counts["th"] += 2
        elif 0x0E80 <= code <= 0x0EFF: counts["lo"] += 2
        elif 0x1780 <= code <= 0x17FF: counts["km"] += 2
        elif 0x1000 <= code <= 0x109F: counts["my"] += 2
        elif 0x3040 <= code <= 0x30FF: counts["ja"] += 3
        elif (0xAC00 <= code <= 0xD7AF) or (0x1100 <= code <= 0x11FF) or (0x3130 <= code <= 0x318F): counts["ko"] += 3
        elif 0x4E00 <= code <= 0x9FFF: counts["zh-cn"] += 2
        elif (0x0600 <= code <= 0x06FF) or (0x0750 <= code <= 0x077F) or (0xFB50 <= code <= 0xFDFF):
            if "fa" in clean_hints: counts["fa"] += 2
            elif "ur" in clean_hints: counts["ur"] += 2
            elif "ug" in clean_hints: counts["ug"] += 2
            elif "ckb" in clean_hints: counts["ckb"] += 2
            elif "ps" in clean_hints: counts["ps"] += 2
            elif "sd" in clean_hints: counts["sd"] += 2
            else: counts["ar"] += 2
        elif (0x0400 <= code <= 0x04FF) or (0x0500 <= code <= 0x052F):
            if ch in "єіїґЄІЇҐ": counts["uk"] += 4
            elif ch in "ўЎ": counts["be"] += 4
            elif ch in "ђјљњћџ": counts["sr"] += 4
            elif ch in "ѓќѕ": counts["mk"] += 4
            elif ch in "ыэъЫЭЪ": counts["ru"] += 3
            else:
                if "uk" in clean_hints: counts["uk"] += 2
                elif "bg" in clean_hints: counts["bg"] += 2
                elif "sr" in clean_hints: counts["sr"] += 2
                elif "be" in clean_hints: counts["be"] += 2
                elif "mk" in clean_hints: counts["mk"] += 2
                elif "kk" in clean_hints: counts["kk"] += 2
                elif "ky" in clean_hints: counts["ky"] += 2
                elif "tg" in clean_hints: counts["tg"] += 2
                elif "mn" in clean_hints: counts["mn"] += 2
                elif "tt" in clean_hints: counts["tt"] += 2
                else: counts["ru"] += 2
        elif (0x0370 <= code <= 0x03FF) or (0x1F00 <= code <= 0x1FFF): counts["el"] += 2
        elif (0x0590 <= code <= 0x05FF) or (0xFB1D <= code <= 0xFB4F):
            if "yi" in clean_hints: counts["yi"] += 2
            else: counts["he"] += 2
        elif 0x0900 <= code <= 0x097F:
            if "mr" in clean_hints: counts["mr"] += 2
            elif "ne" in clean_hints: counts["ne"] += 2
            elif "sa" in clean_hints: counts["sa"] += 2
            elif "bho" in clean_hints: counts["bho"] += 2
            elif "mai" in clean_hints: counts["mai"] += 2
            else: counts["hi"] += 2
        elif 0x0980 <= code <= 0x09FF:
            if "as" in clean_hints: counts["as"] += 2
            else: counts["bn"] += 2
        elif 0x0A00 <= code <= 0x0A7F: counts["pa"] += 2
        elif 0x0A80 <= code <= 0x0AFF: counts["gu"] += 2
        elif 0x0B00 <= code <= 0x0B7F: counts["or"] += 2
        elif 0x0B80 <= code <= 0x0BFF: counts["ta"] += 2
        elif 0x0C00 <= code <= 0x0C7F: counts["te"] += 2
        elif 0x0C80 <= code <= 0x0CFF: counts["kn"] += 2
        elif 0x0D00 <= code <= 0x0D7F: counts["ml"] += 2
        elif 0x0D80 <= code <= 0x0DFF: counts["si"] += 2
        elif 0x10A0 <= code <= 0x10FF: counts["ka"] += 2
        elif 0x0530 <= code <= 0x058F: counts["hy"] += 2
        elif 0x1200 <= code <= 0x137F:
            if "ti" in clean_hints: counts["ti"] += 2
            else: counts["am"] += 2
        elif 0x0780 <= code <= 0x07BF: counts["dv"] += 2
        # Latin diacritics & special characters
        elif ch in "ğĞıİşŞ":
            counts["tr"] += 5
        elif ch in "çÇ":
            if "tr" in clean_hints: counts["tr"] += 4
            elif "pt" in clean_hints: counts["pt"] += 4
            elif "fr" in clean_hints: counts["fr"] += 4
            elif "ca" in clean_hints: counts["ca"] += 4
            else: counts["fr"] += 3
        elif ch in "öÖüÜ":
            if "tr" in clean_hints: counts["tr"] += 4
            elif "de" in clean_hints: counts["de"] += 4
            elif "hu" in clean_hints: counts["hu"] += 4
            elif "fi" in clean_hints: counts["fi"] += 4
            elif "sv" in clean_hints: counts["sv"] += 4
            else: counts["de"] += 3
        elif ch in "ñ¿¡Ñ":
            counts["es"] += 5
        elif ch in "ãõÃÕ":
            counts["pt"] += 5
        elif ch in "đĐơƠưƯàảãạằẳẵặầẩẫậèẻẽẹềểễệìỉĩịòỏõọồổỗộờởỡợùủũụừửữựỳỷỹỵ":
            counts["vi"] += 5
        elif ch in "ß":
            counts["de"] += 5
        elif ch in "œŒæÆ":
            counts["fr"] += 5
        elif ch in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ":
            counts["pl"] += 5
        elif ch in "ăîșțȘȚ":
            counts["ro"] += 5
        elif ch in "čďěňřšťůžČĎĚŇŘŠŤŮŽ":
            if "sk" in clean_hints: counts["sk"] += 5
            elif "cs" in clean_hints: counts["cs"] += 5
            elif "hr" in clean_hints or "bs" in clean_hints or "sl" in clean_hints: counts["hr"] += 5
            else: counts["cs"] += 5
        elif ch in "őűŐŰ":
            counts["hu"] += 5
        elif ch in "åøÅØ":
            if "da" in clean_hints: counts["da"] += 5
            elif "no" in clean_hints: counts["no"] += 5
            else: counts["sv"] += 5
        elif (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A):
            latin_char_count += 1

    # Check non-Latin scripts first
    non_latin = {k: v for k, v in counts.items() if k not in LATIN_LANGS}
    if non_latin:
        max_non_latin = max(non_latin, key=non_latin.get)
        if non_latin[max_non_latin] > 0:
            return max_non_latin

    # 2. Normalized Unaccented Word Token Matching
    norm_text = normalize_unaccented(text)
    words = re.findall(r'[a-z]+', norm_text)

    for w in words:
        for lang, vocab_set in VOCAB_UNACCENTED.items():
            if w in vocab_set:
                weight = 6 if lang in clean_hints else 4
                counts[lang] += weight

    # 3. Hint weighting for tiebreaking between active languages
    if clean_hints:
        for h in clean_hints:
            if h in counts and counts[h] > 0:
                counts[h] += 2

    if counts:
        best_lang = max(counts, key=counts.get)
        if counts[best_lang] > 0:
            return best_lang

    if latin_char_count > 0:
        if "en" in clean_hints:
            return "en"
        elif clean_hints:
            return list(clean_hints)[0]
        return "en"

    return "en"


# NLLB-200 / Flores-200 Language Code Mapping (Comprehensive Master Map for 127+ Languages)
NLLB_LANG_MAP = {
    "ace": "ace_Latn",
    "ace-arab": "ace_Arab",
    "acm": "acm_Arab",
    "acq": "acq_Arab",
    "aeb": "aeb_Arab",
    "af": "afr_Latn",
    "ajp": "ajp_Arab",
    "ak": "aka_Latn",
    "am": "amh_Ethi",
    "apc": "apc_Arab",
    "ar": "arb_Arab",
    "ars": "ars_Arab",
    "ary": "ary_Arab",
    "arz": "arz_Arab",
    "as": "asm_Beng",
    "ast": "ast_Latn",
    "awa": "awa_Deva",
    "ay": "ayr_Latn",
    "az": "azj_Latn",
    "azb": "azb_Arab",
    "ba": "bak_Cyrl",
    "ban": "ban_Latn",
    "be": "bel_Cyrl",
    "bem": "bem_Latn",
    "bg": "bul_Cyrl",
    "bho": "bho_Deva",
    "bjn": "bjn_Latn",
    "bjn-arab": "bjn_Arab",
    "bm": "bam_Latn",
    "bn": "ben_Beng",
    "bo": "bod_Tibt",
    "bs": "bos_Latn",
    "bug": "bug_Latn",
    "ca": "cat_Latn",
    "ceb": "ceb_Latn",
    "cjk": "cjk_Latn",
    "ckb": "ckb_Arab",
    "crh": "crh_Latn",
    "cs": "ces_Latn",
    "cy": "cym_Latn",
    "da": "dan_Latn",
    "de": "deu_Latn",
    "dik": "dik_Latn",
    "dyu": "dyu_Latn",
    "dz": "dzo_Tibt",
    "ee": "ewe_Latn",
    "el": "ell_Grek",
    "en": "eng_Latn",
    "eo": "epo_Latn",
    "es": "spa_Latn",
    "et": "est_Latn",
    "eu": "eus_Latn",
    "fa": "pes_Arab",
    "fi": "fin_Latn",
    "fj": "fij_Latn",
    "fo": "fao_Latn",
    "fon": "fon_Latn",
    "fr": "fra_Latn",
    "fur": "fur_Latn",
    "fuv": "fuv_Latn",
    "gd": "gla_Latn",
    "gl": "glg_Latn",
    "gle": "gle_Latn",
    "gn": "grn_Latn",
    "gu": "guj_Gujr",
    "ha": "hau_Latn",
    "he": "heb_Hebr",
    "hi": "hin_Deva",
    "hne": "hne_Deva",
    "hr": "hrv_Latn",
    "ht": "hat_Latn",
    "hu": "hun_Latn",
    "hy": "hye_Armn",
    "id": "ind_Latn",
    "ig": "ibo_Latn",
    "ilo": "ilo_Latn",
    "is": "isl_Latn",
    "it": "ita_Latn",
    "iw": "heb_Hebr",
    "ja": "jpn_Jpan",
    "jv": "jav_Latn",
    "jw": "jav_Latn",
    "ka": "kat_Geor",
    "kab": "kab_Latn",
    "kac": "kac_Latn",
    "kam": "kam_Latn",
    "kbp": "kbp_Latn",
    "kea": "kea_Latn",
    "kg": "kon_Latn",
    "kik": "kik_Latn",
    "kk": "kaz_Cyrl",
    "km": "khm_Khmr",
    "kmb": "kmb_Latn",
    "kn": "kan_Knda",
    "knc": "knc_Latn",
    "knc-arab": "knc_Arab",
    "ko": "kor_Hang",
    "ks": "kas_Deva",
    "ks-arab": "kas_Arab",
    "ku": "kmr_Latn",
    "ky": "kir_Cyrl",
    "lb": "ltz_Latn",
    "lg": "lug_Latn",
    "li": "lim_Latn",
    "lij": "lij_Latn",
    "lmo": "lmo_Latn",
    "ln": "lin_Latn",
    "lo": "lao_Laoo",
    "lt": "lit_Latn",
    "ltg": "ltg_Latn",
    "lua": "lua_Latn",
    "luo": "luo_Latn",
    "lus": "lus_Latn",
    "lv": "lvs_Latn",
    "mag": "mag_Deva",
    "mai": "mai_Deva",
    "mg": "plt_Latn",
    "mi": "mri_Latn",
    "min": "min_Latn",
    "mk": "mkd_Cyrl",
    "ml": "mal_Mlym",
    "mn": "khk_Cyrl",
    "mni-mtei": "mni_Beng",
    "mos": "mos_Latn",
    "mr": "mar_Deva",
    "ms": "zsm_Latn",
    "mt": "mlt_Latn",
    "my": "mya_Mymr",
    "ne": "npi_Deva",
    "nl": "nld_Latn",
    "nn": "nno_Latn",
    "no": "nob_Latn",
    "nso": "nso_Latn",
    "nus": "nus_Latn",
    "ny": "nya_Latn",
    "oc": "oci_Latn",
    "om": "gaz_Latn",
    "or": "ory_Orya",
    "pa": "pan_Guru",
    "pag": "pag_Latn",
    "pap": "pap_Latn",
    "pl": "pol_Latn",
    "prs": "prs_Arab",
    "ps": "pbt_Arab",
    "pt": "por_Latn",
    "qu": "quy_Latn",
    "rn": "run_Latn",
    "ro": "ron_Latn",
    "ru": "rus_Cyrl",
    "rw": "kin_Latn",
    "sa": "san_Deva",
    "sat": "sat_Beng",
    "sc": "srd_Latn",
    "scn": "scn_Latn",
    "sd": "snd_Arab",
    "sg": "sag_Latn",
    "shn": "shn_Mymr",
    "si": "sin_Sinh",
    "sk": "slk_Latn",
    "sl": "slv_Latn",
    "sm": "smo_Latn",
    "sn": "sna_Latn",
    "so": "som_Latn",
    "sq": "als_Latn",
    "sr": "srp_Cyrl",
    "ss": "ssw_Latn",
    "st": "sot_Latn",
    "su": "sun_Latn",
    "sv": "swe_Latn",
    "sw": "swh_Latn",
    "szl": "szl_Latn",
    "ta": "tam_Taml",
    "taq": "taq_Latn",
    "taq-tfng": "taq_Tfng",
    "te": "tel_Telu",
    "tg": "tgk_Cyrl",
    "th": "tha_Thai",
    "ti": "tir_Ethi",
    "tk": "tuk_Latn",
    "tl": "tgl_Latn",
    "tn": "tsn_Latn",
    "tr": "tur_Latn",
    "ts": "tso_Latn",
    "tt": "tat_Cyrl",
    "twi": "twi_Latn",
    "tzm": "tzm_Tfng",
    "ug": "uig_Arab",
    "uk": "ukr_Cyrl",
    "umb": "umb_Latn",
    "ur": "urd_Arab",
    "uz": "uzn_Latn",
    "vec": "vec_Latn",
    "vi": "vie_Latn",
    "war": "war_Latn",
    "wo": "wol_Latn",
    "xh": "xho_Latn",
    "yi": "ydd_Hebr",
    "yo": "yor_Latn",
    "yue": "yue_Hant",
    "zh": "zho_Hans",
    "zh-cn": "zho_Hans",
    "zh-tw": "zho_Hant",
    "zu": "zul_Latn"
}

ALL_NLLB_SPECIAL_TOKENS = set(NLLB_LANG_MAP.values()) | {"</s>", "<s>", "<pad>", "<unk>", "<mask_1>", "<mask_2>"}
KNOWN_TAG_SUFFIXES = (
    "_Latn", "_Thai", "_Hans", "_Hant", "_Deva", "_Arab", "_Cyrl", "_Grek", "_Hebr",
    "_Khmr", "_Laoo", "_Mymr", "_Armn", "_Beng", "_Geor", "_Gujr", "_Guru", "_Jpan",
    "_Knda", "_Kana", "_Kore", "_Mlym", "_Orya", "_Sinh", "_Taml", "_Telu", "_Tibt"
)

# Recommended Multilingual Models
RECOMMENDED_MODELS = [
    {
        "id": "nllb-200-600m",
        "name": _("NLLB-200 Standard (600M - Fast ~600 MB)"),
        "repo": "JustFrederik/nllb-200-distilled-600M-ct2-int8",
        "approx_size_mb": 600,
        "is_multilingual": True
    },
    {
        "id": "nllb-200-1.3b",
        "name": _("NLLB-200 High Quality (1.3B - Enhanced Accuracy ~1.3 GB)"),
        "repo": "JustFrederik/nllb-200-distilled-1.3B-ct2-int8",
        "approx_size_mb": 1300,
        "is_multilingual": True
    }
]

OFFLINE_MODELS_CATALOG = RECOMMENDED_MODELS


def get_installed_offline_models():
    """Returns a list of folder names for valid installed models."""
    installed = []
    if os.path.exists(MODELS_DIR):
        for item in os.listdir(MODELS_DIR):
            item_path = os.path.join(MODELS_DIR, item)
            if os.path.isdir(item_path):
                # Ensure directory contains valid model weights
                if os.path.isfile(os.path.join(item_path, "model.bin")):
                    installed.append(item)
        installed.sort()
    return installed


def delete_installed_model(model_id):
    """Deletes an installed model directory."""
    if not model_id or not isinstance(model_id, str):
        return False
    clean_id = model_id.strip()
    if not re.match(r'^[a-zA-Z0-9_\.-]+$', clean_id) or ".." in clean_id or "/" in clean_id or "\\" in clean_id:
        logHandler.log.error(f"OmniTranslate: Refusing to delete model with invalid or dangerous ID: {model_id}")
        return False

    models_dir_abs = os.path.abspath(MODELS_DIR)
    model_dir = os.path.abspath(os.path.join(MODELS_DIR, clean_id))
    if not model_dir.startswith(models_dir_abs + os.sep) or model_dir == models_dir_abs:
        logHandler.log.error(f"OmniTranslate: Path traversal detected in delete model: {model_dir}")
        return False

    _MODEL_LANG_CACHE.pop(clean_id, None)
    if os.path.exists(model_dir):
        try:
            if model_dir in _LOADED_MODELS:
                try:
                    engine = _LOADED_MODELS.pop(model_dir, None)
                    if engine:
                        translator = engine.get("translator")
                        if translator and hasattr(translator, "unload_model"):
                            translator.unload_model()
                        del engine
                except Exception:
                    pass
                import gc
                gc.collect()
            shutil.rmtree(model_dir, ignore_errors=True)
            return True
        except Exception as e:
            logHandler.log.error(f"OmniTranslate: Failed to delete model {clean_id}: {e}")
            return False
    return False


def get_model_supported_languages(model_id):
    """Returns supported source and target language codes for a given model (supports custom/user-installed models)."""
    if not model_id or model_id == "none":
        all_langs = list(NLLB_LANG_MAP.keys())
        return {"src": all_langs, "tgt": all_langs, "is_multilingual": True}

    if model_id in _MODEL_LANG_CACHE:
        return _MODEL_LANG_CACHE[model_id]

    model_dir = os.path.join(MODELS_DIR, model_id)
    info_file = os.path.join(model_dir, "model_info.json")

    res = None
    # 1. Check model_info.json metadata
    if os.path.exists(info_file):
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                info = json.load(f)
            if info.get("is_multilingual", False) or "nllb" in model_id.lower():
                all_langs = list(NLLB_LANG_MAP.keys())
                res = {"src": all_langs, "tgt": all_langs, "is_multilingual": True}
            else:
                src = info.get("from", "").lower()
                tgt = info.get("to", "").lower()
                if src and tgt:
                    res = {"src": [src], "tgt": [tgt], "is_multilingual": False}
        except Exception:
            pass

    # 2. Check model vocabulary for NLLB / Multilingual tags (Deep inspection of custom models)
    if res is None:
        for vocab_name in ("shared_vocabulary.txt", "shared_vocabulary.json"):
            vocab_path = os.path.join(model_dir, vocab_name)
            if os.path.exists(vocab_path):
                try:
                    with open(vocab_path, "r", encoding="utf-8", errors="ignore") as vf:
                        sample = vf.read(4096)
                        if "tha_Thai" in sample or "eng_Latn" in sample or "zho_Hans" in sample:
                            all_langs = list(NLLB_LANG_MAP.keys())
                            res = {"src": all_langs, "tgt": all_langs, "is_multilingual": True}
                            break
                except Exception:
                    pass

    # 3. Check Multilingual indicators in folder name
    if res is None:
        lower_id = model_id.lower()
        if any(k in lower_id for k in ("nllb", "m2m", "multilingual", "flores")):
            all_langs = list(NLLB_LANG_MAP.keys())
            res = {"src": all_langs, "tgt": all_langs, "is_multilingual": True}

    # 4. Check bilingual pair pattern in folder name (e.g., en-th, opus-mt-en-th, marian_de_en, th_ja)
    if res is None:
        clean_id = lower_id.replace("opus-mt-", "").replace("opus_", "").replace("marian-", "").replace("marian_", "")
        for sep in ("-", "_"):
            if sep in clean_id:
                parts = clean_id.split(sep)
                if len(parts) >= 2 and parts[0] in NLLB_LANG_MAP and parts[1] in NLLB_LANG_MAP:
                    res = {"src": [parts[0]], "tgt": [parts[1]], "is_multilingual": False}
                    break

    if res is None:
        all_langs = list(NLLB_LANG_MAP.keys())
        res = {"src": all_langs, "tgt": all_langs, "is_multilingual": True}

    _MODEL_LANG_CACHE[model_id] = res
    return res


def download_model_package(model_info, on_complete=None):
    """Downloads CTranslate2 model package with live progress."""
    if getattr(globalVars.appArgs, "secureMode", False):
        wx.CallAfter(ui.message, _("Model download is disabled on secure screens."))
        return

    model_id = str(model_info.get("id", "nllb-200-600m")).strip()
    if not re.match(r'^[a-zA-Z0-9_\.-]+$', model_id) or ".." in model_id or "/" in model_id or "\\" in model_id:
        logHandler.log.error(f"OmniTranslate: Invalid model ID for download: {model_id}")
        return

    models_dir_abs = os.path.abspath(MODELS_DIR)
    target_dir = os.path.abspath(os.path.join(MODELS_DIR, model_id))
    if not target_dir.startswith(models_dir_abs + os.sep):
        logHandler.log.error(f"OmniTranslate: Path traversal detected in target_dir: {target_dir}")
        return

    repo_name = str(model_info.get("repo", "JustFrederik/nllb-200-distilled-600M-ct2-int8")).strip()
    if not re.match(r'^[a-zA-Z0-9_\.-]+/[a-zA-Z0-9_\.-]+$', repo_name) or ".." in repo_name:
        logHandler.log.error(f"OmniTranslate: Invalid repo name for download: {repo_name}")
        return
    base_url = f"https://huggingface.co/{repo_name}/resolve/main/"

    files_to_download = [
        ("config.json", False),
        ("shared_vocabulary.txt", False),
        ("shared_vocabulary.json", False),
        ("sentencepiece.bpe.model", False),
        ("source.spm", False),
        ("spm.model", False),
        ("opus.spm", False),
        ("model.bin", True)
    ]

    def _worker():
        try:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            wx.CallAfter(ui.message, _("Connecting to download {name}...").format(
                name=model_info["name"]
            ))

            total_downloaded_bytes = 0

            for fname, is_required in files_to_download:
                file_url = base_url + fname
                dest_path = os.path.join(target_dir, fname)
                req = urllib.request.Request(
                    file_url,
                    headers={'User-Agent': 'Mozilla/5.0 OmniTranslate-NVDA'}
                )

                try:
                    with urllib.request.urlopen(req, timeout=25) as res:
                        content_len = res.headers.get('Content-Length')
                        file_total = int(content_len) if content_len else 0
                        file_done = 0
                        last_pct = 0

                        part_path = dest_path + ".part"
                        with open(part_path, "wb") as out_file:
                            while True:
                                chunk = res.read(1024 * 512)
                                if not chunk:
                                    break
                                out_file.write(chunk)
                                file_done += len(chunk)
                                total_downloaded_bytes += len(chunk)

                                if file_total > 5 * 1024 * 1024:
                                    pct = int((file_done / file_total) * 100)
                                    if pct - last_pct >= 20:
                                        last_pct = pct
                                        done_mb = file_done / (1024 * 1024)
                                        total_mb = file_total / (1024 * 1024)
                                        msg = _("Downloading {name}: {pct}% ({done_mb:.1f} MB / {total_mb:.1f} MB)").format(
                                             name=model_info["name"],
                                             pct=pct,
                                             done_mb=done_mb,
                                             total_mb=total_mb
                                         )
                                        wx.CallAfter(ui.message, msg)
                        os.replace(part_path, dest_path)
                except urllib.error.HTTPError as he:
                    if is_required:
                        raise he
                except Exception as e:
                    if is_required:
                        raise e
                    continue

            # Verify that essential model files (model.bin and at least one tokenizer) were downloaded successfully
            has_tokenizer = any(
                os.path.isfile(os.path.join(target_dir, sp_name))
                for sp_name in ("source.spm", "spm.model", "sentencepiece.bpe.model", "opus.spm")
            )
            if not os.path.isfile(os.path.join(target_dir, "model.bin")) or not has_tokenizer:
                raise Exception(_("Model package is incomplete: missing weights or tokenizer."))

            with open(os.path.join(target_dir, "model_info.json"), "w", encoding="utf-8") as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)

            total_mb = total_downloaded_bytes / (1024 * 1024)
            wx.CallAfter(tones.beep, 880, 50)
            wx.CallAfter(ui.message, _("Installation complete: {name} ({total_mb:.1f} MB) is ready.").format(
                name=model_info["name"],
                total_mb=total_mb
            ))

            _MODEL_LANG_CACHE.pop(model_id, None)

            if on_complete:
                on_complete(model_id)

        except Exception as e:
            logHandler.log.error(f"OmniTranslate: Error downloading model: {e}")
            # Clean up incomplete model folder so corrupted weights are not loaded
            if not os.path.exists(os.path.join(target_dir, "model.bin")):
                try:
                    shutil.rmtree(target_dir, ignore_errors=True)
                except Exception:
                    pass
            err_msg = _("Model download failed: {error}").format(error=str(e))
            wx.CallAfter(ui.message, err_msg)

    threading.Thread(target=_worker, daemon=True).start()


def get_loaded_engine(model_dir):
    """Loads and caches CTranslate2 engine and SentencePiece tokenizer."""
    if model_dir in _LOADED_MODELS:
        return _LOADED_MODELS[model_dir]

    try:
        import ctranslate2
        import sentencepiece as spm

        sp_path = None
        for name in ("source.spm", "spm.model", "sentencepiece.bpe.model", "opus.spm"):
            candidate = os.path.join(model_dir, name)
            if os.path.exists(candidate):
                sp_path = candidate
                break

        if not sp_path:
            logHandler.log.error(f"OmniTranslate: No tokenizer file found in {model_dir}")
            return None

        sp_processor = spm.SentencePieceProcessor(model_file=sp_path)
        translator = ctranslate2.Translator(model_dir, device="cpu", compute_type="auto")

        engine = {
            "sp": sp_processor,
            "translator": translator
        }
        _LOADED_MODELS[model_dir] = engine
        return engine
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Engine initialization error: {e}")
        return None


def clean_output_text(translated_text, original_text):
    """Sanitizes translation output by removing artificial NMT dialogue dashes and subword artifacts."""
    if not translated_text:
        return ""
    res = translated_text.strip()
    orig_stripped = original_text.strip() if original_text else ""
    if not orig_stripped.startswith(("-", "—", "–", "•", "*")):
        if res.startswith(("- ", "— ", "– ", "• ", "* ")):
            res = res[2:].strip()
        elif res.startswith(("-", "—", "–", "_")) and len(res) > 1 and res[1] not in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
            res = res[1:].strip()
    return res


def get_language_display_name(code):
    """Helper to get user-friendly translated language name."""
    try:
        from . import settingsDialogs
        return settingsDialogs.AVAILABLE_LANGUAGES.get(code, code)
    except Exception:
        return code


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


def translate_offline(text, model_id, src_lang="en", tgt_lang="th"):
    """Translates text offline with support for Multilingual and Bilingual models."""
    if not text or not isinstance(text, str) or not text.strip():
        return ""

    model_dir = os.path.join(MODELS_DIR, model_id)
    if not os.path.exists(model_dir):
        raise Exception(_("Model directory not found: ") + model_id)

    engine = get_loaded_engine(model_dir)
    if not engine:
        raise Exception(_("Offline neural engine runtime is not available or model is invalid."))

    try:
        sp = engine["sp"]
        translator = engine["translator"]
        supp_info = get_model_supported_languages(model_id)
        is_multilingual = supp_info.get("is_multilingual", True)

        lines = normalize_newlines(text).split("\n")
        batch_inputs = []
        batch_indices = []
        max_raw_len = 1

        if is_multilingual:
            clean_src = src_lang.lower() if src_lang else "en"
            clean_tgt = tgt_lang.lower() if tgt_lang else "th"
            if clean_src not in NLLB_LANG_MAP:
                clean_src = clean_src.split("-")[0]
            if clean_tgt not in NLLB_LANG_MAP:
                clean_tgt = clean_tgt.split("-")[0]

            if clean_tgt not in NLLB_LANG_MAP:
                tgt_display = get_language_display_name(tgt_lang)
                raise Exception(_("The offline model does not support target language '{lang}'.").format(lang=tgt_display))

            nllb_src = NLLB_LANG_MAP.get(clean_src, "eng_Latn")
            nllb_tgt = NLLB_LANG_MAP[clean_tgt]

            for idx, line in enumerate(lines):
                line_str = line.strip()
                if line_str:
                    raw_tokens = sp.encode(line_str, out_type=str)
                    if len(raw_tokens) > max_raw_len:
                        max_raw_len = len(raw_tokens)
                    source_tokens = raw_tokens + ["</s>", nllb_src]
                    batch_inputs.append(source_tokens)
                    batch_indices.append((idx, line_str))

            if not batch_inputs:
                return text

            target_prefix = [[nllb_tgt]] * len(batch_inputs)
            max_dec = max(128, int(max_raw_len * 4) + 64)

            results = translator.translate_batch(
                batch_inputs,
                target_prefix=target_prefix,
                beam_size=4,
                repetition_penalty=1.05,
                no_repeat_ngram_size=0,
                max_decoding_length=max_dec
            )

            output_lines = list(lines)
            for res_idx, (line_idx, orig_line) in enumerate(batch_indices):
                hyp = results[res_idx].hypotheses[0]
                clean_tokens = [tok for tok in hyp if tok not in ALL_NLLB_SPECIAL_TOKENS and not tok.endswith(KNOWN_TAG_SUFFIXES)]
                translated = sp.decode(clean_tokens)
                cleaned = clean_output_text(translated, orig_line)
                output_lines[line_idx] = cleaned if cleaned else orig_line

            return "\r\n".join(output_lines)

        else:
            # Bilingual Pair Mode (Opus-MT / Marian / Custom Pair)
            supp_tgt = [t.lower() for t in supp_info.get("tgt", [])]
            clean_tgt = tgt_lang.lower() if tgt_lang else "th"
            if supp_tgt and clean_tgt not in supp_tgt and clean_tgt.split("-")[0] not in supp_tgt:
                tgt_display = get_language_display_name(tgt_lang)
                raise Exception(_("The offline model '{model}' does not support target language '{lang}'.").format(model=model_id, lang=tgt_display))

            special_tokens = {"</s>", "<s>", "<pad>", "<unk>"}
            for idx, line in enumerate(lines):
                line_str = line.strip()
                if line_str:
                    raw_tokens = sp.encode(line_str, out_type=str)
                    if len(raw_tokens) > max_raw_len:
                        max_raw_len = len(raw_tokens)
                    batch_inputs.append(raw_tokens)
                    batch_indices.append((idx, line_str))

            if not batch_inputs:
                return text

            max_dec = max(128, int(max_raw_len * 4) + 64)
            results = translator.translate_batch(
                batch_inputs,
                beam_size=4,
                repetition_penalty=1.05,
                no_repeat_ngram_size=0,
                max_decoding_length=max_dec
            )

            output_lines = list(lines)
            for res_idx, (line_idx, orig_line) in enumerate(batch_indices):
                hyp = results[res_idx].hypotheses[0]
                clean_tokens = [tok for tok in hyp if tok not in special_tokens]
                translated = sp.decode(clean_tokens)
                cleaned = clean_output_text(translated, orig_line)
                output_lines[line_idx] = cleaned if cleaned else orig_line

            return "\r\n".join(output_lines)

    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Translation execution error: {e}")
        err_str = str(e)
        if "Offline translation error:" in err_str or "does not support" in err_str or "Model directory not found" in err_str:
            raise e
        raise Exception(_("Offline translation error: ") + err_str)