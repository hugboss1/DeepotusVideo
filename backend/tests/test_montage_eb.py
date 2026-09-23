# -*- coding: utf-8 -*-
"""Lot E-B — E-2 backend (23/09/2026) : `GET /api/jobs` PAGINE ET FILTRE, ET LE
JUGE « VIDEO » EST UNIQUE.

Avant ce lot, `GET /api/jobs` ne prenait que `limit` : le tiroir Medias
aurait du tout charger puis filtrer en JavaScript (et `offset` etait ignore —
c'est l'ETAT VIDE que la section [1] etablit d'abord : la page 2 rendait la
page 1). Ici `offset` pagine, `providers` (liste separee par des virgules)
filtre, `q` cherche dans le titre sans casse, et `video=1` ne garde que les
jobs dont l'artefact porte une extension de la REGLE servie par
`GET /api/montage/media-rules`.

Le banc ne recopie PAS la regle : il lit `/media-rules` UNE fois (temoin
`200`) et l'applique lui-meme pour juger chaque job rendu par `video=1`.
Mesure du 23/09/2026 : `/media-rules` rend `{video_exts:[...]}` et RIEN
d'autre — pas de `video_providers`. Le plan disait « si la regle inclut des
providers, video=1 applique la meme » : elle n'en inclut pas, donc `video=1`
= extension seule, comme `_is_video_artifact` et `DzTracks.isVideoJob`.

Ecart au plan (23/09/2026) : `list_jobs` mesure a pipeline.py:1283-1319 (le
plan disait 1283-1321) ; la route a routes.py:3368-3371. `routes.py`
n'importe pas `montage_service` en tete de module (imports TARDIFS partout,
p. ex. l. 4335) — la route `/jobs` fait de meme pour `media_rules`.

En-tete recopie de test_montage_ea.py (env AVANT `import app`, `check`,
`J`). Les jobs sont INSERES dans la base temporaire par sqlite3 apres le
lifespan (tables creees), avec des `created_at` distincts pour que l'ordre
`created_at.desc()` soit deterministe.
Run : & $PY tests/test_montage_eb.py   (depuis backend/)

PROTOCOLE : toute reponse passe par `J()`/`L()` (jamais `.json()` nu), tout
acces est un `.get`. Une negation ne vaut que si son operande a vecu.
"""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzeb_")
DB = TMP + "/t.db"
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + DB.replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON dict, ou {} — ce banc doit ROUGIR, pas mourir."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {}


def L(resp):
    """Corps JSON liste de dicts, ou None (une liste vide reste une liste)."""
    try:
        v = resp.json()
    except Exception:
        return None
    return [j for j in v if isinstance(j, dict)] if isinstance(v, list) else None


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

# ---- jeu de jobs (sqlite3 direct, tables deja creees par le lifespan) ----
import sqlite3, datetime as _dt
_T0 = _dt.datetime(2026, 9, 23, 12, 0, 0)
JOBS = []  # (id, status, provider, title, video_path, final_video_path)
for i in range(5):
    JOBS.append((f"sd{i}", "done", "seedance", f"Seedance {i}", f"/out/sd{i}.mp4", None))
JOBS.append(("ep1", "done", "episode", "Chapitre 1", None, "/out/ep1.MP4"))
JOBS.append(("nw1", "done", "news", "Journal", "/out/nw1.mov", None))
JOBS.append(("pv1", "done", "template", "Le rendu PREUVE-EB du jour", "/out/pv1.webm", None))
JOBS.append(("im1", "done", "sprite2d", "Planche", "/out/im1.png", None))
JOBS.append(("px1", "done", "montage_proxy", "proxy", "/out/px1.mp4", None))
JOBS.append(("nu1", "done", None, "provider nul", "/out/nu1.mp4", None))
JOBS.append(("np1", "done", "heygen", "sans artefact", None, None))
with sqlite3.connect(DB) as _cx:
    for k, (jid, st, prov, title, vp, fvp) in enumerate(JOBS):
        _cx.execute("INSERT INTO jobs (id, status, progress, title, image_filename, provider, "
                    "video_path, final_video_path, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (jid, st, 100, title, "x.png", prov, vp, fvp,
                     (_T0 + _dt.timedelta(seconds=k)).isoformat(sep=" ")))
    _cx.commit()
NB_ATTENDU = len(JOBS) - 1  # le proxy reste exclu

# ---- la regle vidéo, LUE une fois, jamais recopiee ----
rr = c.get("/api/montage/media-rules"); REGLE = J(rr)
EXTS = [str(e).lower() for e in (REGLE.get("video_exts") or []) if isinstance(e, str)]
check("eb_media_rules_repond_200_avec_des_extensions",
      rr.status_code == 200 and len(EXTS) >= 1 and all(e.startswith(".") for e in EXTS), (rr.status_code, REGLE))
