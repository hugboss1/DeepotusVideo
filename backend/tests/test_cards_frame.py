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


# ═══════════════ 1. LE CATALOGUE : 48 combinaisons, et une seule liste ══════

def test_au_moins_20_combinaisons():
    """La barre en propose 3. Le seuil de la spec est 20."""
    cat = FR.catalog()
    assert cat["combos"] == len(FR.FAMILIES) * len(FR.RARITIES)
    assert cat["combos"] >= COMBOS_MIN, \
        f"{cat['combos']} combinaisons, seuil {COMBOS_MIN}"
    assert cat["combos"] == 48, "8 familles x 6 raretés"
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
    """Le source, PRIVÉ des fonctions qui manipulent une image DE
    L'UTILISATEUR — celle qu'il importe pour son verso (3c-T4) et celle qu'il
    fait générer pour le décor de cadre (3c-T5). Voir le test ci-dessous.

    3c-T5 : la liste n'a PAS grandi, et c'est le point. Le décodeur du décor
    n'est pas un décodeur de plus — c'est `loadFrameImg`, le MÊME, avec le
    magasin en paramètre. Le nom a changé (il ne charge plus seulement le
    verso) ; le compte, lui, reste UN."""
    for nom in ("loadFrameImg", "importBackImage", "downscaleBack"):
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
    assert cat["combos"] == 48
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
    # Depuis la phase 6 (D5), paintTop repartit gemme et bandeau par
    # `ornementsAuPlan` (couche 40 ou 70 selon le plan de l'ornement) — les
    # boites viennent toujours du MEME plan d'occupation, jamais d'une
    # constante.
    assert "ornementsAuPlan(plan.boxes, couche)" in src, \
        "paintTop doit repartir les ornements par leur plan"
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


def _py_fn(py: str, nom: str) -> str:
    """Le SOURCE d'une fonction de module de `cards/frame.py` — de son `def`
    au `def` suivant. Suffisant pour lire ce qu'une fonction fait ; ce dépôt
    n'imbrique pas de définitions au niveau du module."""
    i = py.index(f"\ndef {nom}(")
    j = py.find("\ndef ", i + 1)
    return py[i:j if j > 0 else len(py)]


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
    `back_layers`, le verso personnalisé (spec §6.2ter). 32 depuis la 3c-5 :
    `decor`, le décor de cadre par IA (spec §6.3)."""
    src = _js()
    cles = _js_defaults_keys(src)
    assert len(cles) == len(set(cles)), f"clé en double dans DEFAULTS : {cles}"
    # 40 depuis la phase 5-T2 (D3, « les éléments libérés ») : `gem_x`,
    # `gem_y`, `gem_r` (le placement de la gemme, `null` = calculé),
    # `corner_dx`, `corner_dy`, `corner_scale` (les ornements de coin) et
    # `win_stroke_color` / `win_stroke_mm` (le liseré propre de la fenêtre).
    # 42 depuis la phase 6-T3 (D5, « le plan des ornements ») : `gem_plan` et
    # `banner_plan` (« dessus » = décor haut, « dessous » = sous les blocs).
    assert len(cles) == 42, f"{len(cles)} clés dans DEFAULTS : {cles}"
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
    # 42 depuis la phase 6-T3 (D5) : `gem_plan` et `banner_plan`.
    assert len(cles) == 42, f"{len(cles)} clés dans DEFAULTS : {cles}"
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert "39 clés que l'on écrit" in py, \
        "le commentaire de l'habillage ne suit pas les clés neuves (39 " \
        "écrites, la 40e étant `art_window`, publiée par le painter)"


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
    # 42 depuis la phase 6-T3 (D5) : `gem_plan` et `banner_plan`.
    assert len(cles) == 42, f"{len(cles)} clés dans DEFAULTS : {cles}"
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
      /* LE DECOR DE CADRE (3c-T5) passe par le MEME banc : c'est le meme
         geste — une branche imbriquee de `st()` a comparer a son miroir. */
      decor: f.decor,
      /* L'ALIAS : le tableau rendu est-il CELUI du schema ? `DEFAULTS` est
         l'objet meme que `CF.register` remet au registre du CORE — un alias
         rendu ici ferait d'un reglage de carte une ecriture dans le schema
         partage (la lecon du sous-objet `seal`, T1). */
      alias: f.back_layers === mod.DEFAULTS.back_layers,
      alias_decor: f.decor === mod.DEFAULTS.decor });
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
    # ... et la pièce charge bien SES images par SA route (règle 8). Depuis la
    # 3c-T5 la clé porte AUSSI le MAGASIN : un `img_1.png` du jeu et un
    # `img_1.png` du magasin de l'application ne sont pas le même fichier, et
    # le nom seul les confondrait DANS UN MÊME JEU — ce que le rechargement de
    # page ne rattrape pas.
    src = _js()
    st = _js_fn(src, "IMG_STORES") if "function IMG_STORES(" in src else \
        src[src.index("const IMG_STORES = {"):src.index("function imgKey(")]
    assert 'M.api.url("image/"' in st, st
    assert '"/api/images/"' in st, "le magasin de l'application n'est pas lu"
    assert st.count("encodeURIComponent") == 2, \
        "un nom de fichier n'est pas encodé dans l'URL"
    cle = _js_fn(src, "imgKey")
    assert "mag" in cle and "file" in cle, cle


def test_le_painter_du_verso_ATTEND_ses_images_avant_de_peindre():
    """Le patron de P3 : sans l'attente, la première frame peint un damier à
    la place d'une image qui existe — et cette première frame EST le fichier
    livré quand l'export part tout de suite."""
    src = _js()
    i = src.index("painters: [")
    corps = src[i:src.index("state: DEFAULTS", i)]
    assert 'await ensureFrameImgs(files, "deck")' in corps, \
        "le painter ne charge pas les images du verso avant de peindre"
    # ... et le RECTO fait de même pour le décor de l'IA (3c-T5) : même raison,
    # même attente, l'autre magasin
    assert 'await ensureFrameImgs(dfs, "app")' in corps, \
        "le painter ne charge pas le décor du cadre avant de peindre"
    assert "async fn(" in corps, "le painter n'est pas asynchrone"
    # l'attente est BORNÉE : le CORE laisse 4 s à un painter
    ens = _js_fn(src, "ensureFrameImgs")
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


# ═════════════════════════════════════════════════════════════════════════════
# 18. LE DÉCOR DE CADRE PAR IA — phase 3c, tâche 5 (spec §6.3, décision 6)
#
# « Générer le décor de cadre par IA » : la liste des modèles ET LEUR TARIF
# viennent de la table de tarifs de l'application (jamais d'une liste recopiée
# à l'écran), le prix est dit AVANT le clic, l'image générée devient
# `doc.frame.decor = {src, alpha}` et se peint DANS le bloc déjà clippé de
# `paintFront` — la bande, jamais la fenêtre.
#
# LE MAGASIN EST CELUI DE L'APPLICATION (`/api/images`, décision 6) et non le
# dossier du jeu : c'est le MÊME générateur que P1, donc le même magasin. Un
# modèle enregistré depuis ce jeu garde donc le RÉGLAGE (l'opacité) et perd le
# FICHIER (le `src`), comme le verso de la T4 — avec sa note.
# ═════════════════════════════════════════════════════════════════════════════

DECOR_ALPHA_SPEC = (0.0, 1.0)


# ── 18.1 le SCHÉMA, des deux côtés ───────────────────────────────────────────

def test_le_decor_est_la_32e_cle_et_son_schema_est_le_meme_des_deux_cotes():
    """`decor` est un sous-objet — le SECOND de `doc.frame` après `seal`. Comme
    lui il a sa branche imbriquée dans `st()` et son miroir d'exécution au
    backend ; comme lui il naît ÉTEINT (aucune source) pour qu'aucun jeu déjà
    enregistré ne change d'aspect.

    « 32e » est son rang D'ARRIVÉE et il ne bouge pas ; le TOTAL, lui, a
    grandi (40 depuis les huit clés de la phase 5-T2)."""
    src = _js()
    cles = _js_defaults_keys(src)
    assert "decor" in cles, f"la clé decor manque à DEFAULTS : {cles}"
    # 42 depuis la phase 6-T3 (D5) : `gem_plan` et `banner_plan`.
    assert len(cles) == 42, f"{len(cles)} clés dans DEFAULTS : {cles}"
    assert f"porte toujours les {len(cles)} cles" in src, \
        "le commentaire de st() ne dit pas le compte réel"
    # les défauts, littéralement les mêmes
    js = _bloc_const("DECOR_DEFAULTS", src)
    assert re.search(r'src:\s*""', js), js
    assert re.search(r"alpha:\s*1\b", js), js
    assert FR.DECOR_DEFAULTS == {"src": "", "alpha": 1.0}, FR.DECOR_DEFAULTS
    # la borne de l'opacité est dans LIMITS des deux côtés (le test générique
    # `test_les_bornes_sont_les_memes_des_deux_cotes` la compare déjà)
    assert tuple(FR.LIMITS["decor_alpha"]) == DECOR_ALPHA_SPEC, \
        FR.LIMITS["decor_alpha"]


def test_le_motif_des_sources_de_decor_est_ANCRE_des_deux_cotes():
    """Le vocabulaire de `decor.src` : vide, ou `img:<fichier>` du magasin de
    l'APPLICATION. Ancré des DEUX bouts — le `$` d'un motif JavaScript s'arrête
    à la fin de la chaîne, celui de Python accepte un saut de ligne final :
    d'où `fullmatch` au backend (le piège payé trois fois dans ce dépôt)."""
    js = _bloc_const("DECOR_SRC_RE")
    assert js.startswith("/^") and js.endswith("$/"), js
    assert "fullmatch" in _py_fn(pathlib.Path(FR.__file__).read_text(
        encoding="utf-8"), "decor_of"), \
        "decor_of n'utilise pas fullmatch : « img:x.png\\n » traverserait"


DECOR_HOSTILE = {
    "absent": {},
    "vide": {"decor": {}},
    "pas_un_objet": {"decor": "beaucoup"},
    "une_liste": {"decor": [{"src": "img:a.png"}]},
    "normal": {"decor": {"src": "img:gen_ab12cd34.png", "alpha": 0.4}},
    "hors_bornes": {"decor": {"src": "img:gen_1.png", "alpha": 9}},
    "hors_bornes_bas": {"decor": {"src": "img:gen_1.png", "alpha": -3}},
    "src_folle": {"decor": {"src": "img:../meta.json"}},
    "src_absolue": {"decor": {"src": "http://ailleurs/x.png"}},
    "src_deck": {"decor": {"src": "local:x.png"}},
    "src_non_chaine": {"decor": {"src": 7}},
    "saut_de_ligne": {"decor": {"src": "img:gen_1.png\n"}},
    "src_trop_longue": {"decor": {"src": "img:" + "a" * 200 + ".png"}},
    # ── LES FORMES QUI SÉPARENT LES DEUX LANGAGES (leçons F3 et F4 de la T4,
    # rejouées d'office plutôt que redécouvertes) : `null` et `""` que le
    # générique `num()` lirait ZÉRO là où `float()` retombe au DÉFAUT ; et les
    # chaînes numériques que `Number()` et `float()` ne lisent pas pareil.
    "absent_explicite": {"decor": {"src": "img:gen_1.png", "alpha": None}},
    "chaine_vide": {"decor": {"src": "img:gen_1.png", "alpha": ""}},
    "espaces": {"decor": {"src": "img:gen_1.png", "alpha": "  "}},
    "liste": {"decor": {"src": "img:gen_1.png", "alpha": []}},
    "hexa": {"decor": {"src": "img:gen_1.png", "alpha": "0x10"}},
    "souligne": {"decor": {"src": "img:gen_1.png", "alpha": "1_0"}},
    "exposant": {"decor": {"src": "img:gen_1.png", "alpha": "1e0"}},
    "espaces_autour": {"decor": {"src": "img:gen_1.png", "alpha": " 0.5 "}},
    "decimale": {"decor": {"src": "img:gen_1.png", "alpha": "0.5"}},
    "booleen": {"decor": {"src": "img:gen_1.png", "alpha": False}},
}


def test_les_deux_normaliseurs_du_DECOR_rendent_LA_MEME_CHOSE(tmp_path):
    """Parité d'EXÉCUTION (la leçon 3b : aucune correspondance de source ne
    remplace deux exécutions comparées). Les mêmes corps hostiles passent par
    `st()` au navigateur et par `frame.decor_of` au backend."""
    cas = [{"nom": n, "frame": f} for n, f in DECOR_HOSTILE.items()]
    res = _banc_verso_st(tmp_path, cas)
    for nom, fr in DECOR_HOSTILE.items():
        r = res[nom]
        assert r["ok"], f"{nom} : {r.get('err')}"
        assert r["decor"] == FR.decor_of(fr.get("decor")), \
            f"{nom} : écran {r['decor']} vs backend {FR.decor_of(fr.get('decor'))}"
    # ... et ce que la normalisation garantit, NOMMÉ plutôt que déduit
    assert res["normal"]["decor"] == {"src": "img:gen_ab12cd34.png", "alpha": 0.4}
    assert res["hors_bornes"]["decor"]["alpha"] == 1.0
    assert res["hors_bornes_bas"]["decor"]["alpha"] == 0.0
    for nom in ("src_folle", "src_absolue", "src_deck", "src_non_chaine",
                "saut_de_ligne", "src_trop_longue", "pas_un_objet",
                "une_liste"):
        assert res[nom]["decor"]["src"] == "", (nom, res[nom]["decor"])
    # ABSENT vaut DÉFAUT, JAMAIS zéro — des deux côtés (le piège `num()`)
    for nom in ("absent_explicite", "chaine_vide", "espaces", "liste",
                "hexa", "souligne", "exposant", "espaces_autour"):
        assert res[nom]["decor"]["alpha"] == FR.DECOR_DEFAULTS["alpha"], \
            (nom, res[nom]["decor"])
    assert res["decimale"]["decor"]["alpha"] == 0.5
    assert res["booleen"]["decor"]["alpha"] == 0.0


def test_le_decor_rendu_n_est_JAMAIS_celui_du_schema(tmp_path):
    """`DEFAULTS.decor` est le MÊME objet que celui remis au registre du CORE
    (`state: DEFAULTS`). Rendu tel quel, régler l'opacité sur UNE carte
    l'écrirait dans le SCHÉMA — tous les jeux ouverts ensuite naîtraient avec.
    La leçon du sous-objet `seal` (T1), rejouée sur la clé neuve."""
    res = _banc_verso_st(tmp_path, [{"nom": "defaut", "frame": {}}])
    assert res["defaut"]["ok"], res["defaut"].get("err")
    assert res["defaut"]["decor"] == FR.DECOR_DEFAULTS
    assert res["defaut"]["alias_decor"] is False, \
        "st() rend le sous-objet DU SCHÉMA : un réglage écrirait dans le registre"


# ── 18.2 LA ROUTE ai-models : le tarif de l'application, jamais une copie ────

def test_la_route_ai_models_du_cadre_publie_le_TARIF_DE_L_APPLICATION():
    """Le miroir de `face.py:ai-models` (spec §6.3 : « patron face.py:ai-models
    ; JAMAIS de liste recopiée à l'écran »). Le montant vient de la table de
    tarifs que l'utilisateur édite dans Réglages, pas d'un nombre écrit ici."""
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/frame/ai-models")
    assert r.status_code == 200, r.text
    assert "json" in r.headers.get("content-type", "").lower()
    d = r.json()
    for k in ("models", "configured", "devise", "tarif_source", "cle_absente",
              "repli", "erreur"):
        assert k in d, f"{k} absent de la réponse : {sorted(d)}"
    assert d["devise"] == "USD" and d["tarif_source"]
    assert d["models"], "FAL_KEY est posée dans l'environnement de test"
    par_id = {m["id"]: m for m in d["models"]}
    assert "flux" in par_id, sorted(par_id)
    from app.services import pricing
    attendu = pricing.load()["flux_image_usd"]
    assert par_id["flux"]["usd_par_image"] == pytest.approx(attendu), \
        "le prix publié doit être CELUI de l'application, pas une copie"
    assert par_id["flux"]["provider"] == "fal"
    for m in d["models"]:
        assert set(m) == {"id", "label", "provider", "note", "usd_par_image"}, m
    # UN MODÈLE ABSENT DE LA TABLE DE TARIFS N'AFFICHE AUCUN MONTANT :
    # `pricing.estimate` retomberait sur FLUX, et ce repli serait un prix faux.
    # LA RÈGLE EST ÉCRITE CONTRE LA TABLE, PAS CONTRE UN MODÈLE NOMMÉ, et
    # c'est une correction de la phase 5 : l'assertion nommait `nano-banana`
    # et affirmait « il n'a pas de prix » — un fait VRAI le jour où elle a été
    # écrite, et que la tâche T1 de cette phase a rendu faux en tabulant
    # `nano_banana_usd` (plan D2). Un test qui grave un état transitoire de la
    # table de tarifs rougit quand la table s'enrichit, ce qui est exactement
    # l'inverse de ce qu'il protège. Le CONTRAT, lui, ne bouge pas : ce qui est
    # publié est ce que la table porte, et rien quand elle ne porte rien.
    tarifs = pricing.load()
    table = getattr(pricing, "_IMAGE_MODELS", {}) or {}
    vus = 0
    for m in d["models"]:
        spec = table.get(m["id"])
        cle = spec[2] if (spec and len(spec) > 2) else None
        attendu_m = tarifs.get(cle) if cle else None
        if attendu_m is None:
            assert m["usd_par_image"] is None, m
        else:
            assert m["usd_par_image"] == pytest.approx(attendu_m), m
            vus += 1
    assert vus, "aucun modèle tabulé : la règle ne mesurerait rien"
    # ... et le repli existe pour que l'écran ne dise jamais « aucun modèle »
    # quand une clé EST posée
    assert set(FR._keyed_providers()) >= {"fal"}


def test_la_liste_des_modeles_n_est_PAS_RECOPIEE_dans_la_piece():
    """LE PIN DE LA TÂCHE. Une liste de modèles recopiée dans `frame.py`
    dériverait de celle de l'application au premier ajout — un menu qui propose
    un modèle que le backend ne sait pas servir, ou qui cache celui qu'il sert.
    Les DEUX sources sont IMPORTÉES : la table de tarifs
    (`app.services.pricing`) et la liste réellement servie
    (`app.api.routes.list_image_models`).

    Et rien n'est importé de la PIÈCE VOISINE (règle 8) : `face.py` porte le
    même patron, on ne l'importe pas — on importe ce qu'il importe."""
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert "from app.services import pricing" in py, \
        "le tarif ne vient pas de la table de l'application"
    assert "from app.api.routes import list_image_models" in py, \
        "la liste ne vient pas de la route de l'application"
    for voisin in ("from .face import", "from app.services.cards import face",
                   "from . import face"):
        assert voisin not in py, f"règle 8 : {voisin}"
    # AUCUN identifiant de modèle écrit en dur dans la pièce
    sans_com = re.sub(r"#[^\n]*", "", py)
    sans_com = re.sub(r'"""(?:.|\n)*?"""', "", sans_com)
    for mid in ("flux", "gpt-image", "dall-e", "nano-banana", "seedream",
                "recraft"):
        assert mid not in sans_com, \
            f"« {mid} » est écrit en dur dans frame.py : la liste est recopiée"


def test_ai_models_ne_fait_jamais_500_et_refuse_un_deck_inconnu():
    """La règle de la pièce : jamais de 500. Un identifiant illisible est un
    400 qui le dit, un jeu absent un 404."""
    r = _api("GET", "/api/cards/pas_un_deck/frame/ai-models")
    assert r.status_code in (400, 404), r.status_code
    assert r.status_code != 500
    assert isinstance(r.json().get("detail"), str)
    from app.main import app
    assert "/api/cards/{did}/frame/ai-models" in list(app.openapi()["paths"])


# ── 18.3 LE PEINTRE : des pixels, pas des intentions ─────────────────────────
#
# Le banc du verso (17.x) sait les couleurs mais pas le DÉCOUPAGE ; celui du
# peintre (15.2) sait le découpage mais pas les couleurs. Le décor a besoin des
# deux à la fois : ce qui le tient hors de la fenêtre EST le découpage de
# `paintFront`, et ce qu'il pose EST une image en couleurs.
#
# D'où ce banc : le rastériseur par balayage de lignes du banc du peintre —
# courbes aplaties, pair-impair, clip honoré — auquel on ajoute des PIXELS
# RVBA, l'alpha et `drawImage`.
#
# LA MESURE EST DIFFÉRENTIELLE, et c'est ce qui la rend exacte : on rend la
# MÊME carte deux fois, avec et sans décor, et l'on compte les pixels qui
# CHANGENT. Tout le reste du dessin est déterministe (PRNG à graine fixe), donc
# l'écart EST l'empreinte du décor — sans avoir à démêler le décor de la
# matière qui passe par-dessus.
#
# CE QUE LE BANC N'IMITE PAS, ET C'EST DIT : un dégradé rend un gris à 35 % (le
# banc ne modélise pas les arrêts de couleur). L'approximation est la même dans
# les deux rendus, donc elle disparaît de la différence.

BANC_DECOR = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));

const N_BEZ = 12, N_ARC = 20;
const TEXTES = [];
const MODES = {};

function couleur(s) {
  const t = String(s);
  let m = /^#([0-9a-f]{6})$/i.exec(t);
  if (m) { const n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 255]; }
  m = /^#([0-9a-f]{3})$/i.exec(t);
  if (m) { const c = m[1];
    return [parseInt(c[0] + c[0], 16), parseInt(c[1] + c[1], 16),
      parseInt(c[2] + c[2], 16), 255]; }
  m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/
    .exec(t);
  if (m) return [+m[1], +m[2], +m[3],
    Math.round((m[4] === undefined ? 1 : +m[4]) * 255)];
  return [0, 0, 0, 255];
}
/* un DEGRADE : le banc ne modelise pas les arrets de couleur — il rend un gris
   a 35 %, le MEME dans les deux rendus compares. */
const GRAD = { addColorStop: function () {}, toString: function () {
  return "rgba(128,128,128,0.35)"; } };

function Ctx(W, H) {
  this.W = W; this.H = H;
  this.d = new Uint8ClampedArray(W * H * 4);
  this.msk = new Uint8Array(W * H).fill(1);
  this.stk = []; this.t = { sx: 1, sy: 1, tx: 0, ty: 0 };
  this.sub = []; this.cur = null;
  this.fillStyle = "#000000"; this.strokeStyle = "#000000"; this.lineWidth = 1;
  this.globalAlpha = 1; this.globalCompositeOperation = "source-over";
  this.shadowBlur = 0; this.shadowColor = ""; this.lineCap = "";
  this.lineJoin = ""; this.font = ""; this.textAlign = "";
  this.textBaseline = ""; this.imageSmoothingEnabled = true;
}
Ctx.prototype.save = function () {
  this.stk.push({ t: { sx: this.t.sx, sy: this.t.sy, tx: this.t.tx, ty: this.t.ty },
    msk: this.msk.slice(), fs: this.fillStyle, ss: this.strokeStyle,
    lw: this.lineWidth, ga: this.globalAlpha,
    op: this.globalCompositeOperation, sb: this.shadowBlur,
    sc: this.shadowColor });
};
Ctx.prototype.restore = function () {
  const s = this.stk.pop();
  if (!s) return;
  this.t = s.t; this.msk = s.msk; this.fillStyle = s.fs; this.strokeStyle = s.ss;
  this.lineWidth = s.lw; this.globalAlpha = s.ga;
  this.globalCompositeOperation = s.op; this.shadowBlur = s.sb;
  this.shadowColor = s.sc;
};
Ctx.prototype.translate = function (x, y) {
  this.t.tx += x * this.t.sx; this.t.ty += y * this.t.sy;
};
Ctx.prototype.scale = function (x, y) { this.t.sx *= x; this.t.sy *= y; };
Ctx.prototype.rotate = function () {};
Ctx.prototype._p = function (x, y) {
  return [x * this.t.sx + this.t.tx, y * this.t.sy + this.t.ty];
};
Ctx.prototype.beginPath = function () { this.sub = []; this.cur = null; };
Ctx.prototype.moveTo = function (x, y) {
  this.cur = [this._p(x, y)]; this.sub.push(this.cur);
};
Ctx.prototype.lineTo = function (x, y) {
  if (!this.cur) this.moveTo(x, y); else this.cur.push(this._p(x, y));
};
Ctx.prototype.closePath = function () {};
Ctx.prototype.rect = function (x, y, w, h) {
  this.moveTo(x, y); this.lineTo(x + w, y);
  this.lineTo(x + w, y + h); this.lineTo(x, y + h);
  this.cur = null;
};
Ctx.prototype.arcTo = function (x1, y1, x2, y2) {
  this.lineTo(x1, y1); this.lineTo(x2, y2);
};
Ctx.prototype.arc = function (cx, cy, r, a0, a1) {
  for (let i = 0; i <= N_ARC; i++) {
    const a = a0 + (a1 - a0) * i / N_ARC;
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    if (i === 0 && !this.cur) this.moveTo(x, y); else this.lineTo(x, y);
  }
};
Ctx.prototype.ellipse = function (cx, cy, rx, ry, rot, a0, a1) {
  const ca = Math.cos(rot || 0), sa = Math.sin(rot || 0);
  for (let i = 0; i <= N_ARC; i++) {
    const a = a0 + (a1 - a0) * i / N_ARC;
    const px = Math.cos(a) * rx, py = Math.sin(a) * ry;
    const x = cx + px * ca - py * sa, y = cy + px * sa + py * ca;
    if (i === 0 && !this.cur) this.moveTo(x, y); else this.lineTo(x, y);
  }
};
Ctx.prototype.bezierCurveTo = function (x1, y1, x2, y2, x3, y3) {
  if (!this.cur) this.moveTo(x1, y1);
  const p0 = this.cur[this.cur.length - 1];
  const ix = (p0[0] - this.t.tx) / this.t.sx, iy = (p0[1] - this.t.ty) / this.t.sy;
  for (let i = 1; i <= N_BEZ; i++) {
    const t = i / N_BEZ, u = 1 - t;
    this.lineTo(u * u * u * ix + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3,
      u * u * u * iy + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3);
  }
};
Ctx.prototype.quadraticCurveTo = function (x1, y1, x2, y2) {
  this.bezierCurveTo(x1, y1, x1, y1, x2, y2);
};
Ctx.prototype._pose = function (q, src, ga) {
  MODES[this.globalCompositeOperation] =
    (MODES[this.globalCompositeOperation] || 0) + 1;
  const o = q * 4, sa = (src[3] / 255) * ga, da = this.d[o + 3] / 255;
  const a = sa + da * (1 - sa);
  for (let k = 0; k < 3; k++) {
    const Cs = src[k] / 255, Cb = this.d[o + k] / 255;
    this.d[o + k] = a ? Math.round((Cs * sa + Cb * da * (1 - sa)) / a * 255) : 0;
  }
  this.d[o + 3] = Math.round(a * 255);
};
Ctx.prototype._balayage = function (eo, cb, brut) {
  for (let y0 = 0; y0 < this.H; y0++) {
    const y = y0 + 0.5, xs = [];
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
      if (!(eo ? (i % 2 === 0) : (w !== 0))) continue;
      let g0 = Math.ceil(xs[i][0] - 0.5), g1 = Math.ceil(xs[i + 1][0] - 0.5);
      if (g0 < 0) g0 = 0;
      if (g1 > this.W) g1 = this.W;
      for (let x = g0; x < g1; x++) {
        const q = y0 * this.W + x;
        if (brut || this.msk[q]) cb(q);
      }
    }
  }
};
Ctx.prototype._trace = function (cb) {
  for (let s = 0; s < this.sub.length; s++) {
    const sp = this.sub[s];
    for (let i = 0; i + 1 < sp.length; i++) {
      const a = sp[i], b = sp[i + 1];
      const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.5));
      for (let k = 0; k <= n; k++) {
        const x = Math.floor(a[0] + (b[0] - a[0]) * k / n);
        const y = Math.floor(a[1] + (b[1] - a[1]) * k / n);
        if (x < 0 || y < 0 || x >= this.W || y >= this.H) continue;
        const q = y * this.W + x;
        if (this.msk[q]) cb(q);
      }
    }
  }
};
Ctx.prototype.fill = function (rule) {
  const c = couleur(this.fillStyle), ga = this.globalAlpha, self = this;
  this._balayage(rule === "evenodd", function (q) { self._pose(q, c, ga); });
};
Ctx.prototype.stroke = function () {
  const c = couleur(this.strokeStyle), ga = this.globalAlpha, self = this;
  this._trace(function (q) { self._pose(q, c, ga); });
};
Ctx.prototype.clip = function (rule) {
  const m = new Uint8Array(this.W * this.H);
  this._balayage(rule === "evenodd", function (q) { m[q] = 1; }, true);
  for (let i = 0; i < m.length; i++) if (!m[i]) this.msk[i] = 0;
};
Ctx.prototype.fillRect = function (x, y, w, h) {
  this.beginPath(); this.rect(x, y, w, h); this.fill();
};
Ctx.prototype.strokeRect = function (x, y, w, h) {
  this.beginPath(); this.rect(x, y, w, h); this.stroke();
};
Ctx.prototype.createLinearGradient = function () { return GRAD; };
Ctx.prototype.createRadialGradient = function () { return GRAD; };
Ctx.prototype.createPattern = function () { return null; };
Ctx.prototype.setLineDash = function () {};
Ctx.prototype.fillText = function (t) { TEXTES.push(String(t)); };
Ctx.prototype.strokeText = function () {};
Ctx.prototype.measureText = function (t) { return { width: String(t).length * 6 }; };
Ctx.prototype.drawImage = function (img, dx, dy, dw, dh) {
  if (dw === undefined) { dx = dx || 0; dy = dy || 0; dw = img.width; dh = img.height; }
  const x0 = Math.max(0, Math.floor(dx)), x1 = Math.min(this.W, Math.ceil(dx + dw));
  const y0 = Math.max(0, Math.floor(dy)), y1 = Math.min(this.H, Math.ceil(dy + dh));
  for (let j = y0; j < y1; j++) {
    let sy = Math.floor((j + 0.5 - dy) / dh * img.height);
    sy = Math.min(img.height - 1, Math.max(0, sy));
    for (let i = x0; i < x1; i++) {
      let sx = Math.floor((i + 0.5 - dx) / dw * img.width);
      sx = Math.min(img.width - 1, Math.max(0, sx));
      const q = j * this.W + i;
      if (!this.msk[q]) continue;
      const s = (sy * img.width + sx) * 4;
      this._pose(q, [img.d[s], img.d[s + 1], img.d[s + 2], img.d[s + 3]],
        this.globalAlpha);
    }
  }
};
Ctx.prototype.getImageData = function (x, y, w, h) {
  const out = new Uint8ClampedArray(w * h * 4);
  for (let j = 0; j < h; j++)
    for (let i = 0; i < w; i++) {
      const s = ((y + j) * this.W + (x + i)) * 4, o = (j * w + i) * 4;
      out[o] = this.d[s]; out[o + 1] = this.d[s + 1];
      out[o + 2] = this.d[s + 2]; out[o + 3] = this.d[s + 3];
    }
  return { width: w, height: h, data: out };
};
Ctx.prototype.putImageData = function (im, x, y) {
  for (let j = 0; j < im.height; j++)
    for (let i = 0; i < im.width; i++) {
      const o = (j * im.width + i) * 4, s = ((y + j) * this.W + (x + i)) * 4;
      this.d[s] = im.data[o]; this.d[s + 1] = im.data[o + 1];
      this.d[s + 2] = im.data[o + 2]; this.d[s + 3] = im.data[o + 3];
    }
};
globalThis.document = { createElement: function () {
  const cv = { _w: 0, _h: 0, ctx: null };
  Object.defineProperty(cv, "width", { get: () => cv._w,
    set: (v) => { cv._w = v | 0; cv.ctx = new Ctx(cv._w, cv._h || 1); } });
  Object.defineProperty(cv, "height", { get: () => cv._h,
    set: (v) => { cv._h = v | 0; cv.ctx = new Ctx(cv._w || 1, cv._h); } });
  cv.getContext = () => cv.ctx || new Ctx(1, 1);
  return cv;
} };

