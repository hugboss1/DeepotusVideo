# -*- coding: utf-8 -*-
"""L6 — BANC CROISE couche / bundle / service : ce que le lot L6 (audio)
ecrit EN DUR d'un cote du reseau doit etre CE QUE l'autre cote lit, ou etre
DATE comme un ecart. Fichier SEPARE de test_montage_l6.py (un processus, un
code de sortie). Modele : test_montage_l5_croise.py (regex GARDEES par un
temoin de longueur ou de compte, le litteral ET le comportement, etat vide
construit, sous-processus node qui rend {} quand il meurt). AUCUN reseau,
AUCUN serveur, AUCUN ffmpeg : la route noise-profile est appelee en direct
avec une vraie Request starlette (client 127.0.0.1), ses couches basses
(`_media_source`, `_has_audio_stream`, `_probe_duration`, `_ff_run`)
espionnees. Jamais /api/audio/voiceover ni /api/audio/sfx (payants).
Run : & $PY tests/test_montage_l6_croise.py   (depuis backend/)

CE QUI EST COMPARE.
  [1] D-23/D-25 : `SVX_FX_DEFS` du bundle LIVRE (extrait entre ses bornes
      1/1, regex gardee par un temoin de longueur ET de compte) ==
      `sfx_service._FX_PARAMS` (import) : memes types, memes params, memes
      (min, max, defaut) pour TOUS les types, rangees cachees comprises
      (`learn_in` / `learn_out`) ; `filter.mode` a part (seg == cles de
      `_FILTER_MODES`, defaut "low").
  [2] Ordre : l'ordre du catalogue client ET celui de son commentaire
      (« Ordre de chaîne fixe : … ») == `_FX_ORDER`.
  [3] D-25 : `dzmLearnRange` (la couche, sous node) accepte / refuse comme
      `learn_of` (borne basse 0,2 avec sa tolerance) ET comme la route
      `noise-profile` (0,2..30) sur une table de cas (0,2 ; 0,19999 ;
      1,0-1,2 ; 2,0-2,2 ; 30 ; 30,01) ; et ce que la couche ECRIT
      (`dzmDenoiseLearn`) est relu par `sanitize_fx` + `learn_of` comme une
      plage apprise ; les deux gardes de L'AFFICHAGE (`dzmNlAppris`, couche,
      et le resume « · appris » du rack, bundle) jugent comme `learn_of` sur
      0,2 / 1,0-1,2 / 1,0-1,199 (revue finale : 1,2 - 1,0 = 0,1999... en JS).
  [4] D-25 : `dzmNfEffectif` (node) == le plancher EMIS par `_fx_denoise`
      (Python, par `sanitize_fx` + `fx_chain`) sur -95, -80, -20,5, -19, -5,
      -0,6, -0,3, 0.
  [5] Routes : celles qu'appellent la couche (`/api/montage/noise-profile`,
      `/api/audio/recording`) et le bundle (`/api/audio/audition`, dans
      `sfxAudition`) sont DECLAREES en POST par le backend (`ms.router`,
      `routes.router`, prefixes de main.py).
  [6] D-26 : `vo_record` present une fois, combo `Alt+R` portee par elle
      seule, absente de `SVM_COMBO_RESERVED` et non refusee par
      `svmComboReserved` (jouee sous node), dispatchee ; `voiceover` ABSENT
      du CODE L6 (couche L6 et sections L6 du patcher, commentaires retires)
      -- temoin : present ailleurs dans le bundle.

Mesure du 25/09/2026 (sommet a669092 + ce banc) : voir le compte en fin de
sortie ; aucune divergence entre le service, la couche et le bundle.

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
Faute n°6 : aucune lecture nue ; un dict vide de node ou une regex qui ne
trouve rien fait ROUGIR, pas mourir.
"""
import asyncio
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl6x_")
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


def sans_commentaires(t):
    """Le code sans ses commentaires /* … */ (les seuls que portent la couche L6 et les sections L6)."""
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


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


def REQ(path, body, host="127.0.0.1"):
    from starlette.requests import Request as _R
    raw = json.dumps(body).encode("utf-8")

    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": path, "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": (host, 5000)}, rcv)


