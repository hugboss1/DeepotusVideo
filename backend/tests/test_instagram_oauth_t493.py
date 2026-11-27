# -*- coding: utf-8 -*-
"""t493 (G3, 26/11/2026) — Instagram : connexion OAuth « Instagram Login », scopes, jeton longue durée au coffre.

Préparé SANS la décision D7 : tout est INERTE tant que l'utilisateur n'a pas saisi IG_APP_ID et IG_APP_SECRET ; le
collage manuel (IG_ACCESS_TOKEN + IG_BUSINESS_ID, comptes.PLATEFORMES["instagram"], OAuth=False) ne bouge pas.
Aucun réseau : chaque appel à Meta passe par un faux client HTTP qui les relève.

[1] inerte sans application : rien ne part, le collage manuel est intact
[2] démarrage : URL d'autorisation, quatre scopes, state, aucun secret ; coffre exigé
[3] state : inconnu, expiré, déjà utilisé, refus de l'utilisateur -> refusé sans appel
[4] retour : échange du code, jeton longue durée AU COFFRE, date d'expiration, vérification du compte, compte d'espace
[5] jamais un secret dans un journal, une réponse, une URL rendue ou un fichier hors coffre
[6] renouvellement daté (24 h d'âge, 10 jours avant l'échéance), branché sur la passe quotidienne du Planificateur
[7] hôte : graph.instagram.com pour un jeton IGAA, graph.facebook.com pour EAA (publication, vérification)
[8] convention t520 : liste blanche, rubrique, coffre, console, guide daté, test sans appel
[9] écran : module partagé, maillon dziglogin, son inverse, traductions
Run (depuis backend/) : & $PY tests/test_instagram_oauth_t493.py"""
import asyncio, json, os, pathlib, re, subprocess, sys, tempfile, time
from urllib.parse import parse_qs, urlsplit
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt493_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.pop("DEEPOTUS_HOSTNAME", None)
for k in ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID", "IG_APP_ID", "IG_APP_SECRET", "IG_OAUTH_REDIRECT"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
JOURNAL: list = []
logger.add(lambda m: JOURNAL.append(str(m)), level="DEBUG")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:400]}")


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.config import settings                                      # noqa: E402
from app.api.routes import _ALLOWED_ENV_KEYS                         # noqa: E402
from app.api import settings_routes as SR                            # noqa: E402
from app.services import appairage as APR, coffre as CF, comptes as CPT, diagnostic as D   # noqa: E402
from app.services import guides_fournisseurs as G, cles_a_chaud as CAC, verif_canaux as V  # noqa: E402
from app.services import instagram_publisher as IP                   # noqa: E402
from app.services import instagram_oauth as IO                       # noqa: E402

APP_ID = "1234567890123456"
APP_SECRET = "SECRET-APP-493-zz"
CODE = "AQBcode-493-xyz"
COURT = "IGAAcourt-SECRET-493"
LONG = "IGAAlong-SECRET-493"
NEUF = "IGAAneuf-SECRET-493"
IG_ID = "17841400000000493"
SECRETS = (APP_SECRET, CODE, COURT, LONG, NEUF)

APPELS: list = []
REPONSES: dict = {}


class _R:
    def __init__(self, code, corps):
        self.status_code, self._c = code, corps
        self.text = json.dumps(corps)

    def json(self):
        return self._c


class _Faux:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

    async def _rep(self, meth, url, **k):
        APPELS.append((meth, url, k))
        for debut, f in REPONSES.items():
            if url.startswith(debut):
                return f(meth, url, k)
        return _R(599, {"error": {"message": "url inattendue"}})

    async def get(self, url, **k): return await self._rep("GET", url, **k)
    async def post(self, url, **k): return await self._rep("POST", url, **k)


IO._client = lambda *a, **k: _Faux()
VAPPELS: list = []


async def faux_vget(url, headers=None, params=None):
    VAPPELS.append((url, dict(params or {})))
    return 200, {"id": IG_ID, "username": "deepotus_ai"}


V._get = faux_vget
c = TestClient(app, client=("127.0.0.1", 50000))

print("[1] inerte sans application Meta")
check("1.1 non configuré sans IG_APP_ID ni IG_APP_SECRET", IO.configure() is False)
try:
    IO.demarrer(None)
    check("1.2 démarrer refuse sans application", False)
