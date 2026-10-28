# -*- coding: utf-8 -*-
"""t358 (28/10/2026) — Veille & prospection P7 : le SUIVI des réponses. Passage à l'humain (motif, prochaine action,
effacé quand l'utilisateur reprend), lecture des réponses par prospect (extraits e-mail ENCADRÉS, WhatsApp : la date),
garde de lexique (prix, devis, plainte, STOP → l'agent ne répond pas), séquence « réponse » d'une étape admise pour une
fiche « A répondu » ; outils `reponses_lire` et `relance_proposer`.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_prospects_suivi.py"""
import asyncio, os, pathlib, sys, tempfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsuivi358_"))
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


from app.services import agent_outils as ao, agent_store as st, email_canal as M, espaces as E   # noqa: E402
from app.services import prospects as P, prospects_score as SC, prospects_sequences as S, prospects_suivi as U   # noqa: E402
from app.services.storage import init_db                                                              # noqa: E402

for m in (P, SC):
    m._aujourdhui = lambda: date(2026, 10, 28)
S._maintenant = lambda: datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc)


async def interdits(eid):
    return [], []


ao._mots_interdits = interdits


async def preparer():
    await init_db()
    A = E.creer({"nom": "Prospection"})["id"]
    return A, (await st.creer("campagnes", A, "x"))["id"]


A, cid = asyncio.run(preparer())
ctx = ao.Ctx(cid=cid, espace_id=A)
SRC = {"type": "web", "url": "https://x.fr", "date": "2026-10-20"}


def fiche(nom, email, statut="repondu"):
    pid = P.creer(A, {"nom": nom, "entreprise": nom, "source": SRC, "base_legale": "interet_legitime_b2b",
                      "canaux": [{"type": "email", "valeur": email}]})["id"]
    for s in ("qualifie", "contacte", "repondu")[: ("qualifie", "contacte", "repondu").index(statut) + 1]:
        P.changer_statut(A, pid, s)
    return pid


def refus(fn, code=None):
    try:
        fn()
    except (P.RefusProspect, S.RefusSequence) as e:
        return code is None or e.code == code, e.code
    return False, "aucun refus"


print("[1] passer à l'humain")
p1 = fiche("Studio Prix", "contact@studio-prix.fr")
f = P.passer_a_l_humain(A, p1, "prix", "demande le tarif pour 10 vidéos", qui="agent")
check("1a drapeau, motif, prochaine action datée du jour", f["a_l_humain"]["motif"] == "prix" and f["prochaine_action"]["le"] == "2026-10-28"
      and "Reprendre la main" in f["prochaine_action"]["texte"], f)
check("1b historique noté (qui = agent)", f["historique"][-1]["quoi"] == "a_l_humain" and f["historique"][-1]["qui"] == "agent")
check("1c motif inconnu refusé", refus(lambda: P.passer_a_l_humain(A, p1, "promo", "x"), "champ")[0])
P.noter_contact(A, p1, "sortant", "appel")
check("1d l'utilisateur note un contact : le drapeau s'efface", P.lire(A, p1)["a_l_humain"] is None)
P.passer_a_l_humain(A, p1, "devis", "veut un devis")
P.changer_statut(A, p1, "rdv")
check("1e l'utilisateur change le statut : le drapeau s'efface", P.lire(A, p1)["a_l_humain"] is None)

print("[2] réponses par prospect")
p2 = fiche("Studio Oui", "contact@studio-oui.fr")
M.ajouter_reponse(A, {"pid": p2, "de": "contact@studio-oui.fr", "sujet": "Re: Vos vidéos", "extrait": "Oui, intéressés, on en parle mardi ?", "stop": False})
p3 = fiche("Studio Cher", "contact@studio-cher.fr")
M.ajouter_reponse(A, {"pid": p3, "de": "contact@studio-cher.fr", "sujet": "Re", "extrait": "Combien ça coûte pour 10 vidéos ?", "stop": False})
p4 = fiche("Studio WA", "contact@studio-wa.fr")
P.noter_contact(A, p4, "entrant", "whatsapp : message reçu", "systeme")
p5 = fiche("Pas répondu", "a@pasrepondu.fr", statut="contacte")
r = {x["pid"]: x for x in U.reponses(A)}
check("2a les fiches qui ont répondu, pas les autres", {p2, p3, p4} <= set(r) and p5 not in r, list(r))
check("2b e-mail : objet et extrait", r[p2]["reponses"][0]["extrait"].startswith("Oui, intéressés") and r[p2]["reponses"][0]["canal"] == "email")
check("2c WhatsApp : la date seulement (le texte n'est jamais rangé)", any(x["canal"] == "whatsapp" and not x.get("extrait") for x in r[p4]["reponses"]), r[p4])
check("2d garde : une question de prix exige l'humain", r[p3]["garde"] == "prix" and r[p2]["garde"] is None, (r[p3]["garde"], r[p2]["garde"]))
check("2e garde : devis, plainte, STOP", U.garde("Pouvez-vous m'envoyer un devis ?") == "devis" and U.garde("C'est du spam, inadmissible") == "plainte"
      and U.garde("STOP") == "stop" and U.garde("Merci, à mardi") is None)

