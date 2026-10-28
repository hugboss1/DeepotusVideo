# -*- coding: utf-8 -*-
"""t356 (28/10/2026) — Veille & prospection P5, tâche 1 : le CANAL E-MAIL d'un espace (service email_canal).
Réglages (identité obligatoire, SMTP ou Brevo, IMAP), secrets scellés DPAPI jamais rendus, composition (pied d'identité,
STOP, List-Unsubscribe, en-têtes sans injection), adaptateurs SMTP / Brevo (faux), plafond 10/20/30 borné par le réglage,
taux de rebond et pause.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_email_canal.py"""
import json, os, pathlib, sys, tempfile
from datetime import date, datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmail356_"))
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


from app.services import email_canal as M, espaces as E   # noqa: E402

A = E.creer({"nom": "Prospection"})["id"]


def refus(fn, code=None):
    try:
        fn()
    except M.RefusEmail as e:
        return code is None or e.code == code, e.code
    return False, "aucun refus"


REGL = {"mode": "smtp", "expediteur": {"nom": "Léa de Studio", "adresse": "lea@deepotus.fr"},
        "identite": {"raison_sociale": "Deepotus SAS", "adresse_postale": "1 rue de la Paix, 75002 Paris"},
        "smtp": {"hote": "smtp.deepotus.fr", "port": 465, "securite": "ssl", "utilisateur": "lea@deepotus.fr"},
        "imap": {"hote": "imap.deepotus.fr", "port": 993, "utilisateur": "lea@deepotus.fr"}, "plafond_jour": 25}

print("[1] réglages")
v = M.lire(A)
check("1a vierge : non prêt, ce qui manque est dit", v["pret"] is False and {"expediteur", "identite", "smtp", "imap", "mdp"} <= set(v["manques"]), v["manques"])
v = M.regler(A, REGL)
check("1b réglé : champs gardés, plafond 25", v["expediteur"]["adresse"] == "lea@deepotus.fr" and v["plafond_jour"] == 25 and v["smtp"]["port"] == 465)
check("1c sans mot de passe : encore non prêt", v["pret"] is False and v["manques"] == ["mdp"], v["manques"])
check("1d adresse illisible refusée", refus(lambda: M.regler(A, {"expediteur": {"nom": "x", "adresse": "pas-une-adresse"}}), "champ")[0])
check("1e nom avec retour à la ligne refusé (injection d'en-tête)", refus(lambda: M.regler(A, {"expediteur": {"nom": "a\r\nBcc: x@y.fr", "adresse": "a@b.fr"}}), "champ")[0])
check("1f mode inconnu refusé", refus(lambda: M.regler(A, {"mode": "sendgrid"}), "champ")[0])
check("1g port hors bornes refusé", refus(lambda: M.regler(A, {"smtp": dict(REGL["smtp"], port=70000)}), "champ")[0])
check("1h hôte avec schéma refusé", refus(lambda: M.regler(A, {"imap": dict(REGL["imap"], hote="https://imap.x.fr")}), "champ")[0])
check("1i plafond au-delà de 30 refusé", refus(lambda: M.regler(A, {"plafond_jour": 31}), "champ")[0])
check("1j sécurité inconnue refusée", refus(lambda: M.regler(A, {"smtp": dict(REGL["smtp"], securite="aucune")}), "champ")[0])
check("1k champ inconnu refusé", refus(lambda: M.regler(A, {"secrets": {"mdp": "x"}}), "champ")[0])

