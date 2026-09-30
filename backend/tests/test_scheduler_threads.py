# -*- coding: utf-8 -*-
"""Fils X (plan scheduler T15 — tâche #32 PR3, 30/09/2026) : la suite d'un post est un post lié (thread_of, thread_index,
fil PLAT à racine unique, canal x) ; elle part en RÉPONSE au message distant du précédent ; tant que le précédent n'est
pas publié, la suite est REPORTÉE (et le dit), jamais échouée ; un tour de boucle publie le fil dans l'ordre. Canal X
factice (aucun réseau), une seule boucle asynchrone, data-dir temporaire. Témoin : la base 28cccdd n'a pas de route de
suite.
Run : & $PY tests/test_scheduler_threads.py   (depuis backend/)"""
import asyncio, os, pathlib, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzfil_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_r = subprocess.run(["git", "show", "28cccdd:backend/app/api/routes.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 28cccdd")
check("0.1 TÉMOIN : pas de route /schedule/{id}/thread", _r and "/schedule/{post_id}/thread" not in _r)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
for _k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    setattr(settings, _k, "")
from httpx import AsyncClient, ASGITransport                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db                            # noqa: E402
from app.services import marketing, publishers                      # noqa: E402
from app.services.publishers import PublishResult                   # noqa: E402

VUS = []


async def _pub(caption, video, image, meta):
    VUS.append((caption, meta.get("reply_to")))
    return PublishResult(True, "x: ok", "r%d" % len(VUS))

publishers.register("x", lambda: True, _pub)                        # X factice : AUCUN réseau


async def main():
    await init_db()
    past = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"
    async with AsyncClient(transport=ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://test") as c:
        async def lignes():
            return {q["id"]: q for q in (await c.get("/api/schedule")).json()}

        p1 = (await c.post("/api/schedule", json={"title": "Tête", "caption": "1/ le début", "channels": ["x", "telegram"],
                                                  "run_at": past, "source_image": "s.png", "status": "scheduled",
                                                  "mode": "auto"})).json()["id"]
        print("\n[1] poser la suite")
        r = await c.post(f"/api/schedule/{p1}/thread", json={"caption": "2/ la suite"})
        j = r.json()
        p2 = j.get("id")
        check("1.1 la suite est liée à la tête (index 1), sur X seul, programmée, deux minutes après", j.get("thread_of") == p1
              and j.get("thread_index") == 1 and j.get("channels") == ["x"] and j.get("status") == "scheduled"
              and j.get("mode") == "auto", str(j)[:300])
        r = await c.post(f"/api/schedule/{p2}/thread", json={"caption": "3/ la fin"})
        j3 = r.json()
        p3 = j3.get("id")
        check("1.2 la suite d'une suite garde la MÊME racine (fil plat), index 2", j3.get("thread_of") == p1 and j3.get("thread_index") == 2, str(j3)[:200])
        check("1.3 post inconnu : 404 ; légende vide : 400",
              (await c.post("/api/schedule/inconnu/thread", json={"caption": "x"})).status_code == 404
              and (await c.post(f"/api/schedule/{p1}/thread", json={"caption": "  "})).status_code == 400)

        print("\n[2] l'ordre est garanti")
        res = (await c.post(f"/api/schedule/{p2}/fire")).json()
        rows = await lignes()
        check("2.1 la suite seule, précédent non publié : REPORTÉE (programmée, pas échouée), et c'est dit, rien n'est parti",
              res.get("status") == "scheduled" and VUS == [] and rows[p2]["status"] == "scheduled"
              and "attend" in (rows[p2]["error"] or "").lower(), str((res, rows[p2]["error"])))
        await c.post(f"/api/schedule/{p1}/fire")
        await c.post(f"/api/schedule/{p3}/fire")
        check("2.2 le 3e avant le 2e : reporté aussi (il répond au 2e, pas à la tête)", len(VUS) == 1
              and (await lignes())[p3]["status"] == "scheduled", str(VUS))
        await c.post(f"/api/schedule/{p2}/fire")
        await c.post(f"/api/schedule/{p3}/fire")
        check("2.3 chaque message répond au précédent : tête sans réponse, 2 → r1, 3 → r2",
              VUS == [("1/ le début", None), ("2/ la suite", "r1"), ("3/ la fin", "r2")], str(VUS))
        rows = await lignes()
        check("2.4 tout le fil publié, l'attente effacée", all(rows[i]["status"] == "posted" for i in (p1, p2, p3))
              and rows[p2]["error"] is None and rows[p3]["error"] is None, str({i: (rows[i]["status"], rows[i]["error"]) for i in (p2, p3)}))

        print("\n[3] un tour de boucle publie un fil entier dans l'ordre")
        VUS.clear()
        t1 = (await c.post("/api/schedule", json={"title": "Fil B", "caption": "B1", "channels": ["x"], "run_at": past,
                                                  "source_image": "s.png", "status": "scheduled", "mode": "auto"})).json()["id"]
        t2 = (await c.post(f"/api/schedule/{t1}/thread", json={"caption": "B2"})).json()["id"]
        import sqlite3
        con = sqlite3.connect(str(_tmp / "t.db"))
        con.execute("UPDATE scheduled_posts SET run_at = datetime('now', '-5 minutes') WHERE id=?", (t2,))   # la suite DUE avant la tête
        con.commit(); con.close()
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        check("3.1 même dus dans le désordre, la tête part d'abord et la suite lui répond", VUS == [("B1", None), ("B2", "r1")], str(VUS))

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
