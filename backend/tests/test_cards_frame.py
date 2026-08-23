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
import math
import os
import pathlib
import re
import struct
import sys
import tempfile
import zlib
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


# ═══════════════ 1. LE CATALOGUE : 42 combinaisons, et une seule liste ══════

def test_au_moins_20_combinaisons():
    """La barre en propose 3. Le seuil de la spec est 20."""
    cat = FR.catalog()
    assert cat["combos"] == len(FR.FAMILIES) * len(FR.RARITIES)
    assert cat["combos"] >= COMBOS_MIN, \
        f"{cat['combos']} combinaisons, seuil {COMBOS_MIN}"
    assert cat["combos"] == 42, "7 familles x 6 raretés"
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


def _hors_verso(src: str) -> str:
    """Le source, PRIVÉ des deux fonctions qui manipulent l'image que
    l'UTILISATEUR importe pour son verso (3c-T4). Voir le test ci-dessous."""
    for nom in ("loadBackImg", "importBackImage", "downscaleBack"):
        corps = _js_fn(src, nom)
        src = src.replace(corps, f"/* {nom} : hors périmètre */")
    return src


def test_le_module_ne_charge_aucune_image():
    """Un cadre qui vient d'un fichier image a une résolution ; un cadre
    tracé n'en a pas. On refuse donc TOUT chargement d'image dans le module,
    pas seulement les PNG posés dans le dépôt.

    AMENDÉ EN 3c-T4, ET LA PORTÉE EST RESSERRÉE PLUTÔT QU'OUVERTE. §6.2ter
    donne au dos une IMAGE IMPORTÉE PAR L'UTILISATEUR : la charger est le
    fait même de la fonction, et l'interdire interdirait la fonctionnalité.
    Ce que le seuil de la spec protège n'est pas « aucun décodeur d'image
    dans le fichier », c'est « LE CADRE n'a pas de résolution » — aucun
    bitmap LIVRÉ, aucune texture de cadre, aucune image dans le DESSIN. Le
    verso personnalisé n'est pas un cadre : c'est le contenu de
    l'utilisateur, comme l'illustration l'est pour P1.

    Deux chargeurs sont donc admis, NOMMÉMENT et à un seul endroit chacun ;
    tout le reste — les URI de données, `<img>`, `createPattern` (une texture
    de cadre déguisée) — reste interdit PARTOUT, et la feuille de style ne
    référence toujours aucune ressource externe."""
    src, css = _js(), CSS.read_text(encoding="utf-8")
    ailleurs = _hors_verso(src)
    for rx, quoi in ((r"new\s+Image\s*\(", "new Image()"),
                     (r"createImageBitmap\s*\(", "createImageBitmap()")):
        assert not re.search(rx, ailleurs), \
            f"mod-frame.js charge une image HORS du verso personnalisé : {quoi}"
        assert len(re.findall(rx, src)) == 1, \
            f"{quoi} apparaît {len(re.findall(rx, src))} fois : un seul " \
            f"chargeur, à un seul endroit"
    interdits = [
        (r"createElement\(\s*[\"']img[\"']", "createElement('img')"),
        (r"<img\b", "<img>"),
        (r"data:image/", "data: URI d'image"),
        (r"createPattern\s*\(", "createPattern()"),
    ]
    for rx, quoi in interdits:
        assert not re.search(rx, src), f"mod-frame.js charge une image : {quoi}"
    assert not re.search(r"url\s*\(", css), \
        "mod-frame.css référence une ressource externe (url(...))"
    # ... ET AUCUN BITMAP N'EST LIVRÉ AVEC LA PIÈCE : le seuil de la spec
    # (« zéro PNG de cadre ») porte sur le DÉPÔT, et il tient tel quel — le
    # verso personnalisé lit un fichier du JEU, jamais un asset de la pièce.
    for p in (JS.parent.parent).rglob("*"):
        assert not (p.is_file() and p.suffix.lower() in RASTER_EXT
                    and "mod-frame" in p.name), p
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
    assert cat["combos"] == 42
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


def test_chaque_famille_a_une_silhouette_distincte():
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
    # (3c-T4 : les deux chargeurs du verso personnalisé sont retirés du
    # périmètre — ils importent le fichier de l'UTILISATEUR, ils ne relisent
    # pas le fichier livré. Le test voisin les épingle à un seul endroit
    # chacun ; ici on vérifie que la RELECTURE reste une lecture d'octets.)
    sans_com = re.sub(r"/\*.*?\*/", "", _hors_verso(src), flags=re.S)
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


def test_le_parseur_png_ne_porte_plus_d_octet_nul_brut():
    r"""Spec 9.6-5 (barre de fluidite, amendement du 20/08) : `pngHeader` /
    `pngChunks` savent lire un chunk `tEXt`, dont le separateur mot-cle/texte
    du format PNG est un octet NUL -- ce fichier en portait un brut, litteral
    entre les guillemets d'un `String.prototype.indexOf(...)`. Legal en JS,
    mais l'octet fait passer TOUT le fichier pour du binaire aux outils
    textuels (grep s'y est deja arrete une fois) ; la sequence ECHAPPEE
    `\x00` dit exactement la meme chose sans ce cout. Octets bruts, pas texte
    decode : un decodage UTF-8 rendrait le NUL invisible a une simple
    recherche de sous-chaine, ce test doit lire ce que lit vraiment un outil
    binaire (grep, un octet-scan) sur le fichier livre. Le lint (R13, scripts
    /qa/lint_cardforge.py) porte la meme regle sur les 10 pieces du labo ;
    cette assertion-ci l'epingle sur CETTE piece precisement, la ou l'octet
    a ete trouve et corrige."""
    raw = JS.read_bytes()
    assert b"\x00" not in raw, (
        "mod-frame.js contient a nouveau un octet NUL brut -- l'ecrire "
        'echappe : "\\x00" (4 caracteres), pas le caractere de controle')
    assert b'indexOf("\\x00")' in raw, (
        "le separateur mot-cle/texte du chunk PNG tEXt (fonction "
        "pngHeader) ne porte plus la forme echappee attendue")


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


def test_la_fenetre_effective_est_publiee_pour_les_autres_pieces():
    """LE CONTRAT QUE P1 ATTENDAIT DEPUIS LE PREMIER JOUR. `mod-face.js` lit
    `frame.art_window` pour caler la pose sur ce que le cadre laisse voir --
    la cle n'etait jamais ecrite : le mode << auto >> de la fenetre
    d'illustration retombait TOUJOURS sur la toile entiere, et la pose par
    defaut laissait jusqu'a 70 % de l'illustration sous le cadre (reste connu
    du commit de cloture du gauntlet).

    La piece publie desormais la fenetre EFFECTIVE (auto ou manuelle), la
    meme que `winMM` fait dessiner -- une mesure du calcul qui peint, pas une
    seconde formule -- differee et gardee par comparaison (un painter qui
    patche sans garde est une boucle de rendu), et null quand aucune famille
    ne masque rien."""
    src = JS.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)

    # la cle est au schema : sans elle, patchAs refuserait l'ecriture
    assert "art_window: null" in code

    pub = code.split("function publishWindow(")[1].split("\n  }")[0]
    # la valeur publiee vient de winMM -- jamais d'une seconde formule
    assert "winMM(g, f)" in pub
    assert "0.105" not in pub and "0.79" not in pub, \
        "la publication recopie la formule au lieu de relire winMM"
    # null quand rien ne masque
    assert '"none"' in pub
    # differee et gardee par comparaison : pas de boucle de rendu
    assert "setTimeout" in pub and "clearTimeout" in pub
    assert "M.patch({ art_window: pub })" in pub

    # le painter la publie a chaque rendu (bloc `painters:` du registre)
    peintres = code.split("painters: [")[1].split("state: DEFAULTS")[0]
    assert "publishWindow(geom, f)" in peintres

    # le contrat a deux bouts : P1 la lit telle quelle
    face = (JS.parent / "mod-face.js").read_text(encoding="utf-8")
    assert 'CF.get("frame.art_window"' in face

# ═════════════════════════════════════════════════════════════════════════════
# 15. PHASE 3a — L'HABILLAGE DES SEPT ARCHÉTYPES (§6.2), ET LA SEPTIÈME FAMILLE
#
# La règle de la tâche : la MESURE décide, pas le catalogue de la spec. Pour
# chacun des sept archétypes on a d'abord tenté d'habiller avec les SIX
# familles livrées. Six y sont arrivés :
#
#   superstar -> `deco`   (fenêtre à pans coupés + gradins : la « plaque à pans
#                          coupés 4,4 -> 55 x 80 » EST `edge_mm = 4`)
#   duel      -> `sable`  (un seul filet, plaque RECTANGLE stricte : le tableau
#                          zébré, et « PAS d'ellipse »)
#   créature  -> `timber` (bande épaisse + rivets : le gros liseré coloré)
#   arcane    -> `arcane` (fenêtre en arc, volutes, plaque en arc)
#   monstre   -> `runic`  (fenêtre RECTANGLE + anneau plein : `grad: false`
#                          rend le « cadre couleur pleine = catégorie »)
#   légende   -> `sable`  (anneau CLAIR = la bordure blanche vintage, filet
#                          0,35 mm, fenêtre presque pleine page)
#
# UN SEUL ne pouvait pas : « Arcane gravée » demande un FOND IVOIRE et des
# aplats de pochoir au REPÉRAGE DÉCALÉ de 0,2 mm. Les six familles encrent
# l'anneau depuis `PAL`, dont les six raretés sont SOMBRES, et aucune ne pose
# d'aplat décalé — d'où `gravure`, septième famille.
#
# AMENDEMENT AU PLAN, mesuré : le plan attendait la famille nouvelle POUR le
# « double filet 1,5/3 mm ». Ce filet-là est atteignable avec le moteur
# existant — `edge_mm 1,5` + `line_mm 0,5` + `gap_mm 1,1` posent le second
# filet à 1,5 + 0,25 + 1,1 + 0,15 = 3,00 mm EXACTEMENT (arithmétique de
# `paintFront` §6, vérifiée plus bas). Ce n'est donc pas le filet qui justifie
# la famille, c'est l'ivoire et le décalage. La raison publiée est la vraie.
# ═════════════════════════════════════════════════════════════════════════════

ARCHETYPES = ("superstar", "duel", "creature", "arcane", "monstre",
              "legende", "gravee")


def _js_defaults_keys(src: str) -> list:
    """Les clés RÉELLES de `doc.frame`, lues dans le bloc DEFAULTS du JS."""
    m = re.search(r"const DEFAULTS = \{(.*?)\n  \};", src, re.S)
    assert m, "bloc DEFAULTS absent de mod-frame.js"
    txt = re.sub(r"/\*.*?\*/", " ", m.group(1), flags=re.S)
    return re.findall(r"(\w+)\s*:", txt)


def test_le_compte_de_cles_ecrit_dans_le_source_est_le_vrai():
    """Le commentaire de `st()` disait « les 22 cles » quand `DEFAULTS` en
    porte 28 : un lecteur qui compte sur ce chiffre pour savoir ce que
    `patch` accepte se trompe de six clés. Corrigé en passant (tâche 3a-2),
    et VERROUILLÉ au compte réel — pas au compte recopié.

    29 depuis la phase 3c-1 : `seal`, le PREMIER sous-objet de `doc.frame`
    (le Sceau prismatique, spec §6.2bis). 31 depuis la 3c-4 : `back_image` et
    `back_layers`, le verso personnalisé (spec §6.2ter)."""
    src = _js()
    cles = _js_defaults_keys(src)
    assert len(cles) == len(set(cles)), f"clé en double dans DEFAULTS : {cles}"
    assert len(cles) == 31, f"{len(cles)} clés dans DEFAULTS : {cles}"
    assert "les 22 cles" not in src and "22 clés" not in src, \
        "le commentaire périmé « 22 clés » est toujours là"
    assert f"porte toujours les {len(cles)} cles" in src, \
        "le commentaire de st() ne dit pas le compte réel"


# ── 15.1 la septième famille : catalogue, tables JS, colonnes ────────────────

def test_la_septieme_famille_existe_des_deux_cotes():
    """Une famille n'existe que si les DEUX catalogues la portent (le test de
    parité générique le voit déjà) ET si les trois tables JS-seules la
    connaissent : `FAM_FN` (le dessin), `WIN_SHAPE` (la forme de fenêtre),
    `PROFILE` (les cinq signatures de silhouette). Une entrée de menu sans
    peintre, c'est un cadre qui rend l'image d'une AUTRE famille."""
    src = _js()
    ids = [f["id"] for f in FR.FAMILIES]
    assert "gravure" in ids, f"familles backend : {ids}"
    assert ("gravure", "Gravure") in _js_list(_catalog_block(src), "FAMILIES")
    assert re.search(r"const FAM_FN = \{[^}]*gravure: famGravure", src), \
        "gravure n'a pas de peintre dans FAM_FN"
    assert re.search(r"const WIN_SHAPE = \{[^}]*gravure: \"\w+\"", src), \
        "gravure n'a pas de forme de fenêtre"
    assert "function famGravure(" in src, "le peintre famGravure n'existe pas"
    rows = {r[0]: r for r in _profile_rows(src)}
    assert "gravure" in rows, "gravure n'a pas de profil de silhouette"
    # les cinq colonnes de gravure ne doivent RIEN partager : le test générique
    # `test_chaque_famille_a_une_silhouette_distincte` le vérifie colonne par
    # colonne pour toutes les familles — ici on nomme la nouvelle.
    assert rows["gravure"][7] == "ivoire", rows["gravure"]


def test_le_double_filet_1_5_3_mm_sort_du_moteur_existant():
    """L'AMENDEMENT, arithmétique à l'appui. `paintFront` pose le second filet
    à `edge + line*0.5 + gap + line*0.3` de la coupe. Avec l'habillage de
    « gravée » (edge 1,5 · line 0,5 · gap 1,1) cela fait 3,00 mm pile, et le
    premier filet est sur son axe à 1,5 mm : le « double filet 1,5/3 mm » de
    la spec §6.2-7 ne demandait aucune famille nouvelle."""
    src = _js()
    assert "const o2 = m.edge + m.line * 0.5 + m.gap + m.line * 0.3;" in src, \
        "l'arithmétique du second filet a bougé : re-mesurer avant de recopier"
    hab = FR.ARCHETYPE_FRAMES["gravee"]
    axe1 = hab["edge_mm"]
    axe2 = hab["edge_mm"] + hab["line_mm"] * 0.5 + hab["gap_mm"] \
        + hab["line_mm"] * 0.3
    assert abs(axe1 - 1.5) < 1e-9, axe1
    assert abs(axe2 - 3.0) < 1e-9, axe2


# ── 15.2 LE RASTÉRISEUR DE CONTRÔLE : des pixels, pas des intentions ─────────
#
# node n'a pas de contexte 2D dans ce dépôt. On en écrit un qui ne fait qu'une
# chose : dire QUELLES CELLULES d'une grille de 0,5 mm reçoivent de l'encre.
# Les courbes sont aplaties, les remplissages tramés par balayage de lignes
# (pair-impair ou non-nul), les traits marqués le long du chemin, et le CLIP
# est honoré — sans lui `outerRing` ne voudrait rien dire et une famille qui
# déborde sur l'illustration passerait pour saine.
#
# Ce que ce banc prouve : qu'un peintre de famille ENCRE VRAIMENT, et OÙ. Ce
# qu'il ne prouve pas : les tons (c'est la mesure de silhouettes du panneau,
# faite au navigateur sur la toile livrée, qui les juge).

BANC_PEINTRE = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { st: st, model: model, winMM: winMM, FAMILIES: FAMILIES,"
  + " PROFILE: PROFILE, WIN_SHAPE: WIN_SHAPE, FAM_FN: FAM_FN,"
  + " famProfile: famProfile, winMoulding: winMoulding,"
  + " platePath: platePath, plateTrim: plateTrim, winPath: winPath };\n})();")();

const N_BEZ = 12, N_ARC = 20;
const GRAD = { addColorStop: function () {} };

function Rec(W, H, GW, GH) {
  this.W = W; this.H = H; this.GW = GW; this.GH = GH;
  this.cov = new Uint8Array(GW * GH);
  this.msk = new Uint8Array(GW * GH).fill(1);
  this.stk = []; this.t = { sx: 1, sy: 1, tx: 0, ty: 0 };
  this.sub = []; this.cur = null; this.ops = 0;
  this.fillStyle = ""; this.strokeStyle = ""; this.lineWidth = 1;
  this.globalAlpha = 1; this.shadowBlur = 0; this.shadowColor = "";
  this.lineCap = ""; this.lineJoin = ""; this.font = ""; this.textAlign = "";
  this.textBaseline = ""; this.imageSmoothingEnabled = true;
}
Rec.prototype.save = function () {
  this.stk.push({ t: { sx: this.t.sx, sy: this.t.sy, tx: this.t.tx, ty: this.t.ty },
    msk: this.msk.slice() });
};
Rec.prototype.restore = function () {
  const s = this.stk.pop();
  if (s) { this.t = s.t; this.msk = s.msk; }
};
Rec.prototype.translate = function (x, y) {
  this.t.tx += x * this.t.sx; this.t.ty += y * this.t.sy;
};
Rec.prototype.scale = function (x, y) { this.t.sx *= x; this.t.sy *= y; };
Rec.prototype.rotate = function () {};
Rec.prototype._p = function (x, y) {
  return [x * this.t.sx + this.t.tx, y * this.t.sy + this.t.ty];
};
Rec.prototype.beginPath = function () { this.sub = []; this.cur = null; };
Rec.prototype.moveTo = function (x, y) {
  this.cur = [this._p(x, y)]; this.sub.push(this.cur);
};
Rec.prototype.lineTo = function (x, y) {
  if (!this.cur) this.moveTo(x, y); else this.cur.push(this._p(x, y));
};
Rec.prototype.closePath = function () {};
Rec.prototype.rect = function (x, y, w, h) {
  this.moveTo(x, y); this.lineTo(x + w, y);
  this.lineTo(x + w, y + h); this.lineTo(x, y + h);
  this.cur = null;
};
/* arcTo : le coin arrondi devient un coin coupe. A 0,5 mm de resolution,
   l'ecart est d'une cellule sur quatre coins — assez pour compter l'encre,
   trop grossier pour juger une forme (ce n'est pas ce que ce banc juge). */
Rec.prototype.arcTo = function (x1, y1, x2, y2) {
  this.lineTo(x1, y1); this.lineTo(x2, y2);
};
Rec.prototype.arc = function (cx, cy, r, a0, a1) {
  const n = N_ARC;
  for (let i = 0; i <= n; i++) {
    const a = a0 + (a1 - a0) * i / n;
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    if (i === 0 && !this.cur) this.moveTo(x, y); else this.lineTo(x, y);
  }
};
Rec.prototype.ellipse = function (cx, cy, rx, ry, rot, a0, a1) {
  const n = N_ARC, ca = Math.cos(rot || 0), sa = Math.sin(rot || 0);
  for (let i = 0; i <= n; i++) {
    const a = a0 + (a1 - a0) * i / n;
    const px = Math.cos(a) * rx, py = Math.sin(a) * ry;
    const x = cx + px * ca - py * sa, y = cy + px * sa + py * ca;
    if (i === 0 && !this.cur) this.moveTo(x, y); else this.lineTo(x, y);
  }
};
Rec.prototype.bezierCurveTo = function (x1, y1, x2, y2, x3, y3) {
  if (!this.cur) this.moveTo(x1, y1);
  const p0 = this.cur[this.cur.length - 1];
  const inv = { x: (p0[0] - this.t.tx) / this.t.sx, y: (p0[1] - this.t.ty) / this.t.sy };
  for (let i = 1; i <= N_BEZ; i++) {
    const t = i / N_BEZ, u = 1 - t;
    const x = u * u * u * inv.x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3;
    const y = u * u * u * inv.y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3;
    this.lineTo(x, y);
  }
};
Rec.prototype.quadraticCurveTo = function (x1, y1, x2, y2) {
  this.bezierCurveTo(x1, y1, x1, y1, x2, y2);
};
Rec.prototype._raster = function (eo, target, brut) {
  const GW = this.GW, GH = this.GH;
  for (let gy = 0; gy < GH; gy++) {
    const y = (gy + 0.5) * this.H / GH;
    const xs = [];
    for (let s = 0; s < this.sub.length; s++) {
      const sp = this.sub[s], n = sp.length;
      if (n < 2) continue;
      for (let i = 0; i < n; i++) {
        const a = sp[i], b = sp[(i + 1) % n];
        if ((a[1] <= y) === (b[1] <= y)) continue;
        const t = (y - a[1]) / (b[1] - a[1]);
        xs.push([a[0] + t * (b[0] - a[0]), b[1] > a[1] ? 1 : -1]);
      }
    }
    if (xs.length < 2) continue;
    xs.sort(function (p, q) { return p[0] - q[0]; });
    let w = 0;
    for (let i = 0; i < xs.length - 1; i++) {
      w += xs[i][1];
      const dedans = eo ? (i % 2 === 0) : (w !== 0);
      if (!dedans) continue;
      const x0 = xs[i][0], x1 = xs[i + 1][0];
      let g0 = Math.floor(x0 * GW / this.W), g1 = Math.ceil(x1 * GW / this.W);
      if (g0 < 0) g0 = 0;
      if (g1 > GW) g1 = GW;
      for (let gx = g0; gx < g1; gx++) {
        const xc = (gx + 0.5) * this.W / GW;
        if (xc < x0 || xc >= x1) continue;
        const q = gy * GW + gx;
        if (brut || this.msk[q]) target[q] = 1;
      }
    }
  }
};
Rec.prototype._trace = function (target) {
  const GW = this.GW, GH = this.GH;
  const pas = Math.min(this.W / GW, this.H / GH) * 0.5;
  const marque = (x, y) => {
    const gx = Math.floor(x * GW / this.W), gy = Math.floor(y * GH / this.H);
    if (gx < 0 || gy < 0 || gx >= GW || gy >= GH) return;
    const q = gy * GW + gx;
    if (this.msk[q]) target[q] = 1;
  };
  for (let s = 0; s < this.sub.length; s++) {
    const sp = this.sub[s];
    for (let i = 0; i + 1 < sp.length; i++) {
      const a = sp[i], b = sp[i + 1];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const n = Math.max(1, Math.ceil(L / pas));
      for (let k = 0; k <= n; k++) {
        marque(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n);
      }
    }
  }
};
Rec.prototype.fill = function (rule) {
  this.ops++; this._raster(rule === "evenodd", this.cov, false);
};
Rec.prototype.stroke = function () { this.ops++; this._trace(this.cov); };
Rec.prototype.clip = function (rule) {
  const m = new Uint8Array(this.GW * this.GH);
  this._raster(rule === "evenodd", m, true);
  for (let i = 0; i < m.length; i++) if (!m[i]) this.msk[i] = 0;
};
Rec.prototype.fillRect = function (x, y, w, h) {
  this.beginPath(); this.rect(x, y, w, h); this.fill();
};
Rec.prototype.strokeRect = function (x, y, w, h) {
  this.beginPath(); this.rect(x, y, w, h); this.stroke();
};
Rec.prototype.createLinearGradient = function () { return GRAD; };
Rec.prototype.createRadialGradient = function () { return GRAD; };
Rec.prototype.createPattern = function () { return null; };
Rec.prototype.drawImage = function () {};
Rec.prototype.setLineDash = function () {};
Rec.prototype.fillText = function () {};
Rec.prototype.strokeText = function () {};
Rec.prototype.measureText = function () { return { width: 0 }; };
Rec.prototype.empreinte = function () {
  /* L'EMPREINTE DE LA SILHOUETTE DESSINEE — FNV-1a 32 bits sur TOUTES les
     cellules de la grille, plus le compte des cellules encrees. Un COMPTE ne
     voit pas deux familles qui dessinent la meme chose au meme endroit ; un
     bitmap, si. C'est le seul garde de « deux entrees de menu, un seul
     dessin » qui tourne en integration : le badge de l'ecran, lui, mesure des
     TONS et n'est pas dans la suite. */
  let a = 2166136261, n = 0;
  for (let i = 0; i < this.cov.length; i++) {
    a ^= this.cov[i]; a = Math.imul(a, 16777619) >>> 0;
    if (this.cov[i]) n++;
  }
  return { h: ("0000000" + a.toString(16)).slice(-8), n: n };
};
Rec.prototype.part = function (bx) {
  /* la part de cellules encrees dans une boite EN PIXELS DE TOILE */
  const GW = this.GW, GH = this.GH;
  const y0 = Math.max(0, Math.floor(bx[1] * GH / this.H));
  const y1 = Math.min(GH, Math.ceil((bx[1] + bx[3]) * GH / this.H) + 1);
  const x0 = Math.max(0, Math.floor(bx[0] * GW / this.W));
  const x1 = Math.min(GW, Math.ceil((bx[0] + bx[2]) * GW / this.W) + 1);
  let n = 0, tot = 0;
  for (let gy = y0; gy < y1; gy++) {
    const y = (gy + 0.5) * this.H / GH;
    if (y < bx[1] || y >= bx[1] + bx[3]) continue;
    for (let gx = x0; gx < x1; gx++) {
      const x = (gx + 0.5) * this.W / GW;
      if (x < bx[0] || x >= bx[0] + bx[2]) continue;
      tot++;
      if (this.cov[gy * GW + gx]) n++;
    }
  }
  return tot ? Math.round(n / tot * 10000) / 10000 : -1;
};

