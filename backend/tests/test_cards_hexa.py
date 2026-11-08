# -*- coding: utf-8 -*-
"""Card Forge — t421 : les HUIT formats hexagonaux et leur contour.

Un hexagone régulier vit dans le rectangle qui l'englobe : `trim_mm` reste ce
rectangle, donc toile, fond perdu et pixels gardent la règle de `contract.py`.
Ce banc verrouille :

  1. les huit ids et leurs `trim_mm`, ÉCRITS EN DUR (p × 2/√3, 3 décimales) ;
  2. six sommets, côtés égaux, sens horaire depuis le sommet haut ;
  3. `decale` : décalage perpendiculaire, apothème + d ;
  4. le fond perdu hexagonal tronqué à la toile (la pointe dépasse de
     0,155 × fond perdu : 0,46 mm pour 3 mm) en gardant plus de 2,5 mm ;
  5. un rectangle ne change pas d'un octet (`to_dict` figé) ;
  6. la parité Python / JS (`CF.hexContours`) à 0,001 mm, par le vrai nœud ;
  7. corner_mm par défaut 0 pour un hexagone, profils d'imprimeurs fermés.

Run : <embedded python> backend/tests/test_cards_hexa.py
"""
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
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

from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import core as CC                       # noqa: E402
from app.services.cards import hexa as HX                       # noqa: E402

CORE_JS = (pathlib.Path(__file__).resolve().parent.parent.parent
           / "frontend" / "cardforge" / "js" / "core.js")
CARTES_JSON = (pathlib.Path(__file__).resolve().parent.parent.parent
               / "frontend" / "shared" / "i18n" / "cartes.json")

POINTE = ["hex_p50", "hex_p635", "hex_p75", "hex_p90"]
PLAT = ["hex_f50", "hex_f635", "hex_f75", "hex_f90"]
HEX = POINTE + PLAT

# trim_mm écrits en dur : (p, round(p * 2 / sqrt(3), 3)).
TRIM = {
    "hex_p50": (50.0, 57.735), "hex_p635": (63.5, 73.323),
    "hex_p75": (75.0, 86.603), "hex_p90": (90.0, 103.923),
    "hex_f50": (57.735, 50.0), "hex_f635": (73.323, 63.5),
    "hex_f75": (86.603, 75.0), "hex_f90": (103.923, 90.0),
}


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ═══════════════════════ 1. la table ═══════════════════════════════════════

def test_les_huit_formats_hexagonaux_et_les_douze_anciens():
    assert len(CT.FORMATS) == 20
    assert [f for f in CT.FORMATS if CT.FORMATS[f].get("forme") == "hex"] == HEX
    for f in POINTE:
        assert CT.FORMATS[f]["orientation"] == "pointe"
    for f in PLAT:
        assert CT.FORMATS[f]["orientation"] == "plat"
    for f in HEX:
        assert CT.FORMATS[f]["unit"] == "mm"
    # les douze premiers n'ont ni forme ni orientation : l'absence vaut « rect »
    for f in list(CT.FORMATS)[:12]:
        assert "forme" not in CT.FORMATS[f] and "orientation" not in CT.FORMATS[f]


@pytest.mark.parametrize("fmt", HEX)
def test_trim_mm_ecrit_en_dur(fmt):
    assert tuple(CT.FORMATS[fmt]["trim_mm"]) == TRIM[fmt]
    assert CT.geom(fmt).trim_mm == TRIM[fmt]


def test_le_fond_perdu_natif_d_un_hexagone_est_3_mm():
    for f in HEX:
        assert CT.native_bleed_mm(f) == 3.0
        assert CT.geom(f).bleed_mm == 3.0


# ═══════════════════════ 2. le contour ═════════════════════════════════════

@pytest.mark.parametrize("fmt", HEX)
def test_six_sommets_cotes_egaux_sens_horaire(fmt):
    g = CT.geom(fmt)
    pts = g.contour_mm
    assert g.forme == "hex" and len(pts) == 6
    cotes = [_dist(pts[i], pts[(i + 1) % 6]) for i in range(6)]
    assert max(cotes) - min(cotes) < 0.002, cotes
    # horaire à l'écran (y vers le bas) : l'aire signée « formule du lacet »
    # est POSITIVE avec y vers le bas.
    aire = sum(pts[i][0] * pts[(i + 1) % 6][1] - pts[(i + 1) % 6][0] * pts[i][1]
               for i in range(6)) / 2
    assert aire > 0
    # tout sommet est dans le rectangle de coupe
    w, h = g.trim_mm
    for x, y in pts:
        assert -1e-9 <= x <= w + 1e-9 and -1e-9 <= y <= h + 1e-9


