# -*- coding: utf-8 -*-
"""t310 (27/10/2026) — Tâche 2 : client REST Kapso. ZÉRO réseau : `kapso._requete` (seule fonction qui touche le réseau) et
`kapso._dormir` (attente du réessai 429) sont remplacés ; `_requete` elle-même n'est exercée qu'avec un faux httpx.AsyncClient.
Couvre : méthode/URL/corps exacts de chaque fonction du relevé, clé en en-tête (jamais dans la query), 429 (Retry-After puis
200 ; six 429 = 5 essais), erreurs sans réessai (un seul appel), Review Focus 1 (aucun secret dans str(e), e.message ni le
journal loguru), `token` du lien jamais rendu, clé absente sans réseau, `media` (HTTPS, hôte api.kapso.ai, pas de redirection),
BSUID sans `to`.
Run (depuis backend/) : & $PY tests/test_kapso.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzkapso_"))
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

try:
    from app.services import kapso as K                            # noqa: E402
except ImportError as e:
    print(f"  FAIL  0 module kapso absent ({e})")
    print(f"\n{ok} PASS / 1 FAIL")
    sys.exit(1)

CLE = "SECRET-KAPSO-123"
PL, PX = K.PLATFORM, K.PROXY
settings.KAPSO_API_KEY = CLE

APPELS: list = []          # (methode, url, json, params)
FILE: list = []            # réponses à rendre, dans l'ordre (la dernière se répète) : (statut, corps, entetes) ou exception
DORS: list = []
VRAIE_REQUETE = K._requete  # gardée pour la section [e] (avec un faux httpx)


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


def rep(corps, statut=200, entetes=None):
    return (statut, corps, entetes or {})


print("[a] constantes et classe d'erreur")
check("A1 PLATFORM", PL == "https://api.kapso.ai/platform/v1")
check("A2 PROXY", PX == "https://api.kapso.ai/meta/whatsapp/v24.0")
e = K.KapsoErreur("m", statut=422, code="131047", reessayable=False)
check("A3 KapsoErreur : RuntimeError + attributs", isinstance(e, RuntimeError) and e.statut == 422 and e.code == "131047"
      and e.reessayable is False and e.message == "m" and str(e) == "m")
check("A4 message borné à 200", len(K.KapsoErreur("x" * 500).message) == 200)

print("\n[b] plateforme : méthode, URL, corps")
scene(rep({"data": {"id": "c1", "name": "Rip", "external_customer_id": "e1"}}, 201))
r = run(K.creer_customer("Rip", "e1"))
check("B1 creer_customer : POST /customers, corps {customer:{name,external_customer_id}}",
      APPELS == [("POST", f"{PL}/customers", {"customer": {"name": "Rip", "external_customer_id": "e1"}}, None)], APPELS)
check("B2 creer_customer rend data", r["id"] == "c1")
scene(rep({"data": {"id": "L1", "url": "https://app.kapso.ai/s/x", "token": "TOK-LIEN-999", "expires_at": "2026-11-26",
                    "status": "active", "whatsapp_setup_status": "pending"}}, 201))
r = run(K.creer_lien("c1", "customer_managed"))
check("B3 creer_lien : POST /customers/c1/setup_links, corps {setup_link:{meta_billing_mode}}",
      APPELS == [("POST", f"{PL}/customers/c1/setup_links", {"setup_link": {"meta_billing_mode": "customer_managed"}}, None)],
      APPELS)
check("B4 creer_lien rend id/url/expire_le/statut", r == {"id": "L1", "url": "https://app.kapso.ai/s/x",
                                                          "expire_le": "2026-11-26", "statut": "active"}, r)
check("B5 creer_lien : le token n'est jamais rendu", "TOK-LIEN-999" not in repr(r) and "token" not in r)
scene(rep({"data": {"id": "L2", "url": "u", "expires_at": None, "status": "active"}}, 201))
run(K.creer_lien("c1", "partner_managed", "en"))
check("B6 creer_lien avec langue", APPELS[0][2] == {"setup_link": {"meta_billing_mode": "partner_managed", "language": "en"}},
      APPELS)
scene(rep({"data": [{"id": "L1", "status": "used", "created_at": "t1", "whatsapp_setup_status": "completed",
                     "whatsapp_setup_error": None, "token": "ZZZ", "url": "u"}]}))
r = run(K.liens("c1"))
check("B7 liens : GET /customers/c1/setup_links", APPELS == [("GET", f"{PL}/customers/c1/setup_links", None, None)], APPELS)
check("B8 liens : champs rendus, sans token",
      r == [{"id": "L1", "statut": "used", "whatsapp_setup_status": "completed", "whatsapp_setup_error": None,
             "cree_le": "t1"}], r)
scene(rep({"data": [{"id": "PN1", "phone_number_id": "PN1", "display_phone_number": "+33 6", "verified_name": "Rip",
                     "quality_rating": "GREEN", "status": "CONNECTED", "business_account_id": "W1", "autre": 1}]}))
r = run(K.numeros("c1"))
check("B9 numeros : GET /whatsapp/phone_numbers?customer_id=c1",
      APPELS == [("GET", f"{PL}/whatsapp/phone_numbers", None, {"customer_id": "c1"})], APPELS)
check("B10 numeros : champs rendus", r == [{"phone_number_id": "PN1", "display_phone_number": "+33 6", "verified_name": "Rip",
                                            "quality_rating": "GREEN", "status": "CONNECTED", "business_account_id": "W1"}], r)
scene(rep({"data": {"phone_number_id": "PN1", "status": "CONNECTED"}}))
r = run(K.numero("PN1"))
check("B11 numero : GET /whatsapp/phone_numbers/PN1", APPELS == [("GET", f"{PL}/whatsapp/phone_numbers/PN1", None, None)]
      and r["status"] == "CONNECTED", APPELS)

print("\n[c] opt-out marketing")
scene(rep({"data": [{"phone_number_id": "PN1", "status": "resumed", "marketing_allowed": True}]}))
check("C1 marketing_allowed vrai -> True", run(K.preferences_marketing("+33600000000")) is True)
check("C2 URL : contact encodé, sans query",
      APPELS == [("GET", f"{PL}/whatsapp/contacts/%2B33600000000/marketing_preferences", None, None)], APPELS)
scene(rep({"data": [{"phone_number_id": "PN1", "status": "stopped", "marketing_allowed": False}]}))
check("C3 arrêté -> False", run(K.preferences_marketing("+33600000000")) is False)
scene(rep({"data": []}))
check("C4 tableau vide = abonné -> True", run(K.preferences_marketing("+33600000000")) is True)
scene(rep({"data": [{"phone_number_id": "PN1", "marketing_allowed": False},
                    {"phone_number_id": "PN2", "marketing_allowed": True}]}))
check("C5 filtre par numéro émetteur (optionnel)",
      run(K.preferences_marketing("x", phone_number_id="PN2")) is True and run(K.preferences_marketing("x")) is False)
scene(rep({"error": "Marketing preference not found"}, 404))
check("C6 404 « Marketing preference not found » -> True", run(K.preferences_marketing("+33600000000")) is True)
scene(rep({"error": "WhatsApp contact not found"}, 404))
check("C7 404 contact inconnu -> None", run(K.preferences_marketing("+33600000000")) is None)
scene(rep({"error": "boom"}, 401))
e = erreur(K.preferences_marketing("x"))
check("C8 autre erreur : KapsoErreur", isinstance(e, K.KapsoErreur) and e.statut == 401, repr(e))

print("\n[d] proxy : méthode, URL, corps")
scene(rep({"messaging_product": "whatsapp", "contacts": [{"wa_id": "336"}],
           "messages": [{"id": "wamid.1", "message_status": "accepted"}]}))
r = run(K.envoyer("PN1", {"type": "text", "to": "336", "text": {"body": "salut"}}))
check("D1 envoyer : POST /PN1/messages, messaging_product ajouté",
      APPELS == [("POST", f"{PX}/PN1/messages", {"messaging_product": "whatsapp", "type": "text", "to": "336",
                                                  "text": {"body": "salut"}}, None)], APPELS)
check("D2 envoyer rend {id, statut}", r == {"id": "wamid.1", "statut": "accepted"}, r)
scene(rep({"messages": [{"id": "wamid.2"}]}))
r = run(K.envoyer("PN1", {"type": "text", "recipient": "FR.BSUID", "to": None, "text": {"body": "a"}}))
check("D3 BSUID : recipient sans to dans le corps", "to" not in APPELS[0][2] and APPELS[0][2]["recipient"] == "FR.BSUID",
      APPELS)
check("D3b statut par défaut", r == {"id": "wamid.2", "statut": "accepted"}, r)
scene(rep({"messages": []}))
e = erreur(K.envoyer("PN1", {"type": "text", "to": "1"}))
check("D3c réponse sans message : KapsoErreur", isinstance(e, K.KapsoErreur) and e.code == "reponse_invalide", repr(e))
scene(rep({"success": True}))
r = run(K.marquer_lu("PN1", "wamid.1"))
check("D4 marquer_lu : POST /PN1/messages {status: read, message_id}",
      APPELS == [("POST", f"{PX}/PN1/messages", {"messaging_product": "whatsapp", "status": "read",
                                                  "message_id": "wamid.1"}, None)] and r is None, APPELS)
scene(rep({"data": [{"id": "m1"}], "paging": {"cursors": {"before": "b", "after": "CUR2"}}}))
lst, cur = run(K.messages("PN1"))
check("D5 messages : GET /PN1/messages?limit=100, curseur suivant = after",
      APPELS == [("GET", f"{PX}/PN1/messages", None, {"limit": 100})] and lst == [{"id": "m1"}] and cur == "CUR2", APPELS)
scene(rep({"data": [], "paging": {}}))
lst, cur = run(K.messages("PN1", depuis="2026-10-27T00:00:00Z", apres="CUR2", limite=500))
check("D6 messages : since/after/limit (borné à 100)",
      APPELS[0][3] == {"limit": 100, "since": "2026-10-27T00:00:00Z", "after": "CUR2"} and lst == [] and cur is None, APPELS)
scene(rep({"data": [{"id": "cv1"}], "paging": {"cursors": {"after": "C9"}}}))
lst, cur = run(K.conversations("PN1", apres="C1", limite=20))
check("D7 conversations : GET /PN1/conversations", APPELS == [("GET", f"{PX}/PN1/conversations", None,
                                                               {"limit": 20, "after": "C1"})] and cur == "C9", APPELS)
scene(rep({"data": []}))
run(K.conversations("PN1", champs="kapso()"))
check("D7b conversations : fields optionnel", APPELS[0][3] == {"limit": 100, "fields": "kapso()"}, APPELS)
scene(rep({"data": [{"id": "t1", "name": "bienvenue"}]}))
r = run(K.modeles("W1"))
check("D8 modeles : GET /W1/message_templates?status=APPROVED",
      APPELS == [("GET", f"{PX}/W1/message_templates", None, {"status": "APPROVED", "limit": 100})]
      and r == [{"id": "t1", "name": "bienvenue"}], APPELS)
scene(rep({"data": []}))
run(K.modeles("W1", statut="PENDING"))
check("D9 modeles : statut choisi", APPELS[0][3]["status"] == "PENDING", APPELS)

print("\n[e] clé : en-tête seulement, absente = sans réseau")
settings.KAPSO_API_KEY = ""
scene(rep({"data": []}))
e = erreur(K.liens("c1"))
check("E1 clé absente : KapsoErreur(cle_absente), aucun appel réseau",
      isinstance(e, K.KapsoErreur) and e.code == "cle_absente" and APPELS == [] and e.reessayable is False, repr(e))
settings.KAPSO_API_KEY = CLE


class FauxReponse:
    status_code = 200
    headers = {"content-type": "application/json"}
    content = b'{"data": []}'
    def json(self):
        return {"data": []}


VU: dict = {}


class FauxClient:
    def __init__(self, **kw):
        VU["init"] = kw
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def request(self, methode, url, **kw):
        VU["req"] = (methode, url, kw)
        return FauxReponse()


vrai_client = K.httpx.AsyncClient
K.httpx.AsyncClient = FauxClient
try:
    st, corps, ent = run(VRAIE_REQUETE("GET", f"{PX}/PN1/messages", params={"limit": 5}))
    ini, req = VU["init"], VU["req"]
    check("E2 _requete : AsyncClient(verify=SSL_VERIFY, timeout=30, follow_redirects=False)",
          ini.get("timeout") == 30 and ini.get("follow_redirects") is False and "verify" in ini, ini)
    check("E3 _requete : X-API-Key porte la clé, la query ne la porte jamais",
          req[2]["headers"].get("X-API-Key") == CLE and CLE not in repr(req[1]) and CLE not in repr(req[2].get("params")), req)
    check("E4 _requete rend (statut, corps JSON, en-têtes)", st == 200 and corps == {"data": []} and isinstance(ent, dict))
    VU.pop("req", None)
    refus = erreur(VRAIE_REQUETE("GET", "http://api.kapso.ai/x"))
    check("E5 _requete refuse http, sans appel (la clé ne part jamais en clair)",
          isinstance(refus, K.KapsoErreur) and "req" not in VU, repr(refus))
    refus2 = erreur(VRAIE_REQUETE("GET", "https://evil.example/x"))
    check("E5b autre hôte refusé sans appel (la clé ne part jamais ailleurs)",
          isinstance(refus2, K.KapsoErreur) and refus2.code == "hote_refuse" and "req" not in VU, repr(refus2))
finally:
    K.httpx.AsyncClient = vrai_client

print("\n[f] 429 : un réessai après Retry-After, cinq essais au plus")
scene(rep({"error": "Rate limit exceeded"}, 429, {"Retry-After": "2"}), rep({"data": []}))
r = run(K.liens("c1"))
check("F1 429 (Retry-After: 2) puis 200 : deux appels, une attente de 2 s", len(APPELS) == 2 and DORS == [2.0] and r == [],
      (APPELS, DORS))
scene(rep({"error": "x"}, 429, {"retry-after": "3"}), rep({"error": "x"}, 429, {}), rep({"data": []}))
run(K.liens("c1"))
check("F2 en-tête insensible à la casse ; sans Retry-After : repli 2 s au 2e essai", DORS == [3.0, 2.0], DORS)
scene(rep({"error": "x"}, 429, {}))
e = erreur(K.liens("c1"))
check("F3 six 429 de suite : 5 essais, KapsoErreur(code 429)", isinstance(e, K.KapsoErreur) and e.code == "429"
      and len(APPELS) == 5 and e.statut == 429, (repr(e), len(APPELS)))
check("F4 attentes de repli 1, 2, 4, 8", DORS == [1.0, 2.0, 4.0, 8.0], DORS)
check("F4b 429 épuisé : réessayable par l'appelant", e.reessayable is True)
scene(rep({"error": {"message": "in flight", "code": "message_in_flight"}}, 409), rep({"messages": [{"id": "w"}]}))
r = run(K.envoyer("PN1", {"type": "text", "to": "1"}))
check("F5 409 message_in_flight : un réessai", len(APPELS) == 2 and r["id"] == "w" and DORS == [1.0], (APPELS, DORS))

print("\n[g] sans réessai : un seul appel, reessayable=False")
CAS = [
    ("422 131047 (proxy)", rep({"error": {"message": "Re-engagement", "type": "OAuthException", "code": 131047}}, 422), "131047"),
    ("422 marketing_preference_stopped (platform)",
     rep({"error": "Contact stopped marketing", "code": "marketing_preference_stopped"}, 422), "marketing_preference_stopped"),
    ("409 thread_not_owner", rep({"error": "Thread not owned", "code": "thread_not_owner"}, 409), "thread_not_owner"),
    ("402 insufficient_credits", rep({"error": "No credits", "code": "insufficient_credits"}, 402), "insufficient_credits"),
    ("502", rep({"error": "bad gateway"}, 502), "502"),
]
for lib, rp, code in CAS:
    scene(rp)
    e = erreur(K.envoyer("PN1", {"type": "text", "to": "1"}))
    check(f"G {lib} : un appel, code={code}, non réessayable",
          isinstance(e, K.KapsoErreur) and len(APPELS) == 1 and DORS == [] and e.reessayable is False and e.code == code
          and e.statut == rp[0], (repr(e), len(APPELS)))
scene(rep({"error": {"message": "m", "code": 100, "error_subcode": 2018}}, 400))
e = erreur(K.liens("c1"))
check("G6 forme proxy : message/code lus", e.code == "100" and e.message == "m", repr(e))
scene(rep("<html>Bad</html>", 500))
e = erreur(K.liens("c1"))
check("G7 corps non JSON : message générique", isinstance(e, K.KapsoErreur) and "<html>" not in e.message and e.code == "500", repr(e))
scene(RuntimeError(f"connexion https://api.kapso.ai/?key={CLE} refusée"))
e = erreur(K.liens("c1"))
check("G8 exception réseau : KapsoErreur(reseau), réessayable, texte de l'exception jamais recopié",
      isinstance(e, K.KapsoErreur) and e.code == "reseau" and e.reessayable is True and CLE not in e.message
      and len(APPELS) == 1, repr(e))

print("\n[h] Review Focus 1 : aucun secret dans l'erreur ni le journal")
journal: list = []
logger.add(lambda m: journal.append(str(m)), level="DEBUG")
PIEGE = (f"clé {CLE} refusée ; setup {{\"token\": \"TOKEN-LIEN-777\"}} ; "
         "https://api.kapso.ai/meta/whatsapp/media_download?token=ABC&x=1 ; token=DEF")
for lib, rp in [("Platform", rep({"error": PIEGE, "code": "x_" + CLE}, 422)),
                ("proxy", rep({"error": {"message": PIEGE, "type": "T", "code": 5, "error_subcode": CLE}}, 400)),
                ("429 épuisé", rep({"error": PIEGE}, 429, {}))]:
    scene(rp)
    e = erreur(K.envoyer("PN1", {"type": "text", "to": "1"}))
    texte = " ".join([str(e), getattr(e, "message", ""), getattr(e, "code", ""), repr(e)])
    check(f"H {lib} : ni clé, ni token de lien, ni token d'URL dans str/message/code",
          isinstance(e, K.KapsoErreur) and not any(s in texte for s in (CLE, "TOKEN-LIEN-777", "ABC", "DEF")), texte[:300])
scene(RuntimeError(f"échec {CLE}"))
erreur(K.liens("c1"))
scene(rep({"download_url": "https://api.kapso.ai/meta/whatsapp/media_download?token=TOKJOURNAL"}), rep({"error": PIEGE}, 404))
erreur(K.media("MID", "PN1"))
check("H4 journal loguru capturé : rien n'est noté ET aucun secret", len(journal) > 0 and
      not any(s in "\n".join(journal) for s in (CLE, "TOKEN-LIEN-777", "ABC", "DEF", "TOKJOURNAL")), "\n".join(journal)[:400])

print("\n[i] media : HTTPS, hôte api.kapso.ai, pas de redirection")
DL = "https://api.kapso.ai/meta/whatsapp/media_download?token=T1"
scene(rep({"id": "MID", "download_url": DL}), rep(b"\x89PNGdata"))
r = run(K.media("MID", "PN1"))
check("I1 media : GET /MID?phone_number_id=PN1 puis GET download_url tel quel",
      APPELS == [("GET", f"{PX}/MID", None, {"phone_number_id": "PN1"}), ("GET", DL, None, None)], APPELS)
check("I2 media rend les octets", r == b"\x89PNGdata", r)
for lib, url in [("autre hôte", "https://evil.example/media_download?token=T"),
                 ("http", "http://api.kapso.ai/meta/whatsapp/media_download?token=T"),
                 ("hôte déguisé", "https://api.kapso.ai.evil.example/x?token=T"),
                 ("userinfo", "https://api.kapso.ai@evil.example/x?token=T"),
                 ("autre port", "https://api.kapso.ai:8443/x?token=T")]:
    scene(rep({"id": "MID", "download_url": url}), rep(b"x"))
    e = erreur(K.media("MID", "PN1"))
    check(f"I3 {lib} : refusé AVANT le téléchargement (un seul appel)",
          isinstance(e, K.KapsoErreur) and e.code == "media_hote_refuse" and len(APPELS) == 1, (repr(e), len(APPELS)))
scene(rep({"id": "MID"}))
e = erreur(K.media("MID", "PN1"))
check("I4 sans download_url : KapsoErreur(media_sans_url)", isinstance(e, K.KapsoErreur) and e.code == "media_sans_url", repr(e))
scene(rep({"id": "MID", "download_url": DL}), (302, b"", {"Location": "https://evil.example/x"}))
e = erreur(K.media("MID", "PN1"))
check("I5 redirection 302 non suivie : KapsoErreur, un seul téléchargement",
      isinstance(e, K.KapsoErreur) and e.statut == 302 and len(APPELS) == 2, (repr(e), len(APPELS)))
scene(rep({"id": "MID", "download_url": DL}), rep({"x": 1}))
e = erreur(K.media("MID", "PN1"))
check("I6 corps du téléchargement non binaire : KapsoErreur", isinstance(e, K.KapsoErreur) and e.code == "reponse_invalide", repr(e))

print("\n[j] fixes de revue : curseur de fin, préférences fermées, téléchargement sans réessai, __context__")
scene(rep({"data": [], "paging": {"cursors": {"after": "CURX"}}}))
check("J1 page vide avec after non vide : curseur None (messages)", run(K.messages("PN1"))[1] is None)
scene(rep({"data": [], "paging": {"cursors": {"after": "CURX"}}}))
check("J1b idem (conversations)", run(K.conversations("PN1"))[1] is None)
scene(rep({"data": [{"id": "m"}], "paging": {"cursors": {"after": "CURX"}}}))
check("J2 page pleine : curseur gardé", run(K.messages("PN1"))[1] == "CURX")
scene(rep({"data": [{"phone_number_id": "PN1", "status": "stopped"}]}))
check("J3 ligne sans marketing_allowed mais status stopped : refusé", run(K.preferences_marketing("x")) is False)
scene(rep({"id": "MID", "download_url": DL}), rep({"error": "slow"}, 429, {"Retry-After": "1"}))
e = erreur(K.media("MID", "PN1"))
check("J4 429 sur le téléchargement : un seul essai, aucune attente, réessayable",
      isinstance(e, K.KapsoErreur) and e.code == "429" and e.reessayable is True and len(APPELS) == 2 and DORS == [],
      (repr(e), len(APPELS), DORS))
scene(RuntimeError("boom"))
e = erreur(K.liens("c1"))
check("J5 erreur réseau : __context__ et __cause__ vides", isinstance(e, K.KapsoErreur) and e.__context__ is None
      and e.__cause__ is None, repr(e))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
