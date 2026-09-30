# -*- coding: utf-8 -*-
"""Métriques et tableau de bord (plan scheduler T7 — tâche #29, 30/09/2026). Passe = un fetcher par canal (faux ici),
une ligne post_metrics par (post, canal, passe), le DERNIER instantané gagne dans l'agrégat ; analytics par canal /
format / semaine ISO + top ; X rationné à 10 posts par passe ET à son budget MENSUEL de lectures (le plan oubliait le
mois : 10 par jour = ~300 lectures pour 100 au palier gratuit) ; les posts d'avant le socle (x_post_id sans
remote_ids) sont relus ; la colonne `metrics` garde le format BRUT de X que performance_context lit (le plan y
écrivait la forme normalisée : les plans générés auraient perdu leurs chiffres). Data-dir temporaire.
Témoin : la base aee2c94 n'a pas de metrics_service.
Run : & $PY tests/test_scheduler_metrics.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sqlite3, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmet_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_db = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_base = subprocess.run(["git", "ls-tree", "--name-only", "aee2c94", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base aee2c94")
check("0.1 TÉMOIN : pas de metrics_service.py", "quota.py" in _base and "metrics_service.py" not in _base)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
for _k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    setattr(settings, _k, "")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db, ScheduledPost, async_session_factory  # noqa: E402
from app.services import marketing, metrics_service as ms, quota    # noqa: E402

TICK, X_IDS = {"n": 0}, []


async def _yt(ids):
    TICK["n"] += 1
    return {i: {"views": 1000 * TICK["n"], "likes": 10, "comments": 2, "shares": 0, "saves": 0} for i in ids}


def _x_sync(ids):                                                   # remplace l'appel tweepy : format BRUT de X
    X_IDS.append(list(ids))
    return {i: {"impression_count": 300, "like_count": 5, "reply_count": 1, "retweet_count": 4, "quote_count": 0} for i in ids}


async def _panne(ids):
    raise RuntimeError("réseau coupé")

marketing._fetch_x_metrics_sync = _x_sync
# la passe n'interroge que les canaux DISPONIBLES : clés factices (aucun réseau : les deux fetchers sont remplacés)
settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = "banc"
settings.YOUTUBE_CLIENT_ID = settings.YOUTUBE_CLIENT_SECRET = settings.YOUTUBE_REFRESH_TOKEN = "banc"
FETCH_APP = dict(ms.FETCHERS)                                       # ce que l'application a enregistré
ms.FETCHERS.clear()
ms.FETCHERS["youtube"], ms.FETCHERS["x"] = _yt, FETCH_APP.get("x")


async def seed():
    now = datetime.utcnow()
    async with async_session_factory() as s:
        for i in range(12):
            legacy = i % 2 == 1                                     # un sur deux : publié AVANT le socle (x_post_id seul)
            s.add(ScheduledPost(id=f"p{i}", title=f"Post {i}", channels="x", run_at=now, status="posted",
                                posted_at=now - timedelta(days=i), format="image" if i % 2 else "seedance",
                                x_post_id=f"tw{i}", remote_ids=None if legacy else json.dumps({"x": f"tw{i}"})))
        s.add(ScheduledPost(id="y1", title="Short", channels="youtube", run_at=now, status="posted",
                            posted_at=now - timedelta(days=2), format="seedance", remote_ids=json.dumps({"youtube": "vid1"})))
        # non publié mais le PLUS RÉCENT et porteur d'un id X (repassé « ready » après un rejeu) : sans le filtre de
        # statut, il entrerait dans les 10
        s.add(ScheduledPost(id="d1", title="Brouillon", channels="x", run_at=now, status="ready", x_post_id="twD",
                            posted_at=now + timedelta(minutes=5)))
        await s.commit()


async def main():
    await init_db()
    await seed()
    print("\n[1] une passe")
    check("1.0 l'application enregistre un fetcher X (patron des adaptateurs)", callable(FETCH_APP.get("x")), str(FETCH_APP))
    counts = await ms.refresh_all(max_per_channel=10)
    check("1.1 X rationné à 10 posts par passe, YouTube 1", counts == {"youtube": 1, "x": 10}, str(counts))
    check("1.2 X : les 10 PLUS RÉCENTS, anciens posts (x_post_id sans remote_ids) compris, brouillon exclu",
          X_IDS and sorted(X_IDS[0]) == sorted(f"tw{i}" for i in range(10)), str(X_IDS[:1]))
    con = sqlite3.connect(_db)
    n_rows = con.execute("SELECT count(*) FROM post_metrics").fetchone()[0]
    raw_p1 = con.execute("SELECT metrics FROM scheduled_posts WHERE id='p1'").fetchone()[0]
    con.close()
    check("1.3 une ligne post_metrics par (post, canal)", n_rows == 11, str(n_rows))
    check("1.4 la colonne `metrics` garde le format BRUT de X (impression_count…)", raw_p1 and json.loads(raw_p1).get("impression_count") == 300, str(raw_p1))
    perf = await marketing.performance_context()
    check("1.5 performance_context (prompt des plans) lit TOUJOURS les chiffres", "impressions=300" in perf and "likes=5" in perf, perf[:200])

    print("\n[2] le dernier instantané gagne ; l'agrégat")
    await ms.refresh_all(max_per_channel=10)
    a = await ms.analytics(days=28)
    check("2.1 YouTube : le second instantané (2000 vues) remplace le premier, engagement = likes + 2×commentaires",
          a["channels"].get("youtube") == {"posts": 1, "views": 2000, "likes": 10, "comments": 2, "shares": 0, "saves": 0,
                                           "engagement": 14}, str(a["channels"].get("youtube")))
    check("2.2 X : 10 posts, normalisés (vues = impressions, partages = retweets), engagement 5 + 2 + 12 par post",
          a["channels"].get("x", {}).get("posts") == 10 and a["channels"]["x"]["views"] == 3000
          and a["channels"]["x"]["engagement"] == 10 * 19, str(a["channels"].get("x")))
    check("2.3 par format et par semaine ISO", set(a["formats"]) == {"image", "seedance"} and len(a["weeks"]) >= 2
          and all(w["week"][4:6] == "-W" for w in a["weeks"]), str(a["weeks"][:2]))
    check("2.4 top 5 trié par engagement", len(a["top"]) == 5 and a["top"][0]["engagement"] == 19
          and a["top"][0]["channel"] == "x" and a["items"] == sorted(a["items"], key=lambda d: -d["engagement"]))
    check("2.5 quotas et notes : X (lectures) et Telegram (aucune vue exposée par l'API Bot) sont DITS",
          "quotas" in a and "x" in a["notes"] and "telegram" in a["notes"] and "vue" in a["notes"]["telegram"])
    a7 = await ms.analytics(days=3)
    check("2.6 la fenêtre de jours filtre sur la date de publication", a7["channels"]["x"]["posts"] == 3, str(a7["channels"].get("x")))

    print("\n[3] le budget MENSUEL de lectures X")
    lim = quota.LIMITS.get("x_lecture", ())
    check("3.1 budget déclaré, daté, au mois", lim[:1] == ("month",) and lim[1] == 100 and "2026" in lim[2], str(lim))
    check("3.2 les deux passes ont compté 20 lectures", quota.used("x_lecture") == 20, str(quota.used("x_lecture")))
    quota.LIMITS["x_lecture"] = ("month", 25, "banc : 25 lectures/mois")
    X_IDS.clear()
    c3 = await ms.refresh_all(max_per_channel=10)
    c4 = await ms.refresh_all(max_per_channel=10)
    check("3.3 il reste 5 lectures : la passe n'en lit que 5, puis plus aucune (et YouTube continue)",
          c3.get("x") == 5 and "x" not in c4 and [len(x) for x in X_IDS] == [5] and c4.get("youtube") == 1, str((c3, c4, X_IDS)))
    a = await ms.analytics(days=28)
    check("3.4 budget épuisé : c'est DIT dans les notes du tableau de bord", "épuisé" in a["notes"].get("x", ""), a["notes"].get("x"))
    quota.LIMITS["x_lecture"] = ("month", 100, lim[2])

    print("\n[4] une panne n'arrête pas les autres canaux")
    ms.FETCHERS["youtube"] = _panne
    c5 = await ms.refresh_all(max_per_channel=10)
    check("4.1 YouTube en panne : X passe quand même, YouTube absent du compte", "youtube" not in c5 and c5.get("x") == 10, str(c5))
    ms.FETCHERS["youtube"] = _yt

    print("\n[4b] un canal sans clés n'est pas interrogé")
    settings.YOUTUBE_REFRESH_TOKEN = ""
    TICK["n"] = 0
    c6 = await ms.refresh_all(max_per_channel=10)
    check("4.2 YouTube déconnecté : pas d'appel, pas de compte", "youtube" not in c6 and TICK["n"] == 0, str(c6))
    settings.YOUTUBE_REFRESH_TOKEN = "banc"

    print("\n[5] la boucle quotidienne passe par le service")
    appels = []

    async def _espion(max_per_channel=10):
        appels.append(max_per_channel)
        return {}

    class _Stop(BaseException):
        pass

    async def _dort(_s):
        raise _Stop()
    vrai_refresh, vrai_sleep = ms.refresh_all, marketing.asyncio.sleep
    ms.refresh_all, marketing.asyncio.sleep = _espion, _dort
    try:
        await marketing.schedule_loop()
    except _Stop:
        pass
    finally:
        ms.refresh_all, marketing.asyncio.sleep = vrai_refresh, vrai_sleep
    check("5.1 schedule_loop lance la passe de métriques (10 par canal) ; refresh_x_metrics a disparu",
          appels == [10] and not hasattr(marketing, "refresh_x_metrics"), str(appels))

asyncio.run(main())

print("\n[6] les routes")
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    r = c.get("/api/schedule/analytics", params={"days": 28})
    check("6.1 GET /schedule/analytics", r.status_code == 200 and r.json()["channels"]["youtube"]["posts"] == 1, r.text[:200])
    q = c.get("/api/schedule/quotas").json()
    check("6.2 GET /schedule/quotas : publication ET lectures X", q.get("x", {}).get("limit") == 500
          and q.get("x_lecture", {}).get("limit") == 100, str(q)[:200])
    r = c.post("/api/schedule/analytics/refresh")
    check("6.3 POST /schedule/analytics/refresh : une passe manuelle, rationnée pareil", r.status_code == 200
          and r.json().get("x") == 10, r.text[:200])
    check("6.4 days borné (0 → 1 jour, pas une erreur)", c.get("/api/schedule/analytics", params={"days": 0}).json()["days"] == 1)

_p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import app.main; "
                     "from app.services import metrics_service as M; print(sorted(M.FETCHERS))"],
                    cwd=str(racine / "backend"), capture_output=True, text=True,
                    env=dict(os.environ, DEEPOTUS_DATA_DIR=str(_tmp / "neuf")))
_l = _p.stdout.strip().splitlines()
check("7.1 l'application seule (import app.main) enregistre les fetchers x, youtube, instagram, tiktok",
      _p.returncode == 0 and _l and {"x", "youtube", "instagram", "tiktok"} <= set(json.loads(_l[-1].replace("'", '"'))),
      (_p.stdout + _p.stderr)[-300:])

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
