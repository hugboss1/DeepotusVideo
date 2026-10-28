# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, relecture finale : les défauts graves relevés, gardés.
C1 : une ligne fautive (date impossible, refus du service) ne coupe pas l'import : elle va au relevé, la suite continue.
I1 : un vrai .csv (UTF-8 ou cp1252, en-têtes usuels « Date d'inscription », « Adresse e-mail », « Consentement RGPD »)
     se dépose et s'importe.
I2 : l'e-mail retenu doit être une adresse ENTIÈRE de la page (pas un morceau).
I3 : le devis Anthropic couvre les jetons des résultats de recherche (estimation haute réaliste).
I4 : une recherche Anthropic en erreur (HTTP 200) note quand même les jetons payés.
I5 : la décision de la carte s'écrit AVANT la recherche (jamais de verrou global pendant l'appel ; une recherche en échec
     ne se rejoue pas : 409, pas de second paiement).
I6 : l'import des fiches tourne hors de la boucle (thread).
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_prospects_relecture354.py"""
import asyncio, os, pathlib, sys, tempfile, threading
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzr354_"))
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
from app.services import pricing as PR, prospects as P, prospects_score as SC, prospects_sources as PS, recherche_web as RW   # noqa: E402
from app.services.storage import init_db                                                           # noqa: E402

for m in (P, SC, PS):
    m._aujourdhui = lambda: date(2026, 10, 28)
c = TestClient(app)


async def preparer():
    await init_db()
    A = E.creer({"nom": "Prospection"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    return A, cid


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)

print("[C1] une ligne fautive ne coupe pas l'import")
r = PS.lire_csv("email,nom,date,consentement\na@a.fr,A,2026-02-30,oui\nb@b.fr,B,2026-10-01,oui\n", "liste_attente")
check("C1a date impossible : refusée au relevé par lire_csv", len(r["lignes"]) == 1 and r["refus"][0]["ligne"] == 2, r)
THREADS = []
_creer = P.creer


def creer_espion(eid, champs, qui="utilisateur"):
    THREADS.append(threading.current_thread() is threading.main_thread())
    if champs.get("nom") == "Panne":
        raise P.RefusProspect("fiche Prospects momentanément illisible : réessayez dans un instant", "indisponible")
    return _creer(eid, champs, qui)


P.creer = creer_espion
nom = asyncio.run(ao.enregistrer_depot(cid, "l.csv", "email,nom,date,consentement\np1@a.fr,Un,2026-10-01,oui\n"
                                       "p2@a.fr,Panne,2026-10-01,oui\np3@a.fr,Trois,2026-10-01,oui\n"))
r = asyncio.run(ao.executer("prospects_chercher", {"source": "depot", "depot": nom[:-4], "origine": "liste_attente"}, ctx))
P.creer = _creer
check("C1b refus du service sur une ligne : relevé, les autres créées", r["ok"] and r["donnees"]["crees"] == 2
      and any(x["ligne"] == 3 for x in r["donnees"]["refus"]), r)
check("I6 la création tourne hors de la boucle (thread)", THREADS and not any(THREADS), THREADS)

print("[I1] un vrai .csv se dépose")
corps = "Prénom;Nom;Adresse e-mail;Téléphone portable;Date d'inscription;Consentement RGPD\nLéa;Martin;lea@studio-lune.fr;+33611111111;2026-10-20;Oui\n"
r = c.post(f"/api/agent/campagnes/{cid}/depot", files={"fichier": ("liste.csv", corps.encode("cp1252"), "text/csv")})
check("I1a .csv cp1252 accepté", r.status_code == 200, r.text[:200])
dep = (r.json() or {}).get("depot") or (r.json() or {}).get("nom") or ""
txt = ao._texte_depot(asyncio.run(st.lire(cid)), cid, dep[:-4] if dep.endswith(".txt") else (dep or "liste"))
check("I1b décodé sans casse (Prénom, Téléphone)", "Prénom" in txt and "Téléphone" in txt, txt[:120])
r = PS.lire_csv(txt, "liste_attente")
L = r["lignes"]
check("I1c en-têtes usuels reconnus : e-mail, téléphone, date, consentement", len(L) == 1 and L[0]["nom"] == "Léa Martin"
      and {"type": "telephone", "valeur": "+33611111111"} in L[0]["canaux"] and L[0]["source"]["date"] == "2026-10-20", r)

print("[I2] adresse entière de la page")
ao._telecharger = lambda url: asyncio.sleep(0, result="Écrivez à contact@studio-lyon.fr pour un devis.")
ao._url_sure = lambda u: None
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte": "https://studio-lyon.fr/contact"}])]))
for faux in ("t@studio-lyon.fr", "contact@studio-lyon.f", "lyon"):
    r = asyncio.run(ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://studio-lyon.fr/contact",
                                                       "fiche": {"entreprise": "Studio Lyon", "email": faux}}, ctx))
    check(f"I2 « {faux} » refusé", not r["ok"], r["resume"])
r = asyncio.run(ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://studio-lyon.fr/contact",
                                                   "fiche": {"entreprise": "Studio Lyon", "email": "Contact@Studio-Lyon.fr"}}, ctx))
check("I2 l'adresse entière (casse libre) acceptée", r["ok"], r["resume"])

print("[I3] devis Anthropic réaliste")
jetons = PR.estimate({"kind": "llm", "provider": "anthropic", "modele": RW._modele(), "in_tok": 30000, "out_tok": 1500})["total_usd"]
check("I3 le devis couvre 2 recherches + 30 000 jetons d'entrée", RW.devis("anthropic") >= 2 * RW.PRIX["anthropic"] + jetons,
      (RW.devis("anthropic"), jetons))

print("[I4] erreur Anthropic : jetons notés")
settings.ANTHROPIC_API_KEY = "sk-x"


async def poste_erreur(url, h, b):
    return 200, {"content": [{"type": "web_search_tool_result", "content": {"type": "web_search_tool_result_error", "error_code": "unavailable"}}],
                 "usage": {"input_tokens": 5000, "output_tokens": 100}}


RW._POST = poste_erreur
try:
    asyncio.run(RW.rechercher("x", 5, "anthropic")); e = None
except RW.RechercheEchouee as x:
    e = x
check("I4 l'erreur porte le coût des jetons", e is not None and getattr(e, "cout_usd", 0) > 0, getattr(e, "cout_usd", None))

print("[I5] décision écrite avant la recherche ; échec non rejouable")
VU = []


async def rech(q, n=5, f=None):
    l = await st.lire(cid)
    VU.append(any(m["role"] == "fait" and m["blocs"][0].get("genre") == "recherche" for m in l["messages"]))
    raise RW.RechercheEchouee("tavily a refusé la recherche (HTTP 500)", 0.0)


RW.rechercher = rech
RW.choisir("tavily")
settings.TAVILY_API_KEY = "tvly"
k = asyncio.run(ao.executer("entreprises_rechercher", {"requete": "studios"}, ctx))["carte"]
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
l = asyncio.run(st.lire(cid))
from app.api.agent_campagnes_routes import _cartes                   # noqa: E402
n = len(_cartes(l["messages"])) - 1
r = c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "acceptee"})
check("I5a la décision est écrite avant l'appel", VU == [True], VU)
check("I5b échec : dit (502)", r.status_code == 502, r.status_code)
r = c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "acceptee"})
check("I5c pas de second paiement : 409, aucun nouvel appel", r.status_code == 409 and len(VU) == 1, (r.status_code, VU))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
