"""Post-traitement d'une image de sprite, en PIL PUR (plan sprites, T6 / P4 ; t110 du suivi).

AUCUNE BOUCLE PYTHON PAR PIXEL, et c'est la contrainte qui a dicté chaque choix : `MaxFilter`, `MedianFilter`,
`BoxBlur` et `GaussianBlur` sont implémentés en C dans Pillow, et `point()` construit une table de 256 entrées — pas
une boucle sur les pixels. Le runtime embarqué n'a pas numpy (`pixel_ops.py` le dit déjà en tête).

ORDRE : nettoyage -> contour -> ombre. Le nettoyage d'abord, sinon un pixel orphelin recevrait son propre anneau de
contour ; l'ombre en dernier, pour qu'elle porte la silhouette CONTOUR COMPRIS — c'est ce qu'un artiste attend.

La toile GRANDIT (le contour déborde, l'ombre se décale) : `apply_post` rend donc une image plus grande que celle qu'on
lui donne. C'est pourquoi il tourne dans `generate_sprites`, AVANT `_assemble` — qui mesure la cellule « native » sur
les images qu'on lui passe. Les particules et les séquences Kenney appellent `_assemble` directement : elles n'héritent
pas du post, et c'est voulu (un contour de 1 px sur une étincelle n'a pas de sens).
"""
from __future__ import annotations

import re

from PIL import Image, ImageChops, ImageFilter, ImageOps

__all__ = ["normalize_post", "apply_post"]

_HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


# ── normalisation ───────────────────────────────────────────────────────────
def _int(bloc: dict, nom: str, defaut: int, lo: int, hi: int) -> int:
    brut = bloc.get(nom)
    if brut is None or brut == "":
        return defaut
    try:
        v = int(brut)
    except (TypeError, ValueError):
        raise ValueError(f"post.{nom} must be an integer ({lo}..{hi})")
    if not lo <= v <= hi:
        raise ValueError(f"post.{nom} must be between {lo} and {hi}")
    return v


def _couleur(v, defaut: tuple[int, int, int, int]):
    if v in (None, ""):
        return defaut
    m = _HEX.match(str(v))
    if not m:
        raise ValueError(f"post color {v!r} must be #RRGGBB or #RRGGBBAA")
    h = m.group(1)
    vals = tuple(int(h[i:i + 2], 16) for i in range(0, len(h), 2))
    return vals if len(vals) == 4 else vals + (255,)


def normalize_post(spec) -> dict | None:
    """{outline?, shadow?, clean?} normalisé, ou **None** quand rien n'est demandé — le None fait sauter toute la
    passe dans `generate_sprites`, plutôt que de payer une copie d'image pour ne rien faire."""
    if spec in (None, "", {}):
        return None
    if not isinstance(spec, dict):
        raise ValueError("post must be an object {outline, shadow, clean}")
    out: dict = {}

    ol = spec.get("outline")
    if ol not in (None, "", {}):
        if not isinstance(ol, dict):
            raise ValueError("post.outline must be an object {width, color}")
        out["outline"] = {"width": _int(ol, "width", 1, 1, 4),
                          "color": _couleur(ol.get("color"), (0, 0, 0, 255))}

    sh = spec.get("shadow")
    if sh not in (None, "", {}):
        if not isinstance(sh, dict):
            raise ValueError("post.shadow must be an object {dx, dy, blur, opacity, color}")
        out["shadow"] = {"dx": _int(sh, "dx", 2, -32, 32),
                         "dy": _int(sh, "dy", 2, -32, 32),
                         "blur": _int(sh, "blur", 0, 0, 4),
                         "opacity": _int(sh, "opacity", 110, 0, 255),
                         "color": _couleur(sh.get("color"), (0, 0, 0, 255))}

    cl = spec.get("clean")
    if cl not in (None, "", {}):
        if not isinstance(cl, dict):
            raise ValueError("post.clean must be an object {orphans, smooth}")
        c = {"orphans": bool(cl.get("orphans")), "smooth": bool(cl.get("smooth"))}
        if c["orphans"] or c["smooth"]:
            out["clean"] = c

    return out or None


# ── briques ─────────────────────────────────────────────────────────────────
def _masque(im: Image.Image) -> Image.Image:
    """Alpha BINAIRE (seuil 128) — même seuil que `pixel_ops.pixelate`, sinon un bord à demi transparent produirait
    un contour à demi transparent et le pixel-art perdrait sa netteté."""
    return im.getchannel("A").point(lambda a: 255 if a >= 128 else 0)


