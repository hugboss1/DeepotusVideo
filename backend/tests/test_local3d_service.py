# -*- coding: utf-8 -*-
"""T107 (plan-moteurs-3d T10, D4) — service GPU local optionnel (patron Voicebox), BRANCHÉ SANS ÊTRE INSTALLÉ (décision
de l'utilisateur, 06/10). Rien ne sort : la détection, la lecture de carte et l'appel HTTP sont stubbés. Le banc
vérifie la TABLE de décision par la VRAM, le repli parlant, la forme du résultat (un data: URI relu par le VRAI
téléchargeur), et les trous que le plan laissait : sans clé fal et sans envoi au stockage fal, le moteur local doit
marcher ; un service absent refuse AVANT tout job ; un moteur local se liste grisé tant que le service dort.
Run : python tests/test_local3d_service.py (depuis backend/)"""
import asyncio, base64, io, json, os, pathlib, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzlocal3d_")
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
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import gltf_builder, local3d_service as L      # noqa: E402

UPLOADS, ENVOIS = [], []
_ETAT = {"joignable": False}


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/{pathlib.Path(p).name}"


async def _faux_post(url, charge, timeout):
    ENVOIS.append((url, charge))
    return gltf_builder.build_glb({}, None, "cube", "local")


A3._upload = _faux_upload
L.joignable = lambda timeout=2.0, ttl=5.0: _ETAT["joignable"]
L._poster_generate = _faux_post
# la carte de la machine qui lance le banc ne décide RIEN : on remplit le cache (11 Go, la carte mesurée le 06/10)
L._carte_cache.update(t=time.monotonic() + 10 ** 6, v={"nom": "banc", "vram_mo": 11264, "source": "banc",
                                                     "avertissement": None})
_BASE = []


def _pret():
    if not _BASE:
        from app.services.storage import init_db
        asyncio.run(init_db()); _BASE.append(1)


def _source(nom="src.png"):
    b = io.BytesIO(); Image.new("RGB", (32, 32), (200, 90, 40)).save(b, "PNG")
    (settings.images_path / nom).write_bytes(b.getvalue())
    return nom


def test_la_table_de_decision_suit_la_vram_pas_le_millesime():
    assert L.decision(30000)["moteur"] == "hunyuan-2.1" and L.decision(30000)["texture"] is True
    assert L.decision(22000)["texture"] is True
    d = L.decision(11264)                                     # la RTX 2080 Ti de l'utilisateur, relue le 06/10
    assert d["moteur"] == "hunyuan-2.1" and d["texture"] is False and "10" in d["pourquoi"], d
    assert L.decision(8000)["moteur"] == "hunyuan-optimise" and L.decision(8000)["verifie"] is False
    assert L.decision(2000)["moteur"] == "fal" and L.decision(None)["moteur"] == "fal"


def test_la_carte_prefere_nvidia_smi_et_avertit_sur_le_plafond_win32():
    sauve = dict(L._carte_cache), L._lire_nvidia_smi, L._lire_win32
    try:
        L._carte_cache["t"] = 0.0
        L._lire_nvidia_smi = lambda timeout=4.0: ("NVIDIA GeForce RTX 2080 Ti", 11264)
        c = L.carte()
        assert c["vram_mo"] == 11264 and c["source"] == "nvidia-smi" and c["avertissement"] is None, c
        L._carte_cache["t"] = 0.0
        L._lire_nvidia_smi = lambda timeout=4.0: None
        L._lire_win32 = lambda timeout=6.0: ("NVIDIA GeForce RTX 2080 Ti", 4293918720 // (1 << 20))
        c = L.carte()
        assert c["source"] == "win32" and "uint32" in c["avertissement"] and "4 Gio" in c["avertissement"], c
        L._carte_cache["t"] = 0.0
        L._lire_win32 = lambda timeout=6.0: None
        c = L.carte()
        assert c["vram_mo"] is None and c["source"] is None, c
    finally:
        L._carte_cache.clear(); L._carte_cache.update(sauve[0])
        L._lire_nvidia_smi, L._lire_win32 = sauve[1], sauve[2]


def test_le_moteur_local_est_au_registre_gratuit_et_coherent():
    from app.services.pricing import estimate
    e = A3.ENGINES["hunyuan-local"]
    assert e["local"] is True and e["formats"] == ["glb"] and e["multiview"] is False and e["max_images"] == 1, e
    assert estimate({"kind": "asset3d", "engine": "hunyuan-local", "textures": True})["total_usd"] == 0.0
    args = A3.build_engine_args("hunyuan-local", ["u0", "u1"], {"textures": True, "face_limit": 20000, "seed": 7})
    assert args == {"image_url": "u0", "texture": True, "face_limit": 20000, "seed": 7}, args


def test_l_url_du_service_est_un_reglage():
    assert "LOCAL3D_URL" in type(settings).model_fields, "réglage absent : l'env et le .env seraient ignorés"
    sauve = settings.LOCAL3D_URL
    try:
        settings.LOCAL3D_URL = ""
        assert L.url() == "http://127.0.0.1:8081"
        settings.LOCAL3D_URL = "http://192.168.1.50:9000/"
        assert L.url() == "http://192.168.1.50:9000"
    finally:
        settings.LOCAL3D_URL = sauve


def test_sans_serveur_le_moteur_local_refuse_en_disant_quoi_faire():
    _ETAT["joignable"] = False
    try:
        asyncio.run(L.run_engine("hunyuan-local", {"image_url": "data:image/png;base64,AAAA"}))
        raise AssertionError("aurait dû refuser")
    except RuntimeError as e:
        assert "8081" in str(e) and "Hunyuan" in str(e) and "LOCAL3D_URL" in str(e), e


def test_avec_serveur_le_glb_revient_en_data_uri_et_le_vrai_telechargeur_le_relit():
    _ETAT["joignable"] = True
    ENVOIS.clear()
    png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 8).decode()
    r = asyncio.run(L.run_engine("hunyuan-local", {"image_url": f"data:image/png;base64,{png}", "texture": True,
                                                   "face_limit": 20000, "seed": 7}))
    assert r["mesh_url"].startswith("data:model/gltf-binary;base64,"), r["mesh_url"][:60]
    url, charge = ENVOIS[0]
    assert url.endswith("/generate") and charge["face_count"] == 20000 and charge["seed"] == 7, ENVOIS
    assert charge["texture"] is False, "11 Go : la texture demande 21 Go — jamais demandée au service"
    dest = pathlib.Path(_tmp, "relu.glb")
    A3._download(r["mesh_url"], dest)                         # le VRAI téléchargeur (urllib) sait lire un data: URI
    assert dest.read_bytes()[:4] == b"glTF"


