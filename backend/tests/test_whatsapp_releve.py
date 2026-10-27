# -*- coding: utf-8 -*-
"""t311 tâche 5 (27/10/2026) — le relevé de fond WhatsApp (`whatsapp_releve`) et le mode auto.
Ce que ce banc garde :
  R0  constantes : INTERVALLE 120 s, DELAI_DEMARRAGE 30 s.
  R1  sans clé Kapso : aucun appel Kapso, aucun tour d'agent.
  R2  sautés : espace archivé, compte non relié, agent inactif (aucun appel Kapso pour leurs numéros).
  R3  premier tour d'un compte : l'historique de plus de 10 min est ignoré ; brouillon : rédigé, RIEN envoyé ;
      `marquer_lu` sur le dernier entrant avec `typing_indicator` ; second tour sans neuf : rien.
  R4  STOP -> rien ; état `humain` -> rien.
  R5  auto : envoyé par `WE.envoyer` (le faux Kapso voit le corps), brouillon `envoye`, `auto_jour` +1 ; plafond jour
      atteint -> brouillon ; montant absent de la fiche -> brouillon ; montant de la fiche -> envoyé ; carte modèle ->
      brouillon ; WhatsappRefus `occupee` pendant l'envoi -> brouillon gardé, rien envoyé, compteur intact.
  R6  hors horaires : auto -> un seul message par contact et par jour local (et pas d'appel du modèle) ; jour suivant ->
      de nouveau ; brouillon -> rangé, rien envoyé ; message vide -> rien.
  R7  exception d'un compte -> journalisée par son nom de type, le compte suivant est traité.
  R8  compte supprimé entre deux tours (et pendant un tour) -> sauté sans écrire ni journaliser d'avertissement.
  R9  crochet de validation (tâche 6) : appelé pour chaque entrant neuf AVANT le reste ; True -> message consommé.
  R12 agent inactif : son numéro n'est lu que si une validation client attend (`whatsapp_validation.en_attente`), et
      seul le crochet de validation passe (ni modèle, ni accusé, ni brouillon).
  R10 `releve_loop` : attend DELAI_DEMARRAGE avant le premier tour (aucun `espaces.lire()` avant), puis INTERVALLE ;
      un tour en échec n'arrête pas la boucle ; lifespan : tâche créée et passée à `_arreter_taches`.
  R11 journal : aucun texte de message ni clé.
Faux `kapso._requete` et faux `moteurs_texte.converser` : aucun réseau, aucune dépense.
Run (depuis backend/) : & $PY tests/test_whatsapp_releve.py"""
import asyncio, hashlib, json, os, pathlib, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwarl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "KAPSO_API_KEY", "ANTHROPIC_MODEL", "AGENT_MODEL"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
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
from zoneinfo import ZoneInfo                                        # noqa: E402
from app.config import settings, DATA_ROOT                           # noqa: E402
import app.main as MAIN                                              # noqa: E402
from app.services import comptes as CP, espaces as E, kapso as KA   # noqa: E402
from app.services import moteurs_texte as MT, pricing as PR          # noqa: E402
from app.services import whatsapp as WA, whatsapp_echanges as WE    # noqa: E402
from app.services.storage import init_db                             # noqa: E402
from app.services import agent_whatsapp as AW                        # noqa: E402
try:
    from app.services import whatsapp_releve as WR                   # noqa: E402
except ImportError as e:                                             # banc rouge : le module n'existe pas encore
    print(f"  FAIL  import whatsapp_releve ({e})")
    print(f"\n{ok} ok, 1 fail")
    sys.exit(1)

