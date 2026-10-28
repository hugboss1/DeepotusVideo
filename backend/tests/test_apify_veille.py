# -*- coding: utf-8 -*-
"""t366 (28/10/2026) — A2 veille enrichie par Apify. Le périmètre garde, par concurrent, des valeurs `apify` bornées ;
`veille_sources` les enregistre (une URL seulement si l'utilisateur l'a collée) ; `veille_apify` rend une carte
« collecte » (but veille) dont l'entrée vient du périmètre, jamais inventée (Reddit, X, TikTok : les requêtes du
concurrent par défaut) ; acceptée : les éléments deviennent des lignes de veille (auteur haché, jamais en clair) dans
le brut du jour, puis la veille est reconsolidée (classée par la grille) — sauf si une collecte tourne. Faux run.
Run (depuis backend/) : & $PY tests/test_apify_veille.py"""
import asyncio, json, os, pathlib, sys, tempfile, datetime as dt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzapv_"))
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
from app.services import apify as AP, veille as V, veille_collecte as VC                                              # noqa: E402
from app.services.storage import init_db                                                                              # noqa: E402

c = TestClient(app)
RUNS = []
ITEMS = [
    {"dataType": "post", "title": "Runway is too expensive", "body": "Credits burn way too fast, looking for an alternative",
     "url": "https://reddit.com/r/x/1", "createdAt": "2026-10-01T10:00:00Z", "username": "alice_secret", "upVotes": 12},
    {"dataType": "comment", "body": "Love the motion brush, great quality", "url": "https://reddit.com/r/x/1/c",
     "createdAt": "2026-10-02T10:00:00Z", "username": "bob_secret", "upVotes": 3},
    {"dataType": "post", "title": "", "body": "", "url": "https://reddit.com/r/x/2"},
]


async def faux_devis(cle, n, entree=None):
    return 0.2


async def faux_lancer(cle, entree, n, plafond=None):
    RUNS.append((cle, entree, n))
    return {"items": ITEMS, "cout_usd": 0.05, "statut": "SUCCEEDED", "partiel": False, "run_id": "R1", "devis_usd": 0.2}


AP.devis = faux_devis
AP.lancer = faux_lancer


async def preparer():
    await init_db()
    A = E.creer({"nom": "Veille"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    return A, cid


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)

print("[1] le périmètre")
p = VC.valider_perimetre({"concurrents": [{"id": "runway", "hn": ["runway ml"], "apify": {
    "trustpilot": ["https://www.trustpilot.com/review/runwayml.com"] * 9, "inconnue": ["x"], "g2": ["y" * 400]}}]})
ap = p["concurrents"][0]["apify"]
check("1.1 valeurs apify gardées, bornées à 5 et 300 caractères, sources inconnues écartées",
      len(ap["trustpilot"]) == 5 and "inconnue" not in ap and len(ap["g2"][0]) == 300, ap)
check("1.2 sans apify : objet vide", VC.valider_perimetre({"concurrents": [{"id": "kling"}]})["concurrents"][0]["apify"] == {})
check("1.3 outils dans la boîte « veille »", {"veille_apify", "veille_sources"} <= set(AB.BOITES["veille"]["outils"]))

print("[2] veille_sources")
r = asyncio.run(ao.executer("veille_sources", {"concurrent": "runway", "source": "trustpilot",
                                                "valeurs": ["https://www.trustpilot.com/review/runwayml.com"]}, ctx))
check("2.1 une URL non collée par l'utilisateur : refus", not r["ok"] and "coll" in r["resume"], r)
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte":
    "Trustpilot de Runway : https://www.trustpilot.com/review/runwayml.com"}])]))
r = asyncio.run(ao.executer("veille_sources", {"concurrent": "runway", "source": "trustpilot",
                                                "valeurs": ["https://www.trustpilot.com/review/runwayml.com"]}, ctx))
check("2.2 URL collée : enregistrée au périmètre de l'espace", r["ok"] and V.perimetre(A)["concurrents"] and
      next(x for x in V.perimetre(A)["concurrents"] if x["id"] == "runway")["apify"]["trustpilot"]
      == ["https://www.trustpilot.com/review/runwayml.com"], r)
r = asyncio.run(ao.executer("veille_sources", {"concurrent": "runway", "source": "google_play",
                                                "valeurs": ["com.runwayml.app"]}, ctx))
