# -*- coding: utf-8 -*-
"""t391 (31/10/2026) — l'écran Importer : FBX par Blender (SIMULÉ : la couture `_executer` écrit le GLB attendu,
aucun Blender lancé), VRM comme un GLB, formats refusés, Blender absent → 503, et la route qui ouvre un job.
t405 : Daz Genesis 8 / 8.1 — FBX + dossier de textures posé à côté du FBX, bornes, manifeste `source: daz-g8`.
Run : python tests/test_studio3d_import.py (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3imp_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import studio3d_export as SE, studio3d_import as SI, studio3d_ouvert as SO   # noqa: E402
import _squelette_synthetique as SQ                               # noqa: E402

RIG = SQ.glb_cible()
appels = []
textures_vues = []
CARTES = [("Genesis 8 Female.images/G8FBaseHairScalp_1001_D.tif", b"II*\x00scalp"),
          ("Genesis 8 Female.images/sous/Cheveux_D.png", b"\x89PNG cheveux")]


def faux_executer(argv, delai):
    """Blender simulé : lit les paramètres JSON passés après « -- » et écrit la sortie attendue."""
    appels.append(argv)
    p = json.loads(argv[argv.index("--") + 1])
    assert pathlib.Path(p["source"]).read_bytes() == b"FBX-BINAIRE"
    pathlib.Path(p["sortie"]).write_bytes(RIG)
    if p.get("textures"):                       # t405 : Daz — les cartes sont À CÔTÉ du FBX, chemins relatifs gardés
        dossier = pathlib.Path(p["textures"])
        assert dossier == pathlib.Path(p["source"]).parent
        vues = sorted(f.relative_to(dossier).as_posix() for f in dossier.rglob("*") if f.is_file() and f.suffix != ".fbx")
        textures_vues.append(vues)
        pathlib.Path(p["rapport"]).write_text(json.dumps({
            "os": 172, "noms_os": sorted(SI.OS_GENESIS8) + ["lEyelidUpper"], "trouvees": [pathlib.Path(v).name for v in vues],
            "manquantes": ["G8FBaseEyelashes_1006_D.tif"]}), encoding="utf-8")
    return 0, "DZIMPORT fin"


SE._executer = faux_executer
SE._blender = lambda: {"dispo": True, "exe": "blender.exe", "version": "5.2.2"}


def test_un_fbx_passe_par_blender_et_devient_un_job_rigge():
    r = SI.importer(b"FBX-BINAIRE", "mixamo_marche.fbx")
    assert r["format"] == "fbx" and r["converti_par"] == "blender"
    argv = appels[-1]
    assert argv[1:4] == ["-b", "--factory-startup", "--python"]
    script = pathlib.Path(argv[4]).name
    assert script == "import.py"
    f = SO.fiche(r["job"])
    assert f["rig"]["rigge"] and f["rig"]["os"] > 10
    assert not any(p.name.startswith("_import_") for p in (settings.outputs_path / "assets3d").iterdir())   # ménage


def test_un_vrm_entre_tel_quel_et_les_refus():
    r = SI.importer(RIG, "avatar.vrm")
    assert r["converti_par"] == "vrm" and SO.fiche(r["job"])["rig"]["rigge"]
    for data, nom, motif in ((RIG, "x.blend", "non lu"), (b"", "x.glb", "vide"), (b"pas un glb", "x.vrm", "GLB binaire")):
        try:
            SI.importer(data, nom)
        except ValueError as e:
            assert motif in str(e), (motif, str(e))
        else:
            raise AssertionError(nom)


def test_blender_absent_refuse_en_503_par_la_route():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    vrai = SE._blender
    SE._blender = lambda: {"dispo": False}

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r503 = await c.post("/api/studio3d/importer", files={"file": ("a.fbx", b"FBX-BINAIRE")})
            SE._blender = vrai
            r400 = await c.post("/api/studio3d/importer", files={"file": ("a.blend", b"x")})
            rok = await c.post("/api/studio3d/importer", files={"file": ("perso.fbx", b"FBX-BINAIRE")})
            return r503, r400, rok
    r503, r400, rok = asyncio.run(go())
    assert r503.status_code == 503 and "Blender" in r503.json()["detail"]
    assert r400.status_code == 400
    assert rok.status_code == 200 and rok.json()["triangles"] > 0 and rok.json()["job"].startswith("import_perso")


def test_daz_g8_textures_a_cote_du_fbx_et_manifeste():
    r = SI.importer_daz(b"FBX-BINAIRE", "Genesis 8 Female.fbx", CARTES)
    assert r["source"] == "daz-g8" and r["converti_par"] == "blender" and r["os"] == 172 and r["genesis8"]
    assert textures_vues[-1] == ["Genesis 8 Female.images/G8FBaseHairScalp_1001_D.tif",
                                 "Genesis 8 Female.images/sous/Cheveux_D.png"]
    assert r["textures"] == {"envoyees": 2, "trouvees": ["G8FBaseHairScalp_1001_D.tif", "Cheveux_D.png"],
                             "manquantes": ["G8FBaseEyelashes_1006_D.tif"]}
    m = json.loads((settings.outputs_path / "assets3d" / r["job"] / "asset.json").read_text(encoding="utf-8"))
    assert m["source"] == "daz-g8" and m["os"] == 172 and m["engine"] == "import" and m["created_at"]
    assert m["textures_trouvees"] == r["textures"]["trouvees"] and m["textures_manquantes"] == ["G8FBaseEyelashes_1006_D.tif"]
    assert SO.fiche(r["job"])["rig"]["rigge"]
    # le script FIXE cherche les textures déplacées AVANT d'exporter le GLB
    sc = SI.SCRIPT_FBX_GLB
    assert "bpy.ops.file.find_missing_files(directory=a[\"textures\"]" in sc
    assert sc.index("find_missing_files") < sc.index("export_scene.gltf")
    assert not any(p.name.startswith("_import_") for p in (settings.outputs_path / "assets3d").iterdir())   # ménage


def test_daz_refus_et_bornes():
    for nom, data, textures, motif in (
            ("figure.obj", b"FBX-BINAIRE", [], ".fbx"),
            ("figure.fbx", b"", [], "vide"),
            ("figure.fbx", b"FBX-BINAIRE", [("../../evasion.tif", b"x")], "refusé"),
            ("figure.fbx", b"FBX-BINAIRE", [("C:/Windows/x.tif", b"x")], "refusé"),
            ("figure.fbx", b"FBX-BINAIRE", [("Genesis.images/scene.duf", b"x")], "pas une image")):
        try:
            SI.importer_daz(data, nom, textures)
        except ValueError as e:
            assert motif in str(e), (motif, str(e))
        else:
            raise AssertionError((nom, textures))
    n_max, t_max = SI.TEXTURES_NB_MAX, SI.TEXTURES_TOTAL_MAX
    try:
        SI.TEXTURES_NB_MAX = 1
        try:
            SI.importer_daz(b"FBX-BINAIRE", "f.fbx", CARTES)
        except ValueError as e:
            assert "au plus" in str(e)
        else:
            raise AssertionError("nombre")
        SI.TEXTURES_NB_MAX, SI.TEXTURES_TOTAL_MAX = n_max, 10
        try:
            SI.importer_daz(b"FBX-BINAIRE", "f.fbx", CARTES)
        except ValueError as e:
            assert "en tout" in str(e)
        else:
            raise AssertionError("total")
    finally:
        SI.TEXTURES_NB_MAX, SI.TEXTURES_TOTAL_MAX = n_max, t_max
    # un FBX simple ne reçoit ni dossier de textures ni find_missing_files
    SI.importer(b"FBX-BINAIRE", "simple.fbx")
    assert "textures" not in json.loads(appels[-1][appels[-1].index("--") + 1])


def test_route_daz_multipart():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            fichiers = [("file", ("Genesis 8 Male.fbx", b"FBX-BINAIRE"))] + [("textures", (n, o)) for n, o in CARTES]
            ok = await c.post("/api/studio3d/importer", files=fichiers, data={"type": "daz"})
            sans_type = await c.post("/api/studio3d/importer", files=fichiers)
            return ok, sans_type
    ok, sans_type = asyncio.run(go())
    assert ok.status_code == 200, ok.text
    j = ok.json()
    assert j["source"] == "daz-g8" and j["os"] == 172 and j["triangles"] > 0 and j["job"].startswith("import_genesis")
    assert textures_vues[-1][0] == "Genesis 8 Female.images/G8FBaseHairScalp_1001_D.tif"
    assert sans_type.status_code == 400 and "type=daz" in sans_type.json()["detail"]


def lancer_tous():
    rouges = []
    for nom, fn in list(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (Importer FBX / VRM / Daz)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
