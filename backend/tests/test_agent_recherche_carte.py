# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 5d : la CARTE DE RECHERCHE web. L'outil `entreprises_rechercher`
rend une carte de devis (aucun appel) ; acceptée (POST /api/agent/campagnes/{cid}/carte/{n}) : plafond vérifié AVANT
tout appel (402 = rien), sans clé 503, une recherche chez le fournisseur choisi, les URL publiques déposées (lisibles
ensuite par prospects_chercher), un message `fait` avec la liste, le coût réel noté ; refusée : rien ; décidée deux fois :
409. Faux adaptateur, aucun réseau.
Run (depuis backend/) : & $PY tests/test_agent_recherche_carte.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrc_"))
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
from app.services import agent_format as fmt, agent_outils as ao, agent_store as st, espaces as E   # noqa: E402
from app.services import plafonds as PL, recherche_web as RW                                       # noqa: E402
from app.services.storage import init_db                                                           # noqa: E402

c = TestClient(app)
APPELS = []


async def faux_rechercher(requete, n=5, fournisseur=None):
    APPELS.append((requete, n, fournisseur))
    return {"resultats": [{"titre": "Studio Lune", "url": "https://studio-lune.fr/", "extrait": ""},
                          {"titre": "Local", "url": "http://127.0.0.1:8765/api/keys", "extrait": ""},
                          {"titre": "JS", "url": "javascript:alert(1)", "extrait": ""}],
            "cout_usd": 0.008, "fournisseur": fournisseur}


RW.rechercher = faux_rechercher
NOTES = []
_noter = PL.noter_reel_lignes


async def noter(lignes, usd):
    NOTES.append(usd)
    return await _noter(lignes, usd)


PL.noter_reel_lignes = noter


async def preparer():
    await init_db()
    A = E.creer({"nom": "Prospection"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    return A, cid


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)


async def carte_de(requete):
    r = await ao.executer("entreprises_rechercher", {"requete": requete, "max": 5}, ctx)
    if r["carte"]:
        await st.ajouter(cid, [fmt.nouveau_message("agent", [r["carte"]])])
    return r


print("[1] la carte")
RW.choisir("tavily")
r = asyncio.run(carte_de("studios vidéo Lyon"))
check("1a sans clé : refus dit, aucune carte", not r["ok"] and r["carte"] is None and "clé" in r["resume"], r)
settings.TAVILY_API_KEY = "tvly-x"
r = asyncio.run(carte_de("studios vidéo Lyon"))
k = r["carte"] or {}
check("1b carte « recherche » proposée, devis, fournisseur, aucun appel", r["ok"] and k.get("genre") == "recherche"
      and k.get("etat") == "proposee" and k["arguments"]["fournisseur"] == "tavily" and k["arguments"]["requete"] == "studios vidéo Lyon"
      and k["arguments"]["devis_usd"] == RW.devis("tavily") and not APPELS, k)

print("[2] décision")
n = 0
r = c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "acceptee"})
check("2a acceptée : une recherche", r.status_code == 200 and APPELS == [("studios vidéo Lyon", 5, "tavily")], r.text[:300])
fait = [m for m in r.json()["messages"] if m["role"] == "fait"][-1]["blocs"][0]["arguments"]
check("2b le fait porte les résultats et le coût", fait.get("fournisseur") == "tavily" and fait.get("cout_usd") == 0.008
      and fait["resultats"][0]["url"] == "https://studio-lune.fr/", fait)
check("2c coût réel noté", NOTES == [0.008], NOTES)
l = asyncio.run(st.lire(cid))
dep = ao._urls_deposees(l, cid)
check("2d URL publique déposée ; locale et javascript: jamais", dep == {"https://studio-lune.fr/"}, dep)
check("2e décidée deux fois : 409", c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "acceptee"}).status_code == 409
      and len(APPELS) == 1)

asyncio.run(carte_de("agences"))
r = c.post(f"/api/agent/campagnes/{cid}/carte/1", json={"decision": "refusee"})
check("3a refusée : aucun appel", r.status_code == 200 and len(APPELS) == 1)

asyncio.run(carte_de("éditeurs de jeux"))
_verif = PL.verifier


async def refuse(*a, **k):
    raise PL._refus_402({"devis": 1}) if hasattr(PL, "_refus_402") else __import__("fastapi").HTTPException(402, {"dz_plafond": {}})


PL.verifier = refuse
r = c.post(f"/api/agent/campagnes/{cid}/carte/2", json={"decision": "acceptee"})
PL.verifier = _verif
check("3b plafond : 402, aucun appel, carte encore proposée", r.status_code == 402 and len(APPELS) == 1
      and c.post(f"/api/agent/campagnes/{cid}/carte/2", json={"decision": "refusee"}).status_code == 200, r.status_code)

asyncio.run(carte_de("studios Nantes"))
settings.TAVILY_API_KEY = ""
r = c.post(f"/api/agent/campagnes/{cid}/carte/3", json={"decision": "acceptee"})
check("3c clé retirée entre-temps : 503, aucun appel", r.status_code == 503 and len(APPELS) == 1, r.status_code)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
