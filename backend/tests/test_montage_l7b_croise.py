# -*- coding: utf-8 -*-
"""L7-B — BANC CROISE couche / bundle / service : ce que le lot L7-B ecrit
EN DUR d'un cote du reseau doit etre CE QUE l'autre cote lit, ou etre DATE
comme un ecart. Fichier SEPARE de test_montage_l7b.py (un processus, un code
de sortie). Modele : test_montage_l7_croise.py (regex GARDEES, le literal ET
le comportement, etat vide construit, sous-processus node qui rend {} quand
il meurt). Il n'appelle AUCUN reseau et ne lance AUCUN serveur : les routes
sont appelees en direct avec une vraie Request starlette (client 127.0.0.1),
les couches basses espionnees.
Run : & $PY tests/test_montage_l7b_croise.py   (depuis backend/)

CE QUI EST COMPARE.
  [1] D-37 : les champs de clip LUS par `edl_export` (EDL et FCPXML, regex
      `c.get("…")`) ⊂ les champs du MODELE CLIENT que la sauvegarde envoie
      TELS QUELS (`svmSavePayload` : `clips:clips`) -- mesures par ce que la
      couche et le bundle LISENT d'un clip (`c.<cle>` de renderPayload et de
      subsPayload, DZM_DIFF_CLES et l'`id` de dzmDiffIndex) ; les cles de
      l'enregistrement lues par la route (`name`, `tracks`, `clips`,
      `ratio`) ⊂ les cles du litteral de svmSavePayload ; les clips ECRITS
      par `/autoclips/create` ⊂ ce meme modele ; temoins : `src_in` (le nom
      du FIL de rendu) n'est PAS lu par l'export, et l'EDL reagit a chaque
      champ lu qu'on fait varier (vitesse -> M2, libelle -> CLIP LABEL,
      transition -> D).
  [2] D-40 : bornes du cadrage -- `dzmReframeOf` (couche, sous node) et
      `_reframe_of` (service) rendent le MEME resultat sur un jeu de cas
      TIRES (graine fixe) et sur des cas limites ; constantes egales (240
      points, 5 ms, vitesse 0,25..4).
  [3] D-34 : la note -- les seuils des chips (DZM_NOTE_CHIPS) passent tels
      quels par la route `GET /api/jobs?min_rating=` jusqu'a
      `Pipeline.list_jobs` (espion) ; le nom du parametre de l'URL client ==
      celui de la route ; toute note produite par dzmRatingNext, passee par
      JSON, est ACCEPTEE par `PUT /jobs/{id}/rating`, et ce que la route
      REFUSE est lu 0 par dzmRatingNorm.
  [4] D-41 : les parametres envoyes par `DzmAutoclips` (dzmAcPayload sous
      node, toutes options) ⊂ les parametres LUS par la route
      (`body.get("…")`), dont `max_usd`, `confirm`, `llm`, `lang` ; les
      langues du client passent la garde de la route ; le corps de
      « Creer le projet » ⊂ ce que lit `/autoclips/create` ; les segments
      rendus par le service portent les cles que `create` lit.
  [5] Menus : « Exporter EDL… », « Exporter FCPXML… » et « Decouper aux
      changements de plan » ont chacun une ACTION (`run:function(){…}`) dont
      la fonction est definie une fois dans le bundle, et les formats
      demandes == `_EXPORT_FORMATS` de la route.

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
Faute n°6 : aucune lecture nue ; un dict vide de node ou une regex qui ne
trouve rien fait ROUGIR, pas mourir.
"""
import asyncio
import inspect
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl7bx_")
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


def un(motif, texte, flags=0):
    """LA regex gardee : le match si le motif est trouve EXACTEMENT une fois."""
    ms_ = list(re.finditer(motif, texte, flags))
    return (ms_[0] if len(ms_) == 1 else None), len(ms_)


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
        return (200, v)
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
MSV = lire("backend/app/services/montage_service.py")
EDL = lire("backend/app/services/edl_export.py")
check("x0_couche_bundle_service_et_edl_export_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(MSV) > 100_000 and len(EDL) > 5_000,
      (len(JS), len(BUN), len(MSV), len(EDL)))
check("x0_node_est_sur_le_PATH", bool(NODE), NODE)

try:
    from app.services import montage_service as ms
    from app.services import edl_export as ex
    from app.services import autoclips as ac
