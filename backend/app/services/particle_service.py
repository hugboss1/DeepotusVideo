# -*- coding: utf-8 -*-
"""Génération de sprites de particules — local, gratuit, hors ligne.

Ce module ferme la promesse laissée ouverte par l'écran Son & VFX (« la
génération de sprites de particules n'est pas encore câblée », estimée $0.06
l'élément). Il n'y a rien à facturer : un système de particules est un
compositeur, pas un modèle. On simule un émetteur, on composite une texture
CC0 du catalogue de démarrage frame par frame, et on repasse le résultat dans
l'assembleur de planches DÉJÀ écrit pour le Sprite Lab (sprite_service._assemble).

Conséquences de ce choix :
  - coût réel 0 $, aucune clé API, aucun réseau ;
  - la sortie est un job `sprite2d` ordinaire, donc l'onglet Sprites de la
    Bibliothèque, la visionneuse GIF, l'export ZIP et le pack Unity marchent
    sans une ligne de plus ;
  - un preset = (texture du catalogue + réglages d'émetteur), ce qui rend la
    sélection de l'écran VFX directement exécutable.

Contrainte technique : le runtime Python embarqué N'A PAS numpy (cf.
pixel_ops.py). Tout est en PIL pur. La boucle est rendue tenable par un cache
d'images pré-teintées indexé sur (taille quantifiée, âge quantifié) : deux
particules du même âge apparent et de la même taille partagent le même bitmap.
"""
from __future__ import annotations

import math
import random
import shutil
import subprocess
from pathlib import Path

from loguru import logger

_CANVAS = (128, 256, 512)


