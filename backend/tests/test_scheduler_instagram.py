# -*- coding: utf-8 -*-
"""Instagram Reels (plan scheduler T4 — tâche #26, 29/09/2026). Le VRAI httpx.AsyncClient envoie sur un MockTransport
(tests/fakehttp.py). On vérifie ce qui PART et ce que l'adaptateur en DIT : compteur de publication demandé à Instagram
AVANT tout (100 posts / 24 h GLISSANTES — doc relue le 29/09), conteneur REELS résumable, envoi binaire depuis le PC
(offset/file_size, corps octet pour octet), sondage borné à 5 minutes, media_publish ; l'hôte suit le type de jeton
(connexion Instagram « IG… » → graph.instagram.com, connexion Facebook → graph.facebook.com) ; le jeton n'apparaît
dans AUCUN détail. Data-dir temporaire. Témoin : la base e2f2beb n'a pas d'adaptateur Instagram.
Run : & $PY tests/test_scheduler_instagram.py   (depuis backend/)"""
import asyncio, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzig_"))
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
_base = subprocess.run(["git", "ls-tree", "--name-only", "e2f2beb", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base e2f2beb")
check("0.1 TÉMOIN : youtube_publisher.py oui, instagram_publisher.py non", "youtube_publisher.py" in _base
      and "instagram_publisher.py" not in _base)

from app.config import settings                                     # noqa: E402
from app.services import marketing, quota, instagram_publisher as ip  # noqa: E402

rec = Recorder()
ip._client = rec.factory
DELAIS = tuple(ip.POLL_DELAIS)
ip.POLL_DELAIS = (0,) * len(DELAIS)
TOK_FB, TOK_IG = "EAAB-jeton-facebook-SECRET", "IGAA-jeton-instagram-SECRET"
vid = _tmp / "reel.mp4"
vid.write_bytes(bytes(range(256)) * 7 + b"fin")
N = vid.stat().st_size


def ok_limite(n=3):
    return httpx.Response(200, json={"data": [{"quota_usage": n, "config": {"quota_total": 100, "quota_duration": 86400}}]})


async def main():
    print("\n[1] clés et registre")
    settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = "", ""
    check("1.1 sans clés : instagram indisponible", not settings.has_instagram and "instagram" not in marketing.auto_channels())
    settings.IG_ACCESS_TOKEN = TOK_FB
    check("1.1b un jeton sans l'id du compte pro : toujours indisponible (/<IG_ID>/media n'a pas de cible)",
          not settings.has_instagram and "instagram" not in marketing.auto_channels())
    settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = TOK_FB, "1789"
    check("1.2 jeton + id du compte pro posés (à chaud) : disponible", settings.has_instagram and "instagram" in marketing.auto_channels())
    _p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import app.main; "
                         "from app.services import publishers as P; print(sorted(P._REGISTRY))"],
                        cwd=str(racine / "backend"), capture_output=True, text=True,
                        env=dict(os.environ, DEEPOTUS_DATA_DIR=str(_tmp / "neuf")))
    check("1.3 l'application seule (import app.main) enregistre instagram", _p.returncode == 0
          and _p.stdout.strip().endswith("['instagram', 'telegram', 'x', 'youtube']"), (_p.stdout + _p.stderr)[-300:])
    check("1.4 sondage : 5 minutes au plus (doc : « no more than 5 minutes »), jamais une rafale",
          0 < sum(DELAIS) <= 300 and min(DELAIS) >= 10 and len(DELAIS) <= 8, str(DELAIS))
    lim = quota.LIMITS.get("instagram", ())
    check("1.5 quota local aligné sur la doc du jour : 100 / 24 h, source datée du 29/09", lim[:2] == ("day", 100)
          and "29/09/2026" in lim[2], str(lim))

    print("\n[2] un Reel publié (connexion Facebook)")
    rec.calls.clear()
    rec.script[:] = [ok_limite(),
                     httpx.Response(200, json={"id": "c1", "uri": "https://rupload.facebook.com/ig-api-upload/v25.0/c1"}),
                     httpx.Response(200, json={"success": True, "message": "Upload successful."}),
                     httpx.Response(200, json={"status_code": "IN_PROGRESS"}),
                     httpx.Response(200, json={"status_code": "FINISHED"}),
                     httpx.Response(200, json={"id": "media9"})]
    res = await ip.publish("Légende #reel", str(vid), None, {})
    check("2.1 publié, id du média rendu", res.ok and res.remote_id == "media9" and res.detail == "instagram: reel media9", str(res))
    c = rec.calls + [None] * 6
    lim_c, cont, up, s1, s2, pub = c[:6]
    check("2.2 D'ABORD le compteur d'Instagram (content_publishing_limit), sur graph.facebook.com v25.0",
          lim_c and lim_c.method == "GET" and lim_c.url.startswith("https://graph.facebook.com/v25.0/1789/content_publishing_limit"))
    f = cont.form() if cont else {}
    check("2.3 conteneur : REELS, résumable, légende, partagé au fil", cont and cont.method == "POST"
          and cont.url == "https://graph.facebook.com/v25.0/1789/media" and f.get("media_type") == "REELS"
          and f.get("upload_type") == "resumable" and f.get("caption") == "Légende #reel" and f.get("share_to_feed") == "true", str(f))
    check("2.4 envoi binaire vers l'uri rendue : OAuth, offset 0, file_size et Content-Length exacts, octet pour octet",
          up and up.method == "POST" and up.url == "https://rupload.facebook.com/ig-api-upload/v25.0/c1"
          and up.headers.get("authorization") == f"OAuth {TOK_FB}" and up.headers.get("offset") == "0"
          and up.headers.get("file_size") == str(N) and up.headers.get("content-length") == str(N) and up.body == vid.read_bytes(),
          str(up.headers if up else None))
    check("2.5 sondage du conteneur jusqu'à FINISHED, puis media_publish avec creation_id",
          s1 and s1.method == "GET" and s1.url.startswith("https://graph.facebook.com/v25.0/c1?") and s2
          and pub and pub.url == "https://graph.facebook.com/v25.0/1789/media_publish" and pub.form().get("creation_id") == "c1")

    print("\n[3] connexion Instagram : l'autre hôte")
    settings.IG_ACCESS_TOKEN = TOK_IG
    rec.calls.clear()
    rec.script[:] = [ok_limite(), httpx.Response(200, json={"id": "c2", "uri": "https://rupload.facebook.com/ig-api-upload/v25.0/c2"}),
                     httpx.Response(200, json={"success": True}), httpx.Response(200, json={"status_code": "FINISHED"}),
                     httpx.Response(200, json={"id": "media10"})]
    res = await ip.publish("x", str(vid), None, {})
    hotes = [httpx.URL(k.url).host for k in rec.calls]
    check("3.1 un jeton « IG… » (Business Login for Instagram) parle à graph.instagram.com, l'envoi reste sur rupload",
          res.ok and hotes == ["graph.instagram.com", "graph.instagram.com", "rupload.facebook.com", "graph.instagram.com",
                               "graph.instagram.com"], str(hotes))
    settings.IG_ACCESS_TOKEN = TOK_FB

    print("\n[4] refus parlants, jeton jamais montré")
    rec.calls.clear()
    rec.script[:] = [ok_limite(100)]
    res = await ip.publish("x", str(vid), None, {})
    check("4.1 compteur plein (100/100 sur 24 h glissantes) : refus AVANT le conteneur", not res.ok
          and "100/100" in res.detail and len(rec.calls) == 1, str(res))
    rec.script[:] = [ok_limite(), httpx.Response(400, json={"error": {"message": f"Invalid token {TOK_FB}"}})]
    res = await ip.publish("x", str(vid), None, {})
    check("4.2 conteneur 400 : statut dit, jeton masqué", not res.ok and res.detail.startswith("instagram container 400")
          and TOK_FB not in res.detail and "***" in res.detail, str(res))
    rec.script[:] = [ok_limite(), httpx.Response(200, json={"id": "c3"})]
    rec.calls.clear()
    res = await ip.publish("x", str(vid), None, {})
    check("4.3 conteneur sans uri d'envoi : refus, rien n'est envoyé dans le vide", not res.ok and "uri" in res.detail
          and len(rec.calls) == 2, str(res))
    rec.script[:] = [ok_limite(), httpx.Response(200, json={"id": "c4", "uri": "https://rupload.facebook.com/x/c4"}),
                     httpx.Response(200, json={"success": False, "debug_info": {"message": "bad"}})]
    res = await ip.publish("x", str(vid), None, {})
    check("4.4 envoi non accepté (success false) : refus", not res.ok and res.detail.startswith("instagram upload"), str(res))
    rec.script[:] = [ok_limite(), httpx.Response(200, json={"id": "c5", "uri": "https://rupload.facebook.com/x/c5"}),
                     httpx.Response(200, json={"success": True}),
                     httpx.Response(200, json={"status_code": "ERROR", "status": "Error: 2207026 format vidéo"})]
    res = await ip.publish("x", str(vid), None, {})
    check("4.5 conteneur ERROR : la raison d'Instagram remonte", not res.ok and "ERROR" in res.detail and "2207026" in res.detail, str(res))
    rec.calls.clear()
    rec.script[:] = ([ok_limite(), httpx.Response(200, json={"id": "c6", "uri": "https://rupload.facebook.com/x/c6"}),
                      httpx.Response(200, json={"success": True})]
                     + [httpx.Response(200, json={"status_code": "IN_PROGRESS"})] * len(DELAIS))
    res = await ip.publish("x", str(vid), None, {})
    check("4.6 jamais FINISHED : refus après le nombre de sondages prévu, pas un de plus, aucun media_publish",
          not res.ok and "FINISHED" in res.detail and len(rec.calls) == 3 + len(DELAIS)
          and not any("media_publish" in k.url for k in rec.calls), str((res, len(rec.calls))))
    rec.script[:] = [ok_limite(), httpx.Response(200, json={"id": "c7", "uri": "https://rupload.facebook.com/x/c7"}),
                     httpx.Response(200, json={"success": True}), httpx.Response(200, json={"status_code": "FINISHED"}),
                     httpx.Response(403, json={"error": {"message": "Application does not have permission"}})]
    res = await ip.publish("x", str(vid), None, {})
    check("4.7 media_publish 403 : dit", not res.ok and res.detail.startswith("instagram publish 403"), str(res))
    rec.calls.clear()
    res = await ip.publish("x", None, str(vid), {})
    check("4.8 pas de vidéo : refus SANS réseau (un Reel exige une vidéo)", not res.ok and "exige une vidéo" in res.detail
          and not rec.calls, str(res))
    rec.script[:] = [httpx.Response(500, text=f"panne {TOK_FB}")]
    res = await ip.publish("x", str(vid), None, {})
    check("4.9 compteur illisible : refus prudent, jeton masqué", not res.ok and TOK_FB not in res.detail
          and "content_publishing_limit" in res.detail, str(res))

    print("\n[5] insights")
    rec.calls.clear()
    rec.script[:] = [httpx.Response(200, json={"data": [{"name": "views", "values": [{"value": 500}]},
                                                        {"name": "likes", "values": [{"value": 20}]},
                                                        {"name": "shares", "total_value": {"value": 4}},
                                                        {"name": "saved", "values": [{"value": 2}]}]}),
                     httpx.Response(400, json={"error": {"message": "unsupported"}})]
    st = await ip.fetch_insights(["media9", "vieux"])
    check("5.1 views/likes/comments/shares/saved lus (values OU total_value), absent = 0 ; un média en erreur est omis",
          st == {"media9": {"views": 500, "likes": 20, "comments": 0, "shares": 4, "saves": 2}}, str(st))
    q = rec.calls[0].params() if rec.calls else {}
    check("5.2 les cinq métriques demandées existent pour les Reels (doc du 29/09)",
          q.get("metric") == "views,likes,comments,shares,saved", str(q))

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