print("[2] secrets")
v = M.poser_secret(A, "mdp", "s3cret-motdepasse")
check("2a mot de passe posé : prêt, jamais rendu", v["pret"] is True and v["mdp_pose"] is True and "s3cret" not in json.dumps(v), v)
brut = E.chemin(A, M.FICHIER).read_text(encoding="utf-8")
check("2b jamais en clair sur le disque", "s3cret-motdepasse" not in brut)
check("2c relu par le service", M._secret(A, "mdp") == "s3cret-motdepasse")
check("2d secret inconnu refusé", refus(lambda: M.poser_secret(A, "autre", "x"), "champ")[0])
M.regler(A, {"mode": "brevo"})
check("2e Brevo sans clé : non prêt", M.lire(A)["manques"] == ["brevo"], M.lire(A)["manques"])
M.poser_secret(A, "brevo", "xkeysib-abc")
check("2f Brevo avec clé : prêt", M.lire(A)["pret"] is True)
M.regler(A, {"mode": "smtp"})

print("[3] composition")
m = M.composer(M._doc(A), "contact@studio-lune.fr", "Vos vidéos\r\nBcc: espion@x.fr", "Bonjour Léa,\nune idée.", "<abc@deepotus.fr>")
corps = m.get_body(preferencelist=("plain",)).get_content()
check("3a destinataire, expéditeur avec nom", m["To"] == "contact@studio-lune.fr" and "lea@deepotus.fr" in m["From"] and "Studio" in m["From"], (m["To"], m["From"]))
check("3b objet sans retour à la ligne (pas de Bcc injecté)", "\n" not in str(m["Subject"]) and m["Bcc"] is None, m["Subject"])
check("3c pied : raison sociale, adresse postale, répondre STOP", "Deepotus SAS" in corps and "75002 Paris" in corps and "STOP" in corps, corps)
check("3d List-Unsubscribe mailto vers l'expéditeur", m["List-Unsubscribe"] == "<mailto:lea@deepotus.fr?subject=STOP>", m["List-Unsubscribe"])
check("3e Message-ID posé", m["Message-ID"] == "<abc@deepotus.fr>")
check("3f nouveau Message-ID au domaine de l'expéditeur", M.nouvel_id(M._doc(A)).endswith("@deepotus.fr>"))

print("[4] adaptateurs (faux)")
VU = []


class FauxSMTP:
    def __init__(self, hote, port, timeout=None, context=None):
        VU.append(("connexion", hote, port))
    def starttls(self, context=None): VU.append(("starttls",))
    def login(self, u, p): VU.append(("login", u, p))
    def send_message(self, msg): VU.append(("envoi", msg["To"])); return {}
    def quit(self): VU.append(("quit",))
    def __enter__(self): return self
    def __exit__(self, *a): self.quit()


M._SMTP_SSL = FauxSMTP
M._SMTP = FauxSMTP
r = M.envoyer(A, m)
check("4a SMTP SSL : connexion, login avec le secret, envoi", ("login", "lea@deepotus.fr", "s3cret-motdepasse") in VU and ("envoi", "contact@studio-lune.fr") in VU, VU)
check("4b rend le Message-ID", r["message_id"] == "<abc@deepotus.fr>")
M.regler(A, {"smtp": dict(REGL["smtp"], securite="starttls", port=587)})
VU.clear(); M.envoyer(A, m)
check("4c STARTTLS : starttls avant login", [x[0] for x in VU][:3] == ["connexion", "starttls", "login"], VU)
import smtplib                                                      # noqa: E402


class Refuse(FauxSMTP):
    def send_message(self, msg):
        raise smtplib.SMTPRecipientsRefused({msg["To"]: (550, b"no such user")})


M._SMTP = Refuse
r = refus(lambda: M.envoyer(A, m), "rebond")
check("4d destinataire refusé (550) : rebond définitif", r[0], r)


class Panne(FauxSMTP):
    def __init__(self, *a, **k):
        raise OSError("connexion refusée")


M._SMTP = Panne
check("4e serveur injoignable : échec passager", refus(lambda: M.envoyer(A, m), "passager")[0])


class Auth(FauxSMTP):
    def login(self, u, p):
        raise smtplib.SMTPAuthenticationError(535, b"bad")


M._SMTP = Auth
r = refus(lambda: M.envoyer(A, m), "config")
check("4f identifiants refusés : erreur de réglage, sans le mot de passe", r[0], r)
M._SMTP = FauxSMTP
APPELS = []


