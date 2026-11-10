"""t488 (F6.10, lot « Fiches modèle ») — fond transparent des images.

Schémas fal relus le 09/11/2026 : seuls les GPT Image servis par fal (2, 2.5 Flare, 2.5 Sunburst) ont `background`
(auto | transparent | opaque) ; Nano Banana, FLUX 3, Seedream, Ideogram, Qwen n'en ont pas. Un fond transparent écrit
dans le prompt ne sort jamais du texte : le champ est posé d'office quand le modèle l'a, sinon la réponse le DIT.

Run: <python embarqué> backend/tests/test_fond_transparent.py
"""
import asyncio
import base64
import io
import json
import os
import pathlib
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["FAL_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-oa"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")

FAL = []


async def _fake_subscribe(model, arguments=None, **kw):
    FAL.append({"model": model, "arguments": dict(arguments or {})})
    return {"images": [{"url": "http://fal.test/img.png"}]}

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from PIL import Image as _PILImage                        # noqa: E402
import httpx as _httpx                                    # noqa: E402
from httpx import AsyncClient, ASGITransport              # noqa: E402

_buf = io.BytesIO()
_PILImage.new("RGB", (8, 8)).save(_buf, "PNG")
_PNG = _buf.getvalue()


class _R:
    status_code = 200
    content = _PNG
    text = ""

    def json(self):
        return {"data": [{"b64_json": base64.b64encode(_PNG).decode()}]}

    def raise_for_status(self):
        pass


class _C:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        return _R()

    async def get(self, *a, **k):
        return _R()

_httpx.AsyncClient = _C

from app.main import app                                  # noqa: E402
from app.services.storage import init_db                  # noqa: E402
from app.services import image_providers as IP, catalogue_ia as CI  # noqa: E402
from app.api import routes as R                           # noqa: E402

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


print("\n[1] qui a un vrai fond transparent")
oui = {"gpt-image-2-fal", "gpt-image-2.5-flare-fal", "gpt-image-2.5-sunburst-fal", "gpt-image-2.5-flare"}
tous = set(IP.PROVIDERS)
check("1.1 exactement les GPT via fal et Flare direct", {m for m in tous if IP.accepte_transparent(m)} == oui,
      {m for m in tous if IP.accepte_transparent(m)} ^ oui)
_, a = IP.build_fal_gpt_request("p", "square_hd", 1, None, model="gpt-image-2", background="transparent")
check("1.2 GPT Image 2 via fal : background envoyé (schéma du 09/11)", a.get("background") == "transparent", a)
_, a = IP.build_fal_gpt_request("p", "square_hd", 1, ["u"], model="gpt-image-2", background="transparent")
check("1.3 … en retouche aussi", a.get("background") == "transparent", a)
par = {e["id"]: e for e in CI.lister("image")}
check("1.4 catalogue : `transparent` sur les seuls modèles capables",
      {k for k, e in par.items() if e.get("transparent")} == oui, {k for k, e in par.items() if e.get("transparent")})

print("\n[2] demande écrite dans le prompt")
for p in ("a fox, transparent background", "logo on a TRANSPARENT PNG", "icon, background: transparent",
          "mascotte, fond transparent", "sticker sans fond", "objet détouré sur fond transparent", "no background, flat"):
    check(f"2.1 reconnu : {p!r}", IP.fond_transparent_demande(p))
for p in ("a transparent glass of water on a table", "white background", "fond blanc", "a background character"):
    check(f"2.2 non reconnu : {p!r}", not IP.fond_transparent_demande(p))


async def bloc_route():
    print("\n[3] route /images/generate")
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        FAL.clear()
        r = await c.post("/api/images/generate", json={"prompt": "a fox mascot, transparent background",
                                                      "model": "gpt-image-2-fal"})
        j = r.json()
        check("3.1 modèle capable + demande écrite : background posé d'office, rendu, sans note",
              FAL[-1]["arguments"].get("background") == "transparent" and j.get("background") == "transparent"
              and "notes" not in j, (FAL[-1:], j))
        r = await c.post("/api/images/generate", json={"prompt": "a fox mascot, transparent background",
                                                      "model": "nano-banana-2.1"})
        j = r.json()
        check("3.2 modèle sans fond transparent : rien d'inventé, et la réponse LE DIT",
              "background" not in FAL[-1]["arguments"] and j.get("notes") and "nano-banana-2.1" in j["notes"][0]
              and "background" not in j, (FAL[-1:], j))
        r = await c.post("/api/images/generate", json={"prompt": "a fox", "model": "flux-3", "background": "transparent"})
        check("3.3 champ background demandé sur un modèle incapable : dit aussi", bool(r.json().get("notes")), r.json())
        r = await c.post("/api/images/generate", json={"prompt": "a fox in a forest", "model": "gpt-image-2-fal"})
        j = r.json()
        check("3.4 sans demande : rien ne change (pas de background, pas de note)",
              "background" not in FAL[-1]["arguments"] and "notes" not in j and "background" not in j, (FAL[-1:], j))
    check("3.5 la recette garde le fond SERVI", R._recette_generation({"prompt": "x"}, {"images": ["a"],
                                                                                       "background": "transparent"}
                                                                      ).get("background") == "transparent")
    msg = json.loads((HERE.parent / "app/i18n/messages.json").read_text(encoding="utf-8")).get("ia.image.fond_opaque")
    check("3.6 note traduite FR/EN, nomme le modèle", msg and "{modele}" in msg["fr"] and "{modele}" in msg["en"], msg)


asyncio.run(bloc_route())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
