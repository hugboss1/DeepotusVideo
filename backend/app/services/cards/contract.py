# -*- coding: utf-8 -*-
"""Card Forge — LE CONTRAT backend. Zéro code métier, zéro route.

Ce fichier appartient à CORE et n'est écrit qu'une fois : les dix pièces
(face, frame, type, data, solid, texture, print, gltf, forge3d, capture) le
LISENT et ne le modifient jamais. Il tient trois choses, et rien d'autre :

  1. LA RÈGLE DE GÉOMÉTRIE, unique. Aucun module ne recalcule un pixel à
     partir des millimètres. Jamais.
  2. Le chemin d'un deck sur le disque, avec son double garde-fou.
  3. Les signatures gelées partagées entre pièces — aujourd'hui `card_mesh`,
     écrite par P5 (solid) et lue par P8 (gltf) — plus un maillage de
     RÉFÉRENCE utilisable tout de suite, pour que P8 ne dépende pas du
     calendrier de P5.

── LA RÈGLE, gravée ─────────────────────────────────────────────────────────

    R(x)          = floor(x + 0.5)                    arrondi demi-haut
    px(mm, dpi)   = R(mm / 25.4 * dpi)
    canvas_px     = px(trim_mm + 2*bleed_mm, dpi)     <- la TOILE fait autorité
    trim_px       = px(trim_mm, dpi)
    bleed_off_px  = (canvas_px - trim_px) / 2         <- peut valoir x.5, assumé
    safe_px       = px(trim_mm - 2*safe_mm, dpi)      <- la ZONE SÛRE, de même
    safe_off_px   = bleed_off_px + (trim_px - safe_px) / 2

Pourquoi la TOILE fait autorité et non `trim + 2*round(bleed)` : cette
dérivation-là donne 814 px là où le métier attend 815, et rate les tailles
de nanDECK d'UN pixel sur tous les formats impériaux. Avec la règle
ci-dessus, `poker_us` sort à 825x1125 exactement comme nanDECK et le trait de
coupe tombe à 37,5 px — un demi-pixel assumé, rendu en sous-pixel. Ce
demi-pixel n'est pas une approximation à corriger : c'est le critère de
non-régression (`backend/tests/test_cards_core.py`, tolérance 0 pixel).

UNE SEULE CONVERSION PAR LONGUEUR — et la zone sûre n'y échappe pas. Elle
mesure `trim_mm - 2*safe_mm` : on convertit CETTE longueur, d'un bloc, comme
la toile. La dérivation `trim_px - 2*px(safe_mm)` était exactement l'erreur
que la règle prétend supprimer, et elle la commettait dans les deux sens :
1 px de TROP PEU sur les 7 formats impériaux (`micro` sortait 299x449 pour
une zone sûre de 1 x 1,5 pouce EXACT, donc 300x450) et jusqu'à 1,18 px de
TROP sur les 5 métriques — du texte hors zone sûre passait le contrôle avant
vol de P7. Elle produisait aussi trois collisions internes dans une seule
réponse de `/formats` : 57,15 mm valait 675 px (rogne `bridge_us`) ET 674 px
(zone sûre `poker_us`). Une longueur, un nombre de pixels : c'est tout.

`safe_off_px` est le CENTRAGE de la zone sûre dans la rogne, pas une seconde
somme de marges : demi-différence, comme `bleed_off_px`. Sur `poker_us`,
fond perdu et zone sûre valent tous deux 3,175 mm et donnent tous deux
37,5 px d'inset — deux longueurs égales, deux fois le même nombre de pixels.

Fond perdu natif : métrique -> 3 mm ; impérial -> 0.125 in (3,175 mm).
Zone de sécurité par défaut = fond perdu (convention Artscow / Printer's
Studio). Les deux restent réglables de 0 à 10 mm.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "MODULE_IDS", "DID_RE", "MM_PER_INCH", "DPI_CHOICES", "DPI_MIN", "DPI_MAX",
    "BLEED_MM_MAX", "SAFE_MM_MAX", "CORNER_MM_MAX",
    "BLEED_METRIC_MM", "BLEED_IMPERIAL_MM",
    "FORMATS", "SHEETS", "DEFAULT_FMT", "DEFAULT_DPI", "DEFAULT_CORNER_MM",
    "THICKNESS_MM_MIN", "THICKNESS_MM_MAX", "THICKNESS_MM_DEFAULT",
    "R", "px", "rnd", "RULE_TEXT", "CardGeom", "geom", "sheet_px",
    "format_row", "format_table", "native_bleed_mm", "UV_ISLANDS",
    "is_valid_did", "decks_root", "deck_dir", "card_mesh", "card_mesh_reference",
]

# ── identités gelées ────────────────────────────────────────────────────────
# LA LISTE SUIT LE RAIL, dans son ordre (= le numéro de pièce). Un id hors
# d'ici est refusé partout : registre JS, sous-routeur backend, sous-arbre du
# document. La règle vaut dans les DEUX SENS, et c'est le second qui a coûté :
# une pièce présente au rail mais absente d'ici est une pièce dont le document
# MENT. `doc.forge3d` en a fait la démonstration pendant deux phases — l'écran
# l'envoyait à chaque autosave (`core.js:saveBody` prend tout id du tableau JS
# `MODULES`), `normalize_deck` le jetait en silence faute de le trouver ici, et
# toute édition du graphe P9 était perdue au rechargement en ligne. La doctrine
# du partitionnement était juste ; c'était la liste qui avait du retard.
# Ajouter une pièce au rail SANS l'ajouter ici ne casse rien : ça efface.
MODULE_IDS = ("face", "frame", "type", "data", "solid", "texture",
              "print", "gltf", "forge3d", "capture")

DID_RE = re.compile(r"^deck_[0-9a-f]{8}$")

# ── constantes de géométrie ─────────────────────────────────────────────────
MM_PER_INCH = 25.4

DPI_CHOICES = (150, 300, 600)      # ce que l'écran propose
DPI_MIN, DPI_MAX = 72, 1200        # ce que le backend accepte

BLEED_MM_MAX = 10.0
SAFE_MM_MAX = 10.0
CORNER_MM_MAX = 10.0

BLEED_METRIC_MM = 3.0
BLEED_IMPERIAL_MM = 3.175          # 0.125 in

DEFAULT_FMT = "poker_eu"
DEFAULT_DPI = 300
DEFAULT_CORNER_MM = 3.0

# Épaisseur physique d'une carte à jouer réelle (P5 la règle, P8 la lit).
THICKNESS_MM_MIN = 0.20
THICKNESS_MM_MAX = 1.20
THICKNESS_MM_DEFAULT = 0.32

# ── la table des formats ────────────────────────────────────────────────────
# `trim_mm` est écrit en MILLIMÈTRES décimaux, y compris pour les formats
# impériaux (2.5 in = 63.5 mm exactement) : un seul système d'unités dans le
# code, `unit` ne servant qu'à l'affichage et au choix du fond perdu natif.
# Les sept formats impériaux reproduisent AU PIXEL les tailles avec fond perdu
# de nanDECK : 825x1125, 750x1125, 900x1500, 600x1125, 675x1125, 1125x1725,
# 450x600. Ce n'est pas une coïncidence, c'est le critère de non-régression.
FORMATS: dict[str, dict] = {
    "poker_us":  {"label": "Poker US 2,5 x 3,5 in",   "unit": "in",
                  "trim_mm": (63.5, 88.9)},
    "poker_eu":  {"label": "Poker 63 x 88 mm",        "unit": "mm",
                  "trim_mm": (63.0, 88.0)},
    "bridge_us": {"label": "Bridge US 2,25 x 3,5 in", "unit": "in",
                  "trim_mm": (57.15, 88.9)},
    "bridge_eu": {"label": "Bridge 59 x 91 mm",       "unit": "mm",
                  "trim_mm": (59.0, 91.0)},
    "tarot_us":  {"label": "Tarot US 2,75 x 4,75 in", "unit": "in",
                  "trim_mm": (69.85, 120.65)},
    "tarot_eu":  {"label": "Tarot 70 x 120 mm",       "unit": "mm",
                  "trim_mm": (70.0, 120.0)},
    "mini":      {"label": "Mini 44 x 68 mm",         "unit": "mm",
                  "trim_mm": (44.0, 68.0)},
    "square_eu": {"label": "Carré 70 x 70 mm",        "unit": "mm",
                  "trim_mm": (70.0, 70.0)},
    "domino":    {"label": "Domino 1,75 x 3,5 in",    "unit": "in",
                  "trim_mm": (44.45, 88.9)},
    "business":  {"label": "Carte de visite 2 x 3,5 in", "unit": "in",
                  "trim_mm": (50.8, 88.9)},
    "jumbo":     {"label": "Jumbo 3,5 x 5,5 in",      "unit": "in",
                  "trim_mm": (88.9, 139.7)},
    "micro":     {"label": "Micro 1,25 x 1,75 in",    "unit": "in",
                  "trim_mm": (31.75, 44.45)},
}

# Planches d'imposition (P7). Même règle d'arrondi, aucune exception.
SHEETS: dict[str, dict] = {
    "a4":     {"label": "A4 210 x 297 mm",        "size_mm": (210.0, 297.0)},
    "letter": {"label": "Letter 8,5 x 11 in",     "size_mm": (215.9, 279.4)},
    "a3":     {"label": "A3 297 x 420 mm",        "size_mm": (297.0, 420.0)},
}


# ── la règle ────────────────────────────────────────────────────────────────

def R(x: float) -> int:
    """Arrondi demi-haut : floor(x + 0.5).

    La quantification à 1e-9 AVANT l'arrondi n'est pas une seconde règle :
    elle absorbe le bruit de représentation binaire pour que la valeur
    arrondie soit celle de l'arithmétique exacte. Sans elle, un
    `3.175 / 25.4 * 300` qui retomberait à 37.49999999999999 au lieu de 37.5
    ferait basculer la zone sûre de 674 à 676 px sur TOUS les formats
    impériaux — une régression invisible à la lecture du code.
    """
    return int(math.floor(round(float(x), 9) + 0.5))


def px(mm: float, dpi: int) -> int:
    """Millimètres -> pixels. Le SEUL convertisseur du domaine."""
    return R(mm / MM_PER_INCH * dpi)


def rnd(v: float, n: int) -> float:
    """Arrondi d'AFFICHAGE, demi-haut — le clone exact de `Math.round(v*p)/p`
    de `core.js:rnd`, pas le `round()` de Python.

    Ce n'est pas un détail de présentation : `round()` est un arrondi AU PAIR
    (banquier). `round(0.0625, 3)` rend 0.062 quand l'écran affiche 0.063, et
    `round(1.25, 1)` rend 1.2 quand l'écran affiche 1.3. Deux règles
    différentes pour le même travail dans un fichier qui se déclare miroir
    exact : `verifyGeom` ne compare que les pixels, la dérive passerait
    inaperçue jusqu'à ce qu'un opérateur lise deux chiffres différents sur
    deux écrans. Toutes les longueurs servies ici sont positives, donc
    `floor(v*p + 0.5)/p` reproduit `Math.round` bit pour bit.
    """
    p = 10.0 ** n
    return math.floor(float(v) * p + 0.5) / p


# La règle, en une chaîne — servie telle quelle par GET /formats. Un client
# hors CF (script, autre lab, curl) doit pouvoir la relire sans lire ce
# fichier, et elle doit dire la VÉRITÉ : `floor(x+0.5)`, pas `round`, et la
# zone sûre AUSSI.
RULE_TEXT = (
    "R(x) = floor(x + 0.5) ; px(mm) = R(mm / 25.4 * dpi) ; "
    "canvas_px = px(trim_mm + 2*bleed_mm) ; trim_px = px(trim_mm) ; "
    "bleed_off_px = (canvas_px - trim_px)/2 ; "
    "safe_px = px(trim_mm - 2*safe_mm) ; "
    "safe_off_px = bleed_off_px + (trim_px - safe_px)/2 . "
    "UNE SEULE conversion par longueur ; les offsets peuvent valoir x.5 et "
    "sont rendus en sous-pixel."
)


@dataclass(frozen=True)
class CardGeom:
    """Géométrie d'une carte — vérité unique, gelée.

    SIGNATURE GELÉE : les champs de cette dataclasse ne bougent plus. Tout
    ajout de commodité passe par une propriété ou par `to_dict()`, jamais par
    un champ (un champ de plus casserait tous les appels positionnels).
    """
    fmt: str
    dpi: int
    trim_mm: tuple[float, float]
    bleed_mm: float
    safe_mm: float
    corner_mm: float
    trim_px: tuple[int, int]
    canvas_px: tuple[int, int]
    bleed_off_px: tuple[float, float]
    safe_px: tuple[int, int]
    safe_off_px: tuple[float, float]

    # ── commodités (propriétés : elles n'entrent pas dans la signature) ──
    @property
    def label(self) -> str:
        return FORMATS[self.fmt]["label"]

    @property
    def unit(self) -> str:
        return FORMATS[self.fmt]["unit"]

    @property
    def corner_px(self) -> float:
        """Rayon de coin en pixels. Fractionnaire et assumé, comme le trait de
        coupe : 3 mm à 300 DPI = 35,4 px, pas 35."""
        return rnd(self.corner_mm / MM_PER_INCH * self.dpi, 1)

    @property
    def trim_in(self) -> tuple[float, float]:
        return (rnd(self.trim_mm[0] / MM_PER_INCH, 4),
                rnd(self.trim_mm[1] / MM_PER_INCH, 4))

    def to_dict(self) -> dict:
        """Forme JSON servie par /formats et /{did}/geom.

        Les millimètres sont arrondis à 3 décimales pour l'affichage — par
        `rnd`, le demi-haut de `core.js`, JAMAIS par `round()` : voir `rnd`.
        Les PIXELS, eux, sortent tels quels — ce sont eux qui font le
        fichier."""
        return {
            "fmt": self.fmt,
            "label": self.label,
            "unit": self.unit,
            "dpi": self.dpi,
            "trim_mm": [rnd(v, 3) for v in self.trim_mm],
            "trim_in": list(self.trim_in),
            "bleed_mm": rnd(self.bleed_mm, 3),
            "safe_mm": rnd(self.safe_mm, 3),
            "corner_mm": rnd(self.corner_mm, 3),
            "trim_px": list(self.trim_px),
            "canvas_px": list(self.canvas_px),
            "bleed_off_px": list(self.bleed_off_px),
            "safe_px": list(self.safe_px),
            "safe_off_px": list(self.safe_off_px),
            "corner_px": self.corner_px,
        }


def native_bleed_mm(fmt: str) -> float:
    """Fond perdu du métier pour ce format : 3 mm en métrique, 0.125 in en
    impérial. C'est le défaut, pas une contrainte."""
    return (BLEED_IMPERIAL_MM if FORMATS[fmt]["unit"] == "in"
            else BLEED_METRIC_MM)


