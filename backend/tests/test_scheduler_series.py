# -*- coding: utf-8 -*-
"""Séries récurrentes (plan scheduler T14 — tâche #32 PR2, 30/09/2026) : une série pose des BROUILLONS aux jours et à
l'heure LOCALE dits, jamais deux fois le même créneau (rejouer est sans effet), le gabarit de légende reçoit la date,
le jour et la semaine ; supprimer la règle garde les posts posés ; jours ou heure invalides refusés en le disant. On
relit les posts par l'API. Une seule boucle asynchrone, data-dir temporaire. Témoin : la base b5fe5e1 n'a pas de série.
Run : & $PY tests/test_scheduler_series.py   (depuis backend/)"""
import asyncio, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzser_"))
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
_base = subprocess.run(["git", "ls-tree", "--name-only", "b5fe5e1", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base b5fe5e1")
check("0.1 TÉMOIN : pas de series_service.py", "schedule_slots.py" in _base and "series_service.py" not in _base)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db                            # noqa: E402


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://test") as c:
        async def de_la_serie(sid):
            return [p for p in (await c.get("/api/schedule")).json() if p["series_id"] == sid]

        print("\n[1] créer")
        check("1.1 aucune série : liste vide", (await c.get("/api/schedule/series")).json() == [])
        r = await c.post("/api/schedule/series", json={"name": "Coulisses", "weekdays": "3, 0,3", "time": "9:30",
                                                        "channels": ["x", "telegram"], "format": "image",
                                                        "caption_template": "Coulisses du {date} — {weekday} ({week})"})
        j = r.json()
        sid = j.get("id")
        check("1.2 jours normalisés (triés, sans doublon), heure normalisée, canaux", j.get("weekdays") == "0,3"
              and j.get("time") == "09:30" and j.get("channels") == ["x", "telegram"], str(j))
        for corps, champ in (({"name": "x", "weekdays": "9"}, "0-6"), ({"name": "x", "weekdays": ""}, "au moins un jour"),
                             ({"name": "x", "weekdays": "lundi"}, "weekdays"), ({"name": "x", "weekdays": "1", "time": "25:00"}, "heure")):
            r = await c.post("/api/schedule/series", json=corps)
            check(f"1.3 refusé en le disant : {corps}", r.status_code == 400 and champ in r.json().get("detail", ""), r.text[:200])

        print("\n[2] matérialiser")
        # 2026-09-07 est un lundi : 2 semaines -> lundi 07, jeudi 10, lundi 14, jeudi 17 ; fuseau UTC+2 (offset -120)
        corps = {"weeks": 2, "start_date": "2026-09-07", "tz_offset_minutes": -120}
        r = await c.post(f"/api/schedule/series/{sid}/materialize", json=corps)
        posts = await de_la_serie(sid)
        check("2.1 quatre brouillons posés", r.json() == {"created": 4, "skipped": 0} and len(posts) == 4, r.text[:200])
        check("2.2 à l'heure LOCALE convertie en UTC (09:30 à UTC+2 = 07:30Z)", sorted(p["run_at"] for p in posts) == [
            "2026-09-07T07:30:00Z", "2026-09-10T07:30:00Z", "2026-09-14T07:30:00Z", "2026-09-17T07:30:00Z"],
            str(sorted(p["run_at"] for p in posts)))
        check("2.3 des BROUILLONS assistés : rien ne part sans la validation par lot", all(p["status"] == "draft"
              and p["mode"] == "assisted" and p["validated_at"] is None for p in posts))
        check("2.4 canaux et format de la série", all(p["channels"] == ["x", "telegram"] and p["format"] == "image" for p in posts))
        check("2.5 le gabarit reçoit la date, le jour et la semaine ISO", "Coulisses du 2026-09-10 — jeudi (2026-W37)"
              in [p["caption"] for p in posts], str([p["caption"] for p in posts]))
        r = await c.post(f"/api/schedule/series/{sid}/materialize", json=corps)
        check("2.6 rejouer ne duplique rien", r.json() == {"created": 0, "skipped": 4} and len(await de_la_serie(sid)) == 4, r.text[:200])
        r = await c.post(f"/api/schedule/series/{sid}/materialize", json={"weeks": 1, "start_date": "2026-09-09",
                                                                            "tz_offset_minutes": -120})
        check("2.7 un départ en milieu de semaine ne pose rien AVANT lui (mercredi 09 → seul le jeudi 10, déjà posé)",
              r.json() == {"created": 0, "skipped": 1}, r.text[:200])
        check("2.8 série inconnue : 404", (await c.post("/api/schedule/series/inconnue/materialize", json=corps)).status_code == 404)
        check("2.9 date de départ illisible : 400", (await c.post(f"/api/schedule/series/{sid}/materialize",
                                                                  json={"start_date": "hier"})).status_code == 400)

        print("\n[3] supprimer la règle")
        r = await c.delete(f"/api/schedule/series/{sid}")
        check("3.1 la série est retirée, ses brouillons RESTENT", r.json() == {"deleted": sid}
              and (await c.get("/api/schedule/series")).json() == [] and len(await de_la_serie(sid)) == 4, r.text[:200])
        check("3.2 série inconnue : 404 (pas un DELETE de post)", (await c.delete("/api/schedule/series/inconnue")).status_code == 404)
        check("3.3 une série retirée ne se matérialise plus", (await c.post(f"/api/schedule/series/{sid}/materialize", json=corps)).status_code == 404)

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
