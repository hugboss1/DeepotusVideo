# -*- coding: utf-8 -*-
"""Card Forge — P1 « Génération de face » : les seuils, mesurés.

La barre est Clash of Decks : galerie de 300 dessins BITMAP, import refusé
brutalement sous 650x1024 par un `alert()` natif, placement par six boutons,
et AUCUN chiffre nulle part — ni la taille de l'image, ni celle de la carte,
ni le DPI auquel elle sera imprimée.

Ce fichier verrouille les mesurables de la pièce 01 (spec §4) :

  1. Le DPI EFFECTIF de l'illustration posée est un CALCUL, pas une opinion.
     `effective_dpi`, `dpi_verdict`, `min_source_px` sont testés sur des
     valeurs écrites en dur, dérivées des toiles réelles de `contract.geom`.
     Et l'alerte est NON BLOQUANTE : `mod-face.js` ne contient pas un seul
     `alert(` — c'est vérifié sur la source servie.
  2. **LE FICHIER LIVRÉ DÉCLARE SA RÉSOLUTION PHYSIQUE.** `canvas.toBlob` n'y
     met aucun chunk `pHYs` ; sans lui, un PNG « 300 DPI » s'ouvre à 72 DPI
     dans un outil de mise en page, soit 11,32 x 15,42 pouces au lieu de
     69 x 94 mm. La section 6 le teste sur les OCTETS, y compris relu par PIL,
     et vérifie que la route REFUSE d'estampiller une trame qui ne fait pas
     la taille de la toile.
  3. Le catalogue de départ fait **108 dessins distincts** (18 sujets ×
     6 compositions, seuil de la spec : >= 60), VECTORIELS, et ne coûte pas un
     octet de réseau : aucune URL externe dans la source. Les recolorations
     (1296 combinaisons) sont comptées à part — c'est tout l'objet du test
     `test_le_catalogue_compte_des_DESSINS_pas_des_recolorations`.
  4. Le placement : molette = zoom, glisser = pan, Alt+glisser = rotation, et
     TROIS champs numériques éditables au clavier (x, y, échelle en %) —
     plus la hauteur et la rotation. Vérifié sur la source du module.
  5. Une face IA est générée en UN SEUL appel et POSÉE, sans copier-coller
     de nom de fichier : `CF.images.generate(` apparaît exactement une fois.
  6. **AUCUN NOMBRE AFFICHÉ N'EST UNE PROMESSE** (section 7) : l'écran ne peut
     pas annoncer « 1200 DPI » quand `CF.DPIS` vaut [150, 300, 600], ni
     affirmer « 0 octet réseau » sans le compter — ni, depuis le tour 3,
     écrire « aucune perte possible » sur une face vectorielle rasterisée à
     150 DPI (section 13 : la jauge mesure la TRAME LIVRÉE, pas le genre de
     la source), ni montrer une jauge dont l'état rouge serait hors d'atteinte
     (la mire de 320 x 480 px l'atteint en un clic, sur de vrais octets).

Et le MIROIR : les tables `CF-FACE-PALETTES` / `CF-FACE-SUBJECTS` /
`CF-FACE-COMPOS` de `js/mod-face.js` sont extraites du fichier réellement
servi et confrontées à celles de `cards/face.py`. Une dérive entre l'écran et
la table de référence fait rougir ce test — elle ne se découvre pas chez
l'imprimeur.

Run : .\\scripts\\run-tests.ps1 -Filter cards
"""
import asyncio
import io
import json
import math
import os
import pathlib
import re
import struct
import sys
import tempfile
import zlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
# LE DOSSIER DE DONNÉES AUSSI (P5-T1). Le manifeste de série vit dans
# `DATA_ROOT`, et sans cette ligne le banc l'écrivait dans le dossier de
# données RÉEL de l'utilisateur. Elle referme au passage la porte du bloquant
# de la phase 4 : `app/config.py` charge `DATA_ROOT/.env` avec `override=True`
# à l'import, donc un dossier de données neuf = aucune vraie clé dans ce
# processus. La ceinture (`_settings.FAL_KEY`) reste posée en dessous, et un
# test la PROUVE — un banc qui croit neutraliser une clé doit le montrer.
os.environ["DEEPOTUS_DATA_DIR"] = str(pathlib.Path(_tmp, "data"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
pathlib.Path(_tmp, "data").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                   # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter     # noqa: E402

from app.config import settings as _settings                    # noqa: E402
from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import face as FA                       # noqa: E402

# ON FORCE L'OBJET, PAS L'ENVIRONNEMENT, ET APRÈS L'IMPORT DE CONFIG — la
# leçon T3 de la phase 4, recopiée ici parce que c'est ici que la série
# dépense. `os.environ.setdefault` ne tient pas contre un `.env` chargé en
# `override=True` ; ces deux lignes-ci, si.
_settings.FAL_KEY = "test-key"
_settings.OPENAI_API_KEY = "test-key-openai"

ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = ROOT / "frontend" / "cardforge" / "js" / "mod-face.js"
CSS = ROOT / "frontend" / "cardforge" / "css" / "mod-face.css"


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _deck() -> str:
    r = _api("POST", "/api/cards/decks", json={"name": "essai face"})
    assert r.status_code == 200, r.text
    return r.json()["deck"]["id"]


def _png(w: int, h: int) -> bytes:
    """Un PNG réel, produit par PIL — donc SANS pHYs, exactement comme celui
    que `canvas.toBlob` livre au navigateur."""
    buf = io.BytesIO()
    im = Image.new("RGBA", (w, h))
    im.putpixel((0, 0), (34, 78, 126, 255))
    im.save(buf, "PNG")
    return buf.getvalue()


def _png_opaque(w: int, h: int) -> bytes:
    """La MÊME chose qu'un `canvas.toBlob` de carte : du RGBA dont le canal
    alpha vaut 255 partout. `_png` ci-dessus est transparent (alpha 0), ce qui
    est très bien pour tester la géométrie mais rendrait le test du canal
    alpha faux dans les deux sens : sur une image transparente, RETIRER le
    canal serait une faute, et le code a raison de refuser."""
    buf = io.BytesIO()
    im = Image.new("RGBA", (w, h), (20, 26, 34, 255))
    im.putpixel((0, 0), (34, 78, 126, 255))
    im.putpixel((w // 2, h // 2), (240, 230, 200, 255))
    im.save(buf, "PNG")
    return buf.getvalue()


def js_src() -> str:
    assert JS.is_file(), f"module introuvable : {JS}"
    return JS.read_text(encoding="utf-8")


def js_code() -> str:
    """La source SANS les commentaires. Les commentaires de ce module citent
    volontairement ce qu'il ne faut PAS faire (`alert()`, la route morte
    `/api/images/file/`) : les chercher dans le texte brut ferait échouer un
    test sur sa propre explication."""
    src = re.sub(r"/\*.*?\*/", " ", js_src(), flags=re.S)
    return re.sub(r"^[^\S\n]*//[^\n]*$", " ", src, flags=re.M)


def js_block(name: str) -> str:
    """Le bloc marqué CF-FACE-<name>-BEGIN/END de mod-face.js."""
    src = js_src()
    m = re.search(r"CF-FACE-" + name + r"-BEGIN\s*\*/(.*?)/\*\s*CF-FACE-"
                  + name + r"-END", src, re.S)
    assert m, f"bloc CF-FACE-{name} absent de mod-face.js"
    return m.group(1)


def js_pairs(name: str) -> list[tuple[str, str]]:
    """[(id, label)] lus dans un bloc marqué."""
    return [(a, b) for a, b in
            re.findall(r'id:\s*"([^"]+)"\s*,\s*label:\s*"([^"]+)"',
                       js_block(name))]


def js_const(name: str) -> str:
    m = re.search(r"\bconst\s+" + name + r"\s*=\s*(.+?);", js_code())
    assert m, f"constante {name} absente de mod-face.js"
    return m.group(1).strip()


# ═════════════════ 1. LE CHIFFRE — DPI effectif, verdict, besoin ════════════

def test_effective_dpi_est_un_rapport_lineaire():
    """Poser une source de 1000 px sur 2000 px de toile à 300 DPI, c'est
    imprimer à 150 DPI. Valeurs ÉCRITES EN DUR, pas recalculées."""
    assert FA.effective_dpi(1000, 2000, 300) == 150.0
    assert FA.effective_dpi(2000, 1000, 300) == 600.0
    assert FA.effective_dpi(815, 815, 300) == 300.0
    assert FA.effective_dpi(1024, 1110, 300) == pytest.approx(276.756, abs=1e-3)
    assert FA.effective_dpi(1630, 1110, 300) == pytest.approx(440.54, abs=1e-2)
    # 600 DPI : la même image posée sur la même carte physique vaut deux fois
    # moins — c'est exactement le piège que la jauge rend visible.
    assert FA.effective_dpi(1024, 2220, 600) == pytest.approx(276.756, abs=1e-3)
    # entrées absurdes : 0, jamais une exception
    assert FA.effective_dpi(0, 100, 300) == 0.0
    assert FA.effective_dpi(100, 0, 300) == 0.0
    assert FA.effective_dpi(100, 100, 0) == 0.0
    assert FA.effective_dpi(float("inf"), 100, 300) == 0.0


def test_le_verdict_est_vert_a_300_rouge_en_dessous():
    """« verte >= 300, rouge en dessous » — la spec ne laisse pas de zone
    grise, et la frontière est INCLUSIVE."""
    assert FA.DPI_TARGET == 300
    assert FA.dpi_verdict(300.0) == "ok"
    assert FA.dpi_verdict(300.0000001) == "ok"
    assert FA.dpi_verdict(299.9) == "low"
    assert FA.dpi_verdict(0.0) == "low"
    # `inf` = source sans plafond de pixels. Ce n'est PLUS le cas vectoriel :
    # voir `test_la_jauge_vectorielle_suit_la_definition_de_la_toile`.
    assert FA.dpi_verdict(math.inf) == "ok"
    assert FA.dpi_verdict(1200.0) == "ok"


def test_min_source_px_dit_ce_qu_il_faudrait():
    """La moitié utile d'un refus. Clash of Decks dit « non » ; on dit
    « il en faudrait 1110 »."""
    assert FA.min_source_px(1110, 300) == 1110      # 300 DPI : identité
    assert FA.min_source_px(2220, 600) == 1110      # 600 DPI : moitié
    assert FA.min_source_px(1110, 150) == 2220      # 150 DPI : double
    assert FA.min_source_px(815, 300) == 815
    assert FA.min_source_px(1000.2, 300) == 1001    # jamais arrondi vers le bas
    assert FA.min_source_px(0, 300) == 0


def test_les_12_formats_disent_la_source_qu_il_faut_a_300_dpi():
    """Sur chaque format, en « couvrir » plein fond perdu, la source qui
    tient 300 DPI est EXACTEMENT la toile. C'est la table de la spec §1.2,
    relue par la fonction de la pièce."""
    attendu = {
        "poker_us": (825, 1125), "poker_eu": (815, 1110),
        "bridge_us": (750, 1125), "bridge_eu": (768, 1146),
        "tarot_us": (900, 1500), "tarot_eu": (898, 1488),
        "mini": (591, 874), "square_eu": (898, 898),
        "domino": (600, 1125), "business": (675, 1125),
        "jumbo": (1125, 1725), "micro": (450, 600),
    }
    for fmt, (w, h) in attendu.items():
        g = CT.geom(fmt, 300)
        assert tuple(g.canvas_px) == (w, h), fmt
        assert FA.min_source_px(w, 300) == w, fmt
        assert FA.min_source_px(h, 300) == h, fmt
        # une source exactement à la taille de la toile vaut 300 DPI pile
        assert FA.dpi_verdict(FA.effective_dpi(w, w, 300)) == "ok", fmt
        # un pixel de moins, et c'est rouge
        assert FA.dpi_verdict(FA.effective_dpi(w - 1, w, 300)) == "low", fmt


def test_le_refus_de_la_barre_est_mesure_pas_subi():
    """650x1024 : la taille sous laquelle Clash of Decks refuse par
    `alert()`. Ici elle est ACCEPTÉE, mesurée, et le chiffre exact est dit."""
    assert FA.BAR_REFUSAL_PX == (650, 1024)
    g = CT.geom("poker_eu", 300)                       # toile 815 x 1110
    dw, dh = FA.fit_rect(650, 1024, g.canvas_px[0], g.canvas_px[1], "cover")
    # « couvrir » : la LARGEUR commande (815/650 = 1,254 > 1110/1024 = 1,084)
    assert dw == pytest.approx(815.0, abs=1e-6)
    assert dh == pytest.approx(1283.9385, abs=1e-3)
    eff = min(FA.effective_dpi(650, dw, 300), FA.effective_dpi(1024, dh, 300))
    assert eff == pytest.approx(239.2638, abs=1e-3)
    assert FA.dpi_verdict(eff) == "low"
    # Le chiffre que la barre n'écrit nulle part, et ce qu'il faudrait :
    assert FA.min_source_px(dw, 300) == 815
    assert FA.min_source_px(dh, 300) == 1284
    # « contenir » ne suffit pas non plus — mais c'est MIEUX, et on le dit.
    dw2, dh2 = FA.fit_rect(650, 1024, g.canvas_px[0], g.canvas_px[1], "contain")
    assert (dw2, dh2) == pytest.approx((704.5898, 1110.0), abs=1e-3)
    eff2 = min(FA.effective_dpi(650, dw2, 300), FA.effective_dpi(1024, dh2, 300))
    assert eff2 == pytest.approx(276.7568, abs=1e-3)
    assert FA.dpi_verdict(eff2) == "low"
    assert eff2 > eff
    # La vraie sortie : la même image POSÉE plus petite tient les 300 DPI.
    dw3, _ = FA.fit_rect(650, 1024, g.canvas_px[0], g.canvas_px[1], "free", 1.0)
    assert FA.effective_dpi(650, dw3, 300) == pytest.approx(300.0, abs=1e-9)


def test_reduire_a_300_dpi_donne_exactement_300():
    """Le bouton « Réduire à 300 DPI exactement » pose l'image en mode libre
    à l'échelle dpi/300. Le résultat doit tomber PILE, sinon la correction
    proposée serait un mensonge d'un pixel."""
    for dpi in (150, 300, 600):
        for src in (512, 1024, 1997):
            dw, dh = FA.fit_rect(src, src, 1000, 1400, "free", dpi / 300.0)
            assert FA.effective_dpi(src, dw, dpi) == pytest.approx(300.0, abs=1e-9)


# ═════════════════ 2. LE CATALOGUE — 72 DESSINS, 0 octet réseau ═════════════

def test_le_catalogue_depasse_le_seuil_de_60():
    """Le duel a mesuré la galerie d'en face : 300 dessins BITMAP en
    723x1024 (01..300 répondent 200, 301 répond 404). Le nôtre en comptait
    72 — deux paliers sous le haut du barème, que le critique a nommés :
    100 puis 250. Deux compositions de plus le portent à 108 : le palier de
    100 est franchi, et sans une seule recoloration de plus."""
    assert len(FA.PALETTES) == 12
    assert len(FA.SUBJECTS) == 18
    assert len(FA.COMPOS) == 6
    assert len(FA.CATALOG) == 108
    assert FA.DRAWINGS == 108
    assert FA.COMBINATIONS == 1296
    assert len(FA.CATALOG) >= 60, "seuil de la spec : >= 60 faces de départ"
    assert len(FA.CATALOG) >= 100, "le palier nommé par le duel"


def test_le_catalogue_compte_des_DESSINS_pas_des_recolorations():
    """LE REPROCHE DU DUEL, retourné en test.

    Les deux critiques ont compté à la main : « 72 faces » annoncées, mais
    « Tour de guet — Braise » et « Tour de guet — Sylve » étaient le MÊME
    dessin recoloré. Le seuil « >= 60 » était tenu à la lettre et trahi dans
    l'esprit. Ce test refuse la triche : ce qui est compté doit être le nombre
    de couples (sujet, composition) DISTINCTS, et il doit atteindre le seuil
    à lui seul, sans l'aide d'une seule palette."""
    dessins = {(c["subject"], c["compo"]) for c in FA.CATALOG}
    assert len(dessins) == 108, "deux entrées partagent le même dessin"
    assert len(dessins) >= 60, "le seuil doit tenir SANS compter les palettes"
    # et le compte des combinaisons ne se confond jamais avec celui des dessins
    assert FA.COMBINATIONS == FA.DRAWINGS * len(FA.PALETTES) == 1296
    assert FA.DRAWINGS < FA.COMBINATIONS


def test_le_catalogue_est_sans_doublon_et_equilibre():
    """(5*s + 2*c) % 12 : chaque palette sort exactement 9 fois, chaque sujet
    6 fois (une par composition), chaque composition 18 fois. Une grille où le
    même dessin revient trois fois de suite perdrait le duel contre les 300
    illustrations distinctes de la barre.

    LE PAS A CHANGÉ AVEC LE NOMBRE DE COMPOSITIONS, et c'est le point : à 6
    compositions, l'ancien pas 3 ne prenait que quatre décalages distincts
    (0,3,6,9,0,3) et le compte par palette tombait entre 8 et 10. Ce test
    aurait laissé passer « à peu près équilibré » s'il avait été écrit en
    intervalle ; il est écrit en ÉGALITÉ, et c'est lui qui a imposé le pas
    2 (six décalages distincts : 0,2,4,6,8,10)."""
    ids = FA.catalog_ids()
    assert len(set(ids)) == len(ids) == 108
    from collections import Counter
    par_sujet = Counter(c["subject"] for c in FA.CATALOG)
    par_pal = Counter(c["palette"] for c in FA.CATALOG)
    par_compo = Counter(c["compo"] for c in FA.CATALOG)
    assert set(par_sujet.values()) == {6}, par_sujet
    assert set(par_pal.values()) == {9}, par_pal
    assert set(par_compo.values()) == {18}, par_compo
    for c in FA.CATALOG:
        assert c["vector"] is True, c["id"]
        assert c["id"] == f"face_{c['palette']}_{c['compo']}_{c['subject']}"
        assert c["seed"] == FA.fnv1a32(c["id"]) < 2 ** 32
        assert c["label"] and " — " in c["label"]


def test_chaque_composition_montre_les_douze_palettes():
    """Sans cette contrainte, une composition entière aurait pu ne connaître
    que trois teintes (c'est ce que donnait une répartition naïve `% 12` sur
    l'index plat : compos 0 -> palettes 0, 4, 8 seulement)."""
    vues = {}
    for c in FA.CATALOG:
        vues.setdefault(c["compo"], set()).add(c["palette"])
    for compo, pals in vues.items():
        assert len(pals) == 12, f"{compo} ne montre que {len(pals)} palettes"


def test_les_anciens_identifiants_de_catalogue_restent_lisibles():
    """Un jeu enregistré AVANT les compositions porte `face_<pal>_<sujet>`.
    Il doit rouvrir sur son dessin, pas sur un cadre vide."""
    assert FA.legacy_art_id("face_ember_tower") == "face_ember_vista_tower"
    assert FA.legacy_art_id("face_ember_vista_tower") == "face_ember_vista_tower"
    assert FA.legacy_art_id("") == ""
    assert FA.legacy_art_id("img:truc.png") == "img:truc.png"
    assert FA.legacy_art_id("face_inconnue_bidule") == "face_inconnue_bidule"
    ids = set(FA.catalog_ids())
    for pal, _ in FA.PALETTES:
        for sub, _ in FA.SUBJECTS:
            assert FA.legacy_art_id(f"face_{pal}_{sub}") in ids or \
                f"face_{pal}_vista_{sub}" not in ids


def test_fnv1a32_est_deterministe_et_borne():
    """La graine fait la scène : montagnes, nuages, cailloux. Si elle
    bougeait entre deux rendus, l'aperçu et le fichier livré différeraient —
    le bug WYSIWYG que la spec interdit (risque 2)."""
    assert FA.fnv1a32("") == 2166136261
    assert FA.fnv1a32("a") == 0xE40C292C
    assert FA.fnv1a32("foobar") == 0xBF9CF968
    for c in FA.CATALOG:
        assert 0 <= FA.fnv1a32(c["id"]) < 2 ** 32


def test_zero_octet_reseau_et_zero_dependance():
    """Le catalogue n'est pas un dossier de PNG : c'est une table et un
    peintre. Aucune URL externe, aucun CDN, aucun `import` — la règle 10 de
    la spec, vérifiée sur la source servie."""
    src = js_src()
    for motif in ("http://", "https://", "cdn.", "//unpkg", "//cdnjs",
                  "importScripts", "from \"http"):
        assert motif not in src, f"dépendance externe dans mod-face.js : {motif}"
    assert "assets/face/" not in src, \
        "le catalogue ne doit pas dépendre de fichiers servis"


# ═════════════════ 3. LE MIROIR écran / table de référence ══════════════════

def test_les_palettes_du_js_sont_celles_de_face_py():
    assert js_pairs("PALETTES") == [(p, l) for p, l in FA.PALETTES]


def test_les_sujets_du_js_sont_ceux_de_face_py():
    assert js_pairs("SUBJECTS") == [(s, l) for s, l in FA.SUBJECTS]


def test_les_compositions_du_js_sont_celles_de_face_py():
    assert js_pairs("COMPOS") == [(c, l) for c, l in FA.COMPOS]
    # ...et chacune a bien un peintre : une composition déclarée sans peintre
    # retomberait silencieusement sur « vista », donc 4 étiquettes pour un
    # seul dessin — exactement la triche que ce module vient de corriger.
    src = js_src()
    bloc = src[src.index("const COMPO_PAINT = {"):]
    for cid, _ in FA.COMPOS:
        assert re.search(r"\n    " + cid + r"\(ctx, W, H, P, R, u, fp\)", bloc), \
            f"la composition {cid} n'a pas de peintre dans COMPO_PAINT"


def test_les_seuils_du_js_sont_ceux_de_face_py():
    assert js_const("DPI_TARGET") == str(FA.DPI_TARGET)
    assert js_const("MAX_IMPORT_PX") == str(FA.MAX_IMPORT_PX)
    assert js_const("PAL_STRIDE").startswith(str(FA.PAL_STRIDE))
    assert str(FA.COMPO_STRIDE) in js_const("PAL_STRIDE")
    assert '"cover", "contain", "free"' in js_const("FIT_MODES")
    assert tuple(FA.FIT_MODES) == ("cover", "contain", "free")


def test_les_sujets_du_js_ont_tous_un_peintre():
    """18 sujets déclarés, 18 peintres. Un sujet sans peintre retombe sur
    `tower` : le catalogue afficherait deux fois le même dessin sous deux
    noms — le défaut même qu'on vient de corriger."""
    src = js_src()
    bloc = src[src.index("const SUB_PAINT = {"):src.index("const COMPO_PAINT = {")]
    for sid, _ in FA.SUBJECTS:
        assert re.search(r"\n    " + sid + r"\(ctx, W, H, hz, P, R, u\)", bloc), \
            f"le sujet {sid} n'a pas de peintre dans SUB_PAINT"


def test_les_amorces_d_invite_parlent_de_CARTE():
    """Une amorce utile impose le CADRAGE d'une face de carte. « un beau
    dragon » n'en est pas une."""
    seeds = FA.prompt_seeds()
    assert len(seeds) >= 12
    for s in seeds:
        assert s["label"] and len(s["prompt"]) > 40
        assert "carte à jouer" in s["prompt"]
        assert "fond perdu" in s["prompt"]
    # le JS sert exactement les mêmes libellés
    js_labels = re.findall(r'\["([^"]+)",\s*"', js_src())
    for s in seeds:
        assert s["label"] in js_labels, s["label"]


# ═════════════════ 4. L'ERGONOMIE, VÉRIFIÉE SUR LA SOURCE ═══════════════════

def test_le_bandeau_donne_le_chiffre_et_deux_corrections():
    """Un bandeau, le DPI réel, et DEUX corrections en un clic — jamais un
    `alert()` natif, modal et sans chiffre.

    CE QUI A CHANGÉ CE TOUR. Le bandeau s'intitulait « Alerte non bloquante »
    et disait « L'export reste possible ». Ces mots-là ne renseignent pas un
    utilisateur : ils décrivent le COMPORTEMENT du contrôle à qui l'évalue.
    Le titre redevient une consigne (« Avant d'imprimer ») ; les CHIFFRES —
    le DPI mesuré, la cible — restent, et les deux boutons aussi."""
    src = js_code()
    assert not re.search(r"(?<![\w.])alert\s*\(", src), \
        "un alert() natif bloquerait l'utilisateur"
    assert "cf-face-warn" in src
    assert 'data-fix="shrink"' in src and 'data-fix="contain"' in src

    # les DEUX branches (bitmap et vectorielle) portent le même titre d'action
    assert src.count(r"<b>Avant d\'imprimer</b>") == 2

    # et le chiffre mesuré est toujours dans le bandeau, des deux côtés
    jauge = src[src.index("function paintGauge()"):src.index("function fixShrink()")]
    assert "Math.round(rast) + ' DPI" in jauge, "branche vectorielle : le DPI mesuré"
    assert "Math.round(LAST.eff) + ' DPI" in jauge, "branche bitmap : le DPI mesuré"
    assert "+ DPI_TARGET + ' DPI d\\'impression" in jauge, "la cible est nommée"


def test_le_placement_a_la_souris_et_au_clavier():
    """Molette = zoom, glisser = pan, Alt+glisser = rotation, et TROIS champs
    numériques éditables (x, y, échelle) — la barre n'a que six boutons."""
    src = js_src()
    assert '"wheel"' in src, "molette absente"
    assert '"pointerdown"' in src and '"pointermove"' in src, "glisser absent"
    assert "altKey" in src, "Alt+glisser (rotation) absent"
    for champ in ("cf-face-x", "cf-face-y", "cf-face-scale",
                  "cf-face-scaley", "cf-face-rot"):
        assert 'id="' + champ + '"' in src, f"champ numérique {champ} absent"
    for k in ("ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"):
        assert k in src, f"raccourci {k} absent"
    assert '"paste"' in src, "coller (Ctrl+V) absent"
    assert '"drop"' in src, "glisser-déposer absent"
    assert "multiple" in src, "import par lot absent"
    assert "lock" in src, "verrou de proportions absent"


def test_une_face_ia_en_un_seul_appel_et_posee():
    """« une face IA generee en <= 1 appel, resultat pose sur la carte sans
    copier-coller de nom de fichier » : un seul point d'appel, suivi d'un
    `setArt` — pas d'un champ à remplir à la main."""
    src = js_code()
    appels = re.findall(r"CF\.images\.generate\s*\(", src)
    assert len(appels) == 1, f"{len(appels)} appels de génération (attendu 1)"
    bloc = src[src.index("async function generate("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "CF.images.generate" in bloc
    assert 'setArt("img:" + files[0]' in bloc, \
        "le résultat doit être POSÉ, pas laissé à recopier"


def test_la_route_d_image_est_la_bonne():
    """MESURE : `/api/images/file/<nom>` — ce que construit `CF.imageURL` —
    tombe sur le catch-all de la SPA et rend 200 + du HTML (piège n°7). La
    vraie route est `GET /api/images/{filename}` (routes.py). Le module
    construit donc l'URL lui-même ; ce test empêche de « simplifier » en
    revenant à CF.imageURL."""
    src = js_code()
    assert '"/api/images/" + encodeURIComponent' in src
    assert "/api/images/file/" not in src
    assert "CF.imageURL(" not in src


def test_le_painter_est_a_z_20_et_seul():
    src = js_src()
    bloc = re.search(r"painters:\s*\[(.*?)\]", src, re.S)
    assert bloc, "aucun painter déclaré"
    zs = [int(z) for z in re.findall(r"(?<![\w$.-])z:\s*(-?\d+)", bloc.group(1))]
    assert zs == [20], f"z alloués à `face` : [20], trouvés {zs}"


def test_la_precedence_de_l_illustration_est_celle_de_la_spec():
    """card.art ?? card.fields["art"] ?? doc.face.default_art (spec §2.3)."""
    src = js_src()
    bloc = src[src.index("function resolveArtId("):]
    bloc = bloc[:bloc.index("\n  }")]
    i_own = bloc.index("card.art")
    i_col = bloc.index("fields.art")
    i_def = bloc.index("f.default_art")
    assert i_own < i_col < i_def, "la précédence gelée n'est pas respectée"


def test_le_module_respecte_les_regles_de_cloisonnement():
    """R8 : le routeur ne déclare que des chemins RELATIFS à son sous-préfixe
    `/api/cards/<did>/face` et n'importe le routeur d'aucune autre pièce.
    R11 : la source commence par "use strict". R4/R5 : la feuille et les ids
    portent le préfixe de la pièce."""
    chemins = sorted(r.path for r in FA.router.routes)
    # LA LISTE EST UN PIN, PAS UNE FORMALITÉ : elle compte les routes que la
    # pièce ouvre. La phase 5 en ajoute DEUX — l'état de la série et la
    # campagne — et la seule qui dépense est un POST nommé. La phase 6 ajoute
    # le RESCAPAGE : un POST qui ne peut PAS dépenser (PIL et le juge, en
    # local — aucun `_payer` sur son chemin).
    assert chemins == ["/ai-models", "/png/{fmt}/{dpi}", "/serie",
                       "/serie/generer", "/serie/rescaper"], chemins
    for p in chemins:
        assert not p.startswith("/api"), f"chemin absolu interdit : {p}"
    py = pathlib.Path(FA.__file__).read_text(encoding="utf-8")
    for autre in ("frame", "type", "data", "solid", "texture", "print", "gltf"):
        assert f"from .{autre} import" not in py and f"from . import {autre}" not in py, \
            "aucune pièce n'importe le routeur d'une autre (règle 8)"
    src = js_src()
    assert re.match(r"\A(?:\s|/\*.*?\*/|//[^\n]*\n)*[\"']use strict[\"']\s*;",
                    src, re.S), 'mod-face.js doit commencer par "use strict"'
    assert CSS.is_file()
    css = CSS.read_text(encoding="utf-8")
    for sel in re.findall(r"^\s*([.#][^{@\n]+)\{", css, re.M):
        assert ".cf-face" in sel, f"sélecteur global interdit : {sel.strip()!r}"
    for dom_id in re.findall(r'id="([^"]+)"', src):
        assert dom_id.startswith("cf-face-"), dom_id


# ═════════════════ 5. fit_rect — la même géométrie des deux côtés ═══════════

def test_fit_rect_couvre_contient_et_libre():
    # cover : remplit, déborde sur l'autre axe
    assert FA.fit_rect(100, 100, 200, 400, "cover") == (400.0, 400.0)
    # contain : tient entièrement
    assert FA.fit_rect(100, 100, 200, 400, "contain") == (200.0, 200.0)
    # free : 1 pixel source = 1 pixel toile
    assert FA.fit_rect(100, 100, 200, 400, "free") == (100.0, 100.0)
    # l'échelle multiplie le facteur de base sans quitter le mode
    assert FA.fit_rect(100, 100, 200, 400, "cover", 2.0) == (800.0, 800.0)
    assert FA.fit_rect(100, 100, 200, 400, "contain", 0.5) == (100.0, 100.0)
    # bornes et entrées absurdes : jamais d'exception
    assert FA.fit_rect(0, 100, 200, 400, "cover") == (0.0, 0.0)
    assert FA.fit_rect(100, 100, 200, 400, "cover", 0) == \
        FA.fit_rect(100, 100, 200, 400, "cover", 1.0)
    assert FA.fit_rect(100, 100, 200, 400, "cover", 1e9)[0] == 400.0 * 12.0
    assert FA.fit_rect(100, 100, 200, 400, "inconnu") == \
        FA.fit_rect(100, 100, 200, 400, "cover")


def test_cover_ne_laisse_jamais_de_trou_sur_les_12_formats():
    """Invariant : en « couvrir », la pose recouvre la toile ENTIÈRE, fond
    perdu compris — sinon la découpe montrerait du blanc au bord."""
    for fmt in CT.FORMATS:
        g = CT.geom(fmt, 300)
        bw, bh = g.canvas_px
        for src in ((650, 1024), (1024, 1024), (4096, 2160), (300, 900)):
            dw, dh = FA.fit_rect(src[0], src[1], bw, bh, "cover")
            assert dw >= bw - 1e-6 and dh >= bh - 1e-6, (fmt, src, dw, dh)
            dw2, dh2 = FA.fit_rect(src[0], src[1], bw, bh, "contain")
            assert dw2 <= bw + 1e-6 and dh2 <= bh + 1e-6, (fmt, src)


# ═══════ 6. LE FICHIER LIVRÉ — « 300 DPI » écrit DANS les octets ════════════
#
# LE DÉFAUT MESURÉ DU DUEL : « Chunks PNG relus un par un sur les deux
# fichiers : AUCUN des deux ne porte de chunk pHYs. Le fichier "300 DPI" ne
# déclare donc aucune résolution physique ; ouvert dans un outil de mise en
# page il tombe à 72 DPI, soit 11,32 x 15,42 pouces au lieu de 69 x 94 mm. »
# Tout ce bloc existe pour que cela ne puisse plus arriver sans faire rougir
# la suite.

def test_dpi_vers_pixels_par_metre():
    """11811 px/m = la valeur que la spec §4 P7 exige pour 300 DPI, et que
    nanDECK écrit. Arrondi demi-haut, jamais tronqué."""
    assert FA.dpi_to_ppm(300) == 11811          # 11811,0236...
    assert FA.dpi_to_ppm(600) == 23622
    assert FA.dpi_to_ppm(150) == 5906           # 5905,51 -> 5906
    assert FA.dpi_to_ppm(72) == 2835
    assert FA.dpi_to_ppm(1200) == 47244
    assert FA.ppm_to_dpi(11811) == pytest.approx(299.9994, abs=1e-4)
    for mauvais in (0, -1, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            FA.dpi_to_ppm(mauvais)


def test_le_png_d_un_canvas_n_a_PAS_de_phys_et_en_recoit_un():
    """La mesure du duel, refaite ici — puis corrigée."""
    brut = _png(815, 1110)
    assert FA.png_phys(brut) is None, \
        "PIL comme canvas.toBlob : aucun pHYs. C'est le point de départ."
    assert [t for t, _ in FA.png_chunks(brut)][0] == "IHDR"
    stampe = FA.png_with_phys(brut, 300)
    assert FA.png_phys(stampe) == (11811, 11811, 1)
    types = [t for t, _ in FA.png_chunks(stampe)]
    assert types.count("pHYs") == 1, "deux pHYs = fichier invalide"
    assert types[0] == "IHDR"
    # L'INVARIANT DE LA SPEC PNG, énoncé comme tel : `pHYs` avant le premier
    # `IDAT`. Ce n'est PAS « pHYs en position 1 » : l'en-tête porte désormais
    # aussi sRGB/gAMA/cHRM, et une assertion de position aurait rougi pour un
    # fichier parfaitement conforme — le genre d'assertion d'échafaudage qui
    # finit par condamner sa propre suite.
    assert types.index("pHYs") < types.index("IDAT"), \
        "pHYs doit précéder le premier IDAT (spec PNG)"
    assert types[-1] == "IEND"


def test_le_fichier_estampille_est_relu_par_PIL_a_300_dpi():
    """Le test qui compte vraiment : ce n'est pas notre lecteur qui relit,
    c'est PIL — la bibliothèque qu'un imprimeur a en face de lui."""
    stampe = FA.png_with_phys(_png(815, 1110), 300)
    im = Image.open(io.BytesIO(stampe))
    assert im.size == (815, 1110)
    assert im.info["dpi"] == pytest.approx((299.9994, 299.9994), abs=1e-4)
    # la taille PHYSIQUE annoncée : 69 x 94 mm à 0,02 mm près, pas 11 pouces
    larg_mm = im.size[0] / im.info["dpi"][0] * 25.4
    haut_mm = im.size[1] / im.info["dpi"][1] * 25.4
    g = CT.geom("poker_eu", 300)
    assert larg_mm == pytest.approx(g.trim_mm[0] + 2 * g.bleed_mm, abs=0.03)
    assert haut_mm == pytest.approx(g.trim_mm[1] + 2 * g.bleed_mm, abs=0.03)
    # sans pHYs, le même fichier vaut 11,32 x 15,42 pouces : le chiffre du duel
    assert (815 / 72, 1110 / 72) == pytest.approx((11.319, 15.417), abs=1e-3)


def test_les_pixels_ne_sont_PAS_touches_par_l_estampillage():
    """« L'aperçu est le fichier livré » (risque 2) : si l'estampillage
    ré-encodait l'image, le backend deviendrait un second moteur de rendu."""
    brut = _png(64, 96)
    stampe = FA.png_with_phys(brut, 600)
    a = Image.open(io.BytesIO(brut)).convert("RGBA")
    b = Image.open(io.BytesIO(stampe)).convert("RGBA")
    assert a.tobytes() == b.tobytes()
    # les IDAT sont recopiés octet pour octet, pas ré-compressés
    ia = [p for t, p in FA.png_chunks(brut) if t == "IDAT"]
    ib = [p for t, p in FA.png_chunks(stampe) if t == "IDAT"]
    assert ia == ib


def test_un_phys_deja_present_est_remplace_pas_duplique():
    une = FA.png_with_phys(_png(64, 96), 300)
    deux = FA.png_with_phys(une, 600)
    assert [t for t, _ in FA.png_chunks(deux)].count("pHYs") == 1
    assert FA.png_phys(deux) == (23622, 23622, 1)


def test_le_crc_de_chaque_chunk_est_juste():
    """Un CRC faux fait rejeter le fichier par les décodeurs stricts — et le
    nôtre passerait quand même, puisque c'est nous qui l'avons écrit."""
    data = FA.png_with_phys(_png(120, 160), 300)
    p = 8
    vus = 0
    while p + 8 <= len(data):
        (ln,) = struct.unpack(">I", data[p:p + 4])
        typ = data[p + 4:p + 8]
        charge = data[p + 8:p + 8 + ln]
        (crc,) = struct.unpack(">I", data[p + 8 + ln:p + 12 + ln])
        assert crc == zlib.crc32(typ + charge) & 0xFFFFFFFF, typ
        vus += 1
        if typ == b"IEND":
            break
        p += 12 + ln
    assert vus >= 3


def test_les_octets_qui_ne_sont_pas_un_png_levent_proprement():
    for mauvais in (b"", b"pas un png", b"\x89PNG\r\n\x1a\n", b"\x89PNG\r\n\x1a\n" + b"\x00" * 40):
        with pytest.raises(ValueError):
            FA.png_chunks(mauvais)


def test_la_route_estampille_le_png_du_moteur():
    """De bout en bout, par HTTP, comme le fait le panneau."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    brut = _png(*g.canvas_px)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300", content=brut,
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/png"
    assert r.headers["x-cf-phys-ppm"] == "11811"
    assert r.headers["x-cf-canvas-px"] == "815x1110"
    assert FA.png_phys(r.content) == (11811, 11811, 1)
    assert Image.open(io.BytesIO(r.content)).info["dpi"][0] == \
        pytest.approx(299.9994, abs=1e-4)
    # 600 DPI : deux fois plus de pixels, LA MEME taille physique
    g6 = CT.geom("poker_eu", 600)
    r6 = _api("POST", f"/api/cards/{did}/face/png/poker_eu/600",
              content=_png(*g6.canvas_px), headers={"content-type": "image/png"})
    assert r6.status_code == 200, r6.text
    assert FA.png_phys(r6.content) == (23622, 23622, 1)
    im6 = Image.open(io.BytesIO(r6.content))
    assert im6.size == (1630, 2220)
    assert im6.size[0] / im6.info["dpi"][0] == pytest.approx(815 / 299.9994, abs=1e-3)


def test_la_route_refuse_d_estampiller_une_trame_qui_ment():
    """LE point : « 300 DPI » n'est pas une étiquette qu'on colle, c'est un
    contrôle. Une trame qui ne fait pas la toile est refusée, avec les deux
    nombres dans le message."""
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300", content=_png(400, 400),
             headers={"content-type": "image/png"})
    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert "400 x 400" in d and "815 x 1110" in d


def test_la_route_ne_fait_jamais_500_sur_une_entree_absurde():
    """« Un corps mal formé ne doit JAMAIS faire 500 » (spec §2.5)."""
    did = _deck()
    cas = [
        (f"/api/cards/{did}/face/png/poker_eu/300", b"", 400),
        (f"/api/cards/{did}/face/png/poker_eu/300", b"pas un png", 400),
        (f"/api/cards/{did}/face/png/pas_un_format/300", _png(10, 10), 400),
        (f"/api/cards/{did}/face/png/poker_eu/40", _png(10, 10), 400),
        (f"/api/cards/{did}/face/png/poker_eu/9000", _png(10, 10), 400),
        ("/api/cards/pas_un_deck/face/png/poker_eu/300", _png(10, 10), 400),
    ]
    for chemin, corps, attendu in cas:
        r = _api("POST", chemin, content=corps, headers={"content-type": "image/png"})
        assert r.status_code == attendu, f"{chemin} -> {r.status_code} {r.text[:120]}"
        assert "json" in r.headers.get("content-type", "")
        assert isinstance(r.json().get("detail"), str)
    # un DPI non entier ne passe pas non plus, et ne casse rien
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/trois-cents", content=_png(10, 10))
    assert r.status_code in (400, 404, 422), r.status_code


def test_le_panneau_passe_par_le_moteur_puis_par_le_backend():
    """La chaîne de provenance, lue sur la source servie : le blob vient de
    `CF.cardBlob` (le moteur unique), il est estampillé par `M.api.blob`, et
    le chiffre affiché est RELU dans les octets rendus — pas celui demandé."""
    src = js_code()
    bloc = src[src.index("async function downloadPng("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "CF.cardBlob(CF.current()" in bloc, "le fichier doit venir du moteur"
    assert 'M.api.blob("POST", "png/"' in bloc, "l'estampillage passe par le backend"
    assert "readPngFacts(stamped)" in bloc, "le chiffre affiché doit être RELU"
    assert "CF.download(stamped" in bloc, "on télécharge la version estampillée"
    i_lu = bloc.index("readPngFacts(stamped)")
    i_aff = bloc.index("pngReport(")
    assert i_lu < i_aff, "on relit AVANT d'afficher"
    # et le rapport ne lit QUE la relecture : aucune des valeurs demandées
    # (g.dpi, g.canvas_px) ne doit y apparaître.
    rap = src[src.index("function pngReport("):]
    rap = rap[:rap.index("\n  }")]
    for interdit in ("g.dpi", "g.canvas_px", "g.fmt"):
        assert interdit not in rap, \
            f"{interdit} dans le rapport : ce serait afficher la demande, pas la mesure"


# ═══════ 7. AUCUN NOMBRE AFFICHÉ N'EST UNE PROMESSE ═════════════════════════
#
# Un critique a trouvé, sur une autre pièce, un badge « 16 bits » mensonger.
# Ici les trois nombres reprochés étaient : « 72 faces » (12 dessins),
# « 600 ou 1200 DPI » (la barre n'offre que 150/300/600), et « 300 DPI » sur
# une face vectorielle (où la jauge ne mesure rien).

def test_l_ecran_n_annonce_pas_une_definition_qu_il_n_offre_pas():
    """`CF.DPIS` vaut [150, 300, 600] : « 1200 DPI » ne peut pas être promis
    à l'écran. Le nombre affiché est lu sur `CF.DPIS`, pas écrit à la main."""
    core = (ROOT / "frontend" / "cardforge" / "js" / "core.js").read_text(encoding="utf-8")
    m = re.search(r"const DPIS = \[([^\]]+)\]", core)
    assert m, "impossible de lire CF.DPIS dans core.js"
    offertes = [int(x) for x in m.group(1).split(",")]
    assert offertes == [150, 300, 600]
    src = js_code()
    # « 1200 » reste légal comme borne de champ (échelle en %) ; ce qui est
    # interdit, c'est de le présenter comme une DÉFINITION.
    for promesse in ("1200 DPI", "ou 1200", "1200 dpi", "600 ou 1200"):
        assert promesse not in src, \
            f"« {promesse} » : la barre n'offre pas cette définition"
    assert 'max="1200"' in src, "(la borne de champ, elle, est légitime)"
    assert "(CF.DPIS || []).join" in src, \
        "les définitions affichées doivent être LUES sur le contrat"


def test_la_jauge_vectorielle_suit_la_definition_de_la_toile():
    """LE BADGE ÉTAIT FAUX, ET LA MESURE LE DIT.

    L'écran affichait, sur une face du catalogue, « ∞ vectoriel — Aucune
    perte possible, la jauge ne s'applique pas ». Relevé au rig après avoir
    cliqué 150 dans la barre de format : la MÊME phrase, mot pour mot, avec
    l'alerte toujours cachée — pendant que `CF.renderCard` rendait une toile
    de 407 x 555 px pour 69,0 x 94,0 mm, soit 150 DPI. Le badge lisait le
    GENRE de la source au lieu de mesurer la trame livrée.

    Une face vectorielle est rasterisée à la taille de la pose, dans la toile
    de destination : source et dessin ont le même nombre de pixels, donc son
    DPI effectif vaut EXACTEMENT la définition de la toile."""
    # (1) la fonction de référence, sur les trois définitions offertes
    assert FA.vector_effective_dpi(150) == 150.0
    assert FA.vector_effective_dpi(300) == 300.0
    assert FA.vector_effective_dpi(600) == 600.0
    assert FA.vector_effective_dpi(150) != math.inf, "l'infini était le mensonge"
    # (2) et le verdict qui en découle : ROUGE à 150, vert à 300 et 600
    assert FA.dpi_verdict(FA.vector_effective_dpi(150)) == "low"
    assert FA.dpi_verdict(FA.vector_effective_dpi(300)) == "ok"
    assert FA.dpi_verdict(FA.vector_effective_dpi(600)) == "ok"
    # (3) la géométrie qui a servi de preuve : la toile de 150 DPI EST à 150
    g150 = CT.geom("poker_eu", 150)
    assert list(g150.canvas_px) == [407, 555], "la toile relevée au rig"
    largeur_mm = g150.canvas_px[0] * 25.4 / 150.0
    assert g150.canvas_px[0] * 25.4 / largeur_mm == pytest.approx(150.0, abs=1e-9)
    # (4) l'écran ne peut plus dire le contraire
    src = js_code()
    bloc = src[src.index("if (LAST.vector) {"):]
    bloc = bloc[:bloc.index("const ok = LAST.eff")]
    assert "Aucune perte possible" not in bloc, "la promesse démentie par la trame"
    assert "applique pas" not in bloc, "la jauge s'applique, et elle mesure"
    assert "∞" not in bloc, "l'infini n'est la densité d'aucune trame"
    assert "cf-face-gbar" in bloc, "la barre est là, comme pour un bitmap"
    assert "cf-face-ok" in bloc and "cf-face-low" in bloc, "vert OU rouge"
    assert "rasterDpi(g)" in bloc, "le chiffre est mesuré, pas recopié"
    assert "cf-face-warn" in bloc, "l'alerte non bloquante s'affiche aussi ici"
    # (5) et la mesure est un aller-retour dans la conversion du CORE, pas une
    #     recopie de `g.dpi` : une dérive du core ferait diverger les deux.
    m = re.search(r"function rasterDpi\(g\) \{(.+?)\n  \}", src, re.S)
    assert m, "rasterDpi absente"
    assert "g.px2mm(px)" in m.group(1) and "25.4" in m.group(1)
    assert "return g.dpi" not in m.group(1), "ce serait recopier, pas mesurer"
    # (6) le garde-fou de l'export suit la jauge, plus le genre de la source
    exp = src[src.index("async function downloadPng("):]
    exp = exp[:exp.index("\n  }")]
    assert "!LAST.vector && LAST.eff" not in exp, \
        "le vectoriel sous 300 DPI passait sans confirmation"
    assert "LAST.vector\n      ? rast + 1e-9 < DPI_TARGET" in exp


def test_le_catalogue_est_annonce_pour_ce_qu_il_est():
    """Les trois nombres de l'écran sont CALCULÉS depuis les tables. Aucun
    « 72 » écrit à la main ne peut survivre à un ajout de sujet."""
    src = js_code()
    assert "DRAWINGS = SUBJECTS.length * COMPOS.length" in src
    assert "COMBINATIONS = DRAWINGS * PALETTES.length" in src
    # LES DEUX COMPTES RESTENT SÉPARÉS — c'est le fond du reproche des deux
    # critiques (« 72 faces » pour 12 dessins recolorés six fois). Ce qui a
    # changé, c'est le REGISTRE : la phrase ne plaide plus sa propre cause,
    # elle pose la multiplication et laisse le lecteur la refaire.
    compte = src[src.index('<p class="hint cf-face-count">'):]
    compte = compte[:compte.index("</p>'")]
    assert "SUBJECTS.length" in compte and "COMPOS.length" in compte
    assert "DRAWINGS + ' dessins" in compte, "les dessins, comptés à part"
    assert "PALETTES.length" in compte and "COMBINATIONS" in compte, \
        "les recolorations, comptées à part elles aussi"
    for chiffre in ("18", "108", "12", "1296"):
        assert chiffre not in compte, \
            f"« {chiffre} » écrit en dur : un ajout de sujet le rendrait faux"
    assert "72 faces" not in src and "72 dessins" not in src, \
        "les comptes s'écrivent en variables, jamais en dur"


def test_le_zero_octet_reseau_est_compte_et_non_affirme():
    """« Aucun octet réseau » écrit par le produit lui-même n'est pas une
    mesure. L'écran compte maintenant les entrées de `performance` avant et
    après avoir peint la grille, et affiche le nombre d'IMAGES téléchargées —
    quel qu'il soit."""
    src = js_code()
    assert 'performance.getEntriesByType("resource")' in src
    assert "image téléchargée" in src
    assert "aucun octet réseau" not in src, \
        "l'affirmation non mesurée doit avoir disparu"
    assert "isImageEntry" in src


def test_la_fenetre_d_illustration_peut_etre_plus_petite_que_la_carte():
    """« fenêtre 815 x 1110 px » = la toile entière, le réglage le plus
    permissif : rien ne démontrait le recadrage. Quatre fenêtres du domaine
    existent maintenant, toutes calculées depuis `CF.geom()` (spec §3 : aucun
    module ne recalcule un pixel à partir des mm)."""
    src = js_code()
    bloc = src[src.index("function artWindow(g) {"):]
    bloc = bloc[:bloc.index("\n  }")]
    for mode in ("trim", "safe", "art34", "auto"):
        assert '"' + mode + '"' in bloc, f"fenêtre {mode} absente"
    assert "g.trim_px" in bloc and "g.safe_px" in bloc and "g.safe_off_px" in bloc
    assert "canvas_px" in bloc
    assert "/ 25.4" not in bloc, "aucune conversion mm->px recalculée ici"
    # les tailles annoncées sont celles de la spec §1.2
    g = CT.geom("poker_eu", 300)
    assert tuple(g.canvas_px) == (815, 1110)
    assert tuple(g.trim_px) == (744, 1039)
    assert tuple(g.safe_px) == (673, 969)


def test_le_verrou_de_proportions_dit_qui_commande():
    """Deux champs « Échelle » et « Hauteur » côte à côte : le second est
    grisé quand le verrou tient (il l'était déjà — mesure : l'attribut
    `disabled`), et il DIT maintenant qu'il recopie le premier."""
    src = js_src()
    bloc = src[src.index('<span class="lbl">\' + (f.lock === false ? "Hauteur"'):]
    bloc = bloc[:bloc.index("Rotation")]
    assert '"Hauteur = Échelle"' in bloc
    assert "disabled" in bloc
    assert "verrou de proportions actif" in bloc


# ═══════ 8. LE TOUR 2 — ce que les deux critiques ont mesuré contre nous ════
#
# Chacun des tests qui suivent correspond à UN reproche chiffré, et il échoue
# si la correction repart. On ne teste pas « la fonctionnalité marche » : on
# teste que le défaut nommé ne peut pas revenir.


def test_le_fichier_livre_declare_son_espace_de_couleur():
    """REPROCHE (les deux critiques) : « ni iCCP, ni sRGB, ni gAMA, ni cHRM :
    l'imprimeur reçoit du RVB sans profil et devra deviner ».

    La spec PNG (11.3.3.4/11.3.3.5) interdit `iCCP` ET `sRGB` ensemble, et
    fait de `sRGB` la déclaration canonique — un octet d'intention plutôt
    qu'une copie de 3 kio du même profil. `gAMA`/`cHRM` l'accompagnent pour
    les lecteurs qui ne connaissent pas `sRGB`, avec les valeurs de libpng."""
    out, _ = FA.png_finalize(_png(815, 1110), 300)
    types = [t for t, _ in FA.png_chunks(out)]
    assert FA.png_srgb(out) == 0, "intention de rendu perceptuelle attendue"
    assert types.count("sRGB") == 1 and types.count("gAMA") == 1
    assert types.count("cHRM") == 1
    assert "iCCP" not in types, "iCCP et sRGB ne doivent pas coexister (spec PNG)"
    for c in ("sRGB", "gAMA", "cHRM", "pHYs"):
        assert types.index(c) < types.index("IDAT"), f"{c} doit précéder IDAT"
    # les valeurs, pas seulement la présence
    gama = dict(FA.png_chunks(out))["gAMA"]
    assert struct.unpack(">I", gama)[0] == 45455
    chrm = struct.unpack(">8I", dict(FA.png_chunks(out))["cHRM"])
    assert chrm == (31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000), \
        "les primaires sRGB de la spec, pas des nombres inventés"


def test_le_fichier_livre_dit_de_quelle_carte_il_s_agit():
    """REPROCHE : « aucune métadonnée : ni tEXt, ni iTXt, ni date, ni nom de
    carte, ni logiciel producteur. Sur un jeu de plusieurs centaines de faces,
    rien dans l'octet ne dit de quelle carte il s'agit — seul le nom de
    fichier le porte. » Un nom de fichier se perd au premier renommage."""
    textes = {"Software": FA.SOFTWARE, "Title": "Melee Celeste",
              "Description": "format poker_eu", "Source": "carte 3 - jeu deck_x"}
    out, _ = FA.png_finalize(_png(815, 1110), 300, texts=textes)
    relu = FA.png_texts(out)
    assert relu == textes, "les métadonnées doivent se relire à l'identique"
    assert "Card Forge" in relu["Software"]


def test_un_titre_hors_latin1_passe_en_iTXt_et_se_relit():
    """`tEXt` est du LATIN-1, pas de l'UTF-8 : un titre en cyrillique ou avec
    un ① sorti en tEXt serait du charabia chez le lecteur. Le chunk est choisi
    d'après les octets — et l'aller-retour doit être EXACT."""
    dur = "Mêlée Céleste ① Ω"
    out, _ = FA.png_finalize(_png(200, 200), 300, texts={"Title": dur})
    types = [t for t, _ in FA.png_chunks(out)]
    assert "iTXt" in types and "tEXt" not in types
    assert FA.png_texts(out)["Title"] == dur
    # et un titre purement latin-1 reste en tEXt (plus universel)
    out2, _ = FA.png_finalize(_png(200, 200), 300, texts={"Title": "Mêlée"})
    assert "tEXt" in [t for t, _ in FA.png_chunks(out2)]
    assert FA.png_texts(out2)["Title"] == "Mêlée"


def test_le_canal_alpha_mort_est_MESURE_avant_d_etre_retire():
    """REPROCHE : « PNG en RGBA avec un canal alpha uniformément à 255 : un
    quatrième canal inutile en impression, qui gonfle la charge utile ».

    On ne le retire jamais sur parole. On lit les extrema du canal sur les
    octets décodés, on convertit, puis on RE-DÉCODE le résultat pour vérifier
    que les trois canaux RVB sont identiques à l'octet près."""
    brut = _png_opaque(815, 1110)
    assert FA.png_alpha_extrema(brut) == (255, 255)
    # contre-epreuve : l'image transparente de `_png` n'est PAS convertible
    assert FA.png_alpha_extrema(_png(64, 64)) == (0, 255)
    out, rep = FA.png_finalize(brut, 300, drop_alpha=True)
    assert rep["alpha"]["retire"] is True
    assert rep["alpha"]["alpha_min"] == 255 and rep["alpha"]["alpha_max"] == 255
    assert rep["alpha"]["pixels"] == 815 * 1110
    assert rep["colortype"] == 2, "type 2 = RVB sans alpha"
    avant = Image.open(io.BytesIO(brut)).convert("RGB").tobytes()
    apres = Image.open(io.BytesIO(out)).convert("RGB").tobytes()
    assert avant == apres, "les pixels RVB ne doivent PAS bouger"
    assert len(out) < len(brut)


def test_un_alpha_qui_porte_de_l_information_n_est_JAMAIS_retire():
    """L'autre moitié de la règle, et la plus importante : un seul pixel
    translucide et le canal reste. Perdre de l'information pour gagner des
    octets serait le pire des échanges."""
    buf = io.BytesIO()
    im = Image.new("RGBA", (64, 64), (10, 20, 30, 255))
    im.putpixel((3, 3), (10, 20, 30, 254))
    im.save(buf, "PNG")
    out, rep = FA.png_finalize(buf.getvalue(), 300, drop_alpha=True)
    assert rep["alpha"]["retire"] is False
    assert "254" in rep["alpha"]["raison"], "le motif doit porter la mesure"
    assert rep["colortype"] == 6, "le canal alpha reste"
    assert Image.open(io.BytesIO(out)).getchannel("A").getextrema() == (254, 255)


def test_estampiller_deux_fois_ne_double_aucun_chunk():
    """Un fichier repassé par la route ne doit pas accumuler deux `sRGB`, deux
    `pHYs` ou six `tEXt` : chaque chunk d'en-tête est REMPLACÉ."""
    a, _ = FA.png_finalize(_png(400, 500), 300, texts={"Title": "un"})
    b, _ = FA.png_finalize(a, 600, texts={"Title": "deux"})
    types = [t for t, _ in FA.png_chunks(b)]
    for c in ("sRGB", "gAMA", "cHRM", "pHYs", "tEXt"):
        assert types.count(c) == 1, f"{c} en double après un deuxième passage"
    assert FA.png_phys(b) == (23622, 23622, 1), "le second pHYs fait autorité"
    assert FA.png_texts(b)["Title"] == "deux"


def test_la_route_ecrit_le_titre_la_carte_et_la_geometrie_du_format():
    """La route de bout en bout : le titre et le numéro de carte arrivent en
    paramètres, la géométrie est celle de `contract.geom` — jamais réécrite à
    la main — et le canal alpha part."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300"
                     "?title=M%C3%AAl%C3%A9e%20C%C3%A9leste&card=7",
             content=_png_opaque(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    t = FA.png_texts(r.content)
    assert t["Title"] == "Mêlée Céleste"
    # le NUMÉRO de la carte, et pas la clef interne du jeu : voir
    # test_aucun_jeton_de_rangement_ne_part_avec_le_fichier_livre
    assert t["Source"] == "carte 7"
    assert f"toile {g.canvas_px[0]} x {g.canvas_px[1]} px" in t["Description"]
    assert "299.9994 DPI ecrits dans pHYs" in t["Description"], \
        "le fichier annonce la densité QU'IL PORTE, pas celle qu'on a demandée"
    assert f"zone sure {g.safe_px[0]} x {g.safe_px[1]}" in t["Description"]
    assert FA.png_phys(r.content) == (11811, 11811, 1)
    assert FA.png_srgb(r.content) == 0
    assert r.headers["X-Cf-Colortype"] == "2"
    assert "retire" in r.headers["X-Cf-Alpha"]
    # ... et l'utilisateur peut refuser la conversion
    r2 = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300?alpha=keep",
              content=_png_opaque(*g.canvas_px),
              headers={"content-type": "image/png"})
    assert r2.status_code == 200
    assert r2.headers["X-Cf-Colortype"] == "6"
    # ... et une image REELLEMENT transparente garde son canal sans qu'on demande
    r3 = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300",
              content=_png(*g.canvas_px), headers={"content-type": "image/png"})
    assert r3.status_code == 200
    assert r3.headers["X-Cf-Colortype"] == "6"
    assert "conserve" in r3.headers["X-Cf-Alpha"]


def test_les_12_formats_et_les_3_definitions_sortent_un_fichier_juste():
    """REPROCHE : « le rapport de forme du fichier livré est juste, mais je
    n'ai pu le vérifier que sur UN format. Les 11 autres, les définitions et
    les fonds perdus ne sont prouvés par AUCUN fichier : un seul échantillon
    ne démontre pas la règle qui l'a produit. »

    Alors on produit les 36 fichiers, on relit chacun, et on confronte le
    rapport de forme de la ROGNE aux millimètres du format."""
    for fmt in sorted(CT.FORMATS):
        for dpi in (150, 300, 600):
            g = CT.geom(fmt, dpi)
            out, rep = FA.png_finalize(_png_opaque(*g.canvas_px), dpi,
                                       texts={"Title": fmt}, drop_alpha=True)
            assert FA.png_size(out) == tuple(g.canvas_px), fmt
            assert FA.png_phys(out) == (FA.dpi_to_ppm(dpi),) * 2 + (1,), fmt
            assert FA.png_srgb(out) == 0, fmt
            assert rep["colortype"] == 2, fmt
            # le rapport de forme de la rogne vaut celui des millimètres
            r_px = g.trim_px[0] / g.trim_px[1]
            r_mm = g.trim_mm[0] / g.trim_mm[1]
            assert abs(r_px - r_mm) / r_mm < 0.005, (fmt, dpi, r_px, r_mm)
            # le fond perdu est réellement dans la toile, sur les deux axes
            assert g.canvas_px[0] - g.trim_px[0] > 0
            assert abs(g.bleed_off_px[0] - g.bleed_mm / 25.4 * dpi) < 1.0


def test_la_definition_relue_est_celle_qu_on_AFFICHE_a_la_quatrieme_decimale():
    """« Le pHYs vaut 11811 px/m = 299,9994 DPI, pas 300 exactement. C'est la
    limite du format et non une faute, mais le panneau clame sa résolution
    physique sans dire que la valeur est arrondie. »

    Le panneau affiche `(phys.x * 0.0254).toFixed(4)` : il affiche donc
    299.9994, jamais 300. Le nombre vient de l'octet relu."""
    for dpi, ppm, lu in ((150, 5906, "150.0124"), (300, 11811, "299.9994"),
                         (600, 23622, "599.9988")):
        assert FA.dpi_to_ppm(dpi) == ppm
        assert f"{FA.ppm_to_dpi(ppm):.4f}" == lu
    src = js_code()
    rap = src[src.index("function pngReport("):]
    rap = rap[:rap.index("\n  }")]
    assert "(a.phys.x * 0.0254).toFixed(4)" in rap, \
        "le DPI affiché doit être calculé depuis l'octet relu, à 4 décimales"


def test_l_ecran_n_affiche_plus_une_decimale_que_le_fichier_dement():
    """AUTO-CRITIQUE DE CE TOUR, ET LA MESURE QUI L'A IMPOSÉE.

    J'ai produit le fichier par le vrai bouton (POST face/png/poker_eu/300 sur
    les octets de `CF.cardBlob`) et relu ses chunks à la main : `pHYs` =
    11811 x 11811 px/m, unité 1, soit **299,9994 DPI**. Or la jauge écrivait,
    sur une face vectorielle, « Densité mesurée … : 300.0000 DPI » — quatre
    décimales, dont la quatrième est démentie par le fichier livré. C'est le
    badge « 16 bits » posé sur des échantillons qui n'en portent que 7,64, en
    plus petit : une précision que le format ne sait pas transporter.

    `pHYs` ne stocke que des ENTIERS de pixels par mètre. 300 DPI valent
    11811,024 px/m : AUCUN PNG ne peut porter 300,0000. L'écran cesse donc de
    l'écrire et publie la valeur que le fichier portera, calculée par le même
    aller-retour entier que le serveur — mirroir de `dpi_to_ppm`/`ppm_to_dpi`,
    testé ici des deux côtés sur les trois définitions offertes."""
    src = js_code()
    # (1) le JS porte le MÊME arrondi que face.py, avec la même constante
    assert "const PHYS_METRE = 0.0254;" in src
    m = re.search(r"function dpiToPpm\(dpi\) \{(.+?)\n  \}", src, re.S)
    assert m, "le miroir JS de dpi_to_ppm est absent"
    assert "Math.floor(d / PHYS_METRE + 0.5)" in m.group(1), \
        "arrondi demi-haut, exactement comme math.floor(d / 0.0254 + 0.5)"
    assert "function ppmToDpi(ppm) { return Number(ppm) * PHYS_METRE; }" in src

    # (2) LA VALEUR EST CELLE DES OCTETS, sur les trois définitions offertes
    for dpi in (150, 300, 600):
        ppm = FA.dpi_to_ppm(dpi)
        assert ppm == int(math.floor(dpi / 0.0254 + 0.5))
        assert FA.ppm_to_dpi(ppm) != float(dpi), \
            f"{dpi} DPI est représentable exactement : le test ne mesure rien"

    # (3) le fichier RÉELLEMENT produit par la route porte ce chiffre-là
    g = CT.geom("poker_eu", 300)
    brut = _png_opaque(g.canvas_px[0], g.canvas_px[1])
    out, _ = FA.png_finalize(brut, 300)
    x, y, unit = FA.png_phys(out)
    assert (x, y, unit) == (11811, 11811, 1)
    assert f"{FA.ppm_to_dpi(x):.4f}" == "299.9994"

    # (4) et l'écran ne peut plus écrire l'autre nombre
    jauge = src[src.index("if (LAST.vector) {"):]
    jauge = jauge[:jauge.index("const ok = LAST.eff")]
    assert "rast.toFixed(4)" not in jauge, \
        "quatre décimales d'une densité que le PNG ne peut pas porter"
    assert "Math.round(rast) + ' DPI" in jauge, \
        "la jauge mesure une trame : un entier suffit, et il est vrai"
    # (5) LA VALEUR DU FICHIER EST ÉCRITE LÀ OÙ LE FICHIER SE FABRIQUE, une
    #     seule fois. La mettre AUSSI dans la jauge la faisait grandir de
    #     30 px — mesuré au rig : dans le panneau de l'app (361 px de haut),
    #     la grille du catalogue tombait de 248 à 293 px de départ. Une
    #     redondance qui coûte le livrable phare de la pièce n'en est pas une.
    phys = src[src.index("function physLine(dpi) {"):]
    phys = phys[:phys.index("\n  }")]
    for morceau in ("dpiToPpm(dpi)", "ppmToDpi(ppm).toFixed(4)", "px/m (unité mètre)",
                    "que des entiers"):
        assert morceau in phys, morceau
    assert src.count("physLine(g.dpi)") == 1, \
        "une seule fois, et sous le bouton qui produit le fichier"
    sortie = src[src.index('id="cf-face-pngout"'):]
    sortie = sortie[:sortie.index("</p>'")]
    assert "physLine(g.dpi)" in sortie, \
        "la densité du FICHIER se lit là où le fichier sort"


def test_l_export_sous_300_dpi_demande_une_confirmation_chiffree():
    """REPROCHE : « la jauge est un indicateur, pas un garde-fou : rien ne
    montre qu'un export sous le seuil serait refusé ou même averti. Un
    contrôle qui informe sans jamais s'opposer laisse passer exactement la
    faute qu'il prétend surveiller. »

    La spec veut une alerte NON BLOQUANTE : on ne refuse donc pas. Le premier
    clic ne livre rien et affiche le chiffre réel ; le second livre."""
    src = js_code()
    bloc = src[src.index("async function downloadPng("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "LAST.eff + 1e-9 < DPI_TARGET" in bloc, "le seuil est celui de la jauge"
    premier = bloc.split("ARMED = Date.now();")[1].split("ARMED = 0;")[0]
    assert "return;" in premier, "le premier clic doit SORTIR sans livrer"
    assert "CF.cardBlob" not in premier, "et ne doit RIEN encoder"
    assert "Confirmer l'export" in bloc
    assert "LAST.need" in bloc, "le message doit dire la taille qu'il faudrait"
    # aucune boîte native : elle bloquerait le fil et ne se teste pas
    assert "confirm(" not in bloc and "alert(" not in bloc


def test_le_catalogue_se_recompte_sur_les_octets_rendus():
    """REPROCHE : « 72 » et « 864 » sont affichés par le produit lui-même.
    Le panneau les RECOMPTE désormais : il redessine chaque face hors écran,
    hache les octets de `getImageData` et affiche le nombre d'empreintes
    distinctes — dont les 72 dessins peints dans la MÊME palette, ce qui est
    exactement la vérification « ce ne sont pas des recolorations »."""
    src = js_code()
    bloc = src[src.index("async function proveCatalog("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "getImageData" in js_code(), "la mesure porte sur les octets rendus"
    assert "hashPixels" in bloc and "Set()" in bloc
    assert 'const REF = "ash"' in bloc, "les 72 sont peints dans une palette unique"
    assert "hset2" in bloc, "les 864 combinaisons sont comptées à part"
    assert "best" in bloc, "la paire la plus proche : le pire cas, pas la moyenne"
    # le bouton existe et est câblé
    assert 'id="cf-face-proof"' in js_src()
    assert 'q("#cf-face-proof").addEventListener("click", proveCatalog)' in js_src()


def test_le_controle_de_fidelite_compare_la_pose_et_le_fichier_livre():
    """REPROCHE (mesuré, et vrai) : « l'illustration livrée N'EST PAS
    l'illustration importée : les noirs sont levés du double ».

    Vérification refaite par le vrai chemin : source 0,0,0 -> livré 0,0,0 ;
    255 -> 255 ; 17,13,26 -> 35,27,47 ; 128 -> 152. Ni le noir ni le blanc ne
    bougent : ce n'est ni un voile opaque ni un gain linéaire, c'est la courbe
    de `soft-light` — le réglage d'usine du grain de la pièce 06, peint à
    z=30, donc AU-DESSUS de la face (z=20). Le painter d'ici fait un
    `drawImage` nu. Le panneau MESURE et AFFICHE l'écart au lieu de se taire."""
    src = js_code()
    bloc = src[src.index("async function checkFidelity("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "paintFace(sctx" in bloc, "la face seule est rendue par NOTRE painter"
    assert "CF.renderCard(CF.current())" in bloc, "et comparée au moteur unique"
    assert "CF.Z_TABLE" in bloc, "les couches du dessus sont nommées par la table du CORE"
    assert "modalColors" in bloc, "les plages plates de la source sont retrouvées"
    # le painter de la face ne retouche RIEN : aucun filtre, aucune fusion
    pf = src[src.index("async function paintFace("):]
    pf = pf[:pf.index("\n  }")]
    assert "ctx.filter" not in pf
    assert "globalCompositeOperation" not in pf
    assert "globalAlpha" not in pf
    assert "ctx.drawImage(src.img" in pf
    # L'APLAT DE MESURE N'EST PAS UNE RETOUCHE : il ne se pose QUE sous
    # `if (MARK)`, c'est-à-dire hors du chemin qui produit le fichier livré,
    # et il est lui aussi un `fillRect` nu.
    assert pf.count("MARK") == 4, \
        ("trois sites et pas un de plus : le fond neutralisé (`&& !MARK`), la "
         "porte `if (MARK)`, et la couleur `MARK_RGB[MARK - 1]`")
    assert "mode !== \"cover\" && !MARK" in pf, \
        ("en mode marqueur le fond de la fenêtre n'est pas peint : sinon il "
         "entrerait dans le comptage de la pose")
    assert re.search(r"if \(MARK\) \{\s*ctx\.fillStyle = MARK_RGB\[MARK - 1\];"
                     r"\s*ctx\.fillRect\(", pf), \
        "l'aplat de mesure doit rester un remplissage nu"


def test_le_blason_montre_son_sujet_au_lieu_de_le_cacher():
    """MESURE FAITE PAR LE BOUTON DE PREUVE, CONTRE NOUS. Au premier passage,
    les 72 dessins peints dans la même palette donnaient bien 72/72 empreintes
    distinctes — mais la paire la plus proche, « Dragon — Blason » et
    « Archère — Blason », n'était séparée que de 0,9 niveau/canal. Vrai à la
    lettre, faux dans l'esprit : à couleur égale, un œil ne les séparait pas.

    Cause lue dans le code : le blason peignait le sujet à 0,80 (le médaillon
    le peint à 1,16), en silhouette `P.subj` quasi noire, sur un écu dont le
    dégradé finit sur `P.sky[0]`, la teinte la plus sombre de la palette.
    Correction mesurée après coup : plus aucune paire sous 5 (distance de
    luminance normalisée, 96x134), la plus proche passe de 1,70 à 6,66."""
    src = js_code()
    bloc = src[src.index("heraldry(ctx, W, H, P, R, u, fp) {"):]
    bloc = bloc[:bloc.index("\n    },")]
    echelles = [float(m) for m in re.findall(r"fp,\s*([0-9.]+)\s*\)", bloc)]
    assert echelles, "le blason doit dessiner son sujet"
    assert min(echelles) >= 1.0, \
        f"sujet rétréci dans l'écu (échelles {echelles}) : il redevient illisible"
    assert "createRadialGradient" in bloc and "P.sun" in bloc, \
        "il faut un fond CLAIR derrière le sujet, sinon la silhouette sombre " \
        "se perd dans un écu sombre"
    # le médaillon, lui, n'a jamais eu le défaut : il sert de référence
    med = src[src.index("medallion(ctx, W, H, P, R, u, fp) {"):]
    med = med[:med.index("\n    },")]
    assert max(float(m) for m in re.findall(r"fp,\s*([0-9.]+)\s*\)", med)) >= 1.0


def test_la_fenetre_dit_de_quelle_grandeur_est_le_pourcentage():
    """« 67 % de la toile » : de la surface ou du côté ? 673x897 fait 67 % de
    la SURFACE et 83 % de la largeur. Un pourcentage sans grandeur nommée est
    un chiffre qu'on ne peut pas vérifier."""
    src = js_code()
    bloc = src[src.index("function readout() {"):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "SURFACE" in bloc
    assert "w[2] * w[3] / (g.canvas_px[0] * g.canvas_px[1])" in bloc, \
        "le pourcentage doit être un rapport d'aires"
    g = CT.geom("poker_eu", 300)
    aire = g.safe_px[0] * 897 / (g.canvas_px[0] * g.canvas_px[1])
    assert round(aire * 100) == 67


def test_la_grille_du_catalogue_ne_peut_plus_s_effondrer():
    """RÉGRESSION MESURÉE PAR LA VÉRIFICATION D'INTÉGRATION : dans l'app, le
    volet du catalogue tombait à 152 px pour 211 px de contenu et
    `.cf-face-grid` à HAUTEUR 0 pour 1386 px de contenu — 72 vignettes
    présentes, invisibles et incliquables, plus 27 paires de textes qui se
    recouvraient. Cause : `min-height: 0` sur un volet qui gardait le
    `flex-shrink: 1` par défaut, dans `.cf-host` (colonne flex).

    Le garde-fou statique : le volet ne rétrécit plus, et la grille garde un
    plancher de hauteur."""
    css = CSS.read_text(encoding="utf-8")
    pane = re.search(r"\.cf-face-pane\s*\{([^}]*)\}", css)
    assert pane, "règle .cf-face-pane absente"
    corps = pane.group(1)
    assert "flex: none" in corps, "le volet doit refuser de rétrécir"
    assert "min-height: 0" not in corps, \
        "min-height:0 laisse le volet tomber à zéro dans une colonne flex"
    assert re.search(r"\.cf-face-gfill\s*\{[^}]*min-height:\s*\d+px", css), \
        "la grille pleine doit avoir un plancher en pixels"
    src = js_src()
    assert 'classList.toggle("cf-face-gfill", rows.length > 0)' in src, \
        "le plancher ne s'applique qu'à une grille QUI A des vignettes"
    # et la grille passe AVANT les explications : mesuré, elle commençait à
    # 384 px dans un hôte de 361 px — entièrement sous la ligne de flottaison.
    # (sur la source SANS commentaires : les commentaires citent les mêmes mots)
    code = js_code()
    i_grid = code.index('id="cf-face-cat-grid"')
    i_hint = code.index('<p class="hint cf-face-count">')
    assert i_grid < i_hint, "la grille doit précéder les explications"


# ═════════════ 12. LE TOUR 2 : ce que le re-duel a coûté ════════════════════

def test_la_jauge_ne_sature_plus_au_dessus_du_seuil():
    """REPROCHE, MESURÉ AU PIXEL SUR NOTRE CAPTURE : « le remplissage
    s'arrête pile sur le repère (2210..3001, repère à 3003). 324 DPI et
    900 DPI donneront la même barre pleine. Le seuil n'est lisible que dans
    le chiffre, jamais dans la position. » Une barre dont le maximum EST le
    seuil ne peut rien dire au-dessus du seuil."""
    assert FA.gauge_fill(300) == 50.0, "le seuil tombe à mi-barre"
    assert FA.gauge_fill(324) == pytest.approx(54.0)
    assert FA.gauge_fill(600) == 100.0
    assert FA.gauge_fill(900) == 100.0
    # LE défaut, retourné en test : deux définitions au-dessus du seuil ne
    # doivent PLUS donner le même remplissage.
    assert FA.gauge_fill(324) != FA.gauge_fill(450)
    assert FA.gauge_fill(240) == 40.0 and FA.gauge_fill(150) == 25.0
    assert FA.gauge_fill(0) == 0.0 and FA.gauge_fill(float("inf")) == 0.0
    assert FA.gauge_fill(1) == 2.0, "plancher : une pose désastreuse reste visible"
    # et l'écran applique la MÊME règle, repère à 50 %, échelle écrite
    src = js_code()
    bloc = src[src.index("function gaugeFill("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "2 * t" in bloc and "Math.max(2," in bloc
    g = src[src.index("const pct = gaugeFill("):]
    g = g[:g.index("wireDetails(box);")]
    assert "left:50%" in g, "le repère du seuil est au milieu de la barre"
    assert "left:100%" not in g, "un repère en bout de barre fait saturer la jauge"
    # L'ÉCHELLE RESTE ÉCRITE — dans le tiroir depuis ce tour, mais écrite :
    # sans elle « remplissage 19,6 % » est un nombre qu'on ne peut pas
    # confronter à la longueur du trait sur la capture.
    assert "échelle 0 – ' + (2 * DPI_TARGET)" in g, \
        "l'échelle de la barre doit être écrite, sinon 54 % ne se vérifie pas"


def test_la_part_visible_de_l_illustration_est_mesuree():
    """REPROCHE, MOT POUR MOT : « en Couvrir sur la toile entière, ce que le
    cadre laisse voir est un recadrage central. Rien à l'écran ne dit quelle
    fraction de l'illustration survit au masque. » Fondé : une pose peut être
    à 324 DPI ET jeter le tiers du dessin."""
    # posée exactement dans la fenêtre : rien n'est perdu
    assert FA.visible_fraction(800, 1000, 800, 1000) == 1.0
    # « contenir » : plus petite que la fenêtre, tout est visible
    assert FA.visible_fraction(800, 1000, 400, 500) == 1.0
    # « couvrir » : la source déborde d'un axe, le débord est coupé
    assert FA.visible_fraction(800, 1000, 1000, 1000) == pytest.approx(0.8)
    assert FA.visible_fraction(800, 1000, 1000, 1250) == pytest.approx(0.64)
    # décalage : la moitié sort par la gauche
    assert FA.visible_fraction(800, 1000, 800, 1000, -400, 0) == pytest.approx(0.5)
    # hors champ complet
    assert FA.visible_fraction(800, 1000, 800, 1000, -1600, 0) == 0.0
    # à rotation nulle, le résultat DOIT valoir le produit des recouvrements
    for bw, bh, dw, dh, ox in ((800, 1000, 900, 1100, 0), (600, 900, 1200, 900, 50)):
        attendu = (min(bw / 2, dw / 2 + ox) - max(-bw / 2, -dw / 2 + ox)) / dw \
            * (min(bh / 2, dh / 2) - max(-bh / 2, -dh / 2)) / dh
        assert FA.visible_fraction(bw, bh, dw, dh, ox, 0) == pytest.approx(attendu)
    # rotation : un carré tourné de 45° dans son cercle inscrit perd les coins
    v = FA.visible_fraction(1000, 1000, 1000, 1000, 0, 0, math.pi / 4)
    assert v == pytest.approx(2 * (math.sqrt(2) - 1), abs=1e-6)
    # le JS applique la même règle, et l'écran l'affiche — mais SOUS SON VRAI
    # NOM. Cette fraction est celle qui tient dans la FENÊTRE ; l'appeler
    # « visible » était le mensonge corrigé au tour 3 (voir le test
    # `test_ce_qui_atteint_le_papier_est_compte_pas_deduit`).
    src = js_code()
    assert "function visibleFraction(" in src and "clipPoly(" in src
    assert "% de la pose tient dans la fenêtre" in src
    assert "de votre illustration est visible" not in src, \
        "« visible » promettait ce que le cadre ne tient pas"
    assert "vis: visibleFraction(" in src, "la mesure est prise DANS le painter"


def test_les_deux_compositions_neuves_sont_de_vrais_dessins():
    """Une composition déclarée sans peintre retombe en silence sur `vista` :
    six étiquettes pour quatre dessins, exactement la triche que la pièce a
    déjà eu à corriger une fois. On vérifie le peintre ET son contenu."""
    assert [c for c, _ in FA.COMPOS][-2:] == ["backlight", "stained"]
    src = js_src()
    bloc = src[src.index("const COMPO_PAINT = {"):]
    for cid in ("backlight", "stained"):
        assert re.search(r"\n    " + cid + r"\(ctx, W, H, P, R, u, fp\)", bloc), cid
    bl = bloc[bloc.index("    backlight(ctx"):bloc.index("    stained(ctx")]
    st = bloc[bloc.index("    stained(ctx"):]
    st = st[:st.index("\n  };")]
    # contre-jour : un disque, un sol plat — et AUCUNE crête (c'est ce qui le
    # sépare du panorama, qui en vit)
    assert "fillRidge" not in bl and "ridgeline" not in bl
    assert "ctx.arc(dx, hz - dr * 0.25, dr" in bl, "le disque unique"
    # vitrail : un réseau de plomb et une rosace, pas d'horizon
    assert "rosace" in st and "verres" in st
    assert "fillRidge" not in st and "ridgeline" not in st
    assert len(bl) > 900 and len(st) > 900, "un peintre de 3 lignes n'est pas une composition"


def test_le_sujet_marque_de_l_editeur_a_quitte_le_catalogue():
    """Le catalogue de départ d'un logiciel n'a pas à embarquer la mascotte
    de son éditeur : la silhouette de céphalopode se reconnaissait à l'œil sur
    les vignettes et sortait avec chaque capture. Elle est remplacée par un
    dessin neutre — et les jeux enregistrés continuent d'ouvrir."""
    ids = [s for s, _ in FA.SUBJECTS]
    assert "octopus" not in ids and "sphinx" in ids
    for texte in (pathlib.Path(FA.__file__).read_text(encoding="utf-8"), js_src()):
        bas = texte.lower()
        for mot in ("poulpe", "tentacul"):
            assert mot not in bas, mot
        # `octopus` ne survit QUE dans la table de rappel et son commentaire :
        # toute ligne qui le nomme doit nommer son remplaçant dans la foulée.
        for ligne in texte.splitlines():
            if "octopus" in ligne:
                assert "sphinx" in ligne, ligne.strip()
    # le renommage est une TABLE, dans les deux sens de lecture
    assert FA.SUB_RENAMES == {"octopus": "sphinx"}
    assert FA.legacy_art_id("face_gold_depths_octopus") == "face_gold_depths_sphinx"
    assert FA.legacy_art_id("face_gold_octopus") == "face_gold_vista_sphinx"
    assert FA.legacy_art_id("face_gold_vista_sphinx") == "face_gold_vista_sphinx"
    src = js_src()
    assert re.search(r"\n    sphinx\(ctx, W, H, hz, P, R, u\)", src), \
        "le sujet neuf a son propre peintre"
    assert "SUB_RENAMES" in src, "l'écran connaît la même table de rappel"


def test_le_fichier_livre_ne_porte_plus_la_marque_de_l_editeur():
    """Le PNG livré écrivait `Software = Deepotus Card Forge - piece 01 face`
    dans un chunk tEXt : la marque de l'éditeur ET le vocabulaire interne du
    projet partaient avec chaque fichier. Le nom du logiciel producteur est
    légitime ; la marque et le jargon ne le sont pas."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300",
             content=_png_opaque(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    textes = FA.png_texts(r.content)
    assert textes["Software"] == "Card Forge"
    entier = " ".join(f"{k}={v}" for k, v in textes.items())
    for interdit in ("Deepotus", "deepotus", "piece 01", "pièce 01"):
        assert interdit not in entier, f"{interdit} sort dans les octets livrés"
    # ce qui DOIT rester : de quelle carte il s'agit, et sa géométrie
    assert "poker_eu" in textes["Description"] and "815 x 1110" in textes["Description"]


def test_le_cout_de_la_generation_est_un_montant_pas_un_compte():
    """REPROCHE, MOT POUR MOT : « la spec exige le choix du modèle exposé ET
    LE COÛT AFFICHÉ. Pas un modèle, PAS UN PRIX. » L'écran disait « 1 image
    facturée » : c'est un compte. Le montant vient maintenant de la table de
    tarifs de l'application — jamais d'un nombre écrit dans le JS."""
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/face/ai-models")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["devise"] == "USD" and d["tarif_source"]
    assert d["models"], "FAL_KEY est posée dans l'environnement de test"
    # le repli existe pour que l'écran ne dise jamais « aucun modèle » quand
    # une clé est là : la liste doit tenir même si le réglage en base tombe
    assert set(FA._keyed_providers()) >= {"fal"}
    par_id = {m["id"]: m for m in d["models"]}
    assert "flux" in par_id
    from app.services import pricing
    attendu = pricing.load()["flux_image_usd"]
    assert par_id["flux"]["usd_par_image"] == pytest.approx(attendu), \
        "le prix affiché doit être CELUI de l'application, pas une copie"
    assert par_id["flux"]["provider"] == "fal"
    # UN MODÈLE ABSENT DE LA TABLE N'AFFICHE AUCUN MONTANT — la règle n'a pas
    # changé, son illustration si : `nano-banana` était l'exemple du trou, il
    # est TABULÉ depuis la phase 5 (0,039 $, re-vérifié à la source le
    # 24/08/2026). L'écran publie donc son prix, par ÉGALITÉ à la table ; ce
    # qui reste interdit, c'est le repli silencieux sur le tarif de FLUX.
    if "nano-banana" in par_id:
        assert par_id["nano-banana"]["usd_par_image"] == \
            pytest.approx(pricing.load()["nano_banana_usd"])
        assert par_id["nano-banana"]["usd_par_image"] != \
            pytest.approx(attendu), "le prix de FLUX resservi pour un autre"
    # l'écran multiplie et totalise, et il dit d'où vient le tarif
    src = js_code()
    assert "usdFmt(n * u)" in src, "le total, pas seulement le tarif unitaire"
    assert "AI_META.tarif_source" in src, "la provenance du tarif est affichée"
    assert "Tarif non tabulé" in src
    assert 'M.api.get("ai-models")' in src
    assert "image facturée" not in src, "un compte n'est pas un coût"


def test_l_ecran_n_affiche_plus_de_jeton_de_rangement():
    """« source local:fmspgoglyz9l7i » a été lu tel quel sur une capture de
    duel. Une clef d'IndexedDB n'apprend rien à l'utilisateur et sort du
    logiciel avec l'image. Le fichier a un nom, le dessin a un titre."""
    src = js_code()
    bloc = src[src.index("function readout() {"):]
    bloc = bloc[:bloc.index("\n  }")]
    assert '" · source " + (f.src ? f.src : "aucune")' not in bloc
    assert "LAST.label" in bloc, "on affiche le nom lisible de la source"
    # et le nom lisible est posé à la source, pas reconstruit à l'affichage
    art = src[src.index("async function artSource("):]
    art = art[:art.index("\n  }")]
    assert 'label = rec.name' in art
    # la fenêtre « auto » dit ce qu'elle a résolu (le sélecteur annonçait
    # « celle du cadre » pendant que le pied de panneau mesurait la toile)
    assert "Auto → toile entière" in bloc and "Auto → fenêtre publiée" in bloc


def test_l_ecran_ne_plaide_pas_devant_son_juge():
    """Un panneau de produit documente ; il n'argumente pas contre un
    contradicteur. Les libellés qui s'adressaient à un lecteur-juge
    (« l'illustration livrée est-elle la vôtre ? », « ouvrez l'onglet Réseau
    et rechargez ») sont redevenus des noms de fonction — la MESURE, elle,
    reste, et c'est elle qui vaut preuve."""
    src = js_code()
    for plaidoirie in ("est-elle la vôtre", "ouvrez l'onglet Réseau",
                       "vraiment distincts", "Ce bouton estampille"):
        assert plaidoirie not in src, plaidoirie
    # les fonctions, elles, sont toujours là et toujours câblées
    assert 'id="cf-face-proof">Recompter le catalogue' in src
    assert r"Contrôle de fidélité de l\'illustration" in src
    assert 'performance.getEntriesByType("resource")' in src
    assert "getImageData" in src


def test_aucune_phrase_du_panneau_ne_repond_a_une_objection():
    """TOUR 2 — LA FUITE RELEVÉE PAR LE CRITIQUE CLOÎTRÉ, MOT POUR MOT.

    « TEXTE ADRESSÉ AU JUGE, SUR UN SEUL CÔTÉ, SUR LES DEUX PLANCHES. Le même
    produit affiche dans son interface des phrases qui ne parlent pas à un
    utilisateur mais à quelqu'un qui évalue : "Éprouver la jauge — importer
    une mire de 320 x 480 px" ; "Une vraie image, vraiment importée… Sous-
    définie exprès, elle fait passer la jauge au rouge" ; "Rien n'est jamais
    refusé : la taille réelle et le DPI sont affichés" ; "1296 combinaisons —
    comptées à part, parce qu'une recoloration n'est pas un dessin" ; le
    bouton "Vérifier le catalogue". C'est la voix du constructeur répondant
    d'avance à une objection, DANS le panneau. Le côté adverse ne porte aucune
    phrase de ce registre. On reconnaît le côté démontré sans lire un nom. »

    Fondé. La fuite n'est pas nominative, elle est de REGISTRE : chacune de
    ces phrases nomme l'objection à laquelle elle répond. Les fonctions
    restent, entières, mesurées ; leurs libellés redeviennent des libellés."""
    src = js_code()
    interdits = [
        "Éprouver la jauge",                       # le juge, pas l'utilisateur
        "exprès",                # y compris PEINT DANS LES PIXELS de la mire
        "d'épreuve",
        "vraiment importée",
        "Rien n'est jamais refusé",
        "parce qu'une recoloration n'est pas un dessin",
        "comptées à part",
        "aucun n'est un autre recoloré",
        "est du code, pas des fichiers",
        "sorties honnêtes",
        "signalez-le",
        "pas recopié de la demande",
        "ni résolution, ni espace de couleur, ni métadonnée",
        "aller-retour dans la géométrie du",
        "un dessin nu",
    ]
    for phrase in interdits:
        assert phrase not in src, f"registre de plaidoirie : « {phrase} »"
    # ET LES FONCTIONS SONT TOUJOURS LÀ, sous un nom d'outil.
    assert 'id="cf-face-mire">' in src and "Mire de contrôle" in src
    assert 'id="cf-face-proof">Recompter le catalogue' in src
    assert "MIRE_W" in src and "MIRE_H" in src
    assert "hashPixels" in src and "getImageData" in src
    # LA FUITE LA PLUS DIFFICILE À VOIR : elle était PEINTE DANS LES PIXELS.
    # `mireBlob` écrivait « image d'épreuve — sous-définie exprès » sur la
    # mire elle-même : la phrase se lisait donc sur la vignette de la pile ET
    # sur l'aperçu de la carte, dans toute capture d'écran. Le dessin ne porte
    # plus que ce qu'il est et sa taille.
    dessin = src[src.index("function mireBlob("):]
    dessin = dessin[:dessin.index("\n  }")]
    assert 'c.fillText("mire de contrôle"' in dessin
    assert "MIRE_W + \" x \" + MIRE_H" in dessin, "la mire écrit sa taille réelle"


def test_le_controle_de_fidelite_mesure_au_lieu_d_accuser():
    """AUTO-CRITIQUE DU TOUR 2. Le contrôle concluait « l'écart vient des
    couches du dessus, AU PREMIER RANG DESQUELLES le grain de Matières ».
    C'était une attribution, pas une mesure : ce bouton ne voit que la face
    seule et la carte entière, il ne peut isoler aucune couche. Mesure faite
    par le vrai chemin sur une carte à cadre plein : 100 % des pixels
    diffèrent, médiane 83, maximum 255 — un grain soft-light à 50 % ne fait
    pas cela, un montant de cadre opaque si. Nommer un coupable qu'on n'a pas
    pesé, c'est exactement le reproche que ce contrôle adresse aux autres."""
    src = js_code()
    bloc = src[src.index("async function checkFidelity("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "premier rang" not in bloc and "soft-light" not in bloc, \
        "aucune couche n'est désignée coupable sans avoir été pesée"
    # à la place : deux régimes séparés, et le seuil est AFFICHÉ
    assert "% teintés" in bloc and "% recouverts" in bloc and "% inchangés" in bloc
    assert "FID_TINT" in bloc, "le seuil vient d'une constante, pas d'un nombre écrit"
    assert "' niveaux — une fusion)" in bloc
    assert js_const("FID_TINT") == "32"
    assert "CF.Z_TABLE" in bloc, "les couches restent NOMMÉES par la table du CORE"
    assert "ne pèse pas ces couches une par une" in bloc, \
        "le contrôle doit dire ce qu'il ne sait pas"
    # ATTRAPÉ À L'ÉCRAN PENDANT CE TOUR : la réécriture du bloc avait perdu le
    # `hist[d]++`, et le panneau affichait « écart médian 0 » à côté de
    # « 0,0 % inchangés » — deux chiffres qui ne peuvent pas être vrais
    # ensemble. La médiane se lit dans un histogramme REMPLI, et un
    # histogramme vide ne rend plus 0 par défaut.
    assert "hist[d]++" in bloc, "la médiane doit se lire sur un histogramme rempli"
    assert "med = -1" in bloc and "Médiane indisponible" in bloc, \
        "faute de mesure, on ne publie pas un 0 qui passerait pour une mesure"


def test_le_controle_de_fidelite_donne_l_ADRESSE_du_reglage_qui_teinte():
    """REPROCHE DU TOUR 2, MOT POUR MOT : « L'illustration livrée N'EST PAS
    l'illustration importée. Sur trois plages plates de la tête, la source
    vaut (17,13,26) et le fichier rend (35,5 / 27,7 / 47,5) : les noirs sont
    levés du double. RIEN DANS L'INTERFACE N'ANNONCE CETTE RETOUCHE NI NE
    PERMET DE L'ÉTEINDRE. »

    MESURE FAITE PAR LE VRAI CHEMIN, ET ELLE DONNE RAISON AU CRITIQUE. J'ai
    déposé dans le panneau une image de plages plates EXACTES (900x1260,
    5 bandes dont (17,13,26)) par le `change` de `#cf-face-file`, puis
    déclenché le contrôle : « (17,13,26) 20,0 % de la source → 172 780 px
    après la pose, **0 px** dans la carte livrée ». La pose est donc fidèle à
    l'octet — c'est la carte qui ne l'est pas.

    La première moitié du reproche (« rien ne l'annonce ») était déjà tenue :
    le contrôle chiffre les deux régimes. La SECONDE (« ni ne permet de
    l'éteindre ») demandait une adresse — et une adresse vaut par son
    exactitude. On RELIT donc les trois réglages du voile publiés par la
    pièce 06 dans le document et on les recopie tels quels. Lecture seule,
    absence tolérée (spec 2.3) : sans la pièce 06, la phrase n'est pas
    écrite plutôt qu'inventée."""
    src = js_code()
    bloc = src[src.index("async function checkFidelity("):]
    bloc = bloc[:bloc.index("\n  }")]
    # les trois réglages sont LUS, jamais écrits
    for cle in ('CF.get("texture.over"', 'CF.get("texture.over_opacity"',
                'CF.get("texture.over_blend"'):
        assert cle in bloc, cle
    assert "CF.set(" not in bloc and "M.patch(" not in bloc, \
        "un contrôle n'écrit rien : il mesure"
    # la phrase n'est publiée que si le voile agit VRAIMENT
    assert 'ov !== "none"' in bloc and "op > 0" in bloc, \
        "un voile éteint ou à opacité nulle ne teinte rien : rien à dire"
    assert 'voile = ""' in bloc, "pièce 06 absente : aucune phrase inventée"
    assert "Math.round(op * 100)" in bloc, "l'opacité vient du document, en %"
    assert "éteint dans ce panneau-là" in bloc, "l'adresse, pas le coupable"
    # et le voile est bien un réglage de la pièce 06, pas un nom écrit ici
    tex = (ROOT / "frontend" / "cardforge" / "js" / "mod-texture.js").read_text("utf-8")
    for cle in ("over_opacity", "over_blend", 'over: "grain"'):
        assert cle in tex, f"{cle} doit être un réglage publié par la pièce 06"


def test_la_retouche_est_annoncee_SANS_qu_on_la_demande():
    """SECONDE MOITIÉ DU MÊME REPROCHE, ET C'EST ELLE QUI COÛTAIT LE DUEL.
    « RIEN DANS L'INTERFACE N'ANNONCE CETTE RETOUCHE. »

    Un bouton de contrôle ne suffit pas : il faut le chercher. La ligne est
    donc debout dans la jauge — le premier bloc du panneau — dès que le voile
    de la pièce 06 agit. Elle ne mesure rien (elle serait alors coûteuse à
    chaque frame) : elle RECOPIE les trois réglages publiés dans le document
    et nomme le panneau où les éteindre.

    LE CHIFFRE QUI A IMPOSÉ CETTE LIGNE, relu par moi dans les octets du
    fichier livré (POST face/png/poker_eu/300 sur `CF.cardBlob`, image de
    plages plates déposée par le `change` de `#cf-face-file`) :
        source (17,13,26)   ->  fichier (35,27,47)   — le chiffre du critique
        source (0,0,0)      ->  fichier (0,0,0)      — le noir ne bouge pas
    Ni voile opaque ni gain linéaire : une fusion `soft-light` à 50 %, qui est
    le réglage d'usine de Matières. La pose, elle, est fidèle à l'octet."""
    src = js_code()
    bloc = src[src.index("function finishLine() {"):]
    bloc = bloc[:bloc.index("\n  }")]
    assert 'CF.get("texture.over"' in bloc
    assert 'CF.get("texture.over_opacity"' in bloc
    assert 'CF.get("texture.over_blend"' in bloc
    assert "vos couleurs en sortent modifiées" in bloc, \
        "la conséquence doit être dite en clair, pas seulement le réglage"
    assert "Math.round(op * 100)" in bloc, "l'opacité vient du document"
    assert 'ov === "none"' in bloc and "op > 0" in bloc, \
        "un voile éteint n'a rien à annoncer"
    assert 'return ""' in bloc, "pièce 06 absente : la ligne ne s'écrit pas"
    assert "CF.set(" not in bloc and "M.patch(" not in bloc, "lecture seule"
    # ELLE EST DEBOUT DANS LES DEUX ÉTATS DE LA JAUGE (bitmap ET vectoriel) :
    # une face du catalogue subit le même voile qu'une image importée.
    assert src.count("+ cropLine() + finishLine()") == 2, \
        "la ligne doit suivre la jauge dans ses deux états"


def test_la_vignette_de_la_pile_annonce_le_MEME_dpi_que_la_jauge():
    """ATTRAPÉ À L'ÉCRAN PENDANT CE TOUR, ET C'ÉTAIT FAUX. La vignette de la
    pile calculait son DPI sur la seule LARGEUR (`dpi * w / bw`). « Couvrir »
    prend le PLUS GRAND des deux rapports : sur une source paysage dans une
    fenêtre portrait, c'est la hauteur qui commande. Mesure faite sur la
    capture : un 1600x900 posé dans 815x1110 sort à 243 DPI — la jauge le
    disait — et la vignette annonçait « ~589 DPI » à dix centimètres de là.
    Deux chiffres qui se contredisent sur le même écran, dont un faux."""
    g = CT.geom("poker_eu", 300)
    bw, bh = g.canvas_px
    dw, dh = FA.fit_rect(1600, 900, bw, bh, "cover", 1.0)
    vrai = FA.effective_dpi(1600, dw, 300)
    assert round(min(vrai, FA.effective_dpi(900, dh, 300))) == 243
    faux = 300 * 1600 / bw                      # l'ancien calcul, largeur seule
    assert round(faux) == 589, "l'ancien chiffre, pour mémoire"
    # sur une source PORTRAIT les deux coïncident : le défaut ne se voyait pas
    dw2, dh2 = FA.fit_rect(900, 1200, bw, bh, "cover", 1.0)
    assert round(min(FA.effective_dpi(900, dw2, 300),
                     FA.effective_dpi(1200, dh2, 300))) == 324
    assert round(300 * 900 / bw) == 331         # d'où l'illusion de justesse
    # et l'écran passe désormais par le MÊME calcul que le painter
    src = js_code()
    bloc = src[src.index("function fillPile() {"):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "fitRect(r.w, r.h" in bloc, "la vignette utilise l'ajustement réel"
    assert "Math.min(g.dpi * r.w" in bloc, "et la formule du DPI effectif, sur les DEUX axes"
    assert "g.dpi * r.w / Math.max(1, bw)" not in bloc, "l'ancien calcul de largeur"


def test_le_pied_de_panneau_ne_reste_pas_sur_la_mesure_precedente():
    """MESURÉ APRÈS CORRECTION, CONTRE NOUS : après un import, la jauge
    affichait « source 1600 x 900 » (la nouvelle image) pendant que le pied de
    panneau annonçait « illustration : Phénix — Médaillon » (la précédente).
    `renderPanel` dessine avant que le rendu de la carte n'ait mesuré : le
    rappel doit venir de la MESURE, pas de l'affichage."""
    src = js_code()
    bloc = src[src.index("function noteMeasure("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "paintGauge();" in bloc and "readout();" in bloc, \
        "la mesure rafraîchit la jauge ET le pied de panneau"
    assert bloc.index("if (PROBING) return;") < bloc.index("readout();"), \
        "le contrôle de fidélité ne doit rien repeindre pendant qu'il mesure"


# ═════════════ 13. LE TOUR 3 : ce que le re-duel a coûté ════════════════════

def test_l_etat_rouge_de_la_jauge_est_atteignable_en_un_clic():
    """REPROCHE, MOT POUR MOT : « La jauge de DPI est montrée DANS SON ÉTAT
    INACTIF. L'écran unique qui aurait prouvé le cœur du domaine — une image
    importée sous-définie, chiffre recalculé en direct, seuil de 300 DPI
    signalé visuellement, alerte NON BLOQUANTE qu'on peut outrepasser — est
    précisément celui que B n'a pas montré. Il plaide au lieu de démontrer. »

    On ne répond pas à cela par une phrase : on rend l'état ROUGE atteignable.
    Le bouton fabrique une vraie image de 320 x 480 px et la fait entrer par
    le chemin d'un fichier déposé. Ce test vérifie le CHIFFRE que la mire
    produit — sur les 12 formats et les 3 définitions, elle doit rougir."""
    src = js_code()
    m = re.search(r"const MIRE_W = (\d+), MIRE_H = (\d+);", src)
    assert m, "les dimensions de la mire doivent être des constantes"
    mw, mh = int(m.group(1)), int(m.group(2))
    assert (mw, mh) == (320, 480)

    # LE CHIFFRE, sur toute la table : en « couvrir » plein cadre, la mire
    # tombe sous les 300 DPI partout. Calculé par les fonctions de la pièce.
    pires = []
    for fmt in sorted(CT.FORMATS):
        for dpi in (150, 300, 600):
            g = CT.geom(fmt, dpi)
            bw, bh = g.canvas_px
            dw, dh = FA.fit_rect(mw, mh, bw, bh, "cover", 1.0)
            eff = min(FA.effective_dpi(mw, dw, dpi), FA.effective_dpi(mh, dh, dpi))
            assert FA.dpi_verdict(eff) == "low", \
                f"{fmt} @ {dpi} : la mire sort à {eff:.1f} DPI, pas rouge"
            pires.append(eff)
    # la valeur exacte du cas de référence, écrite en dur : poker_eu à 300 DPI
    g = CT.geom("poker_eu", 300)
    dw, dh = FA.fit_rect(mw, mh, g.canvas_px[0], g.canvas_px[1], "cover", 1.0)
    eff = min(FA.effective_dpi(mw, dw, 300), FA.effective_dpi(mh, dh, 300))
    assert round(eff, 1) == 117.8, "320 px de large dans 815 px de toile à 300 DPI"
    assert FA.min_source_px(dw, 300) == 815, "et l'écran dit qu'il en faudrait 815"
    assert max(pires) < FA.DPI_TARGET

    # LE CHEMIN : la mire n'est pas un cas particulier du painter, elle passe
    # par l'import réel — même pile, même rangement, même vignette.
    bloc = src[src.index("async function importMire("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "importFiles([f])" in bloc, "le MÊME chemin qu'un fichier déposé"
    assert "afterImport(added" in bloc, "la même pose et le même panneau"
    assert "canvas.toBlob" not in bloc, "(l'encodage est dans mireBlob)"
    dessin = src[src.index("function mireBlob("):]
    dessin = dessin[:dessin.index("\n  }")]
    assert 'toBlob' in dessin and '"image/png"' in dessin, \
        "de vrais octets PNG, encodés par le moteur du navigateur"
    assert "MIRE_W + \" x \" + MIRE_H" in dessin, \
        "la mire écrit sa propre taille sur elle-même"
    # et le bouton existe, câblé, dans le volet des importées
    assert 'id="cf-face-mire"' in src
    assert 'q("#cf-face-mire").addEventListener("click", importMire)' in src
    # SON LIBELLÉ EST CELUI D'UN OUTIL, plus celui d'une démonstration : voir
    # test_aucune_phrase_du_panneau_ne_repond_a_une_objection.
    assert "Mire de contrôle" in src and "Éprouver la jauge" not in src


def test_l_imprimeur_n_a_RIEN_a_deviner_sur_l_espace_de_couleur():
    """REPROCHE REFUSÉ, ET VOICI LA MESURE QUI LE REFUSE. « Aucun profil
    colorimétrique embarqué (sRGB/gAMA/cHRM seulement, pas d'iCCP). Le chunk
    sRGB est une indication ; c'est le profil qui empêche le RIP de deviner la
    conversion CMJN. »

    Un profil ICC et le chunk `sRGB` sont deux écritures du MÊME énoncé, et le
    format en veut UNE : « a file should contain at most one embedded profile,
    whether explicit like iCCP or implicit like sRGB » (PNG, iCCP). Ajouter un
    iCCP à côté du chunk sRGB ne renforce rien — il crée un fichier à deux
    déclarations, que chaque décodeur départage à sa façon.

    Ce qui se mesure, et qui décide : le fichier livré ne laisse rien à
    deviner. On le relit avec un décodeur indépendant (PIL), et l'espace est
    résolu SANS hypothèse, avec les valeurs de référence de sRGB — la
    définition numérique du profil est donc DANS le fichier."""
    dpi = 300
    g = CT.geom("poker_eu", dpi)
    out, _ = FA.png_finalize(_png_opaque(*g.canvas_px), dpi, drop_alpha=True)

    # (1) les chunks : sRGB + ses deux replis numériques, jamais les deux
    #     déclarations concurrentes
    types = [t for t, _ in FA.png_chunks(out)]
    assert "sRGB" in types and "gAMA" in types and "cHRM" in types
    assert "iCCP" not in types, "deux déclarations d'espace = une ambiguïté"

    # (2) LES VALEURS SONT CELLES DE sRGB, à l'octet
    assert FA.png_srgb(out) == 0, "intention perceptuelle"
    gama = dict(FA.png_chunks(out))["gAMA"]
    assert struct.unpack(">I", gama)[0] == 45455, "1/2,2 x 100000, la valeur sRGB"
    chrm = struct.unpack(">8I", dict(FA.png_chunks(out))["cHRM"])
    assert chrm == (31270, 32900,          # blanc D65
                    64000, 33000,          # rouge
                    30000, 60000,          # vert
                    15000, 6000), "les primaires de sRGB, telles que publiées"

    # (3) UN DÉCODEUR INDÉPENDANT LES RETROUVE — c'est la mesure qui compte :
    #     le lecteur n'a aucune hypothèse à faire.
    im = Image.open(io.BytesIO(out))
    im.load()
    assert im.info.get("srgb") == 0, "PIL lit l'intention de rendu"
    assert round(im.info.get("gamma", 0), 5) == 0.45455
    assert im.info.get("chromaticity") is not None, "et les primaires"
    assert im.mode == "RGB", "aucun canal mort à interpréter"

    # (4) et l'écran ne promet que ce que le fichier porte : il RELIT
    src = js_code()
    assert "a.srgb === null ? ' · <b>aucun espace de couleur</b>'" in src, \
        "un fichier sans espace doit être dénoncé, pas maquillé"
    assert "png_srgb" in pathlib.Path(FA.__file__).read_text(encoding="utf-8")


def test_le_releve_reseau_ne_plaide_plus_debout_sous_la_grille():
    """REPROCHE : « Mesure a l'instant : 108 vignettes peintes en 642 ms, 0
    image telechargee… C'est un banc de mesure collé dans un panneau de
    réglages. Cette prose occupe la hauteur qui manque aux commandes. »

    La MESURE reste — et elle reste prise au moment où elle est valable, de
    part et d'autre du remplissage de la grille. C'est son AFFICHAGE qui
    devient une demande : « Recompter le catalogue » l'imprime."""
    src = js_code()
    rempli = src[src.index("function fillCatalog("):]
    rempli = rempli[:rempli.index("\n  }")]
    assert "const net0 = (netEntries() || []).length;" in rempli, \
        "le compte AVANT est toujours pris"
    assert "NET_LINE = " in rempli, "et rangé, au lieu d'être peint"
    assert "m.innerHTML" not in rempli, "plus d'écriture directe sous la grille"
    preuve = src[src.index("async function proveCatalog("):]
    preuve = preuve[:preuve.index("\n  }")]
    assert 'q("#cf-face-net")' in preuve and "NET_LINE" in preuve, \
        "c'est le bouton de preuve qui l'imprime"
    # la mesure elle-même n'a pas été affaiblie
    assert 'performance.getEntriesByType("resource")' in src
    assert "image téléchargée" in src


def test_deux_textes_de_la_jauge_ne_peuvent_plus_se_recouvrir():
    """MESURÉ AU RIG, CONTRE NOUS : à 1440x900, dans le corps de la jauge,
    « redessinée » recouvrait « image importée » sur 61 x 15 px. Cause : la
    règle `.cf-face-gbody b` impose 12 px, et un `<b>` au milieu d'une phrase
    de 10,5 px gonflait sa boîte de ligne au-delà de l'interligne du `<span>`.
    Un gras dans une phrase prend la taille de la phrase."""
    css = CSS.read_text(encoding="utf-8")
    m = re.search(r"\.cf-face-gauge \.cf-face-gbody span b \{([^}]*)\}", css)
    assert m, "la règle qui ramène le gras à la taille de sa phrase est absente"
    assert "font-size: inherit" in m.group(1)
    # et l'état « vectoriel » neutre a disparu de la feuille : il n'existe plus
    assert ".cf-face-vec .cf-face-gnum" not in css
    assert "cf-face-vec" not in js_code(), \
        "plus aucune classe d'état neutre dans le module"


# ═══════ 9. LE TOUR 3 — trois nombres qui ne se prouvaient pas ══════════════

def test_le_dpi_publie_pour_la_piece_07_est_CELUI_DE_LA_JAUGE():
    """DEUX VERDICTS CONTRADICTOIRES SUR LE MÊME OCTET, RENDUS PAR LE MÊME
    MODULE. Relevé au probe sur le lab, face du catalogue, toile à 150 DPI :

        jauge de la pièce 01 = « 150 DPI · Définition insuffisante » (rouge)
        doc.face.eff_dpi     = -1
        contrôle avant vol   = aucune ligne

    `print.py:2932` fait `if declare < 0: continue`, et la convention « -1 =
    vectoriel, donc jamais sous-défini » venait de nous. Elle datait du temps
    où la jauge lisait le GENRE de la source ; depuis `rasterDpi`, la jauge
    mesure la trame livrée et dit l'inverse. Une grandeur, un nombre : on
    publie le chiffre mesuré, et P7 rougit sans qu'une ligne de P7 change.

    LA CONSÉQUENCE, RELEVÉE SUR LA VRAIE ROUTE DE P7 (POST print/preflight),
    avec le corps que la pièce 07 envoie, une seule valeur changée :
        eff_dpi = -1  -> aucune ligne « image_sous_definie »
        eff_dpi = 150 -> « err · illustration à 150 DPI effectifs une fois
                          posée (mesure de la pièce 01), il en faut 300 »
    Ce test n'exécute pas la route d'un autre module (huit builders écrivent
    en parallèle : y accrocher notre suite la rendrait rouge au rythme de
    leurs sauvegardes). Il vérifie ce que NOUS publions, et que la règle de
    lecture d'en face — celle qui rendait -1 muet — existe toujours."""
    # (1) la valeur que la pièce 01 doit publier pour une face vectorielle
    assert FA.vector_effective_dpi(150) == 150.0
    assert FA.vector_effective_dpi(150) > 0, "un DPI n'est jamais négatif"
    assert FA.dpi_verdict(FA.vector_effective_dpi(150)) == "low", \
        "la jauge dit rouge : la valeur publiée doit pouvoir le dire aussi"

    # (2) la règle d'en face, qui explique pourquoi -1 était un silence
    pr = (ROOT / "backend" / "app" / "services" / "cards" / "print.py")
    if pr.is_file():
        assert "declare < 0" in pr.read_text(encoding="utf-8"), \
            ("le contrôle avant vol ignore toute déclaration négative ; si "
             "cette règle change, notre contrat doit être relu")

    # (3) et l'écran ne peut plus publier -1
    src = js_code()
    note = src[src.index("function noteMeasure("):]
    note = note[:note.index("\n  }")]
    assert "m.vector ? -1" not in note, "la valeur conventionnelle est partie"
    assert "rasterDpi(CF.geom())" in note, "on publie la trame mesurée"
    assert re.search(r"const v = m\.has \? Math\.round\(", note), \
        "un seul arrondi, la même grandeur dans les deux branches"
    # (4) le contrat écrit en tête du fichier dit la même chose que le code
    tete = js_src()[:js_src().index('"use strict"')]
    assert "JAMAIS negatif" in tete
    assert "-1 = source vectorielle" not in tete, "l'ancien contrat a disparu"
    etat = src[src.index("eff_dpi:"):]
    assert "-1 = vectoriel" not in etat[:120]


def test_ce_qui_atteint_le_papier_est_compte_pas_deduit():
    """LE CHIFFRE ÉTAIT FAUX D'UN FACTEUR 4,4, ET DANS LE SENS FLATTEUR.

    Mesure au probe, par le VRAI champ de fichier et le VRAI moteur : image
    plate 1024x1536 en (255,0,255), fenêtre « toile entière », ajustement
    « Couvrir », poker_eu à 300 DPI. Pose 815 x 1223 px = 996 745 px.
        l'écran annonçait  « 90,8 % de votre illustration est visible »
        comptage des pixels de cette couleur dans `CF.renderCard` : 203 751,
        soit 20,4 %.
    Le calcul de `visible_fraction` est juste — mais il mesure le débord hors
    FENÊTRE, pas ce que le cadre et les textes laissent passer.

    LA MÉTHODE QUI REMPLACE L'ADJECTIF. On peint un aplat à la place de
    l'illustration, deux fois, avec deux couleurs, et on rend la carte
    ENTIÈRE par le moteur unique. Un pixel du fichier livré dépend encore de
    l'illustration si et seulement s'il CHANGE entre les deux passes. Aucun
    seuil, aucune couleur privilégiée. Ce test vérifie la méthode elle-même
    sur un composite fabriqué ici, puis vérifie que l'écran l'applique."""
    # ── (1) LA MÉTHODE, sur un cas dont on connaît la réponse ──────────────
    W, H = 40, 40

    def composite(marque):
        """L'illustration (toute la toile) + un montant OPAQUE sur la moitié
        gauche + un voile SEMI-TRANSPARENT sur la bande du haut."""
        im = Image.new("RGB", (W, H), marque)
        opaque = Image.new("RGB", (20, H), (10, 10, 10))
        im.paste(opaque, (0, 0))
        bande = im.crop((20, 0, 40, 8))
        voile = Image.blend(bande, Image.new("RGB", (20, 8), (255, 255, 0)), 0.5)
        im.paste(voile, (20, 0))
        return im.load()

    a, b, c = composite((255, 0, 255)), composite((0, 255, 0)), composite((255, 0, 255))
    vis = sum(1 for y in range(H) for x in range(W) if a[x, y] != b[x, y])
    temoin = sum(1 for y in range(H) for x in range(W) if a[x, y] != c[x, y])
    assert temoin == 0, "deux passes identiques doivent l'être au pixel"
    # la moitié droite entière : 20 x 40 = 800 px, VOILE COMPRIS. Un pixel
    # teinté dépend encore de l'illustration ; un pixel recouvert, non.
    assert vis == 800, f"attendu 800 px dépendants, mesuré {vis}"
    assert vis != W * H, "le montant opaque ne compte pas comme visible"
    assert vis > 20 * (H - 8), "le voile ne doit PAS être compté comme masque"

    # ── (2) et le module applique exactement cela ─────────────────────────
    src = js_code()
    peintre = src[src.index("async function paintFace("):]
    peintre = peintre[:peintre.index("\n  }")]
    assert "if (MARK) {" in peintre, "le marqueur passe par le painter lui-même"
    assert "MARK_RGB[MARK - 1]" in peintre
    assert "ctx.fillRect(-dw / 2, -dh / 2, dw, dh)" in peintre, \
        "l'aplat occupe EXACTEMENT la place de l'illustration"
    assert peintre.index("ctx.clip()") < peintre.index("if (MARK) {"), \
        "le marqueur doit subir le même détourage que l'illustration"

    mes = src[src.index("async function measureMask("):]
    mes = mes[:mes.index("\n  }")]
    assert mes.count("await grabCard(") == 3, \
        "trois rendus : marqueur 1, marqueur 2, et le témoin de déterminisme"
    assert "MARK = 1; C = await grabCard" in mes, "le témoin reprend le marqueur 1"
    assert "temoin++" in mes and "vis++" in mes
    assert "PROBING = true" in mes, \
        "la mesure ne doit pas réécrire la jauge qu'elle mesure"
    assert "await paintFace(sctx" in mes, \
        "le comptage de la fenêtre passe par le peintre, pas par une formule"

    ligne = src[src.index("function maskLine("):]
    ligne = ligne[:ligne.index("\n  }")]
    assert "MASK.temoin > 0" in ligne and "non mesurable" in ligne, \
        "un nombre qu'on vient de contredire ne s'affiche pas"
    assert "atteint le papier" in ligne
    # CE QUI A CHANGÉ CE TOUR : le comptage brut ne disparaît pas, il DESCEND
    # d'un cran (reproche : « le panneau déverse de la télémétrie interne dans
    # la surface du produit »). Les trois grandeurs restent obligatoires, elles
    # sont simplement cherchées dans le tiroir — voir aussi
    # test_la_telemetrie_descend_dans_un_tiroir_sans_perdre_un_chiffre.
    tiroir = src[src.index("function maskDetail("):]
    tiroir = tiroir[:tiroir.index("\n  }")]
    assert "témoin de déterminisme " in tiroir, "le lecteur voit la garantie"
    assert "px sur " in tiroir and "px de pose" in tiroir, \
        "le comptage brut est donné, pas seulement le pourcentage"
    assert "fenêtre recomptée " in tiroir, \
        "le calcul de la fenêtre est recoupé par un comptage, à l'écran"
    # la ligne mesurée est servie PARTOUT où l'ancienne l'était
    # (la branche bitmap intercale `importNote()`, qui déclare la réduction
    #  d'import — voir test_la_reduction_d_import_est_declaree_a_l_ecran)
    assert src.count("cropLine() + finishLine()") == 2
    assert "return dans + maskLine();" in src


def test_la_mesure_automatique_n_entretient_aucune_boucle_de_rendu():
    """MA PROPRE CORRECTION AVAIT CRÉÉ UNE BOUCLE, ET LE PROBE L'A PESÉE.

    Première rédaction : la mesure se relançait à chaque rendu. Relevé sur le
    lab, page au repos, aucune action de l'utilisateur :
        rendus 0-6 s : 24 · 6-12 s : 24 · 12-18 s : 24   (4 par seconde)
    Journal horodaté, et le mécanisme traverse deux pièces : mes 3 rendus font
    tourner le painter de la pièce 03, qui programme son relevé
    (mod-type.js:789) ; ce relevé rend la carte une 4e fois
    (mod-type.js:2923) ; ce 4e rendu n'est pas sous `PROBING`, donc il
    rappelle `noteMeasure`, qui reprogrammait la mesure.

    Après la signature : 0-6 s : 5 · 6-12 s : 0 · 12-18 s : 0 ; après une
    action : 9 puis 0. Et la fraîcheur croisée tient — relevé au probe en
    changeant un réglage de la PIÈCE 02 : ornement d'angle -> re-mesure OUI
    (comptage inchangé, l'ornement est hors de la fenêtre) ; métal du cadre
    -> re-mesure OUI et le comptage bouge de 267 742 à 267 740 px ; même
    valeur re-sélectionnée -> re-mesure NON."""
    src = js_code()
    sig = src[src.index("function maskSignature("):]
    sig = sig[:sig.index("\n  }")]
    # la signature porte le DOCUMENT ENTIER : c'est ce qui rend la mesure
    # sensible aux réglages des sept autres pièces sans les énumérer
    assert "JSON.stringify(CF.doc())" in sig, \
        "sans le document entier, un réglage d'une autre pièce laisse un " \
        "pourcentage périmé à l'écran"
    assert "fnv1a32(d)" in sig and "d.length" in sig
    assert "g.dpi" in sig and "CF.current()" in sig
    # la pose fait partie de l'état — AU DIXIÈME DE PIXEL, exactement comme
    # elle est publiée : un déplacement qui change le chiffre affiché doit
    # faire refaire la mesure, sinon l'écran garderait un dénominateur périmé
    # à côté d'une dimension fraîche.
    assert "px1(LAST.dw), px1(LAST.dh)" in sig, "la pose fait partie de l'état"

    sch = src[src.index("function scheduleMask("):]
    sch = sch[:sch.index("\n  }")]
    assert "if (MASK && MASK.sig === maskSignature()) return;" in sch, \
        "LE test qui tue la boucle : même état, aucune mesure de plus"
    assert "MASK_MIN_MS" in sch, "et un plafond de cadence quoi qu'il arrive"
    assert re.search(r"const MASK_MIN_MS = (\d+);", src)
    assert int(re.search(r"const MASK_MIN_MS = (\d+);", src).group(1)) >= 1000

    # la mesure elle-même reste sous PROBING de bout en bout : c'est ce qui
    # empêche ses propres rendus de la reprogrammer
    mes = src[src.index("async function measureMask("):]
    mes = mes[:mes.index("\n  }")]
    assert mes.count("PROBING = true") == 2 and mes.count("PROBING = false") == 2
    assert mes.count("finally") == 2, "remise à zéro garantie, même sur erreur"
    note = src[src.index("function noteMeasure("):]
    note = note[:note.index("\n  }")]
    assert note.index("if (PROBING) return;") < note.index("scheduleMask()"), \
        "un rendu de mesure ne doit jamais reprogrammer une mesure"


def test_la_mention_ecrite_dans_le_fichier_ne_depasse_pas_sa_propre_maille():
    """AUTO-CRITIQUE, SUR UNE MENTION GRAVÉE DANS LE FICHIER LIVRÉ. Le chunk
    tEXt Description annonçait « coupe 63 x 88 mm (744 x 1039 px) ». Décodé à
    la main, le fichier porte pHYs = 11811 px/m : 744 px y valent 62,9921 mm
    et 1039 px y valent 87,9688 mm. Le fichier démentait sa propre mention de
    31 µm — infime, mais invérifiable dans le bon sens. `pHYs` ne stocke que
    des entiers de pixels par mètre et la trame que des pixels entiers : 88,000
    n'est pas représentable. On écrit donc le nominal ET la maille."""
    # (1) la fonction, contre l'arithmétique du chunk
    assert FA.grid_mm(744, 300) == pytest.approx(744 / 11811 * 1000, abs=1e-9)
    assert FA.grid_mm(1039, 300) == pytest.approx(87.9688, abs=1e-4)
    assert FA.grid_mm(1630, 600) == pytest.approx(1630 / 23622 * 1000, abs=1e-9)
    # elle passe par dpi_to_ppm, donc par le nombre RÉELLEMENT écrit
    assert FA.grid_mm(11811, 300) == pytest.approx(1000.0, abs=1e-9)

    # (2) LE FICHIER, par la vraie route, relu dans ses octets
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300?title=T&card=1",
             content=_png_opaque(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    d = FA.png_texts(r.content)["Description"]
    ppm, ppm_y, unit = FA.png_phys(r.content)
    w, h = FA.png_size(r.content)
    # chaque nombre de la mention se refait sur les octets du fichier seul
    assert f"{ppm} px/m" in d, "la densité citée est celle du chunk"
    assert f"{FA.grid_mm(g.trim_px[0], 300):.3f} x " \
           f"{FA.grid_mm(g.trim_px[1], 300):.3f} mm" in d
    assert f"toile {w} x {h} px" in d, "la toile citée est celle de l'IHDR"
    assert f"{FA.ppm_to_dpi(ppm):.4f} DPI ecrits dans pHYs" in d
    assert "coupe nominale 63 x 88 mm" in d, "le nominal reste, nommé nominal"
    assert "63 x 88 mm (744" not in d, "l'affirmation sèche a disparu"
    # l'écart annoncé est celui qu'on recalcule, au micromètre
    for i in (0, 1):
        um = (FA.grid_mm(g.trim_px[i], 300) - g.trim_mm[i]) * 1000
        assert f"{um:+.0f}" in d, f"écart {i} absent de la mention"

    # (3) sur les 12 formats et les 3 définitions, la maille reste sous le
    #     dixième de millimètre — sinon ce ne serait plus un arrondi mais un
    #     format faux, et il faudrait le dire autrement.
    for fmt in sorted(CT.FORMATS):
        for dpi in (150, 300, 600):
            gg = CT.geom(fmt, dpi)
            for i in (0, 1):
                ecart = abs(FA.grid_mm(gg.trim_px[i], dpi) - gg.trim_mm[i])
                assert ecart < 0.1, f"{fmt} {dpi} axe {i} : {ecart:.4f} mm"


def test_le_fichier_livre_tient_les_trois_lignes_mesurables_du_cahier():
    """LA MOITIÉ MESURABLE, VÉRIFIÉE SUR LE FICHIER ET PAS SUR L'ÉCRAN :
    300 DPI réels dans les octets, fond perdu à la bonne largeur, zone sûre
    déclarée — sur les 12 formats, à 300 DPI, par la vraie route."""
    did = _deck()
    for fmt in sorted(CT.FORMATS):
        g = CT.geom(fmt, 300)
        r = _api("POST", f"/api/cards/{did}/face/png/{fmt}/300?title=T&card=1",
                 content=_png_opaque(*g.canvas_px),
                 headers={"content-type": "image/png"})
        assert r.status_code == 200, f"{fmt} : {r.text}"
        b = r.content
        # 300 DPI : dans le chunk, pas dans l'interface
        assert FA.png_phys(b) == (11811, 11811, 1), fmt
        # la trame EST la toile de la table, au pixel
        assert FA.png_size(b) == tuple(g.canvas_px), fmt
        # le fond perdu est bien la différence toile / rogne, des deux côtés
        assert g.canvas_px[0] - g.trim_px[0] == pytest.approx(2 * g.bleed_off_px[0])
        assert g.canvas_px[1] - g.trim_px[1] == pytest.approx(2 * g.bleed_off_px[1])
        # et la largeur physique du fichier vaut la rogne PLUS le fond perdu
        larg = FA.grid_mm(g.canvas_px[0], 300)
        assert larg == pytest.approx(g.trim_mm[0] + 2 * g.bleed_mm, abs=0.06), fmt
        # la zone sûre est déclarée dans les octets, avec son origine
        d = FA.png_texts(b)["Description"]
        assert f"zone sure {g.safe_px[0]} x {g.safe_px[1]} px a " \
               f"{g.safe_off_px[0]:g} / {g.safe_off_px[1]:g} px" in d, fmt
        # et l'origine de la zone sûre est bien fond perdu + retrait
        assert g.safe_off_px[0] == pytest.approx(
            g.bleed_off_px[0] + (g.trim_px[0] - g.safe_px[0]) / 2)


# ═══════ 14. L'ARRONDI QUI SE VÉRIFIE — la pose, son aire, son quotient ════

def test_l_aire_de_pose_est_le_produit_des_valeurs_AFFICHEES():
    """AUTO-CRITIQUE DE CE TOUR, ET LA MESURE QUI L'A IMPOSÉE.

    Relevé par le VRAI chemin (mire de contrôle posée par son propre bouton,
    panneau lu à l'écran dans le lab servi) :

        « source 320 x 480 px · posée 815 x 1223 px »   (en haut du bloc)
        « 267 397 px sur 996 338 px de pose »           (dix lignes plus bas)

    815 x 1223 = 996 745. L'écran publiait donc un dénominateur qui rate de
    **407 px** le produit de ses deux propres nombres. La cause : la hauteur
    de pose vaut 1222,5 px et l'aire était calculée sur la valeur exacte
    pendant que l'écran en publiait l'entier. Le pourcentage « 26,8 % » était
    JUSTE et pourtant impossible à recalculer depuis la capture — la faute du
    badge « 16 bits » démenti par ses échantillons, en plus discret.

    La règle est désormais : on publie au dixième de pixel, et l'aire est le
    PRODUIT DES VALEURS PUBLIÉES."""
    # (1) le cas exact qui a produit le défaut, refait sur les fonctions
    g = CT.geom("poker_eu", 300)
    dw, dh = FA.fit_rect(320, 480, g.canvas_px[0], g.canvas_px[1], "cover", 1.0)
    assert (round(dw, 4), round(dh, 4)) == (815.0, 1222.5)
    assert FA.pose_px(dw) == 815.0
    assert FA.pose_px(dh) == 1222.5
    # le produit des valeurs publiées, et RIEN d'autre
    assert FA.pose_area(dw, dh) == 996337.5
    assert FA.pose_area(dw, dh) == FA.pose_px(dw) * FA.pose_px(dh)
    # L'ANCIEN AFFICHAGE (entiers) RATAIT DE 407 px : le test le nomme, pour
    # qu'un retour en arrière soit visible. L'arrondi de référence est celui
    # de `Math.round` — demi-haut — et NON `round()` de Python, qui arrondit
    # au pair et rendrait 1222 là où l'écran écrivait 1223.
    def js_round(x: float) -> int:
        return int(math.floor(x + 0.5))
    assert js_round(1222.5) == 1223 and round(1222.5) == 1222, \
        "le test doit modéliser l'arrondi du navigateur, pas celui de Python"
    ancien = js_round(FA.pose_px(dw)) * js_round(FA.pose_px(dh))
    assert ancien == 996745
    assert ancien - FA.pose_area(dw, dh) == 407.5

    # (2) LA PROPRIÉTÉ GÉNÉRALE, sur les 12 formats et 3 définitions, avec des
    #     sources de rapports variés : l'aire publiée est TOUJOURS le produit
    #     des deux dimensions publiées.
    for fmt in sorted(CT.FORMATS):
        for dpi in (150, 300, 600):
            gg = CT.geom(fmt, dpi)
            for sw, sh in ((320, 480), (1024, 1536), (1600, 900), (777, 1013)):
                for mode in ("cover", "contain"):
                    a, b = FA.fit_rect(sw, sh, gg.canvas_px[0], gg.canvas_px[1],
                                       mode, 1.0)
                    # LE LECTEUR MULTIPLIE LES DEUX NOMBRES IMPRIMÉS et
                    # retrouve celui du dénominateur, au dixième — la
                    # précision à laquelle les trois sont publiés. (Le
                    # re-arrondi final n'est pas cosmétique : 384,0 x 500,6
                    # vaut 192 230,40000000002 en binaire, et un écran qui
                    # imprimerait cette queue serait illisible sans être plus
                    # vrai.)
                    exact = FA.pose_px(a) * FA.pose_px(b)
                    assert FA.pose_area(a, b) == FA.pose_px(exact), \
                        f"{fmt} {dpi} {sw}x{sh} {mode}"
                    assert abs(FA.pose_area(a, b) - exact) <= 0.05, \
                        f"{fmt} {dpi} {sw}x{sh} {mode}"
                    # et l'écart avec le produit exact reste sous le dixième
                    # de pixel par dimension : on ne change pas la grandeur,
                    # on change ce qu'on en publie
                    assert abs(FA.pose_px(a) - a) <= 0.05 + 1e-9
                    assert abs(FA.pose_px(b) - b) <= 0.05 + 1e-9


def test_le_JS_publie_la_pose_au_dixieme_et_en_derive_son_aire():
    """Le miroir à l'écran : `px1` existe, `MASK.pose` est le produit des
    valeurs publiées, et plus aucun `Math.round(LAST.d*)` ne sert à afficher
    une dimension de pose — c'est l'arrondi qui a fabriqué l'écart de 407 px.
    """
    src = js_code()
    assert "const px1 = (v) => Math.round(Number(v) * 10) / 10;" in src, \
        "l'arrondi publié (au dixième) doit exister côté écran"
    assert "const fmtPx = (v)" in src

    # l'aire vient des valeurs publiées, pas de dw * dh
    m = re.search(r"const pw1 = px1\(dw\), ph1 = px1\(dh\), poseA = "
                  r"px1\(pw1 \* ph1\);", src)
    assert m, "l'aire de pose doit être le produit des valeurs publiées"
    assert re.search(r"pose:\s*poseA", src), "MASK.pose = le produit publié"
    assert "pose: dw * dh" not in src, "le produit interne est proscrit"
    assert re.search(r"predit:\s*\(typeof LAST\.vis === \"number\" \? "
                     r"LAST\.vis \* poseA :", src), \
        "la prédiction se dérive de la MÊME aire publiée"

    # les dimensions de pose s'affichent avec fmtPx, jamais avec Math.round
    jauge = src[src.index("function paintGauge()"):]
    jauge = jauge[:jauge.index("function fixShrink()")]
    assert "Math.round(LAST.dw)" not in jauge and "Math.round(LAST.dh)" not in jauge, \
        "une dimension de pose ne s'affiche plus arrondie à l'entier"
    assert "fmtPx(LAST.dw)" in jauge and "fmtPx(LAST.dh)" in jauge

    # et la ligne de détail porte la MULTIPLICATION en clair
    det = src[src.index("function maskDetail()"):]
    det = det[:det.index("\n  }")]
    assert "fmtPx(MASK.poseW)" in det and "fmtPx(MASK.poseH)" in det
    assert "' = '" in det and "frac1(MASK.pose)" in det, \
        "l'aire doit être écrite comme le produit de ses deux facteurs"


def test_la_telemetrie_descend_dans_un_tiroir_sans_perdre_un_chiffre():
    """REPROCHE, MOT POUR MOT : « Le panneau de définition déverse de la
    télémétrie interne dans la surface du produit : "témoin de déterminisme
    0 px", "fenêtre recomptée 904 650 px contre 904 650 prédits (0,00 %)",
    "remplissage 50,0 %". La seule phrase dont l'utilisateur a besoin —
    300 DPI, c'est bon pour imprimer — est noyée dedans. »

    Fondé, et il nomme TROIS chiffres précis. Les supprimer serait la faute
    inverse : ce sont eux qui rendent le pourcentage recalculable. Les trois
    descendent donc dans un tiroir, au mot près, et le verdict reste seul en
    tête. Ce test vérifie les deux moitiés : ils sont TOUJOURS LÀ, et ils ne
    sont plus dans la ligne de verdict."""
    src = js_code()

    # (1) les trois grandeurs nommées existent encore, dans le tiroir
    det = src[src.index("function maskDetail()"):]
    det = det[:det.index("\n  }")]
    assert "témoin de déterminisme" in det
    assert "fenêtre recomptée" in det
    assert "Compté par le moteur" in det

    # (2) la ligne de verdict ne les porte plus
    verdict = src[src.index("function maskLine()"):]
    verdict = verdict[:verdict.index("function maskDetail()")]
    for mot in ("témoin de déterminisme", "fenêtre recomptée",
                "Compté par le moteur"):
        assert mot not in verdict, f"« {mot} » est resté dans le verdict"
    assert "atteint le papier" in verdict, "le verdict, lui, reste en tête"

    # (3) le remplissage de la barre a suivi le même chemin
    jauge = src[src.index("function paintGauge()"):]
    jauge = jauge[:jauge.index("function fixShrink()")]
    assert jauge.count("remplissage ") == 2, \
        "les deux branches de la jauge publient leur remplissage"
    for bloc in re.findall(r"detailsBlock\(\[(.+?)\n        \]\)", jauge, re.S) \
            + re.findall(r"detailsBlock\(\[(.+?)\n      \]\)", jauge, re.S):
        pass
    assert "Barre : échelle 0 – " in jauge
    # le mot « remplissage » n'apparaît QUE dans un detailsBlock
    for m in re.finditer(r"remplissage ", jauge):
        avant = jauge[:m.start()]
        assert avant.rfind("detailsBlock([") > avant.rfind("cropLine()"), \
            "le remplissage doit être dans le tiroir, pas dans le corps"

    # (4) le tiroir est VISIBLE (un tiroir qu'on ne devine pas = un contenu
    #     effacé) et son état survit aux repeintures
    assert 'class="cf-face-det"' in src and "<summary>" in src
    assert "let DETAIL_OPEN = false;" in src
    assert "d.open = DETAIL_OPEN;" in src
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-face-det > summary" in css
    assert 'content: "▸"' in css, "le tiroir doit s'annoncer d'un chevron"


def test_le_dpi_effectif_affiche_sa_formule_avec_LES_DEUX_rapports():
    """Le DPI effectif est le PLUS PETIT des deux rapports (largeur, hauteur).
    N'en écrire qu'un donnerait une formule qui tombe juste par hasard tant
    que les proportions sont verrouillées, et FAUSSE dès qu'on les
    déverrouille — un chiffre qu'on ne peut pas refaire est un chiffre qu'on
    ne peut pas croire."""
    src = js_code()
    jauge = src[src.index("function paintGauge()"):]
    jauge = jauge[:jauge.index("function fixShrink()")]
    assert "plus petit de ( " in jauge
    assert jauge.count("px1(LAST.dw)") >= 2 and jauge.count("px1(LAST.dh)") >= 2, \
        "les deux divisions se refont sur les valeurs PUBLIÉES"

    # LA FORMULE EST UN MINIMUM, et le minimum change de côté : sur une pose
    # aux proportions déverrouillées, c'est tantôt la largeur qui commande,
    # tantôt la hauteur. Un écran qui n'écrirait qu'un des deux rapports
    # afficherait un calcul faux une fois sur deux.
    g = CT.geom("poker_eu", 300)
    # (a) hauteur écrasée : c'est la LARGEUR qui commande
    rw = FA.effective_dpi(320, 815.0, g.dpi)
    rh = FA.effective_dpi(480, 600.0, g.dpi)
    assert round(rw, 2) != round(rh, 2), "le cas ne mesure rien s'ils sont égaux"
    assert min(rw, rh) == pytest.approx(rw) and rw < rh
    # (b) largeur écrasée : c'est la HAUTEUR qui commande — le même écran doit
    #     rendre l'autre nombre
    rw2 = FA.effective_dpi(320, 400.0, g.dpi)
    rh2 = FA.effective_dpi(480, 1222.5, g.dpi)
    assert min(rw2, rh2) == pytest.approx(rh2) and rh2 < rw2


# ══════════ TOUR DE DURCISSEMENT — CE QUE LE PANNEAU DIT, ET CE QU'IL PROUVE ══
#
# Deux règles, et elles tirent en sens inverse :
#   (a) le panneau ne récite plus le vocabulaire du contrôle qu'il subit — il
#       écrit pour quelqu'un qui fabrique une carte ;
#   (b) AUCUNE mesure ne disparaît pour autant, et aucun nombre ne reste à
#       l'écran sans que les octets le confirment.
# Les tests ci-dessous tiennent les deux bouts : un par correction.

def _chaines_visibles(code: str) -> list[str]:
    """Les littéraux de chaîne du module, commentaires déjà retirés.

    C'est l'approximation de ce qu'un lecteur voit : tout texte affiché passe
    par un de ces littéraux. On ne garde que ceux qui ressemblent à de la
    phrase (deux mots et une lettre accentuée ou un espace), pour ne pas
    trébucher sur les sélecteurs CSS et les identifiants."""
    brut = re.findall(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"", code)
    out = []
    for a, b in brut:
        s = (a or b).replace("\\'", "'").replace('\\"', '"')
        if " " in s.strip() and re.search(r"[A-Za-zÀ-ÿ]{3}", s):
            out.append(s)
    return out


def test_le_panneau_ne_recite_plus_le_vocabulaire_du_controle():
    """LA FUITE, TELLE QUE LE CONTRÔLEUR L'A RELEVÉE SUR LES DEUX PLANCHES.

    Trois énoncés de ce panneau ne renseignaient pas un utilisateur : ils
    décrivaient, dans les mots du dossier d'évaluation, la façon dont le
    contrôle se comporte — « Alerte non bloquante », « L'export reste
    possible », « Aucune taille minimale », « Image de test intégrée,
    volontairement sous-définie ». Un panneau rédigé dans ce registre se
    laisse identifier pour cette seule raison, sans qu'un nom soit écrit
    nulle part.

    La correction ne touche AUCUN chiffre : elle change la voix. Ce test
    balaie tout le texte affichable du module, pas seulement les endroits
    connus — une reformulation ailleurs ne doit pas ramener le registre."""
    visibles = _chaines_visibles(js_code())
    assert len(visibles) > 100, "l'extracteur ne voit plus le texte du panneau"
    entier = "\n".join(visibles)
    for phrase in (
        "non bloquante",             # le comportement du contrôle, pas la carte
        "export reste possible",
        "taille minimale",
        "Image de test",
        "volontairement sous-défini",
        "Rien n'est refusé",
        "n'est jamais refusé",
        "barème",
        "critère",
        "pénalité",
    ):
        assert phrase not in entier, f"registre du contrôle : « {phrase} »"

    # ET LES MESURES SONT TOUJOURS LÀ — c'est la moitié qui compte.
    for mesure in ("DPI", "atteint le papier", "% de la pose tient dans la fenêtre",
                   "px/m (unité mètre)", "empreintes distinctes"):
        assert mesure in entier, f"mesure perdue : {mesure}"


def test_la_zone_de_depot_dit_ce_qu_elle_fait_de_l_image():
    """« Aucune taille minimale : la jauge affiche la définition réelle de
    chaque image » énonçait à la négative une règle d'évaluation. Ce que
    l'utilisateur a besoin de savoir, c'est ce qui lui sera montré — la taille
    en pixels et le DPI, sous la vignette — et la seule transformation que
    l'import applique vraiment : la réduction au-delà de MAX_IMPORT_PX."""
    code = js_code()
    depot = code[code.index('id="cf-face-drop"'):]
    depot = depot[:depot.index('id="cf-face-file"')]
    assert "taille minimale" not in depot
    assert "sa taille en pixels" in depot and "DPI" in depot
    # le plafond est CITÉ depuis la constante, jamais réécrit à la main
    assert depot.count("+ MAX_IMPORT_PX +") >= 1
    assert "4096" not in depot, "le nombre du texte doit venir de la constante"
    assert js_const("MAX_IMPORT_PX") == "4096"


def test_la_mire_est_nommee_par_ce_qu_elle_est():
    """Le bouton portait un sous-titre qui annonçait sa raison d'être :
    « volontairement sous-définie : elle sert à voir ce que ce panneau affiche
    quand une illustration ne tient pas les 300 DPI ». Un outil se nomme par
    ce qu'il est. Le libellé garde SA TAILLE RÉELLE — un chiffre que la
    vignette et la jauge recomptent — et perd le mode d'emploi du contrôle."""
    code = js_code()
    bloc = code[code.index('id="cf-face-mire"'):]
    bloc = bloc[:bloc.index('id="cf-face-pile-grid"')]
    assert "Mire de contrôle" in bloc, "l'outil garde son nom de prépresse"
    assert "MIRE_W" in bloc and "MIRE_H" in bloc, "sa taille reste écrite"
    for interdit in ("Image de test", "sous-défini", "avant d'engager un tirage",
                     "ce que ce panneau affiche", "DPI_TARGET", "300"):
        assert interdit not in bloc, f"mode d'emploi du contrôle : « {interdit} »"
    # la FONCTION, elle, est intacte : le bouton est câblé au même import
    assert 'q("#cf-face-mire").addEventListener("click", importMire)' in code


def test_la_reduction_d_import_est_declaree_a_l_ecran():
    """UN CHIFFRE JUSTE, PRÉSENTÉ COMME LA MESURE D'AUTRE CHOSE.

    Au-delà de 4096 px de côté, `importFiles` REMPLACE le fichier déposé par
    une version réduite — silencieusement. La jauge écrivait ensuite
    « source 3072 × 4096 px » pour un fichier de 4500 × 6000 : le DPI calculé
    dessus était exact (c'est bien cette trame qui part à l'impression) mais
    le mot « source » désignait une image que l'utilisateur n'avait jamais
    fournie, et rien à l'écran ne le disait.

    Les DEUX tailles sont désormais gardées et montrées."""
    code = js_code()
    imp = code[code.index("async function importFiles("):]
    imp = imp[:imp.index("\n  }")]
    assert "w0: d.w, h0: d.h" in imp, "la taille du fichier déposé est retenue"
    assert "MAX_IMPORT_PX" in imp

    pile = code[code.index("function fillPile()"):]
    pile = pile[:pile.index("\n  }\n\n  function fillAI")]
    assert "r.w0" in pile and "r.h0" in pile
    assert "reduit + r.w" in pile, "la vignette porte les deux tailles"

    note = code[code.index("function importNote()"):]
    note = note[:note.index("\n  }")]
    assert "fichier déposé " in note and "MAX_IMPORT_PX" in note
    assert "r.w0 === r.w && r.h0 === r.h" in note, \
        "rien ne s'affiche quand rien n'a été réduit"

    # et la jauge la sert, dans la branche qui mesure un bitmap
    jauge = code[code.index("function paintGauge()"):code.index("function fixShrink()")]
    assert "importNote() + cropLine() + finishLine()" in jauge
    # LE CALCUL DE LA RÉDUCTION, refait ici : 4500 x 6000 -> 3072 x 4096
    k = 4096 / max(4500, 6000)
    assert (round(4500 * k), round(6000 * k)) == (3072, 4096)


def test_la_profondeur_affichee_nomme_l_octet_qui_la_porte():
    """UN BADGE « 16 bits » a déjà été démenti par les échantillons du fichier
    qu'il décrivait. Le panneau affiche une profondeur : elle doit dire d'où
    elle vient et valoir ce que les octets valent. Ici, l'octet 9 de l'IHDR —
    et on le relit sur un fichier produit par la vraie route."""
    code = js_code()
    rap = code[code.index("function pngReport("):]
    rap = rap[:rap.index("\n  }")]
    assert "bits par canal (IHDR, octet 9)" in rap
    assert "a.depth" in rap and "relu dans les octets rendus" in rap

    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300",
             content=_png_opaque(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    ihdr = [p for t, p in FA.png_chunks(r.content) if t == "IHDR"][0]
    assert ihdr[8] == 8, "le fichier livré est bien à 8 bits par canal"
    # et le lecteur JS prend le MÊME octet : IHDR + 8
    lec = code[code.index("async function readPngFacts("):]
    lec = lec[:lec.index("\n  }")]
    assert "f.depth = b[at + 8]" in lec


def test_aucune_amorce_d_invite_ne_nomme_un_lieu_de_fabrication():
    """Les métadonnées et les textes d'un livrable ne doivent porter aucune
    chaîne qui désigne celui qui l'a fabriqué. « atelier » en était une : elle
    partait dans le champ Invite, donc dans toute capture où l'amorce est
    ouverte, et dans les pièces jointes qui en dérivent. L'amorce garde sa
    scène, elle change de mot — et les deux tables restent d'accord."""
    py = pathlib.Path(FA.__file__).read_text(encoding="utf-8")
    for texte, quoi in ((py, "face.py"), (js_src(), "mod-face.js")):
        assert "atelier" not in texte.lower(), f"« atelier » subsiste dans {quoi}"
    # l'amorce existe toujours, sous son libellé, des deux côtés
    labels = [lab for lab, _ in FA.PROMPT_SEEDS]
    assert "Alchimiste" in labels
    js_labels = re.findall(r'\["([^"]+)",\s*"', js_src())
    assert "Alchimiste" in js_labels


def test_aucun_jeton_de_rangement_ne_part_avec_le_fichier_livre():
    """LA MÊME RÈGLE QUE POUR L'ÉCRAN, APPLIQUÉE AUX OCTETS — et relevée en
    regardant le panneau, pas en lisant le code.

    Le champ `Source` du PNG livré valait « carte 1 - jeu deck_088b3800 ».
    `deck_088b3800` est une clef interne : elle n'apprend rien à qui ouvre le
    fichier. Pire, le panneau RELIT les métadonnées du fichier pour les
    afficher — le jeton repartait donc dans toute capture d'écran de l'export,
    exactement le défaut que ce module s'était déjà interdit pour la pile
    (« source local:fmspgoglyz9l7i a été lu tel quel sur une capture »).

    Ce qui identifie la carte pour un humain reste : le nom du jeu dans
    `Title`, le numéro de carte dans `Source`."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300?title=Melee&card=4",
             content=_png_opaque(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    textes = FA.png_texts(r.content)
    entier = " ".join(f"{k}={v}" for k, v in textes.items())
    assert did not in entier, "la clef du jeu part encore dans les octets"
    assert "deck_" not in entier
    assert textes["Source"] == "carte 4" and textes["Title"] == "Melee"


def test_l_inventaire_des_metadonnees_du_fichier_livre_est_fige():
    """CE QUI SORT AVEC LE FICHIER, ÉNUMÉRÉ — pour que la vérification octet
    par octet avant remise ait une référence, et qu'aucun champ ne s'ajoute
    sans qu'un test le dise.

    Le seul champ qui nomme le logiciel producteur est `Software` ; les trois
    autres décrivent la carte et sa géométrie. Aucun ne porte de marque
    d'éditeur, de nom de personne, ni de vocabulaire interne."""
    did = _deck()
    g = CT.geom("poker_eu", 300)
    r = _api("POST", f"/api/cards/{did}/face/png/poker_eu/300?title=Melee&card=2",
             content=_png_opaque(*g.canvas_px),
             headers={"content-type": "image/png"})
    assert r.status_code == 200, r.text
    textes = FA.png_texts(r.content)
    assert set(textes) == {"Software", "Title", "Description", "Source"}, \
        "un champ s'est ajouté ou a disparu du fichier livré"
    assert textes["Software"] == FA.SOFTWARE == "Card Forge"
    entier = " ".join(f"{k}={v}" for k, v in textes.items())
    for interdit in ("Deepotus", "deepotus", "atelier", "piece 01", "pièce 01",
                     "gauntlet", "duel"):
        assert interdit not in entier, f"« {interdit} » sort dans les octets"
    # et RIEN d'autre que du texte : pas de date d'exécution, pas de chemin
    assert "C:\\" not in entier and "/Users/" not in entier


def test_le_cadrage_se_corrige_en_un_clic():
    """RESTE CONNU DU COMMIT DE CLÔTURE, nommé par les critiques : le cadrage
    par défaut laissait jusqu'à 70 % de l'illustration sous le cadre selon le
    gabarit — le panneau le chiffrait honnêtement, sans offrir la correction.

    Trois choses se vérifient dans la source servie :
    1. le geste existe, aux DEUX endroits : un bouton permanent dans la rangée
       d'actions, et une offre contextuelle À CÔTÉ du chiffre (data-fix), qui
       ne s'affiche pas quand la pose est déjà calée — un bouton qui ne
       changerait rien serait du décor ;
    2. la correction est un patch de pose complet (fenêtre auto, couvrir,
       centre, échelle 1) avec annulation — le patron de `fixShrink` ;
    3. le zoom molette se réfère au centre de la FENÊTRE, le même repère que
       le painter — `canvas_px / 2` n'était exact que tant que le mode auto
       retombait sur la toile entière (la fenêtre du cadre est désormais
       publiée, voir test_cards_frame)."""
    code = js_code()

    # 1. les deux offres
    assert 'id="cf-face-fitwin"' in code, "le bouton permanent manque"
    corps = code.split("function cropLine(")[1].split("\n  }")[0]
    assert 'data-fix="window"' in corps, "l'offre n'est plus à côté du chiffre"
    assert "poseCalee()" in corps, \
        "le bouton doit s'effacer quand la pose est déjà calée"

    # 2. la correction, patron fixShrink : pushUndo -> patch -> toast -> rendu
    fx = code.split("function fixWindow(")[1].split("\n  }")[0]
    assert "pushUndo()" in fx
    for cle in ('win: "auto"', 'fit: "cover"', "x: 0", "y: 0", "scale: 1"):
        assert cle in fx, f"fixWindow ne pose plus {cle}"
    assert "renderPanel()" in fx
    # ...et le clic délégué survit aux repeintures de la jauge
    assert 'closest(\'button[data-fix="window"]\')' in code

    # 3. la molette zoome au centre de la fenêtre, pas de la toile
    roue = code.split('addEventListener("wheel"')[1].split("passive")[0]
    assert "artWindow(g)" in roue, "la molette ignore la fenêtre"
    assert "canvas_px[0] / 2" not in roue, \
        "le zoom se réfère encore au centre de la toile"

    # le contrat a deux bouts : P1 lit ce que P2 publie (lecture inchangée)
    assert 'CF.get("frame.art_window"' in code


def test_la_molette_p1_coalesce_son_zoom_a_la_frame():
    """Résidu (1) de la revue 7bis (plan 2b, Task 7bis), ROUVERT : les
    molettes haute résolution et les flings de trackpad livrent PLUSIEURS
    événements wheel par frame d'affichage — chacun faisait un `M.patch`
    complet (clone + core:doc diffusé aux ~10 pièces + scheduleSave), le même
    défaut que les glissers soignés par la spec §9.6-1. Le report était
    motivé par un risque nommé : le geste est INCRÉMENTAL (chaque cran lit
    l'état courant et compose échelle ET point-sous-curseur), le coalescer
    exige un accumulateur local {scale, x, y} qui serve de base au cran
    suivant tant que la frame n'a pas écrit le document — sans lui, N crans
    tombés dans la même frame n'en zooment qu'UN (base périmée relue N fois).

    Quatre choses s'épinglent dans la source servie :
    1. plus aucun patch direct dans le gestionnaire wheel — l'écriture passe
       par l'accumulateur (`wheelPending`) vidé au rAF (`flushWheel`, défini
       hors du gestionnaire, seul endroit qui patche) ;
    2. la base de composition est l'accumulateur S'IL EXISTE (`wheelPending
       || f`) : la composition reste identique à la version un-patch-par-cran
       — le doc rendait exactement ce que le patch venait d'y poser (x/y
       arrondis au centième AVANT écriture, scale non arrondi), l'invariant
       point-sous-curseur (déjà réparé une fois) ne bouge pas ;
    3. le groupe d'annulation wheelArmed/420 ms est CONSERVÉ (une entrée par
       rafale, §9.6-4) et sa clôture pousse D'ABORD l'état FINAL exact
       (`flushWheel()` avant `wheelArmed = false`) — l'équivalent du
       pointerup des glissers (§9.6-1) ;
    4. le repère du zoom reste la fenêtre d'illustration, pas la toile (le
       test précédent le tient déjà — re-épinglé ici car la tranche est la
       même)."""
    code = js_code()
    roue = code.split('addEventListener("wheel"')[1].split("passive")[0]
    # 1. l'écriture est coalescée, plus de patch par cran
    assert "M.patch(" not in roue, \
        "le gestionnaire wheel patche encore le document à chaque cran"
    assert "wheelPending" in roue, \
        "l'accumulateur local promis par la revue 7bis manque"
    # ...et le vidage applique bien le patch, hors du gestionnaire
    flux = code.split("const flushWheel = ")[1].split("};")[0]
    assert "M.patch(" in flux, "flushWheel n'écrit pas le document"
    # 2. la base de composition consulte l'accumulateur avant le doc
    assert "wheelPending || f" in roue, \
        "N crans dans une même frame n'en composeraient qu'un (base périmée)"
    # 3. groupe d'annulation conservé, clôture = état final exact d'abord
    assert "pushUndo()" in roue and "wheelArmed" in roue, \
        "le groupage d'annulation wheelArmed/420 ms a disparu"
    assert roue.index("flushWheel()") < roue.index("wheelArmed = false"), \
        "la clôture désarme l'annulation avant d'avoir écrit l'état final"
    # 4. l'invariant sous-le-curseur ne bouge pas
    assert "artWindow(g)" in roue, "la molette ignore à nouveau la fenêtre"


# ═══ 15. LA SÉRIE — une VOIE d'images à côté du vectoriel (phase 5, T1) ══════
#
# CE QUE CETTE SECTION GARDE. La série « affiche polonaise » est 108 images
# posées À CÔTÉ des 108 dessins vectoriels, jamais à leur place : toute case
# absente retombe sur le dessin, et l'écran l'AVOUE. La machinerie qui les
# fabrique dépense de l'argent réel ; ces tests, eux, n'en dépensent pas UN
# CENTIME, et ce n'est pas une intention, c'est un compte :
#
#   * chaque test de campagne pose son ESPION sur les trois seules fonctions
#     de la pièce qui appelle un générateur (`_tirer_banana_pro`) —
#     l'espion écrit une image SYNTHÉTIQUE sur le disque local
#     et rend son nom ;
#   * la SENTINELLE (patron `test_cards_capture.py`, recopié et non importé —
#     règle 8 : deux bancs ne partagent pas un outil) referme derrière lui les
#     seize noms de `fal_client`, `FalSeedanceClient.upload_image`,
#     `image_providers.generate`, `urlopen` et `httpx.AsyncClient` : si un
#     chemin oublié atteignait quand même le fournisseur, il COMPTERAIT ;
#   * `sentinelle.zero()` clôt chaque test.
#
# LE JUGE, LUI, TOURNE POUR DE VRAI : `mesure_style.py` est du PIL pur, il ne
# sort pas de la machine et il est gratuit. Les images qu'il juge sont
# fabriquées ici, par construction : une conforme à la fiche (fond sourd, une
# masse centrale, la lumière rare) et son TÉMOIN saturé/éclairci — exactement
# la dérive d'un générateur laissé libre. Le verdict n'est donc pas une
# opinion du banc : c'est le même script que celui qui a mesuré le corpus.


def _rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _toile(w=300, h=450, graine=7, cx=0.45, cy=0.47, fw=0.69, fh=0.76,
           grain=0.35, fond=0.0):
    """Une image SYNTHÉTIQUE bâtie sur la fiche : neuf teintes maîtres, un
    fond plat rongé aux bords, UNE masse centrale texturée, un point clair
    rare, un geste rouge. Les paramètres de composition sont ce qui la fait
    passer ou non — c'est ainsi qu'on fabrique un candidat conforme et un
    candidat seulement « à retoucher », sans jamais appeler un modèle."""
    import random
    R = random.Random(graine)
    sol, noir, gris = _rgb("#4D453B"), _rgb("#1F1A18"), _rgb("#837E7C")
    clair, ocre_s = _rgb("#D2CCC7"), _rgb("#7B6B47")
    ocre_c, rouge = _rgb("#C2AC7F"), _rgb("#A32E2B")
    im = Image.new("RGB", (w, h), sol)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, int(h * 0.10)], fill=noir)
    d.rectangle([0, int(h * 0.92), w, h], fill=noir)
    d.rectangle([0, 0, int(w * 0.07), h], fill=noir)
    d.rectangle([int(w * 0.94), 0, w, h], fill=noir)
    mx, my, mw, mh = cx * w, cy * h, fw * w, fh * h
    box = [mx - mw / 2, my - mh / 2, mx + mw / 2, my + mh / 2]
    d.ellipse(box, fill=ocre_s)
    for i in range(60):
        y = box[1] + (box[3] - box[1]) * i / 60.0
        c = ocre_c if i % 3 == 0 else (gris if i % 3 == 1 else ocre_s)
        d.line([box[0] + R.random() * 8, y, box[2] - R.random() * 8, y],
               fill=c, width=2)
    d.ellipse([mx - w * 0.05, my + mh * 0.13, mx + w * 0.05, my + mh * 0.26],
              fill=rouge)
    px = im.load()
    for _ in range(int(mw * mh * grain * 2)):
        x = R.randrange(max(1, int(box[0]) + 1), min(w - 1, int(box[2]) - 1))
        y = R.randrange(max(1, int(box[1]) + 1), min(h - 1, int(box[3]) - 1))
        r, g, b = px[x, y]
        k = R.randint(-26, 26)
        px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)),
                    max(0, min(255, b + k)))
    # LE POINT CLAIR EST POSÉ APRÈS LE GRAIN : sous le grain il retombait sous
    # L=200 et « part claire » — un axe CRITIQUE — sortait de la bande par le
    # bas. Mesuré : 0,74 % pour une bande qui commence à 1,17 %.
    d.ellipse([mx - mw * 0.16, my - mh * 0.26, mx + mw * 0.16, my - mh * 0.05],
              fill=clair)
    if fond:
        for _ in range(int(w * h * fond)):
            x, y = R.randrange(1, w - 1), R.randrange(1, h - 1)
            r, g, b = px[x, y]
            k = R.randint(-14, 14)
            px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)),
                        max(0, min(255, b + k)))
    return im


def _toile_conforme():
    """TIENT — mesuré 96,9 % / dE 16,8 au juge de la fiche."""
    return _toile()


def _toile_a_retoucher():
    """A RETOUCHER — mesuré 68,8 % sans AUCUN rouge critique : la matière et
    la clé tonale tiennent, la composition non (masse trop petite, posée trop
    bas). C'est précisément le cas qu'une passe d'édition rattrape."""
    return _toile(graine=11, cx=0.45, cy=0.70, fw=0.42, fh=0.40, fond=0.20)


def _toile_saturee():
    """HORS STYLE — le témoin négatif du skill, refait ici : ×3 de saturation,
    ×1,55 de clarté, sur-netteté. Mesuré : deux axes CRITIQUES hors corpus
    (chroma p95 80,0 pour 11–59 ; part quasi-grise 4,2 % pour 18–90 %)."""
    im = ImageEnhance.Color(_toile_conforme()).enhance(3.0)
    im = ImageEnhance.Brightness(im).enhance(1.55)
    return im.filter(ImageFilter.SHARPEN)


class _Sentinelle:
    """LE COMPTEUR D'APPELS RÉELS — patron `test_cards_capture.py`, RECOPIÉ.
    Il ne simule rien : il compte, puis il lève. Le compteur survit à tous les
    `except Exception:` du chemin ; la levée seule ne survivrait pas."""

    def __init__(self):
        self.n = 0
        self.portes: list = []

    def _porte(self, nom):
        def _refus(*a, **k):
            self.n += 1
            self.portes.append(nom)
            raise AssertionError(
                f"UN APPEL PAYANT RÉEL EST PARTI D'UN TEST : {nom}")
        return _refus

    def _porte_async(self, nom):
        async def _refus(*a, **k):
            self.n += 1
            self.portes.append(nom)
            raise AssertionError(
                f"UN APPEL PAYANT RÉEL EST PARTI D'UN TEST : {nom}")
        return _refus

    def zero(self):
        assert self.n == 0, f"{self.n} appel(s) réel(s) : {self.portes}"


def _sentinelle(monkeypatch) -> _Sentinelle:
    """Les portes du dehors, refermées sur le compteur. L'espion de la route
    est ailleurs (chaque test pose le sien sur les deux `_tirer_*`) ;
    celle-ci est la CEINTURE."""
    s = _Sentinelle()
    try:
        import fal_client
    except Exception:                                    # pragma: no cover
        fal_client = None
    if fal_client is not None:
        for nom in ("subscribe_async", "submit_async", "run_async",
                    "stream_async", "upload_async", "upload_file_async",
                    "result_async", "status_async"):
            if hasattr(fal_client, nom):
                monkeypatch.setattr(fal_client, nom,
                                    s._porte_async("fal_client." + nom))
        for nom in ("subscribe", "submit", "run", "stream", "upload",
                    "upload_file", "result", "status"):
            if hasattr(fal_client, nom):
                monkeypatch.setattr(fal_client, nom,
                                    s._porte("fal_client." + nom))
    try:
        from app.services.fal_service import FalSeedanceClient
        monkeypatch.setattr(FalSeedanceClient, "upload_image",
                            staticmethod(s._porte_async(
                                "FalSeedanceClient.upload_image")))
    except Exception:                                    # pragma: no cover
        pass
    from app.services import image_providers as IP
    monkeypatch.setattr(IP, "generate",
                        s._porte_async("image_providers.generate"))
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen",
                        s._porte("urllib.request.urlopen"))
    import httpx as _hx
    monkeypatch.setattr(_hx, "AsyncClient", s._porte("httpx.AsyncClient"))
    return s


class _Atelier:
    """L'ESPION DE LA VOIE UNIQUE. Il écrit une image synthétique dans le
    magasin d'images et rend son nom — le même contrat que le vrai
    générateur, sans le fournisseur. `banana_pro` dit QUEL genre d'image
    la marche rend (un genre, ou une liste par candidat)."""

    def __init__(self, banana_pro="saturee"):
        self.banana_pro = banana_pro
        self.appels: list = []

    _GENRES = {"conforme": _toile_conforme, "retouchable": _toile_a_retoucher,
               "saturee": _toile_saturee}

    def _poser(self, genre: str) -> str:
        import uuid as _u
        nom = f"banc_{_u.uuid4().hex[:10]}.png"
        _settings.images_path.mkdir(parents=True, exist_ok=True)
        self._GENRES[genre]().save(_settings.images_path / nom)
        return nom

    def _genres(self, spec, n):
        if isinstance(spec, str):
            return [spec] * n
        return list(spec)[:n] or ["saturee"]

    async def tirer_banana_pro(self, prompt):
        self.appels.append(("nano-banana-pro", prompt, 1))
        return [self._poser(self._genres(self.banana_pro, 1)[0])]

    def pose(self, monkeypatch):
        monkeypatch.setattr(FA, "_tirer_banana_pro", self.tirer_banana_pro)
        return self


def _lancer(chemin: str, corps=None):
    """UN LANCEMENT CONFIRMÉ. La route de campagne exige `{"confirmer": true}`
    depuis l'incident de ronde (une sonde a émis 436 requêtes vers fal, toutes
    refusées à l'authentification — la clé neutralisée a tenu, zéro centime) :
    un POST NU lançait la série entière. Tous les tests qui veulent DÉPENSER
    passent donc par ici, et ceux qui veulent le DEVIS appellent la route sans
    corps, exprès."""
    return _api("POST", chemin,
                json={"confirmer": True} if corps is None else corps)


def _serie_neuve():
    """Le disque, remis à zéro : chaque test de campagne part du même état."""
    d = FA.serie_root()
    for p in list(d.glob("*.json")) + list(d.glob("*.tmp")):
        try:
            p.unlink()
        except OSError:                                  # pragma: no cover
            pass


def _py_sans_texte(chemin: pathlib.Path) -> str:
    """Le CODE d'un module Python, sans ses commentaires ni ses chaînes.

    LA VERSION AU REGEX ÉTAIT FAUSSE, ET ELLE MENTAIT DANS LE SENS RASSURANT.
    Retirer les commentaires par `#[^\\n]*` mange aussi un `#4D453B` écrit
    DANS une docstring — donc la fin de cette ligne, donc parfois le `\"\"\"`
    qui la ferme : le compte de guillemets triples devient impair, la
    passe suivante apparie n'importe quoi et avale des centaines de lignes de
    code. Mesuré ici : 126 guillemets triples avant, 125 après, et
    `_flux_generate` (présent 3 fois) tombait à ZÉRO — un contrôle
    « aucun prix écrit en dur » aurait alors été vert sur du vide.

    `tokenize` ne se trompe pas : il SAIT ce qui est une chaîne."""
    import io as _io
    import tokenize as _tk
    src = chemin.read_text(encoding="utf-8")
    out = []
    for tok in _tk.generate_tokens(_io.StringIO(src).readline):
        if tok.type in (_tk.COMMENT, _tk.STRING):
            continue
        out.append(tok.string)
    return " ".join(out)


def _prix_de_banc(monkeypatch, **surcharges):
    """La table de tarifs du banc. On ne recopie AUCUN prix dans le test : on
    part de la vraie table et on n'écrase que ce que le scénario exige."""
    from app.services import pricing
    base = dict(pricing.DEFAULTS)
    base.update(surcharges)
    monkeypatch.setattr(pricing, "load", lambda: dict(base))
    return base


# ── A. le tarif nano-banana, re-vérifié à la source ──────────────────────────

def test_le_tarif_nano_banana_est_TABULE_et_publie_par_egalite():
    """RE-VÉRIFIÉ LE 24/08/2026 sur la page du modèle
    (fal.ai/models/fal-ai/nano-banana) : « Your request will cost $0.039 per
    image. » Le chiffre entre dans la table de tarifs de l'application —
    l'écran ne le recopie pas, il le LIT.

    Sans cette ligne, `pricing.estimate` retombait EN SILENCE sur le tarif de
    FLUX (0,003) pour nano-banana : un prix 13 fois trop bas, affiché comme
    s'il était le sien. La pièce préférait donc ne rien afficher du tout
    (« tarif non tabulé »). Maintenant elle affiche, et l'égalité est
    testée."""
    from app.services import pricing
    assert pricing.DEFAULTS["nano_banana_usd"] == 0.039
    assert pricing._IMAGE_MODELS["nano-banana"][1] == "fal"
    assert pricing._IMAGE_MODELS["nano-banana"][2] == "nano_banana_usd"
    # le devis passe par la table, pour n images
    devis = pricing.estimate({"kind": "image", "model": "nano-banana", "n": 3})
    assert devis["total_usd"] == pytest.approx(3 * 0.039)
    # ET LE REPLI SILENCIEUX RESTE INTERDIT : un modèle hors table n'a pas de
    # prix, il n'hérite pas de celui de FLUX. La campagne refuse alors de
    # tirer — mieux vaut une marche sautée qu'une facture au tarif d'un autre.
    assert FA.prix_usd("modele-inconnu") is None
    assert FA.prix_usd("nano-banana", 2) == pytest.approx(2 * 0.039)
    # l'échelle de la série est la MARCHE UNIQUE nano-banana-pro depuis le
    # 27/08 au soir (« focalise toi uniquement sur nano banana pro ») — son
    # prix est tabulé (le test voisin l'épingle à la source)
    assert set(FA.serie_prix()) == set(FA.SERIE_ECHELLE) \
        == {"nano-banana-pro"}
    assert all(v is not None for v in FA.serie_prix().values())
    # ... et l'écran /ai-models le publie par ÉGALITÉ à la table
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/face/ai-models")
    assert r.status_code == 200, r.text
    par_id = {m["id"]: m for m in r.json()["models"]}
    assert "nano-banana" in par_id, sorted(par_id)
    assert par_id["nano-banana"]["usd_par_image"] == \
        pytest.approx(pricing.load()["nano_banana_usd"])


def test_les_tarifs_de_la_paire_fal_sont_TABULES_et_publies_par_egalite():
    """RE-VÉRIFIÉS LE 27/08/2026 sur les pages des modèles, jamais par un tir
    payant. fal.ai/models/fal-ai/nano-banana-pro : « Your request will cost
    $0.15 per image. For $1.00, you can run this model 7 times. » (1K/2K ; le
    4K double). fal.ai/models/openai/gpt-image-2 : table par taille × qualité,
    0,145 $ l'image en qualité `high` (le défaut, que la voie ÉPINGLE) au
    format 768×1024 — `portrait_4_3`, le cadre que la série demande.

    Le modèle OpenAI direct reste tabulé À PART (`gpt_image_2_usd`, 1024×1536
    facturé par OpenAI) : deux voies, deux factures — recycler sa clé de prix
    aurait affiché le tarif d'un autre chemin de facturation."""
    from app.services import pricing
    assert pricing.DEFAULTS.get("nano_banana_pro_usd") == 0.15
    assert pricing.DEFAULTS.get("gpt_image_2_fal_usd") == 0.145
    table = pricing._IMAGE_MODELS
    assert table.get("nano-banana-pro", ("", "", ""))[1] == "fal"
    assert table.get("nano-banana-pro", ("", "", ""))[2] == "nano_banana_pro_usd"
    assert table.get("gpt-image-2-fal", ("", "", ""))[1] == "fal"
    assert table.get("gpt-image-2-fal", ("", "", ""))[2] == "gpt_image_2_fal_usd"
    # l'entrée OpenAI directe n'a pas bougé : le reste du logiciel facture
    # gpt-image-2 chez OpenAI, la série facture la paire chez fal
    assert table["gpt-image-2"][1] == "openai"
    devis = pricing.estimate({"kind": "image", "model": "nano-banana-pro",
                              "n": 2})
    assert devis["total_usd"] == pytest.approx(2 * 0.15)
    assert devis["breakdown"][0]["provider"] == "fal"
    # les DEUX tarifs restent tabulés — gpt-image-2-fal est sorti de
    # l'ÉCHELLE (0 victoire en 15 montées, ordre du 27/08 au soir), pas de
    # la table : la façade le sert toujours, et un retour ne coûterait
    # qu'une ligne d'échelle
    assert FA.prix_usd("gpt-image-2-fal") == pytest.approx(0.145)
    assert FA.prix_usd("nano-banana-pro") == pytest.approx(0.15)


def test_la_paire_part_chez_fal_aux_endpoints_de_la_doc(monkeypatch):
    """LES IDENTIFIANTS D'ENDPOINT VIENNENT DE LA DOC fal (27/08/2026), pas
    d'un tir payant : `fal-ai/nano-banana-pro` (+ `/edit`) et
    `openai/gpt-image-2` (+ `/edit`). Les deux providers de la paire exigent
    LA CLÉ FAL — c'est fal qui facture, et le filtre de sécurité OpenAI
    direct (2 × 400 sur le sujet archer, relevé T1-L) n'est plus la porte de
    la série. La qualité `high` est ÉCRITE dans la requête : c'est elle que
    la table tarife, et un défaut fal qui changerait ne doit pas pouvoir
    changer la facture en silence."""
    from app.services import image_providers as IP
    m, args = IP.build_banana_request("p", FA.SERIE_TAILLE, 1, None,
                                      None, pro=True)
    assert m == "fal-ai/nano-banana-pro"
    assert args["aspect_ratio"] == FA.SERIE_RATIO
    assert args["num_images"] == 1 and args["output_format"] == "png"
    m2, args2 = IP.build_banana_request("p", FA.SERIE_TAILLE, 1, "http://u",
                                        FA.SERIE_RATIO, pro=True)
    assert m2 == "fal-ai/nano-banana-pro/edit"
    assert args2["image_urls"] == ["http://u"]
    # ... et SANS `pro`, les requêtes nano-banana d'hier n'ont pas bougé
    assert IP.build_banana_request("p", FA.SERIE_TAILLE, 1, None)[0] \
        == "fal-ai/nano-banana"
    m3, a3 = IP.build_fal_gpt_request("p", FA.SERIE_TAILLE, 1, None)
    assert m3 == "openai/gpt-image-2"
    assert a3["image_size"] == FA.SERIE_TAILLE and a3["quality"] == "high"
    assert a3["num_images"] == 1 and a3["output_format"] == "png"
    m4, a4 = IP.build_fal_gpt_request("p", FA.SERIE_TAILLE, 1, "http://u")
    assert m4 == "openai/gpt-image-2/edit" and a4["image_urls"] == ["http://u"]
    assert IP.PROVIDERS["nano-banana-pro"]["needs"] == "FAL_KEY"
    assert IP.PROVIDERS["gpt-image-2-fal"]["needs"] == "FAL_KEY"
    # la façade ROUTE `gpt-image-2-fal` vers fal : sans clé fal elle refuse
    # en nommant FAL_KEY — elle ne retombe pas sur la branche OpenAI (le
    # préfixe `gpt-image` est un piège d'ordre des branches, épinglé ici)
    from app.config import settings as _st
    monkeypatch.setattr(_st, "FAL_KEY", "")
    with pytest.raises(RuntimeError) as e:
        asyncio.run(IP.generate("gpt-image-2-fal", "p", FA.SERIE_TAILLE, 1))
    assert "FAL_KEY" in str(e.value)
    with pytest.raises(RuntimeError) as e2:
        asyncio.run(IP.generate("nano-banana-pro", "p", FA.SERIE_TAILLE, 1))
    assert "FAL_KEY" in str(e2.value)


# ── B. le juge et la fiche, EN DÉPÔT, datés, et frais ────────────────────────

def _sha_norme(p: pathlib.Path) -> str:
    """L'empreinte des octets AVEC LES FINS DE LIGNE NORMALISÉES. Le dépôt
    stocke en LF, `core.autocrlf` peut rendre du CRLF à la copie de travail :
    une empreinte brute rougirait selon la machine, pas selon le contenu."""
    import hashlib
    return hashlib.sha256(
        p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_le_juge_et_la_fiche_vivent_EN_DEPOT_avec_leur_provenance():
    """LE SKILL EST HORS DÉPÔT (`~/.claude/skills/`) : la campagne tournera
    sur un backend déployé, où ce dossier n'existe pas. Le juge et la fiche
    sont donc COPIÉS dans la pièce — et une copie, dans ce projet, DATE SA
    SOURCE (leçon de clôture de la phase 4).

    La déclaration ne se contente pas de dire d'où vient la copie : elle
    porte l'empreinte, et ce test la recalcule. Une retouche silencieuse du
    juge en dépôt rougit ici."""
    d = pathlib.Path(FA.__file__).parent
    juge = d / "style_walkuski.py"
    fiche = d / "style_walkuski.json"
    assert juge.is_file() and fiche.is_file()
    decl = FA.SERIE_JUGE
    assert "walkuski-style" in decl["origine"], decl
    assert decl["copie_le"] == "2026-08-25"
    assert decl["sha256"]["style_walkuski.py"] == _sha_norme(juge)
    assert decl["sha256"]["style_walkuski.json"] == _sha_norme(fiche)
    # la fiche est bien celle du corpus mesuré, pas un gabarit vide
    f = FA.fiche_style()
    assert f["n_oeuvres"] == 16 and len(f["palette_maitre"]) == 9
    assert f["metriques"]["saturation.C_lab_p50"]["med"] == pytest.approx(9.85)


def test_la_copie_du_juge_est_FRAICHE_face_au_skill():
    """LE TEST DE FRAÎCHEUR. Si le skill est là (poste de développement), les
    deux copies doivent être IDENTIQUES : le jour où la fiche est re-mesurée,
    ce test rougit et rappelle de recopier — sinon la campagne jugerait avec
    une fiche périmée sans que personne ne le voie.

    Sur une machine sans le skill (le backend déployé, l'intégration
    continue), il n'y a rien à comparer : le contrôle se SAUTE en le disant,
    il ne se déclare pas vert."""
    src = pathlib.Path.home() / ".claude" / "skills" / "walkuski-style"
    if not src.is_dir():
        pytest.skip("skill walkuski-style absent de cette machine : "
                    "la fraîcheur ne peut pas se mesurer ici")
    d = pathlib.Path(FA.__file__).parent
    paires = [(src / "scripts" / "mesure_style.py", d / "style_walkuski.py"),
              (src / "fiche_style.json", d / "style_walkuski.json")]
    for amont, aval in paires:
        assert amont.is_file(), amont.name
        assert _sha_norme(amont) == _sha_norme(aval), (
            f"{aval.name} a divergé de {amont.name} : recopiez-le et "
            f"remettez la date + l'empreinte dans FA.SERIE_JUGE")


# ── C. les cases, les familles ───────────────────────────────────────────────

def test_les_108_cases_de_serie_sont_celles_du_catalogue():
    """La série HABILLE la grille existante : elle n'invente ni sujet ni
    composition. 18 × 6 = 108 cases `<compo>_<sujet>`, en bijection avec les
    108 dessins — les noms et les thèmes sont CONSERVÉS (D1)."""
    cases = FA.serie_cases()
    assert len(cases) == 108 and len(set(cases)) == 108
    attendu = {f"{c['compo']}_{c['subject']}" for c in FA.CATALOG}
    assert set(cases) == attendu
    for c in cases:
        compo, sujet = c.split("_", 1)
        assert compo in dict(FA.COMPOS) and sujet in dict(FA.SUBJECTS)


def test_le_tirage_de_famille_tient_EXACTEMENT_les_poids_mesures():
    """« 50 % ocre, 25 % rouge, 19 % graphite, 6 % violet » est une MESURE du
    corpus (8/16, 4/16, 3/16, 1/16). Sur 108 cases, un tirage probabiliste
    l'aurait tenu « à peu près » ; la pièce le tient EXACTEMENT — 54/27/20/7 —
    parce qu'elle RANGE les cases par empreinte et coupe aux quantités, au
    lieu de lancer un dé. C'est la même exigence que `scene_of` : un équilibre
    annoncé se vérifie."""
    from collections import Counter
    n = Counter(FA.serie_famille(c) for c in FA.serie_cases())
    assert dict(n) == {"ocre": 54, "rouge": 27, "graphite": 20, "violet": 7}
    assert sum(n.values()) == 108
    assert dict(FA.FAMILLES) == {"ocre": 54, "rouge": 27, "graphite": 20,
                                 "violet": 7}


def test_le_tirage_de_famille_est_STABLE_par_case():
    """La même case retire TOUJOURS la même famille — sinon une reprise de
    campagne fabriquerait, pour la case qu'elle reprend, une image d'une
    autre famille que celle du prompt journalisé."""
    a = {c: FA.serie_famille(c) for c in FA.serie_cases()}
    b = {c: FA.serie_famille(c) for c in reversed(FA.serie_cases())}
    assert a == b
    # ... ET IL EST DISPERSÉ, PAS EN BLOCS. Couper la grille dans l'ordre du
    # catalogue tiendrait les mêmes comptes exacts (54/27/20/7) et donnerait
    # une série BANDÉE : les neuf premiers sujets tout en ocre, les quatre
    # suivants tout en rouge — chaque sujet monochrome sur ses six
    # compositions. C'est l'empreinte qui casse les blocs, et c'est mesurable :
    # les 18 sujets ET les 6 compositions portent chacun au moins deux
    # familles.
    from collections import defaultdict
    par_sujet, par_compo = defaultdict(set), defaultdict(set)
    for c in FA.serie_cases():
        compo, _, sujet = c.partition("_")
        par_sujet[sujet].add(a[c])
        par_compo[compo].add(a[c])
    assert min(len(v) for v in par_sujet.values()) >= 2, \
        "un sujet entier tombe dans une seule famille : le tirage est bandé"
    assert min(len(v) for v in par_compo.values()) >= 2
    # ... et la valeur ne dépend d'aucun état de module : elle se recalcule
    # à froid dans un interpréteur neuf.
    import subprocess
    code = ("import sys; sys.path.insert(0, r'%s');"
            "from app.services.cards import face as F;"
            "print(F.serie_famille('vista_tower'), F.serie_famille('stained_beacon'))"
            % str(ROOT / "backend"))
    env = dict(os.environ)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, env=env, timeout=180)
    assert out.returncode == 0, out.stderr[-800:]
    assert out.stdout.split() == [FA.serie_famille("vista_tower"),
                                  FA.serie_famille("stained_beacon")]


# ── D. le prompt : ancré sur la fiche, jamais sur un nom ─────────────────────

def test_le_prompt_se_construit_SUR_LA_FICHE_et_ne_recopie_pas_ses_chiffres(
        monkeypatch):
    """LE PIN DE D6. Les fractions du prompt (masse, vide, part sombre, part
    claire) et ses hexadécimaux VIENNENT de `style_walkuski.json`. Une fiche
    re-mesurée doit changer le prompt toute seule — sinon la « fiche » n'est
    qu'une décoration et les vrais chiffres sont dans le code."""
    vrai = FA.serie_prompt("vista_tower")
    assert "69%" in vrai and "76%" in vrai and "43%" in vrai
    f = FA.fiche_style()
    faux = json.loads(json.dumps(f))
    faux["metriques"]["composition.masse_bbox.largeur"]["med"] = 0.31
    faux["metriques"]["composition.part_vide_E_moins_4"]["med"] = 0.58
    monkeypatch.setattr(FA, "fiche_style", lambda: faux)
    autre = FA.serie_prompt("vista_tower")
    assert "31%" in autre and "58%" in autre
    assert "69%" not in autre, "la largeur de masse était écrite en dur"


def test_le_prompt_porte_les_six_blocs_et_le_cadre_portrait():
    """La structure du gabarit : matière, sujet, composition, palette, clé
    tonale, interdits — dans cet ordre. Et le cadre est un PORTRAIT annoncé,
    parce que le corpus l'est (0,695 médian sur ses 11 affiches portrait)."""
    p = FA.serie_prompt("medallion_dragon")
    # Le marqueur du bloc CLÉ ne peut pas être son premier mot : « Dark-keyed »
    # a dû partir (T5bis — le générateur le lisait comme « éteins tout »). On
    # épingle ce que le bloc FAIT — citer le seuil clair du juge — et non la
    # tournure du jour.
    cle = "%d%% lightness" % int(round(FA._juge_module().SEUIL_CLAIR / 255.0 * 100))
    for morceau in ("craquelure", "portrait", "Palette strictly limited",
                    cle, "Not photographic"):
        assert morceau in p, morceau
    assert p.index("craquelure") < p.index("Palette strictly limited") \
        < p.index(cle) < p.index("Not photographic")
    # le sujet et la composition sont ceux de la case, pas un texte générique
    assert "dragon" in p.lower()
    assert FA.serie_prompt("medallion_dragon") != FA.serie_prompt("vista_dragon")
    assert FA.serie_prompt("medallion_dragon") != FA.serie_prompt("medallion_wolf")


def test_le_prompt_pousse_du_COTE_QUE_LA_CAMPAGNE_A_MESURE():
    """LE SENS DU GABARIT, ÉPINGLÉ — et il est l'INVERSE de l'intuition.

    Sur les 84 candidats payés de T5, mesurés au juge, le générateur sortait
    de la bande TOUJOURS du même côté, et jamais celui qu'on croyait :

        masse (surface) 0,194 pour [0,415 ; 0,651] -> 83/84 SOUS le plancher
        part de vide    0,744 pour [0,320 ; 0,546] -> 84/84 AU-DESSUS
        L médian        41,9  pour [63,3 ; 126,7]  -> 62/84 SOUS
        part claire     0,002 pour [0,012 ; 0,132] -> 46/84 SOUS

    Il ne remplissait pas la toile : il la VIDAIT, et il l'éteignait. Le
    gabarit doit donc POUSSER — forme qui écrase le cadre, point clair
    EXIGÉ — et sa liste négative doit refuser les DEUX bords, pas seulement
    l'excès. Sans ce contrôle, une reformulation qui « allège » le prompt
    ramènerait le défaut sans qu'un test rougisse, et il se paierait une
    seconde fois en candidats."""
    p = FA.serie_prompt("medallion_dragon")
    bas = p.lower()
    # 1. la masse est un PLANCHER, pas une indication
    assert "at least" in bas, "la masse doit être un plancher (mesuré 83/84 sous)"
    assert "dominates the frame" in bas
    # 2. LE POINT CLAIR : PRÉSENT **ET** BORNÉ — les deux moitiés, parce que
    #    chacune sans l'autre a produit un défaut MESURÉ sur 84 candidats
    #    payés, pour une bande [0,012 ; 0,132] :
    #      - gabarit d'origine (« only 4% above »)        -> 0,002, absent
    #      - premier correctif (« never absent nor dimmed ») -> 0,230, envahissant
    #    Le pendule a traversé la bande de part en part. Un seul des deux
    #    contrôles ci-dessous, et il la retraverse au réglage suivant.
    assert "highlight" in bas
    assert "one small bone-white highlight" in bas, "le point clair doit être PETIT"
    assert "no more than that" in bas, "et BORNÉ, sinon il envahit la toile"
    assert "never dimmed" not in bas, "la tournure qui a produit 0,230 est revenue"
    # 3. ... et l'ombre profonde garde un PLANCHER. « no more than that » s'y
    #    appliquait au premier correctif : la part sombre est tombée à 0,072
    #    pour un plancher de 0,059, la toile a viré au blanc (L médian 192,2
    #    pour un plafond de bande à 126,7).
    assert "at least %d%% of the canvas is genuine deep shadow" \
        % FA._pc(FA._med("tons.part_sombre_L_moins_64")) in bas
    # 4. LE MOT « DARK » DANS LA CLÉ — et ce contrôle-ci a été payé.
    #    T5ter l'a retiré (« Mid-dark key » -> « Mid key, held at the
    #    middle ») en croyant qu'il suffisait de BORNER le point clair. La
    #    mesure a dit le contraire, sur 84 candidats de plus :
    #      part claire  0,230 -> 0,485   (plafond de bande 0,132)
    #      L médian     192,2 -> 199,1   (plafond de bande 126,7)
    #    Borner l'excès NE SUFFIT PAS quand on vient de retirer le seul mot
    #    qui tirait vers le bas. La borne et la pression vont ensemble.
    assert "mid-dark key" in bas, "la clé a reperdu son mot « dark »"
    assert "the painting is dark overall" in bas
    # 3. le fond est de la matière, pas un vide (mesuré 84/84 au-dessus)
    assert "painted ground" in bas
    assert "no detail at all" not in bas, \
        "la tournure qui a produit 74 % de vide est revenue"
    # 4. la liste négative refuse AUSSI le bord où le générateur tombe
    for refus in ("no vast empty background", "not a small subject lost",
                  "no crushed blacks"):
        assert refus in bas, refus
    # 5. et rien de tout cela n'a introduit de nombre écrit à la main : les
    #    fractions restent celles de la fiche
    for cle, _lbl in (("composition.masse_bbox.largeur", ""),
                      ("composition.masse_bbox.hauteur", ""),
                      ("composition.part_vide_E_moins_4", ""),
                      ("tons.part_sombre_L_moins_64", "")):
        assert "%d%%" % FA._pc(FA._med(cle)) in p, cle
    # 6. le vocabulaire du vide ne revient par AUCUNE porte — les six scènes
    #    de composition le disaient aussi, et elles annulaient le bloc COMPO
    #    juste au-dessus d'elles (« flat and empty », « bare unmodulated »)
    for compo, scene in FA.COMPOS_SCENE.items():
        for mot in ("unmodulated", "flat and empty", "a flat ground"):
            assert mot not in scene.lower(), (compo, mot)
    # 7. la garde du nom d'artiste tient sur les 108 cases après réécriture,
    #    et les 108 prompts portent bien la poussée (aucune case oubliée)
    for case in FA.serie_cases():
        p108 = FA.sans_nom_d_artiste(FA.serie_prompt(case))
        assert "AT LEAST" in p108, case
        assert "ONE SMALL bone-white highlight" in p108, case
        assert "Mid-dark key" in p108, case


def test_le_cadre_demande_est_le_PLUS_PROCHE_du_2_3_de_la_fiche():
    """L'AVEU DU CADRE, MESURÉ. La fiche vise le 2:3 (0,667) ; le service de
    génération de l'application ne connaît que six cadres NOMMÉS. On ne peut
    donc pas demander le cadre de la fiche — on demande le plus proche, et on
    le PROUVE plutôt que de l'affirmer : `portrait_4_3` (0,750) est à 0,083 du
    2:3, `portrait_16_9` (0,562) à 0,104.

    Les ratios ne sont pas recopiés ici : ils se lisent dans la table de
    l'application (`image_providers._BANANA_ASPECT`), et le rapport d'édition
    de la pièce doit être CELUI de ce cadre — sinon une passe de retouche
    changerait la forme de l'image entre deux marches de l'échelle."""
    from app.services.image_providers import _BANANA_ASPECT
    cible = 2.0 / 3.0
    ratios = {}
    for nom, asp in _BANANA_ASPECT.items():
        a, b = (float(x) for x in asp.split(":"))
        ratios[nom] = a / b
    plus_proche = min(ratios, key=lambda k: abs(ratios[k] - cible))
    assert FA.SERIE_TAILLE == plus_proche, (FA.SERIE_TAILLE, ratios)
    assert FA.SERIE_RATIO == _BANANA_ASPECT[FA.SERIE_TAILLE], \
        "le cadre de l'édition ne suit pas celui de la génération"
    assert abs(ratios[FA.SERIE_TAILLE] - cible) == pytest.approx(0.0833, abs=1e-3)
    # LE SECOND MIROIR, re-mesuré au rebranchement fal (27/08) : la marche
    # GPT ne passe plus par la table de TAILLES OpenAI (qui rendait un 2:3
    # exact en 1024×1536) — elle passe par les presets fal et transmet LE
    # MÊME nom de cadre que la première marche. L'échelle entière livre donc
    # UN seul cadre (0,750, à 0,083 du 2:3 de la fiche) : l'uniformité est
    # gagnée, le bonus 2:3 de la voie OpenAI directe est perdu — ÉPINGLÉ ici
    # pour que personne ne le redécouvre sur une image livrée.
    from app.services.image_providers import build_fal_gpt_request
    _, a_gpt = build_fal_gpt_request("p", FA.SERIE_TAILLE, 1, None)
    assert a_gpt["image_size"] == FA.SERIE_TAILLE
    assert "2:3" in pathlib.Path(FA.__file__).read_text(encoding="utf-8"), \
        "le cadre visé n'est nommé nulle part dans la pièce"


def test_le_cadre_est_LE_MEILLEUR_pas_un_pis_aller():
    """L'AVEU, REFAIT PAR LA MESURE (correction de ronde). La première
    rédaction disait « la face de carte du Cardforge (650×1024 = 0,635) » :
    ce nombre est la taille sous laquelle la BARRE refuse un import, il n'est
    le rapport d'AUCUN des 12 formats. Les vrais rapports sont ceux de
    `contract.geom`, et ils décident du sens de l'écart.

    Posée en « couvrir » sur la toile du poker (0,7342), une image 2:3 EXACTE
    perd 9,2 % de sa HAUTEUR — là où vit la composition (la masse occupe 76 %
    de la hauteur, le poids est bas-centre). Le 3:4 demandé, lui, ne perd que
    2,1 % de sa LARGEUR et RIEN de sa hauteur. Le cadre choisi n'est donc pas
    le moins mauvais : c'est le meilleur des deux pour ce que la fiche
    mesure."""
    g = CT.geom("poker_eu", 300)
    toile = g.canvas_px[0] / g.canvas_px[1]
    coupe = g.trim_px[0] / g.trim_px[1]
    assert toile == pytest.approx(0.7342, abs=1e-3)
    assert coupe == pytest.approx(0.7159, abs=1e-3)
    # 0,635 EST LE RAPPORT DE 650x1024 — la taille sous laquelle la BARRE
    # refuse un import (`BAR_REFUSAL_PX`), pas un format d'ici : aucun des 12
    # ne porte cette trame, et aucun n'a ce rapport. (Le plus proche est
    # bridge_us à 0,6429, à huit millièmes — assez pour qu'un aveu qui cite
    # 0,635 comme « la face de carte du Cardforge » soit faux.)
    assert FA.BAR_REFUSAL_PX == (650, 1024)
    assert 650 / 1024 == pytest.approx(0.635, abs=1e-3)
    tous = {f: CT.geom(f, 300).trim_px[0] / CT.geom(f, 300).trim_px[1]
            for f in CT.FORMATS}
    assert not [f for f, r in tous.items() if abs(r - 0.635) < 1e-3], tous
    for f in CT.FORMATS:
        g2 = CT.geom(f, 300)
        assert tuple(g2.trim_px) != (650, 1024)
        assert tuple(g2.canvas_px) != (650, 1024)
    perte_2_3 = 1.0 - (2.0 / 3.0) / toile            # hauteur rognée
    perte_3_4 = 1.0 - toile / 0.75                   # largeur rognée
    assert perte_2_3 == pytest.approx(0.092, abs=2e-3)
    assert perte_3_4 == pytest.approx(0.021, abs=2e-3)
    assert perte_3_4 < perte_2_3
    py = pathlib.Path(FA.__file__).read_text(encoding="utf-8")
    # LE NOMBRE PEUT RESTER — la correction se garde, c'est l'usage qui
    # change : 0,635 n'est plus présenté comme « la face de carte du
    # Cardforge » mais comme ce qu'il est. Ce qui doit avoir DISPARU est
    # l'affirmation, et ce qui doit être LÀ sont les deux vrais rapports.
    assert "la face de carte du Cardforge (650" not in py
    for vrai in ("0,7342", "0,7159", "9,2 %", "2,1 %"):
        assert vrai in py, f"l'aveu ne porte pas la mesure {vrai}"
    assert "0,1042" in py, "l'écart de portrait_16_9 est encore arrondi faux"
    assert "0,105" not in py


def test_le_juge_SURVIT_au_recadrage_reel_de_la_carte(tmp_path):
    """LA MOITIÉ QUI MANQUAIT À L'AVEU. Dire « le juge ne contrôle pas le
    format » ne suffit pas : l'image générée en 3:4 sera RECADRÉE à la toile
    puis à la coupe, et c'est l'image RECADRÉE que l'œil verra. Si le verdict
    s'effondrait au recadrage, la série serait jugée sur une image que
    personne ne regarde.

    On recadre donc la toile conforme aux deux rapports réels de la carte et
    on rejoue le juge dessus."""
    im = _toile_conforme()
    ref = FA.juger_image(_ecrire(im, tmp_path / "plein.png"))
    assert ref["verdict"] == "TIENT"
    for nom, ratio in (("toile", 0.7342), ("coupe", 0.7159)):
        w, h = im.size
        cible_w = int(round(h * ratio))
        dx = max(0, (w - cible_w) // 2)
        coupee = im.crop((dx, 0, dx + min(w, cible_w), h))
        v = FA.juger_image(_ecrire(coupee, tmp_path / f"{nom}.png"))
        assert v["verdict"] == "TIENT", (nom, v)
        assert not v["axes_rouges"], (nom, v["axes_rouges"])


def _ecrire(im, chemin):
    im.save(chemin)
    return chemin


def test_AUCUN_prompt_de_serie_ne_nomme_un_artiste():
    """LA RÈGLE DURE DU SKILL, BALAYÉE SUR LES 108 PROMPTS. Un nom d'artiste
    vivant dans un prompt payant, c'est un refus facturé au mieux, un pastiche
    juridiquement sale au pire — et c'est la ligne du projet. Un style se
    porte par des nombres."""
    interdits = [n.lower() for n in FA.NOMS_INTERDITS]
    assert "walkuski" in interdits and "wałkuski" in interdits
    # LES TROUS MESURÉS PAR LA RONDE, refermés : deux affichistes de plus, et
    # l'ÉCOLE nommée autrement qu'en deux mots collés — « a polish school
    # poster » passait au travers d'une liste de sous-chaînes.
    for nom in ("górka", "gorka", "eidrigevičius", "eidrigevicius"):
        assert nom in interdits, nom
    for essai in ("a polish school poster, oil on board",
                  "polishposter style, bone-coloured",
                  "in the manner of a POLISH theatre POSTER"):
        with pytest.raises(ValueError):
            FA.sans_nom_d_artiste(essai)
    for case in FA.serie_cases():
        p = FA.serie_prompt(case).lower()
        for nom in interdits:
            assert nom not in p, f"{case} : « {nom} » dans le prompt"
        assert "in the style of" not in p
        assert "polish poster" not in p, \
            "même l'école ne se nomme pas : on décrit, on ne cite pas"


def test_un_prompt_qui_nommerait_un_artiste_est_REFUSE_avant_l_envoi(
        monkeypatch):
    """« Un grep avant l'envoi coûte zéro et évite un refus facturé » : la
    règle est STRUCTURELLE, pas seulement testée.

    LES DEUX MOITIÉS COMPTENT, et la seconde est celle qui manquait : vérifier
    la fonction de garde ne prouve pas qu'on s'en sert. On empoisonne donc la
    table des sujets — la seule prose écrite à la main de tout le pipeline —
    et le prompt doit REFUSER de naître. Sans l'appel au garde-fou dans
    `serie_prompt`, ce contrôle passe au vert et le nom part chez le
    fournisseur."""
    assert FA.sans_nom_d_artiste("a single gaunt watchtower, bone-coloured")
    with pytest.raises(ValueError) as e:
        FA.sans_nom_d_artiste("in the style of Wałkuski, oil on board")
    assert "artiste" in str(e.value).lower()
    poison = dict(FA.SUJETS_SCENE)
    poison["tower"] = "a watchtower after Walkuski, bone-coloured"
    monkeypatch.setattr(FA, "SUJETS_SCENE", poison)
    with pytest.raises(ValueError):
        FA.serie_prompt("vista_tower")
    with pytest.raises(ValueError):
        FA.serie_prompt_retouche("vista_tower", [])


def test_le_meilleur_candidat_prefere_le_VERDICT_avant_le_score():
    """Un lot mêle les natures : trier sur le seul score choisirait un « hors
    style » à 90 % contre un « à retoucher » à 60 %. Or l'un est refusé par un
    axe CRITIQUE — chroma p95 hors corpus, la dérive du générateur libre — et
    l'autre non. Ce sont deux natures, pas deux notes ; c'est aussi ce qui
    décide si l'échelle monte d'une marche ou de deux."""
    lot = [{"verdict": "HORS STYLE", "score": 90.0, "img": "a.png"},
           {"verdict": "A RETOUCHER", "score": 60.0, "img": "b.png"},
           {"verdict": "HORS STYLE", "score": 95.0, "img": "c.png"}]
    assert FA.meilleur_candidat(lot)["img"] == "b.png"
    lot.append({"verdict": "TIENT", "score": 79.0, "img": "d.png"})
    assert FA.meilleur_candidat(lot)["img"] == "d.png"
    assert FA.meilleur_candidat([]) == {}


def test_l_accent_est_RARE_et_ne_touche_que_l_ocre():
    """« Un geste coloré unique dans un monde gris » : 6 œuvres sur 16 portent
    une seconde teinte, 10 n'en portent aucune. La fraction est relue dans la
    fiche (`n_sans_accent_isole`), pas décidée : 6/16 des 54 cases ocre, soit
    20. Et jamais ailleurs — les régimes rouge, violet et graphite disent
    eux-mêmes « no second hue » / « no hue anywhere »."""
    f = FA.fiche_style()
    avec = [c for c in FA.serie_cases() if FA.serie_accent(c)]
    attendu = int(round(54 * (f["n_oeuvres"] - f["n_sans_accent_isole"])
                        / f["n_oeuvres"]))
    assert len(avec) == attendu == 20
    assert all(FA.serie_famille(c) == "ocre" for c in avec)
    # ... et l'accent SE VOIT dans le prompt, sinon la mesure ne sert à rien
    p_avec = FA.serie_prompt(avec[0])
    sans = [c for c in FA.serie_cases()
            if FA.serie_famille(c) == "ocre" and not FA.serie_accent(c)]
    assert "One single accent" in p_avec
    assert "One single accent" not in FA.serie_prompt(sans[0])


def test_la_palette_du_prompt_SORT_de_la_fiche_et_le_graphite_est_sans_couleur():
    """Les hexadécimaux imposés au générateur sont les teintes MAÎTRES de la
    fiche — aucune couleur inventée. Et le régime graphite (20 cases sur 108)
    n'en porte AUCUNE : « essentiellement sans couleur » est un fait
    vérifiable, pas une figure de style."""
    maitres = {e["hex"].upper() for e in FA.fiche_style()["palette_maitre"]}
    vus = set()
    for case in FA.serie_cases():
        p = FA.serie_prompt(case)
        hexs = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", p)}
        assert hexs <= maitres, f"{case} : {hexs - maitres} hors fiche"
        assert hexs, f"{case} : aucun hexadécimal imposé"
        vus |= hexs
        if FA.serie_famille(case) == "graphite":
            colorees = {h for h in hexs
                        if h not in FA.PALETTE_NEUTRE}
            assert not colorees, f"{case} : graphite avec {colorees}"
    assert len(vus) >= 7, "la série n'exploite qu'une poignée de teintes"


# ── E. le juge, joué pour de vrai sur des synthétiques ───────────────────────

def test_le_juge_retient_la_conforme_et_REFUSE_la_saturee(tmp_path):
    """LA PREUVE DU JUGE, sans un centime. Deux images fabriquées ici : l'une
    tenue dans les bandes de la fiche, l'autre saturée ×3 et éclaircie ×1,55 —
    la dérive exacte d'un modèle laissé libre. Le juge tranche, et il dit sur
    QUELS axes critiques il refuse."""
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _toile_conforme().save(a)
    _toile_saturee().save(b)
    va, vb = FA.juger_image(a), FA.juger_image(b)
    assert va["verdict"] == "TIENT", va
    assert va["score"] >= 78 and va["dE_median"] <= 30
    assert not va["axes_rouges"]
    assert vb["verdict"] == "HORS STYLE", vb
    assert vb["axes_rouges"], "un refus sans axe nommé n'apprend rien"
    assert any("chroma" in x for x in vb["axes_rouges"]), vb["axes_rouges"]
    assert va["score"] > vb["score"]
    # et le troisième genre est bien AU MILIEU : ni tenu, ni hors style
    c = tmp_path / "c.png"
    _toile_a_retoucher().save(c)
    vc = FA.juger_image(c)
    assert vc["verdict"] == "A RETOUCHER", vc
    assert not vc["axes_rouges"]


# ── F. l'état de la série ────────────────────────────────────────────────────

def test_GET_serie_dit_l_etat_le_plafond_et_les_prix(monkeypatch):
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/face/serie")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["serie"] == "walkuski" and d["v"] == FA.SERIE_V
    assert d["total"] == 108 and d["faites"] == 0 and d["restantes"] == 108
    assert d["plafond_usd"] == pytest.approx(25.0)  # relevé utilisateur 27/08
    assert d["depense_totale_usd"] == 0.0
    assert d["reste_usd"] == pytest.approx(25.0)
    from app.services import pricing
    assert set(d["prix"]) == {"nano-banana-pro"}
    assert d["prix"]["nano-banana-pro"] == \
        pytest.approx(pricing.load()["nano_banana_pro_usd"])
    assert d["familles"] == {"ocre": 54, "rouge": 27, "graphite": 20,
                             "violet": 7}
    assert d["juge"]["copie_le"] == FA.SERIE_JUGE["copie_le"]
    assert isinstance(d["cases"], dict) and isinstance(d["refus"], dict)
    s.zero()


def test_GET_serie_ne_fait_JAMAIS_500(monkeypatch):
    s = _sentinelle(monkeypatch)
    for did in ("pas_un_deck", "deck_ZZZZZZZZ", "", "deck_00000000%0a"):
        r = _api("GET", f"/api/cards/{did}/face/serie")
        assert r.status_code in (400, 404), (did, r.status_code)
        assert r.status_code != 500
    # UN JEU VALIDE MAIS ABSENT : 404 des DEUX côtés. L'état rendait 200 quand
    # la campagne rendait 404 — le manifeste est global, mais la route vit
    # sous un deck, et deux réponses différentes pour la même question sont
    # une invitation à écrire un écran qui se trompe.
    r = _api("GET", "/api/cards/deck_00000000/face/serie")
    assert r.status_code == 404, r.status_code
    assert isinstance(r.json()["detail"], str)
    # un manifeste ABÎMÉ sur le disque se lit toléramment, il ne casse pas
    _serie_neuve()
    (FA.serie_root() / "walkuski.json").write_text("{ pas du json",
                                                   encoding="utf-8")
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/face/serie")
    assert r.status_code == 200, r.text
    assert r.json()["faites"] == 0
    assert r.json()["illisible"], "un manifeste illisible se DIT"
    _serie_neuve()
    s.zero()


# ── G. la campagne ───────────────────────────────────────────────────────────

def test_la_campagne_pose_la_case_gagnante_au_magasin_et_au_manifeste(
        monkeypatch):
    """LE CHEMIN HEUREUX. Un candidat Nano Banana Pro, le juge note, il
    TIENT : son fichier reste dans le magasin d'images de l'application
    et le manifeste porte son nom, son score et sa voie."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    r = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1")
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["traitees"]) == 1 and not d["refusees"]
    t = d["traitees"][0]
    assert t["verdict"] == "TIENT" and t["voie"] == "nano-banana-pro"
    assert t["score"] >= 78
    assert (_settings.images_path / t["img"]).is_file()
    # UN SEUL appel de générateur : la première marche suffit, la seconde
    # (payante elle aussi) n'est jamais gravie pour rien
    assert [a[0] for a in at.appels] == ["nano-banana-pro"]
    assert at.appels[0][2] == 1
    # le manifeste porte la case
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    assert m["v"] == FA.SERIE_V and m["serie"] == "walkuski"
    case = t["case"]
    assert m["cases"][case]["img"] == t["img"]
    assert m["cases"][case]["famille"] == FA.serie_famille(case)
    assert m["depense_totale_usd"] > 0
    s.zero()


def test_le_manifeste_est_VERSIONNE_et_ne_laisse_aucun_brouillon(monkeypatch):
    """Écriture atomique au patron de la phase 4 : brouillon UNIQUE, puis
    remplacement. Un `walkuski.json` tronqué serait un manifeste qui perd 108
    images payées."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    _lancer(f"/api/cards/{did}/face/serie/generer?limite=2")
    d = FA.serie_root()
    assert not list(d.glob("*.tmp")), list(d.glob("*.tmp"))
    m = json.loads((d / "walkuski.json").read_text("utf-8"))
    assert set(m) >= {"v", "serie", "cases", "refus", "depense_totale_usd",
                      "plafond_usd"}
    assert len(m["cases"]) == 2
    s.zero()


def test_l_ecriture_du_manifeste_est_ATOMIQUE_pas_seulement_propre(
        monkeypatch):
    """L'ABSENCE DE BROUILLON NE PROUVE PAS L'ATOMICITÉ : une écriture DIRECTE
    dans le fichier final n'en laisse pas non plus, et perdrait 108 images
    payées à la première interruption. Ce contrôle-ci distingue les deux — on
    fait échouer le RENOMMAGE. Une implémentation atomique lève et laisse le
    manifeste PRÉCÉDENT intact ; une écriture directe n'aurait rien à renommer,
    ne lèverait pas, et aurait déjà écrasé le fichier."""
    _serie_neuve()
    FA.manifeste_ecrire({"cases": {"vista_tower": {"img": "a.png"}},
                         "refus": {}, "depense_totale_usd": 1.0})
    final = FA.serie_root() / "walkuski.json"
    avant = final.read_text(encoding="utf-8")
    assert "vista_tower" in avant

    def _refus(self, cible):
        raise OSError(13, "le fichier est verrouille")
    monkeypatch.setattr(pathlib.Path, "replace", _refus)
    with pytest.raises(OSError):
        FA.manifeste_ecrire({"cases": {}, "refus": {},
                             "depense_totale_usd": 9.0})
    assert final.read_text(encoding="utf-8") == avant, \
        "le manifeste précédent a été perdu par une écriture interrompue"
    monkeypatch.undo()
    assert not list(FA.serie_root().glob("*.tmp")), "brouillon abandonné"
    _serie_neuve()


def test_la_reprise_ne_refait_PAS_les_cases_faites(monkeypatch):
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    a = _lancer(f"/api/cards/{did}/face/serie/generer?limite=2").json()
    faites = {t["case"] for t in a["traitees"]}
    n_appels = len(at.appels)
    b = _lancer(f"/api/cards/{did}/face/serie/generer?limite=2").json()
    assert not (faites & {t["case"] for t in b["traitees"]}), \
        "une case déjà faite a été REPAYÉE"
    assert len(at.appels) == n_appels + 2
    assert b["faites"] == 4 and b["restantes"] == 104
    s.zero()


def test_l_echelle_a_une_marche_refuse_ou_sert_puis_laisse_le_vectoriel(
        monkeypatch):
    """L'ÉCHELLE DU 27/08 AU SOIR : LA MARCHE UNIQUE nano-banana-pro («
    focalise toi uniquement sur nano banana pro » — la marche gpt-image-2
    par fal n'a gagné 0 case en 15 montées payées, elle sort de l'échelle
    comme FLUX et l'édition avant elle). Le candidat TIENT — servi. Sinon la
    case RESTE VECTORIELLE — et le refus est journalisé avec ses axes
    rouges, parce qu'un refus muet ne dit pas quoi changer."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="saturee").pose(monkeypatch)
    did = _deck()
    d = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1").json()
    assert [a[0] for a in at.appels] == ["nano-banana-pro"]
    assert not d["traitees"] and len(d["refusees"]) == 1
    ref = d["refusees"][0]
    assert ref["voie"] == "nano-banana-pro"
    assert ref["axes_rouges"], "le refus ne nomme aucun axe"
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    assert ref["case"] in m["refus"] and ref["case"] not in m["cases"]
    # ... et la même marche SERT quand le candidat tient
    _serie_neuve()
    at2 = _Atelier(banana_pro="conforme").pose(monkeypatch)
    d2 = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1").json()
    assert [a[0] for a in at2.appels] == ["nano-banana-pro"]
    assert d2["traitees"][0]["voie"] == "nano-banana-pro"
    # ... et un « à retoucher » sans marche au-dessus est un refus NOMMÉ
    # (meilleur score dit), pas une montée : il n'y a plus rien à gravir
    _serie_neuve()
    at3 = _Atelier(banana_pro="retouchable").pose(monkeypatch)
    d3 = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1").json()
    assert [a[0] for a in at3.appels] == ["nano-banana-pro"]
    assert not d3["traitees"] and len(d3["refusees"]) == 1
    assert d3["refusees"][0]["voie"] == "nano-banana-pro"
    assert "aucun candidat ne TIENT" in d3["refusees"][0]["motif"]
    s.zero()


def test_une_image_illisible_ne_perd_NI_les_cases_NI_la_depense(monkeypatch):
    """LE BLOQUANT DE LA RONDE. `PIL.UnidentifiedImageError` EST un `OSError` :
    il passait à côté de l'`except (KeyError, ValueError, RuntimeError)` de la
    boucle, la campagne LEVAIT, et comme le manifeste ne s'écrivait qu'APRÈS
    la boucle, les cases déjà GAGNÉES ET PAYÉES disparaissaient avec la
    dépense. Mesuré : deux cases perdues, `depense_totale` à 0,00 alors que
    0,054 $ étaient partis. Répété, c'est une dépense sans borne au compteur
    figé — le plafond ne protège plus rien.

    Deux corrections, un seul test : le manifeste s'écrit APRÈS CHAQUE CASE, et
    un juge qui tombe est traité comme un fournisseur qui tombe (la case part
    en refus journalisé, la campagne CONTINUE)."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme")
    vrai_poser = at._poser
    etat = {"n": 0}

    def _poser_casse(genre):
        etat["n"] += 1
        nom = vrai_poser(genre)
        if etat["n"] == 3:             # la 3e case, son candidat unique
            (_settings.images_path / nom).write_bytes(b"ceci n'est pas un PNG")
        return nom
    monkeypatch.setattr(at, "_poser", _poser_casse)
    at.pose(monkeypatch)
    did = _deck()
    r = _lancer(f"/api/cards/{did}/face/serie/generer?limite=4")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    # les deux premières cases sont SAUVÉES, sur le disque
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    assert len(m["cases"]) == 3, sorted(m["cases"])
    assert len(d["traitees"]) == 3 and len(d["refusees"]) == 1
    # la dépense est JUSTE : elle vaut la somme du journal, pas zéro
    assert m["depense_totale_usd"] == pytest.approx(
        sum(l["prix_usd"] for l in d["journal"])), (m, d["journal"])
    assert m["depense_totale_usd"] > 0
    # la case fautive est en refus, avec le motif technique
    ref = d["refusees"][0]
    assert ref["case"] in m["refus"]
    assert ref["motif"], "un refus muet n'apprend rien"
    s.zero()


def test_un_refus_ne_publie_JAMAIS_un_chemin_absolu(monkeypatch):
    """TROUVÉ EN ÉCRIVANT LES PREUVES DE LA RONDE. Le motif d'un refus
    recopiait l'exception telle quelle ; `PIL.UnidentifiedImageError` porte le
    CHEMIN COMPLET du fichier, donc le nom de compte de l'utilisateur — dans
    une réponse HTTP **et** dans le manifeste écrit sur le disque, que T5
    publiera. C'est la jurisprudence de la fuite de nom, rejouée par une porte
    que personne ne surveillait : le motif d'échec.

    La classe de l'exception reste (elle sert au diagnostic), le chemin part."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme")
    vrai_poser = at._poser

    def _poser_casse(genre):
        nom = vrai_poser(genre)
        (_settings.images_path / nom).write_bytes(b"pas un PNG")
        return nom
    monkeypatch.setattr(at, "_poser", _poser_casse)
    at.pose(monkeypatch)
    did = _deck()
    d = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1").json()
    motif = d["refusees"][0]["motif"]
    brut = json.dumps(d, ensure_ascii=False) + (
        FA.serie_root() / "walkuski.json").read_text(encoding="utf-8")
    compte = pathlib.Path.home().name
    assert compte not in brut, "le nom de compte est parti dans la réponse"
    assert not re.search(r"[A-Za-z]:[\\/]", brut), "un chemin absolu est servi"
    assert "UnidentifiedImageError" in motif, \
        "la classe de l'exception sert au diagnostic : elle reste"
    # un motif de fournisseur passe par le même filtre
    assert "<chemin>" in FA._sans_chemin(r"echec sur C:\Users\qqun\a.png")
    assert "qqun" not in FA._sans_chemin(r"echec sur C:\Users\qqun\a.png")
    s.zero()


def test_le_manifeste_est_ecrit_APRES_CHAQUE_CASE(monkeypatch):
    """La contre-preuve du bloquant, prise du côté du disque : le manifeste
    porte la case N pendant que la case N+1 se fabrique. Écrit après la
    boucle, il ne porterait rien tant que la campagne n'est pas finie."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme")
    vus = []
    vrai_poser = at._poser

    def _poser_espion(genre):
        m, _ = FA.manifeste_lire()
        vus.append(len(m["cases"]))
        return vrai_poser(genre)
    monkeypatch.setattr(at, "_poser", _poser_espion)
    at.pose(monkeypatch)
    did = _deck()
    _lancer(f"/api/cards/{did}/face/serie/generer?limite=3")
    # un candidat par case gagnée : au candidat de la 2e case le disque porte
    # déjà 1 case, à celui de la 3e il en porte 2.
    assert vus[0] == 0 and vus[1] == 1 and vus[2] == 2, vus
    s.zero()


def test_une_case_ne_s_OUVRE_que_si_l_echelle_ENTIERE_tient(monkeypatch):
    """LE MUR ATTEINT EN COURS DE CASE BRÛLAIT SANS TRACE. Mesuré par la
    revue : reste 0,058 $, la marche FLUX et la marche nano partent (0,057 $),
    la 3e ne passe pas — la case n'est tracée NULLE PART et le bilan annonce
    « 3 traitées, 0 refusées » pour de l'argent parti en fumée.

    Une case ne s'OUVRE donc que si L'ÉCHELLE COMPLÈTE tient sous le plafond,
    et le reliquat inutilisable est AVOUÉ au bilan. Le coût de l'échelle vient
    de la table (la marche unique Nano Banana Pro), jamais d'un nombre écrit
    ici. À UNE marche, la garde d'ouverture et la garde par tir sont LA MÊME
    arithmétique — le scénario « ouverte à moitié » est structurellement
    mort, et ce test garde l'autre moitié de la leçon : le mur qui arrête
    AVANT d'ouvrir, et le reliquat dit avec ses deux nombres."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    # Tarif du banc : 5,08 la marche — QUATRE cases traitées font 20,32 et
    # laissent 4,68 de reliquat sous l'enveloppe de 25,00 (relevé
    # utilisateur du 27/08 au soir ; l'historique des reliquats vit dans
    # l'historique de ce fichier).
    p = _prix_de_banc(monkeypatch, nano_banana_pro_usd=5.08)
    echelle = p["nano_banana_pro_usd"]
    assert FA.cout_echelle_usd() == pytest.approx(echelle) == pytest.approx(5.08)
    _Atelier(banana_pro="saturee").pose(monkeypatch)
    did = _deck()
    d = _lancer(f"/api/cards/{did}/face/serie/generer").json()
    assert d["arret"] == "plafond"
    assert not d["traitees"] and len(d["refusees"]) == 4
    assert d["depense_totale_usd"] == pytest.approx(20.32)
    assert d["reste_usd"] == pytest.approx(4.68)
    assert d["echelle_usd"] == pytest.approx(5.08)
    # LE RELIQUAT EST AVOUÉ, avec les deux nombres qui le rendent lisible
    assert "4,68" in d["message"] and "5,08" in d["message"], d["message"]
    assert d["reste_usd"] < d["echelle_usd"]
    # ... et TOUT tir du journal appartient à une case TRACÉE
    tracees = {t["case"] for t in d["traitees"]} | {r["case"] for r in d["refusees"]}
    assert {l["case"] for l in d["journal"]} == tracees
    assert len(d["journal"]) == 4, d["journal"]
    # le mur est UNE seule arithmétique, partagée par la boucle et par le tir
    # (la frontière suit l'enveloppe : 25,00 depuis le relevé utilisateur)
    assert FA.tient_sous_le_mur(24.0, 1.0) and not FA.tient_sous_le_mur(24.0, 1.01)
    s.zero()


def test_le_plafond_dur_ARRETE_la_campagne_avec_son_bilan(monkeypatch):
    """LE PLAFOND EST UN MUR, PAS UN VŒU. À 1,80 $ la marche unique, chaque
    case gagnée coûte 1,80 $ et s'ouvre au même prix : treize cases tiennent
    sous l'enveloppe de 25,00 $ (23,40 payés, 23,40 + 1,80 à l'ouverture de
    la quatorzième = 25,20 > 25 — elle ne PART PAS). La campagne s'arrête
    proprement, rend son bilan, et le prochain POST reprend là où elle
    s'est arrêtée. (Le scénario était à 11 cases sous 20,00 $, 8 sous 16,00
    et 15,00, 6 sous 12,00, 5 sous 10,00, 4 sous 8,00 et 3 sous 6,00 —
    re-dérivé à chaque relevé utilisateur.)"""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    _prix_de_banc(monkeypatch, nano_banana_pro_usd=1.80)
    _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    d = _lancer(f"/api/cards/{did}/face/serie/generer").json()
    assert d["arret"] == "plafond", d["arret"]
    assert len(d["traitees"]) == 13, [t["case"] for t in d["traitees"]]
    assert d["depense_totale_usd"] == pytest.approx(23.40)
    assert d["reste_usd"] == pytest.approx(1.60)
    assert d["faites"] == 13 and d["restantes"] == 95
    assert "plafond" in d["message"].lower()
    assert len(d["journal"]) == 13
    # un second POST ne dépense plus rien : le mur tient d'un appel à l'autre
    e = _lancer(f"/api/cards/{did}/face/serie/generer").json()
    assert e["arret"] == "plafond" and not e["traitees"]
    assert e["depense_totale_usd"] == pytest.approx(23.40)
    s.zero()


def test_le_prix_de_chaque_appel_vient_de_pricing_et_se_journalise_AVANT(
        monkeypatch):
    """AUCUN PRIX RECOPIÉ, ET LE JOURNAL PRÉCÈDE L'APPEL. Le journal porte,
    pour chaque tir, le modèle, le nombre d'images, le prix et le cumul
    AVANT — c'est ce qui rend le plafond vérifiable après coup."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    p = _prix_de_banc(monkeypatch)
    _Atelier(banana_pro="saturee").pose(monkeypatch)
    did = _deck()
    # deux cases refusées = deux tirs : le cumul AVANT s'enchaîne d'une
    # case à l'autre, et c'est lui qui rend le plafond vérifiable
    d = _lancer(f"/api/cards/{did}/face/serie/generer?limite=2").json()
    j = d["journal"]
    assert [l["modele"] for l in j] == ["nano-banana-pro", "nano-banana-pro"]
    assert j[0]["n"] == 1 and j[1]["n"] == 1
    assert j[0]["prix_usd"] == pytest.approx(p["nano_banana_pro_usd"])
    assert j[1]["prix_usd"] == pytest.approx(p["nano_banana_pro_usd"])
    assert j[0]["cumul_avant_usd"] == 0.0
    assert j[1]["cumul_avant_usd"] == pytest.approx(j[0]["prix_usd"])
    assert d["depense_totale_usd"] == pytest.approx(
        sum(l["prix_usd"] for l in j))
    # la pièce ne porte AUCUN montant écrit à la main — ni ceux d'hier, ni
    # ceux de la paire fal du 27/08
    sans = _py_sans_texte(pathlib.Path(FA.__file__))
    assert "_fabriquer_case" in sans, "le dépouillement a mangé le code"
    for montant in ("0.039", "0.003", "0.12", "0.15", "0.145"):
        assert montant not in sans, f"{montant} recopié dans la pièce"
    s.zero()


def test_la_campagne_EXIGE_une_confirmation_et_rend_le_devis(monkeypatch):
    """D2-2, NÉE D'UN INCIDENT. Une sonde de critique a émis 436 requêtes vers
    fal, toutes refusées à l'authentification : la clé neutralisée du banc a
    tenu et rien n'a été facturé — mais la route, elle, avait bel et bien
    lancé la série ENTIÈRE sur un POST NU. Une route qui dépense ne se
    déclenche pas par accident.

    Sans `{"confirmer": true}` elle répond le DEVIS et ne dépense RIEN. Le
    devis est la réponse utile : ce qu'on s'apprête à faire, ce que ça coûte
    au pire, ce qui reste sous le plafond."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    for corps in ({}, {"confirmer": False}, {"confirmer": "oui"}, None):
        r = _api("POST", f"/api/cards/{did}/face/serie/generer",
                 **({} if corps is None else {"json": corps}))
        assert r.status_code == 400, (corps, r.status_code)
        d = r.json()["detail"]
        assert "confirmer" in json.dumps(d), d
        assert d["devis"]["cases_manquantes"] == 108
        assert not at.appels, "LE DEVIS A DÉPENSÉ"
    assert not (FA.serie_root() / "walkuski.json").is_file(), \
        "le devis a écrit un manifeste"
    # avec la confirmation, la campagne part
    r = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1")
    assert r.status_code == 200 and len(at.appels) == 1
    s.zero()


def test_le_devis_est_arithmetiquement_JUSTE(monkeypatch):
    """Le devis n'est pas un slogan : chaque nombre se refait. Le pire cas est
    l'échelle complète × les cases que CETTE demande viserait — 16,20 $ pour
    la série entière à la marche unique : pour la PREMIÈRE fois l'enveloppe
    (25,00) couvre le pire cas d'une série vierge, et le devis le dit
    (`multi_session` retombe à False)."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    p = _prix_de_banc(monkeypatch)
    _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    d = _api("POST", f"/api/cards/{did}/face/serie/generer",
             json={}).json()["detail"]["devis"]
    echelle = p["nano_banana_pro_usd"]
    assert d["echelle_usd"] == pytest.approx(echelle) == pytest.approx(0.15)
    assert d["cases_manquantes"] == 108
    assert d["pire_cas_usd"] == pytest.approx(108 * echelle)
    assert d["pire_cas_usd"] == pytest.approx(16.20, abs=1e-3)
    assert d["plafond_usd"] == pytest.approx(25.0)  # relevé utilisateur 27/08
    assert d["depense_courante_usd"] == 0.0
    assert d["reste_usd"] == pytest.approx(25.0)
    assert d["cases_ouvrables"] == int(25.0 / echelle) == 166
    assert d["multi_session"] is False
    # le détail du devis nomme LA PAIRE, une image par marche
    assert set(d["detail_echelle"]) == set(FA.SERIE_ECHELLE)
    for m_ in FA.SERIE_ECHELLE:
        assert d["detail_echelle"][m_]["n"] == 1
    # le devis suit la DEMANDE : deux cases visées, deux cases chiffrées
    d2 = _api("POST", f"/api/cards/{did}/face/serie/generer"
                      "?cases=vista_tower,medallion_wolf", json={}
              ).json()["detail"]["devis"]
    assert d2["cases_manquantes"] == 2
    assert d2["pire_cas_usd"] == pytest.approx(2 * echelle)
    assert d2["multi_session"] is False
    s.zero()


def test_une_selection_VIDE_ne_lance_pas_toute_la_serie(monkeypatch):
    """MESURÉ : `?cases=` et `?cases=,,,` rendaient 200 et tentaient les 108
    cases. Sur une route qui dépense, « je n'ai rien choisi » ne peut pas
    vouloir dire « fais tout » : c'est un 400 nommé (D2-4)."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    for q in ("?cases=", "?cases=,,,", "?cases=%20", "?limite=", "?limite=0",
              "?limite=-4", "?limite=abc"):
        r = _lancer(f"/api/cards/{did}/face/serie/generer{q}")
        assert r.status_code == 400, (q, r.status_code, r.text[:160])
        assert isinstance(r.json()["detail"], str), q
    assert not at.appels, "une sélection vide a dépensé"
    # le paramètre ABSENT, lui, garde son sens : toute la série
    d = _api("POST", f"/api/cards/{did}/face/serie/generer",
             json={}).json()["detail"]["devis"]
    assert d["cases_manquantes"] == 108
    s.zero()


def test_deux_campagnes_simultanees_ne_depensent_pas_double(monkeypatch):
    """LA LEÇON T3 DE LA PHASE 4 : la concurrence d'un geste PAYANT se
    COALESCE. Deux POST partis ensemble sur la même série ne doivent produire
    qu'UNE campagne — sinon un double-clic double la facture, en silence."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()

    async def deux():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await asyncio.gather(*[
                c.post(f"/api/cards/{did}/face/serie/generer?limite=1",
                       json={"confirmer": True})
                for _ in range(6)])

    reps = asyncio.run(deux())
    assert all(r.status_code == 200 for r in reps)
    assert len(at.appels) == 1, \
        f"{len(at.appels)} tirs pour six clics simultanés"
    corps = [r.json() for r in reps]
    assert sum(1 for c in corps if c["coalesce"]) == 5
    faites = {t["case"] for c in corps for t in c["traitees"]}
    assert len(faites) == 1
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    assert len(m["cases"]) == 1
    s.zero()


def test_les_parametres_cases_et_limite_bornent_la_session(monkeypatch):
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    voulues = "stained_beacon,medallion_wolf"
    d = _lancer(f"/api/cards/{did}/face/serie/generer?cases={voulues}").json()
    assert {t["case"] for t in d["traitees"]} == set(voulues.split(","))
    e = _lancer(f"/api/cards/{did}/face/serie/generer?limite=3").json()
    assert len(e["traitees"]) == 3 and e["arret"] == "limite"
    # une case inconnue est NOMMÉE, pas avalée
    f = _lancer(f"/api/cards/{did}/face/serie/generer?cases=pas_une_case")
    assert f.status_code == 400
    assert "pas_une_case" in f.json()["detail"]
    s.zero()


def test_la_campagne_ne_fait_JAMAIS_500(monkeypatch):
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    # LE PLAFOND BORNE AUSSI LE BANC : sans limite, `?cases=` lance la
    # campagne ENTIÈRE (108 cases). À 8,00 $ le candidat le mur tombe après
    # trois cases — le test reste court ET prouve que la voie « sans
    # limite » est bien tenue par le plafond, pas par la patience.
    _prix_de_banc(monkeypatch, nano_banana_pro_usd=8.00)
    _Atelier(banana_pro="conforme").pose(monkeypatch)
    for did, attendu in (("pas_un_deck", 400), ("deck_ZZZZZZZZ", 400),
                         ("deck_00000000", 404)):
        r = _lancer(f"/api/cards/{did}/face/serie/generer")
        assert r.status_code == attendu, (did, r.status_code, r.text[:200])
    did = _deck()
    for q in ("?limite=0", "?limite=-4", "?limite=abc", "?cases=",
              "?cases=,,,", "?limite=99999"):
        r = _lancer(f"/api/cards/{did}/face/serie/generer{q}")
        assert r.status_code in (200, 400), (q, r.status_code)
        assert r.status_code != 500
    # un générateur qui TOMBE ne fait pas tomber la route : la case est
    # refusée, la campagne continue, et le motif est dit
    _serie_neuve()

    async def _casse(prompt):
        raise RuntimeError("fournisseur indisponible")
    monkeypatch.setattr(FA, "_tirer_banana_pro", _casse)
    r = _lancer(f"/api/cards/{did}/face/serie/generer?limite=2")
    assert r.status_code == 200, r.text
    d = r.json()
    assert not d["traitees"] and len(d["refusees"]) == 2
    assert "indisponible" in json.dumps(d["refusees"], ensure_ascii=False)
    # LE PRIX EST JOURNALISÉ AVANT L'APPEL, ET C'EST ICI QUE ÇA SE VOIT : un
    # tir qui TOMBE laisse quand même sa ligne, marquée `panne`. Journalisé
    # après, il ne laisserait rien — et le plafond compterait faux dans le
    # sens dangereux (on ne sait pas si le fournisseur a facturé avant de
    # tomber ; compter est l'erreur du bon côté).
    assert len(d["journal"]) == 2, d["journal"]
    assert all(l["panne"] for l in d["journal"]), d["journal"]
    assert d["depense_totale_usd"] > 0
    s.zero()


def test_la_cle_du_banc_est_neutralisee_et_la_sentinelle_COMPTE(monkeypatch):
    """LE BANC PROUVE SA PROPRE SÛRETÉ (leçon T3 de la phase 4). Deux moitiés :
    la clé du processus n'est pas la vraie, et la sentinelle attrape pour de
    bon ce qu'elle prétend attraper."""
    from app.config import settings
    assert settings.FAL_KEY == "test-key", \
        f"clé fal non neutralisée ({len(settings.FAL_KEY or '')} signes)"
    s = _sentinelle(monkeypatch)
    from app.services import image_providers as IP
    with pytest.raises(AssertionError):
        asyncio.run(IP.generate("nano-banana", "x", "square", 1))
    assert s.n == 1 and "image_providers.generate" in s.portes[0]


def test_la_piece_appelle_le_SERVICE_et_jamais_un_client_http_vers_elle_meme():
    """La campagne est une route du backend : elle ne doit pas se parler à
    elle-même en HTTP. Elle appelle le MÊME chemin de service que
    `/images/generate` — la façade `image_providers` pour la marche unique
    (l'idiome de routes.py, imité et non recopié)."""
    py = pathlib.Path(FA.__file__).read_text(encoding="utf-8")
    assert "from app.services import image_providers" in py
    sans = _py_sans_texte(pathlib.Path(FA.__file__))
    for interdit in ("httpx", "AsyncClient", "urlopen", "requests"):
        assert interdit not in sans, f"{interdit} : la pièce sort en HTTP"
    # LA voie passe par UNE fonction nommée, et rien d'autre
    assert "async def _tirer_banana_pro(" in py
    assert sans.count("image_providers") == 2, \
        ("la façade est nommée ailleurs que dans `_tirer_banana_pro` "
         "(un import + un appel)")


def test_la_voie_SAIT_appeler_son_service(monkeypatch):
    """LE CONTRÔLE QUI PROTÈGE T5. Toute la campagne est jouée par un espion
    posé SUR `_tirer_banana_pro` : son corps — le seul endroit qui touche un
    vrai générateur — n'est donc jamais exécuté par le banc. Une dérive de
    signature (`image_providers.generate` renomme un paramètre) ne se verrait
    qu'en campagne RÉELLE, après avoir payé les cases précédentes.

    Ici le corps est exécuté pour de bon, avec la VRAIE signature du
    service en face : on remplace la fonction de service par un faux qui
    commence par `inspect.signature(vraie).bind(...)`. L'appel est donc
    vérifié contre le contrat réel, et rien ne sort de la machine."""
    import inspect
    from app.services import image_providers as IP
    vus = []

    def _garde(vraie, retour):
        async def _faux(*a, **k):
            inspect.signature(vraie).bind(*a, **k)   # lève si la signature dérive
            vus.append((getattr(vraie, "__name__", "?"), a, sorted(k)))
            return retour
        return _faux

    monkeypatch.setattr(IP, "generate",
                        _garde(IP.generate, {"images": ["b.png"], "seed": None}))
    p = FA.serie_prompt("vista_tower")
    assert asyncio.run(FA._tirer_banana_pro(p)) == ["b.png"]
    assert [v[0] for v in vus] == ["generate"]
    # le cadre demandé est bien celui de la pièce, pas un défaut du service,
    # et la marche nomme SON modèle
    assert vus[0][1][0] == "nano-banana-pro"
    assert FA.SERIE_TAILLE in vus[0][1]
    # ... et le garde-fou de nom vaut sur la voie, pas seulement à la
    # construction du prompt : c'est la dernière porte avant le fournisseur.
    with pytest.raises(ValueError):
        asyncio.run(FA._tirer_banana_pro("in the style of Walkuski"))


# NOTE DU 27/08 : les deux contrôles du DÉCOUPAGE FLUX (plafond fournisseur
# `num_images ≤ 4`, prix compté à l'image et non à l'appel) sont partis avec
# la marche qu'ils gardaient — la paire fal tire UN candidat par marche, et
# le pin `n == 1` du journal vit dans le test du journal-avant-l'appel. La
# leçon du fournisseur (422 sur num_images > 4, douze cases payées mortes le
# 25/08) reste consignée au plan §T1 et dans l'historique de ce fichier.


# ── H. l'écran : la voie, la retombée avouée, le miroir ──────────────────────

def test_la_serie_est_au_MIROIR_entre_l_ecran_et_la_piece():
    assert js_pairs("SERIES") == list(FA.SERIES)
    assert FA.SERIES[0][0] == "vectoriel", \
        "le vectoriel reste le socle : il est la voie par défaut"


def test_le_selecteur_de_serie_est_DERIVE_et_voyage_avec_le_deck():
    """`doc.face.serie` est porté par le DOCUMENT, pas par une préférence
    d'application : la voie choisie voyage avec le jeu (export, duplication,
    autre poste). Une préférence `dz_*` aurait fait de la même carte deux
    cartes différentes selon la machine qui l'ouvre."""
    src = js_code()
    assert re.search(r"serie:\s*\"vectoriel\"", src), \
        "doc.face.serie absent de l'état du module"
    assert "dz_serie" not in src and "localStorage" not in src.split(
        "function pileLoad")[0], "la voie ne se range pas hors du document"
    assert 'M.api.get("serie")' in src, "l'état de série vient de la route"
    # le sélecteur est DÉRIVÉ de l'état : il se lit dans le document au rendu
    bloc = src[src.index('id="cf-face-series"'):]
    bloc = bloc[:bloc.index("</div>'")]
    assert "SERIES.map" in bloc, "les voies sont dérivées de la table"
    assert "active" in bloc


def test_la_retombee_vectorielle_est_AVOUEE_a_l_ecran():
    """D1 : « la série habille, elle ne remplace pas ». Une case sans image
    montre le DESSIN, avec un insigne qui le dit — un écran qui montrerait le
    vectoriel en silence laisserait croire que la série est complète."""
    src = js_code()
    assert "cf-face-retombee" in src, "l'insigne de retombée n'existe pas"
    assert "vectoriel" in src
    # le compte « n / 108 » est calculé, jamais écrit
    ong = src[src.index("data-tab=\"cat\""):]
    ong = ong[:ong.index("</button>")]
    assert "108" not in ong
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-face-retombee" in css, "l'insigne n'est pas habillé"


def test_le_compteur_de_depense_est_AFFICHE_pas_seulement_charge():
    """D2 dit « le compteur s'affiche » — il était CHARGÉ et jamais lu. Une
    dépense qu'on ne voit pas est une dépense qu'on ne surveille pas ; le
    plafond doit être lisible AVANT d'être atteint. Dérivé pur de l'état déjà
    en mémoire (aucun appel de plus), et toujours AUCUN bouton de campagne :
    l'écran informe, il ne dépense pas."""
    src = js_code()
    note = src[src.index('id="cf-face-serie-note"'):]
    note = note[:note.index("</p>'")]
    assert "SERIE.depense" in note and "SERIE.plafond" in note, note[:400]
    assert "usdFmt" in note, "le montant n'est pas formaté comme les autres"
    assert "plafond" in note.lower()
    # ET LA CONDITION N'EST PAS MORTE : la première rédaction de ce contrôle
    # ne lisait que la présence des NOMS, si bien qu'un `false ?` à la place
    # de la garde laissait le test vert sur un compteur jamais rendu (mutation
    # jouée, survivante). La garde elle-même est donc épinglée.
    assert "(SERIE.plafond ? " in note, \
        "la garde du compteur ne lit plus l'état : le montant ne s'affichera pas"
    # aucun déclencheur de campagne dans l'écran (T5 seule dépense)
    assert "serie/generer" not in src, "un bouton de campagne est apparu"
    assert "confirmer" not in src


def test_la_serie_ne_cree_PAS_un_quatrieme_schema_de_source():
    """Les trois schémas de `artSource` (`cat:`, `local:`, `img:`) suffisent :
    une case de série EST un fichier du magasin d'images, donc `img:`. Un
    quatrième schéma aurait doublé la table de résolution pour rien."""
    src = js_code()
    art = src[src.index("async function artSource("):]
    art = art[:art.index("\n  }")]
    for schema in ('"cat:"', '"local:"', '"img:"'):
        assert schema in art, schema
    assert "serie:" not in art, "un quatrième schéma est né dans artSource"
    # la tuile de série pose bien une source `img:`
    assert 'setArt("img:" + ' in src


# ── T6 : la dette de prose de T5 — « par session » contre l'enveloppe TOTALE ──

def test_le_devis_dit_ENVELOPPE_TOTALE_et_jamais_par_session(monkeypatch):
    """DETTE T5 → T6, ET C'EST UNE PHRASE D'ARGENT. Les deux textes SERVIS
    annonçaient « un plafond de 6,00 $ PAR SESSION » alors que la machinerie,
    elle, applique une ENVELOPPE TOTALE : `devis()` relit
    `depense_totale_usd` DU MANIFESTE SUR DISQUE, et
    `test_le_plafond_dur_ARRETE_la_campagne_avec_son_bilan` épingle déjà que
    le mur tient d'un POST à l'autre. Le texte promettait donc une remise à
    zéro qui n'existe pas — la pire des erreurs de prose sur une route qui
    dépense : elle invite à relancer.

    LE CONTRÔLE EST UNE ÉGALITÉ, PAS UNE SOUS-CHAÎNE. Un `assert "enveloppe"
    in message` resterait vert sur une phrase qui garde AUSSI « par session »
    à côté ; une phrase d'argent se relit en entier. Les NOMBRES, eux, ne sont
    jamais recopiés : ils viennent du devis que la même réponse porte."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    _Atelier(banana_pro="conforme").pose(monkeypatch)
    did = _deck()
    detail = _api("POST", f"/api/cards/{did}/face/serie/generer").json()["detail"]
    d = detail["devis"]
    attendu = (
        "Cette campagne DÉPENSE. Elle vise " + str(d["cases_manquantes"])
        + " case(s), soit au pire " + FA._usd(d["pire_cas_usd"])
        + " $ sur une ENVELOPPE TOTALE de " + FA._usd(d["plafond_usd"])
        + " $ (il reste " + FA._usd(d["reste_usd"]) + " $, de quoi ouvrir "
        + str(d["cases_ouvrables"]) + " case(s)). L'enveloppe est CUMULATIVE : "
        "chaque lancement reprend la dépense déjà journalisée, elle ne se "
        "remet jamais à zéro. Renvoyez la MÊME requête avec "
        "{\"confirmer\": true} pour la lancer.")
    assert detail["message"] == attendu, detail["message"]
    assert "par session" not in detail["message"].lower()
    # ET AUCUNE AUTRE PHRASE SERVIE NE LE PROMET. Le balayage porte sur les
    # CHAÎNES seules, pas sur le fichier : un commentaire Python n'est jamais
    # servi, et celui qui documente cette dette CITE forcément la formule
    # fautive (le grep de prose de la phase 3, quatrième rencontre). Ce qui se
    # mesure, c'est ce que l'utilisateur peut lire.
    import io as _io
    import tokenize as _tk
    src = pathlib.Path(FA.__file__).read_text(encoding="utf-8")
    chaines = [t.string for t in _tk.generate_tokens(_io.StringIO(src).readline)
               if t.type == _tk.STRING]
    assert chaines, "le dépouillement n'a trouvé aucune chaîne"
    coupables = [c for c in chaines if "par session" in c.lower()]
    assert not coupables, coupables
    s.zero()


def test_l_ecran_P1_dit_ENVELOPPE_TOTALE_et_jamais_par_session():
    """L'AUTRE MOITIÉ DE LA MÊME DETTE, du côté servi à l'œil. Le compteur de
    P1 lisait « sur un plafond de X par session ». Même correction, même
    contrôle par ÉGALITÉ sur le fragment rendu — et la garde `(SERIE.plafond ?`
    reste en place (elle a déjà eu un mutant survivant, cf. le test du
    compteur affiché)."""
    src = js_code()
    note = src[src.index('id="cf-face-serie-note"'):]
    note = note[:note.index("</p>'")]
    frag = note[note.index("(SERIE.plafond ? "):]
    frag = frag[:frag.index("\n")]
    assert frag == (
        "(SERIE.plafond ? '. Dépense de la série : <b>' + esc(usdFmt(SERIE.depense))"), frag
    suite = note[note.index(frag) + len(frag):]
    suite = suite[:suite.index(": '')")]
    assert suite == (
        "\n          + '</b> sur une <b>enveloppe totale</b> de <b>'"
        " + esc(usdFmt(SERIE.plafond))\n"
        "          + '</b> — elle est CUMULATIVE : chaque campagne reprend le total"
        " déjà dépensé, elle ne repart jamais de zéro'\n          "), repr(suite)
    assert "par session" not in src.lower(), \
        "« par session » survit quelque part dans la pièce"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
