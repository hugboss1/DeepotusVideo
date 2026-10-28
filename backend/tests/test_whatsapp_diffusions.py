# -*- coding: utf-8 -*-
"""t328 tâche 3 (27/10/2026) — service `whatsapp_diffusions` : configurer, lancer, relire, a_relire.
Plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md (Décisions 1-7, Review Focus 1-4). Faux Kapso EN
MÉMOIRE par `kapso._requete` (aucun réseau), data-dir et base temporaires. Ce que ce banc garde :
  C1  configurer : modèle inconnu ou paramètres faux -> ValueError ; config rangée, audience {n, ecartes}, devis par marché
      sans réservation (aucune Depense) ; audience vide -> n = 0, config rangée quand même
  N1  nominal 2 500 destinataires : 3 lots (1000/1000/500), numéros « +chiffres », composants Meta, nom dz-<post>-…,
      id Meta du modèle, `errors` lus en 201 et `duplicates` comptés, UN send, devis réservé une fois (une ligne par
      marché, ref = broadcast), statut `sending`, compteur du mois + n
  N2  second lancer / configurer après lancement -> refus `deja_lancee`, aucun appel Kapso
  I1  send 500 -> incertain, réservation gardée ; second lancer sans confirmation -> relecture (GET) puis refus 409
      `incertain` si Kapso dit `draft`, jamais de second send ; confirmé -> nouvelle diffusion, ancienne réservation à 0
  I2  send en panne réseau puis Kapso dit `sending` -> lancer rend l'état, incertain levé, aucun second send
  R1  send 422 -> KapsoErreur, réservation remise à 0, statut `echec` ; relançable
  R2  send 429 -> un seul essai, réservation à 0, statut `configuree`, pas incertain
  V1  audience vide -> refus `accord`, aucun appel Kapso, rien de réservé
  P1  plafond du mois -> refus `plafond`, aucun appel Kapso
  E1  espace archivé -> ValueError, aucun appel Kapso ; config absente -> ValueError
  L1  relire : toutes les pages, compteurs, `suppressed` et 131050 -> désinscription (absents de l'audience suivante),
      coût réel = Σ marché sent × prix, posé une seule fois (statut terminal)
  A1  a_relire : non terminées dont `maj` a plus de 60 s
  J1  journal sans numéro ni texte de modèle (fichier de log temporaire)
Run (depuis backend/) : & $PY tests/test_whatsapp_diffusions.py"""
import asyncio, json, os, pathlib, re, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwadif_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["KAPSO_API_KEY"] = ""
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
from app.config import settings                                      # noqa: E402
from app.services import comptes as CP, espaces as E, kapso as KA, plafonds as PF, pricing as PR, storage  # noqa: E402
from app.services import whatsapp as WA                              # noqa: E402
from app.services import whatsapp_diffusions as WD                   # noqa: E402

os.environ["KAPSO_API_KEY"] = "CLE-BANC-77"
setattr(settings, "KAPSO_API_KEY", "CLE-BANC-77")
BOUCLE = asyncio.new_event_loop()
run = BOUCLE.run_until_complete
run(storage.init_db())

TEXTE_MODELE = "Bonjour {{prenom}}, profitez des SOLDES-SECRETES-ETE"
PARAM = "VALEUR-PARAM-SECRETE"


class Faux:
    def __init__(self):
        self.appels = []            # (méthode, chemin)
        self.lots = []              # tailles des lots de destinataires
        self.crees = []             # corps de création
        self.bc = {}                # id -> {status, recipients: [dict]}
        self.send = []              # réponses de send à servir : (statut, corps) ou "reseau"
        self.erreurs_lot = {}       # n° de lot (1..) -> (errors, duplicates)
        self.n_lots = 0
        self.lot_panne = None       # n° de lot qui répond 422
        self.get_panne = set()      # broadcasts dont le GET répond 500
        self.sans_sent = set()      # broadcasts dont le GET omet `sent_count`
        self.pendant = None         # fabrique de coroutine lancée au premier lot de destinataires
        self.tache = None
        self.vider = []             # revue finale I1 : réponses du DELETE …/recipients à servir : (statut, corps) ou fonction
        self.get_404 = set()        # revue finale M9 : broadcasts dont le GET répond 404 (supprimés chez Kapso)


