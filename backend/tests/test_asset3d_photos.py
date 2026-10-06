# -*- coding: utf-8 -*-
"""T107 (plan-moteurs-3d T11, D5) — des photos RÉELLES comme vues. Décision de l'utilisateur (06/10) : le téléphone
dépose par la synchro EXISTANTE (/sync/depot, source « mobile ») ; le PC bâtit le jeu de vues depuis la Bibliothèque —
aucune route nouvelle ouverte au réseau. fal stubbé, aucun réseau. Vérifié : la photo est REDRESSÉE selon son EXIF
(le téléphone tourne, pas nous) et bornée à 2048 px sans changer de rapport ; aucune génération ; une photo ne se
« rejoue » pas mais se détoure ; le détourage de toutes les vues est local et gratuit ; avec le moteur LOCAL rien ne
part au stockage fal, ni à la préparation ni au tir (les vues partent en data: URI) ; la route refuse avant tout job
(face exigée, image absente, moteur inconnu, clé fal pour un moteur fal) et n'écrit aucune dépense ; elle n'est PAS
dans les écritures ouvertes au réseau.
Run : python tests/test_asset3d_photos.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzphotos_")
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
from app.services import asset3d_views as V                      # noqa: E402

UPLOADS, EDITS, MOTEURS = [], [], []


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/{pathlib.Path(p).parent.name}/{pathlib.Path(p).name}"


async def _faux_seedream(url, prompt):
    EDITS.append(prompt)
    return "https://fal.test/jamais.png"


async def _faux_moteur(engine, args, endpoint=None):
    MOTEURS.append((engine, args))
    return {"mesh_url": "https://fal.test/m.glb", "format_urls": {}, "texture_urls": {}, "preview_url": None}


def _faux_download(url, dest, timeout=120):
    dest.write_bytes(gltf_builder.build_glb({}, None, "cube", "m"))
    return True


A3._upload, A3._seedream_edit, A3._run_engine, A3._download = _faux_upload, _faux_seedream, _faux_moteur, _faux_download
_BASE = []


def _pret():
    if not _BASE:
        from app.services.storage import init_db
        asyncio.run(init_db()); _BASE.append(1)


def _vider():
    UPLOADS.clear(); EDITS.clear(); MOTEURS.clear()


def _photo(nom, w=640, h=480, orientation=None, fmt="JPEG"):
    """Une photo de téléphone : sujet sombre sur fond clair ; `orientation` = la balise EXIF 0x0112."""
    im = Image.new("RGB", (w, h), (235, 232, 226))
    im.paste(Image.new("RGB", (w // 3, h // 2), (60, 40, 30)), (w // 3, h // 4))
    b = io.BytesIO()
    if orientation:
        ex = Image.Exif(); ex[0x0112] = orientation
        im.save(b, fmt, exif=ex)
    else:
        im.save(b, fmt)
    (settings.images_path / nom).write_bytes(b.getvalue())
    return nom


def _shot(job, i):
    return Image.open(settings.outputs_path / "assets3d" / job / f"shot_{i}.png")


def test_une_photo_tournee_par_le_telephone_est_redressee():
    _photo("tel_tourne.jpg", 640, 480, orientation=6)      # 6 = « tourner de 90° » : l'image vraie est en portrait
    asyncio.run(V.preparer_depuis_images("ph_rot", {"front": "tel_tourne.jpg"}, {"engine": "tripo"}, role="photo"))
    im = _shot("ph_rot", 0)
    assert im.size == (480, 640), im.size


def test_une_photo_trop_grande_est_ramenee_a_la_borne_sans_changer_de_rapport():
    _photo("tel_grande.jpg", 4000, 3000)
    asyncio.run(V.preparer_depuis_images("ph_big", {"front": "tel_grande.jpg"}, {"engine": "tripo"}, role="photo"))
    im = _shot("ph_big", 0)
    assert max(im.size) == V.PHOTO_MAX_PX and im.size == (2048, 1536), im.size
    assert (settings.images_path / "tel_grande.jpg").stat().st_size > 0, "l'original de la Bibliothèque reste intact"


def test_des_photos_ne_coutent_aucune_generation_et_gardent_leur_cle():
    _vider()
    noms = {k: _photo(f"tel_{k}.jpg") for k in ("left", "front", "back")}
    r = asyncio.run(V.preparer_depuis_images("ph_ok", noms, {"engine": "tripo-h3.1", "source": "photos"}, role="photo"))
    assert EDITS == [] and r["vues"] == 3, (EDITS, r)
    vj = V.lire_vues("ph_ok")
    assert [v["cle"] for v in vj["vues"]] == ["front", "back", "left"] and all(v["role"] == "photo" for v in vj["vues"])
    assert vj["source"] == "photos" and [v["origine"] for v in vj["vues"]] == [noms["front"], noms["back"], noms["left"]]
    assert UPLOADS == ["shot_0.png", "shot_1.png", "shot_2.png"], "c'est la vue BORNÉE qui part, pas l'original"


def test_une_photo_ne_se_rejoue_pas_mais_se_detoure_et_toutes_d_un_coup():
    noms = {k: _photo(f"tel_d{k}.jpg") for k in ("front", "back")}
    asyncio.run(V.preparer_depuis_images("ph_det", noms, {"engine": "tripo"}, role="photo"))
    try:
        asyncio.run(V.rejouer_vue("ph_det", 1)); raise AssertionError("rejouée")
    except ValueError as e:
        assert "photo" in str(e), e
    r = asyncio.run(V.detourer_toutes("ph_det"))
    assert r["detourees"] == 2 and r["usd"] == 0.0, r
    vj = V.lire_vues("ph_det")
    assert all(v["detoure"] == "local" and v["a_renvoyer"] for v in vj["vues"]), vj["vues"]
    assert _shot("ph_det", 0).mode == "RGBA"


def test_avec_le_moteur_local_rien_ne_part_chez_fal():
    _vider()
    noms = {k: _photo(f"tel_l{k}.jpg") for k in ("front", "back")}
    asyncio.run(V.preparer_depuis_images("ph_loc", noms, {"engine": "hunyuan-local"}, role="photo"))
    assert UPLOADS == [], f"préparation : {UPLOADS}"
    asyncio.run(V.detourer_vue("ph_loc", 0, via="local"))
    asyncio.run(V.tirer_vues("ph_loc"))
    assert UPLOADS == [], f"tir : {UPLOADS}"
    assert MOTEURS[0][0] == "hunyuan-local" and MOTEURS[0][1]["image_url"].startswith("data:image/png;base64,"), \
        str(MOTEURS)[:200]


def test_les_refus_du_service():
    _photo("tel_r.jpg")
    for vues, mot in (({}, "1 à 4"), ({"back": "tel_r.jpg"}, "face"), ({"front": "absente.jpg"}, "library")):
        try:
            asyncio.run(V.preparer_depuis_images("ph_ko", vues, {"engine": "tripo"}, role="photo"))
            raise AssertionError(f"accepté : {vues}")
        except ValueError as e:
            assert mot in str(e).lower(), (mot, e)


def test_la_comptabilite_nomme_des_photos_comme_des_photos():
    from types import SimpleNamespace
    from app.api.routes import _job_to_cost
    from app.services import pricing
    j = lambda meta: SimpleNamespace(provider="asset3d", duration_s=None, cost_meta=json.dumps(meta))
    ph = _job_to_cost(j({"kind": "asset3d_views", "views": 0, "source": "photos"}), pricing.load())
    pl = _job_to_cost(j({"kind": "asset3d_views", "views": 0, "source": "decoupe"}), pricing.load())
    assert ph["total_usd"] == 0.0 and "photo" in json.dumps(ph, ensure_ascii=False).lower(), ph
    assert "planche" in json.dumps(pl, ensure_ascii=False).lower(), pl


def test_route():
    _pret()
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy import func, select
    from app.main import app, _ECRITURES_OUVERTES
    from app.services.storage import Depense, JobRecord, async_session_factory
    noms = {k: _photo(f"tel_route_{k}.jpg", orientation=6) for k in ("front", "right")}

    async def compter():
        async with async_session_factory() as s:
            return ((await s.execute(select(func.count()).select_from(Depense))).scalar(),
                    (await s.execute(select(func.count()).select_from(JobRecord))).scalar())

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            avant = await compter()
            P = "/api/assets/3d/views/photos"
            o["sans_face"] = (await c.post(P, json={"vues": {"right": noms["right"]}})).status_code
            o["absente"] = (await c.post(P, json={"vues": {"front": "nulle.jpg"}})).status_code
            o["moteur"] = (await c.post(P, json={"vues": {"front": noms["front"]}, "engine": "x"})).status_code
            o["pas_dict"] = (await c.post(P, json={"vues": ["a.jpg"]})).status_code
            fk, settings.FAL_KEY = settings.FAL_KEY, ""
            o["fal"] = (await c.post(P, json={"vues": {"front": noms["front"]}, "engine": "tripo"})).status_code
            r = await c.post(P, json={"vues": {"front": noms["front"]}, "engine": "hunyuan-local"})
            o["local_sans_cle"] = r.status_code
            settings.FAL_KEY = fk
            o["refus_muets"] = (await compter())[1] == avant[1] + (1 if r.status_code == 200 else 0)
            _vider()
            r = await c.post(P, json={"vues": noms, "engine": "tripo", "detourer": True})
            o["lance"] = (r.status_code, r.json())
            for _ in range(200):
                j = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
                if j.get("status") in ("done", "failed"):
                    break
                await asyncio.sleep(0.02)
            o["job"] = j
            o["vues"] = (await c.get(f"/api/assets/3d/{r.json()['job']}/views")).json()
            o["dep"] = (await compter())[0] - avant[0]
        return o

    o = asyncio.run(main())
    assert o["sans_face"] == 400 and o["absente"] == 400 and o["moteur"] == 400 and o["pas_dict"] == 400, o
    assert o["fal"] == 400, "un moteur fal sans clé : refus avant tout job"
    assert o["local_sans_cle"] == 200, "le moteur local n'a pas besoin de la clé fal"
    assert o["refus_muets"], "un refus n'ouvre aucun job"
    st, l = o["lance"]
    assert st == 200 and l["status"] == "queued" and l["usd_estime"] == 0.0 and o["job"]["status"] == "done", o
    vj = o["vues"]
    assert vj["source"] == "photos" and [v["cle"] for v in vj["vues"]] == ["front", "right"], vj
    assert all(v["role"] == "photo" and v["detoure"] == "local" for v in vj["vues"]), vj["vues"]
    assert o["dep"] == 0, "aucune dépense pour des photos"
    assert "/api/assets/3d/views/photos" not in _ECRITURES_OUVERTES, "décision de l'utilisateur : rien d'ouvert au réseau"


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_photos)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