asyncio.run(init_db())
MODELE = "claude-banc"
GRILLE = {"33": {"marketing": 0.0859, "utility": 0.0300, "authentication": 0.0300, "service": 0.0100}}
PR._PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
PR._PRICING_FILE.write_text(json.dumps({"llm_claude_usd_per_mtok": {MODELE: {"in": 0.5, "out": 2.5}},
                                        "whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0}),
                            encoding="utf-8")
CLE_ANT = "sk-ant-FACTICE-releve"
settings.ANTHROPIC_API_KEY = CLE_ANT
settings.AGENT_MODEL = MODELE
KA_CLE = "CLE-KAPSO-SECRETE-RELEVE"


def poser_cle_kapso(v):
    os.environ["KAPSO_API_KEY"] = v
    setattr(settings, "KAPSO_API_KEY", v)


def maintenant():
    return datetime.now(timezone.utc)


def ts(d):
    return str(int(d.timestamp()))


PARIS = ZoneInfo("Europe/Paris")


def jour_local(d):
    return d.astimezone(PARIS).date().isoformat()


def horaires_ouverts():
    """Horaires qui couvrent l'instant présent (tous les jours, de -3 h à +3 h, nuit tolérée par `dans_horaires`)."""
    loc = datetime.now(PARIS)
    return {"jours": [0, 1, 2, 3, 4, 5, 6], "debut": (loc - timedelta(hours=3)).strftime("%H:%M"),
            "fin": (loc + timedelta(hours=3)).strftime("%H:%M"), "fuseau": "Europe/Paris"}


FERMES = {"jours": [], "debut": "09:00", "fin": "18:00", "fuseau": "Europe/Paris"}


# ---- le faux Kapso ----------------------------------------------------------------------------------------------------
class Faux:
    def __init__(self):
        self.appels, self.envois, self.lus, self.msgs = [], [], [], {}
        self.pannes, self.a_la_lecture = set(), {}


FK = Faux()


async def faux_requete(methode, url, *, json=None, params=None, fichiers=None):
    await asyncio.sleep(0)
    chemin = url.replace(KA.PROXY, "").replace(KA.PLATFORM, "").replace(f"https://{KA.HOTE}", "").split("?")[0]
    FK.appels.append((methode, chemin, dict(params or {})))
    parts = chemin.strip("/").split("/")
    if len(parts) == 2 and parts[0] in FK.pannes:
        return 500, {"error": {"message": "panne du faux"}}, {}
    if methode == "POST" and len(parts) == 2 and parts[1] == "messages":
        if (json or {}).get("status") == "read":
            FK.lus.append((parts[0], dict(json)))
            return 200, {"success": True}, {}
        FK.envois.append((parts[0], json))
        return 200, {"messaging_product": "whatsapp", "messages": [{"id": f"wamid.RL{len(FK.envois)}"}]}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "messages":
        geste = FK.a_la_lecture.pop(parts[0], None)
        if geste:
            geste()
        # le faux IGNORE `since` : le relevé doit filtrer lui-même l'historique
        return 200, {"data": [dict(x) for x in FK.msgs.get(parts[0], [])], "paging": {"cursors": {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "conversations":
        return 200, {"data": [], "paging": {"cursors": {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "message_templates":
        return 200, {"data": [], "paging": {}}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


async def faux_dormir(_s):
    return None


KA._requete = faux_requete
KA._dormir = faux_dormir


class Script:
    def __init__(self, reponses):
        self.reponses, self.appels = list(reponses), []

    def __call__(self, modele, systeme, messages, outils, max_tokens, timeout=120.0, sur_delta=None):
        self.appels.append(1)
        if not self.reponses:
            raise AssertionError("appel du modèle en trop")
        return self.reponses.pop(0)


def outil(nom, args, uid=None):
    return {"blocs": [{"type": "tool_use", "id": uid or f"toolu_{nom}", "name": nom, "input": args}],
            "arret": "tool_use", "in_tok": 1500, "out_tok": 200}


def poser(script):
    MT.converser = script
    return script


def run(coro):
    return asyncio.run(coro)


N = [0]


BASE = maintenant() + timedelta(minutes=5)


def entrant(texte, tel, il_y_a=None):
    """Un entrant. Sans `il_y_a` : daté d'une horloge de banc strictement croissante (BASE + 2 s par message), toujours
    postérieure aux brouillons déjà rangés (le garde « déjà traité » compare `cree_le`/`traite_jusqu_a` à `quand`)."""
    N[0] += 1
    quand = BASE + timedelta(seconds=2 * N[0]) if il_y_a is None else maintenant() - il_y_a
    return {"id": f"in{N[0]}", "type": "text", "text": {"body": texte}, "from": tel,
            "timestamp": ts(quand), "kapso": {"direction": "inbound"}}


def ajouter(pid, *msgs):
    """Range des messages chez le faux (plus récents d'abord, comme Kapso)."""
    tous = list(msgs) + FK.msgs.get(pid, [])
    FK.msgs[pid] = sorted(tous, key=lambda m: int(m["timestamp"]), reverse=True)
    return msgs[-1] if msgs else None


def appels_pid(pid, depuis=0):
    return [a for a in FK.appels[depuis:] if a[1].strip("/").split("/")[0] == pid]


def empreinte(dossier):
    h = hashlib.sha1()
    for p in sorted(pathlib.Path(dossier).rglob("*")):
        h.update(str(p.relative_to(dossier)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def espace(nom, agent=None, archive=False):
    eid = E.creer({"nom": nom})["id"]
    if agent is not None:
        WA.regler_espace(eid, {"agent": agent})
    if archive:
        doc = json.loads((E.dossier() / "espaces.json").read_text(encoding="utf-8"))
        doc["espaces"][eid]["archive"] = True
        E._ecrire_json(E.dossier() / "espaces.json", doc)
    return eid


def compte(eid, pid=None):
    cid = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
    if pid:
        CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": pid, "WHATSAPP_WABA_ID": "WABA-" + pid})
    return cid


def tick(marqueur, quand=None):
    return run(WR.releve_tick(marqueur, maintenant=quand))


# ---------------------------------------------------------------------------------------------------------------------
print("[R0] constantes")
check("R0.1 INTERVALLE 120 s, DELAI_DEMARRAGE 30 s", WR.INTERVALLE == 120 and WR.DELAI_DEMARRAGE == 30)

E.lire()
ACTIF = {"actif": True, "mode": "brouillon", "roles": ["faq"], "horaires": horaires_ouverts()}
A = espace("Salon Alpha", ACTIF)
pa = E.persona(A)
pa["display_name"] = "Salon Alpha"
pa["tarifs"] = "Coupe femme : 25 € (prix public)"
pa["horaires"] = "samedi de 9 h à 12 h"            # relecture finale : un nombre absent de la fiche garde le brouillon
E.ecrire_persona(A, pa)
cA = compte(A, "PN-A")
B = espace("Salon Archivé", ACTIF, archive=True)
cB = compte(B, "PN-B")
C = espace("Salon Non Relié", ACTIF)
cC = compte(C)
D = espace("Salon Inactif", {**ACTIF, "actif": False})
cD = compte(D, "PN-D")
for pid in ("PN-B", "PN-D"):
    ajouter(pid, entrant("bonjour, vous ouvrez demain ?", "33611110000"))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R1] sans clé Kapso")
poser_cle_kapso("")
ajouter("PN-A", entrant("bonjour, vous ouvrez demain ?", "33600000001"))
s = poser(Script([]))
M = {}
r = tick(M)
check("R1.1 sans clé : aucun appel Kapso, aucun appel du modèle, marqueur vide", FK.appels == [] and s.appels == []
      and M == {}, (FK.appels, M))
check("R1.2 rend un dict", isinstance(r, dict), r)
poser_cle_kapso(KA_CLE)
FK.msgs["PN-A"] = []

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R2/R3] premier tour, brouillon, sautés")
TEL_OLD, TEL1 = "33600000009", "33600000001"
vieux = entrant("Message d'hier soir", TEL_OLD, il_y_a=timedelta(minutes=30))
neuf = entrant("Quels sont vos horaires ?", TEL1)
ajouter("PN-A", vieux, neuf)
n0 = len(FK.appels)
s = poser(Script([outil("rediger_reponse", {"texte": "Nous ouvrons de 9 h à 18 h."})]))
r = tick(M)
check("R2.1 espace archivé, compte non relié, agent inactif : aucun appel Kapso pour leurs numéros",
      appels_pid("PN-B", n0) == [] and appels_pid("PN-D", n0) == [], FK.appels[n0:])
check("R3.1 un seul appel du modèle (le message de 30 min est de l'historique)", len(s.appels) == 1, s.appels)
bA = AW.brouillons(A, "PN-A")
check("R3.2 brouillon rédigé pour le contact neuf, aucun pour l'historique",
      (bA.get("tel:" + TEL1) or {}).get("etat") == "attente" and "tel:" + TEL_OLD not in bA, bA)
check("R3.3 mode brouillon : rien envoyé", FK.envois == [], FK.envois)
check("R3.4 marquer_lu sur le dernier entrant avec typing_indicator",
      [(p, j.get("message_id"), j.get("typing_indicator")) for p, j in FK.lus] == [("PN-A", neuf["id"], {"type": "text"})],
      FK.lus)
check("R3.5 marqueur du compte = ISO du dernier entrant vu",
      cA in M and datetime.fromisoformat(M[cA]) == datetime.fromtimestamp(int(neuf["timestamp"]), timezone.utc), M)
lus0 = len(FK.lus)
s = poser(Script([]))
r = tick(M)
check("R3.6 second tour sans neuf : aucun appel du modèle, aucun accusé", s.appels == [] and len(FK.lus) == lus0)
# un compte vu pour la première fois avec SEULEMENT de l'historique
A2 = espace("Salon Bis", ACTIF)
cA2 = compte(A2, "PN-A2")
ajouter("PN-A2", entrant("Bonjour", "33600000077", il_y_a=timedelta(hours=3)))
s = poser(Script([]))
tick(M)
check("R3.7 premier tour avec seulement un vieil historique : rien (aucun modèle, aucun accusé, aucun brouillon)",
      s.appels == [] and len(FK.lus) == lus0 and AW.brouillons(A2, "PN-A2") == {}, AW.brouillons(A2, "PN-A2"))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R4] STOP et humain")
TEL_STOP, TEL_H = "33600000002", "33600000003"
stop = entrant("STOP", TEL_STOP)
ajouter("PN-A", stop)
s = poser(Script([]))
lus0 = len(FK.lus)
tick(M)
check("R4.1 STOP : aucun appel du modèle, aucun accusé, aucun brouillon", s.appels == [] and len(FK.lus) == lus0
      and "tel:" + TEL_STOP not in AW.brouillons(A, "PN-A"))
AW.ranger(A, "PN-A", "tel:" + TEL_H, "humain", None, "mot_cle")
ajouter("PN-A", entrant("Et alors, vous me répondez ?", TEL_H))
s = poser(Script([]))
tick(M)
check("R4.2 état humain : aucun appel du modèle, aucun accusé, brouillon intact", s.appels == [] and len(FK.lus) == lus0
      and AW.brouillons(A, "PN-A")["tel:" + TEL_H]["etat"] == "humain")

print("\n[R4b] décision humaine postérieure à un entrant neuf")
TEL_DH = "33600000017"
ajouter("PN-A", entrant("Bonjour, vous coupez les enfants ?", TEL_DH))
s = poser(Script([outil("rediger_reponse", {"texte": "Oui, dès 3 ans."})]))
tick(M)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_DH) or {}
check("R4b.1 premier entrant : brouillon en attente, trace posée", b.get("etat") == "attente" and b.get("traite_jusqu_a"), b)
m2 = entrant("Et le samedi ?", TEL_DH)                              # entrant neuf à T+10 (pendant que le brouillon attend)
ajouter("PN-A", m2)
q2 = datetime.fromtimestamp(int(m2["timestamp"]), timezone.utc)


def decision_humaine(b_):                                            # décision humaine à T+20, avant le tour suivant
    b_["etat"] = "rejete"
    b_["decide_le"] = (q2 + timedelta(seconds=10)).isoformat()
    return b_


AW._modifier(A, "PN-A", "tel:" + TEL_DH, decision_humaine)
s = poser(Script([outil("rediger_reponse", {"texte": "Oui, le samedi aussi."})]))
tick(M)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_DH) or {}
check("R4b.2 tour suivant : l'entrant neuf est traité malgré decide_le >= quand (rediger appelé, brouillon neuf)",
      len(s.appels) == 1 and b.get("etat") == "attente" and b["carte"]["arguments"]["texte"] == "Oui, le samedi aussi."
      and datetime.fromisoformat(b["traite_jusqu_a"]) == q2, (s.appels, b))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R5] mode auto")
WA.regler_espace(A, {"agent": {"mode": "auto", "plafond_jour_contact": 1}})
TEL_AUTO = "33600000004"
ajouter("PN-A", entrant("Vous êtes ouverts samedi ?", TEL_AUTO))
s = poser(Script([outil("rediger_reponse", {"texte": "Oui, samedi de 9 h à 12 h."})]))
e0 = len(FK.envois)
quand = maintenant()
r = tick(M, quand)
envois = FK.envois[e0:]
check("R5.1 auto : envoyé par WE.envoyer, le faux Kapso voit le corps texte",
      len(envois) == 1 and envois[0][0] == "PN-A" and envois[0][1].get("type") == "text"
      and envois[0][1]["text"]["body"] == "Oui, samedi de 9 h à 12 h." and envois[0][1].get("to") == TEL_AUTO, envois)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_AUTO) or {}
check("R5.2 brouillon envoye, auto_jour du jour local = 1", b.get("etat") == "envoye"
      and (b.get("auto_jour") or {}).get(jour_local(quand)) == 1, b)
check("R5.2b traite_jusqu_a = quand du dernier entrant traité", b.get("traite_jusqu_a") is not None
      and datetime.fromisoformat(b["traite_jusqu_a"]) >= datetime.fromtimestamp(int(FK.msgs["PN-A"][0]["timestamp"]),
                                                                                timezone.utc), b)
# (a) marqueur perdu (redémarrage) : le même entrant n'obtient jamais une seconde réponse
M.clear()
s = poser(Script([]))
e0 = len(FK.envois)
tick(M, quand)
check("R5.2c marqueur vidé puis nouveau tour : zéro envoi, zéro appel du modèle", FK.envois[e0:] == [] and s.appels == [],
      (FK.envois[e0:], s.appels))
ajouter("PN-A", entrant("Et dimanche ?", TEL_AUTO))
s = poser(Script([outil("rediger_reponse", {"texte": "Fermé le dimanche."})]))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_AUTO) or {}
check("R5.3 plafond jour atteint (1) : brouillon attente, rien envoyé, compteur inchangé",
      FK.envois[e0:] == [] and b.get("etat") == "attente" and b["auto_jour"].get(jour_local(quand)) == 1, b)

WA.regler_espace(A, {"agent": {"plafond_jour_contact": 5}})
TEL_PRIX = "33600000005"
ajouter("PN-A", entrant("Combien coûte une coloration ?", TEL_PRIX))
s = poser(Script([outil("rediger_reponse", {"texte": "La coloration est à 1 € aujourd'hui."})]))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_PRIX) or {}
check("R5.4 montant absent de la fiche : brouillon attente, rien envoyé", FK.envois[e0:] == [] and b.get("etat") == "attente"
      and not b.get("auto_jour"), b)
TEL_PRIX2 = "33600000006"
ajouter("PN-A", entrant("Et une coupe femme ?", TEL_PRIX2))
s = poser(Script([outil("rediger_reponse", {"texte": "Le prix d'une coupe femme est de 25 €."})]))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_PRIX2) or {}
check("R5.5 montant présent dans la fiche : envoyé", len(FK.envois[e0:]) == 1 and b.get("etat") == "envoye", b)
TEL_30 = "33600000013"
ajouter("PN-A", entrant("C'est combien la mèche ?", TEL_30))
s = poser(Script([outil("rediger_reponse", {"texte": "Le prix est de 30"})]))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_30) or {}
check("R5.5b « Le prix est de 30 » (30 absent de la fiche, sans devise) : brouillon, rien envoyé",
      FK.envois[e0:] == [] and b.get("etat") == "attente", b)