const mod = new Function("return (function(){ " + CODE
  + "\nreturn { st: st, model: model, paintFront: paintFront,"
  + " paintDecor: paintDecor, decorFile: decorFile,"
  + " decorMissRect: decorMissRect, backCover: backCover,"
  + " BIMGS: BIMGS, imgKey: imgKey, WIN_SHAPE: WIN_SHAPE, winPath: winPath };"
  + "\n})();")();

function image(spec) {
  const w = spec.w, h = spec.h;
  const im = { width: w, height: h, d: new Uint8ClampedArray(w * h * 4) };
  for (let i = 0; i < w * h; i++) {
    im.d[i * 4] = spec.rgba[0]; im.d[i * 4 + 1] = spec.rgba[1];
    im.d[i * 4 + 2] = spec.rgba[2]; im.d[i * 4 + 3] = spec.rgba[3];
  }
  return im;
}

const CARTE = { i: 0, id: "c1", fields: {}, art: null, back: null };

const out = [];
for (const c of CAS.cas) {
  const dpi = c.g.dpi;
  const g = Object.assign({}, c.g, { mm2px: (v) => v / 25.4 * dpi });
  TEXTES.length = 0;
  for (const k of Object.keys(MODES)) delete MODES[k];
  try {
    const f = mod.st({ frame: c.frame });
    const m = mod.model(g, f);
    /* LE CACHE DU MODULE, SEME A LA MAIN : c'est `paintFront` lui-meme qui va
       chercher l'etat de l'image, et la CLE porte le MAGASIN. */
    mod.BIMGS.clear();
    for (const nom of Object.keys(c.imgs || {})) {
      mod.BIMGS.set(mod.imgKey(c.magasin || "app", nom),
        { img: image(c.imgs[nom]), ok: true, file: nom });
    }
    const rendu = (frame) => {
      const ctx = new Ctx(m.W, m.H);
      mod.paintFront(ctx, g, mod.st({ frame: frame }), CARTE, {});
      return ctx;
    };
    if (c.mode === "direct") {
      /* le peintre SEUL, sur un aplat connu : l'oracle de l'alpha */
      const ctx = new Ctx(m.W, m.H);
      ctx.fillStyle = c.base; ctx.fillRect(0, 0, m.W, m.H);
      const IM = {};
      for (const nom of Object.keys(c.imgs || {})) IM[nom] = image(c.imgs[nom]);
      const get = (file) => (IM[file] ? { img: IM[file], ok: true, file: file }
        : { img: null, ok: false, file: file });
      mod.paintDecor(ctx, m, f, get);
      const px = (x, y) => { const o = ((y | 0) * m.W + (x | 0)) * 4;
        return [ctx.d[o], ctx.d[o + 1], ctx.d[o + 2], ctx.d[o + 3]]; };
      out.push({ nom: c.nom, ok: true, mode: "direct",
        toile: [m.W, m.H], coupe: [m.trim.x, m.trim.y, m.trim.w, m.trim.h],
        encart: mod.decorMissRect(m),
        couvre: mod.backCover(4, 4, m.W, m.H),
        modes: Object.keys(MODES).sort(), textes: TEXTES.slice(),
        px: { hg: px(2, 2), centre: px(m.W >> 1, m.H >> 1),
          bd: px(m.W - 3, m.H - 3) } });
      continue;
    }
    /* MESURE DIFFERENTIELLE : la meme carte avec et sans decor */
    const avec = rendu(c.frame);
    const sans = rendu(Object.assign({}, c.frame, { decor: { src: "" } }));
    const nomsImg = Object.keys(c.imgs || {});
    const dec = nomsImg.length ? c.imgs[nomsImg[0]].rgba : [-1, -1, -1, -1];
    /* LA FENETRE EST CELLE DU PRODUIT, pas une boite recalculee ici : elle est
       ARQUEE chez `arcane`, chanfreinee chez `deco`, et une boite
       rectangulaire y comprendrait des coins de BANDE — c'est-a-dire du decor
       legitime, compte comme une fuite. On rejoue donc `winPath` du module sur
       un masque. */
    const mw = new Ctx(m.W, m.H);
    mw.beginPath();
    mod.winPath(mw, m, mod.WIN_SHAPE[f.family] || "rect");
    mw.clip();
    const zone = (bx, dedans) => {
      let chg = 0, tot = 0, pur = 0;
      const x0 = Math.max(0, Math.round(bx[0])), x1 = Math.min(m.W, Math.round(bx[0] + bx[2]));
      const y0 = Math.max(0, Math.round(bx[1])), y1 = Math.min(m.H, Math.round(bx[1] + bx[3]));
      for (let j = y0; j < y1; j++) for (let i = x0; i < x1; i++) {
        const q = j * m.W + i;
        if (dedans !== undefined && (!!mw.msk[q]) !== dedans) continue;
        const o = q * 4;
        tot++;
        if (avec.d[o] !== sans.d[o] || avec.d[o + 1] !== sans.d[o + 1]
          || avec.d[o + 2] !== sans.d[o + 2]) chg++;
        if (avec.d[o] === dec[0] && avec.d[o + 1] === dec[1]
          && avec.d[o + 2] === dec[2]) pur++;
      }
      return { chg: chg, tot: tot, pur: pur };
    };
    const T = m.trim, W = m.win, E = mod.decorMissRect(m);
    out.push({ nom: c.nom, ok: true, mode: "carte",
      toile: [m.W, m.H], coupe: [T.x, T.y, T.w, T.h],
      win: [W.x, W.y, W.w, W.h],
      encart: E,
      textes: TEXTES.slice(),
      zones: {
        /* LA BOITE QUE `decorMissRect` ANNONCE, relue sur les pixels : elle
           dit ou l'encart DEVRAIT etre. Un encart pose ailleurs (au centre,
           par exemple) n'y change rien — et le decoupage l'aurait avale. */
        encart: zone(E),
        toile: zone([0, 0, m.W, m.H]),
        /* LA FENETRE, rentree de 2 px sur le masque du produit : le filet
           interieur et l'ombre portee sont peints SUR son arete, et le banc
           n'a pas d'anticrenelage — un pixel de bord partage par deux chemins
           ne prouverait rien. */
        fenetre: zone([W.x + 2, W.y + 2, W.w - 4, W.h - 4], true),
        bande_haut: zone([T.x, T.y, T.w, W.y - T.y], false),
        bande_bas: zone([T.x, W.y + W.h, T.w, T.y + T.h - (W.y + W.h)], false),
        perdu: zone([0, 0, m.W, T.y], false),
      } });
  } catch (e) {
    out.push({ nom: c.nom, ok: false, err: String((e && e.stack) || e) });
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_decor(tmp_path, cas: list, mutations=()) -> dict:
    """Le VRAI `paintFront` sur une toile RVBA à découpage réel."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du décor ne peut pas tourner")
    code = _verso_js_source()
    for avant, apres in mutations:
        assert avant in code, f"mutation introuvable : {avant!r}"
        code = code.replace(avant, apres)
    js = tmp_path / "decor.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_decor.mjs"
    banc.write_text(BANC_DECOR, encoding="utf-8")
    conf = tmp_path / "cas_decor.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=600)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x for x in json.loads(r.stdout)}


DECOR_RGBA = [250, 10, 190, 255]        # un magenta que rien d'autre ne produit
DECOR_FILE = "gen_ab12cd34.png"


def _cas_decor(nom, src="img:" + DECOR_FILE, alpha=1.0, imgs=None,
               mode="carte", base="#204060", fmt="poker_eu", dpi=150,
               magasin="app", **frame):
    fr = {"family": "arcane", "rarity": "rare",
          "decor": {"src": src, "alpha": alpha}}
    fr.update(frame)
    fichiers = {}
    for f, spec in (imgs if imgs is not None
                    else {DECOR_FILE: (4, 4, DECOR_RGBA)}).items():
        fichiers[f] = {"w": spec[0], "h": spec[1], "rgba": spec[2]}
    return {"nom": nom, "g": _geom_js(fmt, 3, dpi), "frame": fr, "mode": mode,
            "base": base, "imgs": fichiers, "magasin": magasin}


def test_le_decor_lit_le_magasin_de_L_APPLICATION_pas_celui_du_JEU(tmp_path):
    """La décision 6, MESURÉE sur les pixels et non lue dans le code.

    Le même nom de fichier rangé dans le cache sous le magasin DU JEU n'est pas
    le décor : le peintre ne le trouve pas et peint son encart de manque. Une
    clé de cache qui oublierait le magasin les confondrait — dans un même jeu,
    et le rechargement de page qui protège le reste n'y changerait rien."""
    res = _banc_decor(tmp_path, [
        _cas_decor("app", magasin="app"),
        _cas_decor("deck", magasin="deck")])
    assert res["app"]["textes"] == [], \
        "le décor du magasin de l'application n'a pas été trouvé"
    assert DECOR_FILE in res["deck"]["textes"], \
        "une image rangée sous le magasin DU JEU a servi de décor : la clé de " \
        "cache ne porte pas le magasin"


def test_le_decor_encre_la_BANDE_et_JAMAIS_la_fenetre(tmp_path):
    """LE SEUIL DE LA TÂCHE, mesuré sur les pixels du VRAI `paintFront`.

    Le décor est peint DANS le bloc déjà découpé « toile MOINS fenêtre » : ce
    qui le tient hors de l'illustration n'est pas une boîte calculée à la main,
    c'est le découpage du peintre. La mesure est DIFFÉRENTIELLE — la même carte
    rendue deux fois, avec et sans décor — donc l'écart EST le décor, matière
    comprise."""
    res = _banc_decor(tmp_path, [_cas_decor("plein")])
    r = res["plein"]
    assert r["ok"], r.get("err")
    z = r["zones"]
    assert z["fenetre"]["chg"] == 0, \
        f"{z['fenetre']['chg']} pixels de l'illustration changent : le décor " \
        f"déborde sur la fenêtre"
    for coin in ("bande_haut", "bande_bas"):
        part = z[coin]["chg"] / z[coin]["tot"]
        assert part > 0.5, f"{coin} : seulement {part:.0%} de la bande reçoit le décor"
    # ... ET LE FOND PERDU AUSSI : la découpe vient APRÈS l'impression, un
    # décor calé sur la seule rogne poserait la matière de bande sur l'arête
    assert z["perdu"]["chg"] / z["perdu"]["tot"] > 0.5, z["perdu"]


HORS_CLIP = [
    ("    paintDecor(ctx, m, f, decorRec);\n", ""),
    ("    ctx.restore();\n\n    /* 3. la plaque de texte",
     "    ctx.restore();\n    paintDecor(ctx, m, f, decorRec);\n"
     "\n    /* 3. la plaque de texte"),
]
SUR_LA_MATIERE = [
    ("    paintDecor(ctx, m, f, decorRec);\n", ""),
    ("    matter(ctx, m, f, shape);\n    winMoulding",
     "    matter(ctx, m, f, shape);\n    paintDecor(ctx, m, f, decorRec);\n"
     "    winMoulding"),
]


def test_sans_le_decoupage_le_decor_couvre_l_illustration(tmp_path):
    """LE MUTANT, et il meurt. Sorti du bloc découpé — le MÊME appel, deux
    lignes plus bas, après le `restore()` de l'étape 2 — le décor recouvre la
    fenêtre, c'est-à-dire l'illustration de P1, sous un cadre censé
    l'encadrer."""
    r = _banc_decor(tmp_path, [_cas_decor("hors_clip")],
                    mutations=HORS_CLIP)["hors_clip"]
    assert r["ok"], r.get("err")
    z = r["zones"]["fenetre"]
    assert z["chg"] / z["tot"] > 0.9, \
        f"le mutant ne couvre que {z['chg']}/{z['tot']} de la fenêtre : la " \
        f"mesure ne verrait pas un décor sorti du découpage"


def test_le_decor_passe_SOUS_la_matiere_et_pas_dessus(tmp_path):
    """LA DÉCISION DE PLACEMENT, rendue mesurable.

    Le décor est l'ILLUSTRATION de la bande ; `matter()` est le FINI de sa
    surface (trames, patine, usures). On imprime l'encre, puis le grain du
    papier et l'usure appartiennent à la surface AU-DESSUS d'elle : le décor
    passe donc SOUS la matière, et le fini continue de courir par-dessus lui —
    sans quoi l'image générée efface la matière et le cadre devient un
    autocollant.

    Mesure : la part de la bande dont les pixels sortent EXACTEMENT à la
    couleur BRUTE du décor. Sous la matière elle reste basse (le fini repasse
    dessus) ; au-dessus, elle saute. Relevé au banc, poker 150 DPI, arcane,
    aplat opaque : haut de bande 1,6 % contre 78,8 %, fond perdu 0 % contre
    100 % — au-dessus, la matière a purement disparu."""
    normal = _banc_decor(tmp_path, [_cas_decor("sous")])["sous"]
    dessus = _banc_decor(tmp_path, [_cas_decor("dessus")],
                         mutations=SUR_LA_MATIERE)["dessus"]
    assert normal["ok"] and dessus["ok"], (normal.get("err"), dessus.get("err"))
    for zn in ("bande_haut", "perdu"):
        a, b = normal["zones"][zn], dessus["zones"][zn]
        pa, pb = a["pur"] / a["tot"], b["pur"] / b["tot"]
        assert pa < 0.2, \
            f"{zn} : {pa:.1%} sort à la couleur brute du décor — la matière " \
            f"ne passe plus par-dessus"
        assert pb > 0.6, \
            f"{zn} : le mutant ne laisse que {pb:.1%} de couleur brute, la " \
            f"mesure ne sépare plus les deux ordres"


def test_l_opacite_du_decor_est_CELLE_DU_REGLAGE(tmp_path):
    """L'alpha, sur un aplat connu et avec l'oracle du compositeur. Le peintre
    est appelé SEUL (mode direct) : la matière ne repasse pas dessus, donc le
    pixel est exactement le mélange annoncé."""
    cas = [_cas_decor("a100", alpha=1.0, mode="direct"),
           _cas_decor("a050", alpha=0.5, mode="direct"),
           _cas_decor("a000", alpha=0.0, mode="direct")]
    res = _banc_decor(tmp_path, cas)
    base = [0x20, 0x40, 0x60]
    for nom, a in (("a100", 1.0), ("a050", 0.5), ("a000", 0.0)):
        r = res[nom]
        assert r["ok"], r.get("err")
        attendu = [_sur(DECOR_RGBA[k], base[k], a) for k in range(3)]
        assert r["px"]["hg"][:3] == attendu, (nom, r["px"]["hg"], attendu)
        assert r["px"]["centre"][:3] == attendu, (nom, r["px"]["centre"])
    # l'opacité NULLE ne pose rien du tout — pas un aplat transparent
    assert res["a000"]["px"]["hg"][:3] == base


def test_l_opacite_ignoree_ferait_ROUGIR_l_aplat(tmp_path):
    """Le mutant : `globalAlpha` laissé à 1. Sans lui, le curseur d'opacité est
    un réglage qui ne règle rien."""
    res = _banc_decor(
        tmp_path, [_cas_decor("mut", alpha=0.5, mode="direct")],
        mutations=[("ctx.globalAlpha = a;", "ctx.globalAlpha = 1;")])
    px = res["mut"]["px"]["hg"][:3]
    assert px == DECOR_RGBA[:3], px


def test_le_decor_couvre_la_TOILE_ENTIERE_pas_la_seule_coupe(tmp_path):
    """Le cadrage « cover » part du bord de TOILE, la même règle que l'image du
    verso (T4) et que le remplissage de l'anneau du Sceau : la découpe vient
    APRÈS l'impression, et un décor calé sur la rogne laisserait 3 mm de bande
    nue sous la lame."""
    r = _banc_decor(tmp_path, [_cas_decor("cover", mode="direct")])["cover"]
    W, H = r["toile"]
    assert r["couvre"] == [pytest.approx((W - max(W, H)) / 2),
                           pytest.approx((H - max(W, H)) / 2),
                           pytest.approx(max(W, H)),
                           pytest.approx(max(W, H))], r["couvre"]
    # les quatre coins de TOILE portent le décor (mode direct, alpha 1)
    for coin in ("hg", "bd"):
        assert r["px"][coin][:3] == DECOR_RGBA[:3], (coin, r["px"][coin])


def test_un_decor_ABSENT_donne_un_ENCART_NOMME_dans_la_bande(tmp_path):
    """L'état « ce fichier n'est pas arrivé », peint DANS le fichier livré (le
    patron de la T4) — mais un encart CENTRÉ tomberait dans la fenêtre, donc
    dans la seule zone que le découpage efface : le manque serait MUET. Il se
    pose donc dans la BANDE, du côté le plus large, et il se NOMME."""
    res = _banc_decor(tmp_path, [
        _cas_decor("manque", imgs={}, mode="direct"),
        _cas_decor("manque_carte", imgs={}),
        _cas_decor("vide", src="", imgs={}, mode="direct")])
    r = res["manque"]
    assert r["ok"], r.get("err")
    assert DECOR_FILE in r["textes"], r["textes"]
    assert any("décor" in t for t in r["textes"]), r["textes"]
    # l'encart tient dans la BANDE : au-dessus (ou au-dessous) de la fenêtre,
    # jamais sur la carte entière
    e, T = r["encart"], r["coupe"]
    assert e[2] < T[2] and e[3] < T[3] * 0.5, (e, T)
    assert e[0] >= T[0] and e[0] + e[2] <= T[0] + T[2] + 1, (e, T)
    # ... ET IL EST VRAIMENT LÀ, sur les pixels de la carte : la boîte que
    # `decorMissRect` annonce est celle qui a changé. Un encart posé ailleurs —
    # au centre, comme celui du verso — laisserait cette boîte intacte, et le
    # découpage l'aurait avalé sans un mot (c'est le mutant, et il meurt ici).
    car = res["manque_carte"]["zones"]
    assert car["encart"]["chg"] / car["encart"]["tot"] > 0.7, \
        f"seuls {car['encart']['chg']}/{car['encart']['tot']} pixels de " \
        f"l'encart annoncé ont changé : il n'est pas peint là"
    assert car["fenetre"]["chg"] == 0, "l'encart déborde sur l'illustration"
    # une source VIDE ne salit RIEN : c'est un décor qu'on n'a pas généré
    assert res["vide"]["textes"] == [], res["vide"]["textes"]
    assert res["vide"]["px"]["hg"][:3] == [0x20, 0x40, 0x60]


def test_le_decor_ne_demande_JAMAIS_qu_un_source_over(tmp_path):
    """La preuve d'empilement de §4.2 juge la couche « cadre » en la
    re-empilant en `source-over`. Le décor est un `drawImage` nu : il ne
    demande aucun mode de fusion, donc il ne fait PAS basculer la couche en
    « empreinte » (le Sceau, lui, le fait — et c'est orthogonal)."""
    r = _banc_decor(tmp_path, [_cas_decor("modes", mode="direct")])["modes"]
    assert r["modes"] == ["source-over"], r["modes"]
    src = _js()
    corps = _js_fn(src, "paintDecor")
    assert "globalCompositeOperation" not in corps, corps


def test_la_couche_du_cadre_reste_ISOLEE_avec_un_decor(tmp_path):
    """Le banc §4.2 sur la VRAIE `layers()` du CORE : une couche qui ne pose
    que du `source-over` opaque se re-empile à l'identique, donc « isolée ».
    Le décor n'y change rien — c'est le Sceau qui bascule en « empreinte », et
    les deux réglages sont indépendants."""
    r = _banc_empilement(tmp_path, "source-over")
    assert dict(r["modes"])["cadre"] == "isolee", r["modes"]
    assert r["stack_ok"] is True, r
    # ... et le décor est bien de cette nature-là : un `drawImage` nu, sans
    # `globalCompositeOperation` (mesuré au banc du décor, ci-dessus).
    assert "globalCompositeOperation" not in _js_fn(_js(), "paintDecor")


# ── 18.4 L'ÉCRAN : les trois jambes du prix, et l'invite pré-remplie ─────────
#
# Ce que ces deux fonctions ÉCRIVENT, joué. Elles sont pures à leurs variables
# libres près (`AI_MODELS`, `AI_META`, `UI`) : on les injecte, on lit le HTML.

BANC_ECRAN = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const out = [];
for (const c of CAS.cas) {
  const UI = { decorModel: { value: c.model }, decorCost: { innerHTML: "" } };
  const f = new Function("UI", "AI_MODELS", "AI_META", CODE
    + "\nreturn { options: decorModelOptions, cout: decorCostLine };")(
    UI, c.modeles || [], c.meta || {});
  const options = f.options();
  f.cout();
  out.push({ nom: c.nom, options: options, cout: UI.decorCost.innerHTML });
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_ecran(tmp_path, cas: list) -> dict:
    """`decorModelOptions` et `decorCostLine`, jouées telles qu'elles sont
    livrées — avec `esc` et `usdFmt`, dont elles se servent."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de l'écran ne peut pas tourner")
    src = _js()
    code = "\n".join(_js_fn(src, n) for n in
                     ("esc", "usdFmt", "decorModelOptions", "decorCostLine"))
    js = tmp_path / "ecran.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_ecran.mjs"
    banc.write_text(BANC_ECRAN, encoding="utf-8")
    conf = tmp_path / "cas_ecran.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x for x in json.loads(r.stdout)}


MODELES_ESPION = [
    {"id": "flux", "label": "FLUX schnell", "provider": "fal", "note": "",
     "usd_par_image": 0.003},
    {"id": "sans-tarif", "label": "Inconnu", "provider": "fal", "note": "",
     "usd_par_image": None},
]


def test_le_panneau_porte_le_groupe_du_decor_et_ses_commandes():
    """Le groupe « Décor de cadre par IA » (spec §6.3) : le menu des modèles,
    l'invite, le coût du clic, le bouton qui dépense, l'opacité et le retrait.
    Un écran qui génère sans offrir de retirer laisse l'utilisateur devant une
    dépense qu'il ne peut pas défaire."""
    src = _js()
    assert 'grp("Décor de cadre par IA"' in src, \
        "le groupe du décor n'existe pas dans le panneau"
    for attendu in ("UI.decorModel", "UI.decorPrompt", "UI.decorCost",
                    "UI.decorGen", "UI.decorA", "UI.decorRead"):
        assert attendu in src, f"{attendu} absent du panneau"
    assert "Retirer le décor" in src, "aucun moyen de retirer le décor"
    assert "decorGenerate" in src


def test_le_cout_du_decor_est_un_MONTANT_pas_un_compte(tmp_path):
    """Les TROIS jambes du patron P1, sur cette pièce-ci : le tarif par modèle
    DANS l'étiquette du menu, « Coût de ce clic » AVANT le clic, et le montant
    facturé dit APRÈS. Un écran qui chiffre avant et se tait après laisse
    l'utilisateur sans trace de sa dépense.

    LES DEUX PREMIÈRES JAMBES SONT MESURÉES, PAS GREPPÉES — et c'est une leçon
    payée à la ronde de mutation : deux mutants qui VIDAIENT le prix (l'un de
    l'étiquette, l'autre de la ligne de coût) ont SURVÉCU à des `assert "Coût
    de ce clic" in src`, parce que la même phrase vit dans l'autre branche
    (« tarif non tabulé »). Un grep de prose est un cliquet, pas une preuve —
    la troisième fois que ce dépôt l'apprend. On fait donc TOURNER les deux
    fonctions et on lit ce qu'elles écrivent."""
    src = _js()
    assert 'M.api.get("ai-models")' in src, \
        "l'écran ne lit pas la route qui porte les tarifs"
    r = _banc_ecran(tmp_path, [
        {"nom": "tabule", "modeles": MODELES_ESPION, "model": "flux",
         "meta": {"tarif_source": "la table de tarifs de l'application"}},
        {"nom": "hors_table", "modeles": MODELES_ESPION, "model": "sans-tarif",
         "meta": {"tarif_source": "la table de tarifs de l'application"}},
        {"nom": "sans_cle", "modeles": [], "model": "", "meta": {}},
    ])
    # 1. LE TARIF DANS L'ÉTIQUETTE DU MENU — avant d'ouvrir quoi que ce soit
    opts = r["tabule"]["options"]
    assert "0,003 $/image" in opts, opts
    assert "tarif non tabulé" in opts, \
        "un modèle hors table doit le DIRE dans son étiquette"
    assert "0,01" not in opts, "un montant emprunté à un autre modèle"
    # 2. LE COÛT DU CLIC — un MONTANT, pas un compte
    cout = r["tabule"]["cout"]
    assert "Coût de ce clic" in cout and "0,003 $" in cout, cout
    assert "1 image" not in cout.replace("1 × 0,003 $", ""), \
        "« 1 image » est un compte, pas un coût"
    assert "la table de tarifs de l'application" in cout, \
        "la provenance du tarif n'est pas dite"
    assert "fal" in cout, "le fournisseur qui facture n'est pas nommé"
    # ... un modèle absent de la table n'affiche AUCUN montant
    assert "$" not in r["hors_table"]["cout"], r["hors_table"]["cout"]
    assert "Tarif non tabulé" in r["hors_table"]["cout"]
    # ... et sans clé, l'écran le dit AVANT de laisser cliquer
    assert "Aucun modèle" in r["sans_cle"]["cout"], r["sans_cle"]["cout"]
    assert "$" not in r["sans_cle"]["cout"]
    # 3. APRÈS LA DÉPENSE : mesuré par le banc de génération, plus bas.
    assert "facturés chez" in src, "rien n'est dit APRÈS la dépense"
    # ... et AUCUN montant écrit en dur dans la pièce
    bloc = _js_fn(src, "decorCostLine") + _js_fn(src, "decorModelOptions")
    assert not re.search(r"\$\s*\d", bloc), bloc


BANC_INVITE = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { decorPrompt: decorPrompt, DECOR_PROMPT_DEFAUT: DECOR_PROMPT_DEFAUT };"
  + "\n})();")();
const out = [];
for (const c of CAS.cas) {
  try {
    out.push({ nom: c.nom, ok: true,
      texte: mod.decorPrompt(c.preset, c.modeles),
      defaut: mod.DECOR_PROMPT_DEFAUT });
  } catch (e) { out.push({ nom: c.nom, ok: false, err: String((e && e.stack) || e) }); }
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_invite(tmp_path, cas: list) -> dict:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de l'invite ne peut pas tourner")
    src = _js()
    # `decorPrompt` est une FONCTION PURE de (preset, catalogue) : la tranche
    # extraite se réduit à elle et à l'invite neutre qu'elle rend. Rien du
    # module n'est évalué — ni `CF.register`, ni un seul painter.
    i = src.index("  const DECOR_PROMPT_DEFAUT = ")
    fin = _js_fn(src, "decorPrompt")
    js = tmp_path / "invite.js"
    js.write_text(src[i:src.index(fin) + len(fin)], encoding="utf-8")
    banc = tmp_path / "banc_invite.mjs"
    banc.write_text(BANC_INVITE, encoding="utf-8")
    conf = tmp_path / "cas_invite.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x for x in json.loads(r.stdout)}


def test_l_invite_est_PRE_REMPLIE_par_l_archetype_actif(tmp_path):
    """Spec §6.3 : « prompt pré-rempli par l'archétype actif ». La provenance
    d'un jeu est écrite dans `doc.type.preset` sous la forme « modele:<id> »
    (models.py, ronde T3) — un preset SANS préfixe n'est PAS un modèle, même
    s'il en porte le nom : c'est un gabarit local, et deviner est exactement ce
    qui a produit le défaut que ce préfixe a fermé.

    Ce que le modèle apporte est son `hint` : la phrase qui décrit le design.
    Sans modèle, une invite NEUTRE — jamais un champ vide qui laisse
    l'utilisateur devant une page blanche avant une dépense."""
    from app.services.cards import models as MO
    superstar = MO.model("superstar")
    # les quatre champs que `CF.models()` porte VRAIMENT — `custom` compris :
    # c'est lui qui sépare le `hint` de STYLE d'une usine du `hint`
    # ADMINISTRATIF d'un perso (voir le test suivant).
    modeles = [{"id": m["id"], "label": m["label"], "hint": m["hint"],
                "custom": m["custom"]} for m in MO.catalogue()["models"]]
    res = _banc_invite(tmp_path, [
        {"nom": "modele", "preset": "modele:superstar", "modeles": modeles},
        {"nom": "gabarit", "preset": "superstar", "modeles": modeles},
        {"nom": "aucun", "preset": "", "modeles": modeles},
        {"nom": "inconnu", "preset": "modele:jamais-vu", "modeles": modeles},
        {"nom": "sans_liste", "preset": "modele:superstar", "modeles": []},
    ])
    r = res["modele"]
    assert r["ok"], r.get("err")
    assert superstar["hint"][:40] in r["texte"], (superstar["hint"], r["texte"])
    assert superstar["label"] in r["texte"], r["texte"]
    # un preset SANS préfixe est un gabarit, pas un modèle : invite neutre
    for nom in ("gabarit", "aucun", "inconnu", "sans_liste"):
        assert res[nom]["texte"] == res[nom]["defaut"], (nom, res[nom]["texte"])
    assert len(res["aucun"]["defaut"]) > 30, "l'invite neutre est vide"


def test_le_hint_d_un_modele_PERSO_ne_part_JAMAIS_dans_l_invite(tmp_path):
    """LE CHAMP `hint` A DEUX NATURES, ET UNE SEULE EST DU STYLE.

    Chez les SEPT modèles d'usine, `hint` décrit le design — c'est la phrase
    qui a du sens dans une invite. Chez un modèle PERSO, il est fabriqué par
    `models.modele_depuis_deck` et il est purement ADMINISTRATIF :
    « Modèle enregistré depuis « … » le JJ/MM/AAAA. » plus, le cas échéant, les
    notes de purge du verso et du décor — et le tout est coupé au caractère 240
    (`_texte` tranche, il ne résume pas), donc EN PLEIN MOT. Aucune route ne
    permet de l'éditer : ce n'est pas une phrase de style qu'un utilisateur
    aurait écrite, c'est une étiquette de rangement.

    L'injecter verbatim faisait donc partir une date et un rappel de purge
    tronqué dans une invite QUI DÉPENSE, à 100 % des modèles perso — c'est-à-
    dire dans le flux exact du modèle `deepotus-fragments`. La garde saute le
    `hint` quand le modèle résolu est perso et retombe sur l'invite neutre ;
    l'usine, elle, garde le sien."""
    from app.services.cards import models as MO
    # UN MODÈLE PERSO RÉEL, avec ses deux purges — donc son hint le plus long
    did = _api("POST", "/api/cards/decks",
               json={"model": "arcane"}).json()["deck"]["id"]
    cadre = dict(FR.archetype_frame("arcane"))
    cadre["back"] = "custom"
    cadre["back_image"] = "img:img_1.png"
    cadre["decor"] = {"src": "img:gen_ab12cd34.png", "alpha": 0.5}
    _api("PATCH", f"/api/cards/{did}", json={"frame": cadre})
    m = _api("POST", "/api/cards/models",
             json={"did": did, "name": "Mon Jeu"}).json()["model"]
    p = MO.models_root() / f"{m['id']}.json"
    try:
        hint = m["hint"]
        # LE FAIT DONT LA GARDE DÉPEND, épinglé plutôt qu'affirmé
        assert m["custom"] is True, m
        assert hint.startswith("Modèle enregistré depuis"), hint
        assert len(hint) == 240, \
            f"le hint perso ne sature plus le cap : {len(hint)}"
        assert not hint.rstrip().endswith("."), \
            f"le hint perso n'est plus coupé en plein mot : ...{hint[-40:]!r}"
        modeles = [{"id": x["id"], "label": x["label"], "hint": x["hint"],
                    "custom": x.get("custom", False)}
                   for x in MO.catalogue()["models"]]
        assert any(x["id"] == m["id"] for x in modeles), \
            "le modèle perso n'est pas au catalogue que l'écran lit"
        res = _banc_invite(tmp_path, [
            {"nom": "perso", "preset": "modele:" + m["id"], "modeles": modeles},
            {"nom": "usine", "preset": "modele:superstar", "modeles": modeles},
        ])
        # 1. LE PERSO NE POLLUE RIEN : ni la date, ni la note de purge tronquée
        t = res["perso"]["texte"]
        assert t == res["perso"]["defaut"], t
        for fuite in ("Modèle enregistré", "/2026", "purge", "ré-importer",
                      "Mon Jeu"):
            assert fuite not in t, (fuite, t)
        # 2. L'USINE GARDE LE SIEN — la garde vise le perso, pas le hint
        u = res["usine"]["texte"]
        assert u != res["usine"]["defaut"], u
        assert MO.model("superstar")["hint"][:40] in u, u
    finally:
        p.unlink()


def test_la_generation_passe_par_LE_CORE_et_ne_paie_qu_UNE_FOIS():
    """`CF.images.generate` est le SEUL dehors qui dépense (règle 17) : la
    pièce ne pose aucun `fetch` libre, et un clic = un appel."""
    src = _js()
    corps = _js_fn(src, "decorGenerate")
    assert "CF.images.generate(" in corps, corps
    assert len(re.findall(r"CF\.images\.generate\(", src)) == 1, \
        "la génération part de plus d'un endroit"
    assert not re.search(r"\bfetch\s*\(", src), "fetch libre dans la pièce"
    assert 'M.busy(true' in corps and "M.busy(false)" in corps, \
        "le clic qui dépense ne dit pas qu'il travaille"
    assert '"img:" + files[0]' in corps, \
        "l'image générée ne devient pas la source du décor"




# ── 18.5 LA GÉNÉRATION, AVEC UN ESPION : zéro appel réel, zéro dollar ────────
#
# La seule action de cet écran qui DÉPENSE. Elle n'est jamais jouée pour de
# vrai ici : `CF.images.generate` est remplacé par un ESPION qui note la
# requête et rend une réponse fabriquée. Ce que le test juge est ce que le
# produit ENVOIE et ce qu'il FAIT du retour — pas ce qu'un fournisseur répond.

BANC_GENERE = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));

const out = [];
for (const c of CAS.cas) {
  const j = { requetes: [], toasts: [], busy: [], ecrit: [], charges: [] };
  const UI = { decorPrompt: { value: c.prompt, focus: () => {} },
    decorModel: { value: c.model } };
  const M = {
    toast: (t, err) => j.toasts.push([String(t), !!err]),
    busy: (b, t) => j.busy.push([!!b, String(t || "")]),
    invalidate: () => {},
  };
  const CF = { images: { generate: async (req) => {
    j.requetes.push(req);
    if (c.echec) throw new Error("crédit épuisé");
    return { images: c.images, model: c.rendu };
  } } };
  const setDecor = (p, lab) => j.ecrit.push([p, lab]);
  const loadFrameImg = async (f, mag) => { j.charges.push([f, mag]); };
  const fn = new Function("UI", "M", "CF", "AI_MODELS", "setDecor",
    "loadFrameImg", CODE + "\nreturn decorGenerate;")(
    UI, M, CF, c.modeles || [], setDecor, loadFrameImg);
  try { await fn(); } catch (e) { j.leve = String((e && e.message) || e); }
  out.push({ nom: c.nom, j: j });
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_genere(tmp_path, cas: list) -> dict:
    """`decorGenerate` joué avec un ESPION à la place du générateur. Le code
    est le SOURCE LIVRÉ de la fonction, plus `usdFmt` dont elle se sert : rien
    n'est réécrit ici, et AUCUN appel ne part vers un fournisseur."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de génération ne peut pas tourner")
    src = _js()
    # `_js_fn` accroche « function <nom>( » : le mot-clé `async` reste devant,
    # hors de la tranche. On le remet, comme le banc d'empilement le fait pour
    # `layers` — sans lui la fonction extraite n'a plus le droit d'attendre.
    code = _js_fn(src, "usdFmt") + "\nasync " + _js_fn(src, "decorGenerate")
    js = tmp_path / "genere.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_genere.mjs"
    banc.write_text(BANC_GENERE, encoding="utf-8")
    conf = tmp_path / "cas_genere.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x["j"] for x in json.loads(r.stdout)}


def test_la_generation_envoie_UNE_requete_et_pose_l_image_sur_le_cadre(tmp_path):
    """Le flux P1, verbatim : une invite, UN appel, l'image posée, la dépense
    dite APRÈS avec le MÊME tarif qu'avant le clic.

    ZÉRO DOLLAR : le générateur est un espion. Ce qu'on mesure est la forme de
    la requête et ce que le produit fait du retour."""
    res = _banc_genere(tmp_path, [
        {"nom": "ok", "prompt": " volutes dorées ", "model": "flux",
         "images": ["gen_ab12cd34.png", "gen_zz.png"], "rendu": "flux",
         "modeles": MODELES_ESPION},
        {"nom": "sans_invite", "prompt": "   ", "model": "flux",
         "images": ["x.png"], "modeles": MODELES_ESPION},
        {"nom": "vide", "prompt": "des runes", "model": "flux",
         "images": [], "modeles": MODELES_ESPION},
        {"nom": "echec", "prompt": "des runes", "model": "flux",
         "images": [], "echec": True, "modeles": MODELES_ESPION},
        {"nom": "hors_table", "prompt": "des runes", "model": "sans-tarif",
         "images": ["gen_1.png"], "rendu": "sans-tarif",
         "modeles": MODELES_ESPION},
    ])
    j = res["ok"]
    assert len(j["requetes"]) == 1, j["requetes"]
    req = j["requetes"][0]
    assert req["prompt"] == "volutes dorées", req
    assert req["n"] == 1, "un décor, pas quatre : chaque image est facturée"
    assert req["model"] == "flux" and req["size"], req
    # l'image générée devient la source du décor — et elle seule
    assert j["ecrit"] == [[{"src": "img:gen_ab12cd34.png"}, "décor de cadre"]],         j["ecrit"]
    # ... relue dans le magasin de l'APPLICATION, pas dans le dossier du jeu
    assert j["charges"] == [["gen_ab12cd34.png", "app"]], j["charges"]
    assert j["busy"][0][0] is True and j["busy"][-1][0] is False, j["busy"]
    dit = " ".join(t[0] for t in j["toasts"])
    assert "0,003" in dit and "fal" in dit, dit
    # UNE INVITE VIDE NE DÉPENSE PAS
    assert res["sans_invite"]["requetes"] == [], res["sans_invite"]
    assert res["sans_invite"]["toasts"][0][1] is True
    # zéro image rendue, ou un échec du fournisseur : dit, et rien n'est écrit
    for nom in ("vide", "echec"):
        assert res[nom]["ecrit"] == [], (nom, res[nom])
        assert res[nom]["toasts"][-1][1] is True, (nom, res[nom]["toasts"])
        assert res[nom]["busy"][-1][0] is False, "le voyant reste allumé"
    assert "crédit épuisé" in res["echec"]["toasts"][-1][0]
    # UN MODÈLE HORS TABLE N'AFFICHE AUCUN MONTANT — pas celui d'un autre
    dit2 = " ".join(t[0] for t in res["hors_table"]["toasts"])
    assert "$" not in dit2, dit2


# ── 18.6 LE MODÈLE : le décor voyage en RÉGLAGE, jamais en OCTETS ────────────

def test_le_decor_est_ADMIS_a_la_liste_blanche_des_modeles():
    """La clé `decor` traverse la liste blanche — qui DÉRIVE des habillages
    d'archétype (interaction 3a-F1). Une clé de cadre ajoutée à P2 et oubliée
    dans les sept habillages serait REFUSÉE sans que rien ne le dise."""
    from app.services.cards import models as MO
    assert "decor" in MO._FRAME_CLES, sorted(MO._FRAME_CLES)
    for nom in ("superstar", "arcane", "gravee"):
        hab = FR.archetype_frame(nom)
        assert hab["decor"] == FR.DECOR_DEFAULTS, (nom, hab.get("decor"))
    # ... en copie PROFONDE : deux archétypes ne partagent pas un sous-objet
    a, b = FR.archetype_frame("superstar"), FR.archetype_frame("arcane")
    a["decor"]["alpha"] = 0.123
    assert b["decor"]["alpha"] == FR.DECOR_DEFAULTS["alpha"]
    assert FR.archetype_frame("superstar")["decor"]["alpha"] \
        == FR.DECOR_DEFAULTS["alpha"], "la table de module a été écrite"
    # ... ET DANS LA TABLE ELLE-MÊME, pas seulement dans la copie servie.
    # `archetype_frame` recopie en sortie, donc un sous-objet PARTAGÉ entre les
    # sept entrées de `ARCHETYPE_FRAMES` ne se voit pas de l'extérieur — jusqu'à
    # ce qu'un appelant touche la table (elle est publique, comme `LIMITS`) et
    # empoisonne les sept d'un coup. C'est la leçon `window`/`seal` de la T1,
    # et elle vaut pour la clé neuve.
    t = FR.ARCHETYPE_FRAMES
    assert t["superstar"]["decor"] is not t["arcane"]["decor"], \
        "les sept habillages partagent un seul sous-objet `decor`"
    assert len({id(v["decor"]) for v in t.values()}) == len(t), \
        "deux habillages partagent le même `decor`"


# ═══════ 19. LA HUITIÈME FAMILLE ET « ADOPTER LA BORDURE » (phase 4, T4) ════
#
# CE QUE CETTE SECTION VERROUILLE, et pourquoi chaque contrôle existe.
#
# §7.1.5 donne à P2 un geste : « adopter la bordure » — famille et réglages
# LES PLUS PROCHES d'une bordure MESURÉE par la pièce 10, avec l'ÉCART AVOUÉ.
# §9.1 en fait une exigence chiffrée : « l'écart famille↔mesure est celui
# affiché ». Trois façons de se tromper, trois contrôles :
#
#   1. LA TABLE PEUT ÊTRE INVENTÉE. `FAMILY_TRAITS` prétend décrire ce que
#      chaque famille DESSINE ; on rejoue donc la mesure sur les vrais
#      peintres et on compare (§ « les traits sont la MESURE du rendu »).
#   2. LES DEUX CÔTÉS PEUVENT DÉRIVER. Le catalogue est en double, et un
#      test de TEXTE ne verrait pas deux calculs qui divergent sur une
#      valeur limite. La parité se prend donc À L'EXÉCUTION : les deux
#      sources tournent sur le MÊME banc de mesures et doivent rendre la
#      même famille et la MÊME PHRASE.
#   3. LA PHRASE PEUT MENTIR. Chaque chiffre affiché est recalculé ici,
#      au même arrondi et dans la même unité (le DEGRÉ pour un angle).

def _js_const(src: str, nom: str) -> str:
    """Le SOURCE d'une const fléchée d'une ligne (`const cl = (v,a,b) => …;`)."""
    m = re.search(r"^  const " + nom + r" = .*?;$", src, re.M)
    assert m, f"const {nom} introuvable dans mod-frame.js"
    return m.group(0)


def _bloc_js(src: str) -> str:
    """Le bloc CF-FRAME-CATALOG, ÉVALUABLE. Les deux marqueurs vivent dans un
    commentaire : la tranche extraite s'ouvre sur la fin de l'un et se ferme
    sur le début de l'autre. On la referme des deux côtés plutôt que de la
    raboter — le bloc évalué reste celui du dépôt, à l'octet près."""
    return "/*" + _catalog_block(src) + "*/"


HUITIEME = "filigrane"


def test_la_huitieme_famille_existe_des_deux_cotes():
    """Une famille n'existe que si les DEUX catalogues la portent ET si les
    trois tables JS-seules la connaissent : `FAM_FN` (le dessin), `WIN_SHAPE`
    (la forme de fenêtre), `PROFILE` (les cinq signatures de silhouette). Une
    entrée de menu sans peintre, c'est un cadre qui rend l'image d'une AUTRE
    famille. C'est le patron exact de la septième (`gravure`, 3a)."""
    src = _js()
    ids = [f["id"] for f in FR.FAMILIES]
    assert HUITIEME in ids, f"familles backend : {ids}"
    assert (HUITIEME, "Filigrane à instruments") \
        in _js_list(_catalog_block(src), "FAMILIES")
    assert re.search(r"const FAM_FN = \{[^}]*" + HUITIEME + r": famFiligrane",
                     src), f"{HUITIEME} n'a pas de peintre dans FAM_FN"
    assert re.search(r"const WIN_SHAPE = \{[^}]*" + HUITIEME + r": \"\w+\"",
                     src), f"{HUITIEME} n'a pas de forme de fenêtre"
    assert "function famFiligrane(" in src, "le peintre famFiligrane n'existe pas"
    rows = {r[0]: r for r in _profile_rows(src)}
    assert HUITIEME in rows, f"{HUITIEME} n'a pas de profil de silhouette"
    # les cinq colonnes NEUVES, nommées (le test générique les vérifie déjà
    # colonne par colonne pour les huit)
    assert rows[HUITIEME][1] == "filets", rows[HUITIEME]
    assert rows[HUITIEME][3] == "medaillon", rows[HUITIEME]
    assert rows[HUITIEME][4] == "tablette", rows[HUITIEME]
    assert rows[HUITIEME][7] == "orfevre", rows[HUITIEME]
    # ... et les branches qui les servent EXISTENT (une colonne sans branche
    # rendrait la famille muette là où les sept autres dessinent)
    # UNE branche, et une seule : `in` ne compte pas, et une famille dont la
    # grammaire apparaît deux fois dans la même fonction a un `else if` mort
    # quelque part. On compte.
    for quoi, branche in (("ringZone", 'pr.zone === "orfevre"'),
                          ("famProfile", 'pr.kind === "filets"'),
                          ("winMoulding", 'pr.moulure === "medaillon"'),
                          ("platePath", 'k === "tablette"'),
                          ("plateTrim", 'pr.plaque === "tablette"')):
        n = _js_fn(src, quoi).count(branche)
        assert n == 1, \
            f"{quoi} porte {n} branche(s) pour {HUITIEME} ({branche}) — " \
            f"il en faut exactement une"


def test_le_double_filet_du_filigrane_est_a_2_1_et_3_2_mm():
    """L'ANATOMIE DU PATRIARCHE, écrite en millimètres et non en `edge_mm`.
    Spec §7.2 : « filets à ~2,1 et ~3,2 du bord ». Ces deux distances sont
    celles de la CARTE, pas des curseurs de l'utilisateur — un filet posé par
    `edge_mm` bougerait au premier réglage."""
    src = _js()
    m = re.search(r"const FIL_MM = \[([\d.]+), ([\d.]+)\];", src)
    assert m, "FIL_MM absent de mod-frame.js"
    assert (float(m.group(1)), float(m.group(2))) == (2.1, 3.2), m.group(0)
    corps = _js_fn(src, "famFiligrane")
    assert "FIL_MM[0]" in corps and "FIL_MM[1]" in corps, \
        "le peintre ne pose pas ses filets aux distances nommées"
    # les instruments sont des CHEMINS, jamais des glyphes : une police
    # absente rendrait un rectangle vide dans le fichier livré
    for nom in ("insCompas", "insSextant", "insPlume"):
        assert f"function {nom}(" in src, f"instrument {nom} absent"
        ins = _js_fn(src, nom)
        assert "fillText" not in ins and "font" not in ins, \
            f"{nom} passe par une police au lieu d'un tracé"


# ── 19.1 LE BANC DE MESURE DES TRAITS ───────────────────────────────────────
#
# Le rastériseur de contrôle de la §15.2, avec DEUX ajouts que la mesure des
# traits exige et que la mesure de couverture n'exigeait pas :
#
#   · LES COULEURS. `teinte_h` n'a pas de sens sur un masque binaire. Chaque
#     `fill`/`stroke` compose sa couleur sur le fond (blanc), les dégradés
#     valant la moyenne de leurs arrêts — le banc ne juge donc pas un ton
#     précis, il juge une TEINTE, qui est ce que la table publie.
#   · LA LARGEUR DU TRAIT. Le rastériseur de la §15.2 marque UNE cellule par
#     point de chemin, quelle que soit `lineWidth`. Ici cela FAUSSERAIT LA
#     MESURE : le front de 0,9 mm que la pièce 10 relève sur sept familles est
#     la LÈVRE DE RELIEF, un trait de 0,55 mm de large. Réduite à une cellule,
#     elle deviendrait un accident de banc au lieu d'une bande. `lineWidth`
#     est donc honoré.
#
# Le second module (`modS`, l'anneau plat retiré de la source) reste chargé :
# il ne sert plus la table — la voie de production l'a remplacée — mais le
# rastériseur l'expose et le contrôle négatif s'en sert.

BANC_TRAITS = r"""
import { readFileSync, writeFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const EXPORTS = "\nreturn { st: st, model: model, winMM: winMM, FAMILIES: FAMILIES,"
  + " PROFILE: PROFILE, WIN_SHAPE: WIN_SHAPE, FAM_FN: FAM_FN,"
  + " famProfile: famProfile, ringZone: ringZone, winMoulding: winMoulding,"
  + " platePath: platePath, plateTrim: plateTrim, winPath: winPath,"
  + " bandPaint: bandPaint, pal: pal, mix: mix, rgba: rgba };\n})();";
const SANS = CODE.replace("    ringZone(ctx, m, f);", "    /* hors mesure */");
if (SANS === CODE) { throw new Error("l'appel a ringZone n'a pas ete trouve"); }
const modS = new Function("return (function(){ " + SANS + EXPORTS)();
const mod = new Function("return (function(){ " + CODE + EXPORTS)();

const N_BEZ = 12, N_ARC = 20;
function parseCol(s) {
  if (!s) return null;
  s = String(s);
  let m = /^rgba?\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*(?:,\s*([-\d.]+)\s*)?\)$/.exec(s);
  if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
  m = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(s);
  if (m) {
    const t = m[1].length === 3
      ? m[1][0] + m[1][0] + m[1][1] + m[1][1] + m[1][2] + m[1][2] : m[1];
    const n = parseInt(t, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1];
  }
  return null;
}
function Grad() { this.stops = []; }
Grad.prototype.addColorStop = function (p, c) { this.stops.push(c); };
function colOf(v) {
  if (v && v.stops) {
    let r = 0, g = 0, b = 0, a = 0, n = 0;
    for (const s of v.stops) {
      const c = parseCol(s);
      if (!c) continue;
      r += c[0]; g += c[1]; b += c[2]; a += c[3]; n++;
    }
    return n ? [r / n, g / n, b / n, a / n] : null;
  }
  return parseCol(v);
}
function Rec(W, H, GW, GH) {
  this.W = W; this.H = H; this.GW = GW; this.GH = GH;
  this.cov = new Uint8Array(GW * GH);
  this.covF = new Uint8Array(GW * GH);
  this.R = new Float64Array(GW * GH).fill(255);
  this.G = new Float64Array(GW * GH).fill(255);
  this.B = new Float64Array(GW * GH).fill(255);
  this.msk = new Uint8Array(GW * GH).fill(1);
  this.stk = []; this.t = { sx: 1, sy: 1, tx: 0, ty: 0 };
  this.sub = []; this.cur = null; this.ops = 0; this.plein = false;
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
Rec.prototype.arcTo = function (x1, y1, x2, y2) {
  this.lineTo(x1, y1); this.lineTo(x2, y2);
};
Rec.prototype.arc = function (cx, cy, r, a0, a1) {
  for (let i = 0; i <= N_ARC; i++) {
    const a = a0 + (a1 - a0) * i / N_ARC;
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    if (i === 0 && !this.cur) this.moveTo(x, y); else this.lineTo(x, y);
  }
};
Rec.prototype.ellipse = function (cx, cy, rx, ry, rot, a0, a1) {
  const ca = Math.cos(rot || 0), sa = Math.sin(rot || 0);
  for (let i = 0; i <= N_ARC; i++) {
    const a = a0 + (a1 - a0) * i / N_ARC;
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
Rec.prototype._ink = function (q, col) {
  const ga = (this.globalAlpha == null) ? 1 : this.globalAlpha;
  const a = Math.max(0, Math.min(1, col[3] * ga));
  if (a <= 0.002) return;
  this.R[q] = this.R[q] * (1 - a) + col[0] * a;
  this.G[q] = this.G[q] * (1 - a) + col[1] * a;
  this.B[q] = this.B[q] * (1 - a) + col[2] * a;
  if (a >= 0.25) { this.cov[q] = 1; if (this.plein) this.covF[q] = 1; }
};
Rec.prototype._raster = function (eo, brut, col) {
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
        if (brut) { this._m[q] = 1; continue; }
        if (this.msk[q] && col) this._ink(q, col);
      }
    }
  }
};
Rec.prototype._trace = function (col) {
  const GW = this.GW, GH = this.GH;
  const cw = this.W / GW, ch = this.H / GH;
  const pas = Math.min(cw, ch) * 0.5;
  const marque = (x, y) => {
    const r = Math.max(0, (Number(this.lineWidth) || 0) / 2);
    const g0x = Math.floor((x - r) / cw), g1x = Math.floor((x + r) / cw);
    const g0y = Math.floor((y - r) / ch), g1y = Math.floor((y + r) / ch);
    for (let gy = Math.max(0, g0y); gy <= Math.min(GH - 1, g1y); gy++) {
      for (let gx = Math.max(0, g0x); gx <= Math.min(GW - 1, g1x); gx++) {
        const cx = (gx + 0.5) * cw, cy = (gy + 0.5) * ch;
        if (r > 0 && Math.hypot(cx - x, cy - y) > r + Math.min(cw, ch) * 0.5) continue;
        const q = gy * GW + gx;
        if (this.msk[q] && col) this._ink(q, col);
      }
    }
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
  this.ops++; this.plein = true;
  this._raster(rule === "evenodd", false, colOf(this.fillStyle));
  this.plein = false;
};
Rec.prototype.stroke = function () { this.ops++; this._trace(colOf(this.strokeStyle)); };
Rec.prototype.clip = function (rule) {
  this._m = new Uint8Array(this.GW * this.GH);
  this._raster(rule === "evenodd", true, null);
  for (let i = 0; i < this._m.length; i++) if (!this._m[i]) this.msk[i] = 0;
};
Rec.prototype.fillRect = function (x, y, w, h) {
  this.beginPath(); this.rect(x, y, w, h); this.fill();
};
Rec.prototype.strokeRect = function (x, y, w, h) {
  this.beginPath(); this.rect(x, y, w, h); this.stroke();
};
Rec.prototype.createLinearGradient = function () { return new Grad(); };
Rec.prototype.createRadialGradient = function () { return new Grad(); };
Rec.prototype.createPattern = function () { return null; };
Rec.prototype.drawImage = function () {};
Rec.prototype.setLineDash = function () {};
Rec.prototype.fillText = function () {};
Rec.prototype.strokeText = function () {};
Rec.prototype.measureText = function () { return { width: 0 }; };

function teinte(r, g, b) {
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  if (d < 1e-9) return -1;
  let h;
  if (mx === r) h = ((g - b) / d) % 6;
  else if (mx === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  h *= 60;
  return (h % 360 + 360) % 360;
}
function mediane(a) {
  if (!a.length) return 0;
  const b = a.slice().sort((x, y) => x - y);
  return b[Math.floor(b.length / 2)];
}
function geomDe(c) {
  return Object.assign({}, c.g, { mm2px: (v) => v / 25.4 * c.g.dpi });
}
function toileDe(m, g, GW, GH, source, f, shape) {
  const k = new Rec(g.canvas_px[0], g.canvas_px[1], GW, GH);
  k.beginPath(); k.rect(0, 0, k.W, k.H);
  mod.winPath(k, m, shape); k.clip("evenodd");
  k.save();
  source.famProfile(k, m, f);
  const fn = source.FAM_FN[f.family];
  if (fn) fn(k, m, f);
  k.restore();
  return k;
}
/* LA CARTE, dans l'ordre de `paintFront` : le corps (la matiere de bande),
   la signature de famille, la moulure, la plaque. Ce qui MANQUE, et pourquoi
   c'est dit : `matter()` (trames, patine, usures) est un GRAIN par pixel que
   ce rasteriseur ne sait pas representer honnetement — et le detecteur de
   front de la piece 10 RELEVE son plancher avec le bruit du profil, donc un
   faux grain deplacerait la mesure au lieu de l'affiner. On mesure la carte
   SANS son grain, et la table le dit. */
function carteDe(m, g, GW, GH, f, shape) {
  const k = new Rec(g.canvas_px[0], g.canvas_px[1], GW, GH);
  const u = g.mm2px(1), p = mod.pal(f);
  k.beginPath(); k.rect(0, 0, k.W, k.H); mod.winPath(k, m, shape);
  k.fillStyle = mod.bandPaint(k, m, f);
  k.fill("evenodd");
  k.save();
  k.beginPath(); k.rect(0, 0, k.W, k.H); mod.winPath(k, m, shape);
  k.clip("evenodd");
  mod.famProfile(k, m, f);
  const fn = mod.FAM_FN[f.family];
  if (fn) fn(k, m, f);
  mod.winMoulding(k, m, f, shape);
  k.restore();
  if (f.plate && m.plate.h > u * 6) {
    k.save();
    k.globalAlpha = f.plate_alpha;
    const gr = k.createLinearGradient(0, m.plate.y, 0, m.plate.y + m.plate.h);
    gr.addColorStop(0, mod.mix(p.plate, "#ffffff", 0.10));
    gr.addColorStop(1, p.plate);
    k.fillStyle = gr;
    mod.platePath(k, m, f); k.fill();
    k.globalAlpha = 1;
    k.strokeStyle = mod.rgba(p.line, 0.35);
    k.lineWidth = Math.max(0.5, u * 0.16);
    mod.platePath(k, m, f); k.stroke();
    mod.plateTrim(k, m, f);
    k.restore();
  }
  return k;
}

/* ── 1. LES RENDUS : la carte de chaque famille, en OCTETS ──────────────────
   Le banc ne mesure plus rien ici. Il RASTERISE, écrit les octets, et laisse
   la pièce 10 les mesurer avec SES analyseurs : c'est la voie de production,
   la seule dont l'unité soit celle du relevé qui entrera par la frontière. */
const rendus = [];
for (const c of (CAS.rendus || [])) {
  const g = geomDe(c);
  const f = mod.st({ frame: c.frame });
  const m = mod.model(g, f);
  const shape = mod.WIN_SHAPE[f.family] || "rect";
  const GW = c.gw, GH = c.gh, T = m.trim;
  const k = carteDe(m, g, GW, GH, f, shape);
  const buf = Buffer.allocUnsafe(GW * GH * 3);
  for (let q = 0; q < GW * GH; q++) {
    buf[q * 3] = Math.max(0, Math.min(255, Math.round(k.R[q])));
    buf[q * 3 + 1] = Math.max(0, Math.min(255, Math.round(k.G[q])));
    buf[q * 3 + 2] = Math.max(0, Math.min(255, Math.round(k.B[q])));
  }
  writeFileSync(c.fichier, buf);
  const px = (v, tot, n) => Math.round(v / tot * n);
  rendus.push({
    nom: c.nom, famille: f.family, fichier: c.fichier, w: GW, h: GH,
    /* LA COUPE, en cellules : c'est elle qu'un import verrait — une photo de
       carte ne porte pas le fond perdu. */
    coupe: [px(T.x, k.W, GW), px(T.y, k.H, GH),
      px(T.x + T.w, k.W, GW), px(T.y + T.h, k.H, GH)],
  });
}

/* ── 2. LES SILHOUETTES, en GRIS NORMALISÉ, toutes les paires ───────────── */
function grayNorm(k) {
  const n = k.GW * k.GH, o = new Float64Array(n);
  let mn = 1e9, mx = -1e9;
  for (let i = 0; i < n; i++) {
    const v = 0.299 * k.R[i] + 0.587 * k.G[i] + 0.114 * k.B[i];
    o[i] = v; if (v < mn) mn = v; if (v > mx) mx = v;
  }
  const s = (mx - mn) || 1;
  for (let i = 0; i < n; i++) o[i] = (o[i] - mn) / s * 255;
  return o;
}
const sil = { paires: [], min: null };
if (CAS.silhouettes) {
  const S = CAS.silhouettes;
  const g = geomDe(S);
  const GW = S.gw, GH = S.gh;
  for (const ra of S.raretes) {
    const gris = {};
    for (const fa of S.familles) {
      const f = mod.st({ frame: { family: fa, rarity: ra } });
      const m = mod.model(g, f);
      const shape = mod.WIN_SHAPE[fa] || "rect";
      const k = toileDe(m, g, GW, GH, mod, f, shape);
      k.save();
      mod.winMoulding(k, m, f, shape);
      k.restore();
      if (f.plate && m.plate.h > g.mm2px(1) * 6) {
        mod.platePath(k, m, f); k.fill(); mod.plateTrim(k, m, f);
      }
      gris[fa] = grayNorm(k);
    }
    for (let i = 0; i < S.familles.length; i++) {
      for (let j = i + 1; j < S.familles.length; j++) {
        const a = gris[S.familles[i]], b = gris[S.familles[j]];
        let s = 0;
        for (let q = 0; q < a.length; q++) s += Math.abs(a[q] - b[q]);
        sil.paires.push({ a: S.familles[i], b: S.familles[j], rarete: ra,
          d: Math.round(s / a.length * 100) / 100 });
      }
    }
  }
  for (const p of sil.paires) if (sil.min === null || p.d < sil.min) sil.min = p.d;
}
process.stdout.write(JSON.stringify({ rendus: rendus, silhouettes: sil }));
"""


def _banc_traits(tmp_path, cas: dict, code: str | None = None) -> dict:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc des traits ne peut pas tourner")
    js = tmp_path / "traits.js"
    js.write_text(code if code is not None else _painter_js_source(),
                  encoding="utf-8")
    banc = tmp_path / "banc_traits.mjs"
    banc.write_text(BANC_TRAITS, encoding="utf-8")
    conf = tmp_path / "cas_traits.json"
    conf.write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=600)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


# ── LA VOIE DE PRODUCTION, ET POURQUOI LA PREMIÈRE TABLE ÉTAIT FAUSSE ───────
#
# La première écriture mesurait, sur le rendu, l'ÉPAISSEUR TYPIQUE de la marque
# que chaque famille pose. C'est une grandeur honnête, et elle ne sert à rien :
# ce qui entre par la frontière, c'est `doc.capture.border.mm`, et celui-là est
# la PROFONDEUR DU PREMIER FRONT depuis le bord. Deux grandeurs sous le même
# nom. MESURÉ par la revue en rendant chaque famille et en la passant dans la
# vraie voie : 2 familles sur 8 se reconnaissaient.
#
# La table se mesure donc PAR LA VOIE QUI LA CONSOMMERA — le banc rastérise,
# écrit les octets, et `cards.capture` les mesure avec SES analyseurs. Elle
# parle désormais la langue de son entrée, et l'axe s'appelle ce qu'il est :
# `front_mm`, pas « bande ». (Le mot « bande » reste dans la PHRASE affichée :
# c'est le mot de l'écran, celui de la spec §7.1.5, et le curseur qui reçoit
# la mesure s'appelle « Marge intérieure (bande) ».)
TRAITS_CELL = 0.1              # 0,1 mm : la coupe fait 630 x 880 px
TRAITS_FMT = "poker_eu"


def _cas_rendus(tmp_path, familles=None):
    g = _geom_js(TRAITS_FMT, 3)
    tw, th = CT.FORMATS[TRAITS_FMT]["trim_mm"]
    gw, gh = round((tw + 6) / TRAITS_CELL), round((th + 6) / TRAITS_CELL)
    ids = familles if familles is not None else [f["id"] for f in FR.FAMILIES]
    return [{"nom": i, "g": g, "frame": {"family": i}, "gw": gw, "gh": gh,
             "fichier": str(tmp_path / f"rendu_{i}.rgb")} for i in ids]


def _traits_mesures(tmp_path, familles=None, code=None) -> dict:
    """Chaque famille RENDUE, puis mesurée par les analyseurs de la PIÈCE 10.

    `cards.capture` est importée en LECTURE SEULE — c'est le module de la
    pièce voisine, jamais modifié ici. C'est le seul moyen d'avoir la même
    unité des deux côtés de la frontière."""
    from PIL import Image

    from app.services.cards import capture as CAP
    cas = _cas_rendus(tmp_path, familles)
    res = _banc_traits(tmp_path, {"rendus": cas}, code)
    tw = CT.FORMATS[TRAITS_FMT]["trim_mm"][0]
    out = {}
    for r in res["rendus"]:
        octets = pathlib.Path(r["fichier"]).read_bytes()
        im = Image.frombytes("RGB", (r["w"], r["h"]), octets)
        # LA COUPE, ET RIEN QU'ELLE : une photo de carte ne porte pas le fond
        # perdu, et c'est une photo de carte que la pièce 10 reçoit.
        im = im.crop(tuple(r["coupe"]))
        mm_par_px = tw / float(im.size[0])
        notes = []
        b, _ep = CAP._analyse_bordure(im, mm_par_px, notes)
        out[r["famille"]] = {
            "border": b, "notes": notes,
            "front_mm": None if b is None else b["mm"],
            "color": None if b is None else b["color"],
            "teinte_h": None if b is None else FR.teinte_de(b["color"]),
            "saturation": None if b is None else FR.saturation_de(b["color"]),
        }
    return out


def test_les_traits_sont_la_MESURE_de_la_VOIE_DE_PRODUCTION(tmp_path):
    """`FAMILY_TRAITS` PRÉTEND décrire ce que la pièce 10 mesurera sur une
    carte de cette famille. Ici on le rejoue PAR LA VOIE RÉELLE : les huit
    familles sont rendues par leurs vrais peintres, les octets sont recadrés
    à la coupe, et ce sont les analyseurs de `cards.capture` — pas une
    reformulation — qui rendent le relevé.

    AUCUNE TOLÉRANCE SUR LE FRONT. `_analyse_bordure` rend un multiple entier
    de `mm_par_px` (0,1 mm ici) : la mesure est exacte et reproductible, et
    une tolérance ne servirait qu'à cacher une table fausse. La ronde l'a
    montré en échangeant deux valeurs voisines de l'ancienne table : elles
    tenaient dans la tolérance et le choix de famille changeait quand même.
    La teinte, elle, est comparée à 0,05° — la moitié du dernier chiffre
    STOCKÉ, rien de plus.

    Relevé du jour (poker 300 DPI, cellules de 0,1 mm, DEFAULTS) :
      runic 0,9 / #08121d / 211,4    arcane 0,9 / #08121d / 211,4
      timber 0,9 / #86a3c3 / 211,5   deco   0,9 / #08121d / 211,4
      neon  3,2 / #1c4067 / 211,2    sable  0,9 / #90a5bb / 210,7
      gravure 0,9 / #acaba5 / 51,4   filigrane 0,9 / #9d8650 / 42,1"""
    mes = _traits_mesures(tmp_path)
    assert set(mes) == set(FR.FAMILY_TRAITS), \
        f"mesurées {sorted(mes)} / table {sorted(FR.FAMILY_TRAITS)}"
    for fid, t in FR.FAMILY_TRAITS.items():
        m = mes[fid]
        assert m["border"] is not None, \
            f"{fid} : la pièce 10 REFUSE de mesurer cette carte — {m['notes']}"
        assert m["front_mm"] == t["front_mm"], \
            f"{fid} : front mesuré {m['front_mm']} mm, table {t['front_mm']}"
        if t["teinte_h"] is None:
            assert m["teinte_h"] is None, \
                f"{fid} : la table dit « sans teinte », la mesure dit " \
                f"{m['teinte_h']}° (saturation {m['saturation']})"
        else:
            assert m["teinte_h"] is not None, \
                f"{fid} : teinte refusée (saturation {m['saturation']:.4f}) " \
                f"alors que la table porte {t['teinte_h']}°"
            assert abs(m["teinte_h"] - t["teinte_h"]) <= 0.05, \
                f"{fid} : teinte mesurée {m['teinte_h']}, table {t['teinte_h']}"


def test_le_banc_des_traits_VOIT_une_table_fausse(tmp_path):
    """LE CONTRÔLE NÉGATIF. Un banc qui ne peut pas rougir ne prouve rien : on
    retire la LÈVRE DE RELIEF de `ringZone` — celle qui fait le front de
    0,9 mm chez sept familles sur huit — et le front mesuré DOIT changer.
    (Mutation sur la COPIE du banc, jamais sur le dépôt.)"""
    code = _painter_js_source()
    ancre = 'ctx.strokeStyle = "rgba(255,255,255,.16)";'
    assert code.count(ancre) == 1, "la lèvre de relief a changé de forme"
    mut = code.replace(ancre, 'ctx.strokeStyle = "rgba(255,255,255,0)";')
    sain = _traits_mesures(tmp_path, ["runic"])["runic"]
    mort = _traits_mesures(tmp_path, ["runic"], mut)["runic"]
    assert sain["front_mm"] == FR.FAMILY_TRAITS["runic"]["front_mm"], sain
    assert mort["front_mm"] != sain["front_mm"], \
        f"retirer la lèvre ne change pas le front mesuré : {mort}"


# ── 19.1bis L'ALLER-RETOUR : ce que la pièce 10 rend, P2 le reconnaît-il ? ──
#
# LE CONTRÔLE QUI MANQUAIT, ET QUI A FAIT TOMBER LA PREMIÈRE TABLE. Une table
# de traits peut être exacte et INUTILE : il suffit qu'elle mesure une autre
# grandeur que celle qui entre par la frontière. On ferme donc la boucle —
# rendre la famille, la faire mesurer par la pièce 10, donner le relevé à
# `famille_proche` — et l'on épingle l'issue HONNÊTE, y compris là où elle est
# négative. Prétendre une reconnaissance que la géométrie interdit serait
# exactement le badge menteur que ce dépôt refuse partout ailleurs.

ALLER_RETOUR = {
    # celles qui se reconnaissent, et POURQUOI
    "neon": "neon",          # seule à ne pas porter la lèvre : front 3,2
    "sable": "sable",        # sa teinte s'écarte de 0,7° des trois jumelles
    "timber": "timber",      # 0,1° — le plus mince écart qui décide encore
    "gravure": "gravure",    # ivoire : teinte chaude, loin des froides
    "filigrane": "filigrane",  # or : la plus chaude des huit
    "runic": "runic",        # première du groupe froid : elle gagne l'égalité
    # celles que la mesure NE PEUT PAS distinguer : même front, même couleur
    # au bit près (#08121d). Elles tombent sur la première du groupe.
    "arcane": "runic",
    "deco": "runic",
}
INDISCERNABLES = {"arcane", "deco"}


def test_l_ALLER_RETOUR_de_la_piece_10_vers_P2(tmp_path):
    """Chaque famille rendue → mesurée par la pièce 10 → adoptée par P2.

    SIX FAMILLES SUR HUIT se reconnaissent. Les deux autres (Arcane, Art déco)
    rendent EXACTEMENT le même relevé que Runique — même front de 0,9 mm, même
    couleur de lisière #08121d — et aucune distance ne sépare deux points
    confondus. Elles tombent sur la première du groupe, et la PHRASE le dit :
    c'est le contrat, pas un accident."""
    mes = _traits_mesures(tmp_path)
    obtenu, avoue = {}, {}
    for fid, m in mes.items():
        ch = FR.famille_proche(m["front_mm"], m["teinte_h"])
        obtenu[fid] = ch["id"]
        avoue[fid] = FR.phrase_ecart(m["front_mm"], m["teinte_h"], ch)
    assert obtenu == ALLER_RETOUR, obtenu
    reconnues = {k for k, v in obtenu.items() if k == v}
    assert len(reconnues) == 6, sorted(reconnues)
    # LES INDISCERNABLES SONT VRAIMENT INDISCERNABLES — on le PROUVE au lieu
    # de le supposer : leur relevé est identique à celui de la famille qui les
    # rafle, front ET couleur.
    for fid in INDISCERNABLES:
        assert mes[fid]["front_mm"] == mes[obtenu[fid]]["front_mm"], fid
        assert mes[fid]["color"] == mes[obtenu[fid]]["color"], \
            f"{fid} rend {mes[fid]['color']}, {obtenu[fid]} rend " \
            f"{mes[obtenu[fid]]['color']} — elles sont donc séparables"
    # ... ET LA PHRASE AVOUE. Pas de reconnaissance annoncée là où le
    # catalogue a tranché par son ordre.
    for fid in INDISCERNABLES | {"runic"}:
        assert "voisine" in avoue[fid], (fid, avoue[fid])
        assert "le catalogue retient la première" in avoue[fid], avoue[fid]
    for fid in ("neon", "gravure", "filigrane"):
        assert "voisine" not in avoue[fid], (fid, avoue[fid])


def test_le_cas_PATRIARCHE_tombe_sur_le_filigrane():
    """L'ORACLE CHAUD (§7.2, D9). Une bordure d'or de 2,1 mm — l'anatomie du
    Patriarche — doit choisir « Filigrane à instruments ». C'est le cas d'usage
    NOMMÉ de la huitième famille ; s'il tombe ailleurs, la famille ne sert à
    rien. On vérifie aussi la marge : la deuxième est loin."""
    h = FR.teinte_de("#d8b76a")
    ch = FR.famille_proche(2.1, h)
    assert ch["id"] == "filigrane", (ch, h)
    assert not ch["voisines"], \
        f"le choix n'est pas net : {ch['voisines']}"
    # ... et l'or reste l'or sur toute la plage du dossier fabricant
    for hexa in ("#8a6a2e", "#d8b76a", "#c9992f", "#a5813a"):
        c = FR.famille_proche(2.1, FR.teinte_de(hexa))
        assert c["id"] == "filigrane", (hexa, c["id"])
    # ... tandis qu'un or PÂLE (l'ivoire de l'estampe) va bien chez Gravure
    assert FR.famille_proche(2.1, FR.teinte_de("#acaba5"))["id"] != "filigrane"


def test_les_huit_silhouettes_restent_deux_a_deux_distinctes(tmp_path):
    """LA QA DE SILHOUETTES, EN PAIRWISE 8 x 8. Le badge de l'écran mesure la
    même chose au navigateur (`SIL_SEUIL = 4` / 255 sur gris normalisé) ; il
    n'est pas dans la suite. On la mesure ici sur le rastériseur de contrôle,
    en COULEUR, sur les mêmes étapes de signature (profil, dessin, moulure,
    plaque) et les six raretés : 28 paires x 6 = 168 mesures.

    LE SEUIL NE BOUGE PAS. Une famille qui passe dessous se REDESSINE — c'est
    la règle écrite dans mod-frame.js depuis la septième, et la huitième ne
    l'assouplit pas. On mesure DEUX minimums : celui des sept familles
    d'avant, et celui des huit. Si le second est plus bas, c'est la famille
    neuve qui tire le catalogue vers le bas, et c'est elle qu'on redessine.

    NB : ces chiffres ne sont PAS ceux du badge (qui rend la toile livrée à
    815 x 1110 avec la matière et le texte par-dessus). Ils sont plus élevés,
    parce que ce banc ne peint que les couches de famille — la comparaison
    qui compte ici est AVANT/APRÈS, à méthode constante.

    RELEVÉ, à méthode constante (0,25 mm de cellule, poker 300 DPI) :
      · SEPT familles, 126 mesures : minimum 31,60 / 255
        (« Runique x Art déco » en Rare)
      · PREMIER JET de la huitième — anneau noir à lisière d'or + moulure de
        fenêtre en jonc plein : 22,43, et la paire la plus serrée devenait
        « Gravure x Filigrane ». Au-dessus du seuil, mais la famille NEUVE
        tirait le catalogue vers le bas. Deux redessins mesurés : l'anneau en
        TROIS bandes (or / chenal noir / or) -> 23,01 (presque rien : ce
        n'était pas là que ça se jouait), puis la moulure de fenêtre passée
        du jonc plein à QUATRE MÉDAILLONS discrets -> 33,90.
      · HUIT familles, 168 mesures : minimum 31,60 / 255, « Runique x Art
        déco » en Rare — EXACTEMENT la paire et la valeur d'avant. La
        huitième famille ne coûte rien au catalogue."""
    src = _js()
    m = re.search(r"const SIL_SEUIL = (\d+);", src)
    assert m, "SIL_SEUIL absent de mod-frame.js"
    seuil = float(m.group(1))
    assert seuil == 4, "le seuil de silhouettes a bougé — re-mesurer avant"
    g = _geom_js(TRAITS_FMT, 3)
    tw, th = CT.FORMATS[TRAITS_FMT]["trim_mm"]
    cell = 0.25
    res = _banc_traits(tmp_path, {"traits": [], "silhouettes": {
        "g": g, "gw": round((tw + 6) / cell), "gh": round((th + 6) / cell),
        "familles": [f["id"] for f in FR.FAMILIES],
        "raretes": [r["id"] for r in FR.RARITIES]}})
    paires = res["silhouettes"]["paires"]
    n = len(FR.FAMILIES)
    assert len(paires) == n * (n - 1) // 2 * len(FR.RARITIES), len(paires)
    pire = min(paires, key=lambda p: p["d"])
    sans = [p for p in paires
            if p["a"] != HUITIEME and p["b"] != HUITIEME]
    pire7 = min(sans, key=lambda p: p["d"])
    assert pire["d"] >= seuil, \
        f"paire trop proche : {pire} (seuil {seuil}) — c'est la SILHOUETTE " \
        f"qui doit changer, pas le seuil"
    # LA HUITIÈME NE COÛTE RIEN AU CATALOGUE : le minimum des huit est celui
    # des sept. C'est une exigence PLUS DURE que le seuil, et c'est elle qui a
    # fait redessiner la famille deux fois (voir le relevé ci-dessus) — sans
    # elle, une famille neuve peut diviser l'écart par deux et rester verte.
    assert pire["d"] >= pire7["d"] - 0.01, \
        f"la huitième famille tire le catalogue vers le bas : " \
        f"{pire} contre {pire7} sans elle"
    assert pire7["d"] == pytest.approx(31.60, abs=0.05), \
        f"le catalogue à sept a bougé : {pire7} — re-mesurer avant de recopier"


# ── 19.2 LE BANC D'ADOPTION : les deux sources jouées, pas relues ───────────

BANC_ADOPTION = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = new Function("return (function(){ " + CODE
  + "\nreturn { teinteDe: teinteDe, satDe: satDe, rgbDe: rgbDe,"
  + " ecartTeinte: ecartTeinte, traitsEchelles: traitsEchelles,"
  + " familleProche: familleProche, mm1: mm1, nb2: nb2,"
  + " phraseEcart: phraseEcart, bordureLue: bordureLue,"
  + " adoptionBordure: adoptionBordure, FAMILY_TRAITS: FAMILY_TRAITS,"
  + " PROCHE_EPS: PROCHE_EPS, SAT_MIN: SAT_MIN };\n})();")();
const out = { echelles: mod.traitsEchelles(), traits: mod.FAMILY_TRAITS,
  eps: mod.PROCHE_EPS, sat_min: mod.SAT_MIN,
  teintes: [], mesures: [], bordures: [] };
for (const c of (CAS.teintes || [])) {
  out.teintes.push({ hex: c, h: mod.teinteDe(c), s: mod.satDe(c) });
}
for (const m of (CAS.mesures || [])) {
  const h = (m.teinte_h === undefined) ? null : m.teinte_h;
  const ch = mod.familleProche(m.mm, h);
  out.mesures.push({ nom: m.nom, id: ch.id, d: ch.d, d_front: ch.d_front,
    d_teinte: ch.d_teinte, voisines: ch.voisines,
    phrase: mod.phraseEcart(m.mm, h, ch) });
}
for (const b of (CAS.bordures || [])) {
  const bo = mod.bordureLue(b.border);
  if (!bo) { out.bordures.push({ nom: b.nom, lue: null }); continue; }
  const a = mod.adoptionBordure(bo, b.win);
  out.bordures.push({ nom: b.nom, lue: bo, famille: a.famille,
    patch: a.patch, ecart: a.ecart, precisions: a.precisions });
}
process.stdout.write(JSON.stringify(out));
"""


def _adoption_js_source() -> str:
    """LE CALCUL D'ADOPTION, extrait TEL QUEL : le bloc miroir en entier, plus
    les fonctions qui l'emploient. Aucune réimplémentation — une
    réimplémentation prouverait la réimplémentation."""
    src = _js()
    return "\n".join([_bloc_js(src), _js_const(src, "cl"),
                      _js_const(src, "r2"), _js_const(src, "CONF_FAIBLE"),
                      _js_fn(src, "nb2"), _js_fn(src, "nbLu"),
                      _js_fn(src, "bordureLue"),
                      _js_fn(src, "adoptionBordure")])


def _banc_adoption(tmp_path, cas: dict, mutations=()) -> dict:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'adoption ne peut pas tourner")
    code = _adoption_js_source()
    for avant, apres in mutations:
        assert avant in code, f"mutation introuvable : {avant!r}"
        code = code.replace(avant, apres)
    js = tmp_path / "adoption.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_adoption.mjs"
    banc.write_text(BANC_ADOPTION, encoding="utf-8")
    conf = tmp_path / "cas_adoption.json"
    # L'INFINI NE TRAVERSE PAS JSON. `json.dumps(float("inf"))` écrit
    # `Infinity`, que `JSON.parse` refuse ; et c'est justement la valeur que
    # `isFinite` existe pour arrêter. On la fait passer par un jeton, remplacé
    # par le littéral que JavaScript, lui, lit comme l'infini.
    conf.write_text(json.dumps(cas).replace('"@INF@"', "1e999"),
                    encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


# LE BANC DE MESURES : fronts de 0,5 à 6 mm, teintes tout autour du cercle —
# LE TOUR (350 contre 10, que la spec §9.2 appelle par son nom) et LES DEUX
# CRÊTES, ces relevés qui tombent pile entre deux familles et où un dixième de
# degré change la réponse. Les crêtes sont là parce que la ronde a montré
# qu'un « témoin survivant » choisi sans elles avait une raison FAUSSE :
# déplacer une teinte de 0,7° passait pour inoffensif alors qu'il basculait le
# choix sur toute une crête.
MESURES_BANC = [
    {"nom": "fine-or", "mm": 0.5, "teinte_h": 45.0},
    {"nom": "mince-ivoire", "mm": 0.9, "teinte_h": 55.0},
    {"nom": "patriarche", "mm": 2.1, "teinte_h": 43.0},
    {"nom": "moyenne-bleue", "mm": 2.4, "teinte_h": 211.0},
    {"nom": "moyenne-verte", "mm": 2.6, "teinte_h": 140.0},
    {"nom": "large-rouge", "mm": 3.2, "teinte_h": 10.0},
    {"nom": "large-magenta", "mm": 4.0, "teinte_h": 300.0},
    {"nom": "tres-large", "mm": 6.0, "teinte_h": 200.0},
    {"nom": "tour-350", "mm": 2.1, "teinte_h": 350.0},
    {"nom": "tour-010", "mm": 2.1, "teinte_h": 10.0},
    {"nom": "tour-355-fine", "mm": 0.6, "teinte_h": 355.0},
    {"nom": "sans-teinte", "mm": 3.0, "teinte_h": None},
    {"nom": "bord-zero", "mm": 0.05, "teinte_h": 0.0},
    {"nom": "bord-360", "mm": 5.0, "teinte_h": 359.9},
    # LES DEUX CRÊTES, mesurées : à 210,9° Épure gagne d'un dixième sur
    # Runique ; à 211,35° Runique gagne d'un vingtième sur Bois sculpté.
    {"nom": "crete-sable", "mm": 0.9, "teinte_h": 210.9},
    {"nom": "crete-timber", "mm": 0.9, "teinte_h": 211.35},
]
# LES COULEURS DU BANC : les ors et les noirs de la spec, les primaires, les
# formes REFUSÉES, et — depuis la ronde — les GRIS À 1 LSB qui choisissaient
# une famille au hasard, plus les trois formes de dièse que `replace` de
# JavaScript et `replace` de Python ne lisaient PAS pareil.
TEINTES_BANC = ["#d8b76a", "#8a6a2e", "#f7f0dd", "#2b5f96", "#0f2338",
                "#c0c0c0", "#000000", "#ffffff", "#ff0000", "#00ff00",
                "#0000ff", "#010200", "#fe0001", "abc", "#abc", "",
                "#GGGGGG", "#12345", "  #D8B76A  ",
                "#6a6b6c", "#6c6b6a", "#282a28", "#acaba5", "#08121d",
                "##d8b76a", "###abc", "d8b76a#"]


def test_les_traits_et_le_plus_proche_sont_les_memes_des_deux_cotes(tmp_path):
    """LA PARITÉ, PRISE À L'EXÉCUTION (§9.2). Pas une comparaison de textes :
    les deux sources tournent sur le MÊME banc de 16 relevés et 27 couleurs,
    et doivent rendre la même famille, la même distance, les mêmes voisines et
    la MÊME PHRASE.

    Une comparaison de textes ne verrait pas deux `%` qui ne se comportent pas
    pareil — `-1 % 6` vaut -1 en JavaScript et 5 en Python, et la formule de
    teinte y passe dès que le bleu domine. Elle ne verrait pas non plus deux
    `replace` qui ne remplacent pas le même nombre d'occurrences : « ##d8b76a »
    traversait d'un côté et pas de l'autre."""
    res = _banc_adoption(tmp_path, {"teintes": TEINTES_BANC,
                                    "mesures": MESURES_BANC})
    assert res["traits"] == FR.FAMILY_TRAITS, \
        f"FAMILY_TRAITS diverge : JS {res['traits']} / py {FR.FAMILY_TRAITS}"
    assert res["eps"] == FR.PROCHE_EPS
    assert res["sat_min"] == FR.SAT_MIN
    e = FR.traits_echelles()
    assert res["echelles"]["front"] == pytest.approx(e["front"])
    assert res["echelles"]["teinte"] == pytest.approx(e["teinte"])
    for row in res["teintes"]:
        py, js = FR.teinte_de(row["hex"]), row["h"]
        if py is None or js is None:
            assert py is None and js is None, (row["hex"], js, py)
        else:
            assert js == pytest.approx(py, abs=1e-9), (row["hex"], js, py)
        pys, jss = FR.saturation_de(row["hex"]), row["s"]
        if pys is None or jss is None:
            assert pys is None and jss is None, (row["hex"], jss, pys)
        else:
            assert jss == pytest.approx(pys, abs=1e-12), (row["hex"], jss, pys)
    assert len(res["mesures"]) == len(MESURES_BANC) >= 10
    for row in res["mesures"]:
        m = [x for x in MESURES_BANC if x["nom"] == row["nom"]][0]
        py = FR.famille_proche(m["mm"], m["teinte_h"])
        assert row["id"] == py["id"], (row["nom"], row["id"], py["id"])
        assert row["d"] == pytest.approx(py["d"], abs=1e-9), row["nom"]
        assert row["voisines"] == py["voisines"], row["nom"]
        assert row["phrase"] == FR.phrase_ecart(m["mm"], m["teinte_h"], py), \
            row["nom"]


def test_les_trois_formes_de_diese_se_lisent_pareil():
    """`replace` de JavaScript ne remplace QUE LA PREMIÈRE occurrence ; celui
    de Python les remplace toutes. MESURÉ par la ronde : « ##d8b76a » rendait
    42,0° d'un côté et rien de l'autre — cinq formes divergeaient, toutes hors
    du banc d'alors. Les deux côtés emploient maintenant une forme GLOBALE, et
    les trois formes sont au banc."""
    src = _js()
    assert 'replace(/#/g, "")' in _js_fn(src, "rgbDe"), \
        "le JS ne retire pas TOUS les dièses"
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert '.replace("#", "")' in _py_fn(py, "_rgb_de"), \
        "le Python a changé de forme : re-mesurer la parité"
    for hexa in ("##d8b76a", "###abc", "#d8b76a"):
        assert FR.teinte_de(hexa) is not None, hexa
    assert FR.teinte_de("##d8b76a") == pytest.approx(42.0)
    assert FR.teinte_de("###abc") == FR.teinte_de("#abc")


def test_la_teinte_circulaire_est_indispensable(tmp_path):
    """MUTATION. `min(d, 360 - d)` retiré : une bordure à 350° cesse d'être à
    52° de l'or du filigrane (42,1°) et passe à 308. MESURÉ sur le banc — la
    famille choisie CHANGE, et la phrase change de chiffre avec elle. Les deux
    chiffres sont RECALCULÉS ici, jamais recopiés."""
    cas = {"mesures": [m for m in MESURES_BANC
                       if m["nom"] in ("tour-350", "tour-355-fine",
                                       "patriarche")]}
    sain = {r["nom"]: r for r in _banc_adoption(tmp_path, cas)["mesures"]}
    mut = {r["nom"]: r for r in _banc_adoption(tmp_path, cas, mutations=[
        ("return d > 180 ? 360 - d : d;", "return d;")])["mesures"]}
    assert sain["tour-350"]["id"] == "filigrane", sain["tour-350"]
    assert mut["tour-350"]["id"] != sain["tour-350"]["id"], \
        f"la distance circulaire ne change RIEN : {mut['tour-350']}"
    h8 = FR.FAMILY_TRAITS["filigrane"]["teinte_h"]
    court = math.floor(FR.ecart_teinte(350.0, h8) + 0.5)          # 52
    long_ = math.floor(abs(350.0 - h8) + 0.5)                     # 308
    assert court < 90 < long_, (court, long_)
    assert f"teinte à {court}°" in sain["tour-350"]["phrase"], \
        sain["tour-350"]["phrase"]
    assert f"teinte à {court}°" not in mut["tour-350"]["phrase"], \
        mut["tour-350"]["phrase"]
    assert mut["patriarche"]["id"] == sain["patriarche"]["id"]


# ── 19.1ter LE SEUIL DE SATURATION : le gris ne choisit plus au hasard ──────

def test_le_seuil_de_saturation_tombe_dans_le_creux(tmp_path):
    """LES DEUX SEUILS NE SONT PAS DES CHIFFRES RONDS, C'EST UN CREUX MESURÉ.

    Et le SECOND seuil est né ici même. La première écriture n'avait que la
    saturation HSV ; ce test l'a démentie au premier passage : `#141516` est
    un gris à UN LSB près et sa saturation vaut 0,091 — trois fois le seuil.
    Une saturation est RELATIVE au maximum ; dans les tons sombres, deux
    unités de bruit pèsent autant qu'un vrai écart dans les tons clairs. Il
    faut donc les deux : un plancher ABSOLU de chroma (le bruit de
    quantification l'est) et un plancher relatif (un presque-blanc a une
    teinte réelle mais illisible).

    Deux populations, relevées et non supposées :
      · les GRIS — ceux que la ronde a joués (`#6a6b6c`, `#6c6b6a`) et des
        neutres de tous les tons : chroma 0 à 2 ;
      · les DOMINANTES QUE LA VOIE DE PRODUCTION REND VRAIMENT sur les huit
        familles : chroma 7 (l'ivoire de Gravure) à 138.
    La marge est MINCE — 2,5x au-dessus du bruit, 1,4x sous l'ivoire — et
    c'est écrit ici plutôt que caché : l'ivoire de « Gravure » est la teinte
    la moins certaine des huit, et si un jour son anneau change, ce test
    rougit avant l'utilisateur."""
    def chroma(h):
        c = FR._rgb_de(h)
        return max(c) - min(c)
    GRIS = ("#6a6b6c", "#6c6b6a", "#808080", "#c0c0c0", "#ffffff",
            "#000000", "#282a28", "#141516", "#fefdfe", "#010002")
    assert max(chroma(h) for h in GRIS) <= 2, [(h, chroma(h)) for h in GRIS]
    mes = _traits_mesures(tmp_path)
    vraies = [t["color"] for t in mes.values() if t["color"] is not None]
    assert len(vraies) == len(FR.FAMILIES)
    assert max(chroma(h) for h in GRIS) < FR.CHROMA_MIN \
        <= min(chroma(h) for h in vraies), \
        f"le plancher de chroma {FR.CHROMA_MIN} n'est pas dans le creux : " \
        f"gris <= {max(chroma(h) for h in GRIS)}, dominantes >= " \
        f"{min(chroma(h) for h in vraies)}"
    assert FR.SAT_MIN <= min(FR.saturation_de(h) for h in vraies), \
        [(h, round(FR.saturation_de(h), 4)) for h in vraies]
    # AUCUN gris ne garde de teinte, quel que soit son ton — c'est ce que le
    # plancher absolu ajoute, et la saturation seule ne savait pas le faire.
    assert all(FR.teinte_de(h) is None for h in GRIS), \
        [(h, FR.teinte_de(h)) for h in GRIS if FR.teinte_de(h) is not None]
    # ... et le seuil FAIT SON TRAVAIL : les deux gris de la ronde n'ont plus
    # de teinte, donc ils ne choisissent plus deux familles opposées.
    a = FR.famille_proche(0.9, FR.teinte_de("#6a6b6c"))
    b = FR.famille_proche(0.9, FR.teinte_de("#6c6b6a"))
    assert FR.teinte_de("#6a6b6c") is None and FR.teinte_de("#6c6b6a") is None
    assert a["id"] == b["id"], (a["id"], b["id"])


def test_sans_seuil_deux_gris_jumeaux_choisissent_deux_familles(tmp_path):
    """LE CONTRÔLE NÉGATIF DU SEUIL, sur la mutation exacte de la ronde : la
    garde ramenée à l'égalité stricte. Les deux gris redeviennent « teintés »
    et repartent chacun de son côté."""
    cas = {"teintes": ["#6a6b6c", "#6c6b6a"]}
    mut = _banc_adoption(tmp_path, cas, mutations=[
        ("if (d < CHROMA_MIN || (mx && d / mx < SAT_MIN)) return null;",
         "if (d === 0) return null;")])
    t = {r["hex"]: r["h"] for r in mut["teintes"]}
    assert t["#6a6b6c"] is not None and t["#6c6b6a"] is not None, t
    # ... et ces deux teintes-là, données au MÊME choix de famille, partent
    # chacune de son côté : c'est le tirage au sort que le seuil arrête.
    a = FR.famille_proche(0.9, t["#6a6b6c"])["id"]
    b = FR.famille_proche(0.9, t["#6c6b6a"])["id"]
    assert a != b, \
        f"la mutation ne sépare pas les deux gris : {a} / {b} ({t})"
    sain = _banc_adoption(tmp_path, cas)
    assert all(r["h"] is None for r in sain["teintes"]), sain["teintes"]
    assert FR.famille_proche(0.9, None)["id"] \
        == FR.famille_proche(0.9, None)["id"]


# ── 19.3 CE QUE L'ADOPTION ÉCRIT ────────────────────────────────────────────
#
# LE MAPPING, et pourquoi ces clés-là (vérifié à la source, pas supposé) :
#   front mesuré  -> `inner_mm`   (le modèle pose la bande entre la coupe et
#                                  `trim` rentré de `inner_mm` ; le panneau
#                                  l'appelle « Marge intérieure (bande) »)
#   couleur       -> `line_color` + `metal: false` (sinon `inkPaint` rend le
#                                  dégradé métallique et `line_color` n'est
#                                  JAMAIS lu — un réglage qui ne règle rien)
#   rayon         -> `window.r`   (le SEUL rayon de `doc.frame` ; celui de la
#                                  CARTE est `doc.format.corner_mm`, propriété
#                                  de la pièce 00 — P2 ne l'écrit pas)

WIN_BANC = {"x": 6.6, "y": 6.6, "w": 49.8, "h": 44.4, "r": 2.5, "auto": False}
WIN_AUTO = dict(WIN_BANC, auto=True)


def _cas_bordure(nom, border, win=None):
    return {"nom": nom, "border": border, "win": dict(win or WIN_BANC)}


def test_l_adoption_pose_les_reglages_MESURES_clampes_par_LIMITS(tmp_path):
    """Les trois grandeurs mesurées deviennent trois réglages, chacune dans
    SES bornes. Une bordure de 40 mm mesurée sur une image mal cadrée ne doit
    pas écrire 40 dans `inner_mm` : `LIMITS` est la borne, et elle mord."""
    res = _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure("patriarche", {"mm": 2.1, "color": "#d8b76a",
                                    "radius_mm": 3.0, "confidence": 0.82}),
        _cas_bordure("enorme", {"mm": 40.0, "color": "#8a6a2e",
                                "radius_mm": 99.0, "confidence": 1.0}),
        _cas_bordure("negatif", {"mm": 2.0, "color": "#2b5f96",
                                 "radius_mm": -4.0, "confidence": 0.5}),
        _cas_bordure("rayon-nul", {"mm": 2.0, "color": "#2b5f96",
                                   "radius_mm": 0.0, "confidence": 0.5}),
    ]})["bordures"]
    r = {x["nom"]: x for x in res}
    p = r["patriarche"]["patch"]
    assert p["family"] == "filigrane", p
    assert p["inner_mm"] == 2.1, p
    assert p["line_color"] == "#d8b76a" and p["metal"] is False, p
    assert p["window"]["r"] == 3.0, p
    for k in ("x", "y", "w", "h"):
        assert p["window"][k] == WIN_BANC[k], p["window"]
    g = r["enorme"]["patch"]
    assert g["inner_mm"] == FR.LIMITS["inner_mm"][1], g
    assert g["window"]["r"] == FR.LIMITS["win_r_mm"][1], g
    # ... un rayon NÉGATIF n'est pas une mesure hors bornes, c'est une mesure
    # qui n'a pas eu lieu : on ne la ramène pas à 0 (ce serait publier un angle
    # vif que personne n'a vu), on ne pose pas de fenêtre du tout.
    assert r["negatif"]["lue"]["radius_mm"] is None, r["negatif"]["lue"]
    assert "window" not in r["negatif"]["patch"], r["negatif"]
    # ... un rayon de ZÉRO, lui, EST une mesure : des coins vifs se mesurent.
    assert r["rayon-nul"]["patch"]["window"]["r"] == 0.0, r["rayon-nul"]


