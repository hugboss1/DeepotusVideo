# -*- coding: utf-8 -*-
"""Registre des adaptateurs + quotas vérifiés (plan scheduler T2 — tâche #24, 29/09/2026).
Un canal factice « fakenet » plafonné à 2/jour : fire_post itère le registre, écrit remote_ids par canal, refuse au
quota avec un message qui NOMME la source, ne republie jamais un canal déjà parti, ne compte que les succès. X et
Telegram passent par le même registre (publish_x / publish_telegram remplacés au banc : AUCUN réseau) ; le data-dir
est temporaire et les clés vidées, pour qu'aucune clé réelle ne puisse publier. On lit la base, le fichier de
quotas et la route — jamais le code. Témoin : la base 37187a6 n'a ni registre ni quotas.
Run : & $PY tests/test_scheduler_publish.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sqlite3, subprocess, sys, tempfile
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpub_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_db = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
for _k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    setattr(settings, _k, "")                                       # aucune clé réelle ne doit pouvoir publier

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_base = subprocess.run(["git", "ls-tree", "--name-only", "37187a6", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 37187a6")
check("0.1 TÉMOIN : ni publishers.py ni quota.py", "services/marketing.py" in _base
      and "publishers.py" not in _base and "quota.py" not in _base)

from httpx import AsyncClient, ASGITransport                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db                            # noqa: E402
from app.services import marketing, publishers, quota               # noqa: E402
from app.services.publishers import PublishResult                   # noqa: E402

QF = _tmp / "scheduler" / "quota.json"
check("0.2 le fichier de quotas vit sous le data-dir", quota._FILE == QF, str(quota._FILE))
quota.LIMITS["fakenet"] = ("day", 2, "banc : 2 par jour")
CALLS, MODE = [], {"v": "ok"}


async def _fake(caption, video, image, meta):
    CALLS.append((caption, meta.get("title")))
    if MODE["v"] == "leve":
        raise RuntimeError("réseau coupé")
    if MODE["v"] == "refus":
        return PublishResult(False, "fakenet 403: refusé")
    return PublishResult(True, f"fakenet: ok {len(CALLS)}", f"rid-{len(CALLS)}")

publishers.register("fakenet", lambda: True, _fake)
X_CALLS, TG_CALLS = [], []


async def _faux_x(caption, *, video_path=None, image_path=None, retries=2, reply_to=None):
    X_CALLS.append((caption, reply_to))
    return True, "tweet 1790", "1790"


async def _faux_tg(caption, *, video_path=None, image_path=None):
    TG_CALLS.append(caption)
    return True, "sent"


def jour():
    return datetime.utcnow().strftime("%Y-%m-%d")


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async def poster(**kw):
            body = {"title": "T", "caption": "salut", "channels": ["fakenet"], "run_at": "2026-09-10T10:00:00Z",
                    "status": "scheduled", "mode": "auto"}
            body.update(kw)
            return (await c.post("/api/schedule", json=body)).json()["id"]

        async def ligne(pid):
            return next(p for p in (await c.get("/api/schedule")).json() if p["id"] == pid)

        print("\n[1] le registre")
        ac = marketing.auto_channels()
        check("1.1 auto_channels = les adaptateurs enregistrés ET disponibles : fakenet oui ; x, telegram non (clés vides) ; "
              "instagram non (aucun adaptateur)", "fakenet" in ac and not ({"x", "telegram", "instagram"} & ac), str(ac))

        print("\n[2] fire_post itère le registre")
        pid = await poster(title="T1", channels=["fakenet", "instagram"])
        res = await marketing.fire_post(pid)
        check("2.1 publié sur fakenet, instagram reste assisté et c'est dit", res.get("ok") and res.get("status") == "posted"
              and res.get("sent") == ["fakenet: ok 1"] and res.get("pending") == ["instagram: assisted (no auto adapter)"], str(res))
        check("2.2 l'adaptateur reçoit la légende et le titre du post", CALLS[:1] == [("salut", "T1")], str(CALLS))
        r = await ligne(pid)
        check("2.3 remote_ids par canal, lu par la route", r.get("remote_ids") == {"fakenet": "rid-1"}, str(r.get("remote_ids")))
        check("2.4 x_post_id n'est pas touché par un autre canal", r.get("x_post_id") is None)

        print("\n[3] le rejeu ne republie jamais un canal déjà parti")
        await c.patch(f"/api/schedule/{pid}", json={"status": "scheduled"})
        res = await marketing.fire_post(pid)
        check("3.1 fakenet : « déjà publié (rid-1) », aucun second appel", res.get("sent") == ["fakenet: déjà publié (rid-1)"]
              and len(CALLS) == 1, str(res))
        check("3.2 le rejeu ne compte pas au quota", json.loads(QF.read_text("utf-8"))["fakenet"] == {jour(): 1})

        print("\n[4] le quota : vérifié AVANT, compté APRÈS, refus parlant")
        q1 = await poster(title="Q1")
        r1 = await marketing.fire_post(q1)
        q2 = await poster(title="Q2")
        r2 = await marketing.fire_post(q2)
        check("4.1 le 2e succès passe (2/2)", r1.get("ok"), str(r1))
        check("4.2 le 3e est refusé AVANT l'appel, message qui nomme le plafond et sa source",
              not r2.get("ok") and r2.get("pending") == ["quota fakenet : 2/2 — banc : 2 par jour"] and len(CALLS) == 2, str(r2))
        check("4.3 un post refusé repasse « ready » (publiable à la main), l'erreur est gardée",
              r2.get("status") == "ready" and "quota fakenet" in ((await ligne(q2)).get("error") or ""))
        check("4.4 le fichier de quotas dit 2 pour aujourd'hui (jour UTC)", json.loads(QF.read_text("utf-8"))["fakenet"] == {jour(): 2})

        print("\n[5] un échec n'est jamais compté")
        quota.LIMITS["fakenet"] = ("day", 10, "banc : 10 par jour")
        MODE["v"] = "refus"
        e1 = await marketing.fire_post(await poster(title="E1"))
        MODE["v"] = "leve"
        e2 = await marketing.fire_post(await poster(title="E2"))
        check("5.1 un refus de l'adaptateur remonte tel quel", e1.get("pending") == ["fakenet 403: refusé"], str(e1))
        check("5.2 une exception devient un échec lisible, jamais un crash de fire_post",
              e2.get("pending") == ["fakenet error: réseau coupé"] and e2.get("status") == "ready", str(e2))
        check("5.3 ni l'un ni l'autre n'est compté", json.loads(QF.read_text("utf-8"))["fakenet"] == {jour(): 2})
        MODE["v"] = "ok"

        print("\n[6] X et Telegram passent par le même registre")
        marketing.publish_x, marketing.publish_telegram = _faux_x, _faux_tg
        settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = "banc"
        settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID = "1:banc", "-100"
        check("6.0 les clés posées à chaud rendent x et telegram disponibles (disponible() relu à chaque appel)",
              {"x", "telegram"} <= marketing.auto_channels())
        px = await poster(title="X1", caption="pour X", channels=["x", "telegram"],
                          brief={"tg_caption": "pour Telegram"})
        rx = await marketing.fire_post(px)
        lx = await ligne(px)
        check("6.1 X : x_post_id ET remote_ids.x synchronisés", lx.get("x_post_id") == "1790"
              and lx.get("remote_ids") == {"x": "1790"}, str(lx.get("remote_ids")))
        check("6.2 Telegram reçoit la tg_caption du brief, X la légende", TG_CALLS == ["pour Telegram"]
              and X_CALLS == [("pour X", None)] and rx.get("sent") == ["x: tweet 1790", "telegram: sent"], str(rx))
        qd = json.loads(QF.read_text("utf-8"))
        check("6.3 X est compté au MOIS, Telegram (sans plafond publié) ne l'est pas",
              qd.get("x") == {datetime.utcnow().strftime("%Y-%m"): 1} and "telegram" not in qd, str(qd))

        print("\n[7] la route et les fils X")
        con = sqlite3.connect(_db)
        con.execute("UPDATE scheduled_posts SET remote_ids='{pas du json' WHERE id=?", (px,))
        con.commit(); con.close()
        check("7.1 un remote_ids illisible rend None, jamais un 500", (await ligne(px)).get("remote_ids", "absent") is None)

    captured = {}

    class _Cli:
        def create_tweet(self, **kw):
            captured.update(kw)
            return type("R", (), {"data": {"id": "42"}})()
    marketing._x_client = lambda: _Cli()
    r = marketing._publish_x_sync("fil", None, None, reply_to="99")
    check("7.2 _publish_x_sync transmet reply_to à create_tweet (in_reply_to_tweet_id), pour les fils X de T15",
          r == (True, "tweet 42", "42") and captured.get("in_reply_to_tweet_id") == "99" and captured.get("text") == "fil",
          str((r, captured)))
    s = quota.summary()
    check("7.3 summary : plafond, période et source datée pour chaque canal plafonné",
          all({"used", "limit", "period", "source"} <= set(v) for v in s.values())
          and {"x", "instagram", "youtube", "tiktok"} <= set(s) and all("/2026)" in s[k]["source"] for k in ("x", "instagram", "youtube", "tiktok")), str(s)[:300])

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
