# -*- coding: utf-8 -*-
"""T106 (plan-moteurs-3d T7, D1) — les vues d'un maillage viennent de la planche de la BIBLE au lieu d'un prompt neuf :
l'identité tenue par la bible est ce qu'on ne veut pas régénérer. Le banc COMPOSE une vraie planche avec board_service,
la rattache à une entité, et vérifie : aucune génération d'image (Seedream compté, jamais appelé), aucune dépense, les
vues par CLÉ (recette v3 ou découpe vérifiée de la planche, `_entity_ref_views` de la tâche #62), les refus parlants
(pas de planche, planche sans vue de face, mosaïque d'une autre géométrie), une vue de planche qui ne se « rejoue » pas
mais se détoure, et au tir le maillage qui rejoint la fiche de l'entité.
Run : python tests/test_asset3d_bible_vues.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzbibvues_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                        # noqa: E402
logger.remove()
from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3, gltf_builder     # noqa: E402
from app.services import asset3d_views as V, board_service as BS  # noqa: E402
from app.services.storage import init_db                         # noqa: E402

UPLOADS, EDITS, MOTEURS = [], [], []
_BASE = []


def _pret():
    if not _BASE:
        asyncio.run(init_db()); _BASE.append(1)


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/{pathlib.Path(p).name}"


async def _faux_seedream(url, prompt):
    EDITS.append(prompt)
    return "https://fal.test/jamais.png"


async def _faux_moteur(engine, args, endpoint=None):
    MOTEURS.append((engine, args))
    return {"mesh_url": "https://fal.test/m.glb", "format_urls": {}, "texture_urls": {}, "preview_url": None}


def _faux_download(url, dest, timeout=120):
    if str(dest).endswith(".glb"):
        dest.write_bytes(gltf_builder.build_glb({}, None, "cube", "m"))
    else:
        b = io.BytesIO(); Image.new("RGB", (8, 8), (0, 0, 0)).save(b, "PNG"); dest.write_bytes(b.getvalue())
    return True


A3._upload, A3._seedream_edit, A3._run_engine, A3._download = _faux_upload, _faux_seedream, _faux_moteur, _faux_download
COULEURS = {"front": (220, 40, 40), "left": (40, 220, 40), "right": (40, 40, 220), "back": (220, 220, 40)}


def _panneau(nom, couleur, w, h):
    Image.new("RGB", (w, h), couleur).save(settings.images_path / nom, "PNG")
    return nom


def _planche(prefixe="p") -> tuple[str, dict]:
    panels = {k: _panneau(f"{prefixe}_{k}.png", c, 300, 700) for k, c in COULEURS.items()}
    panels.update({f"face_{k}": _panneau(f"{prefixe}_f_{k}.png", tuple(v // 2 + 60 for v in COULEURS[k]), 300, 300)
                   for k in ("front", "left", "right")})
    return BS.compose_character_board(settings.images_path, panels), panels


def _vider():
    UPLOADS.clear(); EDITS.clear(); MOTEURS.clear()


def _dominante(fichier):
    im = Image.open(settings.images_path / fichier).convert("RGB")
    return im.getpixel((im.width // 2, int(im.height * 0.85)))


# ── service ──────────────────────────────────────────────────────────────────

def test_les_vues_venues_d_images_ne_coutent_aucune_generation():
    board, panels = _planche("s")
    _vider()
    r = asyncio.run(V.preparer_depuis_images(
        "bib_vues", {k: panels[k] for k in ("back", "left", "front", "right")},
        {"engine": "tripo-h3.1", "entity_id": "ent-42", "source": "recette"}))
    assert EDITS == [], "AUCUN appel Seedream : les vues existent déjà"
    assert r["vues"] == 4 and len(UPLOADS) == 4, (r, UPLOADS)
    vj = V.lire_vues("bib_vues")
    # l'ordre d'auteur (front, back, left, right), quel que soit l'ordre donné ; chaque vue garde SA clé
    assert [v["cle"] for v in vj["vues"]] == ["front", "back", "left", "right"], vj["vues"]
    assert [v["origine"] for v in vj["vues"]] == [panels[k] for k in ("front", "back", "left", "right")]
    assert all(v["role"] == "planche" and v["prompt"] is None for v in vj["vues"]), vj["vues"]
    assert vj["etat"] == "en_attente" and vj["entity_id"] == "ent-42" and vj["source"] == "recette", vj
    assert vj["image_filename"] == panels["front"], vj
    d = settings.outputs_path / "assets3d" / "bib_vues"
    assert all((d / f"shot_{i}.png").is_file() for i in range(4))


def test_les_refus_du_service():
    _, panels = _planche("r")
    for mauvais, mot in (({}, "1 à 4"), ({"left": panels["left"]}, "face"),
                         ({"front": "absente.png"}, "library"), ({"front": panels["front"], "top": panels["left"]}, "top")):
        try:
            asyncio.run(V.preparer_depuis_images("bib_ko", mauvais, {"engine": "tripo"}))
            raise AssertionError(f"aurait dû refuser {mauvais}")
        except ValueError as e:
            assert mot in str(e).lower(), (mot, e)


def test_une_vue_de_planche_ne_se_rejoue_pas_mais_se_detoure():
    _, panels = _planche("d")
    asyncio.run(V.preparer_depuis_images("bib_det", {"front": panels["front"], "back": panels["back"]}, {}))
    try:
        asyncio.run(V.rejouer_vue("bib_det", 1)); raise AssertionError("rejouée")
    except ValueError as e:
        assert "planche" in str(e), e
    r = asyncio.run(V.detourer_vue("bib_det", 0, via="local"))
    assert r["via"] == "local", r


def test_tirer_un_jeu_de_planche_respecte_l_ordre_du_moteur():
    _, panels = _planche("t")
    asyncio.run(V.preparer_depuis_images("bib_tir", {k: panels[k] for k in COULEURS}, {"engine": "tripo-h3.1"}))
    _vider()
    asyncio.run(V.tirer_vues("bib_tir"))
    envoyees = next(x for x in MOTEURS[0][1].values() if isinstance(x, list))
    noms = [u.rsplit("/", 1)[-1] for u in envoyees]
    assert noms == [panels[k] for k in ("front", "left", "back", "right")], noms   # [front, left, back, right] de H3.1
    assert A3.read_manifest("bib_tir")["image_filename"] == panels["front"]


# ── route de la bible ────────────────────────────────────────────────────────

def test_route_from_board():
    _pret()
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy import func, select
    from app.main import app
    from app.services.storage import BibleEntity, Depense, JobRecord, async_session_factory
    board_dec, panels_dec = _planche("bd")            # planche SANS recette : découpe vérifiée
    board_rec, panels_rec = _planche("br")            # planche AVEC recette v3 : les panneaux d'origine
    mosaique = _panneau("board_mosaique.png", (242, 239, 233), 900, 500)

    async def entites():
        async with async_session_factory() as s:
            s.add(BibleEntity(id="e-dec", kind="character", name="Le Prophète", ref_image=board_dec))
            s.add(BibleEntity(id="e-rec", kind="character", name="L'Oracle", ref_image=board_rec,
                              prompt_recipe=json.dumps({"v": 3, "kind": "character", "panels": [
                                  {"key": k, "file": panels_rec[k]} for k in ("front", "left", "back", "face_front")],
                                  "mirrors": {"right": panels_rec["right"]}, "board": board_rec})))
            s.add(BibleEntity(id="e-nue", kind="character", name="Sans planche"))
            s.add(BibleEntity(id="e-mos", kind="character", name="Le Tableau", ref_image=mosaique))
            s.add(BibleEntity(id="e-lieu", kind="place", name="La Crypte", prompt_recipe=json.dumps({"v": 3, "kind": "place",
                "panels": [{"key": k, "file": _panneau(f"lieu_{k}.png", (90, 90, 90), 400, 300)}
                           for k in ("wide", "angle", "detail")]})))
            await s.commit()

    async def compter():
        async with async_session_factory() as s:
            return ((await s.execute(select(func.count()).select_from(Depense))).scalar(),
                    (await s.execute(select(func.count()).select_from(JobRecord))).scalar())

    async def attendre(c, jid):
        for _ in range(200):
            j = (await c.get(f"/api/jobs/{jid}")).json()
            if j.get("status") in ("done", "failed"):
                return j
            await asyncio.sleep(0.02)
        return j

    async def main():
        await entites()
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            avant = await compter()
            for eid in ("e-nue", "e-mos", "e-lieu", "inconnue"):
                r = await c.post(f"/api/bible/entities/{eid}/model3d", json={"from_board": True})
                o[eid] = (r.status_code, r.text)
            o["moteur_x"] = (await c.post("/api/bible/entities/e-dec/model3d",
                                          json={"from_board": True, "engine": "x"})).status_code
            fk, settings.FAL_KEY = settings.FAL_KEY, " "
            o["fal"] = (await c.post("/api/bible/entities/e-dec/model3d", json={"from_board": True})).status_code
            settings.FAL_KEY = fk
            o["refus_muets"] = (await compter()) == avant

            _vider()
            dep0 = (await compter())[0]
            r = await c.post("/api/bible/entities/e-dec/model3d", json={"from_board": True})
            o["dec"] = (r.status_code, r.json())
            o["dec_job"] = await attendre(c, r.json()["job_id"])
            o["dec_vues"] = (await c.get(f"/api/assets/3d/{r.json()['job']}/views")).json()
            r = await c.post("/api/bible/entities/e-rec/model3d", json={"from_board": True, "engine": "tripo"})
            o["rec"] = (r.status_code, r.json())
            await attendre(c, r.json()["job_id"])
            o["rec_vues"] = (await c.get(f"/api/assets/3d/{r.json()['job']}/views")).json()
            o["edits"] = list(EDITS)
            o["dep_vues"] = (await compter())[0] - dep0

            job = o["dec"][1]["job"]
            o["rej"] = (await c.post(f"/api/assets/3d/{job}/views/1/rejouer", json={})).status_code
            r = await c.post(f"/api/assets/3d/{job}/tirer")
            o["tir"] = (r.status_code, await attendre(c, r.json()["job_id"]))
            async with async_session_factory() as s:
                e = await s.get(BibleEntity, "e-dec")
                o["entite"] = (e.model3d_job, e.model3d_file)
                o["autre"] = (await s.get(BibleEntity, "e-rec")).model3d_job
            o["fiche"] = (await c.get("/api/bible/entities")).json()
        return o

    o = asyncio.run(main())
    assert o["e-nue"][0] == 400 and "planche" in o["e-nue"][1], o["e-nue"]
    assert o["e-mos"][0] == 400 and "mosaïque" in o["e-mos"][1].lower(), o["e-mos"]
    assert o["e-lieu"][0] == 400 and "face" in o["e-lieu"][1], o["e-lieu"]
    assert o["inconnue"][0] == 404, o["inconnue"]
    assert o["moteur_x"] == 400 and o["fal"] == 503, (o["moteur_x"], o["fal"])
    assert o["refus_muets"], "un refus n'inscrit ni dépense ni job"
    st, d = o["dec"]
    assert st == 200 and d["source"] == "decoupe" and d["vues"] == ["front", "back", "left", "right"] \
        and d["engine"] == "tripo-h3.1", o["dec"]
    assert o["dec_job"]["status"] == "done", o["dec_job"]
    vj = o["dec_vues"]
    assert vj["entity_id"] == "e-dec" and vj["source"] == "decoupe" and vj["etat"] == "en_attente", vj
    couleurs = {v["cle"]: _dominante(v["origine"]) for v in vj["vues"]}
    assert all(couleurs[k] == COULEURS[k] for k in COULEURS), couleurs          # la découpe rend LES BONS panneaux
    st, d = o["rec"]
    assert st == 200 and d["source"] == "recette", o["rec"]
    assert {v["cle"]: v["origine"] for v in o["rec_vues"]["vues"]} == {k: panels_rec[k] for k in COULEURS}, o["rec_vues"]
    assert o["edits"] == [] and o["dep_vues"] == 0, (o["edits"], o["dep_vues"])   # ni génération, ni dépense
    assert o["rej"] == 400, o["rej"]
    assert o["tir"][0] == 200 and o["tir"][1]["status"] == "done", o["tir"]
    assert o["entite"] == (job_attendu := o["dec"][1]["job"], "model.glb"), (o["entite"], job_attendu)
    assert o["autre"] is None, "le tir d'un jeu ne touche que SON entité"
    fiche = next(x for x in o["fiche"]["entities"] if x["id"] == "e-dec")
    assert fiche["model3d_job"] == o["dec"][1]["job"], fiche


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_bible_vues)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