async def appel(f, *a):
    """(code, corps) d'une route appelee en direct ; une HTTPException rend son code et son detail."""
    try:
        v = await f(*a)
        return (getattr(v, "status_code", 200), v)
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
MSV = lire("backend/app/services/montage_service.py")
RTS = lire("backend/app/api/routes.py")
MAIN = lire("backend/app/main.py")
check("x0_couche_bundle_service_routes_et_main_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(MSV) > 100_000 and len(RTS) > 100_000 and len(MAIN) > 1_000,
      (len(JS), len(BUN), len(MSV), len(RTS), len(MAIN)))
check("x0_node_est_sur_le_PATH", bool(NODE), NODE)

try:
    from app.services import sfx_service as sx
    from app.services import montage_service as ms
except Exception as e:                       # le banc rougit, ne meurt pas
    sx = ms = None
    print(f"  (import des services impossible : {e!r})")
try:
    from app.api import routes as rt
except Exception as e:
    rt = None
    print(f"  (import des routes impossible : {e!r})")
try:
    _spec = importlib.util.spec_from_file_location("patch_bundle_montage_l6x",
                                                   os.path.join(ROOT, "scripts", "patch_bundle_montage.py"))
    P = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(P)
except BaseException as e:                   # SystemExit d'une garde compris
    P = None
    print(f"  (import du patcher impossible : {e!r})")
check("x0_services_routes_et_patcher_importes_avec_les_symboles_L6",
      None not in (sx, ms, rt, P)
      and all(hasattr(sx, k) for k in ("_FX_PARAMS", "_FX_ORDER", "_FILTER_MODES", "sanitize_fx", "fx_chain",
                                       "learn_of", "LEARN_MIN"))
      and all(hasattr(ms, k) for k in ("montage_noise_profile", "_media_source", "_has_audio_stream",
                                       "_probe_duration", "_ff_run", "router"))
      and hasattr(rt, "router") and isinstance(getattr(P, "L6", None), list) and len(P.L6) == 8,
      (sx, ms, rt, P))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[1] D-23/D-25 : SVX_FX_DEFS (bundle livre) == _FX_PARAMS (sfx_service) pour TOUS les types")
SVD = entre(BUN, "var SVX_FX_DEFS=[", "var SVX_FX_BY={};")
RX_T = re.compile(r'\{type:"(\w+)",label:"([^"]+)",live:([01]),params:\[')
RX_P = re.compile(r'\{k:"(\w+)",label:"[^"]*",min:(-?[\d.]+),max:(-?[\d.]+),d:(-?[\d.]+),step:(-?[\d.]+)')
RX_K = re.compile(r'\{k:"(\w+)"')


def _svx_params(t):
    """{type: {param: (min, max, defaut)}} des params NUMERIQUES, et {type: [toutes les cles k]} (temoin de la regex)."""
    num, cles = {}, {}
    for m in RX_T.finditer(t):
        fin = t.find("]}", m.end())
        corps = t[m.end():fin] if fin > m.end() else ""
        num[m.group(1)] = {k: (float(a), float(b), float(d)) for k, a, b, d, _s in RX_P.findall(corps)}
        cles[m.group(1)] = RX_K.findall(corps)
    return num, cles


SVP, SVK = _svx_params(SVD)
FXP = getattr(sx, "_FX_PARAMS", {}) if sx is not None else {}
ORDER = list(getattr(sx, "_FX_ORDER", ())) if sx is not None else []
# TEMOIN DE LA REGEX : chaque cle `k` du catalogue est lue comme numerique, sauf `filter.mode` (seg) -- une rangee
# que la regex numerique manquerait (format change) ferait diverger les deux comptes, et le banc rougit.
_n_k = sum(len(v) for v in SVK.values())
_n_num = sum(len(v) for v in SVP.values())
check("x1_catalogue_lu_entre_ses_bornes_regex_gardee_toute_cle_lue_numerique_sauf_filter_mode",
      len(SVD) > 3000 and BUN.count("var SVX_FX_DEFS=[") == 1 and BUN.count("var SVX_FX_BY={};") == 1
      and len(SVP) == 12 and _n_k == _n_num + 1 and SVK.get("filter", [None])[0] == "mode"
      and "mode" not in SVP.get("filter", {"mode": 1}),
      (len(SVD), len(SVP), _n_k, _n_num))
