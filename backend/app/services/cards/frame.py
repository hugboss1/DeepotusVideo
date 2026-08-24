# -*- coding: utf-8 -*-
"""Card Forge — P2 « Bordures et cadres ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/frame`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P2. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8). Ce dont il a besoin vient de
`cards/contract.py` (géométrie, `deck_dir`) et de `cards/core.py` (lecture du
document) — jamais d'un voisin.

CE QU'IL NE FAIT PAS, ET POURQUOI
---------------------------------
Il ne DESSINE rien. Le cadre est tracé par `js/mod-frame.js` dans le moteur
unique de `core.js`, à `geom.canvas_px` — c'est-à-dire dans le fichier livré
lui-même. Un second dessinateur ici, ce serait le bug WYSIWYG que ce dépôt a
déjà payé (`test_export_wysiwyg.py`, risque 2 de la spec) : l'écran et le PDF
divergeraient sans que rien ne le dise. Le backend tient donc deux choses, et
seulement deux :

  * `/catalog` — LE CATALOGUE, miroir mot pour mot du bloc
    `CF-FRAME-CATALOG` de `js/mod-frame.js`. `test_cards_frame.py` EXTRAIT ce
    bloc du JavaScript et le compare à celui-ci, identifiants ET libellés :
    deux listes qui dérivent en silence, c'est un menu qui propose un cadre
    que le backend ne connaît pas.
  * `/metrics` — la conversion des millimètres du cadre en PIXELS DE TOILE,
    par la seule règle du domaine (`contract.px` / `MM_PER_INCH`). L'écran
    calcule les mêmes valeurs et les confronte à celles-ci à chaque
    changement : même doctrine que `verifyGeom` pour la géométrie. Un filet de
    0,9 mm doit faire le même nombre de pixels des deux côtés, sinon
    l'épaisseur affichée dans l'interface n'est pas celle qui part chez
    l'imprimeur.
  * `/occupancy` — LE MODÈLE D'OCCUPATION. Chaque meuble du cadre (bandeau de
    rareté, gemme, plaque, logements de statistiques, socles) est une BOÎTE
    RÉSERVÉE en millimètres depuis la coupe ; les mentions de `doc.type.slots`
    (pièce 03) en sont d'autres. Le module résout les recouvrements au tracé
    et le reste est COMPTÉ. Sans ce compteur, chaque nouvelle famille de cadre
    est une occasion de recouvrir en silence le nom de l'artiste.
  * `/stamp` — LE CHUNK `pHYs`. Un PNG sans `pHYs` ne porte PAS ses 300 DPI :
    Photoshop, InDesign ou un imprimeur lui appliquent 72 DPI par défaut et
    lisent une carte de 28,7 x 39,1 cm. Le fichier 300 et le fichier 600 sont
    alors indiscernables en aval. Cette route relit les octets, VÉRIFIE que
    IHDR porte bien `geom.canvas_px`, puis écrit `pHYs` + `tEXt` (format, fond
    perdu, zone sûre, boîtes de coupe). C'est la seule façon d'avoir le droit
    d'écrire « 300 DPI » quelque part.

Aucun corps mal formé ne doit produire un 500 : tout ce qui vient du client
passe par `_len()` qui lève `ValueError`, transformé en 400 nommant la borne.
"""
from __future__ import annotations

import asyncio
import copy
import io
import math
import os
import pathlib
import re
import struct
import uuid
import zlib

from fastapi import APIRouter, HTTPException, Request, Response

from .contract import (FORMATS, MM_PER_INCH, R, deck_dir, geom, is_valid_did,
                       rnd)

router = APIRouter()

# ═════════════════════════════════════════════════════════════════════════════
# LE CATALOGUE — miroir du bloc CF-FRAME-CATALOG de js/mod-frame.js.
# 8 familles x 6 raretés = 48 combinaisons vectorielles (la barre Clash of
# Decks en sert TROIS, en PNG 638x1004, soit 255 DPI au format poker).
# ═════════════════════════════════════════════════════════════════════════════
FAMILIES = [
    {"id": "runic", "label": "Runique",
     "hint": "gravure fine, équerres, tirets runiques"},
    {"id": "arcane", "label": "Arcane",
     "hint": "volutes, fenêtre en arc, filigrane"},
    {"id": "timber", "label": "Bois sculpté",
     "hint": "veines, rivets, bande épaisse"},
    {"id": "deco", "label": "Art déco",
     "hint": "chevrons étagés, éventails, coins coupés"},
    {"id": "neon", "label": "Néon",
     "hint": "double trait lumineux, coins coupés"},
    {"id": "sable", "label": "Épure",
     "hint": "un seul filet, grande marge, rien d'autre"},
    {"id": "gravure", "label": "Gravure",
     "hint": "marge ivoire, aplat de pochoir décalé, repères"},
    # LA HUITIÈME (phase 4, spec §7.2 — l'anatomie du Patriarche) : le
    # filigrane d'orfèvre. L'IDENTIFIANT est `filigrane` et non
    # « filigrane-instrument » : les trois tables JS-seules (FAM_FN,
    # WIN_SHAPE, PROFILE) sont des objets littéraux dont les tests lisent les
    # clés en `\w+` — un trait d'union casserait les trois lectures. Le NOM
    # de la spec, lui, est dans le libellé.
    {"id": "filigrane", "label": "Filigrane à instruments",
     "hint": "double filet 2,1/3,2 mm, instruments de coin, médaillons"},
]

# ═════════════════════════════════════════════════════════════════════════════
# LES TRAITS MESURÉS DE CHAQUE FAMILLE (phase 4, D6) — miroir du bloc
# CF-FRAME-CATALOG de js/mod-frame.js, et miroir d'EXÉCUTION : `test_cards_
# frame.py` ne compare pas deux textes, il fait tourner les deux sources sur
# un banc de mesures et exige le même choix et la même phrase.
#
# À QUOI ILS SERVENT : « adopter la bordure » (§7.1.5) choisit la famille LA
# PLUS PROCHE d'une bordure MESURÉE sur une carte importée. Sans table de
# traits, « le plus proche » n'a pas de sens.
#
# MESURÉS PAR LA VOIE DE PRODUCTION, ET C'EST UNE CORRECTION DE RONDE. La
# première table mesurait l'ÉPAISSEUR TYPIQUE de la marque de chaque famille.
# Grandeur honnête, et sans rapport avec ce qui entre par la frontière :
# `doc.capture.border.mm` est la PROFONDEUR DU PREMIER FRONT depuis le bord.
# Deux grandeurs sous un même nom — et l'aller-retour P10 -> P2 ne se
# reconnaissait que 2 fois sur 8. La table est donc mesurée en rendant chaque
# famille (poker 300 DPI, `DEFAULTS`, rareté « rare », cellules de 0,1 mm,
# l'ordre de `paintFront` : corps, signature, moulure, plaque — le GRAIN de
# `matter()` exclu, un rastériseur de contrôle ne sait pas le représenter et
# le détecteur de front relève son plancher avec le bruit) puis en passant les
# octets dans les analyseurs de la PIÈCE 10 eux-mêmes :
#   · front_mm = `_analyse_bordure(...)["mm"]` — la profondeur du premier
#     front, exactement l'unité qui arrivera par `doc.capture.border.mm` ;
#   · teinte_h = la teinte du `_couleur_bande` publié, lu sur le HEXA (donc
#     arrondi 8 bits, la seule forme que la frontière peut porter — le flottant
#     du banc donnait 55,4° pour Gravure là où la voie réelle donne 51,4°, et
#     ces 4 degrés lui faisaient perdre sa propre famille).
#
# CE QUE LA TABLE AVOUE, ET QUE LA GÉOMÉTRIE IMPOSE. Sept familles sur huit
# rendent un front de 0,90 mm : ce n'est pas leur dessin, c'est la LÈVRE DE
# RELIEF que `ringZone` pose à 1,2 mm de la coupe et qui occupe [0,92 ; 1,48].
# Seule « Néon » en diffère (3,20 mm) — sa zone est « vide », `ringZone` sort
# avant la lèvre, et son premier front est le halo du biseau. L'axe du front
# ne sépare donc QUE Néon. La teinte, elle, ne sépare que le CHAUD du FROID :
# cinq familles (Runique, Arcane, Bois, Art déco, Épure) tirent leur anneau de
# `PAL`, dont la teinte appartient à la RARETÉ, et tiennent dans 0,8 degré ;
# trois d'entre elles rendent la MÊME couleur au bit près (#08121d).
# CONSÉQUENCE ASSUMÉE : Arcane et Art déco ne peuvent pas se reconnaître —
# elles tombent sur Runique, la première du groupe, et la PHRASE avoue la
# quasi-égalité. Six familles sur huit se reconnaissent (test d'aller-retour).
# Prétendre mieux serait prétendre une mesure que le dessin ne porte pas.
# ═════════════════════════════════════════════════════════════════════════════
FAMILY_TRAITS = {
    "runic": {"front_mm": 0.9, "teinte_h": 211.4},
    "arcane": {"front_mm": 0.9, "teinte_h": 211.4},
    "timber": {"front_mm": 0.9, "teinte_h": 211.5},
    "deco": {"front_mm": 0.9, "teinte_h": 211.4},
    "neon": {"front_mm": 3.2, "teinte_h": 211.2},
    "sable": {"front_mm": 0.9, "teinte_h": 210.7},
    "gravure": {"front_mm": 0.9, "teinte_h": 51.4},
    "filigrane": {"front_mm": 0.9, "teinte_h": 42.1},
}
# L'ÉGALITÉ QU'ON AVOUE. Deux familles à moins de ce dixième de largeur de
# catalogue l'une de l'autre ne sont pas départageables par la mesure : la
# phrase le DIT au lieu de laisser croire à une reconnaissance.
PROCHE_EPS = 0.02
RARITIES = [
    {"id": "common", "label": "Commune"},
    {"id": "uncommon", "label": "Peu commune"},
    {"id": "rare", "label": "Rare"},
    {"id": "epic", "label": "Épique"},
    {"id": "legendary", "label": "Légendaire"},
    {"id": "mythic", "label": "Mythique"},
]
BACKS = [
    {"id": "mirror", "label": "Miroir du recto"},
    {"id": "lattice", "label": "Treillis"},
    {"id": "guilloche", "label": "Guilloché"},
    {"id": "sunburst", "label": "Soleil"},
    {"id": "scales", "label": "Écailles"},
    {"id": "chevron", "label": "Chevrons"},
    {"id": "runes", "label": "Runes"},
    # LE VERSO PERSONNALISÉ (spec §6.2ter) — pas un motif de plus : le dos
    # devient une IMAGE importée plus une pile de calques. Il arrive EN
    # DERNIER pour que les sept motifs gardent leur rang (`card.back` et les
    # sept habillages en portent déjà les identifiants).
    {"id": "custom", "label": "Personnalisé"},
]
# Les modes de fusion d'un calque de verso — CEUX QUI EMPILENT, et rien
# d'autre (§6.2ter). Le `multiply` n'est pas demandé au compositeur : il est
# PRÉCOMPOSÉ dans les pixels du calque au moment du rendu, sans quoi la
# couche « cadre » du rendu par couches cesserait d'être isolée (§4.2).
BACK_BLENDS = [
    {"id": "normal", "label": "Normal"},
    {"id": "multiply", "label": "Multiplier"},
]
CORNERS = [
    {"id": "none", "label": "Aucun"},
    {"id": "bracket", "label": "Équerre"},
    {"id": "scroll", "label": "Volute"},
    {"id": "stud", "label": "Rivet"},
    {"id": "fleuron", "label": "Fleuron"},
    {"id": "spike", "label": "Pointe"},
]
# LE SCEAU PRISMATIQUE (spec §6.2bis) — pas un archétype de mise en page : un
# CONTOUR holographique combinable avec tout archétype. Deux recettes, les
# mêmes que le matériau 3D de la phase 2b (argent / dorure).
SEAL_KINDS = [
    {"id": "argent", "label": "Argent holographique"},
    {"id": "dorure", "label": "Dorure holographique"},
]
METALS = [
    {"id": "gold", "label": "Or"},
    {"id": "silver", "label": "Argent"},
    {"id": "copper", "label": "Cuivre"},
    {"id": "steel", "label": "Acier"},
    {"id": "rose", "label": "Or rose"},
]
PRESETS = [
    {"id": "sobre", "label": "Runique sobre"},
    {"id": "heroique", "label": "Arcane légendaire"},
    {"id": "cyber", "label": "Néon épique"},
    {"id": "taverne", "label": "Bois commun"},
    {"id": "musee", "label": "Épure rare"},
]

# Bornes des longueurs du cadre, en millimètres. `line_mm` et le rayon de
# fenêtre vont de 0 à 8 mm : c'est le seuil chiffré de la pièce 02.
# `edge_mm` s'arrêtait à 6 : un filet de 8 mm ne pouvait alors pas être rentré
# de plus de 6 mm, et la combinaison des deux curseurs était amputée sans
# qu'aucun écran ne le dise. Même borne haute que l'épaisseur.
LIMITS = {
    "line_mm": [0, 8],
    "gap_mm": [0, 4],
    "edge_mm": [0, 8],
    "inner_mm": [0, 20],
    "win_r_mm": [0, 8],
    "corner_mm": [0, 8],
    "plate_alpha": [0, 1],
    "grad_angle": [0, 360],
    "socle_alpha": [0, 1],
    # La LARGEUR DE BANDE du filigrane du Sceau (§6.2bis-d). Le plancher n'est
    # pas un chiffre rond : 0,2 mm est le trait minimal qu'un imprimeur foil
    # accepte (§6.2bis-b, vérifié avant tout export). Le plafond est un choix ;
    # la borne qui MORD vraiment est celle du format, plus bas.
    "seal_width_mm": [0.2, 6],
    # LE VERSO PERSONNALISÉ (§6.2ter) : l'opacité et l'échelle d'un calque.
    # L'échelle part de 0,25 et non de 0 — un calque à l'échelle nulle n'est
    # pas un réglage, c'est un calque qu'on aurait dû éteindre (l'opacité,
    # elle, va jusqu'à 0 : c'est exactement ce qu'elle veut dire).
    "back_opacity": [0, 1],
    "back_scale": [0.25, 4],
    # LE DÉCOR DE CADRE PAR IA (§6.3) : son opacité. Elle va bien jusqu'à 0 —
    # c'est « ne pas le montrer sans le perdre », ce qu'un curseur d'opacité
    # veut dire.
    "decor_alpha": [0, 1],
}

# ── LA BORNE QUE LE FORMAT IMPOSE ────────────────────────────────────────────
# BUG TROUVÉ PAR LE BALAYAGE DES DOUZE FORMATS, mesuré avant correction :
# format `micro` (31,75 x 44,45 mm) et marge intérieure au maximum du curseur
# (20 mm) -> bande = 31,75 - 40 = -8,25 mm, soit -97 px à 300 DPI. Le tracé
# retourne son rectangle, le découpage en anneau n'en est plus un et l'encre
# sort sur toute la toile : cadre entièrement faux, sans une seule exception.
# Les bornes des curseurs sont en millimètres ABSOLUS ; une carte, non.
# La plaque de texte est posée à `band.x + 1,2 mm` et large de `band.w - 2,4` :
# la bande doit garder au moins ces 2,4 mm plus de quoi l'y voir -> 4 mm.
# Sur les douze formats livrés, cette borne ne mord que sur `micro`.
# Bloc JUMEAU de `bandMaxMM` dans mod-frame.js, comparé par le test.
BAND_MIN_MM = 4


