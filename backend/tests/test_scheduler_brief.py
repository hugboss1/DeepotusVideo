# -*- coding: utf-8 -*-
"""Brief de campagne persistant (plan scheduler T13 — tâche #32 PR2, 30/09/2026) : un seul actif, relu par le plan ;
l'objectif, la fenêtre, les messages et les rubriques entrent dans le prompt ; les INTERDITS sont dits au modèle ET
retirés de la sortie (légendes, hashtags…), et le plan rend la liste de ce qui a dû être retiré. Écart au plan : le
retrait respecte les LIMITES DE MOT (interdire « garanti » ne mutile pas « garantie » en « e »). Plan déterministe (aucun
LLM, aucune dépense), une seule boucle asynchrone, data-dir temporaire. Témoin : la base b5fe5e1 n'a pas de brief.
Run : & $PY tests/test_scheduler_brief.py   (depuis backend/)"""
import asyncio, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzbrief_"))
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
_m = subprocess.run(["git", "show", "b5fe5e1:backend/app/services/marketing.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base b5fe5e1")
check("0.1 TÉMOIN : ni active_brief ni apply_forbidden", _m and "def active_brief" not in _m and "def apply_forbidden" not in _m)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.PLANNER_PROVIDER = ""
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OLLAMA_MODEL"):
    setattr(settings, _k, "")                                       # plan déterministe
from httpx import AsyncClient, ASGITransport                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db                            # noqa: E402
from app.services import marketing                                  # noqa: E402

PROMPTS = []


async def _faux_moteur(full_prompt, days, ppd, channels, language, persona):
    """Remplace le moteur Ollama : enregistre le prompt REÇU et « insiste » sur les interdits (aucun réseau)."""
    PROMPTS.append(full_prompt)
    return [{"day_offset": d, "time": "09:00", "title": f"P{d}", "channels": ["x"], "format": "image",
             "caption": f"gain garanti #1000x jour {d}", "hashtags": "#1000x #SOL", "hook": "garanti"} for d in range(days)]


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://test") as c:
        print("\n[1] le brief")
        r = await c.get("/api/marketing/brief")
        check("1.1 aucun brief : null", r.status_code == 200 and r.json() is None, r.text[:100])
        r = await c.put("/api/marketing/brief", json={
            "name": "Mint de septembre", "objective": "faire connaître le mint",
            "start_date": "2026-09-05", "end_date": "2026-09-30",
            "messages": "le mint ouvre le 12\nles missions donnent des places\n\n",
            "forbidden": "#1000x\ngaranti", "rubrics": "lundi : coulisses\nvendredi : démo"})
        j = r.json()
        check("1.2 PUT : le brief actif est rendu, une ligne par entrée (lignes vides écartées)",
              j.get("name") == "Mint de septembre" and j.get("active") == 1
              and j.get("messages") == ["le mint ouvre le 12", "les missions donnent des places"]
              and j.get("forbidden") == ["#1000x", "garanti"] and j.get("rubrics", [None])[0] == "lundi : coulisses", str(j))
        check("1.3 PUT sans nom : 400", (await c.put("/api/marketing/brief", json={"objective": "x"})).status_code == 400)
        b = await marketing.active_brief()
        ctx = marketing.brief_context(b)
        check("1.4 le contexte du prompt : objectif, fenêtre, messages, rubriques ET interdits DITS au modèle",
              all(x in ctx for x in ("faire connaître le mint", "2026-09-05", "2026-09-30", "le mint ouvre le 12",
                                     "vendredi : démo", "#1000x", "garanti")), ctx)
        check("1.5 pas de brief : contexte vide", marketing.brief_context(None) == "")

        print("\n[2] retirer les interdits")
        posts, retires = marketing.apply_forbidden(
            [{"caption": "gain GARANTI #Deepotus #1000x", "hashtags": "#1000x #SOL", "tg_caption": "garanti !"},
             {"caption": "rien à retirer, une garantie reste une garantie", "hashtags": "#SOL #1000xyz"}], b["forbidden"])
        check("2.1 retirés sans égard à la casse, espaces resserrés", posts[0]["caption"] == "gain #Deepotus"
              and posts[0]["hashtags"] == "#SOL" and posts[0]["tg_caption"] == "!", str(posts[0]))
        check("2.2 LIMITES DE MOT : « garantie » et « #1000xyz » ne sont pas mutilés (écart au plan)",
              posts[1]["caption"] == "rien à retirer, une garantie reste une garantie" and posts[1]["hashtags"] == "#SOL #1000xyz",
              str(posts[1]))
        check("2.3 la liste de ce qui a dû être retiré", sorted(retires) == ["#1000x", "garanti"], str(retires))

        print("\n[3] le plan lit le brief")
        vrai, settings.OLLAMA_MODEL = marketing._PLAN_PROVIDERS["ollama"], "banc"
        marketing._PLAN_PROVIDERS["ollama"] = _faux_moteur
        try:
            plan = (await c.post("/api/marketing/plan", json={"prompt": "semaine de lancement", "days": 2,
                                                              "posts_per_day": 1, "channels": ["x"]})).json()
        finally:
            marketing._PLAN_PROVIDERS["ollama"], settings.OLLAMA_MODEL = vrai, ""
        sortie = " ".join((p.get("caption") or "") + " " + (p.get("hashtags") or "") + " " + (p.get("hook") or "")
                          for p in plan.get("posts", []))
        check("3.1 le prompt REÇU par le planificateur porte le brief (objectif, messages, interdits)",
              PROMPTS and "semaine de lancement" in PROMPTS[0] and "faire connaître le mint" in PROMPTS[0]
              and "NEVER" in PROMPTS[0] and "#1000x" in PROMPTS[0], str(PROMPTS)[:300])
        check("3.2 le modèle insiste : les interdits sont RETIRÉS de sa sortie (légende, hashtags, accroche)",
              plan.get("posts") and "#1000x" not in sortie and "garanti" not in sortie.lower(), sortie[:200])
        check("3.3 le plan porte le nom du brief et la liste des termes retirés", plan.get("engine") == "ollama"
              and plan.get("campaign_brief") == "Mint de septembre" and sorted(plan.get("removed") or []) == ["#1000x", "garanti"],
              str({k: plan.get(k) for k in ("engine", "campaign_brief", "removed")}))
        plan2 = (await c.post("/api/marketing/plan", json={"prompt": "x", "days": 1, "posts_per_day": 1, "channels": ["x"]})).json()
        check("3.4 le plan déterministe (sans LLM) porte aussi le brief", plan2.get("engine") == "deterministic"
              and plan2.get("campaign_brief") == "Mint de septembre" and "removed" in plan2, str(plan2)[:200])

        print("\n[4] un seul actif")
        await c.put("/api/marketing/brief", json={"name": "Octobre", "objective": "suite"})
        b2 = await marketing.active_brief()
        check("4.1 le nouveau remplace l'ancien, sans ses interdits", b2["name"] == "Octobre" and b2["forbidden"] == [])
        import sqlite3
        con = sqlite3.connect(str(_tmp / "t.db"))
        n_act, n_tot = con.execute("SELECT sum(active), count(*) FROM campaign_briefs").fetchone()
        con.close()
        check("4.2 un seul actif, l'ancien gardé pour l'historique", (n_act, n_tot) == (1, 2), str((n_act, n_tot)))

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
