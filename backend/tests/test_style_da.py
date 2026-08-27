"""Atelier DA — direction artistique: builders providers, proposition de
styles par l'agent, planches via provider alternatif, référence de style.
Run: <embedded python> backend/tests/test_style_da.py"""
import asyncio, io, json, os, sys, tempfile, pathlib, types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-oa")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": (arguments or {}).get("seed", 111)}


async def _fake_upload(path):
    return "http://fal.test/up.png"

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport            # noqa: E402
import httpx as _httpx                                    # noqa: E402
from PIL import Image as _PILImage                        # noqa: E402
from app.main import app                                  # noqa: E402
from app.services.storage import init_db                  # noqa: E402
from app.services import image_providers as IP            # noqa: E402
from app.services import summarizer as SUMZ                # noqa: E402

_buf = io.BytesIO()
_PILImage.new("RGB", (8, 8), (40, 40, 80)).save(_buf, "PNG")
PNG = _buf.getvalue()
_orig_get = _httpx.AsyncClient.get


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG,
                               request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)

_httpx.AsyncClient.get = _fake_get


def test_builders():
    # OpenAI: generations vs edits
    url, p = IP.build_openai_request("gpt-image-2", "un chat", "portrait_16_9",
                                     1, has_image=False)
    assert url.endswith("/images/generations") and p["size"] == "1024x1536"
    url, p = IP.build_openai_request("gpt-image-2", "un chat", "landscape_16_9",
                                     1, has_image=True)
    assert url.endswith("/images/edits") and p["size"] == "1536x1024"
    # Nano Banana: t2i (aspect) vs edit (image_urls)
    m, a = IP.build_banana_request("un chat", "portrait_16_9", 1, None)
    assert m == "fal-ai/nano-banana" and a["aspect_ratio"] == "9:16"
    m, a = IP.build_banana_request("un chat", "square", 1, "http://x/y.png")
    assert m == "fal-ai/nano-banana/edit" and a["image_urls"] == ["http://x/y.png"]
    # registre selon les clés (FAL + OPENAI posées)
    ids = {p["id"] for p in IP.available()}
    assert {"flux", "gpt-image-2", "nano-banana"} <= ids
    assert next(p for p in IP.available() if p["id"] == "flux")["seeds"] is True
    assert next(p for p in IP.available() if p["id"] == "nano-banana")["seeds"] is False


def test_canons():
    from app.services import manuscript_agent as MA
    # chaque canon est complet (char/face/decor/label/kw) + presets valides
    # + v1.25: cadre vertical (frame) et plage de têtes mesurable (heads)
    for cid, c in MA.PROPORTION_CANONS.items():
        assert c["char"] and c["face"] and c["decor"] and c["label"], cid
        assert c["frame"] in ("portrait_16_9", "portrait_4_3",
                              "square_hd"), cid
        lo, hi = c["heads"]
        assert 1.5 <= lo < hi <= 10, cid
        # leçon tests A/B: le rapport doit être énoncé dans les deux sens
        assert "heads tall" in c["char"], cid
    for p in MA.STYLE_PRESETS:
        assert p["canon"] in MA.PROPORTION_CANONS, p["id"]
    # résolution: explicite > mots-clés du style > défaut De Vinci
    assert MA.resolve_canon("anime manga art style") == "manga_shonen"
    assert MA.resolve_canon("ligne claire influence, tintin") == "ligne_claire"
    assert MA.resolve_canon("American comic book style, superhero") == "comics_heroic"
    assert MA.resolve_canon("style Astérix, humour gros nez") == "gros_nez"
    assert MA.resolve_canon("Moebius metal hurlant") == "bd_realiste"
    assert MA.resolve_canon("gravure abyssale monochrome") == "davinci"
    assert MA.resolve_canon("anime manga", explicit="chibi") == "chibi"
    assert MA.resolve_canon("x", explicit="inexistant") == "davinci"


