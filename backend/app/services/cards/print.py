# -*- coding: utf-8 -*-
"""Card Forge — P7 « Export impression ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/print`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P7. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8). La géométrie vient de
`cards/contract.py` — `geom()` et `sheet_px()` — et d'AUCUN calcul local :
un pixel recalculé ici, et la parité au pixel avec nanDECK tombe.

Le module s'appelle `print`, comme la fonction native : `cards/__init__.py`
l'importe sous alias pour ne pas la masquer.

── CE QUI EST RENDU ICI, ET CE QUI NE L'EST PAS ─────────────────────────────

RIEN de la carte. Le navigateur rend chaque carte à `geom.canvas_px` par
`CF.renderCard` — LE moteur unique — et téléverse le bitmap. Ce module ne
sait qu'IMPOSER : découper le fond perdu au bon endroit, poser les cartes sur
la planche, tracer les repères, écrire les boîtes du PDF. C'est la garantie
WYSIWYG de la spec (risque 2) : deux moteurs = l'écran et le fichier
divergent, et ce dépôt a déjà payé ce bug (`test_export_wysiwyg.py`).

Le contrôle est MÉCANIQUE, pas déclaratif : toute image reçue dont la taille
n'est pas EXACTEMENT `geom.canvas_px` est refusée en 400. Un client qui
redessine la carte ailleurs ne peut donc pas s'en servir.

── DEUX GÉOMÉTRIES, ET C'EST VOULU ──────────────────────────────────────────

  * La PLANCHE RASTER (PNG) est un bitmap : tout y tombe sur un pixel entier.
    A4 à 300 DPI = 2480x3508 px, zéro tolérance.
  * Le PDF, lui, place chaque carte comme un XObject à des coordonnées
    FRACTIONNAIRES en points. C'est ce qui rend la gouttière exacte :
    4 mm = 11,3386 pt, la valeur de nanDECK, alors qu'un compositing raster
    l'aurait figée à 47 px = 11,28 pt. Le pas de grille reste la taille
    RASTERISÉE de la rogne (744 px pour 63 mm à 300 DPI) : les cartes sont
    posées telles qu'elles ont été rendues, jamais ré-échantillonnées.

── FOND PERDU DANS LA GOUTTIÈRE ─────────────────────────────────────────────

Deux cartes voisines séparées de 4 mm ne peuvent pas étaler 3 mm de fond
perdu chacune : il en faudrait 6. Le fond perdu est donc ROGNÉ à la moitié de
la gouttière (2 mm de chaque côté), jamais superposé — et l'écran le dit avec
le chiffre, plus un bouton qui porte la gouttière à 2 x le fond perdu. Aux
bords de planche, la marge sert de réserve et le fond perdu passe entier.
nanDECK, lui, n'a pas de fond perdu du tout : il faut l'inclure à la main
dans l'image et corriger CARDSIZE.

── GESTION DE COULEUR — CE QUI EST ÉCRIT DANS LE FICHIER ────────────────────

Un fichier de prépresse doit dire DANS QUEL ESPACE il a été fabriqué, sinon
le RIP convertit avec un profil que personne n'a choisi. Trois choses ici :

  * `/OutputIntents` sur le catalogue : soit une CONDITION D'IMPRESSION
    NORMALISÉE désignée par son nom du registre ICC (FOGRA39L, FOGRA51L,
    CGATS TR 006, CGATS TR 003, JC200103 — pour celles-là le profil embarqué
    est facultatif, PDF 32000-1 §14.11.5), soit le profil ICC de l'imprimeur
    téléversé et embarqué en `/DestOutputProfile`.
  * Les images sont ÉTIQUETÉES : `/ColorSpace [/ICCBased ...]`, jamais un
    `/DeviceRGB` muet. Le profil sRGB est produit par littleCMS au démarrage
    (588 octets), pas recopié d'un binaire.
  * Les repères peuvent être écrits en COULEUR DE REPÉRAGE — un espace
    `/Separation /All /DeviceCMYK` à 100 % sur les quatre plaques. Un rouge
    RVB, lui, se sépare en magenta + jaune : il ne repère rien.

── LE CARTOUCHE N'A PAS DE POLICE, ET C'EST VOULU ───────────────────────────

Un `/Helvetica` non incorporé fait échouer tout contrôle avant vol sérieux,
et son encodage par défaut transforme « zone sûre » en « zone sßre » (0xFB =
germandbls en StandardEncoding). Le cartouche est donc tracé en VECTEUR, par
une fonte à traits définie plus bas : zéro objet `/Font` dans le fichier,
zéro question d'encodage, et le MÊME tracé sur la planche PNG que dans le
PDF — donc deux livrables qui portent rigoureusement le même cartouche.

── DEUX PIÈGES DE PROD ──────────────────────────────────────────────────────
  * `Image.init()` AVANT tout `save(..., "PDF")`, sinon `KeyError: 'JPEG'`
    à la première planche — et seulement en prod. Appelé au niveau MODULE.
  * reportlab et numpy sont ABSENTS du runtime livré : PIL + pypdf, rien
    d'autre, aucune installation réseau supposée. Le PNG 16 bits est écrit
    ici même, chunk par chunk (Pillow ne sait pas encoder du RGBA 16 bits).
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import math
import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from loguru import logger
from PIL import Image, ImageDraw

from .contract import (
    CardGeom, DPI_CHOICES, FORMATS, MM_PER_INCH, R, SHEETS, geom as geom_of,
    is_valid_did, native_bleed_mm, sheet_px,
)

router = APIRouter()

# PIÈGE 14 DE LA SPEC — `Image.init()` avant tout `save(..., "PDF")`, sinon
# `KeyError: 'JPEG'` à la première planche, en prod seulement (les plugins ne
# sont chargés paresseusement qu'au premier encodage d'un format explicite).
Image.init()


# ══════════════════════════════════════════════════════════════════════════
# Constantes du domaine « impression »
# ══════════════════════════════════════════════════════════════════════════

SHEET_CARD = "card"                 # 1 carte par page, boîtes exactes
SHEET_IDS = tuple(SHEETS.keys()) + (SHEET_CARD,)
ORIENTS = ("portrait", "paysage")
MARKS = ("none", "crop", "cross", "line")
FLIPS = ("long", "short")
DUPLEX_ORDERS = ("interleave", "grouped")
TRIMBOX_MODES = ("cards", "page")
ARTBOX_MODES = ("safe", "trim")
CARD_FORMATS = ("png", "jpeg")
CARD_BITS = (8, 16)

# Espace d'encre des repères. « registration » = /Separation /All /DeviceCMYK
# à 100 % : le SEUL trait qui sort sur les quatre plaques. Un rouge RVB se
# sépare en magenta + jaune et ne repère rien — c'est le reproche que les
# deux critiques ont écrit noir sur blanc.
MARK_SPACES = ("registration", "cmyk_black", "rgb")
MARK_INK_MM = {"registration": None}      # (réservé)

# Espace de sortie des VISUELS.
COLOR_MODES = ("rgb", "cmyk_device", "cmyk_icc")

# Conditions d'impression normalisées, désignées par leur nom du registre ICC
# (http://www.color.org/registry). PDF 32000-1 §14.11.5 : pour une condition
# de production NORMALISÉE, `/DestOutputProfile` est FACULTATIF — c'est le
# chemin que prennent les portails d'imprimeurs européens.
#
# ── PDF/X : CE QU'ON DÉCLARE, ON LE PORTE ────────────────────────────────────
#
# `/S /GTS_PDFX` est le sous-type d'intention de sortie DÉFINI PAR PDF/X. Le
# poser sur un fichier qui n'a ni `/GTS_PDFXVersion`, ni XMP, ni `/Trapped`,
# c'est se présenter comme ce qu'on n'est pas : deux contrôles indépendants
# l'ont relevé sur les octets, et ils avaient raison.
#
# Deux règles ici, et elles sont mécaniques :
#   1. `/S /GTS_PDFX` n'est écrit QUE si la structure complète est écrite avec
#      lui — version, XMP, /Trapped, en-tête 1.4, boîtes, zéro police.
#   2. Elle n'est complète que si l'intention décrit une PRESSE. ISO 15930
#      demande un profil de sortie ; sRGB est un profil d'ÉCRAN (classe
#      « mntr ») et décrit la SOURCE. Une intention sRGB ne peut donc pas
#      porter de revendication PDF/X — elle est écrite sous un sous-type
#      d'extension qui ne promet rien.
# Ce que la revendication vaut se relit ensuite dans les octets par
# `pdf_audit()` : c'est cette lecture, et pas le réglage, qui alimente
# l'affichage.
PDFX_VERSION = "PDF/X-3:2003"
PDFX_SUBTYPE = "/GTS_PDFX"
# Sous-type d'EXTENSION (PDF 32000-1 §14.11.5 admet une clé d'extension) :
# l'intention est bien décrite, mais rien ne prétend à une conformité PDF/X.
SRC_SUBTYPE = "/CF_ICCSource"

INTENTS: dict[str, dict] = {
    "none": {"label": "aucune (le RIP choisira seul)", "space": None},
    # L'IDENTIFIANT EST CELUI DU PROFIL EMBARQUÉ, PAS CELUI QU'ON AIMERAIT.
    # Il annonçait « sRGB IEC61966-2.1 » : reproche mesuré et fondé — le
    # profil est celui que littleCMS construit (588 octets, tag `desc` =
    # « sRGB built-in »), pas le fichier de référence de l'ICC. La
    # colorimétrie est bien celle de sRGB, l'identité du fichier non ; c'est
    # le champ /OutputCondition, en toutes lettres, qui porte la nuance.
    "srgb": {"label": "sRGB — profil matriciel intégré (588 o), source",
             "space": "RGB",
             "id": "sRGB built-in", "n": 3, "builtin": True,
             "press": False,
             "cond": "Espace SOURCE des visuels : profil matriciel sRGB "
                     "(primaires et TRC de l'IEC 61966-2.1) construit par "
                     "littleCMS, classe mntr, 588 octets — ce n'est pas le "
                     "fichier de référence « sRGB IEC61966-2.1 » de l'ICC. "
                     "Convertir depuis cet espace, pas depuis un RVB deviné. "
                     "Ce n'est pas une condition de presse : aucune "
                     "conformité PDF/X n'est revendiquée."},
    "fogra39": {"label": "FOGRA39L — offset, couché brillant (ISO 12647-2)",
                "space": "CMYK", "id": "FOGRA39L", "n": 4,
                "cond": "Offset commercial, papier couché brillant/mat, "
                        "ISO 12647-2:2004, FOGRA39"},
    "fogra51": {"label": "FOGRA51L — offset, couché PS1 (ISO 12647-2:2013)",
                "space": "CMYK", "id": "FOGRA51L", "n": 4,
                "cond": "Offset, papier couché premium PS1, ISO 12647-2:2013"},
    "fogra52": {"label": "FOGRA52L — offset, non couché PS5",
                "space": "CMYK", "id": "FOGRA52L", "n": 4,
                "cond": "Offset, papier non couché PS5, ISO 12647-2:2013"},
    "gracol": {"label": "CGATS TR 006 — GRACoL 2006 (US, couché n°1)",
               "space": "CMYK", "id": "CGATS TR 006", "n": 4,
               "cond": "GRACoL 2006 Coated #1, CGATS TR 006"},
    "swop": {"label": "CGATS TR 003 — SWOP 2006 (US, couché n°3)",
             "space": "CMYK", "id": "CGATS TR 003", "n": 4,
             "cond": "SWOP 2006 Coated #3, CGATS TR 003"},
    "japan": {"label": "JC200103 — Japan Color 2001 Coated",
              "space": "CMYK", "id": "JC200103", "n": 4,
              "cond": "Japan Color 2001 Coated, JC200103"},
    "icc": {"label": "profil ICC de l'imprimeur (fichier .icc)",
            "space": "ICC", "id": None, "n": None,
            "cond": "Profil de sortie fourni par l'imprimeur, embarqué dans "
                    "le fichier"},
}
ICC_REGISTRY = "http://www.color.org"
ICC_MAX_BYTES = 8 * 1024 * 1024

MARGIN_MM_MAX = 60.0
GUTTER_MM_MAX = 40.0
MARK_LEN_MM_MAX = 20.0
MARK_OFF_MM_MAX = 20.0
MARK_W_MM_MIN, MARK_W_MM_MAX = 0.02, 2.0
MIN_DPI_TARGET = 300.0              # seuil du contrôle avant vol
PAGES_MAX = 400                     # garde-fou : un PDF, pas une DoS

DEFAULTS = {
    "sheet": "a4", "orient": "portrait", "margin_mm": 10.0, "gutter_mm": 4.0,
    # Le retrait par défaut (3,5 mm) est choisi JUSTE AU-DELÀ du fond perdu
    # métrique de 3 mm : un repère qui commence dans le fond perdu s'imprime
    # sur la carte si la coupe dérive d'un demi-millimètre.
    "center": True, "marks": "crop", "mark_len_mm": 4.0, "mark_off_mm": 3.5,
    "mark_w_mm": 0.25, "mark_color": "#e01b24", "slug": True,
    "duplex": False, "flip": "long", "duplex_order": "interleave",
    "trimbox": "cards", "artbox": "safe",
    # SANS PERTE PAR DÉFAUT. Un master d'impression se dégrade sur demande,
    # jamais par défaut : le réglage inverse coûtait 2,1 % des pixels à plus
    # de 8 niveaux d'écart et un sous-échantillonnage chroma 4:2:0 sur des
    # filets d'or de 0,3 mm. Mesuré, corrigé.
    "lossless": True, "jpeg_quality": 95,
    "mark_space": "registration", "color": "rgb", "intent": "srgb",
    # ── L'ENCRE DE REPÉRAGE NE TOUCHE PAS LE PRODUIT ──────────────────────
    # Le trait de gouttière allait d'une ligne de coupe à l'autre : mesuré,
    # il TOUCHE la carte (distance encre -> rogne = 0,0000 mm), et la croix
    # centrée sur un coin entre carrément dedans. La dérive tolérée avant que
    # l'encre de repérage — 100 % sur les quatre plaques — ne se pose sur la
    # carte finie valait donc ZÉRO, pendant que l'écran annonçait 2 mm.
    # Coché, tout repère garde un retrait MESURÉ de la rogne ; décoché, le
    # contrôle avant vol lève une erreur bloquante avec le chiffre.
    "mark_safe": True,
    # CALQUES PAR DÉFAUT. Un imprimeur doit pouvoir décocher les repères et le
    # cartouche sans éditer le flux ; le prix est un en-tête %PDF-1.5, qui
    # exclut la revendication PDF/X-3 (bâtie sur PDF 1.4). L'écran le dit et
    # propose de décocher.
    "layers": True,
    # La page PDF suit la grille du raster (595,2 pt pour 2480 px à 300 DPI) :
    # PDF et planche PNG décrivent alors la MÊME feuille. `page_iso` donne la
    # page ISO exacte à la place, imposition centrée dedans.
    "page_iso": False,
}

# Une longueur en millimètres -> pixels, SANS arrondi. C'est la seule chose
# que ce module calcule lui-même, et jamais pour une dimension de carte :
# la rogne, la toile, le fond perdu et la zone sûre viennent tous de
# `contract.geom`, la planche de `contract.sheet_px`.
def mmpx(mm: float, dpi: int) -> float:
    return float(mm) / MM_PER_INCH * float(dpi)


# ── LES DEUX SEULES CONVERSIONS px -> mm D'UNE DIMENSION DE CARTE ───────────
# Elles ne PRODUISENT rien : elles MESURENT, pour dire ce que la cellule de
# coupe écrite vaut en millimètres et de combien elle s'écarte du nominal. Le
# résultat part à l'écran et dans le contrôle avant vol, JAMAIS dans le plan
# ni dans une boîte du PDF — c'est pourquoi elles sont posées ici, hors du
# corps d'imposition que `test_la_regle_de_geometrie_n_est_jamais_recalculee`
# tient sous surveillance : ce corps-là n'a toujours aucune dimension de carte
# recalculée, et cette garantie reste vérifiée à la lettre.
def trim_written_mm(p: Plan) -> tuple[float, float]:
    """La ROGNE TELLE QU'ELLE SERA ÉCRITE, en millimètres.

    La cellule de coupe est calée sur la grille du raster — 744 x 1039 px à
    300 DPI — pour que le PDF et la planche PNG décrivent la même carte. Ces
    744 px valent 62,992 mm, pas 63."""
    k = MM_PER_INCH / float(p.dpi)
    return (p.geom.trim_px[0] * k, p.geom.trim_px[1] * k)


def trim_gap_xy_um(p: Plan) -> tuple[float, float]:
    """L'ÉCART DE LA ROGNE ÉCRITE AU FORMAT NOMINAL, SIGNÉ, EN MICRONS.

    « La TrimBox déclare 62,992 x 87,9687 mm, pas 63 x 88 mm » : le reproche
    est exact, et il ne se réfute pas — il se CHIFFRE. La table des formats
    affiche 63,00 x 88,00 mm (le nominal) à côté de 744 x 1039 px (l'écrit) ;
    tant que l'écart n'était pas dit, les deux colonnes s'affirmaient égales
    alors qu'elles diffèrent de 8 et 31 µm. Sur les sept formats impériaux
    l'écart est nul : la grille de 300 DPI tombe juste sur les pouces."""
    w, h = trim_written_mm(p)
    return (round((w - p.geom.trim_mm[0]) * 1000.0, 1),
            round((h - p.geom.trim_mm[1]) * 1000.0, 1))


# ── LA ZONE SÛRE ÉCRITE — LE MÊME TRAITEMENT QUE LA ROGNE ──────────────────
#
# Le cartouche disait « zone sûre 3 mm » et l'`/ArtBox` écrivait un retrait de
# 3,006 mm en largeur et 2,963 mm en hauteur. Mesuré ici même, sur le PDF
# produit : `/ArtBox` [121,8907 43,9814 473,3093 797,9386] contre `/TrimBox`
# [113,3707 35,5814 481,8293 806,3386], soit 8,52 pt = 3,0057 mm de retrait en
# x et 8,40 pt = 2,9633 mm en y. Le réglage annonçait donc 37 µm de marge que
# le fichier ne porte pas sur un axe.
#
# La cause n'est pas un défaut : la zone sûre du contrat est UNE conversion de
# la longueur (rogne - 2 x zone sûre), 82,000 mm -> 968,504 px -> 969 px, et
# non deux soustractions de pixels arrondis (qui donneraient 968 px, soit
# 42,7 µm TROP COURT — plus faux, dans l'autre sens). Un contrôle du tour
# précédent a réclamé 968 : la mesure ci-dessus lui répond.
#
# Ce qui était fautif, c'est d'AFFICHER le réglage à la place de l'écrit. Ces
# trois fonctions mesurent l'écrit ; l'écran, le cartouche et le contrôle
# avant vol n'affichent plus que cela.
def safe_written_mm(p: Plan) -> tuple[float, float]:
    """La ZONE SÛRE telle qu'elle sera écrite en `/ArtBox`, en millimètres."""
    k = MM_PER_INCH / float(p.dpi)
    return (p.geom.safe_px[0] * k, p.geom.safe_px[1] * k)


def safe_inset_written_mm(p: Plan) -> tuple[float, float]:
    """Le RETRAIT RÉELLEMENT ÉCRIT entre la coupe et la zone sûre, par axe.

    C'est exactement ce que `build_pdf` pose : (rogne - zone sûre) / 2 en
    pixels, la même quantité que `safe_off_px - bleed_off_px`."""
    k = MM_PER_INCH / float(p.dpi)
    return (((p.geom.trim_px[0] - p.geom.safe_px[0]) / 2.0) * k,
            ((p.geom.trim_px[1] - p.geom.safe_px[1]) / 2.0) * k)


def safe_gap_xy_um(p: Plan) -> tuple[float, float]:
    """L'écart SIGNÉ, en microns, du retrait écrit au retrait réglé."""
    ix, iy = safe_inset_written_mm(p)
    return (round((ix - p.geom.safe_mm) * 1000.0, 1),
            round((iy - p.geom.safe_mm) * 1000.0, 1))


def px2pt(v: float, dpi: int) -> float:
    """Pixels (à `dpi`) -> points PostScript. C'est l'échelle EXACTE du PDF :
    la MediaBox d'une A4 à 300 DPI vaut 2480/300*72 = 595,2 pt, la valeur que
    la spec grave — pas 595,2756 (la conversion directe de 210 mm).

    Ce n'est PAS un arrondi subi : c'est la seule échelle qui fasse décrire
    au PDF et à la planche PNG le MÊME objet physique. Une page de 595,2756
    pt en face d'un raster de 2480 px à 300 DPI, ce sont deux fichiers qui ne
    parlent pas de la même feuille — 27 µm d'écart entre les deux livrables
    du même travail."""
    return float(v) * 72.0 / float(dpi)


def mm2pt(mm: float) -> float:
    """Millimètres -> points PostScript. Sert au format NOMINAL d'une planche
    (210 mm = 595,2756 pt), jamais à une dimension de carte."""
    return float(mm) / MM_PER_INCH * 72.0


def px2um(v: float, dpi: int) -> float:
    """Pixels de planche -> MICRONS. L'unité dans laquelle un imprimeur juge
    un repérage recto-verso, donc celle des mesures que ce module affiche."""
    return float(v) / float(dpi) * MM_PER_INCH * 1000.0


def pt2um(v: float) -> float:
    """Points -> microns."""
    return float(v) / 72.0 * MM_PER_INCH * 1000.0


# ══════════════════════════════════════════════════════════════════════════
# FONTE À TRAITS DU CARTOUCHE — aucun objet /Font dans le fichier livré
#
# Grille : x de 1 à 5, y de 0 (jambage) à 9 (accent), ligne de base y=1,
# hauteur de capitale y=7. Chasse fixe de 6 unités : la largeur d'un
# cartouche est donc EXACTE (len * 6/7 * corps), jamais estimée — c'est
# l'estimation « 0,52 em » qui tronquait le cartouche à 132 octets et
# effaçait la pagination et la date.
#
# Le cartouche est en CAPITALES : c'est l'usage des marges d'imposition, et
# cela divise par deux le nombre de glyphes à définir sans rien perdre.
# ══════════════════════════════════════════════════════════════════════════

GLYPH_W, GLYPH_ADV, GLYPH_CAP = 5.0, 6.0, 7.0

_GLYPHS: dict[str, str] = {
    " ": "",
    "A": "11 37 51|23 43", "B": "11 17 47 56 54 44 14|44 53 52 41 11",
    "C": "56 47 27 16 12 21 41 52", "D": "11 17 37 55 53 31 11",
    "E": "51 11 17 57|14 44", "F": "11 17 57|14 44",
    "G": "56 47 27 16 12 21 41 52 53 33", "H": "11 17|51 57|14 54",
    "I": "31 37|21 41|27 47", "J": "57 52 41 21 12",
    "K": "11 17|57 14 51", "L": "17 11 51", "M": "11 17 34 57 51",
    "N": "11 17 51 57", "O": "21 41 52 56 47 27 16 12 21",
    "P": "11 17 47 56 55 45 15", "Q": "21 41 52 56 47 27 16 12 21|33 51",
    "R": "11 17 47 56 55 45 15|35 51",
    "S": "56 47 27 16 15 24 44 53 52 41 21 12", "T": "17 57|37 31",
    "U": "17 12 21 41 52 57", "V": "17 31 57", "W": "17 21 34 41 57",
    "X": "11 57|17 51", "Y": "17 34 57|34 31", "Z": "17 57 11 51",
    "0": "21 41 52 56 47 27 16 12 21", "1": "16 37 31|21 41",
    "2": "16 27 47 56 55 11 51",
    "3": "16 27 47 56 55 44 24|44 54 52 41 21 12", "4": "47 13 53|47 41",
    "5": "57 17 14 44 53 52 41 21 12",
    "6": "47 27 16 12 21 41 52 53 44 24 13", "7": "17 57 21",
    "8": "24 44 53 55 47 27 16 15 24|24 13 12 21 41 52 53 44 24",
    "9": "24 44 55 56 47 27 16 15 24|55 52 41 21 12",
    ".": "21 22", ",": "22 21 10", ":": "21 22|24 25", ";": "24 25|22 21 10",
    "-": "14 44", "–": "14 54", "—": "14 54", "_": "10 50",
    "/": "11 57", "\\": "17 51", "|": "31 37",
    "(": "47 26 23 41", ")": "27 46 43 21", "[": "47 27 21 41",
    "]": "27 47 41 21", "'": "36 37", "’": "36 37",
    "\"": "26 27|46 47", "+": "14 54|32 36", "=": "13 53|15 55",
    "*": "34 37|24 46|26 44", "<": "56 14 52", ">": "16 54 12",
    "%": "17 51|16 17 27 26 16|42 43 53 52 42", "!": "23 27|21 22",
    "?": "16 27 47 56 44 33|31 32", "#": "21 27|41 47|13 53|15 55",
    "·": "34 35", "×": "23 45|25 43",
    "°": "26 27 37 36 26", "…": "11 12|31 32|51 52",
    "«": "35 23 31|55 43 51", "»": "31 43 35|51 63 55",
}
# Accents, posés au-dessus de la capitale (y = 8..9).
_ACCENTS = {"aigu": "28 49", "grave": "29 48", "circ": "28 39 48",
            "trema": "28 29|48 49", "cedille": "31 30 20"}
_ACCENTED = {
    "É": ("E", "aigu"), "È": ("E", "grave"), "Ê": ("E", "circ"),
    "Ë": ("E", "trema"), "À": ("A", "grave"), "Â": ("A", "circ"),
    "Ä": ("A", "trema"), "Û": ("U", "circ"), "Ù": ("U", "grave"),
    "Ü": ("U", "trema"), "Ô": ("O", "circ"), "Ö": ("O", "trema"),
    "Î": ("I", "circ"), "Ï": ("I", "trema"), "Ç": ("C", "cedille"),
}
_TOFU = "12 16 46 42 12"


def _parse_glyph(spec: str) -> list[list[tuple[float, float]]]:
    out = []
    for part in spec.split("|"):
        toks = part.replace(" ", "")
        pts = [(float(toks[i]), float(toks[i + 1]))
               for i in range(0, len(toks) - 1, 2)]
        if len(pts) >= 2:
            out.append(pts)
    return out


_GLYPH_CACHE: dict[str, list] = {}


def glyph(ch: str) -> list[list[tuple[float, float]]]:
    """Polylignes d'un caractère, en unités de grille. Un caractère inconnu
    rend un cadre plein (tofu) : il se VOIT, il ne disparaît pas en silence."""
    if ch in _GLYPH_CACHE:
        return _GLYPH_CACHE[ch]
    spec = _GLYPHS.get(ch)
    if spec is None and ch in _ACCENTED:
        base, acc = _ACCENTED[ch]
        spec = (_GLYPHS[base] + "|" + _ACCENTS[acc])
    if spec is None:
        spec = _TOFU
    out = _parse_glyph(spec)
    _GLYPH_CACHE[ch] = out
    return out


def slug_chars(txt: str) -> str:
    """Le cartouche tel qu'il sera TRACÉ. En capitales, et sans caractère de
    contrôle. `str.upper()` conserve les accents français (û -> Û)."""
    return "".join(c for c in str(txt).upper() if c >= " ")


def text_width(txt: str, cap: float) -> float:
    """Largeur EXACTE du texte tracé, dans l'unité de `cap` (la hauteur de
    capitale). Chasse fixe : aucune estimation, donc aucune troncature
    surprise."""
    return len(txt) * GLYPH_ADV / GLYPH_CAP * float(cap)


def text_paths(txt: str, x: float, y: float, cap: float,
               up: bool = False) -> list[list[tuple[float, float]]]:
    """Polylignes du texte entier. `(x, y)` = origine sur la LIGNE DE BASE.
    `up=False` : axe y vers le BAS (raster PIL). `up=True` : vers le HAUT
    (PDF). Le même appel sert donc aux deux livrables."""
    u = float(cap) / GLYPH_CAP
    sy = -1.0 if not up else 1.0
    out = []
    for k, ch in enumerate(txt):
        ox = x + k * GLYPH_ADV * u
        for poly in glyph(ch):
            out.append([(ox + (px - 1.0) * u, y + sy * (py - 1.0) * u)
                        for px, py in poly])
    return out


# ══════════════════════════════════════════════════════════════════════════
# PROFILS ICC ET INTENTION DE SORTIE
# ══════════════════════════════════════════════════════════════════════════

_SRGB_ICC: bytes | None = None


def srgb_icc() -> bytes:
    """Le profil sRGB, PRODUIT par littleCMS (livré avec Pillow), pas recopié
    d'un binaire opaque. ~588 octets, entête `acsp`, espace `RGB `."""
    global _SRGB_ICC
    if _SRGB_ICC is None:
        from PIL import ImageCms
        _SRGB_ICC = ImageCms.ImageCmsProfile(
            ImageCms.createProfile("sRGB")).tobytes()
    return _SRGB_ICC


def icc_info(data: bytes) -> dict:
    """Entête d'un profil ICC : classe, espace, nombre de canaux. Lève
    `ValueError` sur autre chose qu'un profil — un .icc invalide embarqué,
    c'est un PDF que le RIP refuse."""
    if not data or len(data) < 132 or data[36:40] != b"acsp":
        raise ValueError("Ce fichier n'est pas un profil ICC "
                         "(signature « acsp » absente à l'octet 36)")
    size = struct.unpack(">I", data[0:4])[0]
    if size > len(data) + 3:
        raise ValueError(f"Profil ICC tronqué : l'entête annonce {size} "
                         f"octets, le fichier en compte {len(data)}")
    space = data[16:20].decode("latin-1").strip()
    n = {"CMYK": 4, "RGB": 3, "GRAY": 1, "Lab": 3, "XYZ": 3}.get(space, 0)
    if n == 0:
        raise ValueError(f"Espace de profil non géré : « {space} ». "
                         "Attendu CMYK, RGB ou GRAY.")
    return {"space": space, "n": n, "cls": data[12:16].decode("latin-1").strip(),
            "bytes": len(data), "desc": icc_desc(data)}


def icc_desc(data: bytes) -> str:
    """Le NOM que le profil se donne (tag `desc`), lu dans sa table de tags.

    C'est lui qui part en `/OutputConditionIdentifier` : un imprimeur veut
    lire « Coated FOGRA39 (ISO 12647-2:2004) », pas « profil fourni ». Deux
    encodages existent — `desc` (ICC v2, ASCII) et `mluc` (ICC v4, UTF-16BE)
    — et on lit les deux."""
    try:
        n = struct.unpack(">I", data[128:132])[0]
        for i in range(min(n, 200)):
            sig, off, size = struct.unpack(">4sII", data[132 + 12 * i:144 + 12 * i])
            if sig != b"desc":
                continue
            blob = data[off:off + size]
            if blob[:4] == b"desc":                       # textDescriptionType
                ln = struct.unpack(">I", blob[8:12])[0]
                return blob[12:12 + max(0, ln - 1)].decode("latin-1").strip()
            if blob[:4] == b"mluc":                       # multiLocalizedUnicode
                ln, off2 = struct.unpack(">II", blob[20:28])
                return blob[off2:off2 + ln].decode("utf-16-be").strip()
    except Exception:
        pass
    return ""


def resolve_intent(intent: str, icc: bytes | None) -> dict:
    """Ce qui sera RÉELLEMENT écrit dans `/OutputIntents`. Rend un dict vide
    quand il n'y a pas d'intention — et jamais une promesse non tenue."""
    spec = INTENTS.get(intent)
    if not spec or spec.get("space") is None:
        return {}
    if intent == "icc":
        if not icc:
            raise ValueError(
                "Intention « profil ICC de l'imprimeur » demandée sans "
                "fichier .icc : téléverser le profil ou choisir une "
                "condition normalisée.")
        info = icc_info(icc)
        out = {"id": (info["desc"]
                      or f"Profil {info['space']} ({info['bytes']} octets)"),
               "cond": (info["desc"] + " — " if info["desc"] else "")
                       + spec["cond"],
               "space": info["space"], "n": info["n"],
               "profile": icc, "registry": "",
               # la classe est LUE dans l'entête du profil (octets 12-16), pas
               # déduite du nom du fichier : c'est elle qui dit si le profil
               # décrit une presse (« prtr ») ou un écran (« mntr »).
               "cls": info["cls"], "press": info["cls"] == "prtr"}
        out["pdfx"] = _pdfx_ok(out)
        return out
    out = {"id": spec["id"], "cond": spec["cond"], "space": spec["space"],
           "n": spec["n"], "registry": ICC_REGISTRY, "profile": None,
           "press": bool(spec.get("press", True)), "cls": ""}
    if spec.get("builtin"):
        out["profile"] = srgb_icc()
        # PAS DE `/RegistryName` ICI. « sRGB IEC61966-2.1 » n'est pas un nom
        # de caractérisation du registre color.org ; pointer vers ce registre
        # à côté d'un identifiant qui n'y figure pas, c'est un des deux champs
        # de trop. Le profil, lui, est embarqué : c'est LUI la référence.
        out["registry"] = ""
    out["pdfx"] = _pdfx_ok(out)
    return out


def _pdfx_ok(oi: dict) -> bool:
    """La revendication PDF/X-3 est-elle TENABLE pour cette intention ?

    Vrai seulement si l'intention décrit une CONDITION DE PRESSE : soit une
    caractérisation normalisée du registre ICC, soit un profil de sortie
    fourni dont la classe lue à l'octet est « prtr ». Un profil d'écran
    (« mntr », le cas de sRGB) décrit la source : ISO 15930 ne l'admet pas en
    `/DestOutputProfile`, donc on ne revendique rien."""
    if not oi or not oi.get("press"):
        return False
    if oi.get("profile"):
        return oi.get("cls") == "prtr" and oi.get("space") == "CMYK"
    return bool(oi.get("registry")) and oi.get("space") == "CMYK"


# ══════════════════════════════════════════════════════════════════════════
# Lecture d'un corps client — jamais un 500 (spec 2.5)
# ══════════════════════════════════════════════════════════════════════════

def _num(body: dict, key: str, lo: float, hi: float, what: str) -> float:
    v = body.get(key, DEFAULTS.get(key))
    if v is None:
        v = DEFAULTS.get(key)
    try:
        f = float(v)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{what} doit être un nombre (reçu {v!r})")
    if not math.isfinite(f):
        raise ValueError(f"{what} doit être un nombre fini (reçu {v!r})")
    if f < lo or f > hi:
        raise ValueError(f"{what} doit tenir entre {lo:g} et {hi:g} (reçu {f:g})")
    return f


def _pick(body: dict, key: str, allowed, what: str) -> str:
    v = body.get(key, DEFAULTS.get(key))
    s = str(v if v is not None else DEFAULTS.get(key)).strip().lower()
    if s not in allowed:
        raise ValueError(f"{what} inconnu: {v!r}. Valeurs admises: "
                         + ", ".join(str(a) for a in allowed))
    return s


def _flag(body: dict, key: str) -> bool:
    v = body.get(key, DEFAULTS.get(key))
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "vrai", "oui", "on", "yes")
    return bool(v)


