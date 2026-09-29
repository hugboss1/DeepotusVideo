# -*- coding: utf-8 -*-
"""Socle du Scheduler (plan scheduler T1 — tâche #24, 29/09/2026) : les colonnes neuves de scheduled_posts posées par
auto-ALTER sur une base d'AVANT (ligne ancienne intacte), les tables post_metrics / campaign_briefs / post_series
créées. Banc-miroir : il lit PRAGMA table_info et la base, jamais le modèle. Témoin : la base 37187a6 n'a rien de tout ça.
Run : & $PY tests/test_scheduler_socle.py   (depuis backend/)"""
import asyncio, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsoc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_db = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from app.services.storage import init_db                            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
vieux = subprocess.run(["git", "show", "37187a6:backend/app/services/storage.py"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 37187a6")
check("0.1 TÉMOIN : ni remote_ids ni post_metrics", vieux and "remote_ids" not in vieux and "post_metrics" not in vieux)

# la forme EXACTE de scheduled_posts avant ce plan (v1.27) : c'est sur elle que l'auto-ALTER doit poser le neuf
LEGACY = ("CREATE TABLE scheduled_posts (id VARCHAR(36) PRIMARY KEY, title VARCHAR(200),"
          " caption TEXT, channels VARCHAR(120), run_at DATETIME, status VARCHAR(20),"
          " mode VARCHAR(12), job_id VARCHAR(36), format VARCHAR(20), hook TEXT,"
          " script_idea TEXT, image_idea TEXT, plan_id VARCHAR(36), error TEXT,"
          " created_at DATETIME, posted_at DATETIME, x_post_id VARCHAR(40), metrics TEXT,"
          " source_image VARCHAR(255), brief TEXT)")
NEUVES = {"remote_ids": "TEXT", "validated_at": "DATETIME", "thread_of": "VARCHAR(36)", "thread_index": "INTEGER",
          "series_id": "VARCHAR(36)", "recycled_from": "VARCHAR(36)", "published_by": "VARCHAR(40)"}


def cols(table):
    con = sqlite3.connect(_db)
    try:
        return {r[1]: r[2] for r in con.execute(f"PRAGMA table_info({table})")}
    finally:
        con.close()


async def main():
    con = sqlite3.connect(_db)
    con.execute(LEGACY)
    con.execute("INSERT INTO scheduled_posts (id,title,channels,run_at,status,mode,x_post_id)"
                " VALUES ('old1','ancien','x','2026-09-01 10:00:00','posted','assisted','1790')")
    con.commit(); con.close()
    await init_db()
    await init_db()                                                 # deux démarrages : l'ALTER ne se rejoue pas

    print("\n[1] scheduled_posts : l'auto-ALTER sur une base d'avant")
    sp = cols("scheduled_posts")
    check("1.1 les sept colonnes neuves sont posées, avec leur type", all(sp.get(c) == t for c, t in NEUVES.items()),
          str({c: sp.get(c) for c in NEUVES}))
    con = sqlite3.connect(_db)
    r = con.execute("SELECT title, x_post_id, remote_ids, validated_at FROM scheduled_posts WHERE id='old1'").fetchone()
    con.close()
    check("1.2 la ligne ancienne est intacte, ses colonnes neuves à NULL (pas d'id distant inventé)",
          r == ("ancien", "1790", None, None), str(r))

    print("\n[2] les trois tables neuves")
    pm = cols("post_metrics")
    check("2.1 post_metrics : un instantané par (post, canal, date) et ses cinq compteurs",
          {"id", "post_id", "channel", "remote_id", "fetched_at", "views", "likes", "comments", "shares", "saves", "raw"} <= set(pm),
          str(sorted(pm)))
    check("2.2 l'engagement est CALCULÉ, jamais stocké", "engagement" not in pm)
    cb = cols("campaign_briefs")
    check("2.3 campaign_briefs : objectif, dates, messages, termes interdits, rubriques, actif",
          {"id", "name", "objective", "start_date", "end_date", "messages", "forbidden", "rubrics", "active", "updated_at"} <= set(cb),
          str(sorted(cb)))
    ps = cols("post_series")
    check("2.4 post_series : jours, heure locale, canaux, format, gabarit de légende, actif",
          {"id", "name", "weekdays", "time", "channels", "format", "caption_template", "active", "created_at"} <= set(ps),
          str(sorted(ps)))
    con = sqlite3.connect(_db)
    idx = {r[1] for r in con.execute("PRAGMA index_list(post_metrics)")}
    con.close()
    check("2.5 post_metrics indexé par post et par canal (la passe quotidienne les relit)",
          any("post_id" in i for i in idx) and any("channel" in i for i in idx), str(idx))

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