PROPOSALS = json.dumps([
    {"label": "Anticipation froide", "style_prompt": "cold retro-futuristic "
     "cinematic style, desaturated steel palette, volumetric fog",
     "canon": "cine",
     "rationale": "La pluie d'acier et la ville-machine du chapitre 1."},
    {"label": "Encre abyssale", "style_prompt": "inked noir illustration, "
     "deep blacks", "rationale": "Le ton noir du récit."},
    {"label": "BD moderne", "style_prompt": "modern euro comic art",
     "rationale": "Le rythme séquentiel."},
    {"label": "Photo-réalisme", "style_prompt": "photorealistic film still",
     "rationale": "Les détails concrets du texte."},
])


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # ── proposition de DA par l'agent (persistée) ──
        await c.post("/api/chapters", json={
            "title": "C1", "script_text": "Sous la pluie d'acier, la ville-machine "
            "respire. " * 20})
        SUMZ.available = lambda: True
        SUMZ._chat_dispatch = lambda p, s, m: (PROPOSALS, "stub")
        r = await c.post("/api/atelier/style/propose", json={})
        assert r.status_code == 200, r.text
        assert len(r.json()["proposals"]) == 4
        assert r.json()["proposals"][0]["label"] == "Anticipation froide"
        # canon: fourni par l'agent (cine) ou déduit du style_prompt
        assert r.json()["proposals"][0]["canon"] == "cine"
        assert all(p["canon"] for p in r.json()["proposals"])
        st = (await c.get("/api/atelier/settings")).json()["settings"]
        assert "Anticipation froide" in st["style_proposals"]

        # ── providers endpoint ──
        r = await c.get("/api/atelier/providers")
        assert any(p["id"] == "nano-banana" for p in r.json()["providers"])

        # ── planches via Nano Banana (t2i maître + edit chaînés, sans seed) ──
        await c.put("/api/atelier/settings",
                    json={"image_provider": "nano-banana", "global_style": ""})
        ent = (await c.post("/api/bible/entities", json={
            "kind": "place", "name": "La Caverne",
            "description": "caverne abyssale"})).json()
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{ent['id']}/generate", json={})
        assert r.status_code == 200, r.text
        assert len(CALLS) == 3
        assert CALLS[0]["model"] == "fal-ai/nano-banana"
        assert CALLS[0]["arguments"]["aspect_ratio"] == "16:9"
        for call in CALLS[1:]:
            assert call["model"] == "fal-ai/nano-banana/edit"
            assert call["arguments"]["image_urls"] == ["http://fal.test/up.png"]
        assert r.json()["ref_image"].startswith("board_")
        # la recette fige le provider → 🔁 rejoue en nano-banana
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{ent['id']}/generate",
                         json={"use_recipe": True})
        assert r.status_code == 200
        assert CALLS[0]["model"] == "fal-ai/nano-banana"

        # ── canon de proportions injecté selon le style (DA2) ──
        from app.services import proportion_qc as PQC
        PQC.measure = lambda p: None          # QC vision neutralisé ici
        await c.put("/api/atelier/settings",
                    json={"image_provider": "flux", "style_canon": "auto",
                          "global_style": "anime manga art style, cel shading"})
        perso = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Yuki",
            "description": "jeune héroïne aux cheveux argentés"})).json()
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{perso['id']}/generate", json={})
        assert r.status_code == 200, r.text
        # style manga auto-détecté → canon shōnen: visage manga sur le
        # headshot maître, 6,5-7 têtes sur le corps
        assert "manga face" in CALLS[0]["arguments"]["prompt"]
        assert any("6.5 to 7 heads" in cl["arguments"]["prompt"] for cl in CALLS)
        # v1.25: les panneaux CORPS chaînés imposent le cadre du canon
        # (resolution_mode Kontext) — leçon anti-tassement des tests A/B
        body_calls = [cl for cl in CALLS
                      if "FULL BODY" in cl["arguments"]["prompt"]
                      or "full body" in cl["arguments"]["prompt"]]
        assert body_calls, "aucun panneau corps généré"
        assert all(cl["arguments"].get("resolution_mode") == "9:16"
                   for cl in body_calls)      # manga_shonen → portrait_16_9
        # les panneaux VISAGE chaînés gardent le cadre de la référence
        face_chained = [cl for cl in CALLS
                        if "LEFT PROFILE" in cl["arguments"]["prompt"]
                        and "full body" not in cl["arguments"]["prompt"]]
        assert all("resolution_mode" not in cl["arguments"]
                   for cl in face_chained)

        # ── v1.25 QC proportions: mesure hors canon → retry correctif + leçon
        _mes = {"n": 0}

        def _fake_measure(path):
            _mes["n"] += 1
            if _mes["n"] == 1:      # 1ʳᵉ mesure: corps tassé (4.6 têtes)
                return {"heads": 4.6, "full_body": True, "feet_visible": True}
            return {"heads": 6.8, "full_body": True, "feet_visible": True}

        PQC.measure = _fake_measure
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{perso['id']}/generate", json={})
        assert r.status_code == 200, r.text
        # 5 panneaux + 1 retry correctif du corps
        assert len(CALLS) == 6, len(CALLS)
        retry = [cl for cl in CALLS
                 if "PREVIOUS ATTEMPT FAILED" in cl["arguments"]["prompt"]]
        assert len(retry) == 1 and "squashed at only 4.6" in \
            retry[0]["arguments"]["prompt"]
        # la leçon est persistée…
        st = (await c.get("/api/atelier/settings")).json()["settings"]
        lessons = json.loads(st["canon_lessons"])
        assert lessons["manga_shonen"]["fails"] == 1
        assert "PROPORTION GUARD" in lessons["manga_shonen"]["hint"]
        # …et ré-appliquée d'office à la génération suivante du même canon
        PQC.measure = lambda p: {"heads": 6.8, "full_body": True,
                                 "feet_visible": True}
        CALLS.clear()
        await c.post(f"/api/bible/entities/{perso['id']}/generate", json={})
        assert len(CALLS) == 5                # plus de retry nécessaire
        assert any("PROPORTION GUARD (learned)" in cl["arguments"]["prompt"]
                   for cl in CALLS)
        PQC.measure = lambda p: None
        # choix EXPLICITE gros nez → il prime sur la détection
        await c.put("/api/atelier/settings", json={"style_canon": "gros_nez"})
        CALLS.clear()
        await c.post(f"/api/bible/entities/{perso['id']}/generate", json={})
        assert any("4 to 5.5 heads" in cl["arguments"]["prompt"] for cl in CALLS)
        assert "oversized round" in CALLS[0]["arguments"]["prompt"]  # gros nez
        # la recette FIGE le canon: rejouer 🔁 ignore le réglage courant
        await c.put("/api/atelier/settings", json={"style_canon": "chibi"})
        CALLS.clear()
        await c.post(f"/api/bible/entities/{perso['id']}/generate",
                     json={"use_recipe": True})
        assert any("4 to 5.5 heads" in cl["arguments"]["prompt"] for cl in CALLS)
        await c.put("/api/atelier/settings",
                    json={"style_canon": "auto", "global_style": ""})

        # ── référence de STYLE (flux, entité sans identité propre) ──
        (pathlib.Path(_tmp, "images") / "style-bd.png").write_bytes(PNG)
        await c.put("/api/atelier/settings",
                    json={"image_provider": "flux",
                          "style_ref_image": "style-bd.png"})
        ent2 = (await c.post("/api/bible/entities", json={
            "kind": "decor", "name": "Mobilier", "description": "mobilier froid"})).json()
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{ent2['id']}/generate", json={})
        assert r.status_code == 200, r.text
        assert CALLS[0]["model"] == "fal-ai/flux-kontext/dev"   # conditionné
        assert "ART STYLE of the reference image" in CALLS[0]["arguments"]["prompt"]
        # décors: la perspective/échelle du canon (De Vinci par défaut) est
        # injectée sur le panneau maître
        assert "true human scale" in CALLS[0]["arguments"]["prompt"]

        # ── option vitrail (27/08): /images/generate applique le bloc épinglé
        CALLS.clear()
        r = await c.post("/api/images/generate",
                         json={"prompt": "a lighthouse keeper", "n": 1,
                               "model": "flux", "style": "vitrail"})
        assert r.status_code == 200, r.text
        envoye = CALLS[0]["arguments"]["prompt"]
        assert envoye.startswith("a lighthouse keeper")
        assert "#0047AB" in envoye and "entirely original artwork" in envoye
        assert "wyspia" not in envoye.lower()
        assert r.json()["prompt"] == envoye     # le prompt stylisé est rendu
        # un nom d'artiste tapé par l'utilisateur est épuré avant l'envoi
        CALLS.clear()
        r = await c.post("/api/images/generate",
                         json={"prompt": "after Wyspianski, a tall tower",
                               "n": 1, "model": "flux", "style": "vitrail"})
        assert r.status_code == 200, r.text
        assert "wyspia" not in CALLS[0]["arguments"]["prompt"].lower()
        assert "tall tower" in CALLS[0]["arguments"]["prompt"]
        # sans style: prompt inchangé (non-régression)
        CALLS.clear()
        r = await c.post("/api/images/generate",
                         json={"prompt": "plain subject", "n": 1,
                               "model": "flux"})
        assert r.status_code == 200, r.text
        assert CALLS[0]["arguments"]["prompt"] == "plain subject"
        # style inconnu: refus clair, aucune dépense
        CALLS.clear()
        r = await c.post("/api/images/generate",
                         json={"prompt": "x", "model": "flux",
                               "style": "gothico"})
        assert r.status_code == 400, r.text
        assert not CALLS

        # ── option vitrail: /episodes/scenes stylise les prompts de scène ──
        SCENES = json.dumps([
            {"text": "Para un.", "illustration_prompt": "a keeper on a pier"},
            {"text": "Para deux.",
             "illustration_prompt": "a lake city at dusk"},
        ])
        CAP = []
        SUMZ.available = lambda: True
        SUMZ._chat_dispatch = lambda p, s, m: (CAP.append((p, s)) or SCENES,
                                               "stub")
        r = await c.post("/api/episodes/scenes",
                         json={"script": "Para un.\n\nPara deux.",
                               "method": "ai", "style": "vitrail"})
        assert r.status_code == 200, r.text
        sc = r.json()["scenes"]
        assert len(sc) == 2
        for s in sc:
            assert s["illustration_prompt"].startswith(("a keeper", "a lake"))
            assert "#0047AB" in s["illustration_prompt"]
            assert "wyspia" not in s["illustration_prompt"].lower()
        # avec style, la consigne LLM demande des prompts SUJET (le thème
        # abyssal câblé ne s'impose plus); sans style, comportement d'origine
        assert "deep-sea" not in CAP[-1][0]
        CAP.clear()
        r = await c.post("/api/episodes/scenes",
                         json={"script": "Para un.\n\nPara deux.",
                               "method": "ai"})
        assert [s["illustration_prompt"] for s in r.json()["scenes"]] == \
            ["a keeper on a pier", "a lake city at dusk"]
        assert "deep-sea" in CAP[-1][0]
        # paragraphes + style: la première phrase du paragraphe, stylisée
        r = await c.post("/api/episodes/scenes",
                         json={"script": "Para un.\n\nPara deux.",
                               "method": "paragraph", "style": "vitrail"})
        assert r.status_code == 200
        for s in r.json()["scenes"]:
            assert s["illustration_prompt"].startswith("Para")
            assert "#0047AB" in s["illustration_prompt"]
    print("STYLE DA TEST: PASS")


test_builders()
test_canons()
asyncio.run(main())
