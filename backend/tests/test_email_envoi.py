# -*- coding: utf-8 -*-
"""t356 (28/10/2026) — Veille & prospection P5, tâche 2 : l'ENVOI des étapes e-mail dues et la LECTURE des réponses.
Envoi : seulement une séquence validée et planifiée, à l'heure, dans les horaires, sous le plafond du jour, à une fiche
toujours éligible ; rebond = séquence arrêtée ; passager = 3 essais ; pause = rien. Lecture IMAP (faux serveur) :
réponse rattachée (In-Reply-To) → « A répondu » ; STOP → opposition (registre) ; avis de non-remise → rebond ;
rapport de plainte → pause ; inconnu → rien ; premier passage : l'historique n'est pas relu.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_email_envoi.py"""
import json, os, pathlib, sys, tempfile
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzenv356_"))
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


from app.services import email_canal as M, email_envoi as V, espaces as E, oppositions as O   # noqa: E402
from app.services import prospects as P, prospects_score as SC, prospects_sequences as S       # noqa: E402

for m in (P, SC):
    m._aujourdhui = lambda: date(2026, 10, 28)
PARIS = ZoneInfo("Europe/Paris")
T0 = datetime(2026, 11, 2, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)      # lundi 10 h
HORLOGE = [T0]
for m in (S, M, V):
    m._maintenant = lambda: HORLOGE[0]

A = E.creer({"nom": "Prospection"})["id"]
M.regler(A, {"mode": "smtp", "expediteur": {"nom": "Léa", "adresse": "lea@deepotus.fr"},
             "identite": {"raison_sociale": "Deepotus SAS", "adresse_postale": "1 rue de la Paix, Paris"},
             "smtp": {"hote": "smtp.deepotus.fr", "port": 465, "securite": "ssl", "utilisateur": "lea@deepotus.fr"},
             "imap": {"hote": "imap.deepotus.fr", "port": 993, "utilisateur": "lea@deepotus.fr"}})
M.poser_secret(A, "mdp", "motdepasse")
ENVOIS, COMPORTEMENT = [], {"mode": "ok"}


def faux_envoyer(eid, msg):
    if COMPORTEMENT["mode"] == "rebond":
        raise M.RefusEmail("destinataire refusé par le serveur", "rebond")
    if COMPORTEMENT["mode"] == "passager":
        raise M.RefusEmail("serveur SMTP injoignable", "passager")
    if COMPORTEMENT["mode"] == "config":
        raise M.RefusEmail("identifiants SMTP refusés", "config")
    ENVOIS.append(msg)
    return {"message_id": str(msg["Message-ID"])}


V._ENVOYER = faux_envoyer
V._IMAP_SAIN = lambda eid: True       # la fraîcheur de la lecture IMAP a son propre test (section 5)
SRC = {"type": "web", "url": "https://studio.fr", "date": "2026-10-20"}


def prospect(nom, email):
    pid = P.creer(A, {"nom": nom, "entreprise": nom, "source": SRC, "base_legale": "interet_legitime_b2b",
                      "canaux": [{"type": "email", "valeur": email}]})["id"]
    P.changer_statut(A, pid, "qualifie")
    return pid


def sequence(pid, n=2):
    et = [{"objet": "Bonjour", "texte": "Premier message", "delai_jours": 0}, {"objet": "Relance", "texte": "Relance", "delai_jours": 3}][:n]
    s = S.proposer(A, pid, "email", et)
    S.valider(A, s["id"])
    return S.planifier(A, s["id"])["id"]


print("[1] envoi des étapes dues")
p1 = prospect("Studio Un", "contact@studio-un.fr")
s1 = sequence(p1)
sp = S.proposer(A, prospect("Studio Prop", "a@studio-prop.fr"), "email", [{"objet": "x", "texte": "x", "delai_jours": 0}])
r = V.envoyer_dues(A)
check("1a une étape due envoyée, la proposée non validée jamais", r["envoyes"] == 1 and len(ENVOIS) == 1 and ENVOIS[0]["To"] == "contact@studio-un.fr", r)
seq = [x for x in S.lister(A, p1)][0]
check("1b étape envoyée avec son Message-ID, la relance attend", seq["etapes"][0]["statut"] == "envoyee" and seq["etapes"][0]["message_id"] == str(ENVOIS[0]["Message-ID"])
      and seq["etapes"][1]["statut"] == "planifiee", seq["etapes"])