except IO.RefusIG as e:
    check("1.2 démarrer refuse sans application (400, nomme IG_APP_ID)", e.statut == 400 and "IG_APP_ID" in str(e), e)
r = c.post("/api/oauth/instagram/demarrer", json={})
check("1.3 route démarrer : 400, aucun appel", r.status_code == 400 and not APPELS, (r.status_code, r.text[:200]))
r = c.post("/api/oauth/instagram/demarrer", json={}, headers={"Accept-Language": "en"})
check("1.4 refus en anglais", r.status_code == 400 and "IG_APP_ID" in r.text and "Settings" in r.text, r.text[:200])
e = c.get("/api/oauth/instagram/etat").json()
check("1.5 état : configure False, adresse de retour par défaut, quatre scopes",
      e.get("configure") is False and e.get("redirect_uri") == "http://127.0.0.1:8765/api/oauth/instagram/callback"
      and e.get("scopes") == list(IO.SCOPES), e)
n = len(APPELS)
r = asyncio.run(IO.renouveler_dus())
check("1.6 renouvellement sans rien de relié : rien, aucun appel", r == [] and len(APPELS) == n, r)
lib, champs, req, oauth = CPT.PLATEFORMES["instagram"]
check("1.7 collage manuel intact : PLATEFORMES instagram (jeton secret, id public, OAuth False)",
      champs == [("IG_ACCESS_TOKEN", True), ("IG_BUSINESS_ID", False)] and req == ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID")
      and oauth is False, CPT.PLATEFORMES["instagram"])
CAC.appliquer({"IG_ACCESS_TOKEN": "EAAcolle-manuel", "IG_BUSINESS_ID": "17841400000000001"})
check("1.8 collage manuel : has_instagram vrai sans application", settings.has_instagram and IP.available())
CAC.appliquer({"IG_ACCESS_TOKEN": "", "IG_BUSINESS_ID": ""})
check("1.9 IG_SCOPES : les quatre de la fiche, rien de plus", IO.SCOPES == (
    "instagram_business_basic", "instagram_business_content_publish", "instagram_business_manage_comments",
    "instagram_business_manage_insights"), IO.SCOPES)

print("[2] démarrage")
CAC.appliquer({"IG_APP_ID": APP_ID})
os.environ["IG_APP_SECRET"] = ""
check("2.0 l'ID seul ne suffit pas", IO.configure() is False)
# pas de coffre posé : le secret de l'application irait au .env — le banc le pose en mémoire pour tester le refus
CAC.appliquer({"IG_APP_SECRET": APP_SECRET})
check("2.1 configuré avec ID et secret", IO.configure() is True)
try:
    IO.demarrer(None)
    check("2.2 sans coffre ouvert : refus 409", False)
except IO.RefusIG as e:
    check("2.2 sans coffre ouvert : refus 409 (le jeton ne serait pas au coffre)", e.statut == 409 and "coffre" in str(e).lower(), e)
CF.poser("motdepasse-banc-493", {})
CF.ouvrir("motdepasse-banc-493")
CF.ecrire_cle("IG_APP_SECRET", APP_SECRET)
url = IO.demarrer(None)
u = urlsplit(url)
q = {k: v[0] for k, v in parse_qs(u.query).items()}
check("2.3 www.instagram.com/oauth/authorize", u.scheme == "https" and u.netloc == "www.instagram.com"
      and u.path == "/oauth/authorize", url)
check("2.4 client_id, response_type=code, redirect_uri de la boucle locale",
      q.get("client_id") == APP_ID and q.get("response_type") == "code"
      and q.get("redirect_uri") == "http://127.0.0.1:8765/api/oauth/instagram/callback", q)
check("2.5 les quatre scopes, séparés par des virgules", q.get("scope") == ",".join(IO.SCOPES), q.get("scope"))
check("2.6 state anti-rejeu : 32 caractères hexadécimaux, gardé côté serveur",
      re.fullmatch(r"[0-9a-f]{32}", q.get("state", "")) and q["state"] in IO._ETATS, q.get("state"))
