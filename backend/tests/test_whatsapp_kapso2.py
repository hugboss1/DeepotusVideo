# -*- coding: utf-8 -*-
"""t311 tâche 2 (27/10/2026) — Kapso étendu, médias rangés, modèles complets.
Plan docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md (tâche 2). Faux `kapso._requete` (aucun réseau), data-dir
temporaire, TestClient. Ce que ce banc garde :
  K1  `kapso.modeles` : pagination par `paging.cursors.after` (3 pages lues, 5 au plus), `statut=None` = pas de filtre.
  K2  `kapso.marquer_lu` : `typing_indicator` seulement si `ecrit`.
  K3  `prendre_fil` / `rendre_fil` : corps exact ; 502 et 409 `thread_control_in_progress` jamais réessayés.
  K4  `televerser_media` : multipart reçu par le faux (`fichiers`), id rendu ; MIME et poids refusés AVANT tout appel ;
      un faux `_requete` sans `fichiers` marche encore pour un appel ordinaire.
  K5  `preferences_marketing` : un BSUID est transmis tel quel.
  K6  `WE.modeles` : `statut`, `composants` (entête, boutons) ; `tous=False` = approuvés seulement.
  K7  envoi modèle avec `entete` et `boutons` : composants Meta exacts ; refus (payload trop long, index inconnu, entête).
  K8  envoi image : corps exact, hors fenêtre -> 409 `fenetre`, validations.
  K9  envoi boutons : `entete_media_id` et `ids` fournis ; validations.
  K10 médias : `lire` range les entrants (confiné, > 16 Mo non rangé, échec = message gardé), `ranger_media` refuse `../x`,
      la route média sert le fichier local sans appel Kapso.
  K11 routes : POST relire (= GET messages), POST fil, GET modeles?tous=1 ; `WE.marquer_lu`.
Run (depuis backend/) : & $PY tests/test_whatsapp_kapso2.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwak2_"))
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
JOURNAL = []
logger.add(lambda m: JOURNAL.append(str(m)), level="DEBUG")

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
from fastapi.testclient import TestClient                            # noqa: E402
from app.config import settings                                      # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import comptes as CP, espaces as E, kapso as KA, pricing as PR  # noqa: E402
from app.services import whatsapp as WA, whatsapp_echanges as WE     # noqa: E402

CLE = "CLE-KAPSO-SECRETE-88"
PL, PX = KA.PLATFORM, KA.PROXY


def poser_cle(v):
    os.environ["KAPSO_API_KEY"] = v
    setattr(settings, "KAPSO_API_KEY", v)


def maintenant():
    return datetime.now(timezone.utc)


def iso(d):
    return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class Faux:
    def __init__(self):
        self.appels = []              # (méthode, chemin, params, json, fichiers)
        self.pages_modeles = {}       # waba -> [pages] (page i servie pour after=i)
        self.infini = False           # modèles : toujours un curseur de plus
        self.envois = []
        self.refus = []               # [(statut, corps)] pour le prochain appel thread_control
        self.convs = {}
        self.msgs = {}
        self.media = {}               # id -> (octets, mime)
        self.televerse = []
        self.sans_next = False        # modèles : curseur sans `paging.next`


F = Faux()


async def faux_requete(methode, url, *, json=None, params=None, fichiers=None):
    await asyncio.sleep(0)
    chemin = url.replace(PX, "").replace(PL, "").replace(f"https://{KA.HOTE}", "").split("?")[0]
    F.appels.append((methode, chemin, dict(params or {}), json, fichiers))
    parts = chemin.strip("/").split("/")
    if methode == "POST" and len(parts) == 2 and parts[1] == "messages":
        if (json or {}).get("status") == "read":
            return 200, {"success": True}, {}
        F.envois.append(json)
        return 200, {"messaging_product": "whatsapp", "messages": [{"id": f"wamid.E{len(F.envois)}"}]}, {}
    if methode == "POST" and len(parts) == 2 and parts[1] == "thread_control":
        if F.refus:
            st, corps = F.refus.pop(0)
            return st, corps, {}
        return 200, {"success": True}, {}
    if methode == "POST" and len(parts) == 2 and parts[1] == "media":
        F.televerse.append(fichiers)
        return 200, {"id": "MEDIA-UP-1"}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "message_templates":
        i = int((params or {}).get("after") or 0)
        if F.infini:
            return 200, {"data": [{"name": f"m{i}", "language": "fr", "status": "APPROVED"}],
                         "paging": {"cursors": {"after": str(i + 1)}, "next": "https://x/n"}}, {}
        pages = F.pages_modeles.get(parts[0], [[]])
        page = pages[i] if i < len(pages) else []
        apres = str(i + 1) if i + 1 < len(pages) else None
        if F.sans_next:
            return 200, {"data": page, "paging": {"cursors": {"after": str(i + 1)}}}, {}
        return 200, {"data": page, "paging": ({"cursors": {"after": apres}, "next": "https://x/n"} if apres else {})}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "conversations":
        return 200, {"data": [dict(x) for x in F.convs.get(parts[0], [])], "paging": {"cursors": {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "messages":
        pages = F.msgs.get(parts[0], [[]])
        return 200, {"data": [dict(x) for x in pages[0]], "paging": {}}, {}
    if methode == "GET" and chemin.startswith("/whatsapp/contacts/") and chemin.endswith("/marketing_preferences"):
        return 200, {"data": []}, {}
    if methode == "GET" and parts[0] == "dl":
        octets, mime = F.media[parts[1]]
        return 200, octets, {"content-type": mime}
    if methode == "GET" and len(parts) == 1 and parts[0] in F.media:
        return 200, {"id": parts[0], "mime_type": F.media[parts[0]][1],
                     "download_url": f"https://api.kapso.ai/dl/{parts[0]}?token=JETON"}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


async def faux_dormir(_s):
    return None


KA._requete = faux_requete
KA._dormir = faux_dormir


def run(coro):
    return asyncio.run(coro)


poser_cle(CLE)
GRILLE = {"33": {"marketing": 0.0859, "utility": 0.03, "authentication": 0.03, "service": 0.01}}
c = TestClient(app, client=("127.0.0.1", 50000))
c.__enter__()
E.lire()
PR.save({"whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0})

boite = E.creer({"nom": "Atelier Soleil"})["id"]
cid = CP.creer({"espace_id": boite, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": "PN-1", "WHATSAPP_WABA_ID": "WABA-1"})
TEL = "tel:33612345678"
WA.noter_accord(cid, TEL, "formulaire")


def conv(pid, tel, il_y_a=timedelta(hours=1)):
    F.convs.setdefault(pid, []).append({"id": "conv-1", "phone_number": tel, "status": "active", "kapso": {
        "contact_name": "Léa", "last_inbound_at": iso(maintenant() - il_y_a)}})


def envoyer(ident, envoi):
    return c.post(f"/api/whatsapp/{cid}/envoyer", json={"identite": ident, "envoi": envoi})


def dernier_envoi():
    return F.envois[-1] if F.envois else None


# ---------------------------------------------------------------------------------------------------------------------
print("\n[K1] kapso.modeles : pagination")
F.pages_modeles["WABA-1"] = [[{"name": "a", "status": "APPROVED"}], [{"name": "b", "status": "APPROVED"}],
                             [{"name": "c", "status": "PENDING"}]]
F.appels.clear()
res = run(KA.modeles("WABA-1"))
check("K1.1 trois pages lues, suivies par `after`", [x["name"] for x in res] == ["a", "b", "c"]
      and [a[2].get("after") for a in F.appels] == [None, "1", "2"], (res, F.appels))
check("K1.2 statut APPROVED par défaut, limite 100", F.appels[0][2].get("status") == "APPROVED"
      and F.appels[0][2].get("limit") == 100, F.appels[0])
F.appels.clear()
run(KA.modeles("WABA-1", statut=None))
check("K1.3 statut=None : aucun filtre `status`", all("status" not in a[2] for a in F.appels), F.appels)
F.infini = True
F.appels.clear()
res = run(KA.modeles("WABA-1"))
check("K1.4 curseur sans fin : cinq pages au plus", len(F.appels) == 5 and len(res) == 5, (len(F.appels), len(res)))
F.infini = False
F.pages_modeles["WABA-1"] = [[{"name": "a", "language": "fr"}], [{"name": "a", "language": "fr"}, {"name": "a", "language": "en"}],
                             [{"name": "z", "language": "fr"}]]
F.sans_next = True
F.appels.clear()
res = run(KA.modeles("WABA-1"))
check("K1.5 `paging.next` absent : une seule page lue", len(F.appels) == 1 and [x["name"] for x in res] == ["a"], (F.appels, res))
F.sans_next = False
res = run(KA.modeles("WABA-1"))
check("K1.6 dédoublonnage par (nom, langue)", [(x["name"], x["language"]) for x in res] == [
    ("a", "fr"), ("a", "en"), ("z", "fr")], res)
F.pages_modeles["WABA-1"] = [[{"name": "a", "status": "APPROVED"}], [], [{"name": "jamais", "status": "APPROVED"}]]
F.appels.clear()
res = run(KA.modeles("WABA-1"))
check("K1.7 page vide : arrêt", len(F.appels) == 2 and [x["name"] for x in res] == ["a"], (F.appels, res))

print("\n[K2] kapso.marquer_lu : typing_indicator")
F.appels.clear()
run(KA.marquer_lu("PN-1", "wamid.X"))
check("K2.1 sans `ecrit` : corps t310 exact", F.appels[-1][3] == {"messaging_product": "whatsapp", "status": "read",
                                                                 "message_id": "wamid.X"}, F.appels[-1][3])
run(KA.marquer_lu("PN-1", "wamid.X", ecrit=True))
check("K2.2 `ecrit` : typing_indicator text en plus", F.appels[-1][3] == {
    "messaging_product": "whatsapp", "status": "read", "message_id": "wamid.X", "typing_indicator": {"type": "text"}},
      F.appels[-1][3])

print("\n[K3] thread_control")
F.appels.clear()
run(KA.prendre_fil("PN-1", {"to": "33612345678"}))
check("K3.1 prendre : POST /PN-1/thread_control, corps exact", F.appels[-1][:2] == ("POST", "/PN-1/thread_control")
      and F.appels[-1][3] == {"messaging_product": "whatsapp", "action": "take", "to": "33612345678"}, F.appels[-1])
run(KA.rendre_fil("PN-1", {"recipient": "FR.L2"}))
check("K3.2 rendre : BSUID dans `recipient`", F.appels[-1][3] == {
    "messaging_product": "whatsapp", "action": "release", "recipient": "FR.L2"}, F.appels[-1][3])
F.refus = [(502, {"error": {"message": "panne", "code": 1}})]
F.appels.clear()
try:
    run(KA.prendre_fil("PN-1", {"to": "1"}))
    err = None
except KA.KapsoErreur as e:
    err = e
check("K3.3 502 : une seule tentative, erreur levée", err is not None and err.statut == 502 and len(F.appels) == 1,
      (err, len(F.appels)))
F.refus = [(409, {"error": {"message": "en cours", "code": "thread_control_in_progress"}})]
F.appels.clear()
try:
    run(KA.rendre_fil("PN-1", {"to": "1"}))
    err = None
except KA.KapsoErreur as e:
    err = e
check("K3.4 409 thread_control_in_progress : jamais réessayé", err is not None and err.statut == 409
      and err.code == "thread_control_in_progress" and len(F.appels) == 1, (err, len(F.appels)))

print("\n[K4] televerser_media")
F.appels.clear()
mid = run(KA.televerser_media("PN-1", b"\xff\xd8\xffJPG", "image/jpeg", "a.jpg"))
f = F.televerse[-1] if F.televerse else {}
check("K4.1 id rendu, POST /PN-1/media sans corps JSON", mid == "MEDIA-UP-1" and F.appels[-1][:2] == ("POST", "/PN-1/media")
      and F.appels[-1][3] is None, (mid, F.appels[-1][:2]))
check("K4.2 multipart : messaging_product, type, file", f.get("messaging_product") == (None, "whatsapp")
      and f.get("type") == (None, "image/jpeg") and f.get("file") == ("a.jpg", b"\xff\xd8\xffJPG", "image/jpeg"), f)
F.appels.clear()
for lbl, args in (("MIME gif", (b"x", "image/gif", "a.gif")), ("MIME pdf", (b"x", "application/pdf", "a.pdf")),
                  ("5 Mo + 1", (b"x" * (5 * 1024 * 1024 + 1), "image/png", "a.png")), ("vide", (b"", "image/png", "a.png"))):
    try:
        run(KA.televerser_media("PN-1", *args))
        r_ = None
    except ValueError as e:
        r_ = e
    check(f"K4.3 {lbl} refusé (ValueError)", r_ is not None, r_)
check("K4.4 aucun appel pour un refus", F.appels == [], F.appels)
run(KA.televerser_media("PN-1", b"x" * (5 * 1024 * 1024), "image/png", "a.png"))
check("K4.5 exactement 5 Mo accepté", True)
cle_vue = []


async def ancien_faux(methode, url, *, json=None, params=None):          # signature t310 : pas de `fichiers`
    cle_vue.append((methode, url))
    return 200, {"data": []}, {}


sauve = KA._requete
KA._requete = ancien_faux
run(KA.modeles("WABA-1"))
KA._requete = sauve
check("K4.6 un faux `_requete` sans `fichiers` marche pour un appel ordinaire", len(cle_vue) == 1, cle_vue)

print("\n[K5] preferences_marketing avec un BSUID")
F.appels.clear()
run(KA.preferences_marketing("FR.L2"))
check("K5.1 identifiant transmis tel quel", F.appels and F.appels[-1][1] == "/whatsapp/contacts/FR.L2/marketing_preferences",
      F.appels)

# ---------------------------------------------------------------------------------------------------------------------
print("\n[K6] WE.modeles : statut et composants")
MODELES = [
    {"name": "promo_img", "language": "fr", "status": "APPROVED", "category": "MARKETING", "components": [
        {"type": "HEADER", "format": "IMAGE"}, {"type": "BODY", "text": "Salut {{1}}"},
        {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": "Oui"}, {"type": "PHONE_NUMBER", "text": "Appel"},
                                        {"type": "URL", "text": "Voir", "url": "https://x.fr/{{1}}"},
                                        {"type": "URL", "text": "Site", "url": "https://x.fr/"}]}]},
    {"name": "rappel", "language": "fr", "status": "APPROVED", "category": "UTILITY", "components": [
        {"type": "HEADER", "format": "TEXT", "text": "Rappel {{1}}"}, {"type": "BODY", "text": "RDV"}]},
    {"name": "fixe", "language": "fr", "status": "APPROVED", "category": "UTILITY", "components": [
        {"type": "HEADER", "format": "TEXT", "text": "Titre fixe"}, {"type": "BODY", "text": "ok"}]},
    {"name": "simple", "language": "fr", "status": "APPROVED", "category": "UTILITY", "components": [
        {"type": "BODY", "text": "ok"}]},
    {"name": "attente", "language": "fr", "status": "PENDING", "category": "MARKETING", "components": [
        {"type": "BODY", "text": "bientôt"}]},
]
F.pages_modeles["WABA-1"] = [MODELES]
res = run(WE.modeles(cid))
check("K6.1 approuvés seulement par défaut", [m["nom"] for m in res] == ["promo_img", "rappel", "fixe", "simple"], res)
pi = res[0]
check("K6.2 statut rendu", pi.get("statut") == "approved", pi.get("statut"))
check("K6.3 entête image, boutons quick_reply index 0 et url index 2 (avec paramètre), url fixe sans paramètre",
      pi.get("composants") == {"entete": "image", "entete_variable": False, "boutons": [
          {"index": 0, "type": "quick_reply", "parametre": False}, {"index": 2, "type": "url", "parametre": True},
          {"index": 3, "type": "url", "parametre": False}]}, pi.get("composants"))
check("K6.4 entête texte ; sans composants : entête None, boutons vides", res[1]["composants"] == {"entete": "text", "boutons": [], "entete_variable": True}
      and res[2]["composants"] == {"entete": "text", "boutons": [], "entete_variable": False}
      and res[3]["composants"] == {"entete": None, "boutons": [], "entete_variable": False}, (res[1], res[2], res[3]))
res = run(WE.modeles(cid, tous=True))
check("K6.5 tous=True : le modèle en attente aussi, statut pending", [m["nom"] for m in res][-1] == "attente"
      and res[-1]["statut"] == "pending" and len(res) == 5, res)
check("K6.6 les champs t310 restent", set(res[0]) >= {"nom", "langue", "categorie", "parametres", "n_parametres"}, res[0])

# ---------------------------------------------------------------------------------------------------------------------
print("\n[K7] envoi modèle avec entête et boutons")
conv("PN-1", "+33 6 12 34 56 78")
F.pages_modeles["WABA-1"] = [MODELES]
base = {"type": "modele", "nom": "promo_img", "langue": "fr", "parametres": ["Léa"]}
WA.noter_accord(cid, TEL, "formulaire")
r = envoyer(TEL, {**base, "entete": {"type": "image", "media_id": "MEDIA-9"},
                  "boutons": [{"index": 0, "payload": "val:12:ok"}]})
check("K7.1 200", r.status_code == 200, r.text)
corps = (dernier_envoi() or {}).get("template", {})
check("K7.2 composants Meta exacts : header, body, button quick_reply", corps.get("components") == [
    {"type": "header", "parameters": [{"type": "image", "image": {"id": "MEDIA-9"}}]},
    {"type": "body", "parameters": [{"type": "text", "text": "Léa"}]},
    {"type": "button", "sub_type": "quick_reply", "index": "0", "parameters": [{"type": "payload", "payload": "val:12:ok"}]}],
      corps)
n0 = len(F.envois)
r = envoyer(TEL, {"type": "modele", "nom": "rappel", "langue": "fr", "parametres": [],
                  "entete": {"type": "text", "texte": "Lundi"}})
check("K7.3 entête texte accepté", r.status_code == 200
      and (dernier_envoi() or {}).get("template", {}).get("components") == [
          {"type": "header", "parameters": [{"type": "text", "text": "Lundi"}]}], (r.text, dernier_envoi()))


def refus400(label, envoi):
    n = len(F.envois)
    r_ = envoyer(TEL, envoi)
    check(f"K7 {label} : 400, aucun envoi", r_.status_code == 400 and len(F.envois) == n, (r_.status_code, r_.text))


ent9 = {"entete": {"type": "image", "media_id": "MEDIA-9"}}
refus400("payload > 128", {**base, **ent9, "boutons": [{"index": 0, "payload": "x" * 129}]})
refus400("payload vide", {**base, **ent9, "boutons": [{"index": 0, "payload": ""}]})
refus400("index inconnu du modèle", {**base, **ent9, "boutons": [{"index": 1, "payload": "p"}]})
refus400("index en double", {**base, **ent9, "boutons": [{"index": 0, "payload": "p"}, {"index": 0, "payload": "q"}]})
refus400("entête média sans media_id", {**base, "entete": {"type": "image"}})
refus400("entête sur un modèle sans entête", {"type": "modele", "nom": "simple", "langue": "fr", "parametres": [],
                                               "entete": {"type": "image", "media_id": "M"}})
refus400("entête d'un autre type que le modèle", {**base, "entete": {"type": "video", "media_id": "M"}})
refus400("entête média manquant (modèle à en-tête image)", {**base})
refus400("entête texte pour un en-tête texte SANS variable", {"type": "modele", "nom": "fixe", "langue": "fr",
                                                             "parametres": [], "entete": {"type": "text", "texte": "x"}})
r = envoyer(TEL, {"type": "modele", "nom": "fixe", "langue": "fr", "parametres": []})
check("K7.4 en-tête texte sans variable : envoi sans `entete` accepté", r.status_code == 200, r.text)
refus400("entête texte vide", {"type": "modele", "nom": "rappel", "langue": "fr", "parametres": [],
                               "entete": {"type": "text", "texte": ""}})

# ---------------------------------------------------------------------------------------------------------------------
print("\n[K8] envoi image")
r = envoyer(TEL, {"type": "image", "media_id": "MEDIA-5", "legende": "Voici"})
check("K8.1 200, corps Meta exact", r.status_code == 200 and (dernier_envoi() or {}) == {
    "messaging_product": "whatsapp", "to": "33612345678", "type": "image", "image": {"id": "MEDIA-5", "caption": "Voici"}},
      (r.text, dernier_envoi()))
r = envoyer(TEL, {"type": "image", "media_id": "MEDIA-5"})
check("K8.2 sans légende : pas de `caption`", r.status_code == 200 and dernier_envoi()["image"] == {"id": "MEDIA-5"},
      (r.text, dernier_envoi()))
refus400("légende > 1024", {"type": "image", "media_id": "M", "legende": "x" * 1025})
refus400("media_id invalide", {"type": "image", "media_id": "../x"})
refus400("media_id absent", {"type": "image"})
F.convs["PN-1"].clear()
conv("PN-1", "+33 6 12 34 56 78", il_y_a=timedelta(hours=30))
n = len(F.envois)
r = envoyer(TEL, {"type": "image", "media_id": "MEDIA-5"})
d = r.json().get("detail", {}) if r.status_code == 409 else {}
check("K8.3 hors fenêtre : 409 `fenetre`, aucun envoi", r.status_code == 409 and d.get("code") == "fenetre"
      and len(F.envois) == n, (r.status_code, r.text))
F.convs["PN-1"].clear()
conv("PN-1", "+33 6 12 34 56 78")

print("\n[K9] envoi boutons : entête image et ids fournis")
r = envoyer(TEL, {"type": "boutons", "texte": "Valider ?", "boutons": ["Valider", "Corriger"],
                  "ids": ["val:12:ok", "val:12:corr"], "entete_media_id": "MEDIA-7"})
check("K9.1 200, interactive avec header image et ids fournis", r.status_code == 200 and (dernier_envoi() or {}).get(
    "interactive") == {"type": "button", "header": {"type": "image", "image": {"id": "MEDIA-7"}},
                       "body": {"text": "Valider ?"},
                       "action": {"buttons": [{"type": "reply", "reply": {"id": "val:12:ok", "title": "Valider"}},
                                              {"type": "reply", "reply": {"id": "val:12:corr", "title": "Corriger"}}]}},
      (r.text, dernier_envoi()))
r = envoyer(TEL, {"type": "boutons", "texte": "Ok ?", "boutons": ["Oui", "Non"]})
check("K9.2 sans ids ni entête : ids b1, b2, pas de header (t310)", r.status_code == 200 and dernier_envoi()["interactive"] == {
    "type": "button", "body": {"text": "Ok ?"}, "action": {"buttons": [
        {"type": "reply", "reply": {"id": "b1", "title": "Oui"}}, {"type": "reply", "reply": {"id": "b2", "title": "Non"}}]}},
      (r.text, dernier_envoi()))
refus400("ids de longueur différente", {"type": "boutons", "texte": "t", "boutons": ["A", "B"], "ids": ["a"]})
refus400("id hors forme", {"type": "boutons", "texte": "t", "boutons": ["A"], "ids": ["a b"]})
refus400("id > 256", {"type": "boutons", "texte": "t", "boutons": ["A"], "ids": ["a" * 257]})
refus400("ids en double", {"type": "boutons", "texte": "t", "boutons": ["A", "B"], "ids": ["a", "a"]})
refus400("entete_media_id invalide", {"type": "boutons", "texte": "t", "boutons": ["A"], "entete_media_id": "../x"})

# ---------------------------------------------------------------------------------------------------------------------
print("\n[K10] médias rangés")
OCT = b"\x89PNG-OCTETS-RANGES-\x00\x01"
F.media["MED-A"] = (OCT, "image/png")
F.media["MED-GROS"] = (b"g" * (16 * 1024 * 1024 + 1), "image/jpeg")
F.media["MED-BIN"] = (b"zz", "application/x-truc")
F.media["MED-MAJ"] = (b"maj", "Image/PNG; charset=binary")
T_IN = int(maintenant().timestamp()) - 60


def entrant(i, mid, mime, type_="image"):
    return {"id": f"wamid.IN{i}", "timestamp": str(T_IN + i), "type": type_, "from": "33612345678",
            type_: {"id": mid, "mime_type": mime}, "kapso": {"direction": "inbound", "status": "received"}}


F.msgs["PN-1"] = [[entrant(1, "MED-A", "image/png"), entrant(2, "MED-GROS", "image/jpeg"),
                   entrant(3, "MED-ABSENT", "image/jpeg"), entrant(4, "MED-BIN", "application/x-truc", "document")]]
F.appels.clear()
res = run(WE.lire(cid))
rac = _tmp / "espaces" / boite / "whatsapp_medias" / "PN-1"
check("K10.1 le média neuf est rangé sous espaces/<id>/whatsapp_medias/<pid>/<id>.png", (rac / "MED-A.png").read_bytes() == OCT
      if (rac / "MED-A.png").exists() else False, sorted(str(p) for p in _tmp.rglob("whatsapp_medias/**/*")))
check("K10.2 > 16 Mo : rien rangé ; téléchargement en échec : rien rangé ; les messages restent tous rendus",
      not [x for x in rac.glob("MED-GROS*") if x.suffix != ".refus"] and not [x for x in rac.glob("MED-ABSENT*") if x.suffix != ".refus"] and len(res["messages"]) == 4,
      (sorted(p.name for p in rac.glob("*")), len(res["messages"])))
check("K10.3 MIME inconnu : extension .bin", (rac / "MED-BIN.bin").exists(), sorted(p.name for p in rac.glob("*")))
F.appels.clear()
run(WE.lire(cid))
check("K10.4 un média déjà rangé n'est pas retéléchargé", not any(a[1] == "/MED-A" for a in F.appels), F.appels)
for mauvais in ("../x", "a/b", "..\\x", ""):
    try:
        run(WE.ranger_media(cid, boite, mauvais))
        r_ = None
    except ValueError as e:
        r_ = e
    check(f"K10.5 ranger_media({mauvais!r}) refusé par _MEDIA_ID", r_ is not None, r_)
p = run(WE.ranger_media(cid, boite, "MED-A"))
check("K10.6 ranger_media rend le chemin du fichier existant", p is not None and pathlib.Path(p) == rac / "MED-A.png", p)
check("K10.7 ranger_media > 16 Mo rend None", run(WE.ranger_media(cid, boite, "MED-GROS")) is None, "")
tout = {x.name for x in rac.glob("*")}
run(WE.ranger_media(cid, boite, "MED-MAJ"))
check("K10.7b MIME normalisé (casse, paramètres) : extension .png", (rac / "MED-MAJ.png").exists(), sorted(x.name for x in rac.glob("*")))
tout = {x.name for x in rac.glob("*")}
check("K10.8 rien hors du dossier de l'espace (confinement)", all(x.resolve().is_relative_to((_tmp / "espaces" / boite).resolve())
                                                              for x in rac.glob("*")) and ".." not in "".join(tout), tout)

print("\n[K10b] média non rangé : marqueur .refus")
F.appels.clear()
run(WE.lire(cid))
run(WE.lire(cid))
check("K10.13 > 16 Mo : marqueur trop_gros, jamais redemandé à Kapso (deux lectures de plus)",
      (rac / "MED-GROS.refus").read_text(encoding="utf-8").splitlines()[1:] == ["trop_gros"]
      and not any(a[1] == "/MED-GROS" for a in F.appels), [a for a in F.appels if "GROS" in a[1]])
ref = (rac / "MED-ABSENT.refus").read_text(encoding="utf-8").splitlines() if (rac / "MED-ABSENT.refus").exists() else []
check("K10.14 erreur Kapso : marqueur horodaté + raison courte (sans texte)", len(ref) == 2 and ref[1].startswith("erreur:")
      and "chemin inconnu" not in "".join(ref) and WE._date_iso(ref[0]) is not None, ref)
check("K10.15 … pas redemandée avant 6 h", not any(a[1] == "/MED-ABSENT" for a in F.appels), F.appels)
vraie = WE._horloge
WE._horloge = lambda: vraie() + timedelta(hours=5, minutes=59)
F.appels.clear()
run(WE.lire(cid))
check("K10.16 5 h 59 plus tard : toujours pas", not any(a[1] == "/MED-ABSENT" for a in F.appels), F.appels)
WE._horloge = lambda: vraie() + timedelta(hours=6, minutes=1)
F.appels.clear()
run(WE.lire(cid))
check("K10.17 6 h 01 plus tard : redemandé (une fois)", sum(1 for a in F.appels if a[1] == "/MED-ABSENT") == 1, F.appels)
check("K10.18 … le > 16 Mo, jamais", not any(a[1] == "/MED-GROS" for a in F.appels), F.appels)
F.media["MED-ABSENT"] = (b"ok", "image/jpeg")
WE._horloge = lambda: vraie() + timedelta(hours=13)
run(WE.lire(cid))
check("K10.19 réussi : rangé et marqueur retiré", (rac / "MED-ABSENT.jpg").exists() and not (rac / "MED-ABSENT.refus").exists(),
      sorted(x.name for x in rac.glob("*")))
WE._horloge = vraie
F.appels.clear()
r = c.get(f"/api/whatsapp/{cid}/medias/MED-A")
check("K10.9 la route sert le fichier local, type image/png, sans appel Kapso", r.status_code == 200 and r.content == OCT
      and r.headers.get("content-type", "").startswith("image/png") and F.appels == [], (r.status_code, F.appels))
r = c.get(f"/api/whatsapp/{cid}/medias/MED-BIN")
check("K10.10 .bin : servi en pièce jointe octet-stream", r.status_code == 200
      and r.headers.get("content-type", "").startswith("application/octet-stream")
      and r.headers.get("content-disposition") == "attachment", (r.status_code, dict(r.headers)))
F.media["MED-C"] = (b"c", "image/png")
r = c.get(f"/api/whatsapp/{cid}/medias/MED-C")
check("K10.11 média non rangé : toujours servi depuis Kapso, rien d'écrit", r.status_code == 200 and not (rac / "MED-C.png").exists(),
      r.status_code)
check("K10.12 aucun journal ne porte le jeton ni la clé", not any("JETON" in x or CLE in x for x in JOURNAL), "")

# ---------------------------------------------------------------------------------------------------------------------
print("\n[K11] routes relire, fil, modeles ; marquer_lu")
g = c.get(f"/api/whatsapp/{cid}/messages")
p_ = c.post(f"/api/whatsapp/{cid}/relire", json={})
check("K11.1 POST relire = GET messages", p_.status_code == 200 and p_.json() == g.json(), (p_.status_code, p_.text[:200]))
p_ = c.post(f"/api/whatsapp/{cid}/relire", json={"depuis": "pas une date"})
check("K11.2 relire : date invalide -> 400", p_.status_code == 400, p_.status_code)
F.appels.clear()
p_ = c.post(f"/api/whatsapp/{cid}/relire", json={"depuis": iso(maintenant() - timedelta(days=1)), "apres": "1"})
check("K11.3 relire transmet depuis et apres", p_.status_code == 200 and F.appels[0][2].get("after") == "1"
      and "since" in F.appels[0][2], F.appels[:1])
F.appels.clear()
r = c.post(f"/api/whatsapp/{cid}/fil", json={"identite": TEL, "action": "prendre"})
check("K11.4 fil prendre : thread_control take, to", r.status_code == 200 and F.appels[-1][:2] == ("POST", "/PN-1/thread_control")
      and F.appels[-1][3] == {"messaging_product": "whatsapp", "action": "take", "to": "33612345678"}, (r.text, F.appels))
r = c.post(f"/api/whatsapp/{cid}/fil", json={"identite": "bsuid:FR.L2", "action": "rendre"})
check("K11.5 fil rendre BSUID : recipient", r.status_code == 200 and F.appels[-1][3] == {
    "messaging_product": "whatsapp", "action": "release", "recipient": "FR.L2"}, (r.text, F.appels[-1]))
n = len(F.appels)
check("K11.6 action inconnue -> 400 sans appel", c.post(f"/api/whatsapp/{cid}/fil", json={
    "identite": TEL, "action": "voler"}).status_code == 400 and len(F.appels) == n, "")
check("K11.7 identité invalide -> 400", c.post(f"/api/whatsapp/{cid}/fil", json={
    "identite": "x", "action": "prendre"}).status_code == 400, "")
F.refus = [(502, {"error": {"message": "panne", "code": 7}})]
r = c.post(f"/api/whatsapp/{cid}/fil", json={"identite": TEL, "action": "prendre"})
check("K11.8 refus Kapso -> 502 {message, code}", r.status_code == 502 and r.json()["detail"]["code"] == "7", r.text)
r = c.get(f"/api/whatsapp/{cid}/modeles")
check("K11.9 GET modeles : approuvés", r.status_code == 200 and len(r.json()) == 4, r.text[:200])
r = c.get(f"/api/whatsapp/{cid}/modeles?tous=1")
check("K11.10 GET modeles?tous=1 : tous, avec statut et composants", r.status_code == 200 and len(r.json()) == 5
      and "composants" in r.json()[0] and r.json()[-1]["statut"] == "pending", r.text[:200])
F.appels.clear()
run(WE.marquer_lu(cid, "wamid.Z"))
run(WE.marquer_lu(cid, "wamid.Z", ecrit=True))
check("K11.11 WE.marquer_lu : sans puis avec typing_indicator, vers le numéro du compte",
      [a[3].get("typing_indicator") for a in F.appels if a[1] == "/PN-1/messages"] == [None, {"type": "text"}], F.appels)

c.__exit__(None, None, None)
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