check("eb_media_rules_ne_porte_pas_de_providers_mesure_du_23_09",
      rr.status_code == 200 and "video_exts" in REGLE and "video_providers" not in REGLE
      and "providers" not in REGLE, list(REGLE.keys()))

def _ext(fp):
    nm = str(fp or "").replace("\\", "/").split("/")[-1]
    k = nm.rfind(".")
    return nm[k:].lower() if k > 0 else ""

def _est_video(j):
    """La regle de /media-rules appliquee au chemin (final_video_path sinon video_path)."""
    return _ext(j.get("final_video_path") or j.get("video_path")) in EXTS


print("\n[1] E-2 backend : GET /api/jobs pagine (offset), filtre providers/q, juge video unique")
r_tous = c.get("/api/jobs", params={"limit": 50}); j_tous = L(r_tous)
ids_tous = [j.get("job_id") for j in (j_tous or [])]
check("eb_jobs_limit_50_rend_tous_les_jobs_sauf_le_proxy",
      r_tous.status_code == 200 and j_tous is not None and len(j_tous) == NB_ATTENDU
      and "px1" not in ids_tous and "sd0" in ids_tous, (r_tous.status_code, ids_tous))
check("eb_jobs_tri_created_at_desc",
      j_tous is not None and len(ids_tous) == NB_ATTENDU and ids_tous[0] == "np1" and ids_tous[-1] == "sd0", ids_tous)
# etat vide : l ancien /jobs ignore offset (rend la meme premiere page)
r0 = c.get("/api/jobs", params={"limit": 3}); j0 = L(r0) or []
r1 = c.get("/api/jobs", params={"limit": 3, "offset": 3}); j1 = L(r1) or []
ids0 = [j.get("job_id") for j in j0]; ids1 = [j.get("job_id") for j in j1]
check("eb_jobs_offset_rend_la_page_suivante_sans_recouvrement",
      r0.status_code == 200 and r1.status_code == 200 and len(ids0) == 3 and len(ids1) == 3
      and not set(ids0) & set(ids1) and ids0 + ids1 == ids_tous[:6], (ids0, ids1))
r_fin = c.get("/api/jobs", params={"limit": 50, "offset": NB_ATTENDU - 2}); j_fin = L(r_fin)
check("eb_jobs_offset_pres_de_la_fin_rend_le_reste",
      r_fin.status_code == 200 and j_fin is not None
      and [j.get("job_id") for j in j_fin] == ids_tous[-2:], j_fin and [j.get("job_id") for j in j_fin])
rp = c.get("/api/jobs", params={"limit": 50, "providers": "episode,news"}); jp = L(rp)
check("eb_jobs_providers_ne_rend_que_ces_providers",
      rp.status_code == 200 and jp is not None and len(jp) == 2
      and all(j.get("provider") in ("episode", "news") for j in jp), jp and [j.get("provider") for j in jp][:8])
rps = c.get("/api/jobs", params={"limit": 50, "providers": " seedance , ,"}); jps = L(rps)
check("eb_jobs_providers_espaces_et_vides_tolere_et_provider_nul_lu_seedance",
      rps.status_code == 200 and jps is not None and len(jps) == 6
      and {j.get("job_id") for j in jps} == {"sd0", "sd1", "sd2", "sd3", "sd4", "nu1"},
      jps and [j.get("job_id") for j in jps])
rq = c.get("/api/jobs", params={"limit": 50, "q": "preuve-eb"}); jq = L(rq)
check("eb_jobs_q_filtre_par_titre_insensible_a_la_casse",
      rq.status_code == 200 and jq is not None and len(jq) == 1
      and "preuve-eb" in (jq[0].get("title") or "").lower() and jq[0].get("job_id") == "pv1",
      jq and [j.get("job_id") for j in jq])
rq0 = c.get("/api/jobs", params={"limit": 50, "q": "RIEN-NE-PORTE-CE-TITRE"}); jq0 = L(rq0)
check("eb_jobs_q_sans_correspondance_rend_une_liste_vide_pas_une_erreur",
      rq0.status_code == 200 and jq0 == [] and jq is not None and len(jq) == 1, (rq0.status_code, jq0))
rv = c.get("/api/jobs", params={"limit": 50, "video": 1}); jv = L(rv)
non_videos_dans_tous = [j.get("job_id") for j in (j_tous or []) if not _est_video(j)]
check("eb_jobs_video_1_ne_rend_que_des_jobs_video_selon_media_rules",
      rv.status_code == 200 and jv is not None and len(jv) >= 1 and all(_est_video(j) for j in jv)
      and len(non_videos_dans_tous) >= 1
      and not {j.get("job_id") for j in jv} & set(non_videos_dans_tous),
      (jv and [j.get("job_id") for j in jv], non_videos_dans_tous))
