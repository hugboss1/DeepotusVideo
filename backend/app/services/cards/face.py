# -*- coding: utf-8 -*-
"""Card Forge — P1 « Génération de face » (import + IA). Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/face`.

────────────────────────────────────────────────────────────────────────────
CE QUE CE MODULE FAIT — ET LA SEULE CHOSE QU'IL SERT EN HTTP
────────────────────────────────────────────────────────────────────────────
La pièce 01 dessine dans le navigateur : le catalogue de départ est
**vectoriel et procédural** (une TABLE de scènes que `js/mod-face.js` peint à
`geom.canvas_px`), les imports vivent dans l'IndexedDB, la génération IA passe
par `CF.images.generate`. Rien de tout cela n'a besoin d'un aller-retour.

Il reste EXACTEMENT une chose que le navigateur ne sait pas faire, et c'est
celle qui décide de la moitié mesurable du cahier des charges :

    **`canvas.toBlob("image/png")` n'écrit AUCUN chunk `pHYs`.**

Mesuré sur le fichier livré par le duel (815x1110, 1 145 125 octets) : les
chunks sont `IHDR` + 280 `IDAT` + `IEND`, rien d'autre. Un PNG sans `pHYs` ne
déclare aucune résolution physique : ouvert dans Photoshop ou InDesign il
arrive à 72 DPI, soit 11,32 x 15,42 pouces au lieu de 69 x 94 mm. Toute la
revendication « 300 DPI » s'évapore à la seconde où le fichier quitte
l'application.

D'où l'unique route de ce module, `POST /png/{fmt}/{dpi}` : elle prend les
octets PNG **produits par le moteur unique** (`CF.cardBlob`, spec §5 —
personne ne redessine côté serveur, risque 2), VÉRIFIE que la trame fait
exactement `canvas_px` du format demandé, et n'estampille `pHYs` qu'à cette
condition. Le chiffre écrit dans le fichier n'est donc jamais une promesse :
c'est un contrôle. Une trame qui ne tombe pas sur la toile est refusée en 409
avec les deux nombres.

(La route est aussi le seul chemin par lequel un fichier peut atteindre
`CF.download` avec une provenance : le CORE n'accepte qu'un blob sorti de
`CF.cardBlob` ou rapporté par `M.api.blob` — spec §9.)

`backend/tests/test_cards_face.py` EXTRAIT les tables du fichier JS servi pour
les confronter à celles d'ici : une dérive entre l'écran et cette table fait
rougir le test, elle ne se découvre pas chez l'imprimeur.

Ce qui est gravé ici :

* `DPI_TARGET = 300` — le seuil vert de la jauge de DPI effectif.
* `effective_dpi(...)` — le DPI réel d'une illustration à la taille POSÉE.
  C'est le chiffre que la barre (Clash of Decks) n'affiche nulle part : elle
  refuse brutalement en dessous de 650x1024 par un `alert()` natif et ne dit
  jamais où l'on en est.
* `min_source_px(...)` — la taille de source qu'il FAUDRAIT, en pixels.
  Un refus qui dit « il en faut 1630 x 2220 » vaut mieux qu'un refus muet.
* `fit_rect(...)` — la géométrie de `cover` / `contain` / `free`, la même des
  deux côtés.
* `png_with_phys(...)` / `png_phys(...)` — l'écriture et la RELECTURE du chunk
  de résolution physique, sur les octets.
* `CATALOG` — **108 dessins distincts** : 18 sujets × 6 COMPOSITIONS. La
  composition n'est pas une couleur : `vista` a un horizon, des crêtes et une
  lune ; `medallion` n'a pas d'horizon du tout ; `heraldry` est un aplat
  symétrique ; `depths` est une colonne d'eau ; `backlight` est un disque
  unique et un sol plat ; `stained` est une baie de vitrail au réseau de
  plomb. Chaque dessin est recolorable en 12 palettes, soit 1296 combinaisons — et c'est ainsi que
  l'écran le dit, pièce par pièce, parce que « 72 faces » quand il n'y avait
  que 12 dessins était un chiffre faux.
* `PROMPT_SEEDS` — les amorces d'invite adaptées à une FACE DE CARTE
  (cadrage, marge de fond perdu, sujet centré), pas des invites génériques.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import struct
import time
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path as _Path

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from .contract import FORMATS, geom, is_valid_did

# Règle 8 : signature imposée, chemins RELATIFS.
router = APIRouter()

__all__ = [
    "DPI_TARGET", "FIT_MODES", "MAX_IMPORT_PX", "PALETTES", "SUBJECTS",
    "COMPOS", "CATALOG", "PROMPT_SEEDS", "PAL_STRIDE", "COMPO_STRIDE",
    "catalog", "catalog_ids", "effective_dpi", "dpi_verdict", "min_source_px",
    "fit_rect", "fnv1a32", "prompt_seeds", "scene_of", "legacy_art_id",
    "PNG_SIG", "MAX_PNG_BYTES", "dpi_to_ppm", "ppm_to_dpi", "png_chunks",
    "png_size", "png_phys", "png_with_phys", "gauge_fill", "visible_fraction",
    "price_table", "SUB_RENAMES",
    # ── la série « affiche polonaise » (phase 5, T1) ────────────────────────
    "SERIES", "SERIE_ID", "SERIE_V", "SERIE_JUGE", "SERIE_PLAFOND_USD",
    "SERIE_CANDIDATS", "SERIE_FLUX_MAX", "FAMILLES", "NOMS_INTERDITS",
    "PALETTE_NEUTRE",
    "fiche_style", "serie_cases", "serie_famille", "serie_familles",
    "serie_accent", "serie_prompt", "serie_prompt_retouche",
    "sans_nom_d_artiste", "juger_image", "meilleur_candidat", "serie_root",
    "manifeste_lire", "manifeste_ecrire", "prix_usd", "serie_prix",
    "campagne", "cout_echelle_usd", "devis", "manifeste_fusionner",
]

# ── seuils ──────────────────────────────────────────────────────────────────
DPI_TARGET = 300          # jauge verte à partir d'ici, rouge en dessous
FIT_MODES = ("cover", "contain", "free")
MAX_IMPORT_PX = 4096      # côté long au-delà duquel un import est ré-échelonné
SCALE_MIN, SCALE_MAX = 0.05, 12.0
ROT_MIN, ROT_MAX = -180.0, 180.0

# La barre refuse tout import sous cette taille, par `alert()` natif, sans
# jamais dire ce qu'il manque. On garde le chiffre pour le TEST de parité :
# à cette taille exacte, sur un poker_eu à 300 DPI en `cover`, la nôtre
# ACCEPTE et affiche le DPI réel.
BAR_REFUSAL_PX = (650, 1024)


# ── le hachage de graine, MIROIR EXACT de mod-face.js ───────────────────────
def fnv1a32(s: str) -> int:
    """FNV-1a 32 bits. Le JS le refait avec `Math.imul` : mêmes graines des
    deux côtés, donc la même montagne, le même nuage, le même caillou. Une
    scène qui ne serait pas déterministe rendrait l'aperçu et le fichier
    livré différents — le bug WYSIWYG que la spec interdit."""
    h = 2166136261
    for ch in s:
        h ^= ord(ch) & 0xFF
        h = (h * 16777619) & 0xFFFFFFFF
    return h


# ── le catalogue de départ : 18 sujets x 6 compositions = 108 dessins ───────
# CF-FACE-PALETTES-BEGIN
PALETTES = [
    ("ember", "Braise"),
    ("frost", "Givre"),
    ("verdant", "Sylve"),
    ("dusk", "Crépuscule"),
    ("abyss", "Abysse"),
    ("gold", "Or"),
    ("ash", "Cendre"),
    ("storm", "Orage"),
    ("bloom", "Floraison"),
    ("void", "Néant"),
    ("sand", "Sable"),
    ("jade", "Jade"),
]
# CF-FACE-PALETTES-END

# CF-FACE-SUBJECTS-BEGIN
SUBJECTS = [
    ("tower", "Tour de guet"),
    ("pines", "Forêt de pins"),
    ("monolith", "Portail de pierre"),
    ("dragon", "Dragon"),
    ("sphinx", "Sphinx de garde"),
    ("portal", "Portail arcanique"),
    ("crystals", "Cristaux"),
    ("ship", "Navire"),
    ("wolf", "Loup"),
    ("knight", "Chevalier"),
    ("citadel", "Citadelle"),
    ("whale", "Baleine céleste"),
    ("phoenix", "Phénix"),
    ("serpent", "Serpent des mers"),
    ("golem", "Golem de pierre"),
    ("archer", "Archère"),
    ("grimoire", "Grimoire"),
    ("beacon", "Brasier"),
]
# CF-FACE-SUBJECTS-END

# CF-FACE-COMPOS-BEGIN
# La COMPOSITION est ce qui manquait : douze silhouettes recolorées douze fois
# restaient « la même image », et les deux critiques l'ont compté à la main.
# Une composition change l'horizon, la lumière, la présence même d'un paysage.
COMPOS = [
    ("vista", "Panorama"),        # horizon, crêtes, lune, brume — le paysage
    ("medallion", "Médaillon"),   # aucun horizon : disque, anneau, sujet gros
    ("heraldry", "Blason"),       # aplat symétrique, écu, sujet + son reflet
    ("depths", "Profondeurs"),    # colonne d'eau, rais verticaux, sujet flottant
    ("backlight", "Contre-jour"), # un seul disque, sol plat, bandes de brume
    ("stained", "Vitrail"),       # baie en arc brisé, réseau de plomb, rosace
]
# CF-FACE-COMPOS-END

PAL_STRIDE = 5            # premier avec 12
COMPO_STRIDE = 2          # (5*s + 2*c) % 12 : chaque palette sort 9 fois PILE
# Le pas valait 3 tant qu'il y avait 4 compositions (6 sorties par palette,
# pile). À 6 compositions, 3c ne prend que quatre valeurs distinctes
# (0,3,6,9,0,3) : le compte tombait entre 8 et 10 selon la palette. Le pas 2
# donne six décalages distincts (0,2,4,6,8,10) et rend l'équilibre EXACT —
# 9 pour chacune des 12. Un équilibre annoncé doit se vérifier.


def scene_of(s_index: int, c_index: int) -> tuple[str, str, str]:
    """(palette_id, compo_id, subject_id) du dessin (sujet, composition).

    La règle est arithmétique, pas une liste écrite à la main. Elle garantit
    trois choses vérifiées par le test : chaque sujet sort 6 fois (une par
    composition), chaque composition 18 fois, et chaque palette EXACTEMENT
    9 fois — y compris à l'intérieur d'une même composition, où les 12
    palettes apparaissent toutes. Le JS applique la même formule."""
    sub = SUBJECTS[s_index % len(SUBJECTS)][0]
    compo = COMPOS[c_index % len(COMPOS)][0]
    pal = PALETTES[(s_index * PAL_STRIDE + c_index * COMPO_STRIDE)
                   % len(PALETTES)][0]
    return pal, compo, sub


def catalog() -> list[dict]:
    """Les 108 DESSINS de départ — 18 sujets × 6 compositions.

    Aucun n'est un fichier : `vector` est vrai partout, et c'est le point —
    un PNG de galerie plafonne (la barre sert du 723x1024), une scène
    vectorielle se redessine à `geom.canvas_px` quel que soit le DPI.

    `palette` est la teinte DE DÉPART du dessin : l'écran laisse la changer
    parmi les 12, ce qui fait 72 × 12 = 864 combinaisons. On compte les
    dessins et les combinaisons séparément, sans jamais additionner les deux
    sous une seule étiquette."""
    # (le compte exact est vérifié par test : 108 dessins, 1296 combinaisons)
    pal_lbl = dict(PALETTES)
    sub_lbl = dict(SUBJECTS)
    com_lbl = dict(COMPOS)
    out: list[dict] = []
    for si in range(len(SUBJECTS)):
        for ci in range(len(COMPOS)):
            pal, compo, sub = scene_of(si, ci)
            fid = f"face_{pal}_{compo}_{sub}"
            out.append({
                "id": fid,
                "label": f"{sub_lbl[sub]} — {com_lbl[compo]}",
                "palette": pal,
                "palette_label": pal_lbl[pal],
                "compo": compo,
                "subject": sub,
                "seed": fnv1a32(fid),
                "vector": True,
                "tags": [pal, compo, sub],
            })
    return out


CATALOG = catalog()
DRAWINGS = len(SUBJECTS) * len(COMPOS)          # 108 dessins distincts
COMBINATIONS = DRAWINGS * len(PALETTES)         # 1296 combinaisons


def catalog_ids() -> list[str]:
    return [c["id"] for c in CATALOG]


# Un sujet retiré du catalogue emporterait avec lui toutes les cartes qui le
# portaient : on garde la table de rappel — `octopus` devient `sphinx`.
# Le catalogue de départ d'un logiciel n'a pas à embarquer la mascotte de son
# éditeur : la silhouette se reconnaissait à l'œil sur les vignettes, et elle
# partait avec chaque capture d'écran du produit.
SUB_RENAMES = {"octopus": "sphinx"}


def legacy_art_id(art_id: str) -> str:
    """`face_<pal>_<sujet>` (ancien catalogue à deux mots) -> `face_<pal>_vista_<sujet>`,
    et tout sujet renommé ramené sur son nouveau nom.

    Un jeu enregistré avant l'ajout des compositions porte l'ancien
    identifiant. Sans cette table de rappel il rouvrirait sur un cadre vide —
    la pire façon de livrer une amélioration."""
    s = str(art_id or "")
    if not s.startswith("face_"):
        return s
    bits = s.split("_")
    if len(bits) == 4 and bits[3] in SUB_RENAMES:
        return f"{bits[0]}_{bits[1]}_{bits[2]}_{SUB_RENAMES[bits[3]]}"
    if len(bits) != 3:
        return s
    pal, sub = bits[1], SUB_RENAMES.get(bits[2], bits[2])
    if pal in dict(PALETTES) and sub in dict(SUBJECTS):
        return f"face_{pal}_vista_{sub}"
    return s


# ── la jauge : le chiffre que la barre n'affiche pas ────────────────────────
def effective_dpi(src_px: float, drawn_px: float, dpi: int) -> float:
    """DPI RÉEL de l'illustration à la taille où elle est posée.

    `src_px`  : côté de l'image source, en pixels d'origine.
    `drawn_px`: le même côté, une fois posé sur la toile (pixels de toile).
    `dpi`     : la définition de la toile.

    Poser une image de 1000 px sur 2000 px de toile à 300 DPI, c'est
    l'imprimer à 150 DPI : le rapport est linéaire, il n'y a rien de plus.
    Rend `inf` pour une source vectorielle (drawn_px = 0 n'arrive pas ; une
    source nulle non plus)."""
    try:
        s = float(src_px)
        d = float(drawn_px)
        n = int(dpi)
    except (TypeError, ValueError):
        raise ValueError("effective_dpi attend des nombres")
    if not (math.isfinite(s) and math.isfinite(d)) or s <= 0 or d <= 0 or n <= 0:
        return 0.0
    return n * s / d


def vector_effective_dpi(dpi: int) -> float:
    """DPI RÉEL d'une face VECTORIELLE — et ce n'est pas l'infini.

    CE QUI A CHANGÉ, ET LA MESURE QUI L'A IMPOSÉ. L'écran affichait, sur une
    face du catalogue, « ∞ vectoriel — Aucune perte possible, la jauge ne
    s'applique pas ». J'ai cliqué 150 dans la barre de format et relevé la
    même phrase, mot pour mot, alors que `CF.renderCard` rendait une toile de
    407 x 555 px pour 69,0 x 94,0 mm — soit 150 DPI, la moitié de la
    définition d'impression. Le badge lisait le GENRE de la source au lieu de
    mesurer la trame livrée : exactement le défaut du « 16 bits » annoncé par
    un IHDR que ses propres échantillons démentent.

    Un dessin vectoriel est rasterisé À LA TAILLE DE LA POSE, directement dans
    la toile de destination : sa trame EST celle de la toile. Sa source et son
    dessin ont donc le même nombre de pixels — le rapport de `effective_dpi`
    vaut 1 — et son DPI effectif vaut la définition de la toile. Ni plus (rien
    ne le rend plus fin que la trame), ni l'infini (rien ne l'en dispense).

    Conséquence tenue à l'écran : à 150 DPI la jauge passe au ROUGE sur une
    face vectorielle, l'alerte non bloquante s'affiche, et l'export demande
    une confirmation chiffrée — comme pour un bitmap sous-défini. La cause
    diffère (c'est la toile, pas la source), la correction aussi, et l'écran
    le dit."""
    return effective_dpi(1.0, 1.0, dpi)


def dpi_verdict(eff: float, target: int = DPI_TARGET) -> str:
    """« ok » (vert) à partir de la cible, « low » (rouge) en dessous.
    Binaire et sans zone grise : la spec dit vert >= 300, rouge en dessous."""
    if eff == math.inf:
        return "ok"
    try:
        v = float(eff)
    except (TypeError, ValueError):
        return "low"
    if not math.isfinite(v):
        return "ok" if v > 0 else "low"
    return "ok" if v + 1e-9 >= float(target) else "low"


# ── l'arrondi qui se vérifie : la pose publiée, et l'aire qui en découle ────
def pose_px(v: float) -> float:
    """La dimension de pose TELLE QU'ELLE EST PUBLIÉE : au dixième de pixel.

    AUTO-CRITIQUE DE CE TOUR, RELEVÉE PAR LE VRAI CHEMIN. Mire de contrôle
    posée par son propre bouton, panneau lu à l'écran :

        « source 320 x 480 px · posée 815 x 1223 px »   (en haut)
        « 267 397 px sur 996 338 px de pose »           (dix lignes plus bas)

    Un lecteur qui multiplie les deux nombres AFFICHÉS trouve 815 x 1223 =
    996 745 : 407 px d'écart avec le dénominateur publié. La hauteur de pose
    vaut en réalité 1222,5 px ; l'écran en publiait l'entier pendant que
    l'aire était calculée sur la valeur exacte. Le pourcentage « 26,8 % »
    était donc JUSTE et pourtant impossible à recalculer depuis l'écran — la
    même faute que le badge « 16 bits » démenti par ses échantillons, en plus
    discret.

    La règle : on publie au dixième, et tout ce qui en découle se calcule sur
    la valeur publiée."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("pose_px attend un nombre")
    if not math.isfinite(x):
        return 0.0
    # arrondi commercial, comme Math.round(v * 10) / 10 côté écran
    return math.floor(abs(x) * 10.0 + 0.5) / 10.0 * (1.0 if x >= 0 else -1.0)


def pose_area(w: float, h: float) -> float:
    """L'aire de pose = LE PRODUIT DES VALEURS PUBLIÉES, arrondi au dixième.

    Jamais `w * h` sur les valeurs internes : ce serait un dénominateur que le
    lecteur ne peut pas retrouver en multipliant ce qu'il voit."""
    return pose_px(pose_px(w) * pose_px(h))


def min_source_px(drawn_px: float, dpi: int, target: int = DPI_TARGET) -> int:
    """Pixels de source qu'il FAUDRAIT pour tenir `target` DPI à cette taille.

    C'est la moitié utile d'un refus. Clash of Decks dit « trop petit » et
    s'arrête ; on dit « il en faut 1630 » et l'utilisateur sait quoi faire."""
    d = float(drawn_px)
    if not math.isfinite(d) or d <= 0 or dpi <= 0:
        return 0
    return int(math.ceil(d * float(target) / float(dpi) - 1e-9))


# ── la barre de la jauge : une échelle qui NE SATURE PAS ────────────────────
def gauge_fill(eff: float, target: int = DPI_TARGET) -> float:
    """Remplissage de la barre, en %, sur une échelle 0 → 2 × `target`.

    REPROCHE, MOT POUR MOT : « la jauge sature : le remplissage s'arrête pile
    sur le repère (mesure au pixel : remplissage 2210..3001, repère à 3003).
    324 DPI et 900 DPI donneront la même barre pleine. Le seuil de 300 n'est
    donc lisible que dans le chiffre, jamais dans la position. » Exact.

    Une barre dont le maximum EST le seuil ne peut rien dire au-dessus du
    seuil : elle transforme « atteint » et « largement dépassé » en la même
    image. L'échelle va donc jusqu'au DOUBLE de la cible et le repère tombe à
    la moitié : 324 DPI remplit 54 %, 600 en remplit 100, et la position
    redevient une information. Le plancher de 2 % existe pour qu'une pose
    catastrophique reste visible comme un trait, pas comme rien."""
    t = float(target or DPI_TARGET)
    e = float(eff)
    if not math.isfinite(e) or e <= 0 or t <= 0:
        return 0.0
    return max(2.0, min(100.0, e / (2.0 * t) * 100.0))


# ── ce que le cadre laisse voir : la fraction VISIBLE de l'illustration ─────
def _clip_poly(poly, bw: float, bh: float):
    """Sutherland-Hodgman contre le rectangle [0,bw] x [0,bh]."""
    def cut(p, q, v, axis):
        d = q[axis] - p[axis]
        t = 0.0 if abs(d) < 1e-12 else (v - p[axis]) / d
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    tests = ((lambda p: p[0] >= 0.0, 0.0, 0), (lambda p: p[0] <= bw, bw, 0),
             (lambda p: p[1] >= 0.0, 0.0, 1), (lambda p: p[1] <= bh, bh, 1))
    cur = list(poly)
    for inside, v, axis in tests:
        nxt = []
        n = len(cur)
        for i in range(n):
            a, b = cur[i], cur[(i + 1) % n]
            ia, ib = inside(a), inside(b)
            if ia:
                nxt.append(a)
            if ia != ib:
                nxt.append(cut(a, b, v, axis))
        cur = nxt
        if not cur:
            return []
    return cur


def _poly_area(poly) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        s += a[0] * b[1] - b[0] * a[1]
    return abs(s) / 2.0


def visible_fraction(box_w: float, box_h: float, draw_w: float, draw_h: float,
                     off_x: float = 0.0, off_y: float = 0.0,
                     rot_rad: float = 0.0) -> float:
    """Part de l'illustration POSÉE qui tombe dans la fenêtre, dans [0, 1].

    REPROCHE, MOT POUR MOT : « en Couvrir sur la toile entière, ce que le
    cadre laisse réellement voir est un recadrage central. Le damier du haut
    et la bande de sol du bas sont supprimés du rendu. RIEN À L'ÉCRAN NE DIT
    À L'UTILISATEUR QUELLE FRACTION DE SON ILLUSTRATION SURVIT AU MASQUE. »

    Fondé. C'est le seul chiffre qui manquait à côté du DPI : une pose peut
    être à 324 DPI ET jeter le tiers du dessin. Le quadrilatère réellement
    dessiné — rotation comprise — est découpé par la fenêtre au polygone et
    on rend le rapport des aires. Exact, pas approché : à rotation nulle le
    résultat vaut le produit des recouvrements sur chaque axe, ce que le test
    vérifie."""
    if min(box_w, box_h, draw_w, draw_h) <= 0:
        return 0.0
    cx, cy = box_w / 2.0 + off_x, box_h / 2.0 + off_y
    c, s = math.cos(rot_rad), math.sin(rot_rad)
    quad = [(cx + x * c - y * s, cy + x * s + y * c)
            for x, y in ((-draw_w / 2, -draw_h / 2), (draw_w / 2, -draw_h / 2),
                         (draw_w / 2, draw_h / 2), (-draw_w / 2, draw_h / 2))]
    a = _poly_area(_clip_poly(quad, float(box_w), float(box_h)))
    return max(0.0, min(1.0, a / (draw_w * draw_h)))


# ── ajustement cover / contain / libre ──────────────────────────────────────
def fit_rect(src_w: float, src_h: float, box_w: float, box_h: float,
             mode: str = "cover", scale: float = 1.0) -> tuple[float, float]:
    """Taille dessinée (w, h) d'une source dans une fenêtre.

    `cover`   : remplit la fenêtre, déborde sur l'autre axe (aucun trou).
    `contain` : tient entièrement, laisse du vide.
    `free`    : `scale` est absolu, 1.0 = 1 pixel source pour 1 pixel toile.

    `scale` multiplie le facteur de base dans les deux premiers modes : c'est
    ce qui permet de zoomer à la molette SANS quitter le mode."""
    sw, sh = float(src_w), float(src_h)
    bw, bh = float(box_w), float(box_h)
    if sw <= 0 or sh <= 0 or bw <= 0 or bh <= 0:
        return 0.0, 0.0
    s = float(scale)
    if not math.isfinite(s) or s <= 0:
        s = 1.0
    s = max(SCALE_MIN, min(SCALE_MAX, s))
    if mode == "contain":
        base = min(bw / sw, bh / sh)
    elif mode == "free":
        base = 1.0
    else:                                   # cover, et tout mode inconnu
        base = max(bw / sw, bh / sh)
    return sw * base * s, sh * base * s


# ── amorces d'invite : pour une FACE DE CARTE, pas pour une image ───────────
# Chacune impose le cadrage vertical, le sujet centré et la marge de fond
# perdu — c'est ce qui distingue une amorce utile d'un « beau dragon ».
_FRAMING = ("cadrage vertical de carte à jouer, sujet centré, "
            "marge sur les bords pour le fond perdu")

PROMPT_SEEDS = [
    ("Créature de garde",
     "créature gardienne massive de trois-quarts, armure gravée, "
     "brume au sol, " + _FRAMING),
    ("Héros au combat",
     "héros en pleine action, cape en mouvement, éclat d'arme, "
     "arrière-plan simplifié, " + _FRAMING),
    ("Sort élémentaire",
     "explosion d'énergie élémentaire, volutes lumineuses, "
     "fond sombre pour lire le titre, " + _FRAMING),
    ("Paysage de royaume",
     "vaste paysage de royaume au crépuscule, silhouette d'architecture, "
     "ciel très travaillé, " + _FRAMING),
    ("Artefact posé",
     "artefact unique posé sur un socle, éclairage rasant, "
     "arrière-plan neutre, " + _FRAMING),
    ("Bête des profondeurs",
     "bête abyssale cuirassée, eaux sombres, rais de lumière, "
     + _FRAMING),
    ("Portail arcanique",
     "portail arcanique ouvert, runes flottantes, particules, "
     + _FRAMING),
    ("Monture ailée",
     "monture ailée en vol au-dessus des nuages, contre-jour, "
     + _FRAMING),
    ("Alchimiste",
     "alchimiste penché sur ses fioles luminescentes, clair-obscur, "
     + _FRAMING),
    ("Ruine engloutie",
     "ruine engloutie envahie de végétation, faisceau de lumière, "
     + _FRAMING),
    ("Blason héraldique",
     "blason héraldique stylisé, symétrie parfaite, aplats lisibles, "
     + _FRAMING),
    ("Champ de bataille",
     "champ de bataille au petit matin, étendards, poussière, "
     + _FRAMING),
    ("Familier",
     "petit familier expressif, pose dynamique, couleurs saturées, "
     + _FRAMING),
    ("Cité suspendue",
     "cité suspendue dans les nuages, ponts de pierre, échelle épique, "
     + _FRAMING),
    ("Rituel nocturne",
     "rituel nocturne, cercle de bougies, ombres portées longues, "
     + _FRAMING),
    ("Machine de guerre",
     "machine de guerre à vapeur, rivets, fumée, perspective basse, "
     + _FRAMING),
]


def prompt_seeds() -> list[dict]:
    return [{"label": lbl, "prompt": txt} for lbl, txt in PROMPT_SEEDS]


# ── le chunk pHYs : « 300 DPI » écrit DANS les octets ───────────────────────
PNG_SIG = b"\x89PNG\r\n\x1a\n"
PHYS_UNIT_METRE = 1               # le seul mode où pHYs vaut une résolution
MAX_PNG_BYTES = 96 * 1024 * 1024  # A3 à 600 DPI en RGBA tient très en dessous


def dpi_to_ppm(dpi) -> int:
    """DPI -> pixels par mètre, arrondi demi-haut. 300 -> 11811 (11811,024),
    600 -> 23622, 150 -> 5906. C'est le chiffre que la spec §4 P7 exige et que
    nanDECK écrit à 299,9994 DPI près."""
    d = float(dpi)
    if not math.isfinite(d) or d <= 0:
        raise ValueError("définition invalide")
    return int(math.floor(d / 0.0254 + 0.5))


def ppm_to_dpi(ppm) -> float:
    """La relecture. 11811 px/m -> 299,9994 DPI : on rend le VRAI nombre, pas
    l'entier qu'on aurait aimé lire."""
    return float(ppm) * 0.0254


def grid_mm(px: int, dpi) -> float:
    """Ce que `px` pixels MESURENT VRAIMENT à la densité écrite dans le fichier.

    AUTO-CRITIQUE DE CE TOUR, ET ELLE PORTE SUR UNE MENTION ÉCRITE DANS LE
    FICHIER LIVRÉ, donc plus grave qu'un chiffre d'écran. Le chunk `tEXt`
    Description annonçait « coupe 63 x 88 mm (744 x 1039 px) ». J'ai décodé le
    PNG à la main (zlib puis défiltrage) et refait la division sur ses propres
    octets : le fichier porte `pHYs` = 11811 px/m, donc 744 px y valent
    62,9921 mm et 1039 px y valent 87,9688 mm. Le fichier affirmait donc
    « 88 mm » là où ses deux autres chunks disent 87,969 — 31 µm d'écart.

    C'est infime, et ce n'est pas le sujet : c'est un nombre que le fichier
    lui-même dément. La cause est connue et incontournable — `pHYs` ne stocke
    que des entiers de pixels par mètre et la trame ne stocke que des pixels
    entiers, donc 88,000 mm n'est pas représentable. On cesse d'affirmer le
    nominal tout seul : la Description porte désormais le nominal ET la valeur
    de la maille, calculée par cette fonction, avec l'écart en micromètres.
    Miroir du calcul de `physLine` côté écran."""
    return float(px) / float(dpi_to_ppm(dpi)) * 1000.0


def png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    """[(type, charge utile)] d'un PNG, dans l'ordre. Lève sur toute trame qui
    n'est pas un PNG — jamais d'IndexError silencieuse."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("PNG attendu (octets)")
    b = bytes(data)
    if len(b) < 8 or not b.startswith(PNG_SIG):
        raise ValueError("ce ne sont pas des octets PNG (signature absente)")
    out: list[tuple[str, bytes]] = []
    p = 8
    while p + 8 <= len(b):
        (ln,) = struct.unpack(">I", b[p:p + 4])
        typ = b[p + 4:p + 8].decode("ascii", "replace")
        if p + 12 + ln > len(b):
            raise ValueError(f"chunk {typ} tronqué")
        out.append((typ, b[p + 8:p + 8 + ln]))
        p += 12 + ln
        if typ == "IEND":
            break
    if not out or out[0][0] != "IHDR":
        raise ValueError("PNG sans IHDR")
    return out


def png_size(data: bytes) -> tuple[int, int]:
    """(largeur, hauteur) lues dans IHDR."""
    ihdr = png_chunks(data)[0][1]
    if len(ihdr) < 8:
        raise ValueError("IHDR tronqué")
    w, h = struct.unpack(">II", ihdr[:8])
    return int(w), int(h)


def png_phys(data: bytes) -> tuple[int, int, int] | None:
    """(px_par_unité_x, y, unité) du chunk pHYs, ou None s'il n'y en a pas.
    C'est la mesure du critique, refaite ici : le PNG du duel rend None."""
    for typ, payload in png_chunks(data):
        if typ == "pHYs" and len(payload) >= 9:
            x, y = struct.unpack(">II", payload[:8])
            return int(x), int(y), int(payload[8])
    return None


def _chunk(typ: str, payload: bytes) -> bytes:
    t = typ.encode("ascii")
    return (struct.pack(">I", len(payload)) + t + payload
            + struct.pack(">I", zlib.crc32(t + payload) & 0xFFFFFFFF))


def png_with_phys(data: bytes, dpi: int) -> bytes:
    """Le même PNG, avec un `pHYs` juste après IHDR.

    Trois précautions qui font la différence entre « ça marche chez moi » et
    un fichier qu'un imprimeur ouvre :
      * un `pHYs` déjà présent est REMPLACÉ, jamais dupliqué (deux pHYs =
        fichier invalide, et certains lecteurs prennent le second) ;
      * le chunk est posé avant le premier IDAT — la spec PNG l'exige ;
      * le CRC est recalculé (`zlib.crc32(type + charge)`), sinon le fichier
        est rejeté par les décodeurs stricts.
    Les pixels ne sont PAS touchés : l'aperçu reste le fichier livré."""
    return png_finalize(data, dpi, texts=None, drop_alpha=False)[0]


# ── L'ESPACE DE COULEUR, écrit DANS les octets ──────────────────────────────
# LES DEUX CRITIQUES ONT RELEVÉ LA MÊME CHOSE : « ni iCCP, ni sRGB, ni gAMA,
# ni cHRM : l'imprimeur reçoit du RVB sans profil et devra deviner ». C'était
# vrai, et c'est la moitié d'un fichier de prépresse.
#
# POURQUOI LE CHUNK `sRGB` ET PAS UN PROFIL ICC RECOPIÉ. La spec PNG (11.3.3.4
# et 11.3.3.5) est explicite : `iCCP` et `sRGB` NE DOIVENT PAS coexister, et
# quand l'image est en sRGB, `sRGB` est la déclaration canonique — un octet
# d'intention de rendu, que tout décodeur moderne comprend, au lieu d'une copie
# de 3 kio du même profil. La spec recommande d'écrire EN PLUS `gAMA` et `cHRM`
# pour les lecteurs qui ne connaissent pas `sRGB` : c'est exactement ce que
# `png_set_sRGB_gAMA_and_cHRM()` de libpng écrit, avec ces valeurs-là.
SRGB_INTENT_PERCEPTUAL = 0
SRGB_GAMA = 45455                  # 1/2,2 x 100000, valeur libpng
SRGB_CHRM = (31270, 32900,         # point blanc D65
             64000, 33000,         # rouge
             30000, 60000,         # vert
             15000, 6000)          # bleu


def png_srgb_chunks() -> list[bytes]:
    """`sRGB` + `gAMA` + `cHRM`, dans l'ordre où libpng les écrit."""
    return [
        _chunk("sRGB", bytes([SRGB_INTENT_PERCEPTUAL])),
        _chunk("gAMA", struct.pack(">I", SRGB_GAMA)),
        _chunk("cHRM", struct.pack(">8I", *SRGB_CHRM)),
    ]


def png_srgb(data: bytes) -> int | None:
    """L'intention de rendu lue dans le chunk `sRGB`, ou None. La RELECTURE,
    pas la promesse."""
    for typ, payload in png_chunks(data):
        if typ == "sRGB" and len(payload) >= 1:
            return int(payload[0])
    return None


# ── Les métadonnées : quelle carte, quel format, quel logiciel ──────────────
# « Sur un jeu de plusieurs centaines de faces, rien dans l'octet ne dit de
# quelle carte il s'agit — seul le nom de fichier le porte. » Exact. Un nom de
# fichier se perd au premier renommage.
SOFTWARE = "Card Forge"
TEXT_MAX = 400


def _clean_text(s) -> str:
    """Pas de NUL (il termine le mot-clé et la valeur), pas de caractère de
    contrôle, longueur bornée. Une métadonnée mal formée casse le fichier."""
    out = []
    for ch in str(s or ""):
        if ch in ("\r", "\n", "\t"):
            out.append(" ")
        elif ord(ch) >= 32 and ch != "\x7f":
            out.append(ch)
    return "".join(out).strip()[:TEXT_MAX]


def png_text_chunk(key: str, value: str) -> bytes:
    """`tEXt` si tout tient en Latin-1, `iTXt` (UTF-8) sinon.

    `tEXt` est du LATIN-1, pas de l'UTF-8 : un nom de carte en cyrillique ou
    une œ écrits en tEXt sortent en charabia chez le lecteur. On choisit le
    chunk d'après les octets, pas d'après l'espoir."""
    k = _clean_text(key)[:79] or "Comment"
    v = _clean_text(value)
    try:
        return _chunk("tEXt", k.encode("latin-1") + b"\x00" + v.encode("latin-1"))
    except UnicodeEncodeError:
        # iTXt : mot-cle NUL, compression 0, methode 0, langue NUL, traduit NUL
        return _chunk(
            "iTXt",
            k.encode("ascii", "replace") + b"\x00\x00\x00\x00\x00"
            + v.encode("utf-8"))


def png_texts(data: bytes) -> dict[str, str]:
    """Les métadonnées RELUES dans les octets, tEXt et iTXt confondus."""
    out: dict[str, str] = {}
    for typ, payload in png_chunks(data):
        if typ == "tEXt" and b"\x00" in payload:
            k, v = payload.split(b"\x00", 1)
            out[k.decode("latin-1", "replace")] = v.decode("latin-1", "replace")
        elif typ == "iTXt" and payload.count(b"\x00") >= 4:
            k, rest = payload.split(b"\x00", 1)
            if len(rest) >= 2 and rest[0] == 0:
                body = rest[2:].split(b"\x00", 2)
                if len(body) == 3:
                    out[k.decode("ascii", "replace")] = body[2].decode("utf-8", "replace")
    return out


# ── Le canal alpha mort : mesuré, puis retiré ───────────────────────────────
# « PNG en RGBA avec un canal alpha uniformément à 255 : un quatrième canal
# inutile en impression, qui gonfle la charge utile d'environ 25 %. » Vrai :
# `canvas.toBlob` ne sait produire que du RGBA. On ne le retire JAMAIS sur
# parole : on lit les extrema du canal alpha sur les octets décodés, et on ne
# convertit que s'ils valent (255, 255). Un seul pixel translucide et le canal
# reste — retirer de l'information pour gagner des octets serait le pire des
# échanges.
def png_alpha_extrema(data: bytes) -> tuple[int, int] | None:
    """(min, max) du canal alpha, ou None si l'image n'en a pas."""
    try:
        from PIL import Image
    except ImportError:                                   # pragma: no cover
        return None
    import io
    with Image.open(io.BytesIO(data)) as im:
        if im.mode not in ("RGBA", "LA", "PA"):
            return None
        a = im.convert("RGBA").getchannel("A")
        lo, hi = a.getextrema()
        return int(lo), int(hi)


def png_strip_alpha(data: bytes) -> tuple[bytes, dict]:
    """Le même PNG en RGB, si et seulement si l'alpha est constant à 255.

    Rend `(octets, rapport)`. Le rapport dit ce qui a été MESURÉ :
    extrema du canal alpha, égalité stricte des trois canaux avant/après
    (`tobytes()` des deux images RVB), et les tailles. En cas d'échec ou
    d'absence de Pillow, les octets d'origine sont rendus tels quels avec le
    motif — jamais une conversion silencieuse."""
    rep: dict = {"retire": False, "raison": "", "avant": len(data)}
    try:
        from PIL import Image
    except ImportError:                                   # pragma: no cover
        rep["raison"] = "Pillow indisponible"
        return data, rep
    import io
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.mode != "RGBA":
                rep["raison"] = f"image en mode {im.mode}, pas de canal alpha à retirer"
                return data, rep
            lo, hi = im.getchannel("A").getextrema()
            rep["alpha_min"], rep["alpha_max"] = int(lo), int(hi)
            rep["pixels"] = im.width * im.height
            if (lo, hi) != (255, 255):
                rep["raison"] = (f"alpha non constant ({lo}..{hi}) : le canal porte "
                                 "de l'information, il reste")
                return data, rep
            rgb = im.convert("RGB")
            before = rgb.tobytes()
            buf = io.BytesIO()
            rgb.save(buf, format="PNG", optimize=True)
            out = buf.getvalue()
        with Image.open(io.BytesIO(out)) as re_im:
            after = re_im.convert("RGB").tobytes()
    except Exception as e:                                # pragma: no cover
        rep["raison"] = f"conversion impossible : {e}"
        return data, rep
    if after != before:                                   # pragma: no cover
        rep["raison"] = "les pixels RVB auraient changé : on garde l'original"
        return data, rep
    rep["retire"] = True
    rep["apres"] = len(out)
    rep["identique_rvb"] = True
    return out, rep


def png_finalize(data: bytes, dpi: int, texts: dict | None = None,
                 drop_alpha: bool = False) -> tuple[bytes, dict]:
    """Le fichier livré : pixels intacts, en-tête complet.

    Ordre des chunks — celui que la spec impose (tout ce qui précède `PLTE`
    d'abord, `pHYs` avant `IDAT`) :
        IHDR · sRGB · gAMA · cHRM · pHYs · tEXt/iTXt* · IDAT* · IEND
    Tout `sRGB`/`gAMA`/`cHRM`/`pHYs`/`tEXt`/`iTXt` déjà présent est REMPLACÉ,
    jamais doublé. Rend `(octets, rapport)` ; le rapport est ce que la route
    publie en en-têtes, et il ne contient que du mesuré."""
    rep: dict = {"alpha": {"retire": False, "raison": "non demandé"}}
    if drop_alpha:
        data, rep["alpha"] = png_strip_alpha(data)
    ppm = dpi_to_ppm(dpi)
    chunks = png_chunks(data)
    out = [PNG_SIG, _chunk("IHDR", chunks[0][1])]
    out += png_srgb_chunks()
    out.append(_chunk("pHYs", struct.pack(">IIB", ppm, ppm, PHYS_UNIT_METRE)))
    for k, v in (texts or {}).items():
        if _clean_text(v):
            out.append(png_text_chunk(k, v))
    drop = {"pHYs", "sRGB", "gAMA", "cHRM", "tEXt", "iTXt"}
    for typ, payload in chunks[1:]:
        if typ in drop:
            continue
        out.append(_chunk(typ, payload))
    blob = b"".join(out)
    ihdr = png_chunks(blob)[0][1]
    rep["colortype"] = int(ihdr[9])
    rep["depth"] = int(ihdr[8])
    rep["chunks"] = [t for t, _ in png_chunks(blob)]
    rep["octets"] = len(blob)
    return blob, rep


# ── LE TARIF : le chiffre que l'écran affiche avant de dépenser ─────────────
# REPROCHE, MOT POUR MOT : « la spec exige une face générée en un seul appel,
# avec le choix du modèle exposé et LE COÛT AFFICHÉ. Sur toute la planche il
# n'y a de cela qu'un mot : un onglet inerte. Pas un modèle, PAS UN PRIX. »
#
# « 1 image facturée » n'est pas un coût : c'est un compte. Ce qu'il faut,
# c'est un montant — et un montant inventé dans le JS serait exactement le
# chiffre invérifiable que ce tour interdit. On va donc le chercher LÀ OÙ
# L'APPLICATION LE TIENT DÉJÀ : `app.services.pricing`, la table qui alimente
# le compteur de dépense de tout le logiciel et que l'utilisateur édite dans
# Réglages → Tarifs & budget (pricing.json). Le prix affiché sur cette face
# est donc, à l'octet près, celui que le reste du produit facture.
#
# Un modèle absent de la table de tarifs rend `usd_par_image = null` et
# l'écran écrit « tarif non tabulé » : `pricing.estimate` retombe en silence
# sur le tarif de FLUX pour un identifiant inconnu, et afficher ce repli
# serait annoncer un prix qui n'est pas celui du modèle choisi.
def price_table() -> dict:
    """{model_id: {"label", "provider", "usd"}} d'après la table de tarifs de
    l'application. Vide (et non fausse) si le service est indisponible."""
    try:
        from app.services import pricing
    except Exception:                                     # pragma: no cover
        return {}
    try:
        p = pricing.load()
        table = getattr(pricing, "_IMAGE_MODELS", {}) or {}
        out = {}
        for mid, spec in table.items():
            label = spec[0] if len(spec) > 0 else str(mid)
            prov = spec[1] if len(spec) > 1 else ""
            key = spec[2] if len(spec) > 2 else None
            if key and key in p:
                out[str(mid)] = {"label": str(label), "provider": str(prov),
                                 "usd": float(p[key])}
        return out
    except Exception:                                     # pragma: no cover
        return {}


def _keyed_providers() -> set:
    """Les fournisseurs d'image dont la clé est enregistrée. Sert UNIQUEMENT
    de repli quand la route de l'application ne répond pas : sans lui, un
    incident de base de données ferait afficher « aucun modèle » alors que
    les clés sont là — un écran qui se trompe dans le sens rassurant."""
    try:
        from app.config import settings
    except Exception:                                     # pragma: no cover
        return set()
    out = set()
    if getattr(settings, "FAL_KEY", ""):
        out.add("fal")
    if getattr(settings, "OPENAI_API_KEY", ""):
        out.add("openai")
    return out


@router.get("/ai-models")
async def ai_models(did: str):
    """Les modèles d'image RÉELLEMENT servis, avec leur tarif unitaire.

    La liste vient de la route de l'application (`/api/image-models`) : elle
    ne montre que les modèles dont la clé est enregistrée, donc une liste
    VIDE veut dire « aucune clé », et l'écran doit le dire avant le clic
    plutôt que de laisser l'utilisateur découvrir l'échec après."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    prix = price_table()
    models: list = []
    configured = ""
    erreur = ""
    repli = False
    try:
        from app.api.routes import list_image_models
        d = await list_image_models()
        models = list((d or {}).get("models") or [])
        configured = str((d or {}).get("configured") or "")
    except Exception as e:
        # La route de l'application lit aussi un réglage en base : un incident
        # là ne doit pas faire disparaître des modèles dont la clé EST posée.
        # LE CHEMIN N'EN SORT PAS : une erreur SQLAlchemy porte volontiers le
        # DSN sqlite, donc le chemin absolu de la base — donc le nom de compte,
        # dans un champ servi. (Même filtre que les motifs de refus de la
        # série ; le jumeau `frame.py` porte la même ligne, à corriger là-bas.)
        erreur = _sans_chemin(e)
        repli = True
        keyed = _keyed_providers()
        models = [{"id": mid, "label": spec["label"], "provider": spec["provider"],
                   "note": ""}
                  for mid, spec in sorted(prix.items())
                  if spec["provider"] in keyed]
    out = []
    for m in models:
        mid = str(m.get("id") or "")
        spec = prix.get(mid)
        out.append({
            "id": mid,
            "label": str(m.get("label") or mid),
            "provider": str(m.get("provider") or ""),
            "note": str(m.get("note") or ""),
            "usd_par_image": (spec or {}).get("usd"),
        })
    return {
        "models": out,
        "configured": configured,
        "devise": "USD",
        "tarif_source": "la table de tarifs de l'application (Réglages → Tarifs "
                        "et budget, pricing.json) — le fournisseur facture "
                        "directement",
        "cle_absente": not out,
        "repli": repli,
        "erreur": erreur,
    }


# ── LA route : estampiller, mais seulement si la trame est la bonne ─────────
@router.post("/png/{fmt}/{dpi}")
async def stamp_png(did: str, fmt: str, dpi: int, request: Request,
                    title: str = "", card: str = "", alpha: str = "strip"):
    """Les octets PNG du moteur, rendus en fichier de prépresse.

    Le corps est le PNG **brut** produit par `CF.cardBlob` (spec §5) : rien
    n'est redessiné ici (risque 2 — deux moteurs = l'écran et le fichier qui
    divergent). On vérifie, on complète l'en-tête, on rend.

    Ce qui est écrit dans les octets, et que `canvas.toBlob` n'écrit pas :
      * `pHYs`   la résolution physique (sinon 72 DPI chez l'imprimeur) ;
      * `sRGB` + `gAMA` + `cHRM`  l'espace de couleur (sinon il devine) ;
      * `tEXt`/`iTXt`  quelle carte, quel format, quel logiciel ;
      * et le canal alpha mort est retiré — APRÈS avoir mesuré qu'il est
        constant à 255 et que les trois canaux RVB survivent à l'octet.

    409 si la trame ne fait pas `canvas_px` : estampiller « 300 DPI » sur une
    image qui n'a pas la taille de la toile serait exactement le mensonge que
    cette route existe pour empêcher."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    if fmt not in FORMATS:
        raise HTTPException(
            400, "Format inconnu : " + ", ".join(sorted(FORMATS)))
    if not (72 <= int(dpi) <= 1200):
        raise HTTPException(400, "La définition doit être entre 72 et 1200 DPI")
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyez les octets PNG")
    if len(raw) > MAX_PNG_BYTES:
        raise HTTPException(400, f"PNG trop lourd (> {MAX_PNG_BYTES} octets)")
    try:
        w, h = png_size(raw)
    except ValueError as e:
        raise HTTPException(400, f"PNG illisible : {e}")
    g = geom(fmt, int(dpi))
    if (w, h) != tuple(g.canvas_px):
        raise HTTPException(
            409,
            f"La trame fait {w} x {h} px ; la toile de {fmt} à {dpi} DPI fait "
            f"{g.canvas_px[0]} x {g.canvas_px[1]} px. Rien n'est estampillé : "
            "un fichier qui annonce une définition qu'il n'a pas est pire "
            "qu'un fichier muet.")
    texts = {
        "Software": SOFTWARE,
        "Title": _clean_text(title) or "carte sans titre",
        # CHAQUE NOMBRE DE CETTE LIGNE SE REFAIT SUR LES OCTETS DU FICHIER, ET
        # AUCUN N'AFFIRME PLUS QUE CE QUE LA MAILLE PERMET (voir `grid_mm`).
        "Description": (
            f"format {fmt} - coupe nominale {g.trim_mm[0]:g} x {g.trim_mm[1]:g} "
            f"mm ; {g.trim_px[0]} x {g.trim_px[1]} px a "
            f"{dpi_to_ppm(dpi)} px/m = {grid_mm(g.trim_px[0], dpi):.3f} x "
            f"{grid_mm(g.trim_px[1], dpi):.3f} mm ("
            f"{(grid_mm(g.trim_px[0], dpi) - g.trim_mm[0]) * 1000:+.0f} / "
            f"{(grid_mm(g.trim_px[1], dpi) - g.trim_mm[1]) * 1000:+.0f} um) - "
            f"toile {g.canvas_px[0]} x {g.canvas_px[1]} px, "
            f"{ppm_to_dpi(dpi_to_ppm(dpi)):.4f} DPI ecrits dans pHYs - "
            f"fond perdu {g.bleed_mm:g} mm = "
            f"{g.bleed_off_px[0]:g} / {g.bleed_off_px[1]:g} px - zone sure "
            f"{g.safe_px[0]} x {g.safe_px[1]} px a {g.safe_off_px[0]:g} / "
            f"{g.safe_off_px[1]:g} px"),
        # LE JETON DE RANGEMENT NE SORT PAS — NI DANS L'OCTET, NI À L'ÉCRAN.
        # Ce champ portait « carte 7 - jeu deck_088b3800 ». `did` est une clef
        # interne : elle n'apprend rien à qui ouvre le fichier, et le panneau
        # RELIT les métadonnées pour les afficher, donc elle repartait aussi
        # dans toute capture d'écran de l'export. Le module s'était déjà
        # interdit cela ailleurs, mot pour mot (« source local:fmspgoglyz9l7i
        # a été lu tel quel sur une capture »). Ce qui identifie la carte pour
        # un humain est déjà là : `Title` porte le nom du jeu, `Source` le
        # numéro de la carte.
        "Source": f"carte {_clean_text(card) or '?'}",
    }
    try:
        out, rep = png_finalize(raw, int(dpi), texts=texts,
                                drop_alpha=(alpha != "keep"))
    except ValueError as e:
        raise HTTPException(400, f"PNG illisible : {e}")
    ppm = dpi_to_ppm(dpi)
    a = rep.get("alpha", {})
    return Response(
        content=out,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="carte_{dpi}dpi.png"',
            "X-Cf-Phys-Ppm": str(ppm),
            "X-Cf-Canvas-Px": f"{w}x{h}",
            "X-Cf-Dpi-Reel": f"{ppm_to_dpi(ppm):.4f}",
            "X-Cf-Chunks": ",".join(rep.get("chunks", [])[:12]),
            "X-Cf-Colortype": str(rep.get("colortype", "?")),
            "X-Cf-Alpha": ("retire, constant 255 verifie sur "
                           f"{a.get('pixels', 0)} pixels" if a.get("retire")
                           else "conserve : " + str(a.get("raison", ""))),
            "X-Cf-Octets": f"{len(raw)}->{len(out)}",
        },
    )


