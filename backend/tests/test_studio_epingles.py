# -*- coding: utf-8 -*-
"""Plan-studio T1-T2 (tache #67 du suivi, PR A, 02/10/2026) — EPINGLER le resultat d'un noeud du Studio pour ne pas
le repayer, COTE SERVEUR : l'empreinte de la requete reelle, la substitution gratuite, le manifeste des parties.
DECISIONS DE L'UTILISATEUR (02/10) : l'empreinte est celle de la requete REELLE (modele effectif, format — HeyGen :
celui de la region —, mode voix effectif, CONTENU des fichiers) ; epingle automatique (cote editeur, PR B) ; un noeud
seul (/generate) n'a pas d'epingle.
Ce que le plan faisait faux, et que ce banc garde : une empreinte du GRAPHE qui ratait le format, le modele par defaut
et le mode voix (un clip au mauvais format reemploye) ; une garde de cout qui comptait les noeuds reemployes ; des
sous-rendus PAYES perdus quand un autre echoue (manifeste ecrit a la fin) ; les effets perdus sur un clip epingle.
Generations SIMULEES (aucun appel paye), composition ffmpeg simulee, data-dir isole, cles de banc.
Temoin positif : la base (dfc77040) n'a ni le module ni les routes.
Run (depuis backend/) : & $PY tests/test_studio_epingles.py"""
import json, os, pathlib, shutil, sqlite3, subprocess, sys, tempfile, types, uuid
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpin_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "dfc77040"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/studio_pins.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni le module ni les routes d'epingle", r0.returncode != 0 and r1.returncode == 0
      and b'"/jobs/{job_id}/parts"' not in r1.stdout and b'"/studio/pins/verifier"' not in r1.stdout)

sys.modules["fal_client"] = types.ModuleType("fal_client")
from PIL import Image                                               # noqa: E402
Image.new("RGB", (90, 160), (200, 40, 40)).save(_tmp / "images" / "depart.png")

try:
    from app.services import studio_pins as SP                      # noqa: E402
except ImportError as e:
    SP = None
    check("T2 le module existe", False, str(e))
from app.models.schemas import TemplateSlotValue                    # noqa: E402

SEED = {"image_filename": "depart.png", "custom_prompt": "Vane entre", "duration_s": 5}
HEY = {"avatar_id": "av1", "voice_id": "vx1", "script": "Bonjour."}


def sv(kind, payload, **kw):
    return TemplateSlotValue(**{"source_kind": kind, kind: payload, **kw})


if SP:
    print("[E] l'empreinte de la requete REELLE")
    e0 = SP.empreinte(sv("seedance", SEED))
    check("E1 stable, et sans effet de ce qui ne change pas le clip (max_usd, notes)",
          e0 == SP.empreinte(sv("seedance", dict(SEED, max_usd=3, notes="x"))) and e0 is not None and len(e0) == 32)
    from app.services.fal_service import DEFAULT_VIDEO_MODEL
    check("E2 le MODELE EFFECTIF : « aucun » = le defaut resolu (meme empreinte), un autre modele change tout",
          e0 == SP.empreinte(sv("seedance", dict(SEED, video_model=DEFAULT_VIDEO_MODEL)))
          and e0 != SP.empreinte(sv("seedance", dict(SEED, video_model="seedance-v1-pro"))))
    check("E3 le FORMAT (venu du noeud Rendu) change l'empreinte — le bug du plan", e0 != SP.empreinte(sv("seedance", dict(SEED, aspect_ratio="16:9"))))
    check("E4 le MODE VOIX effectif (celui du rendu quand le noeud n'en a pas) change l'empreinte",
          e0 != SP.empreinte(sv("seedance", SEED), voice_mode="oracle")
          and SP.empreinte(sv("seedance", SEED), voice_mode="oracle") == SP.empreinte(sv("seedance", dict(SEED, voice_mode="oracle"))))
    Image.new("RGB", (90, 160), (40, 40, 200)).save(_tmp / "images" / "depart.png")
    e_reecrit = SP.empreinte(sv("seedance", SEED))
    Image.new("RGB", (90, 160), (200, 40, 40)).save(_tmp / "images" / "depart.png")
    check("E5 une image REECRITE sous le meme nom change l'empreinte (le contenu compte, pas le nom)",
          e_reecrit != e0 and SP.empreinte(sv("seedance", SEED)) == e0)
    h0 = SP.empreinte(sv("heygen", HEY))
    check("E6 HeyGen : le format de la REGION entre dans l'empreinte ; un slot non genere n'en a pas",
          h0 != SP.empreinte(sv("heygen", HEY), heygen_aspect="1:1") and SP.empreinte(TemplateSlotValue(source_kind="text", text="x")) is None)

# ── la route, le rendu ────────────────────────────────────────────────────────────────────────────────────────────
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402
from app.services.storage import JobRecord                          # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
CLIP = _tmp / "clip.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x112:d=1", "-pix_fmt", "yuv420p", str(CLIP)], capture_output=True, check=True)
APPELS, ECHEC, RENDUS = [], {"heygen": False, "seedance": False}, []


