# -*- coding: utf-8 -*-
"""t308 (26/10/2026) — Tâche 1 : vérification d'un compte de diffusion SANS publier (X, Telegram, YouTube, Instagram,
TikTok). ZÉRO réseau : `verif_canaux._get`, `verif_canaux._x_me` et les jetons OAuth sont remplacés.
Couvre : vert / rouge (401) / orange (500, puis exception réseau) par plateforme ; Review Focus 1 (aucun secret dans
une sortie) ; Review Focus 3 (Telegram n'appelle jamais /send*) ; champs manquants ; TikTok non audité.
Tâche 3 (section « récapitulatif ») : recap_espace.recapitulatif, route GET /api/espaces/{id}/recapitulatif, raisons d'`ignores`
de l'import traduites par L10.
Tâche 2 (section « enregistrée ») : noter_verification, canal_id, effacement par poser/supprimer (Review Focus 2), historique,
compte porté par le téléphone sans réseau ni secret (Review Focus 5), route POST /api/comptes/{id}/verifier (200, 404, 403).
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


_X_ME_REEL = V._x_me
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
    check(f"{p} vert : clés exactes du résultat", set(r) == {"etat", "raison", "id_distant", "nom_distant", "code"} and isinstance(r["raison"], str), str(r))
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

# --- Correctifs, tour 1 (26/10/2026) ---------------------------------------------------------------------------------
def avec_get(code, corps, p, **kw):
    anc = V._get
    async def g(url, headers=None, params=None, *a, **k):
        return code, corps
    V._get = g
    try:
        return verifier(p, **kw)
    finally:
        V._get = anc

# 1. Instagram : jeton Graph invalide = HTTP 400 + OAuthException (code 190, 102, 10, 200) -> rouge
for c in (190, 102, 10, 200):
    r = avec_get(400, {"error": {"message": "Error validating access token SECRET-IG-456", "type": "OAuthException", "code": c}}, "instagram")
    check(f"IG 400 OAuthException code {c} : rouge, sans secret", r["etat"] == "rouge" and not sans_secret(r), str(r))
r = avec_get(400, {"error": {"message": "Unsupported get request", "type": "GraphMethodException", "code": 100}}, "instagram")
check("IG 400 ordinaire (sans OAuthException) : reste orange", r["etat"] == "orange", str(r))
r = avec_get(400, "Bad request", "instagram")
check("IG 400 corps texte : reste orange", r["etat"] == "orange", str(r))

# 2. exceptions : classification étroite
def avec_tok(modul, exc, p):
    anc = modul.access_token
    async def t():
        raise exc
    modul.access_token = t
    try:
        return verifier(p)
    finally:
        modul.access_token = anc
r = avec_tok(YP, RuntimeError("youtube token 503: upstream 401 request id 401"), "youtube")
check("YouTube token 503 dont le corps contient 401 : orange", r["etat"] == "orange", str(r))
r = avec_tok(YP, RuntimeError("youtube token 400: invalid_grant"), "youtube")
check("YouTube token 400 invalid_grant : rouge", r["etat"] == "rouge", str(r))
r = avec_tok(YP, RuntimeError("youtube token 403: nope"), "youtube")
check("YouTube token 403 en tête : rouge", r["etat"] == "rouge", str(r))
r = avec_tok(TP, RuntimeError("tiktok token 500: boom 403"), "tiktok")
check("TikTok token 500 dont le corps contient 403 : orange", r["etat"] == "orange", str(r))
r = avec_tok(TP, RuntimeError("tiktok token 401: x"), "tiktok")
check("TikTok token 401 en tête : rouge", r["etat"] == "rouge", str(r))
r = avec_tok(TP, RuntimeError("erreur interne invalid_client"), "tiktok")
check("TikTok invalid_client : rouge", r["etat"] == "rouge", str(r))
r = avec_tok(YP, RuntimeError("le serveur dit forbidden 401 quelque part"), "youtube")
check("texte libre avec forbidden/401 hors motif : orange", r["etat"] == "orange", str(r))
def _x_texte():
    raise RuntimeError("503 gateway, ref 401 unauthorized")
V._x_me = _x_texte
r = verifier("x")
check("X : RuntimeError dont le texte contient 401/unauthorized : orange (par type, pas par texte)", r["etat"] == "orange", str(r))
def _x_forbidden():
    class Forbidden(Exception): pass
    raise Forbidden("403 Forbidden")
V._x_me = _x_forbidden
r = verifier("x")
check("4. X Forbidden : rouge, palier d'API évoqué", r["etat"] == "rouge" and "palier d'API X insuffisant" in r["raison"], str(r))
V._x_me = faux_x_me

# 3. YouTube 403 de quota : orange, dit quota
for rs in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
    r = avec_get(403, {"error": {"code": 403, "message": "q", "errors": [{"reason": rs}]}}, "youtube")
    check(f"YouTube 403 {rs} : orange, raison = quota", r["etat"] == "orange" and "quota" in r["raison"].lower(), str(r))
r = avec_get(403, {"error": {"code": 403, "message": "q", "errors": [{"reason": "forbidden"}]}}, "youtube")
check("YouTube 403 forbidden : reste rouge", r["etat"] == "rouge", str(r))

# 6. chemin réel asyncio.to_thread : le compte courant est visible dans le fil de _x_me
from app.services import comptes, marketing                         # noqa: E402
VU: list = []
class _FauxClient:
    def get_me(self):
        VU.append(comptes.courant())
        class D: id = 9; username = "reel"
        class M: data = D
        return M
_xc = marketing._x_client
marketing._x_client = lambda: _FauxClient()
V._x_me = _X_ME_REEL
_man = V._manquants
V._manquants = lambda p: []
cid = comptes.creer({"plateforme": "x", "libelle": "banc"})["id"]
with comptes.sous_compte(cid):
    r = asyncio.run(V.verifier_plateforme("x"))
check("to_thread réel : _x_me voit le compte posé par sous_compte", VU == [cid], f"{VU} vs {cid}")
check("to_thread réel : identité lue", r["etat"] == "vert" and r["id_distant"] == "9" and r["nom_distant"] == "@reel", str(r))
marketing._x_client = _xc
V._manquants = _man
V._x_me = faux_x_me

# ============ Tâche 2 : la vérification ENREGISTRÉE, le canal porté par le téléphone, la route ============
print("[enregistrée] noter_verification / canal_id / effacement / porté par le téléphone / route")
from app.services import fiche_client as FC, coffre                 # noqa: E402
import json as _json                                                # noqa: E402

def _brut():
    return _json.loads((_tmp / "espaces" / "comptes.json").read_text(encoding="utf-8"))

VERT = {"etat": "vert", "raison": "compte joint", "id_distant": "1784000", "nom_distant": "@insta_nom"}
ci = comptes.creer({"espace_id": "deepotus", "plateforme": "instagram", "libelle": "IG banc",
                    "valeurs": {"IG_ACCESS_TOKEN": "SECRET-IG-456", "IG_BUSINESS_ID": "1784000"}})["id"]
check("E0 un compte neuf : verification None, canal_id None",
      comptes.obtenir(ci)["verification"] is None and comptes.obtenir(ci)["canal_id"] is None, str(comptes.obtenir(ci)))
rg = comptes.noter_verification(ci, VERT)
check("E1 noter_verification rend la vérification rangée (6 clés, date ISO secondes)",
      set(rg) == {"etat", "raison", "code", "date", "id_distant", "nom_distant"} and rg["etat"] == "vert"
      and len(rg["date"]) == 19 and rg["date"][10] == "T", str(rg))
v = comptes.obtenir(ci)
check("E2 aller-retour : la vue porte verification et canal_id", v["verification"] == rg and v["canal_id"] == "instagram:1784000", str(v))
check("E3 rangée dans doc[verifications][cid] (clé de premier niveau)", _brut()["verifications"][ci] == rg)
check("E4 lister porte aussi les deux clés", [x for x in comptes.lister("deepotus") if x["id"] == ci][0]["canal_id"] == "instagram:1784000")
check("E5 canal_id rejette un id_distant hors CANAL_ID",
      comptes.canal_id({"plateforme": "instagram", "verification": {"id_distant": "a b/c"}}) is None
      and comptes.canal_id({"plateforme": "instagram", "verification": {"id_distant": ""}}) is None
      and comptes.canal_id({"plateforme": "instagram", "verification": {"id_distant": None}}) is None
      and comptes.canal_id({"plateforme": "instagram", "verification": None}) is None
      and comptes.canal_id({"plateforme": "instagram"}) is None)
check("E5b ... et accepte un id de chat Telegram négatif",
      comptes.canal_id({"plateforme": "telegram", "verification": {"id_distant": "-100777"}}) == "telegram:-100777")
rg2 = comptes.noter_verification(ci, {"etat": "rouge", "raison": "refusé", "id_distant": "x y", "nom_distant": None})
check("E5c id_distant invalide : rangé tel quel mais canal_id None", comptes.obtenir(ci)["canal_id"] is None and rg2["etat"] == "rouge")
comptes.noter_verification(ci, VERT)
try:
    comptes.noter_verification("c00000000", VERT); check("E6 compte inconnu : KeyError", False)
except KeyError:
    check("E6 compte inconnu : KeyError", True)
try:
    comptes.noter_verification("pas-un-compte", VERT); check("E6b id mal formé : KeyError", False)
except KeyError:
    check("E6b id mal formé : KeyError", True)
# Review Focus 2 : réécrire un champ (secret ou public) efface la vérification
comptes.poser(ci, {"IG_BUSINESS_ID": "1784001"})
check("E7 poser un champ public efface la vérification (vue « non vérifiée »)",
      comptes.obtenir(ci)["verification"] is None and comptes.obtenir(ci)["canal_id"] is None and ci not in _brut().get("verifications", {}))
comptes.noter_verification(ci, VERT)
comptes.poser(ci, {"IG_ACCESS_TOKEN": "SECRET-IG-NEUF"})
check("E8 poser un secret efface la vérification", comptes.obtenir(ci)["verification"] is None)
comptes.noter_verification(ci, VERT)
comptes.poser(ci, {})
check("E8b poser sans champ n'efface rien", comptes.obtenir(ci)["verification"] is not None)
comptes.modifier(ci, {"libelle": "Renommé"})
check("E8c renommer (libellé) n'efface pas la vérification", comptes.obtenir(ci)["verification"] is not None)
autre = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram"})["id"]
comptes.noter_verification(autre, {"etat": "orange", "raison": "r", "id_distant": None, "nom_distant": None})
comptes.poser(ci, {"IG_BUSINESS_ID": "9"})
check("E8d l'effacement est par compte : l'autre garde la sienne", comptes.obtenir(autre)["verification"]["etat"] == "orange")
comptes.noter_verification(ci, VERT)
comptes.supprimer(ci)
check("E9 supprimer retire la vérification du fichier", ci not in _brut().get("verifications", {}) and autre in _brut()["verifications"])
comptes.supprimer(autre)
_d = comptes._lire(); _d.pop("verifications", None); comptes._ecrire(_d)
check("E9b _lire tolère l'absence de la clé verifications", comptes._lire().get("comptes") is not None
      and comptes.lister("deepotus") is not None)
# historique : rangée et relue
poser(**S)
vh = comptes.noter_verification("historique-x", VERT)
check("E10 historique : la vérification est rangée et relue",
      [x for x in comptes.lister("deepotus") if x["id"] == "historique-x"][0]["verification"] == vh
      and comptes.obtenir("historique-x")["canal_id"] == "x:1784000" and _brut()["verifications"]["historique-x"] == vh)
check("E10b historique : un autre compte sans vérification porte verification None",
      comptes.obtenir("historique-telegram")["verification"] is None)
try:
    comptes.noter_verification("historique-inconnu", VERT); check("E10c historique d'une plateforme inconnue : KeyError", False)
except KeyError:
    check("E10c historique d'une plateforme inconnue : KeyError", True)
# porter_par_telephone : service seulement
cp = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Porté",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-PHONE", "TELEGRAM_CHAT_ID": "-100555"}})["id"]
check("E11 un compte non porté : pas de porte_par dans la vue", "porte_par" not in comptes.obtenir(cp))
DECL = {"appareil_id": "tel-1", "appareil_nom": "Pixel d'Oli", "verifie_le": "2026-10-20T09:30:00", "etat": "vert",
        "id_distant": "-100555"}
comptes.noter_verification(cp, {"etat": "rouge", "raison": "ancienne", "id_distant": None, "nom_distant": None})
vp = comptes.porter_par_telephone(cp, DECL)
check("E12 porter_par_telephone rend la vue avec porte_par", vp["id"] == cp and vp["porte_par"] == DECL, str(vp.get("porte_par")))
check("E12b la déclaration efface la vérification d'avant", vp["verification"] is None)
check("E12c la vue ne contient aucune valeur secrète", "SECRET-TG-PHONE" not in _json.dumps(comptes.obtenir(cp)))
for quoi, mauvais in (("appareil_id manquant", {**DECL, "appareil_id": ""}), ("appareil_nom non texte", {**DECL, "appareil_nom": 3}),
                      ("etat inconnu", {**DECL, "etat": "bleu"}), ("date illisible", {**DECL, "verifie_le": "hier"}),
                      ("champ étranger", {**DECL, "jeton": "x"}), ("pas un dict", ["x"]),
                      ("id_distant hors CANAL_ID", {**DECL, "id_distant": "a b"})):
    try:
        comptes.porter_par_telephone(cp, mauvais); check(f"E13 refus : {quoi}", False)
    except ValueError:
        check(f"E13 refus : {quoi}", True)
check("E13b ces refus n'ont rien changé", comptes.obtenir(cp)["porte_par"] == DECL)
try:
    comptes.porter_par_telephone("historique-telegram", DECL); check("E14 historique : CompteHistorique", False)
except comptes.CompteHistorique:
    check("E14 historique : CompteHistorique", True)
try:
    comptes.porter_par_telephone("c00000000", DECL); check("E14b compte inconnu : KeyError", False)
except KeyError:
    check("E14b compte inconnu : KeyError", True)
vn = comptes.porter_par_telephone(cp, {**DECL, "verifie_le": None, "etat": None, "id_distant": None})
check("E15 une déclaration « jamais vérifié » est acceptée", vn["porte_par"]["verifie_le"] is None and vn["porte_par"]["etat"] is None)
comptes.porter_par_telephone(cp, DECL)

# Review Focus 5 : un compte porté par le téléphone ne lit AUCUN secret et ne fait AUCUN appel réseau
def _x_interdit():
    raise AssertionError("APPEL RÉSEAU INTERDIT (compte porté par le téléphone)")
async def _get_interdit(*a, **k):
    raise AssertionError("APPEL RÉSEAU INTERDIT (compte porté par le téléphone)")
def _secret_interdit(nom):
    raise AssertionError(f"LECTURE DE SECRET INTERDITE : {nom}")
async def _vp_interdit(p):
    raise AssertionError("verifier_plateforme appelé pour un compte porté par le téléphone")
_g, _vs, _xm, _vp = V._get, comptes._valeur_secrete, V._x_me, V.verifier_plateforme

def verifier_sans_rien(cid_):
    V._get, V._x_me, V.verifier_plateforme = _get_interdit, _x_interdit, _vp_interdit
    comptes._valeur_secrete = _secret_interdit
    try:
        return asyncio.run(V.verifier(cid_)), ""
    except AssertionError as e:
        return None, str(e)
    finally:
        V._get, V._x_me, V.verifier_plateforme = _g, _xm, _vp
        comptes._valeur_secrete = _vs

vv, err = verifier_sans_rien(cp)
check("E16 porté par le téléphone : ni appel réseau ni lecture de secret", vv is not None, err)
vf = vv["verification"] if vv else {}
check("E16b la raison porte la date de la déclaration", "porté par le téléphone, vérifié le" in vf.get("raison", "")
      and "2026-10-20" in vf.get("raison", ""), str(vf))
check("E16c l'état est celui de la déclaration, l'id distant aussi, le canal_id suit",
      vf.get("etat") == "vert" and vf.get("id_distant") == "-100555" and vv["canal_id"] == "telegram:-100555", str(vv))
check("E16d la vérification est rangée (relue par obtenir)", comptes.obtenir(cp)["verification"] == vf)
comptes.porter_par_telephone(cp, {**DECL, "verifie_le": None, "etat": None, "id_distant": None})
vj, err = verifier_sans_rien(cp)
check("E17 jamais vérifié : orange, raison dite, aucun appel", vj is not None and vj["verification"]["etat"] == "orange"
      and vj["verification"]["raison"] == "porté par le téléphone, jamais vérifié" and vj["canal_id"] is None, f"{vj} {err}")
comptes.porter_par_telephone(cp, {**DECL, "etat": "rouge"})
vr, err = verifier_sans_rien(cp)
check("E17b déclaration rouge : l'état rouge est repris", vr is not None and vr["verification"]["etat"] == "rouge", f"{vr} {err}")
comptes.porter_par_telephone(cp, {**DECL, "etat": None})
vr, err = verifier_sans_rien(cp)
check("E17c vérifié mais sans état : orange (jamais vert par défaut)", vr is not None and vr["verification"]["etat"] == "orange", f"{vr} {err}")

# un compte ordinaire : verifier = sous_compte + verifier_plateforme, puis rangé
cn = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Ordinaire",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"}})["id"]
for k in S:
    setattr(settings, k, "")                 # les clés plates vidées : seul le compte parle
ROUTE["mode"] = "vert"; APPELS.clear()
V._get = faux_get
vo = asyncio.run(V.verifier(cn))
check("E18 compte ordinaire : vert, identité du compte, rangée, canal_id", vo["verification"]["etat"] == "vert"
      and vo["canal_id"] == "telegram:-100777" and comptes.obtenir(cn)["verification"] == vo["verification"], str(vo))
check("E18b aucun appel d'envoi", not any("/send" in u for u, _p, _h in APPELS))
ROUTE["mode"] = "401"
vo = asyncio.run(V.verifier(cn))
check("E19 refus : rouge rangé, aucun secret dans la vue ni dans la raison",
      vo["verification"]["etat"] == "rouge" and not any(s in _json.dumps(vo) for s in TOUS_SECRETS), str(vo)[:300])
ROUTE["mode"] = "vert"
try:
    asyncio.run(V.verifier("c00000000")); check("E20 compte inconnu : KeyError", False)
except KeyError:
    check("E20 compte inconnu : KeyError", True)
poser(**S)
vh = asyncio.run(V.verifier("historique-telegram"))
check("E21 historique : lit les clés plates, rangée sous historique-telegram",
      vh["verification"]["etat"] == "vert" and _brut()["verifications"]["historique-telegram"]["etat"] == "vert", str(vh)[:300])

print("[enregistrée] route POST /api/comptes/{id}/verifier")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _jeton_appareil as JA                                        # noqa: E402
for k in S:
    setattr(settings, k, "")
ROUTE["mode"] = "vert"
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    r = client.post(f"/api/comptes/{cn}/verifier")
    j = r.json() if r.status_code == 200 else {}
    check("R1 200 avec la vue du compte", r.status_code == 200 and j.get("compte", {}).get("id") == cn
          and j["compte"]["verification"]["etat"] == "vert" and j["compte"]["canal_id"] == "telegram:-100777", r.text[:300])
    check("R2 jamais de secret dans la réponse", not any(s in r.text for s in TOUS_SECRETS + ["SECRET-TG-PHONE"]))
    check("R3 compte inconnu : 404", client.post("/api/comptes/c00000000/verifier").status_code == 404)
    check("R3b id mal formé : 404", client.post("/api/comptes/nimporte/verifier").status_code == 404)
    ROUTE["mode"] = "401"
    r = client.post(f"/api/comptes/{cn}/verifier")
    check("R4 un refus distant reste un 200 (rouge dans la vue)", r.status_code == 200 and r.json()["compte"]["verification"]["etat"] == "rouge"
          and not any(s in r.text for s in TOUS_SECRETS), r.text[:200])
    ROUTE["mode"] = "vert"
    comptes.porter_par_telephone(cp, {**DECL, "verifie_le": None, "etat": None, "id_distant": None})
    r = client.post(f"/api/comptes/{cp}/verifier")
    check("R5 compte porté par le téléphone : 200, aucun appel", r.status_code == 200
          and r.json()["compte"]["verification"]["raison"] == "porté par le téléphone, jamais vérifié", r.text[:200])
    avant = comptes.obtenir(cn)["verification"]
    H = JA.entetes(app)
    lan = TestClient(app, client=("192.168.1.20", 50000))
    r = lan.post(f"/api/comptes/{cn}/verifier", headers=H)
    check("R6 appareil appairé : 403", r.status_code == 403, str(r.status_code))
    check("R6b ... et rien n'a changé", comptes.obtenir(cn)["verification"] == avant)
    check("R6c aucune route d'écriture « porté par » n'est exposée (service seulement)",
          client.post(f"/api/comptes/{cp}/porte_par", json=DECL).status_code in (404, 405)
          and client.post(f"/api/comptes/{cp}/porter", json=DECL).status_code in (404, 405))
V._get = _g


# ============ Correctifs, tour 1 : révision du compte, code de vérification, canal porté jamais publié par le PC ============
print("[correctifs] rev (vérification périmée), code, publish d'un canal porté, normalisation")
from app.services import publishers as PUB                          # noqa: E402

# 1. une vérification en vol qui finit APRÈS un poser ne range rien
poser(**S)
cr = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Course",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"}})["id"]
for k in S:
    setattr(settings, k, "")
ROUTE["mode"] = "vert"
rev0 = comptes.revision(cr)
check("C1 revision : un compte ordinaire a une révision (str), l'historique une chaîne vide avant toute péremption (t326)",
      isinstance(rev0, str) and comptes.revision("historique-telegram") == "", repr(rev0))
async def _get_qui_pose(url, headers=None, params=None, *a, **k):
    if "getMe" in url:
        comptes.poser(cr, {"TELEGRAM_CHAT_ID": "-100999"})      # l'utilisateur corrige le chat PENDANT la vérification
    return await faux_get(url, headers, params)
V._get = _get_qui_pose
vc = asyncio.run(V.verifier(cr))
V._get = faux_get
check("C2 poser pendant l'appel : rien n'est rangé, la vue reste « non vérifié »",
      vc["verification"] is None and vc["canal_id"] is None and cr not in _brut().get("verifications", {}), str(vc.get("verification")))
check("C2b poser a changé la révision", comptes.revision(cr) != rev0)
vc = asyncio.run(V.verifier(cr))
check("C3 une vérification normale range toujours", vc["verification"] is not None and vc["verification"]["etat"] == "vert")
rev1 = comptes.revision(cr)
comptes.poser(cr, {})
check("C3b poser sans champ ne change pas la révision", comptes.revision(cr) == rev1)
comptes.modifier(cr, {"libelle": "Renommé"})
check("C3c renommer ne change pas la révision", comptes.revision(cr) == rev1)
check("C4 noter_verification(rev périmée) rend None et ne range rien",
      comptes.noter_verification(cr, VERT, rev="ancienne") is None and comptes.obtenir(cr)["verification"]["etat"] == "vert"
      and comptes.obtenir(cr)["verification"]["raison"] != VERT["raison"])
check("C4b noter_verification(rev courante) range", comptes.noter_verification(cr, VERT, rev=rev1)["raison"] == VERT["raison"])
cq = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Course tel"})["id"]
async def _get_qui_declare(url, headers=None, params=None, *a, **k):
    comptes.porter_par_telephone(cq, DECL | {"id_distant": "-100555"})
    return await faux_get(url, headers, params)
comptes.poser(cq, {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"})
V._get = _get_qui_declare
vq = asyncio.run(V.verifier(cq))
V._get = faux_get
check("C5 porter_par_telephone pendant l'appel : rien n'est rangé non plus", vq["verification"] is None and "porte_par" in vq, str(vq.get("verification")))
check("C6 historique : pas de garde de révision, la vérification est rangée",
      (poser(**S), asyncio.run(V.verifier("historique-telegram")))[1]["verification"] is not None)
for k in S:
    setattr(settings, k, "")

# 2. un canal porté par le téléphone n'est JAMAIS publié par le PC (§11 bis), même avec un secret au même nom
from app.services import tiktok_publisher as _TP                    # noqa: E402
APPELS_PUB: list = []
async def _adaptateur_interdit(*a, **k):
    APPELS_PUB.append(a)
    raise AssertionError("adaptateur de publication appelé pour un canal porté par le téléphone")
_vsec, _reg = comptes._valeur_secrete, dict(PUB._REGISTRY)
PUB._REGISTRY["telegram"] = (lambda: True, _adaptateur_interdit)
comptes.porter_par_telephone(cq, DECL | {"id_distant": "-100555"})
comptes._valeur_secrete = _secret_interdit
try:
    rp = asyncio.run(PUB.publish("telegram", "bonjour", None, None, {}, compte=cq)); errp = ""
except AssertionError as e:
    rp, errp = None, str(e)
finally:
    comptes._valeur_secrete = _vsec
check("P1 publish(compte porté) : échec propre, ni secret lu ni adaptateur appelé",
      rp is not None and rp.ok is False and not APPELS_PUB, errp)
check("P1b la raison est dite", rp is not None and "canal porté par le téléphone : il publie depuis le téléphone" in rp.detail, str(rp))
comptes.poser(cq, {"TELEGRAM_CHAT_ID": "-100777"})
async def _adaptateur_ok(caption, video, image, meta):
    return PUB.PublishResult(True, "telegram: ok", "r1")
PUB._REGISTRY["telegram"] = (lambda: True, _adaptateur_ok)
cz = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Ordinaire pub"})["id"]
check("P2 un compte NON porté publie toujours (non-régression)", asyncio.run(PUB.publish("telegram", "bonjour", None, None, {}, compte=cz)).ok is True)
PUB._REGISTRY.clear(); PUB._REGISTRY.update(_reg)

# 3. code : jeu fermé, chaque branche
VUS: set = set()
def code_de(r, attendu, label):
    VUS.add(r.get("code"))
    check(f"K {label} -> {attendu}", r.get("code") == attendu and r.get("code") in V.CODES, f"{r.get('code')} {r.get('raison')}")
check("K0 CODES est un tuple sans doublon", isinstance(V.CODES, tuple) and len(set(V.CODES)) == len(V.CODES))
for p in ATTENDU:
    code_de(verifier(p), "ok", f"{p} vert")
    code_de(verifier(p, "401"), "refuse", f"{p} 401")
    code_de(verifier(p, "reseau"), "reseau", f"{p} réseau")
for p in ("telegram", "instagram"):
    code_de(verifier(p, "500"), "indetermine", f"{p} 500 (HTTP)")
code_de(verifier("youtube", "500"), "reseau", "youtube 500 (échange de jeton)")
code_de(verifier("x", "500"), "reseau", "x 500 (exception)")
code_de(verifier("tiktok", "500"), "reseau", "tiktok 500 (échange de jeton)")
code_de(verifier("telegram", "chat404"), "chat_introuvable", "telegram chat introuvable")
code_de(verifier("tiktok", TIKTOK_AUDITED=""), "non_audite", "tiktok non audité")
code_de(verifier("x", X_ACCESS_SECRET=""), "incomplet", "x incomplet")
code_de(verifier("nimporte"), "plateforme_inconnue", "plateforme inconnue")
_xf = V._x_me
V._x_me = _x_forbidden
code_de(verifier("x"), "refuse_palier", "x Forbidden")
V._x_me = _xf
_ft = _get_yt = None
async def _get_quota(url, headers=None, params=None, *a, **k):
    return 403, {"error": {"code": 403, "message": "q", "errors": [{"reason": "quotaExceeded"}]}}
V._get = _get_quota
code_de(verifier("youtube"), "quota", "youtube quota")
async def _get_http500(url, headers=None, params=None, *a, **k):
    return 500, {"error": "boom"}
V._get = _get_http500
code_de(verifier("youtube"), "indetermine", "youtube HTTP 500")
code_de(verifier("tiktok"), "indetermine", "tiktok HTTP 500")
async def _get_vide(url, headers=None, params=None, *a, **k):
    return 200, {"items": [], "data": {"user": {}}}
V._get = _get_vide
code_de(verifier("youtube"), "indetermine", "youtube sans chaîne")
V._get = faux_get
ROUTE["mode"] = "vert"
comptes.porter_par_telephone(cq, DECL | {"id_distant": "-100555"})
code_de(asyncio.run(V.verifier(cq))["verification"], "telephone_verifie", "téléphone vérifié")
comptes.porter_par_telephone(cq, DECL | {"verifie_le": None, "etat": None, "id_distant": None})
code_de(asyncio.run(V.verifier(cq))["verification"], "telephone_jamais", "téléphone jamais vérifié")
check("K1 noter_verification range le code (relu par la vue)", comptes.obtenir(cq)["verification"]["code"] == "telephone_jamais")
check("K2 chaque code du jeu est produit par un chemin testé", VUS == set(V.CODES), str(set(V.CODES) ^ VUS))
check("K3 la raison reste le détail français (non vide)", all(verifier("telegram", "401")["raison"] for _ in (0,)))

# 4. mineurs
vn = comptes.porter_par_telephone(cq, DECL | {"verifie_le": "2026-10-20T09:30:00.123456"})
check("M1 verifie_le est normalisé à la seconde", vn["porte_par"]["verifie_le"] == "2026-10-20T09:30:00", str(vn["porte_par"]))
vn = comptes.porter_par_telephone(cq, DECL | {"verifie_le": "2026-10-20"})
check("M1b une date seule devient ISO secondes", vn["porte_par"]["verifie_le"] == "2026-10-20T00:00:00", str(vn["porte_par"]))
comptes.porter_par_telephone(cq, DECL | {"verifie_le": None, "etat": "vert", "id_distant": "-100555"})
vm = asyncio.run(V.verifier(cq))["verification"]
check("M2 etat sans verifie_le : « jamais vérifié », orange", vm["etat"] == "orange" and vm["code"] == "telephone_jamais"
      and vm["raison"] == "porté par le téléphone, jamais vérifié", str(vm))

# ============ Tâche 3 : récapitulatif d'un espace (canaux, consentements) et raisons d'import en deux langues ============
print("[récapitulatif] canaux vérifiés, consentements, produit qui suit son client, route, ignores L10")
import io as _io, subprocess as _sp, zipfile as _zf                  # noqa: E402
from app.services import espaces as ESP, fiche_client as FC, espaces_paquet as PQ  # noqa: E402
from app.i18n import erreurs as ERR                                  # noqa: E402
try:
    from app.services import recap_espace as RE                      # noqa: E402
except ImportError as e:
    check("T3-0 module recap_espace présent", False, str(e))
    print(f"\n{ok} PASS / {fail} FAIL")
    sys.exit(1)

def _ok(cid, plat, id_distant, etat="vert"):
    comptes.noter_verification(cid, {"etat": etat, "raison": "banc", "id_distant": id_distant, "nom_distant": "n"})

marque = ESP.creer({"nom": "Marque Recap"})
cm = comptes.creer({"espace_id": marque["id"], "plateforme": "telegram", "libelle": "TG marque"})["id"]
_ok(cm, "telegram", "-100111")
rm = RE.recapitulatif(marque["id"])
check("S1 marque : pas de client, mode None, consentement sans_objet",
      rm["client_responsable"] is None and rm["mode_publication"] is None and rm["type"] == "marque"
      and [c["consentement"] for c in rm["canaux"]] == ["sans_objet"] and rm["manques"]["consentements"] == 0, str(rm))
check("S1b forme du canal (compte, plateforme, libellé, état, date, canal_id)",
      set(rm["canaux"][0]) == {"compte", "plateforme", "libelle", "etat", "code", "verifie_le", "canal_id", "consentement"}
      and rm["canaux"][0]["etat"] == "vert" and rm["canaux"][0]["canal_id"] == "telegram:-100111"
      and rm["canaux"][0]["libelle"] == "TG marque" and rm["canaux"][0]["verifie_le"], str(rm["canaux"]))

cl = ESP.creer({"nom": "Client Recap", "type": "client"})
FC.ecrire(cl["id"], {"societe": "Recap SARL", "mode_publication": "publie_en_son_nom"})
c_ok = comptes.creer({"espace_id": cl["id"], "plateforme": "telegram", "libelle": "TG couvert"})["id"]
c_sans = comptes.creer({"espace_id": cl["id"], "plateforme": "instagram", "libelle": "IG sans consentement"})["id"]
c_nv = comptes.creer({"espace_id": cl["id"], "plateforme": "youtube", "libelle": "YT jamais vérifié"})["id"]
_ok(c_ok, "telegram", "-100222")
_ok(c_sans, "instagram", "1784777", "orange")
FC.ajouter_consentement(cl["id"], "telegram:-100222", ["publier"], "ecrit")
rc = RE.recapitulatif(cl["id"])
par = {c["compte"]: c for c in rc["canaux"]}
check("S2 client : mode de la fiche, client_responsable = lui-même",
      rc["client_responsable"] == cl["id"] and rc["mode_publication"] == "publie_en_son_nom" and rc["type"] == "client", str(rc)[:300])
check("S3 canal vérifié avec consentement en cours : en_cours", par[c_ok]["consentement"] == "en_cours", str(par[c_ok]))
check("S4 canal vérifié sans consentement : manquant (orange reste orange)",
      par[c_sans]["consentement"] == "manquant" and par[c_sans]["etat"] == "orange", str(par[c_sans]))
check("S5 canal jamais vérifié : non_verifie ET consentement manquant (Review Focus 4)",
      par[c_nv]["etat"] == "non_verifie" and par[c_nv]["canal_id"] is None and par[c_nv]["consentement"] == "manquant"
      and par[c_nv]["verifie_le"] is None, str(par[c_nv]))
check("S5b manques : 1 non vérifié, 2 consentements", rc["manques"] == {"non_verifies": 1, "consentements": 2}, str(rc["manques"]))
FC.revoquer(cl["id"], "telegram:-100222")
rc2 = RE.recapitulatif(cl["id"])
check("S5c consentement révoqué : le canal repasse à manquant",
      {c["compte"]: c for c in rc2["canaux"]}[c_ok]["consentement"] == "manquant" and rc2["manques"]["consentements"] == 3)
FC.ajouter_consentement(cl["id"], "telegram:-100222", ["publier"], "ecrit")

# un compte dont la vérification est écrasée par poser() redevient non vérifié (Review Focus 2 vu du récapitulatif)
comptes.poser(c_ok, {"TELEGRAM_CHAT_ID": "-100999"})
rc3 = RE.recapitulatif(cl["id"])
check("S5d compte réécrit : non_verifie et manquant dans le récapitulatif",
      {c["compte"]: c for c in rc3["canaux"]}[c_ok]["etat"] == "non_verifie"
      and {c["compte"]: c for c in rc3["canaux"]}[c_ok]["consentement"] == "manquant")
_ok(c_ok, "telegram", "-100222")

pr = ESP.creer({"nom": "Produit Recap", "type": "produit", "parent": cl["id"]})
cpr = comptes.creer({"espace_id": pr["id"], "plateforme": "telegram", "libelle": "TG produit"})["id"]
cpr2 = comptes.creer({"espace_id": pr["id"], "plateforme": "instagram", "libelle": "IG produit"})["id"]
_ok(cpr, "telegram", "-100222")
_ok(cpr2, "instagram", "1784888")
rp = RE.recapitulatif(pr["id"])
pp = {c["compte"]: c for c in rp["canaux"]}
check("S6 produit : suit son client (mode, client_responsable, consentements du client)",
      rp["type"] == "produit" and rp["client_responsable"] == cl["id"] and rp["mode_publication"] == "publie_en_son_nom"
      and pp[cpr]["consentement"] == "en_cours" and pp[cpr2]["consentement"] == "manquant", str(rp)[:400])
pr_libre = ESP.creer({"nom": "Produit sous marque", "type": "produit", "parent": marque["id"]})
rpl = RE.recapitulatif(pr_libre["id"])
check("S6b produit d'une marque : sans client, sans_objet", rpl["client_responsable"] is None and rpl["mode_publication"] is None)
try:
    RE.recapitulatif("esp_inconnu00"); check("S7 espace inconnu : KeyError", False)
except KeyError:
    check("S7 espace inconnu : KeyError", True)
check("S7b espace Deepotus (historique) : lisible, sans client", RE.recapitulatif("deepotus")["client_responsable"] is None)
av = ESP.lire()["actif"]
RE.recapitulatif(cl["id"])
check("S8 lecture seule : l'espace actif n'a pas bougé", ESP.lire()["actif"] == av)

with TestClient(app, client=("127.0.0.1", 50000)) as client:
    r = client.get(f"/api/espaces/{cl['id']}/recapitulatif")
    check("S9 route 200 : le récapitulatif", r.status_code == 200 and r.json()["espace_id"] == cl["id"]
          and r.json()["manques"] == rc["manques"], r.text[:200])
    check("S9b aucun secret dans la réponse", not any(s in r.text for s in TOUS_SECRETS))
    check("S10 route 404 pour un espace inconnu", client.get("/api/espaces/esp_inconnu00/recapitulatif").status_code == 404)

    # ---- les raisons d'import, traduites à la sortie (même dictionnaire que les erreurs, L10) ----
    data, _n = PQ.exporter(cl["id"])
    zf = _zf.ZipFile(_io.BytesIO(data))
    paq = json.loads(zf.read("client.json"))
    paq.update(mode_publication="telepathie", consentements=[
        {"canal_id": "pas un canal", "permis": ["publier"], "date": "2026-10-25T10:00:00"},
        {"canal_id": "telegram:-100222", "permis": ["publier"], "date": "2026-10-25T10:00:00", "moyen": "telepathie"},
        {"canal_id": "instagram:5", "permis": ["publier"], "date": "2026-10-25T10:00:00", "moyen": "ecrit"},
        {"canal_id": "instagram:5", "permis": ["publier"], "date": "2026-10-26T10:00:00", "moyen": "ecrit"}],
        journal=[{"quand": "2026-10-25T10:00:00", "quoi": "consentement", "canal_id": "xx yy", "qui": "robot"},
                 {"quand": "", "quoi": "import", "canal_id": "", "qui": "client"}] + [
                 {"quand": "2026-10-25T10:00:00", "quoi": "import", "canal_id": "", "qui": "client"}] * (FC.MAX_JOURNAL + 1))
    tete = json.loads(zf.read("espace.json"))
    tete["espace"].update(type="client", parent="esp_zzzzzzzz")
    def _paquet(tete_, client_json):
        b = _io.BytesIO()
        with _zf.ZipFile(b, "w") as z:
            z.writestr("espace.json", json.dumps(tete_)); z.writestr("persona.json", zf.read("persona.json"))
            if client_json is not None: z.writestr("client.json", json.dumps(client_json))
        return b.getvalue()
    def _importer(octets, lang=None):
        h = {"Accept-Language": lang} if lang else {}
        return client.post("/api/espaces/importer", files={"file": ("p.zip", octets, "application/zip")}, headers=h)
    r_fr = _importer(_paquet(tete, paq))
    ig_fr = r_fr.json().get("ignores", [])
    r_en = _importer(_paquet(tete, paq), "en")
    ig_en = r_en.json().get("ignores", [])
    check("S11 import sans langue : raisons françaises inchangées", r_fr.status_code == 200 and len(ig_fr) >= 8
          and all(x.startswith(("client.json :", "parent ")) for x in ig_fr), str(ig_fr))
    check("S11b import en anglais : même nombre de raisons, aucune ne reste en français",
          r_en.status_code == 200 and len(ig_en) == len(ig_fr) and not any(
              ("remplacé" in x or "écart" in x or "invalide" in x or "retiré" in x or "tronqué" in x or "court déjà" in x)
              for x in ig_en), str(ig_en))
    # t308 relecture finale (26/10/2026) : S11c teste les chaînes anglaises EXACTES (plus de `and`/`or` sans parenthèses,
    # dont une branche ne pouvait jamais être vraie) ; S11c-mut prouve qu'il refuse une valeur interpolée perdue.
    def _s11c(lst):
        return ("client.json: consent no. 2: unknown means, replaced by “ecrit”" in lst
                and any(x.startswith("client.json: consent no. 3: ") and "(no. 4)" in x and "channel instagram:5," in x
                        for x in lst)
                and "client.json: unknown publication mode (telepathie), replaced by valide_par_client" in lst
                and any(x.startswith("parent esp_zzzzzzzz ") for x in lst))
    check("S11c les valeurs interpolées survivent à la traduction (n°, canal, mode, parent)", _s11c(ig_en), str(ig_en))
    check("S11c-mut ... et une valeur interpolée perdue le fait échouer (n°4 devenu n°3, canal perdu)",
          not _s11c([x.replace("(no. 4)", "(no. 3)") for x in ig_en])
          and not _s11c([x.replace("instagram:5", "{canal}") for x in ig_en])
          and not _s11c([x.replace("no. 2", "no. {i}") for x in ig_en]))
    check("S11d chaque raison traduite a son vis-à-vis français (même ordre, même valeurs)",
          all(any(t in e for t in ("telepathie", "esp_zzzzzzzz", "instagram:5", str(FC.MAX_JOURNAL)))
              == any(t in f for t in ("telepathie", "esp_zzzzzzzz", "instagram:5", str(FC.MAX_JOURNAL)))
              for e, f in zip(ig_en, ig_fr)), str(list(zip(ig_en, ig_fr))[:3]))
    tete2 = dict(tete); tete2["espace"] = dict(tete["espace"], type="marque", parent=None)
    r_m = _importer(_paquet(tete2, paq), "en")
    check("S12 fiche d'un paquet de marque : raison traduite", any("the space is not a client" in x for x in r_m.json()["ignores"]),
          str(r_m.json()["ignores"]))
    tete3 = dict(tete); tete3["espace"] = dict(tete["espace"], type="inconnu", parent=None)
    r_t = _importer(_paquet(tete3, None), "en")
    check("S12b type inconnu : raison traduite", any("unknown space type (inconnu)" in x for x in r_t.json()["ignores"]),
          str(r_t.json()["ignores"]))
    check("S13 une raison d'entrée ignorée (nom de fichier) passe telle quelle",
          ERR.texte("notes.txt", "en") == "notes.txt")
# le service lui-même garde le français (c'est la route qui traduit à la sortie)
check("S14 le service rend du français : traduire par ERR.texte donne l'anglais",
      all(ERR.texte(x, "en") != x for x in ig_fr), str([x for x in ig_fr if ERR.texte(x, "en") == x]))

# L10 : le générateur voit chaque raison (gabarit) et --check est propre
_py = sys.executable
_rc = _sp.run([_py, str(pathlib.Path(__file__).resolve().parent.parent.parent / "scripts" / "i18n_l10_erreurs.py"), "--check"],
              capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
check("S15 i18n_l10_erreurs.py --check propre (chaque raison d'import a sa traduction)", _rc.returncode == 0, _rc.stdout[-300:])


# ============ Relecture finale t308 (26/10/2026) : identité du canal préservée, reconnexion OAuth, coffre fermé ============
print("[relecture finale] I-1 reconnexion OAuth, I-2 identité gardée et coffre fermé, consentement par fiche_client")
from app.services import youtube_publisher as _YP2                  # noqa: E402
from urllib.parse import urlparse as _up, parse_qs as _pq           # noqa: E402
for k in S:
    setattr(settings, k, "")
ROUTE["mode"] = "vert"
V._get = faux_get

# I-1 : oublier_verification existe, retire la vérification ET change la révision
cf = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Oubli",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"}})["id"]
asyncio.run(V.verifier(cf))
rev_f = comptes.revision(cf)
check("F1 avant : vérifié vert, canal_id posé", comptes.obtenir(cf)["canal_id"] == "telegram:-100777")
_oubli = getattr(comptes, "oublier_verification", None)
if _oubli:
    _oubli(cf)
check("F2 oublier_verification : vérification None, canal_id None, révision changée",
      _oubli is not None and comptes.obtenir(cf)["verification"] is None and comptes.obtenir(cf)["canal_id"] is None
      and comptes.revision(cf) != rev_f and cf not in _brut().get("verifications", {}), str(comptes.obtenir(cf).get("verification")))
check("F2b noter_verification(rev d'avant l'oubli) ne range rien",
      comptes.noter_verification(cf, VERT, rev=rev_f) is None and comptes.obtenir(cf)["verification"] is None)
try:
    comptes.oublier_verification("c00000000"); check("F2c compte inconnu : KeyError", False)
except KeyError:
    check("F2c compte inconnu : KeyError", True)
except AttributeError:
    check("F2c compte inconnu : KeyError", False, "oublier_verification absente")

# I-1 : le rappel OAuth (« Connecter » de nouveau, autre chaîne) périme la vérification ; une vérification en vol est refusée
cy2 = comptes.creer({"espace_id": "deepotus", "plateforme": "youtube", "libelle": "YT reconnecté",
                     "valeurs": {"YOUTUBE_CLIENT_ID": "SECRET-YT-ID", "YOUTUBE_CLIENT_SECRET": "SECRET-YT-CS",
                                 "YOUTUBE_REFRESH_TOKEN": "SECRET-YT-RT"}})["id"]
vy = asyncio.run(V.verifier(cy2))
check("F3 avant le rappel : vert sur la chaîne A (youtube:UC123)", vy["canal_id"] == "youtube:UC123", str(vy.get("verification")))
async def _faux_echange(code, state):
    _YP2._VERIFS.pop(state, None)
    return "SECRET-YT-RT-NEUF"
_ech = _YP2.exchange_code
_YP2.exchange_code = _faux_echange
_rappel = {}
try:
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        d = client.get(f"/api/oauth/youtube/start?compte={cy2}", follow_redirects=False)
        etat_oauth = _pq(_up(d.headers.get("location", "")).query).get("state", [""])[0]
        # la vérification relève sa révision, PUIS le rappel OAuth arrive pendant l'appel réseau
        async def _get_rappel(url, headers=None, params=None, *a, **k):
            if not _rappel:
                _rappel["r"] = client.get(f"/api/oauth/youtube/callback?code=abc&state={etat_oauth}")
            return await faux_get(url, headers, params)
        V._get = _get_rappel
        vy2 = asyncio.run(V.verifier(cy2))
        V._get = faux_get
finally:
    _YP2.exchange_code = _ech
    V._get = faux_get
r_cb = _rappel.get("r")
check("F4 le rappel OAuth réussit (jeton gardé)", r_cb is not None and r_cb.status_code == 200
      and "SECRET" not in r_cb.text, str(r_cb.status_code if r_cb is not None else None))
with comptes.sous_compte(cy2):
    check("F4b le refresh token neuf est dans le compte", comptes.cle("YOUTUBE_REFRESH_TOKEN") == "SECRET-YT-RT-NEUF")
check("F5 la vérification en vol pendant le rappel est refusée par la garde de révision (rien de rangé)",
      vy2["verification"] is None, str(vy2.get("verification")))
check("F6 après le rappel : aucune vérification, canal_id None (l'ancienne chaîne est oubliée)",
      comptes.obtenir(cy2)["verification"] is None and comptes.obtenir(cy2)["canal_id"] is None, str(comptes.obtenir(cy2)))
# garder_secret seul (rotation TikTok PENDANT une vérification) ne périme rien
ct = comptes.creer({"espace_id": "deepotus", "plateforme": "tiktok", "libelle": "TT rotation",
                    "valeurs": {"TIKTOK_CLIENT_KEY": "ck-pub", "TIKTOK_CLIENT_SECRET": "SECRET-TT-CS",
                                "TIKTOK_REFRESH_TOKEN": "SECRET-TT-RT", "TIKTOK_AUDITED": "1"}})["id"]
async def _tt_qui_tourne():
    comptes.garder_secret("TIKTOK_REFRESH_TOKEN", "SECRET-TT-RT-TOURNE")
    return "SECRET-ACCESS-TT"
_ttk = TP.access_token
TP.access_token = _tt_qui_tourne
try:
    vt = asyncio.run(V.verifier(ct))
finally:
    TP.access_token = _ttk
check("F7 la rotation du refresh token TikTok pendant la vérification ne la périme pas (vert rangé)",
      (vt.get("verification") or {}).get("etat") == "vert" and vt["canal_id"] == "tiktok:oid-9", str(vt.get("verification")))

# I-2 (b) : un résultat SANS id_distant garde l'identité connue (même révision) ; un refus aussi
ck = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Identité gardée",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"}})["id"]
v0 = asyncio.run(V.verifier(ck))
check("G0 vert : canal_id et nom distant posés", v0["canal_id"] == "telegram:-100777"
      and v0["verification"]["nom_distant"] == "Le Canal", str(v0["verification"]))
for mode, etat_att, code_att in (("reseau", "orange", "reseau"), ("500", "orange", "indetermine"), ("401", "rouge", "refuse")):
    ROUTE["mode"] = mode
    vg = asyncio.run(V.verifier(ck))
    ver = vg["verification"] or {}
    check(f"G1 {mode} : état {etat_att}, code {code_att}, raison neuve ; id et nom distants GARDÉS, canal_id inchangé",
          ver.get("etat") == etat_att and ver.get("code") == code_att and ver.get("raison") != v0["verification"]["raison"]
          and ver.get("id_distant") == "-100777" and ver.get("nom_distant") == "Le Canal" and vg["canal_id"] == "telegram:-100777",
          str(ver))
ROUTE["mode"] = "vert"
for label, corps_get in (("quota", _get_quota), ("429", None)):
    async def _g429(url, headers=None, params=None, *a, **k):
        return 429, {"error": "trop de requêtes"}
    V._get = corps_get or _g429
    vq2 = asyncio.run(V.verifier(cy2 if label == "quota" else ck))
    V._get = faux_get
    if label == "quota":
        check("G2 quota YouTube sans identité connue : orange quota, canal_id reste None (rien à garder)",
              vq2["verification"]["code"] == "quota" and vq2["canal_id"] is None, str(vq2["verification"]))
    else:
        check("G2b 429 : orange, canal_id gardé", vq2["verification"]["etat"] == "orange" and vq2["canal_id"] == "telegram:-100777",
              str(vq2["verification"]))
asyncio.run(V.verifier(cy2))
V._get = _get_quota
vq3 = asyncio.run(V.verifier(cy2))
V._get = faux_get
check("G2c quota YouTube après un vert : orange quota, la chaîne connue reste", vq3["verification"]["code"] == "quota"
      and vq3["canal_id"] == "youtube:UC123" and vq3["verification"]["nom_distant"] == "Ma Chaine", str(vq3["verification"]))
# un résultat AVEC une identité la remplace ; poser / porter / oublier / supprimer l'effacent
gv = comptes.noter_verification(ck, {"etat": "vert", "raison": "autre chat", "id_distant": "-100888", "nom_distant": "Autre"})
check("G3 un vert avec une autre identité la remplace", gv["id_distant"] == "-100888" and comptes.obtenir(ck)["canal_id"] == "telegram:-100888")
comptes.poser(ck, {"TELEGRAM_CHAT_ID": "-100777"})
ROUTE["mode"] = "reseau"
vp = asyncio.run(V.verifier(ck))
ROUTE["mode"] = "vert"
check("G4 après poser, un orange sans identité ne ressuscite pas l'ancienne", vp["canal_id"] is None
      and vp["verification"]["id_distant"] is None, str(vp["verification"]))
asyncio.run(V.verifier(ck))
comptes.oublier_verification(ck)
check("G5 oublier_verification efface l'identité gardée", comptes.obtenir(ck)["canal_id"] is None)

# canal porté par le téléphone jamais vérifié : le récapitulatif porte le CODE (l'écran dit « jamais vérifié », pas « vérifié le »)
ctj = comptes.creer({"espace_id": marque["id"], "plateforme": "telegram", "libelle": "TG porté"})["id"]
comptes.porter_par_telephone(ctj, DECL | {"verifie_le": None, "etat": None, "id_distant": None})
asyncio.run(V.verifier(ctj))
ctj_r = {c["compte"]: c for c in RE.recapitulatif(marque["id"])["canaux"]}[ctj]
check("H0 récapitulatif : un canal porté jamais vérifié porte code telephone_jamais",
      ctj_r.get("code") == "telephone_jamais" and ctj_r["etat"] == "orange", str(ctj_r))
check("H0b un canal jamais vérifié du tout : code None",
      {c["compte"]: c for c in RE.recapitulatif(cl["id"])["canaux"]}[c_nv].get("code", "absent") is None)

# consentement : UNE lecture de fiche_client.consentements_en_cours (source unique de « en cours »)
_cec, _n_cec = FC.consentements_en_cours, []
def _cec_compte(eid):
    _n_cec.append(eid)
    return _cec(eid)
FC.consentements_en_cours = _cec_compte
try:
    rcc = RE.recapitulatif(cl["id"])
    check("H1 le récapitulatif lit fiche_client.consentements_en_cours UNE fois (3 canaux)",
          _n_cec == [cl["id"]] and len(rcc["canaux"]) == 3, str(_n_cec))
    FC.consentements_en_cours = lambda eid: []         # une règle future (échéance…) qui ne garde aucun consentement
    rcv = RE.recapitulatif(cl["id"])
    check("H2 ... et suit ce qu'elle rend (aucun en cours -> tous manquants)",
          all(c["consentement"] == "manquant" for c in rcv["canaux"]), str([c["consentement"] for c in rcv["canaux"]]))
finally:
    FC.consentements_en_cours = _cec

# I-2 (a) : coffre FERMÉ -> 409, rien n'est rangé, jamais « identifiants incomplets » (en dernier : le coffre reste posé)
MDP = "banc-coffre-t308"
coffre.poser(MDP, {})
coffre.ouvrir(MDP)
cv = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Coffre",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"}})["id"]
vv = asyncio.run(V.verifier(cv))
check("V0 coffre ouvert : vert", (vv["verification"] or {}).get("etat") == "vert", str(vv.get("verification")))
avant_v = comptes.obtenir(cv)["verification"]
coffre.fermer()
check("V0b coffre fermé : verrouillé, le secret ne se lit plus", coffre.verrouille() and not comptes.obtenir(cv)["champs"][0]["pose"],
      str(comptes.obtenir(cv)["champs"]))
APPELS.clear()
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    r = client.post(f"/api/comptes/{cv}/verifier")
    r_en = client.post(f"/api/comptes/{cv}/verifier", headers={"Accept-Language": "en"})
check("V1 POST /verifier coffre fermé : 409, message du coffre verrouillé existant", r.status_code == 409
      and r.json().get("detail", "").startswith("Coffre verrouillé : "), f"{r.status_code} {r.text[:200]}")
check("V1b ... en anglais aussi (409, « Vault locked »)", r_en.status_code == 409 and r_en.json().get("detail", "").startswith("Vault locked"),
      r_en.text[:200])
check("V2 rien n'est rangé : la vérification d'avant reste (même date, même état, même identité)",
      comptes.obtenir(cv)["verification"] == avant_v and comptes.obtenir(cv)["canal_id"] == "telegram:-100777")
check("V3 aucun appel réseau ni « identifiants incomplets »", not APPELS and "incomplet" not in r.text, r.text[:200])
try:
    asyncio.run(V.verifier(cv)); check("V4 le service lève CoffreVerrouille", False)
except coffre.CoffreVerrouille:
    check("V4 le service lève CoffreVerrouille", True)
# un champ PUBLIC vide reste « incomplet » même coffre fermé (le coffre n'y est pour rien)
cw = comptes.creer({"espace_id": "deepotus", "plateforme": "instagram", "libelle": "Public vide"})["id"]
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    rw = client.post(f"/api/comptes/{cw}/verifier")
check("V5 coffre fermé, aucun secret posé non plus : 409 (le secret requis peut être au coffre)", rw.status_code == 409, rw.text[:200])
coffre.ouvrir(MDP)
cpub = comptes.creer({"espace_id": "deepotus", "plateforme": "instagram", "libelle": "IG sans id",
                      "valeurs": {"IG_ACCESS_TOKEN": "SECRET-IG-456"}})["id"]
vo =asyncio.run(V.verifier(cpub))
check("V7 coffre ouvert, champ public manquant : orange « incomplet » (le vrai manque)",
      vo["verification"]["code"] == "incomplet" and "IG_BUSINESS_ID" in vo["verification"]["raison"], str(vo["verification"]))

# ============ t326 (26/10/2026) : révision des historiques, vérification écartée signalée, date du téléphone ============
print("[t326] T1 révision de l'historique, ecartee, date du téléphone")
from datetime import datetime as _dt                                # noqa: E402
poser(**S)
ROUTE["mode"] = "vert"
V._get = faux_get
r_av = comptes.revision("historique-telegram")
comptes.perimer_historiques(["TELEGRAM_BOT_TOKEN"])
r_ap = comptes.revision("historique-telegram")
check("T1a révision de l'historique : \"\" avant, une chaîne différente après perimer_historiques",
      r_av == "" and isinstance(r_ap, str) and r_ap != "" and r_ap != r_av, f"{r_av!r} {r_ap!r}")
try:
    comptes.revision("historique-inconnue"); check("T1a2 historique d'une plateforme inconnue : KeyError", False)
except KeyError:
    check("T1a2 historique d'une plateforme inconnue : KeyError", True)

asyncio.run(V.verifier("historique-telegram"))
vb0 = comptes.obtenir("historique-telegram")
check("T1b0 avant : historique vérifié vert avec identité", vb0["verification"]["etat"] == "vert" and vb0["canal_id"], str(vb0.get("canal_id")))
check("T1b perimer_historiques([CHAT_ID]) périme l'historique : vérification et canal_id retirés",
      comptes.perimer_historiques(["TELEGRAM_CHAT_ID"]) == ["historique-telegram"]
      and comptes.obtenir("historique-telegram")["verification"] is None and comptes.obtenir("historique-telegram")["canal_id"] is None)

_fc = comptes._fichier()
avant_txt = _fc.read_bytes()
_mt = _fc.stat().st_mtime_ns
check("T1c nom inconnu ou d'un autre service : rien de périmé, fichier non réécrit",
      comptes.perimer_historiques(["OPENAI_API_KEY", "INCONNU"]) == []
      and _fc.read_bytes() == avant_txt and _fc.stat().st_mtime_ns == _mt)

rev_h = comptes.revision("historique-telegram")
async def _get_qui_perime(url, headers=None, params=None, *a, **k):
    if "getMe" in url:
        comptes.perimer_historiques(["TELEGRAM_CHAT_ID"])     # les clés plates changent PENDANT la vérification
    return await faux_get(url, headers, params)
V._get = _get_qui_perime
vd = asyncio.run(V.verifier("historique-telegram"))
V._get = faux_get
check("T1d historique périmé en vol : rien n'est rangé, vue « non vérifié », ecartee",
      vd["verification"] is None and "historique-telegram" not in _brut().get("verifications", {}) and vd.get("ecartee") is True
      and comptes.revision("historique-telegram") != rev_h, str(vd.get("verification")))

ce = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Écartée",
                    "valeurs": {"TELEGRAM_BOT_TOKEN": "SECRET-TG-123", "TELEGRAM_CHAT_ID": "-100777"}})["id"]
async def _get_qui_pose2(url, headers=None, params=None, *a, **k):
    if "getMe" in url:
        comptes.poser(ce, {"TELEGRAM_CHAT_ID": "-100999"})
    return await faux_get(url, headers, params)
V._get = _get_qui_pose2
ve = asyncio.run(V.verifier(ce))
V._get = faux_get
check("T1e compte d'espace modifié en vol : ecartee True, rien rangé", ve.get("ecartee") is True and ve["verification"] is None)
ve2 = asyncio.run(V.verifier(ce))
check("T1e2 vérification normale : pas de clé ecartee", ve2["verification"] is not None and "ecartee" not in ve2)

ct = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Tel date"})["id"]
comptes.porter_par_telephone(ct, {**DECL, "verifie_le": "2026-10-20T08:15:00", "etat": "vert", "id_distant": "123"})
vt = asyncio.run(V.verifier(ct))
check("T1f compte porté par le téléphone : la date rangée est celle de l'appareil",
      vt["verification"]["date"] == "2026-10-20T08:15:00", str(vt["verification"]))

cg = comptes.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Date illisible"})["id"]
comptes.noter_verification(cg, {"etat": "vert", "date": "pas une date"})
dg = comptes.obtenir(cg)["verification"]["date"]
check("T1g date illisible : maintenant", dg.startswith(_dt.now().date().isoformat()), dg)
comptes.noter_verification(cg, {"etat": "vert", "date": "2026-01-02T03:04:05"})
check("T1g2 date ISO lisible : gardée", comptes.obtenir(cg)["verification"]["date"] == "2026-01-02T03:04:05")

# ============ t326 (26/10/2026) T2 : set_key périme l'historique, rappel OAuth sans 500, CoffreVerrouille traduit ============
print("[t326] T2 routes et L10")
import subprocess as _sp2                                           # noqa: E402
poser()
V._get = faux_get
asyncio.run(V.verifier("historique-telegram"))
check("T2a0 avant : historique telegram vérifié", comptes.obtenir("historique-telegram")["verification"] is not None)
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    r2a = client.post("/api/settings/keys", json={"name": "TELEGRAM_CHAT_ID", "value": "-1001"})
check("T2a POST /settings/keys TELEGRAM_CHAT_ID : 200 et l'historique telegram n'est plus vérifié",
      r2a.status_code == 200 and comptes.obtenir("historique-telegram")["verification"] is None
      and "historique-telegram" not in _brut().get("verifications", {}), f"{r2a.status_code} {r2a.text[:150]}")

poser()
asyncio.run(V.verifier("historique-telegram"))
v_avant = comptes.obtenir("historique-telegram")["verification"]
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    r2b = client.post("/api/settings/keys", json={"name": "PAS_AUTORISEE", "value": "x"})
    r2b_mix = client.post("/api/settings/keys", json={"entries": [{"name": "TELEGRAM_CHAT_ID", "value": "-5"},
                                                                    {"name": "PAS_AUTORISEE", "value": "x"}]})
check("T2b clé refusée (400) : la vérification est gardée",
      r2b.status_code == 400 and r2b_mix.status_code == 400 and comptes.obtenir("historique-telegram")["verification"] == v_avant,
      f"{r2b.status_code} {r2b_mix.status_code}")
coffre.fermer()
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    r2b2 = client.post("/api/settings/keys", json={"entries": [{"name": "TELEGRAM_CHAT_ID", "value": "-6"},
                                                                 {"name": "TELEGRAM_BOT_TOKEN", "value": "SECRET-TG-NEUF"}]})
check("T2b2 coffre posé fermé + secret (409) : la vérification est gardée",
      r2b2.status_code == 409 and comptes.obtenir("historique-telegram")["verification"] == v_avant, f"{r2b2.status_code} {r2b2.text[:150]}")
coffre.ouvrir(MDP)

# T2c : le rappel OAuth ne renvoie jamais 500 si l'oubli de la vérification échoue
cy3 = comptes.creer({"espace_id": "deepotus", "plateforme": "youtube", "libelle": "YT oubli KO",
                     "valeurs": {"YOUTUBE_CLIENT_ID": "SECRET-YT-ID", "YOUTUBE_CLIENT_SECRET": "SECRET-YT-CS",
                                 "YOUTUBE_REFRESH_TOKEN": "SECRET-YT-RT"}})["id"]
_ech3, _oubli3 = _YP2.exchange_code, comptes.oublier_verification
_YP2.exchange_code = _faux_echange
def _oubli_en_panne(cid):
    raise OSError("disque plein SECRET-MSG")
comptes.oublier_verification = _oubli_en_panne
_journal = []
_idj = logger.add(lambda m: _journal.append(str(m)), level="WARNING")
try:
    with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as client:
        d3 = client.get(f"/api/oauth/youtube/start?compte={cy3}", follow_redirects=False)
        st3 = _pq(_up(d3.headers.get("location", "")).query).get("state", [""])[0]
        r2c = client.get(f"/api/oauth/youtube/callback?code=abc&state={st3}")
finally:
    _YP2.exchange_code = _ech3
    comptes.oublier_verification = _oubli3
    logger.remove(_idj)
with comptes.sous_compte(cy3):
    jeton3 = comptes.cle("YOUTUBE_REFRESH_TOKEN")
check("T2c oubli en panne : 200 (pas de 500), page « revérifiez », jeton rangé",
      r2c.status_code == 200 and "revérifiez" in r2c.text and jeton3 == "SECRET-YT-RT-NEUF", f"{r2c.status_code} {r2c.text[:300]}")
check("T2c2 journal : le type de l'exception seulement, jamais son message ni un secret",
      any("OSError" in j for j in _journal) and not any("disque plein" in j or "SECRET" in j for j in _journal)
      and "SECRET" not in r2c.text and "disque plein" not in r2c.text, str(_journal)[:200])

# T2c3 : compte supprimé pendant la connexion : toujours la page 404
cy4 = comptes.creer({"espace_id": "deepotus", "plateforme": "youtube", "libelle": "YT supprimé",
                     "valeurs": {"YOUTUBE_CLIENT_ID": "SECRET-YT-ID", "YOUTUBE_CLIENT_SECRET": "SECRET-YT-CS"}})["id"]
_YP2.exchange_code = _faux_echange
try:
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        d4 = client.get(f"/api/oauth/youtube/start?compte={cy4}", follow_redirects=False)
        st4 = _pq(_up(d4.headers.get("location", "")).query).get("state", [""])[0]
        comptes.supprimer(cy4)
        r2c3 = client.get(f"/api/oauth/youtube/callback?code=abc&state={st4}")
finally:
    _YP2.exchange_code = _ech3
check("T2c3 compte supprimé : la page 404 existante", r2c3.status_code == 404, f"{r2c3.status_code} {r2c3.text[:150]}")

# T2d : L10, « Coffre verrouillé : le coffre est fermé » traduit
_rc = _sp2.run([sys.executable, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "i18n_l10_erreurs.py"), "--check"],
               capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
check("T2d i18n_l10_erreurs.py --check : code 0", _rc.returncode == 0, (_rc.stdout + _rc.stderr)[-300:])
check("T2d2 « Coffre verrouillé : le coffre est fermé » -> EN",
      ERR.texte("Coffre verrouillé : le coffre est fermé", "en") == "Vault locked: the vault is closed",
      ERR.texte("Coffre verrouillé : le coffre est fermé", "en"))

coffre.fermer()
coffre.FICHIER.unlink()

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
