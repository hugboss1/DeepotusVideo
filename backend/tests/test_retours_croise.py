# -*- coding: utf-8 -*-
"""Retours L6 — BANC CROISE couche / service : ce que les retours du 26/09
(image etalonnee dans le lecteur, scopes flottants) ecrivent EN DUR d'un cote
du reseau doit etre CE QUE l'autre cote lit, ou etre DECLARE comme un ecart.
Fichier SEPARE (un processus, un code de sortie). Modele :
test_montage_l5_croise.py et son vecteur l5_courbes_vecteurs.json (regex
GARDEES, le literal ET le comportement, etat vide construit, sous-processus
node qui rend {} quand il meurt). AUCUN reseau, AUCUN serveur, AUCUN
ffmpeg : les routes sont jouees par un TestClient SANS lifespan (hote
« testclient », accepte par `_require_localhost`), les couches basses
(`_media_source`, `grading.graded_frame`, `grading.scopes_png`) espionnees.
Run : & $PY tests/test_retours_croise.py   (depuis backend/)

CE QUI EST COMPARE.
  [1] Bornes t0/t1 d'un effet en mode cadre : `dzmGlActif` (la couche, sous
      node) == `grading._au_temps` (Python) == `attendu` sur la table
      PARTAGEE tests/retours_bornes_vecteurs.json ({t0, t1, t_local, dur,
      attendu} ; ±inf / NaN en JETONS {"$num": …} decodes en natifs de chaque
      cote) ; les chaines ou float() et la couche divergent (chiffres non
      ASCII) sont DECLAREES dans la table et le banc prouve qu'elles
      divergent exactement comme declare.
  [2] Corps : `dzmGlBody` (image etalonnee du lecteur) et `dzmScwBody`
      (scopes flottants), fabriques par la couche sous node, sont ACCEPTES par
      les routes (200) et le service espionne recoit le cadre normalise
      `_cadre_of(cadre du client)`, la largeur / taille envoyees, les effets
      et le masque ; les cles du cadre client ⊂ celles que lit `_cadre_of`.
  [3] Bornes : `dzmGlW` et `dzmScwSize` (client) == `_cadre_w` et
      `_scopes_size` (serveur) — minimum, maximum, defaut, parite : toute
      valeur que le client produit est un POINT FIXE du serveur.
  [4] Ratios : `DZM_GL_RATIOS` ⊂ `_CANVAS` (les quatre, ceux du rendu) ;
      repli du client (dzmGlRatio) == repli de `_cadre_of` (9:16).
  [5] Routes : celles que la couche appelle par dzmGpFetch (grade-frame,
      scopes, …) sont declarees POST par montage_service sous /api/montage.

Mesure du 26/09/2026 (sommet 15d1ba7) : voir le compte en fin de sortie.
Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif. Faute n°6 : aucune lecture nue.
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

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzrtx_")
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


def node_json(nom, script):
    """Joue le script sous node et rend le DERNIER objet JSON de sa sortie --
    ou {} avec la raison (l'etat VIDE, demasque par la presence des cles)."""
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


JS = lire("frontend/patches/montage.js")
MSV = lire("backend/app/services/montage_service.py")
MAIN = lire("backend/app/main.py")
check("x0_couche_service_et_main_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(MSV) > 100_000 and len(MAIN) > 1_000, (len(JS), len(MSV), len(MAIN)))
check("x0_node_est_sur_le_PATH", bool(NODE), NODE)

try:
    from app.services import grading as gr
    from app.services import montage_service as ms
except Exception as e:                       # le banc rougit, ne meurt pas
    gr = ms = None
    print(f"  (import des services impossible : {e!r})")
check("x0_services_importes_avec_les_symboles_des_retours",
      None not in (gr, ms) and all(hasattr(gr, k) for k in ("_au_temps", "graded_frame", "scopes_png"))
      and all(hasattr(ms, k) for k in ("_cadre_of", "_cadre_w", "_scopes_size", "_CANVAS", "_media_source",
                                       "montage_grade_frame", "montage_scopes", "router",
                                       "_CADRE_W_MIN", "_CADRE_W_MAX", "_CADRE_W_DEFAUT",
                                       "_SCOPES_SIZE_MIN", "_SCOPES_SIZE_MAX", "_SCOPES_SIZE_DEFAUT")),
      (gr, ms))

try:
    TAB = json.loads(open(os.path.join(HERE, "retours_bornes_vecteurs.json"), "rb").read().decode("utf-8"))
except (OSError, ValueError):
    TAB = {}
CAS = [c for c in (TAB.get("cas") or []) if isinstance(c, dict) and "attendu" in c and "t_local" in c] \
    if isinstance(TAB, dict) else []
DIV = [c for c in (TAB.get("divergences") or []) if isinstance(c, dict) and "python" in c and "couche" in c] \
    if isinstance(TAB, dict) else []

_JETONS = {"nan": float("nan"), "inf": float("inf"), "-inf": float("-inf")}


def py_dec(v):
    """Jeton {"$num": "nan"|"inf"|"-inf"} -> float natif ; le reste tel quel."""
    if isinstance(v, dict) and set(v) == {"$num"} and v["$num"] in _JETONS:
        return _JETONS[v["$num"]]
    return v


def py_actif(c):
    """grading._au_temps sur UN effet de la table -> True / False, ou "LEVE …"."""
    e = {"type": "x"}
    for k in ("t0", "t1"):
        if k in c:
            e[k] = py_dec(c[k])
    try:
        return bool(gr._au_temps([e], float(c["t_local"]), py_dec(c.get("dur"))))
    except Exception as ex:                  # noqa: BLE001
        return "LEVE %s" % type(ex).__name__


# ── la sonde : la couche sous node ────────────────────────────────────────────
_PROBE = r"""
var out={};
var CAS=__CAS__,DIV=__DIV__;
function dec(v){if(v&&typeof v==="object"&&!Array.isArray(v)&&Object.keys(v).length===1&&"$num" in v){
  return v.$num==="nan"?NaN:v.$num==="inf"?Infinity:v.$num==="-inf"?-Infinity:v}return v}
function actif(c){var f={type:"x"};if("t0" in c)f.t0=dec(c.t0);if("t1" in c)f.t1=dec(c.t1);
  try{return !!dzmGlActif(f,c.t_local,dec(c.dur))}catch(e){return "LEVE "+e}}
out.cas=CAS.map(actif);
out.div=DIV.map(actif);
/* [2] les corps : un plan V1 avec source, deux effets (l'un borne, l'autre eteint), un masque, recadrage manuel et zoom */
var C={tr:"v1",id:"c1",src:{job_id:"j1"},srcIn:2,start:10,end:14,speed:1,
  effects:[{type:"negate",t0:1,t1:3},{type:"grain",off:true},{type:"wheels",gain_r:1.2}],
  mask:{shape:"ellipse",x:.25,y:.25,w:.5,h:.5,soft:.1,inv:false},
  reframe:{mode:"manuel",x:.3},dz:{x0:0,y0:0,w0:1,x1:.2,y1:.1,w1:.6,ease:"lin"}};
out.gl=dzmGlBody(C,11.5,"16:9");
if(out.gl)out.gl.w=dzmGlW(333.5,2);
out.scw=dzmScwBody(C,11.5,"1:1",300,1.5);
out.gl_nu=dzmGlBody({tr:"v1",id:"c2",src:{job_id:"j2"},start:0,end:2},1,"9:16");
out.gl_hors=dzmGlBody(Object.assign({},C,{effects:[{type:"negate",t0:3,t1:4}]}),11.5,"9:16");
/* [3] bornes */
out.glw=[dzmGlW(1,1),dzmGlW(10000,1),dzmGlW(null,1),dzmGlW(0,1),dzmGlW(-5,2),dzmGlW(333,1),dzmGlW(640,1.5),dzmGlW(95,1),dzmGlW(1281,1)];
out.scws=[dzmScwSize(1,1),dzmScwSize(10000,1),dzmScwSize(null,1),dzmScwSize(0,1),dzmScwSize(333,1),dzmScwSize(300,1.5),dzmScwSize(255,1),dzmScwSize(1025,1)];
out.scw_def=DZM_SCW_DEF;
var i,gw=[],sz=[];for(i=0;i<=1400;i+=7){gw.push(dzmGlW(i,1));gw.push(dzmGlW(i,1.25));sz.push(dzmScwSize(i,1));sz.push(dzmScwSize(i,2))}
out.glw_tous=gw;out.scws_tous=sz;
/* [4] ratios */
out.ratios=DZM_GL_RATIOS.slice();
out.repli=[dzmGlRatio("3:4"),dzmGlRatio(null),dzmGlRatio(["9:16"]),dzmGlRatio("16:9")];
console.log(JSON.stringify(out));
"""
_shim = ('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n"
         + _PROBE.replace("__CAS__", json.dumps(CAS)).replace("__DIV__", json.dumps(DIV)))
D, _dwhy = node_json("rtx_couche.js", _shim)
check("x0_la_couche_s_execute_sous_node_et_rend_les_cles_de_la_sonde",
      bool(D) and all(k in D for k in ("cas", "div", "gl", "scw", "gl_nu", "gl_hors", "glw", "scws", "ratios", "repli")),
      _dwhy or sorted(D))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[1] bornes t0/t1 : dzmGlActif (couche) == grading._au_temps (service) == attendu, table partagee de %d cas"
      % len(CAS))
PYA = [py_actif(c) for c in CAS] if gr is not None else []
JSA = D.get("cas") if isinstance(D.get("cas"), list) else []
ATT = [c["attendu"] for c in CAS]
_jet = sum(1 for c in CAS if any(isinstance(c.get(k), dict) and "$num" in c.get(k) for k in ("t0", "t1")))
_nan = sum(1 for c in CAS if any((isinstance(c.get(k), dict) and c.get(k).get("$num") == "nan")
                                  or (isinstance(c.get(k), str) and "nan" in c.get(k).lower()) for k in ("t0", "t1")))
check("x1_table_lue_au_moins_60_cas_jetons_nan_et_infinis_presents_les_deux_verdicts",
      len(CAS) >= 60 and len(PYA) == len(JSA) == len(CAS) and _jet >= 10 and _nan >= 8
      and True in ATT and False in ATT and sum(1 for a in ATT if a is False) >= 20,
      (len(CAS), len(PYA), len(JSA), _jet, _nan))
DV = [(i, CAS[i], ATT[i], PYA[i], JSA[i]) for i in range(min(len(PYA), len(JSA))) if not (PYA[i] is JSA[i] is ATT[i])]
check("x1_service_couche_et_attendu_egaux_sur_toute_la_table_aucune_divergence",
      len(PYA) == len(JSA) == len(CAS) >= 60 and DV == [], DV[:4])
# Les jetons sont bien decodes en NATIFS des deux cotes (sinon un {"$num": …} serait un objet illisible -> « tout le plan »
# des deux cotes, egalite creuse) : le cas t0 = 3, t1 = NaN, t_local 2 est FAUX des deux cotes, et vrai s'il n'etait pas decode.
_i_nan = next((i for i, c in enumerate(CAS) if c.get("t0") == 3 and c.get("t1") == {"$num": "nan"}
               and c.get("t_local") == 2), None)
check("x1_temoin_jeton_nan_decode_en_natif_des_deux_cotes",
      _i_nan is not None and len(PYA) > _i_nan and len(JSA) > _i_nan and PYA[_i_nan] is False and JSA[_i_nan] is False
      and py_actif(dict(CAS[_i_nan], t1={"$autre": 1})) is True, _i_nan)
PYD = [py_actif(c) for c in DIV] if gr is not None else []
JSD = D.get("div") if isinstance(D.get("div"), list) else []
check("x1_divergences_declarees_divergent_exactement_comme_la_table_le_dit",
      len(DIV) >= 1 and len(PYD) == len(JSD) == len(DIV)
      and all(PYD[i] is DIV[i]["python"] and JSD[i] is DIV[i]["couche"] and PYD[i] is not JSD[i] for i in range(len(DIV))),
      (PYD, JSD, [(c["python"], c["couche"]) for c in DIV]))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[2] corps : dzmGlBody / dzmScwBody acceptes par grade-frame et scopes (TestClient, 200), cadre normalise transmis")
GL = D.get("gl") if isinstance(D.get("gl"), dict) else {}
SW = D.get("scw") if isinstance(D.get("scw"), dict) else {}
CK = set(re.findall(r'\braw\.get\("([a-z_]+)"\)', MSV[MSV.find("def _cadre_of("):MSV.find("def _cadre_pre(")]))
check("x2_corps_du_client_fabriques_avec_cadre_et_cles_du_cadre_lues_par_cadre_of",
      set(GL) == {"src", "t", "effects", "mask", "cadre", "w"} and set(SW) == {"src", "t", "effects", "mask", "size", "cadre"}
      and CK == {"ratio", "t_local", "dur", "reframe", "dz"}
      and set(GL.get("cadre") or {}) == {"ratio", "t_local", "dur", "reframe", "dz"}
      and set(GL.get("cadre") or {}) <= CK and set(SW.get("cadre") or {}) <= CK,
      (sorted(GL), sorted(SW), sorted(CK), GL.get("cadre")))
check("x2_temoin_plan_sans_effet_et_effet_hors_de_ses_bornes_aucun_corps",
      "gl_nu" in D and D.get("gl_nu") is None and "gl_hors" in D and D.get("gl_hors") is None and bool(GL),
      (D.get("gl_nu"), D.get("gl_hors")))

_vus = []
_FAUX = pathlib.Path(TMP) / "src.mp4"
_FAUX.write_bytes(b"x")
_IMG = pathlib.Path(TMP) / "img.jpg"
_IMG.write_bytes(b"\xff\xd8\xff\xd9")


async def _src(request, src, *, video=False):
    _vus.append(("src", src, video))
    return _FAUX


def _gf(p, t, effects=None, mask=None, w=240, fmt="png", cadre=None):
    _vus.append(("gf", t, effects, mask, w, fmt, cadre))
    return _IMG


def _sp(p, t, effects=None, mask=None, size=512, cadre=None):
    _vus.append(("sp", t, effects, mask, size, cadre))
    return _IMG


_res = {}
_cli = None
if ms is not None and gr is not None and GL and SW:
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        _cli = TestClient(app, raise_server_exceptions=False)     # SANS `with` : aucun lifespan
    except Exception as e:                   # noqa: BLE001
        print(f"  (TestClient impossible : {e!r})")
    if _cli is not None:
        _o = (ms._media_source, gr.graded_frame, gr.scopes_png)
        ms._media_source, gr.graded_frame, gr.scopes_png = _src, _gf, _sp
        try:
            for k, url, corps in (("gl", "/api/montage/grade-frame", GL), ("sc", "/api/montage/scopes", SW)):
                _vus.clear()
                try:
                    r = _cli.post(url, json=corps)
                    _res[k] = (r.status_code, list(_vus))
                except Exception as e:       # noqa: BLE001
                    _res[k] = ("LEVE %r" % e, list(_vus))
        finally:
            ms._media_source, gr.graded_frame, gr.scopes_png = _o


def _cad(raw):
    try:
        return ms._cadre_of(raw)
    except Exception as e:                   # noqa: BLE001
        return "LEVE %r" % e


_glv = _res.get("gl", (None, []))
_cad_gl = _cad(GL.get("cadre")) if ms is not None else None
check("x2_grade_frame_200_avec_le_corps_du_client_cadre_normalise_largeur_effets_masque_tels_quels",
      _glv[0] == 200 and isinstance(_cad_gl, dict) and _cad_gl.get("ratio") == "16:9"
      and _cad_gl.get("reframe") == {"mode": "manuel", "x": 0.3} and isinstance(_cad_gl.get("dz"), dict)
      and ("src", GL.get("src"), True) in _glv[1]
      and ("gf", GL.get("t"), GL.get("effects"), GL.get("mask"), GL.get("w"), "jpg", _cad_gl) in _glv[1],
      (_glv, _cad_gl))
_scv = _res.get("sc", (None, []))
_cad_sc = _cad(SW.get("cadre")) if ms is not None else None
check("x2_scopes_200_avec_le_corps_du_client_taille_et_cadre_normalise",
      _scv[0] == 200 and isinstance(_cad_sc, dict) and _cad_sc.get("ratio") == "1:1"
      and ("sp", SW.get("t"), SW.get("effects"), SW.get("mask"), SW.get("size"), _cad_sc) in _scv[1],
      (_scv, _cad_sc))
# le t_local et la duree que le client envoie sont ceux que le serveur garde (arrondis au millieme des deux cotes)
check("x2_t_local_et_dur_du_client_gardes_tels_quels_par_cadre_of",
      isinstance(_cad_gl, dict) and _cad_gl.get("t_local") == (GL.get("cadre") or {}).get("t_local") == 1.5
      and _cad_gl.get("dur") == (GL.get("cadre") or {}).get("dur") == 4, (_cad_gl, GL.get("cadre")))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[3] bornes : dzmGlW / dzmScwSize (client) == _cadre_w / _scopes_size (serveur)")
GW = D.get("glw") if isinstance(D.get("glw"), list) else []
SS = D.get("scws") if isinstance(D.get("scws"), list) else []
_srv = (ms._CADRE_W_MIN, ms._CADRE_W_MAX, ms._CADRE_W_DEFAUT, ms._SCOPES_SIZE_MIN, ms._SCOPES_SIZE_MAX,
        ms._SCOPES_SIZE_DEFAUT) if ms is not None else ()
check("x3_largeur_du_cadre_min_max_defaut_du_client_egaux_au_serveur",
      len(GW) == 9 and len(_srv) == 6 and GW[0] == _srv[0] == 96 and GW[1] == _srv[1] == 1280 and GW[2] == _srv[2] == 720
      and GW[3] == GW[4] == 720 and GW[5] == 334 and GW[6] == 960 and GW[7] == 96 and GW[8] == 1280,
      (GW, _srv))
check("x3_taille_des_scopes_min_max_du_client_egaux_au_serveur_defaut_du_client_dit",
      len(SS) == 8 and len(_srv) == 6 and SS[0] == _srv[3] == 256 and SS[1] == _srv[4] == 1024
      and SS[2] == SS[3] == 320 == D.get("scw_def") and SS[4] == 334 and SS[5] == 450 and SS[6] == 256 and SS[7] == 1024
      and _srv[5] == 512, (SS, _srv, D.get("scw_def")))
_gwt = D.get("glw_tous") if isinstance(D.get("glw_tous"), list) else []
_sst = D.get("scws_tous") if isinstance(D.get("scws_tous"), list) else []
_pf_gw = [v for v in _gwt if ms is None or ms._cadre_w(v) != v]
_pf_ss = [v for v in _sst if ms is None or ms._scopes_size(v) != v]
check("x3_toute_largeur_et_toute_taille_du_client_est_un_point_fixe_du_serveur",
      len(_gwt) >= 400 and len(_sst) >= 400 and _pf_gw == [] and _pf_ss == []
      and len(set(_gwt)) > 50 and len(set(_sst)) > 50, (len(_gwt), len(_sst), _pf_gw[:5], _pf_ss[:5]))
# temoin : une largeur IMPAIRE (que le client ne produit jamais) n'est PAS un point fixe du serveur
check("x3_temoin_largeur_impaire_ramenee_par_le_serveur",
      ms is not None and ms._cadre_w(333) == 332 and ms._scopes_size(777) == 776 and 333 not in _gwt and 777 not in _sst,
      (ms._cadre_w(333) if ms else None,))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[4] ratios : DZM_GL_RATIOS ⊂ _CANVAS, repli 9:16 des deux cotes")
RT = D.get("ratios") if isinstance(D.get("ratios"), list) else []
RP = D.get("repli") if isinstance(D.get("repli"), list) else []
_can = set(getattr(ms, "_CANVAS", {}) or {}) if ms is not None else set()
check("x4_les_ratios_du_client_sont_ceux_du_canvas_du_rendu",
      len(RT) == 4 and set(RT) <= _can and set(RT) == _can == {"9:16", "16:9", "1:1", "4:5"}, (RT, sorted(_can)))
_rsrv = [(_cad({"ratio": r, "t_local": 0}) or {}).get("ratio") if ms is not None else None
         for r in ("3:4", None, ["9:16"], "16:9")]
check("x4_repli_du_client_egal_au_repli_de_cadre_of",
      RP == ["9:16", "9:16", "9:16", "16:9"] and RP == _rsrv, (RP, _rsrv))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[5] routes : celles que la couche appelle par dzmGpFetch sont declarees POST sous /api/montage")
APPELS = set(re.findall(r'dzmGpFetch\("(/api/montage/[a-z-]+)"', JS))
_rts = {}
if ms is not None:
    for _r in getattr(ms.router, "routes", []):
        _rts.setdefault(getattr(_r, "path", ""), set()).update(getattr(_r, "methods", set()) or set())
_nd = sorted(a for a in APPELS if "POST" not in _rts.get(a[len("/api/montage"):], set()))
check("x5_routes_appelees_par_la_couche_declarees_post_sous_le_prefixe_de_main",
      {"/api/montage/grade-frame", "/api/montage/scopes"} <= APPELS and len(APPELS) >= 4 and _nd == []
      and MAIN.count('app.include_router(montage_router, prefix="/api/montage")') == 1,
      (sorted(APPELS), _nd))
# les deux composants des retours appellent grade-frame (lecteur) et scopes (fenetre flottante) : chacun une fois de plus
_gl_src = JS[JS.find("function DzmGradeLive("):JS.find("function dzmLearnRange(")]
_sc_src = JS[JS.find("function DzmScopes("):JS.find("function DzmScopes(") + 6000]
check("x5_image_etalonnee_appelle_grade_frame_et_fenetre_des_scopes_appelle_scopes",
      len(_gl_src) > 500 and _gl_src.count('dzmGpFetch("/api/montage/grade-frame"') == 1
      and _sc_src.count('dzmGpFetch("/api/montage/scopes"') == 1, (len(_gl_src), len(_sc_src)))

print(f"\n=== {ok} passed, {fail} failed ===")
try:
    from loguru import logger as _lg
    _lg.remove()
except Exception:                            # noqa: BLE001
    pass
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
