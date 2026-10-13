# -*- coding: utf-8 -*-
"""t203 (Espaces de marque E3, 13/10/2026) — PLUSIEURS comptes de diffusion par plateforme, rattachés à un espace.
Ce que ce banc garde :
  - les clés plates d'avant restent le compte HISTORIQUE de Deepotus, lu tel quel (rien de migré, rien de cassé) ;
  - un compte neuf range ses SECRETS hors de comptes.json (coffre ouvert, sinon .env, sous DZC_<ID>_<CHAMP>) et ses
    champs publics dans comptes.json ; aucune route ne rend jamais une valeur secrète ;
  - publier / tester SOUS un compte lit SES identifiants (X par un faux tweepy, dans le fil d'asyncio.to_thread ;
    Telegram par un faux httpx), sans compte les clés plates ; un compte d'une autre plateforme est refusé ;
  - TikTok : jeton d'accès mis en cache PAR compte, refresh token tournant réécrit DANS le compte (pas la clé plate) ;
  - OAuth YouTube : ?compte= au départ, le jeton rendu au retour est rangé dans CE compte ;
  - coffre posé mais FERMÉ : aucun secret écrit (409) ; supprimer un compte efface ses secrets ;
  - un compte historique ne se modifie pas ici (409). Aucun réseau, rien de payé, data-dir isolé.
Témoin positif : la base (80bcb649) n'a ni le module ni les routes /comptes.
Run (depuis backend/) : & $PY tests/test_espaces_comptes.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcpt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
# clés de banc : celles de l'utilisateur (variables Windows héritées) ne doivent jamais servir ici (#69)
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CHANNEL_ID", "IG_ACCESS_TOKEN",
          "IG_BUSINESS_ID", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "80bcb649"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/comptes.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a ni le module ni les routes /comptes", r0.returncode != 0 and b'"/comptes"' not in r1.stdout)

from app.config import settings, ENV_FILE                          # noqa: E402
from app.services import comptes as CP, espaces as ES, coffre as C, publishers as PUB, marketing as MK  # noqa: E402
from app.services import tiktok_publisher as TP, youtube_publisher as YP  # noqa: E402

# l'historique : des clés plates X et Telegram réglées (comme chez l'utilisateur)
for k, v in {"X_API_KEY": "plat-k", "X_API_SECRET": "plat-s", "X_ACCESS_TOKEN": "plat-t", "X_ACCESS_SECRET": "plat-ts",
             "TELEGRAM_BOT_TOKEN": "111:PLAT", "TELEGRAM_CHAT_ID": "-100plat"}.items():
    setattr(settings, k, v)
ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]

print("[H] le compte historique")
h = {c["id"]: c for c in CP.lister("deepotus")}
check("H1 X et Telegram plats -> comptes historiques de Deepotus, disponibles ; pas YouTube (rien de réglé)",
      set(h) == {"historique-x", "historique-telegram"} and all(v["disponible"] and v["historique"] for v in h.values()), str(list(h)))
check("H2 un autre espace n'a PAS les comptes historiques", CP.lister(rip) == [])
check("H3 sans compte courant, cred = settings (comportement d'avant)", CP.cred.X_ACCESS_TOKEN == "plat-t" and CP.cred.has_x is True)
try:
    CP.modifier("historique-x", {"libelle": "z"}); check("H4 un compte historique ne se modifie pas ici", False)
except CP.CompteHistorique:
    check("H4 un compte historique ne se modifie pas ici", True)

print("\n[C] un compte neuf (pas de coffre : .env)")
SECRETS = {"X_API_KEY": "rip-k-SECRET", "X_API_SECRET": "rip-s-SECRET", "X_ACCESS_TOKEN": "rip-t-SECRET", "X_ACCESS_SECRET": "rip-ts-SECRET"}
cx = CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "Rippled X", "handle": "@rippled", "valeurs": SECRETS})
cid = cx["id"]
check("C1 créé : id cxxxxxxxx, de l'espace Rippled, disponible", cid.startswith("c") and cx["espace_id"] == rip and cx["disponible"], str(cx))
env = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
check("C2 secrets dans le .env sous DZC_<ID>_<CHAMP>", f"DZC_{cid.upper()}_X_ACCESS_TOKEN=rip-t-SECRET" in env, env[-300:])
brut = (_tmp / "espaces" / "comptes.json").read_text(encoding="utf-8")
VALEURS_SECRETES = ("rip-k-SECRET", "rip-s-SECRET", "rip-t-SECRET", "rip-ts-SECRET", "RIP-SECRET", "rs-SECRET", "rr-NEUF", "rip-csec-SECRET", "RT-DU-COMPTE-SECRET")
def fuite(t):
    return [v for v in VALEURS_SECRETES if v in t]
check("C3 comptes.json ne contient AUCUN secret", not fuite(brut) and "@rippled" in brut, str(fuite(brut)))
check("C4 la vue du compte ne rend aucune valeur secrète (posé : oui/non)", not fuite(json.dumps(CP.lister()))
      and all(f["pose"] for f in cx["champs"]))
with CP.sous_compte(cid):
    check("C5 sous le compte, cred lit SES identifiants", CP.cred.X_ACCESS_TOKEN == "rip-t-SECRET" and CP.cred.has_x)
check("C6 hors du bloc, retour aux clés plates", CP.cred.X_ACCESS_TOKEN == "plat-t")
ct = CP.creer({"espace_id": rip, "plateforme": "telegram", "valeurs": {"TELEGRAM_BOT_TOKEN": "222:RIP-SECRET", "TELEGRAM_CHAT_ID": "-100rip"}})
check("C7 Telegram : chat public dans comptes.json, jeton secret ailleurs",
      '"-100rip"' in (_tmp / "espaces" / "comptes.json").read_text(encoding="utf-8")
      and "RIP-SECRET" not in (_tmp / "espaces" / "comptes.json").read_text(encoding="utf-8"))
for mauvais, quoi in (({"espace_id": "inconnu", "plateforme": "x"}, KeyError), ({"espace_id": rip, "plateforme": "myspace"}, ValueError)):
    try:
        CP.creer(mauvais); check(f"C8 refus {quoi.__name__}", False)
    except quoi:
        check(f"C8 refus {quoi.__name__}", True)
try:
    CP.poser(cid, {"TELEGRAM_CHAT_ID": "x"}); check("C9 un champ étranger à la plateforme est refusé", False)
except ValueError:
    check("C9 un champ étranger à la plateforme est refusé", True)
check("C10 de_l_espace : la garde de t204", CP.de_l_espace(cid, rip) and not CP.de_l_espace(cid, "deepotus")
      and CP.de_l_espace("historique-x", "deepotus") and not CP.de_l_espace("historique-x", rip))

print("\n[P] publier sous un compte")
vu = []
class FauxClient:
    def __init__(self, **kw): vu.append(kw)
    def create_tweet(self, **kw): return types.SimpleNamespace(data={"id": "777"})
import tweepy                                                        # noqa: E402
_orig = tweepy.Client
tweepy.Client = FauxClient
try:
    r1 = asyncio.run(PUB.publish("x", "bonjour", None, None, {}, compte=cid))
    r2 = asyncio.run(PUB.publish("x", "bonjour", None, None, {}))
finally:
    tweepy.Client = _orig
check("P1 X sous le compte : tweepy reçoit SES clés (dans le fil to_thread)", r1.ok and vu[0]["access_token"] == "rip-t-SECRET", str(vu[:1]))
check("P2 X sans compte : les clés plates (comportement d'avant)", r2.ok and vu[1]["access_token"] == "plat-t", str(vu[1:2]))
r3 = asyncio.run(PUB.publish("x", "b", None, None, {}, compte=ct["id"]))
r4 = asyncio.run(PUB.publish("x", "b", None, None, {}, compte="cdeadbeef"))
check("P3 un compte Telegram pour X est refusé, sans appel", not r3.ok and "telegram" in r3.detail and len(vu) == 2)
check("P4 un compte inconnu est refusé", not r4.ok and "inconnu" in r4.detail)
envois = []
class FauxHttpx:
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def post(self, url, data=None, json=None, files=None):
        envois.append((url, (json or data or {}).get("chat_id")))
        return types.SimpleNamespace(status_code=200, json=lambda: {"ok": True})
_oh = MK.httpx.AsyncClient
MK.httpx.AsyncClient = FauxHttpx
try:
    rt = asyncio.run(PUB.publish("telegram", "salut", None, None, {}, compte=ct["id"]))
    rt2 = asyncio.run(PUB.publish("telegram", "salut", None, None, {}))
finally:
    MK.httpx.AsyncClient = _oh
check("P5 Telegram sous le compte : son bot et son chat ; sans compte : les plats",
      rt.ok and rt2.ok and envois[0] == ("https://api.telegram.org/bot222:RIP-SECRET/sendMessage", "-100rip")
      and envois[1] == ("https://api.telegram.org/bot111:PLAT/sendMessage", "-100plat"), str(envois))

print("\n[K] TikTok : cache et refresh token tournant par compte")
ck = CP.creer({"espace_id": rip, "plateforme": "tiktok", "valeurs": {"TIKTOK_CLIENT_KEY": "rk", "TIKTOK_CLIENT_SECRET": "rs-SECRET",
                                                                   "TIKTOK_REFRESH_TOKEN": "rr-ANCIEN"}})
settings.TIKTOK_REFRESH_TOKEN = "plat-rr"
demandes = []
async def faux_token(grant):
    demandes.append((grant.get("refresh_token"), CP.cred.TIKTOK_CLIENT_KEY))
    return {"access_token": "acc-" + str(len(demandes)), "expires_in": 3600, "refresh_token": "rr-NEUF"}
_ot = TP._token
TP._token = faux_token
TP._oublier_jeton()
try:
    async def k():
        with CP.sous_compte(ck["id"]):
            a = await TP.access_token(); b = await TP.access_token()
        return a, b
    a, b = asyncio.run(k())
finally:
    TP._token = _ot
check("K1 le compte rafraîchit avec SON refresh token et SON client ; le 2e appel sort du cache",
      demandes == [("rr-ANCIEN", "rk")] and a == b == "acc-1", str(demandes))
with CP.sous_compte(ck["id"]):
    neuf = CP.cred.TIKTOK_REFRESH_TOKEN
check("K2 le refresh token tournant est réécrit DANS le compte, la clé plate intacte",
      neuf == "rr-NEUF" and settings.TIKTOK_REFRESH_TOKEN == "plat-rr", f"{neuf} / {settings.TIKTOK_REFRESH_TOKEN}")
check("K3 le cache du compte historique n'a rien reçu", TP._jeton["valeur"] == "")

print("\n[O] OAuth YouTube par compte")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
cy = CP.creer({"espace_id": rip, "plateforme": "youtube", "valeurs": {"YOUTUBE_CLIENT_ID": "rip-cid", "YOUTUBE_CLIENT_SECRET": "rip-csec-SECRET"}})
d = c.get(f"/api/oauth/youtube/start?compte={cy['id']}", follow_redirects=False)
from urllib.parse import urlparse, parse_qs                         # noqa: E402
q = parse_qs(urlparse(d.headers.get("location", "")).query)
check("O1 départ : redirection Google avec le client_id DU COMPTE", d.status_code == 302 and q.get("client_id") == ["rip-cid"], d.text[:200])
check("O2 départ sans client réglé pour un compte vide -> 400",
      c.get(f"/api/oauth/youtube/start?compte={CP.creer({'espace_id': rip, 'plateforme': 'youtube'})['id']}", follow_redirects=False).status_code == 400)
check("O3 départ avec un compte d'une autre plateforme -> 400", c.get(f"/api/oauth/youtube/start?compte={cid}", follow_redirects=False).status_code == 400)
vu_ex = []
async def faux_exchange(code, state):
    vu_ex.append(CP.cred.YOUTUBE_CLIENT_ID); YP._VERIFS.pop(state, None); return "RT-DU-COMPTE-SECRET"
_oe = YP.exchange_code
YP.exchange_code = faux_exchange
try:
    rb = c.get(f"/api/oauth/youtube/callback?code=abc&state={q['state'][0]}")
finally:
    YP.exchange_code = _oe
with CP.sous_compte(cy["id"]):
    rt_compte = CP.cred.YOUTUBE_REFRESH_TOKEN
check("O4 retour : l'échange se fait avec le client du compte, le jeton est rangé DANS le compte, la clé plate vide",
      rb.status_code == 200 and vu_ex == ["rip-cid"] and rt_compte == "RT-DU-COMPTE-SECRET" and settings.YOUTUBE_REFRESH_TOKEN == "",
      f"{rb.status_code} {vu_ex} {rt_compte!r}")
check("O5 le compte YouTube est désormais disponible", {x["id"]: x for x in CP.lister(rip)}[cy["id"]]["disponible"])

print("\n[R] les routes")
g = c.get(f"/api/comptes?espace={rip}")
check("R1 GET /api/comptes : les comptes de l'espace, AUCUNE valeur secrète, les plateformes décrites",
      g.status_code == 200 and not fuite(g.text) and len(g.json()["comptes"]) >= 5
      and set(g.json()["plateformes"]) == {"x", "telegram", "youtube", "instagram", "tiktok"}, g.text[:200])
check("R2 GET sans espace = l'espace actif (Deepotus) : les historiques (TikTok depuis la clé plate posée en K)",
      {x["id"] for x in c.get("/api/comptes").json()["comptes"]} == {"historique-x", "historique-telegram", "historique-tiktok"})
p = c.post("/api/comptes", json={"espace_id": rip, "plateforme": "instagram", "libelle": "IG Rippled"})
check("R3 POST crée", p.status_code == 200 and p.json()["compte"]["plateforme"] == "instagram")
check("R4 POST plateforme inconnue -> 400, espace inconnu -> 404",
      c.post("/api/comptes", json={"espace_id": rip, "plateforme": "z"}).status_code == 400
      and c.post("/api/comptes", json={"espace_id": "nope", "plateforme": "x"}).status_code == 404)
check("R5 modifier l'historique -> 409", c.post("/api/comptes/historique-x", json={"libelle": "z"}).status_code == 409)
tc = []
async def faux_tg(caption, **kw):
    tc.append(CP.cred.TELEGRAM_CHAT_ID); return True, "sent"
_otg = MK.publish_telegram
MK.publish_telegram = faux_tg
try:
    rr = c.post("/api/channels/test", json={"channel": "telegram", "compte": ct["id"]})
    rr2 = c.post("/api/channels/test", json={"channel": "telegram"})
finally:
    MK.publish_telegram = _otg
check("R6 tester un compte lit SES identifiants ; sans compte, les plats", rr.json().get("ok") and tc == ["-100rip", "-100plat"], str(tc))
check("R7 tester un compte d'une autre plateforme -> 400", c.post("/api/channels/test", json={"channel": "x", "compte": ct["id"]}).status_code == 400)
dist = TestClient(app, client=("192.168.1.20", 50000))
check("R8 écrire depuis le réseau local sans jeton -> refusé", dist.post("/api/comptes", json={"espace_id": rip, "plateforme": "x"}).status_code in (401, 403))

print("\n[V] coffre posé mais FERMÉ, suppression")
C.poser("mot-de-passe-de-banc", {})
check("V0 coffre posé et fermé", C.verrouille())
avant = ENV_FILE.read_text(encoding="utf-8")
v = c.post(f"/api/comptes/{cid}", json={"valeurs": {"X_ACCESS_TOKEN": "NOUVEAU-SECRET"}})
check("V1 écrire un secret coffre fermé -> 409, rien d'écrit", v.status_code == 409 and ENV_FILE.read_text(encoding="utf-8") == avant
      and "NOUVEAU-SECRET" not in json.dumps(dict(os.environ)), v.text[:200])
check("V2 supprimer un compte à secrets coffre fermé -> 409", c.delete(f"/api/comptes/{cid}").status_code == 409)
C.ouvrir("mot-de-passe-de-banc")
v3 = c.post(f"/api/comptes/{cid}", json={"valeurs": {"X_ACCESS_TOKEN": "COFFRE-SECRET"}})
check("V3 coffre ouvert : le secret va AU COFFRE (pas au .env)", v3.status_code == 200 and C.lire_cle(f"DZC_{cid.upper()}_X_ACCESS_TOKEN") == "COFFRE-SECRET"
      and "COFFRE-SECRET" not in ENV_FILE.read_text(encoding="utf-8"))
dl = c.delete(f"/api/comptes/{cid}")
env2 = ENV_FILE.read_text(encoding="utf-8")
check("V4 supprimer efface ses secrets (coffre ET .env) et le retire de la liste",
      dl.status_code == 200 and C.lire_cle(f"DZC_{cid.upper()}_X_ACCESS_TOKEN") is None and f"DZC_{cid.upper()}_" not in env2
      and all(x["id"] != cid for x in CP.lister()) and not os.environ.get(f"DZC_{cid.upper()}_X_API_KEY"), env2[-300:])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