def band_max_mm(tw: float, th: float) -> float:
    v = min(float(tw or 0), float(th or 0)) / 2 - BAND_MIN_MM / 2
    return rnd(v, 2) if v > 0 else 0.0


DEFAULTS = {
    "line_mm": 0.9, "gap_mm": 1.1, "edge_mm": 1.6, "inner_mm": 5.5,
}


# ── « ADOPTER LA BORDURE » : LE CALCUL, jumeau de mod-frame.js ───────────────
# Ces quatre fonctions sont un MIROIR D'EXÉCUTION du bloc CF-FRAME-CATALOG :
# le test fait tourner les deux sources sur un banc de mesures et exige le
# même choix ET la même phrase. Une table recopiée peut dériver en silence ;
# deux calculs qui rendent le même résultat sur un banc, non.
#
# LE MODULO DE JAVASCRIPT N'EST PAS CELUI DE PYTHON. `-1 % 6` vaut -1 en JS et
# 5 ici : la formule de teinte passe par une valeur négative dès que le bleu
# domine, et les deux langages rendraient alors deux teintes différentes pour
# la MÊME couleur. `math.fmod` a le signe du dividende, comme JS — c'est lui
# qu'on emploie partout où le JS écrit `%`.
def _fmod_js(a: float, b: float) -> float:
    return math.fmod(a, b)


# ── LE SEUIL DE SATURATION, ET POURQUOI L'ÉGALITÉ EXACTE NE SUFFIT PAS ──────
# Premier jet : « un gris n'a pas de teinte » gardé par `max == min`. MESURÉ
# par la ronde : `#6a6b6c` rend « teinte à 1° » et choisit Arcane, `#6c6b6a`
# rend « teinte à 12° » et choisit Filigrane — deux gris que personne ne
# distingue, deux familles opposées. Le gris EXACT est un événement de mesure
# nulle : la couleur qui arrive vient d'une quantification median-cut sur une
# photo, elle n'est jamais exactement neutre.
# DEUX SEUILS, ET LE SECOND EST NÉ D'UN ÉCHEC DE BANC. Le premier jet n'avait
# que la saturation HSV. Le banc l'a démentie tout de suite : `#141516` est un
# gris à UN LSB près, et sa saturation vaut 0,091 — trois fois le seuil. Une
# saturation est RELATIVE au maximum ; dans les tons sombres, deux unités de
# bruit pèsent autant qu'un vrai écart dans les tons clairs. Il faut donc :
#   · CHROMA_MIN, un plancher ABSOLU (max − min en unités 8 bits) — le bruit
#     de quantification, lui, est absolu : 2 unités quel que soit le ton ;
#   · SAT_MIN, un plancher RELATIF — un presque-blanc à 6 unités de chroma a
#     une teinte réelle mais illisible, et n'a rien à décider.
# MESURÉS (test « le seuil de saturation tombe dans le creux ») : les gris à
# 1 LSB donnent chroma 2 et saturation ≤ 0,091 ; la dominante la moins saturée
# que la voie de production rende vraiment est l'ivoire de « Gravure », chroma
# 7 et saturation 0,041. Les seuils se posent entre les deux populations.
# LA MARGE EST MINCE — 2,5x au-dessus du bruit, 1,4x sous l'ivoire — et c'est
# écrit plutôt que caché : l'ivoire de « Gravure » est la teinte la moins
# certaine des huit, et le test rougit avant l'utilisateur si son anneau
# change. Jumeaux de `SAT_MIN` / `CHROMA_MIN` de js/mod-frame.js.
SAT_MIN = 0.03
CHROMA_MIN = 5