except Exception as e:                       # le banc rougit, ne meurt pas
    ms = ex = ac = None
    print(f"  (import des services impossible : {e!r})")
try:
    from app.api import routes as rt
    from app.services import pipeline as pl
except Exception as e:
    rt = pl = None
    print(f"  (import des routes impossible : {e!r})")
check("x0_services_et_routes_importes_avec_les_symboles_L7B",
      ms is not None and ex is not None and ac is not None and rt is not None and pl is not None
      and all(hasattr(ms, k) for k in ("_reframe_of", "_RF_MAX_POINTS", "montage_autoclips", "montage_autoclips_create",
                                       "montage_export", "_EXPORT_FORMATS", "_v1_speed"))
      and all(hasattr(rt, k) for k in ("list_jobs", "rate_job")),
      (ms, ex, ac, rt, pl))

# ── la couche ENTIERE sous node (shim du banc edition) : les cas sont passes en JSON par python
random.seed(24092026)


def _tire_num():
    r = random.random()
    if r < 0.08:
        return random.choice([None, True, False, "abc", "", "nan", "inf", -1e9, 1e9, [], {}])
    if r < 0.2:
        return str(round(random.uniform(-2, 12), random.choice([0, 1, 2, 3, 4])))
    return round(random.uniform(-2, 12), random.choice([0, 1, 2, 3, 4, 6]))


def _tire_cas():
    mode = random.choice(["suivi", "suivi", "suivi", "manuel", "manuel", "centre", "zz", None])
    c = {"start": _tire_num() if random.random() < 0.15 else round(random.uniform(0, 30), 3)}
    c["end"] = _tire_num() if random.random() < 0.15 else round(c["start"] + random.uniform(0.2, 12), 3) \
        if isinstance(c["start"], (int, float)) and not isinstance(c["start"], bool) else 5
    sp = random.random()
    if sp < 0.4:
        c["speed"] = random.choice([2, 0.5, 0.25, 4, 10, 0.1, 1, "2", "abc", 0, -1, None, True, 1.5])
    rf = {"mode": mode}
    if mode == "manuel":
        rf["x"] = _tire_num() if random.random() < 0.5 else round(random.uniform(-0.5, 1.5), 4)
    elif mode == "suivi":
        n = random.choice([0, 1, 2, 5, 30, 239, 240, 241, 300, 500])
        pts = []
        for _ in range(n):
            t = round(random.uniform(-1, 20), random.choice([2, 3, 4]))
            x = round(random.uniform(-0.3, 1.3), 4)
            u = random.random()
            if u < 0.05:
                pts.append([t, x])
            elif u < 0.08:
                pts.append({"t": _tire_num(), "x": x})
            elif u < 0.1:
                pts.append("zz")
            else:
                pts.append({"t": t, "x": x})
        rf["points"] = pts
    c["reframe"] = rf if random.random() > 0.05 else random.choice(["suivi", [1], None])
    return c


CAS = [_tire_cas() for _ in range(160)]
# cas LIMITES ecrits a la main : t pile a la duree de source, doublons a 5 ms, 5 ms moins un epsilon, vitesse bornee
CAS += [
    {"start": 0, "end": 4, "speed": 2, "reframe": {"mode": "suivi", "points": [{"t": 8, "x": 0.5}, {"t": 9, "x": 0.6}]}},
    {"start": 0, "end": 4, "reframe": {"mode": "suivi", "points": [{"t": 1, "x": 0.1}, {"t": 1.004, "x": 0.9}, {"t": 1.005, "x": 0.3}]}},
    {"start": 1, "end": 3, "speed": 10, "reframe": {"mode": "suivi", "points": [{"t": 7.9, "x": 0.2}, {"t": 99, "x": 2}]}},
    {"start": 0, "end": 2, "reframe": {"mode": "manuel", "x": "0.25"}},
    {"start": 0, "end": 2, "reframe": {"mode": "manuel", "x": True}},
    {"start": 0, "end": 2, "reframe": {"mode": "centre", "x": 0.3}},
    {"start": 0, "end": 2, "reframe": {"mode": "suivi", "points": [{"t": 0.0005, "x": 0.5}, {"t": 0.0015, "x": 0.6}]}},
    # le PLAFOND : 300 et 241 points distincts (pas de 10 ms) -> 240 sous-echantillonnes des deux cotes
    {"start": 0, "end": 10, "reframe": {"mode": "suivi", "points": [{"t": round(i * 0.01, 3), "x": round((i % 17) / 16, 4)} for i in range(300)]}},
    {"start": 0, "end": 10, "speed": 0.5, "reframe": {"mode": "suivi", "points": [{"t": round(i * 0.013, 3), "x": 0.5} for i in range(241)]}},
]
N_CAS_169 = len(CAS)
# revue finale du lot (24/09/2026) : points du CHAMP en temps ABSOLU de source, srcIn COURANT soustrait des deux
# cotes -- les 169 cas rejoues tels quels (srcIn absent = 0), puis 80 copies des cas tires avec un srcIn tire
# (nombres, chaines, negatifs, illisibles) et des cas LIMITES de fenetre ecrits a la main.
random.seed(25092026)
for _c in CAS[:80]:
    _k = json.loads(json.dumps(_c))
    _u = random.random()
    _k["srcIn"] = (random.choice([None, "abc", True, -3, "4.5", "", 1e9]) if _u < 0.12
                   else round(random.uniform(0, 15), random.choice([0, 1, 2, 3, 4])))
    CAS.append(_k)