# ════════════════════════════════════════════════════════════════════════════
# LA SÉRIE « AFFICHE POLONAISE » — une VOIE d'images, pas un remplacement
# ════════════════════════════════════════════════════════════════════════════
#
# CE QUE C'EST (plan de phase 5, D1). Le catalogue de P1 est vectoriel :
# 108 dessins calculés dans le navigateur, zéro octet de réseau, nets à
# n'importe quelle définition. C'est le SOCLE, et il ne bouge pas. La série
# est une SECONDE VOIE posée à côté : les mêmes 108 cases — les mêmes 18
# sujets, les mêmes 6 compositions, les mêmes noms — habillées d'images
# peintes par un modèle dans un langage visuel MESURÉ. Une case sans image
# retombe sur son dessin, et l'écran le DIT (l'insigne « vectoriel »).
#
# LE STYLE EST PORTÉ PAR DES NOMBRES, JAMAIS PAR UN NOM (D6). Le prompt de
# chaque case naît de la fiche mesurée (`style_walkuski.json`) : les fractions
# de composition, les bornes tonales et les hexadécimaux imposés en sortent
# tous. Aucun nom d'affichiste n'entre dans un prompt payant — les
# générateurs les refusent, et c'est la ligne du projet. `sans_nom_d_artiste`
# le vérifie AVANT chaque envoi : un grep coûte zéro, un refus est facturé.
#
# LE JUGE EST LE MÊME SCRIPT QUE CELUI QUI A MESURÉ LE CORPUS. Il note chaque
# candidat contre les bandes de la fiche et rend un verdict à trois états
# (TIENT / A RETOUCHER / HORS STYLE). C'est ce qui fait de « la série tient
# dans le style » un fait vérifiable plutôt qu'une impression.
#
# ── LA COPIE DU JUGE, ET POURQUOI ELLE EST ICI ─────────────────────────────
# Le juge et la fiche sont nés dans un SKILL, hors dépôt
# (`~/.claude/skills/walkuski-style/`). La campagne, elle, tourne sur le
# backend déployé, où ce dossier n'existe pas. Les deux fichiers sont donc
# COPIÉS dans la pièce — et une copie, dans ce projet, DATE SA SOURCE.
# `SERIE_JUGE` porte l'origine, la date et l'empreinte des octets ; un test
# recalcule l'empreinte (une retouche silencieuse rougit) et un second
# compare à l'amont QUAND il est là (une fiche re-mesurée rougit aussi,
# au lieu de laisser la campagne juger avec des bandes périmées).
SERIE_ID = "walkuski"
SERIE_V = 1                       # schéma du manifeste
SERIE_DIR = "cardforge_series"    # sous `DATA_ROOT`, patron des modèles perso
SERIE_PLAFOND_USD = 6.00          # LE MUR (plan D2) — dur, pas indicatif
SERIE_CANDIDATS = 6               # candidats par case à la première marche
# LE PLAFOND DU FOURNISSEUR, MESURÉ EN PAYANT (campagne T5, 25/08/2026).
# `fal-ai/flux/schnell` refuse `num_images > 4`, et il le refuse à la
# VALIDATION DU CORPS, avant tout calcul :
#   {'type': 'less_than_equal', 'loc': ['body', 'num_images'],
#    'msg': 'Input should be less than or equal to 4', 'input': 6}
# Les six candidats du plan D2 partent donc en DEUX tirs (4 + 2). Le prix ne
# bouge pas d'un centime : il se compte à l'IMAGE (6 × 0,003 $), jamais à
# l'appel — `_payer` reste inchangé, et le plafond de campagne aussi. C'est
# une contrainte de TRANSPORT, pas de facturation.
#
# CE QUI A LAISSÉ PASSER LE DÉFAUT : le banc vérifiait la SIGNATURE de
# `_flux_generate` (elle liait, et elle liait juste) mais jamais la VALEUR de
# son troisième argument. Une signature n'est pas un contrat de domaine : le
# fournisseur avait le droit de refuser un nombre que la fonction acceptait.
SERIE_FLUX_MAX = 4
SERIE_TAILLE = "portrait_4_3"     # cadre demandé au service de génération
SERIE_RATIO = "3:4"               # le même, dit comme l'édition l'écrit
JUGE_FICHIER = "style_walkuski.py"
FICHE_FICHIER = "style_walkuski.json"