def faux_brevo(cle, corps):
    APPELS.append((cle, corps))
    return 201, {"messageId": "<brevo-1@smtp-relay>"}


M._BREVO = faux_brevo
M.regler(A, {"mode": "brevo"})
r = M.envoyer(A, m)
c = APPELS[0][1] if APPELS else {}
check("4g Brevo : clé, expéditeur, destinataire, objet, texte, en-têtes", APPELS and APPELS[0][0] == "xkeysib-abc" and c["sender"]["email"] == "lea@deepotus.fr"
      and c["to"] == [{"email": "contact@studio-lune.fr"}] and "STOP" in c["textContent"] and c["headers"]["List-Unsubscribe"].startswith("<mailto:"), c)
M._BREVO = lambda cle, corps: (400, {"code": "invalid_parameter", "message": "email is not valid"})
check("4h Brevo 400 : rebond définitif", refus(lambda: M.envoyer(A, m), "rebond")[0])
M._BREVO = lambda cle, corps: (401, {"code": "unauthorized"})
check("4i Brevo 401 : erreur de réglage", refus(lambda: M.envoyer(A, m), "config")[0])
M._BREVO = lambda cle, corps: (503, {})
check("4j Brevo 503 : passager", refus(lambda: M.envoyer(A, m), "passager")[0])
M.regler(A, {"mode": "smtp"})

print("[5] plafond, journal, rebonds, pause")
PARIS = E and __import__("zoneinfo").ZoneInfo("Europe/Paris")
J0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
check("5a plafond du jour sans envoi : 10 (1re semaine)", M.plafond_du_jour(A, J0.date()) == 10)
for i in range(10):
    M.noter(A, "envoye", f"p{i}@x.fr", f"<m{i}@deepotus.fr>", quand=J0 + timedelta(minutes=i))
check("5b 10 envois le jour même : plafond atteint", M.reste_du_jour(A, J0.date()) == 0)
check("5c 2e semaine : 20, mais borné par le réglage (25 → 20)", M.plafond_du_jour(A, J0.date() + timedelta(days=8)) == 20)
check("5d 3e semaine : 30 borné à 25 par le réglage", M.plafond_du_jour(A, J0.date() + timedelta(days=15)) == 25)
check("5e pas de pause à 0 rebond", M.lire(A)["pause"]["active"] is False)
M.noter(A, "rebond", "p1@x.fr", "<m1@deepotus.fr>", quand=J0 + timedelta(hours=1))
check("5f 1 rebond sur 10 envois (10 %) : pause", M.lire(A)["pause"]["active"] is True and M.lire(A)["pause"]["motif"] == "rebonds", M.lire(A)["pause"])
check("5g taux rendu", abs(M.lire(A, maintenant=J0 + timedelta(hours=2))["taux_rebond"] - 0.1) < 1e-9, M.lire(A)["taux_rebond"])
M.reprendre(A)
check("5h reprendre : pause levée, rebonds oubliés pour le calcul", M.lire(A)["pause"]["active"] is False)
M.noter(A, "plainte", "p2@x.fr", None, quand=J0 + timedelta(hours=3))
check("5i plainte : pause immédiate", M.lire(A)["pause"]["active"] is True and M.lire(A)["pause"]["motif"] == "plainte")
check("5j en pause : envoyer refusé", refus(lambda: M.envoyer(A, m), "pause")[0])
M.reprendre(A)
check("5k le journal ne garde que 2000 lignes", M.MAX_JOURNAL == 2000)

print("[6] fichier illisible, espace inconnu")
check("6a espace inconnu : refus", refus(lambda: M.lire("es_inconnu00"), "inconnu")[0])
f = E.chemin(A, M.FICHIER)
f.write_text("{pas du json", encoding="utf-8")
check("6b illisible : mis de côté, réglages vierges", M.lire(A)["pret"] is False and any(x.name.startswith("email.json.illisible-") for x in f.parent.iterdir()))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
