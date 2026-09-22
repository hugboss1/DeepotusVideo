# -*- coding: utf-8 -*-
"""Lot E-A — E-1 (22/09/2026) : UN MONTAGE NEUF EST VIDE, ET LE RESTE.

Le drapeau `vide` est OPT-IN STRICT (`body.get("vide") is True`) : pose par
`POST /projects {vide:true}`, garde par `_save_record` quand le client le
renvoie a l'autosave, lu par `GET /project` pour NE PAS reconstruire la
timeline depuis la Bibliotheque, et par `open` pour ne pas rendre 409. SANS
lui, tout est l'historique octet pour octet — les deux 400 « Aucune timeline
a enregistrer » epingles par test_montage_projets.py restent.

En-tete recopie de test_montage_projets.py (env AVANT `import app`, `check`,
`J`). Banc par la ROUTE, fastapi.testclient, dossier de donnees NEUF.
Run : & $PY tests/test_montage_ea.py   (depuis backend/)

PROTOCOLE : toute reponse passe par `J()` (jamais `.json()` nu), tout acces
est un `.get`. Une negation ne vaut que si son operande a vecu : chaque
ligne qui affirme une absence exige d'abord le fait mesure a cote.
"""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzea_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
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
    """Corps JSON, ou {} — ce banc doit ROUGIR, pas mourir."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


def tracks_of(d):
    return [t.get("id") for t in (d.get("tracks") or []) if isinstance(t, dict)]


# `raise_server_exceptions=False` : une exception non rattrapee dans une route
# devient un 500 que `J()` rend {} — les assertions decident, le banc vit.
c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

print("\n[1] E-1 un montage NEUF et vide : cree, garde, ouvert, jamais rempli par la Bibliotheque")
r = c.post("/api/montage/projects", json={"name": "sans rien"}); d = J(r)
check("e1_sans_vide_le_400_historique_est_garde", r.status_code == 400,
      f"{r.status_code} {r.text[:100]}")
TR5 = [{"id": "t1", "kind": "title"}, {"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
       {"id": "a1", "kind": "audio", "bus": "dialogue"}, {"id": "s1", "kind": "subs"}]
r = c.post("/api/montage/projects", json={"name": "neuf", "vide": True, "tracks": TR5}); d = J(r)
check("e1_vide_true_cree_un_projet_200",
      r.status_code == 200 and d.get("ok") is True and str(d.get("id", "")).startswith("m_"),
      (r.status_code, d))
pid = str(d.get("id") or "")
check("e1_la_meta_dit_vide_et_zero_clip", d.get("vide") is True and d.get("clips") == 0, d)
r = c.get("/api/montage/projects"); L = J(r)
lst = L.get("_liste") if isinstance(L.get("_liste"), list) else (L.get("projects") or [])
check("e1_la_liste_porte_le_drapeau",
      bool(pid) and any(isinstance(p, dict) and p.get("id") == pid and p.get("vide") is True
                        for p in lst), str(lst)[:200])
r = c.get("/api/montage/project"); d = J(r)
check("e1_get_project_rend_le_vide_sans_le_remplir",
      r.status_code == 200 and d.get("ok") is True and d.get("has_assets") is True
      and d.get("saved") is True and d.get("vide") is True and d.get("clips") == []
      and bool(pid) and d.get("project_id") == pid, str(d)[:300])
check("e1_les_pistes_et_la_duree_sont_celles_posees",
      tracks_of(d) == ["t1", "v2", "v1", "a1", "s1"]
      and isinstance(d.get("duration"), (int, float)) and d["duration"] >= 10,
      (d.get("tracks"), d.get("duration")))
r2 = c.post("/api/montage/projects", json={"name": "neuf2", "vide": True}); d2 = J(r2)
pid2 = str(d2.get("id") or "")
r3 = c.post("/api/montage/projects/%s/open" % pid2); d3 = J(c.get("/api/montage/project"))
check("e1_vide_sans_tracks_prend_les_sept_pistes_par_defaut_du_client",
      r2.status_code == 200 and r3.status_code == 200
      and tracks_of(d3) == ["t1", "v2", "v1", "a1", "a2", "a3", "s1"],
      (r2.status_code, r3.status_code, d3.get("tracks")))
r = c.post("/api/montage/projects/%s/open" % pid)
check("e1_ouvrir_un_projet_vide_200_pas_409", r.status_code == 200,
      f"{r.status_code} {r.text[:120]}")
# Revue E-1 : la branche `vide` ecrivait SANS plafond (mesure : 10 449 112
# octets sur le disque avec 10 000 pistes d'1 ko). Le plafond vit dans
# _save_record, donc ici aussi.
r = c.post("/api/montage/projects",
           json={"name": "obese", "vide": True,
                 "tracks": [{"id": "x", "kind": "video", "pad": "k" * 1000} for _ in range(10_000)]})
check("e1_vide_de_dix_mo_est_refuse_400_deux_mo", r.status_code == 400 and "2 Mo" in r.text,
      f"{r.status_code} {r.text[:120]}")
# `_save_record` ne verifie PAS les sources (mesure : il stocke les clips
# tels quels) ; c'est GET /project qui ELAGUE un clip dont la source a
# disparu (`x.mp3` ici). Le drapeau doit survivre a cet elagage.
CLIP_A1 = [{"id": "a", "tr": "a1", "start": 0, "end": 3, "src": {"audio": "x.mp3"}}]
r = c.post("/api/montage/save", json={"name": "neuf", "vide": True, "clips": CLIP_A1})
d = J(c.get("/api/montage/project"))
check("e1_autosave_garde_vide_quand_le_client_le_renvoie",
      r.status_code == 200 and d.get("saved") is True and d.get("vide") is True, str(d)[:200])
r = c.post("/api/montage/save", json={"name": "neuf", "clips": CLIP_A1})
d = J(c.get("/api/montage/project"))
# MESURE (le `return` du repli Bibliotheque, `"saved": False`) : il rend {ok, has_assets:<bool>,
# saved:False, ...} — sur des donnees vierges, has_assets est faux.
check("e1_sans_vide_et_sans_v1_l_ancien_chemin_reconstruit_depuis_la_bibliotheque",
      r.status_code == 200 and d.get("ok") is True and d.get("saved") is False
      and d.get("has_assets") is False and "vide" not in d, str(d)[:200])


print("\n[2] E-4 publier = un brouillon Scheduler cree par le backend, a la demande")
# Une source REELLE : mp4 testsrc2 de 2 s via ffmpeg_bin (SKIP dit sans
# ffmpeg — les lignes qui exigent JID se marquent SKIP, jamais vertes a vide),
# envoyee par POST /api/videos/upload -> job `done` porteur d'un .mp4.
import datetime as _dt, json, subprocess, pathlib
_SRC = str(pathlib.Path(TMP) / "reel.mp4")
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    subprocess.run([_fb(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=s=64x64:r=10:d=2", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", _SRC], check=False, capture_output=True, timeout=60)
except Exception as _e:
    print("  (ffmpeg injoignable : %s)" % _e)
JID = ""
if os.path.exists(_SRC) and os.path.getsize(_SRC) > 0:
    with open(_SRC, "rb") as _fh:
        d = J(c.post("/api/videos/upload", files={"file": ("reel.mp4", _fh, "video/mp4")}))
    JID = str(d.get("job_id") or "")
skip = 0
NPOSTS = 0
def check_jid(label, cond, detail=""):
    global skip
    if not JID: skip += 1; print(f"  SKIP  {label} (pas de source reelle)")
    else: check(label, cond, detail)
r = c.post("/api/montage/publish", json={"job_id": "nope"})
check("e4_job_inconnu_404", r.status_code == 404, r.status_code)
r = c.post("/api/montage/publish", json={})
check("e4_sans_job_id_400", r.status_code == 400, r.status_code)
r = c.post("/api/montage/publish", json={"job_id": JID, "channels": ["x", "zzz", "youtube"],
                                         "caption": "salut", "project_id": "m_abc12345"}); d = J(r)
P = d.get("post") if isinstance(d.get("post"), dict) else {}
check_jid("e4_200_rend_le_post_avec_id_et_job",
          r.status_code == 200 and d.get("ok") is True and bool(P) and P.get("job_id") == JID
          and isinstance(P.get("id"), str) and P.get("id") != "", str(d)[:200])
# MESURE : _post_to_dict rend `channels` en LISTE, `brief` en dict decode, run_at suffixe « Z ».
check_jid("e4_les_canaux_sont_filtres_par_la_liste_blanche", P.get("channels") == ["x", "youtube"],
          P.get("channels"))
check_jid("e4_statut_brouillon_mode_assiste", P.get("status") == "draft" and P.get("mode") == "assisted",
          (P.get("status"), P.get("mode")))
def _parse(s):
    try: return _dt.datetime.fromisoformat(str(s).replace("Z", ""))
    except Exception: return None
ra = _parse(P.get("run_at"))
check_jid("e4_run_at_par_defaut_est_a_deux_heures",
          ra is not None and 110 * 60 <= (ra - _dt.datetime.utcnow()).total_seconds() <= 130 * 60,
          P.get("run_at"))
_b = P.get("brief"); _bd = _b if isinstance(_b, dict) else {}
check_jid("e4_project_id_voyage_dans_brief", _bd.get("project_id") == "m_abc12345", _b)
check_jid("e4_la_legende_est_celle_envoyee_le_titre_celui_du_job",
          P.get("caption") == "salut" and P.get("title") == "reel", (P.get("caption"), P.get("title")))
r = c.post("/api/montage/publish", json={"job_id": JID, "channels": [], "run_at": "2026-12-01T09:00:00"})
d = J(r); P2 = d.get("post") if isinstance(d.get("post"), dict) else {}
check_jid("e4_canaux_vides_retombent_sur_x_et_run_at_explicite_est_garde",
          r.status_code == 200 and P2.get("channels") == ["x"]
          and str(P2.get("run_at", "")).startswith("2026-12-01T09:00") and P2.get("brief") is None
          and P2.get("caption") == "reel", str(d)[:200])
check_jid("e4_run_at_invalide_400",
          c.post("/api/montage/publish", json={"job_id": JID, "run_at": "hier"}).status_code == 400)
check_jid("e4_run_at_nombre_400",
          c.post("/api/montage/publish", json={"job_id": JID, "run_at": 12345}).status_code == 400)
# Revue E-4 : un fuseau fourni est RAMENE en UTC avant stockage naif (le
# Scheduler le jetait : +02:00 stocke 09:00, post 2 h en retard).
r = c.post("/api/montage/publish", json={"job_id": JID, "run_at": "2026-12-01T09:00:00+02:00"})
d = J(r); P3 = d.get("post") if isinstance(d.get("post"), dict) else {}
check_jid("e4_run_at_avec_fuseau_est_ramene_en_utc",
          r.status_code == 200 and str(P3.get("run_at", "")).startswith("2026-12-01T07:00"), P3.get("run_at"))
r = c.post("/api/montage/publish", json={"job_id": JID, "run_at": "2026-12-01T09:00:00Z",
                                         "channels": "youtube", "title": 42, "caption": "k" * 5000})
d = J(r); P4 = d.get("post") if isinstance(d.get("post"), dict) else {}
check_jid("e4_run_at_z_inchange_canaux_chaine_x_titre_non_chaine_job_legende_bornee_4000",
          r.status_code == 200 and str(P4.get("run_at", "")).startswith("2026-12-01T09:00")
          and P4.get("channels") == ["x"] and P4.get("title") == "reel"
          and len(P4.get("caption") or "") == 4000,
          (P4.get("run_at"), P4.get("channels"), P4.get("title"), len(P4.get("caption") or "")))
NPOSTS = 4
r = c.get("/api/schedule"); L = J(r); lst = L.get("_liste") if isinstance(L.get("_liste"), list) else []
check_jid("e4_deux_brouillons_existent_dans_le_scheduler",
          r.status_code == 200 and len(lst) == NPOSTS and all(p.get("job_id") == JID for p in lst), len(lst))
# 409 : un job `queued` fabrique en base DANS la boucle de l'app (portal) — le
# moteur aiosqlite est lie a cette boucle, un asyncio.run() a part ne le verrait pas.
from app.services.storage import JobRecord as _JR, async_session_factory as _ASF
async def _mk_queued():
    async with _ASF() as s:
        s.add(_JR(id="q_en_cours", status="queued", image_filename="x.png", title="encours"))
        await s.commit()
c.portal.call(_mk_queued)
r = c.post("/api/montage/publish", json={"job_id": "q_en_cours"})
check("e4_job_non_termine_409", r.status_code == 409, f"{r.status_code} {r.text[:100]}")
r = c.get("/api/schedule"); L = J(r); lst = L.get("_liste") if isinstance(L.get("_liste"), list) else []
check("e4_le_409_n_a_rien_cree", r.status_code == 200 and len(lst) == (NPOSTS if JID else 0), len(lst))
# Revue E-4 : un job `done` dont le .mp4 a DISPARU (suffixe bon, fichier absent) -> 409.
async def _mk_disparu():
    async with _ASF() as s:
        s.add(_JR(id="d_disparu", status="done", image_filename="x.png", title="disparu",
                  final_video_path=str(pathlib.Path(TMP) / "disparu.mp4")))
        await s.commit()
c.portal.call(_mk_disparu)
r = c.post("/api/montage/publish", json={"job_id": "d_disparu"})
check("e4_fichier_disparu_409", r.status_code == 409, f"{r.status_code} {r.text[:100]}")
r = c.get("/api/schedule"); L = J(r); lst = L.get("_liste") if isinstance(L.get("_liste"), list) else []
check("e4_le_409_fichier_disparu_n_a_rien_cree", r.status_code == 200 and len(lst) == (NPOSTS if JID else 0), len(lst))

c.__exit__(None, None, None)
print(f"\n=== {ok} passed, {fail} failed, {skip} skipped ===")
sys.exit(1 if fail else 0)