function zones(m, u) {
  const B = m.band, W = m.W, H = m.H;
  return {
    perdu: [0, 0, W, m.trim.y],
    haut: [0, 0, W, B.y],
    bas: [0, B.y + B.h, W, H - (B.y + B.h)],
    gauche: [0, 0, B.x, H],
    droite: [B.x + B.w, 0, W - (B.x + B.w), H],
    fenetre: [m.win.x + 4 * u, m.win.y + 4 * u,
      m.win.w - 8 * u, m.win.h - 8 * u],
    plaque: [m.plate.x, m.plate.y, m.plate.w, m.plate.h],
    toile: [0, 0, W, H],
  };
}

const out = [];
for (const c of CAS.cas) {
  const dpi = c.g.dpi;
  const g = Object.assign({}, c.g, { mm2px: (v) => v / 25.4 * dpi });
  try {
    const f = mod.st({ frame: c.frame });
    const m = mod.model(g, f);
    const u = g.mm2px(1);
    const shape = mod.WIN_SHAPE[f.family] || "rect";
    const Z = zones(m, u);
    /* LE DECOUPAGE DE `paintFront`, PAS TOUTE SON ETAPE 2 : tout ce que la
       famille peint est clipe « toile MOINS fenetre ». Sans lui, les veines
       de « Bois sculpte » couvriraient l'illustration dans le banc alors
       qu'elles ne la couvrent pas dans le fichier. Le dos, lui, n'a pas de
       trou de fenetre : `paintBack` clipe la toile entiere.
       CE QUE LE BANC N'APPELLE PAS, ET POURQUOI : `matter()` (trames, patine,
       gravure, relief). Ses deux passes de hachures traversent la carte
       entiere tous les 1,9 a 3,4 mm — a 0,5 mm de cellule, elles SATURENT la
       grille et toute mesure de « qui encre quoi » tombe a 1,00 partout. Le
       banc mesure donc la SIGNATURE de famille (profil, dessin, moulure,
       plaque), pas la matiere. */
    const neuf = () => {
      const k = new Rec(g.canvas_px[0], g.canvas_px[1], c.gw, c.gh);
      if (c.face !== "back") {
        k.beginPath(); k.rect(0, 0, m.W, m.H);
        mod.winPath(k, m, shape); k.clip("evenodd");
      }
      return k;
    };
    const releve = (ctx) => {
      const o = { ops: ctx.ops, emp: ctx.empreinte() };
      for (const k of Object.keys(Z)) o[k] = ctx.part(Z[k]);
      return o;
    };
    const etapes = {};
    let ctx = neuf(); mod.famProfile(ctx, m, f); etapes.profil = releve(ctx);
    ctx = neuf();
    const fn = mod.FAM_FN[f.family];
    if (fn) fn(ctx, m, f);
    etapes.signature = releve(ctx);
    ctx = neuf(); mod.winMoulding(ctx, m, f, shape); etapes.moulure = releve(ctx);
    /* LA GARDE DU PAINTER, PAS UNE APPROXIMATION. `paintFront` ne dessine la
       plaque que si `m.plate.h > u * 6` : sous cette hauteur, la plaque
       n'existe pas dans le fichier. Le banc l'ignorait et annonçait une boite
       remplie a 0,98 la ou le fichier ne portait RIEN (mesure : un habillage
       dont la fenetre descend a 76 mm laisse 5 mm de plaque). */
    const plaqueVue = f.plate && m.plate.h > u * 6;
    ctx = new Rec(g.canvas_px[0], g.canvas_px[1], c.gw, c.gh);
    if (plaqueVue) { mod.platePath(ctx, m, f); ctx.fill(); mod.plateTrim(ctx, m, f); }
    etapes.plaque = releve(ctx);
    /* la carte entiere, matiere exclue (voir ci-dessus) : recto = les quatre
       etapes de signature, « miroir » = les deux que `paintBack` appelle dans
       sa branche `else` (famProfile + FAM_FN) quand le dos est « Miroir du
       recto ». Les six autres dos sont des MOTIFS, hors de la tranche
       extraite : le banc ne les mesure pas et ne pretend pas le faire. */
    ctx = neuf();
    ctx.save();
    mod.famProfile(ctx, m, f);
    if (fn) fn(ctx, m, f);
    if (c.face !== "back") {
      mod.winMoulding(ctx, m, f, shape);
      ctx.restore();
      if (plaqueVue) { mod.platePath(ctx, m, f); ctx.fill(); mod.plateTrim(ctx, m, f); }
    }
    etapes.tout = releve(ctx);
    out.push({ nom: c.nom, ok: true, famille: f.family, face: c.face || "front",
      win: [m.wm.x, m.wm.y, m.wm.w, m.wm.h], plaque_mm: m.plate.h / u,
      plaque_vue: !!plaqueVue, etapes: etapes });
  } catch (e) {
    out.push({ nom: c.nom, ok: false, err: String((e && e.stack) || e) });
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _painter_js_source() -> str:
    """Le PEINTRE DE FAMILLE, extrait TEL QUEL : du catalogue à `atCorners`,
    d'un seul tenant. Aucune réimplémentation — une réimplémentation
    prouverait la réimplémentation. Le morceau ne contient que des
    déclarations au niveau du module (mesuré : aucune instruction exécutée à
    l'évaluation), il s'évalue donc sans `window` ni `CF`."""
    src = _js()
    i = src.index("  const FAMILIES = [")
    fin = _js_fn(src, "atCorners")
    return src[i:src.index(fin) + len(fin)]


def _banc_peintre(tmp_path, cas: list, code: str | None = None) -> list:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du peintre ne peut pas tourner")
    js = tmp_path / "peintre.js"
    js.write_text(code if code is not None else _painter_js_source(),
                  encoding="utf-8")
    banc = tmp_path / "banc_peintre.mjs"
    banc.write_text(BANC_PEINTRE, encoding="utf-8")
    conf = tmp_path / "cas_peintre.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _cas_famille(nom, frame, face="front", fmt="poker_eu"):
    g = _geom_js(fmt, 3)
    # une cellule de 0,5 mm : la toile fait 69 x 94 mm (rogne + fond perdu)
    gw = round((CT.FORMATS[fmt]["trim_mm"][0] + 6) / 0.5)
    gh = round((CT.FORMATS[fmt]["trim_mm"][1] + 6) / 0.5)
    return {"nom": nom, "g": g, "frame": frame, "face": face,
            "gw": gw, "gh": gh}


def test_chaque_famille_encre_vraiment_la_carte(tmp_path):
    """LE CONTRÔLE QUI MANQUAIT AUX FAMILLES : des PIXELS, pas des intentions.

    Une entrée de catalogue dont le peintre ne dessine rien rend exactement la
    même carte qu'une autre — et le seul juge qui existait pour cela était un
    badge d'écran, donc absent de la suite. Ici chaque famille est rendue par
    ses VRAIES fonctions (`famProfile`, son `FAM_FN`, `winMoulding`, la
    plaque) sur une grille de 0,5 mm, et l'on compte les cellules encrées.

    Quatre exigences, chacune une propriété de produit :
      1. la SIGNATURE de famille encre (sinon l'entrée de menu est un doublon);
      2. le profil encre l'ANNEAU (la masse que l'œil voit en premier) ;
      3. l'encre de l'anneau TRAVERSE LE TRAIT DE COUPE et remplit le fond
         perdu — la correction du tour 4 n'était jusqu'ici épinglée que sur
         le source (`outerRing` part de la toile) ; ici elle est COMPTÉE,
         famille par famille, sur la bande de 3 mm qui part du bord de
         fichier ;
      4. la plaque du bas ne monte jamais dans l'illustration."""
    cas = [_cas_famille(f["id"], {"family": f["id"], "rarity": "rare"})
           for f in FR.FAMILIES]
    res = _banc_peintre(tmp_path, cas)
    assert len(res) == len(FR.FAMILIES)
    zones = {r[0]: r[7] for r in _profile_rows(_js())}
    for r in res:
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        e = r["etapes"]
        assert e["signature"]["ops"] >= 1, \
            f"{r['nom']} : le peintre de famille ne dessine rien"
        assert e["signature"]["toile"] > 0.0005, \
            f"{r['nom']} : la signature n'encre aucune cellule"
        assert e["profil"]["toile"] > 0.02, \
            f"{r['nom']} : le profil n'encre que {e['profil']['toile']:.4f}"
        anneau = [e["tout"][k] for k in ("haut", "bas", "gauche", "droite")]
        assert sum(1 for v in anneau if v > 0.03) >= 3, \
            f"{r['nom']} : anneau presque vide {anneau}"
        if zones[r["nom"]] != "vide":
            assert e["profil"]["perdu"] > 0.6, \
                f"{r['nom']} : le fond perdu n'est encré qu'à "  \
                f"{e['profil']['perdu']:.2f} — l'anneau s'arrête à la coupe"
        assert e["plaque"]["fenetre"] == 0, \
            f"{r['nom']} : la plaque monte dans l'illustration"


def test_la_famille_gravure_encre_le_recto_et_le_dos_miroir(tmp_path):
    """La septième famille, recto ET dos MIROIR. « Miroir du recto » est le dos
    que l'habillage de « gravée » choisit (`back: "mirror"`), et le seul des
    sept à le faire : il passe par la branche `else` de `paintBack`, qui
    rappelle `famProfile` puis le `FAM_FN` de la famille — si le peintre neuf
    n'y dessine pas, le dos d'un jeu « gravée » est celui d'une carte sans
    famille. Les six autres archétypes portent des dos à MOTIF (soleil,
    chevrons, écailles…) dont le code est hors de la tranche extraite : ce banc
    ne les mesure pas, et ne prétend pas le faire.

    Le décalage de repérage, lui, ne se mesure pas ici : 0,2 mm valent 2,36 px
    à 300 DPI, soit moins d'une demi-cellule de la grille. Il est ÉPINGLÉ au
    source — c'est la raison publiée de l'existence de cette famille, elle ne
    peut pas disparaître en silence."""
    src = _js()
    dos = _js_fn(src, "paintBack")
    assert "famProfile(ctx, m, f);" in dos and "const fam = FAM_FN[f.family];" \
        in dos, "la branche miroir de paintBack a changé de forme"
    assert "const POCHOIR_MM = 0.2;" in src, \
        "le repérage décalé de 0,2 mm — LA raison publiée de cette famille — " \
        "n'est plus écrit"
    assert "ctx.translate(u * POCHOIR_MM, u * POCHOIR_MM);" in src, \
        "l'aplat de pochoir n'est plus décalé : la famille perd sa raison"
    assert FR.ARCHETYPE_FRAMES["gravee"]["family"] == "gravure"
    hab = dict(FR.ARCHETYPE_FRAMES["gravee"])
    cas = [_cas_famille("gravure/recto", hab),
           _cas_famille("gravure/miroir", hab, face="back")]
    res = {r["nom"]: r for r in _banc_peintre(tmp_path, cas)}
    for nom, r in res.items():
        assert r["ok"], f"{nom} : {r.get('err')}"
        assert r["famille"] == "gravure", r
        e = r["etapes"]
        assert e["tout"]["toile"] > 0.05, f"{nom} : {e['tout']['toile']:.4f}"
        for k in ("haut", "bas", "gauche", "droite"):
            assert e["tout"][k] > 0.05, f"{nom} : anneau {k} vide"
    recto = res["gravure/recto"]["etapes"]
    assert recto["signature"]["ops"] >= 4, recto["signature"]
    assert recto["plaque"]["plaque"] > 0.5, \
        f"la plaque « cartouche » ne remplit pas sa boîte : {recto['plaque']}"
    assert recto["moulure"]["toile"] > 0.004, \
        f"l'aplat de pochoir n'encre rien : {recto['moulure']}"


def test_deux_familles_ne_peuvent_pas_dessiner_la_meme_signature(tmp_path):
    """LA LEÇON, ARMÉE — et elle ne l'était pas.

    On avait publié, après la mutation du navigateur, que « le compte de
    signatures de pixels ne suffit pas » : la graine de `matter` dépend de
    l'index de famille, donc deux familles au dessin IDENTIQUE rendent quand
    même des images différentes au bruit près, et le compteur de signatures
    reste vert. La revue adverse l'a démontré sur la suite elle-même : aliaser
    `deco: famDeco -> famRunic` laissait 154/154 tests VERTS. Le seul
    instrument qui le voyait était un badge d'écran, hors intégration.

    Ici le banc rend, pour chaque famille, l'EMPREINTE de son bitmap de
    signature (FNV-1a sur la grille de 0,5 mm) et l'on exige que les sept
    soient DEUX À DEUX DISTINCTES. Indépendant du navigateur, de la fenêtre
    d'affichage et des tons — c'est le dessin lui-même qui est comparé.

    Relevé du jour (empreinte:cellules encrées) :
      runic 9eb83889:1134 · arcane 185c2317:230 · timber 37b9d043:1972
      deco b33056cd:520 · neon e47ffc52:591 · sable 29a699ed:24
      gravure 80e086d5:386
    """
    cas = [_cas_famille(f["id"], {"family": f["id"], "rarity": "rare"})
           for f in FR.FAMILIES]
    res = _banc_peintre(tmp_path, cas)
    emp = {}
    for r in res:
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        e = r["etapes"]["signature"]["emp"]
        assert e["n"] > 0, f"{r['nom']} : signature vide"
        emp[r["nom"]] = e["h"]
    doubles = [(a, b) for a in emp for b in emp
               if a < b and emp[a] == emp[b]]
    assert not doubles, \
        f"familles au dessin identique : {doubles} ({emp})"
    assert len(set(emp.values())) == len(FR.FAMILIES)
    # ... et le même fait, lu au source : une famille = SON peintre.
    src = _js()
    m = re.search(r"const FAM_FN = \{(.*?)\};", src, re.S)
    assert m, "table FAM_FN absente"
    paires = re.findall(r"(\w+): (\w+)", m.group(1))
    assert [p[0] for p in paires] == [f["id"] for f in FR.FAMILIES], paires
    fns = [p[1] for p in paires]
    assert len(set(fns)) == len(fns), f"deux familles partagent un peintre : {fns}"


def test_le_banc_voit_deux_familles_qui_dessinent_la_meme_chose(tmp_path):
    """LE CONTRÔLE NÉGATIF DE L'EMPREINTE, sur la mutation EXACTE que la revue
    a fait passer : `deco` aliasée sur le peintre de `runic`. Sans ce contrôle,
    l'exigence de distinction ci-dessus pourrait n'être qu'une décoration —
    elle passerait tout aussi bien si le banc rendait sept empreintes
    aléatoires. (La mutation porte sur la COPIE du banc, jamais sur le dépôt ;
    `WIN_SHAPE` est aligné en même temps, sans quoi les deux dessins
    différeraient par le seul découpage de fenêtre.)"""
    code = _painter_js_source()
    assert "deco: famDeco" in code and 'deco: "chamfer"' in code
    mut = code.replace("deco: famDeco", "deco: famRunic")
    mut = mut.replace('deco: "chamfer"', 'deco: "rect"', 1)
    cas = [_cas_famille(n, {"family": n, "rarity": "rare"})
           for n in ("deco", "runic")]
    sain = {r["nom"]: r["etapes"]["signature"]["emp"]["h"]
            for r in _banc_peintre(tmp_path, cas)}
    clone = {r["nom"]: r["etapes"]["signature"]["emp"]["h"]
             for r in _banc_peintre(tmp_path, cas, mut)}
    assert sain["deco"] != sain["runic"], sain
    assert clone["deco"] == clone["runic"], \
        f"le banc ne VOIT pas deux peintres identiques : {clone}"


def test_le_banc_du_peintre_rougit_si_une_famille_cesse_de_dessiner(tmp_path):
    """LE CONTRÔLE NÉGATIF. Un banc qui ne peut pas rougir ne prouve rien : on
    vide le peintre de la famille neuve et l'encre de sa signature DOIT
    disparaître. (La mutation est faite sur la copie du banc, jamais sur le
    dépôt.)"""
    code = _painter_js_source()
    i = code.index("function famGravure(")
    j = code.index("{", i)
    mut = code[:j + 1] + " return; " + code[j + 1:]
    cas = [_cas_famille("gravure", dict(FR.ARCHETYPE_FRAMES["gravee"]))]
    sain = _banc_peintre(tmp_path, cas)[0]
    mort = _banc_peintre(tmp_path, cas, mut)[0]
    assert sain["ok"] and mort["ok"], (sain.get("err"), mort.get("err"))
    assert sain["etapes"]["signature"]["ops"] >= 4
    assert mort["etapes"]["signature"]["ops"] == 0, \
        "le peintre vidé dessine encore : le banc ne mesure pas ce qu'il dit"
    assert mort["etapes"]["signature"]["toile"] == 0
    assert mort["etapes"]["tout"]["toile"] < sain["etapes"]["tout"]["toile"], \
        "retirer la signature ne change rien à la carte entière"


# ── 15.3 les sept habillages : des données, validées, que T3 importe ─────────

def test_le_banc_applique_la_garde_de_visibilite_de_la_plaque(tmp_path):
    """LE BANC DOIT MENTIR COMME LE PAINTER, OU NE PAS MESURER.

    `paintFront` ne dessine la plaque que si `m.plate.h > u * 6` : sous cette
    hauteur elle n'existe pas dans le fichier livre. Le banc, lui, la dessinait
    toujours — un habillage dont la fenetre descend trop bas passait donc
    « plaque remplie a 0,98 » alors que le fichier ne portait RIEN a cet
    endroit. Mesure : la fenetre de « gravee » a 63 mm de haut laisse 5,0 mm de
    plaque ; le painter ne trace rien, le banc lisait 0,9774.

    L'habillage livre laisse 7,0 mm : un millimetre au-dessus de la falaise.
    Ce test tient les deux bouts — la garde, et la marge qui reste."""
    court = dict(FR.ARCHETYPE_FRAMES["gravee"])
    court["window"] = dict(court["window"])
    court["window"]["h"] = 63.0
    cas = [_cas_famille("plaque-5mm", court),
           _cas_famille("livre", dict(FR.ARCHETYPE_FRAMES["gravee"]))]
    res = {r["nom"]: r for r in _banc_peintre(tmp_path, cas)}
    c = res["plaque-5mm"]
    assert c["ok"], c.get("err")
    assert 4.5 < c["plaque_mm"] < 6.0, c["plaque_mm"]
    assert c["plaque_vue"] is False, "la garde du painter n'est pas reflechie"
    assert c["etapes"]["plaque"]["ops"] == 0 and         c["etapes"]["plaque"]["plaque"] == 0,         "le banc dessine une plaque que le fichier ne porte pas"
    v = res["livre"]
    assert v["ok"] and v["plaque_vue"] is True
    assert v["plaque_mm"] > 6.0, v["plaque_mm"]
    assert v["etapes"]["plaque"]["plaque"] > 0.5


def test_les_sept_archetypes_ont_un_habillage_complet_et_legal():
    """L'objet de la tâche : pour CHAQUE archétype §6.2, un réglage doc.frame
    COMPLET — toutes les clés réelles sauf `art_window`, que le peintre publie
    lui-même et que personne ne saisit à la main.

    C'est cette table que la tâche 3 (models.py) IMPORTE : un modèle qui
    retaperait les réglages serait une seconde source de vérité, et la
    première divergence silencieuse serait un deck instancié qui ne ressemble
    pas à son archétype."""
    A = FR.ARCHETYPE_FRAMES
    assert tuple(A) == ARCHETYPES, list(A)
    cles = set(_js_defaults_keys(_js())) - {"art_window"}
    fams = {f["id"] for f in FR.FAMILIES}
    rars = {r["id"] for r in FR.RARITIES}
    backs = {b["id"] for b in FR.BACKS}
    corners = {c["id"] for c in FR.CORNERS}
    metals = {m["id"] for m in FR.METALS}
    for nom, hab in A.items():
        assert set(hab) == cles, \
            f"{nom} : clés manquantes {cles - set(hab)}, " \
            f"clés inconnues {set(hab) - cles}"
        assert hab["family"] in fams, f"{nom} : famille {hab['family']!r}"
        assert hab["rarity"] in rars, f"{nom} : rareté {hab['rarity']!r}"
        assert hab["back"] in backs, f"{nom} : dos {hab['back']!r}"
        assert hab["corner"] in corners, f"{nom} : coin {hab['corner']!r}"
        assert hab["metal_tone"] in metals, f"{nom} : métal {hab['metal_tone']!r}"
        for k, (lo, hi) in FR.LIMITS.items():
            if k in hab:
                assert lo <= hab[k] <= hi, \
                    f"{nom} : {k} = {hab[k]} hors de [{lo} ; {hi}]"
        w = hab["window"]
        assert isinstance(w, dict) and set(w) == {"x", "y", "w", "h", "r"}, \
            f"{nom} : fenêtre {w!r}"
        tw, th = CT.FORMATS["poker_eu"]["trim_mm"]
        assert 0 <= w["x"] and w["x"] + w["w"] <= tw + 1e-9, f"{nom} : {w}"
        assert 0 <= w["y"] and w["y"] + w["h"] <= th + 1e-9, f"{nom} : {w}"
        assert FR.LIMITS["win_r_mm"][0] <= w["r"] <= FR.LIMITS["win_r_mm"][1]
    # la famille NEUVE ne sert qu'à ce qui la demandait ; les six autres
    # habillages sortent du catalogue déjà livré (la mesure a décidé).
    neuves = {n for n, h in A.items() if h["family"] == "gravure"}
    assert neuves == {"gravee"}, neuves
    # « monstre » : l'illustration CARRÉE est l'archétype même (§6.2-5,
    # 47 x 47) — le verrou de proportions la garde carrée sous le curseur de
    # l'utilisateur. Les deux vont ensemble ou aucun des deux ne sert.
    mo = A["monstre"]
    assert mo["window"]["w"] == mo["window"]["h"], mo["window"]
    assert mo["win_lock"] is True, \
        "fenêtre carrée sans verrou : le premier glissement la rend rectangle"
    assert all(h["win_lock"] is False for n, h in A.items() if n != "monstre"), \
        "un verrou de proportions ailleurs : il bride l'utilisateur sans raison"


def test_les_sept_habillages_rendent_sans_erreur_et_encrent_leur_bande(tmp_path):
    """Chaque habillage est RENDU par les vrais peintres, recto et dos, et
    compté : aucune exception (une exception, c'est une ligne de plus dans
    `cv.cfErrors` sur la carte livrée), et de l'encre là où l'archétype en
    attend — l'anneau et la plaque de son bas de carte."""
    cas = []
    for nom, hab in FR.ARCHETYPE_FRAMES.items():
        cas.append(_cas_famille(nom, dict(hab)))
        cas.append(_cas_famille(nom + "/dos", dict(hab), face="back"))
    res = _banc_peintre(tmp_path, cas)
    assert len(res) == 2 * len(ARCHETYPES)
    for r in res:
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        e = r["etapes"]
        assert e["tout"]["toile"] > 0.02, \
            f"{r['nom']} : carte presque vide ({e['tout']['toile']:.4f})"
        if r["nom"].endswith("/dos"):
            continue
        assert e["signature"]["ops"] >= 1, \
            f"{r['nom']} : la famille ne signe rien"
        anneau = max(e["tout"][k] for k in ("haut", "bas", "gauche", "droite"))
        assert anneau > 0.1, f"{r['nom']} : anneau vide {anneau:.4f}"
        if FR.ARCHETYPE_FRAMES[r["nom"]]["plate"]:
            assert r["plaque_vue"], \
                f"{r['nom']} : plaque de {r['plaque_mm']:.1f} mm — sous la " \
                "garde de visibilité du painter (6 mm), le fichier n'en " \
                "porte AUCUNE"
            assert r["plaque_mm"] > 6, r["plaque_mm"]
            assert e["plaque"]["plaque"] > 0.5, \
                f"{r['nom']} : la plaque ne remplit pas sa boîte"


def test_les_fenetres_des_archetypes_sont_celles_de_la_spec(tmp_path):
    """Les zones §6.2 sont la LOI (décision de conception 2) : la fenêtre
    d'illustration de chaque archétype est celle que la spec écrit en
    millimètres, et c'est la fenêtre EFFECTIVE du modèle qui le prouve — pas
    la table de réglages relue à elle-même.

    SIX des sept citent une zone d'illustration ; « légende » n'en cite pas
    (sa spec ne décrit que le bandeau de nom), sa fenêtre est donc un CHOIX
    D'IMPLÉMENTEUR — épinglé ici comme les six autres, pour qu'il ne dérive
    pas en silence : c'est la seule géométrie de cette table que personne ne
    peut re-dériver de la spec."""
    attendu = {                       # spec :323-357, en mm depuis la coupe
        "superstar": (22, 8, 36, 38),
        "duel": (4, 13, 55, 31),
        "creature": (6, 11, 51, 35),
        "arcane": (5, 9.5, 53, 39),
        "monstre": (8, 18.5, 47, 47),
        "gravee": (4, 13, 55, 61),
        # pas de zone §6.2 — choix d'implémenteur (bordure vintage de 2,5 mm,
        # photo jusqu'au bandeau de nom), publié dans la note de tâche.
        "legende": (2.5, 2.5, 58, 69.5),
    }
    assert set(attendu) == set(ARCHETYPES), \
        f"archétype sans fenêtre épinglée : {set(ARCHETYPES) - set(attendu)}"
    cas = [_cas_famille(n, dict(FR.ARCHETYPE_FRAMES[n])) for n in attendu]
    for r in _banc_peintre(tmp_path, cas):
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        got = tuple(round(v, 3) for v in r["win"])
        assert got == attendu[r["nom"]], f"{r['nom']} : {got}"


def test_les_habillages_sont_servis_en_copie_profonde():
    """`ARCHETYPE_FRAMES` est une table de MODULE : rendre ses sous-dicts tels
    quels, c'est laisser une instanciation contaminer toutes les suivantes du
    même processus (le `window` est partagé). La T3 consomme
    `archetype_frame()`, qui rend une copie PROFONDE — ce test le prouve en
    écrivant dans la copie."""
    a = FR.archetype_frame("monstre")
    a["window"]["w"] = 1.0
    a["family"] = "neon"
    b = FR.archetype_frame("monstre")
    assert b["window"]["w"] == 47.0, "le sous-dict `window` est PARTAGÉ"
    assert b["family"] == "runic"
    assert FR.ARCHETYPE_FRAMES["monstre"]["window"]["w"] == 47.0,         "la table de module a été contaminée"
    with pytest.raises(KeyError):
        FR.archetype_frame("taverne")          # 2e fournée, pas encore là


def test_les_zones_sont_celles_du_poker_et_le_disent(tmp_path):
    """CE QUE LA TABLE NE PROMET PAS, ÉCRIT NOIR SUR BLANC. Les zones §6.2
    sont transcrites pour le poker 63 x 88. Sur un format plus petit, `winMM`
    RE-BORNE la fenêtre à la rogne : mesuré ici, le carré 47 x 47 de
    « monstre » — qui EST l'archétype — devient 44,45 x 47 sur `domino` et
    31,75 x 44,45 sur `micro`, et la plaque de bas de carte passe à une hauteur
    négative sur `micro` (le painter n'en dessine alors aucune).

    Ce test ne demande pas que cela change (re-dériver les zones par format est
    un travail de modèle, donc de la T3) : il empêche que la limite se
    découvre chez un utilisateur, et il tient le commentaire de la table
    honnête."""
    cas = [_cas_famille("monstre@" + f, dict(FR.ARCHETYPE_FRAMES["monstre"]),
                        fmt=f) for f in ("poker_eu", "domino", "micro")]
    res = {r["nom"]: r for r in _banc_peintre(tmp_path, cas)}
    assert [round(v, 2) for v in res["monstre@poker_eu"]["win"]] == [8, 18.5, 47, 47]
    dom = [round(v, 2) for v in res["monstre@domino"]["win"]]
    assert dom[2] != dom[3] and dom[2] == 44.45, dom
    mic = [round(v, 2) for v in res["monstre@micro"]["win"]]
    assert mic[2:] == [31.75, 44.45], mic
    assert res["monstre@micro"]["plaque_mm"] < 0, res["monstre@micro"]["plaque_mm"]
    assert res["monstre@micro"]["plaque_vue"] is False
    # et le commentaire de la table le dit, pour qui lit la table
    py = (REPO / "backend" / "app" / "services" / "cards" / "frame.py")         .read_text(encoding="utf-8")
    assert "CES ZONES SONT CELLES DU FORMAT POKER" in py
    assert "win_lock` ne protège RIEN" in py


# ── 15.4 LA QA DE SILHOUETTES : l'arbitre, et son plancher ───────────────────

def test_le_pire_couple_de_silhouettes_reste_au_dessus_du_seuil():
    """LA QA DE SILHOUETTES EST L'ARBITRE DE TOUTE FAMILLE NOUVELLE, et le
    seuil ne bouge pas : une famille qui passe sous 4/255 se REDESSINE.

    Les deux chiffres sont mesurés au NAVIGATEUR par le badge du panneau (les
    vignettes affichées, et la toile livrée rendue par les painters du
    fichier, six raretés, masque des couches voisines actif) — la suite ne
    peut pas les recalculer sans un moteur de rendu. Ils sont donc ÉCRITS dans
    le source, sous une forme relisible, et ce test en fait un PLANCHER :
    personne ne peut inscrire un pire couple sous le seuil sans que le fichier
    rougisse, et personne ne peut effacer la mesure.

    Refaire les chiffres : ouvrir le volet « Cadre », l'infobulle du badge
    « silhouettes » publie les deux surfaces et nomme la paire."""
    src = _js()
    assert "const SIL_SEUIL = 4;" in src, "le seuil a bougé"
    m = re.search(r"MESURE-3A-TOILE\s*=\s*([\d.]+)\s*/255\s*«\s*([^»]+)»", src)
    assert m, "la mesure 3a sur la toile livrée n'est pas publiée dans le source"
    v = float(m.group(1))
    assert v >= 4, f"pire couple {v}/255 sous le seuil ({m.group(2).strip()})"
    n = re.search(r"MESURE-3A-VIGNETTE\s*=\s*([\d.]+)\s*/255\s*«\s*([^»]+)»", src)
    assert n, "la mesure 3a sur les vignettes n'est pas publiée"
    assert float(n.group(1)) >= 4, n.group(0)
    for pair in (m.group(2), n.group(2)):
        assert " x " in pair and "«" not in pair, f"paire non nommée : {pair!r}"


# ═════════════════════════════════════════════════════════════════════════════
# 16. PHASE 3c — TÂCHE 1 : LE SCEAU PRISMATIQUE À L'ÉCRAN (spec §6.2bis a + d)
#
# CE QUE LA TÂCHE LIVRE : un sous-objet `doc.frame.seal` (le PREMIER de P2),
# un peintre DÉTERMINISTE À PHASE FIXÉE inséré dans `paintFront`, et trois
# interrupteurs de PORTÉE (écran / impression / 3D) dont l'écran dit toujours
# lesquels sont actifs.
#
# CE QUE CETTE SECTION MESURE, ET AVEC QUOI :
#   · la parité du SCHÉMA (JS ↔ cards/frame.py) — lecture des deux sources et
#     exécution des deux bornes sur les douze formats ;
#   · le PEINTRE, sur le rastériseur de contrôle de la section 15 (grille de
#     0,5 mm, clip honoré) : l'anneau encre DANS sa bande et nulle part
#     ailleurs, et le fichier ne bouge pas d'une cellule quand le Sceau est
#     éteint ;
#   · le DÉTERMINISME sur les octets des fonctions pures (champ de paillettes,
#     arrêts de dégradé), plus les MUTATIONS qui doivent les faire rougir ;
#   · la PREUVE D'EMPILEMENT (§4.2) : la vraie `layers()` de core.js, exécutée
#     sur un contexte 2D raster minimal, doit basculer une couche non-empilable
#     en « empreinte » ET garder `stack_ok`.
# ═════════════════════════════════════════════════════════════════════════════

CORE_JS = REPO / "frontend" / "cardforge" / "js" / "core.js"

SEAL_PHASE_SPEC = 0.35          # spec §6.2bis-a : la phase du fichier livré
SEAL_WIDTH_LIMITS = (0.2, 6)    # plan 3c décision 1
SEAL_MIN_MM_SPEC = 0.2          # spec §6.2bis-b : trait vectoriel >= 0,2 mm


def _sceau_js_source() -> str:
    """La tranche du peintre, ÉTENDUE JUSQU'À `paintFront` — c'est là que le
    Sceau s'insère, et une tranche qui s'arrête avant ne pourrait pas prouver
    que le fichier livré ne bouge pas quand le Sceau est éteint.

    La tranche court jusqu'à `paintSeats`, que `paintFront` appelle en
    dernier ; `paintFront` appelle aussi `planOf`, qui lit
    `CF.get("type.slots")` — le banc fournit le seul stub nécessaire, en TÊTE,
    sans toucher au source."""
    src = _js()
    i = src.index("  const FAMILIES = [")
    fin = _js_fn(src, "paintSeats")
    return ("  const CF = { get: function (k, d) { return d; } };\n"
            + src[i:src.index(fin) + len(fin)])


# ── le banc du Sceau : le rastériseur de la section 15, plus les fonctions
#    pures du Sceau relues telles quelles ────────────────────────────────────
REC_JS = BANC_PEINTRE[BANC_PEINTRE.index("const N_BEZ ="):
                      BANC_PEINTRE.index("function zones(")]

BANC_SCEAU = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { st: st, model: model, winMM: winMM, WIN_SHAPE: WIN_SHAPE,"
  + " METAL_STOPS: METAL_STOPS, LIMITS: LIMITS, SEAL_KINDS: SEAL_KINDS,"
  + " SEAL_DEFAULTS: SEAL_DEFAULTS, SEAL_MIN_MM: SEAL_MIN_MM,"
  + " SEAL_PHASE: SEAL_PHASE, SEAL_SPARKS: SEAL_SPARKS,"
  + " sealOf: sealOf, sealMaxMM: sealMaxMM, sealRing: sealRing,"
  + " sealStops: sealStops, sealField: sealField, sealSeed: sealSeed,"
  + " sealSpark: sealSpark, sealLive: sealLive, paintSeal: paintSeal,"
  + " paintFront: paintFront, capOf: capOf, bandMaxMM: bandMaxMM };\n})();")();
""" + REC_JS + r"""
/* ── LA TRACE ────────────────────────────────────────────────────────────────
   L'empreinte de COUVERTURE ne peut pas juger un recto ENTIER : `paintFront`
   remplit la toile de bord à bord (étape 1, « tout sauf la fenêtre », puis la
   réserve d'illustration), donc toutes les cellules sont encrées quoi qu'on
   dessine par-dessus — mesuré : 103 776 / 103 776 à 0,25 mm de cellule. On
   hache donc la SUITE DES OPÉRATIONS : type, style, alpha, mode de fusion,
   points du chemin, arrêts de dégradé. Deux rendus identiques donnent la même
   trace ; une seule paillette déplacée la change. C'est le « octets
   identiques » du contrat, au niveau où ce banc peut le prononcer. */
function TRec(W, H, GW, GH) { Rec.call(this, W, H, GW, GH); this.hh = 2166136261; }
TRec.prototype = Object.create(Rec.prototype);
TRec.prototype.constructor = TRec;
TRec.prototype._mix = function (s) {
  const t = String(s);
  for (let i = 0; i < t.length; i++) {
    this.hh ^= t.charCodeAt(i); this.hh = Math.imul(this.hh, 16777619) >>> 0;
  }
};
TRec.prototype._pts = function () {
  for (let s = 0; s < this.sub.length; s++) {
    const sp = this.sub[s];
    for (let i = 0; i < sp.length; i++) {
      this._mix(Math.round(sp[i][0] * 100) + "," + Math.round(sp[i][1] * 100));
    }
  }
};
TRec.prototype.fill = function (rule) {
  this._mix("F|" + rule + "|" + this.fillStyle + "|" + this.globalAlpha
    + "|" + this.globalCompositeOperation);
  this._pts();
  Rec.prototype.fill.call(this, rule);
};
TRec.prototype.stroke = function () {
  this._mix("S|" + this.strokeStyle + "|" + this.lineWidth + "|"
    + this.globalAlpha + "|" + this.globalCompositeOperation);
  this._pts();
  Rec.prototype.stroke.call(this);
};
TRec.prototype.clip = function (rule) {
  this._mix("C|" + rule); this._pts();
  Rec.prototype.clip.call(this, rule);
};
TRec.prototype.createLinearGradient = function (x0, y0, x1, y1) {
  const self = this;
  self._mix("G|" + [x0, y0, x1, y1].map((v) => Math.round(v * 100)).join(","));
  return {
    addColorStop: function (t, c) { self._mix("|" + t + "|" + c); },
    toString: function () { return "grad"; },
  };
};
TRec.prototype.trace = function () {
  return ("0000000" + (this.hh >>> 0).toString(16)).slice(-8);
};

const out = [];
for (const c of CAS.cas) {
  const dpi = c.g.dpi;
  const g = Object.assign({}, c.g, { mm2px: (v) => v / 25.4 * dpi });
  try {
    const f = mod.st({ frame: c.frame });
    const m = mod.model(g, f);
    const ring = mod.sealRing(g, m, f);
    const carte = c.card || { i: 0, id: "c1" };
    const rec = () => new TRec(g.canvas_px[0], g.canvas_px[1], c.gw, c.gh);
    let k = rec();
    if (c.quoi === "front") mod.paintFront(k, g, f, carte, { frame: c.frame });
    else mod.paintSeal(k, g, m, f, carte);
    const u = g.mm2px(1);
    const O = m.outer;
    const boites = {
      /* la BANDE du Sceau, en haut : de l'anneau extérieur vers l'intérieur */
      bande: ring ? [O.x + O.w * 0.3, O.y + ring.t * 0.15,
        O.w * 0.4, Math.max(1, ring.t * 0.7)] : [0, 0, 1, 1],
      /* DEHORS : entre le bord de toile et l'anneau extérieur */
      dehors: [m.W * 0.3, 0, m.W * 0.4, Math.max(1, O.y * 0.7)],
      /* DEDANS : sous le bord intérieur de l'anneau, hors fenêtre */
      dedans: ring ? [O.x + O.w * 0.3, O.y + ring.t * 1.6,
        O.w * 0.4, Math.max(1, ring.t * 0.8)] : [0, 0, 1, 1],
      /* le coeur de la fenêtre d'illustration */
      fenetre: [m.win.x + 4 * u, m.win.y + 4 * u,
        m.win.w - 8 * u, m.win.h - 8 * u],
    };
    const parts = {};
    for (const nom of Object.keys(boites)) parts[nom] = k.part(boites[nom]);
    const e1 = k.empreinte(), t1 = k.trace();
    k = rec();
    if (c.quoi === "front") mod.paintFront(k, g, f, carte, { frame: c.frame });
    else mod.paintSeal(k, g, m, f, carte);
    const e2 = k.empreinte(), t2 = k.trace();
    out.push({ nom: c.nom, ok: true, ops: k.ops, parts: parts,
      emp: e1, emp2: e2, trace: t1, trace2: t2, cellules: c.gw * c.gh,
      anneau: ring ? { mm: ring.mm, max_mm: ring.max_mm, t: ring.t,
        outer: [ring.x, ring.y, ring.w, ring.h, ring.r],
        inner: [ring.ix, ring.iy, ring.iw, ring.ih, ring.ir] } : null,
      seal: f.seal, live: mod.sealLive(f),
      stops: mod.sealStops(f, mod.SEAL_PHASE),
      champ: JSON.stringify(mod.sealField(mod.sealSeed(carte), 24)),
      graine: mod.sealSeed(carte),
      phase: mod.SEAL_PHASE, cap: mod.capOf(g),
      seal_max: mod.sealMaxMM(g.trim_mm[0], g.trim_mm[1],
        Math.min(f.edge_mm, mod.capOf(g)), m.wm) });
  } catch (e) {
    out.push({ nom: c.nom, ok: false, err: String((e && e.stack) || e) });
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_sceau(tmp_path, cas: list, mutations=()) -> list:
    """Fait tourner le VRAI peintre du Sceau — jamais une réécriture."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du Sceau ne peut pas tourner")
    code = _sceau_js_source()
    for avant, apres in mutations:
        assert avant in code, f"mutation introuvable : {avant!r}"
        code = code.replace(avant, apres)
    js = tmp_path / "sceau.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_sceau.mjs"
    banc.write_text(BANC_SCEAU, encoding="utf-8")
    conf = tmp_path / "cas_sceau.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _cas_sceau(nom, seal, quoi="seal", fmt="poker_eu", card=None, cell=None,
               **frame):
    """Une cellule de 0,5 mm, comme au banc du peintre de la section 15 : elle
    suffit à compter l'encre de l'anneau des deux côtés de chaque arête. Le
    RECTO complet, lui, n'est pas jugé à la couverture (il encre toute la
    toile) mais à la TRACE — la finesse de grille n'y change rien."""
    c = cell if cell else 0.5
    g = _geom_js(fmt, 3)
    gw = round((CT.FORMATS[fmt]["trim_mm"][0] + 6) / c)
    gh = round((CT.FORMATS[fmt]["trim_mm"][1] + 6) / c)
    fr = {"family": "arcane", "rarity": "rare"}
    fr.update(frame)
    if seal is not None:
        fr["seal"] = seal
    return {"nom": nom, "g": g, "frame": fr, "quoi": quoi, "gw": gw, "gh": gh,
            "card": card}


SEAL_ON = {"on": True, "kind": "argent", "width_mm": 1.2,
           "scope": {"screen": True, "print": False, "mesh": False}}


def _teintes(stops) -> list:
    """Les TEINTES saturées des arrêts de dégradé, en degrés.

    Le peintre écrit ses arrêts dans l'unité NATURELLE de chaque base :
    `hsl(...)` pour l'arc-en-ciel (la teinte EST le réglage) et l'hexadécimal
    de `METAL_STOPS` pour la base calme (les tons du métal sont déjà écrits
    là-bas, une seconde table serait une seconde vérité). La conversion vit
    donc ICI, dans l'instrument de mesure, et pas dans le produit.

    Un arrêt désaturé (le blanc pur du liseré argent) n'a pas de teinte :
    l'inclure ferait mesurer 210° d'écart sur un métal parfaitement uni."""
    out = []
    for _t, css in stops:
        m = re.match(r"hsl\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%\s*\)",
                     css)
        if m:
            h, s = float(m.group(1)) % 360, float(m.group(2))
        else:
            n = re.match(r"#([0-9a-fA-F]{6})$", css)
            assert n, f"arrêt de dégradé illisible : {css!r}"
            v = int(n.group(1), 16)
            r, g, b = ((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, \
                (v & 255) / 255
            mx, mn = max(r, g, b), min(r, g, b)
            d, lum = mx - mn, (mx + mn) / 2
            if d == 0:
                h, s = 0.0, 0.0
            else:
                s = d / (1 - abs(2 * lum - 1)) * 100
                if mx == r:
                    h = 60 * (((g - b) / d) % 6)
                elif mx == g:
                    h = 60 * ((b - r) / d + 2)
                else:
                    h = 60 * ((r - g) / d + 4)
                h %= 360
        if s >= 5:
            out.append(h)
    return out


def _etendue(hues) -> float:
    """L'ÉTENDUE CIRCULAIRE des teintes : 360 moins le plus grand écart entre
    deux teintes voisines sur le cercle. Un arc-en-ciel complet la sature ;
    un métal uni la laisse près de zéro."""
    if len(hues) < 2:
        return 0.0
    xs = sorted(hues)
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    gaps.append(360 - xs[-1] + xs[0])
    return round(360 - max(gaps), 2)


# ── 16.1 le SCHÉMA, des deux côtés ───────────────────────────────────────────

def test_le_sceau_a_le_meme_schema_des_deux_cotes():
    """`doc.frame.seal` est le PREMIER sous-objet de P2 : son schéma vit dans
    le bloc partagé du catalogue, et `cards/frame.py` en porte le jumeau. Deux
    schémas qui dérivent, c'est une carte enregistrée avec une portée que le
    backend ne saura pas relire — le même défaut que deux catalogues."""
    b = _catalog_block(_js())
    assert _js_list(b, "SEAL_KINDS") == _py_list(FR.SEAL_KINDS), \
        "SEAL_KINDS diverge entre mod-frame.js et cards/frame.py"
    assert [k["id"] for k in FR.SEAL_KINDS] == ["argent", "dorure"], \
        FR.SEAL_KINDS
    m = re.search(r"const SEAL_MIN_MM = ([\d.]+);", b)
    assert m, "SEAL_MIN_MM n'est pas dans le bloc partagé du catalogue"
    assert float(m.group(1)) == FR.SEAL_MIN_MM == SEAL_MIN_MM_SPEC, \
        f"plancher imprimeur : JS {m.group(1)} / backend {FR.SEAL_MIN_MM}"
    d = re.search(r"const SEAL_DEFAULTS = \{(.*?)\};", b, re.S)
    assert d, "SEAL_DEFAULTS absent du bloc partagé"
    txt = d.group(1)
    assert re.search(r"on:\s*false", txt), \
        "le Sceau doit être ÉTEINT par défaut — sinon tous les jeux existants " \
        "changent d'aspect au premier chargement"
    assert FR.SEAL_DEFAULTS["on"] is False, FR.SEAL_DEFAULTS
    assert re.search(r'kind:\s*"' + FR.SEAL_DEFAULTS["kind"] + '"', txt), txt
    assert re.search(r"width_mm:\s*" + str(FR.SEAL_DEFAULTS["width_mm"]), txt), \
        txt
    for k, v in FR.SEAL_DEFAULTS["scope"].items():
        assert re.search(k + r":\s*" + ("true" if v else "false"), txt), \
            f"portée {k} : le défaut diverge ({txt})"


def test_la_borne_de_largeur_du_sceau_est_ecrite_des_deux_cotes():
    """`seal_width_mm` passe par le test générique de parité des bornes ; ici
    on épingle la VALEUR décidée (0,2 à 6 mm) et son plancher : 0,2 mm est le
    trait minimal d'un imprimeur foil (spec §6.2bis-b), pas un chiffre rond."""
    assert FR.LIMITS["seal_width_mm"] == list(SEAL_WIDTH_LIMITS), \
        FR.LIMITS.get("seal_width_mm")
    assert FR.LIMITS["seal_width_mm"][0] == FR.SEAL_MIN_MM
    b = _catalog_block(_js())
    m = re.search(r"seal_width_mm:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]", b)
    assert m, "seal_width_mm absent de LIMITS côté JS"
    assert [float(m.group(1)), float(m.group(2))] == list(SEAL_WIDTH_LIMITS)


def test_le_catalogue_publie_le_sceau():
    """Ce que l'écran propose doit être joignable de l'extérieur : la route
    `/catalog` publie les métaux du Sceau, son plancher et ses défauts."""
    did = _deck()
    cat = _api("GET", f"/api/cards/{did}/frame/catalog").json()["catalog"]
    assert cat["seal_kinds"] == FR.SEAL_KINDS
    assert cat["seal_min_mm"] == FR.SEAL_MIN_MM
    assert cat["seal_defaults"] == FR.SEAL_DEFAULTS
    assert cat["limits"]["seal_width_mm"] == list(SEAL_WIDTH_LIMITS)


def test_la_borne_de_format_du_sceau_est_la_meme_des_deux_cotes(tmp_path):
    """L'anneau doit tenir ENTRE la coupe et la fenêtre : au-delà, ce n'est
    plus un contour, c'est une plaque posée sur l'illustration. La borne se
    DÉDUIT donc du format ET de la fenêtre — patron `bandMaxMM`. Les douze
    formats, exécutés des deux côtés."""
    cas = [_cas_sceau(f, SEAL_ON, fmt=f) for f in sorted(CT.FORMATS)]
    res = _banc_sceau(tmp_path, cas)
    assert len(res) == len(cas)
    for r in res:
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        g = CT.geom(r["nom"], 300, 3, 3, 3)
        tw, th = g.trim_mm
        edge = min(1.6, FR.band_max_mm(tw, th))
        win = FR._win_of(None, g)
        attendu = FR.seal_max_mm(tw, th, edge, win)
        assert abs(r["seal_max"] - attendu) < 1e-9, \
            f"{r['nom']} : JS {r['seal_max']} != backend {attendu}"
        assert r["anneau"] is not None, f"{r['nom']} : anneau dégénéré"
        assert r["anneau"]["mm"] > 0


def test_sous_le_plancher_imprimeur_le_sceau_ne_dessine_PAS(tmp_path):
    """LE DÉFAUT DE LA RONDE 1, mesuré. `sealMaxMM` rabotait la largeur à la
    place disponible SANS jamais confronter le résultat au plancher qu'il
    prétendait tenir : une fenêtre posée à 1,61 mm de la coupe laissait
    0,01 mm de place, et l'écran DESSINAIT une bande de 0,01 mm (0,118 px à
    300 DPI), le panneau lisait « Bande de 0.01 mm » et `/metrics` publiait
    `seal_mm[0] = 0.01`. C'est exactement la largeur que le préflight de la
    tâche 2 est spécifié REFUSER (trait ≥ 0,2 mm, spec §6.2bis-b) : l'écran
    dessinait ce que la presse rejette.

    Sous le plancher il n'y a pas d'anneau étroit, il n'y a PAS D'ANNEAU — et
    l'écran le dit."""
    def fen(d):
        return {"x": d, "y": d, "w": 63 - 2 * d, "h": 88 - 2 * d, "r": 0}

    cas = [
        # 1,61 mm de marge − 1,6 mm de retrait = 0,01 mm : sous le plancher
        _cas_sceau("sous", dict(SEAL_ON, width_mm=3), window=fen(1.61)),
        # 1,85 − 1,6 = 0,25 mm : au-dessus, sans ambiguïté. (Le cas EXACTEMENT
        # à 0,2 n'est pas épinglé : `1.8 - 1.6` vaut 0,19999999999999973 en
        # IEEE 754, et le verdict y bascule sur le dernier bit. La comparaison
        # porte volontairement sur la valeur non arrondie, donc le doute tombe
        # du côté du REFUS — jamais du côté d'une largeur que la presse
        # rejette. Épingler ce bit-là figerait un accident, pas un contrat.)
        _cas_sceau("juste", dict(SEAL_ON, width_mm=3), window=fen(1.85)),
    ]
    res = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    for r in res.values():
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
    assert res["sous"]["seal_max"] == 0, \
        f"la borne rend {res['sous']['seal_max']} mm — sous le plancher de " \
        f"{SEAL_MIN_MM_SPEC} mm elle doit rendre 0"
    assert res["sous"]["anneau"] is None, \
        f"un anneau de {res['sous']['anneau']} est dessiné sous le plancher"
    assert res["sous"]["ops"] == 0, \
        "le peintre pose des opérations alors qu'aucun anneau n'est légal"
    assert res["juste"]["seal_max"] == 0.25, res["juste"]["seal_max"]
    assert res["juste"]["anneau"]["mm"] == 0.25
    assert res["juste"]["ops"] > 0

    # ... le backend rend le même verdict, et `/metrics` ne publie plus 0,01
    g = CT.geom("poker_eu", 300, 3, 3, 3)
    assert FR.seal_max_mm(63, 88, 1.6, fen(1.61)) == 0
    assert FR.seal_max_mm(63, 88, 1.6, fen(1.85)) == 0.25
    m = FR.frame_metrics(g, 0.9, 1.1, 1.6, 5.5, fen(1.61), FR.seal_of(SEAL_ON))
    assert m["seal_mm"] == [0.0, 0.0], m["seal_mm"]
    assert m["seal_px"][0] == 0.0, m["seal_px"]

    # ... et l'ÉCRAN LE DIT : la ligne d'état nomme le plancher et le format
    fn = _js_fn(_js(), "sealText")
    assert "aucun contour" in fn, \
        "la ligne d'état ne dit pas qu'aucun contour n'est dessiné"
    assert "0,2" in fn or "SEAL_MIN_MM" in fn, \
        "la ligne d'état ne nomme pas le plancher d'imprimeur"


def test_sans_le_plancher_la_bande_de_0_01_mm_revient(tmp_path):
    """LE CONTRÔLE NÉGATIF DU PLANCHER. On rend à `sealMaxMM` sa forme d'avant
    (« tout ce qui est positif ») : la bande de 0,01 mm DOIT revenir, sinon ce
    test ne prouve rien et le plancher n'est qu'une décoration."""
    fen = {"x": 1.61, "y": 1.61, "w": 59.78, "h": 84.78, "r": 0}
    cas = [_cas_sceau("sous", dict(SEAL_ON, width_mm=3), window=fen)]
    avec = _banc_sceau(tmp_path, cas)[0]
    assert avec["anneau"] is None
    sans = _banc_sceau(tmp_path, cas, mutations=[
        ("return v >= SEAL_MIN_MM ? Math.round(v * 100) / 100 : 0;",
         "return v > 0 ? Math.round(v * 100) / 100 : 0;"),
    ])[0]
    assert sans["ok"], sans.get("err")
    assert sans["anneau"] is not None and sans["anneau"]["mm"] == 0.01, \
        f"sans le plancher on attendait 0,01 mm, on trouve {sans['anneau']}"


def test_le_sceau_absent_du_document_repart_des_defauts(tmp_path):
    """Un preset ou un jeu enregistré AVANT cette tâche n'a pas de clé `seal` :
    `st()` doit y injecter les défauts, et rendre un objet NEUF (un alias de
    `DEFAULTS.seal` ferait d'un réglage de carte une écriture dans le schéma
    partagé avec le registre du CORE)."""
    cas = [
        _cas_sceau("absent", None),
        _cas_sceau("hostile", {"on": "oui", "kind": "platine",
                               "width_mm": 999, "scope": "toutes"}),
        _cas_sceau("plancher", {"on": True, "width_mm": 0.01,
                                "scope": {"screen": False}}),
        # `null` = ABSENT, pas zéro. Le générique `num()` de la pièce prend
        # `Number(null) === 0` et ramènerait la largeur au plancher (0,2) là
        # où le backend, lui, rend le DÉFAUT (1,2). Deux valeurs différentes
        # pour un même document : la branche du Sceau tranche pour « absent ».
        _cas_sceau("nul", {"on": True, "width_mm": None}),
    ]
    res = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    for r in res.values():
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
    a = res["absent"]["seal"]
    assert a == FR.SEAL_DEFAULTS, a
    assert res["nul"]["seal"]["width_mm"] == FR.SEAL_DEFAULTS["width_mm"], \
        f"width_mm null -> {res['nul']['seal']['width_mm']} au lieu du défaut"
    h = res["hostile"]["seal"]
    assert h["on"] is False, "une chaîne n'est pas un booléen"
    assert h["kind"] == FR.SEAL_DEFAULTS["kind"], h
    assert h["width_mm"] == SEAL_WIDTH_LIMITS[1], h
    assert h["scope"] == FR.SEAL_DEFAULTS["scope"], h
    p = res["plancher"]["seal"]
    assert p["width_mm"] == SEAL_WIDTH_LIMITS[0], p
    assert p["scope"]["screen"] is False and p["scope"]["print"] is False


def test_le_backend_normalise_le_sceau_comme_l_ecran():
    """La parité d'EXÉCUTION, pas de lecture : les mêmes corps hostiles passés
    à `frame.seal_of` doivent donner ce que `st()` rend — À UNE EXCEPTION
    NOMMÉE, qui est la doctrine déjà en place pour `win_r_mm` et les quatre
    longueurs du cadre.

    Les deux côtés n'ont pas le même travail. `st()` RÉPARE un document que
    l'écran possède déjà : une valeur folle y est ramenée dans les bornes,
    parce qu'un document illisible n'est pas une option. `seal_of()` VALIDE le
    corps d'une requête : une valeur hors bornes y est REFUSÉE, avec la borne
    citée, pour que le client sache qu'il a envoyé n'importe quoi (règle « un
    corps mal formé ne fait jamais un 500, il fait un 400 qui nomme »). La
    divergence ne peut pas mordre en pratique : l'écran n'envoie au backend
    que du `st()` déjà normalisé.

    Sur tout le reste — défauts, appartenance au catalogue, booléens, portées
    partielles — les deux sont le même."""
    assert FR.seal_of(None) == FR.SEAL_DEFAULTS
    assert FR.seal_of({}) == FR.SEAL_DEFAULTS
    # 1. ce qui n'est pas un booléen retombe au défaut, des deux côtés
    h = FR.seal_of({"on": "oui", "kind": "platine", "scope": "toutes"})
    assert h == FR.SEAL_DEFAULTS, h
    # 2. `null` vaut ABSENT des deux côtés — jamais zéro
    assert FR.seal_of({"width_mm": None}) == FR.SEAL_DEFAULTS
    # 3. une portée PARTIELLE complète les deux autres avec leur défaut
    p = FR.seal_of({"on": True, "width_mm": 0.2, "scope": {"screen": False}})
    assert p["scope"] == {"screen": False, "print": False, "mesh": False}
    assert p["on"] is True and p["width_mm"] == 0.2
    # 4. hors bornes : le backend REFUSE en nommant la borne (l'écran, lui,
    #    ramène — mesuré par le banc, test voisin)
    for mauvais in (999, 0.01, "beaucoup", float("nan")):
        with pytest.raises(ValueError) as exc:
            FR.seal_of({"width_mm": mauvais})
        assert "Sceau" in str(exc.value), str(exc.value)


def test_le_compte_de_cles_du_document_suit_le_sceau():
    """`seal` est la 29e clé de `doc.frame`. Le compte est écrit dans le
    commentaire de `st()` ET dans `frame.py` : trois endroits, un seul
    nombre."""
    cles = _js_defaults_keys(_js())
    assert "seal" in cles, f"la clé seal manque à DEFAULTS : {cles}"
    assert len(cles) == 31, f"{len(cles)} clés dans DEFAULTS : {cles}"
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert "30 clés que l'on écrit" in py, \
        "le commentaire de l'habillage ne suit pas les clés neuves (30 " \
        "écrites, la 31e étant `art_window`, publiée par le painter)"


# ── 16.2 le PEINTRE : des pixels, pas des intentions ─────────────────────────

def test_l_anneau_du_sceau_encre_sa_bande_et_rien_d_autre(tmp_path):
    """LE SEUIL DE LA TÂCHE, mesuré au rastériseur : l'anneau encre la BANDE
    (de la coupe rentrée vers l'intérieur, sur `width_mm`) et NI le fond perdu
    au-delà, NI l'intérieur de la carte, NI la fenêtre d'illustration.

    Une bande de 3 mm est choisie pour que la grille de 0,5 mm ait de quoi
    compter des deux côtés de chaque arête."""
    seal = dict(SEAL_ON, width_mm=3)
    res = {r["nom"]: r for r in _banc_sceau(tmp_path, [
        _cas_sceau("on", seal),
        _cas_sceau("off", dict(seal, on=False)),
    ])}
    on = res["on"]
    assert on["ok"], on.get("err")
    p = on["parts"]
    assert p["bande"] > 0.95, \
        f"l'anneau n'encre que {p['bande']:.2f} de sa propre bande"
    assert p["dehors"] == 0, \
        f"l'anneau déborde vers la coupe ({p['dehors']:.3f})"
    assert p["dedans"] == 0, \
        f"l'anneau déborde vers l'intérieur ({p['dedans']:.3f})"
    assert p["fenetre"] == 0, \
        f"l'anneau entre dans la fenêtre ({p['fenetre']:.3f})"
    off = res["off"]
    assert off["ok"], off.get("err")
    assert off["ops"] == 0 and off["emp"]["n"] == 0, \
        "Sceau éteint : le peintre ne doit pas poser une seule opération"


def test_sans_le_clip_l_anneau_deborde_partout(tmp_path):
    """LE CONTRÔLE NÉGATIF DU CLIP. Un découpage qui ne sert jamais ne prouve
    rien : on le neutralise et l'encre DOIT sortir — sur la fenêtre
    d'illustration comme sur le fond perdu."""
    cas = [_cas_sceau("on", dict(SEAL_ON, width_mm=3))]
    avec = _banc_sceau(tmp_path, cas)[0]
    assert avec["parts"]["fenetre"] == 0 and avec["parts"]["dehors"] == 0
    sans = _banc_sceau(tmp_path, cas, mutations=[
        ('ctx.clip("evenodd");   /* CF-SCEAU-CLIP */', ""),
    ])[0]
    assert sans["ok"], sans.get("err")
    assert sans["parts"]["fenetre"] > 0.5, \
        "sans le clip, l'anneau devrait couvrir la fenêtre — le test ne " \
        "prouverait rien"
    assert sans["parts"]["dehors"] > 0.5, sans["parts"]


def test_le_sceau_eteint_ne_change_pas_un_pixel_du_recto(tmp_path):
    """LE FICHIER LIVRÉ D'AVANT, À L'OPÉRATION PRÈS. Le Sceau est éteint par
    défaut : tout jeu existant doit rendre EXACTEMENT le même recto qu'avant
    la tâche. On le prouve en comparant la TRACE du recto complet à celle du
    MÊME recto peint par un `paintFront` d'où l'appel au Sceau a été RETIRÉ —
    pas à un nombre recopié qui vieillirait.

    Pourquoi la trace et pas la couverture : `paintFront` remplit la toile de
    bord à bord (étape 1 « tout sauf la fenêtre », puis la réserve
    d'illustration), donc l'empreinte de cellules encrées vaut 1 partout quoi
    qu'on peigne — mesuré, 103 776 / 103 776 cellules à 0,25 mm."""
    cas = [_cas_sceau("defaut", None, quoi="front"),
           _cas_sceau("eteint", dict(SEAL_ON, on=False), quoi="front")]
    avec = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    src = _sceau_js_source()
    appel = "    paintSeal(ctx, g, m, f, card);"
    assert appel in src, "l'appel du Sceau dans paintFront a bougé"
    sans = {r["nom"]: r for r in
            _banc_sceau(tmp_path, cas, mutations=[(appel, "")])}
    for nom in ("defaut", "eteint"):
        assert avec[nom]["ok"] and sans[nom]["ok"], (avec[nom], sans[nom])
        assert avec[nom]["ops"] == sans[nom]["ops"], \
            f"{nom} : {avec[nom]['ops']} opérations avec le Sceau éteint " \
            f"contre {sans[nom]['ops']} sans lui"
        assert avec[nom]["trace"] == sans[nom]["trace"], \
            f"{nom} : le recto bouge alors que le Sceau est éteint " \
            f"({avec[nom]['trace']} != {sans[nom]['trace']})"
    # ... et le CONTRÔLE : allumé, la trace DOIT changer.
    allume = _banc_sceau(tmp_path, [
        _cas_sceau("allume", dict(SEAL_ON, width_mm=3), quoi="front")])[0]
    assert allume["ok"], allume.get("err")
    assert allume["ops"] > avec["defaut"]["ops"], \
        "allumé, le Sceau ne pose pas une opération de plus"
    assert allume["trace"] != avec["defaut"]["trace"], \
        "allumé, le Sceau ne change rien : le test précédent ne prouve rien"


def test_le_recto_est_le_meme_a_deux_rendus(tmp_path):
    """DÉTERMINISME À PHASE FIXÉE. Deux rendus du même recto, même carte, même
    phase : la même empreinte, à la cellule. C'est ce qui rend l'aperçu et le
    fichier livré indiscernables — et ce que `Math.random` casserait."""
    for quoi in ("seal", "front"):
        r = _banc_sceau(tmp_path, [
            _cas_sceau("deux-" + quoi, dict(SEAL_ON, width_mm=3), quoi=quoi)])[0]
        assert r["ok"], r.get("err")
        assert r["trace"] == r["trace2"], \
            f"{quoi} : deux rendus, deux traces ({r['trace']} / {r['trace2']})"
        assert r["emp"] == r["emp2"], \
            f"{quoi} : deux rendus, deux dessins ({r['emp']} / {r['emp2']})"


def test_le_champ_de_paillettes_est_seme_par_carte(tmp_path):
    """Spec §6.2bis-a : « PRNG SEEDÉ, seed = id de carte — jamais
    `Math.random` ». Deux cartes différentes n'ont pas le même scintillement ;
    la MÊME carte a toujours le sien."""
    cas = [
        _cas_sceau("c1", SEAL_ON, card={"i": 0, "id": "c1"}),
        _cas_sceau("c1bis", SEAL_ON, card={"i": 0, "id": "c1"}),
        _cas_sceau("c2", SEAL_ON, card={"i": 1, "id": "c2"}),
        _cas_sceau("dragon", SEAL_ON, card={"i": 7, "id": "dragon"}),
        _cas_sceau("sans-id", SEAL_ON, card={"i": 0}),
    ]
    res = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    for r in res.values():
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
    assert res["c1"]["champ"] == res["c1bis"]["champ"], \
        "la même carte n'a pas le même champ de paillettes"
    assert res["c1"]["champ"] != res["c2"]["champ"], \
        "deux cartes partagent leur champ de paillettes"
    assert res["c1"]["champ"] != res["dragon"]["champ"]
    assert len({res[k]["graine"] for k in ("c1", "c2", "dragon")}) == 3, \
        "les graines se collisionnent"
    # une carte SANS `id` retombe sur l'identité que le CORE lui donnerait
    # (`normCard` : id = "c" + (i + 1)) — pas sur une graine constante.
    assert res["sans-id"]["graine"] == res["c1"]["graine"]
    # ... et la graine ARRIVE JUSQU'AU RECTO LIVRÉ, pas seulement jusqu'à la
    # fonction pure : deux cartes, deux traces de `paintFront`.
    rectos = {r["nom"]: r for r in _banc_sceau(tmp_path, [
        _cas_sceau("r1", dict(SEAL_ON, width_mm=3), quoi="front",
                   card={"i": 0, "id": "c1"}),
        _cas_sceau("r2", dict(SEAL_ON, width_mm=3), quoi="front",
                   card={"i": 1, "id": "c2"}),
    ])}
    assert rectos["r1"]["ok"] and rectos["r2"]["ok"]
    assert rectos["r1"]["trace"] != rectos["r2"]["trace"], \
        "deux cartes rendent le même recto : la graine n'arrive pas au peintre"


def test_le_sceau_ne_tire_aucun_hasard(tmp_path):
    """LE CONTRÔLE NÉGATIF DU PRNG. On remplace le générateur seedé par
    `Math.random` : le champ de paillettes DOIT cesser d'être reproductible.
    Sans ce contrôle, `prng` pourrait n'être qu'une décoration."""
    src = _sceau_js_source()
    i = src.index("function sealField(")
    j = src.index("function paintSeal(")
    assert "Math.random" not in src[i:j], \
        "le bloc du Sceau tire déjà au hasard"
    cas = [_cas_sceau("c1", SEAL_ON, card={"i": 0, "id": "c1"}),
           _cas_sceau("c1bis", SEAL_ON, card={"i": 0, "id": "c1"})]
    faux = {r["nom"]: r for r in _banc_sceau(tmp_path, cas, mutations=[
        ("const rnd = prng(seed);", "const rnd = Math.random;"),
    ])}
    assert faux["c1"]["ok"] and faux["c1bis"]["ok"]
    assert faux["c1"]["champ"] != faux["c1bis"]["champ"], \
        "avec Math.random le champ reste identique — le banc ne mesure rien"


def test_la_graine_ne_promet_que_ce_que_l_identite_des_cartes_tient():
    """CE QUE LA RONDE 1 AFFIRMAIT DE TROP. Le commentaire de `sealSeed`
    disait que la graine « survit à un réordonnancement du jeu ». C'est faux
    sur le deck PAR DÉFAUT : `cards/data.py` assigne `id = "c" + idx`, un
    numéro POSITIONNEL, quand aucune colonne `id` n'est mappée — et c'est le
    défaut. Déplacer une carte change alors son id, donc sa graine, donc son
    scintillement.

    La phrase vraie est conditionnelle : la graine est l'IDENTITÉ de la carte,
    et cette identité ne suit la carte QUE si une colonne `id` est mappée.

    Ce test ne juge pas une tournure : il épingle le FAIT dont la phrase
    dépend (le repli positionnel de data.py) et interdit le retour de
    l'affirmation inconditionnelle. Si data.py se met un jour à donner un
    identifiant stable, ce test rougit et la phrase est à réécrire — dans le
    bon sens."""
    data_py = (REPO / "backend" / "app" / "services" / "cards"
               / "data.py").read_text(encoding="utf-8")
    assert '"id": (cid or ("c" + str(idx)))[:64]' in data_py, \
        "le repli d'identifiant de data.py a changé : la note de `sealSeed` " \
        "sur la portabilité de la graine est à re-mesurer"
    src = _js()
    # le commentaire vit AVANT la fonction : on prend le bloc entier, de son
    # titre jusqu'à la fonction suivante.
    bloc = src[src.index("LA GRAINE, PAR CARTE"):src.index("function sealField(")]
    assert "survit a un reordonnancement" not in bloc \
        and "survit à un réordonnancement" not in bloc, \
        "l'affirmation inconditionnelle est revenue — elle est FAUSSE sans " \
        "colonne `id` mappée"
    assert "colonne" in bloc, \
        "le commentaire ne dit pas à quelle condition la graine suit la carte"
    assert "code MORT" in bloc, \
        "le repli positionnel passe toujours pour du code utile"


def test_une_graine_constante_donnerait_le_meme_scintillement_a_tout_le_jeu(
        tmp_path):
    """LE CONTRÔLE NÉGATIF DE LA GRAINE PAR CARTE. On remplace l'identité de la
    carte par une constante : les deux cartes doivent alors rendre le MÊME
    recto. C'est le défaut que la spec nomme en écrivant « seed = id de
    carte » — un jeu de 200 cartes dont les 200 contours scintillent au même
    endroit n'est pas un foil, c'est un motif."""
    cas = [_cas_sceau("r1", dict(SEAL_ON, width_mm=3), quoi="front",
                      card={"i": 0, "id": "c1"}),
           _cas_sceau("r2", dict(SEAL_ON, width_mm=3), quoi="front",
                      card={"i": 1, "id": "c2"})]
    vrai = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    assert vrai["r1"]["trace"] != vrai["r2"]["trace"]
    fige = {r["nom"]: r for r in _banc_sceau(tmp_path, cas, mutations=[
        ("const pts = sealField(sealSeed(card), SEAL_SPARKS);",
         "const pts = sealField(1234, SEAL_SPARKS);"),
    ])}
    assert fige["r1"]["ok"] and fige["r2"]["ok"], fige
    assert fige["r1"]["trace"] == fige["r2"]["trace"], \
        "avec une graine constante les deux rectos diffèrent encore — le " \
        "banc ne mesure pas ce qu'il annonce"


def test_la_phase_du_fichier_livre_est_canonique(tmp_path):
    """Spec §6.2bis-a : « La phase du fichier livré est CANONIQUE (0.35) ».
    Elle est écrite une fois, et le peintre n'a AUCUNE autre source de phase —
    ni pointeur, ni horloge, ni compteur d'animation. C'est ce qui garde
    l'aperçu identique au fichier."""
    src = _js()
    m = re.search(r"const SEAL_PHASE = ([\d.]+);", src)
    assert m, "SEAL_PHASE n'est pas déclarée"
    assert float(m.group(1)) == SEAL_PHASE_SPEC, \
        f"phase canonique {m.group(1)} au lieu de {SEAL_PHASE_SPEC}"
    corps = _js_fn(src, "paintSeal")
    for interdit in ("Date.now", "performance.now", "requestAnimationFrame",
                     "clientX", "offsetX", "event", "Math.random"):
        assert interdit not in corps, \
            f"le peintre du Sceau lit {interdit} : le fichier livré ne serait " \
            "plus l'aperçu"
    assert corps.count("SEAL_PHASE") >= 1, \
        "le peintre n'utilise pas la phase canonique"
    r = _banc_sceau(tmp_path, [_cas_sceau("phase", SEAL_ON)])[0]
    assert r["phase"] == SEAL_PHASE_SPEC
    faux = _banc_sceau(tmp_path, [_cas_sceau("phase", dict(SEAL_ON, width_mm=3))],
                       mutations=[("const SEAL_PHASE = 0.35;",
                                   "const SEAL_PHASE = 0.71;")])[0]
    vrai = _banc_sceau(tmp_path, [
        _cas_sceau("phase", dict(SEAL_ON, width_mm=3))])[0]
    assert faux["stops"] != vrai["stops"], \
        "la phase ne change rien au dégradé : elle n'est pas branchée"


# ── 16.3 la PORTÉE : hors écran, la base calme ───────────────────────────────

def test_dans_la_portee_ecran_le_contour_est_un_arc_en_ciel(tmp_path):
    """Spec §6.2bis-a : base arc-en-ciel, saturation 70-90 %. Mesuré sur les
    arrêts de dégradé RÉELS du peintre, pas sur l'intention."""
    r = _banc_sceau(tmp_path, [_cas_sceau("ecran", SEAL_ON)])[0]
    assert r["ok"], r.get("err")
    assert r["live"] is True
    hues = _teintes(r["stops"])
    assert _etendue(hues) >= 300, \
        f"étendue de teintes {_etendue(hues)}° — ce n'est pas un arc-en-ciel"
    for _t, css in r["stops"]:
        s = float(re.match(r"hsl\([\d.]+,\s*([\d.]+)%", css).group(1))
        assert 70 <= s <= 90, f"saturation {s} % hors de la plage 70-90 de la spec"


def test_hors_portee_ecran_le_contour_reste_dans_sa_base_calme(tmp_path):
    """Spec §6.2bis-d : « 3D uniquement » est une configuration de PREMIER
    RANG — l'écran montre alors le contour dans sa base calme (or/argent non
    holo). Mesuré : l'étendue de teintes tombe à presque rien, et les tons
    viennent de `METAL_STOPS`, pas d'une seconde table de couleurs."""
    cas = [_cas_sceau("3d-argent", {"on": True, "kind": "argent",
                                    "width_mm": 1.2,
                                    "scope": {"screen": False, "print": False,
                                              "mesh": True}}),
           _cas_sceau("3d-dorure", {"on": True, "kind": "dorure",
                                    "width_mm": 1.2,
                                    "scope": {"screen": False, "print": True,
                                              "mesh": True}})]
    res = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    for r in res.values():
        assert r["ok"], f"{r['nom']} : {r.get('err')}"
        assert r["live"] is False
        e = _etendue(_teintes(r["stops"]))
        assert e <= 15, \
            f"{r['nom']} : étendue de teintes {e}° — la base calme " \
            "arc-en-cielise"
        assert r["ops"] > 0, f"{r['nom']} : hors portée écran, rien n'est peint"
    assert res["3d-argent"]["stops"] != res["3d-dorure"]["stops"], \
        "argent et dorure rendent le même métal"
    src = _js()
    corps = _js_fn(src, "sealStops")
    assert "METAL_STOPS" in corps, \
        "la base calme n'emprunte pas les tons de métal déjà écrits"


def test_la_portee_ecran_ignoree_ferait_rougir_la_base_calme(tmp_path):
    """LE CONTRÔLE NÉGATIF DE LA PORTÉE. Un peintre qui ignore
    `scope.screen` peint l'arc-en-ciel partout : la mesure de la base calme
    doit alors échouer."""
    cas = [_cas_sceau("3d", {"on": True, "kind": "dorure", "width_mm": 1.2,
                             "scope": {"screen": False, "print": False,
                                       "mesh": True}})]
    sourd = _banc_sceau(tmp_path, cas, mutations=[
        ("return !!(f.seal && f.seal.on && f.seal.scope && f.seal.scope.screen);",
         "return !!(f.seal && f.seal.on);"),
    ])[0]
    assert sourd["ok"], sourd.get("err")
    assert _etendue(_teintes(sourd["stops"])) >= 300, \
        "en ignorant la portée, la base reste calme — le test ne prouve rien"


# ── 16.4 la PARITÉ DES NOMBRES : /metrics porte l'anneau ─────────────────────

def test_la_route_metrics_publie_l_anneau_du_sceau():
    """La vérité vectorielle du Sceau est portable en NOMBRES PURS (l'anneau
    est un rectangle arrondi partout). Le backend les publie — c'est ce dont
    le masque de foil (tâche 2) et la portée 3D (tâche 3) auront besoin, et
    c'est ce que la pastille de vérification confronte à l'écran."""
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/frame/metrics",
             json={"fmt": "poker_eu", "dpi": 300, "bleed_mm": 3, "safe_mm": 3,
                   "corner_mm": 3, "line_mm": 0.9, "gap_mm": 1.1,
                   "edge_mm": 1.6, "inner_mm": 5.5, "seal": SEAL_ON})
    assert r.status_code == 200, r.text[:400]
    m = r.json()["metrics"]
    assert "seal_mm" in m and "seal_px" in m, sorted(m)
    assert m["seal_mm"][0] == 1.2
    assert m["seal_px"][0] == _exact_px(1.2, 300)
    # l'anneau extérieur : la coupe rentrée de `edge_mm`, en px depuis la TOILE
    g = CT.geom("poker_eu", 300, 3, 3, 3)
    assert abs(m["seal_px"][1] - (g.bleed_off_px[0] + 1.6 / 25.4 * 300)) < 0.02,         m["seal_px"]


def test_une_largeur_de_sceau_hors_bornes_fait_400_jamais_500():
    did = _deck()
    for mauvais, mot in ((0.05, "0,2"), (12, "6"), ("beaucoup", "millimètres")):
        r = _api("POST", f"/api/cards/{did}/frame/metrics",
                 json={"fmt": "poker_eu", "dpi": 300, "corner_mm": 3,
                       "seal": dict(SEAL_ON, width_mm=mauvais)})
        assert r.status_code == 400, (mauvais, r.status_code, r.text[:200])
        assert "Sceau" in r.text or "sceau" in r.text, r.text[:200]


def test_l_ecran_et_le_backend_comptent_les_memes_pixels_d_anneau(tmp_path):
    """PARITÉ D'EXÉCUTION : `localMetrics` de l'écran et `frame_metrics` du
    backend, sur les douze formats ET SUR SIX LARGEURS. Deux anneaux
    différents, ce serait un masque de foil décalé du contour affiché.

    LA RONDE 1 NE COMPARAIT QUE LA GÉOMÉTRIE DE L'ANNEAU — jamais la LARGEUR,
    c'est-à-dire le seul nombre que la borne de format CHANGE. Soixante-douze
    cas sains ne prouvaient rien sur le seul chiffre qui bouge. Les largeurs
    d'épreuve encadrent le plancher et un arrondi non trivial (0,205 mm et
    2,005 mm : leur deuxième décimale doit tomber de la même façon des deux
    côtés)."""
    src = _js()
    assert "seal_px" in _js_fn(src, "localMetrics"), \
        "l'écran ne publie pas l'anneau : la pastille ne le vérifierait jamais"
    assert "seal:" in _js_fn(src, "verify"), \
        "la vérification n'envoie pas le Sceau au backend"
    LARGEURS = (0.2, 0.205, 1.2, 2.005, 5.5, 6)
    cas = [_cas_sceau(f"{f}/{w}", dict(SEAL_ON, width_mm=w), fmt=f)
           for f in sorted(CT.FORMATS) for w in LARGEURS]
    res = {r["nom"]: r for r in _banc_sceau(tmp_path, cas)}
    assert len(res) == len(CT.FORMATS) * len(LARGEURS)
    borne_mordue = 0
    for nom, r in res.items():
        assert r["ok"], f"{nom} : {r.get('err')}"
        fmt, w = nom.rsplit("/", 1)
        g = CT.geom(fmt, 300, 3, 3, 3)
        win = FR._win_of(None, g)
        seal = FR.seal_of(dict(SEAL_ON, width_mm=float(w)))
        m = FR.frame_metrics(g, 0.9, 1.1, 1.6, 5.5, win, seal)
        a = r["anneau"]
        assert a is not None, f"{nom} : anneau dégénéré côté écran"
        # la GÉOMÉTRIE (x, y, w, h, r) de l'anneau extérieur...
        for i, v in enumerate(a["outer"]):
            assert abs(m["seal_px"][i + 1] - v) < 0.02, \
                f"{nom} : anneau px[{i}] écran {v} != backend {m['seal_px'][i + 1]}"
        # ... ET LA LARGEUR TRACÉE, le nombre que la borne change
        assert abs(m["seal_mm"][0] - a["mm"]) < 1e-9, \
            f"{nom} : largeur écran {a['mm']} != backend {m['seal_mm'][0]}"
        assert abs(m["seal_mm"][1] - r["seal_max"]) < 1e-9, \
            f"{nom} : borne écran {r['seal_max']} != backend {m['seal_mm'][1]}"
        # les PIXELS publiés sont ceux que l'écran TRACE (`ring.t`), pas ceux
        # du millimètre arrondi pour l'affichage : à 0,205 mm le panneau lit
        # « 0.21 mm » et la presse reçoit 2,42 px, pas 2,48. Même doctrine que
        # `edge_px` — le millimètre s'arrondit à l'écran, le pixel jamais.
        assert abs(m["seal_px"][0] - a["t"]) < 0.01, \
            f"{nom} : largeur px publiée {m['seal_px'][0]} != tracée {a['t']}"
        assert a["mm"] >= SEAL_MIN_MM_SPEC, \
            f"{nom} : largeur TRACÉE {a['mm']} mm sous le plancher imprimeur"
        if a["mm"] < float(w):
            borne_mordue += 1
    assert borne_mordue > 0, \
        "sur 72 cas la borne de format n'a jamais mordu : le test ne mesure " \
        "pas ce qu'il annonce"


# ── 16.5 LE PANNEAU : l'écran dit toujours quelle portée est active ──────────

def test_le_panneau_porte_le_groupe_du_sceau_et_ses_trois_interrupteurs():
    src = _js()
    fn = _js_fn(src, "buildUI")
    assert "Sceau prismatique" in fn, "le groupe du Sceau n'existe pas"
    assert "UI.sealOn" in fn and "UI.sealKind" in fn and "UI.sealW" in fn, \
        "case, métal ou largeur manquants"
    for cle, lbl in (("screen", "écran"), ("print", "impression"),
                     ("mesh", "3D")):
        assert '"' + cle + '", "' + lbl + '"' in fn, \
            f"l'interrupteur de portée {cle} n'est pas étiqueté « {lbl} »"
    assert "LIMITS.seal_width_mm" in fn, \
        "le curseur de largeur n'est pas borné par LIMITS"


def test_l_ecran_dit_toujours_quelle_portee_est_active():
    """Spec §6.2bis-d : « L'écran dit toujours quelle portée est active. » La
    ligne d'état nomme les trois surfaces, dit ce que CET écran montre, et ne
    promet RIEN des deux autres — leurs consommateurs sont les tâches 2 et 3."""
    src = _js()
    fn = _js_fn(src, "sealText")
    assert "Portée déclarée" in fn, "la ligne d'état ne nomme pas la portée"
    for mot in ("écran", "impression", "3D"):
        assert mot in fn, f"la portée « {mot} » n'est pas nommée"
    assert "base calme" in fn, \
        "hors portée écran, la ligne ne dit pas que le contour est calme"
    assert "phase canonique" in fn, \
        "dans la portée écran, la ligne ne dit pas que l'aperçu EST le fichier"
    # AUCUNE promesse sur ce qui n'est pas livré : pas de « bientôt », pas de
    # tâche future citée à l'utilisateur.
    for promesse in ("bientôt", "à venir", "tâche 2", "tâche 3", "prochaine"):
        assert promesse not in fn.lower(), \
            f"la ligne d'état promet quelque chose (« {promesse} »)"
    assert "sealText(" in _js_fn(src, "syncNow"), \
        "la ligne d'état n'est jamais rafraîchie"


# ── 16.6 LA PREUVE D'EMPILEMENT (§4.2), EXÉCUTÉE ─────────────────────────────
#
# Le peintre du Sceau pose une bande de reflet en `overlay`. Là où sa propre
# base n'est pas parfaitement opaque — la frange d'anticrénelage du découpage
# de l'anneau — le résultat DÉPEND de ce qu'il y a dessous : la couche cesse
# d'être « isolée » et `layers()` la garde en « EMPREINTE » (delta des
# cumulatifs, exact par construction). C'est le mécanisme que §4.2 a été conçu
# pour absorber ; il n'avait, jusqu'ici, AUCUN test exécutable dans la suite —
# seulement une lecture de source (test_cards_forge3d.py).
#
# Ce banc exécute la VRAIE `layers()` de core.js sur un contexte 2D raster
# minimal. Le moteur (`renderRaw`) est un stub du banc — il ne fait que ce que
# le contrat de core.js promet (`only_z`, `paper`) ; la logique jugée, elle,
# est le produit relu tel quel.

BANC_EMPILEMENT = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const W = 24, H = 24;

function Ctx(cv) { this.cv = cv; this.fillStyle = "#000000";
  this.globalAlpha = 1; this.stk = [];
  this.globalCompositeOperation = "source-over"; }
/* save/restore et globalAlpha : le peintre du verso (3c-T4) les emploie, et
   un banc qui les ignorerait rendrait un verdict sur un autre dessin. */
Ctx.prototype.save = function () {
  this.stk.push([this.fillStyle, this.globalAlpha,
    this.globalCompositeOperation]);
};
Ctx.prototype.restore = function () {
  const s = this.stk.pop();
  if (s) { this.fillStyle = s[0]; this.globalAlpha = s[1];
    this.globalCompositeOperation = s[2]; }
};
function couleur(s) {
  let m = /^#([0-9a-f]{6})$/i.exec(s);
  if (m) { const n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 255]; }
  m = /^rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)$/.exec(s);
  if (m) return [+m[1], +m[2], +m[3],
    Math.round((m[4] === undefined ? 1 : +m[4]) * 255)];
  return [0, 0, 0, 255];
}
/* UN BANC QUI NE SAIT PAS DOIT LE DIRE. Ce mélangeur ne connaît que deux
   modes ; s'il en rencontrait un troisième — `multiply` d'une pièce Matières,
   `screen` d'un futur Sceau — il le traiterait en silence comme du
   source-over et rendrait un verdict « isolée » qui ne vaut rien. Un banc qui
   ment plus tard est le trou qu'on a déjà payé trois fois : il REFUSE. */
const OPS_CONNUS = ["source-over", "overlay"];
function melange(d, o, src, op, ga) {
  if (ga !== undefined && ga !== 1) src = [src[0], src[1], src[2], src[3] * ga];
  if (OPS_CONNUS.indexOf(op) < 0) {
    throw new Error("banc d'empilement : mode de fusion inconnu \"" + op
      + "\" — le mélangeur ne sait composer que " + OPS_CONNUS.join(", ")
      + ". L'ajouter ICI avant de s'en servir dans un cas.");
  }
  const sa = src[3] / 255, da = d[o + 3] / 255;
  if (op === "overlay") {
    for (let k = 0; k < 3; k++) {
      const b = d[o + k] / 255, s = src[k] / 255;
      const r = b <= 0.5 ? 2 * b * s : 1 - 2 * (1 - b) * (1 - s);
      /* le fond compte pour ce qu'il PÈSE : sur un fond transparent le
         mélange retombe sur la source, comme le fait un vrai canvas. */
      const eff = r * da + s * (1 - da);
      d[o + k] = Math.round((eff * sa + (d[o + k] / 255) * da * (1 - sa))
        / (sa + da * (1 - sa) || 1) * 255);
    }
    d[o + 3] = Math.round((sa + da * (1 - sa)) * 255);
    return;
  }
  const a = sa + da * (1 - sa);
  for (let k = 0; k < 3; k++) {
    d[o + k] = a ? Math.round(((src[k] / 255) * sa
      + (d[o + k] / 255) * da * (1 - sa)) / a * 255) : 0;
  }
  d[o + 3] = Math.round(a * 255);
}
Ctx.prototype.fillRect = function (x, y, w, h) {
  const src = couleur(this.fillStyle), d = this.cv.d;
  for (let j = Math.max(0, y | 0); j < Math.min(this.cv.height, (y + h) | 0); j++)
    for (let i = Math.max(0, x | 0); i < Math.min(this.cv.width, (x + w) | 0); i++)
      melange(d, (j * this.cv.width + i) * 4, src,
        this.globalCompositeOperation, this.globalAlpha);
};
Ctx.prototype.getImageData = function (x, y, w, h) {
  return { width: w, height: h, data: this.cv.d.slice() };
};
Ctx.prototype.putImageData = function (img) { this.cv.d.set(img.data); };
Ctx.prototype.drawImage = function (src, dx, dy, dw, dh) {
  const d = this.cv.d, s = src.d;
  /* la forme A DEUX ARGUMENTS (celle de `stackOnto` de core.js) : plein
     cadre, source-over pur. La forme a CINQ (le peintre du verso) place et
     redimensionne — echantillonnage au plus proche, le banc juge des aplats. */
  if (dw === undefined) {
    for (let o = 0; o < d.length; o += 4)
      melange(d, o, [s[o], s[o + 1], s[o + 2], s[o + 3]],
        this.globalCompositeOperation, this.globalAlpha);
    return;
  }
  const W = this.cv.width, H = this.cv.height;
  const x0 = Math.max(0, Math.floor(dx)), x1 = Math.min(W, Math.ceil(dx + dw));
  const y0 = Math.max(0, Math.floor(dy)), y1 = Math.min(H, Math.ceil(dy + dh));
  for (let j = y0; j < y1; j++) {
    let sy = Math.floor((j + 0.5 - dy) / dh * src.height);
    sy = Math.min(src.height - 1, Math.max(0, sy));
    for (let i = x0; i < x1; i++) {
      let sx = Math.floor((i + 0.5 - dx) / dw * src.width);
      sx = Math.min(src.width - 1, Math.max(0, sx));
      const o = (sy * src.width + sx) * 4;
      melange(d, (j * W + i) * 4, [s[o], s[o + 1], s[o + 2], s[o + 3]],
        this.globalCompositeOperation, this.globalAlpha);
    }
  }
};
function mkCanvas(w, h) {
  const cv = { _w: 0, _h: 0, d: new Uint8ClampedArray(0) };
  const alloc = () => { cv.d = new Uint8ClampedArray(cv._w * cv._h * 4); };
  Object.defineProperty(cv, "width", { get: () => cv._w,
    set: (v) => { cv._w = v | 0; alloc(); } });
  Object.defineProperty(cv, "height", { get: () => cv._h,
    set: (v) => { cv._h = v | 0; alloc(); } });
  cv.getContext = () => new Ctx(cv);
  cv.width = w; cv.height = h;
  return cv;
}
const document = { createElement: () => mkCanvas(0, 0) };
/* le peintre du verso (3c-T4) fabrique sa toile de cuisson par
   `document.createElement` : le banc l'expose donc au global, comme un
   navigateur le fait. */
globalThis.document = document;
const PAPER = "#ffffff";
let RENDER_CHAIN = Promise.resolve();
/* LE PEINTRE DU VERSO PERSONNALISE, CHARGE TEL QUEL quand un cas le demande
   (argv[4] = la tranche de mod-frame.js). Un stub qui imiterait ce qu'on
   espere ne prouverait que le stub. */
const VERSO = (process.argv[4] && CAS.verso)
  ? new Function("return (function(){ "
    + readFileSync(process.argv[4], "utf8")
    + "\nreturn { paintBackCustom: paintBackCustom };\n})();")()
  : null;
const VIMG = (CAS.verso && CAS.verso.img) ? (function (s) {
  const im = { width: s.w, height: s.h,
    d: new Uint8ClampedArray(s.w * s.h * 4) };
  for (let o = 0; o < im.d.length; o += 4) {
    im.d[o] = s.rgba[0]; im.d[o + 1] = s.rgba[1];
    im.d[o + 2] = s.rgba[2]; im.d[o + 3] = s.rgba[3];
  }
  return im;
})(CAS.verso.img) : null;
const PEINTRES = [
  { z: 20, fn: (c) => { c.globalCompositeOperation = "source-over";
    c.fillStyle = "#204080"; c.fillRect(2, 2, 20, 20); } },
  { z: 40, fn: (c) => {
    if (VERSO) {
      /* `paintBack` remplit la toile de la matiere de bande AVANT d'appeler
         le verso personnalise : le banc pose la meme base opaque. */
      c.globalCompositeOperation = "source-over";
      c.fillStyle = CAS.verso.base; c.fillRect(0, 0, W, H);
      VERSO.paintBackCustom(c, { W: W, H: H, u: 1,
        trim: { x: 2, y: 2, w: W - 4, h: H - 4 } }, CAS.verso.f,
        (file) => (VIMG && file === "img_1.png")
          ? { img: VIMG, ok: true, file: file }
          : { img: null, ok: false, file: file });
      return;
    }
    /* la BASE du Sceau, opaque, sur sa bande */
    c.globalCompositeOperation = "source-over";
    c.fillStyle = "#c08040"; c.fillRect(4, 4, 16, 6);
    /* la BANDE DE REFLET en overlay — elle déborde de la base opaque, comme
       la frange d'anticrénelage du découpage de l'anneau. */
    c.globalCompositeOperation = CAS.op;
    c.fillStyle = "rgba(255,255,255,0.6)"; c.fillRect(4, 4, 16, 10);
    c.globalCompositeOperation = "source-over";
  } },
];
function renderRaw(i, o) {
  const cv = mkCanvas(W, H);
  const c = cv.getContext("2d");
  if (o.paper !== false) { c.fillStyle = PAPER; c.fillRect(0, 0, W, H); }
  const only = Array.isArray(o.only_z) ? o.only_z : null;
  for (const p of PEINTRES) {
    if (only && only.indexOf(p.z) < 0) continue;
    p.fn(c);
  }
  return Promise.resolve(cv);
}
const hasDOM = true;
const layers = new Function("document", "PAPER", "renderRaw", "RENDER_CHAIN",
  "hasDOM", "return (function(){ " + CODE + "\nreturn layers; })();")(
  document, PAPER, renderRaw, RENDER_CHAIN, hasDOM);
layers(0, { face: CAS.face === "back" ? "back" : "front", groups: [
  { role: "illustration", z: [20] }, { role: "cadre", z: [40] }] })
  .then((L) => {
    /* le pixel CENTRAL de la couche « cadre » LIVREE : une couche declaree
       exacte mais vide serait un export qui ment (§6.2ter, « l'export par
       couches livre le verso »). */
    const cadre = L.layers.filter((l) => l.role === "cadre")[0];
    const o = (((H >> 1) * W) + (W >> 1)) * 4;
    const d = cadre ? cadre.canvas.d : null;
    process.stdout.write(JSON.stringify({
      stack_ok: L.stack_ok, face: L.face,
      modes: L.layers.map((l) => [l.role, l.mode]),
      couche_cadre: d ? [d[o], d[o + 1], d[o + 2], d[o + 3]] : null,
    }));
  }, (e) => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


def _banc_empilement(tmp_path, op: str, echec: bool = False):
    """Rend le verdict du banc — ou, si `echec`, le message par lequel il a
    refusé de rendre un verdict."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'empilement ne peut pas tourner")
    src = CORE_JS.read_text(encoding="utf-8")
    code = "async " + _js_fn(src, "layers")
    js = tmp_path / "layers.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_empilement.mjs"
    banc.write_text(BANC_EMPILEMENT, encoding="utf-8")
    conf = tmp_path / f"cas_empilement_{op}.json"
    conf.write_text(json.dumps({"op": op}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    if echec:
        assert r.returncode != 0, \
            f"le banc a rendu un verdict au lieu de refuser : {r.stdout[:300]}"
        return r.stderr
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def test_le_banc_d_empilement_refuse_un_mode_de_fusion_qu_il_ne_sait_pas(
        tmp_path):
    """Son mélangeur ne connaît que `source-over` et `overlay`. Un troisième
    mode — le `multiply` que la pièce Matières pose déjà, ou un futur `screen`
    du Sceau — serait traité en silence comme du source-over, et le banc
    rendrait « isolée » sur une couche qui ne l'est pas. Il doit REFUSER en
    nommant le mode."""
    err = _banc_empilement(tmp_path, "multiply", echec=True)
    assert "multiply" in err, err[-600:]
    assert "mode de fusion inconnu" in err, err[-600:]


def test_le_sceau_pose_bien_une_bande_de_reflet_en_overlay():
    """La PRÉMISSE du banc d'empilement, relue dans le peintre livré : c'est
    bien un `overlay` que le Sceau pose, et il est posé sous `save()` — sans
    quoi il fuirait sur tout ce que `paintFront` dessine après lui."""
    corps = _js_fn(_js(), "paintSeal")
    assert 'globalCompositeOperation = "overlay"' in corps, \
        "la bande de reflet n'est plus en overlay : re-mesurer la preuve " \
        "d'empilement avant de recopier ce test"
    i = corps.index('globalCompositeOperation = "overlay"')
    assert "ctx.save();" in corps[:i] and "ctx.restore();" in corps[i:], \
        "l'overlay n'est pas encadré par save/restore"


def test_une_couche_non_empilable_bascule_en_empreinte_et_la_preuve_tient(
        tmp_path):
    """§4.2, EXÉCUTÉ. Une couche qui pose un mode de fusion non-empilable là où
    sa propre base n'est pas opaque ne peut pas être livrée « isolée » : la
    vraie `layers()` de core.js la garde en « empreinte » (delta des
    cumulatifs) et `stack_ok` TIENT quand même.

    Le contrôle est dans le même banc : la MÊME couche repeinte en
    `source-over` redevient « isolée ». Sans lui, un `layers()` qui écrirait
    « empreinte » partout passerait."""
    r = _banc_empilement(tmp_path, "overlay")
    modes = dict(r["modes"])
    assert modes["illustration"] == "isolee", r["modes"]
    assert modes["cadre"] == "empreinte", \
        f"la couche du cadre reste « {modes['cadre']} » malgré l'overlay"
    assert r["stack_ok"] is True, \
        "la preuve d'empilement tombe : l'empreinte n'est pas exacte"
    temoin = _banc_empilement(tmp_path, "source-over")
    assert dict(temoin["modes"])["cadre"] == "isolee", \
        "en source-over la couche reste « empreinte » — le banc ne " \
        "discrimine rien"
    assert temoin["stack_ok"] is True


# ═════════════════════════════════════════════════════════════════════════════
# 17. LE VERSO PERSONNALISÉ — phase 3c, tâche 4 (spec §6.2ter :448-464)
#
# Le dos sort du seul catalogue : `back: "custom"` = UNE IMAGE IMPORTÉE, plus
# une PILE ORDONNÉE de calques (≤ 6), chacun avec opacité, échelle et mode de
# fusion. C'est la PREMIÈRE pile ordonnée de P2 (tout le reste y est booléen ou
# énuméré), et elle arrive avec trois contraintes qui ne se négocient pas :
#
#   · les modes de fusion autorisés restent ceux qui EMPILENT (§4.2) — le
#     `multiply` est CUIT dans les pixels du calque, jamais demandé au
#     compositeur ; la couche « cadre » du rendu par couches reste isolée ;
#   · la route d'images de P2 est SA PROPRE route (règle 8 : jamais celle de
#     la voisine), avec LE MÊME durcissement que celle de P3 (réservation
#     exclusive, bombe de pixels à l'en-tête, liste blanche avant le disque,
#     compteur MAX+1, plafond) ;
#   · « enregistrer comme modèle » emporte les RÉGLAGES, jamais les octets :
#     les `src` deck-locaux sont purgés, et le modèle le DIT.
# ═════════════════════════════════════════════════════════════════════════════

BACK_LAYERS_MAX_SPEC = 6        # plan 3c décision 5 : « ×≤6 »
BACK_IMAGES_MAX_SPEC = 8        # plan 3c décision 5 : « cap 8 »
BACK_OPACITY_SPEC = (0.0, 1.0)
BACK_SCALE_SPEC = (0.25, 4.0)
BACK_BLENDS_SPEC = ("normal", "multiply")


def _bloc_const(nom: str, src: str | None = None):
    """La valeur littérale d'une constante du bloc catalogue."""
    block = _catalog_block(src if src is not None else _js())
    m = re.search(r"const\s+" + nom + r"\s*=\s*([^;]+);", block, re.S)
    assert m, f"constante {nom} absente du bloc catalogue de mod-frame.js"
    return m.group(1).strip()


# ── 17.1 le VOCABULAIRE, des deux côtés ──────────────────────────────────────

def test_le_dos_personnalise_est_au_catalogue_des_deux_cotes():
    """`BACKS += custom` — parité stricte (le test générique compare déjà les
    deux listes ; celui-ci NOMME l'entrée et son rang). Un dos que l'écran
    propose et que le backend ne connaît pas, c'est un menu qui ment."""
    js = dict(_js_list(_catalog_block(_js()), "BACKS"))
    py = dict(_py_list(FR.BACKS))
    assert js == py, (js, py)
    assert "custom" in py, f"le dos personnalisé manque : {sorted(py)}"
    assert py["custom"] == "Personnalisé", py["custom"]
    # il arrive EN DERNIER : les sept dos du catalogue gardent leur rang, donc
    # `card.back` et les habillages déjà écrits gardent le leur.
    assert [b["id"] for b in FR.BACKS][-1] == "custom", \
        "le dos personnalisé s'est inséré au milieu du catalogue"
    assert len(FR.BACKS) == 8, len(FR.BACKS)


def test_le_schema_du_verso_custom_est_le_meme_des_deux_cotes():
    """Deux clés neuves dans `doc.frame` (`back_image`, `back_layers`), leurs
    bornes dans LIMITS, le plafond de la pile, le vocabulaire de fusion et les
    défauts d'un calque : tout cela vit dans le bloc catalogue partagé et
    `cards/frame.py` en porte le jumeau."""
    src = _js()
    cles = _js_defaults_keys(src)
    assert "back_image" in cles and "back_layers" in cles, cles
    assert len(cles) == 31, f"{len(cles)} clés dans DEFAULTS : {cles}"
    # les bornes, des deux côtés et au chiffre de la spec
    for k, attendu in (("back_opacity", BACK_OPACITY_SPEC),
                       ("back_scale", BACK_SCALE_SPEC)):
        assert k in FR.LIMITS, f"{k} absent de LIMITS (backend)"
        assert tuple(FR.LIMITS[k]) == attendu, FR.LIMITS[k]
        m = re.search(k + r":\s*\[([^\]]+)\]", _catalog_block(src))
        assert m, f"{k} absent de LIMITS (écran)"
        assert tuple(float(v) for v in m.group(1).split(",")) == attendu, \
            m.group(1)
    # le plafond de la pile et celui du dossier d'images
    assert FR.BACK_LAYERS_MAX == BACK_LAYERS_MAX_SPEC
    assert FR.BACK_IMAGES_MAX == BACK_IMAGES_MAX_SPEC
    assert _bloc_const("BACK_LAYERS_MAX") == str(BACK_LAYERS_MAX_SPEC)
    assert _bloc_const("BACK_IMAGES_MAX") == str(BACK_IMAGES_MAX_SPEC)
    # les modes de fusion : ceux qui EMPILENT, et rien d'autre
    js_bl = dict(_js_list(_catalog_block(src), "BACK_BLENDS"))
    py_bl = dict(_py_list(FR.BACK_BLENDS))
    assert js_bl == py_bl, (js_bl, py_bl)
    assert tuple(b["id"] for b in FR.BACK_BLENDS) == BACK_BLENDS_SPEC, py_bl
    # les défauts d'un calque
    assert FR.BACK_LAYER_DEFAULTS == {"src": "", "opacity": 1.0, "scale": 1.0,
                                      "blend": "normal"}, FR.BACK_LAYER_DEFAULTS
    assert FR.DEFAULTS_BACK == {"back_image": "", "back_layers": []}, \
        FR.DEFAULTS_BACK


def test_le_motif_des_sources_de_verso_est_ANCRE_des_deux_cotes():
    r"""`img:img_N.png` et RIEN d'autre. Le piège du `$` avec `match` a déjà
    été payé trois fois dans ce dépôt (3b-T2, 3c-T3) : côté Python c'est
    `fullmatch`, côté JS le motif porte `^…$` et une chaîne à saut de ligne
    doit être refusée des deux côtés."""
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert "BACK_SRC_RE.fullmatch" in py, \
        "le motif des sources de verso est appliqué avec `match` (le `$` " \
        "accepte un saut de ligne final)"
    assert "BACK_IMG_NAME_RE.fullmatch" in py, \
        "le motif des noms de fichier est appliqué avec `match`"
    for bon in ("", "img:img_1.png", "img:img_42.png"):
        assert FR.back_image_of(bon) == bon, bon
    for mauvais in ("img:img_1.png\n", "img:../meta.json", "img:img_1.PNG",
                    "img_1.png", "img:", "img:img_.png", None, 42, {}):
        assert FR.back_image_of(mauvais) == "", repr(mauvais)


# ── 17.2 la PARITÉ D'EXÉCUTION : deux normaliseurs, un seul résultat ─────────
#
# `seal` a une divergence VOULUE (l'écran clampe, la route refuse) parce que
# `/metrics` REÇOIT un sceau dans un corps de requête. AUCUNE route ne reçoit
# `back_image` / `back_layers` : le miroir n'a donc rien à refuser, il
# NORMALISE — et la parité se mesure sur les valeurs, y compris hors bornes.

BANC_VERSO_ST = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { st: st, DEFAULTS: DEFAULTS, backOf: backOf,"
  + " backImageOf: backImageOf, backLayersOf: backLayersOf };\n})();")();
const out = [];
for (const c of CAS.cas) {
  try {
    const f = mod.st({ frame: c.frame });
    out.push({ nom: c.nom, ok: true, back: f.back,
      /* LE DOS EFFECTIF de la carte : `f.back` quand le dos est commun,
         `card.back` sinon. C'est LUI que `paintBack` lit pour choisir sa
         branche — donc lui qui decide si le verso personnalise rend. */
      kind: mod.backOf(f, c.card || null),
      back_image: f.back_image, back_layers: f.back_layers,
      /* L'ALIAS : le tableau rendu est-il CELUI du schema ? `DEFAULTS` est
         l'objet meme que `CF.register` remet au registre du CORE — un alias
         rendu ici ferait d'un reglage de carte une ecriture dans le schema
         partage (la lecon du sous-objet `seal`, T1). */
      alias: f.back_layers === mod.DEFAULTS.back_layers });
  } catch (e) { out.push({ nom: c.nom, ok: false, err: String((e && e.stack) || e) }); }
}
process.stdout.write(JSON.stringify(out));
"""


def _verso_js_source() -> str:
    """La tranche du peintre ÉTENDUE JUSQU'À `paintBack` : c'est là que vit le
    verso personnalisé. Extraite TELLE QUELLE — une réimplémentation
    prouverait la réimplémentation."""
    src = _js()
    i = src.index("  const FAMILIES = [")
    fin = _js_fn(src, "paintBack")
    return ("  const CF = { get: function (k, d) { return d; } };\n"
            + src[i:src.index(fin) + len(fin)])


def _banc_verso_st(tmp_path, cas: list, mutations=()) -> dict:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du verso ne peut pas tourner")
    code = _verso_js_source()
    for avant, apres in mutations:
        assert avant in code, f"mutation introuvable : {avant!r}"
        code = code.replace(avant, apres)
    js = tmp_path / "verso_st.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_verso_st.mjs"
    banc.write_text(BANC_VERSO_ST, encoding="utf-8")
    conf = tmp_path / "cas_verso_st.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x for x in json.loads(r.stdout)}


VERSO_HOSTILE = {
    "absent": {},
    "vide": {"back_image": "", "back_layers": []},
    "pas_une_liste": {"back_image": None, "back_layers": "beaucoup"},
    "entrees_folles": {"back_image": "img:../meta.json",
                       "back_layers": [None, 3, "x", {"src": "img:img_2.png"}]},
    "hors_bornes": {"back_image": "img:img_1.png", "back_layers": [
        {"src": "img:img_1.png", "opacity": 9, "scale": 0, "blend": "screen"},
        {"src": "img:img_2.png", "opacity": -1, "scale": 99, "blend": None}]},
    "trop_long": {"back_image": "img:img_1.png",
                  "back_layers": [{"src": "img:img_%d.png" % i}
                                  for i in range(1, 12)]},
    "saut_de_ligne": {"back_image": "img:img_1.png\n",
                      "back_layers": [{"src": "img:img_1.png\n"}]},
    # ── LES FORMES QUI SÉPARENT VRAIMENT LES DEUX LANGAGES ────────────────
    # La première batterie passait à côté du seul cas que `bnum()` existe pour
    # fermer : elle ne donnait jamais `null` ni `""`. MESURÉ, mutant `bnum` ->
    # `num` : `{"opacity": null}` rend 0 à l'écran et 1,0 au backend — un
    # calque qui DISPARAÎT sur la carte pendant que le serveur le croit opaque.
    # C'est la divergence `width_mm: null` de la T1, sur une autre clé.
    "absent_explicite": {"back_layers": [
        {"src": "img:img_1.png", "opacity": None, "scale": None},
        {"src": "img:img_2.png", "opacity": "", "scale": "  "},
        {"src": "img:img_3.png", "opacity": [], "scale": {}}]},
    # ... et les CHAÎNES NUMÉRIQUES, que `Number()` et `float()` ne lisent PAS
    # de la même façon : « 0x10 » vaut 16 en JS et lève en Python ; « 1_0 »
    # vaut 10 en Python et NaN en JS. Atteignable par un fichier de jeu édité
    # à la main — le scénario que ce dépôt traite partout ailleurs.
    "chaines_numeriques": {"back_layers": [
        {"src": "img:img_1.png", "opacity": "0x10", "scale": "0x10"},
        {"src": "img:img_2.png", "opacity": "1_0", "scale": "1_0"},
        {"src": "img:img_3.png", "opacity": "1e0", "scale": "1e0"},
        {"src": "img:img_4.png", "opacity": " 0.5 ", "scale": " 2.5 "},
        {"src": "img:img_5.png", "opacity": "0.5", "scale": "2.5"}]},
}


def test_les_deux_normaliseurs_du_verso_rendent_LA_MEME_CHOSE(tmp_path):
    """Parité d'EXÉCUTION, pas de lecture (la leçon 3b : aucune correspondance
    de source ne remplace deux exécutions comparées). Les mêmes corps hostiles
    passent par `st()` au navigateur et par `frame.back_*_of` au backend, et le
    résultat doit être le même OBJET — bornes comprises.

    Ici les deux côtés font le même travail, et c'est dit : contrairement à
    `seal`, AUCUNE route ne reçoit ces clés, le miroir n'a donc rien à REFUSER.
    Il normalise."""
    cas = [{"nom": n, "frame": dict(f, back="custom")}
           for n, f in VERSO_HOSTILE.items()]
    res = _banc_verso_st(tmp_path, cas)
    for nom, f in VERSO_HOSTILE.items():
        r = res[nom]
        assert r["ok"], f"{nom} : {r.get('err')}"
        assert r["back_image"] == FR.back_image_of(f.get("back_image")), \
            f"{nom} : image {r['back_image']!r} vs " \
            f"{FR.back_image_of(f.get('back_image'))!r}"
        assert r["back_layers"] == FR.back_layers_of(f.get("back_layers")), \
            f"{nom} : calques {r['back_layers']} vs " \
            f"{FR.back_layers_of(f.get('back_layers'))}"
    # ... et ce que la normalisation garantit, nommé plutôt que déduit
    assert res["entrees_folles"]["back_image"] == ""
    assert res["entrees_folles"]["back_layers"] == \
        [dict(FR.BACK_LAYER_DEFAULTS, src="img:img_2.png")]
    assert len(res["trop_long"]["back_layers"]) == BACK_LAYERS_MAX_SPEC
    hb = res["hors_bornes"]["back_layers"]
    assert hb[0]["opacity"] == 1.0 and hb[0]["scale"] == BACK_SCALE_SPEC[0]
    assert hb[0]["blend"] == "normal", "un mode de fusion inconnu est accepté"
    assert hb[1]["opacity"] == 0.0 and hb[1]["scale"] == BACK_SCALE_SPEC[1]
    assert res["saut_de_ligne"]["back_image"] == ""
    assert res["saut_de_ligne"]["back_layers"] == [dict(FR.BACK_LAYER_DEFAULTS)]
    # ABSENT vaut DÉFAUT, jamais zéro — des deux côtés (le piège `num()`)
    for l in res["absent_explicite"]["back_layers"]:
        assert l["opacity"] == FR.BACK_LAYER_DEFAULTS["opacity"], l
        assert l["scale"] == FR.BACK_LAYER_DEFAULTS["scale"], l
    # UNE CHAÎNE N'EST UN NOMBRE QUE SI LES DEUX LANGAGES LA LISENT PAREIL :
    # décimale simple, sans espace, sans base, sans exposant, sans souligné.
    ch = res["chaines_numeriques"]["back_layers"]
    for i in range(4):
        assert ch[i]["opacity"] == FR.BACK_LAYER_DEFAULTS["opacity"], (i, ch[i])
        assert ch[i]["scale"] == FR.BACK_LAYER_DEFAULTS["scale"], (i, ch[i])
    assert ch[4]["opacity"] == 0.5 and ch[4]["scale"] == 2.5, ch[4]


def test_la_pile_de_calques_rendue_n_est_JAMAIS_celle_du_schema(tmp_path):
    """`DEFAULTS.back_layers` est le MÊME objet que celui remis au registre du
    CORE (`state: DEFAULTS`). Rendu tel quel, un `push` d'utilisateur écrirait
    dans le SCHÉMA — tous les jeux ouverts ensuite naîtraient avec le calque
    du précédent. La branche rend toujours un tableau NEUF, d'objets NEUFS."""
    res = _banc_verso_st(tmp_path, [{"nom": "defaut", "frame": {}}])
    assert res["defaut"]["ok"], res["defaut"].get("err")
    assert res["defaut"]["back_layers"] == []
    assert res["defaut"]["alias"] is False, \
        "st() rend le tableau du schéma : un réglage de carte écrit dans " \
        "DEFAULTS"


# ── 17.3 LA ROUTE D'IMAGES DE P2 — le quintette de durcissement de la 3b ─────
#
# P2 ne peut PAS importer la route de P3 (règle 8, écrite en tête de frame.py :
# « jamais d'un voisin »). Elle a donc LA SIENNE — et avec elle les cinq
# leçons payées en 3b-T2, rejouées ici sur la porte neuve :
#   1. la RÉSERVATION exclusive (O_CREAT|O_EXCL) — six imports simultanés font
#      six fichiers, pas un ;
#   2. la BOMBE DE PIXELS refusée sur l'EN-TÊTE, avant tout décodage ;
#   3. la LISTE BLANCHE AVANT le disque, dans la fonction qui COMPOSE le
#      chemin — pas seulement chez son appelant ;
#   4. le compteur MAX+1 : les trous d'une suppression manuelle ne sont pas
#      repris (un `img_2.png` réécrit changerait le dos d'une autre carte) ;
#   5. le PLAFOND, dit AVANT avec son arithmétique.

def _post_verso(did: str, data: bytes):
    return _api("POST", f"/api/cards/{did}/frame/image", content=data,
                headers={"Content-Type": "application/octet-stream"})


def _frame_dir(did: str) -> pathlib.Path:
    return CT.deck_dir(did) / "frame"


def _png_verso(w: int, h: int, couleur=(200, 40, 90)) -> bytes:
    import io as _io
    from PIL import Image
    buf = _io.BytesIO()
    Image.new("RGB", (int(w), int(h)), couleur).save(buf, format="PNG")
    return buf.getvalue()


def _bombe_png(w: int, h: int) -> bytes:
    """Un PNG VALIDE et minuscule qui DÉCLARE `w` x `h` (la même arme que
    test_cards_type.py, sur l'autre porte)."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    co = zlib.compressobj(1)
    ligne = b"\x00" * (w + 1)
    morceaux = [co.compress(ligne) for _ in range(h)]
    morceaux.append(co.flush())
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", b"".join(morceaux)) + chunk(b"IEND", b""))


def _api_ensemble(appels):
    """N requêtes lancées ENSEMBLE : `asyncio.gather` les entrelace vraiment,
    et le travail disque part en `to_thread` — la course est JOUÉE."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=60.0) as c:
            return await asyncio.gather(
                *[c.request(m, p, **kw) for m, p, kw in appels],
                return_exceptions=True)
    return asyncio.run(go())


def test_la_route_du_verso_range_l_image_AVEC_LE_JEU():
    """Un dos personnalisé voyage avec son jeu : export, duplication,
    sauvegarde. L'image est donc rangée dans `decks/{did}/frame/`, jamais dans
    le navigateur — et la réponse rend le `src` EXACT que le document accepte
    (`img:img_N.png`), pas un chemin à recomposer à l'écran."""
    did = _deck()
    r = _post_verso(did, _png_verso(40, 30))
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["file"] == "img_1.png" and d["src"] == "img:img_1.png", d
    assert d["px"] == [40, 30] and d["max"] == BACK_IMAGES_MAX_SPEC, d
    assert (_frame_dir(did) / "img_1.png").is_file(), \
        sorted(p.name for p in _frame_dir(did).iterdir())
    # le `src` servi TRAVERSE la normalisation du document : une source servie
    # que `st()`/`back_image_of` jetterait serait un piège.
    assert FR.back_image_of(d["src"]) == d["src"]
    # ... et il se relit par la route de lecture, avec un cache IMMUABLE (le
    # compteur garantit qu'`img_1.png` ne change jamais de contenu).
    g = _api("GET", f"/api/cards/{did}/frame/image/img_1.png")
    assert g.status_code == 200 and g.headers["content-type"] == "image/png"
    assert "immutable" in g.headers.get("cache-control", ""), g.headers
    assert g.content == (_frame_dir(did) / "img_1.png").read_bytes()


def test_six_imports_SIMULTANES_de_verso_font_six_fichiers():
    """LA COURSE, REJOUÉE sur la porte neuve. Sans réservation exclusive, six
    imports lisent le même « prochain numéro », écrivent le même temporaire et
    se le reprennent : un fichier, quatre clients convaincus d'avoir écrit
    `img_1.png`, et des 500 sur une pièce qui n'en fait jamais."""
    did = _deck()
    n = 6
    corps = [_png_verso(8 + i, 5 + i) for i in range(n)]
    reps = _api_ensemble([("POST", f"/api/cards/{did}/frame/image",
                           {"content": c,
                            "headers": {"Content-Type": "application/octet-stream"}})
                          for c in corps])
    for r in reps:
        assert not isinstance(r, BaseException), repr(r)
        assert r.status_code == 200, (r.status_code, r.text[:300])
    noms = sorted(r.json()["file"] for r in reps)
    assert len(set(noms)) == n, f"deux imports ont reçu le même nom : {noms}"
    sur_disque = sorted(p.name for p in _frame_dir(did).glob("img_*.png"))
    assert sur_disque == noms, (sur_disque, noms)
    from PIL import Image
    tailles = set()
    for nom in sur_disque:
        with Image.open(_frame_dir(did) / nom) as im:
            tailles.add(im.size)
    assert tailles == {(8 + i, 5 + i) for i in range(n)}, tailles
    assert not list(_frame_dir(did).glob("*.tmp")), \
        sorted(p.name for p in _frame_dir(did).iterdir())
    # la réservation et le temporaire unique, épinglés dans la source : le
    # remède est MÉCANIQUE, pas une coïncidence d'ordonnancement.
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    i = py.index("def _store_back_image(")
    corps_fn = py[i:py.index("\ndef ", i + 10)]
    assert "O_EXCL" in corps_fn, "le numéro n'est pas RÉSERVÉ (création exclusive)"
    assert "uuid" in corps_fn, "le temporaire n'a rien qui le distingue"


def test_une_BOMBE_DE_PIXELS_est_refusee_par_la_porte_du_verso():
    """Le corps est pesé (64 Mo), la TRAME non — et c'est la trame qui coûte :
    un demi-mégaoctet peut déclarer 12000 x 12000, soit 144 millions de pixels
    et un demi-gigaoctet de tampon PAR REQUÊTE. Le refus se prend sur les
    dimensions DÉCLARÉES, lues dans l'en-tête, AVANT tout décodage."""
    from PIL import Image
    import io as _io
    did = _deck()
    bombe = _bombe_png(12000, 12000)
    assert len(bombe) < 1_000_000, len(bombe)
    with Image.open(_io.BytesIO(bombe)) as im:
        assert im.size == (12000, 12000)
    assert FR.IMG_MAX_PIXELS == 32 * 1024 * 1024
    r = _post_verso(did, bombe)
    assert r.status_code == 413, (r.status_code, r.text[:200])
    detail = r.json()["detail"]
    assert "12000" in detail and "pixel" in detail.lower(), detail
    assert not list(_frame_dir(did).glob("img_*.png")), "la bombe a été écrite"
    assert _post_verso(did, _png_verso(40, 30)).status_code == 200
    # L'ORDRE, ÉPINGLÉ : après `img.load()` le tampon est déjà alloué.
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    i = py.index("def _decode_bounded(")
    corps = py[i:py.index("\ndef ", i + 10)]
    assert corps.index("IMG_MAX_PIXELS") < corps.index("img.load()"), \
        "les dimensions sont contrôlées APRÈS le décodage"
    # le plafond de POIDS est celui des pièces voisines, au même chiffre
    from app.services.cards import type as TY
    assert FR.IMG_MAX_BYTES == TY.IMG_MAX_BYTES
    assert FR.IMG_MAX_PIXELS == TY.IMG_MAX_PIXELS
    assert FR.MAX_IMPORT_PX == TY.MAX_IMPORT_PX == 4096
    # ... et l'écran RÉDUIT au même chiffre avant d'envoyer (recopié, jamais
    # importé : règle 8 — le test de P3 épingle déjà les quatre autres)
    assert "const MAX_IMPORT_PX = 4096;" in _js()
    vide = _api("POST", f"/api/cards/{did}/frame/image", content=b"")
    assert vide.status_code == 400, vide.text[:200]


def test_le_lecteur_d_image_de_verso_porte_SA_PROPRE_liste_blanche():
    """Doctrine `deck_dir` : motif PUIS confinement, et le second garde-fou vit
    DANS la fonction qui COMPOSE le chemin. Le dossier `decks/{did}/frame/`
    n'a aujourd'hui que des `img_N.png` — rien ne garantit qu'il n'aura pas
    d'état interne demain, et cette route ne doit pas s'élargir avec lui."""
    did = _deck()
    assert _post_verso(did, _png_verso(8, 5)).status_code == 200
    assert FR._read_back_image(did, "img_1.png") is not None
    for nom in ("../meta.json", "..", "job.json", "img_1.PNG", "",
                "img_1.png\n", "img_1.png ", "deck.json", "img_1.png/../x"):
        assert FR._read_back_image(did, nom) is None, nom
    assert FR._read_back_image("pas_un_deck", "img_1.png") is None
    # ... et la ROUTE refuse AVANT de composer quoi que ce soit
    for nom in ("..%2Fmeta.json", "deck.json", "img_1.PNG"):
        r = _api("GET", f"/api/cards/{did}/frame/image/{nom}")
        assert r.status_code in (400, 404), (nom, r.status_code)
        assert r.status_code != 500, nom
    manquant = _api("GET", f"/api/cards/{did}/frame/image/img_7.png")
    assert manquant.status_code == 404, manquant.status_code


def test_le_compteur_d_images_de_verso_GARDE_ses_trous():
    """MAX + 1, jamais « le premier libre ». Un `img_2.png` supprimé à la main
    puis RÉATTRIBUÉ ferait changer de dos toutes les cartes dont le document
    pointe encore `img:img_2.png` — un fichier différent sous un nom
    identique, et pas une ligne pour le dire."""
    did = _deck()
    for _ in range(3):
        assert _post_verso(did, _png_verso(9, 9)).status_code == 200
    (_frame_dir(did) / "img_2.png").unlink()
    r = _post_verso(did, _png_verso(11, 11))
    assert r.status_code == 200, r.text[:200]
    assert r.json()["file"] == "img_4.png", \
        f"le trou a été repris : {r.json()['file']}"
    assert sorted(p.name for p in _frame_dir(did).glob("img_*.png")) == \
        ["img_1.png", "img_3.png", "img_4.png"]
    # le compte RENDU est celui du disque, pas celui de la session
    assert r.json()["n"] == 3, r.json()


def test_le_plafond_de_HUIT_images_de_verso_est_tenu_et_NOMME():
    """Huit images de verso par jeu (plan 3c, décision 5). Le refus NOMME le
    plafond et le geste à faire — un 409 muet enverrait chercher la panne du
    côté du réseau."""
    did = _deck()
    for i in range(BACK_IMAGES_MAX_SPEC):
        assert _post_verso(did, _png_verso(6, 6)).status_code == 200, i
    r = _post_verso(did, _png_verso(6, 6))
    assert r.status_code == 409, (r.status_code, r.text[:200])
    detail = r.json()["detail"]
    assert str(BACK_IMAGES_MAX_SPEC) in detail, detail
    assert "verso" in detail.lower() or "dos" in detail.lower(), detail
    assert len(list(_frame_dir(did).glob("img_*.png"))) == \
        BACK_IMAGES_MAX_SPEC, "la neuvième a été écrite"
    # et le plafond est RECOMPTÉ après la réservation : deux imports partis
    # ensemble sur un jeu plein ne peuvent pas écrire la neuvième à eux deux.
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    i = py.index("def _store_back_image(")
    corps = py[i:py.index("\ndef ", i + 10)]
    assert corps.count("BACK_IMAGES_MAX") >= 3, \
        "le plafond n'est pas recompté APRÈS la réservation du numéro"


def test_la_route_du_verso_n_importe_RIEN_de_sa_voisine():
    """Règle 8, écrite en tête de `frame.py` : « Aucun autre module ne
    l'importe, et il n'importe le routeur d'aucun autre ». La route d'images
    de P2 est une JUMELLE de celle de P3, pas un appel à elle."""
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    for interdit in ("from .type import", "from . import type",
                     "from .face import", "from . import face",
                     "import type as", "cards.type"):
        assert interdit not in py, f"frame.py importe une voisine : {interdit}"


# ── 17.4 LE PEINTRE DU VERSO — des PIXELS, pas des intentions ───────────────
#
# Le rastériseur de la section 15 compte des CELLULES ; il ne sait rien des
# couleurs (`drawImage` y est un no-op). Or tout ce que cette tâche promet est
# une égalité de COULEUR : « l'image couvre la coupe », « permuter deux calques
# change le résultat », « le multiply cuit vaut le multiply du compositeur ».
# On écrit donc une VRAIE toile RGBA — 4 octets par pixel, la formule de
# composition du canvas — et on y fait tourner le peintre livré tel quel.

BANC_VERSO = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));

