"""Suite de t190 (12/10) — le tir GUIDÉ du Vectorlab : POST /images/process op « edit » chiffré comme le devis du panneau.

Le panneau « Image IA sur le calque » (frontend/vectorlab/js/mod-iacalque.js) demande à /api/cost/estimate une op
{kind: "image", model, n: 1} — la même que pour une génération. Ce banc vérifie que la GARDE de dépense de l'op edit
reçoit exactement cette op, pour les trois chemins de routes.py : un modèle de la façade (flux-3, nano-banana), FLUX
Kontext (« flux ») et GPT Image (gpt-image-2) ; que le modèle part bien de l'image GUIDE (image_path) ; et que
l'enveloppe de /images/process note l'image produite avec son guide pour parent (relation « edit »).

Données jetables (dossier temporaire), clés factices posées ici, AUCUN réseau : _plafond, IP.generate,
_flux_generate et LI.noter sont espionnés.
Run : & $PY tests/test_vectorlab_guide_devis.py   (depuis backend/)"""
import asyncio
import os
import pathlib
import sys
import tempfile

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for _k in ("ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "ANTHROPIC_API_KEY", "MESHY_API_KEY", "GEMINI_API_KEY"):
    os.environ[_k] = ""
os.environ["FAL_KEY"] = "banc-factice"
os.environ["OPENAI_API_KEY"] = "banc-factice"
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8")   # le harnais lit la sortie en UTF-8
except Exception:  # noqa: BLE001
    pass
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  PASS  " if cond else "  FAIL  ") + nom + ("" if cond else f" — {str(detail)[:300]}"))


async def main():
    from PIL import Image
    from httpx import AsyncClient, ASGITransport
    from app.api import routes as R
    from app.services import image_providers as IP
    from app.services import library_index as LI

    GUIDE = "vector_d1_guide_c3_k.png"
    Image.new("RGB", (64, 48), (240, 200, 40)).save(_tmp / "images" / GUIDE)

    gardes, tirs, notes = [], [], []

    async def plafond(op, categorie="", ref=None):
        gardes.append(dict(op))

    async def generate(provider, prompt, size, n=1, **kw):
        tirs.append({"modele": provider, "image": pathlib.Path(kw.get("image_path") or "").name, "size": size})
        return {"images": [f"gen_{provider}.png"], "seed": None}

    async def flux(prompt, size, n, **kw):
        tirs.append({"modele": "kontext", "image": pathlib.Path(kw.get("image_path") or "").name, "size": size})
        return {"images": ["gen_kontext.png"]}

    async def noter(noms, source, **kw):
        notes.append({"noms": list(noms), "source": source, **kw})

    R._plafond, IP.generate, R._flux_generate, LI.noter = plafond, generate, flux, noter

    from fastapi import FastAPI
    app = FastAPI()                       # le routeur seul, sans le lifespan de app.main (aucune tâche de fond)
    app.include_router(R.router, prefix="/api")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        for modele, op_garde in (("flux-3", "flux-3"), ("nano-banana", "nano-banana"), ("flux", "flux"),
                                 ("gpt-image-2", "gpt-image-2")):
            gardes.clear(); tirs.clear(); notes.clear()
            # le corps EXACT du panneau (requeteGuide)
            corps = {"op": "edit", "filename": GUIDE, "prompt": "un renard", "model": modele, "n": 1,
                     "size": "landscape_4_3", "source": "vectorlab"}
            r = await client.post("/api/images/process", json=corps)
            check(f"[{modele}] op edit : 200", r.status_code == 200, r.text)
            # le devis du panneau : {kind: "image", model, n: 1} (devisCorps) — la garde reçoit la même op
            devis = {"kind": "image", "model": modele, "n": 1}
            check(f"[{modele}] la garde reçoit l'op du devis du panneau {devis}",
                  gardes == [{"kind": "image", "n": 1, "model": op_garde}] and op_garde == devis["model"], gardes)
            check(f"[{modele}] le modèle part de l'image GUIDE, au format demandé",
                  len(tirs) == 1 and tirs[0]["image"] == GUIDE and tirs[0]["size"] == "landscape_4_3", tirs)
            n = notes[-1] if notes else {}
            check(f"[{modele}] provenance : l'image produite a son guide pour parent (relation edit)",
                  n.get("parent") == GUIDE and n.get("relation") == "edit" and n.get("noms") == r.json().get("images"), notes)

        # une clé absente : 503 AVANT la garde (rien de dépensé)
        os.environ["FAL_KEY"] = ""
        from app.config import settings
        cle = settings.FAL_KEY
        settings.FAL_KEY = ""
        gardes.clear()
        r = await client.post("/api/images/process", json={"op": "edit", "filename": GUIDE, "prompt": "x", "model": "flux-3", "n": 1})
        check("[sans clé] 503 qui nomme la clé, aucune garde (rien de dépensé)", r.status_code == 503 and "FAL_KEY" in r.text and not gardes, r.text)
        settings.FAL_KEY = cle

    print(f"\n=== {len(OK)} passed, {len(KO)} failed ===")
    return 1 if KO else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