def _rgb_de(hexa):
    """(r, g, b) d'un « #rrggbb » ou « #rgb », ou None. `replace` remplace
    TOUTES les occurrences ici comme en JS (`replaceAll`) : sans cela
    « ##d8b76a » traversait d'un côté et pas de l'autre."""
    s = str(hexa if hexa is not None else "").strip().replace("#", "")
    if not re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", s):
        return None
    if len(s) == 3:
        s = s[0] * 2 + s[1] * 2 + s[2] * 2
    n = int(s, 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def saturation_de(hexa) -> float | None:
    """La saturation HSV — (max − min) / max. None si la couleur n'est pas
    lisible ; 0 pour un noir pur (dont la teinte ne veut rien dire non plus)."""
    c = _rgb_de(hexa)
    if c is None:
        return None
    mx, mn = max(c), min(c)
    return 0.0 if mx == 0 else (mx - mn) / float(mx)


def teinte_de(hexa) -> float | None:
    """La teinte d'un « #rrggbb », en DEGRÉS — ou None quand elle ne veut rien
    dire : couleur illisible, ou saturation sous `SAT_MIN`.

    Un gris n'a pas de teinte : lui en inventer une (0 = rouge) ferait choisir
    une famille chaude pour une bordure d'acier."""
    c = _rgb_de(hexa)
    if c is None:
        return None
    r, g, b = c
    mx, mn = max(c), min(c)
    d = mx - mn
    if d < CHROMA_MIN or (mx and d / float(mx) < SAT_MIN):
        return None
    if mx == r:
        h = _fmod_js((g - b) / d, 6.0)
    elif mx == g:
        h = (b - r) / d + 2.0
    else:
        h = (r - g) / d + 4.0
    h *= 60.0
    return _fmod_js(_fmod_js(h, 360.0) + 360.0, 360.0)


def ecart_teinte(a: float, b: float) -> float:
    """L'écart de deux teintes est CIRCULAIRE : 350 et 10 sont à 20 degrés
    l'un de l'autre, pas à 340."""
    d = abs(_fmod_js(_fmod_js(a - b, 360.0) + 360.0, 360.0))
    return 360.0 - d if d > 180.0 else d


def traits_echelles() -> dict:
    """Les deux échelles de la distance — MESURÉES SUR LA TABLE, pas choisies.

    Additionner des millimètres et des degrés demande un poids, et un poids
    choisi à la main serait un goût. Chaque axe est divisé par l'ÉTENDUE que
    le catalogue occupe sur cet axe : un écart d'une largeur-de-catalogue en
    front pèse alors exactement autant qu'un écart d'une largeur-de-catalogue
    en teinte. (Aux huit familles livrées : front 2,30 mm, teinte 169,4°.)

    L'étendue de teinte est le MAXIMUM des distances CIRCULAIRES par paires,
    et non max−min : sur un cercle, « l'étendue » d'un nuage n'est pas une
    différence de coordonnées. Elle sature à 180° — deux familles diamétrale-
    ment opposées donnent la plus grande étendue possible, et c'est juste."""
    fronts, teintes = [], []
    for fa in FAMILIES:
        t = FAMILY_TRAITS.get(fa["id"])
        if not t:
            continue
        fronts.append(t["front_mm"])
        if t["teinte_h"] is not None:
            teintes.append(t["teinte_h"])
    h_max = 0.0
    for i in range(len(teintes)):
        for j in range(i + 1, len(teintes)):
            h_max = max(h_max, ecart_teinte(teintes[i], teintes[j]))
    b = (max(fronts) - min(fronts)) if fronts else 0.0
    return {"front": b if b > 0 else 1.0, "teinte": h_max if h_max > 0 else 1.0}


def _ecart_axe_teinte(mesure, trait, echelle: float) -> float:
    """L'axe de teinte quand l'une des deux teintes N'EXISTE PAS.

    « Pas de teinte » n'est pas « teinte inconnue » : c'est une VALEUR — la
    couleur est neutre. Deux neutres se ressemblent (écart nul) ; un or et un
    gris ne se ressemblent pas du tout (écart maximal, une largeur de
    catalogue). Rendre 0 dans tous les cas ferait gagner d'office toute
    famille sans teinte, quelle que soit la couleur importée."""
    if mesure is None and trait is None:
        return 0.0
    if mesure is None or trait is None:
        return 1.0
    return ecart_teinte(float(mesure), float(trait)) / echelle


def famille_proche(front_mm: float, teinte_h) -> dict | None:
    """La famille la plus proche d'une bordure mesurée. En cas d'égalité,
    l'ORDRE DU CATALOGUE tranche (le `<` est strict) — la même règle des deux
    côtés, sinon deux égalités parfaites rendraient deux familles.

    Rend AUSSI les VOISINES : celles qui tombent à moins de `PROCHE_EPS` du
    choix. Le catalogue en porte de vraies (Arcane et Art déco rendent le même
    front et la même couleur au bit près que Runique) et l'écart affiché doit
    le dire — sinon l'écran annonce une reconnaissance là où il a tiré au
    sort."""
    e = traits_echelles()
    best = None
    tous = []
    for fa in FAMILIES:
        fid = fa["id"]
        t = FAMILY_TRAITS.get(fid)
        if not t:
            continue
        db = abs(float(front_mm) - t["front_mm"]) / e["front"]
        dh = _ecart_axe_teinte(teinte_h, t["teinte_h"], e["teinte"])
        d = db + dh
        tous.append((fid, d, db, dh))
        if best is None or d < best["d"] - 1e-12:
            best = {"id": fid, "d": d, "d_front": db, "d_teinte": dh}
    if best is None:
        return None
    best["voisines"] = [fid for fid, d, _b, _h in tous
                        if fid != best["id"] and d <= best["d"] + PROCHE_EPS]
    return best


def _mm1(v) -> str:
    """Un millimètre écrit à une décimale, virgule française. `Math.round` de
    JS arrondit vers +∞ à la demie (2,5 -> 3) ; `round()` de Python arrondit
    au pair (2,5 -> 2). On écrit donc l'arrondi de JS, à la main."""
    n = math.floor(float(v) * 10 + 0.5)
    return f"{n / 10:.1f}".replace(".", ",")


def _label_de(fid) -> str:
    for fa in FAMILIES:
        if fa["id"] == fid:
            return fa["label"]
    return str(fid)


def phrase_ecart(front_mm: float, teinte_h, choix) -> str:
    """L'ÉCART AVOUÉ (§7.1.5, §9.1). Chaque chiffre de cette phrase est celui
    du calcul, au même arrondi : le test les recalcule un à un et reconstruit
    la phrase entière. L'unité d'un écart de teinte est le DEGRÉ — la spec
    l'écrivait en « % » et l'orchestrateur l'a amendée en ce sens le 24/08
    (spec :510, commit 9f030be).

    `choix` est le relevé de `famille_proche` — ou un simple identifiant quand
    l'appelant n'a pas besoin des voisines. LE MOT « bande » RESTE : c'est
    celui de la spec et celui du curseur qui reçoit la mesure ; et des deux
    côtés de la flèche il désigne bien la MÊME grandeur, la profondeur du
    premier front."""
    if isinstance(choix, dict):
        fid = choix.get("id")
        voisines = list(choix.get("voisines") or [])
    else:
        fid, voisines = choix, []
    t = FAMILY_TRAITS.get(fid)
    if not t:
        return f"famille inconnue : {fid}"
    p = (f"bande {_mm1(front_mm)} mm ↔ {_label_de(fid)} "
         f"{_mm1(t['front_mm'])} mm")
    ht = t["teinte_h"]
    if teinte_h is None and ht is None:
        p += ", ni la mesure ni la famille n'a de teinte"
    elif teinte_h is None:
        p += ", teinte de la mesure non mesurable (gris)"
    elif ht is None:
        p += ", la famille n'a pas de teinte propre"
    else:
        ec = math.floor(ecart_teinte(float(teinte_h), ht) + 0.5)
        p += f", teinte à {ec}°"
    if voisines:
        s = "s" if len(voisines) > 1 else ""
        noms = ", ".join(_label_de(v) for v in voisines)
        p += (f" — {len(voisines)} famille{s} voisine{s} à moins de "
              f"{_mm1(PROCHE_EPS * 100)} % ({noms}) : le catalogue retient "
              f"la première")
    return p

# ── LE SCEAU : SCHÉMA ET BORNE, jumeau du bloc de mod-frame.js ───────────────
# `doc.frame.seal` est le PREMIER sous-objet de `doc.frame` (les 28 autres clés
# sont plates). Le backend ne le DESSINE pas — il n'en tient que la
# normalisation et les millimètres, exactement comme pour la fenêtre : c'est de
# ces nombres-là que dériveront le masque d'imprimeur (P7) et la texture 3D
# (P9), jamais d'un PNG repassé de l'un à l'autre (« le piège des deux
# cadres », spec §6.2bis).
#
# LA BORNE DU SCEAU. L'anneau épouse `m.outer` (la coupe rentrée de `edge_mm`)
# et creuse vers l'intérieur sur `width_mm`. Deux choses le bornent, et aucune
# n'est un millimètre absolu :
#   1. LA FENÊTRE — au-delà, l'anneau n'est plus un contour, c'est une plaque
#      posée sur l'illustration ;
#   2. LE FORMAT — comme la bande, l'anneau s'INVERSE si sa largeur passe la
#      demi-carte (le défaut mesuré sur `micro`, voir BAND_MIN_MM).
# `SEAL_MIN_MM` est le trait minimal d'un imprimeur foil (§6.2bis-b), et il
# s'applique AU RÉSULTAT, pas seulement au curseur : une fenêtre posée à
# 1,61 mm de la coupe ne laisse que 0,01 mm, et publier cette largeur-là
# ferait dessiner à l'écran ce que le préflight de la presse refuse. Sous le
# plancher, PAS D'ANNEAU (0.0) — et la ligne d'état de l'écran le dit.
SEAL_MIN_MM = 0.2

SEAL_DEFAULTS = {
    "on": False, "kind": "argent", "width_mm": 1.2,
    "scope": {"screen": True, "print": False, "mesh": False},
}


def seal_max_mm(tw: float, th: float, edge_mm: float, win: dict) -> float:
    e = float(edge_mm or 0)
    W, H = float(tw or 0), float(th or 0)
    w = win if isinstance(win, dict) else {"x": 0, "y": 0, "w": W, "h": H}
    fen = min(w["x"], w["y"], W - (w["x"] + w["w"]), H - (w["y"] + w["h"])) - e
    carte = (min(W, H) - 2 * e - SEAL_MIN_MM) / 2
    v = min(fen, carte)
    # la comparaison porte sur la valeur NON ARRONDIE : 0,196 mm s'arrondirait
    # à 0,20 et publierait une largeur que la place ne porte pas.
    return rnd(v, 2) if v >= SEAL_MIN_MM else 0.0


def seal_of(raw) -> dict:
    """Le Sceau, NORMALISÉ — miroir d'exécution de `sealOf()` de mod-frame.js.

    Rend toujours un dictionnaire NEUF et complet : un corps absent repart des
    défauts, un booléen qui n'en est pas retombe au défaut, une largeur hors
    bornes lève `ValueError` (transformée en 400 nommant la borne). La borne de
    FORMAT ne s'applique pas ici — elle demande une géométrie, et tombe au
    calcul des métriques, comme `min(edge_mm, cap)`."""
    s = raw if isinstance(raw, dict) else {}
    sc = s.get("scope")
    sc = sc if isinstance(sc, dict) else {}

    def b(v, d):
        return v if isinstance(v, bool) else d

    kinds = [k["id"] for k in SEAL_KINDS]
    kind = s.get("kind")
    return {
        "on": b(s.get("on"), SEAL_DEFAULTS["on"]),
        "kind": kind if kind in kinds else SEAL_DEFAULTS["kind"],
        "width_mm": _len(s.get("width_mm"), SEAL_DEFAULTS["width_mm"],
                         LIMITS["seal_width_mm"][0], LIMITS["seal_width_mm"][1],
                         "La largeur de bande du Sceau"),
        "scope": {k: b(sc.get(k), v)
                  for k, v in SEAL_DEFAULTS["scope"].items()},
    }


# ── LE VERSO PERSONNALISÉ : SCHÉMA ET MOTIFS, jumeau du bloc de mod-frame.js ─
# `doc.frame.back_image` (une image de fond) et `doc.frame.back_layers` (la
# PREMIÈRE pile ordonnée de P2 — tout le reste y est booléen ou énuméré).
#
# `BACK_SRC_RE` est le motif du VOCABULAIRE (ce qu'un document a le droit de
# nommer), `BACK_IMG_NAME_RE` celui de la ROUTE (ce qu'un GET a le droit de
# demander). Les deux sont EXACTS, et pour la même raison : ces noms ne
# viennent pas de l'utilisateur, ils sont FABRIQUÉS par le compteur d'imports.
# Un motif permissif ouvrirait `decks/{did}/frame/` — qui n'a aujourd'hui que
# des `img_N.png`, mais rien ne garantit qu'il n'aura pas d'état interne
# demain, et cette porte ne doit pas s'élargir avec lui.
BACK_SRC_RE = re.compile(r"(|img:img_\d+\.png)")
BACK_IMG_NAME_RE = re.compile(r"img_\d+\.png")
# LA FORME D'UN NOMBRE ÉCRIT EN CHAÎNE. `float()` et `Number()` ne lisent pas
# les mêmes chaînes, et l'écart n'est pas théorique — MESURÉ sur les deux
# normaliseurs : « 0x10 » vaut 16 en JavaScript et LÈVE ici ; « 1_0 » vaut 10
# ici et NaN en JavaScript. Après bornage, cela fait 4 d'un côté contre 1 de
# l'autre : le même document rendu différemment à l'écran et au backend. Un
# jeu édité à la main suffit à les produire. On n'accepte donc QUE la forme que
# les deux langages lisent identiquement. Jumeau de `BACK_NUM_RE` de
# mod-frame.js.
BACK_NUM_RE = re.compile(r"-?\d+(\.\d+)?")
BACK_LAYERS_MAX = 6          # spec §6.2ter, plan 3c décision 5
BACK_IMAGES_MAX = 8          # images de verso par jeu (plan 3c décision 5)
BACK_LAYER_DEFAULTS = {"src": "", "opacity": 1.0, "scale": 1.0,
                       "blend": "normal"}
DEFAULTS_BACK = {"back_image": "", "back_layers": []}

# Les plafonds d'IMPORT, RECOPIÉS et non importés : la règle 8 interdit à une
# pièce d'importer le module d'une voisine, et `cards/type.py` porte les mêmes
# chiffres pour sa propre porte. Le test de parité épingle les deux.
IMG_MAX_BYTES = 64 * 1024 * 1024      # pesé AVANT tout décodage
IMG_MAX_PIXELS = 32 * 1024 * 1024     # la TRAME, lue dans l'EN-TÊTE
MAX_IMPORT_PX = 4096                  # côté long au-delà duquel on réduit


def back_image_of(raw) -> str:
    """L'image de fond du verso, NORMALISÉE — miroir d'exécution de
    `backImageOf()` de mod-frame.js.

    `fullmatch` et non `match` : le `$` d'un motif accepte un saut de ligne
    final, et « img:img_1.png\\n » traverserait. Ce dépôt a payé ce piège
    trois fois (3b-T2, 3c-T3) ; il ne se rejoue pas ici.

    CE MIROIR NORMALISE, IL NE REFUSE PAS — et c'est une différence VOULUE
    avec `seal_of`. `/metrics` REÇOIT un sceau dans un corps de requête, donc
    une valeur folle y mérite un 400 qui nomme la borne. AUCUNE route ne
    reçoit `back_image` / `back_layers` : ces clés ne vivent que dans le
    document, où la doctrine est celle de `st()` — on RÉPARE ce qu'on
    possède."""
    s = raw if isinstance(raw, str) else ""
    return s if BACK_SRC_RE.fullmatch(s) else ""


def _borne(v, defaut: float, lo: float, hi: float) -> float:
    """Une longueur de calque, RAMENÉE dans ses bornes (jamais refusée).

    L'ADMISSION EST ÉCRITE, elle n'est pas déléguée à `float()` : un nombre,
    un booléen, ou une chaîne de la forme que les DEUX langages lisent pareil
    (`BACK_NUM_RE`). `None`, `""`, une liste, « 0x10 » ou « 1_0 » valent
    ABSENT — jamais zéro, jamais un nombre que l'écran lirait autrement."""
    if isinstance(v, bool):          # AVANT `int` : `isinstance(True, int)`
        n = 1.0 if v else 0.0
    elif isinstance(v, (int, float)):
        n = float(v)
    elif isinstance(v, str) and BACK_NUM_RE.fullmatch(v):
        n = float(v)
    else:
        return float(defaut)
    if not math.isfinite(n):
        return float(defaut)
    return float(lo) if n < lo else (float(hi) if n > hi else n)


def back_layers_of(raw) -> list:
    """La pile de calques du verso, NORMALISÉE — miroir de `backLayersOf()`.

    Chaque entrée rend un dictionnaire NEUF et COMPLET : le peintre reçoit la
    pile du document telle quelle, un partiel obligerait chaque lecteur à
    connaître les défauts. Ce qui n'est pas un objet est JETÉ (une entrée
    `null` dans une liste ordonnée n'est pas un calque éteint, c'est un
    document abîmé), et la pile est tronquée au plafond."""
    blends = [b["id"] for b in BACK_BLENDS]
    out = []
    for e in (raw if isinstance(raw, list) else []):
        if not isinstance(e, dict):
            continue
        blend = e.get("blend")
        out.append({
            "src": back_image_of(e.get("src")),
            "opacity": _borne(e.get("opacity"), BACK_LAYER_DEFAULTS["opacity"],
                              LIMITS["back_opacity"][0],
                              LIMITS["back_opacity"][1]),
            "scale": _borne(e.get("scale"), BACK_LAYER_DEFAULTS["scale"],
                            LIMITS["back_scale"][0], LIMITS["back_scale"][1]),
            "blend": blend if blend in blends else BACK_LAYER_DEFAULTS["blend"],
        })
        if len(out) >= BACK_LAYERS_MAX:
            break
    return out


# ── LE DÉCOR DE CADRE PAR IA : SCHÉMA, jumeau du bloc de mod-frame.js ────────
# `doc.frame.decor = {src, alpha}` (spec §6.3, plan 3c décision 6). Une image
# GÉNÉRÉE devient le fond de la bande.
#
# LE MAGASIN N'EST PAS CELUI DU VERSO, et c'est la décision 6 : le verso lit
# `decks/{did}/frame/img_N.png` (des octets IMPORTÉS, qui voyagent avec le jeu),
# le décor lit `/api/images/<fichier>` — le magasin d'images de l'APPLICATION,
# celui que `CF.images.generate` remplit. C'est le MÊME générateur que P1 : un
# second magasin pour les mêmes octets ferait deux endroits à ramasser.
#
# Conséquence assumée : ces noms de fichier ne sont pas fabriqués par un
# compteur à nous (le générateur écrit `gen_<hex>.png`, l'import garde le nom
# donné), donc le motif ne peut pas être `img_\d+` comme celui du verso. Il
# borne le JEU DE SIGNES et la longueur, et il est ANCRÉ des deux bouts —
# `fullmatch` et non `match`, le `$` d'un motif Python acceptant un saut de
# ligne final (piège payé trois fois dans ce dépôt). Aucune route ne SERT ce
# fichier ici : il est servi par `/api/images/{filename}`, qui a sa propre
# containment (`Path(name).name`), et ce motif-ci ne fait que borner ce qu'un
# DOCUMENT a le droit de nommer.
DECOR_SRC_RE = re.compile(r"(|img:[A-Za-z0-9][A-Za-z0-9._-]{0,119})")
# `alpha: 1.0` et non une demi-teinte : un décor livré à moitié transparent
# ferait croire à une génération ratée. C'est aussi l'opacité par défaut d'un
# calque de verso, sa clé voisine.
DECOR_DEFAULTS = {"src": "", "alpha": 1.0}


def decor_of(raw) -> dict:
    """Le décor de cadre, NORMALISÉ — miroir d'exécution de `decorOf()` de
    mod-frame.js.

    L'opacité passe par `_borne`, donc par l'admission ÉCRITE (un nombre, un
    booléen, ou une chaîne de la forme que les DEUX langages lisent pareil) :
    `None` et `""` valent ABSENT, jamais zéro. C'est la leçon F3 de la T4,
    appliquée dès la naissance de la clé plutôt que redécouverte.

    Comme `back_image_of`, ce miroir NORMALISE et ne refuse pas : aucune route
    ne reçoit `decor`, cette clé ne vit que dans le document — où la doctrine
    est celle de `st()`, on RÉPARE ce qu'on possède."""
    s = raw if isinstance(raw, dict) else {}
    src = s.get("src")
    if not (isinstance(src, str) and DECOR_SRC_RE.fullmatch(src)):
        src = ""
    return {
        "src": src,
        "alpha": _borne(s.get("alpha"), DECOR_DEFAULTS["alpha"],
                        LIMITS["decor_alpha"][0], LIMITS["decor_alpha"][1]),
    }


# ═════════════════════════════════════════════════════════════════════════════
# LE MODÈLE D'OCCUPATION — les constantes du GABARIT DE MEUBLES
# Bloc EXTRAIT et comparé au bloc jumeau de `js/mod-frame.js` par le test.
# Toutes les longueurs sont en MILLIMÈTRES depuis le coin de COUPE.
# ═════════════════════════════════════════════════════════════════════════════
# ═════ CF-FRAME-OCC-BEGIN ═════
CLEAR_MM = 0.8        # jeu minimal entre un meuble mobile et une mention
BANNER_H_MM = 5.2     # hauteur du bandeau de rareté
BANNER_MIN_H_MM = 3.0  # ... jusqu'où il accepte de maigrir pour tenir
BANNER_CH_MM = 3.4    # largeur réservée par caractère du libellé
BANNER_PAD_CH = 4     # caractères de marge (les deux pointes du ruban)
BANNER_MAX_F = 0.62   # largeur maxi du bandeau, en fraction de la rogne
GEM_R_MM = 4.6        # rayon de la gemme de rareté
GEM_OFF_F = 0.75      # centre de la gemme = marge + 0.75 x rayon
PIP_STEP_MM = 1.5     # pas des crans de rareté à droite de la gemme
PIP_R_MM = 0.5        # rayon d'un cran
SOCLE_PAD_MM = 0.7    # débord du socle autour d'une mention
SEAT_PAD_MM = 0.8     # débord d'un logement de statistique
SEAT_MIN_FRAC = 0.30  # ... au-delà de cette part de la mention DANS l'anneau
SOCLE_MIN_FRAC = 0.05  # ... et de cette part SUR l'illustration
GEM_SEAT_RATIO = 1.6  # au-delà, l'écrin n'est plus un disque mais un cartouche
TOL_MM2 = 0.5         # sous cette surface, un contact n'est pas une collision
TOL_FRAC = 0.02       # ... ni sous cette fraction de la mention
# ═════ CF-FRAME-OCC-END ═════

# ═════════════════════════════════════════════════════════════════════════════
# L'HABILLAGE DES SEPT ARCHÉTYPES — phase 3a, tâche 2 (spec §6.2:318-363)
#
# CE QUE C'EST : pour chacun des sept archétypes, un réglage `doc.frame`
# COMPLET — les 31 clés que l'on écrit, la trente-deuxième (`art_window`)
# étant PUBLIÉE par le painter et jamais saisie. (28 depuis la phase 3c-1 :
# `seal`, le Sceau prismatique, qui reste ÉTEINT dans les sept habillages — un
# archétype qui l'allumerait changerait l'aspect de tous les jeux déjà
# instanciés ; 30 depuis la 3c-4 : `back_image` et `back_layers`, le verso
# personnalisé, VIDES pour la même raison — un archétype qui pointerait un
# fichier pointerait le fichier d'un AUTRE jeu ; 31 depuis la 3c-5 : `decor`,
# le décor de cadre par IA, SANS SOURCE pour cette même raison.) Rien
# d'autre : ni police, ni
# slot, ni palette de texte — ceux-là appartiennent à P3 et au modèle.
#
# QUI LE CONSOMME : la tâche 3 (`models.py`) l'IMPORTE. Un modèle qui
# retaperait ces réglages serait une seconde source de vérité, et la première
# divergence silencieuse serait un deck instancié qui ne ressemble pas à son
# archétype. `test_cards_frame.py` valide la table ici : clés complètes,
# famille/rareté/dos/coin/métal du catalogue, longueurs dans LIMITS, fenêtres
# incluses dans la rogne, et RENDU sans exception par les vrais painters.
#
# COMMENT ILS ONT ÉTÉ CHOISIS (règle de la tâche : la mesure décide) : on a
# d'abord tenté d'habiller chaque archétype avec les familles DÉJÀ LIVRÉES ;
# six y sont arrivés. Un seul ne pouvait pas — « Arcane gravée », qui demande
# une marge de PAPIER IVOIRE (les six familles encrent l'anneau depuis `PAL`,
# dont les six raretés sont sombres) et un aplat de pochoir au REPÉRAGE
# DÉCALÉ de 0,2 mm, que rien ne savait poser. D'où `gravure`, la septième.
#
# Les zones sont celles de la spec, en millimètres depuis le coin de COUPE
# (même origine que les slots P3) ; les fenêtres sont recopiées telles quelles
# de §6.2, et le test les relit sur la fenêtre EFFECTIVE du modèle, pas sur
# cette table relue à elle-même.
#
# CES ZONES SONT CELLES DU FORMAT POKER (63 x 88). Elles ne se transposent pas
# toutes seules — MESURÉ sur les douze formats livrés, avec le vrai `winMM` :
#   · la fenêtre est RE-BORNÉE à la rogne dès que le format est plus petit —
#     le carré 47 x 47 de « monstre » devient 44,45 x 47 sur `domino` et
#     31,75 x 44,45 sur `micro` (il cesse d'être carré, ce qui est justement
#     l'archétype) ;
#   · la PLAQUE de bas de carte peut disparaître : sa hauteur tombe à une
#     valeur NÉGATIVE sur `micro`, `mini` et `square_eu` (la fenêtre y occupe
#     toute la hauteur utile), et le painter ne dessine alors rien ;
#   · `win_lock` ne protège RIEN de tout cela : il n'agit que sur les
#     RETAILLES faites par l'utilisateur dans le panneau, jamais sur ce
#     re-bornage-là.
# ENTRÉE POUR LA T3 : un modèle instancié sur un format non-poker doit soit
# re-dériver ses zones, soit déclarer son format et le dire à l'écran. Ne pas
# supposer que l'habillage « tient » partout : il tient en poker, et sur les
# formats plus grands (tarot, jumbo) où rien n'est re-borné.
# ═════════════════════════════════════════════════════════════════════════════
_HABILLAGE_COMMUN = {
    "line_color": "", "banner_text": "", "win_lock": False,
    "back_same": True, "back_label": True,
    # LE VERSO PERSONNALISÉ est VIDE dans les sept habillages, et ce n'est pas
    # un oubli : un archétype qui pointerait un fichier pointerait le fichier
    # d'un AUTRE jeu. Les clés existent quand même (c'est par elles que la
    # liste blanche des modèles les admet — voir models.py).
    "back_image": "", "back_layers": [],
    "fit": True, "socles": True, "seats": True, "socle_alpha": 0.82,
}


def _habillage(**kw) -> dict:
    out = dict(_HABILLAGE_COMMUN)
    # LE SCEAU EST ÉTEINT DANS LES SEPT HABILLAGES, et ce n'est pas un oubli :
    # un archétype qui l'allumerait changerait l'aspect de tout deck déjà
    # instancié sur lui. En copie PROFONDE — `archetype_frame` en rend une de
    # toute façon, mais la table elle-même ne doit pas partager un sous-objet
    # entre ses sept entrées (la leçon de `window`, juste au-dessus).
    out["seal"] = copy.deepcopy(SEAL_DEFAULTS)
    # MÊME RAISON pour la pile du verso : `dict(_HABILLAGE_COMMUN)` est une
    # copie de SURFACE, les sept habillages partageraient une seule liste.
    out["back_layers"] = []
    # LE DÉCOR DE CADRE est SANS SOURCE dans les sept habillages, et ce n'est
    # pas un oubli : un archétype qui pointerait un fichier du magasin de
    # l'application pointerait l'image d'un autre jeu. La clé existe quand même
    # — c'est par elle que la liste blanche des modèles l'admet (models.py).
    # En copie PROFONDE, pour la même raison que `seal`.
    out["decor"] = copy.deepcopy(DECOR_DEFAULTS)
    out.update(kw)
    return out


ARCHETYPE_FRAMES = {
    # 1. Superstar du stade — « plaque à pans coupés 4,4 -> 55 x 80 » EST
    #    `edge_mm = 4` (63 - 8 = 55, 88 - 8 = 80, au millimètre) ; les pans
    #    coupés eux-mêmes viennent de `deco`, seule famille dont la fenêtre
    #    est chanfreinée ET la plaque étagée. Or champagne = rareté
    #    « legendary » + métal or ; les paliers argent/bronze sont un
    #    changement de rareté, pas un autre modèle.
    "superstar": _habillage(
        family="deco", rarity="legendary",
        line_mm=1.2, double=True, gap_mm=1.0, edge_mm=4.0, inner_mm=5.5,
        metal=True, metal_tone="gold", grad=True, grad_angle=104,
        corner="bracket", gem=True, banner=True,
        plate=True, plate_alpha=0.9,
        window={"x": 22.0, "y": 8.0, "w": 36.0, "h": 38.0, "r": 2.0},
        back="sunburst",
    ),
    # 2. Duel de chiffres — « bandeau titre rectangle, PAS d'ellipse » et un
    #    tableau zébré : c'est la plaque « epure » d'`sable`, un rectangle
    #    strict sans rayon. Papier mat = `grad: false` (aplat) et aucun métal.
    #    `inner_mm = 4` pose la bande à 55 mm de large : la colonne de la spec.
    "duel": _habillage(
        family="sable", rarity="rare",
        line_mm=0.5, double=False, gap_mm=0.0, edge_mm=2.0, inner_mm=4.0,
        metal=False, metal_tone="silver", grad=False, grad_angle=90,
        corner="none", gem=False, banner=False,
        plate=True, plate_alpha=1.0,
        window={"x": 4.0, "y": 13.0, "w": 55.0, "h": 31.0, "r": 0.0},
        back="chevron",
    ),
    # 3. Créature à évolutions — le gros liseré coloré d'un jeu de créatures :
    #    `timber` est la seule famille dont la bande a une masse de 3 mm, avec
    #    ses rivets ; le métal or donne le liseré, la rareté donne l'élément
    #    (uncommon = vert par défaut, la teinte se change en un clic).
    "creature": _habillage(
        family="timber", rarity="uncommon",
        line_mm=1.4, double=True, gap_mm=0.8, edge_mm=1.8, inner_mm=6.0,
        metal=True, metal_tone="gold", grad=True, grad_angle=120,
        corner="stud", gem=True, banner=True,
        plate=True, plate_alpha=0.9,
        window={"x": 6.0, "y": 11.0, "w": 51.0, "h": 35.0, "r": 2.5},
        back="scales",
    ),
    # 4. Arcane mystique — « bordure 2,5 mm » EST `edge_mm = 2.5`. La famille
    #    `arcane` porte déjà la fenêtre en arc, les volutes et la plaque en
    #    arc de la boîte à règles ; rien à inventer.
    "arcane": _habillage(
        family="arcane", rarity="epic",
        line_mm=0.9, double=True, gap_mm=1.1, edge_mm=2.5, inner_mm=4.0,
        metal=True, metal_tone="gold", grad=True, grad_angle=118,
        corner="scroll", gem=True, banner=True,
        plate=True, plate_alpha=0.92,
        window={"x": 5.0, "y": 9.5, "w": 53.0, "h": 39.0, "r": 3.0},
        back="runes",
    ),
    # 5. Monstre de duel — « cadre couleur pleine = catégorie » : `grad:
    #    false` rend l'aplat, et l'anneau plein de `runic` (zone « anneau »)
    #    en est la masse. Fenêtre CARRÉE 47 x 47, verrou de proportions armé —
    #    c'est le carré qui fait l'archétype. Le code couleur est PROPRE :
    #    rareté « mythic » + filet d'argent, décalé de l'original.
    "monstre": _habillage(
        family="runic", rarity="mythic",
        line_mm=1.0, double=False, gap_mm=0.0, edge_mm=1.6, inner_mm=6.0,
        metal=True, metal_tone="silver", grad=False, grad_angle=90,
        corner="spike", gem=True, banner=False,
        plate=True, plate_alpha=0.95,
        window={"x": 8.0, "y": 18.5, "w": 47.0, "h": 47.0, "r": 1.0},
        win_lock=True, back="lattice",
    ),
    # 6. Légende du terrain — la seule chose que P2 doit dessiner ici est la
    #    BORDURE BLANCHE VINTAGE : `sable`, dont l'anneau est CLAIR, un filet
    #    de 0,35 mm, et une fenêtre qui descend jusqu'au bandeau de nom. La
    #    plaque tombe alors à 73,8 -> 84,3 mm, soit la bande « 0,74 (63 x 10) »
    #    de la spec en hauteur (la largeur, elle, est celle de la bande :
    #    55,6 mm — une plaque pleine largeur n'existe pas dans ce moteur).
    #    « Photo pleine page » est à un glissement de fenêtre, ou à « Aucun
    #    cadre » : c'est un réglage, pas un autre archétype.
    "legende": _habillage(
        family="sable", rarity="common",
        line_mm=0.35, double=False, gap_mm=0.0, edge_mm=1.2, inner_mm=2.5,
        metal=True, metal_tone="silver", grad=False, grad_angle=90,
        corner="none", gem=False, banner=False,
        plate=True, plate_alpha=1.0,
        window={"x": 2.5, "y": 2.5, "w": 58.0, "h": 69.5, "r": 0.0},
        back="guilloche",
    ),
    # 7. Arcane gravée — LA SEULE À EXIGER UNE FAMILLE NOUVELLE (`gravure`).
    #    Le « double filet 1,5/3 mm », lui, sort du moteur existant : le
    #    second filet est posé à `edge + line/2 + gap + 0,3 line`, soit
    #    1,5 + 0,25 + 1,1 + 0,15 = 3,00 mm PILE. Ce qu'aucune famille ne
    #    savait faire : la marge ivoire et l'aplat de pochoir décalé.
    #    Vermillon/bleu/ocre/vert de la spec = les raretés mythic/rare/
    #    legendary/uncommon, qui donnent ici la couleur de l'ENCRE.
    "gravee": _habillage(
        family="gravure", rarity="mythic",
        line_mm=0.5, double=True, gap_mm=1.1, edge_mm=1.5, inner_mm=4.0,
        metal=False, metal_tone="copper", grad=False, grad_angle=90,
        corner="none", gem=False, banner=False,
        plate=True, plate_alpha=1.0,
        window={"x": 4.0, "y": 13.0, "w": 55.0, "h": 61.0, "r": 0.0},
        back="mirror",
    ),
}


def archetype_frame(nom: str) -> dict:
    """L'habillage d'un archétype, en COPIE PROFONDE — LA porte d'entrée.

    `ARCHETYPE_FRAMES` est une table de MODULE : ses sous-dictionnaires
    (`window`) sont partagés par tous ceux qui la lisent. Une instanciation qui
    écrirait dans le `window` reçu — un modèle qui recale une zone, un test qui
    bidouille une valeur — contaminerait TOUS les decks instanciés ensuite dans
    le même processus, sans rien casser tout de suite. C'est le genre de
    partage qui se paie trois semaines plus tard.

    La T3 consomme cette fonction, jamais la table. `KeyError` nommée pour un
    archétype inconnu : c'est à l'appelant d'en faire un 404 en français."""
    hab = ARCHETYPE_FRAMES.get(nom)
    if hab is None:
        raise KeyError(nom)
    return copy.deepcopy(hab)


def catalog() -> dict:
    """Le catalogue complet. `combos` est CALCULÉ, jamais écrit à la main."""
    # TOUT SORT EN COPIE PROFONDE, ET C'EST UNE CORRECTION DE RONDE. Les six
    # listes du catalogue sortaient NUES : un appelant qui touchait le
    # dictionnaire rendu écrivait dans les tables du module, pour tout le
    # processus. `family_traits` avait sa copie, ses voisines non — la moitié
    # d'une garde n'en est pas une.
    return {
        "families": copy.deepcopy(FAMILIES),
        # LES TRAITS MESURÉS (phase 4, D6) : ce sur quoi « adopter la
        # bordure » choisit sa famille. Publiés pour être vérifiables de
        # l'extérieur — et parce qu'un choix qu'on ne peut pas recalculer
        # est un choix qu'il faut croire.
        "family_traits": copy.deepcopy(FAMILY_TRAITS),
        "family_scales": traits_echelles(),
        "family_eps": PROCHE_EPS,
        "rarities": copy.deepcopy(RARITIES),
        "backs": copy.deepcopy(BACKS),
        "corners": copy.deepcopy(CORNERS),
        "metals": copy.deepcopy(METALS),
        "presets": copy.deepcopy(PRESETS),
        "limits": copy.deepcopy(LIMITS),
        # la borne que le FORMAT ajoute aux bornes absolues : au-delà, la bande
        # s'inverserait. Publiée pour qu'elle soit vérifiable de l'extérieur.
        "band_min_mm": BAND_MIN_MM,
        "band_max_mm": {k: band_max_mm(v["trim_mm"][0], v["trim_mm"][1])
                        for k, v in FORMATS.items()},
        # LE SCEAU : ses métaux, son plancher d'imprimeur et son schéma —
        # joignables de l'extérieur, comme le reste du catalogue.
        "seal_kinds": copy.deepcopy(SEAL_KINDS),
        "seal_min_mm": SEAL_MIN_MM,
        "seal_defaults": copy.deepcopy(SEAL_DEFAULTS),
        # LE VERSO PERSONNALISÉ : ses modes de fusion, ses plafonds et les
        # défauts d'un calque — joignables de l'extérieur comme le reste.
        "back_blends": copy.deepcopy(BACK_BLENDS),
        "back_layers_max": BACK_LAYERS_MAX,
        "back_images_max": BACK_IMAGES_MAX,
        "back_layer_defaults": dict(BACK_LAYER_DEFAULTS),
        # LE DÉCOR DE CADRE PAR IA : son schéma, joignable de l'extérieur
        "decor_defaults": dict(DECOR_DEFAULTS),
        "defaults": dict(DEFAULTS),
        "combos": len(FAMILIES) * len(RARITIES),
        "vector": True,
        "raster_assets": 0,
        "note": ("Cadres tracés au canvas à geom.canvas_px : aucun bitmap, "
                 "aucune résolution plafond. Le backend ne dessine pas — "
                 "moteur unique, règle du WYSIWYG."),
    }


# ═════════════════════════════════════════════════════════════════════════════
# MÉTRIQUES — millimètres du cadre -> pixels de la TOILE
# ═════════════════════════════════════════════════════════════════════════════
def _len(value, default: float, lo: float, hi: float, what: str) -> float:
    """Longueur en mm venant du client. Jamais d'exception non maîtrisée,
    jamais un 500 : hors bornes -> ValueError qui cite la borne."""
    if value is None:
        return float(default)
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{what} doit être un nombre de millimètres")
    if not math.isfinite(v):
        raise ValueError(f"{what} doit être un nombre de millimètres")
    if v < lo or v > hi:
        raise ValueError(
            f"{what} doit tenir entre {lo:g} et {hi:g} mm (reçu {v:g})")
    return v


def _px(mm: float, dpi: int) -> float:
    """mm -> px, SANS arrondi entier : un filet se dessine en sous-pixel,
    exactement comme le trait de coupe à 37,5 px des formats impériaux.
    L'ordre des opérations est celui de `mod-frame.js` — `v / 25.4 * dpi` —
    parce que deux ordres différents ne donnent pas le même double."""
    return rnd(mm / MM_PER_INCH * dpi, 2)


def frame_metrics(g, line_mm: float, gap_mm: float, edge_mm: float,
                  inner_mm: float, win: dict, seal: dict | None = None) -> dict:
    """Le miroir exact de `localMetrics()` de js/mod-frame.js.

    `win` est la fenêtre d'illustration en millimètres depuis le coin de
    COUPE (la même origine que les slots de texte de P3) ; elle sort en
    pixels depuis le coin de TOILE, fond perdu compris.

    `seal` sort en DEUX tableaux plutôt qu'en sous-objet : la pastille de
    vérification de l'écran compare `JSON.stringify` clé par clé, et deux
    dictionnaires dont l'ordre d'insertion diffère se comparent faux sans
    qu'un seul nombre ait bougé. Un tableau n'a qu'un ordre.
      seal_mm : [largeur TRACÉE, borne du format]
      seal_px : [largeur, x, y, w, h, r] — l'anneau EXTÉRIEUR, depuis la TOILE
    """
    dpi = g.dpi
    # Les pixels PUBLIÉS sont ceux du dessin : `model()` de mod-frame.js borne
    # le retrait et la marge par le format (band_max_mm), donc ici aussi —
    # sinon l'écran et le backend divergeraient sur le seul format concerné et
    # la pastille de vérification passerait au rouge sans qu'un pixel bouge.
    cap = band_max_mm(g.trim_mm[0], g.trim_mm[1])
    e = min(edge_mm, cap)
    s = seal if isinstance(seal, dict) else SEAL_DEFAULTS
    smax = seal_max_mm(g.trim_mm[0], g.trim_mm[1], e, win)
    swid = min(float(s.get("width_mm", SEAL_DEFAULTS["width_mm"])), smax)
    # l'anneau EXTÉRIEUR, en pixels de toile : la même arithmétique que
    # `m.outer` du painter (`bx + edge`, `tw - 2 * edge`, `max(0, R - edge)`).
    epx = e / MM_PER_INCH * dpi
    return {
        "line_px": _px(line_mm, dpi),
        "gap_px": _px(gap_mm, dpi),
        "edge_px": _px(min(edge_mm, cap), dpi),
        "inner_px": _px(min(inner_mm, cap), dpi),
        "corner_px": rnd(g.corner_px, 2),
        "win_px": [
            rnd(g.bleed_off_px[0] + win["x"] / MM_PER_INCH * dpi, 2),
            rnd(g.bleed_off_px[1] + win["y"] / MM_PER_INCH * dpi, 2),
            _px(win["w"], dpi),
            _px(win["h"], dpi),
            _px(win["r"], dpi),
        ],
        "seal_mm": [rnd(swid, 2), smax],
        "seal_px": [
            _px(swid, dpi),
            rnd(g.bleed_off_px[0] + epx, 2),
            rnd(g.bleed_off_px[1] + epx, 2),
            rnd(g.trim_px[0] - 2 * epx, 2),
            rnd(g.trim_px[1] - 2 * epx, 2),
            rnd(max(0.0, g.corner_px - epx), 2),
        ],
        "canvas_px": [g.canvas_px[0], g.canvas_px[1]],
    }


def _win_of(raw, g) -> dict:
    """La fenêtre par défaut est PROPORTIONNELLE au format : la pièce se tient
    debout sur les 12 formats sans qu'on lui écrive 12 rectangles."""
    tw, th = g.trim_mm
    if not isinstance(raw, dict):
        return {"x": rnd(tw * 0.105, 2), "y": rnd(th * 0.075, 2),
                "w": rnd(tw * 0.79, 2), "h": rnd(th * 0.505, 2), "r": 2.5}
    return {
        "x": _len(raw.get("x"), 0.0, 0, 1000, "L'abscisse de la fenêtre"),
        "y": _len(raw.get("y"), 0.0, 0, 1000, "L'ordonnée de la fenêtre"),
        "w": _len(raw.get("w"), tw, 0, 1000, "La largeur de la fenêtre"),
        "h": _len(raw.get("h"), th, 0, 1000, "La hauteur de la fenêtre"),
        "r": _len(raw.get("r"), 2.5, LIMITS["win_r_mm"][0],
                  LIMITS["win_r_mm"][1], "Le rayon de la fenêtre"),
    }


# ═════════════════════════════════════════════════════════════════════════════
# OCCUPATION — meubles réservés, résolution des recouvrements, comptage
#
# Le défaut que ce bloc supprime : le bandeau de rareté était peint à une
# position FIXE de la bande basse, et la signature de l'artiste passait
# dessous. Mesuré sur le document par défaut : le bandeau recouvrait 72,7 %
# de la boîte `artist` et 68,9 % de `num`, et la gemme 73,5 % de `cost` — sans
# qu'aucun compteur ne le dise. Un meuble MOBILE choisit maintenant sa place
# dans une voie libre ; ce qui reste est compté et affiché.
# ═════════════════════════════════════════════════════════════════════════════
def _ov(a, b) -> float:
    """Surface commune de deux boîtes [x, y, w, h], en mm²."""
    dx = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    dy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return dx * dy if dx > 0 and dy > 0 else 0.0


def _box4(b) -> list | None:
    """Une boîte de mention venue du document : [x, y, w, h] en mm, ou None.
    Un slot mal formé n'est pas une erreur 500, c'est un slot ignoré."""
    if not isinstance(b, (list, tuple)) or len(b) < 4:
        return None
    try:
        v = [float(b[0]), float(b[1]), float(b[2]), float(b[3])]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(x) for x in v) or v[2] <= 0 or v[3] <= 0:
        return None
    return v