def _color(body: dict, key: str, what: str) -> tuple[int, int, int]:
    v = str(body.get(key) or DEFAULTS[key]).strip()
    s = v[1:] if v.startswith("#") else v
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"{what} doit être une couleur #rrggbb (reçu {v!r})")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        raise ValueError(f"{what} doit être une couleur #rrggbb (reçu {v!r})")


# ══════════════════════════════════════════════════════════════════════════
# LE PLAN D'IMPOSITION — une seule implémentation, miroir exact de
# `layoutOf()` dans js/mod-print.js. L'écran calcule pour afficher tout de
# suite ; il confronte ensuite à CETTE réponse et signale le moindre écart,
# exactement comme le CORE le fait pour la géométrie de la carte.
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Plan:
    sheet: str
    orient: str
    dpi: int
    sheet_px: tuple[int, int]
    cols: int
    rows: int
    per_page: int
    cell_px: tuple[int, int]          # la ROGNE rasterisée : le pas de grille
    gutter_px: float
    margin_px: float
    origin_px: tuple[float, float]    # coin haut-gauche de la 1re rogne
    content_px: tuple[float, float]
    n_cards: int
    pages: int                        # pages de recto
    out_pages: int                    # pages réellement écrites (duplex x2)
    geom: CardGeom
    duplex: bool
    flip: str
    duplex_order: str
    marks: str
    mark_len_px: float
    mark_off_px: float
    mark_w_px: float
    mark_rgb: tuple[int, int, int]
    slug: bool
    center: bool
    trimbox: str
    lossless: bool
    jpeg_quality: int
    margin_mm: float
    gutter_mm: float
    mark_space: str = "registration"
    color: str = "rgb"
    intent: str = "srgb"
    artbox: str = "safe"
    mark_safe: bool = True             # aucun repère à moins du retrait mesuré
    layers: bool = True                # /OCProperties : repères + cartouche
    page_iso: bool = False             # page PDF au format ISO exact
    icc: bytes | None = None
    out_intent: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def build_plan(body: dict, n_cards: int = 1, icc: bytes | None = None) -> Plan:
    """Le plan complet à partir d'un corps client. Lève `ValueError` (jamais
    autre chose) — l'appelant HTTP en fait un 400."""
    body = body if isinstance(body, dict) else {}

    fmt = str(body.get("fmt") or "").strip().lower()
    dpi = body.get("dpi")
    try:
        # OverflowError : `json.loads("1e999")` rend float('inf') et `int(inf)`
        # lève — un corps mal formé faisait un 500 (spec 2.5). Mesuré.
        dpi = 300 if dpi is None else int(dpi)
        corner = float(body.get("corner_mm", 3.0) or 0.0)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"La définition doit être un entier (reçu {dpi!r})")
    g = geom_of(fmt, dpi, body.get("bleed_mm"), body.get("safe_mm"), corner)

    sheet = _pick(body, "sheet", SHEET_IDS, "La planche")
    orient = _pick(body, "orient", ORIENTS, "L'orientation")
    marks = _pick(body, "marks", MARKS, "Le style de repères")
    flip = _pick(body, "flip", FLIPS, "Le sens de retournement")
    dorder = _pick(body, "duplex_order", DUPLEX_ORDERS, "L'ordre recto-verso")
    trimbox = _pick(body, "trimbox", TRIMBOX_MODES, "Le mode de TrimBox")
    artbox = _pick(body, "artbox", ARTBOX_MODES, "Le mode d'ArtBox")
    mark_space = _pick(body, "mark_space", MARK_SPACES, "L'encre des repères")
    color = _pick(body, "color", COLOR_MODES, "L'espace de sortie")
    intent = _pick(body, "intent", tuple(INTENTS.keys()), "L'intention de sortie")
    margin_mm = _num(body, "margin_mm", 0.0, MARGIN_MM_MAX, "La marge")
    gutter_mm = _num(body, "gutter_mm", 0.0, GUTTER_MM_MAX, "La gouttière")
    mark_len = _num(body, "mark_len_mm", 0.0, MARK_LEN_MM_MAX,
                    "La longueur des repères")
    mark_off = _num(body, "mark_off_mm", 0.0, MARK_OFF_MM_MAX,
                    "Le retrait des repères")
    mark_w = _num(body, "mark_w_mm", MARK_W_MM_MIN, MARK_W_MM_MAX,
                  "L'épaisseur des repères")
    quality = int(_num(body, "jpeg_quality", 40, 100, "La qualité JPEG"))
    rgb = _color(body, "mark_color", "La couleur des repères")
    center = _flag(body, "center")
    duplex = _flag(body, "duplex")
    slug = _flag(body, "slug")
    lossless = _flag(body, "lossless")
    layers = _flag(body, "layers")
    page_iso = _flag(body, "page_iso")
    mark_safe = _flag(body, "mark_safe")

    try:
        n = max(0, int(n_cards))
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"Le nombre de cartes doit être un entier (reçu {n_cards!r})")

    if icc is not None and len(icc) > ICC_MAX_BYTES:
        raise ValueError(f"Profil ICC trop lourd : {len(icc)} octets, "
                         f"le maximum est {ICC_MAX_BYTES}")
    out_intent = resolve_intent(intent, icc)
    if color == "cmyk_icc":
        if not icc:
            raise ValueError(
                "« Séparation par profil ICC » demandée sans fichier .icc. "
                "Téléverser le profil de l'imprimeur, ou choisir « CMYK "
                "d'appareil » (conversion sans profil, annoncée comme telle).")
        if icc_info(icc)["space"] != "CMYK":
            raise ValueError("Le profil fourni n'est pas un profil CMYK : "
                             f"son espace est « {icc_info(icc)['space']} ».")
    # Un CMYK ne peut pas voyager en JPEG ici : les JPEG CMYK d'Adobe sont
    # écrits INVERSÉS et réclament un /Decode dans le PDF. On ne livre pas un
    # piège pour gagner des octets — le CMYK sort en Flate, sans perte.
    if color != "rgb":
        lossless = True

    warn: list[dict] = []
    cell_w, cell_h = g.trim_px

    # ── 1 CARTE PAR PAGE : la planche EST la toile, boîtes exactes ────────
    if sheet == SHEET_CARD:
        sw, sh = g.canvas_px
        cols = rows = 1
        gut = 0.0
        marge = 0.0
        ox, oy = g.bleed_off_px
    else:
        sw, sh = sheet_px(sheet, g.dpi)
        if orient == "paysage":
            sw, sh = sh, sw
        gut = mmpx(gutter_mm, g.dpi)
        marge = mmpx(margin_mm, g.dpi)
        avail_w = sw - 2.0 * marge
        avail_h = sh - 2.0 * marge
        cols = int(math.floor((avail_w + gut) / (cell_w + gut))) if cell_w > 0 else 0
        rows = int(math.floor((avail_h + gut) / (cell_h + gut))) if cell_h > 0 else 0
        cols = max(0, cols)
        rows = max(0, rows)
        if cols < 1 or rows < 1:
            raise ValueError(
                "La carte ne tient pas sur cette planche : "
                f"{cell_w}x{cell_h} px de rogne pour {sw}x{sh} px de planche "
                f"moins 2 x {margin_mm:g} mm de marge. Réduire la marge, "
                "changer de planche ou passer en paysage.")
        cw = cols * cell_w + (cols - 1) * gut
        ch = rows * cell_h + (rows - 1) * gut
        if center:
            ox, oy = (sw - cw) / 2.0, (sh - ch) / 2.0
        else:
            ox, oy = marge, marge

    per_page = cols * rows
    content = (cols * cell_w + (cols - 1) * gut,
               rows * cell_h + (rows - 1) * gut)
    pages = int(math.ceil(n / per_page)) if (n and per_page) else (1 if per_page else 0)
    out_pages = pages * (2 if duplex else 1)
    if out_pages > PAGES_MAX:
        raise ValueError(
            f"{out_pages} pages demandées, le maximum est {PAGES_MAX} — "
            "découper l'export en plusieurs lots.")

    # ── ce que l'opérateur doit savoir AVANT de payer une impression ──────
    if sheet != SHEET_CARD and cols > 1 and gut < 2.0 * mmpx(g.bleed_mm, g.dpi) - 1e-9:
        warn.append({
            "kind": "gouttiere_courte", "level": "warn",
            "value": round(gut / 2.0 / g.dpi * MM_PER_INCH, 3),
            "limit": round(g.bleed_mm, 3),
            "message": (
                f"Gouttière {gutter_mm:g} mm pour un fond perdu de "
                f"{g.bleed_mm:g} mm : il en faudrait {2 * g.bleed_mm:g}. Le fond "
                f"perdu est rogné à {gut / 2.0 / g.dpi * MM_PER_INCH:.2f} mm "
                "entre deux cartes (jamais superposé)."),
        })
    if sheet != SHEET_CARD and marge < mmpx(g.bleed_mm, g.dpi) - 1e-9:
        warn.append({
            "kind": "marge_courte", "level": "warn",
            "value": round(margin_mm, 3), "limit": round(g.bleed_mm, 3),
            "message": (
                f"Marge {margin_mm:g} mm inférieure au fond perdu "
                f"{g.bleed_mm:g} mm : le fond perdu des cartes de bord est "
                "rogné au bord de planche."),
        })
    if (marks == "crop" and sheet != SHEET_CARD
            and mmpx(mark_off, g.dpi) < mmpx(g.bleed_mm, g.dpi) - 1e-9):
        warn.append({
            "kind": "reperes_dans_le_fond_perdu", "level": "warn",
            "value": round(mark_off, 2), "limit": round(g.bleed_mm, 3),
            "message": (f"Retrait des repères {mark_off:g} mm inférieur au fond "
                        f"perdu {g.bleed_mm:g} mm : les traits mordent sur "
                        "l'illustration si la coupe dérive."),
        })
    if n and per_page and n % per_page:
        warn.append({
            "kind": "derniere_page_incomplete", "level": "info",
            "value": n % per_page, "limit": per_page,
            "message": (f"Dernière page : {n % per_page} carte(s) sur "
                        f"{per_page} emplacements."),
        })
    # ── hygiène de fichier d'impression, contrôlée sur ce qui SERA ÉCRIT ───
    if not out_intent:
        warn.append({
            "kind": "sans_intention_de_sortie", "level": "warn",
            "value": 0, "limit": 1,
            "message": ("Aucune intention de sortie : le PDF ne dira pas dans "
                        "quel espace il a été fabriqué et le RIP convertira "
                        "avec un profil que personne n'aura choisi."),
        })
    if mark_space == "rgb" and marks != "none":
        warn.append({
            "kind": "reperes_hors_reperage", "level": "warn",
            "value": 0, "limit": 4,
            "message": ("Repères en RVB : à la séparation ce rouge devient "
                        "magenta + jaune et ne sort donc pas sur les quatre "
                        "plaques. La couleur de repérage sort sur les 4."),
        })
    if color == "cmyk_device":
        warn.append({
            "kind": "cmyk_sans_profil", "level": "warn",
            "value": 0, "limit": 1,
            "message": ("CMYK d'appareil : conversion sans profil, sans "
                        "retrait des sous-couleurs ni noir squelette. "
                        "Acceptable en numérique, à éviter en offset."),
        })

    p = Plan(
        sheet=sheet, orient=orient, dpi=g.dpi, sheet_px=(int(sw), int(sh)),
        cols=cols, rows=rows, per_page=per_page, cell_px=(cell_w, cell_h),
        gutter_px=gut, margin_px=marge, origin_px=(ox, oy), content_px=content,
        n_cards=n, pages=pages, out_pages=out_pages, geom=g, duplex=duplex,
        flip=flip, duplex_order=dorder, marks=marks,
        mark_len_px=mmpx(mark_len, g.dpi), mark_off_px=mmpx(mark_off, g.dpi),
        mark_w_px=mmpx(mark_w, g.dpi), mark_rgb=rgb, slug=slug, center=center,
        trimbox=trimbox, lossless=lossless, jpeg_quality=quality,
        margin_mm=margin_mm, gutter_mm=gutter_mm,
        mark_space=mark_space, color=color, intent=intent, artbox=artbox,
        mark_safe=mark_safe, layers=layers, page_iso=page_iso,
        icc=icc, out_intent=out_intent, warnings=warn,
    )
    # ── CE QUE LES CALQUES COÛTENT, DIT AVANT L'EXPORT ────────────────────
    if layers and out_intent and out_intent.get("pdfx"):
        warn.append({
            "kind": "calques_contre_pdfx", "level": "warn", "value": 0,
            "limit": 0,
            "message": ("Calques optionnels demandés : le contenu optionnel "
                        "est une construction PDF 1.5 que PDF/X-3:2003 (bâti "
                        "sur PDF 1.4) n'admet pas. Aucune conformité PDF/X "
                        "n'est donc revendiquée sur ce fichier."),
            "fix": {"layers": False, "label": "sans calques, revendiquer "
                                              + PDFX_VERSION},
        })
    # ── LE SEUL RISQUE RÉEL DE CETTE PLANCHE, ET IL SE COMPTE ─────────────
    #    Il fallait le plan complet pour compter les traits : la règle est
    #    donc posée après. Un trait de gouttière court par-dessus le fond
    #    perdu des deux voisines ; si la coupe dérive de plus que ce qui
    #    reste de fond perdu, l'encre de repérage se pose SUR la carte finie.
    #    Aucune des deux critiques ne l'avait vu levé — il l'est maintenant,
    #    avec le nombre de traits et la dérive tolérée en millimètres.
    # ── LA DÉRIVE TOLÉRÉE : MESURÉE, PLUS AFFIRMÉE ────────────────────────
    #    Elle était annoncée égale au fond perdu restant en gouttière
    #    (« 2,00 mm »). Mesure sur la géométrie écrite : le trait allait d'une
    #    ligne de coupe à l'autre, donc la distance encre -> carte valait
    #    0,0000 mm et la moindre dérive posait de l'encre de repérage sur le
    #    produit. Le chiffre affiché est désormais RELU sur les segments
    #    rendus, et il vaut le retrait réellement laissé.
    touche = mark_touch(p)
    clr = mark_clearance_mm(p)
    if p.marks != "none" and clr >= 0.0:
        _e, interne = bleed_mm_real(p)
        if touche:
            warn.append({
                "kind": "reperes_sur_la_carte", "level": "err",
                "value": touche, "limit": 0,
                "message": (
                    f"{touche} trait(s) de repère touchent la rogne d'une "
                    f"carte : dérive tolérée 0,00 mm. L'encre de repérage — "
                    f"100 % sur les quatre plaques — se pose sur le produit "
                    f"fini au premier micron d'écart du massicot."),
                # LE CORRECTIF PROPOSÉ DOIT CORRIGER. Celui d'avant portait la
                # gouttière à 6 mm : mesuré, il rendait le fond perdu entier et
                # laissait la distance encre -> carte à 0,0000 mm. Ici le
                # bouton dépend de CE QUI annule le retrait.
                "fix": ({"mark_safe": True,
                         "label": "repères hors carte (retrait mesuré)"}
                        if not mark_safe else
                        {"mark_off_mm": 1.0,
                         "label": "retrait des repères à 1 mm"}),
            })
        else:
            # CE QU'IL Y A AU-DELÀ DE LA DÉRIVE, ET C'EST MESURÉ AUSSI : au
            # bord de planche, la marge est du papier nu ; entre deux cartes,
            # les deux fonds perdus se rejoignent au milieu de la gouttière
            # (2 + 2 = 4 mm), donc au-delà c'est l'illustration de la VOISINE
            # qui arrive — jamais du blanc. Le dire faux là aurait remplacé un
            # chiffre faux par une phrase fausse.
            warn.append({
                "kind": "reperes_hors_carte", "level": "ok",
                "value": clr, "limit": round(interne, 2),
                "message": (
                    f"repères à {clr:.2f} mm de la rogne au plus près "
                    f"({len(mark_segments(p))} trait(s), dont {gutter_marks(p)} "
                    f"en gouttière) : la coupe peut dériver de {clr:.2f} mm "
                    f"avant que l'encre de repérage n'atteigne la carte. Fond "
                    f"perdu posé {_e:.2f} mm au bord de planche (papier nu "
                    f"au-delà)"
                    + ("." if per_page < 2 else
                       f" et {interne:.2f} mm entre deux cartes "
                       f"(l'illustration de la voisine au-delà)."
                       if interne > 0.005 else
                       ", et aucun entre deux cartes : elles se touchent, la "
                       "voisine commence à la ligne de coupe.")),
            })
    return p