# LE CADRE — ET POURQUOI C'EST LE MEILLEUR, PAS UN PIS-ALLER (aveu refait en
# ronde : la première rédaction citait « la face de carte du Cardforge
# (650x1024 = 0,635) », un nombre qui est la taille sous laquelle LA BARRE
# refuse un import et le rapport d'AUCUN des 12 formats — le test le vérifie).
#
# Les vrais rapports, relus dans `contract.geom` : toile poker 815x1110 =
# 0,7342, coupe 744x1039 = 0,7159. La fiche, elle, vise le 2:3 (0,6667) et le
# corpus portrait est à 0,695. Le service ne connaît que six cadres NOMMÉS :
# `portrait_4_3` (0,750) est à 0,0833 du 2:3, `portrait_16_9` (0,5625) à
# 0,1042.
#
# CE QUE L'ÉCART COÛTE, POSÉ SUR LA CARTE (mesuré, test à l'appui) : en
# « couvrir » sur la toile, une image 2:3 EXACTE perd 9,2 % de sa HAUTEUR —
# précisément là où vit la composition (la masse tient 76 % de la hauteur, le
# poids est bas-centre) ; le 3:4 demandé ne perd que 2,1 % de sa LARGEUR et
# RIEN de sa hauteur. Le cadre choisi est donc le MEILLEUR des deux pour ce
# que la fiche mesure, pas le moins mauvais.
#
# ET LE JUGE SURVIT AU RECADRAGE : la toile conforme recadrée à 0,7342 puis à
# 0,7159 tient encore (mesuré des deux côtés — la revue et le banc d'ici).
# Le verdict porte donc bien sur l'image que l'œil verra.
#
# LA MARCHE GPT, ELLE, LIVRE LE 2:3 EXACT : `image_providers._OPENAI_SIZE`
# mappe `portrait_4_3` sur 1024x1536, soit 0,6667 pile. Le même nom de cadre
# donne donc deux rapports selon la marche — c'est un BONUS sur la marche de
# secours, pas un défaut, et les DEUX miroirs sont épinglés au test pour que
# personne ne les fasse diverger en silence.