def _mm(value, default: float, hi: float, what: str) -> float:
    """Longueur en mm venant du client : jamais une exception non maîtrisée,
    jamais un 500. Hors bornes -> ValueError avec la borne citée."""
    if value is None:
        return float(default)
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{what} doit être un nombre de millimètres")
    if not math.isfinite(v):
        raise ValueError(f"{what} doit être un nombre de millimètres")
    if v < 0.0 or v > hi:
        raise ValueError(f"{what} doit tenir entre 0 et {hi:g} mm (reçu {v:g})")
    return v


def geom(fmt: str, dpi: int = DEFAULT_DPI, bleed_mm: float | None = None,
         safe_mm: float | None = None,
         corner_mm: float = DEFAULT_CORNER_MM) -> CardGeom:
    """SIGNATURE GELÉE — la géométrie d'un format. CORE seul l'appelle avec
    des valeurs déjà lues du document ; les modules la reçoivent.

    `bleed_mm=None` -> fond perdu natif du format.
    `safe_mm=None`  -> zone sûre = fond perdu (convention du métier).
    Lève `ValueError` (jamais autre chose) sur toute entrée hors liste
    blanche ou hors bornes ; l'appelant HTTP en fait un 400.
    """
    key = str(fmt or "").strip().lower()
    if key not in FORMATS:
        raise ValueError(
            "Format de carte inconnu: %r. Formats admis: %s"
            % (fmt, ", ".join(FORMATS)))
    try:
        d = int(dpi)
    except (TypeError, ValueError, OverflowError):
        # OverflowError : json.loads("1e999") rend float('inf'), et int(inf)
        # lève. Sans lui, un corps mal formé faisait un 500 (spec 2.5).
        raise ValueError(f"DPI doit être un entier (reçu {dpi!r})")
    if d < DPI_MIN or d > DPI_MAX:
        raise ValueError(
            f"DPI doit tenir entre {DPI_MIN} et {DPI_MAX} (reçu {d})")

    trim_mm = tuple(float(v) for v in FORMATS[key]["trim_mm"])
    bleed = _mm(bleed_mm, native_bleed_mm(key), BLEED_MM_MAX, "Le fond perdu")
    safe = _mm(safe_mm, bleed, SAFE_MM_MAX, "La zone de sécurité")
    corner = _mm(corner_mm, DEFAULT_CORNER_MM, CORNER_MM_MAX,
                 "Le rayon de coin")

    # ═══ CF-GEOM-FORMULA-BEGIN ═══ (miroir exact de core.js, même bloc)
    trim_px = (px(trim_mm[0], d), px(trim_mm[1], d))
    # LA TOILE FAIT AUTORITÉ : on convertit (rogne + 2*fond perdu) d'un bloc.
    canvas_px = (px(trim_mm[0] + 2 * bleed, d), px(trim_mm[1] + 2 * bleed, d))
    bleed_off_px = ((canvas_px[0] - trim_px[0]) / 2.0,
                    (canvas_px[1] - trim_px[1]) / 2.0)
    # LA ZONE SÛRE AUSSI : une longueur (rogne - 2*zone sûre), une conversion.
    safe_px = (px(trim_mm[0] - 2 * safe, d), px(trim_mm[1] - 2 * safe, d))
    safe_off_px = (bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2.0,
                   bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2.0)
    # ═══ CF-GEOM-FORMULA-END ═══

    return CardGeom(
        fmt=key, dpi=d, trim_mm=trim_mm, bleed_mm=bleed, safe_mm=safe,
        corner_mm=corner, trim_px=trim_px, canvas_px=canvas_px,
        bleed_off_px=bleed_off_px, safe_px=safe_px, safe_off_px=safe_off_px,
    )


