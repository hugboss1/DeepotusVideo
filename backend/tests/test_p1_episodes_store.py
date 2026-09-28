# -*- coding: utf-8 -*-
"""P1 t132 (lot B de #6, 28/09/2026) — LES EPISODES S'ENREGISTRENT, ET LA
NARRATION DEJA PAYEE N'EST PLUS REPAYEE.

Defaut : aucun store, aucun CRUD, aucun /narrate (spec 2026-06-22) ; l'etat
de la page Episodes se perdait au changement de vue, et chaque assemblage
repayait la narration ElevenLabs de TOUTES les scenes.
Decisions de l'utilisateur (28/09) : /narrate + REEMPLOI (cle = texte + voix
+ langue) ; bouton Enregistrer + enregistrement automatique a l'assemblage.

METHODE : la voix est SIMULEE (0 $) — elle ecrit un vrai mp3 ffmpeg et
COMPTE ses appels ; les fichiers ecrits sont LUS sur le disque. Temoin :
l'ancienne run_episode (base de branche, `git show`) narre chaque scene a
chaque rendu, sans aucune notion d'episode. Faute n6 : details par _d().
Run : & $PY tests/test_p1_episodes_store.py   (depuis backend/, PATH avec le ffmpeg de l'app)
"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1es_")
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

BASE = "4e7bcc2"
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


class FausseVoix:
    """Ecrit un vrai mp3 (0,05 s par caractere, borne 1..6 s) et compte."""
    appels: list = []
    @staticmethod
    def is_enabled():
        return True
    def generate_long(self, text, output_path=None, language="en", voice_id=None, **kw):
        FausseVoix.appels.append(text)
        dur = max(1.0, min(6.0, 0.05 * len(text)))
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={dur}",
                        str(output_path)], check=True, capture_output=True)
        return output_path


from app.config import settings                            # noqa: E402

print("\n[0] preconditions")
check("0.1 ffmpeg de l'app sur le PATH", bool(FF), "")
try:
    from app.services import episode_store as ES
except Exception as e:                                      # noqa: BLE001
    ES = None
    print("   (module absent :", e, ")")
check("0.2 module episode_store present", ES is not None, "")

SCENES = [{"text": "Premiere scene, la maree monte.", "image_filename": None, "motion": "kenburns",
           "illustration_prompt": "tide", "video_model": "seedance-v1-pro", "resolution": "720p", "champ_futur": 7},
          {"text": "Deuxieme scene, le poulpe s'eveille.", "image_filename": None, "motion": "still"}]
DOC = {"title": "Chapitre 1", "language": "fr", "voice_id": "", "script": "Premiere scene...\n\nDeuxieme...",
       "scenes": SCENES, "scene_method": "paragraph", "scene_style": "", "narration": None}

print("\n[1] store (pur)")
if ES:
    e1 = ES.creer(DOC)
    lu = ES.lire(e1["id"])
    f1 = settings.outputs_path / "_episodes" / f"{e1['id']}.json"
    check("1.1 id ep_<hex12>, fichier outputs/_episodes/<id>.json ecrit", ES.ID_RE.fullmatch(e1["id"]) is not None and f1.is_file(), _d(e1["id"]))
    check("1.2 relu tel qu'ecrit : AUCUN champ de scene perdu (video_model, resolution, champ_futur)",
          lu and lu["scenes"] == SCENES and lu["title"] == "Chapitre 1" and lu["created_at"] and lu["updated_at"], _d(lu))
    import time as _t; _t.sleep(1.1)
    e1b = ES.remplacer(e1["id"], dict(DOC, title="Chapitre 1 bis", created_at="1999", id="ep_000000000000"))
    check("1.3 remplacer : garde id et created_at, avance updated_at, ignore l'id/created_at du corps",
          e1b["id"] == e1["id"] and e1b["created_at"] == e1["created_at"] and e1b["updated_at"] > e1["updated_at"]
          and ES.lire(e1["id"])["title"] == "Chapitre 1 bis", _d(e1b.get("id"), e1b.get("created_at")))
    e2 = ES.creer(dict(DOC, title="Autre", scenes=SCENES[:1]))
    li = ES.lister()
    check("1.4 lister : plus recent d'abord, resume (id, title, updated_at, scene_count, language)",
          [x["id"] for x in li] == [e2["id"], e1["id"]] and li[1]["scene_count"] == 2 and li[0]["title"] == "Autre"
          and "script" not in li[0], _d(li))
    _inval = []
    for mauvais in ("../x", "ep_zz", "ep_" + "0" * 13, "", None):
        try:
            _inval.append(ES.lire(mauvais) is None)
        except ValueError:
            _inval.append(True)
    check("1.5 ids invalides (traversee, hex, longueur) : jamais un fichier hors du store", all(_inval), _d(_inval))
    try:
        ES.creer(dict(DOC, script="x" * (ES.TAILLE_MAX + 10)))
        _gros = False
    except ValueError:
        _gros = True
    check("1.6 document trop gros : refuse (ValueError)", _gros, "")
    (settings.outputs_path / "episodes" / e2["id"] / "narr").mkdir(parents=True, exist_ok=True)
    check("1.7 supprimer : fichier ET dossier media retires", ES.supprimer(e2["id"]) is True
          and not (settings.outputs_path / "_episodes" / f"{e2['id']}.json").exists()
          and not (settings.outputs_path / "episodes" / e2["id"]).exists() and ES.supprimer(e2["id"]) is False, "")
    k1 = ES.cle_narration("Bonjour", "v1", "fr")
    check("1.8 cle de narration : texte + voix + langue (espaces de bord ignores)",
          k1 == ES.cle_narration("  Bonjour ", "v1", "fr") and k1 != ES.cle_narration("Bonjour", "v2", "fr")
          and k1 != ES.cle_narration("Bonjour", "v1", "en") and k1 != ES.cle_narration("Bonjour!", "v1", "fr"), "")

print("\n[2] routes CRUD")
from app.main import app                                    # noqa: E402
from app.api import routes as RT                            # noqa: E402
from app.services.elevenlabs_service import VoiceoverService  # noqa: E402
VoiceoverService.is_enabled = staticmethod(lambda: True)
_lances = []
async def _faux_run_episode(**kw):
    _lances.append(kw)
_vrai_run = RT.pipeline.run_episode


async def _http(fn):
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1/api", timeout=120) as c:
        return await fn(c)


async def _crud(c):
    cr = await c.post("episodes", json=DOC)
    eid = cr.json().get("id") if cr.status_code == 200 else ""
    li = await c.get("episodes")
    g = await c.get(f"episodes/{eid}")
    pu = await c.put(f"episodes/{eid}", json=dict(DOC, title="Titre PUT"))
    g2 = await c.get(f"episodes/{eid}")
    inc = await c.get("episodes/ep_ffffffffffff")
    bad = await c.get("episodes/ep_..%2F..%2Fx")
    return eid, cr, li, g, pu, g2, inc, bad

eid, cr, li, g, pu, g2, inc, bad = asyncio.run(_http(_crud))
check("2.1 POST /episodes -> id ; GET /episodes le liste", cr.status_code == 200 and eid
      and any(x["id"] == eid for x in (li.json().get("episodes") if li.status_code == 200 else [])), _d(cr.status_code, cr.text[:120]))
check("2.2 GET /episodes/{id} rend le document ; PUT le remplace", g.status_code == 200 and g.json().get("scenes") == SCENES
      and pu.status_code == 200 and g2.json().get("title") == "Titre PUT", _d(g.status_code, pu.status_code))
check("2.3 inconnu -> 404 ; chemin piege (..%2F) : jamais un document du store (404, ou la page SPA de secours)",
      inc.status_code == 404 and (bad.status_code in (400, 404, 422) or "text/html" in bad.headers.get("content-type", ""))
      and '"scenes"' not in bad.text, _d(inc.status_code, bad.status_code, bad.headers.get("content-type")))

print("\n[3] /episodes/{id}/narrate : narration par scene, cache, narration complete")
import app.services.pipeline as PLm                          # noqa: E402
RT.pipeline.voice = FausseVoix()
async def _narr(c):
    FausseVoix.appels = []
    n1 = await c.post(f"episodes/{eid}/narrate", json={})
    a1 = list(FausseVoix.appels)
    FausseVoix.appels = []
    n2 = await c.post(f"episodes/{eid}/narrate", json={})
    a2 = list(FausseVoix.appels)
    doc = (await c.get(f"episodes/{eid}")).json()
    doc["scenes"][1]["text"] = "Deuxieme scene, REECRITE."
    await c.put(f"episodes/{eid}", json=doc)
    FausseVoix.appels = []
    n3 = await c.post(f"episodes/{eid}/narrate", json={})
    a3 = list(FausseVoix.appels)
    return n1, a1, n2, a2, n3, a3, (await c.get(f"episodes/{eid}")).json()

n1, a1, n2, a2, n3, a3, docn = asyncio.run(_http(_narr))
j1 = n1.json() if n1.status_code == 200 else {}
check("3.1 premiere narration : 2 scenes narrees (2 appels payes), caracteres payes comptes",
      n1.status_code == 200 and len(a1) == 2 and j1.get("paid_chars") == sum(len(s["text"]) for s in SCENES)
      and [s.get("cached") for s in j1.get("scenes", [])] == [False, False], _d(n1.status_code, j1))
check("3.2 deuxieme narration identique : 0 appel, tout vient du cache", n2.status_code == 200 and a2 == []
      and n2.json().get("paid_chars") == 0, _d(a2, n2.text[:160]))
check("3.3 une scene reecrite : 1 seul appel (la seule modifiee)", n3.status_code == 200 and a3 == ["Deuxieme scene, REECRITE."],
      _d(a3))
_narr_fn = ((docn.get("narration") or {}).get("filename") or "")
check("3.4 narration complete dans la Bibliotheque audio, rattachee a l'episode, durees par scene",
      _narr_fn.endswith(".mp3") and (RT._audio_dir() / _narr_fn).is_file()
      and all((s.get("duration_s") or 0) > 0.5 for s in docn.get("scenes", [])), _d(docn.get("narration"), [s.get("duration_s") for s in docn.get("scenes", [])]))

print("\n[4] rendu : la narration deja payee est REEMPLOYEE")
from app.services.storage import init_db, async_session_factory, JobRecord  # noqa: E402
asyncio.run(init_db())


def _rendu(jid, scenes, episode_id=None):
    pl = PLm.Pipeline()
    pl.voice = FausseVoix()
    FausseVoix.appels = []
    kw = {"episode_id": episode_id} if episode_id else {}
    asyncio.run(pl.run_episode(job_id=jid, title="banc", voice_id=None, language="fr", scenes=scenes, **kw))
    async def _j():
        async with async_session_factory() as s:
            j = await s.get(JobRecord, jid)
            return j.status, json.loads(j.cost_meta or "{}")
    st, meta = asyncio.run(_j())
    return st, meta, list(FausseVoix.appels)

sc_doc = docn.get("scenes", [])
st1, meta1, ap1 = _rendu("es-r1", sc_doc, episode_id=eid)
check("4.1 rendu d'un episode deja narre : 0 appel TTS, chars payes = 0", st1 == "done" and ap1 == [] and meta1.get("chars") == 0,
      _d(st1, ap1, meta1))
sc_mod = [dict(sc_doc[0], text="Premiere scene, ENCORE modifiee."), sc_doc[1]]
st2, meta2, ap2 = _rendu("es-r2", sc_mod, episode_id=eid)
check("4.2 une scene modifiee : 1 appel, chars payes = sa longueur ; le rendu REMPLIT le cache",
      st2 == "done" and ap2 == ["Premiere scene, ENCORE modifiee."] and meta2.get("chars") == len("Premiere scene, ENCORE modifiee.")
      and ES and (ES.chemin_narration(eid, ES.cle_narration("Premiere scene, ENCORE modifiee.", "", "fr"))).is_file(),
      _d(st2, ap2, meta2))
st3, meta3, ap3 = _rendu("es-r3", sc_mod)
check("4.3 sans episode_id : comportement d'avant (chaque scene narree)", st3 == "done" and len(ap3) == 2, _d(ap3))
_g = subprocess.run(["git", "show", f"{BASE}:backend/app/services/pipeline.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
check("4.4 temoin : a la base, run_episode n'a pas de parametre episode_id (narration repayee a chaque rendu)",
      _g.returncode == 0 and "async def run_episode(self, *, job_id: str, title=None, voice_id=None," in _g.stdout
      and "episode_id" not in _g.stdout.split("async def run_episode(")[1].split("\n    async def ")[0], "")

print("\n[5] /episodes/render rattache le job a l'episode")
RT.pipeline.run_episode = _faux_run_episode
async def _rend(c):
    r1 = await c.post("episodes/render", json={"scenes": sc_mod, "episode_id": eid})
    r2 = await c.post("episodes/render", json={"scenes": sc_mod, "episode_id": "ep_ffffffffffff"})
    return r1, r2, (await c.get(f"episodes/{eid}")).json()
r1, r2, doc5 = asyncio.run(_http(_rend))
RT.pipeline.run_episode = _vrai_run
check("5.1 rendu avec episode_id : 200, episode_id transmis a la pipeline, last_job_id pose sur l'episode",
      r1.status_code == 200 and _lances and _lances[-1].get("episode_id") == eid and doc5.get("last_job_id") == r1.json().get("job_id"),
      _d(r1.status_code, doc5.get("last_job_id")))
check("5.2 episode inconnu : 404, rien en file", r2.status_code == 404 and len(_lances) == 1, _d(r2.status_code, len(_lances)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
