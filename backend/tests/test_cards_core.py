# -*- coding: utf-8 -*-
"""Card Forge — CORE : la géométrie AU PIXEL, le magasin de decks, le contrat.

La moitié mesurable du domaine « cartes » est ici, et elle se juge à ZÉRO
pixel de tolérance. Toutes les valeurs attendues sont ÉCRITES EN DUR
ci-dessous, relevées sur nanDECK 1.29 (la barre) et non recalculées par la
formule qu'elles sont censées vérifier — un test qui rejoue l'implémentation
ne prouve rien.

Ce qui est verrouillé :

  1. LA TOILE FAIT AUTORITÉ. `canvas_px = R((trim + 2*bleed)/25.4*dpi)`.
     La dérivation naïve `trim_px + 2*R(bleed)` donne 814 px là où le métier
     attend 815 : `test_la_toile_fait_autorite` montre les deux nombres.
  2. Les 7 formats impériaux reproduisent AU PIXEL les tailles avec fond
     perdu de nanDECK : 825x1125, 750x1125, 900x1500, 600x1125, 675x1125,
     1125x1725, 450x600.
  3. Le trait de coupe à 37,5 px reste FRACTIONNAIRE. Arrondi par mégarde,
     la carte perd un pixel et la parité tombe.
  4. Planches : A4 = 2480x3508 à 300 DPI, 4961x7016 à 600 DPI.
  5. `deck_dir` refuse la traversée (motif PUIS confinement).
  6. `meta.json` atomique, document PARTITIONNÉ, jamais de 500 sur un corps
     mal formé.
  7. `card_mesh` de référence : 3 îlots UV DISJOINTS, déterminant UV NÉGATIF
     sur tout triangle, et un compte de triangles différent de la sphère.
  8. Le routeur est réellement monté : `/api/cards/formats` répond du JSON.

Run : <embedded python> backend/tests/test_cards_core.py
"""
import asyncio
import json
import math
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
from app.services.cards import core as CC                       # noqa: E402


# ═══════════════════════ les seuils, écrits en dur ══════════════════════════
# (trim_px, canvas_px, bleed_off_px, safe_px, safe_off_px) à 300 DPI, au fond
# perdu NATIF du format et zone sûre = fond perdu.
#
# ATTENTION — CETTE TABLE NE PROUVE RIEN À ELLE SEULE. Elle est dérivée de la
# même règle que l'implémentation : elle attrape une régression, pas une règle
# fausse. C'est exactement ce qui a permis à la zone sûre de sortir 674 px là
# où 2,25 pouces valent 675 pendant que le test restait vert. Les DEUX oracles
# EXTERNES sont plus bas et ils font autorité :
#   · `test_geometrie_contre_arithmetique_exacte` — Fraction, zéro flottant,
#     millimètres ressaisis, 12 formats x 6 définitions x 5 fonds perdus x
#     4 zones sûres ;
#   · `test_parite_ecran_backend` — le bloc de formule EXTRAIT de core.js,
#     transposé mécaniquement, comparé au Python.
TABLE = {
    "poker_us":  ((750, 1050), (825, 1125), (37.5, 37.5), (675, 975), (75.0, 75.0)),
    "poker_eu":  ((744, 1039), (815, 1110), (35.5, 35.5), (673, 969), (71.0, 70.5)),
    "bridge_us": ((675, 1050), (750, 1125), (37.5, 37.5), (600, 975), (75.0, 75.0)),
    "bridge_eu": ((697, 1075), (768, 1146), (35.5, 35.5), (626, 1004), (71.0, 71.0)),
    "tarot_us":  ((825, 1425), (900, 1500), (37.5, 37.5), (750, 1350), (75.0, 75.0)),
    "tarot_eu":  ((827, 1417), (898, 1488), (35.5, 35.5), (756, 1346), (71.0, 71.0)),
    "mini":      ((520, 803),  (591, 874),  (35.5, 35.5), (449, 732),  (71.0, 71.0)),
    "square_eu": ((827, 827),  (898, 898),  (35.5, 35.5), (756, 756),  (71.0, 71.0)),
    "domino":    ((525, 1050), (600, 1125), (37.5, 37.5), (450, 975),  (75.0, 75.0)),
    "business":  ((600, 1050), (675, 1125), (37.5, 37.5), (525, 975),  (75.0, 75.0)),
    "jumbo":     ((1050, 1650), (1125, 1725), (37.5, 37.5), (975, 1575), (75.0, 75.0)),
    "micro":     ((375, 525),  (450, 600),  (37.5, 37.5), (300, 450),  (75.0, 75.0)),
}

# Les tailles AVEC FOND PERDU relevées sur nanDECK 1.29. Sept formats.
NANDECK = {
    "poker_us": (825, 1125), "bridge_us": (750, 1125), "tarot_us": (900, 1500),
    "domino": (600, 1125), "business": (675, 1125), "jumbo": (1125, 1725),
    "micro": (450, 600),
}

# Planches : (150 DPI, 300 DPI, 600 DPI)
PLANCHES = {
    "a4":     ((1240, 1754), (2480, 3508), (4961, 7016)),
    "letter": ((1275, 1650), (2550, 3300), (5100, 6600)),
    "a3":     ((1754, 2480), (3508, 4961), (7016, 9921)),
}


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


# ═══════════════════ 1. la géométrie, à zéro pixel près ═════════════════════

@pytest.mark.parametrize("fmt", list(TABLE))
def test_geometrie_au_pixel(fmt):
    """Chaque format contre sa ligne de la table. Tolérance : 0 pixel."""
    trim, canvas, boff, safe, soff = TABLE[fmt]
    g = CT.geom(fmt, 300)
    assert g.trim_px == trim, f"{fmt}: rogne {g.trim_px} au lieu de {trim}"
    assert g.canvas_px == canvas, \
        f"{fmt}: toile {g.canvas_px} au lieu de {canvas}"
    assert g.bleed_off_px == boff, \
        f"{fmt}: décalage de fond perdu {g.bleed_off_px} au lieu de {boff}"
    assert g.safe_px == safe, f"{fmt}: zone sûre {g.safe_px} au lieu de {safe}"
    assert g.safe_off_px == soff, \
        f"{fmt}: décalage de zone sûre {g.safe_off_px} au lieu de {soff}"


