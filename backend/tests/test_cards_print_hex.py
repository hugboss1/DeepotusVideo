# -*- coding: utf-8 -*-
"""Card Forge — t421 (cartes hexagonales, 08/11/2026, tâche 7) : la planche en
NID D'ABEILLES et ses fichiers de coupe.

La feuille imprimée et le fichier de coupe doivent tomber AU MÊME ENDROIT, et
chaque verso exactement derrière son recto après retournement : une erreur ici
ne se découvre qu'à la découpe, sur du vrai papier. Ce banc mesure donc tout
sur les SORTIES (sommets relus dans le SVG, dans le DXF par un petit lecteur,
pixels relus sur la planche), jamais sur une promesse du plan.

Valeurs écrites en dur, calculées à la main :
  * hex_p50 sur A4, marge 12, gouttière 6 : zone 186 x 273 mm, pas 56 x
    48,497 -> 5 rangées 3/2/3/2/3 = 13 cases ; grille droite 3 x 4 = 12.
  * hex_f90 sur A3, marge 12, gouttière 6 : zone 273 x 396, pas 83,138 x 96 ->
    3 colonnes 4/3/4 = 11 ; grille droite 2 x 4 = 8.
  * hex_f635 sur Letter, marge 12, gouttière 6 : 6 cases par page.

Run (depuis backend/) : <python embarqué> tests/test_cards_print_hex.py
"""
import asyncio
import io
import json
import math
import os
import pathlib
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                   # noqa: E402
from httpx import ASGITransport, AsyncClient                    # noqa: E402
from PIL import Image, ImageDraw                                # noqa: E402
from pypdf import PdfReader                                     # noqa: E402

from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import core as CC                       # noqa: E402
from app.services.cards import hexa as HX                       # noqa: E402
from app.services.cards import print_hex as PH                  # noqa: E402

TOL = 0.01                       # mm
BLEU = (40, 90, 160)
SVG = "{http://www.w3.org/2000/svg}"


# ═════════════════════ géométrie de banc (indépendante du module) ═══════════

def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _dedans(p, poly):
    """Point dans un polygone convexe (quel que soit le sens)."""
    s = 0
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        c = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if abs(c) < 1e-12:
            continue
        if s == 0:
            s = 1 if c > 0 else -1
        elif (c > 0) != (s > 0):
            return False
    return True


def _dist_point_poly(p, poly):
    if _dedans(p, poly):
        return 0.0
    return min(_seg_dist(p, poly[i], poly[(i + 1) % len(poly)])
               for i in range(len(poly)))


def _dist_polys(P, Q):
    """Distance entre deux polygones convexes disjoints."""
    return min(min(_dist_point_poly(p, Q) for p in P),
               min(_dist_point_poly(q, P) for q in Q))


def _separation(P, Q):
    """Axes séparateurs : > 0 séparés, 0 qui se touchent, < 0 profondeur du
    chevauchement."""
    best = -math.inf
    for poly in (P, Q):
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = b[1] - a[1], a[0] - b[0]
            ln = math.hypot(nx, ny)
            nx, ny = nx / ln, ny / ln
            pp = [x * nx + y * ny for x, y in P]
            qq = [x * nx + y * ny for x, y in Q]
            best = max(best, min(qq) - max(pp), min(pp) - max(qq))
    return best


def _fond_feuille(p, k):
    """Le contour du fond perdu de la case k, repère feuille, recalculé ici
    depuis `hexa.contour_toile_mm` et le décalage coupe -> toile."""
    g = p.geom
    ox = g.bleed_off_px[0] * 25.4 / g.dpi
    oy = g.bleed_off_px[1] * 25.4 / g.dpi
    x, y = p.cases[k]
    return [(u - ox + x, v - oy + y) for u, v in HX.contour_toile_mm(g)]


def _proche(a, b, tol=TOL):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _memes_points(A, B, tol=TOL):
    return len(A) == len(B) and all(any(_proche(a, b, tol) for b in B) for a in A)


# ═════════════════════ 1. le nid ════════════════════════════════════════════

CAS_NID = [("hex_p50", "a4", 13, 12), ("hex_f90", "a3", 11, 8)]