def _mentions(slots) -> list[dict]:
    """Les mentions obligatoires : les slots de texte de la pièce 03, lus en
    LECTURE UNIVERSELLE (règle 3). Le cadre ne les déplace jamais — c'est lui
    qui s'écarte."""
    out = []
    if not isinstance(slots, (list, tuple)):
        return out
    for s in slots:
        if not isinstance(s, dict):
            continue
        box = _box4(s.get("box"))
        if box is None:
            continue
        out.append({"id": str(s.get("id") or "slot"), "box": box})
    return out


def _free_lanes(occupied: list[tuple[float, float]], lo: float,
                hi: float) -> list[tuple[float, float]]:
    """Complément de `occupied` dans [lo, hi] : les intervalles LIBRES."""
    segs = sorted((max(lo, a), min(hi, b)) for a, b in occupied if b > lo and a < hi)
    lanes, cur = [], lo
    for a, b in segs:
        if a > cur:
            lanes.append((cur, a))
        cur = max(cur, b)
    if cur < hi:
        lanes.append((cur, hi))
    return lanes


def _place_banner(tw: float, th: float, inner: float, edge: float,
                  label: str, mentions: list[dict], wbox: list,
                  fit: bool) -> dict:
    """Le bandeau garde sa largeur et son centrage ; il choisit son ORDONNÉE,
    et il MAIGRIT si la seule voie libre est plus étroite que lui — c'est le
    « la bande se scinde autour de lui » du cahier des charges, appliqué au
    ruban lui-même. Déterministe : l'aperçu et le fichier livré sont le même
    bitmap.

    Deux leviers, dans cet ordre : (1) descendre/monter dans une voie libre de
    sa colonne, (2) réduire sa hauteur jusqu'à BANNER_MIN_H_MM. Une voie qui
    tombe sur l'illustration est pénalisée : mieux vaut un ruban plus fin en
    bas de carte qu'un ruban pleine hauteur au milieu du dessin.
    """
    w = min(tw * BANNER_MAX_F, BANNER_CH_MM * (len(label) + BANNER_PAD_CH))
    h = BANNER_H_MM
    x = tw / 2.0 - w / 2.0
    y0 = th - inner - h * 0.62
    lo, hi = edge, th - edge
    y, lane = y0, "naturelle"
    if fit:
        occ = [(m["box"][1] - CLEAR_MM, m["box"][1] + m["box"][3] + CLEAR_MM)
               for m in mentions
               if m["box"][0] < x + w and m["box"][0] + m["box"][2] > x]
        lanes = [(a, b) for a, b in _free_lanes(occ, lo, hi)
                 if b - a >= BANNER_MIN_H_MM]
        best = None
        for a, b in lanes:
            hh = min(h, b - a)
            cand = min(max(y0, a), b - hh)
            # pénalité d'illustration : la moitié de la hauteur de rogne, donc
            # toujours pire qu'un déplacement dans la moitié basse.
            pen = th * 0.5 if _ov([x, cand, w, hh], wbox) > 0 else 0.0
            d = abs((cand + hh / 2.0) - (y0 + h / 2.0)) + pen
            if best is None or d < best[0] - 1e-9:
                best = (d, cand, hh, pen)
        if best is not None:
            _, y, h, pen = best
            if abs(y - y0) < 1e-9 and abs(h - BANNER_H_MM) < 1e-9:
                lane = "naturelle"
            elif h < BANNER_H_MM - 1e-9:
                lane = "voie libre, ruban aminci"
            else:
                lane = "voie libre"
        else:
            lane = "aucune voie libre"
    return {"id": "banner", "label": "bandeau de rareté", "z": 70,
            "movable": True, "lane": lane,
            "box": [rnd(x, 2), rnd(y, 2), rnd(w, 2), rnd(h, 2)]}


