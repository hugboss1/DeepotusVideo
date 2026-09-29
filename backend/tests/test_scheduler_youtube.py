# -*- coding: utf-8 -*-
"""YouTube Shorts (plan scheduler T3 — tâche #25, 29/09/2026). Le VRAI httpx.AsyncClient envoie sur un MockTransport
(tests/fakehttp.py) : seul le réseau est simulé. On vérifie ce qui PART (URL, en-têtes, corps lu en entier, formulaire
OAuth) et ce que l'adaptateur en DIT : init résumable à la taille réelle, PUT du fichier octet pour octet, 201 = succès,
visibilité RÉELLEMENT appliquée (un projet Google non vérifié force « private » — doc videos.insert relue le 29/09),
refus parlants, aucune clé dans les messages, PKCE S256. Data-dir temporaire, clés posées sur l'objet settings.
Témoin : la base 8fde215 n'a pas d'adaptateur YouTube.
Run : & $PY tests/test_scheduler_youtube.py   (depuis backend/)"""
import asyncio, base64, hashlib, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzyt_"))
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
_base = subprocess.run(["git", "ls-tree", "--name-only", "8fde215", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
_cfg = subprocess.run(["git", "show", "8fde215:backend/app/config.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 8fde215")
check("0.1 TÉMOIN : ni youtube_publisher.py ni has_youtube", "publishers.py" in _base and "youtube_publisher.py" not in _base
      and _cfg and "has_youtube" not in _cfg)

from app.config import settings                                     # noqa: E402
from app.services import marketing, publishers, youtube_publisher as yp  # noqa: E402

rec = Recorder()
yp._client = rec.factory
SECRET, RT = "GOCSPX-secret-du-banc", "1//refresh-du-banc"
vid = _tmp / "short.mp4"
vid.write_bytes(b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 9)


async def main():
    print("\n[1] clés et registre")
    for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        setattr(settings, k, "")
    check("1.1 sans clés : youtube indisponible, donc assisté", not settings.has_youtube and "youtube" not in marketing.auto_channels())
    settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET = "cid.apps.googleusercontent.com", SECRET
    check("1.2 client sans refresh token : toujours indisponible (l'OAuth n'a pas eu lieu)", not settings.has_youtube)
    settings.YOUTUBE_REFRESH_TOKEN = RT
    check("1.3 les trois clés posées (à chaud) : youtube entre dans le registre", settings.has_youtube
          and "youtube" in marketing.auto_channels() and "youtube" in publishers._REGISTRY)
    # le banc importe youtube_publisher lui-même : l'enregistrement par l'APPLICATION se prouve dans un processus neuf
    # qui n'importe que app.main (le chemin de production)
    _p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import app.main; "
                         "from app.services import publishers as P; print(sorted(P._REGISTRY))"],
                        cwd=str(racine / "backend"), capture_output=True, text=True,
                        env=dict(os.environ, DEEPOTUS_DATA_DIR=str(_tmp / "neuf")))
    check("1.4 l'application seule (import app.main) enregistre youtube, x et telegram",
          _p.returncode == 0 and {"telegram", "x", "youtube"} <= set(eval(_p.stdout.strip().splitlines()[-1] or "[]")),
          (_p.stdout + _p.stderr)[-300:])  # #26 : instagram s'y ajoute

    print("\n[2] OAuth appli de bureau : loopback et PKCE")
    u = httpx.URL(yp.auth_url("s1"))
    q = dict(u.params)
    check("2.1 point d'autorisation Google, redirection loopback 127.0.0.1 sur le port du backend",
          str(u).startswith("https://accounts.google.com/o/oauth2/v2/auth?")
          and q.get("redirect_uri") == f"http://127.0.0.1:{settings.PORT}/api/oauth/youtube/callback", str(q))
    check("2.2 hors ligne + consentement (sinon pas de refresh token), portée upload + lecture, état transmis",
          q.get("access_type") == "offline" and q.get("prompt") == "consent" and q.get("state") == "s1"
          and set(q.get("scope", "").split()) == {"https://www.googleapis.com/auth/youtube.upload",
                                                  "https://www.googleapis.com/auth/youtube.readonly"}, str(q))
    check("2.3 PKCE S256 (recommandé par Google pour les applis natives)", q.get("code_challenge_method") == "S256"
          and len(q.get("code_challenge", "")) >= 43)
    rec.calls.clear()
    rec.script[:] = [httpx.Response(200, json={"refresh_token": "1//neuf", "access_token": "at"})]
    got = await yp.exchange_code("code-google", "s1")
    f = rec.calls[0].form() if rec.calls else {}
    ver = f.get("code_verifier", "")
    chal = base64.urlsafe_b64encode(hashlib.sha256(ver.encode()).digest()).rstrip(b"=").decode()
    check("2.4 l'échange envoie le code, la même redirection et le vérificateur qui correspond au défi",
          got == "1//neuf" and f.get("code") == "code-google" and f.get("grant_type") == "authorization_code"
          and f.get("redirect_uri") == q.get("redirect_uri") and ver and chal == q.get("code_challenge"), str(f))
    rec.calls.clear()
    check("2.5 un état inconnu (ou déjà consommé) est refusé SANS appel réseau",
          await yp.exchange_code("code-google", "s1") == "" and await yp.exchange_code("x", "inconnu") == "" and not rec.calls)
    yp.auth_url("s2")
    rec.script[:] = [httpx.Response(400, json={"error": "invalid_grant"})]
    check("2.6 Google refuse l'échange : chaîne vide", await yp.exchange_code("mauvais", "s2") == "")

    print("\n[3] envoi résumable")
    rec.calls.clear()
    rec.script[:] = [httpx.Response(200, json={"access_token": "at-1", "expires_in": 3599}),
                     httpx.Response(200, headers={"location": "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=U1"}),
                     httpx.Response(201, json={"id": "vid123", "status": {"privacyStatus": "public"}})]
    res = await yp.publish("Titre du short\nLigne 2 #Shorts", str(vid), None, {"title": "Mon <Short>"})
    check("3.1 201 = succès, id rendu", res.ok and res.remote_id == "vid123" and res.detail == "youtube: short vid123", str(res))
    tok, init, put = (rec.calls + [None, None, None])[:3]
    check("3.2 jeton : refresh_token + client, formulaire au point de jeton", tok and tok.url == "https://oauth2.googleapis.com/token"
          and tok.form().get("grant_type") == "refresh_token" and tok.form().get("refresh_token") == RT)
    ib = json.loads(init.body) if init else {}
    check("3.3 init : POST résumable, taille RÉELLE et type annoncés, jeton porteur",
          init and init.method == "POST" and init.url.startswith("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable")
          and "part=snippet%2Cstatus" in init.url.replace(",", "%2C")
          and init.headers.get("x-upload-content-length") == str(vid.stat().st_size)
          and init.headers.get("x-upload-content-type") == "video/mp4" and init.headers.get("authorization") == "Bearer at-1",
          str(init.headers if init else None))
    check("3.4 métadonnées : titre du post nettoyé des chevrons interdits, légende en description, public demandé",
          ib.get("snippet", {}).get("title") == "Mon Short" and ib["snippet"].get("description", "").startswith("Titre du short")
          and ib.get("status", {}).get("privacyStatus") == "public" and ib["status"].get("selfDeclaredMadeForKids") is False, str(ib))
    check("3.5 PUT vers l'URI de session, le fichier OCTET POUR OCTET, par le vrai client asynchrone",
          put and put.method == "PUT" and put.url.endswith("upload_id=U1") and put.body == vid.read_bytes()
          and put.headers.get("content-type") == "video/mp4", str(put.headers if put else None))
    check("3.6 le PUT annonce sa taille (Content-Length), jamais un envoi « chunked » que l'envoi résumable refuse",
          put and put.headers.get("content-length") == str(vid.stat().st_size) and "transfer-encoding" not in put.headers,
          str(put.headers if put else None))

    print("\n[4] ce que YouTube a vraiment fait")
    rec.script[:] = [httpx.Response(200, json={"access_token": "at-2"}),
                     httpx.Response(200, headers={"location": "https://up.example/s2"}),
                     httpx.Response(201, json={"id": "vidP", "status": {"privacyStatus": "private"}})]
    res = await yp.publish("Un short", str(vid), None, {})
    check("4.1 demandé public, rendu PRIVÉ : c'est un succès, mais c'est DIT (projet Google non vérifié)",
          res.ok and res.remote_id == "vidP" and "privé" in res.detail and "non vérifié" in res.detail, str(res))
    rec.script[:] = [httpx.Response(200, json={"access_token": "at-3"}),
                     httpx.Response(200, headers={"location": "https://up.example/s3"}),
                     httpx.Response(201, json={"id": "vidU", "status": {"privacyStatus": "unlisted"}})]
    res = await yp.publish("Un short", str(vid), None, {"privacy": "unlisted"})
    check("4.2 non répertorié demandé et obtenu : rien à signaler", res.ok and res.detail == "youtube: short vidU", str(res))

    print("\n[5] refus parlants")
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"}), httpx.Response(403, text="quotaExceeded")]
    res = await yp.publish("x", str(vid), None, {})
    check("5.1 init 403 : le statut et la raison remontent", not res.ok and res.detail.startswith("youtube init 403")
          and "quotaExceeded" in res.detail, str(res))
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"}), httpx.Response(200, headers={})]
    res = await yp.publish("x", str(vid), None, {})
    check("5.2 init sans URI de session : refus, AUCUN PUT dans le vide", not res.ok and "session" in res.detail
          and not any(c.method == "PUT" for c in rec.calls[-2:]), str(res))
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"}),
                     httpx.Response(200, headers={"location": "https://up.example/s4"}), httpx.Response(500, text="backend")]
    res = await yp.publish("x", str(vid), None, {})
    check("5.3 PUT 500 : échec d'envoi dit", not res.ok and res.detail.startswith("youtube upload 500"), str(res))
    rec.calls.clear()
    rec.script[:] = [httpx.Response(400, json={"error": "invalid_grant", "error_description": "Token has been expired or revoked."})]
    res = await yp.publish("x", str(vid), None, {})
    check("5.4 refresh token révoqué : dit, sans aucune clé dans le message", not res.ok and "invalid_grant" in res.detail
          and SECRET not in res.detail and RT not in res.detail and len(rec.calls) == 1, str(res))
    rec.calls.clear()
    res = await yp.publish("x", None, str(vid), {})
    check("5.5 pas de vidéo : refus SANS réseau (un Short exige une vidéo)", not res.ok and "exige une vidéo" in res.detail
          and not rec.calls, str(res))

    print("\n[6] statistiques (1 unité)")
    rec.calls.clear()
    rec.script[:] = [httpx.Response(200, json={"access_token": "at"}),
                     httpx.Response(200, json={"items": [{"id": "vid123", "statistics": {
                         "viewCount": "42", "likeCount": "3", "commentCount": "1"}}, {"id": "vidX", "statistics": {}}]})]
    st = await yp.fetch_stats(["vid123", "vidX"])
    check("6.1 statistics lues, partages/enregistrements à 0 (l'API ne les donne pas), compteurs absents = 0",
          st == {"vid123": {"views": 42, "likes": 3, "comments": 1, "shares": 0, "saves": 0},
                 "vidX": {"views": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0}}, str(st))
    g = rec.calls[1] if len(rec.calls) > 1 else None
    check("6.2 un seul GET part=statistics pour tous les ids", g and g.method == "GET" and g.params().get("part") == "statistics"
          and g.params().get("id") == "vid123,vidX")
    rec.calls.clear()
    check("6.3 aucune vidéo : aucun appel", await yp.fetch_stats([]) == {} and not rec.calls)

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