def cell_rect(p: Plan, r: int, c: int) -> tuple[float, float, float, float]:
    """Rectangle de ROGNE d'une case, en pixels flottants, origine en HAUT à
    gauche de la planche."""
    x = p.origin_px[0] + c * (p.cell_px[0] + p.gutter_px)
    y = p.origin_px[1] + r * (p.cell_px[1] + p.gutter_px)
    return (x, y, float(p.cell_px[0]), float(p.cell_px[1]))


def keep_bleed(p: Plan, r: int, c: int) -> tuple[float, float, float, float]:
    """Fond perdu réellement conservé autour de la rogne d'une case
    (gauche, haut, droite, bas), en pixels.

    Entre deux cartes : la MOITIÉ de la gouttière — deux fonds perdus de 3 mm
    dans 4 mm de gouttière se recouvriraient, et l'un mangerait la coupe de
    l'autre. Au bord de planche : tout ce que la marge autorise."""
    bx, by = p.geom.bleed_off_px
    x, y, w, h = cell_rect(p, r, c)
    left = (p.gutter_px / 2.0) if c > 0 else x
    right = (p.gutter_px / 2.0) if c < p.cols - 1 else (p.sheet_px[0] - (x + w))
    top = (p.gutter_px / 2.0) if r > 0 else y
    bot = (p.gutter_px / 2.0) if r < p.rows - 1 else (p.sheet_px[1] - (y + h))
    return (max(0.0, min(bx, left)), max(0.0, min(by, top)),
            max(0.0, min(bx, right)), max(0.0, min(by, bot)))


def cells_for_page(p: Plan, page: int, side: str = "front") -> list[tuple[int, int, int]]:
    """Cases occupées d'une page : (ligne, colonne, index de carte).

    RECTO-VERSO — le verso est le MIROIR du recto. Retournement bord long
    (le pli vertical) : la colonne s'inverse, la ligne ne bouge pas ; bord
    court : l'inverse. C'est la seule chose qui compte à l'impression, et
    c'est celle que les scripts se trompent le plus souvent."""
    out = []
    for k in range(p.per_page):
        idx = page * p.per_page + k
        if idx >= p.n_cards:
            break
        r, c = divmod(k, p.cols)
        if side == "back":
            if p.flip == "long":
                c = p.cols - 1 - c
            else:
                r = p.rows - 1 - r
        out.append((r, c, idx))
    return out


def origin_for(p: Plan, side: str = "front") -> tuple[float, float]:
    """Coin haut-gauche de la 1re rogne, POUR CE CÔTÉ-LÀ.

    ── LE DÉFAUT QUE PERSONNE N'AVAIT MESURÉ ────────────────────────────────
    Inverser l'INDEX de colonne (ci-dessus) dit quelle carte va où. Encore
    faut-il que la colonne inversée tombe à la position MIROIR. Elle n'y tombe
    que si la grille est symétrique par rapport à l'axe de pliage — donc
    seulement quand l'imposition est CENTRÉE. Sans centrage, la grille
    commence à la marge et tout l'espace restant est de l'autre côté : le
    verso partait avec ce reste en décalage. Mesuré sur la géométrie écrite,
    A4 300 DPI, 2x3 poker :

        marge 10 mm, non centré : 708,54 px = 59,99 mm d'erreur
        marge  5 mm, non centré :  35,40 px =  3,00 mm
        bord court, non centré  :  60,29 px =  5,11 mm
        centré (le cas jugé)    :   0,00 px

    Chaque carte s'imprimait à cheval sur sa voisine au verso. Les deux
    contrôles avaient écrit que le miroir restait « NON PROUVÉ ... la mise en
    page est symétrique, donc le miroir est une opération neutre ici » : ils
    n'avaient vu que le cas où le bug ne se voit pas.

    Le miroir de l'ORIGINE est exact quelle que soit la marge :
        x_verso(cols-1-c) = SW - x_recto(c) - largeur_de_rogne
    et il redonne l'origine du recto quand l'imposition est centrée — donc
    rien ne bouge là où c'était déjà juste."""
    ox, oy = p.origin_px
    if side != "back" or p.sheet == SHEET_CARD:
        return (float(ox), float(oy))
    cw, ch = p.content_px
    if p.flip == "long":                       # pli vertical : x se retourne
        return (float(p.sheet_px[0]) - ox - cw, float(oy))
    return (float(ox), float(p.sheet_px[1]) - oy - ch)


def side_plan(p: Plan, side: str = "front") -> Plan:
    """LE MÊME PLAN, VU DU CÔTÉ DEMANDÉ — un seul point de vérité.

    Tout ce qui dessine (cases, fond perdu conservé, repères, cartouche)
    travaille sur le plan rendu ici. Le verso ne peut donc pas diverger du
    recto par oubli d'un paramètre : il n'y a pas de « chemin verso » à
    maintenir, il y a le même code sur une origine miroir."""
    if side != "back" or p.sheet == SHEET_CARD:
        return p
    o = origin_for(p, side)
    if (abs(o[0] - p.origin_px[0]) < 1e-12
            and abs(o[1] - p.origin_px[1]) < 1e-12):
        return p
    from dataclasses import replace
    return replace(p, origin_px=o)


def mirror_px(p: Plan) -> float:
    """L'ÉCART AU MIROIR PARFAIT, en pixels de planche.

    Mesuré case par case sur la géométrie QUI SERA ÉCRITE, pas déduit du
    réglage : pour chaque carte, on compare la position de son verso à la
    position miroir de son recto par rapport à l'axe de pliage. 0 = le verso
    tombe exactement derrière le recto. C'est la seule chose qui compte quand
    on retourne la feuille, et c'est le critère 9 du cahier des charges."""
    if not p.duplex or p.sheet == SHEET_CARD or p.per_page < 1:
        return 0.0
    pf, pb = side_plan(p, "front"), side_plan(p, "back")
    sw, sh = float(p.sheet_px[0]), float(p.sheet_px[1])
    fronts = {i: cell_rect(pf, r, c)
              for r, c, i in cells_for_page(p, 0, "front")}
    backs = {i: cell_rect(pb, r, c)
             for r, c, i in cells_for_page(p, 0, "back")}
    worst = 0.0
    for i, (fx, fy, cw, ch) in fronts.items():
        bx, by = backs.get(i, (fx, fy))[:2]
        if p.flip == "long":
            worst = max(worst, abs(bx - (sw - (fx + cw))), abs(by - fy))
        else:
            worst = max(worst, abs(by - (sh - (fy + ch))), abs(bx - fx))
    return worst


def mirror_um(p: Plan) -> float:
    """Le même écart, en MICRONS — l'unité dans laquelle un imprimeur juge un
    repérage recto-verso. Arrondi au dixième de micron."""
    return round(px2um(mirror_px(p), p.dpi), 1)


def bleed_mm_sides(p: Plan, raster: bool = False) -> tuple[float, float]:
    """Le fond perdu réellement posé, PIRE CAS DES DEUX CÔTÉS.

    Hors centrage, le verso n'a pas les mêmes marges que le recto : annoncer
    la mesure du recto sur un fichier recto-verso serait annoncer la
    meilleure des deux."""
    e, i = bleed_mm_real(p, raster)
    if p.duplex and p.sheet != SHEET_CARD:
        e2, i2 = bleed_mm_real(side_plan(p, "back"), raster)
        e, i = min(e, e2), min(i, i2)
    return (e, i)


def sheet_pt_nominal(p: Plan) -> tuple[float, float] | None:
    """La taille NOMINALE de la planche en points : 210x297 mm pour l'A4
    (595,2756 x 841,8898 pt), 8,5x11 in pour la Letter (612 x 792 pt exacts).
    None pour « 1 carte par page », où la page EST la toile."""
    if p.sheet not in SHEETS:
        return None
    a, b = SHEETS[p.sheet]["size_mm"]
    w, h = mm2pt(a), mm2pt(b)
    return (h, w) if p.orient == "paysage" else (w, h)


def page_pt(p: Plan) -> tuple[float, float]:
    """La page PDF telle qu'elle sera ÉCRITE, en points."""
    nom = sheet_pt_nominal(p) if p.page_iso else None
    if nom:
        return nom
    return (px2pt(p.sheet_px[0], p.dpi), px2pt(p.sheet_px[1], p.dpi))


def iso_gap_xy_um(p: Plan) -> tuple[float, float]:
    """L'ÉCART À L'ISO, EN MICRONS, SIGNÉ ET PAR AXE.

    UN SEUL NOMBRE MENTAIT PAR OMISSION. Le panneau écrivait « 26,7 µm SOUS
    le format nominal » ; mesuré sur les octets, l'A4 de la grille raster
    fait 595,20 x 841,92 pt contre 595,2756 x 841,8898 : la largeur est bien
    26,7 µm EN DESSOUS, mais la hauteur est 10,7 µm AU-DESSUS. Le mot « sous »
    était faux d'un axe sur deux, et le maximum en valeur absolue cachait
    l'autre. Les deux écarts sortent maintenant avec leur signe."""
    nom = sheet_pt_nominal(p)
    if not nom:
        return (0.0, 0.0)
    w, h = page_pt(p)
    return (round(pt2um(w - nom[0]), 1), round(pt2um(h - nom[1]), 1))


def iso_gap_um(p: Plan) -> float:
    """Le PIRE des deux écarts ci-dessus, en valeur absolue. Sert de seuil
    (« format nominal exact » = sous 0,05 µm), jamais de libellé."""
    dx, dy = iso_gap_xy_um(p)
    return max(abs(dx), abs(dy))


# ══════════════════════════════════════════════════════════════════════════
# REPÈRES — une seule géométrie, servie au raster ET au PDF
# ══════════════════════════════════════════════════════════════════════════

def _bands(edges_lo: list[float], edges_hi: list[float],
           span: float) -> list[tuple[float, float, bool]]:
    """Zones SANS carte le long d'un axe : (début, fin, est_une_gouttière)."""
    out = [(0.0, edges_lo[0], False)]
    for i in range(len(edges_hi) - 1):
        out.append((edges_hi[i], edges_lo[i + 1], True))
    out.append((edges_hi[-1], span, False))
    return [b for b in out if b[1] - b[0] > 1e-6]


def mark_keepout_px(p: Plan) -> float:
    """LE RETRAIT EXIGÉ entre l'encre d'un repère et la rogne d'une carte.

    Il n'y a pas de place « en dehors du fond perdu » dans une gouttière : le
    fond perdu la remplit entièrement (il est rogné à la moitié de chaque
    côté). Un repère posé là est donc forcément sur du fond perdu ; ce qui se
    choisit, c'est la DISTANCE à la ligne de coupe, et elle vaut exactement la
    dérive de massicot qu'on tolère avant que l'encre de repérage se pose sur
    la carte finie.

    Le trait de gouttière est donc CENTRÉ : sa longueur vaut la moitié de la
    gouttière (ou la longueur réglée si elle est plus courte), et le reste se
    partage en deux retraits égaux — plafonnés par le retrait réglé, qui garde
    son sens pour les repères de marge."""
    if not p.mark_safe:
        return 0.0
    g = float(p.gutter_px)
    if p.cols <= 1 and p.rows <= 1 or g <= 0.0:
        return max(0.0, float(p.mark_off_px))
    utile = min(float(p.mark_len_px), g / 2.0)
    return max(0.0, min(float(p.mark_off_px), (g - utile) / 2.0))


def _keep_off_cards(segs, p: Plan, keepout: float):
    """Retire de chaque segment tout ce dont l'ENCRE approcherait une carte à
    moins de `keepout`. L'encre d'un trait déborde de la moitié de son
    épaisseur sur les quatre côtés (bout rond, `1 J`) : le calcul le compte,
    sinon le retrait annoncé serait faux d'un demi-filet.

    Un segment peut traverser une carte de part en part (mode « lignes ») :
    il ressort alors en DEUX morceaux, pas en un seul tronqué."""
    if keepout <= 0.0 or p.per_page < 1:
        return list(segs)
    demi = float(p.mark_w_px) / 2.0
    cells = [cell_rect(p, r, c)
             for r in range(max(1, p.rows)) for c in range(max(1, p.cols))]
    out = []
    for x0, y0, x1, y1 in segs:
        vert = abs(x0 - x1) < 1e-6
        fixe = x0 if vert else y0
        lo, hi = ((min(y0, y1), max(y0, y1)) if vert
                  else (min(x0, x1), max(x0, x1)))
        vivants = [(lo, hi)]
        for cx, cy, cw, ch in cells:
            # bornes de la carte, élargies du retrait, sur les deux axes
            fx0, fx1 = ((cx - keepout, cx + cw + keepout) if vert
                        else (cy - keepout, cy + ch + keepout))
            if not (fixe + demi > fx0 + 1e-9 and fixe - demi < fx1 - 1e-9):
                continue                   # l'encre passe à côté : rien à ôter
            tx0, tx1 = ((cy - keepout - demi, cy + ch + keepout + demi) if vert
                        else (cx - keepout - demi, cx + cw + keepout + demi))
            reste = []
            for a, b in vivants:
                if b <= tx0 + 1e-9 or a >= tx1 - 1e-9:
                    reste.append((a, b))
                    continue
                if a < tx0 - 1e-9:
                    reste.append((a, tx0))
                if b > tx1 + 1e-9:
                    reste.append((tx1, b))
            vivants = reste
            if not vivants:
                break
        for a, b in vivants:
            if b - a <= 1e-6:
                continue
            out.append((fixe, a, fixe, b) if vert else (a, fixe, b, fixe))
    return out


def mark_clearance_px(p: Plan) -> float:
    """LA DÉRIVE TOLÉRÉE, MESURÉE : distance minimale entre l'encre des
    repères et la rogne de la carte la plus proche, sur les segments qui
    seront réellement écrits.

    C'est le chiffre que l'écran affiche, et c'est un MINIMUM sur toute la
    planche, pas la valeur d'un réglage. `-1` quand il n'y a aucun repère."""
    segs = mark_segments(p)
    if not segs or p.per_page < 1:
        return -1.0
    demi = float(p.mark_w_px) / 2.0
    cells = [cell_rect(p, r, c)
             for r in range(max(1, p.rows)) for c in range(max(1, p.cols))]
    if not cells:
        return -1.0
    pire = float("inf")
    for x0, y0, x1, y1 in segs:
        ax0, ax1 = min(x0, x1) - demi, max(x0, x1) + demi
        ay0, ay1 = min(y0, y1) - demi, max(y0, y1) + demi
        for cx, cy, cw, ch in cells:
            dx = max(cx - ax1, ax0 - (cx + cw), 0.0)
            dy = max(cy - ay1, ay0 - (cy + ch), 0.0)
            d = math.hypot(dx, dy)
            if d < pire:
                pire = d
                if pire <= 0.0:
                    return 0.0
    return pire if pire < float("inf") else -1.0


def mark_clearance_mm(p: Plan) -> float:
    """La même, en millimètres, arrondie au centième."""
    d = mark_clearance_px(p)
    return -1.0 if d < 0 else round(d / float(p.dpi) * MM_PER_INCH, 2)


def mark_touch(p: Plan) -> int:
    """COMBIEN DE TRAITS TOUCHENT UNE CARTE. Zéro est la seule valeur
    acceptable pour un fichier d'impression : au premier micron de dérive,
    ces traits-là s'impriment sur le produit."""
    segs = mark_segments(p)
    if not segs or p.per_page < 1:
        return 0
    demi = float(p.mark_w_px) / 2.0
    cells = [cell_rect(p, r, c)
             for r in range(max(1, p.rows)) for c in range(max(1, p.cols))]
    n = 0
    for x0, y0, x1, y1 in segs:
        ax0, ax1 = min(x0, x1) - demi, max(x0, x1) + demi
        ay0, ay1 = min(y0, y1) - demi, max(y0, y1) + demi
        for cx, cy, cw, ch in cells:
            if (ax1 > cx + 1e-9 and ax0 < cx + cw - 1e-9
                    and ay1 > cy + 1e-9 and ay0 < cy + ch - 1e-9):
                n += 1
                break
    return n


def mark_segments(p: Plan) -> list[tuple[float, float, float, float]]:
    """Segments des repères, en pixels flottants (origine haut-gauche).

    Le DOUBLE TRAIT DE COUPE dans la gouttière n'est pas une option : chaque
    gouttière est bordée par DEUX arêtes de rogne (la droite de la carte de
    gauche, la gauche de celle de droite), donc deux traits. nanDECK n'en
    trace qu'un par gouttière — la coupe y perd le fond perdu du voisin.

    ET AUCUN DE CES TRAITS NE TOUCHE UNE CARTE : `mark_keepout_px` fixe le
    retrait, `_keep_off_cards` le fait respecter, `mark_clearance_px` le
    RELIT sur les segments rendus. Sans lui, le trait de gouttière allait
    d'une coupe à l'autre et la croix mordait 2 mm dans la carte."""
    if p.marks == "none" or p.mark_w_px <= 0 or p.per_page < 1:
        return []
    xs_lo = [cell_rect(p, 0, c)[0] for c in range(p.cols)]
    xs_hi = [x + p.cell_px[0] for x in xs_lo]
    ys_lo = [cell_rect(p, r, 0)[1] for r in range(p.rows)]
    ys_hi = [y + p.cell_px[1] for y in ys_lo]
    xs = sorted(xs_lo + xs_hi)
    ys = sorted(ys_lo + ys_hi)
    sw, sh = float(p.sheet_px[0]), float(p.sheet_px[1])
    segs: list[tuple[float, float, float, float]] = []

    if p.marks == "line":
        for x in xs:
            segs.append((x, 0.0, x, sh))
        for y in ys:
            segs.append((0.0, y, sw, y))
        return _fini(segs, p, sw, sh)

    if p.marks == "cross":
        half = p.mark_len_px / 2.0
        for x in xs:
            for y in ys:
                segs.append((x - half, y, x + half, y))
                segs.append((x, y - half, x, y + half))
        return _fini(segs, p, sw, sh)

    # "crop" : traits dans les marges (retrait + longueur), et la gouttière
    # ENTIÈRE entre deux cartes — c'est là que le double trait se lit.
    for x in xs:
        for a, b, gutter in _bands(ys_lo, ys_hi, sh):
            if gutter:
                segs.append((x, a, x, b))
            elif a == 0.0:                       # marge haute
                y1 = b - p.mark_off_px
                segs.append((x, max(a, y1 - p.mark_len_px), x, y1))
            else:                                # marge basse
                y0 = a + p.mark_off_px
                segs.append((x, y0, x, min(b, y0 + p.mark_len_px)))
    for y in ys:
        for a, b, gutter in _bands(xs_lo, xs_hi, sw):
            if gutter:
                segs.append((a, y, b, y))
            elif a == 0.0:
                x1 = b - p.mark_off_px
                segs.append((max(a, x1 - p.mark_len_px), y, x1, y))
            else:
                x0 = a + p.mark_off_px
                segs.append((x0, y, min(b, x0 + p.mark_len_px), y))
    return _fini(segs, p, sw, sh)


def gutter_marks(p: Plan) -> int:
    """COMBIEN DE TRAITS TRAVERSENT UNE GOUTTIÈRE, par page.

    Un trait de gouttière est tracé PAR-DESSUS le fond perdu des deux cartes
    voisines. C'est propre tant que le massicot tombe juste : le trait part à
    la coupe. Mais avec un fond perdu interne rogné à 2 mm, une dérive de
    coupe supérieure à ce reste dépose de l'encre de repérage — 100 % sur les
    quatre plaques — sur la tranche de la carte finie. C'est le seul risque
    réel de cette planche, et il se COMPTE : la mesure alimente une règle du
    contrôle avant vol au lieu de rester une intuition."""
    if p.cols < 1 or p.rows < 1:
        return 0
    xs_lo = [cell_rect(p, 0, c)[0] for c in range(p.cols)]
    xs_hi = [x + p.cell_px[0] for x in xs_lo]
    ys_lo = [cell_rect(p, r, 0)[1] for r in range(p.rows)]
    ys_hi = [y + p.cell_px[1] for y in ys_lo]
    bx = [(xs_hi[i], xs_lo[i + 1]) for i in range(len(xs_lo) - 1)]
    by = [(ys_hi[i], ys_lo[i + 1]) for i in range(len(ys_lo) - 1)]
    n = 0
    for x0, y0, x1, y1 in mark_segments(p):
        lo, hi = (min(y0, y1), max(y0, y1)) if abs(x0 - x1) < 1e-6 \
            else (min(x0, x1), max(x0, x1))
        bandes = by if abs(x0 - x1) < 1e-6 else bx
        for a, b in bandes:
            if lo >= a - 1e-6 and hi <= b + 1e-6:
                n += 1
                break
    return n


def _fini(segs, p: Plan, sw: float, sh: float):
    """La sortie de `mark_segments`, dans l'ordre : on écarte l'encre des
    cartes, PUIS on pince à la planche. Un seul passage, pour les trois
    styles de repères — le retrait ne peut donc pas s'appliquer à l'un et
    s'oublier chez l'autre."""
    return _clip(_keep_off_cards(segs, p, mark_keepout_px(p)), sw, sh)


def _clip(segs, sw: float, sh: float):
    """Hors planche = pas de trait. Les segments sont horizontaux ou
    verticaux : un simple pincement des bornes suffit."""
    out = []
    for x0, y0, x1, y1 in segs:
        x0c, x1c = max(0.0, min(sw, x0)), max(0.0, min(sw, x1))
        y0c, y1c = max(0.0, min(sh, y0)), max(0.0, min(sh, y1))
        if abs(x1c - x0c) < 1e-6 and abs(y1c - y0c) < 1e-6:
            continue
        out.append((x0c, y0c, x1c, y1c))
    return out


def bleed_px_real(p: Plan, raster: bool = False) -> tuple[float, float]:
    """LE FOND PERDU RÉELLEMENT POSÉ, en pixels : (bord de planche, entre
    deux cartes). Ce n'est pas le réglage : c'est ce que la gouttière et la
    marge laissent réellement passer, mesuré sur la géométrie qui sera
    écrite.

    C'est la seule mesure que le cartouche annonçait FAUX — il imprimait
    « fond perdu 3 mm » alors qu'il n'en restait que 2 dans la gouttière,
    et l'écran, lui, le disait. Un fichier ne doit pas mentir là où l'écran
    dit vrai.

    `raster=True` rend la valeur de la PLANCHE PNG, où tout tombe sur un
    pixel entier ; `raster=False` celle du PDF, où le chemin de rognage est
    à la coordonnée exacte. Les deux sont affichées : c'est le seul écart
    entre les deux livrables du même travail, et il vaut un demi-pixel."""
    bx, by = p.geom.bleed_off_px
    cw, chh = p.cell_px
    outer, inner = [], []
    for r in range(max(1, p.rows)):
        for c in range(max(1, p.cols)):
            if raster:
                kl, kt, kr, kb = keep_bleed(p, r, c)
                x0, y0 = R(bx - kl), R(by - kt)
                x1, y1 = R(bx + cw + kr), R(by + chh + kb)
                l, t = bx - x0, by - y0
                rr, bo = x1 - (bx + cw), y1 - (by + chh)
            else:
                l, t, rr, bo = keep_bleed(p, r, c)
            (inner if c > 0 else outer).append(l)
            (inner if c < p.cols - 1 else outer).append(rr)
            (inner if r > 0 else outer).append(t)
            (inner if r < p.rows - 1 else outer).append(bo)
    e = min(outer) if outer else 0.0
    return (e, min(inner) if inner else e)


