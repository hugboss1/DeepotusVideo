# -*- coding: utf-8 -*-
"""P1 #11 (28/09/2026) — UNE CLE DE FOURNISSEUR ABSENTE REPOND 503, PARTOUT.

Mesure du 28/09 (TestClient sans aucune cle, base 8a97e72) : les treize
voies image / 3D essayees repondaient TOUTES 400 (« FAL_KEY non configuree »,
« not configured »…) ; aucune 502 ; seule la dictee disait 503, et la forge
3D pour MESHY_API_KEY. 400 dit « ta requete est fautive » : faux, la requete
est bonne, c'est le serveur qui n'est pas configure. Le client lit le TEXTE
(dzProviderErr), aucun appelant ne branche sur le code (mesure : bundle,
couches, backend, scripts).
Decision de l'utilisateur (28/09) : 503 partout -- chaque refus « cle /
configuration de fournisseur absente » : « not configured », « non
configuree », « Aucune voix disponible — configure la cle », « Aucun LLM
configure », « … keys not set », « FIGMA_TOKEN absent » (409).
Le banc : [1] statique -- plus AUCUN HTTPException 4xx dont le message dit une
cle absente (temoin : la source de la base en a 43) ; [2] execute -- les
voies, sans cle, repondent 503 et le message nomme toujours la cle.
Faute n6 : details par _d().
Run : & $PY tests/test_p1_cle_absente.py   (depuis backend/)
"""
import asyncio, json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1ck_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                 # noqa: E402
logger.remove()
BASE = "8a97e72"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:700]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


# Un refus « cle absente » : HTTPException(<code>, <message>) dont le message (sur la ligne ou les deux suivantes) dit
# qu'une cle / un fournisseur n'est pas configure.
MOTIF = re.compile(r"not configured|non configur|Aucune voix disponible\s*[—:]\s*configure la cl|Aucun LLM configur|keys not set|FIGMA_TOKEN absent")
FICHIERS = ["app/api/routes.py", "app/services/cards/forge3d.py"]


def _refus(txt):
    """[(ligne, code)] des HTTPException dont le message dit une cle absente."""
    lignes = txt.splitlines()
    out = []
    for i, l in enumerate(lignes):
        m = re.search(r"HTTPException\((\d{3})\s*,?", l)
        if not m:
            continue
        bloc = " ".join(lignes[i:i + 3])[m.start():]
        k = bloc.find("raise ", 1)                       # le message s'arrete au raise suivant
        bloc = bloc if k < 0 else bloc[:k]
        if MOTIF.search(bloc):
            out.append((i + 1, int(m.group(1))))
    return out


print("\n[0] temoin : la source de la base (%s)" % BASE)
vieux = []
for f in FICHIERS:
    src = subprocess.run(["git", "show", f"{BASE}:backend/{f}"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")
    vieux += [(f, l, c) for l, c in _refus(src)]
_codes_vieux = sorted({c for _f, _l, c in vieux})
check("0.1 TEMOIN : a la base, 43 refus « cle absente » dont 40 en 400, 1 en 409 (Figma), 2 en 503 (Meshy)",
      len(vieux) == 43 and sum(1 for v in vieux if v[2] == 400) == 40 and sum(1 for v in vieux if v[2] == 409) == 1
      and sum(1 for v in vieux if v[2] == 503) == 2, _d(len(vieux), _codes_vieux, [v for v in vieux if v[2] != 400]))

print("\n[1] statique : plus aucun refus « cle absente » hors 503")
neufs = []
for f in FICHIERS:
    neufs += [(f, l, c) for l, c in _refus((BACKEND / f).read_text(encoding="utf-8"))]
check("1.1 les 43 refus sont toujours la, + 1 (tache #51 : /generate/extend, 01/10) + 1 (tache #63 : voix temoin de l'animatique, 02/10)"
      " + 1 (tache #66 : la reecriture, 02/10)", len(neufs) == 46, _d(len(neufs)))
check("1.2 et TOUS repondent 503", all(c == 503 for _f, _l, c in neufs), _d([v for v in neufs if v[2] != 503]))

print("\n[2] execute : sans aucune cle, les voies repondent 503 et nomment la cle")
from app.config import settings                           # noqa: E402
for k in ("FAL_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "ANTHROPIC_API_KEY",
          "FIGMA_TOKEN", "MESHY_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "X_API_KEY", "X_API_SECRET",
          "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
    if hasattr(settings, k):
        setattr(settings, k, "")
from app.services.storage import init_db                  # noqa: E402
asyncio.run(init_db())
from fastapi.testclient import TestClient                 # noqa: E402
from app.main import app                                  # noqa: E402
from PIL import Image                                      # noqa: E402
settings.images_path.mkdir(parents=True, exist_ok=True)
Image.new("RGB", (64, 64)).save(settings.images_path / "a.png")
c = TestClient(app)
VOIES = [
    ("generate nano-banana", "/api/images/generate", {"prompt": "chat", "model": "nano-banana"}, "FAL_KEY"),
    ("generate nano-banana-pro", "/api/images/generate", {"prompt": "chat", "model": "nano-banana-pro"}, "FAL_KEY"),
    ("generate flux", "/api/images/generate", {"prompt": "chat", "model": "flux"}, "FAL_KEY"),
    ("generate gpt-image-1", "/api/images/generate", {"prompt": "chat", "model": "gpt-image-1"}, "OPENAI_API_KEY"),
    ("edit nano-banana", "/api/images/process", {"op": "edit", "filename": "a.png", "prompt": "x", "model": "nano-banana"}, "FAL_KEY"),
    ("edit kontext", "/api/images/process", {"op": "edit", "filename": "a.png", "prompt": "x", "model": "flux"}, "FAL_KEY"),
    ("upscale ai", "/api/images/process", {"op": "upscale", "filename": "a.png", "mode": "ai"}, "FAL_KEY"),
    ("remove-bg api", "/api/images/process", {"op": "remove-bg", "filename": "a.png", "method": "api"}, "FAL_KEY"),
    ("assets/3d tripo", "/api/assets/3d", {"engine": "tripo", "image_filename": "a.png"}, "FAL_KEY"),
    ("assets/3d refine", "/api/assets/3d/x/refine", {}, "FAL_KEY"),
]
res = []
for nom, url, corps, cle in VOIES:
    r = c.post(url, json=corps)
    try:
        det = r.json().get("detail")
    except Exception:                                       # noqa: BLE001
        det = r.text[:80]
    res.append((nom, r.status_code, det))
    check(f"2.x {nom} : 503 et le message nomme {cle}", r.status_code == 503 and cle in str(det), _d(r.status_code, det))

import shutil                                              # noqa: E402
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
