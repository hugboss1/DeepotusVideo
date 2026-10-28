# -*- coding: utf-8 -*-
"""t315 (28/10/2026) (D1, tâche 2) — banc des routes /api/capture/* (app/api/capture_routes.py).
Plan docs/superpowers/plans/2026-10-28-t315-capture.md, spec boîte à outils §8.1-8.3.
Sections :
  1. session : POST /sessions -> id + options relues ;
  2. morceaux : PUT dans l'ordre (200), hors ordre 409, MIME 415, corps > 16 Mo 413, piste inconnue 400 ;
  3. terminer : scène copiée dans outputs/captures, job `capture` fini (Bibliothèque), index `capture` (propre),
     piste des clics nettoyée et identifiée, générations ajoutées (jobs créés pendant la capture, jamais les
     captures elles-mêmes), compte des clics reconnus ; seconde clôture 409 ; sans image 409 ; aucune dépense
     comptée pour un job `capture` ;
  4. lecture : GET /sessions/{id} (session + piste), GET …/pistes/{piste} (octets), 404 piste absente ; DELETE ;
  5. hors machine locale : 403 partout, rien d'écrit ;
  6. messages L10 : les refus se disent en anglais avec Accept-Language: en.
Données jetables, aucun réseau. Run (depuis backend/) : & $PY tests/test_capture_routes.py"""
import json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcaprt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
_JOURNAL = []
logger.add(lambda m: _JOURNAL.append(str(m)), level="DEBUG")
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
from app.services import capture as C                               # noqa: E402
from app.api import routes as R                                     # noqa: E402
import asyncio                                                      # noqa: E402

R._probe_seconds = lambda p: 3.0                                    # pas de ffprobe dans le banc


def jobs():
    from sqlalchemy import select
    from app.services.storage import JobRecord, async_session_factory
    async def f():
        async with async_session_factory() as s:
            return list((await s.execute(select(JobRecord))).scalars())
    return asyncio.run(f())


def index(nom):
    from app.services.storage import LibraryAsset, async_session_factory
    async def f():
        async with async_session_factory() as s:
            return await s.get(LibraryAsset, nom)
    return asyncio.run(f())