# ── ORACLE EXTERNE n°1 : l'arithmétique exacte ──────────────────────────────

def _px_exact(mm: str, dpi: int) -> int:
    """R(mm/25.4*dpi) en rationnels EXACTS. Aucun flottant : pas de 37.4999."""
    return math.floor(Fraction(mm) / Fraction("25.4") * dpi + Fraction(1, 2))


def _mmf(v) -> str:
    """Millimètres -> chaîne décimale exacte (Fraction(str) est exact)."""
    return format(Fraction(str(v)), "")


@pytest.mark.parametrize("fmt", list(TABLE))
def test_geometrie_contre_arithmetique_exacte(fmt):
    """LE vrai oracle : la règle, réécrite en arithmétique exacte, sur toute
    la plage utile. Aucune valeur n'est recopiée de l'implémentation.

    C'est ce test-ci qui aurait attrapé la zone sûre calculée en DEUX
    conversions : `micro` a une zone sûre de 1 x 1,5 pouce EXACT, donc
    300 x 450 px ; l'ancienne dérivation servait 299 x 449 (et jusqu'à
    +1,18 px de trop sur les formats métriques, donc du texte hors zone sûre
    qui passait le contrôle avant vol de P7)."""
    W, H = (Fraction(str(v)) for v in CT.FORMATS[fmt]["trim_mm"])
    for dpi in (72, 96, 150, 300, 600, 1200):
        for bleed in ("0", "3", "3.175", "5.5", "10"):
            for safe in ("0", "1.5", "3.175", "10"):
                g = CT.geom(fmt, dpi, float(Fraction(bleed)),
                            float(Fraction(safe)))
                b, s = Fraction(bleed), Fraction(safe)
                trim = (_px_exact(_mmf(W), dpi), _px_exact(_mmf(H), dpi))
                canvas = (_px_exact(_mmf(W + 2 * b), dpi),
                          _px_exact(_mmf(H + 2 * b), dpi))
                safe_px = (_px_exact(_mmf(W - 2 * s), dpi),
                           _px_exact(_mmf(H - 2 * s), dpi))
                boff = ((canvas[0] - trim[0]) / 2, (canvas[1] - trim[1]) / 2)
                soff = (boff[0] + (trim[0] - safe_px[0]) / 2,
                        boff[1] + (trim[1] - safe_px[1]) / 2)
                ctx = f"{fmt} dpi={dpi} bleed={bleed} safe={safe}"
                assert g.trim_px == trim, ctx
                assert g.canvas_px == canvas, ctx
                assert g.safe_px == safe_px, ctx
                assert g.bleed_off_px == boff, ctx
                assert g.safe_off_px == soff, ctx


def test_une_seule_conversion_par_longueur():
    """La règle en une phrase : une même longueur donne un même nombre de
    pixels, où qu'elle apparaisse. L'ancienne zone sûre produisait TROIS
    collisions dans une seule réponse de /formats — 57,15 mm valait 675 px
    (rogne `bridge_us`) ET 674 px (zone sûre `poker_us`)."""
    G = {f: CT.geom(f, 300) for f in CT.FORMATS}
    # (longueur en mm, d'où elle vient comme rogne, d'où elle vient comme
    #  zone sûre) : les trois collisions historiques.
    for mm, a, b in ((57.15, "bridge_us", "poker_us"),
                     (63.5, "poker_us", "tarot_us"),
                     (50.8, "business", "bridge_us")):
        rogne = G[a].trim_px[0]
        zone = G[b].safe_px[0]
        assert rogne == zone == CT.px(mm, 300), \
            f"{mm} mm : rogne {a}={rogne} vs zone sûre {b}={zone}"
    # et les deux insets d'une longueur commune sont égaux
    g = CT.geom("poker_us", 300)
    assert g.bleed_mm == g.safe_mm
    assert g.bleed_off_px[0] == g.safe_off_px[0] - g.bleed_off_px[0] == 37.5


def test_zone_sure_micro_vaut_un_pouce_et_demi():
    """1,25 - 2*0,125 = 1 pouce ; 1,75 - 2*0,125 = 1,5 pouce. À 300 DPI, cela
    ne peut valoir que 300 x 450 px."""
    g = CT.geom("micro", 300)
    assert (g.trim_mm[0] - 2 * g.safe_mm) / 25.4 == 1.0
    assert g.safe_px == (300, 450)
    assert CT.geom("micro", 600).safe_px == (600, 900)


def test_les_douze_formats_sont_livres():
    """La table de la spec en compte douze. Pas onze."""
    assert list(CT.FORMATS) == list(TABLE)
    assert len(CT.FORMATS) == 12


@pytest.mark.parametrize("fmt", list(NANDECK))
def test_parite_nandeck(fmt):
    """Les sept formats impériaux, au pixel, contre la barre."""
    assert CT.geom(fmt, 300).canvas_px == NANDECK[fmt]


def test_la_toile_fait_autorite():
    """LE piège de la spec, montré des deux côtés.

    `poker_eu` : rogne 744 px, fond perdu 3 mm. La dérivation naïve
    744 + 2*R(3 mm) = 744 + 70 = 814. Le métier attend 815 — et c'est la
    conversion de (63 + 2*3) mm d'un seul bloc qui le donne."""
    g = CT.geom("poker_eu", 300)
    naif = g.trim_px[0] + 2 * CT.px(g.bleed_mm, 300)
    assert naif == 814, "la dérivation naïve doit bien donner 814"
    assert g.canvas_px[0] == 815, "la toile fait autorité : 815"
    assert g.canvas_px[0] - naif == 1, "un pixel, sur chaque format impérial"
    naif_v = g.trim_px[1] + 2 * CT.px(g.bleed_mm, 300)
    assert naif_v == 1109 and g.canvas_px[1] == 1110