CAS += [
    # bords pile sur des points (aucun point de bord ajoute), points de part et d'autre, tout avant, tout apres
    {"start": 0, "end": 2, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 5, "x": 0.2}, {"t": 7, "x": 0.8}]}},
    {"start": 0, "end": 2, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 4, "x": 0.2}, {"t": 6, "x": 0.4}, {"t": 8, "x": 0.8}]}},
    {"start": 0, "end": 2, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 1, "x": 0.2}, {"t": 2, "x": 0.9}]}},
    {"start": 0, "end": 2, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 10, "x": 0.2}, {"t": 12, "x": 0.9}]}},
    {"start": 0, "end": 2, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 4, "x": 0.2}, {"t": 9, "x": 0.9}]}},
    # vitesse x2 : fenetre de 4 s de source ; srcIn en chaine ; srcIn negatif (borne a 0) ; sans fin lisible
    {"start": 1, "end": 3, "speed": 2, "srcIn": "3.25", "reframe": {"mode": "suivi", "points": [{"t": 3, "x": 0.1}, {"t": 8, "x": 0.9}]}},
    {"start": 1, "end": 3, "srcIn": -2, "reframe": {"mode": "suivi", "points": [{"t": -1, "x": 0.1}, {"t": 3, "x": 0.9}]}},
    {"start": 1, "end": "zz", "srcIn": 2, "reframe": {"mode": "suivi", "points": [{"t": 1, "x": 0.1}, {"t": 9, "x": 0.9}]}},
    # un point a 1 ms du bord (doublon a 5 ms avec le point de bord : le dernier gagne), la decoupe [0,10] -> [5,10]
    {"start": 0, "end": 2, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 4, "x": 0.2}, {"t": 5.001, "x": 0.3}, {"t": 7, "x": 0.8}]}},
    {"start": 5, "end": 10, "srcIn": 5, "reframe": {"mode": "suivi", "points": [{"t": 0, "x": 0.2}, {"t": 10, "x": 0.8}]}},
]
AC_E = {"src": {"job_id": "j1"}, "text": "  un texte  ", "n": "3", "persona": " gamer ", "llm": False, "lang": "de"}
_PROBE = r"""
var T=DzTracks,out={};
var CAS=__CAS__;
out.rf=CAS.map(function(c){var r=T.reframeOf(c);return r===void 0?"UNDEF":r});
out.rf_max=typeof DZM_RF_MAX==="number"?DZM_RF_MAX:null;
out.note_chips=DZM_NOTE_CHIPS.map(function(n){return n[0]});
out.rating_next=(function(){var r=[],a,b;for(a=-1;a<=6;a++)for(b=-1;b<=6;b++)r.push(T.ratingNext(a,b));return r})();
out.rating_norm=["3",3.5,true,null,6,-1,3,0,5].map(function(v){return T.ratingNorm(v)});
var AE=__ACE__,EOK={ok:true,usd:.05,pour:T.acCle(AE.src)};
out.ac_libre=T.acPayload(AE);
out.ac_paye=T.acPayload({src:AE.src,n:2,persona:"p",llm:true,lang:"en",payer:EOK,vu:EOK});
out.ac_langs=DZM_AC_LANGS;
console.log(JSON.stringify(out));
"""
_shim = ('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n"
         + _PROBE.replace("__CAS__", json.dumps(CAS)).replace("__ACE__", json.dumps(AC_E)))