def test_le_clamp_de_la_bande_SE_DIT_dans_la_phrase(tmp_path):
    """LE CLAMP ÉTAIT MUET, et celui du rayon parlait. MESURÉ par la ronde :
    « bande 25,0 mm ↔ Bois sculpté 3,1 mm » pendant que le document recevait
    20. L'écran annonçait un réglage que le jeu ne portait pas.

    Le test confronte la PHRASE au PATCH : la valeur dite doit être celle
    écrite, sur les deux branches (clampée, non clampée)."""
    res = {x["nom"]: x for x in _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure("clampe", {"mm": 25.0, "color": "", "radius_mm": None}),
        _cas_bordure("dedans", {"mm": 2.0, "color": "", "radius_mm": None}),
    ]})["bordures"]}
    c = res["clampe"]
    borne = FR.LIMITS["inner_mm"][1]
    assert c["patch"]["inner_mm"] == borne, c["patch"]
    assert f"ramenée à {FR._mm1(borne)} mm" in c["precisions"], c["precisions"]
    assert "la borne du curseur" in c["precisions"], c["precisions"]
    # la phrase d'écart, elle, dit la MESURE — c'est son rôle : elle compare
    # ce qui a été mesuré à ce que la famille porte.
    assert c["ecart"].startswith("bande 25,0 mm ↔"), c["ecart"]
    # ... et sans clamp, personne ne parle de borne
    assert "ramenée" not in res["dedans"]["precisions"], res["dedans"]