def test_le_demi_pixel_reste_fractionnaire():
    """37,5 px n'est PAS 37 ni 38. Arrondi, la carte perd un pixel."""
    for fmt in NANDECK:
        g = CT.geom(fmt, 300)
        assert g.bleed_off_px == (37.5, 37.5), fmt
        assert isinstance(g.bleed_off_px[0], float)
        assert g.bleed_off_px[0] != int(g.bleed_off_px[0])


def test_arrondi_demi_haut():
    """R(x) = floor(x + 0.5) : 0,5 monte, et il monte pour de vrai en
    flottant (3,175 mm à 300 DPI vaut EXACTEMENT 37,5 px)."""
    assert CT.R(0.5) == 1 and CT.R(1.5) == 2 and CT.R(-0.5) == 0
    assert CT.R(2.4999) == 2 and CT.R(2.5) == 3
    assert CT.px(3.175, 300) == 38, "37,5 px doit monter à 38, pas tomber à 37"
    assert CT.px(3.0, 300) == 35


def test_le_dpi_est_reellement_applique():
    """Mêmes millimètres, trois résolutions. Valeurs exactes : 2,5 in à
    150/300/600 DPI = 375/750/1500 px, pas d'approximation possible."""
    assert CT.geom("poker_us", 150).trim_px == (375, 525)
    assert CT.geom("poker_us", 300).trim_px == (750, 1050)
    assert CT.geom("poker_us", 600).trim_px == (1500, 2100)
    assert CT.geom("poker_us", 600).canvas_px == (1650, 2250)
    # 2,75 in à 150 DPI = 412,5 px : la toile monte à 413.
    assert CT.geom("poker_us", 150).canvas_px == (413, 563)


@pytest.mark.parametrize("sheet", list(PLANCHES))
def test_planches_au_pixel(sheet):
    p150, p300, p600 = PLANCHES[sheet]
    assert CT.sheet_px(sheet, 150) == p150
    assert CT.sheet_px(sheet, 300) == p300
    assert CT.sheet_px(sheet, 600) == p600


def test_a4_300_et_600():
    """Les deux chiffres cités nommément par la spec."""
    assert CT.sheet_px("a4", 300) == (2480, 3508)
    assert CT.sheet_px("a4", 600) == (4961, 7016)


# ═══════════════════ 2. fond perdu, zone sûre, bornes ═══════════════════════

def test_fond_perdu_natif_par_systeme():
    """Métrique -> 3 mm ; impérial -> 0.125 in = 3,175 mm."""
    assert CT.native_bleed_mm("poker_eu") == 3.0
    assert CT.native_bleed_mm("poker_us") == 3.175
    for fid, meta in CT.FORMATS.items():
        attendu = 3.175 if meta["unit"] == "in" else 3.0
        assert CT.geom(fid, 300).bleed_mm == attendu, fid


def test_zone_sure_par_defaut_egale_le_fond_perdu():
    for fid in CT.FORMATS:
        g = CT.geom(fid, 300)
        assert g.safe_mm == g.bleed_mm, fid


def test_fond_perdu_et_zone_sure_sont_reglables():
    g = CT.geom("poker_eu", 300, bleed_mm=0.0, safe_mm=0.0)
    assert g.canvas_px == g.trim_px == (744, 1039)
    assert g.bleed_off_px == (0.0, 0.0)
    assert g.safe_px == (744, 1039)
    g10 = CT.geom("poker_eu", 300, bleed_mm=10.0, safe_mm=10.0)
    # 63 + 20 = 83 mm -> R(980.31) = 980 ; 88 + 20 = 108 -> R(1275.59) = 1276
    assert g10.canvas_px == (980, 1276)


def test_entrees_hors_liste_blanche():
    """Toujours ValueError, jamais autre chose — l'appelant HTTP en fait
    un 400 et le message énumère la liste blanche."""
    with pytest.raises(ValueError) as e:
        CT.geom("poker_xx", 300)
    assert "poker_eu" in str(e.value), "le message doit énumérer les formats"
    for mauvais in (None, "", "../etc", 12):
        with pytest.raises(ValueError):
            CT.geom(mauvais, 300)
    for dpi in (0, 71, 1201, "beaucoup", None):
        with pytest.raises(ValueError):
            CT.geom("poker_eu", dpi)
    for bl in (-1.0, 10.1, float("nan"), "épais"):
        with pytest.raises(ValueError):
            CT.geom("poker_eu", 300, bleed_mm=bl)
    with pytest.raises(ValueError):
        CT.sheet_px("a5", 300)


def test_signature_gelee_de_cardgeom():
    """Les onze champs de la spec 2.4, dans l'ordre. Un champ de plus et
    tous les appels positionnels des pièces cassent."""
    import dataclasses
    noms = [f.name for f in dataclasses.fields(CT.CardGeom)]
    assert noms == ["fmt", "dpi", "trim_mm", "bleed_mm", "safe_mm",
                    "corner_mm", "trim_px", "canvas_px", "bleed_off_px",
                    "safe_px", "safe_off_px"]
    g = CT.geom("poker_eu", 300)
    with pytest.raises(dataclasses.FrozenInstanceError):
        g.trim_px = (1, 1)
    # les commodités sont des propriétés, elles n'entrent pas dans la signature
    assert g.label == "Poker 63 x 88 mm" and g.unit == "mm"
    assert g.corner_px == 35.4


# ── ORACLE EXTERNE n°2 : l'écran, extrait de core.js ────────────────────────
# La formule vit des deux côtés parce que le rendu navigateur est synchrone et
# ne peut pas attendre le réseau. Le risque est qu'elles DÉRIVENT. core.js
# annonçait ce harnais depuis le premier jour ; il n'existait pas, et la parité
# écran/backend — que la spec appelle la promesse du contrat — n'était affirmée
# que par un commentaire. Ici on lit le VRAI fichier, on en extrait le bloc
# encadré, on le transpose MÉCANIQUEMENT et on compare les deux sorties.

CORE_JS = (pathlib.Path(__file__).resolve().parent.parent.parent
           / "frontend" / "cardforge" / "js" / "core.js")