def test_sommet_haut_et_orientation():
    w, h = TRIM["hex_p50"]
    assert CT.geom("hex_p50").orientation == "pointe"
    p = CT.geom("hex_p50").contour_mm
    assert p[0] == pytest.approx((w / 2, 0.0), abs=1e-9)           # la pointe
    assert p[3] == pytest.approx((w / 2, h), abs=1e-9)
    assert CT.geom("hex_f50").orientation == "plat"
    q = CT.geom("hex_f50").contour_mm
    w, h = TRIM["hex_f50"]
    assert q[0] == pytest.approx((w / 4, 0.0), abs=1e-9)           # côté plat en haut
    assert q[1] == pytest.approx((3 * w / 4, 0.0), abs=1e-9)


def test_un_rectangle_reste_un_rectangle():
    g = CT.geom("poker_us")
    assert g.forme == "rect" and g.orientation is None
    assert len(g.contour_mm) == 4


# ═══════════════════════ 3. decale ═════════════════════════════════════════

def _apotheme(pts):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    a, b = pts[0], pts[1]
    nx, ny = b[1] - a[1], a[0] - b[0]
    n = math.hypot(nx, ny)
    return abs((cx - a[0]) * nx / n + (cy - a[1]) * ny / n)


@pytest.mark.parametrize("fmt", HEX)
def test_decale_de_3_mm_donne_apotheme_plus_3(fmt):
    pts = CT.geom(fmt).contour_mm
    a0 = _apotheme(pts)
    assert a0 == pytest.approx(TRIM[fmt][0] / 2 if fmt in POINTE
                               else TRIM[fmt][1] / 2, abs=0.001)
    assert _apotheme(HX.decale(pts, 3.0)) == pytest.approx(a0 + 3.0, abs=1e-6)
    assert _apotheme(HX.decale(pts, -3.0)) == pytest.approx(a0 - 3.0, abs=1e-6)
    assert len(HX.decale(pts, 3.0)) == 6
    # l'hexagone reste régulier
    ext = HX.decale(pts, 3.0)
    cotes = [_dist(ext[i], ext[(i + 1) % 6]) for i in range(6)]
    assert max(cotes) - min(cotes) < 0.002


def test_decale_zero_est_l_identite_et_trop_vers_l_interieur_est_vide():
    pts = CT.geom("hex_p50").contour_mm
    for a, b in zip(HX.decale(pts, 0.0), pts):
        assert a == pytest.approx(b, abs=1e-9)
    assert HX.decale(pts, -26.0) == []        # apothème 25 mm : inversé


# ═══════════════════════ 4. la toile ═══════════════════════════════════════

def _toile_mm(g):
    return (g.canvas_px[0] / g.dpi * 25.4, g.canvas_px[1] / g.dpi * 25.4)


@pytest.mark.parametrize("fmt", HEX)
def test_fond_perdu_tronque_a_la_toile(fmt):
    g = CT.geom(fmt, 300, 3.0)
    cw, ch = _toile_mm(g)
    pts = HX.contour_toile_mm(g)
    assert len(pts) >= 6
    for x, y in pts:
        assert -1e-9 <= x <= cw + 1e-9 and -1e-9 <= y <= ch + 1e-9, (x, y)


def test_pointe_a_plus_de_2_5_mm_de_la_coupe():
    g = CT.geom("hex_p50", 300, 3.0)
    fond = HX.contour_toile_mm(g)
    coupe = HX.contour_coupe_toile_mm(g)
    # la pointe du fond perdu est à la toile (y = 0) ; celle de la coupe
    # est à ~3 mm : il reste plus de 2,5 mm de fond perdu.
    assert min(p[1] for p in fond) == pytest.approx(0.0, abs=1e-9)
    assert min(p[1] for p in coupe) - min(p[1] for p in fond) > 2.5
    assert max(p[1] for p in fond) == pytest.approx(_toile_mm(g)[1], abs=1e-9)
    # la pointe est tronquée : le polygone passe de 6 à 8 sommets
    assert len(fond) == 8