check("2.3 un identifiant d'application (pas une URL) : accepté", r["ok"], r)
r = asyncio.run(ao.executer("veille_sources", {"concurrent": "inconnu", "source": "reddit", "valeurs": ["x"]}, ctx))
check("2.4 concurrent hors périmètre : refus", not r["ok"], r)

print("[3] veille_apify")
r = asyncio.run(ao.executer("veille_apify", {"source": "reddit", "concurrent": "runway", "max": 50}, ctx))
check("3.1 sans clé : refus", not r["ok"] and "Apify" in r["resume"], r)
settings.APIFY_TOKEN = "apify_api_X"
r = asyncio.run(ao.executer("veille_apify", {"source": "reddit", "concurrent": "runway", "max": 50}, ctx))
k = r["carte"] or {}
a = k.get("arguments") or {}
hn = next(x for x in V.perimetre(A)["concurrents"] if x["id"] == "runway")["hn"]
check("3.2 Reddit : requêtes du concurrent par défaut, but veille, concurrent nommé, aucun run",
      r["ok"] and a.get("acteur") == "reddit" and a.get("but") == "veille" and a.get("concurrent") == "runway"
      and a.get("entree") == {"searches": hn} and not RUNS, k)
r2 = asyncio.run(ao.executer("veille_apify", {"source": "trustpilot", "concurrent": "runway", "max": 50}, ctx))
check("3.3 Trustpilot : les URL du périmètre", (r2["carte"] or {}).get("arguments", {}).get("entree")
      == {"companyUrls": ["https://www.trustpilot.com/review/runwayml.com"]}, r2)
r3 = asyncio.run(ao.executer("veille_apify", {"source": "g2", "concurrent": "runway"}, ctx))
check("3.4 source sans valeur au périmètre (G2) : refus qui dit quoi faire", not r3["ok"] and "veille_sources" in r3["resume"], r3)
r4 = asyncio.run(ao.executer("veille_apify", {"source": "google_maps", "concurrent": "runway"}, ctx))
check("3.5 une source de leads n'est pas une source de veille", not r4["ok"], r4)

print("[4] acceptée : verbatims")
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
n_carte = sum(1 for m in asyncio.run(st.lire(cid))["messages"] for b in m["blocs"] if b.get("type") == "carte") - 1
r = c.post(f"/api/agent/campagnes/{cid}/carte/{n_carte}", json={"decision": "acceptee"})
check("4.1 un run", r.status_code == 200 and len(RUNS) == 1, r.text[:300])
fa = [m for m in r.json()["messages"] if m["role"] == "fait"][-1]["blocs"][0]["arguments"]
check("4.2 le fait dit les verbatims ajoutés (2, l'élément vide écarté)", fa.get("verbatims") == 2, fa)
jour = dt.date.today().isoformat()
f = V.dossier(A, jour) / "brut" / "apify-reddit-runway.jsonl"
lignes = [json.loads(x) for x in f.read_text("utf-8").splitlines()] if f.exists() else []
check("4.3 brut du jour : lignes de veille, source reddit, concurrent runway", len(lignes) == 2
      and all(x["source"] == "reddit" and x["concurrent"] == "runway" for x in lignes), lignes)
check("4.4 auteur haché, jamais en clair", lignes and all(x["auteur_hash"] and "secret" not in json.dumps(x) for x in lignes))
rap = V.dernier(A)
check("4.5 veille reconsolidée : rapport du jour, verbatims classés", rap and rap.get("date") == jour
      and any(v["source"] == "reddit" for v in V.verbatims(A)), (rap or {}).get("date"))

print("[5] une collecte tourne : brut seul")
V._TACHES[A] = asyncio.new_event_loop().create_future() if False else type("T", (), {"done": lambda self: False})()
_en_vie = V._en_vie
V._en_vie = lambda eid: True
r5 = V.ajouter_brut(A, "reddit", "kling", [VC._ligne("kling", "reddit", "https://reddit.com/k", "2026-10-03", "carol",
                                                     "Kling is great value", 5, "kling ai")])
V._en_vie = _en_vie
V._TACHES.pop(A, None)
check("5.1 écrit au brut, non consolidé (la collecte en cours le fera)", r5 == {"ajoutes": 1, "consolide": False}, r5)
r6 = V.ajouter_brut(A, "reddit", "kling", [VC._ligne("kling", "reddit", "https://reddit.com/k", "2026-10-03", "carol",
                                                     "Kling is great value", 5, "kling ai")])
check("5.2 relancé : aucun doublon", r6["ajoutes"] == 0, r6)

settings.APIFY_TOKEN = ""
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