def _bloc_js(nom: str) -> str:
    src = CORE_JS.read_text(encoding="utf-8")
    # entre les deux LIGNES de marqueur, exclues : ce qui reste est du code.
    m = re.search(r"CF-GEOM-FORMULA-BEGIN[^\n]*\n(.*?)\n[^\n]*CF-GEOM-FORMULA-END",
                  src, re.S)
    assert m, "bloc CF-GEOM-FORMULA introuvable dans core.js"
    return m.group(1)


def _transpose(js: str) -> str:
    """JS -> Python, ligne à ligne, sans interpréter : si le bloc cesse d'être
    transposable, le test ROUGIT — c'est voulu, il doit rester le miroir
    littéral de `contract.geom`, pas un programme."""
    out = []
    for raw in js.strip().splitlines():
        s = raw.strip()
        if not s or s.startswith("/*") or s.startswith("//") or s.startswith("*"):
            continue
        s = s.rstrip(";")
        m = re.match(r"const (\w+) = \((.*?)\) => (.*)$", s)
        if m:
            out.append("def %s(%s): return %s" % m.groups())
            continue
        m = re.match(r"const (\w+) = \[(.*)\]$", s)
        if m:
            out.append("%s = (%s)" % m.groups())
            continue
        raise AssertionError("ligne non transposable dans core.js : " + raw)
    py = "\n".join(out)
    py = py.replace("Math.floor(", "math.floor(")
    py = re.sub(r"Number\((\w+)\.toFixed\((\d+)\)\)", r"round(\1, \2)", py)
    assert "Math." not in py and "=>" not in py, py
    return py


def _formats_js() -> list:
    """La table FORMATS recopiée à la main dans core.js, relue telle quelle."""
    src = CORE_JS.read_text(encoding="utf-8")
    rows = re.findall(
        r'\{\s*id:\s*"([^"]+)",\s*label:\s*"([^"]*)",\s*unit:\s*"(\w+)",'
        r'\s*trim_mm:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]\s*\}', src)
    return [(i, lab, u, (float(w), float(h))) for i, lab, u, w, h in rows]


def test_la_table_des_formats_est_la_meme_des_deux_cotes():
    """La table est RECOPIÉE entre contract.py et core.js — libellés compris.
    Une recopie que personne ne vérifie finit par diverger ; celle-ci est
    vérifiée."""
    js = _formats_js()
    assert len(js) == 12, f"12 formats attendus dans core.js, {len(js)} lus"
    py = [(f, m["label"], m["unit"], tuple(m["trim_mm"]))
          for f, m in CT.FORMATS.items()]
    assert js == py, "core.js et contract.py ne décrivent pas les mêmes formats"


def test_parite_ecran_backend():
    """Le bloc de core.js, transposé, contre `contract.geom` : 12 formats x
    6 définitions x 5 fonds perdus x 4 zones sûres = 1440 géométries, 5 champs
    de pixels chacune. Tolérance : 0 pixel."""
    src = _transpose(_bloc_js("CF-GEOM-FORMULA"))
    n = 0
    for fmt, meta in CT.FORMATS.items():
        w_mm, h_mm = meta["trim_mm"]
        for dpi in (72, 96, 150, 300, 600, 1200):
            for bleed_mm in (0.0, 3.0, 3.175, 5.5, 10.0):
                for safe_mm in (0.0, 1.5, 3.175, 10.0):
                    ns = {"math": math, "w_mm": w_mm, "h_mm": h_mm,
                          "dpi": dpi, "bleed_mm": bleed_mm, "safe_mm": safe_mm}
                    exec(src, ns)                       # noqa: S102 — c'est le sujet
                    g = CT.geom(fmt, dpi, bleed_mm, safe_mm)
                    ctx = f"{fmt} dpi={dpi} bleed={bleed_mm} safe={safe_mm}"
                    assert g.trim_px == ns["trim_px"], ctx
                    assert g.canvas_px == ns["canvas_px"], ctx
                    assert g.bleed_off_px == ns["bleed_off_px"], ctx
                    assert g.safe_px == ns["safe_px"], ctx
                    assert g.safe_off_px == ns["safe_off_px"], ctx
                    n += 1
    assert n == 12 * 6 * 5 * 4


def test_l_arrondi_d_affichage_est_le_meme_des_deux_cotes():
    """`round()` de Python est un arrondi AU PAIR : round(0.0625, 3) = 0.062
    quand l'écran (Math.round) affiche 0.063, et round(1.25, 1) = 1.2 quand
    l'écran affiche 1.3. Deux règles pour le même travail dans un fichier qui
    se déclare miroir exact : `contract.rnd` est le demi-haut de core.js."""
    assert CT.rnd(0.0625, 3) == 0.063 and round(0.0625, 3) == 0.062
    assert CT.rnd(1.25, 1) == 1.3 and round(1.25, 1) == 1.2
    assert CT.rnd(3.175, 3) == 3.175 and CT.rnd(35.43307086, 1) == 35.4
    # et il est bien BRANCHÉ : corner_mm=0,25 à 127 DPI -> 1.25 px -> 1.3
    assert CT.geom("poker_eu", 127, corner_mm=0.25).corner_px == 1.3
    assert CT.geom("poker_eu", 300, bleed_mm=0.0625).to_dict()["bleed_mm"] \
        == 0.063


def test_to_dict_sert_les_pixels_tels_quels():
    d = CT.geom("poker_us", 300).to_dict()
    assert d["canvas_px"] == [825, 1125] and d["trim_px"] == [750, 1050]
    assert d["bleed_off_px"] == [37.5, 37.5]
    assert d["safe_px"] == [675, 975]
    assert d["safe_off_px"] == [75.0, 75.0]
    assert json.loads(json.dumps(d))["canvas_px"] == [825, 1125]


# ═══════════════════ 3. le magasin de decks ═════════════════════════════════

