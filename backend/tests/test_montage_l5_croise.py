# -*- coding: utf-8 -*-
"""L5 — BANC CROISE couche / bundle / service : ce que le lot L5 (couleur)
ecrit EN DUR d'un cote du reseau doit etre CE QUE l'autre cote lit, ou etre
DATE comme un ecart. Fichier SEPARE de test_montage_l5.py (un processus, un
code de sortie). Modele : test_montage_l7b_croise.py (regex GARDEES, le
literal ET le comportement, etat vide construit, sous-processus node qui rend
{} quand il meurt). AUCUN reseau, AUCUN serveur, AUCUN ffmpeg : les routes
sont appelees en direct avec une vraie Request starlette (client 127.0.0.1),
les couches basses (`_media_source`, `grading`, `color_match`) espionnees.
Run : & $PY tests/test_montage_l5_croise.py   (depuis backend/)

CE QUI EST COMPARE.
  [1] D-29 : `curves_clean` (effects_engine.py) == `dzmCurveClean` (la
      couche, sous node) sur les 61 vecteurs partages
      (tests/l5_courbes_vecteurs.json, sortie attendue comprise) ET sur 40
      entrees TIREES (graine fixe : separateurs, jetons invalides, exposants,
      bornes, plus de 16 points, non-chaines) + 6 cas LIMITES ecrits a la main.
  [2] D-30 : `mask_of` (mask_region.py) == `dzmMaskOf` sur 40 entrees tirees
      (formes, nombres en chaine, booleens, illisibles, debordements) + 5 cas
      LIMITES ecrits a la main.
  [3] D-27 : les bornes et defauts des neuf parametres de `wheels` au
      catalogue == les bornes du coeur (`DZM_WHEEL_B`) ET le clamp MESURE de
      `dzmWheelToRgb` (maitre a +/-100 -> la borne, neutre -> le defaut).
  [4] D-32 : `DZM_COLOR_TYPES` ⊂ `catalog()` (alias `lut` compris, et
      `lut` est bien un ALIAS) ; actions `grade_copy` / `grade_paste` dans
      le bundle avec Ctrl+Alt+C / Ctrl+Alt+V, dispatchees, uniques, et
      ABSENTES de `SVM_COMBO_RESERVED` (temoin : Ctrl+Maj+C y est).
  [5] Routes : celles que la couche appelle (`/api/montage/color-match`,
      `/scopes`, `/grade-frame`) == celles que `montage_service.py` declare
      (POST, sous le prefixe /api/montage de main.py).
  [6] Champs : les corps de `dzmFrameBody`, `dzmScopesBody` et
      `dzmMatchBody` (sous node) == les champs LUS par les routes
      (`body.get`, `tgt.get`, `ref.get`) ; puis les routes appelees AVEC ces
      corps passent aux services espionnes exactement t, effets, masque et
      largeur envoyes.

Mesure du 24/09/2026 (sommet 76987ad) : 36/0, aucune divergence entre le
service et la couche. DEUX TROUS trouves par la campagne de mutations de
cloture (mutations_montage_l5.py) et comblés AVANT le premier commit de ce
banc : n°18 (grade_copy remappee sur Ctrl+Maj+C) -- la ligne « absentes de
SVM_COMBO_RESERVED » ne lisait que le litteral : s'y ajoute la ligne des
combos EFFECTIVES des deux actions ; n°19 (/grade-frame lit `width`) -- la
sonde envoyait w=240, le DEFAUT de la route : la largeur envoyee est
desormais 320 (non defaut), et l'espion voit la difference.

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
Faute n°6 : aucune lecture nue ; un dict vide de node ou une regex qui ne
trouve rien fait ROUGIR, pas mourir.
"""
import asyncio
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl5x_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
NODE = shutil.which("node")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    """Le fichier en OCTETS, decode, LF -- ou "" (le banc rougit, ne meurt pas)."""
    p = os.path.join(ROOT, *rel.split("/"))
    try:
        return open(p, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""


def entre(texte, debut, fin):
    """La tranche [debut, fin[ si les deux bornes sont trouvees DANS L'ORDRE, sinon ""."""
    i = texte.find(debut)
    j = texte.find(fin, i + len(debut)) if i >= 0 else -1
    return texte[i:j] if 0 <= i < j else ""


def node_json(nom, script):
    """Joue le script sous node et rend le DERNIER objet JSON de sa sortie --
    ou {} avec la raison : l'etat VIDE, que chaque lecteur demasque par la
    presence de sa cle."""
    if not NODE:
        return {}, "node absent du PATH"
    p = os.path.join(TMP, nom)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script)
    try:
        r = subprocess.run([NODE, p], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {}, repr(e)
    if r.returncode != 0:
        return {}, "rc=%d %s" % (r.returncode, (r.stderr or "")[-400:])
    lignes = (r.stdout or "").strip().splitlines()
    try:
        d = json.loads(lignes[-1]) if lignes else None
    except ValueError:
        d = None
    return (d if isinstance(d, dict) else {}), ("" if isinstance(d, dict) else "sortie illisible : " + repr((r.stdout or "")[-200:]))


def REQ(path, body):
    from starlette.requests import Request as _R
    raw = json.dumps(body).encode("utf-8")

    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": path, "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": ("127.0.0.1", 5000)}, rcv)


async def appel(f, *a):
    """(code, corps) d'une route appelee en direct ; une HTTPException rend son code et son detail."""
    try:
        v = await f(*a)
        if hasattr(v, "status_code") and hasattr(v, "body"):
            try:
                return (v.status_code, json.loads(bytes(v.body).decode("utf-8")))
            except ValueError:
                return (v.status_code, None)
        return (getattr(v, "status_code", 200), v)
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


def _norm(v):
    """Les nombres en float arrondis a 1e-9 (JSON de node rend 1 pour 1.0)."""
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), 9)
    return v


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
MSV = lire("backend/app/services/montage_service.py")
MAIN = lire("backend/app/main.py")
check("x0_couche_bundle_service_et_main_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(MSV) > 100_000 and len(MAIN) > 1_000,
      (len(JS), len(BUN), len(MSV), len(MAIN)))