@pytest.mark.parametrize("fmt,sheet,attendu,droite", CAS_NID)
def test_le_nid_decale_tient_la_gouttiere_et_bat_la_grille_droite(fmt, sheet, attendu, droite):
    g = CT.geom(fmt, 300)
    p = PH.plan_hex(g, sheet, 12, 6, 100)
    W, H = g.trim_mm
    sw, sh = CT.SHEETS[sheet]["size_mm"]
    assert p.par_page == attendu
    # la grille droite, recalculée ici
    aw, ah = sw - 24, sh - 24
    assert droite == math.floor((aw + 6) / (W + 6)) * math.floor((ah + 6) / (H + 6))
    assert p.par_page > droite

    # rangées (pointe) ou colonnes (plat) décalées d'une demi-case
    if g.orientation == "pointe":
        lignes = sorted({round(y, 6) for _, y in p.cases})
        debuts = [min(x for x, y in p.cases if round(y, 6) == ly) for ly in lignes]
        demi = (W + 6) / 2
    else:
        lignes = sorted({round(x, 6) for x, _ in p.cases})
        debuts = [min(y for x, y in p.cases if round(x, 6) == lx) for lx in lignes]
        demi = (H + 6) / 2
    assert len(lignes) >= 3
    for a, b in zip(debuts, debuts[1:]):
        assert abs(abs(a - b) - demi) <= TOL, (a, b, demi)

    coupes = [PH.contour_page_mm(p, k) for k in range(p.par_page)]
    fonds = [_fond_feuille(p, k) for k in range(p.par_page)]
    voisines = 0
    for i in range(len(coupes)):
        for j in range(i + 1, len(coupes)):
            ci, cj = p.cases[i], p.cases[j]
            d_centres = math.hypot(ci[0] - cj[0], ci[1] - cj[1])
            d = _dist_polys(coupes[i], coupes[j])
            assert d >= 6 - TOL, (i, j, d)
            if d_centres <= min(W, H) + 6 + 0.5:          # deux voisines
                voisines += 1
                assert abs(d - 6) <= TOL, (i, j, d)
            # jamais deux fonds perdus qui se chevauchent
            assert _separation(fonds[i], fonds[j]) >= -TOL, (i, j)
    assert voisines >= p.par_page          # droites ET diagonales

    for poly in coupes:                    # toutes dans la marge
        for x, y in poly:
            assert 12 - 1e-6 <= x <= sw - 12 + 1e-6
            assert 12 - 1e-6 <= y <= sh - 12 + 1e-6
    r = PH.REPERE_DIAMETRE_MM / 2
    for c in p.reperes_mm:                 # aucune à moins de 3 mm d'un repère
        for poly in coupes:
            assert _dist_point_poly(c, poly) >= r + 3 - 1e-6
        for poly in fonds:                 # ni dans un fond perdu
            assert _dist_point_poly(c, poly) > r
    # l'ensemble est centré
    xs = [x for poly in coupes for x, _ in poly]
    ys = [y for poly in coupes for _, y in poly]
    assert abs((min(xs) + max(xs)) / 2 - sw / 2) <= 1e-6
    assert abs((min(ys) + max(ys)) / 2 - sh / 2) <= 1e-6


def test_une_gouttiere_sous_deux_fonds_perdus_est_refusee():
    g = CT.geom("hex_p50", 300)              # fond perdu natif 3 mm
    with pytest.raises(ValueError) as e:
        PH.plan_hex(g, "a4", 12, 5, 4)
    assert "gouttière" in str(e.value) and "6 mm" in str(e.value)
    assert PH.plan_hex(g, "a4", 12, 6, 4).gouttiere_mm == 6


def test_les_refus_du_plan():
    g = CT.geom("hex_p50", 300)
    with pytest.raises(ValueError):
        PH.plan_hex(g, "card", 12, 6, 1)
    with pytest.raises(ValueError):
        PH.plan_hex(g, "a5", 12, 6, 1)
    with pytest.raises(ValueError):
        PH.plan_hex(CT.geom("poker_eu", 300), "a4", 12, 6, 1)
    with pytest.raises(ValueError) as e:     # la marge ne loge pas les repères
        PH.plan_hex(g, "a4", 8, 6, 1)
    assert "11 mm" in str(e.value)
    with pytest.raises(ValueError):          # aucune case n'entre
        PH.plan_hex(CT.geom("hex_f90", 300), "a4", 55, 6, 1)
    with pytest.raises(ValueError):
        PH.plan_hex(g, "a4", 12, 6, 0)


