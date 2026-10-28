# -*- coding: utf-8 -*-
"""t365 (28/10/2026) — A4 leads locaux : l'outil `entreprises_carte` rend une carte « collecte » Google Maps (catégorie,
ville, N ≤ 100, but leads, plafond 1 $), sans run ; acceptée, la route lance le run, puis rend des CIBLES {nom, site,
note, categorie, ville} (ni téléphone ni avis) et DÉPOSE le site public de chaque cible : `prospects_chercher(source=
"entreprise", url=site)` l'accepte (lecteur t354), jamais un site local ou javascript:. Aucune fiche écrite. Faux run.
Run (depuis backend/) : & $PY tests/test_apify_leads.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzleads_"))
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
from app.services import apify as AP, prospects as P                                                                  # noqa: E402
from app.services.storage import init_db                                                                              # noqa: E402

c = TestClient(app)
RUNS = []
ITEMS = [
    {"title": "Studio Lune", "website": "https://studio-lune.fr/", "totalScore": 4.7, "categoryName": "Studio vidéo",
     "city": "Lyon", "phone": "+33 4 00 00 00 00", "reviews": [{"text": "x"}]},
    {"title": "Local", "website": "http://127.0.0.1:8765/api/keys", "totalScore": 4.0, "categoryName": "x"},
    {"title": "Sans site", "totalScore": 3.1, "categoryName": "Studio vidéo"},
    {"title": "JS", "website": "javascript:alert(1)"},
]


async def faux_devis(cle, n, entree=None):
    return round(0.004 * n, 4)


async def faux_lancer(cle, entree, n, plafond=None):
    RUNS.append((cle, entree, n))
    return {"items": ITEMS, "cout_usd": 0.016, "statut": "SUCCEEDED", "partiel": False, "run_id": "R1", "devis_usd": 0.016}


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
check("1.0 dans la boîte « prospects » de l'agent Campagnes", "entreprises_carte" in AB.BOITES["prospects"]["outils"])
r = asyncio.run(ao.executer("entreprises_carte", {"categorie": "studio vidéo", "ville": "Lyon", "max": 20}, ctx))
check("1.1 sans clé Apify : refus dit, aucune carte", not r["ok"] and r["carte"] is None and "Apify" in r["resume"], r)
settings.APIFY_TOKEN = "apify_api_X"
r = asyncio.run(ao.executer("entreprises_carte", {"categorie": "studio vidéo", "ville": "Lyon", "max": 20}, ctx))
k = r["carte"] or {}
a = k.get("arguments") or {}
check("1.2 carte « collecte » google_maps, but leads, entrée = catégorie et ville, aucun run",
      r["ok"] and k.get("genre") == "collecte" and a.get("acteur") == "google_maps" and a.get("but") == "leads"
      and a.get("entree") == {"searchStringsArray": ["studio vidéo"], "locationQuery": "Lyon", "language": "fr"}
      and a.get("max") == 20 and not RUNS, k)
r2 = asyncio.run(ao.executer("entreprises_carte", {"categorie": "studio", "ville": "Lyon", "max": 500}, ctx))
check("1.3 N borné à 100", (r2["carte"] or {}).get("arguments", {}).get("max") == 100, r2)
r3 = asyncio.run(ao.executer("entreprises_carte", {"categorie": "", "ville": "Lyon"}, ctx))
check("1.4 catégorie vide : refus", not r3["ok"], r3)

print("[2] acceptée")
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
r = c.post(f"/api/agent/campagnes/{cid}/carte/0", json={"decision": "acceptee"})
check("2.1 un run", r.status_code == 200 and len(RUNS) == 1, r.text[:300])
fa = [m for m in r.json()["messages"] if m["role"] == "fait"][-1]["blocs"][0]["arguments"]
ci = fa.get("cibles") or []
check("2.2 cibles : nom, site, note, catégorie, ville ; ni téléphone ni avis",
      ci and ci[0] == {"nom": "Studio Lune", "site": "https://studio-lune.fr/", "note": 4.7, "categorie": "Studio vidéo",
                       "ville": "Lyon"} and "phone" not in json.dumps(fa) and "reviews" not in json.dumps(fa), ci)
check("2.3 une cible sans site reste (site vide)", any(x["nom"] == "Sans site" and x["site"] == "" for x in ci), ci)
check("2.4 site local ou javascript: jamais rendu", not any("127.0.0.1" in x["site"] or "javascript" in x["site"] for x in ci), ci)
l = asyncio.run(st.lire(cid))
dep = ao._urls_deposees(l, cid)
check("2.5 seul le site public est déposé", dep == {"https://studio-lune.fr/"}, dep)
check("2.6 aucune fiche écrite", P.lister(A) == [])

print("[3] le lecteur t354 accepte le site déposé")
async def faux_lire_site(url):
    return [(url, "Contact : bonjour@studio-lune.fr")]
ao._lire_site = faux_lire_site
r = asyncio.run(ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://studio-lune.fr/"}, ctx))
check("3.1 prospects_chercher lit le site déposé (preuve encadrée)", r["ok"] and "PREUVE" in json.dumps(r, ensure_ascii=False), r)
r = asyncio.run(ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://autre-site.fr/"}, ctx))
check("3.2 un site non déposé reste refusé", not r["ok"], r)

print("[4] relecture")
dep = ao._dossier_conversation(asyncio.run(st.lire(cid))) / "depots"
brut_depot = "".join(f.read_text("utf-8") for f in dep.glob("apify-*.txt"))
check("4.1 C1 : le dépôt garde les cibles, ni téléphone ni avis", brut_depot and "+33" not in brut_depot
      and "reviews" not in brut_depot and "Studio Lune" in brut_depot, brut_depot[:200])

settings.APIFY_TOKEN = ""
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