def test_deck_dir_refuse_la_traversee():
    """Motif PUIS confinement. Aucune de ces entrées ne doit produire un
    chemin."""
    for mauvais in ("..", "../..", "deck_../../x", "deck_XXXXXXXX",
                    "deck_0000000", "deck_000000000", "mat_a1b2c3d4",
                    "deck_a1b2c3d4/../..", "C:/windows", "", None, 42,
                    "deck_a1b2c3d4\x00"):
        with pytest.raises(ValueError):
            CT.deck_dir(mauvais)
        assert CT.is_valid_did(mauvais) is False
    assert CT.is_valid_did("deck_a1b2c3d4") is True
    p = CT.deck_dir("deck_a1b2c3d4")
    assert str(p).startswith(str(CT.decks_root().resolve()))


def test_meta_json_est_ecrit_atomiquement():
    doc = CC.create_deck("Jeu témoin")
    d = CT.deck_dir(doc["id"])
    assert (d / "meta.json").is_file()
    assert not (d / "meta.json.tmp").exists(), "aucun temporaire ne survit"
    relu = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    assert relu["id"] == doc["id"] and relu["name"] == "Jeu témoin"


def test_un_meta_json_abime_se_repare():
    """Un document tronqué (autosave interrompue) ne doit pas faire tomber
    l'ouverture : il se normalise."""
    doc = CC.create_deck("cassé")
    d = CT.deck_dir(doc["id"])
    (d / "meta.json").write_text("{ pas du json", encoding="utf-8")
    relu = CC.read_deck(doc["id"])
    assert relu is not None
    assert relu["format"]["fmt"] == CT.DEFAULT_FMT
    assert set(CT.MODULE_IDS).issubset(relu)


def test_le_document_est_partitionne():
    """Un sous-arbre par pièce, et RIEN d'autre : une clé étrangère est
    jetée, sinon deux pièces finiraient par se marcher dessus."""
    doc = CC.create_deck("partition")
    assert [k for k in CT.MODULE_IDS if k not in doc] == []
    assert all(doc[k] == {} for k in CT.MODULE_IDS)
    sale = CC.patch_deck(doc["id"], {
        "face": {"art_fit": "cover"},
        "solid": {"thickness_mm": 0.32},
        "id": "deck_ffffffff",          # jamais repris du client
        "v": 99,
        "intrus": {"x": 1},             # jeté
    })
    assert sale["face"] == {"art_fit": "cover"}
    assert sale["solid"] == {"thickness_mm": 0.32}
    assert sale["id"] == doc["id"], "l'id ne vient jamais du corps"
    assert sale["v"] == CC.DOC_VERSION
    assert "intrus" not in sale


def test_le_magasin_ne_leve_jamais_sur_une_entree_pourrie():
    doc = CC.create_deck("robuste")
    for corps in (None, {}, [], "texte", 7, {"format": "poker"},
                  {"format": {"fmt": "../x", "dpi": "beaucoup"}},
                  {"face": "pas un dict"}, {"name": None}):
        out = CC.patch_deck(doc["id"], corps if isinstance(corps, dict) else None)
        assert out is not None and out["id"] == doc["id"]
    assert CC.read_deck(doc["id"])["format"]["fmt"] in CT.FORMATS
    assert CC.read_deck("deck_deadbeef") is None
    assert CC.patch_deck("deck_deadbeef", {}) is None
    assert CC.delete_deck("pas un did") is False


def test_un_patch_partiel_du_format_ne_change_pas_le_format():
    """« Fusion PARTIELLE » veut dire qu'une clé absente n'est pas touchée.
    Mesuré avant correction : un deck `tarot_us` (toile 900x1500) recevait
    `{"format":{"dpi":600}}` et revenait à `poker_eu` SANS UN MOT — /geom
    servait 1630x2220 au lieu de 1800x3000. `normalize_format` repartait de
    `default_format()`, donc `fmt` absent voulait dire poker_eu."""
    doc = CC.create_deck("partiel", fmt={"fmt": "tarot_us"})
    did = doc["id"]
    assert CC.geom_of(doc).canvas_px == (900, 1500)

    out = CC.patch_deck(did, {"format": {"dpi": 600}})
    assert out["format"]["fmt"] == "tarot_us", "le format ne bouge pas"
    assert out["format"]["dpi"] == 600
    assert out["format"]["bleed_mm"] == 3.175, "ni le fond perdu"
    assert CC.geom_of(out).canvas_px == (1800, 3000)

    # un bloc `format` illisible ne remet rien à zéro
    for pourri in ("pas un objet", None, [1, 2], 7):
        out = CC.patch_deck(did, {"format": pourri})
        assert out["format"]["fmt"] == "tarot_us" and out["format"]["dpi"] == 600

    # une valeur hors bornes reprend l'ancienne, pas le défaut d'usine
    out = CC.patch_deck(did, {"format": {"dpi": 99999, "bleed_mm": -3}})
    assert out["format"]["dpi"] == 600 and out["format"]["bleed_mm"] == 3.175

    # mais changer de format reprend bien son fond perdu NATIF
    out = CC.patch_deck(did, {"format": {"fmt": "poker_eu"}})
    assert out["format"]["bleed_mm"] == 3.0 and out["format"]["dpi"] == 600
    CC.delete_deck(did)


def test_un_sous_arbre_absent_ou_mal_forme_survit():
    """Le cœur du « dernier merge gagne en silence », côté disque : deux
    onglets (ou deux des huit builders) sur le même jeu. Un PATCH qui ne parle
    pas de `face` ne doit pas vider `face` ; un `{"face": null}` non plus."""
    doc = CC.create_deck("deux onglets")
    did = doc["id"]
    CC.patch_deck(did, {"face": {"fit": "travail-onglet-A"}})
    # l'onglet B enregistre SON sous-arbre, sans un mot sur face
    out = CC.patch_deck(did, {"frame": {"family": "travail-onglet-B"}})
    assert out["face"] == {"fit": "travail-onglet-A"}, "A a été effacé"
    assert out["frame"] == {"family": "travail-onglet-B"}
    # un sous-arbre mal formé est IGNORÉ, pas appliqué
    for pourri in (None, "texte", [1], 7):
        out = CC.patch_deck(did, {"face": pourri})
        assert out["face"] == {"fit": "travail-onglet-A"}, pourri
    # pour vider, on envoie {} — explicitement
    out = CC.patch_deck(did, {"face": {}})
    assert out["face"] == {}
    CC.delete_deck(did)


