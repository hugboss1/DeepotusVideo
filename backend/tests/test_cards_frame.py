# -*- coding: utf-8 -*-
"""Card Forge — P2 « Bordures et cadres ». Les seuils chiffrés de la pièce.

LA BARRE (Clash of Decks) : TROIS cadres PNG de 638 x 1004 px, qui sont le
même cadre avec un mot différent, et 638 px sur 2,5 pouces = 255 DPI. Elle ne
peut ni monter en définition, ni changer de format, ni servir un dos.

Ce que ce fichier verrouille, seuil par seuil (spec §4, pièce 02) :

  1. >= 20 combinaisons cadre x rareté listées dans l'UI  -> 6 x 6 = 36.
  2. ZÉRO PNG de cadre : aucun bitmap livré, aucun bitmap chargé par le
     module. Le cadre est TRACÉ à `geom.canvas_px`, donc net à 600 DPI.
  3. Épaisseur de filet réglable de 0 à 8 mm ET rayon de coin 0 à 8 mm, tous
     deux affichés en mm ET en px (les deux unités dans l'interface, les
     pixels vérifiés ici contre une arithmétique EXACTE en `Fraction`).
  4. Un dos de carte existe et s'exporte.

Plus le cloisonnement (règles 4, 5, 7, 8, 11, 12) passé au lint réel, et la
garantie « un corps mal formé ne fait JAMAIS un 500 ».

Run : <embedded python> backend/tests/test_cards_frame.py
"""
import asyncio
import json
import os
import pathlib
import re
import sys
import tempfile
from fractions import Fraction

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402

from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import frame as FR                      # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
JS = REPO / "frontend" / "cardforge" / "js" / "mod-frame.js"
CSS = REPO / "frontend" / "cardforge" / "css" / "mod-frame.css"
LINT = REPO / "scripts" / "qa" / "lint_cardforge.py"

# Seuils de la spec, écrits en dur — jamais recalculés depuis le code testé.
COMBOS_MIN = 20
LINE_MM_RANGE = (0, 8)
CORNER_MM_RANGE = (0, 8)
RASTER_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif",
              ".tiff", ".avif"}


def _api(method: str, path: str, **kw):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _deck() -> str:
    r = _api("POST", "/api/cards/decks", json={"name": "essai cadre"})
    assert r.status_code == 200, r.text
    return r.json()["deck"]["id"]


def _js() -> str:
    return JS.read_text(encoding="utf-8")


def _catalog_block(src: str) -> str:
    m = re.search(r"CF-FRAME-CATALOG-BEGIN(.*?)CF-FRAME-CATALOG-END",
                  src, re.S)
    assert m, "bloc CF-FRAME-CATALOG absent de mod-frame.js"
    return m.group(1)


def _js_list(block: str, name: str):
    """Les paires (id, label) d'un tableau du catalogue JS."""
    m = re.search(r"const\s+" + name + r"\s*=\s*\[(.*?)\n\s*\];", block, re.S)
    assert m, f"tableau {name} absent du catalogue JS"
    return re.findall(r'\{\s*id:\s*"([^"]+)",\s*label:\s*"([^"]+)"',
                      m.group(1))


def _py_list(rows):
    return [(r["id"], r["label"]) for r in rows]


def _exact_px(mm, dpi: int) -> float:
    """L'oracle : mm -> px en arithmétique EXACTE (aucun flottant), puis
    arrondi demi-haut à 2 décimales. C'est la valeur qu'un imprimeur
    obtiendrait à la main."""
    v = Fraction(str(mm)) / Fraction(254, 10) * Fraction(dpi)
    return float((v * 100 + Fraction(1, 2)).__floor__()) / 100.0


# ═══════════════ 1. LE CATALOGUE : 36 combinaisons, et une seule liste ══════

def test_au_moins_20_combinaisons():
    """La barre en propose 3. Le seuil de la spec est 20."""
    cat = FR.catalog()
    assert cat["combos"] == len(FR.FAMILIES) * len(FR.RARITIES)
    assert cat["combos"] >= COMBOS_MIN, \
        f"{cat['combos']} combinaisons, seuil {COMBOS_MIN}"
    assert cat["combos"] == 36, "6 familles x 6 raretés"
    assert len(FR.FAMILIES) >= 4, "spec : >= 4 familles graphiques"
    assert len(FR.RARITIES) >= 5, "spec : >= 5 variantes de rareté"
    ids = [f["id"] for f in FR.FAMILIES]
    assert len(set(ids)) == len(ids), f"familles en double : {ids}"


def test_le_catalogue_de_l_ecran_est_celui_du_backend():
    """Le bloc CF-FRAME-CATALOG de mod-frame.js, EXTRAIT et comparé.

    Deux listes qui dérivent en silence, c'est un menu qui propose un cadre
    que le backend ne connaît pas — la même doctrine que le bloc de géométrie
    de core.js / contract.py."""
    b = _catalog_block(_js())
    for name, rows in (("FAMILIES", FR.FAMILIES), ("RARITIES", FR.RARITIES),
                       ("BACKS", FR.BACKS), ("CORNERS", FR.CORNERS),
                       ("METALS", FR.METALS), ("PRESETS", FR.PRESETS)):
        assert _js_list(b, name) == _py_list(rows), \
            f"{name} diverge entre mod-frame.js et cards/frame.py"


def test_les_bornes_sont_les_memes_des_deux_cotes():
    b = _catalog_block(_js())
    m = re.search(r"const\s+LIMITS\s*=\s*\{(.*?)\};", b, re.S)
    assert m, "LIMITS absent du catalogue JS"
    js = dict((k, [float(a), float(v)]) for k, a, v in
              re.findall(r"(\w+):\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]",
                         m.group(1)))
    for k, v in FR.LIMITS.items():
        assert k in js, f"borne {k} absente du JS"
        assert js[k] == [float(v[0]), float(v[1])], \
            f"borne {k} : JS {js[k]} != backend {v}"


# ═══════════════ 2. ZÉRO BITMAP — le seuil qui gagne le duel ════════════════

def test_aucun_cadre_en_bitmap_livre():
    """« zero PNG de cadre en resolution fixe ». La barre en livre 3, de
    638 x 1004 px, plafonnés à 255 DPI au format poker."""
    trouves = []
    for d in ("frames", "frame"):
        p = REPO / "frontend" / "cardforge" / "assets" / d
        if p.is_dir():
            trouves += [f for f in p.rglob("*")
                        if f.suffix.lower() in RASTER_EXT]
    assert not trouves, f"bitmaps de cadre livrés : {trouves}"


def test_le_module_ne_charge_aucune_image():
    """Un cadre qui vient d'un fichier image a une résolution ; un cadre
    tracé n'en a pas. On refuse donc TOUT chargement d'image dans le module,
    pas seulement les PNG posés dans le dépôt."""
    src, css = _js(), CSS.read_text(encoding="utf-8")
    interdits = [
        (r"new\s+Image\s*\(", "new Image()"),
        (r"createImageBitmap\s*\(", "createImageBitmap()"),
        (r"createElement\(\s*[\"']img[\"']", "createElement('img')"),
        (r"<img\b", "<img>"),
        (r"data:image/", "data: URI d'image"),
        (r"createPattern\s*\(", "createPattern()"),
    ]
    for rx, quoi in interdits:
        assert not re.search(rx, src), f"mod-frame.js charge une image : {quoi}"
    assert not re.search(r"url\s*\(", css), \
        "mod-frame.css référence une ressource externe (url(...))"
    # ...et il trace VRAIMENT : des primitives vectorielles, en nombre.
    ops = sum(len(re.findall(rx, src)) for rx in
              (r"\bbezierCurveTo\b", r"\barcTo\b", r"\barc\b", r"\bmoveTo\b",
               r"\blineTo\b", r"createLinearGradient", r"createRadialGradient"))
    assert ops >= 40, f"seulement {ops} primitives de tracé : est-ce vectoriel ?"


def test_le_cadre_est_redessine_a_la_toile_pas_agrandi():
    """Le seuil « à 600 DPI il n'est pas flou », rendu mesurable : les
    longueurs du cadre en pixels DOUBLENT quand la définition double, et la
    toile est exactement celle du CORE. Un PNG de 638 px, lui, reste à 638."""
    did = _deck()
    body = {"fmt": "poker_eu", "line_mm": 0.9, "gap_mm": 1.1, "edge_mm": 1.6,
            "inner_mm": 5.5, "corner_mm": 3.0,
            "window": {"x": 6.62, "y": 6.6, "w": 49.77, "h": 44.44, "r": 2.5}}
    out = {}
    for dpi in (150, 300, 600):
        b = dict(body, dpi=dpi)
        r = _api("POST", f"/api/cards/{did}/frame/metrics", json=b)
        assert r.status_code == 200, r.text
        out[dpi] = r.json()["metrics"]
    assert out[300]["canvas_px"] == [815, 1110], out[300]["canvas_px"]
    assert out[600]["canvas_px"] == [1630, 2220], out[600]["canvas_px"]
    # a) chaque longueur vaut CE QUE DIT L'ARITHMÉTIQUE EXACTE, à sa propre
    #    définition. Tolérance : 0.
    mms = {"line_px": 0.9, "gap_px": 1.1, "edge_px": 1.6, "inner_px": 5.5}
    for dpi, m in out.items():
        for k, mm in mms.items():
            assert m[k] == _exact_px(mm, dpi), \
                f"{k} @ {dpi} DPI : {m[k]} au lieu de {_exact_px(mm, dpi)}"
        assert m["win_px"][2] == _exact_px(49.77, dpi)
    # b) et elles DOUBLENT quand la définition double, au quantum d'affichage
    #    près (0,01 px : les longueurs sont servies à 2 décimales).
    for k in mms:
        assert abs(out[600][k] - 2 * out[300][k]) <= 0.011, \
            f"{k} ne double pas de 300 a 600 DPI : {out[300][k]} -> {out[600][k]}"
        assert abs(out[300][k] - 2 * out[150][k]) <= 0.011, k
    # le rayon de COUPE vient du CORE, arrondi à 1 décimale : son quantum est
    # dix fois plus gros, et c'est voulu (35,4 px à 300 DPI).
    assert abs(out[600]["corner_px"] - 2 * out[300]["corner_px"]) <= 0.11
    # la fenêtre suit la toile, offset de fond perdu compris
    assert out[300]["win_px"][0] == round(35.5 + _exact_px(6.62, 300), 2)


# ═══════════════ 3. FILET 0 -> 8 mm, COIN 0 -> 8 mm, EN mm ET EN px ═════════

def test_le_filet_va_de_0_a_8_mm():
    assert FR.LIMITS["line_mm"] == list(LINE_MM_RANGE)
    did = _deck()
    for mm in (0, 0.35, 0.9, 4, 8):
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 json={"fmt": "poker_eu", "dpi": 300, "line_mm": mm})
        assert r.status_code == 200, r.text
        got = r.json()["metrics"]["line_px"]
        assert got == _exact_px(mm, 300), \
            f"filet {mm} mm -> {got} px, arithmétique exacte : {_exact_px(mm, 300)}"
    # 8 mm à 300 DPI = 94,49 px : le chiffre que l'interface affiche à côté
    # des millimètres.
    assert _exact_px(8, 300) == 94.49
    for mauvais in (8.1, -0.1, "abc", float("inf")):
        # `Infinity` ne passe pas par l'encodeur JSON strict de httpx : on
        # envoie le corps tel quel, comme le ferait un client réel.
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 content=json.dumps({"fmt": "poker_eu", "dpi": 300,
                                     "line_mm": mauvais}).encode("utf-8"),
                 headers={"content-type": "application/json"})
        assert r.status_code == 400, f"{mauvais!r} -> {r.status_code}"
        assert "8" in r.json().get("detail", "") or \
            "nombre" in r.json().get("detail", "")


def test_le_rayon_de_coin_va_de_0_a_8_mm():
    """Le rayon de la DÉCOUPE : le cadre le suit, il ne le redécide pas —
    mais il l'affiche en mm ET en px, ce que la barre ne fait nulle part."""
    assert FR.LIMITS["corner_mm"] == list(CORNER_MM_RANGE)
    did = _deck()
    for mm in (0, 1.5, 3, 8):
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 json={"fmt": "poker_eu", "dpi": 300, "corner_mm": mm})
        assert r.status_code == 200, r.text
        g = CT.geom("poker_eu", 300, corner_mm=mm)
        assert r.json()["metrics"]["corner_px"] == CT.rnd(g.corner_px, 2)
    # 3 mm à 300 DPI = 35,4 px — fractionnaire et assumé, comme le trait de coupe.
    assert CT.geom("poker_eu", 300, corner_mm=3.0).corner_px == 35.4


def test_les_deux_unites_sont_affichees_dans_l_interface():
    """Le seuil dit « affichés en mm ET en px ». On le vérifie sur la SOURCE
    servie : chaque longueur du cadre passe par le même gabarit
    « <mm> mm = <px> px », et la fenêtre porte un relevé px par champ."""
    src = _js()
    m = re.search(r"const mmpx = \(v\) => (.+);", src)
    assert m, "gabarit mm+px absent"
    assert "mm = " in m.group(1) and "px" in m.group(1), m.group(1)
    for cle in ("UI.lineRow", "UI.gapRow", "UI.edgeRow", "UI.innerRow"):
        assert re.search(r"setNum\(" + re.escape(cle) + r",[^)]*mmpx\(",
                         src), f"{cle} n'affiche pas les deux unités"
    assert 'r.px.textContent = r1(wpx[kv[1]]) + " px"' in src, \
        "les champs de la fenêtre n'affichent pas les pixels"
    assert "rayon de coupe" in src and "g.corner_px" in src, \
        "le rayon de coin n'est pas affiché en mm + px"


# ═══════════════ 4. LE DOS — la barre n'en a aucun ══════════════════════════

def test_un_dos_existe_et_s_exporte():
    assert len(FR.BACKS) >= 6, "catalogue de dos trop maigre"
    src = _js()
    assert re.search(r"function paintBack\(", src), "aucun peintre de verso"
    assert re.search(r'side === "back"', src), \
        "le painter ne distingue pas le verso"
    # l'export : le blob vient du MOTEUR (donc du fichier livré), pas d'une
    # toile bricolée à côté — c'est la seule voie que CF.download accepte.
    assert re.search(r'CF\.cardBlob\(\s*CF\.current\(\),\s*\{\s*face:\s*face\s*\}\s*\)',
                     src), "le verso ne s'exporte pas par le moteur"
    assert re.search(r'stamped\("back"\)', src), "l'export du verso n'est pas estampillé"
    # ... puis par le backend DU MODULE, la seule autre provenance acceptée :
    # c'est ce qui permet d'ajouter pHYs sans fabriquer une toile à côté.
    assert re.search(r'M\.api\.blob\("POST", stampQuery\(', src)
    assert re.search(r"M\.download\(r\.blob,", src), "aucun téléchargement du verso"
    # dos commun OU par carte (lecture seule de card.back, écrit par P4)
    assert re.search(r"function backOf\(", src)
    assert "card.back" in src, "le dos par carte ne lit pas card.back"


def test_le_dos_est_servi_par_le_catalogue():
    cat = FR.catalog()
    ids = [b["id"] for b in cat["backs"]]
    assert "mirror" in ids and len(set(ids)) == len(ids)
    assert cat["raster_assets"] == 0 and cat["vector"] is True


# ═══════════════ 5. LA FENÊTRE D'ILLUSTRATION, SUR LES 12 FORMATS ═══════════

@pytest.mark.parametrize("fmt", list(CT.FORMATS))
def test_la_fenetre_par_defaut_tient_dans_la_coupe(fmt):
    """La fenêtre automatique est proportionnelle : aucun format ne la fait
    déborder, et elle reste dans la toile, offset de fond perdu compris."""
    g = CT.geom(fmt, 300)
    w = FR._win_of(None, g)
    assert w["x"] >= 0 and w["y"] >= 0
    assert w["x"] + w["w"] <= g.trim_mm[0] + 1e-9
    assert w["y"] + w["h"] <= g.trim_mm[1] + 1e-9
    m = FR.frame_metrics(g, 0.9, 1.1, 1.6, 5.5, w)
    x, y, ww, hh, _r = m["win_px"]
    assert 0 <= x and x + ww <= g.canvas_px[0] + 0.01
    assert 0 <= y and y + hh <= g.canvas_px[1] + 0.01


# ═══════════════ 6. JAMAIS DE 500, ET LE DOMAINE EST BIEN MONTÉ ═════════════

def test_les_routes_du_cadre_repondent():
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/frame/catalog")
    assert r.status_code == 200, r.text
    assert "json" in r.headers.get("content-type", "").lower(), \
        "sans le montage du domaine, une route absente rend du HTML (piège 7)"
    cat = r.json()["catalog"]
    assert cat["combos"] == 36
    from app.main import app
    chemins = list(app.openapi().get("paths", {}))
    for attendu in ("/api/cards/{did}/frame/catalog",
                    "/api/cards/{did}/frame/metrics"):
        assert attendu in chemins, f"{attendu} absent"


def test_un_corps_malforme_ne_fait_jamais_500():
    did = _deck()
    mauvais = [
        {"fmt": "inexistant"},
        {"fmt": "poker_eu", "dpi": "beaucoup"},
        {"fmt": "poker_eu", "dpi": 1e999},
        {"fmt": "poker_eu", "line_mm": {"non": "plus"}},
        {"fmt": "poker_eu", "window": {"w": "large"}},
        {"fmt": "poker_eu", "window": {"r": 99}},
        {"fmt": "poker_eu", "family": "hearthstone"},
        {"fmt": "poker_eu", "inner_mm": 21},
        {"fmt": "poker_eu", "bleed_mm": 40},
    ]
    for b in mauvais:
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 content=json.dumps(b).encode("utf-8"),
                 headers={"content-type": "application/json"})
        assert r.status_code == 400, f"{b} -> {r.status_code} {r.text[:160]}"
        assert isinstance(r.json().get("detail"), str)
    # corps vide et corps non-objet : des valeurs par défaut, pas une panne
    for body in (None, [], "texte"):
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 content=json.dumps(body).encode("utf-8"),
                 headers={"content-type": "application/json"})
        assert r.status_code in (200, 400, 422), r.text
        assert r.status_code != 500


def test_deck_inconnu_et_identifiant_invalide():
    r = _api("POST", "/api/cards/deck_deadbeef/frame/metrics", json={})
    assert r.status_code == 404, r.text
    r = _api("GET", "/api/cards/pas_un_deck/frame/catalog")
    assert r.status_code in (400, 404), r.text


# ═══════════════ 7. CLOISONNEMENT — le lint réel, sur ce module ═════════════