# CF-FACE-SERIES-BEGIN
SERIES = [
    ("vectoriel", "Vectoriel"),
    ("walkuski", "Affiche polonaise"),
]
# CF-FACE-SERIES-END

SERIE_JUGE = {
    "origine": "skill walkuski-style (user-level, ~/.claude/skills/"
               "walkuski-style/) — scripts/mesure_style.py + fiche_style.json",
    "copie_le": "2026-08-24",
    "corpus": "16 affiches 1986-2018, mesurées le 24/08/2026",
    # Empreintes SHA-256 des octets AVEC FINS DE LIGNE NORMALISÉES (le dépôt
    # stocke en LF, une copie de travail peut porter du CRLF : une empreinte
    # brute dirait « périmé » pour un contenu identique).
    "sha256": {
        "style_walkuski.py":
            "1a7b3bd0bcd01d55ed6449c3fda0a8422b43a3104ac85fd35c5713007b2901c4",
        "style_walkuski.json":
            "cd12cf8604c87a8d530857ec10b92e4c10c58085c1d5e0a38e5aae20d7c387c4",
    },
}

# LA RÈGLE DURE DU SKILL, RENDUE STRUCTURELLE. Un nom d'affichiste dans un
# prompt payant, c'est un refus facturé au mieux et un pastiche juridiquement
# sale au pire. La liste couvre l'auteur du corpus et ses contemporains de
# l'école polonaise — ceux qu'un rédacteur de prompt serait tenté de citer.
NOMS_INTERDITS = (
    "walkuski", "wałkuski", "swierzy", "świerzy", "starowieyski", "lenica",
    "tomaszewski", "pagowski", "pągowski", "sadowski", "olbinski", "olbiński",
    "dudzinski", "dudziński", "fangor", "mlodozeniec", "młodożeniec",
    "cieslewicz", "cieślewicz", "gorowski", "górowski", "czerniawski",
    # AJOUTS DE RONDE : deux affichistes de plus, chacun sous ses deux
    # graphies (la diacritique n'est pas une protection — un rédacteur la
    # tape rarement).
    "gorka", "górka", "eidrigevicius", "eidrigevičius",
)
PHRASES_INTERDITES = ("in the style of", "polish poster", "polishposter",
                      "à la manière de")
# ET UN MOTIF, parce qu'une liste de sous-chaînes ne voit pas ce qui se glisse
# ENTRE deux mots : « a polish school poster » passait au travers de
# « polish poster ». Le motif couvre l'école nommée en trois mots comme en un
# seul. (Les évasions par espacement exotique — « p o l i s h » — ne sont PAS
# visées : ces prompts sont construits par la machine, pas dictés.)
MOTIFS_INTERDITS = (re.compile(r"polish.{0,12}poster", re.I),)


# ── la fiche : la SOURCE des chiffres, jamais une décoration ────────────────
_FICHE: dict | None = None