def test_l_adoption_sans_clamp_ecrirait_hors_bornes(tmp_path):
    """MUTATION : le `cl(...)` de la bande retiré. Une bordure de 40 mm
    passerait telle quelle dans un curseur qui s'arrête à 20."""
    cas = {"bordures": [_cas_bordure("enorme", {"mm": 40.0, "color": "",
                                                "radius_mm": None})]}
    mut = _banc_adoption(tmp_path, cas, mutations=[
        ("const bande = r2(cl(bo.mm, LIMITS.inner_mm[0], LIMITS.inner_mm[1]));",
         "const bande = r2(bo.mm);")])["bordures"][0]
    assert mut["patch"]["inner_mm"] == 40.0, mut
    sain = _banc_adoption(tmp_path, cas)["bordures"][0]
    assert sain["patch"]["inner_mm"] == FR.LIMITS["inner_mm"][1], sain


def test_le_verrou_de_proportions_ne_garde_PAS_le_rayon(tmp_path):
    """CORRECTION DE RONDE. Le premier jet retirait la fenêtre du patch dès que
    `win_lock` était armé. Or `win_lock` est un verrou de PROPORTIONS — son
    libellé le dit et ses trois lectures le font : la hauteur recopie
    l'échelle. Un rayon n'est pas une proportion, et l'adoption ne touche ni
    la largeur ni la hauteur. Le verrou n'a donc rien à garder ici.

    On le vérifie DEUX FOIS : à la source (le verrou n'est plus lu par le
    calcul d'adoption) et au banc (le patch porte la fenêtre)."""
    # le CODE, commentaires retirés : le mot `win_lock` doit encore pouvoir
    # être EXPLIQUÉ dans la prose (il l'est, longuement) sans faire rougir.
    corps = re.sub(r"/\*.*?\*/", " ",
                   _js_fn(_js(), "adoptionBordure"), flags=re.S)
    assert "win_lock" not in corps, \
        "le calcul d'adoption consulte encore le verrou de proportions"
    b = {"mm": 2.1, "color": "#d8b76a", "radius_mm": 3.0, "confidence": 0.9}
    r = _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure("rayon", b)]})["bordures"][0]
    assert r["patch"]["window"]["r"] == 3.0, r["patch"]
    # ... et la LARGEUR comme la HAUTEUR sortent inchangées : c'est ce que le
    # verrou garde, et l'adoption n'y touche pas, verrou ou non.
    assert r["patch"]["window"]["w"] == WIN_BANC["w"], r["patch"]
    assert r["patch"]["window"]["h"] == WIN_BANC["h"], r["patch"]