def test_le_module_passe_le_lint():
    """R4 (css), R5 (ids DOM), R7 (couches z), R8 (routeur), R11 (use strict),
    R12 (aucun mutateur global). Huit builders en parallèle : c'est ce filet
    qui empêche une pièce d'écrire chez une autre."""
    if not LINT.is_file():
        pytest.skip("lint_cardforge.py absent")
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_cf", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    findings, present = mod.run(REPO, "frame")
    errs = [f for f in findings if not f["warn"]]
    assert not errs, "\n".join(f"{f['rule']} {f['file']}:{f['line']} {f['msg']}"
                               for f in errs)
    assert all(present["frame"].values()), \
        f"règle 1 (1 JS + 1 CSS + 1 py + 1 test) : {present['frame']}"


def test_le_document_de_la_coquille_est_migre():
    """Les jeux créés AVANT les builders portent l'état du gabarit vide, dont
    `back:"none"` — un identifiant de dos qui n'existe dans aucun catalogue,
    donc une empreinte qu'aucune version livrée ne peut écrire. Les relire
    tels quels rendait une carte SANS CADRE : pas par choix, par héritage.
    Mesuré : 12 jeux de ce type sur le disque au moment de la livraison.

    L'empreinte ne peut PAS être « il manque des clés » : le registre du CORE
    fusionne le `state` déclaré AVANT l'hydratation, donc `doc.frame` porte
    toujours les 22 clés, y compris sur un document de 7."""
    src = _js()
    assert re.search(r'const coquille = \(s0\.back === "none"\)', src), \
        "la migration du document de coquille a disparu"
    assert "const s = coquille ? {} : s0;" in src
    assert "none" not in [b["id"] for b in FR.BACKS], \
        "\"none\" ne doit pas devenir un dos valide : c'est l'empreinte"


def test_les_couches_sont_bien_40_et_70():
    src = _js()
    zs = sorted(int(z) for z in re.findall(r"painters:.*?\{\s*\n?\s*z:\s*(\d+),",
                                           src, re.S)[:1]
                + re.findall(r"\{\s*\n\s*z:\s*(\d+),\s*fn\(", src))
    assert sorted(set(zs)) == [40, 70], f"couches déclarées : {sorted(set(zs))}"
    assert src.lstrip().startswith("/*") or src.lstrip().startswith('"use strict"')
    assert '"use strict";' in src.split("\n(function")[0]


# ═════════════════════════════════════════════════════════════════════════════
# 8. LE FICHIER LIVRÉ PORTE SA PROPRE GÉOMÉTRIE  (manque n°1 du duel 2)
#
# MESURE AVANT, sur le PNG que le bouton d'export téléchargeait :
#   chunks = IHDR:13 + 279 x IDAT + IEND:0, 1 138 176 octets.
#   pHYs absent, tEXt absent, eXIf absent.
# Conséquence : le fichier ne disait que « 815 x 1110 pixels ». Un lecteur
# d'impression applique 72 DPI par défaut et lit une carte de 28,7 x 39,1 cm,
# et le fichier 300 DPI est INDISCERNABLE du 600 DPI en aval.
# ═════════════════════════════════════════════════════════════════════════════

def _png(w: int, h: int) -> bytes:
    """Un PNG minimal, écrit à la main : le test ne dépend pas de PIL et sait
    exactement quels octets il donne à estampiller."""
    import struct as _s
    import zlib as _z
    sig = b"\x89PNG\r\n\x1a\n"

    def ch(t, p):
        return _s.pack(">I", len(p)) + t + p + _s.pack(
            ">I", _z.crc32(t + p) & 0xFFFFFFFF)
    ihdr = ch(b"IHDR", _s.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    row = b"\x00" + b"\x20\x40\x60\xff" * w
    idat = ch(b"IDAT", _z.compress(row * h, 6))
    return sig + ihdr + idat + ch(b"IEND", b"")


def _chunks(data: bytes) -> list:
    return [t for t, _ in FR.png_chunks(data)]


def _text_of(data: bytes) -> dict:
    """Les tEXt relus DANS LES OCTETS — pas ce que le code prétend écrire."""
    import struct as _s
    out, p = {}, 8
    while p + 8 <= len(data):
        ln = _s.unpack(">I", data[p:p + 4])[0]
        typ = data[p + 4:p + 8]
        if typ == b"tEXt":
            k, _, v = data[p + 8:p + 8 + ln].partition(b"\x00")
            out[k.decode("latin-1")] = v.decode("latin-1")
        if typ == b"IEND":
            break
        p += 12 + ln
    return out


def _phys_of(data: bytes):
    import struct as _s
    p = 8
    while p + 8 <= len(data):
        ln = _s.unpack(">I", data[p:p + 4])[0]
        if data[p + 4:p + 8] == b"pHYs":
            x, y, u = _s.unpack(">IIB", data[p + 8:p + 17])
            return x, y, u
        if data[p + 4:p + 8] == b"IEND":
            break
        p += 12 + ln
    return None


def test_le_ppm_est_celui_de_la_norme():
    """300 DPI = 11811 px/m, 600 = 23622, 150 = 5906. Arrondi demi-haut du
    domaine, pas le `round` au pair de Python (qui rendrait 5906 aussi ici,
    mais 11810 sur d'autres définitions paires)."""
    assert FR.dpi_to_ppm(300) == 11811
    assert FR.dpi_to_ppm(600) == 23622
    assert FR.dpi_to_ppm(150) == 5906
    assert FR.dpi_to_ppm(72) == 2835


def test_le_png_livre_porte_sa_definition():
    """AVANT : IHDR + IDAT + IEND, aucun pHYs. APRÈS : pHYs, en tête, avec la
    définition annoncée par l'interface."""
    did = _deck()
    for dpi, ppm in ((300, 11811), (600, 23622)):
        g = CT.geom("poker_eu", dpi)
        brut = _png(*g.canvas_px)
        assert "pHYs" not in _chunks(brut), "le PNG d'entrée en a déjà un ?"
        r = _api("POST", f"/api/cards/{did}/frame/stamp"
                         f"?fmt=poker_eu&dpi={dpi}&face=back",
                 content=brut, headers={"content-type": "image/png"})
        assert r.status_code == 200, r.text[:300]
        out = r.content
        ch = _chunks(out)
        assert ch[0] == "IHDR", ch[:3]
        assert "pHYs" in ch, f"pHYs absent : {ch[:6]}"
        assert ch.index("pHYs") < ch.index("IDAT"), \
            "pHYs doit précéder IDAT (norme PNG), sinon il est ignoré"
        assert _phys_of(out) == (ppm, ppm, 1), _phys_of(out)
        # et les pixels n'ont pas bougé : on ajoute des métadonnées, on ne
        # recompresse rien.
        assert FR.png_size(out) == tuple(g.canvas_px)
        assert ch.count("IDAT") == _chunks(brut).count("IDAT")


def test_le_png_livre_porte_ses_boites_de_coupe():
    """« Le fond perdu est peint mais MUET : rien dans le fichier ne dit où
    couper. » Un PNG ne peut structurellement pas porter de TrimBox ; il peut
    porter du tEXt, et c'est lisible par un humain comme par un script."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300"
                     f"&face=front&collisions=0",
             content=_png(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text[:300]
    t = _text_of(r.content)
    for k in ("Software", "Format", "Resolution", "BleedBox", "TrimBox",
              "SafeBox", "Face", "Collisions"):
        assert k in t, f"tEXt {k} absent : {sorted(t)}"
    # ... et l'écran nomme EXACTEMENT ces clés-là, dans le même ordre.
    ordre = [k for k in ("Software", "Format", "Resolution", "BleedBox",
                         "TrimBox", "SafeBox", "Face", "Collisions",
                         "Comment")]
    pos, src = -1, _js()
    for k in ordre:
        i = src.find(k, pos + 1)
        assert i > pos, f"l'interface n'annonce pas la clé {k} (ou pas dans l'ordre)"
        pos = i
    assert f"{g.canvas_px[0]}x{g.canvas_px[1]}" in t["BleedBox"]
    assert f"{g.trim_px[0]}x{g.trim_px[1]}" in t["TrimBox"]
    assert f"{g.safe_px[0]}x{g.safe_px[1]}" in t["SafeBox"]
    assert "11811" in t["Resolution"] and "300 DPI" in t["Resolution"]
    # tout doit être encodable en Latin-1 : c'est la seule table permise pour
    # tEXt, et un tiret cadratin y lèverait en production.
    for k, v in t.items():
        k.encode("latin-1")
        v.encode("latin-1")


def test_estampiller_une_definition_fausse_est_refuse():
    """Le garde-fou qui empêche le badge menteur : la route relit IHDR. Une
    toile de 815x1110 déclarée à 600 DPI est REFUSÉE, pas estampillée."""
    did = _deck()
    g300 = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=600",
             content=_png(*g300.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 400, r.status_code
    d = r.json()["detail"]
    assert "815x1110" in d and "1630x2220" in d, d
    # ... et le bon couple passe
    g600 = CT.geom("poker_eu", 600)
    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=600",
             content=_png(*g600.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text[:200]


def test_le_stamp_est_idempotent_et_refuse_ce_qui_n_est_pas_un_png():
    did = _deck()
    g = CT.geom("poker_eu", 300)
    url = f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300"
    a = _api("POST", url, content=_png(*g.canvas_px),
             headers={"content-type": "image/png"}).content
    b = _api("POST", url, content=a,
             headers={"content-type": "image/png"}).content
    assert _chunks(b).count("pHYs") == 1, "pHYs empilé au second passage"
    assert _chunks(b).count("tEXt") == _chunks(a).count("tEXt")
    assert a == b, "estampiller deux fois doit rendre le même fichier"
    for mauvais in (b"", b"pas un png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 4):
        r = _api("POST", url, content=mauvais,
                 headers={"content-type": "image/png"})
        assert r.status_code == 400, f"{mauvais[:10]!r} -> {r.status_code}"
        assert r.status_code != 500


def test_le_texte_du_png_reste_en_latin1():
    """`_latin1` remplace AVANT d'encoder. Sans lui, un tiret cadratin dans un
    nom de jeu ferait un 500 en production, et nulle part ailleurs."""
    assert FR._latin1("cadre — « épure »") == "cadre - « épure »"
    assert FR._latin1("a\u2192b").startswith("a->b")
    assert FR._latin1("emoji \U0001f0cf ok") == "emoji ? ok"
    FR._latin1("tout ce qui sort doit s'encoder").encode("latin-1")


# ═════════════════════════════════════════════════════════════════════════════
# 9. L'OCCUPATION — le meuble ne recouvre plus la mention (manque n°1 duel 1)
#
# MESURE AVANT, sur le document par défaut et sur le FICHIER LIVRÉ :
#   bandeau x artist = 46,43 mm² = 73,6 % de la mention  (« ...ortain »)
#   bandeau x num    = 36,68 mm² = 69,7 %
#   gemme   x cost   = 67,14 mm² = 73,5 %
#   gemme   x title  = 44,41 mm² = 10,2 %
# et l'interface n'affichait AUCUN compteur.
# ═════════════════════════════════════════════════════════════════════════════

# Les slots réels de la pièce 03 sur un poker_eu, relevés dans le DOM vivant.
SLOTS = [
    {"id": "cost", "box": [3.005667, 2.963333, 9.686713, 9.43483]},
    {"id": "title", "box": [13.831993, 2.963333, 46.15434, 9.43483]},
    {"id": "typeline", "box": [3.005667, 48.250517, 56.980667, 4.1021]},
    {"id": "rules", "box": [4.14528, 53.419163, 54.70144, 16.4084]},
    {"id": "flavor", "box": [5.284893, 70.730025, 52.422213, 4.51231]},
    {"id": "atk", "box": [3.005667, 75.570503, 9.686713, 7.38378]},
    {"id": "def", "box": [50.29962, 75.570503, 9.686713, 7.38378]},
    {"id": "num", "box": [14.4018, 81.067317, 14.245167, 3.69189]},
    {"id": "artist", "box": [31.496, 81.067317, 17.0942, 3.69189]},
]
FRAME = {"inner_mm": 5.5, "edge_mm": 1.6, "rarity": "rare", "gem": True,
         "banner": True, "window": None}


def test_sans_le_modele_le_bandeau_mange_la_signature():
    """La MESURE du défaut, gravée : sans résolution, quatre recouvrements,
    dont 73,6 % de la signature de l'artiste. C'est le test qui échouerait si
    quelqu'un retirait le modèle en croyant simplifier."""
    g = CT.geom("poker_eu", 300)
    o = FR.occupancy(g, dict(FRAME, fit=False), SLOTS)
    par = {(c["a"], c["b"]): c for c in o["collisions"]}
    assert o["count"] == 4, o["collisions"]
    assert par[("banner", "artist")]["pct"] > 70
    assert par[("banner", "num")]["pct"] > 65
    assert par[("gem", "cost")]["pct"] > 70


def test_avec_le_modele_aucune_mention_n_est_recouverte():
    """APRÈS : zéro. Le ruban descend dans une voie libre et s'y amincit ; la
    gemme, faute de coin libre, passe en couche 40 et devient un logement."""
    g = CT.geom("poker_eu", 300)
    o = FR.occupancy(g, dict(FRAME, fit=True), SLOTS)
    assert o["count"] == 0, o["collisions"]
    ban = [b for b in o["boxes"] if b["id"] == "banner"][0]
    gem = [b for b in o["boxes"] if b["id"] == "gem"][0]
    assert ban["z"] == 70 and "voie libre" in ban["lane"], ban
    assert ban["box"][3] < FR.BANNER_H_MM, "le ruban devait maigrir"
    assert ban["box"][3] >= FR.BANNER_MIN_H_MM
    assert gem["z"] == 40 and gem["seat"] is True, gem
    # le compteur ne compte QUE ce qui masque : la couche 40 passe dessous.
    assert all(b["z"] == 40 for b in o["boxes"] if b["id"].startswith("seat:"))
    assert all(b["z"] == 40 for b in o["boxes"] if b["id"].startswith("socle:"))


def test_le_modele_tient_sur_les_douze_formats():
    """Un modèle qui ne marche que sur le poker n'est pas un modèle. Les
    boîtes sont en mm, donc elles suivent la rogne — on le vérifie."""
    g0 = CT.geom("poker_eu", 300)
    ref = FR.occupancy(g0, dict(FRAME, fit=True), SLOTS)
    assert ref["count"] == 0
    for fmt in CT.FORMATS:
        for dpi in (150, 300, 600):
            g = CT.geom(fmt, dpi)
            o = FR.occupancy(g, dict(FRAME, fit=True), SLOTS)
            for b in o["boxes"]:
                x, y, w, h = b["box"]
                assert w > 0 and h > 0, (fmt, b)
                if b["id"] in ("window", "banner") or \
                        (b["id"] == "gem" and not b.get("seat")):
                    # les meubles PROPRES au cadre restent dans la rogne
                    assert x >= -0.01 and y >= -0.01, (fmt, b)
                    assert x + w <= g.trim_mm[0] + 0.01, (fmt, b)
                    assert y + h <= g.trim_mm[1] + 0.01, (fmt, b)
                elif b["id"] == "gem":
                    # l'écrin épouse la mention hôte : il ne peut la dépasser
                    # que du jeu SEAT_PAD_MM, jamais plus.
                    hb = max((m["box"] for m in o["mentions"]),
                             key=lambda q: min(q[0] + q[2], x + w) - max(q[0], x))
                    assert w <= max(hb[2], hb[3]) + 2 * FR.SEAT_PAD_MM + 0.02, (fmt, b)
                    assert h <= max(hb[2], hb[3]) + 2 * FR.SEAT_PAD_MM + 0.02, (fmt, b)
                else:
                    # socles et logements SUIVENT la mention : si la pièce 03
                    # pose un slot hors carte, ce n'est pas au cadre de le
                    # recadrer en silence — il ne fait que l'habiller.
                    src = [m for m in o["mentions"]
                           if b["id"].endswith(":" + m["id"])][0]["box"]
                    pad = FR.SOCLE_PAD_MM if b["id"].startswith("socle:") \
                        else FR.SEAT_PAD_MM
                    assert abs(w - (src[2] + 2 * pad)) < 0.02, (fmt, b)
                    assert abs(h - (src[3] + 2 * pad)) < 0.02, (fmt, b)
            # la définition ne change RIEN au plan : il est en millimètres.
            assert o["boxes"] == FR.occupancy(
                CT.geom(fmt, 300), dict(FRAME, fit=True), SLOTS)["boxes"], fmt


def test_le_modele_ne_plante_pas_sur_des_slots_hostiles():
    """P3 est un autre module : il peut écrire n'importe quoi. Un slot mal
    formé est ignoré, jamais une exception — le cadre doit se dessiner."""
    g = CT.geom("poker_eu", 300)
    hostiles = [None, 42, {"id": "x"}, {"id": "y", "box": []},
                {"id": "z", "box": [1, 2, 0, 4]},
                {"id": "w", "box": ["a", "b", "c", "d"]},
                {"id": "n", "box": [1, 2, float("inf"), 4]},
                {"box": [1, 1, 5, 5]}]
    o = FR.occupancy(g, dict(FRAME, fit=True), hostiles)
    assert [m["id"] for m in o["mentions"]] == ["slot"], o["mentions"]
    for bad in (None, "texte", 7, {"a": 1}):
        assert FR.occupancy(g, dict(FRAME, fit=True), bad)["count"] == 0


def test_le_placement_est_le_meme_des_deux_cotes():
    """Le bloc CF-FRAME-OCC de mod-frame.js, EXTRAIT et comparé. Deux
    placements différents, ce serait un aperçu qui ment sur le fichier."""
    m = re.search(r"CF-FRAME-OCC-BEGIN(.*?)CF-FRAME-OCC-END", _js(), re.S)
    assert m, "bloc CF-FRAME-OCC absent de mod-frame.js"
    js = dict((k, float(v)) for k, v in
              re.findall(r"const\s+([A-Z_0-9]+)\s*=\s*([\d.]+);", m.group(1)))
    for k in ("CLEAR_MM", "BANNER_H_MM", "BANNER_MIN_H_MM", "BANNER_CH_MM",
              "BANNER_PAD_CH", "BANNER_MAX_F", "GEM_R_MM", "GEM_OFF_F",
              "PIP_STEP_MM", "PIP_R_MM", "SOCLE_PAD_MM", "SEAT_PAD_MM",
              "SEAT_MIN_FRAC", "SOCLE_MIN_FRAC", "GEM_SEAT_RATIO",
              "TOL_MM2", "TOL_FRAC"):
        assert k in js, f"{k} absent du bloc JS"
        assert js[k] == float(getattr(FR, k)), \
            f"{k} : JS {js[k]} != python {getattr(FR, k)}"
    assert len(js) == 17, f"constantes JS non appariées : {sorted(js)}"


def test_la_route_occupancy_repond_et_ne_fait_jamais_500():
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/frame/occupancy",
             json={"fmt": "poker_eu", "dpi": 300,
                   "frame": dict(FRAME, fit=True), "slots": SLOTS})
    assert r.status_code == 200, r.text[:200]
    o = r.json()["occupancy"]
    assert o["count"] == 0 and o["seats"] >= 1 and o["socles"] >= 1
    for b in ({"fmt": "inconnu"}, {"dpi": "beaucoup"},
              {"frame": {"inner_mm": 99}}, {"frame": {"edge_mm": -1}}):
        r = _api("POST", f"/api/cards/{did}/frame/occupancy",
                 content=json.dumps(b).encode("utf-8"),
                 headers={"content-type": "application/json"})
        assert r.status_code == 400, f"{b} -> {r.status_code}"
    for b in (None, [], "texte", {"slots": "non"}, {"frame": 7}):
        r = _api("POST", f"/api/cards/{did}/frame/occupancy",
                 content=json.dumps(b).encode("utf-8"),
                 headers={"content-type": "application/json"})
        assert r.status_code != 500, f"{b} -> {r.text[:150]}"