check("x0_node_est_sur_le_PATH", bool(NODE), NODE)

try:
    from app.services import effects_engine as ee
    from app.services import mask_region as mr
    from app.services import grading as gr
    from app.services import color_match as cm
    from app.services import montage_service as ms
except Exception as e:                       # le banc rougit, ne meurt pas
    ee = mr = gr = cm = ms = None
    print(f"  (import des services impossible : {e!r})")
check("x0_services_importes_avec_les_symboles_L5",
      None not in (ee, mr, gr, cm, ms)
      and all(hasattr(ee, k) for k in ("curves_clean", "catalog", "EFFECTS", "_ALIASES"))
      and hasattr(mr, "mask_of") and all(hasattr(gr, k) for k in ("graded_frame", "scopes_png"))
      and all(hasattr(cm, k) for k in ("frame_stats", "match_effect", "auto_effect"))
      and all(hasattr(ms, k) for k in ("montage_color_match", "montage_scopes", "montage_grade_frame",
                                       "_media_source", "router")),
      (ee, mr, gr, cm, ms))

try:
    VEC = json.loads(open(os.path.join(HERE, "l5_courbes_vecteurs.json"), "rb").read().decode("utf-8"))
except (OSError, ValueError):
    VEC = []
VEC = [v for v in VEC if isinstance(v, dict) and "in" in v and "out" in v] if isinstance(VEC, list) else []

# ── les entrees TIREES (graine fixe) : courbes puis masques ─────────────────
random.seed(24092026)


def _nb():
    v = random.uniform(-0.3, 1.3)
    r = random.random()
    if r < 0.1:
        return "%.1e" % v
    if r < 0.15:
        return ("+" if v >= 0 else "") + ("%g" % v).lstrip("0") if abs(v) < 1 else "%g" % v
    return str(round(v, random.choice([0, 1, 2, 3, 4, 5])))


_MAUVAIS = ["abc", "1/2/3", "1_0/0.5", "inf/0.5", "nan/1", "1e999/0.5", "0.5/", "/0.5", "0x1/0.5",
            "٠.٥/0.5", "0.5/0.5\x0b0.2/0.1", "0.5//0.5", ".", "1e/0.5", "--0.1/0.2"]
_SEPS = [" ", " ", " ", "\t", ",", ", ", "\n", "\r\n", "  ", " "]


def _courbe():
    r = random.random()
    if r < 0.06:
        return random.choice([None, 5, 0.5, [], {}, True, ["0/0", "1/1"]])
    n = random.choice([0, 1, 2, 3, 5, 8, 16, 17, 20, 40])
    toks = []
    for _ in range(n):
        toks.append(random.choice(_MAUVAIS) if random.random() < 0.15 else _nb() + "/" + _nb())
    s = ""
    for t in toks:
        s += t + random.choice(_SEPS)
    return (random.choice(["", " ", ",", "\t"]) + s) if random.random() < 0.3 else s.strip(" ")


