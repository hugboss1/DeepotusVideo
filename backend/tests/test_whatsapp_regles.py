# -*- coding: utf-8 -*-
"""t310 tâche 4 (27/10/2026) — B1 WhatsApp via Kapso : règles d'envoi, accords, STOP, plafond, journal, par espace.
Plan docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md (tâche 4, Review Focus 4), spec §6.1 « Identité des
contacts » et §6.3. Fonctions réelles (`whatsapp.controler`…), data-dir temporaire, AUCUN réseau, horloge injectée.
Ce que ce banc garde :
  R1  identité : BSUID d'abord, sinon numéro en chiffres ; `destinataire` : to / recipient ; message sans identité : ValueError.
  R2  STOP : « Stop », « STOP. », « arrêt » ; « stop ou encore ? » n'en est pas un ; un entrant note l'accord, un STOP le stop.
  R3  un cas par code de refus (accord, stop, fenetre, marketing, bsuid_authentification, plafond, consentement) ; ordre.
  R4  un cas qui passe pour chaque type (texte, boutons, modele).
  R5  fenêtre : 23 h 59 ouverte, 24 h 01 fermée (horloge injectée).
  R6  Review Focus 4 : contact BSUID seul : accord, STOP, envoi par `recipient` ; AUTHENTICATION refusé.
  R7  journal : 2 001 envois -> 2 000 lignes, aucune ne contient le texte envoyé.
  R8  le compteur passe au mois suivant ; plafond réglable.
  R9  espace client : consentement `whatsapp:<phone_id>` de la fiche du client responsable (produit compris).
  R10 `etat` par NUMÉRO (clé WHATSAPP_PHONE_ID), les autres clés de whatsapp.json (liaison) sont gardées ; WhatsappRefus :
      PermissionError.
  R14 relecture finale I1 : STOP noté, compte supprimé, nouveau compte du même espace relié au même numéro : refus stop,
      compteurs du mois gardés ; un compte sans numéro n'a pas d'état (ValueError) ; un autre espace part d'un état vide.
  R15 relecture finale I2 (ruling 15) : un modèle MARKETING exige un accord saisi ; un accord né d'un entrant permet texte,
      boutons, utility et authentication ; groupe d'alias compris ; un entrant ne rétrograde jamais un accord saisi.
  R16 relecture finale Minor 1 (ruling 16) : plafond PAR ESPACE (`reglages` de whatsapp.json), sortants + entrants du mois
      sur tous les numéros de l'espace ; `service` reste par numéro.
  R17 relecture finale Minor 3 : mots d'arrêt élargis, un mot de politesse au plus.
Run (depuis backend/) : & $PY tests/test_whatsapp_regles.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwaregl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
          "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "KAPSO_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
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


from datetime import datetime, timedelta, timezone                  # noqa: E402
from app.services import comptes as CP, espaces as E, fiche_client as FC  # noqa: E402
from app.services import whatsapp as WA                              # noqa: E402

E.lire()
T0 = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
TXT = "Bonjour, voici le SECRET-TEXTE-ENVOYE"


def compte(eid, pid):
    cid_ = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
    CP.poser_publics_serveur(cid_, {"WHATSAPP_PHONE_ID": pid})
    return cid_


def refus(cid_, ident, **kw):
    base = dict(type="texte", categorie=None, dernier_entrant=T0 - timedelta(hours=1), maintenant=T0)
    base.update(kw)
    try:
        WA.controler(cid_, ident, **base)
    except WA.WhatsappRefus as e:
        return e.code
    return None


boite = E.creer({"nom": "Atelier Soleil"})["id"]
cid = compte(boite, "PN-R1")
TEL = "tel:33612345678"
BS = "bsuid:FR.1234567890"

print("\n[R1] identité")
check("R1.1 BSUID d'abord", WA.identite({"from": "33612345678", "from_user_id": "FR.1"}) == "bsuid:FR.1")
check("R1.2 numéro en chiffres seuls", WA.identite({"from": "+33 6 12-34.56.78"}) == "tel:33612345678")
check("R1.3 BSUID seul (from absent)", WA.identite({"from_user_id": "FR.9"}) == "bsuid:FR.9")
try:
    WA.identite({"type": "text"})
    rien = False
except ValueError:
    rien = True
check("R1.4 sans identité : ValueError", rien)
check("R1.5 destinataire : to pour un numéro, recipient pour un BSUID",
      WA.destinataire(TEL) == {"to": "33612345678"} and WA.destinataire(BS) == {"recipient": "FR.1234567890"})
check("R1.6 numero_normalise : 06 -> marché, 00 -> sans, indicatif gardé",
      WA.numero_normalise("06 12 34 56 78") == "33612345678" and WA.numero_normalise("0033 6 12 34 56 78") == "33612345678"
      and WA.numero_normalise("+33 6 12 34 56 78") == "33612345678")

print("\n[R2] STOP")


def stop_de(texte):
    WA.noter_entrant(cid, {"id": "m", "from": "33700000001", "type": "text", "text": {"body": texte}}, T0)
    return "tel:33700000001" in WA.etat(cid)["stops"]


check("R2.1 « Stop », « STOP. », « arrêt », « Désabonner ! »",
      all(stop_de(t) for t in ("Stop", "STOP.", "arrêt", " Désabonner ! ")))
check("R2.2 le STOP ne note pas d'accord", "tel:33700000001" not in WA.etat(cid)["accords"])
WA.noter_entrant(cid, {"id": "m2", "from": "33700000002", "type": "text", "text": {"body": "stop ou encore ?"}}, T0)
e1 = WA.etat(cid)
check("R2.3 « stop ou encore ? » : accord, pas de stop",
      "tel:33700000002" in e1["accords"] and "tel:33700000002" not in e1["stops"]
      and e1["accords"]["tel:33700000002"]["source"] == "entrant")
WA.noter_entrant(cid, {"id": "m3", "from": "33700000003", "type": "image"}, T0)
check("R2.4 un entrant non texte vaut accord", "tel:33700000003" in WA.etat(cid)["accords"])
check("R2.5 le journal garde l'entrant sans texte",
      "stop ou encore" not in json.dumps(WA.etat(cid)["journal"]) and WA.etat(cid)["journal"][-1]["sens"] == "entrant")

print("\n[R3] un cas par code de refus")
WA.noter_accord(cid, TEL, "formulaire", T0)
check("R3.0 accord par saisie : texte dans la fenêtre passe", refus(cid, TEL) is None)
check("R3.1 accord : aucun accord enregistré", refus(cid, "tel:33699999999") == "accord")
check("R3.2 accord : même un modèle sans accord", refus(cid, "tel:33699999999", type="modele", categorie="UTILITY") == "accord")
check("R3.3 stop", refus(cid, "tel:33700000001") == "stop")
check("R3.4 fenetre : jamais d'entrant", refus(cid, TEL, dernier_entrant=None) == "fenetre")
check("R3.5 fenetre : boutons hors fenêtre", refus(cid, TEL, type="boutons", dernier_entrant=T0 - timedelta(days=2)) == "fenetre")
WA.noter_desinscription(cid, TEL, T0)
check("R3.6 marketing : modèle MARKETING vers un désinscrit", refus(cid, TEL, type="modele", categorie="MARKETING") == "marketing")
check("R3.7 marketing : un modèle UTILITY passe encore", refus(cid, TEL, type="modele", categorie="UTILITY") is None)
check("R3.8 un texte dans la fenêtre passe encore", refus(cid, TEL) is None)
WA.noter_accord(cid, BS, "formulaire", T0)
check("R3.9 bsuid_authentification", refus(cid, BS, type="modele", categorie="AUTHENTICATION") == "bsuid_authentification")
check("R3.10 AUTHENTICATION vers un numéro : passe", refus(cid, TEL, type="modele", categorie="AUTHENTICATION") is None)
check("R3.11 ordre : stop avant accord, accord avant fenêtre",
      refus(cid, "tel:33700000001", dernier_entrant=None) == "stop"
      and refus(cid, "tel:33699999999", dernier_entrant=None) == "accord")
check("R3.12 codes du refus", set(WA.CODES_REFUS) == {"accord", "stop", "fenetre", "marketing", "plafond", "consentement",
                                                      "prix", "bsuid_authentification"})

print("\n[R4] chaque type passe")
check("R4.1 texte, boutons, modèle (UTILITY et MARKETING non désinscrit)",
      refus(cid, TEL) is None and refus(cid, TEL, type="boutons") is None
      and refus(cid, TEL, type="modele", categorie="UTILITY", dernier_entrant=None) is None
      and refus(cid, BS, type="modele", categorie="MARKETING", dernier_entrant=None) is None)
try:
    WA.controler(cid, TEL, type="carte", categorie=None, dernier_entrant=None, maintenant=T0)
    inconnu = False
except ValueError:
    inconnu = True
check("R4.2 type inconnu : ValueError", inconnu)

print("\n[R5] fenêtre de 24 h")
check("R5.1 23 h 59 : ouverte", refus(cid, TEL, dernier_entrant=T0 - timedelta(hours=23, minutes=59)) is None)
check("R5.2 24 h 01 : fermée", refus(cid, TEL, dernier_entrant=T0 - timedelta(hours=24, minutes=1)) == "fenetre")
check("R5.3 date sans fuseau acceptée (UTC)", refus(cid, TEL, dernier_entrant=(T0 - timedelta(hours=1)).replace(tzinfo=None)) is None)

print("\n[R6] Review Focus 4 : un contact BSUID seul")
msg = {"id": "wamid.B1", "from_user_id": "FR.777", "type": "text", "text": {"body": "bonjour"}}
ib = WA.noter_entrant(cid, msg, T0)
check("R6.1 identité bsuid, accord noté", ib == "bsuid:FR.777" and WA.etat(cid)["accords"][ib]["source"] == "entrant")
check("R6.2 envoi par recipient", WA.destinataire(ib) == {"recipient": "FR.777"} and refus(cid, ib) is None)
check("R6.3 modèle AUTHENTICATION refusé", refus(cid, ib, type="modele", categorie="authentication") == "bsuid_authentification")
WA.noter_entrant(cid, {"id": "wamid.B2", "from_user_id": "FR.777", "type": "text", "text": {"body": "STOP"}}, T0)
check("R6.4 STOP du BSUID seul : refus stop", refus(cid, ib) == "stop" and ib in WA.etat(cid)["stops"])

print("\n[R7] journal borné, sans texte")
cj = compte(E.creer({"nom": "Journal"})["id"], "PN-J")
WA.noter_accord(cj, TEL, "papier", T0)
for i in range(2001):
    WA.noter_envoi(cj, TEL, type="texte", categorie=None, statut="envoye", id=f"wamid.{i}", maintenant=T0)
j = WA.etat(cj)["journal"]
check("R7.1 2 000 lignes au plus (les plus récentes)", len(j) == 2000 and j[-1]["id"] == "wamid.2000" and j[0]["id"] == "wamid.1",
      len(j))
check("R7.2 aucune ligne ne contient le texte envoyé", TXT not in json.dumps(j) and all(
    set(x) == {"quand", "sens", "identite", "type", "categorie", "statut", "id"} for x in j))
check("R7.3 le compteur a compté les 2 001", WA.etat(cj)["compteur"]["2026-10"] == {"sortants": 2001, "service": 2001})

print("\n[R8] compteur par mois, plafond")
ck = compte(E.creer({"nom": "Plafond"})["id"], "PN-K")
WA.noter_accord(ck, TEL, "papier", T0)
check("R8.0 plafond par défaut 1000, marché 33", WA.etat(ck)["plafond_mois"] == 1000 and WA.etat(ck)["marche_defaut"] == "33")
WA.regler(ck, plafond_mois=2)
WA.noter_envoi(ck, TEL, type="modele", categorie="UTILITY", statut="envoye", id="a", maintenant=T0)
check("R8.1 sous le plafond : passe", refus(ck, TEL, type="modele", categorie="UTILITY") is None)
WA.noter_envoi(ck, TEL, type="modele", categorie="UTILITY", statut="envoye", id="b", maintenant=T0)
check("R8.2 plafond atteint : refus", refus(ck, TEL, type="modele", categorie="UTILITY") == "plafond")
suivant = datetime(2026, 11, 1, 0, 5, tzinfo=timezone.utc)
check("R8.3 le mois suivant : compteur reparti de zéro", refus(ck, TEL, type="modele", categorie="UTILITY", maintenant=suivant) is None)
cmp_ = WA.etat(ck)["compteur"]
check("R8.4 compteur par mois, modèle hors service", cmp_ == {"2026-10": {"sortants": 2, "service": 0}}, cmp_)
try:
    WA.regler(ck, plafond_mois=-1)
    neg = False
except ValueError:
    neg = True
check("R8.5 plafond négatif refusé", neg)

print("\n[R9] espace client : consentement de la fiche")
lune = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
pain = E.creer({"nom": "Pain Lune", "type": "produit", "parent": lune})["id"]
cl = compte(lune, "PN-LUNE")
cp = compte(pain, "PN-PAIN")
for c_ in (cl, cp):
    WA.noter_accord(c_, TEL, "papier", T0)
check("R9.1 espace client sans consentement : consentement", refus(cl, TEL) == "consentement")
check("R9.2 produit gouverné par le client : consentement", refus(cp, TEL) == "consentement")
FC.ajouter_consentement(lune, "whatsapp:PN-LUNE", ["messages"], "ecrit")
check("R9.3 consentement du bon canal : passe", refus(cl, TEL) is None)
check("R9.4 le canal du produit est un autre canal", refus(cp, TEL) == "consentement")
FC.ajouter_consentement(lune, "whatsapp:PN-PAIN", ["messages"], "ecrit")
check("R9.5 le produit passe sur la fiche DU CLIENT", refus(cp, TEL) is None)
FC.revoquer(lune, "whatsapp:PN-LUNE")
check("R9.6 consentement révoqué : refus (avant stop et accord)", refus(cl, TEL) == "consentement")
check("R9.7 espace non client : aucun contrôle de consentement", refus(cid, TEL) is None)

print("\n[R10] état par compte, autres clés gardées")
ec = E.creer({"nom": "Deux comptes"})["id"]
c1, c2 = compte(ec, "PN-D1"), compte(ec, "PN-D2")
WA._ranger_liaison(ec, c1, {"lien_id": "L1"})
WA.noter_accord(c1, TEL, "papier", T0)
check("R10.1 l'accord d'un compte n'est pas celui de l'autre", TEL in WA.etat(c1)["accords"] and TEL not in WA.etat(c2)["accords"])
doc = json.loads((_tmp / "espaces" / ec / "whatsapp.json").read_text(encoding="utf-8"))
check("R10.2 la liaison est gardée à côté de `etat`, rangé par numéro (pas par compte)",
      doc["liaison"][c1] == {"lien_id": "L1"} and set(doc["etat"]) == {"PN-D1"})
check("R10.3 WhatsappRefus est une PermissionError avec code et message",
      issubclass(WA.WhatsappRefus, PermissionError) and WA.WhatsappRefus("m", "stop").code == "stop")
try:
    WA.etat("compte-inconnu")
    inc = False
except KeyError:
    inc = True
check("R10.4 compte inconnu : KeyError", inc)

print("\n[R11] identités liées (BSUID + numéro d'un même message)")
ca = compte(E.creer({"nom": "Alias"})["id"], "PN-A")


def entrant(cid_, texte, **ident):
    return WA.noter_entrant(cid_, {"id": "w", "type": "text", "text": {"body": texte}, **ident}, T0)


X, Y = "tel:33611110000", "bsuid:FR.alias1"
entrant(ca, "STOP", **{"from": "33611110000"})
entrant(ca, "bonjour", **{"from": "33611110000", "from_user_id": "FR.alias1"})
check("R11.1 STOP par numéro, puis message avec les deux : le BSUID est refusé (stop)", refus(ca, Y) == "stop" and refus(ca, X) == "stop")
check("R11.2 l'alias n'a pas levé le stop ni noté d'accord sur le BSUID", Y not in WA.etat(ca)["accords"])
cb = compte(E.creer({"nom": "Alias B"})["id"], "PN-B")
Z, W = "tel:33622220000", "bsuid:FR.alias2"
entrant(cb, "stop", from_user_id="FR.alias2")
entrant(cb, "oui", **{"from": "33622220000", "from_user_id": "FR.alias2"})
check("R11.3 STOP sous BSUID, envoi au numéro : stop", refus(cb, Z) == "stop" and refus(cb, W) == "stop")
cc = compte(E.creer({"nom": "Alias C"})["id"], "PN-C")
V, U = "tel:33633330000", "bsuid:FR.alias3"
entrant(cc, "salut", **{"from": "33633330000", "from_user_id": "FR.alias3"})
check("R11.4 alias posé : accord sur les deux, envois permis", refus(cc, V) is None and refus(cc, U) is None
      and WA.etat(cc)["alias"] == {U: V, V: U})
entrant(cc, "STOP", from_user_id="FR.alias3")
check("R11.5 alias puis STOP sur un seul : les deux refusés", refus(cc, V) == "stop" and refus(cc, U) == "stop")
cd = compte(E.creer({"nom": "Alias D"})["id"], "PN-D")
entrant(cd, "salut", **{"from": "33644440000", "from_user_id": "FR.alias4"})
WA.noter_desinscription(cd, "tel:33644440000", T0)
check("R11.6 désinscription marketing valable pour l'alias",
      refus(cd, "bsuid:FR.alias4", type="modele", categorie="MARKETING") == "marketing")

print("\n[R12] STOP robuste")
cs = compte(E.creer({"nom": "Stop"})["id"], "PN-S")


def est_stop(t):
    return WA._est_stop(t)


check("R12.1 variantes : stop, 'STOP', (stop), STOP 🛑, « arrêt » décomposé",
      all(est_stop(t) for t in ("stop", "'STOP'", "(stop)", "STOP 🛑", "arrêt", "“Stop” !", "  stop\n")))
check("R12.2 « stop ou encore ? », vide, ponctuation seule : pas STOP",
      not any(est_stop(t) for t in ("stop ou encore ?", "", "...", "ne stop pas", None)))

print("\n[R13] bornes et UTC")
check("R13.1 exactement 24 h 00 : fermée", refus(cid, TEL, dernier_entrant=T0 - timedelta(hours=24)) == "fenetre")
check("R13.2 23 h 59 min 59 s : ouverte", refus(cid, TEL, dernier_entrant=T0 - timedelta(hours=23, minutes=59, seconds=59)) is None)
cm = compte(E.creer({"nom": "Mois"})["id"], "PN-M")
WA.noter_accord(cm, TEL, "papier", T0)
WA.regler(cm, plafond_mois=1)
paris = timezone(timedelta(hours=2))
minuit_paris = datetime(2026, 11, 1, 0, 30, tzinfo=paris)          # 31/10 22:30 UTC : encore octobre
WA.noter_envoi(cm, TEL, type="modele", categorie="UTILITY", statut="envoye", id="x", maintenant=minuit_paris)
check("R13.3 horloge locale juste après minuit le 1er : toujours le mois UTC (2026-10)",
      list(WA.etat(cm)["compteur"]) == ["2026-10"]
      and refus(cm, TEL, type="modele", categorie="UTILITY", maintenant=minuit_paris) == "plafond")
check("R13.4 dates rangées en UTC", WA.etat(cm)["journal"][-1]["quand"].endswith("+00:00"))
WA.noter_envoi(cm, TEL, type="texte", categorie="y" * 200, statut="z" * 200, id="w" * 200, maintenant=T0)
ligne = WA.etat(cm)["journal"][-1]
check("R13.5 champs externes du journal bornés à 80", all(len(ligne[k]) == 80 for k in ("categorie", "statut", "id")), ligne)
check("R13.6 numero_normalise : (0) de tronc", WA.numero_normalise("+33 (0)6 12 34 56 78") == "33612345678"
      and WA.numero_normalise("0033 (0)6 12 34 56 78") == "33612345678")

print("\n[R14] I1 : l'état suit le NUMÉRO, pas le compte")
ei = E.creer({"nom": "Suppression"})["id"]
c_old = compte(ei, "PN-I1")
WA.noter_entrant(c_old, {"id": "s1", "from": "33600000141", "type": "text", "text": {"body": "STOP"}}, T0)
WA.noter_accord(c_old, TEL, "papier", T0)
WA.noter_envoi(c_old, TEL, type="texte", categorie="service", statut="envoye", id="e1", maintenant=T0)
WA.noter_desinscription(c_old, TEL, T0)
avant_cpt = WA.etat(c_old)["compteur"]
CP.supprimer(c_old)
c_new = compte(ei, "PN-I1")
check("R14.1 nouveau compte, même numéro : le STOP tient (refus stop)", refus(c_new, "tel:33600000141") == "stop")
check("R14.2 compteurs du mois gardés (sortants, service, entrants)",
      WA.etat(c_new)["compteur"] == avant_cpt == {"2026-10": {"entrants": 1, "sortants": 1, "service": 1}},
      WA.etat(c_new)["compteur"])
check("R14.3 désinscription et accord gardés", TEL in WA.etat(c_new)["desinscrits_marketing"]
      and WA.etat(c_new)["accords"][TEL]["source"] == "papier")
c_nu = CP.creer({"espace_id": ei, "plateforme": "whatsapp"})["id"]
for nom_, f_ in (("etat", lambda: WA.etat(c_nu)), ("noter_stop", lambda: WA.noter_stop(c_nu, TEL, T0)),
                 ("controler", lambda: WA.controler(c_nu, TEL, type="texte", categorie=None, dernier_entrant=T0,
                                                    maintenant=T0))):
    try:
        f_()
        sans = False
    except ValueError as x:
        sans = "relié à aucun numéro" in str(x)
    check(f"R14.4 compte sans numéro : {nom_} -> ValueError", sans)
e_autre = E.creer({"nom": "Autre espace"})["id"]
CP.supprimer(c_new)
c_ail = compte(e_autre, "PN-I1")
WA.noter_accord(c_ail, "tel:33600000141", "papier", T0)
check("R14.5 le même numéro relié dans un AUTRE espace y part d'un état vide (rien ne suit en silence)",
      refus(c_ail, "tel:33600000141") is None and "tel:33600000141" not in WA.etat(c_ail)["stops"])
check("R14.6 … et l'état d'origine reste dans le fichier de l'espace d'origine",
      "tel:33600000141" in json.loads((_tmp / "espaces" / ei / "whatsapp.json").read_text(encoding="utf-8"))
      ["etat"]["PN-I1"]["stops"])

print("\n[R15] I2 : un modèle MARKETING exige un accord saisi")
cm2 = compte(E.creer({"nom": "Marketing"})["id"], "PN-MK")
IN = "tel:33600000151"
WA.noter_entrant(cm2, {"id": "k1", "from": "33600000151", "type": "text", "text": {"body": "bonjour"}}, T0)
check("R15.1 accord d'entrant : modèle MARKETING refusé (accord)",
      refus(cm2, IN, type="modele", categorie="MARKETING") == "accord")
try:
    WA.controler(cm2, IN, type="modele", categorie="marketing", dernier_entrant=None, maintenant=T0)
    msg_ = ""
except WA.WhatsappRefus as x:
    msg_ = x.message
check("R15.2 message distinct de « aucun accord »", "marketing" in msg_ and msg_ != "aucun accord de ce contact : aucun envoi",
      msg_)
check("R15.3 accord d'entrant : texte, boutons, UTILITY, AUTHENTICATION passent",
      refus(cm2, IN) is None and refus(cm2, IN, type="boutons") is None
      and refus(cm2, IN, type="modele", categorie="UTILITY", dernier_entrant=None) is None
      and refus(cm2, IN, type="modele", categorie="AUTHENTICATION", dernier_entrant=None) is None)
WA.noter_accord(cm2, IN, "formulaire", T0)
check("R15.4 accord saisi : modèle MARKETING passe", refus(cm2, IN, type="modele", categorie="MARKETING") is None)
WA.noter_entrant(cm2, {"id": "k2", "from": "33600000151", "type": "text", "text": {"body": "merci"}}, T0)
check("R15.5 un entrant ultérieur ne rétrograde pas l'accord saisi", WA.etat(cm2)["accords"][IN]["source"] == "formulaire"
      and refus(cm2, IN, type="modele", categorie="MARKETING") is None)
ALT, ALB = "tel:33600000152", "bsuid:FR.mk2"
WA.noter_entrant(cm2, {"id": "k3", "from": "33600000152", "from_user_id": "FR.mk2", "type": "text",
                       "text": {"body": "hey"}}, T0)
check("R15.6 groupe d'alias, accords d'entrant seulement : MARKETING refusé des deux côtés",
      refus(cm2, ALT, type="modele", categorie="MARKETING") == "accord"
      and refus(cm2, ALB, type="modele", categorie="MARKETING") == "accord")
WA.noter_accord(cm2, ALB, "papier", T0)
check("R15.7 accord saisi sur le BSUID : vaut pour le numéro lié (MARKETING passe des deux côtés)",
      refus(cm2, ALT, type="modele", categorie="MARKETING") is None
      and refus(cm2, ALB, type="modele", categorie="MARKETING") is None)

print("\n[R16] plafond par espace, entrants compris")
ep2 = E.creer({"nom": "Deux numéros"})["id"]
n1, n2 = compte(ep2, "PN-P1"), compte(ep2, "PN-P2")
for c_ in (n1, n2):
    WA.noter_accord(c_, TEL, "papier", T0)
WA.regler(n1, plafond_mois=3)
doc2 = json.loads((_tmp / "espaces" / ep2 / "whatsapp.json").read_text(encoding="utf-8"))
check("R16.1 le réglage est celui de l'espace (whatsapp.json `reglages`), lu par les deux numéros",
      {k: WA.reglages(ep2)[k] for k in ("plafond_mois", "marche_defaut")} == {"plafond_mois": 3, "marche_defaut": "33"}  # t311 : reglages porte aussi `agent`
      and WA.etat(n2)["plafond_mois"] == 3
      and doc2["reglages"]["plafond_mois"] == 3 and "plafond_mois" not in doc2["etat"]["PN-P1"], doc2)
WA.noter_envoi(n1, TEL, type="modele", categorie="UTILITY", statut="envoye", id="p1", maintenant=T0)
WA.noter_envoi(n2, TEL, type="texte", categorie="service", statut="envoye", id="p2", maintenant=T0)
check("R16.2 2 sortants sur deux numéros, plafond 3 : passe", refus(n1, TEL) is None and refus(n2, TEL) is None)
WA.noter_entrant(n2, {"id": "pin", "from": "33600000161", "type": "text", "text": {"body": "salut"}}, T0)
check("R16.3 un entrant compte : 2 sortants + 1 entrant = 3, les DEUX numéros refusés (plafond)",
      refus(n1, TEL) == "plafond" and refus(n2, TEL) == "plafond")
check("R16.4 compteurs par numéro, `service` par numéro",
      WA.etat(n1)["compteur"]["2026-10"] == {"sortants": 1, "service": 0}
      and WA.etat(n2)["compteur"]["2026-10"] == {"sortants": 1, "service": 1, "entrants": 1},
      [WA.etat(n1)["compteur"], WA.etat(n2)["compteur"]])
check("R16.5 un autre espace n'est pas touché", refus(cid, TEL) is None)
check("R16.6 le mois suivant : de nouveau permis",
      refus(n1, TEL, maintenant=datetime(2026, 11, 2, tzinfo=timezone.utc), dernier_entrant=datetime(2026, 11, 1, 23,
            tzinfo=timezone.utc)) is None)

print("\n[R17] mots d'arrêt élargis")
check("R17.1 arrêtez, arretez, arrête, arrete, désinscrire, desinscrire, cancel, quit, end, opt out, optout, opt-out",
      all(est_stop(t) for t in ("Arrêtez", "arretez", "Arrête !", "arrete", "Désinscrire", "desinscrire", "CANCEL", "quit",
                                "End.", "opt out", "Opt  Out", "optout", "opt-out", "unsubscribe")))
check("R17.2 un mot de politesse au plus : STOP svp, stop stp, Stop, merci, opt out please, unsubscribe thanks",
      all(est_stop(t) for t in ("STOP svp", "stop stp", "Stop, merci", "opt out please", "unsubscribe thanks",
                                "arrêtez SVP !")))
check("R17.3 pas STOP : « stop ou encore ? », « stop the music please », « stop svp merci », « merci stop »",
      not any(est_stop(t) for t in ("stop ou encore ?", "stop the music please", "stop svp merci", "merci stop", "endless",
                                    "please", "svp")))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