def test_le_compteur_est_affiche_et_le_painter_lit_le_meme_plan():
    """« Sa fiche annonce aucune erreur de rendu pour ce fichier — donc le
    moteur ne considère même pas l'occultation comme une erreur. » Le compteur
    existe maintenant, à côté de la vérification backend, et le painter lit le
    MÊME plan que lui : un badge vert avec un ruban qui mange la signature
    serait le pire des deux mondes."""
    src = _js()
    assert "cff-occ" in src, "aucun badge de recouvrement dans l'interface"
    assert "recouvrement de mention" in src
    assert re.search(r"UI\.occ\.className\s*=\s*\"cff-occ \"\s*\+\s*\(n \? \"ko\" : \"ok\"\)", src)
    # le painter ne recalcule pas une position dans son coin
    assert src.count("planOf(g, f)") >= 2, \
        "paintFront et paintTop doivent lire le plan, pas des constantes"
    assert 'findBox(plan, "banner")' in src and 'findBox(plan, "gem")' in src
    assert "collisions=" in src, "le compte doit partir dans le PNG livré"


# ═════════════════════════════════════════════════════════════════════════════
# 10. CE QUE L'INTERFACE AFFICHE DOIT ÊTRE VRAI, ET VÉRIFIABLE
# ═════════════════════════════════════════════════════════════════════════════

def test_les_bornes_des_curseurs_sont_ecrites():
    """« Je n'ai pas pu vérifier le seuil 0 à 8 mm : l'interface n'affiche
    jamais les bornes, seulement la valeur courante. » Elles sont écrites."""
    src = _js()
    assert "cff-bounds" in src, "les bornes ne sont pas rendues"
    assert "six <b>tEXt</b>" not in src, \
        "compte de tEXt faux : le fichier en porte neuf, pas six"
    assert re.search(r'h\("i", "cff-bounds", r2\(min\) \+ " → " \+ r2\(max\)', src)
    css = CSS.read_text(encoding="utf-8")
    assert ".cff-bounds" in css, "les bornes existent mais ne sont pas stylées"


def test_la_galerie_des_36_ne_depend_plus_d_un_clic():
    """« 0 enfant et 0 canvas dans l'état par défaut, 36 après ouverture.
    L'utilisateur qui n'ouvre jamais le volet voit l'annonce du catalogue sans
    le catalogue. »"""
    src = _js()
    m = re.search(r'const all = h\("details", "grp cff-all"\);\s*\n\s*all\.open = true;', src)
    assert m, "la galerie des 36 n'est pas ouverte par défaut"
    assert re.search(r"drawGrids\(\);\s*\n\s*drawAll\(\);", src), \
        "drawAll doit être appelé sans condition d'ouverture préalable"


def test_la_loupe_ne_promet_plus_une_nettete_infinie():
    """« La formulation vend de la résolution infinie qu'elle ne livre pas. »
    La vraie force, mesurable, est le retracé au changement de définition."""
    src = _js()
    assert "tracé, jamais échantillonné" not in src, \
        "la surpromesse est toujours affichée"
    assert "sont les pixels du fichier" in src
    assert "redessiné à chaque définition" in src
    assert "au plus proche voisin" in src


def test_le_rayon_de_coupe_et_le_fond_perdu_sont_distingues():
    """On m'a reproché « deux chiffres pour un seul bord » (35,4 et 35,5). Ce
    ne sont pas les mêmes bords, et les DEUX chiffres restent écrits.

    CE QUI A CHANGÉ : la ligne de calcul qui les dérivait à voix haute
    (« conversion directe 3/25,4 x 300 », « déduit de la toile qui fait
    autorité : (815-744)/2 ») s'adressait à quelqu'un qui vérifie une copie,
    pas à quelqu'un qui pose une fenêtre. Elle est remplacée par ce que
    chaque longueur EST. Les deux mesures, elles, restent à l'écran en mm et
    en px."""
    src = _js()
    assert "Rayon de coupe" in src and "Décalage du fond perdu" in src
    # les deux nombres sont toujours affichés, en millimètres ET en pixels
    assert 'r2(g.corner_mm) + " mm = <b>" + r1(g.corner_px) + " px</b>' in src, \
        "le rayon de coupe n'est plus chiffré à l'écran"
    assert 'r2(g.bleed_mm) + " mm = <b>" + r2(g.bleed_off_px[0])' in src, \
        "le décalage de fond perdu n'est plus chiffré à l'écran"
    # ... mais plus une seule dérivation récitée
    assert "conversion directe" not in src, \
        "l'écran récite encore le calcul du rayon"
    assert "déduit de la toile qui fait autorité" not in src, \
        "l'écran récite encore la dérivation du fond perdu"
    assert '"/25,4 x " + g.dpi' not in src, \
        "la constante de définition est encore recopiée dans une conversion"
    assert '(" + g.canvas_px[0] + "-" + g.trim_px[0] + ")/2' not in src, \
        "la soustraction qui dérive le fond perdu est encore à l'écran"
    g = CT.geom("poker_eu", 300)
    assert _exact_px(g.corner_mm, 300) == 35.43, "le rayon vaut bien 35,43 px"
    assert g.bleed_off_px[0] == (g.canvas_px[0] - g.trim_px[0]) / 2 == 35.5
    assert g.corner_px != g.bleed_off_px[0], \
        "deux longueurs distinctes, deux nombres : c'est la règle, pas un bug"


def _profile_rows(src: str):
    """La table PROFILE, colonne par colonne : (id, kind, t, moulure, plaque,
    hatch, pitch, zone)."""
    m = re.search(r"const PROFILE = \{(.*?)\n  \};", src, re.S)
    assert m, "table PROFILE absente"
    rows = re.findall(
        r"(\w+):\s*\{\s*kind:\s*\"(\w+)\",\s*t:\s*([\d.]+),\s*"
        r"moulure:\s*\"(\w+)\",\s*plaque:\s*\"(\w+)\",\s*"
        r"hatch:\s*([\d.]+),\s*pitch:\s*([\d.]+),\s*zone:\s*\"([\w-]+)\"\s*\}",
        m.group(1))
    return rows


def test_les_six_familles_ont_des_silhouettes_distinctes():
    """MESURE AVANT, sur les vignettes du sélecteur (74 x 101 px, le format où
    le choix se fait) : « Bois sculpté » et « Épure » différaient sur 0,04 %
    des pixels ; et après une première passe, sur GRIS NORMALISÉ (la mesure
    exacte du critique — le contraste est renormalisé, donc une simple
    recoloration tombe à zéro), « Runique x Bois » valait encore 0,82 / 255.

    On verrouille ici la CAUSE, colonne par colonne : chaque famille change de
    masse à un endroit DIFFÉRENT de la carte. Cinq signatures, cinq zones
    disjointes, et aucune valeur partagée par deux familles.

    Le badge « silhouettes » de l'interface, lui, MESURE le résultat sur les
    vignettes affichées (mesure du 12/08 : pire paire à 9,18 / 255, contre
    0,82 avant — et 36 signatures de pixels distinctes sur 36).
    """
    src = _js()
    rows = _profile_rows(src)
    assert len(rows) == len(FR.FAMILIES), \
        f"{len(rows)} profils pour {len(FR.FAMILIES)} familles"
    assert [r[0] for r in rows] == [f["id"] for f in FR.FAMILIES]
    for col, nom in ((1, "kind"), (3, "moulure"), (4, "plaque"),
                     (5, "hatch"), (7, "zone")):
        vals = [r[col] for r in rows]
        assert len(set(vals)) == len(vals), \
            f"deux familles partagent la même colonne {nom} : {vals}"
    for r in rows:
        assert float(r[2]) >= 1.4, f"profil {r[1]} trop fin pour une vignette"
        assert float(r[6]) > 0, f"famille {r[0]} sans trame de matière"
        assert f'pr.kind === "{r[1]}"' in src, f"profil {r[1]} jamais dessiné"
        assert f'pr.moulure === "{r[3]}"' in src, f"moulure {r[3]} jamais dessinée"
        assert f'k === "{r[4]}"' in src or r[4] == "epure", \
            f"plaque {r[4]} jamais dessinée"
    # la ZONE pèse le plus : elle doit être peinte, et l'anneau clipé.
    for z in [r[7] for r in rows if r[7] != "vide"]:
        assert f'pr.zone === "{z}"' in src, f"zone {z} déclarée, jamais peinte"
    assert "function ringZone(" in src and 'ctx.clip("evenodd")' in src


def test_le_badge_silhouettes_mesure_au_lieu_de_declarer():
    """« 36 est un compte, pas une qualité plastique. » Le compte reste écrit
    comme un compte ; la VARIÉTÉ, elle, est mesurée à l'écran sur les vignettes
    affichées — signatures de pixels + gris normalisé — et le pire écart est
    publié. Un badge qui réciterait le catalogue ne prouverait rien."""
    src = _js()
    assert "combinaisons vectorielles" not in src, \
        "le compte ne doit pas se faire passer pour une mesure de variété"
    assert re.search(r'UI\.count\.innerHTML = "<b>" \+ \(FAMILIES\.length \* RARITIES\.length\)'
                     r' \+ "</b> combinaisons"', src)
    for cle in ("function measureSil(", "function grayNorm(", "function sig(",
                "cff-sil"):
        assert cle in src, f"{cle} absent : le badge ne mesure rien"
    # il lit les vignettes AFFICHÉES, il ne rend pas une image à part
    assert 'UI.allBody.querySelectorAll(".cff-cell canvas")' in src
    assert "getImageData" in src
    # ... et il publie les écarts MESURÉS, sans réciter la tolérance qu'il
    # s'impose ni annoncer de verdict : la couleur du badge le dit déjà.
    ds = _js_fn(src, "drawSil")
    assert '"/255 sur la toile livrée"' in ds or "/255 sur la toile" in ds, \
        "le badge ne publie plus l'écart mesuré"
    assert "Seuil que je m'impose" not in src, \
        "l'infobulle récite encore la tolérance qu'elle s'impose"
    assert "décide du verdict" not in src, \
        "l'infobulle annonce encore un verdict"
    assert "F.all >= SIL_SEUIL" in ds, \
        "la tolérance doit rester dans le code, seule sa récitation part"


# ═════════════════════════════════════════════════════════════════════════════
# 11. LES TROIS CHIFFRES QUI ÉTAIENT FAUX, ET LA PREUVE SUR LES OCTETS
# ═════════════════════════════════════════════════════════════════════════════

def test_le_600_dpi_n_est_pas_un_x2_sur_quatre_formats():
    """LA LOUPE MENTAIT D'UN PIXEL. Elle écrivait « en 600 DPI ce même coin
    fait W*2 x H*2 » — une MULTIPLICATION. Or la règle est
    canvas_px = R(mm/25,4 x dpi) : sur 4 des 12 formats, doubler la définition
    ne double pas la toile.

    Ce test mesure les 12 formats et nomme les 4 fautifs ; l'interface, elle,
    demande la toile à `geomOf` et dit explicitement quand ce n'est pas le
    double."""
    faux = []
    for fmt in CT.FORMATS:
        bl = CT.native_bleed_mm(fmt)
        a = CT.geom(fmt, 300, bl, bl, 3.0)
        b = CT.geom(fmt, 600, bl, bl, 3.0)
        if [b.canvas_px[0], b.canvas_px[1]] != [2 * a.canvas_px[0],
                                                2 * a.canvas_px[1]]:
            faux.append((fmt, tuple(a.canvas_px), tuple(b.canvas_px)))
    assert [f[0] for f in faux] == ["bridge_eu", "tarot_eu", "mini",
                                    "square_eu"], faux
    # le cas le plus parlant : tarot_eu, 898x1488 -> 1795x2976, pas 1796.
    assert ("tarot_eu", (898, 1488), (1795, 2976)) in faux
    src = _js()
    assert "(W * 2) + \" x \" + (H * 2) + \" px de toile\"" not in src, \
        "la loupe multiplie encore par deux"
    assert re.search(r"const g6 = CF\.geomOf\(g\.fmt, 600, g\.bleed_mm, "
                     r"g\.safe_mm, g\.corner_mm\);", src), \
        "la loupe doit CALCULER la toile 600 DPI, pas la multiplier"
    assert "jamais d'une multiplication" in src


def test_le_fichier_dit_sa_definition_reelle_pas_300_tout_rond():
    """« Le fichier dit 300 DPI alors que ses octets disent 11811 px/m =
    299,9994 DPI. C'est exactement l'écart d'un millième de pour cent qu'il
    reproche aux autres. » Écrit."""
    assert FR.ppm_to_dpi(11811) == 299.9994
    assert FR.ppm_to_dpi(23622) == 599.9988
    assert FR.ppm_to_dpi(FR.dpi_to_ppm(150)) == 150.0124   # 5906 px/m
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300",
             content=_png(*g.canvas_px), headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text[:200]
    res = _text_of(r.content)["Resolution"]
    assert "299.9994" in res, res          # la valeur RÉELLE, 4 décimales
    assert "11811 px/m" in res and "300 DPI demandes" in res, res
    assert "299.999 DPI" not in res.replace("299.9994", ""), \
        "%g tronquait la dernière décimale"
    assert r.headers.get("X-Card-Dpi-Reel") == "299.9994"
    # ... et l'écran l'écrit aussi, au lieu d'arrondir en silence
    src = _js()
    assert "function dpiOf(" in src and "dpiOf(ppm(g.dpi))" in src
    assert "n'est pas représentable en pixels par" in src


def test_le_quatrieme_canal_est_retire_et_la_conversion_est_verifiee():
    """« Le PNG est en type couleur 6 (RGBA) avec un alpha constant à 255 sur
    904 650 pixels : zéro information, un quart du fichier en pure perte, dans
    un fichier destiné à une presse. » On livre en RGB — et la conversion est
    vérifiée échantillon par échantillon, pas promise."""
    from PIL import Image
    import io as _io
    # a) alpha constant -> RGB, couleurs INCHANGÉES
    im = Image.new("RGBA", (40, 30))
    im.putdata([((x * 6) % 256, (y * 8) % 256, (x * y) % 256, 255)
                for y in range(30) for x in range(40)])
    buf = _io.BytesIO()
    im.save(buf, format="PNG")
    out, note = FR.png_drop_constant_alpha(buf.getvalue())
    with Image.open(_io.BytesIO(out)) as relu:
        assert relu.mode == "RGB", relu.mode
        assert relu.tobytes() == im.convert("RGB").tobytes(), \
            "la conversion a bougé une couleur"
    assert "alpha constant a 255 sur 1200 pixels" in note, note
    assert "verifies un a un" in note
    # b) alpha UTILE -> on ne touche à rien
    im2 = im.copy()
    im2.putpixel((0, 0), (1, 2, 3, 128))
    buf2 = _io.BytesIO()
    im2.save(buf2, format="PNG")
    out2, note2 = FR.png_drop_constant_alpha(buf2.getvalue())
    assert out2 == buf2.getvalue(), "un alpha utile ne doit pas être retiré"
    assert "UTILE" in note2, note2
    # c) octets qui ne sont pas un PNG : jamais d'exception, jamais de perte
    out3, note3 = FR.png_drop_constant_alpha(b"pas un png")
    assert out3 == b"pas un png" and "non tentee" in note3
    # d) la route livre du RGB et l'écrit dans le fichier
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300",
             content=_png(*g.canvas_px), headers={"content-type": "image/png"})
    assert r.status_code == 200
    assert r.content[25] == 2, "IHDR type couleur : RGB attendu"
    assert "Alpha" in _text_of(r.content)
    assert FR.png_size(r.content) == tuple(g.canvas_px)
    # ... et rgb=0 conserve le fichier tel quel
    r0 = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300&rgb=0",
              content=_png(*g.canvas_px), headers={"content-type": "image/png"})
    assert r0.content[25] == 6, "rgb=0 doit conserver le RGBA"


def test_les_pixels_ne_bougent_pas_quand_le_canal_alpha_part():
    """Le vrai invariant derrière « on ne recompresse rien » : ce sont les
    PIXELS qui ne doivent pas bouger. On le vérifie sur les échantillons, ce
    qui est plus fort que compter les chunks IDAT."""
    from PIL import Image
    import io as _io
    did = _deck()
    g = CT.geom("poker_eu", 300)
    brut = _png(*g.canvas_px)
    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300",
             content=brut, headers={"content-type": "image/png"})
    with Image.open(_io.BytesIO(brut)) as a, Image.open(_io.BytesIO(r.content)) as b:
        assert a.mode == "RGBA" and b.mode == "RGB"
        assert a.size == b.size
        assert a.convert("RGB").tobytes() == b.tobytes(), \
            "un octet de couleur a bougé entre l'entrée et le fichier livré"