def sheet_px(sheet: str, dpi: int = DEFAULT_DPI) -> tuple[int, int]:
    """Planche d'imposition en pixels. Même règle, sans exception :
    A4 à 300 DPI = 2480x3508, à 600 DPI = 4961x7016."""
    key = str(sheet or "").strip().lower()
    if key not in SHEETS:
        raise ValueError(
            "Planche inconnue: %r. Planches admises: %s"
            % (sheet, ", ".join(SHEETS)))
    try:
        d = int(dpi)
    except (TypeError, ValueError, OverflowError):
        # OverflowError : json.loads("1e999") rend float('inf'), et int(inf)
        # lève. Sans lui, un corps mal formé faisait un 500 (spec 2.5).
        raise ValueError(f"DPI doit être un entier (reçu {dpi!r})")
    if d < DPI_MIN or d > DPI_MAX:
        raise ValueError(
            f"DPI doit tenir entre {DPI_MIN} et {DPI_MAX} (reçu {d})")
    w, h = SHEETS[key]["size_mm"]
    return (px(w, d), px(h, d))


def format_row(fmt: str, dpi: int = DEFAULT_DPI) -> dict:
    """Une ligne du catalogue : le format à son fond perdu natif."""
    g = geom(fmt, dpi)
    row = g.to_dict()
    row["native_bleed_mm"] = round(native_bleed_mm(fmt), 3)
    return row


