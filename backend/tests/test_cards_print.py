# -*- coding: utf-8 -*-
"""Card Forge — P7 « Export impression ». Les seuils, au pixel et au point.

Chaque nombre attendu ci-dessous est ÉCRIT EN DUR, relevé sur nanDECK 1.29
(la barre) ou sur la spec, et JAMAIS recalculé par la formule qu'il est censé
vérifier — un test qui rejoue l'implémentation ne prouve rien.

Ce qui est verrouillé, seuil par seuil :

  1. `poker_us` -> carte 825x1125 px, `poker_eu` -> 815x1110 px. 0 pixel.
  2. Planche A4 -> 2480x3508 px à 300 DPI, 4961x7016 à 600. 0 pixel.
  3. A4, marges 10 mm, gouttière 4 mm, poker -> 2 colonnes x 3 lignes = 6.
  4. Gouttière mesurée DANS LE PDF = 11,34 pt (parité nanDECK). C'est le
     seuil qui interdit le compositing raster : 4 mm arrondis à 47 px
     donneraient 11,28 pt.
  5. PNG exporté : chunk `pHYs` = 11811 px/m (300 DPI).
  6. PDF : `/MediaBox [0 0 595.2 841.92]` ET `/TrimBox` + `/BleedBox` sur
     CHAQUE page — ce que le PDF de nanDECK n'a pas.
  7. Traits de coupe VECTORIELS (`m`/`l`/`S` + `RG`), pas des pixels.
  8. Duplex : la carte 1 du recto fait face à la carte en position MIROIR du
     verso.
  9. Contrôle avant vol : deux règles, avec le nom de la carte et le chiffre.
 10. 60 cartes + PDF A4 en moins de 30 s.
 11. Un bitmap qui n'est pas à `geom.canvas_px` est REFUSÉ (400) : c'est le
     verrou mécanique de « un seul moteur de rendu ».

Run : .\\scripts\\run-tests.ps1 -Filter cards
"""
import asyncio
import io
import json
import os
import pathlib
import re
import struct
import sys
import tempfile
import time
import zlib

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
from app.services.cards import print as PR                      # noqa: E402


# ═════════════════════ les seuils, écrits en dur ════════════════════════════

TOILE = {"poker_us": (825, 1125), "poker_eu": (815, 1110),
         "bridge_us": (750, 1125), "tarot_us": (900, 1500),
         "micro": (450, 600), "jumbo": (1125, 1725)}
ROGNE = {"poker_us": (750, 1050), "poker_eu": (744, 1039)}
PLANCHE_300 = {"a4": (2480, 3508), "letter": (2550, 3300), "a3": (3508, 4961)}
PLANCHE_600 = {"a4": (4961, 7016), "letter": (5100, 6600), "a3": (7016, 9921)}
MEDIABOX_A4_300 = [0.0, 0.0, 595.2, 841.92]
GOUTTIERE_4MM_PT = 11.34          # nanDECK : GAP = 0.4 cm
PHYS_300DPI = 11811               # px/m


def base(**kw):
    d = {"fmt": "poker_eu", "dpi": 300, "sheet": "a4", "orient": "portrait",
         "margin_mm": 10, "gutter_mm": 4, "marks": "crop"}
    d.update(kw)
    return d


def carte(fmt="poker_eu", dpi=300, bleed=None, tag="", mode="RGB"):
    """Un bitmap de carte à la taille EXACTE que le backend exige."""
    g = CT.geom(fmt, dpi, bleed)
    im = Image.new(mode, tuple(g.canvas_px), (247, 243, 235)
                   if mode == "RGB" else (247, 243, 235, 255))
    d = ImageDraw.Draw(im)
    bx, by = g.bleed_off_px
    d.rectangle([bx, by, bx + g.trim_px[0] - 1, by + g.trim_px[1] - 1],
                outline=(20, 20, 20), width=3)
    if tag:
        d.text((bx + 20, by + 20), tag, fill=(0, 0, 0))
    return im


def png_bytes(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def pdf_ops(data: bytes, page: int = 0) -> str:
    """Le flux de contenu d'une page, décodé. `pypdf` sait le rendre ;
    on ne fouille pas les octets bruts."""
    r = PdfReader(io.BytesIO(data))
    return r.pages[page].get_contents().get_data().decode("latin-1")


def bloc(ops: str, tag: str) -> str:
    """Le contenu BALISÉ `/<tag> BMC ... EMC` du flux. La coupe et le
    cartouche sont deux tracés vectoriels dans le même flux : sans balise, un
    trait de lettre passerait pour un trait de coupe — c'est exactement ce
    qui arrivait avant, et ça fausse toute mesure de gouttière."""
    i = ops.find("/" + tag + " BMC")
    if i < 0:
        return ""
    j = ops.find("EMC", i)
    return ops[i:j if j > 0 else len(ops)]


# ═══════════════════════ 1-2. les pixels, tolérance zéro ════════════════════

def test_la_carte_sort_aux_pixels_de_nandeck():
    """`poker_us` -> 825x1125, `poker_eu` -> 815x1110. Zéro tolérance.

    Le plan d'imposition n'a pas le droit de recalculer une dimension de
    carte : il reçoit `CardGeom` et la sert telle quelle."""
    for fmt, attendu in TOILE.items():
        p = PR.build_plan(base(fmt=fmt), 1)
        assert tuple(p.geom.canvas_px) == attendu, fmt
    for fmt, attendu in ROGNE.items():
        p = PR.build_plan(base(fmt=fmt), 1)
        assert tuple(p.cell_px) == attendu, fmt
        assert tuple(p.geom.trim_px) == attendu, fmt


def test_la_planche_sort_aux_pixels_de_nandeck():
    """A4 = 2480x3508 à 300 DPI, 4961x7016 à 600. Zéro tolérance."""
    for sid, attendu in PLANCHE_300.items():
        p = PR.build_plan(base(sheet=sid, margin_mm=5), 1)
        assert tuple(p.sheet_px) == attendu, sid
    for sid, attendu in PLANCHE_600.items():
        p = PR.build_plan(base(sheet=sid, dpi=600, margin_mm=5), 1)
        assert tuple(p.sheet_px) == attendu, f"{sid}@600"


def test_le_paysage_echange_les_deux_dimensions_et_rien_d_autre():
    p = PR.build_plan(base(orient="paysage"), 1)
    assert tuple(p.sheet_px) == (3508, 2480)


# ═══════════════════════ 3. la grille ═══════════════════════════════════════

def test_a4_marges_10_gouttiere_4_poker_donne_2x3():
    """Le seuil le plus visible de la pièce : 2 colonnes x 3 lignes = 6
    cartes par page — pour les DEUX poker, métrique et impérial."""
    for fmt in ("poker_eu", "poker_us"):
        p = PR.build_plan(base(fmt=fmt), 6)
        assert (p.cols, p.rows, p.per_page) == (2, 3, 6), fmt
        assert p.pages == 1, fmt
    p = PR.build_plan(base(fmt="poker_eu"), 7)
    assert p.pages == 2 and p.out_pages == 2
    p = PR.build_plan(base(fmt="poker_eu", duplex=True), 7)
    assert p.out_pages == 4, "recto-verso = deux fois plus de pages écrites"


def test_le_centrage_est_un_vrai_centrage():
    p = PR.build_plan(base(), 6)
    assert abs(p.origin_px[0] - (p.sheet_px[0] - p.content_px[0]) / 2) < 1e-9
    assert abs(p.origin_px[1] - (p.sheet_px[1] - p.content_px[1]) / 2) < 1e-9
    q = PR.build_plan(base(center=False), 6)
    assert abs(q.origin_px[0] - q.margin_px) < 1e-9


def test_une_carte_trop_grande_refuse_le_plan_en_le_disant():
    """Jumbo (139,7 mm de haut) sur une A4 en paysage (210 mm) avec 40 mm de
    marge de chaque côté : il reste 130 mm, il en faut 139,7. Zéro ligne —
    et une phrase qui dit les deux chiffres, pas un plan à zéro carte."""
    with pytest.raises(ValueError) as e:
        PR.build_plan(base(fmt="jumbo", sheet="a4", orient="paysage",
                           margin_mm=40), 1)
    assert "ne tient pas" in str(e.value)
    assert "1050x1650" in str(e.value)


# ═══════════════════════ 4. la gouttière, DANS le PDF ═══════════════════════

def test_la_gouttiere_mesure_11_34_pt_dans_le_pdf():
    """PARITÉ nanDECK, et le seuil qui interdit le compositing raster.

    4 mm à 300 DPI = 47,244 px. Un bitmap composé les figerait à 47 px, soit
    11,28 pt. Ici chaque carte est un XObject posé à une coordonnée
    FRACTIONNAIRE : la mesure se lit sur les traits de coupe du PDF, qui
    tombent exactement sur les arêtes de rogne."""
    p = PR.build_plan(base(), 6)
    assert round(PR.px2pt(p.gutter_px, p.dpi), 2) == GOUTTIERE_4MM_PT

    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    ops = bloc(pdf_ops(data), "CFmarks")
    xs = sorted({round(float(m.group(1)), 4)
                 for m in re.finditer(r"([\d.]+) ([\d.]+) m \1 ([\d.]+) l S", ops)})
    ecarts = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert GOUTTIERE_4MM_PT in ecarts, (
        f"gouttière absente des traits verticaux {xs} (écarts {ecarts})")


def test_la_gouttiere_du_pdf_n_est_pas_arrondie_au_pixel():
    """Le contre-exemple, explicite : 47 px valent 11,28 pt et NON 11,34."""
    p = PR.build_plan(base(), 6)
    assert round(PR.px2pt(round(p.gutter_px), p.dpi), 2) == 11.28
    assert round(PR.px2pt(p.gutter_px, p.dpi), 4) == 11.3386


# ═══════════════════════ 5. le PNG et sa densité ════════════════════════════

def phys_of(png: bytes):
    i = png.find(b"pHYs")
    if i < 0:
        return None
    x, y, unit = struct.unpack(">IIB", png[i + 4:i + 13])
    return x, y, unit


def test_png_8_bits_porte_phys_11811():
    out, mime, ext = PR.encode_image(carte(), "png", 8, 300, True, 95)
    assert mime == "image/png" and ext == "png"
    assert phys_of(out) == (PHYS_300DPI, PHYS_300DPI, 1)
    assert Image.open(io.BytesIO(out)).size == (815, 1110)


def test_png_16_bits_est_vraiment_en_16_bits_avec_alpha():
    """Pillow ne sait pas encoder du RGBA 16 bits : le writer maison est
    vérifié sur l'en-tête ET sur la relecture."""
    out, _m, _e = PR.encode_image(carte(mode="RGBA"), "png", 16, 300, True, 95)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"
    prof, ctype = out[24], out[25]          # IHDR : profondeur, type couleur
    assert prof == 16, "profondeur de bit"
    assert ctype == 6, "RGBA"
    assert phys_of(out) == (PHYS_300DPI, PHYS_300DPI, 1)
    im = Image.open(io.BytesIO(out))
    im.load()
    assert im.size == (815, 1110) and im.mode == "RGBA"
    # sans alpha demandé, on retombe sur du RGB 16 bits (type 2)
    out2, _m, _e = PR.encode_image(carte(mode="RGBA"), "png", 16, 300, False, 95)
    assert out2[24] == 16 and out2[25] == 2


def test_le_phys_suit_la_definition():
    for dpi, ppm in ((150, 5906), (300, 11811), (600, 23622)):
        assert PR.phys_ppm(dpi) == ppm
    out, _m, _e = PR.encode_image(carte(dpi=600), "png", 8, 600, True, 95)
    assert phys_of(out) == (23622, 23622, 1)


def test_jpeg_q95_porte_sa_densite_et_pas_d_alpha():
    out, mime, ext = PR.encode_image(carte(mode="RGBA"), "jpeg", 8, 300, True, 95)
    assert (mime, ext) == ("image/jpeg", "jpg")
    im = Image.open(io.BytesIO(out))
    assert im.mode == "RGB" and im.size == (815, 1110)
    assert im.info.get("dpi") == (300, 300)


# ═══════════════════════ 6-7. le PDF : boîtes et vecteurs ═══════════════════

def test_mediabox_trimbox_et_bleedbox_sur_chaque_page():
    """LE duel : un imprimeur ouvre les deux PDF et voit en 2 secondes que
    celui de nanDECK n'annonce que /MediaBox."""
    p = PR.build_plan(base(), 8)
    data = PR.build_pdf(p, {i: carte() for i in range(8)}, {}, "T")
    r = PdfReader(io.BytesIO(data))
    assert len(r.pages) == 2
    for i, page in enumerate(r.pages):
        media = [round(float(v), 2) for v in page.mediabox]
        assert media == MEDIABOX_A4_300, f"page {i}: {media}"
        assert "/TrimBox" in page, f"page {i} sans TrimBox"
        assert "/BleedBox" in page, f"page {i} sans BleedBox"
        trim = [float(v) for v in page.trimbox]
        bleed = [float(v) for v in page.bleedbox]
        # la boîte de rogne est STRICTEMENT dedans, et le fond perdu la
        # déborde de tous les côtés : deux boîtes distinctes, pas un alias.
        assert bleed[0] < trim[0] and bleed[1] < trim[1]
        assert bleed[2] > trim[2] and bleed[3] > trim[3]
        assert trim[0] > 0 and trim[2] < media[2]


def test_les_traits_de_coupe_sont_vectoriels():
    """`m`/`l`/`S` avec une couleur de trait, comme nanDECK — pas des pixels
    cuits dans l'image. On le prouve DEUX fois : les opérateurs sont là, et
    la page ne contient que les images des cartes."""
    p = PR.build_plan(base(marks="crop"), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    ops = pdf_ops(data)
    assert re.search(r"[\d.]+ [\d.]+ [\d.]+ RG", ops), "aucune couleur de trait"
    assert len(re.findall(r" m [\d.]+ [\d.]+ l S", ops)) >= 20
    r = PdfReader(io.BytesIO(data))
    xo = r.pages[0]["/Resources"]["/XObject"]
    assert len(xo) == 6, "une image par carte, et rien d'autre"
    for v in xo.values():
        assert v.get_object()["/Height"] in (1110, 1075, 1039 + 71, 1039 + 47,
                                             1039 + 35 + 24, 1039 + 24 + 35)


def test_aucun_repere_quand_on_n_en_veut_pas():
    p = PR.build_plan(base(marks="none"), 6)
    assert PR.mark_segments(p) == []
    ops = pdf_ops(PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T"))
    assert bloc(ops, "CFmarks") == "", "un bloc de coupe alors qu'on n'en veut pas"


def test_le_double_trait_de_coupe_borde_la_gouttiere():
    """Ce que nanDECK ne fait pas : DEUX traits par gouttière, un par arête
    de rogne, donc la coupe garde le fond perdu du voisin."""
    p = PR.build_plan(base(), 6)
    segs = PR.mark_segments(p)
    x_droite = PR.cell_rect(p, 0, 0)[0] + p.cell_px[0]
    x_gauche = PR.cell_rect(p, 0, 1)[0]
    assert abs((x_gauche - x_droite) - p.gutter_px) < 1e-6
    verticaux = {round(s[0], 3) for s in segs if abs(s[0] - s[2]) < 1e-6}
    assert round(x_droite, 3) in verticaux
    assert round(x_gauche, 3) in verticaux


def test_une_carte_par_page_donne_des_boites_exactes():
    """Le format que réclament les imprimeurs de cartes : une page = une
    carte, TrimBox = la coupe au point près, BleedBox = la toile."""
    p = PR.build_plan(base(sheet="card", marks="none"), 3)
    assert tuple(p.sheet_px) == (815, 1110) and p.per_page == 1
    data = PR.build_pdf(p, {i: carte() for i in range(3)}, {}, "T")
    r = PdfReader(io.BytesIO(data))
    assert len(r.pages) == 3
    page = r.pages[0]
    media = [round(float(v), 2) for v in page.mediabox]
    assert media == [0.0, 0.0, round(815 * 72 / 300, 2), round(1110 * 72 / 300, 2)]
    trim = [round(float(v), 2) for v in page.trimbox]
    assert trim == [round(35.5 * 72 / 300, 2), round(35.5 * 72 / 300, 2),
                    round((35.5 + 744) * 72 / 300, 2),
                    round((35.5 + 1039) * 72 / 300, 2)]
    assert [round(float(v), 2) for v in page.bleedbox] == media


def test_le_pdf_sans_perte_est_bien_sans_perte():
    """« Sans perte » se prouve sur les PIXELS relus dans le PDF, pas sur le
    nom du filtre : on redécode l'image du fichier et on la compare octet
    pour octet à la carte rendue par le navigateur.

    Le PDF porte la TOILE ENTIÈRE, détourée par un chemin de rognage — pas un
    découpage. C'est ce qui rend la comparaison possible à l'octet près."""
    src = carte()
    p = PR.build_plan(base(lossless=True), 2)
    data = PR.build_pdf(p, {0: src, 1: src}, {}, "T")
    r = PdfReader(io.BytesIO(data))
    assert all(str(v.get_object()["/Filter"]) == "/FlateDecode"
               for v in r.pages[0]["/Resources"]["/XObject"].values())
    relu = r.pages[0].images[0].image.convert("RGB")
    assert relu.size == (815, 1110)
    assert relu.tobytes() == src.convert("RGB").tobytes(), \
        "le PDF sans perte a perdu"

    q = PR.build_plan(base(lossless=False), 2)
    data2 = PR.build_pdf(q, {0: src, 1: src}, {}, "T")
    r2 = PdfReader(io.BytesIO(data2))
    assert all(str(v.get_object()["/Filter"]) == "/DCTDecode"
               for v in r2.pages[0]["/Resources"]["/XObject"].values())


# ═══════════════════════ 8. recto-verso ═════════════════════════════════════

def test_duplex_le_verso_est_le_miroir_du_recto():
    """Retournement bord long : la carte posée en (ligne r, colonne c) au
    recto doit se retrouver en (r, cols-1-c) au verso. C'est l'erreur la plus
    courante des scripts d'imposition, et elle ne se voit qu'une fois la
    planche imprimée des deux côtés."""
    p = PR.build_plan(base(duplex=True), 6)
    recto = {(r, c): i for r, c, i in PR.cells_for_page(p, 0, "front")}
    verso = {(r, c): i for r, c, i in PR.cells_for_page(p, 0, "back")}
    assert recto[(0, 0)] == 0 and verso[(0, 1)] == 0, "carte 1 : F(0,0) <-> B(0,1)"
    for (r, c), idx in recto.items():
        assert verso[(r, p.cols - 1 - c)] == idx, f"{(r, c)}"
    # « F1 <-> B7 » : la 7e case du flux duplex est le VERSO DE LA CARTE 1 —
    # posé en (0,1), la position miroir, et surtout PAS en (0,0), qui porte
    # le verso de la carte 2.
    dos = PR.cells_for_page(p, 0, "back")
    assert dos[0][2] == 0 and (dos[0][0], dos[0][1]) == (0, 1)
    assert verso[(0, 0)] == 1
    flux = ([i for _r, _c, i in PR.cells_for_page(p, 0, "front")]
            + [i for _r, _c, i in dos])
    assert len(flux) == 12 and flux[6] == 0


def test_duplex_bord_court():
    p = PR.build_plan(base(duplex=True, flip="short"), 6)
    recto = {(r, c): i for r, c, i in PR.cells_for_page(p, 0, "front")}
    verso = {(r, c): i for r, c, i in PR.cells_for_page(p, 0, "back")}
    for (r, c), idx in recto.items():
        assert verso[(p.rows - 1 - r, c)] == idx


def test_duplex_ordre_des_pages():
    p = PR.build_plan(base(duplex=True), 7)
    data = PR.build_pdf(p, {i: carte() for i in range(7)},
                        {i: carte(tag="V") for i in range(7)}, "T")
    assert len(PdfReader(io.BytesIO(data)).pages) == 4   # 2 pages x recto/verso
    q = PR.build_plan(base(duplex=True, duplex_order="grouped"), 7)
    data2 = PR.build_pdf(q, {i: carte() for i in range(7)},
                         {i: carte(tag="V") for i in range(7)}, "T")
    assert len(PdfReader(io.BytesIO(data2)).pages) == 4


# ═══════════════════════ fond perdu jamais superposé ════════════════════════

def test_le_fond_perdu_est_rogne_a_la_moitie_de_la_gouttiere():
    """3 mm de fond perdu de chaque côté ne tiennent pas dans 4 mm de
    gouttière. On rogne à la moitié — et JAMAIS on ne superpose : la carte de
    droite mangerait la coupe de celle de gauche."""
    p = PR.build_plan(base(), 6)
    kl, kt, kr, kb = PR.keep_bleed(p, 1, 0)          # case intérieure à droite
    assert abs(kr - p.gutter_px / 2) < 1e-9
    assert abs(kl - p.geom.bleed_off_px[0]) < 1e-9   # bord de planche : entier
    droite = PR.cell_rect(p, 1, 0)[0] + p.cell_px[0] + kr
    gauche = PR.cell_rect(p, 1, 1)[0] - PR.keep_bleed(p, 1, 1)[0]
    assert droite <= gauche + 1e-9, "les fonds perdus se recouvrent"
    kinds = [w["kind"] for w in p.warnings]
    assert "gouttiere_courte" in kinds
    # gouttière à 2 x le fond perdu : plus d'avertissement, fond perdu entier
    # au 1/15e de pixel près. Ce résidu n'est pas une erreur : 6 mm valent
    # 70,866 px et la TOILE, elle, est arrondie à 815 px, ce qui donne
    # 35,5 px de fond perdu rendu contre 35,433 px de demi-gouttière. La
    # règle « la toile fait autorité » se paie ici, et elle se paie en
    # 0,07 pixel.
    q = PR.build_plan(base(gutter_mm=6), 6)
    assert "gouttiere_courte" not in [w["kind"] for w in q.warnings]
    perdu = q.geom.bleed_off_px[0] - PR.keep_bleed(q, 1, 0)[2]
    assert 0 <= perdu < 0.1, perdu


def test_le_decoupage_ne_deplace_jamais_la_rogne():
    """La découpe est entière, le placement ne l'est pas : c'est ce couple
    qui garde la coupe exactement où le plan la met."""
    p = PR.build_plan(base(), 6)
    im = carte()
    for r in range(p.rows):
        for c in range(p.cols):
            piece, dx, dy = PR.crop_for_cell(im, p, r, c)
            assert piece.size[0] - dx >= p.cell_px[0] - 1e-9
            assert piece.size[1] - dy >= p.cell_px[1] - 1e-9
            assert 0 <= dx <= p.geom.bleed_off_px[0] + 1e-9
            assert 0 <= dy <= p.geom.bleed_off_px[1] + 1e-9


# ═══════════════════════ 9. contrôle avant vol ══════════════════════════════

def test_controle_avant_vol_texte_hors_zone_sure():
    """Règle 1 : un slot qui sort de la zone sûre, avec le nom de la carte et
    le dépassement en pixels. Le mot « safe » n'existe pas dans les 202 pages
    du manuel de nanDECK."""
    out = PR.preflight({
        "fmt": "poker_eu", "dpi": 300,
        "slots": [{"id": "title", "label": "Titre", "box": [1, 1, 40, 10]},
                  {"id": "rules", "label": "Règles", "box": [5, 40, 53, 30]}],
        "cards": [{"i": 0, "name": "Octopode", "fields": {"title": "Octopode"},
                   "art": {"w": 2000, "h": 2800}}],
    })
    lignes = [r for r in out["rows"] if r["kind"] == "texte_hors_zone_sure"]
    assert len(lignes) == 1, out["rows"]
    assert lignes[0]["card"] == "Octopode"
    assert lignes[0]["value"] == 23.7          # 35,5 px de zone sûre - 11,8
    assert "px" in lignes[0]["message"] and "mm" in lignes[0]["message"]
    assert out["errors"] >= 1 and out["ok"] is False
    # le slot « rules » (5 mm, largeur 53) tient dans la zone sûre : silence.
    assert not [r for r in out["rows"] if r.get("slot") == "rules"]


def test_controle_avant_vol_image_sous_300_dpi():
    """Règle 2 : le DPI EFFECTIF de l'illustration à la taille posée, avec le
    chiffre. 650x1024 sur une toile de 815x1110 -> 239 DPI."""
    out = PR.preflight({
        "fmt": "poker_eu", "dpi": 300, "slots": [],
        "cards": [{"i": 0, "name": "Octopode", "art": {"w": 650, "h": 1024}},
                  {"i": 1, "name": "Oracle", "art": {"w": 2000, "h": 2800}},
                  {"i": 2, "name": "Abysse"}],
    })
    faibles = [r for r in out["rows"] if r["kind"] == "image_sous_definie"]
    assert len(faibles) == 1
    assert faibles[0]["card"] == "Octopode"
    assert faibles[0]["value"] == 239.3
    assert faibles[0]["limit"] == 300
    assert "239 DPI" in faibles[0]["message"]
    manquantes = [r for r in out["rows"] if r["kind"] == "illustration_absente"]
    assert len(manquantes) == 1 and manquantes[0]["card"] == "Abysse"


def test_le_controle_prefere_la_mesure_de_la_piece_01():
    """`doc.face.eff_dpi` est le DPI de l'illustration TELLE QU'ELLE EST
    POSÉE (recadrage, échelle, rotation compris) : la pièce 01 le mesure,
    nous ne connaissons que la taille du fichier. Quand elle a mesuré, c'est
    elle qui a raison — et -1 veut dire vectoriel, donc jamais sous-défini."""
    out = PR.preflight({
        "fmt": "poker_eu", "dpi": 300, "slots": [], "file_checks": False,
        "cards": [
            {"i": 0, "name": "Vectorielle", "eff_dpi": -1, "art": {"w": 8, "h": 8}},
            {"i": 1, "name": "Trop petite", "eff_dpi": 181.4},
            {"i": 2, "name": "Nette", "eff_dpi": 420},
            {"i": 3, "name": "Posée ailleurs", "has_art": True},
        ],
    })
    assert [r["card"] for r in out["rows"]] == ["Trop petite"]
    assert out["rows"][0]["value"] == 181.4
    assert "181 DPI" in out["rows"][0]["message"]
    assert "pièce 01" in out["rows"][0]["message"]


def test_controle_avant_vol_ne_crie_pas_pour_rien():
    out = PR.preflight({
        "fmt": "poker_eu", "dpi": 300, "file_checks": False,
        "slots": [{"id": "t", "label": "Titre", "box": [5, 5, 50, 10]}],
        "cards": [{"i": 0, "name": "OK", "art": {"w": 1000, "h": 1400},
                   "fields": {"t": "OK"}}],
    })
    assert out["rows"] == [] and out["ok"] is True
    assert out["safe_px"] == [673, 969]


# ═══════════════════════ 10. le temps ═══════════════════════════════════════

def test_60_cartes_et_un_pdf_a4_en_moins_de_30_s():
    """Seuil de la spec. On mesure la part BACKEND (imposition + écriture),
    la seule que ce test puisse tenir : le rendu des 60 cartes est celui du
    navigateur, et le lab le chronomètre avec son banc d'essai."""
    p = PR.build_plan(base(), 60)
    assert p.pages == 10
    src = carte()
    t0 = time.time()
    data = PR.build_pdf(p, {i: src for i in range(60)}, {}, "Deck 60")
    dt = time.time() - t0
    assert len(PdfReader(io.BytesIO(data)).pages) == 10
    assert dt < 30.0, f"{dt:.1f} s"
    assert dt < 5.0, f"marge insuffisante pour le rendu navigateur: {dt:.1f} s"


def test_une_planche_raster_reste_a_la_taille_de_la_planche():
    p = PR.build_plan(base(), 6)
    sheet = PR.compose_sheet(p, {i: carte() for i in range(6)}, 0, "front", "T")
    assert sheet.size == (2480, 3508)
    assert sheet.mode == "RGB"


def test_le_cartouche_ne_deborde_jamais_de_la_planche():
    """Le cartouche tient dans la largeur utile, TOUJOURS — et la mesure est
    exacte, pas estimée : la fonte à traits est à chasse fixe.

    Mesuré AVANT sur une vraie planche : la chaîne était coupée à 132 octets
    et se terminait par « pa? », l'estimation « 0,52 em » ayant tranché en
    plein milieu de « page 1/2 »."""
    for sheet, marge, dpi, fmt in (("a4", 10, 300, "poker_eu"),
                                   ("a4", 3, 300, "poker_eu"),
                                   ("a3", 10, 300, "tarot_eu"),
                                   ("letter", 10, 600, "poker_us"),
                                   ("a4", 10, 150, "micro")):
        p = PR.build_plan(base(sheet=sheet, margin_mm=marge, dpi=dpi, fmt=fmt), 10)
        cap0 = PR.slug_cap_px(p)
        x0 = max(2.0, p.margin_px * 0.18)
        utile = p.sheet_px[0] - 2 * x0
        nom = "Un nom de jeu particulièrement long " * 4
        g, d, cap = PR.slug_fit(p, nom, 0, "front", utile, cap0)
        large = (PR.text_width(g, cap) + PR.text_width("  ", cap)
                 + PR.text_width(d, cap))
        assert large <= utile + 1e-9, f"{sheet}/{marge}: {large} > {utile}"
        # la pagination et la date ne se perdent JAMAIS
        assert d.startswith("PAGE 1/") and "RECTO" in d
        assert "?" not in g and "?" not in d, "aucun caractère de remplacement"
        # et le tracé reste dans la planche
        polys, _w = PR.slug_layout(p, nom, 0, "front")
        assert polys
        assert max(x for poly in polys for x, _y in poly) <= p.sheet_px[0]
        assert min(x for poly in polys for x, _y in poly) >= 0


def test_le_cartouche_porte_la_page_et_la_date_et_change_de_page():
    """La case promet « format, DPI, page, date ». Les deux pages portaient
    RIGOUREUSEMENT le même texte, tronqué avant d'arriver à la pagination :
    deux planches mêlées sur une table de massicot étaient indiscernables."""
    p = PR.build_plan(base(), 10)
    data = PR.build_pdf(p, {i: carte() for i in range(10)}, {}, "Nouveau jeu")
    s1, s2 = bloc(pdf_ops(data, 0), "CFslug"), bloc(pdf_ops(data, 1), "CFslug")
    assert s1 and s2, "aucun cartouche dans le PDF"
    assert s1 != s2, "les deux pages portent le même cartouche"
    x0 = max(2.0, p.margin_px * 0.18)
    _g, d1, _c = PR.slug_fit(p, "Nouveau jeu", 0, "front",
                             p.sheet_px[0] - 2 * x0, PR.slug_cap_px(p))
    _g, d2, _c = PR.slug_fit(p, "Nouveau jeu", 1, "front",
                             p.sheet_px[0] - 2 * x0, PR.slug_cap_px(p))
    assert d1.startswith("PAGE 1/2") and d2.startswith("PAGE 2/2")
    assert re.search(r"\d{4}-\d{2}-\d{2}", d1), "pas de date"


def test_le_cartouche_n_a_aucune_police_a_incorporer():
    """Un `/Helvetica` non incorporé fait échouer tout contrôle avant vol, et
    son encodage par défaut imprimait « zone sßre » (0xFB = germandbls en
    StandardEncoding). Le cartouche est tracé : 0 objet /Font."""
    p = PR.build_plan(base(), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "Zone sûre")
    assert data.count(b"/Font") == 0, "un objet /Font dans le fichier"
    assert data.count(b"/Helvetica") == 0
    assert data.count(b"/FontFile") == 0
    ops = pdf_ops(data)
    assert " Tj" not in ops and "BT" not in ops
    assert bloc(ops, "CFslug").count(" m ") >= 30, "cartouche non tracé"
    # les accents français existent bien dans la fonte, ils ne sont pas des
    # tofus : « Û » se dessine, et pas comme un caractère inconnu
    assert PR.glyph("Û") and PR.glyph("Û") != PR.glyph("")
    assert PR.glyph("É") != PR.glyph("E")


# ═══════════════════════ 11. un seul moteur de rendu ════════════════════════

def test_un_bitmap_a_la_mauvaise_taille_est_refuse():
    """Le verrou mécanique de la spec (risque 2) : si le backend acceptait
    n'importe quelle taille, un second moteur de rendu pourrait s'installer
    et l'écran cesserait d'être ce qu'on imprime."""
    p = PR.build_plan(base(), 1)
    with pytest.raises(ValueError) as e:
        PR.open_card(png_bytes(Image.new("RGB", (800, 1100))), p, 0)
    assert "815x1110" in str(e.value) and "CF.renderCard" in str(e.value)
    # la bonne taille passe, elle
    assert PR.open_card(png_bytes(carte()), p, 0).size == (815, 1110)
    with pytest.raises(ValueError):
        PR.open_card(b"pas une image", p, 0)


# ═══════════════════════ les routes ═════════════════════════════════════════

def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process — la même
    forme que `test_cards_core._api` : le harnais lance UN PROCESSUS PAR
    FICHIER et `pytest-asyncio` n'est pas de la partie."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def test_les_routes_repondent_et_le_pdf_arrive():
    from app.services.cards.contract import decks_root
    doc = CC.create_deck("Jeu de test", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    assert (decks_root() / did).is_dir()

    r = _api("GET", f"/api/cards/{did}/print/sheets")
    assert r.status_code == 200
    d = r.json()
    assert [s["id"] for s in d["sheets"]] == ["a4", "letter", "a3", "card"]
    assert d["sheets"][0]["px"]["300"] == [2480, 3508]
    assert d["sheets"][0]["px"]["600"] == [4961, 7016]

    r = _api("POST", f"/api/cards/{did}/print/layout",
             json={"n_cards": 6, "margin_mm": 10, "gutter_mm": 4})
    assert r.status_code == 200
    plan = r.json()["plan"]
    assert (plan["cols"], plan["rows"], plan["per_page"]) == (2, 3, 6)
    assert plan["sheet_px"] == [2480, 3508]
    assert plan["gutter_pt"] == 11.3386
    assert plan["geom"]["canvas_px"] == [815, 1110]

    img = png_bytes(carte())
    files = [("fronts", (f"f{i}.png", img, "image/png")) for i in range(6)]
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps({"margin_mm": 10, "gutter_mm": 4})},
             files=files)
    assert r.status_code == 200, r.text[:400]
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["x-cf-grid"] == "2x3"
    assert r.headers["x-cf-gutter-pt"].startswith("11.338")
    pdf = PdfReader(io.BytesIO(r.content))
    assert len(pdf.pages) == 1
    assert [round(float(v), 2) for v in pdf.pages[0].mediabox] == MEDIABOX_A4_300
    assert "/TrimBox" in pdf.pages[0] and "/BleedBox" in pdf.pages[0]

    r = _api("POST", f"/api/cards/{did}/print/sheet",
             data={"spec": json.dumps({})}, files=files)
    assert r.status_code == 200
    assert r.headers["x-cf-pixels"] == "2480x3508"
    assert Image.open(io.BytesIO(r.content)).size == (2480, 3508)

    r = _api("POST", f"/api/cards/{did}/print/card",
             data={"spec": json.dumps({"card_fmt": "png", "card_bits": 16})},
             files={"file": ("c.png", img, "image/png")})
    assert r.status_code == 200
    assert r.headers["x-cf-phys"] == "11811"
    assert r.content[24] == 16 and phys_of(r.content)[0] == PHYS_300DPI

    r = _api("POST", f"/api/cards/{did}/print/preflight",
             json={"slots": [{"id": "t", "label": "T", "box": [0, 0, 60, 8]}],
                   "cards": [{"i": 0, "name": "Zéro", "art": {"w": 100, "h": 100}}]})
    assert r.status_code == 200
    kinds = {x["kind"] for x in r.json()["rows"]}
    assert {"texte_hors_zone_sure", "image_sous_definie"} <= kinds
    # les trois règles de FICHIER, celles qu'un vrai contrôle avant vol lève
    assert {"intention_de_sortie", "police_incorporee", "compression"} <= kinds
    r = _api("POST", f"/api/cards/{did}/print/preflight",
             json={"slots": [], "cards": [], "file_checks": False})
    assert r.json()["rows"] == []


def test_le_controle_avant_vol_REFUSE_vraiment_l_export():
    """« Le contrôle détecte parfaitement mais ne refuse RIEN : avec 6 erreurs
    rouges à l'écran, le PDF part quand même, sans confirmation. »

    La porte est dans la ROUTE, pas seulement dans l'écran : un client qui
    saute l'interface la rencontre aussi. Elle ne cède qu'à un `force: true`
    explicite — l'utilisateur garde le dernier mot, mais il doit le dire."""
    doc = CC.create_deck("Jeu porte", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    img = png_bytes(carte())
    files = [("fronts", (f"f{i}.png", img, "image/png")) for i in range(6)]
    # un débordement de zone sûre FABRIQUÉ, exactement comme à l'écran :
    # la boîte du titre part à -4 mm et fait 70 mm de large sur 63 de carte.
    faute = {"slots": [{"id": "title", "label": "Titre",
                        "box": [-4, -4, 70, 10]}],
             "cards": [{"i": i, "name": f"C{i}", "fields": {"title": f"C{i}"},
                        "has_art": True} for i in range(6)]}

    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(faute)}, files=files)
    assert r.status_code == 409, "le PDF fautif est parti sans un mot"
    d = r.json()["detail"]
    assert d["errors"] == 6, d
    assert d["rows"] and "zone sûre" in d["rows"][0]["message"]
    assert d["rows"][0]["card"] == "C0" and d["rows"][0]["slot"] == "title"

    # la planche et la carte seule passent par la MÊME porte
    r = _api("POST", f"/api/cards/{did}/print/sheet",
             data={"spec": json.dumps(faute)}, files=files)
    assert r.status_code == 409
    r = _api("POST", f"/api/cards/{did}/print/card",
             data={"spec": json.dumps(faute)},
             files={"file": ("c.png", img, "image/png")})
    assert r.status_code == 409

    # FORCÉ EN LE SACHANT : le fichier sort, et c'est le seul chemin.
    force = dict(faute, force=True)
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(force)}, files=files)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"

    # boîte remise dedans -> plus d'erreur, plus de porte.
    bon = dict(faute, slots=[{"id": "title", "label": "Titre",
                              "box": [12, 6, 39, 10]}])
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(bon)}, files=files)
    assert r.status_code == 200
    # et une demande SANS contrôle par carte n'est pas bloquée par surprise :
    # sans slots ni cards, il n'y a rien à contrôler, et on ne le prétend pas.
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps({})}, files=files)
    assert r.status_code == 200