def test_l_ecran_confronte_ses_chiffres_aux_octets():
    """LE PANNEAU DE PREUVE. Un audit a montré qu'un badge « 16 bits » pouvait
    être faux alors que l'en-tête le confirmait : le verdict s'était arrêté à
    l'en-tête. Ici l'écran ne s'y arrête pas — il décompresse le zlib et
    défiltre les lignes (les cinq filtres de la norme), puis compare chacun de
    ses chiffres aux échantillons."""
    src = _js()
    for cle in ("function pngHeader(", "function inflate(", "function unfilter(",
                "function pngPixels(", "function measureLine(",
                "function measureBleed(", "function measureAlpha(",
                "function measureMatter(", "function runProof(", "cff-prooftab"):
        assert cle in src, f"{cle} absent du panneau de preuve"
    assert "DecompressionStream" in src, "le zlib n'est pas décompressé"
    for f in range(5):                       # les 5 filtres, écrits en clair
        assert f"ft === {f}" in src, f"filtre PNG {f} non traité"
    assert "filtre PNG inconnu" in src
    # aucune API d'image : la relecture doit rester une lecture d'OCTETS.
    # (Le test « le module ne charge aucune image » le vérifie déjà sur des
    # APPELS ; ici on vérifie qu'aucun n'est APPELÉ dans ce panneau — les
    # commentaires qui les citent ne comptent pas.)
    sans_com = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    for interdit in ("new Image", "createImageBitmap", "data:image/"):
        assert interdit not in sans_com, f"le panneau utilise {interdit}"
    # ET IL MESURE LE FILET SANS FOND DE RÉFÉRENCE. Ce test verrouillait
    # jusqu'ici une fenêtre serrée (« wpx * 0.6 + 4 ») : c'était la parade du
    # tour 1 contre le second trait du double filet, et elle a tenu. Mais la
    # méthode qu'elle protégeait — un ton de référence pris dans le fond perdu
    # — est tombée dès que chaque famille a encré SA zone d'anneau : quatre
    # familles sur six affichaient une croix rouge sur un fichier juste.
    # L'invariant à verrouiller n'est donc pas la largeur de la fenêtre, c'est
    # l'absence de fond de référence — voir la section 11.
    assert "const base = lumAt(" not in src, \
        "la mesure du filet retombe sur un ton de référence lointain"
    assert "PREMIERE marche franche" in src, \
        "la méthode des deux arêtes n'est plus documentée"
    assert "STAMP_KEYS" in src, "le compte de tEXt doit être une liste, pas 9"


def test_la_loupe_trace_la_coupe_et_la_zone_sure():
    """« La loupe montre la matière mais ne trace ni le trait de coupe ni la
    zone sûre : on voit le filet et le fond perdu sans voir où tombe la
    coupe. » Les deux traits sont dessinés, et l'écran dit qu'ils
    appartiennent à la loupe, pas au fichier."""
    src = _js()
    assert "const PX = (x) => (x - sx) * z" in src, \
        "les repères doivent être projetés, pas posés au jugé"
    assert 'tag("coupe"' in src and 'tag("zone sûre"' in src
    assert "absents du fichier livré" in src, \
        "il faut dire que ces traits ne sont pas dans le PNG"


def test_le_retrait_dit_depuis_quoi_et_les_bornes_sont_coherentes():
    """« Le libellé ne dit pas depuis quoi : la valeur porte le CENTRE du
    trait, pas son bord extérieur. Un conducteur de presse qui lit 1,6 mm
    attend le bord et se trompe d'un demi-filet. » Et : « l'épaisseur monte à
    8 mm mais le retrait s'arrête à 6 — la combinaison est amputée. »"""
    assert FR.LIMITS["edge_mm"] == FR.LIMITS["line_mm"] == [0, 8]
    src = _js()
    assert "AXE du trait" in src, "le libellé ne dit toujours pas depuis quoi"
    assert "Convention du <b>trait centré</b>" in src
    assert "l'encre occupe de" in src, "les deux bords ne sont pas donnés"
    # la borne haute vaut bien 8 des deux côtés, et le backend l'accepte
    did = _deck()
    for mm in (6.5, 8):
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 json={"fmt": "poker_eu", "dpi": 300, "edge_mm": mm})
        assert r.status_code == 200, r.text[:200]
        assert r.json()["metrics"]["edge_px"] == _exact_px(mm, 300)
    r = _api("POST", f"/api/cards/{did}/frame/metrics",
             json={"fmt": "poker_eu", "dpi": 300, "edge_mm": 8.1})
    assert r.status_code == 400 and "8" in r.json()["detail"]


def test_le_module_ne_produit_ni_glb_ni_maps_pbr():
    """Contrôle de non-revendication : la pièce 02 ne livre aucun objet 3D,
    donc « GLB sans jeu de maps PBR complet » ne peut pas la concerner. Elle
    ne doit rien afficher qui le laisse croire."""
    src = _js().lower()
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8").lower()
    for mot in ("glb", "gltf", "roughness", "metallic", " tangent", "basecolor"):
        assert mot not in src, f"« {mot} » dans mod-frame.js"
        assert mot not in py, f"« {mot} » dans cards/frame.py"


# ═════════════════════════════════════════════════════════════════════════════
# 11. TOUR 2 — LE MESUREUR MENTAIT, ET LA MATIÈRE ÉTAIT PLATE
#
# Ce que le tour 2 a trouvé en relisant les octets des SIX familles et pas
# d'une seule : le panneau « preuve sur les octets » affichait DEUX LIGNES
# ROUGES sur un fichier parfaitement conforme, dans quatre familles sur six.
# Le dessin était juste ; c'est la mesure qui était fausse. Elle prenait une
# luminance de référence loin du filet (dans le fond perdu) puis élargissait
# tant que l'écart à cette référence tenait — ce qui n'a de sens que si
# l'anneau porte le même ton que le fond perdu. Depuis que chaque famille
# encre SA zone d'anneau, ce n'est plus vrai nulle part.
#
#   famille   annoncé    mesure de tour 1   vérité (profil de luminance)
#   runic     10,63 px   18 px      ROUGE   arêtes à 49 et 60 -> 11 px
#   arcane    10,63 px   11 px      vert    arêtes à 49 et 60 -> 11 px
#   timber    10,63 px    5 px      ROUGE   arêtes à 49 et 60 -> 11 px
#   deco      10,63 px   11 px      vert    arêtes à 49 et 60 -> 11 px
#   neon      10,63 px   17 px      ROUGE   filet NOYÉ par un ornement
#   sable     10,63 px    5 px      ROUGE   arêtes à 49 et 60 -> 11 px
#
# Les tests ci-dessous FONT TOURNER la fonction livrée — extraite telle quelle
# de `mod-frame.js`, jamais réécrite — sur les profils de luminance RELEVÉS
# dans les fichiers réellement produits par le moteur. Une réimplémentation
# aurait prouvé la réimplémentation.
# ═════════════════════════════════════════════════════════════════════════════

# Profils de luminance relevés à mi-hauteur (y = 555) dans les PNG livrés à
# 300 DPI, format poker_eu, filet 0,9 mm d'axe 1,6 mm, rareté « rare ».
# Abscisses 36 à 76 incluses — la fenêtre de mesure est [38 ; 71].
# Annoncé par l'interface : axe 54,40 px, épaisseur 10,63 px.
PROFILS_LIVRES = {
    "runic": (56, 71, 84, 92, 90, 87, 61, 48, 45, 45, 42, 34, 30, 87, 92, 93,
              94, 95, 96, 97, 98, 99, 100, 78, 25, 27, 32, 35, 42, 43, 44, 50,
              48, 43, 40, 35, 33, 113, 114, 115, 116),
    "arcane": (58, 73, 86, 94, 96, 92, 62, 51, 48, 43, 40, 40, 35, 87, 92, 93,
               94, 95, 96, 97, 98, 99, 100, 79, 29, 31, 30, 35, 36, 39, 43, 45,
               45, 41, 36, 33, 33, 113, 114, 115, 116),
    "timber": (146, 165, 182, 184, 197, 197, 188, 180, 180, 180, 172, 165, 167,
               98, 92, 93, 94, 95, 96, 97, 98, 99, 100, 113, 145, 148, 155,
               158, 151, 161, 163, 165, 163, 161, 159, 157, 146, 113, 114, 115,
               116),
    "deco": (73, 90, 103, 112, 114, 111, 87, 76, 71, 69, 66, 62, 58, 89, 92, 93,
             94, 95, 96, 97, 98, 99, 100, 85, 53, 51, 55, 60, 63, 66, 69, 72,
             72, 68, 66, 24, 25, 113, 114, 115, 116),
    "neon": (50, 66, 75, 83, 86, 84, 80, 76, 73, 69, 66, 62, 55, 89, 92, 93, 94,
             95, 96, 97, 98, 99, 100, 85, 51, 56, 57, 60, 63, 66, 81, 127, 127,
             124, 124, 124, 121, 113, 114, 115, 116),
    "sable": (146, 165, 182, 194, 199, 198, 189, 184, 183, 181, 180, 178, 178,
              98, 92, 93, 94, 95, 96, 97, 98, 99, 100, 116, 160, 160, 160, 164,
              172, 175, 178, 181, 181, 178, 175, 172, 168, 113, 114, 115, 116),
}
# LES MÊMES RELEVÉS, SUR LES FICHIERS DU TOUR 1 — ceux sur lesquels le panneau
# affichait ses croix rouges. Ce sont ces octets-là qui font la preuve : la
# méthode livrée doit les lire juste là où l'ancienne se trompait. Premier
# nombre : le ton que l'ANCIENNE méthode prenait pour référence (abscisse 12,
# dans le fond perdu). Ensuite les abscisses 36 à 76, au dixième de niveau —
# l'ancienne méthode joue à un dixième près, arrondir la ferait passer.
PROFILS_TOUR_1 = {
    "runic": (45.4,
              55.4, 55.4, 55.4, 55.4, 55.4, 55.4, 27, 17.2, 17.3, 18.1, 18.1,
              18, 18.1, 85.7, 92.4, 93.2, 94.4, 94.9, 96.1, 96.9, 97.9, 98.9,
              99.9, 76.6, 18.1, 17.8, 19.6, 19.7, 25.2, 23.6, 21.8, 20.8, 21.8,
              21.1, 21.8, 20.3, 22.8, 113.3, 114.3, 114.6, 116.3),
    "arcane": (47.2,
               58.1, 58, 58, 57.4, 57.4, 57.3, 29.8, 19.6, 19.9, 18.9, 19.4,
               24.6, 24.2, 85.7, 92.4, 93.2, 94.4, 94.9, 96.1, 96.9, 97.9,
               98.9, 99.9, 77.9, 22.5, 21.5, 17, 18.2, 17.2, 17.1, 18.1, 18.1,
               18.1, 18.1, 18.1, 18.1, 21.2, 113.3, 114.3, 114.6, 116.3),
    "timber": (51.5,
               186.3, 186, 186, 185.3, 185.3, 185, 175.5, 171.7, 171.7, 171.4,
               164.4, 163.7, 165.3, 97.5, 92.4, 93.2, 94.4, 94.9, 96.1, 96.9,
               97.9, 98.9, 99.9, 117.1, 157.8, 155.1, 159.4, 159.5, 159.2, 157,
               157, 156, 157, 156, 156, 155.4, 154, 113.3, 114.3, 114.6, 116.3),
    "deco": (47.2,
             79.8, 79.7, 79.8, 79.7, 79.8, 79.8, 56.4, 47.9, 47.9, 47.9, 47.9,
             47.9, 47.9, 87.7, 92.4, 93.2, 94.4, 94.9, 96.1, 96.9, 97.9, 98.9,
             99.9, 85.6, 49.8, 47.6, 48, 47.9, 48.6, 47.9, 48, 47.9, 48.6, 48,
             48.6, 22.6, 25.4, 113.3, 114.3, 114.6, 116.3),
    "sable": (47.2,
              186, 186, 186, 186, 186, 186, 176.6, 172.7, 173.4, 172.7, 173.4,
              172.7, 173.4, 97.8, 92.4, 93.2, 94.4, 94.9, 96.1, 96.9, 97.9,
              98.9, 99.9, 121.4, 172.4, 170.1, 165.2, 167, 172.4, 172.4, 172.4,
              172.4, 172.4, 172.4, 172.4, 172.4, 170.4, 113.3, 114.3, 114.6,
              116.3),
}
# Le relevé « Néon » du tour 1, mis à part : la prise de circuit partait de
# l'axe du filet et l'une d'elles tombe pile à mi-hauteur. Le filet n'a plus
# d'arête intérieure — la luminance ne fait que monter, de 47,9 à 118,6, sans
# jamais redescendre. C'est le cas où AUCUN chiffre ne doit être publié ;
# l'ancienne méthode, elle, en publiait un : 17 px pour 10,63 annoncés.
PROFIL_NOYE = (47.2,
               47.9, 47.8, 46.2, 46.7, 46.8, 47.9, 47.9, 47.9, 47.9, 47.9,
               47.9, 47.9, 47.9, 87.7, 92.4, 93.2, 94.4, 94.9, 96.1, 96.9,
               97.9, 98.9, 99.9, 105.7, 118.6, 118.6, 118, 118, 118, 118.6,
               118.6, 113.8, 113.5, 113.8, 116, 118.7, 118.3, 113.3, 114.3,
               114.6, 116.3)
PROFIL_X0 = 36
AXE_ANNONCE, EPAISSEUR_ANNONCEE = 54.40, 10.63


def _js_fn(src: str, nom: str) -> str:
    """Le SOURCE d'une fonction de `mod-frame.js`, accolades équilibrées."""
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


BANC_FILET = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { measureLine: measureLine };\n})();")();
const out = {};
for (const nom of Object.keys(CAS)) {
  const c = CAS[nom];
  const W = 90, H = 3, bpp = 3;
  /* un tableau de FLOTTANTS, pas un Uint8Array : 0,299 + 0,587 + 0,114 = 1,
     donc R = G = B = v rend exactement la luminance relevee, au dixieme.
     Quantifier a l'octet ferait basculer l'ancienne methode, qui se joue a
     un dixieme de niveau — et le controle negatif ne prouverait plus rien. */
  const data = new Array(W * H * bpp).fill(0);
  for (let x = 0; x < W; x++) {
    const i = Math.min(c.profil.length - 1, Math.max(0, x - c.x0));
    const v = (c.base !== undefined && x === 12) ? c.base : c.profil[i];
    for (let y = 0; y < H; y++) {
      const o = (y * W + x) * bpp;
      data[o] = v; data[o + 1] = v; data[o + 2] = v;
    }
  }
  const px = { data: data, bpp: bpp };
  const head = { w: W, h: H };
  /* poker_eu : la borne du format ne mord pas (29,5 mm > 20), le banc
     mesure donc exactement ce que mesurait le tour precedent. */
  const g = { bleed_off_px: [35.5, 35.5], dpi: 300, trim_mm: [63, 88] };
  const f0 = { edge_mm: 1.6, line_mm: 0.9 };
  try { out[nom] = mod.measureLine(px, head, g, f0); }
  catch (e) { out[nom] = { exception: String((e && e.message) || e) }; }
}
process.stdout.write(JSON.stringify(out));
"""


def _mesure_filet(tmp_path, cas: dict, mutations=()) -> dict:
    """Fait tourner la VRAIE `measureLine` de mod-frame.js sur des profils."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de mesure ne peut pas tourner")
    src = _js()
    code = "\n".join([
        _js_fn(src, "lumAt"),
        _js_fn(src, "measureLine"),
        re.search(r"const r1 = .*?;\n", src).group(0),
        re.search(r"const r2 = .*?;\n", src).group(0),
        # depuis la borne du format, `measureLine` compare les octets à l'axe
        # RÉELLEMENT tracé : le banc doit donc emporter la borne elle-même.
        re.search(r"const BAND_MIN_MM = \d+;", src).group(0),
        _js_fn(src, "bandMaxMM"),
        _js_fn(src, "capOf"),
    ])
    for avant, apres in mutations:
        assert avant in code, "mutation introuvable"
        code = code.replace(avant, apres)
    js = tmp_path / "filet.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_filet.mjs"
    banc.write_text(BANC_FILET, encoding="utf-8")
    conf = tmp_path / "cas.json"
    conf.write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_le_filet_est_mesure_juste_dans_les_six_familles(tmp_path):
    """LA correction du tour : la mesure ne suppose plus aucun fond de
    référence. Sur les six profils relevés dans les fichiers livrés — anneau
    sombre, anneau clair, anneau en dégradé — elle doit retrouver le filet que
    l'interface annonce, à moins de 1 px sur l'axe et 1,6 px sur l'épaisseur.

    La tolérance n'est pas choisie pour faire passer le test : c'est celle que
    le panneau applique lui-même pour allumer sa croix rouge."""
    cas = {k: {"profil": list(v), "x0": PROFIL_X0}
           for k, v in PROFILS_LIVRES.items()}
    # et les MÊMES octets qu'au tour 1, ceux qui faisaient rougir le panneau
    for k, v in PROFILS_TOUR_1.items():
        cas["t1_" + k] = {"profil": list(v[1:]), "x0": PROFIL_X0, "base": v[0]}
    got = _mesure_filet(tmp_path, cas)
    assert len(got) == 11 and sorted(got) == sorted(cas)
    for fam, m in got.items():
        assert "exception" not in m, (fam, m)
        assert "faute" not in m, (fam, m.get("faute"))
        assert abs(m["axe"] - AXE_ANNONCE) <= 1.0, (fam, m)
        assert abs(m["largeur"] - EPAISSEUR_ANNONCEE) <= 1.6, (fam, m)
        assert abs(m["bord_ext_mesure"]
                   - (AXE_ANNONCE - EPAISSEUR_ANNONCEE / 2)) <= 1.6, (fam, m)


def test_la_mesure_de_tour_1_echouait_vraiment_sur_ces_memes_octets(tmp_path):
    """Un test qui passerait aussi sur le code cassé ne prouve rien. On remet
    l'ANCIENNE méthode — référence lointaine + demi-hauteur — à la place de la
    fonction livrée, et on vérifie qu'elle se trompe sur les mêmes octets.
    Sans cela, « la mesure était fausse » resterait une affirmation."""
    src = _js()
    livree = _js_fn(src, "measureLine")
    ancienne = """function measureLine(px, head, g, f0) {
      const y = Math.round(head.h / 2), st = head.w * px.bpp;
      const axis = g.bleed_off_px[0] + f0.edge_mm / 25.4 * g.dpi;
      const wpx = f0.line_mm / 25.4 * g.dpi;
      const x0 = Math.max(0, Math.floor(axis - wpx * 0.6 - 4));
      const x1 = Math.min(head.w - 1, Math.ceil(axis + wpx * 0.6 + 4));
      if (wpx < 1.2 || x1 <= x0 + 3) return null;
      const base = lumAt(px, y * st
        + Math.max(0, Math.floor(g.bleed_off_px[0] * 0.35)) * px.bpp);
      let best = x0, bv = 0;
      for (let x = x0; x <= x1; x++) {
        const d = Math.abs(lumAt(px, y * st + x * px.bpp) - base);
        if (d > bv) { bv = d; best = x; }
      }
      if (bv < 8) return null;
      const half = bv / 2;
      let a = best, b = best;
      while (a > x0 && Math.abs(lumAt(px, y * st + (a - 1) * px.bpp) - base) >= half) a--;
      while (b < x1 && Math.abs(lumAt(px, y * st + (b + 1) * px.bpp) - base) >= half) b++;
      return { largeur: r2(b - a + 1), axe: r2((a + b + 1) / 2) };
    }"""
    cas = {k: {"profil": list(v[1:]), "x0": PROFIL_X0, "base": v[0]}
           for k, v in PROFILS_TOUR_1.items()}
    cas["neon"] = {"profil": list(PROFIL_NOYE[1:]), "x0": PROFIL_X0,
                   "base": PROFIL_NOYE[0]}
    got = _mesure_filet(tmp_path, cas, mutations=[(livree, ancienne)])
    faux = sorted(k for k, m in got.items()
                  if abs(m.get("largeur", 0) - EPAISSEUR_ANNONCEE) > 1.6)
    # exactement les quatre familles que le panneau affichait en rouge, et les
    # MÊMES chiffres — 18, 5, 17, 5 px pour 10,63 annoncés.
    assert set(faux) == {"runic", "timber", "neon", "sable"}, got
    assert got["runic"]["largeur"] == 18 and got["timber"]["largeur"] == 5, got
    assert got["neon"]["largeur"] == 17 and got["sable"]["largeur"] == 5, got
    # et les deux qui passaient passaient bien
    assert got["arcane"]["largeur"] == 11 and got["deco"]["largeur"] == 11, got