def test_le_GEL_de_la_fenetre_automatique_est_dit(tmp_path):
    """UNE FENÊTRE « AUTO » SE RE-PROPORTIONNE AU FORMAT ; UNE FOIS POSÉE, NON.
    Mesuré au passage poker -> tarot : 16 mm de hauteur en moins, et
    `publishWindow` gèle la pose de P1 avec. C'est grand, c'est invisible, et
    une phrase suffit — mais elle ne doit apparaître QUE là où elle est vraie."""
    b = {"mm": 2.1, "color": "#d8b76a", "radius_mm": 3.0, "confidence": 0.9}
    res = {x["nom"]: x for x in _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure("auto", b, WIN_AUTO),
        _cas_bordure("manuelle", b, WIN_BANC),
        _cas_bordure("auto-sans-rayon", {"mm": 2.1, "color": "#d8b76a",
                                         "radius_mm": None}, WIN_AUTO),
    ]})["bordures"]}
    assert "cesse de se re-proportionner" in res["auto"]["precisions"], \
        res["auto"]["precisions"]
    assert "Ctrl+Z" in res["auto"]["precisions"]
    assert "cesse de se re-proportionner" not in res["manuelle"]["precisions"], \
        res["manuelle"]["precisions"]
    # ... et sans rayon, la fenêtre n'est pas posée du tout : rien à geler
    assert "cesse de se re-proportionner" \
        not in res["auto-sans-rayon"]["precisions"]
    assert "window" not in res["auto-sans-rayon"]["patch"]


def test_la_confiance_de_la_mesure_est_AFFICHEE(tmp_path):
    """La confiance était calculée par la pièce 10, transportée jusqu'ici, et
    JAMAIS montrée. C'est pourtant la seule chose qui sépare une adoption sûre
    d'une adoption à 21 % — les millimètres, eux, sont les mêmes."""
    res = {x["nom"]: x for x in _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure("sure", {"mm": 2.1, "color": "", "radius_mm": None,
                              "confidence": 0.82}),
        _cas_bordure("faible", {"mm": 2.1, "color": "", "radius_mm": None,
                                "confidence": 0.21}),
        _cas_bordure("sans", {"mm": 2.1, "color": "", "radius_mm": None}),
    ]})["bordures"]}
    assert "confiance 0,82" in res["sure"]["precisions"], res["sure"]
    assert "PEU SÛRE" not in res["sure"]["precisions"]
    assert "PEU SÛRE" in res["faible"]["precisions"], res["faible"]
    assert "0,21" in res["faible"]["precisions"], res["faible"]
    assert res["sans"]["lue"]["confidence"] is None
    assert "confiance" not in res["sans"]["precisions"], res["sans"]


def test_une_bordure_absente_ou_folle_ne_donne_RIEN_a_adopter(tmp_path):
    """LECTURE TOLÉRANTE (règle 3, patron `sectionsBasses`). `doc.capture` est
    la propriété d'une AUTRE pièce : absent, `null`, partiel, ou rempli de
    n'importe quoi, chaque cas rend `null` — et un bloc d'adoption sans
    matière à adopter n'existe pas."""
    hostiles = [
        ("absent", None), ("vide", {}), ("liste", []), ("texte", "beaucoup"),
        ("mm-nul", {"mm": 0, "color": "#d8b76a"}),
        ("mm-negatif", {"mm": -3, "color": "#d8b76a"}),
        ("mm-texte", {"mm": "deux", "color": "#d8b76a"}),
        ("mm-infini", {"mm": "@INF@", "color": "#d8b76a"}),
        ("mm-nul-explicite", {"mm": None, "color": "#d8b76a"}),
    ]
    res = {x["nom"]: x for x in _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure(n, b) for n, b in hostiles]})["bordures"]}
    for n, _b in hostiles:
        assert res[n]["lue"] is None, (n, res[n])
    # ... et une couleur folle ne fait pas tomber le geste : la bande, elle,
    # est mesurable, donc on adopte ce qui est mesuré et rien de plus
    partiel = _banc_adoption(tmp_path, {"bordures": [
        _cas_bordure("couleur-folle", {"mm": 2.1, "color": "rouge vif",
                                       "radius_mm": None}),
        _cas_bordure("couleur-absente", {"mm": 2.1}),
        _cas_bordure("couleur-grise", {"mm": 2.1, "color": "#6a6b6c"}),
    ]})["bordures"]
    for x in partiel[:2]:
        assert x["lue"] is not None, x
        assert x["lue"]["color"] == "", x
        assert "line_color" not in x["patch"], x
        assert "metal" not in x["patch"], x
        assert "non mesurable (gris)" in x["ecart"], x["ecart"]
    # un gris LISIBLE, lui, se pose bien comme couleur — c'est sa TEINTE qui
    # n'existe pas, pas la couleur.
    gris = partiel[2]
    assert gris["patch"]["line_color"] == "#6a6b6c", gris
    assert "non mesurable (gris)" in gris["ecart"], gris["ecart"]


def test_la_phrase_d_ecart_porte_LES_CHIFFRES_DU_CALCUL(tmp_path):
    """§9.1 : « l'écart famille↔mesure est celui affiché ». Chaque nombre de
    la phrase est recalculé ici — le front mesuré, celui de la famille choisie,
    et l'écart de teinte EN DEGRÉS.

    LA PROSE SE MESURE : on ne cherche pas « la phrase contient un nombre »,
    on reconstruit la phrase entière à partir du calcul et on exige
    l'égalité."""
    res = _banc_adoption(tmp_path, {"mesures": MESURES_BANC})["mesures"]
    for row in res:
        m = [x for x in MESURES_BANC if x["nom"] == row["nom"]][0]
        t = FR.FAMILY_TRAITS[row["id"]]
        lab = [f["label"] for f in FR.FAMILIES if f["id"] == row["id"]][0]
        attendu = (f"bande {FR._mm1(m['mm'])} mm ↔ {lab} "
                   f"{FR._mm1(t['front_mm'])} mm")
        if m["teinte_h"] is None and t["teinte_h"] is None:
            attendu += ", ni la mesure ni la famille n'a de teinte"
        elif m["teinte_h"] is None:
            attendu += ", teinte de la mesure non mesurable (gris)"
        elif t["teinte_h"] is None:
            attendu += ", la famille n'a pas de teinte propre"
        else:
            deg = math.floor(
                FR.ecart_teinte(m["teinte_h"], t["teinte_h"]) + 0.5)
            attendu += f", teinte à {deg}°"
        if row["voisines"]:
            s = "s" if len(row["voisines"]) > 1 else ""
            noms = ", ".join(FR._label_de(v) for v in row["voisines"])
            attendu += (f" — {len(row['voisines'])} famille{s} voisine{s} à "
                        f"moins de {FR._mm1(FR.PROCHE_EPS * 100)} % ({noms}) :"
                        f" le catalogue retient la première")
        assert row["phrase"] == attendu, (row["nom"], row["phrase"], attendu)
        if m["teinte_h"] is not None and t["teinte_h"] is not None:
            deg = math.floor(
                row["d_teinte"] * FR.traits_echelles()["teinte"] + 0.5)
            assert f"teinte à {deg}°" in row["phrase"], (row, deg)


def test_la_phrase_d_ecart_est_celle_de_la_spec():
    """L'EXEMPLE DE LA SPEC, joué. §7.1.5 écrit « bande 2,1 mm ↔ famille sable
    2,0 mm, teinte à N » : même forme, même ordre, même flèche. Le LIBELLÉ y
    remplace l'identifiant (« Épure », pas « sable ») — c'est le mot que
    l'utilisateur voit dans la grille des familles juste à côté.

    L'UNITÉ EST LE DEGRÉ, ET L'AMENDEMENT EXISTE. La spec écrivait « 6 % » ;
    la première écriture de ce test affirmait « amendé à la source » alors que
    la source ne l'était pas — une revendication d'amendement se vérifie comme
    un fait. Elle l'est désormais : l'orchestrateur a amendé spec :510 le
    24/08 (commit 9f030be), et ce test LIT le fichier au lieu de le croire."""
    p = FR.phrase_ecart(2.1, 43.0, "sable")
    assert p.startswith("bande 2,1 mm ↔ Épure "), p
    assert " mm, teinte à " in p and p.endswith("°"), p
    assert "%" not in p, "un écart d'angle n'est pas un pourcentage"
    spec = (REPO / "docs" / "superpowers" / "specs"
            / "2026-08-19-cardforge-universel-design.md")
    txt = spec.read_text(encoding="utf-8")
    assert "teinte à 6° »" in txt, \
        "l'amendement de la spec (« % » -> degré) n'est pas dans le fichier"
    assert "l'unité\n     d'un écart de teinte est le degré" in txt, txt[:0]


def test_la_phrase_AVOUE_les_familles_voisines(tmp_path):
    """LA QUASI-ÉGALITÉ SE DIT. Trois familles rendent le même relevé (même
    front, même couleur au bit près) : annoncer « Runique » sans un mot
    laisserait croire à une reconnaissance là où le catalogue a tranché par
    son ORDRE. La phrase nomme les voisines et dit la règle."""
    ch = FR.famille_proche(0.9, 211.4)
    assert ch["id"] == "runic", ch
    assert set(ch["voisines"]) >= {"arcane", "deco"}, ch["voisines"]
    p = FR.phrase_ecart(0.9, 211.4, ch)
    assert "voisines à moins de 2,0 %" in p, p
    assert "Arcane" in p and "Art déco" in p, p
    assert "le catalogue retient la première" in p, p
    # ... et un choix NET ne dit rien de tel
    net = FR.famille_proche(3.2, 211.2)
    assert net["id"] == "neon" and not net["voisines"], net
    assert "voisine" not in FR.phrase_ecart(3.2, 211.2, net)


# ── 19.4 LE NON-DÉPART : sans matière, il n'y a pas de bouton ───────────────
#
# Le verrou de la 3b est un NON-DÉPART : « 0 écouteur posé, rien à dépiler ».
# Ici la même doctrine garde le geste d'adoption — quand `doc.capture.border`
# n'a rien de mesurable, il n'y a pas un bouton grisé qui refuserait, il n'y a
# AUCUN écouteur, donc aucune entrée d'annulation à reprendre.

