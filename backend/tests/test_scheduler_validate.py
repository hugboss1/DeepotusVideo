# -*- coding: utf-8 -*-
"""Validation par lot (plan scheduler T10 — tâche #30, 30/09/2026) : la fenêtre (ou le plan) passe scheduled + auto +
validated_at ; un post SANS média est ignoré ET nommé (l'automatique n'envoie pas de texte nu) ; un contenu RÉELLEMENT
modifié après validation revient en attente (draft/assisted) — renvoyer la même valeur ou changer le statut seul ne
casse rien ; un tour de boucle (`tick`) publie le lot dû sur un canal factice, dans l'ordre des fils. Data-dir
temporaire, clés vidées : aucun réseau. Témoin : la base 09621e3 n'a ni route de validation ni tick.
Run : & $PY tests/test_scheduler_validate.py   (depuis backend/)"""
import asyncio, os, pathlib, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzval_"))
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
_r = subprocess.run(["git", "show", "09621e3:backend/app/api/routes.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
_m = subprocess.run(["git", "show", "09621e3:backend/app/services/marketing.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 09621e3")
check("0.1 TÉMOIN : ni /schedule/validate ni tick()", _r and "/schedule/validate" not in _r and "async def tick(" not in _m)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
for _k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
           "YOUTUBE_REFRESH_TOKEN", "IG_ACCESS_TOKEN", "TIKTOK_REFRESH_TOKEN"):
    setattr(settings, _k, "")
from httpx import AsyncClient, ASGITransport                      # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import marketing, publishers                      # noqa: E402
from app.services.publishers import PublishResult                   # noqa: E402

SENT = []


async def _ok(cap, v, i, m):
    SENT.append(cap)
    return PublishResult(True, "fakenet: ok", f"r{len(SENT)}")

publishers.register("fakenet", lambda: True, _ok)
iso = lambda d: d.isoformat() + "Z"                                 # noqa: E731

from app.services.storage import init_db                            # noqa: E402
import sqlite3                                                      # noqa: E402


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://test") as c:
        now = datetime.utcnow()

        async def mk(**k):
            return (await c.post("/api/schedule", json={"channels": ["fakenet"], **k})).json()["id"]

        async def lignes():
            return {p["id"]: p for p in (await c.get("/api/schedule")).json()}

        async def valider(**k):
            return await c.post("/api/schedule/validate", json=k)

        async def patch(pid, **k):
            return (await c.patch(f"/api/schedule/{pid}", json=k)).json()

        a = await mk(title="A", caption="a", run_at=iso(now + timedelta(hours=2)), source_image="s.png")
        b = await mk(title="B", caption="b", run_at=iso(now - timedelta(minutes=1)), job_id="job-x")
        n = await mk(title="Nu", caption="rien", run_at=iso(now + timedelta(hours=3)))
        far = await mk(title="Loin", caption="l", run_at="2030-01-01T10:00:00Z", source_image="s.png")
        pst = await mk(title="Déjà", caption="p", run_at=iso(now + timedelta(hours=1)), source_image="s.png", status="ready")

        print("\n[1] valider un lot")
        r = await valider(**{"from": iso(now - timedelta(days=1))})
        j = r.json()
        check("1.1 la fenêtre (défaut : +7 jours) valide les posts AVEC média, nomme le post nu, ignore le lointain et le « ready »",
              r.status_code == 200 and set(j.get("validated", [])) == {a, b}
              and j.get("skipped") == [{"id": n, "title": "Nu", "reason": "sans média"}], str(j))
        rows = await lignes()
        check("1.2 validé = scheduled + auto + validated_at ; le nu reste un brouillon ; le lointain intact",
              rows[a]["mode"] == "auto" and rows[a]["status"] == "scheduled" and rows[a]["validated_at"]
              and rows[n]["status"] == "draft" and rows[n]["validated_at"] is None and rows[far]["validated_at"] is None
              and rows[pst]["status"] == "ready", str({k: (v["status"], v["mode"], v["validated_at"]) for k, v in rows.items()}))
        check("1.3 la route rend les champs du plan (fils, séries, recyclage, qui a publié)",
              all(k in rows[a] for k in ("thread_of", "thread_index", "series_id", "recycled_from", "published_by")))
        check("1.4 bornes illisibles : 400", (await valider(**{"from": "hier"})).status_code == 400)

        print("\n[2] modifier après validation")
        r = await patch(a, caption="a")
        check("2.1 renvoyer la MÊME légende (formulaire enregistré tel quel) ne casse pas la validation",
              r["validated_at"] and r["mode"] == "auto" and r["status"] == "scheduled", str(r))
        r = await patch(b, status="scheduled")
        check("2.2 un changement de statut seul ne casse pas la validation", r["validated_at"] and r["mode"] == "auto", str(r))
        r = await patch(a, caption="a modifiée")
        check("2.3 contenu RÉELLEMENT modifié : retour en attente (draft, assisté, plus validé)",
              r["status"] == "draft" and r["mode"] == "assisted" and r["validated_at"] is None, str(r))
        await valider(**{"from": iso(now - timedelta(days=1))})
        r = await patch(a, run_at=iso(now + timedelta(hours=5)))
        check("2.4 déplacer l'heure est une modification de contenu", r["validated_at"] is None and r["status"] == "draft", str(r))

        print("\n[3] le plan entier")
        ids = [await mk(title=f"P{i}", caption="p", run_at="2031-01-0%dT10:00:00Z" % (i + 1), source_image="s.png") for i in range(2)]
        con = sqlite3.connect(str(_tmp / "t.db"))
        con.executemany("UPDATE scheduled_posts SET plan_id=? WHERE id=?", [("plan-banc", x) for x in ids])
        con.commit(); con.close()
        j = (await valider(plan_id="plan-banc")).json()
        check("3.1 plan_id : tout le plan, quelle que soit la date", set(j["validated"]) == set(ids), str(j))

        print("\n[4] un tour de boucle")
        t1 = await mk(title="Fil 2", caption="deux", run_at=iso(now - timedelta(minutes=3)), source_image="s.png")
        t0 = await mk(title="Fil 1", caption="un", run_at=iso(now - timedelta(minutes=2)), source_image="s.png")
        con = sqlite3.connect(str(_tmp / "t.db"))
        con.executemany("UPDATE scheduled_posts SET thread_of='fil', thread_index=? WHERE id=?", [(1, t1), (0, t0)])
        con.commit(); con.close()
        await valider(**{"from": iso(now - timedelta(days=1))})
        await marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")])
        rows = await lignes()
        check("4.1 le tick publie les posts validés DUS (b, le fil) ; a (pas encore dû) ne part pas",
              rows[b]["status"] == "posted" and rows[t0]["status"] == "posted" and rows[t1]["status"] == "posted"
              and rows[a]["status"] != "posted", str({k: rows[k]["status"] for k in (a, b, t0, t1)}))
        check("4.2 un fil part dans l'ordre de ses index, même si le 2e était prévu avant",
              "un" in SENT and "deux" in SENT and SENT.index("un") < SENT.index("deux"), str(SENT))
        check("4.3 chacun une seule fois", sorted(SENT) == sorted(["b", "un", "deux"]), str(SENT))

    print("\n[5] la boucle délègue au tick")
    appels = []

    async def _espion(marker=None):
        appels.append(list(marker) if marker is not None else None)

    class _Stop(BaseException):
        pass

    async def _dort(_s):
        raise _Stop()
    vrai_tick, vrai_sleep = marketing.tick, marketing.asyncio.sleep
    marketing.tick, marketing.asyncio.sleep = _espion, _dort
    try:
        await marketing.schedule_loop()
    except _Stop:
        pass
    finally:
        marketing.tick, marketing.asyncio.sleep = vrai_tick, vrai_sleep
    check("5.1 schedule_loop appelle tick() avec un marqueur qui survit d'un tour à l'autre", appels == [[None]], str(appels))

asyncio.run(main())

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