check("x1_memes_types_des_deux_cotes_douze",
      len(FXP) == 12 and set(SVP) == set(FXP), (sorted(SVP), sorted(FXP)))
_fxp_num = {t: {k: tuple(float(x) for x in v) for k, v in d.items()} for t, d in FXP.items()}
DIFF = {t: (SVP.get(t), _fxp_num.get(t)) for t in set(SVP) | set(_fxp_num) if SVP.get(t) != _fxp_num.get(t)}
check("x1_bornes_et_defauts_de_tous_les_params_egaux_types_caches_compris_aucune_divergence",
      _n_num == sum(len(v) for v in FXP.values()) == 43 and DIFF == {}, DIFF)
check("x1_les_rangees_cachees_learn_in_learn_out_sont_comparees_comme_les_autres",
      SVP.get("denoise", {}).get("learn_in") == _fxp_num.get("denoise", {}).get("learn_in") == (0.0, 86400.0, 0.0)
      and SVP.get("denoise", {}).get("learn_out") == (0.0, 86400.0, 0.0)
      and entre(SVD, '{k:"learn_in"', "}").count("hide:1") == 1 and entre(SVD, '{k:"learn_out"', "}").count("hide:1") == 1,
      (SVP.get("denoise"), entre(SVD, '{k:"learn_in"', "}")))
_seg = re.search(r'\{k:"mode",kind:"seg",opts:\[((?:\["\w+","[^"]*"\],?)+)\],d:"(\w+)"\}', SVD)
_opts = re.findall(r'\["(\w+)","', _seg.group(1)) if _seg else []
check("x1_filter_mode_seg_egal_aux_cles_de_FILTER_MODES_defaut_low",
      bool(_seg) and sorted(_opts) == sorted(getattr(sx, "_FILTER_MODES", {})) and len(_opts) == 3 and _seg.group(2) == "low",
      (_opts, _seg.group(2) if _seg else None))
# ETAT VIDE : le comparateur VOIT une divergence fabriquee (borne haute de eq6.ls_g poussee a 24)
_faux = json.loads(json.dumps({t: {k: list(v) for k, v in d.items()} for t, d in SVP.items()}))
if isinstance(_faux.get("eq6", {}).get("ls_g"), list):
    _faux["eq6"]["ls_g"][1] = 24.0
check("x1_etat_vide_le_comparateur_voit_une_borne_fabriquee_temoin_egal_avant",
      DIFF == {} and _faux.get("eq6", {}).get("ls_g") == [-12.0, 24.0, 0.0]
      and tuple(_faux["eq6"]["ls_g"]) != _fxp_num.get("eq6", {}).get("ls_g"), _faux.get("eq6", {}).get("ls_g"))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[2] Ordre : catalogue client ET son commentaire == _FX_ORDER")
ORD_CAT = [m.group(1) for m in RX_T.finditer(SVD)]
_com = entre(BUN, "   Ordre de chaîne fixe : ", "live:1 = audible")
ORD_COM = re.findall(r"\b([a-z0-9]+)\b", _com.replace("Ordre de chaîne fixe :", "").split("(L6")[0])
check("x2_ordre_du_catalogue_client_egal_a_FX_ORDER_douze_types",
      len(ORDER) == 12 and ORD_CAT == ORDER, (ORD_CAT, ORDER))
check("x2_ordre_du_commentaire_du_catalogue_egal_a_FX_ORDER",
      BUN.count("   Ordre de chaîne fixe : ") == 1 and len(ORD_COM) == 12 and ORD_COM == ORDER, (ORD_COM, ORDER))
check("x2_temoin_dehum_avant_eq3_et_eq6_apres_denoise",
      len(ORDER) == 12 and ORDER.index("dehum") < ORDER.index("eq3") < ORDER.index("denoise") < ORDER.index("eq6"), ORDER)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[3] D-25 : dzmLearnRange (couche) == learn_of (service) et route noise-profile, sur une table de cas")
