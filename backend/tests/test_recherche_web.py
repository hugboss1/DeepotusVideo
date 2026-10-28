# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 5b : les FOURNISSEURS DE RECHERCHE WEB (Anthropic, Tavily, Exa,
Serper), au choix. Chaque adaptateur sur un faux transport : forme rendue {titre, url, extrait}, erreur dite, sans clé
refus net, coût (devis et réel) ; le choix du fournisseur et les clés (coffre) par des routes LOCALES ; les prix passent
par pricing (`recherche_web`) pour que les plafonds les voient. Aucun réseau.
Run (depuis backend/) : & $PY tests/test_recherche_web.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrw_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY"):
    os.environ[k] = ""
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
from app.services import coffre as CF, pricing as PR, recherche_web as RW   # noqa: E402

c = TestClient(app)
lan = TestClient(app, client=("192.168.1.20", 50000))
APPELS, REP = [], {}


async def faux_post(url, headers, corps):
    APPELS.append((url, dict(headers), corps))
    return REP[url]


RW._POST = faux_post
REP["https://api.tavily.com/search"] = (200, {"results": [{"title": "Studio Lune", "url": "https://studio-lune.fr/", "content": "studio vidéo"}]})
REP["https://api.exa.ai/search"] = (200, {"results": [{"title": "Agence Z", "url": "https://agence-z.fr/"}], "costDollars": {"total": 0.007}})
REP["https://google.serper.dev/search"] = (200, {"organic": [{"title": "Maison X", "link": "https://maison-x.fr/", "snippet": "jeux"}]})
REP["https://api.anthropic.com/v1/messages"] = (200, {"content": [
    {"type": "server_tool_use", "id": "s1", "name": "web_search", "input": {"query": "studios"}},
    {"type": "web_search_tool_result", "tool_use_id": "s1", "content": [
        {"type": "web_search_result", "url": "https://studio-nord.fr/", "title": "Studio Nord", "encrypted_content": "x"}]},
    {"type": "text", "text": "voici"}],
    "usage": {"input_tokens": 2000, "output_tokens": 300, "server_tool_use": {"web_search_requests": 1}}})


def run(co):
    return asyncio.run(co)


print("[1] sans clé")
for f in RW.FOURNISSEURS:
    try:
        run(RW.rechercher("studios vidéo Lyon", 5, f)); code = None
    except RW.SansCle as e:
        code = str(e)
    check(f"1 {f} : sans clé, refus net et aucun appel", code and not APPELS, code)

print("[2] adaptateurs")
for k, v in (("TAVILY_API_KEY", "tvly-x"), ("EXA_API_KEY", "exa-x"), ("SERPER_API_KEY", "serp-x"), ("ANTHROPIC_API_KEY", "sk-ant-x")):
    setattr(settings, k, v)
r = run(RW.rechercher("studios vidéo Lyon", 5, "tavily"))
u, h, b = APPELS[-1]
check("2a Tavily : Bearer, query, max_results ; forme", h.get("Authorization") == "Bearer tvly-x" and b["query"] == "studios vidéo Lyon"
      and b["max_results"] == 5 and r["resultats"] == [{"titre": "Studio Lune", "url": "https://studio-lune.fr/", "extrait": "studio vidéo"}]
      and r["fournisseur"] == "tavily" and r["cout_usd"] == RW.PRIX["tavily"], r)
r = run(RW.rechercher("agences", 3, "exa"))
u, h, b = APPELS[-1]
check("2b Exa : x-api-key, numResults ; coût réel rendu par Exa", h.get("x-api-key") == "exa-x" and b["numResults"] == 3
      and r["resultats"][0]["url"] == "https://agence-z.fr/" and r["cout_usd"] == 0.007, r)
r = run(RW.rechercher("jeux", 4, "serper"))
u, h, b = APPELS[-1]
check("2c Serper : X-API-KEY, q, num ; organic", h.get("X-API-KEY") == "serp-x" and b == {"q": "jeux", "num": 4}
      and r["resultats"] == [{"titre": "Maison X", "url": "https://maison-x.fr/", "extrait": "jeux"}], r)