check("2.7 aucun secret dans l'URL, pas de PKCE (non documenté par Meta)",
      APP_SECRET not in url and "code_challenge" not in q, url)
r = c.post("/api/oauth/instagram/demarrer", json={})
check("2.8 route démarrer : {url} vers Instagram, aucun appel réseau", r.status_code == 200
      and r.json()["url"].startswith("https://www.instagram.com/oauth/authorize?") and not APPELS, r.text[:200])
r = c.post("/api/oauth/instagram/demarrer", json={"compte": "c00000000"})
check("2.9 compte inconnu : 404", r.status_code == 404, r.text[:200])
cx = CPT.creer({"plateforme": "x", "espace_id": "deepotus", "libelle": "X banc"})
r = c.post("/api/oauth/instagram/demarrer", json={"compte": cx["id"]})
check("2.10 compte d'une autre plateforme : 400", r.status_code == 400, r.text[:200])
CAC.appliquer({"IG_OAUTH_REDIRECT": "https://localhost/deepotus-instagram"})
q2 = {k: v[0] for k, v in parse_qs(urlsplit(IO.demarrer(None)).query).items()}
check("2.11 adresse de retour réglée (https://localhost…) : c'est elle qui part", q2["redirect_uri"]
      == "https://localhost/deepotus-instagram" and IO.redirect_uri() == "https://localhost/deepotus-instagram", q2)
CAC.appliquer({"IG_OAUTH_REDIRECT": "javascript:alert(1)"})
check("2.12 adresse de retour qui n'est pas http(s) : ignorée (boucle locale)",
      IO.redirect_uri() == "http://127.0.0.1:8765/api/oauth/instagram/callback", IO.redirect_uri())
CAC.appliquer({"IG_OAUTH_REDIRECT": ""})

print("[3] state refusé")
n = len(APPELS)
for etiquette, st in (("inconnu", "f" * 32), ("vide", "")):
    try:
        asyncio.run(IO.terminer(CODE, st))
        check(f"3.1 state {etiquette} refusé", False)
    except IO.RefusIG as e:
        check(f"3.1 state {etiquette} refusé (400), aucun appel", e.statut == 400 and len(APPELS) == n, e)
st = parse_qs(urlsplit(IO.demarrer(None)).query)["state"][0]
try:
    asyncio.run(IO.terminer(CODE, st, maintenant=time.time() + IO.ETAT_DUREE_S + 5))
    check("3.2 state expiré refusé", False)
except IO.RefusIG as e:
    check("3.2 state expiré refusé, aucun appel", e.statut == 400 and len(APPELS) == n and st not in IO._ETATS, e)
r = c.get("/api/oauth/instagram/callback", params={"code": CODE, "state": "a" * 32})
check("3.3 rappel au state inconnu : page 400, aucun appel", r.status_code == 400 and "<h2>" in r.text and len(APPELS) == n,
      r.text[:300])
st = parse_qs(urlsplit(IO.demarrer(None)).query)["state"][0]
r = c.get("/api/oauth/instagram/callback", params={"error": "access_denied", "error_reason": "user_denied", "state": st})
check("3.4 refus de l'utilisateur : page 400, state consommé, aucun appel",
      r.status_code == 400 and "user_denied" in r.text and st not in IO._ETATS and len(APPELS) == n, r.text[:300])
r = c.post("/api/oauth/instagram/retour", json={"adresse": "https://localhost/x?state=" + "b" * 32})
check("3.5 adresse collée sans code : 400", r.status_code == 400 and len(APPELS) == n, r.text[:200])
check("3.6 lire_retour : code nettoyé de « #_ », state, erreur",
      IO.lire_retour("https://localhost/cb?code=AB12&state=" + "c" * 32 + "#_") == ("AB12", "c" * 32, "")
      and IO.lire_retour("https://localhost/cb?state=s0&code=AB12#_") == ("AB12", "s0", "")
      and IO.lire_retour("https://localhost/cb?code=AB12%23_&state=s1") == ("AB12", "s1", "")
      and IO.lire_retour("https://localhost/cb?error=access_denied&error_reason=user_denied&state=s2")[2] == "user_denied",
      IO.lire_retour("https://localhost/cb?code=AB12&state=" + "c" * 32 + "#_"))


