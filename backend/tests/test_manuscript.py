"""Agent manuscrit (v1.19) : segmentation, pipeline complet (LLM stubbé),
consolidation/alias, surlignage, idempotence du ré-import.
Run: <embedded python> backend/tests/test_manuscript.py"""
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
from app.services import manuscript_agent as MA          # noqa: E402
from app.services import summarizer as SUMZ               # noqa: E402

MANUSCRIT = """CHAPITRE 1 — L'ÉVEIL

Elias Vane s'éveille avant l'alarme. Le Prophète l'observe depuis la caverne
noyée d'une lumière bleutée d'aube froide.

Vane serre la Clé de Nacre dans sa main.

CHAPITRE 2 — LA PLUIE

En 2049, Londres disparaît sous une pluie fine. Elias marche, la Clé de
Nacre pèse dans sa poche. Le vieil oracle attend toujours dans la caverne.
"""

# ── stub LLM : 1 réponse d'extraction par chapitre, puis la consolidation ──
_LLM_CALLS = []
_EXTRACT_CH1 = json.dumps([
    {"kind": "character", "name": "Elias Vane", "aliases": ["Vane"],
     "description": "homme fatigué qui s'éveille avant l'alarme",
     "quotes": ["s'éveille avant l'alarme"]},
    {"kind": "character", "name": "Le Prophète", "aliases": [],
     "description": "figure qui observe depuis la caverne", "quotes": []},
    {"kind": "place", "name": "la caverne", "aliases": [],
     "description": "caverne baignée de lumière bleutée", "quotes": []},
    {"kind": "object", "name": "Clé de Nacre", "aliases": [],
     "description": "clé serrée dans la main d'Elias", "quotes": []},
    {"kind": "ambiance", "name": "aube froide", "aliases": [],
     "description": "lumière bleutée d'aube froide",
     "quotes": ["lumière bleutée d'aube froide"]},
])
_EXTRACT_CH2 = json.dumps([
    {"kind": "character", "name": "Elias Vane", "aliases": ["Elias"],
     "description": "marche sous la pluie", "quotes": []},
    {"kind": "character", "name": "le vieil oracle", "aliases": [],
     "description": "attend dans la caverne", "quotes": []},
    {"kind": "place", "name": "Londres", "aliases": [],
     "description": "ville sous la pluie fine", "quotes": []},
    {"kind": "date", "name": "2049", "aliases": [],
     "description": "année où Londres disparaît sous la pluie", "quotes": []},
])
_CONSOLIDATE = json.dumps([
    {"kind": "character", "name": "Elias Vane", "aliases": ["Vane", "Elias"],
     "description": "Homme fatigué au regard vide; marche sous la pluie de Londres."},
    {"kind": "character", "name": "Le Prophète",
     "aliases": ["le vieil oracle"],
     "description": "Vieil oracle qui observe et attend dans la caverne."},
    {"kind": "place", "name": "la caverne", "aliases": [],
     "description": "Caverne noyée d'une lumière bleutée."},
    {"kind": "place", "name": "Londres", "aliases": [],
     "description": "Ville qui disparaît sous une pluie fine."},
    {"kind": "object", "name": "Clé de Nacre", "aliases": [],
     "description": "Clé mystérieuse que Vane garde sur lui."},
    {"kind": "date", "name": "2049", "aliases": [],
     "description": "Année de la pluie sur Londres."},
    {"kind": "ambiance", "name": "aube froide", "aliases": [],
     "description": "Lumière bleutée, froide, d'avant l'aube."},
])


def _stub_dispatch(prompt, system, max_tokens):
    _LLM_CALLS.append(prompt[:60])
    if "Consolidate this entity list" in prompt:
        return _CONSOLIDATE, "stub"
    if "L'ÉVEIL" in prompt or "s'éveille avant l'alarme" in prompt:
        return _EXTRACT_CH1, "stub"
    return _EXTRACT_CH2, "stub"


SUMZ._chat_dispatch = _stub_dispatch
SUMZ.available = lambda: True
MA_extract_orig = None  # (l'agent importe _chat_dispatch à l'appel → stub actif)