check("eb_jobs_video_1_ecarte_le_png_et_le_sans_artefact_et_garde_l_extension_en_capitales",
      jv is not None and {"im1", "np1"} <= set(ids_tous)
      and {"im1", "np1"} & {j.get("job_id") for j in jv} == set()
      and "ep1" in {j.get("job_id") for j in jv}
      and len(jv) == len([j for j in (j_tous or []) if _est_video(j)]),
      jv and [j.get("job_id") for j in jv])
rvp = c.get("/api/jobs", params={"limit": 2, "offset": 1, "video": 1, "providers": "seedance",
                                 "q": "seedance"}); jvp = L(rvp)
check("eb_jobs_les_filtres_se_combinent_avec_la_pagination",
      rvp.status_code == 200 and jvp is not None
      and [j.get("job_id") for j in jvp] == ["sd3", "sd2"], jvp and [j.get("job_id") for j in jvp])
rb = c.get("/api/jobs", params={"limit": 9999, "offset": -5}); jb = L(rb)
check("eb_jobs_offset_negatif_ou_limit_hors_bornes_sont_ramenes",
      rb.status_code == 200 and jb is not None and len(jb) == NB_ATTENDU, (rb.status_code, jb and len(jb)))
rb0 = c.get("/api/jobs", params={"limit": 0}); jb0 = L(rb0)
check("eb_jobs_limit_zero_est_ramene_a_un",
      rb0.status_code == 200 and jb0 is not None and len(jb0) == 1, (rb0.status_code, jb0 and len(jb0)))
r_out = c.get("/api/jobs", params={"limit": 50, "offset": 500}); j_out = L(r_out)
check("eb_jobs_offset_au_dela_rend_une_liste_vide_200",
      r_out.status_code == 200 and j_out == [] and NB_ATTENDU >= 1, (r_out.status_code, j_out))


print("\n[2] E-2 backend : espion — video=1 lit la MEME regle que /media-rules (un seul juge)")
import app.services.montage_service as MS
import app.services.pipeline as PL
check("eb_media_rules_est_une_fonction_pure_du_service",
      callable(getattr(MS, "media_rules", None)) and isinstance(MS.media_rules(), dict)
      and [str(e).lower() for e in MS.media_rules().get("video_exts", [])] == EXTS, getattr(MS, "media_rules", None))
_appels = []
# etat vide : sans `media_rules`, l'espion ne se pose pas et les trois lignes suivantes rougissent
_vrai = getattr(MS, "media_rules", None) or (lambda: {})
def _espion():
    d = _vrai(); _appels.append(dict(d)); return d
MS.media_rules = _espion
try:
    rr2 = c.get("/api/montage/media-rules"); d2 = J(rr2)
    n_route = len(_appels)
    rv2 = c.get("/api/jobs", params={"limit": 50, "video": 1}); jv2 = L(rv2)
    n_video = len(_appels) - n_route
    rn2 = c.get("/api/jobs", params={"limit": 50}); jn2 = L(rn2)
    n_sans = len(_appels) - n_route - n_video
finally:
    MS.media_rules = _vrai
check("eb_la_route_media_rules_passe_par_media_rules",
      rr2.status_code == 200 and n_route == 1 and d2 == _appels[0], (rr2.status_code, n_route))
check("eb_video_1_passe_par_media_rules_et_limit_seul_non",
      rv2.status_code == 200 and n_video == 1 and rn2.status_code == 200 and n_sans == 0
      and jv2 is not None and jn2 is not None and len(jn2) > len(jv2), (n_video, n_sans))
# espion sur la regle : une extension inventee traverse jusqu a la requete
MS.media_rules = lambda: {"video_exts": [".png"]}
try:
    rv3 = c.get("/api/jobs", params={"limit": 50, "video": 1}); jv3 = L(rv3)
finally:
    MS.media_rules = _vrai
check("eb_la_regle_servie_est_celle_appliquee_par_video_1",
      rv3.status_code == 200 and jv3 is not None and [j.get("job_id") for j in jv3] == ["im1"]
      and jv is not None and "im1" not in {j.get("job_id") for j in jv}, jv3 and [j.get("job_id") for j in jv3])
import inspect
_sig = inspect.signature(PL.Pipeline.list_jobs)
check("eb_pipeline_list_jobs_porte_les_cinq_parametres",
      list(_sig.parameters) == ["limit", "offset", "providers", "q", "video_exts"], list(_sig.parameters))

c.__exit__(None, None, None)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
