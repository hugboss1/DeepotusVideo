"""Préférences de l'écran du Photolab (t159, parité L9) : ce que l'utilisateur règle dans Édition › Préférences,
Raccourcis clavier et Menus, gardé entre deux sessions.

Un fichier `<données>/photolab/preferences.json`. Rien n'y est envoyé au moteur (`prefs.*` écrirait ses préférences ; en
mode `serve` il n'en garde d'ailleurs aucune) : ce sont des réglages d'ÉCRAN. Les sections et les clés reprennent les
noms de photocraft (`prefs.get`), leurs énumérations et bornes sont celles que `prefs.set` annonce (relevé du
09/10/2026) — restreintes à ce que l'écran sait honorer. La validation est une liste blanche STRICTE (clé inconnue,
mauvais type, hors bornes : refusé) ; une clé absente prend son défaut. La copie JavaScript du schéma
(frontend/photolab/js/mod-preferences.js) est comparée par le banc test_photolab_preferences.
"""
import json
import os
import re
import tempfile
from pathlib import Path

UNITES = ["pixels", "inches", "cm", "mm", "points", "picas", "percent"]
STYLES_TRAIT = ["lines", "dashedLines", "dots"]
# (type, défaut, valeurs | bornes) ; « couleur » = #rrggbb.
SCHEMA = {
    "general": {
        "zoomWithScrollWheel": ("bool", False),
        "resizeImageDuringPlace": ("bool", True),
        "alwaysCreateSmartObjectsWhenPlacing": ("bool", True),
    },
    "interface": {
        "canvasColor": ("enum", "default", ["default", "black", "darkGray", "mediumGray", "lightGray", "custom"]),
        "canvasCustomColor": ("couleur", "#282828"),
        # défaut « line » (photocraft : dropShadow) : le filet que l'écran dessinait avant t159
        "canvasBorder": ("enum", "line", ["dropShadow", "line", "none"]),
        "showTooltips": ("bool", True),
        "showMenuColors": ("bool", True),
    },
    "workspace": {
        "largeTabs": ("bool", False),
        "rememberWorkspaceChanges": ("bool", True),
    },
    "tools": {
        "useShiftKeyForToolSwitch": ("bool", False),
        "overscroll": ("bool", True),
        "zoomClickedPointToCenter": ("bool", False),
    },
    "fileHandling": {
        "lowercaseExtension": ("bool", True),
    },
    "export": {
        # gif : le pont n'exporte pas ce format (FORMATS de photolab_routes)
        "quickExportFormat": ("enum", "png", ["png", "jpg", "webp"]),
        "jpegQuality": ("int", 85, (1, 100)),
        # photocraft : ask|sameFolder ; chez nous il n'y a pas de dossier : demander, télécharger, Bibliothèque
        "quickExportLocation": ("enum", "download", ["ask", "download", "library"]),
    },
    "cursors": {
        "painting": ("enum", "normalTip", ["standard", "precise", "normalTip", "fullSizeTip"]),
        "other": ("enum", "standard", ["standard", "precise"]),
        "showCrosshairInBrushTip": ("bool", False),
        "showOnlyCrosshairWhilePainting": ("bool", False),
    },
    "transparencyAndGamut": {
        "gridSize": ("enum", "medium", ["none", "small", "medium", "large"]),
        # « theme » (défaut, ajouté par Deepotus) : le damier aux couleurs du thème, comme avant t159
        "gridColors": ("enum", "theme", ["theme", "light", "medium", "dark", "red", "orange", "green", "blue", "purple", "custom"]),
        "customLight": ("couleur", "#ffffff"),
        "customDark": ("couleur", "#cccccc"),
    },
    "unitsAndRulers": {
        "rulers": ("enum", "pixels", UNITES),
    },
    "guidesGridAndSlices": {
        "guideColor": ("couleur", "#4affff"),
        "guideStyle": ("enum", "lines", STYLES_TRAIT),
        "gridColor": ("couleur", "#8c8c8c"),
        "gridStyle": ("enum", "lines", STYLES_TRAIT),
        "gridlineEvery": ("num", 1.0, (0.001, 10000)),
        "gridUnit": ("enum", "inches", UNITES),
        "subdivisions": ("int", 4, (1, 100)),
    },
    "type": {
        # photocraft a aussi « off » ; l'écran montre toujours un aperçu (mod-texte : APERCUS)
        "fontPreview": ("enum", "medium", ["small", "medium", "large", "extraLarge", "huge"]),
        "useEscToCommit": ("bool", True),
    },
}
# Sections du dialogue dans l'ordre du menu Édition › Préférences : celles de SCHEMA ont des réglages, les autres sont
# des sections explicatives (décision Q1 du 09/10/2026).
SECTIONS_EXPLICATIVES = ("historyLog", "performance", "scratchDisks", "plugIns", "enhancedControls", "rawDefaults",
                         "integrations")