def test_cote_plat_sans_troncature_aux_cotes_plats_mais_aux_pointes():
    g = CT.geom("hex_f50", 300, 3.0)
    fond = HX.contour_toile_mm(g)
    cw, ch = _toile_mm(g)
    assert min(p[0] for p in fond) == pytest.approx(0.0, abs=1e-9)
    assert max(p[0] for p in fond) == pytest.approx(cw, abs=1e-9)
    assert len(fond) == 8


def test_sans_fond_perdu_le_fond_est_la_coupe():
    g = CT.geom("hex_p75", 300, 0.0, 0.0)
    a, b = HX.contour_toile_mm(g), HX.contour_coupe_toile_mm(g)
    assert len(a) == 6
    for p, q in zip(a, b):
        assert p == pytest.approx(q, abs=1e-6)


@pytest.mark.parametrize("fmt", HEX)
def test_zone_sure_dedans_et_milieux_sur_les_cotes(fmt):
    g = CT.geom(fmt, 300, 3.0, 3.0)
    sur = HX.contour_sur_mm(g)
    coupe = HX.contour_coupe_toile_mm(g)
    assert len(sur) == 6
    assert _apotheme(sur) == pytest.approx(_apotheme(coupe) - 3.0, abs=1e-6)
    mil = HX.milieux_cotes_mm(g)
    assert len(mil) == 6
    for i, m in enumerate(mil):
        a, b = coupe[i], coupe[(i + 1) % 6]
        assert m == pytest.approx(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2),
                                  abs=1e-9)


def test_un_rectangle_refuse_les_fonctions_hexagonales():
    g = CT.geom("poker_eu")
    for fn in (HX.contour_toile_mm, HX.contour_sur_mm, HX.milieux_cotes_mm,
               HX.contour_coupe_toile_mm):
        with pytest.raises(ValueError):
            fn(g)


# ═══════════════════════ 5. un rectangle ne change pas ═════════════════════

def test_to_dict_d_un_rectangle_est_fige():
    """Instantané relevé AVANT t421 sur poker_eu : égalité stricte, ni clé
    ajoutée ni valeur changée."""
    assert CT.geom("poker_eu").to_dict() == {
        "fmt": "poker_eu", "label": "Poker 63 x 88 mm", "unit": "mm",
        "dpi": 300, "trim_mm": [63.0, 88.0], "trim_in": [2.4803, 3.4646],
        "bleed_mm": 3.0, "safe_mm": 3.0, "corner_mm": 3.0,
        "trim_px": [744, 1039], "canvas_px": [815, 1110],
        "bleed_off_px": [35.5, 35.5], "safe_px": [673, 969],
        "safe_off_px": [71.0, 70.5], "corner_px": 35.4}


def test_to_dict_d_un_hexagone_ajoute_forme_orientation_contour():
    d = CT.geom("hex_p50").to_dict()
    assert d["forme"] == "hex" and d["orientation"] == "pointe"
    assert len(d["contour_mm"]) == 6
    assert d["trim_mm"] == [50.0, 57.735]


# ═══════════════════════ 6. coin, profils, normalisation ═══════════════════

def test_normalize_format_coin_zero_pour_un_hexagone():
    f = CC.normalize_format({"fmt": "hex_p50"})
    assert f["fmt"] == "hex_p50" and f["corner_mm"] == 0.0
    assert f["bleed_mm"] == 3.0 and f["safe_mm"] == 3.0
    # vague finale (I4, ruling) : un hexagone est TOUJOURS à sommets vifs — le
    # fichier de coupe, le trait, le masque et le gabarit n'ont pas d'arcs ; un
    # coin explicite est ramené à 0 (l'écran grise le champ).
    assert CC.normalize_format({"fmt": "hex_p50", "corner_mm": 2.0})["corner_mm"] == 0.0
    base = CC.normalize_format({"fmt": "hex_f75"})
    assert CC.normalize_format({"corner_mm": 3.0}, base=base)["corner_mm"] == 0.0
    assert CC.normalize_format({"fmt": "hex_f75", "corner_mm": 1.5}, base=None)["corner_mm"] == 0.0
    # un hexagone déjà enregistré avec un coin (avant la vague finale) se relit à 0
    assert CC.normalize_format({"fmt": "hex_f75", "corner_mm": 1.5},
                               base={"fmt": "hex_f75", "corner_mm": 1.5})["corner_mm"] == 0.0
    # et un rectangle garde son coin par défaut, et son coin explicite
    assert CC.normalize_format({"fmt": "poker_us"})["corner_mm"] == 3.0
    assert CC.normalize_format({"fmt": "poker_us", "corner_mm": 1.5})["corner_mm"] == 1.5
    # hexagone -> rectangle : le coin du rectangle revient
    assert CC.normalize_format({"fmt": "poker_eu"}, base=base)["corner_mm"] == 3.0