D, _dwhy = node_json("l7bx_couche.js", _shim)
check("x0_la_couche_s_execute_sous_node_et_rend_les_sept_cles_de_la_sonde",
      bool(D) and all(k in D for k in ("rf", "rf_max", "note_chips", "rating_next", "rating_norm", "ac_libre", "ac_paye")),
      _dwhy or sorted(D))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[1] D-37 : champs de clip lus par l'EDL/FCPXML ⊂ modele client sauvegarde tel quel ; clips de /autoclips/create")
LU = set(re.findall(r'\b(?:c|a\[4\])\.get\("([A-Za-z_]+)"', EDL))
LU_REC = set(re.findall(r'\brec\.get\("([A-Za-z_]+)"', EDL))
check("x1_l_export_lit_au_moins_src_srcIn_start_end_speed_transition_label_et_rec_name_tracks_clips",
      {"src", "srcIn", "start", "end", "speed", "transition", "transition_s", "label", "tr"} <= LU
      and {"name", "tracks", "clips"} <= LU_REC, (sorted(LU), sorted(LU_REC)))
RP = entre(BUN, "  function renderPayload(preview,queue){", "  function launchRender(")
SP = entre(BUN, "  function subsPayload(){", "  function subs")
SVP = entre(BUN, "  function svmSavePayload(){", "  function svmDoSave(")
mC, nC = un(r'^var DZM_DIFF_CLES=(\[[^\]]*\]);$', JS, re.M)
try:
    CLES = json.loads(mC.group(1)) if mC else []
except ValueError:
    CLES = []
IDX = entre(JS, "function dzmDiffIndex(clips){", "function dzmDiff(a,b){")
LU_RP = set(re.findall(r'\bc\.([A-Za-z_]+)', RP))
LU_SP = set(re.findall(r'\b[cs]\.([A-Za-z_]+)', SP))   # subsPayload lit ses segments par `s.` (text, words, hidden)
LU_IDX = set(re.findall(r'\bc\.([A-Za-z_]+)', IDX))
CLIENT = LU_RP | LU_SP | set(CLES) | LU_IDX | {"srcIn", "start", "end"}
check("x1_le_modele_client_est_mesure_renderPayload_subsPayload_svmSavePayload_DZM_DIFF_CLES_et_dzmDiffIndex_trouves",
      len(RP) > 2000 and len(SP) > 200 and len(SVP) > 300 and nC == 1 and len(CLES) == 19 and "id" in LU_IDX
      and {"tr", "src", "start", "end", "srcIn", "speed"} <= LU_RP, (len(RP), len(SP), len(SVP), nC, len(CLES), sorted(LU_IDX)))
ORPH = sorted(LU - CLIENT)
check("x1_tout_champ_de_clip_lu_par_l_export_est_un_champ_du_modele_client_aucune_orpheline_temoin_srcIn_lu_des_deux_cotes",
      len(LU) >= 9 and "srcIn" in LU and "srcIn" in CLIENT and ORPH == [], (ORPH, sorted(LU), sorted(CLIENT)))
# la sauvegarde envoie les clips TELS QUELS : c'est ce modele que _load_saved relit pour l'export
check("x1_svmSavePayload_envoie_clips_tels_quels_et_name_ratio_tracks_que_la_route_relit",
      SVP.count("clips:clips") == 1 and all(("%s:" % k) in SVP for k in ("name", "ratio", "tracks"))
      and LU_REC <= {"name", "tracks", "clips", "ratio"} and MSV.count('str(rec.get("ratio") or "9:16")') == 1,
      (SVP.count("clips:clips"), sorted(LU_REC)))
# temoin negatif : l'export ne lit PAS le nom du fil de rendu `src_in` (il lit la SAUVEGARDE, pas renderPayload)
check("x1_temoin_l_export_ne_lit_pas_src_in_nom_du_fil_de_rendu_mais_srcIn",
      "srcIn" in LU and "src_in" not in LU and EDL.count('"src_in"') == 0 and RP.count("srcIn:c.srcIn") == 1, sorted(LU))