def ajouter_job(jid, provider, cree, fini=None, statut="done"):
    from app.services.storage import JobRecord, async_session_factory
    async def f():
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, status=statut, image_filename="x.png", provider=provider, created_at=cree,
                            completed_at=fini))
            await s.commit()
    asyncio.run(f())


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("[1] session")
    r = c.post("/api/capture/sessions", json={"options": {"mode": "app", "camera": True, "zoom": "oui"}})
    j = r.json()
    cid = j.get("id", "")
    check("1.1 POST /sessions -> 200, id, options relues", r.status_code == 200 and C.ID.match(cid)
          and j["options"]["camera"] is True and j["options"]["zoom"] is False, j)
    check("1.2 corps illisible -> 400", c.post("/api/capture/sessions", content=b"[1,", headers={"Content-Type": "application/json"}).status_code == 400)

    print("[2] morceaux")
    put = lambda piste, n, corps, mime="video/webm;codecs=vp9": c.put(f"/api/capture/sessions/{cid}/pistes/{piste}/{n}",  # noqa: E731
                                                                      content=corps, headers={"Content-Type": mime})
    check("2.1 morceau 0 de la scène", put("scene", 0, b"S0").status_code == 200)
    check("2.2 morceau 1 de la scène", put("scene", 1, b"S1").json() == {"piste": "scene", "recu": 1, "octets": 4})
    check("2.3 hors ordre -> 409", put("scene", 3, b"S3").status_code == 409)
    check("2.4 MIME refusé -> 415", put("ecran", 0, b"E", "image/png").status_code == 415)
    check("2.5 piste inconnue -> 400", put("clavier", 0, b"K").status_code == 400)
    check("2.6 corps > 16 Mo -> 413", put("ecran", 0, b"x" * (C.MAX_MORCEAU + 10)).status_code == 413)
    check("2.7 numéro négatif -> 400 ou 422", put("ecran", -1, b"E").status_code in (400, 422))
    put("ecran", 0, b"E0")
    put("voix", 0, b"V0", "audio/webm;codecs=opus")

    print("[3] terminer")
    s0 = C.lire(cid)["session"]
    debut = datetime.fromtimestamp(s0["debut_ms"] / 1000, timezone.utc).replace(tzinfo=None)
    ajouter_job("job-pendant", "fal", debut + timedelta(milliseconds=200), debut + timedelta(milliseconds=600))
    ajouter_job("job-avant", "fal", debut - timedelta(hours=2))
    ajouter_job("job-capture", "capture", debut + timedelta(milliseconds=100))
    clics = {"evenements": [
        {"type": "ecran", "t": 0, "ecran": "settings"},
        {"type": "clic", "t": 300, "x": 0.4, "y": 0.5, "bouton": 0, "ecran": "settings",
         "cible": {"balise": "button", "role": "", "t": "Poser le coffre", "i": ""}},
        {"type": "clic", "t": 500, "x": 0.2, "y": 0.3, "bouton": 0, "ecran": "settings", "secret": True,
         "cible": {"balise": "input", "role": "", "t": "", "i": "sk-ant-api03-zzz"}},
        {"type": "touche", "t": 600, "cle": "s"},
    ]}
    r = c.post(f"/api/capture/sessions/{cid}/terminer", json={"clics": clics, "duree_ms": 2000,
                                                             "cadre": {"largeur": 1280, "hauteur": 720}, "titre": "Démo"})
    j = r.json()
    check("3.1 terminer -> 200 {id, job_id, fichier, clics}", r.status_code == 200 and j.get("job_id")
          and j["fichier"].startswith("capture_") and j["clics"] == {"evenements": 5, "clics": 2, "reconnus": 1}, j)
    dest = settings.outputs_path / "captures" / j.get("fichier", "?")
    check("3.2 la scène est copiée dans outputs/captures (mêmes octets)", dest.is_file() and dest.read_bytes() == b"S0S1")
    jj = {x.id: x for x in jobs()}
    jc = jj.get(j.get("job_id"))
    check("3.3 job `capture` fini, vidéo = la scène, titre gardé", jc is not None and jc.provider == "capture"
          and jc.status == "done" and jc.final_video_path == str(dest) and jc.title == "Démo", jc and vars(jc))
    ix = index(dest.name)
    check("3.4 index de la Bibliothèque : source capture, vidéo, licence propriétaire, recette sans chemin",
          ix is not None and ix.source == "capture" and ix.kind == "video" and ix.licence == "propriétaire"
          and json.loads(ix.recette)["capture_id"] == cid and "\\" not in ix.recette, ix and vars(ix))
    lu = json.loads((C.racine() / cid / f"{cid}.dzclics.json").read_text("utf-8"))
    types = [e["type"] for e in lu["evenements"]]
    check("3.5 piste : touche retirée, générations du job « pendant » seulement (ni avant, ni captures)",
          "touche" not in types and types.count("generation_debut") == 1 and types.count("generation_fin") == 1
          and all(e.get("job_id") == "job-pendant" for e in lu["evenements"] if e["type"].startswith("generation")), lu)
    clic = next(e for e in lu["evenements"] if e["type"] == "clic" and not e.get("secret"))
    check("3.6 le clic « Poser le coffre » porte sa fiche du catalogue", clic.get("fiche") == "reglages.coffre.poser", clic)
    check("3.7 la zone secrète ne garde aucun texte", "sk-ant" not in json.dumps(lu))
    check("3.8 seconde clôture -> 409, et aucun job de plus", c.post(f"/api/capture/sessions/{cid}/terminer", json={}).status_code == 409
          and sum(1 for x in jobs() if x.provider == "capture") == 2)
    vide = c.post("/api/capture/sessions", json={}).json()["id"]
    r = c.post(f"/api/capture/sessions/{vide}/terminer", json={"duree_ms": 10})
    check("3.9 sans image -> 409, la session reste ouverte", r.status_code == 409 and C.lire(vide)["session"]["etat"] == "en_cours")
    # revue finale t315 (I1) : une clôture déjà réservée (autre /terminer en cours) -> 409 sans toucher aux fichiers
    s4 = c.post("/api/capture/sessions", json={}).json()["id"]
    c.put(f"/api/capture/sessions/{s4}/pistes/scene/0", content=b"Z0", headers={"Content-Type": "video/webm"})
    C.reserver(s4)
    avant = sorted(x.name for x in (settings.outputs_path / "captures").iterdir())
    r = c.post(f"/api/capture/sessions/{s4}/terminer", json={"duree_ms": 10})
    check("3.12 /terminer concurrent -> 409, aucun fichier copié ni effacé, le fichier de la 1re capture intact",
          r.status_code == 409 and sorted(x.name for x in (settings.outputs_path / "captures").iterdir()) == avant
          and dest.is_file())
    C.liberer(s4)
    check("3.13 la clôture libérée aboutit ensuite", c.post(f"/api/capture/sessions/{s4}/terminer", json={"duree_ms": 10}).status_code == 200)
    check("3.14 sans image : la réservation est rendue (en_cours)", C.lire(vide)["session"]["etat"] == "en_cours")
    check("3.10 un job `capture` n'engage aucune dépense (liste blanche des jobs gratuits)", "capture" in R._JOBS_SANS_DEPENSE)
    check("3.11 journaux : aucun libellé cliqué ni clé", not any("Poser le coffre" in m or "sk-ant" in m for m in _JOURNAL))

    print("[4] lecture et abandon")
    r = c.get(f"/api/capture/sessions/{cid}")
    check("4.1 GET session + piste", r.status_code == 200 and r.json()["session"]["etat"] == "terminee"
          and r.json()["clics"]["version"] == 1)
    r = c.get(f"/api/capture/sessions/{cid}/pistes/voix")
    check("4.2 GET piste brute voix (octets, type audio)", r.status_code == 200 and r.content == b"V0"
          and r.headers["content-type"].startswith("audio/webm"))
    check("4.3 piste absente -> 404", c.get(f"/api/capture/sessions/{cid}/pistes/camera").status_code == 404)
    check("4.4 capture inconnue -> 404, id hors motif -> 400",
          c.get("/api/capture/sessions/0123456789abcdef").status_code == 404
          and c.get("/api/capture/sessions/ZZZ").status_code == 400)
    r = c.delete(f"/api/capture/sessions/{vide}")
    check("4.5 DELETE -> abandonnee", r.status_code == 200 and r.json()["etat"] == "abandonnee")
    check("4.6 DELETE d'une capture close -> 409", c.delete(f"/api/capture/sessions/{cid}").status_code == 409)

    print("[6] L10")
    r = c.put(f"/api/capture/sessions/{cid}/pistes/scene/9", content=b"x", headers={"Content-Type": "video/webm",
                                                                                      "Accept-Language": "en"})
    check("6.1 refus traduit en anglais (Accept-Language: en)", r.status_code == 409
          and "closed" in r.json().get("detail", "").lower(), r.text)

sys.path.insert(0, str(_ICI))
import _jeton_appareil as _JA                                       # noqa: E402
# un téléphone APPAIRÉ (jeton valide) : il passe la garde réseau, la garde locale le refuse quand même
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    print("[5] hors machine locale")
    n_avant = len(list(C.racine().iterdir()))
    codes = [c2.post("/api/capture/sessions", json={}).status_code,
             c2.put(f"/api/capture/sessions/{cid}/pistes/scene/0", content=b"x").status_code,
             c2.post(f"/api/capture/sessions/{cid}/terminer", json={}).status_code,
             c2.delete(f"/api/capture/sessions/{cid}").status_code,
             c2.get(f"/api/capture/sessions/{cid}").status_code,
             c2.get(f"/api/capture/sessions/{cid}/pistes/voix").status_code]
    check("5.1 403 partout", codes == [403] * 6, codes)
    check("5.2 rien d'écrit", len(list(C.racine().iterdir())) == n_avant)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