check("R5.5c montants voisins d'un mot d'argent : 30 relevé, 25 € de la fiche aussi",
      WR._montants("le prix est de 30") == {"30"} and "25" in WR._montants("coupe femme : 25 € (prix public)"))

# (b) sans clé Anthropic : `rediger` ne range rien, mais le même entrant n'est pas redonné à `rediger`
APPELS_R = []
_rediger_orig = AW.rediger


async def rediger_compte(cid, eid, identite, langue="fr"):
    APPELS_R.append(identite)
    return await _rediger_orig(cid, eid, identite, langue=langue)


TEL_SC = "33600000014"
ajouter("PN-A", entrant("Vous avez des créneaux jeudi ?", TEL_SC))
settings.ANTHROPIC_API_KEY = ""
AW.rediger = rediger_compte
s = poser(Script([]))
try:
    tick(M, quand)
    tick(M, quand)
    M.clear()
    tick(M, quand)
finally:
    AW.rediger = _rediger_orig
    settings.ANTHROPIC_API_KEY = CLE_ANT
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_SC) or {}
check("R5.5d sans clé : rediger appelé UNE fois sur trois tours (marqueur gardé puis vidé), aucun brouillon à décider",
      APPELS_R.count("tel:" + TEL_SC) == 1 and s.appels == [] and "etat" not in b and b.get("traite_jusqu_a"),
      (APPELS_R, b))