/* les modes de fusion VUS par la toile — c'est la mesure de « le peintre ne
   demande jamais au compositeur autre chose que source-over ». */
const MODES = {};
const TEXTES = [];

function couleur(s) {
  let m = /^#([0-9a-f]{6})$/i.exec(String(s));
  if (m) { const n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 255]; }
  m = /^#([0-9a-f]{3})$/i.exec(String(s));
  if (m) { const t = m[1];
    return [parseInt(t[0] + t[0], 16), parseInt(t[1] + t[1], 16),
      parseInt(t[2] + t[2], 16), 255]; }
  m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/
    .exec(String(s));
  if (m) return [+m[1], +m[2], +m[3],
    Math.round((m[4] === undefined ? 1 : +m[4]) * 255)];
  return [0, 0, 0, 255];
}
/* la composition du canvas, ecrite une fois : source-over et multiply, avec
   le fond qui compte pour ce qu'il PESE (sur un fond transparent tout mode
   separable retombe sur la source — formule de composition PDF/Canvas). */
function pose(d, o, src, op, ga) {
  MODES[op] = (MODES[op] || 0) + 1;
  const sa = (src[3] / 255) * ga, da = d[o + 3] / 255;
  const a = sa + da * (1 - sa);
  for (let k = 0; k < 3; k++) {
    const Cs = src[k] / 255, Cb = d[o + k] / 255;
    const B = (op === "multiply") ? Cs * Cb : Cs;
    const eff = B * da + Cs * (1 - da);
    d[o + k] = a ? Math.round((eff * sa + Cb * da * (1 - sa)) / a * 255) : 0;
  }
  d[o + 3] = Math.round(a * 255);
}
function Ctx(cv) {
  this.cv = cv; this.fillStyle = "#000000"; this.globalAlpha = 1;
  this.globalCompositeOperation = "source-over";
  this.font = ""; this.textAlign = ""; this.textBaseline = "";
  this.stk = [];
}
Ctx.prototype.save = function () {
  this.stk.push([this.fillStyle, this.globalAlpha,
    this.globalCompositeOperation]);
};
Ctx.prototype.restore = function () {
  const s = this.stk.pop();
  if (s) { this.fillStyle = s[0]; this.globalAlpha = s[1];
    this.globalCompositeOperation = s[2]; }
};
Ctx.prototype.beginPath = function () {};
Ctx.prototype.rect = function () {};
Ctx.prototype.clip = function () {};
Ctx.prototype.fillRect = function (x, y, w, h) {
  const src = couleur(this.fillStyle), d = this.cv.d;
  const W = this.cv.width, H = this.cv.height;
  const x0 = Math.max(0, Math.round(x)), x1 = Math.min(W, Math.round(x + w));
  const y0 = Math.max(0, Math.round(y)), y1 = Math.min(H, Math.round(y + h));
  for (let j = y0; j < y1; j++)
    for (let i = x0; i < x1; i++)
      pose(d, (j * W + i) * 4, src, this.globalCompositeOperation,
        this.globalAlpha);
};
/* echantillonnage au PLUS PROCHE : le banc juge des aplats et des positions,
   jamais la qualite d'un reechantillonnage (que le navigateur seul fait). */