def bleed_mm_real(p: Plan, raster: bool = False) -> tuple[float, float]:
    """Le même, en millimètres, arrondi au centième — la précision qu'un
    imprimeur lit."""
    k = MM_PER_INCH / float(p.dpi)
    e, i = bleed_px_real(p, raster)
    return (round(e * k, 2), round(i * k, 2))


def _mm(v: float) -> str:
    s = f"{float(v):.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def slug_parts(p: Plan, name: str, page: int, side: str,
               raster: bool = False) -> tuple[list, str]:
    """Le cartouche, en DEUX morceaux : à gauche l'identité et la géométrie
    (segments jetables un par un si la planche est étroite), à droite la
    pagination et la date — qui ne se perdent JAMAIS.

    L'ancien cartouche était une seule chaîne, mesurée « à 0,52 em près »,
    tronquée à 132 octets et terminée par « pa? » : la pagination et la date
    que la case à cocher promet n'apparaissaient dans AUCUN des deux PDF, et
    les deux pages portaient exactement le même texte."""
    g = p.geom
    face = "verso" if side == "back" else "recto"
    edge, inner = bleed_mm_real(p, raster)
    c2 = lambda v: f"{float(v):.2f}".replace(".", ",")      # noqa: E731
    # Sous 0,02 mm d'écart (un demi-pixel à 600 DPI), les deux bords sont le
    # même fond perdu à l'arrondi près : on annonce le PLUS PETIT — c'est
    # celui dont dépend le massicot.
    fp = (f"fond perdu {_mm(g.bleed_mm)} mm : posé {c2(min(edge, inner))} mm"
          if abs(edge - inner) < 0.02 else
          f"fond perdu {_mm(g.bleed_mm)} mm : posé {c2(edge)} bord / "
          f"{c2(inner)} gouttière")
    # LA ZONE SÛRE, ÉCRITE ET NON RÉGLÉE — même règle que le fond perdu
    # juste au-dessus : ce que porte l'/ArtBox, pas ce que dit le curseur.
    zx, zy = safe_inset_written_mm(p)
    zs = (f"zone sûre {_mm(g.safe_mm)} mm"
          if max(abs(zx - g.safe_mm), abs(zy - g.safe_mm)) < 0.0005 else
          f"zone sûre {_mm(g.safe_mm)} mm : écrite {c2(zx)}"
          if abs(zx - zy) < 0.0005 else
          f"zone sûre {_mm(g.safe_mm)} mm : écrite {c2(zx)} / {c2(zy)}")
    oi = p.out_intent
    encre = {"registration": "repères repérage 100/100/100/100",
             "cmyk_black": "repères noir 100 %",
             "rgb": "repères RVB"}[p.mark_space]
    espace = {"rgb": "visuels RVB", "cmyk_device": "visuels CMYK d'appareil",
              "cmyk_icc": "visuels CMYK par profil"}[p.color]
    gauche = [
        (0, str(name or "Jeu")),            # 0 = jamais jeté
        (0, fp),                            # 0 = la mesure qui mentait
        (1, g.label),
        (1, f"{g.dpi} DPI"),
        (2, zs),
        (3, espace + (" · " + oi["id"] if oi else " · sans intention")),
        (4, f"coupe {g.trim_px[0]}x{g.trim_px[1]} px"),
        (5, f"toile {g.canvas_px[0]}x{g.canvas_px[1]} px"),
        (6, f"{p.cols}x{p.rows}/page"),
        (7, encre),
    ]
    # LA DÉRIVE TOLÉRÉE VOYAGE AVEC LA PLANCHE. C'est le chiffre dont dépend
    # le massicot, et il était affirmé à l'écran sans jamais partir dans le
    # fichier. Priorité 8 : c'est le premier segment lâché sur une planche
    # étroite, jamais la pagination ni la mesure du fond perdu.
    clr = mark_clearance_mm(p)
    if p.marks != "none" and clr >= 0:
        gauche.append((8, f"repères à {c2(clr)} mm de la coupe"))
    droite = (f"page {page + 1}/{max(1, p.pages)} {face} · "
              f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return gauche, droite


def slug_text(p: Plan, name: str, page: int, side: str,
              raster: bool = False) -> str:
    """Le cartouche COMPLET, sans souci de largeur — c'est ce que portent les
    métadonnées du PDF, où rien ne le tronque."""
    gauche, droite = slug_parts(p, name, page, side, raster)
    return " · ".join([t for _, t in gauche] + [droite])


SLUG_SCALES = (1.0, 0.88, 0.78, 0.68, 0.58)


def slug_fit(p: Plan, name: str, page: int, side: str,
             largeur: float, cap: float,
             raster: bool = False) -> tuple[str, str, float]:
    """(gauche, droite, corps) tenant dans `largeur`. La pagination et la
    date sont INTOUCHABLES : elles sont posées à droite, et c'est la gauche
    qui cède.

    L'ordre d'essai dit ce que le cartouche défend : d'abord garder TOUT en
    écrivant plus petit, ensuite seulement jeter un segment. La mesure est
    EXACTE (chasse fixe), donc « ça tient » n'est jamais une estimation —
    l'ancienne, à « 0,52 em » près, tronquait le cartouche à 132 octets et
    supprimait la pagination et la date qu'annonce la case à cocher."""
    gauche, droite = slug_parts(p, name, page, side, raster)
    droite = slug_chars(droite)
    mini = min(cap, mmpx(1.4, p.dpi))     # plus petit qu'un imprimeur ne lit
    best = None
    for sc in SLUG_SCALES:
        c = cap * sc
        if c < mini and best is not None:
            break
        for seuil in (99, 7, 6, 5, 4, 3, 2, 1):
            keep = [t for pri, t in gauche if pri < seuil]
            gtxt = slug_chars(" · ".join(keep))
            if (text_width(gtxt, c) + text_width("  ", c)
                    + text_width(droite, c) <= largeur):
                if best is None or len(keep) > best[3]:
                    best = (gtxt, droite, c, len(keep))
                break
    if best is not None:
        return best[0], best[1], best[2]
    # Planche minuscule : on garde la droite, entière, et on rogne la gauche
    # au caractère — avec un vrai caractère de suspension, jamais un « ? ».
    c = cap * SLUG_SCALES[-1]
    reste = largeur - text_width("  ", c) - text_width(droite, c)
    gtxt = slug_chars(str(name or "Jeu"))
    lo, hi = 0, len(gtxt)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text_width(gtxt[:mid] + "…", c) <= reste:
            lo = mid
        else:
            hi = mid - 1
    return ((gtxt[:lo] + "…") if lo else "", droite, c)


def slug_cap_px(p: Plan) -> float:
    """Hauteur de capitale du cartouche, EN PIXELS de planche. Une seule
    valeur pour les deux livrables : la planche PNG la prend telle quelle, le
    PDF la convertit en points. Ils portent donc le même cartouche à la même
    taille physique."""
    return max(5.0, min(p.margin_px * 0.30, mmpx(1.9, p.dpi)))


def slug_layout(p: Plan, name: str, page: int, side: str,
                raster: bool = False):
    """-> (polylignes en px, épaisseur de trait en px) ou None. Origine en
    HAUT à gauche de la planche, axe y vers le bas."""
    if not p.slug or p.sheet == SHEET_CARD or p.margin_px <= 4:
        return None
    cap0 = slug_cap_px(p)
    x0 = max(2.0, p.margin_px * 0.18)
    largeur = p.sheet_px[0] - 2.0 * x0
    if largeur <= cap0:
        return None
    g, d, cap = slug_fit(p, name, page, side, largeur, cap0, raster)
    base = x0 + cap                       # ligne de base sous la marge haute
    polys = text_paths(g, x0, base, cap)
    polys += text_paths(d, x0 + largeur - text_width(d, cap), base, cap)
    return polys, max(0.6, cap * 0.11)


# ══════════════════════════════════════════════════════════════════════════
# Images reçues — le contrôle qui tient la garantie WYSIWYG
# ══════════════════════════════════════════════════════════════════════════

def open_card(data: bytes, p: Plan, i: int) -> Image.Image:
    """Ouvre un bitmap de carte et REFUSE toute taille autre que
    `geom.canvas_px`. C'est le seul verrou mécanique de « un seul moteur » :
    sans lui, n'importe quel client pourrait imposer des cartes rendues
    ailleurs, à une autre échelle, et le fichier livré ne serait plus celui
    de l'écran."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise ValueError(f"La carte {i + 1} n'est pas une image lisible")
    w, h = im.size
    if (w, h) != tuple(p.geom.canvas_px):
        raise ValueError(
            f"La carte {i + 1} mesure {w}x{h} px ; la géométrie du jeu impose "
            f"{p.geom.canvas_px[0]}x{p.geom.canvas_px[1]} px "
            f"({p.geom.label} à {p.geom.dpi} DPI, fond perdu {p.geom.bleed_mm:g} mm). "
            "Les cartes doivent venir de CF.renderCard, jamais d'un autre moteur.")
    return im


def crop_for_cell(im: Image.Image, p: Plan, r: int, c: int):
    """Découpe le bitmap au fond perdu réellement conservé pour cette case.

    Rend (image, dx, dy) où dx/dy sont la distance EXACTE, en pixels, entre
    le bord de l'image découpée et l'arête de rogne. C'est ce couple qui
    permet de poser l'image à une coordonnée fractionnaire sans jamais
    déplacer la rogne : la découpe est entière, le placement ne l'est pas."""
    bx, by = p.geom.bleed_off_px
    kl, kt, kr, kb = keep_bleed(p, r, c)
    x0 = int(R(bx - kl))
    y0 = int(R(by - kt))
    x1 = int(R(bx + p.cell_px[0] + kr))
    y1 = int(R(by + p.cell_px[1] + kb))
    x0 = max(0, min(x0, im.size[0]))
    y0 = max(0, min(y0, im.size[1]))
    x1 = max(x0 + 1, min(x1, im.size[0]))
    y1 = max(y0 + 1, min(y1, im.size[1]))
    return im.crop((x0, y0, x1, y1)), (bx - x0), (by - y0)


def _flatten(im: Image.Image) -> Image.Image:
    """Sur du papier, il n'y a pas d'alpha : l'apercu montre du blanc, le
    fichier doit montrer du blanc."""
    if im.mode == "RGB":
        return im
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, im).convert("RGB")
    return im.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════
# PLANCHE RASTER (PNG)
# ══════════════════════════════════════════════════════════════════════════

def mark_rgb_shown(p: Plan) -> tuple[int, int, int]:
    """La couleur À L'ÉCRAN et sur la planche PNG de l'encre choisie. Le
    repérage (100 % des quatre encres) se voit comme un noir très dense ; le
    dire en RVB sur un aperçu, c'est WYSIWYG, pas un mensonge — le PDF, lui,
    porte l'espace réel."""
    if p.mark_space == "registration":
        return (17, 17, 17)
    if p.mark_space == "cmyk_black":
        return (0, 0, 0)
    return p.mark_rgb


def compose_sheet(p: Plan, images: dict[int, Image.Image], page: int,
                  side: str, name: str = "") -> Image.Image:
    """Une page de planche, en bitmap. A4 à 300 DPI = 2480x3508 px, zéro
    tolérance : la taille vient de `contract.sheet_px`, jamais d'un calcul
    local."""
    # LE VERSO EST LE MIROIR PHYSIQUE DU RECTO : tout ce qui suit travaille
    # sur le plan de CE côté, cases, repères et cartouche compris.
    ps = side_plan(p, side)
    sheet = Image.new("RGB", p.sheet_px, (255, 255, 255))
    for r, c, idx in cells_for_page(p, page, side):
        im = images.get(idx)
        if im is None:
            continue
        piece, dx, dy = crop_for_cell(_flatten(im), ps, r, c)
        x, y, _w, _h = cell_rect(ps, r, c)
        sheet.paste(piece, (int(R(x - dx)), int(R(y - dy))))
    d = ImageDraw.Draw(sheet)
    lw = max(1, int(R(p.mark_w_px)))
    ink = mark_rgb_shown(p)
    for x0, y0, x1, y1 in mark_segments(ps):
        d.line((R(x0), R(y0), R(x1), R(y1)), fill=ink, width=lw)
    lay = slug_layout(ps, name or "Jeu", page, side, raster=True)
    if lay:
        polys, w = lay
        iw = max(1, int(R(w)))
        for poly in polys:
            d.line([(x, y) for x, y in poly], fill=(110, 110, 110),
                   width=iw, joint="curve")
    return sheet


# ══════════════════════════════════════════════════════════════════════════
# PNG — 8 et 16 bits, avec `pHYs`. Pillow ne sait pas encoder du RGBA 16
# bits : ce writer-là le fait, en trois chunks et sans dépendance.
# ══════════════════════════════════════════════════════════════════════════

def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def phys_ppm(dpi: int) -> int:
    """Pixels par mètre du chunk `pHYs`. 300 DPI -> 11811, la valeur que
    Pillow écrit aussi et que nanDECK relit en 299,9994 DPI."""
    return int(float(dpi) / 0.0254 + 0.5)


def phys_dpi(dpi: int) -> float:
    """LA DÉFINITION QUE LE FICHIER PORTE VRAIMENT, pas celle du curseur.

    L'unité du chunk `pHYs` est le MÈTRE ENTIER : 300 DPI vaudrait
    11811,0236 px/m, la grille n'accepte que 11811, et 11811 px/m redonne
    299,9994 DPI. L'écart est de 6 dix-millièmes de DPI — il ne se voit sur
    aucune presse, mais il EXISTE dans les octets, et un panneau qui affiche
    « 300,00 DPI » à côté de « pHYs 11811 » affirme une égalité fausse.
    Cette fonction est la seule source du chiffre affiché."""
    return phys_ppm(dpi) * 0.0254


def _iccp_chunk(profile: bytes, nom: str = "") -> bytes:
    """Chunk `iCCP` : le profil ICC embarqué dans le PNG. Un fichier qui
    annonce 300 DPI sans dire dans quel RVB il est laisse la moitié du travail
    à faire — le `pHYs` donne l'échelle, l'`iCCP` donne la couleur.

    LE NOM DU CHUNK EST CELUI QUE LE PROFIL SE DONNE, lu dans son tag `desc`.
    Il s'appelait « sRGB IEC61966-2.1 » : reproche mesuré, et fondé — le
    profil est un profil matriciel de 588 octets produit par littleCMS, dont
    le tag `desc` dit « sRGB built-in », et ce n'est PAS le fichier de
    référence de l'ICC qui pèse des dizaines de kilo-octets. La colorimétrie
    est bien celle de sRGB ; l'identité du fichier, non. On écrit l'identité
    qu'il porte."""
    nom = nom or icc_desc(profile) or "ICC profile"
    return _png_chunk(b"iCCP", nom.encode("latin-1", "replace")[:79]
                      + b"\x00\x00" + zlib.compress(profile, 6))