def _nettoyer(im: Image.Image, cl: dict) -> Image.Image:
    mask = _masque(im)
    if cl["orphans"]:
        # BoxBlur(1) = moyenne d'une fenêtre 3x3, x255. Un pixel opaque SEUL vaut 255/9 = 28 ; lui plus UN voisin,
        # 57 ; un trio, 85. Le seuil 56 retire donc le pixel seul et le couple, garde le trio.
        dens = mask.filter(ImageFilter.BoxBlur(1))
        mask = ImageChops.multiply(mask, dens.point(lambda v: 255 if v > 56 else 0))
        # TROU d'un pixel dans une zone pleine : 8 voisins sur 9 -> 226.
        trou = ImageChops.multiply(dens.point(lambda v: 255 if v >= 200 else 0), mask.point(lambda v: 255 - v))
        mask = ImageChops.lighter(mask, trou)
    if cl["smooth"]:
        # médiane 3x3 sur un masque binaire = vote majoritaire : une dent d'un pixel disparaît, un trait continu
        # d'un pixel de large survit.
        mask = mask.filter(ImageFilter.MedianFilter(3)).point(lambda v: 255 if v >= 128 else 0)
    # les pixels DEVENUS opaques (trous bouchés) n'ont pas de couleur sous eux : on leur donne la médiane du
    # voisinage, les autres gardent la leur.
    rgb = im.convert("RGB")
    out = Image.composite(rgb, rgb.filter(ImageFilter.MedianFilter(3)), _masque(im)).convert("RGBA")
    out.putalpha(mask)
    return out


def _contour(im: Image.Image, ol: dict) -> Image.Image:
    """Dilatation de l'alpha par `MaxFilter(3)` répétée `width` fois, moins le masque d'origine : l'anneau
    EXTÉRIEUR, exactement `width` pixels."""
    mask = _masque(im)
    grossi = mask
    for _ in range(ol["width"]):
        grossi = grossi.filter(ImageFilter.MaxFilter(3))
    anneau = ImageChops.subtract(grossi, mask)
    r, g, b, a = ol["color"]
    couche = Image.new("RGBA", im.size, (r, g, b, 0))
    couche.putalpha(anneau.point(lambda v: v * a // 255))
    return Image.alpha_composite(couche, im)


def _ombre(im: Image.Image, sh: dict) -> Image.Image:
    mask = _masque(im)
    if sh["blur"]:
        mask = mask.filter(ImageFilter.GaussianBlur(sh["blur"]))
    r, g, b, a = sh["color"]
    opac = sh["opacity"] * a // 255
    couche = Image.new("RGBA", im.size, (r, g, b, 0))
    couche.putalpha(mask.point(lambda v: v * opac // 255))
    fond = Image.new("RGBA", im.size, (0, 0, 0, 0))
    # `paste` accepte une boîte NÉGATIVE et rogne : c'est ce qui rend dx/dy négatifs sans arithmétique de bord
    # (alpha_composite, lui, refuserait). SANS masque : le fond est vide, le copier tel quel est exact — passer
    # `couche` en masque appliquerait son alpha DEUX fois (opacité 128 -> 64, mesuré par le banc).
    fond.paste(couche, (sh["dx"], sh["dy"]))
    return Image.alpha_composite(fond, im)


# ── op ──────────────────────────────────────────────────────────────────────
def apply_post(img: Image.Image, opts: dict | None) -> Image.Image:
    """Image -> image post-traitée, PLUS GRANDE de `pad` de chaque côté."""
    if not opts:
        return img
    im = img.convert("RGBA")
    ol, sh, cl = opts.get("outline"), opts.get("shadow"), opts.get("clean")
    pad = 0
    if ol:
        pad = max(pad, ol["width"])
    if sh:
        pad = max(pad, abs(sh["dx"]) + sh["blur"], abs(sh["dy"]) + sh["blur"])
    if pad:
        im = ImageOps.expand(im, pad, (0, 0, 0, 0))
    if cl:
        im = _nettoyer(im, cl)
    if ol:
        im = _contour(im, ol)
    if sh:
        im = _ombre(im, sh)
    return im