# les clips ECRITS par /autoclips/create : leurs cles (dict litteraux du corps de la route) ⊂ modele client (+ words des S1)
CRE = entre(MSV, "async def montage_autoclips_create(request: Request):", "\ndef _f_or(")
# la tranche qui construit les clips (de `clips = [` a `_save_record(`), les cles litterales `"k":` et `s1["k"] =` ;
# `w` est la cle d'un MOT (words[].w), pas d'un clip -- ecartee et comptee a part
BATI = entre(CRE, "    clips = [{", "    cur = _save_record(")
CLES_CRE = set(re.findall(r'"([A-Za-z_]+)": ', BATI)) | set(re.findall(r's1\["([A-Za-z_]+)"\] =', BATI))
check("x1_les_clips_ecrits_par_autoclips_create_portent_des_champs_du_modele_client_seulement",
      len(BATI) > 800 and BATI.count('{"tr": "') == 3 and "w" in CLES_CRE
      and {"tr", "id", "label", "src", "srcIn", "start", "end", "text", "words", "transition"} <= CLES_CRE
      and sorted(CLES_CRE - CLIENT - {"w"}) == [], (len(BATI), sorted(CLES_CRE), sorted(CLES_CRE - CLIENT)))
# comportement : l'EDL REAGIT a chaque champ lu qu'on fait varier (sinon « lu » ne veut rien dire)
_SRC = os.path.join(TMP, "p.mp4")
open(_SRC, "wb").write(b"x")


def _edl(**kw):
    c = dict({"tr": "v1", "id": "a", "label": "Plan", "src": {"file_path": _SRC}, "srcIn": 0, "start": 0, "end": 2,
              "transition": "cut", "transition_s": 0}, **kw)
    rec = {"name": "x", "tracks": [{"id": "v1", "kind": "video"}], "clips": [c]}
    try:
        return ex.to_edl(rec, {ex.src_key({"file_path": _SRC}): {"path": _SRC, "dur": 60.0, "video": True}}, fps=30)
    except Exception as e:
        return "ERR %r" % e


_e1, _e2, _e3 = _edl(), _edl(speed=2), _edl(label="Autre")
check("x1_comportement_l_edl_reagit_a_speed_M2_et_au_label_CLIP_LABEL_temoin_sans_vitesse_ni_M2_ni_SPEED",
      "* CLIP LABEL: Plan" in _e1 and "M2   " not in _e1 and "* SPEED:" not in _e1
      and "M2   AX       060.0" in _e2 and "* SPEED: 2" in _e2 and "* CLIP LABEL: Autre" in _e3, (_e1, _e2, _e3))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[2] D-40 : dzmReframeOf (couche, sous node) == _reframe_of (service) sur %d cas tires et limites" % len(CAS))


def _py_rf(c):
    try:
        r = ms._reframe_of(c)
    except Exception as e:
        return "LEVE %s" % type(e).__name__
    if r is None:
        return None
    if r.get("mode") == "suivi":
        return {"mode": "suivi", "points": [{"t": t, "x": x} for t, x in r["points"]]}
    return r


def _norm(v):
    """Les nombres en float arrondis a 1e-9 (JSON de node rend 1 pour 1.0)."""
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), 9)
    return v


PYRF = [_norm(_py_rf(c)) for c in CAS] if ms is not None else []
_RFO_TXT = inspect.getsource(ms._reframe_of) if ms is not None else ""
JSRF = [_norm(v) for v in D.get("rf", [])] if isinstance(D.get("rf"), list) else []
DIFF = [(i, CAS[i], PYRF[i], JSRF[i]) for i in range(min(len(PYRF), len(JSRF))) if PYRF[i] != JSRF[i]]
_n_suivi = sum(1 for v in PYRF if isinstance(v, dict) and v.get("mode") == "suivi")
_n_manuel = sum(1 for v in PYRF if isinstance(v, dict) and v.get("mode") == "manuel")
_n_none = sum(1 for v in PYRF if v is None)
_n_240 = sum(1 for v in PYRF if isinstance(v, dict) and len(v.get("points") or []) == 240)
check("x2_le_jeu_tire_couvre_suivi_manuel_centre_et_le_plafond_240_des_deux_cotes",
      len(PYRF) == len(CAS) == len(JSRF) and _n_suivi >= 20 and _n_manuel >= 10 and _n_none >= 20 and _n_240 >= 2,
      (len(PYRF), len(JSRF), _n_suivi, _n_manuel, _n_none, _n_240))
_n_src = sum(1 for i, c in enumerate(CAS) if c.get("srcIn") not in (None, 0) and i < len(PYRF)
             and isinstance(PYRF[i], dict) and PYRF[i].get("mode") == "suivi")