def test_segmentation():
    segs = MA.segment_chapters(MANUSCRIT)
    assert len(segs) == 2, segs
    assert segs[0]["title"].startswith("CHAPITRE 1")
    assert segs[1]["title"].startswith("CHAPITRE 2")
    assert "Elias Vane s'éveille" in segs[0]["text"]
    # marqueur docx \x1f
    segs2 = MA.segment_chapters("\x1fLe Réveil\n\ncorps du premier chapitre " + "x" * 200
                                + "\n\n\x1fLa Pluie\n\ncorps du second " + "y" * 200)
    assert [s["title"] for s in segs2] == ["Le Réveil", "La Pluie"]


def test_spans_folding():
    ents = [{"id": "e1", "name": "Clé de Nacre", "aliases": [], "quotes": []}]
    text = "Il tient la CLE DE NACRE contre lui. La clé de nacre brille."
    spans = MA.compute_spans(text, ents)
    assert len(spans) == 2
    for sp in spans:
        assert text[sp["start"]:sp["end"]].lower().replace("é", "e") \
            .startswith("cle de nacre")


async def test_pipeline():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        files = {"manuscript": ("roman.txt", MANUSCRIT.encode(), "text/plain"),
                 "companion": ("notes.txt", "Notes: le Prophete est un poulpe.".encode(),
                                "text/plain")}
        r = await c.post("/api/atelier/manuscript", files=files,
                         data={"series": "Lost Abyss"})
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        for _ in range(60):
            st = (await c.get(f"/api/atelier/manuscript/{jid}")).json()
            if st["done"]:
                break
            await asyncio.sleep(0.2)
        assert st["done"] and not st["error"], st
        assert st["stats"]["chapitres_crees"] == 2
        assert st["stats"]["entites_creees"] == 7
        assert st["stats"]["zones_surlignees"] > 5

        # bible consolidée: alias fusionnés (le vieil oracle → Le Prophète)
        ents = (await c.get("/api/bible/entities")).json()["entities"]
        kinds = sorted(e["kind"] for e in ents)
        assert kinds == ["ambiance", "character", "character", "date",
                         "object", "place", "place"], kinds
        proph = next(e for e in ents if e["name"] == "Le Prophète")
        assert "le vieil oracle" in proph["aliases"]
        elias = next(e for e in ents if e["name"] == "Elias Vane")
        assert set(elias["aliases"]) >= {"Vane", "Elias"}
        assert elias["evidence"], "evidence quotes manquantes"

        # chapitres + spans (mentions par nom ET alias, quotes)
        chs = (await c.get("/api/chapters")).json()["chapters"]
        lost = [x for x in chs if x["series"] == "Lost Abyss"]
        assert len(lost) == 2
        ch1 = (await c.get(f"/api/chapters/{lost[0]['id']}")).json()
        sp_ents = {s["entity_id"] for s in ch1["spans"]}
        assert elias["id"] in sp_ents and proph["id"] in sp_ents
        texts = [s["text"].lower() for s in ch1["spans"]]
        assert any(t == "vane" for t in texts), "alias 'Vane' non surligné"
        assert any("lumière bleutée" in t for t in texts), "quote ambiance non surlignée"
        # offsets exacts
        for s in ch1["spans"]:
            assert ch1["script_text"][s["start"]:s["end"]] == s["text"]

        # ré-import: idempotent (mêmes chapitres mis à jour, entités enrichies)
        r = await c.post("/api/atelier/manuscript",
                         files={"manuscript": ("roman.txt", MANUSCRIT.encode(),
                                               "text/plain")},
                         data={"series": "Lost Abyss"})
        jid2 = r.json()["job_id"]
        for _ in range(60):
            st = (await c.get(f"/api/atelier/manuscript/{jid2}")).json()
            if st["done"]:
                break
            await asyncio.sleep(0.2)
        assert st["stats"]["chapitres_crees"] == 0
        assert st["stats"]["chapitres_mis_a_jour"] == 2
        assert st["stats"]["entites_creees"] == 0
        assert len((await c.get("/api/chapters")).json()["chapters"]) == len(chs)


test_segmentation()
test_spans_folding()
asyncio.run(test_pipeline())
print("MANUSCRIT AGENT TEST: PASS")