def _num_m(lo, hi):
    r = random.random()
    if r < 0.07:
        return random.choice([None, True, False, "abc", "", " 0.25 ", "1e-1", "0x10", "1_0", "﻿0.3",
                              "٠.٥", "Infinity", 1e9, -1e9, "0.5", " .5", "+.5", [], {}])
    v = random.uniform(lo, hi)
    return str(round(v, 3)) if random.random() < 0.15 else round(v, random.choice([0, 2, 3, 4, 6]))


def _masque():
    r = random.random()
    if r < 0.05:
        return random.choice([None, [], "ellipse", 3, {"shape": "rect"}])
    m = {"shape": random.choice(["rect", "ellipse", "ellipse", "rect", "rect", "zz", None, ""])}
    for k in ("x", "y"):
        m[k] = _num_m(-0.15, 0.95)
    for k in ("w", "h"):
        m[k] = _num_m(-0.05, 0.9)
    if random.random() < 0.8:
        m["soft"] = _num_m(-0.2, 0.8)
    if random.random() < 0.7:
        m["inv"] = random.choice([True, False, "true", 1, None, True])
    return m


COURBES = [_courbe() for _ in range(40)]
MASQUES = [_masque() for _ in range(40)]
N_TIRES = 40
# cas LIMITES ecrits a la main (apres les 40 tirages) : plafond de 16 points (20 et 17 points, virgules), un
# jeton invalide au milieu, blancs seuls, BOM en tete (jeton invalide des deux cotes), exposants
COURBES += [", ".join("%g/%g" % (i / 19, (i / 19) ** 2) for i in range(20)),
            " ".join("%g/%g" % (i / 16, 1 - i / 16) for i in range(17)) + " zz",
            "0/0 0.25/0.1 x 0.75/0.9 1/1", " \t\n ", "﻿0.5/0.6 0.2/0.1", "5e-1/7E-1 1e0/1e0 0e0/0"]
MASQUES += [{"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.1, "inv": True},
            {"shape": "rect", "x": "0.9", "y": 0.95, "w": 0.5, "h": 0.5},
            {"shape": "rect", "x": 0.995, "y": 0, "w": 1, "h": 1},
            {"shape": "ellipse", "x": 0, "y": 0, "w": 1, "h": 1, "soft": 9, "inv": "true"},
            {"shape": "rect", "x": 0.123456789, "y": 0.00005, "w": 0.33335, "h": 0.66665, "soft": -1}]

_PROBE = r"""
var T=DzTracks,out={};
var VIN=__VIN__,CIN=__CIN__,MIN=__MIN__;
out.vec=VIN.map(function(s){return dzmCurveClean(s)});
out.cc=CIN.map(function(s){return dzmCurveClean(s)});
out.mk=MIN.map(function(m){var r=dzmMaskOf(m);return r===void 0?"UNDEF":r});
out.color_types=DZM_COLOR_TYPES.slice();
out.wheel_b=DZM_WHEEL_B;
out.wheel_clamp={};
["lift","gamma","gain"].forEach(function(k){
  out.wheel_clamp[k]={haut:dzmWheelToRgb(k,0,0,100),bas:dzmWheelToRgb(k,0,0,-100),neutre:dzmWheelToRgb(k,0,0,0),
    rouge:dzmWheelToRgb(k,0,1,.8)}});
var C={tr:"v1",id:"c1",src:{job_id:"j1"},srcIn:2,start:10,end:14,speed:1,
  effects:[{type:"wheels",gain_r:1.5,t0:1,t1:2},{type:"grain",off:true},{type:"curves",pts_m:"0/0 0.5/0.7 1/1"}],
  mask:{shape:"ellipse",x:.25,y:.25,w:.5,h:.5,soft:.1,inv:false}};
var P={tr:"v1",id:"c0",src:{job_id:"j0"},srcIn:0,start:0,end:10};
out.frame=dzmFrameBody(C,11,320);
out.frame_nu=dzmFrameBody({tr:"v1",id:"c2",src:{job_id:"j2"},start:0,end:2},1,240);
out.scopes=dzmScopesBody(C,11);
out.match_ref=dzmMatchBody(C,11,P,!1);
out.match_auto=dzmMatchBody(C,11,null,!0);
out.fetch_urls=[];
console.log(JSON.stringify(out));
"""
_shim = ('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n"
         + _PROBE.replace("__VIN__", json.dumps([v["in"] for v in VEC]))
         .replace("__CIN__", json.dumps(COURBES)).replace("__MIN__", json.dumps(MASQUES)))
D, _dwhy = node_json("l5x_couche.js", _shim)
check("x0_la_couche_s_execute_sous_node_et_rend_les_cles_de_la_sonde",
      bool(D) and all(k in D for k in ("vec", "cc", "mk", "color_types", "wheel_b", "wheel_clamp", "frame",
                                       "scopes", "match_ref", "match_auto")),
      _dwhy or sorted(D))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[1] D-29 : curves_clean (service) == dzmCurveClean (couche) sur %d vecteurs, %d tirages et %d cas limites"
      % (len(VEC), N_TIRES, len(COURBES) - N_TIRES))


