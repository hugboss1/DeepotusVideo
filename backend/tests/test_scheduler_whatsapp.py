# -*- coding: utf-8 -*-
"""t328 tâche 4 (27/10/2026) — les diffusions WhatsApp DEPUIS LE PLANIFICATEUR : cibles, adaptateur, routes, boucle.
Plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md (tâche 4, Décisions 6-8, Review Focus 1 et 5). Faux
Kapso EN MÉMOIRE par `kapso._requete` (aucun réseau), data-dir et base temporaires, routes réelles par ASGITransport (la
boucle de fond n'est pas démarrée). Ce que ce banc garde :
  S1  un compte whatsapp de l'espace passe `verifier_cibles` (et `_poser_comptes`) ; celui d'un autre espace est refusé
  S2  routes diffusion : PUT range la config {config, audience, devis}, GET {config, audience, devis, etat}, 404 post
      inconnu, 409 post sans compte whatsapp, 403 hors boucle locale (rien d'écrit)
  S3  fire -> adaptateur -> `lancer` : post `posted`, remote_ids["whatsapp:<compte>"] = broadcast, un seul send
  S4  sans config : post `ready`, erreur claire, aucun appel Kapso de diffusion
  S5  config rangée sur un AUTRE compte que la cible du post : refus, aucune création chez Kapso
  S6  send 500 : post `ready`, erreur neutre (ni numéro, ni texte du modèle) ; second fire : aucun second send (RF1) ;
      confirmer {confirme_incertain} -> nouvelle diffusion, post `posted`
  S7  client `valide_par_client` : fire et confirmer sans validation -> 409, aucun appel Kapso ; validé -> part ;
      PUT après validation efface la validation et la diffusion ne part pas (RF5)
  S8  tick relit une diffusion `sending` ; une incertaine que Kapso tranche (`sending`) passe le post `posted` ; une
      relecture qui lève ne casse pas le tick (journal : le type seulement)
  S9  espace archivé : le tick ne lance rien
  Revue t328 tâche 4, tour 1 :
  F1  confirmer sur une diffusion non incertaine -> 409 pas_incertaine, aucun appel Kapso ; lancée hors /fire puis fire
      -> post posted avec le remote id, aucun second send
  F2  canaux par défaut d'un projet : jamais un compte whatsapp (poser_canaux l'écarte, canaux_par_defaut aussi)
  F3  402 : confirmer rend HTTP 402 dz_plafond ; fire rend 200 {ok: false}, erreur « plafond », aucun send
  F4  PUT efface aussi validated_at (assisted, draft)
  F5  relecture de fond : résumé seul tant que non terminée, pages au terme ; budget de temps par tour
  F7  GET/PUT : identités COMPTÉES (n_identites), jamais la liste
  F8  post X + WhatsApp sans config : X part, post `posted`, l'erreur WhatsApp gardée ; après PUT + fire, WhatsApp part
      seul (X pas republié) ; GET ?relire=1 lit les pages
  Revue finale t328 :
  RF-I4 client « publié en son nom » : PUT et confirmer sans confirme_client -> 409 `confirmation` (rien d'écrit) ; avec
      confirme_client = le client -> 200 (même règle que PATCH et /fire)
  RF-M1 diffusion incertaine d'un post de client tranchée par la relecture de fond : post `posted` ET ligne `publication`
      au journal du client (comme fire_post)
  RF-M5 GET : `etat.relancable` (faux pour une diffusion partie, vrai pour un failed prouvé sans envoi et soldé),
      `rien_envoye`, `reel_note`
  J1  journal sans numéro ni texte de modèle
Run (depuis backend/) : & $PY tests/test_scheduler_whatsapp.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzschwa_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "KAPSO_API_KEY"):
    os.environ[k] = ""
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                           # noqa: E402
logger.remove()
JOURNAL = _tmp / "journal.log"
logger.add(str(JOURNAL), level="DEBUG", enqueue=False)

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


from datetime import datetime, timedelta, timezone                  # noqa: E402
from sqlalchemy import select                                        # noqa: E402
from httpx import AsyncClient, ASGITransport                         # noqa: E402
from app.config import settings                                      # noqa: E402
from app.main import app                                             # noqa: E402
from app.api import routes as R                                      # noqa: E402
from app.services import comptes as CP, espaces as E, kapso as KA, pricing as PR, storage, marketing  # noqa: E402
from app.services import fiche_client as FC, whatsapp as WA          # noqa: E402
from app.services import whatsapp_diffusions as WD                   # noqa: E402

for _k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    setattr(settings, _k, "")
os.environ["KAPSO_API_KEY"] = "CLE-BANC-88"
setattr(settings, "KAPSO_API_KEY", "CLE-BANC-88")

TEXTE_MODELE = "Bonjour {{prenom}}, profitez des SOLDES-SECRETES-HIVER"
PARAM = "VALEUR-PARAM-SECRETE"


class Faux:
    def __init__(self):
        self.appels = []
        self.bc = {}
        self.send = []


F = Faux()
MODELES = [{"id": "999", "name": "promo", "language": "fr", "category": "MARKETING", "status": "APPROVED",
            "components": [{"type": "BODY", "text": TEXTE_MODELE,
                            "example": {"body_text_named_params": [{"param_name": "prenom", "example": "Ana"}]}}]}]


async def faux_requete(methode, url, *, json=None, params=None, fichiers=None):
    await asyncio.sleep(0)
    chemin = url.replace(KA.PROXY, "").replace(KA.PLATFORM, "").split("?")[0]
    F.appels.append((methode, chemin))
    if "message_templates" in chemin:
        return 200, {"data": MODELES, "paging": {}}, {}
    parts = chemin.strip("/").split("/")
    if parts[:2] != ["whatsapp", "broadcasts"]:
        return 500, {"error": "chemin inconnu du faux"}, {}
    if methode == "POST" and len(parts) == 2:
        bid = f"bc-{len(F.bc) + 1:04d}"
        F.bc[bid] = {"status": "draft", "recipients": []}
        return 201, {"data": {"id": bid, "status": "draft"}}, {}
    bid = parts[2]
    b = F.bc.get(bid)
    if b is None:
        return 404, {"error": "Broadcast not found"}, {}
    if len(parts) == 4 and parts[3] == "recipients" and methode == "POST":
        lot = json["whatsapp_broadcast"]["recipients"]
        for r in lot:
            b["recipients"].append({"phone_number": r["phone_number"].lstrip("+"), "status": "pending",
                                    "error_details": None})
        return 201, {"data": {"added": len(lot), "duplicates": 0, "errors": []}}, {}
    if len(parts) == 4 and parts[3] == "recipients" and methode == "DELETE":     # revue finale I1 : vider un brouillon
        if b["status"] != "draft":
            return 422, {"error": "Broadcast is not a draft"}, {}
        b["recipients"] = []
        return 200, {"data": {"id": bid, "status": "draft"}}, {}
    if len(parts) == 4 and parts[3] == "recipients" and methode == "GET":
        page, pp = int(params["page"]), int(params["per_page"])
        tout = b["recipients"]
        pages = max(1, -(-len(tout) // pp))
        return 200, {"data": tout[(page - 1) * pp: page * pp],
                     "meta": {"page": page, "per_page": pp, "total_pages": pages, "total_count": len(tout)}}, {}
    if len(parts) == 4 and parts[3] == "send":
        rep = F.send.pop(0) if F.send else (202, {"data": {"id": bid, "status": "sending"}})
        if rep[0] == 202:
            b["status"] = ((rep[1] or {}).get("data") or {}).get("status") or "sending"
        return rep[0], rep[1], {}
    if len(parts) == 3 and methode == "GET":
        r = b["recipients"]
        cpt = lambda s: sum(1 for x in r if x["status"] == s)       # noqa: E731
        return 200, {"data": {"id": bid, "status": b["status"], "total_recipients": len(r),
                              "pending_count": cpt("pending"), "sent_count": cpt("sent"), "failed_count": cpt("failed"),
                              "suppressed_count": cpt("suppressed"), "delivered_count": 0, "read_count": 0}}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


KA._requete = faux_requete


async def _rien(_s):
    return None
KA._dormir = _rien


def diffusions_kapso():
    """Les appels Kapso de DIFFUSION (création, destinataires, send) — les modèles et les relectures n'en sont pas."""
    return [(m, c) for m, c in F.appels if m == "POST" and "broadcasts" in c]