def format_table(dpi: int = DEFAULT_DPI) -> list[dict]:
    """Le catalogue complet, dans l'ordre de la table."""
    return [format_row(f, dpi) for f in FORMATS]


# ── chemins ─────────────────────────────────────────────────────────────────

def is_valid_did(did) -> bool:
    """`fullmatch` et NON `match`. Le motif est ancré des deux bouts, mais `$`
    accepte un saut de ligne FINAL : `re.match` laissait donc passer
    « deck_a1b2c3d4\\n », qui ressortait de `deck_dir` en chemin valide et
    aurait fait naître un dossier de jeu au nom invisible. Le dépôt écrit
    `fullmatch` partout ailleurs pour cette raison exacte — ici il ne le
    faisait pas, et c'est la porte d'entrée de cinquante-deux appelants."""
    return bool(isinstance(did, str) and DID_RE.fullmatch(did))


def decks_root() -> Path:
    """`outputs/decks/`. Voisin de materials/, sprites/, assets3d/ — aucune
    table SQL, comme ses voisins."""
    from app.config import settings
    p = settings.outputs_path / "decks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def deck_dir(did: str, create: bool = False) -> Path:
    """SIGNATURE GELÉE — dossier d'un deck. Refuse tout `did` hors
    ``^deck_[0-9a-f]{8}$``.

    DOUBLE GARDE-FOU, la doctrine de l'audit sécurité : le motif interdit
    déjà séparateurs, points et chemins absolus (donc `..`, `C:\\`, `a/b`) ;
    le confinement qui suit est la ceinture par-dessus les bretelles, au cas
    où le motif viendrait à être élargi un jour.
    """
    if not is_valid_did(did):
        raise ValueError(f"Identifiant de deck invalide: {did!r}")
    root = decks_root()
    p = (root / did).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ValueError(f"Identifiant de deck invalide: {did!r}")
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