# (t0, t1, verdict attendu) en temps de TIMELINE (clip start 0, srcIn 0, vitesse 1 : plage de source = plage I/O).
# MESURE 25/09/2026 : la couche ARRONDIT la plage au millieme AVANT la garde (dzmCoR(…, 3)) et c'est la plage
# arrondie qu'elle ENVOIE a la route et ECRIT dans le debruiteur -- 0,19999 s devient 0–0,2 et passe ; le service,
# lui, juge les nombres BRUTS (temoin : 0,19999 brut y est refuse). Le service est donc compare sur la plage que la
# couche lui transmet (arrondie au millieme) ; 0,1994 (-> 0,199) est refuse partout. learn_of n'a pas de borne
# haute (il plafonne L a 1 s) : il est compare sur la borne BASSE seule (b - a <= 30).
CAS = [(0.0, 0.2, True), (0.0, 0.19999, True), (0.0, 0.1994, False), (1.0, 1.2, True), (2.0, 2.2, True),
       (5.1, 5.3, True), (0.0, 30.0, True), (0.0, 30.01, False), (4.0, 4.1, False)]


def R3(v):
    return round(v + 0.0, 3)
_PROBE = r"""
var out={};var CAS=__CAS__;
out.lr=CAS.map(function(c){return dzmLearnRange({start:0,srcIn:0,speed:1,end:60},{"in":c[0],out:c[1]},0)});
out.ecrit=CAS.map(function(c){var r=dzmLearnRange({start:0,srcIn:0,speed:1,end:60},{"in":c[0],out:c[1]},0);
  return r.refus?null:dzmDenoiseLearn([],r.a,r.b,-30)});
out.nfe=[-95,-80,-20.5,-19,-5,-0.6,-0.3,0].map(function(n){return dzmNfEffectif(n)});
out.aff=__AFF__.map(function(c){return dzmNlAppris([{type:"denoise",params:{amount:12,learn_in:c[0],learn_out:c[1]}}])!==null});
console.log(JSON.stringify(out));
"""
_shim = ('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n"
         + _PROBE.replace("__CAS__", json.dumps([[a, b] for a, b, _ in CAS])))
# LES GARDES DE L'AFFICHAGE (revue finale L6, 25/09) : dzmNlAppris (statut, « Oublier ») et le resume « · appris » du
# rack (bundle) jugent la plage comme learn_of (LEARN_MIN - 1e-9) -- 1,2 - 1,0 = 0,19999999999999996 en JS : sans la
# tolerance, 1,0-1,2 (que la couche ecrit et que le rendu apprend) s'affichait « aucun bruit appris ».
AFF = [(0.0, 0.2, True), (1.0, 1.2, True), (1.0, 1.199, False), (7.0, 8.0, True)]
_shim = _shim.replace("__AFF__", json.dumps([[a, b] for a, b, _ in AFF]))
D, _dwhy = node_json("l6x_couche.js", _shim)
check("x0_la_couche_s_execute_sous_node_et_rend_les_cles_de_la_sonde",
      bool(D) and all(k in D for k in ("lr", "ecrit", "nfe", "aff")), _dwhy or sorted(D))
LR = D.get("lr") if isinstance(D.get("lr"), list) else []
JS_OK = [isinstance(v, dict) and "a" in v and "refus" not in v for v in LR]


def _lo(a, b):
    try:
        return sx.learn_of([{"type": "denoise", "params": {"amount": 12, "learn_in": a, "learn_out": b}}]) is not None
    except Exception as e:
        return "LEVE %s" % type(e).__name__


PY_OK = [_lo(R3(a), R3(b)) for a, b, _ in CAS] if sx is not None else []
check("x3_la_table_couvre_acceptes_et_refuses_des_deux_bornes_verdicts_attendus",
      len(LR) == len(CAS) and JS_OK == [c[2] for c in CAS]
      and sum(1 for v in LR if isinstance(v, dict) and v.get("refus") == "courte") == 2
      and sum(1 for v in LR if isinstance(v, dict) and v.get("refus") == "longue") == 1,
      LR)
check("x3_temoin_le_service_juge_le_brut_0_19999_refuse_brut_accepte_arrondi_par_la_couche",
      sx is not None and _lo(0.0, 0.19999) is False and _lo(0.0, 0.2) is True and JS_OK[1] is True
      and LR[1] == {"a": 0, "b": 0.2}, (LR[1] if len(LR) > 1 else None))
DL = [(CAS[i][:2], JS_OK[i], PY_OK[i]) for i in range(min(len(LR), len(PY_OK)))
      if CAS[i][1] - CAS[i][0] <= 30 and JS_OK[i] != PY_OK[i]]