def test_l_audit_du_pdf_se_lit_sur_les_octets_par_la_route():
    """Le badge affiché ne vient pas du réglage : la route construit un vrai
    PDF, le relit, et rend la mesure. Les en-têtes du /pdf portent la même."""
    doc = CC.create_deck("Jeu audit", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    r = _api("POST", f"/api/cards/{did}/print/audit", json={"intent": "srgb"})
    assert r.status_code == 200
    a = r.json()["audit"]
    # Calques par defaut -> %PDF-1.5 et deux /OCG, LUS dans le catalogue.
    assert a["header"] == "%PDF-1.5" and a["intent_subtype"] == "/CF_ICCSource"
    assert a["ocg_count"] == 2 and len(a["ocg_names"]) == 2
    assert a["pdfx"] == "" and a["pdfx_manques"] == []
    assert a["profile_bytes"] == len(PR.srgb_icc()) and a["font_hits"] == 0

    r = _api("POST", f"/api/cards/{did}/print/audit",
             json={"intent": "srgb", "layers": False})
    a2 = r.json()["audit"]
    assert a2["header"] == "%PDF-1.4" and a2["ocg_count"] == 0

    # La revendication PDF/X ne tient QUE sans calques : le contenu optionnel
    # est du PDF 1.5, que PDF/X-3:2003 (PDF 1.4) n'admet pas.
    r = _api("POST", f"/api/cards/{did}/print/audit",
             json={"intent": "fogra39", "color": "cmyk_device"})
    assert r.json()["audit"]["pdfx"] == ""
    r = _api("POST", f"/api/cards/{did}/print/audit",
             json={"intent": "fogra39", "color": "cmyk_device", "layers": False})
    assert r.json()["audit"]["pdfx"] == "PDF/X-3:2003"

    img = png_bytes(carte())
    files = [("fronts", (f"f{i}.png", img, "image/png")) for i in range(6)]
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps({})}, files=files)
    assert r.status_code == 200
    assert r.headers["x-cf-header"] == "%PDF-1.5"
    assert r.headers["x-cf-pdfx"] == "aucune"
    assert r.headers["x-cf-layers"].count(",") == 1
    assert r.headers["x-cf-subtype"] == "/CF_ICCSource"
    assert r.headers["x-cf-boxes"] == "1/1"
    assert r.headers["x-cf-fonts"] == "0"
    assert r.headers["x-cf-trapped"] == "/False"
    assert r.headers["x-cf-gutter-marks"] == "14"
    # LA DÉRIVE TOLÉRÉE VOYAGE AVEC LE FICHIER, relue dans ses octets :
    # 1,0000 mm, 34 traits, 0 qui touche une carte.
    assert r.headers["x-cf-mark-clearance"] == "1.0000/34/0"
    assert a["mark_clearance_mm"] == 1.0 and a["mark_touch"] == 0


def test_les_traits_de_gouttiere_sont_comptes_et_leur_risque_est_leve():
    """« 14 traits de repérage par page sont tracés PAR-DESSUS l'illustration
    à fond perdu, dans les gouttières. […] c'est précisément celui que son
    contrôle avant vol ne lève PAS. » Il le lève — et surtout le chiffre qu'il
    donnait était FAUX : la dérive tolérée annoncée valait 2 mm, la mesure en
    donne 0. Ce test garde les deux mesures côte à côte."""
    p = PR.build_plan(base(gutter_mm=4), 6)
    n = PR.gutter_marks(p)
    assert n == 14, "2 verticales x 1 gouttière + 4 horizontales x ... "
    # le compte se recoupe à la main : chaque trait de gouttière est
    # entièrement contenu dans une bande sans carte.
    xs = [PR.cell_rect(p, 0, c)[0] for c in range(p.cols)]
    bandex = (xs[0] + p.cell_px[0], xs[1])
    dedans = [s for s in PR.mark_segments(p)
              if abs(s[1] - s[3]) < 1e-6
              and s[0] >= bandex[0] - 1e-6 and s[2] <= bandex[1] + 1e-6]
    assert len(dedans) == 6, "6 traits horizontaux dans la gouttière verticale"

    # ── LE CHIFFRE QUI ÉTAIT FAUX, ET SA MESURE ───────────────────────────
    # La règle annonçait « la dérive tolérée est exactement le fond perdu qui
    # reste entre deux cartes, soit 2,00 mm ». MESURE sur la géométrie écrite
    # avec l'ancien tracé (`mark_safe` décoché, qui le reproduit exactement) :
    # le trait allait d'une ligne de coupe à l'autre, donc l'encre TOUCHAIT la
    # carte et la dérive tolérée valait ZÉRO. Le fond perdu restant, lui,
    # valait bien 2 mm — mais il ne mesure pas la même chose.
    vieux = PR.build_plan(base(gutter_mm=4, mark_safe=False), 6)
    assert PR.mark_clearance_mm(vieux) == 0.0
    assert PR.mark_touch(vieux) == 14
    assert PR.bleed_mm_real(vieux)[1] == 2.0        # le 2 mm, lui, est vrai
    v = {x["kind"]: x for x in vieux.warnings}
    assert v["reperes_sur_la_carte"]["level"] == "err"
    assert v["reperes_sur_la_carte"]["value"] == 14
    assert v["reperes_sur_la_carte"]["fix"] == {
        "mark_safe": True, "label": "repères hors carte (retrait mesuré)"}

    # ── ET LE CORRECTIF D'AVANT NE CORRIGEAIT PAS ─────────────────────────
    # Il proposait « gouttière à 6 mm ». Mesuré : le fond perdu passe entier
    # (3,00 mm), et la distance encre -> carte reste à 0,0000 mm. Un bouton
    # qui ne corrige pas le défaut qu'il annonce vaut moins que pas de bouton.
    six = PR.build_plan(base(gutter_mm=6, mark_safe=False), 6)
    assert PR.bleed_mm_real(six) == (3.01, 3.0)
    assert PR.mark_clearance_mm(six) == 0.0 and PR.mark_touch(six) == 14

    # ── CE QUI EST AFFICHÉ MAINTENANT : UNE DISTANCE RELUE ────────────────
    w = {x["kind"]: x for x in p.warnings}
    assert "reperes_sur_la_carte" not in w
    assert w["reperes_hors_carte"]["level"] == "ok"
    assert w["reperes_hors_carte"]["value"] == PR.mark_clearance_mm(p) == 1.0
    assert "1.00 mm" in w["reperes_hors_carte"]["message"]
    # les DEUX distances sont dites, et elles ne se confondent pas : 1,00 mm
    # avant l'encre de repérage, 2,00 mm avant l'illustration de la voisine.
    assert "2.00 mm entre deux cartes" in w["reperes_hors_carte"]["message"]
    q = PR.build_plan(base(gutter_mm=6), 6)
    assert PR.mark_clearance_mm(q) == 1.5 and PR.mark_touch(q) == 0
    assert PR.bleed_mm_real(q) == (3.01, 3.0)
    # aucun repère du tout -> plus rien à lever, et rien à promettre.
    z = PR.build_plan(base(marks="none"), 6)
    assert PR.gutter_marks(z) == 0 and PR.mark_clearance_mm(z) == -1.0
    assert not any(x["kind"].startswith("reperes_") for x in z.warnings)