# ── maillage de la carte ────────────────────────────────────────────────────
# P5 (solid) écrit le corps, P8 (gltf) l'importe EN LECTURE SEULE.
# La signature ci-dessous ne bouge plus.

def _tangents(pos: list, nrm: list, uv: list, idx: list) -> list:
    """Tangentes par sommet (Lengyel), même formule que
    `gltf_builder._tangents` — recopiée plutôt qu'importée pour que le
    contrat reste sans dépendance. `w` donne la main du repère
    (bitangente = cross(N, T) * w), indispensable dès que des îlots UV
    voisins n'ont pas la même orientation."""
    n = len(pos) // 3
    tan = [0.0] * (n * 3)
    bit = [0.0] * (n * 3)
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        p0, p1, p2 = i0 * 3, i1 * 3, i2 * 3
        q0, q1, q2 = i0 * 2, i1 * 2, i2 * 2
        e1 = (pos[p1] - pos[p0], pos[p1 + 1] - pos[p0 + 1], pos[p1 + 2] - pos[p0 + 2])
        e2 = (pos[p2] - pos[p0], pos[p2 + 1] - pos[p0 + 1], pos[p2 + 2] - pos[p0 + 2])
        du1, dv1 = uv[q1] - uv[q0], uv[q1 + 1] - uv[q0 + 1]
        du2, dv2 = uv[q2] - uv[q0], uv[q2 + 1] - uv[q0 + 1]
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-12:
            continue
        f = 1.0 / det
        tx = (dv2 * e1[0] - dv1 * e2[0]) * f
        ty = (dv2 * e1[1] - dv1 * e2[1]) * f
        tz = (dv2 * e1[2] - dv1 * e2[2]) * f
        bx = (du1 * e2[0] - du2 * e1[0]) * f
        by = (du1 * e2[1] - du2 * e1[1]) * f
        bz = (du1 * e2[2] - du2 * e1[2]) * f
        for i in (i0, i1, i2):
            k = i * 3
            tan[k] += tx; tan[k + 1] += ty; tan[k + 2] += tz
            bit[k] += bx; bit[k + 1] += by; bit[k + 2] += bz
    out = []
    for i in range(n):
        k = i * 3
        nx, ny, nz = nrm[k], nrm[k + 1], nrm[k + 2]
        tx, ty, tz = tan[k], tan[k + 1], tan[k + 2]
        d = nx * tx + ny * ty + nz * tz
        tx -= nx * d; ty -= ny * d; tz -= nz * d
        ln = math.sqrt(tx * tx + ty * ty + tz * tz)
        if ln < 1e-8:
            ax = (0.0, 0.0, 1.0) if abs(nx) > 0.9 else (1.0, 0.0, 0.0)
            tx = ny * ax[2] - nz * ax[1]
            ty = nz * ax[0] - nx * ax[2]
            tz = nx * ax[1] - ny * ax[0]
            ln = math.sqrt(tx * tx + ty * ty + tz * tz) or 1.0
        tx, ty, tz = tx / ln, ty / ln, tz / ln
        cx = ny * tz - nz * ty
        cy = nz * tx - nx * tz
        cz = nx * ty - ny * tx
        w = -1.0 if (cx * bit[k] + cy * bit[k + 1] + cz * bit[k + 2]) < 0.0 else 1.0
        out += [tx, ty, tz, w]
    return out


