# -*- coding: utf-8 -*-
"""Chorégraphe (t234, lot « Studio : Animation », 17/10/2026) — script + direction → éléments du nœud Animation.

Option A validée par l'utilisateur : un moteur de texte CHOISI (registre `moteurs_texte`, jamais un fournisseur codé en
dur) rend un JSON borné que l'on verse tel quel dans le nœud Animation (t235 branchera le bouton « Chorégraphier »).

  - l'appel passe par `moteurs_texte.tirer_garde(..., json=True, categorie="motion")` : estimation et plafonds AVANT ;
  - la direction vient de la bibliothèque t233 : la fiche de style maison, et la consigne d'un prompt importé ou d'un
    skill — ou la consigne éditée dans le nœud, qui prime ;
  - la sortie du modèle est une DONNÉE : `valider` la borne, la répare et n'en garde que les clés du nœud ; jamais
    évaluée ; une image n'est gardée que si son `filename` est un fichier déjà présent ET proposé (une URL n'est jamais
    suivie ni téléchargée) ;
  - sortie invalide → une seconde tentative, puis le REPLI déterministe (une ligne de script = un élément texte, presets
    du style, temps proportionnel aux mots). Sans moteur, ou moteur non configuré : le repli, sans erreur ;
  - couleurs et police : le kit de marque de l'espace actif (accent, marque) et sa typographie d'identité si elle est
    livrée (`template_service._FONT_FILES`), sinon Anton, la police par défaut du nœud.

La forme d'un élément est celle de `mk()` du composant DzAnimation (bundle) : id, type, style, keyframes, start, dur,
hold, preset, text | filename — c'est aussi ce que lit `animation_service.transform_at` au rendu.

Personnalisation (t240, 18/10/2026, spec « personnalisation » § P1-P6, P8) — tout vient des champs du nœud, rien n'est
demandé pendant l'appel (P6) :
  - `direction.champs` : les valeurs des `champs` d'une fiche maison, substituées aux `{{id}}` de sa consigne (vide ou
    absent → défaut ; texte nettoyé et tronqué ; nombre borné ; liste hors options → défaut ; id inconnu ignoré) ;
  - `direction.precisions` (prompt importé ou skill seulement) : un bloc APRÈS la consigne, sous la règle « en cas de
    conflit, ces précisions priment » ; le texte importé n'est pas touché ;
  - `direction.curseurs` {creativite, rythme, finition} 0-4, 2 = neutre : nos phrases (backend/app/motion/
    personnalisation.json) en fin de direction pour Créativité et Rythme ; Finition 0-1 → une tentative, 3-4 → une
    passe de vérification (bornes, deux textes au même endroit au même instant, tenue minimale) ;
  - `tempo_bpm` 40-220 : donné au modèle, et chaque `start` (modèle ou repli) calé sur le temps le plus proche.
"""
import json
import math
import re
import unicodedata
from pathlib import Path

from app.services import motion_biblio as MB

TYPES = ("text", "sticker", "image")
PRESETS = MB.PRESETS
EASINGS = MB.EASINGS
FORMATS = MB.FORMATS
BORNES = {"x": (0, 100), "y": (0, 100), "scale": (0.1, 4), "rotation": (-720, 720), "opacity": (0, 1)}
CLES = tuple(BORNES)
MAX_ELEMENTS = 24
MAX_CLES = 8
MAX_TEXTE = 160
MAX_SCRIPT = 6000
MAX_CONSIGNE = 8000
MAX_IMAGES = 50
MAX_TOKENS = 3000
DUREE_MIN, DUREE_MAX, DUREE_DEFAUT = 1, 120, 8
TAILLE = (12, 400)
DEFAUT_CLE = {"x": 50, "y": 50, "scale": 1, "rotation": 0, "opacity": 1}
POLICE_DEFAUT = "Anton"
COULEUR_DEFAUT = "#00e5ff"             # le cyan de mk() : la couleur d'un élément neuf du nœud
PERSO_FICHIER = Path(__file__).resolve().parent.parent / "motion" / "personnalisation.json"
CURSEURS = ("creativite", "rythme", "finition")
NEUTRE = 2
TEMPO = (40, 220)
MAX_PRECISION = 300
MAX_CHAMP = 400
PRECISIONS = ("usage", "duree", "couleurs", "police", "autre")
TENUE_MIN = {3: 0.5, 4: 0.8}            # finition → tenue minimale (s) vérifiée
PROCHE = (10, 8)                        # deux textes à moins de 10 % en x et 8 % en y : « au même endroit »
_CHAMP_ID = re.compile(r"\{\{([a-z0-9_]+)\}\}")