def _meta_ok():
    REPONSES.clear()
    REPONSES[IO.TOKEN_URL] = lambda m, u, k: _R(200, {"data": [{"access_token": COURT, "user_id": IG_ID,
                                                                "permissions": ",".join(IO.SCOPES)}]})
    REPONSES[IO.LONG_URL] = lambda m, u, k: _R(200, {"access_token": LONG, "token_type": "bearer",
                                                     "expires_in": 5183944})
    REPONSES[IO.ME_URL] = lambda m, u, k: _R(200, {"user_id": IG_ID, "username": "deepotus_ai",
                                                   "account_type": "BUSINESS", "id": "2600000000000000"})


print("[4] retour : échange, jeton longue durée au coffre, vérification")
_meta_ok()
APPELS.clear()
VAPPELS.clear()
t0 = time.time()
st = parse_qs(urlsplit(IO.demarrer(None)).query)["state"][0]
res = asyncio.run(IO.terminer(CODE + "#_", st, maintenant=t0))
m1, m2, m3 = (APPELS + [None] * 3)[:3]
check("4.1 trois appels dans l'ordre : code, longue durée, /me", [a[:2] for a in APPELS] == [
    ("POST", IO.TOKEN_URL), ("GET", IO.LONG_URL), ("GET", IO.ME_URL)], [a[:2] for a in APPELS])
check("4.2 échange du code : POST api.instagram.com, client_id, secret, authorization_code, redirect_uri, code sans « #_ »",
      IO.TOKEN_URL == "https://api.instagram.com/oauth/access_token" and m1 and m1[2].get("data") == {
          "client_id": APP_ID, "client_secret": APP_SECRET, "grant_type": "authorization_code",
          "redirect_uri": "http://127.0.0.1:8765/api/oauth/instagram/callback", "code": CODE}, m1)
check("4.3 jeton longue durée : GET graph.instagram.com/access_token, ig_exchange_token",
      IO.LONG_URL == "https://graph.instagram.com/access_token" and m2 and m2[2].get("params") == {
          "grant_type": "ig_exchange_token", "client_secret": APP_SECRET, "access_token": COURT}, m2)
check("4.4 vérification : /me?fields=user_id,username,account_type avec le jeton LONG",
      m3 and m3[1].startswith("https://graph.instagram.com/") and m3[1].endswith("/me")
      and m3[2].get("params", {}).get("fields") == "user_id,username,account_type"
      and m3[2]["params"].get("access_token") == LONG, m3)
check("4.5 jeton longue durée AU COFFRE, appliqué, l'ID du compte posé", CF.lire_cle("IG_ACCESS_TOKEN") == LONG
      and settings.IG_ACCESS_TOKEN == LONG and settings.IG_BUSINESS_ID == IG_ID and settings.has_instagram, res)
check("4.6 réponse : compte, @nom, type, expiration datée (~60 j), endroit = coffre",
      res.get("username") == "deepotus_ai" and res.get("account_type") == "BUSINESS" and res.get("ou") == "coffre"
      and res.get("compte") == "historique-instagram"
      and abs(res.get("expire_ts", 0) - (t0 + 5183944)) < 2 and re.fullmatch(r"20\d\d-\d\d-\d\d", res.get("expire", "")), res)
e = IO.etat()
check("4.7 état : relié, expiration et date d'obtention gardées hors secret", e["comptes"].get("historique-instagram", {})
      .get("expire_ts") == res["expire_ts"] and e["comptes"]["historique-instagram"].get("username") == "deepotus_ai", e)
check("4.8 verif_canaux : le compte est vérifié vert sur graph.instagram.com (jeton IGAA)",
      VAPPELS and VAPPELS[-1][0] == f"https://graph.instagram.com/{IP.VERSION}/{IG_ID}"
      and (CPT.obtenir("historique-instagram").get("verification") or {}).get("etat") == "vert",
      (VAPPELS, CPT.obtenir("historique-instagram").get("verification")))
check("4.9 le state a servi une fois", st not in IO._ETATS)
try:
    asyncio.run(IO.terminer(CODE, st))
    check("4.10 rejeu du même state refusé", False)
except IO.RefusIG as e:
    check("4.10 rejeu du même state refusé", e.statut == 400, e)

