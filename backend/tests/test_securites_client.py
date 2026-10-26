# -*- coding: utf-8 -*-
"""t309 tâche 2 (26/10/2026) — Boîte à outils, lot A4 : le Planificateur et la fiche client appliquent les RÈGLES d'un
client (services/regles_client.py, tâche 1). Plan docs/superpowers/plans/2026-10-26-t309-securites-client.md.
Ce que ce banc garde (routes réelles, TestClient, data-dir et sqlite temporaires, aucun réseau : vérifications posées par
comptes.noter_verification, publishers.publish remplacé par un faux qui compte ses appels) :
  S1  POST dans un client `valide_par_client` : sans statut -> a_valider ; status scheduled -> 409 a_valider, rien en base.
  S2  PATCH scheduled d'un post a_valider -> 409 ; « Réponse du client » valide -> date, draft, journal par canal ; puis 200.
  S3  contenu changé d'un post validé et programmé -> a_valider, date effacée ; run_at seul -> inchangé.
  S4  `publie_en_son_nom` : confirmation nominative exigée, gardée, effacée par un changement de comptes.
  S5  canal sans consentement -> 409 consentement dans les deux modes ; /fire -> 409 sans publier.
  S6  POST /schedule/validate : le post de client non conforme est dans `skipped` avec la raison ; les autres passent.
  S7  fil : l'enfant hérite de la confirmation du parent ; parent non validé -> 409.
  S8  GET /schedule liste un post a_valider hors fenêtre ; GET /schedule/{id}/client rend les exigences sans secret.
  S9  révocation : `en_pause` = posts programmés du client (et de ses produits) sur ce canal.
  S10 Deepotus et une marque : rien ne change.
  S11 materialize_plan dans un client : aucun post `scheduled`.
Run (depuis backend/) : & $PY tests/test_securites_client.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsecc_"))
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
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import comptes as C, espaces as E, fiche_client as F, storage, marketing   # noqa: E402

_loop = asyncio.new_event_loop()


def run(coro):
    return _loop.run_until_complete(coro)


run(storage.init_db())
E.lire()


def compte(eid, plateforme, libelle, id_distant=None):
    cid = C.creer({"espace_id": eid, "plateforme": plateforme, "libelle": libelle})["id"]
    if id_distant:
        C.noter_verification(cid, {"etat": "vert", "id_distant": id_distant})
    return cid


# ---- les espaces : un client « à valider », un client « en son nom », un client à produit (S9), une marque ---------------
C1 = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
F.ecrire(C1, {"societe": "Lune SARL"})
c1x = compte(C1, "x", "X Lune", "111")
c1t = compte(C1, "telegram", "TG Lune", "222")
c1n = compte(C1, "x", "X Lune bis")                                     # jamais vérifié : jamais couvert
F.ajouter_consentement(C1, "x:111", ["publier"], "ecrit")
F.ajouter_consentement(C1, "telegram:222", ["publier"], "ecrit")

C2 = E.creer({"nom": "Garage Soleil", "type": "client"})["id"]
F.ecrire(C2, {"societe": "Soleil SAS", "mode_publication": "publie_en_son_nom"})
c2x = compte(C2, "x", "X Soleil", "333")
c2t = compte(C2, "telegram", "TG Soleil", "334")
c2n = compte(C2, "telegram", "TG Soleil bis")                           # jamais vérifié
F.ajouter_consentement(C2, "x:333", ["publier"], "ecrit")
F.ajouter_consentement(C2, "telegram:334", ["publier"], "ecrit")

C3 = E.creer({"nom": "Fleuriste Rose", "type": "client"})["id"]
P3 = E.creer({"nom": "Bouquets", "type": "produit", "parent": C3})["id"]
c3x = compte(C3, "x", "X Rose", "444")
c3t = compte(C3, "telegram", "TG Rose", "555")
p3t = compte(P3, "telegram", "TG Bouquets", "555")                      # même canal distant que c3t
F.ajouter_consentement(C3, "x:444", ["publier"], "ecrit")
F.ajouter_consentement(C3, "telegram:555", ["publier"], "ecrit")

M = E.creer({"nom": "Marque Ciel", "type": "marque"})["id"]
mx = compte(M, "x", "X Ciel", "900")

APPELS = []


async def _faux_publish(ch, cap, video, image, meta, compte=None):
    APPELS.append((ch, compte))
    raise AssertionError("aucune publication ne doit partir dans ce banc")

marketing.publishers.publish = _faux_publish

RUN = "2026-12-01T12:00:00Z"

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402

with TestClient(app, client=("127.0.0.1", 50000)) as client:
    def H(eid):
        return {"X-Dz-Espace": eid} if eid else {}

    def creer(eid, **corps):
        c = {"title": "Post", "caption": "Texte", "run_at": RUN}
        c.update(corps)
        return client.post("/api/schedule", json=c, headers=H(eid))

    def patch(pid, eid=None, **corps):
        return client.patch(f"/api/schedule/{pid}", json=corps, headers=H(eid))

    def tous():
        return client.get("/api/schedule", params={"espace": "*"}).json()

    def detail(r):
        try:
            return r.json().get("detail")
        except ValueError:
            return None

    def refus(r, code):
        d = detail(r)
        return r.status_code == 409 and isinstance(d, dict) and d.get("code") == code

    def valider(pid, eid=None, reponse="valide", moyen="ecrit"):
        return client.post(f"/api/schedule/{pid}/validation-client", json={"reponse": reponse, "moyen": moyen},
                           headers=H(eid))

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S1] POST dans un client valide_par_client")
    r = creer(C1, comptes=[c1x])
    check("S1a sans statut -> a_valider", r.status_code == 200 and r.json().get("status") == "a_valider", r.text[:300])
    check("S1b _post_to_dict rend valide_client_le et confirme_client (None)",
          r.status_code == 200 and "valide_client_le" in r.json() and r.json()["valide_client_le"] is None
          and "confirme_client" in r.json() and r.json()["confirme_client"] is None, r.text[:300])
    n_avant = len(tous())
    r = creer(C1, comptes=[c1x], status="scheduled")
    d = detail(r)
    check("S1c status scheduled -> 409 code a_valider", refus(r, "a_valider"), r.text[:300])
    check("S1d le refus nomme le client (message, client, nom, canaux)",
          isinstance(d, dict) and "Lune SARL" in (d.get("message") or "") and d.get("client") == C1
          and d.get("nom") == "Lune SARL" and isinstance(d.get("canaux"), list), repr(d))
    check("S1e rien en base", len(tous()) == n_avant, f"{n_avant} -> {len(tous())}")
    r = creer(C1, comptes=[c1x], status="draft")
    check("S1f status draft demandé -> a_valider quand même", r.json().get("status") == "a_valider", r.text[:200])

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S2] validation par le client")
    p2 = creer(C1, comptes=[c1x, c1t], caption="Pain du jour").json()
    r = patch(p2["id"], status="scheduled")
    check("S2a PATCH scheduled d'un post a_valider -> 409 a_valider", refus(r, "a_valider"), r.text[:300])
    check("S2b ... rien d'écrit (toujours a_valider)",
          next(x for x in tous() if x["id"] == p2["id"])["status"] == "a_valider")
    j_avant = len(F.lire(C1)["journal"])
    r = valider(p2["id"])
    pv = r.json().get("post") if r.status_code == 200 else {}
    check("S2c validation-client valide/ecrit -> 200, valide_client_le posé, status draft",
          r.status_code == 200 and pv.get("valide_client_le") and pv.get("status") == "draft", r.text[:300])
    nouv = F.lire(C1)["journal"][j_avant:]
    check("S2d journal : une ligne validation qui=client par canal",
          sorted(x["canal_id"] for x in nouv if x["quoi"] == "validation" and x["qui"] == "client")
          == ["telegram:222", "x:111"] and len(nouv) == 2, repr(nouv))
    r = patch(p2["id"], status="scheduled")
    check("S2e puis PATCH scheduled -> 200 scheduled", r.status_code == 200 and r.json().get("status") == "scheduled",
          r.text[:300])
    check("S2f PATCH draft d'un post NON validé -> a_valider (jamais un draft qui contourne)",
          lambda: patch(creer(C1, comptes=[c1x]).json()["id"], status="draft").json().get("status") == "a_valider")
    # erreurs de la route
    check("S2g réponse inconnue -> 400", valider(p2["id"], reponse="peut-etre").status_code == 400)
    check("S2h moyen inconnu -> 400", valider(p2["id"], moyen="pigeon").status_code == 400)
    check("S2i post inconnu -> 404", valider("nexistepas").status_code == 404)
    pdeep = creer(None, channels=["x"]).json()
    check("S2j post sans client (Deepotus) -> 409", valider(pdeep["id"]).status_code == 409)
    pc = creer(C1, comptes=[c1x]).json()
    valider(pc["id"])
    j_avant = len(F.lire(C1)["journal"])
    r = valider(pc["id"], reponse="corriger", moyen="whatsapp")
    check("S2k corriger -> valide_client_le None, a_valider",
          r.status_code == 200 and r.json()["post"]["valide_client_le"] is None
          and r.json()["post"]["status"] == "a_valider", r.text[:300])
    check("S2l corriger -> une ligne de journal validation qui=client",
          [(x["quoi"], x["canal_id"], x["qui"]) for x in F.lire(C1)["journal"][j_avant:]]
          == [("validation", "x:111", "client")], repr(F.lire(C1)["journal"][j_avant:]))

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S3] contenu changé d'un post validé et programmé")
    date_v = next(x for x in tous() if x["id"] == p2["id"])["valide_client_le"]
    r = patch(p2["id"], run_at="2026-12-02T12:00:00Z")
    check("S3a run_at seul -> toujours scheduled, date gardée",
          r.status_code == 200 and r.json()["status"] == "scheduled" and r.json()["valide_client_le"] == date_v, r.text[:300])
    r = patch(p2["id"], caption="Pain du soir")
    check("S3b caption -> valide_client_le None, a_valider",
          r.status_code == 200 and r.json()["valide_client_le"] is None and r.json()["status"] == "a_valider", r.text[:300])

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S4] publie_en_son_nom : confirmation nominative")
    r = creer(C2, comptes=[c2x])
    p4 = r.json()
    check("S4a POST sans statut -> draft (pas de validation dans ce mode)", p4.get("status") == "draft", r.text[:200])
    r = patch(p4["id"], status="scheduled")
    d = detail(r)
    check("S4b PATCH scheduled sans confirme_client -> 409 confirmation", refus(r, "confirmation"), r.text[:300])
    check("S4c le refus nomme le client et les canaux", isinstance(d, dict) and d.get("client") == C2
          and "Soleil SAS" in d.get("message", "") and "x:333" in d.get("canaux", []), repr(d))
    r = patch(p4["id"], status="scheduled", confirme_client="un-autre")
    check("S4d mauvaise valeur -> 409 confirmation", refus(r, "confirmation"), r.text[:300])
    r = patch(p4["id"], status="scheduled", confirme_client=C2)
    check("S4e bonne valeur -> 200 scheduled, confirme_client gardé",
          r.status_code == 200 and r.json()["status"] == "scheduled" and r.json()["confirme_client"] == C2, r.text[:300])
    r = patch(p4["id"], comptes=[c2x, c2t])
    check("S4f comptes changés d'un post programmé, sans confirmation -> 409, rien d'écrit",
          refus(r, "confirmation") and next(x for x in tous() if x["id"] == p4["id"])["comptes"] == [c2x], r.text[:300])
    patch(p4["id"], status="draft")
    r = patch(p4["id"], comptes=[c2x, c2t])
    check("S4g changement de comptes -> confirme_client None",
          r.status_code == 200 and r.json()["confirme_client"] is None, r.text[:300])
    r = creer(C2, comptes=[c2x], status="scheduled", confirme_client=C2)
    check("S4h POST scheduled avec la confirmation -> 200, gardée",
          r.status_code == 200 and r.json()["status"] == "scheduled" and r.json()["confirme_client"] == C2, r.text[:300])

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S5] canal sans consentement")
    p5 = creer(C1, comptes=[c1n]).json()
    valider(p5["id"])
    r = patch(p5["id"], status="scheduled")
    check("S5a valide_par_client : 409 consentement", refus(r, "consentement"), r.text[:300])
    check("S5b ... canaux = le compte non couvert", "X Lune bis" in (detail(r) or {}).get("canaux", []), r.text[:300])
    p5b = creer(C2, comptes=[c2n]).json()
    r = patch(p5b["id"], status="scheduled", confirme_client=C2)
    check("S5c publie_en_son_nom : 409 consentement", refus(r, "consentement"), r.text[:300])
    r = client.post(f"/api/schedule/{p5['id']}/fire", json={})
    check("S5d /fire -> 409 consentement", refus(r, "consentement"), r.text[:300])
    r = client.post(f"/api/schedule/{p5b['id']}/fire")
    check("S5e /fire sans corps -> 409 consentement", refus(r, "consentement"), r.text[:300])
    check("S5f aucune publication (faux publish : 0 appel)", APPELS == [], repr(APPELS))
    check("S5g le post n'est pas réclamé (pas posting)",
          next(x for x in tous() if x["id"] == p5["id"])["status"] in ("draft", "a_valider"))
    r = client.post(f"/api/schedule/{p2['id']}/fire")
    check("S5h /fire d'un post a_valider -> 409 a_valider", refus(r, "a_valider"), r.text[:300])
    r = client.post("/api/schedule/nexistepas/fire")
    check("S5i /fire d'un post inconnu -> 404", r.status_code == 404, r.text[:200])

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S6] validation par lot")
    LOT = "2027-03-01T12:00:00Z"
    pd6 = creer(None, channels=["x"], run_at=LOT, source_image="a.png").json()
    pc6 = creer(C1, comptes=[c1x], run_at=LOT, source_image="b.png").json()
    r = client.post("/api/schedule/validate", json={"from": "2027-03-01T00:00:00Z", "to": "2027-03-02T00:00:00Z"})
    js = r.json() if r.status_code == 200 else {}
    sk = {x["id"]: x for x in js.get("skipped", [])}
    check("S6a le post de Deepotus est validé", pd6["id"] in js.get("validated", []), r.text[:300])
    check("S6b le post de client non validé est dans skipped avec la raison",
          pc6["id"] in sk and "Lune SARL" in sk[pc6["id"]].get("reason", ""), r.text[:400])
    check("S6c ... et reste a_valider", next(x for x in tous() if x["id"] == pc6["id"])["status"] == "a_valider")

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S7] fil")
    par = creer(C2, comptes=[c2x], status="scheduled", confirme_client=C2).json()
    r = client.post(f"/api/schedule/{par['id']}/thread", json={"caption": "la suite"})
    check("S7a parent confirmé : l'enfant hérite de confirme_client et passe",
          r.status_code == 200 and r.json().get("confirme_client") == C2 and r.json().get("status") == "scheduled",
          r.text[:300])
    par1 = creer(C1, comptes=[c1x]).json()
    n_avant = len(tous())
    r = client.post(f"/api/schedule/{par1['id']}/thread", json={"caption": "la suite"})
    check("S7b parent non validé (valide_par_client) -> 409 a_valider, rien créé",
          refus(r, "a_valider") and len(tous()) == n_avant, r.text[:300])
    valider(par1["id"])
    r = client.post(f"/api/schedule/{par1['id']}/thread", json={"caption": "la suite"})
    check("S7c parent validé -> l'enfant hérite de la validation et passe",
          r.status_code == 200 and r.json().get("valide_client_le") and r.json().get("status") == "scheduled", r.text[:300])

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S8] liste et exigences")
    loin = creer(C1, comptes=[c1x], run_at="2031-01-01T12:00:00Z").json()
    r = client.get("/api/schedule", params={"espace": "*", "days_back": 1, "days_forward": 1})
    check("S8a un post a_valider hors fenêtre est listé", any(x["id"] == loin["id"] for x in r.json()), r.text[:200])
    r = client.get(f"/api/schedule/{loin['id']}/client")
    ex = (r.json() or {}).get("exigences") if r.status_code == 200 else None
    check("S8b GET /schedule/{id}/client -> exigences du client",
          isinstance(ex, dict) and ex.get("client") == C1 and ex.get("mode") == "valide_par_client"
          and ex.get("canaux", [{}])[0].get("canal_id") == "x:111", r.text[:300])
    check("S8c aucune clé secret/token", "secret" not in r.text.lower() and "token" not in r.text.lower(), r.text[:300])
    r = client.get(f"/api/schedule/{pdeep['id']}/client")
    check("S8d post de Deepotus -> exigences None", r.status_code == 200 and r.json() == {"exigences": None}, r.text[:200])
    check("S8e post inconnu -> 404", client.get("/api/schedule/nexistepas/client").status_code == 404)

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S9] révocation")
    ids9 = []
    for eid, cpt in ((C3, c3t), (P3, p3t), (C3, c3x)):
        p = creer(eid, comptes=[cpt]).json()
        valider(p["id"], eid)
        r = patch(p["id"], eid, status="scheduled")
        ids9.append(r.status_code)
    check("S9a trois posts programmés (deux sur telegram:555, un sur x:444)", ids9 == [200, 200, 200], repr(ids9))
    r = client.post(f"/api/espaces/{C3}/client/consentements/revoquer", json={"canal_id": "telegram:555"})
    check("S9b en_pause == 2", r.status_code == 200 and r.json().get("en_pause") == 2, r.text[:300])
    check("S9c la fiche est toujours rendue", r.status_code == 200 and "consentements" in r.json(), r.text[:200])

    # ---------------------------------------------------------------------------------------------------------------
    print("\n[S10] Deepotus et une marque : rien ne change")
    r = creer(M, comptes=[mx])
    check("S10a marque : POST -> draft", r.json().get("status") == "draft", r.text[:200])
    r = patch(r.json()["id"], status="scheduled")
    check("S10b marque : PATCH scheduled -> 200", r.status_code == 200 and r.json()["status"] == "scheduled", r.text[:200])
    r = creer(None, channels=["x"])
    check("S10c Deepotus : POST -> draft", r.json().get("status") == "draft", r.text[:200])
    r = patch(r.json()["id"], status="scheduled")
    check("S10d Deepotus : PATCH scheduled -> 200", r.status_code == 200 and r.json()["status"] == "scheduled",
          r.text[:200])
    r = creer(M, comptes=[mx], status="scheduled")
    check("S10e marque : POST scheduled -> 200", r.status_code == 200 and r.json()["status"] == "scheduled", r.text[:200])

# ---------------------------------------------------------------------------------------------------------------
print("\n[S11] materialize_plan")
PLAN = [{"title": "J1", "caption": "a", "day_offset": 0, "time": "10:00", "channels": ["x"]},
        {"title": "J2", "caption": "b", "day_offset": 1, "time": "10:00", "channels": ["x"]}]
from sqlalchemy import select                                       # noqa: E402


async def statuts(ids):
    async with storage.async_session_factory() as s:
        res = await s.execute(select(storage.ScheduledPost).where(storage.ScheduledPost.id.in_(ids)))
        return {p.id: (p.status, p.espace_id) for p in res.scalars().all()}

with E.sous_espace(C1):
    ids = run(marketing.materialize_plan(PLAN, start_date="2027-05-01"))
st = run(statuts(ids))
check("S11a client : aucun post scheduled (a_valider), dans l'espace du client",
      len(st) == 2 and all(v == ("a_valider", C1) for v in st.values()), repr(st))
with E.sous_espace(C2):
    ids = run(marketing.materialize_plan(PLAN, start_date="2027-05-01"))
st = run(statuts(ids))
check("S11b client en son nom : aucun post scheduled (draft)", len(st) == 2 and all(v[0] == "draft" for v in st.values()),
      repr(st))
with E.sous_espace(M):
    ids = run(marketing.materialize_plan(PLAN, start_date="2027-05-01"))
st = run(statuts(ids))
check("S11c marque : scheduled comme avant", len(st) == 2 and all(v[0] == "scheduled" for v in st.values()), repr(st))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