# Les presets du nœud (PRESETS de DzAnimation, bundle), écrits en deux keyframes comme `applyPreset` (t231).
_PRESETS = {
    "fade-in": ((50, 50, 1, 0, 0), (50, 50, 1, 0, 1), "easeOut"),
    "slide-up": ((50, 65, 1, 0, 0), (50, 45, 1, 0, 1), "easeOut"),
    "slide-down": ((50, 35, 1, 0, 0), (50, 55, 1, 0, 1), "easeOut"),
    "slide-left": ((70, 50, 1, 0, 0), (50, 50, 1, 0, 1), "easeOut"),
    "slide-right": ((30, 50, 1, 0, 0), (50, 50, 1, 0, 1), "easeOut"),
    "pop": ((50, 50, 0.3, 0, 0), (50, 50, 1, 0, 1), "easeOutBack"),
    "zoom-in": ((50, 50, 0.6, 0, 0), (50, 50, 1, 0, 1), "easeOut"),
    "ken-burns": ((50, 50, 1, 0, 1), (50, 50, 1.2, 0, 1), "linear"),
}
_NB = r"\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*"
_BEZIER = re.compile(r"^cubic-bezier\(" + ",".join([_NB] * 4) + r"\)$")
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_FICHIER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


# ── la marque ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _police_connue(nom) -> bool:
    from app.services import template_service as T
    return isinstance(nom, str) and nom.strip().lower() in T._FONT_FILES


def marque(m=None) -> dict:
    """{couleur, marque, police} : l'accent et la couleur de marque du kit de l'espace actif, la première typographie
    d'identité LIVRÉE (sinon Anton). `m` False : les valeurs d'un élément neuf du nœud ; `m` objet : ses couleurs
    #RRGGBB et sa police connue l'emportent, toute autre valeur est ignorée."""
    from app.services import brand_kits as BK
    if m is False:
        return {"couleur": COULEUR_DEFAUT, "marque": BK.DEFAUTS["brand_color"], "police": POLICE_DEFAUT}
    out = {"couleur": BK.DEFAUTS["accent_color"], "marque": BK.DEFAUTS["brand_color"], "police": POLICE_DEFAUT}
    try:
        from app.services import espaces as ES
        from app.services import identite as IDV
        kit = ES.kit_de_l_espace()
        for cle, champ in (("couleur", "accent_color"), ("marque", "brand_color")):
            if isinstance(kit.get(champ), str) and _COULEUR.match(kit[champ]):
                out[cle] = kit[champ]
        for t in IDV.lire(ES.espace_courant()).get("typographies") or []:
            if _police_connue(t.get("nom")):
                out["police"] = t["nom"].strip()
                break
    except Exception:  # noqa: BLE001 — une marque illisible n'empêche jamais de chorégraphier
        pass
    if isinstance(m, dict):
        for cle in ("couleur", "marque"):
            if isinstance(m.get(cle), str) and _COULEUR.match(m[cle].strip()):
                out[cle] = m[cle].strip()
        if _police_connue(m.get("police")):
            out["police"] = m["police"].strip()
    return out


# ── la direction ──────────────────────────────────────────────────────────────────────────────────────────────────
def _loc(v, langue: str) -> str:
    if isinstance(v, dict):
        return str(v.get(langue) or v.get("fr") or "")
    return str(v or "")


def personnalisation() -> dict:
    """Les curseurs (états, phrases, effets) et le bloc de précisions, FR / EN — fichier de données du dépôt."""
    return json.loads(PERSO_FICHIER.read_text(encoding="utf-8"))


