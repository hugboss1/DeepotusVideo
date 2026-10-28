# -*- coding: utf-8 -*-
"""t367 (28/10/2026) — A5 signaux de besoin Reddit. `signaux_reddit` rend une carte « collecte » Reddit (but signaux,
requêtes données, communauté facultative) ; acceptée : seuls les posts qui expriment un BESOIN (« alternative à »,
« combien coûte », « looking for », « recommend »…) sont gardés comme signaux {url, extrait ≤ 300, date} (auteur haché
gardé, jamais rendu, jamais en clair) ; `prospects_chercher(source="veille")` les rend avec la règle de réponse publique.
Jamais une fiche, jamais un DM. Faux run.
Run (depuis backend/) : & $PY tests/test_apify_signaux.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsig_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["APIFY_TOKEN"] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services import agent_boites as AB, agent_format as fmt, agent_outils as ao, agent_store as st, espaces as E   # noqa: E402
from app.services import apify as AP, apify_suite as SU, prospects as P                                               # noqa: E402
from app.services.storage import init_db                                                                              # noqa: E402

c = TestClient(app)
RUNS = []
ITEMS = [
    {"dataType": "post", "title": "Looking for an alternative to Runway for client videos",
     "body": "Credits are too pricey", "url": "https://reddit.com/r/vfx/a", "createdAt": "2026-10-20T10:00:00Z",
     "username": "dana_secret"},
    {"dataType": "post", "title": "Combien coûte un studio vidéo IA ?", "body": "", "url": "https://reddit.com/r/fr/b",
     "createdAt": "2026-10-21T10:00:00Z", "username": "eve_secret"},
    {"dataType": "post", "title": "Look at my render", "body": "Made this today", "url": "https://reddit.com/r/vfx/c",
     "username": "fred_secret"},
    {"dataType": "comment", "body": "Can anyone recommend a tool for product shots? " + "x" * 600,
     "url": "https://reddit.com/r/vfx/d", "username": "gina_secret"},
]


async def faux_devis(cle, n, entree=None):
    return 0.1


async def faux_lancer(cle, entree, n, plafond=None):
    RUNS.append((cle, entree, n))
    return {"items": ITEMS, "cout_usd": 0.04, "statut": "SUCCEEDED", "partiel": False, "run_id": "R1", "devis_usd": 0.1}


AP.devis = faux_devis
AP.lancer = faux_lancer


async def preparer():
    await init_db()
    A = E.creer({"nom": "Prospection"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    return A, cid


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)

print("[1] l'outil")
check("1.0 dans la boîte « prospects »", "signaux_reddit" in AB.BOITES["prospects"]["outils"])
settings.APIFY_TOKEN = "apify_api_X"
r = asyncio.run(ao.executer("signaux_reddit", {"requetes": ["alternative to runway", "ai video studio"],
                                                "communaute": "vfx", "max": 40}, ctx))
k = r["carte"] or {}
a = k.get("arguments") or {}
check("1.1 carte reddit, but signaux, requêtes et communauté, tri récent sur un mois, aucun run",
      r["ok"] and a.get("acteur") == "reddit" and a.get("but") == "signaux"
      and a.get("entree") == {"searches": ["alternative to runway", "ai video studio"], "searchCommunityName": "vfx",
                              "sort": "new", "time": "month"} and not RUNS, k)
check("1.2 aucune requête : refus", not asyncio.run(ao.executer("signaux_reddit", {"requetes": []}, ctx))["ok"])
check("1.3 six requêtes : refus", not asyncio.run(ao.executer("signaux_reddit", {"requetes": ["a"] * 6}, ctx))["ok"])

print("[2] acceptée")
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
r = c.post(f"/api/agent/campagnes/{cid}/carte/0", json={"decision": "acceptee"})
fa = [m for m in r.json()["messages"] if m["role"] == "fait"][-1]["blocs"][0]["arguments"]
check("2.1 le fait dit les signaux gardés (3 besoins sur 4)", r.status_code == 200 and fa.get("signaux") == 3, fa)
sig = SU.signaux_reddit(A)
check("2.2 extrait borné à 300, auteur haché, jamais en clair", sig and all(len(x["texte"]) <= 300 and x["auteur_hash"]
      and "secret" not in json.dumps(x) for x in sig), sig)
check("2.3 relancé : aucun doublon (rien d'ajouté, 3 gardés)", SU._garder_signaux(A, sig) == [] and len(SU.signaux_reddit(A)) == 3)
check("2.4 aucune fiche écrite", P.lister(A) == [])

print("[3] prospects_chercher(source=veille)")
r = asyncio.run(ao.executer("prospects_chercher", {"source": "veille"}, ctx))
s = (r.get("donnees") or {}).get("signaux") or []
check("3.1 les signaux Reddit sont rendus, sans auteur, avec la règle de réponse publique",
      r["ok"] and sum(1 for x in s if x.get("source") == "reddit") == 3 and not any("auteur" in "".join(x) for x in s)
      and "message privé" in (r.get("donnees") or {}).get("regle", ""), r)

print("[4] relecture")
dep = ao._dossier_conversation(asyncio.run(st.lire(cid))) / "depots"
brut_depot = "".join(f.read_text("utf-8") for f in dep.glob("apify-*.txt"))
check("4.1 C1 : le dépôt lisible par l'agent ne garde aucun pseudo en clair", brut_depot and "secret" not in brut_depot, brut_depot[:200])
r = asyncio.run(ao.executer("prospects_chercher", {"source": "veille"}, ctx))
s = (r.get("donnees") or {}).get("signaux") or []
check("4.2 I2 : chaque texte de signal revient ENCADRÉ comme preuve", s and all("<<<PREUVE" in str(x.get("texte")) for x in s), s[:1])

settings.APIFY_TOKEN = ""
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