def test_la_bleedbox_est_exactement_ce_qui_est_peint():
    """UN REPROCHE QUE JE REFUSE, MESURE À L'APPUI : « la BleedBox annonce
    3 mm sur tout le pourtour alors qu'il ne pose que 2,00 mm entre deux
    cartes ». La BleedBox est une boîte de PLANCHE : elle borde l'emprise
    peinte, et le fond perdu interne n'est pas sur son pourtour. Elle vaut
    ici, au dix-millième de point près, l'union des rectangles de rognage
    réellement écrits dans le flux — donc rien n'est promis en trop."""
    p = PR.build_plan(base(gutter_mm=4), 6)
    data = PR.build_pdf(p, {i: carte(tag=str(i)) for i in range(6)}, {}, "T")
    pg = PdfReader(io.BytesIO(data)).pages[0]
    bleed = [round(float(v), 4) for v in pg["/BleedBox"]]
    trim = [round(float(v), 4) for v in pg["/TrimBox"]]

    # l'emprise PEINTE, relue dans les opérateurs `re W n` du flux
    ops = pdf_ops(data)
    rects = [tuple(float(x) for x in m)
             for m in re.findall(r"q ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+) re W n",
                                 ops)]
    assert len(rects) == 6, "un rectangle de rognage par carte"
    peint = [min(r[0] for r in rects), min(r[1] for r in rects),
             max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)]
    for i in range(4):
        assert abs(bleed[i] - round(peint[i], 4)) <= 1e-3, \
            f"BleedBox[{i}] = {bleed[i]} pt pour {peint[i]} pt réellement peints"
    # 3 mm dehors, et c'est vrai au dixième de micron près
    dehors = round((trim[0] - bleed[0]) / 72 * 25.4, 4)
    assert dehors == round(35.5 * 25.4 / 300, 4) == 3.0057
    # ce qui reste ENTRE deux cartes, lui, vaut la moitié de la gouttière —
    # et c'est écrit, dans le cartouche, dans /Keywords et dans le XMP.
    assert PR.bleed_mm_real(p) == (3.01, 2.0)
    assert b"fond_perdu_pose_gouttiere_mm>2.00" in data


def test_la_densite_affichee_est_celle_du_chunk_pas_celle_du_curseur():
    """« La fiche arrondit pHYs 11811 px/m en 300,00 DPI. La valeur en octets
    est celle qu'exige le seuil, mais 11811 px/m vaut 299,9994 DPI. »

    L'unité du chunk pHYs est le MÈTRE ENTIER : 300 DPI vaudrait 11811,0236
    px/m et n'est pas représentable. Le panneau affiche donc le chiffre du
    fichier, pas celui du curseur."""
    assert PR.phys_ppm(300) == 11811
    assert round(PR.phys_dpi(300), 4) == 299.9994
    assert PR.phys_dpi(300) != 300.0
    assert PR.phys_ppm(600) == 23622 and round(PR.phys_dpi(600), 4) == 599.9988
    # ce que le PNG livré porte vraiment
    im = carte()
    out, _mime, _ext = PR.encode_image(im, "png", 8, 300, True, 95)
    assert phys_of(out)[0] == PR.phys_ppm(300) == 11811
    # et ce que le plan sert à l'écran : les deux chiffres, jamais l'un pour
    # l'autre.
    d = PR.plan_dict(PR.build_plan(base(), 6))
    assert d["phys_ppm"] == 11811 and d["phys_dpi"] == 299.9994
    assert d["dpi"] == 300
    rows = {r["kind"]: r for r in PR.preflight(base(n_cards=1, slots=[],
                                                    cards=[]))["rows"]}
    assert "11811 px/m" in rows["densite_inscrite"]["message"]
    assert "299.9994 DPI" in rows["densite_inscrite"]["message"]
    # l'écran ne doit nulle part écrire « 300 DPI » à propos du FICHIER
    racine = pathlib.Path(__file__).resolve().parents[2]
    src = (racine / "frontend/cardforge/js/mod-print.js").read_text(encoding="utf-8")
    assert "phys_dpi" in src, "l'écran doit lire la mesure, pas la recalculer"


