# -*- coding: utf-8 -*-
"""T105 C (plan-moteurs-3d T5, R10e P4) — conversion de formats. Le banc relit les fichiers ÉCRITS : OBJ reparsé
(compteurs v/vt/vn/f, usemtl, normales UNITAIRES), MTL, STL relu par print3d, 3MF ouvert comme un zip, glTF relu,
GLB relu. Import OBJ/STL/glTF/GLB → un JOB neuf (fiche, rapport) que l'Établi voit. FBX/USDZ/BLEND par Meshy convert
(docs relues le 06/10 : 1 crédit par TÂCHE, `model_urls`) en MESHY_MOCK, upload fal stubbé ; la route payante passe
par la garde des plafonds et rattache le coût réel.
Run : python tests/test_mesh_convert.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzconv_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["MESHY_MOCK"] = "1"; os.environ["MESHY_MOCK_SPEED"] = "0.005"
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
from app.services import gltf_builder, mesh_convert, mesh_edit, print3d  # noqa: E402
from app.services.storage import init_db                          # noqa: E402

UPLOADS = []


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/{pathlib.Path(p).name}"


A3._upload = _faux_upload
_BASE = []


def _pret():
    if not _BASE:
        asyncio.run(init_db()); _BASE.append(1)


def _png(couleur=(200, 90, 40), taille=32) -> bytes:
    b = io.BytesIO(); Image.new("RGB", (taille, taille), couleur).save(b, "PNG")
    return b.getvalue()


def _job(nom: str, texture: bool = True) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    maps = {"basecolor": _png()} if texture else {}
    (d / "model.glb").write_bytes(gltf_builder.build_glb(maps, None, "cube", "peau"))
    return d


def _lignes(obj, prefixe):
    return [l for l in obj.splitlines() if l.startswith(prefixe)]


def test_les_capacites_disent_ce_qui_est_local_et_ce_qui_coute():
    c = mesh_convert.capacites()
    assert c["local_export"] == ["obj", "stl", "3mf", "gltf"], c
    assert c["local_import"] == ["obj", "stl", "glb", "gltf"], c
    assert c["meshy"] == ["fbx", "usdz", "blend"] and c["credits_meshy"] == 1, c
    assert "FBX" in c["pourquoi_pas_local"] and "Blender" in c["pourquoi_pas_local"], c


def test_l_obj_sort_avec_son_mtl_ses_uv_ses_normales_et_sa_texture():
    _job("cv_obj")
    nom, octets = mesh_convert.exporter("cv_obj", "obj")
    assert nom == "cv_obj_obj.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert "cv_obj.obj" in noms and "cv_obj.mtl" in noms, noms
        pngs = [n for n in noms if n.endswith(".png")]
        assert pngs, noms
        obj = z.read("cv_obj.obj").decode("utf-8")
        assert obj.startswith("# Deepotus") and "mtllib cv_obj.mtl" in obj, obj[:300]
        assert obj.count("\nusemtl ") == 1, obj
        v, vt, vn, f = (len(_lignes(obj, p)) for p in ("v ", "vt ", "vn ", "f "))
        assert v == 24 and vt == 24 and vn == 24 and f == 12, (v, vt, vn, f)
        assert all(len(l.split()) == 4 and l.split()[1].count("/") == 2 for l in _lignes(obj, "f ")), _lignes(obj, "f ")[:3]
        for l in _lignes(obj, "vn "):
            x, y, zz = (float(t) for t in l.split()[1:])
            assert abs((x * x + y * y + zz * zz) ** 0.5 - 1.0) < 1e-4, l          # normales unitaires
        doc, binc = mesh_edit.lire_glb((settings.outputs_path / "assets3d" / "cv_obj" / "model.glb").read_bytes())
        att = doc["meshes"][0]["primitives"][0]["attributes"]
        uv = [tuple(round(c, 5) for c in t) for t in mesh_edit.lire_accesseur(doc, binc, att["TEXCOORD_0"])]
        vt = [tuple(round(float(c), 5) for c in l.split()[1:]) for l in _lignes(obj, "vt ")]
        assert vt == [(u, round(1.0 - v, 5)) for u, v in uv], (vt[:3], uv[:3])          # v glTF compté du HAUT
        mtl = z.read("cv_obj.mtl").decode("utf-8")
        tex = [l.split(" ", 1)[1] for l in mtl.splitlines() if l.startswith("map_Kd ")]
        assert "newmtl peau" in mtl and tex and tex[0] in noms, (mtl, noms)          # la texture citée EXISTE


def test_l_obj_garde_la_translation_des_noeuds_mais_pas_sur_les_normales():
    d = _job("cv_trs", texture=False)
    doc, binc = mesh_edit.lire_glb((d / "model.glb").read_bytes())
    for q in doc["nodes"]:
        if "mesh" in q:
            q["translation"] = [10.0, 0.0, 0.0]
            q["scale"] = [3.0, 1.0, 0.5]                                   # non uniforme : les normales en souffrent
            jumeau = dict(q, translation=[20.0, 0.0, 0.0], name="jumeau")
    doc["nodes"].append(jumeau)
    doc["scenes"][doc.get("scene", 0)]["nodes"].append(len(doc["nodes"]) - 1)
    (d / "model.glb").write_bytes(mesh_edit.ecrire_glb(doc, binc))
    _, octets = mesh_convert.exporter("cv_trs", "obj")
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        obj = z.read("cv_trs.obj").decode("utf-8")
        assert "map_Kd" not in z.read("cv_trs.mtl").decode("utf-8")              # maillage nu : pas de texture
    xs = [float(l.split()[1]) for l in _lignes(obj, "v ")]
    assert min(xs) > 6.0 and max(xs) > 20.0, (min(xs), max(xs))                  # coordonnées MONDE, deux nœuds
    v, f = len(_lignes(obj, "v ")), _lignes(obj, "f ")
    indices = [int(c.split("/")[0]) for l in f for c in l.split()[1:]]
    assert v == 48 and len(f) == 24 and max(indices) == 48 and min(indices) == 1, (v, len(f), max(indices))
    assert min(int(c.split("/")[0]) for l in f[12:] for c in l.split()[1:]) == 25, "le 2e bloc vise SES sommets"
    for l in _lignes(obj, "vn "):
        x, y, zz = (float(t) for t in l.split()[1:])
        assert abs((x * x + y * y + zz * zz) ** 0.5 - 1.0) < 1e-4, l              # la translation n'y entre pas


def test_le_stl_et_le_3mf_passent_par_print3d_et_se_relisent():
    _job("cv_stl", texture=False)
    nom, stl = mesh_convert.exporter("cv_stl", "stl")
    assert nom == "cv_stl.stl" and len(print3d.lire_stl(stl)) == 12
    nom3, mf3 = mesh_convert.exporter("cv_stl", "3mf")
    with zipfile.ZipFile(io.BytesIO(mf3)) as z:
        assert nom3 == "cv_stl.3mf" and "3D/3dmodel.model" in z.namelist(), sorted(z.namelist())
    for mauvais in (0, 1e6, "grand"):
        try:
            mesh_convert.exporter("cv_stl", "stl", cible_mm=mauvais)
            raise AssertionError(f"cible_mm={mauvais} accepté")
        except ValueError as e:
            assert "cible_mm" in str(e), e
    _, stl_mm = mesh_convert.exporter("cv_stl", "stl", cible_mm=100.0)
    bb = print3d.bbox(print3d.lire_stl(stl_mm))
    assert abs(max(b[1] - b[0] for b in bb) - 100.0) < 1e-3, bb


def test_le_gltf_sort_autonome_et_se_relit():
    _job("cv_gltf")
    nom, octets = mesh_convert.exporter("cv_gltf", "gltf")
    assert nom == "cv_gltf.gltf", nom
    doc = json.loads(octets)
    assert str(doc["buffers"][0].get("uri") or "").startswith("data:"), "tampon embarqué : un seul fichier"
    assert doc["meshes"] and doc["images"], sorted(doc)


def test_un_format_inconnu_ou_proprietaire_refuse_en_disant_la_voie():
    _job("cv_ref")
    for fmt in ("fbx", "usdz", "blend"):
        try:
            mesh_convert.exporter("cv_ref", fmt)
            raise AssertionError(f"{fmt} aurait dû refuser")
        except ValueError as e:
            assert "Meshy" in str(e) and "1 crédit" in str(e), (fmt, e)
    try:
        mesh_convert.exporter("cv_ref", "dae")
        raise AssertionError("dae aurait dû refuser")
    except ValueError as e:
        assert "dae" in str(e), e


def test_l_import_stl_obj_gltf_redevient_un_glb_relisible():
    d = _job("cv_in", texture=False)
    stl = print3d.ecrire_stl(print3d.lire_glb_triangles((d / "model.glb").read_bytes()))
    assert len(print3d.lire_glb_triangles(mesh_convert.importer(stl, "objet.stl"))) == 12
    _, zobj = mesh_convert.exporter("cv_in", "obj")
    with zipfile.ZipFile(io.BytesIO(zobj)) as z:
        obj = z.read("cv_in.obj")
    assert len(print3d.lire_glb_triangles(mesh_convert.importer(obj, "objet.obj"))) == 12, "OBJ -> GLB par gltfpack"
    _, gltf = mesh_convert.exporter("cv_in", "gltf")
    assert len(print3d.lire_glb_triangles(mesh_convert.importer(gltf, "objet.gltf"))) == 12
    for mauvais, ext in ((b"xx", "objet.fbx"), (b"pas un stl", "objet.stl"), (b"", "objet.glb")):
        try:
            mesh_convert.importer(mauvais, ext)
            raise AssertionError(f"{ext} aurait dû refuser")
        except ValueError as e:
            assert ext.split(".")[1] in str(e).lower() or "vide" in str(e).lower() or "stl" in str(e).lower(), (ext, e)


def test_l_import_cree_un_job_que_l_etabli_voit():
    from app.services import mesh_report, mesh_sources
    d = _job("cv_src", texture=False)
    stl = print3d.ecrire_stl(print3d.lire_glb_triangles((d / "model.glb").read_bytes()))
    job = mesh_convert.importer_job(stl, "Ma Pièce!.stl")
    assert job.startswith("import_ma_piece_"), job
    jd = settings.outputs_path / "assets3d" / job
    fiche = json.loads((jd / "asset.json").read_text("utf-8"))
    assert (jd / "model.glb").is_file() and fiche["engine"] == "import" and fiche["created_at"], fiche   # daté : rangé
    assert mesh_report.read_registry(job)["current"] == "model.glb"
    assert job in {l["id"] for l in mesh_sources.lister()}
    job2 = mesh_convert.importer_job(stl, "Ma Pièce!.stl")
    assert job2 != job, "deux imports du même nom : deux jobs, jamais un écrasement"


def test_la_conversion_meshy_devis_puis_tache_et_rapatriement():
    _pret()
    d = _job("cv_meshy")
    devis = mesh_convert.devis_meshy(["usdz", "fbx", "fbx"])
    assert devis["formats"] == ["fbx", "usdz"] and devis["credits"] == {"meshy": 1.0}, devis
    for mauvais in ([], ["obj"], ["dae"]):
        try:
            mesh_convert.devis_meshy(mauvais)
            raise AssertionError(f"{mauvais} accepté")
        except ValueError:
            pass
    UPLOADS.clear()
    r = asyncio.run(mesh_convert.convertir_par_meshy("cv_meshy", ["fbx", "usdz"]))
    assert r["task_id"] and sorted(r["files"]) == ["model.fbx", "model.usdz"] and r["manquants"] == [], r
    for f in r["files"]:
        assert (d / "convert" / f).is_file(), (f, r)
    assert UPLOADS == ["model.glb"], UPLOADS


def test_les_routes_convert():
    _pret()
    from app.api.routes import router
    chemins = [x.path for x in router.routes if hasattr(x, "path")]
    assert chemins.index("/assets/3d/{job}/convert") < chemins.index("/assets/3d/{job}/{fmt}")
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services import plafonds as PL
    from app.services.storage import Depense, async_session_factory
    from sqlalchemy import select
    _job("cv_route")
    d0 = settings.outputs_path / "assets3d" / "cv_route"
    stl = print3d.ecrire_stl(print3d.lire_glb_triangles((d0 / "model.glb").read_bytes()))

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            o["caps"] = (await c.get("/api/assets/3d/cv_route/convert")).json()["meshy"]
            s = await c.post("/api/assets/3d/cv_route/convert", json={"format": "stl", "cible_mm": 50})
            o["stl"] = (s.status_code, s.headers.get("content-type"), s.headers.get("content-disposition"), len(s.content))
            o["obj"] = (await c.post("/api/assets/3d/cv_route/convert", json={"format": "obj"})).headers.get("content-type")
            o["dae"] = (await c.post("/api/assets/3d/cv_route/convert", json={"format": "dae"})).status_code
            o["absent"] = (await c.post("/api/assets/3d/absent/convert", json={"format": "stl"})).status_code
            o["mm"] = (await c.post("/api/assets/3d/cv_route/convert", json={"format": "stl", "cible_mm": "grand"})).status_code
            fk, settings.FAL_KEY = settings.FAL_KEY, ""
            o["sans_fal"] = (await c.post("/api/assets/3d/cv_route/convert", json={"format": "fbx"})).status_code
            settings.FAL_KEY = fk
            PL.enregistrer({"par_moteur": {"meshy": 0.001}})
            o["402"] = (await c.post("/api/assets/3d/cv_route/convert", json={"format": "fbx"})).status_code
            PL.enregistrer({"par_moteur": {"meshy": 0}})
            m = await c.post("/api/assets/3d/cv_route/convert", json={"formats": ["fbx", "blend"]})
            o["meshy"] = (m.status_code, m.json())
            jid = m.json().get("job_id")
            for _ in range(300):
                j = (await c.get(f"/api/jobs/{jid}")).json()
                if j.get("status") in ("done", "failed"):
                    break
                await asyncio.sleep(0.05)
            o["job"] = j
            f = await c.get("/api/assets/3d/cv_route/convert/model.fbx")
            o["fbx"] = (f.status_code, len(f.content))
            tv = await c.get("/api/assets/3d/cv_route/convert/asset.json")
            o["fbx_trav"] = (tv.status_code, b'"engine"' in tv.content)
            imp = await c.post("/api/assets/3d/importer", files={"file": ("statue.stl", stl, "application/sla")})
            o["import"] = (imp.status_code, imp.json())
            o["import_fbx"] = (await c.post("/api/assets/3d/importer", files={"file": ("x.fbx", b"zz", "application/octet-stream")})).status_code
            async with async_session_factory() as s_:
                o["dep"] = [(x.op, x.ref, x.reel_unites) for x in (await s_.execute(select(Depense))).scalars().all()]
        return o
    o = asyncio.run(main())
    assert o["caps"] == ["fbx", "usdz", "blend"], o["caps"]
    assert o["stl"][0] == 200 and o["stl"][1] == "model/stl" and 'filename="cv_route.stl"' in o["stl"][2], o["stl"]
    assert o["obj"] == "application/zip", o["obj"]
    assert o["dae"] == 400 and o["absent"] == 404 and o["mm"] == 400, o
    assert o["sans_fal"] == 400 and o["402"] == 402, (o["sans_fal"], o["402"])
    st, js = o["meshy"]
    assert st == 200 and js["status"] == "queued" and js["devis"]["credits"] == {"meshy": 1.0}, o["meshy"]
    assert o["job"]["status"] == "done", o["job"]
    assert o["fbx"][0] == 200 and o["fbx"][1] > 0, o["fbx"]
    assert o["fbx_trav"] == (404, False), o["fbx_trav"]                    # seuls les fichiers du dossier convert/
    st, ij = o["import"]
    assert st == 200 and ij["job"].startswith("import_statue_") and ij["triangles"] == 12, o["import"]
    assert o["import_fbx"] == 400, o["import_fbx"]
    dep = [x for x in o["dep"] if x[0] == "asset3d_convert"]
    assert len(dep) == 1 and dep[0][1] and dep[0][1].startswith("meshy:") and dep[0][2] == 1.0, o["dep"]   # 2 formats, 1 cr


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_convert)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