# (c) envoyer_brouillon lève : le tour suivant ne refait rien (marqueur gardé, puis vidé)
TEL_ERR = "33600000015"
ajouter("PN-A", entrant("Vous prenez la carte ?", TEL_ERR))
_envoyer_orig = AW.envoyer_brouillon


async def envoyer_en_panne(*a, **k):
    raise RuntimeError("panne d'envoi")


AW.envoyer_brouillon = envoyer_en_panne
s = poser(Script([outil("rediger_reponse", {"texte": "Oui, la carte est acceptée."})]))
e0 = len(FK.envois)
try:
    tick(M, quand)
finally:
    AW.envoyer_brouillon = _envoyer_orig
s1 = len(s.appels)
s = poser(Script([]))
tick(M, quand)
M.clear()
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_ERR) or {}
check("R5.5e envoi en panne puis deux tours (marqueur gardé, puis vidé) : rien envoyé, aucun nouvel appel du modèle",
      s1 == 1 and FK.envois[e0:] == [] and s.appels == [] and b.get("etat") == "attente", (s1, s.appels, b))

TEL_MOD = "33600000007"
ajouter("PN-A", entrant("Bonjour, des nouvelles ?", TEL_MOD))
s = poser(Script([outil("choisir_modele", {"nom": "relance", "langue": "fr"})]))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_MOD) or {}
check("R5.6 carte autre que reponse_whatsapp : reste brouillon, rien envoyé", FK.envois[e0:] == []
      and b.get("etat") == "attente" and (b.get("carte") or {}).get("genre") == "modele_whatsapp"
      and not b.get("auto_jour"), (b, s.appels))

# WhatsappRefus « occupee » : une personne a réservé l'envoi entre la rédaction et l'envoi automatique
TEL_OCC = "33600000008"
ajouter("PN-A", entrant("Vous faites les barbes ?", TEL_OCC))
s = poser(Script([outil("rediger_reponse", {"texte": "Oui, sur rendez-vous."})]))
_rediger_vrai = AW.rediger


async def rediger_puis_reserver(cid, eid, identite, langue="fr"):
    r = await _rediger_vrai(cid, eid, identite, langue=langue)
    cle, groupe = AW.canonique(cid, identite)

    def geste(b):
        b["etat"] = "envoi_en_cours"
        b["envoi_depuis"] = datetime.now(timezone.utc).isoformat()
        return b
    AW._modifier(eid, "PN-A", cle, geste, groupe)
    return r


AW.rediger = rediger_puis_reserver
e0 = len(FK.envois)
try:
    tick(M, quand)
finally:
    AW.rediger = _rediger_vrai
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_OCC) or {}
check("R5.7 refus occupee pendant l'envoi auto : rien envoyé, brouillon gardé (carte intacte), compteur intact",
      FK.envois[e0:] == [] and b.get("etat") == "envoi_en_cours" and (b.get("carte") or {}).get("genre") == "reponse_whatsapp"
      and not b.get("auto_jour"), b)
check("R5.8 refus journalisé par son code ou son type, sans texte", any("occupee" in l or "WhatsappRefus" in l
                                                                    for l in JOURNAL[-20:]), JOURNAL[-5:])

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R6] hors horaires")
HORS = "Nous sommes fermés, nous vous répondons dès l'ouverture."
WA.regler_espace(A, {"agent": {"horaires": FERMES, "message_hors_horaires": HORS}})
TEL_NUIT = "33600000010"
ajouter("PN-A", entrant("Bonsoir, une question", TEL_NUIT))
s = poser(Script([]))
e0 = len(FK.envois)
tick(M, quand)
envois = FK.envois[e0:]
check("R6.1 auto hors horaires : message d'absence envoyé, aucun appel du modèle",
      len(envois) == 1 and envois[0][1]["text"]["body"] == HORS and s.appels == [], envois)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_NUIT) or {}
check("R6.2 brouillon envoye et compteur du jour", b.get("etat") == "envoye"
      and b["auto_jour"].get(jour_local(quand)) == 1, b)
ajouter("PN-A", entrant("Vous êtes là ?", TEL_NUIT))
e0 = len(FK.envois)
tick(M, quand)
check("R6.3 même jour local : pas de second message d'absence", FK.envois[e0:] == [] and s.appels == [], FK.envois[e0:])
ajouter("PN-A", entrant("Bonjour ?", TEL_NUIT))
demain = quand + timedelta(days=1)
e0 = len(FK.envois)
tick(M, demain)
check("R6.4 jour local suivant : de nouveau un message d'absence", len(FK.envois[e0:]) == 1, FK.envois[e0:])
TEL_ATT = "33600000016"
CARTE_ATT = {"type": "carte", "genre": "reponse_whatsapp", "etat": "proposee", "arguments": {"texte": "Brouillon à garder"}}
AW.ranger(A, "PN-A", "tel:" + TEL_ATT, "attente", CARTE_ATT)
ajouter("PN-A", entrant("Bonsoir, vous avez vu ?", TEL_ATT))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_ATT) or {}
check("R6.4b auto hors horaires avec un brouillon en attente : rien envoyé, brouillon intact",
      FK.envois[e0:] == [] and b.get("etat") == "attente" and b["carte"]["arguments"]["texte"] == "Brouillon à garder", b)
WA.regler_espace(A, {"agent": {"mode": "brouillon"}})
TEL_NUIT2 = "33600000011"
ajouter("PN-A", entrant("Bonsoir", TEL_NUIT2))
e0 = len(FK.envois)
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_NUIT2) or {}
check("R6.5 brouillon hors horaires : texte d'absence rangé en brouillon, rien envoyé",
      FK.envois[e0:] == [] and b.get("etat") == "attente" and (b.get("carte") or {}).get("genre") == "reponse_whatsapp"
      and b["carte"]["arguments"]["texte"] == HORS, b)
