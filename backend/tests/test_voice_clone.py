# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T14, D4a) — la voix d'un personnage lui appartient : clonage instantané ElevenLabs
(POST /v1/voices/add, page relue le 06/10/2026 : multipart name, files, description, labels,
remove_background_noise ; réponse voice_id, requires_verification) rattaché à une ENTITÉ de la bible, et
tempérament (balises Eleven v3 par personnage) persisté en base par le MÊME clamp que la voix off. Seam multipart
stubbé : on lit ce qui PART, et ce qui reste écrit sur l'entité. Clé absente = 503 (décision du 28/09 : toute
clé ou configuration de fournisseur absente), qui nomme aussi Voicebox (il clone dans SA propre application).
Run: python tests/test_voice_clone.py (depuis backend/)"""
import asyncio, json, os, pathlib, sqlite3, sys, tempfile
from uuid import uuid4
_tmp = tempfile.mkdtemp(prefix="dzclone_")
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
from app.services.storage import init_db, BibleEntity, async_session_factory
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
settings.ELEVENLABS_API_KEY = "test-11l"
audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
(audio / "prise_a.mp3").write_bytes(b"ID3" + b"\0" * 4096)
(audio / "prise_b.mp3").write_bytes(b"ID3" + b"\1" * 2048)
SENT = []
def _fake_add(key, name, files, description, labels, remove_noise):
    SENT.append({"key": key, "name": name, "files": [f[0] for f in files], "tailles": [len(f[1]) for f in files],
                 "description": description, "labels": labels, "noise": remove_noise})
    return {"voice_id": "vx_deep_01", "requires_verification": True}
VC._post_voice_add = _fake_add
EID = uuid4().hex
async def main():
    await init_db()
    async with async_session_factory() as s:
        s.add(BibleEntity(id=EID, kind="character", name="Deepotus", description="le dieu des abysses",
                          voice_prev="https://ancienne/prev.mp3"))
        await s.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        print("\n[1] le clonage")
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone",
                         json={"files": ["prise_a.mp3", "prise_b.mp3"], "description": "voix des abysses"})
        d = r.json()
        check("clone : 200, voice_id et nom renvoyés, vérification demandée DITE",
              r.status_code == 200 and d["voice_id"] == "vx_deep_01" and d["voice_name"] == "Deepotus"
              and d["requires_verification"] is True, r.text[:200])
        check("le POST porte la clé, le nom de l'entité, les DEUX prises (octets entiers), débruitage",
              SENT[-1]["key"] == "test-11l" and SENT[-1]["name"] == "Deepotus" and SENT[-1]["files"] == ["prise_a.mp3", "prise_b.mp3"]
              and SENT[-1]["tailles"] == [4099, 2051] and SENT[-1]["noise"] is True, str(SENT[-1]))
        check("labels : l'entité est nommée, pour retrouver la voix côté ElevenLabs", SENT[-1]["labels"] == {"deepotus_entity": EID},
              str(SENT[-1]["labels"]))
        check("description du corps prioritaire sur celle de la fiche", SENT[-1]["description"] == "voix des abysses")
        await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": ["prise_a.mp3"]})
        check("sans description : celle de la fiche part", SENT[-1]["description"] == "le dieu des abysses", SENT[-1]["description"])
        e = [x for x in (await c.get("/api/bible/entities")).json()["entities"] if x["id"] == EID][0]
        check("relu depuis la base : voix rattachée, ancienne pré-écoute EFFACÉE, tempérament vide",
              e["voice_id"] == "vx_deep_01" and e["voice_name"] == "Deepotus" and e["voice_prev"] is None
              and e["voice_style"] == {"tags": [], "stability": 0.5}, str(e)[:300])
        print("\n[2] le tempérament")
        r = await c.put(f"/api/bible/entities/{EID}",
                        json={"voice_style": {"tags": ["[whispers]", "[curious]", "[zzz]", "[sad]", "[excited]", "[sighs]", "[laughs]"],
                                              "stability": 0.9}})
        st = r.json()["voice_style"]
        check("clampé par le MÊME clamp que la voix off : inconnues retirées ([zzz], [sad] absente de la doc), ≤ 4, stabilité snappée",
              st == {"tags": ["[whispers]", "[curious]", "[excited]", "[sighs]"], "stability": 1.0}, str(st))
        db = sqlite3.connect(pathlib.Path(_tmp, "t.db"))
        brut = db.execute("select voice_style from bible_entities where id=?", (EID,)).fetchone()[0]; db.close()
        check("écrit en base DÉJÀ clampé (banc-miroir : on lit la colonne)",
              json.loads(brut) == {"tags": ["[whispers]", "[curious]", "[excited]", "[sighs]"], "stability": 1.0}, brut)
        r = await c.put(f"/api/bible/entities/{EID}", json={"voice_style": None})
        check("tempérament effaçable", r.json()["voice_style"] == {"tags": [], "stability": 0.5}, r.text[:160])
        r = await c.put(f"/api/bible/entities/{EID}", json={"name": "Deepotus Ier"})
        check("une autre mise à jour ne touche pas au tempérament", r.json()["voice_style"] == {"tags": [], "stability": 0.5})
        db = sqlite3.connect(pathlib.Path(_tmp, "t.db"))
        db.execute("update bible_entities set voice_style='{pas du json' where id=?", (EID,)); db.commit(); db.close()
        e = [x for x in (await c.get("/api/bible/entities")).json()["entities"] if x["id"] == EID][0]
        check("colonne illisible : servie VIDE et complète, jamais une erreur", e["voice_style"] == {"tags": [], "stability": 0.5}, str(e.get("voice_style")))
        print("\n[3] les refus")
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": []})
        check("sans prise : 400 qui dit combien il en faut", r.status_code == 400 and "1 et 25" in r.json()["detail"], r.text[:160])
        for bad in (["../../secret.mp3"], ["..\\secret.mp3"], ["prise_a.mp3", "../t.db"]):
            r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": bad})
            check(f"prise hors du dossier audio {bad} : 400, rien n'est parti", r.status_code == 400 and len(SENT) == 2, f"{r.status_code} {len(SENT)}")
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": ["absente.mp3"]})
        check("prise absente : 404 qui la nomme", r.status_code == 404 and "absente.mp3" in r.json()["detail"])
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": [f"p{i}.mp3" for i in range(26)]})
        check("plus de 25 prises : 400", r.status_code == 400)
        r = await c.post(f"/api/bible/entities/{uuid4().hex}/voice-clone", json={"files": ["prise_a.mp3"]})
        check("entité inconnue : 404", r.status_code == 404)
        settings.ELEVENLABS_API_KEY = ""
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": ["prise_a.mp3"]})
        check("sans clé : 503 nommant ElevenLabs ET Voicebox (qui clone dans sa propre application)",
              r.status_code == 503 and "ElevenLabs" in r.json()["detail"] and "Voicebox" in r.json()["detail"], r.text[:200])
        settings.ELEVENLABS_API_KEY = "test-11l"
        def _refus(*a, **k): raise VC.SfxError(422, "ElevenLabs : échantillon trop court")
        VC._post_voice_add = _refus
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": ["prise_a.mp3"]})
        check("refus d'ElevenLabs : statut et message REMONTÉS, voix de l'entité intacte",
              r.status_code == 422 and "trop court" in r.json()["detail"], r.text[:200])
        e = [x for x in (await c.get("/api/bible/entities")).json()["entities"] if x["id"] == EID][0]
        check("… la voix d'avant reste rattachée", e["voice_id"] == "vx_deep_01")
asyncio.run(main())

print("\n[4] une base EXISTANTE gagne la colonne (auto-ALTER), sans migration écrite")
# Sur une base NEUVE la colonne vient du modèle ; c'est la liste BIBLE_ENTITIES_COLUMNS qui la pose sur une base
# DÉJÀ créée. Les deux sont nécessaires, et seul un ancien schéma le prouve : une table bible_entities d'avant
# T103, puis init_db dans un AUTRE processus (son propre moteur, sa propre DATABASE_URL).
ancienne = pathlib.Path(_tmp, "ancienne.db")
db = sqlite3.connect(ancienne)
db.execute("create table bible_entities (id varchar(36) primary key, kind varchar(12), name varchar(120), "
           "description text, voice_id varchar(80), voice_name varchar(200), voice_prev text, "
           "created_at datetime, updated_at datetime)")
db.execute("insert into bible_entities (id, kind, name) values ('e-ancien', 'character', 'Ancien')")
db.commit(); db.close()
import subprocess as _sp
env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{ancienne.as_posix()}")
code = ("import sys,asyncio; sys.path.insert(0, r'" + str(pathlib.Path(__file__).resolve().parents[1]) + "'); "
        "from loguru import logger; logger.remove(); "
        "from app.services.storage import init_db; asyncio.run(init_db())")
r = _sp.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
db = sqlite3.connect(ancienne)
cols = [c[1] for c in db.execute("pragma table_info(bible_entities)")]
garde = db.execute("select name from bible_entities where id='e-ancien'").fetchone()
db.close()
check("ancien schéma + init_db : la colonne voice_style APPARAÎT, la ligne d'avant est intacte",
      r.returncode == 0 and "voice_style" in cols and garde == ("Ancien",), (r.stderr or "")[-300:] + str(cols))
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
