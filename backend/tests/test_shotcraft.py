# -*- coding: utf-8 -*-
"""W-d video-shotcraft : service (skill installé / fallback embarqué),
doctrine + catalogue dans le prompt du découpage IA, validation
motion_recipe/energy, migration des colonnes sur une base pré-v1.22,
croquis enrichi. Run: <embedded python> backend/tests/test_shotcraft.py"""
import asyncio
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
_db = pathlib.Path(_tmp, "t.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
# Skill absent par défaut → fallback embarqué, test déterministe partout.
os.environ["SHOTCRAFT_SKILL_DIR"] = str(pathlib.Path(_tmp, "absent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---- base legacy pré-v1.22 : table shots SANS motion_recipe/energy + 1 plan
# (create_all n'altère jamais une table existante → seul _auto_migrate peut
# rendre cette base utilisable ; c'est ce qu'on prouve ici).
con = sqlite3.connect(_db)
con.execute("""CREATE TABLE shots (
    id VARCHAR(36) NOT NULL PRIMARY KEY, chapter_id VARCHAR(36) NOT NULL,
    idx INTEGER NOT NULL, source_text TEXT, action TEXT, entities TEXT,
    shot_type VARCHAR(30) NOT NULL, camera_move VARCHAR(40) NOT NULL,
    duration_s FLOAT NOT NULL, sketch_image VARCHAR(255),
    sketch_seed INTEGER, prompt TEXT,
    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)""")
con.execute("CREATE INDEX ix_shots_chapter_id ON shots (chapter_id)")
con.execute("INSERT INTO shots (id, chapter_id, idx, action, entities, "
            "shot_type, camera_move, duration_s, created_at, updated_at) "
            "VALUES ('legacy1', 'chap-legacy', 0, 'plan hérité', '[]', "
            "'medium', 'static, locked-off', 4.0, '2026-01-01', '2026-01-01')")
con.commit()
con.close()

CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": (arguments or {}).get("seed", 31337)}

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport          # noqa: E402
import httpx as _httpx                                 # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402
from app.services import shotcraft_service as sc       # noqa: E402
from app.services import summarizer as _sumz           # noqa: E402
from app.api import routes as R                        # noqa: E402

_orig_get = _httpx.AsyncClient.get
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fea75481840000000049454e44ae426082")


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG,
                               request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)

_httpx.AsyncClient.get = _fake_get

SCRIPT = ("Il pleut sur Londres, gris acier.\n\n"
          "Elias court sous les néons de Soho.\n\n"
          "Un cri déchire la nuit ; tout s'arrête.")


def test_service_fallback():
    st = sc.status()
    assert st["source"] == "bundled" and st["installed"] is False, st
    assert st["cards"] >= 100 and st["anim_cards"] >= 40, st
    for slug in ("tension-camera-moves", "crash-zoom-punch",
                 "page-turn-transitions", "sakuga-timing-shift"):
        assert slug in sc.valid_slugs(), slug
    blk = sc.prompt_block()
    assert "MOTION RECIPE CATALOG" in blk
    assert "One motion idea per shot" in blk            # doctrine
    assert "tension-camera-moves" in blk                # fiche caméra
    assert "collab-cursor-moves" not in blk             # fiche UI hors prompt
    assert "crash zoom" in sc.gloss("crash-zoom-punch")


def test_service_installed_merge():
    fake = pathlib.Path(_tmp, "fakeskill")
    (fake / "gallery" / "api").mkdir(parents=True, exist_ok=True)
    (fake / "SKILL.md").write_text("---\nname: video-shotcraft\n---\n",
                                   encoding="utf-8")
    (fake / "gallery" / "api" / "library.json").write_text(json.dumps({
        "cards": [{"name": "tension-camera-moves", "energy": "A 高 / B 中"},
                  {"name": "brand-new-card", "energy": "中高"}]}),
        encoding="utf-8")
    os.environ["SHOTCRAFT_SKILL_DIR"] = str(fake)
    try:
        st = sc.status()
        assert st["source"] == "installed" and st["installed"] is True, st
        assert st["path"] == str(fake), st
        # nouvelle fiche du skill acceptée (sélection manuelle) sans curation
        assert "brand-new-card" in sc.valid_slugs()
        assert sc.catalog()["cards"]["brand-new-card"]["energy"] == "mid-high"
        assert sc.catalog()["cards"]["brand-new-card"]["anim"] is False
        # catalogue embarqué conservé sous le merge
        assert "crash-zoom-punch" in sc.valid_slugs()
    finally:
        os.environ["SHOTCRAFT_SKILL_DIR"] = str(pathlib.Path(_tmp, "absent"))
    assert sc.status()["source"] == "bundled"


def test_ai_shots_prompt_and_validation():
    seen = {}

    def _fake_chat(prompt, system, max_tokens):
        seen["prompt"], seen["system"] = prompt, system
        return (json.dumps([
            {"source_excerpt": "Il pleut sur Londres, gris acier.",
             "action": "Pluie fine sur les toits", "entities": [],
             "shot_type": "establishing", "camera_move": "slow push-in",
             "duration_s": 6, "prompt": "pluie",
             "motion_recipe": "Tension-Camera-Moves", "energy": 2},
            {"source_excerpt": "Elias court sous les néons de Soho.",
             "action": "Course nocturne", "entities": [],
             "shot_type": "wide", "camera_move": "tracking shot",
             "duration_s": 5, "prompt": "course",
             "motion_recipe": "carte-inventee", "energy": 99},
            {"source_excerpt": "Un cri déchire la nuit ; tout s'arrête.",
             "action": "Silence, visage figé", "entities": [],
             "shot_type": "close-up", "camera_move": "static, locked-off",
             "duration_s": 4, "prompt": "cri",
             "motion_recipe": None, "energy": "beaucoup"}]), "test")

    _orig = _sumz._chat_dispatch
    _sumz._chat_dispatch = _fake_chat
    try:
        shots = R._ai_shots("mot " * 200, [], "fr")
    finally:
        _sumz._chat_dispatch = _orig
    # le prompt de l'agent interne porte la doctrine + le catalogue du skill
    assert "MOTION RECIPE CATALOG" in seen["prompt"]
    assert "One motion idea per shot" in seen["prompt"]
    assert '"motion_recipe"' in seen["prompt"] and '"energy"' in seen["prompt"]
    assert "video-shotcraft" in seen["system"]
    # validation : slug connu (case-insensitive), inconnu → None, clamps
    assert shots[0]["motion_recipe"] == "tension-camera-moves"
    assert shots[0]["energy"] == 2
    assert shots[1]["motion_recipe"] is None
    assert shots[1]["energy"] == 5                      # 99 → clamp
    assert shots[2]["motion_recipe"] is None
    assert shots[2]["energy"] is None                   # non numérique


async def test_api(c):
    # -- migration : la base legacy (sans colonnes W-d) répond, champs à None
    legacy = (await c.get("/api/chapters/chap-legacy/shots")).json()["shots"]
    assert len(legacy) == 1 and legacy[0]["id"] == "legacy1"
    assert legacy[0]["motion_recipe"] is None and legacy[0]["energy"] is None

    # -- chapitre + découpage paragraphe (champs W-d absents → None)
    ch = (await c.post("/api/chapters", json={
        "title": "W-d", "script_text": SCRIPT})).json()
    cid = ch["id"]
    r = await c.post(f"/api/chapters/{cid}/storyboard/decoupe",
                     json={"method": "paragraph"})
    assert r.status_code == 200, r.text
    shots = r.json()["shots"]
    assert len(shots) == 3
    assert all(s["motion_recipe"] is None and s["energy"] is None
               for s in shots)

    # -- PUT : recette valide + énergie clampée, slug invalide → None
    s0 = shots[0]
    r = await c.put(f"/api/shots/{s0['id']}",
                    json={"motion_recipe": "crash-zoom-punch", "energy": 9})
    assert r.status_code == 200, r.text
    assert r.json()["motion_recipe"] == "crash-zoom-punch"
    assert r.json()["energy"] == 5
    r = await c.put(f"/api/shots/{s0['id']}",
                    json={"motion_recipe": "nimporte-quoi"})
    assert r.json()["motion_recipe"] is None
    r = await c.put(f"/api/shots/{s0['id']}", json={
        "action": "Zoom brutal sur le visage d'Elias",
        "motion_recipe": "crash-zoom-punch", "energy": 5})
    assert r.json()["motion_recipe"] == "crash-zoom-punch"

    # -- croquis : la recette et l'énergie colorent le prompt FLUX
    r = await c.post(f"/api/shots/{s0['id']}/sketch", json={"seed": 7})
    assert r.status_code == 200, r.text
    p = CALLS[-1]["arguments"]["prompt"].lower()
    assert "motion intent" in p and "crash zoom" in p   # glose injectée
    assert "explosive" in p                             # énergie 5
    assert "storyboard" in p and "sketch" in p          # style préservé

    # -- endpoint catalogue pour l'UI
    r = await c.get("/api/atelier/shotcraft")
    d = r.json()
    assert d["status"]["cards"] >= 100
    tcm = next(x for x in d["cards"] if x["slug"] == "tension-camera-moves")
    assert tcm["anim"] is True and tcm["gloss"]
    assert d["cards"][0]["anim"] is True                # fiches anim en tête


async def main():
    await init_db()                                    # create_all + ALTER W-d
    test_service_fallback()
    test_service_installed_merge()
    test_ai_shots_prompt_and_validation()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        await test_api(c)
    # informatif : détection du vrai skill sur cette machine (non bloquant)
    os.environ["SHOTCRAFT_SKILL_DIR"] = str(
        pathlib.Path.home() / ".claude" / "skills" / "video-shotcraft")
    real = sc.status()
    print(f"  (info) skill réel : source={real['source']} "
          f"cards={real['cards']} path={real['path']}")
    print("SHOTCRAFT W-d TEST: PASS")

asyncio.run(main())