def _py_cc(s):
    try:
        return ee.curves_clean(s)
    except Exception as e:
        return "LEVE %s" % type(e).__name__


PYV = [_py_cc(v["in"]) for v in VEC] if ee is not None else []
JSV = D.get("vec") if isinstance(D.get("vec"), list) else []
ATT = [v["out"] for v in VEC]
check("x1_les_61_vecteurs_partages_sont_lus",
      len(VEC) == 61 and len(PYV) == 61 and len(JSV) == 61, (len(VEC), len(PYV), len(JSV)))
DV = [(i, VEC[i]["in"], ATT[i], PYV[i], JSV[i]) for i in range(min(len(PYV), len(JSV)))
      if not (PYV[i] == JSV[i] == ATT[i])]
check("x1_vecteurs_service_couche_et_sortie_attendue_egaux_aucune_divergence",
      len(PYV) == len(JSV) == 61 and DV == [], DV[:3])
PYC = [_py_cc(s) for s in COURBES] if ee is not None else []
JSC = D.get("cc") if isinstance(D.get("cc"), list) else []
_n_id = sum(1 for v in PYC if v == "0/0 1/1")
_n_16 = sum(1 for v in PYC if isinstance(v, str) and v.count("/") == 16)
_n_ns = sum(1 for s in COURBES if not isinstance(s, str))
check("x1_le_tirage_couvre_identite_plafond_16_points_non_chaines_et_courbes_ordinaires",
      len(PYC) == len(JSC) == len(COURBES) == N_TIRES + 6 and _n_id >= 3 and _n_16 >= 3 and _n_ns >= 1
      and len(PYC) - _n_id >= 20,
      (len(PYC), len(JSC), _n_id, _n_16, _n_ns))
DC = [(i, COURBES[i], PYC[i], JSC[i]) for i in range(min(len(PYC), len(JSC))) if PYC[i] != JSC[i]]
check("x1_tirages_service_et_couche_rendent_la_meme_chaine_canonique_aucune_divergence",
      len(PYC) == len(JSC) == N_TIRES + 6 and DC == [], DC[:3])
# ETAT VIDE : le meme comparateur VOIT une divergence fabriquee (dernier caractere change)
_i1 = next((i for i, v in enumerate(PYC) if v != "0/0 1/1"), None)
_faux1 = (JSC[_i1][:-1] + ("0" if JSC[_i1][-1] != "0" else "1")) if _i1 is not None and _i1 < len(JSC) else None
check("x1_etat_vide_le_comparateur_voit_une_divergence_fabriquee_temoin_egal_avant",
      _i1 is not None and PYC[_i1] == JSC[_i1] and _faux1 is not None and _faux1 != PYC[_i1], _i1)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[2] D-30 : mask_of (service) == dzmMaskOf (couche) sur %d tirages et %d cas limites"
      % (N_TIRES, len(MASQUES) - N_TIRES))


def _py_mk(m):
    try:
        return mr.mask_of(m)
    except Exception as e:
        return "LEVE %s" % type(e).__name__


PYM = [_norm(_py_mk(m)) for m in MASQUES] if mr is not None else []
JSM = [_norm(v) for v in D.get("mk", [])] if isinstance(D.get("mk"), list) else []
_n_ok = sum(1 for v in PYM if isinstance(v, dict))
_n_ell = sum(1 for v in PYM if isinstance(v, dict) and v.get("shape") == "ellipse")
_n_inv = sum(1 for v in PYM if isinstance(v, dict) and v.get("inv") is True)
check("x2_le_tirage_couvre_masques_valides_ellipses_rectangles_inverses_et_refus",
      len(PYM) == len(JSM) == N_TIRES + 5 and _n_ok >= 12 and 1 <= _n_ell < _n_ok and _n_inv >= 1 and len(PYM) - _n_ok >= 10,
      (len(PYM), len(JSM), _n_ok, _n_ell, _n_inv))