Ctx.prototype.drawImage = function (img, dx, dy, dw, dh) {
  if (dw === undefined) { dx = dx || 0; dy = dy || 0;
    dw = img.width; dh = img.height; }
  const d = this.cv.d, W = this.cv.width, H = this.cv.height;
  const x0 = Math.max(0, Math.floor(dx)), x1 = Math.min(W, Math.ceil(dx + dw));
  const y0 = Math.max(0, Math.floor(dy)), y1 = Math.min(H, Math.ceil(dy + dh));
  for (let j = y0; j < y1; j++) {
    let sy = Math.floor((j + 0.5 - dy) / dh * img.height);
    sy = Math.min(img.height - 1, Math.max(0, sy));
    for (let i = x0; i < x1; i++) {
      let sx = Math.floor((i + 0.5 - dx) / dw * img.width);
      sx = Math.min(img.width - 1, Math.max(0, sx));
      const s = (sy * img.width + sx) * 4;
      pose(d, (j * W + i) * 4,
        [img.d[s], img.d[s + 1], img.d[s + 2], img.d[s + 3]],
        this.globalCompositeOperation, this.globalAlpha);
    }
  }
};
Ctx.prototype.getImageData = function (x, y, w, h) {
  const W = this.cv.width, out = new Uint8ClampedArray(w * h * 4);
  for (let j = 0; j < h; j++)
    for (let i = 0; i < w; i++) {
      const s = ((y + j) * W + (x + i)) * 4, o = (j * w + i) * 4;
      out[o] = this.cv.d[s]; out[o + 1] = this.cv.d[s + 1];
      out[o + 2] = this.cv.d[s + 2]; out[o + 3] = this.cv.d[s + 3];
    }
  return { width: w, height: h, data: out };
};
Ctx.prototype.putImageData = function (img, x, y) {
  const W = this.cv.width;
  for (let j = 0; j < img.height; j++)
    for (let i = 0; i < img.width; i++) {
      const o = (j * img.width + i) * 4, s = ((y + j) * W + (x + i)) * 4;
      this.cv.d[s] = img.data[o]; this.cv.d[s + 1] = img.data[o + 1];
      this.cv.d[s + 2] = img.data[o + 2]; this.cv.d[s + 3] = img.data[o + 3];
    }
};
Ctx.prototype.fillText = function (t) { TEXTES.push(String(t)); };
Ctx.prototype.measureText = function (t) { return { width: String(t).length * 6 }; };
Ctx.prototype.createLinearGradient = function () {
  return { addColorStop: function () {} };
};
Ctx.prototype.createRadialGradient = Ctx.prototype.createLinearGradient;
function mkCanvas(w, h) {
  const cv = { _w: 0, _h: 0, d: new Uint8ClampedArray(0) };
  const alloc = () => { cv.d = new Uint8ClampedArray(cv._w * cv._h * 4); };
  Object.defineProperty(cv, "width", { get: () => cv._w,
    set: (v) => { cv._w = v | 0; alloc(); } });
  Object.defineProperty(cv, "height", { get: () => cv._h,
    set: (v) => { cv._h = v | 0; alloc(); } });
  cv.getContext = () => new Ctx(cv);
  cv.width = w; cv.height = h;
  return cv;
}
globalThis.document = { createElement: () => mkCanvas(0, 0) };

