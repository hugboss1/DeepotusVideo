# -*- coding: utf-8 -*-
"""t497 (G7, 26/11/2026) — banc de la note avant publication (`note_rendu`, routes /api/croissance).

Sections :
  1. pure : noter (bon rendu > 85 ; plan figé, accroche tardive, débit lent, sans sous-titres, horizontal, long ->
     remarques HORODATÉES en codes, note plus basse) ; inconnu = moitié ; libellé « estimation » ; plus_longs_plans ;
     depart_voix ; déterminisme ;
  2. étage 1 (vraie vidéo ffmpeg, job en base) : POST /note gratuit -> note, remarques, mesures ; avec un post : rangée
     dans brief.note_rendu ; job inconnu -> 404 ; sans cible -> 400 ; hors machine -> 403 ; aucun appel payant ;
  3. étage 2 : devis gratuit ; accord bas -> 409 cout ; affiner (faux Claude) : quatre images clés envoyées, remarques
     du modèle, zone sûre lue, garde « campagnes ».
Run (depuis backend/) : & $PY tests/test_note_rendu.py"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznote_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = ""
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
from app.services import note_rendu as NR                           # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import plafonds as PLAF                           # noqa: E402

settings.ANTHROPIC_API_KEY = "cle-de-banc"
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
APPELS, CATS = [], []


class _Rep:
    status_code = 200
    text = ""

    def json(self):
        return {"content": [{"type": "text", "text": json.dumps({"remarques": [{"t": 0, "texte": "Le texte du haut est caché par l'interface."}],
                                                                  "zone_sure": False, "soustitres": True})}],
                "usage": {"input_tokens": 1, "output_tokens": 1}}


MT.httpx.post = lambda url, headers=None, json=None, timeout=None, verify=None: APPELS.append(json) or _Rep()
_v = PLAF.verifier


async def espion(op, categorie="", *a, **k):
    CATS.append(categorie)
    return await _v(op, categorie, *a, **k)


PLAF.verifier = espion
BON = {"duree_s": 20.0, "cadre": "9:16", "coupes_s": [2, 4, 6, 8, 10, 12, 14, 16, 18], "son": True, "silences": [],
       "mots": [{"start": i * 0.37} for i in range(54)], "soustitres": True, "zone_sure": True}


def section_pure():
    print("[1] pure")
    r = NR.noter(BON)
    check("1a bon rendu : note ≥ 85, aucune remarque, estimation", r["note"] >= 85 and not r["remarques"] and r["libelle"] == "estimation", r)
    mauvais = {"duree_s": 75.0, "cadre": "16:9", "coupes_s": [20.0], "son": True, "silences": [[0, 2.5]],
               "mots": [{"start": 2.5 + i} for i in range(60)], "soustitres": False, "zone_sure": False}
    r2 = NR.noter(mauvais)
    codes = {x["code"] for x in r2["remarques"]}
    check("1b remarques : plan long, accroche tardive, débit lent, sans sous-titres, horizontal, long, zone sûre",
          {"plan_long", "accroche_tardive", "debit_lent", "sans_soustitres", "pas_vertical", "long", "hors_zone_sure"} <= codes, codes)
    check("1c note plus basse", r2["note"] < 30, r2["note"])
    pl = [x for x in r2["remarques"] if x["code"] == "plan_long"]
    check("1d plans longs horodatés (20 s figées à 0 s, 55 s à 20 s)", [(x["t"], x["secondes"]) for x in pl] == [(0.0, 20.0), (20.0, 55.0)], pl)
    check("1e remarques triées par temps", [x["t"] for x in r2["remarques"]] == sorted(x["t"] for x in r2["remarques"]))
    inc = NR.noter({"duree_s": 20.0, "cadre": "9:16", "coupes_s": BON["coupes_s"], "son": True, "silences": []})
    check("1f inconnu (mots, sous-titres, zone sûre) = la moitié", inc["composantes"]["debit"] == 0.5
          and inc["composantes"]["soustitres"] == 0.5 and inc["composantes"]["zone_sure"] == 0.5, inc["composantes"])
    check("1g sans son : remarque sans_voix", "sans_voix" in {x["code"] for x in NR.noter({**BON, "son": False, "mots": None})["remarques"]})
    check("1h plus longs plans", NR.plus_longs_plans([3, 10], 12) == [{"debut": 3, "duree": 7}, {"debut": 0.0, "duree": 3}, {"debut": 10, "duree": 2}])
    check("1i départ de la voix = fin du premier silence", NR.depart_voix([[0, 1.2], [5, 6]], True) == 1.2
          and NR.depart_voix([[3, 4]], True) == 0.0 and NR.depart_voix([], False) is None)
    check("1j poids : total 100", sum(NR.POIDS.values()) == 100)
    check("1k déterminisme", NR.noter(mauvais) == NR.noter(mauvais))
    try:
        NR.noter({"duree_s": 0}); check("1l durée nulle refusée", False)
    except NR.NoteImpossible:
        check("1l durée nulle refusée", True)


def fabriquer(out: pathlib.Path):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for c in ("red", "blue"):
        cmd += ["-f", "lavfi", "-i", f"color=c={c}:s=270x480:r=25:d={2 if c == 'red' else 6}"]
    cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=8", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "8", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


async def poser(video: pathlib.Path) -> tuple[str, str]:
    from app.services.storage import JobRecord, ScheduledPost, async_session_factory, init_db
    from datetime import datetime
    await init_db()
    jid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    async with async_session_factory() as s:
        s.add(JobRecord(id=jid, status="done", image_filename="x.png", final_video_path=str(video)))
        s.add(ScheduledPost(id=pid, title="t", run_at=datetime.utcnow(), job_id=jid, brief=json.dumps({"instagram": {"forme": "reel"}})))
        await s.commit()
    return jid, pid


def section_routes():
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("  SAUTÉ sections 2 et 3 : ffmpeg absent")
        return
    from fastapi.testclient import TestClient
    from app.main import app
    video = _tmp / "rendu.mp4"
    fabriquer(video)
    with TestClient(app, client=("127.0.0.1", 50000)) as client, TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        jid, pid = client.portal.call(poser, video)
        print("[2] étage 1")
        r = dehors.post("/api/croissance/note", json={"job_id": jid})
        check("2a hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)
        r = client.post("/api/croissance/note", json={})
        check("2b sans cible -> 400", r.status_code == 400, r.status_code)
        r = client.post("/api/croissance/note", json={"job_id": "inconnu"})
        check("2c job inconnu -> 404", r.status_code == 404, r.text[:200])
        r = client.post("/api/croissance/note", json={"job_id": jid, "soustitres": True})
        j = r.json()
        check("2d 200 : note, estimation, mesures 9:16 et son", r.status_code == 200 and 0 <= j["note"] <= 100 and j["libelle"] == "estimation"
              and j["mesures"]["cadre"] == "9:16" and j["mesures"]["son"] and j["etage"] == 1, r.text[:300])
        check("2e plan figé de 6 s relevé à 2 s", any(x["code"] == "plan_long" and abs(x["t"] - 2.0) < 0.2 for x in j["remarques"]), j["remarques"])
        check("2f aucun appel payant ni ligne de dépense", not APPELS and not CATS, (APPELS, CATS))
        r = client.post("/api/croissance/note", json={"post_id": pid})
        from app.services.storage import ScheduledPost, async_session_factory

        async def lire():
            async with async_session_factory() as s:
                return json.loads((await s.get(ScheduledPost, pid)).brief)
        b = client.portal.call(lire)
        check("2g post : note rangée dans brief.note_rendu, le reste du brief gardé", r.status_code == 200
              and b.get("note_rendu", {}).get("note") == r.json()["note"] and b.get("instagram") == {"forme": "reel"}, b)
        print("[3] étage 2")
        r = client.get(f"/api/croissance/note/devis?job_id={jid}")
        d = r.json()
        check("3a devis gratuit, quatre images (plafond de la garde)", r.status_code == 200 and d["usd"] > 0 and d["images"] == 4 == MT.MAX_IMAGES and not APPELS, d)
        r = client.post("/api/croissance/note/affiner", json={"job_id": jid, "max_usd": 0.000001})
        check("3b accord bas -> 409 cout, rien d'appelé", r.status_code == 409 and r.json()["detail"]["code"] == "cout" and not APPELS, r.text[:200])
        r = client.post("/api/croissance/note/affiner", json={"post_id": pid, "max_usd": d["usd"]})
        j = r.json()
        imgs = [c for m in (APPELS[-1]["messages"] if APPELS else []) for c in (m["content"] if isinstance(m["content"], list) else []) if c.get("type") == "image"]
        check("3c 200 : étage 2, remarque du modèle, zone sûre lue (KO)", r.status_code == 200 and j["etage"] == 2
              and j["remarques_modele"] and j["composantes"]["zone_sure"] == 0.0, r.text[:300])
        check("3d quatre images clés envoyées", len(imgs) == 4, len(imgs))
        check("3e garde « campagnes »", CATS == ["campagnes"], CATS)


def test_note_rendu():
    section_pure()
    section_routes()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    try:
        section_pure()
        section_routes()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
