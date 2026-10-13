# -*- coding: utf-8 -*-
"""t204 (Espaces de marque E4, 13/10/2026) — le Planificateur par ESPACE et par COMPTE de diffusion.
Ce que ce banc garde :
  - migration : `espace_id` et `comptes` ajoutés à scheduled_posts ; un post d'avant (espace vide) est de Deepotus ;
  - GET /schedule : les posts de l'espace courant (« * » = tous) ; un post créé prend l'espace de la requête ;
  - GARDE : un compte d'un autre espace -> 409 (création ET modification, rien d'écrit), inconnu -> 404 ; les canaux
    suivent les comptes ; changer les comptes d'un post validé le dévalide ;
  - publication : un post à comptes publie compte par compte (faux tweepy : CHAQUE compte ses jetons), remote_ids
    « x:<id> » (deux comptes X ne se marchent pas dessus), le rejeu ne republie rien ; quota PAR compte ; un post
    Deepotus sans comptes garde le chemin d'avant (clés plates, clé « x ») ; un post d'un AUTRE espace sans comptes
    n'est JAMAIS publié par les clés de Deepotus ; un compte supprimé depuis est dit, pas publié ;
  - recyclage et fil : même espace, mêmes comptes (la suite d'un fil part du compte X de la tête) ;
  - métriques : une publication par compte est relue avec les identifiants de CE compte.
Aucun réseau, rien de payé, data-dir isolé. Témoin : la base (1dd238a3) n'a pas la colonne espace_id.
Run (depuis backend/) : & $PY tests/test_espaces_scheduler.py"""
import asyncio, json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzesch_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
          "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "1dd238a3:backend/app/services/storage.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas la colonne espace_id", r0.returncode == 0 and b'("espace_id"' not in r0.stdout)

from app.config import settings                                     # noqa: E402
from app.services import comptes as CP, espaces as ES, marketing as MK, quota as Q, metrics_service as MS  # noqa: E402
for k, v in {"X_API_KEY": "plat-k", "X_API_SECRET": "plat-s", "X_ACCESS_TOKEN": "plat-t", "X_ACCESS_SECRET": "plat-ts"}.items():
    setattr(settings, k, v)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
c.__enter__()                                                       # lifespan : init_db (create_all + auto-migration)

print("[M] migration et espace des posts")
cols = {r[1] for r in sqlite3.connect(_tmp / "t.db").execute("PRAGMA table_info(scheduled_posts)")}
check("M1 colonnes espace_id et comptes présentes", {"espace_id", "comptes"} <= cols, str(sorted(cols))[:200])
ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]
def X(cid_secrets):
    return {"X_API_KEY": cid_secrets + "-k", "X_API_SECRET": cid_secrets + "-s", "X_ACCESS_TOKEN": cid_secrets + "-t", "X_ACCESS_SECRET": cid_secrets + "-ts"}
x1 = CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "Rippled X", "valeurs": X("r1")})["id"]
x2 = CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "Rippled X dev", "valeurs": X("r2")})["id"]
xd = CP.creer({"espace_id": "deepotus", "plateforme": "x", "libelle": "Deepotus X jeu", "valeurs": X("d1")})["id"]
QUAND = "2026-11-02T09:00:00Z"
pd = c.post("/api/schedule", json={"title": "deep", "caption": "c", "channels": ["x"], "run_at": QUAND}).json()
check("M2 un post créé prend l'espace de la requête (Deepotus actif)", pd["espace_id"] == "deepotus" and pd["comptes"] == [])
con = sqlite3.connect(_tmp / "t.db")
con.execute("INSERT INTO scheduled_posts (id,title,caption,channels,run_at,status,mode,created_at) VALUES "
            "('ancien','ancien','c','x','2026-11-03 09:00:00','draft','assisted','2026-01-01 00:00:00')")
