# -*- coding: utf-8 -*-
"""Card Forge — t421 (08/11/2026, tâche 7) : la planche en NID D'ABEILLES et
ses fichiers de coupe.

Une carte hexagonale s'imprime sur une feuille (PDF) puis se découpe à la
main ou par une machine (traceur de découpe, laser, CNC) d'après un fichier
SVG / DXF. La feuille imprimée et le fichier de coupe tombent AU MÊME
ENDROIT : les deux sortent du même `PlanHex`, dans le même repère (coin
haut-gauche de la feuille, millimètres, y vers le bas) et à la même échelle.
Une erreur ici ne se découvre qu'à la découpe, sur du vrai papier.

Ce module ne déclare AUCUN routeur : les trois routes vivent dans `print.py`
(`/hex/plan`, `/hex/coupe`, `/hex/pdf`). Il ne touche à rien du chemin
rectangulaire (`Plan`, `build_plan`, `compose_sheet`…) : un rectangle ne
change d'aucun pixel.

── LE PAS ───────────────────────────────────────────────────────────────────
Pointe en haut, W = largeur, H = hauteur de la coupe, g = gouttière (écart
PERPENDICULAIRE entre deux côtés voisins) :

    pas_x = W + g
    pas_y = 0,75 H + g √3 / 2
    rangée impaire : décalage x de pas_x / 2

Côté plat en haut : les axes s'échangent (colonnes décalées d'un demi-pas en
y). Deux voisines sont alors séparées de g sur chacun de leurs six côtés.

── LE FOND PERDU ────────────────────────────────────────────────────────────
Il n'existe pas de rognage hexagonal : le fond perdu de deux voisines ne doit
jamais se chevaucher, donc g >= 2 x fond perdu, sinon REFUS (ValueError, 400
à la route). Un rectangle, lui, ne fait qu'avertir (`gouttiere_courte`).

── LES REPÈRES ──────────────────────────────────────────────────────────────
Trois disques Ø 5 mm DANS la marge, au milieu de sa bande : haut-gauche,
haut-droit, et bas-gauche remonté de 10 mm (une distance au bord différente).
Trois coins d'un L ne sont déjà pas symétriques par demi-tour ni par
retournement ; le décalage du troisième interdit en plus de confondre les
coins entre eux. La marge doit donc loger un disque ET une garde de 3 mm
jusqu'aux cases (et jamais moins que le fond perdu) : une marge trop petite
est refusée avec le chiffre.

── LE RECTO VERSO ───────────────────────────────────────────────────────────
Portrait seulement, retournement sur le GRAND côté : la carte de la case k
au verso est posée en x' = largeur_feuille - x - W (même y). Les repères sont
imprimés au verso en miroir, pour contrôler le calage à contre-jour. La
coupe se fait recto dessus : les fichiers de coupe suivent la page recto. Une
carte sans verso laisse son emplacement BLANC.

── RASTER ET VECTEUR ────────────────────────────────────────────────────────
Le PDF porte une image par page (composée par Pillow, écrite SANS PERTE en
/FlateDecode par pypdf, à `dpi`) : trait de coupe et repères y sont
PIXÉLISÉS ; seul le fichier de coupe est vectoriel.
Une carte est collée au pixel ENTIER le plus proche de sa position exacte :
l'écart vaut au plus un demi-pixel (0,042 mm à 300 DPI), absorbé par le fond
perdu. Le trait de coupe et les repères, eux, sont tracés aux coordonnées
exactes (sous-pixel de la rastérisation près).
"""
from __future__ import annotations

import io
import math
import zipfile
from dataclasses import dataclass

from PIL import Image, ImageDraw

from .contract import CardGeom, MM_PER_INCH, SHEETS, R, sheet_px
from . import hexa

__all__ = ["PlanHex", "plan_hex", "carte_de", "contour_page_mm",
           "cartes_de_page", "coupe_svg", "coupe_dxf", "coupe_zip",
           "compose_page", "pdf_planche", "plan_hex_dict",
           "REPERE_DIAMETRE_MM", "REPERE_GARDE_MM"]

Point = tuple[float, float]

REPERE_DIAMETRE_MM = 5.0          # Ø des trois repères de calage
REPERE_GARDE_MM = 3.0             # jamais un repère à moins de 3 mm d'une case
REPERE_DECALAGE_MM = 10.0         # le repère bas-gauche, remonté de 10 mm
MARGE_MAX_MM = 60.0
GOUTTIERE_MAX_MM = 60.0
TRAIT_MM = 0.1                    # le trait de coupe à la main : fin
_EPS = 1e-9


