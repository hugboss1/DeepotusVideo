# -*- coding: utf-8 -*-
"""Photolab P3 — le registre du moteur photocraft, structuré.

`engine.commands` décrit chaque commande par un texte « JSON-ish » (`params`) : un objet `{ENTREE, …}` puis une
queue libre (` (note)`, ` → résultat`, ` — phrase`). On le parse UNE fois ici en champs typés, pour que le pont
(liste blanche de /executer) et l'écran (formulaires générés) lisent la même vérité au lieu de deviner.

ENTREE = `"clé":TYPE[=DEFAUT][?][ (note)]`. Les séparateurs ne comptent qu'à profondeur 0, hors guillemets.
Bibliothèque standard seulement : ce module est lu par les bancs hors ligne sans moteur ni FastAPI.

Types de champ : number, int, bool, enum, color, str, layerId, index, docIndex (éditables), puis les champs
« opaques » json, struct, intArray, union et « ? » (type non reconnu) : l'écran ne les montre pas dans un
formulaire générique et le pont les borne en taille.
"""
from __future__ import annotations

import json
import re

TYPES = ("number", "int", "bool", "enum", "color", "str", "layerId", "index", "docIndex",
         "json", "struct", "intArray", "union", "?")
OPAQUES = ("json", "struct", "intArray", "union", "?")

_NUM = r"-?\d+(?:\.\d+)?"
# Bornes écrites « 0..100 », « -100..100 » ou, pour liquify, « 0-100 » (le tiret sert alors de séparateur).
_RE_BORNES = re.compile(rf"^({_NUM})\s*(?:\.\.|-)\s*({_NUM})$")
_RE_CLE = re.compile(r'^\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*(.*)$', re.S)
_UNITES = {"px", "deg", "mm", "ppi", "%", "ev", "level", "pt"}
_SCALAIRES = {"bool": "bool", "json": "json", "str": "str", "text": "str", "name": "str",
              "u32": "int", "i32": "int", "int": "int", "u64": "int",
              "id": "layerId", "index": "index", "doc": "docIndex", "color": "color",
              "group": "str", "n": "int"}
_POINTS_DE_SUSPENSION = ("…", "...")


# Limite connue : les guillemets échappés (\") ne sont pas gérés par _decouper, _objet_et_queue ni _premier_egal ;
# le registre épinglé 0.3.0 n'en contient pas. À revoir si le moteur change de version.
def _decouper(s: str, sep: str = ",") -> list[str]:
    """Coupe `s` au séparateur de profondeur 0, hors guillemets (une virgule dans `[x,y]` ne sépare rien)."""
    sortie, profondeur, guillemets, courant = [], 0, False, ""
    for ch in s:
        if ch == '"':
            guillemets = not guillemets
        elif not guillemets and ch in "[{(":
            profondeur += 1
        elif not guillemets and ch in "]})":
            profondeur -= 1
        if ch == sep and profondeur == 0 and not guillemets:
            sortie.append(courant)
            courant = ""
        else:
            courant += ch
    sortie.append(courant)
    return sortie


def _objet_et_queue(s: str):
    """Le premier objet {…} équilibré (sans ses accolades) et ce qui le suit ; (None, s) s'il n'y en a pas."""
    s = s.strip()
    if not s.startswith("{"):
        return None, s
    profondeur, guillemets = 0, False
    for i, ch in enumerate(s):
        if ch == '"':
            guillemets = not guillemets
        elif not guillemets and ch in "{[(":
            profondeur += 1
        elif not guillemets and ch in "}])":
            profondeur -= 1
            if profondeur == 0:
                return s[1:i], s[i + 1:].strip()
    return None, s


def _sans_note(v: str):
    """Retire une note finale ` (…)` de profondeur 0 ; exige une espace avant la parenthèse
    (sinon c'est un morceau du type, pas une note)."""
    v = v.strip()
    note = None
    if v.endswith(")"):
        profondeur = 0
        for i in range(len(v) - 1, -1, -1):
            if v[i] == ")":
                profondeur += 1
            elif v[i] == "(":
                profondeur -= 1
                if profondeur == 0:
                    if i > 0 and v[i - 1] == " ":
                        note = v[i + 1:-1]
                        v = v[:i].strip()
                    break
    return v, note


def _premier_egal(v: str):
    """Coupe (type, défaut) au premier `=` de profondeur 0 hors guillemets ; défaut None s'il n'y en a pas."""
    profondeur, guillemets = 0, False
    for i, ch in enumerate(v):
        if ch == '"':
            guillemets = not guillemets
        elif not guillemets and ch in "[{(":
            profondeur += 1
        elif not guillemets and ch in "]})":
            profondeur -= 1
        elif ch == "=" and profondeur == 0 and not guillemets:
            return v[:i], v[i + 1:]
    return v, None


def _nombre(texte: str):
    """Entier si le texte n'a pas de point (garde le JSON propre : 1000 et pas 1000.0)."""
    f = float(texte)
    return int(f) if "." not in texte else f


def _type_de(t: str):
    """(description du type, optionnel) pour le texte de type d'une entrée."""
    t = t.strip()
    optionnel = t.endswith("?")
    if optionnel:
        t = t[:-1].strip()
    m = _RE_BORNES.match(t)
    if m:
        # `entier` : INDICATION pour l'écran seulement (le pont ne l'exige pas, voir _valeur) — les bornes sont écrites
        # sans point (0..253) -> le curseur va de 1 en 1. Sauf un intervalle d'amplitude ≤ 1 (0..1, 1..2) : c'est une
        # FRACTION écrite sans point — opacité et fond de layer.setProps, centres des flous (relevé t138 A2 : 39
        # champs du registre) ; un pas de 1 y rendrait le curseur inutilisable.
        bas, haut = _nombre(m.group(1)), _nombre(m.group(2))
        return {"type": "number", "min": bas, "max": haut,
                "entier": "." not in m.group(1) + m.group(2) and haut - bas > 1}, optionnel
    if t in _SCALAIRES:
        base = {"type": _SCALAIRES[t]}
        if base["type"] == "color":
            base["formes"] = ["hex"]
        return base, optionnel
    if t in _UNITES:
        return {"type": "number", "unite": t}, optionnel
    # La couleur est testée AVANT l'énumération : `"#rrggbb|[r,g,b,a]"` contient « | » et serait prise pour
    # une énumération de deux valeurs ("#rrggbb" et "[r,g,b,a]").
    if t == '"#rrggbb"':
        # Supposé : le registre 0.3.0 n'emploie pas de couleur nue (sans le type `"#rrggbb"`), seulement la forme hex.
        return {"type": "color", "formes": ["hex"]}, optionnel
    if t == '"#rrggbb|[r,g,b,a]"':
        return {"type": "color", "formes": ["hex", "rgba"]}, optionnel
    if t.startswith('"') and t.endswith('"') and "|" in t and t.count('"') == 2:
        valeurs = t[1:-1].split("|")
        ouverte = False
        # « Multiply|… » : le moteur accepte d'autres valeurs que celles écrites -> énumération ouverte.
        # Le « … » peut aussi être collé au dernier mot (« justify… »).
        while valeurs and valeurs[-1] in _POINTS_DE_SUSPENSION:
            valeurs.pop()
            ouverte = True
        if valeurs and valeurs[-1].endswith(_POINTS_DE_SUSPENSION):
            valeurs[-1] = valeurs[-1].rstrip(".…")
            ouverte = True
        decrit = {"type": "enum", "valeurs": valeurs}
        if ouverte:
            decrit["ouverte"] = True
        return decrit, optionnel
    if t.startswith("[") or t.startswith("{"):
        return {"type": "struct", "forme": t}, optionnel
    if re.fullmatch(r"(\d+\|)+\d+", t):
        return {"type": "enum", "valeurs": [int(x) for x in t.split("|")]}, optionnel
    m = re.fullmatch(r"int\[(\d+)\]", t)
    if m:
        return {"type": "intArray", "n": int(m.group(1))}, optionnel
    if re.fullmatch(r"[A-Za-z0-9 \[\]]+(\|[A-Za-z0-9 \[\]]+)+", t):
        return {"type": "union", "variantes": t.split("|")}, optionnel
    return {"type": "?", "brut": t}, optionnel