async def _faux_sous_rendu(kind, req):
    from app.services.storage import async_session_factory
    from app.models.schemas import JobStatus
    APPELS.append(kind)
    jid = str(uuid.uuid4())
    out = _tmp / "outputs" / f"{kind}_{jid[:8]}.mp4"
    shutil.copy(CLIP, out)
    rate = ECHEC[kind]
    async with async_session_factory() as s:
        s.add(JobRecord(id=jid, status=(JobStatus.FAILED.value if rate else JobStatus.DONE.value), progress=100,
                        title=kind, image_filename=f"{kind}_{jid[:8]}", provider=kind,
                        final_video_path=None if rate else str(out), video_path=None if rate else str(out),
                        error="echec simule" if rate else None, completed_at=datetime.utcnow()))
        await s.commit()
    return jid


async def _faux_run(self, req, *a, **k):
    return await _faux_sous_rendu("seedance", req)


async def _faux_heygen(self, req, *a, **k):
    return await _faux_sous_rendu("heygen", req)


def _fausse_compo(template_id, resolved, out_path, template=None):
    RENDUS.append({"resolved": {k: str(v.get("path", "")) for k, v in resolved.items()}, "template": template})
    shutil.copy(CLIP, out_path)
    return out_path


RT._op_voix_off = lambda req: [{"kind": "elevenlabs", "chars": 400}]   # la voix off PAR DEFAUT d'un Seedance, chiffree
RT.pipeline.__class__.run = _faux_run
RT.pipeline.__class__.run_heygen = _faux_heygen
RT.pipeline.template_engine.render = _fausse_compo
TPL = "tpl_classic_vstack_50_50"
GRAPHE = {"nodes": [{"id": "n1", "type": "Image", "props": {"filename": "depart.png"}},
                    {"id": "n2", "type": "Seedance", "props": {}},
                    {"id": "n5", "type": "Effects", "props": {"targets": ["n2"], "effects": [{"type": "grain", "amount": 0.3}]}}],
          "edges": [{"from": "n1", "to": "n2", "toPort": "image", "fromPort": "out"}]}


def corps(seed=SEED, hey=HEY, pins=None, **kw):
    pins = pins or {}
    return {"template_id": TPL, "max_usd": kw.pop("max_usd", 50), "source_graph": GRAPHE,
            "slot_values": {"animation": {"source_kind": "seedance", "seedance": seed, "node_id": "n2", "pin": pins.get("animation")},
                            "avatar": {"source_kind": "heygen", "heygen": hey, "node_id": "n3", "pin": pins.get("avatar")}}, **kw}