def _valeur_champ(c: dict, v, langue: str):
    """(valeur rendue, texte substitué) d'un champ de fiche ; vide, absent ou fautif → le défaut."""
    t = c.get("type")
    if t == "nombre":
        lo, hi, defaut = c.get("min", 0), c.get("max", 0), c.get("defaut", 0)
        if isinstance(v, str):
            try:
                v = float(v.replace(",", ".")) if v.strip() else None
            except ValueError:
                v = None
        x = _nombre(v, defaut, lo, hi)
        x = int(x) if float(x).is_integer() else x
        return x, "%g" % x
    if t == "liste":
        ops = {o.get("valeur"): o for o in c.get("options") or [] if isinstance(o, dict)}
        cle = v if isinstance(v, str) and v in ops else c.get("defaut")
        return cle, _loc((ops.get(cle) or {}).get("libelle"), langue)
    maxi = int(c.get("max") or 80) if isinstance(c.get("max"), int) else 80
    x = _propre(v, min(maxi, MAX_CHAMP))
    if not x:
        x = _loc(c.get("defaut"), langue)
    return x, x


def substituer(fiche, valeurs, langue: str = "fr") -> tuple:
    """(consigne de la fiche dans `langue`, valeurs appliquées) : chaque `{{id}}` reçoit la valeur du nœud ou le
    défaut. Une seule passe : une valeur qui contient elle-même `{{…}}` n'est jamais substituée à son tour."""
    if not fiche:
        return "", {}
    valeurs = valeurs if isinstance(valeurs, dict) else {}
    appliques, textes = {}, {}
    for c in fiche.get("champs") or []:
        if isinstance(c, dict) and isinstance(c.get("id"), str):
            appliques[c["id"]], textes[c["id"]] = _valeur_champ(c, valeurs.get(c["id"]), langue)
    consigne = _CHAMP_ID.sub(lambda m: textes.get(m.group(1), m.group(0)), _loc(fiche.get("consigne"), langue))
    return consigne, appliques


def precisions(v) -> dict:
    """Les cinq précisions connues, nettoyées (une ligne) et tronquées ; une clé inconnue ou vide est ignorée."""
    v = v if isinstance(v, dict) else {}
    return {k: _propre(v[k], MAX_PRECISION) for k in PRECISIONS if _propre(v.get(k), MAX_PRECISION)}


def curseurs(v) -> dict:
    """{creativite, rythme, finition} entiers 0-4 ; absent ou fautif → 2 (neutre)."""
    v = v if isinstance(v, dict) else {}
    out = {}
    for k in CURSEURS:
        x = v.get(k)
        if isinstance(x, float) and x.is_integer():
            x = int(x)
        out[k] = min(4, max(0, x)) if isinstance(x, int) and not isinstance(x, bool) else NEUTRE
    return out