def png_tag_icc(data: bytes, profile: bytes) -> bytes:
    """Insère `iCCP` juste après `IHDR` — UN SEUL chemin de nommage pour les
    deux encodeurs. Pillow, lui, écrit toujours « ICC Profile » : les deux
    livrables du même travail portaient donc deux noms différents pour le
    même profil."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 16:
        return data
    fin = 8 + 12 + struct.unpack(">I", data[8:12])[0]      # après IHDR
    if data[12:16] != b"IHDR":
        return data
    reste = data[fin:]
    if reste[4:8] == b"iCCP":                              # déjà étiqueté
        reste = reste[12 + struct.unpack(">I", reste[0:4])[0]:]
    return data[:fin] + _iccp_chunk(profile) + reste


def png16_bytes(im: Image.Image, dpi: int) -> bytes:
    """PNG 16 bits par canal, RGBA (type 6) ou RGB (type 2), avec `pHYs`.

    Le contenu vient d'une toile 8 bits : le CONTENEUR est en 16 bits (c'est
    ce que réclament les chaînes d'impression qui refusent le 8 bits), la
    précision reste celle de la source, et l'écran l'écrit noir sur blanc.
    L'expansion v -> v*257 est exacte (0xFF -> 0xFFFF) et se fait par tranche
    de bytearray, pas octet par octet : 815x1110 en 25 ms au lieu de 800."""
    has_alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
    im = im.convert("RGBA" if has_alpha else "RGB")
    ch = 4 if has_alpha else 3
    w, h = im.size
    src = im.tobytes()
    stride = w * ch
    rows = bytearray()
    for y in range(h):
        line = src[y * stride:(y + 1) * stride]
        wide = bytearray(2 * stride)
        wide[0::2] = line
        wide[1::2] = line
        rows += b"\x00" + wide
    ppm = phys_ppm(dpi)
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16,
                                              6 if has_alpha else 2, 0, 0, 0))
            + _iccp_chunk(srgb_icc())
            + _png_chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1))
            + _png_chunk(b"IDAT", zlib.compress(bytes(rows), 6))
            + _png_chunk(b"IEND", b""))


# ══════════════════════════════════════════════════════════════════════════
# LA PROFONDEUR UTILE — MESURÉE SUR LE FICHIER, PAS LUE DANS SON EN-TÊTE
#
# Un audit a démontré, sur une autre pièce de ce même produit, qu'un badge
# « 16 bits » pouvait être FAUX : l'`IHDR` annonçait 16 bits et les 12 582 912
# échantillons tombaient tous sur le réseau k x 257, c'est-à-dire une carte
# 8 bits élargie. Deux verdicts successifs s'étaient contredits sur le même
# octet, parce que l'un s'était arrêté à l'en-tête.
#
# Ici, l'expansion v -> v*257 est VOULUE et documentée (le conteneur est en
# 16 bits, la source écran reste en 8) — mais une phrase d'écran n'est pas une
# mesure. Cette fonction DÉCOMPRESSE le fichier écrit et compte : combien
# d'échantillons, combien de valeurs distinctes, et si tous sont multiples de
# 257. C'est elle, et rien d'autre, qui alimente le chiffre affiché.
# ══════════════════════════════════════════════════════════════════════════

def _png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Ce fichier n'est pas un PNG")
    i, out = 8, []
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        out.append((tag, data[i + 8:i + 8 + ln]))
        i += 12 + ln
        if tag == b"IEND":
            break
    return out


def png_depth(data: bytes) -> dict:
    """Ce que le PNG livré porte VRAIMENT, par canal. Rend :

      declared    la profondeur annoncée par l'IHDR (8 ou 16)
      real_bits   celle que les échantillons occupent réellement
      distinct    le nombre de valeurs distinctes, comptées
      useful_bits log2(distinct), arrondi au centième
      lattice_257 vrai si TOUS les échantillons sont multiples de 257,
                  c'est-à-dire une source 8 bits élargie dans un conteneur
                  16 bits (octet de poids fort = octet de poids faible)
      exact       vrai quand la mesure a pu porter sur tous les échantillons
    """
    ch = _png_chunks(data)
    ihdr = next((p for t, p in ch if t == b"IHDR"), b"")
    if len(ihdr) < 10:
        raise ValueError("PNG sans IHDR lisible")
    w, h, depth, ctype = struct.unpack(">IIBB", ihdr[:10])
    nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype, 1)
    out = {"declared": depth, "real_bits": depth, "channels": nch,
           "px": [w, h], "samples": w * h * nch, "distinct": -1,
           "useful_bits": -1.0, "lattice_257": False, "exact": False,
           "alpha": ctype in (4, 6)}
    if ctype == 3:
        # Image indexée : l'histogramme compterait des INDEX de palette, pas
        # des niveaux. On ne rend pas une mesure qui ne mesure pas ce qu'elle
        # dit — `exact` reste faux. (Ce module n'en produit aucune.)
        return out
    if depth != 16:
        # Un conteneur 8 bits ne peut rien élargir : la seule question qui
        # reste est le nombre de niveaux réellement employés, et le décodeur
        # de PIL le donne exactement (histogramme par canal, en C).
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            hist = im.histogram()
            nb = max(1, len(hist) // 256)
            bandes = [hist[i * 256:(i + 1) * 256] for i in range(nb)]
            vus = sum(1 for v in range(256) if any(b[v] for b in bandes))
            out["distinct"] = vus
            out["useful_bits"] = round(math.log2(vus), 2) if vus else 0.0
            out["exact"] = True
        except Exception:
            pass
        return out
    raw = zlib.decompress(b"".join(p for t, p in ch if t == b"IDAT"))
    stride = w * nch * 2
    if len(raw) < h * (stride + 1):
        return out
    filtres = {raw[y * (stride + 1)] for y in range(h)}
    if filtres != {0}:
        # Filtrage adaptatif : le défiltrage serait exact mais coûteux ici.
        # On ne DEVINE pas — on rend une mesure incomplète, marquée telle.
        return out
    buf = bytearray()
    for y in range(h):
        o = y * (stride + 1) + 1
        buf += raw[o:o + stride]
    hi, lo = bytes(buf[0::2]), bytes(buf[1::2])
    out["exact"] = True
    if hi == lo:                       # v = k*257  <=>  poids fort = faible
        out["lattice_257"] = True
        out["real_bits"] = 8
        vus = len(set(hi))
    else:
        vus = len(set(struct.unpack(">%dH" % (len(buf) // 2), bytes(buf))))
    out["distinct"] = vus
    out["useful_bits"] = round(math.log2(vus), 2) if vus else 0.0
    return out


def depth_probe(g: CardGeom, bits: int, alpha: bool = False) -> dict:
    """La même mesure, sur un TÉMOIN qui porte 256 niveaux — pour que le
    panneau puisse dire la vérité AVANT le premier export.

    Le témoin est une rampe de 0 à 255 sur la largeur de la toile : une source
    qui utilise TOUS les niveaux d'une carte 8 bits. Si le fichier 16 bits
    n'en montre toujours que 256, toutes multiples de 257, alors le 16 bits
    est un conteneur — et c'est démontré, pas affirmé."""
    w, h = g.canvas_px
    ligne = bytes(bytearray(v for x in range(w)
                            for v in ((x * 256) // w,) * 3))
    im = Image.frombytes("RGB", (w, h), ligne * h)
    data, _, _ = encode_image(im, "png", int(bits), g.dpi, alpha, 95)
    out = png_depth(data)
    out["bytes"] = len(data)
    out["source_levels"] = 256
    return out


def encode_image(im: Image.Image, fmt: str, bits: int, dpi: int,
                 alpha: bool, quality: int) -> tuple[bytes, str, str]:
    """-> (octets, type MIME, extension). `pHYs` (PNG) et la densité JFIF
    (JPEG) portent le DPI : un fichier d'impression qui ne dit pas sa
    définition se fait redimensionner par le premier logiciel venu."""
    if fmt == "jpeg":
        buf = io.BytesIO()
        _flatten(im).save(buf, "JPEG", quality=int(quality), subsampling=0,
                          dpi=(dpi, dpi), optimize=True,
                          icc_profile=srgb_icc())
        return buf.getvalue(), "image/jpeg", "jpg"
    if not alpha:
        im = _flatten(im)
    if int(bits) == 16:
        return png16_bytes(im, dpi), "image/png", "png"
    buf = io.BytesIO()
    im.save(buf, "PNG", dpi=(dpi, dpi))
    return png_tag_icc(buf.getvalue(), srgb_icc()), "image/png", "png"


# ══════════════════════════════════════════════════════════════════════════
# PDF — pypdf, pages construites à la main
#
# Chaque carte est un XObject posé par une matrice `cm` à des coordonnées
# FRACTIONNAIRES : c'est ce qui donne une gouttière exacte à 11,3386 pt là où
# un compositing raster la figerait à 11,28 pt. Les repères sont des
# opérateurs `m`/`l`/`S` — du VECTEUR, comme nanDECK, pas des pixels. Et
# chaque page porte `/TrimBox` et `/BleedBox`, ce que le PDF de nanDECK n'a
# pas : un imprimeur voit la différence en deux secondes.
# ══════════════════════════════════════════════════════════════════════════

def _pdf_num(v: float) -> str:
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def to_output_space(im: Image.Image, p: Plan) -> tuple[Image.Image, str]:
    """L'image dans l'espace de SORTIE choisi. -> (image, étiquette honnête).

    `cmyk_icc` passe par littleCMS avec le profil de l'imprimeur : c'est une
    vraie séparation. `cmyk_device` est la conversion d'appareil de Pillow —
    elle est nommée telle quelle partout (écran, cartouche, avertissement du
    plan), parce qu'elle n'a ni retrait des sous-couleurs ni noir squelette.
    """
    rgb = _flatten(im)
    if p.color == "rgb":
        return rgb, "RGB"
    if p.color == "cmyk_icc" and p.icc:
        from PIL import ImageCms
        src = ImageCms.getOpenProfile(io.BytesIO(srgb_icc()))
        dst = ImageCms.getOpenProfile(io.BytesIO(p.icc))
        tr = ImageCms.buildTransform(src, dst, "RGB", "CMYK",
                                     renderingIntent=0)
        return ImageCms.applyTransform(rgb, tr), "CMYK/ICC"
    return rgb.convert("CMYK"), "CMYK"


def _image_xobject(writer, im: Image.Image, p: Plan, cache: dict, cs_ref):
    """Un XObject image prêt à poser, MÉMOÏSÉ sur le contenu.

    Deux cartes identiques (un jeu en a toujours : les jetons, les dos, les
    « rebut ») partageaient jusqu'ici deux flux encodés séparément. Sur un
    jeu de 300 cartes, cela faisait des dizaines de mégaoctets à téléverser
    chez l'imprimeur pour rien. La clé est le sha1 des OCTETS ENCODÉS : deux
    entrées ne fusionnent que si le flux livré est rigoureusement le même.

    Sans perte -> `FlateDecode` (RGB ou CMYK brut zlib). Avec perte ->
    JPEG **4:4:4** encodé ici : `subsampling=0`. Le défaut de Pillow est
    4:2:0, qui divise par deux la définition de la chrominance — exactement
    ce qui se voit sur un filet d'or de 0,3 mm posé sur du bleu nuit."""
    from pypdf.generic import (DecodedStreamObject, NameObject, NumberObject)
    out, _tag = to_output_space(im, p)
    ncomp = 4 if out.mode == "CMYK" else 3
    if p.lossless:
        data, filt = zlib.compress(out.tobytes(), 6), "/FlateDecode"
    else:
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=int(p.jpeg_quality), subsampling=0,
                 optimize=True, dpi=(p.dpi, p.dpi))
        data, filt = buf.getvalue(), "/DCTDecode"
    key = hashlib.sha1(data).hexdigest() + f":{out.size[0]}x{out.size[1]}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    xo = DecodedStreamObject()
    xo.set_data(data)
    xo[NameObject("/Type")] = NameObject("/XObject")
    xo[NameObject("/Subtype")] = NameObject("/Image")
    xo[NameObject("/Width")] = NumberObject(out.size[0])
    xo[NameObject("/Height")] = NumberObject(out.size[1])
    # ÉTIQUETER, pas laisser deviner : un /DeviceRGB muet ne dit pas au RIP
    # ce que valent les nombres. Avec un profil, l'image porte son espace.
    if cs_ref is not None and ((ncomp == 3 and p.color == "rgb")
                               or (ncomp == 4 and p.color == "cmyk_icc")):
        xo[NameObject("/ColorSpace")] = cs_ref
    else:
        xo[NameObject("/ColorSpace")] = NameObject(
            "/DeviceCMYK" if ncomp == 4 else "/DeviceRGB")
    xo[NameObject("/BitsPerComponent")] = NumberObject(8)
    xo[NameObject("/Filter")] = NameObject(filt)
    ref = writer._add_object(xo)
    cache[key] = ref
    return ref


def _icc_stream(writer, data: bytes, n: int):
    """Un profil ICC embarqué, en flux Flate. Sert à la fois de
    `/DestOutputProfile` (intention de sortie) et de base d'un espace
    `/ICCBased` (étiquetage des images)."""
    from pypdf.generic import (DecodedStreamObject, NameObject, NumberObject)
    st = DecodedStreamObject()
    st.set_data(zlib.compress(data, 6))
    st[NameObject("/N")] = NumberObject(int(n))
    st[NameObject("/Filter")] = NameObject("/FlateDecode")
    return writer._add_object(st)


def _registration_cs(writer):
    """L'espace `/Separation /All /DeviceCMYK` : UNE encre logique qui sort
    à 100 % sur les QUATRE plaques. C'est la seule couleur avec laquelle un
    trait de coupe repère quoi que ce soit — un rouge RVB se sépare en
    magenta + jaune et laisse le cyan et le noir vierges."""
    from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject,
                               NameObject, NumberObject)
    fn = DictionaryObject()
    fn[NameObject("/FunctionType")] = NumberObject(2)
    fn[NameObject("/Domain")] = ArrayObject([FloatObject(0), FloatObject(1)])
    fn[NameObject("/C0")] = ArrayObject([FloatObject(0)] * 4)
    fn[NameObject("/C1")] = ArrayObject([FloatObject(1)] * 4)
    fn[NameObject("/N")] = NumberObject(1)
    return ArrayObject([NameObject("/Separation"), NameObject("/All"),
                        NameObject("/DeviceCMYK"), writer._add_object(fn)])


OCG_LAYERS = (("marks", "Repères de coupe et de repérage"),
              ("slug", "Cartouche de traçabilité"))


def _optional_content(writer):
    """DES CALQUES QUE L'IMPRIMEUR DÉCOCHE — `/OCProperties` + un `/OCG` par
    couche non imprimante.

    Reproche mesuré : « Les repères de coupe et le cartouche sont dans le même
    flux de contenu que les cartes... il n'y a pas de calque optionnel
    (/OCProperties absent, 0 occurrence) : un imprimeur qui veut retirer les
    repères ou le cartouche doit éditer le flux. » Il n'a plus à le faire.

    Les deux groupes partent ALLUMÉS (`/BaseState /ON`) : un fichier
    d'imposition doit s'ouvrir tel qu'il s'imprime."""
    from pypdf.generic import (ArrayObject, DictionaryObject, NameObject,
                               TextStringObject)
    refs, ordre = {}, []
    for cle, titre in OCG_LAYERS:
        d = DictionaryObject()
        d[NameObject("/Type")] = NameObject("/OCG")
        d[NameObject("/Name")] = TextStringObject(titre)
        ref = writer._add_object(d)
        refs[cle] = ref
        ordre.append(ref)
    dflt = DictionaryObject()
    dflt[NameObject("/BaseState")] = NameObject("/ON")
    dflt[NameObject("/ON")] = ArrayObject(list(ordre))
    dflt[NameObject("/Order")] = ArrayObject(list(ordre))
    props = DictionaryObject()
    props[NameObject("/OCGs")] = ArrayObject(list(ordre))
    props[NameObject("/D")] = dflt
    writer._root_object[NameObject("/OCProperties")] = props
    return refs


def _oc_open(res, ocg: dict, cle: str) -> bytes:
    """Ouvre le calque `cle` sur cette page — et déclare la ressource
    `/Properties` qui le nomme. Sans calque : rien, pas même un octet."""
    if not ocg or cle not in ocg:
        return b""
    from pypdf.generic import DictionaryObject, NameObject
    props = res.get(NameObject("/Properties"))
    if props is None:
        props = DictionaryObject()
        res[NameObject("/Properties")] = props
    nom = "/OC" + cle
    props[NameObject(nom)] = ocg[cle]
    return ("/OC %s BDC " % nom).encode("ascii")


def _oc_close(ocg: dict, cle: str) -> bytes:
    return b" EMC" if (ocg and cle in ocg) else b""


def _output_intents(writer, oi: dict, claim: bool):
    """`/OutputIntents` sur le catalogue. Pour une condition de production
    NORMALISÉE désignée par son nom du registre ICC, le profil embarqué est
    facultatif (PDF 32000-1 §14.11.5) : c'est le chemin qu'attendent les
    portails d'imprimeurs. Pour un profil fourni, il est embarqué.

    LE SOUS-TYPE EST CONDITIONNEL. `/GTS_PDFX` n'est écrit qu'avec sa version
    — et seulement quand `claim` est vrai, c'est-à-dire quand l'intention
    décrit une presse (cf. `_pdfx_ok`) ET que rien d'autre dans le fichier ne
    contredit la conformité (les calques optionnels, par exemple). Sinon,
    sous-type d'extension : l'intention est décrite, rien n'est promis."""
    from pypdf.generic import (ArrayObject, DictionaryObject, NameObject,
                               TextStringObject)
    d = DictionaryObject()
    d[NameObject("/Type")] = NameObject("/OutputIntent")
    d[NameObject("/S")] = NameObject(PDFX_SUBTYPE if claim else SRC_SUBTYPE)
    if claim:
        d[NameObject("/GTS_PDFXVersion")] = TextStringObject(PDFX_VERSION)
    d[NameObject("/OutputConditionIdentifier")] = TextStringObject(oi["id"])
    d[NameObject("/OutputCondition")] = TextStringObject(oi["cond"])
    if oi.get("registry"):
        d[NameObject("/RegistryName")] = TextStringObject(oi["registry"])
    d[NameObject("/Info")] = TextStringObject(oi["cond"])
    if oi.get("profile"):
        d[NameObject("/DestOutputProfile")] = _icc_stream(
            writer, oi["profile"], oi["n"])
    writer._root_object[NameObject("/OutputIntents")] = ArrayObject([d])


# ── XMP : LA MÊME INFORMATION, LISIBLE PAR UNE MACHINE ───────────────────────
#
# Tout le diagnostic vivait dans `/Info` (DocInfo), que les chaînes de
# prépresse modernes ne lisent plus — et dans un cartouche qu'un humain lit à
# la loupe. Le paquet XMP porte les MÊMES chiffres, dans un espace de noms
# nommé, non compressé, et la revendication PDF/X y figure aussi quand elle
# est tenue (`pdfxid`).

def _xml_esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def xmp_packet(fields: dict, title: str, pdfx: bool) -> bytes:
    """Le paquet XMP, écrit à la main (aucune dépendance réseau, aucun
    générateur : ce dépôt ne livre que PIL + pypdf)."""
    when = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    when = when[:-2] + ":" + when[-2:] if len(when) > 5 else when
    lignes = "".join(
        f"      <cardforge:{k}>{_xml_esc(v)}</cardforge:{k}>\n"
        for k, v in fields.items())
    # L'espace de noms `pdfxid` n'est même pas DÉCLARÉ quand rien n'est
    # revendiqué : un fichier qui ne promet pas PDF/X ne doit pas en porter la
    # moindre trace, pas même un attribut xmlns qu'un lecteur pressé prendrait
    # pour une conformité.
    px = (f'      <pdfxid:GTS_PDFXVersion>{PDFX_VERSION}'
          f'</pdfxid:GTS_PDFXVersion>\n' if pdfx else "")
    nsx = ('    xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"\n'
           if pdfx else "")
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about=""\n'
        '    xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '    xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
        '    xmlns:pdf="http://ns.adobe.com/pdf/1.3/"\n'
        f'{nsx}'
        '    xmlns:cardforge="https://deepotus.local/ns/cardforge/1.0/">\n'
        f'   <dc:format>application/pdf</dc:format>\n'
        f'   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">'
        f'{_xml_esc(title)}</rdf:li></rdf:Alt></dc:title>\n'
        f'   <xmp:CreateDate>{when}</xmp:CreateDate>\n'
        f'   <xmp:ModifyDate>{when}</xmp:ModifyDate>\n'
        f'   <xmp:CreatorTool>Deepotus Card Forge</xmp:CreatorTool>\n'
        f'   <pdf:Producer>Deepotus Card Forge</pdf:Producer>\n'
        f'{px}'
        '   <cardforge:mesures rdf:parseType="Resource">\n'
        f'{lignes}'
        '   </cardforge:mesures>\n'
        '  </rdf:Description>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        '<?xpacket end="w"?>\n').encode("utf-8")


def _attach_xmp(writer, packet: bytes):
    """Le paquet, en flux NON COMPRESSÉ sur le catalogue — un XMP zippé n'est
    plus lisible par les outils qui le cherchent à l'octet."""
    from pypdf.generic import DecodedStreamObject, NameObject
    st = DecodedStreamObject()
    st.set_data(packet)
    st[NameObject("/Type")] = NameObject("/Metadata")
    st[NameObject("/Subtype")] = NameObject("/XML")
    writer._root_object[NameObject("/Metadata")] = writer._add_object(st)


def build_pdf(p: Plan, fronts: dict[int, Image.Image],
              backs: dict[int, Image.Image] | None = None,
              name: str = "Jeu", control: str = "") -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject,
                               DictionaryObject, FloatObject, NameObject,
                               RectangleObject)

    backs = backs or {}
    w = PdfWriter()
    # ── CE QU'ON REVENDIQUE DÉPEND DE CE QU'ON ÉCRIT, ET DE RIEN D'AUTRE ───
    #    Le contenu optionnel est une construction PDF 1.5 ; PDF/X-3:2003 est
    #    bâti sur PDF 1.4 et ne l'admet pas. Les deux ne peuvent donc pas
    #    coexister, et c'est le CALQUE qui l'emporte — parce qu'il est
    #    demandé explicitement, et parce qu'un fichier qui porte les deux
    #    serait refusé par le premier contrôle de conformité venu.
    claim = bool(p.out_intent and p.out_intent.get("pdfx")) and not p.layers
    # `/OutputIntents` est une construction PDF 1.4 ; pypdf écrit 1.3 par
    # défaut. Un fichier qui porte une intention sous un en-tête 1.3 se
    # contredit lui-même dès le premier octet — relevé, corrigé.
    w.pdf_header = "%PDF-1.5" if p.layers else "%PDF-1.4"
    ocg = _optional_content(w) if p.layers else {}
    if p.out_intent:
        _output_intents(w, p.out_intent, claim)
    # L'espace d'étiquetage des images : le profil de l'intention quand il y
    # en a un, sinon rien (et les images restent en /Device*, ce que le plan
    # signale comme un défaut au lieu de le taire).
    cs_ref = None
    oi = p.out_intent
    if oi and oi.get("profile"):
        want = 4 if p.color == "cmyk_icc" else 3
        if oi["n"] == want:
            cs_ref = ArrayObject([NameObject("/ICCBased"),
                                  _icc_stream(w, oi["profile"], oi["n"])])
    if cs_ref is None and p.color == "cmyk_icc" and p.icc:
        cs_ref = ArrayObject([NameObject("/ICCBased"),
                              _icc_stream(w, p.icc, 4)])
    if cs_ref is None and p.color == "rgb":
        cs_ref = ArrayObject([NameObject("/ICCBased"),
                              _icc_stream(w, srgb_icc(), 3)])
    reg_cs = _registration_cs(w) if p.mark_space == "registration" else None
    xcache: dict = {}
    order: list[tuple[int, str]] = []
    if p.duplex and p.duplex_order == "grouped":
        order = ([(k, "front") for k in range(p.pages)]
                 + [(k, "back") for k in range(p.pages)])
    else:
        for k in range(p.pages):
            order.append((k, "front"))
            if p.duplex:
                order.append((k, "back"))

    pt = 72.0 / p.dpi
    raster_w = px2pt(p.sheet_px[0], p.dpi)
    raster_h = px2pt(p.sheet_px[1], p.dpi)
    # ── LA PAGE : LA GRILLE DU RASTER, OU L'ISO EXACT ─────────────────────
    #    2480 px à 300 DPI valent 595,2 pt — la seule échelle qui fasse
    #    décrire au PDF et à la planche PNG la MÊME feuille. Mais 595,2 pt
    #    n'est pas l'A4 de l'ISO (595,2756), et un RIP d'imposition qui
    #    attend du A4 exact lève un avertissement de format : les deux
    #    contrôles l'ont relevé. `page_iso` donne la page ISO au micron, avec
    #    l'imposition CENTRÉE dedans — l'écart n'est plus subi, il est choisi,
    #    et les deux valeurs sont affichées.
    page_w, page_h = page_pt(p)
    dx, dy = (page_w - raster_w) / 2.0, (page_h - raster_h) / 2.0

    def X(v: float) -> float:
        """px de planche -> points de PAGE (axe x)."""
        return px2pt(v, p.dpi) + dx

    def Y(v: float) -> float:
        """px de planche, axe DESCENDANT -> points de PAGE, axe montant."""
        return px2pt(p.sheet_px[1] - v, p.dpi) + dy

    for page_i, side in order:
        # Le verso est le MIROIR PHYSIQUE du recto : cases, fond perdu
        # conservé, repères et cartouche sortent tous de ce plan-là.
        ps = side_plan(p, side)
        page = w.add_blank_page(width=page_w, height=page_h)
        res = page[NameObject("/Resources")]
        xdict = DictionaryObject()
        ops: list[bytes] = []
        src = backs if side == "back" else fronts
        tl = [1e18, 1e18, -1e18, -1e18]        # emprise des rognes (px)
        bl = [1e18, 1e18, -1e18, -1e18]        # emprise fond perdu compris

        for k, (r, c, idx) in enumerate(cells_for_page(p, page_i, side)):
            im = src.get(idx)
            if im is None:
                continue
            # ── LA TOILE ENTIÈRE, DÉTOURÉE — pas un découpage.
            #    Découper le bitmap avant de le poser obligeait à arrondir la
            #    coupe au pixel (0,244 px de blanc restait entre deux fonds
            #    perdus, mesuré) ET rendait chaque carte unique : cinq cartes
            #    rigoureusement identiques donnaient cinq flux différents dès
            #    qu'elles ne tombaient pas dans la même case. Un chemin de
            #    rognage `re W n` fait le travail à la coordonnée EXACTE, et
            #    l'XObject redevient la carte elle-même — donc partageable.
            x, y, cw, chh = cell_rect(ps, r, c)
            kl, kt, kr, kb = keep_bleed(ps, r, c)
            bx, by = p.geom.bleed_off_px
            px0, py0 = x - bx, y - by           # coin de la TOILE, en px
            iw, ih = im.size
            ref = _image_xobject(w, im, p, xcache, cs_ref)
            key = "/Im%d" % k
            xdict[NameObject(key)] = ref
            cx0, cy0 = x - kl, y - kt
            cw2, ch2 = cw + kl + kr, chh + kt + kb
            # PDF : origine en BAS à gauche -> on retourne l'axe y.
            ops.append(("q %s %s %s %s re W n %s 0 0 %s %s %s cm %s Do Q" % (
                _pdf_num(X(cx0)), _pdf_num(Y(cy0 + ch2)),
                _pdf_num(px2pt(cw2, p.dpi)), _pdf_num(px2pt(ch2, p.dpi)),
                _pdf_num(px2pt(iw, p.dpi)), _pdf_num(px2pt(ih, p.dpi)),
                _pdf_num(X(px0)), _pdf_num(Y(py0 + ih)),
                key)).encode("ascii"))
            tl = [min(tl[0], x), min(tl[1], y), max(tl[2], x + cw),
                  max(tl[3], y + chh)]
            bl = [min(bl[0], cx0), min(bl[1], cy0), max(bl[2], cx0 + cw2),
                  max(bl[3], cy0 + ch2)]

        segs = mark_segments(ps)
        if segs:
            if p.mark_space == "registration":
                csd = res.get(NameObject("/ColorSpace"))
                if csd is None:
                    csd = DictionaryObject()
                    res[NameObject("/ColorSpace")] = csd
                csd[NameObject("/CSreg")] = reg_cs
                ink = b"/CSreg CS 1 SCN"
            elif p.mark_space == "cmyk_black":
                ink = b"0 0 0 1 K"
            else:
                ink = ("%s %s %s RG" % (
                    _pdf_num(p.mark_rgb[0] / 255.0),
                    _pdf_num(p.mark_rgb[1] / 255.0),
                    _pdf_num(p.mark_rgb[2] / 255.0))).encode("ascii")
            # Contenu BALISÉ (`BMC`/`EMC`, sans dictionnaire de propriétés) :
            # la coupe et le cartouche se retrouvent dans le flux sans avoir
            # à deviner. Un outil de prépresse — et le test qui mesure la
            # gouttière sur le FICHIER — sait ce qu'il lit. Quand les calques
            # sont demandés, ce bloc est de plus DANS un groupe de contenu
            # optionnel : l'imprimeur décoche « Repères de coupe » au lieu
            # d'éditer le flux.
            ops.append(_oc_open(res, ocg, "marks") + b"/CFmarks BMC q " + ink
                       + (" %s w 1 J" % _pdf_num(
                           px2pt(p.mark_w_px, p.dpi))).encode("ascii"))
            for x0, y0, x1, y1 in segs:
                ops.append(("%s %s m %s %s l S" % (
                    _pdf_num(X(x0)), _pdf_num(Y(y0)),
                    _pdf_num(X(x1)), _pdf_num(Y(y1)))).encode("ascii"))
            ops.append(b"Q EMC" + _oc_close(ocg, "marks"))

        # ── LE CARTOUCHE, EN TRACÉS. Aucun objet /Font n'est créé : rien à
        #    incorporer, donc rien qui puisse manquer chez le prestataire, et
        #    aucun encodage à deviner (l'ancien /Helvetica sans /Encoding
        #    imprimait « zone sßre » — 0xFB = germandbls en StandardEncoding).
        lay = slug_layout(ps, name, page_i, side)
        if lay:
            polys, lw_px = lay
            ops.append(_oc_open(res, ocg, "slug")
                       + ("/CFslug BMC q 0.42 0.42 0.42 RG %s w 1 J 1 j"
                          % _pdf_num(px2pt(lw_px, p.dpi))).encode("ascii"))
            for poly in polys:
                seq = " ".join(
                    "%s %s %s" % (_pdf_num(X(px)), _pdf_num(Y(py)),
                                  "m" if i == 0 else "l")
                    for i, (px, py) in enumerate(poly))
                ops.append((seq + " S").encode("ascii"))
            ops.append(b"Q EMC" + _oc_close(ocg, "slug"))

        cs = DecodedStreamObject()
        cs.set_data(b"\n".join(ops) if ops else b"")
        page[NameObject("/Contents")] = w._add_object(cs)
        if xdict:
            res[NameObject("/XObject")] = xdict

        # ── LES BOÎTES. C'est là que se joue le duel : un PDF nanDECK n'a
        #    que /MediaBox, et l'imprimeur doit deviner où couper.
        if p.trimbox == "page" or tl[2] < tl[0]:
            trim = (0.0, 0.0, float(p.sheet_px[0]), float(p.sheet_px[1]))
            bleed = trim
        else:
            trim = tuple(tl)
            bleed = tuple(bl)
        def _box(b) -> RectangleObject:
            """px (origine haut-gauche) -> RectangleObject en points
            (origine BAS-gauche, comme tout le PDF)."""
            return RectangleObject([
                FloatObject(round(X(b[0]), 4)), FloatObject(round(Y(b[3]), 4)),
                FloatObject(round(X(b[2]), 4)), FloatObject(round(Y(b[1]), 4))])

        page.trimbox = _box(trim)
        page.bleedbox = _box(bleed)
        # ── ArtBox = LA ZONE SÛRE. La moitié mesurable du cahier des charges
        #    dit « fond perdu ET zone de sécurité » : les trois cadres sont
        #    donc DANS le fichier, emboîtés, Bleed ⊃ Trim ⊃ Art, et pas
        #    seulement dessinés à l'écran pendant qu'on compose.
        if p.artbox == "safe" and p.trimbox != "page" and tl[2] >= tl[0]:
            sx = p.geom.safe_off_px[0] - p.geom.bleed_off_px[0]
            sy = p.geom.safe_off_px[1] - p.geom.bleed_off_px[1]
            art = (trim[0] + sx, trim[1] + sy, trim[2] - sx, trim[3] - sy)
            if art[2] <= art[0] or art[3] <= art[1]:
                art = trim
        else:
            art = trim
        page.artbox = _box(art)

    edge, inner = bleed_mm_sides(p)
    redge, rinner = bleed_mm_sides(p, raster=True)
    zx, zy = safe_inset_written_mm(p)
    zsure = (f"zone sure reglee {_mm(p.geom.safe_mm)} mm : retrait ecrit "
             f"{zx:.3f} / {zy:.3f} mm ({p.geom.safe_px[0]}x{p.geom.safe_px[1]} px"
             + (", ArtBox)" if p.artbox == "safe" else ")"))
    oi = p.out_intent
    mots = "; ".join(([control] if control else []) + [
        f"fond perdu pose {_mm(edge)} mm bord / {_mm(inner)} mm gouttiere "
        f"(PDF) et {_mm(redge)} / {_mm(rinner)} mm (planche PNG, au pixel)",
        zsure,
        f"{p.dpi} DPI", f"grille {p.cols}x{p.rows}",
        ("intention " + oi["id"]) if oi else "sans intention de sortie",
        {"rgb": "visuels RGB", "cmyk_device": "visuels CMYK d'appareil",
         "cmyk_icc": "visuels CMYK par profil ICC"}[p.color],
        {"registration": "reperes en couleur de reperage (Separation All)",
         "cmyk_black": "reperes noir 100%", "rgb": "reperes RGB"}[p.mark_space],
        "sans perte" if p.lossless else f"JPEG q{p.jpeg_quality} 4:4:4",
    ] + [str(x.get("message", "")) for x in p.warnings])
    # `/Subject` COURT : beaucoup de portails d'impression tronquent ce champ
    # à l'affichage, et c'est la ligne la plus utile qui sautait. L'essentiel
    # tient ici, le détail va dans /Keywords ET dans le XMP.
    court = (f"{p.geom.label} {p.geom.trim_px[0]}x{p.geom.trim_px[1]} px · "
             f"{p.dpi} DPI · fond perdu posé {_mm(edge)}/{_mm(inner)} mm · "
             f"{p.cols}x{p.rows}/page · {p.out_pages} page(s)")
    quand = datetime.now().astimezone().strftime("D:%Y%m%d%H%M%S%z")
    quand = quand[:-2] + "'" + quand[-2:] + "'" if len(quand) > 8 else quand
    w.add_metadata({"/Producer": "Deepotus Card Forge",
                    "/Creator": "Card Forge P7", "/Title": name[:120],
                    "/CreationDate": quand, "/ModDate": quand,
                    "/Subject": court[:250],
                    # Le diagnostic voyage AVEC le fichier : l'imprimeur lit
                    # ce que l'ecran disait, la ou il le lira vraiment.
                    "/Keywords": mots[:1800]})
    # `/Trapped` est un NOM, pas une chaîne : `(/False)` ne vaut rien.
    w._info[NameObject("/Trapped")] = NameObject("/False")
    _attach_xmp(w, xmp_packet({
        "format": p.geom.label,
        "coupe_px": f"{p.geom.trim_px[0]}x{p.geom.trim_px[1]}",
        "toile_px": f"{p.geom.canvas_px[0]}x{p.geom.canvas_px[1]}",
        "zone_sure_px": f"{p.geom.safe_px[0]}x{p.geom.safe_px[1]}",
        # LE RETRAIT ÉCRIT, PAS LE RÉGLAGE. « zone sûre 3 mm » et une /ArtBox
        # posée à 2,963 mm sur un axe : l'écart part maintenant avec le
        # fichier, mesuré, au lieu d'être arrondi à l'affichage.
        "zone_sure_retrait_ecrit_mm": f"{zx:.3f}/{zy:.3f}",
        "zone_sure_reglee_mm": f"{p.geom.safe_mm:g}",
        "dpi_grille": str(p.dpi),
        "fond_perdu_regle_mm": f"{p.geom.bleed_mm:g}",
        "fond_perdu_pose_bord_mm": f"{edge:.2f}",
        "fond_perdu_pose_gouttiere_mm": f"{inner:.2f}",
        "fond_perdu_planche_png_mm": f"{redge:.2f}/{rinner:.2f}",
        "gouttiere_pt": f"{px2pt(p.gutter_px, p.dpi):.4f}",
        "grille": f"{p.cols}x{p.rows}",
        "pages": str(p.out_pages),
        "espace_visuels": p.color,
        "encre_reperes": p.mark_space,
        "reperes_en_gouttiere": str(gutter_marks(p)),
        # LA DÉRIVE TOLÉRÉE, MESURÉE SUR LES SEGMENTS ÉCRITS. Elle était
        # AFFIRMÉE à l'écran (« 2 mm », le fond perdu restant) et absente du
        # fichier : le trait allait d'une coupe à l'autre et touchait la
        # carte. C'est la distance dont dépend le massicot, elle part donc
        # avec la planche.
        "reperes_traits": str(len(mark_segments(p))),
        "reperes_derive_toleree_mm": (f"{mark_clearance_mm(p):.2f}"
                                      if mark_clearance_mm(p) >= 0
                                      else "sans objet (aucun repère)"),
        "reperes_touchant_une_carte": str(mark_touch(p)),
        # LE CRITÈRE 9, MESURÉ. Ni l'un ni l'autre des deux contrôles n'avait
        # pu vérifier le miroir : il voyage maintenant AVEC le fichier.
        "miroir_recto_verso_um": (f"{mirror_um(p):.1f}" if p.duplex
                                  else "sans objet (recto seul)"),
        "page_pt": f"{page_w:.4f}x{page_h:.4f}",
        "calques_optionnels": ("repères + cartouche" if p.layers else "aucun"),
        "intention": (oi["id"] if oi else "aucune"),
        "conformite_pdfx": (PDFX_VERSION if claim else "aucune revendication"),
        # ── LE CONTRÔLE AVANT VOL VOYAGE AVEC LE FICHIER ──────────────────
        #    « Rien dans les fichiers livrés ne prouve que les règles par
        #    carte savent nommer une carte et sortir un chiffre. » Elles le
        #    prouvent ici : le verdict — nombre de règles, d'erreurs,
        #    d'avertissements — est écrit dans le fichier qui part, et un
        #    export FORCÉ malgré des erreurs porte l'aveu, carte par carte.
        "controle_avant_vol": control or "non fourni par l'appelant",
        "avertissements": " | ".join(str(x.get("message", ""))
                                     for x in p.warnings) or "aucun",
    }, name or "Jeu", claim))
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# AUDIT DU FICHIER LIVRÉ — LA SEULE SOURCE DES CHIFFRES AFFICHÉS
#
# Un contrôle a démontré qu'un badge peut être faux alors que l'en-tête le
# confirme : il suffit de s'arrêter à l'en-tête. Ici, on ne s'arrête pas au
# réglage. `pdf_audit()` OUVRE le PDF qui vient d'être écrit, relit chaque
# chose que le panneau affiche, et rend la mesure À CÔTÉ de l'affirmation.
# Ce que cette fonction ne peut pas mesurer, le panneau ne l'affiche pas.
# ══════════════════════════════════════════════════════════════════════════