def test_liste_et_suppression():
    avant = {d["id"] for d in CC.list_decks()}
    a = CC.create_deck("A")
    assert a["id"] in {d["id"] for d in CC.list_decks()}
    assert CC.delete_deck(a["id"]) is True
    apres = {d["id"] for d in CC.list_decks()}
    assert a["id"] not in apres and avant.issubset(apres | avant)


def test_geom_du_document():
    doc = CC.create_deck("géom", fmt={"fmt": "poker_us", "dpi": 600})
    g = CC.geom_of(doc)
    assert g.fmt == "poker_us" and g.dpi == 600
    assert g.canvas_px == (1650, 2250)


# ═══════════════════ 4. le maillage de référence ════════════════════════════

def _tris(mesh):
    idx, uv = mesh["indices"], mesh["uvs"]
    for t in range(0, len(idx), 3):
        yield [(uv[idx[t + k] * 2], uv[idx[t + k] * 2 + 1]) for k in range(3)]


def test_card_mesh_a_la_forme_de_build_mesh():
    m = CT.card_mesh(CT.geom("poker_eu", 300), {"thickness_mm": 0.32})
    assert set(m) == {"name", "positions", "normals", "uvs", "indices",
                      "tangents"}
    assert m["name"] == "card"
    n = len(m["positions"]) // 3
    assert len(m["normals"]) == n * 3
    assert len(m["uvs"]) == n * 2
    assert len(m["tangents"]) == n * 4
    assert len(m["indices"]) % 3 == 0
    assert max(m["indices"]) < n


def test_determinant_uv_negatif_sur_tout_triangle():
    """L'INVARIANT. Un seul triangle à déterminant positif et le texte de la
    carte se lit EN MIROIR dans le viewport (cf. test_uv_orientation)."""
    m = CT.card_mesh(CT.geom("poker_eu", 300), {})
    fautifs = []
    for i, (t0, t1, t2) in enumerate(_tris(m)):
        det = ((t1[0] - t0[0]) * (t2[1] - t0[1])
               - (t2[0] - t0[0]) * (t1[1] - t0[1]))
        if det >= 0.0:
            fautifs.append((i, det))
    assert not fautifs, f"{len(fautifs)} triangles en miroir : {fautifs[:3]}"


def test_trois_ilots_uv_disjoints():
    """Recto, verso, tranche : aucun triangle de l'un ne tombe dans la boîte
    d'un autre. Sinon la face imprimée baverait sur la tranche."""
    boites = {k: v for k, v in CT.UV_ISLANDS.items()}
    m = CT.card_mesh(CT.geom("poker_eu", 300), {})
    compte = {k: 0 for k in boites}
    for i, tri in enumerate(_tris(m)):
        dedans = [k for k, (u0, v0, u1, v1) in boites.items()
                  if all(u0 - 1e-9 <= u <= u1 + 1e-9
                         and v0 - 1e-9 <= v <= v1 + 1e-9 for u, v in tri)]
        assert len(dedans) == 1, f"triangle {i} dans {dedans} îlot(s)"
        compte[dedans[0]] += 1
    # Le triplet {2, 2, 8} était celui du bouchon de référence. Ce qui compte
    # est que les TROIS îlots soient réellement peuplés et qu'aucun triangle ne
    # se perde : le reste dépend du nombre de segments d'arrondi, réglable.
    assert set(compte) == {"front", "back", "edge"}
    assert all(n > 0 for n in compte.values()), f"îlot vide : {compte}"
    assert sum(compte.values()) == len(m["indices"]) // 3
    noms = list(boites)
    for i in range(len(noms)):
        for j in range(i + 1, len(noms)):
            a, b = boites[noms[i]], boites[noms[j]]
            chevauche = (a[0] < b[2] and b[0] < a[2]
                         and a[1] < b[3] and b[1] < a[3])
            assert not chevauche, f"{noms[i]} et {noms[j]} se recouvrent"


def test_le_maillage_carte_n_est_pas_une_sphere():
    """Piège n°9 : `gltf_builder` rend une SPHÈRE sans un mot si le nom du
    maillage lui est inconnu. Le compte de triangles est la preuve."""
    from app.services.gltf_builder import mesh_stats
    m = CT.card_mesh(CT.geom("poker_eu", 300), {})
    tri_carte = len(m["indices"]) // 3
    # Ce test portait le compte du BOUCHON de référence (12 triangles) tant que
    # la coquille était gelée. La pièce 05 a livré le vrai maillage : on vérifie
    # désormais la PROPRIÉTÉ que le piège menace, pas le chiffre d'un jour.
    assert tri_carte >= 12, f"maillage carte dégénéré : {tri_carte} triangles"
    assert tri_carte != mesh_stats("sphere")["triangles"],         "gltf_builder est retombé sur la sphère sans le dire"
    assert m["name"] != "sphere"
    # le repli silencieux se prouve aussi par la boîte englobante : une sphère
    # unité est cubique, une carte est plate.
    zs = m["positions"][2::3]
    xs = m["positions"][0::3]
    assert (max(zs) - min(zs)) < (max(xs) - min(xs)) / 10,         "l'objet n'est pas plat : ce n'est pas une carte"


def test_les_proportions_physiques_sont_respectees():
    """63 x 88 x 0,32 mm : le rapport largeur/hauteur et l'épaisseur relative
    doivent se retrouver dans le maillage."""
    g = CT.geom("poker_eu", 300)
    m = CT.card_mesh(g, {"thickness_mm": 0.32})
    xs = m["positions"][0::3]
    ys = m["positions"][1::3]
    zs = m["positions"][2::3]
    lx, ly, lz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    assert abs(ly - 2.0) < 1e-9, "demi-hauteur = 1, comme les six maillages"
    assert abs(lx / ly - 63.0 / 88.0) < 1e-9
    assert abs(lz / ly - 0.32 / 88.0) < 1e-9