def _api(method: str, path: str, **kw):
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def test_patch_format_hexagonal_coin_force_a_zero():
    """Vague finale (I4) : PATCH format hex avec corner_mm 3 -> document à 0 ;
    /geom d'un hexagone ignore aussi un corner_mm demandé."""
    did = CC.create_deck("Coin hex", {"fmt": "hex_p50"})["id"]
    out = CC.patch_deck(did, {"format": {"corner_mm": 3.0}})
    assert out["format"]["corner_mm"] == 0.0
    out = CC.patch_deck(did, {"format": {"fmt": "hex_f90", "corner_mm": 3.0}})
    assert out["format"]["fmt"] == "hex_f90" and out["format"]["corner_mm"] == 0.0
    assert CC.read_deck(did)["format"]["corner_mm"] == 0.0
    r = _api("GET", f"/api/cards/{did}/geom", params={"corner_mm": "2"})
    assert r.status_code == 200 and r.json()["geom"]["corner_mm"] == 0.0, r.text
    r = _api("PATCH", f"/api/cards/{did}", json={"format": {"corner_mm": 4}})
    assert r.status_code == 200 and CC.read_deck(did)["format"]["corner_mm"] == 0.0, r.text
    # un rectangle garde son coin
    rid = CC.create_deck("Coin rect", {"fmt": "poker_us"})["id"]
    assert CC.patch_deck(rid, {"format": {"corner_mm": 1.5}})["format"]["corner_mm"] == 1.5
    r = _api("GET", f"/api/cards/{rid}/geom", params={"corner_mm": "2"})
    assert r.json()["geom"]["corner_mm"] == 2.0


def test_les_profils_d_imprimeur_n_admettent_aucun_hexagone():
    for pid, prof in CT.PRINTER_PROFILES.items():
        assert not set(prof["fmts"]) & set(HEX), pid
    assert tuple(CT.PRINTER_PROFILES["maison"]["fmts"]) == tuple(
        f for f in CT.FORMATS if f not in HEX)


def test_hexa_sans_fastapi():
    """La géométrie s'importe sans FastAPI. t421 (07/11/2026, T3) : seul
    `refuser_si_hex` l'importe, À L'APPEL — décision du contrôleur (le refus
    409 commun vit ici, pas dans contract.py qui n'a pas de code métier)."""
    src = pathlib.Path(HX.__file__).read_text(encoding="utf-8")
    k = src.index("def refuser_si_hex(")
    # aucune exception HTTP levée avant le refus, et le refus est la dernière fonction
    assert "HTTPException(" not in src[:k] and chr(10) + "def " not in src[k + 4:]
    assert not [ln for ln in src.splitlines() if ln.startswith(("import", "from")) and "fastapi" in ln]


# ═══════════════════════ 7. libellés traduits ══════════════════════════════

def test_les_huit_libelles_sont_traduits():
    cles = json.loads(CARTES_JSON.read_text(encoding="utf-8"))
    attendu = {
        "hex_p50": ("Hexagone 50 mm, pointe en haut", "Hexagon 50 mm, point up"),
        "hex_f90": ("Hexagone 90 mm, côté plat en haut",
                    "Hexagon 90 mm, flat side up"),
    }
    for f in HEX:
        e = cles["cartes.core.fmt_" + f]
        assert e["fr"] and e["en"] and e["fr"] != e["en"]
        assert e["fr"] == CT.FORMATS[f]["label"]
    for f, (fr, en) in attendu.items():
        assert cles["cartes.core.fmt_" + f] == {"fr": fr, "en": en}
    assert cles["cartes.core.fmt_hex_p635"]["fr"] == "Hexagone 63,5 mm, pointe en haut"
    # vague finale (C4) : l'anglais écrit le nombre à point décimal
    assert cles["cartes.core.fmt_hex_p635"]["en"] == "Hexagon 63.5 mm, point up"
    assert cles["cartes.core.fmt_hex_f635"]["en"] == "Hexagon 63.5 mm, flat side up"
    assert not [k for k, v in cles.items() if k.startswith("cartes.core.fmt_hex") and "," in v["en"].split(" mm")[0]]