check("x2_revue_finale_169_cas_d_origine_puis_des_cas_srcIn_non_nul_suivis_des_deux_cotes",
      N_CAS_169 == 169 and len(CAS) == 169 + 80 + 10 and _n_src >= 30
      and JS.count("win.forEach(function(q){q={t:dzmRfR3(q.t-a),x:q.x};") == 1
      and _RFO_TXT.count("for q in [(round(t - a, 3), x) for t, x in win]:") == 1, (N_CAS_169, len(CAS), _n_src))
check("x2_les_deux_cotes_rendent_le_meme_cadrage_sur_tous_les_cas_aucune_divergence",
      len(PYRF) == len(CAS) == len(JSRF) and DIFF == [], DIFF[:3])
_RFO = inspect.getsource(ms._reframe_of) if ms is not None else ""
check("x2_constantes_egales_240_points_des_deux_cotes_5_ms_et_vitesse_0_25_a_4",
      D.get("rf_max") == 240 and getattr(ms, "_RF_MAX_POINTS", None) == 240
      and JS.count("q.t-out[out.length-1].t<.005") == 1 and _RFO.count("q[0] - out[-1][0] < 0.005") == 1
      and _RFO.count("_v1_speed(c) or 1.0") == 1
      and JS.count("return Math.max(.25,Math.min(4,v))}") == 1 and MSV.count("f = max(0.25, min(4.0, f))") == 1,
      (D.get("rf_max"), getattr(ms, "_RF_MAX_POINTS", None)))
# ETAT VIDE : le meme comparateur VOIT une divergence qu'on fabrique (le premier suivi, un point decale)
_i_s = next((i for i, v in enumerate(PYRF) if isinstance(v, dict) and v.get("mode") == "suivi"), None)
_faux = json.loads(json.dumps(JSRF[_i_s])) if _i_s is not None and _i_s < len(JSRF) else None
if isinstance(_faux, dict) and _faux.get("points"):
    _faux["points"][0]["x"] = round(_faux["points"][0]["x"] + 0.001, 9)
check("x2_etat_vide_le_comparateur_voit_une_divergence_fabriquee_temoin_egal_avant",
      _i_s is not None and PYRF[_i_s] == JSRF[_i_s] and _faux is not None and _faux != PYRF[_i_s], _i_s)

# ═════════════════════════════════════════════════════════════════════════════
print("\n[3] D-34 : seuils des chips == min_rating de la route jusqu'a list_jobs ; notes du client acceptees par PUT")
CHIPS = D.get("note_chips") if isinstance(D.get("note_chips"), list) else []
_vus = []


async def _faux_list(**kw):
    _vus.append(kw.get("min_rating"))
    return []
_lj0 = pl.Pipeline.list_jobs if pl is not None else None
_rl = []
if rt is not None and pl is not None:
    pl.Pipeline.list_jobs = staticmethod(_faux_list)
    try:
        for s in CHIPS + [0]:
            _rl.append(asyncio.run(appel(rt.list_jobs, 24, 0, None, None, 1, s)))
    finally:
        pl.Pipeline.list_jobs = _lj0
check("x3_chaque_seuil_des_chips_passe_tel_quel_de_la_route_a_list_jobs_temoin_0_sans_filtre",
      CHIPS == [3, 5] and _vus == [3, 5, 0] and all(r[0] == 200 for r in _rl), (CHIPS, _vus, _rl))
_sig = list(inspect.signature(rt.list_jobs).parameters) if rt is not None else []
check("x3_le_parametre_d_url_du_client_est_celui_de_la_route_min_rating",
      "min_rating" in _sig and JS.count('+(minNote>0?"&min_rating="+minNote:"")') == 1
      and BUN.count('+(minNote>0?"&min_rating="+minNote:"")') == 1, _sig)
_n_pl = entre(lire("backend/app/services/pipeline.py"), "min_rating = max(0, min(5, int(min_rating or 0)))", "async with")
check("x3_les_seuils_sont_dans_les_bornes_que_list_jobs_ramene_0_5",
      len(_n_pl) > 20 and all(isinstance(s, int) and 1 <= s <= 5 for s in CHIPS), (CHIPS, len(_n_pl)))


class _FJ:
    pass


async def _faux_set(job_id, r):
    return None                          # 404 : la VALIDATION est passee