# Atlas de la carte : TROIS îlots disjoints, gouttières comprises.
# recto  u [0.000, 0.490]  v [0.000, 0.940]
# verso  u [0.510, 1.000]  v [0.000, 0.940]
# tranche u [0.000, 1.000] v [0.960, 1.000]   (4 sous-rectangles, un par côté)
UV_ISLANDS = {
    "front": (0.000, 0.000, 0.490, 0.940),
    "back":  (0.510, 0.000, 1.000, 0.940),
    "edge":  (0.000, 0.960, 1.000, 1.000),
}


def _quad(acc: dict, tl, tr, bl, br, normal, uv_rect) -> None:
    """Un quad vu DE L'EXTÉRIEUR : `tl/tr/bl/br` sont ses quatre coins dans
    l'ordre visuel (haut-gauche, haut-droit, bas-gauche, bas-droit) et
    `uv_rect` = (u0, v0, u1, v1) le rectangle d'atlas correspondant, v vers
    le bas comme dans l'image.

    L'enroulement `[a, c, b] + [b, c, d]` est celui de `_mesh_grid` : c'est
    lui qui garantit à la fois la normale géométrique vers l'extérieur ET
    l'INVARIANT du déterminant UV NÉGATIF sur tout triangle (aucun miroir,
    donc jamais de texte à l'envers — cf. test_uv_orientation).
    """
    u0, v0, u1, v1 = uv_rect
    base = len(acc["pos"]) // 3
    for p, (u, v) in ((tl, (u0, v0)), (tr, (u1, v0)),
                      (bl, (u0, v1)), (br, (u1, v1))):
        acc["pos"] += [p[0], p[1], p[2]]
        acc["nrm"] += [normal[0], normal[1], normal[2]]
        acc["uv"] += [u, v]
    a, b, c, d = base, base + 1, base + 2, base + 3
    acc["idx"] += [a, c, b, b, c, d]