def _place_gem(tw: float, th: float, inner: float, rank: int,
               mentions: list[dict], fit: bool) -> dict:
    """La gemme a quatre logements possibles : les quatre coins de la bande.

    Si AUCUN coin n'est libre — c'est le cas dès que la pièce 03 pose un coût
    et deux statistiques aux angles — la gemme ne se pose pas PAR-DESSUS le
    chiffre : elle DEVIENT son logement. Elle passe alors en couche 40, sous
    le texte, et le chiffre s'assied dedans. Un meuble de la couche 40 ne peut
    pas masquer une mention : le recouvrement disparaît par construction, et
    la carte y gagne le « logement réservé » que le cadre ne fournissait pas.
    """
    r = GEM_R_MM
    reach = 1.5 * r + max(0, rank - 1) * PIP_STEP_MM + PIP_R_MM
    off = inner + r * GEM_OFF_F
    cands = [
        ("HG", off, off, 1), ("HD", tw - off, off, -1),
        ("BG", off, th - off, 1), ("BD", tw - off, th - off, -1),
    ]
    best = None
    for name, cx, cy, d in cands:
        x = cx - r if d > 0 else cx - reach
        box = [x, cy - r, r + reach, 2 * r]
        cost = sum(_ov(box, m["box"]) for m in mentions)
        if best is None or cost < best[0] - 1e-9:
            best = (cost, name, box, cx, cy, d)
        if not fit or cost <= 0.0:
            break
    cost, name, box, cx, cy, d = best
    seat = fit and cost > TOL_MM2
    shape, host = "disc", None
    if seat:
        # Le chiffre le plus recouvert devient l'hôte : la gemme s'aligne sur
        # LUI et se range dessous. Un disque circonscrit à une mention large et
        # plate (la signature : 17 x 3,7 mm) déborderait de la carte — au-delà
        # de GEM_SEAT_RATIO, l'écrin devient un cartouche à la taille de la
        # mention. Mesuré : sans cette règle, un rayon de 9,35 mm centré à
        # 82,9 mm sortait à 92,26 mm sur une carte de 88,9 mm de haut.
        host = max(mentions, key=lambda m: _ov(box, m["box"]))
        hb = host["box"]
        cx, cy = hb[0] + hb[2] / 2.0, hb[1] + hb[3] / 2.0
        lo = min(hb[2], hb[3])
        hi = max(hb[2], hb[3])
        if hi <= GEM_SEAT_RATIO * lo:
            r = hi / 2.0 + SEAT_PAD_MM
            box = [cx - r, cy - r, 2 * r, 2 * r]
        else:
            shape = "rect"
            r = lo / 2.0 + SEAT_PAD_MM
            box = [hb[0] - SEAT_PAD_MM, hb[1] - SEAT_PAD_MM,
                   hb[2] + 2 * SEAT_PAD_MM, hb[3] + 2 * SEAT_PAD_MM]
        name = "logement de " + host["id"]
    return {"id": "gem",
            "label": ("gemme en logement de " + host["id"]) if seat
                     else "gemme de rareté",
            "z": 40 if seat else 70,
            "movable": True, "lane": name, "dir": d, "seat": seat,
            "shape": shape, "pips": 0 if seat else rank,
            "cx": rnd(cx, 2), "cy": rnd(cy, 2), "r": rnd(r, 2),
            "box": [rnd(box[0], 2), rnd(box[1], 2), rnd(box[2], 2), rnd(box[3], 2)]}


def occupancy(g, f: dict, slots) -> dict:
    """Le plan d'occupation complet : meubles placés, socles, logements, et le
    COMPTEUR de recouvrements résiduels."""
    tw, th = float(g.trim_mm[0]), float(g.trim_mm[1])
    # La borne du FORMAT, appliquée exactement comme par `model()` de
    # mod-frame.js : au-delà, la bande s'inverse et les meubles se placeraient
    # par rapport à un anneau qui n'existe pas.
    cap = band_max_mm(tw, th)
    inner = min(float(f.get("inner_mm", DEFAULTS["inner_mm"])), cap)
    edge = min(float(f.get("edge_mm", DEFAULTS["edge_mm"])), cap)
    fit = bool(f.get("fit", True))
    mentions = _mentions(slots)
    win = f.get("window") if isinstance(f.get("window"), dict) else None
    if win is None:
        wbox = [rnd(tw * 0.105, 2), rnd(th * 0.075, 2),
                rnd(tw * 0.79, 2), rnd(th * 0.505, 2)]
    else:
        wbox = [rnd(float(win.get("x", 0)), 2), rnd(float(win.get("y", 0)), 2),
                rnd(float(win.get("w", tw)), 2), rnd(float(win.get("h", th)), 2)]

    boxes = [{"id": "window", "label": "fenêtre d'illustration", "z": 40,
              "movable": False, "lane": "posée", "box": wbox}]

    rank = 1
    for i, r in enumerate(RARITIES):
        if r["id"] == f.get("rarity"):
            rank = i + 1
    if f.get("gem", True):
        boxes.append(_place_gem(tw, th, inner, rank, mentions, fit))
    if f.get("banner", True):
        lab = str(f.get("banner_text") or "").strip()
        if not lab:
            lab = next((r["label"] for r in RARITIES
                        if r["id"] == f.get("rarity")), "")
        lab = lab.upper()
        if lab:
            boxes.append(_place_banner(tw, th, inner, edge, lab, mentions,
                                       wbox, fit))

    # Socles et logements : le cadre FOURNIT le fond dont la mention a besoin.
    # Une mention posée sur l'illustration reçoit une plaque ; une mention qui
    # déborde de la bande sur l'anneau reçoit un logement. Ce sont des meubles
    # de la couche 40 : ils passent SOUS le texte, jamais dessus.
    socles, seats = [], []
    band = [inner, inner, tw - 2 * inner, th - 2 * inner]
    # La gemme rangée en écrin EST le logement de son hôte : lui en dessiner un
    # second superposerait deux contours autour du même chiffre.
    gem_host = next((b["lane"][len("logement de "):] for b in boxes
                     if b["id"] == "gem" and b.get("seat")), None)
    for m in mentions:
        b = m["box"]
        area = b[2] * b[3]
        if f.get("socles", True) and _ov(b, wbox) > SOCLE_MIN_FRAC * area:
            socles.append({"id": "socle:" + m["id"], "label": "socle de " + m["id"],
                           "z": 40, "movable": False, "lane": "sous la mention",
                           "box": [rnd(b[0] - SOCLE_PAD_MM, 2), rnd(b[1] - SOCLE_PAD_MM, 2),
                                   rnd(b[2] + 2 * SOCLE_PAD_MM, 2), rnd(b[3] + 2 * SOCLE_PAD_MM, 2)]})
        # Un logement n'est PAS « la mention dépasse d'un cheveu » : c'est
        # « la mention est assise sur l'anneau ». Sans ce seuil, les neuf
        # slots recevaient un logement, la couronne était pavée de plaques
        # identiques et la signature graphique des six familles disparaissait
        # dessous (mesuré : Bois sculpté et Épure ne différaient plus que sur
        # 0,87 % des pixels de la vignette).
        ring = area - _ov(b, band)
        if f.get("seats", True) and ring > SEAT_MIN_FRAC * area \
                and m["id"] != gem_host:
            seats.append({"id": "seat:" + m["id"], "label": "logement de " + m["id"],
                          "z": 40, "movable": False, "lane": "dans l'anneau",
                          "box": [rnd(b[0] - SEAT_PAD_MM, 2), rnd(b[1] - SEAT_PAD_MM, 2),
                                  rnd(b[2] + 2 * SEAT_PAD_MM, 2), rnd(b[3] + 2 * SEAT_PAD_MM, 2)]})

    # LE COMPTEUR. Ne compte QUE ce qui masque : un meuble de la couche 70,
    # tracé par-dessus le texte de la pièce 03. Un socle ou un logement passe
    # dessous : ce n'est pas un recouvrement, c'est le fond de la mention.
    hits = []
    for fb in boxes:
        if fb.get("z") != 70:
            continue
        for m in mentions:
            a = _ov(fb["box"], m["box"])
            area = m["box"][2] * m["box"][3]
            if a > TOL_MM2 and a > TOL_FRAC * area:
                hits.append({"kind": "recouvrement", "a": fb["id"], "b": m["id"],
                             "mm2": rnd(a, 2), "pct": rnd(100.0 * a / area, 1)})
    hits.sort(key=lambda h: -h["mm2"])
    return {
        "boxes": boxes + socles + seats,
        "mentions": [{"id": m["id"], "box": [rnd(v, 2) for v in m["box"]]}
                     for m in mentions],
        "collisions": hits,
        "count": len(hits),
        "socles": len(socles),
        "seats": len(seats),
        "fit": fit,
    }


# ═════════════════════════════════════════════════════════════════════════════
# pHYs — LE FICHIER PORTE SA PROPRE GÉOMÉTRIE
#
# Un PNG dont les chunks sont IHDR + IDAT + IEND ne dit que « 815 x 1110
# pixels ». Tout ce que l'interface affiche — 63 x 88 mm, 300 DPI, 3 mm de
# fond perdu — meurt à la frontière du fichier, et un lecteur applique 72 DPI.
# `pHYs` coûte 21 octets et transporte la définition ; `tEXt` transporte les
# boîtes en clair, faute de pouvoir écrire un TrimBox dans un PNG.
# ═════════════════════════════════════════════════════════════════════════════
PNG_SIG = b"\x89PNG\r\n\x1a\n"


