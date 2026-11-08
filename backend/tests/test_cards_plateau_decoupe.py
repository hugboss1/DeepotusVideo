# -*- coding: utf-8 -*-
"""Card Forge — plateau hexagonal, lot 1, tâche 2 : découpe des tuiles.

Image de plateau -> tuiles RGBA aux dimensions de la toile du format, fond
perdu fait des pixels voisins. Aucun appel réseau, aucune dépense.

Run : <embedded python> backend/tests/test_cards_plateau_decoupe.py
"""
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


def _plus_proche(g, px, py, k):
    """(rang, colonne) du centre le plus proche du pixel (centre de pixel)."""
    mx, my = (px + 0.5), (py + 0.5)
    return min(g.centres_mm, key=lambda c: (
        (c[2] * k - mx) ** 2 + (c[3] * k - my) ** 2, c[0], c[1]))[:2]


def test_partition_exacte_des_pixels():
    # Chaque pixel de W situé dans la COUPE d'une tuile (centre le plus proche
    # ET dans le contour de fond perdu de cette tuile) est couvert, opaque et
    # de la couleur de W, par sa tuile ; aucun pixel de coupe perdu.
    g = P.grille("hex_p50", 3, 2)
    cg = CT.geom("hex_p50", DPI_TEST, g.bleed_mm)
    cadrage = {}
    w = P._image_travail(_mire(900, 700), g, cadrage, DPI_TEST)
    tuiles = {(r, c): im for r, c, im in P.decouper(
        _mire(900, 700), g, cadrage, DPI_TEST)}
    k = DPI_TEST / 25.4
    origines = {(r, c): (round(x * k - cg.canvas_px[0] / 2),
                         round(y * k - cg.canvas_px[1] / 2))
                for r, c, x, y in g.centres_mm}
    vus = 0
    for py in range(w.height):
        for px in range(w.width):
            cle = _plus_proche(g, px, py, k)
            ox, oy = origines[cle]
            lx, ly = px - ox, py - oy
            im = tuiles[cle]
            if not (0 <= lx < im.width and 0 <= ly < im.height):
                continue       # hors toile : ce pixel n'est dans aucune coupe
            a = im.getpixel((lx, ly))
            if a[3] == 255:
                vus += 1
                assert a == w.getpixel((px, py))
    # l'essentiel de l'image de travail est dans la coupe d'une tuile (les coins vides des rangées décalées n'en sont pas)
    assert vus > 0.7 * w.width * w.height


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
    # pixels opaques hors de la coupe de (2,2) : leur couleur est celle de W
    hors, total = 0, 0
    for ly in range(im.height):
        for lx in range(im.width):
            px, py = lx + ox, ly + oy
            a = im.getpixel((lx, ly))
            if a[3] == 255 and _plus_proche(g, px, py, k) != (2, 2):
                hors += 1
                assert a == w.getpixel((px, py))
            total += 1
    assert hors > 100      # le fond perdu existe bien


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


def test_source_intacte():
    src = _mire(800, 600)
    avant = src.tobytes()
    P.decouper(src, P.grille("hex_f50", 2, 2),
               {"zoom": 1.7, "x": 0.1, "y": 0.9}, DPI_TEST)
    assert src.tobytes() == avant


def test_rendement_6x4_hex_p90_300dpi():
    t0 = time.perf_counter()
    t = P.decouper(_mire(1400, 1000), P.grille("hex_p90", 6, 4), {})
    duree = time.perf_counter() - t0
    print("decouper 6x4 hex_p90 300 dpi : %.2f s" % duree)
    assert len(t) == 24 and duree < 20


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