# un compte d'ESPACE choisi : le jeton va sous son nom propre, l'id dans ses champs publics
ci = CPT.creer({"plateforme": "instagram", "espace_id": "deepotus", "libelle": "IG client"})
APPELS.clear()
r = c.post("/api/oauth/instagram/demarrer", json={"compte": ci["id"]})
st = parse_qs(urlsplit(r.json()["url"]).query)["state"][0]
r = c.post("/api/oauth/instagram/retour", json={"adresse": f"https://localhost/cb?code={CODE}&state={st}#_"})
nom_c = CPT.nom_secret(ci["id"], "IG_ACCESS_TOKEN")
vue = CPT.obtenir(ci["id"])
check("4.11 retour collé pour un compte d'espace : 200, jeton au coffre sous DZC_<ID>_IG_ACCESS_TOKEN",
      r.status_code == 200 and CF.lire_cle(nom_c) == LONG and r.json().get("compte") == ci["id"], (r.status_code, r.text[:300]))
check("4.12 compte d'espace : IG_BUSINESS_ID public, disponible, vérifié",
      any(ch["nom"] == "IG_BUSINESS_ID" and ch.get("valeur") == IG_ID for ch in vue["champs"]) and vue["disponible"]
      and (vue.get("verification") or {}).get("etat") == "vert", vue)
check("4.13 état : listé parmi les comptes Instagram de l'espace", any(x["id"] == ci["id"] for x in IO.etat()["choix"])
      and any(x["id"] == "historique-instagram" for x in IO.etat()["choix"]), IO.etat()["choix"])

# un compte personnel est refusé, rien n'est gardé
REPONSES[IO.ME_URL] = lambda m, u, k: _R(200, {"user_id": "999", "username": "perso", "account_type": "PERSONAL"})
avant = CF.lire_cle("IG_ACCESS_TOKEN")
st = parse_qs(urlsplit(IO.demarrer(None)).query)["state"][0]
try:
    asyncio.run(IO.terminer(CODE, st))
    check("4.14 compte personnel refusé", False)
except IO.RefusIG as e:
    check("4.14 compte personnel refusé, rien de gardé", e.statut == 400 and "perso" in str(e)
          and CF.lire_cle("IG_ACCESS_TOKEN") == avant and settings.IG_BUSINESS_ID == IG_ID, e)
# Meta refuse le code : l'erreur est dite, nettoyée
REPONSES[IO.TOKEN_URL] = lambda m, u, k: _R(400, {"error_type": "OAuthException", "code": 400,
                                                  "error_message": f"Invalid code {CODE} for secret {APP_SECRET}"})
st = parse_qs(urlsplit(IO.demarrer(None)).query)["state"][0]
r = c.post("/api/oauth/instagram/retour", json={"adresse": f"https://localhost/cb?code={CODE}&state={st}"})
check("4.15 Meta refuse le code : 502, ni code ni secret recopiés", r.status_code == 502
      and CODE not in r.text and APP_SECRET not in r.text and "Invalid code" in r.text, r.text[:300])
_meta_ok()

print("[5] aucun secret ne fuit")
st = parse_qs(urlsplit(IO.demarrer(None)).query)["state"][0]
r = c.get("/api/oauth/instagram/callback", params={"code": CODE, "state": st})
check("5.1 rappel direct : page 200 « relié », sans secret", r.status_code == 200 and "deepotus_ai" in r.text
      and not any(s in r.text for s in SECRETS), r.text[:300])
r = c.get("/api/oauth/instagram/etat")
check("5.2 état : aucun secret", r.status_code == 200 and not any(s in r.text for s in SECRETS), r.text[:300])
jr = "\n".join(JOURNAL)
check("5.3 journal : aucun secret (code, jetons, secret de l'application)", not any(s in jr for s in SECRETS),
      [s for s in SECRETS if s in jr])
fuites = []
for p in _tmp.rglob("*"):
    if p.is_file() and p.name != "coffre.dzk":
        try:
            b = p.read_bytes()
        except OSError:
            continue
        fuites += [f"{p.name}:{s}" for s in SECRETS if s.encode() in b]