WA.regler_espace(A, {"agent": {"message_hors_horaires": ""}})
TEL_NUIT3 = "33600000012"
ajouter("PN-A", entrant("Bonsoir", TEL_NUIT3))
tick(M, quand)
b = AW.brouillons(A, "PN-A").get("tel:" + TEL_NUIT3) or {}
check("R6.6 message d'absence vide : aucun brouillon (seule la trace traite_jusqu_a), aucun appel du modèle",
      "etat" not in b and b.get("carte") is None and b.get("traite_jusqu_a") and s.appels == [], b)
WA.regler_espace(A, {"agent": {"horaires": horaires_ouverts()}})

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R7] exception d'un compte")
X = espace("Salon Panne", ACTIF)
cX = compte(X, "PN-X")
Y = espace("Salon Suivant", ACTIF)
cY = compte(Y, "PN-Y")
FK.pannes.add("PN-X")
ajouter("PN-X", entrant("bonjour", "33600000020"))
ajouter("PN-Y", entrant("Vous ouvrez à quelle heure ?", "33600000021"))
s = poser(Script([outil("rediger_reponse", {"texte": "À 9 h."})]))
j0 = len(JOURNAL)
r = tick(M, quand)
check("R7.1 le compte suivant est traité malgré la panne du premier",
      (AW.brouillons(Y, "PN-Y").get("tel:33600000021") or {}).get("etat") == "attente")
check("R7.2 panne journalisée par son nom de type", any("KapsoErreur" in l and cX in l for l in JOURNAL[j0:]), JOURNAL[j0:])
FK.pannes.discard("PN-X")

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R8] compte supprimé")
Z = espace("Salon Supprimé", ACTIF)
cZ = compte(Z, "PN-Z")
tick(M, quand)                                   # premier tour : marqueur posé
CP.supprimer(cZ)
ajouter("PN-Z", entrant("Vous êtes là ?", "33600000030"))
avant = empreinte(DATA_ROOT / "espaces" / Z)
n0, j0 = len(FK.appels), len(JOURNAL)
s = poser(Script([]))
tick(M, quand)
check("R8.1 supprimé entre deux tours : aucun appel Kapso pour son numéro, rien écrit, aucun appel du modèle",
      appels_pid("PN-Z", n0) == [] and empreinte(DATA_ROOT / "espaces" / Z) == avant and s.appels == [])
check("R8.2 marqueur du compte supprimé retiré", cZ not in M, list(M))
Z2 = espace("Salon Supprimé En Vol", ACTIF)
cZ2 = compte(Z2, "PN-Z2")
ajouter("PN-Z2", entrant("Bonjour, une question", "33600000031"))
FK.a_la_lecture["PN-Z2"] = lambda: CP.supprimer(cZ2)
avant = empreinte(DATA_ROOT / "espaces" / Z2)
j0 = len(JOURNAL)
tick(M, quand)
check("R8.3 supprimé PENDANT le tour : sauté sans écrire, sans avertissement, aucun appel du modèle",
      empreinte(DATA_ROOT / "espaces" / Z2) == avant and s.appels == []
      and not any("WARNING" in l and cZ2 in l for l in JOURNAL[j0:]), JOURNAL[j0:])

import shutil                                                        # noqa: E402
FANTOME = "fantome-releve"
try:
    AW.ranger(FANTOME, "PN-F", "tel:33600000099", "attente", None)
    leve = None
except KeyError:
    leve = "KeyError"
check("R8.4 brouillon d'un espace sans dossier : KeyError, `espaces/<eid>/` jamais recréé",
      E.id_valide(FANTOME) and leve == "KeyError" and not (E.dossier() / FANTOME).exists(), leve)
Z3 = espace("Salon Effacé", ACTIF)
cZ3 = compte(Z3, "PN-Z3")
ajouter("PN-Z3", entrant("Bonjour", "33600000032"))
shutil.rmtree(E.dossier() / Z3)
j0 = len(JOURNAL)
tick(M, quand)
check("R8.5 dossier de l'espace effacé : sauté, dossier jamais recréé, aucun avertissement",
      not (E.dossier() / Z3).exists() and not any("WARNING" in l and cZ3 in l for l in JOURNAL[j0:]), JOURNAL[j0:])

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R9] crochet de validation")
VU = []
faux_wv = types.ModuleType("app.services.whatsapp_validation")


async def traiter_reponse(cid, eid, msg):                            # contrat ASYNCHRONE (tâche 6)
    VU.append((cid, eid, msg.get("id"), len(FK.lus)))
    await asyncio.sleep(0)
    if msg.get("texte") == "Boum":
        raise KeyError("validation inconnue")
    return msg.get("texte") == "Valider"


faux_wv.traiter_reponse = traiter_reponse


async def _sans_attente(eid, maintenant=None):                       # tâche 6 : aucune validation client en attente
    return False


faux_wv.en_attente = _sans_attente
import app.services as _pkg                                          # noqa: E402
_mod_vrai = sys.modules.get("app.services.whatsapp_validation")      # tâche 6 : le vrai module, déjà importé
_avait = hasattr(_pkg, "whatsapp_validation")
_attr_vrai = getattr(_pkg, "whatsapp_validation", None)
sys.modules["app.services.whatsapp_validation"] = faux_wv
setattr(_pkg, "whatsapp_validation", faux_wv)
TEL_V = "33600000040"
mv = entrant("Valider", TEL_V)
ajouter("PN-A", mv)
s = poser(Script([]))
lus0 = len(FK.lus)
tick(M, quand)
check("R9.1 crochet appelé pour l'entrant neuf, avant tout accusé de lecture",
      [(c_, e_, i_) for c_, e_, i_, _l in VU] == [(cA, A, mv["id"])] and VU[0][3] == lus0, VU)
bV = AW.brouillons(A, "PN-A").get("tel:" + TEL_V) or {}
check("R9.2 réponse consommée : aucun tour d'agent, aucun accusé, aucun brouillon (seule la trace traite_jusqu_a)",
      s.appels == [] and len(FK.lus) == lus0 and "etat" not in bV and bV.get("carte") is None
      and datetime.fromisoformat(bV.get("traite_jusqu_a") or "1970-01-01T00:00:00+00:00")
      == datetime.fromtimestamp(int(mv["timestamp"]), timezone.utc), bV)
VU.clear()
mv2 = entrant("Merci, et vos horaires ?", TEL_V)
ajouter("PN-A", mv2)
s = poser(Script([outil("rediger_reponse", {"texte": "De 9 h à 18 h."})]))
tick(M, quand)
check("R9.3 réponse non consommée : tour d'agent normal", [i_ for _c, _e, i_, _l in VU] == [mv2["id"]]
      and len(s.appels) == 1 and (AW.brouillons(A, "PN-A").get("tel:" + TEL_V) or {}).get("etat") == "attente")