@dataclass(frozen=True)
class PlanHex:
    """Le plan d'une planche hexagonale. `cases` = le coin haut-gauche de la
    COUPE (mm, repère feuille) de chaque case d'UNE page recto : toutes les
    pages ont les mêmes cases, la dernière n'en remplit que les premières."""
    sheet: str
    size_mm: tuple[float, float]
    geom: CardGeom
    marge_mm: float
    gouttiere_mm: float
    cases: list
    n_cartes: int
    pages: int
    reperes_mm: list
    trait: bool
    duplex: bool

    @property
    def par_page(self) -> int:
        return len(self.cases)

    @property
    def sheet_px(self) -> tuple[int, int]:
        return sheet_px(self.sheet, self.geom.dpi)


def _nombre(v, defaut: float, hi: float, quoi: str) -> float:
    if v is None:
        return float(defaut)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} doit être un nombre de millimètres")
    if not math.isfinite(x) or x < 0 or x > hi:
        raise ValueError(f"{quoi} doit tenir entre 0 et {hi:g} mm (reçu {v!r})")
    return x


def _grille(W: float, H: float, aw: float, ah: float, g: float) -> list[Point]:
    """Les cases d'un nid « pointe en haut » de cellules W x H dans une zone
    aw x ah, coin haut-gauche à (0, 0) : rangées horizontales, une sur deux
    décalée d'un demi-pas."""
    if aw + _EPS < W or ah + _EPS < H:
        return []
    pas_x = W + g
    pas_y = 0.75 * H + g * math.sqrt(3) / 2
    rangees = int(math.floor((ah - H) / pas_y + _EPS)) + 1
    out = []
    for r in range(rangees):
        dx = pas_x / 2 if r % 2 else 0.0
        if aw + _EPS < W + dx:
            continue
        n = int(math.floor((aw - W - dx) / pas_x + _EPS)) + 1
        out.extend((dx + c * pas_x, r * pas_y) for c in range(n))
    return out


def _reperes(sw: float, sh: float, marge: float) -> list[Point]:
    """Les trois centres, au milieu de la bande de marge : haut-gauche,
    haut-droit, bas-gauche remonté de REPERE_DECALAGE_MM."""
    e = marge / 2
    return [(e, e), (sw - e, e), (e, sh - e - REPERE_DECALAGE_MM)]