BANC_ADOPT_DOM = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const out = [];
for (const c of CAS.cas) {
  let ecouteurs = 0;
  const clics = [];
  const patches = [];
  const toasts = [];
  function El(tag) {
    this.tag = tag; this.className = ""; this.innerHTML = "";
    this.title = ""; this.type = ""; this.children = []; this.firstChild = null;
    this._txt = "";
    const s = new Set();
    this.classList = {
      add: (k) => s.add(k), remove: (k) => s.delete(k),
      contains: (k) => s.has(k),
      toggle: (k, on) => { if (on) s.add(k); else s.delete(k); },
      _s: s,
    };
  }
  Object.defineProperty(El.prototype, "textContent", {
    get: function () { return this._txt; },
    set: function (v) {
      this._txt = String(v); this.children = []; this.firstChild = null;
    },
  });
  El.prototype.appendChild = function (n) {
    this.children.push(n);
    this.firstChild = this.children[0];
    return n;
  };
  El.prototype.addEventListener = function (t, fn) {
    ecouteurs++; clics.push({ el: this, type: t, fn: fn });
  };
  El.prototype.querySelector = function () { return null; };
  const document = { createElement: (t) => new El(t) };
  const UI = { adopt: new El("div") };
  const DOC = { capture: c.capture || {}, frame: c.frame || {} };
  const CF = {
    geom: () => c.g,
    doc: () => DOC,
    get: (path, dflt) => {
      const parts = String(path).split(".");
      let cur = DOC;
      for (const p of parts) {
        if (cur === null || typeof cur !== "object"
          || !Object.prototype.hasOwnProperty.call(cur, p)) return dflt;
        cur = cur[p];
      }
      return cur === undefined ? dflt : cur;
    },
  };
  const M = { toast: (t) => toasts.push(String(t)) };
  const f = () => c.frame || {};
  const set = (partial, label) => patches.push({ patch: partial, label: label });
  const mod = new Function("UI", "CF", "M", "f", "set", "document",
    CODE + "\nreturn { renderAdopt: renderAdopt };")(UI, CF, M, f, set, document);
  mod.renderAdopt(c.frame || {}, c.g);
  const avantClic = ecouteurs;
  if (c.clic && clics.length) { clics[0].fn(); }
  const textes = [];
  const marche = (n) => {
    if (!n) return;
    if (n._txt) textes.push(n._txt);
    if (n.innerHTML) textes.push(n.innerHTML);
    (n.children || []).forEach(marche);
  };
  marche(UI.adopt);
  out.push({ nom: c.nom, ecouteurs: avantClic, enfants: UI.adopt.children.length,
    cache: UI.adopt.classList.contains("hidden"), textes: textes,
    patches: patches, toasts: toasts });
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_adopt_dom(tmp_path, cas: list) -> dict:
    """`renderAdopt` JOUÉE, avec ses vraies fabriques de DOM (`h`, `label`,
    `esc`) et son vrai `winMM`. Seul l'environnement est simulé : le document,
    le registre du CORE et l'écriture."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du bloc d'adoption ne peut pas tourner")
    src = _js()
    code = "\n".join([
        _bloc_js(src), _js_const(src, "cl"), _js_const(src, "r2"),
        _js_const(src, "num"), _js_const(src, "CONF_FAIBLE"),
        _js_fn(src, "winMM"), _js_fn(src, "esc"), _js_fn(src, "nb2"),
        _js_fn(src, "h"), _js_fn(src, "label"), _js_fn(src, "nbLu"),
        _js_fn(src, "bordureLue"),
        _js_fn(src, "bordureDuDoc"), _js_fn(src, "adoptionBordure"),
        _js_fn(src, "renderAdopt")])
    js = tmp_path / "adopt_dom.js"
    js.write_text(code, encoding="utf-8")
    banc = tmp_path / "banc_adopt_dom.mjs"
    banc.write_text(BANC_ADOPT_DOM, encoding="utf-8")
    conf = tmp_path / "cas_adopt_dom.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    return {x["nom"]: x for x in json.loads(r.stdout)}


def test_sans_bordure_mesuree_il_n_y_a_AUCUN_ECOUTEUR(tmp_path):
    """LE NON-DÉPART (verrou 3b). Pas de bordure -> pas de bouton -> ZÉRO
    écouteur posé et rien dans le bloc. Un bouton grisé aurait été un bouton
    qui ment, et un écouteur posé « au cas où » serait un geste à défaire.

    Les quatre états de `doc.capture` que la pièce 10 peut produire sont
    joués : jamais analysé, analysé sans bordure trouvée (le refus mesuré de
    §8), bordure partielle, bordure complète."""
    g = _geom_js("poker_eu", 3)
    cas = [
        {"nom": "jamais", "g": g, "capture": {}, "frame": {}},
        {"nom": "sans-bordure", "g": g, "frame": {},
         "capture": {"analyzed": 1770000000000, "border": None}},
        {"nom": "bordure-vide", "g": g, "frame": {},
         "capture": {"analyzed": 1, "border": {}}},
        {"nom": "bordure", "g": g, "frame": {},
         "capture": {"analyzed": 1, "border": {
             "mm": 2.1, "color": "#d8b76a", "radius_mm": 3.0,
             "confidence": 0.82}}},
    ]
    res = _banc_adopt_dom(tmp_path, cas)
    for nom in ("jamais", "sans-bordure", "bordure-vide"):
        r = res[nom]
        assert r["ecouteurs"] == 0, f"{nom} : {r['ecouteurs']} écouteur(s) posé(s)"
        assert r["enfants"] == 0, f"{nom} : le bloc n'est pas vide ({r})"
        assert r["cache"] is True, nom
    r = res["bordure"]
    assert r["ecouteurs"] == 1, f"un seul bouton, un seul écouteur : {r}"
    assert r["enfants"] == 3, r          # titre, rangée du bouton, écart
    assert r["cache"] is False, r
    assert any("Adopter la bordure" in t for t in r["textes"]), r["textes"]
    assert any("bande 2,1 mm ↔" in t for t in r["textes"]), r["textes"]
    assert any("confiance 0,82" in t for t in r["textes"]), r["textes"]


def test_l_adoption_est_UN_SEUL_PAS_D_ANNULATION(tmp_path):
    """Un clic = un `set()` = un `M.patch` = une entrée d'annulation. Quatre
    clés écrites en QUATRE appels donneraient quatre Ctrl+Z pour revenir en
    arrière — le défaut que `set()` existe pour empêcher."""
    g = _geom_js("poker_eu", 3)
    res = _banc_adopt_dom(tmp_path, [{
        "nom": "clic", "g": g, "clic": True,
        "frame": {"window": {k: WIN_BANC[k] for k in ("x", "y", "w", "h", "r")},
                  "win_lock": False},
        "capture": {"analyzed": 1, "border": {
            "mm": 2.1, "color": "#d8b76a", "radius_mm": 3.0,
            "confidence": 0.82}}}])["clic"]
    assert len(res["patches"]) == 1, \
        f"{len(res['patches'])} écritures pour une adoption : {res['patches']}"
    p = res["patches"][0]
    assert p["label"] == "bordure adoptée", p
    assert set(p["patch"]) == {"family", "inner_mm", "line_color", "metal",
                               "window"}, p["patch"]
    assert p["patch"]["family"] == "filigrane", p
    # le toast PORTE l'écart, le même que la ligne du panneau
    assert len(res["toasts"]) == 1, res["toasts"]
    ch = FR.famille_proche(2.1, FR.teinte_de("#d8b76a"))
    assert FR.phrase_ecart(2.1, FR.teinte_de("#d8b76a"), ch) \
        in res["toasts"][0], res["toasts"]
    assert "confiance 0,82" in res["toasts"][0], res["toasts"]


def test_le_bloc_d_adoption_est_repeint_quand_capture_change():
    """La matière n'est pas à nous : `doc.capture` peut naître, changer ou
    disparaître à tout moment. Sans la branche `capture` de l'écouteur du
    CORE, le bouton n'arriverait qu'au prochain réglage du cadre."""
    src = _js()
    m = re.search(r"CF\.on\(\"core:doc\", \(p\) => \{(.*?)\}\);", src, re.S)
    assert m, "l'écouteur core:doc a changé de forme"
    assert 'p.id === "capture"' in m.group(1), \
        "P2 n'écoute pas les publications de la pièce 10"
    # ... et P2 n'ÉCRIT jamais chez la pièce 10 (cloisonnement §7.1.5)
    assert "patchAs" not in src
    assert not re.search(r"M\.patch\(\s*\{\s*capture", src)


def test_le_catalogue_publie_les_traits_mesures():
    """Un choix qu'on ne peut pas recalculer est un choix qu'il faut croire.
    `/catalog` publie donc la table, les deux échelles de la distance et le
    seuil de voisinage.

    ET TOUT SORT EN COPIE PROFONDE. `family_traits` avait la sienne, ses
    voisines non : un appelant qui touchait le dictionnaire rendu écrivait
    dans les tables du module, pour tout le processus. La moitié d'une garde
    n'en est pas une — on le vérifie EN PROFONDEUR, sous-objet compris."""
    cat = FR.catalog()
    assert cat["family_traits"] == FR.FAMILY_TRAITS
    assert set(cat["family_scales"]) == {"front", "teinte"}
    assert cat["family_scales"]["front"] == pytest.approx(2.3)
    assert cat["family_scales"]["teinte"] == pytest.approx(169.4)
    assert cat["family_eps"] == FR.PROCHE_EPS
    # les huit familles ont un trait, et rien qu'elles
    assert set(FR.FAMILY_TRAITS) == {f["id"] for f in FR.FAMILIES}
    for fid, t in FR.FAMILY_TRAITS.items():
        assert set(t) == {"front_mm", "teinte_h"}, (fid, t)
        assert 0 < t["front_mm"] <= FR.LIMITS["inner_mm"][1], (fid, t)
        assert t["teinte_h"] is None or 0 <= t["teinte_h"] < 360, (fid, t)
    # AUCUNE table du module n'est jointe par référence, sous-objets compris
    a, b = FR.catalog(), FR.catalog()
    a["families"][0]["label"] = "PIRATÉ"
    a["family_traits"]["runic"]["front_mm"] = 99
    a["presets"][0]["label"] = "PIRATÉ"
    a["limits"]["inner_mm"][1] = 999
    a["rarities"][0]["id"] = "PIRATÉ"
    a["seal_defaults"]["scope"]["screen"] = "PIRATÉ"
    assert b["families"][0]["label"] != "PIRATÉ"
    assert FR.FAMILIES[0]["label"] != "PIRATÉ"
    assert FR.FAMILY_TRAITS["runic"]["front_mm"] != 99
    assert FR.PRESETS[0]["label"] != "PIRATÉ"
    assert FR.LIMITS["inner_mm"][1] != 999
    assert FR.RARITIES[0]["id"] != "PIRATÉ"
    assert FR.SEAL_DEFAULTS["scope"]["screen"] is True


# ── 19.5 LE BLOC DANS UN VRAI NAVIGATEUR ────────────────────────────────────
#
# Le banc DOM prouve la logique ; il ne prouve pas qu'on VOIT quelque chose.
# Ici la vraie feuille de style et le vrai `renderAdopt` se rencontrent dans un
# Chrome sans tête : le bloc existe, il a une hauteur, il porte ses tokens, et
# il ne pousse pas la largeur de défilement du panneau (le défaut déjà payé
# par `.cff-acts`, mesuré à 160 px de débordement).

BANC_CHROME = r"""
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
const PAGE = process.argv[2];
const CHROME = [process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"]
  .filter(Boolean).find((p) => existsSync(p));
if (!CHROME) { process.stdout.write(JSON.stringify({ skip: "chrome" })); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SONDE = `(() => {
  const el = document.querySelector(".cff-adopt");
  const col = document.querySelector(".cff-colB");
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const bouton = el.querySelector("button");
  const ligne = el.querySelector(".cff-adoptread");
  return {
    enfants: el.children.length,
    hauteur: Math.round(r.height), largeur: Math.round(r.width),
    fond: cs.backgroundColor, bordG: cs.borderLeftWidth,
    couleurLigne: ligne ? getComputedStyle(ligne).color : null,
    bouton: bouton ? bouton.textContent : null,
    ligne: ligne ? ligne.textContent : null,
    debord: col.scrollWidth - col.clientWidth,
    lignePx: ligne ? Math.round(ligne.getBoundingClientRect().width) : 0,
    colPx: Math.round(col.getBoundingClientRect().width),
    erreurs: window.__ERR || [],
  };
})()`;
const port = await new Promise((res, rej) => {
  const s = createServer(); s.on("error", rej);
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); });
});
const profile = join(tmpdir(), "dzcffqa", "p" + port);
try { rmSync(profile, { recursive: true, force: true }); } catch { }
mkdirSync(profile, { recursive: true });
const proc = spawn(CHROME, ["--headless=new", "--disable-gpu",
  "--remote-debugging-port=" + port, "--remote-allow-origins=*",
  "--user-data-dir=" + profile, "--window-size=1200,900", "--no-first-run",
  "--allow-file-access-from-files", "--no-default-browser-check",
  "--disable-background-networking", "--disable-sync", "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"], windowsHide: true });
const cleanup = () => {
  try { spawnSync("taskkill", ["/pid", String(proc.pid), "/T", "/F"], { stdio: "ignore" }); } catch { }
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 3 }); } catch { }
};
process.on("exit", cleanup);
try {
  const fetchJson = async (u, tries = 80) => {
    for (let i = 0; i < tries; i++) {
      try { const r = await fetch(u); if (r.ok) return await r.json(); } catch { }
      await sleep(250);
    }
    throw new Error("injoignable " + u);
  };
  await fetchJson("http://127.0.0.1:" + port + "/json/version");
  let target = null;
  for (let i = 0; i < 60 && !target; i++) {
    const list = await fetchJson("http://127.0.0.1:" + port + "/json/list", 1).catch(() => []);
    target = (list || []).find((t) => t.type === "page" && t.webSocketDebuggerUrl);
    if (!target) await sleep(200);
  }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener("open", res, { once: true });
    ws.addEventListener("error", rej, { once: true });
  });
  let id = 0; const pend = new Map();
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) {
      const p = pend.get(m.id); pend.delete(m.id);
      m.error ? p.rej(new Error(m.error.message)) : p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = ++id; pend.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  await send("Page.enable"); await send("Runtime.enable");
  await send("Page.navigate", { url: "file:///" + PAGE.replace(/\\/g, "/") });
  await sleep(1500);
  const r = await send("Runtime.evaluate", { expression: SONDE, returnByValue: true });
  if (r.exceptionDetails) {
    process.stdout.write(JSON.stringify({ erreur: JSON.stringify(r.exceptionDetails).slice(0, 600) }));
  } else {
    process.stdout.write(JSON.stringify(r.result.value));
  }
} finally { cleanup(); }
"""


def _page_adopt(tmp_path, border: dict) -> pathlib.Path:
    """La page MINIMALE : les vrais tokens, la VRAIE feuille de P2, et le VRAI
    `renderAdopt` qui construit le bloc. Rien n'est recopié — ni le balisage
    ni la CSS."""
    src = _js()
    code = "\n".join([
        _bloc_js(src), _js_const(src, "cl"), _js_const(src, "r2"),
        _js_const(src, "num"), _js_const(src, "CONF_FAIBLE"),
        _js_fn(src, "winMM"), _js_fn(src, "esc"), _js_fn(src, "nb2"),
        _js_fn(src, "h"), _js_fn(src, "label"), _js_fn(src, "nbLu"),
        _js_fn(src, "bordureLue"), _js_fn(src, "bordureDuDoc"),
        _js_fn(src, "adoptionBordure"), _js_fn(src, "renderAdopt")])
    tokens = (REPO / "frontend" / "shared" / "deepotus.tokens.css").as_uri()
    css = CSS.as_uri()
    g = _geom_js("poker_eu", 3)
    page = tmp_path / "adopt.html"
    page.write_text(
        "<!doctype html><meta charset=\"utf-8\">"
        f"<link rel=\"stylesheet\" href=\"{tokens}\">"
        f"<link rel=\"stylesheet\" href=\"{css}\">"
        "<body style=\"margin:0;background:var(--bg-app,#111)\">"
        "<div class=\"cf-frame\" style=\"width:708px\">"
        "<div class=\"cff-cols\"><div class=\"cff-colB\" style=\"width:340px\">"
        "<div class=\"cff-adopt\"></div></div></div></div>"
        "<script>window.__ERR=[];"
        "window.onerror=function(m){window.__ERR.push(String(m));};"
        "(function(){\n"
        + code
        + "\nvar UI={adopt:document.querySelector('.cff-adopt')};"
        "var DOC={capture:{analyzed:1,border:" + json.dumps(border) + "},"
        "frame:{}};"
        "var CF={geom:function(){return " + json.dumps(g) + ";},"
        "doc:function(){return DOC;},"
        "get:function(p,d){var c=DOC,ps=String(p).split('.');"
        "for(var i=0;i<ps.length;i++){"
        "if(c===null||typeof c!=='object'||!Object.prototype"
        ".hasOwnProperty.call(c,ps[i]))return d;c=c[ps[i]];}"
        "return c===undefined?d:c;}};"
        "var M={toast:function(){}};var f=function(){return DOC.frame;};"
        "var set=function(){};"
        "renderAdopt(DOC.frame, CF.geom());"
        "})();</script></body>", encoding="utf-8")
    return page


def test_le_bloc_d_adoption_TIENT_dans_un_vrai_navigateur(tmp_path):
    """LE BLOC, VU. Le banc DOM prouve la logique ; il ne prouve pas qu'on voit
    quelque chose. Ici la VRAIE feuille de P2 et le VRAI `renderAdopt` se
    rencontrent dans un Chrome sans tête.

    Quatre faits, tous mesurés sur la page rendue :
      1. le bloc a une hauteur (il n'est pas replié à zéro) ;
      2. il porte ses tokens — un fond et un liseré, pas une couleur en dur ;
      3. la ligne d'écart, longue par construction, se REPLIE : la colonne ne
         gagne pas un pixel de défilement horizontal (le défaut déjà payé par
         `.cff-acts`, 160 px mesurés) ;
      4. aucune erreur JavaScript."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du navigateur ne peut pas tourner")
    page = _page_adopt(tmp_path, {"mm": 25.0, "color": "#d8b76a",
                                  "radius_mm": 3.0, "confidence": 0.21})
    banc = tmp_path / "banc_chrome.mjs"
    banc.write_text(BANC_CHROME, encoding="utf-8")
    r = subprocess.run([node, str(banc), str(page)], capture_output=True,
                       text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-2000:])
    v = json.loads(r.stdout)
    if v.get("skip"):
        pytest.skip("Chrome absent : la vérification navigateur ne peut pas tourner")
    assert not v.get("erreur"), v.get("erreur")
    assert v["erreurs"] == [], v["erreurs"]
    assert v["enfants"] == 3, v
    assert v["hauteur"] > 40, v
    assert v["largeur"] > 200, v
    # les tokens : un fond OPAQUE et un liseré à gauche, pas les valeurs par
    # défaut du navigateur
    assert v["fond"] not in ("rgba(0, 0, 0, 0)", "transparent"), v["fond"]
    assert v["bordG"] not in ("0px", ""), v["bordG"]
    assert v["couleurLigne"] not in (None, "rgb(0, 0, 0)"), v["couleurLigne"]
    # le texte est bien celui du calcul
    assert v["bouton"] == "Adopter la bordure", v["bouton"]
    assert "bande 25,0 mm ↔" in v["ligne"], v["ligne"]
    assert "PEU SÛRE" in v["ligne"] and "0,21" in v["ligne"], v["ligne"]
    assert "ramenée à 20,0 mm" in v["ligne"], v["ligne"]
    # ... et il TIENT : pas un pixel de débordement horizontal
    assert v["debord"] <= 0, f"la colonne déborde de {v['debord']} px"
    assert v["lignePx"] <= v["colPx"], (v["lignePx"], v["colPx"])




# ═════════════════════════════════════════════════════════════════════════════
# 24. LES ÉLÉMENTS LIBÉRÉS — phase 5, T2 (plan D3)
#
# Ce que la tâche promet, et que ce bloc mesure :
#   · la gemme gagne un placement PERSISTÉ (gem_x, gem_y, gem_r en mm), `null`
#     valant AUTOMATIQUE — le calcul de `placeGem` reste le défaut ;
#   · le passage auto -> manuel SE DIT (patron T4 de la phase 4 : la ligne
#     d'état le nomme, et un geste rend l'automatique) ;
#   · les bornes MORDENT, des deux côtés, sur les MÊMES nombres ;
#   · les ornements de coin gagnent un décalage et une échelle (globaux ×4) ;
#   · la fenêtre gagne son liseré propre, à 0 mm par défaut donc INVISIBLE :
#     les huit familles restent à l'octet ce qu'elles étaient, et la QA de
#     silhouettes — qui rend les familles sur les DÉFAUTS — ne bouge pas.
# ═════════════════════════════════════════════════════════════════════════════

# Le banc d'EXÉCUTION du placement : il évalue le VRAI bloc de mod-frame.js
# (celui que `_painter_js_source` extrait déjà pour les peintres) et appelle
# `occupancy` sur les mêmes entrées que le Python. Aucune réimplémentation —
# une réimplémentation prouverait la réimplémentation.
BANC_OCC = r"""
import { readFileSync } from "node:fs";
const SRC = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
globalThis.window = { CF: { get: () => [], register: () => ({}) } };
const CF = globalThis.window.CF;
const mod = (0, eval)(SRC + "\n({ occupancy: occupancy, st: st, gemManuel: gemManuel })");
const out = [];
for (const c of CAS.cas) {
  try {
    out.push({ nom: c.nom, ok: true,
      occ: mod.occupancy({ trim_mm: c.trim_mm }, c.frame, c.slots || []) });
  } catch (e) { out.push({ nom: c.nom, ok: false, err: String((e && e.message) || e) }); }
}
process.stdout.write(JSON.stringify(out));
"""


def _banc_occ(tmp_path, cas: list, code: str | None = None) -> list:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'occupation ne peut pas tourner")
    js = tmp_path / "occ.js"
    js.write_text(code if code is not None else _painter_js_source(),
                  encoding="utf-8")
    banc = tmp_path / "banc_occ.mjs"
    banc.write_text(BANC_OCC, encoding="utf-8")
    conf = tmp_path / "cas_occ.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


GEM_FRAME = dict(FRAME)


def _gem(o) -> dict:
    return [b for b in o["boxes"] if b["id"] == "gem"][0]


def test_la_gemme_sans_cles_reste_exactement_ou_le_calcul_la_pose():
    """LA NON-RÉGRESSION D'ABORD. Trois clés neuves qui bougeraient une seule
    gemme d'un centième de millimètre changeraient l'aspect de tout jeu déjà
    enregistré. On compare donc le plan D'AVANT (aucune clé) au plan avec les
    trois clés écrites à `None` — et à celui d'un document qui les porte
    fausses (`""`, `[]`, `True`) : « absent » est le seul verdict possible."""
    g = CT.geom("poker_eu", 300)
    ref = FR.occupancy(g, dict(GEM_FRAME, fit=True), SLOTS)
    for faux in ({}, {"gem_x": None, "gem_y": None, "gem_r": None},
                 {"gem_x": "", "gem_y": [], "gem_r": {}},
                 {"gem_x": True, "gem_y": False, "gem_r": None},
                 {"gem_x": "0x10", "gem_y": "1_0", "gem_r": float("nan")}):
        o = FR.occupancy(g, dict(GEM_FRAME, fit=True, **faux), SLOTS)
        assert o["boxes"] == ref["boxes"], faux
        assert o["count"] == ref["count"], faux
    assert _gem(ref)["manual"] is False, ref


def test_la_main_gagne_sur_le_calcul_et_le_dit_dans_le_plan():
    """LE CŒUR DE D3. Sur le jeu de slots réel, le calcul range la gemme en
    ÉCRIN (aucun coin libre) : elle passe en couche 40, perd ses crans et
    prend la taille de son hôte. Une position posée à la main la REPREND —
    couche 70, ses crans, sa place — et le plan porte `manual: True` pour que
    l'écran puisse le dire au lieu de le deviner."""
    g = CT.geom("poker_eu", 300)
    auto = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True), SLOTS))
    assert auto["seat"] is True and auto["z"] == 40 and auto["pips"] == 0

    gem = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True,
                                    gem_x=31.5, gem_y=44.0, gem_r=6.0), SLOTS))
    assert gem["manual"] is True and gem["seat"] is False
    assert gem["z"] == 70, "la main pose un ornement, pas un écrin"
    assert (gem["cx"], gem["cy"], gem["r"]) == (31.5, 44.0, 6.0)
    assert gem["pips"] == 3, "la rareté « rare » compte 3 crans"
    assert gem["lane"] == "posée à la main"
    # LA BOÎTE GARDE LA FORME « gemme + portée des crans » : sa hauteur est le
    # diamètre, sa largeur le rayon plus la portée. La rétrécir aurait fait
    # DISPARAÎTRE des recouvrements bien réels.
    port = 1.5 * 6.0 + 2 * FR.PIP_STEP_MM + FR.PIP_R_MM
    assert gem["box"][3] == pytest.approx(12.0, abs=0.01)
    assert gem["box"][2] == pytest.approx(6.0 + port, abs=0.01)


def test_la_gemme_posee_a_la_main_est_JUGEE_par_le_compteur():
    """Ce que le geste coûte est COMPTÉ, pas caché. Posée sur le coût, la
    gemme redevient un meuble de la couche 70 qui recouvre une mention : le
    compteur le dit en millimètres carrés et en pourcentage — exactement
    comme il le disait du bandeau avant le modèle d'occupation."""
    g = CT.geom("poker_eu", 300)
    cout = [s for s in SLOTS if s["id"] == "cost"][0]["box"]
    cx = cout[0] + cout[2] / 2
    cy = cout[1] + cout[3] / 2
    o = FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_x=cx, gem_y=cy,
                             gem_r=4.6), SLOTS)
    par = {(c["a"], c["b"]): c for c in o["collisions"]}
    assert ("gem", "cost") in par, o["collisions"]
    assert par[("gem", "cost")]["pct"] > 50, par[("gem", "cost")]
    assert o["count"] >= 1


def test_les_crans_rentrent_quand_la_gemme_traverse_le_milieu():
    """Les crans sortent de la gemme vers l'extérieur. Gardés du côté du coin
    que le calcul avait choisi, ils partiraient HORS CARTE dès que la main
    traverse la demi-largeur. Le côté se déduit donc de la POSITION."""
    g = CT.geom("poker_eu", 300)
    tw = g.trim_mm[0]
    for x, sens in ((8.0, 1), (tw - 8.0, -1)):
        gem = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_x=x,
                                        gem_y=44.0, gem_r=4.6), SLOTS))
        assert gem["dir"] == sens, (x, gem)
        assert gem["box"][0] >= -0.01, (x, gem)
        assert gem["box"][0] + gem["box"][2] <= tw + 0.01, (x, gem)


def test_chaque_cle_de_gemme_est_independante():
    """Ne toucher QUE le rayon garde la position calculée, et l'inverse aussi.
    Un `null` sur deux clés n'est pas « à moitié automatique » : c'est « ces
    deux-là restent calculées »."""
    g = CT.geom("poker_eu", 300)
    seul_r = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_r=9.0), SLOTS))
    assert seul_r["r"] == 9.0 and seul_r["manual"] is True
    seul_x = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_x=20.0), SLOTS))
    assert seul_x["cx"] == 20.0
    assert seul_x["r"] == FR.GEM_R_MM, "le rayon devait rester calculé"
    # la position que garde `gem_r` seul est celle du MEILLEUR COIN — l'écrin
    # ne se forme plus, donc ce n'est pas la boîte de l'hôte.
    inner = min(GEM_FRAME["inner_mm"], FR.band_max_mm(*g.trim_mm))
    off = inner + FR.GEM_R_MM * FR.GEM_OFF_F
    assert seul_r["cx"] == pytest.approx(off, abs=0.01), seul_r


def test_les_bornes_de_la_gemme_mordent_des_deux_cotes():
    """`LIMITS` est la borne, et elle mord : un rayon de 900 mm est ramené au
    plafond, un rayon de 0 au plancher (une gemme à rayon nul n'est pas un
    réglage — le booléen `gem` existe pour l'éteindre). La POSITION, elle,
    est ramenée au FORMAT au tracé, pas à un millimètre absolu."""
    g = CT.geom("poker_eu", 300)
    tw = g.trim_mm[0]
    hi = FR.LIMITS["gem_r_mm"][1]
    lo = FR.LIMITS["gem_r_mm"][0]
    for demande, attendu in ((900.0, hi), (0.0, lo), (-5.0, lo)):
        gem = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_r=demande),
                                SLOTS))
        assert gem["r"] == attendu, (demande, gem)
    gem = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_x=999.0,
                                    gem_y=-40.0), SLOTS))
    assert gem["cx"] == pytest.approx(tw, abs=0.01), gem
    assert gem["cy"] == 0.0, gem


def test_le_placement_manuel_est_le_MEME_des_deux_cotes(tmp_path):
    """PARITÉ D'EXÉCUTION, pas de source. Le VRAI `occupancy` de mod-frame.js
    tourne dans node sur les mêmes entrées que celui de cards/frame.py, et les
    deux plans doivent être ÉGAUX clé par clé. Deux placements qui dérivent,
    c'est un aperçu qui ment sur le fichier — et sur ce chemin-là, c'est la
    pastille de vérification de l'écran qui passerait au rouge sans qu'un seul
    pixel bouge."""
    g = CT.geom("poker_eu", 300)
    frames = [
        dict(GEM_FRAME, fit=True),
        dict(GEM_FRAME, fit=True, gem_x=31.5, gem_y=44.0, gem_r=6.0),
        dict(GEM_FRAME, fit=True, gem_r=9.0),
        dict(GEM_FRAME, fit=True, gem_x=8.0),
        dict(GEM_FRAME, fit=True, gem_x=900.0, gem_y=-3.0, gem_r=0.0),
        dict(GEM_FRAME, fit=True, gem_x="12.5", gem_y="7", gem_r="3.25"),
        dict(GEM_FRAME, fit=True, gem_x="0x10", gem_y="1_0", gem_r=True),
        dict(GEM_FRAME, fit=False, gem_x=55.0, gem_y=80.0, gem_r=2.0),
        dict(GEM_FRAME, fit=True, rarity="mythic", gem_x=58.0, gem_y=6.0),
    ]
    cas = [{"nom": f"f{i}", "trim_mm": list(g.trim_mm), "frame": fr,
            "slots": SLOTS} for i, fr in enumerate(frames)]
    res = _banc_occ(tmp_path, cas)
    assert len(res) == len(frames)
    for r, fr in zip(res, frames):
        assert r["ok"], (r["nom"], r.get("err"))
        py = FR.occupancy(g, fr, SLOTS)
        assert r["occ"]["boxes"] == py["boxes"], (r["nom"], r["occ"]["boxes"],
                                                  py["boxes"])
        assert r["occ"]["collisions"] == py["collisions"], r["nom"]
        assert r["occ"]["count"] == py["count"], r["nom"]


def test_le_gel_auto_vers_manuel_se_DIT_et_se_defait_en_un_geste():
    """PATRON T4 (phase 4) : « le gel de la fenêtre auto se DIT quand elle
    était auto ; Ctrl+Z rend l'auto ». Ici les trois surfaces qui doivent le
    porter sont lues DANS LE SOURCE, parce qu'une promesse d'écran non tenue
    est exactement ce que la clôture T4 reproche :
      1. une phrase de passage, envoyée UNE FOIS et seulement quand on quitte
         l'automatique (`ditLeGel` sort tout de suite si c'était déjà manuel) ;
      2. une ligne d'état qui NOMME le régime et ce qu'il a coûté ;
      3. le retour à l'automatique en un geste, et ce geste rend les TROIS
         clés (deux nuls sur trois, c'est encore manuel)."""
    src = _js()
    dit = _js_fn(src, "ditLeGel")
    assert "if (avantManuel) return;" in dit, \
        "la phrase repartirait à chaque geste sur une gemme déjà manuelle"
    assert "posée à la main" in dit and "automatique" in dit, dit
    auto = _js_fn(src, "gemAuto")
    for k in ("gem_x: null", "gem_y: null", "gem_r: null"):
        assert k in auto, f"« Auto » ne rend pas {k} au calcul"
    # `sync()` n'est qu'un coalesceur rAF : le corps vit dans `syncNow()`.
    sy = _js_fn(src, "syncNow")
    assert "UI.gemRead.innerHTML" in sy, "aucune ligne d'état pour la gemme"
    assert "posée à la main" in sy and "Gemme <b>automatique</b>" in sy, \
        "la ligne d'état ne nomme pas le régime en vigueur"
    assert "n'essaie plus les quatre coins" in sy, \
        "la ligne d'état ne dit pas ce que le régime manuel a coûté"
    # le geste : le double-clic du plan vise le MEUBLE sous le pointeur
    wm = _js_fn(src, "wireMap")
    assert 'if (hit === "gem" || hit === "gemr") { gemAuto(); return; }' in wm, \
        "le double-clic sur la gemme ne la rend pas automatique"
    # et l'annulation empile l'ÉTAT D'AVANT, nuls compris
    assert 'HIST.push({ before: d0.etait, label: "gemme" })' in wm, \
        "Ctrl+Z reposerait la gemme au lieu de la rendre automatique"
    assert "etait: {" in wm and "gem_x" in wm


def test_les_ornements_de_coin_gardent_leur_symetrie_par_construction():
    """LA DÉCISION, ÉCRITE ET TENUE : un décalage et une échelle GLOBAUX,
    appliqués dans le repère MIROIR de chaque coin. C'est cette symétrie qui
    fait lire les quatre ornements comme un cadre, et douze clés
    indépendantes l'auraient laissée casser en silence.

    Le test lit le mécanisme là où il vit : `atCorners` pose `scale(±1, ±1)`,
    et `cornerOrn` décale APRÈS lui, dans ce repère-là."""
    src = _js()
    at = _js_fn(src, "atCorners")
    assert "ctx.scale(c[2], c[3])" in at, \
        "atCorners n'applique plus le miroir : le décalage global ne tiendrait plus"
    fn = _js_fn(src, "cornerOrn")
    assert "f.corner_dx" in fn and "f.corner_dy" in fn and "f.corner_scale" in fn
    # la borne est celle du FORMAT, pas un millimètre absolu
    assert "kMax" in fn and "Math.min(m.trim.w, m.trim.h) / 2" in fn, \
        "un décalage de 20 mm sur `micro` enverrait les quatre ornements se croiser"
    assert "LIMITS.corner_scale" in fn, "l'échelle n'est pas bornée par LIMITS"
    # l'échelle multiplie l'UNITÉ de dessin, donc l'ornement grandit entier
    assert "const u = m.u * cs;" in fn, \
        "l'échelle ne passe pas par l'unité : le trait ne suivrait pas"