# Reprise des options que l'écran gardait dans le navigateur (mod-affichage OPTIONS_DEFAUT, mod-texte PREFS_DEFAUT).
AFFICHAGE_BOOLS = ("extras", "regles", "grille", "reperes", "aimanter", "verrouReperes", "miroir", "pixelArt")
AFFICHAGE_SOUS = {"afficher": ("contoursCalque", "contoursSelection", "grillePixels", "apercuPinceau", "reperesCanevas",
                               "compteur", "notes", "tranches"),                  # t160
                  "aimanterA": ("reperes", "grille", "calques", "document", "tranches")}
ECRANS = ("standard", "menus", "plein")
LANGUES_TEXTE = ("type.languageOptions.defaultFeatures", "type.languageOptions.eastAsianFeatures",
                 "type.languageOptions.middleEasternFeatures")

COULEURS_MENU = ("red", "orange", "yellow", "green", "blue", "violet", "gray")
# Entrées qu'on ne masque pas (on ne pourrait plus défaire) — reprises de la référence : les Préférences et Menus….
NON_MASQUABLES = ("edit.menus", "edit.keyboardShortcuts", "edit.preferences.general")
MAX_RACCOURCIS = 1000
MAX_MASQUES = 1000
_ID = re.compile(r"[a-z][A-Za-z0-9]*(\.[a-z][A-Za-z0-9]*)+")
_ID_OUTIL = re.compile(r"[a-z][A-Za-z0-9]{0,40}")
_HEX = re.compile(r"#[0-9a-f]{6}")
# Combinaison normalisée par l'écran (mod-raccourcis.normaliser) : modificateurs dans l'ordre ctrl, alt, shift, puis
# une touche : lettre, chiffre, F1-F12, ou l'un des signes que le catalogue emploie.
_COMBO = re.compile(r"(ctrl\+)?(alt\+)?(shift\+)?([a-z0-9]|f([1-9]|1[0-2])|[\[\]\-=;',./`]|delete|backspace|tab|enter|"
                    r"escape|space|arrowup|arrowdown|arrowleft|arrowright|home|end|pageup|pagedown)")
_CLES = {"version", "prefs", "raccourcis", "menus", "affichage", "texte"}


def etat_defaut() -> dict:
    return {
        "version": 1,
        "prefs": {s: {k: spec[1] for k, spec in cles.items()} for s, cles in SCHEMA.items()},
        "raccourcis": {"commandes": {}, "outils": {}},
        "menus": {"masques": [], "couleurs": {}},
        "affichage": None,                  # None = jamais repris : l'écran garde ses défauts (ou le navigateur)
        "texte": {"langue": LANGUES_TEXTE[0], "composeur": False},
    }


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "preferences.json"


def _objet(v, ou, cles=None):
    if not isinstance(v, dict):
        raise ValueError(f"{ou} : objet attendu")
    if cles is not None:
        inconnues = set(v) - set(cles)
        if inconnues:
            raise ValueError(f"{ou} : clé(s) inconnue(s) : {', '.join(sorted(map(str, inconnues)))}")


def _valeur(spec, v, ou):
    t = spec[0]
    if t == "bool":
        if not isinstance(v, bool):
            raise ValueError(f"{ou} : booléen attendu")
        return v
    if t == "enum":
        if v not in spec[2]:
            raise ValueError(f"{ou} : une valeur parmi {'|'.join(spec[2])}")
        return v
    if t == "couleur":
        if not (isinstance(v, str) and _HEX.fullmatch(v.lower())):
            raise ValueError(f"{ou} : couleur « #rrggbb » attendue")
        return v.lower()
    a, b = spec[2]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (t == "int" and not float(v).is_integer()):
        raise ValueError(f"{ou} : {'entier' if t == 'int' else 'nombre'} attendu")
    if not (a <= v <= b):
        raise ValueError(f"{ou} : entre {a} et {b}")
    return int(v) if t == "int" else float(v)


def _prefs(p) -> dict:
    _objet(p, "prefs", SCHEMA)
    sortie = {}
    for s, cles in SCHEMA.items():
        brut = p.get(s, {})
        _objet(brut, f"prefs.{s}", cles)
        sortie[s] = {k: (_valeur(spec, brut[k], f"prefs.{s}.{k}") if k in brut else spec[1]) for k, spec in cles.items()}
    return sortie


