"""t489 (FDA, lot « Fiches modèle ») — paramètre interne `methode` de la planche de référence d'un personnage.

« actuel » (défaut) = le code d'avant, à l'octet ; « ancre » = héros validé (contrôle d'identité CLIP) + texte de base
identique à l'octet + clause de vue, formulation positive ; « ancre_multi » = « ancre » + plusieurs références par vue
de corps. `face_maitre` (banc) réutilise un visage maître déjà produit. Aucun appel réseau : les générateurs, la
mesure de proportions et la similarité sont simulés.

Run: <python embarqué> backend/tests/test_atelier_methode.py
"""
import asyncio
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
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
IMG = pathlib.Path(_tmp, "images")
IMG.mkdir(exist_ok=True)
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")
sys.modules["fal_client"] = types.ModuleType("fal_client")

from PIL import Image as _PILImage                        # noqa: E402
from httpx import AsyncClient, ASGITransport              # noqa: E402
from app.main import app                                  # noqa: E402
from app.services.storage import init_db                  # noqa: E402
from app.api import routes as R                           # noqa: E402
from app.services import image_providers as IP, board_service as BS, proportion_qc as PQC  # noqa: E402

TIRS = []
_n = [0]


def _png():
    _n[0] += 1
    nom = f"t{_n[0]:04d}.png"
    _PILImage.new("RGB", (60, 80), (20 + _n[0] % 200, 60, 90)).save(IMG / nom)
    return nom


async def _flux(prompt, size, n, seed=None, model=None, image_path=None, ratio=None, guidance=None):
    TIRS.append({"voie": "flux", "prompt": prompt, "ref": image_path.name if image_path else None, "refs": None,
                 "seed": seed, "model": model})
    return {"images": [_png()], "seed": seed if seed is not None else 4242}


async def _ip(provider, prompt, size, n=1, seed=None, image_path=None, ratio=None, background=None,
              image_paths=None, sortie="raster", qualite=None, reecriture=None, resolution=None):
    TIRS.append({"voie": provider, "prompt": prompt, "ref": image_path.name if image_path else None,
                 "refs": [p.name for p in image_paths] if image_paths else None, "seed": seed})
    return {"images": [_png()], "seed": None}


R._flux_generate = _flux
IP.generate = _ip
PQC.measure = lambda p: None                    # pas de contrôle de proportions (vision payante) au banc
SIMS = []
APPELS_SIM = []


def _sim(base, a, b):
    APPELS_SIM.append((a, b))
    return SIMS.pop(0) if SIMS else 0.95


BS.similarite_identite = _sim
GARDES = []
_plafond0 = R._plafond


async def _espion_plafond(op, *a, **k):
    GARDES.append(dict(op) if isinstance(op, dict) else op)
    return await _plafond0(op, *a, **k)


R._plafond = _espion_plafond

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


async def planche(c, eid, corps):
    TIRS.clear()
    r = await c.post(f"/api/bible/entities/{eid}/generate", json=corps)
    rec = None
    if r.status_code == 200:
        e = (await c.get("/api/bible/entities?kind=character")).json()["entities"]
        e = [x for x in e if x["id"] == eid][0]
    return r, list(TIRS)


