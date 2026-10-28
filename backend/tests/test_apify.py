# -*- coding: utf-8 -*-
"""t364 (28/10/2026) — socle Apify, tâche 1 : le client `apify.py`. Liste blanche, entrée filtrée, devis lu dans
`pricingInfos` (PPE, par résultat, gratuit ; forfait refusé), run sous `maxTotalChargeUsd`, suivi, abort au-delà de la
durée (résultats partiels), échec avec coût, 402 du compte Apify, jeton jamais dans une URL ni un message. Aucun réseau.
Run (depuis backend/) : & $PY tests/test_apify.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzapify_"))
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


from app.config import settings                                      # noqa: E402
from app.services import apify as AP, pricing as PR                  # noqa: E402

JETON = "apify_api_SECRET123"
API = AP.API
APPELS = []
ETAT = {"horloge": 0.0}


def ppe(evenements):
    return {"data": {"pricingInfos": [{"pricingModel": "PAY_PER_EVENT", "pricingPerEvent": {"actorChargeEvents": evenements}}]}}


PRIX = {
    "compass~crawler-google-places": ppe({
        "apify-actor-start": {"eventPriceUsd": 0.00005}, "place-scraped": {"eventPriceUsd": 0.004},
        "lead-scraped": {"eventPriceUsd": 0.1}, "contact-details-scraped": {"eventPriceUsd": 0.002}}),
    "trudax~reddit-scraper-lite": {"data": {"pricingInfos": [{"pricingModel": "PRICE_PER_DATASET_ITEM", "pricePerUnitUsd": 0.004}]}},
}
SCENARIO = {}       # url de GET d'un run -> liste de réponses successives


async def faux_get(url, jeton=None):
    APPELS.append(("GET", url, jeton, None))
    if url in PRIX:
        return 200, PRIX[url]
    for cle, rep in SCENARIO.items():
        if url.startswith(cle):
            r = rep.pop(0) if len(rep) > 1 else rep[0]
            ETAT["horloge"] += r.get("_duree", 0)
            return r["statut"], r["json"]
    return 404, {}


async def faux_post(url, corps, jeton=None):
    APPELS.append(("POST", url, jeton, corps))
    if "/abort" in url:
        return 200, {"data": {"status": "ABORTING"}}
    return SCENARIO["POST"][0]["statut"], SCENARIO["POST"][0]["json"]


AP._GET = lambda url, jeton=None: faux_get(url.replace(API + "/acts/", "").split("?")[0] if "/runs" not in url and "/acts/" in url else url, jeton)
AP._POST = faux_post
AP._HORLOGE = lambda: ETAT["horloge"]


def run(co):
    return asyncio.run(co)


def erreur(co):
    try:
        run(co)
        return None
    except Exception as e:  # noqa: BLE001
        return e


def run_fini(statut="SUCCEEDED", cout=0.21, rid="R1"):
    return {"data": {"id": rid, "status": statut, "defaultDatasetId": "D1", "usageTotalUsd": cout}}


def scenario(post, suivis, items, final):
    SCENARIO.clear()
    SCENARIO["POST"] = [{"statut": post[0], "json": post[1]}]
    SCENARIO[f"{API}/actor-runs/R1?"] = suivis
    SCENARIO[f"{API}/datasets/D1/items"] = [{"statut": 200, "json": items}]
    SCENARIO[f"{API}/actor-runs/R1"] = [{"statut": 200, "json": final}]
    APPELS.clear()
    ETAT["horloge"] = 0.0


ENTREE_GM = {"searchStringsArray": ["studio vidéo"], "locationQuery": "Lyon, France"}

print("[1] liste blanche et entrée")
check("1.1 google_maps et reddit dans la liste, usages leads / veille",
      AP.ACTEURS["google_maps"]["usage"] == "leads" and AP.ACTEURS["reddit"]["usage"] == "veille")
check("1.2 chaque entrée : acteur owner~nom, build épinglé, champ du nombre",
      all("~" in a["acteur"] and a["build"][0].isdigit() and a["max"] for a in AP.ACTEURS.values()))
e = erreur(AP.devis("inconnu", 10))
check("1.3 acteur hors liste : refus", isinstance(e, AP.ApifyRefus) and e.code == 422, e)
e = None
try:
    AP.filtrer("google_maps", dict(ENTREE_GM, customMapFunction="x=>x"), 20)
except AP.ApifyRefus as x:
    e = x
check("1.4 champ d'entrée non autorisé : refus nommé", e is not None and "customMapFunction" in str(e), e)
f = AP.filtrer("google_maps", ENTREE_GM, 20)
check("1.5 entrée imposée : contacts, avis, images, leads coupés ; nombre posé",
      f["scrapeContacts"] is False and f["maxReviews"] == 0 and f["maxImages"] == 0
      and f["maximumLeadsEnrichmentRecords"] == 0 and f["maxCrawledPlacesPerSearch"] == 20, f)
e = None
try:
    AP.filtrer("google_maps", dict(ENTREE_GM, scrapeContacts=True), 20)
except AP.ApifyRefus as x:
    e = x
check("1.6 un champ imposé ne se pose pas depuis l'entrée", e is not None, e)
e = None
try:
    AP.filtrer("google_maps", {"searchStringsArray": ["x" * 400]}, 20)
except AP.ApifyRefus as x:
    e = x
check("1.7 valeur trop longue : refus", e is not None, e)

f = AP.filtrer("reddit", {"searches": ["higgsfield ai"]}, 100)
check("1.8 reddit (essai du 28/10 : 10 posts sur 100) : maxPostCount = N, pas de communautés, pas d'URL de départ",
      f["maxItems"] == 100 and f["maxPostCount"] == 100 and f["skipCommunity"] is True and f["ignoreStartUrls"] is True, f)

print("[2] devis")
d = run(AP.devis("google_maps", 100))
check("2.1 PPE : démarrage + par lieu × N, sans les événements optionnels", abs(d - (0.00005 + 0.4)) < 1e-6, d)
check("2.2 par résultat : prix × N", abs(run(AP.devis("reddit", 100)) - 0.4) < 1e-6)
PRIX["trudax~reddit-scraper-lite"] = {"data": {"pricingInfos": [{"pricingModel": "FREE"}]}}
AP.vider_cache()
check("2.3 gratuit : forfait de calcul", abs(run(AP.devis("reddit", 100)) - AP.FORFAIT_CALCUL_USD) < 1e-9)
PRIX["trudax~reddit-scraper-lite"] = {"data": {"pricingInfos": [{"pricingModel": "FLAT_PRICE_PER_MONTH"}]}}
AP.vider_cache()
e = erreur(AP.devis("reddit", 100))
check("2.4 forfait mensuel : refusé", isinstance(e, AP.ApifyRefus), e)
PRIX["trudax~reddit-scraper-lite"] = {"data": {"pricingInfos": [{"pricingModel": "PRICE_PER_DATASET_ITEM", "pricePerUnitUsd": 0.004}]}}
AP.vider_cache()
APPELS.clear()
run(AP.devis("reddit", 10)); run(AP.devis("reddit", 20))
check("2.5 prix gardés en cache (un seul appel pour deux devis)", len([a for a in APPELS if a[0] == "GET"]) == 1, APPELS)
o = run(AP.op("reddit", 100))
check("2.6 op chiffrée par pricing (kind apify)", o["kind"] == "apify" and abs(PR.estimate(o)["total_usd"] - 0.4) < 1e-6, o)

print("[3] sans clé")
check("3.1 configure() faux sans jeton", AP.configure() is False)
APPELS.clear()
e = erreur(AP.lancer("google_maps", ENTREE_GM, 20))
check("3.2 lancer sans jeton : SansCle, aucun run", isinstance(e, AP.SansCle) and not [a for a in APPELS if a[0] == "POST"], e)
settings.APIFY_TOKEN = JETON
check("3.3 configure() vrai avec jeton", AP.configure() is True)

print("[4] run fini d'emblée")
items = [{"title": "Studio Lune", "website": "https://studio-lune.fr"}] * 3
scenario((201, run_fini()), [{"statut": 200, "json": run_fini()}], items, run_fini(cout=0.013))
r = run(AP.lancer("google_maps", ENTREE_GM, 20))
check("4.1 résultats, statut, coût réel, run_id", r["items"] == items and r["statut"] == "SUCCEEDED" and r["cout_usd"] == 0.013
      and r["run_id"] == "R1" and r["partiel"] is False, r)
post = [a for a in APPELS if a[0] == "POST"][0]
check("4.2 URL : build épinglé, maxTotalChargeUsd = plafond leads, maxItems, timeout",
      "build=0.14.777" in post[1] and "maxTotalChargeUsd=1.0" in post[1] and "maxItems=20" in post[1] and "timeout=600" in post[1], post[1])
check("4.3 le jeton n'est JAMAIS dans une URL", all(JETON not in a[1] for a in APPELS))
check("4.4 le jeton part en en-tête (argument jeton)", post[2] == JETON)
check("4.5 l'entrée envoyée est filtrée", post[3]["scrapeContacts"] is False and post[3]["locationQuery"] == "Lyon, France")
items_url = [a[1] for a in APPELS if "/datasets/" in a[1]][0]
check("4.6 dataset borné à N (limit=20, clean)", "limit=20" in items_url and "clean=true" in items_url, items_url)

print("[5] run à suivre")
scenario((201, {"data": dict(run_fini()["data"], status="RUNNING")}),
         [{"statut": 200, "json": {"data": dict(run_fini()["data"], status="RUNNING")}, "_duree": 60},
          {"statut": 200, "json": run_fini()}], items, run_fini(cout=0.02))
r = run(AP.lancer("google_maps", ENTREE_GM, 20))
check("5.1 suivi jusqu'à SUCCEEDED, coût réel", r["statut"] == "SUCCEEDED" and r["cout_usd"] == 0.02, r)
check("5.2 aucun second lancement", len([a for a in APPELS if a[0] == "POST"]) == 1)

print("[6] run trop long : abort et partiel")
long_ = {"statut": 200, "json": {"data": dict(run_fini()["data"], status="RUNNING")}, "_duree": 200}
scenario((201, {"data": dict(run_fini()["data"], status="RUNNING")}), [long_], items[:1], run_fini("ABORTED", 0.005))
r = run(AP.lancer("google_maps", ENTREE_GM, 20))
check("6.1 abort envoyé", any("/abort" in a[1] for a in APPELS if a[0] == "POST"))
check("6.2 résultats déjà là rendus, marqués partiels", r["partiel"] is True and r["items"] == items[:1] and r["cout_usd"] == 0.005, r)

print("[7] échec avec coût")
scenario((201, run_fini("FAILED", 0.03)), [{"statut": 200, "json": run_fini("FAILED", 0.03)}], [], run_fini("FAILED", 0.03))
e = erreur(AP.lancer("google_maps", ENTREE_GM, 20))
check("7.1 FAILED : ApifyEchec avec le coût réel", isinstance(e, AP.ApifyEchec) and e.cout_usd == 0.03, e)
check("7.2 le message ne contient pas le jeton", JETON not in str(e))

print("[8] refus du compte Apify")
scenario((402, {"error": {"type": "not-enough-usage-to-run-paid-actor", "message": "Not enough credit " + JETON}}), [], [], {})
e = erreur(AP.lancer("google_maps", ENTREE_GM, 20))
check("8.1 402 d'Apify : ApifyRefus 402", isinstance(e, AP.ApifyRefus) and e.code == 402, e)
check("8.2 jamais le jeton dans le message, même renvoyé par Apify", JETON not in str(e), str(e))

print("[9] devis au-delà du plafond")
APPELS.clear()
e = erreur(AP.lancer("google_maps", ENTREE_GM, 500))
check("9.1 refus 402 avant tout run", isinstance(e, AP.ApifyRefus) and e.code == 402 and not [a for a in APPELS if a[0] == "POST"], e)
scenario((201, run_fini()), [{"statut": 200, "json": run_fini()}], items, run_fini())
e = erreur(AP.lancer("google_maps", ENTREE_GM, 20, plafond=5.0))
check("9.2 un plafond demandé ne dépasse jamais celui de l'usage", True if e is None else False, e)
post = [a for a in APPELS if a[0] == "POST"][-1]
check("9.3 maxTotalChargeUsd reste au plafond de l'usage", "maxTotalChargeUsd=1.0" in post[1], post[1])

print("[10] panne réseau pendant le suivi")
async def get_panne(url, jeton=None):
    if "/actor-runs/R1?" in url:
        raise OSError("réseau coupé")
    return await faux_get(url, jeton)
scenario((201, {"data": dict(run_fini()["data"], status="RUNNING")}), [], items, run_fini("SUCCEEDED", 0.02))
ancien = AP._GET
AP._GET = get_panne
r = run(AP.lancer("google_maps", ENTREE_GM, 20))
AP._GET = ancien
check("10.1 le run est relu par son id, jamais relancé", len([a for a in APPELS if a[0] == "POST" and "/abort" not in a[1]]) == 1, APPELS)
check("10.2 résultats rendus (partiels : suivi perdu)", r["items"] == items and r["partiel"] is True, r)

settings.APIFY_TOKEN = ""
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