const mod = new Function("return (function(){ " + CODE
  + "\nreturn { st: st, model: model, paintBackCustom: paintBackCustom,"
  + " backCover: backCover, backFiles: backFiles, backFile: backFile };\n})();")();

function image(spec) {
  const w = spec.w, h = spec.h;
  const im = { width: w, height: h, d: new Uint8ClampedArray(w * h * 4) };
  for (let j = 0; j < h; j++)
    for (let i = 0; i < w; i++) {
      const c = spec.rgba;
      const o = (j * w + i) * 4;
      im.d[o] = c[0]; im.d[o + 1] = c[1]; im.d[o + 2] = c[2]; im.d[o + 3] = c[3];
    }
  return im;
}

const out = [];
for (const c of CAS.cas) {
  const dpi = c.g.dpi;
  const g = Object.assign({}, c.g, { mm2px: (v) => v / 25.4 * dpi });
  for (const k of Object.keys(MODES)) delete MODES[k];
  TEXTES.length = 0;
  try {
    const f = mod.st({ frame: c.frame });
    const m = mod.model(g, f);
    const IM = {};
    for (const nom of Object.keys(c.imgs || {})) IM[nom] = image(c.imgs[nom]);
    const get = (file) => (IM[file]
      ? { img: IM[file], ok: true, file: file }
      : { img: null, ok: false, file: file });
    const cv = mkCanvas(m.W, m.H);
    const ctx = cv.getContext("2d");
    /* LA BASE : `paintBack` remplit la toile de la matiere de bande AVANT
       d'appeler le verso personnalise. Le banc pose la meme chose — et peut
       la rendre TRANSPARENTE pour mesurer ce que devient un multiply quand
       le fond ne pese rien. */
    ctx.fillStyle = c.base;
    ctx.fillRect(0, 0, m.W, m.H);
    const modes_base = Object.keys(MODES).slice();
    for (const k of Object.keys(MODES)) delete MODES[k];
    mod.paintBackCustom(ctx, m, f, get);
    const px = (x, y) => {
      const o = ((y | 0) * m.W + (x | 0)) * 4;
      return [cv.d[o], cv.d[o + 1], cv.d[o + 2], cv.d[o + 3]];
    };
    const T = m.trim;
    const points = {
      toile_hg: px(2, 2),
      toile_bd: px(m.W - 3, m.H - 3),
      coupe_hg: px(Math.round(T.x) + 2, Math.round(T.y) + 2),
      coupe_bd: px(Math.round(T.x + T.w) - 3, Math.round(T.y + T.h) - 3),
      centre: px(m.W >> 1, m.H >> 1),
      bord_bas: px(m.W >> 1, m.H - 2),
    };
    let a = 2166136261;
    for (let i = 0; i < cv.d.length; i++) {
      a ^= cv.d[i]; a = Math.imul(a, 16777619) >>> 0;
    }
    out.push({ nom: c.nom, ok: true, px: points,
      hash: ("0000000" + a.toString(16)).slice(-8),
      modes: Object.keys(MODES).sort(), modes_base: modes_base,
      textes: TEXTES.slice(),
      toile: [m.W, m.H], coupe: [T.x, T.y, T.w, T.h],
      couvre: mod.backCover(4, 4, m.W, m.H),
      fichiers: mod.backFiles(f) });
  } catch (e) {
    out.push({ nom: c.nom, ok: false, err: String((e && e.stack) || e) });
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_verso(tmp_path, cas: list, mutations=()) -> dict:
    """Fait tourner le VRAI peintre du verso sur une VRAIE toile RGBA."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du verso ne peut pas tourner")
    code = _verso_js_source()
    for avant, apres in mutations:
        assert avant in code, f"mutation introuvable : {avant!r}"
        code = code.replace(avant, apres)
    js = tmp_path / "verso.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_verso.mjs"
    banc.write_text(BANC_VERSO, encoding="utf-8")
    conf = tmp_path / "cas_verso.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x for x in json.loads(r.stdout)}


# des couleurs CHOISIES pour que le produit ne soit ambigu sur aucun canal
BASE_RGBA = [90, 160, 32, 255]          # la bande, opaque
BASE_CSS = "#5aa020"
CALQUE_A = [128, 64, 200, 255]
CALQUE_B = [240, 200, 80, 255]
IMG_FOND = [20, 30, 210, 255]


def _cas_verso(nom, back_image="", calques=(), imgs=None, base=BASE_CSS,
               fmt="poker_eu", **frame):
    fr = {"family": "arcane", "rarity": "rare", "back": "custom",
          "back_image": back_image, "back_layers": list(calques)}
    fr.update(frame)
    fichiers = {}
    for f, spec in (imgs or {}).items():
        fichiers[f] = {"w": spec[0], "h": spec[1], "rgba": spec[2]}
    return {"nom": nom, "g": _geom_js(fmt, 3), "frame": fr, "base": base,
            "imgs": fichiers}


def _r(x: float) -> int:
    """L'arrondi de `Math.round` : DEMI-HAUT. `round()` de Python arrondit au
    PAIR (174,5 -> 174), et deux oracles qui ne s'accordent pas sur le dernier
    bit feraient rougir un peintre juste."""
    return int(math.floor(x + 0.5))


def _sur(cs, cb, sa):
    """Un pixel de source posé en `source-over` sur un fond OPAQUE, dans le
    MÊME ORDRE D'OPÉRATIONS que le compositeur (banc et canvas).

    UN ORACLE QUI SIMPLIFIE L'ARITHMÉTIQUE TOMBE SUR LE DERNIER BIT. Écrit
    « (a + b) / 2 », il rend 28,5 -> 29 ; le compositeur, lui, passe par
    `25/255*0,5 + 32/255*0,5`, qui vaut 0,11176470588235294, donc
    28,499999999999996, donc 28. Deux oracles qui ne s'accordent pas sur le
    dernier bit font rougir un peintre juste. Mesuré, et écrit ici."""
    return _r((cs / 255.0 * sa + cb / 255.0 * (1 - sa)) * 255)


def _mult(s, b, ab=1.0):
    """La formule que le peintre CUIT dans les pixels du calque : le mélange
    `multiply` du canvas, pondéré par l'opacité du FOND (sur un fond
    transparent, un mode séparable retombe sur la source)."""
    return _r(s * (1 - ab) + s * b / 255.0 * ab)


def test_l_image_du_verso_couvre_la_coupe_ET_LE_FOND_PERDU(tmp_path):
    """« Cover », depuis le bord de TOILE — pas depuis la coupe. La découpe
    vient après l'impression : une image calée sur la seule rogne laisserait
    la matière de bande dans les 3 mm de fond perdu, et un massicot décalé
    d'un millimètre poserait ce liseré sur le bord de la carte livrée. Les
    quatre coins de la TOILE portent donc l'image."""
    r = _banc_verso(tmp_path, [
        _cas_verso("plein", back_image="img:img_1.png",
                   imgs={"img_1.png": (4, 4, IMG_FOND)}),
        _cas_verso("sans", back_image=""),
    ])
    p = r["plein"]
    assert p["ok"], p.get("err")
    for coin in ("toile_hg", "toile_bd", "coupe_hg", "coupe_bd", "centre",
                 "bord_bas"):
        assert p["px"][coin] == IMG_FOND, \
            f"{coin} porte {p['px'][coin]} au lieu de l'image {IMG_FOND}"
    # le témoin : sans image, la base reste partout (le banc discrimine)
    s = r["sans"]
    assert s["ok"], s.get("err")
    assert s["px"]["centre"] == BASE_RGBA, s["px"]
    assert s["hash"] != p["hash"]
    # et le cadrage est un COVER : l'image déborde plutôt que de laisser un
    # bord — le côté court remplit exactement, le long dépasse.
    W, H = p["toile"]
    x, y, w, h = p["couvre"]
    assert w >= W - 1e-6 and h >= H - 1e-6, (x, y, w, h, W, H)
    assert abs(x + w / 2 - W / 2) < 1e-6 and abs(y + h / 2 - H / 2) < 1e-6, \
        "le cadrage n'est pas centré"


def test_l_ORDRE_des_calques_du_verso_est_PORTEUR(tmp_path):
    """Une pile ordonnée dont l'ordre ne changerait rien ne serait pas une
    pile. Deux calques permutés doivent donner deux images DIFFÉRENTES — et
    la mesure porte sur les pixels, pas sur la liste."""
    imgs = {"img_1.png": (4, 4, CALQUE_A), "img_2.png": (4, 4, CALQUE_B)}
    a = {"src": "img:img_1.png", "opacity": 0.5, "scale": 1, "blend": "normal"}
    b = {"src": "img:img_2.png", "opacity": 0.5, "scale": 1, "blend": "normal"}
    r = _banc_verso(tmp_path, [
        _cas_verso("ab", calques=[a, b], imgs=imgs),
        _cas_verso("ba", calques=[b, a], imgs=imgs),
    ])
    assert r["ab"]["ok"] and r["ba"]["ok"], (r["ab"].get("err"),
                                             r["ba"].get("err"))
    assert r["ab"]["hash"] != r["ba"]["hash"], \
        "permuter deux calques ne change RIEN : l'ordre n'est pas porteur"
    # ... et le pixel du dessus est celui du DERNIER calque, à 50 %
    def demi(dessus, dessous):
        return [_sur(dessus[k], _sur(dessous[k], BASE_RGBA[k], 0.5), 0.5)
                for k in range(3)]
    assert r["ab"]["px"]["centre"][:3] == demi(CALQUE_B, CALQUE_A), \
        r["ab"]["px"]["centre"]
    assert r["ba"]["px"]["centre"][:3] == demi(CALQUE_A, CALQUE_B), \
        r["ba"]["px"]["centre"]


def test_l_opacite_et_l_echelle_d_un_calque_sont_CELLES_DU_REGLAGE(tmp_path):
    """Deux réglages, deux effets mesurables : l'opacité mélange, l'échelle
    RÉTRÉCIT autour du centre de la toile (un calque à 0,5 laisse voir ce
    qu'il y a dessous sur tout le pourtour)."""
    imgs = {"img_1.png": (4, 4, CALQUE_A)}
    r = _banc_verso(tmp_path, [
        _cas_verso("pleine", calques=[{"src": "img:img_1.png", "opacity": 1,
                                       "scale": 1, "blend": "normal"}],
                   imgs=imgs),
        _cas_verso("quart", calques=[{"src": "img:img_1.png", "opacity": 0.25,
                                      "scale": 1, "blend": "normal"}],
                   imgs=imgs),
        _cas_verso("nulle", calques=[{"src": "img:img_1.png", "opacity": 0,
                                      "scale": 1, "blend": "normal"}],
                   imgs=imgs),
        _cas_verso("demi_echelle", calques=[{"src": "img:img_1.png",
                                             "opacity": 1, "scale": 0.5,
                                             "blend": "normal"}], imgs=imgs),
    ])
    for v in r.values():
        assert v["ok"], f"{v['nom']} : {v.get('err')}"
    assert r["pleine"]["px"]["centre"] == CALQUE_A, r["pleine"]["px"]["centre"]
    attendu = [_sur(CALQUE_A[k], BASE_RGBA[k], 0.25) for k in range(3)]
    assert r["quart"]["px"]["centre"][:3] == attendu, \
        (r["quart"]["px"]["centre"], attendu)
    assert r["nulle"]["px"]["centre"] == BASE_RGBA, \
        "un calque à opacité nulle a quand même peint"
    d = r["demi_echelle"]
    assert d["px"]["centre"] == CALQUE_A, d["px"]["centre"]
    assert d["px"]["toile_hg"] == BASE_RGBA, \
        f"à l'échelle 0,5 le calque couvre encore le coin : {d['px']['toile_hg']}"


def test_le_MULTIPLY_est_CUIT_dans_les_pixels_du_calque(tmp_path):
    """LE test de la tâche. Le mélange `multiply` est calculé DANS les pixels
    du calque — produit canal par canal contre le verso déjà peint — puis
    posé en `source-over`. Deux choses sont mesurées ensemble, et il faut les
    deux : le RÉSULTAT est bien celui d'un multiply, et le compositeur n'a
    JAMAIS reçu autre chose que `source-over`."""
    imgs = {"img_1.png": (4, 4, CALQUE_A)}
    r = _banc_verso(tmp_path, [
        _cas_verso("mult", calques=[{"src": "img:img_1.png", "opacity": 1,
                                     "scale": 1, "blend": "multiply"}],
                   imgs=imgs),
        _cas_verso("norm", calques=[{"src": "img:img_1.png", "opacity": 1,
                                     "scale": 1, "blend": "normal"}],
                   imgs=imgs),
        _cas_verso("mult_demi", calques=[{"src": "img:img_1.png",
                                          "opacity": 0.5, "scale": 1,
                                          "blend": "multiply"}], imgs=imgs),
    ])
    for v in r.values():
        assert v["ok"], f"{v['nom']} : {v.get('err')}"
    attendu = [_mult(CALQUE_A[k], BASE_RGBA[k]) for k in range(3)]
    assert r["mult"]["px"]["centre"][:3] == attendu, \
        (r["mult"]["px"]["centre"], attendu)
    assert r["mult"]["px"]["centre"] != r["norm"]["px"]["centre"], \
        "multiply et normal donnent le même pixel : rien n'est multiplié"
    # l'opacité porte sur le RÉSULTAT cuit, comme sur un calque normal
    demi = [_sur(attendu[k], BASE_RGBA[k], 0.5) for k in range(3)]
    assert r["mult_demi"]["px"]["centre"][:3] == demi, \
        (r["mult_demi"]["px"]["centre"], demi)
    # ... ET AUCUN mode de fusion vivant n'a atteint la toile
    for nom in ("mult", "norm", "mult_demi"):
        assert r[nom]["modes"] == ["source-over"], \
            f"{nom} : le peintre a demandé {r[nom]['modes']} au compositeur"


def test_un_MULTIPLY_sur_fond_TRANSPARENT_ne_noircit_pas_le_calque(tmp_path):
    """Le piège du produit brut. Multiplier par un fond ABSENT donne du NOIR
    (tout x 0 = 0) : un verso rendu sur toile transparente — le rendu par
    couches de P9 le fait à chaque appel — sortirait tout noir. La cuisson
    pondère donc par l'opacité du fond, exactement comme le compositeur : là
    où rien ne pèse, le calque garde ses couleurs."""
    imgs = {"img_1.png": (4, 4, CALQUE_A)}
    calques = [{"src": "img:img_1.png", "opacity": 1, "scale": 1,
                "blend": "multiply"}]
    r = _banc_verso(tmp_path, [
        _cas_verso("transparent", calques=calques, imgs=imgs,
                   base="rgba(0,0,0,0)"),
        _cas_verso("opaque", calques=calques, imgs=imgs),
    ])
    for v in r.values():
        assert v["ok"], f"{v['nom']} : {v.get('err')}"
    assert r["transparent"]["px"]["centre"] == CALQUE_A, \
        f"sur fond transparent le calque sort {r['transparent']['px']['centre']} " \
        f"au lieu de {CALQUE_A} (produit par un fond nul = noir)"
    assert r["opaque"]["px"]["centre"] != CALQUE_A


def test_une_image_de_verso_ABSENTE_donne_un_DAMIER_NOMME(tmp_path):
    """Le patron de P3 (3b-T2), rejoué : un fichier NOMMÉ qui n'arrive pas est
    un ÉTAT de la carte, pas une panne du painter. Un trou transparent
    laisserait partir une carte incomplète sans un mot ; un damier et le nom
    du fichier sont impossibles à ne pas voir sur une épreuve.

    Une source VIDE, elle, ne salit rien : c'est un dos qu'on vient de choisir
    et dont l'image n'est pas encore déposée — le panneau le montre déjà."""
    r = _banc_verso(tmp_path, [
        _cas_verso("manquante", back_image="img:img_9.png"),
        _cas_verso("vide", back_image=""),
        _cas_verso("calque_manquant",
                   calques=[{"src": "img:img_5.png", "opacity": 1,
                             "scale": 1, "blend": "normal"}]),
    ])
    m = r["manquante"]
    assert m["ok"], m.get("err")
    assert "img_9.png" in m["textes"], m["textes"]
    assert m["px"]["centre"] != BASE_RGBA, "aucun damier n'a été peint"
    v = r["vide"]
    assert v["ok"], v.get("err")
    assert v["textes"] == [], v["textes"]
    assert v["px"]["centre"] == BASE_RGBA, \
        "une source VIDE a sali la carte d'un damier"
    c = r["calque_manquant"]
    assert c["ok"], c.get("err")
    assert "img_5.png" in c["textes"], c["textes"]


def test_le_verso_custom_ne_demande_JAMAIS_qu_un_source_over(tmp_path):
    """L'invariant §4.2, mesuré sur la toile plutôt que lu dans la source :
    quels que soient les modes déclarés dans la pile, le compositeur ne reçoit
    que `source-over`. C'est ce qui garde la couche « cadre » EMPILABLE."""
    imgs = {"img_1.png": (4, 4, CALQUE_A), "img_2.png": (4, 4, CALQUE_B)}
    r = _banc_verso(tmp_path, [_cas_verso(
        "pile", back_image="img:img_1.png", imgs=imgs,
        calques=[{"src": "img:img_2.png", "opacity": 0.7, "scale": 2,
                  "blend": "multiply"},
                 {"src": "img:img_1.png", "opacity": 0.4, "scale": 0.6,
                  "blend": "normal"},
                 {"src": "img:img_2.png", "opacity": 1, "scale": 1,
                  "blend": "multiply"}])])
    assert r["pile"]["ok"], r["pile"].get("err")
    assert r["pile"]["modes"] == ["source-over"], r["pile"]["modes"]


def test_le_verso_custom_passe_par_SON_PEINTRE_et_garde_la_matiere(tmp_path):
    """La couture, lue dans `paintBack` : la branche `custom` appelle le
    peintre du verso personnalisé À LA PLACE d'un motif de catalogue, AVANT
    `matter()` — le carton est le même des deux côtés de la carte, sa matière
    passe donc sur l'illustration du dos comme elle passe sur les motifs. Et
    le médaillon central, qui est un MEUBLE du catalogue, ne vient pas
    s'écraser sur l'image de l'utilisateur."""
    corps = _js_fn(_js(), "paintBack")
    assert 'kind === "custom"' in corps, \
        "paintBack n'a pas de branche pour le dos personnalisé"
    i = corps.index("paintBackCustom(")
    j = corps.index("matter(ctx, m, f")
    assert i < j, "le verso personnalisé est peint APRÈS la matière"
    # le médaillon est SOUS garde : sinon il tombe au milieu de l'image
    k = corps.index("medaillon")
    assert k > j, "le médaillon se peint avant la matière ?"
    assert re.search(r'kind\s*!==\s*"custom"', corps[k:k + 500]), \
        "le médaillon du catalogue se peint sur le verso personnalisé"


# ── 17.5 LA PREUVE D'EMPILEMENT SUR UN VERSO À MULTIPLY (§4.2) ──────────────
#
# Le Sceau (T1) a fait basculer la couche « cadre » en EMPREINTE : son overlay
# vivant, posé là où sa base n'est pas opaque, rend le résultat dépendant de ce
# qu'il y a dessous. L'empreinte est exacte, mais c'est une couche CUITE — on
# ne peut plus la déplacer dans un logiciel de calques.
#
# Le verso personnalisé pose le cas inverse, et c'est ce que la précomposition
# achète : un verso à `multiply` garde une couche ISOLÉE. Ce banc-ci fait
# tourner la VRAIE `layers()` de core.js avec, en z=40, le VRAI peintre du
# verso — pas un stub qui imiterait ce qu'on espère.

def _banc_empilement_verso(tmp_path, cas: dict, mutations=(), echec=False):
    """`_banc_empilement`, mais le peintre z=40 est le peintre livré du verso
    personnalisé, chargé depuis mod-frame.js."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'empilement ne peut pas tourner")
    src = CORE_JS.read_text(encoding="utf-8")
    code = "async " + _js_fn(src, "layers")
    js = tmp_path / "layers.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_empilement.mjs"
    banc.write_text(BANC_EMPILEMENT, encoding="utf-8")
    vcode = _verso_js_source()
    for avant, apres in mutations:
        assert avant in vcode, f"mutation introuvable : {avant!r}"
        vcode = vcode.replace(avant, apres)
    vjs = tmp_path / "verso_empilement.js"
    vjs.write_text(vcode, encoding="utf-8")
    conf = tmp_path / "cas_empilement_verso.json"
    conf.write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf), str(vjs)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    if echec:
        assert r.returncode != 0, \
            f"le banc a rendu un verdict au lieu de refuser : {r.stdout[:300]}"
        return r.stderr
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


CAS_VERSO_EMPILEMENT = {
    "op": "source-over",
    "face": "back",
    "verso": {
        "base": "#c08040",
        "img": {"w": 4, "h": 4, "rgba": [128, 64, 200, 255]},
        "f": {"back_image": "img:img_1.png", "back_layers": [
            {"src": "img:img_1.png", "opacity": 1, "scale": 1,
             "blend": "multiply"}]},
    },
}


def test_un_verso_custom_a_MULTIPLY_garde_sa_couche_ISOLEE(tmp_path):
    """§4.2, exécuté sur le verso. Un `multiply` PRÉCOMPOSÉ ne demande rien au
    compositeur : la couche « cadre » du rendu par couches reste ISOLÉE (une
    vraie couche, déplaçable) au lieu de basculer en empreinte comme le fait
    l'overlay du Sceau — et `stack_ok` tient.

    ET LA COUCHE PORTE VRAIMENT LES PIXELS DE L'IMAGE (§6.2ter, conséquences
    en aval : « l'export par couches livre le verso ») : ce n'est pas un
    rectangle vide qu'on déclarerait exact."""
    L = _banc_empilement_verso(tmp_path, CAS_VERSO_EMPILEMENT)
    assert L["face"] == "back", L["face"]
    modes = dict(L["modes"])
    assert modes["cadre"] == "isolee", \
        f"la couche du cadre est « {modes['cadre']} » : le multiply n'est " \
        f"pas précomposé"
    assert L["stack_ok"] is True, "la preuve d'empilement tombe sur le verso"
    # la couche EXPORTÉE porte le produit image x bande, pas du vide
    px = L["couche_cadre"]
    # le calque a multiply est pose SUR l'image de fond (elle-meme peinte par
    # ce peintre) : le pixel livre est donc l'image MULTIPLIEE PAR ELLE-MEME,
    # ce qui prouve d'un coup les deux — l'image est la, et le multiply a cuit.
    attendu = [_mult(128, 128), _mult(64, 64), _mult(200, 200)]
    assert px[3] == 255, f"la couche du cadre est transparente : {px}"
    assert px[:3] == attendu, (px, attendu)


def test_un_multiply_VIVANT_fait_REFUSER_le_banc_d_empilement(tmp_path):
    """LE CONTRÔLE, et il est dit pour ce qu'il est. Le mélangeur du banc ne
    connaît que `source-over` et `overlay` : un `multiply` demandé au
    compositeur le fait REFUSER de rendre un verdict (T1, ronde 2) plutôt que
    de le traiter en silence comme du source-over.

    Ce que ce contrôle prouve exactement : que le peintre livré ne passe PAS
    par là. Il ne prouve PAS qu'un multiply vivant donnerait d'autres pixels —
    le test suivant mesure qu'il donnerait les MÊMES."""
    err = _banc_empilement_verso(
        tmp_path, CAS_VERSO_EMPILEMENT, echec=True,
        mutations=[('ctx.drawImage(off, 0, 0);',
                    'ctx.globalCompositeOperation = "multiply";'
                    ' ctx.drawImage(off, 0, 0);')])
    assert "multiply" in err, err[-600:]
    assert "mode de fusion inconnu" in err, err[-600:]


MUT_BLEND_VIF = [(
    "      oc.putImageData(L, 0, 0);\n      ctx.save();\n"
    "      ctx.globalAlpha = op;\n      ctx.drawImage(off, 0, 0);",
    "      ctx.save();\n      ctx.globalAlpha = op;\n"
    "      ctx.globalCompositeOperation = \"multiply\";\n"
    "      ctx.drawImage(rec.img, b[0], b[1], b[2], b[3]);")]


def test_la_precomposition_ne_change_les_pixels_qu_a_UN_NIVEAU_PRES(tmp_path):
    """LA PHRASE, REMISE À LA MESURE — DEUX FOIS (leçon 3c-T3-F1 : une prose
    qui promet plus que les octets est une prose fausse, même quand le code
    est bon).

    Premier tour : il serait commode d'écrire « sans la précomposition, la
    preuve d'empilement tombe ». C'est FAUX — un `multiply` VIVANT rend les
    mêmes pixels, donc le même verdict §4.2. Ce que la précomposition achète
    est la SUITE D'OPÉRATIONS : la couche du cadre ne demande jamais autre
    chose que `source-over`.

    Second tour, la revue : « EXACTEMENT les mêmes octets » était faux à son
    tour, et le premier pin ne pouvait pas le voir — il ne faisait varier que
    la couleur, jamais l'ALPHA du calque. Or `_decode_bounded` garde la bande
    alpha PAR CHOIX (« sa transparence porte »), donc un calque semi-
    transparent est une entrée de premier rang. Mesuré : à alpha 64, un canal
    diffère d'UN NIVEAU. L'algèbre, elle, est exacte (re-dérivée à la main
    contre la formule W3C) ; l'écart est la QUANTIFICATION — la cuisson passe
    par `getImageData`/`putImageData`, donc par un aller-retour en entiers 8
    bits, là où le compositeur garde ses flottants jusqu'au bout.

    La phrase tenable est donc : mêmes octets **à un niveau près**, et
    EXACTEMENT les mêmes pour un calque opaque."""
    OPAQUE = [128, 64, 200, 255]
    TRANSLUCIDE = [128, 64, 200, 64]
    cas = [_cas_verso("opaque", back_image="img:img_1.png",
                      imgs={"img_1.png": (4, 4, OPAQUE)},
                      calques=[{"src": "img:img_1.png", "opacity": 0.6,
                                "scale": 1, "blend": "multiply"}]),
           _cas_verso("fond_nul", imgs={"img_1.png": (4, 4, OPAQUE)},
                      base="rgba(0,0,0,0)",
                      calques=[{"src": "img:img_1.png", "opacity": 1,
                                "scale": 1, "blend": "multiply"}]),
           _cas_verso("translucide", back_image="img:img_1.png",
                      imgs={"img_1.png": (4, 4, TRANSLUCIDE)},
                      calques=[{"src": "img:img_1.png", "opacity": 1,
                                "scale": 1, "blend": "multiply"}])]
    produit = _banc_verso(tmp_path, cas)
    vif = _banc_verso(tmp_path, cas, mutations=MUT_BLEND_VIF)
    for nom in produit:
        assert produit[nom]["ok"] and vif[nom]["ok"], nom
    # 1. CALQUE OPAQUE : égalité STRICTE, empreinte comprise
    for nom in ("opaque", "fond_nul"):
        assert produit[nom]["hash"] == vif[nom]["hash"], \
            f"{nom} : un calque OPAQUE doit donner les mêmes octets " \
            f"({produit[nom]['px']['centre']} vs {vif[nom]['px']['centre']})"
    # 2. CALQUE SEMI-TRANSPARENT : l'écart existe, et il est BORNÉ à 1 niveau
    ecart = 0
    for k in produit["translucide"]["px"]:
        for a, b in zip(produit["translucide"]["px"][k], vif["translucide"]["px"][k]):
            ecart = max(ecart, abs(a - b))
    assert ecart <= 1, \
        f"la cuisson s'écarte du compositeur de {ecart} niveaux : ce n'est " \
        f"plus la quantification, c'est l'algèbre — re-dériver la formule"
    # 3. LA SEULE différence qui compte, et c'est tout l'objet du mécanisme
    assert produit["opaque"]["modes"] == ["source-over"]
    assert "multiply" in vif["opaque"]["modes"], vif["opaque"]["modes"]


# ── 17.6 LE PANNEAU : importer, empiler, ordonner ───────────────────────────

def test_le_panneau_offre_l_import_et_la_LISTE_des_calques_du_verso():
    """Le dos « Personnalisé » découvre une zone d'import (dépôt / collage /
    fichier, patron `importFiles` de P1) et la liste des calques : ordre,
    opacité, échelle, fusion, suppression — le patron de la liste de P3."""
    src = _js()
    # l'import, ses trois gestes et la réduction AVANT l'envoi
    i = src.index("async function importBackImage(")
    corps = src[i:src.index("\n  function ", i)]
    assert "M.api.raw" in corps and '"POST", "image"' in corps, corps[:400]
    assert "IMPORTING" in corps, "aucune garde de vol sur l'import du verso"
    assert corps.index("IMPORTING") < corps.index("M.api.raw"), \
        "la garde est posée APRÈS l'envoi"
    assert "finally" in corps and "IMPORTING = false" in corps
    assert "MAX_IMPORT_PX" in src, "aucune réduction avant l'envoi"
    for geste in ("drop", "paste", "change"):
        assert 'addEventListener("' + geste in src, \
            f"le geste « {geste} » n'est pas câblé pour le verso"
    # la liste des calques et ses commandes
    for cmd in ("backLayerAdd", "backLayerMove", "backLayerDel",
                "backLayerSet"):
        assert cmd in src, f"la commande {cmd} manque à la liste des calques"
    assert "cf-frame-back" in src, "la zone d'import n'a pas d'id préfixé"
    # L'APERÇU RESTE CELUI QUI EXISTE (§6.2ter : « aperçu par le bouton
    # recto/verso existant »). Rien de neuf à construire, mais rien à casser
    # non plus : le bouton du CORE et le raccourci qui le conduit sont
    # épinglés ici parce que le verso personnalisé est la première raison
    # sérieuse de s'en servir.
    corps_v = _js_fn(src, "showBack")
    assert "#sideBtn" in corps_v and 'CF.side() !== "back"' in corps_v, corps_v
    assert '#sideBtn' in _js_fn(src, "onKey"), \
        "le raccourci qui montre le verso a disparu"


def test_l_ecran_DIT_l_etat_du_verso_personnalise():
    """Trois états à écrire, et le panneau les écrit : aucune image importée,
    la pile pleine, et ce qu'un modèle emporte (les réglages) ou non (les
    fichiers du jeu)."""
    src = _js()
    i = src.index("function backText(")
    corps = src[i:src.index("\n  function ", i)]
    assert "BACK_LAYERS_MAX" in corps, \
        "l'état du verso ne dit pas le plafond de la pile"
    assert "modèle" in corps, \
        "l'écran ne dit pas ce qu'un modèle emporte du verso"


def test_le_cache_d_images_du_verso_ne_peut_pas_DEBORDER_d_un_jeu_a_l_autre():
    """`img_1.png` existe dans TOUS les jeux : un cache d'images indexé par le
    seul nom de fichier serait un mélange garanti dès qu'on change de jeu.

    Ce qui l'empêche n'est pas dans cette pièce, et c'est pour ça qu'on
    l'épingle ICI plutôt que de l'affirmer : changer de jeu passe par
    `galGo()` du CORE, qui RECHARGE la page (`location.assign`, repli
    `location.reload`). Le cache meurt avec elle. Le jour où le CORE
    échangerait le document en place, ce test rougit — et c'est exactement
    l'endroit où il faut alors ajouter une clé de jeu."""
    core = CORE_JS.read_text(encoding="utf-8")
    corps = _js_fn(core, "galGo")
    assert "location.assign" in corps and "location.reload" in corps, corps
    # ... et la pièce charge bien SES images par SA route (règle 8)
    src = _js()
    i = src.index("function loadBackImg(")
    lb = src[i:src.index("\n  function ", i)]
    assert 'M.api.url("image/"' in lb, lb[:400]
    assert "encodeURIComponent" in lb, "le nom de fichier n'est pas encodé"


def test_le_painter_du_verso_ATTEND_ses_images_avant_de_peindre():
    """Le patron de P3 : sans l'attente, la première frame peint un damier à
    la place d'une image qui existe — et cette première frame EST le fichier
    livré quand l'export part tout de suite."""
    src = _js()
    i = src.index("painters: [")
    corps = src[i:src.index("state: DEFAULTS", i)]
    assert "await ensureBackImgs(" in corps, \
        "le painter ne charge pas les images du verso avant de peindre"
    assert "async fn(" in corps, "le painter n'est pas asynchrone"
    # l'attente est BORNÉE : le CORE laisse 4 s à un painter
    j = src.index("function ensureBackImgs(")
    ens = src[j:src.index("\n  function ", j)]
    assert "Promise.race" in ens and "IMG_WAIT_MS" in ens, ens


# ── 17.7 RONDE DE REVUE (23/08) — ce que les pixels disaient et pas la prose ─

def test_un_calque_MORT_ne_mange_pas_la_carte(tmp_path):
    """F1, MESURÉ AVANT D'ÊTRE CORRIGÉ. Le damier d'un calque dont le fichier
    manque passait par le cadrage du calque, c'est-à-dire un « cover » d'une
    image 1 x 1 : un carré du CÔTÉ LE PLUS LONG de la toile. Mesure à poker :
    la boîte valait [-147,5 ; 0 ; 1110 ; 1110] et **0 point d'échantillon sur
    6** gardait l'image de fond. Un calque mort effaçait donc l'illustration du
    dos, qui, elle, était là — et le commentaire du code promettait le
    contraire (« pas sur toute la carte, sinon on effacerait l'image de fond »).

    Le damier d'un calque est désormais un ENCART CENTRÉ et nommé : assez grand
    pour se lire sur une épreuve, assez petit pour que le fond respire tout
    autour. Le damier de l'IMAGE DE FOND, lui, couvre bien la toile entière —
    c'est le fond qui manque."""
    imgs = {"img_1.png": (4, 4, IMG_FOND)}
    r = _banc_verso(tmp_path, [
        _cas_verso("mort", back_image="img:img_1.png", imgs=imgs,
                   calques=[{"src": "img:img_9.png", "opacity": 1,
                             "scale": 1, "blend": "normal"}]),
        _cas_verso("vivant", back_image="img:img_1.png", imgs=imgs),
    ])
    m, v = r["mort"], r["vivant"]
    assert m["ok"] and v["ok"], (m.get("err"), v.get("err"))
    # LE TÉMOIN d'abord : sans calque mort, les six points portent le fond.
    for k, px in v["px"].items():
        assert px == IMG_FOND, f"témoin : {k} = {px}"
    # LE FOND RESPIRE : les quatre coins (toile ET coupe) le gardent.
    for k in ("toile_hg", "toile_bd", "coupe_hg", "coupe_bd"):
        assert m["px"][k] == IMG_FOND, \
            f"{k} porte {m['px'][k]} : le damier du calque a mangé l'image " \
            f"de fond"
    # ... et le calque mort est bien DIT, au centre, avec son rang
    assert m["px"]["centre"] != IMG_FOND, "aucun damier n'a été peint"
    assert "img_9.png" in m["textes"], m["textes"]
    assert any("calque 1" in t for t in m["textes"]), m["textes"]


def test_le_peintre_du_verso_ne_FUIT_PAS_sa_toile_de_cuisson_ni_son_lecteur():
    """N5 et N6 de la ronde, deux garde-fous qu'aucun pixel ne peut montrer.

    N5 — la toile de cuisson pèse ~21 Mo en tarot 600 DPI. Le CORE ATTRAPE les
    exceptions de painter (il n'arrête pas les sept autres pièces) : une
    exception au milieu de la pile ferait donc fuir cette toile SILENCIEUSEMENT
    et à chaque frame. Elle se relâche sous `finally`.

    N6 — `drawBackLayer` et `backLayerRect` relisent l'opacité et l'échelle
    pour leur compte. Avec le générique `num()`, ce SECOND lecteur rouvrirait
    le piège que `bnum()` ferme (`Number(null) === 0`). Inatteignable
    aujourd'hui — le painter ne reçoit que du `st()` déjà normalisé — mais le
    prochain appelant n'aura pas cette garantie."""
    src = _js()
    # LES COMMENTAIRES SONT RETIRÉS D'ABORD, et c'est le piège de la 3c-T3
    # rejoué : le premier pin cherchait le mot « finally », que le commentaire
    # du code emploie pour se justifier — le mutant qui SORT la libération du
    # `finally` a donc SURVÉCU, en laissant sa propre prose le couvrir. Un grep
    # de prose est un cliquet, pas une preuve : on ancre sur la STRUCTURE.
    corps = re.sub(r"/\*.*?\*/", "", _js_fn(src, "paintBackCustom"), flags=re.S)
    i = corps.index("} finally {")
    assert "cache.off.width = 0" in corps[i:], \
        "la toile de cuisson n'est pas relâchée sous `finally`"
    assert corps.index("cache.off.width = 0") > i, corps[-400:]
    for nom in ("drawBackLayer", "backLayerRect"):
        c = _js_fn(src, nom)
        assert not re.search(r"\bnum\(", c.replace("bnum(", "")), \
            f"{nom} relit une longueur avec le générique num() : le piège " \
            f"`Number(null) === 0` est rouvert"


def test_le_damier_de_l_IMAGE_DE_FOND_couvre_bien_la_carte(tmp_path):
    """Le contrôle de la correction ci-dessus : rétrécir l'encart d'un CALQUE
    ne doit pas rétrécir celui du FOND. Quand c'est l'image de fond qui
    manque, il n'y a rien à laisser respirer — le damier prend la toile."""
    r = _banc_verso(tmp_path, [_cas_verso("fond", back_image="img:img_9.png")])
    f = r["fond"]
    assert f["ok"], f.get("err")
    for k, px in f["px"].items():
        assert px != BASE_RGBA, f"{k} = {px} : le damier du fond ne couvre plus"
    assert "img_9.png" in f["textes"], f["textes"]


def test_un_dos_PAR_CARTE_peut_etre_personnalise_et_REND(tmp_path):
    """N1. `back_same` décoché fait lire `card.back` (colonne du CSV, pièce
    04), et le catalogue accepte maintenant « custom » : une carte peut donc
    porter le verso personnalisé alors que le jeu porte un motif. Ce n'était
    ni testé ni écrit — un chemin atteignable et muet.

    CE QUI REND : le dos EFFECTIF (`backOf`) est ce que `paintBack` lit pour
    choisir sa branche, et ce que le painter lit pour attendre ses images.
    CE QUI NE SUIT PAS, et c'est dit : les FICHIERS restent ceux du jeu
    (`doc.frame.back_image`) — une image PAR CARTE demanderait une colonne de
    plus, et l'affordance du panneau est consignée pour une phase ultérieure.
    Une carte à dos personnalisé rend donc le verso personnalisé DU JEU."""
    cas = [{"nom": "par_carte",
            "frame": {"back": "guilloche", "back_same": False,
                      "back_image": "img:img_1.png"},
            "card": {"i": 0, "id": "c1", "back": "custom"}},
           {"nom": "commun",
            "frame": {"back": "guilloche", "back_same": True,
                      "back_image": "img:img_1.png"},
            "card": {"i": 0, "id": "c1", "back": "custom"}}]
    res = _banc_verso_st(tmp_path, cas)
    assert res["par_carte"]["kind"] == "custom", res["par_carte"]
    # le TÉMOIN : « dos commun » coché, la carte ne décide plus
    assert res["commun"]["kind"] == "guilloche", res["commun"]
    # ... et les deux lecteurs qui comptent lisent bien le dos EFFECTIF
    src = _js()
    corps = _js_fn(src, "paintBack")
    assert "const kind = backOf(f, card)" in corps, corps[:300]
    i = src.index("painters: [")
    pnt = src[i:src.index("state: DEFAULTS", i)]
    assert 'backOf(f, card) === "custom"' in pnt, \
        "le painter attend ses images sur f.back : une carte à dos " \
        "personnalisé peindrait un damier"


def test_un_JALON_DE_RESERVATION_VIDE_n_est_jamais_SERVI():
    """N3, et LES DEUX MAGASINS. La réservation d'un numéro crée le fichier
    final VIDE (`O_CREAT|O_EXCL`) avant d'y déplacer les octets. Entre les
    deux il y a une fenêtre — courte, mais une panne dure du processus la
    traverse, et le jalon reste sur le disque.

    Mesuré avant correction, sur les DEUX portes (P2 comme sa jumelle P3) :
    `GET .../img_1.png` rendait **200, zéro octet, `Cache-Control: immutable`**.
    Un aperçu qui reçoit ça met un fichier vide en cache pour un an.

    LE PLAFOND, LUI, CONTINUE DE LE COMPTER, et c'est un choix : ce que le
    plafond protège est le NUMÉRO, pas les octets. Un jalon a pris son numéro
    et ne le rendra pas (le compteur MAX+1 ne réattribue jamais). Le message
    de refus dit déjà le geste — supprimer le fichier du dossier du jeu."""
    from app.services.cards import type as TY
    did = _deck()
    for piece, lire in (("frame", FR._read_back_image),
                        ("type", TY._read_slot_image)):
        d = CT.deck_dir(did) / piece
        d.mkdir(parents=True, exist_ok=True)
        (d / "img_1.png").write_bytes(b"")
        assert lire(did, "img_1.png") is None, \
            f"{piece} : le lecteur rend les octets d'un jalon vide"
        r = _api("GET", f"/api/cards/{did}/{piece}/image/img_1.png")
        assert r.status_code == 404, (piece, r.status_code, len(r.content))
        assert "immutable" not in r.headers.get("cache-control", ""), \
            f"{piece} : un fichier vide part avec un cache d'un an"
    # ... et le NUMÉRO reste pris : l'import suivant ne réécrit pas img_1
    r = _post_verso(did, _png_verso(9, 9))
    assert r.status_code == 200, r.text[:200]
    assert r.json()["file"] == "img_2.png", r.json()
    assert (_frame_dir(did) / "img_1.png").stat().st_size == 0, \
        "le jalon a été écrasé : un document qui pointait img_1 change de dos"
    # LE CHOIX, ÉPINGLÉ plutôt que raconté : le jalon COMPTE au plafond. Ce
    # que le plafond protège est le NUMÉRO, et celui-là est pris pour de bon.
    assert FR._next_img_index(_frame_dir(did)) == (3, 2), \
        "le jalon vide a cessé de compter : le plafond ne protège plus le " \
        "numéro, il protège les octets — choisir, et le dire"
