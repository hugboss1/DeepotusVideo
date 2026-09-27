# -*- coding: utf-8 -*-
"""Retours du 26/09 et champs IA (plan du 27/09/2026, tache 11) -- BANC CROISE
client / serveur : ce qu'un cote du reseau ecrit EN DUR doit etre CE QUE
l'autre cote lit, ou etre DECLARE comme un ecart (et le banc prouve alors
qu'il diverge exactement comme declare).

Fichier SEPARE (un processus, un code de sortie). Modele :
test_retours_croise.py (regex gardees, sous-processus node qui rend {} quand
il meurt, etat vide construit, temoin positif dans la meme expression que
chaque negation, faute n°6 : aucune lecture nue). AUCUN reseau, AUCUNE
depense, AUCUN ffmpeg : les routes sont jouees par un TestClient SANS
lifespan, les couches payantes espionnees.
Run : & $PY tests/test_retours_ia_croise.py   (depuis backend/)

CE QUI EST COMPARE.
  [1] Champs du `cadre` : ceux qu'envoie `dzmGlBody` (la couche montage.js,
      sous node, sur des plans qui allument TOUS les champs : retime, stab,
      piste J1, recadrage, zoom) == ceux que LIT `_cadre_of` / `_cadre_neufs`
      (un dict ESPION qui note chaque cle lue). Temoin : une cle inconnue
      ajoutee au cadre n'est pas lue.
  [2] Bornes J1 : `dzmGlAdjust` (client) == `_cadre_neufs` (serveur, le
      chemin reel du contrat, `_adjust_bounded` du rendu) sur une table
      generee de 7 950 cas (six clips, 53 formes de bornes, 25 instants) --
      table des re-revues T2 / T3. ECART DATE : les chiffres Unicode non
      ASCII (« ٣ », « ３ ») sont lus par float() et illisibles pour la couche
      -- exclus de l'egalite, et le banc prouve qu'ILS divergent.
  [3] Corps multipart de la dictee : les champs que la couche `dz-champ-ia.js`
      met dans ses deux FormData (estimation, transcription) == les
      parametres de corps des deux routes de `dictation_service` (noms,
      obligatoires) ; puis joues sur le TestClient : le corps du client passe
      (200, transcription espionnee, max_usd transmis), sans `max_usd` -> 422.
  [4] Catalogue image de la pastille : ids (et cle exigee) de
      `CATALOGUE_IMAGE` de la couche == ids de `list_image_models` (deux cles
      posees) == cles de `pricing._IMAGE_MODELS` ; libelles egaux au serveur.
  [5] Tarif et plafond de la vignette video du bundle (`dzVmRates`,
      `dzVmCost`) == `pricing` : taux de Seedance 2.5 (720p) et duree max du
      registre, plafond 10 = `video_max_gen_s` par defaut, et dzVmCost(2.5, d)
      == pricing.estimate(video_request_op(2.5, d, 720p)) pour d = 4..30, au
      demi-centime (arrondi d affichage toFixed).
"""
import asyncio
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import wave

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzria_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ["FAL_KEY"] = "test-fal"
os.environ["OPENAI_API_KEY"] = "test-openai"
os.environ["ELEVENLABS_API_KEY"] = "test-el"
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
                           errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {}, repr(e)
    if r.returncode != 0:
        return {}, "rc=%d %s" % (r.returncode, (r.stderr or "")[-400:])
    lignes = (r.stdout or "").strip().splitlines()
    try:
        d = json.loads(lignes[-1]) if lignes else None
    except ValueError:
        d = None
    return (d if isinstance(d, dict) else {}), ("" if isinstance(d, dict) else "sortie illisible")


