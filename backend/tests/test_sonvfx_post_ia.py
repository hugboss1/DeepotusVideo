# -*- coding: utf-8 -*-
"""Son & VFX › Post-traitement : générateurs IA selon les clés (t277, 22/10/2026).

Les générateurs du catalogue_ia qui TRANSFORMENT une vidéo deviennent des maillons PAYANTS de la pile de t276 :
fal (style, agrandir, interpolation, gestes VFX), Decart (restyle Lucy, par fal), ElevenLabs (habillage sonore, direct
ou par fal) et les bruitages vidéo → son de fal. Un générateur sans clé reste listé et choisissable (503 au lancement).
« Décrire le look » : une phrase passe par moteurs_texte.tirer_garde et rend une pile de presets LOCAUX, PROPOSÉE à
l'écran, jamais appliquée seule (décision Q5).
Sections :
  [G] générateurs : filtrés par nature (vidéo → vidéo, pas d'image requise), par fournisseur, sans clé listés ;
      nature « video_post » au catalogue_ia (interpolation FILM, restyle Decart) ;
  [N] pile mixte : maillons IA et locaux, ids, prompt requis, options du schéma, maillons locaux pour l'aperçu,
      étapes de rendu ;
  [D] devis : une ligne par maillon IA actif, mêmes chiffres que pricing.estimate, pile locale gratuite ;
  [R] routes : /generateurs, /devis, /rendre (503 sans clé, 409 sans confirmation, 402 au plafond, job à faux
      fournisseurs, Bibliothèque), /apercu (maillons IA ignorés), refus du réseau ;
  [L] « Décrire le look » : tirer_garde (catégorie « son », JSON), pile proposée bornée, aucun job, refus ;
  [P] recensement payant : /api/post/rendre atteint le puits et passe la garde ; provider « post » inchangé ;
  [S] [W] [K] la page : source aplatie, sous node (Générer, pastilles de clé, devis, armement, proposition), textes.
Aucun appel réel : fal, ElevenLabs et le moteur de texte sont remplacés par des faux.
Run (depuis backend/) : & $PY tests/test_sonvfx_post_ia.py"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile

_tmp = tempfile.mkdtemp(prefix="dzpostia277_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(RACINE / "backend"))
sys.path.insert(0, str(_ICI))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:700]}")


def _leve(f, typ=ValueError):
    try:
        f()
    except typ:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


from loguru import logger  # noqa: E402
logger.remove()
from app.config import settings  # noqa: E402
from app.services import catalogue_ia as CI, pricing as PR, vfx_ia as VI, sfx_service as SX  # noqa: E402
from app.services import moteurs_texte as MT, effects_engine as FX  # noqa: E402
try:
    from app.services import post_ia as PI  # noqa: E402
except Exception as _e:  # noqa: BLE001
    PI = None
    print(f"  (post_ia introuvable : {_e})")

W = pathlib.Path(_tmp)
FF = shutil.which("ffmpeg") or "ffmpeg"
_CLES0 = {k: getattr(settings, k, "") for k in ("FAL_KEY", "ELEVENLABS_API_KEY")}


def _cles(fal="", eleven=""):
    settings.FAL_KEY = fal
    settings.ELEVENLABS_API_KEY = eleven


def _ffmpeg(*args):
    subprocess.run([FF, "-y", "-v", "error", *args], check=True, capture_output=True, timeout=120)


def _flux(p):
    r = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True, timeout=60)
    return sorted(set(r.stdout.split()))


SRC = W / "src.mp4"
_ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=4", "-f", "lavfi", "-i", "sine=f=440:d=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(SRC))
MUET = W / "muet.mp4"
_ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x180:r=24:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(MUET))
OUTV = W / "fal_sortie.mp4"
_ffmpeg("-f", "lavfi", "-i", "color=c=red:s=320x180:r=24:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(OUTV))
WAV = W / "son.wav"
_ffmpeg("-f", "lavfi", "-i", "sine=f=880:d=4", str(WAV))

# ── [G] générateurs ───────────────────────────────────────────────────────────────────────────────────────────────
print("[G] générateurs")
check("G0 le service post_ia existe", PI is not None)
_cles()
G = PI.generateurs() if PI else []
GI = {g["id"]: g for g in G}
_vfx_video = [m for m in VI.ids() if VI.REGISTRE[m]["entree"] == "video" and VI.REGISTRE[m]["image"] != "requis"]
check("G1 chaque geste VFX vidéo → vidéo sans image requise est un générateur ; ni PixVerse (image) ni relight (image requise)",
      all(f"vfx:{m}" in GI for m in _vfx_video) and "vfx:effets-pixverse" not in GI and "vfx:relight-h3" not in GI,
      sorted(GI))
check("G2 les bruitages vidéo → son de fal sont des générateurs « son »",
      all(GI.get(f"sfx_video:{m}", {}).get("famille") == "son" for m in SX.ids_sfx(SX.SFX_VIDEO)))
check("G3 ElevenLabs : direct (clé ELEVENLABS_API_KEY) et par fal (FAL_KEY), fournisseur « elevenlabs », prompt requis",
      GI.get("sfx:elevenlabs-direct", {}).get("cle") == "ELEVENLABS_API_KEY"
      and GI.get("sfx:elevenlabs-v2-fal", {}).get("cle") == "FAL_KEY"
      and all(GI.get(i, {}).get("fournisseur") == "elevenlabs" and GI[i].get("prompt") == "requis"
              for i in ("sfx:elevenlabs-direct", "sfx:elevenlabs-v2-fal"))
      and not any(i.startswith("sfx:") and i not in ("sfx:elevenlabs-direct", "sfx:elevenlabs-v2-fal") for i in GI))
check("G4 Decart : restyle Lucy par fal, 0,01 $/s, prompt requis",
      GI.get("video_post:restyle-decart", {}).get("fournisseur") == "decart"
      and GI["video_post:restyle-decart"].get("usd") == 0.01 and GI["video_post:restyle-decart"].get("unite") == "s"
      and GI["video_post:restyle-decart"].get("prompt") == "requis" and GI["video_post:restyle-decart"].get("cle") == "FAL_KEY",
      GI.get("video_post:restyle-decart"))
check("G5 interpolation FILM (fal) : famille « interpolation », prix « à mesurer », option num_frames 1-4",
      GI.get("video_post:interpoler-film", {}).get("famille") == "interpolation"
      and GI["video_post:interpoler-film"].get("note") == "a_mesurer"
      and GI["video_post:interpoler-film"]["options"].get("num_frames", {}).get("num") == [1, 4],
      GI.get("video_post:interpoler-film"))
check("G6 familles : style (Kling O3, Flux 3, Decart), agrandir (Topaz), interpolation, son",
      GI.get("vfx:retoucher-kling", {}).get("famille") == "style" and GI.get("vfx:agrandir", {}).get("famille") == "agrandir"
      and {g["famille"] for g in G} >= {"style", "agrandir", "interpolation", "son"})
check("G7 ordre par fournisseur : fal, puis decart, puis elevenlabs", [g["fournisseur"] for g in G]
      == sorted([g["fournisseur"] for g in G], key=("fal", "decart", "elevenlabs").index) and G)
check("G8 SANS CLÉ : tous listés, dispo False, la clé nommée ; le prix reste connu",
      G and all(g["dispo"] is False and g["cle"] in ("FAL_KEY", "ELEVENLABS_API_KEY") for g in G)
      and GI["vfx:agrandir"]["usd"] > 0)
_cles(fal="fal-test")
check("G9 avec la clé fal : les générateurs fal disponibles, ElevenLabs direct toujours sans clé",
      PI and PI.generateurs()[0]["dispo"] is True
      and {g["id"]: g for g in PI.generateurs()}["sfx:elevenlabs-direct"]["dispo"] is False)
_cles()
check("G10 catalogue_ia : nature « video_post » (FILM, Decart) dans le catalogue unique",
      "video_post" in CI.natures() and {e["id"] for e in CI.lister("video_post")} == {"interpoler-film", "restyle-decart"})
check("G11 un générateur inconnu est refusé (ValueError nommée)", PI and _leve(lambda: PI.generateur("vfx:zzz")))
check("G12 chaque générateur a ses champs codés (aucun texte de prix en dur)",
      G and all(set(g) >= {"id", "nature", "modele", "fournisseur", "famille", "label", "voie", "cle", "dispo", "usd",
                           "unite", "note", "prompt", "sortie", "options"} for g in G))

# ── [N] pile mixte ────────────────────────────────────────────────────────────────────────────────────────────────
print("[N] pile mixte")
PILE = [{"preset": "grain16", "intensite": 40},
        {"ia": "video_post:restyle-decart", "prompt": "aquarelle douce"},
        {"preset": "vignette", "intensite": 50},
        {"preset": "bandes", "intensite": 100, "masque": True},
        {"ia": "vfx:agrandir", "options": {"upscale_factor": 2}, "masque": True}]
N = PI.normaliser(PILE) if PI else []
check("N1 la pile garde l'ordre ; un maillon IA est {ia, prompt, options, masque}",
      [m.get("ia") or m.get("preset") for m in N] == ["grain16", "video_post:restyle-decart", "vignette", "bandes",
                                                         "vfx:agrandir"]
      and N[1]["prompt"] == "aquarelle douce" and N[1]["masque"] is False and isinstance(N[1]["options"], dict), N)
check("N2 maillon IA inconnu refusé", PI and _leve(lambda: PI.normaliser([{"ia": "vfx:zzz"}])))
check("N3 preset local inconnu refusé comme avant", PI and _leve(lambda: PI.normaliser([{"preset": "zzz"}])))
check("N4 la pile entière (IA comprise) est bornée à PILE_MAX",
      PI and _leve(lambda: PI.normaliser([{"ia": "vfx:agrandir"}] * 25)))
check("N5 valider : prompt requis absent → ValueError ; option hors schéma → ValueError",
      PI and _leve(lambda: PI.valider([{"ia": "video_post:restyle-decart", "prompt": "  "}]))
      and _leve(lambda: PI.valider([{"ia": "vfx:agrandir", "options": {"upscale_factor": 9}}]))
      and _leve(lambda: PI.valider([{"ia": "video_post:interpoler-film", "options": {"zzz": 1}}])))
check("N6 valider : les options complétées de leurs défauts (Topaz x2, FILM 1 image)",
      PI and PI.valider([{"ia": "vfx:agrandir"}])[0]["options"].get("upscale_factor") == 2
      and PI.valider([{"ia": "video_post:interpoler-film"}])[0]["options"].get("num_frames") == 1)
check("N7 locaux : les seuls maillons locaux, dans l'ordre (l'aperçu ne montre qu'eux)",
      PI and [m["preset"] for m in PI.locaux(PILE)] == ["grain16", "vignette", "bandes"])
E = PI.etapes(PI.valider(PILE)) if PI else []
check("N8 étapes : locaux groupés, un maillon IA par étape, masqués et groupes vides écartés",
      [(k, [m.get("ia") or m.get("preset") for m in (v if k == "local" else [v])]) for k, v in E]
      == [("local", ["grain16"]), ("ia", ["video_post:restyle-decart"]), ("local", ["vignette", "bandes"])], E)
check("N9 actifs_ia et cles_manquantes : seuls les maillons IA visibles, clés nommées une fois",
      PI and [m["ia"] for m in PI.actifs_ia(PILE)] == ["video_post:restyle-decart"]
      and PI.cles_manquantes(PILE + [{"ia": "sfx:elevenlabs-direct", "prompt": "x"}, {"ia": "vfx:agrandir"}])
      == ["FAL_KEY", "ELEVENLABS_API_KEY"])
_cles(fal="fal-test", eleven="el-test")
check("N10 avec les clés : plus aucune clé manquante", PI and PI.cles_manquantes(PILE) == [])
_cles()

# ── [D] devis ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] devis")
OPD = PI.op_devis(PI.valider(PILE), 4.0, 320, 180) if PI else {}
EST = PR.estimate(OPD) if OPD else {"total_usd": -1, "breakdown": []}
check("D1 une ligne par maillon IA ACTIF (le masqué ne coûte rien) : Decart 4 s = 0,04 $",
      OPD.get("kind") == "composition" and len(OPD.get("parts") or []) == 1 and abs(EST["total_usd"] - 0.04) < 1e-9,
      (OPD, EST))
_p2 = [{"ia": "vfx:agrandir"}, {"ia": "sfx:elevenlabs-direct", "prompt": "pluie"}, {"ia": "sfx_video:sonilo-video"}]
_op2 = PI.op_devis(PI.valider(_p2), 4.0, 320, 180) if PI else {}
_attendu = sum(PR.estimate(o)["total_usd"] for o in (VI.op_vfx("agrandir", 4.0, VI.options_valides("agrandir", {}), 320, 180),
                                                     {"kind": "sfx", "duration_s": 4.0},
                                                     SX.op_sfx("sonilo-video", 4.0)))
check("D2 mêmes chiffres que les ops de chaque registre (Topaz, ElevenLabs direct, Sonilo vidéo)",
      _op2 and abs(PR.estimate(_op2)["total_usd"] - _attendu) < 1e-9 and _attendu > 0,
      (PR.estimate(_op2) if _op2 else None, _attendu))
check("D3 la ligne ElevenLabs direct est au fournisseur « elevenlabs », Topaz à « fal »",
      _op2 and {l["provider"] for l in PR.estimate(_op2)["breakdown"]} == {"fal", "elevenlabs"})
check("D4 habillage ElevenLabs : durée de la vidéo bornée à 22 s", PI and
      PR.estimate(PI.op_devis(PI.valider([{"ia": "sfx:elevenlabs-direct", "prompt": "x"}]), 60.0, 320, 180))["total_usd"]
      == PR.estimate({"kind": "sfx", "duration_s": 22.0})["total_usd"])
check("D5 pile sans maillon IA : devis nul", PI and PR.estimate(PI.op_devis(PI.valider(PILE[:1]), 4.0, 320, 180))["total_usd"] == 0)
check("D6 FILM : prix « à mesurer » (0 $) dit dans la ligne, jamais « gratuit »",
      PI and (lambda e: e["total_usd"] == 0 and e["breakdown"] and "mesurer" in str(e["breakdown"][0]["label"]))(
          PR.estimate(PI.op_devis(PI.valider([{"ia": "video_post:interpoler-film"}]), 4.0, 320, 180))))

# ── [R] routes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] routes /api/post")
from httpx import AsyncClient, ASGITransport  # noqa: E402
from sqlalchemy import select, func  # noqa: E402
from app.main import app  # noqa: E402
from app.services import plafonds as PLAF  # noqa: E402
from app.services.storage import init_db, async_session_factory, JobRecord, LibraryAsset, Depense  # noqa: E402
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())
FINAL = settings.outputs_path / "final"
FINAL.mkdir(parents=True, exist_ok=True)
shutil.copyfile(SRC, FINAL / "rendu_a.mp4")
shutil.copyfile(MUET, FINAL / "muet_b.mp4")

APPELS = {"fal": [], "eleven": [], "upload": [], "llm": []}


async def _f_upload(path):
    APPELS["upload"].append(pathlib.Path(path).name)
    return "https://fal.test/" + pathlib.Path(path).name


async def _f_subscribe(endpoint, arguments):
    APPELS["fal"].append((endpoint, dict(arguments)))
    if "sound-effects" in endpoint or "video-to-sound" in endpoint:
        return {"audio": {"url": "https://fal.test/son.wav"}}
    return {"video": {"url": "https://fal.test/sortie.mp4"}, "seed": 7}


async def _f_download(url, dest):
    shutil.copyfile(WAV if url.endswith(".wav") else OUTV, dest)


def _f_eleven(prompt, duree):
    APPELS["eleven"].append((prompt, duree))
    d = SX._audio_dir()
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(WAV, d / "sfx_eleven_test.wav")
    return [{"filename": "sfx_eleven_test.wav"}], None


for _mod in (VI, SX) + ((PI,) if PI else ()):
    for _n, _f in (("_upload", _f_upload), ("_fal_subscribe", _f_subscribe), ("_download", _f_download)):
        if hasattr(_mod, _n):
            setattr(_mod, _n, _f)
if PI and hasattr(PI, "_eleven_direct"):
    PI._eleven_direct = _f_eleven


async def _jobs():
    async with async_session_factory() as s:
        s.add(JobRecord(id="job-rendu", status="done", progress=100, title="Rendu A", image_filename="x",
                        final_video_path=str(FINAL / "rendu_a.mp4"), provider="kling"))
        s.add(JobRecord(id="job-muet", status="done", progress=100, title="Muet B", image_filename="x",
                        final_video_path=str(FINAL / "muet_b.mp4"), provider="kling"))
        await s.commit()


async def _depenses():
    async with async_session_factory() as s:
        return (await s.execute(select(func.count()).select_from(Depense))).scalar_one()


async def _jobs_post():
    async with async_session_factory() as s:
        return (await s.execute(select(JobRecord).where(JobRecord.provider == "post"))).scalars().all()


loop.run_until_complete(_jobs())
RES = {}
PILE_IA = [{"preset": "vignette", "intensite": 60}, {"ia": "video_post:restyle-decart", "prompt": "aquarelle"},
           {"preset": "grain16", "intensite": 40}]


async def _attendre(c, jid):
    for _ in range(400):
        j = (await c.get(f"/api/jobs/{jid}")).json()
        if j.get("status") in ("done", "failed"):
            return j
        await asyncio.sleep(0.25)
    return {}


async def _routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
        _cles()
        RES["gen"] = await c.get("/api/post/generateurs")
        RES["devis"] = await c.post("/api/post/devis", json={"source": "job-rendu", "pile": PILE_IA})
        RES["devis_mal"] = await c.post("/api/post/devis", json={"source": "job-rendu", "pile": [{"ia": "vfx:zzz"}]})
        RES["dep_devis"] = await _depenses()
        RES["r503"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE_IA, "confirme_cout": True})
        RES["dep_503"] = await _depenses()
        RES["jobs_503"] = len(await _jobs_post())
        _cles(fal="fal-test")
        RES["r400"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "confirme_cout": True,
                                                             "pile": [{"ia": "video_post:restyle-decart"}]})
        RES["r409"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE_IA})
        RES["jobs_409"] = len(await _jobs_post())
        PLAF.enregistrer({"global_usd": 0.001, "par_moteur": {}, "alerte_pct": 80})
        RES["r402"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE_IA, "confirme_cout": True})
        RES["fal_402"] = len(APPELS["fal"])
        RES["jobs_402"] = len(await _jobs_post())
        PLAF.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
        RES["rok"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE_IA, "confirme_cout": True,
                                                            "titre": "Pile IA"})
        RES["job"] = await _attendre(c, (RES["rok"].json() or {}).get("job_id"))
        RES["dep_ok"] = await _depenses()
        # habillage sonore ElevenLabs direct sur une vidéo muette, puis par fal sur une vidéo sonore
        _cles(fal="fal-test", eleven="el-test")
        RES["son"] = await c.post("/api/post/rendre", json={"source": "job-muet", "confirme_cout": True,
                                                            "pile": [{"ia": "sfx:elevenlabs-direct", "prompt": "pluie"}]})
        RES["job_son"] = await _attendre(c, (RES["son"].json() or {}).get("job_id"))
        RES["son_fal"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "confirme_cout": True,
                                                                "pile": [{"ia": "sfx:elevenlabs-v2-fal", "prompt": "vent"},
                                                                         {"ia": "vfx:agrandir"}]})
        RES["job_son_fal"] = await _attendre(c, (RES["son_fal"].json() or {}).get("job_id"))
        # l'aperçu ignore les maillons IA : même image que la pile locale seule
        RES["ap_ia"] = await c.post("/api/post/apercu", json={"source": "job-rendu", "pile": PILE_IA, "t": 1.0})
        RES["ap_loc"] = await c.post("/api/post/apercu", json={"source": "job-rendu", "pile": PI.locaux(PILE_IA) if PI else [],
                                                                "t": 1.0})
        # pile 100 % locale : gratuite, aucune confirmation demandée (comportement de t276)
        RES["loc"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": [{"preset": "vignette"}]})
        RES["job_loc"] = await _attendre(c, (RES["loc"].json() or {}).get("job_id"))
        _cles()
    async with AsyncClient(transport=ASGITransport(app=app, client=("192.168.1.20", 5000)), base_url="http://192.168.1.5") as c:
        RES["reseau"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE_IA, "confirme_cout": True})


try:
    loop.run_until_complete(_routes())
except Exception as e:  # noqa: BLE001
    print(f"  (routes : {type(e).__name__}: {e})")


def _j(k):
    r = RES.get(k)
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


def _st(k):
    r = RES.get(k)
    return getattr(r, "status_code", None)


g = _j("gen")
check("R1 GET /generateurs : les générateurs (sans clé : listés, dispo False) et les moteurs de texte",
      _st("gen") == 200 and len(g.get("generateurs") or []) == len(G) and all(x["dispo"] is False for x in g.get("generateurs") or [])
      and any(m.get("id") == "openai" for m in g.get("moteurs_texte") or []), _st("gen"))
d = _j("devis")
check("R2 POST /devis : total, lignes, clé manquante nommée, aucune dépense écrite",
      _st("devis") == 200 and abs(d.get("usd", -1) - 0.04) < 1e-9 and d.get("cles") == ["FAL_KEY"] and d.get("ia") == 1
      and len(d.get("lignes") or []) == 1 and RES.get("dep_devis") == 0, d)
check("R3 POST /devis : pile refusée → 400", _st("devis_mal") == 400, _st("devis_mal"))
check("R4 /rendre sans FAL_KEY : 503 qui nomme la clé et le générateur, AVANT la garde (aucune dépense, aucun job)",
      _st("r503") == 503 and "FAL_KEY" in str(_j("r503").get("detail")) and "Decart" in str(_j("r503").get("detail"))
      and RES.get("dep_503") == 0
      and RES.get("jobs_503") == 0, (_st("r503"), _j("r503")))
check("R5 prompt requis absent : 400", _st("r400") == 400, (_st("r400"), _j("r400")))
check("R6 sans confirmation du coût : 409 avec le devis, aucun job",
      _st("r409") == 409 and RES.get("jobs_409") == 0 and "0.04" in json.dumps(_j("r409")), (_st("r409"), _j("r409")))
check("R7 au-delà du plafond : 402 dz_plafond, fournisseur jamais appelé, aucun job",
      _st("r402") == 402 and "dz_plafond" in json.dumps(_j("r402")) and RES.get("fal_402") == 0
      and RES.get("jobs_402") == 0, (_st("r402"), _j("r402")))
jb = RES.get("job") or {}
check("R8 rendu confirmé : job fini, Decart Lucy appelé avec la consigne, une dépense écrite",
      _st("rok") == 200 and jb.get("status") == "done"
      and any(e == "decart/lucy-restyle" and a.get("prompt") == "aquarelle" for e, a in APPELS["fal"])
      and RES.get("dep_ok", 0) >= 1, (jb, APPELS["fal"][:3]))
_fin = pathlib.Path(jb.get("final_video_path") or jb.get("video_path") or "")
check("R9 la vidéo finale est un MP4 dans outputs/final, le dossier de travail est nettoyé",
      _fin.suffix == ".mp4" and _fin.is_file() and _fin.parent == FINAL
      and not any(f.is_file() for f in (settings.outputs_path / "post_tmp").rglob("*")), str(_fin))


async def _lib():
    async with async_session_factory() as s:
        return (await s.execute(select(LibraryAsset).where(LibraryAsset.filename == _fin.name))).scalars().first()


_la = loop.run_until_complete(_lib()) if _fin.name else None
check("R10 Bibliothèque : relation « post », mère = la source, recette avec la pile IA et le coût",
      _la is not None and _la.relation == "post" and "restyle-decart" in (_la.recette or "")
      and "usd" in (_la.recette or ""), getattr(_la, "recette", None))
js = RES.get("job_son") or {}
check("R11 habillage ElevenLabs direct sur une vidéo muette : appel direct (durée de la vidéo), son posé",
      js.get("status") == "done" and APPELS["eleven"] and APPELS["eleven"][0][0] == "pluie"
      and abs(float(APPELS["eleven"][0][1]) - 4.0) < 0.2
      and "audio" in _flux(js.get("final_video_path") or ""), (js, APPELS["eleven"]))
jsf = RES.get("job_son_fal") or {}
check("R12 ElevenLabs par fal puis Topaz : les deux étapes passent par fal dans l'ordre, son et image gardés",
      jsf.get("status") == "done"
      and [e for e, _ in APPELS["fal"]][-2:] == ["fal-ai/elevenlabs/sound-effects/v2", "topaz/upscale/video/precision"]
      and _flux(jsf.get("final_video_path") or "") == ["audio", "video"], (jsf, [e for e, _ in APPELS["fal"]]))
check("R13 l'aperçu ignore les maillons IA : même image que la pile locale seule",
      _st("ap_ia") == 200 and _st("ap_loc") == 200 and RES["ap_ia"].content == RES["ap_loc"].content)
check("R14 pile locale : gratuite, sans confirmation, job fini (t276 inchangé)",
      _st("loc") == 200 and (RES.get("job_loc") or {}).get("status") == "done", (_st("loc"), RES.get("job_loc")))
check("R15 hors boucle locale : refusé", _st("reseau") in (401, 403), _st("reseau"))

# ── [L] décrire le look ───────────────────────────────────────────────────────────────────────────────────────────
print("[L] décrire le look")
LLM = {"rep": "", "exc": None}


async def _f_tirer_garde(moteur, modele, prompt, systeme, max_tokens=4000, json=False, *, categorie="motion", ref=None,
                         timeout=90.0, effort=None, images=None):
    APPELS["llm"].append({"moteur": moteur, "prompt": prompt, "systeme": systeme, "json": json, "categorie": categorie})
    if LLM["exc"]:
        raise LLM["exc"]
    return LLM["rep"]


_MT0 = (MT.tirer_garde, MT.configure)
MT.tirer_garde = _f_tirer_garde
MT.configure = lambda m: m == "openai"


async def _look():
    RES["jobs_avant_look"] = len(await _jobs_post())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
        LLM["rep"] = json.dumps({"pile": [{"preset": "grain16", "intensite": 140}, {"preset": "zzz"},
                                          {"preset": "halation", "intensite": 35}, {"preset": "lut", "intensite": 50,
                                                                                    "params": {"preset": "kodak_warm"}},
                                          {"preset": "vignette"}, {"preset": "bandes"}, {"preset": "vhs"},
                                          {"preset": "duotone"}, {"preset": "nettete"}]})
        RES["look"] = await c.post("/api/post/decrire", json={"phrase": "pellicule 70s chaude, un peu abîmée"})
        RES["jobs_look"] = len(await _jobs_post())
        LLM["rep"] = "voici ```json\n[{\"preset\": \"vignette\", \"intensite\": 30}]\n```"
        RES["look_bloc"] = await c.post("/api/post/decrire", json={"phrase": "sombre"})
        RES["look_vide"] = await c.post("/api/post/decrire", json={"phrase": "   "})
        RES["look_long"] = await c.post("/api/post/decrire", json={"phrase": "x" * 600})
        LLM["rep"] = "je ne sais pas"
        RES["look_illisible"] = await c.post("/api/post/decrire", json={"phrase": "chaud"})
        RES["look_cle"] = await c.post("/api/post/decrire", json={"phrase": "chaud", "moteur": "gemini"})
        RES["look_inconnu"] = await c.post("/api/post/decrire", json={"phrase": "chaud", "moteur": "zzz"})
        MT.configure = lambda m: False
        RES["look_aucun"] = await c.post("/api/post/decrire", json={"phrase": "chaud"})
        MT.configure = lambda m: m == "openai"
        from fastapi import HTTPException as _HE
        LLM["exc"] = _HE(402, {"dz_plafond": True})
        RES["look_402"] = await c.post("/api/post/decrire", json={"phrase": "chaud"})
        LLM["exc"] = None


try:
    loop.run_until_complete(_look())
except Exception as e:  # noqa: BLE001
    print(f"  (décrire : {type(e).__name__}: {e})")
MT.tirer_garde, MT.configure = _MT0
lk = _j("look")
_pl = lk.get("pile") or []
check("L1 la phrase passe par tirer_garde (catégorie « son », JSON) avec le moteur configuré, la phrase et le catalogue",
      APPELS["llm"] and APPELS["llm"][0]["moteur"] == "openai" and APPELS["llm"][0]["categorie"] == "son"
      and APPELS["llm"][0]["json"] is True and "pellicule 70s" in APPELS["llm"][0]["prompt"]
      and all(p in APPELS["llm"][0]["systeme"] for p in FX.POST_PILE), APPELS["llm"][:1])
check("L2 pile PROPOSÉE : presets inconnus écartés, intensités bornées, au plus 6 maillons, tous locaux",
      _st("look") == 200 and lk.get("propose") is True and 1 <= len(_pl) <= 6
      and [m["preset"] for m in _pl][:3] == ["grain16", "halation", "lut"] and _pl[0]["intensite"] == 100
      and all("ia" not in m and m["preset"] in FX.POST_PILE for m in _pl), lk)
check("L3 la pile proposée est valide pour le moteur (post_pile.normaliser l'accepte telle quelle)",
      _pl and __import__("app.services.post_pile", fromlist=["x"]).normaliser(_pl) and True)
check("L4 rien n'est appliqué : aucun job créé par la proposition", RES.get("jobs_look") == RES.get("jobs_avant_look", -1),
      (RES.get("jobs_look"), RES.get("jobs_avant_look")))
check("L5 une réponse entourée de texte (bloc ```json, liste nue) est lue", _st("look_bloc") == 200
      and [m["preset"] for m in _j("look_bloc").get("pile", [])] == ["vignette"], _j("look_bloc"))
check("L6 phrase vide ou trop longue : 400", _st("look_vide") == 400 and _st("look_long") == 400,
      (_st("look_vide"), _st("look_long")))
check("L7 réponse illisible : 502", _st("look_illisible") == 502, (_st("look_illisible"), _j("look_illisible")))
check("L8 moteur choisi sans clé : 503 qui nomme sa clé ; moteur inconnu : 400 ; aucun moteur : 503",
      _st("look_cle") == 503 and "GEMINI_API_KEY" in str(_j("look_cle").get("detail")) and _st("look_inconnu") == 400
      and _st("look_aucun") == 503, (_st("look_cle"), _st("look_inconnu"), _st("look_aucun")))
check("L9 le 402 du plafond passe tel quel", _st("look_402") == 402, _st("look_402"))

# ── [P] recensement payant ────────────────────────────────────────────────────────────────────────────────────────
print("[P] recensement payant")
import _recensement_payant as RP  # noqa: E402
_rec = RP.recenser({k: v.read_text(encoding="utf-8") for k, v in RP.MODULES.items()}) if "post" in RP.MODULES else {}
check("P1 le module des routes /api/post est recensé", "post" in RP.MODULES)
check("P2 /rendre atteint le puits (appliquer_maillon) ET passe la garde des plafonds",
      bool(_rec.get(("post", "POST", "/rendre"), {}).get("puits")) and _rec[("post", "POST", "/rendre")]["garde"],
      _rec.get(("post", "POST", "/rendre")))
check("P3 /devis, /apercu et /generateurs n'atteignent aucun puits",
      all(not _rec.get(("post", m, u), {}).get("puits") for m, u in (("POST", "/devis"), ("POST", "/apercu"),
                                                                     ("GET", "/generateurs"))))
_tpg = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("P4 /api/post/rendre inscrite aux PAYANTES de test_plafonds_garde", '("post", "POST", "/rendre")' in _tpg)
_prs = (RACINE / "backend" / "app" / "api" / "post_routes.py").read_text(encoding="utf-8")
check("P5 aucun provider neuf : les rendus restent « post » (test_montage_eb_croise)",
      set(re.findall(r'provider="([a-z0-9_]+)"', _prs)) == {"post"})
_tmc = (_ICI / "test_montage_eb_croise.py").read_text(encoding="utf-8")
check("P6 la garde de /rendre est posée AVANT la création du job (lecture du source)",
      "_PLAF.verifier(" in _prs and _prs.find("_PLAF.verifier(") < _prs.find("s.add(JobRecord(", _prs.find("async def rendre(")))

# ── [S] [W] [K] la page ───────────────────────────────────────────────────────────────────────────────────────────
BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
SRCJ = (RACINE / "frontend" / "patches" / "sonvfx-post.js").read_bytes().decode("utf-8")
_i, _jj = BUNDLE.find("/*__dzsvparticules*/"), BUNDLE.find("/*__dzsvpost*/")
PAGE = BUNDLE[_i + len("/*__dzsvparticules*/"):_jj] if 0 <= _i < _jj else ""
print("[S] source et livré")
import patch_bundle_dzsonvfx as PSV  # noqa: E402
check("S1 le livré porte la source aplatie, à l'octet", PAGE and PAGE == PSV.aplatir(SRCJ))
check("S2 routes neuves appelées : générateurs, devis, décrire",
      all(u in PAGE for u in ('"/api/post/generateurs"', '"/api/post/devis"', '"/api/post/decrire"')))
check("S3 chaque route neuve existe côté serveur",
      all(f'@router.{m}("{u}")' in _prs for m, u in (("get", "/generateurs"), ("post", "/devis"), ("post", "/decrire"))))
check("S4 un générateur sans clé n'est JAMAIS désactivé (aucun disabled lié à dispo)",
      PAGE and not re.search(r"disabled:[^,}]*dispo", PAGE))
check("S5 aucun texte en dur dans la page", PAGE and not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', PAGE)
      and not re.search(r'"aria-label":"|placeholder:"|title:"|alt:"', PAGE))
check("S6 aucun arrondi dans la page", PAGE and "border-radius" not in PAGE and "borderRadius" not in PAGE
      and "border-radius" not in PSV.CSS_POST)
_spr = (RACINE / "frontend" / "dist" / "shared" / "icons" / "dz-icons.svg").read_text(encoding="utf-8")
_gl = sorted(set(re.findall(r'"(dz-[a-z0-9-]+)"', SRCJ)))
check("S7 chaque glyphe de la page existe dans le sprite", _gl and all(f'id="{x}"' in _spr for x in _gl),
      [x for x in _gl if f'id="{x}"' not in _spr])
check("S8 attributs d'accroche des maillons gardés (data-sv-post « maillon », data-preset) pour t278",
      '"data-sv-post":"maillon","data-preset":' in PAGE)

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("/*__dzsvparticules*/"),j=S.indexOf("/*__dzsvpost*/");if(i<0||j<i)throw new Error("page introuvable");
const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[],CLEAN={};
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p.d[q]))EFF.push([k,f]);H[k]={d:d||[]}},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const r={jsx:(t,p,k)=>({t,p,k}),jsxs:(t,p,k)=>({t,p,k}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
function dzSvpJson(res){return res.json().catch(()=>({})).then(d=>{if(!res.ok){const m=d&&d.detail;throw new Error((typeof m==="string"&&m)||("code "+res.status))}return d})}
let MINUT=[];function setTimeout(f){MINUT.push(f);return MINUT.length}function clearTimeout(h){if(h>0&&h<=MINUT.length)MINUT[h-1]=null}
function minuteries(){const m=MINUT;MINUT=[];m.forEach(f=>f&&f())}
let NB=0;const URL={createObjectURL:b=>"blob:"+(++NB),revokeObjectURL:u=>0};
class FormData{constructor(){this.e=[]}append(k,v){this.e.push([k,v&&v.name])}}
let APPELS=[],REP={};
const GEN={generateurs:[
 {id:"vfx:agrandir",nature:"vfx",modele:"agrandir",fournisseur:"fal",famille:"agrandir",label:"Agrandir (Topaz)",voie:"fal",cle:"FAL_KEY",dispo:false,usd:0.05,unite:"tranche10s",note:"",prompt:null,sortie:"video",
  options:{upscale_factor:{choix:null,defaut:2,num:[1,4],entier:false,bool:false,requis:false}}},
 {id:"video_post:interpoler-film",nature:"video_post",modele:"interpoler-film",fournisseur:"fal",famille:"interpolation",label:"FILM",voie:"fal",cle:"FAL_KEY",dispo:false,usd:0,unite:"video",note:"a_mesurer",prompt:null,sortie:"video",options:{}},
 {id:"video_post:restyle-decart",nature:"video_post",modele:"restyle-decart",fournisseur:"decart",famille:"style",label:"Lucy Restyle",voie:"fal",cle:"FAL_KEY",dispo:true,usd:0.01,unite:"s",note:"",prompt:"requis",sortie:"video",options:{}},
 {id:"sfx:elevenlabs-direct",nature:"sfx_texte",modele:"elevenlabs-direct",fournisseur:"elevenlabs",famille:"son",label:"ElevenLabs SFX",voie:"elevenlabs",cle:"ELEVENLABS_API_KEY",dispo:false,usd:0,unite:"s",note:"",prompt:"requis",sortie:"son",options:{}}],
 moteurs_texte:[{id:"openai",label:"OpenAI",dispo:true,cle:"OPENAI_API_KEY"},{id:"gemini",label:"Google Gemini",dispo:false,cle:"GEMINI_API_KEY"}]};
const CAT={pile_max:6,luts:[],presets:[
 {id:"grain16",type:"grain16",cat:"retro",intensite:true,defaut:55,params:[],bounds:{}},
 {id:"vignette",type:"vignette",cat:"lumiere",intensite:true,defaut:60,params:[],bounds:{}},
 {id:"halation",type:"halation",cat:"lumiere",intensite:true,defaut:50,params:[],bounds:{}}]};
function json(d,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(d),blob:()=>Promise.resolve({tag:"x"})})}
function fetch(u,o){o=o||{};const corps=o.body&&!(o.body instanceof FormData)?JSON.parse(o.body):null;APPELS.push([u,o.method||"GET",corps]);
 if(REP[u])return json(REP[u].d,REP[u].st);
 if(u==="/api/post/catalogue")return json(CAT);
 if(u==="/api/post/sources")return json({rendus:[{job_id:"jA",titre:"Rendu A",dur:4,w:320,h:180,alpha:false}],vfx:[],particules:[]});
 if(u==="/api/post/presets")return json({presets:[]});
 if(u==="/api/post/generateurs")return json(GEN);
 if(u==="/api/post/devis")return json({usd:0.04,lignes:[{label:"Lucy",usd:0.04,provider:"fal"}],cles:corps.pile.some(m=>m.ia==="sfx:elevenlabs-direct")?["ELEVENLABS_API_KEY"]:[],ia:corps.pile.filter(m=>m.ia).length});
 if(u==="/api/post/decrire")return json({propose:true,moteur:corps.moteur||"openai",pile:[{preset:"grain16",intensite:70,masque:false,params:{}},{preset:"halation",intensite:30,masque:false,params:{}}]});
 if(u==="/api/post/apercu")return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({}),blob:()=>Promise.resolve({tag:"a"})});
 if(u==="/api/post/rendre")return json({job_id:"jp1",status:"queued",usd:0.04});
 if(u.startsWith("/api/jobs/"))return json({status:"generating_video",progress:20});
 return json({},404)}
eval(CODE);
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null||n===false)return "";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join("");if(n.t==="glyph")return "";return n.p?texte(n.p.children):""}
let A=null;
function rendre(){HI=0;EFF=[];A=DzSvPost({go:v=>0});const e=EFF;EFF=[];
 e.forEach(([k,f])=>{if(CLEAN[k])CLEAN[k]();const c=f();CLEAN[k]=typeof c==="function"?c:null});return A}
async function calme(){for(let k=0;k<10;k++){await new Promise(r0=>setImmediate(r0));rendre()}}
async function tic(){minuteries();await calme()}
function sp(a){return tout(A,n=>n.p&&n.p["data-sv-post"]===a,[])[0]}
function tous(a){return tout(A,n=>n.p&&n.p["data-sv-post"]===a,[])}
function dans(m,a){return tout(m,n=>n.p&&n.p["data-sv-post"]===a,[])[0]}
function pile(){return tous("maillon").map(m=>m.p["data-ia"]||m.p["data-preset"])}
function appels(u){return APPELS.filter(a=>a[0]===u)}
const R={};
(async()=>{
rendre();await calme();
R.gen={section:!!sp("generer"),fourn:["fal","decart","elevenlabs"].map(f=>!!sp("fourn-"+f)),
 boutons:GEN.generateurs.map(q=>{const b=sp("gen-"+q.id);return b?[b.p.disabled===true,b.p["data-cle"]||"",texte(b)]:null})};
sp("src-jA").p.onClick();rendre();await tic();
R.sans_ia={devis:appels("/api/post/devis").length,devis_txt:!!sp("devis")};
sp("ajout-vignette").p.onClick();rendre();
sp("gen-video_post:restyle-decart").p.onClick();rendre();
sp("gen-vfx:agrandir").p.onClick();rendre();
R.ajout={pile:pile(),preset_ia:tous("maillon").map(m=>m.p["data-preset"]),prompt:!!dans(tous("maillon")[1],"ia-prompt"),
 opt:!!dans(tous("maillon")[2],"ia-opt-upscale_factor"),payant:texte(tous("maillon")[1])};
dans(tous("maillon")[1],"ia-prompt").p.onChange({target:{value:"aquarelle"}});rendre();
dans(tous("maillon")[2],"ia-opt-upscale_factor").p.onChange({target:{value:"3"}});rendre();
APPELS=[];await tic();
R.apercu=appels("/api/post/apercu").map(a=>a[2].pile.map(m=>m.preset||m.ia));
R.devis={appel:appels("/api/post/devis").map(a=>a[2])[0],txt:texte(sp("devis"))};
APPELS=[];sp("rendre").p.onClick();rendre();
R.arme={appels:appels("/api/post/rendre").length,arme:sp("rendre").p["data-arme"]!==undefined,txt:texte(sp("rendre"))};
sp("rendre").p.onClick();await calme();
R.envoi=appels("/api/post/rendre").map(a=>a[2])[0];
sp("gen-sfx:elevenlabs-direct").p.onClick();rendre();APPELS=[];await tic();
R.cle_manquante=texte(sp("devis"));
R.look={phrase:!!sp("look-phrase"),moteurs:texte(sp("look-moteur")),off:sp("look-proposer").p.disabled};
sp("look-phrase").p.onChange({target:{value:"pellicule 70s chaude"}});rendre();
sp("look-moteur").p.onChange({target:{value:"gemini"}});rendre();
const avant=pile();APPELS=[];sp("look-proposer").p.onClick();await calme();
R.propose={appel:appels("/api/post/decrire").map(a=>a[2])[0],items:tous("look-item").map(texte),pile_inchangee:JSON.stringify(pile())===JSON.stringify(avant),
 rendus:appels("/api/post/rendre").length};
sp("look-ecarter").p.onClick();rendre();R.ecarte={prop:!!sp("look-proposition"),pile:JSON.stringify(pile())===JSON.stringify(avant)};
sp("look-proposer").p.onClick();await calme();sp("look-ajouter").p.onClick();rendre();R.ajoute=pile();
sp("look-proposer").p.onClick();await calme();sp("look-remplacer").p.onClick();rendre();R.remplace=pile();
process.stdout.write(JSON.stringify(R));
})().catch(e=>{process.stdout.write(JSON.stringify({ERREUR:String(e&&e.stack||e)}))});
"""
with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False, encoding="utf-8") as _f:
    _f.write(HARNAIS)
