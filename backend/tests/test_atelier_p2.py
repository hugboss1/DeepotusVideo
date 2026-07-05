"""Atelier P2 storyboard: découpage paragraphe, CRUD des plans, croquis
(fal stubbé), réordonnancement. Run: <embedded python> backend/tests/test_atelier_p2.py"""
import asyncio, json, os, sys, tempfile, pathlib, types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": arguments.get("seed", 31337)}

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport          # noqa: E402
import httpx as _httpx                                 # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402

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

SCRIPT = ("Elias Vane s'éveille avant l'alarme, le regard vide.\n\n"
          "La cuisine s'allume seule. Le café coule à 03:08 précises.\n\n"
          "Dehors, Londres disparaît sous une pluie fine et gris acier.")


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # setup: chapitre + une entité
        ent = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Elias Vane",
            "description": "homme fatigué, imperméable gris"})).json()
        ch = (await c.post("/api/chapters", json={
            "title": "T1", "script_text": SCRIPT})).json()
        cid = ch["id"]

        # ---- découpage paragraphe (sans LLM) ----
        r = await c.post(f"/api/chapters/{cid}/storyboard/decoupe",
                         json={"method": "paragraph"})
        assert r.status_code == 200, r.text
        shots = r.json()["shots"]
        assert len(shots) == 3 and [s["idx"] for s in shots] == [0, 1, 2]
        assert shots[0]["source_text"].startswith("Elias Vane")
        assert shots[0]["duration_s"] > 0

        # ---- découpage ai avec LLM indisponible -> erreur explicite ----
        # (available() est patché pour garder le test gratuit/déterministe —
        # le chemin LLM réel a été validé en live le 2026-07-06.)
        from app.services import summarizer as _sumz
        _orig_avail = _sumz.available
        _sumz.available = lambda: False
        try:
            r = await c.post(f"/api/chapters/{cid}/storyboard/decoupe",
                             json={"method": "ai"})
            assert r.status_code == 200 and r.json().get("error"), r.text
        finally:
            _sumz.available = _orig_avail
        # re-découpe paragraphe pour repartir d'un état connu (l'appel ai
        # ci-dessus n'a rien remplacé)
        r = await c.post(f"/api/chapters/{cid}/storyboard/decoupe",
                         json={"method": "paragraph"})
        shots = r.json()["shots"]
        assert len(shots) == 3

        # ---- PUT champs + entités ----
        s0 = shots[0]
        r = await c.put(f"/api/shots/{s0['id']}", json={
            "action": "Elias ouvre les yeux, gros plan sur son visage",
            "shot_type": "close-up", "camera_move": "slow push-in",
            "duration_s": 6.5, "entities": [ent["id"]]})
        assert r.status_code == 200
        assert r.json()["shot_type"] == "close-up"
        assert r.json()["entities"] == [ent["id"]]

        # ---- croquis (stub fal) : style + action + desc entité + seed ----
        r = await c.post(f"/api/shots/{s0['id']}/sketch", json={"seed": 555})
        assert r.status_code == 200, r.text
        sk = r.json()
        assert sk["sketch_image"] and sk["sketch_seed"] == 555
        p = CALLS[-1]["arguments"]["prompt"].lower()
        assert "storyboard" in p and "sketch" in p       # style croquis
        assert "gros plan" in p or "close-up" in p        # action/type
        assert "imperméable gris" in p                    # desc entité injectée
        assert CALLS[-1]["arguments"]["seed"] == 555

        # ---- insertion après + réindexation ----
        r = await c.post(f"/api/chapters/{cid}/shots", json={"after_id": s0["id"]})
        assert r.status_code == 200
        lst = (await c.get(f"/api/chapters/{cid}/shots")).json()["shots"]
        assert len(lst) == 4 and lst[1]["id"] == r.json()["id"]
        assert [s["idx"] for s in lst] == [0, 1, 2, 3]

        # ---- reorder ----
        ids = [s["id"] for s in lst]
        ids.reverse()
        r = await c.post(f"/api/chapters/{cid}/storyboard/reorder",
                         json={"ids": ids})
        assert r.status_code == 200
        lst2 = (await c.get(f"/api/chapters/{cid}/shots")).json()["shots"]
        assert [s["id"] for s in lst2] == ids

        # ---- delete + réindexation ----
        r = await c.delete(f"/api/shots/{ids[0]}")
        assert r.json()["ok"] is True
        lst3 = (await c.get(f"/api/chapters/{cid}/shots")).json()["shots"]
        assert len(lst3) == 3 and [s["idx"] for s in lst3] == [0, 1, 2]

        # ---- re-découper remplace tout ----
        r = await c.post(f"/api/chapters/{cid}/storyboard/decoupe",
                         json={"method": "paragraph"})
        assert len(r.json()["shots"]) == 3
    print("ATELIER P2 TEST: PASS")

asyncio.run(main())