check("x3_dzmLearnRange_accepte_refuse_comme_learn_of_sur_la_borne_basse_1_0_1_2_compris",
      len(PY_OK) == len(CAS) == len(JS_OK) and DL == [] and JS_OK[3] is True and PY_OK[3] is True, DL)
check("x3_dzmLearnRange_rend_la_plage_de_source_attendue_au_millieme",
      len(LR) == len(CAS) and all(LR[i] == {"a": R3(CAS[i][0]), "b": R3(CAS[i][1])} for i in range(len(CAS)) if JS_OK[i]),
      [LR[i] for i in range(len(LR)) if JS_OK[i]])

# LA ROUTE, appelee en direct : couches basses espionnees, RMS fabrique (-40 dB) -- la route ne juge que la plage
_vus = []
_FAUX = pathlib.Path(TMP) / "src.wav"
_FAUX.write_bytes(b"x")


async def _src(request, src, *, video=False):
    _vus.append(("src", src, video))
    return _FAUX


class _R0:
    returncode = 0
    stdout = ""
    stderr = "[Parsed_astats_0 @ 0] Overall\n[Parsed_astats_0 @ 0] RMS level dB: -40.000000\n"


def _ff(cmd, **kw):
    _vus.append(("ff", list(cmd)))
    return _R0()


RT_OK, RT_RAW = [], []
if ms is not None:
    _o = (ms._media_source, ms._has_audio_stream, ms._probe_duration, ms._ff_run)
    ms._media_source, ms._has_audio_stream, ms._probe_duration, ms._ff_run = (
        _src, lambda p: True, lambda p: 100.0, _ff)
    try:
        for a, b, _ in CAS:
            _vus.clear()
            c, v = asyncio.run(appel(ms.montage_noise_profile,
                                     REQ("/api/montage/noise-profile", {"src": {"audio": "b.wav"}, "t0": R3(a), "t1": R3(b), "fx": []})))
            RT_RAW.append((c, v if c != 200 else {k: v.get(k) for k in ("ok", "nf_db", "t0", "t1")}, len(_vus)))
            RT_OK.append(c == 200 and isinstance(v, dict) and v.get("ok") is True)
    finally:
        ms._media_source, ms._has_audio_stream, ms._probe_duration, ms._ff_run = _o
check("x3_la_route_rend_200_ok_nf_de_la_regle_ou_400_temoin_ffmpeg_appele_seulement_si_200",
      len(RT_RAW) == len(CAS) and all(r[0] in (200, 400) for r in RT_RAW)
      and all((r[0] == 200) == (r[2] == 2) for r in RT_RAW)
      and all(r[1].get("nf_db") == -30 for r in RT_RAW if r[0] == 200) and sum(RT_OK) >= 1,
      RT_RAW)
DR = [(CAS[i][:2], JS_OK[i], RT_OK[i]) for i in range(min(len(JS_OK), len(RT_OK))) if JS_OK[i] != RT_OK[i]]
check("x3_dzmLearnRange_accepte_refuse_comme_la_route_noise_profile_bornes_0_2_et_30",
      len(RT_OK) == len(CAS) == len(JS_OK) and DR == [] and RT_OK[6] is True and RT_OK[7] is False, DR)
# CE QUE LA COUCHE ECRIT est relu par le service comme une plage apprise (sanitize_fx garde learn_*, learn_of l'accepte)
EC = D.get("ecrit") if isinstance(D.get("ecrit"), list) else []
_rel = []
for i, fx in enumerate(EC):
    if fx is None:
        continue
    try:
        n = sx.sanitize_fx(fx, "l6x")
        _rel.append((CAS[i][:2], sx.learn_of(n), (n[0]["params"].get("nf") if n else None)))
    except Exception as e:
        _rel.append((CAS[i][:2], "LEVE %s" % type(e).__name__, None))
check("x3_la_plage_ecrite_par_dzmDenoiseLearn_est_relue_par_sanitize_fx_et_learn_of_plancher_garde",
      len(_rel) == 6 and all(isinstance(r[1], tuple) and r[1][0] == R3(r[0][0])
                             and abs(r[1][1] - (R3(r[0][0]) + min(R3(r[0][1]) - R3(r[0][0]), 1.0))) < 1e-6 and r[2] == -30.0
                             for r in _rel), _rel)
