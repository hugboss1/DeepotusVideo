# -*- coding: utf-8 -*-
"""Card Forge — t421 (tâche 6) : le gabarit hexagonal à télécharger.

`hexa.gabarit_png(g)` : un PNG RGBA de la taille de la toile, DPI inscrit, transparent partout sauf sur les traits.
`hexa.gabarit_svg(g)` : le même dessin en millimètres (groupes coupe, fond-perdu, zone-sure ; six repères milieu).
`GET /api/cards/gabarit/{fmt}.{svg|png}?bleed_mm=&dpi=` : 404 sur un rectangle.

Run : <embedded python> backend/tests/test_cards_gabarit_hexa.py
"""
import asyncio
import io
import os
import pathlib
import re
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["DEEPOTUS_DATA_DIR"] = str(pathlib.Path(_tmp, "data"))
for d in ("images", "outputs", "data"):
    pathlib.Path(_tmp, d).mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402
from PIL import Image                                           # noqa: E402

from app.services.cards import contract as CT, hexa             # noqa: E402

HEX = [f for f in CT.FORMATS if CT.is_hex(f)]


def _api(path: str):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.get(path)
    return asyncio.run(go())


def _groupe(svg: str, ident: str) -> str:
    m = re.search(r'<g id="%s"[^>]*>(.*?)</g>' % ident, svg, re.S)
    assert m, ident
    return m.group(1)


def _points(contenu: str) -> list:
    m = re.search(r'points="([^"]+)"', contenu)
    assert m
    return [tuple(float(v) for v in p.split(",")) for p in m.group(1).split()]


