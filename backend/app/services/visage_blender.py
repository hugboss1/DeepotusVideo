# -*- coding: utf-8 -*-
"""Animation FACIALE dans Blender (22/11/2026) — synchronisation labiale, expressions et clignements sur un personnage
(rig de Blender Studio / CloudRig / Rigify, personnage à clés de forme ARKit ou visèmes, ou personnage GÉNÉRÉ sans
visage animable : Meshy, Tripo, Rodin…).

MÊME DISCIPLINE que blender_gabarits (pont « Scène Blender ») et passes_blender (headless) :
  * tout le CALCUL est ici, en Python pur : les visèmes (depuis un texte, un JSON de Rhubarb Lip Sync ou l'enveloppe
    d'un WAV), puis les COURBES de chaque commande du visage (images clés [image, valeur]) ;
  * le script Blender est un texte FIXE (`GABARIT`) dont l'unique trou `__PARAMS__` reçoit le repr() d'un JSON ASCII
    vérifié (`verifier`) : aucun texte venu d'un écran, d'un agent ou d'un fichier n'y devient du code ; il passe le
    validateur du mode sûr de mcp-for-blender (bpy, mathutils, json, math seulement ; aucun nom d'attribut calculé) ;
  * le script ne crée que des clés de forme préfixées « DZ_ » (mode procédural) et des actions « DZ_Visage_… » ; un
    nouvel envoi remplace les clés posées par l'envoi précédent sur la même plage d'images.

Trois façons d'animer, choisies par le script dans Blender (`mode` = auto) :
  1. CLÉS DE FORME existantes : noms ARKit (jawOpen, eyeBlinkLeft…), visèmes Oculus / Ready Player Me (viseme_aa…),
     VRM (A, I, U, E, O, Blink…), ou noms usuels (MouthOpen, Blink_L…) ;
  2. OS DU VISAGE (rigs de Blender Studio, Rigify, Auto-Rig Pro, Meshy/Mixamo) : mâchoire, coins des lèvres,
     paupières, sourcils trouvés par leur nom ; les gestes sont donnés dans le repère du PERSONNAGE (haut, avant,
     côté) et convertis dans le repère de repos de chaque os, quel que soit son axe — réglables par `os_reglages` ;
  3. PROCÉDURAL : pour un maillage sans visage animable, le script SCULPTE des clés de forme DZ_ (mâchoire, sourire,
     moue, clignement, sourcils) autour de repères placés en coordonnées normalisées de la tête (`reperes`).

Deux chemins d'exécution :
  * Blender OUVERT, par le pont MCP (blender_mcp.executer_script_visage) ;
  * Blender en arrière-plan (`argv_headless`) : ouvre un .blend ou importe un .glb, anime, enregistre un .blend et,
    au choix, exporte un .glb avec ses morphes animés (pour le Studio 3D et le web).
Le script imprime une ligne « DZVISAGE {json} » : la cible trouvée, le mode retenu, les commandes animées.
"""
from __future__ import annotations

import json
import math
import re
import struct
import unicodedata
import wave
from pathlib import Path

VERSION = 1
FPS_DEFAUT = 24
MAX_IMAGES = 24 * 60 * 10           # 10 min d'animation à 24 i/s
MAX_CLES_PAR_COMMANDE = 6000
MAX_TEXTE = 6000
MAX_NOM = 64
MAX_CHEMIN = 400
CARS_PAR_SECONDE = 14.0              # débit moyen d'une voix off (caractères parlés par seconde)
_NOM_SUR = re.compile(r"[^0-9A-Za-z _\-().:']+")

# Les commandes du visage (sous-ensemble ARKit, noms ARKit) : ce que les courbes animent.
COMMANDES = (
    "jawOpen", "mouthClose", "mouthFunnel", "mouthPucker", "mouthPress",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthStretchLeft", "mouthStretchRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeWideLeft", "eyeWideRight", "eyeSquintLeft", "eyeSquintRight",
    "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "browDownLeft", "browDownRight",
)
BOUCHE = tuple(c for c in COMMANDES if c.startswith(("jaw", "mouth")))

# Les visèmes de Rhubarb Lip Sync (formes de bouche de Preston Blair) : A..H + X (repos).
VISEMES = ("A", "B", "C", "D", "E", "F", "G", "H", "X")
VISEME_COMMANDES: dict[str, dict[str, float]] = {
    "A": {"mouthClose": 0.7, "mouthPress": 0.4},                                    # M B P : lèvres closes
    "B": {"jawOpen": 0.15, "mouthStretchLeft": 0.25, "mouthStretchRight": 0.25},     # K S T… dents serrées
    "C": {"jawOpen": 0.35, "mouthStretchLeft": 0.15, "mouthStretchRight": 0.15},     # È, É, AI : ouverte
    "D": {"jawOpen": 0.7},                                                           # A : grande ouverte
    "E": {"jawOpen": 0.3, "mouthFunnel": 0.45},                                      # O, EU : arrondie
    "F": {"jawOpen": 0.1, "mouthPucker": 0.75},                                      # OU, U, W : en avant
    "G": {"jawOpen": 0.08, "mouthClose": 0.3, "mouthStretchLeft": 0.2, "mouthStretchRight": 0.2},  # F V
    "H": {"jawOpen": 0.3},                                                           # L : langue
    "X": {},                                                                         # repos
}
EXPRESSIONS: dict[str, dict[str, float]] = {
    "neutre": {},
    "joie": {"mouthSmileLeft": 0.8, "mouthSmileRight": 0.8, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3,
             "browOuterUpLeft": 0.2, "browOuterUpRight": 0.2},
    "sourire": {"mouthSmileLeft": 0.45, "mouthSmileRight": 0.45},
    "tristesse": {"mouthFrownLeft": 0.6, "mouthFrownRight": 0.6, "browInnerUp": 0.7},
    "colere": {"browDownLeft": 0.8, "browDownRight": 0.8, "mouthPress": 0.4, "eyeSquintLeft": 0.3,
               "eyeSquintRight": 0.3},
    "surprise": {"browInnerUp": 0.8, "browOuterUpLeft": 0.8, "browOuterUpRight": 0.8, "eyeWideLeft": 0.7,
                 "eyeWideRight": 0.7, "jawOpen": 0.3},
    "peur": {"browInnerUp": 0.9, "eyeWideLeft": 0.8, "eyeWideRight": 0.8, "mouthStretchLeft": 0.5,
             "mouthStretchRight": 0.5},
    "degout": {"mouthFrownLeft": 0.4, "mouthFrownRight": 0.4, "eyeSquintLeft": 0.5, "eyeSquintRight": 0.5,
               "browDownLeft": 0.4, "browDownRight": 0.4},
    "malice": {"mouthSmileLeft": 0.6, "mouthSmileRight": 0.15, "browOuterUpLeft": 0.5, "eyeSquintRight": 0.4},
}
MODES = ("auto", "cles", "os", "procedural")
FACES = ("-Y", "+Y")                 # l'avant du personnage dans Blender (-Y : convention de l'import glTF)

