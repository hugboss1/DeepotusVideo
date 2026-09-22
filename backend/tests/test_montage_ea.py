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
      tracks_of(d) == ["t1", "v2", "v1", "a1", "s1"] and float(d.get("duration") or 0) >= 10,
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
# MESURE (`:1433`) : le repli Bibliotheque rend {ok, has_assets:<bool>,
# saved:False, ...} — sur des donnees vierges, has_assets est faux.
check("e1_sans_vide_et_sans_v1_l_ancien_chemin_reconstruit_depuis_la_bibliotheque",
      r.status_code == 200 and d.get("ok") is True and d.get("saved") is False
      and d.get("has_assets") is False and "vide" not in d, str(d)[:200])

c.__exit__(None, None, None)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