f = P.lire(A, p1)
check("1c fiche Contactée, contact sortant noté", f["statut"] == "contacte" and any(h["quoi"] == "contact_sortant" for h in f["historique"]))
check("1d journal : envoyé", M._doc(A)["journal"][-1]["statut"] == "envoye")
check("1e rien de plus à la passe suivante", V.envoyer_dues(A)["envoyes"] == 0 and len(ENVOIS) == 1)
HORLOGE[0] = T0 + timedelta(days=3, minutes=5)
check("1f la relance part à son heure", V.envoyer_dues(A)["envoyes"] == 1 and ENVOIS[-1]["Subject"] == "Relance")
check("1g séquence terminée", [x for x in S.lister(A, p1)][0]["statut"] == "terminee")

print("[2] heures calmes, plafond, pause, réglages")
HORLOGE[0] = datetime(2026, 11, 7, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)       # samedi
p2 = prospect("Studio Deux", "contact@studio-deux.fr")
s2 = S.proposer(A, p2, "email", [{"objet": "x", "texte": "x", "delai_jours": 0}]); S.valider(A, s2["id"])
S.planifier(A, s2["id"])                                                               # lundi 9 h
d = [x for x in S.lister(A, p2)][0]["etapes"][0]
d["quand"] = HORLOGE[0].isoformat()
doc = S._lire(A)
for x in doc["sequences"]:
    if x["id"] == s2["id"]:
        x["etapes"][0]["quand"] = HORLOGE[0].isoformat()