# Repères du mode procédural, en coordonnées normalisées de la TÊTE VUE DE FACE : u = 0 au bord gauche de l'image …
# 1 au bord droit, v = 0 au menton … 1 au sommet. « oeil_gauche » = l'œil GAUCHE DU PERSONNAGE (à droite de l'image,
# comme eyeBlinkLeft d'ARKit). Valeurs de départ d'un personnage stylisé (Meshy / Tripo) ; réglables.
REPERES_DEFAUT = {"bouche": [0.5, 0.27], "oeil_gauche": [0.67, 0.55], "oeil_droit": [0.33, 0.55],
                  "sourcils_v": 0.67, "largeur_bouche": 0.30}
AMPLITUDE_DEFAUT = 1.0


class VisageRefuse(ValueError):
    """Des paramètres inutilisables (400 côté route)."""


# ── visèmes ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def _sans_accent(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


# digrammes d'abord (français puis anglais), puis lettres
_DIGRAMMES = (("ou", "F"), ("oo", "F"), ("au", "E"), ("eau", "E"), ("eu", "E"), ("oi", "D"), ("ai", "C"),
              ("ei", "C"), ("ch", "B"), ("sh", "B"), ("th", "B"), ("ph", "G"), ("qu", "B"), ("gn", "B"),
              ("on", "E"), ("an", "D"), ("en", "D"), ("in", "C"), ("un", "C"), ("ee", "C"), ("ea", "C"))
_LETTRES = {"m": "A", "b": "A", "p": "A", "f": "G", "v": "G", "w": "F", "o": "E", "u": "F", "a": "D",
            "e": "C", "i": "C", "y": "C", "l": "H"}


def visemes_depuis_texte(texte: str, duree_s: float | None = None) -> list[dict]:
    """Une estimation sans dépendance : chaque son reconnu dans le texte donne un visème, sur une durée répartie
    selon le débit moyen (ou étirée sur `duree_s`, la durée de l'audio). Pauses de ponctuation = repos (X).
    Rend [{debut, fin, viseme}] en secondes, visèmes répétés fusionnés."""
    t = _sans_accent(str(texte or "")[:MAX_TEXTE]).lower()
    unites: list[tuple[str, float]] = []          # (visème, poids de durée)
    i = 0
    while i < len(t):
        c = t[i]
        if c in ".!?;:":
            unites.append(("X", 6.0))
            i += 1
            continue
        if c in ",\n—-":
            unites.append(("X", 3.0))
            i += 1
            continue
        if c.isspace():
            unites.append(("X", 0.6))
            i += 1
            continue
        if not c.isalpha():
            i += 1
            continue
        trouve = None
        for dg, v in sorted(_DIGRAMMES, key=lambda x: -len(x[0])):
            if t.startswith(dg, i):
                trouve = (v, len(dg))
                break
        if trouve:
            unites.append((trouve[0], float(trouve[1])))
            i += trouve[1]
            continue
        # muettes finales françaises (« -es », « -ent », « -e » en fin de mot) : rien
        if c in "es" and (i + 1 >= len(t) or not t[i + 1].isalpha()) and i > 0 and t[i - 1].isalpha():
            i += 1
            continue
        if c == "h":
            i += 1
            continue
        unites.append((_LETTRES.get(c, "B"), 1.0))
        i += 1
    if not any(v != "X" for v, _ in unites):
        return []
    total = sum(p for _, p in unites)
    duree = float(duree_s) if duree_s and duree_s > 0 else total / CARS_PAR_SECONDE
    k = duree / total
    out: list[dict] = [{"debut": 0.0, "fin": 0.0, "viseme": "X"}]
    pos = 0.0
    for v, p in unites:
        d = p * k
        if out[-1]["viseme"] == v:
            out[-1]["fin"] = round(pos + d, 4)
        else:
            out.append({"debut": round(pos, 4), "fin": round(pos + d, 4), "viseme": v})
        pos += d
    out = [x for x in out if x["fin"] > x["debut"]]
    if out and out[-1]["viseme"] != "X":
        out.append({"debut": out[-1]["fin"], "fin": round(out[-1]["fin"] + 0.2, 4), "viseme": "X"})
    return out


def visemes_depuis_rhubarb(donnees) -> list[dict]:
    """Le JSON de Rhubarb Lip Sync (`rhubarb -f json voix.wav`) : {"mouthCues": [{start, end, value}]}."""
    if isinstance(donnees, (str, bytes)):
        donnees = json.loads(donnees)
    cues = (donnees or {}).get("mouthCues") if isinstance(donnees, dict) else None
    if not isinstance(cues, list):
        raise VisageRefuse("JSON Rhubarb illisible (mouthCues absent)")
    out = []
    for c in cues[:MAX_CLES_PAR_COMMANDE]:
        try:
            d, f, v = float(c["start"]), float(c["end"]), str(c["value"]).upper()
        except (KeyError, TypeError, ValueError):
            continue
        if v in VISEMES and math.isfinite(d) and math.isfinite(f) and f > d >= 0:
            out.append({"debut": round(d, 4), "fin": round(f, 4), "viseme": v})
    return out


