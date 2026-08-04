"""v1.27 — plans structurés « style Sol » (doc de référence 2026-07-15).
Recette : (1) clean_posts conserve les champs étendus et termine la caption
par les hashtags ; (2) materialize_plan stocke le brief JSON, exposé parsé
par GET /schedule ; (3) fire_post publie la TG_CAPTION sur Telegram ;
(4) le fallback déterministe produit hashtags/liens depuis le prompt.
Aucun réseau (LLM et Telegram stubés).
Run: <embedded python -X utf8> backend/tests/test_plan_brief.py"""
import asyncio
import json
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.config import settings                       # noqa: E402
# le .env du data-dir a priorité sur l'environnement -> forcer sur l'objet
settings.DATABASE_URL = os.environ["DATABASE_URL"]

from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import marketing, plan_schema       # noqa: E402

# ── bloc LLM brut, tel que le planner doit le renvoyer (style Sol) ──
RAW_POST = {
    "day_offset": 0, "time": "19:30", "title": "P1 — Two nights",
    "format": "image", "hook": "Kickoff des deux lives",
    "caption": "TWO NIGHTS. ONE PROPHECY.\nRegister. Watch. Decode.\n"
               "https://www.deepotus.xyz",
    "tg_caption": "DEEPOTUS TRANSMISSION // TWO NIGHTS.\n"
                  "Enter the signal: https://www.deepotus.xyz",
    "image_idea": "Dark red-and-black poster, central DEEPOTUS emblem "
                  "glowing in crimson, crowd of shadowed silhouettes, "
                  "large title TWO NIGHTS. ONE PROPHECY.",
    "on_image_text": "TWO NIGHTS. ONE PROPHECY.",
    "script_idea": "Citizens of the surface. The signal opens in two "
                   "movements.",
    "avatar_script_long": "Citizens of the surface. For too long, you have "
                          "been asked to believe in symbols with no body.",
    "cta": "Set a reminder and share.",
    "hashtags": "#DEEPOTUS #DEEP #PumpFun",
    "links": "https://www.deepotus.xyz",
    "objective": "Official kickoff announcement",
    "priority": "High", "aspect_ratio": "1:1",
    "scheduling_notes": "Pin on X for 12 hours.",
    "channels": ["x", "telegram"],
}


def test_clean_posts():
    out = plan_schema.clean_posts([RAW_POST, "junk", {"day_offset": "x"}], 7)
    assert len(out) == 1
    p = out[0]
    for k in plan_schema.BRIEF_FIELDS:
        assert p[k], f"champ étendu perdu: {k}"
    # hashtags absents de la caption -> ajoutés en fin (prête à publier)
    assert p["caption"].endswith("#DEEPOTUS #DEEP #PumpFun")
    # déjà présents -> pas de doublon
    again = plan_schema.clean_posts([dict(RAW_POST, caption=p["caption"])], 7)
    assert again[0]["caption"].count("#DEEPOTUS") == 1
    print("clean_posts: PASS")


def test_deterministic():
    posts = marketing._deterministic_plan(
        "Lancement $DEEP — site https://www.deepotus.xyz #DEEPOTUS",
        2, 1, ["x", "telegram"], "FR", {"name": "Deepotus"})
    assert len(posts) == 2
    for p in posts:
        assert "#DEEP" in p["hashtags"] and "#DEEPOTUS" in p["hashtags"]
        assert p["links"] == "https://www.deepotus.xyz"
        assert p["caption"].rstrip().endswith(p["hashtags"])
        assert p["tg_caption"]
    print("deterministic enrichi: PASS")


async def main():
    await init_db()
    test_clean_posts()
    test_deterministic()

    # ── materialize -> brief JSON en DB, exposé parsé par l'API ──
    posts = plan_schema.clean_posts([RAW_POST], 7)
    ids = await marketing.materialize_plan(
        posts, start_date="2026-07-20", tz_offset_minutes=0)
    assert len(ids) == 1
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport,
                           base_url="http://test") as c:
        r = await c.get("/api/schedule")
        assert r.status_code == 200, r.text
        row = next(p for p in r.json() if p["id"] == ids[0])
        assert row["brief"]["tg_caption"].startswith("DEEPOTUS TRANSMISSION")
        assert row["brief"]["hashtags"] == "#DEEPOTUS #DEEP #PumpFun"
        assert row["brief"]["scheduling_notes"] == "Pin on X for 12 hours."
        assert row["image_idea"].startswith("Dark red-and-black poster")
        assert row["caption"].endswith("#DEEPOTUS #DEEP #PumpFun")

        # PATCH accepte un brief édité ; None le supprime proprement
        r = await c.patch(f"/api/schedule/{ids[0]}",
                          json={"brief": {"tg_caption": "édité"}})
        assert r.json()["brief"] == {"tg_caption": "édité"}

    # ── fire_post : Telegram reçoit la TG_CAPTION, pas la caption X ──
    sent = {}

    async def _fake_tg(caption, *, video_path=None, image_path=None):
        sent["caption"] = caption
        return True, "message 1"

    marketing.publish_telegram = _fake_tg
    settings.TELEGRAM_BOT_TOKEN = "stub-token"
    settings.TELEGRAM_CHAT_ID = "@stub"
    assert settings.has_telegram
    res = await marketing.fire_post(ids[0])
    assert res["ok"], res
    assert sent["caption"] == "édité"
    print("brief DB + API + fire_post tg_caption: PASS")
    print("PLAN BRIEF TEST: PASS")


asyncio.run(main())