F = Faux()
MODELES = [{"id": "999", "name": "promo", "language": "fr", "category": "MARKETING", "status": "APPROVED",
            "components": [{"type": "BODY", "text": TEXTE_MODELE,
                            "example": {"body_text_named_params": [{"param_name": "prenom", "example": "Ana"}]}}]},
           {"id": "", "name": "sansid", "language": "fr", "category": "MARKETING", "status": "APPROVED", "components": []},
           # revue finale M4 : modèles non diffusables
           {"id": "777", "name": "code", "language": "fr", "category": "AUTHENTICATION", "status": "APPROVED",
            "components": [{"type": "BODY", "text": "Votre code : {{1}}"}]},
           {"id": "778", "name": "entete", "language": "fr", "category": "MARKETING", "status": "APPROVED",
            "components": [{"type": "HEADER", "format": "TEXT", "text": "Salut {{1}}"},
                           {"type": "BODY", "text": "Les soldes"}]}]


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
        F.crees.append(json)
        F.bc[bid] = {"status": "draft", "recipients": []}
        return 201, {"data": {"id": bid, "status": "draft"}}, {}
    bid = parts[2]
    b = F.bc.get(bid)
    if b is None or bid in F.get_404:
        return 404, {"error": "Broadcast not found"}, {}
    if len(parts) == 4 and parts[3] == "recipients" and methode == "DELETE":
        if F.vider:
            rep = F.vider.pop(0)
            rep = rep(b) if callable(rep) else rep
            if rep is not None:
                return rep[0], rep[1], {}
        if b["status"] not in ("draft", "scheduled"):        # relevé §2 : vidage permis en brouillon et en planifié
            return 422, {"error": "Broadcast is not a draft"}, {}
        b["status"] = "draft"
        b["recipients"] = []
        return 200, {"data": {"id": bid, "status": "draft", "total_recipients": 0}}, {}
    if len(parts) == 4 and parts[3] == "recipients" and methode == "POST":
        lot = json["whatsapp_broadcast"]["recipients"]
        if len(lot) > 1000:
            return 422, {"error": "too many"}, {}
        F.n_lots += 1
        if F.n_lots == F.lot_panne:
            return 422, {"error": "Broadcast is importing"}, {}
        if F.pendant is not None:                 # un geste concurrent lancé PENDANT le lancement (en vol)
            F.tache, F.pendant = asyncio.ensure_future(F.pendant()), None
            await asyncio.sleep(0.01)
        F.lots.append(len(lot))
        errs, dups = F.erreurs_lot.get(F.n_lots, ([], 0))
        for r in lot:
            b["recipients"].append({"phone_number": r["phone_number"].lstrip("+"), "status": "pending",
                                    "components": r.get("components"), "error_details": None})
        return 201, {"data": {"added": len(lot) - len(errs) - dups, "duplicates": dups, "errors": errs}}, {}
    if len(parts) == 4 and parts[3] == "recipients" and methode == "GET":
        page, pp = int(params["page"]), int(params["per_page"])
        tout = b["recipients"]
        pages = max(1, -(-len(tout) // pp))
        return 200, {"data": tout[(page - 1) * pp: page * pp],
                     "meta": {"page": page, "per_page": pp, "total_pages": pages, "total_count": len(tout)}}, {}
    if len(parts) == 4 and parts[3] == "send":
        rep = F.send.pop(0) if F.send else (202, {"data": {"id": bid, "status": "sending"}})
        if rep == "reseau":
            raise ConnectionError("panne https://api.kapso.ai/x?token=JETON")
        if rep[0] == 202:
            b["status"] = ((rep[1] or {}).get("data") or {}).get("status") or "sending"
        return rep[0], rep[1], {}
    if methode == "GET" and bid in F.get_panne:
        return 500, {"error": "boom"}, {}
    if len(parts) == 3 and methode == "GET":
        r = b["recipients"]
        cpt = lambda s: sum(1 for x in r if x["status"] == s)       # noqa: E731
        d = {"id": bid, "status": b["status"], "total_recipients": len(r), "pending_count": cpt("pending"),
             "sent_count": cpt("sent"), "failed_count": cpt("failed"),
             "suppressed_count": cpt("suppressed"), "delivered_count": 0, "read_count": 0}
        if bid in F.sans_sent:                    # Kapso omet `sent_count`
            d.pop("sent_count")
        return 200, {"data": d}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


KA._requete = faux_requete


async def _rien(_s):
    return None
KA._dormir = _rien


def refus(coro):
    try:
        run(coro)
    except WA.WhatsappRefus as e:
        return e.code
    except Exception as e:                      # noqa: BLE001
        return f"autre:{type(e).__name__}:{e}"
    return None


def leve(coro, exc):
    try:
        run(coro)
    except exc as e:
        return e
    except Exception as e:                      # noqa: BLE001
        return None
    return None


def depenses(ref=None):
    async def f():
        async with storage.async_session_factory() as s:
            q = select(storage.Depense)
            if ref is not None:
                q = q.where(storage.Depense.ref == ref)
            return (await s.execute(q.order_by(storage.Depense.id))).scalars().all()
    return run(f())


def creer_post(pid, eid):
    async def f():
        async with storage.async_session_factory() as s:
            s.add(storage.ScheduledPost(id=pid, title="Soldes", caption="x", channels="whatsapp", status="scheduled",
                                        mode="auto", run_at=datetime.utcnow(), espace_id=eid))
            await s.commit()
    run(f())


GRILLE = {"33": {"marketing": 0.08, "utility": 0.03, "authentication": 0.03, "service": 0.01},
          "44": {"marketing": 0.05, "utility": 0.02, "authentication": 0.02, "service": 0.01}}
E.lire()
PR.save({"whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0})
boite = E.creer({"nom": "Atelier Soleil"})["id"]
cid = CP.creer({"espace_id": boite, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": "PN-1", "WHATSAPP_WABA_ID": "WABA-1"})
WA.regler(cid, plafond_mois=100000)
FR = [f"tel:3361{i:07d}" for i in range(2000)]
UK = [f"tel:4471{i:07d}" for i in range(500)]
STOPPE = "tel:33699999999"
WA._noter(cid, lambda e: (e["accords"].update({i: {"date": "2026-10-01", "source": "formulaire"} for i in FR + UK + [STOPPE]}),
                          e["stops"].__setitem__(STOPPE, "2026-10-02")))
MOIS = WA._mois(datetime.now(timezone.utc))
MOD = {"nom": "promo", "langue": "fr"}
for p in [f"post-{i}" for i in range(1, 14)]:
    creer_post(p, boite)

print("\n[C1] configurer")
check("C1.1 modèle inconnu -> ValueError", leve(WD.configurer("post-1", cid, modele={"nom": "nope", "langue": "fr"},
                                                               parametres={"prenom": "x"}, identites=None), ValueError))
check("C1.2 paramètres faux -> ValueError", leve(WD.configurer("post-1", cid, modele=MOD, parametres=["a", "b"],
                                                               identites=None), ValueError))
check("C1.3 modèle sans id Meta -> ValueError", leve(WD.configurer("post-1", cid, modele={"nom": "sansid", "langue": "fr"},
                                                                   parametres=[], identites=None), ValueError))
check("C1.4 rien rangé après un refus", WD.lire("post-1", boite) is None)
res = run(WD.configurer("post-1", cid, modele=MOD, parametres={"prenom": PARAM}, identites=None))
check("C1.5 audience 2 500, stop écarté", res["audience"]["n"] == 2500 and res["audience"]["ecartes"]["stop"] == 1, res["audience"])
check("C1.6 devis : une ligne par marché, 2000 x 0,08 + 500 x 0,05",
      len(res["devis"]["lignes"]) == 2 and abs(res["devis"]["usd"] - (160 + 25)) < 1e-6, res["devis"])
cfg = WD.lire("post-1", boite)
check("C1.7 config rangée", cfg and cfg["compte"] == cid and cfg["modele"]["meta_id"] == "999"
      and cfg["modele"]["categorie"] == "marketing" and cfg["statut"] == "configuree" and cfg["identites"] is None, cfg)
check("C1.8 aucune réservation au devis", depenses() == [])
check("C1.9 fichier d'espace whatsapp_diffusions.json", (_tmp / "espaces" / boite / "whatsapp_diffusions.json").is_file()
      or E.chemin(boite, "whatsapp_diffusions.json").is_file())
vide = run(WD.configurer("post-4", cid, modele=MOD, parametres={"prenom": PARAM}, identites=[STOPPE]))
check("C1.10 audience vide -> n = 0, config rangée", vide["audience"]["n"] == 0 and WD.lire("post-4", boite) is not None, vide)
check("C1.11 audience vide : les écartés restent comptés", (vide["audience"]["ecartes"] or {}).get("stop") == 1, vide["audience"])

print("\n[N1] nominal 2 500")
F.erreurs_lot = {2: (["Recipient 7: invalid phone number format"], 2)}
F.appels.clear()
r = run(WD.lancer("post-1"))
bid = r["broadcast_id"]
check("N1.1 rendu {broadcast_id, statut, n, incertain}", r["statut"] == "sending" and r["incertain"] is False
      and r["n"] == 2497 and bid == "bc-0001", r)
check("N1.2 trois lots 1000/1000/500", F.lots == [1000, 1000, 500], F.lots)
rec0 = F.bc[bid]["recipients"][0]
check("N1.3 numéro « +chiffres » envoyé, composants Meta du modèle", F.bc[bid]["recipients"][0]["phone_number"] == FR[0][4:]
      and rec0["components"] == [{"type": "body", "parameters": [{"type": "text", "parameter_name": "prenom", "text": PARAM}]}],
      rec0)
cr = F.crees[0]["whatsapp_broadcast"]
check("N1.4 création : nom dz-<post>-…, numéro, id Meta", cr["name"].startswith("dz-post-1-") and cr["phone_number_id"] == "PN-1"
      and cr["whatsapp_template_id"] == "999", cr)
check("N1.5 un seul send", sum(1 for m, c in F.appels if c.endswith("/send")) == 1)
dp = depenses(bid)
check("N1.6 devis réservé une fois : 2 lignes (marchés), ref = broadcast", len(dp) == 2 and len(depenses()) == 2
      and sorted(round(d.estime_usd, 4) for d in dp) == [25.0, 160.0] and all(d.categorie == "whatsapp" for d in dp),
      [(d.estime_usd, d.ref) for d in dp])
rec = WD.lire("post-1", boite)
check("N1.7 ajout : errors lus en 201, duplicates comptés", rec["ajout"] == {"ajoutes": 2497, "doublons": 2, "erreurs": 1}, rec.get("ajout"))
check("N1.8 enregistrement : broadcast, statut, lignes par marché", rec["broadcast_id"] == bid and rec["statut"] == "sending"
      and not rec["incertain"] and sorted(l["marche"] for l in rec["lignes"]) == ["33", "44"], rec)
check("N1.9 compteur du mois + n", WA.etat(cid)["compteur"][MOIS]["sortants"] == 2497, WA.etat(cid)["compteur"])

print("\n[N2] déjà lancée")
n0 = len(F.appels)
check("N2.1 second lancer -> deja_lancee", refus(WD.lancer("post-1")) == "deja_lancee")
check("N2.2 configurer après lancement -> deja_lancee", refus(WD.configurer("post-1", cid, modele=MOD, parametres={"prenom": "y"},
                                                                         identites=None)) == "deja_lancee")
check("N2.3 aucun appel Kapso", len(F.appels) == n0, F.appels[n0:])
check("N2.4 config intacte", WD.lire("post-1", boite)["parametres"] == {"prenom": PARAM})

print("\n[I1] send 500 -> incertain")
PETIT = FR[:3]
run(WD.configurer("post-2", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
F.send = [(500, {"error": "boom"})]
F.appels.clear()
r = run(WD.lancer("post-2"))
b2 = r["broadcast_id"]
check("I1.1 incertain, statut envoi", r["incertain"] is True and r["statut"] == "envoi", r)
d2 = depenses(b2)
check("I1.2 réservation gardée (réel vide)", len(d2) == 1 and d2[0].reel_usd is None and abs(d2[0].estime_usd - 0.24) < 1e-9,
      [(d.estime_usd, d.reel_usd) for d in d2])
check("I1.6 configurer refusé tant qu'incertain (pas encore relue)", refus(WD.configurer("post-2", cid, modele=MOD,
                                                                        parametres={"prenom": "b"}, identites=PETIT)) == "deja_lancee")
F.appels.clear()
check("I1.3 second lancer sans confirmation (Kapso : draft) -> incertain", refus(WD.lancer("post-2")) == "incertain")
check("I1.4 … après une relecture GET, sans aucun send", ("GET", f"/whatsapp/broadcasts/{b2}") in F.appels
      and not any(c.endswith("/send") for _m, c in F.appels), F.appels)
check("I1.5 toujours incertain", WD.lire("post-2", boite)["incertain"] is True)
F.appels.clear()
r = run(WD.lancer("post-2", confirme_incertain=True))
check("I1.7 confirmé -> nouvelle diffusion envoyée", r["broadcast_id"] != b2 and r["statut"] == "sending"
      and r["incertain"] is False and sum(1 for _m, c in F.appels if c.endswith("/send")) == 1, r)
check("I1.8 ancienne réservation remise à 0 (Kapso disait draft)", depenses(b2)[0].reel_usd == 0.0)
check("I1.9 nouvelle réservation sur le nouveau broadcast", len(depenses(r["broadcast_id"])) == 1)
i_del = F.appels.index(("DELETE", f"/whatsapp/broadcasts/{b2}/recipients")) if ("DELETE", f"/whatsapp/broadcasts/{b2}/recipients") in F.appels else -1
i_cre = F.appels.index(("POST", "/whatsapp/broadcasts")) if ("POST", "/whatsapp/broadcasts") in F.appels else -1
check("I1.10 revue finale : l'ancien brouillon est VIDÉ avant la création de la relance", 0 <= i_del < i_cre
      and F.bc[b2]["recipients"] == [], F.appels)

for p_ in [f"post-{i}" for i in range(18, 27)]:
    creer_post(p_, boite)

print("\n[I3] revue finale I1 : draft relu puis Kapso prend l'envoi au moment de la confirmation")
run(WD.configurer("post-18", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1600:1603]))
F.send = [(500, {"error": "boom"})]
b18 = run(WD.lancer("post-18"))["broadcast_id"]
check("I3.1 relu draft -> attente de confirmation", refus(WD.lancer("post-18")) == "incertain"
      and WD.lire("post-18", boite)["attente_confirmation"] is True)


def _prise(b):                                  # Kapso a pris le send entre la relecture et le vidage
    b["status"] = "sending"
    return 422, {"error": "Broadcast is not a draft"}
F.vider = [_prise]
F.appels.clear()
r = run(WD.lancer("post-18", confirme_incertain=True))
rec18 = WD.lire("post-18", boite)
check("I3.2 vidage refusé 422 : AUCUNE relance (ni création, ni send)",
      not any(c.endswith("/send") for _m, c in F.appels) and ("POST", "/whatsapp/broadcasts") not in F.appels, F.appels)
check("I3.3 la diffusion est relue et suivie normalement : sending, plus incertaine, même broadcast",
      r["broadcast_id"] == b18 and r["statut"] == "sending" and r["incertain"] is False
      and rec18["attente_confirmation"] is False and rec18["broadcast_id"] == b18, (r, rec18))
check("I3.4 réservation gardée (sera soldée au réel au terme)", depenses(b18)[0].reel_usd is None)
check("I3.5 suivie par la relecture de fond",
      "post-18" in {p for p, _e in WD.a_relire(datetime.now(timezone.utc) + timedelta(seconds=120))})

print("\n[I4] revue finale I1 : panne au vidage -> aucune relance")
run(WD.configurer("post-19", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1610:1612]))
F.send = [(500, {"error": "boom"})]
b19 = run(WD.lancer("post-19"))["broadcast_id"]
refus(WD.lancer("post-19"))
F.vider = [(503, {"error": "indisponible"})]
F.appels.clear()
check("I4.1 confirmation refusée « incertain »", refus(WD.lancer("post-19", confirme_incertain=True)) == "incertain")
check("I4.2 ni création ni send", not any(c.endswith("/send") for _m, c in F.appels)
      and ("POST", "/whatsapp/broadcasts") not in F.appels, F.appels)
rec19 = WD.lire("post-19", boite)
check("I4.3 toujours incertaine, réservation gardée", rec19["incertain"] is True and rec19["broadcast_id"] == b19
      and depenses(b19)[0].reel_usd is None, rec19)

print("\n[M3] revue finale : reconfigurer une diffusion en attente de confirmation")
run(WD.configurer("post-20", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1620:1622]))
F.send = [(500, {"error": "boom"})]
b20 = run(WD.lancer("post-20"))["broadcast_id"]
refus(WD.lancer("post-20"))
F.appels.clear()
res20 = run(WD.configurer("post-20", cid, modele=MOD, parametres={"prenom": "neuf"}, identites=FR[1620:1622]))
rec20 = WD.lire("post-20", boite)
check("M3.1 brouillon vidé, réservation soldée à 0", ("DELETE", f"/whatsapp/broadcasts/{b20}/recipients") in F.appels
      and F.bc[b20]["recipients"] == [] and depenses(b20)[0].reel_usd == 0.0, F.appels)
check("M3.2 config neuve rangée, plus incertaine", rec20["statut"] == "configuree" and rec20["incertain"] is False
      and rec20["attente_confirmation"] is False and rec20["parametres"] == {"prenom": "neuf"}, rec20)
check("M3.3 relancée normalement", run(WD.lancer("post-20"))["broadcast_id"] != b20)
run(WD.configurer("post-21", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1630:1632]))
F.send = [(500, {"error": "boom"})]
b21 = run(WD.lancer("post-21"))["broadcast_id"]
refus(WD.lancer("post-21"))
F.vider = [_prise]
check("M3.4 Kapso a pris l'envoi : reconfiguration refusée deja_lancee",
      refus(WD.configurer("post-21", cid, modele=MOD, parametres={"prenom": "b"}, identites=None)) == "deja_lancee")
rec21 = WD.lire("post-21", boite)
check("M3.5 … diffusion relue et suivie, réservation gardée", rec21["statut"] == "sending" and rec21["incertain"] is False
      and rec21["parametres"] == {"prenom": "a"} and depenses(b21)[0].reel_usd is None, rec21)
run(WD.configurer("post-22", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1640:1642]))
F.send = [(500, {"error": "boom"})]
run(WD.lancer("post-22"))
F.vider = []
refus(WD.lancer("post-22"))
F.vider = [(500, {"error": "boom"})]
check("M3.6 panne au vidage : reconfiguration refusée incertain, rien ne change",
      refus(WD.configurer("post-22", cid, modele=MOD, parametres={"prenom": "b"}, identites=None)) == "incertain"
      and WD.lire("post-22", boite)["attente_confirmation"] is True)
F.vider = []

print("\n[M4] revue finale : modèles non diffusables refusés")
F.appels.clear()
check("M4.1 catégorie authentication -> refus modele", refus(WD.configurer("post-23", cid, modele={"nom": "code", "langue": "fr"},
                                                                         parametres=["1"], identites=None)) == "modele")
check("M4.2 en-tête texte variable -> refus modele", refus(WD.configurer("post-23", cid, modele={"nom": "entete", "langue": "fr"},
                                                                        parametres=[], identites=None)) == "modele")
check("M4.3 rien rangé, aucun appel de diffusion", WD.lire("post-23", boite) is None
      and not any("broadcasts" in c for _m, c in F.appels), F.appels)

print("\n[I2] panne réseau puis Kapso dit sending")
run(WD.configurer("post-3", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
F.send = ["reseau"]
r = run(WD.lancer("post-3"))
b3 = r["broadcast_id"]
check("I2.1 panne réseau -> incertain", r["incertain"] is True, r)
F.bc[b3]["status"] = "sending"
F.appels.clear()
r = run(WD.lancer("post-3"))
check("I2.2 relu : sending -> incertain levé, état rendu", r["incertain"] is False and r["statut"] == "sending"
      and r["broadcast_id"] == b3, r)
check("I2.3 aucun second send, aucune création", not any(c.endswith("/send") for _m, c in F.appels)
      and not any(m == "POST" and c == "/whatsapp/broadcasts" for m, c in F.appels), F.appels)
check("I2.4 réservation gardée", depenses(b3)[0].reel_usd is None)

print("\n[R1] send 422")
run(WD.configurer("post-5", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
F.send = [(422, {"error": "Broadcast has no recipients"})]
e = leve(WD.lancer("post-5"), KA.KapsoErreur)
rec5 = WD.lire("post-5", boite)
check("R1.1 KapsoErreur 422", e is not None and e.statut == 422, e)
check("R1.2 réservation remise à 0", all(d.reel_usd == 0.0 for d in depenses(rec5["broadcast_id"])) and depenses(rec5["broadcast_id"]))
check("R1.3 statut echec, pas incertain", rec5["statut"] == "echec" and rec5["incertain"] is False, rec5)
r = run(WD.lancer("post-5"))
check("R1.4 relançable", r["statut"] == "sending", r)

print("\n[R2] send 429")
run(WD.configurer("post-6", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
F.send = [(429, {"error": "rate"}), (202, {"data": {"status": "sending"}})]
F.appels.clear()
e = leve(WD.lancer("post-6"), KA.KapsoErreur)
rec6 = WD.lire("post-6", boite)
check("R2.1 429 : un seul essai", e is not None and sum(1 for _m, c in F.appels if c.endswith("/send")) == 1, F.appels)
check("R2.2 réservation à 0, statut configuree, pas incertain", rec6["statut"] == "configuree" and rec6["incertain"] is False
      and all(d.reel_usd == 0.0 for d in depenses(rec6["broadcast_id"])), rec6)

print("\n[V1] audience vide")
F.appels.clear()
nd = len(depenses())
check("V1.1 refus accord", refus(WD.lancer("post-4")) == "accord")
check("V1.2 aucun appel Kapso, rien réservé", F.appels == [] and len(depenses()) == nd, F.appels)

print("\n[P1] plafond du mois")
run(WD.configurer("post-7", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
WA.regler(cid, plafond_mois=10)
F.appels.clear()
check("P1.1 refus plafond", refus(WD.lancer("post-7")) == "plafond")
check("P1.2 aucun appel Kapso", F.appels == [], F.appels)
WA.regler(cid, plafond_mois=100000)

print("\n[E1] espace archivé, config absente")
autre = E.creer({"nom": "Autre"})["id"]
check("E1.1 config absente -> ValueError", leve(WD.lancer("post-inconnu-de-config"), (ValueError, KeyError)) is not None)
E.archiver(boite, True)
F.appels.clear()
check("E1.2 espace archivé -> ValueError", isinstance(leve(WD.lancer("post-7"), ValueError), ValueError))
check("E1.3 aucun appel Kapso", F.appels == [])
E.archiver(boite, False)

print("\n[L1] relire")
rs = F.bc[bid]["recipients"]
SUPP = [rs[5]["phone_number"], rs[2100]["phone_number"], rs[6]["phone_number"]]
for x in rs:
    x["status"] = "sent"
rs[5]["status"] = rs[2100]["status"] = rs[6]["status"] = "suppressed"
for x in (rs[5], rs[2100], rs[6]):
    x["error_details"] = {"code": "marketing_preference_stopped"}
rs[10].update(status="failed", error_details={"code": 131050, "message": "x"})
rs[11].update(status="failed", error_details={"code": 131026})
F.bc[bid]["status"] = "sending"
appels_reel = []
_nrl = PF.noter_reel_lignes


async def _espion(ids, usd):
    appels_reel.append((list(ids), usd))
    return await _nrl(ids, usd)
PF.noter_reel_lignes = _espion
F.appels.clear()
v0 = run(WD.relire("post-1", boite))
# t328 tâche 4, revue point 5 : non terminée -> le résumé seul (GET du broadcast), aucune page ni désinscription
check("L1.0 relecture de fond non terminée : résumé seul, compteurs à jour, aucune page",
      not any(c.endswith("/recipients") for m, c in F.appels) and v0["compteurs"]["suppressed"] == 3
      and appels_reel == [], F.appels)
F.appels.clear()
v = run(WD.relire("post-1", boite, complet=True))          # relecture explicite (route ?relire=1)
pages = [c for m, c in F.appels if c.endswith("/recipients")]
check("L1.1 toutes les pages lues", len(pages) == -(-len(rs) // 100), len(pages))
check("L1.2 compteurs", v["compteurs"]["suppressed"] == 3 and v["compteurs"]["failed"] == 2, v.get("compteurs"))
e_ = WA.etat(cid)
check("L1.3 suppressed et 131050 -> désinscrits", all(f"tel:{n}" in e_["desinscrits_marketing"] for n in SUPP + [rs[10]["phone_number"]])
      and f"tel:{rs[11]['phone_number']}" not in e_["desinscrits_marketing"], len(e_["desinscrits_marketing"]))
check("L1.4 non terminal : coût réel pas encore posé", appels_reel == [], appels_reel)
aud = WA.audience_diffusion(cid, categorie="marketing")
check("L1.5 audience suivante sans les désinscrits", not any(f"tel:{n}" in aud["retenus"] for n in SUPP)
      and aud["ecartes"]["marketing"] == 4, aud["ecartes"])
F.bc[bid]["status"] = "completed"
v = run(WD.relire("post-1", boite))
sent33 = sum(1 for x in rs if x["status"] == "sent" and x["phone_number"].startswith("33"))
sent44 = sum(1 for x in rs if x["status"] == "sent" and x["phone_number"].startswith("44"))
reel = {round(d.reel_usd, 4) for d in depenses(bid)}
check("L1.6 terminal : coût réel par marché = sent x prix", v["statut"] == "completed"
      and reel == {round(sent33 * 0.08, 4), round(sent44 * 0.05, 4)}, (reel, sent33, sent44))
run(WD.relire("post-1", boite))
check("L1.7 posé une seule fois", len(appels_reel) == 2, appels_reel)
PF.noter_reel_lignes = _nrl

print("\n[A1] a_relire")
maintenant = datetime.now(timezone.utc)
_lire_es = E.lire


def _interdit():
    raise AssertionError("espaces.lire() appelé par a_relire")
E.lire = _interdit
try:
    liste = WD.a_relire(maintenant + timedelta(seconds=120))
    check("A1.0 revue finale I3 : a_relire ne passe jamais par espaces.lire() (lecture seule du disque)", True)
except AssertionError as x:
    liste = []
    check("A1.0 revue finale I3 : a_relire ne passe jamais par espaces.lire() (lecture seule du disque)", False, str(x))
E.lire = _lire_es
check("A1.1 sending ancien (post-2, post-3, post-5, post-18, post-20, post-21) relu ; terminée, non lancée et en attente absentes",
      {p for p, _e in liste} == {"post-2", "post-3", "post-5", "post-18", "post-20", "post-21"} and all(e == boite for _p, e in liste), liste)
check("A1.2 maj récente (< 60 s) : rien", WD.a_relire(maintenant) == [], WD.a_relire(maintenant))

print("\n[K1] deux lancer simultanés")
from fastapi import HTTPException                                    # noqa: E402
run(WD.configurer("post-8", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
F.appels.clear()
async def _deux():
    return await asyncio.gather(WD.lancer("post-8"), WD.lancer("post-8"), return_exceptions=True)
res = run(_deux())
check("K1.1 un seul send, une seule création", sum(1 for _m, c in F.appels if c.endswith("/send")) == 1
      and sum(1 for m, c in F.appels if m == "POST" and c == "/whatsapp/broadcasts") == 1, F.appels)
check("K1.2 l'un part, l'autre est refusé deja_lancee", sum(1 for x in res if isinstance(x, dict) and x["statut"] == "sending") == 1
      and sum(1 for x in res if isinstance(x, WA.WhatsappRefus) and x.code == "deja_lancee") == 1, res)

cid2 = CP.creer({"espace_id": boite, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cid2, {"WHATSAPP_PHONE_ID": "PN-2", "WHATSAPP_WABA_ID": "WABA-2"})
creer_post("post-14", boite)
run(WD.configurer("post-14", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
F.appels.clear()


async def _croises():
    F.pendant = lambda: WD.configurer("post-14", cid2, modele=MOD, parametres={"prenom": "z"}, identites=None)
    r0 = await WD.lancer("post-14")
    r1 = await asyncio.gather(F.tache, return_exceptions=True)
    return [r0, r1[0]]
res = run(_croises())
rec14 = WD.lire("post-14", boite)
check("K1.3 configurer par un AUTRE compte pendant le lancement : refusé, diffusion suivie",
      isinstance(res[1], WA.WhatsappRefus) and res[1].code == "deja_lancee" and rec14["compte"] == cid
      and rec14["broadcast_id"] == res[0]["broadcast_id"] and rec14["statut"] == "sending", (res, rec14))

print("\n[K2] 402 du plafond")
run(WD.configurer("post-9", cid, modele=MOD, parametres={"prenom": "a"}, identites=PETIT))
_ver = PF.verifier


async def _refus402(*a, **k):
    raise HTTPException(402, {"dz_plafond": {"motif": "global"}})
PF.verifier = _refus402
F.appels.clear()
nd = len(depenses())
e = leve(WD.lancer("post-9"), HTTPException)
PF.verifier = _ver
rec9 = WD.lire("post-9", boite)
check("K2.1 402 remonte, aucun send", e is not None and e.status_code == 402 and not any(c.endswith("/send") for _m, c in F.appels))
check("K2.2 rien réservé", len(depenses()) == nd)
check("K2.3 retour à configuree (relançable)", rec9["statut"] == "configuree" and rec9["incertain"] is False, rec9)
check("K2.4 relancé : part", run(WD.lancer("post-9"))["statut"] == "sending")

print("\n[K3] panne pendant l'ajout des destinataires")
run(WD.configurer("post-10", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[100:1600]))
F.lot_panne = F.n_lots + 2
F.appels.clear()
nd = len(depenses())
e = leve(WD.lancer("post-10"), KA.KapsoErreur)
F.lot_panne = None
rec10 = WD.lire("post-10", boite)
check("K3.1 KapsoErreur, aucun send, rien réservé", e is not None and not any(c.endswith("/send") for _m, c in F.appels)
      and len(depenses()) == nd, F.appels)
check("K3.2 état cohérent : configuree, lot partiel noté", rec10["statut"] == "configuree" and rec10["incertain"] is False
      and rec10["ajout"]["ajoutes"] == 1000, rec10)
check("K3.3 relancé : part", run(WD.lancer("post-10"))["statut"] == "sending")

print("\n[K4] re-revue O1 : relance confirmée SANS relecture possible -> l'ancienne est vidée d'abord, jamais parquée")
VIEUX = FR[1700:1703]
run(WD.configurer("post-11", cid, modele=MOD, parametres={"prenom": "a"}, identites=VIEUX))
F.send = [(500, {"error": "boom"})]
b_old = run(WD.lancer("post-11"))["broadcast_id"]
F.get_panne = {b_old}
F.appels.clear()
r = run(WD.lancer("post-11", confirme_incertain=True))
rec11 = WD.lire("post-11", boite)
_del = ("DELETE", f"/whatsapp/broadcasts/{b_old}/recipients")
check("K4.1 relecture en panne : l'ancienne est VIDÉE avant la création de la relance, aucune ancienne parquée",
      r["broadcast_id"] != b_old and r["statut"] == "sending" and F.bc[b_old]["recipients"] == []
      and _del in F.appels and F.appels.index(_del) < F.appels.index(("POST", "/whatsapp/broadcasts"))
      and rec11["anciennes"] == [], (F.appels, rec11.get("anciennes")))
check("K4.2 ancienne réservation soldée à 0 (vidée : rien ne partira)", depenses(b_old)[0].reel_usd == 0.0)
F.get_panne = set()
for p_ in [f"post-{i}" for i in range(27, 33)]:
    creer_post(p_, boite)
# relecture en panne + vidage en panne -> refus, ni création ni send
run(WD.configurer("post-27", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1710:1712]))
F.send = [(500, {"error": "boom"})]
b27 = run(WD.lancer("post-27"))["broadcast_id"]
F.get_panne = {b27}
F.vider = [(503, {"error": "indisponible"})]
F.appels.clear()
check("K4.3 relecture et vidage en panne : refus incertain", refus(WD.lancer("post-27", confirme_incertain=True)) == "incertain")
check("K4.4 … ni création ni send, réservation gardée", ("POST", "/whatsapp/broadcasts") not in F.appels
      and not any(c.endswith("/send") for _m, c in F.appels) and depenses(b27)[0].reel_usd is None, F.appels)
F.get_panne, F.vider = set(), []
# Kapso montre `scheduled` (ni tranché ni brouillon) : vidé (repasse draft) puis relance
run(WD.configurer("post-28", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1720:1722]))
F.send = [(500, {"error": "boom"})]
b28 = run(WD.lancer("post-28"))["broadcast_id"]
F.bc[b28]["status"] = "scheduled"
F.appels.clear()
r = run(WD.lancer("post-28", confirme_incertain=True))
check("K4.5 statut scheduled : vidé d'abord (repassé brouillon), puis relance", r["broadcast_id"] != b28
      and F.bc[b28]["recipients"] == [] and F.bc[b28]["status"] == "draft"
      and ("DELETE", f"/whatsapp/broadcasts/{b28}/recipients") in F.appels and depenses(b28)[0].reel_usd == 0.0, F.appels)
# relecture en panne et vidage 422 : aucune relance, suivie
run(WD.configurer("post-29", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1730:1732]))
F.send = [(500, {"error": "boom"})]
b29 = run(WD.lancer("post-29"))["broadcast_id"]
F.get_panne = {b29}
F.vider = [(422, {"error": "Broadcast is not a draft"})]
F.appels.clear()
r = run(WD.lancer("post-29", confirme_incertain=True))
F.get_panne = set()
check("K4.6 relecture en panne, vidage 422 : AUCUNE relance, même broadcast, toujours suivie",
      r["broadcast_id"] == b29 and ("POST", "/whatsapp/broadcasts") not in F.appels
      and "post-29" in {p for p, _e in WD.a_relire(datetime.now(timezone.utc) + timedelta(seconds=120))}, (r, F.appels))

print("\n[N1] re-revue : un 404 au vidage ne vaut « vidé » que si la diffusion est introuvable")
run(WD.configurer("post-30", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1740:1742]))
F.send = [(500, {"error": "boom"})]
b30 = run(WD.lancer("post-30"))["broadcast_id"]
F.vider = [(404, {"error": "Not found"})]
F.appels.clear()
check("N1.1 DELETE 404 mais GET lisible : refus incertain, aucune relance",
      refus(WD.lancer("post-30", confirme_incertain=True)) == "incertain" and ("POST", "/whatsapp/broadcasts") not in F.appels
      and depenses(b30)[0].reel_usd is None, F.appels)
F.get_404.add(b30)
r = run(WD.lancer("post-30", confirme_incertain=True))
F.get_404.discard(b30)
check("N1.2 DELETE 404 et GET 404 : diffusion disparue, soldée à 0, relance", r["broadcast_id"] != b30
      and depenses(b30)[0].reel_usd == 0.0, r)

print("\n[N2] re-revue : après un vidage refusé (422), jamais « en attente de confirmation »")
run(WD.configurer("post-31", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1750:1752]))
F.send = [(500, {"error": "boom"})]
b31 = run(WD.lancer("post-31"))["broadcast_id"]
refus(WD.lancer("post-31"))                       # relu draft -> attente
F.vider = [(422, {"error": "Broadcast is not a draft"})]          # Kapso montre encore draft, mais a pris l'envoi
r = run(WD.lancer("post-31", confirme_incertain=True))
rec31 = WD.lire("post-31", boite)
check("N2.1 vidage 422 : pas en attente, toujours incertaine, suivie, réservation gardée",
      rec31["attente_confirmation"] is False and rec31["incertain"] is True and rec31["broadcast_id"] == b31
      and "post-31" in {p for p, _e in WD.a_relire(datetime.now(timezone.utc) + timedelta(seconds=120))}
      and depenses(b31)[0].reel_usd is None, rec31)
run(WD.relire("post-31", boite))
check("N2.2 relecture suivante (Kapso dit encore draft) : toujours pas « en attente »",
      WD.lire("post-31", boite)["attente_confirmation"] is False)
F.bc[b31]["status"] = "sending"
run(WD.relire("post-31", boite))
rec31 = WD.lire("post-31", boite)
check("N2.3 Kapso tranche (sending) : plus incertaine, drapeau levé", rec31["incertain"] is False
      and rec31["statut"] == "sending" and "vidage_refuse" not in rec31, rec31)

print("\n[K4L] anciennes héritées (avant la re-revue) : relues jusqu'à leur terme, soldées")


def parquer(post):
    WD._modifier(boite, post, lambda r_: {**r_, "anciennes": [{"broadcast_id": r_["broadcast_id"], "lignes": r_["lignes"]}],
                                          "broadcast_id": None, "statut": "configuree", "lignes": [], "incertain": False})


run(WD.configurer("post-32", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1760:1763]))
b_vieux = run(WD.lancer("post-32"))["broadcast_id"]
parquer("post-32")
check("K4L.1 a_relire suit les anciennes",
      "post-32" in {p for p, _e in WD.a_relire(datetime.now(timezone.utc) + timedelta(seconds=120))})
ro = F.bc[b_vieux]["recipients"]
F.bc[b_vieux]["status"] = "completed"
ro[0]["status"] = "sent"
ro[1].update(status="suppressed", error_details={"code": "marketing_preference_stopped"})
ro[2].update(status="failed", error_details={"code": "131050"})
run(WD.relire("post-32", boite))
e_ = WA.etat(cid)
check("K4L.2 ancienne soldée : 1 sent x 0,08", abs(depenses(b_vieux)[0].reel_usd - 0.08) < 1e-9, depenses(b_vieux)[0].reel_usd)
check("K4L.3 désinscriptions de l'ancienne captées", f"tel:{ro[1]['phone_number']}" in e_["desinscrits_marketing"]
      and f"tel:{ro[2]['phone_number']}" in e_["desinscrits_marketing"])
check("K4L.4 retirée des anciennes", WD.lire("post-32", boite)["anciennes"] == [])
b24 = run(WD.lancer("post-32"))["broadcast_id"]       # une seconde, encore brouillon chez Kapso
F.bc[b24]["status"] = "draft"
parquer("post-32")
F.vider = [_prise]
run(WD.relire("post-32", boite))
check("K4b.1 ancienne draft, vidage 422 : reste suivie, réservation gardée",
      [a["broadcast_id"] for a in WD.lire("post-32", boite)["anciennes"]] == [b24] and depenses(b24)[0].reel_usd is None)
F.bc[b24]["status"] = "draft"
run(WD.relire("post-32", boite))
check("K4b.2 vidée : soldée à 0 et retirée", WD.lire("post-32", boite)["anciennes"] == [] and depenses(b24)[0].reel_usd == 0.0
      and F.bc[b24]["recipients"] == [], WD.lire("post-32", boite)["anciennes"])

print("\n[M9] revue finale : diffusion supprimée chez Kapso (404 persistant)")
run(WD.configurer("post-25", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1660:1662]))
b25 = run(WD.lancer("post-25"))["broadcast_id"]
F.get_404.add(b25)
e1 = leve(WD.relire("post-25", boite), KA.KapsoErreur)
e2 = leve(WD.relire("post-25", boite), KA.KapsoErreur)
check("M9.1 deux 404 : l'erreur remonte, toujours suivie", e1 is not None and e2 is not None and e2.statut == 404
      and WD.lire("post-25", boite)["statut"] == "sending" and WD.lire("post-25", boite)["echecs_404"] == 2)
v25 = run(WD.relire("post-25", boite))
rec25 = WD.lire("post-25", boite)
check("M9.2 au 3e : introuvable, plus incertaine", v25["statut"] == "introuvable" and rec25["statut"] == "introuvable"
      and rec25["incertain"] is False, rec25)
check("M9.3 plus suivie en fond, pas une publication",
      "post-25" not in {p for p, _e in WD.a_relire(datetime.now(timezone.utc) + timedelta(seconds=120))}
      and WD.deja_prise(rec25) is False)
check("M9.4 réservation gardée comme estimation", depenses(b25)[0].reel_usd is None)
check("M9.5 ni relançable ni reconfigurable", refus(WD.lancer("post-25")) == "deja_lancee")
F.appels.clear()
run(WD.relire("post-25", boite))
check("M9.6 une relecture explicite ne rappelle plus Kapso", F.appels == [], F.appels)
F.get_404.discard(b25)
logger.complete()
check("M9.7 une seule ligne « introuvable » au journal", JOURNAL.read_text(encoding="utf-8").count(f"broadcast {b25} : introuvable") == 1)

print("\n[K5] incertain + draft : attente de confirmation")
run(WD.configurer("post-12", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1800:1802]))
F.send = [(500, {"error": "boom"})]
run(WD.lancer("post-12"))
check("K5.1 refus incertain", refus(WD.lancer("post-12")) == "incertain")
check("K5.2 attente_confirmation posée", WD.lire("post-12", boite)["attente_confirmation"] is True)
check("K5.3 a_relire ne la sonde plus",
      "post-12" not in {p for p, _e in WD.a_relire(datetime.now(timezone.utc) + timedelta(seconds=120))})
run(WD.lancer("post-12", confirme_incertain=True))
check("K5.4 confirmée : attente levée", WD.lire("post-12", boite)["attente_confirmation"] is False)

print("\n[K6] Kapso failed")
run(WD.configurer("post-13", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1900:1902]))
b13 = run(WD.lancer("post-13"))["broadcast_id"]
F.bc[b13]["status"] = "failed"
for x in F.bc[b13]["recipients"]:
    x["status"] = "failed"
run(WD.relire("post-13", boite))
r = run(WD.lancer("post-13"))
check("K6.1 failed sans aucun envoi : relançable", r["statut"] == "sending" and r["broadcast_id"] != b13, r)
b13b = r["broadcast_id"]
F.bc[b13b]["status"] = "failed"
F.bc[b13b]["recipients"][0]["status"] = "sent"
run(WD.relire("post-13", boite))
check("K6.2 failed avec des envois : définitif", refus(WD.lancer("post-13")) == "deja_lancee")
for p in ("post-15", "post-16", "post-17"):
    creer_post(p, boite)
# compteur `sent` ABSENT mais une ligne `sent` : aucune preuve que rien n'est parti -> définitif
run(WD.configurer("post-15", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1910:1912]))
b15 = run(WD.lancer("post-15"))["broadcast_id"]
F.sans_sent.add(b15)
F.bc[b15]["status"] = "failed"
F.bc[b15]["recipients"][0]["status"] = "sent"
F.bc[b15]["recipients"][1]["status"] = "failed"
run(WD.relire("post-15", boite))
check("K6.3 compteur absent, une ligne sent : définitif", refus(WD.lancer("post-15")) == "deja_lancee"
      and WD.lire("post-15", boite)["rien_envoye"] is False)
# compteur ABSENT, relecture complète sans aucune ligne `sent` : prouvé -> relançable
run(WD.configurer("post-16", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1920:1922]))
b16 = run(WD.lancer("post-16"))["broadcast_id"]
F.sans_sent.add(b16)
F.bc[b16]["status"] = "failed"
for x in F.bc[b16]["recipients"]:
    x["status"] = "failed"
check("K6.4 failed non relu : définitif (aucune preuve)", refus(WD.lancer("post-16")) == "deja_lancee")
run(WD.relire("post-16", boite))
check("K6.5 compteur absent, relecture complète sans sent : relançable", run(WD.lancer("post-16"))["broadcast_id"] != b16)

print("\n[K8] send 2xx déjà failed")
run(WD.configurer("post-17", cid, modele=MOD, parametres={"prenom": "a"}, identites=FR[1930:1932]))
F.send = [(202, {"data": {"status": "failed"}})]
r = run(WD.lancer("post-17"))
b17 = r["broadcast_id"]
rec17 = WD.lire("post-17", boite)
check("K8.1 relu et soldé aussitôt : compteurs, reel_note, réservation à 0", r["statut"] == "failed"
      and rec17["compteurs"].get("total") == 2 and rec17["reel_note"] is True and rec17["rien_envoye"] is True
      and [d.reel_usd for d in depenses(b17)] == [0.0], (rec17, [d.reel_usd for d in depenses(b17)]))
r2 = run(WD.lancer("post-17"))
check("K8.2 puis relançable, l'ancienne réservation reste soldée", r2["broadcast_id"] != b17 and r2["statut"] == "sending"
      and [d.reel_usd for d in depenses(b17)] == [0.0], r2)

print("\n[K7] fichier illisible")
fd = E.chemin(boite, "whatsapp_diffusions.json")
sain = fd.read_bytes()
fd.write_text("{oups", encoding="utf-8")
F.appels.clear()
check("K7.1 lancer refusé", isinstance(leve(WD.lancer("post-7"), ValueError), WD.FichierIllisible))
check("K7.2 configurer refusé", isinstance(leve(WD.configurer("post-7", cid, modele=MOD, parametres={"prenom": "a"},
                                                              identites=PETIT), ValueError), WD.FichierIllisible))
check("K7.3 relire refusé", isinstance(leve(WD.relire("post-1", boite), ValueError), WD.FichierIllisible))
check("K7.4 lecture d'affichage : vide, a_relire sans erreur", WD.lire("post-1", boite) is None
      and WD.a_relire(datetime.now(timezone.utc)) == [])
check("K7.5 fichier jamais remis à zéro ni déplacé, aucun appel Kapso", fd.read_text(encoding="utf-8") == "{oups"
      and F.appels == [], F.appels)
logger.complete()
check("K7.6 fichier illisible signalé UNE fois au journal (pas à chaque lecture)",
      JOURNAL.read_text(encoding="utf-8").count("illisible dans l'espace") == 1)
fd.write_bytes(sain)

print("\n[J1] journal")
logger.complete()
texte = JOURNAL.read_text(encoding="utf-8")
check("J1.1 le journal parle des diffusions", "bc-0001" in texte and "post-1" in texte, texte[-500:])
check("J1.2 aucun numéro", re.search(r"\d{9,}", texte) is None, re.findall(r".{20}\d{9,}.{5}", texte)[:3])
check("J1.3 aucun texte de modèle ni paramètre", "SOLDES-SECRETES" not in texte and PARAM not in texte)
check("J1.4 aucune clé ni jeton", "CLE-BANC-77" not in texte and "JETON" not in texte)

print(f"\n{ok} OK, {fail} KO")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