def enveloppe_wav(chemin, fps: int = FPS_DEFAUT) -> tuple[list[float], float]:
    """L'énergie (RMS normalisée 0..1) d'un WAV PCM 8/16/32 bits, une valeur par image. Rend (valeurs, durée_s)."""
    with wave.open(str(chemin), "rb") as w:
        n_can, larg, freq, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        brut = w.readframes(n)
    if larg not in (1, 2, 4) or freq <= 0:
        raise VisageRefuse("WAV non pris en charge (PCM 8, 16 ou 32 bits)")
    fmt = {1: "B", 2: "h", 4: "i"}[larg]
    echant = struct.unpack("<%d%s" % (len(brut) // larg, fmt), brut[: (len(brut) // larg) * larg])
    if larg == 1:
        echant = [x - 128 for x in echant]
    if n_can > 1:
        echant = echant[::n_can]
    duree = n / float(freq)
    par_image = max(1, int(round(freq / float(fps))))
    vals = []
    for i in range(0, len(echant), par_image):
        bloc = echant[i:i + par_image]
        vals.append(math.sqrt(sum(x * x for x in bloc) / len(bloc)) if bloc else 0.0)
    haut = sorted(vals)[int(len(vals) * 0.95)] if vals else 0.0
    if haut <= 0:
        return [0.0] * len(vals), duree
    return [min(1.0, v / haut) for v in vals], duree


# ── courbes ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def _blinks(duree_s: float, graine: int = 7, intervalle=(2.2, 5.0)) -> list[float]:
    """Instants de clignement, réguliers mais irréguliers (pseudo-aléatoire DÉTERMINISTE)."""
    x, t, out = (graine * 2654435761) & 0xFFFFFFFF, 0.8, []
    a, b = intervalle
    while t < duree_s - 0.3:
        out.append(round(t, 3))
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        t += a + (b - a) * (x / 0x7FFFFFFF)
    return out


def _expression_a(t: float, expressions: list[dict]) -> dict[str, float]:
    """Les poids d'expression à l'instant t : chaque expression monte en `fondu` s depuis son début, tient, et
    s'efface en `fondu` s à sa fin ; elles s'additionnent (bornées à 1)."""
    out: dict[str, float] = {}
    for e in expressions:
        d, f, fondu = e["debut"], e["fin"], max(0.05, e.get("fondu", 0.3))
        if t <= d - 1e-9 or t >= f + fondu:
            continue
        if t < d + fondu:
            k = (t - d) / fondu
        elif t <= f:
            k = 1.0
        else:
            k = 1.0 - (t - f) / fondu
        k = max(0.0, min(1.0, k)) * e.get("intensite", 1.0)
        for c, w in EXPRESSIONS[e["nom"]].items():
            out[c] = min(1.0, out.get(c, 0.0) + w * k)
    return out


def courbes(visemes: list[dict], *, fps: int = FPS_DEFAUT, expressions: list[dict] | None = None,
            clignements: bool = True, enveloppe: list[float] | None = None, debut_image: int = 1,
            duree_s: float | None = None, intensite_bouche: float = 1.0, graine: int = 7) -> dict:
    """PUR — les courbes de chaque commande : {"controles": {cmd: [[image, valeur]]}, "visemes": {lettre: [[image,
    valeur]]}, "expression": {cmd: …}, "images": [debut, fin]}.
      * `controles` = bouche (visèmes → commandes ARKit) + expressions + clignements : pour un visage à commandes ;
      * `visemes` = une courbe 0/1 par visème (fondus d'1 image) : pour un visage à CLÉS DE VISÈMES (Oculus, VRM) ;
      * `expression` = expressions + clignements seuls : complète `visemes` sans doubler la bouche.
    `enveloppe` (énergie du WAV par image) module l'ouverture : la bouche se ferme dans les silences."""
    expressions = [_expr_valide(e) for e in (expressions or [])]
    fin_s = max([v["fin"] for v in visemes] + [e["fin"] + e.get("fondu", 0.3) for e in expressions]
                + [float(duree_s or 0)] + [0.5])
    n_images = min(MAX_IMAGES, int(math.ceil(fin_s * fps)) + 1)

    def image(t):
        return debut_image + int(round(t * fps))

    # instants clés : début de chaque visème (+ une image avant pour tenir le précédent), expressions, clignements
    instants = {0.0, fin_s}
    for v in visemes:
        instants.add(v["debut"])
        instants.add(max(0.0, v["debut"] - 1.0 / fps))
    for e in expressions:
        for t in (e["debut"], e["debut"] + e.get("fondu", 0.3), e["fin"], e["fin"] + e.get("fondu", 0.3)):
            instants.add(max(0.0, t))
    blinks = _blinks(fin_s, graine) if clignements else []
    for b in blinks:
        for dt in (-0.06, 0.0, 0.05, 0.16):
            instants.add(max(0.0, b + dt))

    def viseme_a(t):
        cur = "X"
        for v in visemes:
            if v["debut"] <= t + 1e-9:
                cur = v["viseme"] if t < v["fin"] + 1e-9 else "X"
            else:
                break
        return cur

    def blink_a(t):
        for b in blinks:
            if b - 0.06 <= t <= b + 0.16:
                return 1.0 if b - 1e-9 <= t <= b + 0.05 + 1e-9 else 0.0
        return 0.0

    controles: dict[str, list] = {c: [] for c in COMMANDES}
    expression: dict[str, list] = {c: [] for c in COMMANDES if c not in BOUCHE}
    vis_courbes: dict[str, list] = {v: [] for v in VISEMES}
    vus = set()
    for t in sorted(instants):
        im = image(t)
        if im in vus or im - debut_image >= n_images:
            continue
        vus.add(im)
        vis = viseme_a(t)
        mod = 1.0
        if enveloppe:
            k = min(len(enveloppe) - 1, max(0, int(round(t * fps))))
            mod = 0.25 + 0.75 * enveloppe[k] if vis != "X" else 1.0
        expr = _expression_a(t, expressions)
        bl = blink_a(t)
        for c in COMMANDES:
            b = VISEME_COMMANDES[vis].get(c, 0.0) * intensite_bouche * (mod if c in ("jawOpen",) else 1.0)
            val = min(1.0, b + expr.get(c, 0.0))
            if c in ("eyeBlinkLeft", "eyeBlinkRight"):
                val = max(val, bl)
            controles[c].append([im, round(val, 3)])
            if c in expression:
                expression[c].append([im, round(val, 3)])
        for v in VISEMES:
            vis_courbes[v].append([im, 1.0 if v == vis else 0.0])
    # on retire les courbes plates à 0 (rien à animer)
    controles = {c: k for c, k in controles.items() if any(v for _, v in k)}
    expression = {c: k for c, k in expression.items() if any(v for _, v in k)}
    vis_courbes = {v: k for v, k in vis_courbes.items() if any(x for _, x in k)}
    return {"controles": controles, "visemes": vis_courbes, "expression": expression,
            "images": [debut_image, debut_image + n_images - 1], "clignements": len(blinks)}


def _expr_valide(e) -> dict:
    if not isinstance(e, dict) or e.get("nom") not in EXPRESSIONS:
        raise VisageRefuse("expression inconnue (attendu : %s)" % ", ".join(EXPRESSIONS))
    try:
        d, f = float(e.get("debut", 0)), float(e.get("fin", 0))
        i = float(e.get("intensite", 1.0))
        fo = float(e.get("fondu", 0.3))
    except (TypeError, ValueError):
        raise VisageRefuse("expression : nombres illisibles") from None
    if not all(math.isfinite(x) for x in (d, f, i, fo)) or f < d or d < 0 or not 0 <= i <= 1 or not 0 <= fo <= 5:
        raise VisageRefuse("expression : bornes invalides")
    return {"nom": e["nom"], "debut": d, "fin": f, "intensite": i, "fondu": fo}


# ── paramètres du script ────────────────────────────────────────────────────────────────────────────────────────────

def nom_sur(texte, defaut: str = "") -> str:
    t = _sans_accent(str(texte or "")).strip()
    t = _NOM_SUR.sub("", t)[:MAX_NOM].strip()
    return t or defaut


def parametres(*, texte: str = "", rhubarb=None, wav: str | None = None, expressions=None, clignements: bool = True,
               fps: int = FPS_DEFAUT, debut_image: int = 1, objet: str = "", armature: str = "", mode: str = "auto",
               face: str = "-Y", reperes: dict | None = None, amplitude: float = AMPLITUDE_DEFAUT,
               intensite_bouche: float = 1.0, os_reglages: dict | None = None, source: str | None = None,
               sortie_blend: str | None = None, sortie_glb: str | None = None, graine: int = 7) -> dict:
    """Les paramètres complets du GABARIT. Source des visèmes, par ordre : `rhubarb` (JSON), sinon `texte` (étiré sur
    la durée du `wav` s'il est donné) ; le `wav` module aussi l'ouverture de la mâchoire."""
    env, duree = None, None
    if wav:
        env, duree = enveloppe_wav(wav, fps)
    if rhubarb is not None:
        vis = visemes_depuis_rhubarb(rhubarb)
    elif texte:
        vis = visemes_depuis_texte(texte, duree)
    elif env:
        vis = _visemes_depuis_enveloppe(env, fps)
    else:
        vis = []
    c = courbes(vis, fps=fps, expressions=expressions, clignements=clignements, enveloppe=env,
                debut_image=debut_image, duree_s=duree, intensite_bouche=intensite_bouche, graine=graine)
    p = {"version": VERSION, "fps": int(fps), "images": c["images"], "mode": mode, "face": face,
         "objet": nom_sur(objet), "armature": nom_sur(armature),
         "reperes": _reperes(reperes), "amplitude": float(amplitude),
         "controles": c["controles"], "visemes": c["visemes"], "expression": c["expression"],
         "os_reglages": _os_reglages(os_reglages), "source": source or "", "sortie_blend": sortie_blend or "",
         "sortie_glb": sortie_glb or ""}
    verifier(p)
    return p


def _visemes_depuis_enveloppe(env: list[float], fps: int) -> list[dict]:
    """Sans texte ni Rhubarb : l'énergie seule choisit repos / entrouverte / ouverte / grande ouverte."""
    out = []
    for i, e in enumerate(env):
        v = "X" if e < 0.12 else "B" if e < 0.35 else "C" if e < 0.65 else "D"
        t = i / float(fps)
        if out and out[-1]["viseme"] == v:
            out[-1]["fin"] = round(t + 1.0 / fps, 4)
        else:
            out.append({"debut": round(t, 4), "fin": round(t + 1.0 / fps, 4), "viseme": v})
    return out


def _reperes(r) -> dict:
    out = json.loads(json.dumps(REPERES_DEFAUT))
    if isinstance(r, dict):
        for k in ("bouche", "oeil_gauche", "oeil_droit"):
            if k in r:
                out[k] = r[k]
        for k in ("sourcils_v", "largeur_bouche"):
            if k in r:
                out[k] = r[k]
    return out


_CANAUX = ("haut", "avant", "cote", "rotation")


def _os_reglages(r) -> dict:
    """{nom_d_os: {commande, canal (haut|avant|cote|rotation), gain}} : force la commande et le geste d'un os."""
    out = {}
    if not isinstance(r, dict):
        return out
    for nom, v in list(r.items())[:40]:
        if not isinstance(v, dict):
            continue
        out[nom_sur(nom, "os")] = {"commande": v.get("commande"), "canal": v.get("canal"), "gain": v.get("gain", 1.0)}
    return out


def _nombre(v, a, b, nom):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not a <= v <= b:
        raise VisageRefuse(f"{nom} hors bornes")


def _chemin(v, suffixes) -> None:
    if v == "":
        return
    if not isinstance(v, str) or len(v) > MAX_CHEMIN or not v.lower().endswith(suffixes) \
            or any(ord(ch) < 32 for ch in v) or ".." in v.replace("\\", "/").split("/") \
            or not (re.match(r"^[A-Za-z]:[\\/]", v) or v.startswith("/")):
        raise VisageRefuse("chemin illisible (absolu, sans « .. », extension attendue)")


def _courbe(k, nom):
    if not isinstance(k, list) or len(k) > MAX_CLES_PAR_COMMANDE:
        raise VisageRefuse(f"courbe {nom} illisible")
    for x in k:
        if not (isinstance(x, list) and len(x) == 2):
            raise VisageRefuse(f"courbe {nom} illisible")
        _nombre(x[0], -100000, 1000000, nom)
        _nombre(x[1], 0.0, 1.0, nom)


def verifier(p: dict) -> None:
    """Ce qui entre dans le script est re-vérifié ici : énumérations fermées, nombres finis bornés, noms sûrs."""
    if not isinstance(p, dict) or p.get("version") != VERSION:
        raise VisageRefuse("version")
    _nombre(p.get("fps"), 1, 240, "fps")
    im = p.get("images")
    if not (isinstance(im, list) and len(im) == 2):
        raise VisageRefuse("images")
    _nombre(im[0], -100000, 1000000, "images")
    _nombre(im[1], -100000, 1000000, "images")
    if p.get("mode") not in MODES:
        raise VisageRefuse("mode (auto, cles, os, procedural)")
    if p.get("face") not in FACES:
        raise VisageRefuse("face (-Y ou +Y)")
    for k in ("objet", "armature"):
        if not isinstance(p.get(k), str) or p[k] != nom_sur(p[k]):
            raise VisageRefuse(f"{k} : nom illisible")
    _nombre(p.get("amplitude"), 0.1, 3.0, "amplitude")
    r = p.get("reperes")
    if not isinstance(r, dict) or set(r) != set(REPERES_DEFAUT):
        raise VisageRefuse("reperes")
    for k in ("bouche", "oeil_gauche", "oeil_droit"):
        if not (isinstance(r[k], list) and len(r[k]) == 2):
            raise VisageRefuse("reperes")
        for x in r[k]:
            _nombre(x, 0.0, 1.0, "reperes")
    _nombre(r["sourcils_v"], 0.0, 1.0, "reperes")
    _nombre(r["largeur_bouche"], 0.05, 0.9, "reperes")
    for groupe, noms in (("controles", COMMANDES), ("expression", COMMANDES), ("visemes", VISEMES)):
        g = p.get(groupe)
        if not isinstance(g, dict) or set(g) - set(noms):
            raise VisageRefuse(groupe)
        for n, k in g.items():
            _courbe(k, n)
    o = p.get("os_reglages")
    if not isinstance(o, dict) or len(o) > 40:
        raise VisageRefuse("os_reglages")
    for nom, v in o.items():
        if nom != nom_sur(nom) or not nom:
            raise VisageRefuse("os_reglages : nom")
        if v.get("commande") not in COMMANDES or v.get("canal") not in _CANAUX:
            raise VisageRefuse("os_reglages : commande ou canal")
        _nombre(v.get("gain"), -5.0, 5.0, "os_reglages.gain")
    _chemin(p.get("source", ""), (".blend", ".glb", ".gltf", ".fbx"))
    _chemin(p.get("sortie_blend", ""), (".blend",))
    _chemin(p.get("sortie_glb", ""), (".glb",))


def generer_script(params: dict) -> str:
    """Le script : le GABARIT fixe, son unique trou rempli par le repr() d'un JSON ASCII vérifié."""
    verifier(params)
    brut = json.dumps(params, ensure_ascii=True, sort_keys=True)
    return GABARIT.replace("__PARAMS__", repr(brut), 1)


def argv_headless(exe: str, script: Path, blend: str | None = None) -> list[str]:
    """Blender en arrière-plan, réglages d'usine, sans son ; ouvre `blend` s'il est donné (sinon la source .glb/.fbx
    est importée par le script)."""
    a = [str(exe), "-b"]
    if blend:
        a.append(str(blend))
    return a + ["--factory-startup", "-noaudio", "--python-exit-code", "3", "--python", str(script)]


def animer_fichier(params: dict, blend: str | None = None, delai_s: int = 600) -> dict:
    """Blender en ARRIÈRE-PLAN : écrit le script (gabarit + paramètres vérifiés) dans un dossier temporaire, lance
    Blender (passes_blender.etat_blender : BLENDER_PATH, sinon le plus récent installé), lit la ligne DZVISAGE.
    `blend` : le .blend à ouvrir (sinon `params["source"]` .glb/.fbx est importé dans une scène vide)."""
    import subprocess
    import tempfile
    from app.services import passes_blender as PB
    e = PB.etat_blender()
    if not e.get("dispo"):
        raise VisageRefuse("Blender introuvable ou trop ancien (Réglages › Moteurs et logiciels 3D)")
    with tempfile.TemporaryDirectory(prefix="dzvisage_") as d:
        sc = Path(d) / "visage.py"
        sc.write_text(generer_script(params), encoding="utf-8")
        r = subprocess.run(argv_headless(e["exe"], sc, blend), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=delai_s)
    res = lire_resume(r.stdout) or {"erreurs": ["Blender n'a rien rendu (code %s)" % r.returncode]}
    res["code"] = r.returncode
    return res


def lire_resume(texte: str) -> dict | None:
    """PUR — la ligne « DZVISAGE {json} » imprimée par le script."""
    for ligne in str(texte or "").splitlines():
        i = ligne.find("DZVISAGE ")
        if i >= 0:
            try:
                v = json.loads(ligne[i + len("DZVISAGE "):].strip())
            except ValueError:
                return None
            return v if isinstance(v, dict) else None
    return None


# Le texte n'appelle que bpy, mathutils, json et math, sans import dynamique ni nom d'attribut calculé : il passe le
# validateur du mode sûr de mcp-for-blender (banc test_visage_blender).
GABARIT = r'''# Script GENERE par DeepotusVideo (animation faciale) : les parametres sont des donnees.
import json
import math
import bpy
import mathutils

P = json.loads(__PARAMS__)
scene = bpy.context.scene
resume = {"mode": "", "objet": "", "armature": "", "animees": [], "absentes": [], "crees": [], "erreurs": []}

# --- noms reconnus --------------------------------------------------------------------------------------------
ARKIT_ALIAS = {
    "jawOpen": ["jawopen", "mouthopen", "jaw_open", "mouth_open", "openmouth", "aa"],
    "mouthClose": ["mouthclose", "mouth_close"],
    "mouthFunnel": ["mouthfunnel", "funnel"],
    "mouthPucker": ["mouthpucker", "pucker", "kiss"],
    "mouthPress": ["mouthpressleft", "mouthpress", "mouthpressright"],
    "mouthSmileLeft": ["mouthsmileleft", "mouthsmile_l", "smile_l", "smileleft", "mouthsmile", "smile", "joy"],
    "mouthSmileRight": ["mouthsmileright", "mouthsmile_r", "smile_r", "smileright", "mouthsmile", "smile", "joy"],
    "mouthFrownLeft": ["mouthfrownleft", "mouthfrown_l", "frown_l", "mouthfrown", "frown", "sorrow"],
    "mouthFrownRight": ["mouthfrownright", "mouthfrown_r", "frown_r", "mouthfrown", "frown", "sorrow"],
    "mouthStretchLeft": ["mouthstretchleft", "mouthstretch_l"],
    "mouthStretchRight": ["mouthstretchright", "mouthstretch_r"],
    "eyeBlinkLeft": ["eyeblinkleft", "eyeblink_l", "blink_l", "blinkleft", "eyesclosed", "blink", "eyeblink"],
    "eyeBlinkRight": ["eyeblinkright", "eyeblink_r", "blink_r", "blinkright", "eyesclosed", "blink", "eyeblink"],
    "eyeWideLeft": ["eyewideleft", "eyewide_l"],
    "eyeWideRight": ["eyewideright", "eyewide_r"],
    "eyeSquintLeft": ["eyesquintleft", "eyesquint_l"],
    "eyeSquintRight": ["eyesquintright", "eyesquint_r"],
    "browInnerUp": ["browinnerup", "browsup", "brows_up", "surprised"],
    "browOuterUpLeft": ["browouterupleft", "browouterup_l", "browup_l"],
    "browOuterUpRight": ["browouterupright", "browouterup_r", "browup_r"],
    "browDownLeft": ["browdownleft", "browdown_l", "angry"],
    "browDownRight": ["browdownright", "browdown_r", "angry"],
}
VISEME_ALIAS = {
    "A": ["viseme_pp", "vrc.v_pp", "v_pp", "pp", "m"],
    "B": ["viseme_kk", "vrc.v_kk", "viseme_ss", "vrc.v_ss", "i", "ih", "kk"],
    "C": ["viseme_e", "vrc.v_e", "e", "eh"],
    "D": ["viseme_aa", "vrc.v_aa", "a", "aa"],
    "E": ["viseme_o", "vrc.v_oh", "o", "oh"],
    "F": ["viseme_u", "vrc.v_ou", "u", "ou"],
    "G": ["viseme_ff", "vrc.v_ff", "ff"],
    "H": ["viseme_nn", "vrc.v_nn", "viseme_dd", "nn"],
}


def norm(t):
    return "".join(c for c in t.lower() if c.isalnum() or c in "._")


def dire():
    print("DZVISAGE " + json.dumps(resume))


# --- la cible ---------------------------------------------------------------------------------------------------
def maillages():
    return [o for o in scene.objects if o.type == "MESH"]


def choisir_objet():
    if P["objet"]:
        o = bpy.data.objects.get(P["objet"])
        if o is not None and o.type == "MESH":
            return o
        resume["erreurs"].append("objet introuvable : " + P["objet"])
    meilleurs = []
    for o in maillages():
        n = len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0
        meilleurs.append((n, len(o.data.vertices), o.name, o))
    if not meilleurs:
        return None
    meilleur = meilleurs[0]
    for m in meilleurs:
        if (m[0], m[1]) > (meilleur[0], meilleur[1]):
            meilleur = m
    return meilleur[3]


def choisir_armature(obj):
    if P["armature"]:
        a = bpy.data.objects.get(P["armature"])
        if a is not None and a.type == "ARMATURE":
            return a
    if obj is not None:
        for m in obj.modifiers:
            if m.type == "ARMATURE" and m.object is not None:
                return m.object
        if obj.parent is not None and obj.parent.type == "ARMATURE":
            return obj.parent
    arms = [o for o in scene.objects if o.type == "ARMATURE"]
    meilleure = None
    for a in arms:
        if meilleure is None or len(a.pose.bones) > len(meilleure.pose.bones):
            meilleure = a
    return meilleure


# --- courbes --------------------------------------------------------------------------------------------------
def poser_cle(kb, courbe, gain):
    effacer_plage(kb.id_data, [kb.name])
    for f, v in courbe:
        kb.value = max(0.0, min(1.0, v * gain))
        kb.keyframe_insert("value", frame=int(f))


def effacer_plage(idb, noms):
    """Retire, sur la plage animee, les cles des SEULES courbes qu'on va reposer (cles de forme ou os nommes) :
    l'animation du corps et les autres canaux restent intacts."""
    ad = idb.animation_data
    if ad is None or ad.action is None:
        return
    i0, i1 = P["images"]
    for fc in action_courbes(ad.action):
        if not any(('["' + n + '"]') in fc.data_path for n in noms):
            continue
        pts = [k for k in fc.keyframe_points if i0 - 0.5 <= k.co[0] <= i1 + 0.5]
        for k in reversed(pts):
            fc.keyframe_points.remove(k)


def action_courbes(action):
    try:
        return list(action.fcurves)
    except AttributeError:
        out = []
        for couche in action.layers:
            for bande in couche.strips:
                for sac in bande.channelbags:
                    out.extend(list(sac.fcurves))
        return out


def trouver_cle(blocs, alias):
    noms = {}
    for kb in blocs:
        noms.setdefault(norm(kb.name), kb)
    for a in alias:
        if norm(a) in noms:
            return noms[norm(a)]
    return None


def animer_cles(obj):
    """Les clés de forme existantes : visemes si le personnage en a, sinon commandes ARKit."""
    sk = obj.data.shape_keys
    if sk is None:
        return False
    blocs = [kb for kb in sk.key_blocks if kb != sk.reference_key]
    if not blocs:
        return False
    vis = {}
    for v, alias in VISEME_ALIAS.items():
        kb = trouver_cle(blocs, alias)
        if kb is not None:
            vis[v] = kb
    utilise_visemes = len(vis) >= 4 and P["visemes"]
    deja = set()
    if utilise_visemes:
        for v, kb in vis.items():
            if v in P["visemes"]:
                poser_cle(kb, P["visemes"][v], P["amplitude"])
                deja.add(kb.name)
                resume["animees"].append("viseme " + v + " -> " + kb.name)
        source = P["expression"]
    else:
        source = P["controles"]
    for c, courbe in source.items():
        kb = trouver_cle(blocs, ARKIT_ALIAS.get(c, [c]))
        if kb is None:
            resume["absentes"].append(c)
            continue
        if kb.name in deja:
            continue
        deja.add(kb.name)
        poser_cle(kb, courbe, P["amplitude"])
        resume["animees"].append(c + " -> " + kb.name)
    return bool(deja)


# --- os du visage ---------------------------------------------------------------------------------------------
def axes_perso(arm):
    """Haut, avant et gauche du personnage dans le repere de l'armature."""
    inv = arm.matrix_world.to_3x3().inverted()
    haut = (inv @ mathutils.Vector((0.0, 0.0, 1.0))).normalized()
    avant = mathutils.Vector((0.0, -1.0, 0.0)) if P["face"] == "-Y" else mathutils.Vector((0.0, 1.0, 0.0))
    avant = (inv @ avant).normalized()
    gauche_perso = haut.cross(avant).normalized()   # la gauche du personnage
    return haut, avant, gauche_perso


def cote(nom):
    n = nom.lower()
    if n.endswith((".l", "_l", "-l", "left", ".l.001", ".l.002")) or ".l." in n or "_l_" in n or "left" in n:
        return "L"
    if n.endswith((".r", "_r", "-r", "right", ".r.001", ".r.002")) or ".r." in n or "_r_" in n or "right" in n:
        return "R"
    return ""


def est_mecanique(nom):
    n = nom.lower()
    return n.startswith(("mch", "org", "def", "str-", "tgt", "vis_", "wgt"))


def classer_os(arm):
    """Associe des os du visage aux commandes : (commande, os, canal, gain)."""
    trouve = []
    pris = set()
    for nom, r in P["os_reglages"].items():
        pb = arm.pose.bones.get(nom)
        if pb is not None:
            trouve.append((r["commande"], pb, r["canal"], r["gain"]))
            pris.add(nom)
    poses = [pb for pb in arm.pose.bones if pb.name not in pris]
    controles = [pb for pb in poses if not est_mecanique(pb.name)] or poses

    def est_jaw(n):
        return n in ("jaw_master", "jaw", "c_jawbone.x", "jaw_ctrl") or "jaw" in n

    jaw = None
    for liste in (controles, poses):
        for pb in liste:
            if jaw is None and est_jaw(pb.name.lower()):
                jaw = pb
    if jaw is not None:
        trouve.append(("jawOpen", jaw, "rotation", 1.0))
    for c_cmd, c_suf in (("Left", "L"), ("Right", "R")):
        coin = None
        for liste in (controles, poses):
            for pb in liste:
                n = pb.name.lower()
                if cote(n) == c_suf and (("lip" in n and ("corner" in n or n.startswith("lips."))) or
                                         "mouth_corner" in n or "lips_corner" in n or "c_lips_smile" in n):
                    coin = pb
                    break
            if coin is not None:
                break
        if coin is not None:
            trouve.append(("mouthSmile" + c_cmd, coin, "haut", 1.0))
            trouve.append(("mouthFrown" + c_cmd, coin, "haut", -1.0))
            trouve.append(("mouthStretch" + c_cmd, coin, "cote", 1.0))
        lid = None
        for liste in (controles, poses):
            for pb in liste:
                n = pb.name.lower()
                if cote(n) == c_suf and ("lid" in n or "eyelid" in n or "paupiere" in n) and \
                        ("t" in n.split(".") or "top" in n or "upper" in n or "_up" in n or ".t." in n or "lid.t" in n):
                    lid = pb
                    break
            if lid is not None:
                break
        if lid is not None:
            trouve.append(("eyeBlink" + c_cmd, lid, "haut", -1.0))
            trouve.append(("eyeWide" + c_cmd, lid, "haut", 0.5))
        brow = None
        for liste in (controles, poses):
            for pb in liste:
                n = pb.name.lower()
                if cote(n) == c_suf and ("brow" in n or "sourcil" in n):
                    brow = pb
                    break
            if brow is not None:
                break
        if brow is not None:
            trouve.append(("browOuterUp" + c_cmd, brow, "haut", 1.0))
            trouve.append(("browDown" + c_cmd, brow, "haut", -1.0))
            trouve.append(("browInnerUp", brow, "haut", 0.7))
    return trouve


def animer_os(arm):
    sel = classer_os(arm)
    if not sel:
        return False
    haut, avant, gauche = axes_perso(arm)
    taille = max(arm.dimensions) if max(arm.dimensions) > 0 else 1.0
    dep = 0.012 * taille * P["amplitude"]        # deplacement plein d'une commande (1,2 % de la taille)
    angle = math.radians(18.0) * P["amplitude"]  # ouverture pleine de la machoire
    par_os = {}
    for cmd, pb, canal, gain in sel:
        if cmd not in P["controles"]:
            continue
        par_os.setdefault(pb.name, (pb, []))[1].append((cmd, canal, gain))
    for nom, (pb, gestes) in par_os.items():
        effacer_plage(arm, [nom])
        rep = pb.bone.matrix_local.to_3x3().inverted()
        images = sorted(set(int(f) for cmd, canal, gain in gestes for f, v in P["controles"][cmd]))
        valeurs = {}
        for cmd, canal, gain in gestes:
            valeurs[cmd] = dict((int(f), v) for f, v in P["controles"][cmd])
        dernier = {}
        for f in images:
            loc = mathutils.Vector((0.0, 0.0, 0.0))
            rot = 0.0
            for cmd, canal, gain in gestes:
                if f in valeurs[cmd]:
                    dernier[cmd] = valeurs[cmd][f]
                v = dernier.get(cmd, 0.0) * gain
                if canal == "rotation":
                    rot += v
                elif canal == "haut":
                    loc += haut * (v * dep)
                elif canal == "avant":
                    loc += avant * (v * dep)
                else:
                    sens = 1.0 if cote(pb.name) == "L" else -1.0
                    loc += gauche * (v * dep * sens)
            if any(canal != "rotation" for _, canal, _ in gestes):
                pb.location = rep @ loc
                pb.keyframe_insert("location", frame=f)
            if any(canal == "rotation" for _, canal, _ in gestes):
                axe = (rep @ gauche).normalized()
                q = mathutils.Quaternion(axe, rot * angle)   # + autour de la gauche du perso = menton qui descend
                if pb.rotation_mode == "QUATERNION":
                    pb.rotation_quaternion = q
                    pb.keyframe_insert("rotation_quaternion", frame=f)
                elif pb.rotation_mode == "AXIS_ANGLE":
                    a = q.to_axis_angle()
                    pb.rotation_axis_angle = (a[1], a[0][0], a[0][1], a[0][2])
                    pb.keyframe_insert("rotation_axis_angle", frame=f)
                else:
                    pb.rotation_euler = q.to_euler(pb.rotation_mode)
                    pb.keyframe_insert("rotation_euler", frame=f)
        resume["animees"].append(nom + " <- " + ", ".join(sorted(set(c for c, _, _ in gestes))))
    return bool(par_os)


# --- procedural : sculpter des cles DZ_ sur un maillage sans visage animable ---------------------------------
def tete(obj, arm):
    """La boite de la tete dans le repere monde : (centre, largeur, hauteur, profondeur, z_bas)."""
    mw = obj.matrix_world
    pts = [mw @ v.co for v in obj.data.vertices]
    zmin = min(p.z for p in pts)
    zmax = max(p.z for p in pts)
    bas = zmax - (zmax - zmin) * 0.14
    if arm is not None:
        for pb in arm.pose.bones:
            n = pb.name.lower()
            if n in ("head", "tete", "c_head.x", "def-head", "org-head") or n.endswith("head"):
                tete_bas = (arm.matrix_world @ pb.bone.head_local).z
                if zmin < tete_bas < zmax:
                    bas = tete_bas
                break
    sel = [p for p in pts if p.z >= bas]
    if len(sel) < 20:
        sel = pts
    xs = [p.x for p in sel]
    ys = [p.y for p in sel]
    zs = [p.z for p in sel]
    centre = mathutils.Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    return centre, max(xs) - min(xs), max(zs) - min(zs), max(ys) - min(ys), min(zs), bas


def lisse(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def sculpter(obj, arm):
    mw = obj.matrix_world
    inv = mw.inverted()
    centre, larg, haut, prof, zbas, coupe = tete(obj, arm)
    av = -1.0 if P["face"] == "-Y" else 1.0           # signe de l'avant sur Y
    R = P["reperes"]
    # u = 0 au bord GAUCHE de l'image vue de face ; si l'avant est -Y, le bord gauche de l'image est en -X
    G = {"av": av, "larg": larg, "haut": haut, "prof": prof, "A": P["amplitude"],
         "bx": centre.x + (R["bouche"][0] - 0.5) * larg * (-av), "bz": zbas + R["bouche"][1] * haut,
         "gx": centre.x + (R["oeil_gauche"][0] - 0.5) * larg * (-av), "gz": zbas + R["oeil_gauche"][1] * haut,
         "dx": centre.x + (R["oeil_droit"][0] - 0.5) * larg * (-av), "dz": zbas + R["oeil_droit"][1] * haut,
         "sz": zbas + R["sourcils_v"] * haut, "lb": R["largeur_bouche"] * larg, "gauche_x": -av}
    G["pivot"] = mathutils.Vector((centre.x, centre.y - av * 0.05 * prof, G["bz"] + 0.12 * haut))
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    base = [v.co.copy() for v in obj.data.vertices]
    monde = [mw @ c for c in base]
    devant = [i for i, p in enumerate(monde) if p.z >= coupe - 0.05 * haut and (p.y - centre.y) * av > -0.05 * prof]
    for cmd in FORMES:
        if cmd not in P["controles"]:
            continue
        nom = "DZ_" + cmd
        vieux = obj.data.shape_keys.key_blocks.get(nom)
        if vieux is not None:
            obj.shape_key_remove(vieux)
        kb = obj.shape_key_add(name=nom, from_mix=False)
        n = 0
        for i in devant:
            d = deplacement(cmd, monde[i], G)
            if d is not None:
                kb.data[i].co = inv @ (monde[i] + d)
                n += 1
        resume["crees"].append(nom + " (" + str(n) + " sommets)")


FORMES = ["jawOpen", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight", "mouthStretchLeft",
          "mouthStretchRight", "mouthPucker", "mouthFunnel", "eyeBlinkLeft", "eyeBlinkRight", "browOuterUpLeft",
          "browOuterUpRight", "browDownLeft", "browDownRight", "browInnerUp"]


def machoire(p, G):
    bz, haut = G["bz"], G["haut"]
    if p.z > bz + 0.01 * haut:
        return None
    w = lisse((bz + 0.01 * haut - p.z) / (0.06 * haut)) * lisse(1.0 - abs(p.x - G["bx"]) / (0.6 * G["larg"]))
    if w <= 0:
        return None
    ang = math.radians(16.0) * G["A"] * w
    q = mathutils.Quaternion(mathutils.Vector((1.0, 0.0, 0.0)), -ang * G["av"])
    return (q @ (p - G["pivot"])) + G["pivot"] - p


def coin(p, G, sens_x, haut_k, cote_k):
    lb = G["lb"]
    cx = G["bx"] + sens_x * lb / 2
    d = math.sqrt((p.x - cx) ** 2 + (p.z - G["bz"]) ** 2)
    w = lisse(1.0 - d / (0.45 * lb))
    if w <= 0:
        return None
    return mathutils.Vector((sens_x * cote_k * 0.06 * lb * w * G["A"], 0.0, haut_k * 0.035 * G["haut"] * w * G["A"]))


def moue(p, G, entonnoir):
    d = math.sqrt((p.x - G["bx"]) ** 2 + (p.z - G["bz"]) ** 2)
    w = lisse(1.0 - d / (0.7 * G["lb"]))
    if w <= 0:
        return None
    v = mathutils.Vector(((G["bx"] - p.x) * 0.35 * w * G["A"], G["av"] * 0.04 * G["prof"] * w * G["A"], 0.0))
    if entonnoir:
        v.z += (0.02 * G["haut"] if p.z > G["bz"] else -0.025 * G["haut"]) * w * G["A"]
    return v


def paupiere(p, G, ex, ez):
    r = 0.16 * G["larg"]
    d = math.sqrt((p.x - ex) ** 2 + (p.z - ez) ** 2)
    if d > r or p.z < ez - 0.01 * G["haut"]:
        return None
    w = lisse(1.0 - d / r)
    return mathutils.Vector((0.0, 0.0, -(p.z - (ez - 0.01 * G["haut"])) * 0.9 * w))


def sourcil(p, G, ex, signe, rayon):
    d = math.sqrt((p.x - ex) ** 2 + ((p.z - G["sz"]) * 1.6) ** 2)
    w = lisse(1.0 - d / (rayon * G["larg"]))
    if w <= 0:
        return None
    return mathutils.Vector((0.0, 0.0, signe * 0.03 * G["haut"] * w * G["A"]))


def deplacement(cmd, p, G):
    """Le deplacement (monde) d'un sommet pour la forme `cmd` ; None = sommet hors de la forme."""
    gx = G["gauche_x"]
    if cmd == "jawOpen":
        return machoire(p, G)
    if cmd == "mouthSmileLeft":
        return coin(p, G, gx, 1.0, 1.0)
    if cmd == "mouthSmileRight":
        return coin(p, G, -gx, 1.0, 1.0)
    if cmd == "mouthFrownLeft":
        return coin(p, G, gx, -1.0, 0.3)
    if cmd == "mouthFrownRight":
        return coin(p, G, -gx, -1.0, 0.3)
    if cmd == "mouthStretchLeft":
        return coin(p, G, gx, 0.0, 1.5)
    if cmd == "mouthStretchRight":
        return coin(p, G, -gx, 0.0, 1.5)
    if cmd == "mouthPucker":
        return moue(p, G, False)
    if cmd == "mouthFunnel":
        return moue(p, G, True)
    if cmd == "eyeBlinkLeft":
        return paupiere(p, G, G["gx"], G["gz"])
    if cmd == "eyeBlinkRight":
        return paupiere(p, G, G["dx"], G["dz"])
    if cmd == "browOuterUpLeft":
        return sourcil(p, G, G["gx"], 1.0, 0.2)
    if cmd == "browOuterUpRight":
        return sourcil(p, G, G["dx"], 1.0, 0.2)
    if cmd == "browDownLeft":
        return sourcil(p, G, G["gx"], -1.0, 0.2)
    if cmd == "browDownRight":
        return sourcil(p, G, G["dx"], -1.0, 0.2)
    if cmd == "browInnerUp":
        return sourcil(p, G, G["bx"], 1.0, 0.22)
    return None


def animer_procedural(obj, arm):
    sculpter(obj, arm)
    sk = obj.data.shape_keys
    for c, courbe in P["controles"].items():
        kb = sk.key_blocks.get("DZ_" + c)
        if kb is None:
            resume["absentes"].append(c)
            continue
        poser_cle(kb, courbe, 1.0)
        resume["animees"].append(c + " -> DZ_" + c)
    return True


# --- source et sorties (arriere-plan) ---------------------------------------------------------------------------
def importer_source():
    s = P["source"]
    if not s or s.lower().endswith(".blend"):
        return
    for o in list(scene.objects):
        if o.type in ("MESH", "CAMERA", "LIGHT") and o.name in ("Cube", "Camera", "Light"):
            bpy.data.objects.remove(o, do_unlink=True)
    if s.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=s)
    elif s.lower().endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=s)


def principal():
    importer_source()
    scene.render.fps = int(P["fps"])
    i0, i1 = P["images"]
    if scene.frame_end < i1:
        scene.frame_end = int(i1)
    obj = choisir_objet()
    arm = choisir_armature(obj)
    if obj is None and arm is None:
        resume["erreurs"].append("aucun maillage ni armature dans la scene")
        return
    resume["objet"] = obj.name if obj is not None else ""
    resume["armature"] = arm.name if arm is not None else ""
    mode = P["mode"]
    fait = False
    if mode in ("auto", "cles") and obj is not None:
        fait = animer_cles(obj)
        if fait:
            resume["mode"] = "cles"
    if not fait and mode in ("auto", "os") and arm is not None:
        fait = animer_os(arm)
        if fait:
            resume["mode"] = "os"
    if not fait and mode in ("auto", "procedural") and obj is not None:
        fait = animer_procedural(obj, arm)
        if fait:
            resume["mode"] = "procedural"
    if not fait:
        resume["erreurs"].append("aucune commande du visage animee (mode " + mode + ")")
    if P["sortie_glb"]:
        try:
            bpy.ops.export_scene.gltf(filepath=P["sortie_glb"], export_format="GLB", export_animations=True,
                                      export_morph=True, export_morph_animation=True)
        except TypeError:
            bpy.ops.export_scene.gltf(filepath=P["sortie_glb"], export_format="GLB")
    if P["sortie_blend"]:
        bpy.ops.wm.save_as_mainfile(filepath=P["sortie_blend"], copy=True)


try:
    principal()
except Exception as e:
    resume["erreurs"].append(repr(e)[:300])
dire()
'''