TEL_B = "33600000041"
mb = entrant("Boum", TEL_B)
ajouter("PN-A", mb)
s = poser(Script([outil("rediger_reponse", {"texte": "Bien reçu."})]))
j0 = len(JOURNAL)
tick(M, quand)
check("R9.4 crochet qui lève (même KeyError) : journalisé par nom de type, compte gardé (marqueur), message traité",
      any("KeyError" in l and cA in l for l in JOURNAL[j0:]) and cA in M
      and datetime.fromisoformat(M[cA]) == datetime.fromtimestamp(int(mb["timestamp"]), timezone.utc)
      and len(s.appels) == 1 and (AW.brouillons(A, "PN-A").get("tel:" + TEL_B) or {}).get("etat") == "attente",
      (JOURNAL[j0:], M.get(cA)))
if _mod_vrai is not None:
    sys.modules["app.services.whatsapp_validation"] = _mod_vrai
else:
    del sys.modules["app.services.whatsapp_validation"]
if _avait:
    setattr(_pkg, "whatsapp_validation", _attr_vrai)
else:
    delattr(_pkg, "whatsapp_validation")

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R12] agent inactif : le crochet de validation seul, quand une validation client attend")
from app.services import whatsapp_validation as WV                  # noqa: E402 — le vrai module
VU2 = []


async def espion_validation(cid, eid, msg):
    VU2.append((cid, eid, msg.get("id")))
    return msg.get("texte") == "Valider"


_tr_vrai = WV.traiter_reponse
WV.traiter_reponse = espion_validation
try:
    I = espace("Salon Validation", {**ACTIF, "actif": False})
    cI = compte(I, "PN-I")
    TEL_I = "33600000050"
    ajouter("PN-I", entrant("bonjour", TEL_I))
    n0, lus0 = len(FK.appels), len(FK.lus)
    s = poser(Script([]))
    tick(M, quand)
    check("R12.1 agent inactif sans validation en attente : aucun appel Kapso pour son numéro, crochet non appelé",
          appels_pid("PN-I", n0) == [] and VU2 == [] and cI not in M, FK.appels[n0:])
    from app.services import storage as ST                       # noqa: E402

    async def _poser_post(pid_, statut):
        async with ST.async_session_factory() as s_:
            s_.add(ST.ScheduledPost(id=pid_, title="Teaser", caption="", channels="x", status=statut, mode="assisted",
                                    run_at=datetime.utcnow() + timedelta(days=2), espace_id=I))
            await s_.commit()
    run(_poser_post("p-brouillon", "draft"))
    AW.modifier_validations(I, lambda v: {**v, "p-brouillon": {"identite": "tel:" + TEL_I, "cid": cI, "etat": "envoye",
                                                              "envoye_le": maintenant().isoformat(timespec="seconds")}})
    tick(M, quand)
    check("R12.1b validation « envoye » d'un post qui n'est plus a_valider : le compte n'est pas lu",
          appels_pid("PN-I", n0) == [] and VU2 == [], FK.appels[n0:])
    run(_poser_post("p-attente", "a_valider"))
    AW.modifier_validations(I, lambda v: {**v, "p-attente": {"identite": "tel:" + TEL_I, "cid": cI, "etat": "envoye",
                                                            "envoye_le": maintenant().isoformat(timespec="seconds")}})
    mI = entrant("Valider", TEL_I)
    ajouter("PN-I", mI)
    tick(M, quand)
    check("R12.2 validation en attente : messages lus, crochet appelé pour chaque entrant neuf",
          appels_pid("PN-I", n0) != [] and mI["id"] in [i_ for _c, _e, i_ in VU2] and all(c_ == cI and e_ == I for c_, e_, _i in VU2)
          and cI in M, (VU2, FK.appels[n0:]))
    check("R12.3 agent inactif : rien d'autre (aucun appel du modèle, aucun accusé, aucun brouillon — la réponse "
          "consommée est seulement notée traitée —, rien envoyé)",
          s.appels == [] and len(FK.lus) == lus0
          and all("etat" not in b_ and b_.get("carte") is None for b_ in AW.brouillons(I, "PN-I").values())
          and (AW.brouillons(I, "PN-I").get("tel:" + TEL_I) or {}).get("traite_jusqu_a")
          and not [e for e in FK.envois if e[0] == "PN-I"], (s.appels, AW.brouillons(I, "PN-I")))
    AW.modifier_validations(I, lambda v: {k: {**x, "etat": "valide"} for k, x in v.items()})
    VU2.clear()
    ajouter("PN-I", entrant("encore", TEL_I))
    tick(M, quand)
    check("R12.4 plus rien en attente : le compte n'est plus lu, son marqueur est retiré",
          VU2 == [] and cI not in M, (VU2, M.get(cI)))
finally:
    WV.traiter_reponse = _tr_vrai

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R13] relecture finale : second toucher, « Prendre le fil », garde-fou argent, borne de rédactions, incertain")
APPELS_R13 = []
_rediger_r13 = AW.rediger


async def rediger_espion(cid, eid, identite, langue="fr"):
    APPELS_R13.append(identite)
    return await _rediger_r13(cid, eid, identite, langue=langue)


