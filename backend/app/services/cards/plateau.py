# -*- coding: utf-8 -*-
"""Card Forge — plateau hexagonal : géométrie de la grille de découpe.

Une image de plateau est découpée en tuiles hexagonales jointives. Ce module
ne fait que la géométrie (mm, pixels source) ; aucun format n'est recopié ici :
la mesure `p` (côté plat à côté plat) et l'orientation viennent de
`contract.FORMATS` / `contract.geom`. Miroir JS, mêmes formules :
`frontend/shared/dz-decoupe-hex-logique.js`.

Pointe en haut : pas horizontal `p`, pas vertical `0,75·h` (h = 2p/√3), les
rangées paires sont décalées de +p/2. Côté plat en haut : la transposée (les
colonnes paires sont décalées de +p/2 vers le bas, pas horizontal `0,75·h`).
Rang et colonne sont 1-based.
"""
from __future__ import annotations

import asyncio
import math
import os
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from loguru import logger
from PIL import Image, ImageChops, ImageDraw

from app.services.noms import NOM_MAX

from . import core, hexa
from .contract import FORMATS, geom, is_hex
from .depuis_images import (IMAGES_MAX, _CADRE_NU, _PREFIXE_PHOTOLAB,
                            _images_dir, _nom_valide, _verifie_presente)

__all__ = ["COTE_MAX", "TUILES_MAX", "Grille", "grille", "cadrage_couvrant",
           "ppp_effectif", "decouper", "iter_tuiles", "router", "PIXELS_MAX"]

router = APIRouter()

COTE_MAX = 30                 # colonnes ou rangées, au plus
TUILES_MAX = IMAGES_MAX       # = 500, le plafond d'un deck depuis des images
# Pixels de l'image de travail (étendue de la grille à `dpi`) : ~600 Mo en RGBA.
# Miroir JS : PIXELS_MAX de frontend/shared/dz-decoupe-hex-logique.js.
PIXELS_MAX = 150_000_000


@dataclass(frozen=True)
class Grille:
    fmt: str
    colonnes: int
    rangees: int
    bleed_mm: float
    # (rang, colonne, x, y), 1-based, rangée par rangée
    centres_mm: tuple[tuple[int, int, float, float], ...]
    # étendue des contours de coupe + 2 × fond perdu
    largeur_mm: float
    hauteur_mm: float


def _entier(valeur, nom: str) -> int:
    try:
        if isinstance(valeur, bool) or int(valeur) != valeur:
            raise ValueError
        return int(valeur)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{nom} doit être un entier (reçu {valeur!r})")


def grille(fmt: str, colonnes: int, rangees: int,
           bleed_mm: float | None = None) -> Grille:
    """Grille hexagonale `colonnes` × `rangees` du format `fmt`.

    `bleed_mm=None` : fond perdu natif du format. Lève `ValueError` sur un
    format non hexagonal, un nombre de colonnes/rangées hors 1..COTE_MAX ou
    plus de TUILES_MAX tuiles, un fond perdu hors bornes."""
    cle = str(fmt or "").strip().lower()
    if not is_hex(cle):
        raise ValueError(f"Format non hexagonal : {fmt!r}")
    nc, nr = _entier(colonnes, "colonnes"), _entier(rangees, "rangées")
    if not (1 <= nc <= COTE_MAX and 1 <= nr <= COTE_MAX):
        raise ValueError(
            f"colonnes et rangées doivent tenir entre 1 et {COTE_MAX}")
    if nc * nr > TUILES_MAX:
        raise ValueError(f"{nc * nr} tuiles : {TUILES_MAX} au plus")

    g = geom(cle, bleed_mm=bleed_mm)      # valide aussi le fond perdu
    b = g.bleed_mm
    p = min(g.trim_mm)
    h = 2.0 * p / math.sqrt(3.0)
    pointe = g.orientation == "pointe"
    pas = 0.75 * h

    centres = []
    for r in range(1, nr + 1):
        for c in range(1, nc + 1):
            if pointe:
                x = b + p / 2 + (c - 1) * p + (p / 2 if r % 2 == 0 else 0.0)
                y = b + h / 2 + (r - 1) * pas
            else:
                x = b + h / 2 + (c - 1) * pas
                y = b + p / 2 + (r - 1) * p + (p / 2 if c % 2 == 0 else 0.0)
            centres.append((r, c, x, y))

    if pointe:
        largeur = nc * p + (p / 2 if nr > 1 else 0.0) + 2 * b
        hauteur = h + (nr - 1) * pas + 2 * b
    else:
        largeur = h + (nc - 1) * pas + 2 * b
        hauteur = nr * p + (p / 2 if nc > 1 else 0.0) + 2 * b
    return Grille(cle, nc, nr, b, tuple(centres), largeur, hauteur)