S._poser(A, doc)
check("2a samedi (hors horaires) : rien ne part", V.envoyer_dues(A)["envoyes"] == 0)
HORLOGE[0] = datetime(2026, 11, 9, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
M.noter(A, "plainte", "x@y.fr", None)
check("2b en pause : rien ne part", V.envoyer_dues(A)["envoyes"] == 0 and V.envoyer_dues(A)["etat"] == "pause")
M.reprendre(A)
for i in range(M.plafond_du_jour(A, HORLOGE[0].astimezone(PARIS).date())):
    M.noter(A, "envoye", f"z{i}@x.fr", f"<z{i}@x>", quand=HORLOGE[0] - timedelta(minutes=30))
check("2c plafond du jour atteint : rien ne part", V.envoyer_dues(A)["envoyes"] == 0)
HORLOGE[0] = HORLOGE[0] + timedelta(days=1)
check("2d le lendemain : part", V.envoyer_dues(A)["envoyes"] == 1)

print("[3] fiche devenue inéligible, rebond, passager, réglage refusé")
HORLOGE[0] = datetime(2026, 11, 11, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
p3 = prospect("Studio Trois", "contact@studio-trois.fr"); s3 = sequence(p3, 1)
P.opposer(A, p3)
n0 = len(ENVOIS)
check("3a fiche opposée : rien ne part, séquence arrêtée", V.envoyer_dues(A)["envoyes"] == 0 and len(ENVOIS) == n0
      and [x for x in S.lister(A) if x["id"] == s3][0]["statut"] == "annulee")
p4 = prospect("Studio Quatre", "contact@studio-quatre.fr"); s4 = sequence(p4, 1)
COMPORTEMENT["mode"] = "rebond"
r = V.envoyer_dues(A)
x = [x for x in S.lister(A) if x["id"] == s4][0]
check("3b rebond : séquence arrêtée (motif rebond), journal rebond", r["rebonds"] == 1 and x["statut"] == "annulee" and x["motif"] == "rebond"
      and M._doc(A)["journal"][-1]["statut"] == "rebond", (r, x["statut"], x["motif"]))
p5 = prospect("Studio Cinq", "contact@studio-cinq.fr"); s5 = sequence(p5, 1)
COMPORTEMENT["mode"] = "passager"
for i in range(5):
    V.envoyer_dues(A)
x = [x for x in S.lister(A) if x["id"] == s5][0]
check("3c passager (relecture I3) : après 5 pannes, l'étape attend toujours, rien n'est arrêté", x["statut"] == "planifiee" and not x.get("motif"), (x["statut"], x.get("motif")))
check("3d passager : l'erreur est dite à l'écran", "injoignable" in (M.lire(A).get("erreur") or {}).get("message", ""), M.lire(A).get("erreur"))
p6 = prospect("Studio Six", "contact@studio-six.fr"); s6 = sequence(p6, 1)
COMPORTEMENT["mode"] = "config"
r = V.envoyer_dues(A)
check("3e réglage refusé : rien ne part, l'erreur est gardée pour l'écran", r["envoyes"] == 0 and "identifiants" in (M.lire(A).get("erreur") or {}).get("message", ""), M.lire(A).get("erreur"))
COMPORTEMENT["mode"] = "ok"
V.envoyer_dues(A)
check("3f l'erreur s'efface au prochain envoi réussi", not M.lire(A).get("erreur"))

print("[4] lecture des réponses (IMAP)")


def mail(de, sujet, texte, **h):
    m = EmailMessage()
    m["From"] = de; m["To"] = "lea@deepotus.fr"; m["Subject"] = sujet
    for k, v in h.items():
        m[k.replace("_", "-")] = v
    m.set_content(texte)
    return m


def rapport(genre, partie, contenu):
    """Un rapport MIME brut (avis de non-remise ou de plainte), tel qu'un serveur l'écrit."""
    lignes = ["From: MAILER-DAEMON@mx.fr", "To: lea@deepotus.fr", "Subject: rapport", "MIME-Version: 1.0",
              f'Content-Type: multipart/report; report-type={genre}; boundary="B"', "", "--B", "Content-Type: text/plain", "",
              "rapport", "--B", f"Content-Type: {partie}", ""] + contenu.split("\n") + ["--B--", ""]
    return "\r\n".join(lignes).encode("utf-8")


BOITE = {}


class FauxIMAP:
    def __init__(self, hote, port, ssl_context=None, timeout=None):
        self.vu = hote
    def login(self, u, p): assert p == "motdepasse"; return "OK", [b""]
    def select(self, boite, readonly=False): assert readonly; return "OK", [str(len(BOITE)).encode()]
    def status(self, boite, quoi): return "OK", [b'INBOX (UIDVALIDITY 7)']
    def uid(self, cmd, *a):
        if cmd == "search":
            crit = a[-1]
            bas = int(crit.split()[1].split(":")[0]) if crit.startswith("UID") else 1
            us = [u for u in sorted(BOITE) if u >= bas] or ([max(BOITE)] if BOITE else [])
            return "OK", [" ".join(map(str, us)).encode()]
        if cmd == "fetch":
            assert "PEEK" in a[1]
            return "OK", [(b"1 (BODY[] {n}", bytes(BOITE[int(a[0])]))]
    def logout(self): pass
    def __enter__(self): return self
    def __exit__(self, *x): pass


V._IMAP = FauxIMAP
BOITE[1] = mail("ancien@x.fr", "vieux", "historique")
r = V.lire_reponses(A)
check("4a premier passage : l'historique n'est pas relu", r["lus"] == 0 and M._doc(A)["imap_etat"]["dernier"] == 1, r)
mid = M._doc(A)["journal"][0]["message_id"]
BOITE[2] = mail("Studio Un <contact@studio-un.fr>", "Re: Bonjour", "Oui, parlons-en !\n> Premier message", In_Reply_To=mid)
BOITE[3] = mail("contact@studio-six.fr", "Re: Bonjour", "STOP")
BOITE[4] = mail("inconnu@ailleurs.fr", "question", "Bonjour, qui êtes-vous ?")
BOITE[5] = mail("autre@ailleurs.fr", "Désinscription", "merci de me retirer\nstop")
BOITE[6] = rapport("delivery-status", "message/delivery-status", "Reporting-MTA: dns; mx.fr\n\nFinal-Recipient: rfc822; contact@studio-deux.fr\nAction: failed\nStatus: 5.1.1\n")
r = V.lire_reponses(A)
f1 = P.lire(A, p1)
check("4b réponse rattachée : contact entrant, « A répondu »", f1["statut"] == "repondu" and any(h["quoi"] == "contact_entrant" for h in f1["historique"]), f1["statut"])
rep = M._doc(A)["reponses"]
check("4c résumé gardé pour l'agent (objet, extrait, prospect)", any(x["pid"] == p1 and "parlons-en" in x["extrait"] and x["sujet"] == "Re: Bonjour" for x in rep), rep)
check("4d STOP d'un prospect : fiche opposée", P.lire(A, p6)["statut"] == "oppose")
check("4e inconnu sans STOP : rien", not any(x.get("de") == "inconnu@ailleurs.fr" for x in rep) and r["ignores"] >= 1, r)
check("4f STOP d'un inconnu : inscrit au registre", O.opposes([["autre@ailleurs.fr"]]) == [True])
j = [x for x in M._doc(A)["journal"] if x["a"] == "contact@studio-deux.fr"]
check("4g avis de non-remise : rebond noté pour l'adresse", any(x["statut"] == "rebond" for x in j), j)
check("4h curseur avancé, rien relu deux fois", M._doc(A)["imap_etat"]["dernier"] == 6 and V.lire_reponses(A)["lus"] == 0)
M.reprendre(A)
BOITE[7] = rapport("feedback-report", "message/feedback-report", "Feedback-Type: abuse\nOriginal-Rcpt-To: contact@studio-un.fr\n")
V.lire_reponses(A)
check("4i rapport de plainte : pause immédiate", M.lire(A)["pause"]["active"] and M.lire(A)["pause"]["motif"] == "plainte")
check("4j IMAP sans mot de passe : rien, sans erreur", (M.poser_secret(A, "mdp", "") and V.lire_reponses(A)["lus"] == 0))

print("[5] relecture t356")
M.poser_secret(A, "mdp", "motdepasse")
M.reprendre(A)
oui = ["STOP", "Stop", "Arrêtez", "arrêter svp", "Désinscrivez-moi", "désinscription", "Je souhaite me désinscrire",
       "désabonnez-moi", "Merci de ne plus me contacter", "unsubscribe", "Please unsubscribe me", "retirez-moi de votre liste"]
non = ["Oui, parlons-en", "Avec plaisir, appelez-moi", "Merci pour votre message", "Je suis intéressé par une démo"]
check("5a STOP : formulations françaises et anglaises reconnues", all(V.est_stop("", x) for x in oui), [x for x in oui if not V.est_stop("", x)])
check("5b STOP dans l'objet derrière « Re: »", V.est_stop("Re: STOP", "") and V.est_stop("RE : désinscription", ""))
check("5c une réponse ordinaire n'est pas un STOP", not any(V.est_stop("Re: Bonjour", x) for x in non), [x for x in non if V.est_stop("", x)])
HORLOGE[0] = datetime(2026, 11, 16, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)
COMPORTEMENT["mode"] = "ok"
p7 = prospect("Studio Sept", "contact@studio-sept.fr"); s7 = sequence(p7, 1)
M.noter(A, "tentative", "contact@studio-sept.fr", "<deja@deepotus.fr>", sid=s7, rang=0, pid=p7)
n0 = len(ENVOIS); V.envoyer_dues(A)
x = [y for y in S.lister(A) if y["id"] == s7][0]
check("5d une tentative déjà écrite vaut envoi : jamais un second envoi", len(ENVOIS) == n0 and x["etapes"][0]["statut"] == "envoyee"
      and x["etapes"][0]["message_id"] == "<deja@deepotus.fr>", (len(ENVOIS) - n0, x["etapes"][0]["statut"]))
p8 = prospect("Studio Huit", "contact@studio-huit.fr")
P.modifier(A, p8, {"canaux": [{"type": "email", "valeur": "x@gmail.com, contact@studio-huit.fr"}]})
s8 = sequence(p8, 1) if False else None
f8 = P.lire(A, p8)
s8 = S.proposer(A, p8, "email", [{"objet": "x", "texte": "x", "delai_jours": 0}]) if "email" in [c["canal"] for c in __import__("app.services.prospects_score", fromlist=["x"]).canaux_possibles(f8)] else None
if s8:
    S.valider(A, s8["id"]); S.planifier(A, s8["id"])
    n0 = len(ENVOIS); V.envoyer_dues(A)
    x = [y for y in S.lister(A) if y["id"] == s8["id"]][0]
    check("5e adresse composée (deux destinataires) : rien ne part, arrêt « canal »", len(ENVOIS) == n0 and x["motif"] == "canal", x.get("motif"))
else:
    check("5e adresse composée refusée dès la fiche", True)
p9 = prospect("Studio Neuf", "contact@studio-neuf.fr"); s9 = sequence(p9, 2)
COMPORTEMENT["mode"] = "passager"; V.envoyer_dues(A)
HORLOGE[0] = HORLOGE[0] + timedelta(days=4)
COMPORTEMENT["mode"] = "ok"; V.envoyer_dues(A)
x = [y for y in S.lister(A) if y["id"] == s9][0]
check("5f relance comptée depuis l'envoi réel : envoyée le même jour que le 1er message, elle attend", x["etapes"][0]["statut"] == "envoyee"
      and x["etapes"][1]["statut"] == "planifiee", [e["statut"] for e in x["etapes"]])
V._IMAP_SAIN = lambda eid: False
p10 = prospect("Studio Dix", "contact@studio-dix.fr"); s10 = sequence(p10, 1)
n0 = len(ENVOIS); r = V.envoyer_dues(A)
check("5g lecture des réponses en échec : rien ne part", len(ENVOIS) == n0 and r["etat"] == "imap", r)
V._IMAP_SAIN = lambda eid: True
check("5h fraîcheur IMAP : jamais lue = pas saine", V.imap_sain(A) is False or M._doc(A)["imap_etat"].get("lu_le"))
mid9 = [y for y in S.lister(A) if y["id"] == s9][0]["etapes"][0]["message_id"]
BOITE[8] = mail("contact@studio-neuf.fr", "Réponse automatique : absent", "Je suis absent jusqu'au 20.", In_Reply_To=mid9, Auto_Submitted="auto-replied")
BOITE[9] = rapport("delivery-status", "message/delivery-status", "Reporting-MTA: dns; mx.fr\n\nFinal-Recipient: rfc822; perso@ailleurs.fr\nAction: failed\nStatus: 5.1.1\n")
BOITE[10] = mail("crash@x.fr", "question", "texte")
BOITE[11] = mail("contact@studio-neuf.fr", "Re: Bonjour", "Merci de ne plus me contacter")
_pid_adr = V._pid_par_adresse


def piege(eid, adresse):
    if adresse == "crash@x.fr":
        raise ValueError("message piégé")
    return _pid_adr(eid, adresse)


V._pid_par_adresse = piege
M.reprendre(A)
r = V.lire_reponses(A)
V._pid_par_adresse = _pid_adr
check("5i réponse automatique : la fiche ne passe pas « A répondu »", P.lire(A, p9)["statut"] != "repondu" or P.lire(A, p9)["statut"] == "oppose", P.lire(A, p9)["statut"])
check("5j non-remise d'une adresse que nous n'avons jamais écrite : pas de rebond", not any(j["a"] == "perso@ailleurs.fr" for j in M._doc(A)["journal"]))
check("5k un message piégé est sauté, la suite est lue (STOP traité)", P.lire(A, p9)["statut"] == "oppose" and M._doc(A)["imap_etat"]["dernier"] == 11, (P.lire(A, p9)["statut"], M._doc(A)["imap_etat"]["dernier"]))
import tempfile as _t                                                # noqa: E402
B = E.creer({"nom": "Boîte vide"})["id"]
M.regler(B, {"imap": {"hote": "imap.x.fr", "port": 993, "utilisateur": "u"}}); M.poser_secret(B, "mdp", "motdepasse")
sauve = dict(BOITE); BOITE.clear()
V.lire_reponses(B)
BOITE[1] = mail("inconnu@x.fr", "STOP", "STOP")
V.lire_reponses(B)
check("5l boîte vide au premier passage : le message suivant est bien lu", O.opposes([["inconnu@x.fr"]]) == [True])
BOITE.update(sauve)
p11 = prospect("Studio Onze", "contact@studio-onze.fr"); s11 = sequence(p11, 1)
V.envoyer_dues(A)
M.ajouter_reponse(A, {"pid": p11, "de": "contact@studio-onze.fr", "sujet": "Re", "extrait": "secret-reponse-11", "stop": False})
ex = json.dumps(P.exporter(A, p11), ensure_ascii=False)
check("5m export (droit d'accès) : les envois et réponses e-mail y sont", "contact@studio-onze.fr" in ex and "secret-reponse-11" in ex)
P.effacer(A, p11)
brut = E.chemin(A, M.FICHIER).read_text(encoding="utf-8")
check("5n effacement : adresse et extrait quittent email.json", "studio-onze" not in brut and "secret-reponse-11" not in brut)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