def test_changer_de_format_reprend_son_fond_perdu_natif():
    """Le piège qui coûte la parité nanDECK sur un simple aperçu.

    Demander un plan `poker_us` depuis un deck `poker_eu` sans préciser le
    fond perdu doit reprendre le fond perdu IMPÉRIAL (0.125 in) : sinon la
    toile sort à 821x1121 au lieu de 825x1125. Mesuré sur le :8765 avant
    correction. Un fond perdu passé explicitement reste prioritaire."""
    doc = CC.create_deck("Jeu", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    r = _api("POST", f"/api/cards/{did}/print/layout",
             json={"fmt": "poker_us", "n_cards": 6})
    assert r.json()["plan"]["geom"]["canvas_px"] == [825, 1125]
    r = _api("POST", f"/api/cards/{did}/print/layout",
             json={"fmt": "poker_us", "bleed_mm": 3.0, "n_cards": 6})
    assert r.json()["plan"]["geom"]["canvas_px"] == [821, 1121], \
        "un fond perdu explicite doit rester prioritaire"
    r = _api("POST", f"/api/cards/{did}/print/layout", json={"n_cards": 6})
    assert r.json()["plan"]["geom"]["canvas_px"] == [815, 1110]


def test_aucun_500_sur_un_corps_mal_forme():
    """Spec 2.5 : un corps mal formé ne doit JAMAIS faire 500."""
    doc = CC.create_deck("Jeu", None)
    did = doc["id"]
    mauvais = [
        {"sheet": "papyrus"}, {"margin_mm": "beaucoup"},
        {"gutter_mm": -3}, {"marks": "arc-en-ciel"}, {"dpi": 99999},
        {"n_cards": "six"}, {"orient": 42}, {"mark_color": "bleu"},
        {"flip": "diagonal"}, {"trimbox": "peut-être"}, {"margin_mm": None},
    ]
    for body in mauvais:
        r = _api("POST", f"/api/cards/{did}/print/layout", json=body)
        assert r.status_code in (200, 400), (body, r.status_code, r.text[:200])
        if r.status_code == 400:
            assert isinstance(r.json()["detail"], str)
    # `1e999` -> float('inf') : httpx refuse de l'encoder, un vrai client le
    # poste tel quel. C'est LE corps qui faisait 500 (`int(inf)` lève).
    r = _api("POST", f"/api/cards/{did}/print/layout",
             content=b'{"margin_mm": 1e999, "dpi": 1e999}',
             headers={"content-type": "application/json"})
    assert r.status_code == 400, r.text[:200]
    assert isinstance(r.json()["detail"], str)
    for body in ({"slots": "beaucoup"}, {"cards": 3}, {"min_dpi": "haut"},
                 {"slots": [{"id": "t", "box": "ailleurs"}]}):
        r = _api("POST", f"/api/cards/{did}/print/preflight", json=body)
        assert r.status_code in (200, 400), (body, r.status_code)
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": "{pas du json"},
             files=[("fronts", ("f.png", png_bytes(carte()), "image/png"))])
    assert r.status_code == 400
    r = _api("POST", f"/api/cards/{did}/print/pdf", data={"spec": "{}"},
             files=[("fronts", ("f.png", png_bytes(
                 Image.new("RGB", (10, 10))), "image/png"))])
    assert r.status_code == 400 and "815x1110" in r.json()["detail"]
    r = _api("GET", "/api/cards/deck_zzzzzzzz/print/sheets")
    assert r.status_code == 400
    r = _api("GET", "/api/cards/deck_00000000/print/sheets")
    assert r.status_code == 404


def test_les_routes_de_p7_sont_montees_sous_son_prefixe():
    from app.main import app
    chemins = [p for p in app.openapi().get("paths", {})
               if "/print" in p]
    for attendu in ("/api/cards/{did}/print/sheets", "/api/cards/{did}/print/layout",
                    "/api/cards/{did}/print/preflight", "/api/cards/{did}/print/card",
                    "/api/cards/{did}/print/sheet", "/api/cards/{did}/print/pdf"):
        assert attendu in chemins, f"{attendu} absent de {chemins}"


# ═══════════════════════ le miroir écran / backend ══════════════════════════

def test_le_plan_de_l_ecran_est_le_meme_que_celui_du_backend():
    """`layoutOf()` de js/mod-print.js est le MIROIR de `build_plan()`. La
    formule vit des deux côtés parce que l'écran ne peut pas attendre le
    réseau à chaque réglage ; le risque est qu'elles dérivent en silence.

    Ici on relit la SOURCE SERVIE et on vérifie que les quatre lignes qui
    comptent y sont, mot pour mot dans leur structure : le nombre de colonnes,
    celui de lignes, le centrage et le pas de grille."""
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-print.js")
    src = js.read_text(encoding="utf-8")
    assert "Math.floor((sw - 2 * marge + gut) / (cw + gut))" in src
    assert "Math.floor((sh - 2 * marge + gut) / (ch + gut))" in src
    assert "st.center ? (sw - cwid) / 2 : marge" in src
    assert "c * (p.cell_px[0] + p.gutter_px)" in src
    # et la pièce n'a AUCUN painter : elle ne dessine pas la carte.
    assert "painters: []" in src


def test_les_valeurs_par_defaut_sont_les_memes_des_deux_cotes():
    """Un défaut qui diffère entre l'écran et le backend, c'est une planche
    qui change de plan au premier export."""
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-print.js")
    src = js.read_text(encoding="utf-8")
    bloc = src[src.index("const DEFAULTS = {"):src.index("};", src.index("const DEFAULTS = {"))]
    for cle, val in PR.DEFAULTS.items():
        if isinstance(val, bool):
            attendu = f"{cle}: {'true' if val else 'false'}"
        elif isinstance(val, str):
            attendu = f'{cle}: "{val}"'
        elif float(val) == int(val):
            attendu = f"{cle}: {int(val)}"
        else:
            attendu = f"{cle}: {val}"
        assert attendu in bloc, f"defaut divergent: {attendu!r}"


def test_la_regle_de_geometrie_n_est_jamais_recalculee_dans_la_piece():
    """Aucune dimension de CARTE ne se recalcule ici : elles viennent toutes
    de `contract.geom`. Le seul `mm -> px` local sert aux longueurs propres à
    l'impression (marge, gouttière, repères).

    LA BORNE DE LA SURVEILLANCE EST LE CORPS D'IMPOSITION — `build_plan` et
    tout ce qui pose des pixels, jusqu'à la section de MESURE. Elle allait
    jusqu'à `def preflight`, ce qui avalait `pdf_audit` et `file_checks` :
    ces deux-là RELISENT et CHIFFRENT (« la rogne écrite vaut 62,992 mm, soit
    -8 µm du nominal »), et ce travail-là exige de nommer le nominal. La
    borne trop large rendait donc ce garde-fou ROUGE dès que le produit s'est
    mis à mesurer ce qu'il écrit. Ce qu'elle protégeait vraiment est intact
    et re-vérifié ci-dessous, par le calcul et non par le texte."""
    py = pathlib.Path(PR.__file__).read_text(encoding="utf-8")
    corps = py[py.index("def build_plan"):]
    for interdit in ("trim_mm", "/ 25.4", "MM_PER_INCH *"):
        assert interdit not in corps.split("def match_format_mm")[0], interdit
    assert "sheet_px(sheet, g.dpi)" in corps
    assert "g.trim_px" in corps
    # LES FONCTIONS DE MESURE MESURENT — elles ne produisent aucune géométrie.
    # Preuve : leur résultat, reconverti, retombe EXACTEMENT sur les pixels du
    # contrat, sur tous les formats et toutes les définitions.
    for fmt in CT.FORMATS:
        for dpi in (300, 600):
            p = PR.build_plan(base(fmt=fmt, dpi=dpi, sheet="card"), 1)
            tw, th = PR.trim_written_mm(p)
            zw, zh = PR.safe_written_mm(p)
            assert (round(tw / 25.4 * dpi), round(th / 25.4 * dpi)) == p.geom.trim_px
            assert (round(zw / 25.4 * dpi), round(zh / 25.4 * dpi)) == p.geom.safe_px
            ix, iy = PR.safe_inset_written_mm(p)
            assert abs(ix - (p.geom.safe_off_px[0] - p.geom.bleed_off_px[0])
                       / dpi * 25.4) < 1e-9
            assert abs(iy - (p.geom.safe_off_px[1] - p.geom.bleed_off_px[1])
                       / dpi * 25.4) < 1e-9


def test_le_module_ne_dessine_aucune_carte():
    """P7 impose, elle ne rend pas. Aucun tracé de carte dans ce fichier :
    ni rectangle arrondi, ni texte de carte, ni police de rendu."""
    py = pathlib.Path(PR.__file__).read_text(encoding="utf-8")
    for interdit in ("rounded_rectangle", "arc(", "ellipse(", "truetype("):
        assert interdit not in py, interdit
    assert "open_card" in py and "geom.canvas_px" in py


# ═══════════════════════════════════════════════════════════════════════════
# 12. GESTION DE COULEUR — le plus gros manque nommé par les DEUX critiques
#
# Mesure AVANT correction, sur le PDF livré : /OutputIntent 0, /ICCBased 0,
# /DeviceCMYK 0, /Separation 0, 10 images en /DeviceRGB, et des traits de
# coupe écrits « 0.8784 0.1059 0.1412 RG » — un rouge RVB, qui à la
# séparation devient magenta + jaune et ne sort donc PAS sur les quatre
# plaques. Rien dans le fichier ne disait à l'imprimeur dans quel espace
# convertir. Chaque test ci-dessous rejoue une de ces mesures.
# ═══════════════════════════════════════════════════════════════════════════

WIN_ICC = pathlib.Path(r"C:\Windows\System32\spool\drivers\color")


def test_le_pdf_declare_son_intention_de_sortie():
    """AVANT : `pdf.count(b"/OutputIntent") == 0`. Le fichier ne disait pas
    dans quel espace il avait été fabriqué.

    ET AVANT AUSSI : il portait `/S /GTS_PDFX` — le sous-type DÉFINI PAR
    PDF/X — sans `/GTS_PDFXVersion`, sans XMP, sans `/Trapped`, sous un
    en-tête %PDF-1.3 antérieur à `/OutputIntents`. Deux contrôles l'ont relevé
    sur les octets. sRGB est un profil d'ÉCRAN (classe « mntr ») et décrit la
    SOURCE : il ne peut pas porter de revendication PDF/X. Le sous-type est
    donc désormais celui d'une extension, qui ne promet rien."""
    p = PR.build_plan(base(intent="srgb"), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    assert data.count(b"/OutputIntent") >= 1
    r = PdfReader(io.BytesIO(data))
    oi = r.trailer["/Root"]["/OutputIntents"][0]
    assert str(oi["/S"]) == PR.SRC_SUBTYPE == "/CF_ICCSource"
    assert b"/GTS_PDFX" not in data, "PDF/X revendiqué sans être livré"
    # L'IDENTIFIANT EST CELUI DU PROFIL EMBARQUE, lu dans son tag `desc` :
    # il annoncait « sRGB IEC61966-2.1 », qui est le nom du fichier de
    # reference de l'ICC (des dizaines de Ko), pas celui d'un profil matriciel
    # de 588 octets construit par littleCMS. La colorimetrie est bien sRGB ;
    # l'identite du fichier, non — et c'est /OutputCondition qui porte la
    # nuance, en toutes lettres.
    assert str(oi["/OutputConditionIdentifier"]) == PR.icc_desc(PR.srgb_icc())
    assert str(oi["/OutputConditionIdentifier"]) == "sRGB built-in"
    assert "IEC 61966-2.1" in str(oi["/OutputCondition"])
    assert "588 octets" in str(oi["/OutputCondition"])
    # « sRGB IEC61966-2.1 » n'est PAS un nom de caractérisation du registre
    # color.org : pointer vers ce registre à côté était un champ de trop.
    assert "/RegistryName" not in oi
    prof = oi["/DestOutputProfile"].get_object()
    octets = prof.get_data()
    assert octets[36:40] == b"acsp", "le profil embarqué n'est pas un ICC"
    assert octets[16:20] == b"RGB "
    assert octets[12:16] == b"mntr", "profil d'écran : pas une condition de presse"
    assert int(prof["/N"]) == 3
    # et sans intention, on ne PROMET rien : le champ disparaît, et le plan
    # le dit lui-même au lieu de le taire.
    q = PR.build_plan(base(intent="none"), 6)
    vide = PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T")
    assert vide.count(b"/OutputIntent") == 0
    assert any(w["kind"] == "sans_intention_de_sortie" for w in q.warnings)


def test_la_revendication_pdfx_n_est_ecrite_qu_avec_toute_sa_structure():
    """LE REPROCHE LE PLUS DUR DES DEUX CÔTÉS, ET IL ÉTAIT JUSTE : « il vend
    du PDF/X qu'il ne livre pas ». Un seul sous-type PDF/X est écrit — et
    seulement accompagné de TOUT ce qu'il implique. La conjonction est
    vérifiée SUR LES OCTETS du fichier écrit, pas sur le réglage."""
    # 1. Condition de PRESSE normalisée -> revendication tenue, et complète.
    p = PR.build_plan(base(intent="fogra39", color="cmyk_device",
                           layers=False), 8)
    data = PR.build_pdf(p, {i: carte() for i in range(8)}, {}, "T")
    a = PR.pdf_audit(data)
    assert a["pdfx"] == PR.PDFX_VERSION == "PDF/X-3:2003"
    assert a["pdfx_manques"] == []
    assert a["intent_subtype"] == "/GTS_PDFX"
    assert a["intent_version"] == "PDF/X-3:2003"
    assert a["header"] == "%PDF-1.4", "OutputIntents est du PDF 1.4"
    assert a["xmp_blocks"] >= 1 and a["xmp_pdfx"] is True
    assert a["trapped"] == "/False"
    assert a["font_hits"] == 0 and a["encrypted"] is False
    assert a["pages_4_boites"] == a["pages"] == 2
    assert a["pages_boites_emboitees"] == a["pages"]
    assert b"GTS_PDFXVersion" in data and b"pdfxid" in data

    # 2. Espace SOURCE (sRGB, classe mntr) -> aucune revendication, nulle part.
    q = PR.build_plan(base(intent="srgb", layers=False), 6)
    d2 = PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T")
    b = PR.pdf_audit(d2)
    assert b["pdfx"] == "" and b["pdfx_manques"] == []
    assert b["intent_subtype"] == "/CF_ICCSource"
    assert b["intent_version"] == ""
    assert b"GTS_PDFXVersion" not in d2 and b"pdfxid" not in d2
    # l'honnêteté n'est pas une régression : l'en-tête, les boîtes, le XMP et
    # /Trapped restent écrits — c'est la seule PROMESSE qui disparaît.
    assert b["header"] == "%PDF-1.4" and b["xmp_blocks"] >= 1
    assert b["trapped"] == "/False" and b["pages_4_boites"] == b["pages"]
    assert b["profile_bytes"] == len(PR.srgb_icc()) and b["profile_class"] == "mntr"

    # 3. L'audit REFUSE une revendication incomplète : on fabrique le mensonge
    #    que les deux critiques ont trouvé (sous-type PDF/X, rien derrière) et
    #    l'audit le nomme au lieu de le confirmer.
    faux = d2.replace(b"/CF_ICCSource", b"/GTS_PDFX\x20\x20\x20\x20")
    c = PR.pdf_audit(faux)
    assert c["intent_subtype"] == "/GTS_PDFX"
    assert c["pdfx"] == "", "un audit qui s'arrête à l'étiquette ne vaut rien"
    assert "/GTS_PDFXVersion absent" in c["pdfx_manques"]
    assert "XMP pdfxid absent" in c["pdfx_manques"]


def test_les_conditions_cmyk_sont_designees_par_leur_nom_de_registre():
    """PDF 32000-1 §14.11.5 : pour une condition de production NORMALISÉE,
    le profil embarqué est facultatif — c'est le chemin des portails
    d'imprimeurs. On écrit alors le nom exact du registre ICC."""
    attendu = {"fogra39": "FOGRA39L", "fogra51": "FOGRA51L",
               "fogra52": "FOGRA52L", "gracol": "CGATS TR 006",
               "swop": "CGATS TR 003", "japan": "JC200103"}
    for ident, nom in attendu.items():
        p = PR.build_plan(base(intent=ident), 6)
        data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
        oi = PdfReader(io.BytesIO(data)).trailer["/Root"]["/OutputIntents"][0]
        assert str(oi["/OutputConditionIdentifier"]) == nom, ident
        assert str(oi["/RegistryName"]) == "http://www.color.org"
        assert "/DestOutputProfile" not in oi, "condition normalisée : facultatif"


def test_les_images_sont_etiquetees_et_non_devicergb_muet():
    """AVANT : 10 XObjects en `/DeviceRGB`, /ICCBased 0. Un /DeviceRGB muet
    ne dit pas au RIP ce que valent les nombres."""
    p = PR.build_plan(base(intent="srgb"), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    assert data.count(b"/DeviceRGB") == 0, "une image en DeviceRGB muet"
    assert data.count(b"/ICCBased") >= 1
    r = PdfReader(io.BytesIO(data))
    for v in r.pages[0]["/Resources"]["/XObject"].values():
        cs = v.get_object()["/ColorSpace"]
        assert str(cs[0]) == "/ICCBased"
        assert int(cs[1].get_object()["/N"]) == 3


def test_les_reperes_sortent_sur_les_quatre_plaques():
    """AVANT : `0.8784 0.1059 0.1412 RG`. Ce rouge se sépare en magenta +
    jaune : il laisse le cyan et le noir vierges, donc il ne repère rien.
    La couleur de repérage est une /Separation /All à 100 % des 4 encres."""
    p = PR.build_plan(base(mark_space="registration"), 6)
    assert PR.DEFAULTS["mark_space"] == "registration", "mauvais défaut"
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    assert data.count(b"/Separation") >= 1
    r = PdfReader(io.BytesIO(data))
    cs = r.pages[0]["/Resources"]["/ColorSpace"]["/CSreg"]
    assert str(cs[0]) == "/Separation" and str(cs[1]) == "/All"
    assert str(cs[2]) == "/DeviceCMYK"
    fn = cs[3].get_object()
    assert int(fn["/FunctionType"]) == 2
    assert [float(v) for v in fn["/C1"]] == [1.0, 1.0, 1.0, 1.0], \
        "le repérage doit valoir 100 % sur les QUATRE plaques"
    assert [float(v) for v in fn["/C0"]] == [0.0, 0.0, 0.0, 0.0]
    ops = bloc(pdf_ops(data), "CFmarks")
    assert "/CSreg CS 1 SCN" in ops
    assert len(re.findall(r" m [\d.]+ [\d.]+ l S", ops)) >= 20, "toujours vectoriel"
    # les deux autres encres restent joignables, et elles sont écrites telles
    # qu'annoncées : noir 100 % pur, ou le RVB d'avant.
    n = PR.build_pdf(PR.build_plan(base(mark_space="cmyk_black"), 6),
                     {i: carte() for i in range(6)}, {}, "T")
    assert "0 0 0 1 K" in bloc(pdf_ops(n), "CFmarks")
    v = PR.build_pdf(PR.build_plan(base(mark_space="rgb"), 6),
                     {i: carte() for i in range(6)}, {}, "T")
    assert re.search(r"[\d.]+ [\d.]+ [\d.]+ RG", bloc(pdf_ops(v), "CFmarks"))


def test_le_cmyk_d_appareil_est_un_vrai_cmyk_et_se_nomme_comme_tel():
    """Quatre canaux dans le fichier, /DeviceCMYK, et sans perte de force :
    un JPEG CMYK d'Adobe s'écrit INVERSÉ et réclame un /Decode — on ne livre
    pas ce piège. Et le plan dit lui-même que c'est une conversion sans
    profil, sans retrait des sous-couleurs."""
    p = PR.build_plan(base(color="cmyk_device", intent="fogra39",
                           lossless=False), 6)
    assert p.lossless is True, "le CMYK doit forcer le sans-perte"
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    r = PdfReader(io.BytesIO(data))
    x = list(r.pages[0]["/Resources"]["/XObject"].values())[0].get_object()
    assert str(x["/ColorSpace"]) == "/DeviceCMYK"
    assert str(x["/Filter"]) == "/FlateDecode"
    assert len(x.get_data()) == int(x["/Width"]) * int(x["/Height"]) * 4
    assert any(w["kind"] == "cmyk_sans_profil" for w in p.warnings)


def test_le_cmyk_par_profil_icc_separe_vraiment():
    """La séparation par profil : littleCMS, le profil de l'imprimeur, et un
    NOIR qui apparaît. La conversion d'appareil de Pillow, elle, rend K=0 —
    c'est toute la différence entre « du CMYK » et une séparation."""
    src = WIN_ICC / "CoatedFOGRA39.icc"
    if not src.exists():
        pytest.skip("aucun profil CMYK sur ce poste")
    icc = src.read_bytes()
    info = PR.icc_info(icc)
    assert info["space"] == "CMYK" and info["n"] == 4 and info["cls"] == "prtr"
    assert info["desc"] == "Coated FOGRA39 (ISO 12647-2:2004)"
    p = PR.build_plan(base(color="cmyk_icc", intent="icc"), 6, icc)
    bleu = Image.new("RGB", tuple(p.geom.canvas_px), (24, 56, 92))
    sep, tag = PR.to_output_space(bleu, p)
    assert sep.mode == "CMYK" and tag == "CMYK/ICC"
    assert sep.getpixel((5, 5))[3] > 40, "aucun noir : ce n'est pas une séparation"
    nai = Image.new("RGB", (4, 4), (24, 56, 92)).convert("CMYK")
    assert nai.getpixel((0, 0))[3] == 0, "la conversion d'appareil n'a pas de noir"
    data = PR.build_pdf(p, {i: bleu for i in range(6)}, {}, "T")
    oi = PdfReader(io.BytesIO(data)).trailer["/Root"]["/OutputIntents"][0]
    assert str(oi["/OutputConditionIdentifier"]) == info["desc"]
    assert len(oi["/DestOutputProfile"].get_object().get_data()) == len(icc)


def test_un_profil_icc_est_valide_a_l_octet():
    """Un .icc invalide embarqué, c'est un PDF que le RIP refuse. On lit la
    signature, pas l'extension du fichier."""
    assert PR.icc_info(PR.srgb_icc())["space"] == "RGB"
    for mauvais in (b"", b"pas un profil" * 20, PR.srgb_icc()[:100]):
        with pytest.raises(ValueError):
            PR.icc_info(mauvais)
    faux = bytearray(PR.srgb_icc())
    faux[36:40] = b"XXXX"
    with pytest.raises(ValueError) as e:
        PR.icc_info(bytes(faux))
    assert "acsp" in str(e.value)
    # et les deux chemins qui EXIGENT un profil le disent au lieu de mentir
    with pytest.raises(ValueError) as e:
        PR.build_plan(base(color="cmyk_icc"), 6)
    assert ".icc" in str(e.value)
    with pytest.raises(ValueError) as e:
        PR.build_plan(base(intent="icc"), 6)
    assert "téléverser" in str(e.value).lower()


# ═══════════════════════════════════════════════════════════════════════════
# 13. LE FICHIER LIVRÉ : poids, perte, cartouche, cadres
# ═══════════════════════════════════════════════════════════════════════════

def test_deux_cartes_identiques_ne_sont_ecrites_qu_une_fois():
    """AVANT : 10 bitmaps encodés séparément pour 4 visuels distincts, 10 md5
    différents — « 5 cartes REBUT rigoureusement identiques encodées 5 fois ».
    La carte est maintenant posée ENTIÈRE et détourée par un chemin de
    rognage : l'XObject redevient la carte, donc partageable."""
    a, b_, c = carte(tag="A"), carte(tag="B"), carte(tag="A")
    imgs = {0: a, 1: b_, 2: c, 3: a, 4: b_, 5: a, 6: a, 7: c, 8: b_, 9: a}
    p = PR.build_plan(base(), 10)
    data = PR.build_pdf(p, imgs, {}, "T")
    r = PdfReader(io.BytesIO(data))
    poses, objets = 0, set()
    for pg in r.pages:
        for v in pg["/Resources"]["/XObject"].values():
            poses += 1
            objets.add(v.indirect_reference.idnum)
    assert poses == 10, "dix cartes posées"
    assert len(objets) == 2, f"deux visuels distincts, {len(objets)} flux écrits"
    assert data.count(b"/Subtype /Image") + data.count(b"/Subtype/Image") == 2


def test_le_defaut_est_sans_perte_et_le_jpeg_reste_en_4_4_4():
    """AVANT : `lossless` livré DÉCOCHÉ, donc /DCTDecode par défaut, avec le
    sous-échantillonnage chroma 4:2:0 de Pillow — la définition de la
    chrominance divisée par deux sur des filets d'or de 0,3 mm."""
    assert PR.DEFAULTS["lossless"] is True, "un master d'impression est sans perte"
    p = PR.build_plan(base(), 6)
    assert p.lossless is True
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    assert data.count(b"/DCTDecode") == 0
    # et quand on DEMANDE la perte, elle reste en 4:4:4
    from PIL import JpegImagePlugin
    q = PR.build_plan(base(lossless=False), 6)
    d2 = PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T")
    r2 = PdfReader(io.BytesIO(d2))
    brut = list(r2.pages[0]["/Resources"]["/XObject"].values())[0]
    j = Image.open(io.BytesIO(brut.get_object().get_data()))
    assert JpegImagePlugin.get_sampling(j) == 0, "4:2:0 : chrominance divisée par 2"


def test_le_cartouche_dit_le_fond_perdu_reellement_pose():
    """AVANT : le cartouche imprimait « fond perdu 3 mm » alors qu'il n'en
    restait que 2 dans la gouttière — et l'écran, lui, le disait. Un fichier
    ne doit pas mentir là où l'écran dit vrai."""
    p = PR.build_plan(base(gutter_mm=4), 6)      # 4 mm pour 3 mm de fond perdu
    bord, gout = PR.bleed_mm_real(p)
    assert (bord, gout) == (3.01, 2.0), (bord, gout)
    txt = PR.slug_text(p, "Jeu", 0, "front")
    assert "2,00" in txt and "gouttière" in txt and "posé" in txt
    # gouttière portée à 6 mm : le fond perdu passe entier, et le cartouche
    # cesse de parler de gouttière
    q = PR.build_plan(base(gutter_mm=6), 6)
    assert PR.bleed_mm_real(q) == (3.01, 3.0)     # 35,5 px et 35,433 px
    txt6 = PR.slug_text(q, "Jeu", 0, "front")
    assert "gouttière" not in txt6 and "posé 3,00 mm" in txt6
    assert not [w for w in q.warnings if w["kind"] == "gouttiere_courte"]


def test_l_ecart_entre_les_deux_livrables_est_annonce():
    """« La planche et le PDF ne sont pas le même fichier, et rien ne
    prévient l'utilisateur. » Il vaut un demi-pixel — et il est ÉCRIT, des
    deux côtés, plutôt que tu."""
    p = PR.build_plan(base(), 6)
    assert PR.bleed_mm_real(p, raster=False) == (3.01, 2.0)
    assert PR.bleed_mm_real(p, raster=True) == (3.01, 1.99)
    px_pdf = PR.bleed_px_real(p, raster=False)
    px_png = PR.bleed_px_real(p, raster=True)
    assert abs(px_pdf[1] - px_png[1]) <= 0.5, "l'écart doit rester sous un demi-pixel"
    d = PR.plan_dict(p)
    assert d["bleed_mm_real"] == [3.01, 2.0]
    assert d["bleed_mm_raster"] == [3.01, 1.99]
    # et chaque livrable annonce SA valeur
    assert "1,99" in PR.slug_text(p, "Jeu", 0, "front", raster=True)
    assert "2,00" in PR.slug_text(p, "Jeu", 0, "front", raster=False)


def test_les_trois_cadres_sont_emboites_dans_le_pdf():
    """La moitié mesurable du cahier des charges dit « fond perdu ET zone de
    sécurité ». Les trois sont donc DANS le fichier, emboîtés :
    /BleedBox > /TrimBox > /ArtBox — pas seulement dessinés à l'écran."""
    p = PR.build_plan(base(artbox="safe"), 8)
    data = PR.build_pdf(p, {i: carte() for i in range(8)}, {}, "T")
    r = PdfReader(io.BytesIO(data))
    assert len(r.pages) == 2
    inset = (p.geom.safe_off_px[0] - p.geom.bleed_off_px[0]) * 72.0 / p.dpi
    assert inset > 0
    for i, page in enumerate(r.pages):
        b_ = [float(v) for v in page.bleedbox]
        t = [float(v) for v in page.trimbox]
        a = [float(v) for v in page.artbox]
        assert b_[0] < t[0] < a[0] and b_[1] < t[1] < a[1], f"page {i}"
        assert b_[2] > t[2] > a[2] and b_[3] > t[3] > a[3], f"page {i}"
        assert abs((a[0] - t[0]) - inset) < 0.01, f"page {i}: ArtBox != zone sûre"
    # et le mode « = TrimBox » reste disponible, sans surprise
    q = PR.build_plan(base(artbox="trim"), 8)
    r2 = PdfReader(io.BytesIO(PR.build_pdf(q, {i: carte() for i in range(8)},
                                           {}, "T")))
    assert [float(v) for v in r2.pages[0].artbox] == \
        [float(v) for v in r2.pages[0].trimbox]


def test_le_diagnostic_voyage_avec_le_fichier():
    """« Le diagnostic est honnête à l'écran ; il ne laisse aucune trace dans
    le PDF, là où l'imprimeur le lira. » Il y est maintenant."""
    p = PR.build_plan(base(gutter_mm=4), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "Nouveau jeu")
    md = PdfReader(io.BytesIO(data)).metadata
    mots = str(md.get("/Keywords") or "")
    assert "il en faudrait 6" in mots, "l'avertissement de gouttière absent"
    assert "reperage" in mots and "sans perte" in mots
    assert "zone sure" in mots and "ArtBox" in mots and "300 DPI" in mots
    # `/Subject` COURT et complet : beaucoup de portails d'impression le
    # tronquent à l'affichage, et c'était la ligne la plus utile qui sautait.
    sujet = str(md.get("/Subject") or "")
    assert len(sujet) <= 250, f"{len(sujet)} caractères : ce champ sera tronqué"
    assert "Poker 63 x 88 mm" in sujet and "744x1039 px" in sujet
    assert "300 DPI" in sujet and "fond perdu posé" in sujet
    # et le MÊME diagnostic, lisible par une MACHINE : le DocInfo hérité ne
    # suffit pas, les chaînes de prépresse modernes ne le lisent plus.
    assert b"<x:xmpmeta" in data and b"cardforge:mesures" in data
    xmp = data[data.find(b"<?xpacket"):data.find(b"<?xpacket end")]
    for cle in (b"fond_perdu_pose_bord_mm", b"fond_perdu_pose_gouttiere_mm",
                b"gouttiere_pt", b"reperes_en_gouttiere", b"intention",
                b"conformite_pdfx", b"zone_sure_px", b"avertissements"):
        assert cle in xmp, cle


def test_la_grille_de_coupe_est_annoncee_en_millimetres():
    """La coupe tombe à 39,995 mm et non à 40,000 : c'est la conséquence
    directe de la règle « la toile fait autorité ». Ce n'est pas caché — le
    plan sert les positions RÉELLES, et l'écran les affiche."""
    p = PR.build_plan(base(), 6)
    d = PR.plan_dict(p)
    assert d["cut_mm_x"] == [39.9947, 102.9867, 106.9867, 169.9787]
    assert len(d["cut_mm_y"]) == 6
    xs = sorted({round(s[0] / p.dpi * 25.4, 4) for s in PR.mark_segments(p)
                 if abs(s[0] - s[2]) < 1e-6})
    assert xs == d["cut_mm_x"], "l'écran doit annoncer les positions du fichier"
    # les deux axes passent par LA MÊME formule : l'écart entre eux n'est que
    # le résidu d'arrondi de px(63) et de px(88), pas deux chemins distincts.
    assert CT.px(63, 300) == 744 and CT.px(88, 300) == 1039
    assert round(744 - 63 / 25.4 * 300, 3) == -0.094
    assert round(1039 - 88 / 25.4 * 300, 3) == -0.37


def test_les_douze_formats_tiennent_dans_le_panneau():
    """« La table annonce LES 12 formats et n'en montre que 9. » Le titre est
    maintenant COMPTÉ, et la boîte est assez haute pour douze lignes."""
    assert len(CT.FORMATS) == 12
    racine = pathlib.Path(__file__).resolve().parents[2]
    src = (racine / "frontend/cardforge/js/mod-print.js").read_text(encoding="utf-8")
    assert "CF.FORMATS.length" in src, "le compte doit être calculé, pas écrit"
    assert '"les 12"' not in src and "'les 12'" not in src
    feuille = (racine / "frontend/cardforge/css/mod-print.css").read_text(
        encoding="utf-8")
    m = re.search(r"cf-print-fmt-scroll\s*\{[^}]*max-height:\s*(\d+)px", feuille)
    assert m, "hauteur de la table introuvable"
    # une ligne mesure 5 + 5 de padding + ~13 de texte + 1 de filet = 24 px
    assert int(m.group(1)) >= 12 * 24, \
        f"{m.group(1)} px : les douze lignes ne tiennent pas sans défiler"


def test_le_controle_avant_vol_leve_les_regles_de_fichier():
    """Un vrai contrôle avant vol lève d'abord deux alertes : police non
    incorporée, et absence d'intention de sortie. Elles sont contrôlées ICI,
    sur ce qui sera réellement écrit — et affichées au même endroit que les
    cartes fautives."""
    out = PR.preflight(base(n_cards=6, intent="none", lossless=False,
                            mark_space="rgb", slots=[], cards=[]))
    kinds = {r["kind"]: r for r in out["rows"]}
    assert kinds["intention_de_sortie"]["level"] == "warn"
    assert kinds["compression"]["level"] == "warn"
    assert kinds["police_incorporee"]["level"] == "ok"
    assert "0 objet /Font" in kinds["police_incorporee"]["message"]
    assert "reperes_hors_reperage" in kinds
    bon = PR.preflight(base(n_cards=6, gutter_mm=6, slots=[], cards=[]))
    k2 = {r["kind"]: r for r in bon["rows"]}
    assert k2["intention_de_sortie"]["level"] == "ok"
    assert "588 octets" in k2["intention_de_sortie"]["message"]
    assert k2["compression"]["level"] == "ok"
    # NEUF règles de FICHIER tenues : DÉRIVE TOLÉRÉE DES REPÈRES, intention,
    # conformité PDF/X, densité inscrite, ROGNE ÉCRITE, ZONE SÛRE ÉCRITE,
    # calques optionnels, police, compression. Le compte est celui des lignes
    # rendues, pas un chiffre écrit à la main.
    assert bon["errors"] == 0
    assert bon["passed"] == len([r for r in bon["rows"] if r["level"] == "ok"])
    assert bon["passed"] == 9, [r["kind"] for r in bon["rows"]]
    assert "1.50 mm de la rogne" in k2["reperes_hors_carte"]["message"]
    assert "62.9920" in k2["rogne_ecrite"]["message"]
    assert "aucune revendication PDF/X" in k2["conformite_pdfx"]["message"]
    assert "11811" in k2["densite_inscrite"]["message"]
    assert "/OCProperties" in k2["calques_optionnels"]["message"]
    # sans calques, la règle disparaît — elle ne décrit que ce qui est écrit.
    sans = PR.preflight(base(n_cards=6, gutter_mm=6, layers=False,
                             slots=[], cards=[]))
    assert "calques_optionnels" not in {r["kind"] for r in sans["rows"]}
    assert sans["passed"] == 8
    # LA ZONE SÛRE ÉCRITE, avec son écart signé : le cartouche annonçait
    # « 3 mm » quand l'/ArtBox pose 2,963 mm sur la hauteur.
    assert "673x969 px" in k2["zone_sure_ecrite"]["message"]
    assert "-36.7" in k2["zone_sure_ecrite"]["message"]
    # LE MIROIR N'EST UNE RÈGLE QUE QUAND IL Y A UN VERSO, et il porte alors
    # un chiffre, pas une affirmation.
    assert "miroir_recto_verso" not in kinds
    rv = PR.preflight(base(n_cards=6, gutter_mm=6, duplex=True, center=False,
                           slots=[], cards=[]))
    k3 = {r["kind"]: r for r in rv["rows"]}
    assert k3["miroir_recto_verso"]["level"] == "ok"
    assert k3["miroir_recto_verso"]["value"] == 0.0
    assert "µm" in k3["miroir_recto_verso"]["message"]


def test_le_profil_de_sortie_se_depose_sur_le_jeu():
    """Téléversé une fois, relu par /layout, /sheet et /pdf : le plan affiché
    est calculé avec le profil qui sera réellement embarqué."""
    doc = CC.create_deck("ICC", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    assert _api("GET", f"/api/cards/{did}/print/icc").json()["icc"] is None
    r = _api("POST", f"/api/cards/{did}/print/icc",
             files={"file": ("truc.icc", b"pas un profil" * 20,
                             "application/octet-stream")})
    assert r.status_code == 400 and "acsp" in r.text
    src = WIN_ICC / "CoatedFOGRA39.icc"
    if not src.exists():
        pytest.skip("aucun profil CMYK sur ce poste")
    icc = src.read_bytes()
    r = _api("POST", f"/api/cards/{did}/print/icc",
             files={"file": ("CoatedFOGRA39.icc", icc,
                             "application/octet-stream")})
    assert r.status_code == 200
    info = r.json()["icc"]
    assert info["space"] == "CMYK" and info["n"] == 4
    assert info["bytes"] == len(icc)
    r = _api("POST", f"/api/cards/{did}/print/layout",
             json={"n_cards": 6, "intent": "icc", "color": "cmyk_icc"})
    assert r.status_code == 200
    oi = r.json()["plan"]["out_intent"]
    assert oi["space"] == "CMYK" and oi["profile_bytes"] == len(icc)
    img = png_bytes(carte())
    files = [("fronts", (f"f{i}.png", img, "image/png")) for i in range(2)]
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps({"intent": "icc", "color": "cmyk_icc"})},
             files=files)
    assert r.status_code == 200
    assert r.headers["x-cf-color"] == "cmyk_icc"
    assert r.headers["x-cf-mark-space"] == "registration"
    assert r.headers["x-cf-lossless"] == "1"
    assert r.headers["x-cf-bleed-mm"] == "3.01/2.0"
    assert r.content.count(b"/DestOutputProfile") == 1
    assert _api("DELETE", f"/api/cards/{did}/print/icc").status_code == 200
    assert _api("GET", f"/api/cards/{did}/print/icc").json()["icc"] is None


def test_les_fichiers_bitmap_portent_leur_espace_et_leur_densite():
    """Un PNG qui annonce 300 DPI sans dire dans quel RVB il est ne fait que
    la moitié du travail : `pHYs` donne l'échelle, `iCCP` donne la couleur.
    Les deux sont là, sur les trois sorties bitmap."""
    p = PR.build_plan(base(), 1)
    for bits in (8, 16):
        out, mime, ext = PR.encode_image(carte(), "png", bits, 300, True, 95)
        assert mime == "image/png" and ext == "png"
        assert phys_of(out)[0] == PHYS_300DPI, bits
        i = out.find(b"iCCP")
        assert i > 0, f"{bits} bits : aucun profil embarqué"
        nom, reste = out[i + 4:].split(b"\x00", 1)
        # LE MEME NOM DANS LES DEUX ENCODEURS, ET C'EST CELUI QUE LE PROFIL SE
        # DONNE (tag `desc`). Les deux livrables du meme travail portaient deux
        # noms differents pour le meme profil — « ICC Profile » cote Pillow,
        # « sRGB IEC61966-2.1 » cote writer 16 bits — et ce second nom est
        # celui d'un fichier de reference de l'ICC que ces 588 octets ne sont
        # pas.
        assert nom == PR.icc_desc(PR.srgb_icc()).encode("latin-1"), nom
        assert nom == b"sRGB built-in", nom
        assert zlib.decompress(reste[1:])[36:40] == b"acsp"
        assert zlib.decompress(reste[1:])[16:20] == b"RGB "
        assert out.find(b"iCCP") < out.find(b"IDAT"), "iCCP après IDAT"
    jpg, mime, _e = PR.encode_image(carte(), "jpeg", 8, 300, False, 95)
    assert mime == "image/jpeg"
    assert b"ICC_PROFILE" in jpg[:2000], "JPEG sans profil ICC"
    assert Image.open(io.BytesIO(jpg)).info.get("dpi") == (300, 300)
    # et la planche PNG aussi
    sheet = PR.compose_sheet(p, {0: carte()}, 0, "front", "T")
    b2 = io.BytesIO()
    sheet.save(b2, "PNG", dpi=(300, 300))
    planche = PR.png_tag_icc(b2.getvalue(), PR.srgb_icc())
    assert b"iCCP" in planche and phys_of(planche)[0] == PHYS_300DPI
    j = planche.find(b"iCCP")
    assert planche[j + 4:].split(b"\x00", 1)[0] == b"sRGB built-in"
    assert planche.find(b"iCCP") < planche.find(b"IDAT")
    # la planche reste lisible, et le profil y est toujours le meme
    im = Image.open(io.BytesIO(planche))
    im.load()
    assert im.size == tuple(p.sheet_px)
    assert im.info.get("icc_profile") == PR.srgb_icc()


def test_le_plan_annonce_ce_que_le_fichier_portera():
    """Tout chiffre affiché doit être vrai : le plan sert l'intention, l'encre
    des repères, l'espace des visuels et la compression — et le fichier les
    tient."""
    p = PR.build_plan(base(intent="fogra39", mark_space="cmyk_black",
                           color="cmyk_device"), 6)
    d = PR.plan_dict(p)
    assert d["intent"] == "fogra39" and d["out_intent"]["id"] == "FOGRA39L"
    assert d["out_intent"]["profile_bytes"] == 0
    assert d["mark_space"] == "cmyk_black" and d["color"] == "cmyk_device"
    assert d["lossless"] is True
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    r = PdfReader(io.BytesIO(data))
    assert str(r.trailer["/Root"]["/OutputIntents"][0]
               ["/OutputConditionIdentifier"]) == d["out_intent"]["id"]
    assert "0 0 0 1 K" in bloc(pdf_ops(data), "CFmarks")
    assert data.count(b"/DCTDecode") == 0


# ═══════════════════════════════════════════════════════════════════════════
# 15. TOUR 2 — LE MIROIR RECTO-VERSO, LES CALQUES, LA PAGE, LE NOM DU PROFIL
#
# Les deux contrôles avaient écrit que le miroir recto-verso restait « NON
# PROUVÉ par ce livrable [...] la mise en page est symétrique, donc le miroir
# est une opération neutre ici ». Ils n'avaient vu que le cas où le défaut ne
# se voit pas : l'imposition était centrée. Hors centrage, le verso partait
# avec tout l'espace resté de l'autre côté.
#
#   MESURE AVANT CORRECTION, sur la géométrie écrite (A4 300 DPI, poker) :
#     marge 10 mm, non centré, bord long  : 708,5354 px = 59,99 mm
#     marge  5 mm, non centré, bord long  :  35,4016 px =  3,00 mm
#     marge 10 mm, non centré, bord court :  60,2913 px =  5,11 mm
#     centré (le seul cas jugé)           :   0,0000 px
# ═══════════════════════════════════════════════════════════════════════════

def _miroir_brut(p, side):
    """La position des cases SANS le miroir d'origine — l'ancien calcul, qui
    se contentait d'inverser l'index de colonne. Sert de témoin : il DOIT
    échouer là où la grille n'est pas symétrique, sinon le test ne mesure
    rien."""
    return {i: PR.cell_rect(p, r, c)
            for r, c, i in PR.cells_for_page(p, 0, side)}


def test_le_verso_est_le_miroir_physique_du_recto_meme_sans_centrage():
    """CRITÈRE 9. Pour chaque carte, la position de son verso doit être la
    position MIROIR de son recto par rapport à l'axe de pliage. Mesuré case
    par case, sur la géométrie qui sera écrite."""
    cas = [
        dict(center=True), dict(center=False), dict(center=False, margin_mm=5),
        dict(center=False, margin_mm=0), dict(center=False, margin_mm=17),
        dict(flip="short"), dict(flip="short", center=False),
        dict(flip="short", center=False, margin_mm=3),
        dict(sheet="a3", center=False, margin_mm=7),
        dict(sheet="letter", orient="paysage", center=False),
        dict(duplex_order="grouped", center=False),
    ]
    for kw in cas:
        p = PR.build_plan(base(duplex=True, **kw), 10)
        sw, sh = float(p.sheet_px[0]), float(p.sheet_px[1])
        f = {i: PR.cell_rect(PR.side_plan(p, "front"), r, c)
             for r, c, i in PR.cells_for_page(p, 0, "front")}
        b = {i: PR.cell_rect(PR.side_plan(p, "back"), r, c)
             for r, c, i in PR.cells_for_page(p, 0, "back")}
        assert set(f) == set(b) and f, kw
        for i, (fx, fy, cw, ch) in f.items():
            bx, by = b[i][0], b[i][1]
            if p.flip == "long":
                assert abs(bx - (sw - (fx + cw))) < 1e-9, (kw, i)
                assert abs(by - fy) < 1e-9, (kw, i)
            else:
                assert abs(by - (sh - (fy + ch))) < 1e-9, (kw, i)
                assert abs(bx - fx) < 1e-9, (kw, i)
        assert PR.mirror_um(p) == 0.0, kw


def test_le_defaut_du_miroir_etait_reel_et_se_mesure_encore():
    """Le témoin : sans le miroir d'origine, l'écart mesuré vaut ce que les
    chiffres ci-dessus annoncent. Un test qui ne peut pas échouer ne prouve
    rien — celui-ci rejoue le bug."""
    attendus = [(dict(center=False, margin_mm=10), 708.5354, 59.99),
                (dict(center=False, margin_mm=5), 35.4016, 3.00)]
    for kw, px_attendu, mm_attendu in attendus:
        p = PR.build_plan(base(duplex=True, **kw), 10)
        sw = float(p.sheet_px[0])
        f, b = _miroir_brut(p, "front"), _miroir_brut(p, "back")
        pire = max(abs(b[i][0] - (sw - (f[i][0] + f[i][2]))) for i in f)
        assert abs(pire - px_attendu) < 1e-3, (kw, pire)
        assert abs(pire / 300 * 25.4 - mm_attendu) < 0.01, (kw, pire)
        # ... et la correction le ramène EXACTEMENT à zéro.
        assert PR.mirror_um(p) == 0.0


def test_le_miroir_se_relit_dans_les_octets_du_pdf():
    """La mesure ne vaut que sur le fichier : on relit les matrices `cm` des
    pages recto et verso dans le flux, et on compare."""
    for kw in (dict(center=True), dict(center=False),
               dict(center=False, margin_mm=5),
               dict(center=False, flip="short"),
               dict(center=False, duplex_order="grouped")):
        p = PR.build_plan(base(duplex=True, **kw), 6)
        im = {i: carte() for i in range(6)}
        data = PR.build_pdf(p, im, dict(im), "T")
        a = PR.pdf_audit(data, p.duplex_order)
        assert a["pages"] == 2, kw
        assert a["mirror_um"] == 0.0, (kw, a["mirror_um"])
        # et les placements existent vraiment : sinon la mesure serait vide
        r = PdfReader(io.BytesIO(data))
        assert len(PR.placements(r.pages[0])) == 6, kw
        assert len(PR.placements(r.pages[1])) == 6, kw
    # sans recto-verso, la mesure se déclare SANS OBJET au lieu d'inventer 0
    q = PR.build_plan(base(), 6)
    d1 = PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T")
    assert PR.pdf_audit(d1)["mirror_um"] == -1.0


def test_la_planche_png_du_verso_suit_le_meme_miroir_que_le_pdf():
    """WYSIWYG : les deux livrables du même travail posent le verso au même
    endroit. On compare les pixels, pas les intentions."""
    # Sans cartouche : il est volontairement NON miroir (il doit rester
    # lisible des deux côtés, et il porte « recto »/« verso »). Le mesurer
    # ici ferait échouer un test qui parle d'imposition, pas de typographie.
    p = PR.build_plan(base(duplex=True, center=False, margin_mm=10,
                           slug=False), 2)
    a = carte(tag="A")
    front = PR.compose_sheet(p, {0: a}, 0, "front", "T")
    back = PR.compose_sheet(p, {0: a}, 0, "back", "T")
    assert front.size == back.size == tuple(p.sheet_px)
    # la case du recto et celle du verso, relues sur le PLAN de chaque côté
    rf = PR.cell_rect(PR.side_plan(p, "front"), 0, 0)
    rb = PR.cell_rect(PR.side_plan(p, "back"), 0, p.cols - 1)
    assert abs(rb[0] - (p.sheet_px[0] - (rf[0] + rf[2]))) < 1e-9
    # et l'encre est bien là où le plan la place, des deux côtés
    for im, rc in ((front, rf), (back, rb)):
        x, y = int(rc[0] + rc[2] / 2), int(rc[1] + rc[3] / 2)
        assert im.getpixel((x, y)) != (255, 255, 255), "case vide"
    # le verso n'est PAS une copie du recto quand la grille est dissymétrique
    assert front.tobytes() != back.tobytes()

    # ── LA MESURE QUI TRANCHE : OÙ L'ENCRE TOMBE VRAIMENT, EN PIXELS ──────
    #    On relève les bandes d'encre sur une ligne traversant la 1re rangée,
    #    des deux côtés. Celles du verso doivent être le miroir EXACT de
    #    celles du recto, au pixel.
    W, H = front.size

    def bandes(im, y):
        px = im.load()
        on = [x for x in range(W) if px[x, y] != (255, 255, 255)]
        seg, deb = [], None
        for i, x in enumerate(on):
            if deb is None:
                deb = x
            elif x != on[i - 1] + 1:
                seg.append((deb, on[i - 1]))
                deb = x
        if deb is not None:
            seg.append((deb, on[-1]))
        return [s for s in seg if s[1] - s[0] > 50]

    y = int(rf[1] + rf[3] / 2)
    bf, bb = bandes(front, y), bandes(back, y)
    assert bf and bb, (bf, bb)
    attendu = [(W - 1 - e, W - 1 - d) for d, e in bf][::-1]
    assert bb == attendu, (bb, attendu)
    # bord long : l'axe vertical, lui, ne bouge pas d'un pixel.
    def bandes_y(im, x):
        px = im.load()
        on = [v for v in range(H) if px[x, v] != (255, 255, 255)]
        return (on[0], on[-1]) if on else None
    assert (bandes_y(front, (bf[0][0] + bf[0][1]) // 2)
            == bandes_y(back, (bb[-1][0] + bb[-1][1]) // 2))


def test_les_calques_optionnels_sont_dans_le_fichier_et_nommes():
    """« Il n'y a pas de calque optionnel (/OCProperties absent, 0
    occurrence) : un imprimeur qui veut retirer les repères ou le cartouche
    doit éditer le flux. » Il n'a plus à le faire."""
    p = PR.build_plan(base(layers=True), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    a = PR.pdf_audit(data)
    assert a["header"] == "%PDF-1.5", "le contenu optionnel est du PDF 1.5"
    assert a["ocg_count"] == 2
    assert a["ocg_names"] == ["Repères de coupe et de repérage",
                              "Cartouche de traçabilité"]
    ops = pdf_ops(data)
    assert "/OCmarks BDC" in ops and "/OCslug BDC" in ops
    # le bloc marqué historique reste : il ne remplace pas le calque, il vit
    # dedans — les mesures de gouttière faites sur /CFmarks tiennent toujours.
    assert "/CFmarks BMC" in ops and "/CFslug BMC" in ops
    assert ops.count("BDC") == ops.count("EMC") - ops.count("BMC")
    # décoché : plus une trace, et l'en-tête redescend
    q = PR.build_plan(base(layers=False), 6)
    d2 = PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T")
    b = PR.pdf_audit(d2)
    assert b["ocg_count"] == 0 and d2.count(b"/OCProperties") == 0
    assert b["header"] == "%PDF-1.4"
    assert "/CFmarks BMC" in pdf_ops(d2)


def test_les_calques_excluent_la_revendication_pdfx_et_le_disent():
    """On ne peut pas être PDF/X-3 (PDF 1.4) ET porter du contenu optionnel
    (PDF 1.5). Le fichier choisit, et l'écran l'annonce avant l'export."""
    p = PR.build_plan(base(intent="fogra39", color="cmyk_device",
                           layers=True), 6)
    d = PR.plan_dict(p)
    assert d["out_intent"]["pdfx"] is True      # l'intention le permettrait
    assert d["out_intent"]["claim"] is False    # le fichier ne le portera pas
    assert d["out_intent"]["subtype"] == PR.SRC_SUBTYPE
    kinds = {w["kind"]: w for w in p.warnings}
    assert "calques_contre_pdfx" in kinds
    assert kinds["calques_contre_pdfx"]["fix"]["layers"] is False
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    a = PR.pdf_audit(data)
    assert a["pdfx"] == "" and a["intent_subtype"] == PR.SRC_SUBTYPE
    assert b"GTS_PDFXVersion" not in data
    # LA TABLE ENTIÈRE : la revendication est portée SI ET SEULEMENT SI le
    # fichier écrit ne porte aucun calque et que l'intention décrit une presse.
    for intent, lay, attendu in (("srgb", True, ""), ("srgb", False, ""),
                                 ("fogra39", True, ""),
                                 ("fogra39", False, PR.PDFX_VERSION),
                                 ("gracol", False, PR.PDFX_VERSION),
                                 ("none", False, "")):
        pp = PR.build_plan(base(intent=intent, layers=lay), 6)
        aa = PR.pdf_audit(PR.build_pdf(pp, {i: carte() for i in range(6)},
                                       {}, "T"))
        assert aa["pdfx"] == attendu, (intent, lay, aa["pdfx"])
        assert aa["pdfx_manques"] == [], (intent, lay)
        assert (aa["ocg_count"] > 0) is lay
        assert (b"GTS_PDFXVersion" in PR.build_pdf(
            pp, {0: carte()}, {}, "T")) is bool(attendu)
    # le même plan sans calques la porte, entière
    q = PR.build_plan(base(intent="fogra39", color="cmyk_device",
                           layers=False), 6)
    assert PR.plan_dict(q)["out_intent"]["claim"] is True
    b2 = PR.pdf_audit(PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T"))
    assert b2["pdfx"] == PR.PDFX_VERSION and b2["pdfx_manques"] == []


def test_la_page_pdf_peut_etre_au_format_nominal_exact():
    """« Sa MediaBox 595,20 x 841,92 pt n'est pas du A4 ISO (595,276 x
    841,890) » : relevé aux deux duels. L'écart est de 27 µm, il est
    désormais chiffré — et annulable d'une case."""
    p = PR.build_plan(base(), 6)
    assert abs(PR.iso_gap_um(p) - 26.7) < 0.2
    d = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    a = PR.pdf_audit(d)
    assert a["media_pt"] == [0.0, 0.0, 595.2, 841.92]
    assert abs(a["iso_um"] - 26.7) < 0.2

    q = PR.build_plan(base(page_iso=True), 6)
    assert PR.iso_gap_um(q) < 1e-9
    d2 = PR.build_pdf(q, {i: carte() for i in range(6)}, {}, "T")
    a2 = PR.pdf_audit(d2)
    assert a2["media_pt"][2:] == [round(PR.mm2pt(210.0), 4),
                                  round(PR.mm2pt(297.0), 4)]
    assert a2["iso_um"] < 0.05
    # L'IMPOSITION EST CENTRÉE DEDANS : les boîtes se décalent d'un demi-écart
    # et pas d'autre chose, et elles restent emboîtées.
    r1, r2 = PdfReader(io.BytesIO(d)), PdfReader(io.BytesIO(d2))
    t1 = PR._rect(r1.pages[0], "/TrimBox")
    t2 = PR._rect(r2.pages[0], "/TrimBox")
    dx = (PR.mm2pt(210.0) - 595.2) / 2.0
    dy = (PR.mm2pt(297.0) - 841.92) / 2.0
    for i, dd in enumerate((dx, dy, dx, dy)):
        assert abs((t2[i] - t1[i]) - dd) < 5e-4, (i, t1, t2)
    # la grille ne bouge pas : même nombre de pages, mêmes boîtes, emboîtées.
    assert a2["pages"] == a["pages"] == p.out_pages
    assert a2["pages_4_boites"] == a2["pages"]
    assert a2["pages_boites_emboitees"] == a2["pages"]
    # la planche RASTER, elle, ne bouge pas d'un pixel : c'est une grille.
    assert PR.compose_sheet(q, {0: carte()}, 0, "front", "T").size == (2480, 3508)


def test_le_profil_embarque_porte_le_nom_qu_il_se_donne():
    """« Le nom promet plus que les octets » : le profil s'annonçait
    « sRGB IEC61966-2.1 », le nom du fichier de référence de l'ICC, alors
    qu'il pèse 588 octets et que son propre tag `desc` dit autre chose."""
    prof = PR.srgb_icc()
    desc = PR.icc_desc(prof)
    assert desc == "sRGB built-in" and len(prof) == 588
    assert prof[12:16] == b"mntr" and prof[36:40] == b"acsp"
    # l'identifiant de l'intention, le chunk iCCP et l'en-tête HTTP disent
    # tous les trois la même chose, et c'est ce que le profil dit de lui-même
    assert PR.INTENTS["srgb"]["id"] == desc
    assert "IEC 61966-2.1" in PR.INTENTS["srgb"]["cond"], "la colorimétrie reste dite"
    chunk = PR._iccp_chunk(prof)
    assert chunk[8:8 + len(desc)] == desc.encode("latin-1")
    for bits in (8, 16):
        out, _m, _e = PR.encode_image(carte(), "png", bits, 300, True, 95)
        i = out.find(b"iCCP")
        assert out[i + 4:].split(b"\x00", 1)[0] == desc.encode("latin-1"), bits


def test_le_fond_perdu_annonce_est_le_pire_des_deux_cotes():
    """Hors centrage, le verso n'a pas les mêmes marges que le recto :
    annoncer la mesure du recto sur un fichier recto-verso serait annoncer la
    meilleure des deux."""
    p = PR.build_plan(base(duplex=True, center=False, margin_mm=1,
                           gutter_mm=6), 6)
    front = PR.bleed_mm_real(p)
    back = PR.bleed_mm_real(PR.side_plan(p, "back"))
    pire = PR.bleed_mm_sides(p)
    assert pire[0] == min(front[0], back[0])
    assert pire[1] == min(front[1], back[1])
    d = PR.plan_dict(p)
    assert d["bleed_mm_real"] == list(pire)
    # recto seul : rien ne change, la mesure reste celle de la seule page.
    q = PR.build_plan(base(center=False, margin_mm=1, gutter_mm=6), 6)
    assert PR.bleed_mm_sides(q) == PR.bleed_mm_real(q)


def test_le_plan_expose_les_mesures_que_l_ecran_affiche():
    """Aucun chiffre du panneau ne vient d'un réglage : chacun a sa mesure
    dans le plan, et le plan est celui du backend."""
    p = PR.build_plan(base(duplex=True, center=False, layers=True), 10)
    d = PR.plan_dict(p)
    for cle in ("mirror_um", "iso_um", "page_pt", "layers", "ocg",
                "page_iso", "phys_ppm", "phys_dpi", "gutter_marks"):
        assert cle in d, cle
    assert d["mirror_um"] == 0.0
    assert d["layers"] is True and len(d["ocg"]) == 2
    assert d["page_pt"] == [595.2, 841.92]
    assert abs(d["iso_um"] - 26.7) < 0.2
    assert d["phys_ppm"] == 11811 and abs(d["phys_dpi"] - 299.9994) < 1e-4


# ══════════════════════════════════════════════════════════════════════════
# TOUR 3 — CE QUI EST AFFICHÉ DOIT ÊTRE VRAI SUR LES OCTETS
#
# Trois affirmations du panneau ne tenaient pas la mesure :
#   1. « 26,7 µm SOUS le format nominal » — la hauteur est AU-DESSUS ;
#   2. « rogne 63,00 x 88,00 mm » à côté de « 744 x 1039 px » — la /TrimBox
#      écrite vaut 62,992 x 87,969 mm, et l'écart n'était dit nulle part ;
#   3. le contrôle avant vol ne regardait JAMAIS le contenu des cartes — une
#      colonne importée qu'aucun bloc n'imprime partait au tirage en silence.
# ══════════════════════════════════════════════════════════════════════════

def test_l_ecart_a_l_iso_est_signe_et_par_axe():
    """« 26,7 µm sous le format nominal » était faux d'un axe sur deux.

    A4 sur la grille du raster : 595,20 x 841,92 pt contre 595,2756 x
    841,8898 pt d'ISO. La largeur est EN DESSOUS, la hauteur AU-DESSUS. Les
    deux chiffres sont écrits en dur ici, jamais recalculés par la formule
    qu'ils vérifient."""
    p = PR.build_plan(base(), 6)
    dx, dy = PR.iso_gap_xy_um(p)
    assert dx < 0 and dy > 0, (dx, dy)          # les deux sens, pas un seul
    assert abs(dx - (-26.7)) < 0.2, dx
    assert abs(dy - 10.7) < 0.2, dy
    # le pire des deux reste le seuil ; il ne porte plus le libellé
    assert abs(PR.iso_gap_um(p) - 26.7) < 0.2
    d = PR.plan_dict(p)
    assert d["iso_um_xy"] == [dx, dy]
    # « format nominal exact » ne s'affiche que quand les DEUX axes tombent
    q = PR.build_plan(base(page_iso=True), 6)
    assert PR.iso_gap_xy_um(q) == (0.0, 0.0)
    # et la mesure relue dans les octets dit la même chose, signe compris
    a = PR.pdf_audit(PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T"))
    assert a["iso_um_xy"][0] < 0 < a["iso_um_xy"][1], a["iso_um_xy"]
    assert abs(a["iso_um_xy"][0] - (-26.7)) < 0.2
    assert abs(a["iso_um_xy"][1] - 10.7) < 0.2


def test_la_rogne_ecrite_n_est_pas_la_rogne_nominale_et_le_dit():
    """« La TrimBox déclare 62,992 x 87,9687 mm, pas 63 x 88 mm. » Exact.

    744 px à 300 DPI valent 62,9920 mm, 1039 px valent 87,96866 mm : -8 µm et
    -31 µm du nominal. Le panneau affichait 63,00 x 88,00 à côté de 744 x 1039
    sans jamais dire que les deux colonnes diffèrent."""
    p = PR.build_plan(base(), 6)
    w, h = PR.trim_written_mm(p)
    assert abs(w - 62.9920) < 1e-4 and abs(h - 87.9687) < 1e-4, (w, h)
    dx, dy = PR.trim_gap_xy_um(p)
    assert abs(dx - (-8.0)) < 0.2 and abs(dy - (-31.3)) < 0.2, (dx, dy)
    d = PR.plan_dict(p)
    assert d["trim_um_xy"] == [dx, dy]
    # LES SEPT FORMATS IMPÉRIAUX TOMBENT JUSTE : la grille de 300 DPI est
    # entière sur les pouces. Un écart non nul y serait un bug, pas un aveu.
    for fid in ("poker_us", "bridge_us", "tarot_us", "domino", "business",
                "jumbo", "micro"):
        q = PR.build_plan(base(fmt=fid), 1)
        ex, ey = PR.trim_gap_xy_um(q)
        assert abs(ex) < 0.05 and abs(ey) < 0.05, (fid, ex, ey)


def test_la_rogne_est_relue_dans_les_octets_du_pdf():
    """La mesure ne vient pas du plan : /TrimBox moins (n-1) pas de grille,
    le pas étant relu dans les matrices `cm` des placements."""
    p = PR.build_plan(base(), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    a = PR.pdf_audit(data)
    assert a["trim_fmt"] == "poker_eu", a["trim_fmt"]
    assert abs(a["trim_cell_mm"][0] - 62.992) < 0.002, a["trim_cell_mm"]
    assert abs(a["trim_cell_mm"][1] - 87.969) < 0.002, a["trim_cell_mm"]
    assert a["trim_um_xy"][0] < 0 and a["trim_um_xy"][1] < 0, a["trim_um_xy"]
    # une carte par page : la /TrimBox EST la cellule, sans arithmétique
    q = PR.build_plan(base(sheet="card"), 1)
    b = PR.pdf_audit(PR.build_pdf(q, {0: carte()}, {}, "T"))
    assert b["trim_fmt"] == "poker_eu"
    assert abs(b["trim_cell_mm"][0] - 62.992) < 0.002, b["trim_cell_mm"]
    # mode « page entière » : rien à déduire, et on ne devine pas
    r = PR.build_plan(base(trimbox="page"), 6)
    c = PR.pdf_audit(PR.build_pdf(r, {i: carte() for i in range(6)}, {}, "T"))
    assert c["trim_cell_mm"] == [] and c["trim_fmt"] == ""


def test_une_colonne_importee_que_rien_n_imprime_nomme_la_carte_et_bloque():
    """LE MANQUE NOMMÉ PAR LES DEUX CONTRÔLES : « le contrôle avant tirage
    n'audite que la FEUILLE, jamais le CONTENU des cartes ». Une colonne
    présente dans le fichier et absente de toute maquette part au tirage sans
    un mot — 9 cartes sur 12 mentaient sur leur rareté et l'outil disait
    « bon ». La règle nomme la carte, la colonne, LA VALEUR, et elle bloque."""
    body = base()
    body["slots"] = [{"id": "title", "label": "Titre", "box": [6, 4, 50, 8]}]
    body["cards"] = [
        {"i": 0, "name": "Lanterne Sourde", "fields": {"title": "Lanterne Sourde"},
         "orphans": {"rarete": "commune"}},
        {"i": 1, "name": "Halte Brève", "fields": {"title": "Halte Brève"},
         "orphans": {"rarete": "rare"}},
    ]
    out = PR.preflight(body)
    lignes = [r for r in out["rows"] if r["kind"] == "colonne_non_imprimee"]
    assert len(lignes) == 2, lignes
    assert all(r["level"] == "err" for r in lignes)
    noms = {r["card"] for r in lignes}
    assert noms == {"Lanterne Sourde", "Halte Brève"}, noms
    # LA VALEUR MESURÉE EST DANS LE MESSAGE, pas seulement le nom du champ
    assert "commune" in [r["message"] for r in lignes
                         if r["card"] == "Lanterne Sourde"][0]
    assert "rarete" in lignes[0]["message"]
    # ET ELLE FERME LA PORTE : un tirage faux ne part pas tout seul
    v = PR.gate(body, None)
    assert v is not None and v["errors"] >= 2, v
    assert PR.gate(dict(body, force=True), None) is None
    # colonne mappée -> plus d'orphelin, plus d'erreur
    body2 = dict(body)
    body2["cards"] = [dict(c, orphans={}) for c in body["cards"]]
    assert not [r for r in PR.preflight(body2)["rows"]
                if r["kind"] == "colonne_non_imprimee"]
    assert PR.gate(body2, None) is None


def test_une_valeur_sous_un_identifiant_sans_bloc_est_nommee():
    """Le même trou, un cran plus loin : une valeur portée par la carte sous
    un identifiant qui n'est celui d'aucun bloc (bloc supprimé après le
    mappage). La donnée voyage, rien ne la pose, personne ne le dit."""
    body = base()
    body["slots"] = [{"id": "title", "label": "Titre", "box": [6, 4, 50, 8]},
                     {"id": "atk", "label": "Attaque", "box": [6, 76, 10, 8]}]
    body["cards"] = [
        {"i": 0, "name": "Relique", "fields": {"title": "Relique", "cout": "3"}},
        {"i": 1, "name": "Golem", "fields": {"title": "Golem", "atk": "7"}},
    ]
    rows = PR.preflight(body)["rows"]
    orph = [r for r in rows if r["kind"] == "champ_sans_bloc"]
    assert len(orph) == 1 and orph[0]["card"] == "Relique", orph
    assert orph[0]["slot"] == "cout" and orph[0]["level"] == "err"
    assert "3" in orph[0]["message"] and "cout" in orph[0]["message"]
    # `art`, `back`, `id` et `qty` sont réservés par P4 : jamais reprochés
    body["cards"][0]["fields"] = {"title": "Relique", "art": "a.png",
                                  "back": "d.png", "id": "c1", "qty": "3"}
    assert not [r for r in PR.preflight(body)["rows"]
                if r["kind"] == "champ_sans_bloc"]
    # CE QU'ON NE MESURE PAS, ON NE LE DIT PAS : P7 ne sait pas si la maquette
    # dessine un conteneur là où la donnée manque. Aucune règle ne le prétend.
    assert not [r for r in rows if r["kind"] == "bloc_vide"]
    assert "bloc_vide" not in pathlib.Path(PR.__file__).read_text(
        encoding="utf-8").split("CE QU'ON NE MESURE PAS")[1]


def test_le_controle_fichier_ecrit_la_rogne_reellement_posee():
    """La ligne de fichier dit la rogne ÉCRITE et son écart signé — pas le
    format nominal du catalogue."""
    rows = PR.file_checks(dict(base(), n_cards=6))
    r = [x for x in rows if x["kind"] == "rogne_ecrite"]
    assert len(r) == 1
    m = r[0]["message"]
    assert "744x1039 px" in m and "62.9920" in m
    assert "-8.0" in m and "-31.3" in m, m
    # sur un format impérial, la même ligne dit « nominal exact »
    m2 = [x for x in PR.file_checks(dict(base(fmt="poker_us"), n_cards=6))
          if x["kind"] == "rogne_ecrite"][0]["message"]
    assert "nominal exact" in m2, m2


# ══════════════════════════════════════════════════════════════════════════
# TOUR 2 — CE QU'ON AFFICHE, ON LE MESURE SUR LES OCTETS
# ══════════════════════════════════════════════════════════════════════════

def _png_samples16(data: bytes):
    """Les échantillons d'un PNG 16 bits, décodés À LA MAIN (zlib puis
    défiltrage) — le test ne doit pas croire le décodeur du produit."""
    i, ihdr, idat = 8, b"", b""
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag, payload = data[i + 4:i + 8], data[i + 8:i + 8 + ln]
        if tag == b"IHDR":
            ihdr = payload
        elif tag == b"IDAT":
            idat += payload
        i += 12 + ln
        if tag == b"IEND":
            break
    w, h, depth, ctype = struct.unpack(">IIBB", ihdr[:10])
    nch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * nch * depth // 8
    bpp = nch * depth // 8
    out, prev = bytearray(), bytearray(stride)
    pos = 0
    for _ in range(h):
        f = raw[pos]; pos += 1
        line = bytearray(raw[pos:pos + stride]); pos += stride
        for k in range(stride):
            a = line[k - bpp] if k >= bpp else 0
            b = prev[k]
            c = prev[k - bpp] if k >= bpp else 0
            x = line[k]
            if f == 1:
                line[k] = (x + a) & 255
            elif f == 2:
                line[k] = (x + b) & 255
            elif f == 3:
                line[k] = (x + (a + b) // 2) & 255
            elif f == 4:
                p_ = a + b - c
                pa, pb, pc = abs(p_ - a), abs(p_ - b), abs(p_ - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[k] = (x + pr) & 255
        out += line
        prev = line
    vals = struct.unpack(">%dH" % (len(out) // 2), bytes(out))
    return vals, (w, h, depth, nch)


def test_le_16_bits_est_un_conteneur_et_le_produit_le_MESURE():
    """LE PIÈGE QUI A FONDÉ LA RÈGLE : un audit a trouvé ailleurs un IHDR à
    16 bits sur une carte 8 bits élargie, et deux verdicts successifs se sont
    contredits parce que l'un s'était arrêté à l'en-tête.

    Ici l'élargissement est VOULU. Il n'est plus seulement écrit dans une
    phrase d'écran : `png_depth()` décompresse le fichier livré et compte, et
    ce test refait la mesure indépendamment, à la main."""
    g = CT.geom("poker_eu", 300)
    # une source qui utilise TOUS les niveaux d'une carte 8 bits
    w, h = g.canvas_px
    ligne = bytes(bytearray(v for x in range(w) for v in ((x * 256) // w,) * 3))
    im = Image.frombytes("RGB", (w, h), ligne * h)

    data, mime, ext = PR.encode_image(im, "png", 16, 300, False, 95)
    vals, (pw, ph, depth, nch) = _png_samples16(data)
    assert (pw, ph, depth, nch) == (w, h, 16, 3), "l'IHDR n'annonce pas 16 bits"
    assert len(vals) == w * h * 3
    # LA MESURE QUI COMPTE : tous les échantillons sur le réseau k*257.
    assert all((v % 257) == 0 for v in vals), "ce n'est pas une source élargie"
    distinct = len(set(vals))
    assert distinct == 256, distinct

    # ce que le PRODUIT en dit doit être exactement cela
    d = PR.png_depth(data)
    assert d["exact"] and d["declared"] == 16 and d["real_bits"] == 8
    assert d["lattice_257"] is True
    assert d["distinct"] == distinct == 256
    assert abs(d["useful_bits"] - 8.0) < 0.01
    assert d["samples"] == len(vals)

    # et le 8 bits ne prétend rien de plus : même contenu, même compte
    d8 = PR.png_depth(PR.encode_image(im, "png", 8, 300, False, 95)[0])
    assert d8["declared"] == 8 and d8["distinct"] == 256 and d8["exact"]
    assert d8["lattice_257"] is False

    # le témoin de l'audit rend la MÊME mesure (c'est lui que l'écran affiche)
    t = PR.depth_probe(g, 16)
    assert (t["declared"], t["real_bits"], t["distinct"]) == (16, 8, 256)
    assert t["lattice_257"] and t["source_levels"] == 256


def test_la_route_carte_annonce_la_profondeur_qu_elle_a_mesuree():
    """L'en-tête `X-CF-Depth` n'est pas la case cochée : c'est le fichier
    relu. Le client peut donc vérifier sans faire confiance."""
    doc = CC.create_deck("Jeu profondeur", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    img = png_bytes(carte())
    r = _api("POST", f"/api/cards/{did}/print/card",
             data={"spec": json.dumps({"card_bits": 16, "card_alpha": False})},
             files={"file": ("c.png", img, "image/png")})
    assert r.status_code == 200
    dec, reel, dist, utiles = r.headers["x-cf-depth"].split("/")
    assert (dec, reel) == ("16", "8"), r.headers["x-cf-depth"]
    d = PR.png_depth(r.content)
    assert d["distinct"] == int(dist) and abs(d["useful_bits"] - float(utiles)) < 0.005
    assert d["lattice_257"] is True
    r8 = _api("POST", f"/api/cards/{did}/print/card",
              data={"spec": json.dumps({"card_bits": 8})},
              files={"file": ("c.png", img, "image/png")})
    assert r8.headers["x-cf-depth"].split("/")[:2] == ["8", "8"]
    rj = _api("POST", f"/api/cards/{did}/print/card",
              data={"spec": json.dumps({"card_fmt": "jpeg"})},
              files={"file": ("c.png", img, "image/png")})
    assert rj.headers["x-cf-depth"] == "jpeg"


def test_la_zone_sure_ecrite_est_dite_au_micron():
    """« zone sûre 3 mm » s'affichait à côté d'une /ArtBox qui pose 2,963 mm
    de retrait sur la hauteur : 37 µm de marge annoncés que le fichier ne
    porte pas. Mesuré, écrit — dans le plan, le contrôle et le cartouche.

    Et la réponse au reproche inverse (« 969 devrait être 968 ») : la zone
    sûre est UNE conversion de la longueur 82 mm -> 968,504 px -> 969 px ;
    968 px vaudrait 81,957 mm, soit 42,7 µm TROP COURT."""
    p = PR.build_plan(base(), 6)
    g = p.geom
    assert g.safe_px == (673, 969)
    zw, zh = PR.safe_written_mm(p)
    assert abs(zw - 56.9807) < 5e-4 and abs(zh - 82.042) < 5e-4, (zw, zh)
    zx, zy = PR.safe_inset_written_mm(p)
    assert abs(zx - 3.0057) < 5e-4 and abs(zy - 2.9633) < 5e-4, (zx, zy)
    assert PR.safe_gap_xy_um(p) == (5.7, -36.7), PR.safe_gap_xy_um(p)
    # 968 px serait plus faux, dans l'autre sens
    assert abs(968 / 300 * 25.4 - 82.0) * 1000 > abs(969 / 300 * 25.4 - 82.0) * 1000

    # ce que la /ArtBox porte VRAIMENT dans le PDF écrit
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "Zone")
    pg = PdfReader(io.BytesIO(data)).pages[0]
    art = [float(v) for v in pg["/ArtBox"]]
    trim = [float(v) for v in pg["/TrimBox"]]
    assert abs((art[0] - trim[0]) / 72 * 25.4 - zx) < 1e-3
    assert abs((art[1] - trim[1]) / 72 * 25.4 - zy) < 1e-3
    # le plan, le contrôle et le cartouche disent le même chiffre
    d = PR.plan_dict(p)
    assert [round(v, 3) for v in d["safe_inset_mm"]] == [3.006, 2.963]
    assert d["safe_um_xy"] == [5.7, -36.7]
    msg = [r for r in PR.file_checks(dict(base(), n_cards=6))
           if r["kind"] == "zone_sure_ecrite"][0]["message"]
    assert "673x969 px" in msg and "3.006 / 2.963" in msg and "-36.7" in msg
    assert "écrite 3,01 / 2,96" in PR.slug_text(p, "Jeu", 0, "front")
    # et le fichier livré le porte aussi
    assert b"zone_sure_retrait_ecrit_mm" in data
    assert b"3.006/2.963" in data


def test_le_verdict_du_controle_part_dans_le_fichier_livre():
    """« Rien dans les fichiers livrés ne prouve que les règles par carte
    savent nommer une carte et sortir un chiffre. » Le verdict est écrit dans
    le PDF, en XMP, et un export FORCÉ malgré des erreurs porte l'aveu."""
    doc = CC.create_deck("Jeu verdict", {"fmt": "poker_eu", "dpi": 300})
    did = doc["id"]
    img = png_bytes(carte())
    files = [("fronts", (f"f{i}.png", img, "image/png")) for i in range(6)]
    sain = {"slots": [{"id": "title", "label": "Titre", "box": [12, 6, 39, 10]}],
            "cards": [{"i": i, "name": f"C{i}", "fields": {"title": f"C{i}"},
                       "has_art": True} for i in range(6)]}
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(sain)}, files=files)
    assert r.status_code == 200
    a = PR.pdf_audit(r.content)
    assert a["control"].startswith("controle avant vol :"), a["control"]
    assert "0 erreur(s)" in a["control"] and a["control_forced"] is False
    assert " regle(s) sur 6 carte(s) et 1 bloc(s)" in a["control"]
    assert r.headers["x-cf-forced"] == "0"
    assert "controle avant vol" in r.headers["x-cf-control"]

    # FORCÉ : le fichier sort, et il l'avoue en nommant la carte
    faute = dict(sain, slots=[{"id": "title", "label": "Titre",
                               "box": [-4, -4, 70, 10]}], force=True)
    r2 = _api("POST", f"/api/cards/{did}/print/pdf",
              data={"spec": json.dumps(faute)}, files=files)
    assert r2.status_code == 200
    a2 = PR.pdf_audit(r2.content)
    assert a2["control_forced"] is True, a2["control"]
    assert "EXPORT FORCE malgre 6 erreur(s)" in a2["control"]
    assert "C0" in a2["control"] and "zone sûre" in a2["control"]
    assert r2.headers["x-cf-forced"] == "1"
    # l'aveu est DANS les octets, pas seulement dans la réponse HTTP
    assert b"EXPORT FORCE" in r2.content
    assert b"EXPORT FORCE" not in r.content
    # UN SEUL CONTRÔLE PAR EXPORT — mesuré, pas relu dans le source : la
    # porte et le tampon partagent la même mesure. Deux appels, c'étaient
    # deux verdicts qui pouvaient diverger sur la même demande.
    vrai, n = PR.preflight, []
    PR.preflight = lambda *a, **k: (n.append(1), vrai(*a, **k))[1]
    try:
        r3 = _api("POST", f"/api/cards/{did}/print/pdf",
                  data={"spec": json.dumps(sain)}, files=files)
    finally:
        PR.preflight = vrai
    assert r3.status_code == 200 and len(n) == 1, len(n)


def test_la_moitie_mesurable_300_dpi_fond_perdu_zone_sure_sur_les_octets():
    """LA MOITIÉ MESURABLE DU CAHIER DES CHARGES, relue sur les fichiers
    RÉELLEMENT produits : 300 DPI, fond perdu sur les quatre côtés, zone de
    sécurité. Aucun chiffre de ce test ne vient d'une étiquette."""
    g = CT.geom("poker_eu", 300)
    im = carte()
    data, _, _ = PR.encode_image(im, "png", 8, 300, False, 95)
    # 1. la toile livrée EST la rogne + 2 x fond perdu, au pixel
    ch = {t: p for t, p in PR._png_chunks(data)}
    w, h, depth, ctype = struct.unpack(">IIBB", ch[b"IHDR"][:10])
    assert (w, h) == g.canvas_px == (815, 1110)
    assert w - g.trim_px[0] == 2 * 35.5 and h - g.trim_px[1] == 2 * 35.5
    assert abs((w - g.trim_px[0]) / 2 / 300 * 25.4 - 3.0) < 0.006
    # 2. la densité est INSCRITE, et c'est la maille entière la plus proche
    ppm = struct.unpack(">IIB", ch[b"pHYs"])
    assert ppm == (11811, 11811, 1)
    assert abs(11811 * 0.0254 - 300.0) < 0.001
    assert abs(PR.phys_dpi(300) - 299.9994) < 1e-4
    # 3. l'espace est nommé : profil ICC embarqué, pas un RVB muet
    nom = ch[b"iCCP"].split(b"\x00")[0].decode("latin-1")
    prof = zlib.decompress(ch[b"iCCP"].split(b"\x00\x00", 1)[1])
    assert prof[36:40] == b"acsp" and prof[16:20] == b"RGB "
    assert nom == PR.icc_desc(prof) != ""
    # 4. la zone sûre est dans le fichier PDF, emboîtée, et mesurée
    p = PR.build_plan(base(), 6)
    pdf = PR.build_pdf(p, {i: im for i in range(6)}, {}, "Mesure")
    pg = PdfReader(io.BytesIO(pdf)).pages[0]
    bleed = [float(v) for v in pg["/BleedBox"]]
    trim = [float(v) for v in pg["/TrimBox"]]
    art = [float(v) for v in pg["/ArtBox"]]
    assert bleed[0] < trim[0] < art[0] and bleed[1] < trim[1] < art[1]
    assert abs((trim[0] - bleed[0]) / 72 * 25.4 - 3.0057) < 1e-3
    assert abs((art[0] - trim[0]) / 72 * 25.4 - 3.0057) < 1e-3
    # 5. et la planche PNG tombe sur la planche A4 à 300 DPI, au pixel
    sheet = PR.compose_sheet(p, {i: im for i in range(6)}, 0, "front", "M")
    assert sheet.size == (2480, 3508) == PLANCHE_300["a4"]


# ══════════════════════════════════════════════════════════════════════════
# LA DÉRIVE TOLÉRÉE — relue dans les octets des DEUX livrables
# ══════════════════════════════════════════════════════════════════════════

def _segments_du_pdf(data: bytes, page: int = 0):
    """Les traits de coupe RELUS dans le flux de la page, en points PDF.
    On ne lit que le bloc balisé `/CFmarks` : un trait de cartouche n'a rien
    à faire dans une mesure de repères."""
    ops = bloc(pdf_ops(data, page), "CFmarks")
    return [tuple(float(v) for v in m)
            for m in re.findall(r"([\d.]+) ([\d.]+) m ([\d.]+) ([\d.]+) l S",
                                ops)]


def test_aucun_repere_ne_touche_une_carte_et_la_derive_est_relue_dans_le_pdf():
    """LE CHIFFRE LE PLUS DANGEREUX DE CETTE PIÈCE : la dérive de massicot
    tolérée avant que l'encre de repérage — 100 % sur les quatre plaques — ne
    se pose sur le produit fini.

    Il était AFFIRMÉ (« 2,00 mm », le fond perdu restant en gouttière) et il
    est maintenant MESURÉ, ici sur les coordonnées écrites dans le PDF et non
    sur le plan qui les a demandées."""
    p = PR.build_plan(base(), 6)
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    segs = _segments_du_pdf(data)
    assert len(segs) == PR.plan_dict(p)["marks_n"] == 34

    # les cellules de coupe, relues elles aussi dans les octets : /TrimBox
    # donne l'emprise, le pas de grille vient des matrices `cm` des images.
    r = PdfReader(io.BytesIO(data))
    trim = [float(v) for v in r.pages[0]["/TrimBox"]]
    poses = PR.placements(r.pages[0])
    pas_x = PR.px2pt(p.cell_px[0] + p.gutter_px, p.dpi)
    pas_y = PR.px2pt(p.cell_px[1] + p.gutter_px, p.dpi)
    cw = PR.px2pt(p.cell_px[0], p.dpi)
    chh = PR.px2pt(p.cell_px[1], p.dpi)
    assert len(poses) == 6
    cells = [(trim[0] + c * pas_x, trim[1] + rr * pas_y, cw, chh)
             for rr in range(p.rows) for c in range(p.cols)]

    # l'ÉPAISSEUR déclarée, relue dans le flux : l'encre déborde d'un demi
    # filet de part et d'autre, et ce demi-filet compte dans la distance.
    ops = bloc(pdf_ops(data), "CFmarks")
    demi = float(re.search(r"([\d.]+) w", ops).group(1)) / 2.0
    assert abs(demi * 2 - 0.7087) < 1e-3            # 0,25 mm

    def distance(seg):
        x0, y0, x1, y1 = seg
        ax0, ax1 = min(x0, x1) - demi, max(x0, x1) + demi
        ay0, ay1 = min(y0, y1) - demi, max(y0, y1) + demi
        d = []
        for cx, cy, w, h in cells:
            dx = max(cx - ax1, ax0 - (cx + w), 0.0)
            dy = max(cy - ay1, ay0 - (cy + h), 0.0)
            d.append((dx * dx + dy * dy) ** 0.5)
        return min(d)

    pire = min(distance(s) for s in segs) / 72 * 25.4
    assert abs(pire - 1.00) < 0.01, pire
    assert abs(pire - PR.mark_clearance_mm(p)) < 0.01
    # ZÉRO trait touche une carte, dans les octets comme dans le plan
    assert sum(1 for s in segs if distance(s) <= 1e-9) == 0
    assert PR.mark_touch(p) == 0
    # et le produit sait la relire tout seul, au même chiffre : c'est cette
    # lecture-là, pas le réglage, qui alimente le panneau d'audit.
    assert PR.pdf_audit(data)["mark_clearance_mm"] == 1.0
    assert PR.mark_clearance_bytes(r.pages[0]) == (1.0, 34, 0)
    vieux = PR.build_pdf(PR.build_plan(base(mark_safe=False), 6),
                         {i: carte() for i in range(6)}, {}, "T")
    assert PR.pdf_audit(vieux)["mark_clearance_mm"] == 0.0
    assert PR.pdf_audit(vieux)["mark_touch"] == 14

    # ── ET LE CHIFFRE PART AVEC LE FICHIER ────────────────────────────────
    #   Il était affirmé à l'écran et absent du livrable. Il est maintenant
    #   dans le XMP (lisible par une machine) ET dans le cartouche (lisible
    #   par l'imprimeur), des deux côtés du réglage.
    for octets, attendu, touche in ((data, b"1.00", b"0"), (vieux, b"0.00", b"14")):
        assert (b"<cardforge:reperes_derive_toleree_mm>" + attendu
                + b"</cardforge:reperes_derive_toleree_mm>") in octets
        assert (b"<cardforge:reperes_touchant_une_carte>" + touche
                + b"</cardforge:reperes_touchant_une_carte>") in octets
    assert "repères à 1,00 mm de la coupe" in PR.slug_text(p, "J", 0, "front")
    # priorité 8 : c'est le PREMIER segment lâché sur une planche étroite,
    # jamais la pagination ni la mesure du fond perdu.
    pri = {t: n for n, t in PR.slug_parts(p, "J", 0, "front")[0]}
    assert pri["repères à 1,00 mm de la coupe"] == 8
    assert max(pri.values()) == 8

    # ── LES TROIS STYLES, PAS SEULEMENT CELUI QU'ON REGARDE ───────────────
    #   La croix était centrée sur le coin : la moitié de chaque bras courait
    #   DANS la carte finie — exactement le défaut relevé chez la référence.
    #   Le mode « lignes » traversait les six cartes de part en part.
    for style, avant in (("crop", 14), ("cross", 48), ("line", 10)):
        vieux = PR.build_plan(base(marks=style, mark_safe=False), 6)
        neuf = PR.build_plan(base(marks=style), 6)
        assert PR.mark_touch(vieux) == avant, style
        assert PR.mark_touch(neuf) == 0, style
        assert PR.mark_clearance_mm(neuf) >= 0.4, style
        d2 = PR.build_pdf(neuf, {i: carte() for i in range(6)}, {}, "T")
        assert len(_segments_du_pdf(d2)) == len(PR.mark_segments(neuf))

    # ── ET LA MÊME GÉOMÉTRIE DANS LA PLANCHE PNG ──────────────────────────
    #   Un seul jeu de segments sert les deux livrables : on le vérifie sur
    #   les PIXELS, en comptant l'encre de repère posée dans la rogne d'une
    #   carte. Le repère est le pixel le plus sombre de la planche.
    blanche = Image.new("RGB", tuple(p.geom.canvas_px), (255, 255, 255))
    ecarts = []
    for safe in (False, True):
        q = PR.build_plan(base(mark_safe=safe), 6)
        sh = PR.compose_sheet(q, {i: blanche for i in range(6)}, 0, "front", "")
        px = sh.load()
        x0, y0, w, h = PR.cell_rect(q, 0, 0)
        bas = y0 + h                       # coupe basse de la carte (0,0)
        haut = PR.cell_rect(q, 1, 0)[1]    # coupe haute de sa voisine du bas
        col = int(round(x0))               # la colonne du trait vertical
        noirs = [y for y in range(int(bas), int(haut) + 1)
                 if px[col, y][0] < 200]
        assert noirs, "aucun trait de gouttière dans la planche"
        ecarts.append(min(noirs) - bas)
    # décoché : l'encre commence SUR la ligne de coupe. Coché : elle commence
    # un millimètre plus loin (11,81 px à 300 DPI), et c'est ce millimètre-là
    # que l'écran annonce.
    assert ecarts[0] <= 0.5, ecarts
    assert ecarts[1] >= 11.0, ecarts


def test_le_retrait_des_reperes_se_refuse_a_l_export_et_l_ecran_le_dit():
    """Un contrôle qui détecte sans refuser ne contrôle rien : décocher
    « repères hors carte » remet l'ancienne géométrie, et l'export part
    en 409 tant qu'on ne le force pas."""
    did = CC.create_deck("Jeu retrait", {"fmt": "poker_eu", "dpi": 300})["id"]
    spec = base(mark_safe=False)
    spec.update({"slots": [], "cards": [{"i": 0, "name": "C0"}]})
    pf = PR.preflight(spec)
    ligne = [r for r in pf["rows"] if r["kind"] == "reperes_sur_la_carte"]
    assert len(ligne) == 1 and ligne[0]["level"] == "err"
    assert "0,00 mm" in ligne[0]["message"]
    assert pf["errors"] >= 1 and pf["ok"] is False
    v = PR.gate(spec, None)
    assert v and v["errors"] >= 1

    files = [("fronts", ("c0.png", png_bytes(carte()), "image/png"))]
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(spec)}, files=files)
    assert r.status_code == 409, r.status_code
    assert any(x["kind"] == "reperes_sur_la_carte"
               for x in r.json()["detail"]["rows"])
    # coché (le défaut), le même export passe — la porte n'est pas un mur
    ok = dict(spec, mark_safe=True)
    r2 = _api("POST", f"/api/cards/{did}/print/pdf",
              data={"spec": json.dumps(ok)}, files=files)
    assert r2.status_code == 200
    # et l'écran porte la même mesure que le fichier
    d = PR.plan_dict(PR.build_plan(ok, 1))
    assert d["mark_clearance_mm"] == 1.0 and d["mark_touch"] == 0
    assert d["mark_safe"] is True and d["mark_keepout_mm"] == 1.0


def test_l_ecran_porte_le_meme_retrait_que_le_backend():
    """`markKeepout` / `keepOff` / `markClearance` de js/mod-print.js sont le
    MIROIR de leurs trois fonctions backend. La parité est vérifiée au pixel
    par le banc `qa/`, ici on verrouille la présence et le défaut."""
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-print.js")
    src = js.read_text(encoding="utf-8")
    for f in ("function markKeepout(", "function keepOff(",
              "function markClearance(", "function markTouch("):
        assert f in src, f
    # la formule du retrait, mot pour mot des deux côtés
    assert "Math.min(off, (g - Math.min(len, g / 2)) / 2)" in src
    # le compte de traits et la dérive sont CONFRONTÉS au backend
    assert "marks_n écran=" in src and "mark_clearance_mm écran=" in src
    # et le réglage existe des deux côtés, à la même valeur
    assert PR.DEFAULTS["mark_safe"] is True
    assert "mark_safe: true" in src


def _pose_cadre(did, frame):
    """`doc.frame` posé sur le jeu par le CŒUR (`patch_deck`) — la voie
    partagée du document, jamais un import du routeur de P2."""
    from app.services.cards.core import patch_deck, read_deck
    f = dict(read_deck(did).get("frame") or {})
    f.update(frame)
    assert patch_deck(did, {"frame": f}) is not None


# ═══════════════════ le masque de foil (phase 3c, tâche 2) ═════════════════
#
# §6.2bis-b : « vectoriel d'abord : couche spot nommée Foil, Overprint activé ;
# repli raster : PNG noir 100 % SANS anti-aliasing, 600-1200 dpi, fond perdu
# inclus ». La vérité est UNE : les millimètres de `doc.frame.seal`. Les deux
# rasterisations en dérivent, jamais l'une de l'autre (« le piège des deux
# cadres »).


def sceau(**kw):
    """Un `doc.frame.seal` de portée IMPRESSION, forme du schéma de la T1."""
    s = {"on": True, "kind": "dorure", "width_mm": 1.2,
         "scope": {"screen": True, "print": True, "mesh": False}}
    s.update(kw)
    return s


def cadre(seal=None, edge_mm=1.6, window=None):
    """Le `doc.frame` que P7 LIT — pas un import du routeur de P2."""
    f = {"edge_mm": edge_mm, "inner_mm": 5.5,
         "seal": sceau() if seal is None else seal}
    if window is not None:
        f["window"] = window
    return f


def res_of(data: bytes, page: int = 0):
    from pypdf import PdfReader
    return PdfReader(io.BytesIO(data)).pages[page]["/Resources"]


def aire(ligne: str) -> float:
    """L'aire SIGNÉE d'un tracé (formule du lacet sur ses points de contrôle).

    Approchée — les points de contrôle des béziers ne sont pas la courbe —
    mais son SIGNE est exact, et c'est lui qui compte : deux tracés de MÊME
    signe tournent dans le MÊME sens, donc la règle de remplissage NON NULLE
    les fusionnerait en une plaque pleine. C'est ce fait-là qui rend le
    pair-impair (`f*`) obligatoire pour obtenir un anneau."""
    n = [float(v) for v in re.findall(r"-?\d+\.?\d*", ligne)]
    p = list(zip(n[0::2], n[1::2]))
    return sum(p[i][0] * p[(i + 1) % len(p)][1]
               - p[(i + 1) % len(p)][0] * p[i][1]
               for i in range(len(p))) / 2.0


def chemins(ops: str):
    """Les tracés du bloc `/CFfoil` — un par ligne, en points PDF.

    Rend une liste de (minx, miny, maxx, maxy) : l'anneau est fait de DEUX
    rectangles arrondis, donc deux tracés par carte, et la boîte de chacun se
    lit sur ses points de contrôle (les béziers d'un quart d'arc ne sortent
    jamais du rectangle)."""
    out = []
    for ligne in bloc(ops, "CFfoil").split("\n"):
        if " m " not in ligne:
            continue
        n = [float(v) for v in re.findall(r"-?\d+\.?\d*", ligne)]
        xs, ys = n[0::2], n[1::2]
        out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def test_le_masque_de_foil_est_une_couche_spot_reelle_dans_le_pdf():
    """« couche spot nommée Foil, Overprint activé » — relu dans les octets.

    Le PDF ne porte pas une COULEUR dorée : il porte une ENCRE LOGIQUE
    `/Separation /Foil`, dont la transformée de teinte n'existe que pour
    l'aperçu. C'est le nom de plaque que le RIP de l'imprimeur lit."""
    p = PR.build_plan(base(sheet="card", frame=cadre()), 1)
    data = PR.build_pdf(p, {0: carte()}, {}, "T")
    ops = pdf_ops(data)
    # 1. le calque optionnel, nommé — l'imprimeur le décoche ou l'isole
    a = PR.pdf_audit(data)
    assert a["ocg_count"] == 3
    assert a["ocg_names"][2] == "Masque de foil (dorure à chaud)"
    assert "/OCfoil BDC" in ops and "/CFfoil BMC" in ops
    # 2. l'encre : une VRAIE Separation, pas un CMJN approché
    r = res_of(data)
    cs = r["/ColorSpace"]["/CSfoil"]
    assert str(cs[0]) == "/Separation"
    assert str(cs[1]) == "/Foil", "le nom de plaque est ce que l'imprimeur lit"
    assert str(cs[2]) == "/DeviceCMYK"
    fn = cs[3].get_object()
    assert int(fn["/FunctionType"]) == 2
    assert [float(v) for v in fn["/C0"]] == [0.0, 0.0, 0.0, 0.0]
    assert sum(float(v) for v in fn["/C1"]) > 0.5, "un aperçu VISIBLE"
    # 3. la surimpression, posée sur l'état graphique
    gs = r["/ExtGState"]["/GSfoil"].get_object()
    assert gs["/OP"].value is True and gs["/op"].value is True
    assert int(gs["/OPM"]) == 1
    # 4. le tracé : l'encre choisie, deux rectangles arrondis, PAIR-IMPAIR
    b = bloc(ops, "CFfoil")
    assert "/GSfoil gs" in b and "/CSfoil cs 1 scn" in b
    assert b.count(" f*") == 1, "un seul remplissage pair-impair par carte"
    assert len(chemins(ops)) == 2, "anneau = extérieur + intérieur"
    assert b.count(" c ") == 8, "4 quarts d'arc par rectangle arrondi"
    # POURQUOI LE PAIR-IMPAIR EST OBLIGATOIRE, mesuré et non épinglé : les
    # deux tracés tournent DANS LE MÊME SENS (aires signées de même signe),
    # donc la règle non nulle les fondrait en une PLAQUE PLEINE au lieu de
    # creuser l'anneau. Et l'intérieur est bien le plus petit des deux.
    aires = [aire(x) for x in b.split("\n") if " m " in x]
    assert len(aires) == 2 and aires[0] * aires[1] > 0, aires
    assert abs(aires[0]) > abs(aires[1]), aires
    assert ops.count("BDC") == ops.count("EMC") - ops.count("BMC")


def test_sans_portee_impression_le_pdf_ne_porte_aucune_trace_de_foil():
    """La portée est un interrupteur, pas une décoration : trois façons de
    l'éteindre, trois fichiers rigoureusement sans foil."""
    for quoi, f in (
        ("sans cadre du tout", None),
        ("sceau éteint", cadre(sceau(on=False))),
        ("portée impression décochée", cadre(
            sceau(scope={"screen": True, "print": False, "mesh": False}))),
        # la fenêtre posée à 1,61 mm de la coupe ne laisse que 0,01 mm : sous
        # le plancher, il n'y a PAS d'anneau étroit, il n'y a pas d'anneau.
        ("largeur tracée nulle", cadre(
            window={"x": 1.61, "y": 1.61, "w": 63 - 3.22, "h": 88 - 3.22,
                    "r": 0})),
    ):
        p = PR.build_plan(base(sheet="card", frame=f), 1)
        data = PR.build_pdf(p, {0: carte()}, {}, "T")
        assert PR.pdf_audit(data)["ocg_count"] == 2, quoi
        assert b"/Separation" not in data or b"/Foil" not in data, quoi
        assert "/CFfoil" not in pdf_ops(data), quoi
        assert b"/GSfoil" not in data, quoi
    # et la largeur nulle est DITE, pas subie
    p = PR.build_plan(base(sheet="card", frame=cadre(
        window={"x": 1.61, "y": 1.61, "w": 59.78, "h": 84.78, "r": 0})), 1)
    assert p.foil["width_mm"] == 0.0
    assert p.foil["cap_mm"] == 0.0


def test_l_anneau_de_foil_tombe_au_millimetre_ou_le_sceau_le_dessine():
    """LE CADRE DANS LEQUEL ON DESSINE, mesuré sur les octets.

    L'anneau ne s'étend PAS jusqu'au fond perdu : sa toile le couvre (le
    masque raster est une toile coupe + fond perdu), mais l'anneau lui-même
    est posé à `edge_mm` de la COUPE, exactement comme le peintre d'écran le
    pose sur `m.outer`. Un anneau tracé au bord du fond perdu, c'est du métal
    dans la chute."""
    edge, larg = 3.4, 1.2
    p = PR.build_plan(base(sheet="card", frame=cadre(edge_mm=edge)), 1)
    g = p.geom
    data = PR.build_pdf(p, {0: carte()}, {}, "T")
    ext, dedans = chemins(pdf_ops(data))
    epx = edge / 25.4 * g.dpi
    tpx = larg / 25.4 * g.dpi
    # en pixels de PLANCHE : la toile est posée en (0,0) sur `sheet=card`
    x0, y0 = g.bleed_off_px[0] + epx, g.bleed_off_px[1] + epx
    w, h = g.trim_px[0] - 2 * epx, g.trim_px[1] - 2 * epx
    att = (PR.px2pt(x0, g.dpi), PR.px2pt(g.canvas_px[1] - (y0 + h), g.dpi),
           PR.px2pt(x0 + w, g.dpi), PR.px2pt(g.canvas_px[1] - y0, g.dpi))
    for i in range(4):
        assert abs(ext[i] - att[i]) < 0.01, (i, ext, att)
    # l'anneau creuse VERS L'INTÉRIEUR de la largeur du Sceau
    t = PR.px2pt(tpx, g.dpi)
    for i, s in enumerate((+1, +1, -1, -1)):
        assert abs(dedans[i] - (att[i] + s * t)) < 0.01, (i, dedans, att)
    # et il reste DANS la coupe : jamais dans le fond perdu
    coupe = (PR.px2pt(g.bleed_off_px[0], g.dpi),
             PR.px2pt(g.bleed_off_px[1], g.dpi))
    assert ext[0] > coupe[0] + 1e-6 and ext[1] > coupe[1] + 1e-6


def test_l_anneau_suit_chaque_carte_et_ne_dore_que_le_recto():
    """Un masque de foil qui ne suivrait pas la grille poserait la dorure à
    côté des cartes. Et il ne dore QUE LE RECTO : le peintre d'écran du Sceau
    s'insère dans `paintFront`, `paintBack` ne le peint pas — poser la plaque
    au verso promettrait une dorure que l'écran ne montre nulle part."""
    p = PR.build_plan(base(frame=cadre(edge_mm=3.4), duplex=True), 6)
    assert (p.cols, p.rows, p.duplex) == (2, 3, True)
    data = PR.build_pdf(p, {i: carte() for i in range(6)},
                        {i: carte() for i in range(6)}, "T")
    tr = chemins(pdf_ops(data, 0))
    assert len(tr) == 12, "6 cartes x (extérieur + intérieur)"
    epx, t = 3.4 / 25.4 * p.dpi, 1.2 / 25.4 * p.dpi
    att = sorted({round(PR.px2pt(PR.cell_rect(p, 0, c)[0] + epx + d, p.dpi), 4)
                  for c in range(p.cols) for d in (0.0, t)})
    # 4 abscisses distinctes : 2 colonnes x (extérieur, intérieur). La
    # tolérance est celle de l'ÉCRITURE (`_pdf_num` arrondit à 1e-4 pt), pas
    # une marge de confort : 0,001 pt = 0,35 µm.
    got = sorted({v[0] for v in tr})
    assert len(got) == len(att) == 4, (got, att)
    for a, b in zip(got, att):
        assert abs(a - b) < 0.001, (got, att)
    # LE VERSO N'EN PORTE PAS UNE TRACE
    assert "/CFfoil" not in pdf_ops(data, 1), "recto seul"
    assert "/OCfoil" not in pdf_ops(data, 1)
    # ... et l'écran le DIT plutôt que de le laisser découvrir
    k = {r["kind"]: r for r in PR.file_checks(
        base(n_cards=6, duplex=True, frame=cadre(edge_mm=3.4)))}
    assert "RECTO SEUL" in k["foil_calque"]["message"]
    sans = {r["kind"]: r for r in PR.file_checks(
        base(n_cards=6, frame=cadre(edge_mm=3.4)))}
    assert "RECTO SEUL" not in sans["foil_calque"]["message"]


def test_le_masque_raster_est_un_1_bit_sans_anticrenelage():
    """« PNG noir 100 % SANS anti-aliasing, 600-1200 dpi, fond perdu inclus ».

    DEUX valeurs, pas trois : un seul pixel gris et le RIP fabrique une trame
    là où l'imprimeur attend une découpe de plaque."""
    did = CC.create_deck("Jeu foil", {"fmt": "poker_eu", "dpi": 300})["id"]
    _pose_cadre(did, cadre(edge_mm=3.4))
    r = _api("GET", f"/api/cards/{did}/print/foil-mask?dpi=600")
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"] == "image/png"
    assert "noir" in r.headers["content-disposition"]
    assert r.headers["X-CF-Foil-Ink"] == "noir=foil"
    im = Image.open(io.BytesIO(r.content))
    assert im.mode == "1", "1 bit, pas un gris déguisé"
    assert r.content[24] == 1, "profondeur 1 dans l'IHDR"
    # Le compte de valeurs est REDONDANT tant que le mode vaut « 1 » (une
    # image 1 bit ne peut pas en porter trois) : il est là pour le jour où
    # quelqu'un desserrera le mode, et c'est dit plutôt que découvert.
    vals = sorted(set(im.convert("L").get_flattened_data()))
    assert vals == [0, 255], vals
    # la toile = COUPE + FOND PERDU, à 600 dpi
    g = CT.geom("poker_eu", 600)
    assert im.size == tuple(g.canvas_px)
    # ── CE QUE LE COMPTE DE VALEURS NE PEUT PAS VOIR ──────────────────────
    #    Un seuil à DIFFUSION D'ERREUR posé sur un bord lissé rend toujours
    #    deux valeurs et toujours du 1 bit — mais il ÉMIETTE les coins en
    #    damier, et une plaque de dorure émiettée est une plaque perdue. Un
    #    anneau propre ne pose jamais plus de DEUX plages noires par ligne
    #    (ses deux montants) ; les lignes de coin sont balayées une par une.
    lu = im.convert("L").load()

    def plages(y):
        n, prev = 0, 255
        for x in range(g.canvas_px[0]):
            v = lu[x, y]
            if v == 0 and prev != 0:
                n += 1
            prev = v
        return n
    lignes = sorted(set(range(0, g.canvas_px[1], 7)) | set(range(145, 240)))
    assert max(plages(v) for v in lignes) == 2
    assert struct.unpack(">I", r.content[r.content.find(b"pHYs") + 4:
                                         r.content.find(b"pHYs") + 8])[0] \
        == PR.phys_ppm(600)
    # LE CADRE : les transitions d'une ligne médiane tombent à edge_mm de la
    # coupe, puis à edge_mm + largeur. Mesuré sur les pixels, pas déclaré.
    y = g.canvas_px[1] // 2
    ligne = [im.getpixel((x, y)) for x in range(g.canvas_px[0])]
    bords = [x for x in range(1, len(ligne)) if ligne[x] != ligne[x - 1]]
    att = [g.bleed_off_px[0] + 3.4 / 25.4 * 600,
           g.bleed_off_px[0] + (3.4 + 1.2) / 25.4 * 600]
    assert len(bords) == 4, bords
    assert abs(bords[0] - att[0]) <= 1, (bords, att)
    assert abs(bords[1] - att[1]) <= 1, (bords, att)
    # le noir est bien l'anneau, le blanc le reste
    assert ligne[bords[0] + 1] == 0 and ligne[0] == 255


def test_la_route_du_masque_refuse_en_nommant_la_raison():
    """Un masque vide n'est pas un masque : la route dit POURQUOI."""
    did = CC.create_deck("Jeu sans foil", {"fmt": "poker_eu", "dpi": 300})["id"]
    r = _api("GET", f"/api/cards/{did}/print/foil-mask")
    assert r.status_code == 409
    assert "portée impression" in r.json()["detail"]
    _pose_cadre(did, cadre(window={"x": 1.61, "y": 1.61, "w": 59.78,
                                   "h": 84.78, "r": 0}))
    r2 = _api("GET", f"/api/cards/{did}/print/foil-mask")
    assert r2.status_code == 409
    assert "0,2" in r2.json()["detail"] or "0.2" in r2.json()["detail"]
    _pose_cadre(did, cadre(edge_mm=3.4))
    r3 = _api("GET", f"/api/cards/{did}/print/foil-mask?dpi=97")
    assert r3.status_code == 400 and "600" in r3.json()["detail"]


def test_le_preflight_du_foil_nomme_ses_regles_et_donne_le_remede():
    """Le contrôle avant vol JUGE LE DOCUMENT, pas l'écran : une largeur
    qu'aucun curseur ne peut produire arrive quand même par un fichier
    modifié à la main, et elle est refusée en la nommant."""
    # sans foil : PAS UNE LIGNE de plus (les 9 règles de fichier tiennent)
    sans = PR.preflight(base(n_cards=6, gutter_mm=6, slots=[], cards=[]))
    assert not [r for r in sans["rows"] if r["kind"].startswith("foil_")]
    assert sans["passed"] == 9

    # le DÉFAUT du jeu : 1,6 mm de la coupe, DANS la zone interdite — un
    # AVERTISSEMENT avec le remède, jamais une erreur (elle bloquerait tout
    # jeu neuf qui coche « impression »).
    d = PR.preflight(base(n_cards=6, gutter_mm=6, slots=[], cards=[],
                          frame=cadre()))
    k = {r["kind"]: r for r in d["rows"]}
    assert k["foil_distance_coupe"]["level"] == "warn"
    assert d["errors"] == 0, "le jeu par défaut ne se refuse pas lui-même"
    msg = k["foil_distance_coupe"]["message"]
    assert "3,2" in msg and "1,60" in msg
    assert "edge_mm" in msg and "variance" in msg
    assert k["foil_limite_produit"]["level"] == "ok"
    assert "CMJN" in k["foil_limite_produit"]["message"]
    assert k["foil_calque"]["level"] == "ok"
    assert "PDF/X" in k["foil_calque"]["message"]
    assert "z=70" in k["foil_recouvrement"]["message"]

    # retrait au-delà de 3,2 mm : la règle passe au vert avec son chiffre
    ok = PR.preflight(base(n_cards=6, gutter_mm=6, slots=[], cards=[],
                           frame=cadre(edge_mm=3.4)))
    k2 = {r["kind"]: r for r in ok["rows"]}
    assert k2["foil_distance_coupe"]["level"] == "ok"
    assert ok["passed"] == 13

    # LE DOCUMENT MODIFIÉ À LA MAIN : 0,1 mm de trait. Erreur nommée, et la
    # porte de l'export s'appuie dessus.
    mauvais = base(n_cards=1, frame=cadre(sceau(width_mm=0.1), edge_mm=3.4),
                   slots=[], cards=[{"i": 0, "name": "C0"}])
    pf = PR.preflight(mauvais)
    k3 = {r["kind"]: r for r in pf["rows"]}
    assert k3["foil_trait"]["level"] == "err"
    assert "0,10" in k3["foil_trait"]["message"] and "0,2" in \
        k3["foil_trait"]["message"]
    assert PR.gate(mauvais, None) is not None

    # portée impression cochée mais anneau IMPOSSIBLE : dit, sans bloquer
    vide = PR.preflight(base(n_cards=6, gutter_mm=6, slots=[], cards=[],
                             frame=cadre(window={"x": 1.61, "y": 1.61,
                                                 "w": 59.78, "h": 84.78,
                                                 "r": 0})))
    k4 = {r["kind"]: r for r in vide["rows"]}
    assert k4["foil_sans_anneau"]["level"] == "warn"
    assert "reculer la fenêtre" in k4["foil_sans_anneau"]["message"]
    assert vide["errors"] == 0


def test_un_anneau_absent_nomme_SA_cause_et_pas_une_autre():
    """« Un chiffre faux vaut moins que pas de chiffre » — la règle de ce
    module, retournée contre lui.

    Deux causes ÉTRANGÈRES l'une à l'autre produisent un anneau nul, et elles
    ne se soignent pas pareil : LA PLACE (fenêtre trop près de la coupe) et LA
    LARGEUR ÉCRITE DANS LE DOCUMENT. Les confondre faisait écrire « il ne
    reste que 5,00 mm, sous le trait minimal de 0,2 mm » — un chiffre qui
    réfute sa propre phrase — et conseiller de bouger un filet qui n'y est
    pour rien."""
    # cause A : LA PLACE. La fenêtre à 1,61 mm de la coupe ne laisse rien.
    place = base(n_cards=1, slots=[], cards=[], frame=cadre(
        window={"x": 1.61, "y": 1.61, "w": 59.78, "h": 84.78, "r": 0}))
    ma = {r["kind"]: r for r in PR.preflight(place)["rows"]}["foil_sans_anneau"]
    assert ma["level"] == "warn"
    assert "il ne reste que 0,00 mm" in ma["message"]
    assert "sous le trait minimal" in ma["message"]
    assert "reculer la fenêtre" in ma["message"]

    # cause B : LA LARGEUR DU DOCUMENT, avec TOUTE la place voulue (5,00 mm).
    doc = base(n_cards=1, slots=[], cards=[],
               frame=cadre(sceau(width_mm=0), edge_mm=1.6))
    assert PR.build_plan(doc, 1).foil["cap_mm"] == 5.0, "la place ne manque pas"
    mb = {r["kind"]: r for r in PR.preflight(doc)["rows"]}["foil_sans_anneau"]
    assert mb["level"] == "warn"
    assert "largeur demandée" in mb["message"] and "0,00 mm" in mb["message"]
    # LA PHRASE QUI ÉTAIT FAUSSE, ET LE CONSEIL QUI NE SOIGNAIT RIEN
    assert "sous le trait minimal" not in mb["message"]
    assert "rapprocher le filet" not in mb["message"]
    assert "reculer la fenêtre" not in mb["message"]

    # LE MÊME PARTAGE AU 409 DE LA ROUTE — un utilisateur qui saute l'écran
    # doit lire la même cause.
    did = CC.create_deck("Jeu cause", {"fmt": "poker_eu", "dpi": 300})["id"]
    _pose_cadre(did, cadre(sceau(width_mm=0), edge_mm=1.6))
    d1 = _api("GET", f"/api/cards/{did}/print/foil-mask").json()["detail"]
    assert "largeur demandée" in d1 and "rapprocher le filet" not in d1
    _pose_cadre(did, cadre(window={"x": 1.61, "y": 1.61, "w": 59.78,
                                   "h": 84.78, "r": 0}))
    d2 = _api("GET", f"/api/cards/{did}/print/foil-mask").json()["detail"]
    assert "reculer la fenêtre" in d2 and "largeur demandée" not in d2


def test_un_retrait_negatif_ne_dore_pas_la_carte_du_voisin():
    """Mesuré avant correctif, poker 2x3, `edge_mm: -5` édité à la main :
    l'anneau sortait de 5 mm HORS de la rogne et celui de la colonne 1
    traversait le trait de coupe de la colonne 0 de 1,00 mm — pendant que le
    contrôle conseillait paisiblement « acceptez la variance ».

    UNE PLAQUE N'EST PAS UN ÉCRAN : la géométrie est ramenée au trait de
    coupe (le plancher que `LIMITS.edge_mm` tient déjà des deux côtés de P2),
    et le DOCUMENT est avoué au lieu d'être réparé en silence."""
    spec = base(frame=cadre(edge_mm=-5), slots=[],
                cards=[{"i": 0, "name": "C0"}])
    p = PR.build_plan(spec, 6)
    assert (p.cols, p.rows) == (2, 3)
    assert p.foil["edge_mm"] == 0.0 and p.foil["edge_asked_mm"] == -5.0
    data = PR.build_pdf(p, {i: carte() for i in range(6)}, {}, "T")
    sh = p.sheet_px[1]
    cases = [(PR.px2pt(x, p.dpi), PR.px2pt(sh - (y + ch), p.dpi),
              PR.px2pt(x + cw, p.dpi), PR.px2pt(sh - y, p.dpi))
             for r in range(p.rows) for c in range(p.cols)
             for x, y, cw, ch in [PR.cell_rect(p, r, c)]]
    tr = chemins(pdf_ops(data))
    assert len(tr) == 12
    for t in tr:
        assert any(a - 1e-3 <= t[0] and t[2] <= c2 + 1e-3
                   and b - 1e-3 <= t[1] and t[3] <= d2 + 1e-3
                   for a, b, c2, d2 in cases), ("dorure hors de sa carte", t)
    # ... et le document est AVOUÉ, avec son chiffre, et il BLOQUE
    k = {r["kind"]: r for r in PR.preflight(spec)["rows"]}
    assert k["foil_retrait_negatif"]["level"] == "err"
    assert "-5,00" in k["foil_retrait_negatif"]["message"]
    assert "voisine" in k["foil_retrait_negatif"]["message"]
    assert PR.gate(spec, None) is not None


def test_la_porte_du_foil_ne_depend_pas_des_cartes():
    """`preflight_safe` se tait quand la demande ne porte ni bloc ni carte :
    il n'y a alors rien à juger PAR CARTE, et c'est juste. Mais le masque de
    foil se calcule du SEUL document — un trait sous le minimum de la presse
    est une erreur avec zéro carte comme avec trois cents. Sans cette
    porte-là, un client qui n'envoie pas ses cartes obtenait un 200 et un
    anneau que l'imprimeur refuse."""
    spec = base(frame=cadre(sceau(width_mm=0.1), edge_mm=3.4))
    assert "slots" not in spec and "cards" not in spec
    assert PR.preflight_safe(spec, None) is None, "rien à juger PAR CARTE"
    v = PR.gate(spec, None)
    assert v is not None and v["errors"] == 1
    assert v["rows"][0]["kind"] == "foil_trait"
    # sans foil, la porte reste EXACTEMENT ce qu'elle était : ouverte.
    assert PR.gate(base(), None) is None
    assert PR.gate(base(frame=cadre(edge_mm=3.4)), None) is None

    did = CC.create_deck("Jeu porte foil", {"fmt": "poker_eu", "dpi": 300})["id"]
    _pose_cadre(did, cadre(sceau(width_mm=0.1), edge_mm=3.4))
    files = [("fronts", ("c0.png", png_bytes(carte()), "image/png"))]
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(base())}, files=files)
    assert r.status_code == 409, r.status_code
    assert any(x["kind"] == "foil_trait" for x in r.json()["detail"]["rows"])
    # `force` reste la seule sortie, et elle est explicite
    r2 = _api("POST", f"/api/cards/{did}/print/pdf",
              data={"spec": json.dumps(base(force=True))}, files=files)
    assert r2.status_code == 200


def test_le_deck_par_defaut_avec_foil_part_quand_meme():
    """Le corollaire du choix « avertir, pas refuser » : un jeu neuf qui
    coche « impression » obtient son PDF, et le fichier porte le foil."""
    did = CC.create_deck("Jeu défaut", {"fmt": "poker_eu", "dpi": 300})["id"]
    _pose_cadre(did, cadre())
    spec = base(sheet="card", slots=[], cards=[{"i": 0, "name": "C0"}])
    r = _api("POST", f"/api/cards/{did}/print/pdf",
             data={"spec": json.dumps(spec)},
             files=[("fronts", ("c0.png", png_bytes(carte()), "image/png"))])
    assert r.status_code == 200, r.text[:400]
    assert r.headers["X-CF-Foil"].startswith("Foil ")
    assert "Masque de foil" in r.headers["X-CF-Layers"]
    assert "/CFfoil BMC" in pdf_ops(r.content)


def test_p7_lit_le_sceau_du_document_sans_importer_p2():
    """RÈGLE 8 : P7 n'importe pas le routeur de P2. Le Sceau est de l'ÉTAT
    PARTAGÉ (`doc.frame.seal`) ; P7 en tient un lecteur LOCAL, dont la parité
    est prouvée ici contre `frame.seal_of` — le même patron que
    `forge3d._sceau_du_doc` livré en T3.

    ET LA DIVERGENCE EST VOULUE : `seal_of` normalise un CORPS DE REQUÊTE et
    LÈVE hors bornes (400 nommant la borne) ; le lecteur de P7 normalise un
    DOCUMENT DÉJÀ ÉCRIT et ne lève jamais — sans quoi une largeur de
    0,1 mm posée à la main sortirait en 400 au lieu de la ligne d'erreur
    nommée que le contrôle avant vol doit rendre."""
    from app.services.cards import frame as P2
    src = pathlib.Path(PR.__file__).read_text(encoding="utf-8")
    # AUCUNE INSTRUCTION d'import de P2 — la prose du fichier, elle, a le
    # droit de citer celle qu'elle refuse d'écrire (c'est même son travail).
    assert not re.search(r"^\s*(?:from\s+\.frame\s+import|from\s+\.\s+"
                         r"import\s+frame|import\s+.*frame)",
                         src, re.M)
    for brut in (None, {}, {"on": True}, {"on": "oui"}, {"kind": "dorure"},
                 {"kind": "inconnu"}, {"width_mm": None}, {"width_mm": 6},
                 {"width_mm": 0.2}, {"scope": {"print": True}},
                 {"scope": {"screen": False, "mesh": True}},
                 {"on": True, "scope": {"print": True, "screen": False}}):
        a, b = P2.seal_of(brut), PR.foil_of({"seal": brut})
        assert (a["on"], a["kind"], a["width_mm"]) == \
            (b["on"], b["kind"], b["width_mm"]), brut
        # LES TROIS PORTÉES, pas seulement celle qui sert ici : `foil_of` est
        # un miroir du schéma, pas un extracteur. Ne comparer que `print`
        # laissait `screen` et `mesh` dériver sans qu'une ligne rougisse.
        for k in ("screen", "print", "mesh"):
            assert a["scope"][k] == b[k], (brut, k)
    # la divergence, épinglée dans les deux sens
    with pytest.raises(ValueError):
        P2.seal_of({"width_mm": 0.1})
    assert PR.foil_of({"seal": {"width_mm": 0.1}})["width_mm"] == 0.1
    # ... et la SECONDE divergence, du même genre : un nombre ILLISIBLE (NaN,
    # infini, chaîne) fait lever `seal_of` et retombe au DÉFAUT ici. Même
    # raison : P7 lit un document déjà écrit, il ne le refuse pas.
    with pytest.raises(ValueError):
        P2.seal_of({"width_mm": "large"})
    for sale in ("large", float("nan"), float("inf"), [], {}):
        assert PR.foil_of({"seal": {"width_mm": sale}})["width_mm"] == 1.2

    # ── LES CINQ CONSTANTES JUMELLES ──────────────────────────────────────
    #    Un miroir dont la couture n'est pas épinglée dérive le jour où
    #    quelqu'un édite frame.py en ne mettant à jour que test_cards_frame.
    assert PR.FOIL_MIN_MM == P2.SEAL_MIN_MM
    assert PR.FOIL_BAND_MIN_MM == P2.BAND_MIN_MM
    assert list(PR.FOIL_KINDS) == [k["id"] for k in P2.SEAL_KINDS]
    assert PR.FOIL_DEFAULTS == P2.SEAL_DEFAULTS
    # `FOIL_TRIM_MM` n'a PAS de jumeau dans frame.py — c'est une contrainte
    # d'IMPRIMEUR, que P2 n'a aucune raison de connaître. Elle est donc
    # épinglée sur la spec, sa seule source. (Idem pour l'espacement entre
    # zones, sans objet ici : un anneau est UNE zone — et l'écran le dit.)
    sp = (pathlib.Path(__file__).resolve().parents[2] / "docs" / "superpowers"
          / "specs" / "2026-08-19-cardforge-universel-design.md"
          ).read_text(encoding="utf-8")
    assert "distance au trait de\n  coupe ≥ 3,2 mm" in sp
    assert "espacement entre zones ≥ 0,25 mm" in sp
    assert PR.FOIL_TRIM_MM == 3.2

    # ── LES NOMBRES, SUR LES DOUZE FORMATS ────────────────────────────────
    CAS = ((1.6, 1.2), (3.4, 2.0), (0.5, 6.0), (8.0, 0.2), (0.0, 3.0),
           (2.0, 2.005))
    mord = 0
    for fmt in CT.FORMATS:
        g = CT.geom(fmt, 300)
        for edge, larg in CAS:
            f = {"edge_mm": edge, "seal": sceau(width_mm=larg)}
            m = P2.frame_metrics(g, 0.9, 1.1, edge, 5.5, P2._win_of(None, g),
                                 P2.seal_of(f["seal"]))
            fo = PR.foil_plan(f, g)
            assert CT.rnd(fo["width_mm"], 2) == m["seal_mm"][0], (fmt, edge, larg)
            assert fo["cap_mm"] == m["seal_mm"][1], (fmt, edge, larg)
            assert [CT.rnd(v, 2) for v in fo["px"]] == m["seal_px"], (fmt, edge)
            if fo["cap_mm"] < larg:
                mord += 1
    assert mord >= 1, "aucun cas où la borne de format MORD : elle ne prouve rien"

    # ── LA COUTURE POSÉE *DANS* LA BANDE QUE LE PLANCHER TIENT ────────────
    #    Les cas ci-dessus tombent tous SUR 0,00 ou bien au-dessus de 0,2 :
    #    ils ne disent rien de l'intervalle (0 ; 0,2) — celui-là même que le
    #    plancher de la T1 existe pour refuser. Les deux fenêtres qui suivent
    #    y posent le résultat BRUT, à la main : 0,10 (refusé -> 0,00) et 0,21
    #    (accepté tel quel). Muter le plancher d'un côté fait diverger les
    #    deux moitiés, ce qu'aucune autre ligne de cette suite ne voit.
    g = CT.geom("poker_eu", 300)
    for edge, win, att in (
            (1.6, {"x": 1.70, "y": 1.70, "w": 59.60, "h": 84.60, "r": 0}, 0.0),
            (1.6, {"x": 1.81, "y": 1.81, "w": 59.38, "h": 84.38, "r": 0}, 0.21),
            (1.61, {"x": 1.61, "y": 1.61, "w": 59.78, "h": 84.78, "r": 0}, 0.0)):
        f = {"edge_mm": edge, "window": win, "seal": sceau(width_mm=1.2)}
        m = P2.frame_metrics(g, 0.9, 1.1, edge, 5.5, P2._win_of(win, g),
                             P2.seal_of(f["seal"]))
        fo = PR.foil_plan(f, g)
        assert fo["cap_mm"] == att == m["seal_mm"][1], (win["x"], fo["cap_mm"])
        assert CT.rnd(fo["width_mm"], 2) == m["seal_mm"][0] == att
        assert [CT.rnd(v, 2) for v in fo["px"]] == m["seal_px"], win["x"]


def _js_fn(src: str, nom: str) -> str:
    """Le SOURCE d'une fonction de `mod-print.js`, accolades équilibrées.
    Même extracteur que le banc de `test_cards_frame.py`."""
    i = src.index("function " + nom + "(")
    j = src.index("{", i)
    n = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            n += 1
        elif src[k] == "}":
            n -= 1
            if n == 0:
                return src[i:k + 1]
    raise AssertionError("accolades non equilibrees pour " + nom)


BANC_FOIL = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE + "\n})();")();
const out = [];
for (const c of CAS) out.push(mod.run(c.seal, c.foil, c.layers));
process.stdout.write(JSON.stringify(out));
"""


def _peint_foil(tmp_path, cas: list) -> list:
    """Fait tourner LA VRAIE `paintFoil` de mod-print.js.

    UN GREP DE PROSE EST UN CLIQUET, PAS UNE PREUVE — la leçon de la T3,
    re-payée ici : la version « chaînes présentes dans le fichier » de ce
    test laissait passer DEUX mutants (la condition des deux causes forcée à
    `true`, et l'aveu du retrait négatif désactivé) parce que les phrases
    restaient dans les octets pendant que la BRANCHE ne s'exécutait plus.
    Le banc juge le HTML rendu, pas le fichier lu."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'écran ne peut pas tourner")
    src = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
           / "js" / "mod-print.js").read_text(encoding="utf-8")
    code = "\n".join([
        'let __h = "", SEAL = null, BPLAN = null, LAYERS = true, FOILDPI = 600;',
        'const __btn = { disabled: null };',
        'function q(s){ if (s === \'[data-role="foil"]\') '
        'return { set innerHTML(v){ __h = v; } };'
        ' if (s === \'[data-act="foilmask"]\') return __btn; return null; }',
        'const CF = { get: (p, d) => (p === "frame.seal" ? SEAL : d) };',
        'function st(){ return { layers: LAYERS }; }',
        # `esc` porte des « &amp; » : couper au premier point-virgule le
        # tronquerait au milieu d'une entité. L'ancre est sa DERNIÈRE.
        re.search(r"const esc = \(s\).*?&quot;\"\);", src, re.S).group(0),
        re.search(r"const nf = \(v, n\) => \{.*?\n  \};", src, re.S).group(0),
        re.search(r"const nfx = [^;]+;", src).group(0),
        _js_fn(src, "paintFoil"),
        "return { run: (seal, foil, layers) => { SEAL = seal; "
        "BPLAN = foil ? { foil: foil } : null; LAYERS = layers !== false; "
        '__h = ""; __btn.disabled = null; paintFoil(); '
        "return { html: __h, off: __btn.disabled }; } };",
    ])
    js = tmp_path / "foil.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_foil.mjs"
    banc.write_text(BANC_FOIL, encoding="utf-8")
    conf = tmp_path / "cas.json"
    conf.write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def _foil_plan_js(**kw):
    """Le bloc `plan.foil` tel que le backend le publie — construit ICI par
    `plan_dict`, jamais écrit à la main : deux tables de champs, ce serait
    deux contrats."""
    f = {"edge_mm": kw.pop("edge_mm", 1.6), "inner_mm": 5.5,
         "seal": sceau(width_mm=kw.pop("width_mm", 1.2))}
    if "window" in kw:
        f["window"] = kw.pop("window")
    return PR.plan_dict(PR.build_plan(base(frame=f), 1))["foil"]


def test_l_ecran_JUGE_les_deux_causes_et_le_retrait_negatif(tmp_path):
    """Le banc exécute `paintFoil` : ce qui est mesuré est le HTML rendu.

    Les trois branches que le contrôle avant vol distingue doivent l'être à
    l'écran aussi, et AVANT l'export — c'est tout l'objet de la tâche."""
    cas = [
        {"seal": sceau(), "foil": _foil_plan_js(edge_mm=3.4)},
        {"seal": sceau(), "foil": _foil_plan_js(
            window={"x": 1.61, "y": 1.61, "w": 59.78, "h": 84.78, "r": 0})},
        {"seal": sceau(), "foil": _foil_plan_js(width_mm=0)},
        {"seal": sceau(), "foil": _foil_plan_js(edge_mm=-5)},
        # LE PLAN QUI DATE : le document dit « plus d'impression », le plan
        # du backend dit encore « live » (il arrive 320 ms plus tard). Les
        # DEUX doivent être d'accord pour que le bouton vive — sans quoi le
        # clic part chercher un masque que la route refuse en 409.
        {"seal": sceau(scope={"screen": True, "print": False, "mesh": False}),
         "foil": _foil_plan_js(edge_mm=3.4)},
    ]
    sain, place, larg, neg, hors = _peint_foil(tmp_path, cas)
    # 1. tout va bien : l'anneau est décrit, le bouton est actif
    assert sain["off"] is False and "Anneau" in sain["html"]
    assert "3,40 mm" in sain["html"] and "au-delà des 3,2" in sain["html"]
    # 2. LA PLACE manque — et on parle de la fenêtre
    assert place["off"] is True
    assert "reculer la fenêtre" in place["html"]
    assert "largeur demandée" not in place["html"]
    # 3. LA LARGEUR du document est nulle, la place ne manque pas (5,00 mm)
    assert larg["off"] is True
    assert "largeur demandée" in larg["html"]
    assert "reculer la fenêtre" not in larg["html"]
    assert "sous le trait minimal" not in larg["html"]
    # 4. LE RETRAIT NÉGATIF est avoué, en erreur, avec son chiffre
    assert "retrait du filet est négatif" in neg["html"]
    assert "-5,00 mm" in neg["html"] and "voisine" in neg["html"]
    assert 'class="cf-print-pf-row err"' in neg["html"]
    assert "retrait du filet est négatif" not in sain["html"]
    # 5. hors portée impression : rien à dorer, et le bouton est mort
    assert hors["off"] is True and "hors portée impression" in hors["html"]


def test_l_ecran_dit_le_foil_avant_que_le_preflight_le_decouvre():
    """« refuser sans donner la sortie » est le défaut de forme que la T1 a
    nommé : l'écran écrit le remède, la variance et la limite produit AVANT
    l'export, pas après le refus."""
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-print.js")
    src = js.read_text(encoding="utf-8")
    assert 'CF.get("frame.seal"' in src, "lecture d'état partagé, pas d'import"
    assert "function paintFoil(" in src
    assert 'data-act="foilmask"' in src
    for phrase in ("3,2", "edge_mm", "variance de fabrication",
                   "1 à 2 mm", "CMJN", "PDF/X", "600", "noir",
                   # la troisième contrainte de §6.2bis-b, dite SANS OBJET là
                   # où l'utilisateur lit les deux autres — pas seulement dans
                   # un commentaire Python qu'il n'ouvrira jamais
                   "0,25 mm", "une zone unique",
                   # les DEUX causes d'un anneau nul, distinctes à l'écran
                   "reculer la fenêtre", "largeur demandée",
                   # et le retrait négatif d'un document édité à la main
                   "retrait du filet est négatif"):
        assert phrase in src, phrase

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
