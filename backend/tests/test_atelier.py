"""Atelier P1: bible entities + chapters CRUD, reference generation with seed,
and the /images/generate FLUX seed passthrough. No live fal call (stubbed).
Run: <embedded python> backend/tests/test_atelier.py"""
import asyncio, json, os, sys, tempfile, pathlib, types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")          # FLUX path must be open
os.environ.setdefault("ELEVENLABS_API_KEY", "test-11l")   # casting voix (B)
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub fal_client BEFORE the app imports it (routes import it lazily inside
# the handler, so a sys.modules stub is picked up at call time).
CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": arguments.get("seed", 424242)}


async def _fake_upload(path):
    return "http://fal.test/uploaded-ref.png"

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport          # noqa: E402
import httpx as _httpx                                 # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402

# The FLUX path downloads each returned URL via httpx — stub the download.
# (vrai PNG décodable: la composition PIL des planches l'ouvre réellement)
_orig_get = _httpx.AsyncClient.get
import io as _io                                          # noqa: E402
from PIL import Image as _PILImage                        # noqa: E402
_buf = _io.BytesIO()
_PILImage.new("RGB", (8, 8), (30, 60, 90)).save(_buf, "PNG")
PNG = _buf.getvalue()


VOICES_11L = {"voices": [
    {"voice_id": "v_geo", "name": "George", "category": "premade",
     "labels": {"gender": "male", "age": "middle-aged", "accent": "british"},
     "preview_url": "http://11l.test/geo.mp3"},
    {"voice_id": "v_dan", "name": "Daniel", "category": "premade",
     "labels": {"gender": "male", "age": "old", "accent": "deep"},
     "preview_url": "http://11l.test/dan.mp3"},
    {"voice_id": "v_ali", "name": "Alice", "category": "premade",
     "labels": {"gender": "female", "age": "young", "accent": "french"},
     "preview_url": "http://11l.test/ali.mp3"},
]}


async def _fake_get(self, url, *a, **kw):
    u = str(url)
    if u.startswith("http://fal.test/"):
        req = _httpx.Request("GET", u)
        return _httpx.Response(200, content=PNG, request=req)
    if "api.elevenlabs.io/v1/voices" in u:
        return _httpx.Response(200, json=VOICES_11L,
                               request=_httpx.Request("GET", u))
    return await _orig_get(self, url, *a, **kw)

_httpx.AsyncClient.get = _fake_get


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # ---- bible entities CRUD ----
        r = await c.get("/api/bible/entities")
        assert r.status_code == 200 and r.json()["entities"] == [], r.text

        r = await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Le Prophète",
            "description": "vieil oracle poulpe, yeux dorés",
            "style_notes": "style anime sombre, palette abyssale"})
        assert r.status_code == 200, r.text
        ent = r.json(); eid = ent["id"]
        assert ent["kind"] == "character" and ent["seed"] is None

        r = await c.post("/api/bible/entities", json={
            "kind": "place", "name": "Caverne", "description": "caverne abyssale"})
        pid = r.json()["id"]

        r = await c.get("/api/bible/entities?kind=character")
        got = r.json()["entities"]
        assert len(got) == 1 and got[0]["name"] == "Le Prophète", got

        r = await c.put(f"/api/bible/entities/{eid}", json={
            "description": "vieil oracle poulpe, cicatrice au front",
            "inspiration_images": ["insp1.png"]})
        assert r.status_code == 200 and "cicatrice" in r.json()["description"]
        assert r.json()["inspiration_images"] == ["insp1.png"]

        # v1.17.1 — direct ref_image/seed re-link (recovery + manual pinning)
        r = await c.put(f"/api/bible/entities/{eid}",
                        json={"ref_image": "manual.png", "seed": 99})
        assert r.json()["ref_image"] == "manual.png" and r.json()["seed"] == 99

        # ═══ v1.20.2 — PLANCHE COMPOSITE (panneaux séparés + assemblage PIL) ═══
        # personnage = 7 panneaux: front(DEV) + left/right/back + 3 visages
        # (tous Kontext chaînés sur le front) → board composé par code.
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{eid}/generate", json={"seed": 777})
        assert r.status_code == 200, r.text
        g = r.json()
        # v6: 5 générations (face_front maître, face_left, front, left, back)
        # + 2 MIROIRS logiciels (face_right, right — jamais générés)
        assert len(CALLS) == 5, f"{len(CALLS)} appels (5 attendus)"
        master = CALLS[0]
        assert master["model"] == "fal-ai/flux/dev"
        assert master["arguments"].get("seed") == 777
        assert master["arguments"]["image_size"] == "portrait_4_3"
        mp = master["arguments"]["prompt"]
        assert "head-and-shoulders" in mp and "front view" in mp
        assert "oracle poulpe" in mp and "abyssale" in mp     # sujet + style
        assert "no titles" in mp and "sharp focus" in mp
        for i, call in enumerate(CALLS[1:], start=1):
            assert call["model"] == "fal-ai/flux-kontext/dev", f"panneau {i}"
            assert call["arguments"]["image_url"].startswith("http://fal.test/")
            assert "exact same" in call["arguments"]["prompt"].lower()
            assert "image_size" not in call["arguments"]
        # 2 headshots générés (face + profil G), 3 corps (face/profil G/dos),
        # aucun panneau "right" généré (dérivé par miroir), proportions OK
        assert sum("head-and-shoulders" in c["arguments"]["prompt"]
                   for c in CALLS) == 2
        assert sum("full body" in c["arguments"]["prompt"].lower()
                   for c in CALLS) == 3
        assert not any("right profile" in c["arguments"]["prompt"].lower()
                       for c in CALLS)
        # canon de proportions (DA2): style_notes "style anime sombre" →
        # canon manga shōnen auto-détecté (6,5-7 têtes, visage manga)
        assert "6.5 to 7 heads" in CALLS[2]["arguments"]["prompt"]
        assert "manga face" in CALLS[0]["arguments"]["prompt"]
        assert any("back view" in c["arguments"]["prompt"].lower()
                   for c in CALLS[3:])
        # board composé et stocké (PIL a réellement assemblé les panneaux)
        assert g["ref_image"].startswith("board_")
        img_dir_p = __import__("pathlib").Path(os.environ["IMAGES_FOLDER"])
        assert (img_dir_p / g["ref_image"]).is_file()
        from PIL import Image as _Img
        with _Img.open(img_dir_p / g["ref_image"]) as bim:
            assert bim.width > bim.height          # planche paysage 2 rangées
        assert g["seed"] == 777 and g["has_recipe"] is True
        assert g["face_image"] is None             # tout est dans le board

        # 🔁 use_recipe rejoue les 5 panneaux avec les seeds figés
        seeds_before = [c["arguments"].get("seed", None) or 424242 for c in CALLS]
        prompts_before = [c["arguments"]["prompt"] for c in CALLS]
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{eid}/generate",
                         json={"use_recipe": True})
        assert r.status_code == 200, r.text
        assert len(CALLS) == 5
        assert [c["arguments"]["prompt"] for c in CALLS] == prompts_before
        assert [c["arguments"]["seed"] for c in CALLS] == seeds_before

        # image d'inspiration PRÉSENTE → le panneau front passe sur Kontext
        # conditionné par TA référence (identité préservée)
        import pathlib as _pl
        (_pl.Path(os.environ["IMAGES_FOLDER"]) / "elias-card.png").write_bytes(PNG)
        r = await c.put(f"/api/bible/entities/{eid}",
                        json={"inspiration_images": ["elias-card.png"]})
        assert r.status_code == 200
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{eid}/generate", json={"seed": 9})
        assert r.status_code == 200, r.text
        assert CALLS[0]["model"] == "fal-ai/flux-kontext/dev"
        assert CALLS[0]["arguments"]["image_url"] == "http://fal.test/uploaded-ref.png"
        assert "same subject, face and design" in CALLS[0]["arguments"]["prompt"]
        assert CALLS[0]["arguments"]["seed"] == 9

        # ═══ lieu = board 3 panneaux + STYLE GLOBAL du projet ═══
        # (l'entité lieu n'a pas de style propre → le style global s'applique;
        #  le personnage ci-dessus avait un style_notes → il a primé)
        r = await c.put("/api/atelier/settings",
                        json={"global_style": "gravure abyssale monochrome"})
        assert r.status_code == 200
        assert r.json()["settings"]["global_style"] == "gravure abyssale monochrome"
        CALLS.clear()
        r = await c.put(f"/api/bible/entities/{pid}",
                        json={"description": "caverne abyssale bleutée"})
        r = await c.post(f"/api/bible/entities/{pid}/generate", json={})
        assert r.status_code == 200, r.text
        assert len(CALLS) == 3
        assert "establishing shot" in CALLS[0]["arguments"]["prompt"]
        assert "gravure abyssale monochrome" in CALLS[0]["arguments"]["prompt"]
        assert CALLS[0]["arguments"]["image_size"] == "landscape_16_9"
        assert "reverse angle" in CALLS[1]["arguments"]["prompt"].lower()
        assert "detail" in CALLS[2]["arguments"]["prompt"].lower()
        assert r.json()["ref_image"].startswith("board_")

        # ---- /images/generate seed passthrough (FLUX branch) ----
        r = await c.post("/api/images/generate", json={
            "prompt": "test still", "n": 1, "seed": 1234})
        assert r.status_code == 200, r.text
        assert r.json().get("seed") == 1234, r.json()
        assert CALLS[-1]["arguments"].get("seed") == 1234

        # ---- chapters CRUD + spans round-trip ----
        spans = [{"start": 10, "end": 21, "text": "Le Prophète", "entity_id": eid}]
        r = await c.post("/api/chapters", json={
            "title": "Chapitre 1", "series": "Lost Abyss",
            "script_text": "Au fond,   Le Prophète s'éveille dans la caverne.",
            "spans": spans})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        r = await c.get(f"/api/chapters/{cid}")
        ch = r.json()
        assert ch["title"] == "Chapitre 1" and ch["spans"] == spans, ch
        r = await c.get("/api/chapters")
        assert any(x["id"] == cid for x in r.json()["chapters"])
        r = await c.put(f"/api/chapters/{cid}", json={"title": "Chapitre 1 — l'éveil"})
        assert "éveil" in r.json()["title"]
        r = await c.delete(f"/api/chapters/{cid}")
        assert r.json()["ok"] is True

        # ═══ v1.21 (B) — casting voix ElevenLabs ═══
        from app.services import summarizer as SUMZ
        SUMZ.available = lambda: True
        SUMZ._chat_dispatch = lambda p, s, m: (
            '{"best": "v_dan", "alternates": ["v_geo"], '
            '"why": "Voix grave et âgée, assortie au vieil oracle."}', "stub")
        r = await c.post(f"/api/bible/entities/{eid}/suggest-voice", json={})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["suggested"]["voice_id"] == "v_dan"
        assert d["entity"]["voice_name"] == "Daniel"
        assert d["entity"]["voice_prev"] == "http://11l.test/dan.mp3"
        assert [a["voice_id"] for a in d["alternates"]] == ["v_geo"]
        assert "oracle" in d["why"]
        # persistance + choix manuel (PUT) d'une alternative
        got = (await c.get("/api/bible/entities?kind=character")).json()["entities"][0]
        assert got["voice_id"] == "v_dan"
        r = await c.put(f"/api/bible/entities/{eid}",
                        json={"voice_id": "v_geo", "voice_name": "George",
                              "voice_prev": "http://11l.test/geo.mp3"})
        assert r.json()["voice_name"] == "George"
        # casting sur un lieu -> refus explicite
        r = await c.post(f"/api/bible/entities/{pid}/suggest-voice", json={})
        assert r.status_code == 400

        # cleanup entity delete
        r = await c.delete(f"/api/bible/entities/{pid}")
        assert r.json()["ok"] is True
    print("ATELIER P1 TEST: PASS")

asyncio.run(main())
