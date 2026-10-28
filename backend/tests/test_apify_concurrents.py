# -*- coding: utf-8 -*-
"""t368 (28/10/2026) — A3 ce que font les concurrents. Périmètre : `pages` (prix/fonctions), `facebook`, `domaine` par
concurrent, `mots_cles` global. `concurrents_pages` (gratuit) relit chaque page (robots.txt respecté) et rend le DIFF
avec la lecture précédente, encadré ; `concurrents_pubs` et `concurrents_serp` rendent des cartes « collecte »
(Actors facebook_pubs et serp de la liste blanche, options payantes coupées) ; acceptées : pubs résumées par concurrent,
positions des domaines des concurrents par mot-clé. `GET /api/veille/{eid}/concurrents` rend le tout. Faux réseau.
Run (depuis backend/) : & $PY tests/test_apify_concurrents.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzconc_"))
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
from app.services import apify as AP, veille as V, veille_collecte as VC, veille_concurrents as VK                    # noqa: E402
from app.services.storage import init_db                                                                              # noqa: E402

c = TestClient(app)
RUNS = []
REPONSE = {}


async def faux_devis(cle, n, entree=None):
    return 0.05


async def faux_lancer(cle, entree, n, plafond=None):
    RUNS.append((cle, entree, n))
    return {"items": REPONSE[cle], "cout_usd": 0.03, "statut": "SUCCEEDED", "partiel": False, "run_id": "R1",
            "devis_usd": 0.05}


AP.devis = faux_devis
AP.lancer = faux_lancer
PAGES = {"https://runwayml.com/pricing": "Standard 12 $ / mois\nPro 28 $ / mois"}
LUES = []


async def faux_lire(url):
    LUES.append(url)
    return PAGES[url]


async def faux_robots(url):
    return "interdit" not in url


VK._LIRE = faux_lire
VK._ROBOTS = faux_robots


async def preparer():
    await init_db()
    A = E.creer({"nom": "Veille"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    return A, cid


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)

print("[0] liste blanche")
fb, sp = AP.ACTEURS.get("facebook_pubs") or {}, AP.ACTEURS.get("serp") or {}
check("0.1 facebook_pubs : Actor épinglé, enrichissement e-commerce coupé, une pub = un événement",
      fb.get("acteur") == "apify~facebook-ads-scraper" and fb["impose"].get("enrichWithEcommerceData") is False
      and fb.get("evenements") == {"apify-default-dataset-item"}, fb)
check("0.2 serp : IA, leads et contenu des sites coupés, une page = un événement",
      sp.get("acteur") == "apify~google-search-scraper" and sp["impose"].get("maximumLeadsEnrichmentRecords") == 0
      and sp["impose"]["websiteContentScraper"] == {"enable": False} and sp["impose"]["chatGptSearch"] == {"enableChatGpt": False}
      and "search-page-scraped" in sp.get("evenements", ()), sp)
check("0.3 serp : N pages réparties sur les mots-clés (une ligne = un mot-clé)",
      AP.volume("serp", {"queries": "a\nb\nc"}, 3) == 3 and AP.filtrer("serp", {"queries": "a\nb\nc"}, 3)["maxPagesPerQuery"] == 1)
check("0.4 outils dans la boîte « veille »", {"concurrents_pages", "concurrents_pubs", "concurrents_serp"}
      <= set(AB.BOITES["veille"]["outils"]))

print("[1] le périmètre")
p = VC.valider_perimetre({"mots_cles": ["générateur vidéo ia"] * 12, "concurrents": [{"id": "runway",
    "pages": ["https://runwayml.com/pricing", "ftp://x", "https://a", "https://b", "https://c"],
    "facebook": ["https://www.facebook.com/runwayml"], "domaine": "RunwayML.com"}]})
r0 = p["concurrents"][0]
check("1.1 pages http(s) seulement, 3 au plus ; domaine en minuscules ; mots-clés 10 au plus",
      r0["pages"] == ["https://runwayml.com/pricing", "https://a", "https://b"] and r0["domaine"] == "runwayml.com"
      and len(p["mots_cles"]) == 10 and r0["facebook"] == ["https://www.facebook.com/runwayml"], p)
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte":
    "prix de runway https://runwayml.com/pricing et sa page https://www.facebook.com/runwayml"}])]))
for src, vals in (("pages", ["https://runwayml.com/pricing"]), ("facebook", ["https://www.facebook.com/runwayml"]),
                  ("domaine", ["runwayml.com"])):
    r = asyncio.run(ao.executer("veille_sources", {"concurrent": "runway", "source": src, "valeurs": vals}, ctx))
    check(f"1.2 veille_sources {src}", r["ok"], r)
r = asyncio.run(ao.executer("veille_sources", {"concurrent": "", "source": "requetes_suivies",
                                                "valeurs": ["générateur vidéo ia", "runway alternative"]}, ctx))
check("1.3 mots-clés (globaux)", r["ok"] and V.perimetre(A)["mots_cles"] == ["générateur vidéo ia", "runway alternative"], r)

print("[2] pages prix (gratuit)")
r = asyncio.run(ao.executer("concurrents_pages", {}, ctx))
d = r.get("donnees") or {}
check("2.1 première lecture : gardée, aucun changement", r["ok"] and d.get("lues") == 1 and d.get("changees") == 0, r)
PAGES["https://runwayml.com/pricing"] = "Standard 15 $ / mois\nPro 28 $ / mois"
r = asyncio.run(ao.executer("concurrents_pages", {}, ctx))
d = r.get("donnees") or {}
check("2.2 deuxième lecture : le changement rendu en diff, encadré comme preuve",
      d.get("changees") == 1 and "15 $" in json.dumps(d, ensure_ascii=False) and "PREUVE" in json.dumps(d), d)
check("2.3 aucun Apify, aucun coût", not RUNS)

print("[3] pubs")
r = asyncio.run(ao.executer("concurrents_pubs", {"concurrent": "runway", "max": 30}, ctx))
check("3.1 sans clé : refus", not r["ok"], r)
settings.APIFY_TOKEN = "apify_api_X"
r = asyncio.run(ao.executer("concurrents_pubs", {"concurrent": "runway", "max": 30}, ctx))
k = r["carte"] or {}
check("3.2 carte facebook_pubs, but pubs, page du périmètre, pubs actives", r["ok"] and k["arguments"]["acteur"] == "facebook_pubs"
      and k["arguments"]["but"] == "pubs" and k["arguments"]["entree"] == {
          "startUrls": [{"url": "https://www.facebook.com/runwayml"}], "activeStatus": "active"}, k)
REPONSE["facebook_pubs"] = [{"snapshot": {"body": {"text": "Gen-4 is here " + "x" * 400}, "title": "Runway"},
                             "startDateFormatted": "2026-10-10", "publisherPlatform": ["FACEBOOK", "INSTAGRAM"],
                             "isActive": True, "url": "https://www.facebook.com/ads/library/?id=1"}]
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
n_carte = sum(1 for m in asyncio.run(st.lire(cid))["messages"] for b in m["blocs"] if b.get("type") == "carte") - 1
rr = c.post(f"/api/agent/campagnes/{cid}/carte/{n_carte}", json={"decision": "acceptee"})
fa = [m for m in rr.json()["messages"] if m["role"] == "fait"][-1]["blocs"][0]["arguments"]
check("3.3 fait : nombre de pubs", rr.status_code == 200 and fa.get("pubs") == 1, fa)

print("[4] SERP")
r = asyncio.run(ao.executer("concurrents_serp", {}, ctx))
k = r["carte"] or {}
check("4.1 carte serp, but serp, une ligne par mot-clé, une page chacun", r["ok"] and k["arguments"]["acteur"] == "serp"
      and k["arguments"]["entree"]["queries"] == "générateur vidéo ia\nrunway alternative" and k["arguments"]["max"] == 2, k)
REPONSE["serp"] = [{"searchQuery": {"term": "générateur vidéo ia"}, "organicResults": [
    {"position": 1, "url": "https://www.capcut.com/x"}, {"position": 3, "url": "https://runwayml.com/gen4"}]},
    {"searchQuery": {"term": "runway alternative"}, "organicResults": [{"position": 2, "url": "https://blog.example/x"}]}]
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
n_carte += 1
rr = c.post(f"/api/agent/campagnes/{cid}/carte/{n_carte}", json={"decision": "acceptee"})
fa = [m for m in rr.json()["messages"] if m["role"] == "fait"][-1]["blocs"][0]["arguments"]
check("4.2 fait : mots-clés relevés", rr.status_code == 200 and fa.get("mots_cles") == 2, fa)

print("[5] la route")
j = c.get(f"/api/veille/{A}/concurrents").json()
check("5.1 pubs : texte borné à 300, plateformes, début, lien", j["pubs"]["runway"][0]["plateformes"] == ["FACEBOOK", "INSTAGRAM"]
      and len(j["pubs"]["runway"][0]["texte"]) <= 300 and j["pubs"]["runway"][0]["debut"] == "2026-10-10", j.get("pubs"))
check("5.2 serp : rang du domaine d'un concurrent connu", {"rang": 3, "domaine": "runwayml.com", "concurrent": "runway"}
      in j["serp"]["mots_cles"]["générateur vidéo ia"], j.get("serp"))
check("5.3 pages : le dernier changement", j["pages"] and j["pages"][0]["concurrent"] == "runway" and j["pages"][0]["change"] is True, j.get("pages"))
check("5.4 espace inconnu : 404", c.get("/api/veille/inconnu/concurrents").status_code == 404)

settings.APIFY_TOKEN = ""
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
