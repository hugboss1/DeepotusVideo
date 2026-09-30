# -*- coding: utf-8 -*-
"""Recyclage proposé (plan scheduler T16 — tâche #32 PR3, 30/09/2026) : les posts les mieux mesurés, assez vieux et
jamais recyclés reviennent en PROPOSITION ; rien ne part sans un POST explicite, qui pose un BROUILLON. La variation est
DÉTERMINISTE par défaut — écart au plan : une simple consultation (GET) n'appelle JAMAIS un LLM payant ; le LLM ne sert
que sur demande (llm=true), en passant par la garde des plafonds. Les interdits du brief sont retirés entre limites de
mot. Faux moteur Ollama (aucun réseau), une seule boucle asynchrone, data-dir temporaire. Témoin : la base 28cccdd n'a
pas de recyclage.
Run : & $PY tests/test_scheduler_recycle.py   (depuis backend/)"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
from datetime import datetime, timedelta
from uuid import uuid4
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrec_"))
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
check("0.1 TÉMOIN : pas de /schedule/recycle", _r and "/schedule/recycle" not in _r)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.PLANNER_PROVIDER = ""
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    setattr(settings, _k, "")
settings.OLLAMA_MODEL = "banc"                                      # un LLM est DISPONIBLE : il ne doit pas servir par défaut
from httpx import AsyncClient, ASGITransport                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import PostMetric, ScheduledPost, async_session_factory, init_db  # noqa: E402
from app.services import marketing                                  # noqa: E402
from app.api import routes as _routes                               # noqa: E402

APPELS = []


async def _faux_llm(prompt, days, ppd, channels, language, persona):
    APPELS.append(prompt)
    return [{"caption": "Réécrit par le modèle, garanti #1000x"}]

marketing._PLAN_PROVIDERS["ollama"] = _faux_llm


async def _poser(titre, jours, engagement, image="s.png"):
    pid = str(uuid4())
    quand = datetime.utcnow() - timedelta(days=jours)
    async with async_session_factory() as s:
        s.add(ScheduledPost(id=pid, title=titre, caption=f"{titre} #1000x garanti", channels="x", run_at=quand,
                            status="posted", mode="auto", format="image", posted_at=quand, source_image=image,
                            hook="accroche", brief=json.dumps({"tg_caption": "tg"}), remote_ids=json.dumps({"x": "r-" + pid[:6]})))
        s.add(PostMetric(id=str(uuid4()), post_id=pid, channel="x", remote_id="r-" + pid[:6], fetched_at=quand,
                         views=1000, likes=engagement, comments=0, shares=0, saves=0))
        await s.commit()
    return pid


async def main():
    await init_db()
    vieux = await _poser("Le meilleur", 40, 90)
    moyen = await _poser("Le moyen", 40, 10)
    frais = await _poser("Trop frais", 3, 500)
    persona_pool = _routes.pipeline.engine.persona.get("default_hashtags_pool") or []
    async with AsyncClient(transport=ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://test") as c:
        await c.put("/api/marketing/brief", json={"name": "B", "forbidden": "#1000x\ngaranti"})
        print("\n[1] les propositions")
        r = (await c.get("/api/schedule/recycle/suggest", params={"days": 90, "limit": 5})).json()
        ids = [x["source_id"] for x in r.get("suggestions", [])]
        check("1.1 les mieux mesurés d'abord ; le trop frais (moins de 21 jours) écarté", ids == [vieux, moyen] and frais not in ids, str(ids))
        top = (r.get("suggestions") or [{}])[0]
        check("1.2 engagement, âge et visuel de la source portés", top.get("engagement") == 90 and top.get("age_days", 0) >= 21
              and top.get("source_image") == "s.png" and top.get("channels") == ["x"], str(top)[:300])
        check("1.3 variation DÉTERMINISTE par défaut : aucun appel au LLM pourtant disponible (une consultation ne coûte rien)",
              top.get("engine") == "deterministic" and APPELS == [], str((top.get("engine"), APPELS)))
        cap = top.get("caption", "")
        check("1.4 une AUTRE légende, qui garde le fond, sans les interdits du brief",
              cap and cap != "Le meilleur #1000x garanti" and "Le meilleur" in cap and "#1000x" not in cap
              and "garanti" not in cap.lower(), cap)
        attendus = [h for h in persona_pool if h.lower() != "#1000x"][:3]
        check("1.5 les trois premiers hashtags du persona sont ajoutés, hors interdits (#1000x du pool écarté)",
              attendus and all(h in cap for h in attendus) and "#1000x" in persona_pool, f"{cap} / {attendus}")
        r2 = (await c.get("/api/schedule/recycle/suggest", params={"days": 90, "limit": 1})).json()
        check("1.6 limit respecté", len(r2["suggestions"]) == 1)

        print("\n[2] le LLM sur demande explicite")
        rl = (await c.get("/api/schedule/recycle/suggest", params={"days": 90, "limit": 1, "llm": "true"})).json()
        s0 = (rl.get("suggestions") or [{}])[0]
        check("2.1 llm=true : le modèle réécrit, ses interdits sont retirés", len(APPELS) == 1 and s0.get("engine") == "ollama"
              and s0.get("caption", "").startswith("Réécrit par le modèle") and "#1000x" not in s0.get("caption", "")
              and "garanti" not in s0.get("caption", "").lower(), str((APPELS[:1], s0)))

        print("\n[3] matérialiser une proposition")
        quand = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        n = (await c.post("/api/schedule/recycle", json={"source_id": vieux, "run_at": quand, "caption": cap})).json()
        check("3.1 un BROUILLON assisté, qui reprend visuel, canaux, accroche et brief, et nomme sa source",
              n.get("recycled_from") == vieux and n.get("status") == "draft" and n.get("mode") == "assisted"
              and n.get("source_image") == "s.png" and n.get("channels") == ["x"] and n.get("hook") == "accroche"
              and (n.get("brief") or {}).get("tg_caption") == "tg" and n.get("caption") == cap, str(n)[:300])
        r3 = (await c.get("/api/schedule/recycle/suggest", params={"days": 90, "limit": 5})).json()
        check("3.2 une fois recyclé, il ne revient plus dans les propositions", [x["source_id"] for x in r3["suggestions"]] == [moyen])
        check("3.3 source inconnue : 404 ; date illisible : 400",
              (await c.post("/api/schedule/recycle", json={"source_id": "inconnu", "run_at": quand})).status_code == 404
              and (await c.post("/api/schedule/recycle", json={"source_id": moyen, "run_at": "demain"})).status_code == 400)

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
