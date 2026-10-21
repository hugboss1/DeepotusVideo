# -*- coding: utf-8 -*-
"""t273 (21/10/2026) — « Cloner une voix » de la page Voix off (Son & VFX) : clonage instantané ElevenLabs LIBRE,
sans entité de la bible. POST /api/voices/clone {nom, fichiers, description?, droit: true} → {voice_id, voice_name,
requires_verification}. Même seam multipart que le clonage d'une entité (voice_clone._post_voice_add) : on lit ce qui
PART. Refus, dans l'ordre : nom absent (400), droit non attesté (400), clé absente (503 qui nomme aussi Voicebox),
prises (400 chemin / nombre, 404 absente), refus d'ElevenLabs remonté tel quel. Le clonage d'une entité garde son
comportement (test_voice_clone).
Run: python tests/test_voix_clone_libre.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzclonelibre_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["ELEVENLABS_API_KEY"] = "test-11l"; os.environ["FAL_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from loguru import logger
logger.remove()
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.services import voice_clone as VC
from app.services.storage import init_db

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


settings.ELEVENLABS_API_KEY = "test-11l"
audio = settings.images_path.parent / "audio"
audio.mkdir(exist_ok=True)
(audio / "prise_a.mp3").write_bytes(b"ID3" + b"\0" * 4096)
(audio / "prise_b.wav").write_bytes(b"RIFF" + b"\1" * 1024)
SENT = []


def _fake_add(key, name, files, description, labels, remove_noise):
    SENT.append({"key": key, "name": name, "files": [f[0] for f in files], "tailles": [len(f[1]) for f in files],
                 "description": description, "labels": labels, "noise": remove_noise})
    return {"voice_id": "vx_libre_01", "requires_verification": False}


VC._post_voice_add = _fake_add
OK = {"nom": "Narrateur grave", "fichiers": ["prise_a.mp3", "prise_b.wav"], "description": "voix posée", "droit": True}


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        print("\n[1] le clonage libre")
        r = await c.post("/api/voices/clone", json=OK)
        d = r.json()
        check("C1 200 : voice_id, nom de la voix et vérification renvoyés",
              r.status_code == 200 and d.get("voice_id") == "vx_libre_01" and d.get("voice_name") == "Narrateur grave"
              and d.get("requires_verification") is False, r.text[:200])
        s = SENT[-1] if SENT else {}
        check("C2 ce qui part : la clé, le nom, les DEUX prises (octets entiers), la description, débruitage",
              s.get("key") == "test-11l" and s.get("name") == "Narrateur grave"
              and s.get("files") == ["prise_a.mp3", "prise_b.wav"] and s.get("tailles") == [4099, 1028]
              and s.get("description") == "voix posée" and s.get("noise") is True, str(s))
        check("C3 labels : la voix est marquée comme clonée depuis Son & VFX (aucune entité)",
              s.get("labels") == {"deepotus_source": "sonvfx"}, str(s.get("labels")))
        r = await c.post("/api/voices/clone", json=dict(OK, nom="  " + "x" * 140 + "  ", description=None))
        check("C4 nom rogné et borné à 100 caractères ; sans description : vide",
              r.status_code == 200 and SENT[-1]["name"] == "x" * 100 and SENT[-1]["description"] == "", r.text[:160])
        print("\n[2] les refus (rien ne part)")
        n0 = len(SENT)
        r = await c.post("/api/voices/clone", json=dict(OK, nom="   "))
        check("C5 sans nom : 400 qui le demande", r.status_code == 400 and "nom" in r.json().get("detail", ""), r.text[:160])
        for droit in (None, False, "oui", 1):
            r = await c.post("/api/voices/clone", json=dict(OK, droit=droit))
            check(f"C6 droit non attesté ({droit!r}) : 400 qui le demande",
                  r.status_code == 400 and "droit" in r.json().get("detail", ""), r.text[:160])
        r = await c.post("/api/voices/clone", json=dict(OK, fichiers=[]))
        check("C7 sans prise : 400 qui dit combien il en faut", r.status_code == 400 and "1 et 25" in r.json()["detail"], r.text[:160])
        for bad in (["../../secret.mp3"], ["..\\secret.mp3"], ["prise_a.mp3", "../t.db"]):
            r = await c.post("/api/voices/clone", json=dict(OK, fichiers=bad))
            check(f"C8 prise hors du dossier audio {bad} : 400", r.status_code == 400, r.text[:160])
        r = await c.post("/api/voices/clone", json=dict(OK, fichiers=["absente.mp3"]))
        check("C9 prise absente : 404 qui la nomme", r.status_code == 404 and "absente.mp3" in r.json()["detail"])
        r = await c.post("/api/voices/clone", json=dict(OK, fichiers="prise_a.mp3"))
        check("C10 fichiers qui n'est pas une liste : 400", r.status_code == 400, r.text[:160])
        r = await c.post("/api/voices/clone", content=b"pas du json", headers={"Content-Type": "application/json"})
        check("C11 corps illisible : 400 (le nom manque)", r.status_code == 400, r.text[:160])
        check("C12 aucun refus n'a rien envoyé à ElevenLabs", len(SENT) == n0, f"{len(SENT)} != {n0}")
        settings.ELEVENLABS_API_KEY = ""
        r = await c.post("/api/voices/clone", json=OK)
        check("C13 sans clé : 503 nommant ElevenLabs ET Voicebox", r.status_code == 503
              and "ElevenLabs" in r.json()["detail"] and "Voicebox" in r.json()["detail"], r.text[:200])
        settings.ELEVENLABS_API_KEY = "test-11l"

        def _refus(*a, **k):
            raise VC.SfxError(422, "ElevenLabs : échantillon trop court")
        VC._post_voice_add = _refus
        r = await c.post("/api/voices/clone", json=OK)
        check("C14 refus d'ElevenLabs : statut et message remontés",
              r.status_code == 422 and "trop court" in r.json()["detail"], r.text[:200])
        VC._post_voice_add = _fake_add
        r = await c.post("/api/voices/clone", json=OK, headers={"Accept-Language": "en"})
        r2 = await c.post("/api/voices/clone", json=dict(OK, droit=False), headers={"Accept-Language": "en"})
        check("C15 en anglais : le refus du droit se dit en anglais", r2.status_code == 400
              and "right" in r2.json().get("detail", "").lower(), r2.text[:200])


def _attendre():
    asyncio.run(main())


_attendre()
print(f"\n=== {ok} passed, {fail} failed ===")


def test_voix_clone_libre():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