def test_trois_reperes_sans_aucune_symetrie():
    p = PH.plan_hex(CT.geom("hex_p50", 300), "a4", 12, 6, 1)
    sw, sh = p.size_mm
    R = p.reperes_mm
    assert len(R) == 3
    for t in (lambda x, y: (sw - x, sh - y),     # demi-tour
              lambda x, y: (sw - x, y),          # retourné, grand côté
              lambda x, y: (x, sh - y)):         # retourné, petit côté
        assert not _memes_points([t(x, y) for x, y in R], R, 0.5)
    # le bas-gauche n'est pas à la même distance du bord que le haut-gauche
    assert abs((sh - R[2][1]) - R[0][1]) > 1


# ═════════════════════ 2. recto verso ═══════════════════════════════════════

def _plan_six(n=7, **kw):
    return PH.plan_hex(CT.geom("hex_f635", 300), "letter", 12, 6, n, duplex=True, **kw)


def test_sept_cartes_sur_des_pages_de_six():
    p = _plan_six(7)
    assert p.par_page == 6 and p.pages == 2
    assert PH.cartes_de_page(p, 0) == 6 and PH.cartes_de_page(p, 1) == 1
    sw = p.size_mm[0]
    W = p.geom.trim_mm[0]
    x, y = PH.carte_de(p, 1, 0, "recto")
    assert (x, y) == p.cases[0]
    xv, yv = PH.carte_de(p, 1, 0, "verso")
    assert abs(xv - (sw - x - W)) <= 1e-9 and yv == y
    with pytest.raises(ValueError):
        PH.carte_de(p, 1, 1, "recto")
    with pytest.raises(ValueError):
        PH.carte_de(p, 1, 1, "verso")
    # les images : page 2, UNE carte au recto et UNE au verso, et le verso à
    # la position miroir exacte
    rec = [_carte(p.geom, BLEU) for _ in range(7)]
    ver = [_carte(p.geom, (200, 40, 40)) for _ in range(7)]
    k = p.geom.dpi / 25.4
    for cote, imgs, coul in (("recto", rec, BLEU), ("verso", ver, (200, 40, 40))):
        page = PH.compose_page(p, imgs, 1, cote)
        for j in range(6):
            cx, cy = p.cases[j]
            if cote == "verso":
                cx = sw - cx - W
            cx += W / 2
            cy += p.geom.trim_mm[1] / 2
            px = page.getpixel((int(cx * k), int(cy * k)))
            if j == 0:
                assert px == coul, (cote, j, px)
            else:
                assert px == (255, 255, 255), (cote, j, px)


def test_chaque_sommet_du_verso_est_le_miroir_du_recto():
    for fmt, sheet in (("hex_f635", "letter"), ("hex_p50", "a4"), ("hex_f90", "a3")):
        p = PH.plan_hex(CT.geom(fmt, 300), sheet, 12, 6, 50, duplex=True)
        sw = p.size_mm[0]
        for page in range(p.pages):
            for j in range(PH.cartes_de_page(p, page)):
                rx, ry = PH.carte_de(p, page, j, "recto")
                vx, vy = PH.carte_de(p, page, j, "verso")
                recto = [(rx + u, ry + v) for u, v in p.geom.contour_mm]
                verso = [(vx + u, vy + v) for u, v in p.geom.contour_mm]
                assert recto == PH.contour_page_mm(p, j)
                assert _memes_points([(sw - x, y) for x, y in recto], verso)


# ═════════════════════ 3. les fichiers de coupe ═════════════════════════════

def _lit_svg(txt):
    root = ET.fromstring(txt)
    groupes = {g.get("id"): g for g in root.findall(SVG + "g")}
    polys = [[tuple(float(v) for v in pt.split(","))
              for pt in el.get("points").split()]
             for el in groupes["coupe"].findall(SVG + "polygon")]
    cercles = [(float(c.get("cx")), float(c.get("cy")), float(c.get("r")))
               for c in groupes["reperes"].findall(SVG + "circle")]
    return root, groupes, polys, cercles