def _rect(page, cle):
    """La boîte TELLE QU'ÉCRITE dans le dictionnaire de la page, ou None.

    PIÈGE : `page.trimbox` de pypdf retombe SILENCIEUSEMENT sur la MediaBox
    quand la boîte manque. Un audit qui l'interroge trouve donc quatre boîtes
    dans un fichier qui n'en porte qu'une. On lit la clé, pas la propriété."""
    try:
        if cle not in page:
            return None
        return [round(float(v), 4) for v in page[cle]]
    except Exception:
        return None


_CM_RE = None


def placements(page) -> list[tuple[float, float, float, float]]:
    """Les placements d'image de la page, RELUS DANS LE FLUX : (w, h, x, y)
    en points, un par opérateur `cm` suivi d'un `Do`.

    C'est la mesure du miroir recto-verso au niveau où elle vaut quelque
    chose : pas la géométrie qu'on voulait, celle que le fichier porte."""
    global _CM_RE
    if _CM_RE is None:
        import re
        _CM_RE = re.compile(
            rb"(-?[\d.]+) 0 0 (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) cm\s*/\w+ Do")
    try:
        flux = page.get_contents().get_data()
    except Exception:
        return []
    out = []
    for m in _CM_RE.finditer(flux):
        try:
            out.append(tuple(float(m.group(i)) for i in (1, 2, 3, 4)))
        except ValueError:
            continue
    return out


_MARK_RE = None


def mark_clearance_bytes(page) -> tuple[float, int, int]:
    """LA DÉRIVE TOLÉRÉE, RELUE DANS LE FICHIER ÉCRIT : (mm, nb de traits,
    nb de traits qui touchent une carte). `(-1, 0, 0)` s'il n'y a rien à
    mesurer.

    Tout vient des octets de la page : les traits du bloc balisé `/CFmarks`,
    leur épaisseur de l'opérateur `w`, les cartes des placements d'image et
    de la cellule de coupe déduite. Aucun réglage n'entre ici — c'est la
    différence entre « l'écran annonce 2 mm » et « le fichier porte 1 mm »."""
    global _MARK_RE
    if _MARK_RE is None:
        import re
        _MARK_RE = re.compile(
            rb"(-?[\d.]+) (-?[\d.]+) m (-?[\d.]+) (-?[\d.]+) l S")
    try:
        flux = page.get_contents().get_data()
    except Exception:
        return (-1.0, 0, 0)
    i = flux.find(b"/CFmarks BMC")
    if i < 0:
        return (-1.0, 0, 0)
    j = flux.find(b"EMC", i)
    zone = flux[i:j if j > 0 else len(flux)]
    segs = [tuple(float(m.group(k)) for k in (1, 2, 3, 4))
            for m in _MARK_RE.finditer(zone)]
    if not segs:
        return (-1.0, 0, 0)
    import re as _re
    mw = _re.search(rb"([\d.]+) w", zone)
    demi = (float(mw.group(1)) / 2.0) if mw else 0.0
    cell = trim_cell_pt(page)
    pos = placements(page)
    if not cell or not pos:
        return (-1.0, len(segs), 0)
    cells = [(x + (w - cell[0]) / 2.0, y + (h - cell[1]) / 2.0,
              cell[0], cell[1]) for w, h, x, y in pos]
    pire, touche = float("inf"), 0
    for x0, y0, x1, y1 in segs:
        ax0, ax1 = min(x0, x1) - demi, max(x0, x1) + demi
        ay0, ay1 = min(y0, y1) - demi, max(y0, y1) + demi
        d = min(math.hypot(max(cx - ax1, ax0 - (cx + cw), 0.0),
                           max(cy - ay1, ay0 - (cy + ch), 0.0))
                for cx, cy, cw, ch in cells)
        pire = min(pire, d)
        if d <= 1e-9:
            touche += 1
    return (round(pire / 72.0 * MM_PER_INCH, 4), len(segs), touche)


def mirror_um_bytes(data: bytes, order: str = "interleave") -> float:
    """L'ÉCART AU MIROIR, EN MICRONS, MESURÉ SUR LE PDF LIVRÉ.

    Pour chaque paire (recto, verso), on relit les placements des deux pages
    dans le flux et on compare la position du verso à la position miroir du
    recto par rapport à l'axe de pliage de la page. -1 = rien à mesurer (pas
    de recto-verso, ou pages dépareillées).

    Le miroir de la TOILE vaut celui de la ROGNE : la toile déborde de la
    même valeur des deux côtés de la rogne, donc la symétrie se conserve."""
    from pypdf import PdfReader
    try:
        r = PdfReader(io.BytesIO(data))
        pages = list(r.pages)
    except Exception:
        return -1.0
    n = len(pages)
    if n < 2 or n % 2:
        return -1.0
    demi = n // 2
    paires = ([(i, i + demi) for i in range(demi)] if order == "grouped"
              else [(2 * i, 2 * i + 1) for i in range(demi)])
    pire = 0.0
    vu = False
    for a, b in paires:
        fa, fb = placements(pages[a]), placements(pages[b])
        if not fa or len(fa) != len(fb):
            continue
        try:
            pw = float(pages[a].mediabox.width)
            ph = float(pages[a].mediabox.height)
        except Exception:
            continue
        for (w1, h1, x1, y1), (w2, h2, x2, y2) in zip(fa, fb):
            vu = True
            # Un seul des deux axes se retourne ; on prend le meilleur des
            # deux hypothèses de pli, sinon on mesurerait le pli qu'on n'a pas.
            dl = max(abs(x2 - (pw - (x1 + w1))), abs(y2 - y1))
            dc = max(abs(y2 - (ph - (y1 + h1))), abs(x2 - x1))
            pire = max(pire, min(dl, dc))
    if not vu:
        return -1.0
    return round(pt2um(pire), 1)


def trim_cell_pt(page) -> tuple[float, float] | None:
    """LA CELLULE DE COUPE D'UNE CARTE, DÉDUITE DES SEULS OCTETS DE LA PAGE.

    Rien ici ne consulte le plan : on relit la /TrimBox écrite et les
    placements d'image du flux. Les abscisses distinctes donnent le nombre de
    colonnes et le PAS de la grille (cellule + gouttière) ; la /TrimBox
    couvre `(n-1)` pas plus une cellule, donc

        cellule = TrimBox - (colonnes - 1) x pas

    C'est la mesure qui permet de dire, sur le fichier livré, si la boîte que
    l'imprimeur lit vaut bien le format nominal — le reproche « la TrimBox
    déclare 62,992 x 87,9687 mm, pas 63 x 88 ». None quand la /TrimBox
    couvre la page entière (mode « page ») : il n'y a alors aucune cellule à
    déduire, et inventer un chiffre serait pire que se taire."""
    trim = _rect(page, "/TrimBox")
    media = _rect(page, "/MediaBox")
    if not trim:
        return None
    if media and all(abs(trim[i] - media[i]) < 1e-4 for i in range(4)):
        return None
    pos = placements(page)
    if not pos:
        return None
    # 4 décimales : la précision à laquelle `_pdf_num` écrit les matrices.
    # Arrondir plus court inventait 0,2 µm d'écart entre la mesure et le plan.
    xs = sorted({round(x, 4) for _w, _h, x, _y in pos})
    ys = sorted({round(y, 4) for _w, _h, _x, y in pos})
    tw, th = trim[2] - trim[0], trim[3] - trim[1]
    pw = (xs[1] - xs[0]) if len(xs) > 1 else 0.0
    ph = (ys[1] - ys[0]) if len(ys) > 1 else 0.0
    cw = tw - (len(xs) - 1) * pw
    ch = th - (len(ys) - 1) * ph
    if cw <= 0 or ch <= 0:
        return None
    return (round(cw, 4), round(ch, 4))


def match_format_mm(w_mm: float, h_mm: float) -> str:
    """Le format nominal le plus proche d'une rogne mesurée, ou "". Tolérance
    0,3 mm : assez pour reconnaître une rogne calée sur la grille du raster
    (l'écart le plus grand du catalogue vaut 31 µm), trop peu pour confondre
    deux formats — les deux plus proches, poker_eu et poker_us, sont séparés
    de 0,9 mm en distance du maximum."""
    best, dmin = "", 0.3
    for fid, f in FORMATS.items():
        a, b = f["trim_mm"]
        d = max(abs(w_mm - a), abs(h_mm - b))
        if d < dmin:
            best, dmin = fid, d
    return best


def pdf_audit(data: bytes, duplex_order: str = "") -> dict:
    """Tout ce que le panneau a le droit d'afficher, relu SUR LES OCTETS."""
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    entete = data[:8].decode("latin-1", "replace")
    root = r.trailer["/Root"]
    pages = list(r.pages)
    boites, hierarchie = 0, 0
    for pg in pages:
        m, t, b, a = (_rect(pg, "/MediaBox"), _rect(pg, "/TrimBox"),
                      _rect(pg, "/BleedBox"), _rect(pg, "/ArtBox"))
        if m and t and b and a:
            boites += 1
            if (b[0] <= t[0] + 1e-4 and b[1] <= t[1] + 1e-4
                    and b[2] >= t[2] - 1e-4 and b[3] >= t[3] - 1e-4
                    and a[0] >= t[0] - 1e-4 and a[1] >= t[1] - 1e-4
                    and a[2] <= t[2] + 1e-4 and a[3] <= t[3] + 1e-4):
                hierarchie += 1

    oi, sub, oid, ver, prof, cls = None, "", "", "", 0, ""
    try:
        oi = root["/OutputIntents"][0]
        sub = str(oi.get("/S", ""))
        oid = str(oi.get("/OutputConditionIdentifier", ""))
        ver = str(oi.get("/GTS_PDFXVersion", ""))
        if "/DestOutputProfile" in oi:
            octets = oi["/DestOutputProfile"].get_object().get_data()
            prof = len(octets)
            cls = octets[12:16].decode("latin-1", "replace").strip() \
                if len(octets) >= 132 and octets[36:40] == b"acsp" else "?"
    except Exception:
        oi = None

    xmp = data.count(b"<x:xmpmeta") if b"/Metadata" in data else 0
    xmp_pdfx = data.count(b"pdfxid:GTS_PDFXVersion") > 0
    # ── LE VERDICT DU CONTRÔLE, RELU DANS LES OCTETS ──────────────────────
    #    Pas depuis la réponse HTTP, pas depuis le plan : depuis le paquet
    #    XMP du fichier écrit. Un export forcé s'y avoue, et l'écran le lit
    #    là où l'imprimeur le lira.
    ctl = ""
    k0 = data.find(b"<cardforge:controle_avant_vol>")
    if k0 >= 0:
        k1 = data.find(b"</cardforge:controle_avant_vol>", k0)
        if k1 > k0:
            ctl = (data[k0 + 30:k1].decode("utf-8", "replace")
                   .replace("&amp;", "&").replace("&lt;", "<")
                   .replace("&gt;", ">").replace("&quot;", '"'))
    fonts = data.count(b"/Font") + data.count(b"/FontFile")
    trans = (data.count(b"/SMask") + data.count(b"/Group")
             + data.count(b"/Transparency"))
    devrgb = data.count(b"/DeviceRGB")
    icc = data.count(b"/ICCBased")
    chiffre = b"/Encrypt" in data
    trapped = str(r.metadata.get("/Trapped", "")) if r.metadata else ""
    # ── LA DÉRIVE TOLÉRÉE, MESURÉE SUR LE PIRE DES PAGES ──────────────────
    clr_mm, marks_n, marks_touch = -1.0, 0, 0
    for pg in pages:
        c, n, t = mark_clearance_bytes(pg)
        marks_n = max(marks_n, n)
        marks_touch = max(marks_touch, t)
        if c >= 0 and (clr_mm < 0 or c < clr_mm):
            clr_mm = c

    # ── LES CALQUES, LUS DANS LE CATALOGUE ────────────────────────────────
    calques: list[str] = []
    try:
        for g in root["/OCProperties"]["/OCGs"]:
            calques.append(str(g.get_object().get("/Name", "")))
    except Exception:
        calques = []
    # ── LA PAGE : CE QU'ELLE MESURE, ET SON ÉCART À L'ISO ─────────────────
    #    SIGNÉ, ET PAR AXE. Un maximum en valeur absolue disait « 26,7 µm »
    #    et laissait croire que les deux côtés manquaient : la largeur est
    #    26,7 µm SOUS le nominal, la hauteur 10,7 µm AU-DESSUS.
    media = _rect(pages[0], "/MediaBox") if pages else None
    iso_um = -1.0
    iso_xy: list[float] = []
    if media:
        pw, ph = media[2] - media[0], media[3] - media[1]
        for smm in (s["size_mm"] for s in SHEETS.values()):
            for a, b in ((smm[0], smm[1]), (smm[1], smm[0])):
                ax, ay = mm2pt(a), mm2pt(b)
                if abs(pw - ax) < 3.0 and abs(ph - ay) < 3.0:
                    d = pt2um(max(abs(pw - ax), abs(ph - ay)))
                    if iso_um < 0 or round(d, 1) < iso_um:
                        iso_um = round(d, 1)
                        iso_xy = [round(pt2um(pw - ax), 1),
                                  round(pt2um(ph - ay), 1)]
    # ── LA ROGNE ÉCRITE, DÉDUITE DU FLUX, ET SON ÉCART AU NOMINAL ─────────
    cell = trim_cell_pt(pages[0]) if pages else None
    trim_mm_v: list[float] = []
    trim_fmt, trim_xy = "", []
    if cell:
        tmm = (cell[0] / 72.0 * MM_PER_INCH, cell[1] / 72.0 * MM_PER_INCH)
        trim_mm_v = [round(tmm[0], 4), round(tmm[1], 4)]
        trim_fmt = match_format_mm(tmm[0], tmm[1])
        if trim_fmt:
            nom = FORMATS[trim_fmt]["trim_mm"]
            trim_xy = [round((tmm[0] - nom[0]) * 1000.0, 1),
                       round((tmm[1] - nom[1]) * 1000.0, 1)]
    miroir = mirror_um_bytes(data, duplex_order or "interleave")

    # LA REVENDICATION EST UNE CONJONCTION, PAS UNE ÉTIQUETTE.
    manques = []
    if sub == PDFX_SUBTYPE:
        # Contenu optionnel = PDF 1.5 ; PDF/X-3:2003 est bâti sur PDF 1.4.
        if calques:
            manques.append(f"{len(calques)} calque(s) optionnel(s) (PDF 1.5)")
        if not ver:
            manques.append("/GTS_PDFXVersion absent")
        if not xmp or not xmp_pdfx:
            manques.append("XMP pdfxid absent")
        if trapped not in ("/False", "/True", "False", "True"):
            manques.append("/Trapped absent")
        if entete < "%PDF-1.4":
            manques.append(f"en-tête {entete} < 1.4")
        if boites != len(pages):
            manques.append(f"boîtes sur {boites}/{len(pages)} pages")
        if fonts:
            manques.append(f"{fonts} occurrence(s) de police")
        if trans:
            manques.append(f"{trans} marqueur(s) de transparence")
        if chiffre:
            manques.append("fichier chiffré")
        if devrgb:
            manques.append(f"{devrgb} /DeviceRGB muet")
        if not prof and not str(oi.get("/RegistryName", "") if oi else ""):
            manques.append("ni profil embarqué ni registre")
    revendique = PDFX_VERSION if (sub == PDFX_SUBTYPE and not manques) else ""
    return {
        "header": entete, "pages": len(pages),
        "pages_4_boites": boites, "pages_boites_emboitees": hierarchie,
        "intent_subtype": sub, "intent_id": oid, "intent_version": ver,
        "intent_registry": str(oi.get("/RegistryName", "")) if oi else "",
        "profile_bytes": prof, "profile_class": cls,
        "xmp_blocks": xmp, "xmp_pdfx": xmp_pdfx, "trapped": trapped,
        "font_hits": fonts, "transparency_hits": trans,
        "devicergb_hits": devrgb, "iccbased_hits": icc,
        "ocg_count": len(calques), "ocg_names": calques,
        "media_pt": media, "iso_um": iso_um, "iso_um_xy": iso_xy,
        # LA CELLULE DE COUPE RELUE DANS LE FLUX, son format reconnu, et
        # l'écart signé au nominal. Tout vient des octets : /TrimBox + les
        # matrices `cm` des placements, rien du plan.
        "trim_cell_pt": list(cell) if cell else [],
        "trim_cell_mm": trim_mm_v, "trim_fmt": trim_fmt,
        "trim_um_xy": trim_xy,
        # LA DÉRIVE TOLÉRÉE, RELUE DANS LE FICHIER : distance de l'encre des
        # repères à la carte la plus proche. Elle était AFFIRMÉE (2 mm) là où
        # les octets en portaient 0 — l'audit la mesure maintenant au même
        # endroit que les boîtes et le miroir.
        "mark_clearance_mm": clr_mm, "marks_n": marks_n,
        "mark_touch": marks_touch,
        "mirror_um": miroir,
        "control": ctl, "control_forced": "EXPORT FORCE" in ctl,
        "encrypted": chiffre, "bytes": len(data),
        "pdfx": revendique, "pdfx_manques": manques,
        # Une revendication PDF/X n'est portée QUE si rien ne manque. Zéro
        # revendication + zéro manque = un fichier honnête, pas un échec.
        "ok": not manques,
    }


# ══════════════════════════════════════════════════════════════════════════
# CONTRÔLE AVANT VOL — le mot « safe » n'apparaît pas dans les 202 pages du
# manuel de nanDECK. Ici il a deux règles, un chiffre, et le nom de la carte.
# ══════════════════════════════════════════════════════════════════════════