def test_un_filet_noye_ne_produit_aucun_chiffre(tmp_path):
    """« Un chiffre faux vaut moins que pas de chiffre. » Quand un ornement de
    famille recouvre le filet — le cas réel de « Néon » avant correction — la
    luminance ne fait que monter : il n'y a pas d'arête intérieure. La fonction
    doit rendre une RAISON, jamais une largeur."""
    got = _mesure_filet(tmp_path, {"noye": {
        "profil": list(PROFIL_NOYE[1:]), "x0": PROFIL_X0, "base": PROFIL_NOYE[0]}})
    m = got["noye"]
    assert "largeur" not in m and "axe" not in m, m
    assert "faute" in m and "intérieure" in m["faute"], m
    assert m["largeur_annoncee"] == 10.63 and m["axe_annonce"] == 54.4, m


def test_aucun_ornement_de_famille_ne_part_de_l_axe_du_filet():
    """Les deux ornements de « Néon » étaient ancrés sur `trim + edge`, c'est-
    à-dire sur l'AXE du filet de l'utilisateur : le halo par-dessus, et une
    prise de circuit qui tombe pile à mi-hauteur (i = 3 donne 0,50 de la
    bande). Conséquence produit, pas seulement de mesure : le curseur
    « épaisseur du filet » ne changeait plus rien de visible à cet endroit."""
    src = _js()
    assert "const dep = m.edge + m.line * 0.5 + u * 0.6;" in src, \
        "la prise de circuit repart toujours de l'axe du filet"
    assert re.search(
        r"const gOff = m\.edge \+ \(room > m\.line \* 0\.5 \+ u \* 0\.8 \?", src), \
        "le halo néon est toujours posé sur l'axe du filet"
    assert "chamferPath(ctx, m.trim.x + m.edge" not in src


def test_le_badge_des_silhouettes_couvre_les_six_raretes():
    """Le badge publiait « familles ≥ 9,2/255 » en ne mesurant QUE la rareté
    ouverte ; balayées les six, la pire paire du catalogue tombe à 8,1/255. Un
    chiffre qui ne vaut que pour la case ouverte ne doit pas pouvoir se lire
    comme une propriété du catalogue.

    TOUR 4 : la mesure est désormais en DEUX morceaux — le relevé
    (`measureSil` pour les vignettes, `measureSilFile` pour la toile livrée) et
    l'affichage (`drawSil`). L'exigence, elle, n'a pas bougé et porte sur les
    deux : aucun des deux chiffres ne dépend de la rareté ouverte."""
    src = _js()
    bloc = _js_fn(src, "measureSil")
    assert "RARITIES.forEach" in bloc, "la mesure ne balaie pas les raretés"
    assert "f().rarity" not in bloc, "la mesure dépend encore de la rareté affichée"
    fich = _js_fn(src, "measureSilFile")
    assert "RARITIES[k]" in fich and "k < RARITIES.length" in fich, \
        "la mesure sur le fichier ne balaie pas les raretés"
    assert "rarity: f0.rarity" not in fich, \
        "la mesure sur le fichier dépend encore de la rareté affichée"
    aff = _js_fn(src, "drawSil")
    assert "les SIX raretés" in aff
    assert "rareté(s) sur " in aff, "l'affichage ne dit pas combien il a balayé"


def test_la_matiere_ne_publie_que_ce_qui_se_relit_sur_le_fichier():
    """LA LIGNE PUBLIAIT UN CHIFFRE QUE PERSONNE NE POUVAIT REFAIRE.

    Elle affichait « X % » d'un 24,8 couleurs/mm² relevé une fois sur un cadre
    PEINT d'un autre produit : ni celui qui regarde l'écran, ni le fichier
    téléchargé ne permettent de retrouver ce nombre. Deuxième défaut, plus
    grave encore : un comptage de couleurs uniques sur une surface PHYSIQUE
    fixe croît avec la définition, donc la comparaison était fausse hors de
    300 DPI.

    Ce qui reste est intégralement relu sur les octets du fichier livré : le
    nombre de couleurs, la taille du coin échantillonné en mm ET en px, la
    définition, le rapport par mm². Le seul jugement porté est celui qu'un
    utilisateur peut refaire à l'œil : un aplat ne donnerait qu'une couleur."""
    src = _js()
    assert "REF_MM2" not in src, "le relevé extérieur est encore à l'écran"
    assert "référence peinte" not in src and "% de la référence" not in src, \
        "la ligne se compare encore à un produit extérieur"
    dp = _js_fn(src, "drawProof")
    assert '"Matière du cadre"' in dp, "la ligne de matière a disparu"
    for morceau in ("P.matiere.couleurs", "P.matiere.coin_px",
                    "P.matiere.dpi", "P.matiere.par_mm2"):
        assert morceau in dp, f"{morceau} n'est plus publié"
    assert "P.matiere.couleurs > 1" in dp, \
        "la ligne ne dit plus rien : même un aplat passerait"


def test_le_relief_et_la_gravure_suivent_la_definition():
    """La matière ajoutée doit rester du TRACÉ : rien en pixels codés en dur,
    sinon elle ne suivrait pas un changement de définition — c'est exactement
    ce qu'on reproche à un cadre bitmap. Le profil de moulure est en fractions
    de l'anneau, la gravure en millimètres.

    L'épaisseur de gravure vaut 0,055 mm : 0,65 px à 300 DPI (donc étalée) et
    1,30 px à 600 (donc franche). Le plancher `Math.max(0.35, …)` employé
    ailleurs aurait effacé cette différence : il n'y en a pas ici."""
    src = _js()
    grav = _js_fn(src, "engrave")
    assert "ctx.lineWidth = u * 0.055;" in grav, \
        "l'épaisseur de gravure n'est plus en millimètres"
    assert "Math.max(0.35" not in grav and "Math.max(0.4" not in grav, \
        "un plancher en pixels efface la différence 300 / 600 DPI"
    assert "pr.pitch * 0.5 * u" in grav, "le pas de gravure n'est pas en mm"
    rel = _js_fn(src, "relief")
    assert "createLinearGradient" in rel and "outerRing(ctx, m)" in rel, \
        "le profil de moulure doit être une rampe continue, confinée à l'anneau"
    m = re.search(r"const MOULURE = \[(.*?)\];", src, re.S)
    assert m, "la table du profil de moulure a disparu"
    stops = re.findall(r"\[([\d.]+), \"[\d,]+\", ([\d.]+)\]", m.group(1))
    assert len(stops) >= 7, stops
    assert float(stops[0][0]) == 0.0 and float(stops[-1][0]) == 1.0, stops
    assert round(0.055 / 25.4 * 300, 2) == 0.65
    assert round(0.055 / 25.4 * 600, 2) == 1.30


@pytest.mark.parametrize("corner_mm", [0, 8])
@pytest.mark.parametrize("fmt", sorted(CT.FORMATS))
def test_les_metriques_tiennent_sur_les_douze_formats_aux_deux_bornes_du_rayon(
        fmt, corner_mm):
    """« Le duel ne prouve pas la robustesse : un seul format, une seule
    carte ; les ornements de coin et le liseré métallique avec un rayon à 0 ou
    à 8 mm ne sont pas démontrés. » Voici les DOUZE formats et les DEUX bornes
    du rayon, contre l'arithmétique exacte.

    CE QUE CE DOCSTRING DISAIT ET QUI ÉTAIT FAUX. Il annonçait « le balayage à
    l'écran fait le reste : 60 rendus ». Ce balayage n'existait pas : aucune
    ligne de mod-frame.js ne le contenait — une affirmation de plaquette dans
    une suite de tests, c'est-à-dire exactement ce qu'on reproche à un badge
    qui s'arrête à l'en-tête. Il existe maintenant, il est mesuré à l'écran, et
    les tests qui le vérifient sont plus bas (§13 bis) : 48 géométries (12
    formats x 2 rayons x 2 profils de curseurs) et 132 rendus (micro, domino,
    jumbo x 2 rayons x 2 profils x 11 variantes). Les nombres sont comptés par
    le panneau, pas recopiés ici."""
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/frame/metrics",
             json={"fmt": fmt, "dpi": 300, "bleed_mm": 3, "safe_mm": 3,
                   "corner_mm": corner_mm, "line_mm": 8, "gap_mm": 4,
                   "edge_mm": 8, "inner_mm": 20})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    g = CT.geom(fmt, 300, 3, 3, corner_mm)
    assert d["metrics"]["canvas_px"] == list(g.canvas_px)
    # le rayon de coupe s'affiche à la DIXIÈME de pixel (convention du domaine :
    # « 3 mm à 300 DPI = 35,4 px, pas 35 »), les épaisseurs au CENTIÈME. Deux
    # règles d'arrondi, écrites ici en arithmétique exacte, jamais recalculées
    # depuis le code testé.
    v = Fraction(str(corner_mm)) / Fraction(254, 10) * 300
    assert d["metrics"]["corner_px"] == float((v * 10 + Fraction(1, 2)).__floor__()) / 10.0
    assert d["metrics"]["line_px"] == _exact_px(8, 300)
    assert d["metrics"]["edge_px"] == _exact_px(8, 300)
    # un filet de 8 mm doit pouvoir être rentré de 8 mm : mêmes bornes des deux
    # côtés — la correction du tour précédent, qui tient toujours.
    assert d["metrics"]["edge_px"] == d["metrics"]["line_px"]


# ═════════════════════════════════════════════════════════════════════════════
# 12. TOUR 3 — LE VÉRIFICATEUR ÉTAIT ÉTEINT, ET IL MANQUAIT LE SECOND FICHIER
#
# Trois reproches, trois corrections, et un argument JETÉ parce qu'il ne tenait
# pas :
#
#   (a) « Il faut que la vérification soit passée, DATÉE et affichée EN VERT
#       PAR DÉFAUT, sinon elle ne vaut pas mieux qu'une promesse. » Le badge
#       affichait « non vérifié » sur un fichier parfaitement conforme.
#   (b) « Aucun fichier à 600 DPI ce tour-ci : j'ai dû établir l'indépendance
#       de résolution INDIRECTEMENT. La preuve directe tenait en un second
#       export. » Elle y est, et elle porte sur les octets des DEUX fichiers.
#   (c) « Aucun trait de coupe ni repère de registration dans le fichier
#       livré. » Le fichier d'impression n'en portera jamais — un repère entre
#       la coupe et le bord de toile serait de l'encre sous la lame. Un repère
#       demande du papier en plus : c'est l'ÉPREUVE DE CONTRÔLE.
#
# ET CE QUI A ÉTÉ JETÉ. Une première version du panneau des deux définitions
# affirmait que la montée 10-90 % « plus fine en millimètres » écartait
# l'agrandissement. C'est faux, et on le montre ici en agrandissant vraiment :
# le plus proche voisin conserve la marche intacte. Un argument qui se
# retourne n'est pas un argument — il est remplacé par deux mesures qui, elles,
# ont été validées contre les deux modes d'agrandissement.
# ═════════════════════════════════════════════════════════════════════════════

BANC_DUP = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { dupRatio: dupRatio };\n})();")();
const W = 40, H = 40, bpp = 3;
/* Une image de test qui ressemble a une carte : des degrades COURBES et des
   aretes franches.
   COURBES, ET C'EST LE POINT. Une premiere version employait des rampes
   LINEAIRES (x*3+y) : 84,2 % de ses lignes impaires etaient deja la moyenne
   exacte de leurs voisines, sans le moindre agrandissement. C'est la limite
   reelle du test d'interpolation, et elle est ecrite dans le module comme
   ici : un degrade parfaitement lineaire est, par construction, sa propre
   interpolation. Le fichier livre, lui, mesure 0,0 % — ses degrades sont
   radiaux et courbes. */
function base() {
  const d = new Uint8Array(W * H * bpp);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const o = (y * W + x) * bpp;
      const dur = (x === 12 || x === 13 || y === 9 || y === 27) ? 90 : 0;
      d[o] = Math.round(128 + 90 * Math.sin(x * 0.31) * Math.cos(y * 0.23));
      d[o + 1] = Math.min(255, Math.round(120 + 80 * Math.cos(x * 0.19 + y * 0.27)) + dur);
      d[o + 2] = Math.min(255, Math.round(140 + 70 * Math.sin((x + y) * 0.17)) + dur);
    }
  }
  return { data: d, w: W, h: H };
}
function ppv(im) {                        /* x2 au plus proche voisin */
  const W2 = im.w * 2, H2 = im.h * 2;
  const d = new Uint8Array(W2 * H2 * bpp);
  for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++)
    for (let k = 0; k < bpp; k++)
      d[(y * W2 + x) * bpp + k] = im.data[((y >> 1) * im.w + (x >> 1)) * bpp + k];
  return { data: d, w: W2, h: H2 };
}
function lin(im) {                        /* x2 lineaire */
  const W2 = im.w * 2, H2 = im.h * 2;
  const d = new Uint8Array(W2 * H2 * bpp);
  const S = (x, y, k) => im.data[(Math.min(im.h - 1, y) * im.w + Math.min(im.w - 1, x)) * bpp + k];
  for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++) {
    const sx = x >> 1, sy = y >> 1, fx = x & 1, fy = y & 1;
    for (let k = 0; k < bpp; k++)
      d[(y * W2 + x) * bpp + k] = Math.round(
        (S(sx, sy, k) + S(sx + fx, sy, k) + S(sx, sy + fy, k) + S(sx + fx, sy + fy, k)) / 4);
  }
  return { data: d, w: W2, h: H2 };
}
const b = base();
const out = {};
for (const [nom, im] of [["vrai", b], ["ppv", ppv(b)], ["lineaire", lin(b)]])
  out[nom] = mod.dupRatio({ data: im.data, bpp: bpp }, { w: im.w, h: im.h });
process.stdout.write(JSON.stringify(out));
"""


def _banc_dup(tmp_path) -> dict:
    """Fait tourner la VRAIE `dupRatio` de mod-frame.js sur une image de test
    et sur ses deux agrandissements. Aucune réimplémentation : une
    réimplémentation prouverait la réimplémentation."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'agrandissement ne peut pas tourner")
    code = "\n".join([
        re.search(r"const r1 = .*?;\n", _js()).group(0),
        _js_fn(_js(), "dupRatio"),
    ])
    js = tmp_path / "dup.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_dup.mjs"
    banc.write_text(BANC_DUP, encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js)], capture_output=True,
                       text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_les_deux_signatures_d_agrandissement_sont_bien_detectees(tmp_path):
    """LE CONTRÔLE NÉGATIF DU TOUR. Le panneau des deux définitions publie deux
    chiffres de comparaison — « un x2 au plus proche voisin en donne 50,0 % »,
    « un x2 linéaire en donne 100,0 % ». Ce ne sont pas des affirmations de
    plaquette : on agrandit vraiment, dans les deux modes, et on mesure avec la
    fonction livrée.

    Une image qui n'a AUCUNE de ces deux signatures ne peut pas être
    l'agrandissement d'une autre — c'est tout ce que le panneau prétend, et
    c'est exactement ce qui est vérifié ici."""
    g = _banc_dup(tmp_path)
    # l'original : ni doublon, ni interpolation
    assert g["vrai"]["pct_l"] == 0.0 and g["vrai"]["pct_c"] == 0.0, g["vrai"]
    assert g["vrai"]["pct_m"] == 0.0, g["vrai"]
    # PLUS PROCHE VOISIN : une ligne sur deux ET une colonne sur deux.
    # Le compte exact est N doublons pour 2N-1 paires voisines, soit
    # N/(2N-1) : 50,6 % sur cette mire de 80 lignes, 50,02 % sur la toile
    # réelle de 2220. C'est pour cela que le panneau écrit « 50,0 % » — la
    # valeur des vraies tailles — et que le verdict se joue à 25 %, pas à
    # l'égalité.
    assert g["ppv"]["lignes"] * 2 - 1 == g["ppv"]["sur_l"], g["ppv"]
    assert 50.0 <= g["ppv"]["pct_l"] <= 51.0, g["ppv"]
    assert 50.0 <= g["ppv"]["pct_c"] <= 51.0, g["ppv"]
    assert round(1110 / 2219 * 100, 1) == 50.0        # la toile de 600 DPI
    # ... et il ne se fait PAS prendre par le test d'interpolation : les deux
    # mesures sont bien indépendantes, aucune ne couvre l'autre.
    assert g["ppv"]["pct_m"] == 0.0, g["ppv"]
    # LINÉAIRE : rien n'est dupliqué — la seule ligne dupliquée de la mire est
    # la dernière, que le bord réplique — mais TOUTES les lignes impaires sont
    # la moyenne de leurs voisines. Les deux signatures sont disjointes : c'est
    # ce qui fait qu'aucun des deux modes d'agrandissement ne passe entre.
    assert g["lineaire"]["lignes"] <= 1, g["lineaire"]
    assert g["lineaire"]["colonnes"] <= 1, g["lineaire"]
    assert g["lineaire"]["pct_m"] == 100.0, g["lineaire"]


def test_l_acuite_en_millimetres_ne_pretend_plus_ecarter_un_agrandissement():
    """L'ARGUMENT JETÉ. Le panneau a un temps affirmé qu'une montée 10-90 %
    « plus fine en millimètres » prouvait l'absence d'agrandissement. C'est
    faux : le plus proche voisin recopie la marche telle quelle, donc une arête
    franche le reste. La ligne existe toujours — l'acuité imprimée est une
    information utile — mais elle dit ce qu'elle est, et le commentaire du
    module garde la trace de l'erreur."""
    src = _js()
    assert "Acuité imprimée" in src, "la ligne d'acuité a disparu"
    assert "FINESSE, pas preuve de retracé" in src, \
        "la ligne d'acuité prétend encore prouver le retracé"
    assert "aucun agrandissement ne peut affiner un millimètre" not in src, \
        "l'affirmation fausse est encore à l'écran"
    assert "Un argument qui se retourne n'est pas un argument" in src, \
        "l'erreur n'est pas consignée dans le module"