def test_le_lisere_de_fenetre_ne_peint_rien_par_defaut():
    """TROIS REFUS, et ils sont le contrat de ce trait : épaisseur nulle,
    couleur illisible, et aucune dépendance au filet du cadre. Le premier est
    ce qui garde les huit familles à l'octet — donc ce qui garde la QA de
    silhouettes intacte."""
    src = _js()
    fn = _js_fn(src, "windowLiner")
    assert "if (!(w > 0)) return;" in fn, \
        "un liseré à 0 mm peindrait un trait que la presse refuse"
    assert "HEX_RE.test(hex)" in fn, \
        "une couleur illisible vaudrait « noir » — le défaut muet de plate_color"
    assert "winPath(ctx, m, shape)" in fn, \
        "le liseré redécrit la fenêtre au lieu de partager son tracé"
    assert "f.line_mm" not in fn and "pal(" not in fn, \
        "le liseré dépend du filet ou de la rareté : il n'est plus propre"
    assert FR.LIMITS["win_stroke_mm"][0] == 0
    # le défaut du document ne peint rien
    # LA COULEUR NAÎT VIDE depuis la ronde : `#000000` rendait la garde
    # « une couleur illisible ne peint rien » MORTE, parce que `st()`
    # normalisait « bleu » vers ce noir-là AVANT que le painter la voie.
    m = re.search(r'win_stroke_color: "(\w*)", win_stroke_mm: (\d+)', src)
    assert m, "le défaut du liseré n'est plus reconnaissable"
    assert m.group(1) == "", "la couleur du liseré ne naît pas vide"
    assert float(m.group(2)) == 0.0, "le liseré est allumé par défaut"
    # ... et il est peint APRÈS le filet et le Sceau, sur le même chemin
    pf = _js_fn(src, "paintFront")
    assert pf.index("paintSeal(") < pf.index("windowLiner("), \
        "le liseré de l'utilisateur passerait sous le Sceau"
    assert pf.index("windowLiner(") < pf.index("cornerOrn("), pf[:0]


def test_les_habillages_portent_les_cles_neuves_a_leur_defaut_inerte():
    """`models.py` DÉRIVE sa liste blanche de cadre des habillages
    (`_FRAME_CLES = frozenset(archetype_frame("superstar"))`) : une clé qui
    n'y serait pas serait JETÉE d'un modèle, en silence. Et elle doit y être
    à sa valeur INERTE — un archétype qui figerait la gemme la figerait pour
    tous les decks qui en naissent, y compris sur les formats où le calcul
    aurait trouvé un coin libre."""
    for nom, hab in FR.ARCHETYPE_FRAMES.items():
        for k in ("gem_x", "gem_y", "gem_r"):
            assert hab[k] is None, f"{nom} : {k} figé à {hab[k]!r}"
        assert hab["corner_dx"] == 0 and hab["corner_dy"] == 0, nom
        assert hab["corner_scale"] == 1, nom
        assert hab["win_stroke_mm"] == 0, nom
        # VIDE, comme `line_color` : « pas de couleur » est un état, et c'est
        # celui qui garde vivante la garde du painter.
        assert hab["win_stroke_color"] == "", nom


def test_la_qa_des_silhouettes_mesure_LE_DEFAUT_pas_l_etat_d_un_jeu():
    """LA QUESTION POSÉE PAR LE PLAN, TRANCHÉE À LA SOURCE : « les silhouettes
    se mesurent gemme en place AUTO — vérifie que déplacer une gemme ne casse
    pas la QA (elle mesure le défaut, pas l'état d'un deck) ».

    RÉPONSE MESURÉE, en deux parties.

    (a) L'ARBITRE — le banc de `test_les_huit_silhouettes_restent_deux_a_deux_
    distinctes` — construit chaque famille par
    `mod.st({ frame: { family, rarity } })` : RIEN d'autre que la famille et
    la rareté n'y entre, donc le reste vient de `DEFAULTS`, où les huit clés
    neuves valent `null` / 0 / 1. Une gemme déplacée dans un deck ne peut pas
    l'atteindre.

    (b) ET IL NE PEINT NI LA GEMME NI LES COINS. Le banc trace la bande, le
    profil, la signature de famille, la moulure et la plaque — `paintTop` (la
    gemme) et `cornerOrn` n'y sont pas appelés du tout. Les deux meubles que
    cette tâche libère sont donc HORS de la mesure de silhouette, ce que le
    plan demandait de confirmer plutôt que de supposer.

    Le badge du NAVIGATEUR, lui, rend la carte courante (`paintFamAt` part de
    `f()`) : il VOIT une gemme déplacée. C'est voulu — il mesure ce deck-ci —
    et sans conséquence sur le seuil, puisque les défauts ne bougent pas."""
    src = _js()
    i = BANC_TRAITS.index("if (CAS.silhouettes)")
    bloc = BANC_TRAITS[i:BANC_TRAITS.index("process.stdout.write", i)]
    assert "mod.st({ frame: { family: fa, rarity: ra } })" in bloc, \
        "le banc de silhouettes ne part plus des DÉFAUTS"
    assert "paintTop" not in bloc and "cornerOrn" not in bloc, \
        "le banc de silhouettes peint la gemme ou les coins : une gemme " \
        "déplacée deviendrait un axe de la mesure"
    # les huit clés neuves naissent inertes — c'est ce qui rend (a) vrai
    d = re.search(r"const DEFAULTS = \{(.*?)\n  \};", src, re.S).group(1)
    d = re.sub(r"/\*.*?\*/", " ", d, flags=re.S)
    assert "gem_x: null, gem_y: null, gem_r: null" in d, d
    assert "corner_dx: 0, corner_dy: 0, corner_scale: 1" in d, d
    assert "win_stroke_mm: 0" in d, d
    # et le seuil n'a pas bougé
    assert re.search(r"const SIL_SEUIL = 4;", src), "le seuil a bougé"


def test_la_route_occupancy_transporte_le_placement_manuel():
    """La route publie le MÊME plan que l'écran — c'est par elle que la
    pastille de vérification confronte les deux. Un corps qui porte des clés
    folles ne fait toujours JAMAIS 500 (spec §2.5)."""
    did = _deck()
    base = {"fmt": "poker_eu", "dpi": 300,
            "frame": dict(GEM_FRAME, fit=True, gem_x=30.0, gem_y=20.0,
                          gem_r=5.5),
            "slots": SLOTS}
    r = _api("POST", f"/api/cards/{did}/frame/occupancy", json=base)
    assert r.status_code == 200, r.text
    gem = _gem(r.json()["occupancy"])
    assert gem["manual"] is True and (gem["cx"], gem["cy"], gem["r"]) == \
        (30.0, 20.0, 5.5)
    # `1e309` n'est PAS testable ici : `json.dumps` refuse `inf` avant même
    # que la requête parte (le corps ne peut donc pas exister). La forme qui
    # ARRIVE vraiment par la frontière est la CHAÎNE — et c'est celle-là que
    # `_ou_nul` doit renvoyer à l'automatique.
    for folles in ({"gem_x": "haut"}, {"gem_r": [1, 2]}, {"gem_y": None},
                   {"gem_x": "1e309"}, {"gem_r": "Infinity"},
                   {"gem_x": {"x": 1}}):
        body = {"fmt": "poker_eu", "dpi": 300,
                "frame": dict(GEM_FRAME, fit=True, **folles), "slots": SLOTS}
        rr = _api("POST", f"/api/cards/{did}/frame/occupancy", json=body)
        assert rr.status_code == 200, (folles, rr.text)


# ── 24.1 LA VÉRIFICATION NAVIGATEUR DES POIGNÉES DE GEMME ────────────────────
#
# Le banc de node prouve le PLACEMENT ; il ne prouve pas qu'une main peut
# attraper la gemme. Ici la VRAIE mini-carte de P2 est dessinée dans un Chrome
# sans tête, sur un vrai `<canvas>`, par les VRAIES fonctions du module —
# `mapGeom`, `drawMapWith`, `mapHit` — et l'on mesure DEUX choses qu'aucun test
# de source ne peut donner :
#   1. la gemme est VISIBLE : de l'encre tombe dans le disque et pas à trois
#      rayons de là, et l'anneau MANUEL se distingue de l'anneau AUTOMATIQUE
#      (trait plein contre pointillé) ;
#   2. la gemme est ATTRAPABLE : `mapHit` rend « gem » au centre, « gemr » sur
#      l'anneau, et rend la main à la FENÊTRE dès qu'on s'éloigne — sans quoi
#      un glisser destiné au cadre re-dessinerait la fenêtre.
#
# CE QUE CETTE PAGE NE PROUVE PAS, ET C'EST DIT : le PLAN. `gemDe` y est un
# bouchon qui rend la boîte que `FR.occupancy` a calculée ICI — parce que le
# plan est déjà prouvé, et à l'exécution des deux côtés, par
# `test_le_placement_manuel_est_le_MEME_des_deux_cotes`. Cette page-ci prouve
# le DESSIN et la PRISE, qui n'existent que dans un navigateur.

def _banc_chrome(sonde: str) -> str:
    """`BANC_CHROME` avec UNE AUTRE sonde. Le pilote (lancer Chrome, ouvrir le
    protocole, nettoyer le profil) est écrit une fois ; ce qu'on lui demande de
    mesurer change d'un test à l'autre."""
    m = re.search(r"const SONDE = `.*?`;\n", BANC_CHROME, re.S)
    assert m, "la sonde de BANC_CHROME n'est plus reconnaissable"
    return BANC_CHROME.replace(m.group(0), "const SONDE = `" + sonde + "`;\n")


def _page_gemme(tmp_path) -> pathlib.Path:
    """La page MINIMALE : la VRAIE feuille de P2, le VRAI canevas `cff-map` et
    les VRAIES fonctions de plan. Rien n'est recopié — ni le tracé ni la CSS."""
    src = _js()
    code = "\n".join([
        _js_const(src, "cl"), _js_const(src, "r1"), _js_const(src, "r2"),
        _js_const(src, "num"), _js_const(src, "has"),
        _js_fn(src, "rgb"), _js_fn(src, "rgba"),
        _js_fn(src, "rrPath"), _js_fn(src, "mapGeom"),
        _js_fn(src, "drawMapWith"), _js_fn(src, "mapHit")])
    tokens = (REPO / "frontend" / "shared" / "deepotus.tokens.css").as_uri()
    css = CSS.as_uri()
    g = _geom_js("poker_eu", 3)
    # la gemme AUTOMATIQUE du document par défaut, calculée ICI par le backend :
    # la page n'en invente pas la position, elle reçoit celle du plan.
    gm = _gem(FR.occupancy(CT.geom("poker_eu", 300),
                           dict(GEM_FRAME, fit=False), []))
    page = tmp_path / "gemme.html"
    page.write_text(
        "<!doctype html><meta charset=\"utf-8\">"
        f"<link rel=\"stylesheet\" href=\"{tokens}\">"
        f"<link rel=\"stylesheet\" href=\"{css}\">"
        "<body style=\"margin:0;background:var(--bg-app,#111)\">"
        "<div class=\"cf-frame\" style=\"width:708px\">"
        "<div class=\"cff-winwrap\"><canvas class=\"cff-map\"></canvas>"
        "<div class=\"cff-winfields\"></div></div></div>"
        "<script>window.__ERR=[];"
        "window.onerror=function(m){window.__ERR.push(String(m));};"
        "(function(){\n"
        + code
        + "\nvar MAP={w:168,h:232};"
        "var UI={map:document.querySelector('.cff-map')};"
        "var DOC={frame:{}};"
        "var CF={geom:function(){return " + json.dumps(g) + ";}};"
        "var f=function(){return DOC.frame;};"
        "function gemDe(){return window.__GEM;}"
        "window.__GEM=" + json.dumps(gm) + ";"
        "window.__W={x:6.6,y:6.6,w:49.8,h:44.4,r:2.5};"
        "window.__peint=function(gm){drawMapWith(window.__W,gm);};"
        "window.__hit=function(x,y,gm){"
        "return mapHit(window.__W,{x:x,y:y},mapGeom(),gm);};"
        "window.__peint(window.__GEM);"
        "})();</script></body>", encoding="utf-8")
    return page


SONDE_GEMME = """(() => {
  const cv = document.querySelector(".cff-map");
  const c = cv.getContext("2d");
  const gm = window.__GEM;
  const pad = 10, tw = 63, th = 88;
  const s = Math.min((168 - 2 * pad) / tw, (232 - 2 * pad) / th);
  const ox = (168 - tw * s) / 2, oy = (232 - th * s) / 2;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const px = (mmx, mmy) => {
    const d = c.getImageData(Math.round((ox + mmx * s) * dpr),
      Math.round((oy + mmy * s) * dpr), 1, 1).data;
    return [d[0], d[1], d[2], d[3]];
  };
  /* L'ENCRE DE LA GEMME SE MESURE PAR DIFFERENCE, et c'est une correction :
     le premier jet sondait « du vide a trois rayons de la » et trouvait
     [240,180,40,51] — la FENETRE, peinte en accent translucide, dans laquelle
     la gemme automatique tombe. Un point du plan n'est jamais vide « par
     defaut ». On peint donc SANS puis AVEC, et l'on exige que le centre
     CHANGE et que le point eloigne ne bouge PAS : c'est ce qui dit a la fois
     « la gemme encre » et « elle n'encre qu'elle ». */
  window.__peint(null);
  const sansC = px(gm.cx, gm.cy), sansL = px(gm.cx, gm.cy + gm.r * 3.5);
  window.__peint(gm);
  const dedans = px(gm.cx, gm.cy);
  const loin = px(gm.cx, gm.cy + gm.r * 3.5);
  const empreinte = (etat) => {
    window.__peint(etat);
    const d = c.getImageData(0, 0, cv.width, cv.height).data;
    let h = 0;
    for (let i = 0; i < d.length; i += 7) { h = (h * 31 + d[i]) >>> 0; }
    return h;
  };
  const auto = empreinte(Object.assign({}, gm, { manual: false }));
  const manuel = empreinte(Object.assign({}, gm, { manual: true }));
  window.__peint(gm);
  return {
    w: cv.width, h: cv.height, dedans: dedans, loin: loin,
    sansC: sansC, sansL: sansL,
    auto: auto, manuel: manuel,
    hit_centre: window.__hit(gm.cx, gm.cy, gm),
    hit_anneau: window.__hit(gm.cx + gm.r + 0.9, gm.cy, gm),
    hit_loin: window.__hit(gm.cx, gm.cy + 22, gm),
    hit_sans: window.__hit(gm.cx, gm.cy, null),
    erreurs: window.__ERR || [],
  };
})()"""


def test_les_poignees_de_gemme_TIENNENT_dans_un_vrai_navigateur(tmp_path):
    """LA GEMME, VUE ET ATTRAPÉE. Quatre faits, tous mesurés sur la page rendue
    par un Chrome sans tête :
      1. le canevas a une taille réelle et l'encre de la gemme y tombe — on
         relève les pixels DANS le disque et à trois rayons de là ;
      2. l'état MANUEL se distingue de l'état AUTOMATIQUE à l'œil : les deux
         rendus du MÊME plan diffèrent (trait plein contre pointillé). C'est le
         premier des trois endroits où le gel se dit ;
      3. `mapHit` rend « gem » au centre et « gemr » sur l'anneau ;
      4. il rend la main à la fenêtre dès qu'on s'éloigne, et zéro erreur JS."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du navigateur ne peut pas tourner")
    page = _page_gemme(tmp_path)
    banc = tmp_path / "banc_chrome_gem.mjs"
    banc.write_text(_banc_chrome(SONDE_GEMME), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(page)], capture_output=True,
                       text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-2000:])
    v = json.loads(r.stdout)
    if v.get("skip"):
        pytest.skip("Chrome absent : la vérification navigateur ne peut pas tourner")
    assert not v.get("erreur"), v.get("erreur")
    assert v["erreurs"] == [], v["erreurs"]
    assert v["w"] > 160 and v["h"] > 220, v
    # 1. la gemme ENCRE le plan — mesuré PAR DIFFÉRENCE (un point du plan n'est
    #    jamais vide par défaut : la fenêtre y est peinte en accent) — et elle
    #    n'encre QU'ELLE : à trois rayons de là, rien n'a bougé.
    assert v["dedans"] != v["sansC"], \
        f"la gemme ne change rien au centre : {v['sansC']} -> {v['dedans']}"
    assert v["dedans"][3] > 0, f"aucune encre dans la gemme : {v['dedans']}"
    assert v["loin"] == v["sansL"], \
        f"la gemme encre à trois rayons d'elle : {v['sansL']} -> {v['loin']}"
    # 2. manuel et automatique NE SE RESSEMBLENT PAS
    assert v["auto"] != v["manuel"], \
        "le plan rend le même dessin en automatique et à la main : le gel ne se voit pas"
    # 3. et 4. la prise
    assert v["hit_centre"] == "gem", v["hit_centre"]
    assert v["hit_anneau"] == "gemr", v["hit_anneau"]
    assert v["hit_loin"] in ("move", "draw"), v["hit_loin"]
    assert v["hit_sans"] in ("move", "draw"), \
        "la gemme est attrapée alors qu'elle est éteinte"


def test_une_forme_de_gabarit_n_est_PAS_une_mention_du_cadre(tmp_path):
    """LE CADRE HABILLE DES MENTIONS, PAS DES DÉCORS (phase 5, T2).

    Le modèle d'occupation pose un SOCLE sous un chiffre qui tombe dans
    l'illustration, un LOGEMENT sous celui qui déborde sur l'anneau, et il
    écarte le ruban et la gemme de ce que P3 écrit. Aucun de ces trois gestes
    n'a de sens pour un rectangle décoratif : un socle sous un aplat serait une
    plaque de fond que personne n'a demandée, et un ruban qui s'écarte d'un
    trait de séparation change de place pour rien.

    MESURE DU DÉFAUT ÉVITÉ : le même rectangle de 30 x 16 mm posé au milieu de
    la fenêtre reçoit un socle s'il est déclaré `text`, et rien s'il est
    déclaré `rect`. Sans ce filtre, chaque forme posée par la palette aurait
    fait naître un meuble de cadre sous elle.

    CE QUI N'EST PAS TRANCHÉ, ET LE TEST LE DIT : un CALQUE D'IMAGE reste une
    mention. Il l'était avant cette tâche ; le changer déplacerait le ruban et
    retirerait des socles sur des jeux déjà enregistrés."""
    g = CT.geom("poker_eu", 300)
    boite = [16.0, 12.0, 30.0, 16.0]          # en plein dans la fenêtre
    comme_texte = FR.occupancy(g, dict(GEM_FRAME, fit=True),
                               [{"id": "deco", "box": boite}])
    assert [m["id"] for m in comme_texte["mentions"]] == ["deco"]
    assert any(b["id"] == "socle:deco" for b in comme_texte["boxes"]), \
        "le témoin ne mesure rien : un slot de texte devrait recevoir un socle"
    for k in ("rect", "ellipse", "line", "arrow"):
        o = FR.occupancy(g, dict(GEM_FRAME, fit=True),
                         [{"id": "deco", "kind": k, "box": boite}])
        assert o["mentions"] == [], (k, o["mentions"])
        assert not [b for b in o["boxes"] if b["id"].startswith(("socle:", "seat:"))], \
            (k, o["boxes"])
    # le calque d'image, LUI, reste une mention — dit, pas supposé
    img = FR.occupancy(g, dict(GEM_FRAME, fit=True),
                       [{"id": "deco", "kind": "image", "box": boite}])
    assert [m["id"] for m in img["mentions"]] == ["deco"], img["mentions"]
    # les trois listes de natures sont la MÊME, à l'ordre près
    from app.services.cards import type as TY2
    js = re.search(r"const SHAPE_KINDS = \[(.*?)\];", _js())
    assert js, "SHAPE_KINDS introuvable dans mod-frame.js"
    trois = {tuple(sorted(re.findall(r'"([a-z]+)"', js.group(1)))),
             tuple(sorted(FR.SHAPE_KINDS)), tuple(sorted(TY2.SHAPES))}
    assert len(trois) == 1, trois


def test_les_formes_ne_changent_PAS_le_plan_des_mentions_deja_posees():
    """LA NON-RÉGRESSION DU FILTRE. Poser une forme au milieu d'un jeu ne doit
    déplacer NI le ruban NI la gemme : le plan avec la forme est celui sans
    elle, boîte par boîte. Un filtre qui aurait laissé passer la forme aurait
    fait maigrir le ruban ou changer le coin de la gemme sans qu'un pixel de
    texte ne bouge."""
    g = CT.geom("poker_eu", 300)
    sans = FR.occupancy(g, dict(GEM_FRAME, fit=True), SLOTS)
    avec = FR.occupancy(g, dict(GEM_FRAME, fit=True), SLOTS + [
        {"id": "sep", "kind": "line", "box": [4.0, 47.0, 55.0, 0.4]},
        {"id": "halo", "kind": "ellipse", "box": [20.0, 10.0, 24.0, 24.0]},
    ])
    assert avec["boxes"] == sans["boxes"]
    assert avec["collisions"] == sans["collisions"]
    assert avec["count"] == sans["count"]


# ═════════════════════════════════════════════════════════════════════════════
# 25. RONDE T2 — CE QUE LA REVUE A MESURÉ SUR LE CADRE
# ═════════════════════════════════════════════════════════════════════════════

CHIFFRES_EXOTIQUES = ("١٢", "१२", "１２")     # arabe · devanagari · pleine chasse


def test_les_chiffres_NON_ASCII_ne_font_PAS_basculer_le_regime_de_la_gemme():
    """LE DÉFAUT LE PLUS SOURNOIS DE LA RONDE. `\\d` de Python est UNICODE,
    `\\d` de JavaScript est ASCII : `BACK_NUM_RE.fullmatch("١٢")` était VRAI
    ici et FAUX à l'écran. Conséquence mesurée par la revue : avec
    `gem_x: "١٢"`, le BACKEND lisait 12,0 et publiait une gemme MANUELLE
    (cx = 12), l'ÉCRAN retombait sur l'automatique (cx = 7,85). Ce n'est plus
    un centième de millimètre qui diverge : c'est le RÉGIME du meuble.

    Le motif est ancré sur `[0-9]` — la seule forme que les deux langages
    lisent pareil, ce que le commentaire de `BACK_NUM_RE` promettait déjà."""
    for ex in CHIFFRES_EXOTIQUES:
        assert FR.BACK_NUM_RE.fullmatch(ex) is None, ex
        assert FR._ou_nul(ex, FR.LIMITS["gem_xy_mm"]) is None, ex
        assert FR._borne(ex, 1.0, 0.0, 1.0) == 1.0, ex
    g = CT.geom("poker_eu", 300)
    auto = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True), SLOTS))
    for ex in CHIFFRES_EXOTIQUES:
        o = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_x=ex), SLOTS))
        assert o["manual"] is False, (ex, o)
        assert o == auto, (ex, o)
    # ... et l'ASCII passe toujours
    assert _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True, gem_x="12"),
                             SLOTS))["cx"] == 12.0
    # LES DEUX MOTIFS SONT LE MÊME MOT À MOT : écrits `\d` de part et d'autre,
    # ils se LISAIENT très bien et rendaient deux verdicts.
    assert "\\d" not in FR.BACK_NUM_RE.pattern
    assert r"/^-?[0-9]+(\.[0-9]+)?$/" in _js()


def test_les_noms_d_image_du_verso_refusent_les_chiffres_exotiques():
    """Même faille, mêmes deux motifs : `img:img_١٢.png` passait ici et pas à
    l'écran — une source que le backend accepte et que le client ne sait pas
    fabriquer est une image qui ne se relit jamais."""
    for ex in CHIFFRES_EXOTIQUES:
        assert FR.BACK_SRC_RE.fullmatch(f"img:img_{ex}.png") is None, ex
        assert FR.BACK_IMG_NAME_RE.fullmatch(f"img_{ex}.png") is None, ex
        assert FR.back_image_of(f"img:img_{ex}.png") == ""
    assert FR.BACK_SRC_RE.fullmatch("img:img_12.png") is not None
    assert "\\d" not in FR.BACK_SRC_RE.pattern
    assert "\\d" not in FR.BACK_IMG_NAME_RE.pattern
    assert r"/^(|img:img_[0-9]+\.png)$/" in _js()


def test_les_trois_ecritures_exotiques_rendent_le_MEME_plan_des_deux_cotes(tmp_path):
    """La parité d'exécution, rejouée sur les trois écritures. C'est le seul
    contrôle qui aurait vu le défaut : les deux tables se lisaient très bien,
    et c'est le VERDICT du motif qui divergeait."""
    g = CT.geom("poker_eu", 300)
    frames = [dict(GEM_FRAME, fit=True, gem_x=ex) for ex in CHIFFRES_EXOTIQUES]
    frames += [dict(GEM_FRAME, fit=True, gem_r=ex) for ex in CHIFFRES_EXOTIQUES]
    frames += [dict(GEM_FRAME, fit=True, gem_x="12", gem_y="١٢")]
    cas = [{"nom": f"x{i}", "trim_mm": list(g.trim_mm), "frame": fr,
            "slots": SLOTS} for i, fr in enumerate(frames)]
    res = _banc_occ(tmp_path, cas)
    for r, fr in zip(res, frames):
        assert r["ok"], (r["nom"], r.get("err"))
        assert r["occ"]["boxes"] == FR.occupancy(g, fr, SLOTS)["boxes"], \
            (r["nom"], fr)


def test_le_rayon_de_la_gemme_est_borne_PAR_LE_FORMAT():
    """LA BORNE ABSOLUE NE SUFFISAIT PAS, et la pièce le savait déjà trois
    fois : `bandMaxMM`, `sealMaxMM`, et mon propre `cornerOrn` qui NOMME
    `micro`. Mesuré : rayon au plafond du curseur (20 mm) sur un `micro`
    (31,75 x 44,45 mm) → une gemme de 40 mm de diamètre, PLUS LARGE QUE LA
    CARTE, dont l'encre sort de la toile des deux côtés.

    `gem_max_r_mm` suit le patron de `sealMaxMM` : la borne du curseur reste
    ce qu'elle est, celle du FORMAT s'applique au TRACÉ."""
    petit = CT.geom("micro", 300)
    tw, th = petit.trim_mm
    assert FR.gem_max_r_mm(tw, th) < FR.LIMITS["gem_r_mm"][1]
    assert 2 * FR.gem_max_r_mm(tw, th) <= min(tw, th)
    grand = CT.geom("tarot_eu", 300)
    assert FR.gem_max_r_mm(*grand.trim_mm) == FR.LIMITS["gem_r_mm"][1], \
        "la borne du format mord là où le format ne l'impose pas"
    # ... et elle s'applique au PLAN, donc au dessin
    gem = _gem(FR.occupancy(petit, dict(GEM_FRAME, fit=True, gem_r=20.0,
                                        gem_x=tw / 2, gem_y=th / 2), []))
    # le plan publie ses millimètres au CENTIÈME (`rnd(r, 2)`) : c'est ce
    # nombre-là que le peintre lit, donc c'est lui qu'on compare.
    assert gem["r"] == FR.rnd(FR.gem_max_r_mm(tw, th), 2), gem
    # CE QUI EST BORNÉ, ET CE QUI NE L'EST PAS — dit plutôt que supposé. Le
    # DISQUE rentre désormais dans la carte : c'était le défaut mesuré (40 mm
    # de diamètre sur 31,75 mm de large, encre hors toile des deux côtés).
    assert gem["cx"] - gem["r"] >= -0.01, gem
    assert gem["cx"] + gem["r"] <= tw + 0.01, gem
    assert gem["cy"] - gem["r"] >= -0.01, gem
    assert gem["cy"] + gem["r"] <= th + 0.01, gem
    # LA PORTÉE DES CRANS, ELLE, N'EST PAS BORNÉE, et c'est volontaire : une
    # gemme posée À LA MAIN au centre d'une carte minuscule, avec le rayon au
    # plafond, laisse ses crans de rareté sortir. C'est le geste de
    # l'utilisateur, pas un calcul qui dérape — et c'est le COMPTEUR
    # d'occupation qui le lui dit, comme il le dit du ruban. Mesuré ici pour
    # que le jour où quelqu'un veut le borner, il sache ce qu'il change.
    assert gem["box"][0] < 0, \
        "la portée des crans ne sort plus : la borne a changé de sens"


def test_la_borne_de_format_de_la_gemme_est_la_MEME_des_deux_cotes(tmp_path):
    """Une borne appliquée d'un seul côté, c'est une gemme de deux tailles."""
    petit = CT.geom("micro", 300)
    tw, th = petit.trim_mm
    frames = [dict(GEM_FRAME, fit=True, gem_r=20.0, gem_x=tw / 2, gem_y=th / 2),
              dict(GEM_FRAME, fit=True, gem_r=999.0),
              dict(GEM_FRAME, fit=True, gem_r=1.0)]
    cas = [{"nom": f"m{i}", "trim_mm": [tw, th], "frame": fr, "slots": []}
           for i, fr in enumerate(frames)]
    for r, fr in zip(_banc_occ(tmp_path, cas), frames):
        assert r["ok"], r.get("err")
        assert r["occ"]["boxes"] == FR.occupancy(petit, fr, [])["boxes"], fr