def test_la_generation_locale_ne_touche_pas_fal():
    """Sans clé fal, sans envoi au stockage fal : la source part en data: URI au service local."""
    _ETAT["joignable"] = True
    UPLOADS.clear(); ENVOIS.clear()
    fk, settings.FAL_KEY = settings.FAL_KEY, ""
    try:
        r = asyncio.run(A3.generate_asset3d({"image_filename": _source(), "engine": "hunyuan-local",
                                             "textures": True}, "loc_gen"))
    finally:
        settings.FAL_KEY = fk
    assert UPLOADS == [], f"rien n'est envoyé chez fal : {UPLOADS}"
    assert ENVOIS and base64.b64decode(ENVOIS[0][1]["image"])[:4] == b"\x89PNG", "la source part en octets"
    d = settings.outputs_path / "assets3d" / "loc_gen"
    assert (d / "model.glb").read_bytes()[:4] == b"glTF" and r["engine"] == "hunyuan-local", r
    assert A3.read_manifest("loc_gen")["texture_mode"] == "no", "forme seule : dit tel quel au manifeste"


def test_les_disponibilites_disent_toujours_l_etat_des_deux_voies():
    _ETAT["joignable"] = False
    d = L.disponible()
    assert {x["id"] for x in d} == {"fal", "local3d"}, d
    loc = next(x for x in d if x["id"] == "local3d")
    assert loc["ready"] is False and loc["decision"]["moteur"] == "hunyuan-2.1" and loc["url"], loc


def test_routes():
    _pret()
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy import func, select
    from app.main import app
    from app.services.storage import Depense, JobRecord, async_session_factory
    src = _source("route.png")

    async def compter():
        async with async_session_factory() as s:
            return ((await s.execute(select(func.count()).select_from(Depense))).scalar(),
                    (await s.execute(select(func.count()).select_from(JobRecord))).scalar())

    async def main():
        o = {}
        fk, settings.FAL_KEY = settings.FAL_KEY, ""
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                _ETAT["joignable"] = False
                o["engines_off"] = {m["id"]: m["available"] for m in (await c.get("/api/assets3d/engines")).json()["engines"]}
                o["local_off"] = (await c.get("/api/assets3d/local")).json()
                avant = await compter()
                r = await c.post("/api/assets/3d", json={"image_filename": src, "engine": "hunyuan-local"})
                o["absent"] = (r.status_code, r.text)
                o["absent_muet"] = (await compter()) == avant
                o["fal_sans_cle"] = (await c.post("/api/assets/3d", json={"image_filename": src, "engine": "tripo"})).status_code
                _ETAT["joignable"] = True
                o["engines_on"] = {m["id"]: m["available"] for m in (await c.get("/api/assets3d/engines")).json()["engines"]}
                o["multivues"] = (await c.post("/api/assets/3d", json={"image_filename": src, "engine": "hunyuan-local",
                                                                       "multiview": True, "views": 4})).status_code
                UPLOADS.clear()
                r = await c.post("/api/assets/3d", json={"image_filename": src, "engine": "hunyuan-local"})
                o["lance"] = (r.status_code, r.json())
                for _ in range(200):
                    j = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
                    if j.get("status") in ("done", "failed"):
                        break
                    await asyncio.sleep(0.02)
                o["job"] = j
                o["uploads"] = list(UPLOADS)
                o["dep"] = (await compter())[0] - avant[0]
        finally:
            settings.FAL_KEY = fk
        return o

    o = asyncio.run(main())
    assert o["engines_off"]["hunyuan-local"] is False and o["engines_off"]["tripo"] is False, o["engines_off"]
    assert o["engines_on"]["hunyuan-local"] is True and o["engines_on"]["tripo"] is False, o["engines_on"]
    lo = next(p for p in o["local_off"]["providers"] if p["id"] == "local3d")
    assert lo["ready"] is False and o["local_off"]["url"].endswith(":8081"), o["local_off"]
    assert o["absent"][0] == 503 and "8081" in o["absent"][1], o["absent"]
    assert o["absent_muet"], "un service absent refuse AVANT tout job et toute dépense"
    assert o["fal_sans_cle"] == 503, "un moteur fal sans clé reste refusé"
    assert o["multivues"] == 400, o["multivues"]
    assert o["lance"][0] == 200 and o["job"]["status"] == "done", (o["lance"], o["job"])
    assert o["uploads"] == [], o["uploads"]


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (local3d)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
