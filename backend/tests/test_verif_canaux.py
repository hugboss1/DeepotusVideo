# -*- coding: utf-8 -*-
"""t308 (26/10/2026) — Tâche 1 : vérification d'un compte de diffusion SANS publier (X, Telegram, YouTube, Instagram,
TikTok). ZÉRO réseau : `verif_canaux._get`, `verif_canaux._x_me` et les jetons OAuth sont remplacés.
Couvre : vert / rouge (401) / orange (500, puis exception réseau) par plateforme ; Review Focus 1 (aucun secret dans
une sortie) ; Review Focus 3 (Telegram n'appelle jamais /send*) ; champs manquants ; TikTok non audité.
Run (depuis backend/) : & $PY tests/test_verif_canaux.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzverif_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CHANNEL_ID", "IG_ACCESS_TOKEN",
          "IG_BUSINESS_ID", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
    os.environ[k] = ""
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
    from app.services import verif_canaux as V                     # noqa: E402
except ImportError as e:
    print(f"  FAIL  0 module verif_canaux absent ({e})")
    print(f"\n{ok} PASS / 1 FAIL")
    sys.exit(1)
from app.services import youtube_publisher as YP, tiktok_publisher as TP  # noqa: E402

S = {"X_API_KEY": "SECRET-X-KEY-1", "X_API_SECRET": "SECRET-X-SEC-2", "X_ACCESS_TOKEN": "SECRET-X-AT-3",
     "X_ACCESS_SECRET": "SECRET-X-AS-4", "TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777",
     "YOUTUBE_CLIENT_ID": "SECRET-YT-ID", "YOUTUBE_CLIENT_SECRET": "SECRET-YT-CS", "YOUTUBE_REFRESH_TOKEN": "SECRET-YT-RT",
     "IG_ACCESS_TOKEN": "SECRET-IG-456", "IG_BUSINESS_ID": "1784000",
     "TIKTOK_CLIENT_KEY": "ck-pub", "TIKTOK_CLIENT_SECRET": "SECRET-TT-CS", "TIKTOK_REFRESH_TOKEN": "SECRET-TT-RT",
     "TIKTOK_AUDITED": "1"}
TOUS_SECRETS = [v for k, v in S.items() if v.startswith("SECRET")] + ["SECRET-ACCESS-YT", "SECRET-ACCESS-TT"]


def poser(**kw):
    for k in S:
        setattr(settings, k, "")
    for k, v in {**S, **kw}.items():
        setattr(settings, k, v)


APPELS: list = []
ROUTE: dict = {"mode": "vert"}      # vert | 401 | 500 | reseau | chat404


def _corps_vert(url):
    if "getMe" in url:
        return {"ok": True, "result": {"id": 42, "username": "deep_bot"}}
    if "getChat" in url:
        return {"ok": True, "result": {"id": -100777, "title": "Le Canal"}}
    if "youtube" in url:
        return {"items": [{"id": "UC123", "snippet": {"title": "Ma Chaine"}}]}
    if "open.tiktokapis" in url:
        return {"data": {"user": {"open_id": "oid-9", "display_name": "Tik Nom"}}}
    return {"id": "1784000", "username": "insta_nom"}


async def faux_get(url, headers=None, params=None, *a, **k):
    APPELS.append((url, dict(params or {}), dict(headers or {})))
    if "/send" in url:
        raise AssertionError(f"APPEL D'ENVOI INTERDIT : {url}")
    m = ROUTE["mode"]
    if m == "reseau":
        raise ConnectionError(f"connexion coupée sur {url}?{params} {headers}")
    if m == "401":
        # le corps d'erreur ÉCHOE les secrets (URL Telegram, query Instagram, jeton porteur)
        return 401, {"error": {"message": f"refus pour {url} {params} {headers}"}, "description": f"bad {url}"}
    if m == "500":
        return 500, {"error": f"boom {url} {params}"}
    if m == "chat404" and "getChat" in url:
        return 400, {"ok": False, "description": "Bad Request: chat not found"}
    return 200, _corps_vert(url)


async def faux_yt_token():
    if ROUTE["mode"] == "reseau":
        raise ConnectionError("réseau coupé SECRET-YT-RT")
    if ROUTE["mode"] == "401":
        raise RuntimeError("youtube token 401: invalid SECRET-YT-RT SECRET-YT-CS")
    if ROUTE["mode"] == "500":
        raise RuntimeError("youtube token 503: indisponible SECRET-YT-RT")
    return "SECRET-ACCESS-YT"


async def faux_tt_token():
    if ROUTE["mode"] == "reseau":
        raise ConnectionError("réseau coupé SECRET-TT-RT")
    if ROUTE["mode"] == "401":
        raise RuntimeError("tiktok token 401: invalid SECRET-TT-RT")
    if ROUTE["mode"] == "500":
        raise RuntimeError("tiktok token 500: boom SECRET-TT-CS")
    return "SECRET-ACCESS-TT"


def faux_x_me():
    if ROUTE["mode"] == "reseau":
        raise ConnectionError("réseau coupé SECRET-X-AT-3")
    if ROUTE["mode"] == "401":
        class Unauthorized(Exception): pass
        raise Unauthorized("401 Unauthorized SECRET-X-KEY-1 SECRET-X-AS-4")
    if ROUTE["mode"] == "500":
        class TwitterServerError(Exception): pass
        raise TwitterServerError("503 Service Unavailable SECRET-X-SEC-2")
    return "x-id-5", "xuser"


V._get = faux_get
V._x_me = faux_x_me
YP.access_token = faux_yt_token
TP.access_token = faux_tt_token


def verifier(p, mode="vert", **kw):
    from app.services import comptes
    poser(**kw)
    ROUTE["mode"] = mode
    APPELS.clear()
    with comptes.sous_compte(None):
        return asyncio.run(V.verifier_plateforme(p))


def sans_secret(r):
    t = json.dumps(r, ensure_ascii=False)
    return [s for s in TOUS_SECRETS if s in t]


ATTENDU = {"x": ("x-id-5", "@xuser"), "telegram": ("-100777", "Le Canal"), "youtube": ("UC123", "Ma Chaine"),
           "instagram": ("1784000", "@insta_nom"), "tiktok": ("oid-9", "Tik Nom")}

for p, (idd, nom) in ATTENDU.items():
    r = verifier(p)
    check(f"{p} vert : état, id et nom distants", r["etat"] == "vert" and r["id_distant"] == idd and r["nom_distant"] == nom, str(r))
    check(f"{p} vert : clés exactes du résultat", set(r) == {"etat", "raison", "id_distant", "nom_distant"} and isinstance(r["raison"], str), str(r))
    r = verifier(p, "401")
    check(f"{p} 401 : rouge, sans identité", r["etat"] == "rouge" and r["id_distant"] is None and r["nom_distant"] is None, str(r))
    check(f"{p} 401 : aucun secret dans la sortie (Review Focus 1)", not sans_secret(r), str(sans_secret(r)) + str(r))
    r = verifier(p, "500")
    check(f"{p} 500 : orange", r["etat"] == "orange" and r["id_distant"] is None, str(r))
    check(f"{p} 500 : aucun secret dans la sortie", not sans_secret(r), str(r))
    r = verifier(p, "reseau")
    check(f"{p} exception réseau : orange, ne remonte pas", r["etat"] == "orange", str(r))
    check(f"{p} exception réseau : aucun secret dans la sortie", not sans_secret(r), str(r))

# Review Focus 1 : la sortie ne contient jamais le jeton, même sous forme de morceau d'URL
r = verifier("telegram", "401")
check("RF1 Telegram : l'URL bot<jeton> du refus est expurgée", "SECRET-TG-123" not in json.dumps(r), str(r))
r = verifier("instagram", "401")
check("RF1 Instagram : la query access_token du refus est expurgée", "SECRET-IG-456" not in json.dumps(r), str(r))
r = verifier("telegram", "reseau")
check("RF1 Telegram : l'exception réseau (URL) est expurgée", "SECRET-TG-123" not in json.dumps(r), str(r))

# Review Focus 3 : Telegram ne reçoit aucun message
r = verifier("telegram")
urls = [u for u, _p, _h in APPELS]
check("RF3 Telegram : getMe puis getChat, rien d'autre", [u.rsplit("/", 1)[-1] for u in urls] == ["getMe", "getChat"], str(urls))
check("RF3 Telegram : aucune URL contenant /send", not any("/send" in u for u in urls))
check("RF3 Telegram : getChat porte le chat_id", APPELS[1][1].get("chat_id") == "-100777", str(APPELS[1]))
r = verifier("telegram", "chat404")
check("Telegram : chat introuvable = rouge", r["etat"] == "rouge" and "SECRET-TG-123" not in json.dumps(r), str(r))
r = verifier("telegram", "401")
check("Telegram : getMe refusé, getChat jamais appelé", [u.rsplit("/", 1)[-1] for u, _p, _h in APPELS] == ["getMe"], str(APPELS))
for p in ATTENDU:
    verifier(p)
    check(f"RF3 {p} : aucun appel /send", not any("/send" in u for u, _p, _h in APPELS))

# Telegram : nom = @username quand le chat n'a pas de titre
_old = V._get
async def _get_user(url, headers=None, params=None, *a, **k):
    if "getChat" in url:
        return 200, {"ok": True, "result": {"id": -100777, "username": "canal_pub"}}
    return await _old(url, headers, params)
V._get = _get_user
r = verifier("telegram")
check("Telegram : sans titre, nom = @username du chat", r["etat"] == "vert" and r["nom_distant"] == "@canal_pub", str(r))
V._get = _old

# champs manquants : orange, noms et jamais valeurs
r = verifier("telegram", TELEGRAM_CHAT_ID="")
check("manquants Telegram : orange + nom du champ", r["etat"] == "orange" and "TELEGRAM_CHAT_ID" in r["raison"]
      and r["raison"].startswith("identifiants incomplets"), str(r))
check("manquants Telegram : ni valeur ni appel réseau", "SECRET-TG-123" not in r["raison"] and not APPELS, str(r) + str(APPELS))
r = verifier("x", X_ACCESS_SECRET="", X_API_KEY="")
check("manquants X : les deux noms, pas les valeurs", r["etat"] == "orange" and "X_ACCESS_SECRET" in r["raison"]
      and "X_API_KEY" in r["raison"] and "SECRET-X" not in r["raison"], str(r))
r = verifier("instagram", IG_BUSINESS_ID="")
check("manquants Instagram : orange", r["etat"] == "orange" and "IG_BUSINESS_ID" in r["raison"], str(r))
r = verifier("youtube", YOUTUBE_REFRESH_TOKEN="")
check("manquants YouTube : orange", r["etat"] == "orange" and "YOUTUBE_REFRESH_TOKEN" in r["raison"], str(r))
r = verifier("tiktok", TIKTOK_CLIENT_KEY="")
check("manquants TikTok : orange", r["etat"] == "orange" and "TIKTOK_CLIENT_KEY" in r["raison"], str(r))

# TikTok non audité
r = verifier("tiktok", TIKTOK_AUDITED="")
check("TikTok non audité : orange, raison dite", r["etat"] == "orange" and "compte non audité : publication privée seulement" in r["raison"], str(r))
check("TikTok non audité : l'identité lue est gardée", r["id_distant"] == "oid-9" and r["nom_distant"] == "Tik Nom", str(r))
r = verifier("tiktok")
check("TikTok audité : vert", r["etat"] == "vert")
check("TikTok : champs demandés open_id,display_name", APPELS[0][1].get("fields") == "open_id,display_name"
      and APPELS[0][2].get("Authorization") == "Bearer SECRET-ACCESS-TT", str(APPELS[0]))

# YouTube : 200 sans chaîne, indéterminé
async def _get_vide(url, headers=None, params=None, *a, **k):
    return 200, {"items": []}
V._get = _get_vide
r = verifier("youtube")
check("YouTube : 200 sans chaîne = orange", r["etat"] == "orange" and r["id_distant"] is None, str(r))
V._get = _old

# plateforme inconnue : ne remonte pas
r = verifier("mastodon")
check("plateforme inconnue : orange, sans exception", r["etat"] == "orange", str(r))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