def sends():
    return [c for m, c in F.appels if c.endswith("/send")]


# ---- espaces, comptes ------------------------------------------------------------------------------------------------
GRILLE = {"33": {"marketing": 0.08, "utility": 0.03, "authentication": 0.03, "service": 0.01}}
E.lire()
PR.save({"whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0})


def compte_wa(eid, pid):
    cid = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
    CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": pid, "WHATSAPP_WABA_ID": "WABA-" + pid})
    WA.regler(cid, plafond_mois=100000)
    return cid


AUDIENCE = [f"tel:3361{i:07d}" for i in range(3)]


def accords(cid):
    WA._noter(cid, lambda e: e["accords"].update({i: {"date": "2026-10-01", "source": "formulaire"} for i in AUDIENCE}))


boite = E.creer({"nom": "Atelier Soleil"})["id"]
wid = compte_wa(boite, "PN-1")
wid2 = compte_wa(boite, "PN-2")
accords(wid); accords(wid2)
xid = CP.creer({"espace_id": boite, "plateforme": "x", "libelle": "X Soleil"})["id"]
ailleurs = E.creer({"nom": "Autre Maison"})["id"]
wautre = compte_wa(ailleurs, "PN-9")
# un client « validé par le client » (mode par défaut d'une fiche) : canal vérifié et consenti
cli = E.creer({"nom": "Salon Lune", "type": "client"})["id"]
FC.ecrire(cli, {"societe": "Salon Lune SARL"})
wcli = compte_wa(cli, "PN-C")
CP.noter_verification(wcli, {"etat": "vert", "id_distant": "PN-C"})
FC.ajouter_consentement(cli, "whatsapp:PN-C", ["publier", "messages"], "ecrit")
accords(wcli)
arch = E.creer({"nom": "Vieux Studio"})["id"]
warch = compte_wa(arch, "PN-A")
accords(warch)
MOD = {"modele": {"nom": "promo", "langue": "fr"}, "parametres": {"prenom": PARAM}}


async def lire_post(pid):
    async with storage.async_session_factory() as s:
        return (await s.execute(select(storage.ScheduledPost).where(storage.ScheduledPost.id == pid))).scalar_one_or_none()


def vieillir(eid, pid, secondes=120):
    """`maj` de la diffusion recule de `secondes` (a_relire attend 60 s)."""
    f = E.chemin(eid, WD.FICHIER)
    doc = json.loads(f.read_text(encoding="utf-8"))
    doc[pid]["maj"] = (datetime.now(timezone.utc) - timedelta(seconds=secondes)).isoformat()
    f.write_text(json.dumps(doc), encoding="utf-8")


async def main():
    await storage.init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async def poster(eid, comptes, **kw):
            body = {"title": "Soldes", "caption": "légende", "run_at": "2026-10-27T09:00:00Z", "espace_id": eid,
                    "comptes": comptes, **kw}
            return await c.post("/api/schedule", json=body)

        print("\n[S1] cibles")
        check("S1.1 verifier_cibles accepte un compte whatsapp de l'espace",
              lambda: CP.verifier_cibles(boite, [wid])[0]["plateforme"] == "whatsapp")
        try:
            CP.verifier_cibles(boite, [wautre]); e1 = None
        except PermissionError as e:
            e1 = e
        check("S1.2 compte whatsapp d'un autre espace : PermissionError", e1 is not None, repr(e1))
        check("S1.3 NON_PUBLIABLES retiré (branche morte), whatsapp dans CIBLES_EXPLICITES",
              not hasattr(CP, "NON_PUBLIABLES") and "whatsapp" in CP.CIBLES_EXPLICITES)
        r = await poster(boite, [wautre])
        check("S1.4 POST /api/schedule avec un compte whatsapp d'un autre espace : 409", r.status_code == 409, r.text[:200])
        r = await poster(boite, [wid])
        check("S1.5 POST /api/schedule avec le compte whatsapp de l'espace : 200, canal whatsapp",
              r.status_code == 200 and r.json()["channels"] == ["whatsapp"] and r.json()["comptes"] == [wid], r.text[:200])
        p3 = r.json()["id"] if r.status_code == 200 else "x"

        print("\n[S2] routes diffusion")
        F.appels.clear()
        r = await c.put(f"/api/schedule/{p3}/diffusion", json=MOD)
        j = r.json() if r.status_code == 200 else {}
        check("S2.1 PUT : 200 {config, audience {n}, devis}", r.status_code == 200 and j.get("audience", {}).get("n") == 3
              and abs(j.get("devis", {}).get("usd", 0) - 0.24) < 1e-9 and j.get("config", {}).get("compte") == wid,
              r.text[:300])
        check("S2.2 PUT : aucun appel de diffusion chez Kapso (devis seulement)", diffusions_kapso() == [], F.appels)
        r = await c.get(f"/api/schedule/{p3}/diffusion")
        j = r.json() if r.status_code == 200 else {}
        check("S2.3 GET : 200 {config, audience, devis, etat}", r.status_code == 200
              and set(j) >= {"config", "audience", "devis", "etat"} and j["etat"]["statut"] == "configuree"
              and j["audience"]["n"] == 3, r.text[:300])
        check("F7.1 GET : n_identites (None = toute l'audience), jamais la clé identites",
              "identites" not in j["config"] and j["config"]["n_identites"] is None, r.text[:300])
        pid7 = (await poster(boite, [wid])).json()["id"]
        r = await c.put(f"/api/schedule/{pid7}/diffusion", json={**MOD, "identites": AUDIENCE[:2]})
        g = await c.get(f"/api/schedule/{pid7}/diffusion")
        check("F7.2 PUT/GET avec une liste : n_identites = 2, aucun numéro dans les réponses",
              r.status_code == 200 and r.json()["config"]["n_identites"] == 2 and g.json()["config"]["n_identites"] == 2
              and not any(i[4:] in r.text + g.text for i in AUDIENCE), r.text[:300])
        r = await c.get("/api/schedule/inconnu-0/diffusion")
        check("S2.4 GET post inconnu : 404", r.status_code == 404, r.text[:200])
        r = await c.put("/api/schedule/inconnu-0/diffusion", json=MOD)
        check("S2.5 PUT post inconnu : 404", r.status_code == 404, r.text[:200])
        rx = await poster(boite, [xid])
        px = rx.json()["id"]
        r = await c.put(f"/api/schedule/{px}/diffusion", json=MOD)
        check("S2.6 PUT sur un post sans compte whatsapp : 409, rien rangé",
              r.status_code == 409 and WD.lire(px, boite) is None, r.text[:200])
        r = await c.put(f"/api/schedule/{p3}/diffusion", json={"modele": {"nom": "nope", "langue": "fr"},
                                                                "parametres": {}})
        check("S2.7 PUT modèle inconnu : 400", r.status_code == 400, r.text[:200])
        async with AsyncClient(transport=ASGITransport(app=app, client=("10.1.2.3", 5000)),
                               base_url="http://test") as lan:
            r1 = await lan.put(f"/api/schedule/{px}/diffusion", json=MOD)
            r2 = await lan.get(f"/api/schedule/{p3}/diffusion")
            r3 = await lan.post(f"/api/schedule/{p3}/diffusion/confirmer", json={"confirme_incertain": True})
        check("S2.8 hors boucle locale : refusé (PUT, GET, confirmer), rien rangé",
              all(x.status_code in (401, 403) for x in (r1, r2, r3)) and WD.lire(px, boite) is None,
              [x.status_code for x in (r1, r2, r3)])

        print("\n[S3] fire nominal")
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p3}/fire")
        j = r.json()
        p = await lire_post(p3)
        rid = json.loads(p.remote_ids or "{}")
        bid3 = WD.lire(p3, boite)["broadcast_id"]
        check("S3.1 fire : ok, post posted", r.status_code == 200 and j.get("ok") is True and p.status == "posted", r.text[:300])
        check("S3.2 remote_ids[whatsapp:<compte>] = broadcast", rid.get(f"whatsapp:{wid}") == bid3 and bid3, rid)
        check("S3.3 un seul send", len(sends()) == 1, F.appels)
        r = await c.post(f"/api/schedule/{p3}/fire")
        check("S3.4 second fire : déjà publié, aucun nouvel appel de diffusion", len(sends()) == 1, F.appels)
        F.appels.clear()
        r = await c.get(f"/api/schedule/{p3}/diffusion?relire=1")
        check("F8.3 GET ?relire=1 : 200, broadcast ET pages de destinataires lus, statut sending",
              r.status_code == 200 and ("GET", f"/whatsapp/broadcasts/{bid3}") in F.appels
              and ("GET", f"/whatsapp/broadcasts/{bid3}/recipients") in F.appels and r.json()["etat"]["statut"] == "sending"
              and sends() == [], (r.text[:200], F.appels))

        print("\n[S4] sans config")
        p4 = (await poster(boite, [wid])).json()["id"]
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p4}/fire")
        p = await lire_post(p4)
        check("S4.1 post ready, erreur claire", p.status == "ready" and "aucune diffusion" in (p.error or ""), (p.status, p.error))
        check("S4.2 aucun appel de diffusion chez Kapso", diffusions_kapso() == [], F.appels)

        print("\n[S5] config sur un autre compte")
        p5 = (await poster(boite, [wid])).json()["id"]
        r = await c.put(f"/api/schedule/{p5}/diffusion", json=MOD)
        r = await c.patch(f"/api/schedule/{p5}", json={"comptes": [wid2]})
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p5}/fire")
        p = await lire_post(p5)
        check("S5.1 post ready, erreur « autre compte »", p.status == "ready" and "autre compte" in (p.error or ""),
              (p.status, p.error))
        check("S5.2 aucune création chez Kapso", diffusions_kapso() == [], F.appels)

        print("\n[S6] send 500")
        p6 = (await poster(boite, [wid])).json()["id"]
        await c.put(f"/api/schedule/{p6}/diffusion", json=MOD)
        F.send = [(500, {"error": "boom"})]
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p6}/fire")
        p = await lire_post(p6)
        b6 = WD.lire(p6, boite)["broadcast_id"]
        err = p.error or ""
        check("S6.1 post ready, pas de remote id, erreur « incertaine »", p.status == "ready" and not p.remote_ids
              and "incertaine" in err, (p.status, p.remote_ids, err))
        check("S6.2 erreur neutre : ni numéro, ni texte, ni paramètre du modèle",
              not any(i[4:] in err for i in AUDIENCE) and "SOLDES" not in err and PARAM not in err, err)
        check("S6.3 un send", len(sends()) == 1, F.appels)
        r = await c.post(f"/api/schedule/{p6}/fire")
        p = await lire_post(p6)
        check("S6.4 second fire : aucun second send (RF1), refus incertain dit", len(sends()) == 1
              and p.status == "ready" and "incertain" in (p.error or ""), (F.appels, p.error))
        r = await c.post(f"/api/schedule/{p6}/diffusion/confirmer", json={"confirme_incertain": True})
        p = await lire_post(p6)
        rid = json.loads(p.remote_ids or "{}")
        nb = WD.lire(p6, boite)["broadcast_id"]
        check("S6.5 confirmer : 200, nouvelle diffusion envoyée", r.status_code == 200 and nb != b6 and len(sends()) == 2
              and r.json()["diffusion"]["incertain"] is False, r.text[:300])
        check("S6.6 … post posted, remote id = la nouvelle diffusion", p.status == "posted" and rid.get(f"whatsapp:{wid}") == nb,
              (p.status, rid))
        r = await c.post(f"/api/schedule/{p6}/diffusion/confirmer", json={"confirme_incertain": True})
        check("S6.7 confirmer une diffusion déjà partie : 409 pas_incertaine, aucun send", r.status_code == 409
              and r.json()["detail"]["code"] == "pas_incertaine" and len(sends()) == 2, r.text[:300])

        print("\n[F1] confirmer réservé à l'incertain ; lancement hors /fire")
        p10 = (await poster(boite, [wid])).json()["id"]
        await c.put(f"/api/schedule/{p10}/diffusion", json=MOD)
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p10}/diffusion/confirmer", json={"confirme_incertain": True})
        check("F1.1 confirmer sur une diffusion configurée (pas incertaine) : 409 pas_incertaine", r.status_code == 409
              and r.json()["detail"]["code"] == "pas_incertaine", r.text[:300])
        check("F1.2 … aucun appel Kapso", F.appels == [], F.appels)
        r10 = await WD.lancer(p10)                 # lancée par un autre chemin que /fire
        n_send = len(sends())
        r = await c.post(f"/api/schedule/{p10}/fire")
        p = await lire_post(p10)
        check("F1.3 fire après un lancement hors /fire : posted, remote id = la diffusion, aucun second send",
              p.status == "posted" and json.loads(p.remote_ids or "{}").get(f"whatsapp:{wid}") == r10["broadcast_id"]
              and len(sends()) == n_send, (p.status, p.remote_ids, p.error))

        print("\n[F3] 402")
        from app.services import plafonds as PF
        p12 = (await poster(boite, [wid])).json()["id"]
        await c.put(f"/api/schedule/{p12}/diffusion", json=MOD)
        PF.enregistrer({"global_usd": 0.01})
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p12}/fire")
        p = await lire_post(p12)
        check("F3.1 fire au-dessus du plafond : 200 {ok: false}, erreur « plafond », post ready",
              r.status_code == 200 and r.json()["ok"] is False and "plafond" in (p.error or "") and p.status == "ready",
              (r.text[:300], p.error))
        check("F3.2 … aucun send, la diffusion revient à configuree", sends() == []
              and WD.lire(p12, boite)["statut"] == "configuree", F.appels)
        PF.enregistrer({"global_usd": 0})
        F.send = [(500, {"error": "boom"})]
        await c.post(f"/api/schedule/{p12}/fire")
        check("F3.3 (préparation) send 500 : incertaine", WD.lire(p12, boite)["incertain"] is True)
        PF.enregistrer({"global_usd": 0.01})
        n_send = len(sends())
        r = await c.post(f"/api/schedule/{p12}/diffusion/confirmer", json={"confirme_incertain": True})
        check("F3.4 confirmer au-dessus du plafond : HTTP 402 dz_plafond, aucun send", r.status_code == 402
              and "dz_plafond" in r.json()["detail"] and len(sends()) == n_send, r.text[:300])
        PF.enregistrer({"global_usd": 0})

        print("\n[N1] confirmer qui aboutit à failed (rien envoyé, prouvé) : aucun fire_post")
        p15 = (await poster(boite, [wid])).json()["id"]
        await c.put(f"/api/schedule/{p15}/diffusion", json=MOD)
        F.send = [(500, {"error": "boom"})]
        await c.post(f"/api/schedule/{p15}/fire")
        FIRES = []
        vrai_fire = marketing.fire_post

        async def espion_fire(pid):
            FIRES.append(pid)
            return await vrai_fire(pid)
        marketing.fire_post = espion_fire
        F.send = [(202, {"data": {"status": "failed"}})]
        n_send = len(sends())
        r = await c.post(f"/api/schedule/{p15}/diffusion/confirmer", json={"confirme_incertain": True})
        marketing.fire_post = vrai_fire
        rec15 = WD.lire(p15, boite)
        p = await lire_post(p15)
        check("N1.1 confirmé -> failed prouvé sans envoi : 200, un seul send, aucun fire_post, post toujours ready",
              r.status_code == 200 and r.json()["diffusion"]["statut"] == "failed" and len(sends()) == n_send + 1
              and FIRES == [] and p.status == "ready" and rec15["rien_envoye"] is True,
              (r.text[:300], len(sends()) - n_send, FIRES, p.status))

        print("\n[F4] PUT efface validated_at")
        p13 = (await poster(boite, [wid], status="scheduled", mode="auto")).json()["id"]
        async with storage.async_session_factory() as s_:
            pp = (await s_.execute(select(storage.ScheduledPost).where(storage.ScheduledPost.id == p13))).scalar_one()
            pp.validated_at = datetime.utcnow()
            await s_.commit()
        r = await c.put(f"/api/schedule/{p13}/diffusion", json=MOD)
        p = await lire_post(p13)
        check("F4.1 PUT sur un post validé par lot : validated_at effacé, assisted, draft",
              r.status_code == 200 and p.validated_at is None and p.mode == "assisted" and p.status == "draft",
              (r.status_code, p.validated_at, p.mode, p.status))

        print("\n[F2] canaux par défaut d'un projet")
        from app.services import library_projects as LP
        pr = await LP.creer("Projet Soleil")
        A_, P_, _I, S_ = LP._t()
        async with S_() as s_:
            pj = await s_.get(P_, pr["id"])
            pj.espace_id = boite
            s_.add(A_(key=LP.cle_actif(boite), value=pr["id"]))
            await s_.commit()
        v = await LP.poser_canaux(pr["id"], [wid, xid])
        check("F2.1 poser_canaux écarte le compte whatsapp", v["canaux"] == [xid], v)
        async with S_() as s_:
            pj = await s_.get(P_, pr["id"])
            pj.canaux = json.dumps([wid, xid])        # rangé avant la règle
            await s_.commit()
        check("F2.2 canaux_par_defaut ne rend jamais un compte whatsapp", await LP.canaux_par_defaut(boite) == [xid])
        r = await c.post("/api/schedule", json={"title": "Défaut", "run_at": "2026-10-27T09:00:00Z", "espace_id": boite})
        check("F2.3 un post créé sans comptes prend les canaux du projet, sans whatsapp",
              r.status_code == 200 and r.json()["comptes"] == [xid] and r.json()["channels"] == ["x"], r.text[:300])

        print("\n[F8] post X + WhatsApp")
        from app.services import publishers as PB
        X_APPELS = []

        async def faux_x(caption, video, image, meta):
            from app.services.publishers import PublishResult
            X_APPELS.append(meta.get("post_id"))
            return PublishResult(True, "x: ok", f"tw-{len(X_APPELS)}")
        PB._REGISTRY["x"] = (lambda: True, faux_x)
        p14 = (await poster(boite, [xid, wid])).json()["id"]
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p14}/fire")
        p = await lire_post(p14)
        rid = json.loads(p.remote_ids or "{}")
        check("F8.1 sans config : X part, post posted, erreur WhatsApp gardée, aucune diffusion",
              p.status == "posted" and rid.get(f"x:{xid}") == "tw-1" and f"whatsapp:{wid}" not in rid
              and "aucune diffusion" in (p.error or "") and diffusions_kapso() == [], (p.status, rid, p.error))
        await c.put(f"/api/schedule/{p14}/diffusion", json=MOD)
        r = await c.post(f"/api/schedule/{p14}/fire")
        p = await lire_post(p14)
        rid = json.loads(p.remote_ids or "{}")
        check("F8.2 après PUT + fire : la diffusion part, X n'est pas republié", rid.get(f"whatsapp:{wid}")
              and len(X_APPELS) == 1 and p.status == "posted" and not p.error, (rid, X_APPELS, p.error))

        print("\n[S7] client valide_par_client")
        r = await poster(cli, [wcli], status="draft")
        p7 = r.json()["id"]
        check("S7.0 post du client né a_valider", r.json()["status"] == "a_valider", r.text[:200])
        r = await c.put(f"/api/schedule/{p7}/diffusion", json=MOD)
        check("S7.1 PUT (devis) permis avant validation", r.status_code == 200, r.text[:300])
        F.appels.clear()
        r = await c.post(f"/api/schedule/{p7}/fire")
        check("S7.2 fire non validé : 409 a_valider", r.status_code == 409 and r.json()["detail"]["code"] == "a_valider",
              r.text[:300])
        r = await c.post(f"/api/schedule/{p7}/diffusion/confirmer", json={"confirme_incertain": True})
        check("S7.3 confirmer non validé : 409 a_valider", r.status_code == 409 and r.json()["detail"]["code"] == "a_valider",
              r.text[:300])
        check("S7.4 aucun appel de diffusion chez Kapso", diffusions_kapso() == [], F.appels)
        r = await c.post(f"/api/schedule/{p7}/validation-client", json={"reponse": "valide", "moyen": "ecrit"})
        check("S7.5 validation client : 200", r.status_code == 200, r.text[:200])
        r = await c.put(f"/api/schedule/{p7}/diffusion", json={**MOD, "parametres": {"prenom": "autre"}})
        p = await lire_post(p7)
        check("S7.6 PUT après validation : 200, valide_client_le et confirme_client effacés (RF5)",
              r.status_code == 200 and p.valide_client_le is None and p.confirme_client is None
              and p.status == "a_valider", (r.status_code, p.valide_client_le, p.status))
        r = await c.post(f"/api/schedule/{p7}/fire")
        check("S7.7 fire après modification : 409, aucun appel de diffusion", r.status_code == 409 and diffusions_kapso() == [],
              (r.status_code, F.appels))
        await c.post(f"/api/schedule/{p7}/validation-client", json={"reponse": "valide", "moyen": "ecrit"})
        r = await c.post(f"/api/schedule/{p7}/fire")
        p = await lire_post(p7)
        check("S7.8 revalidé : fire part, post posted", r.status_code == 200 and p.status == "posted" and len(sends()) == 1,
              (r.text[:200], p.status))

        print("\n[S8] tick")
        vieillir(boite, p3)
        F.appels.clear()
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        check("S8.1 tick relit la diffusion sending (GET du broadcast)", ("GET", f"/whatsapp/broadcasts/{bid3}") in F.appels,
              F.appels)
        check("S8.2 … sans aucun envoi", sends() == [], F.appels)
        check("F5.1 non terminée : résumé seul, aucune page de destinataires",
              not any(c_.endswith("/recipients") for _m, c_ in F.appels), F.appels)
        F.bc[bid3]["status"] = "completed"
        vieillir(boite, p3)
        F.appels.clear()
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        check("F5.2 terminée : pages de destinataires lues, coût réel posé",
              ("GET", f"/whatsapp/broadcasts/{bid3}/recipients") in F.appels and WD.lire(p3, boite)["reel_note"] is True,
              F.appels)
        p8 = (await poster(boite, [wid])).json()["id"]
        await c.put(f"/api/schedule/{p8}/diffusion", json=MOD)
        F.send = [(503, {"error": "indisponible"})]
        await c.post(f"/api/schedule/{p8}/fire")
        b8 = WD.lire(p8, boite)["broadcast_id"]
        check("S8.3 send 503 : post ready, incertain", (await lire_post(p8)).status == "ready"
              and WD.lire(p8, boite)["incertain"] is True)
        F.bc[b8]["status"] = "sending"           # Kapso avait bien pris le send
        vieillir(boite, p8)
        marketing.BUDGET_RELECTURE_S = 0.0
        F.appels.clear()
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        marketing.BUDGET_RELECTURE_S = 20.0
        check("F5.3 budget épuisé : rien relu ce tour, la diffusion reste à relire",
              F.appels == [] and (p8, boite) in WD.a_relire(datetime.now(timezone.utc)), F.appels)
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        p = await lire_post(p8)
        check("S8.4 tick : Kapso tranche sending -> post posted, remote id = la diffusion",
              p.status == "posted" and json.loads(p.remote_ids or "{}").get(f"whatsapp:{wid}") == b8,
              (p.status, p.remote_ids))
        vrai = WD.relire

        async def leve(*_a, **_k):
            raise RuntimeError("panne +33610000001 SOLDES-SECRETES")
        WD.relire = leve
        vieillir(boite, p8)                      # p3 est soldée (terminée) : p8, encore sending, est à relire
        try:
            await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")]); casse = None
        except Exception as e:                  # noqa: BLE001
            casse = e
        WD.relire = vrai
        j_ = JOURNAL.read_text(encoding="utf-8")
        check("S8.5 une relecture qui lève ne casse pas le tick", casse is None, repr(casse))
        check("S8.6 … journal : le type seulement", "RuntimeError" in j_ and "+33610000001" not in j_, j_[-400:])

        print("\n[RF-I4] client publié en son nom : PUT et confirmer acceptent confirme_client")
        nom = E.creer({"nom": "Fleuriste Nom", "type": "client"})["id"]
        FC.ecrire(nom, {"societe": "Fleuriste Nom SARL", "mode_publication": "publie_en_son_nom"})
        wnom = compte_wa(nom, "PN-N")
        CP.noter_verification(wnom, {"etat": "vert", "id_distant": "PN-N"})
        FC.ajouter_consentement(nom, "whatsapp:PN-N", ["publier", "messages"], "ecrit")
        accords(wnom)
        r = await poster(nom, [wnom], status="scheduled", confirme_client=nom)
        pn = r.json()["id"] if r.status_code == 200 else "x"
        check("RF-I4.0 post programmé du client confirmé", r.status_code == 200 and r.json()["status"] == "scheduled", r.text[:300])
        r = await c.put(f"/api/schedule/{pn}/diffusion", json=MOD)
        check("RF-I4.1 PUT sans confirme_client : 409 confirmation, rien rangé",
              r.status_code == 409 and r.json()["detail"]["code"] == "confirmation" and r.json()["detail"]["client"] == nom
              and WD.lire(pn, nom) is None, r.text[:300])
        r = await c.put(f"/api/schedule/{pn}/diffusion", json={**MOD, "confirme_client": nom})
        p = await lire_post(pn)
        check("RF-I4.2 PUT avec confirme_client : 200, config rangée, confirmation gardée, post toujours programmé",
              r.status_code == 200 and WD.lire(pn, nom) is not None and p.confirme_client == nom and p.status == "scheduled",
              (r.text[:300], p.confirme_client, p.status))
        F.send = [(503, {"error": "indisponible"})]
        await c.post(f"/api/schedule/{pn}/fire")
        bn = WD.lire(pn, nom)["broadcast_id"]
        async with storage.async_session_factory() as s_:            # la confirmation du post a été perdue entre-temps
            q = (await s_.execute(select(storage.ScheduledPost).where(storage.ScheduledPost.id == pn))).scalar_one()
            q.confirme_client = None
            await s_.commit()
        F.appels.clear()
        r = await c.post(f"/api/schedule/{pn}/diffusion/confirmer", json={"confirme_incertain": True})
        check("RF-I4.3 confirmer sans confirme_client : 409 confirmation, aucun appel de diffusion",
              r.status_code == 409 and r.json()["detail"]["code"] == "confirmation" and diffusions_kapso() == [], r.text[:300])
        r = await c.post(f"/api/schedule/{pn}/diffusion/confirmer", json={"confirme_incertain": True, "confirme_client": nom})
        check("RF-I4.4 confirmer avec confirme_client : 200, diffusion relancée", r.status_code == 200
              and r.json()["diffusion"]["broadcast_id"] != bn, r.text[:300])

        print("\n[RF-M1] relecture de fond : ligne publication au journal du client")
        pm1 = (await poster(cli, [wcli], status="draft")).json()["id"]
        await c.put(f"/api/schedule/{pm1}/diffusion", json=MOD)
        await c.post(f"/api/schedule/{pm1}/validation-client", json={"reponse": "valide", "moyen": "ecrit"})
        F.send = [(503, {"error": "indisponible"})]
        await c.post(f"/api/schedule/{pm1}/fire")
        bm1 = WD.lire(pm1, cli)["broadcast_id"]
        avant = [x for x in FC.lire(cli)["journal"] if x.get("quoi") == "publication"]
        F.bc[bm1]["status"] = "sending"
        vieillir(cli, pm1)
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        p = await lire_post(pm1)
        apres = [x for x in FC.lire(cli)["journal"] if x.get("quoi") == "publication"]
        check("RF-M1.1 post posted par la relecture, une ligne publication de plus au journal du client (canal du compte)",
              p.status == "posted" and len(apres) == len(avant) + 1 and apres[-1]["canal_id"] == "whatsapp:PN-C"
              and apres[-1]["qui"] == "utilisateur", (p.status, apres[-2:]))
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        check("RF-M1.2 pas de seconde ligne au tour suivant",
              len([x for x in FC.lire(cli)["journal"] if x.get("quoi") == "publication"]) == len(apres))

        print("\n[RF-M5] GET : relancable")
        r = await c.get(f"/api/schedule/{pm1}/diffusion")
        e_ = r.json()["etat"]
        check("RF-M5.1 diffusion partie : relancable faux, rien_envoye et reel_note présents",
              e_["relancable"] is False and e_["rien_envoye"] is False and e_["reel_note"] is False, e_)
        F.bc[bm1]["status"] = "failed"
        for x in F.bc[bm1]["recipients"]:
            x["status"] = "failed"
        r = await c.get(f"/api/schedule/{pm1}/diffusion?relire=1")
        e_ = r.json()["etat"]
        check("RF-M5.2 failed prouvé sans envoi et soldé : relancable vrai", e_["statut"] == "failed"
              and e_["rien_envoye"] is True and e_["reel_note"] is True and e_["relancable"] is True, e_)

        print("\n[S9] espace archivé")
        r = await poster(arch, [warch], status="scheduled", mode="auto", run_at="2026-10-01T09:00:00Z")
        p9 = r.json()["id"]
        await c.put(f"/api/schedule/{p9}/diffusion", json=MOD)
        E.archiver(arch)
        F.appels.clear()
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        p = await lire_post(p9)
        check("S9.1 tick : le post reste scheduled, aucun appel de diffusion", p.status == "scheduled"
              and diffusions_kapso() == [], (p.status, F.appels))

        print("\n[J1] journal")
        j_ = JOURNAL.read_text(encoding="utf-8")
        check("J1.1 aucun numéro de destinataire, ni texte ni paramètre du modèle",
              not any(i[4:] in j_ for i in AUDIENCE) and "SOLDES-SECRETES-HIVER" not in j_ and PARAM not in j_
              and "CLE-BANC-88" not in j_, "")


asyncio.run(main())
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
