# -*- coding: utf-8 -*-
"""Réglages de publication (plan scheduler T6 — tâche #28, 30/09/2026) : clés TikTok admises (les secrètes au coffre),
drapeaux /health, OAuth YouTube ET TikTok par rappel loopback (la voie « coller le code » du plan est abandonnée : la
doc TikTok Desktop accepte 127.0.0.1), jeton rangé là où vivent les clés (coffre.enregistrer_cle), refus si le coffre
est fermé, tests de canal pour les trois réseaux, gardes de boucle locale. Le VRAI échange OAuth tourne : seul le réseau
est simulé (tests/fakehttp.py). Data-dir temporaire. Témoin : la base fc0a8f4 n'a aucune route OAuth.
Run : & $PY tests/test_scheduler_settings.py   (depuis backend/)"""
import os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzset_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fakehttp import Recorder                                       # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_vr = subprocess.run(["git", "show", "fc0a8f4:backend/app/api/routes.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base fc0a8f4")
check("0.1 TÉMOIN : ni route OAuth ni drapeau youtube_enabled", _vr and "/oauth/youtube/start" not in _vr and "youtube_enabled" not in _vr)

from app.config import settings, ENV_FILE                           # noqa: E402
for _k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
           "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
    setattr(settings, _k, "")
settings.TIKTOK_AUDITED = False
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import coffre, youtube_publisher as yp, instagram_publisher as ip, tiktok_publisher as tp  # noqa: E402