DM = [(i, MASQUES[i], PYM[i], JSM[i]) for i in range(min(len(PYM), len(JSM))) if PYM[i] != JSM[i]]
check("x2_service_et_couche_rendent_le_meme_masque_aucune_divergence",
      len(PYM) == len(JSM) == N_TIRES + 5 and DM == [], DM[:3])
_i2 = next((i for i, v in enumerate(PYM) if isinstance(v, dict)), None)
_faux2 = json.loads(json.dumps(JSM[_i2])) if _i2 is not None and _i2 < len(JSM) else None
if isinstance(_faux2, dict):
    _faux2["soft"] = round(_faux2["soft"] + 0.0001, 9)
check("x2_etat_vide_le_comparateur_voit_une_divergence_fabriquee_temoin_egal_avant",
      _i2 is not None and PYM[_i2] == JSM[_i2] and isinstance(_faux2, dict) and _faux2 != PYM[_i2], _i2)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[3] D-27 : bornes de wheels au catalogue == bornes du coeur (DZM_WHEEL_B et clamp de dzmWheelToRgb)")
CAT = ee.catalog() if ee is not None else {}
WB = CAT.get("wheels", {}).get("bounds", {}) if isinstance(CAT.get("wheels"), dict) else {}
JB = D.get("wheel_b") if isinstance(D.get("wheel_b"), dict) else {}
WC = D.get("wheel_clamp") if isinstance(D.get("wheel_clamp"), dict) else {}
check("x3_wheels_au_catalogue_neuf_parametres_et_coeur_trois_genres",
      sorted(CAT.get("wheels", {}).get("params", [])) == sorted(f"{k}_{c}" for k in ("lift", "gamma", "gain") for c in "rgb")
      and sorted(JB) == ["gain", "gamma", "lift"] and sorted(WC) == ["gain", "gamma", "lift"], (sorted(WB), sorted(JB)))
_diffb = []
for k in ("lift", "gamma", "gain"):
    for c in "rgb":
        s = WB.get(f"{k}_{c}") or {}
        jb = JB.get(k) or [None, None, None]
        if [s.get("min"), s.get("max"), s.get("default")] != jb or s.get("type") != "range":
            _diffb.append((k, c, s, jb))
check("x3_min_max_defaut_des_neuf_parametres_egaux_a_DZM_WHEEL_B",
      len(WB) == 9 and len(JB) == 3 and _diffb == [], _diffb)
_diffc = []
for k in ("lift", "gamma", "gain"):
    w = WC.get(k) or {}
    s = WB.get(f"{k}_r") or {}
    for cle, att in (("haut", s.get("max")), ("bas", s.get("min")), ("neutre", s.get("default"))):
        got = w.get(cle) or {}
        if [got.get(c) for c in "rgb"] != [att] * 3:
            _diffc.append((k, cle, got, att))
check("x3_clamp_mesure_maitre_plus_moins_100_rend_la_borne_du_catalogue_neutre_le_defaut",
      len(WC) == 3 and _diffc == [], _diffc)
# temoin : une roue POUSSEE vers le rouge sature R a la borne haute sans que G et B la depassent
_rg = (WC.get("gain") or {}).get("rouge") or {}
check("x3_temoin_roue_gain_poussee_au_rouge_R_a_la_borne_haute_G_B_dans_les_bornes",
      _rg.get("r") == (WB.get("gain_r") or {}).get("max") == 2
      and all(0 <= (_rg.get(c) if isinstance(_rg.get(c), (int, float)) else -1) < 2 for c in "gb"), _rg)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[4] D-32 : DZM_COLOR_TYPES ⊂ catalogue ; actions grade_copy / grade_paste au bundle, non reservees")
CT = D.get("color_types") if isinstance(D.get("color_types"), list) else []
check("x4_DZM_COLOR_TYPES_huit_types_tous_au_catalogue_lut_compris_et_lut_est_un_alias",
      len(CT) == 8 and "lut" in CT and len(CAT) > 40 and sorted(set(CT) - set(CAT)) == []
      and getattr(ee, "_ALIASES", {}).get("lut") == "grade" and all(t in getattr(ee, "EFFECTS", {}) for t in CT),
      (CT, sorted(set(CT) - set(CAT))))
