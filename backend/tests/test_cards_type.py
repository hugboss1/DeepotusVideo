# -*- coding: utf-8 -*-
"""Card Forge — P3 « Typographie » : les seuils chiffrés de la pièce.

Ce que ce fichier verrouille, dans l'ordre des seuils de la spec (§4, pièce
03) :

  1. **23 familles sélectionnables.** Elles sont LUES sur le disque, jamais
     devinées : 22 `.ttf` et un `.otf` (`PolandKaito.otf` — le piège nommé
     par la spec). Chaque fichier annoncé par l'API existe vraiment.
  2. **0 troncature silencieuse.** Le titre de démonstration fait 44
     caractères — exactement le cas de la spec — et il est SERVI EN ENTIER
     par le gabarit. Aucun chemin du module ne raccourcit un texte destiné au
     dessin : le seul `slice` de `mod-type.js` est le plafond de stockage à
     4000 caractères, et le caractère « … » n'apparaît nulle part dans le
     moteur de mise en page.
  3. **>= 10 réglages par slot.** Le schéma en compte 27, dont les onze cités
     par la spec (police, corps, couleur, interlettrage, interligne,
     alignement H, alignement V, contour, ombre, casse, rotation).
  4. **L'encadré de règles accepte >= 400 caractères et reste dans la zone
     sûre, mesuré en px.** Le texte du gabarit fait plus de 400 caractères ;
     le confinement est jugé par `layout()` avec la règle de géométrie du
     CORE, sur les encombrements RÉELLEMENT MESURÉS par le navigateur.
  5. **Les gabarits tiennent sur les douze formats.** Exprimés en fractions
     de la zone sûre — et de la zone sûre EN PIXELS, celle qui existe dans le
     fichier livré, pas celle des millimètres demandés — ils sortent dans la
     zone sûre à 12 formats x 3 définitions x 4 gabarits, à zéro pixel.
  6. **Une seule table de gabarits.** Le bloc `CF-TYPE-PRESETS` de
     `js/mod-type.js` est EXTRAIT et comparé au dictionnaire Python, clé par
     clé, texte par texte. Idem pour `CF-TYPE-DEFAULTS`. Deux tables recopiées
     à la main auraient dérivé au premier ajout — et le lab hors ligne aurait
     servi une autre mise en page que le backend.
  7. **Jamais de 500 sur un corps mal formé** (spec §2.5), et les chemins
     restent RELATIFS au préfixe `/api/cards/{did}/type` (règle 8).

Run : <embedded python> backend/tests/test_cards_type.py
"""
import asyncio
import io
import json
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
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402

from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import type as TY                       # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
JS = REPO / "frontend" / "cardforge" / "js" / "mod-type.js"
CSS = REPO / "frontend" / "cardforge" / "css" / "mod-type.css"

# ── les seuils, ÉCRITS EN DUR (spec §4, pièce 03) ───────────────────────────
FONTS_ATTENDUES = 23
TTF_ATTENDUS = 22
OTF_ATTENDUS = 1
TITRE_LONG_CAR = 44          # « un titre de 44 caractères »
REGLES_CAR_MIN = 400         # « l'encadré accepte >= 400 caractères »
REGLAGES_MIN = 10            # « >= 10 réglages par slot »
# les onze réglages nommés par la spec, dans son ordre
REGLAGES_NOMMES = ("font", "size_pt", "color", "track", "leading", "align",
                   "valign", "outline", "shadow", "caps", "rotate")


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _did() -> str:
    r = _api("POST", "/api/cards/decks", json={"name": "Typo"})
    assert r.status_code == 200, r.text
    return r.json()["deck"]["id"]


# ═══════════════════ 1. les 23 polices, lues sur le disque ══════════════════

def test_23_familles_dont_un_otf_et_pas_devine():
    """La spec insiste : « 22 .ttf + PolandKaito.otf — lire l'extension, ne
    pas la deviner ». Ici l'extension vient de `Path.suffix`, et le fichier
    annoncé par l'API doit exister."""
    d = TY.fonts_dir()
    assert d.is_dir(), f"dossier des polices introuvable : {d}"
    fonts = TY.scan_fonts()
    assert len(fonts) == FONTS_ATTENDUES, \
        f"{len(fonts)} polices servies, {FONTS_ATTENDUES} attendues"
    assert sum(1 for f in fonts if f["ext"] == "ttf") == TTF_ATTENDUS
    assert sum(1 for f in fonts if f["ext"] == "otf") == OTF_ATTENDUS
    kaito = [f for f in fonts if f["id"] == "PolandKaito"]
    assert kaito and kaito[0]["ext"] == "otf" and kaito[0]["file"] == "PolandKaito.otf"
    for f in fonts:
        assert (d / f["file"]).is_file(), f["file"]
        assert f["url"] == "/fonts/" + f["file"]
        assert f["family"].startswith(TY.FONT_FAMILY_PREFIX)
        assert f["bytes"] > 0
    # aucune police « autre » : le catalogue est entièrement libellé
    assert not [f for f in fonts if f["kind"] == "autre"], \
        "une police du dossier n'est pas répertoriée dans FONT_META"


def test_le_repli_hors_ligne_de_l_ecran_porte_les_memes_23_polices():
    """Le lab reste utilisable quand /api/cards n'est pas monté : sa table de
    repli doit lister EXACTEMENT les mêmes familles, mêmes extensions."""
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("const FONTS_LOCAL = [", 1)[1].split("].map(", 1)[0]
    lignes = re.findall(r'\["([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\]',
                        bloc)
    assert len(lignes) == FONTS_ATTENDUES, f"{len(lignes)} dans le repli"
    par_id = {f["id"]: f for f in TY.scan_fonts()}
    assert {li[0] for li in lignes} == set(par_id)
    for fid, label, kind, ext in lignes:
        assert par_id[fid]["label"] == label, fid
        assert par_id[fid]["kind"] == kind, fid
        assert par_id[fid]["ext"] == ext, fid


def test_api_fonts_sert_le_catalogue():
    did = _did()
    r = _api("GET", f"/api/cards/{did}/type/fonts")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["count"] == FONTS_ATTENDUES
    assert d["ttf"] == TTF_ATTENDUS and d["otf"] == OTF_ATTENDUS
    assert "json" in r.headers.get("content-type", "")
    # un identifiant hors motif ne descend pas plus loin
    assert _api("GET", "/api/cards/pas-un-did/type/fonts").status_code == 400


# ═══════════════ 2. les deux tables miroir JS <-> Python ════════════════════

def _bloc_js(nom: str) -> str:
    src = JS.read_text(encoding="utf-8")
    m = re.search(r"CF-TYPE-" + nom + r"-BEGIN[^\n]*\n(.*?)/\*[^\n]*CF-TYPE-"
                  + nom + r"-END", src, re.S)
    assert m, f"bloc CF-TYPE-{nom} introuvable dans {JS}"
    corps = m.group(1)
    corps = corps.split("=", 1)[1].strip()
    return corps.rstrip().rstrip(";").strip()


def test_la_table_des_gabarits_est_la_meme_des_deux_cotes():
    """`test_cards_core.py` fait pareil pour la table des FORMATS : une table
    recopiée ne prouve rien contre celle qui l'a produite, alors on compare
    les deux."""
    js = json.loads(_bloc_js("PRESETS"))
    assert js == TY.PRESETS, "les gabarits de l'écran et du backend divergent"


def test_les_defauts_de_slot_sont_les_memes_des_deux_cotes():
    js = json.loads(_bloc_js("DEFAULTS"))
    assert js == TY.SLOT_DEFAULTS


# ═══════════ 3. >= 10 réglages par slot, et les onze nommés ═════════════════

def test_au_moins_dix_reglages_par_slot():
    cles = set(TY.SLOT_DEFAULTS) - {"id", "label", "box", "text", "on"}
    assert len(cles) >= REGLAGES_MIN, sorted(cles)
    for k in REGLAGES_NOMMES:
        assert k in TY.SLOT_DEFAULTS, k
    # 49 clés en tout, dont 44 réglages (`hyphen` est arrivé avec la césure,
    # `just_max` et `last_pct` avec le plafond d'élasticité et la ligne creuse,
    # `read_pt` avec le plancher de lisibilité, `plate_color` / `plate_alpha`
    # / `plate_radius` avec la plaque de fond de la phase 3a, `lock` avec le
    # verrou d'édition de la 3b, `kind` / `src` / `fit` avec le calque
    # d'image de la 3b-T2, et les DIX de la phase 5-T2 : l'encre des formes
    # (`fill`, `fill_alpha`, `stroke`, `stroke_mm`), la flèche (`head_mm`,
    # `arrow_start`, `arrow_end`), l'axe (`flip`) et le contour propre d'une
    # zone (`plate_stroke`, `plate_stroke_mm`))
    assert len(TY.SLOT_DEFAULTS) == 49, sorted(TY.SLOT_DEFAULTS)
    assert len(cles) == 44, sorted(cles)


# ═══════════ 4. le titre de 44 caractères et l'encadré de 400+ ══════════════

def test_le_titre_de_44_caracteres_est_servi_entier():
    """La barre coupe à 25 caractères, en silence. Ici le gabarit porte le cas
    difficile dès l'ouverture : 44 caractères, entiers."""
    titres = [s for s in TY.PRESETS["champion"]["slots"] if s["id"] == "title"]
    assert titres and len(titres[0]["text"]) == TITRE_LONG_CAR, \
        f"titre de démonstration : {len(titres[0]['text'])} caractères"
    # et il traverse la normalisation sans perdre un caractère
    g = CT.geom("poker_eu", 300)
    pose = [s for s in TY.preset_slots("champion", g) if s["id"] == "title"][0]
    assert pose["text"] == titres[0]["text"]


def test_aucun_chemin_du_module_ne_raccourcit_un_texte():
    """La régression classique : « ça ne tient pas, on met des points de
    suspension ». Le moteur de mise en page ne contient ni ellipse, ni
    `substr`, ni troncature depuis le début (`slice(0, n)`) — la seule
    troncature du fichier est le plafond de STOCKAGE à 4000 caractères, dans
    la normalisation.

    Et surtout : le compte est MESURÉ à l'exécution. `layoutSlot` recompte les
    glyphes après la mise en page et rend l'écart dans `cut` ; c'est ce
    chiffre-là que le panneau affiche. Un test statique dit ce que le code ne
    contient pas ; seul le recompte dit ce qu'il fait."""
    src = JS.read_text(encoding="utf-8")
    moteur = src.split("3. MISE EN PAGE", 1)[1].split("5. LE MODULE", 1)[0]
    assert "…" not in moteur, "une ellipse dans le moteur de mise en page"
    assert "substr" not in moteur
    for m in re.finditer(r"\.slice\(\s*0\s*,", moteur):
        raise AssertionError("troncature dans le moteur de mise en page : "
                             + moteur[max(0, m.start() - 60):m.start() + 20])
    # le plafond de stockage, lui, est bien là et vaut 4000
    assert re.search(r"\.slice\(0,\s*4000\)", src)
    # l'invariant est RECOMPTÉ, pas affirmé : `cut` vient d'une soustraction
    assert re.search(r"const cut = Math\.max\(0, flat\(text\) - flat\(", src)
    assert re.search(r"cut:\s*cut", src)
    # ... et c'est ce chiffre que le relevé affiche
    assert "hero.m.cut" in src


def test_l_encadre_de_regles_depasse_400_caracteres_partout():
    for pid, p in TY.PRESETS.items():
        for s in p["slots"]:
            if s["id"] != "rules":
                continue
            assert len(s["text"]) >= REGLES_CAR_MIN, \
                f"{pid}/rules : {len(s['text'])} caractères"


def test_l_encadre_de_regles_reste_dans_la_zone_sure_en_pixels():
    """Le seuil se mesure EN PIXELS, sur l'encombrement réel du texte : c'est
    le navigateur qui mesure (lui seul a les polices et le moteur de texte du
    fichier livré), le backend qui juge, avec la règle du CORE."""
    g = CT.geom("poker_eu", 300)
    slots = TY.preset_slots("champion", g)
    regles = [s for s in slots if s["id"] == "rules"][0]
    assert len(regles["text"]) >= REGLES_CAR_MIN
    b = TY.box_px(regles["box"], g)
    # un encombrement plausible : le pavé occupe 96 % de la boîte
    ink = [b[0] + 2, b[1] + 2, b[2] * 0.96, b[3] * 0.96]
    rep = TY.layout(g, slots, {"rules": ink})
    ligne = [r for r in rep["slots"] if r["id"] == "rules"][0]
    assert ligne["ink_inside_safe"] is True, ligne["ink_out_px"]
    assert rep["safe_rect_px"][2:] == [673.0, 969.0]      # la zone sûre mesurée
    assert rep["summary"]["ok"] is True
    # ... et un pavé qui déborde EST signalé : le juge n'est pas complaisant
    large = [b[0] - 90, b[1], b[2] + 180, b[3]]
    rep2 = TY.layout(g, slots, {"rules": large})
    l2 = [r for r in rep2["slots"] if r["id"] == "rules"][0]
    assert l2["ink_inside_safe"] is False
    assert l2["ink_out_px"]["left"] > 0
    assert "rules" in rep2["summary"]["outside_safe"]


# ═══════════ 5. les gabarits tiennent sur les douze formats ═════════════════

def test_les_gabarits_tiennent_dans_la_zone_sure_des_douze_formats():
    """12 formats x 3 définitions x 4 gabarits = 144 mises en page, zéro
    pixel hors zone sûre. C'est ce que garantit le repère : un gabarit est
    écrit en fractions de la zone sûre EN PIXELS, pas de la rogne."""
    n = 0
    for fmt in CT.FORMATS:
        for dpi in CT.DPI_CHOICES:
            g = CT.geom(fmt, dpi)
            for pid in TY.PRESETS:
                rep = TY.layout(g, TY.preset_slots(pid, g))
                assert rep["summary"]["ok"], \
                    f"{fmt}@{dpi} / {pid} : {rep['summary']['outside_safe']}"
                n += 1
    assert n == len(CT.FORMATS) * len(CT.DPI_CHOICES) * len(TY.PRESETS) == 144


def test_la_zone_sure_du_gabarit_est_celle_des_pixels_pas_des_millimetres():
    """Sur poker_eu, 3 mm de consigne donnent une zone sûre de 673 x 969 px
    CENTRÉE dans la rogne — soit 3,0057 mm en largeur et 2,9633 mm en
    hauteur. Un gabarit calé sur les 3 mm demandés tombait 0,07 px hors de la
    zone sûre du fichier livré, et le contrôle avant vol l'aurait signalé."""
    g = CT.geom("poker_eu", 300)
    sx, sy, sw, sh = TY.safe_rect_mm(g)
    assert round(sx, 4) == 3.0057 and round(sy, 4) == 2.9633
    assert abs(sx - 3.0) > 1e-4 and abs(sy - 3.0) > 1e-4
    # l'aller-retour mm -> px retombe EXACTEMENT sur la zone sûre en pixels
    assert abs(TY.box_px([sx, sy, sw, sh], g)[0] - g.safe_off_px[0]) < 1e-4
    assert abs(TY.box_px([sx, sy, sw, sh], g)[1] - g.safe_off_px[1]) < 1e-4
    assert abs(TY.mm2px(sw, g.dpi) - g.safe_px[0]) < 1e-4
    assert abs(TY.mm2px(sh, g.dpi) - g.safe_px[1]) < 1e-4


def test_la_conversion_des_points_est_celle_de_la_typographie():
    """1 pt = 1/72 in. À 300 DPI un corps de 12 pt fait 50 px, à 600 DPI il en
    fait 100 : c'est ce qui rend l'aperçu et le fichier identiques quand la
    définition change."""
    assert TY.pt2px(12, 300) == 50.0
    assert TY.pt2px(12, 600) == 100.0
    assert round(TY.pt2px(8.5, 300), 4) == 35.4167


# ═══════════════════ 6. les routes, et leurs erreurs ════════════════════════

def test_api_presets_convertit_pour_le_format_demande():
    did = _did()
    r = _api("GET", f"/api/cards/{did}/type/presets",
             params={"fmt": "micro", "dpi": 600})
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["presets"]) == len(TY.PRESETS)
    assert d["geom"]["canvas_px"] == [900, 1200]      # micro à 600 DPI
    for p in d["presets"]:
        assert p["ok"] is True, (p["id"], p["outside_safe"])
        assert p["n"] == len(p["slots"]) >= 2
    r = _api("GET", f"/api/cards/{did}/type/presets", params={"fmt": "nawak"})
    assert r.status_code == 400 and "poker_eu" in r.json()["detail"]


def test_api_layout_juge_les_encombrements_mesures():
    did = _did()
    g = CT.geom("poker_us", 300)
    slots = TY.preset_slots("champion", g)
    b = TY.box_px(slots[1]["box"], g)                 # le titre
    dehors = [b[0] - 200, b[1], b[2], b[3]]
    r = _api("POST", f"/api/cards/{did}/type/layout",
             json={"fmt": "poker_us", "dpi": 300, "slots": slots,
                   "ink": {"title": dehors}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["canvas_px"] == [825, 1125]              # parité nanDECK
    assert d["safe_rect_px"] == [75.0, 75.0, 675.0, 975.0]
    assert d["summary"]["outside_safe"] == ["title"]
    ligne = [x for x in d["slots"] if x["id"] == "title"][0]
    # le titre commence à 75 + 0,19 x 675 = 203,25 px ; décalé de 200 px il
    # dépasse le bord gauche de la zone sûre de 71,75 px, au centième près
    assert ligne["ink_out_px"]["left"] == 71.75
    assert ligne["inside_safe"] is True               # la BOÎTE, elle, tenait


def test_un_corps_mal_forme_ne_fait_jamais_500():
    """Spec §2.5. Aucun de ces corps n'est légal ; aucun ne doit faire 500."""
    did = _did()
    for corps in ({}, {"slots": "pas une liste"}, {"slots": [1, 2, 3]},
                  {"fmt": None, "dpi": "beaucoup"},
                  {"slots": [{"id": "!!", "box": ["a", "b", "c", "d"],
                              "size_pt": "grand", "color": "rouge",
                              "align": 42, "leading": None}]},
                  {"ink": "n'importe quoi"},
                  {"slots": [{"id": "x"}], "ink": {"x": ["a", 1, 2, 3]}}):
        r = _api("POST", f"/api/cards/{did}/type/layout", json=corps)
        assert r.status_code in (200, 400), (corps, r.status_code, r.text)
        assert "json" in r.headers.get("content-type", "")
    # deux slots de même id : ils sont dédoublonnés, pas confondus (P4
    # remplirait sinon le mauvais)
    r = _api("POST", f"/api/cards/{did}/type/layout",
             json={"slots": [{"id": "title"}, {"id": "title"}]})
    ids = [s["id"] for s in r.json()["slots"]]
    assert ids == ["title", "title2"]


def test_les_routes_sont_montees_sous_le_prefixe_de_la_piece():
    """Règle 8 : chemins RELATIFS, préfixe posé par cards/__init__.py."""
    from app.main import app
    chemins = list(app.openapi().get("paths", {}))
    for attendu in ("/api/cards/{did}/type/fonts",
                    "/api/cards/{did}/type/presets",
                    "/api/cards/{did}/type/layout"):
        assert attendu in chemins, f"{attendu} absent"


def test_le_contrat_sortant_de_la_piece_a_la_forme_gelee():
    """`doc.type.slots[] = {id, label, box:[x,y,w,h] en mm depuis le coin
    ROGNE}` — c'est ce que P4 et P7 lisent (spec §2.3)."""
    g = CT.geom("tarot_eu", 300)
    for s in TY.preset_slots("champion", g):
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,23}", s["id"]), s["id"]
        assert isinstance(s["label"], str) and s["label"]
        assert isinstance(s["box"], list) and len(s["box"]) == 4
        assert all(isinstance(v, float) for v in s["box"])
        assert s["box"][2] > 0 and s["box"][3] > 0
        assert s["side"] in TY.SIDES and isinstance(s["on"], bool)


# ════════ 7. CE QUE LES DEUX CRITIQUES ONT MESURÉ, ET QUI EST CORRIGÉ ═══════
# Chaque test ci-dessous verrouille un manque nommé par un critique. Ils sont
# STATIQUES par nature : la mesure vit dans le navigateur (lui seul a les
# polices et le moteur de texte du fichier livré). Ce qui se teste ici, c'est
# que le mécanisme EXISTE, qu'il est branché sur le relevé, et qu'aucun
# raccourci ne peut le rendre complaisant.

def _js() -> str:
    return JS.read_text(encoding="utf-8")


def _js_fn(src: str, nom: str) -> str:
    """Le SOURCE d'une fonction de `mod-type.js`, accolades équilibrées.
    Jumeau de l'outil du même nom de `test_cards_frame.py` : lire une fonction
    ENTIÈRE vaut mieux que chercher une ligne dans tout le fichier — « cette
    chaîne est quelque part » ne dit pas dans quelle fonction."""
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
    raise AssertionError("accolades non équilibrées pour " + nom)


def _js_sans_commentaires() -> str:
    """`mod-type.js` privé de ses commentaires.

    Les commentaires de ce fichier sont écrits en français : ils portent des
    apostrophes, et une apostrophe ressemble à une ouverture de chaîne. Un
    extracteur naïf lisait donc des PARAGRAPHES DE COMMENTAIRE comme du texte
    affiché — c'est ce qui rendait rouge le contrôle de vocabulaire, sur des
    phrases que personne ne voit jamais. On enlève les commentaires d'abord."""
    src = _js()
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"(?m)^\s*//.*$", " ", src)
    return src


def _textes_affiches() -> list[str]:
    """Les littéraux de chaîne du module, commentaires ôtés — c'est-à-dire ce
    qui peut arriver à l'écran."""
    src = _js_sans_commentaires()
    trouves = re.findall(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"", src)
    return [a or b for a, b in trouves]


def _js_presets() -> dict:
    """La table des gabarits telle que l'ÉCRAN la porte (bloc miroir extrait
    de `mod-type.js`), pour la comparer à celle du backend."""
    return json.loads(_bloc_js("PRESETS"))


def test_le_controle_est_photometrique_pas_seulement_geometrique():
    """MANQUE nº1 des deux critiques : « le contrôle teste la boîte du slot
    contre le rectangle de zone sûre, et jamais contre ce que les autres
    couches peignent au même endroit ». Un slot enseveli sous une bannière
    dessinée à un z supérieur était certifié « 0 hors zone sûre ».

    Le contrôle relit désormais LES OCTETS : l'encre de chaque slot est
    redessinée seule sur une toile de la même géométrie, et comparée au
    composite final rendu par `CF.renderCard`. Un pixel de CORPS de glyphe est
    opaque : sans occlusion le composite y vaut exactement la couleur de
    l'encre."""
    src = _js()
    assert "async function runAudit()" in src
    # il relit le composite RÉEL, pas une estimation
    assert re.search(r"await CF\.renderCard\(CF\.current\(\), \{ face: MEAS_SIDE \}\)", src)
    # il redessine l'encre du slot SEULE, ombre coupée (l'ombre est un halo)
    assert re.search(r"drawSlot\(sctx, solo, g, m\)", src)
    assert re.search(r"shadow: 0, shadow_dx: 0, shadow_dy: 0, opacity: 100", src)
    # le verdict vient d'une COMPARAISON DE PIXELS, pas d'un rectangle
    assert "Math.abs(F[i] - S[i]) <= AUDIT_TOL" in src
    assert re.search(r"rate: total \? vis / total : 1", src)
    # et il est branché sur le relevé : la ligne « Lisibilité » et les badges
    assert "Lisibilité (photométrique)" in src
    assert "% masqué" in src


def test_le_compteur_ne_dit_jamais_zero_avant_d_avoir_regarde():
    """« Un compteur qui ment est pire qu'une absence de compteur, parce qu'il
    éteint la vigilance. » Tant que le contrôle n'a pas relu le composite
    COURANT, la ligne dit « en cours », pas « 0 masqué » : `AUDIT.stamp` doit
    valoir `AUDIT_STAMP`, qui s'incrémente à CHAQUE passe du painter."""
    src = _js()
    assert "AUDIT_STAMP++" in src
    assert re.search(r"if \(!AUDIT \|\| AUDIT\.stamp !== AUDIT_STAMP\)", src)
    assert "contrôle photométrique en cours sur le composite" in src
    # auditOf() ne rend rien non plus quand le relevé est périmé
    assert re.search(r"function auditOf\(id\) \{\s*\n\s*if \(!AUDIT \|\| AUDIT\.stamp !== AUDIT_STAMP\) return null;", src)


def test_le_contraste_est_mesure_contre_le_fond_reellement_derriere():
    """MANQUE nº2 : « aucun contrôle de contraste ». Il est désormais calculé
    sur les octets du composite — luminance relative WCAG — entre l'encre qui
    survit et le fond ÉCHANTILLONNÉ AUTOUR DES GLYPHES (≤ 6 px), pas supposé.

    Et il tient compte du contour : un chiffre crème cerclé de noir se lit sur
    un fond crème. Mesurer seulement crème-contre-crème aurait condamné un
    texte parfaitement lisible — c'est le faux positif qui aurait fait
    désactiver le contrôle au bout d'une heure."""
    src = _js()
    assert "function lumOf(" in src and "0.2126" in src and "0.7152" in src and "0.0722" in src
    assert re.search(r"function wcag\(l1, l2\)", src)
    assert "const BG_NEAR = 6;" in src
    # le contour sert de RELAIS : encre contre contour, puis contour contre
    # fond — et c'est le maillon faible des deux qui compte
    assert "const legInk = wcag(iL, oL), legBg = wcag(oL, b);" in src
    assert "const relay = Math.min(legInk, legBg);" in src
    assert "if (relay > o.r)" in src
    # seuils WCAG appliqués à la taille PHYSIQUE, pas à des pixels d'écran
    assert re.search(r"function wcagSeuil\(pt, bold\) \{ return \(pt >= 18 \|\| \(bold && pt >= 14\)\) \? 3\.0 : 4\.5; \}", src)


def test_un_slot_vide_est_un_fait_pas_un_non_evenement():
    """MANQUE nº3 : « le slot Coût ne rend aucun glyphe, la sphère reste vide,
    et aucun compteur ne le mentionne ». Le painter sortait de la boucle sans
    laisser de trace. Il MESURE désormais le slot vide et le compte."""
    src = _js()
    # l'ancien raccourci a disparu
    assert 'if (!String(text).length) return;' not in src
    assert re.search(r"m\.empty = !String\(text\)\.length;", src)
    assert re.search(r"if \(!m\.empty\) drawSlot\(ctx, slot, geom, m\);", src)
    assert "slot configuré, aucun glyphe posé" in src
    assert '>vide</em>' in src


def test_la_marge_optique_existe_et_ne_s_applique_qu_aux_bords_de_zone_sure():
    """MANQUE nº4 : « l'encre s'arrête à 4 px du bord de zone sûre, soit
    0,339 mm — sous la dérive usuelle des repères de coupe ». La marge optique
    est retranchée de la boîte AVANT composition, mais SEULEMENT du côté qui
    touche la bordure de la zone sûre : l'appliquer aux quatre côtés de toutes
    les boîtes coûtait du corps à des slots posés au milieu de la carte."""
    src = _js()
    assert "const OPTICAL_MM_DEF = 0.5;" in src
    assert re.search(r"optical_mm: OPTICAL_MM_DEF", src)
    # ... et elle réserve de l'ENCRE, pas de la boîte : le demi-trait de
    # contour et le liséré d'anticrénelage se posent EN DEHORS du cadre
    # composé, donc ils sont retranchés en plus. Sans eux, une marge annoncée
    # à 0,50 mm laissait l'encre arriver à 0,34 mm du bord (mesuré dans l'app).
    assert "const AA_PX = 1;" in src
    assert "const base = optPx + grow + AA_PX;" in src
    assert "Math.max(bx0, sr[0] + padL)" in src and "Math.min(bx1, sr[0] + sr[2] - padR)" in src
    # un slot volontairement hors zone sûre n'est pas rapatrié
    assert "cx > sr[0] && cx < sr[0] + sr[2] && cy > sr[1] && cy < sr[1] + sr[3]" in src
    # le dégagement est MESURÉ et signalé sous le seuil — et le seuil comparé
    # est celui qui est RÉGLÉ à l'écran, pas la constante par défaut
    # (l'écran ne dit plus « zone sûre » — le vocabulaire du dossier a quitté
    #  le panneau au tour 5 — mais il dit toujours OÙ s'arrête l'encre.)
    assert "mm du bord du cadre de composition — sous la marge optique de " in src
    assert "tight: rows.filter((r) => optMm > 0 && nearestClearMm(r) != null" in src


def test_la_meme_grandeur_s_ecrit_partout_pareil():
    """MANQUE nº5 (défaut mesuré par le second critique) : « le pied de page dit
    corps 9,1 pt (38 px), le panneau dit 37,8 px ». Une seule fonction écrit
    désormais cette grandeur, et les deux endroits l'appellent."""
    src = _js()
    assert "function corps(m, g) {" in src
    assert src.count("corps(m, g)") + src.count("corps(hero.m, g)") >= 2
    # plus aucun arrondi à l'unité sur un corps en pixels
    assert 'fx(hero.m.sizePx, 0)' not in src
    # ET LES DEUX NOMBRES SE RETROUVENT L'UN L'AUTRE. Le corps affiché est
    # arrondi au dixième ; les pixels sont calculés SUR CET ARRONDI, sinon
    # « 9,2 pt (38,1 px) » se contredit dès qu'on refait 9,2 / 72 x 300 = 38,3.
    assert "const pt = Math.round(m.pt * 10) / 10;" in src
    assert 'fx(pt, 1) + " pt (" + fx(pxOfPt(pt, g || CF.geom()), 1) + " px)"' in src


def test_la_justification_et_la_cesure_existent_et_sont_mesurees():
    """MANQUE nº6 : « aucune césure ni justification : les 5 lignes sont en
    drapeau avec des fins de ligne très irrégulières ». `justify` est un
    alignement de plein droit (backend compris), la césure respecte le tiret
    conditionnel U+00AD et n'invente une coupe qu'entre deux consonnes
    encadrées de voyelles."""
    assert "justify" in TY.ALIGNS, TY.ALIGNS
    assert TY.norm_slot({"align": "justify"})["align"] == "justify"
    assert TY.norm_slot({"align": "nawak"})["align"] == "left"
    assert TY.SLOT_DEFAULTS["hyphen"] is False
    assert TY.norm_slot({"hyphen": 1})["hyphen"] is True
    src = _js()
    assert "function hyphenPoints(word)" in src and "DIGRAPHS" in src
    assert "function justifyGaps(line, extra)" in src
    # l'irrégularité des fins de ligne est un CHIFFRE affiché, pas un adjectif
    assert "ragged" in src and "d'irrégularité" in src
    # les encadrés livrés sont justifiés et coupés
    for pid, p in TY.PRESETS.items():
        for s in p["slots"]:
            if s["id"] == "rules":
                assert s["align"] == "justify", pid
                assert s["hyphen"] is True, pid


def test_la_cesure_ajoute_un_tiret_sans_fausser_l_invariant():
    """Piège de la césure : le tiret de coupe est un glyphe AJOUTÉ. Compté
    naïvement, il aurait rendu l'invariant « 0 caractère supprimé » négatif —
    ou pire, l'aurait masqué. Le recompte retire les tirets de fin de ligne
    AVANT de comparer, et il le fait sans `slice(0, n)` (le garde-fou du test
    précédent reste actif)."""
    src = _js()
    assert re.search(r'\? l\.replace\(/-\$/, ""\) : l\)\)\.join\(""\)', src)
    assert "const cut = Math.max(0, flat(text) - flat(posed));" in src


def test_le_controle_de_serie_existe_et_rend_l_etendue_des_corps():
    """MANQUE nº7 : « sur 200 cartes importées, les titres n'auront pas tous le
    même corps et rien ne le montrera au niveau du deck ». Le contrôle de série
    remet en page CHAQUE carte (sans dessiner) et rend l'étendue réelle."""
    src = _js()
    assert "function runSeries()" in src
    assert re.search(r"const list = cards\.length \? cards : \[CF\.card\(CF\.current\(\)\)\];", src)
    assert "au corps mini" in src and "cf-type-series" in src


def test_p3_ne_LIVRE_aucun_octet_d_image():
    """PRIORITÉ CLIENT « 300 DPI avec fond perdu et zone de sécurité ». Le
    chunk `pHYs` se pose sur le FICHIER LIVRÉ, et cette pièce n'en produit
    aucun : elle ne sait que poser du texte (et, depuis la 3b, l'image d'un
    calque) sur la toile du CORE. Aucun chemin d'EXPORT, ni à l'écran ni au
    backend — le vérifier ici évite qu'un deuxième chemin de livraison échappe
    à l'estampille de P7.

    CE QUE LA 3b-T2 A CHANGÉ, ET CE QUI N'A PAS BOUGÉ. La pièce RANGE
    désormais des octets : une image importée par l'utilisateur, écrite dans le
    dossier du deck et resservie telle quelle (`img_{n}.png`). C'est un ASSET
    D'ENTRÉE, l'exact contraire d'une livraison — il ENTRE, il ne sort pas, et
    il ne porte aucune estampille de fabrication. La ligne rouge est donc
    déplacée là où elle veut dire quelque chose : **P3 n'ENCODE aucune image de
    CARTE et n'en livre aucune**. Le seul encodage d'écran reste celui de la
    mesure (`asFile`) plus celui de la réduction avant import ; aucun des deux
    ne devient un fichier remis à l'utilisateur."""
    src = _js()
    # AUCUN CHEMIN DE LIVRAISON. Ce sont ces noms-là qui font sortir un octet
    # du module vers l'utilisateur : un lien de téléchargement, une URL
    # d'objet, une image en base64. Aucun n'est ici.
    for interdit in ("toDataURL", "M.download", "CF.download", "createObjectURL",
                     "URL.createObjectURL", "image/jpeg", "<a download"):
        assert interdit not in src, f"P3 livre un fichier image : {interdit}"
    # DEUX ENCODAGES, ET AUCUN N'EST UNE LIVRAISON.
    #   1. `asFile` : le contrôle photométrique et le contrôle de définition
    #      n'ont pas le droit de mesurer une TOILE — leurs chiffres doivent
    #      sortir d'octets PNG, sinon « relu sur le fichier » est un mot. Le
    #      blob est décodé sur place et jeté.
    #   2. `downscaleImg` : la réduction d'une image AVANT son envoi à la route
    #      d'import. Le blob part au backend de la pièce, et nulle part ailleurs.
    assert src.count("toBlob") == 2, "un troisième chemin d'encodage est apparu"
    assert src.count('"image/png"') == 2
    i = src.index("async function asFile(cv)")
    j = src.index("async function runAudit()")
    assert i < src.index("cv.toBlob(", i) < j, "le toBlob de mesure n'est plus dans asFile"
    k = src.index("function downscaleImg(")
    assert k < src.index("cv.toBlob(", k) < src.index("\n  async function importImage("), \
        "le toBlob de réduction a déménagé hors de downscaleImg"
    # le blob de MESURE n'est jamais téléversé : le seul envoi d'octets est
    # l'import de calque, et il est nommé.
    assert "M.api.post(\"layout\"" in src
    for appel in ("M.api.post(\"png", "M.api.blob(", "FormData"):
        assert appel not in src, f"le blob de mesure part au backend : {appel}"
    assert src.count("M.api.raw(") == 1, "un second envoi d'octets est apparu"
    assert 'M.api.raw("POST", "image"' in src
    py = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    # LE BACKEND NE FABRIQUE TOUJOURS RIEN : pas de rendu, pas d'estampille de
    # définition, pas de flux. Il DÉCODE une image reçue pour la borner (PIL,
    # importé dans la fonction, comme P6) et la réécrit en PNG — c'est du
    # rangement, pas de la fabrication.
    for interdit in ("StreamingResponse", "pHYs", "ImageDraw", "ImageFont"):
        assert interdit not in py, f"cards/type.py fabrique un fichier : {interdit}"
    # `FileResponse` reste interdit — pas le MOT (la docstring de la route dit
    # justement pourquoi on ne s'en sert pas), mais la CHOSE : ni import, ni
    # appel. Il re-stat le fichier au moment de l'envoi, donc APRÈS le
    # contrôle, ce qui y lève RuntimeError sur une suppression concurrente —
    # un 500 sur une pièce qui n'en fait jamais (patron `get_node_file`, 2c).
    assert "fastapi.responses" not in py
    assert "FileResponse(" not in py
    assert py.count("from PIL import Image") == 1, \
        "le décodage d'image s'est répandu dans le module"


def test_la_feuille_de_style_ne_deborde_pas_de_la_piece():
    """Règle 4, vérifiée aussi ici : une pièce qui repeint les sept autres est
    invisible en test unitaire et catastrophique à l'écran."""
    css = CSS.read_text(encoding="utf-8")
    sans_commentaires = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for bloc in re.finditer(r"([^{}]+)\{", sans_commentaires):
        sel = " ".join(bloc.group(1).split())
        if sel.startswith("@"):
            continue
        for un in sel.split(","):
            un = un.strip()
            if un:
                assert ".cf-type" in un, f"sélecteur hors pièce : {un!r}"


# ════════ 8. LE MOTEUR, EXÉCUTÉ — pas relu ══════════════════════════════════
# Les tests ci-dessus lisent le code ; ceux-ci le FONT TOURNER. Un banc d'essai
# node charge `mod-type.js` avec un `window.CF` de paille et appelle SON painter
# z=60 avec un contexte 2D qui NOTE CHAQUE APPEL DE DESSIN. On mesure ensuite ce
# qui a réellement été posé : les caractères, les blancs, les lignes. Rien n'est
# réimplémenté — une réimplémentation aurait prouvé la réimplémentation.
#
# La métrique de police est déterministe (table de chasses), pas celle de
# Chrome : ce qu'on vérifie n'est pas la largeur d'un « m » d'IBM Plex, c'est le
# COMPORTEMENT du moteur — combien de caractères il pose, comment il répartit
# les blancs, ce qu'il fait d'une dernière ligne trop courte.

BANC = r"""
import { readFileSync } from "node:fs";
let SRC = readFileSync(process.argv[2], "utf8");
const OPT = JSON.parse(process.argv[3] ? readFileSync(process.argv[3], "utf8") : "{}");

const W = { " ": 0.26, "i": 0.28, "l": 0.28, "j": 0.28, "t": 0.34, "f": 0.34, "r": 0.36,
  ".": 0.28, ",": 0.28, "'": 0.2, "’": 0.2, "-": 0.33, "m": 0.85, "w": 0.75,
  "M": 0.9, "W": 0.95 };
const wOf = (ch) => (W[ch] !== undefined ? W[ch] : (ch >= "A" && ch <= "Z" ? 0.62 : 0.5));
const draws = [];
function ctx2d() {
  let size = 10;
  const c = {
    _font: "", save() { }, restore() { }, translate() { }, rotate() { },
    clearRect() { }, setTransform() { },
    measureText(s) {
      let w = 0;
      for (const ch of String(s)) w += wOf(ch) * size;
      return { width: w, actualBoundingBoxAscent: size * 0.72,
        actualBoundingBoxDescent: size * 0.21 };
    },
    fillText(t, x, y) { draws.push({ t: String(t), x: x, y: y, mode: "fill", s: size }); },
    strokeText(t, x, y) { draws.push({ t: String(t), x: x, y: y, mode: "stroke", s: size }); },
  };
  Object.defineProperty(c, "font", { get() { return c._font; },
    set(v) { c._font = v; const m = /([\d.]+)px/.exec(v); if (m) size = parseFloat(m[1]); } });
  return c;
}
function geom(fmt_mm, dpi, bleed_mm, safe_mm) {
  const R = (x) => Math.floor(Number(x.toFixed(9)) + 0.5);
  const px = (mm) => R(mm / 25.4 * dpi);
  const canvas_px = [px(fmt_mm[0] + 2 * bleed_mm), px(fmt_mm[1] + 2 * bleed_mm)];
  const trim_px = [px(fmt_mm[0]), px(fmt_mm[1])];
  const bleed_off_px = [(canvas_px[0] - trim_px[0]) / 2, (canvas_px[1] - trim_px[1]) / 2];
  const safe_px = [px(fmt_mm[0] - 2 * safe_mm), px(fmt_mm[1] - 2 * safe_mm)];
  const safe_off_px = [bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2,
    bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2];
  return { fmt: "poker_eu", label: "Poker", dpi: dpi, canvas_px, trim_px, bleed_off_px,
    safe_px, safe_off_px, bleed_mm, safe_mm, mm2px: (v) => v / 25.4 * dpi,
    px2mm: (v) => v * 25.4 / dpi };
}
const G = geom([63, 88], 300, 3, 3);
const DOC = { type: { optical_mm: OPT.optical_mm === undefined ? 0.5 : OPT.optical_mm } };
let MOD = null;
const CF = {
  register(cfg) {
    MOD = cfg;
    return { patch: (p) => Object.assign(DOC.type, p),
      api: { get: async () => ({}), post: async () => ({}) },
      emit() { }, slot() { }, aside() { }, invalidate() { }, toast() { }, busy() { }, on() { } };
  },
  get(path, def) {
    let v = DOC;
    for (const p of String(path).split(".")) { if (v == null) return def; v = v[p]; }
    return v === undefined ? def : v;
  },
  geom: () => G, current: () => 0, cards: () => [], card: () => ({ fields: {} }),
  on() { }, renderCard: async () => null, modules: () => [],
};
globalThis.window = { CF: CF, addEventListener() { } };
globalThis.document = {
  createElement: () => ({ width: 0, height: 0, getContext: () => ctx2d(), style: {},
    appendChild() { }, addEventListener() { }, remove() { }, querySelector: () => null,
    querySelectorAll: () => [],
    classList: { add() { }, remove() { }, toggle() { }, contains: () => false } }),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() { },
  body: { appendChild() { } }, fonts: { add() { } },
};
const boom = [];
process.on("uncaughtException", (e) => { boom.push(String((e && e.message) || e)); });
(0, eval)(SRC);
const base = Object.assign({
  id: "rules", label: "Encadre", on: true, side: "front", box: [4.5, 55, 54, 18],
  font: "IBMPlexSans", size_pt: 8, min_pt: 4.5, color: "#efe7d6",
  align: "justify", valign: "top", track: 0, leading: 1.22, hyphen: true,
  caps: "none", bold: false, italic: false, outline: 0, outline_color: "#0a0a0c",
  shadow: 0, shadow_color: "#000000", shadow_dx: 0, shadow_dy: 0,
  rotate: 0, arc: 0, autofit: true, wrap: true, opacity: 100,
  just_max: 133, last_pct: 25, text: "",
}, OPT.slot || {});
if (OPT.sans_reglages_neufs) { delete base.just_max; delete base.last_pct; }
const painter = MOD.painters.filter((p) => p.z === 60)[0];
await painter.fn(ctx2d(), G, { type: { slots: [base] } }, { fields: {} }, "front");
await new Promise((r) => setTimeout(r, 200));
const byY = {};
draws.filter((d) => d.mode === "fill").forEach((d) => {
  (byY[d.y.toFixed(2)] = byY[d.y.toFixed(2)] || []).push(d);
});
const lignes = Object.keys(byY).map(Number).sort((a, b) => a - b).map((y) => {
  const g = byY[y.toFixed(2)].slice().sort((a, b) => a.x - b.x);
  const mots = [], lettres = [];
  const size = g[0].s;
  for (let i = 1; i < g.length; i++) {
    if (g[i - 1].t === " ") mots.push(g[i].x - g[i - 1].x);
    else lettres.push(g[i].x - g[i - 1].x - wOf(g[i - 1].t) * size);
  }
  const moy = (a) => (a.length ? a.reduce((p, q) => p + q, 0) / a.length : null);
  const som = (s) => Array.from(s).reduce((a, ch) => a + wOf(ch) * size, 0);
  /* une ligne sans blanc etire ni interlettrage est dessinee EN UN SEUL appel :
     sa largeur ne se lit pas dans les abscisses, elle se mesure. */
  const larg = (g.length > 1)
    ? (g[g.length - 1].x - g[0].x) + wOf(g[g.length - 1].t) * size
    : som(g[0].t);
  return { texte: g.map((d) => d.t).join(""), size: size, nat: wOf(" ") * size,
    mots: mots, x0: g[0].x, x1: g[g.length - 1].x, larg: larg, inter: moy(lettres) };
});
const flat = (s) => Array.from(String(s).split("­").join("").replace(/\s+/g, "")).length;
const posePlat = flat(lignes.map((l) => l.texte.replace(/-$/, "")).join(""));
const tous = [].concat.apply([], lignes.map((l) => l.mots));
const nat = lignes.length ? lignes[0].nat : 0;
process.stdout.write(JSON.stringify({
  n_lignes: lignes.length, corps_px: lignes.length ? lignes[0].size : null,
  espace_naturel: nat,
  lignes: lignes.map((l) => ({ texte: l.texte, mots: l.mots.length,
    blanc_max: l.mots.length ? Math.max.apply(null, l.mots) : null,
    /* l'abscisse du PREMIER glyphe posé : c'est elle qui dit où le moteur a
       calé sa composition, donc ce que la marge optique a réservé. */
    x0: l.x0, x1: l.x1,
    largeur: l.larg, inter: l.inter })),
  car_source: flat(base.text), car_pose: posePlat, perdus: flat(base.text) - posePlat,
  etirement_max: (tous.length && nat) ? Math.max.apply(null, tous) / nat : null,
  exceptions: boom,
}));
"""

# le texte de démonstration : c'est celui du gabarit, donc le cas difficile
RULES_TXT = TY.PRESETS["champion"]["slots"][3]["text"]
TITRE_TXT = TY.PRESETS["champion"]["slots"][1]["text"]
FLAVOR_TXT = TY.PRESETS["champion"]["slots"][4]["text"]   # noqa: F841  (gardé : lisible dans les rapports)


def _banc(tmp_path, opts: dict, mutations=()) -> dict:
    """Fait tourner le moteur de `mod-type.js` et rend ce qu'il a DESSINÉ.

    `mutations` retire des protections du source avant exécution : un test qui
    passerait aussi sur le code cassé ne prouverait rien."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'essai du moteur ne peut pas tourner")
    src = JS.read_text(encoding="utf-8", newline="")   # newline='' : CRLF gardé
    for avant, apres in mutations:
        assert avant in src, f"mutation introuvable : {avant!r}"
        src = src.replace(avant, apres)
    js = tmp_path / "mod-type-sous-test.js"
    js.write_text(src, encoding="utf-8", newline="")
    banc = tmp_path / "banc.mjs"
    banc.write_text(BANC, encoding="utf-8")
    conf = tmp_path / "opts.json"
    conf.write_text(json.dumps(opts, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_le_releve_ne_leve_plus_quand_le_painter_rend_avant_le_panneau(tmp_path):
    """RÉGRESSION relevée par la vérification d'intégration : « Uncaught
    TypeError: Cannot read properties of null (reading 'querySelector') » à
    CHAQUE ouverture de l'onglet Cartes, 3 rechargements sur 3.

    Le CORE compose la carte dès qu'un module s'enregistre ; `init(host)`
    n'arrive qu'au premier affichage du panneau. Le painter demandait pourtant
    un relevé 30 ms plus tard et `renderList` déréférençait un HOST encore nul.

    Ici le banc appelle le painter SANS jamais appeler `init` — exactement la
    séquence du bug — et attend que le relevé différé se déclenche."""
    d = _banc(tmp_path, {"slot": {"text": RULES_TXT}})
    assert d["exceptions"] == [], d["exceptions"]
    assert d["n_lignes"] >= 5, d          # et il a quand même dessiné

    # ... et le banc VOIT le défaut quand on retire les deux gardes : sans
    # cette contre-épreuve, le test passerait aussi sur le code cassé.
    casse = _banc(tmp_path, {"slot": {"text": RULES_TXT}}, mutations=(
        ("      if (!HOST) return;\r\n      checkPending();",
         "      checkPending();"),
        ('const wrap = HOST && HOST.querySelector(".cf-type-list");',
         'const wrap = HOST.querySelector(".cf-type-list");'),
    ))
    assert casse["exceptions"], "le banc ne voit plus le défaut qu'il doit voir"
    assert "querySelector" in casse["exceptions"][0], casse["exceptions"]


def test_zero_caractere_perdu_mesure_sur_ce_qui_est_dessine(tmp_path):
    """Le seuil central de la pièce, vérifié SUR LE DESSIN et plus seulement
    sur une lecture du code : on recolle tous les appels de dessin et on
    recompte les glyphes. Le titre de 44 caractères, l'encadré de 424, et un
    mot plus long que sa boîte — aucun ne perd un caractère."""
    for nom, slot in (
        ("encadré 424", {"text": RULES_TXT}),
        ("titre 44", {"text": TITRE_TXT, "box": [4.5, 3.5, 45, 9], "size_pt": 14,
                      "min_pt": 6.5, "align": "center", "caps": "upper"}),
        ("mot géant", {"text": "Anticonstitutionnellement", "box": [5, 55, 12, 10],
                       "size_pt": 9, "min_pt": 9, "autofit": False, "align": "left"}),
    ):
        d = _banc(tmp_path, {"slot": slot})
        assert d["exceptions"] == [], (nom, d["exceptions"])
        assert d["perdus"] == 0, (nom, d["car_source"], d["car_pose"])
        assert d["car_pose"] > 0, nom
    # et le compte de référence est bien celui de la spec
    assert len(TITRE_TXT) == TITRE_LONG_CAR
    assert len(RULES_TXT) >= REGLES_CAR_MIN


def test_les_blancs_justifies_sont_plafonnes(tmp_path):
    """DÉFAUT nommé par le premier critique : « justification sans plafond
    d'élasticité — les blancs vont de 6 px à 16 px selon la ligne (rapport
    2,67). Le produit se félicite de fins de ligne à 0 % d'irrégularité, mais
    il mesure le seul bord droit, jamais l'irrégularité des blancs internes —
    c'est-à-dire précisément le défaut que produit une justification. »

    Le plafond est mesuré SUR LES COORDONNÉES DE DESSIN : l'avance réellement
    posée d'un blanc, interlettrage compris — c'est ce qu'un re-mesurage
    trouve sur le bitmap, donc c'est ce qui doit tenir."""
    libre = _banc(tmp_path, {"slot": {"text": RULES_TXT, "just_max": 400}})
    tenu = _banc(tmp_path, {"slot": {"text": RULES_TXT, "just_max": 133}})
    assert libre["etirement_max"] > 2.0, libre["etirement_max"]
    assert tenu["etirement_max"] <= 1.335, tenu["etirement_max"]
    # le plafond ne coûte NI un caractère NI une ligne : il déplace le
    # supplément dans l'interlettrage, il ne recompose pas le paragraphe
    assert tenu["perdus"] == 0 and libre["perdus"] == 0
    assert tenu["n_lignes"] == libre["n_lignes"]
    assert [l["texte"] for l in tenu["lignes"]] == [l["texte"] for l in libre["lignes"]]
    # ... et les lignes rattrapées portent bien de l'interlettrage
    rattrapees = [l for l in tenu["lignes"] if (l["inter"] or 0) > 0.01]
    assert rattrapees, tenu["lignes"]
    assert all((l["inter"] or 0) < 2.0 for l in rattrapees), rattrapees


def test_la_derniere_ligne_trop_courte_est_rattrapee(tmp_path):
    """DÉFAUT nommé par le premier critique : « aucun contrôle de veuve ni
    d'orpheline. La dernière ligne du texte d'ambiance ne porte que "jours. »"
    […] Aucun réglage des 17 ne permet d'interdire ça. »

    C'est désormais un réglage (`last_pct`, en % de la justification, 25 % par
    défaut — la règle classique du quart), et il agit : le mot resté seul est
    rejoint par le dernier mot de la ligne précédente. Sans perdre un
    caractère, et sans jamais couper.

    CE TEST POSSÈDE SON ENTRÉE. Il l'a d'abord empruntée au texte d'ambiance du
    gabarit livré ; changer cette copie — pour la rendre neutre, par exemple —
    faisait alors tomber le texte sur UNE ligne et le cas de veuve disparaissait,
    donnant l'illusion d'une régression du contrôle de veuve alors que seule la
    largeur des glyphes avait bougé. Une preuve de comportement ne doit pas
    dépendre de la copie qu'on expédie aux utilisateurs : la chaîne ci-dessous
    est celle qui reproduisait le défaut d'origine, figée ici pour de bon."""
    orpheline = "« Il compte les marées comme d'autres comptent les jours. »"
    boite = {"box": [5.28, 70.73, 52.41, 4.51], "size_pt": 7, "min_pt": 4.5,
             "align": "center", "valign": "middle", "hyphen": False}
    sans = _banc(tmp_path, {"slot": dict(boite, text=orpheline, last_pct=0)})
    avec = _banc(tmp_path, {"slot": dict(boite, text=orpheline, last_pct=25)})
    assert sans["n_lignes"] == avec["n_lignes"] >= 2
    # sans contrôle, la dernière ligne est un moignon ; avec, elle ne l'est plus
    court = sans["lignes"][-1]["largeur"]
    long_ = avec["lignes"][-1]["largeur"]
    assert long_ > court * 3, (court, long_)
    # sans contrôle : un seul mot survit sur la dernière ligne. Avec : plusieurs.
    assert len(sans["lignes"][-1]["texte"].split()) == 1, sans["lignes"]
    assert len(avec["lignes"][-1]["texte"].split()) >= 2, avec["lignes"]
    assert sans["perdus"] == 0 and avec["perdus"] == 0
    # le texte reste le même, mot pour mot : on n'a rien coupé, rien inventé
    assert ("".join(l["texte"] for l in sans["lignes"]).replace(" ", "")
            == "".join(l["texte"] for l in avec["lignes"]).replace(" ", ""))


def test_un_document_enregistre_avant_ces_reglages_se_compose_encore(tmp_path):
    """Le piège des réglages neufs : un jeu enregistré AVANT eux n'a ni
    `just_max` ni `last_pct`, et `undefined / 100` vaut NaN — c'est-à-dire une
    carte VIDE, sans un message. Les deux valeurs sont relues à travers les
    mêmes bornes que la normalisation ; un défaut manquant vaut le défaut."""
    d = _banc(tmp_path, {"slot": {"text": RULES_TXT}, "sans_reglages_neufs": True})
    assert d["exceptions"] == [], d["exceptions"]
    assert d["perdus"] == 0 and d["n_lignes"] >= 5, d
    assert d["etirement_max"] <= 1.335, d["etirement_max"]      # le défaut s'applique


# ════════ 9. LES CHIFFRES AFFICHÉS SE PROUVENT SUR LES OCTETS ═══════════════

def test_le_pave_annonce_est_l_encre_ENTIERE(tmp_path=None):
    """DÉFAUT nommé par le premier critique : « le pavé de règles est annoncé à
    645 x 188 px, je le mesure à 647 x 193 (bbox d'encre, accents et jambages
    compris) […] le chiffre affiché mesure la boîte théorique, pas l'encre
    réelle — un typographe mesure l'encre. »

    La cause était que la boîte d'encre ne comptait que les pixels PLEINS
    (alpha ≥ 250) : le liséré d'anticrénelage, qui est de l'encre pour
    l'imprimeur, en était exclu. Elle compte désormais TOUTE couverture, et le
    corps plein reste réservé au masquage et au contraste (lui seul permet
    d'affirmer une couleur). Contrôlé dans l'app : 649 x 194 px annoncés,
    649 x 194 px mesurés par soustraction de deux rendus."""
    src = _js()
    # la bbox balaie toute couverture...
    assert re.search(r"for \(let p = 0; p < n; p\+\+\) \{\s*\r?\n\s*if \(!A\[p\]\) continue;", src)
    # ... et le corps plein reste le seul juge du masquage
    assert "if (A[p] !== 2) continue;" in src
    assert "anticrénelage compris" in src
    # l'ombre portée est mesurée À PART : un re-mesurage par soustraction la
    # trouve, et la taire ferait passer le pavé annoncé pour trop petit
    assert "halo_px: halo" in src and "halo d'ombre" in src
    # et si la fenêtre de lecture rogne l'encre, le chiffre le dit
    assert "const clipped = inkRect != null" in src
    assert re.search(r'au\.clipped \? "≥ "', src)


def test_le_contraste_affiche_se_recalcule_a_la_main():
    """DÉFAUT nommé par le second critique : « le chiffre de lisibilité affiché
    (contraste le plus bas 4,29:1) ne correspond à aucune lecture WCAG directe
    des deux couleurs […] le calcul est plus sévère que la norme mais il est
    non documenté dans le panneau, donc invérifiable par un imprimeur qui
    recompterait. »

    Trois corrections : le chiffre NOMME son slot, son corps et son seuil ; il
    est suivi de la DIVISION qui le produit ; et quand c'est le contour qui
    fait le relais, c'est la division du CONTOUR qui est écrite — sinon le
    lecteur refait le calcul sur l'encre et trouve autre chose.

    Ici on refait justement le calcul, en Python, sur les luminances relevées
    dans l'app : « Attaque » à 19 pt, relais par le contour."""
    src = _js()
    assert "function contrastCalc(r)" in src
    assert "c'est le contour qui fait le relais" in src
    assert "lum_a: lumA, lum_b: lumB, via: via" in src
    # le slot est nommé à côté du chiffre, avec son corps et son seuil
    assert 'contraste le plus bas " + fx(wr.contrast_min, 2) + ":1 — « " + esc(wr.label)' in src
    assert "seuil AA " in src
    # la convention est écrite dans le panneau, pas seulement dans le code
    assert "Conventions de mesure" in src and "5<sup>e</sup> centile" in src

    def contraste(l1, l2):
        a, b = max(l1, l2), min(l1, l2)
        return (a + 0.05) / (b + 0.05)
    # relevé dans l'app sur « Attaque » : L encre 0,8064 · L contour 0,0068 ·
    # L fond 0,1872 -> le chemin direct donne 3,61 et le relais 4,18. C'est
    # 4,18 qui est affiché, et c'est la division du relais qui est écrite.
    assert round(contraste(0.8064, 0.1872), 2) == 3.61
    assert round(contraste(0.1872, 0.0068), 2) == 4.18
    assert round(min(contraste(0.8064, 0.0068), contraste(0.0068, 0.1872)), 2) == 4.18


def test_les_deux_nouveaux_reglages_sont_bornes_des_deux_cotes():
    """Un plafond d'élasticité sous 100 % RÉTRÉCIRAIT les blancs — les mots se
    colleraient. Une dernière ligne exigée à 95 % de la justification serait
    impossible à satisfaire. Les deux bornes sont donc dans la normalisation,
    des deux côtés, et un corps mal formé retombe sur le défaut."""
    assert TY.SLOT_DEFAULTS["just_max"] == 133.0
    assert TY.SLOT_DEFAULTS["last_pct"] == 25.0
    assert TY.norm_slot({"just_max": 10})["just_max"] == TY.JUST_MAX_MIN == 100.0
    assert TY.norm_slot({"just_max": 9999})["just_max"] == TY.JUST_MAX_MAX == 400.0
    assert TY.norm_slot({"just_max": "beaucoup"})["just_max"] == 133.0
    assert TY.norm_slot({"last_pct": -5})["last_pct"] == 0.0
    assert TY.norm_slot({"last_pct": 500})["last_pct"] == TY.LAST_PCT_MAX == 80.0
    assert TY.norm_slot({"last_pct": None})["last_pct"] == 25.0
    # et le contrat sortant les porte, pour P4 et P7
    g = CT.geom("poker_eu", 300)
    for s in TY.preset_slots("champion", g):
        assert isinstance(s["just_max"], float) and isinstance(s["last_pct"], float)


def test_le_pied_de_carte_est_symetrique():
    """DÉFAUT nommé par le premier critique : « asymétrie non expliquée dans le
    pied de carte : le numéro est fer à gauche dans sa boîte tandis que le
    crédit d'illustration est fer à droite dans la sienne, pour deux boîtes de
    même facture posées côte à côte. »

    Les deux boîtes sont maintenant le miroir exact l'une de l'autre autour de
    l'axe de la zone sûre : les deux alignements se tournent alors le dos vers
    l'extérieur, ce qui est la disposition du métier — et l'asymétrie apparente
    devient une symétrie qui se mesure."""
    slots = {s["id"]: s for s in TY.PRESETS["champion"]["slots"]}
    num, art = slots["num"]["rel"], slots["artist"]["rel"]
    assert num[2] == art[2], "largeurs différentes"
    assert num[1] == art[1] and num[3] == art[3], "hauteurs ou ordonnées différentes"
    assert abs((num[0] + num[2]) - (1.0 - art[0])) < 1e-9, (num, art)
    assert abs((art[0] + art[2]) - (1.0 - num[0])) < 1e-9, (num, art)
    assert slots["num"]["align"] == "left" and slots["artist"]["align"] == "right"


def test_les_credits_passent_le_seuil_aa_sur_le_fond_qu_ils_ont():
    """DÉFAUT nommé par le premier critique : « le crédit d'illustration est à
    4,28:1 de contraste. C'est SOUS le seuil WCAG AA de 4,5:1 pour du texte
    courant, et à 5 pt ce n'est en aucun cas du grand texte. »

    Mesuré dans l'app sur le composite : le fond le plus clair AU CONTACT des
    glyphes du pied de carte vaut L = 0,0504 (bande du cadre, stable d'un
    tirage à l'autre — trois chargements, trois illustrations différentes,
    même bande). L'ancienne couleur #a89b83 (L 0,3341) y donnait 3,83:1. La
    couleur du gabarit doit tenir 4,5:1 contre ce fond-là."""
    def lum(hexa: str) -> float:
        def c(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, v, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * c(r) + 0.7152 * c(v) + 0.0722 * c(b)
    FOND_MESURE = 0.0504
    for sid in ("num", "artist"):
        s = [x for x in TY.PRESETS["champion"]["slots"] if x["id"] == sid][0]
        rapport = (lum(s["color"]) + 0.05) / (FOND_MESURE + 0.05)
        assert rapport >= 4.5, f"{sid} : {rapport:.2f}:1 contre le fond mesuré"
        assert s["size_pt"] < 18, "à ce corps le seuil AA est bien 4,5:1"
    # l'ancienne couleur, elle, échouait : le test dit ce qu'il a corrigé
    assert (lum("#a89b83") + 0.05) / (FOND_MESURE + 0.05) < 4.5


def test_le_releve_dit_ce_qu_il_mesure_et_pas_ce_qui_l_arrange():
    """« Fins de ligne à 0 % d'irrégularité » est vrai et ne dit rien : c'est le
    bord où une justification est bonne PAR CONSTRUCTION. Le relevé porte
    désormais, à côté, ce que la justification coûte vraiment — les blancs
    posés, leur étirement, le plafond, les lignes rattrapées — et la longueur
    de la dernière ligne."""
    src = _js()
    assert "function justInfo(m)" in src
    assert "blancs-mots " in src and "étirement max " in src and "plafond " in src
    assert "ligne(s) rattrapée(s) par l'interlettrage" in src
    assert "dernière ligne " in src and "% de la justification" in src
    assert "(bord droit)" in src, "l'irrégularité doit dire de quel bord elle parle"
    # le corps le plus petit RÉELLEMENT posé est au relevé : c'est lui qui
    # décide si la carte se lit une fois imprimée
    assert "corps le plus petit " in src
    # et le relevé du paragraphe est aussi sous les réglages qui le produisent
    assert "cf-type-bpx\">' + justInfo(m)" in src


# ══════ 10. TOUR 2 — « ça tient » n'est pas « ça se lit », et tout chiffre
#             affiché se refait à la main sur les octets ═══════════════════════

def test_le_plancher_de_lisibilite_existe_et_porte_les_fourchettes_du_metier():
    """DÉFAUT nommé aux deux tours : « pour faire tenir le titre de référence de
    44 caractères, il descend le corps à 9 pt, sous la fourchette de 12 à 20 pt
    que le dossier fixe pour un titre […] le badge vert "ajusté" certifie donc
    un pavé conforme géométriquement et trop petit typographiquement […] il
    manque un plancher de corps PAR NATURE DE BLOC, avec alerte quand
    l'ajustement automatique passe dessous. »

    `min_pt` était un plancher d'ENCOMBREMENT ; `read_pt` est celui du MÉTIER.
    Les deux existent, ils ne veulent pas dire la même chose, et le second
    porte les bas de fourchette du dossier : titre 12 pt, encadré 6, crédits 4.
    """
    assert "read_pt" in TY.SLOT_DEFAULTS and TY.SLOT_DEFAULTS["read_pt"] == 0.0
    # borné des deux côtés, et jamais NaN sur un corps mal formé
    assert TY.norm_slot({"read_pt": -3})["read_pt"] == TY.READ_PT_MIN == 0.0
    assert TY.norm_slot({"read_pt": 1e9})["read_pt"] == TY.READ_PT_MAX == 400.0
    assert TY.norm_slot({"read_pt": "grand"})["read_pt"] == 0.0
    assert TY.norm_slot({})["read_pt"] == 0.0
    # il n'est PAS rabattu sous `size_pt` : « ce bloc est déjà trop petit » est
    # une information juste, pas une saisie à corriger en silence
    assert TY.norm_slot({"size_pt": 5, "read_pt": 12})["read_pt"] == 12.0
    assert TY.norm_slot({"size_pt": 5, "min_pt": 12})["min_pt"] == 5.0

    attendu = {"title": 12.0, "name": 12.0, "typeline": 6.0, "rules": 6.0,
               "flavor": 6.0, "arcnum": 6.0, "cost": 8.0, "atk": 8.0,
               "def": 8.0, "num": 4.0, "artist": 4.0}
    assert TY.READ_FLOOR_PT == attendu
    g = CT.geom("poker_eu", 300)
    for pid in TY.PRESETS:
        for s in TY.preset_slots(pid, g):
            assert s["read_pt"] == attendu[s["id"]], (pid, s["id"], s["read_pt"])
            assert s["read_pt"] > 0, "un gabarit livré sans plancher ne dit rien"


def test_le_backend_juge_le_plancher_avec_le_corps_REELLEMENT_COMPOSE():
    """Le backend n'a pas les polices : il ne peut pas recalculer le corps posé
    (un second moteur de texte ferait diverger l'écran et le fichier — risque 2
    de la spec). Il reçoit donc `posed`, le corps que le navigateur a VRAIMENT
    composé, et applique la MÊME règle de plancher. Deux verdicts sur la même
    grandeur : un désaccord serait visible au lieu de rester dans l'écran.

    Relevé dans l'app sur le gabarit « Champion » à 300 DPI : titre 9 pt pour un
    plancher de 12, encadré 5,5 pour 6, ambiance 5,9 pour 6 — trois blocs, et le
    bandeau du panneau affiche bien « contrôlé par le backend : 0 hors zone
    sûre, 3 sous le plancher de lisibilité »."""
    did = _did()
    g = CT.geom("poker_eu", 300)
    slots = TY.preset_slots("champion", g)
    corps = {"title": 9.0, "rules": 5.5, "flavor": 5.9}

    r = _api("POST", f"/api/cards/{did}/type/layout",
             json={"fmt": "poker_eu", "dpi": 300, "slots": slots, "posed": corps})
    assert r.status_code == 200, r.text
    d = r.json()
    rows = {x["id"]: x for x in d["slots"]}
    assert d["summary"]["under_read"] == ["title", "rules", "flavor"]
    assert d["summary"]["ok"] is True, "le plancher n'est PAS un défaut de zone sûre"
    assert rows["title"]["posed_pt"] == 9.0 and rows["title"]["read_pt"] == 12.0
    assert rows["title"]["under_read"] is True
    assert rows["rules"]["under_read"] is True and rows["flavor"]["under_read"] is True
    assert rows["atk"]["under_read"] is None, "sans corps composé, aucun verdict inventé"
    # le plancher en pixels de toile, à la définition demandée
    assert rows["title"]["read_px"] == TY.rnd(12.0 / 72.0 * 300, 2) == 50.0

    # LA COMPARAISON SE FAIT A LA PRECISION AFFICHEE, au dixieme de point. La
    # dichotomie s'arrete a 11,99 pt quand on visait 12 : juge au centieme, le
    # badge ecrivait « 12 < 12 pt » — releve tel quel dans le lab. Une phrase
    # fausse a l'oeil et vraie au centieme reste invendable.
    for pose in (12.0, 11.99, 11.96, 11.951):
        r2 = _api("POST", f"/api/cards/{did}/type/layout",
                  json={"fmt": "poker_eu", "dpi": 300, "slots": slots,
                        "posed": {"title": pose}})
        assert r2.json()["summary"]["under_read"] == [], pose
    for pose in (11.94, 11.9, 9.0):
        r2 = _api("POST", f"/api/cards/{did}/type/layout",
                  json={"fmt": "poker_eu", "dpi": 300, "slots": slots,
                        "posed": {"title": pose}})
        assert r2.json()["summary"]["under_read"] == ["title"], pose
    # et un corps mal formé ne fait ni 500 ni verdict
    r3 = _api("POST", f"/api/cards/{did}/type/layout",
              json={"fmt": "poker_eu", "dpi": 300, "slots": slots,
                    "posed": {"title": "petit", "rules": None, "flavor": []}})
    assert r3.status_code == 200
    assert r3.json()["summary"]["under_read"] == []


def test_le_badge_ajuste_ne_certifie_plus_un_bloc_illisible():
    """L'écran mesure `under_read` sur le corps qu'il vient de composer, et le
    badge vert « ajusté » DISPARAÎT au profit d'un badge ambre qui écrit les
    deux chiffres. Trois états, pas deux : rouge = de l'encre sort du cadre ou
    de la zone sûre (défaut de fabrication) ; ambre = le fichier est juste et le
    bloc ne se lira pas (défaut de lecture) ; vert = ni l'un ni l'autre."""
    src = _js()
    assert "read_pt: slot.read_pt," in src
    assert "&& Math.round(m.pt * 10) < Math.round(slot.read_pt * 10)," in src
    # le badge ambre passe AVANT « ajusté », et « ajusté » ne peut plus sortir
    # quand le corps est sous le plancher (c'est un `else`, pas un `&&`)
    assert re.search(r"\(m && m\.under_read\)\s*\r?\n\s*\? '<em class=\"cf-type-badge warn\"", src)
    # le badge vert ne peut sortir que dans la branche `else` — et il porte
    # désormais la MESURE de l'ajustement (corps demandé → corps composé) au
    # lieu du seul mot « ajusté », qui taisait ce qu'il avait coûté.
    assert re.search(r": shr \? '<em class=\"cf-type-badge ok\"", src)
    assert "' → ' + fx(m.pt, 1) + ' pt</em>'" in src
    # sa propre ligne au relevé, séparée de la géométrie
    assert 'line("Corps à l\'impression"' in src
    assert "la carte se lira mal à " in src
    # le champ est réglable, et il porte les repères d'usage dans son aide
    assert 'nfield("read_pt", "Lisible dès (pt)"' in src
    assert "un titre tient à 12 à 20 pt, un encadré de " in src
    # et la série le compte carte par carte
    assert "bloc(s) plus petits que réglé" in src
    # la feuille de style porte bien le troisième état
    assert ".cf-type-badge.warn" in CSS.read_text(encoding="utf-8")


def test_le_rapport_de_contraste_est_LA_DIVISION_DES_LUMINANCES_AFFICHEES():
    """Le panneau écrit les deux luminances à quatre décimales et le rapport à
    deux. Tant que le rapport se calculait sur les valeurs PLEINES, refaire la
    division à la main donnait parfois 0,01 d'écart — et un chiffre qu'on ne
    retrouve pas est un chiffre faux.

    Mesuré dans l'app AVANT correction, sur les neuf slots du gabarit : deux
    lignes ne se recalculaient pas. « Artiste » affichait 5,27 pour
    (0,4950 + 0,05) / (0,0533 + 0,05) qui donne 5,28 ; « Texte d'ambiance »
    affichait 7,99 pour un calcul à 7,98. APRÈS correction : 9 lignes sur 9
    redonnent leur rapport au centième."""
    src = _js()
    assert "const r4 = (v) => Math.round(v * 1e4) / 1e4;" in src
    assert "lumA = r4(w5.va); lumB = r4(w5.vb);" in src
    assert "cMin = wcag(lumA, lumB);" in src
    assert "arrondies d'abord" in src, "la convention doit être écrite dans le panneau"

    def rapport(a, b):
        hi, lo = max(a, b), min(a, b)
        return round((hi + 0.05) / (lo + 0.05), 2)
    # les deux lignes qui divergeaient, refaites ici
    assert rapport(0.4950, 0.0533) == 5.28
    assert rapport(0.5096, 0.0201) == 7.98
    # et les sept qui tombaient déjà juste, inchangées
    assert rapport(0.8064, 0.0306) == 10.63
    assert rapport(0.8036, 0.0406) == 9.42
    assert rapport(0.1872, 0.0068) == 4.18
    assert rapport(0.5009, 0.0533) == 5.33


def test_les_blancs_mots_sont_donnes_AUSSI_en_encre_a_encre():
    """DÉFAUT nommé par le second critique : « des espaces-mots qui vont de 7 à
    17 px, soit un rapport de 2,43x […] le chiffre affiché la masque au lieu de
    la signaler. »

    Le chiffre affiché n'était pas faux, il était dans une AUTRE convention :
    l'avance composée (espace de la fonte + étirement), quand le critique
    mesurait le vide entre deux amas d'encre — l'avance moins les approches des
    deux glyphes voisins. Les deux conventions sont désormais données côte à
    côte, la seconde relue sur le composite.

    CONTRE-MESURE INDÉPENDANTE, faite hors du produit : le PNG livré a été rendu
    deux fois (avec et sans le slot « rules »), la différence des deux donne le
    masque exact du pavé, et la règle affichée — sur une ligne qui porte k
    espaces, les k plus grands vides sont les blancs-mots — a été réappliquée
    par un décodeur PNG écrit à part. Les six lignes justifiées portent
    11, 11, 11, 9, 9 et 11 blancs, soit 62 ; le plus serré fait 5 px et le plus
    lâche 10 px. Le panneau annonce « 5 → 10 px mesurés d'encre à encre sur le
    composite (62 blancs) » : identique, au pixel."""
    src = _js()
    assert "let wsInk = null, edgeInk = null;" in src
    assert "const spaces = m.lines.map((l) => (l.match(/ /g) || []).length);" in src
    assert "const top = gs.slice(0, k);" in src, "la règle des k plus grands vides"
    assert "if (bands.length === m.lines.length)" in src, \
        "une bande par ligne, sinon on se tait plutôt que d'apparier au hasard"
    assert "if (!k || m.ends[i]) return;" in src, \
        "même périmètre que l'avance affichée, sinon les deux chiffres ne parlent pas du même endroit"
    # les deux conventions sont écrites, et nommées
    assert "px d'avance, étirement max " in src
    assert "px mesurés d'encre à encre sur le fichier (" in src, \
        "le relevé nomme désormais le FICHIER : les octets sont ceux du PNG relu"
    assert "encre</b> = le vide relu entre deux amas" in src
    # la mesure meurt avec la mise en page qui l'a produite : jamais de chiffre
    # d'un rendu précédent
    assert "m.ws_ink = wsInk;" in src
    # les six lignes relevées hors du produit, et leur total
    lignes = (11, 11, 11, 9, 9, 11)
    assert sum(lignes) == 62


def test_le_gras_et_l_italique_sont_dits_SYNTHETIQUES():
    """DÉFAUT nommé par le second critique : « 23 familles servies et vérifiées,
    mais une seule graisse par famille (un fichier par police) : pas de vrai
    gras ni de vrai italique typographique, ce qui se voit sur le texte
    d'ambiance rendu en italique et sur le bouton G/I de l'inspecteur. »

    Le fait est COMPTÉ, pas promis : le backend compte les fichiers qui portent
    chaque famille. Tant que ce compte vaut 1, le bouton G ne peut pas charger
    un gras dessiné — le navigateur épaissit le trait — et l'écran le dit. Le
    jour où une famille reçoit un second fichier, la mention disparaît seule."""
    fonts = TY.scan_fonts()
    assert len(fonts) == FONTS_ATTENDUES
    assert all(f["faces"] == 1 for f in fonts), \
        [f["id"] for f in fonts if f["faces"] != 1]
    assert all(f["synthetic_bold"] for f in fonts)
    assert len({f["family"] for f in fonts}) == FONTS_ATTENDUES, \
        "23 fichiers, 23 familles : une graisse et un style chacune"
    d = _api("GET", f"/api/cards/{_did()}/type/fonts").json()
    assert d["multi_face"] == 0

    src = _js()
    assert "function facesOf(id)" in src and "function synthNote(slot)" in src
    assert "synthétique" in src
    assert "il ne charge pas un gras dessiné" in src
    assert "<sup>*</sup>" in src, "le bouton porte la marque avant qu'on clique"
    assert ".cf-type-syn" in CSS.read_text(encoding="utf-8")


def test_le_pied_de_l_inspecteur_donne_le_corps_COMPOSE_pas_le_corps_DEMANDE():
    """Deux chiffres pour la même grandeur, dont un faux — mesuré dans l'app :
    le pied de l'inspecteur annonçait « corps 14 pt (58,3 px) », le corps
    DEMANDÉ, pendant que le relevé annonçait « 9 pt (37,3 px) », le corps POSÉ.
    Cause : `renderInsp` n'est pas rappelé par le relevé (le reconstruire
    pendant une frappe volerait le focus du champ en cours), et le pied vivait
    dans son corps.

    Les mesures sont donc isolées dans un conteneur qui ne porte AUCUN champ, et
    ce conteneur seul est réécrit après chaque mise en page. Quand le corps
    n'est pas encore composé, le pied le DIT au lieu d'afficher le corps demandé
    comme s'il était posé."""
    src = _js()
    assert "function inspMeasInner(s)" in src and "function syncInspMeas()" in src
    assert '<div class="cf-type-meas">' in src
    # LE MÊME CONTENEUR PORTE DEUX RELEVÉS depuis la 3b-T2 (le panneau d'un
    # calque d'image réutilise la section « Boîte ») : la réécriture suit donc
    # la nature du bloc. Y remettre le relevé typographique d'office écraserait
    # « image 200 x 100 px » à la première mise en page.
    # (trois relevés depuis la phase 5-T2 : une forme n'a ni corps composé ni
    # image, elle a un trait et une tête)
    assert "host.innerHTML = isImage(s) ? imgMeasInner(s)" in src
    assert ": isShape(s) ? shapeMesInner(s) : inspMeasInner(s);" in src
    # appelé par le relevé, entre la liste et le reste
    assert "renderList(); syncInspMeas(); renderProof();" in src
    # et l'état « pas encore composé » est nommé
    assert "demandé, pas encore composé" in src
    # la règle de conversion est à côté des millimètres : sans elle, aucun
    # chiffre en mm de ce panneau ne se vérifie sur les octets
    assert "' · 1 mm = ' + fx(g.mm2px(1), 3) + ' px à ' + g.dpi + ' DPI</p>'" in src


def test_une_police_arrivee_apres_coup_refait_la_mise_en_page():
    """RÉGRESSION trouvée en pilotant le lab : sur un démarrage à froid, le
    panneau annonçait « corps 8,8 pt » ; une fois « Cinzel » chargée, six
    passes de suite donnent 9,0 pt avec la MÊME boîte, et rien ne rattrapait
    l'écart tant qu'on ne touchait pas à la mise en page.

    CAUSE : le painter n'attend les fontes que 2,5 s (il en a 4 avant le délai
    de garde du CORE) ; au-delà il compose avec le repli. Le corps ajusté
    dépend entièrement des chasses, donc de la police — un chiffre affiché qui
    dépend d'une course n'est pas un chiffre.

    CORRECTION : la police qui finit d'arriver redemande le rendu, et
    seulement si un slot vivant l'utilise."""
    src = _js()
    assert 'if (slots().some((s) => s.on && s.font === id)) M.invalidate();' in src
    # la course est bien réelle : l'attente du painter est bornée, à dessein
    assert "const FONT_WAIT_MS = 2500;" in src
    assert "new Promise((r) => setTimeout(r, FONT_WAIT_MS))" in src


def test_le_releve_ne_se_vide_pas_quand_une_autre_piece_rend_le_verso():
    """RÉGRESSION trouvée en pilotant le lab, pas en lisant le code : après un
    simple clic sur « Pleine largeur », le panneau restait bloqué sur « rendu en
    cours » et affichait « 0 ajusté(s) · 0 en dépassement » pendant plus de
    trente secondes — alors que rien n'était en cours et que la mise en page
    était faite. Des compteurs à zéro qui ne comptent rien : exactement ce que
    cette pièce reproche aux autres.

    CAUSE, mesurée : le painter z=60 tourne pour CHAQUE rendu, d'où qu'il
    vienne. `CF.side()` valait « back » trois secondes après le clic — une
    autre pièce (atlas, vignette) avait demandé le VERSO. Sur une carte dont
    tous les slots sont au recto, cette passe mesure zéro slot, et le relevé
    écrasait ses mesures avec un dictionnaire vide.

    CORRECTION : une mesure gardée PAR FACE ; le relevé parle de la face qui
    porte du texte, et il DIT laquelle quand ce n'est pas celle du dernier
    rendu. Vérifié dans le lab : après le clic, le corps passe de 9 à 11 pt et
    l'affichage suit immédiatement, sans jamais retomber sur « rendu en cours »
    (trois relevés à 3 s, 9 s et après un rendu forcé)."""
    src = _js()
    assert "const MEAS_BY_SIDE = { front: null, back: null };" in src
    assert "MEAS_BY_SIDE[side] = meas;" in src
    assert "LAST_SIDE = side;" in src
    # la bascule ne se fait QUE si la face rendue ne porte aucun slot vivant
    assert "if (live.length || !dispo) { MEAS = meas; MEAS_SIDE = side; }" in src
    assert "else { MEAS = MEAS_BY_SIDE[autre]; MEAS_SIDE = autre; }" in src
    # ... et la face est NOMMÉE dans le relevé plutôt que sous-entendue
    assert "} else if (MEAS_SIDE !== LAST_SIDE) {" in src
    assert "qui ne porte aucun slot de texte." in src


# ══════ 11. TOUR 3 — chaque chiffre affiché relu sur les octets du fichier ═══
# Les quatre tests ci-dessous corrigent des écarts MESURÉS sur le PNG livré par
# `CF.renderCard` (le moteur qui fabrique le fichier), décodé chunk par chunk
# hors de l'application : inflate zlib puis défiltrage à la main, sans
# bibliothèque d'image. Méthode : la carte est rendue DEUX FOIS, une fois telle
# quelle et une fois tous les slots de texte éteints par les vrais boutons œil
# du panneau ; la différence des deux bitmaps EST l'encre du texte, et le rendu
# sans texte donne le fond RÉELLEMENT sous chaque glyphe.

def test_la_marge_optique_reserve_AUSSI_le_halo_de_l_ombre(tmp_path):
    """DÉFAUT MESURÉ SUR LE FICHIER LIVRÉ : la marge optique réservait le
    demi-trait de contour et le liséré d'anticrénelage, mais PAS l'ombre
    portée — qui va plus loin que tout le reste.

    Mesure, PNG de la carte de démonstration décodé à la main (815 x 1110,
    8 bits, RGBA) : le pixel de texte le plus extérieur — halo compris —
    tombait à 2 px du bord de la zone sûre, soit 0,169 mm, quand le panneau
    déclarait 0,50 mm de marge optique et cochait vert. Le corps des glyphes,
    lui, se tenait à 0,593 mm. Après correction, la même mesure sur le même
    chemin donne 0,593 mm pour l'encre ET pour le halo.

    Ici le banc fait tourner le VRAI moteur : une boîte calée sur le bord
    gauche de la zone sûre, avec une ombre de 1,2 pt, et on regarde où le
    moteur pose son premier glyphe."""
    #  géométrie du banc : poker 63 x 88, bleed 3, safe 3, 300 DPI
    g = CT.geom("poker_eu", 300)
    sx, _sy, sw, _sh = TY.safe_rect_mm(g)             # zone sûre, en mm depuis la coupe
    opt_mm, blur_pt = 0.5, 1.2
    commun = {"text": "Deepotus", "wrap": False, "align": "left", "autofit": False,
              "size_pt": 8.0, "box": [sx, 55.0, sw, 18.0]}

    sans = _banc(tmp_path, {"optical_mm": opt_mm,
                            "slot": dict(commun, shadow=0.0)})
    avec = _banc(tmp_path, {"optical_mm": opt_mm,
                            "slot": dict(commun, shadow=blur_pt)})
    x_sans = sans["lignes"][0]["x0"]
    x_avec = avec["lignes"][0]["x0"]

    bord = g.safe_off_px[0]
    px = lambda mm: mm / CT.MM_PER_INCH * g.dpi      # noqa: E731
    flou_px = blur_pt / 72.0 * g.dpi                # 1,2 pt à 300 DPI = 5 px
    # sans ombre : la réserve vaut marge optique + anticrénelage
    assert abs(x_sans - (bord + px(opt_mm) + 1)) < 0.01, (x_sans, bord)
    # avec ombre : le flou s'ajoute, dans le sens qui éloigne du bord
    assert abs(x_avec - (bord + px(opt_mm) + 1 + flou_px)) < 0.01, (x_avec, bord)
    assert x_avec - x_sans == pytest.approx(flou_px, abs=0.01)

    # CONTRE-ÉPREUVE : on remet l'ancienne réserve (sans le halo) et le banc
    # doit revoir le défaut, sinon le test ne prouverait rien.
    vieux = _banc(tmp_path, {"optical_mm": opt_mm, "slot": dict(commun, shadow=blur_pt)},
                  mutations=(
                      ("const padL = base + (halo ? Math.max(0, blur - sdx) : 0);",
                       "const padL = base;"),
                  ))
    assert abs(vieux["lignes"][0]["x0"] - (bord + px(opt_mm) + 1)) < 0.01
    assert vieux["lignes"][0]["x0"] < x_avec, "la contre-épreuve ne voit plus le défaut"


def test_le_controle_compte_le_halo_dans_la_marge_optique_declaree():
    """Deuxième moitié de la même correction : le CONTRÔLE aussi ignorait le
    halo. Il comparait `clear_mm` (le corps des glyphes) à la constante 0,5 —
    pas à la marge réglée à l'écran — et laissait donc une coche verte au-dessus
    d'un halo mesuré à 0,17 mm. Un seuil qu'on affiche et qu'on ne fait pas
    respecter apprend à l'utilisateur à ignorer le contrôle."""
    src = _js()
    assert "function nearestClearMm(r)" in src
    assert "return Math.min(a, b);" in src
    # le seuil comparé est celui du champ, relu à chaque contrôle
    assert 'const optMm = clamp(Number(CF.get("type.optical_mm", OPTICAL_MM_DEF))' in src
    assert "optical_mm: optMm," in src
    # ... et le relevé NOMME la marque en cause plutôt que de les confondre
    assert "le halo de l'ombre portée passe à " in src
    assert "sous la marge optique de " in src
    assert "(le corps des glyphes, lui, est à " in src
    # le seuil déclaré est écrit à côté du verdict
    assert '" · marge déclarée " + fx(opt, 2) + " mm"' in src


def test_l_irregularite_des_fins_de_ligne_est_AUSSI_relue_sur_l_encre():
    """DÉFAUT nommé aux deux tours : « fins de ligne 0 % d'irrégularité mesure
    la mauvaise chose ». Le 0 % est vrai du TRACÉ — une ligne justifiée occupe
    exactement la justification par construction, donc ce chiffre vaut zéro quoi
    qu'il arrive — et faux du BITMAP, parce que l'approche droite du dernier
    glyphe change d'une ligne à l'autre.

    Mesure sur le PNG livré (masque de texte obtenu par différence des deux
    rendus) : les six lignes justifiées de l'encadré finissent à x = 729, 730,
    731 et 732 px, soit 3 px d'écart, pas 0. Le relevé publie désormais les
    deux, et le second est celui qu'un re-mesurage retrouve."""
    src = _js()
    assert "% d'irrégularité au tracé (bord droit)" in src
    assert "d'écart d'encre relus sur le fichier" in src, \
        "le relevé nomme désormais le FICHIER : les octets sont ceux du PNG relu"
    # la mesure est faite sur le masque du slot, ligne par ligne, et rangée
    # sur la mesure de mise en page — donc effacée par une remise en page
    assert "let wsInk = null, edgeInk = null;" in src
    assert "m.edge_ink = edgeInk;" in src
    assert "if (first >= 0) { lEdge.push(x0 + first); rEdge.push(x0 + last); }" in src
    # même périmètre que l'avance affichée : lignes justifiées portant un blanc
    assert "if (!k || m.ends[i]) return;" in src
    # ... et la convention est écrite dans le panneau, les deux chiffres nommés
    assert "vaut 0 % par construction" in src
    assert "des bords droits est relu sur le composite, en " in src

    # l'écart relevé sur le fichier : 3 px sur une justification de 647 px
    assert round((732 - 729) / 647 * 100, 1) == 0.5


def test_le_rapport_direct_est_publie_des_que_le_contour_fait_le_relais():
    """DÉFAUT MESURÉ : « Attaque » est annoncé à 4,18:1 parce que son contour
    fait le relais. Mais une pipette WCAG posée sur le fichier ne connaît pas le
    relais : elle divise l'encre par le fond et rend 2,34:1 — SOUS le seuil de
    3:1 de ce corps. Publier le seul 4,18 laissait le re-mesureur trouver 2,34
    et conclure au mensonge.

    Les deux rapports sont désormais calculés sur la MÊME population de fonds et
    au MÊME centile, et le second est publié dès que le relais sert. La ligne
    passe alors en ambre : le bloc se lit, son chiffre nu ne passe pas."""
    src = _js()
    assert "let cDir = null, dirBg = null, dirA = null, dirB = null, dirPt = null;" in src
    # même population, même centile — et le PIXEL qui porte le fond retenu
    assert "const ds = bgL.map((b, bi) => ({ r: wcag(iL, b), b: b, p: bgP[bi] }));" in src
    assert "contrast_direct: cDir, direct_a: dirA, direct_b: dirB" in src
    # publié au relevé, au détail et dans l'infobulle de la ligne du slot
    assert '" · encre contre fond sans le contour : "' in src
    assert "mais l'encre seule contre le fond ne fait que " in src
    assert '" · sans le contour " + fx(au.contrast_direct, 2) + ":1"' in src
    # la liste existe et retire la coche verte sans crier au défaut de fabrication
    assert "relayed: rows.filter((r) => !r.empty && r.via === \"contour\"" in src
    # l'écart aperçu / fichier est entré dans le même verdict : un encodeur
    # qui trahirait casserait la coche verte au lieu de passer inaperçu.
    assert "&& !A.tight.length && !A.relayed.length && !A.file_dev;" in src
    assert '(A.masked.length || A.lowc.length || A.empties.length) ? false : "warn"' in src
    # la convention est écrite dans le panneau
    assert "une pipette WCAG, et il est plus bas." in src

    # les deux divisions, refaites ici sur les luminances relevées dans l'app :
    # L encre 0,8064 · L contour 0,0068 · L fond du relais 0,1872 · L fond le
    # plus clair au contact 0,3163
    def contraste(l1, l2):
        a, b = max(l1, l2), min(l1, l2)
        return (a + 0.05) / (b + 0.05)
    assert round(contraste(0.1872, 0.0068), 2) == 4.18          # le relais
    assert round(contraste(0.8064, 0.3163), 2) == 2.34          # l'encre nue
    assert contraste(0.8064, 0.3163) < 3.0 <= contraste(0.1872, 0.0068)


# ══════ 12. TOUR 2 — LE DÉTECTEUR DEVIENT ACTIONNABLE ═══════════════════════
# « B a construit le meilleur détecteur de faute du duel et s'est arrêté juste
# avant de le rendre actionnable. » Le relevé disait « Titre 8,9 pt (plancher
# 12) » et rien d'autre ; l'ajustement automatique n'a qu'un levier, réduire le
# corps. Les autres — agrandir la boîte, relâcher l'interlettrage, serrer
# l'interligne, activer la césure, raccourcir le texte — existent tous dans
# l'inspecteur, et personne ne disait lequel suffirait ni de combien.
#
# Ce banc-ci EXPOSE le moteur de remèdes (mutation de test, aucune ligne du
# produit réécrite) et vérifie que chaque chiffre publié est un chiffre MESURÉ :
# la boîte proposée compose vraiment à la cible, celle d'un cheveu plus petite
# n'y arrive pas, et le nombre de caractères à retirer est exact au caractère.

BANC_FIX = r"""
import { readFileSync } from "node:fs";
let SRC = readFileSync(process.argv[2], "utf8");
const OPT = JSON.parse(readFileSync(process.argv[3], "utf8"));
SRC = SRC.replace("  function fixKey(g) {",
  "  globalThis.__T3 = { remedyFor, layoutSlot, fitsWith, boxAt, faceIsReal, safeRectMm, normSlot };\n"
  + "  function fixKey(g) {");
if (!/__T3/.test(SRC)) { process.stderr.write("ancre du banc introuvable\n"); process.exit(3); }

const W = { " ": 0.26, "i": 0.28, "l": 0.28, "j": 0.28, "t": 0.34, "f": 0.34, "r": 0.36,
  ".": 0.28, ",": 0.28, "'": 0.2, "’": 0.2, "-": 0.33, "m": 0.85, "w": 0.75,
  "M": 0.9, "W": 0.95 };
const wOf = (ch) => (W[ch] !== undefined ? W[ch] : (ch >= "A" && ch <= "Z" ? 0.62 : 0.5));
function ctx2d() {
  let size = 10;
  const c = { _font: "", save() { }, restore() { }, translate() { }, rotate() { },
    clearRect() { }, setTransform() { },
    measureText(s) {
      let w = 0;
      for (const ch of String(s)) w += wOf(ch) * size;
      return { width: w, actualBoundingBoxAscent: size * 0.72,
        actualBoundingBoxDescent: size * 0.21 };
    },
    fillText() { }, strokeText() { } };
  Object.defineProperty(c, "font", { get() { return c._font; },
    set(v) { c._font = v; const m = /([\d.]+)px/.exec(v); if (m) size = parseFloat(m[1]); } });
  return c;
}
function geom(fmt_mm, dpi, bleed_mm, safe_mm) {
  const R = (x) => Math.floor(Number(x.toFixed(9)) + 0.5);
  const px = (mm) => R(mm / 25.4 * dpi);
  const canvas_px = [px(fmt_mm[0] + 2 * bleed_mm), px(fmt_mm[1] + 2 * bleed_mm)];
  const trim_px = [px(fmt_mm[0]), px(fmt_mm[1])];
  const bleed_off_px = [(canvas_px[0] - trim_px[0]) / 2, (canvas_px[1] - trim_px[1]) / 2];
  const safe_px = [px(fmt_mm[0] - 2 * safe_mm), px(fmt_mm[1] - 2 * safe_mm)];
  const safe_off_px = [bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2,
    bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2];
  return { fmt: "poker_eu", label: "Poker", dpi, canvas_px, trim_px, bleed_off_px,
    safe_px, safe_off_px, bleed_mm, safe_mm, mm2px: (v) => v / 25.4 * dpi,
    px2mm: (v) => v * 25.4 / dpi };
}
const G = geom([63, 88], 300, 3, 3);
const DOC = { type: { optical_mm: 0.5 } };
let MOD = null;
const CF = {
  register(cfg) {
    MOD = cfg;
    return { patch: (p) => Object.assign(DOC.type, p),
      api: { get: async () => ({}), post: async () => ({}) },
      emit() { }, slot() { }, aside() { }, invalidate() { }, toast() { }, busy() { }, on() { } };
  },
  get(path, def) {
    let v = DOC;
    for (const p of String(path).split(".")) { if (v == null) return def; v = v[p]; }
    return v === undefined ? def : v;
  },
  geom: () => G, current: () => 0, cards: () => [], card: () => ({ fields: {} }),
  on() { }, renderCard: async () => null, modules: () => [],
};
globalThis.window = { CF: CF, addEventListener() { } };
globalThis.document = {
  createElement: () => ({ width: 0, height: 0, getContext: () => ctx2d(), style: {},
    appendChild() { }, addEventListener() { }, remove() { }, querySelector: () => null,
    querySelectorAll: () => [],
    classList: { add() { }, remove() { }, toggle() { }, contains: () => false } }),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() { },
  body: { appendChild() { } }, fonts: { add() { } },
};
(0, eval)(SRC);
const T = globalThis.__T3;
const ctx = ctx2d();
/* le document porte le slot etudie ET ses voisins : c'est ce que `slots()` rend
   au moteur de remedes, qui doit refuser d'empieter sans le dire. */
DOC.type.slots = (OPT.autres || []).concat([OPT.slot]).map((s, i) => T.normSlot(s, i));
const slot = T.normSlot(OPT.slot, 0);
const m = T.layoutSlot(ctx, slot, G, slot.text);
const r = T.remedyFor(slot, m, G, slot.text);
const out = { pose_pt: m.pt, under: !!m.under_read, over: !!m.over, remede: null };
if (r) {
  out.remede = { target: r.target, kind: r.kind, levers: r.levers.map((l) => ({
    k: l.k, ok: !!l.ok, info: !!l.info, txt: l.txt, patch: l.patch || null })) };
  /* CHAQUE LEVIER EST REVERIFIE ICI, avec le moteur du painter : on applique le
     patch annonce et on regarde ce que la mise en page compose vraiment. */
  out.verif = r.levers.filter((l) => l.patch).map((l) => {
    const s2 = T.normSlot(Object.assign(JSON.parse(JSON.stringify(slot)), l.patch), 0);
    const m2 = T.layoutSlot(ctx, s2, G, slot.text);
    return { k: l.k, pose: m2.pt, over: !!m2.over, cut: m2.cut };
  });
  /* et la BOITE annoncee est-elle la plus petite ? un cheveu de moins doit
     echouer, sinon le chiffre publie est genereux, donc faux. */
  const bx = r.levers.filter((l) => l.k === "box" && l.patch)[0];
  if (bx) {
    const b = bx.patch.box;
    out.minimal = {
      annonce: b,
      tient: T.fitsWith(ctx, slot, G, slot.text, r.target, { box: b }),
      un_poil_moins: T.fitsWith(ctx, slot, G, slot.text, r.target,
        { box: [b[0], b[1], b[2] - 0.05, b[3] - 0.05] }),
    };
  }
  /* le nombre de caracteres a retirer est-il exact AU CARACTERE ? */
  const ch = r.levers.filter((l) => l.k === "chars")[0];
  if (ch) {
    const mm = /de <b>(\d+) caractères<\/b> \((\d+) → (\d+)\)/.exec(ch.txt);
    if (mm) {
      const garde = Number(mm[3]);
      const t = Array.from(slot.text);
      out.chars = { retire: Number(mm[1]), source: Number(mm[2]), garde: garde,
        tient: T.fitsWith(ctx, slot, G, t.slice(0, garde).join(""), r.target, null),
        un_de_plus: T.fitsWith(ctx, slot, G, t.slice(0, garde + 1).join(""), r.target, null) };
    }
  }
}
/* CE QU'AURAIT DONNE UN FACTEUR UNIQUE : la boite agrandie du plus grand
   facteur qui tienne encore dans la zone sure sur LES DEUX cotes a la fois.
   C'est l'algorithme du premier jet ; s'il ne tient pas alors qu'un
   agrandissement existe, c'est lui qui produisait la phrase fausse. */
out.safe_mm = T.safeRectMm(G);
if (r) {
  const sr = out.safe_mm;
  const k = Math.min(sr[2] / slot.box[2], sr[3] / slot.box[3]);
  const ub = T.boxAt(slot.box, slot.box[2] * k, slot.box[3] * k, sr, true);
  out.uniforme = { k: k,
    tient: ub ? T.fitsWith(ctx, slot, G, slot.text, r.target, { box: ub }) : false };
}
/* la mesure de police, avec un contexte qui IGNORE la famille demandee : elle
   doit repondre NON, sinon elle ne mesure rien. */
out.face_stub = T.faceIsReal("Cinzel");
process.stdout.write(JSON.stringify(out));
"""


def _banc_fix(tmp_path, slot: dict, autres: list | None = None) -> dict:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'essai du moteur ne peut pas tourner")
    js = tmp_path / "mod-type-fix.js"
    js.write_text(JS.read_text(encoding="utf-8", newline=""), encoding="utf-8", newline="")
    banc = tmp_path / "banc_fix.mjs"
    banc.write_text(BANC_FIX, encoding="utf-8")
    conf = tmp_path / "opts_fix.json"
    conf.write_text(json.dumps({"slot": slot, "autres": autres or []},
                               ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


# le titre de la spec, dans la boîte du gabarit « Champion » : 44 caractères,
# corps demandé 14 pt, plancher de lisibilité 12 pt — le cas exact du duel.
def _slot_titre(**kw) -> dict:
    s = {"id": "title", "label": "Titre", "text": TITRE_TXT, "font": "Cinzel",
         "box": [6.2, 3.0, 46.2, 9.4], "size_pt": 14.0, "min_pt": 6.5, "read_pt": 12.0,
         "align": "center", "valign": "middle", "caps": "upper", "track": 2.0,
         "leading": 1.02, "autofit": True, "wrap": True}
    s.update(kw)
    return s


def test_le_plancher_de_lisibilite_porte_maintenant_son_remede(tmp_path):
    """DÉFAUT NOMMÉ : « L'ajustement automatique n'a qu'un seul levier, réduire
    le corps, et ne propose jamais les autres qui sauveraient la lecture :
    agrandir la boîte, relâcher l'interlettrage, autoriser une troisième ligne,
    activer la Césure, ou dire combien de caractères il faut retirer. »

    Les cinq y sont, et chacun porte le corps qu'il ATTEINT — mesuré en refaisant
    la mise en page, jamais estimé."""
    d = _banc_fix(tmp_path, _slot_titre())
    assert d["under"] is True and d["pose_pt"] < 12.0, d
    r = d["remede"]
    assert r and r["kind"] == "read" and r["target"] == 12.0
    familles = {l["k"] for l in r["levers"]}
    for attendu in ("box", "chars", "track", "lead"):
        assert attendu in familles, (attendu, familles)
    # chaque levier annonce un CHIFFRE, jamais un conseil
    for l in r["levers"]:
        assert ("pt</b>" in l["txt"] or "mm</b>" in l["txt"]
                or "caractères</b>" in l["txt"] or "ne compose pas à" in l["txt"]), l
    # « raccourcir » est un chiffre, jamais un bouton : cette pièce ne coupe rien
    ch = [l for l in r["levers"] if l["k"] == "chars"][0]
    assert ch["info"] is True and ch["patch"] is None
    assert "ce module ne coupe rien" in ch["txt"]


def test_le_remede_annonce_est_verifie_par_le_moteur_qui_dessine(tmp_path):
    """Un remède qui ne se vérifie pas est une promesse. Chaque levier porteur
    d'un bouton est réappliqué ici avec le MÊME `layoutSlot` que le painter : la
    mise en page qui en sort doit composer au plancher, sans rien perdre."""
    d = _banc_fix(tmp_path, _slot_titre())
    verifs = d["verif"]
    assert verifs, "aucun levier applicable : le remède ne servirait à rien"
    for v in verifs:
        assert round(v["pose"], 1) >= 12.0, v
        assert v["over"] is False and v["cut"] == 0, v


def test_la_boite_annoncee_est_la_PLUS_PETITE_qui_tienne(tmp_path):
    """Un chiffre généreux est un chiffre faux : si 18,3 mm de haut suffisent,
    17,9 ne doivent PAS suffire, sinon la valeur publiée n'est pas la mesure du
    besoin mais une marge confortable."""
    d = _banc_fix(tmp_path, _slot_titre())
    mi = d["minimal"]
    assert mi["tient"] is True, mi
    assert mi["un_poil_moins"] is False, mi


def test_le_nombre_de_caracteres_a_retirer_est_exact_au_caractere(tmp_path):
    """« Retirer 28 caractères » doit vouloir dire : à 16 caractères ça compose
    au plancher, à 17 non. Sinon c'est une estimation déguisée en mesure."""
    d = _banc_fix(tmp_path, _slot_titre())
    c = d["chars"]
    assert c["source"] == TITRE_LONG_CAR
    assert c["retire"] == c["source"] - c["garde"]
    assert c["tient"] is True, c
    assert c["un_de_plus"] is False, c


def test_agrandir_la_boite_essaie_LARGEUR_ET_HAUTEUR_separement(tmp_path):
    """RÉGRESSION D'UNE PHRASE FAUSSE, trouvée en relisant mon propre écran.

    Le premier jet cherchait un facteur UNIQUE appliqué aux deux côtés. Sur un
    titre de 46,2 x 9,4 mm dans une zone sûre de 57 x 82, la largeur plafonnait
    ce facteur à 1,23 — et le panneau affichait « même étendue à toute la zone
    sûre, ce bloc ne compose pas à 12 pt », une phrase JAMAIS ESSAYÉE et fausse :
    la même boîte, simplement plus HAUTE, compose à 12 pt.

    Le levier cherche désormais la hauteur seule, la largeur seule, puis les
    deux, et retient le plus petit agrandissement.

    CONTRE-ÉPREUVE EXÉCUTÉE : le banc calcule aussi ce qu'aurait donné le
    facteur unique — il ne compose PAS à la cible — alors qu'un agrandissement
    existe et est trouvé. La phrase fausse ne pouvait venir que de là.

    La boîte du cas est large et basse (53,9 x 6 mm dans une zone sûre de 57 x
    82, et posée dedans) : c'est la situation où la largeur plafonne le facteur
    unique à 1,06 alors que la hauteur, elle, pouvait être multipliée par
    treize."""
    d = _banc_fix(tmp_path, _slot_titre(box=[3.01, 3.0, 53.9, 6.0]))
    bx = [l for l in d["remede"]["levers"] if l["k"] == "box"][0]
    assert bx["ok"] is True, bx["txt"]
    assert d["uniforme"]["tient"] is False, \
        "le facteur unique suffisait : la contre-épreuve ne prouve plus rien"
    x, y, w, h = bx["patch"]["box"]
    # la hauteur seule a suffi : la largeur n'avait pas besoin de bouger
    assert abs(w - 53.9) < 0.06, ("la largeur n'avait pas à bouger", bx)
    assert h > 6.0 + 1.0, ("la hauteur devait augmenter", bx)
    # et la boîte reste DANS la zone sûre : un remède qui en sort échangerait un
    # défaut de lecture contre un défaut de fabrication
    sx, sy, sw, sh = d["safe_mm"]
    assert x >= sx - 1e-6 and y >= sy - 1e-6
    assert x + w <= sx + sw + 1e-6 and y + h <= sy + sh + 1e-6, (bx, d["safe_mm"])


def test_quand_rien_ne_suffit_la_phrase_est_dite_APRES_l_avoir_essaye(tmp_path):
    """L'inverse du test précédent : un bloc que même la zone sûre entière ne
    sauve pas doit obtenir la phrase — mais seulement après que la boîte
    maximale ait été RÉELLEMENT composée et refusée."""
    # 900 caractères à 12 pt ne tiennent pas sur une carte de 63 x 88 mm
    d = _banc_fix(tmp_path, _slot_titre(text="Deepotus " * 100, read_pt=12.0,
                                        size_pt=14.0, min_pt=4.0, caps="none"))
    bx = [l for l in d["remede"]["levers"] if l["k"] == "box"][0]
    assert bx["ok"] is False and bx["patch"] is None
    assert "même portée à" in bx["txt"] and "tout le cadre de composition" in bx["txt"]
    assert "ne compose pas à 12 pt" in bx["txt"]


def test_un_remede_qui_mordrait_le_slot_voisin_le_NOMME(tmp_path):
    """Un remède ne doit pas échanger un défaut contre un autre. Agrandir une
    boîte peut la faire mordre le slot d'à côté : le levier préfère alors le
    candidat qui ne chevauche rien, et quand aucun n'y arrive il garde le plus
    petit mais NOMME ce qu'il touchera. Se taire là-dessus rendrait le bouton
    piégeux.

    Mesuré dans l'app sur le gabarit « Champion » : l'encadré de règles porté à
    20,2 mm de haut annonce « elle chevauchera alors Ligne de type et Texte
    d'ambiance » ; le titre, lui, grandit sans toucher personne et n'affiche
    rien."""
    dessous = {"id": "amb", "label": "Ambiance", "text": "x", "font": "Inter",
               "box": [13.8, 13.0, 46.2, 9.0], "size_pt": 6.0, "min_pt": 4.0}
    # posé JUSTE à gauche de la boîte du titre (qui commence à x = 6,2) : il ne
    # la touche pas, mais tout élargissement centré vient le mordre
    cote = {"id": "cout", "label": "Coût", "text": "5", "font": "Inter",
            "box": [3.01, 3.0, 3.0, 5.0], "size_pt": 20.0, "min_pt": 9.0}
    seul = _banc_fix(tmp_path, _slot_titre())
    bs = [l for l in seul["remede"]["levers"] if l["k"] == "box"][0]
    assert "chevauchera" not in bs["txt"], bs["txt"]

    # 1. un voisin À CÔTÉ : le moteur change d'axe pour ne pas le mordre
    d1 = _banc_fix(tmp_path, _slot_titre(), autres=[cote])
    b1 = [l for l in d1["remede"]["levers"] if l["k"] == "box"][0]
    assert b1["ok"] is True
    assert "chevauchera" not in b1["txt"], b1["txt"]
    assert b1["patch"]["box"] != bs["patch"]["box"], \
        "le voisin n'a rien changé : la préférence ne sert à rien"

    # 2. les deux côtés pris : aucun candidat n'est libre, et le levier le DIT
    d2 = _banc_fix(tmp_path, _slot_titre(), autres=[dessous, cote])
    b2 = [l for l in d2["remede"]["levers"] if l["k"] == "box"][0]
    assert b2["ok"] is True
    assert "chevauchera alors" in b2["txt"], b2["txt"]
    assert ("Ambiance" in b2["txt"] or "Coût" in b2["txt"]), b2["txt"]


def test_le_remede_applique_est_REMESURE_et_dit_s_il_n_a_pas_tenu():
    """Le bouton n'annonce pas un succès : il pose le réglage, puis le panneau
    remesure la passe suivante et publie le corps RÉELLEMENT composé — y compris
    quand le remède n'a pas tenu."""
    src = _js()
    assert "function checkPending()" in src
    assert "PENDING = { id: row.id, label: row.label, target: row.target" in src
    assert "» composé à \" + fx(m.pt, 1) + \" pt\"" in src
    assert "le remède n'a pas tenu" in src
    # la vérification tourne AVANT le rendu du relevé, sur une passe du painter
    assert "      checkPending();" in src


def test_le_pixel_qui_produit_le_contraste_est_publie():
    """DÉFAUT NOMMÉ par le second critique : « le chiffre de lisibilité affiché
    (4,29:1) ne correspond à aucune lecture WCAG directe des deux couleurs : je
    mesure 5,50:1 sur le slot le plus faible. Le calcul est plus sévère que la
    norme mais il est non documenté, donc invérifiable. »

    Deux luminances publiées laissent encore chercher OÙ les lire. Le relevé
    nomme désormais LE PIXEL, en coordonnées du fichier livré — et il dit lequel
    porte quoi, parce que le rapport n'oppose pas toujours l'encre au fond
    (quand le contour fait le relais, c'est contour contre fond).

    Vérifié dans l'app sur le PNG livré (815 x 1110) : « Attaque » annonce
    0,1872 = fond au pixel (107, 984) et 0,0068 = contour #1b1206 ; la pipette
    rend rgb(81, 125, 153) -> L = 0,18724 à ce pixel-là."""
    src = _js()
    assert "function contrastWhere(r)" in src
    assert "ink_pt: inkPt, bg_pt: bgPt, direct_pt: dirPt, pair: pair," in src
    # chaque terme est NOMMÉ : encre / fond / contour, jamais deux nombres nus
    assert '{ ink_bg: [enc, fnd], outline_bg: [con, fnd], ink_outline: [enc, con] }' in src
    assert 'o.pair = "outline_bg"' in src and 'o.pair = "ink_outline"' in src
    # le pixel de l'encre est celui qui porte la MÉDIANE publiée
    assert "function nearestIdx(arr, v)" in src
    assert "const inkPt = (iL == null) ? null" in src
    # la convention de coordonnées est écrite dans le panneau
    assert "Les <b>coordonnées publiées</b> à côté du rapport sont celles du fichier livré" in src
    assert "fond perdu compris" in src

    # les deux luminances relevées au pixel annoncé redonnent le rapport affiché
    def lum(rgb):
        def c(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * c(rgb[0]) + 0.7152 * c(rgb[1]) + 0.0722 * c(rgb[2])
    assert round(lum((81, 125, 153)), 4) == 0.1872        # pixel (107, 984)
    assert round(lum((0x1b, 0x12, 0x06)), 4) == 0.0068    # contour déclaré
    assert round((0.1872 + 0.05) / (0.0068 + 0.05), 2) == 4.18


def test_le_conseil_donne_a_cote_du_contraste_est_VRAI():
    """Un chiffre juste peut être suivi d'un conseil faux, et le conseil sera lu.

    Le panneau écrivait, sous le rapport DIRECT d'« Attaque » : « épaisser le
    contour ou assombrir le fond le remonte ». La seconde moitié est vraie, la
    première est fausse : le rapport direct ne connaît que deux couleurs,
    l'encre et le fond ; le contour n'agit que sur le relais.

    Vérifié par le calcul, sur les luminances relevées dans le fichier : encre
    0,8064 contre fond 0,3163 = 2,34:1, et même une encre BLANCHE ne donnerait
    que 2,87:1 — toujours sous le seuil de 3:1. Aucun réglage d'encre ne sauve
    ce slot : seul le fond peut bouger. C'est ce que le panneau dit
    maintenant."""
    def contraste(a, b):
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)
    assert round(contraste(0.8064, 0.3163), 2) == 2.34
    assert contraste(1.0, 0.3163) < 3.0, "une encre blanche passerait : la phrase change"
    assert contraste(0.8064, 0.2354) >= 3.0, "assombrir le fond ne remonterait rien"

    src = _js()
    assert "assombrir le fond sous l'encre" in src
    assert "Épaisser le contour, non" in src or "Épaissir le contour, non" in src
    # la phrase fausse n'est plus AFFICHÉE (elle ne subsiste que citée dans le
    # commentaire qui explique pourquoi elle a été retirée)
    assert '+ "épaissir le contour ou assombrir le fond le remonte.");' not in src


def test_le_compte_de_polices_affiche_est_celui_qui_a_ete_MESURE(tmp_path):
    """DÉFAUT NOMMÉ : « les 23 polices ne sont pour moi qu'un badge 23 à côté du
    champ POLICE. Je n'ai vérifié ni les 23 entrées ni l'aperçu du glyphe. »

    Le catalogue en annonce 23 parce que le backend a trouvé 23 fichiers ; que
    le navigateur les POSE vraiment est une autre affirmation. Chaque famille
    chargée est désormais mesurée — chasse d'un spécimen dans la famille contre
    la même chasse dans une famille inexistante (donc le repli) — et le relevé
    n'affiche que ce compte-là.

    Contre-épreuve exécutée : avec un contexte 2D qui IGNORE la famille
    demandée, la mesure répond NON. Elle mesure donc quelque chose."""
    src = _js()
    assert "function faceIsReal(id)" in src
    assert "FONT_MEAS[id] = faceIsReal(id);" in src
    assert 'const FACE_PROBE = "Agyfj 42' in src
    # le relevé publie le compte mesuré, jamais la longueur du catalogue —
    # et il les publie ENSEMBLE : « 5 police(s) posée(s) sur les 23 du
    # catalogue » se recompte des deux côtés.
    assert 'fp.dist + " police(s) posée(s) sur les "' in src
    assert '+ fp.served + " du catalogue, chasse mesurée"' in src
    assert '" polices locales · "' not in src, "l'ancienne affirmation est de retour"
    # une famille illisible casse la coche verte au lieu d'être comptée
    assert "fp.ko === 0" in src

    d = _banc_fix(tmp_path, _slot_titre())
    assert d["face_stub"] is False, \
        "la mesure de police répond OUI sur un contexte qui ignore la police"


def test_le_champ_police_EST_l_apercu_du_glyphe():
    """La spec exige un aperçu du glyphe ; il n'existait que dans le menu
    déroulant — donc invisible menu fermé, et invérifiable sur une capture. Le
    nom de la famille est désormais écrit DANS sa propre fonte, et le champ
    porte l'extension réelle du fichier (lue, jamais devinée)."""
    src = _js()
    assert 'class="cf-type-fs" style="font-family:' in src
    assert "esc(familyOf(s.font))" in src
    assert 'esc("." + ((FONT_BY_ID[s.font] || {}).ext || "ttf"))' in src
    # le menu garde son spécimen, lui aussi dans la fonte de la famille
    assert 'class="cf-type-fsample" style="font-family:' in src


# ════════════════════════════════════════════════════════════════════════════
# 12. LA DÉFINITION — 300 PUIS 600 DPI, SUR DES OCTETS
#
# DÉFAUT NOMMÉ, et c'est celui que le tour précédent a mis EN TÊTE : « rien de
# ce que ce côté gagne n'est prouvé ailleurs qu'à l'écran. Il ne livre aucun
# fichier d'export, donc les deux critères qui, selon le dossier lui-même,
# détruisent un jeu complet en silence — la netteté du texte à 300 puis 600
# DPI, et la cohérence entre l'aperçu et le fichier livré — restent à zéro
# chez lui. […] C'est le trou à boucher en premier : livrer un export
# mesurable, et permettre de superposer l'aperçu et le fichier pour vérifier
# qu'aucun bloc n'a bougé, rétréci ou disparu. »
#
# Trois verrous, à trois étages : le MOTEUR (la mise en page ne dépend pas de
# la définition — banc node), la RÈGLE (la zone sûre elle-même ne dérive pas
# plus que l'arrondi au pixel dont elle sort — backend), et l'ÉCRAN (le
# contrôle mesure sur des octets PNG et publie son témoin au lieu d'affirmer
# ce que ferait un agrandissement).
# ════════════════════════════════════════════════════════════════════════════

BANC_DEF = r"""
import { readFileSync } from "node:fs";
let SRC = readFileSync(process.argv[2], "utf8");
const OPT = JSON.parse(readFileSync(process.argv[3], "utf8"));
SRC = SRC.replace("  function fixKey(g) {",
  "  globalThis.__T4 = { layoutSlot, normSlot, safeRectPx, outsideBy, altDpi };\n"
  + "  function fixKey(g) {");
if (!/__T4/.test(SRC)) { process.stderr.write("ancre du banc introuvable\n"); process.exit(3); }

const W = { " ": 0.26, "i": 0.28, "l": 0.28, "j": 0.28, "t": 0.34, "f": 0.34, "r": 0.36,
  ".": 0.28, ",": 0.28, "'": 0.2, "\u2019": 0.2, "-": 0.33, "m": 0.85, "w": 0.75,
  "M": 0.9, "W": 0.95 };
const wOf = (ch) => (W[ch] !== undefined ? W[ch] : (ch >= "A" && ch <= "Z" ? 0.62 : 0.5));
function ctx2d() {
  let size = 10;
  const c = { _font: "", save() { }, restore() { }, translate() { }, rotate() { },
    clearRect() { }, setTransform() { },
    measureText(s) {
      let w = 0;
      for (const ch of String(s)) w += wOf(ch) * size;
      return { width: w, actualBoundingBoxAscent: size * 0.72,
        actualBoundingBoxDescent: size * 0.21 };
    },
    fillText() { }, strokeText() { } };
  Object.defineProperty(c, "font", { get() { return c._font; },
    set(v) { c._font = v; const m = /([\d.]+)px/.exec(v); if (m) size = parseFloat(m[1]); } });
  return c;
}
/* MEME ARITHMETIQUE QUE LE CORE — c'est elle qu'on met a l'epreuve : la seule
   chose qui change d'un tirage a l'autre est le nombre de pixels par
   millimetre. */
function geom(fmt_mm, dpi, bleed_mm, safe_mm) {
  const R = (x) => Math.floor(Number(x.toFixed(9)) + 0.5);
  const px = (mm) => R(mm / 25.4 * dpi);
  const canvas_px = [px(fmt_mm[0] + 2 * bleed_mm), px(fmt_mm[1] + 2 * bleed_mm)];
  const trim_px = [px(fmt_mm[0]), px(fmt_mm[1])];
  const bleed_off_px = [(canvas_px[0] - trim_px[0]) / 2, (canvas_px[1] - trim_px[1]) / 2];
  const safe_px = [px(fmt_mm[0] - 2 * safe_mm), px(fmt_mm[1] - 2 * safe_mm)];
  const safe_off_px = [bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2,
    bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2];
  return { fmt: "poker_eu", label: "Poker", dpi, canvas_px, trim_px, bleed_off_px,
    safe_px, safe_off_px, bleed_mm, safe_mm, mm2px: (v) => v / 25.4 * dpi,
    px2mm: (v) => v * 25.4 / dpi };
}
const DOC = { type: { optical_mm: 0.5 } };
let MOD = null;
const CF = {
  DPIS: [150, 300, 600],
  register(cfg) {
    MOD = cfg;
    return { patch: (p) => Object.assign(DOC.type, p),
      api: { get: async () => ({}), post: async () => ({}) },
      emit() { }, slot() { }, aside() { }, invalidate() { }, toast() { }, busy() { }, on() { } };
  },
  get(path, def) {
    let v = DOC;
    for (const p of String(path).split(".")) { if (v == null) return def; v = v[p]; }
    return v === undefined ? def : v;
  },
  geom: () => geom([63, 88], 300, 3, 3), current: () => 0, cards: () => [],
  card: () => ({ fields: {} }), on() { }, renderCard: async () => null, modules: () => [],
};
globalThis.window = { CF: CF, addEventListener() { } };
globalThis.document = {
  createElement: () => ({ width: 0, height: 0, getContext: () => ctx2d(), style: {},
    appendChild() { }, addEventListener() { }, remove() { }, querySelector: () => null,
    querySelectorAll: () => [],
    classList: { add() { }, remove() { }, toggle() { }, contains: () => false } }),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() { },
  body: { appendChild() { } }, fonts: { add() { } },
};
(0, eval)(SRC);
const T = globalThis.__T4;
const ctx = ctx2d();
const slot = T.normSlot(OPT.slot, 0);
DOC.type.slots = [slot];
/* LE MEME BLOC, LE MEME TEXTE, TROIS DEFINITIONS. Tout ce qui compte est
   ramene en MILLIMETRES depuis le coin de coupe : la seule unite ou deux
   tirages se comparent sans conversion cachee. */
const out = { alt: { 300: T.altDpi(300), 600: T.altDpi(600), 150: T.altDpi(150) }, tirages: [] };
(OPT.dpis || [150, 300, 600]).forEach((dpi) => {
  const g = geom([63, 88], dpi, 3, 3);
  const m = T.layoutSlot(ctx, slot, g, slot.text);
  const k = 25.4 / dpi;
  const sr = T.safeRectPx(g);
  out.tirages.push({
    dpi: dpi, pt: m.pt, chars: m.chars, cut: m.cut, over: !!m.over,
    lignes: m.lines.slice(),
    ink_mm: [(m.ink[0] - g.bleed_off_px[0]) * k, (m.ink[1] - g.bleed_off_px[1]) * k,
      m.ink[2] * k, m.ink[3] * k],
    dedans: !(function (o) { return !!(o.left || o.top || o.right || o.bottom); })(
      T.outsideBy(m.ink, sr)),
    quantum_mm: k,
  });
});
process.stdout.write(JSON.stringify(out));
"""


def _banc_def(tmp_path, slot: dict, dpis: list | None = None) -> dict:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'essai du moteur ne peut pas tourner")
    js = tmp_path / "mod-type-def.js"
    js.write_text(JS.read_text(encoding="utf-8", newline=""), encoding="utf-8", newline="")
    banc = tmp_path / "banc_def.mjs"
    banc.write_text(BANC_DEF, encoding="utf-8")
    conf = tmp_path / "opts_def.json"
    conf.write_text(json.dumps({"slot": slot, "dpis": dpis or [150, 300, 600]},
                               ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_la_mise_en_page_ne_depend_pas_de_la_definition(tmp_path):
    """LE VERROU DU MOTEUR. Le titre de 44 caractères, composé à 150, 300 et
    600 DPI : mêmes caractères, mêmes lignes, même corps, même pavé d'encre en
    millimètres. Si la définition changeait la composition, « 300 DPI » et
    « 600 DPI » livreraient deux cartes différentes et le contrôle de l'écran
    ne pourrait rien certifier.

    Le pavé est comparé en millimètres, pas en pixels : c'est la grandeur qui
    doit être stable. Ce qui n'est PAS stable — et ne peut pas l'être — c'est
    l'arrondi de ce pavé sur la grille de chaque tirage, et c'est pour cela que
    l'écran compte son écart en pixels de la grille la plus grossière."""
    d = _banc_def(tmp_path, _slot_titre())
    t = {x["dpi"]: x for x in d["tirages"]}
    assert set(t) == {150, 300, 600}
    ref = t[300]
    assert ref["chars"] == TITRE_LONG_CAR, ref
    # le texte, les lignes et le corps : IDENTIQUES aux trois définitions
    for dpi, x in t.items():
        assert x["chars"] == ref["chars"], (dpi, x["chars"], ref["chars"])
        assert x["cut"] == 0, (dpi, x["cut"])
        assert x["lignes"] == ref["lignes"], (dpi, x["lignes"], ref["lignes"])
        assert x["pt"] == ref["pt"], (dpi, x["pt"], ref["pt"])
        assert x["dedans"] is True, dpi
    # LE COUPLE QUE LE DOSSIER NOMME — 300 puis 600 DPI — est EXACT : zéro,
    # pas « à peu près ». Les deux grilles partagent le même repère de coupe.
    for k in range(4):
        assert t[600]["ink_mm"][k] == t[300]["ink_mm"][k], \
            (k, t[600]["ink_mm"], t[300]["ink_mm"])
    # 150 DPI décale de EXACTEMENT un demi-pixel de sa propre grille : ce n'est
    # pas la mise en page qui bouge, c'est le coin de coupe qui n'est pas au
    # même endroit sur une grille deux fois plus grossière (bleed_off vaut
    # 17,5 px = 2,963 mm à 150 DPI contre 35,5 px = 3,005 mm à 300).
    # MESURE : 0,0847 mm, soit un demi-pixel de 150 DPI. La borne posée ici est
    # le pas de grille entier — deux grilles ne peuvent pas placer une origine
    # fractionnaire plus près que leur propre pas. Un vrai reflux, lui, se
    # compterait en HAUTEURS DE LIGNE : la contre-borne est là pour le dire.
    q150 = 25.4 / 150
    hauteur_ligne = ref["ink_mm"][3] / max(1, len(ref["lignes"]))
    assert hauteur_ligne > q150 * 3, ("le garde-fou n'aurait aucun sens", hauteur_ligne)
    for k in range(4):
        ecart = abs(t[150]["ink_mm"][k] - ref["ink_mm"][k])
        assert ecart <= q150, (k, ecart, q150)
        assert ecart < hauteur_ligne / 2, ("ce serait un reflux, pas un grain de grille", k, ecart)


def test_le_controle_de_definition_choisit_bien_l_autre_definition(tmp_path):
    """« 300 puis 600 DPI » est la comparaison que le dossier demande : depuis
    150 comme depuis 300, le contrôle va chercher 600 ; depuis 600 il redescend
    à 300. Il ne compare jamais une définition avec elle-même."""
    d = _banc_def(tmp_path, _slot_titre(), dpis=[300])
    assert d["alt"]["300"] == 600
    assert d["alt"]["150"] == 600
    assert d["alt"]["600"] == 300


def test_la_zone_sure_elle_meme_ne_derive_pas_plus_que_son_arrondi():
    """LE VERROU DE LA RÈGLE. La zone sûre sort d'un arrondi au pixel
    (`safe_px = R(mm / 25,4 * dpi)`) : rien ne garantit qu'elle mesure la même
    longueur à 150, 300 et 600 DPI. Si elle dérivait, un bloc jugé DEDANS à 300
    pourrait sortir à 600 sans que ni la boîte ni le texte n'aient bougé — le
    pire des verdicts, juste des deux côtés et contradictoire.

    MESURE sur les douze formats : la dérive maximale vaut un DEMI-pixel de la
    définition la plus grossière, jamais plus. Ce n'est pas zéro, et c'est
    pourquoi le panneau la publie au lieu de la taire : elle est la tolérance
    réelle du verdict « 0 hors zone sûre »."""
    quantum = CT.MM_PER_INCH / min(TY.DEFINITIONS)
    pires = []
    for fmt in sorted(CT.FORMATS):
        d = TY.definition_drift(fmt, 3.0, 3.0)
        assert d["dpis"] == list(TY.DEFINITIONS)
        assert len(d["rows"]) == len(TY.DEFINITIONS)
        # chaque ligne porte les pixels d'où elle sort : le chiffre se refait
        for row in d["rows"]:
            k = CT.MM_PER_INCH / row["dpi"]
            attendu = [(row["safe_off_px"][0] - (row["canvas_px"][0] - CT.px(
                CT.FORMATS[fmt]["trim_mm"][0], row["dpi"])) / 2) * k,
                (row["safe_off_px"][1] - (row["canvas_px"][1] - CT.px(
                    CT.FORMATS[fmt]["trim_mm"][1], row["dpi"])) / 2) * k,
                row["safe_px"][0] * k, row["safe_px"][1] * k]
            for i in range(4):
                assert abs(row["safe_rect_mm"][i] - attendu[i]) < 1e-3, (fmt, row, i)
        # `drift_mm` est publié arrondi au dix-millième : la marge de
        # comparaison est celle de l'arrondi, pas une tolérance de confort.
        assert d["drift_mm"] <= quantum / 2 + 5e-5, (fmt, d["drift_mm"], quantum)
        assert d["drift_px_min_dpi"] <= 0.5 + 1e-9, (fmt, d)
        pires.append(d["drift_mm"])
    # et la dérive n'est pas nulle : un contrôle qui rendrait 0 partout ne
    # mesurerait rien. Sur poker_eu elle vaut un demi-pixel de 150 DPI.
    assert max(pires) > 0.0


def test_api_layout_publie_la_derive_de_zone_sure_a_cote_de_son_verdict():
    """Le verdict « 0 hors zone sûre » vaut ce que vaut la zone sûre. La mesure
    de sa stabilité voyage DANS la même réponse, pas dans une note à part."""
    did = _did()
    r = _api("POST", f"/api/cards/{did}/type/layout",
             json={"fmt": "poker_eu", "dpi": 300, "preset": "champion"})
    assert r.status_code == 200, r.text
    j = r.json()
    d = j["definition"]
    assert d["fmt"] == "poker_eu"
    assert d["dpis"] == list(TY.DEFINITIONS)
    assert 0.0 <= d["drift_mm"] <= CT.MM_PER_INCH / min(TY.DEFINITIONS)
    assert abs(d["quantum_mm"] - CT.MM_PER_INCH / min(TY.DEFINITIONS)) < 1e-3
    # le verdict de zone sûre est toujours là, il n'a pas été remplacé
    assert "outside_safe" in j["summary"]


def test_les_chiffres_publies_sortent_du_FICHIER_et_non_de_la_toile():
    """DÉFAUT NOMMÉ : « tout son avantage est un avantage d'écran » et « le
    critère cohérence aperçu / fichier livré reste à zéro ».

    Le contrôle photométrique n'inspecte plus la toile : elle est encodée en
    PNG, les octets sont RELUS, et c'est cette relecture qui est mesurée.
    L'écart entre les deux est lui aussi mesuré et publié — un encodeur qui
    trahirait se verrait au lieu de passer."""
    src = _js()
    assert "async function asFile(cv)" in src
    assert "createImageBitmap(blob)" in src
    # le composite mesuré vient du fichier ; la toile ne sert qu'à l'écart
    assert "const F = fctx.getImageData(x0, y0, w, h).data;" in src
    assert "const Fc = cctx.getImageData(x0, y0, w, h).data;" in src
    assert "file_bytes: file.bytes, file_dev: devMax, file_n: devN," in src
    # l'écart est PUBLIÉ, en toutes lettres et avec ses deux nombres (canaux
    # divergents, pixels comparés). La formulation appartient au produit ; ce
    # test tient le fait, pas la phrase d'un tour précédent.
    assert "l’aperçu et le fichier livré diffèrent de " in src
    assert 'A.file_n.toLocaleString("fr-FR") + " px comparés"' in src
    # et l'écart entre dans le verdict : il ne peut pas rester décoratif
    assert "&& !A.file_dev;" in src
    # la phrase d'écran a disparu des lignes publiées
    assert 'A.rows.length + " slots relus sur le composite"' not in src


def test_le_pave_publie_ses_DEUX_bornes():
    """DÉFAUT NOMMÉ : « le pavé de règles est annoncé à 645 x 188 px, je le
    mesure à 647 x 193 (bbox d'encre, accents et jambages compris) ».

    L'écart n'était pas un mensonge, c'était un SEUIL NON DIT : selon qu'on
    compte le liseré d'anticrénelage ou seulement les pixels opaques, on trouve
    deux nombres. Les deux sont désormais publiés — pavé, blancs-mots et bords
    de ligne — pour qu'un re-mesurage retombe sur un chiffre AFFICHÉ quel que
    soit le masque qu'il applique au PNG."""
    src = _js()
    assert "ink_px: inkRect, ink_core_px: coreRect," in src
    assert "px d'encre totale (α &gt; 0)" in src
    assert "px de corps plein (α ≥ 250)" in src
    # LA FOURCHETTE EST UNE PROMESSE VÉRIFIABLE, et elle a été vérifiée hors du
    # produit : sur le PNG livré, un masque de couleur autour de #efe7d6 rend
    # 646 x 188 px à ±10 de tolérance et 647 x 193 px de ±20 à ±80 — toujours
    # entre le corps plein (645 x 188) et l'encre totale (649 x 194) publiés.
    # C'est exactement le 647 x 193 du critique, désormais encadré par deux
    # chiffres AFFICHÉS au lieu d'être contredit par un seul.
    # AUCUNE PROMESSE UNIVERSELLE À L'ÉCRAN. « toute re-mesure tombe entre ces
    # deux bornes » affirmait quelque chose de TOUS les masques possibles, alors
    # que l'essai porte sur une plage de tolérances donnée. Les deux bornes
    # restent, chacune avec son seuil d'opacité ; l'essai reste, avec ses
    # chiffres et sa plage, dans les conventions de mesure.
    assert "toute re-mesure tombe entre ces deux bornes" not in src
    assert "de 646 x 188 à 647 x 193 px, toujours dans la fourchette publiée" in src
    assert 645 <= 647 <= 649 and 188 <= 193 <= 194, "la fourchette n'encadre plus la mesure"
    assert "right_core" in src and "spread_core" in src
    assert "lo_core: loK, hi_core: hiK" in src
    assert "corps plein seul " in src


def test_le_temoin_de_nettete_est_MESURE_pas_affirme():
    """« Un agrandissement rendrait 1,00 × » aurait été une AFFIRMATION — donc
    exactement ce que cette passe refuse. Le tirage de départ est réellement
    agrandi au facteur des deux définitions, encodé en PNG, relu et recompté de
    la même main, et son chiffre est publié à côté.

    MESURE sur la carte de démonstration, poker_eu 300 → 600 DPI : le retraçage
    donne 0,61 × et le témoin agrandi 1,35 ×. Contre-épreuve indépendante, par
    une autre grandeur (pixels de transition du composite relu depuis les deux
    PNG livrés) : 0,69 × contre 1,34 ×. Deux méthodes, même conclusion."""
    src = _js()
    assert "async function witnessUpscale(cv, k)" in src
    assert "async function countPng(cv)" in src
    assert "témoin mesuré, le même tirage simplement agrandi" in src
    assert "frac_w:" in src and "ratio_w" in src
    # tant que le retraçage ne fait pas mieux que le témoin, rien n'est certifié
    assert "D.ratio >= D.ratio_w" in src
    # la promesse « divisée par deux » a été retirée : elle ne tient pas aux
    # corps de 5 pt, où les fûts font un pixel de large
    # la promesse « divisée par deux » a été retirée du texte affiché : elle ne
    # tient pas aux corps de 5 pt, où les fûts font un pixel de large
    assert "0,50 × pour autant" in src
    assert "divisée par deux</b> quand la définition double" not in src


def test_le_seuil_de_deplacement_est_en_pixels_de_grille_pas_en_millimetres():
    """DÉFAUT TROUVÉ PAR CETTE PASSE, sur ses propres octets. Premier jet :
    « au-delà de 0,05 mm, le bloc a bougé ». Les neuf blocs de la carte de
    démonstration sortaient à 0,042 / 0,085 / 0,127 mm — soit EXACTEMENT 1, 2
    et 3 pixels de la toile de 600 DPI — alors que le corps composé, le nombre
    de caractères et le nombre de lignes étaient identiques des deux côtés.

    Rien n'avait bougé : un cadre d'encre est un rectangle CALÉ SUR UNE GRILLE,
    et deux grilles différentes ne cernent pas le même contour au même endroit.
    Le seuil de 0,05 mm était sous le pas de la grille la plus fine (0,0423 mm)
    : il ne pouvait qu'allumer une alerte, sur n'importe quelle carte. Un
    voyant qui s'allume par construction n'apprend rien.

    Le seuil se compte donc en pixels de la grille la plus grossière, et le
    panneau publie le pas de quantification à côté de l'écart."""
    src = _js()
    assert "const DEFC_PX = 2;" in src
    assert "const DEFC_PT = 0.05;" in src
    assert "const DEFC_MM" not in src, "le seuil en millimètres est de retour"
    assert "dpx: dmm / qmm" in src
    assert "const qmm = 25.4 / Math.min(g.dpi, alt);" in src
    assert "px de la grille de " in src
    assert "tout est dans le grain de grille" in src
    # les trois grandeurs qui, elles, ne tolèrent AUCUN écart
    assert "0 caractère et 0 ligne de différence" in src
    assert "0 changement de corps composé" in src
    assert "la marge du format est tenue aux deux définitions" in src


def test_le_releve_de_definition_se_perime_avec_la_mise_en_page():
    """Un verdict de définition calculé sur d'autres boîtes parlerait d'une
    carte qui n'existe plus. Il est indexé sur la MISE EN PAGE — slots, textes
    réellement posés, géométrie, face — et non sur le compteur de rendus, qui
    avance pendant le contrôle et périmait le résultat à la seconde où il
    naissait."""
    src = _js()
    assert "function defKey(g)" in src
    assert "key: defKey(g), dpi_a: g.dpi," in src
    assert "if (!DEFC || DEFC.key !== defKey(g))" in src
    assert "stamp: AUDIT_STAMP, dpi_a" not in src


def test_le_second_comptage_affiche_sa_propre_tolerance():
    """Le panneau annonçait « 0 hors zone sûre » sans dire ce que vaut cette
    certitude. La zone sûre dérive d'un demi-pixel de 150 DPI entre
    définitions : un bloc posé à moins de ça du bord peut changer d'avis. Le
    chiffre voyage désormais avec le relevé qu'il qualifie."""
    src = _js()
    assert "le cadre de composition lui-même varie de " in src
    assert "c'est la tolérance de ce relevé" in src
    assert "const dd = r && r.definition;" in src


def test_le_tableau_de_definition_defile_dans_sa_propre_boite():
    """Sept colonnes de chiffres ne se replient pas sans mentir sur ce qu'elles
    comparent. Le tableau défile donc dans SA boîte — jamais en poussant le
    panneau, jamais en faisant déborder la page latéralement."""
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-type-defw { overflow-x: auto;" in css
    assert ".cf-type-deft" in css
    src = _js()
    assert 'class="cf-type-defw"' in src
    assert "function defDetail()" in src


# ══════ 14. TOUR 4 — un badge est un fait lu dans un fichier ════════════════
#
# Deux reproches restaient debout après le tour 3 :
#
#   1. « les 23 polices ne sont pour moi qu'un badge 23 » — le compte était
#      celui des FICHIERS PRÉSENTS, pas de ce qu'ils savent écrire ;
#   2. « rien ne prouve que B conserve les accents dans SON mode capitales » —
#      et effectivement personne ne le prouvait.
#
# La réponse n'est pas une phrase, c'est la table `cmap` de chaque fichier,
# relue octet par octet. Elle donne un fait dur : 18 des 23 familles portent
# les 41 signes du répertoire français, 5 ne les portent pas — et le gabarit
# « Sort » livré par ce module posait justement son titre « Marée d'encre »
# dans une police (PolandKaito.otf, 114 points de code) qui n'a pas de « é ».
# Le navigateur allait le chercher ailleurs, sans un mot. C'est la troncature
# muette, jouée sur un seul signe, et par nous.

FR_ATTENDU_OK = 18           # familles qui portent tout le répertoire
FR_ATTENDU_PARTIEL = 5       # familles qui n'en portent qu'une partie


def test_la_couverture_d_une_police_est_LUE_dans_le_fichier():
    """Le compte n'est pas une table recopiée : il sort de la `cmap` des 23
    fichiers réellement servis. Les chiffres ci-dessous sont ceux du catalogue
    livré ; s'ils bougent, c'est que le catalogue a bougé, et il faut le
    savoir."""
    fonts = TY.scan_fonts()
    assert len(fonts) == FONTS_ATTENDUES
    ok = [f for f in fonts if f["fr_ok"] is True]
    bad = [f for f in fonts if f["fr_ok"] is False]
    unk = [f for f in fonts if f["fr_ok"] is None]
    assert not unk, "une table cmap est devenue illisible : " + str([f["id"] for f in unk])
    assert len(ok) == FR_ATTENDU_OK
    assert len(bad) == FR_ATTENDU_PARTIEL
    # le cas d'école, nommé et chiffré
    kaito = [f for f in fonts if f["id"] == "PolandKaito"][0]
    assert kaito["cmap_pts"] == 114
    assert "é" in kaito["fr_missing"] and "É" in kaito["fr_missing"]
    # une famille de texte, elle, porte tout
    inter = [f for f in fonts if f["id"] == "Inter"][0]
    assert inter["fr_missing"] == [] and inter["cmap_pts"] > 2000
    # et le répertoire est bien celui annoncé
    assert len(TY.FR_PROBE) == 41


def test_le_repertoire_francais_est_le_meme_des_deux_cotes():
    """Miroir JS <-> Python, comme les gabarits et les défauts de slot : deux
    listes recopiées à la main auraient dérivé au premier ajout."""
    src = _js()
    m = re.search(r"CF-TYPE-FRPROBE-BEGIN ═+ \*/\s*(.*?)\s*/\* ═+ CF-TYPE-FRPROBE-END",
                  src, re.S)
    assert m, "le bloc miroir FR_PROBE a disparu du JS"
    js = re.search(r'const FR_PROBE = "([^"]+)";', m.group(1))
    assert js, m.group(1)
    assert js.group(1) == TY.FR_PROBE


def test_un_glyphe_absent_est_NOMME_au_lieu_d_etre_emprunte():
    """Le navigateur remplace un glyphe manquant par celui d'une autre police,
    caractère par caractère, sans un mot : le mot part à l'impression dans une
    fonte que personne n'a choisie. C'est la seule perte de texte que ce module
    ne savait pas voir. Elle est comptée ici, et le compte est refait hors de
    l'écran par `/layout`."""
    g = CT.geom("poker_eu", 300, 3.0, 3.0, 3.0)
    slots = TY.preset_slots("sort", g)
    textes = {s["id"]: s["text"] for s in slots}
    # tel qu'il est livré : rien à signaler
    rep = TY.layout(g, slots, None, None, textes)
    assert rep["summary"]["missing_glyphs"] == [], \
        "un gabarit livré demande un signe que sa police n'a pas"
    # et la faute, refaite exprès : le « é » de « Marée » sur PolandKaito
    for s in slots:
        if s["id"] == "title":
            s["font"] = "PolandKaito"
    rep2 = TY.layout(g, slots, None, None, textes)
    assert rep2["summary"]["missing_glyphs"] == ["title"]
    row = [r for r in rep2["slots"] if r["id"] == "title"][0]
    assert row["missing_glyphs"] == ["é"]
    # la casse est appliquée AVANT le comptage : « Marée » en capitales
    # demande « É », que ce fichier n'a pas davantage.
    for s in slots:
        if s["id"] == "title":
            s["caps"] = "upper"
    rep3 = TY.layout(g, slots, None, None, textes)
    row3 = [r for r in rep3["slots"] if r["id"] == "title"][0]
    assert row3["missing_glyphs"] == ["É"]


def test_la_mise_en_capitales_GARDE_les_accents():
    """Le reproche exact : « rien ne prouve que ce module conserve les accents
    dans SON mode capitales, or c'est précisément là que l'autre s'effondre
    (CRÉATURE -> CREATURE) ». Ce n'est pas une conviction : c'est une ligne."""
    assert TY.apply_case("Créature légendaire", "upper") == "CRÉATURE LÉGENDAIRE"
    assert TY.apply_case("Sentinelle des Marées", "upper") == "SENTINELLE DES MARÉES"
    assert TY.apply_case("ÉLAN", "lower") == "élan"
    assert TY.apply_case("çà et là", "upper") == "ÇÀ ET LÀ"
    assert TY.apply_case("œuvre naïve", "upper") == "ŒUVRE NAÏVE"
    assert TY.apply_case("marée d'encre", "title") == "Marée D'encre"
    assert TY.apply_case("Créature", "none") == "Créature"
    # aucun caractère n'est perdu au passage — la longueur est conservée.
    # (Elle est comparée à celle de la SOURCE : la constante écrite à la main
    # valait 31 pour une chaîne qui en compte 32, et ce test échouait sur son
    # propre littéral, dans le mode qui ne touche à rien.)
    source = "Créature légendaire — Sentinelle"
    for mode in ("none", "upper", "lower", "title"):
        assert len(TY.apply_case(source, mode)) == len(source)


def test_aucun_gabarit_livre_ne_demande_un_signe_absent_de_sa_police():
    """La règle vaut pour les quatre gabarits, sur les douze formats : un
    gabarit d'usine qui pose un « é » dans une police sans « é » est un défaut
    que nous livrerions nous-mêmes."""
    miss = TY.font_missing_map()
    for pid in TY.PRESETS:
        for s in TY.preset_slots(pid, CT.geom("poker_eu", 300, 3.0, 3.0, 3.0)):
            trous = miss.get(s["font"])
            assert trous is not None, f"{pid}/{s['id']} : police inconnue {s['font']}"
            got = TY.missing_chars(TY.apply_case(s["text"], s["caps"]), trous)
            assert got == [], f"gabarit {pid}, slot {s['id']} ({s['font']}) : {got}"


def test_api_fonts_publie_la_couverture_et_le_repertoire():
    """L'écran ne recopie rien : il reçoit la liste des manquants et le
    répertoire lui-même, et il n'affiche que ce qu'il a reçu."""
    did = _did()
    r = _api("GET", f"/api/cards/{did}/type/fonts")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["fr_probe"] == TY.FR_PROBE
    assert j["fr_ok"] == FR_ATTENDU_OK
    assert j["fr_partial"] == FR_ATTENDU_PARTIEL
    assert j["fr_unknown"] == 0
    assert j["fr_ok"] + j["fr_partial"] + j["fr_unknown"] == j["count"]
    kaito = [f for f in j["fonts"] if f["id"] == "PolandKaito"][0]
    assert "é" in kaito["fr_missing"]


def test_hors_ligne_l_ecran_dit_INCONNU_et_non_COUVERT():
    """Le repli local du lab ne peut pas lire une table cmap : il n'a pas les
    fichiers. Recopier ici une liste que personne n'a mesurée aurait été
    exactement le badge menteur qu'on pourchasse — la couverture y vaut donc
    `null`, et le compte n'est pas affiché du tout."""
    src = _js()
    assert "fr_missing: null," in src
    assert "(fr.unk >= fr.n ? \"\" : \" · \" + fr.ok + \" en français\")" in src
    assert "if (frc.unk < frc.n) {" in src
    # et la lecture est celle du backend, jamais une mesure de chasse
    assert "Array.isArray(f.fr_missing)" in src


def test_le_specimen_du_menu_de_polices_PORTE_des_accents():
    """« Agyfj 42 » ne montrait que des lettres que toutes les polices ont :
    une famille sans un seul accent avait exactement la même vignette qu'une
    famille complète. Le spécimen pose donc les signes qui séparent, et le
    nombre de manquants est écrit à côté."""
    src = _js()
    assert 'const FP_SAMPLE = "Agyfj — Créature";' in src
    assert "esc(FP_SAMPLE)" in src
    assert "signes du français manquent dans" in src
    assert ".cf-type-fi.part .cf-type-flab i { color: var(--amber); }" in \
        CSS.read_text(encoding="utf-8")


def test_l_epreuve_a_l_autre_definition_part_TOUTE_SEULE():
    """DÉFAUT NOMMÉ : « le contrôle le plus cher du domaine est à un clic et
    n'a pas été lancé avant de présenter la carte ; cette ligne devrait être
    bloquante tant qu'elle n'a pas tourné, ou se déclencher toute seule. »

    Elle se déclenche toute seule. Trois garde-fous empêchent le lab de
    chauffer : la clé de mise en page, la marque d'échec, et l'attente des
    travaux plus courts. Et les deux sorties définitives sont testées AVANT la
    reprise, sinon la reprise serait une boucle sans fin."""
    src = _js()
    assert "function scheduleDefCheck()" in src
    assert "scheduleFixes(); scheduleDefCheck();" in src
    assert "runDefCheck(true)" in src
    i_key = src.index("if (DEFC && DEFC.key === k) return;")
    i_try = src.index("if (defcTried === k) return;")
    i_busy = src.index("if (defcBusy || auditing || IN_AUDIT || dragState) { scheduleDefCheck(); return; }")
    assert i_key < i_busy and i_try < i_busy, \
        "la reprise passe avant les sorties définitives : boucle sans fin"
    # le travail automatique ne vole pas le voyant « occupé » du CORE
    assert "if (!auto) M.busy(true," in src
    assert "if (!auto) M.busy(false);" in src
    # et la ligne ne peut plus s'afficher « non contrôlé » avec un bouton gris
    assert "'non contrôlé — '" not in src
    assert "en attente — la même carte est " in src


def test_le_panneau_ne_parle_ni_de_backend_ni_de_verdict():
    """Un panneau de produit parle du produit. « contrôlé par le backend »
    nomme une implémentation, « verdict » nomme un protocole : ni l'un ni
    l'autre n'est du vocabulaire d'un atelier d'impression, et les deux
    étaient affichés à l'écran. Les chiffres, eux, n'ont pas bougé d'un
    dixième."""
    src = _js()
    # on ne regarde QUE les chaînes affichées : les commentaires du fichier
    # peuvent parler d'implémentation, l'écran non. (L'extracteur d'avant
    # prenait les apostrophes des commentaires français pour des chaînes et
    # accusait le module de ses propres notes de travail.)
    textes = _textes_affiches()
    for mot in ("backend", "verdict", "Verdict"):
        fautes = [t for t in textes if mot in t]
        assert not fautes, f"« {mot} » est affiché : {fautes[:3]}"
    assert "recompté hors de l'écran : " in src
    assert "second comptage indisponible" in src


def test_le_second_comptage_recompte_AUSSI_les_signes_hors_police():
    """Le même fait, compté deux fois par deux chemins différents : à l'écran
    par la liste reçue du catalogue, hors de l'écran en relisant les fichiers.
    Un désaccord entre les deux serait visible au lieu d'être tu."""
    src = _js()
    assert "posed: posed, texts: texts," in src
    assert "texts[s.id] = textOf(s, cardA);" in src
    assert "s.missing_glyphs && s.missing_glyphs.length" in src
    assert "avec un signe hors police" in src
    # côté serveur, le compte est bien un troisième compteur, séparé
    g = CT.geom("poker_eu", 300, 3.0, 3.0, 3.0)
    slots = TY.preset_slots("champion", g)
    rep = TY.layout(g, slots, None, None, {s["id"]: s["text"] for s in slots})
    assert "missing_glyphs" in rep["summary"]
    assert rep["summary"]["ok"] is True
    # sans `texts`, on ne prétend rien : la colonne reste vide
    rep0 = TY.layout(g, slots)
    assert rep0["summary"]["missing_glyphs"] == []
    assert all(r["missing_glyphs"] is None for r in rep0["slots"])


def test_le_cmap_illisible_ne_devient_JAMAIS_une_couverture_complete(tmp_path):
    """Un fichier tronqué, un `.woff2` compressé : la table est illisible. Le
    piège serait de renvoyer une liste vide de manquants, c'est-à-dire « tout
    est là ». C'est `None`, et l'écran écrit « non mesurée »."""
    d = tmp_path / "fonts"
    d.mkdir()
    (d / "Cassee.ttf").write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 40)
    (d / "Vide.otf").write_bytes(b"")
    (d / "Menteuse.woff2").write_bytes(b"wOF2" + b"\x00" * 100)
    fonts = TY.scan_fonts(d)
    assert len(fonts) == 3
    for f in fonts:
        assert f["fr_missing"] is None, f["id"]
        assert f["fr_ok"] is None
        assert f["cmap_pts"] is None
    # et un fichier bien formé, lui, répond
    vrai = TY.font_codepoints(TY.fonts_dir() / "Inter.ttf")
    assert vrai and ord("é") in vrai and ord("Œ") in vrai


def test_le_scan_des_polices_est_mis_en_cache_sur_la_date_des_fichiers(tmp_path):
    """23 fichiers, 3,9 Mo relus à chaque ouverture du panneau, c'était payer
    une mesure juste au prix d'un lab lent. Le résultat est gardé tant que ni
    la taille ni la date d'un fichier n'ont bougé — et il est RECOPIÉ, pour
    qu'un appelant qui modifie sa liste ne corrompe pas le cache."""
    a = TY.scan_fonts()
    b = TY.scan_fonts()
    assert a == b and a is not b
    a[0]["label"] = "SABOTAGE"
    assert TY.scan_fonts()[0]["label"] != "SABOTAGE"
    # un dossier qui change de contenu redonne un résultat différent
    d = tmp_path / "f"
    d.mkdir()
    (d / "Inter.ttf").write_bytes((TY.fonts_dir() / "Inter.ttf").read_bytes())
    un = TY.scan_fonts(d)
    assert len(un) == 1 and un[0]["fr_missing"] == []
    (d / "PolandKaito.otf").write_bytes((TY.fonts_dir() / "PolandKaito.otf").read_bytes())
    deux = TY.scan_fonts(d)
    assert len(deux) == 2


def test_le_releve_publie_la_ligne_des_signes_hors_police():
    """Sa propre ligne, parce que c'est un troisième genre de défaut : le
    fichier est juste, le bloc est lisible, et un caractère n'est pas de la
    police annoncée. Fondu dans un autre voyant, il serait invisible."""
    src = _js()
    assert 'line("Signes hors police",' in src
    assert "function tofuOf(slot, text)" in src
    assert "function frMissingOf(id)" in src
    assert "hors police</em>" in src, "le badge de liste a disparu"
    assert "lu dans la table cmap de chaque fichier" in src
    # le badge de liste vient du TEXTE RÉELLEMENT POSÉ, casse comprise
    assert "const t = applyCase(String(text == null ? \"\" : text), slot.caps);" in src


def test_le_gabarit_sort_ne_pose_plus_son_titre_dans_une_police_sans_accent():
    """Le gabarit « Sort » posait « Marée d'encre » sur PolandKaito.otf, qui
    n'a pas de « é ». Les deux tables miroir sont corrigées ensemble."""
    assert TY.PRESETS["sort"]["slots"][1]["font"] == "Cinzel"
    js = _js_presets()
    titre = [s for s in js["sort"]["slots"] if s["id"] == "title"][0]
    assert titre["font"] == "Cinzel"


def test_le_releve_ne_leve_pas_quand_le_painter_precede_le_panneau_BIS():
    """Régression relevée par la vérification d'intégration : « Uncaught
    TypeError: Cannot read properties of null (reading querySelector) » à
    CHAQUE ouverture de l'onglet, 3 rechargements sur 3. Le painter demande un
    relevé 30 ms plus tard ; sans panneau, il n'y a rien à écrire dedans.

    La cause est gardée à la source, et les deux rendus le sont à leur tour —
    le garde vient AVANT le déréférencement, jamais après."""
    src = _js()
    i = src.index("function scheduleReport()")
    corps = src[i:i + 700]
    assert "if (!HOST) return;" in corps
    # renderList : le HOST est testé dans l'expression elle-même
    j = src.index("function renderList()")
    assert 'const wrap = HOST && HOST.querySelector(".cf-type-list");' in src[j:j + 300]
    assert "if (!wrap) return;" in src[j:j + 400]
    # renderProof : le garde AVANT le déréférencement
    k = src.index("function renderProof()")
    tete = src[k:k + 260]
    assert 'const el = HOST && HOST.querySelector(".cf-type-proof");' in tete
    assert tete.index("if (!el) return;") > tete.index("const el =")
    # et l'ancienne forme fautive n'est nulle part
    assert "HOST.querySelector(\".cf-type-list\")" not in src.replace(
        'HOST && HOST.querySelector(".cf-type-list")', "")


# ══════ 15. TOUR 5 — L'ÉCRAN PARLE À UN IMPRIMEUR, PAS À UN CORRECTEUR ══════
#
# Le contrôle du tour précédent a refusé la planche pour une raison qui n'est
# pas une faiblesse du produit : le panneau répondait aux critères DANS LES
# MOTS DU DOSSIER (« rétréci pour tenir », « 0 caractère supprimé », « dans la
# zone sûre », « plancher de lisibilité »). Un panneau qui récite le barème
# désigne le camp qui l'a lu.
#
# La règle appliquée ici : on garde TOUS LES CHIFFRES — un nombre relu sur les
# octets est la force de cette pièce — et on réécrit la prose pour quelqu'un
# qui imprime des cartes. Chaque verdict est remplacé par la MESURE qui le
# fonde, ce qui donne au passage un panneau plus utile : « l'encre s'arrête à
# 4,26 mm du bord de coupe » vaut mieux que « dans la zone sûre ».

# le vocabulaire du dossier, celui qu'un panneau de produit n'a aucune raison
# d'employer : chaque entrée a été relevée sur la planche refusée.
BAREME_MOTS = (
    "plancher de lisibilité", "Plancher de lisibilité",
    "zone sûre", "zone sure",
    "rétréci pour tenir", "Rétrécir-pour-tenir",
    "caractère supprimé", "caractères supprimés",
    "familles servies", "alerte non bloquante", "aucune taille minimale",
    "jamais coupé", "jamais tronqué", "non bloquant",
)


def test_l_ecran_ne_recite_plus_le_vocabulaire_du_dossier():
    """FUITE Nº1 DU CONTRÔLE : « le bloc de relevé répond, dans les mots exacts
    du dossier, à 5 des 7 critères ». Le panneau nommait le barème ; il nomme
    maintenant des millimètres, des points et des signes.

    Ce test lit les CHAÎNES AFFICHÉES (commentaires ôtés) : le code peut garder
    ses noms internes — `read_pt`, `under_read` — c'est l'écran qui parle au
    client."""
    textes = _textes_affiches()
    for mot in BAREME_MOTS:
        fautes = [t for t in textes if mot in t]
        assert not fautes, f"« {mot} » est affiché : {fautes[:3]}"


def test_aucun_chiffre_mesure_n_a_quitte_l_ecran():
    """Le corollaire, et le vrai risque de la manœuvre : nettoyer la prose en
    emportant les mesures. Chaque grandeur que la planche montrait est
    retrouvée ici, dans sa nouvelle phrase — nombre de signes, corps composé
    ET demandé, corps le plus petit, distance à la coupe, définition, compte de
    polices, pavé d'encre, séries."""
    src = _js()
    # le compte de signes : DEUX comptes au lieu d'un zéro
    assert 'hero.m.posed + " des " + hero.m.srcn + " signes composés' in src
    assert "srcn: flat(text), posed: flat(posed)," in src
    # le corps composé, le corps demandé, le corps mini, le corps réglé
    assert 'fx(pt, 1) + " pt (" + fx(pxOfPt(pt, g || CF.geom()), 1) + " px)"' in src
    assert '", demandé " + fx(hero.s.size_pt, 1) + " pt"' in src
    assert '" · corps mini " + fx(hero.s.min_pt, 1) + " pt atteint"' in src
    assert 'fx(hero.m.read_pt, 1)' in src
    assert '" · corps le plus petit " + fx(ptMin, 1) + " pt"' in src
    # les millimètres, les pixels, la règle de conversion et la définition
    assert "' · 1 mm = ' + fx(g.mm2px(1), 3) + ' px à ' + g.dpi + ' DPI</p>'" in src
    assert "g.safe_px[0] + ' x ' + g.safe_px[1] + ' px'" in src
    # le compte de polices, mesuré et catalogué
    assert 'fp.dist + " police(s) posée(s) sur les "' in src
    # le pavé d'encre relu sur le PNG, ses deux bornes
    assert "px d'encre totale (α &gt; 0)" in src
    assert "px de corps plein (α ≥ 250)" in src
    # la série : les deux totaux
    assert 'SERIES.srcn.toLocaleString("fr-FR") + " signes demandés, "' in src


def test_l_encre_est_SITUEE_en_millimetres_du_bord_de_coupe():
    """Le remplacement, et pourquoi il vaut mieux que ce qu'il remplace.
    « dans la zone sûre » demandait qu'on croie un oui ; « l'encre s'arrête à
    4,26 mm du bord de coupe » se vérifie à la règle sur l'épreuve, et prévient
    AVANT que la marge soit franchie. Les deux rectangles viennent de la
    géométrie qui a rendu le fichier, l'encre de la mise en page qui l'a
    dessinée : la soustraction se refait à la main."""
    src = _js()
    assert "function trimRectPx(g)" in src
    assert "return [g.bleed_off_px[0], g.bleed_off_px[1], g.trim_px[0], g.trim_px[1]];" in src
    assert "function trimClearMm(rect, g)" in src
    assert "* 25.4 / g.dpi;" in src
    assert "function clearTxt(rect, g, bad)" in src
    assert '"l\'encre s\'arrête à " + fx(c, 2) + " mm du bord de coupe"' in src
    # le cas où la lame passe DANS le texte est nommé, avec son chiffre
    assert '"<b>l\'encre passe " + fx(-c, 2) + " mm sous la lame</b>"' in src
    # et le relevé nomme le bloc le plus proche du bord, avec sa distance
    assert '" · encre la plus proche de la coupe " + fx(pres.c, 2) + " mm (« "' in src


def test_le_memo_clavier_ne_s_imprime_plus_sur_le_panneau():
    """Trois lignes d'écran servaient à redire ce que la souris apprend en une
    seconde — et elles nommaient, une à une, les manipulations attendues. Le
    mémo est replié : il reste dans le DOM, à un clic, et la place revient à la
    liste des blocs."""
    src = _js()
    assert '<details class="cf-type-keys"><summary>Raccourcis</summary>' in src
    assert "<b>Ctrl+D</b> duplique" in src, "le mémo a été supprimé au lieu d'être replié"
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-type-keys > summary" in css


def test_la_casse_titre_ne_capitalise_pas_apres_l_apostrophe():
    """VRAI DÉFAUT TROUVÉ EN DURCISSANT : « marée d'encre » en capitales
    initiales sortait « Marée D'Encre ». L'apostrophe était traitée comme une
    espace, donc `encre` passait pour un mot neuf — faux dans toutes les
    langues qui élident, et imprimé sur la carte.

    Les deux moteurs sont corrigés ENSEMBLE : celui du backend et celui de
    l'écran partagent la même classe de coupure."""
    assert TY.apply_case("marée d'encre", "title") == "Marée D'encre"
    assert TY.apply_case("l'ORACLE des profondeurs", "title") == "L'oracle Des Profondeurs"
    assert TY.apply_case("qu'importe", "title") == "Qu'importe"
    # les vraies coupures restent des coupures
    assert TY.apply_case("(petit texte)", "title") == "(Petit Texte)"
    # et les accents ne bougent pas d'un iota
    assert TY.apply_case("créature légendaire", "title") == "Créature Légendaire"
    # miroir de l'écran : la même classe de caractères, l'apostrophe hors jeu
    src = _js()
    i = src.index("function applyCase(t, caps)")
    corps = src[i:i + 420]
    assert "'" not in corps.split("caps === \"title\"", 1)[1].split(")/g", 1)[0], \
        "l'apostrophe est redevenue une coupure de mot à l'écran"


def test_le_remede_essaie_UNE_AUTRE_POLICE_et_ne_mesure_que_les_posees():
    """MANQUE NOMMÉ PAR LE PREMIER CRITIQUE : « aucune des sorties qui
    sauveraient la pièce n'a été tentée — agrandir la boîte, réduire
    l'interlettrage, PROPOSER UNE POLICE PLUS ÉTROITE parmi les 23 servies ».

    Le levier existe et il est MESURÉ par le moteur qui dessine. Deux
    garde-fous, sans quoi le chiffre publié ne vaudrait rien : on n'essaie
    qu'une famille réellement posée (fichier chargé ET chasse différente du
    repli du système — sinon on mesurerait le repli et on l'annoncerait sous un
    autre nom), et jamais une famille à qui il manque un signe du texte."""
    src = _js()
    assert 'FONT_STATE[f.id] === "ok" && FONT_MEAS[f.id] === true' in src
    assert "!tofuOf(Object.assign(clone(slot), { font: f.id }), text).length" in src
    assert 'maxPtWith(ctx, base, g, text, { font: f.id }, lo, hi)' in src
    assert '"changer de police pour « " + esc(bf.f.label)' in src
    assert '" familles essayées qui savent écrire ce texte</i>"' in src
    # le bouton n'est offert que si la famille ATTEINT la cible mesurée
    assert "patch: okf ? { font: bf.f.id } : null" in src
    # et les polices sont chargées avant d'être mesurées, sinon on mesure le repli
    assert "if (fautif && !fontsForFix)" in src
    assert "ensureFonts(FONTS.map((f) => f.id)).then(() => {" in src


def test_un_seul_bouton_applique_la_sortie_qui_suffit():
    """« Un signalement n'est pas une correction : au tirage, la carte reste
    fausse, la seule différence est que l'imprimeur a été prévenu. »

    Le panneau mesurait cinq sorties et laissait choisir. Il porte désormais un
    bouton qui applique la première sortie MESURÉE qui suffit — avec, s'il le
    faut, le préalable de corps demandé, en une seule mise en page. Il écarte
    la boîte quand elle mordrait un bloc voisin (ce serait échanger un défaut
    contre un autre), sauf si elle est la seule à suffire. Et il ne s'affiche
    PAS quand rien ne suffit : pas de bouton qui promette sans tenir."""
    src = _js()
    assert "function autoLever(r)" in src
    assert "const suff = r.levers.filter((l) => l.ok && !l.info && l.patch);" in src
    assert "if (!suff.length) return null;" in src
    assert "const doux = suff.filter((l) => !l.heurt);" in src
    assert 'const pre = r.levers.filter((l) => l.info && l.patch && l.k === "size")[0];' in src
    assert "patch: Object.assign({}, pre ? pre.patch : null, best.patch)," in src
    # le bouton n'existe que si autoLever a trouvé quelque chose
    assert "const auto = autoLever(r);" in src
    assert "(auto ? ' <button class=\"cf-type-fixgo\"" in src
    # et il passe par le MÊME chemin de vérification que les boutons unitaires
    i = src.index('el.querySelectorAll(".cf-type-fixgo")')
    corps = src[i:i + 600]
    assert "PENDING = { id: row.id, label: row.label, target: row.target," in corps
    assert "patchSlot(row.id, a.patch);" in corps
    assert ".cf-type-fixgo {" in CSS.read_text(encoding="utf-8")


def test_les_reglages_du_domaine_passent_devant_les_replis(tmp_path):
    """MANQUE NOMMÉ PAR LES DEUX CRITIQUES : « aucun contrôle de casse,
    d'alignement horizontal ou vertical, de contour ni d'ombre portée
    n'apparaît sur le panneau de réglages ». Ils existaient tous — sous six
    lignes de champs numériques et dans un groupe replié, c'est-à-dire nulle
    part pour qui ouvre le panneau.

    Aucun réglage n'a été retiré : ils ont changé de rang. Ce que touche un
    typographe passe devant, ce qu'on règle une fois passe derrière.

    LU SUR LE PANNEAU RENDU, plus sur l'ordre des lignes du fichier (3b-T2) :
    depuis que la plaque et la boîte sont partagées avec le calque d'image,
    leur code vit AVANT `renderInsp` alors qu'elles s'affichent APRÈS. L'ordre
    du fichier ne disait donc plus l'ordre de l'écran — et c'est l'ordre de
    l'écran que ce test défend."""
    corps = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False),
                                              "sel": "titre"}})["insp"]
    ordre = [corps.index(">Alignement<"), corps.index(">Vertical<"),
             corps.index(">Casse<"), corps.index("<summary>Contour, ombre, arc</summary>"),
             corps.index("<summary>Opacité, justification</summary>"),
             corps.index("<summary>Boîte")]
    assert ordre == sorted(ordre), "l'ordre de l'inspecteur a changé"
    # les six réglages nommés sont AVANT le groupe replié, et le groupe
    # contour/ombre/arc est ouvert par défaut
    assert corps.index(">Casse<") < corps.index("<summary>Opacité, justification</summary>")
    assert '<details class="grp cf-type-grp" open><summary>Contour, ombre, arc</summary>' in corps
    # et rien n'a disparu : les onze réglages nommés par la spec sont là — la
    # police par son bouton d'aperçu, les autres par leur champ ou leur segment
    assert 'class="btn cf-type-font"' in corps
    assert "font-family:'CFT" in corps, "le nom n'est plus écrit dans sa fonte"
    assert 'class="cf-type-col"' in corps, "le sélecteur de couleur a disparu"
    for k in REGLAGES_NOMMES:
        if k in ("font", "color"):     # bouton d'aperçu · sélecteur de couleur
            continue
        assert 'data-k="' + k + '"' in corps, k


# ════════ 9. LA PLAQUE DE FOND D'UN SLOT — JUGÉE SUR DES PIXELS ════════════
# Le banc de la section 8 NOTE les appels de dessin : il sait dire quels
# glyphes ont été posés, il ne sait RIEN dire d'un recouvrement. Or c'est
# exactement l'enjeu d'une plaque de fond : dessinée après le texte, elle
# l'efface — et un banc qui n'enregistre que `fillText` ne verrait jamais la
# différence. Celui-ci COMPOSITE pour de vrai, source-over et alpha compris,
# dans un tampon RGBA, et le verdict se prend au pixel.
#
# Les glyphes y sont des pavés pleins de la chasse mesurée : ce qu'on juge
# n'est pas la forme d'un « e » — le banc n'a pas de fonte — c'est QUI
# RECOUVRE QUOI, et avec quel alpha. Le painter dessiné est le vrai, chargé
# depuis `mod-type.js` ; rien n'est réimplémenté.

BANC_PLAQUE = r"""
import { readFileSync } from "node:fs";
const SRC = readFileSync(process.argv[2], "utf8");
const OPT = JSON.parse(readFileSync(process.argv[3], "utf8"));

const W = { " ": 0.26, "i": 0.28, "l": 0.28, "j": 0.28, "t": 0.34, "f": 0.34, "r": 0.36,
  ".": 0.28, ",": 0.28, "'": 0.2, "’": 0.2, "-": 0.33, "m": 0.85, "w": 0.75,
  "M": 0.9, "W": 0.95 };
const wOf = (ch) => (W[ch] !== undefined ? W[ch] : (ch >= "A" && ch <= "Z" ? 0.62 : 0.5));

function hexOf(s) {
  let h = String(s == null ? "" : s).trim();
  if (h[0] === "#") h = h.slice(1);
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  if (h.length !== 6 && h.length !== 8) return null;
  const v = (i) => parseInt(h.slice(i, i + 2), 16);
  return [v(0), v(2), v(4), h.length === 8 ? v(6) / 255 : 1];
}

/* ── LE CONTEXTE 2D QUI COMPOSITE VRAIMENT ──────────────────────────────
   Transformations affines completes (la rotation d'un slot et l'arc les
   utilisent), pile save/restore, source-over non premultiplie — c'est ce
   que rend `getImageData` d'une vraie toile. */
function makeCtx(w, h) {
  const buf = new Uint8ClampedArray(w * h * 4);
  const texts = [];
  const labels = [];
  const draws = [];
  let S = { alpha: 1, fill: "#000000", stroke: "#000000", size: 10, font: "",
    m: [1, 0, 0, 1, 0, 0], clip: null };
  const stack = [];
  const mul = (a, b) => [
    a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1],
    a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
    a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5]];
  const app = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  function invOf(m) {
    const d = m[0] * m[3] - m[1] * m[2];
    return [m[3] / d, -m[1] / d, -m[2] / d, m[0] / d,
      (m[2] * m[5] - m[3] * m[4]) / d, (m[1] * m[4] - m[0] * m[5]) / d];
  }
  function inRR(x, r, px, py) {
    if (px < x[0] || py < x[1] || px >= x[0] + x[2] || py >= x[1] + x[3]) return false;
    if (r <= 0) return true;
    const cx = Math.min(Math.max(px, x[0] + r), x[0] + x[2] - r);
    const cy = Math.min(Math.max(py, x[1] + r), x[1] + x[3] - r);
    const dx = px - cx, dy = py - cy;
    return dx * dx + dy * dy <= r * r;
  }
  /* LE CHEMIN ACCUMULE, teste par PARITE DE TRAVERSEES. Le contour de
     `platePath` est simple et ferme : la parite suffit, et elle ne suppose
     RIEN de la forme — c'est ce qui rend la comparaison avec `inRR` honnete
     (deux rasterisations independantes du meme trace, pas la meme deux fois). */
  function inPoly(P, px, py) {
    let dedans = false;
    for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
      if ((P[i][1] > py) !== (P[j][1] > py)
        && px < (P[j][0] - P[i][0]) * (py - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0]) {
        dedans = !dedans;
      }
    }
    return dedans;
  }
  /* un rectangle (eventuellement arrondi) EXPRIME EN COORDONNEES LOCALES,
     rasterise a travers la transformation courante : chaque pixel de la boite
     englobante est ramene en local par la transformation inverse. */
  function fillLocal(rect, r, col, alpha, out, poly) {
    const c = hexOf(col);
    if (!c) return null;
    const a = Math.max(0, Math.min(1, alpha * c[3]));
    if (a <= 0) return null;
    const pts = (poly || [[rect[0], rect[1]], [rect[0] + rect[2], rect[1]],
      [rect[0], rect[1] + rect[3]], [rect[0] + rect[2], rect[1] + rect[3]]])
      .map((p) => app(S.m, p[0], p[1]));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const x0 = Math.max(0, Math.floor(Math.min.apply(null, xs)));
    const y0 = Math.max(0, Math.floor(Math.min.apply(null, ys)));
    const x1 = Math.min(w, Math.ceil(Math.max.apply(null, xs)));
    const y1 = Math.min(h, Math.ceil(Math.max.apply(null, ys)));
    const iv = invOf(S.m);
    /* LA FENETRE DE DECOUPE, s'il y en a une : un `clip()` pose un rectangle
       EN COORDONNEES LOCALES du moment ou il a ete appele — on le retraverse
       donc par SA propre transformation, pas par celle d'aujourd'hui. C'est ce
       qui permet de mesurer que « cover » ne deborde pas de la boite. */
    const cl = S.clip ? { r: S.clip.r, iv: invOf(S.clip.m) } : null;
    for (let py = y0; py < y1; py++) {
      for (let px = x0; px < x1; px++) {
        const lx = iv[0] * (px + 0.5) + iv[2] * (py + 0.5) + iv[4];
        const ly = iv[1] * (px + 0.5) + iv[3] * (py + 0.5) + iv[5];
        if (!(poly ? inPoly(poly, lx, ly) : inRR(rect, r, lx, ly))) continue;
        if (cl) {
          const gx = cl.iv[0] * (px + 0.5) + cl.iv[2] * (py + 0.5) + cl.iv[4];
          const gy = cl.iv[1] * (px + 0.5) + cl.iv[3] * (py + 0.5) + cl.iv[5];
          if (gx < cl.r[0] || gy < cl.r[1] || gx >= cl.r[0] + cl.r[2]
            || gy >= cl.r[1] + cl.r[3]) continue;
        }
        /* le pave REELLEMENT peint, pixel par pixel : c'est lui, et non le
           rectangle demande, qui dit si la decoupe a mordu. */
        if (out) {
          if (px < out.x0) out.x0 = px; if (px > out.x1) out.x1 = px;
          if (py < out.y0) out.y0 = py; if (py > out.y1) out.y1 = py;
        }
        const i = (py * w + px) << 2;
        const da = buf[i + 3] / 255;
        const na = a + da * (1 - a);
        if (na <= 0) continue;
        for (let k = 0; k < 3; k++) {
          buf[i + k] = (c[k] * a + buf[i + k] * da * (1 - a)) / na;
        }
        buf[i + 3] = Math.round(na * 255);
      }
    }
    return [x0, y0, Math.max(0, x1 - x0), Math.max(0, y1 - y0)];
  }
  const c = {
    _font: "", canvas: { width: w, height: h },
    save() { stack.push(Object.assign({}, S, { m: S.m.slice() })); },
    restore() { if (stack.length) S = stack.pop(); },
    translate(x, y) { S.m = mul(S.m, [1, 0, 0, 1, x, y]); },
    rotate(t) { S.m = mul(S.m, [Math.cos(t), Math.sin(t), -Math.sin(t), Math.cos(t), 0, 0]); },
    setTransform(a, b, cc, d, e, f) { S.m = [a, b, cc, d, e, f]; },
    clearRect() { },
    beginPath() { c._path = null; c._poly = null; },
    quadraticCurveTo() { },
    /* ── LE CHEMIN ACCUMULE (dette « branche arcTo », 3a/3b) ────────────────
       `platePath` a DEUX branches : `roundRect` quand la toile l'offre, et
       quatre raccords d'arc sinon. La seconde n'avait jamais rasterise ici —
       moveTo/arcTo/closePath etaient des coquilles vides — donc le repli
       d'un moteur sans `roundRect` n'etait couvert par aucun pixel.
       `arcTo` AU SENS DE LA TOILE : un raccord de rayon r tangent aux deux
       segments P0->P1 et P1->P2. On calcule les deux points de tangence et le
       centre, puis on aplatit l'arc en 16 cordes — c'est cette approximation,
       et elle seule, qui autorise l'ecart de coin mesure par le test. */
    moveTo(x, y) { c._path = null; c._poly = [[x, y]]; },
    lineTo(x, y) { if (c._poly) c._poly.push([x, y]); },
    arcTo(x1, y1, x2, y2, r) {
      const P = c._poly;
      if (!P || !P.length) return;
      const p0 = P[P.length - 1];
      const nz = (ax, ay) => { const L = Math.hypot(ax, ay) || 1; return [ax / L, ay / L]; };
      const u = nz(p0[0] - x1, p0[1] - y1), v = nz(x2 - x1, y2 - y1);
      const phi = Math.acos(Math.max(-1, Math.min(1, u[0] * v[0] + u[1] * v[1])));
      if (!(phi > 1e-9) || !(r > 0)) { P.push([x1, y1]); return; }
      const d = r / Math.tan(phi / 2), h = r / Math.sin(phi / 2);
      const m = nz(u[0] + v[0], u[1] + v[1]);
      const cx = x1 + m[0] * h, cy = y1 + m[1] * h;
      const a0 = Math.atan2(y1 + u[1] * d - cy, x1 + u[0] * d - cx);
      let a1 = Math.atan2(y1 + v[1] * d - cy, x1 + v[0] * d - cx);
      if (a1 - a0 > Math.PI) a1 -= 2 * Math.PI;
      if (a0 - a1 > Math.PI) a1 += 2 * Math.PI;
      for (let k = 0; k <= 16; k++) {
        const t = a0 + (a1 - a0) * k / 16;
        P.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]);
      }
    },
    closePath() { if (c._poly && c._poly.length) c._poly.push(c._poly[0].slice()); },
    rect(x, y, ww, hh) { c._poly = null; c._path = { r: [x, y, ww, hh], k: 0 }; },
    /* ── L'ELLIPSE, APLATIE EN CORDES (phase 5 T2-B) ────────────────────────
       Meme parti que `arcTo` juste au-dessus : le banc n'a pas de moteur de
       courbes, il aplatit. 128 cordes sur un tour — a 300 DPI le plus grand
       demi-axe d'une carte fait ~520 px, donc la fleche de corde vaut
       r*(1-cos(pi/128)) < 0,16 px : sous le pixel, donc invisible pour une
       sonde. C'est cette approximation, et elle seule, qui autorise la
       tolerance d'IoU du test. */
    ellipse(cx, cy, rx, ry, rot, a0, a1) {
      const P = [];
      const co = Math.cos(rot || 0), si = Math.sin(rot || 0);
      for (let k = 0; k <= 128; k++) {
        const t = (a0 || 0) + ((a1 === undefined ? Math.PI * 2 : a1) - (a0 || 0)) * k / 128;
        const ex = rx * Math.cos(t), ey = ry * Math.sin(t);
        P.push([cx + ex * co - ey * si, cy + ex * si + ey * co]);
      }
      c._path = null; c._poly = P;
    },
    arc(cx, cy, r, a0, a1) { c.ellipse(cx, cy, r, r, 0, a0, a1); },
    /* ── LE TRAIT, RASTERISE COMME UN RUBAN ─────────────────────────────────
       Une toile trace un contour ; ce banc n'en a pas. Chaque segment devient
       le QUADRILATERE de largeur `lineWidth` centre dessus (bout carre), et
       chaque sommet interieur recoit un carre de raccord — c'est la jointure
       « round » approchee au carre, une demi-largeur de cote. Ce qu'on mesure
       ici n'est pas la finesse d'une jointure : c'est OU l'encre tombe. */
    stroke() {
      const w = Math.max(0.6, Number(c.lineWidth) || 1);
      let P = c._poly;
      if (!P && c._path) {
        const r = c._path.r;
        P = [[r[0], r[1]], [r[0] + r[2], r[1]], [r[0] + r[2], r[1] + r[3]],
          [r[0], r[1] + r[3]], [r[0], r[1]]];
      }
      if (!P || P.length < 2) return;
      const h = w / 2;
      for (let i = 1; i < P.length; i++) {
        const a = P[i - 1], b = P[i];
        const dx = b[0] - a[0], dy = b[1] - a[1];
        const L = Math.hypot(dx, dy);
        if (!(L > 1e-9)) continue;
        const nx = -dy / L * h, ny = dx / L * h;
        fillLocal(null, 0, S.stroke, S.alpha, null,
          [[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny],
            [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny]]);
        if (i < P.length - 1) {
          fillLocal([b[0] - h, b[1] - h, w, w], 0, S.stroke, S.alpha);
        }
      }
    },
    roundRect(x, y, ww, hh, rr) {
      const v = Array.isArray(rr) ? Number(rr[0]) : Number(rr);
      c._poly = null;
      c._path = { r: [x, y, ww, hh], k: isFinite(v) ? v : 0 };
    },
    fill() {
      if (c._path) { fillLocal(c._path.r, c._path.k, S.fill, S.alpha); return; }
      if (c._poly && c._poly.length > 2) fillLocal(null, 0, S.fill, S.alpha, null, c._poly);
    },
    /* le damier de l'image absente peint des rectangles NUS, sans chemin. */
    fillRect(x, y, ww, hh) { fillLocal([x, y, ww, hh], 0, S.fill, S.alpha); },
    /* la fenetre de decoupe : le chemin courant, GARDE avec la transformation
       qui l'a trace (c'est ainsi qu'une toile la retient). */
    clip() { if (c._path) S.clip = { r: c._path.r.slice(), m: S.m.slice() }; },
    /* L'IMAGE DE PAILLE EST UN APLAT. Ce que ce banc doit trancher n'est pas
       le dessin d'une illustration mais SA BOITE DE DESTINATION et les pixels
       qu'elle couvre vraiment — donc le `fit`, la decoupe, l'ordre avec la
       plaque et l'opacite. On note l'appel ET le pave peint. */
    drawImage(im, dx, dy, dw, dh) {
      const out = { x0: 1e9, y0: 1e9, x1: -1, y1: -1 };
      fillLocal([dx, dy, dw, dh], 0, (im && im._hex) || "#20c0ff", S.alpha, out);
      draws.push({ dest: [dx, dy, dw, dh], alpha: S.alpha,
        peint: out.x1 < 0 ? null : [out.x0, out.y0, out.x1 - out.x0 + 1, out.y1 - out.y0 + 1] });
    },
    measureText(s) {
      let ww = 0;
      for (const ch of String(s)) ww += wOf(ch) * S.size;
      return { width: ww, actualBoundingBoxAscent: S.size * 0.72,
        actualBoundingBoxDescent: S.size * 0.21 };
    },
    /* UN GLYPHE = SON PAVE D'ENCRE. Le banc n'a pas de fonte ; ce qu'il doit
       trancher n'est pas le dessin d'un « e » mais l'ORDRE de composition. */
    fillText(t, x, y) {
      const ww = c.measureText(t).width;
      if (!(ww > 0)) return;
      const r = fillLocal([x, y - S.size * 0.72, ww, S.size * 0.93], 0, S.fill, S.alpha);
      if (r) texts.push(r);
      labels.push(String(t));
    },
    /* le contour est peint AVANT le remplissage par `drawSlot`, au meme
       endroit : le peindre ici doublerait le pave sans rien apprendre. */
    strokeText() { },
  };
  Object.defineProperty(c, "font", { get() { return c._font; },
    set(v) { c._font = v; const m = /([\d.]+)px/.exec(v); if (m) S.size = parseFloat(m[1]); } });
  Object.defineProperty(c, "globalAlpha", { get() { return S.alpha; },
    set(v) { S.alpha = Number(v); } });
  Object.defineProperty(c, "fillStyle", { get() { return S.fill; }, set(v) { S.fill = v; } });
  Object.defineProperty(c, "strokeStyle", { get() { return S.stroke; }, set(v) { S.stroke = v; } });
  ["lineWidth", "lineJoin", "miterLimit", "textAlign", "textBaseline",
    "shadowColor", "shadowBlur", "shadowOffsetX", "shadowOffsetY",
    "globalCompositeOperation"].forEach((k) => { c[k] = null; });
  /* UN MOTEUR SANS `roundRect` — l'etat d'un navigateur, pas un reglage du
     produit : on RETIRE la methode du contexte, exactement comme si elle
     n'avait jamais existe. C'est ainsi que la seconde branche de `platePath`
     se met a peindre, sans qu'une ligne du module ait bouge. */
  if (OPT.sans_arrondi) delete c.roundRect;
  c._buf = buf; c._texts = texts; c._labels = labels; c._draws = draws;
  c._at = (x, y) => {
    const i = ((y | 0) * w + (x | 0)) << 2;
    return [buf[i], buf[i + 1], buf[i + 2], buf[i + 3]];
  };
  return c;
}

function geom(fmt_mm, dpi, bleed_mm, safe_mm) {
  const R = (x) => Math.floor(Number(x.toFixed(9)) + 0.5);
  const px = (mm) => R(mm / 25.4 * dpi);
  const canvas_px = [px(fmt_mm[0] + 2 * bleed_mm), px(fmt_mm[1] + 2 * bleed_mm)];
  const trim_px = [px(fmt_mm[0]), px(fmt_mm[1])];
  const bleed_off_px = [(canvas_px[0] - trim_px[0]) / 2, (canvas_px[1] - trim_px[1]) / 2];
  const safe_px = [px(fmt_mm[0] - 2 * safe_mm), px(fmt_mm[1] - 2 * safe_mm)];
  const safe_off_px = [bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2,
    bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2];
  return { fmt: "poker_eu", label: "Poker", dpi: dpi, canvas_px, trim_px, bleed_off_px,
    safe_px, safe_off_px, bleed_mm, safe_mm, mm2px: (v) => v / 25.4 * dpi,
    px2mm: (v) => v * 25.4 / dpi };
}
const G = geom([63, 88], 300, 3, 3);
const DOC = { type: { optical_mm: 0.5 } };
let MOD = null;
/* ── LES IMAGES DE DECK, SERVIES PAR LE BANC ──────────────────────────────
   `OPT.images = {"img_1.png": [w, h, "#hex"]}`. Un nom ABSENT de cette table
   se comporte comme un 404 : c'est ainsi qu'on eprouve l'etat « image
   absente » sans inventer un drapeau que le module ne connaitrait pas. */
class ImageStub {
  constructor() { this._src = ""; this.decoding = ""; }
  set src(v) {
    this._src = String(v);
    const m = /(img_\d+\.png)/.exec(this._src);
    const spec = (OPT.images || {})[m ? m[1] : ""] || null;
    setTimeout(() => {
      if (!spec) { if (this.onerror) this.onerror(new Error("404")); return; }
      this.naturalWidth = spec[0]; this.naturalHeight = spec[1];
      this.width = spec[0]; this.height = spec[1];
      this._hex = spec[2] || "#20c0ff";
      if (this.onload) this.onload();
    }, 0);
  }
  get src() { return this._src; }
}
globalThis.Image = ImageStub;
const urls = [];
const CF = {
  register(cfg) {
    MOD = cfg;
    return { patch: (p) => Object.assign(DOC.type, p),
      api: { get: async () => ({}), post: async () => ({}),
        url: (sub) => { urls.push(String(sub)); return "/api/cards/deck_00000000/type/" + sub; } },
      emit() { }, slot() { }, aside() { }, invalidate() { }, toast() { }, busy() { }, on() { } };
  },
  get(path, def) {
    let v = DOC;
    for (const p of String(path).split(".")) { if (v == null) return def; v = v[p]; }
    return v === undefined ? def : v;
  },
  geom: () => G, current: () => 0, cards: () => [], card: () => ({ fields: {} }),
  on() { }, renderCard: async () => null, modules: () => [],
};
globalThis.window = { CF: CF, addEventListener() { } };
globalThis.document = {
  createElement: () => ({ width: 0, height: 0, getContext: () => makeCtx(8, 8), style: {},
    appendChild() { }, addEventListener() { }, remove() { }, querySelector: () => null,
    querySelectorAll: () => [],
    classList: { add() { }, remove() { }, toggle() { }, contains: () => false } }),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() { },
  body: { appendChild() { } }, fonts: { add() { } },
};
const boom = [];
process.on("uncaughtException", (e) => { boom.push(String((e && e.message) || e)); });
(0, eval)(SRC);

const BASE = { id: "rules", label: "Encadre", on: true, side: "front",
  box: [4.5, 55, 54, 18], font: "IBMPlexSans", size_pt: 8, min_pt: 4.5,
  color: "#efe7d6", align: "left", valign: "top", track: 0, leading: 1.22,
  hyphen: false, caps: "none", bold: false, italic: false, outline: 0,
  outline_color: "#0a0a0c", shadow: 0, shadow_color: "#000000", shadow_dx: 0,
  shadow_dy: 0, rotate: 0, arc: 0, autofit: true, wrap: true, opacity: 100,
  just_max: 133, last_pct: 25, plate_color: null, plate_alpha: 1,
  plate_radius: 0, text: "" };
/* `kind`, `src` et `fit` ne sont PAS dans BASE : un document d'AVANT la 3b ne
   les porte pas, et c'est ce cas-la que la non-regression doit voir. Un slot
   d'image les nomme explicitement dans OPT.slots. */

const slots = (OPT.slots || [{}]).map((s) => {
  const o = Object.assign({}, BASE, s);
  (OPT.drop || []).forEach((k) => { delete o[k]; });
  return o;
});
const ctx = makeCtx(G.canvas_px[0], G.canvas_px[1]);
const painter = MOD.painters.filter((p) => p.z === 60)[0];
/* `OPT.passes` : rejouer le painter sur le MEME contexte, comme le CORE le
   fait a chaque frame. C'est ainsi qu'on mesure ce qu'un cache evite. */
for (let pass = 0; pass < Math.max(1, OPT.passes || 1); pass++) {
  await painter.fn(ctx, G, { type: { slots: slots } }, { fields: {} }, "front");
  await new Promise((r) => setTimeout(r, 60));
}
await new Promise((r) => setTimeout(r, 200));

/* FNV-1a sur tout le tampon : deux rendus identiques au bit pres rendent la
   meme empreinte, et un pixel de difference la change. */
let hs = 0x811c9dc5;
for (let i = 0; i < ctx._buf.length; i++) {
  hs ^= ctx._buf[i]; hs = Math.imul(hs, 0x01000193) >>> 0;
}
const boxOf = (s) => [G.bleed_off_px[0] + G.mm2px(s.box[0]),
  G.bleed_off_px[1] + G.mm2px(s.box[1]), G.mm2px(s.box[2]), G.mm2px(s.box[3])];
/* UN POINT DE LA BOITE QU'AUCUN GLYPHE NE TOUCHE : c'est la que la plaque se
   lit toute seule. Cherche, jamais suppose — le texte remplit ce qu'il veut.
   On sonde la COLONNE CENTRALE, en remontant depuis le bas : un coin arrondi
   n'y mord jamais (le rayon sature a la moitie de la largeur), et le bas d'une
   boite est ce que le texte laisse libre en premier. */
function freePoint(b) {
  const rs = ctx._texts;
  const px = Math.floor(b[0] + b[2] / 2);
  for (let dy = 3; dy < b[3] - 2; dy++) {
    const py = Math.floor(b[1] + b[3] - 2 - dy);
    let libre = true;
    for (const r of rs) {
      if (px >= r[0] - 1 && px <= r[0] + r[2] + 1
        && py >= r[1] - 1 && py <= r[1] + r[3] + 1) { libre = false; break; }
    }
    if (libre) return [px, py];
  }
  return null;
}
/* L'EMPREINTE, LIGNE PAR LIGNE : pour chaque rangee de pixels de la boite, le
   premier peint, le dernier peint, et combien. Deux traces du MEME contour
   rendent la meme empreinte ; un repli qui derive se lit alors en pixels, a la
   ligne pres — au lieu d'etre noye dans une empreinte globale qui dit
   seulement « ce n'est pas identique » sans dire de combien ni ou. */
function empreinte(b) {
  const x0 = Math.max(0, Math.floor(b[0]) - 2);
  const x1 = Math.min(G.canvas_px[0], Math.ceil(b[0] + b[2]) + 2);
  const y0 = Math.max(0, Math.floor(b[1]) - 2);
  const y1 = Math.min(G.canvas_px[1], Math.ceil(b[1] + b[3]) + 2);
  const l = [];
  for (let py = y0; py < y1; py++) {
    let a = -1, z = -1, n = 0;
    for (let px = x0; px < x1; px++) {
      if (ctx._at(px, py)[3] > 0) { if (a < 0) a = px; z = px; n++; }
    }
    l.push([py, a, z, n]);
  }
  return l;
}
/* ── LES SONDES A VERITE CONNUE (phase 5 T2-B) ──────────────────────────────
   `OPT.points = {nom: [mm_x, mm_y]}` : la couleur RELUE au point de la carte
   que le test a calcule LUI-MEME, en millimetres depuis le coin de coupe. Le
   test ne demande jamais au code teste ou son encre est tombee ; il pose un
   point et regarde. */
const ptPx = (mm) => [Math.round(G.bleed_off_px[0] + G.mm2px(mm[0])),
  Math.round(G.bleed_off_px[1] + G.mm2px(mm[1]))];
const points = {};
Object.keys(OPT.points || {}).forEach((k) => {
  const p = ptPx(OPT.points[k]);
  points[k] = ctx._at(p[0], p[1]);
});
/* `OPT.pave = [x, y, w, h]` en mm : les EXTREMES des pixels encres dans cette
   fenetre. C'est la boite REELLEMENT peinte, pas celle qu'on a demandee. */
function paveDe(mm) {
  const a = ptPx([mm[0], mm[1]]), b = ptPx([mm[0] + mm[2], mm[1] + mm[3]]);
  const x0 = Math.max(0, a[0] - 6), y0 = Math.max(0, a[1] - 6);
  const x1 = Math.min(G.canvas_px[0], b[0] + 6), y1 = Math.min(G.canvas_px[1], b[1] + 6);
  let mnx = 1e9, mny = 1e9, mxx = -1, mxy = -1, n = 0;
  for (let py = y0; py < y1; py++) {
    for (let px = x0; px < x1; px++) {
      if (ctx._at(px, py)[3] === 0) continue;
      n++;
      if (px < mnx) mnx = px; if (px > mxx) mxx = px;
      if (py < mny) mny = py; if (py > mxy) mxy = py;
    }
  }
  return n ? { x: mnx, y: mny, w: mxx - mnx + 1, h: mxy - mny + 1, n: n }
    : { x: null, y: null, w: 0, h: 0, n: 0 };
}
/* `OPT.masque = [x, y, w, h]` en mm : le masque PEINT dans cette fenetre,
   confronte au DISQUE INSCRIT construit ici a la main (centre de la boite,
   rayon = demi-petit-cote). L'intersection sur l'union, chiffree. */
function masqueDe(mm) {
  const a = ptPx([mm[0], mm[1]]), b = ptPx([mm[0] + mm[2], mm[1] + mm[3]]);
  const cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
  const rx = (b[0] - a[0]) / 2, ry = (b[1] - a[1]) / 2;
  let inter = 0, union = 0, peints = 0, cellules = 0, attendus = 0;
  for (let py = a[1]; py < b[1]; py++) {
    for (let px = a[0]; px < b[0]; px++) {
      cellules++;
      const dx = (px + 0.5 - cx) / rx, dy = (py + 0.5 - cy) / ry;
      const dedans = (dx * dx + dy * dy) <= 1;
      const encre = ctx._at(px, py)[3] > 0;
      if (dedans) attendus++;
      if (encre) peints++;
      if (dedans && encre) inter++;
      if (dedans || encre) union++;
    }
  }
  return { peints: peints, attendus: attendus, cellules: cellules,
    iou: union ? Math.round(inter / union * 10000) / 10000 : 0 };
}
const rows = slots.map((s) => {
  const b = boxOf(s);
  const lib = freePoint(b);
  const t = ctx._texts[0];
  const gl = t ? [Math.floor(t[0] + t[2] / 2), Math.floor(t[1] + t[3] / 2)] : null;
  const co = [Math.floor(b[0]) + 2, Math.floor(b[1]) + 2];
  const ce = [Math.floor(b[0] + b[2] / 2), Math.floor(b[1] + b[3] / 2)];
  return { id: s.id, box: b.map((v) => Math.round(v * 100) / 100),
    libre: lib, libre_px: lib ? ctx._at(lib[0], lib[1]) : null,
    glyphe: gl, glyphe_px: gl ? ctx._at(gl[0], gl[1]) : null,
    coin: co, coin_px: ctx._at(co[0], co[1]),
    centre: ce, centre_px: ctx._at(ce[0], ce[1]) };
});
process.stdout.write(JSON.stringify({
  hash: hs.toString(16), n_textes: ctx._texts.length, slots: rows, exceptions: boom,
  /* `OPT.empreinte` seulement : la releve coute une passe sur la boite, et
     les quarante autres tests de ce banc n'en ont que faire. */
  empreinte: (OPT.empreinte && slots.length) ? empreinte(boxOf(slots[0])) : null,
  roundRect: typeof ctx.roundRect === "function",
  /* les APPELS D'IMAGE : boite de destination demandee, opacite en vigueur, et
     le pave REELLEMENT peint (qui dit si la decoupe a mordu). */
  draws: ctx._draws, labels: ctx._labels, urls: urls,
  /* les sondes a verite connue (phase 5 T2-B) */
  points: points,
  pave: OPT.pave ? paveDe(OPT.pave) : null,
  masque: OPT.masque ? masqueDe(OPT.masque) : null,
  /* le RELEVE du painter, ouvert par mutation (patron `__solo`) : c'est lui
     qui alimente les passes d'encre, donc c'est lui qui doit ignorer les
     calques d'image. */
  meas: globalThis.__meas ? Object.keys(globalThis.__meas()) : null,
}));
"""


def _banc_plaque(tmp_path, opts: dict, mutations=()) -> dict:
    """Fait tourner le painter z=60 sur un VRAI tampon de pixels et rend ce
    qu'il a composité. `mutations` casse une protection avant exécution : un
    test qui passerait aussi sur le code cassé ne prouverait rien."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de pixels ne peut pas tourner")
    src = JS.read_text(encoding="utf-8", newline="")   # newline='' : CRLF gardé
    for avant, apres in mutations:
        assert avant in src, f"mutation introuvable : {avant!r}"
        assert src.count(avant) == 1, f"mutation ambiguë : {avant!r}"
        src = src.replace(avant, apres)
    js = tmp_path / "mod-type-plaque.js"
    js.write_text(src, encoding="utf-8", newline="")
    banc = tmp_path / "banc-plaque.mjs"
    banc.write_text(BANC_PLAQUE, encoding="utf-8")
    conf = tmp_path / "opts-plaque.json"
    conf.write_text(json.dumps(opts, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    d = json.loads(r.stdout)
    assert d["exceptions"] == [], d["exceptions"]
    return d


PLAQUE_TXT = "Vol, celerite. A l'entree en jeu, revelez trois cartes."
PLAQUE_SLOT = {"text": PLAQUE_TXT, "plate_color": "#3050a0", "plate_alpha": 0.8,
               "plate_radius": 2.0}


def test_les_trois_reglages_de_plaque_sont_dans_les_deux_tables():
    """Le verrou de la pièce : le bloc JS est du JSON littéral et l'égalité
    avec le dictionnaire Python est STRICTE. Trois clés ajoutées d'un seul
    côté font rougir `test_les_defauts_de_slot_sont_les_memes_des_deux_cotes`
    — celui-ci nomme ce qu'elles valent, et que le défaut est NEUTRE."""
    js = json.loads(_bloc_js("DEFAULTS"))
    for k in ("plate_color", "plate_alpha", "plate_radius"):
        assert k in TY.SLOT_DEFAULTS, k
        assert k in js, k
        assert js[k] == TY.SLOT_DEFAULTS[k], k
    # NEUTRE PAR DEFAUT : pas de couleur = pas de plaque. C'est ce qui rend les
    # quatre gabarits existants byte-identiques après l'ajout.
    assert TY.SLOT_DEFAULTS["plate_color"] is None
    assert TY.SLOT_DEFAULTS["plate_alpha"] == 1.0
    assert TY.SLOT_DEFAULTS["plate_radius"] == 0.0
    # et le compte total suit (les deux tables sont comparées ailleurs) — 36 à
    # l'arrivée du verrou, 39 depuis le calque d'image de la 3b-T2, 49 depuis
    # les formes de la phase 5-T2.
    assert len(js) == 49, sorted(js)


def test_la_plaque_est_bornee_des_deux_cotes():
    """Un rayon hors bornes ne fait pas 500 et ne fait pas non plus une carte
    au hasard : il est RAMENÉ. Les bornes sont nommées, des deux côtés."""
    assert (TY.PLATE_RADIUS_MIN, TY.PLATE_RADIUS_MAX) == (0.0, 30.0)
    assert (TY.PLATE_ALPHA_MIN, TY.PLATE_ALPHA_MAX) == (0.0, 1.0)
    assert TY.norm_slot({"plate_radius": 999})["plate_radius"] == TY.PLATE_RADIUS_MAX
    assert TY.norm_slot({"plate_radius": -12})["plate_radius"] == TY.PLATE_RADIUS_MIN
    assert TY.norm_slot({"plate_radius": "large"})["plate_radius"] == 0.0
    assert TY.norm_slot({"plate_alpha": 42})["plate_alpha"] == 1.0
    assert TY.norm_slot({"plate_alpha": -1})["plate_alpha"] == 0.0
    assert TY.norm_slot({"plate_alpha": None})["plate_alpha"] == 1.0
    # la couleur : hex ou RIEN. « bleu » n'est pas une couleur pour une toile.
    assert TY.norm_slot({"plate_color": "#3050A0"})["plate_color"] == "#3050a0"
    assert TY.norm_slot({"plate_color": "#abc"})["plate_color"] == "#abc"
    assert TY.norm_slot({"plate_color": "bleu"})["plate_color"] is None
    assert TY.norm_slot({})["plate_color"] is None
    # et le corps mal formé traverse la route sans 500
    did = _did()
    r = _api("POST", f"/api/cards/{did}/type/layout",
             json={"slots": [{"id": "a", "plate_color": 17, "plate_alpha": "beaucoup",
                              "plate_radius": [1, 2]}]})
    assert r.status_code == 200, r.text
    # l'écran borne AUX MÊMES VALEURS — le painter reçoit des slots bruts, pas
    # normalisés : c'est lui qui doit tenir la borne (voir le test du coin).
    src = JS.read_text(encoding="utf-8")
    assert "const PLATE_RADIUS_MAX_MM = 30;" in src
    assert re.search(r"s\.plate_alpha = num\(r\.plate_alpha, 1, 0, 1\);", src)
    assert re.search(r"s\.plate_radius = num\(r\.plate_radius, 0, 0, PLATE_RADIUS_MAX_MM\);", src)


def test_la_plaque_est_peinte_SOUS_le_texte_du_slot(tmp_path):
    """LE TEST QUI COMPTE. Une plaque bleue à 80 % sous un encadré crème :

      · un pixel de la boîte qu'aucun glyphe ne touche est TEINTÉ — c'est la
        plaque, et son alpha est celui demandé (204/255, pas 255) ;
      · un pixel de CORPS DE GLYPHE porte encore la couleur du texte — donc la
        plaque est passée DESSOUS, pas dessus.

    Les deux mesures sortent du même tampon, composité par le vrai painter."""
    d = _banc_plaque(tmp_path, {"slots": [PLAQUE_SLOT]})
    row = d["slots"][0]
    assert d["n_textes"] > 0, "le banc n'a posé aucun texte"
    assert row["libre"], "aucun pixel de la boîte n'est libre de glyphe"
    r, g, b, a = row["libre_px"]
    assert (r, g, b) == (48, 80, 160), row          # #3050a0
    assert a == 204, row                            # 0,8 x 255, arrondi
    # ... et le texte est PAR-DESSUS : la couleur lue est celle de l'encre.
    gr, gg, gb, ga = row["glyphe_px"]
    assert (gr, gg, gb) == (239, 231, 214), row     # #efe7d6
    assert ga == 255, row

    # ── MUTATION 1 : la plaque après le texte. Le pixel de glyphe vire au
    # bleu — c'est le défaut que ce test existe pour attraper.
    apres = _banc_plaque(tmp_path, {"slots": [PLAQUE_SLOT]}, mutations=(
        ("    drawPlate(ctx, slot, g, m);\r\n    const strokeW = pxOfPt(slot.outline, g);",
         "    const strokeW = pxOfPt(slot.outline, g);"),
        # L'ANCRE VISE LA FIN DE `drawSlot`, ET ELLE LE DIT : depuis la phase
        # 5-T2, `drawShapeSlot` se termine sur les mêmes trois lignes et
        # l'ancre courte devenait ambiguë (mutation refusée par le banc — ce
        # qui est exactement ce qu'on lui demande de faire). Le `});` de la
        # boucle des passes d'encre, juste avant, appartient à `drawSlot` seul.
        ("   });\r\n    ctx.restore();\r\n  }\r\n",
         "   });\r\n    drawPlate(ctx, slot, g, m);\r\n    ctx.restore();\r\n  }\r\n"),
    ))
    mr, mg, mb = apres["slots"][0]["glyphe_px"][:3]
    assert (mr, mg, mb) != (239, 231, 214), \
        "plaque dessinée APRÈS le texte et le banc ne le voit pas"
    assert mb > mr, apres["slots"][0]      # le glyphe a viré au bleu de la plaque

    # ── MUTATION 2 : l'alpha ignoré. Le pixel libre devient opaque.
    sans_alpha = _banc_plaque(tmp_path, {"slots": [PLAQUE_SLOT]}, mutations=(
        ("const pa = num(slot.plate_alpha, 1, 0, 1);", "const pa = 1;"),
    ))
    assert sans_alpha["slots"][0]["libre_px"][3] != 204, \
        "l'alpha de plaque n'est pas appliqué et le banc ne le voit pas"


def test_sans_couleur_de_plaque_aucun_octet_ne_change(tmp_path):
    """La condition de non-régression de la phase 3a : les trois clés neuves,
    à leur défaut neutre, ne changent RIEN au fichier. On compare les
    empreintes de trois rendus : sans les clés du tout (le document d'AVANT),
    avec les clés aux défauts, et avec une plaque d'alpha nul."""
    ref = _banc_plaque(tmp_path, {"slots": [{"text": PLAQUE_TXT}],
                                  "drop": ["plate_color", "plate_alpha", "plate_radius"]})
    neutre = _banc_plaque(tmp_path, {"slots": [{"text": PLAQUE_TXT}]})
    assert neutre["hash"] == ref["hash"], "les clés neuves changent le rendu"
    # alpha 0 = aucune plaque visible, même avec une couleur demandée
    nul = _banc_plaque(tmp_path, {"slots": [dict(PLAQUE_SLOT, plate_alpha=0)]})
    assert nul["hash"] == ref["hash"], "une plaque à alpha 0 laisse des pixels"
    # et une couleur illisible ne peint pas non plus (pas de fillStyle bancal)
    faux = _banc_plaque(tmp_path, {"slots": [dict(PLAQUE_SLOT, plate_color="bleu")]})
    assert faux["hash"] == ref["hash"], "une couleur non hexadécimale a peint"
    # contre-épreuve : une VRAIE plaque, elle, change l'empreinte
    vraie = _banc_plaque(tmp_path, {"slots": [PLAQUE_SLOT]})
    assert vraie["hash"] != ref["hash"]


def test_le_rayon_de_plaque_est_borne_par_le_painter(tmp_path):
    """Le painter reçoit les slots du document TELS QUELS — `normSlot` ne
    passe que par le panneau. Un rayon aberrant doit donc être ramené AU
    DESSIN, et cela se lit au coin : à rayon nul le coin est peint, à rayon
    démesuré il ne peut pas l'être (le rayon sature à la moitié du petit
    côté), mais le centre l'est toujours."""
    carre = _banc_plaque(tmp_path, {"slots": [dict(PLAQUE_SLOT, plate_radius=0)]})
    assert carre["slots"][0]["coin_px"][3] == 204, carre["slots"][0]
    enorme = _banc_plaque(tmp_path, {"slots": [dict(PLAQUE_SLOT, plate_radius=9999)]})
    assert enorme["slots"][0]["coin_px"][3] == 0, \
        "un rayon démesuré peint quand même le coin : il n'est pas borné"
    assert enorme["slots"][0]["centre_px"][3] == 204, enorme["slots"][0]
    # ... et le rayon négatif retombe sur le carré, il n'inverse rien
    negatif = _banc_plaque(tmp_path, {"slots": [dict(PLAQUE_SLOT, plate_radius=-9)]})
    assert negatif["hash"] == carre["hash"]

    # MUTATION : rayon non borné -> le coin reste peint (le rayon démesuré est
    # ignoré ou explose), et le banc doit le voir.
    libre = _banc_plaque(tmp_path, {"slots": [dict(PLAQUE_SLOT, plate_radius=9999)]},
                         mutations=(
        ("Math.min(g.mm2px(mm), b[2] / 2, b[3] / 2)", "g.mm2px(mm)"),
    ))
    assert libre["slots"][0]["coin_px"][3] != 0, \
        "le rayon n'était pas borné et le banc ne le voit pas"


# ── LA BRANCHE `arcTo` (dette 3a/3b, soldée en 3c-T6) ───────────────────────
# `platePath` a deux branches : `roundRect` quand la toile l'offre, quatre
# raccords d'arc sinon (Safari < 16, WebView anciennes). La seconde n'avait
# JAMAIS rasterisé au banc — moveTo / arcTo / closePath étaient des coquilles
# vides — donc « même tracé » n'était qu'une phrase de commentaire.
# Le banc accumule maintenant le chemin et le remplit par parité de traversées,
# c'est-à-dire par un rastériseur INDÉPENDANT de celui du rectangle arrondi :
# la comparaison mesure bien deux chemins, pas deux fois le même.
#
# LE BUDGET A ÉTÉ DÉPASSÉ, ET C'EST DIT : le plan estimait « ≤ ~30 lignes de
# harnais ». Mesuré après coup — 43 lignes de code pour l'accumulation seule
# (`arcTo` au sens de la toile en pèse 20 à lui tout seul : tangentes, centre,
# aplatissement) et 61 avec la relève d'empreinte qui la juge — 85 lignes
# ajoutées au banc en tout, 24 de commentaire. Le rastériseur
# indépendant n'est pas négociable : réutiliser `inRR` en re-déduisant le
# rectangle depuis le chemin ferait comparer la forme à elle-même.

def test_le_repli_sans_roundRect_trace_LA_MEME_PLAQUE(tmp_path):
    """On retire `roundRect` DU CONTEXTE (l'état d'un moteur, pas un réglage
    du produit) et l'on compare les deux empreintes, ligne par ligne.

    MESURÉ, plaque 54 x 18 mm à rayon 2 mm sur poker 300 DPI (638 x 213 px,
    rayon 23,6 px) : 135 243 pixels peints par `roundRect`, 135 242 par le
    repli — UN pixel d'écart (0,0007 %), sur UNE seule ligne de balayage, dans
    la bande d'un coin. Bande peinte et boîte englobante identiques au pixel.
    L'écart vient de l'aplatissement de l'arc en 16 cordes, qui passe un cheveu
    à l'intérieur du cercle : c'est la seule tolérance, et elle est nommée."""
    o = {"slots": [PLAQUE_SLOT], "empreinte": True}
    avec = _banc_plaque(tmp_path, o)
    sans = _banc_plaque(tmp_path, dict(o, sans_arrondi=True))
    # la BRANCHE a bien basculé : sans cette assertion, un `delete` sans effet
    # ferait passer le test en comparant deux fois le chemin `roundRect`.
    assert avec["roundRect"] is True and sans["roundRect"] is False
    assert avec["hash"] != sans["hash"], "les deux branches ne peuvent pas " \
        "rendre le MÊME octet : l'une échantillonne un cercle, l'autre 16 cordes"

    a, s = avec["empreinte"], sans["empreinte"]
    assert a and s and len(a) == len(s)
    peintes_a = [r for r in a if r[3] > 0]
    peintes_s = [r for r in s if r[3] > 0]
    # 1. la BANDE peinte et la BOÎTE englobante sont les mêmes, au pixel près
    assert (peintes_a[0][0], peintes_a[-1][0]) == (peintes_s[0][0], peintes_s[-1][0])
    assert (min(r[1] for r in peintes_a), max(r[2] for r in peintes_a)) \
        == (min(r[1] for r in peintes_s), max(r[2] for r in peintes_s))
    # 2. le nombre de pixels peints ne bouge que d'un cheveu
    pa, ps = sum(r[3] for r in a), sum(r[3] for r in s)
    assert abs(pa - ps) <= 8, (pa, ps)
    assert abs(pa - ps) / pa < 1e-4, (pa, ps)
    # 3. et les lignes qui diffèrent sont DANS LES COINS, nulle part ailleurs :
    #    un bord droit qui bougerait ne serait pas une tolérance de coin.
    r_px = PLAQUE_SLOT["plate_radius"] / 25.4 * 300
    haut, bas = peintes_a[0][0], peintes_a[-1][0]
    ecarts = [x[0] for x, y in zip(a, s) if x[1:] != y[1:]]
    assert len(ecarts) <= 4, ecarts
    for y in ecarts:
        assert y <= haut + r_px + 1 or y >= bas - r_px - 1, (y, haut, bas, r_px)


def test_un_repli_QUI_NE_TRACE_PAS_LA_MEME_FORME_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : un seul des quatre raccords devient un segment
    droit — le coin haut-droit du repli redevient CARRÉ. Le produit ne lève
    pas, la plaque se peint encore, et seule l'empreinte le dit. Sans ce
    mutant, la tolérance de huit pixels ci-dessus pourrait couvrir n'importe
    quoi."""
    o = {"slots": [PLAQUE_SLOT], "empreinte": True, "sans_arrondi": True}
    droit = _banc_plaque(tmp_path, o, mutations=(
        ("    ctx.arcTo(x + w, y, x + w, y + h, r);",
         "    ctx.lineTo(x + w, y);"),))
    ref = _banc_plaque(tmp_path, {"slots": [PLAQUE_SLOT], "empreinte": True})
    pa = sum(r[3] for r in ref["empreinte"])
    pd = sum(r[3] for r in droit["empreinte"])
    # un coin carré rend ~un quart de (r² - πr²/4) de plus : très au-dessus des
    # huit pixels de tolérance, et la mesure le dit en clair.
    assert pd - pa > 100, (pa, pd)
    ecarts = [x[0] for x, y in zip(ref["empreinte"], droit["empreinte"])
              if x[1:] != y[1:]]
    assert len(ecarts) > 4, ecarts


def test_les_quatre_gabarits_rendent_a_l_octet_pres_comme_avant(tmp_path):
    """Le seuil de non-régression le plus large : chacun des quatre gabarits
    livrés, rendu par le painter AVEC les clés neuves aux défauts, doit sortir
    exactement le même tampon qu'un document d'AVANT la phase 3a (les clés
    absentes). Aucun gabarit ne nomme la plaque : ils héritent du défaut, et
    le défaut ne peint pas."""
    g = CT.geom("poker_eu", 300)
    for pid in sorted(TY.PRESETS):
        slots = TY.preset_slots(pid, g)
        for s in slots:
            assert s["plate_color"] is None, (pid, s["id"])
            assert s["plate_alpha"] == 1.0 and s["plate_radius"] == 0.0, (pid, s["id"])
        avant = _banc_plaque(tmp_path, {"slots": slots,
                                        "drop": ["plate_color", "plate_alpha",
                                                 "plate_radius"]})
        apres = _banc_plaque(tmp_path, {"slots": slots})
        assert apres["hash"] == avant["hash"], f"gabarit « {pid} » a bougé"
        assert apres["n_textes"] > 0, pid


# (« les mesures d'encre ignorent la plaque » a déménagé en section 10 : les
#  trois passes passent désormais par `soloClone`, et c'est le helper — plus
#  trois littéraux recopiés — que le test épingle.)


def test_le_panneau_offre_les_trois_reglages_de_plaque(tmp_path):
    """« Un réglage qui n'a pas de commande n'existe pas pour l'utilisateur. »
    Les trois vivent dans l'inspecteur de slot, avec les patrons voisins : un
    `input[type=color]` comme la couleur du contour, deux champs numériques
    comme l'opacité — et ils sont câblés sur `patchSlot`.

    LU SUR LE PANNEAU RENDU depuis la 3b-T2 : le bloc est partagé avec le
    calque d'image (`inspPlaque`), donc son code ne vit plus dans le corps de
    `renderInsp`. Ce que ce test défend n'a pas changé — ce sont les trois
    commandes et leur rang à l'écran."""
    corps = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False),
                                              "sel": "titre"}})["insp"]
    assert "<summary>Plaque de fond et bordure</summary>" in corps
    assert 'class="cf-type-pcol"' in corps
    assert 'data-k="plate_alpha"' in corps
    assert 'data-k="plate_radius"' in corps
    # ... et le bouton qui RETIRE la plaque, sans quoi une couleur posée par
    # erreur ne se reprend plus (un `input[type=color]` ne sait pas dire null).
    assert 'class="btn sm cf-type-pnone"' in corps
    # l'ordre de l'inspecteur n'a pas bougé : la plaque s'insère AVANT le
    # groupe contour/ombre/arc, qui reste devant opacité/justification.
    assert (corps.index("<summary>Plaque de fond et bordure</summary>")
            < corps.index("<summary>Contour, ombre, arc</summary>")
            < corps.index("<summary>Opacité, justification</summary>"))
    # câblés : la couleur par son écouteur dédié, les nombres par la boucle
    # générique `input[type="number"][data-k]`. Le branchement est commun aux
    # deux natures de bloc depuis la 3b-T2, donc il est lu dans `wireInspCommun`
    # — et le fait qu'il soit COMMUN est ce qui empêche le panneau d'image de
    # perdre la plaque en silence.
    src = _js()
    i = src.index("function wireInspCommun(")
    fil = src[i:src.index("\n  function ", i + 10)]
    assert '.cf-type-pcol").addEventListener("input"' in fil
    assert "{ plate_color: e.target.value }" in fil
    assert "{ plate_color: null }" in fil
    assert 'input[type="number"][data-k]' in fil


# ════════ 10. LE VERROU, LE PAS DE LA SPEC, LA PASSE D'ENCRE PARTAGÉE ═══════
# Phase 3b, tâche 1. Trois fondations et un filet :
#
#   · `lock` — 36e clé. Un bloc verrouillé refuse les GESTES DE SCÈNE (glisser,
#     poignées, flèches, Suppr au clavier) et rien d'autre : il reste
#     sélectionnable — c'est par la sélection qu'on atteint le panneau pour le
#     déverrouiller — et le panneau l'édite normalement. Le verrou protège de
#     la main qui dérape, pas de l'intention.
#   · le pas du clavier passe à celui que la spec NOMME (§6.1:307) : 1 mm,
#     Maj = 0,2 mm. L'ancien 0,5 / Maj 5 mm inversait le sens de Maj.
#   · `soloClone` — les trois passes qui redessinent un slot SEUL partagent
#     enfin un helper au lieu de recopier l'objet de neutralisation.
#
# Le banc ci-dessous ne fait pas tourner le painter : il fait tourner `init()`
# et récupère les écouteurs LÀ OÙ LE MODULE LES POSE (pointerdown sur le
# calque d'édition, keydown sur le document). Ce qu'il éprouve n'est donc pas
# une fonction interne choisie à la main — c'est la surface que la main touche.

BANC_VERROU = r"""
import { readFileSync } from "node:fs";
const SRC = readFileSync(process.argv[2], "utf8");
const OPT = JSON.parse(readFileSync(process.argv[3], "utf8"));

/* un contexte 2D de paille : ce banc ne juge AUCUN pixel (celui de la section
   9 s'en charge), il lui faut seulement de quoi mesurer un texte pour que la
   mise en page du panneau aboutisse. */
function ctx2d() {
  const c = {
    canvas: { width: 8, height: 8 }, _size: 10,
    save() { }, restore() { }, translate() { }, rotate() { }, setTransform() { },
    clearRect() { }, beginPath() { }, closePath() { }, moveTo() { }, lineTo() { },
    quadraticCurveTo() { }, arcTo() { }, rect() { }, roundRect() { }, fill() { },
    fillText() { }, strokeText() { }, drawImage() { },
    getImageData: (x, y, w, h) => ({ data: new Uint8ClampedArray(Math.max(4, w * h * 4)) }),
    measureText(s) {
      const w = Array.from(String(s)).length * 0.5 * c._size;
      return { width: w, actualBoundingBoxAscent: c._size * 0.72,
        actualBoundingBoxDescent: c._size * 0.21 };
    },
  };
  Object.defineProperty(c, "font", { get() { return c._f || ""; },
    set(v) { c._f = v; const m = /([\d.]+)px/.exec(v); if (m) c._size = parseFloat(m[1]); } });
  ["globalAlpha", "fillStyle", "strokeStyle", "lineWidth", "lineJoin", "miterLimit",
    "textAlign", "textBaseline", "shadowColor", "shadowBlur", "shadowOffsetX",
    "shadowOffsetY", "globalCompositeOperation", "imageSmoothingEnabled"]
    .forEach((k) => { c[k] = null; });
  return c;
}

/* ── UN VRAI `querySelectorAll`, SUR LE HTML QUE LE MODULE VIENT D'ECRIRE ──
   LE TROU QUE CECI BOUCHE (consigne en 3b-T4) : `querySelectorAll` rendait []
   de paille. Or `renderList` ECRIT son HTML puis va CHERCHER ses rangees pour
   y brancher l'oeil, le cadenas, l'ordre, la corbeille et le glisser. Avec un
   [] , aucun de ces cinq ecouteurs n'etait jamais pose : le banc mesurait la
   PRESENCE des classes dans une chaine de caracteres, et rien du geste.
   Ce qui suit est le strict necessaire pour ce cablage-la : un analyseur de
   balises, des selecteurs `.classe` et `balise`, un `closest` qui remonte par
   le parent. Ce n'est pas un DOM — c'est de quoi retrouver un bouton et
   appuyer dessus. L'arbre est REBATI a chaque ecriture d'`innerHTML` : une
   repeinture jette les anciens nœuds avec leurs ecouteurs, exactement comme
   un vrai navigateur. */
const VIDES = { br: 1, hr: 1, img: 1, input: 1, meta: 1, link: 1 };
const ENTITES = { "&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">", "&#39;": "'" };
const deent = (s) => String(s == null ? "" : s)
  .replace(/&(?:quot|amp|lt|gt|#39);/g, (m) => ENTITES[m]);
function matche(n, sel) {
  const s = String(sel).trim();
  if (!s) return false;
  if (s.charAt(0) === ".") return n._cls.has(s.slice(1));
  return n.tagName === s.toUpperCase();
}
function noeud(tag, attrs) {
  const n = { tagName: String(tag).toUpperCase(), kids: [], dataset: {}, style: {},
    listeners: {}, _cls: new Set(), parent: null, value: "", textContent: "" };
  String(attrs || "").replace(/([\w:-]+)(?:="([^"]*)")?/g, (m, k, v) => {
    if (k === "class") String(v || "").split(/\s+/).forEach((c) => { if (c) n._cls.add(c); });
    else if (k.slice(0, 5) === "data-") {
      n.dataset[k.slice(5).replace(/-(\w)/g, (x, c) => c.toUpperCase())] = deent(v);
    }
    return m;
  });
  n.classList = {
    add: (c) => n._cls.add(c), remove: (c) => n._cls.delete(c),
    contains: (c) => n._cls.has(c),
    toggle: (c, v) => { const on = (v === undefined) ? !n._cls.has(c) : !!v;
      if (on) n._cls.add(c); else n._cls.delete(c); },
  };
  n.addEventListener = (t, fn) => { (n.listeners[t] = n.listeners[t] || []).push(fn); };
  n.removeEventListener = (t, fn) => {
    const a = n.listeners[t] || [], i = a.indexOf(fn);
    if (i >= 0) a.splice(i, 1);
  };
  n.tous = () => n.kids.reduce((a, k) => a.concat([k], k.tous()), []);
  n.querySelectorAll = (sel) => n.tous().filter((k) => matche(k, sel));
  n.querySelector = (sel) => n.querySelectorAll(sel)[0] || null;
  n.closest = (sel) => { let c = n; while (c) { if (matche(c, sel)) return c; c = c.parent; } return null; };
  n.contains = (c) => n.tous().indexOf(c) >= 0;
  n.setAttribute = () => { }; n.removeAttribute = () => { };
  n.focus = () => { }; n.blur = () => { }; n.click = () => { };
  n.scrollIntoView = () => { }; n.remove = () => { n._out = true; };
  n.appendChild = (c) => { n.kids.push(c); return c; };
  n.getBoundingClientRect = () => ({ left: 0, top: 0, width: 0, height: 0 });
  return n;
}
function arbre(html) {
  const racine = noeud("div", "");
  const pile = [racine];
  const re = /<(\/)?([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:="[^"]*")?)*)\s*(\/)?>/g;
  let m;
  while ((m = re.exec(String(html || "")))) {
    if (m[1]) { if (pile.length > 1) pile.pop(); continue; }
    const n = noeud(m[2], m[3]);
    n.parent = pile[pile.length - 1];
    n.parent.kids.push(n);
    if (!m[4] && !VIDES[m[2].toLowerCase()]) pile.push(n);
  }
  return racine;
}

/* UN ELEMENT DE PAILLE. `querySelector` MEMORISE : le même sélecteur rend
   toujours le même objet, sans quoi on ne pourrait pas relire ce que le module
   vient d'écrire dedans (c'est ainsi qu'on lit la liste des blocs). Il reste
   memorise — c'est par lui que le banc atteint les CONTENEURS. Seul
   `querySelectorAll` lit vraiment le HTML : c'est le seul dont le module se
   sert pour cabler des elements qu'il vient d'ecrire. */
function elm(tag) {
  const cache = {}, cls = new Set(), lis = {};
  /* LES OBSERVATEURS DE CLASSE. Node n'a pas de `MutationObserver` : sans ce
     relais, la branche « le panneau s'efface » du module ne serait jamais
     posée au banc, et le pin de fermeture des popovers ne mesurerait rien. */
  const prevenir = () => (e._obs || []).forEach((fn) => fn([], null));
  const e = {
    tagName: String(tag || "div").toUpperCase(), style: {}, dataset: {},
    kids: [], listeners: lis, _h: "", value: "", textContent: "",
    options: { length: 0 },
    classList: {
      add: (c) => { cls.add(c); prevenir(); },
      remove: (c) => { cls.delete(c); prevenir(); },
      contains: (c) => cls.has(c),
      toggle: (c, v) => { const on = (v === undefined) ? !cls.has(c) : !!v;
        if (on) cls.add(c); else cls.delete(c); prevenir(); },
    },
    addEventListener(t, fn) { (lis[t] = lis[t] || []).push(fn); },
    removeEventListener(t, fn) {
      const a = lis[t] || [], i = a.indexOf(fn);
      if (i >= 0) a.splice(i, 1);
    },
    appendChild(c) { e.kids.push(c); return c; },
    insertAdjacentHTML() { }, setAttribute() { }, removeAttribute() { },
    setPointerCapture() { }, releasePointerCapture() { },
    /* un nœud RETIRÉ le reste : c'est ainsi qu'on lit si un popover a été
       fermé (son HTML, lui, se relit encore — et c'est voulu : on veut savoir
       si quelqu'un l'a repeint APRÈS sa fermeture). */
    remove() { e._out = true; }, focus() { }, blur() { }, click() { }, scrollIntoView() { },
    getContext: () => ctx2d(),
    querySelector(sel) { return (cache[sel] = cache[sel] || elm("div")); },
    /* L'ARBRE EST REBATI A CHAQUE ECRITURE (`_arbre` remis a null par le
       setter d'`innerHTML`) : deux `renderList` de suite rendent deux jeux de
       rangees distincts, avec leurs propres ecouteurs. */
    querySelectorAll(sel) {
      if (!e._arbre) e._arbre = arbre(e._h);
      return e._arbre.querySelectorAll(sel);
    },
    closest() { return null; },
    /* la fermeture au clic dehors demande `contains` : sans lui, le popover
       de la palette lèverait au premier pointerdown du document. */
    contains(c) { return e.kids.indexOf(c) >= 0; },
    getBoundingClientRect() { return e._rect || { left: 0, top: 0, width: 0, height: 0 }; },
  };
  /* `_n` COMPTE LES ÉCRITURES. Une garde de repeinture qui ne se mesure pas est
     une garde qu'on peut retirer sans que rien ne rougisse : c'est le seul moyen
     de dire « deux peintures du MÊME état n'ont écrit qu'une fois ». */
  Object.defineProperty(e, "innerHTML", { get: () => e._h,
    set: (v) => { e._h = String(v); e._n = (e._n || 0) + 1; e._arbre = null; } });
  Object.defineProperty(e, "className", { get: () => "", set() { } });
  return e;
}

function geom(fmt_mm, dpi, bleed_mm, safe_mm) {
  const R = (x) => Math.floor(Number(x.toFixed(9)) + 0.5);
  const px = (mm) => R(mm / 25.4 * dpi);
  const canvas_px = [px(fmt_mm[0] + 2 * bleed_mm), px(fmt_mm[1] + 2 * bleed_mm)];
  const trim_px = [px(fmt_mm[0]), px(fmt_mm[1])];
  const bleed_off_px = [(canvas_px[0] - trim_px[0]) / 2, (canvas_px[1] - trim_px[1]) / 2];
  const safe_px = [px(fmt_mm[0] - 2 * safe_mm), px(fmt_mm[1] - 2 * safe_mm)];
  const safe_off_px = [bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2,
    bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2];
  return { fmt: "poker_eu", label: "Poker", dpi: dpi, canvas_px, trim_px, bleed_off_px,
    safe_px, safe_off_px, bleed_mm, safe_mm, mm2px: (v) => v / 25.4 * dpi,
    px2mm: (v) => v * 25.4 / dpi };
}
const G = geom([63, 88], 300, 3, 3);
const DOC = { type: Object.assign(
  { slots: [], sel: "", seeded: true, show_boxes: true, audit: false,
    preset: "champion", optical_mm: 0.5 }, OPT.state || {}) };
/* LES SOUS-ARBRES DES AUTRES PIÈCES. `OPT.doc` les pose TELS QUELS — clé absente
   = clé absente, ce qui est justement l'état qu'une carte des calques doit
   savoir nommer sans mentir. */
Object.assign(DOC, OPT.doc || {});
let MOD = null;
/* CE QUE LE MODULE A DIT À L'ÉCRAN. Un refus qui ne se mesure pas est un refus
   qu'on peut vider de sa phrase sans que rien ne rougisse — or c'est la PHRASE
   qui fait la moitié du travail d'un plafond. */
const TOASTS = [];
/* CHAQUE ÉCRITURE AU DOCUMENT, RETENUE. Le pin des rangées fixes de la liste de
   calques est un pin d'ABSENCE : « aucun patch » ne se prouve qu'en comptant
   ceux qui passent. */
const PATCHS = [];
/* LES ABONNEMENTS DU MODULE. `on()` ne faisait rien : les branches accrochées à
   `core:render` n'étaient donc JAMAIS jouées au banc. */
const ONS = {};
/* LA NAVIGATION DU CORE, ESPIONNÉE (core.js:971 `show`, celle que les boutons du
   rail appellent). Le banc ne l'exécute pas : il note l'id demandé. */
const SHOWS = [];
const CF = {
  register(cfg) {
    MOD = cfg;
    return { patch: (p) => { PATCHS.push(JSON.parse(JSON.stringify(p))); return Object.assign(DOC.type, p); },
      api: { get: async () => ({}), post: async () => ({}), raw: async () => ({ ok: false }) },
      emit() { }, slot() { }, aside() { }, invalidate() { }, busy() { }, on() { },
      toast: (m, err) => { TOASTS.push({ m: String(m), err: !!err }); } };
  },
  get(path, def) {
    let v = DOC;
    for (const p of String(path).split(".")) { if (v == null) return def; v = v[p]; }
    return v === undefined ? def : v;
  },
  /* LA TABLE DES Z, telle que le CORE la publie (core.js:2248 — copie gelée sur
     le global gelé). `OPT.ztable` la BROUILLE : une liste de bandes recopiée
     dans la pièce ne bougerait pas d'un pouce, et c'est ce qu'on veut voir. */
  Z_TABLE: Object.freeze(OPT.ztable
    || { 10: "texture", 20: "face", 30: "texture", 40: "frame", 60: "type", 70: "frame", 90: "__core__" }),
  show: (id) => { SHOWS.push(String(id)); },
  side: () => OPT.face || "front",
  geom: () => G, geomOf: () => G, current: () => 0, cards: () => [],
  card: () => (OPT.carte || { fields: {} }),
  on(ev, fn) { (ONS[ev] = ONS[ev] || []).push(fn); },
  renderCard: async () => null, modules: () => [],
};
/* LE CATALOGUE DES MODÈLES, tel que `CF.models` le sert (core.js:modelsPublic).
   `OPT.catalogue` pilote : une liste de modèles, "absent" pour un catalogue
   injoignable, "sanscore" pour un CORE plus vieux que la pièce (la clé
   n'existe alors PAS, comme sur un vrai vieux core). `OPT.lent` retarde la
   réponse — c'est le seul moyen d'ouvrir DEUX fois le menu pendant qu'UNE
   requête est en vol, donc d'éprouver la garde d'étiquette. */
if (OPT.catalogue !== "sanscore") {
  CF.models = async () => {
    if (OPT.lent) await new Promise((r) => setTimeout(r, OPT.lent));
    if (OPT.catalogue === "absent") throw new Error(OPT.err || "backend injoignable (qa)");
    return Array.isArray(OPT.catalogue) ? OPT.catalogue : [];
  };
}

const HOSTE = elm("div");
const PANNEAU = elm("div");
PANNEAU.classList.add("on");        /* le calque n'est vivant que panneau OUVERT */
HOSTE.closest = () => PANNEAU;
const SCENE = elm("canvas");
/* echelle 1 : un pixel d'ecran = un pixel de toile, donc un deplacement en
   pixels se relit en millimetres sans conversion cachee. */
SCENE._rect = { left: 0, top: 0, width: G.canvas_px[0], height: G.canvas_px[1] };
const DOCQ = { ".stage-canvas": SCENE };
const DOCL = {};
const CORPS = [];
globalThis.window = { CF: CF, addEventListener() { } };
globalThis.document = {
  createElement: (t) => elm(t),
  querySelector: (sel) => (DOCQ[sel] = DOCQ[sel] || elm("div")),
  querySelectorAll: () => [],
  addEventListener(t, fn) { (DOCL[t] = DOCL[t] || []).push(fn); },
  removeEventListener() { },
  body: { appendChild(c) { CORPS.push(c); return c; } },
  fonts: { add() { } },
  activeElement: null,
};
/* L'OBSERVATEUR DE CLASSE, de paille : il relaie ce que `elm.classList` vient
   de faire. Le module s'en sert pour suivre l'état du panneau (devant /
   derrière) — c'est ce qui lui dit qu'on a changé de pièce. Node n'en a pas. */
globalThis.MutationObserver = class {
  constructor(fn) { this._fn = fn; }
  observe(el) { (el._obs = el._obs || []).push(this._fn); }
  disconnect() { }
};
const boom = [];
process.on("uncaughtException", (e) => { boom.push(String((e && e.message) || e)); });
(0, eval)(SRC);
await MOD.init(HOSTE);
await new Promise((r) => setTimeout(r, 60));

/* LE CALQUE = l'element pose sur document.body qui porte un pointerdown.
   Trouve, pas suppose : si le module changeait de support, ce banc le dirait. */
const OV = CORPS.filter((e) => (e.listeners.pointerdown || []).length)[0];
if (!OV) throw new Error("aucun calque d'edition n'a ete pose sur document.body");
const onDown = OV.listeners.pointerdown[0];
const onKey = (DOCL.keydown || [])[0];
if (!onKey) throw new Error("aucun ecouteur clavier n'a ete pose sur le document");

function ptr(id, x, y, h, maj) {
  const hb = { dataset: { id: id },
    closest: (s) => (s === ".cf-type-hbox" ? hb : null) };
  const cible = h ? { dataset: { h: h },
    closest: (s) => (s === ".cf-type-hh" ? cible : (s === ".cf-type-hbox" ? hb : null)) } : hb;
  return { isPrimary: true, target: cible, clientX: x, clientY: y, pointerId: 1,
    altKey: false, shiftKey: !!maj, preventDefault() { } };
}
/* LE FOND DU CALQUE — la surface qui n'appartient a AUCUNE boite, celle ou le
   lasso commence. Dans un vrai navigateur c'est un element a part (le calque
   lui-meme est `pointer-events: none`) : ici on rend donc une cible dont
   `closest(".cf-type-hbox")` vaut NULL, ce qui est exactement ce que le module
   doit voir pour savoir qu'il est en terrain vide. */
function fond(x, y, maj) {
  const bg = { dataset: {}, closest: (s) => (s === ".cf-type-ovbg" ? bg : null) };
  return { isPrimary: true, target: bg, clientX: x, clientY: y, pointerId: 1,
    altKey: false, shiftKey: !!maj, preventDefault() { } };
}
function kev(a) {
  return { key: a.k, target: { tagName: "DIV" }, shiftKey: !!a.maj, altKey: !!a.alt,
    ctrlKey: !!a.ctrl, metaKey: false, preventDefault() { } };
}
/* LES MENUS POSÉS SUR LE CORPS, dans l'ordre : le popover de la palette est
   un <div> ajouté à `document.body` (comme celui des gabarits), et c'est là
   qu'on lit ce qu'il OFFRE. Trouvés par leur contenu, pas par un sélecteur —
   le banc n'a pas de vrai DOM. */
function menus() {
  return CORPS.filter((e) => String(e._h).indexOf("cf-type-mi") >= 0
    || String(e._h).indexOf("cf-type-paln") >= 0);
}
/* LA PILE D'ANNULATION, ouverte par mutation (patron `__solo`). Un geste de
   rangee doit poser UNE entree, pas zero (rien a annuler) ni deux (deux
   Ctrl+Z pour defaire un clic). Sans ce compteur, « une entree par geste »
   ne se prouve pas — c'est du texte dans un commentaire. */
const undoN = () => (globalThis.__undo ? globalThis.__undo() : null);
/* LES RANGEES QUE `renderList` VIENT D'ECRIRE, retrouvees par leur `data-id`
   comme le ferait une main sur l'ecran (jamais par indice : l'ordre est
   justement ce que « monter / descendre » et le glisser deplacent). */
function rangees() {
  return HOSTE.querySelector(".cf-type-list").querySelectorAll(".cf-type-row");
}
function rangee(id) {
  return rangees().filter((r) => r.dataset.id === id)[0] || null;
}
const traces = [];
for (const a of (OPT.actes || [])) {
  if (a.t === "rangee") {
    /* UN BOUTON DE RANGEE, JOUE. On appuie sur l'ECOUTEUR QUE LE MODULE A
       POSE — pas sur une fonction choisie a la main : si `renderList` cessait
       de cabler ce bouton, `cable` tomberait a faux et le test le dirait. */
    const row = rangee(a.id);
    let cible = null;
    if (row) {
      cible = (a.b === "mv")
        ? row.querySelectorAll(".cf-type-mv").filter((b) => b.dataset.d === String(a.d))[0]
        : row.querySelector(".cf-type-" + a.b);
    }
    const fn = cible && (cible.listeners.click || [])[0];
    const avP = PATCHS.length, avU = undoN();
    if (fn) fn({ target: cible, currentTarget: cible, preventDefault() { } });
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "rangee", id: a.id, b: a.b, d: a.d === undefined ? null : a.d,
      trouve: !!row, cable: !!fn, patchs: PATCHS.length - avP,
      undo: (avU == null || undoN() == null) ? null : undoN() - avU });
  } else if (a.t === "ligne") {
    /* LE CLIC SUR LA LIGNE, pas sur un bouton : il ne fait que DESIGNER. La
       garde du module (`e.target.closest("button")`) est jouee pour de vrai —
       `bouton: true` fait passer la cible pour un bouton de la rangee. */
    const row = rangee(a.id);
    const cible = a.bouton ? (row && row.querySelector(".cf-type-eye")) : row;
    const fn = row && (row.listeners.click || [])[0];
    const avP = PATCHS.length;
    if (fn) fn({ target: cible || row, preventDefault() { } });
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "ligne", id: a.id, bouton: !!a.bouton, cable: !!fn,
      patchs: PATCHS.length - avP });
  } else if (a.t === "drag") {
    /* LE GLISSER-DEPOSER, dans son ordre reel : dragstart sur la rangee de
       depart, dragover puis drop sur celle d'arrivee. LE PRESSE-PAPIER est de
       paille mais il est le SEUL canal — le drop ne sait qui bouge que par ce
       qu'il y relit. Et `preventDefault` est compte : sans lui, un vrai
       navigateur refuse le depot, donc son absence serait un defaut MUET. */
    const de = rangee(a.from), vers = rangee(a.to);
    let charge = "", prev = 0;
    const dt = { setData: (t, v) => { charge = String(v); }, getData: () => charge,
      effectAllowed: "" };
    const ev = (c) => ({ dataTransfer: dt, target: c, preventDefault() { prev++; } });
    const ds = de && (de.listeners.dragstart || [])[0];
    const dov = vers && (vers.listeners.dragover || [])[0];
    const dr = vers && (vers.listeners.drop || [])[0];
    const avP = PATCHS.length, avU = undoN();
    if (ds) ds(ev(de));
    const glisse = !!(de && de.classList.contains("drag"));
    if (dov) dov(ev(vers));
    const survol = !!(vers && vers.classList.contains("over"));
    if (dr) dr(ev(vers));
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "drag", from: a.from, to: a.to,
      cable: !!(ds && dov && dr), charge: charge, glisse: glisse, survol: survol,
      relache: !!(vers && vers.classList.contains("over")), prevent: prev,
      patchs: PATCHS.length - avP,
      undo: (avU == null || undoN() == null) ? null : undoN() - avU });
  } else if (a.t === "down") {
    const avU0 = undoN();
    onDown(ptr(a.id, a.x || 0, a.y || 0, a.h, a.maj));
    /* LA TRACE QUI COMPTE : un glisser qui DEMARRE branche un pointermove sur
       le calque. Zero ecouteur = aucun geste n'a commence. */
    traces.push({ acte: "down", moves: (OV.listeners.pointermove || []).length,
      sel: JSON.parse(JSON.stringify(DOC.type.sel)),
      undo: (avU0 == null || undoN() == null) ? null : undoN() - avU0 });
  } else if (a.t === "move") {
    const mv = (OV.listeners.pointermove || [])[0];
    /* `alt` PAR DEFAUT VRAI : les bancs d'avant les guides mesuraient un
       deplacement NU (ni grille ni aimant), et ils doivent continuer de le
       mesurer. Un banc qui veut eprouver l'aimantation le dit (`alt: false`). */
    if (mv) mv({ clientX: a.x || 0, clientY: a.y || 0,
      altKey: a.alt === undefined ? true : !!a.alt, shiftKey: !!a.maj });
    /* LE CALQUE TEL QU'IL EST PENDANT LE GESTE : les lignes de guide ne vivent
       QUE la, entre deux `pointermove`. Les lire a la fin du banc ne dirait
       rien — `onOvUp` les efface, et c'est justement ce qu'on veut mesurer. */
    traces.push({ acte: "move", branche: !!mv, ov: OV._h });
  } else if (a.t === "lasso") {
    /* LE LASSO, DANS SON ORDRE REEL : appui sur le FOND du calque, glisser,
       relachement. C'est le seul geste qui commence hors de toute boite. */
    const avU = undoN(), avP = PATCHS.length;
    onDown(fond(a.x0 || 0, a.y0 || 0, a.maj));
    const mv = (OV.listeners.pointermove || [])[0];
    if (mv) mv({ clientX: a.x1 || 0, clientY: a.y1 || 0, altKey: false, shiftKey: !!a.maj });
    const up = (OV.listeners.pointerup || [])[0];
    if (up) up();
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "lasso", branche: !!(mv && up),
      sel: JSON.parse(JSON.stringify(DOC.type.sel)),
      patchs: PATCHS.length - avP,
      undo: (avU == null || undoN() == null) ? null : undoN() - avU });
  } else if (a.t === "barre") {
    /* UN BOUTON DE LA BARRE CONTEXTUELLE, joue sur l'ECOUTEUR QUE LE PANNEAU A
       POSE — jamais sur une fonction choisie a la main. */
    const insp = HOSTE.querySelector(".cf-type-insp");
    const b = insp.querySelectorAll("." + (a.cl || "cf-type-alg"))
      .filter((x) => x.dataset[a.dk || "a"] === a.v)[0];
    const fn = b && (b.listeners.click || [])[0];
    const avP = PATCHS.length, avU = undoN();
    if (fn) fn({ target: b, currentTarget: b, preventDefault() { } });
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "barre", v: a.v, trouve: !!b, cable: !!fn,
      patchs: PATCHS.length - avP,
      undo: (avU == null || undoN() == null) ? null : undoN() - avU });
  } else if (a.t === "lot") {
    /* UN REGLAGE EN LOT, joue sur l'ECOUTEUR du panneau multiple. Les deux
       familles que le DOM de paille sait retrouver (elles portent une CLASSE)
       sont les bandeaux segmentes et les puces — les champs numeriques, eux,
       se lisent par un selecteur d'attribut que ce DOM n'a pas. */
    const insp = HOSTE.querySelector(".cf-type-insp");
    const avP = PATCHS.length, avU = undoN();
    let cable = false;
    if (a.seg) {
      const seg = insp.querySelectorAll(".cf-type-seg")
        .filter((x) => x.dataset.k === a.k)[0];
      const fn = seg && (seg.listeners.click || [])[0];
      const cible = { dataset: { v: a.v } };
      cible.closest = (s) => (s === "button[data-v]" ? cible : null);
      cable = !!fn;
      if (fn) fn({ target: cible });
    } else {
      const b = insp.querySelectorAll(".cf-type-t")
        .filter((x) => x.dataset.k === a.k)[0];
      const fn = b && (b.listeners.click || [])[0];
      cable = !!fn;
      if (fn) fn({ target: b, currentTarget: b });
    }
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "lot", k: a.k, v: a.v === undefined ? null : a.v,
      cable: cable, patchs: PATCHS.length - avP,
      undo: (avU == null || undoN() == null) ? null : undoN() - avU });
  } else if (a.t === "up") {
    const up = (OV.listeners.pointerup || [])[0];
    if (up) up();
    traces.push({ acte: "up", branche: !!up });
  } else if (a.t === "key") {
    onKey(kev(a));
    traces.push({ acte: "key", k: a.k });
  } else if (a.t === "pal") {
    /* LE BOUTON DE LA BARRE, pas une fonction choisie à la main : on joue
       l'écouteur que `buildPanel` a posé sur `.cf-type-pal`. */
    const b = HOSTE.querySelector(".cf-type-pal");
    const fn = (b.listeners.click || [])[0];
    if (fn) fn({ currentTarget: b });
    await new Promise((r) => setTimeout(r, a.ms || 30));
    traces.push({ acte: "pal", cable: !!fn, menus: menus().length });
  } else if (a.t === "palclic") {
    /* le clic est DÉLÉGUÉ (un seul écouteur pour n entrées) : la cible porte
       `data-o` et se retrouve elle-même par `closest`, comme un vrai bouton. */
    const menu = menus().slice(-1)[0];
    const fn = menu && (menu.listeners.click || [])[0];
    const cible = { dataset: { o: a.o } };
    cible.closest = (s) => (s === ".cf-type-mi" ? cible : null);
    if (fn) fn({ target: cible });
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "palclic", o: a.o, branche: !!fn });
  } else if (a.t === "bande") {
    /* UNE RANGÉE FIXE DE LA LISTE DE CALQUES. La pièce à atteindre n'est pas
       donnée au banc : elle est LUE dans la rangée que le module a peinte —
       sans quoi le test prouverait sa propre table. Le clic est délégué au
       corps de la section (un seul écouteur pour toutes les rangées). */
    const corps = HOSTE.querySelector(".cf-type-lbody");
    const html = String(HOSTE.querySelector(".cf-type-bhaut")._h)
      + String(HOSTE.querySelector(".cf-type-bbas")._h);
    const m = new RegExp('data-z="' + a.z + '"[\\s\\S]{0,600}?data-mod="([^"]*)"').exec(html);
    const cible = { dataset: { mod: m ? m[1] : "" } };
    cible.closest = (s) => (s === ".cf-type-go" ? cible : null);
    const fn = (corps.listeners.click || [])[0];
    const av = PATCHS.length;
    if (fn) fn({ target: cible });
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "bande", z: a.z, mod: m ? m[1] : null, branche: !!fn,
      patchs: PATCHS.length - av });
  } else if (a.t === "peint") {
    /* LE CORE A REPEINT LA CARTE. `core:render` part à CHAQUE frame — c'est
       l'évènement sous lequel la garde d'égalité de texte doit tenir. */
    for (const fn of (ONS["core:render"] || [])) fn({});
    await new Promise((r) => setTimeout(r, 10));
    traces.push({ acte: "peint",
      ecrits: [HOSTE.querySelector(".cf-type-bhaut")._n || 0,
        HOSTE.querySelector(".cf-type-bbas")._n || 0] });
  } else if (a.t === "etat") {
    /* CHANGER L'ÉTAT D'UNE AUTRE PIÈCE, comme le ferait son panneau : la carte
       des calques ne l'apprend que par la peinture suivante. */
    Object.assign(DOC, a.doc || {});
    traces.push({ acte: "etat" });
  } else if (a.t === "quitte") {
    /* CHANGER DE PIÈCE : le CORE retire `.on` de la section du panneau. AU
       CLAVIER (Entrée sur le rail), il n'y a pas de `pointerdown` — la
       fermeture au clic dehors ne court donc pas, et c'est tout le sujet. */
    PANNEAU.classList.remove("on");
    await new Promise((r) => setTimeout(r, 20));
    traces.push({ acte: "quitte" });
  }
}
await new Promise((r) => setTimeout(r, (OPT.lent || 0) + 60));

/* ── EQUIVALENCE DU HELPER D'ENCRE ────────────────────────────────────────
   `soloClone` vit dans la fermeture du module : pour le comparer aux TROIS
   LITTERAUX QU'IL REMPLACE, le banc se fait ouvrir la porte par une mutation
   (`globalThis.__solo = soloClone;` pose juste avant la parenthese finale),
   exactement comme les autres mutants — sur la COPIE, jamais sur le depot.
   Ce qu'on compare est la SERIALISATION : memes cles, memes valeurs, meme
   ORDRE. « Ca neutralise pareil » ne suffisait pas, il fallait « ca rend le
   meme objet ». */
let solo = null;
if (OPT.solo && globalThis.__solo) {
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const base = Object.assign({}, OPT.solo);
  /* LES DEUX LITTERAUX D'AVANT, recopies mot pour mot depuis le code qui
     precede le partage (mod-type.js:3410 / :3704 / :3908). */
  const vieux_sans_ombre = Object.assign(clone(base),
    { shadow: 0, shadow_dx: 0, shadow_dy: 0, opacity: 100, plate_color: null });
  const vieux_avec_ombre = Object.assign(clone(base), { opacity: 100, plate_color: null });
  const neuf_sans_ombre = globalThis.__solo(base);
  const neuf_avec_ombre = globalThis.__solo(base, { shadow: true });
  solo = {
    egal_sans_ombre: JSON.stringify(neuf_sans_ombre) === JSON.stringify(vieux_sans_ombre),
    egal_avec_ombre: JSON.stringify(neuf_avec_ombre) === JSON.stringify(vieux_avec_ombre),
    /* et le CONTRAIRE : les deux formes ne sont pas la meme (sans quoi
       l'egalite ci-dessus serait vraie pour de mauvaises raisons). */
    formes_distinctes: JSON.stringify(neuf_sans_ombre) !== JSON.stringify(neuf_avec_ombre),
    source_intacte: JSON.stringify(base) === JSON.stringify(OPT.solo),
    sans_ombre: neuf_sans_ombre, avec_ombre: neuf_avec_ombre,
  };
}

/* ── LES DEUX NORMALISEURS, EPROUVES L'UN CONTRE L'AUTRE ──────────────────
   `normSlot` vit dans la fermeture : la meme porte que `soloClone`
   (`globalThis.__norm = normSlot;` pose avant la parenthese finale) le rend
   appelable. On rend DEUX passes : la premiere sert a la parite avec le
   backend, la seconde a l'idempotence — une normalisation qui REPARE sa propre
   sortie n'est pas une normalisation. */
let norm = null;
if (OPT.norm && globalThis.__norm) {
  norm = { un: [], deux: [] };
  OPT.norm.forEach((r, i) => {
    const a = globalThis.__norm(r, i);
    norm.un.push(a);
    norm.deux.push(globalThis.__norm(a, i));
  });
}

/* ── LA PALETTE, OUVERTE PAR MUTATION (patron `__solo`) ────────────────────
   `globalThis.__pal = {…}` est posé avant la parenthèse finale, sur la COPIE.
   Ce qu'on en tire : les OFFRES (dérivées du preset AU MOMENT DE PEINDRE), la
   phrase que la palette dit quand elle n'a rien de plus, son HTML — et le
   miroir client de `norm_slots`, éprouvé par EXÉCUTION contre le backend et
   jamais par un match de source (leçon B1). */
let pal = null;
if (OPT.pal && globalThis.__pal) {
  await globalThis.__pal.ensure();
  pal = {
    offres: globalThis.__pal.offres().map(
      (o) => ({ id: o.id, label: o.label, hint: o.hint, n: o.n })),
    note: globalThis.__pal.note(),
    html: globalThis.__pal.html(),
  };
}
let norms = null;
if (OPT.norms && globalThis.__pal) {
  norms = OPT.norms.map((l) => globalThis.__pal.normSlots(l));
}

process.stdout.write(JSON.stringify({
  slots: DOC.type.slots, sel: DOC.type.sel, traces: traces, norm: norm,
  pal: pal, norms: norms, menus: menus().map((e) => e._h), toasts: TOASTS,
  /* LE DERNIER POPOVER A-T-IL ÉTÉ RETIRÉ DU CORPS ? `null` s'il n'y en a
     jamais eu — un banc qui n'ouvre pas de menu ne dit rien sur sa fermeture. */
  ferme: (() => { const l = menus(); return l.length ? !!l[l.length - 1]._out : null; })(),
  ov: OV._h, liste: HOSTE.querySelector(".cf-type-list")._h,
  /* LES RANGEES, RELUES SUR LES ELEMENTS et non dans la chaine : leur ORDRE
     (c'est lui que « monter / descendre » et le glisser deplacent), l'etat de
     l'oeil et du cadenas, et le compte des commandes reellement cablees. */
  rangees: rangees().map((r) => {
    const oeil = r.querySelector(".cf-type-eye");
    const cad = r.querySelector(".cf-type-lock");
    return { id: r.dataset.id, off: r._cls.has("off"), sel: r._cls.has("on"),
      lock: !!cad && cad._cls.has("on"),
      cable: [oeil, cad, r.querySelector(".cf-type-del")]
        .filter((b) => b && (b.listeners.click || []).length).length
        + r.querySelectorAll(".cf-type-mv")
          .filter((b) => (b.listeners.click || []).length).length,
      gestes: ["click", "dragstart", "dragover", "drop"]
        .filter((t) => (r.listeners[t] || []).length).length };
  }),
  undo: undoN(),
  /* LA LISTE DE CALQUES : les deux conteneurs de bandes fixes, ce qu'ils
     portent et COMBIEN DE FOIS on les a écrits ; les pièces demandées ; le
     nombre total d'écritures au document. */
  bhaut: HOSTE.querySelector(".cf-type-bhaut")._h,
  bbas: HOSTE.querySelector(".cf-type-bbas")._h,
  ecrits: [HOSTE.querySelector(".cf-type-bhaut")._n || 0,
    HOSTE.querySelector(".cf-type-bbas")._n || 0],
  shows: SHOWS, patchs: PATCHS.length,
  /* LE PANNEAU DE BLOC : c'est lui qui bascule ses sections selon le `kind`.
     Le meme cache de selecteurs qui rend la liste le rend, sans un mot de
     plus au module. */
  insp: HOSTE.querySelector(".cf-type-insp")._h,
  panneau: HOSTE._h,
  solo: solo, exceptions: boom,
}));
"""


def _banc_verrou(tmp_path, opts: dict, mutations=()) -> dict:
    """Fait tourner `init()` du module dans un DOM de paille, puis joue les
    gestes demandés SUR LES ÉCOUTEURS QUE LE MODULE A POSÉS. `mutations` casse
    une protection avant exécution : un test qui passerait aussi sur le code
    cassé ne prouverait rien."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de gestes ne peut pas tourner")
    src = JS.read_text(encoding="utf-8", newline="")   # newline='' : CRLF gardé
    for avant, apres in mutations:
        assert avant in src, f"mutation introuvable : {avant!r}"
        assert src.count(avant) == 1, f"mutation ambiguë : {avant!r}"
        src = src.replace(avant, apres)
    js = tmp_path / "mod-type-verrou.js"
    js.write_text(src, encoding="utf-8", newline="")
    banc = tmp_path / "banc-verrou.mjs"
    banc.write_text(BANC_VERROU, encoding="utf-8")
    conf = tmp_path / "opts-verrou.json"
    conf.write_text(json.dumps(opts, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    d = json.loads(r.stdout)
    assert d["exceptions"] == [], d["exceptions"]
    return d


def _slots_verrou(lock: bool) -> list:
    """Deux blocs, dont le premier porte (ou non) le verrou. Objets COMPLETS :
    le painter comme le calque reçoivent les slots du document tels quels."""
    a = TY.norm_slot({"id": "titre", "label": "Titre", "box": [10.0, 20.0, 30.0, 10.0],
                      "text": "Veilleur", "lock": lock})
    b = TY.norm_slot({"id": "regles", "label": "Règles", "box": [8.0, 50.0, 46.0, 20.0],
                      "text": "Vol, célérité."})
    return [a, b]


GLISSE = [{"t": "down", "id": "titre", "x": 0, "y": 0},
          {"t": "move", "x": 118, "y": 59},      # ~10 mm x ~5 mm à 300 DPI
          {"t": "up"}]


def test_le_verrou_est_la_36e_cle_des_deux_cotes():
    """Le verrou est une clé de slot comme les autres : il voyage avec le deck,
    il se lit des deux côtés, et son défaut est NEUTRE — c'est ce qui garde les
    quatre gabarits livrés byte-identiques (rendu prouvé plus bas)."""
    js = json.loads(_bloc_js("DEFAULTS"))
    assert "lock" in TY.SLOT_DEFAULTS and "lock" in js
    assert TY.SLOT_DEFAULTS["lock"] is False and js["lock"] is False
    assert js == TY.SLOT_DEFAULTS
    # `lock` est la 36e clé PAR SON ARRIVÉE ; le total, lui, a bougé depuis (39
    # depuis le calque d'image de la tâche 2, 49 depuis les formes de la phase
    # 5-T2). Ce qui compte ici et ne bouge pas : les deux tables sont la MÊME,
    # à la clé près.
    assert len(js) == len(TY.SLOT_DEFAULTS) == 49, sorted(js)
    # normalisé des deux côtés, et sans surprise : tout ce qui n'est pas
    # explicitement vrai est faux (un document d'avant n'a pas la clé).
    assert TY.norm_slot({})["lock"] is False
    assert TY.norm_slot({"lock": True})["lock"] is True
    assert TY.norm_slot({"lock": "oui"})["lock"] is True
    assert TY.norm_slot({"lock": 0})["lock"] is False
    src = _js()
    assert "s.lock = !!r.lock;" in src, "normSlot de l'écran ignore le verrou"
    # aucun gabarit livré ne naît verrouillé
    g = CT.geom("poker_eu", 300)
    for pid in sorted(TY.PRESETS):
        for s in TY.preset_slots(pid, g):
            assert s["lock"] is False, (pid, s["id"])


def test_le_verrou_ne_change_pas_un_octet_du_rendu(tmp_path):
    """Condition de non-régression de la 36e clé : à son défaut, elle ne peint
    rien. Chacun des quatre gabarits doit sortir le même tampon avec et sans
    la clé (le document d'AVANT la 3b)."""
    g = CT.geom("poker_eu", 300)
    for pid in sorted(TY.PRESETS):
        slots = TY.preset_slots(pid, g)
        avant = _banc_plaque(tmp_path, {"slots": slots, "drop": ["lock"]})
        apres = _banc_plaque(tmp_path, {"slots": slots})
        assert apres["hash"] == avant["hash"], f"gabarit « {pid} » a bougé"
        assert apres["n_textes"] > 0, pid
    # ... et un slot VERROUILLÉ se peint exactement comme le même déverrouillé :
    # le verrou est une protection d'édition, pas un état de la carte.
    libre = _banc_plaque(tmp_path, {"slots": _slots_verrou(False)})
    ferme = _banc_plaque(tmp_path, {"slots": _slots_verrou(True)})
    assert ferme["hash"] == libre["hash"], "le verrou change le fichier livré"


def test_un_slot_verrouille_refuse_le_glisser_et_les_poignees(tmp_path):
    """LE TEST QUI COMPTE. Le même glisser, sur le même bloc, verrou ouvert
    puis fermé : la boîte bouge, puis elle ne bouge plus. Et le refus est un
    NON-DÉMARRAGE — aucun pointermove n'est branché — pas un geste joué puis
    annulé, qui aurait laissé une entrée d'annulation derrière lui."""
    libre = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                                    "actes": GLISSE})
    assert libre["slots"][0]["box"][0] != 10.0, "le glisser de contrôle n'a rien bougé"
    assert libre["traces"][0]["moves"] == 1, libre["traces"]

    ferme = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                                    "actes": GLISSE})
    assert ferme["slots"][0]["box"] == [10.0, 20.0, 30.0, 10.0], ferme["slots"][0]["box"]
    assert ferme["traces"][0]["moves"] == 0, \
        "le glisser a DÉMARRÉ sur un bloc verrouillé (pointermove branché)"
    assert ferme["traces"][1]["branche"] is False

    # une POIGNÉE non plus : le redimensionnement passe par le même écouteur.
    poignee = [{"t": "down", "id": "titre", "x": 0, "y": 0, "h": "se"},
               {"t": "move", "x": 118, "y": 59}, {"t": "up"}]
    hh = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                                 "actes": poignee})
    assert hh["slots"][0]["box"] == [10.0, 20.0, 30.0, 10.0], hh["slots"][0]["box"]

    # MUTATION : le garde retiré du pointerdown -> le bloc verrouillé glisse.
    #
    # DEPUIS T3, LE VERROU EST TENU À DEUX ENDROITS et la mutation doit les
    # ouvrir TOUS LES DEUX pour prouver quelque chose : (1) le geste ne DÉMARRE
    # pas sur un bloc verrouillé, (2) un bloc verrouillé du LOT ne SUIT pas le
    # glisser d'un voisin. Ce ne sont pas deux copies de la même garde — ce sont
    # deux questions (« puis-je commencer ici ? », « qui bouge avec moi ? ») —,
    # mais elles se recouvrent sur le bloc attrapé. N'en retirer qu'une laissait
    # la mutation VERTE : le mutant survivant a été trouvé ici même.
    sourd = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                                    "actes": GLISSE},
                         mutations=(("if (s.lock) return;   /* VERROU : aucun geste ne demarre */",
                                      "if (false) return;"),
                                    ("const libres = vise.filter((q) => par[q] && !par[q].lock);",
                                     "const libres = vise.filter((q) => par[q]);")))
    assert sourd["slots"][0]["box"][0] != 10.0, \
        "le verrou n'était pas ce qui arrêtait le glisser"


def test_un_slot_verrouille_refuse_la_fleche_et_la_suppression(tmp_path):
    """Le clavier est l'autre main sur la scène : flèches (déplacement),
    Alt+flèches (redimensionnement), Suppr. Les trois s'arrêtent au verrou."""
    actes = [{"t": "key", "k": "ArrowRight"},
             {"t": "key", "k": "ArrowDown", "maj": True},
             {"t": "key", "k": "ArrowRight", "alt": True},
             {"t": "key", "k": "Delete"}]
    ferme = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                                    "actes": actes})
    assert len(ferme["slots"]) == 2, "Suppr a effacé un bloc verrouillé"
    assert ferme["slots"][0]["box"] == [10.0, 20.0, 30.0, 10.0], ferme["slots"][0]["box"]
    # contrôle : déverrouillé, les mêmes touches font tout leur travail
    libre = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                                    "actes": actes})
    assert len(libre["slots"]) == 1, "le contrôle n'a rien supprimé"

    # MUTATION : le garde retiré du clavier -> la flèche pousse le bloc
    # verrouillé. DEPUIS T3, CE GARDE VIT DANS `lotLibre` : les trois gestes de
    # clavier (flèche, Alt+flèche, Suppr) passent tous par lui, parce qu'ils
    # visent tous LE LOT et non plus le seul premier bloc. Une garde par geste
    # aurait été trois occasions d'en oublier une.
    sourd = _banc_verrou(tmp_path,
                         {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                          "actes": [{"t": "key", "k": "ArrowRight"}]},
                         mutations=(("const libres = ids.filter((q) => par[q] && !par[q].lock);",
                                      "const libres = ids.filter((q) => par[q]);"),))
    assert sourd["slots"][0]["box"][0] != 10.0, \
        "le verrou n'était pas ce qui arrêtait la flèche"
    # ... et la MÊME mutation fait passer Suppr : c'est bien une seule garde
    efface = _banc_verrou(tmp_path,
                          {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                           "actes": [{"t": "key", "k": "Delete"}]},
                          mutations=(("const libres = ids.filter((q) => par[q] && !par[q].lock);",
                                      "const libres = ids.filter((q) => par[q]);"),))
    assert len(efface["slots"]) == 1, \
        "le verrou n'était pas ce qui arrêtait la suppression"


def test_le_verrou_laisse_la_selection_et_le_panneau_libres(tmp_path):
    """« Le verrou protège des gestes de scène, pas de l'intention. » Cliquer
    un bloc verrouillé le SÉLECTIONNE — sans quoi on ne pourrait plus atteindre
    le panneau pour le déverrouiller —, et le panneau continue de l'éditer."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "regles"},
                                "actes": [{"t": "down", "id": "titre", "x": 0, "y": 0},
                                          {"t": "up"}]})
    assert d["sel"] == ["titre"], "un bloc verrouillé ne se sélectionne plus"
    assert d["slots"][0]["box"] == [10.0, 20.0, 30.0, 10.0]
    # le cadenas se voit : dans la ligne de la liste ET sur la boîte de l'aperçu
    assert 'class="cf-type-lock' in d["liste"], "aucun cadenas dans la liste"
    assert "cf-type-hbox" in d["ov"] and " lock" in d["ov"], \
        "la boîte verrouillée n'est pas marquée sur l'aperçu"
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-type-hbox.lock" in css and ".cf-type-lock" in css
    # ... et le bouton de la liste est câblé sur le verrou, avec UNE annulation
    src = _js()
    assert '{ lock: !s.lock }' in src, "le cadenas de la liste n'est pas câblé"
    # LE CHEMIN DU PANNEAU N'EST PAS GARDÉ, et c'est voulu : `patchSlot` est la
    # porte de TOUTE écriture de réglage (y compris celle qui déverrouille).
    # Un garde ici enfermerait le bloc pour de bon.
    corps = src[src.index("function patchSlot("):]
    corps = corps[:corps.index("\n  }")]
    assert "lock" not in corps, \
        "patchSlot regarde le verrou : le panneau ne pourrait plus éditer (ni déverrouiller)"


def test_la_copie_d_un_bloc_verrouille_nait_deverrouillee(tmp_path):
    """DÉCISION, pinée ici. Ctrl+D ne touche pas au bloc protégé : il en pose
    un AUTRE, à 2 mm, avec un identifiant neuf. C'est un acte d'intention, pas
    un geste de scène — il reste donc permis. La copie, elle, naît OUVERTE :
    le verrou marque un bloc DÉJÀ placé, et une copie qu'on vient de créer se
    place. Née fermée, elle aurait refusé le glisser qui la suit d'une seconde,
    sans que rien à l'écran ne dise pourquoi."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                                "actes": [{"t": "key", "k": "d", "ctrl": True}]})
    assert len(d["slots"]) == 3, "Ctrl+D a été refusé sur un bloc verrouillé"
    copie = [s for s in d["slots"] if s["id"] not in ("titre", "regles")]
    assert len(copie) == 1, [s["id"] for s in d["slots"]]
    assert copie[0]["lock"] is False, "la copie hérite du verrou"
    assert d["slots"][0]["lock"] is True, "l'original a perdu son verrou"


def test_le_pas_du_clavier_est_CELUI_DE_LA_SPEC(tmp_path):
    """§6.1:307 nomme le patron : « pas 1 mm, Maj = 0,2 mm ». P3 faisait
    0,5 mm et Maj = 5 mm — Maj y AGRANDISSAIT le pas au lieu de l'affiner,
    l'inverse du geste de précision qu'il nomme. Les deux constantes d'avant
    sont mortes, et le pas se mesure sur une boîte, pas sur une lecture."""
    src = _js()
    assert "const NUDGE_MM = 1, NUDGE_FINE_MM = 0.2," in src
    assert "NUDGE_BIG_MM" not in src, "l'ancien pas de 5 mm survit"
    assert "NUDGE_MM = 0.5" not in src
    # le mémo du panneau dit la même chose que le code
    assert "<b>flèches</b> 1 mm (<b>Maj</b> 0,2 mm)" in src

    base = [10.0, 20.0, 30.0, 10.0]
    def box(actes):
        d = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                                    "actes": actes})
        return d["slots"][0]["box"]
    assert box([{"t": "key", "k": "ArrowRight"}])[0] == base[0] + 1.0
    assert box([{"t": "key", "k": "ArrowUp"}])[1] == base[1] - 1.0
    assert box([{"t": "key", "k": "ArrowRight", "maj": True}])[0] == base[0] + 0.2
    assert box([{"t": "key", "k": "ArrowDown", "maj": True}])[1] == base[1] + 0.2
    # Alt = redimensionnement, sémantique inchangée, nouveaux pas
    assert box([{"t": "key", "k": "ArrowRight", "alt": True}])[2] == base[2] + 1.0
    assert box([{"t": "key", "k": "ArrowDown", "alt": True, "maj": True}])[3] == base[3] + 0.2

    # MUTATION : l'ancien pas restauré -> la mesure rougit.
    vieux = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                                    "actes": [{"t": "key", "k": "ArrowRight"}]},
                         mutations=(("const NUDGE_MM = 1,", "const NUDGE_MM = 0.5,"),))
    assert vieux["slots"][0]["box"][0] == 10.5, vieux["slots"][0]["box"]


def test_les_trois_passes_d_encre_partagent_UN_helper(tmp_path):
    """La plaque est du DÉCOR, pas de l'encre. Les trois passes qui redessinent
    un slot SEUL pour mesurer son encre (contrôle photométrique, halo d'ombre,
    relevé sur fichier) doivent la couper : une plaque opaque sur toute la
    boîte ferait passer chaque pixel de la boîte pour un corps de glyphe, et le
    contrôle de masquage comme celui de contraste rendraient n'importe quoi.

    Elles le faisaient TOUTES LES TROIS À LA MAIN, chacune avec son propre
    littéral — trois occasions d'oublier la clé suivante. Elles passent
    désormais par `soloClone`, et le COMPTE est épinglé : une quatrième passe
    qui recopierait l'objet au lieu d'appeler le helper fait rougir ce test."""
    src = _js_sans_commentaires()
    assert src.count("function soloClone(") == 1, "le helper n'existe pas (ou en double)"
    appels = len(re.findall(r"(?<!function )\bsoloClone\(", src))
    assert appels == 3, (
        f"{appels} appel(s) à soloClone : les passes « encre seule » sont trois "
        "aujourd'hui (contrôle photométrique, halo d'ombre, relevé sur fichier). "
        "Une quatrième doit PASSER PAR LE HELPER et monter ce compte à 4 — pas "
        "recopier l'objet de neutralisation une quatrième fois.")
    # ce que le helper garantit, énoncé une fois pour toutes : la plaque et
    # l'opacité tombent TOUJOURS, l'ombre seulement quand on ne la mesure pas.
    i0 = src.index("function soloClone(")
    i1 = i0 + src[i0:].index("\n  }")
    corps = src[i0:i1]
    # ... et plus AUCUN littéral de neutralisation recopié hors du helper
    assert all(i0 < m.start() < i1
               for m in re.finditer(r"opacity: 100, plate_color: null", src)), \
        "une passe neutralise encore l'encre à la main, hors du helper"
    assert "plate_color: null" in corps and "opacity: 100" in corps
    assert "shadow: 0, shadow_dx: 0, shadow_dy: 0" in corps
    assert "garde && garde.shadow" in corps
    # la passe du HALO est la seule à garder l'ombre — c'est elle qui la mesure
    assert src.count("soloClone(slot, { shadow: true })") == 1


def test_soloClone_rend_EXACTEMENT_les_objets_que_les_litteraux_rendaient(tmp_path):
    """Un partage qui change une mesure d'un cheveu ne serait pas un partage,
    ce serait une régression photométrique — et personne ne la verrait, ces
    trois passes ne tournant que dans un navigateur. Le helper est donc
    comparé aux DEUX LITTÉRAUX QU'IL REMPLACE, sur un slot qui porte tout ce
    qu'il doit neutraliser (ombre décalée, opacité à 40, plaque bleue) : mêmes
    clés, mêmes valeurs, MÊME ORDRE de sérialisation."""
    slot = dict(TY.norm_slot({"id": "titre", "label": "Titre",
                              "box": [10.0, 20.0, 30.0, 10.0], "text": "Veilleur",
                              "shadow": 2.0, "shadow_dx": 1.0, "shadow_dy": -1.0,
                              "shadow_color": "#101010", "opacity": 40.0,
                              "plate_color": "#3050a0", "plate_alpha": 0.8,
                              "plate_radius": 2.0, "lock": True}))
    d = _banc_verrou(tmp_path,
                     {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                      "solo": slot},
                     mutations=(("\r\n})();", "\r\n  globalThis.__solo = soloClone;\r\n})();"),))
    s = d["solo"]
    assert s, "la porte du banc ne s'est pas ouverte sur soloClone"
    assert s["egal_sans_ombre"], s["sans_ombre"]
    assert s["egal_avec_ombre"], s["avec_ombre"]
    assert s["formes_distinctes"], "les deux gardes rendent le même objet"
    assert s["source_intacte"], "soloClone MUTE le slot qu'on lui passe"
    # et ce qu'il neutralise, énoncé en clair sur les valeurs rendues
    assert s["sans_ombre"]["shadow"] == 0 and s["sans_ombre"]["shadow_dx"] == 0
    assert s["sans_ombre"]["shadow_dy"] == 0
    assert s["avec_ombre"]["shadow"] == 2.0, "la passe du halo a perdu l'ombre"
    assert s["avec_ombre"]["shadow_dx"] == 1.0 and s["avec_ombre"]["shadow_dy"] == -1.0
    for forme in ("sans_ombre", "avec_ombre"):
        assert s[forme]["opacity"] == 100, forme
        assert s[forme]["plate_color"] is None, forme
        # ... et RIEN D'AUTRE : la plaque garde son alpha et son rayon (ils ne
        # peignent plus rien sans couleur), le texte et la boîte sont intacts.
        assert s[forme]["plate_alpha"] == 0.8 and s[forme]["plate_radius"] == 2.0, forme
        assert s[forme]["box"] == slot["box"] and s[forme]["text"] == slot["text"], forme
        assert s[forme]["lock"] is True, forme


def test_les_mesures_d_encre_ignorent_toujours_la_plaque(tmp_path):
    """Le helper n'a pas changé ce qui est neutralisé : contre-épreuve au
    pixel. Une plaque opaque sur toute la boîte, et le relevé continue de dire
    « encre » pour les glyphes seuls — la même mesure qu'avant le partage."""
    sans = _banc_plaque(tmp_path, {"slots": [{"text": PLAQUE_TXT}]})
    avec = _banc_plaque(tmp_path, {"slots": [PLAQUE_SLOT]})
    # la plaque PEINT (le rendu diffère) ...
    assert avec["hash"] != sans["hash"]
    # ... et le texte reste par-dessus, à sa couleur, dans les deux cas
    assert avec["slots"][0]["glyphe_px"] == sans["slots"][0]["glyphe_px"]


# ── R14 : le filtre de noms ne suffisait pas ────────────────────────────────

def _lint():
    import importlib.util
    chemin = REPO / "scripts" / "qa" / "lint_cardforge.py"
    if not chemin.is_file():
        pytest.skip("lint_cardforge.py absent")
    spec = importlib.util.spec_from_file_location("lint_cf_type", chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _r14(src: str, mod=None) -> list:
    """Les signalements de R14 sur une source. `mod` permet de faire tourner la
    règle MUTILÉE (le module est réinstancié à chaque `_lint()`, la mutation ne
    fuit donc pas d'un test à l'autre)."""
    mod, trouves = (mod or _lint()), []
    mod.check_r14("type", "sonde.js", src,
                  lambda rule, path, line, msg, warn=False: trouves.append((line, msg)))
    return trouves


def test_la_regle_d_echappement_balaie_ce_QUI_ECRIT_DU_HTML_pas_ce_qui_le_dit():
    """R14 ne regardait que les fonctions dont le NOM contient « Html » ou
    « paint ». `renderInsp`, `renderList`, `buildStatics`, `fillPalettes` en
    écrivent tout autant et n'étaient pas balayées — un filtre de noms est une
    liste à tenir à jour, et personne ne la tient. Le critère est désormais
    MÉCANIQUE : une fonction qui pose du `innerHTML` écrit du HTML.

    Contre-épreuve dans les deux sens — la sonde fautive rougit, la fonction
    qui n'écrit aucun HTML reste hors périmètre."""
    fautive = ("function renderInsp() {\n"
               "  box.innerHTML = '<i data-id=\"' + s.id + '\"></i>';\n"
               "}\n")
    assert _r14(fautive), "l'élargissement ne mord pas : la sonde passe"
    # le nom seul ne suffisait pas ...
    assert not _r14(fautive.replace("innerHTML", "textContent")), \
        "une fonction qui n'écrit aucun HTML est balayée : périmètre trop large"
    # ... et le vieux critère de nom tient toujours
    assert _r14("function fooHtml() {\n"
                "  return '<i data-id=\"' + s.id + '\">';\n"
                "}\n")


def test_la_regle_d_echappement_ne_prend_pas_la_PROSE_pour_un_attribut():
    """L'élargissement a mis sous les yeux de la règle des fonctions qui
    écrivent du HTML ET des phrases. « ligne y=42 », « 300 DPI = 12 / mm² »,
    « &seed=7 » finissent tous par `nom=` : la fin de littéral ne suffit plus à
    dire « valeur d'attribut ». Le GUILLEMET, lui, tranche — et c'est
    exactement le cas que la règle existe pour attraper (un guillemet dans la
    valeur ferme l'attribut). Une valeur d'attribut sans guillemets n'existe
    nulle part dans ce labo ; la prose, elle, est partout."""
    for prose in ('  el.innerHTML = "x";\n  rows.push("ligne y=" + P.filet.y);\n',
                  '  el.innerHTML = "x";\n  u("t?a=" + b + "&seed=" + s.seed);\n',
                  '  el.innerHTML = "x";\n  rows.push("à " + P.m.dpi + " DPI = " + P.m.par_mm2);\n'):
        assert not _r14("function drawProof() {\n" + prose + "}\n"), prose
    # et la vraie faute, guillemet compris, rougit toujours
    assert _r14('function drawProof() {\n'
                '  el.innerHTML = \'<b title="\' + P.m.par_mm2 + \'">x</b>\';\n'
                '}\n')


SONDE_NUE = ("function {nom}() {{\n"
             "  el.innerHTML = '<div data-id=' + s.id + '>';\n"
             "}}\n")


def test_la_regle_d_echappement_attrape_AUSSI_l_attribut_SANS_guillemets():
    """LA RÉGRESSION QU'A COÛTÉE LE GUILLEMET EXIGÉ, et sa réparation.

    `'<div data-id=' + s.id + '>'` est un patron de DOM-XSS réel — et le PIRE
    des deux : dans une valeur d'attribut citée il faut un guillemet pour
    s'échapper ; sans guillemets, une simple ESPACE suffit à poser un attribut
    de plus (`x onerror=…`). L'ancienne règle l'attrapait dans les fonctions
    « …Html/paint » ; exiger le guillemet l'a fait rater PARTOUT.

    La réparation n'est pas de rendre le guillemet à nouveau facultatif — ce
    serait re-signaler la prose (« ligne y=42 »). C'est un SECOND motif :
    `nom=` nu, MAIS seulement si le fragment est encore DANS une balise
    ouverte (son dernier `<` vient après son dernier `>`). Une phrase n'a pas
    de `<` ; une balise ouverte, si."""
    for nom in ("renderX",      # balayée par le SINK (nom sans Html/paint)
                "paintFoo",     # balayée par le NOM — la classe d'origine
                "listeHtml"):
        assert _r14(SONDE_NUE.format(nom=nom)), \
            f"{nom}() : l'attribut SANS guillemets passe encore"
    # le message NOMME ce qui est en jeu (une espace suffit), il ne recopie pas
    # celui du cas cité — les deux fautes ne se réparent pas de la même façon.
    msg = _r14(SONDE_NUE.format(nom="renderX"))[0][1]
    assert "guillemets" in msg and "espace" in msg.lower(), msg
    # le cas CITÉ reste attrapé (la réparation n'a rien remplacé)
    assert _r14('function renderX() {\n'
                '  el.innerHTML = \'<div data-id="\' + s.id + \'">\';\n'
                '}\n')
    # ... et la POSITION TEXTE reste hors périmètre : la balise est refermée.
    assert not _r14('function renderX() {\n'
                    '  el.innerHTML = \'<b>\' + s.id + \'</b>\';\n'
                    '}\n')

    # MUTATION : second motif retiré -> la sonde nue repasse.
    mut = _lint()
    mut.R14_ATTR_NU = re.compile(r"(?!x)x")      # ne matche jamais rien
    assert not _r14(SONDE_NUE.format(nom="renderX"), mut), \
        "le second motif n'était pas ce qui attrapait l'attribut nu"


def test_les_cinq_faux_positifs_de_prose_restent_PROPRES():
    """L'autre moitié du contrat : les cinq phrases que l'élargissement avait
    fait rougir doivent rester muettes, et le test ne doit pas devenir creux si
    quelqu'un les efface — on vérifie donc AUSSI qu'elles sont toujours là.

    Ce sont de vraies lignes de deux modules voisins : « ligne y=42 »,
    « r=3 mm », « 300 DPI = 12 / mm² », « tile?mat=…&seed=7 ». Aucune n'ouvre
    une balise — c'est exactement ce que le second motif sait voir."""
    mod = _lint()
    for mid, proses in (
        ("frame", ('" r=" + r.corner + " "',
                   '"non isolable sur la ligne y=" + P.filet.y',
                   'ligne y=" + P.filet.y + ")"',
                   '" DPI = "')),
        ("texture", ('"&seed=" + s.seed',)),
    ):
        chemin = REPO / "frontend" / "cardforge" / "js" / f"mod-{mid}.js"
        src = chemin.read_text(encoding="utf-8")
        for p in proses:
            assert p in src, f"la prose épinglée a disparu de mod-{mid}.js : {p}"
        trouves = []
        mod.check_r14(mid, chemin, src,
                      lambda rule, path, line, msg, warn=False: trouves.append((line, msg)))
        assert not trouves, f"mod-{mid}.js : {trouves}"


def test_la_regle_d_echappement_balaie_AUSSI_ce_qui_RETOURNE_du_html():
    """LE TROU QUE LE REFACTOR DE LA TÂCHE 2 A OUVERT. R14 balayait une
    fonction sur son NOM (`Html|paint`) ou sur son SINK (`innerHTML =`). Sortir
    trois blocs de HTML de `renderInsp` pour les partager entre les deux
    natures de bloc leur a fait perdre les deux : `inspHead` ne s'appelle pas
    `…Html` et ne pose rien — elle RETOURNE une chaîne, que son appelante pose.

    Le critère suit le même principe qu'en T1 : le FAIT mécanique, pas
    l'intention. Une fonction qui rend un littéral commençant par `<` fabrique
    du balisage, quel que soit son nom et quel que soit qui l'affiche."""
    mod = _lint()
    # LA MUTATION QUI PROUVE LE CLIQUET : on dé-échappe la valeur d'attribut de
    # `inspHead` et la règle doit l'attraper. Avant l'élargissement, elle
    # rendait ZÉRO signalement — la fonction n'était pas balayée du tout.
    src = JS.read_text(encoding="utf-8")
    avant = 'class="cf-type-label" value="\' + esc(s.label) + \'"'
    assert avant in src and src.count(avant) == 1, "l'ancre de mutation a bougé"
    casse = src.replace(avant, 'class="cf-type-label" value="\' + s.label + \'"', 1)
    trouves = []
    mod.check_r14("type", JS, casse,
                  lambda rule, path, line, msg, warn=False: trouves.append(msg))
    assert trouves, "inspHead dé-échappée ne fait rien rougir : R14 ne la balaie pas"
    assert any("inspHead" in m for m in trouves), trouves
    # ... et le dépôt RÉEL, lui, reste propre (0 signalement sur les 9 pièces —
    # c'est `test_le_module_passe_le_lint_ELARGI` qui le tient).
    propres = []
    mod.check_r14("type", JS, src,
                  lambda rule, path, line, msg, warn=False: propres.append(msg))
    assert not propres, propres


def test_l_elargissement_de_R14_ne_prend_pas_la_PROSE_pour_du_balisage():
    """Le différentiel de l'élargissement, mesuré : combien de fonctions en
    plus sont balayées sur les neuf pièces, et zéro faux signalement. Une règle
    qui crie sur du texte finit désactivée — c'est la leçon de la T1, reprise
    telle quelle."""
    mod = _lint()
    total = 0
    for chemin in sorted((REPO / "frontend" / "cardforge" / "js").glob("mod-*.js")):
        src = chemin.read_text(encoding="utf-8")
        trouves = []
        mod.check_r14(chemin.stem, chemin, src,
                      lambda rule, path, line, msg, warn=False: trouves.append(msg))
        assert not trouves, f"{chemin.name} : {trouves}"
        total += len(mod.R14_RETOUR.findall(src))
    # le motif TROUVE quelque chose : sans cela l'élargissement serait décoratif
    assert total > 0, "aucune fabrique de HTML par retour dans les neuf pièces"


def test_le_module_passe_le_lint_ELARGI():
    """Le filet, sur les neuf pièces du labo — R14 compris, dans sa version
    élargie. S'il reste un `a.b` nu dans une valeur d'attribut quelque part,
    c'est ici que ça se voit."""
    mod = _lint()
    findings, present = mod.run(REPO)
    errs = [f for f in findings if not f["warn"]]
    assert not errs, "\n".join(f"{f['rule']} {f['file']}:{f['line']} {f['msg']}"
                               for f in errs)


# ══════════════ 11. LE CALQUE D'IMAGE (phase 3b, tâche 2) ═══════════════════
# Un calque d'image est un SLOT P3 d'une autre nature (`kind: "image"`), pas un
# objet neuf : il hérite gratuitement de l'ordre de peinture, de l'œil, du
# verrou, du calque d'édition, de HIST et de la fluidité. Ce que cette section
# verrouille :
#
#   · le VOCABULAIRE — trois clés, mêmes bornes des deux côtés, défauts
#     INERTES (les quatre gabarits livrés ne bougent pas d'un octet) ;
#   · le STOCKAGE — serveur, dans le dossier du deck, numéroté par un COMPTEUR
#     qui n'écrase jamais et ne recycle pas un numéro libéré ; borné en nombre,
#     en poids et en côté ; servi par un GET dont le nom passe une liste
#     blanche AVANT que le disque soit touché ;
#   · le DESSIN — la plaque dessous, l'image dans sa boîte selon `fit`,
#     l'opacité, et ZÉRO passe de glyphe ;
#   · les EXCLUSIONS — un calque d'image n'entre ni dans le relevé du painter
#     (donc dans aucune des trois passes d'encre), ni dans le juge de
#     lisibilité du backend. Il n'a pas de texte : il n'y a rien à mesurer, et
#     mesurer zéro aurait rempli le relevé de lignes « vides » mensongères.

IMG_MAX_ATTENDU = 12          # images de calque par deck
IMPORT_PX_ATTENDU = 4096      # côté long au-delà duquel un import est réduit
MOD_FACE_JS = REPO / "frontend" / "cardforge" / "js" / "mod-face.js"


def _png_bytes(w: int, h: int, couleur=(200, 40, 90)) -> bytes:
    import io as _io
    from PIL import Image
    buf = _io.BytesIO()
    Image.new("RGB", (int(w), int(h)), couleur).save(buf, format="PNG")
    return buf.getvalue()


def _post_img(did: str, data: bytes):
    return _api("POST", f"/api/cards/{did}/type/image", content=data,
                headers={"Content-Type": "application/octet-stream"})


def _type_dir(did: str) -> pathlib.Path:
    return CT.deck_dir(did) / "type"


# ── 11.1 le vocabulaire ─────────────────────────────────────────────────────

def test_les_trois_cles_du_calque_d_image_sont_dans_les_deux_tables():
    """39 clés par slot. Le bloc JS est du JSON littéral et l'égalité avec le
    dictionnaire Python est STRICTE : trois clés ajoutées d'un seul côté font
    rougir la suite. Celui-ci nomme ce qu'elles valent, et que le défaut est
    INERTE — un slot d'avant la 3b reste un slot de texte sans image."""
    js = json.loads(_bloc_js("DEFAULTS"))
    for k in ("kind", "src", "fit"):
        assert k in TY.SLOT_DEFAULTS, k
        assert k in js, k
        assert js[k] == TY.SLOT_DEFAULTS[k], k
    assert TY.SLOT_DEFAULTS["kind"] == "text"
    assert TY.SLOT_DEFAULTS["src"] == ""
    assert TY.SLOT_DEFAULTS["fit"] == "contain"
    assert len(js) == 49, sorted(js)
    assert js == TY.SLOT_DEFAULTS


def test_le_kind_et_le_fit_sont_sur_liste_blanche_des_deux_cotes():
    """Deux énumérations, pas deux chaînes libres. Une valeur inconnue retombe
    sur le défaut — jamais un `kind` inventé qui ferait sauter le painter dans
    une branche qui n'existe pas."""
    assert TY.KINDS[:2] == ("text", "image")
    assert TY.FITS == ("contain", "cover")
    assert TY.norm_slot({"kind": "image"})["kind"] == "image"
    assert TY.norm_slot({"kind": "video"})["kind"] == "text"
    assert TY.norm_slot({"kind": None})["kind"] == "text"
    assert TY.norm_slot({"kind": 7})["kind"] == "text"
    assert TY.norm_slot({"fit": "cover"})["fit"] == "cover"
    assert TY.norm_slot({"fit": "fill"})["fit"] == "contain"
    assert TY.norm_slot({})["fit"] == "contain"
    # tolérance de saisie IDENTIQUE des deux côtés : rognée, mise en bas de
    # casse, puis comparée. Deux lectures différentes de la même chaîne
    # feraient rendre un document autrement à l'écran qu'au contrôle.
    assert TY.norm_slot({"kind": " IMAGE "})["kind"] == "image"
    assert TY.norm_slot({"fit": "COVER"})["fit"] == "cover"
    src = _js()
    # les DEUX listes, ÉGALES à l'ordre près : `test_les_quatre_formes_sont_
    # dans_les_deux_vocabulaires` verrouille la ligne entière ; celui-ci
    # verrouille l'ÉGALITÉ des deux tables, quelle que soit leur longueur.
    m = re.search(r"const KINDS = \[(.*?)\];", src)
    assert m, "KINDS introuvable dans mod-type.js"
    assert tuple(re.findall(r'"([a-z]+)"', m.group(1))) == TY.KINDS, m.group(1)
    assert 'const FITS = ["contain", "cover"];' in src
    assert "s.kind = pick(r.kind, KINDS, SLOT_DEFAULTS.kind);" in src
    assert "s.fit = pick(r.fit, FITS, SLOT_DEFAULTS.fit);" in src
    # `pick` EST le miroir de `_choice` : même rognage, même bas de casse.
    assert "const pick = (v, list, d) => {" in src
    assert 'String(v == null ? "" : v).trim().toLowerCase()' in src


SRC_REFUSES = (
    "img:../../meta.json", "img:../img_1.png", "img:img_1.png/../x",
    "/etc/passwd", "img:img_1.PNG", "img:img_.png", "img_1.png",
    "img:paper.png", "http://ailleurs/x.png", "img:img_1.png ", "local:abc",
    "img:img_1.png\nimg:img_2.png", "img:img_1.pngX", "img:", "img:img_01.png/",
)


def test_la_source_d_une_image_ne_peut_nommer_QUE_un_fichier_du_deck():
    """`src` n'est pas un chemin : c'est un NOM que la route d'import a
    fabriqué elle-même (`img_{n}.png`). Le motif est donc exact des deux côtés,
    et tout le reste vaut « pas d'image » — pas une erreur, pas un chemin
    raboté en silence."""
    assert TY.norm_slot({"src": "img:img_7.png"})["src"] == "img:img_7.png"
    assert TY.norm_slot({"src": "img:img_12.png"})["src"] == "img:img_12.png"
    assert TY.norm_slot({"src": ""})["src"] == ""
    assert TY.norm_slot({})["src"] == ""
    assert TY.norm_slot({"src": None})["src"] == ""
    assert TY.norm_slot({"src": 42})["src"] == ""
    for mauvais in SRC_REFUSES:
        assert TY.norm_slot({"src": mauvais})["src"] == "", mauvais
    # L'ÉCRAN BORNE À LA MÊME RÈGLE, écrite au même motif — et `[0-9]` PLUTÔT
    # QUE `\d` depuis la ronde de la phase 5 : `\d` de Python est UNICODE,
    # celui de JavaScript est ASCII, si bien que `img:img_١٢.png` (chiffres
    # arabo-indiens) passait ici et pas là-bas. Le motif est le même mot à mot
    # des deux côtés parce qu'il n'a plus de sens dépendant du langage.
    assert TY.SLOT_SRC_RE.pattern == r"^(|img:img_[0-9]+\.png)$"
    assert r"/^(|img:img_[0-9]+\.png)$/" in _js()
    # ... et un corps mal formé traverse la route sans 500
    did = _did()
    r = _api("POST", f"/api/cards/{did}/type/layout",
             json={"slots": [{"id": "a", "kind": ["image"], "src": {"x": 1},
                              "fit": 3}]})
    assert r.status_code == 200, r.text
    row = r.json()["slots"][0]
    assert row["kind"] == "text"


# ── 11.2 le stockage : compteur, plafonds, liste blanche ────────────────────

def test_la_route_d_import_ecrit_un_fichier_numerote_sans_jamais_ecraser():
    """L'import répond par le NOM qu'il a écrit et par le `src` tout fait : le
    client n'a pas à recomposer la chaîne (il l'aurait mal recomposée un jour).
    Le second import ne touche pas au premier — pas d'écrasement, jamais."""
    from PIL import Image
    did = _did()
    r = _post_img(did, _png_bytes(8, 5))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["file"] == "img_1.png"
    assert d["src"] == "img:img_1.png"
    assert d["px"] == [8, 5]
    r2 = _post_img(did, _png_bytes(9, 4))
    assert r2.status_code == 200, r2.text
    assert r2.json()["file"] == "img_2.png"
    assert r2.json()["src"] == "img:img_2.png"
    dd = _type_dir(did)
    assert sorted(p.name for p in dd.glob("img_*.png")) == ["img_1.png", "img_2.png"]
    # LE PREMIER FICHIER EST INTACT : c'est ce que « compteur » veut dire.
    with Image.open(dd / "img_1.png") as im:
        assert im.size == (8, 5)
    with Image.open(dd / "img_2.png") as im:
        assert im.size == (9, 4)
    # aucun résidu temporaire n'est resté sur le disque
    assert not list(dd.glob("*.tmp")), sorted(p.name for p in dd.iterdir())
    # et le `src` rendu est ACCEPTÉ par la normalisation (les deux se parlent)
    assert TY.norm_slot({"src": d["src"]})["src"] == d["src"]
    # LE COMPTE ANNONCÉ EST CELUI DU DISQUE, recompté APRÈS l'écriture — c'est
    # lui que le message d'import affiche (« 2 / 12 »). Un compte calculé avant
    # la réservation aurait menti dès que deux imports se croisent.
    assert r.json()["n"] == 1 and r2.json()["n"] == 2
    assert r2.json()["max"] == TY.SLOT_IMAGES_MAX
    assert r2.json()["n"] == len(list(dd.glob("img_*.png")))


def test_un_compteur_QUI_MENT_ne_fait_perdre_aucune_image(monkeypatch):
    """MUTATION, et elle a changé de cible avec le remède de la revue.

    Le non-écrasement reposait sur le COMPTEUR (« lis le plus grand, ajoute
    un ») — une lecture, donc quelque chose que deux imports simultanés font en
    même temps et obtiennent pareil. Il repose désormais sur la RÉSERVATION :
    le nom final est créé en exclusivité, et celui qui perd passe au suivant.
    Le compteur n'est plus qu'un point de départ.

    On le casse donc pour de bon — il rend toujours « 1 », ce qu'il rendrait
    sous une course — et on vérifie qu'AUCUNE image n'est perdue quand même.
    Avant le remède, la seconde écrivait par-dessus la première."""
    from PIL import Image
    did = _did()
    assert _post_img(did, _png_bytes(8, 5)).status_code == 200
    monkeypatch.setattr(TY, "_next_img_index", lambda d: (1, 0))
    r = _post_img(did, _png_bytes(64, 20))
    assert r.status_code == 200, r.text
    assert r.json()["file"] == "img_2.png", \
        "un compteur qui ment écrase encore : la réservation ne protège pas"
    with Image.open(_type_dir(did) / "img_1.png") as im:
        assert im.size == (8, 5), "la première image a été écrasée"
    with Image.open(_type_dir(did) / "img_2.png") as im:
        assert im.size == (64, 20)


def test_le_compteur_ne_recycle_pas_un_numero_libere():
    """Le compteur vaut MAX + 1, pas « le premier trou ». Un slot supprimé peut
    être annulé (Ctrl+Z) : son image doit rester joignable, et un import qui
    reprendrait le numéro libéré ferait réapparaître le bloc annulé avec une
    AUTRE image. Les trous sont donc gardés."""
    did = _did()
    for _ in range(3):
        assert _post_img(did, _png_bytes(4, 4)).status_code == 200
    (_type_dir(did) / "img_1.png").unlink()
    r = _post_img(did, _png_bytes(6, 6))
    assert r.status_code == 200, r.text
    assert r.json()["file"] == "img_4.png", "le compteur a recyclé un numéro"
    assert sorted(p.name for p in _type_dir(did).glob("img_*.png")) == \
        ["img_2.png", "img_3.png", "img_4.png"]


def test_la_treizieme_image_est_refusee_AVEC_un_mot():
    """Un plafond nommé, qui COMPTE CE QUI EXISTE (pas ce qui a été importé
    dans cette session). Le refus dit le chiffre et ce qu'il faut faire."""
    assert TY.SLOT_IMAGES_MAX == IMG_MAX_ATTENDU
    did = _did()
    for i in range(TY.SLOT_IMAGES_MAX):
        assert _post_img(did, _png_bytes(4, 4)).status_code == 200, i
    r = _post_img(did, _png_bytes(4, 4))
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert "12" in detail and "image" in detail.lower(), detail
    # le refus n'a rien écrit
    assert len(list(_type_dir(did).glob("img_*.png"))) == IMG_MAX_ATTENDU


def test_un_import_qui_n_est_pas_une_image_ne_fait_jamais_500():
    """Doctrine de la pièce (spec §2.5) : jamais de 500, et un refus NOMMÉ."""
    did = _did()
    r = _post_img(did, b"ceci n'est pas une image")
    assert r.status_code == 400, r.text
    assert "image" in r.json()["detail"].lower()
    r = _post_img(did, b"")
    assert r.status_code == 400
    assert "vide" in r.json()["detail"].lower()
    # un PNG tronqué : illisible, donc refusé de la même main
    r = _post_img(did, _png_bytes(8, 8)[:40])
    assert r.status_code == 400, r.text
    # identifiant de deck illégal / deck absent
    assert _post_img("pas_un_deck", _png_bytes(4, 4)).status_code == 400
    assert _post_img("deck_deadbeef", _png_bytes(4, 4)).status_code == 404
    # rien n'a été écrit
    assert not list(_type_dir(did).glob("img_*.png"))


def test_le_poids_du_corps_est_borne_AVANT_le_decodage():
    """64 Mo, comme la matière de P6 : le corps est pesé AVANT d'être confié à
    la bibliothèque d'images — c'est le seul ordre qui protège la mémoire."""
    assert TY.IMG_MAX_BYTES == 64 * 1024 * 1024
    py = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    i = py.index("async def post_slot_image")
    corps = py[i:py.index("\n@router", i)]
    assert corps.index("IMG_MAX_BYTES") < corps.index("_store_slot_image"), \
        "le corps est décodé avant d'être pesé"
    assert "413" in corps, "le refus de poids n'est pas nommé par son code"


NOMS_REFUSES = ("job.json", "paper.png", "img_1.PNG", "img_.png",
                "img_1.png.bak", "IMG_1.PNG", "img_1", "img_1.png%00.txt",
                "..", "img_1.jpg", "%2e%2e%2fmeta.json", "img_1.png%0a",
                "img_1.png%20")


def test_la_route_qui_sert_une_image_filtre_le_NOM_avant_le_disque():
    """LISTE BLANCHE D'ABORD, DISQUE ENSUITE — l'ordre est le fond de l'affaire
    (patron `get_node_file`, 2c). Un motif appliqué APRÈS avoir composé un
    chemin a déjà laissé le chemin exister."""
    did = _did()
    assert _post_img(did, _png_bytes(8, 5)).status_code == 200
    for nom in NOMS_REFUSES:
        r = _api("GET", f"/api/cards/{did}/type/image/{nom}")
        assert r.status_code in (400, 404), (nom, r.status_code)
        assert "image/png" not in r.headers.get("content-type", ""), nom
    # L'ORDRE, ÉPINGLÉ SUR LA SOURCE : le motif est vérifié avant que le nom
    # touche un dossier.
    py = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    i = py.index("async def get_slot_image")
    corps = py[i:py.index("\n@router", i) if "\n@router" in py[i:] else len(py)]
    assert "IMG_NAME_RE" in corps
    assert corps.index("IMG_NAME_RE") < corps.index("_read_slot_image"), \
        "le nom est filtré APRÈS que le chemin a été composé"
    # et le SEUL endroit qui compose un chemin avec ce nom est le lecteur, en
    # aval du filtre : la route elle-même ne touche pas au disque.
    assert "type_dir(" not in corps


def test_le_disque_N_EST_PAS_TOUCHE_par_un_nom_refuse(monkeypatch):
    """L'ORDRE, MESURÉ ET PAS SEULEMENT RELU. On remplace le lecteur de disque
    par un mouchard : sur les noms refusés, il ne doit JAMAIS être appelé. Un
    filtre posé après la composition du chemin ferait rougir cette ligne — et
    c'est la seule façon de le montrer sans lire le fichier source."""
    did = _did()
    assert _post_img(did, _png_bytes(8, 5)).status_code == 200
    vus = []
    vrai = TY._read_slot_image
    monkeypatch.setattr(TY, "_read_slot_image",
                        lambda d, n: (vus.append(n), vrai(d, n))[1])
    for nom in NOMS_REFUSES:
        _api("GET", f"/api/cards/{did}/type/image/{nom}")
    assert vus == [], f"un nom refusé a atteint le disque : {vus}"
    # ... et le mouchard n'est pas inerte : un nom LÉGAL, lui, y arrive.
    r = _api("GET", f"/api/cards/{did}/type/image/img_1.png")
    assert r.status_code == 200 and vus == ["img_1.png"], vus


def test_l_image_servie_est_octet_pour_octet_celle_qui_est_sur_le_disque():
    """Et son cache est PERMIS : un `img_{n}.png` ne change jamais de contenu
    (le compteur n'écrase pas), donc `no-store` ne protégerait de rien et
    coûterait un aller-retour à chaque frame de l'aperçu."""
    did = _did()
    assert _post_img(did, _png_bytes(8, 5)).status_code == 200
    p = _type_dir(did) / "img_1.png"
    r = _api("GET", f"/api/cards/{did}/type/image/img_1.png")
    assert r.status_code == 200, r.text
    assert r.content == p.read_bytes()
    assert r.headers["content-type"] == "image/png"
    assert "no-store" not in r.headers.get("cache-control", "").lower()
    assert "immutable" in r.headers.get("cache-control", "").lower()
    # une image ABSENTE : 404 nommé, et le nom demandé est dans la phrase
    r = _api("GET", f"/api/cards/{did}/type/image/img_9.png")
    assert r.status_code == 404, r.text
    assert "img_9.png" in r.json()["detail"]
    # deck absent : 404 aussi, jamais 500
    r = _api("GET", "/api/cards/deck_deadbeef/type/image/img_1.png")
    assert r.status_code == 404, r.text


def test_aucune_route_ne_supprime_une_image_de_calque():
    """DÉCISION ÉCRITE : pas de purge à la suppression d'un slot. Un bloc
    supprimé se rattrape par Ctrl+Z, et une purge aurait effacé les octets
    pendant que l'annulation était encore possible. Le ramassage des images
    orphelines est un travail de la 3c, et c'est dit dans le code."""
    from app.main import app
    chemins = app.openapi().get("paths", {})
    routes = {p: sorted(v) for p, v in chemins.items() if "/type/image" in p}
    assert set(routes) == {"/api/cards/{did}/type/image",
                           "/api/cards/{did}/type/image/{name}"}, sorted(routes)
    assert routes["/api/cards/{did}/type/image"] == ["post"]
    assert routes["/api/cards/{did}/type/image/{name}"] == ["get"]
    py = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    assert "3c" in py, "la dette du ramassage n'est pas consignée"


def test_le_plafond_de_reduction_est_LE_MEME_des_trois_cotes():
    """`MAX_IMPORT_PX` existait déjà pour l'illustration (P1). P3 le REPREND —
    il ne l'IMPORTE PAS de `face.py` : la règle 8 interdit à une pièce
    d'importer le module d'une voisine. Le chiffre est donc écrit ici et
    ÉPINGLÉ contre les trois autres endroits qui le portent."""
    from app.services.cards import face as FA
    assert TY.MAX_IMPORT_PX == IMPORT_PX_ATTENDU
    assert FA.MAX_IMPORT_PX == IMPORT_PX_ATTENDU
    assert "const MAX_IMPORT_PX = 4096;" in _js()
    assert "const MAX_IMPORT_PX = 4096;" in MOD_FACE_JS.read_text(encoding="utf-8")
    py = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    for interdit in ("from .face", "from . import face", "import face"):
        assert interdit not in py, f"P3 importe une voisine : {interdit}"


def test_une_image_trop_grande_est_reduite_AU_SERVEUR():
    """Le client réduit avant d'envoyer (moins d'octets sur le fil) ; le
    serveur réduit QUAND MÊME, parce qu'un client n'est pas une garantie."""
    did = _did()
    r = _post_img(did, _png_bytes(IMPORT_PX_ATTENDU + 400, 600))
    assert r.status_code == 200, r.text
    px = r.json()["px"]
    assert max(px) == IMPORT_PX_ATTENDU, px
    # le rapport de forme est gardé (600 * 4096 / 4496 = 546,7 -> 547)
    assert px[1] == round(600 * IMPORT_PX_ATTENDU / (IMPORT_PX_ATTENDU + 400)), px
    # et une image plus petite n'est PAS agrandie
    r = _post_img(did, _png_bytes(40, 30))
    assert r.json()["px"] == [40, 30]


# ── 11.3 les exclusions : le juge de mise en page ───────────────────────────

def test_le_juge_NE_MESURE_RIEN_de_typographique_sur_un_calque_d_image():
    """Un calque d'image n'a pas de texte. Les colonnes typographiques du
    relevé valent donc `None` — pas 0, pas « ok » : un zéro se lit comme une
    mesure, un `None` se lit comme « sans objet ». Et il n'entre NI dans le
    plancher de lisibilité NI dans les signes hors police.

    Ce qui reste jugé : LA GÉOMÉTRIE. Une image qui sort du cadre de
    composition est un défaut de fabrication comme un autre — la coupe emporte
    ses pixels exactement comme elle emporterait des glyphes."""
    g = CT.geom("poker_eu", 300)
    txt = TY.norm_slot({"id": "titre", "text": "Créature", "read_pt": 12.0,
                        "box": [5.0, 5.0, 50.0, 10.0], "font": "Cinzel"})
    img = TY.norm_slot({"id": "fond", "kind": "image", "src": "img:img_1.png",
                        "box": [5.0, 20.0, 50.0, 30.0], "read_pt": 12.0,
                        "text": "Créature"})
    rep = TY.layout(g, [txt, img],
                    posed={"titre": 8.0, "fond": 8.0},
                    texts={"titre": "Créature", "fond": "Créature"})
    row = [r for r in rep["slots"] if r["id"] == "fond"][0]
    assert row["kind"] == "image"
    for k in ("size_px", "min_px", "read_pt", "read_px", "posed_pt",
              "under_read", "missing_glyphs"):
        assert row[k] is None, (k, row[k])
    assert "fond" not in rep["summary"]["under_read"]
    assert "fond" not in rep["summary"]["missing_glyphs"]
    # la géométrie, elle, est là et elle est jugée
    assert row["box_px"] and row["inside_safe"] is True
    assert row["src"] == "img:img_1.png" and row["fit"] == "contain"
    dehors = TY.norm_slot({"id": "hors", "kind": "image",
                           "box": [-20.0, -20.0, 10.0, 10.0]})
    rep2 = TY.layout(g, [dehors])
    assert rep2["summary"]["outside_safe"] == ["hors"]
    # CONTRE-ÉPREUVE : le slot de texte, lui, est mesuré comme avant.
    rowt = [r for r in rep["slots"] if r["id"] == "titre"][0]
    assert rowt["kind"] == "text"
    assert rowt["posed_pt"] == 8.0 and rowt["under_read"] is True
    assert rowt["size_px"] is not None and rowt["missing_glyphs"] is not None
    assert rep["summary"]["under_read"] == ["titre"]


# ── 11.4 le painter, mesuré au pixel ────────────────────────────────────────

# une source NON CARRÉE dans une boîte d'un AUTRE rapport : c'est le seul cas
# où « contain » et « cover » ne se confondent pas. 200 x 100 (rapport 2,0)
# dans 30 x 20 mm (rapport 1,5).
IMG_SRC_W, IMG_SRC_H = 200, 100
IMG_HEX = "#20c0ff"
IMG_BOX_MM = [10.0, 20.0, 30.0, 20.0]
IMG_TABLE = {"img_1.png": [IMG_SRC_W, IMG_SRC_H, IMG_HEX]}


def _slot_image(**kw) -> dict:
    s = {"id": "fond", "label": "Calque d'image", "kind": "image",
         "src": "img:img_1.png", "fit": "contain", "box": list(IMG_BOX_MM),
         # UN TEXTE QUI NE DOIT JAMAIS ÊTRE POSÉ : c'est le piège du test.
         "text": "Veilleur, Grand Oracle"}
    s.update(kw)
    return s


def test_le_calque_d_image_se_peint_dans_sa_boite_selon_le_fit(tmp_path):
    """« contain » entre ENTIÈREMENT dans la boîte (des bandes vides restent
    sur le petit côté) ; « cover » la REMPLIT et déborde — mais le débordement
    est DÉCOUPÉ, donc aucun pixel ne quitte la boîte. Les deux sont mesurés :
    la boîte de destination demandée à la toile ET le pavé réellement peint."""
    c = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="contain")],
                                "images": IMG_TABLE})
    v = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover")],
                                "images": IMG_TABLE})
    box = c["slots"][0]["box"]
    assert len(c["draws"]) == 1 and len(v["draws"]) == 1, (c["draws"], v["draws"])
    dc, dv = c["draws"][0]["dest"], v["draws"][0]["dest"]
    # contain : la largeur touche les deux bords, la hauteur non
    kc = min(box[2] / IMG_SRC_W, box[3] / IMG_SRC_H)
    assert dc[2] == pytest.approx(IMG_SRC_W * kc, abs=0.01)
    assert dc[3] == pytest.approx(IMG_SRC_H * kc, abs=0.01)
    assert dc[2] == pytest.approx(box[2], abs=0.01), "contain ne remplit pas la largeur"
    assert dc[3] < box[3] - 1, "contain remplit la hauteur : ce n'est plus contain"
    # ... et il est CENTRÉ : les deux bandes vides sont égales
    assert dc[0] == pytest.approx(box[0], abs=0.01)
    assert dc[1] - box[1] == pytest.approx((box[3] - dc[3]) / 2, abs=0.01)
    # cover : la hauteur touche les deux bords, la largeur déborde
    kv = max(box[2] / IMG_SRC_W, box[3] / IMG_SRC_H)
    assert dv[2] == pytest.approx(IMG_SRC_W * kv, abs=0.01)
    assert dv[3] == pytest.approx(box[3], abs=0.01), "cover ne remplit pas la hauteur"
    assert dv[2] > box[2] + 1, "cover ne déborde pas : ce n'est plus cover"
    assert dv[0] - box[0] == pytest.approx((box[2] - dv[2]) / 2, abs=0.01)
    # LE DÉBORDEMENT EST DÉCOUPÉ : le pavé peint tient dans la boîte.
    peint = v["draws"][0]["peint"]
    assert peint is not None
    assert peint[0] >= int(box[0]) - 1 and peint[1] >= int(box[1]) - 1
    assert peint[0] + peint[2] <= box[0] + box[2] + 1, peint
    assert peint[1] + peint[3] <= box[1] + box[3] + 1, peint
    # et les deux rendus ne sont PAS le même (sans quoi tout ce qui précède
    # serait vrai pour de mauvaises raisons)
    assert c["hash"] != v["hash"]
    # LA BANDE DU HAUT : vide en contain (lettrage), peinte en cover.
    haut = c["slots"][0]
    assert haut["coin_px"][3] == 0, "contain a peint la bande vide du haut"
    assert v["slots"][0]["coin_px"][3] > 0, "cover a laissé la bande du haut vide"
    # le centre est peint dans les deux cas, à la couleur de l'image
    for d in (c, v):
        assert d["slots"][0]["centre_px"][3] > 0
        assert d["slots"][0]["centre_px"][0] == 0x20, d["slots"][0]["centre_px"]


def test_le_cadrage_COVER_n_est_pas_un_CONTAIN_deguise(tmp_path):
    """MUTATION. Les deux cadrages ne diffèrent que par un `max` là où l'autre
    a un `min` : c'est la faute la plus facile à écrire et la plus difficile à
    voir, parce que sur une image DÉJÀ au rapport de la boîte les deux rendus
    sont identiques. On casse donc le `max` et on vérifie que le banc rougit."""
    ref = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="contain")],
                                  "images": IMG_TABLE})
    mut = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover")],
                                  "images": IMG_TABLE},
                       mutations=(('const k = (mode === "cover")\r\n'
                                   "      ? Math.max(b[2] / sw, b[3] / sh) "
                                   ": Math.min(b[2] / sw, b[3] / sh);",
                                   "const k = Math.min(b[2] / sw, b[3] / sh);"),))
    assert mut["hash"] == ref["hash"], \
        "« cover » ramené à « contain » ne change pas le rendu : le test de fit ne prouve rien"
    vrai = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover")],
                                   "images": IMG_TABLE})
    assert vrai["hash"] != ref["hash"]


def test_les_quatre_gabarits_ne_bougent_pas_apres_le_calque_d_image(tmp_path):
    """Le seuil de non-régression de la tâche : chacun des quatre gabarits
    livrés, rendu AVEC les trois clés neuves à leur défaut, doit sortir le même
    tampon qu'un document d'AVANT (les clés absentes). Aucun gabarit ne nomme
    `kind` : tous héritent de « text », et « text » est exactement ce que le
    painter faisait avant qu'il y ait un `kind`."""
    g = CT.geom("poker_eu", 300)
    for pid in sorted(TY.PRESETS):
        slots = TY.preset_slots(pid, g)
        for s in slots:
            assert s["kind"] == "text" and s["src"] == "" and s["fit"] == "contain", \
                (pid, s["id"])
        avant = _banc_plaque(tmp_path, {"slots": slots,
                                        "drop": ["kind", "src", "fit"]})
        apres = _banc_plaque(tmp_path, {"slots": slots})
        assert apres["hash"] == avant["hash"], f"gabarit « {pid} » a bougé"
        assert apres["n_textes"] > 0 and apres["draws"] == [], pid


def test_le_calque_d_image_ne_pose_AUCUN_GLYPHE(tmp_path):
    """Le slot porte un `text` — hérité du vocabulaire commun — et le painter
    doit l'IGNORER. Le banc compte les appels de dessin : zéro pavé de glyphe,
    et l'URL demandée est celle de la route de la pièce."""
    d = _banc_plaque(tmp_path, {"slots": [_slot_image()], "images": IMG_TABLE})
    assert d["n_textes"] == 0, "un calque d'image a posé du texte"
    assert d["labels"] == [], d["labels"]
    assert d["urls"] == ["image/img_1.png"], d["urls"]
    # CONTRE-ÉPREUVE : le même slot en `kind: "text"` pose bien ses glyphes.
    t = _banc_plaque(tmp_path, {"slots": [_slot_image(kind="text")],
                                "images": IMG_TABLE})
    assert t["n_textes"] > 0
    assert t["draws"] == []


def test_la_plaque_passe_SOUS_l_image_et_l_opacite_porte_sur_les_deux(tmp_path):
    """Même règle que pour le texte, et pour la même raison : peinte au-dessus,
    la plaque effacerait ce qu'elle est censée porter. La bande vide du
    lettrage (contain) est l'endroit où la plaque se lit toute seule."""
    slot = _slot_image(fit="contain", plate_color="#3050a0", plate_alpha=0.8)
    d = _banc_plaque(tmp_path, {"slots": [slot], "images": IMG_TABLE})
    row = d["slots"][0]
    # la bande du haut ne porte QUE la plaque : bleu, à 204/255
    assert row["coin_px"][3] == 204, row["coin_px"]
    assert row["coin_px"][:3] == [0x30, 0x50, 0xa0], row["coin_px"]
    # le centre porte l'IMAGE, opaque, par-dessus la plaque
    assert row["centre_px"][3] == 255, row["centre_px"]
    assert row["centre_px"][:3] == [0x20, 0xc0, 0xff], row["centre_px"]
    # MUTATION : la plaque peinte APRÈS l'image l'effacerait — le banc le voit.
    mut = _banc_plaque(tmp_path, {"slots": [slot], "images": IMG_TABLE},
                       mutations=(
        ("    drawPlate(ctx, slot, g, { box: b });\r\n    if (!rec || !rec.ok) {",
         "    if (!rec || !rec.ok) {"),
        ("      ctx.drawImage(rec.img, r[0], r[1], r[2], r[3]);\r\n      ctx.restore();",
         "      ctx.drawImage(rec.img, r[0], r[1], r[2], r[3]);\r\n      ctx.restore();"
         "\r\n      drawPlate(ctx, slot, g, { box: b });"),
    ))
    assert mut["slots"][0]["centre_px"][:3] != [0x20, 0xc0, 0xff], \
        "la plaque au-dessus de l'image ne change rien : l'ordre n'est pas mesuré"

    # L'OPACITÉ DU SLOT PORTE SUR L'IMAGE : 40 % de 255 = 102.
    o = _banc_plaque(tmp_path, {"slots": [_slot_image(opacity=40)],
                                "images": IMG_TABLE})
    assert o["draws"][0]["alpha"] == pytest.approx(0.4, abs=1e-6)
    assert o["slots"][0]["centre_px"][3] == 102, o["slots"][0]["centre_px"]


def test_une_image_absente_laisse_un_damier_ET_SON_NOM(tmp_path):
    """404, fichier effacé à la main, deck à moitié copié : l'aperçu doit dire
    LEQUEL manque. Un rectangle vide se lit comme « le calque est cassé » ; un
    damier et un nom se lisent comme « ce fichier-là n'est pas arrivé ». C'est
    un ÉTAT, pas une erreur — le painter ne lève pas."""
    d = _banc_plaque(tmp_path, {"slots": [_slot_image(src="img:img_9.png")],
                                "images": IMG_TABLE})
    assert d["exceptions"] == [], d["exceptions"]
    assert d["draws"] == [], "une image absente a quand même été dessinée"
    # le damier occupe la boîte
    assert d["slots"][0]["centre_px"][3] > 0, "aucun damier n'a été posé"
    # ... et le NOM du fichier manquant est écrit dessus
    assert any("img_9.png" in t for t in d["labels"]), d["labels"]
    # une image PRÉSENTE, elle, ne pose pas de damier (contre-épreuve)
    ok = _banc_plaque(tmp_path, {"slots": [_slot_image()], "images": IMG_TABLE})
    assert ok["labels"] == []
    assert ok["hash"] != d["hash"]


def test_le_cache_d_images_NE_REDECODE_PAS_a_chaque_frame(tmp_path):
    """Le painter tourne à chaque frame ; sans cache, chaque frame redécoderait
    le PNG. Le banc compte les URL demandées : deux calques qui portent LE MÊME
    fichier, sur DEUX passes de painter, n'en demandent qu'une.

    Et le cache garde un ÉTAT, jamais une promesse rejetée : un fichier absent
    y entre comme « pas là » (le damier), ce qui est un état de la carte, pas
    une panne qui traverserait le painter et noircirait les sept autres
    pièces — le banc vérifie qu'aucune exception n'est remontée."""
    d = _banc_plaque(tmp_path, {
        "slots": [_slot_image(), dict(_slot_image(), id="fond2",
                                      box=[10.0, 55.0, 30.0, 20.0]),
                  dict(_slot_image(), id="fond3", src="img:img_9.png",
                       box=[10.0, 78.0, 30.0, 8.0])],
        "images": IMG_TABLE, "passes": 2})
    assert d["exceptions"] == [], d["exceptions"]
    assert sorted(d["urls"]) == ["image/img_1.png", "image/img_9.png"], d["urls"]
    # les deux calques du même fichier sont bien dessinés tous les deux, aux
    # deux passes : le cache sert, il ne remplace pas le dessin.
    assert len(d["draws"]) == 4, d["draws"]


def test_un_calque_d_image_sans_source_ne_peint_RIEN(tmp_path):
    """`src` vide = le calque vient de naître, l'utilisateur n'a pas encore
    déposé son image. Ce n'est pas un manque : c'est un état d'attente, et il
    ne salit pas la carte d'un damier."""
    vide = _banc_plaque(tmp_path, {"slots": [_slot_image(src="")],
                                   "images": IMG_TABLE})
    rien = _banc_plaque(tmp_path, {"slots": [_slot_image(src="", on=False)],
                                   "images": IMG_TABLE})
    assert vide["draws"] == [] and vide["labels"] == []
    assert vide["hash"] == rien["hash"], "un calque sans source a peint"
    # ... PAS MÊME SA PLAQUE, et c'est exactement ce que fait le painter d'un
    # bloc de texte vide : un cartouche sans son contenu est un défaut visible
    # que personne n'a demandé.
    plaque = _banc_plaque(tmp_path, {"slots": [_slot_image(src="",
                                                           plate_color="#3050a0")],
                                     "images": IMG_TABLE})
    assert plaque["hash"] == rien["hash"], "la plaque d'un calque vide est peinte"


# LE TEST DE ROTATION, rédigé par l'agent T2-3b et JAMAIS EXÉCUTÉ ; joué et
# calibré par la ronde T3. Son auteur avait prévu ±2 px « au premier run » en
# RAISONNANT sur la rastérisation par transformée inverse. MESURE : l'écart
# maximum est de 0,39 px sur les huit valeurs (boîte 153,61 x 271,72 +
# 354,33 x 236,22 px ; tournée, on lit 213 / 213 / 236 / 354 pour 212,66 /
# 212,67 / 236,22 / 354,33 attendus). La tolérance est donc RESSERRÉE à ±1 px :
# c'est l'arrondi d'échantillonnage au demi-pixel, et rien d'autre — à ±2 une
# dérive d'un pixel serait passée. La propriété défendue : `drawImgSlot`
# (mod-type.js) fait save() -> rotation -> rect(b)+clip()+drawImage, et la
# découpe vit donc dans le repère TOURNÉ ; le test épingle cet ordre contre un
# refactor qui sortirait le clip de la rotation.
ROT_TOL_PX = 1

def test_le_cadrage_SURVIT_A_LA_ROTATION(tmp_path):
    """LA DÉCOUPE TOURNE AVEC LA BOÎTE, et rien ne le disait.

    Un calque tourné à 90° est le cas où les deux fautes possibles se
    séparent : si la découpe était posée AVANT la rotation (ou hors d'elle),
    les pixels retenus seraient ceux du rectangle DROIT, et l'image dépasserait
    de la boîte visible sur ses deux petits côtés. Le pavé réellement peint
    doit donc être celui de la boîte TOURNÉE — largeur et hauteur échangées —
    et c'est ce qu'on mesure.

    Le rectangle de destination, lui, ne bouge PAS : la rotation vit dans la
    transformation de la toile, pas dans la géométrie du cadrage. Deux fois la
    même valeur serait le signe qu'on l'applique deux fois."""
    droit = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover")],
                                    "images": IMG_TABLE})
    tourne = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover", rotate=90)],
                                     "images": IMG_TABLE})
    b = droit["slots"][0]["box"]
    cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
    # la boîte tournée d'un quart de tour autour de son centre : côtés échangés
    attendu = [cx - b[3] / 2, cy - b[2] / 2, b[3], b[2]]
    peint = tourne["draws"][0]["peint"]
    assert peint is not None
    for i, (v, a) in enumerate(zip(peint, attendu)):
        assert abs(v - a) <= ROT_TOL_PX, (i, peint, attendu)
    # CONTRE-ÉPREUVE : sans rotation, c'est la boîte droite qui est remplie.
    droit_peint = droit["draws"][0]["peint"]
    for i, (v, a) in enumerate(zip(droit_peint, b)):
        assert abs(v - a) <= ROT_TOL_PX, (i, droit_peint, b)
    # ... et les deux ne se confondent pas (la boîte n'est pas carrée)
    assert abs(peint[2] - droit_peint[2]) > 50, (peint, droit_peint)
    # LE CADRAGE EST LE MÊME OBJET : la rotation n'entre pas dans le calcul.
    assert tourne["draws"][0]["dest"] == droit["draws"][0]["dest"]
    assert tourne["hash"] != droit["hash"]


def test_un_CLIP_HISSE_HORS_DE_LA_ROTATION_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : la découpe posée AVANT la rotation. C'est le
    refactor plausible — « le clip ne dépend que de la boîte, sortons-le de la
    branche » — et il donne une image qui déborde de sa boîte visible sur ses
    deux petits côtés, sans que rien d'autre ne bouge. Le test ci-dessus
    mesure donc bien cet ordre-là."""
    mut = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover", rotate=90)],
                                  "images": IMG_TABLE}, mutations=(
        ("      ctx.beginPath();\r\n      ctx.rect(b[0], b[1], b[2], b[3]);\r\n"
         "      ctx.clip();\r\n", ""),
        # L'ANCRE PORTE LE `if (!file) return;` QUI LA PRÉCÈDE, et c'est une
        # correction de la phase 5-T2 : `drawShapeSlot` ouvre sa passe sur la
        # MÊME paire de lignes (opacité puis rotation — c'est justement le
        # squelette partagé qu'on a voulu), et l'ancre courte est devenue
        # ambiguë. Le banc l'a REFUSÉE au lieu de muter la mauvaise fonction.
        ("    if (!file) return;\r\n    ctx.save();\r\n"
         "    ctx.globalAlpha = clamp(num(slot.opacity, 100, 0, 100) / 100, 0, 1);\r\n"
         "    if (slot.rotate) {",
         "    if (!file) return;\r\n    ctx.save();\r\n"
         "    ctx.globalAlpha = clamp(num(slot.opacity, 100, 0, 100) / 100, 0, 1);\r\n"
         "    ctx.beginPath();\r\n    ctx.rect(b[0], b[1], b[2], b[3]);\r\n"
         "    ctx.clip();\r\n    if (slot.rotate) {"),))
    b = _banc_plaque(tmp_path, {"slots": [_slot_image(fit="cover")],
                                "images": IMG_TABLE})["slots"][0]["box"]
    cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
    attendu = [cx - b[3] / 2, cy - b[2] / 2, b[3], b[2]]
    peint = mut["draws"][0]["peint"]
    assert peint is not None
    ecarts = [i for i, (v, a) in enumerate(zip(peint, attendu))
              if abs(v - a) > ROT_TOL_PX]
    assert ecarts, ("le clip hissé ne change rien : le test ne mesure pas "
                    "l'ordre", peint, attendu)


# ── 11.5 les exclusions : les trois passes d'encre ──────────────────────────

MUT_MEAS = ("\r\n})();", "\r\n  globalThis.__meas = () => MEAS;\r\n})();")


def test_les_passes_d_encre_IGNORENT_les_calques_d_image(tmp_path):
    """LE RELEVÉ DU PAINTER (`MEAS`) est l'entrée des trois passes d'encre — le
    contrôle photométrique, le relevé du halo, le second tirage. Un calque
    d'image n'y entre pas : il n'a pas de glyphe, donc pas de taux de survie,
    pas de contraste, pas de corps composé. Y entrer l'aurait fait compter
    comme un « slot vide » — un défaut annoncé qui n'existe pas.

    Le banc se fait ouvrir la fermeture par une mutation (patron `__solo`) et
    lit les clés du relevé."""
    opts = {"slots": [_slot_image(), dict(_slot_image(kind="text"), id="titre")],
            "images": IMG_TABLE}
    d = _banc_plaque(tmp_path, opts, mutations=(MUT_MEAS,))
    assert d["meas"] is not None, "la porte du banc ne s'est pas ouverte sur MEAS"
    assert d["meas"] == ["titre"], d["meas"]

    # MUTATION : le calque d'image entre dans le relevé -> il entrerait dans
    # les trois passes, et le banc le voit.
    mut = _banc_plaque(tmp_path, opts, mutations=(
        MUT_MEAS,
        ('if (isImage(slot)) { drawImgSlot(ctx, slot, geom); return; }',
         'if (isImage(slot)) { drawImgSlot(ctx, slot, geom); }'),
    ))
    assert "fond" in mut["meas"], \
        "le calque d'image entre dans le relevé et le banc ne le voit pas"


def test_les_trois_passes_d_encre_NOMMENT_l_exclusion_des_images():
    """Les trois passes tournent sur `MEAS` ou sur `slots()` — la première est
    déjà propre par construction, les deux autres doivent le DIRE. Une garde
    écrite est ce qui empêche une quatrième passe de reprendre l'oubli."""
    src = _js()
    # le helper d'exclusion existe une seule fois et il est nommé
    assert src.count("function isImage(") == 1
    # les deux passes qui repartent de `slots()` filtrent explicitement
    assert "const live = slots().filter((s) => s.on && !isImage(s)\n" in src, \
        "le second tirage prend encore les calques d'image"
    assert "if (!slot || isImage(slot)) return;" in src, \
        "le contrôle photométrique ne dit pas qu'il saute les images"
    # LE QUATRIÈME LIEU DE MESURE, celui qu'on oublie : le contrôle de SÉRIE
    # remet en page chaque carte du deck. Un calque d'image y aurait compté
    # « vide » 200 fois.
    assert "const a = slots().filter((s) => s.on && !isImage(s));" in src, \
        "le contrôle de série mesure encore les calques d'image"
    # et le compte d'appels de `soloClone` n'a pas bougé : la quatrième passe
    # devra passer par le helper (règle posée en T1).
    assert src.count("soloClone(") == 4, "compte d'appels de soloClone modifié"
    # `isImage` est le SEUL test de nature du module : personne ne compare
    # `kind === "image"` à la main ailleurs (ce serait le prochain oubli).
    assert src.count('kind === "image"') == 1, \
        "la nature d'un bloc est testée hors de `isImage`"


# ── 11.6 l'éditeur ──────────────────────────────────────────────────────────

def _slots_image_verrou() -> list:
    a = TY.norm_slot({"id": "fond", "label": "Calque d'image", "kind": "image",
                      "src": "img:img_1.png", "fit": "cover",
                      "box": [8.0, 20.0, 46.0, 30.0]})
    b = TY.norm_slot({"id": "titre", "label": "Titre", "text": "Veilleur",
                      "box": [10.0, 5.0, 40.0, 10.0]})
    return [a, b]


def test_le_panneau_de_calque_d_image_MASQUE_la_typographie(tmp_path):
    """Le panneau bascule ses sections selon le `kind`. Un calque d'image n'a
    ni police, ni corps, ni casse, ni césure — les afficher inertes aurait été
    onze réglages qui ne font rien. Il gagne en échange sa zone de dépôt et son
    cadrage. Ce qui RESTE des deux côtés : la boîte, la rotation, l'opacité, la
    plaque, la face."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _slots_image_verrou(),
                                          "sel": "fond"}})
    insp = d["insp"]
    assert insp, "le panneau de bloc est vide"
    # ce qu'un calque d'image N'A PAS
    for absent in ("cf-type-font", 'data-k="size_pt"', 'data-k="min_pt"',
                   'data-k="track"', 'data-k="leading"', 'data-k="read_pt"',
                   'data-k="arc"', "cf-type-text", 'data-k="caps"',
                   'data-k="align"', 'data-k="outline"', 'data-k="valign"',
                   "cf-type-ocol", "cf-type-scol", 'data-k="just_max"'):
        assert absent not in insp, f"réglage typographique offert à une image : {absent}"
    # ce qu'il A
    for present in ("cf-type-drop", 'data-k="fit"', 'data-k="bx"',
                    'data-k="bw"', 'data-k="rotate"', 'data-k="opacity"',
                    "cf-type-pcol", 'data-k="side"', "cf-type-file",
                    "cf-type-dup", "cf-type-center"):
        assert present in insp, f"le panneau d'image n'offre pas : {present}"
    # LE KIND EST MONTRÉ, PAS BASCULÉ : aucun contrôle ne change la nature d'un
    # bloc déjà né (décision de tâche — voir le commentaire du module).
    assert 'data-k="kind"' not in insp, "le panneau bascule le kind d'un bloc né"
    assert "cf-type-kind" in insp, "la nature du bloc n'est pas dite"
    # LE PIED DE LA SECTION « BOÎTE » PORTE LES MESURES DE L'IMAGE, pas celles
    # d'un corps composé — c'est le même conteneur (`cf-type-meas`) et il est
    # réécrit après chaque mise en page (voir `syncInspMeas`).
    assert 'class="cf-type-meas"' in insp
    assert "px de toile" in insp
    assert "demandé, pas encore composé" not in insp, \
        "le pied d'un calque d'image parle encore de corps typographique"
    # ... et il dit OÙ ce calque se peint : la bande z=60 passe au-dessus du
    # cadre de base et sous le décor haut.
    assert "au-dessus du cadre de base et sous le décor haut" in insp

    # CONTRE-ÉPREUVE : sur un slot de TEXTE, le panneau n'a pas changé.
    t = _banc_verrou(tmp_path, {"state": {"slots": _slots_image_verrou(),
                                          "sel": "titre"}})
    for present in ("cf-type-font", 'data-k="size_pt"', 'data-k="caps"',
                    "cf-type-text", 'data-k="bx"', "cf-type-pcol",
                    'data-k="arc"', 'data-k="just_max"', "cf-type-scol",
                    "cf-type-dup", 'data-k="rotate"', 'data-k="opacity"'):
        assert present in t["insp"], f"le panneau de texte a perdu : {present}"
    assert "cf-type-drop" not in t["insp"]
    assert 'data-k="fit"' not in t["insp"]


def test_la_liste_badge_la_NATURE_du_bloc(tmp_path):
    """La liste est la seule vue où les deux natures se croisent : elle doit
    les distinguer d'un coup d'œil, et dire quel fichier porte un calque."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _slots_image_verrou(),
                                          "sel": "fond"}})
    liste = d["liste"]
    assert liste.count('class="cf-type-row') == 2, liste
    assert "cf-type-kind" in liste, "aucun badge de nature dans la liste"
    assert "img_1.png" in liste, "la liste ne dit pas quel fichier porte le calque"
    # le badge « vide » (slot sans glyphe) ne doit JAMAIS toucher un calque
    # d'image : il n'a pas de glyphe par nature.
    ligne = liste.split('data-id="fond"')[1].split("cf-type-row")[0]
    assert ">vide<" not in ligne, ligne


def test_le_calque_d_image_NAIT_par_un_geste_a_lui(tmp_path):
    """DÉCISION : le `kind` se pose À LA NAISSANCE. « + Image » crée un calque
    d'image, « + Slot » un bloc de texte ; le panneau montre la nature sans la
    changer. Basculer un bloc existant aurait changé le SENS de ses réglages
    sous la main de l'utilisateur (un `src` sur un bloc de texte ne veut rien
    dire, une police sur un calque d'image non plus) — et la manœuvre honnête,
    créer l'autre puis supprimer le premier, est déjà à deux clics."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}})
    assert "cf-type-addimg" in d["panneau"], "aucun geste ne crée un calque d'image"
    assert "cf-type-add" in d["panneau"]
    src = _js()
    # `addSlot` n'a pas changé de nature, `addImgSlot` naît en image
    assert "function addImgSlot()" in src
    assert 'kind: "image"' in src
    # et AUCUN chemin d'édition n'écrit `kind` sur un bloc existant
    assert "patchSlot(id, { kind:" not in src
    assert 'patchSlot(id, { kind"' not in src


def test_l_import_du_panneau_reduit_AVANT_d_envoyer(tmp_path):
    """Le client réduit à `MAX_IMPORT_PX` avant l'envoi — le serveur le refait
    de toute façon (il ne croit pas le client), mais un fichier de 40 Mo qui
    part pour revenir à 4096 px est un aller-retour payé pour rien."""
    src = _js()
    i = src.index("async function importImage(")
    corps = src[i:src.index("\n  function ", i)]
    assert "MAX_IMPORT_PX" in corps, "l'import du panneau ne borne pas le côté"
    assert 'M.api.raw("POST", "image"' in corps, "l'import ne passe pas par la route"
    assert corps.index("MAX_IMPORT_PX") < corps.index('M.api.raw'), \
        "la réduction a lieu APRÈS l'envoi"
    # dépôt ET collage, les deux patrons de P1
    assert 'drop.addEventListener("drop"' in src
    assert '"paste"' in src


# ═══════ 12. LA RONDE DE REVUE DE LA TÂCHE 2 ════════════════════════════════
# Ce que la revue adverse a mesuré, et qui est corrigé ici. Deux bloquants
# (un lien de garde posé sur le mauvais opérande, une course d'écriture), deux
# moyens (une bombe de pixels, un cliquet de lint que le refactor avait
# contourné), deux bas (une ceinture manquante, un `match` là où le dépôt
# écrit `fullmatch` partout ailleurs).

# ── 12.1 B1 : les deux normaliseurs, ÉPROUVÉS L'UN CONTRE L'AUTRE ───────────
# La parité des tables était pinnée par des MATCHS DE SOURCE (« cette ligne est
# dans le fichier »). Un match de source ne dit rien de ce que le code FAIT :
# `SRC_RE.test(String(r.src == null ? "" : r.src)) ? String(r.src) : ""` porte
# sa garde nulle sur l'opérande TESTÉ et pas sur le RÉSULTAT — le motif accepte
# la chaîne vide, donc le test passe, et c'est `String(undefined)` qui est
# rangé. Les 21 slots des gabarits sortaient avec `src: "undefined"`.
#
# Le remède n'est pas un pin de plus sur la ligne : c'est de faire TOURNER les
# deux normaliseurs sur la même batterie et de comparer leurs sorties.

MUT_NORM = ("\r\n})();", "\r\n  globalThis.__norm = normSlot;\r\n})();")

# la batterie : le document VIDE (le cas de B1), les absences explicites, un
# slot d'AVANT la 3b, et des entrées hostiles sur chaque clé neuve.
NORM_BATTERIE = [
    {},
    {"src": None},
    {"src": ""},
    {"id": "titre", "label": "Titre", "box": [10.0, 5.0, 40.0, 10.0],
     "font": "Cinzel", "size_pt": 14.0, "text": "Veilleur"},
    {"kind": "image", "src": "img:img_3.png", "fit": "cover"},
    {"kind": " IMAGE ", "fit": "COVER", "src": "img:img_12.png"},
    {"kind": "video", "fit": "fill", "src": "img:../../meta.json"},
    {"kind": 7, "fit": None, "src": 42},
    {"src": "img:img_1.png "},
    {"src": "IMG:IMG_1.PNG"},
    {"src": True},
    {"kind": "image"},
    {"id": "", "label": "", "box": "pas une boite", "opacity": "beaucoup"},
]


def test_les_deux_NORMALISEURS_rendent_le_MEME_slot(tmp_path):
    """PARITÉ D'EXÉCUTION, pas de source. On ouvre la fermeture du module
    (patron `__solo`), on fait tourner `normSlot` sur la batterie, et on compare
    clé par clé au `norm_slot` du backend. C'est le seul test qui aurait vu
    « undefined » : la ligne, elle, se lisait très bien."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "norm": NORM_BATTERIE},
                     mutations=(MUT_NORM,))
    js = d["norm"]
    assert js, "la porte du banc ne s'est pas ouverte sur normSlot"
    assert len(js["un"]) == len(NORM_BATTERIE)
    for i, entree in enumerate(NORM_BATTERIE):
        py = TY.norm_slot(entree, i)
        ecran = js["un"][i]
        assert set(ecran) == set(py), \
            f"[{i}] clés divergentes : {sorted(set(ecran) ^ set(py))}"
        for k in sorted(py):
            assert ecran[k] == py[k], f"[{i}] {k} : écran {ecran[k]!r} != backend {py[k]!r}"
    # LE CAS DE B1, NOMMÉ : un slot sans `src` n'a pas de source — pas la
    # chaîne « undefined », qui est une source, et illégale.
    assert js["un"][0]["src"] == ""
    assert js["un"][1]["src"] == ""


def test_le_normaliseur_de_l_ecran_est_IDEMPOTENT(tmp_path):
    """`normSlot(normSlot(x)) == normSlot(x)`. C'est la propriété que le dépôt
    exige des slots de modèles (« la normalisation ne change RIEN — cette
    idempotence est la preuve que la donnée est propre ») ; l'écran doit la
    tenir aussi, sans quoi la deuxième passe RÉPARE la première et le document
    enregistré n'est pas celui qu'on relit."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "norm": NORM_BATTERIE},
                     mutations=(MUT_NORM,))
    for i in range(len(NORM_BATTERIE)):
        assert d["norm"]["deux"][i] == d["norm"]["un"][i], \
            f"[{i}] la seconde passe change le slot : {d['norm']['un'][i]}"


def test_les_gabarits_de_l_ecran_ne_portent_AUCUNE_source(tmp_path):
    """La conséquence visible de B1 : les 21 slots des quatre gabarits
    passaient par `normSlot` et en ressortaient avec `src: "undefined"` — une
    valeur que `norm_slot` refuse, donc un document que le backend RÉPARE au
    chargement. Un document réparé à chaque tour n'est pas un document."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "seeded": False,
                                          "preset": "champion", "sel": ""}})
    slots = d["slots"]
    assert len(slots) == len(TY.PRESETS["champion"]["slots"]), len(slots)
    for s in slots:
        assert s["src"] == "", f"{s['id']} : src = {s['src']!r}"
        assert s["kind"] == "text" and s["fit"] == "contain", s["id"]
        # ... et le backend n'a RIEN à réparer : il rend le slot tel quel.
        assert TY.norm_slot(s) == s, f"{s['id']} : le backend le corrige"


# ── 12.2 B2 : six imports simultanés font six fichiers ──────────────────────

def _api_ensemble(appels):
    """N requêtes lancées ENSEMBLE sur la même application, dans une seule
    boucle. `asyncio.gather` les entrelace vraiment : le travail disque part en
    `to_thread`, donc deux imports décodent et écrivent en même temps — c'est
    la condition de course, jouée et pas supposée."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=60.0) as c:
            return await asyncio.gather(
                *[c.request(m, p, **kw) for m, p, kw in appels],
                return_exceptions=True)
    return asyncio.run(go())


def test_six_imports_SIMULTANES_font_six_fichiers():
    """LA COURSE, REJOUÉE. Deux Ctrl+V rapprochés, deux onglets, un dépôt
    multiple : rien n'empêche deux imports de se croiser. Ils lisaient tous le
    même « prochain numéro », écrivaient tous le même `.tmp`, et se le
    reprenaient — sur Windows, `replace` sur un fichier tenu par un autre lève
    WinError 32, c'est-à-dire un 500 sur une pièce qui n'en fait jamais.

    Après le remède : chaque import obtient SON numéro (création exclusive,
    `O_CREAT|O_EXCL`, numéro suivant à chaque collision) et SON temporaire."""
    did = _did()
    n = 6
    corps = [_png_bytes(8 + i, 5 + i) for i in range(n)]
    reps = _api_ensemble([("POST", f"/api/cards/{did}/type/image",
                           {"content": c,
                            "headers": {"Content-Type": "application/octet-stream"}})
                          for c in corps])
    for r in reps:
        assert not isinstance(r, BaseException), repr(r)
        assert r.status_code != 500, r.text[:300]
        assert r.status_code == 200, (r.status_code, r.text[:300])
    noms = sorted(r.json()["file"] for r in reps)
    assert len(set(noms)) == n, f"deux imports ont reçu le même nom : {noms}"
    sur_disque = sorted(p.name for p in _type_dir(did).glob("img_*.png"))
    assert sur_disque == noms, (sur_disque, noms)
    # SIX FICHIERS, SIX IMAGES DISTINCTES : aucune n'a été écrasée par une autre
    from PIL import Image
    tailles = set()
    for nom in sur_disque:
        with Image.open(_type_dir(did) / nom) as im:
            tailles.add(im.size)
    assert tailles == {(8 + i, 5 + i) for i in range(n)}, tailles
    # aucun temporaire n'a survécu, et aucun n'est partagé
    assert not list(_type_dir(did).glob("*.tmp")), \
        sorted(p.name for p in _type_dir(did).iterdir())


def test_le_temporaire_d_un_import_est_A_LUI_SEUL():
    """Le nom du temporaire porte de quoi le distinguer : deux imports qui
    partagent `img_3.png.tmp` se marchent dessus même quand ils finissent par
    obtenir deux numéros différents."""
    src = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    i = src.index("def _store_slot_image(")
    corps = src[i:src.index("\ndef ", i + 10)]
    assert "uuid" in corps, "le temporaire n'a rien qui le distingue"
    assert "O_EXCL" in corps, "le numéro n'est pas réservé par création exclusive"
    assert corps.count(".tmp") >= 1


def test_l_ecran_refuse_un_SECOND_import_pendant_le_premier():
    """La garde de vol côté écran. `M.busy` grise le panneau, mais le CLAVIER
    passe à travers : deux Ctrl+V rapprochés lançaient deux imports. Le refus
    est ici un NON-DÉPART, pas un envoi annulé."""
    src = _js()
    i = src.index("async function importImage(")
    corps = src[i:src.index("\n  function ", i)]
    assert "IMPORTING" in corps, "aucune garde de vol sur l'import"
    assert corps.index("IMPORTING") < corps.index('M.api.raw'), \
        "la garde est posée APRÈS l'envoi"
    # ... et elle est relâchée quoi qu'il arrive
    assert "finally" in corps and "IMPORTING = false" in corps


# ── 12.3 M3 : la bombe de pixels ────────────────────────────────────────────

def _bombe_png(w: int, h: int) -> bytes:
    """Un PNG VALIDE et minuscule qui déclare `w` x `h` (voir la jumelle de
    test_cards_texture.py : la même arme, sur l'autre porte)."""
    import struct as _s
    import zlib as _z

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (_s.pack(">I", len(data)) + typ + data
                + _s.pack(">I", _z.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = _s.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    co = _z.compressobj(1)
    ligne = b"\x00" * (w + 1)
    morceaux = [co.compress(ligne) for _ in range(h)]
    morceaux.append(co.flush())
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", b"".join(morceaux)) + chunk(b"IEND", b""))


def test_une_BOMBE_DE_PIXELS_est_refusee_sur_ses_DIMENSIONS():
    """Le corps est pesé, la TRAME non — et c'est la trame qui coûte. 64 Mo de
    plafond ne disent rien des 144 millions de pixels qu'un demi-mégaoctet peut
    déclarer, soit un demi-gigaoctet de tampon PAR REQUÊTE. Le refus se prend
    sur les dimensions DÉCLARÉES, lues dans l'en-tête, avant tout décodage."""
    from PIL import Image
    did = _did()
    bombe = _bombe_png(12000, 12000)
    assert len(bombe) < 1_000_000, len(bombe)
    with Image.open(io.BytesIO(bombe)) as im:
        assert im.size == (12000, 12000)
    assert TY.IMG_MAX_PIXELS == 32 * 1024 * 1024
    r = _post_img(did, bombe)
    assert r.status_code == 413, (r.status_code, r.text[:200])
    detail = r.json()["detail"]
    assert "12000" in detail and "pixel" in detail.lower(), detail
    assert not list(_type_dir(did).glob("img_*.png")), "la bombe a été écrite"
    # une image normale, elle, passe : le plafond ne gêne personne
    assert _post_img(did, _png_bytes(40, 30)).status_code == 200
    # ORDRE ÉPINGLÉ : après `img.load()`, le tampon est déjà alloué.
    py = pathlib.Path(TY.__file__).read_text(encoding="utf-8")
    i = py.index("def _decode_bounded(")
    corps = py[i:py.index("\ndef ", i + 10)]
    assert corps.index("IMG_MAX_PIXELS") < corps.index("img.load()"), \
        "les dimensions sont contrôlées APRÈS le décodage"
    # et le plafond des deux pièces est le MÊME chiffre
    from app.services.cards import texture as TX
    assert TX.IMG_MAX_PIXELS == TY.IMG_MAX_PIXELS


# ── 12.4 L5 : la ceinture du lecteur ────────────────────────────────────────

def test_le_lecteur_d_image_porte_SA_PROPRE_liste_blanche():
    """Doctrine `deck_dir` : motif PUIS confinement, et le second garde-fou vit
    DANS la fonction qui compose le chemin — pas seulement chez son appelant.
    Un ramasse-miettes de la 3c ou une palette qui appellerait `_read_slot_image`
    en direct n'hérite de rien de la route."""
    did = _did()
    assert _post_img(did, _png_bytes(8, 5)).status_code == 200
    assert TY._read_slot_image(did, "img_1.png") is not None
    for nom in ("../meta.json", "..", "job.json", "img_1.PNG", "",
                "img_1.png\n", "img_1.png ", "deck.json"):
        assert TY._read_slot_image(did, nom) is None, nom
    # ... et l'identifiant de deck aussi : la fonction ne suppose pas que son
    # appelant a vérifié.
    assert TY._read_slot_image("pas_un_deck", "img_1.png") is None


# ═══════ 13. LA PALETTE D'ÉLÉMENTS (3b-T3, spec §6.1) ═══════════════════════
# Trois entrées GÉNÉRIQUES toujours là, plus les éléments du MODÈLE dont le jeu
# est né. Le deck n'en garde AUCUNE copie (models.py:instancier — « c'est une
# graine, pas un lien ») : le seul fil est `doc.type.preset`, et l'écran va
# chercher le reste au catalogue.
#
# LA QUESTION D'ARCHITECTURE DE LA TÂCHE, ET SA RÉPONSE. `M.api` est confiné à
# /api/cards/{did}/type (règle 8) ; la liste des modèles vit à
# /api/cards/models, hors de tout sous-préfixe de pièce. La pièce ne s'y rend
# donc pas toute seule : le CORE l'expose en LECTURE (`CF.models`, patron
# `CF.images` — « le SEUL dehors, tenu par le CORE »), sur la liste que la
# galerie de démarrage a déjà chargée et cachée. Les deux autres voies sont
# fermées et le restent : un `window.fetch` nu rouvrirait le « fetch libre »
# que `makeApi` a retiré (rien ne l'attrape), et une table recopiée à l'écran
# est refusée explicitement par le banc du contrat.

MUT_PAL = ("\r\n})();",
           "\r\n  globalThis.__pal = { ensure: ensureModels, offres: paletteOffres,"
           " note: paletteNote, html: paletteHtml, normSlots: normSlots };\r\n})();")


def _modele(mid: str) -> dict:
    """Un modèle d'usine RÉEL, tel que GET /api/cards/models le sert. Recopier
    un faux élément ici aurait prouvé que le banc sait lire le banc."""
    from app.services.cards import models as MD
    return MD.model(mid)


def _entrees(menu: str) -> int:
    return menu.count('class="cf-type-mi"')


def _n_generiques() -> int:
    """Le nombre d'entrées GÉNÉRIQUES de la palette, LU dans le source.

    Il valait 3, écrit en dur dans une quinzaine d'assertions ; la phase 5 en a
    posé quatre de plus (les formes) et les quinze ont rougi d'un coup. Ce que
    ces tests mesurent n'a jamais été « il y en a trois » : c'est « les
    génériques SONT LÀ quoi qu'il arrive au catalogue, et les éléments du
    modèle s'y AJOUTENT ». Le compte se dérive donc, et la propriété reste
    vraie à la prochaine entrée."""
    bloc = re.search(r"const GENERIQUES = \[(.*?)\n  \];", _js(), re.S)
    assert bloc, "GENERIQUES introuvable dans mod-type.js"
    n = len(re.findall(r'id: "gen:', bloc.group(1)))
    assert n >= 3, n
    return n


def test_la_palette_vit_dans_la_barre_et_pose_son_menu_sur_le_corps(tmp_path):
    """Le bouton existe, il est CÂBLÉ, et son clic pose un popover — trouvé
    dans `document.body`, pas supposé. Les trois entrées génériques y sont
    quoi qu'il arrive au catalogue : ce sont celles qui ne dépendent de rien."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "actes": [{"t": "pal"}]})
    assert "cf-type-pal" in d["panneau"], "aucun bouton de palette dans la barre"
    assert d["traces"][0]["cable"] is True, d["traces"]
    assert len(d["menus"]) == 1, d["menus"]
    menu = d["menus"][0]
    assert _entrees(menu) == _n_generiques(), menu
    for lib in ("Zone de texte", "Zone de statistique", "Calque d'image"):
        assert lib in menu, menu
    for oid in ("gen:texte", "gen:stat", "gen:image"):
        assert 'data-o="' + oid + '"' in menu, menu


def test_la_zone_de_statistique_NAIT_EN_PAIRE_et_ne_laisse_QU_UNE_annulation(tmp_path):
    """LA PAIRE. Deux blocs, UN geste : étiquette à gauche, valeur à droite,
    boîtes ADJACENTES (la forme de `models.py:_duel_ligne`, généralisée). La
    sélection se pose sur le PREMIER né, et un seul Ctrl+Z les enlève TOUS LES
    DEUX — sans quoi « annuler » laisserait la moitié d'un geste à l'écran."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "actes": [{"t": "pal"},
                                          {"t": "palclic", "o": "gen:stat"}]})
    s = d["slots"]
    assert [x["id"] for x in s] == ["etiq1", "val1"], [x["id"] for x in s]
    assert d["sel"] == ["etiq1"], d["sel"]
    assert s[0]["align"] == "left" and s[1]["align"] == "right"
    # LA VALEUR EST EN CHASSE FIXE — le seul emprunt à `_duel_ligne` qui ne
    # soit pas de la décoration : une colonne de chiffres proportionnelle
    # danse d'une carte à l'autre, et c'est un défaut de série.
    assert s[1]["font"] == "JetBrainsMono", s[1]["font"]
    # ADJACENTES : la valeur commence exactement où l'étiquette finit
    assert round(s[0]["box"][0] + s[0]["box"][2], 6) == round(s[1]["box"][0], 6)
    assert s[0]["box"][1] == s[1]["box"][1] and s[0]["box"][3] == s[1]["box"][3]
    # deux blocs de TEXTE ordinaires, et le backend n'a rien à réparer
    for x in s:
        assert x["kind"] == "text", x["id"]
        assert TY.norm_slot(x) == x, x["id"]
    # UNE naissance = UNE entrée d'annulation
    d2 = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                 "actes": [{"t": "pal"},
                                           {"t": "palclic", "o": "gen:stat"},
                                           {"t": "key", "k": "z", "ctrl": True}]})
    assert d2["slots"] == [], [x["id"] for x in d2["slots"]]


def test_la_paire_nee_en_DEUX_gestes_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : si la paire naissait par deux appels successifs,
    elle laisserait DEUX entrées d'annulation et un Ctrl+Z ne défairait que la
    moitié. Le test ci-dessus mesure donc quelque chose."""
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                  "actes": [{"t": "pal"},
                                            {"t": "palclic", "o": "gen:stat"},
                                            {"t": "key", "k": "z", "ctrl": True}]},
                       mutations=(
        ("    const next = normSlots(slots().concat(specs));",
         "    if (specs.length > 1) { specs.forEach((sp) => naitre([sp], quoi)); return null; }\r\n"
         "    const next = normSlots(slots().concat(specs));"),))
    assert len(mut["slots"]) == 1, [x["id"] for x in mut["slots"]]


def test_les_deux_autres_generiques_naissent_par_la_palette(tmp_path):
    """« Zone de texte » et « calque d'image » passent par les MÊMES portes que
    les boutons de la barre (`addSlot` / `addImgSlot`) : la palette n'a pas à
    savoir ce qu'est un calque d'image (décision de la tâche 2)."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "actes": [{"t": "pal"},
                                          {"t": "palclic", "o": "gen:image"},
                                          {"t": "pal"},
                                          {"t": "palclic", "o": "gen:texte"}]})
    s = d["slots"]
    assert [x["id"] for x in s] == ["image1", "texte1"], [x["id"] for x in s]
    assert s[0]["kind"] == "image" and s[0]["fit"] == "contain"
    assert s[1]["kind"] == "text"
    assert d["sel"] == ["texte1"], d["sel"]


def test_la_palette_offre_les_elements_DU_MODELE_dont_le_jeu_est_ne(tmp_path):
    """Le preset du document désigne un modèle SERVI : ses éléments s'ajoutent
    aux trois génériques, avec leur libellé et leur phrase — celles du modèle,
    pas une ligne réécrite ici."""
    m = _modele("superstar")
    els = m["elements"]
    assert els, "le modèle d'usine n'a plus d'éléments : ce test ne prouve rien"
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": [m], "actes": [{"t": "pal"}]})
    menu = d["menus"][-1]
    assert _entrees(menu) == _n_generiques() + len(els), menu
    for e in els:
        assert 'data-o="mod:' + e["id"] + '"' in menu, menu
        assert e["label"] in menu, menu
        assert e["hint"][:40] in menu, menu
    # rien à dire : il y a des éléments à poser
    assert "cf-type-paln" not in menu, menu


def test_la_LISTE_DES_OFFRES_est_derivee_du_preset_AU_MOMENT_DE_PEINDRE(tmp_path):
    """Le constructeur d'offres, ouvert par mutation (patron `__solo`). Il ne
    capture rien : il relit `type.preset` à chaque appel. C'est ce qui rend
    impossible — par construction et non par un drapeau — d'afficher les
    éléments d'un modèle que le document a cessé de désigner (poser un gabarit
    réécrit le preset, sans recharger la page)."""
    m = _modele("superstar")
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": [m], "pal": True},
                     mutations=(MUT_PAL,))
    offres = d["pal"]["offres"]
    ng = _n_generiques()
    assert [o["id"] for o in offres[:3]] == ["gen:texte", "gen:stat", "gen:image"]
    assert [o["n"] for o in offres[:3]] == [1, 2, 1], offres[:3]
    assert all(o["id"].startswith("gen:") for o in offres[:ng]), offres[:ng]
    assert [o["id"] for o in offres[ng:]] == ["mod:" + e["id"] for e in m["elements"]]
    for o, e in zip(offres[ng:], m["elements"]):
        assert o["label"] == e["label"] and o["hint"] == e["hint"]
        assert o["n"] == len(e["slots"])
    assert d["pal"]["note"] == "", d["pal"]["note"]
    # ... et le même catalogue sous un AUTRE preset n'offre que les génériques
    d2 = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                           "preset": "minimal"},
                                 "catalogue": [m], "pal": True},
                      mutations=(MUT_PAL,))
    assert len(d2["pal"]["offres"]) == _n_generiques(), d2["pal"]["offres"]


def test_un_element_de_modele_NAIT_a_sa_zone_avec_ses_REGLAGES(tmp_path):
    """L'instanciation est un APPEND des slots de l'élément — sa boîte, sa
    plaque, sa police, telles que le modèle les déclare. Et le document qui en
    sort est celui que le backend relira sans y toucher."""
    m = _modele("superstar")
    el = m["elements"][0]
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": [m],
                                "actes": [{"t": "pal"},
                                          {"t": "palclic", "o": "mod:" + el["id"]}]})
    s = d["slots"]
    assert len(s) == len(el["slots"]), [x["id"] for x in s]
    assert d["sel"] == [el["slots"][0]["id"]], d["sel"]
    for ne, ref in zip(s, el["slots"]):
        assert ne == ref, (ne["id"], sorted(k for k in ref if ne.get(k) != ref[k]))
        assert TY.norm_slot(ne) == ne, ne["id"]


def test_ajouter_DEUX_FOIS_le_meme_element_RENOMME_comme_le_serveur(tmp_path):
    """LA COLLISION. Deux slots de même id et P4 ne saurait plus lequel
    remplir : `norm_slots` renomme, il ne jette JAMAIS. L'écran doit rendre le
    MÊME document — sans quoi le backend « répare » au chargement suivant ce
    que l'utilisateur vient de voir naître."""
    m = _modele("superstar")
    el = m["elements"][0]
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": [m],
                                "actes": [{"t": "pal"},
                                          {"t": "palclic", "o": "mod:" + el["id"]},
                                          {"t": "pal"},
                                          {"t": "palclic", "o": "mod:" + el["id"]}]})
    ids = [x["id"] for x in d["slots"]]
    attendu = [x["id"] for x in TY.norm_slots(el["slots"] + el["slots"])]
    assert ids == attendu, (ids, attendu)
    assert len(set(ids)) == len(ids), ids
    n = len(el["slots"])
    assert ids[n].startswith(ids[0]) and ids[n] != ids[0], ids
    # la sélection suit le SECOND ajout, sur son premier bloc
    assert d["sel"] == [ids[n]], d["sel"]


# la batterie de collisions : l'écran et le serveur doivent renommer PAREIL.
UNIQ_BATTERIE = [
    [{"id": "stat7"}, {"id": "stat7"}],
    [{"id": "a"}, {"id": "a"}, {"id": "a"}, {"id": "a2"}],
    # la collision se joue APRÈS la normalisation, jamais avant : « SLOT1 » et
    # «  slot1  » sont le MÊME id une fois rognés et mis en bas de casse.
    [{"id": "SLOT1"}, {"id": " slot1 "}],
    # l'id que `norm_slot` FABRIQUE quand il n'y en a pas est indexé : deux
    # slots sans id ne se marchent pas dessus, un « slot1 » écrit à la main
    # après eux, si.
    [{}, {}, {"id": "slot1"}],
    [{"id": "a1"}, {"id": "a"}, {"id": "a"}],
    # 24 signes — la borne du motif d'id. Le suffixe la DÉPASSE, et le serveur
    # ne re-valide pas après avoir renommé : l'écran ne doit pas le faire non
    # plus (c'est la raison pour laquelle `naitre` n'appelle pas `commit`).
    [{"id": "a" * 24}, {"id": "a" * 24}],
    [{"id": "9bad"}, {"id": "9bad"}],
    [{"id": "z"}, {"id": "z"}, {"id": "z2"}, {"id": "z"}],
]


def test_l_UNIQUIFICATION_de_l_ecran_est_CELLE_du_serveur(tmp_path):
    """PARITÉ D'EXÉCUTION, pas de source (leçon B1) : les deux uniquificateurs
    tournent sur la même batterie et on compare leurs sorties, clé par clé."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "norms": UNIQ_BATTERIE},
                     mutations=(MUT_PAL,))
    assert d["norms"] is not None, "la porte du banc ne s'est pas ouverte"
    for i, entree in enumerate(UNIQ_BATTERIE):
        py = TY.norm_slots(entree)
        js = d["norms"][i]
        assert [x["id"] for x in js] == [x["id"] for x in py], \
            (i, [x["id"] for x in js], [x["id"] for x in py])
        for k, (a, b) in enumerate(zip(js, py)):
            assert a == b, (i, k, sorted(x for x in b if a.get(x) != b[x]))


def test_une_uniquification_QUI_DIVERGE_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : un suffixe d'une autre forme (« stat7_2 » au lieu
    de « stat72 ») passe tous les tests de « les ids sont uniques » et fait
    quand même diverger le document de ce que le backend en fera."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "norms": UNIQ_BATTERIE},
                     mutations=(MUT_PAL,
                                ('while (seen[sid]) { sid = s.id + n; n++; }',
                                 'while (seen[sid]) { sid = s.id + "_" + n; n++; }')))
    ecarts = [i for i, e in enumerate(UNIQ_BATTERIE)
              if [x["id"] for x in d["norms"][i]]
              != [x["id"] for x in TY.norm_slots(e)]]
    assert ecarts, "la parité ne mesure rien : un autre suffixe passe encore"


def test_le_plafond_est_dit_AVANT_avec_SON_ARITHMETIQUE(tmp_path):
    """Un élément de deux blocs demandé à 39 est refusé ENTIER — jamais posé à
    moitié — et le refus DONNE les chiffres. « 40 slots au maximum » ne dit pas
    combien il en manque ; « 39 + 2 = 41 » se vérifie sous les yeux."""
    deja = [TY.norm_slot({"id": f"s{i}", "label": f"S{i}"}) for i in range(39)]
    actes = [{"t": "pal"}, {"t": "palclic", "o": "gen:stat"}]
    d = _banc_verrou(tmp_path, {"state": {"slots": deja, "sel": "s0"},
                                "actes": actes})
    assert len(d["slots"]) == 39, "la paire est passée (entière ou à moitié)"
    refus = [t for t in d["toasts"] if t["err"]]
    assert refus, d["toasts"]
    msg = refus[-1]["m"]
    assert "39 slot(s) + 2 = 41, le maximum est 40" in msg, msg
    assert "zone de statistique" in msg, msg
    # ... et à 38, la paire passe : le plafond ne gêne personne avant.
    ok = _banc_verrou(tmp_path, {"state": {"slots": deja[:38], "sel": "s0"},
                                 "actes": actes})
    assert len(ok["slots"]) == 40, len(ok["slots"])


def test_un_plafond_NON_CONTROLE_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : sans le compte AVANT, la paire est posée et le
    document sort à 41 slots — que le backend tronquera, muettement."""
    deja = [TY.norm_slot({"id": f"s{i}", "label": f"S{i}"}) for i in range(39)]
    mut = _banc_verrou(tmp_path, {"state": {"slots": deja, "sel": "s0"},
                                  "actes": [{"t": "pal"},
                                            {"t": "palclic", "o": "gen:stat"}]},
                       mutations=(
        ("if (!specs.length || !placeOu(specs.length, quoi)) return null;",
         "if (!specs.length) return null;"),))
    assert len(mut["slots"]) == 41, len(mut["slots"])
    assert len(mut["slots"]) > TY.SLOTS_MAX


def test_un_modele_SANS_ELEMENTS_est_DIT(tmp_path):
    """« Rien à ajouter » et « je n'ai pas pu regarder » ne se réparent pas de
    la même façon : la palette NOMME le cas au lieu de se contenter d'être
    courte. Un élément sans slot ne compte pas — même règle qu'au backend
    (`models.py:_elements_normalises`), sinon ce serait un bouton qui ne pose
    rien."""
    for els in ([], [{"id": "vide", "label": "Vide", "hint": "", "slots": []}]):
        m = _modele("superstar")
        m["elements"] = els
        d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                              "preset": "modele:superstar"},
                                    "catalogue": [m], "actes": [{"t": "pal"}]})
        menu = d["menus"][-1]
        assert _entrees(menu) == _n_generiques(), menu
        assert "cf-type-paln" in menu, menu
        assert "sans éléments" in menu, menu
        assert m["label"] in menu, menu


def test_sans_modele_la_palette_offre_les_trois_generiques_ET_SE_TAIT(tmp_path):
    """Un jeu né d'un GABARIT local (« champion ») n'est pas né d'un modèle :
    il n'y a rien à dire, et une phrase de plus serait du bruit. C'est le SEUL
    cas où la palette se tait."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "champion"},
                                "catalogue": [_modele("superstar")],
                                "actes": [{"t": "pal"}]})
    menu = d["menus"][-1]
    assert _entrees(menu) == _n_generiques(), menu
    assert "cf-type-paln" not in menu, menu


def test_UN_GABARIT_LOCAL_NE_DESIGNE_JAMAIS_UN_MODELE(tmp_path):
    """F2 — LA COLLISION D'ESPACE DE NOMS, REJOUÉE. « arcane » est une clé des
    quatre gabarits de P3 ET l'identifiant d'un archétype d'usine : un deck
    posé sur le GABARIT se voyait offrir les éléments d'un design dont il
    n'était pas né. Depuis la ronde, la provenance est ÉCRITE à l'instanciation
    (`modele:<id>`) et un preset sans préfixe ne désigne rien.

    Les deux sens sont éprouvés ici : le gabarit qui n'attrape plus le modèle,
    et le modèle qui reste bien servi quand il DIT d'où il vient."""
    from app.services.cards import models as MD
    arcane = MD.model("arcane")
    els = arcane["elements"]
    assert els, "l'archétype « arcane » n'a plus d'éléments : ce test ne prouve rien"
    assert "arcane" in TY.PRESETS, "le gabarit « arcane » a disparu : le cas a changé"
    # SENS 1 — le gabarit local ne reçoit RIEN, et ne dit rien : il n'a pas de
    # modèle, ce n'est pas une anomalie.
    gab = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "arcane"},
                                  "catalogue": [arcane], "actes": [{"t": "pal"}]})
    menu = gab["menus"][-1]
    assert _entrees(menu) == _n_generiques(), menu
    assert "cf-type-paln" not in menu, menu
    # SENS 2 — le deck INSTANCIÉ du même modèle, lui, les reçoit.
    inst = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                             "preset": "modele:arcane"},
                                   "catalogue": [arcane], "actes": [{"t": "pal"}]})
    assert _entrees(inst["menus"][-1]) == _n_generiques() + len(els), inst["menus"][-1]
    # ... et un modèle PERSO nommé « Champion » (slug « champion ») ne peut
    # plus se faire passer pour le gabarit du même nom.
    faux = dict(arcane, id="champion", label="Champion")
    per = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "champion"},
                                  "catalogue": [faux], "actes": [{"t": "pal"}]})
    assert _entrees(per["menus"][-1]) == _n_generiques(), per["menus"][-1]


def test_la_COLLISION_rejouee_sans_le_prefixe_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : `modelCourant` remis à l'ancienne règle (l'id
    NU) — et le deck posé sur le gabarit « arcane » se voit de nouveau offrir
    les éléments du modèle « arcane ». Le test ci-dessus mesure bien le
    défaut, pas le hasard."""
    from app.services.cards import models as MD
    arcane = MD.model("arcane")
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "arcane"},
                                  "catalogue": [arcane], "actes": [{"t": "pal"}]},
                       mutations=(
        ('return p.indexOf(PRESET_MODELE) === 0 ? p.slice(PRESET_MODELE.length) : "";',
         'return p;'),))
    assert _entrees(mut["menus"][-1]) == _n_generiques() + len(arcane["elements"]), \
        "l'ancienne règle n'attrape plus le modèle : le cas a changé de forme"


def test_un_catalogue_INJOIGNABLE_est_un_ETAT_NOMME_pas_une_panne(tmp_path):
    """404, hors ligne, CORE plus ancien que la pièce : la palette garde ses
    trois entrées, les rend POSABLES, et dit ce qui manque. Aucune exception
    (`_banc_verrou` refuserait le relevé)."""
    for cat, mot in (("absent", "backend injoignable (qa)"),
                     ("sanscore", "pas disponible dans cette version")):
        d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                              "preset": "modele:superstar"},
                                    "catalogue": cat,
                                    "actes": [{"t": "pal"},
                                              {"t": "palclic", "o": "gen:texte"}]})
        menu = d["menus"][-1]
        assert _entrees(menu) == _n_generiques(), menu
        # LA PHRASE PARLE DU PRODUIT (« backend » est un mot banni du
        # panneau, pin de la pièce), le DIAGNOSTIC vit dans l'infobulle.
        assert "n'a pas pu être lu" in menu, menu
        assert 'title="' in menu, menu
        assert mot in menu, menu
        # le catalogue absent ne bloque AUCUNE des trois entrées génériques
        assert len(d["slots"]) == 1 and d["slots"][0]["id"] == "texte1", d["slots"]


def test_le_catalogue_qui_arrive_APRES_ne_repeint_QUE_SON_ouverture(tmp_path):
    """LA GARDE, MESURÉE. Le plan redoutait un cache survivant à un changement
    de jeu ; changer de jeu est une NAVIGATION (`core.js:galGo` ->
    `location.assign`), donc ce cache et la requête en vol meurent avec la
    page, et le catalogue n'est même pas propre à un jeu. Ce qui change
    VRAIMENT sous une réponse en vol, c'est l'ouverture du menu : deux
    ouvertures, une seule requête, et la réponse ne doit repeindre que la
    dernière — sinon un popover fermé se remplit dans le vide."""
    m = _modele("superstar")
    opts = {"state": {"slots": [], "sel": "", "preset": "modele:superstar"},
            "catalogue": [m], "lent": 150,
            "actes": [{"t": "pal", "ms": 5}, {"t": "pal", "ms": 5}]}
    d = _banc_verrou(tmp_path, opts)
    assert len(d["menus"]) == 2, d["menus"]
    assert _entrees(d["menus"][0]) == _n_generiques(), d["menus"][0]
    assert "chargement du catalogue" in d["menus"][0], d["menus"][0]
    assert _entrees(d["menus"][1]) == _n_generiques() + len(m["elements"]), d["menus"][1]
    mut = _banc_verrou(tmp_path, opts, mutations=(
        ("if (seq === PAL_SEQ && PAL_MENU === menu) paintPalette(menu);",
         "if (true) paintPalette(menu);"),))
    assert _entrees(mut["menus"][0]) == _n_generiques() + len(m["elements"]), \
        "la garde d'étiquette ne mesure rien"


def test_la_palette_ECHAPPE_ce_qui_vient_du_CATALOGUE(tmp_path):
    """Les libellés et les phrases d'un modèle PERSO sont un fichier JSON du
    dossier de données : de la donnée serveur, écrite par quelqu'un. Elle
    traverse `esc` — dans les entrées comme dans la phrase de repli."""
    poison = '"><img src=x onerror=alert(1)>'
    base = {"id": "perso", "label": poison, "hint": poison, "elements": []}
    avec = dict(base, elements=[{"id": "e1", "label": poison, "hint": poison,
                                 "slots": [TY.norm_slot({"id": "z"})]}])
    for faux in (base, avec):
        d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                              "preset": "modele:perso"},
                                    "catalogue": [faux], "actes": [{"t": "pal"}]})
        menu = d["menus"][-1]
        assert "<img" not in menu, menu
        assert "&quot;&gt;&lt;img" in menu, menu


def test_un_libelle_de_catalogue_NON_ECHAPPE_rougit(tmp_path):
    """MUTATION DE CONTRÔLE, deux fois. La phrase (`hint`) est en position
    TEXTE : R14 ne la voit pas par construction (c'est écrit dans la règle),
    c'est donc CE test qui la tient. L'id, lui, est en position d'ATTRIBUT :
    R14 doit rougir tout seul — vérifié plus bas."""
    poison = '"><img src=x onerror=alert(1)>'
    faux = {"id": "perso", "label": "M", "hint": "h",
            "elements": [{"id": "e1", "label": "E", "hint": poison,
                          "slots": [TY.norm_slot({"id": "z"})]}]}
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "modele:perso"},
                                  "catalogue": [faux], "actes": [{"t": "pal"}]},
                       mutations=(("esc(o.hint)", "o.hint"),))
    assert "<img" in mut["menus"][-1], mut["menus"][-1]


def test_R14_attrape_un_ATTRIBUT_de_palette_non_echappe(tmp_path):
    """Le cliquet mécanique, sur la position que la règle SAIT juger. Le lint
    intégral est à 0 sur le dépôt ; il doit rougir dès qu'on dé-échappe la
    valeur d'attribut `data-o` de la palette."""
    import shutil
    import subprocess
    lint = REPO / "scripts" / "qa" / "lint_cardforge.py"
    if not lint.is_file():
        pytest.skip("lint_cardforge.py absent")
    src = JS.read_text(encoding="utf-8", newline="")
    faux = tmp_path / "depot"
    (faux / "frontend" / "cardforge" / "js").mkdir(parents=True)
    (faux / "frontend" / "cardforge" / "css").mkdir(parents=True)
    shutil.copy2(CSS, faux / "frontend" / "cardforge" / "css" / "mod-type.css")
    cible = faux / "frontend" / "cardforge" / "js" / "mod-type.js"
    # `data-o="…"` est une lecture POINTÉE (`o.id`) en position d'attribut :
    # c'est exactement ce que la règle sait juger.
    assert src.count("esc(o.id)") == 1
    cible.write_text(src.replace("esc(o.id)", "o.id"), encoding="utf-8",
                     newline="")
    r = subprocess.run([sys.executable, str(lint), "--root", str(faux),
                        "--module", "type"],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    assert r.returncode == 1, (r.returncode, r.stdout[-2000:])
    assert "R14" in r.stdout, r.stdout[-2000:]
    # LA LIMITE, MESURÉE ET NOMMÉE plutôt que supposée : la ronde a ajouté une
    # seconde valeur d'attribut, `title="' + esc(MODELS_ERR) + '"`, et R14 ne
    # la voit PAS — elle ne juge que les lectures pointées, une variable nue
    # lui échappe par construction. Élargir la règle aux identifiants nus
    # ferait rougir tout `class="' + cls + '"' du dépôt. C'est donc le banc qui
    # tient celle-là (test ci-dessous), et cette ligne empêche qu'on l'oublie.
    assert src.count("esc(MODELS_ERR)") == 1
    cible.write_text(src.replace("esc(MODELS_ERR)", "MODELS_ERR"),
                     encoding="utf-8", newline="")
    r2 = subprocess.run([sys.executable, str(lint), "--root", str(faux),
                         "--module", "type"],
                        capture_output=True, text=True, encoding="utf-8",
                        timeout=180)
    assert r2.returncode == 0, ("R14 voit maintenant les variables nues : "
                                "le pin du banc peut devenir un pin de règle",
                                r2.stdout[-2000:])


def test_le_lint_emet_de_l_UTF_8_sur_ses_DEUX_flux():
    """Un harnais de contrôle dont le verdict ne se DÉCODE pas peut fabriquer
    un faux résultat — même classe de faute que le drapeau inconnu avalé en
    silence. Mesuré ici même : sous Windows, le processus du lint héritait du
    codage de LOCALE (cp1252) sur ses tuyaux, le « · » de l'en-tête
    VIOLATIONS partait en octet 0xb7 — invalide en UTF-8 — et le lecteur du
    test voisin en mourait, rendant un `r.stdout` à None et un TypeError qui
    ne nomme rien. Le lint force donc SON codage à la source ; ce test tient
    le contrat : tout octet émis, flux normal comme flux d'erreur, se décode
    en UTF-8 STRICT — témoin non-ASCII à l'appui, pour que la preuve ne
    s'évapore pas le jour où une phrase de sortie change."""
    import subprocess
    lint = REPO / "scripts" / "qa" / "lint_cardforge.py"
    if not lint.is_file():
        pytest.skip("lint_cardforge.py absent")
    # Flux normal : l'en-tête aux « · » est imprimé à CHAQUE passe lisible,
    # violations ou pas — le code de retour, lui, est l'affaire de l'arbre du
    # moment et ce test n'en juge pas.
    r = subprocess.run([sys.executable, str(lint), "--module", "type"],
                       capture_output=True, timeout=180)
    out = r.stdout.decode("utf-8")          # UnicodeDecodeError = la faute
    assert "·" in out, "témoin non-ASCII absent : l'en-tête a changé ?"
    # Flux d'erreur : le refus d'un drapeau inconnu fait ÉCHO au drapeau tel
    # quel — un nom non-ASCII prouve que stderr porte le même codage.
    r2 = subprocess.run([sys.executable, str(lint), "--drapeau·"],
                        capture_output=True, timeout=180)
    assert r2.returncode == 2, (r2.returncode, r2.stderr[-500:])
    assert "·" in r2.stderr.decode("utf-8")


def test_le_DIAGNOSTIC_D_ECHEC_est_ECHAPPE_dans_son_infobulle(tmp_path):
    """Ce que R14 ne peut pas juger, le banc le mesure. Le message d'échec
    vient du réseau (c'est la phrase que le CORE rapporte) et il atterrit dans
    une valeur d'ATTRIBUT — la position la plus grave, celle où un guillemet
    referme l'attribut et pose ce qu'on veut sur la balise."""
    poison = '"><img src=x onerror=alert(1)>'
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": "absent", "err": poison,
                                "actes": [{"t": "pal"}]})
    menu = d["menus"][-1]
    assert "<img" not in menu, menu
    assert "&quot;&gt;&lt;img" in menu, menu
    # MUTATION DE CONTRÔLE : sans `esc`, le poison sort de l'attribut.
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "modele:superstar"},
                                  "catalogue": "absent", "err": poison,
                                  "actes": [{"t": "pal"}]},
                       mutations=(("esc(MODELS_ERR)", "MODELS_ERR"),))
    assert "<img" in mut["menus"][-1], mut["menus"][-1]


def test_TOUTES_les_naissances_passent_par_LA_MEME_porte():
    """Une entrée d'annulation par geste, une sélection sur le premier né, un
    plafond compté avant : ces trois-là ne se tiennent que si les quatre
    naissances (texte, statistique, image, élément de modèle) passent par la
    MÊME fonction. La leçon de `soloClone`, prise avant la quatrième copie.

    T3 EN AJOUTE UNE CINQUIÈME — « adopter les zones » (§7.1.5) — et c'est
    précisément le cas que ce contrôle existe pour tenir : une adoption qui
    aurait fait naître ses slots dans une boucle rendrait N pas d'annulation
    pour UN geste, et franchirait le plafond bloc par bloc au lieu de refuser
    l'élément entier."""
    src = _js()
    deb, fin = src.index("function placeOu("), src.index("function dupSlot(")
    zone = src[deb:fin]
    assert zone.count("pushUndo()") == 1, \
        "plus d'une entrée d'annulation dans la zone des naissances"
    # une définition, SEPT appels (le sixième est `addShapeSlot`, phase 5-T2 :
    # les quatre formes passent par UNE porte, pas par quatre ; le septième
    # est `addDecorShapes`, phase 6-T4 : les formes du décor naissent par la
    # MÊME porte que tout le monde)
    assert zone.count("naitre(") == 8, zone.count("naitre(")
    for quoi in ("function addSlot()", "function addImgSlot()",
                 "function addStatSlot()", "function addShapeSlot(",
                 "function palAdd(", "function adopterZones()",
                 "function addDecorShapes()"):
        assert quoi in src, quoi
    # LES QUATRE FORMES NE FONT QU'UNE NAISSANCE. Quatre `addRectSlot`,
    # `addEllipseSlot`… auraient été quatre occasions d'oublier `pushUndo`.
    assert src.count("function addShapeSlot(") == 1, \
        "plusieurs portes de naissance pour les formes"
    # `commit` re-normalise : il ne doit PAS être sur le chemin des naissances
    # (il remplacerait un id renommé au-delà de 24 signes par « slotN »).
    assert "commit(" not in zone, "une naissance repasse par `commit`"


def test_P3_lit_le_catalogue_par_LE_CORE_et_par_AUCUN_RESEAU_NU():
    """LA DÉCISION D'ARCHITECTURE DE LA TÂCHE, ÉPINGLÉE. `M.api` est confiné à
    /api/cards/{did}/type (règle 8) ; la liste des modèles est ailleurs. Un
    `window.fetch` nu dans une pièce rouvrirait le « fetch libre » que
    `makeApi` a retiré — rien ne l'attraperait, ni le lint ni le CORE — et le
    premier module qui le reprend le rouvre pour les huit autres."""
    js_dir = REPO / "frontend" / "cardforge" / "js"
    # SUR LE CODE, commentaires ôtés : ce fichier PARLE de /api/cards/models et
    # de `window.fetch` — c'est même tout l'objet du pavé de la section 6bis.
    # Un pin qui rougirait sur une explication serait un pin qu'on supprime.
    src = _js_sans_commentaires()
    assert "CF.models(" in src, "la palette ne lit pas le catalogue par le CORE"
    for interdit in ("fetch(", "XMLHttpRequest", "/api/cards/models"):
        assert interdit not in src, interdit
    # AUCUNE des neuf pièces ne fait de réseau nu : le CORE est le seul dehors
    for p in sorted(js_dir.glob("mod-*.js")):
        t = re.sub(r"/\*.*?\*/", " ", p.read_text(encoding="utf-8"), flags=re.S)
        assert "fetch(" not in t, p.name
        assert "XMLHttpRequest" not in t, p.name
    # ... et le CORE rend une copie PROFONDE ET GELÉE de SA liste déjà cachée :
    # un module qui écrirait dedans empoisonnerait la galerie et les huit
    # autres pièces, dans le même onglet, sans rien casser tout de suite.
    core = (js_dir / "core.js").read_text(encoding="utf-8")
    i = core.index("async function modelsPublic(")
    corps = core[i:core.index("\n  /*", i + 10)]
    assert "galModelsList" in corps, "le CORE recharge une seconde fois la liste"
    assert "deepFreeze" in corps and "JSON.parse(JSON.stringify" in corps, corps
    assert "e.missing" in corps, "une route absente n'est pas une liste vide"
    assert "models: modelsPublic," in core
    # la lecture seule, et rien de plus : aucune ÉCRITURE de modèle n'apparaît
    assert "POST" not in corps and "DELETE" not in corps


# ═══════ 14. LA RONDE DE REVUE DE LA TÂCHE 3 ════════════════════════════════
# Trois correctifs (Échap sous une garde de sélection, l'espace de noms partagé
# entre gabarits et modèles, deux états muets) et quatre notes prises.

def test_ECHAP_ferme_la_palette_sur_un_jeu_VIDE(tmp_path):
    """F1 — Échap était SOUS `if (!selSlot()) return`, et `selSlot()` est nul
    exactement quand le document n'a aucun bloc : c'est-à-dire l'état d'un jeu
    neuf, celui où l'on ouvre justement la palette. Échap n'y fermait donc
    rien, et la réponse du catalogue revenait repeindre un menu que
    l'utilisateur croyait fermé."""
    m = _modele("superstar")
    opts = {"state": {"slots": [], "sel": "", "preset": "modele:superstar"},
            "catalogue": [m], "lent": 150,
            "actes": [{"t": "pal", "ms": 5}, {"t": "key", "k": "Escape"}]}
    d = _banc_verrou(tmp_path, opts)
    # le menu a été fermé AVANT que le catalogue n'arrive : il en reste aux
    # trois génériques, la réponse ne l'a pas rattrapé.
    assert len(d["menus"]) == 1, d["menus"]
    assert _entrees(d["menus"][0]) == _n_generiques(), d["menus"][0]
    # ... et sur un jeu qui a des blocs, Échap fermait déjà (contrôle : le
    # défaut était bien la GARDE, pas la branche).
    plein = dict(opts, state={"slots": _slots_verrou(False), "sel": "titre",
                              "preset": "modele:superstar"})
    dp = _banc_verrou(tmp_path, plein)
    assert _entrees(dp["menus"][0]) == _n_generiques(), dp["menus"][0]


def test_ECHAP_remis_SOUS_la_garde_de_selection_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : la branche Échap redescendue sous `if (!s)
    return` — sur un jeu vide, le menu fermé se fait repeindre par la réponse
    en vol, exactement comme la revue l'a mesuré."""
    m = _modele("superstar")
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "modele:superstar"},
                                  "catalogue": [m], "lent": 150,
                                  "actes": [{"t": "pal", "ms": 5},
                                            {"t": "key", "k": "Escape"}]},
                       mutations=(
        # LA MUTATION DIT LA MÊME CHOSE QU'AVANT, EN UNE LIGNE : la garde de
        # sélection REMISE AU-DESSUS d'Échap. (La branche Échap a grandi en
        # T3 — elle vide aussi le lot — et la déplacer bloc à bloc aurait fait
        # d'un pin de comportement un pin de mise en page.)
        ('    if (e.key === "Escape") {',
         '    if (!selSlot()) return;\r\n    if (e.key === "Escape") {'),))
    assert _entrees(mut["menus"][0]) == _n_generiques() + len(m["elements"]), \
        "le menu fermé n'a pas été repeint : la garde ne mesure rien"


def test_le_MODELE_DISPARU_est_NOMME(tmp_path):
    """F3a — le preset désigne un modèle que le catalogue CHARGÉ ne porte pas :
    perso supprimé, jeu rapporté d'une autre machine. « ce jeu n'a pas de
    modèle » et « son modèle n'est plus là » ne se réparent pas de la même
    façon ; le second se dit."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:disparu"},
                                "catalogue": [_modele("superstar")],
                                "actes": [{"t": "pal"}]})
    menu = d["menus"][-1]
    assert _entrees(menu) == _n_generiques(), menu
    assert "cf-type-paln" in menu, menu
    assert "n'est plus disponible sur ce poste" in menu, menu
    assert "disparu" in menu, menu
    # l'identifiant vient du DOCUMENT : il est échappé comme le reste
    poison = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                               "preset": 'modele:"><img src=x>'},
                                     "catalogue": [_modele("superstar")],
                                     "actes": [{"t": "pal"}]})
    assert "<img" not in poison["menus"][-1], poison["menus"][-1]


def test_un_CATALOGUE_VIDE_est_NOMME(tmp_path):
    """F3b, côté écran — `!MODELS` est FAUX pour un tableau vide, et c'est
    ainsi que cet état est resté muet. Or tout backend qui a la route sert au
    moins les sept archétypes d'usine : une liste vide ne dit pas « ce poste
    n'a pas de modèles », elle dit « personne n'a répondu »."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": [], "actes": [{"t": "pal"}]})
    menu = d["menus"][-1]
    assert _entrees(menu) == _n_generiques(), menu
    assert "cf-type-paln" in menu, menu
    assert "aucun modèle disponible sur ce poste" in menu, menu


def test_le_message_d_ECHEC_meurt_avec_la_NOUVELLE_TENTATIVE(tmp_path):
    """N4 — `MODELS_ERR` retenu au-delà de l'échec faisait dire
    « injoignable » à la palette pendant qu'une requête FRAÎCHE volait : un
    état faux, et le seul que l'utilisateur voyait au moment précis où il
    refaisait le geste."""
    # Le dernier acte referme : sans lui, la 3e réponse (qui échoue aussi)
    # repeindrait le menu et l'on ne verrait plus l'état INTERMÉDIAIRE — celui
    # que l'utilisateur a sous les yeux pendant que sa tentative vole.
    actes = [{"t": "pal", "ms": 5}, {"t": "pal", "ms": 400},
             {"t": "pal", "ms": 5}, {"t": "quitte"}]
    opts = {"state": {"slots": [], "sel": "", "preset": "modele:superstar"},
            "catalogue": "absent", "lent": 150, "actes": actes}
    d = _banc_verrou(tmp_path, opts)
    assert len(d["menus"]) == 3, d["menus"]
    # 1re ouverture : rien n'est encore su -> « chargement »
    assert "chargement du catalogue" in d["menus"][0], d["menus"][0]
    # 2e : la réponse est arrivée, l'échec est connu et NOMMÉ
    assert "injoignable" in d["menus"][1], d["menus"][1]
    # 3e : une tentative REPART -> plus « injoignable », « chargement »
    assert "chargement du catalogue" in d["menus"][2], d["menus"][2]
    assert "injoignable" not in d["menus"][2], d["menus"][2]
    # MUTATION DE CONTRÔLE : le message survit au départ de la tentative.
    mut = _banc_verrou(tmp_path, opts, mutations=(
        ('    MODELS_ERR = "";\r\n    let lire;', "    let lire;"),))
    assert "injoignable" in mut["menus"][2], mut["menus"][2]


def test_le_PANNEAU_QUI_S_EFFACE_emporte_son_popover(tmp_path):
    """N3 — le popover vit sur `document.body`, pas dans le panneau. La
    fermeture au clic dehors ne le rattrape pas quand on change de pièce AU
    CLAVIER (Entrée sur le rail = `click` sans `pointerdown`) : le menu restait
    seul au-dessus d'un autre module. Il part avec la classe du panneau, le
    même observateur que le calque d'édition."""
    m = _modele("superstar")
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                          "preset": "modele:superstar"},
                                "catalogue": [m], "lent": 150,
                                "actes": [{"t": "pal", "ms": 5},
                                          {"t": "quitte"}]})
    assert d["ferme"] is True, "le popover n'a pas été retiré du corps"
    assert _entrees(d["menus"][0]) == _n_generiques(), \
        "un menu orphelin s'est quand même fait repeindre"


def test_le_popover_SURVIVANT_au_changement_de_piece_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : l'observateur remis à son ancien corps (le seul
    `syncOverlay`) — le menu reste posé sur le corps au-dessus d'une autre
    pièce."""
    m = _modele("superstar")
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": "",
                                            "preset": "modele:superstar"},
                                  "catalogue": [m], "lent": 150,
                                  "actes": [{"t": "pal", "ms": 5},
                                            {"t": "quitte"}]},
                       mutations=(
        ("          if (!panelOn()) { closeFontPicker(); closePalette(); }\r\n", ""),))
    assert mut["ferme"] is False, "le menu part quand même : le pin ne mesure rien"


# ── 14.1 LE BANC DU CORE : la capacité de lecture, éprouvée à l'EXÉCUTION ────
# `CF.models` est la voie par laquelle P3 lit le catalogue (voir la section 13).
# Ce qu'elle promet — une copie PROFONDE ET GELÉE, et une liste VIDE quand la
# route est absente — était épinglé par des MATCHS DE SOURCE. Un match de
# source ne dit rien de ce que le code FAIT : le mutant qui gèle le cache du
# CORE et rend une copie NON gelée passait. C'est la leçon B1, appliquée à la
# capacité que cette tâche a fait naître. Le banc charge le VRAI core.js dans
# un `vm` sans DOM (patron `qa/test_core_contract.mjs:loadCF`) et bouchonne
# `fetch` — le CORE n'est pas modifié pour être testé.

CORE_JS = REPO / "frontend" / "cardforge" / "js" / "core.js"

BANC_CORE = r"""
import { readFileSync } from "node:fs";
import vm from "node:vm";
const SRC = readFileSync(process.argv[2], "utf8");
const OPT = JSON.parse(readFileSync(process.argv[3], "utf8"));

const appels = [];
function rep(corps, ct, code) {
  return {
    ok: code >= 200 && code < 300, status: code, statusText: "qa",
    headers: { get: (k) => (String(k).toLowerCase() === "content-type" ? ct : null) },
    json: async () => JSON.parse(corps),
  };
}
/* LES TROIS REPONSES QUI COMPTENT : la bonne, le catch-all SPA (200 + HTML —
   « ce backend n'a pas la route ») et une panne qui PARLE en JSON. */
const fetchQA = async (u) => {
  appels.push(String(u));
  if (OPT.route === "absente")
    return rep("<!doctype html><title>SPA</title>", "text/html; charset=utf-8", 200);
  if (OPT.route === "morte")
    return rep('{"detail":"le backend a quelque chose a dire"}', "application/json", 500);
  return rep(JSON.stringify({ models: OPT.models || [] }), "application/json", 200);
};
const ctx = vm.createContext({ console, setTimeout, clearTimeout, URL, fetch: fetchQA });
ctx.globalThis = ctx;
vm.runInContext(SRC, ctx, { filename: "core.js" });
const CF = ctx.CF;
const out = { erreur: null, liste: null, gele: null, gele_item: null,
  ecriture_champ: null, ecriture_liste: null, cache: null, appels: 0, appels2: 0 };
try {
  const a = await CF.models();
  out.liste = a;
  out.gele = Object.isFrozen(a);
  out.gele_item = a.length ? Object.isFrozen(a[0]) : null;
  out.appels = appels.length;
  /* ON ECRIT VRAIMENT DEDANS. Ce module est en mode strict (ESM) : une copie
     gelee LEVE, une copie libre accepte — et si elle n'est pas une COPIE, la
     seconde lecture rendra le mensonge. */
  if (a.length) {
    try { a[0].label = "PIRATE"; out.ecriture_champ = "acceptee"; }
    catch (e) { out.ecriture_champ = "refusee:" + String(e && e.name); }
  }
  try { a.push({ id: "pirate" }); out.ecriture_liste = "acceptee"; }
  catch (e) { out.ecriture_liste = "refusee:" + String(e && e.name); }
  const b = await CF.models();
  out.cache = b.map((m) => (m && m.label) || null);
  out.appels2 = appels.length;
} catch (e) { out.erreur = String((e && e.message) || e); }
process.stdout.write(JSON.stringify(out));
"""


def _banc_core(tmp_path, opts: dict, mutations=()) -> dict:
    """Fait tourner le VRAI core.js dans un `vm` sans DOM, `fetch` bouchonné."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du CORE ne peut pas tourner")
    src = CORE_JS.read_text(encoding="utf-8", newline="")
    for avant, apres in mutations:
        assert avant in src, f"mutation introuvable : {avant!r}"
        assert src.count(avant) == 1, f"mutation ambiguë : {avant!r}"
        src = src.replace(avant, apres)
    js = tmp_path / "core-banc.js"
    js.write_text(src, encoding="utf-8", newline="")
    banc = tmp_path / "banc-core.mjs"
    banc.write_text(BANC_CORE, encoding="utf-8")
    conf = tmp_path / "opts-core.json"
    conf.write_text(json.dumps(opts, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([node, str(banc), str(js), str(conf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


CAT_QA = [{"id": "superstar", "label": "Superstar", "elements": []},
          {"id": "duel", "label": "Duel", "elements": []}]


def test_CF_models_rend_une_copie_GELEE_et_le_cache_du_CORE_INTACT(tmp_path):
    """N1 — PIN D'EXÉCUTION. On écrit vraiment dans ce que le CORE a rendu :
    une copie gelée LÈVE (mode strict), et la lecture suivante prouve que le
    cache de la galerie n'a pas bougé. Un module qui écrirait dans cette liste
    empoisonnerait la galerie et les huit autres pièces, dans le même onglet,
    sans rien casser tout de suite."""
    d = _banc_core(tmp_path, {"models": CAT_QA})
    assert d["erreur"] is None, d["erreur"]
    assert [m["id"] for m in d["liste"]] == ["superstar", "duel"]
    assert d["gele"] is True and d["gele_item"] is True, d
    assert str(d["ecriture_champ"]).startswith("refusee:TypeError"), d["ecriture_champ"]
    assert str(d["ecriture_liste"]).startswith("refusee:TypeError"), d["ecriture_liste"]
    assert d["cache"] == ["Superstar", "Duel"], d["cache"]
    # UNE requête, un cache : la seconde lecture ne repart pas au réseau.
    assert d["appels"] == 1 and d["appels2"] == 1, (d["appels"], d["appels2"])


def test_une_COPIE_NON_GELEE_rougit(tmp_path):
    """MUTATION DE CONTRÔLE, celle que le match de source ne voyait pas : la
    copie est bien faite, le gel non. Les écritures passent — et rien dans la
    source ne l'aurait dit, `deepFreeze` y étant toujours écrit ailleurs."""
    mut = _banc_core(tmp_path, {"models": CAT_QA}, mutations=(
        ("      return deepFreeze(JSON.parse(JSON.stringify(l)));",
         "      return JSON.parse(JSON.stringify(l));"),))
    assert mut["gele"] is False, mut
    assert mut["ecriture_champ"] == "acceptee", mut["ecriture_champ"]


def test_SANS_COPIE_le_cache_du_CORE_est_empoisonne(tmp_path):
    """La seconde moitié du pin : sans la copie profonde, écrire dans la liste
    rendue écrit dans le cache de la GALERIE."""
    mut = _banc_core(tmp_path, {"models": CAT_QA}, mutations=(
        ("      return deepFreeze(JSON.parse(JSON.stringify(l)));", "      return l;"),))
    assert mut["ecriture_champ"] == "acceptee", mut
    assert mut["cache"][0] == "PIRATE", mut["cache"]


def test_une_ROUTE_ABSENTE_rend_une_LISTE_VIDE_pas_une_panne(tmp_path):
    """F3b, de bout en bout — la branche que `modelsPublic` existe pour
    produire, et qui n'avait jamais été exercée. Le catch-all SPA rend 200 et
    du HTML : c'est « ce backend n'a pas la route », donc AUCUN modèle, pas une
    panne. Les autres erreurs, elles, REMONTENT : « aucun modèle » serait faux
    quand le backend a quelque chose à dire."""
    vide = _banc_core(tmp_path, {"route": "absente"})
    assert vide["erreur"] is None, vide["erreur"]
    assert vide["liste"] == [], vide["liste"]
    assert vide["gele"] is True, vide
    morte = _banc_core(tmp_path, {"route": "morte"})
    assert morte["liste"] is None, morte
    assert "quelque chose a dire" in str(morte["erreur"]), morte["erreur"]


# ════════ 16. LA LISTE DE CALQUES MULTI-BANDES (3b-T4, décision 4) ══════════
# Une carte du document, pas une télécommande : les bandes des AUTRES pièces s'y
# lisent (une ligne dérivée de l'état publié) et ne s'y règlent jamais. La bande
# z=60 est la liste de blocs EXISTANTE, à sa place dans la pile.

def _bandes(html: str) -> list:
    """Les rangées fixes d'un conteneur, DANS L'ORDRE OÙ ELLES SONT ÉCRITES :
    (z, pièce visée). L'ordre du HTML est l'ordre de l'écran."""
    return [(int(z), mod) for z, mod in re.findall(
        r'class="cf-type-band" data-z="(\d+)"[\s\S]{0,700}?data-mod="([^"]*)"', html)]


def _resume(html: str, z: int) -> str:
    """La ligne dérivée d'une bande — ce que la rangée DIT de la couche."""
    m = re.search(r'data-z="%d"[\s\S]{0,700}?class="cf-type-bres">([^<]*)<' % z, html)
    return m.group(1) if m else ""


def _z_table_du_core() -> dict:
    """La table des z, lue DANS core.js — la seule autorité (spec §2.2)."""
    src = CORE_JS.read_text(encoding="utf-8")
    m = re.search(r"const Z_TABLE = \{([^}]*)\}", src)
    assert m, "la table des z du CORE est introuvable"
    return {int(k): v for k, v in re.findall(r'(\d+)\s*:\s*"([^"]+)"', m.group(1))}


def _z_nommes() -> set:
    """Les z auxquels la pièce a donné un NOM et un résumé."""
    src = _js()
    m = re.search(r"const BANDES = \{([\s\S]*?)\n  \};", src)
    assert m, "la table des noms de bandes est introuvable dans mod-type.js"
    return {int(z) for z in re.findall(r"(?m)^\s{4}(\d+):", m.group(1))}


# un document où les CINQ couches voisines disent quelque chose
DOC_PLEIN = {"texture": {"paper": "kraft", "over": "holo"},
             "face": {"src": "cat:golem", "default_art": None},
             "frame": {"family": "runique", "rarity": "legendary",
                       "gem": True, "banner": True}}


def test_la_section_des_calques_MONTRE_l_ordre_de_peinture(tmp_path):
    """DÉCISION 4. Une section « Calques » où la pile se lit de haut en bas
    comme elle se peint de haut en bas (convention Figma : le calque du dessus
    est la rangée du dessus) — décor haut (70), LA LISTE DE BLOCS (60), cadre
    (40), effet (30), illustration (20), papier (10).

    Le z=90 n'y est PAS : c'est le CORE et ses repères de coupe, qui ne partent
    dans aucun fichier ; l'annoncer comme un calque de la carte serait faux."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                                "doc": DOC_PLEIN})
    p = d["panneau"]
    # la liste EXISTANTE est physiquement ENTRE les deux conteneurs de bandes :
    # c'est ce qui fait de l'ordre affiché l'ordre de peinture réel.
    for cls in ("cf-type-lay", "cf-type-bhaut", "cf-type-list", "cf-type-bbas"):
        assert cls in p, cls
    assert p.index("cf-type-bhaut") < p.index('class="cf-type-list"') < p.index("cf-type-bbas"), p
    assert _bandes(d["bhaut"]) == [(70, "frame")], d["bhaut"]
    assert _bandes(d["bbas"]) == [(40, "frame"), (30, "texture"),
                                  (20, "face"), (10, "texture")], d["bbas"]
    # 90 = les repères du CORE, 60 = la liste elle-même : ni l'un ni l'autre
    # n'est une rangée fixe.
    assert 'data-z="90"' not in d["bhaut"] + d["bbas"]
    assert 'data-z="60"' not in d["bhaut"] + d["bbas"]
    # une rangée fixe ne porte AUCUNE commande d'écriture (ni œil, ni cadenas,
    # ni ordre, ni corbeille) : la visibilité de ces couches appartient à leur
    # pièce, et cette rangée est une CARTE, pas une télécommande.
    for interdit in ("cf-type-eye", "cf-type-lock", "cf-type-mv", "cf-type-del"):
        assert interdit not in d["bhaut"] + d["bbas"], interdit


def test_l_ordre_des_bandes_est_DERIVE_de_la_table_du_CORE(tmp_path):
    """L'ordre n'est pas recopié : il est LU sur `CF.Z_TABLE` (core.js:2248 —
    copie gelée publiée sur le global gelé). La preuve est une table BROUILLÉE :
    des z que la pièce n'a jamais vus, dans un ordre qu'elle ne peut pas
    connaître. Une bande sans nom ne DISPARAÎT pas pour autant — elle se
    présente par son z et sa pièce : une carte muette vaut mieux qu'un trou."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "ztable": {"5": "face", "60": "type",
                                           "88": "frame", "90": "__core__"}})
    assert _bandes(d["bhaut"]) == [(88, "frame")], d["bhaut"]
    assert _bandes(d["bbas"]) == [(5, "face")], d["bbas"]
    assert "88" in d["bhaut"] and "frame" in d["bhaut"], d["bhaut"]


def test_un_ordre_de_bandes_RECOPIE_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : une table des z recopiée dans la pièce. Tout
    resterait vert sur la table réelle — et c'est exactement le défaut qu'on
    veut voir, puisqu'il ne se déclarerait que le jour où le CORE bouge."""
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                  "ztable": {"5": "face", "60": "type",
                                             "88": "frame", "90": "__core__"}},
                       mutations=(
        ("    const T = (CF && CF.Z_TABLE) || {};",
         '    const T = { 10: "texture", 20: "face", 30: "texture", 40: "frame", '
         '60: "type", 70: "frame", 90: "__core__" };'),))
    assert _bandes(mut["bhaut"]) == [(70, "frame")], mut["bhaut"]
    assert _bandes(mut["bbas"]) == [(40, "frame"), (30, "texture"),
                                    (20, "face"), (10, "texture")], mut["bbas"]


def test_chaque_bande_de_la_table_du_CORE_porte_un_NOM():
    """PIN DE COUTURE : le jour où le CORE ajoute un z, cette liste doit le
    NOMMER. La rangée générique évite le trou à l'écran ; ce test évite qu'elle
    y reste. Les deux littéraux sont relus à la source, des deux côtés."""
    zt = _z_table_du_core()
    attendus = {z for z, mod in zt.items() if mod not in ("__core__", "type")}
    assert attendus == {10, 20, 30, 40, 70}, attendus
    manquants = attendus - _z_nommes()
    assert not manquants, f"bandes sans nom ni résumé : {sorted(manquants)}"
    # et la bande de la pièce elle-même est UNIQUE : c'est elle qui coupe la
    # pile en deux, la liste de blocs prenant sa place.
    assert [z for z, mod in zt.items() if mod == "type"] == [60], zt


def test_les_resumes_sont_DERIVES_de_l_etat_publie(tmp_path):
    """La rangée dit ce que le DOCUMENT porte — lu par `CF.get` sur les
    sous-arbres des autres pièces (patron art_window). Ce sont leurs
    identifiants qui s'affichent, jamais leurs libellés : recopier ici la table
    des matières de P6 ou celle des cadres de P2 aurait menti au premier
    renommage, et cette pièce n'a aucun droit sur leur catalogue."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}, "doc": DOC_PLEIN})
    assert _resume(d["bbas"], 10) == "kraft", d["bbas"]
    assert _resume(d["bbas"], 30) == "holo", d["bbas"]
    assert _resume(d["bbas"], 20) == "posée", d["bbas"]
    assert _resume(d["bbas"], 40) == "runique · legendary", d["bbas"]
    assert _resume(d["bhaut"], 70) == "gemme + bandeau", d["bhaut"]
    # l'illustration suit la PRÉCÉDENCE GELÉE (spec 2.3, mod-face.js:1688) :
    # une carte qui porte SA propre image en a une, même si le document n'en
    # pose aucune par défaut.
    p = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "doc": {"face": {"src": None, "default_art": None}},
                                "carte": {"art": "cat:golem", "fields": {}}})
    assert _resume(p["bbas"], 20) == "posée", p["bbas"]


def test_une_couche_MUETTE_ne_se_dit_jamais_ABSENTE(tmp_path):
    """LE PIÈGE DE LA CARTE QUI MENT. Un document neuf ne porte AUCUNE clé de
    matière ni de cadre — et pourtant un vélin et un cadre arcane se peignent :
    chaque pièce applique SES défauts. Écrire « aucun » là aurait été faux, et
    recopier ici les défauts des voisins les aurait fait dériver au premier
    changement. La rangée dit donc « par défaut » : le document ne nomme rien,
    la pièce propriétaire décide.

    L'illustration, elle, est bel et bien VIDE : sa précédence (mod-face.js:1688)
    ne retombe sur rien du tout."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}, "doc": {}})
    for z in (10, 30, 40):
        assert _resume(d["bbas"], z) == "par défaut", (z, d["bbas"])
        assert "aucun" not in _resume(d["bbas"], z), z
    assert _resume(d["bbas"], 20) == "vide", d["bbas"]
    # le décor haut, lui, se lit SANS défaut recopié : le painter teste
    # `!== false` (mod-frame.js:462), un document muet peint donc les deux.
    assert _resume(d["bhaut"], 70) == "gemme + bandeau", d["bhaut"]


def test_une_couche_ETEINTE_est_dite_ETEINTE(tmp_path):
    """L'autre moitié : quand le document dit explicitement « rien », la rangée
    le dit aussi. « aucun » et « par défaut » ne se réparent pas de la même
    façon — le premier est un choix, le second une absence."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "doc": {"texture": {"paper": "none", "over": "none"},
                                        "face": {"src": None},
                                        "frame": {"family": "none", "gem": False,
                                                  "banner": False}}})
    # LE PAPIER AUSSI S'ÉTEINT, et en UN clic : la grille des matières ouvre sur
    # une tuile « Aucune » (mod-texture.js:1877) qui patche `paper: "none"`, et
    # le painter la teste nommément (`s.paper !== "none"`, mod-texture.js:658) —
    # rien n'est peint que la teinte. Sans cette ligne, la rangée affichait le
    # littéral « none » : le seul des cinq résumés qu'aucun test ne couvrait
    # était le seul cassé.
    assert _resume(d["bbas"], 10) == "aucun", d["bbas"]
    assert _resume(d["bbas"], 30) == "aucun", d["bbas"]
    assert _resume(d["bbas"], 40) == "aucun", d["bbas"]
    assert _resume(d["bbas"], 20) == "vide", d["bbas"]
    assert _resume(d["bhaut"], 70) == "aucun", d["bhaut"]


MOD_FACE = REPO / "frontend" / "cardforge" / "js" / "mod-face.js"
MOD_FRAME = REPO / "frontend" / "cardforge" / "js" / "mod-frame.js"
MOD_TEXTURE = REPO / "frontend" / "cardforge" / "js" / "mod-texture.js"

# ── LES RÈGLES QUE CETTE PIÈCE REJOUE, ET LEUR SOURCE ───────────────────────
# Deux résumés ne LISENT pas seulement l'état d'un voisin : ils REJOUENT une
# règle qui vit chez lui. C'est délibéré (recopier ses DÉFAUTS aurait dérivé au
# premier changement, cf. la note de livraison) — mais une règle rejouée sans
# pin devient fausse EN SILENCE le jour où le voisin la change, et une carte
# muette ne se signale jamais. Chaque entrée : (fichier, fragment attendu chez
# le voisin, fragment miroir dans mod-type.js, ce qu'il faut faire).
COUTURES = [
    (MOD_FACE, "return own || col || f.default_art || f.src || null;",
     'return (own || lu("face.default_art") || lu("face.src")) ? "posée" : VIDE;',
     "la précédence gelée de l'illustration (spec 2.3) a bougé chez P1 : "
     "`resFace` doit la rejouer à l'identique, sinon la rangée « illustration » "
     "dira « vide » sur une carte qui en porte une"),
    (MOD_FRAME, "if (fr.banner !== false) {",
     'if (CF.get("frame.banner", null) !== false) on.push("bandeau" + sous("banner_plan"));',
     "P2 ne teste plus le bandeau par `!== false` : `resDecor` rejoue ce test "
     "PRÉCIS pour ne pas avoir à recopier le défaut `banner: true` (et depuis "
     "la phase 6-T3, la rangée DIT la rétrogradation « sous les blocs »)"),
    (MOD_FRAME, "if (f.gem && gemB && !gemB.seat) {",
     'if (CF.get("frame.gem", null) !== false) on.push("gemme" + sous("gem_plan"));',
     "P2 ne peint plus la gemme sur une valeur simplement VRAIE : `resDecor` "
     "suppose qu'une clé absente (donc le défaut `gem: true`) la peint (et "
     "depuis la phase 6-T3, la rangée DIT la rétrogradation « sous les blocs »)"),
    (MOD_FRAME, 'if (f.family === "none") return;',
     'if (lu("frame.family") === "none") return AUCUN;',
     "P2 ne sort plus du décor haut sur `family === \"none\"` : la rangée "
     "« décor haut » annoncerait une gemme que personne ne peint"),
    (MOD_TEXTURE, 'else if (s.paper !== "none" && MAT_BY_ID[s.paper]) {',
     'return p === "none" ? AUCUN : (p === "__import" ? "importé" : p);',
     "P6 ne traite plus `paper: \"none\"` comme « rien peint » : `resPapier` "
     "le traduit en « aucun » sur cette seule foi"),
]


def test_les_regles_REJOUEES_sont_TOUJOURS_CELLES_DES_PIECES_VOISINES():
    """PINS DE COUTURE (patron du pin Z_TABLE, appliqué aux règles). Les deux
    résumés qui ne se contentent pas de LIRE — l'illustration et le décor haut,
    plus la traduction de « none » du papier — rejouent un test qui vit chez le
    voisin. Ce pin relit les DEUX bouts : le fragment chez lui, le miroir ici.
    Le jour où l'un bouge, c'est ce test qui le dit, et pas un utilisateur
    devant une carte qui ment."""
    src = _js()
    for path, chez_lui, miroir, quoi in COUTURES:
        voisin = path.read_text(encoding="utf-8")
        assert chez_lui in voisin, (
            f"{path.name} : « {chez_lui} » a disparu — {quoi}")
        assert miroir in src, (
            f"mod-type.js : le miroir « {miroir} » a disparu — {quoi}")


def test_les_pins_de_COUTURE_ne_sont_pas_CREUX():
    """MUTATION DE CONTRÔLE d'un pin de SOURCE. Un pin qui cherche une chaîne
    est creux si la chaîne ne peut pas manquer : on rejoue donc, sur chaque
    couture, LE REFACTOR PLAUSIBLE qui la casserait (le `!== false` resserré en
    booléen strict, la précédence raccourcie, le « none » oublié) et l'on vérifie
    qu'il n'est PAS dans la source — autrement dit que le pin au-dessus rougirait
    le jour où il y serait."""
    mutants = [
        (MOD_FACE, "return own || col || f.default_art || null;"),
        (MOD_FRAME, "if (fr.banner === true) {"),
        (MOD_FRAME, "if (f.gem === true && gemB && !gemB.seat) {"),
        (MOD_FRAME, 'if (!f.family) return;'),
        (MOD_TEXTURE, "else if (MAT_BY_ID[s.paper]) {"),
    ]
    assert len(mutants) == len(COUTURES)
    for (path, attendu, _m, _q), (pm, mutant) in zip(COUTURES, mutants):
        assert path == pm
        voisin = path.read_text(encoding="utf-8")
        assert mutant != attendu, mutant
        assert mutant not in voisin, (
            f"{path.name} : le refactor « {mutant} » est DANS la source — "
            "la couture a bougé et le pin ne l'a pas dit")


def test_une_rangee_fixe_MENE_a_sa_piece_et_n_ECRIT_RIEN(tmp_path):
    """« Aller au module » = `CF.show`, la fonction que les boutons du rail du
    CORE appellent eux-mêmes (core.js:954). Elle vit sur le GLOBAL GELÉ, là où
    le CORE range ce qui n'écrit pas (« Ce qui ECRIT n'est pas ici : c'est sur
    le jeton », core.js:2227) : aucune surface de pouvoir neuve n'a été ouverte.

    Et le pin d'ABSENCE, celui qui compte : cliquer une rangée fixe n'émet AUCUN
    patch. Le cloisonnement de la 3a-T4 reste entier."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}, "doc": DOC_PLEIN,
                                "actes": [{"t": "bande", "z": 70}, {"t": "bande", "z": 40},
                                          {"t": "bande", "z": 30}, {"t": "bande", "z": 20},
                                          {"t": "bande", "z": 10}]})
    assert [t["mod"] for t in d["traces"]] == ["frame", "frame", "texture", "face", "texture"], d["traces"]
    assert all(t["branche"] for t in d["traces"]), d["traces"]
    assert d["shows"] == ["frame", "frame", "texture", "face", "texture"], d["shows"]
    for t in d["traces"]:
        assert t["patchs"] == 0, t


def test_une_rangee_fixe_QUI_ECRIT_rougit(tmp_path):
    """MUTATION DE CONTRÔLE du pin d'absence : la même rangée, qui pousse un
    patch en plus de naviguer. L'espion des écritures doit la voir."""
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}, "doc": DOC_PLEIN,
                                  "actes": [{"t": "bande", "z": 40}]},
                       mutations=(
        ("      if (b) CF.show(b.dataset.mod);",
         '      if (b) { mpatch({ sel: "" }); CF.show(b.dataset.mod); }'),))
    assert mut["traces"][0]["patchs"] == 1, mut["traces"]


def test_deux_peintures_du_MEME_etat_n_ecrivent_QU_UNE_FOIS(tmp_path):
    """FLUIDITÉ (§9.6). `core:render` part à CHAQUE frame de la carte, y compris
    pendant un glisser. Les résumés se dérivent en lectures de chaînes — bon
    marché — mais le DOM ne s'écrit que si le TEXTE a changé (patron de
    `mod-gltf.js:867` : on mesure une signature au lieu de repeindre par
    réflexe). Deux peintures du même état = une seule écriture."""
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}, "doc": DOC_PLEIN,
                                "actes": [{"t": "peint"}, {"t": "peint"},
                                          {"t": "etat", "doc": {"texture": {"paper": "lin"}}},
                                          {"t": "peint"}]})
    tr = [t for t in d["traces"] if t["acte"] == "peint"]
    assert tr[0]["ecrits"] == [1, 1], tr[0]
    assert tr[1]["ecrits"] == [1, 1], tr[1]
    # l'état a bougé SOUS la bande basse : elle seule se réécrit.
    assert tr[2]["ecrits"] == [1, 2], tr[2]
    assert _resume(d["bbas"], 10) == "lin", d["bbas"]


def test_la_garde_de_REPEINTURE_retiree_rougit(tmp_path):
    """MUTATION DE CONTRÔLE : sans la comparaison de texte, chaque frame
    réécrit les deux conteneurs — et l'écran s'en tirerait sans un symptôme
    visible, ce qui est exactement pourquoi ce compteur existe."""
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""}, "doc": DOC_PLEIN,
                                  "actes": [{"t": "peint"}, {"t": "peint"}]},
                       mutations=(
        ("      if (h[k] === BANDES_HTML[k]) return;",
         "      if (false) return;"),))
    tr = [t for t in mut["traces"] if t["acte"] == "peint"]
    assert tr[1]["ecrits"] == [3, 3], tr[1]


def test_les_resumes_sont_ECHAPPES(tmp_path):
    """R14 EN EXÉCUTION. Ces valeurs viennent du sous-arbre d'UNE AUTRE PIÈCE :
    à cette frontière, une donnée d'ailleurs est une donnée non fiable — un
    identifiant de matière importé d'un jeu rapporté d'une autre machine passe
    par ici sans que personne ne l'ait relu."""
    poison = '"><img src=x onerror=alert(1)>'
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "doc": {"texture": {"paper": poison},
                                        "frame": {"family": poison}}})
    assert "<img" not in d["bbas"], d["bbas"]
    # les DEUX résumés empoisonnés, entièrement entités : plus un chevron ni un
    # guillemet capable de refermer quoi que ce soit.
    assert d["bbas"].count("&quot;&gt;&lt;img src=x onerror=alert(1)&gt;") == 2, d["bbas"]
    # ET LA POSITION D'ATTRIBUT, celle pour laquelle R14 existe : le nom de la
    # pièce vient de la table du CORE et atterrit dans `data-mod=` autant que
    # dans l'infobulle. Une valeur qui s'y échapperait poserait un attribut de
    # plus sur la balise — un `onload=`, par exemple.
    a = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "ztable": {"10": 'texture" onload="boom',
                                           "60": "type", "90": "__core__"}})
    assert 'onload="boom"' not in a["bbas"], a["bbas"]
    assert "&quot; onload=&quot;boom" in a["bbas"], a["bbas"]


def test_un_resume_NON_ECHAPPE_rougit(tmp_path):
    """MUTATION DE CONTRÔLE, et la limite de R14 NOMMÉE : le résumé passe par
    une VARIABLE, pas par une lecture de champ littérale — le lint ne peut donc
    pas le voir (même angle mort qu'en T3). C'est ce banc qui tient
    l'échappement, et lui seul."""
    casse = ('      + \'<i class="cf-type-bres">\' + esc(res) + \'</i></span>\'',
             '      + \'<i class="cf-type-bres">\' + res + \'</i></span>\'')
    mut = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                  "doc": {"texture": {"paper": '"><img src=x>'}}},
                       mutations=(casse,))
    assert "<img" in mut["bbas"], mut["bbas"]
    # ANCRE DE CONTRÔLE : la même source mutilée, passée au lint. R14 n'en dit
    # RIEN — position texte, et variable nue. Ce n'est pas un trou à boucher
    # (l'élargir ferait rougir chaque `+ cls +` légitime du lab) : c'est la
    # frontière de la règle, et la raison pour laquelle ce banc existe.
    src = _js().replace(casse[0], casse[1])
    assert casse[1] in src, "la mutation n'a pas pris sur la source"
    assert _r14(src) == [], _r14(src)
    # ...et la règle n'est pas morte pour autant : une lecture de champ à la
    # même place, dans une valeur d'attribut, elle, est bien vue.
    sonde = ('function bandeHtml(b) {\n'
             '  return \'<div data-mod="\' + b.mod + \'"></div>\';\n}\n')
    assert _r14(sonde), "R14 ne mord plus sur une valeur d'attribut"


def test_la_bande_60_reste_LA_LISTE_avec_toutes_ses_commandes(tmp_path):
    """La bande z=60 n'est pas une rangée de plus : c'est la liste EXISTANTE,
    déplacée à sa place dans la pile et pas réécrite. Œil, cadenas, ordre,
    corbeille, badge de nature et glisser-déposer sont là, inchangés."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(True), "sel": "titre"},
                                "doc": DOC_PLEIN})
    for cls in ("cf-type-row", "cf-type-eye", "cf-type-lock", "cf-type-kind",
                "cf-type-mv", "cf-type-del"):
        assert cls in d["liste"], cls
    assert 'draggable="true"' in d["liste"], d["liste"]
    assert d["liste"].count('class="cf-type-eye"') == 2, d["liste"]
    # et les gestes de la pièce écrivent toujours, eux : la section n'a rien
    # gelé (nudge de 1 mm, spec §6.1:307 — le pin de la T1 tient).
    r = _banc_verrou(tmp_path, {"state": {"slots": _slots_verrou(False), "sel": "titre"},
                                "doc": DOC_PLEIN,
                                "actes": [{"t": "key", "k": "ArrowDown"}]})
    assert r["slots"][0]["box"][1] == 21.0, r["slots"][0]["box"]


# ══════ 14. LES BOUTONS DE RANGÉE, JOUÉS (dette 3b-T4, soldée en 3c-T6) ═════
# Le pin d'au-dessus lit des CLASSES dans une chaîne de caractères. Il ne
# pouvait pas faire mieux : `querySelectorAll` du DOM de paille rendait `[]`,
# donc `renderList` n'a JAMAIS branché l'œil, le cadenas, l'ordre, la corbeille
# ni le glisser au banc — les cinq écouteurs étaient écrits et jamais joués.
# Le remède esquissé au plan 3b (:1013-1015) est appliqué ici : le banc a
# maintenant un vrai `querySelectorAll`, et cette section JOUE les gestes.
#
# CE QUI EST MESURÉ À CHAQUE GESTE, et pourquoi les trois ensemble :
#   · l'ÉCOUTEUR est celui que le module a posé (`cable`) — pas une fonction
#     choisie à la main : `renderList` qui cesserait de câbler le ferait voir ;
#   · l'ÉTAT DU DOCUMENT change (le slot, son ordre, sa présence) ;
#   · UNE entrée d'annulation, ni zéro ni deux — un geste qu'un Ctrl+Z ne
#     défait pas est un geste qui ment, et rien d'autre ne l'attrape.

MUT_UNDO = ("\r\n})();", "\r\n  globalThis.__undo = () => UNDO.length;\r\n})();")


def _banc_rangees(tmp_path, actes, lock=False, mutations=()):
    """Le banc de gestes, avec la porte de la pile d'annulation ouverte."""
    return _banc_verrou(tmp_path,
                        {"state": {"slots": _slots_verrou(lock), "sel": ["titre"]},
                         "doc": DOC_PLEIN, "actes": actes},
                        mutations=(MUT_UNDO,) + tuple(mutations))


def _ids(d) -> list:
    return [s["id"] for s in d["slots"]]


def test_les_cinq_commandes_de_rangee_sont_CABLEES_pas_seulement_ecrites(tmp_path):
    """Le trou nommé en 3b : les classes étaient là, les écouteurs non. On
    compte maintenant ce que `renderList` a réellement branché — quatre boutons
    par rangée et quatre gestes sur la rangée elle-même (clic, dragstart,
    dragover, drop)."""
    d = _banc_rangees(tmp_path, [])
    assert _ids(d) == ["titre", "regles"], d["slots"]
    assert [r["id"] for r in d["rangees"]] == ["titre", "regles"], d["rangees"]
    for r in d["rangees"]:
        # œil + cadenas + corbeille + les DEUX flèches = 5 boutons câblés
        assert r["cable"] == 5, r
        assert r["gestes"] == 4, r
    # la rangée désignée porte sa marque, et elle seule
    assert [r["sel"] for r in d["rangees"]] == [True, False], d["rangees"]


def test_l_oeil_joue_bascule_le_bloc_et_pose_UNE_annulation(tmp_path):
    """L'œil éteint le bloc, le rallume, et chaque clic vaut UN Ctrl+Z."""
    d = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "eye"}])
    t = d["traces"][0]
    assert t["trouve"] and t["cable"], t
    assert t["patchs"] == 1 and t["undo"] == 1, t
    assert d["slots"][0]["on"] is False, d["slots"][0]
    # …et la rangée repeinte le DIT (classe `off` lue sur l'élément)
    assert d["rangees"][0]["off"] is True, d["rangees"]
    # deux clics reviennent à l'état de départ — deux entrées d'annulation
    d2 = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "eye"},
                                  {"t": "rangee", "id": "titre", "b": "eye"}])
    assert d2["slots"][0]["on"] is True, d2["slots"][0]
    assert [t["undo"] for t in d2["traces"]] == [1, 1], d2["traces"]


def test_le_cadenas_joue_bascule_le_verrou_de_CETTE_rangee(tmp_path):
    """Le cadenas est un état du bloc, pas du panneau : il s'écrit dans le
    document, il se relit sur la rangée, et il ne touche pas le voisin."""
    d = _banc_rangees(tmp_path, [{"t": "rangee", "id": "regles", "b": "lock"}])
    t = d["traces"][0]
    assert t["cable"] and t["patchs"] == 1 and t["undo"] == 1, t
    par_id = {s["id"]: s for s in d["slots"]}
    assert par_id["regles"]["lock"] is True and par_id["titre"]["lock"] is False
    assert [r["lock"] for r in d["rangees"]] == [False, True], d["rangees"]


def test_les_deux_fleches_reordonnent_et_le_bord_ne_fait_RIEN(tmp_path):
    """« Descendre » sur le premier bloc l'échange avec le second. « Monter »
    sur le premier n'a nulle part où aller : AUCUN patch, AUCUNE entrée
    d'annulation — un Ctrl+Z qui ne défait rien serait pire que rien."""
    d = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "mv", "d": 1}])
    assert d["traces"][0]["cable"], d["traces"]
    assert _ids(d) == ["regles", "titre"], d["slots"]
    assert d["traces"][0]["undo"] == 1, d["traces"]
    assert [r["id"] for r in d["rangees"]] == ["regles", "titre"], d["rangees"]
    # remonter le rend à sa place
    r = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "mv", "d": 1},
                                 {"t": "rangee", "id": "titre", "b": "mv", "d": -1}])
    assert _ids(r) == ["titre", "regles"], r["slots"]
    # le bord : rien ne bouge, rien ne s'annule
    b = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "mv", "d": -1}])
    assert _ids(b) == ["titre", "regles"], b["slots"]
    assert b["traces"][0]["patchs"] == 0 and b["traces"][0]["undo"] == 0, b["traces"]


def test_la_corbeille_supprime_le_bloc_et_deplace_la_designation(tmp_path):
    """La corbeille retire le bloc du document ET redésigne un survivant : une
    liste qui garde un `sel` mort laisse le panneau régler un fantôme."""
    d = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "del"}])
    t = d["traces"][0]
    assert t["cable"] and t["patchs"] == 1 and t["undo"] == 1, t
    assert _ids(d) == ["regles"], d["slots"]
    assert d["sel"] == ["regles"], d["sel"]
    assert [r["id"] for r in d["rangees"]] == ["regles"], d["rangees"]


def test_le_glisser_depose_reordonne_par_le_presse_papier(tmp_path):
    """La séquence complète : dragstart marque la rangée, dragover la survole
    (et appelle `preventDefault`, sans quoi un vrai navigateur REFUSE le
    dépôt), drop relit l'id dans le presse-papier et réordonne. Le survol se
    relâche au dépôt — une rangée qui reste allumée après coup est un défaut
    qu'aucune capture d'écran ne montre."""
    d = _banc_rangees(tmp_path, [{"t": "drag", "from": "regles", "to": "titre"}])
    t = d["traces"][0]
    assert t["cable"], t
    assert t["charge"] == "regles", t          # le SEUL canal du glisser
    assert t["prevent"] == 2, t                # dragover ET drop
    assert t["glisse"] and t["survol"] and not t["relache"], t
    assert t["patchs"] == 1 and t["undo"] == 1, t
    assert _ids(d) == ["regles", "titre"], d["slots"]
    # se déposer SUR SOI-MÊME n'est pas un geste : rien d'écrit, rien à annuler
    s = _banc_rangees(tmp_path, [{"t": "drag", "from": "titre", "to": "titre"}])
    assert s["traces"][0]["patchs"] == 0 and s["traces"][0]["undo"] == 0, s["traces"]
    assert _ids(s) == ["titre", "regles"], s["slots"]


def test_le_clic_sur_la_ligne_DESIGNE_mais_pas_a_travers_un_bouton(tmp_path):
    """La garde `e.target.closest("button")` de la ligne, jouée : le clic nu
    désigne, le clic qui atterrit sur une commande laisse la commande faire son
    travail — sans quoi chaque appui sur l'œil redésignerait aussi le bloc."""
    d = _banc_rangees(tmp_path, [{"t": "ligne", "id": "regles"}])
    assert d["traces"][0]["cable"] and d["traces"][0]["patchs"] == 1, d["traces"]
    assert d["sel"] == ["regles"], d["sel"]
    g = _banc_rangees(tmp_path, [{"t": "ligne", "id": "regles", "bouton": True}])
    assert g["traces"][0]["patchs"] == 0, g["traces"]
    assert g["sel"] == ["titre"], g["sel"]


# ── LES MUTANTS DE LA SECTION : chacun casse UNE moitié du geste ─────────────

def test_un_bouton_de_rangee_SANS_annulation_rougit(tmp_path):
    """MUTATION DE CONTRÔLE, celle qui justifie le compteur d'annulations :
    l'œil bascule toujours le bloc, la rangée se repeint toujours — seule la
    pile d'annulation reste vide. Sans ce compteur, ce défaut passerait le banc
    en vert et se découvrirait au premier Ctrl+Z d'un utilisateur."""
    mut = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "eye"}],
                        mutations=(("        patchSlot(id, { on: !s.on });",
                                    "        patchSlot(id, { on: !s.on }, true);"),))
    t = mut["traces"][0]
    assert t["cable"] and t["patchs"] == 1, t     # le geste marche encore
    assert mut["slots"][0]["on"] is False, mut["slots"][0]
    assert t["undo"] == 0, t                      # …et il n'est PAS annulable


def test_une_fleche_QUI_PERD_SON_SENS_rougit(tmp_path):
    """MUTATION DE CONTRÔLE du câblage : `data-d` est ce qui distingue les deux
    flèches. Le mutant les rend IDENTIQUES — les deux montent. « Descendre »
    sur le premier bloc devient alors un geste sans effet : le bouton reste
    câblé, la rangée reste peinte, et rien ne bouge. (Le mutant plus naïf,
    `moveSlot(id, 0)`, ne convient PAS : l'échange d'un bloc avec lui-même
    n'est pas gardé, il pousse quand même un patch et une annulation — c'est
    l'ORDRE, jamais le compteur, qui juge cette flèche-là.)"""
    mut = _banc_rangees(tmp_path, [{"t": "rangee", "id": "titre", "b": "mv", "d": 1}],
                        mutations=((
                            '        b.addEventListener("click", () => moveSlot(id, Number(b.dataset.d)));',
                            '        b.addEventListener("click", () => moveSlot(id, -1));'),))
    assert mut["traces"][0]["cable"], mut["traces"]
    assert _ids(mut) == ["titre", "regles"], mut["slots"]
    assert mut["traces"][0]["patchs"] == 0, mut["traces"]


def test_un_glisser_QUI_N_ANNONCE_RIEN_rougit(tmp_path):
    """MUTATION DE CONTRÔLE du presse-papier : `dragstart` est le seul endroit
    où la rangée dit QUI se déplace. Vidé, les trois écouteurs partent quand
    même et le dépôt ne réordonne rien."""
    mut = _banc_rangees(tmp_path, [{"t": "drag", "from": "regles", "to": "titre"}],
                        mutations=((
                            '        e.dataTransfer.setData("text/plain", id);',
                            '        e.dataTransfer.setData("text/plain", "");'),))
    t = mut["traces"][0]
    assert t["cable"] and t["prevent"] == 2, t
    assert t["charge"] == "", t
    assert t["patchs"] == 0 and t["undo"] == 0, t
    assert _ids(mut) == ["titre", "regles"], mut["slots"]


# ═══════ « ADOPTER LES ZONES » — la naissance groupée (phase 4, T3) ════════
#
# §7.1.5 donne à P3 un geste : « boîtes -> slots de gabarit (éditables
# ensuite, §6.1) ». Ce qui se garde ICI est la moitié qui appartient à P3 —
# ce que le SERVEUR fera des slots nés de cette adoption. La moitié qui
# appartient au contrat de P10 (la lecture tolérante de `doc.capture`, les
# libellés, l'aveu des tronquées) est gardée chez la pièce qui PUBLIE,
# `test_cards_capture.py` : c'est son schéma qui casserait.
#
# LE RISQUE PROPRE À P3, et il est silencieux : un slot que `norm_slots`
# RÉPARE au chargement suivant. L'utilisateur verrait d'autres identifiants
# que ceux qu'il a adoptés, ou des boîtes déplacées, sans un mot — le défaut
# `src: "undefined"` des 21 slots de gabarit, exactement.


def _fonction_js_type(nom: str) -> str:
    """Une fonction de `mod-type.js`, du `function nom(` à l'accolade de fin
    de colonne 2 — l'indentation du module est stable."""
    src = _js()
    i = src.index("function " + nom + "(")
    return src[i:src.index("\n  }", i)] + "\n  }\n"


def _node_type(source: str) -> str:
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    r = subprocess.run([node, "-e", source], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:600]
    return r.stdout.decode("utf-8", "replace")


# Les trois boîtes d'une carte réelle, en millimètres depuis le coin rogné —
# le repère de `doc.capture.boxes` (T2) ET celui de `slot.box` (`safe_rect_mm`
# est « la zone sûre en mm depuis le coin ROGNE »). Une unité par frontière :
# il n'y a RIEN à convertir, et c'est ce que ce contrôle prouve.
ZONES_MM = [{"x": 8.0, "y": 4.4, "w": 47.0, "h": 7.1, "tronquee": True},
            {"x": 8.0, "y": 62.0, "w": 47.0, "h": 15.0, "tronquee": False},
            {"x": 6.0, "y": 20.0, "w": 9.0, "h": 9.0, "tronquee": False}]


def _specs_adoptees(base: int = 1) -> list:
    """Les specs que l'écran ferait naître, produites par LA VRAIE fonction
    de `mod-type.js`, exécutée dans node. Rien n'est réécrit ici : un test qui
    recopierait la forme des specs ne mesurerait que lui-même."""
    doc = json.dumps({"capture": {"boxes": ZONES_MM}}, ensure_ascii=False)
    return json.loads(_node_type(
        _fonction_js_type("specsZones")
        + f"console.log(JSON.stringify(specsZones({doc}, {base})));"))


def test_les_ZONES_ADOPTEES_traversent_le_normaliseur_du_SERVEUR_INTACTES():
    """La naissance passe par `normSlots` côté écran, mais c'est
    `type.py:norm_slots` qui a le dernier mot au chargement suivant. Les
    deux doivent rendre le MÊME slot : un identifiant renommé ou une boîte
    déplacée par le serveur serait une divergence MUETTE."""
    specs = _specs_adoptees()
    rows = TY.norm_slots(specs)
    assert len(rows) == len(specs) == 3, (len(rows), len(specs))
    for spec, row in zip(specs, rows):
        assert row["id"] == spec["id"], \
            f"le serveur renomme {spec['id']} en {row['id']}"
        assert row["label"] == spec["label"], (spec["label"], row["label"])
        assert row["box"] == spec["box"], (spec["box"], row["box"])
        assert row["kind"] == "text", row["kind"]
        assert row["text"] == "", row["text"]
        assert row["src"] == "", \
            "une source inventée : le défaut `src: \"undefined\"` rejoué"


def test_les_MILLIMETRES_de_P10_sont_DEJA_ceux_d_un_SLOT():
    """« Une unité par frontière » (D3), et la frontière est le coin ROGNÉ.
    Les boîtes de P10 sont mesurées depuis le coin haut-gauche de l'image de
    la carte ; `safe_rect_mm` place la zone sûre depuis le MÊME coin. Une
    conversion cachée entre les deux ferait dériver toutes les adoptions du
    même décalage — et personne ne le verrait sur une seule carte."""
    g = TY.geom_of("poker_eu", 300)
    sr = TY.safe_rect_mm(g)
    rows = TY.norm_slots(_specs_adoptees())
    # la zone sûre commence à ~3 mm : une boîte posée à y = 4,4 mm est DEDANS
    # verticalement, et une boîte de 47 mm de large tient dans les 57 mm sûrs.
    dedans = rows[1]
    assert dedans["box"][0] >= sr[0] - 0.01, (dedans["box"], sr)
    assert dedans["box"][0] + dedans["box"][2] <= sr[0] + sr[2] + 0.01, \
        (dedans["box"], sr)
    # ... et le repère n'est PAS celui de la zone sûre : une boîte à x = 6 mm
    # (dans la marge) reste à 6 mm, elle n'est pas repoussée à 9.
    assert rows[2]["box"][0] == 6.0, rows[2]["box"]


def test_les_ZONES_ADOPTEES_ne_peuvent_pas_DEPASSER_le_plafond():
    """`SLOTS_MAX` est le plafond de la PIÈCE, pas un second chiffre : la
    valeur de l'écran est LUE et confrontée à celle du backend, et le
    serveur tronque ce qui déborde. L'écran, lui, refuse l'élément ENTIER
    avant de poser quoi que ce soit (`placeOu`) — une moitié d'adoption
    serait un défaut muet."""
    m = re.search(r"const SLOTS_MAX = (\d+)", _js())
    assert m and int(m.group(1)) == TY.SLOTS_MAX == 40, (m, TY.SLOTS_MAX)
    naitre = _fonction_js_type("naitre")
    assert "placeOu(specs.length" in naitre, naitre
    assert "slots().concat(specs)" in naitre, \
        "les zones REMPLACENT les slots au lieu de s'y ajouter"
    trop = TY.norm_slots(_specs_adoptees() * 20)
    assert len(trop) == TY.SLOTS_MAX, len(trop)


def test_l_ADOPTION_DES_ZONES_est_UN_SEUL_PAS_D_ANNULATION():
    """« naitre() EN UN APPEL (un pas d'undo) ». La fonction d'adoption
    n'appelle `naitre` qu'une fois et n'ajoute pas son propre `pushUndo` :
    sinon un geste unique demanderait N annulations."""
    corps = _fonction_js_type("adopterZones")
    assert corps.count("naitre(") == 1, corps
    assert "pushUndo" not in corps, corps
    assert "commit(" not in corps, \
        "l'adoption écrit à côté de la naissance atomique"
    # UN SEUL APPEL DANS LA SOURCE NE VEUT PAS DIRE UN SEUL APPEL À
    # L'EXÉCUTION : `naitre` posé dans une boucle reste UNE occurrence de
    # texte et fait N naissances. Mesuré — la mutation « naître dans une
    # boucle » restait verte ici. Aucune boucle sur ce chemin.
    for boucle in ("forEach", "for (", "while (", ".reduce("):
        assert boucle not in corps, \
            f"la naissance est dans une boucle ({boucle})"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ═════════════════════════════════════════════════════════════════════════════
# 14. LES FORMES DE GABARIT — phase 5, T2 (plan D3)
#
# « P3 gagne des KINDS de formes : rect, ellipse (ferme le transmis cercle —
#   le halo devient une vraie ellipse à rayon), line, arrow. »
#
# LA DÉCISION DE FOND, ET ELLE SE MESURE ICI : une forme est un SLOT d'une
# autre nature, pas un objet neuf. Elle hérite donc, sans une ligne de plus,
# de l'ordre de peinture dans la bande z=60, de l'œil, du verrou, du calque
# d'édition (glisser, poignées, flèches), de l'annulation, de la fluidité, de
# la liste, de l'export par couches et de `doc.type.slots` — le contrat que P4
# et P7 lisent déjà. C'est exactement le raisonnement du calque d'image de la
# 3b-T2, rejoué : « la pile de calques d'un éditeur d'images, pour le prix
# d'une clé ».
#
# CE QUI EN DÉCOULE POUR LE z : les formes se peignent dans la couche 60,
# comme le texte et comme les calques d'image, dans l'ordre de la liste. Il n'y
# a pas de couche « formes » : il y a des slots, et ils sont où les slots sont.
# ═════════════════════════════════════════════════════════════════════════════

FORMES = ("rect", "ellipse", "line", "arrow")
CLES_FORMES = ("fill", "fill_alpha", "stroke", "stroke_mm", "head_mm",
               "arrow_start", "arrow_end", "flip")
CLES_CONTOUR = ("plate_stroke", "plate_stroke_mm")


def test_les_quatre_formes_sont_dans_les_deux_vocabulaires():
    """`KINDS` s'élargit des DEUX côtés ou d'aucun : une valeur que l'écran
    connaît et que le backend ignore, c'est un slot RÉPARÉ en « text » à
    chaque chargement — un document que le serveur réécrit sous l'auteur."""
    assert TY.KINDS == ("text", "image") + FORMES, TY.KINDS
    src = _js()
    assert 'const KINDS = ["text", "image", "rect", "ellipse", "line", "arrow"];' \
        in src, "le vocabulaire de l'écran diverge"
    for k in FORMES:
        assert TY.norm_slot({"kind": k})["kind"] == k, k
        assert TY.norm_slot({"kind": k.upper()})["kind"] == k, k
        assert TY.norm_slot({"kind": " " + k + " "})["kind"] == k, k
    # une nature inventée retombe toujours sur le texte
    assert TY.norm_slot({"kind": "polygon"})["kind"] == "text"
    assert TY.norm_slot({"kind": "arrowhead"})["kind"] == "text"


def test_les_dix_cles_neuves_sont_dans_les_deux_tables_et_INERTES():
    """49 clés par slot. Le bloc JS est du JSON littéral et l'égalité avec le
    dictionnaire Python est STRICTE.

    ET LE DÉFAUT NE PEINT RIEN : `fill` et `stroke` naissent nuls, `stroke_mm`
    et `plate_stroke_mm` à 0. C'est ce qui garde les quatre gabarits livrés
    identiques À L'OCTET après l'arrivée de dix réglages — la même règle que
    `plate_color: null` de la 3a et `kind: "text"` de la 3b."""
    js = json.loads(_bloc_js("DEFAULTS"))
    assert js == TY.SLOT_DEFAULTS
    assert len(js) == 49, sorted(js)
    for k in CLES_FORMES + CLES_CONTOUR:
        assert k in js and k in TY.SLOT_DEFAULTS, k
    assert TY.SLOT_DEFAULTS["fill"] is None
    assert TY.SLOT_DEFAULTS["stroke"] is None
    assert TY.SLOT_DEFAULTS["plate_stroke"] is None
    assert TY.SLOT_DEFAULTS["stroke_mm"] == 0.0
    assert TY.SLOT_DEFAULTS["plate_stroke_mm"] == 0.0
    assert TY.SLOT_DEFAULTS["fill_alpha"] == 1.0
    assert TY.SLOT_DEFAULTS["arrow_end"] is True
    assert TY.SLOT_DEFAULTS["arrow_start"] is False
    assert TY.SLOT_DEFAULTS["flip"] is False
    assert TY.SLOT_DEFAULTS["head_mm"] == 3.0


def test_les_couleurs_de_forme_valent_PAS_DE_COULEUR_quand_elles_sont_folles():
    """La leçon de `plate_color`, appliquée aux trois couleurs neuves : une
    couleur illisible ne vaut pas « noir ». Peindre du noir sur une forme
    parce qu'un import a écrit « bleu » serait un défaut visible et muet."""
    for k in ("fill", "stroke", "plate_stroke"):
        assert TY.norm_slot({k: "#a1b2c3"})[k] == "#a1b2c3"
        assert TY.norm_slot({k: "#A1B2C3"})[k] == "#a1b2c3", "bas de casse"
        assert TY.norm_slot({k: "#abc"})[k] == "#abc"
        assert TY.norm_slot({k: "#a1b2c3ff"})[k] == "#a1b2c3ff", "l'alpha 8 signes"
        for fou in ("bleu", "", None, 7, [], {}, "#12345", "rgb(1,2,3)"):
            assert TY.norm_slot({k: fou})[k] is None, (k, fou)


def test_les_longueurs_de_forme_sont_bornees_des_deux_cotes():
    """Des millimètres, pas des chaînes libres. Un trait de 900 mm sur une
    carte de 63 mm n'est pas un réglage : il est ramené au plafond, et le
    plafond est le MÊME des deux côtés."""
    assert (TY.STROKE_MM_MIN, TY.STROKE_MM_MAX) == (0.0, 20.0)
    assert (TY.HEAD_MM_MIN, TY.HEAD_MM_MAX) == (0.0, 40.0)
    for k, hi in (("stroke_mm", TY.STROKE_MM_MAX),
                  ("plate_stroke_mm", TY.STROKE_MM_MAX),
                  ("head_mm", TY.HEAD_MM_MAX)):
        assert TY.norm_slot({k: 900})[k] == hi, k
        assert TY.norm_slot({k: -3})[k] == 0.0, k
        assert TY.norm_slot({k: "pas un nombre"})[k] == TY.SLOT_DEFAULTS[k], k
        assert TY.norm_slot({k: None})[k] == TY.SLOT_DEFAULTS[k], k
    assert TY.norm_slot({"fill_alpha": 9})["fill_alpha"] == 1.0
    assert TY.norm_slot({"fill_alpha": -1})["fill_alpha"] == 0.0
    src = _js()
    assert "const STROKE_MM_MAX = 20;" in src, "la borne de l'écran diverge"
    assert "const HEAD_MM_MAX = 40;" in src, "la borne de l'écran diverge"


# ── 14.1 LE PEINTRE : des pixels à VÉRITÉ CONNUE ────────────────────────────
#
# Le banc de pixels (`_banc_plaque`) fait tourner le VRAI painter z=60 sur un
# tampon réel. On y pose une forme dont on connaît la géométrie AVANT de la
# peindre, et on relit les octets aux points que le TEST a calculés — jamais
# ceux que le code testé annonce.

RECT_SLOT = {"id": "forme", "kind": "rect", "box": [10.0, 20.0, 30.0, 16.0],
             "fill": "#20c0ff", "stroke": None, "stroke_mm": 0.0, "text": ""}


def test_un_rect_encre_SA_BOITE_et_rien_de_plus(tmp_path):
    """VÉRITÉ CONNUE : une boîte de 30 x 16 mm posée à (10, 20). À 300 DPI
    c'est 354,33 x 188,98 px. On relit le pavé RÉELLEMENT encré et on le
    compare à cette arithmétique-là, faite ici."""
    d = _banc_plaque(tmp_path, {"slots": [RECT_SLOT],
                                "pave": [10.0, 20.0, 30.0, 16.0],
                                "points": {"dedans": [25.0, 28.0],
                                           "gauche": [8.0, 28.0],
                                           "droite": [42.0, 28.0],
                                           "haut": [25.0, 18.0],
                                           "bas": [25.0, 38.0]}})
    p = d["points"]
    assert p["dedans"][3] > 200, "le rect ne peint rien à son centre"
    assert p["dedans"][:3] == [32, 192, 255], p["dedans"]      # #20c0ff
    for nom in ("gauche", "droite", "haut", "bas"):
        assert p[nom][3] == 0, (nom, p[nom])
    pv = d["pave"]
    attendu_w = 30.0 / 25.4 * 300
    attendu_h = 16.0 / 25.4 * 300
    assert abs(pv["w"] - attendu_w) <= 2, (pv, attendu_w)
    assert abs(pv["h"] - attendu_h) <= 2, (pv, attendu_h)


ELL_SLOT = {"id": "halo", "kind": "ellipse", "box": [16.0, 30.0, 24.0, 24.0],
            "fill": "#20c0ff", "stroke": None, "stroke_mm": 0.0, "text": ""}


def test_une_ellipse_a_boite_CARREE_est_le_DISQUE_inscrit(tmp_path):
    """LE TRANSMIS DE LA PHASE 4 SE FERME ICI. Il n'existait « pas de cercle »
    et le halo du Patriarche était posé en calque d'image ; la recette est
    désormais écrite dans le code ET mesurée : ellipse + boîte carrée = disque,
    rayon = demi-côté, centre = centre de la boîte.

    LA PREUVE EST UN IoU, pas une impression. Le banc construit le disque
    ATTENDU à la main (centre de la boîte, demi-côté) et le confronte au
    masque PEINT, pixel par pixel. Un rendu qui déborderait, se décalerait ou
    resterait rectangulaire ferait chuter le chiffre ; un « ça a l'air rond »
    ne l'aurait pas vu.

    Le second chiffre est la COUVERTURE : un rectangle plein occuperait 100 %
    de la boîte, le disque inscrit en occupe π/4 = 78,54 %. C'est lui qui
    sépare les deux formes sans rien savoir de leur position."""
    d = _banc_plaque(tmp_path, {"slots": [ELL_SLOT],
                                "masque": [16.0, 30.0, 24.0, 24.0],
                                "points": {"dedans": [28.0, 42.0],
                                           "coin_hg": [17.0, 31.0],
                                           "coin_hd": [39.0, 31.0],
                                           "coin_bg": [17.0, 53.0],
                                           "coin_bd": [39.0, 53.0]}})
    m = d["masque"]
    assert m["peints"] > 0, "l'ellipse ne peint rien"
    part = m["peints"] / float(m["cellules"])
    assert 0.76 <= part <= 0.81, f"couverture {part:.4f} : ce n'est pas un disque"
    assert m["iou"] >= 0.97, f"IoU {m['iou']:.4f} contre le disque attendu"
    assert d["points"]["dedans"][3] > 200, d["points"]
    for nom in ("coin_hg", "coin_hd", "coin_bg", "coin_bd"):
        assert d["points"][nom][3] == 0, (nom, d["points"][nom])


def test_un_rect_de_MEME_boite_couvre_toute_sa_boite(tmp_path):
    """LE TÉMOIN DE LA MESURE PRÉCÉDENTE. Sans lui, « couverture entre 76 % et
    81 % » ne prouve rien : il faut montrer que la MÊME mesure sur la MÊME
    boîte rend 100 % pour un rectangle. Deux formes, un seul instrument."""
    d = _banc_plaque(tmp_path, {"slots": [dict(ELL_SLOT, kind="rect")],
                                "masque": [16.0, 30.0, 24.0, 24.0]})
    m = d["masque"]
    part = m["peints"] / float(m["cellules"])
    assert part > 0.99, f"couverture {part:.4f} : le rect n'est pas plein"
    # ... et son IoU contre le DISQUE est justement mauvais : π/4
    assert 0.77 <= m["iou"] <= 0.80, m["iou"]


FLECHE_SLOT = {"id": "fleche", "kind": "arrow", "box": [10.0, 40.0, 40.0, 0.0],
               "stroke": "#ff4020", "stroke_mm": 1.0, "head_mm": 6.0,
               "arrow_start": False, "arrow_end": True, "text": ""}


def test_une_fleche_posee_a_VERITE_CONNUE_met_son_trait_et_sa_tete_au_bon_endroit(tmp_path):
    """VÉRITÉ CONNUE, la plus exigeante du bloc. Une flèche horizontale de
    (10, 40) à (50, 40) mm — boîte de 40 x 0 mm —, trait de 1 mm, tête de
    6 mm, pointe à droite.

    Ce qu'on exige, et qui se calcule sans le code testé :
      · de l'encre AU MILIEU du fût, à (30, 40) ;
      · de l'encre juste avant la POINTE, à (49,6 ; 40) ;
      · de l'encre à la base de la tête, ÉCARTÉE du fût : à (44,5 ; ±1,4 mm)
        il y a la tête, et il n'y aurait RIEN sans elle — le fût ne fait que
        1 mm de large, donc ± 0,5 mm autour de y = 40 ;
      · RIEN 2 mm avant le départ, ni 2 mm après la pointe, ni 4 mm au-dessus
        du fût à mi-course (là où la tête n'est pas) ;
      · et l'autre bout est NU (`arrow_start` faux) : à (15,5 ; 41,4) il n'y a
        rien, alors que c'est le SYMÉTRIQUE EXACT d'un point encré à l'autre
        bout (44,5 ; 41,4)."""
    d = _banc_plaque(tmp_path, {"slots": [FLECHE_SLOT], "points": {
        "fut_milieu": [30.0, 40.0],
        "pointe": [49.6, 40.0],
        "tete_base_haut": [44.5, 41.4],
        "tete_base_bas": [44.5, 38.6],
        "avant_depart": [8.0, 40.0],
        "apres_pointe": [52.0, 40.0],
        "au_dessus_du_fut": [30.0, 36.0],
        "bout_nu": [15.5, 41.4],
    }})
    p = d["points"]
    for nom in ("fut_milieu", "pointe", "tete_base_haut", "tete_base_bas"):
        assert p[nom][3] > 200, (nom, p[nom])
        assert p[nom][:3] == [255, 64, 32], (nom, p[nom])   # #ff4020
    for nom in ("avant_depart", "apres_pointe", "au_dessus_du_fut", "bout_nu"):
        assert p[nom][3] == 0, (nom, p[nom])


def test_les_deux_bouts_de_la_fleche_sont_INDEPENDANTS(tmp_path):
    """`arrow_start` et `arrow_end` sont deux réglages, pas un. Le témoin est
    le MÊME point (11,5 ; 41,4) : vide quand le bout de départ est nu, encré
    quand il porte sa tête."""
    # les DEUX points sont symétriques à l'axe de la flèche : à 5,5 mm de leur
    # pointe, la tête de 6 mm est large de 2,75 mm de part et d'autre, donc
    # 1,4 mm y tombe DEDANS. Choisir deux points asymétriques aurait fait
    # « prouver » l'indépendance par la géométrie plutôt que par le réglage.
    pts = {"depart_haut": [15.5, 41.4], "fin_haut": [44.5, 41.4],
           "fut_milieu": [30.0, 40.0]}
    nu = _banc_plaque(tmp_path, {"slots": [FLECHE_SLOT], "points": pts})
    assert nu["points"]["depart_haut"][3] == 0, nu["points"]
    assert nu["points"]["fin_haut"][3] > 200, nu["points"]
    deux = _banc_plaque(tmp_path, {"slots": [
        dict(FLECHE_SLOT, arrow_start=True)], "points": pts})
    assert deux["points"]["depart_haut"][3] > 200, deux["points"]
    assert deux["points"]["fin_haut"][3] > 200, "la tête de fin a disparu"
    aucun = _banc_plaque(tmp_path, {"slots": [
        dict(FLECHE_SLOT, arrow_start=False, arrow_end=False)], "points": pts})
    assert aucun["points"]["depart_haut"][3] == 0
    assert aucun["points"]["fin_haut"][3] == 0, "une tête sans bout demandé"
    # ... et le fût reste : une flèche sans tête est un trait, pas rien
    assert aucun["points"]["fut_milieu"][3] > 200


def test_la_tete_de_fleche_SUIT_sa_longueur(tmp_path):
    """`head_mm` est une longueur, pas un interrupteur. Une tête de 12 mm
    encre un point que la tête de 6 mm ne touche pas — et le fût, lui, ne
    bouge pas d'un pixel."""
    pts = {"loin_derriere": [39.0, 41.4], "fut_milieu": [30.0, 40.0]}
    court = _banc_plaque(tmp_path, {"slots": [FLECHE_SLOT], "points": pts})
    assert court["points"]["loin_derriere"][3] == 0, court["points"]
    longue = _banc_plaque(tmp_path, {"slots": [dict(FLECHE_SLOT, head_mm=12.0)],
                                     "points": pts})
    assert longue["points"]["loin_derriere"][3] > 200, longue["points"]
    assert longue["points"]["fut_milieu"][3] > 200


def test_la_ligne_va_D_UN_COIN_A_L_AUTRE_et_le_flip_la_retourne(tmp_path):
    """LA DÉCISION D'AXE, MESURÉE. Une ligne va du coin haut-gauche de sa
    boîte au coin bas-droit ; `flip` la fait partir du coin bas-gauche. C'est
    la règle la plus simple qui donne l'horizontale (hauteur nulle), la
    verticale (largeur nulle) et les deux diagonales sans un réglage d'angle
    de plus — et ce test la sépare de son contraire au pixel.

    Boîte 20 x 20 mm posée à (10, 40) : la diagonale descendante passe par
    (15, 45) et PAS par (15, 55) ; retournée, l'inverse exactement."""
    box = {"id": "trait", "kind": "line", "box": [10.0, 40.0, 20.0, 20.0],
           "stroke": "#20c0ff", "stroke_mm": 1.2, "text": ""}
    pts = {"descendante": [15.0, 45.0], "montante": [15.0, 55.0]}
    a = _banc_plaque(tmp_path, {"slots": [box], "points": pts})
    assert a["points"]["descendante"][3] > 200, a["points"]
    assert a["points"]["montante"][3] == 0, a["points"]
    b = _banc_plaque(tmp_path, {"slots": [dict(box, flip=True)], "points": pts})
    assert b["points"]["montante"][3] > 200, b["points"]
    assert b["points"]["descendante"][3] == 0, b["points"]


ENCART = {"id": "rules", "text": "X", "align": "left", "valign": "top",
          "size_pt": 7.0, "min_pt": 7.0, "autofit": False, "wrap": False,
          "plate_color": None, "box": [10.0, 20.0, 30.0, 16.0]}


def test_le_contour_propre_d_un_encart_borde_SANS_remplir(tmp_path):
    """`plate_stroke` + `plate_stroke_mm` sur TOUTE zone — « la main sur les
    bordures des encarts ». Le cas qui compte est celui SANS plaque : un
    encadré de règles qu'on veut BORDER sans rien peindre dessous. Le bord
    doit exister et l'intérieur rester vide.

    Le témoin porte un texte d'un signe, posé en haut à gauche : la sonde du
    milieu-bas est donc à distance de tout glyphe, et ce qu'elle mesure est le
    FOND — pas une lettre."""
    slot = dict(ENCART, plate_stroke="#ff4020", plate_stroke_mm=0.8)
    d = _banc_plaque(tmp_path, {"slots": [slot], "points": {
        "bord_haut": [25.0, 20.0],
        "bord_gauche": [10.0, 32.0],
        "milieu": [25.0, 32.0],
        "dehors": [25.0, 17.0],
    }})
    p = d["points"]
    assert p["bord_haut"][3] > 150 and p["bord_haut"][:3] == [255, 64, 32], p
    assert p["bord_gauche"][3] > 150, p
    assert p["milieu"][3] == 0, "le contour a REMPLI la zone"
    assert p["dehors"][3] == 0, p
    # ... et avec une plaque, les deux coexistent : fond + bord
    d2 = _banc_plaque(tmp_path, {"slots": [dict(slot, plate_color="#20c0ff")],
                                 "points": {"milieu": [25.0, 32.0],
                                            "bord_haut": [25.0, 20.0]}})
    assert d2["points"]["milieu"][:3] == [32, 192, 255], d2["points"]
    assert d2["points"]["bord_haut"][:3] == [255, 64, 32], d2["points"]


def test_le_contour_d_encart_a_zero_mm_ne_peint_RIEN(tmp_path):
    """Le pendant du liseré de fenêtre de P2 : à 0 mm il n'y a pas un trait
    fin, il n'y a PAS DE TRAIT. C'est cette ligne-là qui garde les gabarits
    livrés identiques."""
    ref = _banc_plaque(tmp_path, {"slots": [ENCART]})
    for var in ({"plate_stroke": "#ff4020", "plate_stroke_mm": 0.0},
                {"plate_stroke": None, "plate_stroke_mm": 2.0},
                {"plate_stroke": "bleu", "plate_stroke_mm": 2.0}):
        d = _banc_plaque(tmp_path, {"slots": [dict(ENCART, **var)]})
        assert d["hash"] == ref["hash"], var


def test_un_encart_VIDE_ne_recoit_ni_fond_ni_bord(tmp_path):
    """LA RÈGLE HÉRITÉE, ET ELLE VAUT AUSSI POUR LE BORD. Un bloc de texte
    sans glyphe ne peint RIEN — pas même sa plaque : « un cartouche sans son
    contenu est un défaut visible qu'on n'a pas demandé ». Le contour propre
    suit son fond : le donner au bloc vide aurait posé un cadre rouge autour
    d'une colonne CSV manquante, exactement le compteur menteur que cette
    pièce pourchasse."""
    vide = dict(ENCART, text="", plate_color="#20c0ff",
                plate_stroke="#ff4020", plate_stroke_mm=0.8)
    d = _banc_plaque(tmp_path, {"slots": [vide], "points": {
        "bord_haut": [25.0, 20.0], "milieu": [25.0, 32.0]}})
    assert d["points"]["bord_haut"][3] == 0, d["points"]
    assert d["points"]["milieu"][3] == 0, d["points"]


def test_une_forme_sans_encre_ne_peint_RIEN(tmp_path):
    """Le pendant du calque d'image sans source : une forme sans remplissage
    ni contour n'est pas un carré noir, c'est une forme qu'on n'a pas encore
    habillée. Le panneau la montre ; la carte, non."""
    vide = {"id": "forme", "kind": "rect", "box": [10.0, 20.0, 30.0, 16.0],
            "text": ""}
    ref = _banc_plaque(tmp_path, {"slots": [dict(vide, kind="text")]})
    for k in FORMES:
        d = _banc_plaque(tmp_path, {"slots": [dict(vide, kind=k)]})
        assert d["hash"] == ref["hash"], \
            f"{k} sans encre peint quelque chose"


def test_une_forme_n_entre_PAS_dans_le_releve_typographique(tmp_path):
    """Le relevé alimente les trois passes d'encre (contraste, halo, survie) et
    le panneau. Une forme n'a pas de glyphe : y entrer la ferait compter comme
    « slot vide » — un défaut annoncé qui n'existe pas, exactement ce qu'on a
    évité pour les calques d'image."""
    d = _banc_plaque(tmp_path, {"slots": [
        dict(RECT_SLOT, id="forme"),
        {"id": "titre", "text": "Veilleur", "box": [4.0, 4.0, 50.0, 8.0]},
    ]}, mutations=(MUT_MEAS,))
    assert d["meas"] is not None, "la porte du relevé ne s'est pas ouverte"
    assert d["meas"] == ["titre"], d["meas"]


def test_les_quatre_gabarits_livres_restent_identiques_A_L_OCTET(tmp_path):
    """DIX CLÉS NEUVES, ZÉRO PIXEL BOUGÉ. On rend chaque gabarit avec les clés
    et SANS elles (le banc les retire du slot, comme le ferait un document
    écrit avant cette phase) : les deux empreintes doivent être ÉGALES."""
    g = CT.geom("poker_eu", 300)
    for pid in TY.PRESETS:
        slots = TY.preset_slots(pid, g)
        avant = _banc_plaque(tmp_path, {"slots": slots,
                                        "drop": list(CLES_FORMES + CLES_CONTOUR)})
        apres = _banc_plaque(tmp_path, {"slots": slots})
        assert avant["hash"] == apres["hash"], \
            f"{pid} : les clés neuves changent le gabarit livré"


def test_les_deux_NORMALISEURS_rendent_le_MEME_slot_de_FORME(tmp_path):
    """PARITÉ D'EXÉCUTION sur les dix clés neuves — la leçon B1 rejouée. Deux
    normaliseurs qui divergent, c'est un document que le serveur RÉPARE au
    chargement, et personne ne le voit."""
    batterie = [
        {"kind": "rect", "fill": "#20c0ff", "stroke": "#000", "stroke_mm": 1.5},
        {"kind": "ellipse", "fill_alpha": 0.5},
        {"kind": "line", "flip": True, "stroke_mm": "2.5"},
        {"kind": "arrow", "head_mm": 900, "arrow_start": 1, "arrow_end": 0},
        {"kind": "ARROW", "head_mm": -4, "flip": "oui"},
        {"kind": "arrow", "head_mm": None, "stroke": "bleu", "fill": ""},
        {"plate_stroke": "#ABCDEF", "plate_stroke_mm": 999},
        {"plate_stroke": [1], "plate_stroke_mm": "beaucoup"},
        {"kind": "rect", "fill": "#a1b2c3ff", "fill_alpha": "0.25"},
        {"kind": " Line ", "stroke": "#ABC", "arrow_end": None},
    ]
    d = _banc_verrou(tmp_path, {"state": {"slots": [], "sel": ""},
                                "norm": batterie},
                     mutations=(MUT_NORM,))
    js = d["norm"]
    assert js and len(js["un"]) == len(batterie)
    for i, entree in enumerate(batterie):
        py = TY.norm_slot(entree, i)
        ecran = js["un"][i]
        assert set(ecran) == set(py), \
            f"[{i}] clés divergentes : {sorted(set(ecran) ^ set(py))}"
        for k in sorted(py):
            assert ecran[k] == py[k], \
                f"[{i}] {k} : écran {ecran[k]!r} != backend {py[k]!r}"
        # ... et la seconde passe ne change rien (idempotence)
        assert js["deux"][i] == js["un"][i], f"[{i}] seconde passe"


def test_la_palette_offre_une_entree_PAR_FORME_en_francais():
    """« une entrée de palette par forme, étiquetée français ». Et chaque
    entrée doit NAÎTRE habillée : une forme posée sans encre serait un bouton
    qui ne pose rien de visible — le reproche qu'on fait aux barres
    concurrentes."""
    src = _js()
    bloc = re.search(r"const GENERIQUES = \[(.*?)\n  \];", src, re.S)
    assert bloc, "GENERIQUES introuvable"
    txt = bloc.group(1)
    for oid, libelle in (("gen:rect", "Rectangle"), ("gen:ellipse", "Ellipse"),
                         ("gen:line", "Ligne"), ("gen:arrow", "Flèche")):
        assert f'id: "{oid}"' in txt, f"{oid} absent de la palette"
        assert f'label: "{libelle}"' in txt, f"{oid} : libellé {libelle!r}"
    # chaque entrée est branchée, sinon le clic ne pose rien
    fn = _js_fn(src, "palAdd")
    for oid in ("gen:rect", "gen:ellipse", "gen:line", "gen:arrow"):
        assert f'"{oid}"' in fn, f"{oid} n'est pas branché dans palAdd"
    # ... et la naissance pose une encre
    nais = _js_fn(src, "addShapeSlot")
    assert "fill:" in nais and "stroke:" in nais, \
        "une forme naît sans encre : le bouton ne poserait rien de visible"


def test_le_panneau_d_une_forme_ne_montre_AUCUN_reglage_typographique():
    """Onze réglages inertes sur un objet qui n'a pas de glyphe, c'est le
    mensonge poli qu'on a refusé pour les calques d'image. Le panneau bascule
    sur la nature du bloc, comme il le fait déjà."""
    src = _js()
    fn = _js_fn(src, "renderInsp")
    assert "if (isShape(s)) { renderInspShape(box, s); return; }" in fn, \
        "le panneau ne bascule pas sur la nature « forme »"
    forme = _js_fn(src, "renderInspShape")
    for interdit in ("Police", "Corps (pt)", "Interlettrage", "Interligne",
                     "Blancs max", "Dern. ligne"):
        assert interdit not in forme, \
            f"le panneau d'une forme montre « {interdit} », qui ne fait rien"
    for attendu in ("Remplissage", "Contour", "Épaisseur"):
        assert attendu in forme, f"le panneau d'une forme n'offre pas « {attendu} »"


def test_le_peintre_des_formes_passe_sous_la_ROTATION_existante():
    """Une forme tourne comme un calque d'image tourne : autour du centre de
    sa boîte, dans la même passe. C'est le précédent de `drawImgSlot`, et le
    recopier ailleurs aurait donné deux conventions de rotation dans une même
    pièce."""
    src = _js()
    fn = _js_fn(src, "drawShapeSlot")
    assert "ctx.rotate(slot.rotate * Math.PI / 180)" in fn, \
        "la forme ne tourne pas autour du centre de sa boîte"
    assert "drawPlate(ctx, slot, g, { box: b })" in fn, \
        "la plaque n'est pas peinte SOUS la forme"
    assert "if (isShape(slot)) { drawShapeSlot(ctx, slot, geom); return; }" in src, \
        "le painter compose une forme au lieu de la dessiner"


def test_une_forme_TOURNEE_emporte_son_encre(tmp_path):
    """La rotation n'est pas décorative : un rect tourné de 90° doit encrer là
    où sa boîte tournée tombe, et PAS là où sa boîte droite tombait. Le témoin
    est un point que la rotation fait passer de vide à encré, et un autre qui
    fait l'inverse."""
    slot = {"id": "forme", "kind": "rect", "box": [20.0, 30.0, 30.0, 6.0],
            "fill": "#20c0ff", "text": ""}
    pts = {"bout_droit": [48.0, 33.0], "bout_tourne": [35.0, 45.0]}
    droit = _banc_plaque(tmp_path, {"slots": [slot], "points": pts})
    assert droit["points"]["bout_droit"][3] > 200, droit["points"]
    assert droit["points"]["bout_tourne"][3] == 0, droit["points"]
    tourne = _banc_plaque(tmp_path, {"slots": [dict(slot, rotate=90)],
                                     "points": pts})
    assert tourne["points"]["bout_tourne"][3] > 200, tourne["points"]
    assert tourne["points"]["bout_droit"][3] == 0, tourne["points"]


def test_l_opacite_du_slot_porte_AUSSI_sur_la_forme(tmp_path):
    """La règle de la plaque, tenue par la forme : l'opacité du slot
    MULTIPLIE celle du remplissage. Un slot à 50 % avec un remplissage à 80 %
    pose 40 %, et non 80 % — sans quoi baisser l'opacité d'un bloc ferait
    ressortir sa forme."""
    plein = _banc_plaque(tmp_path, {"slots": [RECT_SLOT],
                                    "points": {"c": [25.0, 28.0]}})
    demi = _banc_plaque(tmp_path, {"slots": [dict(RECT_SLOT, opacity=50)],
                                   "points": {"c": [25.0, 28.0]}})
    quart = _banc_plaque(tmp_path, {"slots": [
        dict(RECT_SLOT, opacity=50, fill_alpha=0.5)],
        "points": {"c": [25.0, 28.0]}})
    assert plein["points"]["c"][3] == 255, plein["points"]
    assert 120 <= demi["points"]["c"][3] <= 136, demi["points"]
    assert 58 <= quart["points"]["c"][3] <= 70, quart["points"]


# ── 14.2 LA VÉRIFICATION NAVIGATEUR D'UNE FLÈCHE POSÉE ──────────────────────
#
# LE BANC DE NODE PROUVE LA GÉOMÉTRIE ; IL NE PROUVE PAS LA TOILE. Son
# contexte 2D est une réimplémentation : `stroke()` y est un ruban de
# quadrilatères, `ellipse()` un polygone de 128 cordes, `arcTo` seize accords.
# Ce sont des approximations honnêtes et documentées — et une approximation ne
# dit rien de ce que Chrome dessine vraiment.
#
# Ici le MODULE ENTIER est chargé dans un Chrome sans tête, avec un CORE
# bouchonné, et le VRAI painter z=60 compose sur un VRAI `<canvas>`. On relit
# ensuite les pixels aux points que ce test a calculés en millimètres.
# C'est la première fois que ces formes rencontrent un rastériseur de
# production ; c'est aussi le seul endroit où `ctx.ellipse` est celui du
# navigateur et non le nôtre.

BANC_CHROME_TYPE = r"""
import { readFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
const PAGE = process.argv[2];
const SONDE = readFileSync(process.argv[3], "utf8");
const CHROME = [process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"]
  .filter(Boolean).find((p) => existsSync(p));
if (!CHROME) { process.stdout.write(JSON.stringify({ skip: "chrome" })); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const port = await new Promise((res, rej) => {
  const s = createServer(); s.on("error", rej);
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); });
});
const profile = join(tmpdir(), "dzcftype", "p" + port);
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
  await sleep(2000);
  const r = await send("Runtime.evaluate",
    { expression: SONDE, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) {
    process.stdout.write(JSON.stringify({
      erreur: JSON.stringify(r.exceptionDetails).slice(0, 900) }));
  } else {
    process.stdout.write(JSON.stringify(r.result.value));
  }
} finally { cleanup(); }
"""


def _page_formes(tmp_path, slots: list) -> pathlib.Path:
    """La page MINIMALE, et elle charge LE MODULE ENTIER : un CORE bouchonné,
    puis `mod-type.js` tel qu'il est livré. Aucune fonction n'est extraite,
    aucune n'est recopiée — c'est le painter du produit qui compose."""
    g = CT.geom("poker_eu", 300)
    geo = {"fmt": "poker_eu", "label": "Poker", "dpi": 300,
           "canvas_px": list(g.canvas_px), "trim_px": list(g.trim_px),
           "bleed_off_px": list(g.bleed_off_px), "safe_px": list(g.safe_px),
           "safe_off_px": list(g.safe_off_px), "bleed_mm": 3, "safe_mm": 3}
    page = tmp_path / "formes.html"
    page.write_text(
        "<!doctype html><meta charset=\"utf-8\">"
        "<body style=\"margin:0;background:#111\">"
        "<canvas id=\"cf-type-essai\"></canvas>"
        "<script>window.__ERR=[];"
        "window.onerror=function(m){window.__ERR.push(String(m));};"
        "window.__G=" + json.dumps(geo) + ";"
        "window.__G.mm2px=function(v){return v/25.4*300;};"
        "window.__G.px2mm=function(v){return v*25.4/300;};"
        "window.__DOC={type:{slots:" + json.dumps(slots, ensure_ascii=False)
        + "}};"
        "window.CF={"
        "register:function(c){window.__MOD=c;return{"
        "patch:function(p){Object.assign(window.__DOC.type,p);},"
        "api:{get:async function(){return{};},post:async function(){return{};},"
        "url:function(s){return '/api/cards/deck_00000000/type/'+s;}},"
        "emit:function(){},slot:function(){},aside:function(){},"
        "invalidate:function(){},toast:function(){},busy:function(){},"
        "on:function(){}};},"
        "get:function(p,d){var c=window.__DOC,ps=String(p).split('.');"
        "for(var i=0;i<ps.length;i++){if(c===null||typeof c!=='object'"
        "||!Object.prototype.hasOwnProperty.call(c,ps[i]))return d;c=c[ps[i]];}"
        "return c===undefined?d:c;},"
        "geom:function(){return window.__G;},current:function(){return 0;},"
        "cards:function(){return[];},card:function(){return{fields:{}};},"
        "on:function(){},renderCard:async function(){return null;},"
        "modules:function(){return[];}};"
        "</script>"
        f"<script src=\"{JS.as_uri()}\"></script>"
        "</body>", encoding="utf-8")
    return page


SONDE_FORMES = """(async () => {
  const cv = document.getElementById("cf-type-essai");
  cv.width = window.__G.canvas_px[0];
  cv.height = window.__G.canvas_px[1];
  const ctx = cv.getContext("2d", { willReadFrequently: true });
  const p = (window.__MOD.painters || []).filter((q) => q.z === 60)[0];
  if (!p) return { erreur: "aucun painter z=60" };
  await p.fn(ctx, window.__G, window.__DOC, { fields: {} }, "front");
  const px = (mmx, mmy) => {
    const d = ctx.getImageData(
      Math.round(window.__G.bleed_off_px[0] + mmx / 25.4 * 300),
      Math.round(window.__G.bleed_off_px[1] + mmy / 25.4 * 300), 1, 1).data;
    return [d[0], d[1], d[2], d[3]];
  };
  const pts = window.__PTS || {};
  const out = {};
  Object.keys(pts).forEach((k) => { out[k] = px(pts[k][0], pts[k][1]); });
  /* LE DISQUE, COMPTE PAR CHROME LUI-MEME : combien de cellules d'une boite
     carree sont encrees. Un rectangle en remplirait 100 %, le disque inscrit
     pi/4 = 78,54 %. C'est le meme instrument que le banc de node, mais le
     rasteriseur, lui, est celui du produit. */
  let disque = null;
  if (window.__BOX) {
    const b = window.__BOX;
    const x0 = Math.round(window.__G.bleed_off_px[0] + b[0] / 25.4 * 300);
    const y0 = Math.round(window.__G.bleed_off_px[1] + b[1] / 25.4 * 300);
    const w = Math.round(b[2] / 25.4 * 300), h = Math.round(b[3] / 25.4 * 300);
    const d = ctx.getImageData(x0, y0, w, h).data;
    let n = 0;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++;
    disque = { peints: n, cellules: w * h };
  }
  return { points: out, disque: disque, erreurs: window.__ERR || [] };
})()"""


def _chrome_formes(tmp_path, slots, points, box=None):
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du navigateur ne peut pas tourner")
    page = _page_formes(tmp_path, slots)
    txt = page.read_text(encoding="utf-8").replace(
        "</body>",
        "<script>window.__PTS=" + json.dumps(points) + ";"
        + ("window.__BOX=" + json.dumps(box) + ";" if box else "")
        + "</script></body>")
    page.write_text(txt, encoding="utf-8")
    sonde = tmp_path / "sonde.js"
    sonde.write_text(SONDE_FORMES, encoding="utf-8")
    banc = tmp_path / "banc_chrome_type.mjs"
    banc.write_text(BANC_CHROME_TYPE, encoding="utf-8")
    r = subprocess.run([node, str(banc), str(page), str(sonde)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-2000:])
    v = json.loads(r.stdout)
    if v.get("skip"):
        pytest.skip("Chrome absent : la vérification navigateur ne peut pas tourner")
    assert not v.get("erreur"), v.get("erreur")
    assert v.get("erreurs") == [], v.get("erreurs")
    return v


def test_une_fleche_et_un_cercle_TIENNENT_dans_un_vrai_navigateur(tmp_path):
    """LE PAINTER DU PRODUIT, SUR UN VRAI CANEVAS. Le module entier est chargé
    dans un Chrome sans tête ; le painter z=60 compose ; on relit les octets.

    Les mêmes vérités connues que le banc de node — mais mesurées cette fois
    sur `ctx.stroke` et `ctx.ellipse` du NAVIGATEUR, pas sur les nôtres :
      · le fût de la flèche, sa pointe et la base de sa tête sont encrés ;
      · rien avant le départ, rien après la pointe, rien au-dessus du fût ;
      · une ellipse à boîte carrée couvre π/4 de sa boîte, à un cheveu près."""
    fleche = dict(FLECHE_SLOT, id="fleche", side="front", on=True,
                  font="Inter", label="Flèche")
    v = _chrome_formes(tmp_path, [fleche], {
        "fut_milieu": [30.0, 40.0],
        "pointe": [49.6, 40.0],
        "tete_base_haut": [44.5, 41.4],
        "avant_depart": [8.0, 40.0],
        "apres_pointe": [52.0, 40.0],
        "au_dessus_du_fut": [30.0, 36.0],
        "bout_nu": [15.5, 41.4],
    })
    p = v["points"]
    for nom in ("fut_milieu", "pointe", "tete_base_haut"):
        assert p[nom][3] > 200, (nom, p[nom])
        assert p[nom][:3] == [255, 64, 32], (nom, p[nom])
    for nom in ("avant_depart", "apres_pointe", "au_dessus_du_fut", "bout_nu"):
        assert p[nom][3] == 0, (nom, p[nom])

    # ── LE BOUT DE TRAIT, PINNÉ LÀ OÙ IL EXISTE ────────────────────────────
    # Le banc de node n'a aucune notion de cap (son `stroke()` est un ruban de
    # quadrilatères, et son commentaire le dit) : y chercher `butt` contre
    # `round` serait un contrôle qui ne mesure rien. Chrome, lui, les sépare —
    # un bout arrondi déborde d'une DEMI-ÉPAISSEUR au-delà de la pointe, soit
    # 0,5 mm sur un trait de 1 mm. La sonde est posée à 0,3 mm au-delà : vide
    # avec un bout carré, encrée avec un bout rond.
    #
    # C'ÉTAIT UN « TÉMOIN SURVIVANT » AVEC UNE RAISON FAUSSE. Je l'avais écrit
    # non séparable ; il l'est, à une sonde près, et une propriété séparable à
    # coût nul se PINNE (la clôture T2 de la phase 4 : l'aveu se mesure).
    nu = dict(fleche, id="trait", arrow_end=False, head_mm=0.0)
    v3 = _chrome_formes(tmp_path, [nu], {"pointe": [49.6, 40.0],
                                         "apres_pointe": [50.3, 40.0]})
    assert v3["points"]["pointe"][3] > 200, v3["points"]
    assert v3["points"]["apres_pointe"][3] == 0, \
        "le trait déborde de son extrémité : le bout n'est plus carré"

    cercle = dict(ELL_SLOT, id="halo", side="front", on=True, font="Inter",
                  label="Halo")
    v2 = _chrome_formes(tmp_path, [cercle], {"centre": [28.0, 42.0],
                                             "coin_hg": [17.0, 31.0]},
                        box=[16.0, 30.0, 24.0, 24.0])
    assert v2["points"]["centre"][3] > 200, v2["points"]
    assert v2["points"]["coin_hg"][3] == 0, v2["points"]
    d = v2["disque"]
    part = d["peints"] / float(d["cellules"])
    assert 0.77 <= part <= 0.80, \
        f"couverture {part:.4f} : ce n'est pas le disque inscrit (π/4 = 0,7854)"


def test_la_bordure_de_zone_est_offerte_sur_LES_TROIS_natures():
    """« `plate_stroke` + `plate_stroke_mm` sur TOUTE zone. » Le réglage vit
    dans `inspPlaque`, le bloc que les TROIS panneaux partagent (texte, image,
    forme) : un bloc par nature aurait été trois occasions d'oublier la
    bordure sur l'une d'elles. Le test lit le partage là où il est, pas la
    présence d'une chaîne quelque part dans le fichier."""
    src = _js()
    pl = _js_fn(src, "inspPlaque")
    assert 'class="cf-type-bcol"' in pl, "aucun sélecteur de couleur de bordure"
    assert 'nfield("plate_stroke_mm"' in pl, "aucune épaisseur de bordure"
    assert "cf-type-bnone" in pl, "aucun retrait de bordure"
    # les trois panneaux appellent CE bloc-là
    for fn in ("renderInsp", "renderInspImage", "renderInspShape"):
        assert "inspPlaque(s)" in _js_fn(src, fn), \
            f"{fn} n'offre pas la plaque (donc pas la bordure)"
    # « sans bordure » rend les DEUX clés : un état, pas une couleur retirée
    wire = _js_fn(src, "wireInspCommun")
    assert "{ plate_stroke: null, plate_stroke_mm: 0 }" in wire, \
        "« sans bordure » laisserait une épaisseur ou une couleur orpheline"
    # et le pied de section NOMME l'état courant des deux
    assert "aucune bordure — posez une épaisseur" in pl, \
        "le panneau ne dit pas qu'il n'y a pas de bordure"


def _boite_ov(html: str) -> dict:
    """La boîte du calque d'édition, relue dans le style que `paintOverlay`
    écrit. On lit ce que le DOM PORTE, pas ce que la fonction dit faire."""
    m = re.search(r"left:([-\d.]+)px;top:([-\d.]+)px;"
                  r"width:([-\d.]+)px;height:([-\d.]+)px", html)
    assert m, html[:400]
    return {"left": float(m.group(1)), "top": float(m.group(2)),
            "w": float(m.group(3)), "h": float(m.group(4))}


def test_une_ligne_PLATE_reste_attrapable_sur_le_calque_d_edition(tmp_path):
    """UNE LIGNE HORIZONTALE EST UNE BOÎTE DE HAUTEUR NULLE — c'est la règle
    de l'axe, et c'est la forme qu'on trace neuf fois sur dix. Rendue telle
    quelle, sa boîte d'édition ferait ZÉRO pixel de haut : invisible, poignées
    superposées, et le seul chemin restant pour la déplacer serait le panneau.

    La boîte AFFICHÉE reçoit donc un plancher de saisie ; le DOCUMENT ne bouge
    pas. Quatre faits, tous relus sur le style que le calque écrit :
      1. la boîte d'une ligne plate a une hauteur non nulle à l'écran ;
      2. elle reste CENTRÉE sur la ligne (le plancher pousse des deux côtés) ;
      3. le slot, lui, garde sa hauteur nulle — et le geste part de LUI ;
      4. LE TÉMOIN : une boîte de TEXTE plate n'est PAS gonflée. Un défaut à
         voir n'est pas une prise à offrir, et sans ce témoin le test dirait
         seulement « quelque chose a une hauteur »."""
    # objet COMPLET : le calque d'edition recoit les slots du document tels
    # quels, et un partiel serait ecarte par le filtre `on` avant d'etre peint.
    plate = TY.norm_slot({"id": "trait", "kind": "line", "label": "Trait",
                          "box": [10.0, 40.0, 40.0, 0.0],
                          "stroke": "#20c0ff", "stroke_mm": 0.5})
    # LE CALQUE SE REPEINT QUAND LA SELECTION CHANGE : on part sans selection
    # et l'on pose la main sur la ligne, ce qui est exactement le geste dont
    # on teste la prise.
    d = _banc_verrou(tmp_path, {"state": {"slots": [plate], "sel": ""},
                                "actes": [{"t": "down", "id": "trait"},
                                          {"t": "up"}]})
    b = _boite_ov(d["ov"])
    assert b["h"] > 0, f"la boîte d'édition d'une ligne plate est plate : {b}"
    assert d["slots"][0]["box"][3] == 0.0, d["slots"][0]["box"]

    t = _banc_verrou(tmp_path, {
        "state": {"slots": [dict(plate, kind="text", id="txt", label="T")],
                  "sel": ""},
        "actes": [{"t": "down", "id": "txt"}, {"t": "up"}]})
    bt = _boite_ov(t["ov"])
    assert bt["h"] == 0, f"une boîte de TEXTE plate a été gonflée : {bt}"
    # ... et le gonflement est CENTRÉ : le milieu de la boîte de la forme est
    # la position de la boîte de texte, qui n'a pas bougé.
    assert abs((b["top"] + b["h"] / 2) - bt["top"]) < 0.51, (b, bt)
    assert abs(b["w"] - bt["w"]) < 0.01, "la largeur, elle, n'avait pas à bouger"


def test_une_forme_sans_encre_ne_peint_PAS_MEME_SA_PLAQUE(tmp_path):
    """LE TROU QUE LA MUTATION A OUVERT, ET CE QU'IL VALAIT. Le test voisin
    (« une forme sans encre ne peint rien ») reste VERT quand on retire la
    garde de sortie de `drawShapeSlot` : sans elle, les gardes internes
    (`if (fill)`, `if (trait)`) ne peignent rien non plus, et l'empreinte ne
    bouge pas. La garde n'était donc pas mesurée par ce chemin-là.

    ELLE PORTE POURTANT UNE DÉCISION, et c'est celle-ci : une forme qu'on n'a
    pas encore habillée ne peint PAS MÊME SA PLAQUE. C'est exactement la règle
    du bloc de texte vide (« un cartouche sans son contenu est un défaut
    visible qu'on n'a pas demandé ») et celle du calque d'image sans source
    (« RIEN n'est peint, pas même la plaque »). Sans la garde, poser un
    rectangle depuis la palette puis lui retirer son encre laisserait un aplat
    de plaque sur la carte — un objet qu'on croyait effacé.

    Le témoin est la même forme AVEC son encre : elle, peint."""
    nue = {"id": "forme", "kind": "rect", "box": [10.0, 20.0, 30.0, 16.0],
           "text": "", "plate_color": "#20c0ff", "plate_alpha": 1.0,
           "plate_stroke": "#ff4020", "plate_stroke_mm": 0.8}
    pts = {"milieu": [25.0, 28.0], "bord_haut": [25.0, 20.0]}
    d = _banc_plaque(tmp_path, {"slots": [nue], "points": pts})
    assert d["points"]["milieu"][3] == 0, \
        f"une forme sans encre a peint sa plaque : {d['points']}"
    assert d["points"]["bord_haut"][3] == 0, \
        f"une forme sans encre a peint sa bordure : {d['points']}"
    # ... et les quatre natures suivent la même règle
    for k in ("ellipse", "line", "arrow"):
        o = _banc_plaque(tmp_path, {"slots": [dict(nue, kind=k)], "points": pts})
        assert o["points"]["milieu"][3] == 0, (k, o["points"])
    # LE TÉMOIN : la même forme HABILLÉE peint, plaque comprise. Sans lui,
    # « rien n'est peint » se lirait aussi sur un painter mort.
    vif = _banc_plaque(tmp_path, {"slots": [dict(nue, fill="#f2efe9")],
                                  "points": pts})
    assert vif["points"]["milieu"][3] > 200, vif["points"]
    assert vif["points"]["bord_haut"][3] > 100, vif["points"]


# ═════════════════════════════════════════════════════════════════════════════
# 15. RONDE T2 — CE QUE LA REVUE A MESURÉ, ET QUI NE TENAIT PAS
# ═════════════════════════════════════════════════════════════════════════════

def test_layout_TAIT_les_colonnes_typographiques_d_une_forme():
    """LE BLOQUANT. `SHAPES` était du code MORT au backend : `layout()` posait
    `img = kind == "image"` seul, si bien qu'une forme sortait avec des
    CHIFFRES dans les colonnes de lisibilité — `size_px 41.67`, `read_pt 0.0` —
    trois lignes sous un commentaire qui dit « et non 0, qui se lirait comme
    une MESURE ». Une forme passait même par `missing_chars`, c'est-à-dire
    qu'on lui cherchait des glyphes absents.

    La question « ce bloc a-t-il des glyphes ? » se pose désormais UNE fois,
    au seul endroit prévu pour elle, et `SHAPES` sert enfin à ce que son
    commentaire promet."""
    g = CT.geom("poker_eu", 300)
    for k in TY.SHAPES:
        s = TY.norm_slot({"id": "f", "kind": k, "box": [10, 10, 30, 10],
                          "text": "Veilleur", "read_pt": 12.0, "size_pt": 10.0})
        r = TY.layout(g, [s])["slots"][0]
        for col in ("size_px", "min_px", "read_pt", "read_px", "posed_pt",
                    "under_read", "missing_glyphs"):
            assert r[col] is None, (k, col, r[col])
    # LE TÉMOIN : un bloc de TEXTE, lui, porte bien ces chiffres — sans quoi
    # « tout est None » se lirait aussi sur un `layout` mort.
    t = TY.norm_slot({"id": "t", "kind": "text", "box": [10, 10, 30, 10],
                      "text": "Veilleur", "read_pt": 12.0, "size_pt": 10.0})
    rt = TY.layout(g, [t])["slots"][0]
    assert rt["size_px"] is not None and rt["read_pt"] == 12.0


def test_la_ZONE_SURE_VOIT_l_encre_geometrique_d_une_forme():
    """LE DÉFAUT MESURÉ PAR LA REVUE, ET SA SORTIE. Une flèche posée en haut
    de carte, boîte `[10, 5, 40, 0]`, tête au plafond (`head_mm` 40) : sa tête
    encre jusqu'à **y = −2,0 mm**, soit 2 mm HORS COUPE — et `layout` rendait
    `ok: True`, `outside_safe: []`. La boîte, elle, était bien dans la zone
    sûre : c'est l'ENCRE qui en sortait, et personne ne la regardait.

    DÉCISION, ET ELLE EST DITE : c'est `layout()` qui GONFLE le rectangle
    jugé, pas le client qui envoie l'encre. Deux raisons. (a) L'encre d'une
    forme est DÉRIVABLE DU DOCUMENT SEUL — la boîte, `stroke_mm`, `head_mm`,
    les deux bouts — là où l'encre d'un texte dépend des fontes posées, ce qui
    est précisément pourquoi `inks` existe. (b) Le verdict tient alors SANS
    client : une route appelée directement, un contrôle avant vol de P7, un
    deck relu sur le disque sont jugés comme l'écran les juge.

    LA RECETTE, en toutes lettres : la boîte, gonflée de
    `max(stroke_mm / 2, head_mm / 2 si un bout est armé)` sur les quatre
    côtés. Le trait est CENTRÉ sur le chemin (donc la moitié de part et
    d'autre) et la tête est un triangle dont le demi-écart maximal au segment
    vaut `head_mm / 2` — sa pointe, elle, est le coin de la boîte et ne
    dépasse pas. La COULEUR n'entre pas dans le calcul : une flèche qui
    déborde ne devient pas correcte parce qu'on ne lui a pas encore choisi son
    encre."""
    g = CT.geom("poker_eu", 300)
    haut = TY.norm_slot({"id": "fleche", "kind": "arrow",
                         "box": [10.0, 5.0, 40.0, 0.0],
                         "stroke": "#ff4020", "stroke_mm": 1.0,
                         "head_mm": 40.0, "arrow_end": True})
    d = TY.layout(g, [haut])
    r = d["slots"][0]
    assert d["summary"]["ok"] is False, \
        "la flèche du plafond passe toujours pour correcte"
    assert d["summary"]["outside_safe"] == ["fleche"], d["summary"]
    assert r["ink_inside_safe"] is False, r
    # LE DÉBORD EST NOMMÉ, et il porte le nombre : la tête monte 2,0 mm
    # au-dessus du trait de coupe, donc 5,0 mm au-dessus du cadre sûr.
    assert r["ink_out_px"]["top"] > 0, r["ink_out_px"]
    # LES CHIFFRES SONT CEUX DU CALCUL, refaits ici à la main. Sur poker
    # (63 x 88), la borne de format vaut min(63, 88) = 63 : le plafond du
    # curseur (40) est le plus serré des deux, la tête reste donc ENTIÈRE et
    # sa demi-largeur vaut 20 mm. L'encre monte à 5 − 20 = **−15,0 mm** de la
    # coupe ; le cadre sûr commence à 2,9633 mm, d'où **17,9633 mm de débord**.
    y0_mm = (r["ink_px"][1] - g.bleed_off_px[1]) * 25.4 / 300
    assert -15.05 < y0_mm < -14.95, y0_mm
    safe_haut = (g.safe_off_px[1] - g.bleed_off_px[1]) * 25.4 / 300
    assert abs(r["ink_out_px"]["top"] * 25.4 / 300 - (safe_haut - y0_mm)) < 0.01
    assert 17.95 < r["ink_out_px"]["top"] * 25.4 / 300 < 17.98, r["ink_out_px"]
    assert 2.9 < safe_haut < 3.0
    # LE TÉMOIN : la MÊME flèche descendue au milieu de la carte tient, et le
    # dit. Il porte la MÊME tête : ce qui change est la place, pas le réglage.
    bas = TY.norm_slot(dict(haut, box=[10.0, 44.0, 40.0, 0.0]))
    d2 = TY.layout(g, [bas])
    assert d2["summary"]["ok"] is True, (d2["summary"], d2["slots"][0]["ink_px"])
    assert d2["slots"][0]["ink_inside_safe"] is True
    # ... ET LE FAUX DÉFAUT QUE LE PREMIER JET PRODUISAIT : la tête d'une
    # flèche HORIZONTALE ne déborde que vers le haut et le bas. Une marge
    # uniforme la faisait sortir « à gauche » de 5,75 mm — un voyant qu'on
    # apprend à ne plus croire.
    ink = d2["slots"][0]["ink_px"]
    assert abs(ink[0] - (g.bleed_off_px[0] + 10.0 / 25.4 * 300)) < 0.6, ink


def test_l_encre_d_une_forme_suit_SES_LONGUEURS_et_pas_sa_couleur():
    """La recette, éprouvée réglage par réglage : le trait gonfle de sa
    moitié, la tête de sa moitié quand un bout est armé, et RIEN quand aucun
    ne l'est. La couleur ne change pas un millimètre."""
    g = CT.geom("poker_eu", 300)
    mm = 300 / 25.4

    def ink(**kw):
        s = TY.norm_slot(dict({"id": "f", "kind": "arrow",
                               "box": [10.0, 40.0, 40.0, 0.0],
                               "stroke_mm": 0.0, "head_mm": 0.0,
                               "arrow_end": False}, **kw))
        return TY.layout(g, [s])["slots"][0]["ink_px"]

    nu = ink()
    assert abs(nu[3]) < 0.01, nu           # rien à gonfler : hauteur nulle
    trait = ink(stroke_mm=2.0)
    assert abs(trait[3] - 2.0 * mm) < 0.5, trait
    tete = ink(head_mm=6.0, arrow_end=True)
    assert abs(tete[3] - 6.0 * mm) < 0.5, tete
    # le MAX, pas la somme : au même endroit, le plus large gagne
    deux = ink(stroke_mm=2.0, head_mm=6.0, arrow_end=True)
    assert abs(deux[3] - 6.0 * mm) < 0.5, deux
    # une tête sur une LIGNE ne compte pas : `line` n'a pas de tête
    ligne = TY.norm_slot({"id": "f", "kind": "line", "box": [10, 40, 40, 0],
                          "stroke_mm": 2.0, "head_mm": 40.0, "arrow_end": True})
    li = TY.layout(g, [ligne])["slots"][0]["ink_px"]
    assert abs(li[3] - 2.0 * mm) < 0.5, li
    # ... et la COULEUR ne bouge rien
    assert ink(stroke_mm=2.0, stroke="#ff4020") == trait


def test_l_ecran_VOIT_le_meme_debord_que_le_backend(tmp_path):
    """« L'écran aveugle au même endroit » : `MEAS` écarte les formes, donc
    `m` valait `null`, donc le liseré d'alerte du calque d'édition ne partait
    JAMAIS pour une forme. Le calque calcule désormais l'encre géométrique
    lui-même — la même recette, écrite une fois de chaque côté — et la boîte
    fautive porte sa marque."""
    fleche = TY.norm_slot({"id": "fleche", "label": "Flèche", "kind": "arrow",
                           "box": [10.0, 5.0, 40.0, 0.0], "stroke": "#ff4020",
                           "stroke_mm": 1.0, "head_mm": 40.0})
    d = _banc_verrou(tmp_path, {"state": {"slots": [fleche], "sel": ""},
                                "actes": [{"t": "down", "id": "fleche"},
                                          {"t": "up"}]})
    assert "cf-type-hbox" in d["ov"] and " bad" in d["ov"], \
        "le calque d'édition ne marque pas la flèche qui sort du cadre"
    assert "hors cadre" in d["ov"], d["ov"][:400]
    # LE TÉMOIN : la même flèche 20 mm plus bas n'est PAS marquée.
    ok = TY.norm_slot(dict(fleche, box=[10.0, 44.0, 40.0, 0.0]))
    d2 = _banc_verrou(tmp_path, {"state": {"slots": [ok], "sel": ""},
                                 "actes": [{"t": "down", "id": "fleche"},
                                           {"t": "up"}]})
    assert " bad" not in d2["ov"], d2["ov"][:400]


# ── 15.1 `\\d` N'EST PAS LE MÊME DES DEUX CÔTÉS ──────────────────────────────

CHIFFRES_EXOTIQUES = ("١٢", "१२", "１２")     # arabe · devanagari · pleine chasse


def test_les_chiffres_NON_ASCII_tombent_des_DEUX_cotes():
    """`\\d` de Python est UNICODE, `\\d` de JavaScript est ASCII. « ١٢ » (deux
    chiffres arabo-indiens) faisait donc `fullmatch` VRAI ici — `float("١٢")`
    vaut 12.0 — et FAUX à l'écran, qui retombait sur le défaut. Mesuré par la
    revue : trois écarts sur les clés neuves, et LE RÉGIME DE LA GEMME QUI
    BASCULE (voir le jumeau dans `test_cards_frame.py`).

    Le motif est donc ancré sur `[0-9]` explicitement, des deux côtés. Ce
    n'est pas une préférence : c'est la seule forme que les deux langages
    lisent pareil, et c'est déjà la règle écrite pour `BACK_NUM_RE`."""
    for ex in CHIFFRES_EXOTIQUES:
        assert TY._NUM_RE.fullmatch(ex) is None, ex
        for k in ("stroke_mm", "head_mm", "plate_stroke_mm", "size_pt",
                  "opacity", "plate_alpha"):
            assert TY.norm_slot({k: ex})[k] == TY.SLOT_DEFAULTS[k], (k, ex)
    # ... et l'ASCII, lui, passe toujours
    assert TY.norm_slot({"stroke_mm": "2.5"})["stroke_mm"] == 2.5
    # LES DEUX MOTIFS SONT LE MÊME MOT À MOT. Écrits `\d` de part et d'autre,
    # ils se LISAIENT très bien et rendaient deux verdicts : c'est le seul
    # contrôle qui l'aurait vu avant que la revue le mesure.
    assert r"/^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?$/" in _js()
    assert "\\d" not in TY._NUM_RE.pattern


def test_le_nom_d_une_image_ne_peut_PAS_porter_des_chiffres_exotiques():
    """La même faille sur les DEUX motifs de nom : `img:img_١٢.png` passait
    ici (`\\d` unicode) et pas à l'écran. Un nom que le backend accepte et que
    le client ne sait pas fabriquer est une source qui ne se relit jamais."""
    for ex in CHIFFRES_EXOTIQUES:
        assert TY.SLOT_SRC_RE.fullmatch(f"img:img_{ex}.png") is None, ex
        assert TY.IMG_NAME_RE.fullmatch(f"img_{ex}.png") is None, ex
        assert TY.norm_slot({"src": f"img:img_{ex}.png"})["src"] == ""
    assert TY.SLOT_SRC_RE.fullmatch("img:img_12.png") is not None
    assert "\\d" not in TY.SLOT_SRC_RE.pattern
    assert "\\d" not in TY.IMG_NAME_RE.pattern


def test_les_trois_booleens_NEUFS_lisent_la_MEME_chose_des_deux_cotes():
    """`[]` et `{}` valent VRAI en JavaScript (`!![]`) et FAUX en Python
    (`bool([])`). Sur `arrow_start` / `arrow_end` / `flip`, une flèche
    dessinée à un bout ici l'aurait été à l'autre là-bas.

    LA CLASSE EST PLUS LARGE QUE MES TROIS CLÉS — `wrap`, `on`, `lock`,
    `autofit`, `bold`, `italic`, `hyphen` portent la MÊME divergence, et elle
    est ANTÉRIEURE à cette phase. Je ferme ce que j'ai ouvert et je NOMME le
    reste : mon commit annonçait la fermeture de la classe entière, ce qui
    était faux.

    LA RÈGLE DES TROIS NEUVES : seul un VRAI booléen décide ; tout le reste
    vaut le défaut. C'est plus strict que `bool()` et que `!!`, et c'est la
    seule lecture que les deux langages partagent."""
    for k, defaut in (("arrow_start", False), ("arrow_end", True),
                      ("flip", False)):
        assert TY.norm_slot({k: True})[k] is True, k
        assert TY.norm_slot({k: False})[k] is False, k
        for fou in ([], {}, "oui", "", 0, 1, None, [0]):
            assert TY.norm_slot({k: fou})[k] is defaut, (k, fou)


def test_head_mm_est_borne_PAR_LE_FORMAT_et_pas_seulement_en_absolu():
    """Même défaut que le rayon de gemme, même remède : 40 mm de tête sur un
    `micro` (31,75 x 44,45 mm) est une tête PLUS LARGE QUE LA CARTE. La borne
    absolue reste le plafond du curseur ; celle qui MORD vient du format."""
    petit = CT.geom("micro", 300)
    tw, th = petit.trim_mm
    assert TY.head_max_mm(tw, th) < TY.HEAD_MM_MAX
    assert TY.head_max_mm(tw, th) == min(tw, th)
    grand = CT.geom("tarot_eu", 300)
    assert TY.head_max_mm(*grand.trim_mm) == TY.HEAD_MM_MAX, \
        "la borne du format mord là où le format ne l'impose pas"
    # elle s'applique AU TRACÉ, comme `min(f.edge_mm, cap)` du cadre
    s = TY.norm_slot({"id": "f", "kind": "arrow", "box": [4, 20, 20, 0],
                      "stroke_mm": 0.5, "head_mm": 40.0, "arrow_end": True})
    r = TY.layout(petit, [s])["slots"][0]
    mm = 300 / 25.4
    assert r["ink_px"][3] <= TY.head_max_mm(tw, th) * mm + 0.5, r["ink_px"]


def test_le_pied_du_panneau_de_plaque_NE_CONTREDIT_PAS_la_carte():
    """DEUX PHRASES DU MÊME PANNEAU SE CONTREDISAIENT. Sur une forme sans
    encre, la carte ne peint RIEN — pas même la plaque, c'est la règle et elle
    est mesurée — pendant que le pied de la section affirmait « plaque
    #20c0ff à 100 % · bordure 0,80 mm ». Le pied porte désormais la CONDITION
    de la garde quand le bloc est une forme."""
    src = _js()
    pl = _js_fn(src, "inspPlaque")
    assert "plaqueMuette(s)" in pl, \
        "le pied de la plaque ne consulte pas la garde du painter"
    fn = _js_fn(src, "plaqueMuette")
    assert "isShape(s)" in fn and "stroke" in fn, fn
    # la phrase EXISTE et nomme la cause
    assert "tant que cette forme n\u2019a pas d\u2019encre" in pl, pl


def test_les_deux_temoins_survivants_sont_PINNES_par_une_sonde(tmp_path):
    """LA RAISON ÉCRITE NE TENAIT PAS À LA MESURE, et c'est exactement ce que
    la clôture T2 de la phase 4 interdit (« l'aveu se mesure comme une
    affirmation de succès »).

    Ce que j'avais écrit : « la base de la tête et le bout de trait sont des
    décisions de dessin, non séparables ». MESURÉ PAR LA REVUE, et reproduit
    ici : les deux SONT séparables, à une sonde près.
      · la base de la tête (`head * 0.5`) : la sonde (44,5 ; 43,2) est DEHORS
        à 0,5 et DEDANS à 0,7 — un demi-millimètre de plus qu'il n'en faut ;
      · le bout de trait : le banc node n'a aucune notion de cap, mais CHROME
        sépare `butt` de `round` à 0,4 mm au-delà du départ.
    Une propriété séparable à coût nul se PINNE. Le témoin meurt, la mesure
    reste."""
    p = _banc_plaque(tmp_path, {"slots": [FLECHE_SLOT], "points": {
        "base_dehors": [44.5, 43.2],
        "base_dedans": [44.5, 41.4],
    }})
    # à 0,5, la base de la tête vaut 2,75 mm de demi-largeur à cet endroit :
    # 1,4 mm tombe dedans, 3,2 mm tombe dehors. C'est CE couple qui pinne.
    assert p["points"]["base_dedans"][3] > 200, p["points"]
    assert p["points"]["base_dehors"][3] == 0, \
        "la base de la tête est plus large que 0,5 x sa longueur"
    # LE BOUT DE TRAIT NE SE PINNE PAS ICI, ET LE BANC LE DIT LUI-MÊME : son
    # `stroke()` est un ruban de quadrilatères qui n'a AUCUNE notion de cap
    # (c'est écrit dans son propre commentaire). Le chercher dans node aurait
    # été un contrôle qui ne mesure rien — une mutation `butt` -> `round` y
    # reste verte, vérifié. Il est pinné où il EXISTE : dans le banc Chrome,
    # sur le rastériseur du produit (voir
    # `test_une_fleche_et_un_cercle_TIENNENT_dans_un_vrai_navigateur`).
    q = _banc_plaque(tmp_path, {"slots": [
        dict(FLECHE_SLOT, arrow_end=False, head_mm=0.0)],
        "points": {"pointe": [49.6, 40.0]}})
    assert q["points"]["pointe"][3] > 200, q["points"]


def test_le_rendu_d_un_deck_qui_portait_null_CHANGE_et_c_est_ecrit(tmp_path):
    """L'AVEU ÉTAIT FAUX, ET C'EST LUI QU'ON CORRIGE — pas la correction.

    Mon commit annonçait « dix clés neuves, ZÉRO PIXEL BOUGÉ ». C'est vrai des
    dix clés ; c'est FAUX de la réparation de `num()` qui les accompagnait.
    MESURÉ par la revue et reproduit ici : un deck déjà enregistré qui porte
    `plate_alpha: null` rendait une plaque INVISIBLE avant (`Number(null)`
    valait 0) et rend une plaque PLEINE après (`float(None)` retombe sur le
    défaut, 1,0). Le painter reçoit les slots du document TELS QUELS —
    `normalize_deck` ne repasse pas les slots — donc la valeur atteint la
    toile. Idem pour `opacity: ""` : bloc invisible avant, visible après.

    LA CORRECTION EST BONNE : elle aligne l'écran sur le backend, qui rendait
    DÉJÀ 1,0, et c'est l'écran qui mentait. Ce qui devait changer, c'est la
    phrase — et ce test ÉPINGLE le nouveau comportement pour que personne ne
    le « répare » en croyant restaurer l'ancien."""
    slot = {"id": "rules", "text": "X", "align": "left", "valign": "top",
            "size_pt": 7.0, "min_pt": 7.0, "autofit": False, "wrap": False,
            "box": [10.0, 20.0, 30.0, 16.0], "plate_color": "#3050a0"}
    pts = {"milieu": [25.0, 32.0]}
    # `plate_alpha: null` = ABSENT, donc le DÉFAUT (1,0) : plaque pleine.
    nul = _banc_plaque(tmp_path, {"slots": [dict(slot, plate_alpha=None)],
                                  "points": pts})
    assert nul["points"]["milieu"] == [48, 80, 160, 255], nul["points"]
    assert TY.norm_slot({"plate_alpha": None})["plate_alpha"] == 1.0
    # ... et la chaîne vide se lit pareil des deux côtés
    vide = _banc_plaque(tmp_path, {"slots": [dict(slot, opacity="")],
                                   "points": pts})
    assert vide["points"]["milieu"][3] == 255, vide["points"]
    assert TY.norm_slot({"opacity": ""})["opacity"] == 100.0
    # LE TÉMOIN : un ZÉRO ÉCRIT reste un zéro. Ce qui change, c'est la lecture
    # de l'ABSENCE — pas celle d'une valeur posée.
    zero = _banc_plaque(tmp_path, {"slots": [dict(slot, plate_alpha=0)],
                                   "points": pts})
    assert zero["points"]["milieu"][3] == 0, zero["points"]
    assert TY.norm_slot({"plate_alpha": 0})["plate_alpha"] == 0.0


def test_le_compte_de_cles_des_modeles_suit_la_table():
    """`models.py` dit en toutes lettres combien de clés porte un slot de
    modèle. Le chiffre était resté à 39 alors que la table en porte 49 depuis
    les formes — la même ligne de prose que `frame.py` portait, corrigée là et
    oubliée ici. `models.py` n'appartient à personne cette ronde : c'est la
    PROSE seule qui bouge, pas une ligne de code."""
    import app.services.cards.models as MD
    py = pathlib.Path(MD.__file__).read_text(encoding="utf-8")
    n = len(TY.SLOT_DEFAULTS)
    assert f"les {n} clés de `SLOT_DEFAULTS`" in py, \
        f"models.py ne dit pas le compte réel ({n})"
    assert "les 39 clés" not in py, "le compte périmé est toujours là"
    # ... et la table est bien DÉRIVÉE, donc les clés neuves y sont déjà
    s = MD._slot("x", "X", [0, 0, 10, 5])
    assert set(s) == set(TY.SLOT_DEFAULTS), set(s) ^ set(TY.SLOT_DEFAULTS)


# ═════════════════════════════════════════════════════════════════════════════
# 16. LES OUTILS FIGMA (phase 5, T3 — décision D4)
# ═════════════════════════════════════════════════════════════════════════════
#
# CE QUE CETTE SECTION GARDE, ET POURQUOI ELLE COMMENCE PAR DES FONCTIONS
# PURES. Aligner, distribuer, égaliser et aimanter sont de l'ARITHMÉTIQUE sur
# des rectangles : leur vérité se pose en millimètres et se relit en
# millimètres, sans DOM, sans navigateur et sans opinion. Elles sont donc
# écrites comme des fonctions sans effet de bord, EXTRAITES du module et
# EXÉCUTÉES dans node contre des chiffres posés à la main. Le geste de l'écran,
# lui, ne fait que les appeler — c'est la seule façon de mesurer « le lot est
# aligné » autrement qu'en relisant sa propre intention.
#
# LE PIÈGE TRANSMIS PAR LA CLÔTURE T2, ET IL EST NOMMÉ ICI : le calque
# d'édition GONFLE la boîte d'une forme plate (plancher de saisie 12 px) alors
# que le DOCUMENT garde sa hauteur nulle. Un lasso ou un aimant qui lirait le
# DOM lirait donc la boîte gonflée : deux vérités pour un rectangle. Tout ce
# qui suit lit `s.box`, et un test le prouve en posant le lasso DANS la bande
# gonflée mais HORS de la boîte du document — il ne doit rien attraper.


def _pures_js(noms, appel: str) -> str:
    """Les fonctions PURES de `mod-type.js`, extraites et exécutées dans node.
    Rien n'est recopié : un test qui réécrirait la formule ne mesurerait que
    lui-même (la leçon B1)."""
    src = "".join(_fonction_js_type(n) for n in noms)
    return _node_type(src + appel)


# les trois rectangles de référence, posés à la main — les seuls chiffres de
# la section, et tous les résultats attendus en découlent par soustraction.
LOT3 = [[10.0, 20.0, 30.0, 8.0],
        [14.0, 40.0, 12.0, 6.0],
        [6.0, 60.0, 20.0, 4.0]]
# enveloppe : x de 6 à 40 (34 mm), y de 20 à 64 (44 mm)
ENV3 = [6.0, 20.0, 34.0, 44.0]


def test_l_enveloppe_d_un_lot_est_le_plus_petit_rectangle_qui_le_contient():
    """L'enveloppe est la base des six alignements : si elle est fausse, les
    six le sont ensemble et aucun ne le dit."""
    env = json.loads(_pures_js(
        ["enveloppe"], f"console.log(JSON.stringify(enveloppe({json.dumps(LOT3)})));"))
    assert env == ENV3, env
    # un lot VIDE n'a pas d'enveloppe — et ce n'est pas [0,0,0,0], qui serait un
    # rectangle au coin de coupe, donc une cible d'alignement inventée.
    vide = json.loads(_pures_js(["enveloppe"],
                                "console.log(JSON.stringify(enveloppe([])));"))
    assert vide is None, vide


def test_les_SIX_alignements_posent_les_millimetres_attendus():
    """Vérité connue, calculée à la main sur l'enveloppe [6, 20, 34, 44] :

      · gauche  -> x = 6 partout ;
      · droite  -> x = 40 - largeur : 10, 28, 20 ;
      · centreH -> x = 6 + (34 - largeur)/2 : 8, 17, 13 ;
      · haut    -> y = 20 partout ;
      · bas     -> y = 64 - hauteur : 56, 58, 60 ;
      · centreV -> y = 20 + (44 - hauteur)/2 : 38, 39, 40.

    ET CE QUI NE BOUGE PAS : un alignement horizontal ne touche JAMAIS y ni
    les tailles. Sans ce contrôle, une formule qui recentre aussi en vertical
    passerait — et déplacerait la moitié de la carte."""
    out = json.loads(_pures_js(
        ["enveloppe", "aligne"],
        "const L=" + json.dumps(LOT3) + ";"
        "const M=['left','hcenter','right','top','vcenter','bottom'];"
        "const o={};M.forEach((m)=>{o[m]=aligne(L,m);});"
        "console.log(JSON.stringify(o));"))
    assert [b[0] for b in out["left"]] == [6.0, 6.0, 6.0], out["left"]
    assert [b[0] for b in out["right"]] == [10.0, 28.0, 20.0], out["right"]
    assert [b[0] for b in out["hcenter"]] == [8.0, 17.0, 13.0], out["hcenter"]
    assert [b[1] for b in out["top"]] == [20.0, 20.0, 20.0], out["top"]
    assert [b[1] for b in out["bottom"]] == [56.0, 58.0, 60.0], out["bottom"]
    assert [b[1] for b in out["vcenter"]] == [38.0, 39.0, 40.0], out["vcenter"]
    for m in ("left", "hcenter", "right"):
        assert [b[1] for b in out[m]] == [20.0, 40.0, 60.0], (m, out[m])
    for m in ("top", "vcenter", "bottom"):
        assert [b[0] for b in out[m]] == [10.0, 14.0, 6.0], (m, out[m])
    for m in out:
        assert [b[2:] for b in out[m]] == [[30.0, 8.0], [12.0, 6.0], [20.0, 4.0]], m


def test_distribuer_pose_des_ESPACES_EGAUX_et_ne_bouge_pas_les_extremes():
    """« Espaces égaux » est la définition de Figma : ce sont les BLANCS entre
    les rectangles qui deviennent égaux, pas les positions — trois boîtes de
    largeurs différentes réparties « à pas constant » laisseraient des blancs
    inégaux, ce qui est justement le défaut qu'on vient corriger.

    Vérité connue : 0(10) / 20(10) / 100(10) — 30 mm d'objets dans 110 mm de
    portée, donc 80 mm de blanc pour 2 intervalles = 40 mm chacun, et les
    positions tombent sur 0 / 50 / 100."""
    h = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[0,0,10,5],[20,0,10,5],[100,0,10,5]],'h')));"))["boxes"]
    assert [b[0] for b in h] == [0.0, 50.0, 100.0], h
    assert [b[1] for b in h] == [0.0, 0.0, 0.0], "l'axe H a bougé Y"
    v = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[0,0,5,10],[0,20,5,10],[0,100,5,10]],'v')));"))["boxes"]
    assert [b[1] for b in v] == [0.0, 50.0, 100.0], v
    # DEUX BOÎTES N'ONT RIEN À DISTRIBUER : un seul blanc est déjà égal à
    # lui-même. Rien ne bouge — et surtout pas « les coller ».
    deux = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue([[0,0,10,5],[80,0,10,5]],'h')));"))
    assert deux["boxes"] == [[0.0, 0.0, 10.0, 5.0], [80.0, 0.0, 10.0, 5.0]], deux
    # ... et l'ORDRE D'ARRIVÉE ne décide de rien : c'est la POSITION qui range.
    melange = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[100,0,10,5],[0,0,10,5],[20,0,10,5]],'h')));"))["boxes"]
    assert [b[0] for b in melange] == [100.0, 0.0, 50.0], melange


def test_egaliser_prend_la_taille_du_PREMIER_SELECTIONNE():
    """Le patron Figma du « key object » : la référence est le premier
    sélectionné, pas la plus grande ni la moyenne — sans quoi égaliser deux
    fois de suite donnerait deux résultats."""
    r = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,10],[5,20,8,4],[3,40,12,6]],"
        "['rect','text','image'],'h')));"))
    assert r["ref"] == 10.0, r
    assert [b[3] for b in r["boxes"]] == [10.0, 10.0, 10.0], r["boxes"]
    assert r["ignores"] == [], r
    assert [b[2] for b in r["boxes"]] == [20.0, 8.0, 12.0], "la largeur a bougé"
    w = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,10],[5,20,8,4],[3,40,12,6]],"
        "['rect','text','image'],'w')));"))
    assert [b[2] for b in w["boxes"]] == [20.0, 20.0, 20.0], w["boxes"]


def test_une_LIGNE_est_EXCLUE_de_l_egalisation_de_sa_dimension_NULLE():
    """LA DÉCISION TRANSMISE PAR LA CLÔTURE T2, TRANCHÉE ICI. Une ligne
    horizontale est une boîte de HAUTEUR NULLE — c'est la règle de l'axe.
    Égaliser sa hauteur sur un lot ne la « redimensionne » pas : elle la rend
    DIAGONALE, parce que le trait va d'un coin de la boîte à l'autre. Ce n'est
    pas un redimensionnement, c'est un changement de nature.

    La règle tranchée : une ligne ou une flèche dont la dimension VISÉE est
    nulle est IGNORÉE, et l'écran le dit. Une ligne déjà oblique (hauteur non
    nulle), elle, s'égalise comme tout le monde — son angle est un choix de
    l'utilisateur, pas un axe."""
    r = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,10],[5,20,8,4],[3,40,30,0]],"
        "['rect','text','line'],'h')));"))
    assert r["ignores"] == [2], r
    assert r["boxes"][2] == [3.0, 40.0, 30.0, 0.0], r["boxes"]
    assert [b[3] for b in r["boxes"][:2]] == [10.0, 10.0], r["boxes"]
    # LE TÉMOIN : sur la LARGEUR, cette même ligne n'est pas dégénérée — elle
    # s'égalise. L'exclusion vise la dimension nulle, pas la nature « ligne ».
    w = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,10],[5,20,8,4],[3,40,30,0]],"
        "['rect','text','line'],'w')));"))
    assert w["ignores"] == [], w
    assert [b[2] for b in w["boxes"]] == [20.0, 20.0, 20.0], w["boxes"]
    # ... et une flèche OBLIQUE (hauteur 5) suit le lot : elle n'est pas plate.
    o = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,10],[3,40,30,5]],['rect','arrow'],'h')));"))
    assert o["ignores"] == [], o
    assert o["boxes"][1][3] == 10.0, o["boxes"]


def test_une_LIGNE_EN_REFERENCE_fait_REFUSER_l_egalisation_ENTIERE():
    """L'autre moitié de la même décision, et elle est pire : si la RÉFÉRENCE
    est la ligne plate, sa hauteur nulle s'appliquerait à tout le lot — le
    titre, l'encadré et l'illustration deviendraient invisibles d'un clic. Le
    lot n'est pas touché du tout, et le refus porte un nom."""
    r = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[3,40,30,0],[0,0,20,10]],['line','rect'],'h')));"))
    assert r["refuse"] == "reference", r
    assert r["boxes"] == [[3.0, 40.0, 30.0, 0.0], [0.0, 0.0, 20.0, 10.0]], r["boxes"]
    assert r["ignores"] == [], r


def test_l_aimant_colle_au_PLUS_PROCHE_et_seulement_SOUS_LE_SEUIL():
    """L'aimant objet-à-objet, en arithmétique pure. Boîte [10, 20, 30, 8] :
    ses candidats horizontaux sont 10 (bord gauche), 25 (centre) et 40 (bord
    droit), ses candidats verticaux 20, 24 et 28.

    Vérité connue : une cible à 9,7 attire le bord gauche de 0,3 mm ; une
    cible à 40,9 est à 0,9 mm du bord droit, donc HORS du seuil de 0,6 — elle
    ne fait rien. La boîte part à 9,7 et pas ailleurs."""
    r = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],"
        "{x:[{mm:9.7,de:'A'},{mm:40.9,de:'B'}],y:[{mm:20.5,de:'C'}]},0.6)));"))
    assert r["box"] == [9.7, 20.5, 30.0, 8.0], r["box"]
    assert r["hitX"] is True and r["hitY"] is True, r
    assert sorted((g["axe"], g["mm"], g["de"]) for g in r["lignes"]) == \
        [("x", 9.7, "A"), ("y", 20.5, "C")], r["lignes"]
    # LE SEUIL EST UNE FRONTIÈRE, PAS UNE INTENTION : 0,6 colle, 0,61 non.
    pile = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],"
        "{x:[{mm:10.6,de:'A'}],y:[]},0.6)));"))
    assert pile["box"][0] == 10.6 and pile["hitX"] is True, pile
    juste = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],"
        "{x:[{mm:10.61,de:'A'}],y:[]},0.6)));"))
    assert juste["box"][0] == 10.0 and juste["hitX"] is False, juste
    assert juste["lignes"] == [], juste
    # DEUX CIBLES DANS LE SEUIL : la plus proche gagne, pas la première lue.
    duel = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],"
        "{x:[{mm:10.2,de:'loin'},{mm:9.9,de:'pres'}],y:[]},0.6)));"))
    assert duel["box"][0] == 9.9, duel
    assert duel["lignes"][0]["de"] == "pres", duel["lignes"]


def test_l_aimant_colle_AUSSI_par_le_CENTRE_et_par_le_BORD_OPPOSE():
    """Trois prises par axe, et c'est ce qui fait la différence entre « caler
    à gauche » et « centrer sur » : une cible à 25,1 attrape le CENTRE de la
    boîte, donc son bord gauche part à 10,1 — la boîte se déplace de 0,1 mm,
    pas de 15."""
    c = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],"
        "{x:[{mm:25.1,de:'centre'}],y:[]},0.6)));"))
    assert c["box"][0] == 10.1, c["box"]
    assert c["lignes"][0]["mm"] == 25.1, c["lignes"]
    d = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],"
        "{x:[{mm:40.4,de:'droite'}],y:[]},0.6)));"))
    assert d["box"][0] == 10.4, d["box"]
    # AUCUNE CIBLE : la boîte ressort telle quelle, et rien n'est signalé.
    n = json.loads(_pures_js(
        ["aimante"],
        "console.log(JSON.stringify(aimante([10,20,30,8],{x:[],y:[]},0.6)));"))
    assert n["box"] == [10.0, 20.0, 30.0, 8.0], n
    assert n["hitX"] is False and n["hitY"] is False and n["lignes"] == [], n


def test_le_seuil_d_aimantation_est_PLUS_GRAND_que_le_pas_de_grille():
    """UN SEUIL SOUS LE PAS DE GRILLE NE SERAIT JAMAIS ATTEIGNABLE. Le glisser
    arrondit déjà à 0,25 mm : un aimant à 0,2 mm ne se déclencherait que sur
    les cibles elles-mêmes multiples de la grille, c'est-à-dire presque
    jamais. Le seuil est donc écrit, et il est plus grand."""
    src = _js()
    m = re.search(r"const GUIDE_MM = ([\d.]+)", src)
    assert m, "le seuil d'aimantation n'est pas nommé"
    seuil = float(m.group(1))
    g = re.search(r"SNAP_MM = ([\d.]+)", src)
    assert seuil > float(g.group(1)), (seuil, g.group(1))


# ── 16.1 LA SÉLECTION MULTIPLE — `doc.type.sel` devient une LISTE ────────────
#
# LE CONTRAT NOUVEAU, ÉCRIT ICI PARCE QU'IL EST LE SEUL À CHANGER DE FORME :
#
#   · `doc.type.sel` est désormais une LISTE d'identifiants, dans l'ordre où
#     l'utilisateur les a pris. Le PREMIER est le « key object » du patron
#     Figma : c'est lui qui donne sa taille à « égaliser », et c'est lui que
#     l'ancien `selId()` continue de rendre.
#   · LA MIGRATION EST DOUCE, DANS LE SENS DE LA LECTURE : une chaîne est lue
#     comme une liste d'un élément, la chaîne vide comme une liste vide. Un
#     deck enregistré avant cette tâche, et le document que `models.py` fabrique
#     (`"sel": slots[0]["id"]`, une chaîne), s'ouvrent donc sans conversion.
#   · L'ÉCRITURE, ELLE, EST TOUJOURS UNE LISTE : une seule forme sort d'ici.
#   · Les identifiants MORTS sont filtrés à la lecture — une sélection qui
#     survit à la suppression de son bloc réglerait un fantôme.
#   · LE BACKEND NE LIT JAMAIS `sel` : `type.py` ne le connaît pas, `models.py`
#     ne fait que l'écrire une fois. Aucun miroir n'est donc à tenir.

_GEO3 = CT.geom("poker_eu", 300)


def _clx(mm: float) -> float:
    """Millimètres depuis le coin de coupe -> pixels client du banc. Le banc
    pose la scène à l'échelle 1 (un pixel d'écran = un pixel de toile), donc la
    conversion est celle du fichier livré, sans facteur caché."""
    return _GEO3.bleed_off_px[0] + mm / 25.4 * 300


def _cly(mm: float) -> float:
    return _GEO3.bleed_off_px[1] + mm / 25.4 * 300


def _lot2(**kw) -> list:
    """Deux blocs de texte empilés, boîtes rondes en millimètres."""
    a = TY.norm_slot(dict({"id": "a", "label": "A", "box": [10.0, 20.0, 30.0, 8.0],
                           "text": "A"}, **kw))
    b = TY.norm_slot({"id": "b", "label": "B", "box": [10.0, 40.0, 30.0, 8.0],
                      "text": "B"})
    return [a, b]


def test_la_selection_est_une_LISTE_et_relit_encore_une_CHAINE(tmp_path):
    """Les deux moitiés du contrat, mesurées ensemble : ce qui SORT est
    toujours une liste, ce qui ENTRE peut être l'ancienne chaîne."""
    # un document NEUF, sélection vide : un clic écrit une LISTE d'un élément
    d = _banc_verrou(tmp_path, {"state": {"slots": _lot2(), "sel": ""},
                                "actes": [{"t": "down", "id": "b"}, {"t": "up"}]})
    assert d["sel"] == ["b"], d["sel"]
    # un document ANCIEN, `sel` en chaîne : il est lu, et Maj+clic l'étend
    v = _banc_verrou(tmp_path, {"state": {"slots": _lot2(), "sel": "a"},
                                "actes": [{"t": "down", "id": "b", "maj": True}]})
    assert v["sel"] == ["a", "b"], v["sel"]
    # ... et le document que `models.py` fabrique porte EXACTEMENT cette forme
    import app.services.cards.models as MD
    py = pathlib.Path(MD.__file__).read_text(encoding="utf-8")
    assert '"sel": (slots[0]["id"] if slots else "")' in py, \
        "models.py n'écrit plus la chaîne que la lecture tolère"


def test_MAJ_clic_ajoute_puis_RETIRE_du_lot(tmp_path):
    """Le patron Figma : Maj bascule. Deux fois sur le même bloc et il sort du
    lot — sans quoi on ne pourrait retirer qu'en repartant de zéro."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ""},
        "actes": [{"t": "down", "id": "a"}, {"t": "up"},
                  {"t": "down", "id": "b", "maj": True},
                  {"t": "down", "id": "b", "maj": True}]},
        mutations=[MUT_UNDO])
    bas = [t for t in d["traces"] if t["acte"] == "down"]
    assert [t["sel"] for t in bas] == [["a"], ["a", "b"], ["a"]], d["traces"]
    # MAJ+CLIC NE DÉMARRE PAS DE GLISSER : il désigne, point. Un geste qui
    # commencerait ici déplacerait le lot au premier tremblement de main.
    # (le clic NU, lui, en démarre un : c'est la moitié témoin de la mesure)
    assert [t["moves"] for t in bas] == [1, 0, 0], d["traces"]
    # ... et il ne pose AUCUNE entrée d'annulation : désigner n'est pas éditer.
    assert [t["undo"] for t in bas] == [1, 0, 0], d["traces"]


def test_un_clic_NU_sur_un_bloc_DEJA_du_lot_garde_le_lot(tmp_path):
    """Le geste qui rend la multi-sélection utilisable : reprendre le lot à la
    main. Un clic nu sur un bloc HORS du lot le réduit à lui seul (patron
    Figma) ; sur un bloc DÉJÀ dedans, il ne le réduit pas — sinon tout glisser
    de groupe commencerait par le détruire."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ""},
        "actes": [{"t": "down", "id": "a"},
                  {"t": "down", "id": "b", "maj": True},
                  {"t": "down", "id": "a"}]})
    assert d["traces"][2]["sel"] == ["a", "b"], d["traces"]
    r = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ["a", "b"]},
        "actes": [{"t": "down", "id": "b"}, {"t": "up"}]})
    assert r["sel"] == ["a", "b"], r["sel"]
    # un bloc HORS du lot, lui, le remplace
    s = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2() + [TY.norm_slot(
            {"id": "c", "label": "C", "box": [10.0, 60.0, 30.0, 8.0]})],
            "sel": ["a", "b"]},
        "actes": [{"t": "down", "id": "c"}, {"t": "up"}]})
    assert s["sel"] == ["c"], s["sel"]


def test_ECHAP_vide_la_selection(tmp_path):
    """Échap ferme les menus (acquis de la phase 4) ET vide le lot. Une
    sélection qu'on ne sait pas relâcher se traîne d'un geste à l'autre."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ["a", "b"]},
        "actes": [{"t": "key", "k": "Escape"}]})
    assert d["sel"] == [], d["sel"]
    # ... et Échap sur une sélection DÉJÀ vide n'écrit rien du tout
    v = _banc_verrou(tmp_path, {"state": {"slots": _lot2(), "sel": []},
                                "actes": [{"t": "key", "k": "Escape"}]})
    n = _banc_verrou(tmp_path, {"state": {"slots": _lot2(), "sel": []},
                                "actes": []})
    assert v["patchs"] == n["patchs"], (v["patchs"], n["patchs"])


def _lot_trait() -> list:
    """Une LIGNE PLATE (hauteur nulle) et un bloc de texte plus bas. La ligne
    est le piège transmis par la clôture T2 : son calque d'édition est gonflé
    à 12 px, son document ne l'est pas."""
    return [TY.norm_slot({"id": "trait", "kind": "line", "label": "Trait",
                          "box": [10.0, 40.0, 40.0, 0.0],
                          "stroke": "#20c0ff", "stroke_mm": 0.5}),
            TY.norm_slot({"id": "titre", "label": "Titre",
                          "box": [10.0, 60.0, 40.0, 8.0], "text": "T"})]


def test_le_LASSO_prend_ce_qu_il_TOUCHE(tmp_path):
    """Le lasso de Figma prend ce qu'il TOUCHE (intersection), pas seulement ce
    qu'il contient : sur une carte de 63 x 88 mm, exiger l'inclusion complète
    obligerait à partir hors de la carte pour attraper un titre pleine
    largeur."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_trait(), "sel": []},
        "actes": [{"t": "lasso", "x0": _clx(5.0), "y0": _cly(39.5),
                   "x1": _clx(55.0), "y1": _cly(40.5)}]})
    assert d["sel"] == ["trait"], d["sel"]
    # le lasso qui prend les DEUX
    b = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_trait(), "sel": []},
        "actes": [{"t": "lasso", "x0": _clx(5.0), "y0": _cly(30.0),
                   "x1": _clx(55.0), "y1": _cly(70.0)}]})
    assert b["sel"] == ["trait", "titre"], b["sel"]
    # MAJ + LASSO AJOUTE au lot au lieu de le remplacer
    m = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_trait(), "sel": ["titre"]},
        "actes": [{"t": "lasso", "x0": _clx(5.0), "y0": _cly(39.5),
                   "x1": _clx(55.0), "y1": _cly(40.5), "maj": True}]})
    assert m["sel"] == ["titre", "trait"], m["sel"]
    # UN CLIC NU DANS LE VIDE VIDE LE LOT — et ne pose aucune annulation
    v = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_trait(), "sel": ["titre", "trait"]},
        "actes": [{"t": "lasso", "x0": _clx(30.0), "y0": _cly(20.0),
                   "x1": _clx(30.0), "y1": _cly(20.0)}]},
        mutations=[MUT_UNDO])
    assert v["sel"] == [], v["sel"]
    assert v["traces"][0]["undo"] == 0, v["traces"]


# LA MUTATION QUI SÉPARE LES DEUX VÉRITÉS : elle fait lire au lasso la boîte
# GONFLÉE du calque d'édition, exactement comme le ferait un lasso branché sur
# le DOM. Sans elle, « le lasso lit le document » serait une phrase de
# commentaire — le test voisin passerait aussi bien sur le code fautif.
MUT_LASSO_DOM = (
    "    const b = s.box;   /* CF-LASSO-DOC */",
    "    const b = (isShape(s) && s.box[3] === 0)\r\n"
    "      ? [s.box[0], s.box[1] - 0.508, s.box[2], 1.016] : s.box;")


def test_le_LASSO_lit_la_boite_du_DOCUMENT_et_JAMAIS_le_calque(tmp_path):
    """LE PIÈGE TRANSMIS PAR LA CLÔTURE T2, ÉPROUVÉ. Le calque d'édition donne
    à une ligne plate un plancher de saisie de 12 px — soit ±0,508 mm autour
    de sa position à 300 DPI. Sa boîte AFFICHÉE couvre donc 39,49 à 40,51 mm ;
    sa boîte de DOCUMENT est le segment y = 40, épaisseur nulle.

    Le lasso est posé entre 40,25 et 40,45 mm : DANS la bande gonflée, HORS du
    document. Il ne doit RIEN attraper — et la mutation, qui fait lire la boîte
    gonflée, doit l'attraper. Deux vérités pour un rectangle, séparées."""
    acte = [{"t": "lasso", "x0": _clx(5.0), "y0": _cly(40.25),
             "x1": _clx(55.0), "y1": _cly(40.45)}]
    d = _banc_verrou(tmp_path, {"state": {"slots": _lot_trait(), "sel": []},
                                "actes": acte})
    assert d["sel"] == [], \
        "le lasso a attrapé une ligne qui n'est pas là : il lit le calque"
    mut = _banc_verrou(tmp_path, {"state": {"slots": _lot_trait(), "sel": []},
                                  "actes": acte}, mutations=[MUT_LASSO_DOM])
    assert mut["sel"] == ["trait"], \
        "la mutation ne change rien : le test ne sépare pas les deux boîtes"
    # ... et le DOCUMENT n'a pas bougé d'un millimètre dans les deux cas
    assert d["slots"][0]["box"] == [10.0, 40.0, 40.0, 0.0], d["slots"][0]


def test_le_lot_GLISSE_ENSEMBLE_en_UN_SEUL_pas_d_annulation(tmp_path):
    """Le contrat d'annulation de la pièce, tenu sur un geste de groupe : UN
    glisser = UNE entrée, quel que soit le nombre de blocs. 150 px d'écran à
    l'échelle 1 valent exactement 12,7 mm — les deux boîtes partent de 10 et
    arrivent à 22,7."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ["a", "b"]},
        "actes": [{"t": "down", "id": "a", "x": 400, "y": 400},
                  {"t": "move", "x": 550, "y": 400},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    boxes = {s["id"]: s["box"] for s in d["slots"]}
    assert boxes["a"] == [22.7, 20.0, 30.0, 8.0], boxes
    assert boxes["b"] == [22.7, 40.0, 30.0, 8.0], boxes
    assert d["undo"] == 1, d["undo"]
    # LE TÉMOIN : un bloc HORS du lot ne bouge pas.
    t = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2() + [TY.norm_slot(
            {"id": "c", "label": "C", "box": [10.0, 60.0, 30.0, 8.0]})],
            "sel": ["a"]},
        "actes": [{"t": "down", "id": "a", "x": 400, "y": 400},
                  {"t": "move", "x": 550, "y": 400},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    bt = {s["id"]: s["box"] for s in t["slots"]}
    assert bt["a"][0] == 22.7 and bt["b"][0] == 10.0 and bt["c"][0] == 10.0, bt
    assert t["undo"] == 1, t["undo"]


def test_un_bloc_VERROUILLE_du_lot_ne_suit_PAS_le_glisser(tmp_path):
    """Le verrou vaut aussi en lot — sinon il suffirait d'attraper un voisin
    pour déplacer un bloc protégé, ce qui viderait le cadenas de son sens."""
    lot = _lot2()
    lot[1]["lock"] = True
    d = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["a", "b"]},
        "actes": [{"t": "down", "id": "a", "x": 400, "y": 400},
                  {"t": "move", "x": 550, "y": 400},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    boxes = {s["id"]: s["box"] for s in d["slots"]}
    assert boxes["a"] == [22.7, 20.0, 30.0, 8.0], boxes
    assert boxes["b"] == [10.0, 40.0, 30.0, 8.0], "le bloc verrouillé a suivi"
    assert any("verrouill" in t["m"] for t in d["toasts"]), d["toasts"]


def test_UN_SEUL_lecteur_de_type_sel_dans_toute_la_piece():
    """LA MIGRATION SE VÉRIFIE PAR L'ABSENCE DE SECOND LECTEUR. Tant qu'un seul
    endroit lit `type.sel`, la tolérance (chaîne ou liste) et le filtrage des
    identifiants morts sont vrais partout. Un second `CF.get("type.sel"` serait
    un endroit où l'ancienne forme reviendrait."""
    src = _js()
    assert src.count('CF.get("type.sel"') == 1, \
        "plus d'un lecteur brut de `type.sel` : la migration a un trou"
    lec = _js_fn(src, "selIds")
    assert 'CF.get("type.sel"' in lec, "le lecteur unique n'est pas `selIds`"
    # et `selId()` reste le PREMIER du lot : c'est lui que les anciens
    # lecteurs (panneau, calque, liste) continuent d'appeler
    assert "const selId = () => selIds()[0]" in src, \
        "`selId` n'est plus dérivé de la liste"


# ── 16.2 LA BARRE CONTEXTUELLE — aligner, distribuer, égaliser ──────────────
#
# Les fonctions pures ci-dessus SAVENT ; cette section vérifie qu'un bouton du
# panneau les APPELLE, sur les bonnes boîtes, et qu'un Ctrl+Z défait le geste
# entier. C'est la moitié qu'aucune vérité arithmétique ne couvre : une barre
# parfaitement calculée mais branchée sur le mauvais lot serait verte partout.

def _lot3() -> list:
    """Trois blocs aux boîtes de LOT3 — les mêmes chiffres que les fonctions
    pures, pour que le résultat attendu se relise sans recalcul."""
    return [TY.norm_slot({"id": "un", "label": "Un", "box": LOT3[0], "text": "1"}),
            TY.norm_slot({"id": "deux", "label": "Deux", "box": LOT3[1], "text": "2"}),
            TY.norm_slot({"id": "trois", "label": "Trois", "box": LOT3[2], "text": "3"})]


def test_la_barre_n_apparait_QU_A_PARTIR_DE_DEUX_blocs(tmp_path):
    """« Aligner » sur un bloc seul n'a pas de sens : l'enveloppe de la
    sélection EST sa boîte, donc les six boutons ne bougeraient rien. Une barre
    de dix commandes inertes est exactement ce que cette pièce refuse."""
    un = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un"]}})
    assert "cf-type-abar" not in un["insp"], "la barre s'affiche sur un bloc seul"
    deux = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un", "deux"]}})
    assert "cf-type-abar" in deux["insp"], "la barre manque à deux blocs"
    assert "2 blocs" in deux["insp"], deux["insp"][:400]


def test_ALIGNER_A_GAUCHE_pose_les_millimetres_de_la_fonction_pure(tmp_path):
    """Le bouton appelle `aligne` sur les boîtes du LOT — et sur elles seules.
    Vérité connue (enveloppe [6, 20, 34, 44]) : les trois bords gauches
    tombent à 6,0."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    assert d["traces"][0]["cable"], d["traces"]
    assert [s["box"][0] for s in d["slots"]] == [6.0, 6.0, 6.0], d["slots"]
    # ... et RIEN d'autre n'a bougé : ni les Y, ni les tailles
    assert [s["box"][1] for s in d["slots"]] == [20.0, 40.0, 60.0], d["slots"]
    # UN SEUL PAS D'ANNULATION POUR TROIS BOÎTES — le contrat de la pièce
    assert d["traces"][0]["undo"] == 1, d["traces"]
    assert d["traces"][0]["patchs"] == 1, d["traces"]
    # LE TÉMOIN : hors du lot, rien ne bouge — et l'enveloppe change avec le
    # lot. Sans « trois », elle commence à 10 (et non 6), donc les deux
    # premiers restent à 10 et le troisième garde son 6.
    t = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    assert [s["box"][0] for s in t["slots"]] == [10.0, 10.0, 6.0], t["slots"]


def test_ALIGNER_sur_DEUX_blocs_prend_LEUR_enveloppe(tmp_path):
    """Le témoin du test précédent, mesuré pour lui-même : l'enveloppe de
    « un » et « deux » commence à 10 (et non 6, qui est le bord de « trois »)."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["un"][0] == 10.0 and par["deux"][0] == 10.0, par
    assert par["trois"][0] == 6.0, "un bloc hors du lot a été déplacé"


def test_DISTRIBUER_appelle_la_fonction_pure_sur_le_LOT(tmp_path):
    """Trois boîtes verticales de LOT3 : distribuées, elles tombent à
    20 / 41 / 60 — le calcul de la fonction pure, joué par le bouton."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "distv"}]},
        mutations=[MUT_UNDO])
    assert [s["box"][1] for s in d["slots"]] == [20.0, 41.0, 60.0], d["slots"]
    assert d["traces"][0]["undo"] == 1, d["traces"]
    # DEUX BLOCS : rien à distribuer, et l'écran le DIT au lieu de ne rien faire
    r = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux"]},
        "actes": [{"t": "barre", "v": "distv"}]},
        mutations=[MUT_UNDO])
    assert r["traces"][0]["undo"] == 0, r["traces"]
    assert any("trois" in t["m"] for t in r["toasts"]), r["toasts"]


def _lot_avec_ligne() -> list:
    return [TY.norm_slot({"id": "un", "label": "Un", "box": [0.0, 0.0, 20.0, 10.0],
                          "text": "1"}),
            TY.norm_slot({"id": "deux", "label": "Deux", "box": [5.0, 20.0, 8.0, 4.0],
                          "text": "2"}),
            TY.norm_slot({"id": "trait", "kind": "line", "label": "Trait",
                          "box": [3.0, 40.0, 30.0, 0.0],
                          "stroke": "#20c0ff", "stroke_mm": 0.5})]


def test_EGALISER_LA_HAUTEUR_ignore_la_ligne_ET_LE_DIT(tmp_path):
    """LA DÉCISION TRANSMISE, VUE DEPUIS L'ÉCRAN. La ligne garde sa hauteur
    nulle, les deux autres prennent celle du PREMIER sélectionné (10 mm) — et
    le toast nomme l'exclusion avec sa raison. Un refus muet ferait croire à
    une commande cassée."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_avec_ligne(), "sel": ["un", "deux", "trait"]},
        "actes": [{"t": "barre", "v": "eqh"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["un"][3] == 10.0 and par["deux"][3] == 10.0, par
    assert par["trait"][3] == 0.0, "la ligne est devenue diagonale"
    assert d["traces"][0]["undo"] == 1, d["traces"]
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "1 ligne" in msg and "diagonale" in msg, d["toasts"]
    # ... et sur la LARGEUR, la même ligne suit le lot : rien n'est ignoré
    w = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_avec_ligne(), "sel": ["un", "deux", "trait"]},
        "actes": [{"t": "barre", "v": "eqw"}]},
        mutations=[MUT_UNDO])
    assert [s["box"][2] for s in w["slots"]] == [20.0, 20.0, 20.0], w["slots"]
    assert all("diagonale" not in t["m"] for t in w["toasts"]), w["toasts"]


def test_EGALISER_SUR_UNE_LIGNE_EN_REFERENCE_refuse_ET_LE_DIT(tmp_path):
    """Le pire cas : la ligne est le premier sélectionné. Sa hauteur nulle
    aplatirait tout le lot d'un clic. Rien ne bouge, rien ne s'annule, et la
    phrase donne le remède (désigner un autre bloc en premier)."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_avec_ligne(), "sel": ["trait", "un", "deux"]},
        "actes": [{"t": "barre", "v": "eqh"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["un"][3] == 10.0 and par["deux"][3] == 4.0, "le lot a été aplati"
    assert d["traces"][0]["undo"] == 0 and d["traces"][0]["patchs"] == 0, d["traces"]
    msg = " ".join(t["m"] for t in d["toasts"])
    # LA PHRASE A CHANGÉ À LA RONDE (R1) ET C'EST VOULU : le refus ne parle
    # plus de « diagonale », parce que la RAISON du refus n'est pas là. Ce qui
    # refuse, c'est la dimension nulle de la RÉFÉRENCE — elle aplatirait tout
    # le lot, et c'est vrai d'un titre plat comme d'une ligne. La diagonale
    # reste le motif de l'autre branche (une ligne MEMBRE, ignorée).
    assert "référence" in msg and "hauteur nulle" in msg, d["toasts"]
    assert "« Trait »" in msg, "le refus ne nomme pas le bloc en cause"


# ── 16.3 LES RÉGLAGES COMMUNS, ÉDITÉS EN LOT ────────────────────────────────

def test_le_panneau_de_LOT_montre_MIXTE_quand_les_valeurs_different(tmp_path):
    """Le patron Figma : une valeur commune s'affiche, des valeurs différentes
    s'affichent « mixte ». Sans cette distinction, le panneau d'un lot montre
    la valeur du premier et l'utilisateur croit que c'est celle de tous."""
    lot = _lot3()
    lot[1]["side"] = "back"
    d = _banc_verrou(tmp_path, {"state": {"slots": lot, "sel": ["un", "deux"]}})
    assert "mixte" in d["insp"], d["insp"][:800]
    # ... et quand elles sont d'accord, la valeur commune est ACTIVE
    m = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un", "deux"]}})
    assert 'data-v="front" title="recto seul"' in m["insp"].replace(
        'class="seg-b active"', 'class="seg-b active"'), "le segment commun manque"
    assert 'seg-b active" type="button" data-v="front"' in m["insp"], m["insp"][:900]


def test_un_reglage_COMMUN_se_pose_sur_TOUT_le_lot_en_UN_pas(tmp_path):
    """La face, choisie une fois pour trois blocs. Un patch, une annulation."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "trois"]},
        "actes": [{"t": "lot", "seg": True, "k": "side", "v": "back"}]},
        mutations=[MUT_UNDO])
    assert d["traces"][0]["cable"], d["traces"]
    par = {s["id"]: s["side"] for s in d["slots"]}
    assert par == {"un": "back", "deux": "front", "trois": "back"}, par
    assert d["traces"][0]["undo"] == 1 and d["traces"][0]["patchs"] == 1, d["traces"]


def test_les_BOUTS_FLECHES_s_appliquent_AU_LOT_et_les_autres_IGNORENT(tmp_path):
    """LA DÉCISION TRANSMISE PAR LA CLÔTURE T2 : oui, `arrow_start` et
    `arrow_end` s'éditent en lot. Les natures qui n'ont pas de bout fléché
    (texte, image, rectangle, ellipse) ne sont PAS touchées — et l'écran dit
    combien de blocs la commande vise réellement, avant le clic."""
    lot = [TY.norm_slot({"id": "f1", "kind": "arrow", "label": "F1",
                         "box": [0.0, 0.0, 30.0, 0.0], "stroke": "#fff",
                         "stroke_mm": 0.5}),
           TY.norm_slot({"id": "f2", "kind": "arrow", "label": "F2",
                         "box": [0.0, 10.0, 30.0, 0.0], "stroke": "#fff",
                         "stroke_mm": 0.5}),
           TY.norm_slot({"id": "txt", "label": "Texte", "box": [0.0, 20.0, 30.0, 6.0],
                         "text": "x"})]
    ids = ["f1", "f2", "txt"]
    d = _banc_verrou(tmp_path, {"state": {"slots": lot, "sel": ids}})
    # l'écran annonce la portée AVANT le clic : 2 flèches sur 3 blocs
    assert "2 flèche" in d["insp"], d["insp"][:1200]
    r = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ids},
        "actes": [{"t": "lot", "k": "arrow_start"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s for s in r["slots"]}
    assert par["f1"]["arrow_start"] is True and par["f2"]["arrow_start"] is True, par
    # le TÉMOIN : le bloc de texte a bien la clé (elle est dans la table) et
    # elle n'a PAS bougé — la commande l'a ignoré, elle ne l'a pas écrasé.
    assert par["txt"]["arrow_start"] is False, par["txt"]
    assert r["traces"][0]["undo"] == 1, r["traces"]
    # ... et un lot SANS aucune flèche refuse et le dit
    sans = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux"]},
        "actes": [{"t": "lot", "k": "arrow_start"}]},
        mutations=[MUT_UNDO])
    assert sans["traces"][0]["undo"] == 0, sans["traces"]
    assert any("flèche" in t["m"] for t in sans["toasts"]), sans["toasts"]


# ── 16.4 LES GESTES DE PROFONDEUR — UNE SEULE MÉCANIQUE D'ORDRE ─────────────
#
# L'ORDRE DE PEINTURE EST CELUI DU TABLEAU `doc.type.slots` : le rang 0 se
# peint EN PREMIER (donc au fond), le dernier se peint EN DERNIER (donc
# devant). C'est déjà ce que déplacent les deux flèches de rangée. Les gestes
# de canvas s'y branchent par la MÊME fonction : deux vérités d'ordre, c'est
# une liste et une carte qui se contredisent au premier export.

def test_l_ordre_APRES_un_geste_de_profondeur_a_une_verite_connue():
    """La fonction pure, jouée dans node. Quatre gestes, un lot, et le cas du
    BORD : au bout de la pile, un geste ne rend RIEN — pas un ordre identique.
    Un patch qui ne change rien serait un Ctrl+Z qui ne défait rien."""
    out = json.loads(_pures_js(
        ["ordreApres"],
        "const I=['a','b','c','d'];const o={};"
        "[['b','avant'],['b','arriere'],['b','tout-avant'],['b','tout-arriere'],"
        "['a','arriere'],['d','avant']].forEach((q)=>{"
        "o[q[0]+':'+q[1]]=ordreApres(I,[q[0]],q[1]);});"
        "o['lot:tout-avant']=ordreApres(I,['a','c'],'tout-avant');"
        "o['lot:avant']=ordreApres(I,['a','b'],'avant');"
        "console.log(JSON.stringify(o));"))
    assert out["b:avant"] == ["a", "c", "b", "d"], out
    assert out["b:arriere"] == ["b", "a", "c", "d"], out
    assert out["b:tout-avant"] == ["a", "c", "d", "b"], out
    assert out["b:tout-arriere"] == ["b", "a", "c", "d"], out
    assert out["a:arriere"] is None, out
    assert out["d:avant"] is None, out
    # UN LOT SE DÉPLACE EN BLOC, ordre relatif conservé
    assert out["lot:tout-avant"] == ["b", "d", "a", "c"], out
    assert out["lot:avant"] == ["c", "a", "b", "d"], out


def test_les_quatre_gestes_de_profondeur_reordonnent_ET_UNE_ANNULATION(tmp_path):
    """Les boutons, joués. Et le bord ne fait RIEN — ni patch, ni annulation."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "barre", "cl": "cf-type-z", "dk": "z", "v": "avant"}]},
        mutations=[MUT_UNDO])
    assert _ids(d) == ["deux", "un", "trois"], d["slots"]
    assert d["traces"][0]["undo"] == 1 and d["traces"][0]["patchs"] == 1, d["traces"]
    t = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "barre", "cl": "cf-type-z", "dk": "z", "v": "tout-avant"}]},
        mutations=[MUT_UNDO])
    assert _ids(t) == ["deux", "trois", "un"], t["slots"]
    b = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "barre", "cl": "cf-type-z", "dk": "z", "v": "arriere"}]},
        mutations=[MUT_UNDO])
    assert _ids(b) == ["un", "deux", "trois"], b["slots"]
    assert b["traces"][0]["patchs"] == 0 and b["traces"][0]["undo"] == 0, b["traces"]
    # LA SÉLECTION SURVIT AU GESTE : on continue de régler le même bloc
    assert d["sel"] == ["un"], d["sel"]


def test_les_fleches_de_RANGEE_et_les_gestes_de_CANVAS_partagent_la_mecanique():
    """« Les gestes appellent la MÊME mécanique, pas une seconde vérité
    d'ordre. » Mesuré à la source : `moveSlot` (la flèche de rangée) et le
    bouton de profondeur passent tous deux par `zApplique`, qui est le seul
    appelant d'`ordreApres`."""
    src = _js()
    mv = _js_fn(src, "moveSlot")
    assert "zApplique(" in mv, "la flèche de rangée a gardé son propre calcul"
    assert "splice" not in mv, "la flèche de rangée réordonne encore elle-même"
    corps = _js_fn(src, "zApplique")
    assert "ordreApres(" in corps, "zApplique n'appelle pas la fonction d'ordre"
    assert src.count("ordreApres(") == 2, \
        "`ordreApres` a plus d'un appelant : il y a une seconde vérité d'ordre"


# ── 16.5 LA ROTATION À LA POIGNÉE ───────────────────────────────────────────

def test_la_poignee_de_ROTATION_est_servie_en_SOLO_et_GRISEE_en_LOT(tmp_path):
    """Elle reste VISIBLE en lot — une commande absente se cherche, une
    commande grisée s'explique — et son infobulle dit la raison : chacun
    tournerait sur SON centre, donc le lot se disloquerait."""
    solo = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un"]}})
    assert 'class="cf-type-rot"' in solo["ov"], solo["ov"][:600]
    lot = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un", "deux"]}})
    assert 'class="cf-type-rot off"' in lot["ov"], lot["ov"][:900]
    assert "disloquerait" in lot["ov"], lot["ov"][:900]
    # ... et les poignées de TAILLE ne sont pas servies au lot (géométrie de
    # groupe : ce n'est pas de cette phase, et huit prises qui ne retaillent
    # qu'une boîte sur n seraient un geste qui ment)
    assert "cf-type-hh" in solo["ov"] and "cf-type-hh" not in lot["ov"], lot["ov"][:900]


def test_la_ROTATION_tourne_le_bloc_et_MAJ_cale_sur_QUINZE_degres(tmp_path):
    """Vérité connue : la boîte « un » couvre 10..40 x 20..28 mm, son centre est
    donc à (25, 24) mm, soit (330,5 ; 318,9) px d'écran à l'échelle 1. On
    appuie PLEIN EST du centre (angle 0) et on relâche PLEIN SUD (angle +90°) :
    la valeur part de 0 et arrive à 90."""
    cx, cy = _clx(25.0), _cly(24.0)
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "down", "id": "un", "h": "rot", "x": cx + 100, "y": cy},
                  {"t": "move", "x": cx, "y": cy + 100},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s for s in d["slots"]}
    assert abs(par["un"]["rotate"] - 90.0) < 0.001, par["un"]["rotate"]
    assert d["undo"] == 1, d["undo"]
    # ... et la BOÎTE n'a pas bougé : une rotation n'est pas un déplacement
    assert par["un"]["box"] == LOT3[0], par["un"]["box"]
    # MAJ CALE SUR 15° : 40° de mouvement réel tombent sur 45
    m = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "down", "id": "un", "h": "rot", "x": cx + 100, "y": cy},
                  {"t": "move", "x": cx + 76.6, "y": cy + 64.3, "maj": True},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    pm = {s["id"]: s for s in m["slots"]}
    assert pm["un"]["rotate"] == 45.0, pm["un"]["rotate"]


def test_la_ROTATION_est_REFUSEE_en_lot_et_le_refus_se_DIT(tmp_path):
    """Le geste ne démarre pas (aucun pointermove branché) et la phrase donne
    le remède. Un curseur qui ne fait rien se lit comme une panne."""
    cx, cy = _clx(25.0), _cly(24.0)
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux"]},
        "actes": [{"t": "down", "id": "un", "h": "rot", "x": cx + 100, "y": cy}]},
        mutations=[MUT_UNDO])
    assert d["traces"][0]["moves"] == 0, d["traces"]
    assert d["traces"][0]["undo"] == 0, d["traces"]
    assert any("disloquerait" in t["m"] for t in d["toasts"]), d["toasts"]


# ── 16.6 LES GUIDES OBJET-À-OBJET ───────────────────────────────────────────
#
# TROIS RÉGIMES, ET IL FAUT LES TROIS POUR QUE LA MESURE VEUILLE DIRE QUELQUE
# CHOSE : l'aimant prend (la boîte tombe sur le millimètre EXACT du voisin), la
# grille reprend (rien à proximité : 0,25 mm comme avant), Alt débraye les deux
# (main levée). Un test qui ne montrerait que le premier ne dirait pas si
# l'aimant a remplacé la grille ou s'il l'a simplement doublée.
#
# Les déplacements sont donnés en PIXELS D'ÉCRAN (le banc est à l'échelle 1),
# et les millimètres attendus s'en déduisent par 25,4/300 — la conversion du
# fichier livré, pas une constante de test.

def _voisin(x: float) -> list:
    """Un bloc mobile à [10, 20, 30, 8] et un voisin fixe dont le bord gauche
    est posé à `x`."""
    return [TY.norm_slot({"id": "mob", "label": "Mobile", "box": [10.0, 20.0, 30.0, 8.0],
                          "text": "m"}),
            TY.norm_slot({"id": "fixe", "label": "Fixe", "box": [x, 40.0, 20.0, 8.0],
                          "text": "f"})]


def test_l_AIMANT_pose_la_boite_sur_le_BORD_EXACT_du_voisin(tmp_path):
    """235 px d'écran valent 19,8967 mm : le bord gauche du mobile arrive à
    29,8967, soit 0,1033 mm du bord du voisin (30). Sous le seuil de 0,6 :
    l'aimant prend et pose 30,0 EXACTEMENT — pas 29,75, qui est ce que la
    grille de 0,25 mm aurait donné."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _voisin(30.0), "sel": ["mob"]},
        "actes": [{"t": "down", "id": "mob", "x": 400, "y": 400},
                  {"t": "move", "x": 630, "y": 400, "alt": False},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["mob"] == [30.0, 20.0, 30.0, 8.0], par
    assert par["fixe"][0] == 30.0, "le voisin a bougé"
    assert d["undo"] == 1, d["undo"]
    # LA LIGNE DE GUIDE EXISTE PENDANT LE GESTE, et elle nomme sa cible
    ov = d["traces"][1]["ov"]
    assert "cf-type-guide gx" in ov, ov[:600]
    assert "Fixe" in ov, ov[:600]
    # ... et elle a disparu au relâchement : un guide qui reste est une marque
    # que plus rien ne justifie
    assert "cf-type-guide" not in d["ov"], d["ov"][:600]


def test_la_GRILLE_reste_le_REPLI_quand_rien_n_aimante(tmp_path):
    """Le même geste, le voisin déplacé hors de portée : 19,8967 mm arrondis au
    quart de millimètre font 19,75, donc 29,75. La grille n'a pas été retirée,
    elle est passée dessous."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _voisin(58.0), "sel": ["mob"]},
        "actes": [{"t": "down", "id": "mob", "x": 400, "y": 400},
                  {"t": "move", "x": 630, "y": 400, "alt": False},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["mob"] == [29.5, 20.0, 30.0, 8.0], par
    assert "cf-type-guide" not in d["traces"][1]["ov"], d["traces"][1]["ov"][:600]


def test_ALT_DEBRAYE_l_aimant_ET_la_grille(tmp_path):
    """« Alt = à main levée », une seule promesse à retenir : c'est déjà la
    touche qui débrayait la grille, elle débraye maintenant les deux. 19,8967
    mm bruts, sans arrondi et sans aimant."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _voisin(30.0), "sel": ["mob"]},
        "actes": [{"t": "down", "id": "mob", "x": 400, "y": 400},
                  {"t": "move", "x": 630, "y": 400, "alt": True},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["mob"] == [29.473, 20.0, 30.0, 8.0], par
    assert "cf-type-guide" not in d["traces"][1]["ov"], d["traces"][1]["ov"][:600]


def test_la_FENETRE_D_ILLUSTRATION_est_une_CIBLE_d_aimantation(tmp_path):
    """P2 publie `frame.art_window` en millimètres depuis la coupe — le même
    contrat que P1 lit depuis le premier jour. P3 le lit comme cible : caler un
    titre sur le bord de la fenêtre est le geste le plus fréquent d'une mise en
    page de carte, et personne ne devrait avoir à recopier un nombre pour
    l'obtenir.

    24 px = 2,032 mm vers la gauche : le bord part à 7,968, soit 0,032 mm du
    bord de fenêtre (8). L'aimant pose 8,0."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": [TY.norm_slot({"id": "mob", "label": "Mobile",
                                          "box": [10.0, 20.0, 30.0, 8.0],
                                          "text": "m"})],
                  "sel": ["mob"]},
        "doc": {"frame": {"art_window": [8.0, 12.0, 40.0, 40.0]}},
        "actes": [{"t": "down", "id": "mob", "x": 400, "y": 400},
                  {"t": "move", "x": 376, "y": 400, "alt": False},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    assert d["slots"][0]["box"] == [8.0, 20.0, 30.0, 8.0], d["slots"][0]["box"]
    assert "fen" in d["traces"][1]["ov"], d["traces"][1]["ov"][:800]


def test_le_CENTRE_DE_CARTE_est_une_CIBLE_d_aimantation(tmp_path):
    """La carte poker fait 744 px de rogne à 300 DPI, soit 62,992 mm : son
    centre est à 31,496 — un nombre que personne ne tape à la main. 77 px de
    déplacement portent le CENTRE de la boîte à 31,5193, soit 0,0233 mm de la
    cible : le bord gauche se pose à 16,496."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": [TY.norm_slot({"id": "mob", "label": "Mobile",
                                          "box": [10.0, 20.0, 30.0, 8.0],
                                          "text": "m"})],
                  "sel": ["mob"]},
        "actes": [{"t": "down", "id": "mob", "x": 400, "y": 400},
                  {"t": "move", "x": 477, "y": 400, "alt": False},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    assert d["slots"][0]["box"] == [16.496, 20.0, 30.0, 8.0], d["slots"][0]["box"]
    assert "centre de carte" in d["traces"][1]["ov"], d["traces"][1]["ov"][:800]


# LA MUTATION QUI SÉPARE LES DEUX BOÎTES, CÔTÉ AIMANT : elle fait publier au
# fournisseur de cibles la boîte GONFLÉE d'une forme plate, exactement comme le
# ferait un aimant branché sur le DOM.
MUT_AIMANT_DOM = (
    "      trois(s.box, s.label);",
    "      trois((isShape(s) && s.box[3] === 0)\r\n"
    "        ? [s.box[0], s.box[1] - 0.508, s.box[2], 1.016] : s.box, s.label);")


def test_l_AIMANT_lit_la_boite_du_DOCUMENT_et_JAMAIS_le_calque(tmp_path):
    """LE MÊME PIÈGE QUE LE LASSO, DE L'AUTRE CÔTÉ DU GESTE. Une ligne plate
    est une cible à y = 40 et à rien d'autre ; son calque d'édition, lui,
    couvre 39,49 à 40,51 mm.

    366 px portent le bord haut du mobile à 40,988 : à 0,988 mm de la vraie
    cible (hors seuil) mais à 0,48 mm du bord de la boîte GONFLÉE (dans le
    seuil). Lu au document, l'aimant ne prend pas et la grille pose 41,0 ; lu
    au calque, il collerait à 40,508. Les deux valeurs sont mesurées."""
    # LA BOÎTE FAIT 12 mm DE HAUT, ET CE N'EST PAS UN DÉTAIL : à 6 mm, son
    # CENTRE serait tombé sur le centre de carte (43,984 mm) et l'aimant aurait
    # pris par là — le test aurait mesuré la mauvaise cible. Une vérité connue
    # se pose en écartant les autres.
    slots = [TY.norm_slot({"id": "mob", "label": "Mobile", "box": [10.0, 10.0, 20.0, 12.0],
                           "text": "m"}),
             TY.norm_slot({"id": "trait", "kind": "line", "label": "Trait",
                           "box": [10.0, 40.0, 40.0, 0.0],
                           "stroke": "#20c0ff", "stroke_mm": 0.5})]
    actes = [{"t": "down", "id": "mob", "x": 400, "y": 400},
             {"t": "move", "x": 400, "y": 766, "alt": False},
             {"t": "up"}]
    d = _banc_verrou(tmp_path, {"state": {"slots": slots, "sel": ["mob"]},
                                "actes": actes}, mutations=[MUT_UNDO])
    assert d["slots"][0]["box"][1] == 41.0, d["slots"][0]["box"]
    mut = _banc_verrou(tmp_path, {"state": {"slots": slots, "sel": ["mob"]},
                                  "actes": actes},
                       mutations=[MUT_UNDO, MUT_AIMANT_DOM])
    assert mut["slots"][0]["box"][1] == 40.508, \
        "la mutation ne change rien : le test ne sépare pas les deux boîtes"


def test_le_LOT_ENTIER_suit_l_aimant_de_la_boite_ATTRAPEE(tmp_path):
    """L'aimantation d'un lot est celle de la boîte qu'on tient : c'est elle
    qui se cale, les autres suivent du MÊME delta. Chaque boîte s'aimantant
    pour elle-même aurait disloqué le lot au premier voisin."""
    lot = [TY.norm_slot({"id": "mob", "label": "Mobile", "box": [10.0, 20.0, 30.0, 8.0],
                         "text": "m"}),
           TY.norm_slot({"id": "amis", "label": "Ami", "box": [12.0, 32.0, 6.0, 4.0],
                         "text": "a"}),
           TY.norm_slot({"id": "fixe", "label": "Fixe", "box": [30.0, 60.0, 20.0, 8.0],
                         "text": "f"})]
    d = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["mob", "amis"]},
        "actes": [{"t": "down", "id": "mob", "x": 400, "y": 400},
                  {"t": "move", "x": 630, "y": 400, "alt": False},
                  {"t": "up"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["mob"][0] == 30.0, par
    # le compagnon a pris EXACTEMENT le même delta (20,0 mm), pas son propre
    # arrondi : 12 + 20 = 32
    assert par["amis"][0] == 32.0, par
    assert par["fixe"][0] == 30.0, "le bloc hors du lot a bougé"
    assert d["undo"] == 1, d["undo"]


# ── 16.7 LA VÉRIFICATION NAVIGATEUR DES GESTES RÉELS ────────────────────────
#
# LE BANC DE NODE PROUVE LA MÉCANIQUE ; IL NE PROUVE PAS LE NAVIGATEUR. Son
# DOM est un analyseur de balises de trois cents lignes, ses évènements sont
# des objets littéraux, son `closest` remonte par un champ `parent`. Ce sont
# des approximations honnêtes — et une approximation ne dit rien de ce que
# Chrome fait d'un `PointerEvent` qui traverse un `pointer-events: none`.
#
# Ici le MODULE ENTIER est chargé dans un Chrome sans tête, avec un CORE
# bouchonné et une scène à l'échelle 1 (un pixel d'écran = un pixel de toile).
# Les quatre gestes de la tâche y sont joués avec de VRAIS `PointerEvent`
# dispatchés sur les VRAIS nœuds que le module a posés :
#
#   1. le LASSO part du fond du calque — la surface neuve, celle qui n'existe
#      que parce que le calque est `pointer-events: none` ;
#   2. ALIGNER À DROITE, sur le lot que le lasso vient de prendre ;
#   3. la ROTATION à la poignée, sur un bloc seul ;
#   4. un GUIDE qui aimante pendant un glisser — la ligne rouge est lue dans le
#      DOM au milieu du geste, et la boîte tombe sur le millimètre du voisin.
#
# C'est la première fois que ces gestes rencontrent le vrai routage
# d'évènements d'un navigateur.

SONDE_GESTES = r"""(async () => {
  const out = { etapes: [] };
  const host = document.getElementById("cf-host");
  await window.__MOD.init(host);
  await new Promise((r) => setTimeout(r, 400));
  const OV = document.querySelector(".cf-type-ov");
  if (!OV) return { erreur: "aucun calque d'édition posé" };
  const MM = (v) => window.__G.bleed_off_px[0] + v / 25.4 * 300;
  const MMY = (v) => window.__G.bleed_off_px[1] + v / 25.4 * 300;
  const ev = (el, type, x, y, opt) => el.dispatchEvent(new PointerEvent(type, Object.assign(
    { bubbles: true, cancelable: true, composed: true, pointerId: 1,
      isPrimary: true, clientX: x, clientY: y }, opt || {})));
  const attends = () => new Promise((r) => setTimeout(r, 90));
  const sel = () => JSON.parse(JSON.stringify(window.__DOC.type.sel));
  const box = (id) => (window.__DOC.type.slots.filter((s) => s.id === id)[0] || {}).box;
  const rot = (id) => (window.__DOC.type.slots.filter((s) => s.id === id)[0] || {}).rotate;

  /* 1. LE LASSO — il part du FOND du calque, la surface neuve */
  const bg = OV.querySelector(".cf-type-ovbg");
  out.fond = !!bg;
  ev(bg, "pointerdown", MM(5), MMY(15));
  ev(OV, "pointermove", MM(55), MMY(45));
  ev(OV, "pointerup", MM(55), MMY(45));
  await attends();
  out.etapes.push({ geste: "lasso", sel: sel() });

  /* 2. ALIGNER A DROITE, sur le lot que le lasso vient de prendre */
  const bAlign = document.querySelector('.cf-type-alg[data-a="right"]');
  out.barre = !!bAlign;
  if (bAlign) bAlign.click();
  await attends();
  out.etapes.push({ geste: "aligner", un: box("un"), deux: box("deux") });

  /* 3. LA ROTATION A LA POIGNEE, sur un bloc seul */
  const hb = OV.querySelector('.cf-type-hbox[data-id="trois"]');
  ev(hb, "pointerdown", MM(10), MMY(62));
  ev(OV, "pointerup", MM(10), MMY(62));
  await attends();
  const poignee = OV.querySelector(".cf-type-rot");
  out.poignee = !!poignee && !poignee.classList.contains("off");
  const cx = MM(8 + 12 / 2), cy = MMY(60 + 6 / 2);
  if (poignee) {
    ev(poignee, "pointerdown", cx + 100, cy);
    ev(OV, "pointermove", cx, cy + 100);
    ev(OV, "pointerup", cx, cy + 100);
  }
  await attends();
  out.etapes.push({ geste: "rotation", sel: sel(), rotate: rot("trois"),
    box: box("trois") });

  /* 4. UN GUIDE QUI AIMANTE — la ligne est lue AU MILIEU du geste */
  const hb2 = OV.querySelector('.cf-type-hbox[data-id="trois"]');
  ev(hb2, "pointerdown", 400, 400);
  ev(OV, "pointermove", 630, 400, { altKey: false });
  const gd = OV.querySelector(".cf-type-guide");
  const guide = gd ? { classe: gd.className, titre: gd.title,
    gauche: gd.style.left } : null;
  ev(OV, "pointerup", 630, 400);
  await attends();
  out.etapes.push({ geste: "guide", box: box("trois"), guide: guide,
    apres: !!OV.querySelector(".cf-type-guide") });
  out.erreurs = window.__ERR || [];
  return out;
})()"""


def _page_gestes(tmp_path, slots: list) -> pathlib.Path:
    """La page des GESTES : un panneau ouvert, une scène à l'échelle 1, et le
    module livré tel quel. Rien n'est extrait, rien n'est recopié — c'est le
    calque d'édition du produit qui reçoit les évènements."""
    g = CT.geom("poker_eu", 300)
    geo = {"fmt": "poker_eu", "label": "Poker", "dpi": 300,
           "canvas_px": list(g.canvas_px), "trim_px": list(g.trim_px),
           "bleed_off_px": list(g.bleed_off_px), "safe_px": list(g.safe_px),
           "safe_off_px": list(g.safe_off_px), "bleed_mm": 3, "safe_mm": 3,
           "corner_mm": 3, "corner_px": 35.4}
    page = tmp_path / "gestes.html"
    page.write_text(
        "<!doctype html><meta charset=\"utf-8\">"
        # LA FEUILLE DE LA PIÈCE EST CHARGÉE, et ce n'est pas cosmétique : le
        # calque d'édition est `position: fixed` PAR LE CSS, et son fond est
        # `inset: 0`. Sans elle, le calque retombe dans le flux et sa boîte
        # englobante n'est plus celle de la carte — la conversion écran ->
        # millimètres part alors d'une autre origine, et le lasso attrape le
        # vide. (Mesuré : sélection vide sur un lasso qui couvre deux blocs.)
        f"<link rel=\"stylesheet\" href=\"{CSS.as_uri()}\">"
        "<body style=\"margin:0;background:#111\">"
        # LA SCÈNE À L'ÉCHELLE 1 : un pixel d'écran = un pixel de toile, donc
        # un déplacement en pixels se relit en millimètres sans facteur caché.
        "<canvas class=\"stage-canvas\" style=\"position:fixed;left:0;top:0;"
        "width:" + str(g.canvas_px[0]) + "px;height:" + str(g.canvas_px[1])
        + "px\"></canvas>"
        "<div class=\"cf-panel on\"><div id=\"cf-host\"></div></div>"
        "<script>window.__ERR=[];"
        "window.onerror=function(m){window.__ERR.push(String(m));};"
        "window.__G=" + json.dumps(geo) + ";"
        "window.__G.mm2px=function(v){return v/25.4*300;};"
        "window.__G.px2mm=function(v){return v*25.4/300;};"
        "window.__DOC={type:{slots:" + json.dumps(slots, ensure_ascii=False)
        + ",sel:[],seeded:true,show_boxes:true,audit:false,"
        "preset:'champion',font_default:'Inter',autofit:true,fit_rect:[],"
        "optical_mm:0.5}};"
        "window.__TOASTS=[];"
        "window.CF={"
        "register:function(c){window.__MOD=c;return{"
        "patch:function(p){Object.assign(window.__DOC.type,p);"
        "return window.__DOC.type;},"
        "api:{get:async function(){return{};},post:async function(){return{};},"
        "raw:async function(){return{ok:false};},"
        "url:function(s){return '/api/cards/deck_00000000/type/'+s;}},"
        "emit:function(){},slot:function(){},aside:function(){},"
        "invalidate:function(){},busy:function(){},on:function(){},"
        "toast:function(m,e){window.__TOASTS.push(String(m));}};},"
        "get:function(p,d){var c=window.__DOC,ps=String(p).split('.');"
        "for(var i=0;i<ps.length;i++){if(c===null||typeof c!=='object'"
        "||!Object.prototype.hasOwnProperty.call(c,ps[i]))return d;c=c[ps[i]];}"
        "return c===undefined?d:c;},"
        "Z_TABLE:Object.freeze({10:'texture',20:'face',30:'texture',40:'frame',"
        "60:'type',70:'frame',90:'__core__'}),"
        "show:function(){},side:function(){return 'front';},"
        "geom:function(){return window.__G;},"
        "geomOf:function(){return window.__G;},current:function(){return 0;},"
        "cards:function(){return[];},card:function(){return{fields:{}};},"
        "models:async function(){return[];},"
        "doc:function(){return window.__DOC;},"
        "on:function(){},renderCard:async function(){return null;},"
        "modules:function(){return[];}};"
        "</script>"
        f"<script src=\"{JS.as_uri()}\"></script>"
        "</body>", encoding="utf-8")
    return page


def _chrome_gestes(tmp_path, slots, sonde_js=None):
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc du navigateur ne peut pas tourner")
    page = _page_gestes(tmp_path, slots)
    sonde = tmp_path / "sonde_gestes.js"
    sonde.write_text(sonde_js or SONDE_GESTES, encoding="utf-8")
    banc = tmp_path / "banc_chrome_gestes.mjs"
    banc.write_text(BANC_CHROME_TYPE, encoding="utf-8")
    r = subprocess.run([node, str(banc), str(page), str(sonde)],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=300)
    assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-2000:])
    v = json.loads(r.stdout)
    if v.get("skip"):
        pytest.skip("Chrome absent : la vérification navigateur ne peut pas tourner")
    assert not v.get("erreur"), v.get("erreur")
    assert v.get("erreurs") == [], v.get("erreurs")
    return v


def test_les_QUATRE_GESTES_tiennent_dans_un_VRAI_navigateur(tmp_path):
    """LE CALQUE D'ÉDITION DU PRODUIT, SOUS DE VRAIS ÉVÈNEMENTS.

    Les mêmes vérités connues que le banc de node, mesurées cette fois sur le
    routage d'évènements de Chrome — celui qui décide vraiment de ce qu'un
    `pointer-events: none` laisse passer :

      · le LASSO part du FOND du calque et prend les deux blocs qu'il touche ;
      · ALIGNER À DROITE sur l'enveloppe [10, 40] pose « deux » à 20 ;
      · la ROTATION va de plein est à plein sud, donc à 90°, sans que la boîte
        bouge d'un millimètre ;
      · 230 px de glisser portent le bord droit de « trois » à 0,53 mm de
        celui de « un » : l'aimant pose 28,0, et la ligne de guide EXISTE dans
        le DOM pendant le geste puis disparaît après."""
    slots = [TY.norm_slot({"id": "un", "label": "Un", "box": [10.0, 20.0, 30.0, 8.0],
                           "text": "un", "font": "Inter"}),
             TY.norm_slot({"id": "deux", "label": "Deux", "box": [16.0, 40.0, 20.0, 8.0],
                           "text": "deux", "font": "Inter"}),
             TY.norm_slot({"id": "trois", "label": "Trois", "box": [8.0, 60.0, 12.0, 6.0],
                           "text": "trois", "font": "Inter"})]
    v = _chrome_gestes(tmp_path, slots)
    assert v["fond"], "le fond du calque n'existe pas : aucun lasso n'est possible"
    par = {e["geste"]: e for e in v["etapes"]}

    assert par["lasso"]["sel"] == ["un", "deux"], par["lasso"]

    assert v["barre"], "la barre contextuelle n'est pas apparue à deux blocs"
    assert par["aligner"]["un"] == [10.0, 20.0, 30.0, 8.0], par["aligner"]
    assert par["aligner"]["deux"] == [20.0, 40.0, 20.0, 8.0], par["aligner"]

    assert v["poignee"], "la poignée de rotation manque (ou est grisée) en solo"
    assert par["rotation"]["sel"] == ["trois"], par["rotation"]
    assert abs(par["rotation"]["rotate"] - 90.0) < 0.01, par["rotation"]
    assert par["rotation"]["box"] == [8.0, 60.0, 12.0, 6.0], \
        "la rotation a déplacé la boîte"

    assert par["guide"]["box"] == [28.0, 60.0, 12.0, 6.0], par["guide"]
    gd = par["guide"]["guide"]
    assert gd, "aucune ligne de guide dans le DOM pendant le glisser"
    assert "gx" in gd["classe"], gd
    assert "Un" in gd["titre"] and "40" in gd["titre"], gd
    assert not par["guide"]["apres"], "la ligne de guide survit au relâchement"


# ── 16.8 LES MUTANTS DE LA TÂCHE : chacun casse UNE moitié d'un geste ───────
#
# UN TEST QUI PASSERAIT AUSSI SUR LE CODE CASSÉ NE PROUVE RIEN. Chaque mutation
# ci-dessous retire exactement une garantie de la tâche, et le test voisin doit
# alors mesurer AUTRE CHOSE. Ce qui est vérifié ici, ce n'est pas le module :
# c'est que les mesures d'à côté sont sensibles.

def test_un_lot_qui_ne_deplace_QUE_LA_BOITE_ATTRAPEE_rougit(tmp_path):
    """MUTATION : le glisser retombe sur un seul identifiant. Le compagnon
    reste sur place — et le contrat « tout le lot bouge » disparaît sans qu'une
    seule ligne rougisse ailleurs."""
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ["a", "b"]},
        "actes": [{"t": "down", "id": "a", "x": 400, "y": 400},
                  {"t": "move", "x": 550, "y": 400},
                  {"t": "up"}]},
        mutations=[MUT_UNDO,
                   ("const libres = vise.filter((q) => par[q] && !par[q].lock);",
                    "const libres = [id];")])
    par = {s["id"]: s["box"] for s in mut["slots"]}
    assert par["a"][0] == 22.7 and par["b"][0] == 10.0, par


def test_un_clic_NU_qui_REDUIT_le_lot_rougit(tmp_path):
    """MUTATION : la règle « déjà dedans, on garde » retirée. Tout glisser de
    groupe commencerait alors par détruire le groupe — un défaut qu'aucune
    capture d'écran ne montre, parce que le lot disparaît AU MÊME INSTANT où
    le glisser démarre."""
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": _lot2(), "sel": ["a", "b"]},
        "actes": [{"t": "down", "id": "b"}, {"t": "up"}]},
        mutations=[("    else if (i >= 0) return false;          "
                    "/* deja dedans : le lot est garde */",
                    "    else if (false) return false;")])
    assert mut["sel"] == ["b"], mut["sel"]


def test_un_ECHAP_SANS_GARDE_ecrit_au_document_pour_rien(tmp_path):
    """MUTATION : la garde de sélection retirée d'Échap. Chaque Échap sur un
    menu écrirait alors une révision au document — invisible, et pourtant
    chaque révision réveille l'enregistrement différé."""
    ref = _banc_verrou(tmp_path, {"state": {"slots": _lot2(), "sel": []},
                                  "actes": []})
    mut = _banc_verrou(tmp_path, {"state": {"slots": _lot2(), "sel": []},
                                  "actes": [{"t": "key", "k": "Escape"}]},
                       mutations=[("if (selIds().length) { mpatch({ sel: [] }); "
                                   "renderAll(); syncOverlay(); }",
                                   "mpatch({ sel: [] }); renderAll(); syncOverlay();")])
    assert mut["patchs"] == ref["patchs"] + 1, (mut["patchs"], ref["patchs"])


def test_une_egalisation_qui_NE_FILTRE_PAS_les_lignes_les_rend_diagonales(tmp_path):
    """MUTATION : l'exclusion des dimensions nulles retirée d'`egalise`. La
    ligne prend la hauteur du lot — c'est-à-dire qu'elle devient DIAGONALE, ce
    que la décision transmise interdit. Sans ce mutant, « la ligne garde sa
    hauteur nulle » pourrait être vrai par accident."""
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_avec_ligne(), "sel": ["un", "deux", "trait"]},
        "actes": [{"t": "barre", "v": "eqh"}]},
        mutations=[MUT_UNDO,
                   ('    const plat = (k, b) => (k === "line" || k === "arrow") '
                    '&& b[i1] === 0;',
                    "    const plat = () => false;")])
    par = {s["id"]: s["box"] for s in mut["slots"]}
    assert par["trait"][3] == 10.0, par
    assert all("diagonale" not in t["m"] for t in mut["toasts"]), mut["toasts"]


def test_des_bouts_fleches_SANS_FILTRE_ecrasent_les_autres_natures(tmp_path):
    """MUTATION : le filtre de nature retiré du lot. Un bloc de texte reçoit
    `arrow_start` — une clé qu'il porte (elle est dans la table des 49) et qui
    ne veut rien dire sur un titre. Le défaut est MUET : rien ne se dessine
    différemment, et le document ment sur ce qu'il décrit."""
    lot = [TY.norm_slot({"id": "f1", "kind": "arrow", "label": "F1",
                         "box": [0.0, 0.0, 30.0, 0.0], "stroke": "#fff",
                         "stroke_mm": 0.5}),
           TY.norm_slot({"id": "txt", "label": "Texte", "box": [0.0, 20.0, 30.0, 6.0],
                         "text": "x"})]
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["f1", "txt"]},
        "actes": [{"t": "lot", "k": "arrow_start"}]},
        mutations=[MUT_UNDO,
                   ('    const quels = fleche ? ((s) => s.kind === "arrow") : null;',
                    "    const quels = null;")])
    par = {s["id"]: s for s in mut["slots"]}
    assert par["txt"]["arrow_start"] is True, par["txt"]


def test_un_panneau_de_LOT_sans_detection_de_MELANGE_montre_le_PREMIER(tmp_path):
    """MUTATION : `commun` rend toujours la valeur du premier. Le panneau
    affirme alors « recto » sur un lot dont la moitié est au verso — et un clic
    sur « recto » déplacerait silencieusement les autres. C'est exactement le
    défaut que le mot « mixte » existe pour empêcher."""
    lot = _lot3()
    lot[1]["side"] = "back"
    mut = _banc_verrou(tmp_path, {"state": {"slots": lot, "sel": ["un", "deux"]}},
                       mutations=[("      if (list[i][k] !== v) return { mix: true, v: null };",
                                   "      if (false) return { mix: true, v: null };")])
    assert "mixte" not in mut["insp"], mut["insp"][:400]
    assert 'seg-b active" type="button" data-v="front"' in mut["insp"], \
        mut["insp"][:900]


def test_une_disposition_DEJA_POSEE_qui_patche_quand_meme_rougit(tmp_path):
    """MUTATION : la garde « rien à faire » retirée de `poseBoites`. Aligner un
    lot DÉJÀ aligné poserait une entrée d'annulation qui ne défait rien — et
    c'est le genre de Ctrl+Z fantôme qui fait perdre confiance dans toute la
    pile."""
    aligne = [TY.norm_slot({"id": "un", "label": "Un", "box": [6.0, 20.0, 30.0, 8.0],
                            "text": "1"}),
              TY.norm_slot({"id": "deux", "label": "Deux", "box": [6.0, 40.0, 12.0, 6.0],
                            "text": "2"})]
    ref = _banc_verrou(tmp_path, {
        "state": {"slots": aligne, "sel": ["un", "deux"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    assert ref["traces"][0]["undo"] == 0 and ref["traces"][0]["patchs"] == 0, ref["traces"]
    assert any("déjà" in t["m"] for t in ref["toasts"]), ref["toasts"]
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": aligne, "sel": ["un", "deux"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO,
                   ('    if (!bouge) { M.toast("le lot est déjà dans cette '
                    'disposition"); return; }',
                    "    if (false) { return; }")])
    assert mut["traces"][0]["undo"] == 1, mut["traces"]


def test_un_ordre_de_profondeur_SANS_GARDE_DE_BORD_deplace_A_L_ENVERS(tmp_path):
    """MUTATION : la garde de bord retirée d'`ordreApres`. « Derrière » sur le
    bloc DÉJÀ au fond ne rend plus `null` : la place d'insertion négative est
    absorbée par `slice`, et le bloc part... VERS L'AVANT. Le geste fait alors
    l'inverse de son nom, et l'annulation vide devient un déplacement faux."""
    ref = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "barre", "cl": "cf-type-z", "dk": "z", "v": "arriere"}]},
        mutations=[MUT_UNDO])
    assert _ids(ref) == ["un", "deux", "trois"], ref["slots"]
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un"]},
        "actes": [{"t": "barre", "cl": "cf-type-z", "dk": "z", "v": "arriere"}]},
        mutations=[MUT_UNDO,
                   ("    if (pos < 0 || pos > dehors.length) return null;",
                    "    if (false) return null;")])
    assert _ids(mut) == ["deux", "un", "trois"], mut["slots"]
    assert mut["traces"][0]["undo"] == 1 and mut["traces"][0]["patchs"] == 1, \
        mut["traces"]


# ── 16.9 LES TROIS GESTES QUI EXISTAIENT DÉJÀ, ET QUE LE LOT A RENDUS FAUX ──
#
# CE QUE LA MULTI-SÉLECTION CASSE SI L'ON N'Y TOUCHE PAS. Suppr, Ctrl+D et les
# flèches lisaient `selSlot()` — LE PREMIER du lot. Sur une sélection de trois
# blocs, Suppr en effaçait un et laissait les deux autres, les flèches en
# poussaient un et disloquaient le lot, Ctrl+D en dupliquait un.
#
# Ce ne sont pas des « améliorations » : ce sont des défauts introduits PAR la
# tâche, et ils se réparent dans la tâche. La règle est la même que celle du
# glisser de lot — un geste, un delta, UN pas d'annulation, et les blocs
# verrouillés ne suivent pas mais le refus se dit.

def _lot3v(lock=None) -> list:
    lot = _lot3()
    if lock is not None:
        lot[lock]["lock"] = True
    return lot


def test_SUPPR_efface_TOUT_le_lot_en_UN_pas(tmp_path):
    """Trois blocs désignés, une touche : trois effacements, une annulation.
    Et la désignation retombe sur un survivant — un `sel` mort ferait régler
    un fantôme (la leçon de la corbeille de rangée)."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "trois"]},
        "actes": [{"t": "key", "k": "Delete"}]},
        mutations=[MUT_UNDO])
    assert _ids(d) == ["deux"], d["slots"]
    assert d["sel"] == ["deux"], d["sel"]
    assert d["undo"] == 1, d["undo"]
    # ... et le lot ENTIER effacé laisse une sélection VIDE, pas un fantôme
    v = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "key", "k": "Delete"}]},
        mutations=[MUT_UNDO])
    assert v["slots"] == [] and v["sel"] == [], (v["slots"], v["sel"])


def test_SUPPR_garde_les_blocs_VERROUILLES_du_lot_et_le_DIT(tmp_path):
    """Même doctrine que le glisser de lot : ce qui est protégé ne bouge pas,
    le reste passe, et l'écran dit combien. Refuser le geste ENTIER aurait
    fait d'un cadenas sur un bloc un cadenas sur toute la sélection."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3v(1), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "key", "k": "Delete"}]},
        mutations=[MUT_UNDO])
    assert _ids(d) == ["deux"], d["slots"]
    assert d["undo"] == 1, d["undo"]
    assert any("verrouill" in t["m"] for t in d["toasts"]), d["toasts"]
    # TOUT le lot verrouillé : rien n'est effacé, et rien ne s'annule
    t = _banc_verrou(tmp_path, {
        "state": {"slots": [dict(s, lock=True) for s in _lot3()],
                  "sel": ["un", "deux"]},
        "actes": [{"t": "key", "k": "Delete"}]},
        mutations=[MUT_UNDO])
    assert len(t["slots"]) == 3, t["slots"]
    assert t["undo"] == 0, t["undo"]
    assert any("verrouill" in x["m"] for x in t["toasts"]), t["toasts"]


def test_les_FLECHES_poussent_TOUT_le_lot_du_MEME_pas(tmp_path):
    """Une flèche pousse d'un millimètre — le lot entier, du même
    millimètre, en une annulation. Pousser le seul premier aurait disloqué en
    silence un lot qu'on vient d'aligner."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "trois"]},
        "actes": [{"t": "key", "k": "ArrowRight"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["un"][0] == 11.0 and par["trois"][0] == 7.0, par
    assert par["deux"][0] == 14.0, "un bloc hors du lot a bougé"
    assert d["undo"] == 1, d["undo"]
    # Alt+flèche RETAILLE, et le lot entier suit du même millimètre
    a = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "trois"]},
        "actes": [{"t": "key", "k": "ArrowRight", "alt": True}]},
        mutations=[MUT_UNDO])
    pa = {s["id"]: s["box"] for s in a["slots"]}
    assert pa["un"][2] == 31.0 and pa["trois"][2] == 21.0, pa
    assert a["undo"] == 1, a["undo"]
    # ... et un bloc VERROUILLÉ du lot ne bouge pas
    v = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3v(2), "sel": ["un", "trois"]},
        "actes": [{"t": "key", "k": "ArrowRight"}]},
        mutations=[MUT_UNDO])
    pv = {s["id"]: s["box"] for s in v["slots"]}
    assert pv["un"][0] == 11.0 and pv["trois"][0] == 6.0, pv


def test_CTRL_D_duplique_TOUT_le_lot_et_DESIGNE_les_copies(tmp_path):
    """Dupliquer trois blocs et se retrouver à en régler un seul serait une
    demi-copie. Les copies naissent ensemble, décalées de 2 mm, ouvertes (le
    verrou marque un bloc DÉJÀ placé), et c'est ELLES qu'on tient après."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux"]},
        "actes": [{"t": "key", "k": "d", "ctrl": True}]},
        mutations=[MUT_UNDO])
    assert len(d["slots"]) == 5, _ids(d)
    assert d["sel"] == ["un2", "deux2"], d["sel"]
    par = {s["id"]: s for s in d["slots"]}
    assert par["un2"]["box"] == [12.0, 22.0, 30.0, 8.0], par["un2"]["box"]
    assert par["un2"]["lock"] is False, par["un2"]
    assert d["undo"] == 1, d["undo"]


def test_APRES_ECHAP_le_clavier_ne_vise_PLUS_RIEN(tmp_path):
    """LE DANGER QUE LA TOUCHE ÉCHAP VIENT DE CRÉER, ET QUI EST FERMÉ ICI.

    `selSlot()` retombe sur le PREMIER bloc quand rien n'est désigné. Avant
    cette tâche, la sélection vide était rarissime (un jeu légué) ; Échap la
    rend COURANTE. Sans ce changement, « je relâche tout » serait devenu
    l'antichambre d'un effacement au hasard : Suppr aurait effacé un bloc que
    personne n'avait choisi, et Ctrl+D l'aurait dupliqué.

    Les deux surfaces disent maintenant la même chose au même instant : le
    clavier ne vise rien, et le panneau ne montre rien."""
    actes = [{"t": "key", "k": "Escape"}, {"t": "key", "k": "Delete"},
             {"t": "key", "k": "d", "ctrl": True},
             {"t": "key", "k": "ArrowRight"}]
    d = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["deux"]},
                                "actes": actes}, mutations=[MUT_UNDO])
    assert _ids(d) == ["un", "deux", "trois"], d["slots"]
    assert [s["box"] for s in d["slots"]] == LOT3, d["slots"]
    assert d["sel"] == [], d["sel"]
    # ÉCHAP LUI-MÊME NE COMPTE PAS COMME UNE ÉDITION : rien à annuler après
    assert d["undo"] == 0, d["undo"]
    assert "Sélectionnez un slot" in d["insp"], d["insp"][:300]
    # LE TÉMOIN : les mêmes touches, sur un lot désigné, font tout leur travail
    t = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["deux"]},
                                "actes": actes[1:]}, mutations=[MUT_UNDO])
    assert _ids(t) != ["un", "deux", "trois"], t["slots"]


def test_le_PLANCHER_du_lasso_separe_un_CLIC_d_un_RECTANGLE(tmp_path):
    """LE TREMBLEMENT DE LA MAIN N'EST PAS UN LASSO. Sans plancher, un appui
    sur le vide à un demi-millimètre du bord d'un bloc, relâché avec un
    frisson, aurait sélectionné ce bloc — au moment précis où l'utilisateur
    voulait TOUT relâcher.

    Le plancher est un chiffre, et il se mesure des deux côtés : 0,3 mm de
    rectangle sur un bloc ne prennent RIEN (c'est un clic), 0,6 mm le
    prennent (c'est un lasso). Sans ce contrôle, la constante pourrait valoir
    zéro sans qu'une ligne rougisse."""
    lot = [TY.norm_slot({"id": "bloc", "label": "Bloc", "box": [10.0, 20.0, 30.0, 8.0],
                         "text": "b"})]
    clic = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": []},
        "actes": [{"t": "lasso", "x0": _clx(20.0), "y0": _cly(24.0),
                   "x1": _clx(20.3), "y1": _cly(24.3)}]})
    assert clic["sel"] == [], clic["sel"]
    lasso = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": []},
        "actes": [{"t": "lasso", "x0": _clx(20.0), "y0": _cly(24.0),
                   "x1": _clx(20.6), "y1": _cly(24.6)}]})
    assert lasso["sel"] == ["bloc"], lasso["sel"]
    # MUTATION : le plancher à zéro. Le clic devient un lasso d'un point, et
    # il attrape le bloc qu'il touche.
    mut = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": []},
        "actes": [{"t": "lasso", "x0": _clx(20.0), "y0": _cly(24.0),
                   "x1": _clx(20.3), "y1": _cly(24.3)}]},
        mutations=[("const LASSO_MIN_MM = 0.5;", "const LASSO_MIN_MM = 0;")])
    assert mut["sel"] == ["bloc"], \
        "le plancher n'était pas ce qui séparait le clic du rectangle"


def test_la_LISTE_allume_TOUTES_les_rangees_du_lot(tmp_path):
    """LE LECTEUR QU'ON OUBLIE. La liste de blocs allumait la rangée du
    PREMIER désigné : trois blocs pris au lasso, une seule rangée allumée —
    une liste qui contredit la carte, et c'est justement par la liste qu'on
    vérifie ce que le lasso a pris."""
    d = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un", "trois"]}})
    par = {r["id"]: r["sel"] for r in d["rangees"]}
    assert par == {"un": True, "deux": False, "trois": True}, par
    # MUTATION : la rangée redevient un test d'égalité au premier
    mut = _banc_verrou(tmp_path, {"state": {"slots": _lot3(), "sel": ["un", "trois"]}},
                       mutations=[("(lot.indexOf(s.id) >= 0 ? \" on\" : \"\")",
                                   "(s.id === lot[0] ? \" on\" : \"\")")])
    pm = {r["id"]: r["sel"] for r in mut["rangees"]}
    assert pm == {"un": True, "deux": False, "trois": False}, pm


def test_le_COLLAGE_exige_UN_SEUL_calque_designe():
    """LA TROISIÈME FOIS LA MÊME RÈGLE (avec Suppr et Ctrl+D). Le collage
    visait `selSlot()`, qui retombe sur le PREMIER bloc quand rien n'est
    désigné : un Ctrl+V après un Échap serait parti dans un calque que
    personne n'avait choisi. Et sur un LOT, « colle dans lequel ? » n'a pas de
    bonne réponse : on ne devine pas, on ne fait rien."""
    src = _js()
    fn = _js_fn(src, "onPaste")
    # LE CODE, PAS LA PROSE : le commentaire NOMME `selSlot()` pour dire d'où
    # vient le défaut, et une recherche naïve de la chaîne le prendrait pour le
    # défaut lui-même.
    assert "const s = selSlot();" not in fn, \
        "le collage lit encore le repli du premier bloc"
    assert "const l = selSlots();" in fn and "l.length === 1" in fn, fn[:400]
    assert "isImage(s)" in fn, "le collage ne vérifie plus la nature du bloc"


def test_la_CORBEILLE_d_une_rangee_laisse_VIVRE_le_reste_du_lot(tmp_path):
    """Effacer un bloc d'un lot de trois ne doit pas relâcher les deux autres :
    la corbeille d'une rangée vise SA rangée. Le reste du lot survit, et le lot
    vidé retombe sur un survivant plutôt que sur un fantôme."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "rangee", "id": "deux", "b": "del"}]},
        mutations=[MUT_UNDO])
    assert _ids(d) == ["un", "trois"], d["slots"]
    assert d["sel"] == ["un", "trois"], d["sel"]
    assert d["traces"][0]["undo"] == 1, d["traces"]
    # le DERNIER du lot efface : la désignation retombe sur un survivant
    s = _banc_verrou(tmp_path, {
        "state": {"slots": _lot3(), "sel": ["deux"]},
        "actes": [{"t": "rangee", "id": "deux", "b": "del"}]},
        mutations=[MUT_UNDO])
    assert s["sel"] == ["trois"], s["sel"]


# ═════════════════════════════════════════════════════════════════════════════
# 17. LA RONDE ADVERSE DE T3 — un bloquant, trois réels, deux mineurs
# ═════════════════════════════════════════════════════════════════════════════
#
# CE QUE LA REVUE A MESURÉ, ET QUE CETTE SECTION VERROUILLE :
#
#   B1. La barre contextuelle IGNORAIT le verrou, EN SILENCE. Le même bloc
#       verrouillé tenait au glisser (« 1 bloc verrouillé n'a pas suivi ») puis
#       BOUGEAIT à « aligner » un clic plus tard, sans un mot ; « égaliser » le
#       redimensionnait. Le cadenas n'existait qu'au clavier et au glisser.
#   R1. La garde de référence d'`egalise` testait le KIND, pas la DIMENSION :
#       un bloc de TEXTE à hauteur nulle aplatissait tout le lot — le danger
#       que la clause écrite trois lignes plus haut nomme en toutes lettres.
#   R2. `distribue` prenait le bord GAUCHE maximal pour portée, pas le bord
#       DROIT maximal : sur des boîtes qui se chevauchent — la carte NORMALE —
#       un membre sortait de l'enveloppe par la gauche.
#   R3. Le témoin de tangence était avouable... et FAUX de mesure : `dansLasso`
#       est une fonction pure millimètres -> booléen, donc pinnable par le même
#       harnais que les autres. L'aveu se mesure ; celui-là ne se mesurait pas.
#   M3. Trois règles pour une liste : le lasso et l'aimant écartaient les blocs
#       MASQUÉS, la barre les prenait. Une seule règle est tranchée ici.


def _lot_verrou(i_verrou: int) -> list:
    """Trois blocs de largeurs et de positions DIFFÉRENTES — sans quoi
    « aligner » ne prouverait rien — dont un verrouillé."""
    lot = [TY.norm_slot({"id": "un", "label": "Un", "box": [10.0, 20.0, 30.0, 8.0],
                         "text": "1"}),
           TY.norm_slot({"id": "deux", "label": "Deux", "box": [14.0, 40.0, 12.0, 6.0],
                         "text": "2"}),
           TY.norm_slot({"id": "trois", "label": "Trois", "box": [6.0, 60.0, 20.0, 4.0],
                         "text": "3"})]
    lot[i_verrou]["lock"] = True
    return lot


# ── B1 : LE VERROU VAUT AUSSI POUR LA BARRE, ET IL EST UNE ANCRE ────────────

def test_B1_ALIGNER_laisse_le_bloc_VERROUILLE_en_ANCRE(tmp_path):
    """LE BLOQUANT DE LA RONDE. Le verrou protégeait des gestes de scène
    (glisser, poignées, flèches, Suppr) et de rien d'autre : la barre
    contextuelle déplaçait un bloc verrouillé sans un mot, un clic après que le
    glisser l'avait refusé.

    LA RÈGLE TRANCHÉE (patron Figma) : un bloc verrouillé est une ANCRE. Il
    compte dans l'ENVELOPPE — c'est justement sur lui qu'on veut aligner le
    reste — mais il ne reçoit PAS le patch, et l'écran le dit.

    Vérité connue : l'enveloppe des trois vaut [6, 20, 34, 44], donc « aligner
    à gauche » veut 6 pour tout le monde. « deux » est verrouillé : il reste à
    14, et c'est bien l'enveloppe des TROIS (6) que les deux autres prennent —
    pas celle des deux libres (10)."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_verrou(1), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["deux"] == [14.0, 40.0, 12.0, 6.0], "le bloc verrouillé a bougé"
    assert par["un"][0] == 6.0 and par["trois"][0] == 6.0, par
    assert d["traces"][0]["undo"] == 1, d["traces"]
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "verrouill" in msg and "align" in msg, d["toasts"]


def test_B1_DISTRIBUER_laisse_le_bloc_VERROUILLE_en_place_et_le_DIT(tmp_path):
    """Même règle, deuxième famille. Le verrouillé ne bouge pas, les libres
    prennent la place que le calcul leur donne, et la phrase sort."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_verrou(1), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "distv"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["deux"][1] == 40.0, "le bloc verrouillé a été distribué"
    assert par["un"][1] == 20.0 and par["trois"][1] == 60.0, par
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "verrouill" in msg and "distribu" in msg, d["toasts"]


def test_B1_EGALISER_ne_REDIMENSIONNE_PAS_un_bloc_verrouille(tmp_path):
    """Troisième famille, et c'est la plus grave : « égaliser » ne déplaçait
    pas le bloc protégé, il le REDIMENSIONNAIT (hauteur 6 -> 8, zéro toast).

    LA RÉFÉRENCE RESTE LE PREMIER SÉLECTIONNÉ même verrouillé : il DONNE sa
    taille (c'est le « key object »), il n'en reçoit pas."""
    d = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_verrou(1), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "eqh"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["deux"][3] == 6.0, "le bloc verrouillé a été redimensionné"
    assert par["trois"][3] == 8.0, par
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "verrouill" in msg and "égalis" in msg, d["toasts"]
    # ... et la RÉFÉRENCE verrouillée donne quand même sa taille
    r = _banc_verrou(tmp_path, {
        "state": {"slots": _lot_verrou(0), "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "eqh"}]},
        mutations=[MUT_UNDO])
    pr = {s["id"]: s["box"] for s in r["slots"]}
    assert pr["un"][3] == 8.0, "la référence verrouillée a été touchée"
    assert pr["deux"][3] == 8.0 and pr["trois"][3] == 8.0, pr


def test_B1_TOUT_le_lot_verrouille_ne_bouge_RIEN_et_ne_s_annule_pas(tmp_path):
    """Le bord : aucun bloc libre. Rien n'est écrit, rien n'est empilé, et la
    phrase est celle du verrou — pas « le lot est déjà dans cette
    disposition », qui serait faux."""
    lot = [dict(s, lock=True) for s in _lot_verrou(0)]
    d = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    assert [s["box"] for s in d["slots"]] == [b["box"] for b in lot], d["slots"]
    assert d["traces"][0]["undo"] == 0 and d["traces"][0]["patchs"] == 0, d["traces"]
    assert any("verrouill" in t["m"] for t in d["toasts"]), d["toasts"]


def test_B1_le_cadenas_ANNONCE_la_barre_dans_ce_qu_il_refuse():
    """LA QUESTION N'ÉTAIT NI TRANCHÉE NI DITE : ni l'infobulle du cadenas ni
    la doctrine des libertés ne mentionnaient « aligner ». Un verrou dont on
    découvre la portée en la dépassant n'est pas un verrou."""
    src = _js()
    fn = _js_fn(src, "renderList")
    i = fn.index("Verrouiller ce bloc")
    bulle = fn[i:i + 400]
    for mot in ("aligner", "distribuer", "égaliser"):
        assert mot in bulle, f"l'infobulle du cadenas ne nomme pas « {mot} »"
    # ... et la doctrine écrite au-dessus de la rangée aussi
    assert "barre de lot" in src, \
        "la doctrine des libertés ne nomme pas la barre contextuelle"


# ── R1 : LA GARDE DE RÉFÉRENCE TESTE LA DIMENSION, PAS LA NATURE ────────────

def test_R1_un_TEXTE_a_hauteur_NULLE_en_reference_est_REFUSE_aussi():
    """LA CLAUSE ÉTAIT ÉCRITE ET LA GARDE NE LA TENAIT PAS. « Sa hauteur nulle
    aplatirait tout le lot » vaut pour N'IMPORTE QUELLE nature : le champ
    « Hauteur » du panneau accepte 0, et `norm_slot` le borne à [0, 500]. Un
    bloc de texte à hauteur nulle en référence aplatissait donc tout le lot,
    sans un mot.

    La branche REFUS se teste désormais sur la DIMENSION seule. La branche
    IGNORES, elle, garde la nature : une LIGNE membre reste ignorée (l'agrandir
    la rendrait diagonale), un TEXTE membre à hauteur nulle est agrandi comme
    les autres — c'est un bloc plat, pas un axe."""
    r = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,0],[5,20,8,4],[3,40,12,6]],"
        "['text','text','image'],'h')));"))
    assert r["refuse"] == "reference", r
    assert [b[3] for b in r["boxes"]] == [0.0, 4.0, 6.0], r["boxes"]
    # ... et un TEXTE plat MEMBRE (pas référence) suit le lot : il est plat,
    # pas axial — l'agrandir ne change pas sa nature.
    m = json.loads(_pures_js(
        ["egalise"],
        "console.log(JSON.stringify(egalise("
        "[[0,0,20,10],[5,20,8,0],[3,40,30,0]],"
        "['rect','text','line'],'h')));"))
    assert m["ignores"] == [2], m
    assert [b[3] for b in m["boxes"]] == [10.0, 10.0, 0.0], m["boxes"]


def test_R1_le_refus_ne_dit_plus_LIGNE_PLATE_sur_un_texte(tmp_path):
    """« Une ligne plate » est FAUX quand la référence est un titre. La phrase
    se généralise — et elle garde le remède, qui est le même."""
    lot = [TY.norm_slot({"id": "plat", "label": "Titre plat",
                         "box": [0.0, 0.0, 20.0, 0.0], "text": "t"}),
           TY.norm_slot({"id": "b", "label": "B", "box": [5.0, 20.0, 8.0, 4.0],
                         "text": "b"})]
    d = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["plat", "b"]},
        "actes": [{"t": "barre", "v": "eqh"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["b"][3] == 4.0, "le lot a été aplati"
    assert d["traces"][0]["undo"] == 0, d["traces"]
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "ligne plate" not in msg, msg
    assert "hauteur nulle" in msg and "référence" in msg, msg


def test_R1_les_champs_de_TAILLE_ont_un_PLANCHER_dans_le_panneau():
    """LA PORTE D'ENTRÉE SE FERME AUSSI. Le champ « Hauteur » n'avait pas de
    `min` : c'est par là que la boîte à dimension nulle entre. Les champs de
    LARGEUR et de HAUTEUR portent désormais le plancher de la pièce ; ceux de
    POSITION, eux, gardent leur liberté (une boîte peut être à x = 0)."""
    src = _js()
    fn = _js_fn(src, "inspBoite")
    for cle in ("bw", "bh"):
        m = re.search(r'nfield\("' + cle + r'"[\s\S]{0,180}?\)\n', fn)
        assert m and "plancherBoite(s)" in m.group(0), \
            f"{cle} n'a pas de plancher : {m.group(0) if m else None}"
    for cle in ("bx", "by"):
        m = re.search(r'nfield\("' + cle + r'"[^\n]*', fn)
        assert "plancher" not in m.group(0), \
            f"{cle} a hérité d'un plancher qui n'a pas de sens pour une position"
    # ET LE PLANCHER SUIT LA NATURE : une LIGNE horizontale EST une boîte de
    # hauteur nulle (la règle de l'axe, et `SHAPE_NEE.line` en fait naître une
    # comme ça). Un plancher de 2 mm posé en dur aurait rendu toute ligne
    # droite inatteignable au panneau — la correction aurait cassé une nature
    # pour en protéger une autre.
    out = json.loads(_pures_js(
        ["plancherBoite"],
        "const MIN_BOX_MM=2;console.log(JSON.stringify(["
        "plancherBoite({kind:'text'}),plancherBoite({kind:'rect'}),"
        "plancherBoite({kind:'line'}),plancherBoite({kind:'arrow'}),"
        "plancherBoite({kind:'image'})]));"))
    assert out == [2, 2, 0, 0, 2], out


# ── R2 : LA PORTÉE DE LA DISTRIBUTION EST L'ENVELOPPE, PAS UN BORD GAUCHE ───

def test_R2_distribuer_des_boites_QUI_SE_CHEVAUCHENT_garde_l_enveloppe():
    """LA CARTE NORMALE : un rectangle de fond, un titre et une statistique
    posés DEDANS. L'ancienne portée allait du bord gauche minimal au bord
    gauche MAXIMAL + sa largeur — donc 55 au lieu de 60 — et le calcul poussait
    un membre HORS de l'enveloppe, par la gauche.

    Vérité connue : fond [0, 0, 60, 40], titre [10, 5, 30, 8], stat
    [45, 5, 10, 8]. L'enveloppe horizontale va de 0 à 60, les objets font
    100 mm : l'espace égal est NÉGATIF (−20). L'INVARIANT EXACT, et il faut le
    dire juste — ma première écriture de ce test affirmait « aucun membre ne
    sort de l'enveloppe », ce qui est ARITHMÉTIQUEMENT IMPOSSIBLE quand les
    objets ne tiennent pas dans leur propre portée :

      · aucun membre ne commence AVANT le début de l'enveloppe (c'était le
        défaut : un bord à −5 mm) ;
      · le DERNIER dans l'ordre finit EXACTEMENT à la fin de l'enveloppe —
        c'est ça, « la portée est l'enveloppe » ;
      · un membre du MILIEU peut déborder quand le jeu est négatif : c'est le
        chevauchement lui-même, et il est avoué par le calcul (`jeu`) puis
        dit à l'écran."""
    r = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[0,0,60,40],[10,5,30,8],[45,5,10,8]],'h')));"))
    bords = [b[0] for b in r["boxes"]]
    droits = [b[0] + b[2] for b in r["boxes"]]
    assert min(bords) == 0.0, f"un membre part avant l'enveloppe : {bords}"
    # ordre des centres : titre (25), fond (30), stat (50) — le dernier ferme
    assert r["boxes"][2][0] + r["boxes"][2][2] == 60.0, r["boxes"]
    assert [b[0] for b in r["boxes"]] == [10.0, 0.0, 50.0], r["boxes"]
    assert max(droits) == 70.0, "le débord du milieu n'est plus mesuré"
    assert r["jeu"] == -20.0, r["jeu"]

    # LE CONTRÔLE : l'ancienne portée (bord gauche maximal + sa largeur) ne
    # ferme pas l'enveloppe — le lot se distribue sur 55 mm au lieu de 60, et
    # la sélection cesse de couvrir ce qu'elle couvrait.
    # (la portée d'avant se recalcule APRÈS `ord`, sinon la mutation lirait
    # `ord` avant sa déclaration — un mutant qui ne compile pas ne mesure rien)
    mut = json.loads(_node_type(
        _fonction_js_type("enveloppe") + _fonction_js_type("distribue")
        # `_js()` lit en newlines universelles (\n), là où `_banc_verrou` garde
        # les CRLF : deux portes, deux conventions — se tromper de convention
        # rend une mutation SILENCIEUSEMENT inopérante, donc un contrôle vert
        # qui ne contrôle rien. C'est pour ça que l'assertion d'en dessous
        # exige que le mutant DIFFÈRE.
        .replace("    const jeu = (fin - deb - somme) / (n - 1);\n"
                 "    let pos = deb;",
                 "    const deb2 = boxes[ord[0]][i0];\n"
                 "    const fin2 = boxes[ord[n - 1]][i0] + boxes[ord[n - 1]][i1];\n"
                 "    const jeu = (fin2 - deb2 - somme) / (n - 1);\n"
                 "    let pos = deb2;")
        + "console.log(JSON.stringify(distribue("
          "[[0,0,60,40],[10,5,30,8],[45,5,10,8]],'h')));"))
    assert mut["boxes"][2][0] + mut["boxes"][2][2] == 55.0, \
        "la mutation ne change pas la portée : le test ne prouve pas la correction"


def test_R2_l_ordre_de_distribution_est_celui_des_CENTRES():
    """Patron Figma : c'est le CENTRE qui range, pas le bord gauche. Sur des
    boîtes de largeurs très différentes, le bord gauche donne un ordre que
    l'œil ne lit pas — un large bloc commençant tôt passerait « avant » un
    petit bloc pourtant plus à gauche visuellement."""
    r = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[0,0,40,5],[5,0,4,5],[60,0,10,5]],'h')));"))
    # centres : 20, 7, 65 -> l'ordre est [1, 0, 2]
    # enveloppe 0..70, somme 54, jeu = (70 - 0 - 54) / 2 = 8
    assert r["jeu"] == 8.0, r["jeu"]
    assert [b[0] for b in r["boxes"]] == [12.0, 0.0, 60.0], r["boxes"]


def test_R2_les_trois_verites_connues_d_avant_tiennent_encore():
    """La correction ne doit pas déplacer ce qui était juste : trois boîtes
    disjointes de largeurs égales donnent toujours 0 / 50 / 100."""
    h = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[0,0,10,5],[20,0,10,5],[100,0,10,5]],'h')));"))
    assert [b[0] for b in h["boxes"]] == [0.0, 50.0, 100.0], h
    assert h["jeu"] == 40.0, h["jeu"]
    v = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue("
        "[[0,0,5,10],[0,20,5,10],[0,100,5,10]],'v')));"))
    assert [b[1] for b in v["boxes"]] == [0.0, 50.0, 100.0], v
    deux = json.loads(_pures_js(
        ["enveloppe", "distribue"],
        "console.log(JSON.stringify(distribue([[0,0,10,5],[80,0,10,5]],'h')));"))
    assert [b[0] for b in deux["boxes"]] == [0.0, 80.0], deux


def test_R2_le_chevauchement_se_DIT_a_l_ecran(tmp_path):
    """Un espace NÉGATIF n'est pas une erreur d'arithmétique, c'est un fait :
    les blocs ne tiennent pas dans leur propre portée. Il se dit, avec son
    chiffre — sinon l'utilisateur voit ses blocs se superposer sans savoir
    pourquoi."""
    lot = [TY.norm_slot({"id": "fond", "label": "Fond", "kind": "rect",
                         "box": [0.0, 0.0, 60.0, 40.0], "fill": "#f2efe9"}),
           TY.norm_slot({"id": "titre", "label": "Titre", "box": [10.0, 5.0, 30.0, 8.0],
                         "text": "t"}),
           TY.norm_slot({"id": "stat", "label": "Stat", "box": [45.0, 5.0, 10.0, 8.0],
                         "text": "9"})]
    d = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["fond", "titre", "stat"]},
        "actes": [{"t": "barre", "v": "disth"}]},
        mutations=[MUT_UNDO])
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "chevauch" in msg, d["toasts"]
    assert "20" in msg, msg
    bords = [s["box"][0] for s in d["slots"]]
    assert min(bords) == 0.0, bords


# ── R3 : LE TÉMOIN SE PINNE — l'aveu se mesure ─────────────────────────────

def test_R3_le_lasso_prend_ce_qu_il_TOUCHE_A_LA_TANGENCE_EXACTE():
    """L'AVEU ÉTAIT FAUX DE MESURE, et c'est la quatrième fois de la phase que
    la leçon se paie. J'avais déclaré la tangence « non pinnable sans dépendre
    d'un aller-retour flottant px -> mm ». `dansLasso` est une fonction PURE
    millimètres -> booléen : le harnais qui joue `aligne` et `egalise` la joue
    aussi, sans un pixel dans l'affaire.

    Trois faces tangentes d'une ligne plate posée à y = 40, x de 10 à 50 :
      · un lasso dont le BORD HAUT est exactement 40 la touche ;
      · un lasso dont le BORD BAS est exactement 40 la touche ;
      · un lasso dont le BORD GAUCHE est exactement 50 la touche.
    Et le CONTRÔLE, à un millième au-delà (40,001), ne la touche pas — sans
    lui, le test passerait aussi sur un `dansLasso` qui rend toujours vrai."""
    out = json.loads(_pures_js(
        ["dansLasso"],
        "const S={box:[10,40,40,0]};const o={};"
        "o.haut=dansLasso(S,[5,40,55,45]);"
        "o.bas=dansLasso(S,[5,35,55,40]);"
        "o.gauche=dansLasso(S,[50,35,60,45]);"
        "o.droite=dansLasso(S,[0,35,10,45]);"
        "o.hors_bas=dansLasso(S,[5,40.001,55,45]);"
        "o.hors_haut=dansLasso(S,[5,35,55,39.999]);"
        "o.hors_gauche=dansLasso(S,[50.001,35,60,45]);"
        "console.log(JSON.stringify(o));"))
    for face in ("haut", "bas", "gauche", "droite"):
        assert out[face] is True, (face, out)
    for hors in ("hors_bas", "hors_haut", "hors_gauche"):
        assert out[hors] is False, (hors, out)
    # LA MUTATION : « touche » devient « recouvre strictement ». Les quatre
    # faces tangentes basculent ; le contrôle, lui, reste faux des deux côtés.
    mut = json.loads(_node_type(
        _fonction_js_type("dansLasso")
        .replace("b[0] <= r[2] && b[0] + b[2] >= r[0]",
                 "b[0] < r[2] && b[0] + b[2] > r[0]")
        .replace("b[1] <= r[3] && b[1] + b[3] >= r[1]",
                 "b[1] < r[3] && b[1] + b[3] > r[1]")
        + "const S={box:[10,40,40,0]};const o={};"
          "o.haut=dansLasso(S,[5,40,55,45]);"
          "o.bas=dansLasso(S,[5,35,55,40]);"
          "o.gauche=dansLasso(S,[50,35,60,45]);"
          "o.hors_bas=dansLasso(S,[5,40.001,55,45]);"
          "console.log(JSON.stringify(o));"))
    assert mut["haut"] is False and mut["bas"] is False and mut["gauche"] is False, mut
    assert mut["hors_bas"] is False, \
        "le contrôle bascule avec la mutation : il ne contrôle rien"


# ── M3 : UNE SEULE RÈGLE POUR LES BLOCS MASQUÉS ────────────────────────────

def test_M3_les_gestes_de_LOT_agissent_sur_le_VISIBLE_et_le_disent(tmp_path):
    """TROIS RÈGLES POUR UNE LISTE, RAMENÉES À UNE. Le lasso écarte les blocs
    masqués (il ne peut pas les toucher), l'aimant les écarte (ils ne sont pas
    à l'écran), la barre les prenait — donc l'enveloppe d'un alignement
    comptait une boîte que personne ne voit, et un bloc éteint se déplaçait
    dans le dos de l'utilisateur.

    LA RÈGLE TRANCHÉE : les gestes de lot agissent sur le VISIBLE. Ce n'est pas
    le choix de Figma (qui déplace les masqués), et c'est délibéré : ici l'œil
    de la rangée est le seul moyen de mettre un bloc « de côté » pendant qu'on
    travaille, et le mettre de côté doit vouloir dire quelque chose.

    Vérité connue : « trois » masqué, l'enveloppe des deux visibles commence à
    10 (et non 6, qui est le bord de « trois »)."""
    lot = _lot3()
    lot[2]["on"] = False
    d = _banc_verrou(tmp_path, {
        "state": {"slots": lot, "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    par = {s["id"]: s["box"] for s in d["slots"]}
    assert par["trois"] == [6.0, 60.0, 20.0, 4.0], "un bloc masqué a bougé"
    assert par["un"][0] == 10.0 and par["deux"][0] == 10.0, \
        f"l'enveloppe a compté le bloc masqué : {par}"
    msg = " ".join(t["m"] for t in d["toasts"])
    assert "masqué" in msg, d["toasts"]
    # ... et un lot dont il ne reste qu'UN visible n'a plus rien à aligner
    lot2 = _lot3()
    lot2[1]["on"] = False
    lot2[2]["on"] = False
    v = _banc_verrou(tmp_path, {
        "state": {"slots": lot2, "sel": ["un", "deux", "trois"]},
        "actes": [{"t": "barre", "v": "left"}]},
        mutations=[MUT_UNDO])
    assert v["traces"][0]["undo"] == 0 and v["traces"][0]["patchs"] == 0, v["traces"]
    assert any("visible" in t["m"] for t in v["toasts"]), v["toasts"]


# ── 17.1 LE BANC CHROME DE LA RONDE — B1, R1, R2 en gestes réels ───────────
#
# Les trois défauts de la ronde ont été TROUVÉS dans un navigateur, sur des
# gestes que le banc de node ne jouait pas : verrouiller par le cadenas de la
# rangée, puis désigner trois blocs à la souris, puis pousser un bouton de la
# barre. C'est donc là qu'ils se pinnent — le calque, la liste et la barre
# reliés par le vrai routage d'évènements.

SONDE_RONDE = r"""(async () => {
  const out = {};
  const host = document.getElementById("cf-host");
  await window.__MOD.init(host);
  await new Promise((r) => setTimeout(r, 400));
  const attends = () => new Promise((r) => setTimeout(r, 90));
  const boxes = () => {
    const o = {};
    window.__DOC.type.slots.forEach((s) => { o[s.id] = s.box.slice(); });
    return o;
  };
  const rang = (id) => document.querySelector('.cf-type-row[data-id="' + id + '"]');
  const clic = (el, maj) => el.dispatchEvent(new MouseEvent("click",
    { bubbles: true, cancelable: true, shiftKey: !!maj }));
  const designe = async (ids) => {
    for (let i = 0; i < ids.length; i++) {
      const r = rang(ids[i]);
      if (!r) return false;
      clic(r, i > 0);
      await attends();
    }
    return true;
  };
  const barre = async (a) => {
    const b = document.querySelector('.cf-type-alg[data-a="' + a + '"]');
    if (!b) return false;
    window.__TOASTS.length = 0;
    b.click();
    await attends();
    return true;
  };

  /* B1 — LE CADENAS DE LA RANGÉE, PUIS LA BARRE */
  const cad = rang("deux").querySelector(".cf-type-lock");
  cad.click();
  await attends();
  out.verrouille = (window.__DOC.type.slots.filter((s) => s.id === "deux")[0] || {}).lock;
  out.b1_designe = await designe(["un", "deux", "trois"]);
  out.b1_barre = await barre("left");
  out.b1 = { boxes: boxes(), toasts: window.__TOASTS.slice() };

  /* R1 — UN TEXTE À HAUTEUR NULLE EN RÉFÉRENCE */
  out.r1_designe = await designe(["plat", "norm"]);
  out.r1_barre = await barre("eqh");
  out.r1 = { boxes: boxes(), toasts: window.__TOASTS.slice() };

  /* R2 — LA CARTE NORMALE : un fond, un titre, une statistique DEDANS */
  out.r2_designe = await designe(["fond", "titre", "stat"]);
  out.r2_barre = await barre("disth");
  out.r2 = { boxes: boxes(), toasts: window.__TOASTS.slice() };

  out.erreurs = window.__ERR || [];
  return out;
})()"""


def test_la_RONDE_tient_dans_un_VRAI_navigateur(tmp_path):
    """LES TROIS DÉFAUTS DE LA RONDE, REJOUÉS LÀ OÙ ILS ONT ÉTÉ TROUVÉS.

    B1 — le cadenas est posé PAR LA RANGÉE, les trois blocs sont désignés À LA
    SOURIS (clic puis Maj+clic), et « aligner à gauche » est POUSSÉ : le bloc
    verrouillé reste à 14, les deux autres tombent à 6 — c'est-à-dire sur
    l'enveloppe des TROIS, l'ancre comprise — et la phrase sort.

    R1 — un TITRE à hauteur nulle en référence : l'égalisation est refusée,
    rien n'est aplati, et le refus nomme le bloc.

    R2 — la carte normale (un fond, un titre, une stat posés dedans) : la
    distribution garde l'enveloppe (rien avant 0, le dernier ferme à 60) et
    avoue le chevauchement avec son chiffre."""
    slots = [
        TY.norm_slot({"id": "un", "label": "Un", "box": [10.0, 4.0, 30.0, 6.0],
                      "text": "1", "font": "Inter"}),
        TY.norm_slot({"id": "deux", "label": "Deux", "box": [14.0, 12.0, 12.0, 5.0],
                      "text": "2", "font": "Inter"}),
        TY.norm_slot({"id": "trois", "label": "Trois", "box": [6.0, 20.0, 20.0, 4.0],
                      "text": "3", "font": "Inter"}),
        TY.norm_slot({"id": "plat", "label": "Titre plat", "box": [10.0, 28.0, 20.0, 0.0],
                      "text": "p", "font": "Inter"}),
        TY.norm_slot({"id": "norm", "label": "Normal", "box": [10.0, 32.0, 8.0, 4.0],
                      "text": "n", "font": "Inter"}),
        TY.norm_slot({"id": "fond", "label": "Fond", "kind": "rect",
                      "box": [0.0, 40.0, 60.0, 20.0], "fill": "#f2efe9",
                      "font": "Inter"}),
        TY.norm_slot({"id": "titre", "label": "Titre", "box": [10.0, 44.0, 30.0, 8.0],
                      "text": "t", "font": "Inter"}),
        TY.norm_slot({"id": "stat", "label": "Stat", "box": [45.0, 44.0, 10.0, 8.0],
                      "text": "9", "font": "Inter"}),
    ]
    v = _chrome_gestes(tmp_path, slots, SONDE_RONDE)

    # ── B1 ───────────────────────────────────────────────────────────────
    assert v["verrouille"] is True, "le cadenas de la rangée n'a pas pris"
    assert v["b1_designe"] and v["b1_barre"], v
    b = v["b1"]["boxes"]
    assert b["deux"] == [14.0, 12.0, 12.0, 5.0], \
        f"le bloc verrouillé a bougé sous la barre : {b['deux']}"
    assert b["un"][0] == 6.0 and b["trois"][0] == 6.0, b
    msg = " ".join(v["b1"]["toasts"])
    assert "verrouill" in msg and "align" in msg, v["b1"]["toasts"]

    # ── R1 ───────────────────────────────────────────────────────────────
    assert v["r1_designe"] and v["r1_barre"], v
    r = v["r1"]["boxes"]
    assert r["norm"][3] == 4.0, f"le lot a été aplati : {r['norm']}"
    assert r["plat"][3] == 0.0, r["plat"]
    m1 = " ".join(v["r1"]["toasts"])
    assert "hauteur nulle" in m1 and "Titre plat" in m1, v["r1"]["toasts"]

    # ── R2 ───────────────────────────────────────────────────────────────
    assert v["r2_designe"] and v["r2_barre"], v
    d = v["r2"]["boxes"]
    trio = [d["fond"], d["titre"], d["stat"]]
    assert min(x[0] for x in trio) == 0.0, f"un membre part avant l'enveloppe : {trio}"
    assert d["stat"][0] + d["stat"][2] == 60.0, f"le dernier ne ferme pas : {d['stat']}"
    assert [x[0] for x in trio] == [10.0, 0.0, 50.0], trio
    m2 = " ".join(v["r2"]["toasts"])
    assert "chevauch" in m2 and "20" in m2, v["r2"]["toasts"]