def tempo(v):
    """BPM borné 40-220 ; absent, nul ou illisible → None (pas de tempo)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
        return None
    x = min(TEMPO[1], max(TEMPO[0], v))
    return int(x) if float(x).is_integer() else round(x, 2)


def direction(d, langue: str = "fr") -> dict:
    """{fiche, consigne, source, consigne_style, champs, precisions, curseurs} depuis `{style, source, consigne,
    champs, precisions, curseurs}`. Style : une fiche maison (`style-<thème>`), sa consigne aux champs substitués ;
    source : l'id (ou {id}) d'un prompt importé ou d'un skill — sa consigne ; `consigne` (éditée dans le nœud) prime ;
    les précisions ne valent que pour une source. LookupError pour un style ou une source inconnus."""
    d = d if isinstance(d, dict) else {}
    langue = langue if langue in ("fr", "en") else "fr"
    fiche = None
    style = d.get("style")
    if style:
        if not isinstance(style, str) or not style.startswith("style-"):
            eid = str(style)[:80]
            raise LookupError(f"Entrée inconnue : {eid}")
        fiche = MB.lire(style)
    src = d.get("source")
    sid = src.get("id") if isinstance(src, dict) else src
    texte = ""
    if sid and sid != "aucune":
        if not isinstance(sid, str) or sid.startswith("style-"):
            eid = str(sid)[:80]
            raise LookupError(f"Entrée inconnue : {eid}")
        e = MB.lire(sid)
        texte = e.get("consigne") if e.get("nature") == "skill" else e.get("texte")
    else:
        sid = None
    edite = d.get("consigne")
    if isinstance(edite, str) and edite.strip():
        texte = edite
    consigne_style, champs = substituer(fiche, d.get("champs"), langue)
    return {"fiche": fiche, "source": sid, "consigne": _propre(texte or "", MAX_CONSIGNE, lignes=True),
            "langue": langue, "consigne_style": consigne_style, "champs": champs,
            "precisions": precisions(d.get("precisions")) if sid else {}, "curseurs": curseurs(d.get("curseurs"))}


# ── le prompt ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _fin_de_direction(d: dict, lg: str) -> list:
    """Les phrases des curseurs Créativité et Rythme hors du neutre, puis le bloc de précisions (qui priment)."""
    perso = personnalisation()
    out = []
    for k in ("creativite", "rythme"):
        cran = (perso["curseurs"][k]["crans"] or [])[(d.get("curseurs") or {}).get(k, NEUTRE)]
        if cran.get("phrase"):
            out.append(_loc(cran["phrase"], lg))
    if out:
        out = ["", "CURSEURS :"] + out
    pr = d.get("precisions") or {}
    if pr:
        bloc = perso["precisions"]
        libelles = {c["id"]: _loc(c["libelle"], lg) for c in bloc["champs"]}
        out += ["", _loc(bloc["titre"], lg) + " — " + _loc(bloc["regle"], lg)]
        out += [f"- {libelles[k]} : {pr[k]}" for k in PRECISIONS if k in pr]
    return out


def systeme(d: dict, aspect: str, duree_s: float, images=(), tempo_bpm=None) -> str:
    """Le prompt système : le schéma JSON imposé, puis la direction (style aux champs substitués, rythme, consigne,
    tempo, phrases des curseurs, bloc de précisions)."""
    imgs = ", ".join(images) if images else "(aucune)"
    lignes = [
        "Tu es le chorégraphe du nœud Animation de DeepotusVideo. Tu transformes un script en éléments animés.",
        "Ne pose aucune question : tout ce qu'il faut savoir est ci-dessous. Rends UN objet JSON {\"elements\": [...]} "
        "et rien d'autre. Schéma d'un élément :",
        '  "type" : "text" | "sticker" | "image" ;',
        '  "text" (type "text") : une ligne du script, mot pour mot, %d caractères au plus ;' % MAX_TEXTE,
        '  "filename" (types "sticker" / "image") : UNIQUEMENT un de ces fichiers déjà présents : %s ; jamais une URL, '
        "jamais un chemin ;" % imgs,
        '  "start", "dur", "hold" : secondes (entrée, durée de l\'entrée, tenue), le tout dans 0-%g ;' % duree_s,
        '  "keyframes" : 2 à %d clés {"t", "x", "y", "scale", "rotation", "opacity", "easing"} ; t de 0 à 1 dans '
        "l'entrée, x et y 0-100 (pourcentage du cadre, 50 = centre), scale 0.1-4, rotation -720 à 720 (degrés), "
        "opacity 0-1 ;" % MAX_CLES,
        '  "easing" : %s, ou "cubic-bezier(x1,y1,x2,y2)" ;' % ", ".join(EASINGS),
        '  "preset" (facultatif, à la place des keyframes) : %s ;' % ", ".join(PRESETS),
        '  "role" (facultatif) : "marque" pour la couleur de marque, sinon la couleur d\'accent ;',
        '  "style" (facultatif) : {"size"} seulement, %d-%d ; la police et les couleurs sont celles de la marque.'
        % TAILLE,
        "Au plus %d éléments. Format %s, durée totale %g s. Aucune autre clé." % (MAX_ELEMENTS, aspect, duree_s),
    ]
    f = d.get("fiche")
    lg = d.get("langue", "fr")
    if f:
        lignes += ["", "STYLE — " + _loc(f.get("titre"), lg), d.get("consigne_style") or _loc(f.get("consigne"), lg),
                   "Rythme : " + _loc(f.get("rythme"), lg)]
        if f.get("easings"):
            lignes.append("Easings privilégiés : " + ", ".join(e for e in f["easings"] if e in EASINGS))
        if f.get("presets"):
            lignes.append("Presets autorisés : " + ", ".join(p for p in f["presets"] if p in PRESETS))
    if tempo_bpm:
        lignes += ["", "TEMPO : %g BPM — un temps = %g s ; chaque \"start\" tombe sur un temps (un multiple de %g s)."
                   % (tempo_bpm, round(60 / tempo_bpm, 4), round(60 / tempo_bpm, 4))]
    if d.get("consigne"):
        lignes += ["", "CONSIGNE DE DIRECTION :", d["consigne"]]
    lignes += _fin_de_direction(d, lg)
    return "\n".join(lignes)


def prompt(script: str, aspect: str, duree_s: float, erreur: str = "") -> str:
    p = f"Format {aspect}, {duree_s:g} s.\nSCRIPT :\n{script}"
    if erreur:
        p += f"\n\nTa réponse précédente était invalide ({erreur[:200]}). Rends seulement l'objet JSON du schéma."
    return p


# ── validation, bornes, réparation ────────────────────────────────────────────────────────────────────────────────
def _propre(v, maxi: int, lignes: bool = False) -> str:
    """Un texte sans caractère de contrôle (les retours à la ligne gardés si `lignes`), tronqué."""
    if not isinstance(v, str):
        return ""
    t = "".join(ch for ch in v if (lignes and ch == "\n") or unicodedata.category(ch) not in ("Cc", "Cf"))
    return t.strip()[:maxi]


def _nombre(v, defaut, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        v = defaut                          # le défaut aussi est borné (une tenue de 2 s dans une durée de 0 s)
    return round(min(hi, max(lo, v)), 4)


def _easing(v) -> str:
    if isinstance(v, str):
        if v in EASINGS:
            return v
        m = _BEZIER.match(v.strip())
        if m:
            x1, y1, x2, y2 = (float(g) for g in m.groups())
            x1, x2 = min(1, max(0, x1)), min(1, max(0, x2))
            y1, y2 = min(2, max(-1, y1)), min(2, max(-1, y2))
            return "cubic-bezier(%g,%g,%g,%g)" % (x1, y1, x2, y2)
    return "linear"


def _cles_preset(nom: str) -> list:
    a, b, ez = _PRESETS[nom]
    return [dict(zip(CLES, a), t=0, easing=ez), dict(zip(CLES, b), t=1, easing="linear")]


def _cles(brutes) -> list:
    """Au plus MAX_CLES clés valides, t dans 0..1, triées ; chaque valeur bornée, une valeur absente ou fautive reprend
    celle de la clé précédente (sinon le défaut). Une seule clé : tenue de 0 à 1."""
    if not isinstance(brutes, list):
        return []
    sel = [k for k in brutes if isinstance(k, dict)][:MAX_CLES]
    sel = sorted(sel, key=lambda k: _nombre(k.get("t"), 0, 0, 1))
    out, prec = [], dict(DEFAUT_CLE)
    for k in sel:
        c = {"t": _nombre(k.get("t"), 0, 0, 1)}
        for nom, (lo, hi) in BORNES.items():
            c[nom] = _nombre(k.get(nom), prec[nom], lo, hi)
        c["easing"] = _easing(k.get("easing"))
        prec = c
        out.append(c)
    if len(out) == 1:
        out = [dict(out[0], t=0), dict(out[0], t=1)]
    return out


def _style(e: dict, m: dict) -> dict:
    st = e.get("style") if isinstance(e.get("style"), dict) else {}
    return {"font": m["police"], "size": int(_nombre(st.get("size"), 80, *TAILLE)),
            "color": m["marque"] if e.get("role") == "marque" else m["couleur"], "stroke": 0,
            "strokeColor": "#000000", "shadow": 0, "align": "center", "bg": None}


def _element(e, i: int, images: set, m: dict, duree_s: float):
    if not isinstance(e, dict) or e.get("type") not in TYPES:
        return None
    out = {"id": f"el_m{i:02d}", "type": e["type"], "style": _style(e, m)}
    if e["type"] == "text":
        out["text"] = _propre(e.get("text"), MAX_TEXTE)
        if not out["text"]:
            return None
    else:
        f = e.get("filename")
        if not isinstance(f, str) or not _FICHIER.match(f) or f not in images:
            return None                     # une URL, un chemin, un fichier non proposé : jamais suivi
        out["filename"] = f
    kfs = _cles(e.get("keyframes"))
    preset = None
    if not kfs:
        preset = e.get("preset") if e.get("preset") in _PRESETS else "fade-in"
        kfs = _cles_preset(preset)
    out["keyframes"] = kfs
    start = _nombre(e.get("start"), 0, 0, max(0, duree_s - 0.05))
    dur = _nombre(e.get("dur"), 0.8, 0.05, max(0.05, duree_s - start))
    out.update(start=start, dur=dur, hold=_nombre(e.get("hold"), 2, 0, max(0, round(duree_s - start - dur, 4))),
               preset=preset)
    return out


def images_presentes(noms) -> list:
    """Les noms proposés qui sont des fichiers DÉJÀ présents dans le dossier des images (nom simple, sans chemin)."""
    from app.config import settings
    out = []
    for n in (noms if isinstance(noms, list) else [])[:MAX_IMAGES]:
        if isinstance(n, str) and _FICHIER.match(n) and n not in out and (settings.images_path / n).is_file():
            out.append(n)
    return out


def valider(sortie, *, images, marque: dict, duree_s: float) -> list:
    """Les éléments du nœud tirés d'une sortie de modèle (objet {elements} ou liste) ; ValueError si aucun ne tient."""
    brut = sortie.get("elements") if isinstance(sortie, dict) else sortie
    if not isinstance(brut, list):
        raise ValueError("sortie sans liste d'éléments")
    ims = set(images or ())
    out = []
    for e in brut:
        if len(out) >= MAX_ELEMENTS:
            break
        v = _element(e, len(out), ims, marque, duree_s)
        if v:
            out.append(v)
    if not out:
        raise ValueError("aucun élément valide dans la sortie")
    return out