con.commit(); con.close()
ids = {p["id"]: p for p in c.get("/api/schedule").json()}
check("M3 un post d'avant les espaces (vide) est rendu comme Deepotus", ids.get("ancien", {}).get("espace_id") == "deepotus" and pd["id"] in ids)
c.post(f"/api/espaces/{rip}/activate")
pr = c.post("/api/schedule", json={"title": "rip", "caption": "c", "channels": ["x"], "run_at": QUAND, "comptes": [x1], "source_image": "demo.png"}).json()
vue_rip = {p["id"] for p in c.get("/api/schedule").json()}
check("M4 Rippled actif : GET /schedule ne montre QUE ses posts", vue_rip == {pr["id"]}, str(vue_rip))
check("M5 « * » montre tout", {pd["id"], "ancien", pr["id"]} <= {p["id"] for p in c.get("/api/schedule?espace=*").json()})
check("M6 ?espace=deepotus : Deepotus et l'ancien", {p["id"] for p in c.get("/api/schedule?espace=deepotus").json()} == {pd["id"], "ancien"})

print("\n[G] la garde")
check("G1 créé avec ses comptes : canaux suivent, espace Rippled", pr["espace_id"] == rip and pr["comptes"] == [x1] and pr["channels"] == ["x"])
g2 = c.post("/api/schedule", json={"title": "z", "channels": ["x"], "run_at": QUAND, "comptes": [xd]})
check("G2 un compte de Deepotus sur un post Rippled -> 409", g2.status_code == 409, g2.text[:200])
check("G3 le compte historique de Deepotus aussi -> 409",
      c.post("/api/schedule", json={"title": "z", "channels": ["x"], "run_at": QUAND, "comptes": ["historique-x"]}).status_code == 409)
check("G4 compte inconnu -> 404", c.post("/api/schedule", json={"title": "z", "run_at": QUAND, "comptes": ["cdeadbeef"]}).status_code == 404)
avant = c.get("/api/schedule?espace=*").json()
check("G5 aucun post créé par les refus", len(avant) == 3)
vl = c.post("/api/schedule/validate", json={"from": "2026-11-01T00:00:00Z", "to": "2026-11-30T00:00:00Z"}).json()
check("G5b le post Rippled (avec média) est bien VALIDÉ avant la modification", pr["id"] in vl.get("validated", []), str(vl))
p5 = c.patch(f"/api/schedule/{pr['id']}", json={"comptes": [x1, xd]})
check("G6 PATCH avec un compte d'un autre espace -> 409, post inchangé",
      p5.status_code == 409 and {p["id"]: p for p in c.get("/api/schedule").json()}[pr["id"]]["comptes"] == [x1], p5.text[:200])
p6 = c.patch(f"/api/schedule/{pr['id']}", json={"comptes": [x1, x2]}).json()
check("G7 PATCH deux comptes X de l'espace : posés, canaux = x", p6["comptes"] == [x1, x2] and p6["channels"] == ["x"])
check("G8 changer les comptes d'un post validé le dévalide", p6["validated_at"] is None and p6["status"] == "draft", str(p6.get("validated_at")))

print("\n[P] publier compte par compte")
vu = []
class FauxClient:
    def __init__(self, **kw): vu.append(kw["access_token"])
    def create_tweet(self, **kw): return types.SimpleNamespace(data={"id": f"t{len(vu)}"})