def fiche_style() -> dict:
    """La fiche mesurée, lue une fois. Les prompts en DÉRIVENT : re-mesurer le
    corpus change les prompts sans qu'une ligne de code bouge — c'est la seule
    façon d'affirmer que la fiche « fait loi »."""
    global _FICHE
    if _FICHE is None:
        p = _Path(__file__).with_name(FICHE_FICHIER)
        _FICHE = json.loads(p.read_text(encoding="utf-8"))
    return _FICHE


def _juge_module():
    """Le juge, importé À L'APPEL. Il tire PIL ; le domaine « cartes » est
    monté au démarrage de l'application et n'a pas à payer cet import pour
    une route que personne n'appellera peut-être jamais."""
    from . import style_walkuski
    return style_walkuski


def _med(cle: str, defaut: float = 0.0) -> float:
    try:
        return float(fiche_style()["metriques"][cle]["med"])
    except (KeyError, TypeError, ValueError):             # pragma: no cover
        return defaut


def _pc(x: float) -> int:
    """Une fraction de la fiche, dite en pourcents entiers — c'est le registre
    du prompt (« about 43% of the canvas »), pas celui d'un tableur."""
    return int(round(float(x) * 100.0))


# ── les familles : un TIRAGE mesuré, pas une intuition ──────────────────────
#
# Le régime réel du corpus est « une famille à la fois » : 8 œuvres ocre,
# 4 rouges, 3 graphite (monochromes), 1 violette sur 16. Ces comptes ne sont
# PAS recopiés : ils se relisent dans la fiche, œuvre par œuvre, par la teinte
# du fond que le mesureur a relevée. Les bandes ci-dessous sont celles du
# skill (§1.3) ; une œuvre hors bandes serait comptée à part plutôt
# qu'attribuée de force — il n'y en a aucune dans ce corpus.
FAM_BANDES = (("rouge", 330.0, 50.0), ("ocre", 50.0, 130.0),
              ("violet", 250.0, 330.0))
FAM_ORDRE = ("ocre", "rouge", "graphite", "violet")


def _familles_du_corpus() -> dict:
    """{famille: nombre d'œuvres} relu dans la fiche."""
    out = {n: 0 for n in FAM_ORDRE}
    for m in fiche_style().get("par_oeuvre") or []:
        f = m.get("fond") or {}
        if f.get("monochrome") or f.get("hex") is None:
            out["graphite"] += 1
            continue
        h = float(f.get("h") or 0.0) % 360.0
        for nom, lo, hi in FAM_BANDES:
            dedans = (lo <= h < hi) if lo < hi else (h >= lo or h < hi)
            if dedans:
                out[nom] += 1
                break
    return out


def _familles_reparties(total: int) -> tuple:
    """Les comptes du corpus, portés à `total` cases par les PLUS FORTS
    RESTES. Sur 108 cases et le corpus de 16 : 54 ocre, 27 rouge, 20 graphite,
    7 violet — le tirage annoncé par le plan, obtenu sans le recopier."""
    corpus = _familles_du_corpus()
    n = sum(corpus.values()) or 1
    brut = {k: total * v / n for k, v in corpus.items() if v}
    plancher = {k: int(v) for k, v in brut.items()}
    reste = total - sum(plancher.values())
    for k in sorted(brut, key=lambda k: (-(brut[k] - plancher[k]),
                                         FAM_ORDRE.index(k))):
        if reste <= 0:
            break
        plancher[k] += 1
        reste -= 1
    return tuple((k, plancher[k]) for k in FAM_ORDRE if plancher.get(k))


def serie_cases() -> list:
    """Les 108 cases `<compo>_<sujet>` — la grille du catalogue, telle quelle.
    La série HABILLE, elle n'invente pas : noms et thèmes sont conservés."""
    return [f"{c['compo']}_{c['subject']}" for c in CATALOG]


try:
    FAMILLES = _familles_reparties(len(SUBJECTS) * len(COMPOS))
    PALETTE_NEUTRE = frozenset(
        e["hex"].upper() for e in fiche_style()["palette_maitre"]
        if float(e.get("C") or 0.0) < 10.0)
    FICHE_ERREUR = ""
except Exception as _e:                                   # pragma: no cover
    # UNE FICHE ILLISIBLE NE CASSE PAS LE DOMAINE « CARTES ». Elle éteint la
    # série, et les routes le disent — dix pièces ne tombent pas parce qu'un
    # fichier de données de l'une d'elles manque.
    FAMILLES, PALETTE_NEUTRE, FICHE_ERREUR = (), frozenset(), str(_e)[:200]


_FAM_PAR_CASE: dict | None = None


def serie_familles() -> dict:
    """{case: famille} — une ALLOCATION, pas un dé.

    Un tirage probabiliste par case aurait tenu les poids « à peu près » :
    sur 108 tirages, l'écart-type sur le compte ocre est de ±5. Ici les cases
    sont RANGÉES par empreinte (FNV-1a, la même graine que le catalogue) puis
    coupées aux quantités : les comptes sont EXACTS, et la famille d'une case
    ne dépend d'aucun état — la même case retire toujours la même famille,
    dans ce processus comme dans le suivant. C'est l'exigence de `scene_of`,
    appliquée au tirage de style : un équilibre annoncé se vérifie."""
    global _FAM_PAR_CASE
    if _FAM_PAR_CASE is None:
        rang = sorted(serie_cases(), key=lambda c: (fnv1a32(SERIE_ID + ":" + c), c))
        out: dict = {}
        i = 0
        for nom, n in FAMILLES:
            for c in rang[i:i + n]:
                out[c] = nom
            i += n
        for c in rang[i:]:                                # pragma: no cover
            out[c] = FAM_ORDRE[0]
        _FAM_PAR_CASE = out
    return _FAM_PAR_CASE


def serie_famille(case) -> str:
    return serie_familles().get(str(case or ""), "")


def serie_accent(case) -> bool:
    """Le GESTE coloré unique — et sa rareté, mesurée. 6 œuvres sur 16 portent
    une seconde teinte ; 10 n'en portent aucune. Les régimes rouge, violet et
    graphite n'en prennent jamais (leurs blocs de palette disent « no second
    hue » / « no hue anywhere ») : l'accent ne concerne que l'ocre, et
    seulement pour la fraction mesurée de ses cases, rangée par la même
    empreinte que les familles."""
    f = fiche_style()
    n_avec = max(0, int(f.get("n_oeuvres") or 0)
                 - int(f.get("n_sans_accent_isole") or 0))
    part = n_avec / float(f.get("n_oeuvres") or 1)
    ocres = sorted((c for c in serie_cases() if serie_famille(c) == "ocre"),
                   key=lambda c: (fnv1a32("accent:" + c), c))
    return str(case or "") in set(ocres[:int(round(len(ocres) * part))])


# ── le gabarit de prompt : six blocs, tous les nombres venus de la fiche ────
#
# [1 MATIÈRE] [2 SUJET] [3 COMPO] [4 PALETTE] [5 CLÉ] [6 INTERDITS]
#
# Le VOCABULAIRE de matière et la liste d'interdits sont de la prose : ils
# nomment un médium et refusent des réflexes de générateur (« dramatic
# lighting » appelle le contre-jour bleu et 25 % de toile claire). Tout ce qui
# est CHIFFRÉ, en revanche, se relit dans la fiche à chaque appel.

MATIERE = (
    "Oil paint on board with fine craquelure, hairline cracks running across "
    "the paint film, visible paint matter and soft airbrush-and-brush "
    "modelling, no photographic detail - a hand-painted 1980s Eastern "
    "European poster painting on a matte litho surface.")

INTERDITS = (
    "Not photographic, not a 3D render, not CGI, no digital sharpness, no "
    "crisp edges. No global saturation, no neon, no teal-and-orange grade, no "
    "vivid colours. No busy composition, no crowd, no second focal point, no "
    "background scenery detail. No text, no lettering, no title, no logo, no "
    "signature, no watermark, no border, no frame. No lens flare, no bokeh, "
    "no rim light, no glowing particles, no golden hour, no bright sky. "
    # LA MOITIÉ QUI MANQUAIT, ÉCRITE SUR CE QUE LA CAMPAGNE A MESURÉ. La liste
    # ci-dessus ne refusait que l'excès (trop clair, trop saturé, trop chargé)
    # — et le générateur tombait exactement de l'AUTRE côté, sur les six axes
    # à la fois. Une liste négative qui ne refuse qu'un bord pousse au bord
    # opposé.
    "And equally: no vast empty background, not a small subject lost in empty "
    "space, not a tiny distant figure, no wide margins of nothing. Not an "
    "underexposed or near-black image, no crushed blacks, not a flat "
    "silhouette without interior modelling, not a grey wash without any hue.")

# La MÉTAMORPHOSE, sujet par sujet — la seule part que la mesure ne sait pas
# écrire (le skill le dit : « la mesure ne voit pas le geste »). Une figure
# unique, jamais un décor : un élément d'arrière-plan ajouté fait tomber la
# part de vide sous 30 % et l'image sort du style.
SUJETS_SCENE = {
    "tower": "a single gaunt watchtower that is also a vertebra: the stone "
             "shaft is bone, the beam-slots are eye sockets, the roof has "
             "slumped like a skull crown",
    "pines": "a single pine that stands like a figure: the trunk a spine, the "
             "branches thin arms held out, the needles dry hair",
    "monolith": "a single standing stone with a face half-emerged from it, "
                "the open mouth a doorway, the surface split like dried skin",
    "dragon": "a single dragon head seen close, elongated and attenuated, "
              "its skull wrapped in dry parchment skin split along the jaw, "
              "the horns continuing into the dark as bare branches, eye closed",
    "sphinx": "a single seated guardian whose lion body has become knotted "
              "rope and sinew, the human face worn down to a plaster mask",
    "portal": "a single archway made of two enormous hands meeting at the "
              "fingertips, the opening between them flat unlit darkness",
    "crystals": "a single cluster of crystal growing out of an opened "
                "ribcage, the facets bone rather than glass",
    "ship": "a single hull that is a ribcage under sail, the mast a spine, "
            "the rigging drawn as sinew",
    "wolf": "a single wolf head, the muzzle elongated past nature, the pelt "
            "worn to dry parchment, the jaw held shut with coarse thread",
    "knight": "a single suit of armour standing empty and attenuated, the "
              "helm a socket, the mail a skin of dry scales",
    "citadel": "a single city grown on one vertebra: the towers teeth, the "
               "walls a jawbone, the gate a socket",
    "whale": "a single whale suspended without water, its flank opened like a "
             "book, the baleen a comb of bone",
    "phoenix": "a single bird whose wings are torn paper charring at the "
               "edge, the body a hollow cage of bone",
    "serpent": "a single sea serpent coiled into one knot, the scales dry "
               "parchment, the eye closed",
    "golem": "a single stone figure whose seams are stitched with sinew, the "
             "head a smooth featureless boulder",
    "archer": "a single archer drawn thin, the bow continuing out of the "
              "forearm, the string one long tendon",
    "grimoire": "a single heavy book standing open and upright, its two pages "
                "opening like a ribcage, the pages dry parchment skin, the "
                "binding sinew",
    "beacon": "a single brazier that is a cupped hand, the flame a torn sheet "
              "of pale cloth giving off no glow",
}

# La COMPOSITION garde le SENS qu'elle a dans le catalogue vectoriel (P1) —
# `medallion` n'a aucun horizon, `heraldry` est symétrique, `depths` est une
# colonne d'eau — mais dite en contraintes de peinture, pas en dessin.
COMPOS_SCENE = {
    # LE VOCABULAIRE DU VIDE, RETIRÉ DES SCÈNES AUSSI (T5bis). « bare
    # unmodulated ground », « flat and empty », « a flat ground » disaient au
    # générateur exactement ce que le bloc COMPO venait de lui interdire — et
    # sur 84 candidats c'est le vide qui a gagné (0,744 pour un plafond de
    # 0,546). Le SENS de chaque composition est intact — un horizon bas reste
    # un horizon bas, le disque reste un disque : seul « vide » devient
    # « uni, mais peint ».
    "vista": "one low horizon line far down the frame; everything above it is "
             "plain painted ground, no scenery, no second landmark",
    "medallion": "no horizon at all; the form is enclosed in one worn disc, "
                 "the rest of the frame plain but worked in paint",
    "heraldry": "strictly symmetrical about the vertical axis, the form and "
                "its own mirrored shadow, no horizon, no scenery",
    "depths": "the form suspended in a vertical column of dark water, a few "
              "faint vertical rays, nothing else",
    "backlight": "one pale disc of weak light behind the form and a plain "
                 "painted ground below it, nothing else in the frame",
    "stained": "the form set inside one tall pointed arch, thin lead lines "
               "dividing the field into large plain panes",
}


def _teintes(bande) -> list:
    """Les teintes maîtres de la fiche dans une bande de `h`, les plus
    présentes d'abord. `bande = None` rend les NEUTRES (C < 10)."""
    out = []
    for e in fiche_style()["palette_maitre"]:
        c = float(e.get("C") or 0.0)
        h = float(e.get("h") or 0.0) % 360.0
        if bande is None:
            if c < 10.0:
                out.append(e)
            continue
        lo, hi = bande
        dedans = (lo <= h < hi) if lo < hi else (h >= lo or h < hi)
        if c >= 10.0 and dedans:
            out.append(e)
    return sorted(out, key=lambda e: -float(e.get("part_relative") or 0.0))


def _bande_de(famille: str):
    for nom, lo, hi in FAM_BANDES:
        if nom == famille:
            return (lo, hi)
    return None


def _bloc_palette(famille: str, accent: bool) -> str:
    """[4 PALETTE] — les hexadécimaux et leurs parts de toile, tirés de la
    fiche. « Nommer une palette au lieu de la chiffrer » est la première des
    trois erreurs qui tuent le style : « muted earth tones » rend une chroma
    médiane de 45, `#4D453B à 25 % de la toile` en rend 9,9."""
    neutres = _teintes(None)
    while len(neutres) < 4:                               # pragma: no cover
        neutres = neutres + neutres
    hx = [e["hex"] for e in neutres]
    part_sol = _pc(sum(float(e["part_relative"]) for e in neutres[:2]))
    part_mod = _pc(sum(float(e["part_relative"]) for e in neutres[2:4]))
    if famille == "graphite":
        return ("Palette strictly limited to greys: " + ", ".join(hx[:4])
                + ". Essentially colourless - a graphite and charcoal "
                  "painting. No hue anywhere.")
    teintes = _teintes(_bande_de(famille)) or _teintes((50.0, 130.0))
    second = teintes[min(1, len(teintes) - 1)]["hex"]
    if famille == "ocre":
        part_forme = _pc(sum(float(e["part_relative"]) for e in teintes[:2]))
        bloc = ("Palette strictly limited to: %s and %s for the ground (about "
                "%d%% of the canvas together), %s and %s for the neutral "
                "modelling (about %d%%), %s and %s for the bone-ochre lit "
                "form (about %d%%). Muted throughout - but the colour is "
                "really there: the median pixel keeps a faint warm tint, it "
                "does not go grey."
                % (hx[0], hx[1], part_sol, hx[2], hx[3], part_mod,
                   teintes[0]["hex"], second, part_forme))
        if accent:
            rouges = _teintes(_bande_de("rouge"))
            part_acc = max(1, _pc(_med("accent.part_de_surface", 0.046)))
            bloc += (" One single accent of %s covering no more than %d%% of "
                     "the canvas - a small gesture, not a colour scheme."
                     % (rouges[0]["hex"] if rouges else hx[0], part_acc))
        return bloc
    ocres = _teintes((50.0, 130.0)) or neutres
    champ = _pc(_med("fond.part_coloree_totale", 0.44))
    return ("Palette strictly limited to: %s as the whole field (about %d%% of "
            "the canvas), %s as its transition, %s for the eaten edges, %s and "
            "%s for the bone-coloured form. No second hue."
            % (teintes[0]["hex"], champ, second, hx[1], ocres[-1]["hex"],
               hx[3]))