print("[3] séquence « réponse »")
check("3a séquence ordinaire refusée sur une fiche « A répondu »", refus(lambda: S.proposer(A, p2, "email", [{"objet": "x", "texte": "x", "delai_jours": 0}]), "etat")[0])
sr = S.proposer(A, p2, "email", [{"objet": "Re: Vos vidéos", "texte": "Mardi 10 h vous convient ?", "delai_jours": 0}], reponse=True)
check("3b réponse d'une étape admise, marquée", sr["reponse"] is True and sr["statut"] == "proposee")
check("3c réponse de deux étapes refusée", refus(lambda: S.proposer(A, p2, "email", [{"objet": "x", "texte": "x", "delai_jours": 0}, {"objet": "y", "texte": "y", "delai_jours": 3}], reponse=True), "champ")[0])
S.valider(A, sr["id"]); S.planifier(A, sr["id"])
x = [y for y in S.lister(A, p2) if y["id"] == sr["id"]][0]
check("3d « A répondu » n'arrête pas une séquence réponse", x["statut"] == "planifiee", x["statut"])
d = [y for y in S.etapes_dues(A, "email") if y["sid"] == sr["id"]]
check("3e due, marquée réponse pour les envoyeurs", d and d[0]["reponse"] is True and S.statut_admis(d[0], "repondu"), d)

print("[4] outils")
r = asyncio.run(ao.executer("reponses_lire", {}, ctx))
check("4a reponses_lire : les extraits sont ENCADRÉS comme des preuves", r["ok"] and "<<<PREUVE" in str(r["donnees"]) and "intéressés" in str(r["donnees"]), str(r)[:300])
r = asyncio.run(ao.executer("relance_proposer", {"pid": p3, "decision": "repondre", "canal": "email", "objet": "Re", "texte": "Le prix est de 100 €"}, ctx))
check("4b répondre à une question de prix : refusé, passage à l'humain exigé", not r["ok"] and "humain" in r["resume"], r["resume"])
r = asyncio.run(ao.executer("relance_proposer", {"pid": p3, "decision": "humain", "motif": "prix", "raison": "veut un tarif pour 10 vidéos"}, ctx))
check("4c humain : la fiche est à reprendre, aucune carte", r["ok"] and r.get("carte") is None and P.lire(A, p3)["a_l_humain"]["motif"] == "prix", r)
p6 = fiche("Studio Six", "contact@studio-six.fr")
M.ajouter_reponse(A, {"pid": p6, "de": "contact@studio-six.fr", "sujet": "Re", "extrait": "Avec plaisir, quand êtes-vous libre ?", "stop": False})
r = asyncio.run(ao.executer("relance_proposer", {"pid": p6, "decision": "repondre", "canal": "email", "objet": "Re: Bonjour", "texte": "Mardi 10 h ?"}, ctx))
k = r.get("carte") or {}
check("4d répondre : la carte « sequence » (porte 2), séquence réponse", r["ok"] and k.get("genre") == "sequence" and (k.get("arguments") or {}).get("reponse") is True, r)
r = asyncio.run(ao.executer("relance_proposer", {"pid": p6, "decision": "humain"}, ctx))
check("4e humain sans motif : refus", not r["ok"])

print("[5] relecture t358")
for t, m in (("Non merci, pas intéressé", "refus"), ("No thanks, not interested", "refus"), ("Ne me contactez plus", "refus"),
             ("Please stop emailing me", "refus"), ("opt out", "refus"), ("What are your rates and fees?", "prix"),
             ("Quels sont vos délais et conditions du contrat ?", "engagement")):
    check(f"5a garde « {t} » → {m}", U.garde(t) == m, U.garde(t))