def file_checks(body: dict, icc: bytes | None = None) -> list[dict]:
    """LES RÈGLES QUI PORTENT SUR LE FICHIER LIVRÉ, pas sur les cartes.

    Un contrôle avant vol réel (Acrobat, PitStop, portail d'imprimeur) lève
    d'abord deux alertes : police non incorporée, et absence d'intention de
    sortie. Elles sont donc contrôlées ICI, sur ce qui sera réellement écrit,
    et affichées au même endroit que les cartes fautives."""
    rows: list[dict] = []
    try:
        p = build_plan(body, int(body.get("n_cards") or 1), icc)
    except ValueError as e:
        return [{"kind": "plan_impossible", "level": "err", "card": "planche",
                 "card_i": -1, "slot": "", "value": 0, "limit": 0,
                 "message": str(e)}]
    for wv in p.warnings:
        rows.append({"kind": wv["kind"], "level": wv["level"],
                     "card": "planche", "card_i": -1, "slot": "",
                     "value": wv.get("value", 0), "limit": wv.get("limit", 0),
                     "message": wv["message"]})
    oi = p.out_intent
    rows.append({
        "kind": "intention_de_sortie", "level": "ok" if oi else "warn",
        "card": "fichier", "card_i": -1, "slot": "",
        "value": len(oi.get("profile") or b"") if oi else 0, "limit": 0,
        "message": (f"intention de sortie « {oi['id']} »"
                    + (f", profil ICC embarqué de "
                       f"{len(oi['profile'])} octets" if oi.get("profile")
                       else ", condition normalisée du registre ICC")
                    if oi else "aucune intention de sortie déclarée"),
    })
    # ── CE QU'ON DÉCLARE EN PDF/X, ET CE QU'ON N'Y DÉCLARE PAS ────────────
    #    Deux contrôles ont relevé le même défaut sur les octets : `/S
    #    /GTS_PDFX` posé sans `/GTS_PDFXVersion`, sans XMP, sans /Trapped.
    #    La ligne dit maintenant, AVANT l'export, ce que le fichier portera —
    #    et `pdf_audit()` le revérifie sur les octets écrits.
    if oi:
        rows.append({
            "kind": "conformite_pdfx",
            "level": "ok", "card": "fichier", "card_i": -1, "slot": "",
            "value": 0, "limit": 0,
            "message": (
                f"conformité {PDFX_VERSION} revendiquée : sous-type "
                f"{PDFX_SUBTYPE}, /GTS_PDFXVersion, XMP pdfxid, /Trapped, "
                f"en-tête %PDF-1.4"
                if (oi.get("pdfx") and not p.layers) else
                f"aucune revendication PDF/X : les calques optionnels sont du "
                f"PDF 1.5, que {PDFX_VERSION} n'admet pas. Décocher « calques "
                f"» pour revendiquer la conformité."
                if oi.get("pdfx") else
                f"aucune revendication PDF/X (sous-type {SRC_SUBTYPE}) : "
                f"« {oi['id']} » décrit "
                + ("la source, pas une presse"
                   if not oi.get("press") else "une presse sans profil de "
                   "sortie exploitable")
                + " — le fichier ne se présente donc pas comme ce qu'il "
                  "n'est pas"),
        })
    # ── LA DENSITÉ INSCRITE, PAS LA DENSITÉ RÉGLÉE ────────────────────────
    #    L'unité du chunk pHYs est le mètre entier : 300 DPI n'est pas
    #    représentable. On affiche la valeur écrite et le DPI qu'elle vaut.
    rows.append({
        "kind": "densite_inscrite", "level": "ok", "card": "fichier",
        "card_i": -1, "slot": "", "value": phys_ppm(p.dpi), "limit": p.dpi,
        "message": (f"densité écrite dans le PNG : pHYs {phys_ppm(p.dpi)} "
                    f"px/m, soit {phys_dpi(p.dpi):.4f} DPI (la maille entière "
                    f"la plus proche de {p.dpi} ; l'unité du chunk est le "
                    f"mètre)"),
    })
    # ── LA ROGNE ÉCRITE, PAS LA ROGNE NOMINALE ────────────────────────────
    #    « La TrimBox déclare 62,992 x 87,9687 mm, pas 63 x 88 mm. » Exact.
    #    La cellule de coupe est calée sur la grille du raster pour que le PDF
    #    et la planche PNG décrivent la même carte ; le prix est un écart de
    #    quelques microns, et il s'écrit au lieu de se deviner.
    tw, th = trim_written_mm(p)
    dx, dy = trim_gap_xy_um(p)
    exact = abs(dx) < 0.05 and abs(dy) < 0.05
    rows.append({
        "kind": "rogne_ecrite", "level": "ok",
        "card": "fichier", "card_i": -1, "slot": "",
        "value": max(abs(dx), abs(dy)), "limit": 0,
        "message": (
            f"rogne écrite dans la /TrimBox : {p.geom.trim_px[0]}x"
            f"{p.geom.trim_px[1]} px = {tw:.4f} x {th:.4f} mm"
            + (f" — le format nominal exact ({p.geom.trim_mm[0]:g} x "
               f"{p.geom.trim_mm[1]:g} mm)" if exact else
               f", soit {dx:+.1f} / {dy:+.1f} µm du format nominal "
               f"{p.geom.trim_mm[0]:g} x {p.geom.trim_mm[1]:g} mm (la cellule "
               f"est calée sur la grille de {p.dpi} DPI, pour que le PDF et la "
               f"planche PNG décrivent la même carte)")),
    })
    # ── LA ZONE SÛRE ÉCRITE, PAS LA ZONE SÛRE RÉGLÉE ──────────────────────
    #    Le cartouche annonçait « zone sûre 3 mm » et l'/ArtBox posait un
    #    retrait de 3,006 mm en largeur et 2,963 mm en hauteur : 37 µm de
    #    marge promise que le fichier ne portait pas sur un axe. Le chiffre
    #    est mesuré et écrit ; c'est la même règle que pour la rogne.
    zx, zy = safe_inset_written_mm(p)
    zdx, zdy = safe_gap_xy_um(p)
    zw, zh = safe_written_mm(p)
    rows.append({
        "kind": "zone_sure_ecrite", "level": "ok",
        "card": "fichier", "card_i": -1, "slot": "",
        "value": max(abs(zdx), abs(zdy)), "limit": 0,
        "message": (
            f"zone sûre écrite {'en /ArtBox ' if p.artbox == 'safe' else ''}"
            f": {p.geom.safe_px[0]}x{p.geom.safe_px[1]} px = {zw:.3f} x "
            f"{zh:.3f} mm, retrait {zx:.3f} / {zy:.3f} mm depuis la coupe"
            + (f" — le retrait réglé exact ({p.geom.safe_mm:g} mm)"
               if max(abs(zdx), abs(zdy)) < 0.5 else
               f", soit {zdx:+.1f} / {zdy:+.1f} µm du retrait réglé "
               f"({p.geom.safe_mm:g} mm) : la zone sûre est UNE conversion de "
               f"la longueur ({p.geom.trim_mm[0] - 2 * p.geom.safe_mm:g} x "
               f"{p.geom.trim_mm[1] - 2 * p.geom.safe_mm:g} mm), pas deux "
               f"soustractions de pixels arrondis")),
    })
    # ── LE MIROIR RECTO-VERSO, MESURÉ — CRITÈRE 9 ─────────────────────────
    #    « Le miroir du recto-verso reste NON PROUVÉ par ce livrable [...]
    #    c'est une exigence non démontrée, ni chez A ni chez B. » Elle l'est
    #    ici, en microns, sur la géométrie qui sera écrite — et l'écart n'est
    #    nul que parce qu'il a fallu corriger l'origine du verso.
    if p.duplex:
        um = mirror_um(p)
        rows.append({
            "kind": "miroir_recto_verso",
            "level": "ok" if um <= 1.0 else "err",
            "card": "fichier", "card_i": -1, "slot": "",
            "value": um, "limit": 1,
            "message": (
                f"miroir recto-verso ({'bord long' if p.flip == 'long' else 'bord court'}) : "
                f"écart mesuré {um:.1f} µm entre chaque verso et la position "
                f"miroir de son recto"
                + ("" if um <= 1.0 else
                   " — le verso ne tombe pas derrière son recto")),
        })
    if p.layers:
        rows.append({
            "kind": "calques_optionnels", "level": "ok", "card": "fichier",
            "card_i": -1, "slot": "", "value": len(OCG_LAYERS), "limit": 0,
            "message": ("calques optionnels : « "
                        + " » et « ".join(t for _, t in OCG_LAYERS)
                        + " » — l'imprimeur les décoche sans éditer le flux "
                          "(/OCProperties, en-tête %PDF-1.5)"),
        })
    rows.append({
        "kind": "police_incorporee", "level": "ok", "card": "fichier",
        "card_i": -1, "slot": "", "value": 0, "limit": 0,
        "message": ("cartouche tracé en vecteur : 0 objet /Font dans le PDF, "
                    "donc aucune police à incorporer"),
    })
    rows.append({
        "kind": "compression", "level": "ok" if p.lossless else "warn",
        "card": "fichier", "card_i": -1, "slot": "", "value": 0, "limit": 0,
        "message": ("images sans perte (FlateDecode)" if p.lossless else
                    f"images en JPEG q{p.jpeg_quality} 4:4:4 (avec perte) — "
                    "un master d'impression se livre sans perte"),
    })
    return rows


def preflight(body: dict, icc: bytes | None = None) -> dict:
    """Corps : {fmt, dpi, bleed_mm, safe_mm, slots:[{id,label,box:[x,y,w,h]}],
    cards:[{i,name,art:{w,h}|null,fields:{},orphans:{}}], min_dpi?, placed?}.

    `box` est en MILLIMÈTRES depuis le coin de ROGNE (contrat P3 -> P7).
    `orphans` est le contrat P4 -> P7 : les colonnes ACTIVES du fichier
    importé qui n'alimentent aucun bloc, avec leur valeur POUR CETTE CARTE.
    Une colonne désactivée dans l'écran Données n'y figure pas — refuser un
    tirage pour une colonne qu'on a explicitement éteinte serait du bruit.

    Rend des lignes {kind, level, card, message, value, limit} — chacune
    porte un CHIFFRE, jamais un simple « attention »."""
    body = body if isinstance(body, dict) else {}
    g = geom_of(str(body.get("fmt") or "").strip().lower(),
                int(body.get("dpi") or 300), body.get("bleed_mm"),
                body.get("safe_mm"), float(body.get("corner_mm", 3.0) or 0.0))
    try:
        min_dpi = float(body.get("min_dpi") or MIN_DPI_TARGET)
    except (TypeError, ValueError, OverflowError):
        min_dpi = MIN_DPI_TARGET
    slots = body.get("slots")
    slots = slots if isinstance(slots, list) else []
    cards = body.get("cards")
    cards = cards if isinstance(cards, list) else []

    rows: list[dict] = []
    # zone sûre, en pixels depuis le coin de ROGNE
    sx = g.safe_off_px[0] - g.bleed_off_px[0]
    sy = g.safe_off_px[1] - g.bleed_off_px[1]
    sw, sh = g.safe_px
    TOL = 0.5                                  # un demi-pixel : le sous-pixel
                                               # assumé de la règle, pas une
                                               # marge de complaisance.

    for s in slots:
        if not isinstance(s, dict):
            continue
        box = s.get("box")
        if not (isinstance(box, (list, tuple)) and len(box) >= 4):
            continue
        try:
            bx, by, bw, bh = (mmpx(float(box[0]), g.dpi), mmpx(float(box[1]), g.dpi),
                              mmpx(float(box[2]), g.dpi), mmpx(float(box[3]), g.dpi))
        except (TypeError, ValueError, OverflowError):
            continue
        over = max(sx - bx, sy - by, (bx + bw) - (sx + sw), (by + bh) - (sy + sh))
        if over <= TOL:
            continue
        sid = str(s.get("id") or "?")
        label = str(s.get("label") or sid)
        mm = over / g.dpi * MM_PER_INCH
        touched = [c for c in cards
                   if isinstance(c, dict)
                   and str((c.get("fields") or {}).get(sid, "")).strip()]
        targets = touched or [None]
        for c in targets:
            rows.append({
                "kind": "texte_hors_zone_sure", "level": "err",
                "card": (str(c.get("name") or f"carte {int(c.get('i', 0)) + 1}")
                         if isinstance(c, dict) else "toutes les cartes"),
                "card_i": int(c.get("i", 0)) if isinstance(c, dict) else -1,
                "slot": sid,
                "value": round(over, 1), "limit": 0,
                "message": (f"« {label} » dépasse la zone sûre de "
                            f"{over:.1f} px ({mm:.2f} mm)"),
            })

    # ══════════════════════════════════════════════════════════════════════
    # CE QUE LE FICHIER IMPORTÉ PORTE ET QU'AUCUN BLOC N'IMPRIME
    #
    # LE MANQUE QUE LES DEUX CONTRÔLES ONT NOMMÉ, MOT POUR MOT : « le contrôle
    # avant tirage n'audite que la FEUILLE, jamais le CONTENU des cartes — et
    # c'est par ce trou que passe sa faute la plus grave : les 12 cartes
    # portent le bandeau RARE alors que le CSV déclare commune x5 [...] Rien
    # ne le signale. » Et la forme exigée : « une liste NOMMÉE des cartes
    # fautives avec la valeur mesurée ».
    #
    # Une colonne importée qui n'alimente aucun bloc est de la donnée payée,
    # relue, filtrée, dupliquée — et jetée à l'impression. Le tirage part, et
    # personne ne sait que la rareté manque. La règle nomme la carte, la
    # colonne et LA VALEUR, et elle BLOQUE (niveau erreur) : la porte de la
    # route s'appuie dessus.
    # ══════════════════════════════════════════════════════════════════════
    def _nom(c: dict) -> str:
        return str(c.get("name") or f"carte {int(c.get('i', 0) or 0) + 1}")

    slot_ids = {str(s.get("id")) for s in slots
                if isinstance(s, dict) and s.get("id")}
    # Trois identités de service que P4 réserve (`RESERVED` de data.py) plus
    # la colonne de quantité : elles ne s'impriment pas, et c'est voulu.
    HORS_IMPRESSION = {"art", "back", "id", "qty"}
    CAP = 12                       # assez pour une liste nommée, pas un mur
    par_colonne: dict[str, list[tuple[str, str]]] = {}
    for c in cards:
        if not isinstance(c, dict):
            continue
        orph = c.get("orphans")
        if not isinstance(orph, dict):
            continue
        for col, val in orph.items():
            v = str("" if val is None else val).strip()
            if not v or str(col) in HORS_IMPRESSION:
                continue
            par_colonne.setdefault(str(col), []).append((_nom(c), v))
    for col, hits in sorted(par_colonne.items()):
        for nom, v in hits[:CAP]:
            rows.append({
                "kind": "colonne_non_imprimee", "level": "err", "card": nom,
                "card_i": -1, "slot": col, "value": len(hits), "limit": 0,
                "message": (f"la colonne « {col} » vaut « {v} » et n'alimente "
                            f"aucun bloc de la carte : cette valeur ne sera "
                            f"pas imprimée"),
            })
        if len(hits) > CAP:
            rows.append({
                "kind": "colonne_non_imprimee", "level": "err",
                "card": f"+ {len(hits) - CAP} autre(s)", "card_i": -1,
                "slot": col, "value": len(hits), "limit": 0,
                "message": (f"la colonne « {col} » n'est imprimée sur aucune "
                            f"des {len(hits)} carte(s) qui en portent une "
                            f"valeur"),
            })
    # Le même trou, un cran plus loin : une valeur portée par la carte sous un
    # identifiant qui n'est plus celui d'aucun bloc (bloc supprimé après le
    # mappage). La donnée voyage, rien ne la pose.
    if slot_ids:
        vus = 0
        for c in cards:
            if not isinstance(c, dict) or vus >= CAP:
                continue
            for k, v in (c.get("fields") or {}).items():
                k = str(k)
                if k in slot_ids or k in HORS_IMPRESSION or vus >= CAP:
                    continue
                sv = str("" if v is None else v).strip()
                if not sv:
                    continue
                vus += 1
                rows.append({
                    "kind": "champ_sans_bloc", "level": "err", "card": _nom(c),
                    "card_i": int(c.get("i", 0) or 0), "slot": k,
                    "value": 0, "limit": 0,
                    "message": (f"le champ « {k} » vaut « {sv} » mais aucun "
                                f"bloc de la maquette ne porte cet "
                                f"identifiant : la valeur reste dans le jeu "
                                f"et sort du tirage"),
                })
    # ── CE QU'ON NE MESURE PAS, ON NE LE DIT PAS ──────────────────────────
    #    Un troisième reproche visait les CONTENEURS DESSINÉS VIDES (« une
    #    sphère de coût vide et deux cadres vides qui s'impriment comme des
    #    trous de gabarit »). Une règle a été écrite ici, puis RETIRÉE : P7
    #    voit qu'un bloc n'a pas de donnée, mais il ne sait PAS si la maquette
    #    dessine quelque chose à cet endroit quand la donnée manque — c'est
    #    P3 qui peint, et P4 porte déjà le compte des blocs alimentés. Lever
    #    un avertissement sur chaque slot vide aurait affirmé une conséquence
    #    visuelle non mesurée, et noyé les deux règles qui, elles, se
    #    prouvent. Un chiffre faux vaut moins que pas de chiffre.

    for c in cards:
        if not isinstance(c, dict):
            continue
        name = _nom(c)
        art = c.get("art")
        # ── LA MESURE DE LA PIÈCE 01 D'ABORD ────────────────────────────
        # `doc.face.eff_dpi` est le DPI effectif de l'illustration TELLE
        # QU'ELLE EST POSÉE — recadrage, échelle et rotation compris. Nous ne
        # connaissons ici que la taille du fichier ; si P1 a mesuré, c'est
        # elle qui a raison. -1 = illustration vectorielle : jamais
        # sous-définie, quelle que soit la taille de la carte.
        declare = c.get("eff_dpi")
        try:
            declare = float(declare) if declare is not None else 0.0
        except (TypeError, ValueError, OverflowError):
            declare = 0.0
        if declare < 0:
            continue
        if declare > 0:
            if declare < min_dpi - 0.5:
                rows.append({
                    "kind": "image_sous_definie", "level": "err", "card": name,
                    "card_i": int(c.get("i", 0) or 0), "slot": "art",
                    "value": round(declare, 1), "limit": int(min_dpi),
                    "message": (f"illustration à {declare:.0f} DPI effectifs "
                                f"une fois posée (mesure de la pièce 01), il en "
                                f"faut {int(min_dpi)}"),
                })
            continue
        if not isinstance(art, dict):
            if c.get("has_art"):
                continue          # posée mais non mesurable : on se tait
            rows.append({
                "kind": "illustration_absente", "level": "warn", "card": name,
                "card_i": int(c.get("i", 0) or 0), "slot": "",
                "value": 0, "limit": int(min_dpi),
                "message": "aucune illustration posée (fond nu à l'impression)",
            })
            continue
        try:
            aw, ah = float(art.get("w") or 0), float(art.get("h") or 0)
        except (TypeError, ValueError, OverflowError):
            aw = ah = 0.0
        placed = c.get("placed") or body.get("placed") or g.canvas_px
        try:
            pw, ph = float(placed[0]), float(placed[1])
        except (TypeError, ValueError, IndexError, OverflowError):
            pw, ph = float(g.canvas_px[0]), float(g.canvas_px[1])
        if aw <= 0 or ah <= 0 or pw <= 0 or ph <= 0:
            continue
        eff = min(aw * g.dpi / pw, ah * g.dpi / ph)
        if eff < min_dpi - 0.5:
            rows.append({
                "kind": "image_sous_definie", "level": "err", "card": name,
                "card_i": int(c.get("i", 0) or 0), "slot": "art",
                "value": round(eff, 1), "limit": int(min_dpi),
                "message": (f"illustration {int(aw)}x{int(ah)} px posée sur "
                            f"{int(pw)}x{int(ph)} px : {eff:.0f} DPI effectifs, "
                            f"il en faut {int(min_dpi)}"),
            })

    if body.get("file_checks", True):
        b2 = dict(body)
        b2["n_cards"] = max(1, len(cards))
        rows = file_checks(b2, icc) + rows

    errs = sum(1 for r in rows if r["level"] == "err")
    oks = sum(1 for r in rows if r["level"] == "ok")
    return {"rows": rows, "errors": errs,
            "warnings": len(rows) - errs - oks, "passed": oks,
            "ok": errs == 0, "min_dpi": min_dpi,
            "safe_px": list(g.safe_px), "canvas_px": list(g.canvas_px),
            "checked": {"slots": len(slots), "cards": len(cards),
                        "rules": len(rows)}}


# ══════════════════════════════════════════════════════════════════════════
# Routes — chemins RELATIFS à /api/cards/{did}/print (règle 8)
# ══════════════════════════════════════════════════════════════════════════

def _deck(did: str) -> dict:
    """Deck existant, ou l'erreur qui va bien. Import PARESSEUX du magasin :
    le style de `routes.py`, et aucun cycle à l'import."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    from . import core as deck_store
    doc = deck_store.read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return doc


ICC_FILE = "print_output.icc"


def _icc_path(did: str):
    from .contract import deck_dir
    return deck_dir(did) / ICC_FILE


def icc_of(did: str) -> bytes | None:
    """Le profil de sortie DÉPOSÉ SUR LE DECK. Téléversé une fois, relu par
    /layout, /sheet et /pdf : le plan affiché est donc calculé avec le
    profil qui sera réellement embarqué, pas avec un défaut d'usine."""
    try:
        p = _icc_path(did)
        return p.read_bytes() if p.exists() else None
    except Exception:
        return None


def _spec_of(doc: dict, body: dict) -> dict:
    """Le corps du client, complété par ce que le deck sait déjà : format,
    définition, fond perdu, zone sûre. Un client qui n'envoie rien obtient
    donc le plan du deck ouvert, pas un défaut d'usine.

    CHANGER DE FORMAT REPREND SON FOND PERDU NATIF — 0.125 in en impérial,
    3 mm en métrique — exactement comme `core.get_deck_geom` et comme
    `setFormatInternal` côté écran. Sans cette reprise, demander un plan
    `poker_us` depuis un deck `poker_eu` gardait 3 mm et sortait une toile de
    821x1121 au lieu de 825x1125 : la parité nanDECK tombait sur un simple
    aperçu. Mesuré sur le :8765 le 11/08. Un `bleed_mm`/`safe_mm` passé
    EXPLICITEMENT reste prioritaire — il est appliqué juste après.
    """
    out = dict(doc.get("print") or {})
    fmt = doc.get("format") or {}
    for k in ("fmt", "dpi", "bleed_mm", "safe_mm", "corner_mm"):
        if k in fmt:
            out[k] = fmt[k]
    body = body if isinstance(body, dict) else {}
    demande = str(body.get("fmt") or "").strip().lower()
    if demande and demande != out.get("fmt"):
        try:
            out["bleed_mm"] = out["safe_mm"] = native_bleed_mm(demande)
        except KeyError:
            pass                  # format inconnu : build_plan lèvera, avec sa phrase
    out.update({k: v for k, v in body.items() if v is not None})
    return out


@router.get("/sheets")
async def get_sheets(did: str):
    """Le catalogue des planches, en pixels pour les trois définitions —
    CALCULÉ par `contract.sheet_px`, jamais recopié. L'écran affiche ces
    chiffres tels quels ; il n'en recalcule aucun."""
    _deck(did)
    return {
        "sheets": [
            {"id": sid, "label": SHEETS[sid]["label"],
             "size_mm": [round(v, 3) for v in SHEETS[sid]["size_mm"]],
             "px": {str(d): list(sheet_px(sid, d)) for d in DPI_CHOICES}}
            for sid in SHEETS
        ] + [{"id": SHEET_CARD, "label": "1 carte / page (boîtes exactes)",
              "size_mm": None, "px": None}],
        "dpis": list(DPI_CHOICES),
        "marks": list(MARKS),
        "flips": list(FLIPS),
        "limits": {"margin_mm": [0.0, MARGIN_MM_MAX],
                   "gutter_mm": [0.0, GUTTER_MM_MAX],
                   "mark_len_mm": [0.0, MARK_LEN_MM_MAX],
                   "mark_off_mm": [0.0, MARK_OFF_MM_MAX],
                   "mark_w_mm": [MARK_W_MM_MIN, MARK_W_MM_MAX],
                   "pages": PAGES_MAX},
        "defaults": dict(DEFAULTS),
        "min_dpi": MIN_DPI_TARGET,
        "mark_spaces": list(MARK_SPACES),
        "colors": list(COLOR_MODES),
        "intents": [{"id": k, "label": v["label"], "space": v["space"],
                     "cond": v.get("cond", ""), "icc": v.get("id"),
                     # « cette condition peut-elle porter une revendication
                     #   PDF/X ? » — la réponse voyage avec le catalogue, pour
                     #   que l'écran n'ait rien à deviner.
                     "press": bool(v.get("press", v.get("space") is not None)),
                     "pdfx": bool(v.get("space") == "CMYK")}
                    for k, v in INTENTS.items()],
        "srgb_icc_bytes": len(srgb_icc()),
        "pdfx_version": PDFX_VERSION,
        "pdfx_subtype": PDFX_SUBTYPE,
        "src_subtype": SRC_SUBTYPE,
        "phys": {str(d): {"ppm": phys_ppm(d), "dpi": round(phys_dpi(d), 4)}
                 for d in DPI_CHOICES},
    }