def _defaut(d):
    """Valeur par défaut écrite dans le registre. La prose (`foreground`, `first library pattern`) reste
    `{"texte": …}` : elle décrit un comportement du moteur, ce n'est pas une valeur qu'on peut envoyer."""
    d = d.strip().rstrip("?").strip()
    if re.fullmatch(_NUM, d):
        return _nombre(d)
    if d in ("true", "false"):
        return d == "true"
    if len(d) >= 2 and d.startswith('"') and d.endswith('"'):
        return d[1:-1]
    return {"texte": d}


def parser(texte) -> dict:
    """{"ok": bool, "champs": [{cle, type, optionnel, defaut?, min?, max?, entier?, unite?, valeurs?, ouverte?,
    formes?, variantes?, n?, forme?, note?, brut?}], "inconnus": [...], "queue": str}.
    `ok` est faux s'il reste un fragment non typé (`inconnus`) ou si le texte ne commence pas par un objet."""
    if not isinstance(texte, str) or not texte.strip():
        return {"ok": False, "champs": [], "inconnus": [], "queue": "", "raison": "description absente"}
    corps, queue = _objet_et_queue(texte)
    if corps is None:
        return {"ok": False, "champs": [], "inconnus": [], "queue": queue, "raison": "pas d'objet en tête"}
    champs, inconnus = [], []
    if corps.strip():
        for entree in _decouper(corps):
            entree = entree.strip()
            # « … » seul ou « …params of that adjustment kind » : l'objet admet d'autres clés, aucun champ à décrire.
            if not entree or entree.startswith(_POINTS_DE_SUSPENSION):
                continue
            m = _RE_CLE.match(entree)
            if not m:
                inconnus.append(entree)
                continue
            cle, reste = m.group(1), m.group(2)
            reste, note = _sans_note(reste)
            type_txt, defaut = _premier_egal(reste)
            decrit, optionnel = _type_de(type_txt)
            optionnel = optionnel or (defaut is not None and defaut.strip().endswith("?"))
            champ = {"cle": cle, **decrit, "optionnel": optionnel}
            if defaut is not None:
                champ["defaut"] = _defaut(defaut)
            if note:
                champ["note"] = note
            if decrit["type"] == "?":
                inconnus.append(entree)
            champs.append(champ)
    return {"ok": not inconnus, "champs": champs, "inconnus": inconnus, "queue": queue}


# Corrections EXPLICITES du registre, champ par champ (id de commande, clé) -> attributs remplacés. L'exposition est
# écrite « -20..20=0 » : bornes sans point, donc `entier` pour le parseur — or c'est une valeur en EV décimale (0.5
# relevé sur le moteur) que l'écran arrondirait à 1. Aucune heuristique sur le nom : `exposure` existe ailleurs
# (filtres, styles) avec un vrai sens entier.
CORRECTIONS_CHAMPS = {
    ("image.adjustments.exposure", "exposure"): {"entier": False, "unite": "ev"},
    ("layer.newAdjustmentLayer.exposure", "exposure"): {"entier": False, "unite": "ev"},
}


def structurer(commandes: list[dict]) -> dict[str, dict]:
    """id -> {"id", "label", "menu", "enabled", "champs", "ok", "inconnus", "queue"} pour tout le registre
    (une seule passe, ~776 entrées). `ok`/`inconnus` disent si la description est entièrement comprise."""
    sortie: dict[str, dict] = {}
    for c in commandes:
        d = parser(c.get("params"))
        champs = [{**ch, **CORRECTIONS_CHAMPS[(c["id"], ch.get("cle"))]} if (c["id"], ch.get("cle")) in CORRECTIONS_CHAMPS
                  else ch for ch in d["champs"]]
        sortie[c["id"]] = {"id": c["id"], "label": c.get("label"), "menu": c.get("menu") or [],
                           "enabled": c.get("enabled", True), "champs": champs, "ok": d["ok"],
                           "inconnus": d["inconnus"], "queue": d["queue"]}
    return sortie


# ── t138 A2 : la liste blanche du pont ──────────────────────────────────────────────────────────────────────────────
# Le moteur valide mal (relevé t138) : clés inconnues ignorées, mauvais type -> défaut en silence, `blend: 3` « ok »
# sans effet. Le pont n'admet donc que ce que le registre DÉCRIT : commande connue, clés connues, valeur du bon type
# et dans ses bornes. Les refus de fichiers de t136 restent derrière, en défense en profondeur.

# Clés qui désignent un fichier ou du contenu de fichier (comparées en minuscules) : refusées pour un champ texte ou
# opaque, à tout niveau. `data` : colorLookup.data = texte d'un fichier LUT en ligne, brush/gradient = base64.
CLES_CHEMIN = {"path", "file", "mappath", "dir", "directory", "folder", "input", "output", "droplet", "script", "data"}
CHAMP_ALIGN = {"cle": "align", "type": "enum", "optionnel": True,
               "valeurs": ["left", "center", "right", "justify", "justifyCenter", "justifyRight", "justifyAll"]}
# t156 : pour ces commandes, `path` est un TRACÉ VECTORIEL (objet {subpaths, fillRule, inverted}) ou le tracé de travail
# (« work »), jamais un fichier. L'exemption ne vaut que pour cette clé, un objet (ou « work ») ; son contenu passe quand
# même le parcours en profondeur (aucune chaîne « fichier », aucune clé de fichier imbriquée).
COMMANDES_TRACE = {"path.set", "shape.create", "shape.edit", "shape.presets.new"}


def _trace_vectoriel(cid, cle, v):
    return cid in COMMANDES_TRACE and cle == "path" and (isinstance(v, dict) or v == "work")
MAX_CHAINE_STR = 256
MAX_CHAINE_OPAQUE = 64
MAX_PROFONDEUR = 6
MAX_FEUILLES = 5000
# Une clé `points` (lasso, sélection rapide, courbes) porte un tracé à main levée : un lasso soigneux sur une grande
# image dépasse vite 2500 points (5000 nombres). Limite propre à cette clé, 5000 ailleurs.
MAX_FEUILLES_POINTS = 100_000

# Variante de `adjustment` dans doc.inspect -> kind des commandes layer.newAdjustmentLayer.<kind> (16 kinds).
KINDS = {"BrightnessContrast": "brightnessContrast", "Levels": "levels", "Curves": "curves", "Exposure": "exposure",
         "Vibrance": "vibrance", "HueSaturation": "hueSaturation", "ColorBalance": "colorBalance",
         "BlackWhite": "blackWhite", "PhotoFilter": "photoFilter", "ChannelMixer": "channelMixer", "Invert": "invert",
         "Posterize": "posterize", "Threshold": "threshold", "GradientMap": "gradientMap",
         "SelectiveColor": "selectiveColor", "ColorLookup": "colorLookup"}

# Les 28 modes de fusion du moteur : ids acceptés par layer.setProps et libellés anglais rendus par doc.inspect.
# Le moteur compare sans casse, espaces, tirets ni soulignés ; un style de calque accepte N'IMPORTE quelle chaîne et
# setProps accepte un nombre sans rien faire : d'où ce contrôle côté pont.
FUSIONS = ("passThrough", "normal", "dissolve", "darken", "multiply", "colorBurn", "linearBurn", "darkerColor",
           "lighten", "screen", "colorDodge", "linearDodge", "lighterColor", "overlay", "softLight", "hardLight",
           "vividLight", "linearLight", "pinLight", "hardMix", "difference", "exclusion", "subtract", "divide", "hue",
           "saturation", "color", "luminosity")
FUSIONS_LIBELLES = ("Pass Through", "Linear Dodge (Add)")    # seuls libellés qui ne se réduisent pas à leur id