# ── tempo et vérification ─────────────────────────────────────────────────────────────────────────────────────────
def sur_le_temps(t: float, bpm, duree_s: float) -> float:
    """`t` calé sur le temps le plus proche, sans dépasser la dernière entrée possible (duree_s - 0,05)."""
    maxi = max(0.0, duree_s - 0.05)
    if not bpm:
        return min(maxi, max(0.0, t))
    b = 60 / bpm
    s = round(max(0.0, t) / b) * b
    if s > maxi + 1e-9:
        s = math.floor(maxi / b + 1e-9) * b
    return round(s, 4)


def caler(elements: list, bpm, duree_s: float) -> list:
    """Chaque `start` sur un temps ; durée d'entrée et tenue rebornées dans la durée totale."""
    if not bpm:
        return elements
    for e in elements:
        e["start"] = sur_le_temps(e["start"], bpm, duree_s)
        e["dur"] = round(min(e["dur"], max(0.05, duree_s - e["start"])), 4)
        e["hold"] = round(max(0.0, min(e["hold"], duree_s - e["start"] - e["dur"])), 4)
    return elements


def verifier(elements: list, duree_s: float, finition: int) -> tuple:
    """La passe de vérification de la finition 3-4 : (éléments, corrections). Bornes rejouées ; deux textes au même
    endroit (position finale) au même instant → le premier cède la place quand le second entre, s'il reste assez tenu,
    sinon le second est décalé en hauteur ; chaque élément tenu au moins TENUE_MIN s quand la durée le permet."""
    tmin = TENUE_MIN.get(finition, 0.5)
    n = 0
    for e in elements:
        avant = (e["start"], e["dur"], e["hold"])
        e["start"] = round(min(max(0.0, e["start"]), max(0.0, duree_s - 0.05)), 4)
        e["dur"] = round(min(max(0.05, e["dur"]), max(0.05, duree_s - e["start"])), 4)
        e["hold"] = round(max(0.0, min(e["hold"], duree_s - e["start"] - e["dur"])), 4)
        if (e["start"], e["dur"], e["hold"]) != avant:
            n += 1
    textes = sorted((e for e in elements if e["type"] == "text"), key=lambda e: e["start"])
    for i, a in enumerate(textes):
        for b in textes[i + 1:]:
            ka, kb = a["keyframes"][-1], b["keyframes"][-1]
            fin_a, fin_b = a["start"] + a["dur"] + a["hold"], b["start"] + b["dur"] + b["hold"]
            if abs(ka["x"] - kb["x"]) >= PROCHE[0] or abs(ka["y"] - kb["y"]) >= PROCHE[1] \
                    or not (a["start"] < fin_b and b["start"] < fin_a):
                continue
            if b["start"] - a["start"] >= tmin and b["start"] > a["start"]:
                a["hold"] = round(max(0.0, b["start"] - a["start"] - a["dur"]), 4)
                a["dur"] = round(min(a["dur"], b["start"] - a["start"]), 4)
            else:
                dy = 12 if ka["y"] <= 50 else -12
                for k in b["keyframes"]:
                    k["y"] = round(min(100, max(0, k["y"] + dy)), 4)
            n += 1
    for e in elements:
        if e["dur"] + e["hold"] < tmin - 1e-9:
            hold = round(min(tmin - e["dur"], max(0.0, duree_s - e["start"] - e["dur"])), 4)
            if hold > e["hold"]:
                e["hold"] = hold
                n += 1
    return elements, n