def _raccourcis(r) -> dict:
    _objet(r, "raccourcis", {"commandes", "outils"})
    cmd, outils = r.get("commandes", {}), r.get("outils", {})
    _objet(cmd, "raccourcis.commandes")
    _objet(outils, "raccourcis.outils")
    if len(cmd) + len(outils) > MAX_RACCOURCIS:
        raise ValueError(f"raccourcis : {MAX_RACCOURCIS} au plus")
    for k, v in cmd.items():
        if not _ID.fullmatch(str(k)):
            raise ValueError(f"raccourcis.commandes : commande mal formée : {k!r}")
        # "" = raccourci retiré ; une touche seule (sans Ctrl / Alt) reste aux outils, sauf les touches de fonction
        if not isinstance(v, str) or (v and (not _COMBO.fullmatch(v) or not
                                             (v.startswith(("ctrl+", "alt+")) or re.fullmatch(r"(shift\+)?f\d{1,2}", v)))):
            raise ValueError(f"raccourcis.commandes.{k} : combinaison avec Ctrl, Alt ou une touche de fonction attendue")
    vus = {}
    for k, v in cmd.items():
        # deux commandes sur la même combinaison : l'écran ne saurait laquelle lancer (les outils, eux, partagent une
        # lettre par groupe, comme chez photocraft)
        if v and v in vus:
            raise ValueError(f"raccourcis.commandes : {v} est déjà pris par {vus[v]}")
        vus[v] = k
    for k, v in outils.items():
        if not _ID_OUTIL.fullmatch(str(k)):
            raise ValueError(f"raccourcis.outils : outil mal formé : {k!r}")
        if not isinstance(v, str) or (v and not re.fullmatch(r"[a-z]", v)):
            raise ValueError(f"raccourcis.outils.{k} : une lettre attendue")
    return {"commandes": dict(cmd), "outils": dict(outils)}


def _menus(m) -> dict:
    _objet(m, "menus", {"masques", "couleurs"})
    masques, couleurs = m.get("masques", []), m.get("couleurs", {})
    if not isinstance(masques, list) or len(masques) > MAX_MASQUES:
        raise ValueError(f"menus.masques : liste de {MAX_MASQUES} commandes au plus")
    for k in masques:
        if not isinstance(k, str) or not _ID.fullmatch(k):
            raise ValueError(f"menus.masques : commande mal formée : {k!r}")
        if k in NON_MASQUABLES:
            raise ValueError(f"menus.masques : {k} ne se masque pas")
    _objet(couleurs, "menus.couleurs")
    if len(couleurs) > MAX_MASQUES:
        raise ValueError(f"menus.couleurs : {MAX_MASQUES} au plus")
    for k, v in couleurs.items():
        if not _ID.fullmatch(str(k)):
            raise ValueError(f"menus.couleurs : commande mal formée : {k!r}")
        if v not in COULEURS_MENU:
            raise ValueError(f"menus.couleurs.{k} : une couleur parmi {'|'.join(COULEURS_MENU)}")
    return {"masques": list(dict.fromkeys(masques)), "couleurs": dict(couleurs)}


def _affichage(a):
    if a is None:
        return None
    _objet(a, "affichage", set(AFFICHAGE_BOOLS) | set(AFFICHAGE_SOUS) | {"ecran"})
    sortie = {}
    for k in AFFICHAGE_BOOLS:
        if k in a:
            sortie[k] = _valeur(("bool",), a[k], f"affichage.{k}")
    if "ecran" in a:
        sortie["ecran"] = _valeur(("enum", None, ECRANS), a["ecran"], "affichage.ecran")
    for s, cles in AFFICHAGE_SOUS.items():
        if s in a:
            _objet(a[s], f"affichage.{s}", cles)
            sortie[s] = {k: _valeur(("bool",), a[s][k], f"affichage.{s}.{k}") for k in a[s]}
    return sortie


def _texte(t) -> dict:
    _objet(t, "texte", {"langue", "composeur"})
    d = etat_defaut()["texte"]
    if "langue" in t:
        d["langue"] = _valeur(("enum", None, LANGUES_TEXTE), t["langue"], "texte.langue")
    if "composeur" in t:
        d["composeur"] = _valeur(("bool",), t["composeur"], "texte.composeur")
    return d


def valider(obj) -> dict:
    """L'état complet (défauts pour ce qui manque) s'il est admis ; sinon ValueError (message français)."""
    _objet(obj, "état", _CLES)
    if obj.get("version", 1) != 1 or isinstance(obj.get("version"), bool):
        raise ValueError("état.version : 1 attendu")
    return {
        "version": 1,
        "prefs": _prefs(obj.get("prefs", {})),
        "raccourcis": _raccourcis(obj.get("raccourcis", {})),
        "menus": _menus(obj.get("menus", {})),
        "affichage": _affichage(obj.get("affichage")),
        "texte": _texte(obj.get("texte", {})),
    }


def lire() -> dict:
    """{"etat", "enregistre"} : l'état enregistré, ou le défaut (fichier absent, illisible, refusé) avec
    `enregistre: false` — l'écran sait alors qu'il peut reprendre ce que le navigateur gardait."""
    try:
        return {"etat": valider(json.loads(chemin().read_text(encoding="utf-8"))), "enregistre": True}
    except (OSError, ValueError, TypeError, AttributeError):
        return {"etat": etat_defaut(), "enregistre": False}


def ecrire(obj) -> dict:
    """Valide puis écrit d'un seul tenant (fichier temporaire du même dossier puis os.replace)."""
    etat = valider(obj)
    f = chemin()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="preferences-", suffix=".tmp", dir=f.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as h:
            json.dump(etat, h, ensure_ascii=False, indent=1)
        os.replace(tmp, f)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return etat


def reinitialiser() -> dict:
    """Édition › Préférences › Réinitialiser : retour aux défauts (raccourcis et menus compris), enregistré."""
    return ecrire(etat_defaut())