_rn = subprocess.run(["node", _f.name, str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    R = json.loads(_rn.stdout or "{}")
except ValueError:
    R = {"ERREUR": _rn.stdout[-400:] + _rn.stderr[-400:]}
os.unlink(_f.name)
print("[W] sous node")
check("W0 le harnais tourne", "ERREUR" not in R and R, (R.get("ERREUR") or _rn.stderr)[:600])
gn = R.get("gen", {})
check("W1 section « Générer » : un groupe par fournisseur (fal, Decart, ElevenLabs)",
      gn.get("section") is True and gn.get("fourn") == [True, True, True], gn)
check("W2 sans clé : le générateur reste cliquable, pastille de la clé à ajouter ; avec clé : aucune pastille",
      [b[0] for b in gn.get("boutons") or [[1]]] == [False] * 4
      and [b[1] for b in gn["boutons"]] == ["FAL_KEY", "FAL_KEY", "", "ELEVENLABS_API_KEY"]
      and "ia.cle.a_ajouter" in gn["boutons"][0][2] and "ia.cle.a_ajouter" not in gn["boutons"][2][2]
      and "ia.prix.a_mesurer" in gn["boutons"][1][2], gn)
check("W3 pile sans maillon IA : aucun devis demandé", R.get("sans_ia") == {"devis": 0, "devis_txt": False}, R.get("sans_ia"))
a = R.get("ajout", {})
check("W4 ajouter un générateur : maillon IA dans la même pile (data-preset « ia », data-ia), consigne et options, « payant »",
      a.get("pile") == ["vignette", "video_post:restyle-decart", "vfx:agrandir"] and a.get("preset_ia") == ["vignette", "ia", "ia"]
      and a.get("prompt") is True and a.get("opt") is True and "sonvfx.postia.payant" in a.get("payant", ""), a)
check("W5 l'aperçu n'envoie que les maillons locaux (avant : pile vide ; après : la vignette seule)",
      R.get("apercu") and ["vignette"] in R["apercu"] and all(p in ([], ["vignette"]) for p in R["apercu"]),
      R.get("apercu"))
dv = R.get("devis", {})
check("W6 devis : la pile envoyée avec ses maillons IA (consigne, options) ; le coût affiché",
      dv.get("appel") == {"source": "jA", "pile": [{"preset": "vignette", "intensite": 60, "masque": False, "params": {}},
                                                   {"ia": "video_post:restyle-decart", "prompt": "aquarelle", "options": {}, "masque": False},
                                                   {"ia": "vfx:agrandir", "prompt": "", "options": {"upscale_factor": 3}, "masque": False}]}
      and "sonvfx.postia.devis" in dv.get("txt", "") and "0.04" in dv.get("txt", ""), dv)
am = R.get("arme", {})
check("W7 rendre une pile payante : le premier clic ARME (aucun appel), le bouton dit le coût à confirmer",
      am.get("appels") == 0 and am.get("arme") is True and "sonvfx.postia.confirmer" in am.get("txt", ""), am)
check("W8 le second clic envoie la pile avec confirme_cout", (R.get("envoi") or {}).get("confirme_cout") is True
      and [m.get("ia") or m.get("preset") for m in R["envoi"]["pile"]] == ["vignette", "video_post:restyle-decart", "vfx:agrandir"],
      R.get("envoi"))
check("W9 une clé manquante est dite sous le devis (le rendu reste possible : 503 au lancement)",
      "ELEVENLABS_API_KEY" in R.get("cle_manquante", ""), R.get("cle_manquante"))
lo = R.get("look", {})
check("W10 « Décrire le look » : phrase, moteurs (sans clé listés), bouton actif seulement avec une phrase",
      lo.get("phrase") is True and "OpenAI" in lo.get("moteurs", "") and "Google Gemini" in lo.get("moteurs", "")
      and lo.get("off") is True, lo)
pr = R.get("propose", {})
check("W11 proposer : phrase et moteur envoyés ; la pile proposée est AFFICHÉE, la pile n'a pas bougé, aucun rendu",
      pr.get("appel") == {"phrase": "pellicule 70s chaude", "moteur": "gemini"} and len(pr.get("items") or []) == 2
      and pr.get("pile_inchangee") is True and pr.get("rendus") == 0, pr)
check("W12 écarter : la proposition disparaît, la pile reste", R.get("ecarte") == {"prop": False, "pile": True}, R.get("ecarte"))
check("W13 ajouter la proposition à la pile, puis remplacer la pile par elle",
      (R.get("ajoute") or [])[-2:] == ["grain16", "halation"] and len(R.get("ajoute") or []) == 6
      and R.get("remplace") == ["grain16", "halation"], (R.get("ajoute"), R.get("remplace")))

print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "sonvfx_hub.json").read_text(encoding="utf-8"))
CLES = sorted(set(re.findall(r'dzT\("(sonvfx\.postia\.[a-z0-9_]+)"', PAGE)))
check("K1 chaque clé sonvfx.postia.* : FR et EN, mêmes variables",
      CLES and all((DICO.get(k) or {}).get("fr") and (DICO.get(k) or {}).get("en")
                   and set(re.findall(r"\{(\w+)\}", DICO[k]["fr"])) == set(re.findall(r"\{(\w+)\}", DICO[k]["en"]))
                   for k in CLES), [k for k in CLES if k not in DICO])
check("K2 aucune clé sonvfx.postia.* orpheline", sorted(k for k in DICO if k.startswith("sonvfx.postia.")) == CLES,
      sorted(set(k for k in DICO if k.startswith("sonvfx.postia.")) ^ set(CLES)))
_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K3 dictionnaire assemblé (source = copie de dist)", CLES and all(k.encode() in _dico for k in CLES)
      and _dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

for _k, _v in _CLES0.items():
    setattr(settings, _k, _v)
print(f"\n{ok} PASS / {fail} FAIL")
shutil.rmtree(_tmp, ignore_errors=True)


def test_sonvfx_post_ia():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
