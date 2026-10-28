# -*- coding: utf-8 -*-
"""t355 (28/10/2026) — Veille & prospection P4, tâches 2-3 : les OUTILS de séquence de l'agent et leurs ROUTES.
`sequence_proposer` rend une carte « sequence » (porte 2, le tour s'arrête), refuse un mot interdit de l'espace ;
`sequence_planifier` refuse une séquence non validée ; la carte acceptée valide (l'utilisateur), refusée annule, décidée
deux fois : 409. Routes /api/prospects/{eid}/sequences… : lister, valider, planifier, annuler, marquer envoyé.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_agent_sequences.py"""
import asyncio, os, pathlib, sys, tempfile
from datetime import date, datetime, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzaseq355_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
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
from app.services import agent_boites as B, agent_format as fmt, agent_outils as ao, agent_store as st   # noqa: E402
from app.services import espaces as E, prospects as P, prospects_score as SC, prospects_sequences as S    # noqa: E402
from app.services.storage import init_db                                                               # noqa: E402

for m in (P, SC):
    m._aujourdhui = lambda: date(2026, 10, 28)
S._maintenant = lambda: datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc)


async def interdits(eid):
    return ["gratuit"], ["promo"]


ao._mots_interdits = interdits
c = TestClient(app)


async def preparer():
    await init_db()
    A = E.creer({"nom": "Prospection"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    return A, cid


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)
SRC = {"type": "web", "url": "https://studio-lune.fr", "date": "2026-10-20"}
pid = P.creer(A, {"nom": "Studio Lune", "entreprise": "Studio Lune", "source": SRC, "base_legale": "interet_legitime_b2b",
                  "canaux": [{"type": "email", "valeur": "contact@studio-lune.fr"}, {"type": "x", "valeur": "@studiolune"}]})["id"]
P.changer_statut(A, pid, "qualifie")
ETAPES = [{"objet": "Vos vidéos", "texte": "Bonjour, une idée pour vos vidéos.", "delai_jours": 0},
          {"objet": "Relance", "texte": "Je reviens vers vous.", "delai_jours": 4}]


def outil(nom, args):
    return asyncio.run(ao.executer(nom, args, ctx))


print("[1] boîte, format, définitions")
check("1a deux outils de séquence dans la boîte prospects", {"sequence_proposer", "sequence_planifier"} <= set(B.outils_pour("campagnes")))
check("1b aucun outil ne valide à la place de l'utilisateur", not any("valider" in n for n in ao.OUTILS))
check("1c genre de carte « sequence »", "sequence" in fmt.GENRES_CARTE)
check("1d sequence_proposer est une carte, sequence_planifier une écriture",
      ao.OUTILS["sequence_proposer"]["nature"] == "carte" and ao.OUTILS["sequence_planifier"]["nature"] == "ecriture")

print("[2] sequence_proposer")
r = outil("sequence_proposer", {"pid": pid, "canal": "email", "etapes": ETAPES})
k = r.get("carte") or {}
a = k.get("arguments") or {}
check("2a carte « sequence » proposée, le tour s'arrête", r["ok"] and k.get("genre") == "sequence" and k.get("etat") == "proposee"
      and "arrête" in r["resume"], r)
check("2b la carte porte la séquence, le canal et les textes", a.get("sid", "").startswith("sq_") and a.get("canal") == "email"
      and a.get("pid") == pid and [e["texte"] for e in a.get("etapes") or []] == [e["texte"] for e in ETAPES], a)
check("2c la carte est valide au format v1", not fmt.valider(fmt.nouveau_message("agent", [k])))
r2 = outil("sequence_proposer", {"pid": pid, "canal": "email", "etapes": [dict(ETAPES[0], texte="Essai gratuit")]})
check("2d mot interdit du persona refusé", not r2["ok"] and "gratuit" in r2["resume"], r2)
r2 = outil("sequence_proposer", {"pid": pid, "canal": "email", "etapes": [dict(ETAPES[0], objet="Promo")]})
check("2e mot interdit du brief actif refusé", not r2["ok"] and "promo" in r2["resume"].lower(), r2)
r2 = outil("sequence_proposer", {"pid": pid, "canal": "whatsapp", "etapes": [{"texte": "x", "delai_jours": 0}]})
check("2f canal sans accord refusé", not r2["ok"] and "canal" in r2["resume"], r2)

print("[3] sequence_planifier avant et après la porte")
r3 = outil("sequence_planifier", {"sid": a["sid"]})
check("3a non validée : refus", not r3["ok"] and "valid" in r3["resume"], r3)
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [k])]))
from app.api.agent_campagnes_routes import _cartes                   # noqa: E402
n = len(_cartes(asyncio.run(st.lire(cid))["messages"])) - 1
r = c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "acceptee"})
check("3b carte acceptée : 200, séquence validée par l'utilisateur", r.status_code == 200
      and [s for s in S.lister(A, pid) if s["id"] == a["sid"]][0]["statut"] == "validee", r.text[:200])