def plan_hex(g: CardGeom, sheet: str = "a4", marge_mm: float = 12.0,
             gouttiere_mm: float | None = None, n: int = 1,
             trait: bool = False, duplex: bool = False) -> PlanHex:
    """Le plan en nid d'abeilles. Lève `ValueError` (jamais autre chose) :
    rectangle, feuille inconnue ou « card », gouttière < 2 x fond perdu, marge
    trop petite pour les repères, aucune case qui entre."""
    if g.forme != "hex":
        raise ValueError("Le plan en nid d'abeilles ne sert que les cartes "
                         "hexagonales : ce format est rectangulaire.")
    cle = str(sheet or "").strip().lower()
    if cle == "card":
        raise ValueError("La planche en nid d'abeilles s'imprime sur une "
                         "feuille (A4, Letter, A3), pas carte par carte.")
    if cle not in SHEETS:
        raise ValueError("Planche inconnue : %r. Planches admises : %s"
                         % (sheet, ", ".join(SHEETS)))
    sw, sh = (float(v) for v in SHEETS[cle]["size_mm"])
    b = float(g.bleed_mm)
    marge = _nombre(marge_mm, 12.0, MARGE_MAX_MM, "La marge")
    gout = _nombre(gouttiere_mm, 2 * b, GOUTTIERE_MAX_MM, "La gouttière")
    try:
        n = int(n)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"Le nombre de cartes doit être un entier (reçu {n!r})")
    if n < 1:
        raise ValueError("Il faut au moins une carte pour faire une planche.")
    if gout + _EPS < 2 * b:
        raise ValueError(
            f"La gouttière ({gout:g} mm) doit valoir au moins deux fois le fond "
            f"perdu ({2 * b:g} mm) : en dessous, les fonds perdus de deux "
            "cartes voisines se chevauchent, et un hexagone ne se rogne pas.")
    r = REPERE_DIAMETRE_MM / 2
    jeu = max(REPERE_GARDE_MM, b)
    if marge / 2 - r + _EPS < jeu:
        mini = 2 * (r + jeu)
        raise ValueError(
            f"La marge ({marge:g} mm) doit faire au moins {mini:g} mm : elle "
            f"loge les repères de calage (Ø {REPERE_DIAMETRE_MM:g} mm) à "
            f"{jeu:g} mm au moins des cartes et de leur fond perdu.")
    W, H = g.trim_mm
    aw, ah = sw - 2 * marge, sh - 2 * marge
    if g.orientation == "plat":
        # les axes s'échangent : colonnes décalées d'un demi-pas en y
        cases = [(v, u) for u, v in _grille(H, W, ah, aw, gout)]
    else:
        cases = _grille(W, H, aw, ah, gout)
    if not cases:
        raise ValueError(
            f"Aucune carte {W:g} x {H:g} mm n'entre sur la feuille "
            f"{SHEETS[cle]['label']} avec une marge de {marge:g} mm.")
    # centrer l'ensemble sur la feuille (donc dans la zone des cases)
    x0 = min(x for x, _ in cases)
    y0 = min(y for _, y in cases)
    bw = max(x for x, _ in cases) + W - x0
    bh = max(y for _, y in cases) + H - y0
    ox, oy = (sw - bw) / 2 - x0, (sh - bh) / 2 - y0
    cases = sorted(((x + ox, y + oy) for x, y in cases),
                   key=lambda c: (round(c[1], 6), c[0]))
    pages = -(-n // len(cases))
    return PlanHex(sheet=cle, size_mm=(sw, sh), geom=g, marge_mm=marge,
                   gouttiere_mm=gout, cases=cases, n_cartes=n, pages=pages,
                   reperes_mm=_reperes(sw, sh, marge), trait=bool(trait),
                   duplex=bool(duplex))


def cartes_de_page(p: PlanHex, page: int) -> int:
    """Combien de cases la page `page` (0, 1…) remplit."""
    if page < 0 or page >= p.pages:
        raise ValueError(f"Page {page + 1} hors du plan ({p.pages} page(s))")
    return min(p.par_page, p.n_cartes - page * p.par_page)


def carte_de(p: PlanHex, page: int, k: int, cote: str = "recto") -> Point:
    """Le coin haut-gauche de la coupe de la carte k (0…) de la page `page`,
    côté `recto` ou `verso` (miroir du grand côté : x' = largeur - x - W)."""
    if k < 0 or k >= cartes_de_page(p, page):
        raise ValueError(f"La page {page + 1} n'a pas de carte {k + 1}")
    x, y = p.cases[k]
    if cote == "verso":
        return (p.size_mm[0] - x - p.geom.trim_mm[0], y)
    if cote != "recto":
        raise ValueError(f"Côté inconnu : {cote!r} (recto ou verso)")
    return (x, y)


def contour_page_mm(p: PlanHex, k: int) -> list[Point]:
    """Le contour de coupe de la case k, repère feuille, côté recto : ce que
    tracent le fichier de coupe et le trait de coupe à la main."""
    x, y = p.cases[k]
    return [(x + u, y + v) for u, v in p.geom.contour_mm]


def _repere_cote(p: PlanHex, cote: str) -> list[Point]:
    if cote == "verso":
        return [(p.size_mm[0] - x, y) for x, y in p.reperes_mm]
    return list(p.reperes_mm)


# ── le fichier de coupe ──────────────────────────────────────────────────────

def _f(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def coupe_svg(p: PlanHex, page: int) -> str:
    """La coupe de la page recto `page` : SVG en millimètres à l'échelle 1,
    un calque `coupe` (une polyligne fermée par carte) et un calque `reperes`
    (trois cercles Ø 5 mm)."""
    sw, sh = p.size_mm
    n = cartes_de_page(p, page)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<svg xmlns="http://www.w3.org/2000/svg" '
           'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
           f'version="1.1" width="{_f(sw)}mm" height="{_f(sh)}mm" '
           f'viewBox="0 0 {_f(sw)} {_f(sh)}">',
           '<g id="coupe" class="coupe" inkscape:groupmode="layer" '
           'inkscape:label="coupe" fill="none" stroke="#ff0000" '
           'stroke-width="0.1">']
    for k in range(n):
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in contour_page_mm(p, k))
        out.append(f'<polygon data-carte="{page * p.par_page + k + 1}" '
                   f'points="{pts}"/>')
    out.append("</g>")
    out.append('<g id="reperes" class="reperes" inkscape:groupmode="layer" '
               'inkscape:label="reperes" fill="#000000" stroke="none">')
    r = REPERE_DIAMETRE_MM / 2
    for x, y in p.reperes_mm:
        out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}"/>')
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def coupe_dxf(p: PlanHex, page: int) -> str:
    """La même coupe en DXF R12 (AC1009), millimètres ($INSUNITS 4), Y vers
    le HAUT comme tout DXF : y DXF = hauteur de la feuille - y. Calques
    COUPE (POLYLINE fermées, VERTEX, SEQEND) et REPERES (CIRCLE)."""
    sw, sh = p.size_mm
    n = cartes_de_page(p, page)
    L: list[str] = []

    def g(code: int, val) -> None:
        L.append(str(code))
        L.append(val if isinstance(val, str) else _f(val))

    g(0, "SECTION"); g(2, "HEADER")
    g(9, "$ACADVER"); g(1, "AC1009")
    g(9, "$INSUNITS"); g(70, "4")
    g(9, "$EXTMIN"); g(10, 0.0); g(20, 0.0); g(30, 0.0)
    g(9, "$EXTMAX"); g(10, sw); g(20, sh); g(30, 0.0)
    g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "TABLES")
    g(0, "TABLE"); g(2, "LTYPE"); g(70, "1")
    g(0, "LTYPE"); g(2, "CONTINUOUS"); g(70, "0"); g(3, "Solid line")
    g(72, "65"); g(73, "0"); g(40, 0.0)
    g(0, "ENDTAB")
    g(0, "TABLE"); g(2, "LAYER"); g(70, "2")
    for nom, couleur in (("COUPE", "1"), ("REPERES", "5")):
        g(0, "LAYER"); g(2, nom); g(70, "0"); g(62, couleur); g(6, "CONTINUOUS")
    g(0, "ENDTAB")
    g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "ENTITIES")
    for k in range(n):
        g(0, "POLYLINE"); g(8, "COUPE"); g(66, "1")
        g(10, 0.0); g(20, 0.0); g(30, 0.0); g(70, "1")
        for x, y in contour_page_mm(p, k):
            g(0, "VERTEX"); g(8, "COUPE"); g(10, x); g(20, sh - y); g(30, 0.0)
        g(0, "SEQEND"); g(8, "COUPE")
    for x, y in p.reperes_mm:
        g(0, "CIRCLE"); g(8, "REPERES")
        g(10, x); g(20, sh - y); g(30, 0.0); g(40, REPERE_DIAMETRE_MM / 2)
    g(0, "ENDSEC")
    g(0, "EOF")
    return "\n".join(L) + "\n"