def test_epaisseur_bornee_et_defaut():
    g = CT.geom("poker_eu", 300)
    for entree, attendu in (({}, 0.32), ({"thickness_mm": 0.05}, 0.20),
                            ({"thickness_mm": 9.0}, 1.20),
                            ({"thickness_mm": "épais"}, 0.32),
                            (None, 0.32)):
        m = CT.card_mesh(g, entree)
        zs = m["positions"][2::3]
        ep = (max(zs) - min(zs)) / (2.0 / 88.0)
        assert abs(ep - attendu) < 1e-9, f"{entree} -> {ep}"


# ═══════════════════ 5. le routeur est réellement monté ═════════════════════

def test_api_formats_repond_du_json_pas_du_html():
    """Piège n°7 de la spec : sans le montage, la SPA répond du HTML en
    cascade et l'écran a l'air « cassé »."""
    r = _api("GET", "/api/cards/formats")
    assert r.status_code == 200, r.text
    assert "application/json" in r.headers.get("content-type", "")
    assert not r.text.lstrip().startswith("<"), "du HTML = le catch-all SPA"
    body = r.json()
    assert len(body["formats"]) == 12
    par_id = {f["fmt"]: f for f in body["formats"]}
    assert par_id["poker_us"]["canvas_px"] == [825, 1125]
    assert par_id["poker_us"]["trim_px"] == [750, 1050]
    assert par_id["poker_eu"]["canvas_px"] == [815, 1110]
    a4 = [s for s in body["sheets"] if s["id"] == "a4"][0]
    assert a4["px"]["300"] == [2480, 3508] and a4["px"]["600"] == [4961, 7016]
    assert body["dpis"] == [150, 300, 600]


def test_api_cycle_de_vie_d_un_deck():
    r = _api("POST", "/api/cards/decks", json={"name": "Duel"})
    assert r.status_code == 200, r.text
    did = r.json()["deck"]["id"]
    assert CT.DID_RE.match(did)

    r = _api("GET", f"/api/cards/{did}/geom")
    assert r.status_code == 200
    assert r.json()["geom"]["canvas_px"] == [815, 1110]

    # Aperçu d'un autre format sans l'enregistrer. Changer de format REPREND
    # son fond perdu natif (impérial = 0.125 in) : sans cela l'aperçu
    # garderait les 3 mm métriques et sortirait 821x1121.
    r = _api("GET", f"/api/cards/{did}/geom", params={"fmt": "poker_us"})
    assert r.json()["geom"]["canvas_px"] == [825, 1125]
    assert r.json()["geom"]["bleed_mm"] == 3.175
    # ...mais un fond perdu passé EXPLICITEMENT reste prioritaire.
    r = _api("GET", f"/api/cards/{did}/geom",
             params={"fmt": "poker_us", "bleed_mm": 3.0})
    assert r.json()["geom"]["canvas_px"] == [821, 1121]
    assert _api("GET", f"/api/cards/{did}").json()["deck"]["format"]["fmt"] \
        == "poker_eu", "l'aperçu n'écrit rien"

    r = _api("PATCH", f"/api/cards/{did}",
             json={"format": {"fmt": "tarot_us", "dpi": 600},
                   "type": {"slots": []}})
    assert r.status_code == 200
    assert r.json()["deck"]["format"]["fmt"] == "tarot_us"
    assert _api("GET", f"/api/cards/{did}/geom").json()["geom"]["dpi"] == 600

    assert did in [d["id"] for d in _api("GET", "/api/cards/decks").json()["decks"]]
    assert _api("DELETE", f"/api/cards/{did}").json() == {"ok": True}
    assert _api("GET", f"/api/cards/{did}").status_code == 404


def test_api_erreurs_parlantes():
    assert _api("GET", "/api/cards/pas-un-did").status_code == 400
    assert _api("GET", "/api/cards/deck_deadbeef").status_code == 404
    assert _api("GET", "/api/cards/deck_deadbeef/geom").status_code == 404
    did = _api("POST", "/api/cards/decks", json={}).json()["deck"]["id"]
    r = _api("GET", f"/api/cards/{did}/geom", params={"fmt": "poker_xx"})
    assert r.status_code == 400 and "poker_eu" in r.json()["detail"]
    # un corps mal formé ne fait JAMAIS 500
    for corps in ({"format": "poker"}, {"face": 7}, {"name": None}, {}):
        assert _api("PATCH", f"/api/cards/{did}", json=corps).status_code == 200
    assert _api("PATCH", f"/api/cards/{did}", content=b"{pas du json").status_code < 500


def test_aucun_500_sur_un_corps_mal_forme():
    """Spec 2.5, mot pour mot : « un corps mal formé ne doit JAMAIS faire
    500 ». `json.loads("1e999")` rend `float('inf')`, `int(inf)` lève
    OverflowError — trois mots manquaient à un `except` et PATCH comme POST
    rendaient 500 Internal Server Error."""
    did = _api("POST", "/api/cards/decks", json={}).json()["deck"]["id"]
    corps = [b'{"format":{"dpi":1e999}}', b'{"format":{"dpi":-1e999}}',
             b'{"format":{"dpi":1e999,"bleed_mm":1e999}}',
             b'{"format":{"dpi":"beaucoup"}}', b'{"format":{"dpi":[1,2]}}',
             b'{"name":123456}', b'{"face":null}', b'[]', b'"texte"',
             b'{"format":{"bleed_mm":1e999,"safe_mm":-1e999}}']
    for c in corps:
        r = _api("PATCH", f"/api/cards/{did}", content=c,
                 headers={"Content-Type": "application/json"})
        assert r.status_code < 500, f"{c!r} -> {r.status_code} {r.text[:120]}"
        r = _api("POST", "/api/cards/decks", content=c,
                 headers={"Content-Type": "application/json"})
        assert r.status_code < 500, f"POST {c!r} -> {r.status_code}"
    # le deck reste ouvrable et sain
    f = _api("GET", f"/api/cards/{did}").json()["deck"]["format"]
    assert f["fmt"] in CT.FORMATS and CT.DPI_MIN <= f["dpi"] <= CT.DPI_MAX
    _api("DELETE", f"/api/cards/{did}")