# ── presets ─────────────────────────────────────────────────────────────────
# Chaque preset : une texture du catalogue de démarrage + un émetteur. Les
# noms sont ceux que l'utilisateur voit dans la grille « VFX particules ».
# `blend: add` = rendu émissif (feu, magie, étincelles) ; `normal` = matière
# qui occulte (fumée, poussière).
PRESETS: list[dict] = [
    {"id": "explosion", "name": "Explosion", "texture": "fire_02",
     "type": "sprite · 24 f",
     "desc": "Boule de feu en expansion, retombée de braises",
     "emitter": {"count": 46, "frames": 24, "fps": 24, "size": 512,
                 "birth": "burst", "birth_spread": 0.18, "angle": 0,
                 "spread": 180, "speed": 240, "speed_var": 0.6,
                 "gravity": -60, "drag": 1.9, "life": 0.75, "life_var": 0.35,
                 "scale0": 0.30, "scale1": 0.62, "rot_speed": 40,
                 "color0": "FFD9A0", "color1": "8A2B10",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add"}},
    {"id": "smoke", "name": "Fumée douce", "texture": "smoke_04",
     "type": "alpha · boucle",
     "desc": "Colonne lente qui s'élargit et se dilue",
     "emitter": {"count": 34, "frames": 32, "fps": 16, "size": 512,
                 "birth": "stream", "angle": 0, "spread": 22,
                 "speed": 95, "speed_var": 0.35, "gravity": -14, "drag": 1.1,
                 "life": 1.9, "life_var": 0.3, "scale0": 0.22, "scale1": 0.70,
                 "rot_speed": 16, "color0": "C8CCD4", "color1": "5A6068",
                 "alpha0": 0.55, "alpha1": 0.0, "blend": "normal"}},
    {"id": "goldburst", "name": "Éclat doré", "texture": "star_04",
     "type": "sprite · 18 f",
     "desc": "Gerbe d'étoiles dorées, gravité légère",
     "emitter": {"count": 40, "frames": 18, "fps": 24, "size": 512,
                 "birth": "burst", "birth_spread": 0.1, "angle": 0,
                 "spread": 180, "speed": 300, "speed_var": 0.5,
                 "gravity": 340, "drag": 1.2, "life": 0.85, "life_var": 0.25,
                 "scale0": 0.16, "scale1": 0.05, "rot_speed": 180,
                 "color0": "FFF0BE", "color1": "D79A22",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add"}},
    {"id": "sparks", "name": "Étincelles", "texture": "star_05",
     "type": "sprite · 20 f",
     "desc": "Projections vives qui retombent et s'éteignent",
     "emitter": {"count": 60, "frames": 20, "fps": 24, "size": 512,
                 "birth": "burst", "birth_spread": 0.12, "angle": 0,
                 "spread": 140, "speed": 400, "speed_var": 0.7,
                 "gravity": 620, "drag": 1.4, "life": 0.7, "life_var": 0.4,
                 "scale0": 0.10, "scale1": 0.03, "rot_speed": 0,
                 "color0": "FFF4D2", "color1": "FF6A18",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add"}},
    {"id": "magic", "name": "Aura magique", "texture": "twirl_02",
     "type": "alpha · boucle",
     "desc": "Volutes ascendantes, teinte froide",
     "emitter": {"count": 18, "frames": 30, "fps": 20, "size": 512,
                 "birth": "stream", "angle": 0, "spread": 55,
                 "speed": 260, "speed_var": 0.5, "gravity": -90, "drag": 1.0,
                 "life": 1.5, "life_var": 0.25, "scale0": 0.16, "scale1": 0.46,
                 "rot_speed": 120, "color0": "BFE3FF", "color1": "5B3BE0",
                 "alpha0": 0.9, "alpha1": 0.0, "blend": "add",
                 "spawn_x": 0.25, "spawn_y": 0.1}},
    {"id": "muzzle", "name": "Départ de coup", "texture": "muzzle_02",
     "type": "sprite · 8 f",
     "desc": "Éclair de bouche très court, plein axe",
     "emitter": {"count": 8, "frames": 8, "fps": 30, "size": 256,
                 "birth": "burst", "birth_spread": 0.04, "angle": 0,
                 "spread": 26, "speed": 130, "speed_var": 0.4, "gravity": 0,
                 "drag": 2.6, "life": 0.22, "life_var": 0.2,
                 "scale0": 0.55, "scale1": 0.85, "rot_speed": 0,
                 "color0": "FFF6D8", "color1": "FF9A2E",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add",
                 "orient": "velocity"}},
    {"id": "dust", "name": "Poussière", "texture": "dirt_01",
     "type": "alpha · 24 f",
     "desc": "Nuage au sol, gravats qui retombent",
     "emitter": {"count": 38, "frames": 24, "fps": 20, "size": 512,
                 "birth": "burst", "birth_spread": 0.25, "angle": 0,
                 "spread": 165, "speed": 190, "speed_var": 0.55,
                 "gravity": 260, "drag": 1.8, "life": 1.1, "life_var": 0.3,
                 "scale0": 0.14, "scale1": 0.40, "rot_speed": 55,
                 "color0": "C4AE8E", "color1": "6B5A44",
                 "alpha0": 0.75, "alpha1": 0.0, "blend": "normal"}},
    {"id": "trail", "name": "Traînée", "texture": "trace_01",
     "type": "sprite · 24 f",
     "desc": "Sillage étiré, lecture de vitesse",
     "emitter": {"count": 26, "frames": 24, "fps": 24, "size": 512,
                 "birth": "stream", "angle": 90, "spread": 12,
                 "speed": 430, "speed_var": 0.25, "gravity": 0, "drag": 1.0,
                 "life": 0.65, "life_var": 0.2, "scale0": 0.34, "scale1": 0.14,
                 "rot_speed": 0, "color0": "DCF2FF", "color1": "2E7CC4",
                 "alpha0": 0.95, "alpha1": 0.0, "blend": "add",
                 "orient": "velocity", "spawn_y": 0.35}},
    {"id": "embers", "name": "Braises flottantes", "texture": "light_02",
     "type": "alpha · boucle",
     "desc": "Points chauds qui montent en dérivant — plan de fond",
     "emitter": {"count": 44, "frames": 36, "fps": 16, "size": 512,
                 "birth": "stream", "angle": 0, "spread": 60,
                 "speed": 70, "speed_var": 0.6, "gravity": -26, "drag": 1.0,
                 "life": 2.2, "life_var": 0.4, "scale0": 0.055, "scale1": 0.03,
                 "rot_speed": 0, "color0": "FFCF8A", "color1": "C24A12",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add",
                 "spawn_x": 1.0, "spawn_y": 0.8}},
    {"id": "shockwave", "name": "Onde de choc", "texture": "circle_03",
     "type": "sprite · 14 f",
     "desc": "Anneau unique qui s'ouvre et se dissipe",
     "emitter": {"count": 1, "frames": 14, "fps": 24, "size": 512,
                 "birth": "burst", "birth_spread": 0, "angle": 0, "spread": 0,
                 "speed": 0, "speed_var": 0, "gravity": 0, "drag": 1.0,
                 "life": 0.58, "life_var": 0, "scale0": 0.10, "scale1": 0.98,
                 "rot_speed": 0, "color0": "FFFFFF", "color1": "7FB6FF",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add",
                 "orient": "fixed"}},
    {"id": "lightning", "name": "Arcs électriques", "texture": "spark_05",
     "type": "sprite · 16 f",
     "desc": "Décharges nerveuses, apparition/disparition brutale",
     "emitter": {"count": 14, "frames": 16, "fps": 24, "size": 512,
                 "birth": "burst", "birth_spread": 0.7, "angle": 0,
                 "spread": 360, "speed": 60, "speed_var": 0.9, "gravity": 0,
                 "drag": 2.2, "life": 0.18, "life_var": 0.5,
                 "scale0": 0.75, "scale1": 0.85, "rot_speed": 220,
                 "color0": "EAF6FF", "color1": "4C7BFF",
                 "alpha0": 1.0, "alpha1": 0.0, "blend": "add"}},
    {"id": "ashes", "name": "Cendres & neige", "texture": "circle_05",
     "type": "alpha · boucle",
     "desc": "Chute lente et dérivante — surcouche d'ambiance plein cadre",
     "emitter": {"count": 70, "frames": 40, "fps": 16, "size": 512,
                 "birth": "stream", "angle": 175, "spread": 45,
                 "speed": 90, "speed_var": 0.7, "gravity": 30, "drag": 0.9,
                 "life": 2.5, "life_var": 0.2, "scale0": 0.05,
                 "scale1": 0.04, "rot_speed": 0, "color0": "FFFFFF",
                 "color1": "C9D6E6", "alpha0": 0.85, "alpha1": 0.1,
                 "blend": "normal", "spawn_x": 1.4, "spawn_y": 1.4}},
]

PRESET_BY_ID = {p["id"]: p for p in PRESETS}

_DEFAULT_EMITTER = {
    "count": 32, "frames": 24, "fps": 24, "size": 512, "birth": "burst",
    "birth_spread": 0.15, "angle": 0.0, "spread": 180.0, "speed": 220.0,
    "speed_var": 0.5, "gravity": 0.0, "drag": 1.5, "life": 1.0,
    "life_var": 0.3, "scale0": 0.2, "scale1": 0.5, "rot_speed": 0.0,
    "color0": "FFFFFF", "color1": "FFFFFF", "alpha0": 1.0, "alpha1": 0.0,
    "blend": "add", "orient": "random", "spawn_x": 0.0, "spawn_y": 0.0,
    # t274 (21/10/2026) — réglages du canevas Particules de Son & VFX, NEUTRES par défaut : un preset rend à
    # l'octet ce qu'il rendait avant. L'aperçu de l'écran (frontend/patches/sonvfx-particules.js) en est le port JS.
    "pos_x": 0.5, "pos_y": 0.5, "shape": "rect", "wind": 0.0, "turbulence": 0.0,
    "rate_keys": None,
}

_RANGES = {
    "count": (1, 200), "frames": (2, 64), "fps": (4, 60),
    "birth_spread": (0.0, 1.0), "angle": (-360.0, 360.0),
    "spread": (0.0, 360.0), "speed": (0.0, 2000.0), "speed_var": (0.0, 1.0),
    "gravity": (-2000.0, 2000.0), "drag": (0.5, 6.0), "life": (0.05, 6.0),
    "life_var": (0.0, 1.0), "scale0": (0.01, 2.0), "scale1": (0.01, 2.0),
    "rot_speed": (-720.0, 720.0), "alpha0": (0.0, 1.0), "alpha1": (0.0, 1.0),
    "spawn_x": (0.0, 2.0), "spawn_y": (0.0, 2.0),
    "pos_x": (0.0, 1.0), "pos_y": (0.0, 1.0), "wind": (-2000.0, 2000.0),
    "turbulence": (0.0, 400.0),
}

# t274 — zone de naissance : « rect » (le rectangle spawn_x × spawn_y d'origine) ou « disque » (l'ellipse inscrite,
# tirée avec LES MÊMES deux nombres : la suite du générateur ne bouge pas). Clés de cadence : au plus 8 couples
# [t, v] (t et v dans [0, 1], t croissant) ; une particule naît si sa part fixe (i × φ mod 1) est sous la cadence
# interpolée à sa naissance. Aucun tirage de plus : l'aperçu JS et le serveur restent synchrones.
_SHAPES = ("rect", "disque")
_CLES_MAX = 8
_PHI = 0.6180339887498949
_PHASE = 2.399963229728653

# Orientation de la texture. Le pack CC0 mélange des textures RONDES (disques,
# étoiles, fumée : l'orientation n'a aucun sens) et des textures DIRIGÉES
# (cône de bouche, traînée, flamme : elles pointent vers le haut par
# convention). Tourner une texture dirigée au hasard détruit sa lecture — un
# départ de coup devient une tache. D'où trois régimes explicites :
#   random   angle initial aléatoire — le défaut, correct pour tout ce qui est rond
#   fixed    texture laissée droite — halos, anneaux, cadres
#   velocity texture alignée sur la direction d'émission — cônes, traînées, lames
_ORIENTS = ("random", "fixed", "velocity")
_INTS = {"count", "frames", "fps", "size"}


class ParticleError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ── normalisation ───────────────────────────────────────────────────────────
def _hex_rgb(v: str) -> tuple[int, int, int]:
    s = str(v or "").lstrip("#").strip()
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"couleur invalide : {v!r} (RRGGBB attendu)")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        raise ValueError(f"couleur invalide : {v!r} (RRGGBB attendu)")


def _cles_cadence(v) -> list[list[float]] | None:
    """t274 — clés de cadence de la frise : None (cadence pleine) ou 1 à 8 couples [t, v] bornés à [0, 1], triés."""
    if v in (None, "", []):
        return None
    if not isinstance(v, (list, tuple)) or len(v) > _CLES_MAX:
        raise ValueError(f"rate_keys doit être une liste de 1 à {_CLES_MAX} couples [t, v]")
    out = []
    for c in v:
        try:
            t, val = float(c[0]), float(c[1])
        except (TypeError, ValueError, IndexError, KeyError):
            raise ValueError(f"rate_keys doit être une liste de 1 à {_CLES_MAX} couples [t, v]")
        if not (0.0 <= t <= 1.0 and 0.0 <= val <= 1.0):
            raise ValueError("rate_keys : t et v doivent être entre 0 et 1")
        out.append([t, val])
    return sorted(out, key=lambda c: c[0])


def _cadence(cles, u: float) -> float:
    """Cadence (0-1) à l'instant relatif u, interpolée entre les clés ; 1 sans clé."""
    if not cles:
        return 1.0
    if u <= cles[0][0]:
        return cles[0][1]
    for a, b in zip(cles, cles[1:]):
        if u <= b[0]:
            d = b[0] - a[0]
            return b[1] if d <= 0 else _lerp(a[1], b[1], (u - a[0]) / d)
    return cles[-1][1]


def normalize_opts(body: dict) -> dict:
    """Valide la requête. Lève ValueError (-> 400) sur tout ce qui sort des
    bornes, plutôt que d'accepter un job qui produira une planche vide."""
    body = body or {}
    preset_id = str(body.get("preset") or "").strip()
    if preset_id:
        preset = PRESET_BY_ID.get(preset_id)
        if preset is None:
            raise ValueError(f"preset inconnu : {preset_id!r} "
                             f"(voir GET /api/particles/presets)")
        base = dict(_DEFAULT_EMITTER, **preset["emitter"])
        texture = str(body.get("texture") or preset["texture"])
    else:
        base = dict(_DEFAULT_EMITTER)
        texture = str(body.get("texture") or "").strip()
        if not texture:
            raise ValueError("texture requise (ou preset)")

    over = body.get("emitter") or {}
    if not isinstance(over, dict):
        raise ValueError("emitter doit être un objet")
    em = dict(base)
    for k, v in over.items():
        if k not in _DEFAULT_EMITTER:
            logger.warning("particles: réglage inconnu ignoré — {}", k)
            continue
        em[k] = v

    for k in ("color0", "color1"):
        em[k] = _hex_rgb(em[k])
    if em["blend"] not in ("add", "normal"):
        raise ValueError("blend doit valoir 'add' ou 'normal'")
    if em["birth"] not in ("burst", "stream"):
        raise ValueError("birth doit valoir 'burst' ou 'stream'")
    if em["orient"] not in _ORIENTS:
        raise ValueError(f"orient doit valoir {' | '.join(_ORIENTS)}")
    if em["shape"] not in _SHAPES:
        raise ValueError(f"shape doit valoir {' | '.join(_SHAPES)}")
    em["rate_keys"] = _cles_cadence(em["rate_keys"])
    size = int(em["size"])
    if size not in _CANVAS:
        raise ValueError(f"size doit valoir {', '.join(map(str, _CANVAS))}")
    em["size"] = size
    for k, (lo, hi) in _RANGES.items():
        try:
            v = int(em[k]) if k in _INTS else float(em[k])
        except (TypeError, ValueError):
            raise ValueError(f"{k} doit être un nombre ({lo}-{hi})")
        if not lo <= v <= hi:
            raise ValueError(f"{k} doit être entre {lo} et {hi}")
        em[k] = v

    seed = body.get("seed")
    try:
        seed = int(seed) if seed not in (None, "") else None
    except (TypeError, ValueError):
        raise ValueError("seed doit être un entier")

    return {"preset": preset_id, "texture": texture, "emitter": em,
            "seed": seed if seed is not None else random.randrange(1 << 30),
            "title": str(body.get("title") or "").strip(),
            "webm": bool(body.get("webm", True))}


# ── simulation ──────────────────────────────────────────────────────────────
def _spawn(em: dict, rng: random.Random) -> list[dict]:
    """Population de particules : angle, vitesse, durée de vie, naissance.

    Les deux modes de naissance existent pour que la frame 0 ne soit JAMAIS
    vide — un sprite dont la première image est transparente s'affiche comme
    une vignette noire dans toutes les grilles de l'app.

    « burst » : la moitié naît exactement à l'allumage (une explosion commence
    à pleine intensité, elle ne monte pas en régime), l'autre moitié est
    étalée en racine carrée sur `birth_spread` pour éviter l'effet mécanique
    du tir groupé.

    « stream » : les naissances couvrent tout le plan ET le temps est CYCLIQUE
    (voir render_frames). Résultat : la frame 0 voit déjà l'émetteur en régime
    établi, et la dernière frame raccorde exactement sur la première — c'est
    ce qui rend le « alpha · boucle » des presets vrai plutôt que décoratif.
    """
    total = em["frames"] / em["fps"]
    stream = em["birth"] == "stream"
    out = []
    for i in range(em["count"]):
        if stream:
            tb = (i / max(1, em["count"])) * total + rng.uniform(0, .02)
        elif rng.random() < .5:
            tb = 0.0
        else:
            tb = math.sqrt(rng.random()) * em["birth_spread"] * total
        deg = em["angle"] + rng.uniform(-.5, .5) * em["spread"]
        a = math.radians(deg)
        sp = em["speed"] * (1 + rng.uniform(-1, 1) * em["speed_var"])
        life = max(.05, em["life"] * (1 + rng.uniform(-1, 1) * em["life_var"]))
        if stream:
            # une particule qui survit plus d'un cycle se croiserait elle-même
            # à la boucle : on la borne au cycle plutôt que de casser le raccord
            life = min(life, total)
        if em["orient"] == "random":
            rot0 = rng.uniform(0, 360)
        elif em["orient"] == "velocity":
            # PIL tourne dans le sens trigonométrique ; l'angle d'émission est
            # horaire depuis le haut, d'où le signe
            rot0 = -deg
        else:
            rot0 = 0.0
        # ordre des tirages inchangé : signe de rotation, gigue, zone de naissance
        rs = em["rot_speed"] * rng.choice((-1, 1))
        jx, jy = rng.uniform(-.02, .02), rng.uniform(-.02, .02)
        ox, oy = rng.uniform(-.5, .5), rng.uniform(-.5, .5)
        if em["shape"] == "disque":
            # t274 : les deux mêmes nombres, passés en polaire (rayon en racine : densité uniforme sur le disque)
            ray, th = .5 * math.sqrt(ox + .5), (oy + .5) * 2 * math.pi
            ox, oy = ray * math.cos(th), ray * math.sin(th)
        out.append({
            "tb": tb, "life": life,
            # angle 0 = vers le haut de l'image (y décroissant)
            "vx": math.sin(a) * sp, "vy": -math.cos(a) * sp,
            "rot0": rot0,
            "rot_speed": rs,
            "jx": jx, "jy": jy,
            # naissance étalée sur une zone : un effet d'ambiance (neige,
            # braises) doit couvrir le cadre, pas jaillir d'un point unique
            "ox": ox * em["spawn_x"],
            "oy": oy * em["spawn_y"],
        })
    return out


def _lerp(a, b, u):
    return a + (b - a) * u


def _sprite_cache_key(size_px: int, u: float) -> tuple[int, int]:
    """Deux particules de même taille (au pas de 4 px) et de même âge (au
    1/24e) partagent le même bitmap teinté — sans ce cache, chaque particule
    de chaque frame paierait un resize + une multiplication."""
    return (max(2, (size_px // 4) * 4), min(23, int(u * 24)))


def etat_frame(em: dict, parts: list[dict], f: int) -> list[dict]:
    """t274 — l'état DESSINÉ de la frame f, sans un pixel : une entrée par particule visible, dans l'ordre de dessin.
    Champs : i (rang), x, y (centre), px (côté du bitmap), cle (taille quantifiée, âge quantifié au 1/24e), rot
    (degrés), col (RVB de la teinte), a (opacité). C'est ce que le port JS de l'écran recalcule (banc t274)."""
    size = em["size"]
    cx, cy = em["pos_x"] * size, em["pos_y"] * size
    total = em["frames"] / em["fps"]
    cyclic = em["birth"] == "stream"
    cles = em.get("rate_keys")
    turb, vent = em["turbulence"], em["wind"]
    t = f / em["fps"]
    out = []
    for i, p in enumerate(parts):
        if cles and (i * _PHI) % 1.0 >= _cadence(cles, p["tb"] / total):
            continue
        # temps cyclique en mode « stream » : la frame 0 hérite du régime
        # établi et la boucle raccorde à l'image près
        age = (t - p["tb"]) % total if cyclic else t - p["tb"]
        if age < 0 or age > p["life"]:
            continue
        u = age / p["life"]
        # amortissement exponentiel : la particule perd sa vitesse au lieu
        # de filer en ligne droite, ce qui donne la retombée attendue
        k = (1 - math.exp(-em["drag"] * age)) / em["drag"]
        x = cx + p["ox"] * size + p["vx"] * k + p["jx"] * size * age
        y = cy + p["oy"] * size + p["vy"] * k \
            + .5 * em["gravity"] * age * age + p["jy"] * size * age
        if vent:
            x += .5 * vent * age * age
        if turb:
            # t274 : turbulence déterministe (aucun tirage) — deux sinusoïdes déphasées par le rang
            ph = i * _PHASE
            x += turb * (math.sin(age * 2.3 + ph) - math.sin(ph))
            y += turb * (math.cos(age * 1.9 + ph * 1.3) - math.cos(ph * 1.3))
        px = max(2, int(round(_lerp(em["scale0"], em["scale1"], u) * size)))
        cle = _sprite_cache_key(px, u)
        uq = cle[1] / 24.0
        col = tuple(int(round(_lerp(em["color0"][c], em["color1"][c], uq)))
                    for c in range(3))
        out.append({"i": i, "x": x, "y": y, "px": px, "cle": cle,
                    "rot": p["rot0"] + p["rot_speed"] * age, "col": col,
                    "a": _lerp(em["alpha0"], em["alpha1"], uq)})
    return out


def _sprites(tex, em: dict):
    """Bitmaps teintés partagés, indexés sur la clé de cache (voir _sprite_cache_key)."""
    from PIL import Image, ImageChops

    cache: dict[tuple[int, int], "Image.Image"] = {}

    def sprite(cle, col, a):
        hit = cache.get(cle)
        if hit is not None:
            return hit
        px = cle[0]
        im = tex.resize((px, px), Image.LANCZOS)
        rgb = ImageChops.multiply(im.convert("RGB"),
                                  Image.new("RGB", im.size, col))
        lut = bytes(min(255, int(v * a)) for v in range(256))
        im2 = Image.merge("RGBA", (*rgb.split(), im.getchannel("A").point(lut)))
        cache[cle] = im2
        return im2
    return sprite


def composer_frame(em: dict, parts: list[dict], f: int, sprite):
    """Une frame RGBA : les particules de etat_frame, dans l'ordre, sur un plan transparent."""
    from PIL import Image, ImageChops

    size = em["size"]
    add = em["blend"] == "add"
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for d in etat_frame(em, parts, f):
        spr = sprite(d["cle"], d["col"], d["a"])
        rot = d["rot"]
        if rot % 360:
            spr = spr.rotate(rot, resample=Image.BILINEAR, expand=False)
        w = spr.size[0]
        ox, oy = int(round(d["x"] - w / 2)), int(round(d["y"] - w / 2))
        if ox >= size or oy >= size or ox + w <= 0 or oy + w <= 0:
            continue
        box = (max(0, ox), max(0, oy), min(size, ox + w), min(size, oy + w))
        crop = spr.crop((box[0] - ox, box[1] - oy,
                         box[2] - ox, box[3] - oy))
        region = canvas.crop(box)
        # « add » additionne aussi l'alpha : c'est le rendu émissif attendu
        # (les recouvrements montent en intensité) et il reste correct une
        # fois composité sur un plan sombre, qui est l'usage d'un VFX.
        merged = ImageChops.add(region, crop) if add \
            else Image.alpha_composite(region, crop)
        canvas.paste(merged, box)
    return canvas


def _texture(texture: Path):
    from PIL import Image

    with Image.open(texture) as raw:
        return raw.convert("RGBA")


def render_frames(texture: Path, opts: dict, out_dir: Path) -> list[Path]:
    """Simule l'émetteur et écrit une PNG RGBA par frame. Synchrone : appelé
    dans un thread de travail par l'orchestrateur."""
    em = opts["emitter"]
    parts = _spawn(em, random.Random(opts["seed"]))
    sprite = _sprites(_texture(texture), em)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for f in range(em["frames"]):
        dest = out_dir / f"p{f:04d}.png"
        composer_frame(em, parts, f, sprite).save(dest, format="PNG")
        files.append(dest)
    return files


def rendre_image(texture: Path, opts: dict, f: int):
    """t274 — la frame f seule (export PNG de l'écran Particules) : même graine, même image que render_frames."""
    em = opts["emitter"]
    if not 0 <= int(f) < em["frames"]:
        raise ValueError(f"frame doit être entre 0 et {em['frames'] - 1}")
    parts = _spawn(em, random.Random(opts["seed"]))
    return composer_frame(em, parts, int(f), _sprites(_texture(texture), em))


# ── export WebM alpha (overlay direct dans le Montage) ──────────────────────
def _export_webm(frames_dir: Path, fps: int, dest: Path) -> bool:
    """VP9 + yuva420p depuis les frames. Best-effort : un ffmpeg sans VP9 ne
    doit pas faire échouer le job, la planche PNG reste la sortie de référence."""
    cmd = ["ffmpeg", "-y", "-framerate", str(fps),
           "-i", str(frames_dir / "%03d.png"),
           "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
           "-crf", "28", "-an", str(dest)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as e:
        logger.warning("particles: WebM alpha non produit ({})", e)
        return False
    if r.returncode != 0 or not dest.is_file():
        logger.warning("particles: WebM alpha non produit — ffmpeg rc={} {}",
                       r.returncode, (r.stderr or "")[-300:])
        return False
    return True


# ── orchestrateur ───────────────────────────────────────────────────────────
async def generate_particles(payload: dict, job_id: str, on_step=None) -> dict:
    """Émetteur -> frames -> planche + GIF + manifeste + pack Unity, sous
    outputs/sprites/{job_id}/ (le MÊME dossier que le Sprite Lab : la sortie
    est un job sprite2d ordinaire pour tout l'aval)."""
    import asyncio

    from app.config import settings
    from app.services import sprite_service as SS
    from app.services import starter_catalog as SC

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    opts = normalize_opts(payload)
    em = opts["emitter"]
    texture = SC.asset_path("particle", opts["texture"])

    out_dir = settings.outputs_path / "sprites" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw"

    await _step("Simulation des particules", 15)
    frames = await asyncio.to_thread(render_frames, texture, opts, raw_dir)
    if not frames:
        raise RuntimeError("aucune frame produite par l'émetteur")

    await _step("Assemblage de la planche", 60)
    tex_item = SC.get("particle", opts["texture"])
    source_info = {
        "kind": "particles", "preset": opts["preset"] or None,
        "texture": opts["texture"], "texture_name": tex_item.get("name"),
        "license": "CC0-1.0", "attribution": "Kenney (kenney.nl)",
        "seed": opts["seed"], "blend": em["blend"], "count": em["count"],
        "fps_sample": em["fps"],
    }
    # t274 : cellule NATIVE (0) — les frames font déjà em["size"] de côté, `_place_into_cell` les pose à l'octet.
    # `_fit_into_cell` les collait avec elles-mêmes pour masque (alpha appliqué deux fois) : l'export WebM / planche
    # n'était pas l'image simulée, ni l'aperçu du canevas Particules qui en est le port
    sheet_opts = {"cell_size": 0, "align": "center",
                  "trim": "animation", "columns": "auto", "fps": em["fps"],
                  "pixel": None}
    summary = await asyncio.to_thread(
        SS._assemble, [(p, False) for p in frames], sheet_opts, out_dir,
        source_info)

    if opts["webm"]:
        await _step("Export WebM alpha", 85)
        ok = await asyncio.to_thread(
            _export_webm, out_dir / "frames", em["fps"], out_dir / "alpha.webm")
        summary["webm"] = bool(ok)

    await _step("Nettoyage", 95)
    shutil.rmtree(raw_dir, ignore_errors=True)
    await _step("Complete", 100)
    summary.update({"bg_failed": [], "remove_bg": "none",
                    "out_dir": str(out_dir), "seed": opts["seed"],
                    "preset": opts["preset"] or None,
                    "texture": opts["texture"]})
    return summary


# ── import d'une séquence animée du catalogue (sans simulation) ─────────────
async def import_anim(anim_id: str, job_id: str, cell: int = 512,
                      on_step=None) -> dict:
    """Séquence CC0 toute faite -> planche sprite2d, sans passer par
    l'émetteur. C'est le chemin « je veux juste l'explosion prête à l'emploi »."""
    import asyncio

    from app.config import settings
    from app.services import sprite_service as SS
    from app.services import starter_catalog as SC

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    if cell not in _CANVAS:
        raise ValueError(f"cell doit valoir {', '.join(map(str, _CANVAS))}")
    item = SC.get("anim", anim_id)
    frames = SC.anim_frames(anim_id)

    out_dir = settings.outputs_path / "sprites" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    await _step("Assemblage de la planche", 40)
    source_info = {"kind": "starter-anim", "anim": anim_id,
                   "anim_name": item.get("name"), "license": "CC0-1.0",
                   "attribution": "Kenney (kenney.nl)",
                   "fps_sample": 24}
    sheet_opts = {"cell_size": cell, "align": "center", "trim": "animation",
                  "columns": "auto", "fps": 24, "pixel": None}
    summary = await asyncio.to_thread(
        SS._assemble, [(p, False) for p in frames], sheet_opts, out_dir,
        source_info)

    await _step("Export WebM alpha", 85)
    summary["webm"] = await asyncio.to_thread(
        _export_webm, out_dir / "frames", 24, out_dir / "alpha.webm")
    await _step("Complete", 100)
    summary.update({"bg_failed": [], "remove_bg": "none",
                    "out_dir": str(out_dir), "anim": anim_id})
    return summary
