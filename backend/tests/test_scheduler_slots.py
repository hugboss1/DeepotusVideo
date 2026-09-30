# -*- coding: utf-8 -*-
"""Créneaux par canal (plan scheduler T8 — tâche #30, 30/09/2026) : défauts, sauvegarde bornée (HH:MM, canaux connus,
fuseau), affectation k-ième post du jour → k-ième créneau de son PREMIER canal, proposition d'horaire d'après les
métriques (≥ 5 posts mesurés par canal, sinon rien), routes, et le plan généré qui prend les créneaux. On lit le fichier
écrit et les réponses, jamais le code. Data-dir temporaire. Témoin : la base 09621e3 n'a pas de schedule_slots.
Run : & $PY tests/test_scheduler_slots.py   (depuis backend/)"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzslot_"))
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
_base = subprocess.run(["git", "ls-tree", "--name-only", "09621e3", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 09621e3")
check("0.1 TÉMOIN : metrics_service.py oui, schedule_slots.py non", "metrics_service.py" in _base and "schedule_slots.py" not in _base)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.PLANNER_PROVIDER = ""
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OLLAMA_MODEL"):
    setattr(settings, _k, "")                                       # le plan déterministe : aucun LLM, aucune dépense
from app.services import schedule_slots as SL                       # noqa: E402

F = _tmp / "scheduler" / "slots.json"
print("\n[1] défauts et sauvegarde")
check("1.1 le fichier vit sous le data-dir", SL._FILE == F, str(SL._FILE))
d = SL.load()
check("1.2 défauts pour les CINQ canaux, fuseau 0 tant que rien n'est posé",
      d.get("x") == ["08:30", "13:00", "19:30"] and set(d) >= {"x", "telegram", "instagram", "youtube", "tiktok"}
      and SL.tz_offset() == 0, str(d))
s = SL.save({"x": ["25:00", "07:00", "07:00", "7:5"], "tiktok": ["20:15", "09:00"], "bidon": ["10:00"], "_tz": -120,
             "youtube": "09:00"})
disque = json.loads(F.read_text("utf-8"))
check("1.3 heures invalides écartées, doublons fusionnés, triées ; canal inconnu refusé ; une chaîne n'est pas une liste",
      s["x"] == ["07:00"] and s["tiktok"] == ["09:00", "20:15"] and "bidon" not in s and "bidon" not in disque
      and s["youtube"] == ["09:30", "19:00"], str(s))
check("1.4 le fuseau (getTimezoneOffset du navigateur) est gardé", SL.tz_offset() == -120 and disque.get("_tz") == -120)
s = SL.save({"x": ["25:00"]})
check("1.5 un canal dont TOUTES les heures sont invalides revient à ses défauts (jamais une liste vide)",
      s["x"] == ["08:30", "13:00", "19:30"], str(s["x"]))
F.write_text("{pas du json", "utf-8")
check("1.6 fichier illisible : défauts, pas d'exception", SL.load()["x"] == ["08:30", "13:00", "19:30"] and SL.tz_offset() == 0)

print("\n[2] affectation")
posts = [{"day_offset": 0, "channels": ["x"]}, {"day_offset": 0, "channels": ["x", "telegram"]},
         {"day_offset": 1, "channels": ["youtube"]}, {"day_offset": 0, "channels": ["x"]}, {"day_offset": 0}]
SL.assign(posts, {"x": ["07:00", "12:00"], "youtube": ["09:30"]})
check("2.1 k-ième post du jour sur son premier canal → k-ième créneau, en boucle ; sans canal = X",
      [p["time"] for p in posts] == ["07:00", "12:00", "09:30", "07:00", "12:00"], str([p["time"] for p in posts]))

print("\n[3] proposition d'horaire")
items = ([{"channel": "x", "posted_at": "2026-09-01T17:00:00Z", "engagement": 50}] * 3
         + [{"channel": "x", "posted_at": "2026-09-02T06:10:00Z", "engagement": 5}] * 3
         + [{"channel": "youtube", "posted_at": "2026-09-01T08:00:00Z", "engagement": 9}] * 2)
sug = SL.suggest(items, tz_offset_minutes=-120)
check("3.1 X : la demi-heure LOCALE (UTC+2) au meilleur engagement moyen ; YouTube : moins de 5 posts → rien",
      sug == {"x": "19:00", "youtube": None}, str(sug))
sug = SL.suggest([{"channel": "x", "posted_at": "2026-09-01T17:40:00Z", "engagement": 1}] * 5, tz_offset_minutes=0)
check("3.2 17:40 tombe dans la demi-heure 17:30", sug == {"x": "17:30"}, str(sug))
sug = SL.suggest([{"channel": "x", "posted_at": "pas une date", "engagement": 9}] * 9)
check("3.3 dates illisibles ignorées, pas d'exception", sug == {}, str(sug))

print("\n[4] routes et plan")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    r = c.put("/api/schedule/slots", json={"x": ["06:45", "21:00"], "_tz": -60})
    check("4.1 PUT /schedule/slots enregistre et rend le résultat nettoyé", r.status_code == 200
          and r.json()["x"] == ["06:45", "21:00"] and SL.tz_offset() == -60, r.text[:200])
    g = c.get("/api/schedule/slots").json()
    check("4.2 GET /schedule/slots relit le fichier", g["x"] == ["06:45", "21:00"] and g["tiktok"] == ["12:00", "19:00"], str(g))
    r = c.get("/api/schedule/slots/suggest", params={"days": 56})
    check("4.3 GET /schedule/slots/suggest : aucune métrique → rien à proposer, et les créneaux actuels",
          r.status_code == 200 and r.json()["suggested"] == {} and r.json()["slots"]["x"] == ["06:45", "21:00"], r.text[:200])
    r = c.post("/api/marketing/plan", json={"prompt": "lancement", "days": 2, "posts_per_day": 2, "channels": ["x"]})
    heures = [p["time"] for p in r.json().get("posts", [])] if r.status_code == 200 else []
    check("4.4 un plan généré prend les créneaux de son canal (2 posts/jour → 06:45 puis 21:00)",
          heures == ["06:45", "21:00", "06:45", "21:00"], r.text[:300])
    r = c.post("/api/marketing/plan", json={"prompt": "lancement", "days": 1, "posts_per_day": 1, "channels": ["x"],
                                            "use_slots": False})
    check("4.5 use_slots=false : les heures du planificateur sont gardées", r.status_code == 200
          and r.json()["posts"][0]["time"] not in ("06:45", "21:00"), r.text[:300])

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
