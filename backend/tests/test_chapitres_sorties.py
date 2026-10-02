# -*- coding: utf-8 -*-
"""Plan chapitres T18-T19 (tache #66 du suivi, PR B, 02/10/2026) — les SORTIES d'un chapitre vers le Montage : film et
reel, en NOUVEAU projet nomme, depuis le manifeste de l'animatique.
DECISIONS DE L'UTILISATEUR (02/10) : film + reel gratuits ; jamais la timeline en cours ; clips et voix COPIES dans un
instantane ; voix temoin en A1 ; « livre » abandonne (#65), T20 « remplacer le croquis » abandonne.
Ce que le plan faisait faux, et que ce banc garde : la timeline COURANTE ecrasee (_write_saved hors verrou) ; des durees
recalculees SANS les voix ; des clips vivants (purges au rendu suivant) ; la voix perdue ; aucun controle que
l'animatique decrit encore le storyboard.
ffmpeg REEL (540x960, quelques secondes), voix SIMULEE, data-dir isole, cles videes. Aucune depense.
Temoin positif : la base (c9de1181) n'a ni le module ni les routes.
Run (depuis backend/) : & $PY tests/test_chapitres_sorties.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsorties_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
os.environ["ELEVENLABS_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "c9de1181"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/sorties.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni le module ni les routes de sortie", r0.returncode != 0 and r1.returncode == 0
      and b'"/chapters/{chapter_id}/sortie/{nature}"' not in r1.stdout)


def ton(dest, duree):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={duree}", "-ac", "1", "-ar", "22050",
                    str(dest)], capture_output=True, check=True)
    return dest


try:
    from app.services import sorties as SO                          # noqa: E402
except ImportError as e:
    SO = None
    check("T2 le module existe", False, str(e))

if SO:
    print("[S] le module (pur)")
    man = {"plans": [{"idx": i, "shot_id": f"s{i}", "clip": f"p{i:03d}.mp4", "dur": d, "energie": en, "texte": f"t{i}",
                      "voix": (f"voix/v{i}.mp3" if i % 2 == 0 else None)}
                     for i, (d, en) in enumerate([(10, 5), (8, 1), (12, 4), (6, None), (9, 2)])]}
    check("S1 a_jour : memes plans, meme ordre ; un plan deplace ou ajoute -> non ; pas de manifeste -> non",
          SO.a_jour(man, [{"id": f"s{i}", "idx": i} for i in range(5)])
          and not SO.a_jour(man, [{"id": f"s{i}", "idx": 4 - i} for i in range(5)])
          and not SO.a_jour(man, [{"id": f"s{i}", "idx": i} for i in range(6)]) and not SO.a_jour(None, []))
    check("S2 film : tous les plans, dans l'ordre", [p["idx"] for p in SO.choisir(man, "film")] == [0, 1, 2, 3, 4])
    r = SO.choisir(man, "reel")
    check("S3 reel : les plus forts d'abord tant que ca tient dans 30 s (5:10 s, 4:12 s, sans energie=3:6 s -> 28 s), "
          "rendus dans l'ORDRE du chapitre", [p["idx"] for p in r] == [0, 2, 3], str([p["idx"] for p in r]))
    check("S4 reel : au moins un plan meme s'il depasse", [p["idx"] for p in SO.choisir({"plans": [{"idx": 0, "dur": 45, "energie": 1}]}, "reel")] == [0])
    try:
        SO.choisir(man, "livre"); refus = False
    except ValueError:
        refus = True
    check("S5 une nature inconnue est refusee (« livre » est abandonne)", refus and set(SO.NATURES) == {"film", "reel"})
    cl, dur = SO.clips_montage(SO.choisir(man, "reel"), "job-x")
    v1 = [c for c in cl if c["tr"] == "v1"]
    a1 = [c for c in cl if c["tr"] == "a1"]
    check("S6 clips : V1 bout a bout (0-10, 10-22, 22-28) DECOUPES dans l'animatique a la place de chaque plan (srcIn 0, 18, 30) ; "
          "A1 la voix au MEME instant et au meme srcIn ; une seule source, le rendu « job-x »",
          [(c["start"], c["end"]) for c in v1] == [(0.0, 10.0), (10.0, 22.0), (22.0, 28.0)] and dur == 28.0
          and [c["srcIn"] for c in v1] == [0.0, 18.0, 30.0] and [(c["start"], c["end"], c["srcIn"]) for c in a1] == [(0.0, 10.0, 0.0), (10.0, 22.0, 18.0)]
          and all(c["src"] == {"job_id": "job-x"} for c in cl), str(cl)[:300])

# ── les routes, au ffmpeg reel ────────────────────────────────────────────────────────────────────────────────────
sys.modules["fal_client"] = types.ModuleType("fal_client")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
from app.services import voice_providers as VP                      # noqa: E402
from app.services import elevenlabs_service as ELS                  # noqa: E402
from app.services import montage_service as MS                      # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
VP.resolve_provider = lambda requested=None: "elevenlabs"
VP.voicebox_reachable = lambda: False


def _faux_tts(self, text, output_path, language="EN", voice_id=None, **kw):
    ton(pathlib.Path(output_path), 1.2)
    return pathlib.Path(output_path)
ELS.VoiceoverService.generate_long = _faux_tts
ELS.VoiceoverService.is_enabled = staticmethod(lambda: True)


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


print("\n[R] les routes")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    check("R1 chapitre inconnu : 404", c.post("/api/chapters/inconnu/sortie/film").status_code == 404)
    ch = js(c.post("/api/chapters", json={"title": "L’Éveil", "script_text": "Vane entre.\n\nYsolde se tait.\n\nLa porte claque."}))
    cid = ch.get("id")
    shots = js(c.post(f"/api/chapters/{cid}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [])
    for s, (dur, en) in zip(shots, ((1.0, 2), (1.5, 5), (1.0, 4))):
        c.put(f"/api/shots/{s['id']}", json={"duration_s": dur, "energy": en})
    check("R2 nature inconnue : 400", c.post(f"/api/chapters/{cid}/sortie/livre").status_code == 400)
    r = c.post(f"/api/chapters/{cid}/sortie/film")
    check("R3 sans animatique montee : 409 qui le dit", r.status_code == 409 and "Animatique" in r.text, r.text[:120])
    narr = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Narrateur", "description": "voix"}))
    sqlite3.connect(str(_DB)).execute("UPDATE bible_entities SET voice_id='voix-narr' WHERE id=?", (narr.get("id"),)).connection.commit()
    j = js(c.post(f"/api/chapters/{cid}/animatique", json={"voix": True}))
    st = js(c.get(f"/api/atelier/manuscript/{j.get('job_id')}"))
    dossier = _tmp / "outputs" / "animatique" / str(cid)
    man = json.loads((dossier / "animatique.json").read_text(encoding="utf-8")) if (dossier / "animatique.json").is_file() else {}
    check("R4 le rendu ecrit son MANIFESTE : les plans dans l'ordre, leur clip, leur duree REELLE (la voix : 1,2 s), leur voix",
          st.get("phase") == "terminé" and [p.get("shot_id") for p in man.get("plans", [])] == [s["id"] for s in shots]
          and [p.get("dur") for p in man.get("plans", [])] == [1.2, 1.2, 1.2] and all(p.get("voix", "").startswith("voix/") for p in man.get("plans", []))
          and [p.get("energie") for p in man.get("plans", [])] == [2, 5, 4], str(man)[:300])
    from app.services import animatique_service as AN
    vieux = _tmp / "purge"
    vieux.mkdir()
    (vieux / "animatique.json").write_text("{}", encoding="utf-8")
    AN.purger(vieux)
    check("R4b un rendu PURGE l'ancien manifeste d'abord (un rendu rate ne laisse pas un manifeste perime)", not (vieux / "animatique.json").exists())
    e = js(c.get(f"/api/chapters/{cid}/sorties"))
    check("R5 GET /sorties : animatique a jour ; film 3 plans 3,6 s ; reel (energie 5, 4, 2 -> tout tient)",
          e.get("animatique") and e.get("a_jour") and e.get("natures", {}).get("film", {}).get("plans") == 3
          and e["natures"]["film"]["duree_s"] == 3.6 and e["natures"]["film"]["voix"] == 3, str(e))
    MS._write_saved({"name": "MON TRAVAIL EN COURS", "ratio": "9:16", "duration": 5, "mix": {}, "clips": [{"tr": "v1", "id": "x"}]})
    courant_avant = MS._saved_path().read_bytes()
    r = c.post(f"/api/chapters/{cid}/sortie/film")
    j = js(r)
    proj = MS._load_project(j.get("project_id")) if j.get("project_id") else None
    check("R6 FILM : un NOUVEAU projet nomme « L’Éveil — film », et la timeline EN COURS n'a pas bouge d'un octet",
          r.status_code == 200 and proj is not None and proj.get("name") == "L’Éveil — film" and MS._saved_path().read_bytes() == courant_avant,
          f"{r.status_code} {r.text[:200]}")
    v1 = [cl for cl in (proj or {}).get("clips", []) if cl.get("tr") == "v1"]
    a1 = [cl for cl in (proj or {}).get("clips", []) if cl.get("tr") == "a1"]
    import asyncio as _aio
    srcs = {_aio.run(MS._resolve_src(cl["src"])) for cl in v1 + a1}
    job = sqlite3.connect(str(_DB)).execute("SELECT status, provider, final_video_path FROM jobs WHERE id=?", (j.get("job_id"),)).fetchone()
    check("R7 V1 : trois plans bout a bout (0 ; 1,2 ; 2,4) decoupes a leur place (srcIn 0 ; 1,2 ; 2,4), A1 : trois voix au meme instant ; "
          "UNE source : le rendu « animatique » enregistre (fini, sans depense), copie de l'animatique dans l'INSTANTANE",
          [(cl["start"], cl["end"], cl["srcIn"]) for cl in v1] == [(0.0, 1.2, 0.0), (1.2, 2.4, 1.2), (2.4, 3.6, 2.4)] and len(a1) == 3
          and all(cl["src"] == {"job_id": j.get("job_id")} for cl in v1 + a1) and job is not None and job[:2] == ("done", "animatique")
          and "sorties" in pathlib.Path(job[2]).parts, f"{job} {v1[:1]}")
    p_src = next(iter(srcs)) if len(srcs) == 1 else None
    check("R8 le Montage RESOUT la source (le projet n'est pas « inouvrable ») et elle porte la piste son (les voix)",
          p_src is not None and p_src.is_file() and MS._has_audio_stream(p_src), str(srcs))
    j2 = js(c.post(f"/api/chapters/{cid}/animatique", json={}))
    js(c.get(f"/api/atelier/manuscript/{j2.get('job_id')}"))
    check("R9 un NOUVEAU rendu (qui purge le dossier de l'animatique) ne touche pas le projet : sa source existe toujours",
          p_src is not None and p_src.is_file() and (_tmp / "outputs" / "animatique") not in p_src.parents)
    from app.api import routes as RT
    check("R9b un rendu « animatique » est SANS DEPENSE dans les couts", "animatique" in RT._JOBS_SANS_DEPENSE)
    r = c.post(f"/api/chapters/{cid}/sortie/reel")
    j = js(r)
    proj2 = MS._load_project(j.get("project_id")) if j.get("project_id") else None
    check("R10 REEL : un AUTRE projet, sans voix cette fois (rendu muet), durees du plan (1 ; 1,5 ; 1)",
          r.status_code == 200 and proj2 is not None and proj2.get("id") != (proj or {}).get("id") and j.get("voix") == 0
          and [(cl["start"], cl["end"]) for cl in proj2["clips"] if cl["tr"] == "v1"] == [(0.0, 1.0), (1.0, 2.5), (2.5, 3.5)], str(j))
    c.post(f"/api/chapters/{cid}/shots", json={"source_text": "Un plan de plus."})
    e = js(c.get(f"/api/chapters/{cid}/sorties"))
    r = c.post(f"/api/chapters/{cid}/sortie/film")
    check("R11 le storyboard a CHANGE : a_jour faux, et la sortie refuse (409) au lieu de monter un film perime",
          e.get("a_jour") is False and r.status_code == 409 and "remontez" in r.text, f"{e} {r.status_code}")

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
import re as _re                                                     # noqa: E402
_at = _ICI.parent.parent / "frontend" / "atelier"
_js = (_at / "atelier.js").read_text(encoding="utf-8")
_html = (_at / "index.html").read_text(encoding="utf-8")
_fn = _js.split("async function sortieMontage(")[1].split("\n}\n")[0] if "async function sortieMontage(" in _js else ""
check("U1 deux boutons de sortie (film, reel) dans la modale de l'animatique, chacun avec un title",
      len(_re.findall(r'<button id="sortie(?:Film|Reel)" class="btn" data-sortie="(?:film|reel)" title="[^"]+">', _html)) == 2)
check("U2 apres creation : le dialogue maison DIT que la timeline en cours n'est pas touchee, et ouvre le Montage dans un onglet",
      "window.__dzDialogue.confirmer(" in _fn and "pas touchée" in _fn and 'window.open(r.montage, "_blank")' in _fn
      and "/projects/" not in _fn and not _re.search(r"(?<![.\w])(confirm|alert)\(", _fn))
check("U3 l'etat des sorties est relu avec celui de l'animatique ; boutons desactives si l'animatique n'est plus a jour",
      "await sortiesEtat();" in _js and "b.disabled = !s.a_jour;" in _js)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