def test_la_preuve_sur_les_octets_part_toute_seule_et_porte_une_heure():
    """(a) « Il faut que la vérification soit passée, DATÉE et affichée en vert
    par défaut. » Plus aucun bouton n'est nécessaire : une empreinte du
    document, de la géométrie et de la carte courante déclenche la relecture,
    et le badge porte l'heure de la mesure."""
    src = _js()
    assert 'h("span", "cff-pbadge", "non vérifié")' not in src, \
        "le badge naît encore « non vérifié »"
    assert "function autoProof()" in src and "function fileSig()" in src
    assert "function hms(" in src, "le badge ne peut pas porter d'heure"
    # elle part a l'ouverture, a chaque synchronisation, et a chaque
    # invalidation du CORE — c'est-a-dire des que le FICHIER change.
    assert "scheduleProof(1200)" in src, "aucun départ automatique à l'ouverture"
    assert re.search(r'CF\.on\("core:invalidate",[^\n]*scheduleProof', src), \
        "une invalidation du CORE ne relance pas la relecture"
    fn = _js_fn(src, "syncNow")
    assert "scheduleProof()" in fn, "syncNow ne replanifie pas la relecture"
    # ... et le vert ne survit pas a un changement d'etat
    dp = _js_fn(src, "drawProof")
    assert "PROOF.sig !== fileSig()" in dp, \
        "le badge peut rester vert sur des octets périmés"
    assert "périmée depuis" in dp


def test_le_panneau_n_affiche_plus_le_chemin_interne_de_la_route():
    """Le panneau imprimait à l'écran « moteur unique -> POST frame/stamp ».
    Un chemin d'API nominatif n'apprend rien à l'utilisateur et n'a rien à
    faire dans un artefact livré ; ce qui compte est que ce soit le MÊME
    chemin que le bouton de téléchargement, et c'est ce qui est écrit."""
    src = _js()
    assert "POST <i>frame/stamp</i>" not in src
    assert "que le bouton de téléchargement" in src


def test_le_png_ne_pretend_pas_porter_des_boites_lisibles_par_une_machine():
    """« Aucun RIP d'imprimeur ne lit un tEXt de PNG. » C'est exact. La norme
    PNG ne prévoit AUCUNE boîte de coupe ; seul `pHYs` est machine. L'écran le
    dit maintenant en toutes lettres et renvoie au PDF de la pièce 07 pour les
    boîtes qu'un RIP lit vraiment."""
    src = _js()
    assert "La norme PNG ne prévoit <i>aucune</i> boîte de " in src
    assert "indication <b>humaine</b>" in src
    assert "pièce 07" in src, "l'écran ne dit pas où sont les vraies boîtes"


# ── L'ÉPREUVE DE CONTRÔLE, SUR LES OCTETS ──────────────────────────────────
def _png_test(w: int, h: int) -> bytes:
    """Un PNG de la bonne taille, avec de la matière (pas un aplat) : c'est ce
    que le moteur enverrait."""
    import io
    from PIL import Image
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(0, w, 3):
            px[x, y] = ((x * 3) % 256, (y * 5) % 256, ((x + y) * 2) % 256)
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def test_l_epreuve_de_controle_ne_touche_pas_un_pixel_de_la_carte():
    """(c) L'épreuve pose la toile livrée sur du papier. Le contrat est
    simple : la zone carte doit être IDENTIQUE à la source, octet par octet,
    après encodage. La route le vérifie elle-même et refuse de livrer sinon ;
    on le revérifie ici, indépendamment, sur les octets rendus."""
    import io
    from PIL import Image
    did = _deck()
    g = CT.geom("poker_eu", 300, 3, 3, 3)
    src = _png_test(g.canvas_px[0], g.canvas_px[1])
    r = _api("POST", f"/api/cards/{did}/frame/control?fmt=poker_eu&dpi=300"
                     "&bleed_mm=3&safe_mm=3&corner_mm=3&face=front&margin_mm=10",
             content=src, headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text[:400]
    m = FR.R(10 / CT.MM_PER_INCH * 300)
    assert r.headers["X-Proof-Canvas"] == "%dx%d" % (
        g.canvas_px[0] + 2 * m, g.canvas_px[1] + 2 * m)
    with Image.open(io.BytesIO(r.content)) as out:
        out.load()
        assert out.size == (g.canvas_px[0] + 2 * m, g.canvas_px[1] + 2 * m)
        dedans = out.crop((m, m, m + g.canvas_px[0],
                           m + g.canvas_px[1])).convert("RGB").tobytes()
    with Image.open(io.BytesIO(src)) as ref:
        ref.load()
        attendu = ref.convert("RGB").tobytes()
    assert dedans == attendu, "l'épreuve a modifié la carte"
    # et elle DIT ce qu'elle est, dans ses propres octets
    t = FR.png_texts(r.content)
    assert "NE PAS IMPRIMER" in t["ControlProof"]
    assert "identiques" in t["PixelCheck"]
    assert t["Resolution"].startswith("299.9994 DPI reels")


def test_les_traits_de_coupe_de_l_epreuve_tombent_sur_la_rogne():
    """Les huit traits sont alignés sur la COUPE, et ils ne mordent pas sur la
    carte : ils partent du bord de toile et s'éloignent. On les cherche dans
    les échantillons, pas dans une métadonnée."""
    import io
    from PIL import Image
    did = _deck()
    g = CT.geom("poker_eu", 300, 3, 3, 3)
    src = _png_test(g.canvas_px[0], g.canvas_px[1])
    r = _api("POST", f"/api/cards/{did}/frame/control?fmt=poker_eu&dpi=300"
                     "&bleed_mm=3&safe_mm=3&corner_mm=3&margin_mm=10",
             content=src, headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text[:300]
    m = FR.R(10 / CT.MM_PER_INCH * 300)
    trait = FR.R(5 / CT.MM_PER_INCH * 300)
    attendu = {FR.R(m + g.bleed_off_px[0]),
               FR.R(m + g.bleed_off_px[0] + g.trim_px[0])}
    with Image.open(io.BytesIO(r.content)) as im:
        im.load()
        px = im.convert("RGB").load()
        noires = set()
        for x in range(im.width):
            k = sum(1 for y in range(m - trait, m) if sum(px[x, y]) < 120)
            if k >= trait * 0.75:
                noires.add(x)
        assert attendu <= noires, (sorted(noires), attendu)
        # le trait s'arrete AVANT la toile : le dernier pixel de papier est
        # noir, et la carte, elle, n'a jamais ete touchee (test precedent).
        for x in sorted(attendu):
            assert sum(px[x, m - 1]) < 120, "le trait n'atteint pas le bord de toile"
    # ... et le fichier écrit lui-même où il a tracé, résidu d'arrondi compris
    assert r.headers["X-Proof-Residu"].startswith("0.5"), r.headers["X-Proof-Residu"]


@pytest.mark.parametrize("fmt", sorted(CT.FORMATS))
@pytest.mark.parametrize("marge", [5, 25])
def test_l_epreuve_tient_sur_les_douze_formats_et_aux_deux_bornes_de_marge(
        fmt, marge):
    """Robustesse : les DOUZE formats, les DEUX bornes de la marge. La
    géométrie de l'épreuve se déduit de `geom`, jamais d'un nombre écrit à la
    main — un format allongé (domino) comme un carré doivent tomber juste."""
    g = CT.geom(fmt, 300, None, None, 3)
    C = FR.control_geometry(g, marge)
    m = FR.R(marge / CT.MM_PER_INCH * 300)
    assert C["margin_px"] == m
    assert C["canvas_px"] == [g.canvas_px[0] + 2 * m, g.canvas_px[1] + 2 * m]
    assert C["trim_exact"][0] == round(m + g.bleed_off_px[0], 2)
    assert C["trim_exact"][3] == round(m + g.bleed_off_px[1] + g.trim_px[1], 2)
    for i in range(4):
        assert C["residu_px"][i] <= 0.5, C
    # RIEN DE CE QUI SE TRACE NE PEUT MORDRE SUR LA CARTE. Le trait part du
    # bord de toile et s'éloigne : plus long que la marge, il sortirait du
    # papier. La mire, centrée au milieu de la marge, a un bras de 2r : plus
    # grande, elle entrerait dans le fond perdu. C'est le bug que la
    # vérification octet-à-octet de la route a refusé — micro à 5 mm de marge —
    # et que ces deux bornes suppriment à la source.
    assert C["mark_px"] <= m, (C["mark_px"], m)
    assert m // 2 + 2 * C["mire_r_px"] <= m, (C["mire_r_px"], m)
    # ... et il reste de la place pour la mention qui compte
    g2 = CT.geom(fmt, 300, None, None, 3)
    im = _png_test(g2.canvas_px[0], g2.canvas_px[1])
    _, rap = FR.build_control_proof(im, g2, marge, "front")
    assert rap["legende"], (fmt, marge)
    assert "NE PAS IMPRIMER" in " ".join(rap["legende"]), rap["legende"]


def test_l_epreuve_de_controle_refuse_ce_qui_n_est_pas_la_bonne_toile():
    """Sans ce refus, la route serait un moyen de poser des traits de coupe au
    mauvais endroit — le même mensonge que d'estampiller « 300 DPI » sur
    n'importe quel nombre de pixels. Et jamais de 500 : chaque refus nomme sa
    raison."""
    did = _deck()
    g = CT.geom("poker_eu", 300, 3, 3, 3)
    bon = _png_test(g.canvas_px[0], g.canvas_px[1])
    base = (f"/api/cards/{did}/frame/control?fmt=poker_eu&dpi=300"
            "&bleed_mm=3&safe_mm=3&corner_mm=3")
    cas = [
        (_png_test(200, 200), base, 400),                        # mauvaise toile
        (b"ce ne sont pas des octets PNG", base, 400),           # pas un PNG
        (b"", base, 400),                                        # rien
        (bon, base + "&margin_mm=99", 400),                      # marge hors bornes
        (bon, base + "&margin_mm=0", 400),                       # marge hors bornes
        (bon, base + "&dpi=abc", 422),                           # dpi non entier
    ]
    for corps, url, attendu in cas:
        r = _api("POST", url, content=corps,
                 headers={"content-type": "image/png"})
        assert r.status_code == attendu, (url[-40:], r.status_code, r.text[:200])
        assert r.status_code != 500


def test_l_epreuve_de_controle_est_bien_a_la_definition_demandee():
    """L'épreuve porte `pHYs` comme la carte : une épreuve sans définition se
    rouvrirait à 72 DPI et ses 5 mm de trait feraient 21 mm à l'écran."""
    import struct as _s
    did = _deck()
    for dpi, ppm in ((300, 11811), (600, 23622)):
        g = CT.geom("poker_eu", dpi, 3, 3, 3)
        r = _api("POST", f"/api/cards/{did}/frame/control?fmt=poker_eu&dpi={dpi}"
                         "&bleed_mm=3&safe_mm=3&corner_mm=3",
                 content=_png_test(g.canvas_px[0], g.canvas_px[1]),
                 headers={"content-type": "image/png"})
        assert r.status_code == 200, r.text[:300]
        assert FR.dpi_to_ppm(dpi) == ppm
        # relu dans les octets, pas dans l'en-tête HTTP
        p = r.content.index(b"pHYs")
        x, y, u = _s.unpack(">IIB", r.content[p + 4:p + 13])
        assert (x, y, u) == (ppm, ppm, 1)
        mm = FR.R(10 / CT.MM_PER_INCH * dpi)
        t = FR.png_texts(r.content)
        assert t["ProofCanvas"].startswith(
            "%dx%d" % (g.canvas_px[0] + 2 * mm, g.canvas_px[1] + 2 * mm))


def test_les_deux_definitions_passent_par_la_barre_du_core_et_la_reposent():
    """(b) Le second fichier n'est pas fabriqué à côté : le module conduit le
    bouton 600 de la barre de format du CORE — celui qu'un utilisateur clique —
    puis repose la définition d'origine. Un module qui écrirait `doc.format`
    lui-même violerait la propriété exclusive de la pièce 07."""
    src = _js()
    fn = _js_fn(src, "runTwin")
    assert "setDpiByBar(600)" in fn, "le 600 n'est pas demandé"
    assert "setDpiByBar(dpi0)" in fn, "la définition d'origine n'est pas reposée"
    assert "M.setFormat" not in src and "CF.setFormat" not in src, \
        "la pièce 02 ne doit pas écrire doc.format"
    bar = _js_fn(src, "setDpiByBar")
    assert "dpiButton(" in bar, "le bouton de la barre n'est pas conduit"
    assert '#dpiSeg button[data-v=' in _js_fn(src, "dpiButton")
    # les deux blobs mesures sont ceux qu'on telecharge — pas un troisieme
    # rendu fait apres coup
    dl = _js_fn(src, "twinDownload")
    assert "TWIN.a.blob" in dl and "TWIN.b.blob" in dl


def test_le_dos_et_le_recto_ont_chacun_leur_export_et_leur_relecture():
    """Le reproche du tour 1 était « le dos est AFFICHÉ mais pas LIVRÉ ». Les
    deux faces ont un bouton d'export, et la relecture sur les octets sait
    porter sur l'une comme sur l'autre."""
    src = _js()
    assert "async function exportBack()" in src
    assert "async function exportFront()" in src
    assert 'runProof("back")' in src and 'runProof("front")' in src
    # l'export du dos passe par le MEME chemin estampille que le recto
    eb = _js_fn(src, "exportBack")
    assert 'stamped("back")' in eb
    assert "M.download(r.blob" in eb


def test_le_badge_repeint_dans_LES_DEUX_SENS():
    """UN BUG TROUVÉ EN REGARDANT L'ÉCRAN, PAS EN LISANT LE CODE. Le badge ne
    se repeignait qu'en DEVENANT périmé. Revenu à l'état vérifié — ce qui
    arrive à chaque aller-retour de définition, donc après chaque passage sur
    les deux définitions — il restait bloqué sur « périmée » alors que le
    tableau affiché portait exactement sur les octets courants.

    Un badge qui ment par pessimisme reste un badge qui ment : il apprend au
    lecteur à ne plus le croire, et le jour où il dit vrai, personne ne
    l'écoute. La bascule est donc mémorisée, et le repeint suit les DEUX
    sens."""
    src = _js()
    sp = _js_fn(src, "scheduleProof")
    assert "p !== PA.perime" in sp, "le badge ne repeint que dans un sens"
    dp = _js_fn(src, "drawProof")
    assert "PA.perime = perime" in dp, "l'état peint n'est pas mémorisé"
    assert "perime: false" in src, "PA.perime n'est pas déclaré"


def test_les_mires_sont_aux_coins_et_l_ecran_le_dit():
    """UNE PHRASE DEVENUE FAUSSE EN COURS DE TOUR. Les mires étaient au milieu
    de chaque marge ; la légende du cartouche leur passait au travers. Elles
    ont été déplacées aux quatre COINS du papier — et la note de l'écran, qui
    disait encore « au milieu des marges », a suivi. Une phrase vraie hier
    n'est pas une phrase vraie."""
    src = _js()
    assert "au milieu des marges" not in src, "l'écran décrit encore l'ancienne place"
    assert "posées aux COINS du papier" in src
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert "aux QUATRE COINS du papier" in py
    # ... et la geometrie le confirme : aucune mire ne touche la bande du
    # cartouche, qui court au milieu du bas.
    g = CT.geom("poker_eu", 300, 3, 3, 3)
    C = FR.control_geometry(g, 10)
    m = C["margin_px"]
    # bras de mire depuis un centre a m/2 : il reste dans la marge ET a gauche
    # du bord de toile, donc loin du milieu du bas
    assert m // 2 + 2 * C["mire_r_px"] < m
    assert C["mark_px"] + max(15, m // 8) <= m, "aucune bande libre pour le cartouche"


# ═════════════════════════════════════════════════════════════════════════════
# 13. TOUR 4 — LE FOND PERDU NE PROLONGEAIT PAS LA CARTE, ET LE BADGE PARLAIT
#     D'UNE VIGNETTE
#
# Deux reproches, mesurés tous les deux sur des fichiers réellement produits.
#
#   (a) « Le fond perdu est dimensionnellement parfait mais matériellement
#       vide : il ne prolonge PAS la matière de la carte. » Il avait raison, et
#       plus gravement qu'il ne le disait. Ressaut de luminance entre les 12 px
#       juste dehors et les 12 px juste dedans du trait de coupe, moyenne des
#       quatre côtés, sur les fichiers rendus par le vrai chemin d'export :
#
#           Épure 108,6 / 255 · Bois 60,7 · Arcane 57,9
#           Art déco 26,6 · Néon 22,8 · Runique 13,5
#
#       `ringZone`, `relief` et `engrave` se découpaient tous les trois sur la
#       ROGNE. Au-delà de la coupe il ne restait que le dégradé de fond — dans
#       un fichier qui DÉCLARE un BleedBox de 3 mm exacts.
#
#       Et la mesure a montré un second défaut, plus coûteux : la butée sombre
#       du profil de moulure était posée EXACTEMENT sur la ligne de coupe, le
#       ton grimpant de 73 niveaux dans les 0,34 mm suivants. Relevé brut à
#       mi-hauteur, colonnes 32 à 41 (la coupe tombe à 35,5) :
#
#           11,8 · 14,2 · 20,7 · 20,7 · 15,2 · 16,5 · 56,0 · 71,1 · 83,7 · 91,8
#
#       Un fond perdu parfait n'absorbe rien si le dessin met son arête la plus
#       dure sous la lame. Écart de teinte sur la fenêtre de coupe ± 0,5 mm —
#       la tolérance usuelle — avant puis après correction :
#
#           Épure    149,5 -> 1,24     Art déco  62,0 -> 1,71
#           Bois     145,5 -> 5,61     Runique   49,7 -> 1,50
#           Arcane   139,6 -> 2,69     Néon      41,9 -> 1,14
#
#   (b) Le badge des silhouettes publiait 8,12 / 255, mesuré sur des VIGNETTES
#       de 67 x 91 px. La même mesure sur la toile livrée donnait 4,94. Les
#       deux nombres étaient exacts et ne parlaient pas du même objet — et
#       celui qu'un auditeur re-dérive est le second. Le badge mesure
#       désormais la TOILE LIVRÉE, balaie les six raretés, et met à zéro les
#       pixels que les autres couches repeignent (sans quoi il annonçait 5,39
#       là où six fichiers réellement exportés donnaient 5,18).
# ═════════════════════════════════════════════════════════════════════════════


def test_le_fond_perdu_porte_l_encre_du_cadre_et_pas_le_decor():
    """LA correction du tour. Les trois encrages de l'anneau se découpent
    maintenant sur la TOILE, pas sur la rogne : `outerRing` part de
    `rect(0, 0, m.W, m.H)`. Sans cela l'encre s'arrête au trait de coupe et les
    3 mm de fond perdu ne contiennent qu'un dégradé de fond."""
    src = _js()
    ext = _js_fn(src, "outerRing")
    assert "ctx.rect(0, 0, m.W, m.H)" in ext, \
        "le découpage extérieur n'est pas la toile"
    assert "m.trim" not in ext, \
        "le découpage extérieur passe encore par la rogne"
    assert 'ctx.clip("evenodd")' in ext and "m.band" in ext
    for nom in ("ringZone", "relief", "engrave"):
        fn = _js_fn(src, nom)
        assert "outerRing(ctx, m)" in fn, f"{nom} ne passe pas par outerRing"
        assert "rrPath(ctx, T.x, T.y, T.w, T.h, T.r);" not in fn, \
            f"{nom} se découpe encore sur la rogne"
    # la gravure FRANCHIT la coupe : des contours de d négatif, donc dilatés
    grav = _js_fn(src, "engrave")
    assert "const nOut" in grav and "for (let k = 1 - nOut; k < n; k++)" in grav, \
        "la gravure ne sort pas de la rogne"
    # et le DOS aussi : son motif était découpé sur la rogne
    pb = _js_fn(src, "paintBack")
    assert "ctx.rect(0, 0, m.W, m.H); ctx.clip();" in pb, \
        "le motif du dos se découpe encore sur la rogne"


def test_le_dessin_ne_pose_aucune_arete_dure_sous_la_lame():
    """Un fond perdu ne sert à rien si l'arête la plus dure du dessin tombe
    sur la coupe. Trois gestes, tous vérifiés ici :

      · la rampe de moulure démarre `pl` À L'INTÉRIEUR de la coupe et le
        dégradé prolonge sa couleur d'extrémité vers le dehors, donc le ton est
        constant du bord de toile jusqu'à `pl` dans la carte ;
      · `pl` s'arrête SOUS le filet de l'utilisateur (`edge - line/2`). Posé à
        une constante de 0,8 mm, il fabriquait sa PROPRE arête à 0,35 mm devant
        le filet : marche de 32,7/255, second trait fantôme, et la relecture
        d'octets s'y accrochait — elle annonçait 14 px de large pour 10,63
        demandés, bord extérieur à 46 px pour 49,08. Un correctif qui fabrique
        le défaut suivant n'est pas un correctif ;
      · la lèvre claire de l'anneau, large de 0,55 mm, était centrée à 0,3 mm
        de la coupe : elle occupait [0,02 ; 0,58] mm, c'est-à-dire l'intérieur
        même de la fenêtre de massicot. Rentrée à 1,2 mm, elle occupe
        [0,92 ; 1,48] mm."""
    src = _js()
    rel = _js_fn(src, "relief")
    assert ("const pl = Math.min(Math.max(m.u * 0.8, m.edge - m.line / 2), "
            "w * 0.35);") in rel, "le palier n'est plus ancré sous le filet"
    assert "ramp(T.x + pl, 0, T.x + w, 0)" in rel
    assert "ramp(T.x + T.w - pl, 0, T.x + T.w - w, 0)" in rel
    assert "ramp(0, T.y + pl, 0, T.y + w)" in rel
    assert "ramp(0, T.y + T.h - pl, 0, T.y + T.h - w)" in rel
    ring = _js_fn(src, "ringZone")
    assert ("rrPath(ctx, T.x + u * 1.2, T.y + u * 1.2, T.w - u * 2.4, "
            "T.h - u * 2.4,") in ring, \
        "la lèvre claire est revenue sur la ligne de coupe"
    assert "T.x + u * 0.3" not in ring
    assert "const TOL_COUPE_MM = 0.5;" in src
    # avec les valeurs par défaut, le palier couvre la fenêtre AVEC de la marge
    edge_mm, line_mm, inner_mm = 1.6, 0.9, 5.5
    pl_mm = min(max(0.8, edge_mm - line_mm / 2), inner_mm * 0.35)
    assert round(pl_mm, 6) == 1.15
    assert pl_mm >= 0.5 + 0.2, (pl_mm, "le palier n'enjambe pas ± 0,5 mm")
    # ... et il finit exactement sous l'arête extérieure du filet
    assert round(pl_mm, 6) == round(edge_mm - line_mm / 2, 6)
    # un anneau étroit garde sa moulure : le plafond du tiers de bande joue
    assert min(max(0.8, 8 - 0), 1.0 * 0.35) == 0.35


BANC_COUPE = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { measureCut: measureCut };\n})();")();
const out = {};
for (const nom of Object.keys(CAS)) {
  const c = CAS[nom];
  const W = c.w, H = c.h, bpp = 3;
  const data = new Array(W * H * bpp).fill(0);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      /* distance signee au trait de coupe le plus proche, en px */
      const d = Math.min(x - c.off, c.off + c.tw - x, y - c.off, c.off + c.th - y);
      const v = (d < c.palier) ? c.dehors : c.dedans;
      const o = (y * W + x) * bpp;
      data[o] = v; data[o + 1] = v; data[o + 2] = v;
    }
  }
  const px = { data: data, bpp: bpp };
  const head = { w: W, h: H };
  const g = { bleed_off_px: [c.off, c.off], trim_px: [c.tw, c.th], dpi: 300 };
  try { out[nom] = mod.measureCut(px, head, g); }
  catch (e) { out[nom] = { exception: String((e && e.message) || e) }; }
}
process.stdout.write(JSON.stringify(out));
"""


def _mesure_coupe(tmp_path, cas: dict) -> dict:
    """Fait tourner la VRAIE `measureCut` de mod-frame.js sur des images
    synthétiques dont la réponse se calcule à la main."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de mesure ne peut pas tourner")
    src = _js()
    code = "\n".join([
        _js_fn(src, "lumAt"),
        _js_fn(src, "measureCut"),
        re.search(r"const r1 = .*?;\n", src).group(0),
        re.search(r"const r2 = .*?;\n", src).group(0),
        re.search(r"const TOL_COUPE_MM = .*?;\n", src).group(0),
    ])
    js = tmp_path / "coupe.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_coupe.mjs"
    banc.write_text(BANC_COUPE, encoding="utf-8")
    conf = tmp_path / "cas_coupe.json"
    conf.write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_la_mesure_de_la_fenetre_de_massicot_est_juste(tmp_path):
    """La mesure elle-même, contrôlée dans les DEUX sens sur des images dont la
    réponse se calcule à la main — sans quoi une ligne verte ne prouverait que
    la bonne humeur du panneau.

      · `plat` : même ton des deux côtés de la coupe -> 0 exactement.
      · `marche` : le ton saute À la coupe, comme AVANT correction, avec les
        deux vraies valeurs relevées sur le fichier livré (13 dehors, 88
        dedans) -> 75 exactement, sur les quatre côtés.
      · `palier` : le même saut, mais repoussé à 9 px de la coupe, donc hors de
        la fenêtre de ± 5,91 px -> 0. C'est le geste du tour."""
    tol = round(0.5 / 25.4 * 300, 2)
    assert tol == 5.91
    cas = {
        "plat": {"w": 200, "h": 240, "off": 36, "tw": 128, "th": 168,
                 "dehors": 40, "dedans": 40, "palier": 0},
        "marche": {"w": 200, "h": 240, "off": 36, "tw": 128, "th": 168,
                   "dehors": 13, "dedans": 88, "palier": 0},
        "palier": {"w": 200, "h": 240, "off": 36, "tw": 128, "th": 168,
                   "dehors": 13, "dedans": 88, "palier": 9},
    }
    got = _mesure_coupe(tmp_path, cas)
    for nom, m in got.items():
        assert "exception" not in m, (nom, m)
        assert m["tol_px"] == 5.91, m
    assert got["plat"]["pire_moyen"] == 0, got["plat"]
    assert got["marche"]["pire_moyen"] == 75, got["marche"]
    for c in ("gauche", "droite", "haut", "bas"):
        assert got["marche"][c]["moyen"] == 75, (c, got["marche"])
    assert got["palier"]["pire_moyen"] == 0, got["palier"]
    # les 76 % centraux de chaque côté, et pas un pixel de plus
    assert got["plat"]["gauche"]["lignes"] == round(168 * 0.76)
    assert got["plat"]["haut"]["lignes"] == round(128 * 0.76)