def cadrage_couvrant(src_w: int, src_h: int, ext_w: float, ext_h: float,
                     zoom: float = 1.0, x: float = 0.5,
                     y: float = 0.5) -> tuple[float, float, float, float]:
    """Rectangle (gauche, haut, largeur, hauteur) en pixels source, du rapport
    `ext_w/ext_h`. zoom=1 : le plus grand rectangle de ce rapport contenu dans
    l'image ; zoom>1 le divise ; `x`, `y` ∈ [0, 1] = position dans la course
    libre. zoom<1 est ramené à 1, x et y sont bornés."""
    rapport = ext_w / ext_h
    if src_w / src_h > rapport:
        w0, h0 = src_h * rapport, float(src_h)
    else:
        w0, h0 = float(src_w), src_w / rapport
    z = max(1.0, float(zoom))
    w, h = w0 / z, h0 / z
    fx = min(1.0, max(0.0, float(x)))
    fy = min(1.0, max(0.0, float(y)))
    return (fx * (src_w - w), fy * (src_h - h), w, h)


def ppp_effectif(rect_w_px: float, largeur_mm: float) -> float:
    """Points par pouce réels : pixels source du cadrage / largeur imprimée."""
    return rect_w_px / (largeur_mm / 25.4)


def _en_rgba(src: Image.Image) -> Image.Image:
    """RGBA quel que soit le mode d'entrée (P avec transparence, LA, L, CMYK…).
    Renvoie toujours une copie : la source n'est jamais modifiée."""
    if src.mode == "RGBA":
        return src.copy()
    if src.mode == "P":
        return src.convert("RGBA")       # honore la transparence de palette
    if src.mode in ("LA", "La", "RGBa", "PA"):
        return src.convert("RGBA")
    return src.convert("RGB").convert("RGBA")


def _sur_blanc(im: Image.Image) -> Image.Image:
    """`im` (RGBA) composée sur du BLANC opaque. Les zones transparentes de la
    source (document sans fond, calque vide, PNG détouré) deviennent du blanc :
    elles ne creusent pas de trous dans les tuiles."""
    if im.getchannel("A").getextrema()[0] == 255:
        return im
    fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(fond, im)


def _image_travail(src: Image.Image, g: Grille, cadrage: dict,
                   dpi: int) -> Image.Image:
    """Le cadrage couvrant de `src`, rééchantillonné UNE fois (LANCZOS) à
    l'étendue de la grille en pixels : toutes les tuiles en sont des
    fenêtres, donc le fond perdu d'une tuile est fait des pixels voisins.
    La source est d'abord APLATIE sur du blanc opaque : l'alpha d'une tuile ne
    vient ensuite que du masque coupe ∪ fond perdu."""
    cadrage = cadrage or {}
    gauche, haut, w, h = cadrage_couvrant(
        src.width, src.height, g.largeur_mm, g.hauteur_mm,
        cadrage.get("zoom", 1.0), cadrage.get("x", 0.5), cadrage.get("y", 0.5))
    taille = (max(1, round(g.largeur_mm / 25.4 * dpi)),
              max(1, round(g.hauteur_mm / 25.4 * dpi)))
    return _sur_blanc(_en_rgba(src)).resize(
        taille, Image.LANCZOS, box=(gauche, haut, gauche + w, haut + h))


def _origine_tuile(cx_mm: float, cy_mm: float, dpi: int,
                   canvas: tuple[int, int]) -> tuple[int, int]:
    """Coin haut-gauche (pixels de l'image de travail) de la toile d'une tuile."""
    k = dpi / 25.4
    return (round(cx_mm * k - canvas[0] / 2), round(cy_mm * k - canvas[1] / 2))


_Q = 1024     # les centres sont quantifiés au 1/1024 de pixel : tests exacts