def depenses():
    try:
        return sqlite3.connect(str(_DB)).execute("SELECT count(*) FROM depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def statut(c, jid):
    return js(c.get(f"/api/jobs/{jid}")).get("status")


print("\n[R] le rendu de graphe")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    check("R1 manifeste : identifiant douteux 400, rendu sans manifeste 404",
          c.get("/api/jobs/a.b/parts").status_code == 400 and c.get(f"/api/jobs/{uuid.uuid4()}/parts").status_code == 404)
    n_dep = depenses()
    r = c.post(f"/api/layout-templates/{TPL}/render", json=corps())
    j1 = js(r).get("job_id")
    parts = js(c.get(f"/api/jobs/{j1}/parts")).get("parts", [])
    pm = {p["slot"]: p for p in parts}
    check("R2 premier tir : deux generations, le MANIFESTE des parties (noeud, sous-rendu, empreinte, pas de reemploi), depense notee",
          r.status_code == 200 and sorted(APPELS) == ["heygen", "seedance"] and statut(c, j1) == "done"
          and pm.get("animation", {}).get("node_id") == "n2" and pm.get("avatar", {}).get("node_id") == "n3"
          and all(p.get("reemploi") is False and p.get("job_id") and len(p.get("empreinte") or "") == 32 for p in parts)
          and depenses() > n_dep, f"{r.status_code} {APPELS} {parts}")
    from app.services.pipeline import _heygen_aspect_for_slot
    asp = _heygen_aspect_for_slot(RT.template_engine.get_template(TPL), "avatar")
    check("R3 l'empreinte du manifeste est CELLE du serveur (seedance : celle de la requete ; heygen : avec le format de SA region)",
          SP is not None and pm.get("animation", {}).get("empreinte") == SP.empreinte(sv("seedance", SEED))
          and asp is not None and pm.get("avatar", {}).get("empreinte") == SP.empreinte(sv("heygen", HEY), heygen_aspect=asp),
          f"{asp} {pm.get('avatar')}")
    pins = {s: {"job_id": p["job_id"], "empreinte": p["empreinte"]} for s, p in pm.items()}
    v = js(c.post("/api/studio/pins/verifier", json=corps(pins=pins))).get("slots", {})
    check("R4 la verification (avant tir) : les deux epingles VALENT, et rien n'est genere pour le dire",
          v.get("animation", {}).get("valide") is True and v.get("avatar", {}).get("valide") is True and len(APPELS) == 2, str(v))
    APPELS.clear(); RENDUS.clear()
    n_dep = depenses()
    r = c.post(f"/api/layout-templates/{TPL}/render", json=corps(pins=pins, max_usd=0))
    j2 = js(r).get("job_id")
    parts2 = js(c.get(f"/api/jobs/{j2}/parts")).get("parts", [])
    check("R5 deuxieme tir, rien n'a bouge : AUCUNE generation, AUCUNE depense, max_usd 0 accepte (le reemploi ne coute rien)",
          r.status_code == 200 and APPELS == [] and depenses() == n_dep and statut(c, j2) == "done"
          and all(p.get("reemploi") is True for p in parts2) and len(parts2) == 2, f"{r.status_code} {r.text[:160]} {APPELS}")
    eff = [x for x in (RENDUS[0]["template"] or {}).get("regions", []) if x.get("slot_name") == "animation"] if RENDUS else []
    check("R6 les EFFETS du noeud epingle tiennent (sa region garde son grain) et la composition lit le clip DEJA paye",
          eff and any(e.get("type") == "grain" for e in eff[0].get("effects") or [])
          and RENDUS[0]["resolved"].get("animation", "").endswith(pathlib.Path(js(c.get(f"/api/jobs/{pins['animation']['job_id']}")).get("final_video_path") or "x").name),
          str(eff)[:200])
    v = js(c.post("/api/studio/pins/verifier", json=corps(seed=dict(SEED, aspect_ratio="16:9"), pins=pins))).get("slots", {})
    APPELS.clear()
    r = c.post(f"/api/layout-templates/{TPL}/render", json=corps(seed=dict(SEED, aspect_ratio="16:9"), pins=pins, max_usd=0))
    check("R7 le FORMAT a change : l'epingle Seedance ne vaut plus (et c'est dit), max_usd 0 REFUSE — on ne regenere pas en douce",
          v.get("animation", {}).get("valide") is False and "changé" in v.get("animation", {}).get("raison", "")
          and v.get("avatar", {}).get("valide") is True and r.status_code in (402, 422) and APPELS == [], f"{v} {r.status_code}")
    r = c.post(f"/api/layout-templates/{TPL}/render", json=corps(seed=dict(SEED, aspect_ratio="16:9"), pins=pins))
    check("R8 ... avec le budget : seul le noeud change est regenere, l'avatar reste epingle", r.status_code == 200 and APPELS == ["seedance"], str(APPELS))
    from app.services.storage import async_session_factory
    import asyncio as _aio
    pas_fini = str(uuid.uuid4())

    async def _poser():
        async with async_session_factory() as s:
            s.add(JobRecord(id=pas_fini, status="generating_video", progress=50, title="en cours", image_filename="x",
                            provider="seedance", final_video_path=str(CLIP), video_path=str(CLIP)))
            await s.commit()
    _aio.run(_poser())
    v = js(c.post("/api/studio/pins/verifier", json=corps(pins={"animation": {"job_id": pas_fini, "empreinte": pins["animation"]["empreinte"]}}))).get("slots", {})
    check("R8b une epingle sur un rendu PAS FINI (meme avec un fichier) ne vaut pas", v.get("animation", {}).get("valide") is False
          and "pas fini" in v.get("animation", {}).get("raison", ""), str(v.get("animation")))
    fichier = pathlib.Path(js(c.get(f"/api/jobs/{pins['avatar']['job_id']}")).get("final_video_path") or "")
    fichier.unlink(missing_ok=True)
    v = js(c.post("/api/studio/pins/verifier", json=corps(pins=pins))).get("slots", {})
    check("R9 la video epinglee a DISPARU du disque : l'epingle ne vaut plus, et c'est dit", v.get("avatar", {}).get("valide") is False
          and "disparu" in v.get("avatar", {}).get("raison", ""), str(v.get("avatar")))
    APPELS.clear()
    ECHEC["seedance"] = True
    r = c.post(f"/api/layout-templates/{TPL}/render", json=corps(seed=dict(SEED, custom_prompt="autre")))
    j4 = js(r).get("job_id")
    parts4 = {p["slot"]: p for p in js(c.get(f"/api/jobs/{j4}/parts")).get("parts", [])}
    ECHEC["seedance"] = False
    check("R10 le Seedance ECHOUE (rendu en echec) : l'avatar, lui, a ete PAYE — il est quand meme au manifeste (epinglable)",
          statut(c, j4) == "failed" and sorted(APPELS) == ["heygen", "seedance"] and "avatar" in parts4 and "animation" not in parts4, f"{statut(c, j4)} {parts4}")
    APPELS.clear()
    r = c.post(f"/api/layout-templates/{TPL}/render", json=corps(pins=pins, preview=True))
    j5 = js(r).get("job_id")
    check("R11 l'APERCU ne genere rien et n'ecrit aucune partie", APPELS == [] and c.get(f"/api/jobs/{j5}/parts").status_code == 404)
    src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
    check("R12 les deux routes neuves ne sont pas payantes (ni recensees ni puits)", "/studio/pins/verifier" not in src and "/jobs/{job_id}/parts" not in src)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
