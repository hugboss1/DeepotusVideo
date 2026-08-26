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
import inspect
import json
import math
import os
import pathlib
import re
import sys
import tempfile
import threading
import time
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
    chemin.

    LE SAUT DE LIGNE FINAL EST DANS LA LISTE, et il y est parce qu'il manquait :
    `re.match` ancre au DÉBUT et `$` accepte un saut de ligne FINAL — si bien
    que `"deck_a1b2c3d4\\n"` passait le motif, sortait un chemin, et aurait fait
    naître un dossier de jeu au nom invisible. C'est très exactement le piège
    que ce dépôt nomme deux fois dans ses commentaires (`fullmatch` et non
    `match`) et qu'il ne s'appliquait pas ici."""
    for mauvais in ("..", "../..", "deck_../../x", "deck_XXXXXXXX",
                    "deck_0000000", "deck_000000000", "mat_a1b2c3d4",
                    "deck_a1b2c3d4/../..", "C:/windows", "", None, 42,
                    "deck_a1b2c3d4\x00", "deck_a1b2c3d4\n", "deck_a1b2c3d4\r\n",
                    "\ndeck_a1b2c3d4", " deck_a1b2c3d4", "deck_a1b2c3d4 "):
        with pytest.raises(ValueError):
            CT.deck_dir(mauvais)
        assert CT.is_valid_did(mauvais) is False
    assert CT.is_valid_did("deck_a1b2c3d4") is True
    p = CT.deck_dir("deck_a1b2c3d4")
    assert str(p).startswith(str(CT.decks_root().resolve()))
    # le motif lui-même : ancré des DEUX bouts, et lu avec `fullmatch`.
    assert "fullmatch" in inspect.getsource(CT.is_valid_did), \
        "is_valid_did lit son motif avec `match` : le saut de ligne final passe"


def test_meta_json_est_ecrit_atomiquement():
    """AUCUN brouillon ne survit — et le pin cherche `*.tmp`, pas le seul nom
    `meta.json.tmp` : depuis le patron T1, le brouillon porte un suffixe
    UNIQUE, si bien qu'un pin sur le nom fixe serait devenu vrai par accident
    et ne surveillerait plus rien."""
    doc = CC.create_deck("Jeu témoin")
    d = CT.deck_dir(doc["id"])
    assert (d / "meta.json").is_file()
    restes = list(d.glob("*.tmp"))
    assert restes == [], [p.name for p in restes]
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
    # LE TEST NETTOIE SON ÉPAVE (hygiène antérieure à la phase 4, mesurée en
    # ronde adverse). Le jeu abîmé restait sur le disque avec un `updated`
    # re-daté à CHAQUE lecture ultérieure : il s'invitait dans la liste des
    # jeux, en tête du tri par date, et faisait échouer environ un passage
    # sur dix-sept du contrôle de tri (la résolution d'`updated` est la
    # seconde — deux jeux de la même seconde se départagent au hasard).
    # Le nettoyage est ASSERTÉ, sinon rien ne le tient : un `delete_deck`
    # supprimé par mégarde repasserait vert et l'intermittence reviendrait
    # sans que personne fasse le lien.
    CC.delete_deck(doc["id"])
    assert CC.read_deck(doc["id"]) is None, "l'épave du test est restée"


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


# ── LES DIX SOUS-ARBRES (phase 4, D1) ───────────────────────────────────────
# `MODULE_IDS` a été figé à HUIT le jour du gel, et il y est resté deux pièces
# de trop longtemps. Conséquence MESURÉE avant correction : l'écran envoie
# `doc.forge3d` à chaque autosave (`core.js:saveBody` prend tout id du tableau
# JS `MODULES`, qui porte `forge3d` depuis la phase 2a), le backend le jetait
# en silence — `normalize_deck` ne garde que ce qui est dans la liste — et
# TOUTE édition du graphe P9 était perdue au rechargement en ligne. Aucun test
# ne l'épinglait. Les deux tests ci-dessous roulent par LA ROUTE RÉELLE et non
# par `write_deck` : c'est le cycle que vit l'utilisateur, PATCH puis GET, et
# c'est le seul qui traverse `patch_deck` ET `read_deck`.

def test_le_graphe_de_la_forge_SURVIT_a_un_cycle_PATCH_puis_GET():
    """F2 : « doc.forge3d.graph reste LA vérité » (plan 2a) ne tenait pas une
    seconde hors du navigateur. Le graphe part, revient — ou ne revient pas."""
    did = _api("POST", "/api/cards/decks",
               json={"name": "forge"}).json()["deck"]["id"]
    graphe = {
        "nodes": [{"id": "n1", "kind": "layer", "params": {"side": "front"}},
                  {"id": "n2", "kind": "assemble", "params": {}}],
        "edges": [{"from": "n1", "to": "n2", "port": "in"}],
    }
    r = _api("PATCH", f"/api/cards/{did}",
             json={"forge3d": {"graph": graphe, "layout": {"n1": [10, 20]}}})
    assert r.status_code == 200, r.text
    doc = _api("GET", f"/api/cards/{did}").json()["deck"]
    assert "forge3d" in doc, \
        "le document ne porte AUCUN sous-arbre forge3d : la clé a été jetée"
    assert doc["forge3d"].get("graph") == graphe, \
        f"le graphe n'a pas survécu au cycle : {doc.get('forge3d')!r}"
    assert doc["forge3d"].get("layout") == {"n1": [10, 20]}
    CC.delete_deck(did)


def test_capture_est_un_sous_arbre_comme_les_neuf_autres():
    """P10 hériterait du même trou. La PARITÉ de traitement se prouve sur les
    deux bouts : un sous-arbre bien formé survit, un `capture` mal formé
    envoyé par un client donne `{}` sans erreur — jamais un 500, jamais un
    document amputé."""
    did = _api("POST", "/api/cards/decks",
               json={"name": "capture"}).json()["deck"]["id"]
    neuf = _api("GET", f"/api/cards/{did}").json()["deck"]
    assert neuf.get("capture") == {}, \
        "le document neuf ne sème pas capture : default_doc a une pièce de retard"
    assert neuf.get("forge3d") == {}, "ni forge3d"

    r = _api("PATCH", f"/api/cards/{did}",
             json={"capture": {"analyzed": True, "bg": {"confidence": 0.71}}})
    assert r.status_code == 200, r.text
    doc = _api("GET", f"/api/cards/{did}").json()["deck"]
    assert doc.get("capture", {}).get("analyzed") is True, doc.get("capture")
    assert doc["capture"]["bg"] == {"confidence": 0.71}

    # ... et le mal formé ne fait ni 500 ni dégât (patron des huit d'origine)
    for pourri in (None, "texte", [1], 7):
        r = _api("PATCH", f"/api/cards/{did}", json={"capture": pourri})
        assert r.status_code == 200, (pourri, r.status_code, r.text[:200])
        doc = _api("GET", f"/api/cards/{did}").json()["deck"]
        assert doc["capture"]["analyzed"] is True, pourri
    # un document dont le disque porte n'importe quoi se répare en `{}`
    brut = CC.normalize_deck({"id": did, "capture": ["pas un objet"],
                              "forge3d": None})
    assert brut["capture"] == {} and brut["forge3d"] == {}
    CC.delete_deck(did)


def test_liste_et_suppression():
    avant = {d["id"] for d in CC.list_decks()}
    a = CC.create_deck("A")
    assert a["id"] in {d["id"] for d in CC.list_decks()}
    assert CC.delete_deck(a["id"]) is True
    apres = {d["id"] for d in CC.list_decks()}
    assert a["id"] not in apres and avant.issubset(apres | avant)


# ── LA PAGINATION DE `GET /decks` (dette héritée, soldée en 3c-T6) ──────────
# La route servait TOUS les documents ENTIERS : 13,4 Mo et 18 s sur un poste à
# 2 191 jeux (mesure du 22/08). La galerie n'en affichait que vingt-quatre
# lignes de quatre champs, et elle rabotait À L'ARRIVÉE — après le réseau,
# après le parseur JSON, après le tas de l'onglet. Le rabot est passé au
# serveur, et le contrat CHANGE : `{decks, total, limit}`.

def _decks_de_banc(n: int) -> list[str]:
    return [CC.create_deck(f"banc {i}")["id"] for i in range(n)]


def test_la_liste_des_jeux_est_BORNEE_et_DIT_le_total():
    """Le plafond sans le total serait un mensonge par omission : un écran qui
    reçoit trois jeux ne pourrait plus distinguer « ce backend en a trois » de
    « il en a sept et vous en voyez trois »."""
    avant = len(CC.list_decks())
    faits = _decks_de_banc(7)
    try:
        d = _api("GET", "/api/cards/decks", params={"limit": 3}).json()
        assert len(d["decks"]) == 3, d
        assert d["total"] == avant + 7, d
        assert d["limit"] == 3, d
        # PLUS RÉCENT D'ABORD, lu DANS LA RÉPONSE. On ne compare PAS deux
        # balayages champ à champ : un meta.json illisible se RE-DATE à chaque
        # lecture (test juste dessous), donc deux balayages successifs n'ont
        # aucune raison de donner les mêmes dates. L'ORDRE, lui, est stable.
        maj = [x["updated"] for x in d["decks"]]
        assert maj == sorted(maj, reverse=True), maj
        # …et la tranche servie EST la tête de la liste complète, jamais un
        # morceau au hasard : les trois premiers ids d'un listing non plafonné.
        tous = _api("GET", "/api/cards/decks", params={"limit": 500}).json()
        ids = [x["id"] for x in tous["decks"]]
        assert [x["id"] for x in d["decks"]] == ids[:3], (d["decks"], ids[:3])
        # …et entre eux, les jeux de banc gardent l'ordre inverse de création.
        vus = [i for i in ids if i in set(faits)]
        assert vus == list(reversed(faits)), vus
        # sans `limit`, le défaut de la maison
        nu = _api("GET", "/api/cards/decks").json()
        assert nu["limit"] == CC.DECKS_LIMIT_DEFAULT == 100
        assert nu["total"] == avant + 7
        assert len(nu["decks"]) == min(nu["total"], 100)
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_jeu_ILLISIBLE_se_RE_DATE_a_chaque_lecture_et_squatte_la_tete():
    """TROUVÉ EN CHERCHANT UNE INTERMITTENCE (3c-T6), et épinglé plutôt que
    corrigé. `read_deck` NORMALISE un meta.json illisible au lieu de faire
    tomber l'appelant — mais `normalize_deck` remplit alors `created` et
    `updated` avec `_now_iso()`, c'est-à-dire MAINTENANT. Conséquences,
    mesurées ici :

      · deux lectures successives du MÊME fichier abîmé ne rendent pas la même
        date (c'est ce qui faisait clignoter le test au-dessus une fois sur
        vingt-cinq — la cause n'était pas dans le test) ;
      · un document qu'on ne sait pas lire est donc, à chaque balayage, le jeu
        LE PLUS RÉCEMMENT MODIFIÉ du backend. Il passe devant un jeu créé
        APRÈS lui, et il tient la première ligne de la galerie pour toujours ;
      · son nom est perdu et remplacé par le défaut « Mon jeu ».

    LE COMPORTEMENT PRÉCÈDE LA 3c-T6 — ce n'est pas une régression du plafond.
    Mais le plafond le rend conséquent : c'est le SERVEUR qui choisit désormais
    les vingt-quatre lignes servies, et celle-là en prend une définitivement.
    Non corrigé ici parce que le remède est une DÉCISION de produit (que doit
    dire un jeu abîmé ? une date nulle, le mtime du fichier, un badge
    « illisible » que la galerie afficherait ?) et qu'elle n'appartient pas à
    une tâche de dettes. Ce test est là pour que la décision se prenne les
    yeux ouverts."""
    # L'ORDRE DE CRÉATION COMPTE : le jeu sain naît EN PREMIER, l'abîmé
    # ensuite. Sans cela les deux tomberaient dans la même seconde d'`updated`
    # et c'est le mtime qui trancherait — on mesurerait le départage, pas la
    # re-datation.
    sain = CC.create_deck("un jeu qui va bien")["id"]
    did = CC.create_deck("bientôt illisible")["id"]
    try:
        (CC.deck_dir(did) / "meta.json").write_text("{pas du json",
                                                    encoding="utf-8")
        un = CC.read_deck(did)
        time.sleep(1.1)
        deux = CC.read_deck(did)
        assert un["name"] == deux["name"] == "Mon jeu", (un["name"], deux["name"])
        assert un["updated"] != deux["updated"], (un["updated"], deux["updated"])
        # …et à cet instant il DOUBLE le jeu sain, qui n'a pourtant pas bougé :
        # sa date à lui vient d'avancer d'une seconde, tout seul.
        gros = _api("GET", "/api/cards/decks", params={"limit": 500}).json()
        ids = [x["id"] for x in gros["decks"]]
        assert ids.index(did) < ids.index(sain), (ids.index(did), ids.index(sain))
        par_id = {x["id"]: x for x in gros["decks"]}
        assert par_id[did]["updated"] > par_id[sain]["updated"], (
            par_id[did]["updated"], par_id[sain]["updated"])
    finally:
        CC.delete_deck(did)
        CC.delete_deck(sain)


def test_un_jeu_liste_est_un_RESUME_de_quatre_champs():
    """Ce qui traverse le réseau, et rien de plus. Le pin porte sur les CLÉS —
    servir `type`, `frame` ou `data` en plus, c'est reservir les 13,4 Mo."""
    did = CC.create_deck("résumé")["id"]
    try:
        # UN JEU QUI A SERVI, pas un jeu vide : c'est ce qui pèse. Un deck
        # fraîchement créé fait 317 octets — mesurer sur lui aurait donné un
        # rapport flatteur pour la liste et faux pour la dette.
        CC.patch_deck(did, {"type": {"slots": [
            {"id": f"s{i}", "label": f"Bloc {i}", "box": [4.5, 5.0 * i, 54.0, 8.0],
             "font": "IBMPlexSans", "size_pt": 9.0, "color": "#efe7d6",
             "text": "Vol, célérité. À l'entrée en jeu, révélez trois cartes.",
             "align": "left", "valign": "top", "leading": 1.22, "wrap": True}
            for i in range(6)]}})
        d = _api("GET", "/api/cards/decks", params={"limit": 500}).json()
        ligne = [x for x in d["decks"] if x["id"] == did][0]
        assert set(ligne) == {"id", "name", "created", "updated"}, ligne
        assert ligne["name"] == "résumé"
        # …et le document ENTIER, lui, existe toujours : la route par id le
        # sert, c'est elle qu'on ouvre quand on ouvre un jeu.
        entier = _api("GET", f"/api/cards/{did}").json()["deck"]
        assert {"type", "frame", "face", "format"} <= set(entier), sorted(entier)
        assert len(entier["type"]["slots"]) == 6
        # LA MESURE, refaite ici : le résumé pèse une fraction du document.
        court = len(json.dumps(ligne, ensure_ascii=False).encode("utf-8"))
        long_ = len(json.dumps(entier, ensure_ascii=False).encode("utf-8"))
        assert court * 10 < long_, (court, long_)
    finally:
        CC.delete_deck(did)


@pytest.mark.parametrize("demande,attendu", [
    (0, 1), (-5, 1), (1, 1), (500, 500), (501, 500), (99999, 500),
    (3.7, 3),
])
def test_la_limite_est_RAMENEE_jamais_refusee(demande, attendu):
    """`limit` est une commodité d'affichage, pas une contrainte métier : on la
    RAMÈNE dans [1, 500] et l'on DIT la valeur retenue.

    LE CAS QUI COMPTE EST LE NÉGATIF : `rows[:-5]` n'est pas une liste vide,
    c'est TOUTE LA LISTE MOINS LES CINQ DERNIERS — un plafond non borné rendrait
    donc PLUS de jeux pour un nombre plus petit. Et `limit=0` rendrait une liste
    vide sur un backend plein."""
    faits = _decks_de_banc(3)
    try:
        d = _api("GET", "/api/cards/decks", params={"limit": demande}).json()
        assert d["limit"] == attendu, d
        assert len(d["decks"]) == min(attendu, d["total"]), (demande, d["limit"],
                                                             len(d["decks"]))
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_une_limite_QUI_N_EST_PAS_UN_NOMBRE_est_un_400_en_francais():
    """Patron `_q_num` : typée `int`, FastAPI rendrait un 422 pydantic EN
    ANGLAIS là où la spec 2.5 impose 400 + une phrase française."""
    r = _api("GET", "/api/cards/decks", params={"limit": "beaucoup"})
    assert r.status_code == 400, r.text
    assert "nombre" in r.json()["detail"], r.text
    assert _api("GET", "/api/cards/decks",
                params={"limit": "nan"}).status_code == 400


def test_une_limite_NON_BORNEE_rougit(monkeypatch):
    """MUTATION DE CONTRÔLE, jouée PAR LA VRAIE ROUTE : le rabotage est retiré
    et l'on regarde ce que la route sert alors. `limit=-5` ne rend pas une
    liste vide — `rows[:-5]` rend TOUTE LA LISTE MOINS LES CINQ DERNIERS, donc
    un nombre plus petit sert PLUS de jeux ; et `limit=0` vide la liste d'un
    backend plein. Les deux assertions du pin d'au-dessus tombent."""
    faits = _decks_de_banc(8)
    try:
        monkeypatch.setattr(CC, "borne_limite", lambda v: int(float(v)))
        d = _api("GET", "/api/cards/decks", params={"limit": -5}).json()
        assert len(d["decks"]) > 1, d       # le pin exige EXACTEMENT 1
        assert d["limit"] == -5, d
        z = _api("GET", "/api/cards/decks", params={"limit": 0}).json()
        assert z["decks"] == [] and z["total"] >= 8, z
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_TOTAL_derive_de_la_TRANCHE_rougit(monkeypatch):
    """MUTATION DE CONTRÔLE du `total` : une route qui plafonnerait À LA
    SOURCE puis compterait ce qu'elle a reçu annoncerait un total égal à la
    tranche. Le mutant tronque le balayage — le total suit, et il ment."""
    faits = _decks_de_banc(6)
    try:
        vrai = CC.list_deck_summaries
        monkeypatch.setattr(CC, "list_deck_summaries", lambda: vrai()[:2])
        d = _api("GET", "/api/cards/decks", params={"limit": 2}).json()
        assert d["total"] == len(d["decks"]) == 2, d
        assert d["total"] < len(CC.list_decks()), d   # la vérité est ailleurs
    finally:
        for did in faits:
            CC.delete_deck(did)


# ── L'INDEX DE LISTING (performance, hors phase 4) ──────────────────────────
# La 3c a raboté les OCTETS servis, pas le BALAYAGE. La route relisait CHAQUE
# meta.json pour connaître `updated`, donc pour trier — et elle le refaisait à
# chaque appel, y compris quand rien n'avait bougé.
#
#   · déployé, 24/08 : GET /api/cards/decks?limit=1 = 13 850 ms à froid pour
#     2 198 jeux (le même backend répond 177 ms sur /health) ;
#   · corpus synthétique de 2 200 jeux minimaux, cache OS CHAUD, la partie
#     reproductible : 2 200 ouvertures et ~5 800 ms, à CHAQUE appel.
#
# Le remède est un index de listing revalidé PAR STAT. Ce qui est verrouillé
# ci-dessous est un COMPTE D'OUVERTURES, jamais un chrono : un `assert ms < X`
# rougit sur une machine chargée et ne prouve rien de la règle. Le contrat de
# la route, lui, NE BOUGE PAS D'UN OCTET — les pins de la 3c au-dessus sont
# restés mot pour mot.


def _espion_de_meta(monkeypatch) -> dict:
    """Compte les OUVERTURES RÉELLES de meta.json, sur `pathlib` lui-même.

    L'ESPION NE VISE AUCUNE FONCTION DU MAGASIN, ET C'EST DÉLIBÉRÉ. Patcher
    `read_deck` compterait les appels d'un NOM, pas les accès au DISQUE : le
    jour où le balayage passe par une autre porte, le compte tombe à zéro et
    le test se déclare vert en ne mesurant plus rien. C'est le piège du spy
    qui fuit, et il s'évite en visant l'ouverture elle-même.

    LE SCEAU DE L'INSTRUMENT est dans les tests qui s'en servent : chacun
    exige d'abord un compte NON NUL sur le passage à froid. Si le magasin
    passait un jour de `Path.read_text` à `open()`, le compteur tomberait à
    zéro PARTOUT — et c'est cette assertion-là qui rougirait, au lieu de
    laisser un test creux passer.
    """
    vrai = pathlib.Path.read_text
    vu = {"n": 0}

    def espion(self, *a, **kw):
        if self.name == "meta.json":
            vu["n"] += 1
        return vrai(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", espion)
    return vu


def _compte(vu: dict, appel):
    """(ouvertures de meta.json, valeur rendue) pour UN appel."""
    vu["n"] = 0
    out = appel()
    return vu["n"], out


def _listing(limit: int = 500):
    return _api("GET", "/api/cards/decks", params={"limit": limit})


def _api_ensemble(appels):
    """Plusieurs requêtes dans LA MÊME boucle d'événements.

    C'EST AINSI QUE LE VRAI SERVEUR LES TRAITE, et c'est la seule façon de
    mesurer un verrou `asyncio` : un `Lock` créé sous une boucle et attendu
    sous une autre LÈVE (`bound to a different event loop`). Le harnais à
    threads d'`_api` — un `asyncio.run` par fil — ne peut donc pas juger la
    coalescence des écritures ; il reste bon pour secouer le DISQUE, où les
    fils de `to_thread` font le vrai travail."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await asyncio.gather(
                *[c.request(m, p, **kw) for m, p, kw in appels])
    return asyncio.run(go())


def test_un_SECOND_listing_sans_changement_n_OUVRE_AUCUN_meta_json(monkeypatch):
    """L'INVARIANT DE LA TÂCHE. Deux listings de suite, rien n'a bougé entre
    les deux : le second ne doit toucher AUCUN meta.json. C'est cela qui fait
    tomber les 13,8 s — pas un plafond d'octets de plus.

    Le premier passage, lui, balaye tout : c'est le prix payé UNE FOIS, et il
    sert ici de sceau à l'instrument (un compteur qui ne compte rien serait
    vert des deux côtés)."""
    faits = _decks_de_banc(6)
    try:
        vu = _espion_de_meta(monkeypatch)
        froid, un = _compte(vu, CC.list_deck_summaries)
        assert froid >= len(faits), (
            f"l'espion n'a vu que {froid} ouvertures pour {len(faits)} jeux "
            "de banc : il ne mesure plus le disque")
        chaud, deux = _compte(vu, CC.list_deck_summaries)
        assert chaud == 0, (
            f"{chaud} meta.json rouverts alors que rien n'a bougé (un jeu "
            "ILLISIBLE, lui, est relu à chaque fois : c'est voulu)")
        assert deux == un, "l'index ne rend pas la MÊME liste que le disque"
        # …et par la ROUTE RÉELLE, qui balaye dans un thread : le compteur est
        # posé sur pathlib, donc il voit aussi ce thread-là.
        n3, r = _compte(vu, _listing)
        assert r.status_code == 200, r.text
        assert n3 == 0, n3
        assert [x["id"] for x in r.json()["decks"]] == [x["id"] for x in un]
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_RENOMMAGE_est_vu_au_listing_suivant_et_ne_RELIT_QUE_LUI(monkeypatch):
    """La revalidation est PAR JEU : un jeu modifié coûte UNE relecture, les
    2 199 autres coûtent un stat."""
    faits = _decks_de_banc(6)
    cible = faits[2]
    try:
        CC.list_deck_summaries()                      # l'index existe
        vu = _espion_de_meta(monkeypatch)
        assert _compte(vu, CC.list_deck_summaries)[0] == 0
        assert _api("PATCH", f"/api/cards/{cible}",
                    json={"name": "renommé au vol"}).status_code == 200
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 1, f"{n} relectures pour UN renommage"
        ligne = [x for x in lignes if x["id"] == cible][0]
        assert ligne["name"] == "renommé au vol", ligne
        assert lignes[0]["id"] == cible, "le jeu modifié n'est pas en tête"
        # et l'on retombe à zéro : le renommage est entré dans l'index
        assert _compte(vu, CC.list_deck_summaries)[0] == 0
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_une_EDITION_HORS_DE_L_APP_est_VUE(monkeypatch):
    """Un script QA, un éditeur de texte, une restauration de sauvegarde :
    l'index est un CACHE, `meta.json` reste LA VÉRITÉ. Aucun chemin d'écriture
    de l'app n'est passé par là, et pourtant le listing suivant le voit —
    parce que c'est le stat PAR JEU qui fait foi."""
    faits = _decks_de_banc(4)
    cible = faits[1]
    try:
        CC.list_deck_summaries()
        f = CC.deck_dir(cible) / "meta.json"
        brut = json.loads(f.read_text(encoding="utf-8"))
        brut["name"] = "édité hors de l'app"
        brut["updated"] = "2099-01-01T00:00:00Z"
        f.write_text(json.dumps(brut, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        vu = _espion_de_meta(monkeypatch)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 1, f"{n} relectures : l'édition externe a coûté trop cher"
        assert lignes[0]["id"] == cible, [x["id"] for x in lignes[:3]]
        assert lignes[0]["name"] == "édité hors de l'app", lignes[0]
        assert lignes[0]["updated"] == "2099-01-01T00:00:00Z", lignes[0]
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_le_MTIME_DU_DOSSIER_RACINE_ne_voit_PAS_un_meta_json_imbrique():
    """LE PIÈGE WINDOWS, MESURÉ PLUTÔT QU'AFFIRMÉ. Invalider l'index sur le
    mtime de `decks/` serait FAUX : modifier `decks/deck_x/meta.json` ne
    touche pas l'horodatage de `decks/` — un dossier n'est daté que par les
    entrées qu'on lui AJOUTE ou qu'on lui RETIRE. C'est pour cela que la
    revalidation est un stat PAR JEU."""
    did = CC.create_deck("piège de racine")["id"]
    try:
        racine = CC.decks_root()
        avant = racine.stat().st_mtime_ns
        time.sleep(0.05)
        CC.patch_deck(did, {"name": "modifié en profondeur"})
        assert racine.stat().st_mtime_ns == avant, (
            "le mtime de decks/ a bougé sur une écriture imbriquée : "
            "le piège nommé n'en est pas un sur ce système")
    finally:
        CC.delete_deck(did)


def test_une_CREATION_une_COPIE_et_une_SUPPRESSION_sont_VUES(monkeypatch):
    """Les trois autres chemins d'écriture. Aucun n'entretient l'index — la
    revalidation par stat les rattrape tous, et c'est ce qui est prouvé ici."""
    faits = _decks_de_banc(3)
    try:
        CC.list_deck_summaries()
        vu = _espion_de_meta(monkeypatch)
        neuf = CC.create_deck("le petit nouveau")["id"]
        faits.append(neuf)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 1, n
        assert lignes[0]["id"] == neuf and lignes[0]["name"] == "le petit nouveau"

        copie = _api("POST", f"/api/cards/decks/{neuf}/duplicate")
        assert copie.status_code == 200, copie.text
        cid = copie.json()["deck"]["id"]
        faits.append(cid)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 1, n
        par_id = {x["id"]: x for x in lignes}
        assert par_id[cid]["name"] == "copie de le petit nouveau", par_id[cid]

        assert _api("DELETE", f"/api/cards/{cid}").status_code == 200
        faits.remove(cid)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 0, f"{n} relectures pour une SUPPRESSION"
        assert cid not in {x["id"] for x in lignes}, "le jeu supprimé est resté"
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_JEU_ILLISIBLE_n_est_PAS_mis_en_CACHE(monkeypatch):
    """L'INDEX N'IMMORTALISE PAS LE MENSONGE. `read_deck` RE-DATE un meta.json
    illisible à chaque lecture — sémantique ÉPINGLÉE plus haut
    (`test_un_jeu_ILLISIBLE_se_RE_DATE_...`), pas corrigée ici. Un index qui
    mettrait ce document en cache figerait la date bidon et changerait, par la
    bande, un comportement que la 3c a délibérément laissé en place.

    Le remède : un jeu qu'on ne sait pas LIRE n'entre pas dans l'index. Il est
    relu à chaque balayage — il est rare, et il redevient sain dès qu'on le
    répare."""
    sain = CC.create_deck("un jeu qui va bien")["id"]
    did = CC.create_deck("bientôt illisible")["id"]
    try:
        CC.list_deck_summaries()                      # l'index prend l'empreinte
        (CC.deck_dir(did) / "meta.json").write_text("{pas du json",
                                                    encoding="utf-8")
        vu = _espion_de_meta(monkeypatch)
        n1, un = _compte(vu, CC.list_deck_summaries)
        assert n1 == 1, n1
        time.sleep(1.1)
        n2, deux = _compte(vu, CC.list_deck_summaries)
        assert n2 == 1, (
            f"{n2} ouvertures : l'index a mis le jeu illisible en cache "
            "(0) ou relit tout le monde (>1)")
        a = [x for x in un if x["id"] == did][0]["updated"]
        b = [x for x in deux if x["id"] == did][0]["updated"]
        assert b > a, (a, b, "la date bidon a été figée par l'index")
        assert [x["id"] for x in deux][0] == did
    finally:
        CC.delete_deck(did)
        CC.delete_deck(sain)


POISONS = [
    "{ pas du json",                              # tronqué
    "",                                           # vide
    "[]",                                         # pas un objet
    '{"decks": {}}',                              # sans version
    '{"v": 999999, "decks": {}}',                 # version inconnue
    '{"v": 1}',                                   # sans entrées
    '{"v": 1, "decks": "pas un objet"}',
    '{"v": 1, "decks": {"deck_deadbeef": {"name": "fantôme", "created": "",'
    ' "updated": "9999-01-01T00:00:00Z", "mtime": 1, "size": 1}}}',
    '{"v": 1, "decks": {"deck_deadbeef": 42}}',
]


@pytest.mark.parametrize("poison", POISONS)
def test_un_INDEX_ABIME_se_RECONSTRUIT_en_silence(monkeypatch, poison):
    """JAMAIS-500, côté cache. Un index tronqué, vide, d'un schéma inconnu, ou
    qui parle d'un jeu qui n'existe plus : l'issue reste JUSTE, la route reste
    à 200, et l'index se refait tout seul au passage suivant.

    LE FANTÔME EST LE CAS QUI COMPTE VRAIMENT : un index qui MENT par excès ne
    doit pas faire apparaître un jeu absent du disque. La liste ne sort JAMAIS
    de ce que le balayage a réellement vu — l'index ne fait que dispenser de
    l'OUVRIR."""
    faits = _decks_de_banc(4)
    try:
        CC.list_deck_summaries()
        (CC.decks_root() / CC.INDEX_NAME).write_text(poison, encoding="utf-8")
        r = _listing()
        assert r.status_code == 200, r.text
        ids = [x["id"] for x in r.json()["decks"]]
        assert set(faits) <= set(ids), (poison, ids[:8])
        assert "deck_deadbeef" not in ids, "l'index a inventé un jeu"
        assert all(CT.is_valid_did(i) for i in ids), ids[:8]
        # …et il s'est refait : le passage suivant ne rouvre plus rien
        vu = _espion_de_meta(monkeypatch)
        assert _compte(vu, CC.list_deck_summaries)[0] == 0, poison
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_le_FICHIER_D_INDEX_ne_peut_JAMAIS_passer_pour_un_JEU():
    """Le nom est choisi pour qu'AUCUNE confusion ne soit possible : il ne
    satisfait pas `DID_RE`, et le balayage ne retient que des DOSSIERS. Deux
    verrous, la doctrine de `deck_dir` (le motif PUIS le confinement)."""
    assert CT.is_valid_did(CC.INDEX_NAME) is False
    with pytest.raises(ValueError):
        CT.deck_dir(CC.INDEX_NAME)
    racine = CC.decks_root()
    faits = _decks_de_banc(2)
    intrus = [racine / CC.INDEX_NAME,
              racine / f"{CC.INDEX_NAME}.abcdef.tmp",   # un brouillon oublié
              racine / "notes.txt"]
    (racine / "pas_un_deck").mkdir(exist_ok=True)
    (racine / f"{CC.INDEX_NAME}.abcdef.tmp").write_text("{}", encoding="utf-8")
    (racine / "notes.txt").write_text("bonjour", encoding="utf-8")
    try:
        ids = [x["id"] for x in CC.list_deck_summaries()]
        assert set(faits) <= set(ids)
        assert all(CT.is_valid_did(i) for i in ids), ids[:8]
        for p in intrus:
            assert p.name not in ids
        assert "pas_un_deck" not in ids
    finally:
        for p in intrus[1:]:
            p.unlink(missing_ok=True)
        (racine / "pas_un_deck").rmdir()
        for did in faits:
            CC.delete_deck(did)


def test_des_LISTINGS_SIMULTANES_pendant_des_ECRITURES_ne_rendent_JAMAIS_un_500():
    """LA CONCURRENCE, ET SON PLANCHER DE SERVICE. La leçon de T1 : « jamais de
    500 » tout seul est un DEMI-CONTRAT — un serveur qui refuserait poliment
    tout le monde passerait vert. On exige donc AUSSI que tout le monde soit
    SERVI, et servi JUSTE : les DEUX côtés répondent 200, et chaque listing
    porte les jeux du banc.

    Ce que l'on secoue : huit listings et douze autosaves en même temps, donc
    des réécritures d'index concurrentes ET des `replace` sur des `meta.json`
    qu'un balayage est en train de lire.

    CE TEST A TROUVÉ UN VRAI 500, ANTÉRIEUR À L'INDEX. `write_deck` posait son
    brouillon sur un nom FIXE (`meta.json.tmp`) et remplaçait sans patience :
    sur Windows, `replace` par-dessus un fichier ouvert en lecture refuse avec
    WinError 5. Mesuré 2 échecs sur 12 autosaves — reproduits À L'IDENTIQUE
    sur l'arbre d'AVANT l'index, donc pas une régression de celui-ci — et un
    `PATCH` qui rendait 500 pour une frappe au clavier. Corrigé au patron T1
    (brouillon unique + `replace` patient)."""
    faits = _decks_de_banc(12)
    NOMS = {f"secoué {i}" for i in range(12)}
    listings, ecritures, pepins = [], [], []

    def lit():
        try:
            r = _listing()
            listings.append((r.status_code, r.json()))
        except Exception as e:                                 # noqa: BLE001
            pepins.append(repr(e))

    def ecrit(did, base):
        try:
            for i in range(3):
                d = CC.patch_deck(did, {"name": f"secoué {base + i}"})
                ecritures.append(d is not None and d["name"])
        except Exception as e:                                 # noqa: BLE001
            pepins.append(repr(e))

    try:
        # LES QUATRE ÉCRIVAINS TAPENT SUR LE MÊME JEU, et c'est le cas RÉEL :
        # deux onglets ouverts sur la même partie, ou l'un des huit builders
        # qui enregistre pendant que l'écran autosauve. Un brouillon à nom FIXE
        # (`meta.json.tmp`) est alors LE MÊME FICHIER pour tout le monde : l'un
        # le remplace pendant que l'autre y écrit encore.
        #
        # LE MAGASIN EST SECOUÉ DIRECTEMENT, sans passer par la route, et c'est
        # exprès : le verrou par jeu de la route sérialiserait ces quatre-là et
        # l'on ne mesurerait plus l'atomicité de `write_deck`, qui est une
        # garantie DU MAGASIN — tenue même quand l'appelant n'est pas la route.
        fils = ([threading.Thread(target=lit) for _ in range(8)]
                + [threading.Thread(target=ecrit, args=(faits[0], 3 * i))
                   for i in range(4)])
        for f in fils:
            f.start()
        for f in fils:
            f.join(timeout=120)
        assert not pepins, pepins
        # LE PLANCHER DE SERVICE, des deux côtés : personne n'est refusé.
        assert len(listings) == 8, (len(listings), "plancher de service")
        assert len(ecritures) == 12 and set(ecritures) <= NOMS, ecritures
        for code, corps in listings:
            assert code == 200, (code, corps)
            par_id = {x["id"]: x for x in corps["decks"]}
            assert set(faits) <= set(par_id), sorted(set(faits) - set(par_id))
            assert corps["total"] >= len(faits)
            for ligne in corps["decks"]:
                assert set(ligne) == {"id", "name", "created", "updated"}, ligne
            # SERVI JUSTE S'ASSERTIONNE SUR LE NOM, pas sur la présence de la
            # ligne : la galerie servait « Mon jeu », fantôme daté de
            # maintenant, à la place du jeu bousculé — et ce test restait vert.
            assert par_id[faits[0]]["name"] in NOMS | {"banc 0"}, \
                par_id[faits[0]]
            for i, did in enumerate(faits[1:], start=1):
                assert par_id[did]["name"] == f"banc {i}", par_id[did]
        # …et aucun brouillon n'a survécu à la bousculade.
        for did in faits:
            restes = list(CC.deck_dir(did).glob("*.tmp"))
            assert restes == [], [p.name for p in restes]
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_DISQUE_QUI_REFUSE_L_ECRITURE_est_dit_EN_FRANCAIS_sur_les_TROIS_routes(
        monkeypatch):
    """La route `PATCH` était la SEULE des trois qui écrivent à ne pas border
    l'`OSError` : un refus du disque y ressortait en trace nue. Ses deux sœurs
    disent depuis toujours ce que l'OS a refusé, en français — et SANS le
    chemin absolu, qui porterait le nom de compte."""
    did = CC.create_deck("disque plein")["id"]
    avant = {p.name for p in CC.decks_root().iterdir()}
    try:
        def refuse(*a, **kw):
            raise OSError(28, "Il n'y a plus d'espace disponible sur le disque")

        monkeypatch.setattr(CC, "write_deck", refuse)
        for methode, chemin in (("PATCH", f"/api/cards/{did}"),
                                ("POST", "/api/cards/decks"),
                                ("POST", f"/api/cards/decks/{did}/duplicate")):
            r = _api(methode, chemin, json={"name": "x"})
            assert r.status_code == 500, (methode, chemin, r.status_code)
            detail = r.json()["detail"]
            assert "impossible" in detail and "refusée" in detail, detail
            assert "espace" in detail, detail
            assert "\\" not in detail and "/Users" not in detail, detail
    finally:
        # les deux routes de CRÉATION posent le dossier AVANT d'écrire : un
        # refus les laisse derrière, et le test emporte ses épaves.
        for p in CC.decks_root().iterdir():
            if p.name not in avant and CT.is_valid_did(p.name):
                CC.delete_deck(p.name)
        CC.delete_deck(did)


def test_une_ECRITURE_PENDANT_LA_LECTURE_n_entre_PAS_dans_l_index(monkeypatch):
    """LA COURSE LA PLUS FINE, jouée à la main faute de pouvoir l'attendre.

    Une écriture qui tombe pendant la lecture donne un contenu PÉRIMÉ. Mise en
    cache sous l'empreinte d'APRÈS, l'entrée serait périmée POUR TOUJOURS —
    plus aucun stat ne la contredirait. Mise en cache sous l'empreinte d'AVANT
    (c'est le choix, et il tient en un seul stat), le prochain stat l'invalide
    d'office : une relecture de plus, jamais un mensonge.

    La fenêtre est de quelques microsecondes : on ne l'attend pas, on la
    PROVOQUE, en faisant écrire la lecture elle-même."""
    faits = _decks_de_banc(3)
    cible = faits[1]
    try:
        CC.list_deck_summaries()
        f = CC.deck_dir(cible) / "meta.json"
        vrai = CC._lit_meta

        def lit_puis_ecrit(did):
            out = vrai(did)
            if did == cible:
                brut = json.loads(f.read_text(encoding="utf-8"))
                brut["name"] = "écrit pendant sa propre lecture"
                f.write_text(json.dumps(brut, ensure_ascii=False, indent=2),
                             encoding="utf-8")
            return out

        f.touch()                       # invalide l'entrée : le jeu sera relu
        monkeypatch.setattr(CC, "_lit_meta", lit_puis_ecrit)
        CC.list_deck_summaries()
        monkeypatch.setattr(CC, "_lit_meta", vrai)

        vu = _espion_de_meta(monkeypatch)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 1, (
            "le jeu écrit PENDANT sa lecture est entré dans l'index : son "
            "empreinte et son contenu ne viennent pas du même instant")
        ligne = [x for x in lignes if x["id"] == cible][0]
        assert ligne["name"] == "écrit pendant sa propre lecture", ligne
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_LISTING_STABLE_ne_REECRIT_PAS_l_index():
    """L'index n'est posé que s'il a CHANGÉ, et « changé » se juge sur le
    CONTENU, pas sur un drapeau « j'ai relu quelque chose ».

    LE CAS QUI SÉPARE LES DEUX est le jeu ILLISIBLE : il est relu à CHAQUE
    balayage (sa date est re-datée, il n'entre jamais dans le cache). Avec un
    drapeau, sa seule présence ferait réécrire 328 Kio à chaque ouverture de
    la galerie — pour reposer exactement les mêmes octets."""
    faits = _decks_de_banc(3)
    abime = CC.create_deck("abîmé")["id"]
    try:
        CC.list_deck_summaries()
        p = CC.decks_root() / CC.INDEX_NAME
        avant = p.stat().st_mtime_ns
        time.sleep(0.05)
        CC.list_deck_summaries()
        CC.list_deck_summaries()
        assert p.stat().st_mtime_ns == avant, "l'index est reposé pour rien"

        (CC.deck_dir(abime) / "meta.json").write_text("{pas du json",
                                                      encoding="utf-8")
        CC.list_deck_summaries()                  # le jeu abîmé sort du cache
        stable = p.stat().st_mtime_ns
        time.sleep(0.05)
        CC.list_deck_summaries()
        CC.list_deck_summaries()
        assert p.stat().st_mtime_ns == stable, (
            "un jeu illisible fait réécrire l'index à chaque listing")
    finally:
        CC.delete_deck(abime)
        for did in faits:
            CC.delete_deck(did)


def test_l_IDENTIFIANT_SERVI_vient_du_DOSSIER_jamais_de_l_index():
    """Un index qui se tromperait d'identifiant ne doit pas pouvoir servir le
    nom d'un jeu sous l'identifiant d'un AUTRE. L'entrée n'en porte pas — et
    si une main lui en glisse un, il est ignoré."""
    faits = _decks_de_banc(3)
    cible = faits[1]
    p = CC.decks_root() / CC.INDEX_NAME
    try:
        CC.list_deck_summaries()
        brut = json.loads(p.read_text(encoding="utf-8"))
        assert "id" not in brut["decks"][cible], brut["decks"][cible]
        assert set(brut["decks"][cible]) == set(CC.INDEX_CLES)
        brut["decks"][cible]["id"] = "deck_deadbeef"
        p.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        ids = {x["id"] for x in CC.list_deck_summaries()}
        assert "deck_deadbeef" not in ids, "l'index a imposé son identifiant"
        assert cible in ids
        # LA GARDE S'ASSERTIONNE AUSSI SEULE. Depuis que l'entrée est ramenée à
        # cinq clés à la LECTURE de l'index, un `id` glissé n'atteint même plus
        # `_resume_d_entree` — la ceinture est devenue invisible derrière les
        # bretelles. On la tient donc directement, sinon elle pourrirait sans
        # qu'un seul test bronche.
        seul = CC._resume_d_entree("deck_a1b2c3d4",
                                   {"id": "deck_deadbeef", "name": "n",
                                    "created": "c", "updated": "u",
                                    "mtime": 1, "size": 1})
        assert seul["id"] == "deck_a1b2c3d4", seul
    finally:
        p.unlink(missing_ok=True)          # l'index truqué ne survit pas au test
        for did in faits:
            CC.delete_deck(did)


def test_un_BALAYAGE_QUI_ECHOUE_ne_dit_PAS_zero_jeu_et_ne_TOUCHE_PAS_l_index(
        monkeypatch):
    """RÉGRESSION DE LA PREMIÈRE LIVRAISON, trouvée en ronde adverse.

    `_dossiers_de_decks` avalait l'`OSError` du `scandir` et rendait une liste
    VIDE. Deux dégâts, pas un :

      · l'écran recevait « vous n'avez aucun jeu » en 200 — un mensonge poli,
        là où la version d'avant laissait le refus du disque faire son 500 ;
      · pire, le listing continuait et ÉCRASAIT l'index avec `{}`. Le cache de
        2 200 entrées disparaissait sur un accès refusé passager, et le
        passage suivant repayait le balayage entier.

    `decks_root()` — qui fait un `mkdir` — était DANS le même `try` : un
    dossier de sortie en lecture seule produisait exactement la même issue."""
    faits = _decks_de_banc(4)
    try:
        CC.list_deck_summaries()
        p = CC.decks_root() / CC.INDEX_NAME
        avant = json.loads(p.read_text(encoding="utf-8"))
        assert len(avant["decks"]) >= 4, avant["decks"]

        vrai = os.scandir

        def refuse(chemin, *a, **kw):
            if str(chemin) == str(CC.decks_root()):
                raise PermissionError(13, "Accès refusé")
            return vrai(chemin, *a, **kw)

        monkeypatch.setattr(os, "scandir", refuse)
        r = _listing()
        assert r.status_code == 500, (r.status_code, r.text)
        detail = r.json()["detail"]
        assert "jeux" in detail and "refusé" in detail, detail
        assert "Accès refusé" in detail, detail
        assert "\\" not in detail, detail          # jamais le chemin absolu
        monkeypatch.undo()

        apres = json.loads(p.read_text(encoding="utf-8"))
        assert apres == avant, "l'index a été écrasé par un balayage raté"
        vu = _espion_de_meta(monkeypatch)
        assert _compte(vu, CC.list_deck_summaries)[0] == 0, \
            "le cache a été perdu : le passage suivant repaye tout"
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_REFUS_DE_PARTAGE_PASSAGER_n_INVENTE_PAS_un_jeu(monkeypatch):
    """LE FANTÔME. Sur Windows, ouvrir un `meta.json` qu'un `replace` est en
    train de remplacer échoue avec un refus de partage — PASSAGER, le fichier
    est parfaitement sain une milliseconde plus tard.

    `_lit_meta` traitait cet `OSError` comme une corruption : il rendait un
    document NEUF, nommé « Mon jeu », daté de MAINTENANT. Résultat mesuré :
    32 courses sur 32, le fantôme en PREMIÈRE LIGNE de la galerie, à la place
    du jeu qu'on venait justement de modifier. Le défaut existe par ligne
    servie depuis toujours ; le listing 60 fois plus rapide en multiplie
    simplement l'exposition par seconde.

    La règle : on n'INVENTE jamais un document. Un refus passager sert
    l'entrée d'index connue (elle est vraie, juste peut-être d'une seconde) ou
    ne sert RIEN. Seul un contenu VRAIMENT illisible — du JSON invalide — se
    répare et se re-date, exactement comme avant."""
    faits = _decks_de_banc(4)
    cible = faits[2]
    try:
        CC.list_deck_summaries()
        assert _api("PATCH", f"/api/cards/{cible}",
                    json={"name": "un nom bien à moi"}).status_code == 200
        CC.list_deck_summaries()

        vrai = pathlib.Path.read_text

        def refuse(self, *a, **kw):
            if self.name == "meta.json" and self.parent.name == cible:
                raise PermissionError(
                    32, "Le processus ne peut pas accéder au fichier")
            return vrai(self, *a, **kw)

        # on invalide l'entrée pour forcer la relecture, PUIS on la refuse
        (CC.deck_dir(cible) / "meta.json").touch()
        monkeypatch.setattr(pathlib.Path, "read_text", refuse)
        lignes = CC.list_deck_summaries()
        monkeypatch.undo()

        noms = [x["name"] for x in lignes]
        assert "Mon jeu" not in noms, (
            "un fantôme « Mon jeu » a été inventé sur un refus PASSAGER")
        ligne = [x for x in lignes if x["id"] == cible]
        assert ligne and ligne[0]["name"] == "un nom bien à moi", (
            "le refus passager n'a pas servi ce que l'index savait déjà")
        assert lignes[0]["id"] != cible or lignes[0]["name"] != "Mon jeu"

        # …et `read_deck` n'invente rien non plus : un document VIDE écrit
        # par-dessus le vrai, c'est la perte du jeu au premier autosave.
        monkeypatch.setattr(pathlib.Path, "read_text", refuse)
        assert CC.read_deck(cible) is None, \
            "read_deck a fabriqué un document sur un refus passager"
        assert CC.patch_deck(cible, {"face": {"x": 1}}) is None
        monkeypatch.undo()
        entier = _api("GET", f"/api/cards/{cible}").json()["deck"]
        assert entier["name"] == "un nom bien à moi", entier["name"]
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_la_LECTURE_est_PATIENTE_devant_un_refus_QUI_PASSE(monkeypatch):
    """LE REFUS DE PARTAGE DURE UN APPEL SYSTÈME, PAS UNE REQUÊTE — et ne rien
    rendre est la bonne réponse seulement quand il ne passe PAS.

    Sans patience, le remède au fantôme faisait sauter en silence l'autosave
    qui l'avait provoqué : `read_deck` rendait None, `patch_deck` rendait None,
    et la frappe de l'utilisateur disparaissait sans un message (mesuré 1 sur
    12 sous bousculade). La patience de lecture est le pendant exact de celle
    du `replace` : même conflit, vu de l'autre bout.

    Le refus est joué CAPRICIEUX — il cède au dernier essai — parce que c'est
    la seule façon de mesurer la patience elle-même plutôt que le hasard."""
    did = CC.create_deck("patient")["id"]
    essais = {"n": 0}
    vrai = pathlib.Path.read_text

    def capricieux(self, *a, **kw):
        if self.name == "meta.json" and self.parent.name == did:
            essais["n"] += 1
            if essais["n"] < CC.PARTAGE_ESSAIS:
                raise PermissionError(
                    32, "Le processus ne peut pas accéder au fichier")
        return vrai(self, *a, **kw)

    try:
        monkeypatch.setattr(pathlib.Path, "read_text", capricieux)
        doc = CC.read_deck(did)
        monkeypatch.undo()
        assert doc is not None, "la lecture a abandonné avant que le refus cède"
        assert doc["name"] == "patient", doc["name"]
        assert essais["n"] == CC.PARTAGE_ESSAIS, essais["n"]
    finally:
        CC.delete_deck(did)


def test_DEUX_JEUX_DIFFERENTS_ne_PARTAGENT_PAS_leur_verrou():
    """Le verrou est PAR JEU, et cela se prouve sans chronomètre : on prend
    celui d'un jeu, puis celui d'un AUTRE sans lâcher le premier.

    Un verrou global s'auto-bloquerait ici — `asyncio.Lock` n'est pas
    réentrant — et le `wait_for` transforme cet interblocage en échec net au
    lieu d'une suite suspendue. Deux secondes pour une opération qui prend
    quelques microsecondes : aucune machine chargée ne peut faire rougir cela
    par lenteur."""
    a, b = "deck_aaaaaaaa", "deck_bbbbbbbb"

    async def go():
        async with CC._verrou_du_deck(a):
            va = CC._VERROUS[a]

            async def prendre_l_autre():
                async with CC._verrou_du_deck(b):
                    return CC._VERROUS[b]

            vb = await asyncio.wait_for(prendre_l_autre(), timeout=2.0)
            assert va is not vb, "les deux jeux se partagent UN verrou"
        return True

    assert asyncio.run(go()) is True
    assert CC._VERROUS == {} and CC._VERROUS_EN_COURS == {}, CC._VERROUS


def test_une_CLE_ETRANGERE_dans_l_index_ne_peut_RIEN_servir():
    """Le motif est la SEULE bretelle du chemin d'index : `_resume_d_entree` ne
    passe jamais par `deck_dir`, contrairement au chemin de relecture. Une clé
    qui n'est pas un identifiant de jeu est donc écartée À LA LECTURE de
    l'index, pas espérée refusée plus loin."""
    faits = _decks_de_banc(3)
    p = CC.decks_root() / CC.INDEX_NAME
    try:
        CC.list_deck_summaries()
        brut = json.loads(p.read_text(encoding="utf-8"))
        brut["decks"]["notes"] = {"name": "je ne suis pas un jeu",
                                  "created": "2099-01-01T00:00:00Z",
                                  "updated": "2099-01-01T00:00:00Z",
                                  "mtime": 1, "size": 1}
        p.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        # LA GARDE S'ASSERTIONNE AVANT LE BALAYAGE : un listing réécrirait
        # l'index et ferait disparaître la clé pour une tout autre raison —
        # le test passerait vert sans jamais toucher au verrou qu'il vise.
        propres, intact = CC._index_lu()
        assert "notes" not in propres, \
            "la clé étrangère traverse la lecture de l'index"
        assert intact is False, \
            "l'index se croit propre alors qu'il porte une clé étrangère"
        lignes = CC.list_deck_summaries()
        assert "notes" not in {x["id"] for x in lignes}
        assert "je ne suis pas un jeu" not in {x["name"] for x in lignes}
        assert all(CT.is_valid_did(x["id"]) for x in lignes)
        # …et elle ne survit pas non plus dans le fichier
        assert "notes" not in json.loads(
            p.read_text(encoding="utf-8"))["decks"]
    finally:
        p.unlink(missing_ok=True)
        for did in faits:
            CC.delete_deck(did)


def test_une_ENTREE_POLLUEE_est_PURGEE_au_listing_suivant():
    """L'index est AUTO-NETTOYANT. `_entree_a_jour` rendait l'ancienne entrée
    TELLE QUELLE : une clé étrangère de cinq kilo-octets — glissée par une
    main, laissée par un schéma défunt — survivait à tous les listings et
    grossissait le cache pour toujours. L'entrée servie est reconstruite à
    CINQ clés, ni plus ni moins."""
    faits = _decks_de_banc(3)
    cible = faits[1]
    p = CC.decks_root() / CC.INDEX_NAME
    try:
        CC.list_deck_summaries()
        brut = json.loads(p.read_text(encoding="utf-8"))
        brut["decks"][cible]["gras"] = "o" * 5000
        brut["decks"][cible]["id"] = "deck_deadbeef"
        p.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        gros = p.stat().st_size

        CC.list_deck_summaries()
        relu = json.loads(p.read_text(encoding="utf-8"))["decks"][cible]
        assert set(relu) == {"name", "created", "updated", "mtime", "size"}, relu
        assert p.stat().st_size < gros - 4000, (p.stat().st_size, gros)
    finally:
        p.unlink(missing_ok=True)
        for did in faits:
            CC.delete_deck(did)


def test_un_INDEX_DEFINITIVEMENT_NON_POSABLE_le_DIT(monkeypatch):
    """« Au-delà, ce n'est plus une course mais un vrai problème de disque, et
    il doit se DIRE » — la phrase était démentie par un `logger.debug`, muet en
    exploitation. Un index qu'on ne peut plus poser, c'est 13,8 s à CHAQUE
    ouverture de la galerie, pour toujours, sans un signal.

    Le journal parle donc en AVERTISSEMENT — et UNE SEULE FOIS : le répéter à
    chaque listing noierait le journal au lieu de le renseigner."""
    faits = _decks_de_banc(3)
    dits = []
    try:
        CC.list_deck_summaries()
        monkeypatch.setattr(CC, "_INDEX_PLAINTE_DITE", False, raising=False)

        class _Journal:
            def warning(self, m, *a, **k):
                dits.append(str(m))

            def __getattr__(self, _):
                return lambda *a, **k: None

        monkeypatch.setattr(CC, "logger", _Journal())

        def refuse(self, *a, **kw):
            raise OSError(13, "Accès refusé")

        monkeypatch.setattr(pathlib.Path, "write_text", refuse)
        (CC.decks_root() / CC.INDEX_NAME).unlink(missing_ok=True)
        for _ in range(4):
            assert len(CC.list_deck_summaries()) >= 3      # jamais de 500
        monkeypatch.undo()

        plaintes = [m for m in dits if "index" in m.lower()]
        assert len(plaintes) == 1, plaintes
        assert "Accès refusé" in plaintes[0], plaintes[0]
        assert "\\" not in plaintes[0], plaintes[0]
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_DEUX_PATCH_de_SOUS_ARBRES_DIFFERENTS_survivent_TOUS_LES_DEUX():
    """« Ce qu'il n'envoie pas survit » — la promesse de `patch_deck`, et elle
    était FAUSSE dès qu'on la tenait à deux.

    Le PATCH est un lire-modifier-écrire : deux requêtes qui arrivent ensemble
    lisent le MÊME document d'avant, chacune y pose SON sous-arbre, et la
    seconde à écrire efface le travail de la première — sans un mot, sans un
    conflit, sans un journal. Mesuré 40 fois sur 40 avant correction.

    Le remède est un verrou PAR JEU sur la route, tenu à travers le
    `to_thread` : deux onglets sur le même jeu s'attendent l'un l'autre le
    temps d'une écriture, et deux jeux différents ne s'attendent JAMAIS."""
    did = CC.create_deck("deux onglets pressés")["id"]
    try:
        for tour in range(8):
            a, b = f"onglet-A-{tour}", f"onglet-B-{tour}"
            ra, rb = _api_ensemble([
                ("PATCH", f"/api/cards/{did}", {"json": {"face": {"v": a}}}),
                ("PATCH", f"/api/cards/{did}", {"json": {"frame": {"v": b}}}),
            ])
            assert ra.status_code == rb.status_code == 200, (ra.text, rb.text)
            doc = _api("GET", f"/api/cards/{did}").json()["deck"]
            assert doc["face"] == {"v": a}, (tour, doc["face"], doc["frame"])
            assert doc["frame"] == {"v": b}, (tour, doc["face"], doc["frame"])
    finally:
        CC.delete_deck(did)


def test_DEUX_JEUX_DIFFERENTS_ne_s_ATTENDENT_PAS():
    """Le verrou est PAR JEU, pas global. Deux jeux distincts patchés ensemble
    ne se croisent pas — sans quoi la coalescence transformerait l'autosave de
    l'écran en file d'attente à l'échelle du backend."""
    a = CC.create_deck("jeu A")["id"]
    b = CC.create_deck("jeu B")["id"]
    try:
        ra, rb = _api_ensemble([
            ("PATCH", f"/api/cards/{a}", {"json": {"name": "A modifié"}}),
            ("PATCH", f"/api/cards/{b}", {"json": {"name": "B modifié"}}),
        ])
        assert ra.status_code == rb.status_code == 200
        assert _api("GET", f"/api/cards/{a}").json()["deck"]["name"] == "A modifié"
        assert _api("GET", f"/api/cards/{b}").json()["deck"]["name"] == "B modifié"
        # …et le magasin de verrous ne fuit pas : rien ne reste après coup.
        assert CC._VERROUS == {}, CC._VERROUS
    finally:
        CC.delete_deck(a)
        CC.delete_deck(b)


def test_AUCUN_BROUILLON_RASSIS_ne_s_accumule_ni_ne_se_DUPLIQUE(monkeypatch):
    """Le brouillon à SUFFIXE UNIQUE a un revers, et il n'était pas payé : une
    écriture interrompue par autre chose qu'une `OSError` (l'arrêt du
    processus, une `MemoryError`, un `KeyboardInterrupt`) laisse une épave que
    plus RIEN ne ramasse — le nom fixe d'avant, lui, était au moins réutilisé.
    Et `copytree` recopiait consciencieusement ces épaves dans chaque copie du
    jeu.

    Le balayage des brouillons RASSIS se fait à l'écriture, et il respecte les
    autres : un brouillon jeune peut appartenir à une écriture en cours."""
    did = CC.create_deck("épaves")["id"]
    try:
        d = CC.deck_dir(did)
        vieux = [d / f"meta.json.{i:032x}.tmp" for i in range(3)]
        for p in vieux:
            p.write_text("{}", encoding="utf-8")
            vieil_age = time.time() - CC.BROUILLON_RASSIS_S - 60
            os.utime(p, (vieil_age, vieil_age))
        jeune = d / "meta.json.ffffffffffffffffffffffffffffffff.tmp"
        jeune.write_text("{}", encoding="utf-8")

        CC.patch_deck(did, {"name": "après le ménage"})
        restes = sorted(p.name for p in d.glob("*.tmp"))
        assert restes == [jeune.name], restes

        # …et une duplication n'emporte AUCUN brouillon, même jeune.
        copie = _api("POST", f"/api/cards/decks/{did}/duplicate").json()["deck"]
        try:
            assert list(CC.deck_dir(copie["id"]).glob("*.tmp")) == []
            assert (CC.deck_dir(copie["id"]) / "meta.json").is_file()
        finally:
            CC.delete_deck(copie["id"])
    finally:
        CC.delete_deck(did)


def test_un_INDEX_CRU_SANS_REVALIDATION_rougit(monkeypatch):
    """MUTATION n°1 — le stat est ignoré, l'entrée d'index est crue sur parole.
    L'édition faite HORS de l'app devient alors INVISIBLE : le listing sert
    l'ancien nom et n'ouvre rien. Les deux assertions de
    `test_une_EDITION_HORS_DE_L_APP_est_VUE` tombent."""
    faits = _decks_de_banc(4)
    cible = faits[1]
    try:
        CC.list_deck_summaries()
        f = CC.deck_dir(cible) / "meta.json"
        brut = json.loads(f.read_text(encoding="utf-8"))
        brut["name"] = "édité hors de l'app"
        f.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(CC, "_entree_a_jour",
                            lambda vieille, st: vieille
                            if isinstance(vieille, dict) else None)
        vu = _espion_de_meta(monkeypatch)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        assert n == 0, n                      # le pin exige 1
        ligne = [x for x in lignes if x["id"] == cible][0]
        assert ligne["name"] != "édité hors de l'app", ligne
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_une_VERSION_D_INDEX_IGNOREE_rougit(monkeypatch):
    """MUTATION n°2 — `_index_lu` ne regarde plus `v`. Un index d'un schéma
    INCONNU est alors servi tel quel, et ce qu'il raconte passe pour la
    vérité. Le pin `test_un_INDEX_ABIME_se_RECONSTRUIT_en_silence` tombe sur
    le cas `{"v": 999999}`.

    Le mensonge est monté à l'empreinte EXACTE du disque : c'est bien la
    VERSION, et elle seule, qui doit le refuser."""
    faits = _decks_de_banc(3)
    cible = faits[1]
    try:
        CC.list_deck_summaries()
        p = CC.decks_root() / CC.INDEX_NAME
        brut = json.loads(p.read_text(encoding="utf-8"))
        brut["v"] = 999999
        brut["decks"][cible]["name"] = "menteur d'un schéma inconnu"
        p.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")

        sain = [x for x in CC.list_deck_summaries() if x["id"] == cible][0]
        assert sain["name"] != "menteur d'un schéma inconnu", sain

        p.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(
            CC, "_index_lu",
            lambda: (json.loads(p.read_text(encoding="utf-8"))["decks"], True))
        menti = [x for x in CC.list_deck_summaries() if x["id"] == cible][0]
        assert menti["name"] == "menteur d'un schéma inconnu", menti
    finally:
        for did in faits:
            CC.delete_deck(did)


def test_un_JEU_ILLISIBLE_MIS_EN_CACHE_rougit(monkeypatch):
    """MUTATION n°3 — la garde « lisible » saute et le document réparé entre
    dans l'index. La date bidon est alors FIGÉE : deux balayages à plus d'une
    seconde d'écart rendent la MÊME date, ce que le pin de la 3c interdit."""
    did = CC.create_deck("bientôt illisible")["id"]
    try:
        CC.list_deck_summaries()
        (CC.deck_dir(did) / "meta.json").write_text("{pas du json",
                                                    encoding="utf-8")
        vrai = CC._entree_de_document
        monkeypatch.setattr(CC, "_entree_de_document",
                            lambda doc, st, lisible: vrai(doc, st, True))
        un = [x for x in CC.list_deck_summaries() if x["id"] == did][0]
        time.sleep(1.1)
        vu = _espion_de_meta(monkeypatch)
        n, lignes = _compte(vu, CC.list_deck_summaries)
        deux = [x for x in lignes if x["id"] == did][0]
        assert n == 0, n                       # le pin exige 1
        assert deux["updated"] == un["updated"], (un, deux)   # le pin exige >
    finally:
        CC.delete_deck(did)


# ── LES DEUX TÉMOINS SURVIVANTS, AVOUÉS ─────────────────────────────────────
# VINGT-SIX mutations jouées SUR LA SOURCE, VINGT-QUATRE tuées. Les douze de
# la livraison : le stat ignoré, la version d'index ignorée, le jeu illisible
# mis en cache, l'identifiant repris de l'entrée, l'empreinte prise APRÈS la
# lecture, l'index reposé à chaque listing, le `replace` nu de `meta.json`, le
# brouillon à nom fixe, le tri retourné, l'`OSError` du PATCH laissée nue. Les
# quatorze de la ronde adverse : le balayage raté qui ravale son `OSError`, la
# route `/decks` qui ne nomme plus son refus, le refus PASSAGER traité comme
# une corruption (le fantôme), la lecture sans patience, l'index qui ne filtre
# plus ses clés, l'entrée polluée relayée telle quelle, la plainte muette, la
# plainte répétée, le verrou de PATCH retiré, le verrou rendu GLOBAL, les
# verrous non ramassés, le ramassage de brouillons retiré, le ramassage
# aveugle à l'âge, `copytree` qui remporte les épaves.
#
# DEUX SURVIVENT, et elles sont ÉCRITES plutôt que masquées.
#
# 1. LE `replace` NU DE L'INDEX. Retirer sa patience ne fait rougir aucun
#    test, et ce n'est pas un oubli : l'échec d'écriture de l'index est DÉJÀ
#    avalé — c'est un cache, et un cache qu'on n'a pas pu poser ne coûte qu'un
#    balayage de plus au passage suivant. Aucune assertion de JUSTESSE ne peut
#    donc le voir. On l'attraperait en exigeant un taux de pose sous
#    concurrence, mais la leçon T1 (c) est explicite : entre un TROU CONNU
#    ÉCRIT et une INTERMITTENCE ROUGE, le trou écrit gagne. La patience reste
#    malgré tout, parce qu'un listing qui ne réussirait JAMAIS à poser son
#    index resterait froid pour toujours — et c'est exactement les 13,8 s
#    qu'on est venu chercher.
#
#    SON JUMEAU SUR `meta.json`, LUI, EST BIEN VU — mais pas à tous les coups :
#    le `replace` nu y est tué 3 fois sur 5 (deux campagnes de 5 essais, 4/5
#    puis 3/5). C'est le témoin intermittent de la leçon T1 (c), pris du BON
#    côté : le code corrigé, lui, est vert à chaque passage. Un test qui rougit
#    parfois sur du code SAIN serait inacceptable ; un test qui rate parfois un
#    mutant manque de dents, il ne ment pas.
#
# 2. LE FILTRE `is_valid_did` DU BALAYAGE. Le retirer ne change rien à ce qui
#    est servi — mais L'AVEU D'ORIGINE DONNAIT LA MAUVAISE RAISON, et la ronde
#    adverse l'a démontré en mesurant : il affirmait que `deck_dir` refusait
#    l'intrus un cran plus loin. C'est vrai de la branche de RELECTURE, et
#    FAUX de la branche d'INDEX — `_resume_d_entree` sert une entrée sans
#    jamais passer par `deck_dir`. Mutant appliqué + index truqué, une clé
#    `notes` sortait dans la galerie. Le second verrou n'existait pas ; il
#    existe maintenant, dans `_index_lu`, et il a son propre pin
#    (`test_une_CLE_ETRANGERE_dans_l_index_ne_peut_RIEN_servir`).
#
#    L'aveu corrigé : le filtre du balayage est bien la CEINTURE par-dessus
#    les bretelles, et les bretelles sont désormais deux — `deck_dir` sur le
#    chemin qui relit, `_index_lu` sur le chemin qui sert le cache. Il ne se
#    juge donc pas au résultat mais au coût, puisqu'il évite d'aller stat-er
#    et lire ce qu'on sait déjà refuser.
#
#    LA LEÇON, ELLE, NE PORTE PAS SUR CE FILTRE : un témoin qu'on avoue
#    survivant doit être avoué avec la BONNE raison, sinon l'aveu couvre un
#    vrai trou en ayant l'air d'un acte d'honnêteté.


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


def test_la_coquille_des_dix_pieces_est_valide():
    """LES DIX PIÈCES, dans l'ordre du rail, chacune avec SON `router`.

    Ce test a épinglé HUIT ids pendant deux phases, pendant que le rail en
    portait dix et que l'écran envoyait les dix à l'autosave. Il ne gardait
    donc pas le contrat : il gardait un chiffre périmé, et c'est LUI qui
    faisait passer la perte de `doc.forge3d` pour une décision.

    La liste ne se relit pas d'un mot (« il y en a dix ») mais des ids EXACTS
    et de leur ORDRE : le rang dans ce tuple est le numéro de la pièce au
    rail, et `core.js:MODULES` porte la même suite. Les deux se tiennent la
    main — le test de parité écran/backend est plus bas."""
    import importlib
    assert CT.MODULE_IDS == ("face", "frame", "type", "data", "solid",
                             "texture", "print", "gltf", "forge3d", "capture")
    for mid in CT.MODULE_IDS:
        mod = importlib.import_module(f"app.services.cards.{mid}")
        assert hasattr(mod, "router"), mid
        # « part VIDE » décrivait le jour du gel. Les builders ont depuis
        # rempli leur module : ce qui reste vérifiable est le CONTRAT, à savoir
        # que chacun expose son propre routeur et n'emprunte celui de personne.
        from fastapi import APIRouter
        assert isinstance(mod.router, APIRouter), mid
        for autre in CT.MODULE_IDS:
            if autre != mid:
                a = importlib.import_module(f"app.services.cards.{autre}")
                assert mod.router is not a.router,                     f"{mid} et {autre} partagent le même routeur"
    # ... et chaque id a bien son sous-arbre dans un document neuf : la liste
    # ne sert à rien si `default_doc` n'en fait pas des clés.
    doc = CC.default_doc("deck_a1b2c3d4")
    for mid in CT.MODULE_IDS:
        assert doc.get(mid) == {}, mid


def test_la_liste_des_ids_est_LA_MEME_a_l_ecran_et_au_backend():
    """LE COÛT D'UNE DIVERGENCE EST UN EFFACEMENT SILENCIEUX, et il a été payé
    (F2) : `core.js:MODULES` porte les ids que l'autosave envoie,
    `contract.MODULE_IDS` porte ceux que le backend garde. Un id présent d'un
    seul côté est un sous-arbre qui part à chaque enregistrement et ne revient
    jamais. La liste JS est LUE dans le fichier — pas recopiée ici, sinon ce
    test ne comparerait que deux copies écrites par la même main."""
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" /
          "cardforge" / "js" / "core.js").read_text(encoding="utf-8")
    m = re.search(r"const\s+MODULES\s*=\s*\[([^\]]*)\]", js)
    assert m, "core.js:MODULES introuvable — le contrat de l'écran a bougé"
    ids = tuple(re.findall(r'"([a-z0-9]+)"', m.group(1)))
    assert ids == CT.MODULE_IDS, \
        f"écran {ids} != backend {CT.MODULE_IDS}"


def test_le_LINT_connait_exactement_les_MEMES_pieces_que_le_contrat():
    """LA LEÇON F2 N'AVAIT ÉTÉ APPLIQUÉE QU'À UN MIROIR SUR QUATRE. Le lint
    porte sa propre liste `MODULES` et sa propre table `Z_TABLE` : une pièce
    ajoutée au contrat mais oubliée là n'est simplement PAS CONTRÔLÉE — ni sa
    règle 1 (4 fichiers), ni son scoping CSS, ni son `use strict`, ni ses
    couches z. Un garde-fou qui ignore une pièce en silence est exactement le
    défaut que la phase 4 vient de payer, à l'autre bout de la chaîne. La
    liste est LUE dans le fichier du lint."""
    lint = (pathlib.Path(__file__).resolve().parents[2] / "scripts" / "qa" /
            "lint_cardforge.py").read_text(encoding="utf-8")
    m = re.search(r"^MODULES\s*=\s*\[(.*?)\]", lint, re.S | re.M)
    assert m, "lint_cardforge.py:MODULES introuvable"
    ids = tuple(re.findall(r'"([a-z0-9]+)"', m.group(1)))
    assert ids == CT.MODULE_IDS, f"lint {ids} != contrat {CT.MODULE_IDS}"
    z = re.search(r"^Z_TABLE\s*=\s*\{(.*?)^\}", lint, re.S | re.M)
    assert z, "lint_cardforge.py:Z_TABLE introuvable"
    cles = tuple(re.findall(r'"([a-z0-9]+)"\s*:', z.group(1)))
    assert set(cles) == set(CT.MODULE_IDS), \
        f"Z_TABLE {sorted(cles)} != contrat {sorted(CT.MODULE_IDS)}"


def test_la_COQUILLE_HTML_porte_les_dix_pieces_et_dans_L_ORDRE():
    """Le quatrième miroir : `index.html`. Trois listes y vivent — les
    feuilles, les panneaux, les scripts — et un module dont le `<script>`
    manque ne se charge tout simplement pas : le rail affiche une pastille
    grise (`.off`) et le panneau reste vide, sans une erreur. C'est le mode
    de panne le plus silencieux de tout le lab, et rien ne le gardait."""
    html = (pathlib.Path(__file__).resolve().parents[2] / "frontend" /
            "cardforge" / "index.html").read_text(encoding="utf-8")
    feuilles = tuple(re.findall(r'href="css/mod-([a-z0-9]+)\.css"', html))
    panneaux = tuple(re.findall(r'data-mod="([a-z0-9]+)"', html))
    scripts = tuple(re.findall(r'src="js/mod-([a-z0-9]+)\.js"', html))
    hotes = tuple(re.findall(r'data-host="([a-z0-9]+)"', html))
    for nom, vu in (("feuilles", feuilles), ("panneaux", panneaux),
                    ("scripts", scripts), ("hôtes", hotes)):
        assert vu == CT.MODULE_IDS, f"index.html {nom} : {vu}"
    # ... et l'ordre des feuilles compte : la coquille d'abord, les modules
    # ensuite, sinon une primitive écrase une règle de pièce.
    assert html.index('href="cardforge.css"') < html.index('href="css/mod-')
    assert html.index('src="js/core.js"') < html.index('src="js/mod-')


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


# ═══════════════ le zoom d'aperçu et la coulisse des panneaux ═══════════════
# Phase 6, T6-G/T6-H (demande du 26/08). Deux extensions de la COQUILLE, au
# patron 2d (une classe sur `.cf`, la VARIABLE bascule, dz_cf_*, absence de
# clé = état par défaut) :
#   · la COULISSE : une pièce dont des colonnes dorment le DIT
#     (`CF.coulisse(mod, niveau)`) ; le CORE pose `travail-mince`/`bande`
#     selon la pièce ACTIVE et c'est la SCÈNE qui absorbe chaque pixel
#     au-delà du plafond du travail ;
#   · le ZOOM : un état d'ÉCRAN SEUL (patron phase-pointeur de la phase 5) —
#     il multiplie le facteur d'adaptation de l'aperçu, ne touche NI le
#     document NI l'export, persiste `dz_cf_zoom`, et le pied « N % aperçu »
#     devient sa commande.

_SHELL = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"


def _coquille(nom: str) -> str:
    return (_SHELL / nom).read_text(encoding="utf-8")


def _fn_js(src: str, nom: str) -> str:
    """Le SOURCE d'une fonction de `core.js`, accolades équilibrées (le
    patron `_js_fn` du banc frame)."""
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


def test_le_gabarit_de_grille_reste_UN_la_coulisse_comprise():
    """« LE GABARIT DE GRILLE NE SE DÉDOUBLE PAS : c'est la VARIABLE qui
    bascule » (cardforge.css, escamotage 2d). La coulisse des panneaux entre
    par la même porte : le gabarit unique de `.cf` est fait de variables,
    les états `travail-mince`/`travail-bande` REDÉCLARENT les variables (la
    scène devient la colonne flexible, le travail se plafonne), et la
    colonne carte REPLIÉE garde le dernier mot — ses variables sont
    re-déclarées APRÈS (même spécificité : l'ordre tranche)."""
    css = _coquille("cardforge.css")
    assert css.count("grid-template-columns: var(--rail-w)") == 1, \
        "le gabarit de .cf s'est dédoublé"
    assert "grid-template-columns: var(--rail-w) var(--scene-col) var(--travail-col) auto" in css, \
        "le gabarit de .cf n'est pas fait des variables scène/travail"
    assert "--scene-col: var(--stage-w)" in css, \
        "la scène n'a pas de largeur par défaut (celle d'aujourd'hui)"
    assert "--travail-col: minmax(0, 1fr)" in css, \
        "le travail n'a pas sa flexibilité par défaut (celle d'aujourd'hui)"
    assert ".cf.travail-mince {" in css and ".cf.travail-bande {" in css, \
        "aucun état de coulisse sur la grille"
    assert "minmax(var(--stage-w), 1fr)" in css, \
        "la scène n'absorbe pas la place libérée (elle doit devenir flexible)"
    i_mince = css.index(".cf.travail-mince")
    i_stage = css.index(".cf.stage-replie { --scene-col:")
    assert i_mince < i_stage, \
        "la colonne carte repliée ne garde pas le dernier mot sur la coulisse"


def test_la_coulisse_est_un_service_du_CORE_et_la_piece_ACTIVE_decide():
    """`CF.coulisse(mod, niveau)` : la pièce DIT (0, 1, 2 colonnes
    repliées), le CORE arbitre — la classe suit la pièce ACTIVE (changer de
    pièce rend la grille d'origine), et `show` réapplique."""
    src = _coquille("js/core.js")
    fn = _fn_js(src, "coulisse")
    assert "assertId(id)" in fn, "coulisse accepte un module inconnu"
    assert "applyFold()" in fn, "coulisse ne réapplique pas l'état de la grille"
    ap = _fn_js(src, "applyFold")
    assert "TRAVAIL[ACTIVE]" in ap, \
        "la grille ne suit pas la pièce ACTIVE (une pièce replierait pour toutes)"
    assert '"travail-mince"' in ap and '"travail-bande"' in ap, ap
    sh = _fn_js(src, "show")
    assert "applyFold()" in sh, \
        "changer de pièce ne réapplique pas la coulisse de la pièce active"
    assert "coulisse: coulisse," in src, "CF.coulisse n'est pas au contrat"


def test_le_zoom_est_un_etat_d_ECRAN_seul_et_persiste_hors_document():
    """Le patron phase-pointeur (phase 5) : l'état d'écran ne touche jamais
    le fichier livré. Le zoom vit dans `dz_cf_zoom` (absence de clé =
    adapter), multiplie le facteur d'adaptation de l'APERÇU seulement, et
    ni le painter ni l'autosave ne le voient. La définition PLAFOND du
    bitmap reste la source : zoomer n'invente pas de pixels."""
    src = _coquille("js/core.js")
    assert 'const LS_ZOOM = "dz_cf_zoom"' in src, "le zoom ne persiste pas"
    zs = _fn_js(src, "zoomSet")
    assert "localStorage.removeItem(LS_ZOOM)" in zs, \
        "l'état par défaut (adapter) s'écrit au lieu de s'effacer"
    dp = _fn_js(src, "drawPreview")
    assert "PREV_SCALE = Math.max(0.02, fit * ZOOM)" in dp, \
        "le zoom ne compose pas le facteur d'adaptation"
    assert "Math.min(PREV_SCALE * dpr, 1)" in dp, \
        "le bitmap d'aperçu dépasse la définition de la source (mémoire pour rien)"
    assert "ZOOM" not in _fn_js(src, "renderRaw"), \
        "le painter voit le zoom : l'export n'est plus l'aperçu"
    assert "ZOOM" not in _fn_js(src, "saveBody"), \
        "l'autosave transporte le zoom : l'état d'écran fuit dans le document"


def test_le_pied_devient_la_COMMANDE_du_zoom_et_la_molette_suit():
    """« il existe déjà un 44 % aperçu en pied : brancher dessus » — le pied
    porte désormais − / % / + / Adapter / 100 %, la molette zoome avec Ctrl
    (passive:false, sinon preventDefault est un vœu) VERS le pointeur, et
    le bouton du MILIEU glisse l'aperçu (le gauche appartient aux pièces :
    P3 y déplace ses blocs)."""
    html = _coquille("index.html")
    for did in ("zoomOut", "zoomPct", "zoomIn", "zoomFit", "zoom100"):
        assert 'id="' + did + '"' in html, f"{did} absent du pied de scène"
    assert html.index('id="stageRead"') < html.index('id="zoomPct"'), \
        "la commande de zoom n'est pas dans le pied, à côté des mesures"
    src = _coquille("js/core.js")
    ws = _fn_js(src, "wireStage")
    assert '"wheel"' in ws and "passive: false" in ws, \
        "la molette est passive : le navigateur zoome la page à la place"
    assert "ev.ctrlKey" in ws, \
        "la molette nue zoome : elle doit garder son sens (défiler)"
    assert "ev.button !== 1" in ws, \
        "le pan ne se limite pas au bouton du milieu (le gauche est aux pièces)"
    # LES GESTES DE LA SCÈNE S'ÉCOUTENT EN CAPTURE, SUR document. Mesuré au
    # banc navigateur du 26/08 : le calque d'édition de P3 est du DOM posé
    # PAR-DESSUS le canevas (fixé sur body) — un écouteur sur la colonne ne
    # voyait JAMAIS la molette ni le bouton du milieu dès que la pièce pose
    # son calque. La garde est géométrique (la boîte visible de la colonne).
    assert 'document.addEventListener("wheel"' in ws, \
        "la molette s'écoute sous le calque d'édition : morte en écran 03"
    assert "capture: true" in ws, \
        "sans phase de capture, le calque d'édition avale le geste avant la scène"
    assert "surScene(ev)" in ws, \
        "aucune garde géométrique : la molette Ctrl serait volée à toute la page"
    assert 'document.addEventListener("pointerdown"' in ws, \
        "le bouton du milieu s'écoute sous le calque d'édition : mort en écran 03"
    for did in ("#zoomIn", "#zoomOut", "#zoomFit", "#zoom100"):
        assert '"' + did + '"' in ws, f"{did} n'est pas câblé"
    dp = _fn_js(src, "drawPreview")
    assert '"#zoomPct"' in dp, "le pourcentage du pied ne suit pas l'aperçu"
    assert "aperçu</span>" not in dp, \
        "le pourcentage est encore écrit dans stageRead : deux afficheurs divergeraient"


def test_l_apercu_zoome_DEFILE_et_reste_centre_quand_il_est_petit():
    """Le centrage passe de flex à `margin: auto` : les marges auto centrent
    un canevas petit ET s'annulent quand il déborde — un conteneur flex
    centré rend le coin haut-gauche INATTEIGNABLE au défilement. La colonne
    défile (`overflow: auto`), et le canevas n'est plus plafonné à 100 %
    (le plafond tuait le zoom). L'aperçu déplacé le DIT aux pièces :
    `core:scene` part de drawPreview (le calque d'édition de P3 se cale sur
    le rect du canevas)."""
    css = _coquille("cardforge.css")
    i = css.index(".stage-wrap {")
    bloc = css[i:css.index("}", i)]
    assert "overflow: auto" in bloc, "la colonne ne défile pas : pan impossible"
    assert "align-items: center" not in bloc, \
        "le centrage flex rend le coin haut-gauche inatteignable une fois zoomé"
    j = css.index(".stage-canvas {")
    blocC = css[j:css.index("}", j)]
    assert "margin: auto" in blocC, "le canevas n'est plus centré quand il est petit"
    assert "max-width: 100%" not in blocC and "max-height: 100%" not in blocC, \
        "le plafond à 100 % écrase le zoom"
    src = _coquille("js/core.js")
    assert '"core:scene"' in src, \
        "l'aperçu bouge sans le dire : les calques posés dessus dériveraient"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