check("x4_temoin_les_huit_sont_des_effets_couleur_de_la_categorie_etalonnage_sauf_l_alias",
      len(CT) == 8 and all((CAT.get(t) or {}).get("cat") == "etalonnage" for t in CT if t != "lut"),
      [(t, (CAT.get(t) or {}).get("cat")) for t in CT])
ACT = entre(BUN, "var SVM_ACTIONS=[", "var SVM_KEY_SECTIONS=")
_combos = re.findall(r'\{id:"([a-z_0-9]+)",[^\n]*?combo:"([^"]*)"\}', ACT)
_cmap = {}
for _id, _cb in _combos:
    _cmap.setdefault(_cb, []).append(_id)
check("x4_grade_copy_Ctrl_Alt_C_et_grade_paste_Ctrl_Alt_V_une_fois_chacune_au_bundle",
      len(_combos) > 40 and ("grade_copy", "Ctrl+Alt+C") in _combos and ("grade_paste", "Ctrl+Alt+V") in _combos
      and BUN.count('id:"grade_copy"') == 1 and BUN.count('id:"grade_paste"') == 1,
      (len(_combos), [c for c in _combos if c[0].startswith("grade")]))
check("x4_aucune_autre_action_ne_porte_Ctrl_Alt_C_ni_Ctrl_Alt_V",
      _cmap.get("Ctrl+Alt+C") == ["grade_copy"] and _cmap.get("Ctrl+Alt+V") == ["grade_paste"],
      (_cmap.get("Ctrl+Alt+C"), _cmap.get("Ctrl+Alt+V")))
_mres = re.search(r"var SVM_COMBO_RESERVED=(\{[^}]*\});", BUN)
try:
    RES = json.loads(_mres.group(1)) if _mres else {}
except ValueError:
    RES = {}
check("x4_Ctrl_Alt_C_V_absentes_de_SVM_COMBO_RESERVED_temoin_Ctrl_Maj_C_y_est",
      len(RES) >= 10 and "Ctrl+Maj+C" in RES and "Ctrl+Alt+C" not in RES and "Ctrl+Alt+V" not in RES, sorted(RES))
# cloture (campagne de mutations, n°18) : la ligne du dessus ne regarde que le LITTERAL Ctrl+Alt+C -- une action
# remappee sur une combo reservee la laissait verte. Ici : les combos EFFECTIVES des deux actions, lues au bundle.
_gc = [cb for i_, cb in _combos if i_ in ("grade_copy", "grade_paste")]
check("x4_les_combos_effectives_de_grade_copy_et_grade_paste_ne_sont_pas_reservees",
      len(_gc) == 2 and len(RES) >= 10 and all(cb and cb not in RES for cb in _gc), (_gc, sorted(RES)))
check("x4_les_deux_actions_sont_dispatchees_vers_les_gestes_de_l_hote",
      BUN.count('if(id==="grade_copy"){dzGradeCopy(selRef.current);return}') == 1
      and BUN.count('if(id==="grade_paste"){dzGradePaste(selRef.current);return}') == 1
      and BUN.count("function dzGradeCopy(") == 1 and BUN.count("function dzGradePaste(") == 1,
      (BUN.count("function dzGradeCopy("), BUN.count("function dzGradePaste(")))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[5] Routes : celles que la couche appelle == celles que montage_service declare (POST)")
APPELS = set(re.findall(r'dzmGpFetch\("(/api/montage/[a-z-]+)"', JS))
DECL = set("/api/montage" + p for p in re.findall(r'@router\.post\("(/(?:color-match|scopes|grade-frame))"\)', MSV))
_rts = {}
if ms is not None:
    for _r in getattr(ms.router, "routes", []):
        if getattr(_r, "path", "") in ("/color-match", "/scopes", "/grade-frame"):
            _rts.setdefault(_r.path, set()).update(getattr(_r, "methods", set()) or set())