def _put(v):
    body = json.loads(json.dumps({"rating": v}))       # le FIL : ce que JSON.stringify/json.loads laissent passer
    return asyncio.run(appel(rt.rate_job, "j1", REQ("/api/jobs/j1/rating", body)))


_sr0 = pl.Pipeline.set_rating if pl is not None else None
NEXT = sorted(set(D.get("rating_next") or [])) if isinstance(D.get("rating_next"), list) else []
_acc, _ref = [], []
if rt is not None and pl is not None:
    pl.Pipeline.set_rating = staticmethod(_faux_set)
    try:
        _acc = [_put(v) for v in NEXT]
        _ref = [_put(v) for v in ["3", 3.5, True, None, 6, -1]]
    finally:
        pl.Pipeline.set_rating = _sr0
check("x3_toute_note_produite_par_ratingNext_est_acceptee_par_PUT_404_job_inconnu_donc_validation_passee",
      NEXT == [0, 1, 2, 3, 4, 5] and [r[0] for r in _acc] == [404] * 6, (NEXT, _acc))
check("x3_ce_que_PUT_refuse_400_est_lu_0_par_ratingNorm_temoin_3_0_et_5_lus_tels_quels",
      [r[0] for r in _ref] == [400] * 6 and D.get("rating_norm") == [0, 0, 0, 0, 0, 0, 3, 0, 5], (_ref, D.get("rating_norm")))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[4] D-41 : parametres de DzmAutoclips ⊂ parametres de la route ; corps de « Creer » ⊂ /autoclips/create")
ROUTE = entre(MSV, "async def montage_autoclips(request: Request):", "\ndef _autoclips_num(")
LUS_R = set(re.findall(r'\bbody\.get\("([A-Za-z_]+)"', ROUTE))
LIB = D.get("ac_libre") if isinstance(D.get("ac_libre"), dict) else {}
PAY = D.get("ac_paye") if isinstance(D.get("ac_paye"), dict) else {}
ENVOI = set(LIB) | set(PAY)
check("x4_la_route_lit_src_text_n_persona_lang_llm_confirm_max_usd_chapter_id_provider",
      len(ROUTE) > 3000 and {"src", "text", "n", "persona", "lang", "llm", "confirm", "max_usd", "chapter_id", "provider"} <= LUS_R,
      sorted(LUS_R))
check("x4_tout_parametre_envoye_par_le_client_est_lu_par_la_route_dont_max_usd_confirm_llm_lang",
      {"src", "n", "llm", "lang", "text", "persona", "confirm", "max_usd"} <= ENVOI and sorted(ENVOI - LUS_R) == [],
      (sorted(ENVOI), sorted(ENVOI - LUS_R)))
# ecart DATE (24/09/2026, T6) : chapter_id et provider sont lus par la route mais jamais envoyes (pas de selecteur)
check("x4_ecart_date_chapter_id_et_provider_lus_par_la_route_jamais_envoyes_par_le_client",
      len(ENVOI) >= 8 and sorted(LUS_R - ENVOI) == ["chapter_id", "provider"], sorted(LUS_R - ENVOI))
check("x4_types_du_fil_confirm_booleen_strict_max_usd_nombre_llm_booleen_n_entier",
      PAY.get("confirm") is True and PAY.get("max_usd") == 0.05 and LIB.get("llm") is False and PAY.get("llm") is True
      and LIB.get("n") == 3 and "confirm" not in LIB and "max_usd" not in LIB
      and ROUTE.count('confirm = body.get("confirm") is True') == 1, (LIB, PAY))
LANGS = D.get("ac_langs") if isinstance(D.get("ac_langs"), list) else []
_lg = []
if ms is not None:
    for lg in LANGS + ["francais"]:
        try:
            ms._autoclips_str(lg, "lang", 5)
            _lg.append("ok")
        except Exception as e:
            _lg.append(getattr(e, "status_code", "?"))
check("x4_les_langues_du_client_passent_la_garde_lang_de_la_route_temoin_francais_400",
      LANGS == ["fr", "en", "es", "de", "it"] and _lg == ["ok"] * 5 + [400]
      and ROUTE.count('lang_raw = _autoclips_str(body.get("lang"), "lang", 5).lower()') == 1, (LANGS, _lg))
