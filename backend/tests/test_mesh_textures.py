# -*- coding: utf-8 -*-
"""T105 (plan-moteurs-3d T4, R10e P3) — textures d'un modèle exportées aux conventions moteur (R10c). Le banc relit
l'ARCHIVE écrite : noms de fichiers, tailles en pixels, modes, bordereau, textures.json. Puis les routes, par de vrais
appels HTTP. Écart au plan : `clean_res` ne descend pas sous 512 px (liste blanche du Forge) — le banc le fige.
Run : python tests/test_mesh_textures.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dztex_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                        # noqa: E402
logger.remove()
from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import gltf_builder, material_store, mesh_textures  # noqa: E402


def _png(couleur, taille=64) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (taille, taille), couleur).save(b, "PNG")
    return b.getvalue()


def _job(nom: str, maps: dict) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb(maps, None, "cube", "peau"))
    return d


def test_l_inventaire_dit_quels_canaux_le_glb_porte_vraiment():
    _job("tex_inv", {"basecolor": _png((180, 90, 40)), "normal": _png((128, 128, 255))})
    inv = mesh_textures.inventaire("tex_inv")
    assert inv["materiaux"], inv
    m = inv["materiaux"][0]
    assert set(m["canaux"]) >= {"basecolor", "normal"}, m
    assert m["canaux"]["basecolor"]["px"] == [64, 64], m
    assert m["canaux"]["basecolor"]["bytes"] > 0, m
    assert "orm" in inv["manquants"] and "emissive" in inv["manquants"], inv
    assert "basecolor" not in inv["manquants"] and "normal" not in inv["manquants"], inv
    assert inv["file"] == "model.glb" and "blender" in inv["conventions"] and inv["resolutions"][0] == 512, inv


def test_un_glb_sans_texture_est_refuse_avant_l_archive():
    _job("tex_nu", {})
    try:
        mesh_textures.exporter("tex_nu")
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "aucune texture" in str(e).lower(), e


def test_un_glb_compresse_refuse_en_le_disant():
    from app.services import mesh_edit
    d = _job("tex_draco", {"basecolor": _png((1, 2, 3))})
    doc, binc = mesh_edit.lire_glb((d / "model.glb").read_bytes())
    doc["extensionsUsed"] = doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    (d / "model.glb").write_bytes(mesh_edit.ecrire_glb(doc, binc))
    try:
        mesh_textures.inventaire("tex_draco")
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "KHR_draco_mesh_compression" in str(e), e


def test_l_archive_unity_urp_porte_les_noms_et_le_maskmap():
    _job("tex_urp", {"basecolor": _png((180, 90, 40)), "normal": _png((128, 128, 255))})
    nom, octets = mesh_textures.exporter("tex_urp", naming="unity_urp", resolution=512)
    assert nom == "tex_urp_unity_urp.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert "peau/peau_BaseMap.png" in noms and "peau/peau_Normal.png" in noms, noms
        assert "peau/peau_MetallicOcclusion.png" in noms, noms
        assert "BORDEREAU.txt" in noms and "textures.json" in noms, noms
        im = Image.open(io.BytesIO(z.read("peau/peau_BaseMap.png")))
        assert im.size == (512, 512), im.size
        mm = Image.open(io.BytesIO(z.read("peau/peau_MetallicOcclusion.png")))
        assert mm.mode == "RGBA", mm.mode
        nm = Image.open(io.BytesIO(z.read("peau/peau_Normal.png")))
        assert nm.mode in ("I;16", "I;16B", "I", "RGB"), nm.mode
        bord = z.read("BORDEREAU.txt").decode("utf-8")
        assert "Metallic Map ET Occlusion Map" in bord, bord[:400]
        meta = json.loads(z.read("textures.json").decode("utf-8"))
        assert meta["naming"] == "unity_urp" and meta["resolution"] == 512, meta


def test_les_noms_suivent_la_convention_demandee():
    _job("tex_conv", {"basecolor": _png((10, 200, 90))})
    attendus = {"standard": "peau/peau_basecolor.png", "unreal": "peau/T_peau_BC.png",
                "godot": "peau/peau_albedo.png", "unity_hdrp": "peau/peau_BaseMap.png",
                "blender": "peau/peau_base_color.png"}
    for naming, f in attendus.items():
        _, octets = mesh_textures.exporter("tex_conv", naming=naming, resolution=512)
        with zipfile.ZipFile(io.BytesIO(octets)) as z:
            assert f in z.namelist(), (naming, sorted(z.namelist()))


def test_la_convention_inconnue_retombe_sur_standard_comme_le_forge():
    _job("tex_alias", {"basecolor": _png((10, 200, 90))})
    nom, octets = mesh_textures.exporter("tex_alias", naming="n_importe_quoi", resolution=512)
    assert nom == "tex_alias.zip", nom          # standard : pas de suffixe
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        assert "peau/peau_basecolor.png" in z.namelist(), sorted(z.namelist())
    assert material_store.clean_naming("n_importe_quoi") == "standard"


def test_la_cuisson_locale_fabrique_ce_qui_manque_et_le_dit():
    _job("tex_cuit", {"basecolor": _png((120, 120, 120))})
    _, sans = mesh_textures.exporter("tex_cuit", naming="unreal", resolution=512, cuire=False)
    _, avec = mesh_textures.exporter("tex_cuit", naming="unreal", resolution=512, cuire=True)
    with zipfile.ZipFile(io.BytesIO(sans)) as z:
        assert "peau/T_peau_ORM.png" not in z.namelist(), sorted(z.namelist())
        assert json.loads(z.read("textures.json"))["materiaux"][0]["cuits"] == []
        assert "CUITES" not in z.read("BORDEREAU.txt").decode("utf-8")
    with zipfile.ZipFile(io.BytesIO(avec)) as z:
        assert "peau/T_peau_ORM.png" in z.namelist(), sorted(z.namelist())
        orm = Image.open(io.BytesIO(z.read("peau/T_peau_ORM.png")))
        assert orm.mode == "RGB" and orm.size == (512, 512), (orm.mode, orm.size)
        meta = json.loads(z.read("textures.json").decode("utf-8"))
        assert "orm" in meta["materiaux"][0]["cuits"], meta["materiaux"][0]
        bord = z.read("BORDEREAU.txt").decode("utf-8")
        assert "cartes de MOTIF" in bord and "pas un bake de maillage" in bord, bord[-600:]


def test_la_source_est_le_glb_courant_sauf_version_demandee():
    from app.services import mesh_report
    d = _job("tex_ver", {"basecolor": _png((1, 2, 3))})
    (d / "model.v2.glb").write_bytes(gltf_builder.build_glb({"basecolor": _png((9, 9, 9), 32)}, None, "cube", "peau"))
    mesh_report.write_report("tex_ver", "model.v2.glb", version=2, avec_silhouettes=False)
    assert mesh_textures.inventaire("tex_ver")["file"] == "model.v2.glb"
    assert mesh_textures.inventaire("tex_ver", version=1)["file"] == "model.glb"
    assert mesh_textures.inventaire("tex_ver")["materiaux"][0]["canaux"]["basecolor"]["px"] == [32, 32]
    try:
        mesh_textures.inventaire("tex_ver", version=7)
        raise AssertionError("version absente acceptée")
    except FileNotFoundError:
        pass


def test_les_routes_textures_sont_avant_le_catch_all_et_repondent():
    from app.api.routes import router
    chemins = [r.path for r in router.routes if hasattr(r, "path")]
    assert chemins.index("/assets/3d/{job}/textures") < chemins.index("/assets/3d/{job}/{fmt}")
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    _job("tex_route", {"basecolor": _png((180, 90, 40))})
    _job("tex_route_nu", {})
    from app.services import mesh_edit
    dd = _job("tex_route_draco", {"basecolor": _png((1, 2, 3))})
    doc, binc = mesh_edit.lire_glb((dd / "model.glb").read_bytes())
    doc["extensionsUsed"] = doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    (dd / "model.glb").write_bytes(mesh_edit.ecrire_glb(doc, binc))

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            g = await c.get("/api/assets/3d/tex_route/textures")
            o["inv"] = (g.status_code, g.json().get("file"))
            o["absent"] = (await c.get("/api/assets/3d/absent/textures")).status_code
            o["draco"] = (await c.get("/api/assets/3d/tex_route_draco/textures")).status_code
            o["nu"] = (await c.post("/api/assets/3d/tex_route_nu/textures", json={})).status_code
            o["res"] = (await c.post("/api/assets/3d/tex_route/textures", json={"resolution": "beaucoup"})).status_code
            p = await c.post("/api/assets/3d/tex_route/textures", json={"naming": "godot", "resolution": 512})
            o["zip"] = (p.status_code, p.headers.get("content-disposition"), p.content[:2])
        return o
    o = asyncio.run(main())
    assert o["inv"] == (200, "model.glb") and o["absent"] == 404 and o["nu"] == 400, o
    assert o["draco"] == 400, o["draco"]                          # un GLB compressé : refus parlant, pas une panne
    assert o["res"] == 200, o["res"]                               # clean_res : jamais d'erreur, 2048 par défaut
    assert o["zip"][0] == 200 and 'filename="tex_route_godot.zip"' in o["zip"][1] and o["zip"][2] == b"PK", o["zip"]


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_textures)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