def _bloc_compo(compo: str) -> str:
    """[3 COMPO] — les fractions de la fiche, énoncées comme des placements.

    LE SENS EST CELUI QUE LA CAMPAGNE A MESURÉ, et il est l'INVERSE de ce
    qu'on croyait (T5bis, 84 candidats payés, mesurés au juge) :

        masse (surface)  0,194  pour une bande [0,415 ; 0,651] — 83/84 SOUS
        masse (largeur)  0,314  pour [0,553 ; 0,791]           — 81/84 SOUS
        part de vide     0,744  pour [0,320 ; 0,546]           — 84/84 AU-DESSUS

    Le générateur ne REMPLIT pas la toile : il la VIDE. Il lisait « about 43 %
    of the canvas left as quiet, unmodulated ground with no detail at all »
    comme une consigne de vide maximal, et rendait une petite forme perdue
    dans le noir — l'exact contraire de l'affiche, où une figure unique
    ÉCRASE le cadre.

    Les nombres ne changent pas (ils restent tirés de la fiche) ; c'est leur
    ÉNONCÉ qui change. La masse devient un PLANCHER, dit en premier et en
    capitales ; le fond cesse d'être un vide pour redevenir de la MATIÈRE
    PEINTE — qui porte de l'énergie locale, donc fait redescendre la part de
    vide sans qu'on ait à la nommer."""
    scene = COMPOS_SCENE.get(compo, "no scenery, no second subject")
    return ("Vertical composition, 2:3 portrait. THE SINGLE FORM DOMINATES "
            "THE FRAME: it fills AT LEAST %d%% of the frame width and AT "
            "LEAST %d%% of its height - monumental, seen close, so large that "
            "it runs past the top and the bottom edge of the frame. Its mass "
            "is centred on x=%.2f and y=%.2f, the heaviest weight low-centre, "
            "the right third emptier than the left. %s. The remaining %d%% of "
            "the canvas is quiet ground - but it is PAINTED ground: scumbled "
            "and uneven, carrying the craquelure and the drag of the brush, "
            "never a flat empty void. Only the outermost edges are eaten away "
            "into unlit darkness."
            % (_pc(_med("composition.masse_bbox.largeur", 0.69)),
               _pc(_med("composition.masse_bbox.hauteur", 0.76)),
               _med("composition.centroide_x", 0.45),
               _med("composition.centroide_y", 0.47),
               scene[0].upper() + scene[1:],
               _pc(_med("composition.part_vide_E_moins_4", 0.43))))


def _bloc_cle() -> str:
    """[5 CLÉ] — la clé tonale, chiffrée SUR LES SEUILS DU JUGE. Le prompt
    demande exactement ce que le juge mesurera : « sous 25 % de clarté » est
    le seuil `L<64` du mesureur, pas un chiffre choisi à la main.

    CORRIGÉ PAR LA MESURE (T5bis, mêmes 84 candidats) :

        L médian      41,9  pour une bande [63,3 ; 126,7] — 62/84 SOUS
        part sombre   0,773 pour [0,059 ; 0,514]          — 62/84 AU-DESSUS
        part claire   0,002 pour [0,012 ; 0,132]          — 46/84 SOUS

    « Dark-keyed » et « deep shadow occupies more area than light » étaient
    lus comme « éteins tout » : le générateur rendait des toiles quasi noires
    où le point clair n'existait PAS (0,2 % de toile au-dessus du seuil, pour
    4,2 % attendus). Et une toile noire est aussi une toile grise — c'est le
    même défaut qui faisait tomber la chroma médiane à 3,55 pour un plancher
    à 4,80, y compris sur les cases de régime ROUGE.

    Donc : la clé est dite par sa MÉDIANE — la valeur même que le juge
    mesure — la part sombre est un PLAFOND (« no more »), et le point clair
    devient une EXIGENCE plutôt qu'une permission."""
    sw = _juge_module()
    return ("Mid-dark key: the painting is dark overall, and its mid-tone sits "
            "at about %d%% lightness - dark, but not a black canvas. At least "
            "%d%% of the canvas is genuine deep shadow, below %d%% lightness. "
            "Against that dark, ONE SMALL bone-white highlight on the form, "
            "and it stays small: about %d%% of the canvas above %d%% lightness "
            "- no more than that, a coin of light on a dark painting, never a "
            "lit scene, never a bright image. Full tonal range, from true "
            "black to that one highlight, with modelling all the way between."
            % (int(round(_med("tons.L_p50", 99.8) / 255.0 * 100)),
               _pc(_med("tons.part_sombre_L_moins_64", 0.21)),
               int(round(sw.SEUIL_SOMBRE / 255.0 * 100)),
               max(1, _pc(_med("tons.part_claire_L_plus_200", 0.042))),
               int(round(sw.SEUIL_CLAIR / 255.0 * 100))))


def sans_nom_d_artiste(prompt: str) -> str:
    """LE GREP AVANT L'ENVOI. Il lève plutôt que de nettoyer : un prompt qui a
    besoin d'être nettoyé est un prompt écrit par erreur, et le nettoyer en
    silence le reconduirait au tir suivant."""
    bas = str(prompt or "").lower()
    for nom in NOMS_INTERDITS:
        if nom in bas:
            raise ValueError(
                "le prompt nomme un artiste (« " + nom + " ») : le style se "
                "porte par des mesures - palette, bornes tonales, fractions "
                "de composition - jamais par un nom")
    for phrase in PHRASES_INTERDITES:
        if phrase in bas:
            raise ValueError(
                "le prompt cite une manière (« " + phrase + " ») au lieu de "
                "la décrire : un style est une palette et des fractions")
    for motif in MOTIFS_INTERDITS:
        vu = motif.search(bas)
        if vu:
            raise ValueError(
                "le prompt cite une école (« " + vu.group(0) + " ») au lieu "
                "de la décrire : un style est une palette et des fractions")
    return prompt


def serie_prompt(case: str) -> str:
    """Le prompt d'une case — six blocs, tous les nombres venus de la fiche."""
    compo, _, sujet = str(case or "").partition("_")
    if sujet not in dict(SUBJECTS) or compo not in dict(COMPOS):
        raise KeyError(case)
    sujet_txt = SUJETS_SCENE.get(sujet, "a single form")
    return sans_nom_d_artiste("\n\n".join([
        MATIERE,
        sujet_txt[0].upper() + sujet_txt[1:] + ". Nothing else in the frame.",
        _bloc_compo(compo),
        _bloc_palette(serie_famille(case), serie_accent(case)),
        _bloc_cle(),
        INTERDITS,
    ]))


# Ce qu'une passe d'édition doit corriger, axe par axe — la clé du contrôle du
# juge donne la phrase. Un refus qui ne dit pas QUOI changer ne sert à rien.
CORRECTIFS = {
    "tons.part_claire_L_plus_200":
        "keep the lit area rare: only a small bone highlight above 78% "
        "lightness",
    "tons.L_p50": "bring the overall key down to a dark-to-middle grey",
    "tons.L_p95": "let one small highlight reach a true bone white",
    "tons.etendue_p05_p95": "widen the tonal range: true black AND one small "
                            "highlight, not a flat mid grey",
    "tons.part_sombre_L_moins_64": "give deep shadow more area than light",
    "saturation.C_lab_p50": "desaturate: the median pixel must be nearly grey",
    "saturation.C_lab_p95": "mute the most saturated colour, keep it dull",
    "saturation.part_quasi_gris_C_moins_10":
        "leave at least half the canvas without colour",
    "composition.part_vide_E_moins_4":
        "leave more of the canvas as quiet unmodulated ground, no detail",
    "composition.masse_bbox.part_surface":
        "make the single form fill more of the frame",
    "composition.masse_bbox.centre_y": "raise the mass towards the centre",
    "composition.centroide_y": "raise the visual weight towards the centre",
    "composition.part_bande_centrale":
        "pull the weight back into the central column",
    "fond.part_de_surface": "let one hue hold the whole field",
    "accent.part_de_surface": "keep the second hue to a single small gesture",
}


def serie_prompt_retouche(case: str, ecarts) -> str:
    """Le prompt d'ÉDITION : la même consigne, précédée de ce que le juge a
    trouvé de travers sur CETTE image. Les axes viennent du verdict, pas
    d'une liste écrite à l'avance."""
    corrige = []
    for e in ecarts or []:
        phrase = CORRECTIFS.get((e or {}).get("cle") or "")
        if phrase and phrase not in corrige:
            corrige.append(phrase)
    tete = "Repaint this image keeping its subject and its layout."
    if corrige:
        tete += " Fix exactly these: " + "; ".join(corrige) + "."
    return sans_nom_d_artiste(tete + "\n\n" + serie_prompt(case))


# ── le juge, en process ─────────────────────────────────────────────────────

def juger_image(chemin) -> dict:
    """Le verdict d'UNE image, par le mesureur du corpus. Rien ne sort de la
    machine : PIL pur, ~90 ms sur une image de série.

    Ce qui est rendu est ce dont la campagne a besoin — le score, le verdict à
    trois états, les axes CRITIQUES hors corpus (le motif d'un refus) et les
    écarts non tenus (ce qu'une passe d'édition doit corriger). Le détail
    complet reste dans le script : on ne le recopie pas."""
    sw = _juge_module()
    m = sw.mesurer(str(chemin))
    v = sw.verifier(m, fiche_style())
    ecarts = [{"cle": l["cle"], "metrique": l["metrique"],
               "valeur": l["valeur"], "etat": l["etat"],
               "critique": bool(l["critique"])}
              for l in v.get("lignes") or [] if l["etat"] != "DANS"]
    return {
        "verdict": v["verdict"],
        "score": float(v["score_pondere"]),
        "dE_median": v.get("dE_median_palette"),
        "axes_rouges": list(v.get("hors_critiques") or []),
        "ecarts": ecarts,
        "n_dans": v.get("n_dans"), "n_large": v.get("n_large"),
        "n_hors": v.get("n_hors"),
    }


_RANG_VERDICT = {"TIENT": 2, "A RETOUCHER": 1, "HORS STYLE": 0}


def meilleur_candidat(notes) -> dict:
    """Le meilleur d'un lot : le verdict d'abord, le score ensuite. Trier sur
    le seul score choisirait un « hors style » à 77 % contre un « à
    retoucher » à 60 % — or l'un est refusé par un axe critique et l'autre
    non ; ce sont deux natures, pas deux notes."""
    return max(notes or [], key=lambda n: (_RANG_VERDICT.get(n["verdict"], 0),
                                           n["score"]), default={})


# ── le manifeste : {DATA_ROOT}/cardforge_series/walkuski.json ───────────────
#
# SCHÉMA VERSIONNÉ (patron des modèles perso) :
#   {v, serie, cases:{"<compo>_<sujet>": {img, score, verdict, voie, famille,
#    prix_usd, at}}, refus:{"<case>": {score, verdict, axes_rouges, voie, at,
#    motif}}, depense_totale_usd, plafond_usd}
#
# LES CASES ET LES REFUS SONT SÉPARÉS, ET C'EST UNE DÉCISION. Une case refusée
# reste MANQUANTE : la campagne suivante la reprend (un modèle change, la
# fiche est re-mesurée, la chance tourne). Le refus, lui, est gardé avec ses
# axes rouges — c'est le seul document qui dise POURQUOI cette case-là résiste.

def serie_root():
    """`{DATA_ROOT}/cardforge_series/`. Résolu à l'APPEL, comme
    `models.models_root` : le dossier de données est une propriété du
    processus (`DEEPOTUS_DATA_DIR`), pas de l'import."""
    from app.config import DATA_ROOT
    p = DATA_ROOT / SERIE_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _manifeste_vierge() -> dict:
    return {"v": SERIE_V, "serie": SERIE_ID, "cases": {}, "refus": {},
            "depense_totale_usd": 0.0, "plafond_usd": SERIE_PLAFOND_USD}


def manifeste_lire() -> tuple:
    """`(manifeste, motif d'illisibilité)`. NE LÈVE PAS : un fichier abîmé rend
    un manifeste VIERGE et son motif — jamais un 500, et jamais un silence qui
    ferait croire que la campagne n'a rien fait."""
    p = serie_root() / (SERIE_ID + ".json")
    if not p.is_file():
        return _manifeste_vierge(), ""
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("le fichier ne porte pas un objet JSON")
    except OSError as e:
        # `str(OSError)` porte le CHEMIN ABSOLU, donc le nom de compte, et ce
        # motif part dans une réponse HTTP. `strerror` dit ce que l'OS a
        # refusé, et rien d'autre.
        return _manifeste_vierge(), (e.strerror or "E/S")
    except ValueError as e:
        return _manifeste_vierge(), ("JSON invalide : "
                                     + str(getattr(e, "msg", e))[:120])
    m = _manifeste_vierge()
    if isinstance(raw.get("cases"), dict):
        legales = set(serie_cases())
        m["cases"] = {k: v for k, v in raw["cases"].items()
                      if k in legales and isinstance(v, dict) and v.get("img")}
    if isinstance(raw.get("refus"), dict):
        m["refus"] = {k: v for k, v in raw["refus"].items()
                      if isinstance(v, dict)}
    try:
        m["depense_totale_usd"] = round(
            max(0.0, float(raw.get("depense_totale_usd") or 0.0)), 4)
    except (TypeError, ValueError):
        pass
    return m, ""


def manifeste_fusionner(case: str, ligne: dict, gagnee: bool,
                        delta_usd: float) -> dict:
    """UNE CASE, POSÉE SUR LE DISQUE, TOUT DE SUITE. Relit le manifeste, y
    ajoute CETTE case et CE delta de dépense, écrit, rend le fusionné.

    POURQUOI RELIRE PLUTÔT QU'ÉCRIRE L'OBJET EN MÉMOIRE : la ronde a mesuré un
    second écrivain qui effaçait la dépense du premier (5,00 $ ramenés à
    3,018 $). Un objet gardé en mémoire pendant toute une campagne est une
    photo périmée du disque ; la fusion, elle, ne perd ni la case ni le
    centime d'un voisin. Le verrou de campagne (`_coalesce`) sérialise déjà
    les campagnes d'une même série — cette relecture est la ceinture pour tout
    ce qui écrirait à côté (une reprise lancée hors ligne, un T5 qui répare
    une case à la main).

    LE DELTA PLUTÔT QUE LE TOTAL, pour la même raison : additionner un total
    calculé en mémoire écraserait ce qu'un autre a dépensé entre-temps."""
    m, _ = manifeste_lire()
    if gagnee:
        m["cases"][case] = dict(ligne)
        m["refus"].pop(case, None)
    else:
        m["refus"][case] = dict(ligne)
    m["depense_totale_usd"] = round(
        float(m.get("depense_totale_usd") or 0.0) + float(delta_usd or 0.0), 4)
    manifeste_ecrire(m)
    return m