def _masque_coupe(index: int, centres: list[tuple[int, int]],
                  origine: tuple[int, int], canvas: tuple[int, int]) -> Image.Image:
    """Pixels de la toile (centre de pixel) dont le centre de grille le plus
    proche est la tuile `index` ; égalité : plus petit index (= plus petit
    (rang, colonne)). Calcul exact en entiers, rangée par rangée : chaque
    autre centre ne retient qu'un intervalle de colonnes."""
    cw, ch = canvas
    ox, oy = origine
    tx, ty = centres[index]
    # un centre plus loin que la diagonale de la toile ne peut pas gagner
    rayon = 2 * math.hypot(cw, ch) * _Q
    voisins = []
    for j, (ux, uy) in enumerate(centres):
        if j != index and math.hypot(ux - tx, uy - ty) <= rayon:
            voisins.append((ux - tx, uy - ty, tx * tx + ty * ty - ux * ux - uy * uy,
                            index < j))
    masque = Image.new("L", canvas, 0)
    dessin = ImageDraw.Draw(masque)
    for ly in range(ch):
        py = _Q * (oy + ly) + _Q // 2
        bas, haut = ox, ox + cw - 1            # colonnes globales candidates
        for dx, dy, dk, gagne_egalite in voisins:
            # d(X) = A·X + B  ;  la tuile gagne si d < 0 (ou d <= 0 à égalité)
            a_ = 2 * _Q * dx
            b_ = 2 * (_Q // 2) * dx + 2 * py * dy + dk
            if a_ == 0:
                if b_ > 0 or (b_ == 0 and not gagne_egalite):
                    bas, haut = 1, 0
                    break
                continue
            if a_ > 0:
                lim = (-b_) // a_ if gagne_egalite else (-b_ - 1) // a_
                haut = min(haut, lim)
            else:
                m = -a_
                lim = -((-b_) // m) if gagne_egalite else b_ // m + 1
                bas = max(bas, lim)
            if bas > haut:
                break
        if bas <= haut:
            dessin.line([(bas - ox, ly), (haut - ox, ly)], fill=255)
    return masque


def decouper(src: Image.Image, g: Grille, cadrage: dict,
             dpi: int = 300) -> list[tuple[int, int, Image.Image]]:
    """`iter_tuiles` rassemblé en liste (petites grilles, bancs)."""
    return list(iter_tuiles(src, g, cadrage, dpi))


def pixels_travail(g: Grille, dpi: int) -> int:
    """Pixels de l'image de travail d'une grille à `dpi`."""
    return (max(1, round(g.largeur_mm / 25.4 * dpi))
            * max(1, round(g.hauteur_mm / 25.4 * dpi)))


def iter_tuiles(src: Image.Image, g: Grille, cadrage: dict, dpi: int = 300):
    """Découpe `src` en tuiles RGBA (rang, colonne, image), ordre de lecture,
    UNE à la fois (générateur) à partir de l'unique image de travail.

    Chaque tuile est une fenêtre de l'image de travail à la taille de la toile
    du format (`geom(fmt, dpi, bleed).canvas_px`). Alpha 255 = COUPE (pixel
    dont le centre de grille le plus proche, sur les centres FLOTTANTS de toute
    la grille, est cette tuile) ∪ FOND PERDU (intérieur du contour de fond
    perdu, posé sur le vrai centre et non sur l'origine arrondie) ; 0 ailleurs.
    Chaque pixel de coupe est ainsi dans une seule tuile, même sans fond perdu,
    et le fond perdu est fait des pixels réels des voisines. La coupe est
    bornée à l'hexagone de coupe élargi d'un pixel (les tuiles du bord n'ont
    pas de cellule infinie). La source est aplatie sur du blanc (voir
    `_image_travail`) : un pixel de coupe est toujours opaque, même si la
    source est transparente. Fonction pure : `src` n'est pas modifié."""
    cg = geom(g.fmt, dpi, g.bleed_mm)
    canvas = cg.canvas_px
    travail = _image_travail(src, g, cadrage, dpi)
    k = dpi / 25.4
    mm = 25.4 / dpi
    # centre de l'hexagone dans le repère toile (mm) et contours (repère toile)
    ccx = cg.bleed_off_px[0] * mm + cg.trim_mm[0] / 2
    ccy = cg.bleed_off_px[1] * mm + cg.trim_mm[1] / 2
    ox_c, oy_c = cg.bleed_off_px[0] * mm, cg.bleed_off_px[1] * mm
    bleed_toile = hexa.contour_toile_mm(cg)
    coupe_large = [(x + ox_c, y + oy_c) for x, y in
                   hexa.decale(cg.contour_mm, mm)]    # coupe élargie de 1 px
    centres_q = [(round(cx * k * _Q), round(cy * k * _Q))
                 for _, _, cx, cy in g.centres_mm]
    for i, (rang, col, cx, cy) in enumerate(g.centres_mm):
        origine = _origine_tuile(cx, cy, dpi, canvas)
        # position du vrai centre dans la toile de la tuile (px, flottant)
        vx, vy = cx * k - origine[0], cy * k - origine[1]

        def local(pts):
            return [((x - ccx) * k + vx, (y - ccy) * k + vy) for x, y in pts]

        fond = Image.new("L", canvas, 0)
        if g.bleed_mm > 0:      # sans fond perdu, le contour n'est que la coupe
            ImageDraw.Draw(fond).polygon(local(bleed_toile), fill=255)
        borne = Image.new("L", canvas, 0)
        ImageDraw.Draw(borne).polygon(local(coupe_large), fill=255)
        coupe = ImageChops.multiply(
            _masque_coupe(i, centres_q, origine, canvas), borne)
        masque = ImageChops.lighter(fond, coupe)
        tuile = travail.crop((origine[0], origine[1],
                              origine[0] + canvas[0], origine[1] + canvas[1]))
        alpha = Image.new("L", canvas, 0)
        alpha.paste(tuile.getchannel("A"), mask=masque)
        tuile.putalpha(alpha)
        yield (rang, col, tuile)


# ── la route : POST /api/cards/decks/plateau ────────────────────────────────

def _base(nom: str) -> str:
    """Le nom source sans extension ni préfixe de retouche du Photolab."""
    tige = os.path.splitext(nom)[0]
    return _PREFIXE_PHOTOLAB.sub("", tige) or tige


def _nombre(valeur, champ: str) -> float:
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) \
            or not math.isfinite(valeur):
        raise HTTPException(400, f"{champ} : un nombre attendu")
    return float(valeur)


def preparer(body) -> dict:
    """Valide TOUT le corps et rend les paramètres de la découpe. Lève
    HTTPException. Aucun effet de bord : appelée avant toute écriture."""
    if not isinstance(body, dict):
        raise HTTPException(400, "Corps JSON attendu")
    image = _nom_valide(body.get("image"), "image")
    fmt_in = body.get("format")
    if isinstance(fmt_in, str):
        fmt_in = {"fmt": fmt_in}
    if not isinstance(fmt_in, dict):
        raise HTTPException(400, "format : un objet {fmt, …} attendu")
    fmt_id = str(fmt_in.get("fmt") or "").strip().lower()
    if fmt_id not in FORMATS:
        raise HTTPException(400, f"format inconnu : {fmt_id!r}")
    if not is_hex(fmt_id):
        raise HTTPException(400, f"format non hexagonal : {fmt_id!r}")
    fmt = dict(fmt_in)
    fmt["fmt"] = fmt_id
    cadrage_in = body.get("cadrage")
    if cadrage_in is None:
        cadrage = {}
    elif isinstance(cadrage_in, dict):
        cadrage = {k: _nombre(cadrage_in[k], f"cadrage.{k}")
                   for k in ("zoom", "x", "y") if k in cadrage_in}
    else:
        raise HTTPException(400, "cadrage : un objet {zoom, x, y} attendu")
    dpi = body.get("dpi", 300)
    if isinstance(dpi, bool):
        raise HTTPException(400, "dpi : un entier attendu")
    try:
        geom(fmt_id, dpi)                    # valide le dpi (bornes de contract)
        g = grille(fmt_id, body.get("colonnes"), body.get("rangees"),
                   fmt.get("bleed_mm"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    mpx = round(pixels_travail(g, int(dpi)) / 1e6)
    if pixels_travail(g, int(dpi)) > PIXELS_MAX:
        raise HTTPException(
            400, f"image de travail trop grande : {mpx} Mpx pour {PIXELS_MAX // 1_000_000} Mpx "
                 "au plus ; réduisez le nombre de tuiles, la taille ou le dpi")
    commun = body.get("verso_commun")
    if commun is not None:
        _nom_valide(commun, "verso_commun")
    for n in dict.fromkeys([image] + ([commun] if commun else [])):
        _verifie_presente(n)
    base = _base(image)
    return {"image": image, "base": base, "grille": g, "format": fmt,
            "cadrage": cadrage, "dpi": int(dpi), "dos": commun or "",
            "name": core.clean_name(body.get("name"), f"Plateau — {base}")}


def _nom_tuile(base: str, did: str, rang: int, col: int) -> str:
    fin = f"_{did[-8:]}_r{rang:02d}c{col:02d}.png"
    return "tuile_" + base[:NOM_MAX - len("tuile_") - len(fin)] + fin


def _ecrire_tuile(tuile: Image.Image, chemin, dpi: int) -> None:
    tuile.save(chemin, "PNG", dpi=(dpi, dpi))


def _ouvrir_source(prep: dict) -> Image.Image:
    """La source décodée, ouverte en LECTURE puis refermée. Toute erreur de
    décodage (fichier tronqué, corrompu, bombe) est un 400, avant tout effet."""
    try:
        with Image.open(_images_dir() / prep["image"]) as im:
            im.load()
            return im.copy() if im.mode == "RGBA" else im.convert("RGBA")
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400, f"image illisible : {prep['image']}")


def _defaire(did: str, tuiles: list[str]) -> None:
    racine = _images_dir()
    restes = []
    for nom in tuiles:
        try:
            (racine / nom).unlink(missing_ok=True)
        except OSError:
            restes.append(nom)
    if not core.delete_deck(did) or restes:
        logger.error("cards: retour en arrière du plateau incomplet : jeu {} "
                     "(supprimé : {}), tuiles non retirées : {}", did,
                     not (core.deck_dir(did).exists()), restes)


def _fabriquer(prep: dict) -> tuple[dict, list[str], float]:
    """Lit la source, crée le jeu, écrit les tuiles UNE à UNE, ensemence.
    Toute exception après `create_deck` supprime les tuiles déjà écrites ET
    le jeu avant de remonter."""
    src = _ouvrir_source(prep)
    g, cad = prep["grille"], prep["cadrage"]
    rect_w = cadrage_couvrant(src.width, src.height, g.largeur_mm,
                              g.hauteur_mm, cad.get("zoom", 1.0),
                              cad.get("x", 0.5), cad.get("y", 0.5))[2]
    ppp = round(ppp_effectif(rect_w, g.largeur_mm), 1)
    doc = core.create_deck(prep["name"])
    did, noms, rows = doc["id"], [], []
    largeur = 3 if len(g.centres_mm) > 99 else 2
    try:
        racine = _images_dir()
        for i, (rang, col, tuile) in enumerate(
                iter_tuiles(src, g, cad, prep["dpi"]), 1):
            nom = _nom_tuile(prep["base"], did, rang, col)
            noms.append(nom)         # avant l'écriture : un fichier partiel part aussi
            _ecrire_tuile(tuile, racine / nom, prep["dpi"])
            rows.append([f"plateau-{i:0{largeur}d}", nom, prep["dos"],
                         str(rang), str(col)])
        out = core.patch_deck(did, {
            "format": prep["format"],
            "frame": dict(_CADRE_NU),
            "type": {"slots": [], "seeded": True, "sel": ""},
            "face": {"seeded": True, "fit": "cover", "src": None,
                     "default_art": None},
            "data": {"columns": ["nom", "art", "dos", "rang", "colonne"],
                     "rows": rows, "map": {"art": "art", "dos": "back"}},
        })
        if out is not None:
            out = core.poser_categorie(did, "plateau")
        if out is None:
            raise OSError("deck disparu après sa création")
        return out, noms, ppp
    except BaseException:
        _defaire(did, noms)
        raise


@router.post("/decks/plateau")
async def post_plateau(body: dict | None = None):
    prep = await asyncio.to_thread(preparer, body)
    try:
        deck, noms, ppp = await asyncio.to_thread(_fabriquer, prep)
    except OSError as e:
        logger.exception("cards: découpe du plateau impossible")
        raise HTTPException(500, "Création du plateau impossible : écriture "
                                 f"refusée ({e.strerror or 'E/S'})")
    from app.services import library_index
    await library_index.noter(noms, "cardforge", deck_id=deck["id"],
                              parent=prep["image"], relation="plateau")
    return {"deck": deck, "tuiles": noms, "ppp": ppp}