# L6 (25/09/2026, tache 5) : « Apprendre le bruit » (DzmNoiseLearn) REUTILISE dzmGpFetch pour POST /noise-profile -- une
# quatrieme route, voulue (pas de copie du client reseau). Les TROIS routes L5 restent exigees, egales a DECL ; la
# declaration de /noise-profile (tache 2 du lot L6) est tenue par le banc croise L6 (tache 7), pas ici.
_L6_APPELS = {"/api/montage/noise-profile"}
check("x5_la_couche_appelle_trois_routes_par_dzmGpFetch_en_POST",
      APPELS == {"/api/montage/color-match", "/api/montage/scopes", "/api/montage/grade-frame"} | _L6_APPELS
      and JS.count('var op={method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};') == 1,
      sorted(APPELS))
check("x5_ces_routes_sont_declarees_POST_seulement_sous_le_prefixe_de_main",
      DECL == APPELS - _L6_APPELS and MAIN.count('app.include_router(montage_router, prefix="/api/montage")') == 1
      and {k: sorted(v) for k, v in _rts.items()} == {"/color-match": ["POST"], "/scopes": ["POST"], "/grade-frame": ["POST"]},
      (sorted(DECL), {k: sorted(v) for k, v in _rts.items()}))
# temoin : une route que la couche appelle ailleurs (strip, GET) n'est pas comptee ici
check("x5_temoin_strip_est_appelee_par_la_couche_mais_hors_des_trois",
      '"/api/montage/strip' in JS and "/api/montage/strip" not in APPELS and len(APPELS - _L6_APPELS) == 3 and len(APPELS) == 4,
      sorted(APPELS))  # L6 (T5, 25/09) : 3 -> 4 (noise-profile), les trois L5 comptees a part

# ═════════════════════════════════════════════════════════════════════════════
print("\n[6] Champs : corps de dzmFrameBody / dzmScopesBody / dzmMatchBody == champs lus par les routes")
R_CM = entre(MSV, "async def montage_color_match(request: Request):", "\n_SCOPES_MAX")
R_SC = entre(MSV, "async def montage_scopes(request: Request):", '\n@router.post("/grade-frame")')
R_GF = entre(MSV, "async def montage_grade_frame(request: Request):", '\n@router.post("/proxy")')
LU_CM = set(re.findall(r'\bbody\.get\("([a-z_]+)"\)', R_CM))
LU_TGT = set(re.findall(r'\btgt\.get\("([a-z_]+)"\)', R_CM))
LU_REF = set(re.findall(r'\bref\.get\("([a-z_]+)"\)', R_CM))
LU_SC = set(re.findall(r'\bbody\.get\("([a-z_]+)"\)', R_SC))
LU_GF = set(re.findall(r'\bbody\.get\("([a-z_]+)"\)', R_GF))
check("x6_les_trois_routes_trouvees_et_leurs_lectures_mesurees",
      len(R_CM) > 800 and len(R_SC) > 400 and len(R_GF) > 300 and {"target", "ref", "auto"} <= LU_CM
      and {"src", "t"} <= LU_TGT and {"src", "t"} <= LU_REF and {"src", "t"} <= LU_SC and {"src", "t"} <= LU_GF,
      (len(R_CM), len(R_SC), len(R_GF), sorted(LU_CM), sorted(LU_SC), sorted(LU_GF)))
FR = D.get("frame") if isinstance(D.get("frame"), dict) else {}
SC = D.get("scopes") if isinstance(D.get("scopes"), dict) else {}
MR = D.get("match_ref") if isinstance(D.get("match_ref"), dict) else {}
MA = D.get("match_auto") if isinstance(D.get("match_auto"), dict) else {}
check("x6_grade_frame_champs_envoyes_src_t_w_effects_mask_egaux_aux_champs_lus",
      set(FR) == {"src", "t", "w", "effects", "mask"} and set(FR) == LU_GF, (sorted(FR), sorted(LU_GF)))
check("x6_scopes_champs_envoyes_src_t_effects_mask_egaux_aux_champs_lus_sans_largeur",
      set(SC) == {"src", "t", "effects", "mask"} and set(SC) == LU_SC and "w" not in LU_SC, (sorted(SC), sorted(LU_SC)))
check("x6_color_match_corps_ref_et_auto_egaux_aux_champs_lus_cible_et_reference_src_t",
      set(MR) == {"target", "ref"} and set(MA) == {"target", "auto"} and set(MR) | set(MA) == LU_CM
      and set(MR.get("target") or {}) == LU_TGT == {"src", "t"} and set(MR.get("ref") or {}) == LU_REF == {"src", "t"}
      and MA.get("auto") is True, (MR, MA, sorted(LU_CM)))