check("3c décidée deux fois : 409", c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "acceptee"}).status_code == 409)
r3 = outil("sequence_planifier", {"sid": a["sid"]})
check("3d validée : planifiée, dates rendues", r3["ok"] and len(r3["donnees"]["etapes"]) == 2 and r3["donnees"]["etapes"][0]["quand"], r3)
r3 = outil("sequence_planifier", {"sid": "sq_00000000"})
check("3e séquence inconnue : refus", not r3["ok"], r3)

print("[4] carte refusée : annulée")
kx = outil("sequence_proposer", {"pid": pid, "canal": "x", "etapes": [{"texte": "Bonjour", "delai_jours": 0}]})["carte"]
asyncio.run(st.ajouter(cid, [fmt.nouveau_message("agent", [kx])]))
n = len(_cartes(asyncio.run(st.lire(cid))["messages"])) - 1
r = c.post(f"/api/agent/campagnes/{cid}/carte/{n}", json={"decision": "refusee"})
check("4a refusée : séquence annulée", r.status_code == 200
      and [s for s in S.lister(A, pid) if s["id"] == kx["arguments"]["sid"]][0]["statut"] == "annulee", r.text[:200])

print("[5] routes")
r = c.get(f"/api/prospects/{A}/sequences", params={"pid": pid})
check("5a GET liste (avec « due » et « ouvrir »)", r.status_code == 200 and len(r.json()["sequences"]) == 2, r.text[:200])
kx = outil("sequence_proposer", {"pid": pid, "canal": "x", "etapes": [{"texte": "Bonjour", "delai_jours": 0}]})["carte"]
sid = kx["arguments"]["sid"]
check("5b planifier non validée : 409", c.post(f"/api/prospects/{A}/sequences/{sid}/planifier", json={}).status_code == 409)
check("5c valider : 200", c.post(f"/api/prospects/{A}/sequences/{sid}/valider").json()["statut"] == "validee")
r = c.post(f"/api/prospects/{A}/sequences/{sid}/planifier", json={"debut": "demain"})
check("5d date illisible : 422 avec message", r.status_code == 422 and r.json()["detail"]["code"] == "champ", r.text[:200])
r = c.post(f"/api/prospects/{A}/sequences/{sid}/planifier", json={})
check("5e planifier : 200", r.status_code == 200 and r.json()["statut"] == "planifiee", r.text[:200])
r = c.post(f"/api/prospects/{A}/sequences/{sid}/etapes/0/envoye")
check("5f marquer envoyé : 200, séquence terminée", r.status_code == 200 and r.json()["statut"] == "terminee", r.text[:200])
check("5g la fiche est contactée", P.lire(A, pid)["statut"] == "contacte")
check("5h étape e-mail : 409 (envoi automatique)", c.post(f"/api/prospects/{A}/sequences/{a['sid']}/etapes/0/envoye").status_code == 409)
check("5i annuler : 200", c.post(f"/api/prospects/{A}/sequences/{a['sid']}/annuler").json()["statut"] == "annulee")
check("5j séquence inconnue : 404", c.post(f"/api/prospects/{A}/sequences/sq_00000000/valider").status_code == 404)
check("5k espace inconnu : 404", c.get("/api/prospects/es_inconnu00/sequences").status_code == 404)
check("5l étape illisible : 404", c.post(f"/api/prospects/{A}/sequences/{sid}/etapes/9/envoye").status_code in (404, 409))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
