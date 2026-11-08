# -*- coding: utf-8 -*-
"""Card Forge — plateau hexagonal, lot 1, tâche 2 : découpe des tuiles.

Image de plateau -> tuiles RGBA aux dimensions de la toile du format, fond
perdu fait des pixels voisins. Aucun appel réseau, aucune dépense.

Run : <embedded python> backend/tests/test_cards_plateau_decoupe.py
"""
import math
import pathlib
import sys
import time

import pytest
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services.cards import contract as CT  # noqa: E402
from app.services.cards import hexa  # noqa: E402
from app.services.cards import plateau as P  # noqa: E402

DPI_TEST = 72     # le banc reste rapide ; la logique ne dépend pas du dpi


def _mire(w, h):
    """Chaque pixel a une couleur unique : (x % 256, y % 256, (x // 256) * 16 + y // 256)."""
    im = Image.new("RGB", (w, h))
    im.putdata([(x % 256, y % 256, (x // 256) * 16 + y // 256)
                for y in range(h) for x in range(w)])
    return im


def _centre(im):
    return (im.width // 2, im.height // 2)


def test_nombre_taille_et_ordre():
    t = P.decouper(_mire(1200, 900), P.grille("hex_p50", 3, 2), {})
    g = CT.geom("hex_p50", 300, 3.0)
    assert [(r, c) for r, c, _ in t] == [(1, 1), (1, 2), (1, 3),
                                         (2, 1), (2, 2), (2, 3)]
    assert all(im.size == g.canvas_px and im.mode == "RGBA" for _, _, im in t)


def _dans_hexagone(g, cx, cy, k, px, py, marge=0.02):
    """Le centre du pixel (px, py) est-il STRICTEMENT à l'intérieur (marge en
    pixels) de l'hexagone de coupe centré (cx, cy) mm ? Test géométrique
    indépendant du code testé : hexagone régulier de côté plat à côté plat p."""
    pointe = CT.geom(g.fmt).orientation == "pointe"
    p = min(CT.geom(g.fmt).trim_mm) * k
    demi_h = p / math.sqrt(3.0)                    # rayon (sommet) en px
    u, v = (px + 0.5) - cx * k, (py + 0.5) - cy * k
    if not pointe:
        u, v = v, u                               # transposée
    return abs(u) < p / 2 - marge and abs(v) + abs(u) / math.sqrt(3.0) < demi_h - marge


def _cas_partition(fmt, bleed, dpi, colonnes, rangees):
    g = P.grille(fmt, colonnes, rangees, bleed)
    cg = CT.geom(fmt, dpi, g.bleed_mm)
    src = _mire(900, 700)
    w = P._image_travail(src, g, {}, dpi)
    tuiles = P.decouper(src, g, {}, dpi)
    k = dpi / 25.4
    nb = bytearray(w.width * w.height)          # tuiles opaques par pixel de W
    for (r, c, im), (_, _, cx, cy) in zip(tuiles, g.centres_mm):
        ox = round(cx * k - cg.canvas_px[0] / 2)
        oy = round(cy * k - cg.canvas_px[1] / 2)
        alpha = im.getchannel("A").tobytes()
        for ly in range(im.height):
            for lx in range(im.width):
                if alpha[ly * im.width + lx] and 0 <= ox + lx < w.width                         and 0 <= oy + ly < w.height:
                    nb[(oy + ly) * w.width + ox + lx] += 1
    inside, pointes = 0, 0
    for (r, c, im), (_, _, cx, cy) in zip(tuiles, g.centres_mm):
        ox = round(cx * k - cg.canvas_px[0] / 2)
        oy = round(cy * k - cg.canvas_px[1] / 2)
        for ly in range(im.height):
            for lx in range(im.width):
                px, py = ox + lx, oy + ly
                if not (0 <= px < w.width and 0 <= py < w.height):
                    continue
                if _dans_hexagone(g, cx, cy, k, px, py):
                    inside += 1
                    a = im.getpixel((lx, ly))
                    assert a[3] == 255, (fmt, bleed, dpi, r, c, px, py)
                    assert a == w.getpixel((px, py))
                    if bleed == 0:
                        assert nb[py * w.width + px] == 1, (r, c, px, py)
                    # pixels des pointes : à moins de 2 px du sommet du haut
                    if abs(abs(py + 0.5 - cy * k) - min(cg.trim_mm) * k / math.sqrt(3.0)) < 3                             and CT.geom(fmt).orientation == "pointe":
                        pointes += 1
    assert inside > 1000
    if CT.geom(fmt).orientation == "pointe":
        assert pointes > 0
    if bleed == 0:
        # jamais deux tuiles opaques sur un même pixel : coupes disjointes
        assert max(nb) == 1


@pytest.mark.parametrize("fmt,bleed,dpi,colonnes,rangees", [
    ("hex_p50", None, 72, 3, 2),
    ("hex_p50", 0.0, 72, 3, 2),
    ("hex_f50", None, 72, 3, 2),
    ("hex_f50", 0.0, 72, 3, 2),
    ("hex_p50", 0.0, 300, 2, 1),
])
def test_partition_exacte_des_pixels(fmt, bleed, dpi, colonnes, rangees):
    # Tout pixel strictement dans l'hexagone de coupe d'une tuile (test
    # géométrique indépendant) est opaque, de la couleur de l'image de travail
    # ; sans fond perdu, il n'est opaque que dans UNE tuile (partition exacte).
    _cas_partition(fmt, bleed, dpi, colonnes, rangees)


def test_fond_perdu_vient_des_pixels_voisins():
    g = P.grille("hex_p50", 3, 3)
    cg = CT.geom("hex_p50", DPI_TEST, g.bleed_mm)
    src = _mire(900, 900)
    w = P._image_travail(src, g, {}, DPI_TEST)
    t = {(r, c): im for r, c, im in P.decouper(src, g, {}, DPI_TEST)}
    r, c, cx, cy = next(x for x in g.centres_mm if x[:2] == (2, 2))
    k = DPI_TEST / 25.4
    ox, oy = round(cx * k - cg.canvas_px[0] / 2), round(cy * k - cg.canvas_px[1] / 2)
    im = t[(2, 2)]
    hors = 0
    for ly in range(im.height):
        for lx in range(im.width):
            px, py = lx + ox, ly + oy
            a = im.getpixel((lx, ly))
            if a[3] == 255 and not _dans_hexagone(g, cx, cy, k, px, py, -0.5):
                hors += 1
                assert a == w.getpixel((px, py))
    assert hors > 100      # le fond perdu existe bien


def test_cadrage_zoom_position():
    # bande rouge x < 50 sur fond bleu ; zoom 4 calé à gauche : la bande
    # occupe la fraction 50 / (largeur du cadrage) de gauche de l'image de travail.
    src = Image.new("RGB", (800, 600), (0, 0, 255))
    src.paste((255, 0, 0), (0, 0, 50, 600))
    g = P.grille("hex_p50", 2, 2)
    _, _, rw, _ = P.cadrage_couvrant(800, 600, g.largeur_mm, g.hauteur_mm, 4, 0, 0)
    frac = 50 / rw
    assert 0.2 < frac < 0.9
    cg = CT.geom("hex_p50", DPI_TEST, g.bleed_mm)
    k = DPI_TEST / 25.4
    wlarg = round(g.largeur_mm * k)
    _, _, im = P.decouper(src, g, {"zoom": 4, "x": 0, "y": 0}, DPI_TEST)[0]
    cx, cy = g.centres_mm[0][2:]
    ox, oy = round(cx * k - cg.canvas_px[0] / 2), round(cy * k - cg.canvas_px[1] / 2)
    ly = round(cy * k) - oy
    rouge = bleu = 0
    for lx in range(im.width):
        a = im.getpixel((lx, ly))
        if a[3] != 255:
            continue
        x_rel = (ox + lx + 0.5) / wlarg
        if x_rel < frac - 0.03:
            assert a[:3] == (255, 0, 0), (lx, a)
            rouge += 1
        elif x_rel > frac + 0.03:
            assert a[:3] == (0, 0, 255), (lx, a)
            bleu += 1
    assert rouge > 5 and bleu > 5


def test_hors_contour_transparent():
    t = P.decouper(_mire(900, 700), P.grille("hex_p50", 2, 2), {}, DPI_TEST)
    for _, _, im in t:
        for xy in [(0, 0), (im.width - 1, 0), (0, im.height - 1),
                   (im.width - 1, im.height - 1)]:
            assert im.getpixel(xy)[3] == 0
        assert im.getpixel(_centre(im))[3] == 255


def test_image_minuscule_couvre_toutes_les_tuiles():
    t = P.decouper(_mire(30, 200), P.grille("hex_p90", 6, 4), {}, DPI_TEST)
    assert len(t) == 24
    assert all(im.getpixel(_centre(im))[3] == 255 for _, _, im in t)


@pytest.mark.parametrize("mode", ["P", "LA", "L", "CMYK", "RGB", "RGBA"])
def test_modes_d_image(mode):
    base = Image.new("RGB", (200, 160), (200, 120, 60))
    src = base.convert(mode)
    t = P.decouper(src, P.grille("hex_p50", 2, 2), {}, DPI_TEST)
    r, c, im = t[0]
    assert (r, c) == (1, 1) and im.mode == "RGBA"
    px = im.getpixel(_centre(im))
    assert px[3] == 255 and px[:3] != (0, 0, 0)


def _alpha_coupe_opaque(src):
    """Chaque tuile : alpha 255 au centre et sur tout l'intérieur de l'hexagone de coupe (rétréci d'un cran)."""
    g = P.grille("hex_p50", 2, 2)
    t = P.decouper(src, g, {}, DPI_TEST)
    for _, _, im in t:
        a = im.getchannel("A")
        assert a.getpixel(_centre(im)) == 255
        # les seuls pixels non opaques sont hors contour : jamais un trou au milieu
        cx, cy = _centre(im)
        for dx in range(-8, 9, 4):
            for dy in range(-8, 9, 4):
                assert a.getpixel((cx + dx, cy + dy)) == 255
    return t


def test_source_transparente_aplatie_sur_blanc():
    t = _alpha_coupe_opaque(Image.new("RGBA", (400, 300), (10, 200, 30, 0)))
    for _, _, im in t:
        assert im.getpixel(_centre(im)) == (255, 255, 255, 255)


def test_source_a_moitie_transparente():
    src = Image.new("RGBA", (400, 300), (200, 0, 0, 255))
    src.paste((0, 0, 0, 0), (0, 0, 200, 300))            # moitié gauche transparente
    t = _alpha_coupe_opaque(src)
    couleurs = {im.getpixel(_centre(im))[:3] for _, _, im in t}
    assert couleurs <= {(255, 255, 255), (200, 0, 0)} and (255, 255, 255) in couleurs and (200, 0, 0) in couleurs


def test_aplatir_apres_reduction_equivaut_a_aplatir_avant():
    """I-2 : on réduit d'abord (LANCZOS prémultiplié sur RGBA), puis on aplatit sur le petit résultat. Même image
    qu'aplatir la source en pleine taille avant de la réduire (à l'arrondi 8 bits près)."""
    src = Image.new("RGBA", (500, 400), (0, 0, 0, 0))
    src.paste((200, 20, 20, 255), (0, 0, 250, 400))                  # moitié opaque
    src.paste((20, 20, 200, 128), (250, 0, 500, 200))                # quart à moitié transparent
    g = P.grille("hex_p50", 3, 2)
    nouveau = P._image_travail(src, g, {"zoom": 1.3, "x": 0.2, "y": 0.7}, DPI_TEST)
    gauche, haut, w, h = P.cadrage_couvrant(500, 400, g.largeur_mm, g.hauteur_mm, 1.3, 0.2, 0.7)
    ancien = Image.alpha_composite(Image.new("RGBA", src.size, (255, 255, 255, 255)), src).resize(
        nouveau.size, Image.LANCZOS, box=(gauche, haut, gauche + w, haut + h))
    assert nouveau.size == ancien.size and nouveau.getchannel("A").getextrema() == (255, 255)
    # identiques à l'arrondi près partout, sauf sur quelques pixels de bord où les lobes négatifs de LANCZOS
    # écrêtent autrement (couleur prémultipliée ou non) : moins de 0,5 % des pixels, jamais d'écart de zone
    from PIL import ImageChops
    diff = ImageChops.difference(nouveau, ancien).convert("L")
    histo = diff.histogram()
    loin = sum(histo[4:])
    assert loin / (diff.width * diff.height) < 0.005, (loin, histo[:40])
    assert diff.getextrema()[1] < 40


def test_source_rgba_n_est_pas_copiee():
    src = _mire(300, 200).convert("RGBA")
    assert P._en_rgba(src) is src


def test_source_opaque_inchangee():
    src = _mire(400, 300)
    assert P._sur_blanc(src.convert("RGBA")).tobytes() == src.convert("RGBA").tobytes()


def test_source_intacte():
    src = _mire(800, 600)
    avant = src.tobytes()
    P.decouper(src, P.grille("hex_f50", 2, 2),
               {"zoom": 1.7, "x": 0.1, "y": 0.9}, DPI_TEST)
    assert src.tobytes() == avant


def test_rendement_6x4_hex_p90_300dpi(capsys):
    t0 = time.perf_counter()
    t = P.decouper(_mire(1400, 1000), P.grille("hex_p90", 6, 4), {})
    duree = time.perf_counter() - t0
    with capsys.disabled():
        print("decouper 6x4 hex_p90 300 dpi : %.2f s" % duree)
    assert len(t) == 24      # durée relevée dans le rapport, non plafonnée ici


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