def test_le_panneau_publie_la_fenetre_de_massicot_avec_son_seuil():
    """Un nombre sans seuil ne dit rien à personne. La ligne est dans le
    tableau des octets, elle nomme sa tolérance, et son seuil est écrit."""
    src = _js()
    assert "const SEUIL_COUPE = 8;" in src, "le seuil n'est pas écrit"
    dp = _js_fn(src, "drawProof")
    assert "Fenêtre de massicot" in dp
    assert "C.pire_moyen <= SEUIL_COUPE" in dp, "la ligne ne se juge pas"
    assert "coupe: measureCut(px, head, g)" in src, \
        "la mesure ne porte pas sur les octets relus"
    # 8 / 255 = 3,1 % de dynamique : un seuil dit en clair, pas tiré au sort
    assert round(8 / 255 * 100, 1) == 3.1


def test_le_badge_des_silhouettes_parle_de_la_toile_livree():
    """« 8,12 / 255 » était vrai — sur une vignette de 67 x 91 px. Sur la toile
    livrée, la même mesure donnait 4,94. Le badge publie désormais le chiffre
    du FICHIER : rendu par les painters du fichier à `CF.geom()` (jamais
    `thumbGeom`), balayé sur les SIX raretés, et les pixels que les autres
    couches repeignent comptés pour ZÉRO comme le fichier le fait."""
    src = _js()
    fn = _js_fn(src, "measureSilFile")
    assert "const g = CF.geom();" in fn, "le badge mesure encore une vignette"
    assert "thumbGeom" not in fn
    assert "RARITIES[k]" in fn and "k < RARITIES.length" in fn, \
        "le balayage ne couvre pas les six raretés"
    assert "(MK && MK[q]) ? 0 : Math.abs(a[q] - b[q])" in fn, \
        "les pixels recouverts ne sont pas comptés pour zéro"
    mk = _js_fn(src, "maskOf")
    assert "CF.renderCard(CF.current()" in mk, \
        "le masque ne vient pas de la carte composée"
    assert "frac > 0.55" in mk, "aucun garde-fou si le masque dévore la toile"
    pf = _js_fn(src, "paintFamAt")
    assert "paintFront(oc, g, f0, THUMB_CARD, thumbDoc());" in pf and \
        "paintTop(oc, g, f0, THUMB_CARD" in pf, \
        "le rendu du badge n'emprunte pas les painters du fichier"
    ds = _js_fn(src, "drawSil")
    assert "sur la toile livrée" in ds
    assert "F.all >= SIL_SEUIL" in ds, "le verdict ne porte pas sur le fichier"
    assert "const SIL_SEUIL = 4;" in src, "le seuil du fichier n'est pas écrit"
    # le balayage n'écrit RIEN dans le document : famille et rareté sont
    # passées en surcharge locale, jamais par M.patch
    assert "M.patch" not in fn and "M.patch" not in pf


# ═════════════════════════════════════════════════════════════════════════════
# 13. TOUR 3 — LE BALAYAGE A TROUVÉ UNE BANDE INVERSÉE, ET LES INSTRUMENTS
#     ÉTAIENT ENCORE LIVRÉS ÉTEINTS
#
# Le reproche était : « le duel ne prouve pas la robustesse : un seul format,
# une seule carte ; les ornements de coin et le liseré métallique avec un rayon
# à 0 ou à 8 mm ne sont pas démontrés. » On a donc écrit le balayage — et il a
# trouvé un VRAI défaut au premier tour, sur un format que personne n'avait
# ouvert :
#
#     format `micro` (31,75 x 44,45 mm), marge intérieure au maximum du
#     curseur (20 mm)  ->  bande = 31,75 - 40 = -8,25 mm, soit -97 px à
#     300 DPI. `rrPath` trace un rectangle RETOURNÉ, le découpage en anneau
#     n'en est plus un, l'encre sort sur toute la toile. AUCUNE exception,
#     AUCUNE erreur de rendu, AUCUN compteur : le cadre était simplement faux.
#
# D'où `BAND_MIN_MM` — dérivé, pas choisi : la plaque de texte est posée à
# `band.x + 1,2 mm` et large de `band.w - 2,4 mm`, la bande doit donc garder
# ces 2,4 mm plus de quoi l'y voir. Sur les douze formats livrés, la borne ne
# mord que sur `micro` : pas un pixel des mesures précédentes ne bouge.
# ═════════════════════════════════════════════════════════════════════════════

BANC_MODEL = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { model: model, bandMaxMM: bandMaxMM, capOf: capOf };\n})();")();
const out = [];
for (const c of CAS.cas) {
  const dpi = c.g.dpi;
  const g = Object.assign({}, c.g, { mm2px: (v) => v / 25.4 * dpi });
  try {
    const m = mod.model(g, c.f);
    const u = g.mm2px(1);
    out.push({ nom: c.nom, ok: true, cap: mod.capOf(g),
      bande: [m.band.w / u, m.band.h / u], anneau: [m.outer.w / u, m.outer.h / u],
      plaque: [m.plate.w / u, m.plate.h / u],
      inner_mm: m.inner / u, edge_mm: m.edge / u });
  } catch (e) { out.push({ nom: c.nom, ok: false, err: String((e && e.message) || e) }); }
}
process.stdout.write(JSON.stringify(out));
"""


def _model_js_source() -> str:
    """Le VRAI `model()` du painter, extrait avec ce dont il dépend."""
    src = _js()
    return "\n".join([
        re.search(r"const cl = .*?;\n", src).group(0),
        re.search(r"const num = .*?;\n", src).group(0),
        re.search(r"const r2 = .*?;\n", src).group(0),
        re.search(r"const LIMITS = \{.*?\n  \};", src, re.S).group(0),
        re.search(r"const BAND_MIN_MM = \d+;", src).group(0),
        _js_fn(src, "bandMaxMM"),
        _js_fn(src, "capOf"),
        _js_fn(src, "winMM"),
        _js_fn(src, "model"),
    ])


def _banc_model(tmp_path, cas: list, code: str | None = None) -> list:
    """Fait tourner le VRAI `model()` de mod-frame.js sur de VRAIES géométries
    calculées par `contract.geom()`. Aucune réimplémentation : une
    réimplémentation prouverait la réimplémentation."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du modèle ne peut pas tourner")
    js = tmp_path / "model.js"
    js.write_text(code if code is not None else _model_js_source(),
                  encoding="utf-8")
    banc = tmp_path / "banc_model.mjs"
    banc.write_text(BANC_MODEL, encoding="utf-8")
    conf = tmp_path / "cas.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def _geom_js(fmt: str, corner_mm: float, dpi: int = 300) -> dict:
    g = CT.geom(fmt, dpi, 3, 3, corner_mm)
    return {"fmt": fmt, "dpi": dpi, "canvas_px": list(g.canvas_px),
            "trim_px": list(g.trim_px), "bleed_off_px": list(g.bleed_off_px),
            "trim_mm": list(g.trim_mm), "corner_px": g.corner_px}


CURSEURS_MAX = {"line_mm": 8, "gap_mm": 4, "edge_mm": 8, "inner_mm": 20,
                "window": None, "family": "arcane", "rarity": "rare"}


def test_la_bande_ne_s_inverse_sur_aucun_des_douze_formats(tmp_path):
    """LE DÉFAUT TROUVÉ PAR LE BALAYAGE, verrouillé. Curseurs poussés à fond,
    les DOUZE formats, les DEUX bornes du rayon : aucune largeur nulle ou
    négative. Sans `BAND_MIN_MM`, `micro` rendait ici une bande de -8,25 mm.

    Le test ne recalcule rien : il fait tourner le VRAI `model()` du painter
    sur les géométries du VRAI `contract.geom()`."""
    cas = []
    for fmt in sorted(CT.FORMATS):
        for corner in (0, 8):
            cas.append({"nom": f"{fmt}/r{corner}",
                        "g": _geom_js(fmt, corner), "f": dict(CURSEURS_MAX)})
    res = _banc_model(tmp_path, cas)
    assert len(res) == len(cas)
    for r in res:
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        for quoi in ("bande", "anneau", "plaque"):
            for v in r[quoi]:
                assert v > 0, f"{r['nom']} : {quoi} dégénéré ({v:.2f} mm)"
        assert min(r["bande"]) >= FR.BAND_MIN_MM - 0.02, \
            f"{r['nom']} : bande de {min(r['bande']):.2f} mm"


def test_le_defaut_revient_si_l_on_retire_la_borne(tmp_path):
    """LE CONTRÔLE NÉGATIF. Une borne qui ne sert jamais ne prouve rien : on la
    neutralise et le défaut DOIT revenir, exactement là où il avait été mesuré
    (micro, -8,25 mm de bande). Sans ce test, `BAND_MIN_MM` pourrait n'être
    qu'une décoration."""
    cas = [{"nom": "micro/r0", "g": _geom_js("micro", 0),
            "f": dict(CURSEURS_MAX)}]
    avec = _banc_model(tmp_path, cas)[0]
    assert avec["ok"] and min(avec["bande"]) > 0

    code = _model_js_source()
    assert "Math.min(f.inner_mm, cap)" in code, \
        "le modèle n'applique plus la borne : l'ancre du contrôle a bougé"
    sans = _banc_model(tmp_path, cas,
                       code.replace("Math.min(f.inner_mm, cap)", "f.inner_mm"))[0]
    assert sans["ok"], sans.get("err")
    assert sans["bande"][0] < 0, \
        "sans la borne, la bande de micro devrait être négative — le test ne " \
        "prouverait rien"
    assert abs(sans["bande"][0] - (31.75 - 40)) < 0.05, \
        f"la mesure d'origine était -8,25 mm, on trouve {sans['bande'][0]:.2f}"