# ═══════════════════════ 8. parité Python / JS ═════════════════════════════

def _bloc_hex_js() -> str:
    src = CORE_JS.read_text(encoding="utf-8")
    m = re.search(r"CF-HEX-BEGIN[^\n]*\n(.*?)\n[^\n]*CF-HEX-END", src, re.S)
    assert m, "bloc CF-HEX introuvable dans core.js"
    return m.group(1)


BANC_HEX = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
/* le demi-haut de core.js:rnd, pour arrondir le contour comme geomOf */
const rnd = (v, n) => { const p = Math.pow(10, n); return Math.floor(v * p + 0.5) / p; };
const mod = new Function(CODE + "\nreturn { hexSommets: hexSommets, hexContours: hexContours, hexDecale: hexDecale };")();
const out = CAS.map((c) => {
  const g = Object.assign({}, c.g);
  /* comme geomOf : contour arrondi a 3 decimales, c'est ce que lit hexContours */
  g.contour_mm = mod.hexSommets(g.trim_mm, g.orientation).map((p) => [rnd(p[0], 3), rnd(p[1], 3)]);
  const dec = {};
  [3, 0, -3, -26].forEach((d) => { dec[d] = mod.hexDecale(g.contour_mm, d); });
  return { contour_mm: g.contour_mm, hex: mod.hexContours(g), decale: dec };
});
process.stdout.write(JSON.stringify(out));
"""


def _proche(a, b, tol=0.001):
    assert len(a) == len(b), (len(a), len(b), a, b)
    for p, q in zip(a, b):
        assert abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol, (p, q)


def test_parite_python_js_sur_les_huit_formats():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la confrontation Python / JS ne peut pas tourner")
    cas, geoms = [], []
    for fmt in HEX:
        for dpi in (150, 300, 600):
            for bleed, safe in ((0.0, 0.0), (3.0, 3.0), (3.175, 5.0), (6.0, 2.0)):
                g = CT.geom(fmt, dpi, bleed, safe)
                geoms.append(g)
                d = g.to_dict()
                cas.append({"g": {
                    "forme": d["forme"], "orientation": d["orientation"],
                    "trim_mm": d["trim_mm"], "dpi": d["dpi"],
                    "bleed_mm": d["bleed_mm"], "safe_mm": d["safe_mm"],
                    "canvas_px": d["canvas_px"],
                    "bleed_off_px": d["bleed_off_px"]}})
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "hex.js").write_text(_bloc_hex_js(), encoding="utf-8")
    (tmp / "banc.mjs").write_text(BANC_HEX, encoding="utf-8")
    (tmp / "cas.json").write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([node, str(tmp / "banc.mjs"), str(tmp / "hex.js"),
                        str(tmp / "cas.json")],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    sortie = json.loads(r.stdout)
    assert len(sortie) == len(geoms) == 8 * 3 * 4
    for g, s in zip(geoms, sortie):
        ctx = f"{g.fmt} dpi={g.dpi} bleed={g.bleed_mm} safe={g.safe_mm}"
        _proche(g.contour_mm, s["contour_mm"])
        h = s["hex"]
        _proche(HX.contour_coupe_toile_mm(g), h["coupe"])
        _proche(HX.contour_toile_mm(g), h["fond"])
        _proche(HX.contour_sur_mm(g), h["sur"])
        _proche(HX.milieux_cotes_mm(g), h["milieux"])
        # `decale` seul, y compris le décalage qui retourne le polygone -> []
        for d in (3, 0, -3, -26):
            _proche(HX.decale(s["contour_mm"], d), s["decale"][str(d)])
        assert ctx


def test_la_table_js_porte_forme_et_orientation():
    src = CORE_JS.read_text(encoding="utf-8")
    for f in HEX:
        m = re.search(r'\{\s*id:\s*"%s".*?\}' % f, src)
        assert m, f
        meta = CT.FORMATS[f]
        assert 'forme: "hex"' in m.group(0)
        assert 'orientation: "%s"' % meta["orientation"] in m.group(0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