def manifeste_ecrire(m: dict) -> None:
    """Écriture ATOMIQUE au patron de la phase 4 : brouillon UNIQUE (deux
    campagnes concurrentes ne se disputent pas le même temporaire) puis
    `replace` patient. Un manifeste tronqué, c'est 108 images payées et
    perdues."""
    d = serie_root()
    final = d / (SERIE_ID + ".json")
    tmp = d / (SERIE_ID + "." + uuid.uuid4().hex + ".tmp")
    m = dict(m)
    m["v"] = SERIE_V
    m["serie"] = SERIE_ID
    m["plafond_usd"] = SERIE_PLAFOND_USD
    try:
        tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        for reste in range(4, -1, -1):
            try:
                tmp.replace(final)
                return
            except OSError:
                if not reste:
                    raise
                time.sleep(0.02)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass                      # le brouillon a été renommé, ou jamais écrit


# ── les prix : lus dans la table de l'application, jamais recopiés ──────────

def prix_usd(modele: str, n: int = 1):
    """Le prix d'un tir, tel que le RESTE du logiciel le facture. `None` pour
    un modèle absent de la table : `pricing.estimate` retomberait EN SILENCE
    sur le tarif de FLUX, et facturer une campagne au tarif d'un autre modèle
    serait exactement le chiffre invérifiable que ce projet s'interdit."""
    try:
        from app.services import pricing
        if str(modele) not in getattr(pricing, "_IMAGE_MODELS", {}):
            return None
        d = pricing.estimate({"kind": "image", "model": str(modele),
                              "n": int(n)})
        return float(d["total_usd"])
    except Exception:                                     # pragma: no cover
        return None


def serie_prix() -> dict:
    """{modèle: $ par image} pour les trois marches de l'échelle."""
    return {m: prix_usd(m, 1) for m in SERIE_ECHELLE}


def cout_echelle_usd() -> float:
    """CE QUE COÛTE UNE CASE AU PIRE : l'échelle ENTIÈRE, six candidats FLUX +
    une édition + un GPT. Calculé sur la table, jamais écrit — un plafond qui
    se libelle dans une autre monnaie que la facture ne protège rien.

    C'est le nombre qui décide si une case s'OUVRE (correction de ronde) : le
    mur atteint au MILIEU d'une case brûlait les marches déjà payées sans
    laisser de trace, et le bilan annonçait « 3 traitées, 0 refusées » pour de
    l'argent parti. Une case ne commence donc que si elle peut finir."""
    total = 0.0
    for modele, n in ((SERIE_ECHELLE[0], SERIE_CANDIDATS),
                      (SERIE_ECHELLE[1], 1), (SERIE_ECHELLE[2], 1)):
        prix = prix_usd(modele, n)
        if prix is None:                                  # pragma: no cover
            continue
        total += prix
    return round(total, 4)


# ── les trois voies : le MÊME chemin de service que `/images/generate` ──────
#
# La campagne est une route de CE backend : elle ne se parle pas à elle-même
# en HTTP (un client vers son propre serveur, c'est un point mort dès que la
# boucle est occupée, et une seconde autorité sur les paramètres). Elle
# appelle les fonctions de service que `/images/generate` appelle :
# `_flux_generate` pour FLUX, la façade `image_providers.generate` pour les
# deux autres. C'est l'idiome de `routes.py`, répété à ses trois appels
# (images/generate, images/process, matériaux) — on l'imite, on ne recopie pas
# ses branches inlined.

async def _tirer_flux(prompt: str, n: int, graine: int) -> list:
    """Les `n` candidats, en autant de tirs que le fournisseur en accepte.

    Le nom est vérifié UNE fois, avant le premier tir : la garde est la même
    pour tous les lots, et rien ne part si elle lève."""
    from app.api.routes import _flux_generate
    propre = sans_nom_d_artiste(prompt)
    noms: list = []
    reste = max(0, int(n))
    tir = 0
    while reste > 0:
        lot = min(reste, SERIE_FLUX_MAX)
        # UNE GRAINE PAR TIR. La même graine pour les deux lots rendrait le
        # second identique au premier : on paierait six images pour n'en
        # juger que quatre distinctes. Décalée par le RANG du tir, elle reste
        # déterministe — la même case retire toujours les mêmes candidats.
        out = await _flux_generate(propre, SERIE_TAILLE, lot,
                                   seed=(int(graine) + tir) & 0x7FFFFFFF)
        noms.extend((out or {}).get("images") or [])
        reste -= lot
        tir += 1
    return noms


async def _tirer_banana(prompt: str, source: str) -> list:
    from app.services import image_providers
    from app.config import settings
    out = await image_providers.generate(
        "nano-banana", sans_nom_d_artiste(prompt), SERIE_TAILLE, 1,
        image_path=settings.images_path / str(source), ratio=SERIE_RATIO)
    return list((out or {}).get("images") or [])


async def _tirer_gpt(prompt: str) -> list:
    from app.services import image_providers
    out = await image_providers.generate(
        "gpt-image-2", sans_nom_d_artiste(prompt), SERIE_TAILLE, 1)
    return list((out or {}).get("images") or [])


def tient_sous_le_mur(cumul: float, cout: float) -> bool:
    """LE MUR, EN UN SEUL ENDROIT. La boucle demande « cette case peut-elle
    finir ? » et chaque tir demande « celui-ci passe-t-il ? » : deux questions,
    une seule arithmétique. Écrites deux fois, elles auraient fini par
    diverger — et la divergence n'aurait été visible que sur une facture."""
    return (float(cumul) + float(cout)) <= SERIE_PLAFOND_USD + 1e-9


class _Plafond(Exception):
    """Le mur, atteint. Levée plutôt que rendue : elle remonte de la marche où
    elle survient jusqu'à la boucle, sans qu'aucune marche intermédiaire ait à
    savoir compter."""


def _cles_posees() -> dict:
    from app.config import settings
    return {"fal": bool(getattr(settings, "FAL_KEY", "")),
            "openai": bool(getattr(settings, "OPENAI_API_KEY", ""))}


def _horodate() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# UN MESSAGE SERVI NE PORTE JAMAIS DE CHEMIN ABSOLU — la jurisprudence de la
# fuite de nom de compte, appliquée à la porte que personne ne surveillait :
# le MOTIF D'UN ÉCHEC. `PIL.UnidentifiedImageError` porte le chemin complet du
# fichier ; ce motif part dans la réponse HTTP ET dans le manifeste écrit sur
# le disque, que T5 publiera. La classe de l'exception reste (elle sert au
# diagnostic), le chemin s'en va.
_CHEMIN_RE = re.compile(r"""(?:[A-Za-z]:[\\/]|[\\/]{1,2})[^\s'"]{2,}""")


def _sans_chemin(txt, n: int = 200) -> str:
    return _CHEMIN_RE.sub("<chemin>", str(txt or ""))[:n]


# ── LA CAMPAGNE — l'échelle de secours, le journal, le mur ──────────────────
#
# L'ÉCHELLE (plan D2), marche par marche, pour UNE case :
#
#   1. six candidats FLUX schnell d'un seul appel — sur un modèle à 0,003 $,
#      sur-générer coûte moins cher qu'un aller-retour de prompt ;
#   2. le juge note les six ; le meilleur qui TIENT gagne, et c'est fini ;
#   3. sinon, si le meilleur est « à retoucher », UNE passe d'édition
#      nano-banana partant de CE fichier, avec les axes à corriger dans le
#      prompt. Si le lot entier est hors style, on saute cette marche : il n'y
#      a rien à retoucher, et une édition partant d'un raté coûte pour rien ;
#   4. sinon, UN GPT Image 2 ;
#   5. sinon la case RESTE VECTORIELLE, et son refus est journalisé avec ses
#      axes rouges. Une case sans image n'est pas un trou : c'est le dessin du
#      catalogue, et l'écran le dit.
#
# LE MUR EST VÉRIFIÉ AVANT CHAQUE TIR, pas après : `dépense + prix > plafond`
# arrête la campagne AVANT l'appel. Le prix vient de `pricing`, jamais d'un
# nombre écrit ici, et il est JOURNALISÉ avant l'appel — c'est ce qui rend le
# plafond vérifiable après coup, y compris pour un tir qui a échoué.
#
# UN TIR QUI ÉCHOUE EST COMPTÉ QUAND MÊME. On ne sait pas si le fournisseur a
# facturé avant de tomber ; compter est l'erreur du bon côté (le plafond est
# atteint plus tôt, jamais plus tard), et le journal porte `panne` pour que le
# bilan ne fasse pas passer une panne pour une dépense utile.

SERIE_ECHELLE = ("flux", "nano-banana", "gpt-image-2")
SERIE_MOTIFS = {
    "fin": "toutes les cases demandées ont été traitées",
    "limite": "limite de session atteinte",
    "plafond": "plafond de campagne atteint : la campagne s'arrête, elle "
               "reprendra au prochain lancement",
    "rien": "aucune case à faire : la série est complète pour cette demande",
    "fiche": "la fiche de style est illisible : aucune campagne possible",
}


async def _fabriquer_case(case: str, sac: dict, journal: list) -> dict:
    """Une case, de bout en bout. Rend le verdict retenu (gagnant ou refus).

    `sac` porte la seule chose mutable de l'affaire : `depense_totale_usd`, le
    cumul à cet instant. Ce n'est plus le MANIFESTE qu'on promène (il vit sur
    le disque et se fusionne case par case) — un objet gardé en mémoire toute
    une campagne finissait par écraser ce qu'un voisin avait écrit.

    Lève `_Plafond` si un tir ne tient pas sous le mur ; en pratique la boucle
    a déjà refusé d'OUVRIR une case qui ne pourrait pas finir, donc cette
    levée-ci est la ceinture (les prix peuvent changer en cours de campagne :
    `pricing.json` est éditable pendant qu'elle tourne)."""
    from app.config import settings

    async def _payer(modele: str, n: int) -> float:
        prix = prix_usd(modele, n)
        if prix is None:
            raise RuntimeError(
                "modèle « " + modele + " » absent de la table de tarifs : "
                "aucun tir n'est lancé sans son prix")
        avant = float(sac.get("depense_totale_usd") or 0.0)
        if not tient_sous_le_mur(avant, prix):
            raise _Plafond()
        journal.append({"case": case, "modele": modele, "n": int(n),
                        "prix_usd": round(prix, 4),
                        "cumul_avant_usd": round(avant, 4),
                        "cumul_apres_usd": round(avant + prix, 4),
                        "at": _horodate(), "panne": False})
        logger.info(
            f"cardforge/serie {case} : {modele} x{int(n)} = {prix:.4f} USD "
            f"(cumul {avant:.4f} -> {avant + prix:.4f}, "
            f"plafond {SERIE_PLAFOND_USD:.2f})")
        sac["depense_totale_usd"] = round(avant + prix, 4)
        return prix

    async def _juger(noms: list) -> list:
        notes = []
        for nom in noms:
            chemin = settings.images_path / str(nom)
            note = await asyncio.to_thread(juger_image, chemin)
            note["img"] = str(nom)
            notes.append(note)
        return notes

    prompt = serie_prompt(case)
    graine = fnv1a32(SERIE_ID + ":" + case) & 0x7FFFFFFF

    # marche 1 — FLUX, six candidats d'un seul appel
    prix_case = await _payer("flux", SERIE_CANDIDATS)
    try:
        noms = await _tirer_flux(prompt, SERIE_CANDIDATS, graine)
    except Exception as e:
        journal[-1]["panne"] = True
        raise _Panne(_sans_chemin(e))
    if not noms:
        journal[-1]["panne"] = True
        raise _Panne("le générateur n'a rendu aucune image")
    best = meilleur_candidat(await _juger(noms))
    best["voie"] = "flux"
    if best.get("verdict") == "TIENT":
        best["prix_usd"] = round(prix_case, 4)
        return best

    # marche 2 — UNE édition, seulement s'il y a quelque chose à retoucher
    if best.get("verdict") == "A RETOUCHER":
        prix_case += await _payer("nano-banana", 1)
        try:
            noms = await _tirer_banana(
                serie_prompt_retouche(case, best.get("ecarts")), best["img"])
        except Exception as e:
            journal[-1]["panne"] = True
            raise _Panne(_sans_chemin(e))
        if noms:
            neuf = meilleur_candidat(await _juger(noms))
            neuf["voie"] = "nano-banana"
            if neuf.get("verdict") == "TIENT":
                neuf["prix_usd"] = round(prix_case, 4)
                return neuf
            best = max([best, neuf],
                       key=lambda n: (_RANG_VERDICT.get(n["verdict"], 0),
                                      n["score"]))

    # marche 3 — un GPT Image 2, la dernière
    prix_case += await _payer("gpt-image-2", 1)
    try:
        noms = await _tirer_gpt(prompt)
    except Exception as e:
        journal[-1]["panne"] = True
        raise _Panne(_sans_chemin(e))
    if noms:
        neuf = meilleur_candidat(await _juger(noms))
        neuf["voie"] = "gpt-image-2"
        if neuf.get("verdict") == "TIENT":
            neuf["prix_usd"] = round(prix_case, 4)
            return neuf
        if neuf["score"] > best["score"]:
            best = neuf
    best["prix_usd"] = round(prix_case, 4)
    return best


class _Panne(Exception):
    """Un fournisseur qui tombe n'est pas un échec de STYLE. La case est
    refusée avec le motif technique, la campagne continue sur la suivante — et
    on ne monte PAS l'échelle : gravir des marches sur une chaîne cassée, ce
    serait payer trois fois la même panne."""