def coupe_zip(p: PlanHex) -> bytes:
    """Les fichiers de coupe de toutes les pages : `page-01.svg`,
    `page-01.dxf`, `page-02.svg`…"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for page in range(p.pages):
            z.writestr(f"page-{page + 1:02d}.svg",
                       coupe_svg(p, page).encode("utf-8"))
            z.writestr(f"page-{page + 1:02d}.dxf",
                       coupe_dxf(p, page).encode("ascii"))
    return buf.getvalue()


# ── la planche imprimée ──────────────────────────────────────────────────────

def _masque(g: CardGeom) -> Image.Image:
    """Le masque du fond perdu, à la taille de la toile : la toile de la carte
    fait autorité, même sur une image déjà masquée par le navigateur."""
    k = g.dpi / MM_PER_INCH
    m = Image.new("L", tuple(g.canvas_px), 0)
    ImageDraw.Draw(m).polygon([(x * k, y * k) for x, y in hexa.contour_toile_mm(g)],
                              fill=255)
    return m


def _a_plat(im: Image.Image) -> Image.Image:
    """Sur du papier il n'y a pas d'alpha : le transparent devient blanc."""
    if im.mode == "RGB":
        return im
    im = im.convert("RGBA")
    fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(fond, im).convert("RGB")


def compose_page(p: PlanHex, images: list, page: int,
                 cote: str = "recto") -> Image.Image:
    """Une page de la planche, en bitmap à la taille exacte de la feuille
    (`sheet_px`). `images[i]` = la face de la carte i du JEU (indice global) ;
    une entrée absente ou None laisse son emplacement blanc. Recto : cartes,
    trait de coupe si `trait`, repères. Verso : cartes en miroir, repères en
    miroir, pas de trait (la coupe se fait recto dessus)."""
    g = p.geom
    k = g.dpi / MM_PER_INCH
    feuille = Image.new("RGB", p.sheet_px, (255, 255, 255))
    masque = _masque(g)
    bx, by = g.bleed_off_px
    for j in range(cartes_de_page(p, page)):
        i = page * p.par_page + j
        im = images[i] if i < len(images) else None
        if im is None:
            continue
        if tuple(im.size) != tuple(g.canvas_px):
            raise ValueError(
                f"La carte {i + 1} mesure {im.size[0]}x{im.size[1]} px ; la "
                f"géométrie du jeu impose {g.canvas_px[0]}x{g.canvas_px[1]} px")
        x, y = carte_de(p, page, j, cote)
        feuille.paste(_a_plat(im), (int(R(x * k - bx)), int(R(y * k - by))),
                      masque)
    d = ImageDraw.Draw(feuille)
    if p.trait and cote == "recto":
        ep = max(1, int(R(TRAIT_MM * k)))
        for j in range(cartes_de_page(p, page)):
            pts = [(x * k, y * k) for x, y in contour_page_mm(p, j)]
            d.line(pts + [pts[0]], fill=(40, 40, 40), width=ep, joint="curve")
    r = REPERE_DIAMETRE_MM / 2 * k
    for x, y in _repere_cote(p, cote):
        d.ellipse((x * k - r, y * k - r, x * k + r, y * k + r), fill=(0, 0, 0))
    return feuille


def pdf_planche(p: PlanHex, recto: list, verso: list | None = None) -> bytes:
    """Le PDF d'impression : par page, le recto puis (duplex) le verso.

    SANS PERTE, comme le défaut rectangulaire (`lossless: True`) : chaque
    page est UNE image RGB brute en `/FlateDecode` (zlib), écrite ici par
    pypdf (Pillow, lui, n'encode le RGB qu'en JPEG). La `/MediaBox` est la
    feuille en points EXACTS (A4 = 595,2756 x 841,8898 pt) ; l'image, à sa
    taille native `sheet_px / dpi`, est posée au coin HAUT-GAUCHE, origine
    du repère mm du plan et du fichier de coupe : aucun pixel n'est
    ré-échantillonné et aucune position ne glisse vers le bas de page."""
    import zlib
    from pypdf import PdfWriter
    from pypdf.generic import (DecodedStreamObject, DictionaryObject,
                               NameObject, NumberObject)
    verso = verso or []
    faces = []
    for page in range(p.pages):
        faces.append((page, "recto", recto))
        if p.duplex:
            faces.append((page, "verso", verso))
    pt = 72.0 / MM_PER_INCH
    pw, ph = p.size_mm[0] * pt, p.size_mm[1] * pt
    w = PdfWriter()
    for page, cote, imgs in faces:
        im = compose_page(p, imgs, page, cote)
        xo = DecodedStreamObject()
        xo.set_data(zlib.compress(im.tobytes(), 6))
        xo[NameObject("/Type")] = NameObject("/XObject")
        xo[NameObject("/Subtype")] = NameObject("/Image")
        xo[NameObject("/Width")] = NumberObject(im.size[0])
        xo[NameObject("/Height")] = NumberObject(im.size[1])
        xo[NameObject("/ColorSpace")] = NameObject("/DeviceRGB")
        xo[NameObject("/BitsPerComponent")] = NumberObject(8)
        xo[NameObject("/Filter")] = NameObject("/FlateDecode")
        iw = im.size[0] * 72.0 / p.geom.dpi
        ih = im.size[1] * 72.0 / p.geom.dpi
        pg = w.add_blank_page(width=pw, height=ph)
        res = DictionaryObject()
        res[NameObject("/XObject")] = DictionaryObject(
            {NameObject("/Im0"): w._add_object(xo)})
        pg[NameObject("/Resources")] = res
        cs = DecodedStreamObject()
        cs.set_data(("q %.4f 0 0 %.4f 0 %.4f cm /Im0 Do Q"
                     % (iw, ih, ph - ih)).encode("ascii"))
        pg[NameObject("/Contents")] = w._add_object(cs)
    w.add_metadata({"/Title": "Planche en nid d'abeilles"})
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def plan_hex_dict(p: PlanHex) -> dict:
    """La forme JSON servie par `/hex/plan`."""
    return {
        "sheet": p.sheet,
        "size_mm": list(p.size_mm),
        "sheet_px": list(p.sheet_px),
        "geom": p.geom.to_dict(),
        "marge_mm": p.marge_mm,
        "gouttiere_mm": p.gouttiere_mm,
        "cases": [[round(x, 4), round(y, 4)] for x, y in p.cases],
        "par_page": p.par_page,
        "n_cartes": p.n_cartes,
        "pages": p.pages,
        "out_pages": p.pages * (2 if p.duplex else 1),
        "reperes_mm": [[round(x, 4), round(y, 4)] for x, y in p.reperes_mm],
        "repere_diametre_mm": REPERE_DIAMETRE_MM,
        "trait": p.trait,
        "duplex": p.duplex,
        "flip": "long",
    }