check("5.4 aucun fichier hors coffre ne porte un secret (.env, comptes.json, état OAuth…)", not fuites, fuites)
check("5.5 le coffre chiffré ne les porte pas en clair", not any(s.encode() in (_tmp / "coffre.dzk").read_bytes() for s in SECRETS))
r = c.get("/api/oauth/instagram/etat", headers={"Accept-Language": "en"})
check("5.6 hors boucle locale : refus (401 appareil / 403 réglages)",
      TestClient(app, client=("10.0.0.9", 5)).get("/api/oauth/instagram/etat").status_code in (401, 403))

print("[6] renouvellement daté")
APPELS.clear()
REPONSES[IO.REFRESH_URL] = lambda m, u, k: _R(200, {"access_token": NEUF, "token_type": "bearer", "expires_in": 5183944})
t_obt = IO.etat()["comptes"]["historique-instagram"]["obtenu_ts"]
r = asyncio.run(IO.renouveler_dus(maintenant=t_obt + 3600))
check("6.1 jeton de moins de 24 h : pas renouvelé, aucun appel", r == [] and not APPELS, (r, APPELS))
r = asyncio.run(IO.renouveler_dus(maintenant=t_obt + 20 * 86400))
check("6.2 échéance lointaine (40 j) : pas renouvelé", r == [] and not APPELS, (r, APPELS))
t_r = t_obt + 55 * 86400
r = asyncio.run(IO.renouveler_dus(maintenant=t_r))
check("6.3 à 5 j de l'échéance : renouvelé (les deux comptes reliés)", sorted(r) == sorted(["historique-instagram", ci["id"]])
      and all(a[:2] == ("GET", IO.REFRESH_URL) for a in APPELS) and len(APPELS) == 2, (r, APPELS))
check("6.4 refresh : graph.instagram.com/refresh_access_token, ig_refresh_token, jeton courant",
      IO.REFRESH_URL == "https://graph.instagram.com/refresh_access_token" and APPELS
      and APPELS[0][2].get("params", {}).get("grant_type") == "ig_refresh_token"
      and APPELS[0][2]["params"].get("access_token") == LONG, APPELS[:1])
e = IO.etat()["comptes"]["historique-instagram"]
check("6.5 jeton neuf au coffre, nouvelle échéance datée", CF.lire_cle("IG_ACCESS_TOKEN") == NEUF and CF.lire_cle(nom_c) == NEUF
      and abs(e["expire_ts"] - (t_r + 5183944)) < 2 and e.get("renouvele_ts") == t_r, e)
APPELS.clear()
r = asyncio.run(IO.renouveler_dus(maintenant=t_r + 3600))
check("6.6 tout juste renouvelé : rien", r == [] and not APPELS)
REPONSES[IO.REFRESH_URL] = lambda m, u, k: _R(400, {"error": {"message": f"bad token {NEUF}", "code": 190,
                                                              "type": "OAuthException"}})
r = asyncio.run(IO.renouveler_dus(maintenant=t_r + 55 * 86400))
e = IO.etat()["comptes"]["historique-instagram"]
check("6.7 refus de Meta : jeton gardé, erreur notée sans secret", r == [] and CF.lire_cle("IG_ACCESS_TOKEN") == NEUF
      and e.get("erreur") and NEUF not in json.dumps(e), e)
CF.fermer()
APPELS.clear()
r = asyncio.run(IO.renouveler_dus(maintenant=t_r + 55 * 86400))
check("6.8 coffre fermé : aucun renouvellement, aucun appel", r == [] and not APPELS, (r, APPELS))
CF.ouvrir("motdepasse-banc-493")
APPELS.clear()
r = asyncio.run(IO.renouveler_dus(maintenant=t_r + 61 * 86400))
e = IO.etat(maintenant=t_r + 61 * 86400)["comptes"]["historique-instagram"]
check("6.9 jeton expiré : aucun appel, « reliez à nouveau »", r == [] and not APPELS and e.get("expire_passe") is True, e)
src_m = (RACINE / "backend" / "app" / "services" / "marketing.py").read_text("utf-8")
i = src_m.index("async def tick(")
check("6.10 branché sur la passe quotidienne du Planificateur (marketing.tick)",
      "instagram_oauth" in src_m[i:i + 2500] and "renouveler_dus" in src_m[i:i + 2500])