# ── le repli déterministe ─────────────────────────────────────────────────────────────────────────────────────────
def repli(script: str, fiche, m: dict, duree_s: float, bpm=None) -> list:
    """Une ligne non vide = un élément texte ; presets du style dans l'ordre (fade-in sans style) ; chaque ligne reçoit
    une tranche du temps proportionnelle à ses mots : elle entre au début de sa tranche et tient jusqu'à la suivante.
    Avec un tempo, chaque début de tranche est calé sur un temps (strictement croissant tant que la durée le permet)."""
    lignes = [_propre(l, MAX_TEXTE) for l in str(script or "").splitlines()]
    lignes = [l for l in lignes if l][:MAX_ELEMENTS]
    presets = [p for p in ((fiche or {}).get("presets") or []) if p in _PRESETS] or ["fade-in"]
    mots = [max(1, len(l.split())) for l in lignes]
    total = sum(mots) or 1
    debuts, cumul = [], 0
    for i in range(len(lignes)):
        t = round(duree_s * cumul / total, 3)
        cumul += mots[i]
        if bpm:
            t = sur_le_temps(t, bpm, duree_s)
            if debuts and t <= debuts[-1]:
                suivant = round(debuts[-1] + 60 / bpm, 4)
                t = suivant if suivant <= duree_s - 0.05 else debuts[-1]
        debuts.append(t)
    out = []
    for i, l in enumerate(lignes):
        debut = debuts[i]
        fin = debuts[i + 1] if i + 1 < len(lignes) else duree_s   # la dernière tranche finit à duree_s
        tranche = max(0.001, fin - debut)
        dur = round(min(tranche, max(0.2, min(0.8, tranche * 0.35))), 3)
        preset = presets[i % len(presets)]
        taille = 80 if len(l) <= 20 else max(32, int(80 * 20 / len(l)))
        out.append({"id": f"el_m{i:02d}", "type": "text", "text": l,
                    "style": {"font": m["police"], "size": taille, "color": m["couleur"], "stroke": 0,
                              "strokeColor": "#000000", "shadow": 0, "align": "center", "bg": None},
                    "keyframes": _cles_preset(preset), "start": debut, "dur": dur,
                    "hold": round(max(0.0, tranche - dur), 3), "preset": preset})
    return out