def test_les_parametres_de_geom_repondent_400_en_francais():
    """Typés `int`/`float`, FastAPI rendait 422 + une charge pydantic EN
    ANGLAIS là où la spec 2.5 impose 400 et une phrase en français."""
    did = _api("POST", "/api/cards/decks", json={}).json()["deck"]["id"]
    for qs, mot in (({"dpi": "abc"}, "DPI"), ({"bleed_mm": "épais"}, "fond perdu"),
                    ({"safe_mm": "1e999"}, "sécurité"), ({"dpi": "1e999"}, "DPI"),
                    ({"corner_mm": "x"}, "rayon")):
        r = _api("GET", f"/api/cards/{did}/geom", params=qs)
        assert r.status_code == 400, f"{qs} -> {r.status_code}"
        assert mot in r.json()["detail"], r.json()
    # les valeurs légitimes passent toujours, entier comme décimal
    r = _api("GET", f"/api/cards/{did}/geom",
             params={"dpi": "600", "bleed_mm": "3.0", "corner_mm": "2.5"})
    assert r.status_code == 200 and r.json()["geom"]["dpi"] == 600
    _api("DELETE", f"/api/cards/{did}")


def test_le_catalogue_sert_les_constantes_et_la_vraie_regle():
    """La route dont le docstring dit « calculé, jamais une table recopiée »
    recopiait ses propres constantes en littéraux, et sa chaîne `rule` était
    fausse par omission : elle écrivait `round(...)` (qui, en Python, est
    précisément PAS floor(x+0.5)) et ne disait RIEN de la zone sûre — celle
    qui était fausse."""
    b = _api("GET", "/api/cards/formats").json()
    assert b["bleed"] == {"metric_mm": CT.BLEED_METRIC_MM,
                          "imperial_mm": CT.BLEED_IMPERIAL_MM,
                          "max_mm": CT.BLEED_MM_MAX}
    assert b["limits"]["dpi"] == [CT.DPI_MIN, CT.DPI_MAX]
    r = b["rule"]
    assert "floor(x + 0.5)" in r and "round(" not in r
    assert "safe_px = px(trim_mm - 2*safe_mm)" in r
    assert "safe_off_px" in r
    par_id = {f["fmt"]: f for f in b["formats"]}
    assert par_id["micro"]["safe_px"] == [300, 450]
    assert par_id["poker_us"]["safe_off_px"] == [75.0, 75.0]


def test_une_route_inconnue_du_domaine_ne_rend_jamais_du_html():
    """Piège n°7 : sous /api, un chemin non apparié tombait sur le catch-all
    de la SPA et rendait 200 + du HTML. Mesuré : un `did` à séparateurs
    percent-encodés sortait du domaine avant d'atteindre le garde-fou 400."""
    for chemin in ("/api/cards/..%2f..%2f..%2fetc/geom",
                   "/api/cards/deck_a1b2c3d4/face/inexistant",
                   "/api/cards/rien/du/tout"):
        r = _api("GET", chemin)
        assert r.status_code in (400, 404), f"{chemin} -> {r.status_code}"
        assert "json" in r.headers.get("content-type", ""), \
            f"{chemin} rend {r.headers.get('content-type')} — le catch-all SPA"
        assert not r.text.lstrip().startswith("<")


def test_la_coquille_des_huit_pieces_est_valide():
    """Les huit pièces existent, chacune avec son `router`, et chacune part
    VIDE : le corps est le travail des builders, la coquille est gelée."""
    import importlib
    assert CT.MODULE_IDS == ("face", "frame", "type", "data", "solid",
                             "texture", "print", "gltf")
    for mid in CT.MODULE_IDS:
        mod = importlib.import_module(f"app.services.cards.{mid}")
        assert hasattr(mod, "router"), mid
        # « part VIDE » décrivait le jour du gel. Les huit builders ont depuis
        # rempli leur module : ce qui reste vérifiable est le CONTRAT, à savoir
        # que chacun expose son propre routeur et n'emprunte celui de personne.
        from fastapi import APIRouter
        assert isinstance(mod.router, APIRouter), mid
        for autre in CT.MODULE_IDS:
            if autre != mid:
                a = importlib.import_module(f"app.services.cards.{autre}")
                assert mod.router is not a.router,                     f"{mid} et {autre} partagent le même routeur"


def test_le_routeur_est_monte_sous_api_cards():
    """La preuve du câblage de `app/main.py`.

    Elle se lit sur `app.openapi()["paths"]` et NON sur `app.routes` : depuis
    FastAPI 0.141, `include_router` pose des inclusions PARESSEUSES
    (`_IncludedRouter`) que `app.routes` n'aplatit jamais, même après une
    requête. Le document OpenAPI, lui, les résout — et dans l'ordre de
    déclaration."""
    from app.main import app, _cardforge
    chemins = list(app.openapi().get("paths", {}))
    cartes = [p for p in chemins if p.startswith("/api/cards")]
    for attendu in ("/api/cards/formats", "/api/cards/decks",
                    "/api/cards/{did}", "/api/cards/{did}/geom"):
        assert attendu in cartes, f"{attendu} absent de {cartes}"
    # /formats et /decks AVANT le joker /{did} : Starlette apparie dans
    # l'ordre, l'inverse les ferait tomber dans « identifiant invalide ».
    assert cartes.index("/api/cards/formats") < cartes.index("/api/cards/{did}")
    assert cartes.index("/api/cards/decks") < cartes.index("/api/cards/{did}")
    # ...et tout cela AVANT le catch-all de la SPA, sinon l'API rendrait du
    # HTML (piège n°7).
    monts = [getattr(r, "path", None) for r in app.routes
             if type(r).__name__ == "Mount"]
    assert monts[-1] == "", f"le montage SPA doit rester le dernier: {monts}"
    if _cardforge.is_dir():
        assert "/cardforge" in monts, \
            "sans ce montage, l'iframe affiche la SPA en cascade (piège n°7)"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