def test_la_couleur_du_lisere_de_fenetre_NE_VAUT_PAS_NOIR():
    """MA GARDE ÉTAIT MORTE. `windowLiner` refuse une couleur illisible — mais
    `st()` normalisait « bleu » en `#000000` AVANT que le painter la voie :
    l'écran posait un liseré NOIR de 2 mm, muet, c'est-à-dire exactement le
    « défaut visible et muet » que mon propre en-tête interdit.

    Le défaut devient `""` — la valeur que `line_color` porte déjà dans le
    même fichier et que la liste blanche des modèles admet — et le painter ne
    peint que sur un hexa lisible. La garde est vivante."""
    src = _js()
    d = re.search(r"const DEFAULTS = \{(.*?)\n  \};", src, re.S).group(1)
    d = re.sub(r"/\*.*?\*/", " ", d, flags=re.S)
    assert 'win_stroke_color: ""' in d, d
    fn = _js_fn(src, "st")
    assert "HEX_RE.test" in fn and "win_stroke_color" in fn, fn
    assert 'DEFAULTS.win_stroke_color' in fn, fn
    for nom, hab in FR.ARCHETYPE_FRAMES.items():
        assert hab["win_stroke_color"] == "", nom


def test_le_lisere_de_fenetre_DIT_qu_il_peut_mordre_le_fond_perdu():
    """LE MINEUR AVOUÉ. La fenêtre, elle, est bornée à la rogne ; le liseré,
    posé DESSUS et centré sur le chemin, met jusqu'à la moitié de son
    épaisseur au-delà. Sur une fenêtre calée au trait de coupe et un liseré au
    plafond (4 mm), ce sont 2 mm de fond perdu — de l'encre que la lame
    emporte.

    CHOIX AVOUÉ : on le DIT au lieu de le borner. Un liseré qui mord le fond
    perdu est LÉGITIME (c'est ainsi qu'on borde une illustration à fond
    perdu) ; le borner aurait interdit un dessin réel pour éviter une
    surprise. L'aide du champ porte donc le chiffre, et ce test l'exige."""
    src = _js()
    fn = _js_fn(src, "buildPanel") if "function buildPanel(" in src else src
    assert "moitié de son épaisseur" in src and "fond perdu" in src, \
        "l'écran ne dit pas que le liseré peut mordre le fond perdu"
    # la mesure qui le justifie : la moitié de 4 mm au-delà de la coupe
    assert FR.LIMITS["win_stroke_mm"][1] == 4


def test_la_carte_des_poignees_suit_la_FORME_de_l_ecrin():
    """`_place_gem` publie `shape: "rect"` quand l'écrin épouse une mention
    large et plate (une signature de 17 x 3,7 mm) — et la mini-carte dessinait
    un DISQUE quand même, donc une prise ronde sur un cartouche. Le plan dit
    la forme ; la carte des poignées doit la suivre."""
    src = _js()
    dm = _js_fn(src, "drawMapWith")
    assert 'gb.shape === "rect"' in dm, \
        "la mini-carte dessine toujours un disque"
    mh = _js_fn(src, "mapHit")
    assert 'gm.shape === "rect"' in mh, \
        "la prise de la gemme est ronde sur un écrin rectangulaire"
    # le plan publie bien les deux formes — sans quoi ce test ne mesure rien
    g = CT.geom("poker_eu", 300)
    ecrin = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True), SLOTS))
    assert ecrin["seat"] is True and ecrin["shape"] in ("disc", "rect")
    # POUR OBTENIR UN CARTOUCHE IL FAUT LES DEUX CONDITIONS À LA FOIS : aucun
    # coin libre (sinon la gemme s'y pose et reste un disque) ET un hôte PLAT
    # (17 x 3,7 mm : 17 > 1,6 x 3,7, donc au-delà de `GEM_SEAT_RATIO`).
    quatre = [{"id": f"m{i}", "box": [x, y, 17.0, 3.7]}
              for i, (x, y) in enumerate(((3.0, 7.0), (43.0, 7.0),
                                          (3.0, 77.0), (43.0, 77.0)))]
    plat = _gem(FR.occupancy(g, dict(GEM_FRAME, fit=True), quatre))
    assert plat["seat"] is True, plat
    assert plat["shape"] == "rect", plat


def test_l_echelle_des_coins_emporte_l_EPAISSEUR_du_trait():
    """« L'ornement grandit ENTIER, épaisseur comprise » — FAUX dès que
    `line_mm` > 0. Mesuré par la revue : dessin ×12, trait CONSTANT à
    9,57 px ; à l'échelle 0,25 l'ornement devient une tache, à 3 un fil.
    Mon témoin `line_mm: 0` donnait, lui, le comportement annoncé — c'est
    précisément le cas qui NE mord pas.

    L'épaisseur part donc de `m.line * 0.9 * cs` : la phrase redevient vraie
    aux deux échelles."""
    src = _js()
    fn = _js_fn(src, "cornerOrn")
    assert "m.line * 0.9 * cs" in fn, \
        "l'épaisseur du trait de coin ne suit pas l'échelle"


def test_les_champs_de_gemme_montrent_le_placement_EFFECTIF():
    """L'écran se contredisait lui-même : le champ affichait la valeur BRUTE
    du document (500) pendant que sa pastille et la ligne d'état, deux
    centimètres plus bas, disaient 63 — le placement que `placeGem` pose
    vraiment. Et l'input n'avait ni `min` ni `max`, donc rien ne disait où
    s'arrêtait la course.

    CHOIX AVOUÉ : le champ montre L'EFFECTIF, et il porte ses bornes. Le
    brut n'est pas une information utile — c'est un nombre que rien ne
    dessine ; l'effectif est celui du plan, de la pastille, de la ligne
    d'état et du peintre. Un écran d'accord avec lui-même."""
    src = _js()
    fn = _js_fn(src, "syncNow")
    # LE PIN PORTE SUR L'EXPRESSION QUI AFFECTE, pas sur la présence du mot
    # `gmb` quelque part dans la fonction : le premier jet de ce test cherchait
    # « gmb[kv[2]] » et restait VERT quand on remettait `r2(cle)`, parce que la
    # pastille, deux lignes plus bas, contient déjà `gmb`. Une mutation l'a dit.
    assert ': r2(gmb[kv[2]]);' in fn, \
        "le champ de gemme n'affiche pas le placement EFFECTIF"
    assert "r2(cle)" not in fn, \
        "le champ de gemme affiche encore la valeur brute du document"
    assert "champ.i.min" in fn and "champ.i.max" in fn, \
        "l'input de gemme n'a ni min ni max"


def test_la_route_ai_models_ne_fuit_PAS_de_chemin_absolu():
    """DETTE ROUTÉE DE T1, DANS MON FICHIER. `ai_models` publiait
    `str(e)[:200]` tel quel : la MÊME fuite de chemin absolu — donc du nom de
    compte de l'utilisateur — dans une réponse HTTP que T1 vient de filtrer
    chez lui. Le motif est RECOPIÉ (règle 8, chaque pièce porte ses
    constantes) et l'emprunt est avoué à la source."""
    py = pathlib.Path(FR.__file__).read_text(encoding="utf-8")
    assert "def _sans_chemin(" in py, "frame.py n'a pas de filtre de chemin"
    assert "erreur = str(e)[:200]" not in py, "la fuite est toujours là"
    for brut, dedans in (
            (r"C:\Users\dupont\AppData\jeu.json", "dupont"),
            ("/home/dupont/deck/meta.json", "dupont"),
            (r"ouverture de C:\Users\dupont\x.png refusée", "dupont")):
        out = FR._sans_chemin(brut)
        assert dedans not in out, (brut, out)
        assert "<chemin>" in out, (brut, out)
    # ... et un message SANS chemin traverse intact
    assert FR._sans_chemin("la clé fal est absente") == "la clé fal est absente"


# ═════════════════════════════════════════════════════════════════════════════
# 20. LA PHASE-POINTEUR DU SCEAU (phase 5, T3 — décision D4, dernier point)
# ═════════════════════════════════════════════════════════════════════════════
#
# LE TRANSMIS, RECONDUIT TROIS FOIS ET SOLDÉ ICI. `sealStops(f, phase)` accepte
# une phase depuis la phase 3c ; personne ne lui en a jamais passé d'autre que
# la constante canonique. Une souplesse que rien n'appelle est du code mort
# déguisé en promesse : ou bien elle sert, ou bien elle disparaît.
#
# ELLE SERT — ET ELLE SERT LÀ OÙ ELLE NE PEUT RIEN CASSER. Le contrat de la
# pièce est que L'APERÇU EST LE FICHIER LIVRÉ, au pixel : le peintre ne lit
# donc AUCUNE horloge, AUCUN pointeur (c'est le test
# `test_la_phase_du_fichier_livre_est_canonique`, qui interdit `clientX`,
# `Date.now` et `requestAnimationFrame` dans `paintSeal`). Faire vivre la phase
# sur la carte aurait mis un pointeur dans le chemin du fichier.
#
# La phase vivante habite donc une SURFACE À ELLE : une bande d'aperçu dans le
# panneau du Sceau, hors de tout chemin de rendu. Le pointeur la promène autour
# de 0,35 (±0,15 : l'arc-en-ciel fait un tour complet sur la course, sans que
# le repos cesse d'être le fichier livré), `pointerleave` la rend à sa valeur
# canonique, et RIEN n'est écrit au document.
#
# CE QUE CETTE SECTION PROUVE, DANS L'ORDRE :
#   1. la course de phase est une fonction pure, à vérité connue ;
#   2. le survol change les arrêts de dégradé de la BANDE, et le relâchement
#      les rend canoniques ;
#   3. AUCUN patch, AUCUN `set` : le document ne bouge pas ;
#   4. LE PEINTRE NE VOIT PAS LA PHASE VIVANTE — mesuré en la forçant à une
#      autre valeur et en relisant la trace du peintre (identique), avec le
#      contrôle négatif qui prouve que cette trace saurait le voir.

SEAL_AMP_SPEC = 0.15


def _node_frame(source: str) -> str:
    """Une tranche de `mod-frame.js`, EXÉCUTÉE dans node. Jumeau de l'outil du
    même nom de `test_cards_type.py` : une règle qui se lit ne prouve rien, une
    règle qui se joue prouve ce qu'elle rend."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    r = subprocess.run([node, "-e", source], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:800]
    return r.stdout.decode("utf-8", "replace")


def test_la_course_de_phase_est_une_fonction_PURE_a_verite_connue():
    """0 -> 0,20 ; 0,5 -> 0,35 (la canonique, au repos comme au milieu) ;
    1 -> 0,50. Hors [0, 1], la course est bornée : un pointeur qui sort de la
    bande ne pousse pas la phase au-delà de son amplitude."""
    src = _js()
    m = re.search(r"const SEAL_AMP = ([\d.]+);", src)
    assert m, "l'amplitude de la phase vivante n'est pas nommée"
    assert float(m.group(1)) == SEAL_AMP_SPEC, m.group(1)
    fn = _js_fn(src, "sealPhaseAt")
    out = json.loads(_node_frame(
        _js_const(src, "cl") + "\n"
        + "const SEAL_PHASE = " + str(SEAL_PHASE_SPEC) + ";\n"
        + "const SEAL_AMP = " + m.group(1) + ";\n" + fn + "\n"
        + "console.log(JSON.stringify([0,0.25,0.5,0.75,1,-3,7]"
        + ".map(sealPhaseAt)));"))
    assert out == [0.2, 0.275, 0.35, 0.425, 0.5, 0.2, 0.5], out


BANC_SEALPREV = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));

/* LE DOM DE PAILLE : de quoi poser un canevas, y brancher des ecouteurs et
   RELIRE les arrets de degrade que le module y pose. Rien d'autre — cette
   bande ne dessine qu'un rectangle. */
const LARGEUR = 240, HAUTEUR = 14;
let arrets = [];
function ctx2d() {
  return {
    setTransform() { }, clearRect() { }, fillRect() { },
    createLinearGradient() {
      const g = { addColorStop: (t, c) => { arrets.push([t, c]); } };
      return g;
    },
    save() { }, restore() { }, beginPath() { }, moveTo() { }, lineTo() { },
    stroke() { }, fill() { },
    set fillStyle(v) { }, get fillStyle() { return ""; },
    set strokeStyle(v) { }, get strokeStyle() { return ""; },
    set lineWidth(v) { }, get lineWidth() { return 1; },
    set globalAlpha(v) { }, get globalAlpha() { return 1; },
  };
}
function el(tag) {
  const lis = {};
  return {
    tagName: String(tag).toUpperCase(), style: {}, className: "", title: "",
    _txt: "", listeners: lis, width: 0, height: 0,
    set textContent(v) { this._txt = String(v); },
    get textContent() { return this._txt; },
    addEventListener(t, fn) { (lis[t] = lis[t] || []).push(fn); },
    getBoundingClientRect: () => ({ left: 0, top: 0, width: LARGEUR, height: HAUTEUR }),
    getContext: () => ctx2d(),
    appendChild(n) { return n; },
    classList: { add() { }, remove() { }, toggle() { }, contains: () => false },
  };
}
const PATCHS = [];
const document = { createElement: (t) => el(t) };
const window = { devicePixelRatio: 1 };
const rafs = [];
const raf = (fn) => { rafs.push(fn); return rafs.length; };
const caf = () => { };
const UI = { sealPrev: el("canvas"), sealPhase: el("span") };
const FRAME = CAS.frame;
const f = () => FRAME;
const M = { patch: (p) => { PATCHS.push(p); }, toast: () => { } };
const mod = new Function("UI", "f", "M", "document", "window",
  "requestAnimationFrame", "cancelAnimationFrame",
  CODE + "\nreturn { drawSealPrev: drawSealPrev, wireSealPrev: wireSealPrev,"
  + " sealStops: sealStops, SEAL_PHASE: SEAL_PHASE,"
  + " phase: function () { return sealPhaseLive; } };")(
  UI, f, M, document, window, raf, caf);

mod.wireSealPrev(UI.sealPrev);
const lis = UI.sealPrev.listeners;
const vide = () => { arrets = []; };
const vider = () => { while (rafs.length) { rafs.shift()(); } };
const out = { branche: Object.keys(lis).sort(), phases: [], stops: [] };
/* AU REPOS : la bande montre la phase canonique */
vide(); mod.drawSealPrev();
out.repos = { phase: mod.phase(), arrets: arrets.slice() };
out.canon = mod.sealStops(FRAME, mod.SEAL_PHASE);
for (const x of CAS.survols) {
  (lis.pointermove || []).forEach((fn) => fn({ clientX: x }));
  vider();
  vide(); mod.drawSealPrev();
  out.phases.push(mod.phase());
  out.stops.push(arrets.slice());
}
(lis.pointerleave || []).forEach((fn) => fn({}));
vider();
vide(); mod.drawSealPrev();
out.apres = { phase: mod.phase(), arrets: arrets.slice() };
out.patchs = PATCHS.length;
out.texte = UI.sealPhase.textContent;
process.stdout.write(JSON.stringify(out));
"""


def _banc_sealprev(tmp_path, frame: dict, survols: list) -> dict:
    """La bande d'aperçu du Sceau, JOUÉE : ses vrais écouteurs, son vrai
    dessin, ses vrais arrêts de dégradé — relus sur le contexte 2D de paille."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de la bande du Sceau ne peut pas tourner")
    js = tmp_path / "sealprev.js"
    js.write_text(_sceau_js_source(), encoding="utf-8")
    banc = tmp_path / "banc_sealprev.mjs"
    banc.write_text(BANC_SEALPREV, encoding="utf-8")
    conf = tmp_path / "cas_sealprev.json"
    conf.write_text(json.dumps({"frame": frame, "survols": survols}),
                    encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 0, r.stderr[-2500:]
    return json.loads(r.stdout)


def _frame_sceau() -> dict:
    """Un cadre dont le Sceau est allumé et DANS la portée écran — c'est le
    seul régime où la phase a un effet (hors portée, la base est un métal
    calme, et c'est ce que le témoin mesure)."""
    return {"family": "runic", "seal": {"on": True, "kind": "dorure",
                                        "width_mm": 1.2,
                                        "scope": {"screen": True, "print": False,
                                                  "mesh": False}}}


def test_le_SURVOL_de_la_bande_fait_VIVRE_la_phase_autour_de_la_canonique(tmp_path):
    """Trois positions sur une bande de 240 px : le bord gauche, le milieu, le
    bord droit. La phase suit 0,20 / 0,35 / 0,50 et les arrêts de dégradé
    CHANGENT avec elle — mesurés sur ce que le module pose vraiment, pas sur
    l'intention."""
    d = _banc_sealprev(tmp_path, _frame_sceau(), [0, 120, 240])
    assert d["branche"] == ["pointerleave", "pointermove"], d["branche"]
    assert d["repos"]["phase"] == SEAL_PHASE_SPEC, d["repos"]
    assert d["phases"] == [0.2, 0.35, 0.5], d["phases"]
    # au milieu, la bande montre EXACTEMENT le fichier livré
    assert d["stops"][1] == d["canon"], (d["stops"][1], d["canon"])
    # aux deux bords, non — sans quoi la course ne montrerait rien
    assert d["stops"][0] != d["canon"], d["stops"][0]
    assert d["stops"][2] != d["canon"], d["stops"][2]
    assert d["stops"][0] != d["stops"][2], "les deux bords rendent le même dégradé"
    # ET LE RELÂCHEMENT REND LA CANONIQUE : la bande au repos EST le fichier
    assert d["apres"]["phase"] == SEAL_PHASE_SPEC, d["apres"]
    assert d["apres"]["arrets"] == d["canon"], d["apres"]


def test_la_phase_vivante_n_ECRIT_RIEN_au_document(tmp_path):
    """L'aveu à mesurer : « écran seul, jamais écrite au doc ». Un survol
    complet de la bande, et le compteur de patchs reste à zéro. Une phase
    écrite au document aurait voyagé dans le deck, donc dans le fichier
    livré — le contraire exact de ce qu'on construit."""
    d = _banc_sealprev(tmp_path, _frame_sceau(), list(range(0, 241, 12)))
    assert d["patchs"] == 0, d["patchs"]
    # et la valeur courante est DITE à l'écran : une phase qui bouge sans se
    # nommer est un scintillement, pas une mesure
    assert "0,35" in d["texte"] or "0.35" in d["texte"], d["texte"]


def test_hors_portee_ecran_la_bande_reste_dans_sa_BASE_CALME(tmp_path):
    """LE TÉMOIN DE PORTÉE. Hors de la portée écran, `sealStops` rend le métal
    du kind — cinq arrêts fixes, sans arc-en-ciel. La phase a beau vivre, la
    bande ne bouge pas : c'est la garde `sealLive` qui décide, et elle est en
    amont de la phase."""
    froid = {"family": "runic", "seal": {"on": True, "kind": "dorure",
                                         "width_mm": 1.2,
                                         "scope": {"screen": False, "print": True,
                                                   "mesh": True}}}
    d = _banc_sealprev(tmp_path, froid, [0, 120, 240])
    assert d["phases"] == [0.2, 0.35, 0.5], d["phases"]
    assert d["stops"][0] == d["stops"][1] == d["stops"][2] == d["canon"], d["stops"]
    assert len(d["canon"]) == 5, d["canon"]


# ── 20.1 LE PEINTRE NE VOIT PAS LA PHASE VIVANTE ────────────────────────────

def test_le_PEINTRE_ne_lit_JAMAIS_la_phase_vivante(tmp_path):
    """LA PREUVE QUI COMPTE, ET ELLE EST EXÉCUTÉE. On force `sealPhaseLive` à
    0,71 — une valeur qu'aucun repos ne produirait — et l'on relit la TRACE du
    peintre (le hachage de ses opérations, arrêts de dégradé compris) : elle
    est identique à celle du module intact. Le fichier livré ne bouge pas d'un
    arrêt.

    LE CONTRÔLE NÉGATIF est dans le même test, et il est indispensable : on
    branche ENSUITE le peintre sur la phase vivante, et la trace CHANGE. Sans
    lui, « la trace est identique » ne prouverait que l'insensibilité de
    l'instrument."""
    cas = [_cas_sceau("phase-vivante", SEAL_ON)]
    ref = _banc_sceau(tmp_path, cas)[0]
    force = _banc_sceau(tmp_path, cas, mutations=[
        ("let sealPhaseLive = SEAL_PHASE;", "let sealPhaseLive = 0.71;")])[0]
    assert ref["ok"] and force["ok"], (ref.get("err"), force.get("err"))
    assert force["trace"] == ref["trace"], \
        "la phase vivante a atteint le peintre : l'aperçu n'est plus le fichier"
    assert force["stops"] == ref["stops"], (force["stops"], ref["stops"])
    fuite = _banc_sceau(tmp_path, cas, mutations=[
        ("let sealPhaseLive = SEAL_PHASE;", "let sealPhaseLive = 0.71;"),
        ("const stops = sealStops(f, SEAL_PHASE);",
         "const stops = sealStops(f, sealPhaseLive);")])[0]
    assert fuite["ok"], fuite.get("err")
    assert fuite["trace"] != ref["trace"], \
        "la trace ne verrait pas une fuite de phase : le contrôle ne mesure rien"


def test_le_peintre_et_sealStops_n_ont_PAS_CHANGE_pour_ce_branchement():
    """« Chirurgical : le painter et `sealStops` ne changent pas, seul le
    branchement naît. » Mesuré à la source : le peintre appelle toujours la
    CONSTANTE, et le nom de la phase vivante n'apparaît ni dans `paintSeal` ni
    dans `sealStops`."""
    src = _js()
    p = _js_fn(src, "paintSeal")
    assert "sealStops(f, SEAL_PHASE)" in p, "le peintre a changé de phase"
    assert "sealPhaseLive" not in p, "le peintre lit la phase vivante"
    assert "sealPhaseAt" not in p, "le peintre calcule une phase"
    st = _js_fn(src, "sealStops")
    assert "sealPhaseLive" not in st and "SEAL_AMP" not in st, \
        "`sealStops` a été touché : il devait rester la fonction de 3c"
    # ... et la bande est bien BRANCHÉE par le panneau, pas seulement écrite
    ui = _js_fn(src, "buildUI")
    assert "wireSealPrev(" in ui, "la bande n'est jamais branchée"
    assert "UI.sealPrev" in ui, "la bande n'est jamais posée dans le panneau"
    assert "drawSealPrev()" in _js_fn(src, "syncNow"), \
        "la bande ne suit pas les réglages du Sceau"


# =============================================================================
# 25. LE PLAN DES ORNEMENTS - phase 6, T3 (D5)
#
# LE BUG RAPPORTE (25/08) : la gemme deplacee a la main recouvrait le texte a
# 100 %, et AUCUN reglage de plan des blocs ne pouvait la battre - le decor
# haut (couche 70) se peint apres tout ce que P3 empile, par construction de
# Z_TABLE. Le remede tient dans le PLAN D OCCUPATION : `gem_plan` et
# `banner_plan` valent "dessus" (couche 70, le defaut de toujours) ou
# "dessous" - l ornement passe alors en couche 40, au-dessus du cadre de base
# et SOUS tous les blocs de P3. Le texte passe devant se voit enfin, et les
# boutons devant/derriere des blocs retrouvent leur sens.
# =============================================================================


def _ban(o) -> dict:
    return [b for b in o["boxes"] if b["id"] == "banner"][0]


PLAN_FRAME = dict(FRAME, fit=True, banner=True,
                  gem_x=31.5, gem_y=44.0, gem_r=6.0)


def test_le_plan_d_ornement_par_defaut_et_les_valeurs_inconnues():
    """Sans cle, RIEN ne bouge : gemme manuelle et bandeau restent couche 70,
    boites au bit pres. Et une valeur inconnue ("milieu", 3, [], True, "")
    vaut le defaut - un document etranger ne fait pas lever le painter, il
    est LU avec tolerance comme gem_x avant lui."""
    g = CT.geom("poker_eu", 300)
    ref = FR.occupancy(g, dict(PLAN_FRAME), SLOTS)
    assert _gem(ref)["z"] == 70
    assert _ban(ref)["z"] == 70
    assert _gem(ref)["plan"] == "dessus"
    assert _ban(ref)["plan"] == "dessus"
    for faux in ("milieu", 3, [], True, ""):
        o = FR.occupancy(g, dict(PLAN_FRAME, gem_plan=faux,
                                 banner_plan=faux), SLOTS)
        assert o["boxes"] == ref["boxes"], faux


def test_le_plan_dessous_passe_l_ornement_sous_les_blocs():
    """LE REMEDE MESURE : `gem_plan="dessous"` -> couche 40 dans le plan
    d occupation, et RIEN d autre ne bouge (position, crans, boite, manual).
    Pareil pour le bandeau. La couche 40 est peinte AVANT les blocs de P3 :
    c est tout le remede."""
    g = CT.geom("poker_eu", 300)
    ref = FR.occupancy(g, dict(PLAN_FRAME), SLOTS)
    o = FR.occupancy(g, dict(PLAN_FRAME, gem_plan="dessous",
                             banner_plan="dessous"), SLOTS)
    gem, gref = _gem(o), _gem(ref)
    assert gem["z"] == 40 and gref["z"] == 70
    assert gem["plan"] == "dessous"
    for cle in ("cx", "cy", "r", "pips", "box", "manual", "seat", "lane"):
        assert gem[cle] == gref[cle], cle
    ban, bref = _ban(o), _ban(ref)
    assert ban["z"] == 40 and bref["z"] == 70
    assert ban["plan"] == "dessous"
    assert ban["box"] == bref["box"]
    # la gemme rangee en ECRIN (auto, aucun coin libre) reste couche 40 comme
    # avant : le plan ne concerne que l ornement qu on voit, pas son logement
    ecrin = _gem(FR.occupancy(g, dict(FRAME, fit=True,
                                      gem_plan="dessous"), SLOTS))
    assert ecrin["seat"] is True and ecrin["z"] == 40


def test_le_plan_d_ornement_est_miroir_python_js(tmp_path):
    """La parite du banc de rangees, etendue au plan : les MEMES cas rendent
    les MEMES couches des deux cotes. L ecran confronte ce plan au backend a
    chaque changement - une divergence serait un mensonge d apercu."""
    g = CT.geom("poker_eu", 300)
    cas = []
    for plan in ("dessus", "dessous"):
        cas.append({"nom": "plan_" + plan, "trim_mm": list(g.trim_mm),
                    "frame": dict(PLAN_FRAME, gem_plan=plan,
                                  banner_plan=plan),
                    "slots": SLOTS})
    rendu = _banc_occ(tmp_path, cas)
    for r in rendu:
        assert r["ok"], r
        plan = r["nom"].split("_", 1)[1]
        py = FR.occupancy(g, dict(PLAN_FRAME, gem_plan=plan,
                                  banner_plan=plan), SLOTS)
        js_gem = [b for b in r["occ"]["boxes"] if b["id"] == "gem"][0]
        js_ban = [b for b in r["occ"]["boxes"] if b["id"] == "banner"][0]
        assert js_gem["z"] == _gem(py)["z"], plan
        assert js_ban["z"] == _ban(py)["z"], plan
        assert js_gem["plan"] == plan and js_ban["plan"] == plan


BANC_PLAN = r"""
import { readFileSync } from "node:fs";
const SRC = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
const mod = (0, eval)(SRC + "\n({ occupancy: occupancy, ornementsAuPlan: ornementsAuPlan })");
const out = [];
for (const c of CAS.cas) {
  try {
    const occ = mod.occupancy({ trim_mm: c.trim_mm }, c.frame, c.slots || []);
    out.push({ nom: c.nom, ok: true,
      z40: mod.ornementsAuPlan(occ.boxes, 40).map((b) => b.id),
      z70: mod.ornementsAuPlan(occ.boxes, 70).map((b) => b.id) });
  } catch (e) { out.push({ nom: c.nom, ok: false, err: String((e && e.message) || e) }); }
}
process.stdout.write(JSON.stringify(out));
"""


def test_la_repartition_du_decor_par_plan_s_execute_au_banc(tmp_path):
    """`ornementsAuPlan(boxes, z)` est LA fonction que les deux peintres de
    P2 consultent : elle repartit gemme et bandeau entre la couche 40 et la
    couche 70 selon leur plan, et ne rend JAMAIS la fenetre, les socles ou
    les logements (eux ne sont pas des ornements peints par le decor haut).
    On l execute au banc sur la VRAIE source - pas de grep de prose."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du plan ne peut pas tourner")
    g = CT.geom("poker_eu", 300)
    js = tmp_path / "occ_plan.js"
    js.write_text(_painter_js_source(), encoding="utf-8")
    banc = tmp_path / "banc_plan.mjs"
    banc.write_text(BANC_PLAN, encoding="utf-8")
    cas = [{"nom": "dessus", "trim_mm": list(g.trim_mm),
            "frame": dict(PLAN_FRAME), "slots": SLOTS},
           {"nom": "dessous", "trim_mm": list(g.trim_mm),
            "frame": dict(PLAN_FRAME, gem_plan="dessous",
                          banner_plan="dessous"), "slots": SLOTS}]
    conf = tmp_path / "cas_plan.json"
    conf.write_text(json.dumps({"cas": cas}), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    rendu = json.loads(r.stdout)
    par = {v["nom"]: v for v in rendu}
    assert par["dessus"]["ok"] and par["dessous"]["ok"], rendu
    assert sorted(par["dessus"]["z70"]) == ["banner", "gem"]
    assert par["dessus"]["z40"] == []
    assert sorted(par["dessous"]["z40"]) == ["banner", "gem"]
    assert par["dessous"]["z70"] == []