def _lit_dxf(txt):
    """Un petit lecteur DXF R12 : paires (code, valeur) -> en-tête, calques,
    polylignes (fermeture, sommets, calque), cercles."""
    lignes = txt.splitlines()
    assert len(lignes) % 2 == 0
    paires = [(int(lignes[i].strip()), lignes[i + 1].strip())
              for i in range(0, len(lignes), 2)]
    entete, calques, polys, cercles = {}, [], [], []
    section, i = None, 0
    while i < len(paires):
        c, v = paires[i]
        if c == 0 and v == "SECTION":
            section = paires[i + 1][1]
            i += 2
            continue
        if section == "HEADER" and c == 9:
            entete[v] = paires[i + 1][1]
        elif section == "TABLES" and c == 0 and v == "LAYER":
            j = i + 1
            while paires[j][0] != 0:
                if paires[j][0] == 2:
                    calques.append(paires[j][1])
                j += 1
        elif section == "ENTITIES" and c == 0 and v in ("POLYLINE", "CIRCLE"):
            j, attrs = i + 1, {}
            while paires[j][0] != 0:
                attrs[paires[j][0]] = paires[j][1]
                j += 1
            if v == "CIRCLE":
                cercles.append((attrs[8], float(attrs[10]), float(attrs[20]),
                                float(attrs[40])))
            else:
                pts = []
                while paires[j] == (0, "VERTEX"):
                    k, va = j + 1, {}
                    while paires[k][0] != 0:
                        va[paires[k][0]] = paires[k][1]
                        k += 1
                    assert va[8] == attrs[8]
                    pts.append((float(va[10]), float(va[20])))
                    j = k
                assert paires[j] == (0, "SEQEND")
                polys.append((attrs[8], int(attrs[70]) & 1, pts))
            i = j
            continue
        i += 1
    assert paires[-1] == (0, "EOF")
    return entete, calques, polys, cercles


def test_svg_et_dxf_disent_les_memes_sommets_que_le_plan():
    p = _plan_six(7, trait=True)
    sw, sh = p.size_mm
    for page in range(p.pages):
        n = PH.cartes_de_page(p, page)
        attendu = [PH.contour_page_mm(p, k) for k in range(n)]
        root, groupes, polys, cercles = _lit_svg(PH.coupe_svg(p, page))
        assert root.get("width") == "215.9mm" and root.get("height") == "279.4mm"
        assert root.get("viewBox") == "0 0 215.9 279.4"
        assert {"coupe", "reperes"} <= set(groupes)
        assert len(polys) == n
        for a, b in zip(polys, attendu):
            assert len(a) == 6 and all(_proche(u, v) for u, v in zip(a, b))
        assert [(x, y) for x, y, _ in cercles] == pytest.approx(p.reperes_mm, abs=TOL)
        assert all(r == pytest.approx(2.5) for _, _, r in cercles)

        entete, calques, dpolys, dcercles = _lit_dxf(PH.coupe_dxf(p, page))
        assert entete["$INSUNITS"] == "4" and entete["$ACADVER"] == "AC1009"
        assert {"COUPE", "REPERES"} <= set(calques)
        assert len(dpolys) == n
        for (calque, ferme, pts), b in zip(dpolys, attendu):
            assert calque == "COUPE" and ferme == 1 and len(pts) == 6
            # Y inversé : y DXF = hauteur - y
            assert all(_proche((x, sh - y), v) for (x, y), v in zip(pts, b))
        assert len(dcercles) == 3
        for (calque, x, y, r), c in zip(dcercles, p.reperes_mm):
            assert calque == "REPERES" and r == pytest.approx(2.5)
            assert _proche((x, sh - y), c)


def test_le_zip_livre_un_svg_et_un_dxf_par_page():
    p = _plan_six(13)
    assert p.pages == 3
    z = zipfile.ZipFile(io.BytesIO(PH.coupe_zip(p)))
    assert z.namelist() == ["page-01.svg", "page-01.dxf", "page-02.svg",
                            "page-02.dxf", "page-03.svg", "page-03.dxf"]
    _r, _g, polys, cercles = _lit_svg(z.read("page-03.svg").decode("utf-8"))
    assert len(polys) == 1
    _e, _c, dpolys, dcercles = _lit_dxf(z.read("page-03.dxf").decode("ascii"))
    assert len(dpolys) == 1
    # les repères sont identiques sur toutes les pages, SVG et DXF
    for nom in z.namelist():
        txt = z.read(nom).decode("utf-8")
        if nom.endswith(".svg"):
            pts = [(x, y) for x, y, _ in _lit_svg(txt)[3]]
        else:
            pts = [(x, p.size_mm[1] - y) for _, x, y, _ in _lit_dxf(txt)[3]]
        assert _memes_points(pts, p.reperes_mm)