AW.rediger = rediger_espion
try:
    # (1) second toucher sur « Valider » d'un post déjà validé : consommé, jamais donné à l'agent, noté traité
    TEL_2T = "33600000060"
    AW.modifier_validations(A, lambda v: {**v, "p-deja": {"identite": "tel:" + TEL_2T, "cid": cA, "etat": "valide",
                                                         "envoye_le": maintenant().isoformat(timespec="seconds")}})
    N[0] += 1
    q2t = BASE + timedelta(seconds=2 * N[0])
    m2t = {"id": f"in{N[0]}", "type": "interactive", "from": TEL_2T, "timestamp": ts(q2t), "kapso": {"direction": "inbound"},
           "interactive": {"type": "button_reply", "button_reply": {"id": "val:p-deja:ok", "title": "Valider"}}}
    ajouter("PN-A", m2t)
    WA.regler_espace(A, {"agent": {"mode": "auto"}})
    s = poser(Script([outil("rediger_reponse", {"texte": "Merci !"})]))
    e0 = len(FK.envois)
    tick(M, quand)
    b2t = AW.brouillons(A, "PN-A").get("tel:" + TEL_2T) or {}
    check("R13.1 second toucher sur « Valider » (déjà validé) : aucun rediger, aucun appel du modèle, rien envoyé",
          "tel:" + TEL_2T not in APPELS_R13 and s.appels == [] and FK.envois[e0:] == [], (APPELS_R13, FK.envois[e0:]))
    check("R13.2 la réponse consommée est notée traitée (un redémarrage ne la rejoue pas) ; aucun brouillon",
          "etat" not in b2t and datetime.fromisoformat(b2t.get("traite_jusqu_a") or "1970-01-01T00:00:00+00:00") == datetime.fromtimestamp(int(m2t["timestamp"]), timezone.utc), b2t)
    M.clear()
    tick(M, quand)
    check("R13.3 marqueur vidé (redémarrage) puis tour : toujours aucun rediger ni envoi",
          "tel:" + TEL_2T not in APPELS_R13 and FK.envois[e0:] == [], (APPELS_R13, FK.envois[e0:]))

    # (2) « Prendre le fil » : le relevé ne fait rien pour ce contact ; rediger demandé par l'utilisateur marche
    TEL_PF = "33600000061"
    AW.poser_pris(cA, A, "tel:" + TEL_PF, True)
    ajouter("PN-A", entrant("Vous êtes là ?", TEL_PF))
    s = poser(Script([outil("rediger_reponse", {"texte": "Oui."})]))
    lus0, e0 = len(FK.lus), len(FK.envois)
    tick(M, quand)
    bpf = AW.brouillons(A, "PN-A").get("tel:" + TEL_PF) or {}
    check("R13.4 contact pris : aucun rediger, aucun accusé, rien envoyé ; pris gardé, entrant noté traité",
          "tel:" + TEL_PF not in APPELS_R13 and s.appels == [] and len(FK.lus) == lus0 and FK.envois[e0:] == []
          and bpf.get("pris") is True and bpf.get("traite_jusqu_a") and "etat" not in bpf, bpf)
    r = run(AW.rediger(cA, A, "tel:" + TEL_PF))
    bpf = AW.brouillons(A, "PN-A").get("tel:" + TEL_PF) or {}
    check("R13.5 rediger demandé à la main sur un contact pris : brouillon attente, pris gardé",
          r.get("etat") == "attente" and bpf.get("etat") == "attente" and bpf.get("pris") is True, (r, bpf))
    AW.poser_pris(cA, A, "tel:" + TEL_PF, False)
    ajouter("PN-A", entrant("Et maintenant ?", TEL_PF))
    APPELS_R13.clear()
    s = poser(Script([outil("rediger_reponse", {"texte": "Je vous écoute."})]))
    tick(M, quand)
    check("R13.6 fil rendu : le relevé reprend (rediger appelé)", APPELS_R13 == ["tel:" + TEL_PF], APPELS_R13)

    # (3) garde-fou argent élargi en mode auto
    for k_, (tel_, texte_) in enumerate((("33600000062", "Le tarif est de 80 la séance"), ("33600000063", "Comptez 50 USD"),
                                         ("33600000064", "Profitez de −20 % ce mois-ci"), ("33600000065", "C'est gratuit !"))):
        ajouter("PN-A", entrant("Une question", tel_))
        s = poser(Script([outil("rediger_reponse", {"texte": texte_})]))
        e0 = len(FK.envois)
        tick(M, quand)
        b_ = AW.brouillons(A, "PN-A").get("tel:" + tel_) or {}
        check(f"R13.7.{k_ + 1} auto « {texte_} » : brouillon gardé, rien envoyé",
              FK.envois[e0:] == [] and b_.get("etat") == "attente" and WR.montant_hors_fiche(texte_, A), b_)
    check("R13.8 un nombre absent de la fiche, sans mot d'argent, garde aussi le brouillon ; un nombre de la fiche passe",
          WR.montant_hors_fiche("Nous avons 3 places", A) and not WR.montant_hors_fiche("Ouvert samedi de 9 h à 12 h", A))

    # (4) borne de rédactions par contact et par jour (le relevé seulement)
    WA.regler_espace(A, {"agent": {"mode": "brouillon", "plafond_redactions_jour": 1}})
    TEL_PL = "33600000066"
    ajouter("PN-A", entrant("Première question", TEL_PL))
    APPELS_R13.clear()
    s = poser(Script([outil("rediger_reponse", {"texte": "Première réponse."})]))
    tick(M, quand)
    ajouter("PN-A", entrant("Deuxième question", TEL_PL))
    s2 = poser(Script([]))
    tick(M, quand)
    bpl = AW.brouillons(A, "PN-A").get("tel:" + TEL_PL) or {}
    check("R13.9 borne 1 : un seul rediger du relevé ce jour, le second entrant noté traité, brouillon d'avant intact",
          APPELS_R13 == ["tel:" + TEL_PL] and s2.appels == [] and (bpl.get("redactions_jour") or {}).get(jour_local(quand)) == 1
          and bpl.get("etat") == "attente" and bpl["carte"]["arguments"]["texte"] == "Première réponse."
          and datetime.fromisoformat(bpl["traite_jusqu_a"]) == datetime.fromtimestamp(
              int(FK.msgs["PN-A"][0]["timestamp"]), timezone.utc), (APPELS_R13, bpl))
    s = poser(Script([outil("rediger_reponse", {"texte": "Réponse manuelle."})]))
    r = run(AW.rediger(cA, A, "tel:" + TEL_PL))
    check("R13.10 un rediger demandé par l'utilisateur ne compte pas et n'est pas borné",
          r.get("etat") == "attente" and (AW.brouillons(A, "PN-A")["tel:" + TEL_PL].get("redactions_jour") or {}).get(
              jour_local(quand)) == 1, r)
    ajouter("PN-A", entrant("Troisième question", TEL_PL))
    APPELS_R13.clear()
    s = poser(Script([outil("rediger_reponse", {"texte": "Nouveau jour."})]))
    tick(M, quand + timedelta(days=1))
    check("R13.11 jour local suivant : de nouveau une rédaction", APPELS_R13 == ["tel:" + TEL_PL], APPELS_R13)
    WA.regler_espace(A, {"agent": {"plafond_redactions_jour": 20}})

    # (5) le relevé n'envoie jamais un brouillon `incertain`
    TEL_IN = "33600000067"
    cle_in, grp_in = AW.canonique(cA, "tel:" + TEL_IN)
    AW.ranger(A, "PN-A", cle_in, "attente", WR._carte("Bonjour"), None, grp_in)
    AW._modifier(A, "PN-A", cle_in, lambda b_: {**b_, "incertain": True}, grp_in)
    e0 = len(FK.envois)
    envoye = run(WR._envoyer_auto(cA, A, "PN-A", "tel:" + TEL_IN, cle_in, grp_in, jour_local(quand), hors=False))
    bin_ = AW.brouillons(A, "PN-A")[cle_in]
    check("R13.12 envoi automatique d'un brouillon incertain : refusé, rien envoyé, brouillon attente+incertain",
          envoye is False and FK.envois[e0:] == [] and bin_["etat"] == "attente" and bin_.get("incertain") is True, bin_)
finally:
    AW.rediger = _rediger_r13

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R14] correction 2 : texte puis bouton dans le même tour, bouton seul, alias pris, _fil")
APPELS_R14 = []


async def rediger_espion14(cid, eid, identite, langue="fr"):
    APPELS_R14.append(identite)
    return await _rediger_r13(cid, eid, identite, langue=langue)


