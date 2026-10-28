# -*- coding: utf-8 -*-
"""t357 (28/10/2026) — Veille & prospection P6 : les étapes WhatsApp dues partent par `whatsapp_echanges.envoyer` (ses
règles inchangées), depuis le numéro de l'espace qui porte l'accord du contact ; refus des règles → séquence arrêtée
(motif) ; plafond de dépense ou du mois → la passe s'arrête, l'étape attend ; panne → 3 essais ; un message entrant d'un
prospect → contact entrant et « A répondu ».
Data-dir isolé, aucun réseau (faux envoyer). Run (depuis backend/) : & $PY tests/test_whatsapp_prospection.py"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwap357_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from fastapi import HTTPException                                    # noqa: E402
from app.services import espaces as E, kapso as K, prospects as P, prospects_score as SC, prospects_sequences as S   # noqa: E402
from app.services import whatsapp as WA, whatsapp_prospection as WP                                                 # noqa: E402

for m in (P, SC):
    m._aujourdhui = lambda: date(2026, 10, 28)
PARIS = ZoneInfo("Europe/Paris")
HORLOGE = [datetime(2026, 11, 2, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)]
for m in (S, WP):
    m._maintenant = lambda: HORLOGE[0]
A = E.creer({"nom": "Prospection"})["id"]
WA_ETAT = {"etat": {"PID1": {"accords": {"tel:33611111111": {"date": "2026-10-20", "source": "saisi"},
                                         "tel:33622222222": {"date": "2026-10-20", "source": "saisi"},
                                         "tel:33633333333": {"date": "2026-10-20", "source": "saisi"},
                                         "tel:33644444444": {"date": "2026-10-20", "source": "saisi"}},
                             "stops": {}, "desinscrits_marketing": {}, "compteur": {}, "alias": {}, "journal": []}}}
E.chemin(A, "whatsapp.json").write_text(json.dumps(WA_ETAT), encoding="utf-8")
WP._COMPTES = lambda eid: [("cpt_1", "PID1")]
ENVOIS, REPONSE = [], {"mode": "ok"}


async def faux_envoyer(cid, identite, envoi):
    mode = REPONSE["mode"]
    if mode == "stop":
        raise WA.WhatsappRefus("ce contact a écrit STOP : aucun envoi", "stop")
    if mode == "fenetre":
        raise WA.WhatsappRefus("hors de la fenêtre de 24 h : seul un modèle peut partir", "fenetre")
    if mode == "plafond":
        raise HTTPException(402, "plafond de dépense atteint")
    if mode == "panne":
        raise K.KapsoErreur("réseau", code="reseau")
    if mode == "modele":
        raise ValueError("modèle inconnu ou non approuvé pour cette langue")
    ENVOIS.append((cid, identite, envoi))
    return {"id": f"wamid.{len(ENVOIS)}", "statut": "accepted"}


WP._ENVOYER = faux_envoyer
SRC = {"type": "whatsapp", "date": "2026-10-20"}
MOD = {"nom": "prospection_relance", "langue": "fr", "parametres": ["Léa"]}


def prospect(nom, tel):
    pid = P.creer(A, {"nom": nom, "source": SRC, "base_legale": "consentement", "canaux": [{"type": "whatsapp", "valeur": tel}]})["id"]
    P.ajouter_consentement(A, pid, "whatsapp", "consentement", "whatsapp", "2026-10-20")
    P.changer_statut(A, pid, "qualifie")
    return pid


def sequence(pid, etapes):
    s = S.proposer(A, pid, "whatsapp", etapes)
    S.valider(A, s["id"])
    return S.planifier(A, s["id"])["id"]


def passe():
    return asyncio.run(WP.envoyer_dues(A))


print("[1] envoi")
p1 = prospect("Léa", "+33 6 11 11 11 11")
s1 = sequence(p1, [{"texte": "Bonjour Léa", "delai_jours": 0}, {"texte": "aperçu", "delai_jours": 3, "modele": MOD}])
r = passe()
check("1a 1er message : texte, au numéro de l'accord, du compte de l'espace", r["envoyes"] == 1 and ENVOIS[0] == ("cpt_1", "tel:33611111111", {"type": "texte", "texte": "Bonjour Léa"}), (r, ENVOIS))
x = [y for y in S.lister(A, p1)][0]
check("1b étape envoyée (wamid), fiche Contactée", x["etapes"][0]["statut"] == "envoyee" and x["etapes"][0]["message_id"] == "wamid.1" and P.lire(A, p1)["statut"] == "contacte")
HORLOGE[0] = datetime(2026, 11, 5, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
passe()
check("1c relance : le modèle approuvé", ENVOIS[-1][2] == {"type": "modele", "nom": "prospection_relance", "langue": "fr", "parametres": ["Léa"]}, ENVOIS[-1])

print("[2] refus, plafond, panne")
p2 = prospect("Stop", "+33622222222"); s2 = sequence(p2, [{"texte": "x", "delai_jours": 0}])
REPONSE["mode"] = "stop"; passe()
x = [y for y in S.lister(A) if y["id"] == s2][0]
check("2a STOP (règle WhatsApp) : séquence arrêtée, motif canal", x["statut"] == "annulee" and x["motif"] == "canal", (x["statut"], x["motif"]))
p3 = prospect("Fenêtre", "+33633333333"); s3 = sequence(p3, [{"texte": "x", "delai_jours": 0}])
REPONSE["mode"] = "fenetre"; passe()
x = [y for y in S.lister(A) if y["id"] == s3][0]
check("2b fenêtre de 24 h fermée pour un texte : arrêt, motif fenetre", x["statut"] == "annulee" and x["motif"] == "fenetre", (x["statut"], x["motif"]))
p4 = prospect("Plafond", "+33644444444"); s4 = sequence(p4, [{"texte": "x", "delai_jours": 0, "modele": MOD}])
REPONSE["mode"] = "plafond"; r = passe()
x = [y for y in S.lister(A) if y["id"] == s4][0]
check("2c plafond de dépense : l'étape attend, la passe s'arrête", x["statut"] == "planifiee" and r["etat"] == "plafond", (x["statut"], r))
REPONSE["mode"] = "panne"
for _ in range(3):
    passe()
x = [y for y in S.lister(A) if y["id"] == s4][0]
check("2d panne Kapso (leçon t356 I3) : après 3 pannes, l'étape attend toujours", x["statut"] == "planifiee" and not x.get("motif"), (x["statut"], x.get("motif")))
p5 = prospect("Sans accord", "+33655555555"); s5 = sequence(p5, [{"texte": "x", "delai_jours": 0}])
REPONSE["mode"] = "ok"; n0 = len(ENVOIS); passe()
x = [y for y in S.lister(A) if y["id"] == s5][0]
check("2e aucun numéro de l'espace n'a l'accord : rien ne part, arrêt « canal »", not any(e[1] == "tel:33655555555" for e in ENVOIS[n0:]) and x["motif"] == "canal", x["motif"])
HORLOGE[0] = datetime(2026, 11, 7, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
p6 = prospect("Samedi", "+33611111111".replace("1111111", "1111112"))
check("2f hors des heures calmes : rien", passe()["etat"] == "hors_horaires")

print("[3] réponse entrante")
HORLOGE[0] = datetime(2026, 11, 9, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
WP.entrant(A, "tel:33611111111")
f = P.lire(A, p1)
check("3a message entrant d'un prospect contacté : « A répondu », contact entrant", f["statut"] == "repondu" and any(h["quoi"] == "contact_entrant" for h in f["historique"]), f["statut"])
check("3b la séquence s'arrête d'elle-même", [y for y in S.lister(A, p1)][0]["statut"] in ("terminee", "annulee"))
check("3c un inconnu : rien", WP.entrant(A, "tel:33699999999") is None)
check("3d crochet branché dans whatsapp.noter_entrant", "_PROSPECT_ENTRANT" in vars(WA))

print("[4] outil whatsapp_modeles")
from app.services import agent_outils as ao, whatsapp_echanges as WE   # noqa: E402


async def faux_modeles(cid, tous=False):
    return [{"nom": "prospection_relance", "langue": "fr", "categorie": "marketing", "parametres": "positionnels", "n_parametres": 1},
            {"nom": "avec_noms", "langue": "fr", "categorie": "marketing", "parametres": "nommes", "n_parametres": 1}]


WE.modeles = faux_modeles
r = asyncio.run(ao.executer("whatsapp_modeles", {}, ao.Ctx(cid="c", espace_id=A)))
check("4a modèles approuvés positionnels de l'espace", r["ok"] and r["donnees"] == [{"nom": "prospection_relance", "langue": "fr", "categorie": "marketing", "n_parametres": 1}], r)

print("[5] relecture t357")
HORLOGE[0] = datetime(2026, 11, 16, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
ETAT2 = {"etat": {"PIDB": {"accords": {"tel:33677777777": {"date": "2026-10-20", "source": "saisi"}}, "stops": {},
                           "desinscrits_marketing": {}, "compteur": {}, "alias": {}, "journal": []},
                  "PIDA": {"accords": {"tel:33677777777": {"date": "2026-10-21", "source": "entrant"}},
                           "stops": {"tel:33677777777": "2026-10-22"}, "desinscrits_marketing": {}, "compteur": {}, "alias": {}, "journal": []},
                  "PID1": WA_ETAT["etat"]["PID1"]}}
ETAT2["etat"]["PID1"]["accords"].update({"tel:33622222200": {"date": "2026-10-20", "source": "saisi"},
                                         "tel:33688888800": {"date": "2026-10-20", "source": "saisi"},
                                         "tel:33688888801": {"date": "2026-10-20", "source": "saisi"},
                                         "tel:33688888802": {"date": "2026-10-20", "source": "saisi"}})
E.chemin(A, "whatsapp.json").write_text(json.dumps(ETAT2), encoding="utf-8")
WP._COMPTES = lambda eid: [("cpt_B", "PIDB"), ("cpt_A", "PIDA"), ("cpt_1", "PID1")]
REPONSE["mode"] = "ok"
pc = prospect("Deux numéros", "+33677777777"); sc = sequence(pc, [{"texte": "x", "delai_jours": 0}])
n0 = len(ENVOIS); passe()
x = [y for y in S.lister(A) if y["id"] == sc][0]
check("5a STOP sur un autre numéro de l'espace : rien ne part, arrêt « canal »", not any(e[1] == "tel:33677777777" for e in ENVOIS[n0:]) and x["motif"] == "canal", x.get("motif"))
REGISTRE = []
_noter_wa, _reg_wa = WA._noter, WA._stop_au_registre
WA._noter = lambda cid, geste: None
WA._stop_au_registre = lambda cid, ident: REGISTRE.append(ident)
WA.noter_entrant("cpt_1", {"from": "33688888888", "type": "text", "text": {"body": "STOP"}, "id": "m1"})
WA._noter, WA._stop_au_registre = _noter_wa, _reg_wa
check("5b un STOP tapé sur WhatsApp va au registre global", REGISTRE == ["tel:33688888888"], REGISTRE)
pl = prospect("Local", "06 22 22 22 00"); sl = sequence(pl, [{"texte": "Bonjour", "delai_jours": 0}])
n0 = len(ENVOIS); passe()
check("5c numéro au format local (06…) : reconnu, envoyé", any(e[1] == "tel:33622222200" for e in ENVOIS[n0:]), ENVOIS[n0:])
check("5d réponse rattachée même si le message porte un BSUID (groupe)", WP.entrant(A, ["bsuid:US.999", "tel:33622222200"]) == pl)
pm = prospect("Modèle refusé", "+33688888800"); sm = sequence(pm, [{"texte": "x", "delai_jours": 0, "modele": MOD}])
pn = prospect("Suivant", "+33688888801"); sn = sequence(pn, [{"texte": "Bonjour", "delai_jours": 0}])


async def refus_meta(cid, identite, envoi):
    if identite == "tel:33688888800":
        raise K.KapsoErreur("paramètres", statut=400, code="132000")
    ENVOIS.append((cid, identite, envoi))
    return {"id": "wamid.x"}


WP._ENVOYER = refus_meta
n0 = len(ENVOIS); passe()
x = [y for y in S.lister(A) if y["id"] == sm][0]
check("5e refus 4xx de Meta (132000) : arrêt « modele », jamais en boucle", x["statut"] == "annulee" and x["motif"] == "modele", (x["statut"], x.get("motif")))
check("5f …et le prospect suivant part dans la même passe", any(e[1] == "tel:33688888801" for e in ENVOIS[n0:]))
pu = prospect("Incertain", "+33688888802"); su = sequence(pu, [{"texte": "x", "delai_jours": 0, "modele": MOD}])
APPELS_U = []


async def incertain(cid, identite, envoi):
    APPELS_U.append(identite)
    raise K.KapsoErreur("passerelle", statut=502, code="502")


WP._ENVOYER = incertain
passe(); passe()
x = [y for y in S.lister(A) if y["id"] == su][0]
check("5g issue incertaine (5xx après l'appel) : jamais renvoyé, arrêt « incertain »", APPELS_U.count("tel:33688888802") == 1 and x["motif"] == "incertain", (APPELS_U, x.get("motif")))
WP._ENVOYER = faux_envoyer

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