def _norme_fusion(s: str) -> str:
    return re.sub(r"[\s\-_()]", "", s.lower())


_FUSIONS_NORMEES = {_norme_fusion(x) for x in FUSIONS + FUSIONS_LIBELLES}
_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def kind_de(calque) -> str | None:
    """Le kind d'un calque de réglage d'après sa variante `adjustment` (dict à une clé, ou chaîne « Invert ») ;
    None pour un calque qui n'est pas un réglage ou une variante inconnue."""
    a = calque.get("adjustment") if isinstance(calque, dict) else None
    if isinstance(a, str):
        return KINDS.get(a)
    if isinstance(a, dict) and len(a) == 1:
        return KINDS.get(next(iter(a)))
    return None


def _nombre_fini(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def _entier(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _fusion(cid, cle, v):
    if not isinstance(v, str) or _norme_fusion(v) not in _FUSIONS_NORMEES:
        raise ValueError(f"{cid} : {cle} : mode de fusion inconnu : {v!r}")


def _profond(cid, cle, v, fichier, niveau=1, compte=None):
    """Parcourt une valeur à tout niveau : chaînes « fichier » (sauf exemption), clés de fichier et clés `blend`
    imbriquées ; pour un champ opaque (`compte` non None) borne aussi profondeur, feuilles et longueur des chaînes."""
    if isinstance(v, (dict, list)):
        if compte is not None and niveau > MAX_PROFONDEUR:
            raise ValueError(f"{cid} : {cle} : profondeur > {MAX_PROFONDEUR}")
        items = v.items() if isinstance(v, dict) else ((None, w) for w in v)
        for k, w in items:
            if k is not None:
                if str(k).lower() in CLES_CHEMIN:
                    raise ValueError(f"{cid} : {cle}.{k} désigne un fichier — passe par les routes du Photolab")
                if str(k).lower() == "blend":
                    _fusion(cid, f"{cle}.{k}", w)
            _profond(cid, cle, w, fichier, niveau + 1, compte)
        return
    if compte is not None:
        compte[0] += 1
        if compte[0] > compte[1]:
            raise ValueError(f"{cid} : {cle} : plus de {compte[1]} valeurs")
        if isinstance(v, str) and len(v) > MAX_CHAINE_OPAQUE:
            raise ValueError(f"{cid} : {cle} : chaîne de plus de {MAX_CHAINE_OPAQUE} caractères")
    if isinstance(v, str) and fichier(v):
        raise ValueError(f"{cid} : {cle} : la valeur {v!r} désigne un fichier — passe par les routes du Photolab")


def _valeur(cid, cle, champ, v, fichier):
    t = champ["type"]
    exempte = False
    if cle.lower() == "blend":
        # AVANT le type : `blend: 3` est un mode de fusion inconnu (le moteur l'accepterait sans rien faire), et le
        # message le dit ainsi plutôt que « chaîne attendue ».
        _fusion(cid, cle, v)
    if t == "number":
        if not _nombre_fini(v):
            raise ValueError(f"{cid} : {cle} : nombre attendu, reçu {v!r}")
        if "min" in champ and not champ["min"] <= v <= champ["max"]:
            raise ValueError(f"{cid} : {cle} hors bornes ({champ['min']}..{champ['max']}) : {v!r}")
        # `entier` n'est qu'une INDICATION pour l'écran (pas du curseur) : il est déduit de l'écriture des bornes, pas
        # d'un type du moteur. Le pont admet donc tout nombre fini dans les bornes ; l'entier n'est exigé que pour les
        # types int, layerId, index, docIndex (décision du 08/10).
    elif t in ("int", "layerId", "index", "docIndex"):
        if not _entier(v) or (t != "int" and v < 0):
            raise ValueError(f"{cid} : {cle} : entier{'' if t == 'int' else ' ≥ 0'} attendu, reçu {v!r}")
    elif t == "bool":
        if not isinstance(v, bool):
            raise ValueError(f"{cid} : {cle} : booléen attendu, reçu {v!r}")
    elif t == "enum":
        if champ.get("ouverte"):
            if not isinstance(v, str) or len(v) > MAX_CHAINE_OPAQUE:
                raise ValueError(f"{cid} : {cle} : chaîne de {MAX_CHAINE_OPAQUE} caractères au plus attendue, reçu {v!r}")
        else:
            if isinstance(v, bool) or v not in champ["valeurs"]:
                raise ValueError(f"{cid} : {cle} : valeur hors liste {v!r} ({'|'.join(map(str, champ['valeurs']))})")
            # Une valeur de la liste du moteur est sûre… sauf si elle ressemble à un fichier (même définition que
            # partout, extensions comprises) : le registre écrit « /path/to/profile.icc » comme valeur d'exemple
            # (edit.profileInfo) — jamais envoyée telle quelle.
            exempte = not (isinstance(v, str) and fichier(v))
    elif t == "color":
        rgba = "rgba" in champ.get("formes", ())
        bon = isinstance(v, str) and bool(_HEX.fullmatch(v))
        if not bon and rgba and isinstance(v, list) and len(v) in (3, 4):
            bon = all(_nombre_fini(x) and 0 <= x <= 255 for x in v)
        if not bon:
            raise ValueError(f"{cid} : {cle} : couleur attendue (\"#rrggbb\"{' ou [r,g,b,a] en 0..255' if rgba else ''}), "
                             f"reçu {v!r}")
    elif t == "str":
        if cid == "filter.render.flame" and cle == "path":
            # t158 : le NOM d'un tracé du document (path.list) ; son existence est vérifiée par la route
            if not isinstance(v, str) or not 0 < len(v) <= MAX_NOM_TRACE or fichier(v):
                raise ValueError(f"{cid} : path : nom de tracé attendu (1 à {MAX_NOM_TRACE} caractères), reçu {v!r}")
            return
        if cle.lower() in CLES_CHEMIN and not _trace_vectoriel(cid, cle, v):
            raise ValueError(f"{cid} : {cle} désigne un fichier — passe par les routes du Photolab")
        if not isinstance(v, str) or len(v) > MAX_CHAINE_STR:
            raise ValueError(f"{cid} : {cle} : chaîne de {MAX_CHAINE_STR} caractères au plus attendue")
    else:                                                     # opaques : json, struct, intArray, union, ?
        if cle.lower() in CLES_CHEMIN and not _trace_vectoriel(cid, cle, v):
            raise ValueError(f"{cid} : {cle} désigne un fichier — passe par les routes du Photolab")
        _profond(cid, cle, v, fichier, compte=[0, MAX_FEUILLES_POINTS if cle == "points" else MAX_FEUILLES])
        return
    if not exempte:
        _profond(cid, cle, v, fichier)


def verifier(registre: dict, cid, params, kind=None, etat=None) -> dict:
    """Les paramètres tels quels si le registre du moteur admet `cid` avec eux ; sinon ValueError (message français).
    `kind` : pour layer.setAdjustment seulement, le kind du calque visé (lu par la route dans doc.inspect) — ses clés
    admises sont celles de layer.newAdjustmentLayer.<kind>, plus `layer`. `etat` : l'`adjustment` de ce calque dans
    doc.inspect (hueSaturation : bornes de la colorisation quand `colorize` n'est pas dans les paramètres)."""
    # Import tardif : PREFIXES_REFUSES reste DÉCLARÉ dans photolab_moteur.py (le banc JS menus 7.1 l'y relit), et ce
    # module reste lisible seul, sans cycle d'import (photolab_moteur importe celui-ci).
    from app.services import photolab_moteur as PM
    if not isinstance(cid, str) or not PM._ID_COMMANDE.fullmatch(cid):
        raise ValueError(f"commande illisible : {cid!r}")
    if cid.lower().startswith(PM.PREFIXES_REFUSES) and cid not in PM.PERMIS_REFUSES:
        raise ValueError(f"commande réservée aux routes du Photolab : {cid}")
    if cid not in registre:
        raise ValueError(f"commande inconnue du moteur : {cid}")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError(f"{cid} : les paramètres doivent être un objet")
    if cid in VERIFS_T158:
        # t158 : clés et formes nommées une à une (registre trop vague : « <builtin id> », json, struct)
        VERIFS_T158[cid](cid, params)
        return params
    champs = {c["cle"]: c for c in registre[cid]["champs"]}
    if cid.startswith("layer.layerStyle."):
        # honorés par le moteur bien que non décrits dans 9 styles sur 10 (relevé t138)
        champs.setdefault("layer", {"cle": "layer", "type": "layerId", "optionnel": True})
        champs.setdefault("enabled", {"cle": "enabled", "type": "bool", "optionnel": True})
    if cid == "layer.setAdjustment":
        modele = registre.get(f"layer.newAdjustmentLayer.{kind}") if kind in KINDS.values() else None
        if modele is None:
            raise ValueError(f"{cid} : type de réglage inconnu : {kind!r}")
        champs = {"layer": champs.get("layer") or {"cle": "layer", "type": "layerId", "optionnel": True},
                  **{c["cle"]: c for c in modele["champs"]}}
    reglage = kind if cid == "layer.setAdjustment" else _kind_de_commande(cid)
    if reglage == "selectiveColor":
        # Le registre ne décrit que `reds` ; les huit autres gammes sont dans sa note (relevé A4 : le moteur les accepte).
        for g in GAMMES_SELECTIVE:
            champs.setdefault(g, {"cle": g, "type": "json", "optionnel": True})
    if cid == "type.create" and "type.setStyle" in registre:
        # t156 : le registre résume ses clés de caractère et de paragraphe (« …character keys ») ; ce sont celles de
        # type.setStyle (même modèle, relevé sur le vrai moteur), sans `layer` ni `range`.
        for c in registre["type.setStyle"]["champs"]:
            if c["cle"] not in ("layer", "range"):
                champs.setdefault(c["cle"], c)
    if cid in ("type.setStyle", "type.create"):
        # t156 : « align » n'est pas décrit pour setStyle et son énumération est tronquée (« justify… ») pour create :
        # la liste complète du registre de setStyle (texte de ses paramètres), relevée sur le vrai moteur.
        champs["align"] = CHAMP_ALIGN
    if cid in PROFILS_MODE:
        # t158 : « <builtin id>|working|/path/to/profile.icc » au registre — le chemin .icc est la lecture arbitraire
        # relevée au t138. Seuls les profils INTÉGRÉS au moteur de cet espace colorimétrique (edit.profileInfo).
        champs["profile"] = {"cle": "profile", "type": "enum", "valeurs": list(PROFILS_MODE[cid]), "optionnel": True}
    if cid == "tools.setBrush":
        # Le registre résume ses champs en « …BrushSettings fields » : seule la forme de la pointe est admise (t155).
        for c in CHAMPS_POINTE:
            champs.setdefault(c["cle"], c)
    if cid == "select.refineEdge":
        # t157 : rayon et contour progressif sont des « px » sans bornes au registre ; le moteur les borne en silence
        # (smartselect_cmds.rs : 0..250 et 0..1000) — le pont refuse au-delà.
        for c in CHAMPS_AFFINER:
            champs[c["cle"]] = {**champs.get(c["cle"], {}), **c}
    if cid == "filter.filterGallery":
        # t157 : `effects`, `foreground`, `background` sont des « json » au registre ; le moteur ramène EN SILENCE une
        # valeur hors bornes au défaut du filtre (99 -> 4) : chaque effet est vérifié contre filter.gallery.<clé>.
        _galerie(registre, cid, params)
        return params
    ctx = {"colorize": _colorise(params, etat)}
    for k, v in params.items():
        champ = champs.get(k)
        if champ is None:
            raise ValueError(f"{cid} : paramètre inconnu : {k}")
        if reglage == "hueSaturation" and ctx["colorize"] and k in BORNES_COLORIZE:
            # Colorisation : teinte 0..360 et saturation 0..100 (le registre ne donne que les bornes hors colorisation)
            champ = {**champ, "min": BORNES_COLORIZE[k][0], "max": BORNES_COLORIZE[k][1]}
        _valeur(cid, k, champ, v, PM._valeur_fichier)
        schema = SCHEMAS.get((reglage, k))
        if schema is not None:
            schema(cid, k, v, champs, ctx)
    return params


# ── t157 : Sélectionner et masquer, la pile de la Galerie de filtres ────────────────────────────────────────────────
CHAMPS_AFFINER = ({"cle": "radius", "type": "number", "min": 0, "max": 250, "optionnel": True},
                  {"cle": "feather", "type": "number", "min": 0, "max": 1000, "optionnel": True})

MAX_EFFETS_GALERIE = 20
CLES_EFFET = {"filter", "params", "visible"}


def cles_galerie(registre: dict) -> set[str]:
    """Les clés des filtres de la galerie (`filter.gallery.<clé>` du registre)."""
    return {c[len("filter.gallery."):] for c in registre if c.startswith("filter.gallery.")}


def _couleur_01(cid, cle, v):
    # glowColor : [r,g,b(,a)] en 0..1 (l'amont l'écrit [r,g,b,1]) ; une couleur 0..255 serait saturée en silence.
    if not (isinstance(v, list) and len(v) in (3, 4) and all(_nombre_fini(x) and 0 <= x <= 1 for x in v)):
        raise ValueError(f"{cid} : {cle} : couleur [r, g, b(, a)] en 0..1 attendue, reçu {v!r}")


def _galerie(registre: dict, cid, params: dict):
    from app.services import photolab_moteur as PM
    for k in params:
        if k not in ("effects", "foreground", "background", "list", "layer"):
            raise ValueError(f"{cid} : paramètre inconnu : {k}")
    if params.get("list") is True and set(params) == {"list"}:
        return
    if "list" in params:
        raise ValueError(f"{cid} : « list » se demande seul (catalogue)")
    if "layer" in params and (not _entier(params["layer"]) or params["layer"] < 0):
        raise ValueError(f"{cid} : layer : entier ≥ 0 attendu")
    for k in ("foreground", "background"):
        if k in params and not (isinstance(params[k], str) and _HEX.fullmatch(params[k])):
            raise ValueError(f"{cid} : {k} : couleur \"#rrggbb\" attendue, reçu {params[k]!r}")
    effets = params.get("effects")
    if not isinstance(effets, list) or not 1 <= len(effets) <= MAX_EFFETS_GALERIE:
        raise ValueError(f"{cid} : effects : de 1 à {MAX_EFFETS_GALERIE} effets attendus")
    connus = cles_galerie(registre)
    for i, e in enumerate(effets):
        if not isinstance(e, dict):
            raise ValueError(f"{cid} : effet {i} : objet {{filter, params, visible}} attendu")
        inconnues = set(e) - CLES_EFFET
        if inconnues:
            raise ValueError(f"{cid} : effet {i} : clé inconnue : {', '.join(sorted(map(str, inconnues)))}")
        f = e.get("filter")
        if f not in connus:
            raise ValueError(f"{cid} : effet {i} : filtre de la galerie inconnu : {f!r}")
        if "visible" in e and not isinstance(e["visible"], bool):
            raise ValueError(f"{cid} : effet {i} : visible : booléen attendu")
        p = e.get("params", {})
        if not isinstance(p, dict):
            raise ValueError(f"{cid} : effet {i} : params : objet attendu")
        sous = f"filter.gallery.{f}"
        champs = {c["cle"]: c for c in registre[sous]["champs"]}
        for k, v in p.items():
            champ = champs.get(k)
            if champ is None:
                raise ValueError(f"{sous} : paramètre inconnu : {k}")
            if k in ("glowColor", "foreground", "background"):
                if not (isinstance(v, str) and _HEX.fullmatch(v)):      # « #rrggbb » ou [r,g,b(,a)] en 0..1
                    _couleur_01(sous, k, v)
                continue
            _valeur(sous, k, champ, v, PM._valeur_fichier)


# ── Schémas des champs `json` des réglages (relevé A4 sur le vrai moteur) ───────────────────────────────────────────
# Le moteur ACCEPTE puis ignore ou fausse en silence les mauvaises formes : selectiveColor `reds` en objet {cyan…} =
# tout à zéro ; gradientMap `stops` en triplets [r,g,b] = dégradé blanc ; courbes à x non croissants = points perdus.
# Valeurs hors bornes : le moteur borne (gamma 50 -> 9.99, hue 500 -> 180), le pont refuse quand même.
GAMMES_SELECTIVE = ("yellows", "greens", "cyans", "blues", "magentas", "whites", "neutrals", "blacks")


BORNES_COLORIZE = {"hue": (0, 360), "saturation": (0, 100)}

# t155 : champs de tools.setBrush que l'écran envoie (Paramètres de pinceau › Forme de la pointe, barre d'options),
# bornes de l'amont (B §3.9, B §8 : taille 1..5000, espacement 1..1000 %) et unités de brush.get (0..1, espacement
# en fraction de la taille). Les autres sections (dynamique, texture, double pointe…) restent refusées.
CHAMPS_POINTE = (
    {"cle": "size", "type": "number", "min": 1, "max": 5000, "optionnel": True},
    {"cle": "hardness", "type": "number", "min": 0, "max": 1, "optionnel": True},
    {"cle": "spacing", "type": "number", "min": 0.01, "max": 10, "optionnel": True},
    {"cle": "spacingEnabled", "type": "bool", "optionnel": True},
    {"cle": "angle", "type": "number", "min": -180, "max": 180, "optionnel": True},
    {"cle": "roundness", "type": "number", "min": 0.01, "max": 1, "optionnel": True},
    {"cle": "flipX", "type": "bool", "optionnel": True},
    {"cle": "flipY", "type": "bool", "optionnel": True},
    {"cle": "opacity", "type": "number", "min": 0, "max": 1, "optionnel": True},
    {"cle": "flow", "type": "number", "min": 0, "max": 1, "optionnel": True},
)


def _kind_de_commande(cid):
    """Le nom de réglage visé par `layer.newAdjustmentLayer.<x>` (un des 16 kinds) ou `image.adjustments.<x>` (les 16
    kinds, mais aussi les destructifs seuls : hdrToning, replaceColor, matchColor…) ; None sinon."""
    if cid.startswith("layer.newAdjustmentLayer."):
        k = cid[len("layer.newAdjustmentLayer."):]
        return k if k in KINDS.values() else None
    if cid.startswith("image.adjustments."):
        k = cid[len("image.adjustments."):]
        return k if "." not in k else None                 # image.adjustments.colorLookup.list n'est pas un réglage
    return None


def _colorise(params, etat) -> bool:
    """hueSaturation en mode colorisation ? `colorize` des paramètres PRIME ; sinon l'état actuel du calque visé
    (`adjustment` de doc.inspect, lu par la route) pour layer.setAdjustment."""
    if "colorize" in params:
        return params["colorize"] is True
    h = etat.get("HueSaturation") if isinstance(etat, dict) else None
    return isinstance(h, dict) and h.get("colorize") is True


def _s_couleur_hex(cid, cle, v, champs, ctx):
    # Relevé A4 : le moteur n'agit que sur "#rrggbb" (ou "rrggbb") ; [r,g,b], "#rgb" et les noms sont ignorés en silence.
    if not (isinstance(v, str) and _HEX.fullmatch(v)):
        raise ValueError(f"{cid} : {cle} : couleur \"#rrggbb\" attendue (les autres formes seraient ignorées), reçu {v!r}")


def _s_calque_source(cid, cle, v, champs, ctx):
    # Relevé A4 : id d'un calque du document SOURCE (inconnu = erreur du moteur) ; chaîne, négatif, flottant : acceptés
    # puis sans sens — refusés ici.
    if not _entier(v) or v < 0:
        raise ValueError(f"{cid} : {cle} : id de calque (entier ≥ 0) attendu, reçu {v!r}")


def _liste_de(cid, cle, v, n, nom="nombres"):
    if not isinstance(v, list) or len(v) != n:
        raise ValueError(f"{cid} : {cle} : tableau de {n} {nom} attendu, reçu {v!r}")


def _bornes_nombres(cid, cle, v, lo, hi):
    for x in v:
        if not _nombre_fini(x) or not lo <= x <= hi:
            raise ValueError(f"{cid} : {cle} : nombres dans {lo}..{hi} attendus, reçu {v!r}")


def _s_selective(cid, cle, v, champs, ctx):
    _liste_de(cid, cle, v, 4)
    _bornes_nombres(cid, cle, v, -100, 100)


def _s_stops(cid, cle, v, champs, ctx):
    if not isinstance(v, list) or not 2 <= len(v) <= 64:
        raise ValueError(f"{cid} : {cle} : 2 à 64 points [position, \"#rrggbb\"] attendus")
    for p in v:
        if not (isinstance(p, list) and len(p) == 2 and _nombre_fini(p[0]) and 0 <= p[0] <= 1
                and isinstance(p[1], str) and _HEX.fullmatch(p[1])):
            raise ValueError(f"{cid} : {cle} : point [position 0..1, \"#rrggbb\"] attendu, reçu {p!r} "
                             "(des triplets [r,g,b] donneraient du blanc)")


def _s_courbe(cid, cle, v, champs, ctx):
    if not isinstance(v, list) or not 2 <= len(v) <= 19:
        raise ValueError(f"{cid} : {cle} : 2 à 19 points [x, y] attendus")
    x_prec = -1
    for p in v:
        if not (isinstance(p, list) and len(p) == 2 and all(_entier(c) and 0 <= c <= 255 for c in p)):
            raise ValueError(f"{cid} : {cle} : point [x, y] entiers 0..255 attendu, reçu {p!r}")
        if p[0] <= x_prec:
            raise ValueError(f"{cid} : {cle} : les x doivent croître strictement ({p[0]} après {x_prec})")
        x_prec = p[0]


def _s_niveaux(cid, cle, v, champs, ctx):
    if not isinstance(v, dict):
        raise ValueError(f"{cid} : {cle} : objet {{inBlack, gamma, inWhite, outBlack, outWhite}} attendu")
    for k, x in v.items():
        c = champs.get(k)                                  # bornes du composite (même nom de clé au niveau racine)
        if c is None or "min" not in c or k not in ("inBlack", "gamma", "inWhite", "outBlack", "outWhite"):
            raise ValueError(f"{cid} : {cle}.{k} : clé inconnue (inBlack, gamma, inWhite, outBlack, outWhite)")
        if not _nombre_fini(x) or not c["min"] <= x <= c["max"]:
            raise ValueError(f"{cid} : {cle}.{k} hors bornes ({c['min']}..{c['max']}) : {x!r}")


def _s_mixeur(cid, cle, v, champs, ctx):
    _liste_de(cid, cle, v, 4)
    _bornes_nombres(cid, cle, v, -200, 200)


def _s_equilibre(cid, cle, v, champs, ctx):
    _liste_de(cid, cle, v, 3)
    _bornes_nombres(cid, cle, v, -100, 100)


def _s_gamme_teinte(cid, cle, v, champs, ctx):
    if not isinstance(v, dict):
        raise ValueError(f"{cid} : {cle} : objet {{hue, saturation, lightness, range}} attendu")
    for k, x in v.items():
        if k == "range":
            _liste_de(cid, f"{cle}.range", x, 4)
            _bornes_nombres(cid, f"{cle}.range", x, -720, 720)
        elif k in ("hue", "saturation", "lightness"):
            lo, hi = (-180, 180) if k == "hue" else (-100, 100)
            if not _nombre_fini(x) or not lo <= x <= hi:
                raise ValueError(f"{cid} : {cle}.{k} hors bornes ({lo}..{hi}) : {x!r}")
        else:
            raise ValueError(f"{cid} : {cle}.{k} : clé inconnue (hue, saturation, lightness, range)")


SCHEMAS = {("gradientMap", "stops"): _s_stops, ("replaceColor", "color"): _s_couleur_hex,
           ("matchColor", "sourceLayer"): _s_calque_source, ("hdrToning", "curve"): _s_courbe}
SCHEMAS.update({("selectiveColor", g): _s_selective for g in ("reds",) + GAMMES_SELECTIVE})
SCHEMAS.update({("curves", k): _s_courbe for k in ("points", "red", "green", "blue")})
SCHEMAS.update({("levels", k): _s_niveaux for k in ("red", "green", "blue")})
SCHEMAS.update({("channelMixer", k): _s_mixeur for k in ("red", "green", "blue", "gray")})
SCHEMAS.update({("colorBalance", k): _s_equilibre for k in ("shadows", "midtones", "highlights")})
SCHEMAS.update({("hueSaturation", k): _s_gamme_teinte for k in ("reds", "yellows", "greens", "cyans", "blues", "magentas")})


# ── t158 : Image › Mode et Informations sur le fichier ──────────────────────────────────────────────────────────────
# Profils intégrés du moteur 0.3.0 par espace (edit.profileInfo, relevé 09/10 ; le banc les compare au vrai moteur).
PROFILS_MODE = {
    "image.mode.rgb": ("working", "srgb", "display-p3", "adobe-rgb-compat", "prophoto-compat", "linear-srgb", "rec2020"),
    "image.mode.grayscale": ("working", "sgray", "gray-gamma-2.2"),
    "image.mode.cmyk": ("working", "coated-cmyk"),
    "image.mode.lab": ("working", "lab-d50"),
}
MAX_NOM_TRACE = 64
ENCRES_PAR_TYPE = {"monotone": 1, "duotone": 2, "tritone": 3, "quadtone": 4}
MAX_POINTS_COURBE = 16
TABLES = ("custom", "blackBody", "grayscale", "spectrum", "systemMac", "systemWindows", "web")
MAX_TEXTE_INFO = 2000
MAX_MOTS_CLES = 64
STATUTS_COPYRIGHT = ("unknown", "copyrighted", "publicDomain")
_URL = re.compile(r"https?://[^\s\"'<>\\]{1,500}")
_INDEX_TABLE = re.compile(r"(0|[1-9][0-9]{0,2})")


def _cles(cid, params, admises):
    inconnues = sorted(set(params) - set(admises))
    if inconnues:
        raise ValueError(f"{cid} : paramètre inconnu : {inconnues[0]}")


def _hex(cid, cle, v):
    if not (isinstance(v, str) and _HEX.fullmatch(v)):
        raise ValueError(f"{cid} : {cle} : couleur « #rrggbb » attendue, reçu {v!r}")


def _v_bichromie(cid, params):
    """Bichromie : `type` (défaut duotone) et EXACTEMENT autant d'encres — le moteur complète ou tronque en silence."""
    _cles(cid, params, ("type", "inks"))
    t = params.get("type", "duotone")
    if t not in ENCRES_PAR_TYPE:
        raise ValueError(f"{cid} : type hors liste {t!r} ({'|'.join(ENCRES_PAR_TYPE)})")
    encres = params.get("inks")
    if not isinstance(encres, list) or len(encres) != ENCRES_PAR_TYPE[t]:
        raise ValueError(f"{cid} : inks : {ENCRES_PAR_TYPE[t]} encre(s) attendue(s) pour {t}")
    for k, e in enumerate(encres):
        if not isinstance(e, dict):
            raise ValueError(f"{cid} : inks[{k}] : objet attendu")
        _cles(cid, e, ("name", "color", "curve"))
        nom = e.get("name")
        if not isinstance(nom, str) or not 0 < len(nom) <= MAX_CHAINE_OPAQUE:
            raise ValueError(f"{cid} : inks[{k}].name : nom de 1 à {MAX_CHAINE_OPAQUE} caractères attendu")
        _hex(cid, f"inks[{k}].color", e.get("color"))
        if "curve" in e:
            c = e["curve"]
            if not isinstance(c, list) or not 2 <= len(c) <= MAX_POINTS_COURBE:
                raise ValueError(f"{cid} : inks[{k}].curve : 2 à {MAX_POINTS_COURBE} points attendus")
            avant = -1
            for p in c:
                if not (isinstance(p, list) and len(p) == 2 and all(_nombre_fini(x) and 0 <= x <= 100 for x in p)):
                    raise ValueError(f"{cid} : inks[{k}].curve : points [entrée, sortie] en 0..100 attendus")
                if p[0] <= avant:
                    raise ValueError(f"{cid} : inks[{k}].curve : entrées strictement croissantes attendues")
                avant = p[0]


def _v_table(cid, params):
    """Table des couleurs : sans clé, LIT la table (aucune étape) ; `colors` (256 au plus), `entries` {index: couleur},
    `transparent` (index ou null)."""
    _cles(cid, params, ("table", "colors", "entries", "transparent"))
    if "table" in params and params["table"] not in TABLES:
        raise ValueError(f"{cid} : table hors liste {params['table']!r}")
    if "colors" in params:
        c = params["colors"]
        if not isinstance(c, list) or not 1 <= len(c) <= 256:
            raise ValueError(f"{cid} : colors : 1 à 256 couleurs attendues")
        for k, v in enumerate(c):
            _hex(cid, f"colors[{k}]", v)
    if "entries" in params:
        e = params["entries"]
        if not isinstance(e, dict) or not 1 <= len(e) <= 256:
            raise ValueError(f"{cid} : entries : objet de 1 à 256 entrées attendu")
        for k, v in e.items():
            if not (isinstance(k, str) and _INDEX_TABLE.fullmatch(k) and int(k) <= 255):
                raise ValueError(f"{cid} : entries : index 0..255 attendu, reçu {k!r}")
            _hex(cid, f"entries[{k}]", v)
    if "transparent" in params:
        t = params["transparent"]
        if t is not None and not (_entier(t) and 0 <= t <= 255):
            raise ValueError(f"{cid} : transparent : index 0..255 ou null attendu")


def _v_infos(cid, params):
    """Informations sur le fichier : du TEXTE rangé dans le document (aucun n'est lu comme un chemin par le moteur),
    borné ; l'URL du copyright en http(s) seulement ; sans clé, une lecture."""
    textes = ("title", "author", "authorTitle", "description", "copyright")
    _cles(cid, params, textes + ("keywords", "copyrightStatus", "copyrightUrl"))
    for k in textes:
        if k in params and (not isinstance(params[k], str) or len(params[k]) > MAX_TEXTE_INFO):
            raise ValueError(f"{cid} : {k} : texte de {MAX_TEXTE_INFO} caractères au plus attendu")
    if "keywords" in params:
        m = params["keywords"]
        if isinstance(m, str):
            m = [m]
        if not isinstance(m, list) or len(m) > MAX_MOTS_CLES or \
                not all(isinstance(x, str) and len(x) <= MAX_CHAINE_OPAQUE for x in m):
            raise ValueError(f"{cid} : keywords : {MAX_MOTS_CLES} mots-clés de {MAX_CHAINE_OPAQUE} caractères au plus")
    if "copyrightStatus" in params and params["copyrightStatus"] not in STATUTS_COPYRIGHT:
        raise ValueError(f"{cid} : copyrightStatus hors liste {params['copyrightStatus']!r}")
    if "copyrightUrl" in params:
        u = params["copyrightUrl"]
        if not isinstance(u, str) or (u and not _URL.fullmatch(u)):
            raise ValueError(f"{cid} : copyrightUrl : adresse http(s) attendue, reçu {u!r}")


# t159 : préréglages. Le gestionnaire agit par INDEX dans une liste que le moteur rend (`list`) ; l'échange porte des
# DONNÉES (le format que `export` rend), jamais un chemin : `edit.presets.migratePresets` {path} reste refusée.
GENRES_GESTIONNAIRE = ("brushes", "customShapes", "patterns")
GENRES_ECHANGE = ("brushes", "customShapes")
MAX_NOM_PRESET = 64
MAX_INDEX_PRESET = 10_000
MAX_PRESETS_ECHANGE = 500
MAX_OCTETS_ECHANGE = 2_000_000
MAX_PROFONDEUR_ECHANGE = 12
MAX_CHAINE_ECHANGE = 256
_BASE64 = re.compile(r"[A-Za-z0-9+/]*={0,2}")


def _index(cid, cle, v):
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= MAX_INDEX_PRESET:
        raise ValueError(f"{cid} : {cle} : index entier de 0 à {MAX_INDEX_PRESET} attendu")


def _v_gestionnaire(cid, params):
    """Gestionnaire de préréglages : list | rename (index, newName) | delete (index) | move (index, to)."""
    action = params.get("action")
    admises = {"list": (), "rename": ("index", "newName"), "delete": ("index",), "move": ("index", "to")}
    if action not in admises:
        raise ValueError(f"{cid} : action : une valeur parmi {'|'.join(admises)}")
    _cles(cid, params, ("action", "kind") + admises[action])
    if params.get("kind") not in GENRES_GESTIONNAIRE:
        raise ValueError(f"{cid} : kind : une valeur parmi {'|'.join(GENRES_GESTIONNAIRE)}")
    for k in admises[action]:
        if k not in params:
            raise ValueError(f"{cid} : {k} manquant pour {action}")
    for k in ("index", "to"):
        if k in params:
            _index(cid, k, params[k])
    if "newName" in params:
        n = params["newName"]
        if not isinstance(n, str) or not n.strip() or len(n) > MAX_NOM_PRESET or any(ord(c) < 32 for c in n):
            raise ValueError(f"{cid} : newName : 1 à {MAX_NOM_PRESET} caractères, sur une ligne")


def _donnees_echange(cid, v, ou, niveau, compte):
    if niveau > MAX_PROFONDEUR_ECHANGE:
        raise ValueError(f"{cid} : {ou} : profondeur > {MAX_PROFONDEUR_ECHANGE}")
    if isinstance(v, dict):
        for k, w in v.items():
            kl = str(k).lower()
            if kl == "data" and isinstance(w, str) and _BASE64.fullmatch(w):
                continue                                   # pointe échantillonnée : des octets en base64
            if kl in CLES_CHEMIN:
                raise ValueError(f"{cid} : {ou}.{k} désigne un fichier — refusé dans un échange de préréglages")
            _donnees_echange(cid, w, f"{ou}.{k}", niveau + 1, compte)
    elif isinstance(v, list):
        for i, w in enumerate(v):
            _donnees_echange(cid, w, f"{ou}[{i}]", niveau + 1, compte)
    elif isinstance(v, str):
        from app.services import photolab_moteur as PM
        if len(v) > MAX_CHAINE_ECHANGE or PM._valeur_fichier(v):
            raise ValueError(f"{cid} : {ou} : texte refusé (fichier, ou plus de {MAX_CHAINE_ECHANGE} caractères)")
    elif not (v is None or isinstance(v, (bool, int, float))):
        raise ValueError(f"{cid} : {ou} : valeur illisible")


def _v_echange(cid, params):
    """Exporter / importer des préréglages : export {kinds?, includeBuiltins?} ; import {data, kinds?} où `data` est ce
    que l'export a rendu (format photocraft-presets, version 1), borné, sans aucune clé ni valeur de fichier."""
    action = params.get("action")
    if action not in ("export", "import"):
        raise ValueError(f"{cid} : action : export ou import")
    _cles(cid, params, ("action", "kinds", "includeBuiltins") if action == "export" else ("action", "kinds", "data"))
    if "kinds" in params:
        k = params["kinds"]
        if not isinstance(k, list) or not k or any(x not in GENRES_ECHANGE for x in k) or len(set(k)) != len(k):
            raise ValueError(f"{cid} : kinds : liste parmi {'|'.join(GENRES_ECHANGE)}")
    if "includeBuiltins" in params and not isinstance(params["includeBuiltins"], bool):
        raise ValueError(f"{cid} : includeBuiltins : booléen attendu")
    if action == "export":
        return
    d = params.get("data")
    if not isinstance(d, dict):
        raise ValueError(f"{cid} : data : le contenu d'un fichier de préréglages exporté attendu")
    _cles(cid, d, ("format", "version") + GENRES_ECHANGE)
    if d.get("format") != "photocraft-presets" or d.get("version") != 1 or isinstance(d.get("version"), bool):
        raise ValueError(f"{cid} : data : ce n'est pas un fichier de préréglages (format photocraft-presets, version 1)")
    try:
        taille = len(json.dumps(d, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        raise ValueError(f"{cid} : data : illisible")
    if taille > MAX_OCTETS_ECHANGE:
        raise ValueError(f"{cid} : data : {MAX_OCTETS_ECHANGE // 1_000_000} Mo au plus")
    for g in GENRES_ECHANGE:
        liste = d.get(g, [])
        if not isinstance(liste, list) or len(liste) > MAX_PRESETS_ECHANGE:
            raise ValueError(f"{cid} : data.{g} : liste de {MAX_PRESETS_ECHANGE} préréglages au plus")
        for i, item in enumerate(liste):
            if not isinstance(item, dict):
                raise ValueError(f"{cid} : data.{g}[{i}] : objet attendu")
            _donnees_echange(cid, item, f"data.{g}[{i}]", 1, None)


# t160 : comptage, notes, tranches, journal des mesures. Le registre résume leurs formes alternatives (« {index} |
# {x, y} ») et leurs options (« plus Slice Options… ») : chaque commande est décrite ici clé par clé. Les textes (note,
# auteur, nom de groupe, options de tranche) sont rangés dans le document, jamais lus comme chemin : bornés, sur
# l'exemple de file.fileInfo, sans le refus « fichier » (« voir a/b.png » est une note légitime).
MAX_COORD = 1_000_000
MAX_TEXTE_NOTE = 4000
MAX_NOM_COURT = 128
TYPES_TRANCHE = ("image", "noImage", "table")
OPTIONS_TRANCHE = {"name": MAX_NOM_COURT, "url": 2048, "target": MAX_NOM_COURT, "message": 512, "alt": 512, "cellText": MAX_TEXTE_NOTE}


def _borne(cid, cle, v, a=-MAX_COORD, b=MAX_COORD, entier=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or (entier and not float(v).is_integer()):
        raise ValueError(f"{cid} : {cle} : {'entier' if entier else 'nombre'} attendu")
    if not a <= v <= b:
        raise ValueError(f"{cid} : {cle} : entre {a} et {b}")


def _point(cid, cle, v):
    if not isinstance(v, list) or len(v) != 2:
        raise ValueError(f"{cid} : {cle} : [x, y] attendu")
    for i, x in enumerate(v):
        _borne(cid, f"{cle}[{i}]", x)


def _texte(cid, cle, v, n):
    if not isinstance(v, str) or len(v) > n or any(ord(c) < 32 and c not in "\n\t" for c in v):
        raise ValueError(f"{cid} : {cle} : texte de {n} caractères au plus attendu")


def _booleen(cid, cle, v):
    if not isinstance(v, bool):
        raise ValueError(f"{cid} : {cle} : booléen attendu")


def _une_forme(cid, params, formes):
    """`formes` : listes de clés obligatoires ; la première présente en entier est rendue."""
    trouvees = [f for f in formes if all(k in params for k in f)]
    if not trouvees:
        raise ValueError(f"{cid} : il faut " + " ou ".join("{" + ", ".join(f) + "}" for f in formes))
    return trouvees[0]


def _v_comptage(cid, params):
    op = cid.split(".", 1)[1]
    admises = {"add": ("x", "y", "group"), "remove": ("index", "group", "x", "y", "radius"), "move": ("index", "group", "x", "y", "to"),
               "clear": ("group",), "newGroup": ("name", "color"), "deleteGroup": ("group",),
               "setGroup": ("group", "name", "color", "markerSize", "labelSize", "visible", "active")}[op]
    _cles(cid, params, admises)
    if op == "add":
        _une_forme(cid, params, [("x", "y")])
    if op in ("remove", "move"):
        f = _une_forme(cid, params, [("index",), ("x", "y")])
        if f == ("index",) and ("x" in params or "y" in params):
            raise ValueError(f"{cid} : index ou {{x, y}}, pas les deux")
        if f == ("x", "y") and "group" in params:
            raise ValueError(f"{cid} : group ne va qu'avec index")
        if f == ("index",) and "radius" in params:
            raise ValueError(f"{cid} : radius ne va qu'avec {{x, y}}")
    if op == "move":
        if "to" not in params:
            raise ValueError(f"{cid} : to manquant")
        _point(cid, "to", params["to"])
    for k in ("x", "y"):
        if k in params:
            _borne(cid, k, params[k])
    if "index" in params:
        _borne(cid, "index", params["index"], 0, 100_000, True)
    if "radius" in params:
        _borne(cid, "radius", params["radius"], 0, 1000)
    if "group" in params and not (op == "clear" and params["group"] == "all"):
        _borne(cid, "group", params["group"], 0, 1000, True)
    if "name" in params:
        _texte(cid, "name", params["name"], MAX_NOM_COURT)
    if "color" in params:
        _hex(cid, "color", params["color"])
    if "markerSize" in params:
        _borne(cid, "markerSize", params["markerSize"], 1, 10, True)
    if "labelSize" in params:
        _borne(cid, "labelSize", params["labelSize"], 8, 72, True)
    for k in ("visible", "active"):
        if k in params:
            _booleen(cid, k, params[k])


def _v_notes(cid, params):
    op = cid.split(".", 1)[1]
    if op == "delete":
        _cles(cid, params, ("index", "all"))
        f = _une_forme(cid, params, [("index",), ("all",)])
        if len(params) != 1:
            raise ValueError(f"{cid} : index ou all, pas les deux")
        if f == ("all",):
            if params["all"] is not True:
                raise ValueError(f"{cid} : all : true attendu")
        else:
            _borne(cid, "index", params["index"], 0, 100_000, True)
        return
    admises = ("x", "y", "text", "author", "color", "open") + (("index",) if op == "set" else ())
    _cles(cid, params, admises)
    if op == "add":
        _une_forme(cid, params, [("x", "y")])
    else:
        _une_forme(cid, params, [("index",)])
        _borne(cid, "index", params["index"], 0, 100_000, True)
    for k in ("x", "y"):
        if k in params:
            _borne(cid, k, params[k])
    if "text" in params:
        _texte(cid, "text", params["text"], MAX_TEXTE_NOTE)
    if "author" in params:
        _texte(cid, "author", params["author"], MAX_NOM_COURT)
    if "color" in params:
        _hex(cid, "color", params["color"])
    if "open" in params:
        _booleen(cid, "open", params["open"])


def _rect_tranche(cid, params):
    if "rect" in params:
        if any(k in params for k in ("x", "y", "width", "height")):
            raise ValueError(f"{cid} : rect ou x, y, width, height, pas les deux")
        r = params["rect"]
        if not isinstance(r, list) or len(r) != 4:
            raise ValueError(f"{cid} : rect : [x, y, largeur, hauteur] attendu")
        for i, v in enumerate(r):
            _borne(cid, f"rect[{i}]", v, -MAX_COORD if i < 2 else 1, MAX_COORD)
        return True
    xywh = [k for k in ("x", "y", "width", "height") if k in params]
    if xywh and len(xywh) != 4:
        raise ValueError(f"{cid} : x, y, width, height vont ensemble")
    for k in xywh:
        _borne(cid, k, params[k], -MAX_COORD if k in ("x", "y") else 1, MAX_COORD)
    return bool(xywh)


def _options_tranche(cid, params):
    for k, n in OPTIONS_TRANCHE.items():
        if k in params:
            _texte(cid, k, params[k], n)
    if "kind" in params and params["kind"] not in TYPES_TRANCHE:
        raise ValueError(f"{cid} : kind : une valeur parmi {'|'.join(TYPES_TRANCHE)}")
    if "cellTextIsHtml" in params:
        _booleen(cid, "cellTextIsHtml", params["cellTextIsHtml"])
    for k in ("horizontalAlign", "verticalAlign"):
        if k in params:
            _borne(cid, k, params[k], 0, 4, True)
    if "background" in params and params["background"] != "none":
        _hex(cid, "background", params["background"])


def _cible_tranche(cid, params, plusieurs=False):
    formes = [("slice",), ("number",)] + ([("slices",)] if plusieurs else [])
    f = _une_forme(cid, params, formes)
    if sum(k in params for k in ("slice", "number", "slices")) != 1:
        raise ValueError(f"{cid} : une seule cible (slice, number" + (", slices" if plusieurs else "") + ")")
    if f == ("slices",):
        v = params["slices"]
        if not isinstance(v, list) or not v or len(v) > 1000:
            raise ValueError(f"{cid} : slices : liste d'ids attendue")
        for i, x in enumerate(v):
            _borne(cid, f"slices[{i}]", x, 0, 1_000_000, True)
    else:
        _borne(cid, f[0], params[f[0]], 0 if f == ("slice",) else 1, 1_000_000, True)


def _v_tranches(cid, params):
    op = cid.split(".", 1)[1]
    options = tuple(OPTIONS_TRANCHE) + ("kind", "cellTextIsHtml", "horizontalAlign", "verticalAlign", "background")
    rect = ("rect", "x", "y", "width", "height")
    if op == "new":
        _cles(cid, params, rect + options)
        if not _rect_tranche(cid, params):
            raise ValueError(f"{cid} : rect ou x, y, width, height attendu")
        _options_tranche(cid, params)
    elif op == "set":
        _cles(cid, params, ("slice", "number") + rect + options)
        _cible_tranche(cid, params)
        _rect_tranche(cid, params)
        _options_tranche(cid, params)
    elif op == "promote":
        _cles(cid, params, ("slice", "number"))
        _cible_tranche(cid, params)
    elif op == "delete":
        _cles(cid, params, ("slice", "number", "slices"))
        _cible_tranche(cid, params, plusieurs=True)
    elif op == "divide":
        _cles(cid, params, ("slice", "number", "horizontal", "vertical"))
        _cible_tranche(cid, params)
        for k in ("horizontal", "vertical"):
            if k in params:
                _borne(cid, k, params[k], 1, 100, True)


def _v_journal_supprimer(cid, params):
    _cles(cid, params, ("rows", "all"))
    f = _une_forme(cid, params, [("rows",), ("all",)])
    if len(params) != 1:
        raise ValueError(f"{cid} : rows ou all, pas les deux")
    if f == ("all",):
        if params["all"] is not True:
            raise ValueError(f"{cid} : all : true attendu")
        return
    v = params["rows"]
    if not isinstance(v, list) or not v or len(v) > 100_000:
        raise ValueError(f"{cid} : rows : liste d'ids attendue")
    for i, x in enumerate(v):
        _borne(cid, f"rows[{i}]", x, 0, 10_000_000, True)


VERIFS_T158 = {"image.mode.duotone": _v_bichromie, "image.mode.colorTable": _v_table, "file.fileInfo": _v_infos,
               "edit.presets.presetManager": _v_gestionnaire, "edit.presets.exportImportPresets": _v_echange,
               **{f"count.{op}": _v_comptage for op in ("add", "remove", "move", "clear", "newGroup", "deleteGroup", "setGroup")},
               **{f"notes.{op}": _v_notes for op in ("add", "set", "delete")},
               **{f"slice.{op}": _v_tranches for op in ("new", "set", "promote", "delete", "divide")},
               "measurementLog.delete": _v_journal_supprimer}