# ── l'appel ───────────────────────────────────────────────────────────────────────────────────────────────────────
async def choregraphier(corps: dict, langue: str = "fr") -> dict:
    """{elements, moteur, modele, cout, repli, raison, tentatives, aspect, duree_s, effort, effort_applique, champs,
    precisions, curseurs, tempo_bpm, marque, verification}. ValueError (script vide), LookupError (style / source
    inconnus) ; un plafond dépassé remonte (402). Tout le reste finit en repli."""
    from app.services import moteurs_texte as MT
    from app.services import pricing
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    script = _propre(corps.get("script"), MAX_SCRIPT, lignes=True)
    if not script:
        raise ValueError("Le script est vide.")
    d = direction(corps.get("direction"), langue)
    fiche = d["fiche"]
    aspect = corps.get("aspect") if corps.get("aspect") in FORMATS else "9:16"
    defaut = ((fiche or {}).get("duree_s") or {}).get("type") or DUREE_DEFAUT
    duree = float(_nombre(corps.get("duree_s"), defaut, DUREE_MIN, DUREE_MAX))
    images = images_presentes(corps.get("images"))
    m = marque(corps.get("marque"))
    moteur = corps.get("moteur").strip() if isinstance(corps.get("moteur"), str) else ""
    modele = corps.get("modele").strip() if isinstance(corps.get("modele"), str) else ""
    effort = corps.get("effort").strip().lower()[:16] if isinstance(corps.get("effort"), str) else None
    rep = {"moteur": moteur, "modele": modele, "aspect": aspect, "duree_s": duree, "repli": False, "raison": "",
           "tentatives": 0, "cout": {"nature": MT.nature_cout(moteur) if moteur else "gratuit", "estime_usd": 0.0},
           "effort": effort or "auto", "effort_applique": ""}
    dd = corps.get("direction") if isinstance(corps.get("direction"), dict) else {}
    bpm = tempo(corps.get("tempo_bpm")) if corps.get("tempo_bpm") is not None else tempo(dd.get("tempo_bpm"))
    finition = d["curseurs"]["finition"]
    rep.update(champs=d["champs"], precisions=bool(d["precisions"]), curseurs=d["curseurs"], tempo_bpm=bpm, marque=m,
               verification={"faite": False, "corrections": 0})

    def _fini(r: dict, elements: list) -> dict:
        elements = caler(elements, bpm, duree)
        if finition >= 3:
            elements, n = verifier(elements, duree, finition)
            r["verification"] = {"faite": True, "corrections": n}
        return dict(r, elements=elements)

    def _repli(raison: str) -> dict:
        return _fini(dict(rep, repli=True, raison=raison), repli(script, fiche, m, duree, bpm))

    if not moteur:
        return _repli("sans_moteur")
    if not MT.connu(moteur):
        return _repli("moteur_inconnu")
    if not MT.configure(moteur):
        return _repli("non_configure")
    if not modele:
        modele = rep["modele"] = MT.modele_sain(moteur)
    if MT.ressemble_a_une_cle(modele):
        rep["modele"] = ""
        return _repli("modele_fautif")
    rep["effort_applique"] = MT.effort_applique(moteur, modele, effort)     # t239 : "" = Auto (rien envoyé)
    sy = systeme(d, aspect, duree, images, bpm)
    erreur = ""
    for n in ((1,) if finition <= 1 else (1, 2)):           # finition 0-1 : une seule tentative avant le repli
        p = prompt(script, aspect, duree, erreur)
        rep["tentatives"] = n
        rep["cout"]["estime_usd"] = round(rep["cout"]["estime_usd"]
                                          + pricing.estimate(MT.estimer(moteur, p, sy, MAX_TOKENS, effort,
                                                                                     modele=modele))["total_usd"], 6)
        try:
            sortie = await MT.tirer_garde(moteur, modele, p, sy, MAX_TOKENS, json=True, categorie="motion",
                                          effort=effort)
            return _fini(rep, valider(sortie, images=images, marque=m, duree_s=duree))
        except (RuntimeError, ValueError) as e:
            erreur = str(e)
    return _repli("sortie_invalide")