# temoin : sans effet allume, ni effets ni masque ne partent (les routes les lisent optionnels)
FN = D.get("frame_nu") if isinstance(D.get("frame_nu"), dict) else {}
check("x6_temoin_plan_sans_effet_corps_src_t_w_seulement",
      set(FN) == {"src", "t", "w"} and len(FR) == 5, (sorted(FN), sorted(FR)))
check("x6_le_corps_ne_porte_pas_l_effet_eteint_et_porte_le_masque_borne",
      [e.get("type") for e in FR.get("effects") or []] == ["wheels", "curves"] and isinstance(FR.get("mask"), dict)
      and FR["mask"].get("shape") == "ellipse" and FR.get("t") == 3 and FR.get("w") == 320,
      FR)

# COMPORTEMENT : les routes appelees AVEC les corps de la couche passent aux services espionnes ce qui a ete envoye
_vus = []
_FAUX = pathlib.Path(TMP) / "src.mp4"
_FAUX.write_bytes(b"x")


async def _src(request, src, *, video=False):
    _vus.append(("src", src, video))
    return _FAUX


def _gf(p, t, effects=None, mask=None, w=512, fmt="png"):
    _vus.append(("gf", t, effects, mask, w, fmt))
    return _FAUX


def _sp(p, t, effects=None, mask=None):
    _vus.append(("sp", t, effects, mask))
    return _FAUX


def _fs(p, t=1.0):
    _vus.append(("fs", t))
    return {"y": (120.0, 30.0), "u": (128.0, 5.0), "v": (128.0, 5.0)}


_res6 = {}
if ms is not None and gr is not None and cm is not None and FR and SC and MR and MA:
    _o = (ms._media_source, gr.graded_frame, gr.scopes_png, cm.frame_stats)
    ms._media_source, gr.graded_frame, gr.scopes_png, cm.frame_stats = _src, _gf, _sp, _fs
    try:
        _vus.clear()
        _res6["gf"] = (asyncio.run(appel(ms.montage_grade_frame, REQ("/api/montage/grade-frame", FR)))[0], list(_vus))
        _vus.clear()
        _res6["sc"] = (asyncio.run(appel(ms.montage_scopes, REQ("/api/montage/scopes", SC)))[0], list(_vus))
        _vus.clear()
        _res6["mr"] = (asyncio.run(appel(ms.montage_color_match, REQ("/api/montage/color-match", MR))), list(_vus))
        _vus.clear()
        _res6["ma"] = (asyncio.run(appel(ms.montage_color_match, REQ("/api/montage/color-match", MA))), list(_vus))
    finally:
        ms._media_source, gr.graded_frame, gr.scopes_png, cm.frame_stats = _o
_gfv = _res6.get("gf", (None, []))
check("x6_grade_frame_appelee_avec_le_corps_passe_t_effets_masque_largeur_tels_quels_en_jpg",
      _gfv[0] == 200 and ("src", FR.get("src"), True) in _gfv[1]
      and ("gf", FR.get("t"), FR.get("effects"), FR.get("mask"), 320, "jpg") in _gfv[1], _gfv)
_scv = _res6.get("sc", (None, []))
check("x6_scopes_appelee_avec_le_corps_passe_t_effets_masque_tels_quels",
      _scv[0] == 200 and ("sp", SC.get("t"), SC.get("effects"), SC.get("mask")) in _scv[1], _scv)
_mrv = _res6.get("mr", ((None, None), []))
_tr, _rf = (MR.get("target") or {}), (MR.get("ref") or {})
check("x6_color_match_ref_lit_les_deux_sources_et_les_deux_instants_envoyes",
      _mrv[0][0] == 200 and ("src", _tr.get("src"), True) in _mrv[1] and ("src", _rf.get("src"), True) in _mrv[1]
      and sorted(v[1] for v in _mrv[1] if v[0] == "fs") == sorted([_tr.get("t"), _rf.get("t")])
      and isinstance(_mrv[0][1], dict) and (_mrv[0][1].get("effect") or {}).get("type") == "colormatch", _mrv)
_mav = _res6.get("ma", ((None, None), []))
check("x6_color_match_auto_une_seule_source_ref_nulle_effet_colormatch",
      _mav[0][0] == 200 and [v[0] for v in _mav[1]] == ["src", "fs"] and isinstance(_mav[0][1], dict)
      and _mav[0][1].get("ref") is None and (_mav[0][1].get("effect") or {}).get("type") == "colormatch", _mav)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
