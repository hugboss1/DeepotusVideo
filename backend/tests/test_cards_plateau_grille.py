# -*- coding: utf-8 -*-
"""Card Forge — plateau hexagonal, lot 1, tâche 1 : géométrie de la grille.

Python (`app/services/cards/plateau.py`) et son miroir JS
(`frontend/shared/dz-decoupe-hex-logique.js`) : mêmes formules, mêmes valeurs.
Aucun appel réseau, aucune dépense.

Run : <embedded python> backend/tests/test_cards_plateau_grille.py
"""
import itertools
import math
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services.cards import contract as CT  # noqa: E402
from app.services.cards import plateau as P  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
JS = RACINE / "frontend" / "shared" / "dz-decoupe-hex-logique.js"


def test_pointe_6x4_90mm_etendue_et_centres():
    g = P.grille("hex_p90", 6, 4)
    h = 90 * 2 / math.sqrt(3)
    assert g.bleed_mm == 3.0 and len(g.centres_mm) == 24
    assert g.largeur_mm == pytest.approx(6 * 90 + 45 + 6)
    assert g.hauteur_mm == pytest.approx(h + 3 * 0.75 * h + 6)
    assert g.centres_mm[0] == pytest.approx((1, 1, 3 + 45, 3 + h / 2))
    assert g.centres_mm[6][:2] == (2, 1) and g.centres_mm[6][2] == pytest.approx(3 + 45 + 45)


@pytest.mark.parametrize("fmt", ["hex_p50", "hex_f635"])
def test_voisins_a_distance_p(fmt):
    g = P.grille(fmt, 4, 3)
    p = min(CT.geom(fmt, 300).trim_mm)
    pts = {(r, c): (x, y) for r, c, x, y in g.centres_mm}
    dist = [math.dist(pts[a], pts[b]) for a, b in itertools.combinations(pts, 2)]
    assert min(dist) == pytest.approx(p, abs=1e-9)
    voisins = [k for k in pts if k != (2, 2)
               and abs(math.dist(pts[k], pts[(2, 2)]) - p) < 1e-9]
    assert len(voisins) == 6


def test_plat_est_la_transposee():
    a, b = P.grille("hex_p75", 3, 5), P.grille("hex_f75", 5, 3)
    assert a.largeur_mm == pytest.approx(b.hauteur_mm)
    assert a.hauteur_mm == pytest.approx(b.largeur_mm)


def test_plat_decalage_des_colonnes_paires():
    g = P.grille("hex_f50", 2, 2)
    pts = {(r, c): (x, y) for r, c, x, y in g.centres_mm}
    assert pts[(1, 2)][1] - pts[(1, 1)][1] == pytest.approx(25)
    assert pts[(1, 1)][0] == pytest.approx(3 + 50 * 2 / math.sqrt(3) / 2)


def test_une_seule_rangee_sans_demi_decalage():
    assert P.grille("hex_p50", 3, 1).largeur_mm == pytest.approx(3 * 50 + 6)


def test_fond_perdu_explicite():
    assert P.grille("hex_p50", 1, 1, bleed_mm=0).largeur_mm == pytest.approx(50)


@pytest.mark.parametrize("args", [("poker", 2, 2), ("hex_p50", 0, 2),
                                  ("hex_p50", 31, 1), ("hex_p50", 30, 17)])
def test_bornes(args):
    with pytest.raises(ValueError):
        P.grille(*args)


def test_cadrage_couvrant():
    assert P.cadrage_couvrant(2000, 1000, 2, 1) == pytest.approx((0, 0, 2000, 1000))
    assert P.cadrage_couvrant(2000, 1000, 1, 1) == pytest.approx((500, 0, 1000, 1000))
    assert P.cadrage_couvrant(2000, 1000, 1, 1, x=0) == pytest.approx((0, 0, 1000, 1000))
    assert P.cadrage_couvrant(2000, 1000, 1, 1, zoom=2, x=1, y=1) == pytest.approx((1500, 500, 500, 500))
    assert P.cadrage_couvrant(2000, 1000, 1, 1, zoom=0.2) == P.cadrage_couvrant(2000, 1000, 1, 1)


def test_ppp_effectif():
    assert P.ppp_effectif(3000, 254) == pytest.approx(300)


def test_constantes():
    from app.services.cards import depuis_images
    assert P.COTE_MAX == 30 and P.TUILES_MAX == depuis_images.IMAGES_MAX == 500


def test_miroir_js_formats_identiques_au_contrat():
    """FORMATS_HEX du miroir JS = contract.FORMATS (p = min(trim_mm), orientation)."""
    src = JS.read_text(encoding="utf-8")
    m = re.search(r"export const FORMATS_HEX\s*=\s*(\{.*?\n\});", src, re.S)
    assert m, "FORMATS_HEX introuvable dans le miroir JS"
    table = re.findall(r'(hex_\w+)\s*:\s*\{\s*p\s*:\s*([\d.]+)\s*,\s*o\s*:\s*"(\w+)"\s*\}', m.group(1))
    js = {k: (float(p), o) for k, p, o in table}
    attendu = {k: (min(v["trim_mm"]), v["orientation"])
               for k, v in CT.FORMATS.items() if CT.is_hex(k)}
    assert len(attendu) == 8 and set(js) == set(attendu)
    for k, (p, o) in attendu.items():
        assert js[k][1] == o and js[k][0] == pytest.approx(p, abs=0.01), k


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
