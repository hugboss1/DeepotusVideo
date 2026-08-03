"""Atelier C — voice-over minuté par scène: parser Fountain, mode audiobook
hybride (Narrateur + voix castées), durées, job chapitre. TTS/ffmpeg stubbés.
Run: <embedded python> backend/tests/test_voiceover.py"""
import asyncio, os, sys, tempfile, pathlib, shutil

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-11l")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport            # noqa: E402
from app.main import app                                 # noqa: E402
from app.services.storage import (init_db, Scene, BibleEntity,  # noqa: E402
                                  async_session_factory)
from app.services.manuscript_agent import parse_fountain_segments  # noqa: E402
import app.api.routes as RT                              # noqa: E402
from app.services.elevenlabs_service import VoiceoverService  # noqa: E402
from datetime import datetime                            # noqa: E402
from uuid import uuid4                                   # noqa: E402

FOUNTAIN = """Le vent siffle sur les quais. Elias avance.

ELIAS VANE
(dans un souffle)
Tu m'attendais.

LE PROPHETE
Depuis longtemps, veilleur.

Il recule d'un pas. La pluie redouble."""


def test_parser():
    segs = parse_fountain_segments(FOUNTAIN)
    kinds = [(s["kind"], s["character"]) for s in segs]
    assert kinds == [("narration", None), ("dialogue", "ELIAS VANE"),
                     ("dialogue", "LE PROPHETE"), ("narration", None)], kinds
    assert "souffle" not in segs[1]["text"]          # parenthétical non lu
    assert segs[1]["text"] == "Tu m'attendais."
    # cue avec (V.O.) + texte sans dialogue = narration pure
    segs2 = parse_fountain_segments("NARRATEUR (V.O.)\nLa ville dort.\n\nJuste une action.")
    assert segs2[0] == {"kind": "dialogue", "character": "NARRATEUR",
                        "text": "La ville dort."}
    assert segs2[1]["kind"] == "narration"


# ── stubs TTS + ffmpeg ──
TTS_CALLS = []


def _fake_tts(self, text, output_path, language="EN", voice_id=None, **kw):
    TTS_CALLS.append({"text": text, "voice": voice_id, "lang": language})
    pathlib.Path(output_path).write_bytes(b"MP3" + text.encode()[:20])
    return pathlib.Path(output_path)


CONCAT_CALLS = []


def _fake_concat(paths, dest):
    CONCAT_CALLS.append(len(paths))
    shutil.copy2(paths[0], dest)


VoiceoverService.generate_long = _fake_tts
RT._concat_audio = _fake_concat
RT._audio_duration = lambda p: 7.5


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # bible: Elias casté, Prophète casté (via alias), PAS de narrateur
        eli = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Elias Vane"})).json()
        await c.put(f"/api/bible/entities/{eli['id']}",
                    json={"voice_id": "v_eli", "voice_name": "George"})
        pro = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Le Prophète",
            "aliases": []})).json()
        await c.put(f"/api/bible/entities/{pro['id']}",
                    json={"voice_id": "v_pro", "voice_name": "Daniel",
                          "aliases": ["le vieil oracle"]})
        ch = (await c.post("/api/chapters", json={
            "title": "C1", "script_text": "x" * 300})).json()
        async with async_session_factory() as session:
            for i in range(2):
                session.add(Scene(id=str(uuid4()), chapter_id=ch["id"], idx=i,
                                  slugline=f"INT. QUAI - NUIT {i}",
                                  fountain_text=FOUNTAIN,
                                  created_at=datetime.utcnow(),
                                  updated_at=datetime.utcnow()))
            await session.commit()
        scenes = (await c.get(f"/api/chapters/{ch['id']}/scenes")).json()["scenes"]

        # ── sans Narrateur → refus explicite ──
        r = await c.post(f"/api/scenes/{scenes[0]['id']}/voiceover", json={})
        assert r.status_code == 400 and "Narrateur" in r.json()["detail"]

        # ── avec Narrateur casté ──
        nar = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Narrateur"})).json()
        await c.put(f"/api/bible/entities/{nar['id']}",
                    json={"voice_id": "v_nar", "voice_name": "Alice"})
        TTS_CALLS.clear()
        r = await c.post(f"/api/scenes/{scenes[0]['id']}/voiceover",
                         json={"language": "fr"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["duration_s"] == 7.5
        assert d["scene"]["vo_audio"].startswith("vo_")
        assert d["scene"]["duration_s"] == 7.5
        # 4 segments TTS: narration(v_nar), Elias(v_eli), Prophète(v_pro), narration(v_nar)
        assert [t["voice"] for t in TTS_CALLS] == ["v_nar", "v_eli", "v_pro", "v_nar"]
        assert all(t["lang"] == "FR" for t in TTS_CALLS)
        assert CONCAT_CALLS[-1] == 4
        speakers = [s["speaker"] for s in d["segments"]]
        assert speakers == ["Narrateur", "Elias Vane", "Le Prophète", "Narrateur"]
        # fichier audio réellement écrit dans le dossier audio
        audio_dir = pathlib.Path(os.environ["IMAGES_FOLDER"]).parent / "audio"
        assert (audio_dir / d["scene"]["vo_audio"]).is_file()

        # ── job chapitre: ne régénère pas la scène 1 (déjà minutée) ──
        r = await c.post(f"/api/chapters/{ch['id']}/voiceover", json={})
        jid = r.json()["job_id"]
        for _ in range(60):
            st = (await c.get(f"/api/atelier/manuscript/{jid}")).json()
            if st["done"]:
                break
            await asyncio.sleep(0.2)
        assert st["done"] and not st["error"], st
        assert st["stats"]["scenes_generees"] == 1
        assert st["stats"]["scenes_conservees"] == 1
        assert st["stats"]["duree_totale_s"] == 15.0
        # les 2 scènes sont minutées
        scenes = (await c.get(f"/api/chapters/{ch['id']}/scenes")).json()["scenes"]
        assert all(s["duration_s"] == 7.5 and s["vo_audio"] for s in scenes)
    print("VOICEOVER TEST: PASS")


test_parser()
asyncio.run(main())