r = run(RW.rechercher("studios", 5, "anthropic"))
u, h, b = APPELS[-1]
outil = b["tools"][0]
check("2d Anthropic : outil web_search, plafond d'usages, appel direct", h.get("x-api-key") == "sk-ant-x"
      and outil["type"] == "web_search_20260209" and outil["name"] == "web_search" and outil["max_uses"] == RW.MAX_USAGES_ANTHROPIC
      and outil["allowed_callers"] == ["direct"], outil)
check("2e Anthropic : résultats et coût (recherches + jetons)", r["resultats"] == [{"titre": "Studio Nord", "url": "https://studio-nord.fr/", "extrait": ""}]
      and r["cout_usd"] > RW.PRIX["anthropic"], r)
REP["https://api.anthropic.com/v1/messages"] = (200, {"content": [{"type": "web_search_tool_result", "tool_use_id": "s1",
    "content": {"type": "web_search_tool_result_error", "error_code": "too_many_requests"}}], "usage": {"input_tokens": 10, "output_tokens": 5}})
try:
    run(RW.rechercher("studios", 5, "anthropic")); code = None
except RW.RechercheEchouee as e:
    code = str(e)
check("2f Anthropic : un résultat d'erreur est dit", code and "too_many_requests" in code, code)
REP["https://api.tavily.com/search"] = (401, {"detail": "bad key"})
try:
    run(RW.rechercher("x", 5, "tavily")); code = None
except RW.RechercheEchouee as e:
    code = str(e)
check("2g statut HTTP d'échec : dit, sans la clé", code and "401" in code and "tvly-x" not in code, code)
try:
    run(RW.rechercher("x", 5, "bing")); bad = False
except ValueError:
    bad = True
check("2h fournisseur inconnu refusé", bad)

print("[3] prix et plafonds")
check("3a devis Tavily = prix unitaire", abs(RW.devis("tavily", 5) - RW.PRIX["tavily"]) < 1e-9, RW.devis("tavily", 5))
check("3b devis Anthropic : recherches + jetons (au-dessus du prix des recherches seules)",
      RW.devis("anthropic", 5) > RW.PRIX["anthropic"] * RW.MAX_USAGES_ANTHROPIC, RW.devis("anthropic", 5))
check("3c pricing connaît recherche_web", PR.estimate({"kind": "recherche_web", "fournisseur": "serper", "requetes": 2})["total_usd"]
      == 2 * RW.PRIX["serper"])

print("[4] choix et clés (routes locales)")
check("4a défaut : anthropic", RW.fournisseur_actif() == "anthropic")
r = c.get("/api/prospects/recherche")
j = r.json()
check("4b état : fournisseurs, configurés, prix", r.status_code == 200 and j["fournisseur"] == "anthropic"
      and [x["id"] for x in j["fournisseurs"]] == list(RW.FOURNISSEURS) and all("configure" in x and "prix_usd" in x for x in j["fournisseurs"])
      and "tvly-x" not in r.text, j)
r = c.post("/api/prospects/recherche/fournisseur", json={"fournisseur": "exa"})
check("4c choisir exa", r.status_code == 200 and RW.fournisseur_actif() == "exa")
check("4d fournisseur inconnu : 422", c.post("/api/prospects/recherche/fournisseur", json={"fournisseur": "bing"}).status_code == 422)
setattr(settings, "SERPER_API_KEY", "")
r = c.post("/api/prospects/recherche/cle", json={"fournisseur": "serper", "valeur": "serp-neuve"})
check("4e poser la clé Serper : rangée et appliquée, jamais rendue", r.status_code == 200 and settings.SERPER_API_KEY == "serp-neuve"
      and "serp-neuve" not in r.text and r.json().get("ou") in ("env", "coffre", "memoire"), r.text)
check("4f la clé Anthropic ne se pose pas ici", c.post("/api/prospects/recherche/cle", json={"fournisseur": "anthropic", "valeur": "x"}).status_code == 422)
check("4g clés de recherche dans les secrets du coffre", {"TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY"} <= CF.SECRETES)
check("4h local seulement", lan.get("/api/prospects/recherche").status_code in (401, 403)
      and lan.post("/api/prospects/recherche/cle", json={"fournisseur": "exa", "valeur": "x"}).status_code in (401, 403))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
