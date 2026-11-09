"""Suite de t190 (12/10) — le tir GUIDÉ du Vectorlab : POST /images/process op « edit » chiffré comme le devis du panneau.

Le panneau « Image IA sur le calque » (frontend/vectorlab/js/mod-iacalque.js), case « guide » cochée, demande à
/api/cost/estimate une campagne dont l'op image est {kind: "image", model, n: 1, refs: 1, reglages: true}
(devisCorps({guide: true}) de frontend/shared/dz-iacalque-commun.js). Depuis t480/t481, la garde de l'op edit chiffre
{kind, n, model, refs: 1 + refs d'identité, qualite, resolution}, palier et résolution lus dans le corps ou dans les
réglages d'Atelier `image_qualite:<id>` / `image_resolution:<id>` ; le devis serveur résout `reglages` avec les mêmes
réglages. Ce banc vérifie, pour les trois chemins de routes.py — la façade (flux-3, nano-banana, et les modèles de
pricing.IMAGE_REF_USD qui facturent la référence : gpt-image-2-fal, nano-banana-2.1), FLUX Kontext (« flux ») et
GPT Image (gpt-image-2) —, sans réglage puis avec un palier et une résolution ENREGISTRÉS, que le montant du devis
du panneau est celui que la garde retient ; que le modèle part bien de l'image GUIDE (image_path) ; et que
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
    from app.services import pricing as PR
    from app.services.storage import init_db
    await init_db()                       # la table des réglages d'Atelier (palier / résolution enregistrés)

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
        reglages = {"image_qualite:gpt-image-2-fal": "medium", "image_resolution:nano-banana-2.1": "2K"}
        check("[réglages] les modèles de IMAGE_REF_USD du banc facturent bien la référence",
              {"gpt-image-2-fal", "nano-banana-2.1"} <= set(PR.IMAGE_REF_USD), sorted(PR.IMAGE_REF_USD))
        cas = [(m, m, False) for m in ("flux-3", "nano-banana", "flux", "gpt-image-2", "gpt-image-2-fal", "nano-banana-2.1")]
        cas += [("gpt-image-2-fal", "gpt-image-2-fal", True), ("nano-banana-2.1", "nano-banana-2.1", True)]
        for modele, op_garde, enregistre in cas:
            if enregistre and reglages:
                r = await client.put("/api/atelier/settings", json=reglages)
                check("[réglages] palier et résolution enregistrés (PUT /api/atelier/settings)", r.status_code == 200, r.text)
                reglages = None
            tag = f"{modele}{' · réglages' if enregistre else ''}"
            gardes.clear(); tirs.clear(); notes.clear()
            # le corps EXACT du panneau (requeteGuide)
            corps = {"op": "edit", "filename": GUIDE, "prompt": "un renard", "model": modele, "n": 1,
                     "size": "landscape_4_3", "source": "vectorlab"}
            r = await client.post("/api/images/process", json=corps)
            check(f"[{tag}] op edit : 200", r.status_code == 200, r.text)
            # le devis du panneau, case « guide » cochée (devisCorps({guide: true})) : l'image guide comptée en
            # référence, le palier / la résolution laissés au serveur (reglages: true), comme la garde
            devis = {"kind": "image", "model": modele, "n": 1, "refs": 1, "reglages": True}
            q, res = PR.qualite_image(modele, "medium" if enregistre else None), PR.resolution_image(modele, "2K" if enregistre else None)
            qualite = "medium" if enregistre and q else None
            resolution = "2K" if enregistre and res else None
            attendu = {"kind": "image", "n": 1, "model": op_garde} if modele == "flux" else                 {"kind": "image", "n": 1, "model": op_garde, "refs": 1, "qualite": qualite, "resolution": resolution}
            check(f"[{tag}] la garde reçoit {{kind, n, model, refs: 1, qualite, resolution}} (Kontext : l'op nue)",
                  gardes == [attendu], gardes)
            rd = await client.post("/api/cost/estimate", json={"kind": "campaign", "ops": [devis]})
            usd_devis = rd.json().get("total_usd") if rd.status_code == 200 else None
            usd_garde = PR.estimate(gardes[0])["total_usd"] if gardes else None
            check(f"[{tag}] le devis du panneau (/api/cost/estimate) chiffre le montant de la garde ({usd_garde} $)",
                  usd_devis is not None and usd_devis == usd_garde, (rd.status_code, usd_devis, usd_garde))
            if modele in PR.IMAGE_REF_USD or enregistre:
                nu = PR.estimate({"kind": "image", "model": modele, "n": 1})["total_usd"]
                check(f"[{tag}] l'op nue d'avant ({nu} $) ne suffisait pas : la garde retient autre chose",
                      nu != usd_garde, (nu, usd_garde))
            check(f"[{tag}] le modèle part de l'image GUIDE, au format demandé",
                  len(tirs) == 1 and tirs[0]["image"] == GUIDE and tirs[0]["size"] == "landscape_4_3", tirs)
            n = notes[-1] if notes else {}
            check(f"[{tag}] provenance : l'image produite a son guide pour parent (relation edit)",
                  n.get("parent") == GUIDE and n.get("relation") == "edit" and n.get("noms") == r.json().get("images"), notes)

        # reglages: true ne touche que l'op image qui le porte : une op nue reste chiffrée sans palier ni résolution
        rd = await client.post("/api/cost/estimate", json={"kind": "image", "model": "gpt-image-2-fal", "n": 1})
        check("[devis] sans reglages, le palier enregistré n'est pas appliqué (op nue inchangée)",
              rd.status_code == 200 and rd.json()["total_usd"] == PR.estimate({"kind": "image", "model": "gpt-image-2-fal", "n": 1})["total_usd"],
              rd.text)
        rd = await client.post("/api/cost/estimate", json={"kind": "image", "model": "gpt-image-2-fal", "n": 1, "refs": 1,
                                                           "reglages": True, "qualite": "low"})
        check("[devis] le palier du corps prime sur le réglage (comme à la garde)",
              rd.status_code == 200 and rd.json()["total_usd"] == PR.estimate({"kind": "image", "model": "gpt-image-2-fal", "n": 1,
                                                                                 "refs": 1, "qualite": "low"})["total_usd"], rd.text)

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