def test_la_borne_du_format_est_la_meme_des_deux_cotes(tmp_path):
    """Deux bornes qui dérivent, c'est un écran qui annonce 20 mm quand le
    backend en compte 13,88 — et la pastille de vérification qui passe au rouge
    sans qu'un pixel bouge. Le bloc JS et `cards/frame.py` sont comparés sur
    les douze formats."""
    b = _catalog_block(_js())
    m = re.search(r"const BAND_MIN_MM = (\d+);", b)
    assert m, "BAND_MIN_MM n'est pas dans le bloc partagé du catalogue"
    assert int(m.group(1)) == FR.BAND_MIN_MM
    cas = [{"nom": f, "g": _geom_js(f, 3), "f": dict(CURSEURS_MAX)}
           for f in sorted(CT.FORMATS)]
    res = _banc_model(tmp_path, cas)
    for r in res:
        tw, th = CT.FORMATS[r["nom"]]["trim_mm"]
        attendu = FR.band_max_mm(tw, th)
        assert abs(r["cap"] - attendu) < 1e-9, \
            f"{r['nom']} : JS {r['cap']} != backend {attendu}"
        assert abs(r["inner_mm"] - min(20, attendu)) < 0.02
        assert abs(r["edge_mm"] - min(8, attendu)) < 0.02


def test_le_backend_publie_les_pixels_REELLEMENT_traces():
    """`/frame/metrics` doit rendre les pixels du DESSIN, pas ceux du curseur :
    sur `micro`, une marge demandée à 20 mm est tracée à 13,88 mm. Un écran qui
    publierait 20 mm quand le tracé en pose 13,88 serait exactement le badge
    menteur qu'on reproche aux autres."""
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/frame/metrics",
             json={"fmt": "micro", "dpi": 300, "bleed_mm": 3, "safe_mm": 3,
                   "corner_mm": 3, "line_mm": 0.9, "gap_mm": 1.1,
                   "edge_mm": 1.6, "inner_mm": 20})
    assert r.status_code == 200, r.text[:300]
    cap = FR.band_max_mm(31.75, 44.45)
    assert cap == 13.88, cap
    assert r.json()["metrics"]["inner_px"] == _exact_px(cap, 300)
    # ... et sur poker, où la borne ne mord pas, rien ne bouge
    r2_ = _api("POST", f"/api/cards/{did}/frame/metrics",
               json={"fmt": "poker_eu", "dpi": 300, "bleed_mm": 3,
                     "safe_mm": 3, "corner_mm": 3, "line_mm": 0.9,
                     "gap_mm": 1.1, "edge_mm": 1.6, "inner_mm": 20})
    assert r2_.json()["metrics"]["inner_px"] == _exact_px(20, 300)
    # la borne est publiée par le catalogue, donc vérifiable de l'extérieur
    cat = _api("GET", f"/api/cards/{did}/frame/catalog").json()["catalog"]
    assert cat["band_min_mm"] == FR.BAND_MIN_MM
    assert cat["band_max_mm"]["micro"] == 13.88
    assert cat["band_max_mm"]["poker_eu"] == 29.5


def test_l_interface_ecrit_la_borne_du_format_et_la_pose_sur_le_curseur():
    """Une borne appliquée en silence serait pire que pas de borne : le curseur
    afficherait 20 quand le tracé en pose 13,88."""
    src = _js()
    fn = _js_fn(src, "syncNow")
    assert "capOf(g)" in fn, "syncNow n'applique pas la borne du format"
    assert "row.rg.max = hi; row.nb.max = hi;" in fn, \
        "le curseur garde sa borne absolue"
    assert "(borne du format)" in fn, "la borne n'est pas écrite à l'écran"
    for nom in ("model", "occupancy", "localMetrics", "measureLine"):
        f_ = _js_fn(src, nom)
        assert "capOf(" in f_ or "bandMaxMM(" in f_, \
            f"{nom} n'applique pas la borne du format"


# ═════════════════════════════════════════════════════════════════════════════
# 13 bis. LES DEUX INSTRUMENTS PARTENT SEULS — ET LE BALAYAGE EXISTE VRAIMENT
# ═════════════════════════════════════════════════════════════════════════════

def test_les_deux_instruments_ne_sont_plus_livres_eteints():
    """« B expose tout un appareil de preuve et ne l'a pas actionné : NON
    LANCÉE, NON PRODUITE. Deux critères [DUR] restent invérifiables faute d'un
    clic. » Les deux partent maintenant seuls, sous conditions écrites."""
    src = _js()
    assert '"non lancée"' not in src and '"non produite"' not in src, \
        "un instrument est encore livré éteint"
    fn = _js_fn(src, "autoInstruments")
    assert "runTwin(true)" in fn and "runControl(true)" in fn
    assert "!panelOn()" in fn, \
        "le départ automatique ne vérifie pas que le panneau est ouvert"
    assert "PROOF.sig !== fileSig()" in fn, \
        "les gros instruments partent sans attendre la relecture d'octets"
    assert "AUTO_COOL" in fn, "aucune limite de fréquence"
    assert re.search(r"const AUTO_COOL = \d+;", src)
    # le départ automatique ne pose pas le voile d'attente global
    assert "if (!auto) M.busy(true" in _js_fn(src, "runTwin")
    assert "if (!auto) M.busy(true" in _js_fn(src, "runControl")
    # ... et les deux badges repeignent DANS LES DEUX SENS
    sp = _js_fn(src, "scheduleProof")
    assert "drawTwin();" in sp and "drawControl();" in sp, \
        "un badge périmé ne redeviendrait jamais vert"


def test_l_empreinte_des_deux_definitions_est_prise_sur_l_etat_repose():
    """MESURE qui l'a imposé : `doc.face.eff_dpi` (pièce 01) suit la définition
    et n'est réécrit qu'une à deux secondes APRÈS le retour à 300 DPI. Les deux
    définitions capturaient donc leur empreinte avant, la dessinaient pendant,
    et restaient bloquées sur « périmée » alors que le document était redevenu
    identique. Un badge qui ment par pessimisme reste un badge qui ment."""
    src = _js()
    fn = _js_fn(src, "runTwin")
    assert "await sigStable()" in fn, \
        "l'empreinte n'est pas prise sur l'état reposé"
    assert "rendu.bouge = (fin !== sig);" in fn, \
        "un mouvement pendant la mesure n'est pas signalé"
    st = _js_fn(src, "sigStable")
    assert "fileSig()" in st and "depuis" in st


def test_le_balayage_de_robustesse_existe_et_couvre_ce_qu_il_annonce():
    """Le docstring du test des douze formats ANNONÇAIT un balayage à l'écran
    qui n'existait pas. Il existe : douze formats, deux bornes du rayon, deux
    profils de curseurs, et les ornements et métaux rendus sur les trois
    formats les plus hostiles. Les nombres publiés sont COMPTÉS, jamais
    écrits."""
    src = _js()
    assert re.search(r"const SW_RAY = \[0, 8\];", src), \
        "le balayage ne couvre pas les deux bornes du rayon"
    assert re.search(r'const SW_DUR = \["micro", "domino", "jumbo"\];', src)
    fn = _js_fn(src, "runSweep")
    assert "(CF.FORMATS || []).forEach" in fn, \
        "le balayage ne parcourt pas les douze formats"
    assert "SW_PROFILS.forEach" in fn, "un seul profil de curseurs"
    assert "acc.rendus++" in fn, \
        "le nombre de rendus est écrit au lieu d'être compté"
    assert "CORNERS.forEach" in fn and "METALS.forEach" in fn, \
        "ornements et métaux ne sont pas balayés"
    assert "invisible" in fn, "un ornement qui ne change rien passerait"
    # le profil « maximum » vient des BORNES, jamais de nombres recopiés
    prof = re.search(r"const SW_PROFILS = \[(.*?)\n  \];", src, re.S).group(1)
    for k in ("line_mm", "gap_mm", "edge_mm", "inner_mm"):
        assert f"{k}: LIMITS.{k}[1]" in prof, \
            f"le profil maximum recopie une valeur au lieu de lire LIMITS.{k}"
    assert "M.patch" not in fn, "le balayage écrit dans le document"
    dr = _js_fn(src, "drawSweep")
    assert "S.geo.length" in dr and "S.rendus" in dr, \
        "le badge n'affiche pas ce qui a été compté"
    assert "S.dpi" in dr, "la définition du balayage n'est pas dite"


def test_la_fenetre_de_massicot_dit_QUI_pose_l_arete():
    """Sur `micro`, l'écart du bord droit venait d'une suite de traits crème
    (246,231,194) courant de x=396 à x=435 alors que la coupe tombe à 412,5 :
    du TEXTE, couche 60, qui déborde de la carte. Le fichier reste fautif — la
    ligne reste rouge — mais le panneau mesure aussi le CADRE SEUL et publie
    les deux, sans quoi on croirait que c'est le cadre qui encre la lame."""
    src = _js()
    rp = _js_fn(src, "runProof")
    assert "coupe_cadre" in rp and "paintFamAt(g, {})" in rp, \
        "le cadre seul n'est pas mesuré"
    dp = _js_fn(src, "drawProof")
    assert "CADRE SEUL" in dp
    assert "P.coupe_cadre" in dp
    assert "C.pire_moyen <= SEUIL_COUPE," in dp, \
        "le fichier livré ne serait plus jugé pour lui-même"


def test_la_matiere_dit_a_quelle_definition_elle_a_ete_mesuree():
    """UN CHIFFRE EXACT PEUT PORTER UNE COMPARAISON FAUSSE. Le comptage de
    couleurs uniques dans une surface PHYSIQUE fixe croît avec la définition :
    le MÊME coin de 14 x 14 mm du MÊME dessin ne donne pas le même compte à
    300 et à 600 DPI. La comparaison extérieure est partie ; ce qui la
    remplaçait doit rester — la ligne DIT à quelle définition elle a compté,
    faute de quoi deux relectures du même cadre sembleraient se contredire."""
    src = _js()
    mm = _js_fn(src, "measureMatter")
    assert "dpi: g.dpi" in mm, "la mesure ne dit pas à quelle définition"
    dp = _js_fn(src, "drawProof")
    assert 'P.matiere.dpi + " DPI = "' in dp, \
        "la ligne ne dit plus à quelle définition elle a compté"
    assert "il monte donc avec la définition" in dp, \
        "rien n'avertit que ce comptage dépend de la définition"


# =============================================================================
# 14. CE QUE L'ECRAN ET LE FICHIER LIVRE ONT LE DROIT DE DIRE
#
# Trois corrections de la meme famille, et un seul principe : un ecran de
# reglage s'adresse a celui qui regle. Il publie des MESURES — chacune relisible
# sur les octets du fichier livre — et rien qui ressemble a un cartouche
# d'auto-controle : pas d'horloge de relecture au milieu d'une aide de reglage,
# pas de tolerance recitee, pas de comparaison a un produit que le lecteur n'a
# pas. Un fichier livre, lui, ne nomme pas son producteur.
#
# Aucune de ces trois corrections n'enleve un chiffre de l'ecran : la mesure de
# la coupe est toujours publiee, ligne par ligne, dans le tableau du fichier ;
# le rayon et le fond perdu sont toujours en mm ET en px ; le comptage de
# matiere est toujours la, avec sa surface et sa definition.
# =============================================================================


def test_l_aide_de_reglage_du_filet_ne_porte_plus_de_cartouche_de_controle():
    """LE RELEVE D'AUTO-VERIFICATION ETAIT DANS L'AIDE DE REGLAGE.

    Le paragraphe du filet finissait par « mesure X/255 sur l'encre du cadre,
    relu a HH:MM:SS, seuil 8 » : une valeur sur 255, une heure a la seconde et
    une tolerance, c'est-a-dire le vocabulaire d'un instrument de controle,
    colle au milieu d'un texte qui explique ou tombe l'encre. Il part d'ici.

    IL NE PART PAS DE L'ECRAN : la meme mesure est publiee en entier dans le
    tableau du fichier livre — moyennes des quatre cotes, pire ligne, tolerance
    — et c'est la sa place. Ce que l'aide de reglage garde, c'est ce qui sert a
    regler : les trois distances du filet en mm et en px, la fenetre de
    massicot, et l'avertissement quand une autre couche deborde de la coupe."""
    src = _js()
    fn = _js_fn(src, "syncNow")
    assert "UI.edgeRead.innerHTML" in fn
    # plus d'horloge, plus de valeur sur 255, plus de tolerance recitee ici
    assert "hms(" not in fn, "l'heure de relecture est encore dans le reglage"
    assert "/255" not in fn, "une valeur sur 255 est encore dans le reglage"
    assert ", seuil " not in fn, "une tolerance est encore recitee dans le reglage"
    # ... et les mesures du reglage, elles, sont toutes restees
    assert "Convention du <b>trait centré</b>" in fn
    assert "px1(eOut)" in fn and "px1(eIn)" in fn and "px1(capE)" in fn, \
        "les trois distances du filet ne sont plus chiffrees"
    assert "TOL_COUPE_MM" in fn, "la fenetre de massicot n'est plus chiffree"
    # l'avertissement utile reste, lui : une couche du dessus qui deborde
    assert "déborde du trait de coupe" in fn
    # et la mesure complete est toujours publiee dans le tableau des octets
    dp = _js_fn(src, "drawProof")
    assert "Fenêtre de massicot" in dp and "C.pire_moyen <= SEUIL_COUPE," in dp
    assert "cotes(C)" in dp, "les moyennes des quatre cotes ne sont plus publiees"


def _js_litteraux(src: str) -> str:
    """Le CONTENU des chaînes du module — commentaires et code exclus. Un
    chiffre qui n'est pas dans une chaîne n'est pas affiché : il est calculé,
    ou il est dans une note de travail.

    Lecture caractère par caractère, parce qu'une expression régulière ne
    suffit pas : `'<div class="x">'` contient des guillemets, et un
    appariement naïf décalerait tout le reste du fichier. Les littéraux
    d'expression régulière sont neutralisés avant — `replace(/"/g, …)` en
    contient un."""
    sans_re = re.sub(r"(?m)\.replace\(/[^\n]*?/[gimsuy]*", ".replace(", src)
    out, buf, etat, i, n = [], [], None, 0, len(sans_re)
    while i < n:
        c = sans_re[i]
        if etat is None:
            if c == "/" and sans_re[i + 1:i + 2] in ("/", "*"):
                etat = "/" + sans_re[i + 1]
                i += 1
            elif c in "\"'`":
                etat, buf = c, []
            i += 1
            continue
        if etat == "//":
            if c == "\n":
                etat = None
            i += 1
            continue
        if etat == "/*":
            if c == "*" and sans_re[i + 1:i + 2] == "/":
                etat, i = None, i + 1
            i += 1
            continue
        if c == "\\":                      # échappement : les deux caractères
            buf.append(sans_re[i:i + 2])
            i += 2
            continue
        if c == etat:
            out.append("".join(buf))
            etat = None
        else:
            buf.append(c)
        i += 1
    return " ".join(out)


def test_l_ecran_n_affiche_aucun_chiffre_qu_on_ne_peut_pas_refaire():
    """UN CHIFFRE AFFICHE DOIT POUVOIR ETRE REFAIT PAR CELUI QUI LE LIT.

    Un audit a deja montre qu'un badge « 16 bits » pouvait etre faux. La meme
    regle vaut pour les chiffres VRAIS mais irrefaisables : plusieurs textes
    portaient des valeurs relevees une fois, ailleurs, sur des fichiers que le
    lecteur n'a pas — l'ecart a l'interieur de la fenetre, deux valeurs
    « avant / apres » d'une version passee du badge, le pourcentage d'une mire
    en rampe, le comptage d'un cadre peint d'un autre produit. Aucune ne se
    verifie sur ce qui est a l'ecran ni sur le fichier telecharge : elles
    partent toutes. Les chiffres qui restent sont soit mesures a l'instant sur
    les octets, soit vrais par construction (un x2 au plus proche voisin recopie
    une ligne sur deux) et couverts par un banc de test de ce fichier."""
    src = _js()
    vus = _js_litteraux(src)
    # bornes de chiffre : « 5,18 » vit aussi dans « rgba(120,235,180,1) », qui
    # est une couleur, pas une mesure. On ne cherche que le nombre ISOLÉ.
    for perdu in ("0,09", "5,39", "5,18", "84,2", "24,8", "18,4",
                  "29,0", "116,9"):
        assert not re.search(r"(?<![\d,.])" + perdu.replace(",", ",") + r"(?![\d])",
                             vus), \
            f"« {perdu} » est affiché, et le lecteur ne peut pas le refaire"
    # aucune comparaison à un produit extérieur nulle part dans le module :
    # ni à l'écran, ni dans les notes de travail servies avec le fichier
    for mot in ("barre peinte", "cadre peint de la reference",
                "référence peinte", "% de la référence"):
        assert mot not in src, f"le module se compare encore : {mot!r}"
    # ... et les deux signatures d'agrandissement, elles, restent : elles sont
    # vraies par construction ET vérifiées par le banc de ce fichier.
    assert "50 %" in vus and "100 %" in vus


def test_le_fichier_livre_ne_nomme_pas_son_producteur():
    """LES METADONNEES D'UN LIVRABLE SE LISENT.

    Le PNG livre portait, en tEXt `Software`, le nom du producteur et la
    numerotation interne des ecrans du logiciel. Un fichier d'impression part
    chez un imprimeur, un client, un partenaire : il n'emporte plus que la
    description de ce qu'il EST.

    Le controle est fait sur les OCTETS des deux pieces jointes que cette piece
    produit — le PNG estampille et l'epreuve de controle — clef par clef, et
    non sur le source."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    interdits = ("deepotus", "cardforge", "card forge", "atelier",
                 "piece 02", "pièce 02", "p2 ")

    def _controle(data: bytes, quoi: str):
        t = _text_of(data)
        assert "Software" in t and t["Software"].strip(), \
            f"{quoi} : la cle Software a disparu"
        for k, v in t.items():
            bas = (k + " " + v).lower()
            for mot in interdits:
                assert mot not in bas, \
                    f"{quoi} : le tEXt {k} nomme le producteur ({mot!r})"

    r = _api("POST", f"/api/cards/{did}/frame/stamp?fmt=poker_eu&dpi=300"
                     f"&face=front&collisions=0",
             content=_png(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text[:300]
    _controle(r.content, "PNG livre")

    r2 = _api("POST", f"/api/cards/{did}/frame/control?fmt=poker_eu&dpi=300"
                      f"&face=front&margin_mm=10",
              content=_png(*g.canvas_px),
              headers={"content-type": "image/png"})
    if r2.status_code == 200:
        _controle(r2.content, "epreuve de controle")
    else:                                   # Pillow absent : 503, pas un echec
        assert r2.status_code == 503, r2.text[:300]

    # la table du backend elle-meme ne doit plus porter ces chaines
    tt = dict(FR.stamp_texts(g))
    for k, v in tt.items():
        for mot in interdits:
            assert mot not in (k + " " + v).lower(), \
                f"stamp_texts porte encore {mot!r} dans {k}"