def dpi_to_ppm(dpi: float) -> int:
    """DPI -> pixels par mètre, par la règle du domaine (arrondi demi-haut).
    300 -> 11811, 600 -> 23622, 150 -> 5906."""
    return R(float(dpi) / 0.0254)


def ppm_to_dpi(ppm: int) -> float:
    """La réciproque, et la seule définition que le fichier porte VRAIMENT.

    `pHYs` compte des pixels par MÈTRE ENTIERS : 300 DPI n'y est pas
    représentable. 11811 px/m valent 299,9994 DPI. Écrire « 300 DPI » dans le
    fichier serait exactement l'écart d'un millième de pour cent qu'on
    reproche aux autres — on écrit donc la valeur réelle, et la demandée à
    côté.
    """
    return round(float(ppm) * 0.0254, 4)


def png_chunks(data: bytes) -> list[tuple[str, int]]:
    """(type, longueur) de chaque chunk. Lève ValueError si ce n'est pas un
    PNG : c'est ce qui empêche d'estampiller « 300 DPI » sur autre chose."""
    if not isinstance(data, (bytes, bytearray)) or data[:8] != PNG_SIG:
        raise ValueError("Ce ne sont pas des octets PNG (signature absente)")
    out, p, n = [], 8, len(data)
    while p + 8 <= n:
        ln = struct.unpack(">I", data[p:p + 4])[0]
        typ = data[p + 4:p + 8].decode("latin-1")
        out.append((typ, ln))
        if typ == "IEND":
            return out
        p += 12 + ln
        if ln > n:
            raise ValueError("Chunk PNG plus long que le fichier")
    raise ValueError("PNG tronqué : aucun chunk IEND")


def png_size(data: bytes) -> tuple[int, int]:
    """Largeur et hauteur lues dans IHDR — LES OCTETS, pas une promesse."""
    if data[:8] != PNG_SIG or data[12:16] != b"IHDR":
        raise ValueError("Ce ne sont pas des octets PNG (IHDR absent)")
    return struct.unpack(">II", data[16:24])


def _chunk(typ: bytes, payload: bytes) -> bytes:
    body = typ + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(
        ">I", zlib.crc32(body) & 0xFFFFFFFF)


def _latin1(s: str) -> str:
    """`tEXt` est du Latin-1, point. Un tiret cadratin ou une apostrophe
    typographique y lèverait — on les remplace AVANT d'encoder, sinon la seule
    façon de s'en apercevoir est un 500 en production."""
    rep = {"—": "-", "–": "-", "’": "'", "‘": "'",
           "“": '"', "”": '"', " ": " ", "→": "->",
           "×": "x", "…": "...", "≤": "<=", "≥": ">="}
    out = []
    for ch in str(s):
        ch = rep.get(ch, ch)
        try:
            ch.encode("latin-1")
        except UnicodeEncodeError:
            ch = "?"
        out.append(ch)
    return "".join(out).replace("\n", " ").strip()


def png_texts(data: bytes) -> dict:
    """Les `tEXt` DÉJÀ présents dans les octets. Sert à rester idempotent :
    estampiller deux fois doit rendre le même fichier, or la mention du canal
    alpha ne peut plus être recalculée au second passage — le canal a déjà été
    retiré au premier. On la relit plutôt que d'en inventer une autre."""
    out, p = {}, 8
    while p + 8 <= len(data):
        ln = struct.unpack(">I", data[p:p + 4])[0]
        typ = data[p + 4:p + 8]
        if typ == b"tEXt":
            k, _, v = data[p + 8:p + 8 + ln].partition(b"\x00")
            out[k.decode("latin-1")] = v.decode("latin-1")
        if typ == b"IEND":
            break
        p += 12 + ln
    return out


def png_stamp(data: bytes, dpi: float, texts) -> bytes:
    """Réécrit le PNG avec `pHYs` (unité 1 = mètre) puis les `tEXt`, juste
    après IHDR. Idempotent : un `pHYs`/`tEXt` déjà présent est remplacé, pas
    empilé."""
    chunks, p, n = [], 8, len(data)
    if data[:8] != PNG_SIG:
        raise ValueError("Ce ne sont pas des octets PNG (signature absente)")
    while p + 8 <= n:
        ln = struct.unpack(">I", data[p:p + 4])[0]
        typ = data[p + 4:p + 8]
        chunks.append((typ, data[p:p + 12 + ln]))
        if typ == b"IEND":
            break
        p += 12 + ln
    if not chunks or chunks[0][0] != b"IHDR":
        raise ValueError("PNG sans IHDR en tête")
    ppm = dpi_to_ppm(dpi)
    head = [_chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1))]
    for key, val in texts:
        k = _latin1(key)[:79].strip()
        if not k:
            continue
        head.append(_chunk(b"tEXt", k.encode("latin-1") + b"\x00"
                           + _latin1(val).encode("latin-1")))
    out = [PNG_SIG, chunks[0][1]] + head
    for typ, raw in chunks[1:]:
        if typ in (b"pHYs", b"tEXt"):
            continue
        out.append(raw)
    return b"".join(out)


# ═════════════════════════════════════════════════════════════════════════════
# LE QUATRIÈME CANAL — « soit on s'en sert, soit on livre en RGB »
#
# MESURE sur le fichier livré : type couleur 6 (RGBA), et l'alpha vaut 255 sur
# les 904 650 pixels. Zéro information transportée, un quart des échantillons
# en pure perte, dans un fichier destiné à une presse — qui n'a de toute façon
# aucun usage d'un canal de transparence.
#
# On ne peut pas « s'en servir » : le seul masque qui aurait un sens serait la
# découpe, et la rendre transparente effacerait le FOND PERDU, c'est-à-dire la
# raison d'être du fichier. On livre donc en RGB — mais jamais sur parole :
# la conversion est VÉRIFIÉE ici même, échantillon par échantillon, contre la
# source. Si le moindre octet RGB bougeait, on rend les octets d'origine.
# ═════════════════════════════════════════════════════════════════════════════
def png_drop_constant_alpha(data: bytes) -> tuple[bytes, str]:
    """RGBA dont l'alpha est constant à 255 -> RGB, sans toucher aux couleurs.

    Rend `(octets, mention)`. `mention` est la phrase écrite dans le `tEXt`
    `Alpha` : elle dit ce qui a été mesuré ET ce qui a été fait. En cas de
    doute — n'importe quelle exception, un alpha utile, une vérification qui
    ne retombe pas sur ses pieds — les octets d'ORIGINE sortent intacts.
    """
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            if im.mode != "RGBA":
                return data, "aucun canal alpha dans le fichier (mode %s)" % im.mode
            im.load()
            lo, hi = im.getchannel("A").getextrema()
            n = im.width * im.height
            if not (lo == 255 and hi == 255):
                return data, ("canal alpha UTILE (min %d, max %d sur %d pixels) : conserve"
                              % (lo, hi, n))
            rgb = im.convert("RGB")
            attendu = rgb.tobytes()
            buf = io.BytesIO()
            rgb.save(buf, format="PNG", optimize=False, compress_level=6)
            out = buf.getvalue()
        with Image.open(io.BytesIO(out)) as relu:
            relu.load()
            if relu.mode != "RGB" or relu.size != (im.width, im.height) \
                    or relu.tobytes() != attendu:
                return data, ("verification de la conversion RGB en echec : "
                              "octets d'origine conserves")
        return out, ("alpha constant a 255 sur %d pixels (0 information) : "
                     "retire ; les %d octets RGB sont identiques a la source, "
                     "verifies un a un apres re-encodage" % (n, len(attendu)))
    except Exception as e:                                  # noqa: BLE001
        return data, "conversion RGB non tentee (%s) : octets d'origine" % (
            type(e).__name__,)


def stamp_texts(g, extra: dict | None = None) -> list[tuple[str, str]]:
    """Ce que le fichier dira de lui-même. Chaque nombre vient de `geom`, donc
    de la même règle que la toile : rien n'est écrit « en confiance ».

    CE QUE CES CHAÎNES NE DOIVENT PAS PORTER. Un fichier livré part chez un
    imprimeur, un client, un partenaire ; il n'a pas à emporter le nom de
    l'atelier qui l'a produit ni la numérotation interne des écrans du
    logiciel. La valeur `Software` nommait les deux. Elle ne décrit plus que
    le FICHIER — ce qu'il est, comment il a été tracé — et ne permet plus de
    remonter à son producteur. Les métadonnées d'un livrable se lisent, il
    faut donc qu'elles ne disent que ce qu'on accepte de publier.
    """
    bx, by = g.bleed_off_px
    sx, sy = g.safe_off_px
    t = [
        ("Software", "carte a jouer - cadre vectoriel trace a l'echelle 1, "
                     "aucun bitmap"),
        ("Format", "%s - rogne %g x %g mm" % (g.fmt, g.trim_mm[0], g.trim_mm[1])),
        # `%g` tronquait 299.9994 en « 299.999 » : ecrire la valeur reelle
        # puis en perdre la derniere decimale, c'est la meme faute en plus
        # sournois. Quatre decimales, toujours.
        ("Resolution", "%.4f DPI reels - pHYs %d px/m unite 1 - %d DPI demandes"
                       % (ppm_to_dpi(dpi_to_ppm(g.dpi)), dpi_to_ppm(g.dpi),
                          g.dpi)),
        ("BleedBox", "0,0 %dx%d px - fond perdu %g mm"
                     % (g.canvas_px[0], g.canvas_px[1], g.bleed_mm)),
        ("TrimBox", "%g,%g %dx%d px - couper ici"
                    % (bx, by, g.trim_px[0], g.trim_px[1])),
        ("SafeBox", "%g,%g %dx%d px - zone sure %g mm"
                    % (sx, sy, g.safe_px[0], g.safe_px[1], g.safe_mm)),
    ]
    for k, v in (extra or {}).items():
        t.append((str(k), str(v)))
    return t


def _int(value, default: int, what: str) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        # OverflowError : json.loads("1e999") rend inf, et int(inf) lève.
        raise ValueError(f"{what} doit être un entier (reçu {value!r})")


# ═════════════════════════════════════════════════════════════════════════════
# L'ÉPREUVE DE CONTRÔLE — DE VRAIS TRAITS DE COUPE, ET AILLEURS QUE DANS L'ENCRE
#
# Reproche du tour précédent, mot pour mot : « Aucun trait de coupe ni repère de
# registration dans le fichier livré : le fond perdu est bien peint, mais
# l'imprimeur doit faire confiance à des décalages écrits en toutes lettres
# dans une métadonnée au lieu de les voir sur la planche. »
#
# LE FICHIER D'IMPRESSION N'EN PORTERA JAMAIS, ET C'EST VOULU. La toile fait
# exactement `canvas_px` : du trait de coupe au bord, il n'y a que du FOND
# PERDU, c'est-à-dire de l'encre destinée à passer sous la lame. Y tracer un
# repère, c'est mettre un trait noir dans la zone rognée — au mieux inutile, au
# pire visible sur la tranche. Un repère de coupe se pose HORS du fond perdu ;
# il faut donc du papier en plus, et un fichier de plus.
#
# C'est ce fichier-là. Il ajoute une marge de papier autour de la toile livrée,
# y trace les huit traits de coupe alignés sur la rogne, quatre mires de
# repérage et une légende chiffrée — et il ne touche PAS à un seul pixel de la
# carte : la vérification est faite ici même, échantillon par échantillon,
# avant de répondre. Si le moindre octet de la zone carte avait bougé, la route
# refuse de livrer plutôt que de livrer une épreuve qui ment.
# ═════════════════════════════════════════════════════════════════════════════
MARGIN_MM = (5.0, 25.0)          # bornes de la marge de papier de l'épreuve
MARK_MM = 5.0                    # longueur d'un trait de coupe
MARK_W_MM = 0.25                 # épaisseur du trait (0,25 mm = la norme)


def _mark_px(dpi: int) -> int:
    """Épaisseur du trait de coupe, en pixels, au moins 1."""
    return max(1, R(MARK_W_MM / MM_PER_INCH * dpi))