async def campagne(demandees=None, limite: int = 0) -> dict:
    """Les cases MANQUANTES, une par une, jusqu'au mur ou à la limite.

    DEUX RÈGLES NÉES DE LA RONDE, et elles tiennent ensemble :

    (a) LE MANIFESTE S'ÉCRIT APRÈS CHAQUE CASE. Écrit après la boucle, il
        disparaissait entièrement à la première exception : deux cases gagnées
        ET PAYÉES perdues, `depense_totale` à 0,00 pour 0,054 $ partis — donc
        un plafond qui ne protège plus rien dès la deuxième tentative.

    (b) UNE CASE NE S'OUVRE QUE SI L'ÉCHELLE ENTIÈRE TIENT. Le mur atteint au
        MILIEU d'une case laissait les marches déjà payées sans aucune trace,
        et le bilan annonçait « 0 refusée ». Le reliquat inutilisable est
        maintenant AVOUÉ.

    Et l'`except` de la boucle attrape `Exception` : un juge qui tombe (une
    image illisible EST un `OSError`, pas un `ValueError`) est traité comme un
    fournisseur qui tombe — la case part en refus journalisé, la campagne
    CONTINUE."""
    m, illisible = manifeste_lire()
    if not FAMILLES:                                      # pragma: no cover
        return dict(_bilan(m, [], [], [], "fiche"), illisible=illisible)
    voulues = list(demandees) if demandees else serie_cases()
    restantes = [c for c in voulues if c not in m["cases"]]
    traitees, refusees, journal = [], [], []
    sac = {"depense_totale_usd": float(m.get("depense_totale_usd") or 0.0)}
    echelle = cout_echelle_usd()
    arret = "fin" if restantes else "rien"
    for case in restantes:
        if limite and len(traitees) + len(refusees) >= limite:
            arret = "limite"
            break
        if not tient_sous_le_mur(sac["depense_totale_usd"], echelle):
            arret = "plafond"
            break
        avant = sac["depense_totale_usd"]
        try:
            note = await _fabriquer_case(case, sac, journal)
        except _Plafond:                                  # pragma: no cover
            arret = "plafond"
            break
        except _Panne as e:
            note = {"verdict": "HORS STYLE", "score": 0.0, "axes_rouges": [],
                    "voie": "", "motif": str(e), "prix_usd": 0.0}
        except Exception as e:
            # UN JUGE QUI TOMBE = UN FOURNISSEUR QUI TOMBE. `except (KeyError,
            # ValueError, RuntimeError)` laissait passer
            # `PIL.UnidentifiedImageError`, qui est un `OSError` : la campagne
            # levait et emportait tout. Le motif nomme la classe, pour qu'un
            # incident se diagnostique sans relire le journal du serveur.
            note = {"verdict": "HORS STYLE", "score": 0.0, "axes_rouges": [],
                    "voie": "", "prix_usd": 0.0,
                    "motif": _sans_chemin(e.__class__.__name__ + " : " + str(e))}
        ligne = {"case": case, "famille": serie_famille(case),
                 "voie": note.get("voie") or "",
                 "score": round(float(note.get("score") or 0.0), 1),
                 "verdict": note.get("verdict") or "HORS STYLE",
                 "prix_usd": note.get("prix_usd", 0.0),
                 "at": _horodate()}
        gagnee = bool(note.get("verdict") == "TIENT" and note.get("img"))
        if gagnee:
            ligne["img"] = note["img"]
            ligne["dE_median"] = note.get("dE_median")
            traitees.append(ligne)
        else:
            ligne["axes_rouges"] = list(note.get("axes_rouges") or [])
            if note.get("motif"):
                ligne["motif"] = note["motif"]
            elif ligne["axes_rouges"]:
                ligne["motif"] = ("axes hors corpus : "
                                  + ", ".join(ligne["axes_rouges"]))
            else:
                ligne["motif"] = ("aucun candidat ne TIENT (meilleur score "
                                  + str(ligne["score"]) + ")")
            ligne["ecarts"] = [e["metrique"] for e in (note.get("ecarts") or [])]
            refusees.append(ligne)
        # LE DISQUE, TOUT DE SUITE — et le cumul RESYNCHRONISÉ sur ce que le
        # disque porte après fusion (si un voisin a dépensé pendant ce
        # temps-là, le mur se resserre : l'erreur du bon côté).
        m = manifeste_fusionner(case, ligne, gagnee,
                                sac["depense_totale_usd"] - avant)
        sac["depense_totale_usd"] = float(m["depense_totale_usd"])
    return dict(_bilan(m, traitees, refusees, journal, arret, echelle),
                illisible=illisible)


def _usd(x: float) -> str:
    """Un montant en français, pour un message lu par un humain."""
    return ("%.2f" % float(x)).replace(".", ",")


def _bilan(m: dict, traitees, refusees, journal, arret: str,
           echelle: float = 0.0) -> dict:
    depense = round(float(m.get("depense_totale_usd") or 0.0), 4)
    faites = len(m.get("cases") or {})
    total = len(serie_cases())
    session = round(sum(float(l["prix_usd"]) for l in journal), 4)
    reste = round(max(0.0, SERIE_PLAFOND_USD - depense), 4)
    message = SERIE_MOTIFS.get(arret, arret)
    if arret == "plafond":
        # LE RELIQUAT EST AVOUÉ AVEC SES DEUX NOMBRES. « Plafond atteint » sur
        # un compteur à 5,40 $ pour un plafond de 6,00 $ se lit comme une
        # erreur ; ce qui manque, c'est de dire que 0,60 $ n'ouvre pas une
        # case parce qu'une case coûte 1,96 $ au pire.
        message = ("plafond de campagne atteint : reste " + _usd(reste)
                   + " $ — insuffisant pour ouvrir une case, l'échelle "
                   "complète coûte " + _usd(echelle) + " $. La campagne "
                   "reprendra au prochain lancement.")
    return {
        "echelle_usd": round(float(echelle), 4),
        "serie": SERIE_ID, "v": SERIE_V, "total": total, "faites": faites,
        # `n_refus` et non `refus` : la route d'état publie sous `refus` le
        # DICTIONNAIRE des refus. Deux formes sous une même clé, dans la même
        # fonctionnalité, c'est le genre d'écart qu'un écran découvre en
        # production.
        "restantes": total - faites, "n_refus": len(m.get("refus") or {}),
        "traitees": traitees, "refusees": refusees, "journal": journal,
        "arret": arret, "message": message,
        "depense_session_usd": session, "depense_totale_usd": depense,
        "plafond_usd": SERIE_PLAFOND_USD,
        "reste_usd": round(max(0.0, SERIE_PLAFOND_USD - depense), 4),
    }


# ── DEUX CLICS NE PAIENT PAS DEUX FOIS ──────────────────────────────────────
#
# La leçon T3 de la phase 4, sur un geste bien plus cher : douze POST
# simultanés donneraient douze campagnes, donc douze fois la même facture.
# Un appel en vol pour la série ; tous les demandeurs suivants attendent
# CELUI-LÀ et reçoivent le même bilan, marqué `coalesce`.
#
# CE QUE LA COALESCENCE COÛTE, ET C'EST DIT : le second appelant reçoit le
# bilan de la campagne EN VOL, pas celui de ses propres paramètres. C'est le
# bon échange — deux campagnes concurrentes sur la même série se marcheraient
# de toute façon dessus dans le manifeste, et la seconde paierait des cases
# que la première est en train de faire.
_EN_VOL: dict = {}


async def _coalesce(cle: str, faire):
    tache = _EN_VOL.get(cle)
    if tache is None or tache.done():
        tache = asyncio.ensure_future(faire())
        _EN_VOL[cle] = tache
        mien = True
    else:
        mien = False
    try:
        return await asyncio.shield(tache), mien
    finally:
        if _EN_VOL.get(cle) is tache and tache.done():
            _EN_VOL.pop(cle, None)


# ── les deux routes ─────────────────────────────────────────────────────────

def _cases_demandees(brut) -> list:
    """`?cases=a,b,c` → la liste, ou une levée qui NOMME ce qui cloche.

    LE PARAMÈTRE ABSENT (`None`) VEUT DIRE « TOUTE LA SÉRIE » ; LE PARAMÈTRE
    PRÉSENT ET VIDE NE VEUT PAS DIRE ÇA. Mesuré en ronde : `?cases=` et
    `?cases=,,,` rendaient 200 et lançaient les 108 cases. Sur une route qui
    dépense, « je n'ai rien choisi » ne peut pas signifier « fais tout » —
    c'est un refus nommé (D2-4)."""
    if brut is None:
        return []
    voulues = [c.strip() for c in str(brut).split(",") if c.strip()]
    if not voulues:
        raise ValueError(
            "sélection vide : `cases` est présent mais ne nomme aucune case. "
            "Retirez le paramètre pour viser toute la série, ou nommez les "
            "cases — une case s'écrit « <composition>_<sujet> », par exemple "
            + serie_cases()[0])
    legales = set(serie_cases())
    inconnues = [c for c in voulues if c not in legales]
    if inconnues:
        raise ValueError(
            "case inconnue : " + ", ".join(inconnues[:5])
            + " — une case s'écrit « <composition>_<sujet> », par exemple "
            + serie_cases()[0])
    vues, sortie = set(), []
    for c in voulues:
        if c not in vues:
            vues.add(c)
            sortie.append(c)
    return sortie


def _limite_demandee(brut) -> int:
    """Même règle que `cases` : absent = pas de borne, présent et vide = un
    refus nommé (c'est une faute de frappe, pas une intention)."""
    if brut is None:
        return 0
    s = str(brut).strip()
    if not s:
        raise ValueError("`limite` est présent mais vide : retirez le "
                         "paramètre, ou donnez un entier positif")
    try:
        n = int(s)
    except ValueError:
        raise ValueError("la limite doit être un entier (reçu « "
                         + s[:20] + " »)")
    if n <= 0:
        raise ValueError("la limite doit être un entier positif : une session "
                         "de zéro case n'est pas une session")
    return min(n, len(serie_cases()))


@router.get("/serie")
async def serie_etat(did: str):
    """L'état de la série : ce qui est fait, ce qui a été refusé, ce que ça a
    coûté, ce qu'il reste sous le plafond, et le prix de chaque marche.

    JAMAIS 500 : un manifeste abîmé rend un état VIDE et le dit (`illisible`),
    une fiche illisible éteint la série et le dit aussi.

    LE JEU DOIT EXISTER, comme pour la campagne. Le manifeste est GLOBAL (les
    108 images sont un bien commun), mais la route vit sous un deck : rendre
    200 ici quand la campagne rend 404 pour le même identifiant, c'est offrir
    à un écran deux réponses contradictoires à la même question."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    from .contract import deck_dir
    if not deck_dir(did).is_dir():
        raise HTTPException(404, "Jeu introuvable")
    m, illisible = manifeste_lire()
    total = len(serie_cases())
    return {
        "serie": SERIE_ID, "v": SERIE_V, "series": [
            {"id": i, "label": lbl} for i, lbl in SERIES],
        "total": total, "faites": len(m["cases"]),
        "restantes": total - len(m["cases"]),
        "cases": m["cases"], "refus": m["refus"],
        "depense_totale_usd": round(float(m["depense_totale_usd"]), 4),
        "plafond_usd": SERIE_PLAFOND_USD,
        "reste_usd": round(max(0.0, SERIE_PLAFOND_USD
                               - float(m["depense_totale_usd"])), 4),
        "prix": serie_prix(), "devise": "USD",
        "cles": _cles_posees(),
        "familles": dict(FAMILLES),
        "juge": {k: SERIE_JUGE[k] for k in ("origine", "copie_le", "corpus")},
        "fiche_erreur": FICHE_ERREUR,
        "illisible": illisible,
        "tarif_source": "la table de tarifs de l'application (Réglages → "
                        "Tarifs et budget, pricing.json)",
    }


def devis(voulues: list, limite: int = 0) -> dict:
    """CE QUE CETTE DEMANDE FERAIT, ET CE QU'ELLE COÛTERAIT AU PIRE — sans
    rien dépenser.

    Le pire cas est l'échelle complète × les cases visées : 19,12 $ pour la
    série entière, soit 3,19 fois le plafond. La campagne est donc
    MULTI-SESSION par construction, et le devis le DIT plutôt que de laisser
    l'utilisateur le découvrir au troisième « plafond atteint »."""
    m, _ = manifeste_lire()
    cibles = [c for c in (voulues or serie_cases()) if c not in m["cases"]]
    if limite:
        cibles = cibles[:limite]
    echelle = cout_echelle_usd()
    depense = round(float(m.get("depense_totale_usd") or 0.0), 4)
    reste = round(max(0.0, SERIE_PLAFOND_USD - depense), 4)
    ouvrables = int(reste / echelle) if echelle > 0 else 0
    return {
        "cases_manquantes": len(cibles),
        "echelle_usd": echelle,
        "pire_cas_usd": round(len(cibles) * echelle, 4),
        "depense_courante_usd": depense,
        "plafond_usd": SERIE_PLAFOND_USD,
        "reste_usd": reste,
        "cases_ouvrables": ouvrables,
        "multi_session": len(cibles) > ouvrables,
        "prix": serie_prix(), "devise": "USD",
        "detail_echelle": {"flux": {"n": SERIE_CANDIDATS,
                                    "usd": prix_usd(SERIE_ECHELLE[0],
                                                    SERIE_CANDIDATS)},
                           SERIE_ECHELLE[1]: {"n": 1,
                                              "usd": prix_usd(SERIE_ECHELLE[1], 1)},
                           SERIE_ECHELLE[2]: {"n": 1,
                                              "usd": prix_usd(SERIE_ECHELLE[2], 1)}},
    }


@router.post("/serie/generer")
async def serie_generer(did: str, body: dict | None = None,
                        cases: str | None = None, limite: str | None = None):
    """LA CAMPAGNE. Elle DÉPENSE — c'est la seule route de cette pièce qui le
    fasse — et elle s'arrête au plafond avec son bilan, reprenable.

    ELLE EXIGE UNE CONFIRMATION EXPLICITE (`{"confirmer": true}`), et sans
    elle rend le DEVIS. Ce n'est pas de la cérémonie : pendant la ronde, une
    sonde a émis 436 requêtes vers le fournisseur (toutes refusées à
    l'authentification — la clé du banc était neutralisée, zéro centime), et
    ce qui les a déclenchées est un POST NU sur cette route. Une porte par
    laquelle sortent 19 $ ne s'ouvre pas en la poussant du coude.

    NOTE POUR T5 : le prix de chaque tir est relu dans `pricing.load()` À
    CHAQUE APPEL (la table est la fusion des défauts et du `pricing.json` de
    l'utilisateur, éditable pendant que la campagne tourne). Le mur se libelle
    donc dans la monnaie du MOMENT : re-vérifier la table avant de relancer
    une session, et lire `echelle_usd` du bilan pour savoir ce qu'une case
    coûte au pire ce jour-là.

    Les paramètres sont des CHAÎNES et non des entiers typés : un
    `?limite=abc` doit rendre un refus FRANÇAIS qui dit ce qu'on attend, pas
    le 422 d'un validateur de schéma."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    from .contract import deck_dir
    if not deck_dir(did).is_dir():
        raise HTTPException(404, "Jeu introuvable")
    try:
        voulues = _cases_demandees(cases)
        n = _limite_demandee(limite)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if FICHE_ERREUR:                                      # pragma: no cover
        raise HTTPException(
            409, "La fiche de style est illisible (" + FICHE_ERREUR + ") : "
                 "aucune campagne ne peut être lancée sans ses bornes")
    if (body or {}).get("confirmer") is not True:
        d = devis(voulues, n)
        raise HTTPException(400, detail={
            "erreur": "confirmation requise",
            # LA PHRASE DIT L'ENVELOPPE, PAS UNE SESSION. `devis()` relit
            # `depense_totale_usd` DU MANIFESTE SUR DISQUE : le mur tient d'un
            # POST à l'autre (épinglé par le test du plafond dur). Écrire
            # « par session » promettait une remise à zéro qui n'existe pas —
            # sur une route qui dépense, c'était une invitation à relancer.
            "message": ("Cette campagne DÉPENSE. Elle vise "
                        + str(d["cases_manquantes"]) + " case(s), soit au pire "
                        + _usd(d["pire_cas_usd"]) + " $ sur une ENVELOPPE "
                        "TOTALE de " + _usd(d["plafond_usd"]) + " $ (il reste "
                        + _usd(d["reste_usd"]) + " $, de quoi ouvrir "
                        + str(d["cases_ouvrables"]) + " case(s)). L'enveloppe "
                        "est CUMULATIVE : chaque lancement reprend la dépense "
                        "déjà journalisée, elle ne se remet jamais à zéro. "
                        "Renvoyez la MÊME requête avec {\"confirmer\": true} "
                        "pour la lancer."),
            "devis": d,
        })

    async def _faire():
        return await campagne(voulues, n)

    try:
        info, mien = await _coalesce(SERIE_ID, _faire)
    except HTTPException:
        raise
    except Exception as e:                                # pragma: no cover
        logger.warning(f"cardforge/serie : campagne interrompue : "
                       f"{_sans_chemin(e)}")
        raise HTTPException(
            409, "La campagne s'est interrompue : " + _sans_chemin(e, 180))
    out = dict(info)
    out["coalesce"] = not mien
    if not mien:
        out["message"] = ("une campagne était déjà en vol sur cette série : "
                          "ce bilan est le sien — " + str(out.get("message")))
    return out
