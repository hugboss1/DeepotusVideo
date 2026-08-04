"""Passe Scénario (v1.20 A) : adaptation stubbée → scènes + liaisons bible +
Fountain assemblé + édition. Run: <embedded python> backend/tests/test_screenplay.py"""
import asyncio, json, os, sys, tempfile, pathlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport            # noqa: E402
from app.main import app                                 # noqa: E402
from app.services.storage import init_db                 # noqa: E402
from app.services import summarizer as SUMZ               # noqa: E402

_ADAPT = json.dumps([
    {"slugline_location": "LA CAVERNE", "int_ext": "INT",
     "time_of_day": "NUIT",
     "fountain": ("Une lueur bleutée палpite sur la roche.\n\n"
                  "LE PROPHÈTE\n(voix caverneuse)\nTu es en retard, Elias.\n\n"
                  "ELIAS VANE\nJe sais."),
     "lighting": "bioluminescent underwater glow",
     "camera_notes": "slow push-in — resserre l'étau sur Elias au fil du reproche",
     "mood": "menace feutrée",
     "characters": ["Le Prophète", "Elias Vane"],
     "decor": ["stalactites nacrées", "bassin noir"],
     "source_excerpt": "Elias Vane s'éveille avant"},
    {"slugline_location": "RUES DE LONDRES", "int_ext": "EXT",
     "time_of_day": "AUBE",
     "fountain": "Pluie fine. ELIAS VANE remonte son col, avale la brume.",
     "lighting": "overcast diffused light",
     "camera_notes": "tracking shot — accompagne sa fuite en avant",
     "mood": "mélancolie urbaine",
     "characters": ["Elias Vane"],
     "decor": [],
     "source_excerpt": "Dehors, Londres disparaît sous"},
])


def _stub_dispatch(prompt, system, max_tokens):
    return _ADAPT, "stub"

SUMZ._chat_dispatch = _stub_dispatch
SUMZ.available = lambda: True


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # bible existante : la caverne (lieu) + 2 personnages
        cave = (await c.post("/api/bible/entities", json={
            "kind": "place", "name": "La Caverne",
            "description": "caverne abyssale bleutée"})).json()
        (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Elias Vane"})).json()
        proph = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Le Prophète"})).json()
        ch = (await c.post("/api/chapters", json={
            "title": "CHAPITRE 1", "script_text": "x" * 300})).json()

        # adaptation
        r = await c.post(f"/api/chapters/{ch['id']}/screenplay/adapt", json={})
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        for _ in range(60):
            st = (await c.get(f"/api/atelier/manuscript/{jid}")).json()
            if st["done"]:
                break
            await asyncio.sleep(0.2)
        assert st["done"] and not st["error"], st
        assert st["stats"]["scenes"] == 2
        # 2 décors créés + le lieu "Rues De Londres" créé; La Caverne RÉUTILISÉE
        assert st["stats"]["entites_creees"] == 3, st["stats"]

        scenes = (await c.get(f"/api/chapters/{ch['id']}/scenes")).json()["scenes"]
        assert len(scenes) == 2
        s1, s2 = scenes
        assert s1["slugline"] == "INT. LA CAVERNE - NUIT"
        assert s1["location_entity_id"] == cave["id"], "lieu existant non réutilisé"
        assert proph["id"] in s1["entities"]
        assert s1["lighting"] == "bioluminescent underwater glow"
        assert "push-in" in s1["camera_notes"]
        assert s2["slugline"] == "EXT. RUES DE LONDRES - AUBE"

        # décors catalogués dans la bible (réutilisables inter-chapitres)
        ents = (await c.get("/api/bible/entities?kind=decor")).json()["entities"]
        assert {e["name"] for e in ents} >= {"stalactites nacrées", "bassin noir"}

        # scénario Fountain assemblé
        sp = (await c.get(f"/api/chapters/{ch['id']}/screenplay")).json()
        assert sp["scene_count"] == 2
        assert "INT. LA CAVERNE - NUIT" in sp["fountain"]
        assert "LE PROPHÈTE" in sp["fountain"]
        assert "# CHAPITRE 1" in sp["fountain"]
        rf = await c.get(f"/api/chapters/{ch['id']}/screenplay?format=fountain")
        assert rf.headers["content-type"].startswith("text/plain")

        # édition d'une scène (fountain + moment du jour → slugline recomposée)
        r = await c.put(f"/api/scenes/{s2['id']}", json={
            "time_of_day": "NUIT", "lighting": "neon city lights, cyan and magenta"})
        assert r.json()["slugline"] == "EXT. RUES DE LONDRES - NUIT", r.json()

        # ré-adaptation remplace (pas de doublons)
        r = await c.post(f"/api/chapters/{ch['id']}/screenplay/adapt", json={})
        jid2 = r.json()["job_id"]
        for _ in range(60):
            st = (await c.get(f"/api/atelier/manuscript/{jid2}")).json()
            if st["done"]:
                break
            await asyncio.sleep(0.2)
        assert st["stats"]["scenes"] == 2
        assert st["stats"]["entites_creees"] == 0, st["stats"]
        assert len((await c.get(f"/api/chapters/{ch['id']}/scenes")).json()["scenes"]) == 2

        # reset du scénario (le manuscrit reste intact)
        r = await c.delete(f"/api/chapters/{ch['id']}/scenes")
        assert r.status_code == 200 and r.json()["deleted"] == 2
        assert (await c.get(f"/api/chapters/{ch['id']}/scenes")).json()["scenes"] == []
        assert (await c.get(f"/api/chapters/{ch['id']}")).json()["script_text"], \
            "le manuscrit a été touché !"
    print("SCREENPLAY TEST: PASS")

asyncio.run(main())