def control_geometry(g, margin_mm: float) -> dict:
    """Où tombe chaque trait, EN PIXELS DE L'ÉPREUVE, et de combien la coupe
    est arrondie. `bleed_off_px` vaut 35,5 px au format poker : la coupe passe
    ENTRE deux pixels. On trace sur la colonne entière la plus proche et on
    écrit le résidu — plutôt que de laisser croire à un repère au pixel."""
    m = R(float(margin_mm) / MM_PER_INCH * dpi_of(g))
    bx, by = g.bleed_off_px
    trim = [m + bx, m + by, m + bx + g.trim_px[0], m + by + g.trim_px[1]]
    drawn = [R(v) for v in trim]
    # TOUT CE QUI SE TRACE RESTE SUR LE PAPIER, ET C'EST BORNÉ ICI.
    # Le trait de coupe ne peut pas être plus long que la marge, et la mire,
    # centrée au milieu de la marge, ne peut pas déborder dessus non plus :
    # son bras vaut 2r depuis le centre placé à m/2. Sans cette borne, une
    # marge de 5 mm sur un petit format faisait mordre la mire SUR LA CARTE —
    # la vérification octet à octet de `build_control_proof` l'a refusé net,
    # ce qui est la bonne fin, mais un refus n'est pas une géométrie juste.
    return {
        "margin_px": m,
        "canvas_px": [g.canvas_px[0] + 2 * m, g.canvas_px[1] + 2 * m],
        "trim_exact": [rnd(v, 2) for v in trim],
        "trim_drawn": drawn,
        "residu_px": [rnd(abs(drawn[i] - trim[i]), 2) for i in range(4)],
        # Le trait de coupe laisse toujours une bande de papier au cartouche :
        # 15 px au minimum, une ligne de texte plus sa garde. Sur une marge de
        # 10 mm a 300 DPI cela ne change rien (le trait fait ses 5 mm) ; sur la
        # marge minimale de 5 mm, il se raccourcit plutot que d'effacer la
        # mention « NE PAS IMPRIMER ».
        "mark_px": min(max(1, m - max(15, m // 8)),
                       R(MARK_MM / MM_PER_INCH * dpi_of(g))),
        "mark_w_px": _mark_px(dpi_of(g)),
        "mire_r_px": max(2, min(R(2.0 / MM_PER_INCH * dpi_of(g)),
                                (m // 2 - 2) // 2)),
    }


def dpi_of(g) -> int:
    """La définition de la géométrie, en entier — `g.dpi` est déjà entier, mais
    ce petit passage évite de le supposer à cinq endroits."""
    return int(g.dpi)


MENTION_COURTE = "EPREUVE DE CONTROLE - NE PAS IMPRIMER"


def _legende(d, out, txt: str, m: int, L: int) -> list[str]:
    """Écrit la légende SOUS les traits de coupe, en la repliant pour qu'elle
    tienne sur le papier. Rend les lignes réellement écrites (liste vide si
    aucune police n'est disponible) : rien n'est affirmé au hasard.

    Écrite d'un seul trait, elle sortait par la droite du fichier — 200 signes
    pour la largeur d'une carte. Une mention coupée en plein milieu est une
    mention qui ment par omission. On replie donc, et si le papier est trop
    petit pour la légende complète (format micro, marge de 5 mm), on écrit au
    moins la mention qui compte : celle qui dit que ce fichier ne s'imprime
    pas.
    """
    try:
        from PIL import ImageFont
    except Exception:                                       # noqa: BLE001
        return []
    largeur = out.width - 2 * m                # la laisse alignée sur la toile
    haut = out.height - m + L + 1
    dispo = max(0, out.height - haut - 1)
    for source in (txt, MENTION_COURTE):
        mots = source.split(" ")
        for taille in range(max(9, m // 5), 7, -1):
            try:
                police = ImageFont.load_default(size=taille)
            except Exception:                               # noqa: BLE001
                try:
                    police = ImageFont.load_default()
                except Exception:                           # noqa: BLE001
                    return []
            lignes, cur = [], ""
            for mot in mots:
                essai = (cur + " " + mot).strip()
                if cur and d.textlength(essai, font=police) > largeur:
                    lignes.append(cur)
                    cur = mot
                else:
                    cur = essai
            if cur:
                lignes.append(cur)
            # +2 px de garde : `pas` est un interligne calculé, pas la vraie
            # descente de la police. Sans la garde, la dernière ligne frôlait
            # le bord du papier.
            pas = int(taille * 1.25) + 1
            if len(lignes) * pas + 2 <= dispo and \
                    max(d.textlength(x, font=police) for x in lignes) <= largeur:
                for i, ligne in enumerate(lignes):
                    d.text((m, haut + i * pas), ligne, fill=(60, 60, 60),
                           font=police)
                return lignes
    return []


def build_control_proof(data: bytes, g, margin_mm: float,
                        face: str = "front") -> tuple[bytes, dict]:
    """L'épreuve de contrôle. Rend `(octets, rapport)`.

    `rapport["pixels_identiques"]` n'est pas une promesse : la zone carte de
    l'épreuve est relue après encodage et comparée octet à octet à la source.
    """
    import io

    from PIL import Image, ImageDraw

    C = control_geometry(g, margin_mm)
    m = C["margin_px"]
    with Image.open(io.BytesIO(data)) as src:
        src.load()
        carte = src.convert("RGB")
    if carte.size != (g.canvas_px[0], g.canvas_px[1]):
        raise ValueError("La toile reçue fait %dx%d px au lieu de %dx%d"
                         % (carte.width, carte.height,
                            g.canvas_px[0], g.canvas_px[1]))
    attendu = carte.tobytes()

    out = Image.new("RGB", (C["canvas_px"][0], C["canvas_px"][1]),
                    (255, 255, 255))
    out.paste(carte, (m, m))
    d = ImageDraw.Draw(out)
    noir = (0, 0, 0)
    w = C["mark_w_px"]
    L = C["mark_px"]
    x0, y0, x1, y1 = C["trim_drawn"]
    # Les huit traits de coupe. Chacun part du BORD DE TOILE (donc du bord du
    # fond perdu) et s'éloigne : pas un pixel de repère ne touche l'encre.
    for x in (x0, x1):
        d.rectangle([x - w // 2, m - L, x - w // 2 + w - 1, m - 1], fill=noir)
        d.rectangle([x - w // 2, out.height - m, x - w // 2 + w - 1,
                     out.height - m + L - 1], fill=noir)
    for y in (y0, y1):
        d.rectangle([m - L, y - w // 2, m - 1, y - w // 2 + w - 1], fill=noir)
        d.rectangle([out.width - m, y - w // 2, out.width - m + L - 1,
                     y - w // 2 + w - 1], fill=noir)
    # Quatre mires de repérage, aux QUATRE COINS du papier. Le rayon est BORNÉ
    # par `control_geometry` : bras de mire = 2r depuis un centre à m/2, donc
    # une mire trop grande mordrait sur la carte.
    #
    # AUX COINS, ET PAS AU MILIEU DES CÔTÉS. Mesuré à l'écran sur l'épreuve
    # livrée : une mire centrée sous la carte tombait exactement sur la bande
    # où s'écrit la légende, et le texte lui passait au travers. Les coins sont
    # libres — les traits de coupe, eux, sont sur la rogne, donc bien à
    # l'intérieur — et la bande du bas reste entière pour le cartouche.
    r = C["mire_r_px"]
    for cx, cy in ((m // 2, m // 2), (out.width - m // 2, m // 2),
                   (m // 2, out.height - m // 2),
                   (out.width - m // 2, out.height - m // 2)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=noir, width=w)
        d.rectangle([cx - w // 2, cy - r * 2, cx - w // 2 + w - 1, cy + r * 2],
                    fill=noir)
        d.rectangle([cx - r * 2, cy - w // 2, cx + r * 2, cy - w // 2 + w - 1],
                    fill=noir)
    # La légende : ce que l'épreuve est, et les nombres qu'elle montre.
    txt = ("EPREUVE DE CONTROLE - NE PAS IMPRIMER  |  %s %g x %g mm  |  %s  |  "
           "%d DPI demandes, %.4f DPI reels (pHYs %d px/m)  |  toile %dx%d px, "
           "coupe %dx%d px a %g;%g  |  zone sure %dx%d px  |  fond perdu %g mm, "
           "marge de l'epreuve %g mm"
           % (g.fmt, g.trim_mm[0], g.trim_mm[1],
              "verso" if face == "back" else "recto",
              dpi_of(g), ppm_to_dpi(dpi_to_ppm(dpi_of(g))),
              dpi_to_ppm(dpi_of(g)), g.canvas_px[0], g.canvas_px[1],
              g.trim_px[0], g.trim_px[1], g.bleed_off_px[0], g.bleed_off_px[1],
              g.safe_px[0], g.safe_px[1], g.bleed_mm, rnd(margin_mm, 2)))
    # LA LÉGENDE DOIT TENIR SUR LE PAPIER. Écrite d'un trait, elle sortait par
    # la droite : la phrase fait ~200 signes et la marge n'en offre que la
    # largeur de la toile. Une mention coupée en plein milieu est une mention
    # qui ment par omission — on choisit donc la plus grande taille qui rentre,
    # puis on replie sur les lignes disponibles SOUS les traits de coupe.
    lignes = _legende(d, out, txt, m, L)

    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=False, compress_level=6)
    brut = buf.getvalue()
    # LA VÉRIFICATION. On relit l'épreuve encodée et on recompare la zone
    # carte à la source. C'est le seul moyen d'écrire « la carte n'a pas
    # bougé » sans demander qu'on nous croie.
    with Image.open(io.BytesIO(brut)) as relu:
        relu.load()
        dedans = relu.crop((m, m, m + g.canvas_px[0],
                            m + g.canvas_px[1])).convert("RGB").tobytes()
    identique = dedans == attendu
    if not identique:
        raise ValueError("la zone carte de l'epreuve differe de la source : "
                         "refus de livrer une epreuve qui ment")
    rapport = dict(C)
    rapport["pixels_identiques"] = True
    rapport["pixels_compares"] = len(attendu)
    rapport["face"] = "verso" if face == "back" else "recto"
    rapport["legende"] = lignes
    return brut, rapport


# ═════════════════════════════════════════════════════════════════════════════
# LES IMAGES DU VERSO PERSONNALISÉ — `decks/{did}/frame/img_{n}.png`
#
# CETTE PORTE EST UNE JUMELLE, PAS UN APPEL. `cards/type.py` porte la même
# pour ses calques d'image ; P2 ne peut pas l'importer (règle 8, en tête de ce
# fichier : « jamais d'un voisin »), elle est donc RECOPIÉE — et avec elle les
# cinq leçons payées en 3b-T2, qui ne sont pas des politesses :
#
#   1. LA RÉSERVATION. Deux imports qui se croisent (deux Ctrl+V, deux
#      onglets, un dépôt multiple) lisaient le même « prochain numéro » et
#      écrivaient le même fichier. Le numéro n'est pas LU, il est RÉSERVÉ par
#      création exclusive : la création échoue pour tous sauf un.
#   2. LA BOMBE DE PIXELS. Le corps est PESÉ ; ce poids ne dit rien du coût du
#      DÉCODAGE (un demi-mégaoctet peut déclarer 144 millions de pixels). On
#      lit les dimensions dans l'EN-TÊTE et on refuse là.
#   3. LA LISTE BLANCHE AVANT LE DISQUE, dans la fonction qui COMPOSE le
#      chemin — pas seulement chez son appelant.
#   4. LE COMPTEUR MAX+1. Un trou laissé par une suppression manuelle n'est
#      pas repris : `img_2.png` réattribué changerait le dos de toutes les
#      cartes dont le document pointe encore ce nom.
#   5. LE PLAFOND, dit AVANT avec son arithmétique, et RECOMPTÉ après la
#      réservation (deux imports partis ensemble voyaient tous deux « 7 »).
#
# PAS DE ROUTE DE SUPPRESSION, et c'est dit : une image encore référencée par
# un document effacée d'un clic ferait un damier sans rien pour le défaire.
# Le ramassage des images orphelines est une dette CONSIGNÉE du plan 3c.
# ═════════════════════════════════════════════════════════════════════════════
def _frame_files_dir(did: str, create: bool = False) -> pathlib.Path:
    """`decks/<did>/frame/`. `deck_dir` porte déjà le double garde-fou (motif
    PUIS confinement) : on ne le refait pas, on s'appuie dessus."""
    d = deck_dir(did, create=create) / "frame"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _deck_or_404(did: str, create: bool = False) -> pathlib.Path:
    """Le dossier d'images, pour un jeu QUI EXISTE DÉJÀ. L'existence est
    vérifiée SANS `create` — sinon le contrôle se répondrait à lui-même et un
    identifiant bien formé mais inconnu ferait naître un jeu vide."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    try:
        base = deck_dir(did)
    except ValueError:
        raise HTTPException(400, "Identifiant de jeu invalide")
    if not base.is_dir():
        raise HTTPException(404, "Jeu introuvable")
    return _frame_files_dir(did, create=create)


def _next_img_index(d: pathlib.Path) -> tuple[int, int]:
    """(numéro libre, nombre d'images existantes). MAX + 1 : les trous laissés
    par une suppression manuelle ne sont pas repris."""
    hauts, n = 0, 0
    if d.is_dir():
        for p in d.iterdir():
            if BACK_IMG_NAME_RE.fullmatch(p.name) and p.is_file():
                n += 1
                hauts = max(hauts, int(p.name[4:-4]))
    return hauts + 1, n


def _plein(n: int) -> HTTPException:
    return HTTPException(
        409, f"Ce jeu porte déjà {BACK_IMAGES_MAX} images de verso "
             f"(actuellement {n}), le maximum. Réutilisez une image déjà "
             f"importée sur un calque du dos, ou supprimez-en une du dossier "
             f"du jeu.")


def _decode_bounded(raw: bytes):
    """Les octets reçus, décodés et ramenés dans leurs bornes — ou un refus.

    L'ORDRE EST LE FOND DE L'AFFAIRE : `Image.open` n'a pas encore décodé une
    seule ligne quand il publie `size`. On refuse LÀ, et le décodage ne
    commence que pour ce qui a passé la porte."""
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    if w * h > IMG_MAX_PIXELS:
        raise HTTPException(
            413, f"Image trop grande : {w} x {h} pixels, soit "
                 f"{w * h // 1048576} millions de pixels pour un maximum de "
                 f"{IMG_MAX_PIXELS // 1048576}. Réduisez-la avant de l'importer.")
    try:
        img.load()
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    # RGBA gardé : un calque de verso se pose PAR-DESSUS l'image de fond, sa
    # transparence porte donc — contrairement à la matière de P6, qui est un
    # fond et n'a rien sous elle.
    img = img.convert("RGBA")
    if max(img.size) > MAX_IMPORT_PX:
        k = MAX_IMPORT_PX / float(max(img.size))
        img = img.resize((max(1, round(img.size[0] * k)),
                          max(1, round(img.size[1] * k))), Image.LANCZOS)
    return img


def _store_back_image(did: str, raw: bytes) -> dict:
    """Décode, borne, RÉSERVE un numéro, écrit — dans cet ordre."""
    d = _deck_or_404(did, create=True)
    libre, n = _next_img_index(d)
    # LE PLAFOND EST TENU DEUX FOIS, et un mutant l'a prouvé : retirer CETTE
    # garde-ci seule ne fait rougir aucun test — le recompte d'après la
    # réservation (plus bas) tient encore la ligne. Elle n'est donc pas la
    # défense, elle est la POLITESSE : elle refuse AVANT de décoder une image
    # de 64 Mo pour rien. Le mutant qui relève la CONSTANTE, lui, meurt.
    if n >= BACK_IMAGES_MAX:
        raise _plein(n)
    img = _decode_bounded(raw)
    tmp = d / f"img_{libre}.{uuid.uuid4().hex}.tmp"
    try:
        img.save(tmp, format="PNG", optimize=False)
        # LA RÉSERVATION : on essaie les numéros à partir du premier libre
        # CONNU ; une collision veut dire qu'un autre import vient de le
        # prendre, et on passe au suivant.
        for k in range(BACK_IMAGES_MAX * 2 + 4):
            name = f"img_{libre + k}.png"
            final = d / name
            try:
                fd = os.open(str(final), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                continue
            except OSError as e:
                raise HTTPException(
                    409, f"Écriture impossible dans le dossier du jeu : "
                         f"{e.strerror}")
            os.close(fd)
            # LE PLAFOND, RECOMPTÉ APRÈS LA RÉSERVATION : deux imports partis
            # ensemble sur un jeu à 7 images auraient tous deux vu « 7 ». Le
            # compte se refait sur les numéros JUSQU'AU NÔTRE — le premier
            # arrivé garde sa place, le surnuméraire rend la sienne.
            avant_nous = sum(1 for p in d.iterdir()
                             if BACK_IMG_NAME_RE.fullmatch(p.name)
                             and p.is_file() and int(p.name[4:-4]) <= libre + k)
            if avant_nous > BACK_IMAGES_MAX:
                final.unlink(missing_ok=True)
                raise _plein(avant_nous - 1)
            try:
                os.replace(str(tmp), str(final))
            except OSError as e:
                # LE JALON NE SURVIT PAS À SON ÉCHEC : créé vide pour réserver
                # le nom, le laisser ferait compter — et servir — un PNG de
                # zéro octet.
                final.unlink(missing_ok=True)
                raise HTTPException(
                    409, f"Écriture impossible dans le dossier du jeu : "
                         f"{e.strerror}")
            return {"file": name, "src": "img:" + name,
                    "px": [img.size[0], img.size[1]],
                    "bytes": final.stat().st_size,
                    "n": _next_img_index(d)[1], "max": BACK_IMAGES_MAX}
        raise HTTPException(
            409, f"Aucun numéro libre pour une image de verso dans ce jeu "
                 f"(maximum {BACK_IMAGES_MAX}).")
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:                       # pragma: no cover - disque tenu
            pass


def _read_back_image(did: str, name: str) -> bytes | None:
    """Les octets d'une image de verso, ou `None`.

    LA CEINTURE EST ICI AUSSI, et pas seulement chez l'appelant : cette
    fonction COMPOSE un chemin, et la doctrine du dépôt (`deck_dir` : motif
    PUIS confinement) veut que le garde-fou vive là où le chemin naît. Un
    ramasse-miettes ou un écran qui l'appellerait en direct n'hérite de rien
    de la route."""
    if not is_valid_did(did) or not BACK_IMG_NAME_RE.fullmatch(name or ""):
        return None
    try:
        p = _frame_files_dir(did) / name
        if not p.is_file():
            return None
        data = p.read_bytes()
        # UN JALON DE RÉSERVATION N'EST PAS UNE IMAGE. La réservation crée le
        # nom final VIDE (`O_CREAT|O_EXCL`) avant d'y déplacer les octets ;
        # entre les deux il y a une fenêtre qu'une panne dure du processus
        # traverse. Mesuré avant correction : `GET .../img_1.png` rendait
        # **200, zéro octet, `Cache-Control: immutable`** — un aperçu mettait
        # un fichier vide en cache pour un an. Zéro octet vaut donc ABSENT.
        # (Le NUMÉRO, lui, reste pris : c'est ce que le plafond protège, et le
        # compteur MAX+1 ne réattribue jamais. Le refus dit le geste.)
        return data or None
    except (OSError, ValueError):
        return None


# ═════════════════════════════════════════════════════════════════════════════
# ROUTES — chemins RELATIFS à /api/cards/{did}/frame
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/catalog")
async def get_catalog(did: str):
    """Le catalogue des cadres. Volontairement servi même si le jeu n'existe
    plus : un menu qui s'éteint parce qu'un deck a été supprimé est pire
    qu'inutile — l'écran doit pouvoir proposer un cadre en toutes
    circonstances."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    return {"catalog": catalog()}


# ── LES MODÈLES D'IMAGE ET LEUR TARIF (spec §6.3) ────────────────────────────
# « la liste vient de `GET /image-models` enrichie des tarifs, patron
# `face.py:ai-models` ; JAMAIS de liste recopiée à l'écran ».
#
# CE QUI EST IMPORTÉ, ET POURQUOI CE N'EST PAS LA PIÈCE VOISINE. La règle 8
# interdit à une pièce d'importer le module d'une autre : `face.py` porte le
# même patron, on ne l'importe pas — on importe ce qu'il importe, la table de
# tarifs de l'APPLICATION (`app.services.pricing`) et la liste réellement
# servie (`app.api.routes.list_image_models`). Une liste recopiée ici
# dériverait de celle de l'application au premier ajout, et le menu proposerait
# un modèle que le backend ne sait pas servir.
#
# Un modèle absent de la table de tarifs rend `usd_par_image = null` et l'écran
# écrit « tarif non tabulé » : `pricing.estimate` retombe en silence sur le
# tarif de FLUX pour un identifiant inconnu, et afficher ce repli serait
# annoncer un prix qui n'est pas celui du modèle choisi.
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
    """Les fournisseurs d'image dont la clé est enregistrée. Sert UNIQUEMENT de
    repli quand la route de l'application ne répond pas : sans lui, un incident
    de base de données ferait afficher « aucun modèle » alors que les clés sont
    là — un écran qui se trompe dans le sens rassurant."""
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

    Une liste VIDE veut dire « aucune clé enregistrée », et l'écran doit le
    dire AVANT le clic plutôt que de laisser l'utilisateur découvrir l'échec
    après."""
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
        models = [{"id": mid, "label": spec["label"],
                   "provider": spec["provider"], "note": ""}
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


@router.post("/metrics")
async def post_metrics(did: str, body: dict | None = None):
    """Les millimètres du cadre, convertis en pixels de toile par la règle du
    domaine. C'est ce que l'écran confronte à son propre calcul."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    from . import core as core_mod          # import paresseux (style routes.py)
    if core_mod.read_deck(did) is None:
        raise HTTPException(404, "Jeu introuvable")
    b = body if isinstance(body, dict) else {}
    try:
        # `corner_mm` n'est PAS re-validé ici : c'est le rayon de la DÉCOUPE,
        # il appartient au widget de format du CORE. `contract.geom` porte ses
        # bornes ; les re-déclarer plus serrées ferait échouer la vérification
        # de l'écran sur un document parfaitement légal.
        g = geom(
            str(b.get("fmt") or "poker_eu"),
            _int(b.get("dpi"), 300, "La définition"),
            b.get("bleed_mm"), b.get("safe_mm"), b.get("corner_mm"),
        )
        line = _len(b.get("line_mm"), DEFAULTS["line_mm"],
                    LIMITS["line_mm"][0], LIMITS["line_mm"][1],
                    "L'épaisseur du filet")
        gap = _len(b.get("gap_mm"), DEFAULTS["gap_mm"], LIMITS["gap_mm"][0],
                   LIMITS["gap_mm"][1], "L'écart entre filets")
        edge = _len(b.get("edge_mm"), DEFAULTS["edge_mm"],
                    LIMITS["edge_mm"][0], LIMITS["edge_mm"][1],
                    "Le retrait du filet")
        inner = _len(b.get("inner_mm"), DEFAULTS["inner_mm"],
                     LIMITS["inner_mm"][0], LIMITS["inner_mm"][1],
                     "La marge intérieure")
        win = _win_of(b.get("window"), g)
        seal = seal_of(b.get("seal"))
    except ValueError as e:
        raise HTTPException(400, str(e))

    fam = b.get("family")
    if fam is not None and fam != "none" and \
            fam not in [f["id"] for f in FAMILIES]:
        raise HTTPException(
            400, "Famille de cadre inconnue: %r. Familles admises: %s"
            % (fam, ", ".join(f["id"] for f in FAMILIES)))

    return {"metrics": frame_metrics(g, line, gap, edge, inner, win, seal),
            "geom": g.to_dict()}


@router.post("/occupancy")
async def post_occupancy(did: str, body: dict | None = None):
    """Le plan d'occupation et le compteur de recouvrements. L'écran calcule
    le même et confronte : deux placements différents, ce serait un aperçu qui
    ment sur le fichier."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    b = body if isinstance(body, dict) else {}
    try:
        g = geom(
            str(b.get("fmt") or "poker_eu"),
            _int(b.get("dpi"), 300, "La définition"),
            b.get("bleed_mm"), b.get("safe_mm"), b.get("corner_mm"),
        )
        f = b.get("frame") if isinstance(b.get("frame"), dict) else {}
        f = dict(f)
        f["inner_mm"] = _len(f.get("inner_mm"), DEFAULTS["inner_mm"],
                             LIMITS["inner_mm"][0], LIMITS["inner_mm"][1],
                             "La marge intérieure")
        f["edge_mm"] = _len(f.get("edge_mm"), DEFAULTS["edge_mm"],
                            LIMITS["edge_mm"][0], LIMITS["edge_mm"][1],
                            "Le retrait du filet")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"occupancy": occupancy(g, f, b.get("slots"))}


@router.post("/stamp")
async def post_stamp(did: str, request: Request, fmt: str = "poker_eu",
                     dpi: int = 300, bleed_mm: float | None = None,
                     safe_mm: float | None = None, corner_mm: float = 3.0,
                     face: str = "front", collisions: int = 0,
                     note: str = "", rgb: int = 1):
    """Reçoit le PNG rendu par le moteur unique, VÉRIFIE que sa taille est
    bien `geom.canvas_px`, et le rend estampillé `pHYs` + `tEXt`.

    La vérification n'est pas une politesse : sans elle, cette route serait un
    moyen d'écrire « 300 DPI » sur n'importe quel nombre de pixels — exactement
    le badge menteur qu'on cherche à rendre impossible.
    """
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    try:
        g = geom(str(fmt or "poker_eu"), _int(dpi, 300, "La définition"),
                 bleed_mm, safe_mm, corner_mm)
    except ValueError as e:
        raise HTTPException(400, str(e))
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Aucun octet reçu : le PNG à estampiller "
                                 "doit être le corps de la requête")
    if len(raw) > 96 * 1024 * 1024:
        raise HTTPException(400, "PNG trop lourd (plus de 96 Mo)")
    try:
        w, h = png_size(raw)
        png_chunks(raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if [w, h] != [g.canvas_px[0], g.canvas_px[1]]:
        raise HTTPException(
            400, "La toile reçue fait %dx%d px alors que %s a %d DPI en fait "
                 "%dx%d : refus d'estampiller une définition fausse."
                 % (w, h, g.fmt, g.dpi, g.canvas_px[0], g.canvas_px[1]))
    # Le quatrième canal, AVANT l'estampillage (sans quoi le ré-encodage
    # emporterait pHYs et tEXt avec lui).
    deja = png_texts(raw).get("Alpha", "")
    if int(rgb or 0):
        raw, alpha_note = png_drop_constant_alpha(raw)
        # Second passage sur un fichier déjà converti : la mesure d'origine
        # n'est plus possible (le canal n'existe plus). On garde la mention
        # écrite au premier passage — sans quoi estampiller deux fois
        # rendrait deux fichiers différents.
        if deja and alpha_note.startswith("aucun canal alpha"):
            alpha_note = deja
        try:
            w2, h2 = png_size(raw)
            if [w2, h2] != [g.canvas_px[0], g.canvas_px[1]]:
                raise ValueError("taille perdue")
        except ValueError:
            raise HTTPException(500, "conversion RGB incoherente : refus de "
                                     "livrer un fichier non verifie")
    else:
        alpha_note = "conversion RGB desactivee par la requete (rgb=0)"
    # `collisions` est DECLARE par le moteur de rendu, pas recalcule ici : la
    # route ne reçoit pas les slots. On le dit, plutôt que de le faire passer
    # pour une mesure du fichier — ce que seule la géométrie ci-dessus est.
    extra = {"Face": "verso" if face == "back" else "recto",
             "Collisions": "%d recouvrement(s) de mention, plan d'occupation "
                           "du moteur de rendu" % max(0, int(collisions))}
    if note:
        extra["Comment"] = note
    extra["Alpha"] = alpha_note
    try:
        out = png_stamp(raw, g.dpi, stamp_texts(g, extra))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(content=out, media_type="image/png", headers={
        "X-Card-Canvas": "%dx%d" % (g.canvas_px[0], g.canvas_px[1]),
        "X-Card-Ppm": str(dpi_to_ppm(g.dpi)),
        "X-Card-Dpi-Reel": "%.4f" % ppm_to_dpi(dpi_to_ppm(g.dpi)),
        "Content-Disposition": 'attachment; filename="carte.png"',
    })


@router.post("/control")
async def post_control(did: str, request: Request, fmt: str = "poker_eu",
                       dpi: int = 300, bleed_mm: float | None = None,
                       safe_mm: float | None = None, corner_mm: float = 3.0,
                       face: str = "front", margin_mm: float = 10.0):
    """L'ÉPREUVE DE CONTRÔLE : la toile livrée, posée sur du papier, avec de
    VRAIS traits de coupe et des mires — hors du fond perdu, donc hors de
    l'encre. Ce n'est PAS le fichier d'impression, et le fichier retourné le
    dit de lui-même, en clair, dans son `tEXt` et sur sa légende.
    """
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    try:
        g = geom(str(fmt or "poker_eu"), _int(dpi, 300, "La définition"),
                 bleed_mm, safe_mm, corner_mm)
        marge = _len(margin_mm, 10.0, MARGIN_MM[0], MARGIN_MM[1],
                     "La marge de l'épreuve")
    except ValueError as e:
        raise HTTPException(400, str(e))
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Aucun octet reçu : le PNG à contrôler doit "
                                 "être le corps de la requête")
    if len(raw) > 96 * 1024 * 1024:
        raise HTTPException(400, "PNG trop lourd (plus de 96 Mo)")
    try:
        w, h = png_size(raw)
        png_chunks(raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if [w, h] != [g.canvas_px[0], g.canvas_px[1]]:
        raise HTTPException(
            400, "La toile reçue fait %dx%d px alors que %s a %d DPI en fait "
                 "%dx%d : refus de poser des traits de coupe au mauvais endroit."
                 % (w, h, g.fmt, g.dpi, g.canvas_px[0], g.canvas_px[1]))
    try:
        out, rap = build_control_proof(raw, g, marge, face)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except ImportError as e:
        raise HTTPException(503, "Pillow indisponible : %s" % e)
    extra = {
        "Face": rap["face"],
        "ControlProof": "EPREUVE DE CONTROLE - NE PAS IMPRIMER. Marge de "
                        "papier %g mm ajoutee autour de la toile livree ; les "
                        "traits de coupe et les mires sont HORS du fond perdu."
                        % rnd(marge, 2),
        "CropMarks": "coupe a %s px du bord de l'epreuve ; traits traces sur "
                     "%s ; residu d'arrondi %s px ; longueur %d px, epaisseur "
                     "%d px" % (rap["trim_exact"], rap["trim_drawn"],
                                rap["residu_px"], rap["mark_px"],
                                rap["mark_w_px"]),
        "PixelCheck": "zone carte relue apres encodage et comparee a la "
                      "source : %d octets identiques" % rap["pixels_compares"],
        "Comment": "Le fichier d'impression, lui, ne porte AUCUN repere : du "
                   "trait de coupe au bord de toile il n'y a que du fond "
                   "perdu, et un repere y serait de l'encre sous la lame.",
    }
    # La toile de l'épreuve n'est PAS `canvas_px` : `stamp_texts` décrirait la
    # carte, pas le papier. On écrit donc les deux, sans confusion possible.
    textes = stamp_texts(g, extra)
    textes.insert(1, ("ProofCanvas", "%dx%d px - toile livree %dx%d px + %g mm "
                                     "de marge de chaque cote"
                      % (rap["canvas_px"][0], rap["canvas_px"][1],
                         g.canvas_px[0], g.canvas_px[1], rnd(marge, 2))))
    try:
        out = png_stamp(out, g.dpi, textes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(content=out, media_type="image/png", headers={
        "X-Proof-Canvas": "%dx%d" % (rap["canvas_px"][0], rap["canvas_px"][1]),
        "X-Proof-Margin": str(rap["margin_px"]),
        "X-Proof-Trim": ",".join(str(v) for v in rap["trim_drawn"]),
        "X-Proof-Residu": ",".join(str(v) for v in rap["residu_px"]),
        "X-Proof-Pixels": str(rap["pixels_compares"]),
        "Content-Disposition": 'attachment; filename="epreuve-controle.png"',
    })


@router.post("/image")
async def post_back_image(did: str, request: Request):
    """L'image d'un verso personnalisé, importée par l'utilisateur — CORPS BRUT.

    Elle est rangée AVEC LE JEU (`decks/{did}/frame/img_{n}.png`) et non dans
    le navigateur : un dos doit voyager avec sa carte — export, duplication,
    sauvegarde. La duplication de la 3a copie déjà le dossier du jeu, si bien
    qu'un jeu dupliqué arrive avec son verso sans une ligne de plus.

    Le corps est PESÉ avant d'être décodé (seul ordre qui protège la mémoire),
    puis décodé — ce qui refuse du même geste ce qui n'est pas une image —
    puis ramené sous `MAX_IMPORT_PX` de côté."""
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyer une image")
    if len(raw) > IMG_MAX_BYTES:
        raise HTTPException(413, "Image trop lourde (max 64 Mo)")
    return await asyncio.to_thread(_store_back_image, did, raw)


@router.get("/image/{name}")
async def get_back_image(did: str, name: str):
    """L'image d'un verso, telle qu'elle a été rangée.

    LISTE BLANCHE D'ABORD, DISQUE ENSUITE — l'ordre est le fond de l'affaire :
    un motif appliqué APRÈS avoir composé un chemin a déjà laissé le chemin
    exister.

    LES OCTETS SONT LUS ICI, jamais servis par `FileResponse` : celui-ci
    re-stat le fichier au moment de l'ENVOI, donc APRÈS le contrôle — une
    disparition entre les deux y lève RuntimeError, c'est-à-dire un 500 sur
    une pièce qui n'en fait jamais.

    LE CACHE EST PERMIS, et c'est une conséquence du compteur : `img_7.png` ne
    change jamais de contenu (un import écrit `img_8.png`), donc `no-store` ne
    protégerait de rien et coûterait un aller-retour à chaque frame de
    l'aperçu — le peintre du verso en demande une par rendu."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    # `fullmatch` et non `match` : le `$` accepte un saut de ligne final, et
    # ce nom vient d'une URL.
    if not BACK_IMG_NAME_RE.fullmatch(name or ""):
        raise HTTPException(
            400, f"Nom d'image invalide : {name!r} — les images de verso "
                 f"s'appellent « img_1.png », « img_2.png », etc.")
    data = await asyncio.to_thread(_read_back_image, did, name)
    if data is None:
        raise HTTPException(404, f"Aucune image {name} dans ce jeu")
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})