def card_mesh_reference(geom: CardGeom, solid: dict) -> dict:
    """Le maillage de RÉFÉRENCE : boîte NON arrondie, 12 triangles.

    Il existe pour une raison de calendrier, écrite dans la spec : P8 (export
    3D) dépend de `card_mesh` que détient P5 (épaisseur). Sans bouchon, P8 ne
    peut pas démarrer. Celui-ci est complet et juste — proportions réelles,
    trois îlots UV disjoints, déterminant UV négatif partout — simplement
    sans coins arrondis, sans biseau et sans segments.

    Échelle : demi-hauteur = 1.0, comme les six maillages de `gltf_builder`,
    les autres dimensions suivant les proportions PHYSIQUES du format. Une
    carte 63x88x0,32 mm sort donc à 1,432 x 2,000 x 0,00727 unités.
    """
    solid = solid if isinstance(solid, dict) else {}
    try:
        th = float(solid.get("thickness_mm", THICKNESS_MM_DEFAULT))
    except (TypeError, ValueError):
        th = THICKNESS_MM_DEFAULT
    if not math.isfinite(th):
        th = THICKNESS_MM_DEFAULT
    th = max(THICKNESS_MM_MIN, min(THICKNESS_MM_MAX, th))

    w_mm, h_mm = geom.trim_mm
    s = 2.0 / h_mm                      # demi-hauteur = 1.0
    hw, hh, ht = w_mm * s / 2.0, 1.0, th * s / 2.0

    acc = {"pos": [], "nrm": [], "uv": [], "idx": []}
    fu0, fv0, fu1, fv1 = UV_ISLANDS["front"]
    bu0, bv0, bu1, bv1 = UV_ISLANDS["back"]
    eu0, ev0, eu1, ev1 = UV_ISLANDS["edge"]

    # recto (+Z) — vu depuis +Z, x vers la droite, y vers le haut
    _quad(acc, (-hw, hh, ht), (hw, hh, ht), (-hw, -hh, ht), (hw, -hh, ht),
          (0.0, 0.0, 1.0), (fu0, fv0, fu1, fv1))
    # verso (-Z) — vu depuis -Z, la droite de l'écran est -x
    _quad(acc, (hw, hh, -ht), (-hw, hh, -ht), (hw, -hh, -ht), (-hw, -hh, -ht),
          (0.0, 0.0, -1.0), (bu0, bv0, bu1, bv1))

    # tranche : 4 quads dans le MÊME îlot, un quart de bande chacun
    q = (eu1 - eu0) / 4.0
    # haut (+Y)
    _quad(acc, (-hw, hh, -ht), (hw, hh, -ht), (-hw, hh, ht), (hw, hh, ht),
          (0.0, 1.0, 0.0), (eu0 + 0 * q, ev0, eu0 + 1 * q, ev1))
    # droite (+X)
    _quad(acc, (hw, hh, ht), (hw, hh, -ht), (hw, -hh, ht), (hw, -hh, -ht),
          (1.0, 0.0, 0.0), (eu0 + 1 * q, ev0, eu0 + 2 * q, ev1))
    # bas (-Y)
    _quad(acc, (-hw, -hh, ht), (hw, -hh, ht), (-hw, -hh, -ht), (hw, -hh, -ht),
          (0.0, -1.0, 0.0), (eu0 + 2 * q, ev0, eu0 + 3 * q, ev1))
    # gauche (-X)
    _quad(acc, (-hw, hh, -ht), (-hw, hh, ht), (-hw, -hh, -ht), (-hw, -hh, ht),
          (-1.0, 0.0, 0.0), (eu0 + 3 * q, ev0, eu0 + 4 * q, ev1))

    pos, nrm, uv, idx = acc["pos"], acc["nrm"], acc["uv"], acc["idx"]
    return {"name": "card", "positions": pos, "normals": nrm, "uvs": uv,
            "indices": idx, "tangents": _tangents(pos, nrm, uv, idx)}


def card_mesh(geom: CardGeom, solid: dict) -> dict:
    """SIGNATURE GELÉE — le maillage de la carte.

    -> {name, positions, normals, uvs, indices, tangents} — même forme que
    `gltf_builder.build_mesh`. 3 îlots UV disjoints : recto, verso, tranche.
    INVARIANT : déterminant UV négatif sur TOUT triangle
    (cf. `backend/tests/test_uv_orientation.py`).

    Le corps appartient à P5 : dès que `cards/solid.py` expose son propre
    `card_mesh`, c'est lui qui répond ici. Tant qu'il n'existe pas, la
    référence ci-dessus tient le rôle, pour que P8 travaille sans attendre.
    P8 appelle TOUJOURS cette fonction, jamais `solid.card_mesh` directement :
    c'est l'unique point de bascule.
    """
    impl = None
    try:                                     # import paresseux : aucun cycle
        from . import solid as _solid
        impl = getattr(_solid, "card_mesh", None)
    except Exception:                        # pièce absente ou cassée
        impl = None
    if impl is None or impl is card_mesh or impl is card_mesh_reference \
            or not callable(impl):
        return card_mesh_reference(geom, solid)
    return impl(geom, solid)