# LES DEUX GARDES DE L'AFFICHAGE == learn_of sur la table AFF : dzmNlAppris (couche, node) et le resume du rack
# (svxModSummary EXTRAIT du bundle livre, node) ; temoin : le verdict de learn_of sur la table est celui attendu.
JAFF = D.get("aff") if isinstance(D.get("aff"), list) else []
PAFF = [_lo(a, b) for a, b, _ in AFF] if sx is not None else []
_fsum = entre(BUN, "function svxModSummary(def,p){", "\nfunction ")
DS, _dswhy = node_json("l6x_resume.js", '"use strict";\nfunction svxDb1(v){return String(v)}\n' + _fsum
                       + "\nconsole.log(JSON.stringify({ap:" + json.dumps([[a, b] for a, b, _ in AFF])
                       + ".map(function(q){return / · appris$/.test(svxModSummary({type:\"denoise\"},"
                       + "{amount:12,nf:0,learn_in:q[0],learn_out:q[1]}))})}));\n")
BAFF = DS.get("ap") if isinstance(DS.get("ap"), list) else []
check("x3_temoin_learn_of_sur_la_table_de_l_affichage_1_0_1_2_accepte_1_199_refuse",
      PAFF == [c[2] for c in AFF] and PAFF[1] is True and PAFF[2] is False, PAFF)
check("x3_dzmNlAppris_juge_la_plage_comme_learn_of_1_0_1_2_appris",
      len(JAFF) == len(AFF) == len(PAFF) and JAFF == PAFF and JAFF[1] is True, list(zip(AFF, JAFF, PAFF)))
check("x3_resume_du_rack_bundle_dit_appris_comme_learn_of_1_0_1_2_compris",
      len(_fsum) > 300 and len(BAFF) == len(AFF) == len(PAFF) and BAFF == PAFF and BAFF[1] is True,
      (list(zip(AFF, BAFF, PAFF)), _dswhy))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[4] D-25 : dzmNfEffectif (couche) == le plancher emis par _fx_denoise (service)")
NFS = [-95, -80, -20.5, -19, -5, -0.6, -0.3, 0]
_RX_NF = re.compile(r"afftdn=nr=12(?::nf=(-?[\d.]+))?,")


def _py_nf(n):
    try:
        ch = sx.fx_chain(sx.sanitize_fx([{"type": "denoise", "params": {"amount": 12, "nf": n}}]))
    except Exception as e:
        return "LEVE %s" % type(e).__name__
    m = _RX_NF.search(ch)
    if not m:
        return "SANS afftdn : " + ch[:80]
    return float(m.group(1)) if m.group(1) is not None else None


PNF = [_py_nf(n) for n in NFS] if sx is not None else []
JNF = D.get("nfe") if isinstance(D.get("nfe"), list) else []
JNF = [float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for v in JNF]
check("x4_la_regle_python_mesuree_automatique_borne_moins_20_et_moins_80",
      PNF == [-80.0, -80.0, -20.5, -20.0, -20.0, -20.0, None, None], PNF)
check("x4_dzmNfEffectif_egal_au_plancher_emis_par_fx_denoise_sur_les_huit_valeurs",
      len(JNF) == len(NFS) == len(PNF) and JNF == PNF, list(zip(NFS, JNF, PNF)))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[5] Routes : appelees par la couche et le bundle == declarees par le backend (POST)")
JS_L6 = entre(JS, "/* L6 D-25 D-26 (25/09/2026, tâche 4)", "/* LES SCOPES (section L5sc1")
SFXA = entre(BUN, "  function sfxAudition(fx){", "  function duckCfg(){")
AP_JS = set(re.findall(r'(?:dzmGpFetch|fetch)\("(/api/[a-z/-]+)"', JS_L6))
AP_BUN = set(re.findall(r'fetch\("(/api/[a-z/-]+)"', SFXA))
check("x5_la_couche_L6_appelle_noise_profile_et_audio_recording_le_bundle_audio_audition",
      len(JS_L6) > 10_000 and len(SFXA) > 800
      and AP_JS == {"/api/montage/noise-profile", "/api/audio/recording"} and AP_BUN == {"/api/audio/audition"},
      (len(JS_L6), len(SFXA), sorted(AP_JS), sorted(AP_BUN)))