rec = Recorder()
yp._client = ip._client = tp._client = rec.factory
check("0.2 le .env est celui du banc", str(ENV_FILE).startswith(str(_tmp)), str(ENV_FILE))
env = lambda: ENV_FILE.read_text("utf-8") if ENV_FILE.exists() else ""   # noqa: E731

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[1] les clés")
    cles = {k["key"] for k in c.get("/api/settings/keys").json()["keys"]}
    check("1.1 les quatre clés TikTok sont admises ; TIKTOK_REDIRECT_URI (voie « code collé ») n'existe pas",
          {"TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "TIKTOK_AUDITED"} <= cles
          and "TIKTOK_REDIRECT_URI" not in cles, str(sorted(k for k in cles if "TIKTOK" in k)))
    check("1.2 au coffre : le secret du client et le refresh token TikTok ; pas l'identifiant public ni le drapeau d'audit",
          {"TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "YOUTUBE_REFRESH_TOKEN"} <= coffre.SECRETES
          and not ({"TIKTOK_CLIENT_KEY", "TIKTOK_AUDITED"} & coffre.SECRETES))
    r = c.post("/api/settings/keys", json={"entries": [{"name": "TIKTOK_AUDITED", "value": "true"}]})
    check("1.3 TIKTOK_AUDITED=true s'applique à chaud (booléen lu par pydantic)", r.status_code == 200 and settings.TIKTOK_AUDITED is True, r.text[:200])
    c.post("/api/settings/keys", json={"entries": [{"name": "TIKTOK_AUDITED", "value": ""}]})
    check("1.4 vidée, elle revient à faux", settings.TIKTOK_AUDITED is False)

    print("\n[2] /health")
    h = c.get("/api/health").json()
    check("2.1 trois drapeaux, faux sans clés", h.get("youtube_enabled") is False and h.get("instagram_enabled") is False
          and h.get("tiktok_enabled") is False, str({k: v for k, v in h.items() if k.endswith("_enabled")}))

    print("\n[3] YouTube : consentement par rappel loopback")
    r = c.get("/api/oauth/youtube/start", follow_redirects=False)
    check("3.1 sans client Google : 400 qui dit quoi faire (client « Application de bureau »)", r.status_code == 400
          and "YOUTUBE_CLIENT_ID" in r.text and "bureau" in r.text, r.text[:200])
    settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET = "cid.apps.googleusercontent.com", "GOCSPX-banc"
    r = c.get("/api/oauth/youtube/start", follow_redirects=False)
    loc = r.headers.get("location", "")
    state = dict(httpx.URL(loc).params).get("state", "")
    check("3.2 302 vers Google, avec un état et le défi PKCE", r.status_code == 302 and loc.startswith("https://accounts.google.com/")
          and len(state) >= 16 and "code_challenge=" in loc, loc[:120])
    r = c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": "faux"})
    check("3.3 état inconnu : 400, aucun appel à Google", r.status_code == 400 and not rec.calls)
    r = c.get("/api/oauth/youtube/callback", params={"error": "<script>alert(1)</script>", "state": state})
    check("3.4 refus de l'utilisateur : 400, et le paramètre renvoyé est ÉCHAPPÉ (pas d'injection dans la page)",
          r.status_code == 400 and "<script>" not in r.text and "&lt;script&gt;" in r.text, r.text[:200])
    r = c.get("/api/oauth/youtube/start", follow_redirects=False)
    state = dict(httpx.URL(r.headers["location"]).params)["state"]
    rec.script[:] = [httpx.Response(200, json={"refresh_token": "1//rt-yt", "access_token": "at"})]
    r = c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": state})
    f = rec.calls[-1].form() if rec.calls else {}
    check("3.5 le VRAI échange part (code + vérificateur PKCE), la page dit « connecté »", r.status_code == 200
          and "connecté" in r.text.lower() and f.get("code") == "abc" and f.get("code_verifier"), r.text[:200])
    check("3.6 refresh token écrit (pas de coffre ici → .env du data-dir) ET appliqué sans redémarrage",
          "YOUTUBE_REFRESH_TOKEN=1//rt-yt" in env() and settings.has_youtube and c.get("/api/health").json()["youtube_enabled"] is True)
    r = c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": state})
    check("3.7 le même état ne sert pas deux fois", r.status_code == 400)
    r = c.get("/api/oauth/youtube/start", follow_redirects=False)
    state = dict(httpx.URL(r.headers["location"]).params)["state"]
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"})]            # Google n'a pas rendu de refresh token
    r = c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": state})
    check("3.8 pas de refresh token rendu : 502 qui explique (révoquer l'accès puis recommencer)", r.status_code == 502
          and "révoque" in r.text.lower(), r.text[:200])

    print("\n[4] TikTok : même voie (loopback, PKCE hexadécimal)")
    r = c.get("/api/oauth/tiktok/start", follow_redirects=False)
    check("4.1 sans client TikTok : 400 qui nomme les clés", r.status_code == 400 and "TIKTOK_CLIENT_KEY" in r.text, r.text[:200])
    settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET = "awck", "tt-secret-banc"
    r = c.get("/api/oauth/tiktok/start", follow_redirects=False)
    q = dict(httpx.URL(r.headers.get("location", "")).params)
    check("4.2 302 vers TikTok, rappel loopback avec la barre finale", r.status_code == 302
          and r.headers["location"].startswith("https://www.tiktok.com/v2/auth/authorize/")
          and q.get("redirect_uri", "").endswith("/api/oauth/tiktok/callback/"), str(q)[:200])
    rec.script[:] = [httpx.Response(200, json={"access_token": "act", "refresh_token": "rft.tt", "expires_in": 86400})]
    r = c.get("/api/oauth/tiktok/callback/", params={"code": "zzz", "state": q.get("state", "")})
    check("4.3 le rappel TikTok échange le code, range le refresh token, TikTok devient disponible",
          r.status_code == 200 and "connecté" in r.text.lower() and "TIKTOK_REFRESH_TOKEN=rft.tt" in env()
          and settings.has_tiktok and c.get("/api/health").json()["tiktok_enabled"] is True, r.text[:200])

    print("\n[5] tests de canal")
    r = c.post("/api/channels/test", json={"channel": "instagram"})
    check("5.1 Instagram sans clés : 400 qui nomme IG_ACCESS_TOKEN", r.status_code == 400 and "IG_ACCESS_TOKEN" in r.json().get("detail", ""))
    settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = "EAAB-jeton-ig-SECRET", "1789"
    rec.calls.clear()
    rec.script[:] = [httpx.Response(200, json={"username": "deepotus", "id": "1789"})]
    j = c.post("/api/channels/test", json={"channel": "instagram"}).json()
    check("5.2 Instagram : le compte pro répond, son nom revient (graph.facebook.com pour un jeton EAA…)",
          j == {"ok": True, "detail": "@deepotus"} and rec.calls[0].url.startswith("https://graph.facebook.com/v25.0/1789?"), str(j))
    rec.script[:] = [httpx.Response(400, json={"error": {"message": "Invalid EAAB-jeton-ig-SECRET"}})]
    j = c.post("/api/channels/test", json={"channel": "instagram"}).json()
    check("5.3 Instagram refusé : ok faux, jeton masqué", j.get("ok") is False and "SECRET" not in j.get("detail", ""), str(j))
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"}),
                     httpx.Response(200, json={"items": [{"snippet": {"title": "Deepotus"}}]})]
    j = c.post("/api/channels/test", json={"channel": "youtube"}).json()
    check("5.4 YouTube : la chaîne du compte connecté répond", j == {"ok": True, "detail": "chaîne « Deepotus »"}, str(j))
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"}), httpx.Response(200, json={"items": []})]
    j = c.post("/api/channels/test", json={"channel": "youtube"}).json()
    check("5.4b YouTube : un compte Google SANS chaîne n'est pas un succès (rien où publier)", j.get("ok") is False, str(j))
    tp._oublier_jeton()
    rec.script[:] = [httpx.Response(200, json={"access_token": "act2", "refresh_token": "rft.tt", "expires_in": 86400}),
                     httpx.Response(200, json={"data": {"user": {"display_name": "Deep"}}, "error": {"code": "ok"}})]
    j = c.post("/api/channels/test", json={"channel": "tiktok"}).json()
    check("5.5 TikTok : le compte connecté répond", j == {"ok": True, "detail": "compte « Deep »"}, str(j))
    tp._oublier_jeton()
    rec.script[:] = [httpx.Response(400, json={"error": "invalid_grant", "error_description": "bad rft.tt"})]
    j = c.post("/api/channels/test", json={"channel": "tiktok"}).json()
    check("5.6 TikTok refusé : ok faux, refresh token masqué", j.get("ok") is False and "rft.tt" not in j.get("detail", ""), str(j))

    print("\n[6] le coffre")
    coffre.poser("mot-de-passe-du-banc", {})
    r = c.get("/api/oauth/youtube/start", follow_redirects=False)
    check("6.1 coffre posé mais FERMÉ : 409 avant même Google (le jeton rendu ne pourrait pas être gardé)",
          r.status_code == 409 and "coffre" in r.text.lower(), r.text[:200])
    coffre.ouvrir("mot-de-passe-du-banc")
    avant = env()
    r = c.get("/api/oauth/youtube/start", follow_redirects=False)
    state = dict(httpx.URL(r.headers["location"]).params)["state"]
    rec.script[:] = [httpx.Response(200, json={"refresh_token": "1//au-coffre"})]
    r = c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": state})
    check("6.2 coffre OUVERT : le refresh token va au coffre, le .env n'est pas touché", r.status_code == 200
          and coffre.lire_cle("YOUTUBE_REFRESH_TOKEN") == "1//au-coffre" and env() == avant
          and settings.YOUTUBE_REFRESH_TOKEN == "1//au-coffre")
    coffre.fermer()

import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E401,E702
import _jeton_appareil as _JA  # noqa: E402 — tache #56 : le reseau local exige un jeton d'appareil (garde exterieure)
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as d:
    print("\n[7] hors boucle locale")
    codes = [d.get("/api/oauth/youtube/start", follow_redirects=False).status_code,
             d.get("/api/oauth/youtube/callback", params={"code": "x", "state": "y"}).status_code,
             d.get("/api/oauth/tiktok/start", follow_redirects=False).status_code,
             d.get("/api/oauth/tiktok/callback/", params={"code": "x", "state": "y"}).status_code,
             d.post("/api/channels/test", json={"channel": "youtube"}).status_code]
    check("7.1 les routes OAuth et le test de canal refusent tout client distant (403)", codes == [403] * 5, str(codes))

# la garde GLOBALE de main.py refuse déjà tout POST distant : la garde propre à /channels/test se prouve en appelant la
# route elle-même, sans passer par le middleware
import asyncio                                                      # noqa: E402
from starlette.requests import Request as _Req                      # noqa: E402
from fastapi import HTTPException as _HE                            # noqa: E402
from app.api import routes as _routes                               # noqa: E402
_distant = _Req({"type": "http", "method": "POST", "path": "/api/channels/test", "headers": [], "query_string": b"",
                 "client": ("192.168.1.20", 50000)})
try:
    asyncio.run(_routes.test_channel({"channel": "youtube"}, _distant))
    _code = 200
except _HE as e:
    _code = e.status_code
check("7.2 la route /channels/test porte SA garde (appelée sans middleware) : 403", _code == 403, str(_code))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
