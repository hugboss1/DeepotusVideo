# -*- coding: utf-8 -*-
"""P1 #6 lot A (28/09/2026) — SCENES « SEEDANCE (ANIMATED) » D'UN EPISODE.

Defaut mesure : run_episode passait motion="seedance" a scene_clip, qui le
traitait en Ken Burns (« v1 fallback ») ; aucun appel fal, /episodes/render
sans garde de cout. Decisions de l'utilisateur (28/09) : clip COURT (plus
petite duree native du modele, apres le plafond video_max_gen_s) BOUCLE a la
duree de la narration ; modele et resolution PAR SCENE (defaut : modele
global, plus basse resolution) ; un echec Seedance REPLIE la scene en Ken
Burns et le job le DIT.

METHODE : fal et la voix sont SIMULES (0 $) — le faux fal ecrit une vraie
video ffmpeg (testsrc 2 s), la fausse voix un vrai mp3 (sine 3 s) ; le rendu
final est MESURE par ffprobe. Temoins lus a la base de branche (`git show`) :
l'ancienne run_episode n'appelle jamais fal, l'ancienne route /episodes/render
n'a aucune garde de cout.
Faute n6 : details par _d(). Un banc par processus.
Run : & $PY tests/test_p1_episode_seedance.py   (depuis backend/, PATH avec le ffmpeg de l'app)
"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1ep_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(TMP, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(TMP, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(TMP, "outputs"))
os.environ.setdefault("FAL_KEY", "test-key")
for _d0 in ("images", "outputs"):
    pathlib.Path(TMP, _d0).mkdir(exist_ok=True)
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                  # noqa: E402
logger.remove()

BASE = "1e45ecd"   # main au depart de la branche (avant le lot A)
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


FF = shutil.which("ffmpeg")
FP = shutil.which("ffprobe")


def _ff(*args):
    subprocess.run([FF, "-y", "-v", "error", *args], check=True, capture_output=True)


def _probe(p):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "stream=codec_type,width,height,duration:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    v = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]
    a = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    return {"dur": float((j.get("format") or {}).get("duration") or 0),
            "vdur": float((v[0].get("duration") if v else 0) or 0),   # le FLUX video, pas le conteneur
            "w": v[0].get("width") if v else None, "h": v[0].get("height") if v else None, "audio": bool(a)}


from app.config import settings                            # noqa: E402
from app.services import pricing as PR                     # noqa: E402
from app.services.fal_service import VIDEO_MODELS, DEFAULT_VIDEO_MODEL  # noqa: E402

print("\n[0] preconditions")
check("0.1 ffmpeg et ffprobe de l'app sur le PATH", bool(FF) and bool(FP), _d(FF, FP))
# une illustration reelle dans le dossier images
IMG = "scene_test.png"
_ff("-f", "lavfi", "-i", "color=c=0x224466:s=720x1280", "-frames:v", "1", str(settings.images_path / IMG))
check("0.2 illustration de test ecrite", (settings.images_path / IMG).is_file(), "")

print("\n[1] plan des clips (module pur episode_video)")
try:
    from app.services import episode_video as EV
except Exception as e:                                      # noqa: BLE001
    EV = None
    print("   (module absent :", e, ")")
SCENES = [
    {"text": "Scene un, narree.", "image_filename": IMG, "motion": "seedance"},
    {"text": "Scene deux, Ken Burns.", "image_filename": IMG, "motion": "kenburns"},
    {"text": "Scene trois, Seedance un pro en 720p.", "image_filename": IMG, "motion": "seedance",
     "video_model": "seedance-v1-pro", "resolution": "720p", "illustration_prompt": "slow tide"},
    {"text": "Scene quatre, Seedance sans image.", "image_filename": None, "motion": "seedance"},
]
plan = EV.plan_videos(SCENES) if EV else []
check("1.1 seules les scenes seedance AVEC image sont planifiees (0 et 2)", [c["index"] for c in plan] == [0, 2], _d(plan))
_m25 = VIDEO_MODELS[DEFAULT_VIDEO_MODEL]
check("1.2 defaut : modele global, PLUS BASSE resolution, plus courte duree native",
      bool(plan) and plan[0]["model"] == DEFAULT_VIDEO_MODEL and plan[0]["resolution"] == _m25["resolutions"][0]
      and plan[0]["duration_s"] == min(_m25["durations"]), _d(plan[:1]))
check("1.3 choix par scene respecte (seedance-v1-pro, 720p, 3 s)",
      len(plan) > 1 and plan[1]["model"] == "seedance-v1-pro" and plan[1]["resolution"] == "720p"
      and plan[1]["duration_s"] == 3, _d(plan[1:]))
try:
    EV.plan_videos([{"text": "x", "image_filename": IMG, "motion": "seedance", "video_model": "pas-un-modele"}]) if EV else None
    _inconnu = False
except ValueError:
    _inconnu = True
check("1.4 modele inconnu : ValueError (la route en fera un 400)", _inconnu, "")
_res_hors = EV.plan_videos([{"text": "x", "image_filename": IMG, "motion": "seedance",
                            "video_model": "seedance-v1-pro", "resolution": "480p"}]) if EV else []
check("1.5 resolution absente du modele : sa plus basse (720p pour seedance-v1-pro), jamais la plus chere",
      bool(_res_hors) and _res_hors[0]["resolution"] == "720p", _d(_res_hors))

print("\n[2] devis de l'episode (pricing)")
_ops = EV.video_ops(plan) if EV else []
_tot = PR.estimate({"kind": "campaign", "ops": _ops})["total_usd"] if _ops else 0
_att = 4 * PR.video_rate(DEFAULT_VIDEO_MODEL, "480p") + 3 * PR.video_rate("seedance-v1-pro", "720p")
check("2.1 video_ops : 4 s en 2.5/480p + 3 s en 1.0 Pro/720p", abs(_tot - _att) < 1e-6, _d(_tot, _att))
_ep = PR.estimate({"kind": "episode", "images": 0, "chars": 0, "videos": _ops})["total_usd"]
check("2.2 estimate(episode) compte la liste `videos` par scene", abs(_ep - _att) < 1e-6, _d(_ep, _att))

print("\n[3] routes : devis et garde de cout avant mise en file")
from app.main import app                                    # noqa: E402
from app.api import routes as RT                            # noqa: E402
from app.services.elevenlabs_service import VoiceoverService  # noqa: E402
_lances = []
async def _faux_run_episode(**kw):
    _lances.append(kw)
RT.pipeline.run_episode = _faux_run_episode
VoiceoverService.is_enabled = staticmethod(lambda: True)


async def _http():
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1/api") as c:
        dev = await c.post("episodes/estimate", json={"scenes": SCENES})
        bas = await c.post("episodes/render", json={"scenes": SCENES, "max_usd": 0.01})
        n_bas = len(_lances)
        okr = await c.post("episodes/render", json={"scenes": SCENES, "max_usd": round(_att + 0.01, 2)})
        inc = await c.post("episodes/render", json={"scenes": [{"text": "x", "image_filename": IMG, "motion": "seedance",
                                                                 "video_model": "pas-un-modele"}]})
        return dev, bas, n_bas, okr, inc

dev, bas, n_bas, okr, inc = asyncio.run(_http())
_dj = dev.json() if dev.status_code == 200 else {}
check("3.1 /episodes/estimate : total = somme des clips planifies, une ligne par scene seedance",
      dev.status_code == 200 and abs(_dj.get("total_usd", -1) - _att) < 0.006 and [s.get("scene") for s in _dj.get("scenes", [])] == [1, 3],
      _d(dev.status_code, _dj))
check("3.2 /episodes/render sous le devis (max_usd 0,01) : 402 et RIEN en file",
      bas.status_code == 402 and n_bas == 0 and "rien n'a été généré" in bas.text, _d(bas.status_code, bas.text[:160]))
check("3.3 /episodes/render au devis : 200, scenes transmises avec modele/resolution",
      okr.status_code == 200 and len(_lances) == 1 and _lances[0]["scenes"][2].get("video_model") == "seedance-v1-pro",
      _d(okr.status_code, okr.text[:160]))
check("3.4 modele inconnu : 400 qui liste les modeles", inc.status_code == 400 and "seedance-2.5" in inc.text, _d(inc.status_code, inc.text[:160]))
_g = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
check("3.5 temoin : a la base, /episodes/render n'appelait aucune garde de cout",
      _g.returncode == 0 and "_garde_cout" not in _g.stdout.split('@router.post("/episodes/render")')[1].split("@router.")[0], "")

print("\n[4] run_episode : clip Seedance reel (fal simule), boucle a la narration")
from app.services.storage import init_db                    # noqa: E402
from app.services.pipeline import Pipeline                  # noqa: E402
asyncio.run(init_db())


class FauxFal:
    def __init__(self, echoue=False):
        self.appels, self.echoue = [], echoue
    async def upload_image(self, p):
        return "https://fal.test/" + pathlib.Path(p).name
    async def generate_video(self, **kw):
        self.appels.append(kw)
        if self.echoue:
            raise RuntimeError("fal a refuse (simule)")
        return {"video": {"url": "https://fal.test/v.mp4"}}
    @staticmethod
    def extract_video_url(res):
        return (res.get("video") or {}).get("url")
    async def download_video(self, url, dest):
        pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
        _ff("-f", "lavfi", "-i", "testsrc=size=720x1280:rate=24", "-t", "2", "-pix_fmt", "yuv420p", str(dest))
        return dest


class FausseVoix:
    @staticmethod
    def is_enabled():
        return True
    def generate_long(self, text, dest, language="en", voice_id=None):
        _ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(dest))
        return dest


def _rendu(fal, scenes, jid):
    pl = Pipeline()
    pl.fal, pl.voice = fal, FausseVoix()
    asyncio.run(pl.run_episode(job_id=jid, title="banc", voice_id=None, language="fr", scenes=scenes))
    return pl


async def _job(jid):
    from app.services.storage import async_session_factory, JobRecord
    async with async_session_factory() as s:
        j = await s.get(JobRecord, jid)
        return {"status": j.status, "step": j.current_step, "meta": json.loads(j.cost_meta or "{}"),
                "final": j.final_video_path}

fal = FauxFal()
_rendu(fal, SCENES[:3], "ep-ok")
J = asyncio.run(_job("ep-ok"))
P = _probe(J["final"]) if J["final"] and pathlib.Path(J["final"]).is_file() else {}
check("4.1 fal appele pour les DEUX scenes seedance, modele/resolution/duree du plan",
      [(a.get("model_id"), a.get("resolution"), a.get("duration")) for a in fal.appels]
      == [(DEFAULT_VIDEO_MODEL, _m25["resolutions"][0], 4), ("seedance-v1-pro", "720p", 3)], _d(fal.appels))
check("4.2 le prompt de la scene 3 est son prompt d'illustration ; la scene 1 retombe sur son texte",
      len(fal.appels) == 2 and "slow tide" in fal.appels[1].get("prompt", "") and "Scene un" in fal.appels[0].get("prompt", ""),
      _d([a.get("prompt") for a in fal.appels]))
check("4.3 episode termine, 1080x1920, audio, duree = 3 narrations de 3 s (clip de 2 s BOUCLE)",
      J["status"] == "done" and P.get("w") == 1080 and P.get("h") == 1920 and P.get("audio") and abs(P.get("dur", 0) - 9.0) < 0.25
      and abs(P.get("vdur", 0) - 9.0) < 0.25,
      _d(J["status"], P))
check("4.4 cost_meta : les deux clips reellement generes (modele, resolution, duree), aucun repli",
      [(v.get("model"), v.get("resolution"), v.get("duration_s")) for v in J["meta"].get("videos", [])]
      == [(DEFAULT_VIDEO_MODEL, _m25["resolutions"][0], 4), ("seedance-v1-pro", "720p", 3)]
      and not J["meta"].get("replis"), _d(J["meta"]))
_g2 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/pipeline.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
_re = _g2.stdout.split("async def run_episode(")[1].split("\n    async def ")[0] if _g2.returncode == 0 else ""
check("4.5 temoin : l'ancienne run_episode n'appelait jamais fal (Ken Burns pour tout)",
      bool(_re) and "generate_video" not in _re and "fall back to Ken Burns" in _re, "")

print("\n[5] echec Seedance : repli Ken Burns SIGNALE, l'episode va au bout")
fal2 = FauxFal(echoue=True)
_rendu(fal2, SCENES[:2], "ep-repli")
J2 = asyncio.run(_job("ep-repli"))
P2 = _probe(J2["final"]) if J2["final"] and pathlib.Path(J2["final"]).is_file() else {}
check("5.1 episode termine malgre le refus fal, duree = 2 narrations",
      J2["status"] == "done" and abs(P2.get("dur", 0) - 6.0) < 0.25, _d(J2["status"], P2))
check("5.2 le job DIT le repli (etape finale <= 80 car., scene nommee)",
      "repli" in (J2["step"] or "").lower() and "1" in (J2["step"] or "") and len(J2["step"] or "") <= 80, _d(J2["step"]))
check("5.3 cost_meta : aucun clip facture, le repli porte la scene et le motif",
      J2["meta"].get("videos") == [] and J2["meta"].get("replis") == [{"scene": 1, "motif": "fal a refuse (simule)"}],
      _d(J2["meta"]))

print("\n[5b] facturation du job (/cost/usage)")
async def _couts():
    from app.services.storage import async_session_factory, JobRecord
    p = PR.load()
    async with async_session_factory() as s:
        a = RT._job_to_cost(await s.get(JobRecord, "ep-ok"), p)
        b = RT._job_to_cost(await s.get(JobRecord, "ep-repli"), p)
    lab = lambda e: [l.get("label") for l in e.get("breakdown", [])]
    return a, b, lab(a), lab(b)
_ca, _cb, _la, _lb = asyncio.run(_couts())
_video_ok = 4 * PR.video_rate(DEFAULT_VIDEO_MODEL, "480p") + 3 * PR.video_rate("seedance-v1-pro", "720p")
_sans = PR.estimate({"kind": "episode", "images": 3, "chars": J["meta"].get("chars", 0)})["total_usd"]
check("5b.1 le job facture les deux clips generes en plus des images et de la narration",
      abs(_ca["total_usd"] - (_sans + _video_ok)) < 1e-6 and sum("Video" in (x or "") for x in _la) == 2, _d(_la, _ca.get("total_usd")))
check("5b.2 le job replie ne facture AUCUN clip", not any("Video" in (x or "") for x in _lb), _d(_lb))

print("\n[6] scene_clip_video (ffmpeg) seul")
from app.services.ffmpeg_service import FFmpegMerger        # noqa: E402
_v = pathlib.Path(TMP, "v.mp4"); _a = pathlib.Path(TMP, "a.mp3"); _o = pathlib.Path(TMP, "o.mp4")
_ff("-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=25", "-t", "1.5", "-pix_fmt", "yuv420p", str(_v))
_ff("-f", "lavfi", "-i", "sine=duration=4.2", str(_a))
try:
    FFmpegMerger.scene_clip_video(_v, _a, _o, dur=4.2)
    P6 = _probe(_o)
except Exception as e:                                      # noqa: BLE001
    P6 = {"erreur": str(e)[:200]}
check("6.1 clip 16:9 de 1,5 s -> 1080x1920, boucle jusqu'a 4,2 s, avec la narration",
      P6.get("w") == 1080 and P6.get("h") == 1920 and P6.get("audio") and abs(P6.get("dur", 0) - 4.2) < 0.12
      and abs(P6.get("vdur", 0) - 4.2) < 0.12, _d(P6))   # le flux VIDEO dure 4,2 s : il a bien ete boucle

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