async def recette(eid):
    from app.services.storage import BibleEntity, async_session_factory
    async with async_session_factory() as s:
        e = await s.get(BibleEntity, eid)
        return json.loads(e.prompt_recipe)


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        eid = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Elias", "description": "jeune coursier, écharpe rouge, veste en cuir",
            "style_notes": "réaliste cinématographique"})).json()["id"]
        pid = (await c.post("/api/bible/entities", json={"kind": "place", "name": "Port",
                                                         "description": "port la nuit"})).json()["id"]

        print("\n[1] « actuel » : le code d'avant, à l'octet")
        r, t0 = await planche(c, eid, {"seed": 7})
        rec0 = await recette(eid)
        r, t1 = await planche(c, eid, {"seed": 7, "methode": "actuel"})
        rec1 = await recette(eid)
        cle = lambda t: [(x["prompt"], x["ref"] is not None, x["seed"], x["model"]) for x in t]   # noqa: E731
        check("1.1 sans méthode = « actuel » explicite : mêmes tirs, mêmes prompts", cle(t0) == cle(t1), (t0, t1))
        check("1.2 cinq tirs (visage, profil, corps, profil corps, dos)", len(t0) == 5, len(t0))
        check("1.3 recette sans clé de méthode (inchangée)", "methode" not in rec0 and "controle_heros" not in rec0
              and all("profondeur" not in p for p in rec0["panels"]), rec0)
        derives = [x["prompt"] for x in t0[1:]]
        check("1.4 prompts dérivés d'avant (« the exact same … », interdit écrit « no text »)",
              all("the exact same" in p for p in derives) and all("no text" in p for p in derives), derives)

        print("\n[2] « ancre » (FLUX) : base identique, clause de vue, formulation positive")
        r, t = await planche(c, eid, {"seed": 7, "methode": "ancre"})
        rec = await recette(eid)
        check("2.1 200", r.status_code == 200, r.text[:300])
        base = BS.base_ancre("Elias", "jeune coursier, écharpe rouge, veste en cuir", "réaliste cinématographique")
        derives = {p["key"]: p["prompt"] for p in rec["panels"] if p["key"] != "face_front"}
        check("2.2 chaque panneau dérivé commence par LA MÊME base, à l'octet",
              all(p.startswith(base + " View:") or p.startswith(base + " ") for p in derives.values())
              and len({p[:len(base)] for p in derives.values()}) == 1, derives)
        check("2.3 la base est identique à l'octet (seule la vue change)",
              {p[len(base):].split("View:")[0].strip() for k, p in derives.items()} <= {""}, derives)
        check("2.4 formulation positive : plus de « no text », « plain unlettered »",
              all("no text" not in p and "plain unlettered" in p for p in derives.values()), derives)
        check("2.5 le visage maître garde le prompt d'avant", t[0]["prompt"] == t0[0]["prompt"], (t[0], t0[0]))
        check("2.6 recette : méthode « ancre », profondeur 1 partout", rec.get("methode") == "ancre"
              and all(p.get("profondeur") == 1 for p in rec["panels"] if p["key"] != "face_front"), rec["panels"])
        check("2.7 le canon de proportions reste dans la vue du corps de face",
              "heads" in derives["front"].lower() or "tall" in derives["front"].lower(), derives["front"][-200:])

        print("\n[3] héros validé")
        SIMS[:] = [0.50, 0.91]
        r, t = await planche(c, eid, {"seed": 7, "methode": "ancre"})
        rec = await recette(eid)
        ch = rec.get("controle_heros") or {}
        check("3.1 sous le seuil : une relance, la meilleure gardée", len(t) == 6 and ch.get("essais") == 2
              and ch.get("sim") == 0.91 and ch.get("valide") is True, (len(t), ch))
        SIMS[:] = [0.50, 0.40]
        r, t = await planche(c, eid, {"seed": 7, "methode": "ancre"})
        ch = (await recette(eid)).get("controle_heros") or {}
        check("3.2 relance pire : la première gardée, « non validé » dit", ch.get("sim") == 0.50
              and ch.get("valide") is False, ch)
        SIMS[:] = [0.95]
        r, t = await planche(c, eid, {"seed": 7, "methode": "ancre"})
        ch = (await recette(eid)).get("controle_heros") or {}
        check("3.3 au-dessus du seuil : aucune relance", len(t) == 5 and ch.get("essais") == 1 and ch.get("valide"), ch)
        BS_sim = BS.similarite_identite
        BS.similarite_identite = lambda *a: None
        r, t = await planche(c, eid, {"seed": 7, "methode": "ancre"})
        ch = (await recette(eid)).get("controle_heros") or {}
        BS.similarite_identite = BS_sim
        check("3.4 sans moteur CLIP : pas de relance, « non validé », sim None", len(t) == 5 and ch.get("sim") is None
              and ch.get("valide") is False, ch)
        APPELS_SIM.clear()
        r, t = await planche(c, eid, {"seed": 7})
        check("3.5 « actuel » : aucun contrôle de héros (ni dans la recette, ni calculé)",
              "controle_heros" not in (await recette(eid)) and not APPELS_SIM, APPELS_SIM)
        check("3.6 profondeur : « actuel » profil et dos à 2, « ancre » à 1, maître à 0",
              BS.profondeur("left", "actuel") == 2 and BS.profondeur("back", "actuel") == 2
              and BS.profondeur("face_left", "actuel") == 1 and BS.profondeur("left", "ancre") == 1
              and BS.profondeur("face_front", "ancre") == 0)

        print("\n[4] « ancre_multi » et refus")
        r, _ = await planche(c, eid, {"seed": 7, "methode": "ancre_multi"})
        check("4.1 FLUX (une seule entrée) : 400 avant tout tir", r.status_code == 400 and not TIRS, r.text[:200])
        await c.put("/api/atelier/settings", json={"image_provider": "nano-banana-2.1"})
        r, t = await planche(c, eid, {"methode": "ancre_multi"})
        rec = await recette(eid)
        par = {p["key"]: p for p in rec["panels"]}
        face, front = par["face_front"]["file"], par["front"]["file"]
        lb = [x for x in t if x["refs"]]
        check("4.2 profil et dos : deux références, visage maître puis corps validé",
              len(lb) == 2 and all(x["refs"] == [face, front] for x in lb), lb)
        check("4.3 la phrase des rôles est dans la clause de vue, pas dans la base",
              all(BS.ROLES_MULTI in x["prompt"] and x["prompt"].index(BS.ROLES_MULTI) > x["prompt"].index("Keep exactly")
                  for x in lb), [x["prompt"][-260:] for x in lb])
        check("4.4 recette : méthode et références gardées", rec.get("methode") == "ancre_multi"
              and par["left"].get("refs") == [face, front], par["left"])
        r, t = await planche(c, eid, {"methode": "ancre"})
        check("4.5 « ancre » sur Nano Banana : une seule référence par vue", r.status_code == 200
              and not any(x["refs"] for x in t), t)
        await c.put("/api/atelier/settings", json={"image_provider": "flux"})
        r, _ = await planche(c, eid, {"methode": "inventee"})
        check("4.6 méthode inconnue : 400", r.status_code == 400 and not TIRS, r.text[:200])
        r = await c.post(f"/api/bible/entities/{pid}/generate", json={"methode": "ancre"})
        check("4.7 méthode « ancre » sur un lieu : 400", r.status_code == 400, r.text[:200])

        print("\n[5] visage maître fourni (banc)")
        maitre = _png()
        GARDES.clear()
        r, t = await planche(c, eid, {"seed": 7, "methode": "ancre", "face_maitre": maitre})
        check("5.0 la garde de dépense ne chiffre pas le maître fourni (4 tirs, pas 5)",
              GARDES and GARDES[-1].get("n") == 4, GARDES)
        rec = await recette(eid)
        check("5.1 le maître n'est pas tiré : 4 tirs, recette « fourni »", len(t) == 4
              and rec["panels"][0] == {"key": "face_front", "prompt": "", "seed": None, "model": "fourni",
                                       "file": maitre}, (len(t), rec["panels"][0]))
        check("5.2 le profil du visage part du maître fourni", t[0]["ref"] == maitre, t[0])
        r, t = await planche(c, eid, {"seed": 7, "face_maitre": maitre})
        check("5.3 vaut aussi en « actuel » (le banc partage le maître entre bras)", len(t) == 4 and t[0]["ref"] == maitre)
        r, _ = await planche(c, eid, {"face_maitre": "absent.png"})
        check("5.4 maître absent : 400 avant tout tir", r.status_code == 400 and not TIRS, r.text[:200])

        print("\n[6] rejeu de recette")
        r, _ = await planche(c, eid, {"seed": 7, "methode": "ancre"})
        r, t = await planche(c, eid, {"use_recipe": True})
        check("6.1 une recette « ancre » se rejoue en « ancre »", (await recette(eid)).get("methode") == "ancre", t[:1])


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