def plan_dict(p: Plan) -> dict:
    """Le plan, servi tel quel à l'écran. Les pixels sortent sans arrondi
    d'affichage : ce sont eux qui font le fichier."""
    return {
        "sheet": p.sheet, "orient": p.orient, "dpi": p.dpi,
        "sheet_px": list(p.sheet_px), "cols": p.cols, "rows": p.rows,
        "per_page": p.per_page, "cell_px": list(p.cell_px),
        "gutter_px": round(p.gutter_px, 4), "margin_px": round(p.margin_px, 4),
        "gutter_pt": round(px2pt(p.gutter_px, p.dpi), 4),
        "margin_pt": round(px2pt(p.margin_px, p.dpi), 4),
        "origin_px": [round(v, 4) for v in p.origin_px],
        "content_px": [round(v, 4) for v in p.content_px],
        "page_pt": [round(v, 4) for v in page_pt(p)],
        "page_iso": p.page_iso,
        # L'ÉCART AU FORMAT ISO, EN MICRONS, DANS LES DEUX SENS : subir 27 µm
        # ou les corriger doit être un choix, pas une surprise de RIP.
        # `iso_um` est le pire des deux axes (un seuil) ; `iso_um_xy` les
        # porte SIGNÉS, parce que la largeur est en dessous du nominal quand
        # la hauteur est au-dessus — et « sous le format nominal » était donc
        # faux d'un axe sur deux.
        "iso_um": round(iso_gap_um(p), 1),
        "iso_um_xy": list(iso_gap_xy_um(p)),
        # LA ROGNE ÉCRITE, ET SON ÉCART AU NOMINAL. La table des formats
        # affiche 63,00 x 88,00 mm ; ce qui part dans la /TrimBox vaut
        # 62,992 x 87,969. L'écart est petit, il n'est plus tu.
        "trim_mm_written": [round(v, 4) for v in trim_written_mm(p)],
        "trim_um_xy": list(trim_gap_xy_um(p)),
        # LA ZONE SÛRE ÉCRITE, ET LE RETRAIT QUE LA /ArtBox PORTE VRAIMENT.
        # « zone sûre 3 mm » affiché à côté d'un retrait de 2,963 mm : l'écart
        # est mesuré, signé, et affiché là où le réglage l'était.
        "safe_mm_written": [round(v, 4) for v in safe_written_mm(p)],
        "safe_inset_mm": [round(v, 4) for v in safe_inset_written_mm(p)],
        "safe_um_xy": list(safe_gap_xy_um(p)),
        "layers": p.layers,
        "ocg": [t for _, t in OCG_LAYERS] if p.layers else [],
        "n_cards": p.n_cards, "pages": p.pages, "out_pages": p.out_pages,
        "duplex": p.duplex, "flip": p.flip, "duplex_order": p.duplex_order,
        "marks": p.marks, "trimbox": p.trimbox, "artbox": p.artbox,
        "keep_bleed_px": [round(v, 4) for v in keep_bleed(p, 0, 0)],
        "inner_bleed_px": round(min(p.geom.bleed_off_px[0], p.gutter_px / 2.0), 4)
        if p.cols > 1 else round(p.geom.bleed_off_px[0], 4),
        "bleed_mm_real": list(bleed_mm_sides(p)),
        "bleed_mm_raster": list(bleed_mm_sides(p, raster=True)),
        "marks_n": len(mark_segments(p)),
        # LA DÉRIVE TOLÉRÉE, RELUE SUR LES SEGMENTS RENDUS — jamais le
        # réglage. `mark_touch` est le compte des traits qui touchent une
        # carte : sa seule valeur acceptable est 0, et l'écran l'affiche.
        "mark_safe": p.mark_safe,
        "mark_keepout_mm": round(mark_keepout_px(p) / p.dpi * MM_PER_INCH, 4),
        "mark_clearance_mm": mark_clearance_mm(p),
        "mark_touch": mark_touch(p),
        # LE MIROIR, MESURÉ SUR LA GÉOMÉTRIE ÉCRITE (critère 9).
        "mirror_um": mirror_um(p),
        # LA GRILLE DE COUPE, EN MILLIMÈTRES, TELLE QU'ELLE SORTIRA. Ce qui
        # est écrit ne peut pas dériver en douce : l'écran affiche la
        # position réelle, pas la position théorique.
        "cut_mm_x": sorted({round(s[0] / p.dpi * MM_PER_INCH, 4)
                            for s in mark_segments(p) if abs(s[0] - s[2]) < 1e-6}),
        "cut_mm_y": sorted({round(s[1] / p.dpi * MM_PER_INCH, 4)
                            for s in mark_segments(p) if abs(s[1] - s[3]) < 1e-6}),
        "mark_space": p.mark_space, "color": p.color, "intent": p.intent,
        "lossless": p.lossless,
        "out_intent": ({"id": p.out_intent["id"], "space": p.out_intent["space"],
                        "profile_bytes": len(p.out_intent.get("profile") or b""),
                        "cls": p.out_intent.get("cls", ""),
                        "press": bool(p.out_intent.get("press")),
                        # `pdfx` = l'intention le PERMET ; `claim` = ce qui
                        # sera vraiment écrit. Les calques (PDF 1.5) excluent
                        # PDF/X-3 (PDF 1.4) : le panneau ne peut donc pas
                        # annoncer une conformité que le fichier ne portera
                        # pas.
                        "pdfx": bool(p.out_intent.get("pdfx")),
                        "claim": bool(p.out_intent.get("pdfx")) and not p.layers,
                        "subtype": (PDFX_SUBTYPE
                                    if (p.out_intent.get("pdfx") and not p.layers)
                                    else SRC_SUBTYPE),
                        "version": (PDFX_VERSION
                                    if (p.out_intent.get("pdfx") and not p.layers)
                                    else ""),
                        "registry": p.out_intent.get("registry", ""),
                        "cond": p.out_intent["cond"]} if p.out_intent else None),
        # LA DENSITÉ QUE LE FICHIER PORTERA, pas celle du curseur : l'unité du
        # chunk pHYs est le mètre entier, donc 300 DPI n'est pas représentable.
        "phys_ppm": phys_ppm(p.dpi),
        "phys_dpi": round(phys_dpi(p.dpi), 4),
        "gutter_marks": gutter_marks(p),
        "slug_text": slug_text(p, "…", 0, "front"),
        "warnings": list(p.warnings),
        "geom": p.geom.to_dict(),
    }


@router.post("/layout")
async def post_layout(did: str, body: dict | None = None):
    """LE plan d'imposition, calculé ici et nulle part ailleurs.

    L'écran a le même calcul — il doit afficher sans attendre le réseau — et
    confronte SA réponse à celle-ci à chaque réglage. Un écart d'un pixel
    devient une alarme visible, pas une découverte chez l'imprimeur."""
    doc = _deck(did)
    body = body if isinstance(body, dict) else {}
    try:
        n = int(body.get("n_cards") or 1)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(400, "Le nombre de cartes doit être un entier")
    try:
        p = build_plan(_spec_of(doc, body), n, icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"plan": plan_dict(p)}


@router.get("/icc")
async def get_icc(did: str):
    """Le profil de sortie déposé sur ce jeu — ou `null`. Les chiffres rendus
    ici sont lus SUR LES OCTETS du fichier, jamais sur son nom."""
    _deck(did)
    data = icc_of(did)
    if not data:
        return {"icc": None}
    try:
        return {"icc": icc_info(data)}
    except ValueError as e:
        return {"icc": None, "error": str(e)}


@router.post("/icc")
async def post_icc(did: str, file: UploadFile = File(...)):
    """Dépose le profil ICC de l'imprimeur sur le jeu. Il est VALIDÉ à
    l'octet (signature « acsp », espace, nombre de canaux) : un .icc invalide
    embarqué dans un PDF, c'est un fichier que le RIP refuse."""
    _deck(did)
    data = await file.read()
    if len(data) > ICC_MAX_BYTES:
        raise HTTPException(400, f"Profil trop lourd : {len(data)} octets, "
                                 f"le maximum est {ICC_MAX_BYTES}")
    try:
        info = icc_info(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        path = _icc_path(did)
        tmp = path.with_suffix(".icc.tmp")
        await asyncio.to_thread(tmp.write_bytes, data)
        tmp.replace(path)
    except Exception as e:
        logger.exception("cards/print: profil ICC non enregistré")
        raise HTTPException(500, f"Profil non enregistré: {e}")
    info["name"] = str(getattr(file, "filename", "") or "")[:120]
    return {"icc": info}


@router.delete("/icc")
async def del_icc(did: str):
    _deck(did)
    p = _icc_path(did)
    if p.exists():
        p.unlink()
    return {"ok": True}


@router.post("/preflight")
async def post_preflight(did: str, body: dict | None = None):
    """Contrôle avant vol : texte hors zone sûre, illustration sous 300 DPI.
    Chaque ligne porte le nom de la carte ET le chiffre."""
    doc = _deck(did)
    body = body if isinstance(body, dict) else {}
    try:
        out = await asyncio.to_thread(preflight, _spec_of(doc, body),
                                      icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return out


# ══════════════════════════════════════════════════════════════════════════
# LA PORTE — un contrôle avant vol qui ne refuse rien ne contrôle rien
#
# Le contrôle détectait parfaitement (6 erreurs nommées et chiffrées) et
# laissait partir le fichier : « le pilote part chez l'imprimeur avec le
# texte hors zone sûre ». La détection sans barrière n'est pas un contrôle,
# c'est un commentaire.
#
# La porte est ICI, dans la route, et pas seulement dans l'écran : un client
# qui saute l'interface la rencontre quand même. Elle ne se force que par un
# `force: true` EXPLICITE — l'utilisateur garde le dernier mot, mais il doit
# le dire.
# ══════════════════════════════════════════════════════════════════════════

def preflight_safe(body: dict, icc: bytes | None) -> dict | None:
    """Le contrôle avant vol de cette demande, ou None quand il n'y a rien à
    contrôler par carte. Il ne lève JAMAIS : un contrôle en panne ne doit ni
    bloquer un export, ni faire croire qu'il a jugé.

    UN SEUL APPEL PAR EXPORT : le même résultat sert à refuser (la porte) et
    à écrire le verdict dans le fichier livré. Deux appels, c'était deux
    mesures qui pouvaient diverger — et deux fois le prix."""
    if not isinstance(body, dict) or not (body.get("slots") or body.get("cards")):
        return None
    try:
        return preflight(body, icc)
    except Exception:
        return None


def control_line(out: dict | None, forced: bool = False) -> str:
    """LE VERDICT QUI PART DANS LE FICHIER. Une ligne, des chiffres, et — si
    l'export a été forcé malgré des erreurs — l'aveu nommé carte par carte.

    « Rien dans les fichiers livrés ne prouve que les règles par carte savent
    nommer une carte et sortir un chiffre » : elles le prouvent ici. Et un
    utilisateur qui passe outre laisse une trace dans le PDF, pas seulement
    dans un journal d'écran que l'imprimeur ne verra jamais."""
    if not isinstance(out, dict) or not isinstance(out.get("checked"), dict):
        return ""
    c = out["checked"]
    base = (f"controle avant vol : {int(c.get('rules', 0))} regle(s) sur "
            f"{int(c.get('cards', 0))} carte(s) et {int(c.get('slots', 0))} "
            f"bloc(s) — {int(out.get('errors', 0))} erreur(s), "
            f"{int(out.get('warnings', 0))} avertissement(s), "
            f"{int(out.get('passed', 0))} controle(s) OK")
    if not forced or not out.get("errors"):
        return base
    noms = "; ".join(f"{r.get('card')} : {r.get('message')}"
                     for r in out.get("rows", [])
                     if r.get("level") == "err")
    return (f"{base} — EXPORT FORCE malgre {int(out['errors'])} erreur(s) : "
            + noms[:700])


def gate(body: dict, icc: bytes | None, out: dict | None = None) -> dict | None:
    """Rend le verdict qui BLOQUE, ou None. Sans `slots`/`cards` dans la
    demande, il n'y a rien à contrôler par carte : la porte reste ouverte et
    ne prétend pas le contraire."""
    if not isinstance(body, dict):
        return None
    if _flag(body, "force"):            # `force` n'entre PAS dans DEFAULTS :
        return None                     # ce n'est pas un réglage qu'on garde
    out = out if out is not None else preflight_safe(body, icc)
    if not out or not out.get("errors"):
        return None
    errs = [r for r in out["rows"] if r.get("level") == "err"]
    return {
        "errors": out["errors"],
        "message": (f"Contrôle avant vol : {out['errors']} erreur(s). "
                    "L'export est refusé tant qu'elles ne sont pas corrigées "
                    "— relancer avec « force » pour passer outre en le "
                    "sachant."),
        "rows": [{"card": r.get("card"), "slot": r.get("slot"),
                  "kind": r.get("kind"), "message": r.get("message")}
                 for r in errs[:20]],
        "shown": min(20, len(errs)),
    }


def _gate_or_409(body: dict, icc: bytes | None,
                 out: dict | None = None) -> None:
    v = gate(body, icc, out)
    if v is not None:
        raise HTTPException(409, detail=v)


def _json_form(spec: str) -> dict:
    import json
    try:
        d = json.loads(spec or "{}")
    except ValueError:
        raise HTTPException(400, "Le champ « spec » n'est pas du JSON valide")
    if not isinstance(d, dict):
        raise HTTPException(400, "Le champ « spec » doit être un objet JSON")
    return d


@router.post("/card")
async def post_card(did: str, spec: str = Form("{}"),
                    file: UploadFile = File(...)):
    """Ré-encode UNE carte rendue par le navigateur : PNG 8 ou 16 bits (avec
    alpha), ou JPEG. Le DPI est inscrit dans le fichier (`pHYs` / JFIF) —
    sans lui, le premier logiciel venu ré-échelonne la carte."""
    doc = _deck(did)
    body = _json_form(spec)
    data = await file.read()
    try:
        p = build_plan(_spec_of(doc, body), 1, icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _gate_or_409(_spec_of(doc, body), icc_of(did))
    fmt = str(body.get("card_fmt") or "png").strip().lower()
    if fmt not in CARD_FORMATS:
        raise HTTPException(400, "Format de carte inconnu: " + fmt)
    try:
        bits = int(body.get("card_bits") or 8)
    except (TypeError, ValueError, OverflowError):
        bits = 8
    if bits not in CARD_BITS:
        raise HTTPException(400, "Profondeur inconnue: 8 ou 16 bits")

    def work():
        im = open_card(data, p, 0)
        return encode_image(im, fmt, bits, p.dpi,
                            bool(body.get("card_alpha", True)),
                            p.jpeg_quality)
    try:
        out, mime, ext = await asyncio.to_thread(work)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("cards/print: encodage de carte impossible")
        raise HTTPException(500, f"Encodage impossible: {e}")
    # ── CE QUE LE FICHIER PORTE VRAIMENT, RELU SUR SES OCTETS ─────────────
    #    « déclaré/réel/valeurs distinctes/bits utiles ». Une case cochée
    #    « 16 bits » ne prouve rien : l'audit qui a fondé cette règle a
    #    trouvé un IHDR à 16 bits sur une carte 8 bits élargie. Ici
    #    l'élargissement est voulu — et il est MESURÉ, pas affirmé.
    prof = {}
    if fmt == "png":
        try:
            prof = await asyncio.to_thread(png_depth, out)
        except Exception:
            prof = {}
    return Response(content=out, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="carte.{ext}"',
        "X-CF-Pixels": f"{p.geom.canvas_px[0]}x{p.geom.canvas_px[1]}",
        "X-CF-Phys": str(phys_ppm(p.dpi)),
        "X-CF-Depth": (f"{prof['declared']}/{prof['real_bits']}/"
                       f"{prof['distinct']}/{prof['useful_bits']:.2f}"
                       if prof.get("exact") else
                       ("jpeg" if fmt == "jpeg" else "non mesure")),
        # Le profil se nomme lui-même : le nom vient de son tag `desc`.
        "X-CF-Icc": f"{icc_desc(srgb_icc()) or 'ICC'}/{len(srgb_icc())}",
    })


async def _load_all(files: list[UploadFile], p: Plan,
                    label: str) -> dict[int, Image.Image]:
    blobs = [await f.read() for f in (files or [])]

    def work():
        out = {}
        for i, b in enumerate(blobs):
            if not b:
                continue
            out[i] = open_card(b, p, i)
        return out
    try:
        return await asyncio.to_thread(work)
    except ValueError as e:
        raise HTTPException(400, f"{label}: {e}")


@router.post("/sheet")
async def post_sheet(did: str, spec: str = Form("{}"),
                     fronts: list[UploadFile] = File(default=[]),
                     backs: list[UploadFile] = File(default=[])):
    """UNE page de planche, en PNG. `page` et `side` choisissent laquelle."""
    doc = _deck(did)
    body = _json_form(spec)
    try:
        p = build_plan(_spec_of(doc, body),
                       max(1, len(fronts or []), len(backs or [])), icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _gate_or_409(_spec_of(doc, body), icc_of(did))
    side = "back" if str(body.get("side") or "front") == "back" else "front"
    try:
        page = max(0, int(body.get("page") or 0))
    except (TypeError, ValueError, OverflowError):
        page = 0
    if page >= p.pages:
        raise HTTPException(409, f"Page {page + 1} hors du plan ({p.pages} page(s))")
    imgs = await _load_all(backs if side == "back" else fronts, p,
                           "verso" if side == "back" else "recto")

    def work():
        sheet = compose_sheet(p, imgs, page, side, str(doc.get("name") or "Jeu"))
        buf = io.BytesIO()
        sheet.save(buf, "PNG", dpi=(p.dpi, p.dpi))
        return png_tag_icc(buf.getvalue(), srgb_icc())
    try:
        out = await asyncio.to_thread(work)
    except Exception as e:
        logger.exception("cards/print: planche impossible")
        raise HTTPException(500, f"Planche impossible: {e}")
    return Response(content=out, media_type="image/png", headers={
        "Content-Disposition": f'attachment; filename="planche_{page + 1}.png"',
        "X-CF-Pixels": f"{p.sheet_px[0]}x{p.sheet_px[1]}",
        "X-CF-Grid": f"{p.cols}x{p.rows}",
    })


@router.post("/pdf")
async def post_pdf(did: str, spec: str = Form("{}"),
                   fronts: list[UploadFile] = File(default=[]),
                   backs: list[UploadFile] = File(default=[])):
    """Le PDF multipage — traits de coupe VECTORIELS, `/TrimBox` et
    `/BleedBox` sur CHAQUE page. C'est le fichier qu'on envoie à
    l'imprimeur."""
    doc = _deck(did)
    body = _json_form(spec)
    n = len(fronts or [])
    if n < 1:
        raise HTTPException(400, "Aucune carte reçue : le navigateur doit "
                                 "rendre les cartes avant l'imposition")
    spec = _spec_of(doc, body)
    try:
        p = build_plan(spec, n, icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))
    # UN SEUL CONTRÔLE : il refuse (409 sans `force`) ET il part dans le
    # fichier. Deux appels séparés, c'étaient deux verdicts qui pouvaient ne
    # pas dire la même chose de la même demande.
    pf = await asyncio.to_thread(preflight_safe, spec, icc_of(did))
    _gate_or_409(spec, icc_of(did), pf)
    ctl = control_line(pf, _flag(spec, "force"))
    f_imgs = await _load_all(fronts, p, "recto")
    b_imgs = await _load_all(backs, p, "verso") if p.duplex else {}
    if p.duplex and not b_imgs:
        raise HTTPException(409, "Recto-verso demandé sans aucun verso reçu")

    def work():
        data = build_pdf(p, f_imgs, b_imgs, str(doc.get("name") or "Jeu"), ctl)
        # L'AUDIT EST FAIT SUR LE FICHIER QUI PART, pas sur le plan qui
        # l'a demandé : c'est lui, et lui seul, qui alimente le badge.
        return data, pdf_audit(data, p.duplex_order if p.duplex else "")
    try:
        out, audit = await asyncio.to_thread(work)
    except Exception as e:
        logger.exception("cards/print: PDF impossible")
        raise HTTPException(500, f"PDF impossible: {e}")
    edge, inner = bleed_mm_sides(p)
    return Response(content=out, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="planches.pdf"',
        "X-CF-Pages": str(p.out_pages),
        "X-CF-Grid": f"{p.cols}x{p.rows}",
        "X-CF-Gutter-Pt": f"{px2pt(p.gutter_px, p.dpi):.4f}",
        # Des en-têtes qui se VÉRIFIENT sur les octets rendus, pas des
        # promesses : intention de sortie, encre des repères, espace des
        # visuels, fond perdu réellement posé.
        "X-CF-Intent": (p.out_intent["id"] if p.out_intent else "none"),
        "X-CF-Mark-Space": p.mark_space,
        "X-CF-Color": p.color,
        "X-CF-Bleed-Mm": f"{edge}/{inner}",
        "X-CF-Lossless": "1" if p.lossless else "0",
        # ── L'AUDIT DES OCTETS ÉCRITS, RELU PAR L'ÉCRAN ──────────────────
        "X-CF-Header": audit["header"],
        "X-CF-Boxes": f"{audit['pages_4_boites']}/{audit['pages']}",
        "X-CF-Pdfx": audit["pdfx"] or "aucune",
        "X-CF-Subtype": audit["intent_subtype"] or "aucun",
        "X-CF-Fonts": str(audit["font_hits"]),
        "X-CF-Xmp": str(audit["xmp_blocks"]),
        "X-CF-Trapped": audit["trapped"] or "aucun",
        "X-CF-Gutter-Marks": str(gutter_marks(p)),
        # La dérive tolérée RELUE dans le fichier qui part, pas celle du plan
        # qui l'a demandé : « %.4f mm sur N trait(s), dont T qui touchent ».
        "X-CF-Mark-Clearance": ("%.4f/%d/%d" % (audit["mark_clearance_mm"],
                                                audit["marks_n"],
                                                audit["mark_touch"])),
        # ── LES TROIS MESURES AJOUTÉES CE TOUR-CI, TOUTES RELUES SUR LES
        #    OCTETS DU FICHIER QUI PART : le miroir recto-verso (critère 9),
        #    les calques optionnels, et l'écart au format nominal.
        "X-CF-Mirror-Um": ("%.1f" % audit["mirror_um"]
                           if audit["mirror_um"] >= 0 else "sans objet"),
        "X-CF-Layers": (", ".join(audit["ocg_names"]) or "aucun"),
        "X-CF-Page-Pt": ("%.4fx%.4f" % tuple(page_pt(p))),
        "X-CF-Iso-Um": ("%.1f" % audit["iso_um"] if audit["iso_um"] >= 0
                        else "hors table"),
        # Le verdict RELU dans le fichier écrit (XMP), pas celui qu'on vient
        # de calculer : si le stamp n'a pas atterri, l'en-tête ne ment pas.
        "X-CF-Control": (audit["control"][:400].encode("ascii", "replace")
                         .decode("ascii") or "non fourni"),
        "X-CF-Forced": "1" if audit["control_forced"] else "0",
    })


@router.post("/audit")
async def post_audit(did: str, body: dict | None = None):
    """CE QUE LE FICHIER PORTERAIT, MESURÉ SUR UN FICHIER RÉEL.

    L'écran n'a pas le droit d'afficher un badge que personne n'a vérifié :
    cette route construit un PDF d'une page avec le plan courant, le relit
    OCTET PAR OCTET, et rend la mesure. C'est ce que le panneau montre —
    pas la valeur du réglage."""
    doc = _deck(did)
    body = body if isinstance(body, dict) else {}
    try:
        p = build_plan(_spec_of(doc, body), 1, icc_of(did))
        # LE TÉMOIN PORTE CE QU'ON VEUT MESURER. Un témoin d'une seule page ne
        # peut rien dire du miroir recto-verso : quand le plan est en
        # recto-verso, on remplit une planche entière pour que l'audit relise
        # le miroir DANS LES OCTETS, et pas dans le réglage.
        if p.duplex and p.per_page > 1:
            p = build_plan(_spec_of(doc, body), p.per_page, icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))

    def work():
        im = Image.new("RGB", tuple(p.geom.canvas_px), (250, 250, 250))
        f = {i: im for i in range(max(1, p.n_cards))}
        out = pdf_audit(
            build_pdf(p, f, dict(f) if p.duplex else {},
                      str(doc.get("name") or "Jeu"),
                      "temoin d'audit : aucune carte reelle, aucun controle"),
            p.duplex_order if p.duplex else "")
        # ── LA PROFONDEUR, DÉMONTRÉE SUR UN TÉMOIN QUI PORTE 256 NIVEAUX ──
        #    L'écran a le droit de dire « conteneur 16 bits » seulement s'il
        #    peut le PROUVER : deux encodages de la MÊME rampe, mesurés dans
        #    leurs octets. Si le fichier 16 bits ne montre toujours que 256
        #    valeurs, toutes multiples de 257, la démonstration est faite.
        out["depth"] = {"8": depth_probe(p.geom, 8),
                        "16": depth_probe(p.geom, 16)}
        return out
    try:
        return {"audit": await asyncio.to_thread(work)}
    except Exception as e:
        logger.exception("cards/print: audit impossible")
        raise HTTPException(500, f"Audit impossible: {e}")