def _decl(router, prefix):
    out = {}
    for r_ in getattr(router, "routes", []) if router is not None else []:
        pth = getattr(r_, "path", "")
        if pth:
            out.setdefault(prefix + pth, set()).update(getattr(r_, "methods", set()) or set())
    return out


DECL = {}
DECL.update(_decl(getattr(ms, "router", None), "/api/montage"))
for k, v in _decl(getattr(rt, "router", None), "/api").items():
    DECL.setdefault(k, set()).update(v)
_ap = sorted(AP_JS | AP_BUN)
check("x5_les_trois_routes_sont_declarees_en_POST_sous_les_prefixes_de_main",
      len(_ap) == 3 and all("POST" in DECL.get(u, set()) for u in _ap)
      and MAIN.count('app.include_router(montage_router, prefix="/api/montage")') == 1
      and MAIN.count('app.include_router(router, prefix="/api")') == 1,
      {u: sorted(DECL.get(u, set())) for u in _ap})
check("x5_temoin_une_route_inconnue_n_est_pas_declaree_et_la_table_des_routes_est_pleine",
      len(DECL) > 100 and "/api/montage/noise-profile" in DECL and "/api/audio/enregistrer" not in DECL, len(DECL))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[6] D-26 : vo_record (Alt+R) non reservee ; voiceover absent du code L6")
ACT = entre(BUN, "var SVM_ACTIONS=[", "var SVM_KEY_SECTIONS=")
_combos = re.findall(r'\{id:"([a-z_0-9]+)",[^\n]*?combo:"([^"]*)"\}', ACT)
_cmap = {}
for _id, _cb in _combos:
    _cmap.setdefault(_cb, []).append(_id)
_vo = [cb for i_, cb in _combos if i_ == "vo_record"]
check("x6_vo_record_une_fois_au_bundle_avec_Alt_R_portee_par_elle_seule",
      len(_combos) > 40 and _vo == ["Alt+R"] and BUN.count('id:"vo_record"') == 1 and _cmap.get("Alt+R") == ["vo_record"],
      (len(_combos), _vo, _cmap.get("Alt+R")))
_mres = re.search(r"var SVM_COMBO_RESERVED=(\{[^}]*\});", BUN)
try:
    RES = json.loads(_mres.group(1)) if _mres else {}
except ValueError:
    RES = {}
_fres = entre(BUN, "function svmComboReserved(c){", "\n/* overrides")
DR6, _dr6why = node_json("l6x_reserve.js", '"use strict";\nvar SVM_COMBO_RESERVED=' + (json.dumps(RES) if RES else "{}")
                         + ";\n" + _fres + "\nconsole.log(JSON.stringify({vo:[" + ",".join(json.dumps(c) for c in _vo)
                         + "].map(svmComboReserved),temoin:svmComboReserved(\"Ctrl+R\"),f5:svmComboReserved(\"F5\")}));\n")
check("x6_la_combo_effective_de_vo_record_n_est_pas_reservee_temoin_Ctrl_R_et_F5_refusees",
      len(RES) >= 10 and "Ctrl+R" in RES and len(_vo) == 1 and all(cb not in RES for cb in _vo)
      and len(_fres) > 200 and DR6.get("vo") == [""] and bool(DR6.get("temoin")) and bool(DR6.get("f5")),
      (_vo, DR6, _dr6why))
check("x6_vo_record_est_dispatchee_vers_la_bascule_de_la_puce",
      BUN.count('if(id==="vo_record"){if(typeof dzVoRef.current==="function")dzVoRef.current();') == 1
      and BUN.count("var dzVoRef=x.useRef(null);") == 1 and BUN.count("ctl:dzVoRef,") == 1,
      BUN.count('if(id==="vo_record")'))
_R_L6 = "\n".join(r_ for _n, _a, r_ in (P.L6 if P is not None else []))
_code = sans_commentaires(JS_L6) + "\n" + sans_commentaires(_R_L6)
check("x6_voiceover_absent_du_code_L6_couche_et_sections_temoin_present_ailleurs_au_bundle",
      len(JS_L6) > 10_000 and len(_R_L6) > 5_000 and "/api/audio/recording" in _code
      and "voiceover" not in _code.lower() and BUN.count("voiceover") >= 3,
      ([m.start() for m in re.finditer("voiceover", _code.lower())][:5], BUN.count("voiceover")))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