REPONSES[IO.REFRESH_URL] = lambda m, u, k: _R(200, {"access_token": NEUF, "token_type": "bearer", "expires_in": 5183944})

print("[7] hôte selon le jeton")
check("7.1 IGAA -> graph.instagram.com, EAA -> graph.facebook.com",
      IP.hote_graph("IGAAabc") == "graph.instagram.com" and IP.hote_graph("EAAabc") == "graph.facebook.com"
      and IP.hote_graph(" IGQWabc ") == "graph.instagram.com" and IP.hote_graph("") == "graph.facebook.com")
CAC.appliquer({"IG_ACCESS_TOKEN": "EAAbanc-page"})
g_eaa = IP._graph()
CAC.appliquer({"IG_ACCESS_TOKEN": NEUF})
g_ig = IP._graph()
check("7.2 publication : _graph suit le jeton courant", g_eaa == f"https://graph.facebook.com/{IP.VERSION}"
      and g_ig == f"https://graph.instagram.com/{IP.VERSION}", (g_eaa, g_ig))
with CPT.sous_compte(ci["id"]):
    g_c = IP._graph()
check("7.3 sous un compte d'espace : l'hôte suit SON jeton", g_c == f"https://graph.instagram.com/{IP.VERSION}", g_c)
VAPPELS.clear()
CAC.appliquer({"IG_ACCESS_TOKEN": "EAAbanc-page"})
asyncio.run(V.verifier_plateforme("instagram"))
check("7.4 verif_canaux avec un jeton EAA : graph.facebook.com", VAPPELS and VAPPELS[-1][0].startswith("https://graph.facebook.com/"),
      VAPPELS)
CAC.appliquer({"IG_ACCESS_TOKEN": NEUF})

print("[8] convention t520")
for k in ("IG_APP_ID", "IG_APP_SECRET", "IG_OAUTH_REDIRECT"):
    check(f"8.1 {k} : liste blanche, rubrique Comptes connectés", k in _ALLOWED_ENV_KEYS and SR.rubrique_de(k) == "accounts")
check("8.2 seul le secret de l'application va au coffre", "IG_APP_SECRET" in CF.SECRETES and "IG_APP_ID" not in CF.SECRETES
      and "IG_OAUTH_REDIRECT" not in CF.SECRETES)
check("8.3 console rappelée après une révocation", any(x["cle"] == "IG_APP_SECRET" and x["url"].startswith("https://")
                                                       for x in APR.CONSOLES))
for k in ("IG_APP_ID", "IG_APP_SECRET", "IG_OAUTH_REDIRECT"):
    g = G.guide(k) or {}
    check(f"8.4 {k} : guide FR/EN daté du 26/11, console https, Instagram Login, adresse de retour, scopes",
          g.get("fr") and g.get("en") and g.get("verifie_le") == "2026-11-26" and str(g.get("console", "")).startswith("https://")
          and all(m in g["fr"] and m in g["en"] for m in ("Instagram login", IO.redirect_uri(), "https://localhost/",
                                                          *IO.SCOPES)), g)
check("8.5 le guide du collage manuel est intact (Unified login, quatre autorisations)",
      "Unified login" in (G.guide("IG_ACCESS_TOKEN") or {}).get("fr", ""))
n = len(APPELS)
for k in ("IG_APP_ID", "IG_APP_SECRET"):
    rr = asyncio.run(D.tester_cle(k, "valeur-quelconque"))
    check(f"8.6 {k} : testable, « Tester » le dit sans rien appeler (ok None)", D.testable(k) and rr["ok"] is None
          and "Relier par Instagram" in rr["message"] and len(APPELS) == n, rr)
r = c.post("/api/reglages/diagnostic/cle", json={"nom": "IG_APP_SECRET", "valeur": "x"}, headers={"Accept-Language": "en"})
check("8.7 le message du test en anglais", r.status_code == 200 and "Link with Instagram" in r.json()["message"], r.text[:200])

print("[9] écran et traductions")
dico = json.loads((RACINE / "backend" / "app" / "i18n" / "messages.json").read_text("utf-8"))
neufs = {k: v for k, v in dico.items() if k.startswith("ig.oauth.") or k == "diag.cle.ig_app_par_liaison"}
check("9.1 messages ig.oauth.* : FR et EN, mêmes variables", len(neufs) >= 10 and all(
    v.get("fr") and v.get("en") and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
    for v in neufs.values()), sorted(neufs))
