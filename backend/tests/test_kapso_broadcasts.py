# -*- coding: utf-8 -*-
"""t328 (27/10/2026) — Tâche 1 : client Kapso Broadcasts (diffusions WhatsApp en masse). ZÉRO réseau : `kapso._requete` et
`kapso._dormir` sont remplacés. Couvre : chemin, méthode et enveloppe exacts de chaque appel, plus de 1 000 destinataires =
ValueError sans appel, `errors` d'un 201 rendues, `send` en un seul essai (500 comme 429), pagination `meta.total_pages`,
numéro sans `+` toléré, `error_details.code` -> `code_erreur`, aucune clé dans les messages d'erreur.
Run (depuis backend/) : & $PY tests/test_kapso_broadcasts.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzkapsobc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["KAPSO_API_KEY"] = ""
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                          # noqa: E402
logger.remove()
from app.config import settings                                    # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import kapso as K                                # noqa: E402

CLE = "SECRET-KAPSO-123"
PL = K.PLATFORM
settings.KAPSO_API_KEY = CLE
BC = f"{PL}/whatsapp/broadcasts"
APPELS: list = []          # (methode, url, json, params)
FILE: list = []
DORS: list = []


async def faux_requete(methode, url, *, json=None, params=None):
    APPELS.append((methode, url, json, params))
    r = FILE.pop(0) if len(FILE) > 1 else FILE[0]
    if isinstance(r, Exception):
        raise r
    return r


async def faux_dormir(s):
    DORS.append(s)


K._requete = faux_requete
K._dormir = faux_dormir


def scene(*reps):
    APPELS.clear(); FILE.clear(); DORS.clear()
    FILE.extend(reps)


def run(coro):
    return asyncio.run(coro)


def erreur(coro):
    try:
        run(coro)
    except Exception as e:  # noqa: BLE001
        return e
    return None


BID = "0b6f7e1c-1111-4222-8333-444455556666"

print("[a] création")
scene((201, {"data": {"id": BID, "status": "draft", "name": "x"}}, {}))
r = run(K.creer_broadcast("Soldes", "1234567890", "784203120908608"))
check("a1 POST /whatsapp/broadcasts", APPELS[0][:2] == ("POST", BC), APPELS)
check("a2 enveloppe exacte", APPELS[0][2] == {"whatsapp_broadcast": {
    "name": "Soldes", "phone_number_id": "1234567890", "whatsapp_template_id": "784203120908608"}}, APPELS[0][2])
check("a3 retour {id, statut}", r == {"id": BID, "statut": "draft"}, r)
scene((201, {"oups": 1}, {}))
e = erreur(K.creer_broadcast("n", "p", "t"))
check("a4 réponse sans data -> reponse_invalide", isinstance(e, K.KapsoErreur) and e.code == "reponse_invalide", repr(e))

print("[b] destinataires")
scene((201, {"data": {"added": 3, "duplicates": 1, "errors": ["Recipient 2: invalid phone number format"]}}, {}))
dest = [{"phone_number": "+3361111111%d" % i, "components": [{"type": "body", "parameters": []}]} for i in range(4)]
r = run(K.ajouter_destinataires(BID, dest))
check("b1 POST .../recipients", APPELS[0][:2] == ("POST", f"{BC}/{BID}/recipients"), APPELS)
check("b2 enveloppe recipients", APPELS[0][2] == {"whatsapp_broadcast": {"recipients": dest}})
check("b3 ajoutes/doublons/erreurs rendus", r == {"ajoutes": 3, "doublons": 1,
      "erreurs": ["Recipient 2: invalid phone number format"]}, r)
scene((201, {"data": {"added": 0, "duplicates": 0, "errors": [
    "Recipient 1: invalid phone number +33611111111 (33611111111)", f"Recipient 2: bad key {CLE}"]}}, {}))
r = run(K.ajouter_destinataires(BID, dest[:2]))
check("b3b numéro masqué dans les erreurs", all("3361111" not in x and "…" in x for x in r["erreurs"][:1]), r)
check("b3c clé retirée des erreurs", CLE not in " ".join(r["erreurs"]), r)
scene((201, {"data": {"added": 1, "duplicates": 0}}, {}))
r = run(K.ajouter_destinataires(BID, dest[:1]))
check("b4 errors absent -> liste vide", r["erreurs"] == [] and r["ajoutes"] == 1, r)
APPELS.clear()
e = erreur(K.ajouter_destinataires(BID, [{"phone_number": "+1"}] * 1001))
check("b5 1 001 -> ValueError", isinstance(e, ValueError), repr(e))
check("b6 ... sans aucun appel", APPELS == [], APPELS)
scene((201, {"data": {"added": 1000, "duplicates": 0, "errors": []}}, {}))
r = run(K.ajouter_destinataires(BID, [{"phone_number": "+1"}] * 1000))
check("b7 1 000 accepté en un appel", len(APPELS) == 1 and r["ajoutes"] == 1000)

print("[c] envoi : un seul essai")
scene((202, {"data": {"id": BID, "status": "sending"}}, {}))
r = run(K.envoyer_broadcast(BID))
check("c1 POST .../send sans corps", APPELS[0][:3] == ("POST", f"{BC}/{BID}/send", None), APPELS)
check("c2 retour {statut}", r == {"statut": "sending"}, r)
for corps in ({}, b"", b"<html>ok</html>", {"data": None}):
    scene((202, corps, {}))
    e = erreur(K.envoyer_broadcast(BID))
    check(f"c2b 202 sans data ({type(corps).__name__}) : pas d'exception", e is None, repr(e))
scene((202, b"", {}))
check("c2c ... statut vide", run(K.envoyer_broadcast(BID)) == {"statut": ""})
scene((500, {"error": "boom"}, {}))
e = erreur(K.envoyer_broadcast(BID))
check("c3 500 -> KapsoErreur statut 500", isinstance(e, K.KapsoErreur) and e.statut == 500, repr(e))
check("c4 ... un seul appel", len(APPELS) == 1, len(APPELS))
scene((429, {"error": "slow"}, {"Retry-After": "1"}), (202, {"data": {"status": "sending"}}, {}))
e = erreur(K.envoyer_broadcast(BID))
check("c5 429 -> erreur après un seul appel, sans attente", isinstance(e, K.KapsoErreur) and e.statut == 429
      and len(APPELS) == 1 and DORS == [], (repr(e), len(APPELS), DORS))
scene(OSError("coupé"))
e = erreur(K.envoyer_broadcast(BID))
check("c6 panne réseau : un seul appel", isinstance(e, K.KapsoErreur) and e.code == "reseau" and len(APPELS) == 1, repr(e))

print("[d] lecture et arrêt")
scene((200, {"data": {"id": BID, "status": "completed", "total_recipients": 5, "pending_count": 0, "sent_count": 3,
                      "delivered_count": 2, "read_count": 1, "failed_count": 1, "suppressed_count": 1}}, {}))
r = run(K.broadcast(BID))
check("d1 GET /broadcasts/{id}", APPELS[0][:2] == ("GET", f"{BC}/{BID}"), APPELS)
check("d2 id et statut", r["id"] == BID and r["statut"] == "completed", r)
check("d3 compteurs", r["compteurs"] == {"total": 5, "pending": 0, "sent": 3, "failed": 1, "suppressed": 1,
                                         "delivered": 2, "read": 1}, r.get("compteurs"))
scene((200, {"data": {"id": BID, "status": "sending", "total_recipients": 2, "pending_count": 2, "sent_count": 0,
                      "failed_count": 0}}, {}))
r = run(K.broadcast(BID))
check("d4 compteurs absents = 0 (suppressed optionnel)", r["compteurs"]["suppressed"] == 0
      and r["compteurs"]["delivered"] == 0, r["compteurs"])
scene((200, {"data": {"id": BID, "status": "stopped"}}, {}))
r = run(K.arreter_broadcast(BID))
check("d5 PATCH stopped enveloppé", APPELS[0] == ("PATCH", f"{BC}/{BID}",
      {"whatsapp_broadcast": {"status": "stopped"}}, None), APPELS)
check("d6 arrêt rend le statut", r.get("statut") == "stopped", r)

print("[e] lignes de destinataires")
lignes = [
    {"phone_number": "33611111111", "status": "sent", "delivered_at": "2026-10-27T10:00:00Z", "read_at": None,
     "error_message": None, "error_details": None},
    {"phone_number": "+33622222222", "status": "failed", "failed_at": "2026-10-27T10:00:01Z", "error_message": "nope",
     "error_details": {"error_class": "meta", "code": 131047}},
    {"phone_number": "33633333333", "status": "suppressed",
     "error_details": {"code": "marketing_preference_stopped", "detail": "stop"}},
    {"phone_number": "33644444444", "status": "sent", "delivered_at": "x", "read_at": "y"},
]
scene((200, {"data": lignes, "meta": {"page": 1, "per_page": 100, "total_pages": 3, "total_count": 250}}, {}))
r = run(K.destinataires_broadcast(BID))
check("e1 GET .../recipients page=1 per_page=100", APPELS[0][:2] == ("GET", f"{BC}/{BID}/recipients")
      and APPELS[0][3] == {"page": 1, "per_page": 100}, APPELS)
check("e2 pages = meta.total_pages", r["pages"] == 3, r)
check("e3 numéro sans + normalisé", r["lignes"][0]["phone_number"] == "+33611111111", r["lignes"][0])
check("e4 numéro avec + conservé", r["lignes"][1]["phone_number"] == "+33622222222")
check("e5 livré / lu", (r["lignes"][0]["livre"], r["lignes"][0]["lu"]) == (True, False)
      and (r["lignes"][3]["livre"], r["lignes"][3]["lu"]) == (True, True), r["lignes"])
check("e6 error_details.code -> code_erreur (texte)", r["lignes"][1]["code_erreur"] == "131047"
      and r["lignes"][2]["code_erreur"] == "marketing_preference_stopped" and r["lignes"][0]["code_erreur"] == "",
      [x["code_erreur"] for x in r["lignes"]])
check("e7 statut rendu tel quel", [x["statut"] for x in r["lignes"]] == ["sent", "failed", "suppressed", "sent"])
check("e8 clés exactes", set(r["lignes"][0]) == {"phone_number", "statut", "code_erreur", "livre", "lu"}, r["lignes"][0])
scene((200, {"data": []}, {}))
run(K.destinataires_broadcast(BID, page=0, par_page=5000))
check("e9b page >= 1, par_page <= 100", APPELS[0][3] == {"page": 1, "per_page": 100}, APPELS)
scene((200, {"data": []}, {}))
r = run(K.destinataires_broadcast(BID, page=2, par_page=50))
check("e9 page et par_page transmis", APPELS[0][3] == {"page": 2, "per_page": 50}, APPELS)
check("e10 meta absente -> 1 page", r == {"lignes": [], "pages": 1}, r)

print("[f] aucune clé dans les erreurs")
corps_piege = {"error": f"clé {CLE} invalide"}
for nom, appel in (("creer", lambda: K.creer_broadcast("n", "p", "t")),
                   ("ajouter", lambda: K.ajouter_destinataires(BID, [{"phone_number": "+1"}])),
                   ("envoyer", lambda: K.envoyer_broadcast(BID)), ("lire", lambda: K.broadcast(BID)),
                   ("dest", lambda: K.destinataires_broadcast(BID)), ("arret", lambda: K.arreter_broadcast(BID))):
    scene((422, corps_piege, {}))
    e = erreur(appel())
    check(f"f {nom} : KapsoErreur 422 sans la clé", isinstance(e, K.KapsoErreur) and e.statut == 422
          and CLE not in str(e) and CLE not in e.message, repr(e))
e = erreur(K.ajouter_destinataires(BID, [{"phone_number": "+1"}] * 1001))
check("f7 ValueError sans numéro ni clé", CLE not in str(e) and "+1" not in str(e), str(e))
check("f8 ValueError à texte fixe en français", "1 000" in str(e), str(e))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