def bouton_val(tel, post, choix="ok"):
    N[0] += 1
    return {"id": f"in{N[0]}", "type": "interactive", "from": tel, "timestamp": ts(BASE + timedelta(seconds=2 * N[0])),
            "kapso": {"direction": "inbound"},
            "interactive": {"type": "button_reply", "button_reply": {"id": f"val:{post}:{choix}", "title": "Valider"}}}


AW.rediger = rediger_espion14
try:
    WA.regler_espace(A, {"agent": {"mode": "auto"}})
    TEL_TB = "33600000070"
    AW.modifier_validations(A, lambda v: {**v, "p-tb": {"identite": "tel:" + TEL_TB, "cid": cA, "etat": "valide",
                                                       "envoye_le": maintenant().isoformat(timespec="seconds")}})
    m_txt = entrant("Super", TEL_TB)
    m_btn = bouton_val(TEL_TB, "p-tb")
    ajouter("PN-A", m_txt, m_btn)
    s = poser(Script([outil("rediger_reponse", {"texte": "Avec plaisir !"})]))
    e0 = len(FK.envois)
    tick(M, quand)
    btb = AW.brouillons(A, "PN-A").get("tel:" + TEL_TB) or {}
    check("R14.1 « Super » puis « Valider » dans le même tour : aucun rediger, aucun envoi, noté traité jusqu'au bouton",
          APPELS_R14 == [] and s.appels == [] and FK.envois[e0:] == [] and "etat" not in btb
          and datetime.fromisoformat(btb.get("traite_jusqu_a") or "1970-01-01T00:00:00+00:00")
          == datetime.fromtimestamp(int(m_btn["timestamp"]), timezone.utc), (APPELS_R14, FK.envois[e0:], btb))
    texte_fil, _stop = run(AW._fil(cA, "tel:" + TEL_TB))
    check("R14.2 _fil ignore le bouton de validation : le dernier entrant lu est « Super »", texte_fil == "Super", texte_fil)
    TEL_BS = "33600000071"
    WA.regler_espace(A, {"agent": {"mode": "brouillon"}})
    ajouter("PN-A", entrant("Bonjour, une question", TEL_BS))
    s = poser(Script([outil("rediger_reponse", {"texte": "Je vous écoute."})]))
    tick(M, quand)
    AW.modifier_validations(A, lambda v: {**v, "p-bs": {"identite": "tel:" + TEL_BS, "cid": cA, "etat": "envoye",
                                                       "envoye_le": maintenant().isoformat(timespec="seconds")}})
    APPELS_R14.clear()
    ajouter("PN-A", bouton_val(TEL_BS, "p-bs"))
    s = poser(Script([]))
    e0 = len(FK.envois)
    tick(M, quand)
    check("R14.3 bouton seul après un texte déjà traité : aucun rediger, aucun envoi", APPELS_R14 == [] and s.appels == []
          and FK.envois[e0:] == [], APPELS_R14)
    # pris rangé sous l'identité tel: alors que la clé canonique du contact est son BSUID (alias appris après)
    TEL_AL = "33600000072"
    AW._modifier(A, "PN-A", "tel:" + TEL_AL, lambda b_: {"carte": None, "auto_jour": {}, "pris": True})
    WA._noter(cA, lambda e: e["alias"].update({"bsuid:AL-72": "tel:" + TEL_AL, "tel:" + TEL_AL: "bsuid:AL-72"}))
    APPELS_R14.clear()
    ajouter("PN-A", entrant("Vous êtes là ?", TEL_AL))
    s = poser(Script([outil("rediger_reponse", {"texte": "Oui."})]))
    tick(M, quand)
    check("R14.4 pris rangé sous l'alias (avant migration) : le relevé se tait", APPELS_R14 == [] and s.appels == [],
          (APPELS_R14, AW.brouillons(A, "PN-A").get("bsuid:AL-72")))
finally:
    AW.rediger = _rediger_r13

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R10] releve_loop et lifespan")
SEQ = []
_lire_vrai = E.lire


def lire_espion(*a, **k):
    SEQ.append(("lire",))
    return _lire_vrai(*a, **k)


async def dormir_espion(s_):
    SEQ.append(("dormir", s_))
    if sum(1 for x in SEQ if x[0] == "dormir") >= 4:
        raise asyncio.CancelledError


TOURS = []


async def tick_espion(marqueur, maintenant=None):
    TOURS.append(id(marqueur))
    SEQ.append(("tick",))
    if len(TOURS) == 1:
        raise RuntimeError("tour en panne")
    return {}


_dormir_vrai, _tick_vrai = WR._dormir, WR.releve_tick
WR._dormir, WR.releve_tick, E.lire = dormir_espion, tick_espion, lire_espion
try:
    try:
        run(WR.releve_loop())
        sortie = "rendue"
    except asyncio.CancelledError:
        sortie = "annulee"
finally:
    WR._dormir, WR.releve_tick, E.lire = _dormir_vrai, _tick_vrai, _lire_vrai
check("R10.1 première action : dormir DELAI_DEMARRAGE, aucun espaces.lire() avant", SEQ[:1] == [("dormir", 30)], SEQ)
check("R10.2 puis un tour, INTERVALLE, un tour… ; un tour en panne n'arrête pas la boucle",
      SEQ[1:6] == [("tick",), ("dormir", 120), ("tick",), ("dormir", 120), ("tick",)] and sortie == "annulee", SEQ)
check("R10.3 un seul marqueur gardé d'un tour à l'autre", len(set(TOURS)) == 1, TOURS)
src = (pathlib.Path(MAIN.__file__)).read_text(encoding="utf-8")
check("R10.4 lifespan : tâche créée depuis releve_loop et passée à _arreter_taches",
      "asyncio.create_task(releve_loop())" in src and "releve_task" in src.split("_arreter_taches([t for t in (")[1].split(")")[0]
      and hasattr(MAIN, "releve_loop"), "")
from fastapi.testclient import TestClient                            # noqa: E402
import time                                                          # noqa: E402
t0 = time.monotonic()
with TestClient(MAIN.app, client=("127.0.0.1", 50000)) as c_:
    c_.get("/api/health")
check("R10.5 démarrage et arrêt de l'application : la tâche du relevé est annulée sans attendre (< 10 s)",
      time.monotonic() - t0 < 10, time.monotonic() - t0)

# ---------------------------------------------------------------------------------------------------------------------
print("\n[R11] journal")
TEXTES = ("Quels sont vos horaires", "Oui, samedi", "coloration", "Nous sommes fermés", "Vous faites les barbes")
check("R11.1 aucun texte de message ni clé au journal",
      not any(any(t in l for t in TEXTES) or KA_CLE in l or CLE_ANT in l for l in JOURNAL),
      [l for l in JOURNAL if any(t in l for t in TEXTES)][:3])

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
