# -*- coding: utf-8 -*-
"""Avatar live t168e (10/10/2026) — (1) Kling v3 motion control d'après sa doc fal : UN visage lié, et seulement en
orientation « video » ; orientation « image » = 10 s au plus. (2) « Proposer une consigne d'après la prise » : une
image du milieu de la prise part au LLM de vision déjà branché (Anthropic, sinon OpenAI), sous la garde des plafonds ;
le lieu SEUL est décrit, en anglais, et la phrase est nettoyée avant d'être proposée. Sur de VRAIS fichiers ; le
LLM est un espion (aucun réseau).
Run (depuis backend/) : & $PY tests/test_avatar_decrire.py"""
import base64, io, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdecrire_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = ""
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FF = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")


def mp4(nom, secs):
    p = _tmp / nom
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size=720x1280:rate=24:duration={secs}",
                    "-pix_fmt", "yuv420p", str(p)], check=True, timeout=180)
    return p


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (600, 600), (200, 80, 40)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import recast_service as RS, plafonds             # noqa: E402

VISION, APPELS = [], []
REPONSE = {"t": '"The scene takes place in a sunlit wooden kitchen with copper pans and a window on a garden."'}


def f_vision(fournisseur, b64, media):
    VISION.append((fournisseur, b64, media))
    return REPONSE["t"]


async def f_up(path):
    return "https://fal.test/" + pathlib.Path(path).name


async def f_sub(endpoint, arguments):
    APPELS.append((endpoint, dict(arguments)))
    return {"video": {"url": "https://fal.test/s.mp4"}}


async def f_dl(url, dest):
    shutil.copy2(SRC12, dest)

RS._vision, RS._upload, RS._fal_subscribe, RS._download = f_vision, f_up, f_sub, f_dl
SRC5, SRC12 = mp4("cinq.mp4", 5), mp4("douze.mp4", 12)

print("\n[K] Kling v3 motion control, d'après sa doc fal")
prep = {"modele": "mouvement", "resolution": "source", "consigne": "", "orientation": "image"}
a = RS.arguments(prep, "V", ["I0", "I1"])
check("K1 orientation « image » : AUCUN élément de visage (fal ne le lie qu'en « video »)", "elements" not in a, str(a))
a = RS.arguments(dict(prep, orientation="video"), "V", ["I0", "I1", "I2", "I3", "I4"])
check("K2 orientation « video » : UN seul élément, visage frontal + 3 vues au plus",
      a.get("elements") == [{"frontal_image_url": "I0", "reference_image_urls": ["I1", "I2", "I3"]}], str(a))
check("K3 la consigne de nettoyage : guillemets et « The scene takes place » retirés, une phrase, vide si rien",
      RS.nettoyer_consigne(' "The scene takes place  in a red   room." ') == "in a red room."
      and RS.nettoyer_consigne("ok") == "" and len(RS.nettoyer_consigne("in " + "x" * 600)) <= 300)
check("K4 la consigne envoyée au LLM interdit de décrire les personnes", "Never" in RS._DECRIRE and "people" in RS._DECRIRE)

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    pid = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()], "consentement": True}).json()["id"]
    deps = {}
    for nom, src in (("cinq", SRC5), ("douze", SRC12)):
        with open(src, "rb") as fh:
            deps[nom] = loc.post("/api/avatar-live/recast/source", files={"fichier": (f"{nom}.mp4", fh, "video/mp4")}).json()["depot"]

    n = len(APPELS)
    r = loc.post("/api/avatar-live/recast", json={"source": {"depot": deps["douze"]}, "personnage_id": pid, "modele": "mouvement",
                                                  "orientation": "image"})
    check("K5 Kling orientation « image » et prise de 12 s : 400 qui le dit (10 s au plus), rien envoyé",
          r.status_code == 400 and "10 s" in r.text and len(APPELS) == n, r.text[:200])
    r = loc.post("/api/avatar-live/recast", json={"source": {"depot": deps["douze"]}, "personnage_id": pid, "modele": "mouvement",
                                                  "orientation": "video"})
    check("K6 la même prise en orientation « video » : acceptée (30 s au plus)", r.status_code == 200, r.text[:200])

    print("\n[D] proposer une consigne d'après la prise")
    r = loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": deps["cinq"]}})
    check("D1 sans clé Anthropic ni OpenAI : 400 qui le dit, aucun appel", r.status_code == 400 and "Anthropic" in r.text and not VISION, r.text[:200])
    settings.ANTHROPIC_API_KEY = "test-anthropic"
    r = loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": deps["cinq"]}})
    d = r.json() if r.status_code == 200 else {}
    check("D2 la consigne proposée, nettoyée ; Anthropic préféré ; devis LLM > 0",
          r.status_code == 200 and d.get("consigne") == "in a sunlit wooden kitchen with copper pans and a window on a garden."
          and d.get("fournisseur") == "anthropic" and d.get("devis_usd", 0) > 0, r.text[:300])
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(VISION[-1][1]))) if VISION else None
    check("D3 le LLM reçoit UNE image PNG de la prise (largeur ≤ 1024, proportions gardées)",
          im is not None and VISION[-1][2] == "image/png" and im.size[0] <= 1024 and abs(im.size[1] / im.size[0] - 1280 / 720) < 0.02,
          str(im and im.size))
    settings.OPENAI_API_KEY = "test-openai"
    r = loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": deps["cinq"]}})
    check("D3b les deux clés posées : Anthropic d'abord (le LLM par défaut de l'application)",
          r.status_code == 200 and r.json().get("fournisseur") == "anthropic" and VISION[-1][0] == "anthropic", r.text[:200])
    settings.OPENAI_API_KEY = ""
    plafonds.enregistrer({"par_moteur": {"anthropic": 0.000001}})
    nv = len(VISION)
    r = loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": deps["cinq"]}})
    check("D4 plafond Anthropic dépassé : 402, le LLM n'est PAS appelé", r.status_code == 402 and len(VISION) == nv, r.text[:200])
    plafonds.enregistrer({"par_moteur": {}})
    REPONSE["t"] = "  "
    r = loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": deps["cinq"]}})
    check("D5 réponse vide : 502 qui invite à écrire la consigne soi-même", r.status_code == 502 and "consigne" in r.text, r.text[:200])
    settings.ANTHROPIC_API_KEY = ""
    settings.OPENAI_API_KEY = "test-openai"
    REPONSE["t"] = "on a rainy rooftop at night with neon signs"
    r = loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": deps["cinq"]}})
    check("D6 sans Anthropic, OpenAI prend le relais", r.status_code == 200 and r.json().get("fournisseur") == "openai"
          and VISION[-1][0] == "openai", r.text[:200])
    check("D7 source inconnue : 404", loc.post("/api/avatar-live/recast/decrire", json={"source": {"depot": "f" * 24 + ".mp4"}}).status_code == 404)
    check("D8 depuis le Wi-Fi sans jeton : refusé", lan.post("/api/avatar-live/recast/decrire", json={}).status_code in (401, 403))
    settings.OPENAI_API_KEY = ""

print("\n[R] recensement")
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
k = ("avatar_live", "POST", "/recast/decrire")
check("R1 /recast/decrire atteint un puits ET appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