# ═════════════════════ 4. la planche imprimée ═══════════════════════════════

def _carte(g, rgb, repere=False, alpha=False):
    """Une toile pleine ; `repere` : un carré rouge au centre de la toile."""
    im = Image.new("RGBA" if alpha else "RGB", tuple(g.canvas_px),
                   rgb + ((255,) if alpha else ()))
    if repere:
        cx, cy = g.canvas_px[0] / 2, g.canvas_px[1] / 2
        ImageDraw.Draw(im).rectangle((cx - 3, cy - 3, cx + 3, cy + 3), fill=(255, 0, 0))
    return im


def _centre_rouge(im):
    w, h = im.size
    px = im.load()
    xs = ys = n = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > 200 and g < 60 and b < 60:
                xs += x + 0.5
                ys += y + 0.5
                n += 1
    assert n > 0
    return xs / n, ys / n


def test_compose_page_pose_la_carte_au_centre_de_sa_case():
    for fmt in ("hex_p50", "hex_f635"):
        g = CT.geom(fmt, 150)
        p = PH.plan_hex(g, "a4", 12, 6, 1, trait=False)
        page = PH.compose_page(p, [_carte(g, BLEU, repere=True)], 0, "recto")
        assert page.size == CT.sheet_px("a4", 150) == p.sheet_px
        k = 150 / 25.4
        x, y = p.cases[0]
        W, H = g.trim_mm
        cx, cy = _centre_rouge(page)
        assert abs(cx - (x + W / 2) * k) <= 1.0 and abs(cy - (y + H / 2) * k) <= 1.0
        # l'angle de la toile, hors du fond perdu, reste blanc
        ox = g.bleed_off_px[0] / k
        coin = ((x - ox) * k + 2, (y - g.bleed_off_px[1] / k) * k + 2)
        assert page.getpixel((int(coin[0]), int(coin[1]))) == (255, 255, 255)
        # les repères sont imprimés
        for rx, ry in p.reperes_mm:
            assert page.getpixel((int(rx * k), int(ry * k))) == (0, 0, 0)
        # le masque fait autorité même sur une image transparente
        tr = PH.compose_page(p, [_carte(g, BLEU, alpha=True)], 0, "recto")
        assert tr.getpixel((int(coin[0]), int(coin[1]))) == (255, 255, 255)