p7 = fiche("Studio Sept", "contact@studio-sept.fr")
M.ajouter_reponse(A, {"pid": p7, "de": "contact@studio-sept.fr", "sujet": "Re", "extrait": "Combien pour 10 vidéos ?", "stop": False})
M.ajouter_reponse(A, {"pid": p7, "de": "contact@studio-sept.fr", "sujet": "Re", "extrait": "Et une démo possible ?", "stop": False})
check("5b garde sur TOUTES les réponses depuis le dernier envoi (prix dans l'avant-dernière)", {x["pid"]: x for x in U.reponses(A)}[p7]["garde"] == "prix")
p8 = fiche("Studio Huit", "contact@studio-huit.fr")
P.noter_contact(A, p8, "entrant", "whatsapp : message reçu", "systeme")
check("5c dernière réponse WhatsApp (texte inconnu) : garde « illisible »", {x["pid"]: x for x in U.reponses(A)}[p8]["garde"] == "illisible")
p9 = fiche("Studio Neuf", "contact@studio-neuf.fr")
M.ajouter_reponse(A, {"pid": p9, "de": "contact@studio-neuf.fr", "sujet": "Re", "extrait": "Avec plaisir, une démo ?", "stop": False})
r = asyncio.run(ao.executer("relance_proposer", {"pid": p9, "decision": "repondre", "canal": "whatsapp", "texte": "x"}, ctx))
check("5d répondre sur un autre canal que la réponse : refus", not r["ok"] and "canal" in r["resume"], r["resume"])
k9 = asyncio.run(ao.executer("relance_proposer", {"pid": p9, "decision": "repondre", "canal": "email", "objet": "Re", "texte": "Mardi ?"}, ctx))
s9 = k9["carte"]["arguments"]["sid"]
S.valider(A, s9); S.planifier(A, s9)
import time as _time                                                # noqa: E402
_time.sleep(1.1)
P.noter_contact(A, p9, "entrant", "e-mail : Re", "systeme")
M.ajouter_reponse(A, {"pid": p9, "de": "contact@studio-neuf.fr", "sujet": "Re", "extrait": "Non merci finalement", "stop": False})
x = [y for y in S.lister(A, p9) if y["id"] == s9][0]
check("5e une nouvelle réponse arrive : la réponse préparée s'arrête (motif nouvelle_reponse)", x["statut"] == "annulee" and x["motif"] == "nouvelle_reponse", (x["statut"], x.get("motif")))
r = asyncio.run(ao.executer("relance_proposer", {"pid": p9, "decision": "repondre", "canal": "email", "objet": "Re", "texte": "Dommage"}, ctx))
check("5f un refus (« non merci ») : l'agent ne répond pas", not r["ok"] and "humain" in r["resume"], r["resume"])
p10 = fiche("Studio Dix", "contact@studio-dix.fr")
M.ajouter_reponse(A, {"pid": p10, "de": "contact@studio-dix.fr", "sujet": "Re", "extrait": "Intéressés, parlons-en", "stop": False})
k10 = asyncio.run(ao.executer("relance_proposer", {"pid": p10, "decision": "repondre", "canal": "email", "objet": "Re", "texte": "Mardi ?"}, ctx))
r = asyncio.run(ao.executer("relance_proposer", {"pid": p10, "decision": "repondre", "canal": "email", "objet": "Re", "texte": "Et mercredi ?"}, ctx))
check("5g une seule réponse par message reçu : la deuxième est refusée", k10["ok"] and not r["ok"], r["resume"])
P.passer_a_l_humain(A, p10, "autre", "à voir")
x = [y for y in S.lister(A, p10) if y["id"] == k10["carte"]["arguments"]["sid"]][0]
check("5h passer à l'humain : les séquences en cours de la fiche s'arrêtent (motif humain)", x["statut"] == "annulee" and x["motif"] == "humain", (x["statut"], x.get("motif")))
r = asyncio.run(ao.executer("relance_proposer", {"pid": p10, "decision": "repondre", "canal": "email", "objet": "Re", "texte": "x"}, ctx))
r2 = asyncio.run(ao.executer("sequence_proposer", {"pid": p10, "canal": "email", "etapes": [{"objet": "x", "texte": "x", "delai_jours": 0}]}, ctx))
check("5i fiche « à reprendre » : l'agent ne propose plus rien", not r["ok"] and not r2["ok"], (r["resume"], r2["resume"]))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