# « Creer le projet » : le corps de la couche ⊂ ce que lit /autoclips/create
_mb, _nb = un(r'body:JSON\.stringify\(\{src:o\.src,clip:\{start:c\.start,end:c\.end,segments:[^,]+,title:nom\},\s*name:nom\|\|void 0\}\)', JS)
LUS_C = set(re.findall(r'\bbody\.get\("([A-Za-z_]+)"', CRE)) | {"clip." + k for k in re.findall(r'\bclip\.get\("([A-Za-z_]+)"', CRE)}
check("x4_le_corps_de_creer_src_clip_start_end_segments_title_name_est_lu_par_create",
      _nb == 1 and {"src", "clip", "name", "clip.start", "clip.end", "clip.segments", "clip.title"} <= LUS_C, (_nb, sorted(LUS_C)))
# les segments rendus par le service (autoclips._segments) portent ce que create LIT d'un segment
LUS_SG = set(re.findall(r'\bsg\.get\("([A-Za-z_]+)"', CRE))
LUS_W = set(re.findall(r'\bw\.get\("([A-Za-z_]+)"', CRE)) | ({"w"} if 'w["w"]' in CRE else set())
_win = {"start": 0.0, "end": 3.0, "words": [
    {"w": "bonjour", "raw": "Bonjour", "start": 0.0, "end": 0.5},
    {"w": "le", "raw": "le", "start": 0.6, "end": 0.8},
    {"w": "monde", "raw": "monde.", "start": 0.9, "end": 1.4}]}
try:
    _sg = ac._segments(_win) if ac is not None else []
except Exception as e:
    _sg = [{"ERR": repr(e)}]
_ksg = set().union(*[set(s) for s in _sg]) if _sg else set()
_kw = set().union(*[set(w) for s in _sg for w in (s.get("words") or [])]) if _sg else set()
check("x4_les_segments_du_service_portent_start_end_text_words_que_create_lit_et_leurs_mots_w_start_end",
      len(_sg) >= 1 and {"start", "end", "text", "words"} == LUS_SG and LUS_SG <= _ksg
      and {"w", "start", "end"} == LUS_W and LUS_W <= _kw, (sorted(LUS_SG), sorted(_ksg), sorted(LUS_W), sorted(_kw)))

# ═════════════════════════════════════════════════════════════════════════════
print("\n[5] Menus : chaque entree neuve a une action definie ; formats demandes == formats de la route")
_M = [('{lbl:"Exporter EDL…",run:function(){dzExportTl("edl")}}', "  function dzExportTl(fmt){"),
      ('{lbl:"Exporter FCPXML…",run:function(){dzExportTl("fcpxml")}}', "  function dzExportTl(fmt){"),
      ('{lbl:"Découper aux changements de plan",off:!(c.src&&c.src.job_id)||trackKind(c.tr)!=="video",run:function(){dzSceneCut(id)}}',
       "  function dzSceneCut(id){")]
check("x5_trois_entrees_neuves_x1_chacune_avec_run_et_sa_fonction_definie_une_fois",
      all(BUN.count(e) == 1 and BUN.count(f) == 1 for e, f in _M), [(BUN.count(e), BUN.count(f)) for e, f in _M])
_fmts = sorted(set(re.findall(r'dzExportTl\("([a-z]+)"\)', BUN)))
check("x5_formats_demandes_par_le_menu_egaux_aux_formats_de_la_route_et_la_route_rend_400_sinon",
      _fmts == ["edl", "fcpxml"] and ms is not None and sorted(ms._EXPORT_FORMATS) == _fmts
      and BUN.count('fetch("/api/montage/export?format="+fmt)') == 1, (_fmts, ms and sorted(ms._EXPORT_FORMATS)))
# revue finale (M2) : la route prend la requete (boucle locale seulement)
_bad = asyncio.run(appel(ms.montage_export, REQ("/api/montage/export", {}), "mp4")) if ms is not None else ("?", None)
check("x5_temoin_la_route_refuse_un_format_que_le_menu_n_offre_pas",
      _bad[0] == 400 and "edl" in str(_bad[1]), _bad)
_dz = entre(BUN, "  function dzSceneCut(id){", "  function dzMenuProps(")
check("x5_dzSceneCut_appelle_la_route_scenes_et_le_coeur_cutAt_de_la_couche",
      len(_dz) > 800 and _dz.count('fetch("/api/montage/scenes",') == 1 and _dz.count("DzTracks.cutAt(") == 1
      and JS.count("cutAt:dzmCutAt,") == 1 and hasattr(ms, "montage_scenes"), len(_dz))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