@pytest.mark.parametrize("fmt", HEX)
def test_png_rgba_taille_dpi_et_transparence(fmt):
    g = CT.geom(fmt, 300)
    im = Image.open(io.BytesIO(hexa.gabarit_png(g)))
    assert im.format == "PNG" and im.mode == "RGBA"
    assert im.size == tuple(g.canvas_px)
    assert round(im.info["dpi"][0]) == 300 and round(im.info["dpi"][1]) == 300
    w, h = im.size
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        assert im.getpixel(xy)[3] == 0, xy
    # rien de plein : le centre est transparent, les traits sont une mince fraction
    assert im.getpixel((w // 2, h // 2))[3] == 0
    opaques = im.size[0] * im.size[1] - im.getchannel("A").histogram()[0]
    assert 0 < opaques < 0.08 * w * h


def test_png_dpi_inscrit_suit_le_dpi_demande():
    g = CT.geom("hex_p75", 600)
    im = Image.open(io.BytesIO(hexa.gabarit_png(g)))
    assert im.size == tuple(g.canvas_px) and round(im.info["dpi"][0]) == 600


def test_png_les_traits_tombent_sur_les_contours():
    g = CT.geom("hex_p75", 300)
    im = Image.open(io.BytesIO(hexa.gabarit_png(g)))
    k = 300 / 25.4
    x, y = hexa.contour_coupe_toile_mm(g)[1]      # un sommet de la coupe
    zone = [im.getpixel((int(x * k) + dx, int(y * k) + dy))[3]
            for dx in range(-3, 4) for dy in range(-3, 4)]
    assert max(zone) > 0


@pytest.mark.parametrize("fmt", HEX)
def test_svg_structure_et_millimetres(fmt):
    g = CT.geom(fmt, 300)
    svg = hexa.gabarit_svg(g)
    k = 25.4 / 300
    w, h = g.canvas_px[0] * k, g.canvas_px[1] * k
    mw = re.search(r'width="([\d.]+)mm"', svg)
    mh = re.search(r'height="([\d.]+)mm"', svg)
    assert mw and mh
    assert abs(float(mw.group(1)) - w) < 0.01 and abs(float(mh.group(1)) - h) < 0.01
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    assert vb[:2] == [0, 0] and abs(vb[2] - w) < 0.01 and abs(vb[3] - h) < 0.01
    for ident in ("coupe", "fond-perdu", "zone-sure"):
        assert 'id="%s"' % ident in svg
    assert len(re.findall(r'class="milieu"', svg)) == 6
    assert "<text" not in svg


@pytest.mark.parametrize("fmt", HEX)
def test_svg_sommets_egaux_a_la_geometrie(fmt):
    g = CT.geom(fmt, 300)
    svg = hexa.gabarit_svg(g)
    pour = {"coupe": hexa.contour_coupe_toile_mm(g),
            "fond-perdu": hexa.contour_toile_mm(g),
            "zone-sure": hexa.contour_sur_mm(g)}
    for ident, attendu in pour.items():
        pts = _points(_groupe(svg, ident))
        assert len(pts) == len(attendu), ident
        for (a, b), (c, d) in zip(pts, attendu):
            assert abs(a - c) < 0.01 and abs(b - d) < 0.01, ident
    # la coupe est bien le contour_mm de la géométrie, décalé du fond perdu
    ox, oy = g.bleed_off_px[0] * 25.4 / 300, g.bleed_off_px[1] * 25.4 / 300
    for (a, b), (c, d) in zip(_points(_groupe(svg, "coupe")), g.contour_mm):
        assert abs(a - (c + ox)) < 0.01 and abs(b - (d + oy)) < 0.01


def test_svg_reperes_aux_milieux_des_cotes():
    g = CT.geom("hex_f75", 300)
    svg = hexa.gabarit_svg(g)
    milieux = hexa.milieux_cotes_mm(g)
    bruts = re.findall(r'<[^>]*class="milieu"[^>]*>', svg)
    assert len(bruts) == 6
    for brut, (mx, my) in zip(bruts, milieux):
        assert 'data-cx="%.3f"' % mx in brut and 'data-cy="%.3f"' % my in brut


def test_svg_la_zone_sure_demandee_se_dessine():
    # la borne de safe_mm (10 mm) laisse toujours un polygone : l'apothème du plus petit hexagone vaut 25 mm
    g = CT.geom("hex_p50", 300, safe_mm=10.0)
    assert len(_points(_groupe(hexa.gabarit_svg(g), "zone-sure"))) == 6


def test_un_rectangle_est_refuse_par_le_module():
    g = CT.geom("poker_us", 300)
    with pytest.raises(ValueError):
        hexa.gabarit_svg(g)
    with pytest.raises(ValueError):
        hexa.gabarit_png(g)


def test_route_svg_et_png():
    r = _api("/api/cards/gabarit/hex_p75.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert 'id="coupe"' in r.text
    r = _api("/api/cards/gabarit/hex_p75.png?dpi=300&bleed_mm=3")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    g = CT.geom("hex_p75", 300, 3.0)
    assert Image.open(io.BytesIO(r.content)).size == tuple(g.canvas_px)


def test_route_fond_perdu_et_dpi_par_defaut():
    r = _api("/api/cards/gabarit/hex_f50.png")
    g = CT.geom("hex_f50", 300)
    assert r.status_code == 200
    assert Image.open(io.BytesIO(r.content)).size == tuple(g.canvas_px)
    r0 = _api("/api/cards/gabarit/hex_f50.png?bleed_mm=0")
    g0 = CT.geom("hex_f50", 300, 0.0)
    assert Image.open(io.BytesIO(r0.content)).size == tuple(g0.canvas_px)
    assert g0.canvas_px != g.canvas_px


def test_route_refus():
    assert _api("/api/cards/gabarit/poker_us.svg").status_code == 404
    assert _api("/api/cards/gabarit/poker_us.png").status_code == 404
    assert _api("/api/cards/gabarit/inconnu.svg").status_code == 404
    assert _api("/api/cards/gabarit/hex_p75.pdf").status_code == 404
    assert _api("/api/cards/gabarit/hex_p75.svg?dpi=5").status_code == 400
    assert _api("/api/cards/gabarit/hex_p75.svg?dpi=abc").status_code == 422
    assert _api("/api/cards/gabarit/hex_p75.svg?bleed_mm=-1").status_code == 400


# ── l'écran : les boutons « Télécharger le gabarit » ─────────────────────────
CF_JS = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge" / "js"


def test_l_onglet_impression_porte_les_liens_du_gabarit():
    src = (CF_JS / "mod-print.js").read_text(encoding="utf-8")
    assert 'data-role="gabhex"' in src and "hidden>" in src
    assert 'data-role="gabhex-png"' in src and 'data-role="gabhex-svg"' in src
    assert "CF.gabaritUrl(" in src and "function syncGabaritHex(" in src
    assert 'g.forme === "hex"' in src                  # caché pour un rectangle
    assert src.index("syncGabaritHex(g);") > src.index("function sync()")
    for cle in ("gabhex_titre", "gabhex_png", "gabhex_svg", "gabhex_aide"):
        assert 'dzT("cartes.print.%s")' % cle in src, cle


def test_le_dialogue_et_l_onglet_ont_leurs_cles_fr_en():
    import json
    dico = json.loads((CF_JS.parents[1] / "shared" / "i18n" / "cartes.json").read_text(encoding="utf-8"))
    for cle in ("cartes.print.gabhex_titre", "cartes.print.gabhex_png", "cartes.print.gabhex_svg",
                "cartes.print.gabhex_aide", "cartes.depuis.gabarit_titre", "cartes.depuis.gabarit_aide",
                "cartes.depuis.gabarit_png", "cartes.depuis.gabarit_svg"):
        assert dico[cle]["fr"] and dico[cle]["en"] and dico[cle]["fr"] != dico[cle]["en"], cle


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