import tweepy                                                        # noqa: E402
tweepy.Client = FauxClient
r1 = asyncio.run(MK.fire_post(pr["id"]))
post = {p["id"]: p for p in c.get("/api/schedule?espace=*").json()}[pr["id"]]
check("P1 deux comptes X : deux tweets, CHACUN ses jetons", r1["ok"] and vu == ["r1-t", "r2-t"], str(vu))
check("P2 remote_ids par compte « x:<id> »", post["remote_ids"] == {f"x:{x1}": "t1", f"x:{x2}": "t2"}, str(post["remote_ids"]))
qj = json.loads((_tmp / "scheduler" / "quota.json").read_text("utf-8"))
check("P3 quota PAR compte (x@<id>), rien sur le compteur plat « x »", f"x@{x1}" in qj and f"x@{x2}" in qj and "x" not in qj, str(list(qj)))
c.patch(f"/api/schedule/{pr['id']}", json={"status": "ready"})
asyncio.run(MK.fire_post(pr["id"]))
check("P4 rejeu : rien n'est republié", vu == ["r1-t", "r2-t"], str(vu))
r5 = asyncio.run(MK.fire_post(pd["id"]))
pdv = {p["id"]: p for p in c.get("/api/schedule?espace=*").json()}[pd["id"]]
check("P5 post Deepotus sans comptes : chemin d'avant (clés plates, clé « x », compteur « x »)",
      r5["ok"] and vu[-1] == "plat-t" and pdv["remote_ids"] == {"x": "t3"}
      and json.loads((_tmp / "scheduler" / "quota.json").read_text("utf-8")).get("x"), str(pdv["remote_ids"]))
pn = c.post("/api/schedule", json={"title": "rip sans comptes", "channels": ["x"], "run_at": QUAND}).json()
n_avant = len(vu)
r6 = asyncio.run(MK.fire_post(pn["id"]))
pnv = {p["id"]: p for p in c.get("/api/schedule").json()}[pn["id"]]
check("P6 un post Rippled SANS comptes n'est jamais publié par les clés de Deepotus (dit, reste prêt)",
      not r6["ok"] and len(vu) == n_avant and pnv["status"] == "ready" and "aucun compte" in (pnv["error"] or ""), str(r6))
pz = c.post("/api/schedule", json={"title": "rip", "channels": ["x"], "run_at": QUAND, "comptes": [x2]}).json()
CP.supprimer(x2)
r7 = asyncio.run(MK.fire_post(pz["id"]))
check("P7 un compte supprimé depuis : dit, rien de publié", not r7["ok"] and len(vu) == n_avant and "inconnu" in " ".join(r7.get("pending", [])), str(r7))

print("\n[R] recyclage et fil")
x3 = CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "Rippled X 3", "valeurs": X("r3")})["id"]
tg = CP.creer({"espace_id": rip, "plateforme": "telegram", "valeurs": {"TELEGRAM_BOT_TOKEN": "9:z", "TELEGRAM_CHAT_ID": "-1"}})["id"]
tete = c.post("/api/schedule", json={"title": "tête", "run_at": QUAND, "comptes": [tg, x3]}).json()
check("R1 canaux = ceux des comptes, dans l'ordre", tete["channels"] == ["telegram", "x"], str(tete["channels"]))
rc = c.post("/api/schedule/recycle", json={"source_id": tete["id"], "run_at": QUAND}).json()
check("R2 recyclé : même espace, mêmes comptes", rc.get("espace_id") == rip and rc.get("comptes") == [tg, x3], str(rc)[:200])
su = c.post(f"/api/schedule/{tete['id']}/thread", json={"caption": "suite"}).json()
check("R3 suite de fil : même espace, le SEUL compte X de la tête", su.get("espace_id") == rip and su.get("comptes") == [x3], str(su)[:200])

print("\n[K] métriques par compte")
vus_m = []
async def faux_fetch(rids):
    vus_m.append((CP.cred.X_ACCESS_TOKEN, list(rids)))
    return {rid: {"views": 5, "likes": 1, "comments": 0, "shares": 0, "saves": 0} for rid in rids}
MS.FETCHERS["x"] = faux_fetch
asyncio.run(MS.refresh_all())
check("K1 la publication du compte x1 est relue avec SES jetons ; le post Deepotus avec les clés plates",
      ("r1-t", ["t1"]) in vus_m and any(t == "plat-t" and "t3" in r for t, r in vus_m), str(vus_m))
check("K2 le compte supprimé (x2) n'est pas relu (plus d'identifiants)", not any(t == "r2-t" for t, _r in vus_m))

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