def test_le_trait_de_coupe_seulement_s_il_est_demande():
    g = CT.geom("hex_p50", 300)
    k = 300 / 25.4
    imgs = [_carte(g, BLEU)]
    for trait in (False, True):
        p = PH.plan_hex(g, "a4", 12, 6, 1, trait=trait, duplex=True)
        c = PH.contour_page_mm(p, 0)
        mx, my = (c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2   # côté droit
        rec = PH.compose_page(p, imgs, 0, "recto")
        v = rec.getpixel((int(mx * k), int(my * k)))
        assert (v != BLEU) == trait, v
        # pas de trait au verso : on coupe recto dessus
        ver = PH.compose_page(p, imgs, 0, "verso")
        sw = p.size_mm[0]
        assert ver.getpixel((int((sw - mx) * k), int(my * k))) == BLEU


def test_les_reperes_du_verso_sont_en_miroir_et_un_verso_absent_reste_blanc():
    g = CT.geom("hex_p50", 150)
    k = 150 / 25.4
    p = PH.plan_hex(g, "a4", 12, 6, 2, duplex=True)
    ver = PH.compose_page(p, [None, _carte(g, BLEU)], 0, "verso")
    sw = p.size_mm[0]
    for rx, ry in p.reperes_mm:
        assert ver.getpixel((int((sw - rx) * k), int(ry * k))) == (0, 0, 0)
    # le bas-gauche du recto passe à droite au verso : sa place reste blanche
    bx, by = p.reperes_mm[2]
    assert ver.getpixel((int(bx * k), int(by * k))) == (255, 255, 255)
    W, H = g.trim_mm
    for j, attendu in ((0, (255, 255, 255)), (1, BLEU)):
        x, y = PH.carte_de(p, 0, j, "verso")
        assert ver.getpixel((int((x + W / 2) * k), int((y + H / 2) * k))) == attendu
    # une liste courte aussi
    court = PH.compose_page(p, [_carte(g, BLEU)], 0, "verso")
    x, y = PH.carte_de(p, 0, 1, "verso")
    assert court.getpixel((int((x + W / 2) * k), int((y + H / 2) * k))) == (255, 255, 255)
    with pytest.raises(ValueError):
        PH.compose_page(p, [Image.new("RGB", (10, 10))], 0, "recto")


def test_le_pdf_compte_ses_pages_au_format_de_la_feuille():
    g = CT.geom("hex_f635", 150)
    for duplex, attendu in ((True, 4), (False, 2)):
        p = PH.plan_hex(g, "letter", 12, 6, 7, duplex=duplex)
        data = PH.pdf_planche(p, [_carte(g, BLEU)] * 7,
                              [_carte(g, (200, 40, 40))] * 7)
        pdf = PdfReader(io.BytesIO(data))
        assert len(pdf.pages) == attendu == p.pages * (2 if duplex else 1)
        for pg in pdf.pages:
            w, h = float(pg.mediabox.width), float(pg.mediabox.height)
            assert abs(w - 215.9 / 25.4 * 72) <= 0.5
            assert abs(h - 279.4 / 25.4 * 72) <= 0.5


# ═════════════════════ 5. les routes ════════════════════════════════════════

def _api(method: str, path: str, **kw):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            return await c.request(method, path, timeout=300.0, **kw)
    return asyncio.run(go())


def _png(im) -> bytes:
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def test_les_routes_hex():
    did = CC.create_deck("Hex planche", {"fmt": "hex_p50", "dpi": 150})["id"]
    base = f"/api/cards/{did}/print/hex"
    r = _api("POST", base + "/plan", json={"sheet": "a4", "marge_mm": 12,
                                           "gouttiere_mm": 6, "n_cards": 14,
                                           "trait": True, "duplex": True})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["par_page"] == 13 and d["pages"] == 2 and d["out_pages"] == 4
    assert len(d["cases"]) == 13 and len(d["reperes_mm"]) == 3
    assert d["geom"]["fmt"] == "hex_p50"

    r = _api("POST", base + "/plan", json={"gouttiere_mm": 5})
    assert r.status_code == 400 and "gouttière" in r.json()["detail"]
    r = _api("POST", base + "/plan", json={"sheet": "card"})
    assert r.status_code == 400

    r = _api("POST", base + "/coupe", json={"n_cards": 14, "gouttiere_mm": 6})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert zipfile.ZipFile(io.BytesIO(r.content)).namelist() == [
        "page-01.svg", "page-01.dxf", "page-02.svg", "page-02.dxf"]

    g = CC.geom_of(CC.read_deck(did))
    img = _png(_carte(g, BLEU))
    files = [("fronts", (f"f{i}.png", img, "image/png")) for i in range(3)]
    files += [("backs", ("b0.png", img, "image/png")),
              ("backs", ("b1.png", b"", "image/png"))]       # carte 2 : pas de verso
    r = _api("POST", base + "/pdf", files=files,
             data={"spec": json.dumps({"duplex": True, "trait": True})})
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"] == "application/pdf"
    assert len(PdfReader(io.BytesIO(r.content)).pages) == 2
    assert r.headers["x-cf-pages"] == "2"

    r = _api("POST", base + "/pdf", files=[("fronts", ("f.png", _png(Image.new(
        "RGB", (10, 10))), "image/png"))], data={"spec": "{}"})
    assert r.status_code == 400
    r = _api("POST", base + "/pdf", data={"spec": "{}"})
    assert r.status_code == 400

    # un jeu rectangulaire est refusé par les trois routes
    rid = CC.create_deck("Rect", {"fmt": "poker_eu", "dpi": 150})["id"]
    rb = f"/api/cards/{rid}/print/hex"
    for path in ("/plan", "/coupe"):
        r = _api("POST", rb + path, json={})
        assert r.status_code == 400 and "hexagon" in r.json()["detail"]
    r = _api("POST", rb + "/pdf", files=files, data={"spec": "{}"})
    assert r.status_code == 400 and "hexagon" in r.json()["detail"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
