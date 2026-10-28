# -*- coding: utf-8 -*-
"""t317 (28/10/2026) (D3, tâche 3) — banc des routes /api/capture-montage (app/api/capture_montage_routes.py).
Plan docs/superpowers/plans/2026-10-28-t317-montage-capture.md, spec boîte à outils §8.4.
  1. liste des captures closes ; lecture (montage proposé, puis enregistré) ; vidéo remuxée ; capture non close 409 ;
  2. PUT validé et relu ; proposer ne réécrit rien ;
  3. rendre : job `capture` fini (étape Montage), index `capture` (parent = la scène, relation montage, recette),
     chapitres ; verrou 409 ; sous-titres « texte » sur une source muette -> rendu gardé, état dit ;
  4. transcription PAYANTE : devis tant que non confirmée (aucun appel), coût changé 409, confirmée -> un seul appel,
     ligne de dépense écrite (plafonds) ; sans clé -> devis ok:false, rien de lancé ;
  5. hors machine locale : 403 partout ; 6. L10 : refus en anglais.
ffmpeg réel, transcription remplacée, aucun réseau. Run (depuis backend/) : & $PY tests/test_capture_montage_routes.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcapmontrt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY",
          "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import capture as C, capture_montage as M        # noqa: E402
from app.services import transcribe_service as T                   # noqa: E402
from app.services.effects_preview import ffmpeg_bin                 # noqa: E402
FF = ffmpeg_bin()


def requete(f):
    async def g():
        from app.services.storage import async_session_factory
        async with async_session_factory() as s:
            return await f(s)
    return asyncio.run(g())


def job(jid):
    from app.services.storage import JobRecord
    return requete(lambda s: s.get(JobRecord, jid))


def index(nom):
    from app.services.storage import LibraryAsset
    return requete(lambda s: s.get(LibraryAsset, nom))


def depenses():
    from sqlalchemy import select
    from app.services.storage import Depense
    async def f(s):
        return list((await s.execute(select(Depense))).scalars())
    return requete(f)


def fausse_capture(cid, son=True, etat="terminee"):
    d = C.racine() / cid
    d.mkdir(parents=True)
    args = [FF, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=960x600:r=30:d=5"]
    if son:
        args += ["-f", "lavfi", "-i", "sine=f=440:d=5", "-c:a", "libopus"]
    args += ["-c:v", "libvpx", "-b:v", "800k", "-f", "webm", "-live", "1", "pipe:1"]
    octets = subprocess.run(args, capture_output=True).stdout
    (d / "scene.webm").write_bytes(octets)
    s = {"id": cid, "cree_utc": f"2026-10-28T10:00:0{cid[0] if cid[0].isdigit() else 0}+00:00", "debut_ms": 0,
         "fin_ms": 5000, "etat": etat, "duree_ms": 5000, "options": {"mode": "app"},
         "pistes": {"scene": {"mime": "video/webm", "ext": ".webm", "morceaux": 5, "octets": len(octets)}}}
    (d / "session.json").write_text(json.dumps(s), "utf-8")
    if etat == "terminee":
        (d / f"{cid}.dzclics.json").write_text(json.dumps({"version": 1, "id": cid, "duree_ms": 5000,
            "cadre": {"largeur": 960, "hauteur": 600, "mode": "app"},
            "evenements": [{"type": "ecran", "t": 0, "ecran": "quick"},
                           {"type": "clic", "t": 1000, "x": .3, "y": .3, "bouton": 0, "ecran": "quick",
                            "cible": {"balise": "button", "role": "", "t": "Générer", "i": ""}, "fiche": None},
                           {"type": "ecran", "t": 2000, "ecran": "studio"}]}), "utf-8")
        cap = settings.outputs_path / "captures"
        cap.mkdir(parents=True, exist_ok=True)
        (cap / f"capture_20261028-100000_{cid}.webm").write_bytes(octets)


A, B, MUET, EC = "1" * 16, "2" * 16, "3" * 16, "4" * 16
fausse_capture(A); fausse_capture(B); fausse_capture(MUET, son=False); fausse_capture(EC, etat="en_cours")

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("[1] liste et lecture")
    L = c.get("/api/capture-montage/captures").json()["captures"]
    check("1.1 seules les captures closes, avec durée et clics", {x["id"] for x in L} == {A, B, MUET}
          and all(x["duree_ms"] == 5000 and x["clics"] == 1 and x["montage"] is False for x in L), L)
    r = c.get(f"/api/capture-montage/{A}").json()
    check("1.2 lecture : montage proposé (un zoom, deux chapitres), événements, cadre", r["propose"] is True
          and len(r["montage"]["zooms"]) == 1 and [h["ecran"] for h in r["montage"]["chapitres"]] == ["quick", "studio"]
          and len(r["evenements"]) == 3 and r["capture"]["cadre"]["largeur"] == 960, r)
    check("1.3 capture en cours -> 409 ; inconnue 404 ; id invalide 400",
          c.get(f"/api/capture-montage/{EC}").status_code == 409
          and c.get("/api/capture-montage/0123456789abcdef").status_code == 404
          and c.get("/api/capture-montage/xyz").status_code == 400)
    v = c.get(f"/api/capture-montage/{A}/video")
    check("1.4 vidéo remuxée servie", v.status_code == 200 and v.headers["content-type"] == "video/webm"
          and len(v.content) > 1000 and (C.racine() / A / "scene.remux.webm").is_file())

    print("[2] enregistrer, proposer")
    m = dict(r["montage"], format="9:16", chapitres=[dict(h, titre="Ouverture") if h["t"] == 0 else h
                                                     for h in r["montage"]["chapitres"]],
             zooms=r["montage"]["zooms"] + [{"id": "zz", "t0": 3500, "t1": 4800, "k": 9, "x": 0.8, "y": 0.2, "x2": 1}])
    p = c.put(f"/api/capture-montage/{A}", json={"montage": m})
    check("2.1 PUT validé (k borné, champ inconnu retiré) et relu", p.status_code == 200
          and p.json()["montage"]["zooms"][-1] == {"id": "zz", "t0": 3500, "t1": 4800, "k": 2.5, "x": 0.8, "y": 0.2}
          and c.get(f"/api/capture-montage/{A}").json()["propose"] is False
          and c.get(f"/api/capture-montage/{A}").json()["montage"]["format"] == "9:16", p.text)
    check("2.2 PUT illisible -> 400", c.put(f"/api/capture-montage/{A}", json={"montage": "x"}).status_code == 400)
    pr = c.post(f"/api/capture-montage/{A}/proposer").json()["montage"]
    check("2.3 proposer : 16:9, sans écrire", pr["format"] == "16:9"
          and M.lire_montage(A)["format"] == "9:16")

    print("[3] rendre")
    R3 = c.post(f"/api/capture-montage/{A}/rendre", json={"titre": "Tuto"})
    j = R3.json()
    check("3.1 rendu ok : fichier, durée, chapitres", R3.status_code == 200 and j["ok"] is True
          and j["fichier"].endswith(f"_{A}_9x16.mp4") and abs(j["duree_s"] - 5) < 0.4
          and j["chapitres_texte"] == "00:00 Ouverture\n00:02 Studio"
          and (settings.outputs_path / "captures" / j["fichier"]).is_file(), R3.text)
    jb = job(j["job_id"])
    check("3.2 job capture fini, étape Montage, titre", jb is not None and jb.provider == "capture"
          and jb.status == "done" and jb.current_step == "Montage" and jb.title == "Tuto", jb and jb.status)
    ix = index(j["fichier"])
    check("3.3 index capture : parent = la scène, relation montage, recette", ix is not None and ix.source == "capture"
          and ix.parent_filename == f"capture_20261028-100000_{A}.webm" and ix.relation == "montage"
          and json.loads(ix.recette)["format"] == "9:16" and json.loads(ix.recette)["zooms"] == 2,
          ix and (ix.parent_filename, ix.relation, ix.recette))
    from app.api import capture_montage_routes as CR
    CR._EN_COURS.add(B)
    check("3.4 un rendu à la fois par capture -> 409", c.post(f"/api/capture-montage/{B}/rendre", json={}).status_code == 409)
    CR._EN_COURS.discard(B)
    mu = c.get(f"/api/capture-montage/{MUET}").json()["montage"]
    rm = c.post(f"/api/capture-montage/{MUET}/rendre", json={"montage": dict(mu, sous_titres={"source": "texte",
                "texte": "Bonjour, voici le tutoriel.", "langue": "fr"})})
    check("3.5 source muette + texte : rendu gardé, sous-titres dits (pas de plantage)", rm.status_code == 200
          and rm.json()["ok"] is True and rm.json()["sous_titres"]["etat"] in ("echec", "sans_voix", "graves"), rm.text)
    rs = c.post(f"/api/capture-montage/{MUET}/rendre", json={"montage": dict(mu, sous_titres={"source": "texte", "texte": " "})})
    check("3.6 texte vide -> sans_texte", rs.json()["sous_titres"] == {"etat": "sans_texte"}, rs.text)
    rc = c.post(f"/api/capture-montage/{B}/rendre", json={"montage": dict(mu, coupes=[{"id": "c", "t0": 0, "t1": 5000,
                                                                                         "mode": "couper", "vitesse": 8}])})
    check("3.7 coupe de toute la vidéo -> 400", rc.status_code == 400, rc.text)

    print("[4] transcription payante")
    appels = []
    T.estimate_transcription = lambda d, p=None: {"ok": True, "provider": "elevenlabs", "usd": 0.0123,
                                                  "duration_s": d, "label": "ElevenLabs"}
    def faux_transcribe(path, provider=None, language=None, timeout=600.0):
        appels.append(provider)
        w = T._norm_words([{"text": "Bonjour", "start": 0.2, "end": 0.7}, {"text": "monde", "start": 0.8, "end": 1.3}], "text")
        return {"ok": True, "words": w, "text": "Bonjour monde"}
    T.transcribe = faux_transcribe
    mt = dict(c.get(f"/api/capture-montage/{B}").json()["montage"], sous_titres={"source": "transcrire", "langue": "fr"})
    n0 = len(depenses())
    d1 = c.post(f"/api/capture-montage/{B}/rendre", json={"montage": mt})
    check("4.1 sans confirmation : devis, aucun appel, aucun rendu", d1.status_code == 200 and d1.json()["ok"] is False
          and d1.json()["devis"]["usd"] == 0.0123 and appels == []
          and not list((settings.outputs_path / "captures").glob(f"montage_*_{B}_*.mp4")), d1.text)
    d2 = c.post(f"/api/capture-montage/{B}/rendre", json={"montage": mt, "confirme_cout": True, "max_usd": 0.001})
    check("4.2 coût supérieur au plafond confirmé -> 409 avec le nouveau devis", d2.status_code == 409
          and d2.json()["devis"]["usd"] == 0.0123 and appels == [], d2.text)
    d3 = c.post(f"/api/capture-montage/{B}/rendre", json={"montage": mt, "confirme_cout": True})
    check("4.3 confirmation sans max_usd -> 400", d3.status_code == 400 and appels == [])
    d4 = c.post(f"/api/capture-montage/{B}/rendre", json={"montage": mt, "confirme_cout": True, "max_usd": 0.0123})
    check("4.4 confirmée : un appel, sous-titres gravés, dépense écrite", d4.status_code == 200 and d4.json()["ok"]
          and appels == ["elevenlabs"] and d4.json()["sous_titres"] == {"etat": "graves", "repliques": 1}
          and len(depenses()) == n0 + 1, (d4.text, appels, len(depenses()), n0))
    T.estimate_transcription = lambda d, p=None: {"ok": False, "provider": None, "usd": 0.0, "reason": "sans clé"}
    d5 = c.post(f"/api/capture-montage/{B}/rendre", json={"montage": mt, "confirme_cout": True, "max_usd": 1})
    check("4.5 sans clé : devis ok:false, rien de lancé", d5.json()["ok"] is False and appels == ["elevenlabs"], d5.text)

    print("[6] L10")
    r6 = c.get(f"/api/capture-montage/{EC}", headers={"Accept-Language": "en"})
    check("6.1 refus traduit (Accept-Language: en)", r6.status_code == 409 and "finished" in r6.json()["detail"].lower(),
          r6.text)

sys.path.insert(0, str(_ICI))
import _jeton_appareil as _JA                                       # noqa: E402
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    print("[5] hors machine locale")
    codes = [c2.get("/api/capture-montage/captures").status_code, c2.get(f"/api/capture-montage/{A}").status_code,
             c2.get(f"/api/capture-montage/{A}/video").status_code,
             c2.put(f"/api/capture-montage/{A}", json={"montage": {}}).status_code,
             c2.post(f"/api/capture-montage/{A}/proposer").status_code,
             c2.post(f"/api/capture-montage/{A}/rendre", json={}).status_code]
    check("5.1 403 partout", codes == [403] * 6, codes)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
