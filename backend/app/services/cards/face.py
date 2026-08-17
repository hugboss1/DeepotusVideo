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

import math
import struct
import zlib

from fastapi import APIRouter, HTTPException, Request, Response

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
        erreur = str(e)[:200]
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