JS = lire("frontend/patches/montage.js")
CIA = lire("frontend/shared/dz-champ-ia.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
check("x0_couche_montage_couche_champs_ia_et_bundle_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(CIA) > 20_000 and len(BUN) > 1_000_000, (len(JS), len(CIA), len(BUN)))
check("x0_node_est_sur_le_PATH", bool(NODE), NODE)

try:
    from app.services import montage_service as ms
    from app.services import effects_engine as fx
    from app.services import pricing as pr
    from app.services import fal_service as fs
    from app.services import dictation_service as ds
    from app.services import transcribe_service as ts
except Exception as e:                       # le banc rougit, ne meurt pas
    ms = fx = pr = fs = ds = ts = None
    print(f"  (import des services impossible : {e!r})")
check("x0_services_importes_avec_les_symboles_des_retours",
      None not in (ms, fx, pr, fs, ds, ts)
      and all(hasattr(ms, k) for k in ("_cadre_of", "_cadre_neufs", "_adjust_bounded"))
      and all(hasattr(pr, k) for k in ("_IMAGE_MODELS", "DEFAULTS", "estimate", "video_request_op"))
      and hasattr(fs, "VIDEO_MODELS") and hasattr(ds, "router"), (ms, pr, fs, ds))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[1] champs du cadre : envoyes par dzmGlBody (couche, sous node) == lus par _cadre_of / _cadre_neufs")
_PROBE1 = r"""
var out={};
function JJ(e,s,en){return {tr:"j1",id:"jj",start:s,end:en,effects:[e]}}
/* un plan V1 qui allume TOUT : retime blend x0,5, stabilisation, recadrage manuel, zoom D-13, effet present ;
   une piste J1 active a la tete */
var V={tr:"v1",id:"v",src:{job_id:"J"},srcIn:1,start:2,end:8,speed:.5,retime:"blend",
  stab:{on:true,smooth:15,crop:"keep",zoom:0},effects:[{type:"negate",t0:0,t1:5}],
  mask:{shape:"rect",x:0,y:0,w:.5,h:.5,soft:0,inv:false},
  reframe:{mode:"manuel",x:.3},dz:{x0:0,y0:0,w0:1,x1:.2,y1:.1,w1:.6,ease:"lin"}};
var F={tr:"v1",id:"f",src:{job_id:"F"},start:0,end:6,speed:2,retime:"flow",effects:[]};
var A=JJ({type:"__TY__",t0:.5,t1:3},2,8);
out.bodies=[dzmGlBody(V,3,"16:9",[V,A]),dzmGlBody(F,1,"9:16",[F]),dzmGlBody(Object.assign({},V,{stab:null}),3,"9:16",[V,A])];
console.log(JSON.stringify(out));
"""
# le type J1 doit etre un effet CONNU du moteur (`_adjust_bounded` ecarte les autres, comme le rendu ; ECART DATE :
# la couche ne connait pas _fx.EFFECTS)
TY = ("invert" if fx is not None and "invert" in fx.EFFECTS
      else (sorted(fx.EFFECTS)[0] if fx is not None and fx.EFFECTS else "invert"))
D1, _w1 = node_json("ria_cadre.js", '"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n"
                    + _PROBE1.replace("__TY__", TY))
BODIES = [b for b in (D1.get("bodies") or []) if isinstance(b, dict)]
K_CLI = set()
for _b in BODIES:
    K_CLI |= set(_b.get("cadre") or {})


class Espion(dict):
    """Un dict qui NOTE chaque cle lue (get, [], in)."""
    lues = set()

    def get(self, k, d=None):
        Espion.lues.add(k)
        return dict.get(self, k, d)

    def __getitem__(self, k):
        Espion.lues.add(k)
        return dict.__getitem__(self, k)

    def __contains__(self, k):
        Espion.lues.add(k)
        return dict.__contains__(self, k)


_norm = []
if ms is not None:
    for _b in BODIES:
        try:
            _norm.append(ms._cadre_of(Espion(_b.get("cadre") or {})))
        except Exception as e:               # noqa: BLE001
            _norm.append("LEVE %r" % e)
K_SRV = set(Espion.lues)
check("x1_trois_corps_fabriques_par_la_couche_avec_tous_les_champs_neufs_du_cadre",
      len(BODIES) == 3 and {"speed", "retime", "fps", "stab", "adjust", "t_global", "reframe", "dz"} <= K_CLI,
      (_w1, sorted(K_CLI)))
check("x1_champs_envoyes_par_le_client_egaux_aux_champs_lus_par_le_serveur_aucun_champ_mort_d_un_cote",
      bool(K_CLI) and K_CLI == K_SRV, ("client seul", sorted(K_CLI - K_SRV), "serveur seul", sorted(K_SRV - K_CLI)))
# chaque champ neuf du client SURVIT a la normalisation (sinon le serveur le lit pour le jeter)
_neufs_perdus = [(i, sorted(set(("speed", "retime", "fps", "stab", "adjust", "t_global")) & set(b.get("cadre") or {})
                            - set(n if isinstance(n, dict) else {})))
                 for i, (b, n) in enumerate(zip(BODIES, _norm))]
check("x1_les_champs_neufs_envoyes_survivent_a_la_normalisation_du_serveur",
      len(_norm) == 3 and all(isinstance(n, dict) for n in _norm) and all(not p for _i, p in _neufs_perdus),
      (_neufs_perdus, [str(n)[:120] for n in _norm]))
Espion.lues = set()
if ms is not None and BODIES:
    try:
        ms._cadre_of(Espion(dict(BODIES[0].get("cadre") or {}, zz_inconnu=1)))
    except Exception:                        # noqa: BLE001
        pass
check("x1_temoin_une_cle_inconnue_ajoutee_au_cadre_n_est_pas_lue_l_espion_voit_les_autres",
      "zz_inconnu" not in Espion.lues and "ratio" in Espion.lues and "adjust" in Espion.lues, sorted(Espion.lues))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[2] bornes J1 : dzmGlAdjust (couche) == _cadre_neufs (serveur) sur la table des re-revues T2 / T3")
BORNES = [
    {}, {"t0": None}, {"t1": None}, {"t0": None, "t1": None},
    {"t0": 0, "t1": 0}, {"t0": 1, "t1": 2}, {"t0": 5, "t1": 6}, {"t0": 4, "t1": 9}, {"t0": 1, "t1": 1.02},
    {"t0": 1, "t1": 1.05}, {"t0": 1, "t1": 1.049}, {"t0": -4, "t1": 1}, {"t0": -1, "t1": -0.5}, {"t0": 2},
    {"t1": 0.5}, {"t1": 9}, {"t0": 3.99}, {"t0": 3.99, "t1": 9},
    {"t0": "nan"}, {"t1": "nan"}, {"t0": "NaN", "t1": "nan"}, {"t0": "inf"}, {"t1": "inf"}, {"t1": "-inf"},
    {"t0": "-Infinity", "t1": "2"}, {"t0": "1e400"}, {"t1": "1e400"}, {"t0": "x", "t1": 1}, {"t0": 1, "t1": "x"},
    {"t0": "", "t1": 1}, {"t0": 1, "t1": ""}, {"t0": "  ", "t1": 2}, {"t0": " 1 ", "t1": "\t2\n"}, {"t0": "1_0"},
    {"t0": "1__0"}, {"t0": "_1"}, {"t0": "0x5"}, {"t0": "1.", "t1": ".5e1"}, {"t0": "1.e0", "t1": "3"},
    {"t0": "+1", "t1": "-2"}, {"t0": True, "t1": 2}, {"t0": False, "t1": 2}, {"t0": 1, "t1": False},
    {"t0": 1, "t1": True}, {"t0": [], "t1": {}}, {"t0": [1], "t1": 2}, {"t0": {"a": 1}, "t1": 2},
    {"t0": 1, "t1": [2]}, {"t0": "0", "t1": "0.5"}, {"t0": 0.0005, "t1": 1.0005}, {"t0": 1.0015, "t1": 1.0515},
    {"t0": 2.5, "t1": 2.5494}, {"t0": 2.5, "t1": 2.5506},
]
# ECART DATE (re-revues T2 et T3) : chiffres Unicode non ASCII -- float() les lit, la couche non.
UNICODE = [{"t0": "٣", "t1": 4}, {"t0": 1, "t1": "３"}]
CLIPS = [(2, 6), (0, 4), (-1, 3), (2, 2.03), (2, 2.06), (0.3333, 1.7777)]
TGS = [-0.5, 0, 0.0005, 0.5, 1, 1.0005, 1.02, 2, 2.03, 2.5, 2.549, 2.5494, 2.55, 3, 3.0005, 3.02, 3.05, 3.5, 4,
       4.5, 5, 5.9, 5.999, 6, 7]


def table(bornes):
    return [[s, e, dict(b, type=TY), tg] for (s, e) in CLIPS for b in bornes for tg in TGS]


CAS, CASU = table(BORNES), table(UNICODE)


def py_present(c):
    s, e, f, tg = c
    try:
        return bool(ms._cadre_neufs({"adjust": [{"start": s, "end": e, "effects": [f]}], "t_global": tg}).get("adjust"))
    except Exception as ex:                  # noqa: BLE001
        return "LEVE %s" % type(ex).__name__


_PROBE2 = r"""
var C=__C__,U=__U__;
function pres(c){try{return dzmGlAdjust([{tr:"j1",id:"jj",start:c[0],end:c[1],effects:[c[2]]}],c[3]).length>0}
  catch(e){return "LEVE "+e}}
console.log(JSON.stringify({cas:C.map(pres),uni:U.map(pres)}));
"""
D2, _w2 = node_json("ria_j1.js", '"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n"
                    + _PROBE2.replace("__C__", json.dumps(CAS)).replace("__U__", json.dumps(CASU)))
PYP = [py_present(c) for c in CAS] if ms is not None else []
JSP = D2.get("cas") if isinstance(D2.get("cas"), list) else []
DV2 = [(CAS[i], PYP[i], JSP[i]) for i in range(min(len(PYP), len(JSP))) if PYP[i] is not JSP[i]]
check("x2_table_generee_plus_de_7900_cas_les_deux_verdicts_presents_des_deux_cotes",
      len(CAS) >= 7900 and len(PYP) == len(JSP) == len(CAS) and PYP.count(True) >= 500 and PYP.count(False) >= 3000
      and JSP.count(True) >= 500, (len(CAS), len(PYP), len(JSP), PYP.count(True), _w2))
check("x2_dzmGlAdjust_egal_a_cadre_neufs_sur_toute_la_table_aucune_divergence",
      len(PYP) == len(JSP) == len(CAS) >= 7900 and DV2 == [], (len(DV2), DV2[:4]))
PYU = [py_present(c) for c in CASU] if ms is not None else []
JSU = D2.get("uni") if isinstance(D2.get("uni"), list) else []
_du = [i for i in range(min(len(PYU), len(JSU))) if PYU[i] is not JSU[i]]
check("x2_ecart_date_chiffres_unicode_non_ascii_divergent_bien_et_seulement_eux_sont_exclus",
      len(PYU) == len(JSU) == len(CASU) > 0 and len(_du) >= 4 and all(isinstance(v, bool) for v in PYU + JSU),
      (len(_du), len(CASU)))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[3] dictee : corps multipart de la couche == contrat des deux routes de dictation_service")


def champs_client(src):
    """{url: [champs appendus au FormData envoye a url]} lus dans la couche."""
    out = {}
    for var in re.findall(r"var (f\d+) = new W\.FormData\(\);", src):
        m = re.search(r'W\.fetch\("(/api/dictation[a-z/]*)", \{ method: "POST", body: %s \}\)' % var, src)
        if m:
            out[m.group(1)] = re.findall(r'\b%s\.append\("([a-z_]+)"' % var, src)
    return out


CC = champs_client(CIA)
SC = {}
if ds is not None:
    for _r in ds.router.routes:
        dep = getattr(_r, "dependant", None)
        if dep is not None and "POST" in (getattr(_r, "methods", set()) or set()):
            SC["/api" + _r.path] = {p.name: bool(p.field_info.is_required()) for p in dep.body_params}
check("x3_la_couche_envoie_deux_formdata_aux_deux_routes_de_dictee",
      set(CC) == {"/api/dictation/estimate", "/api/dictation"} and CC.get("/api/dictation/estimate") == ["file"]
      and CC.get("/api/dictation") == ["file", "max_usd", "language"], CC)
check("x3_champs_du_client_egaux_aux_parametres_de_corps_du_serveur_et_les_obligatoires_envoyes",
      bool(CC) and set(SC) == set(CC)
      and all(set(CC[u]) == set(SC[u]) and {k for k, req in SC[u].items() if req} <= set(CC[u]) for u in CC)
      and SC.get("/api/dictation", {}).get("max_usd") is True, (CC, SC))

# joue les deux corps du client sur le TestClient : ffmpeg et le fournisseur sont des espions
_tr, _res3 = [], {}
_cli = None
try:
    from fastapi.testclient import TestClient
    from app.main import app
    _cli = TestClient(app, raise_server_exceptions=False)          # SANS `with` : aucun lifespan
except Exception as e:                       # noqa: BLE001
    print(f"  (TestClient impossible : {e!r})")


def _faux_transcodage(contents, tmpd):
    out = pathlib.Path(tmpd) / "prise.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000 * 3)
    return out


def _faux_transcribe(path, provider=None, language=None, **k):
    _tr.append((provider, language))
    return {"text": "bonjour"}


if _cli is not None and ds is not None and ts is not None:
    _o = (ds._transcoder, ts.transcribe)
    ds._transcoder, ts.transcribe = _faux_transcodage, _faux_transcribe
    try:
        _est = _cli.post("/api/dictation/estimate", files={"file": ("dictee.webm", b"xx", "audio/webm")})
        _ej = _est.json() if _est.status_code == 200 else {}
        _usd = _ej.get("usd")
        # le client envoie String(usd) : la valeur EXACTE rendue par le serveur
        _d = _cli.post("/api/dictation", files={"file": ("dictee.webm", b"xx", "audio/webm")},
                       data={"max_usd": str(_usd), "language": "fr-FR"})
        _res3["ok"] = (_est.status_code, _ej, _d.status_code, _d.json() if _d.status_code == 200 else _d.text[:200],
                       list(_tr))
        _tr.clear()
        _sans = _cli.post("/api/dictation", files={"file": ("dictee.webm", b"xx", "audio/webm")},
                          data={"language": "fr-FR"})
        _res3["sans"] = (_sans.status_code, list(_tr))
    except Exception as e:                   # noqa: BLE001
        _res3["erreur"] = repr(e)
    finally:
        ds._transcoder, ts.transcribe = _o
_r3 = _res3.get("ok") or (None, {}, None, None, [])
check("x3_corps_du_client_joue_estimation_200_puis_transcription_200_au_max_usd_rendu_langue_fr",
      _r3[0] == 200 and isinstance(_r3[1].get("usd"), float) and _r3[1].get("available") is True
      and _r3[2] == 200 and isinstance(_r3[3], dict) and _r3[3].get("text") == "bonjour"
      and _r3[4] == [(_r3[1].get("provider"), "fr")], (_res3,))
_r3s = _res3.get("sans") or (None, None)
check("x3_temoin_sans_max_usd_422_et_aucune_transcription_le_corps_complet_passait",
      _r3s[0] == 422 and _r3s[1] == [] and _r3[2] == 200, _res3)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[4] catalogue image : CATALOGUE_IMAGE (couche) == list_image_models == pricing._IMAGE_MODELS")
_cat_src = CIA[CIA.find("var CATALOGUE_IMAGE = ["):CIA.find("];", CIA.find("var CATALOGUE_IMAGE = ["))]
CAT = re.findall(r'\["([a-z0-9.\-]+)", "([^"]+)", "([A-Z_]+)"\]', _cat_src)
_lim = {}
if _cli is not None:
    try:
        from app.api import routes as _rt

        async def _aucun_reglage(session, key):
            return ""                        # SANS lifespan, pas de table : aucun defaut configure

        _o4 = _rt._atelier_setting
        _rt._atelier_setting = _aucun_reglage
        try:
            _ra = _cli.get("/api/image-models")
        finally:
            _rt._atelier_setting = _o4
        _lim = _ra.json() if _ra.status_code == 200 else {"code": _ra.status_code, "txt": _ra.text[:200]}
    except Exception as e:                   # noqa: BLE001
        _lim = {"erreur": repr(e)}
SRV_IM = {m["id"]: m for m in (_lim.get("models") or []) if isinstance(m, dict)}
PRI_IM = set(getattr(pr, "_IMAGE_MODELS", {}) or {}) if pr is not None else set()
_ids = [c[0] for c in CAT]
check("x4_catalogue_de_la_couche_lu_onze_ids_uniques",
      len(CAT) == 11 and len(set(_ids)) == 11, _ids)
check("x4_ids_du_catalogue_egaux_a_list_image_models_deux_cles_posees_et_a_pricing_image_models",
      len(CAT) == 11 and set(_ids) == set(SRV_IM) == PRI_IM,
      ("couche seule", sorted(set(_ids) - set(SRV_IM)), "serveur seul", sorted(set(SRV_IM) - set(_ids)),
       "pricing", sorted(PRI_IM ^ set(_ids)), _lim if not SRV_IM else ""))
_cle = {"fal": "FAL_KEY", "openai": "OPENAI_API_KEY"}
_mauv = [(i, l, k, (SRV_IM.get(i) or {}).get("label"), (SRV_IM.get(i) or {}).get("provider"))
         for i, l, k in CAT if l != (SRV_IM.get(i) or {}).get("label") or k != _cle.get((SRV_IM.get(i) or {}).get("provider"))]
check("x4_libelles_et_cle_exigee_du_catalogue_egaux_au_libelle_et_au_fournisseur_du_serveur",
      len(CAT) == 11 and len(SRV_IM) == 11 and _mauv == [], _mauv)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[5] vignette video du bundle : tarif et plafond de Seedance 2.5 == pricing")
_i0 = BUN.find("var dzVmRates=")
_i1 = BUN.find("function DzVideoModelSel(", _i0)
_COST = BUN[_i0:_i1] if _i0 >= 0 and _i1 > _i0 else ""
DUREES = list(range(4, 31))
_PROBE5 = r"""
__C__
var D=__D__;
console.log(JSON.stringify({rates:dzVmRates,c25:D.map(function(d){return dzVmCost({props:{model:"seedance-2.5",durationS:d}})}),
  vide:D.map(function(d){return dzVmCost({props:{durationS:d}})})}));
"""
D5, _w5 = node_json("ria_vm.js", _PROBE5.replace("__C__", _COST).replace("__D__", json.dumps(DUREES))) if _COST else ({}, "extrait vide")
RATES = D5.get("rates") if isinstance(D5.get("rates"), dict) else {}
_P = pr.load() if pr is not None else {}
_t25 = ((_P.get("video_usd_per_s") or {}).get("seedance-2.5") or {})
_vm25 = (getattr(fs, "VIDEO_MODELS", {}) or {}).get("seedance-2.5") if fs is not None else None
check("x5_taux_de_seedance_2_5_du_bundle_egal_au_720p_de_pricing_et_duree_max_du_registre",
      RATES.get("seedance-2.5") == [_t25.get("720p"), max((_vm25 or {}).get("durations") or [0])]
      and _t25.get("720p") == 0.473 and max((_vm25 or {}).get("durations") or [0]) == 30,
      (RATES.get("seedance-2.5"), _t25, _w5))
_cap = pr.DEFAULTS.get("video_max_gen_s") if pr is not None else None
check("x5_plafond_du_bundle_egal_a_video_max_gen_s_par_defaut_de_pricing",
      _cap == 10 and _COST.count(",en[1],%d)" % (_cap or -1)) == 1, (_cap, _COST[_COST.find("function dzVmCost"):][:200]))


def _usd_srv(model, d):
    return pr.estimate({"kind": "campaign", "ops": [pr.video_request_op(model, d, "720p", p=_P)]}, _P)["total_usd"]


# le client affiche toFixed(2) de d x taux, le serveur garde plus de decimales : l'egalite est au DEMI-CENTIME
# (arrondi d'affichage : 5 s x 0,473 = 2,365 -> « $2.36 » cote client).
_attendu = [_usd_srv("seedance-2.5", d) for d in DUREES] if pr is not None else []
_vide_att = [_usd_srv("", d) for d in DUREES] if pr is not None else []
C25 = D5.get("c25") or []


def _loin(c, a):
    try:
        return abs(float(str(c).lstrip("$")) - float(a)) > 0.005 + 1e-9
    except (TypeError, ValueError):
        return True


_ec = [(d, c, a) for d, c, a in zip(DUREES, C25, _attendu) if _loin(c, a)]
check("x5_dzVmCost_de_seedance_2_5_egal_a_l_estimation_du_serveur_de_4_a_30_s_au_demi_centime",
      len(C25) == len(DUREES) == len(_attendu) == 27 and _ec == [] and C25[-1] == "$4.73" and C25[0] == "$1.89",
      (_ec[:5], C25[:3], _attendu[:3]))
_ecv = [(d, c, a) for d, c, a in zip(DUREES, D5.get("vide") or [], _vide_att) if _loin(c, a)]
check("x5_noeud_sans_modele_chiffre_comme_le_serveur_chiffre_un_modele_vide_defaut_seedance_2_5",
      len(D5.get("vide") or []) == 27 and _ecv == [], _ecv[:5])
# temoin : sans le plafond (le texte d'avant T11), 15 s de 2.5 ne vaut PAS l'estimation du serveur
D5b, _ = node_json("ria_vm_sans.js", _PROBE5.replace("__C__", _COST.replace(",en[1],10)", ",en[1])"))
                   .replace("__D__", json.dumps([15])))
check("x5_temoin_sans_plafond_15_s_de_2_5_chiffres_7_09_contre_4_73_au_serveur",
      (D5b.get("c25") or [None])[0] == "$7.09" and pr is not None and "$%.2f" % _usd_srv("seedance-2.5", 15) == "$4.73",
      (D5b.get("c25"),))

print(f"\n=== {ok} passed, {fail} failed ===")
try:
    from loguru import logger as _lg
    _lg.remove()
except Exception:                            # noqa: BLE001
    pass
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