src_io = (RACINE / "backend" / "app" / "services" / "instagram_oauth.py").read_text("utf-8")
cites = set(re.findall(r'"(ig\.oauth\.[a-z_]+)"', src_io)) | set(re.findall(r'"(ig\.oauth\.[a-z_]+)"',
            (RACINE / "backend" / "app" / "api" / "instagram_oauth_routes.py").read_text("utf-8")))
check("9.2 chaque message cité existe", cites and cites <= set(dico), sorted(cites - set(dico)))
check("9.3 docstring : la doc Meta relue, datée, URL", "26/11/2026" in src_io
      and "developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login" in src_io)
ui = json.loads((RACINE / "frontend" / "shared" / "i18n" / "igrelier.json").read_text("utf-8"))
check("9.4 dictionnaire d'écran igrelier : clés à trois segments, FR et EN", ui and all(
    re.fullmatch(r"igrelier\.[a-z0-9_]+\.[a-z0-9_]+", k) and v.get("fr") and v.get("en") for k, v in ui.items()))
check("9.5 le bouton s'appelle « Relier par Instagram »", (ui.get("igrelier.bouton.relier") or {}).get("fr") == "Relier par Instagram")
mod = RACINE / "frontend" / "shared" / "dz-ig-relier.js"
check("9.6 module partagé, copie dist identique", mod.is_file()
      and mod.read_bytes() == (RACINE / "frontend" / "dist" / "shared" / "dz-ig-relier.js").read_bytes())
check("9.7 chargé par la SPA, une fois", (RACINE / "frontend" / "dist" / "index.html").read_text("utf-8")
      .count('<script src="/shared/dz-ig-relier.js"></script>') == 1)
r_ = subprocess.run(["node", "--check", str(mod)], capture_output=True, text=True)
check("9.8 node --check du module", r_.returncode == 0, r_.stderr[-200:])
src = mod.read_text("utf-8")
check("9.9 aucun texte en dur : toutes les clés citées existent, aucun innerHTML",
      all(k in ui for k in re.findall(r'T\("(igrelier\.[a-z0-9_.]+)"', src)) and 'T("' in src and "innerHTML" not in src)
B = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text("utf-8")
check("9.10 maillon dziglogin : hôte du bouton dans le bloc Instagram, champs de l'application",
      "data-dz-ig-relier-hote" in B and '{k:"IG_APP_ID",label:dzT("igrelier.champ.app_id")}' in B
      and '{k:"IG_APP_SECRET",label:dzT("igrelier.champ.app_secret")}' in B
      and '{k:"IG_OAUTH_REDIRECT",label:dzT("igrelier.champ.redirect")}' in B)
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                                          # noqa: E402
import patch_bundle_dziglogin as PM                                   # noqa: E402
check("9.11 marqueur x2, une pose par paire", B.count(PM.MARKER) == PM.MARKER_ATTENDU == 2)
check("9.12 avant_dziglogin == defaire, sans marqueur rendu tel quel",
      AIDE.avant_dziglogin(B) == PM.defaire(B) and AIDE.avant_dziglogin(PM.defaire(B)) == PM.defaire(B))
aide = (_ICI / "_i18n_l1_aide.py").read_text("utf-8")
i = aide.index("def avant_dzlogiciels3d(")
corps = aide[i:aide.index("\ndef ", i + 10)]
check("9.13 appelé EN TÊTE de avant_dzlogiciels3d", "bundle = avant_dziglogin(bundle)" in corps
      and corps.index("avant_dziglogin(") < corps.index("if _m.MARKER not in bundle"))
check("9.14 épingles du bundle intouchées", B.count("x.useState(") == 731 and B.count("DzTracks") == 181
      and B.count("v2.8.0") == 4 and B.count("await window.__dzDialogue.confirmer(") == 30)
r_ = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dziglogin.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace")
check("9.15 --check : déjà appliqué", r_.returncode == 0 and "déjà appliqué" in r_.stdout, r_.stdout + r_.stderr)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
