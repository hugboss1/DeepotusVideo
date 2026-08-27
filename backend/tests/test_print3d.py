"""Impression 3D — le service print3d (plan 2026-08-27-impression-3d-slicer).

Phase 0 : lecteur GLB minimal PYTHON PUR (triangles monde, refus motivés
des compressions), écrivains STL binaire + 3MF (stdlib), échelle mm et
pose au sol, dossiers d'export + routes + ouverture slicer gardée.

Run: pytest tests/test_print3d.py -q
"""
import json as _json
import os
import pathlib
import struct
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── fabrique de GLB : le banc écrit ses fixtures à l'octet ───────────────────

def _glb(doc, bin_data=b""):
    j = _json.dumps(doc, separators=(",", ":")).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    chunks = struct.pack("<I", len(j)) + b"JSON" + j
    if bin_data:
        b = bin_data + b"\x00" * ((4 - len(bin_data) % 4) % 4)
        chunks += struct.pack("<I", len(b)) + b"BIN\x00" + b
    return b"glTF" + struct.pack("<II", 2, 12 + len(chunks)) + chunks


def _glb_cube_translate():
    """Cube 2×2×2 centré origine ; nœud parent translation x+10 ; l'enfant
    porte le maillage ET une MATRICE colonne-majeure z+5 — la composition
    parent×enfant est donc exercée, pas seulement lue."""
    pos = []
    for x in (-1, 1):
        for y in (-1, 1):
            for z in (-1, 1):
                pos += [x, y, z]
    idx = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1,
           2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3]
    vb = struct.pack("<24f", *pos)
    ib = struct.pack("<36H", *idx)
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [
            {"translation": [10, 0, 0], "children": [1]},
            {"matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 5, 1],
             "mesh": 0},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 8,
             "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 36,
             "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(vb)},
            {"buffer": 0, "byteOffset": len(vb), "byteLength": len(ib)},
        ],
        "buffers": [{"byteLength": len(vb) + len(ib)}],
    }
    return _glb(doc, vb + ib)


def _glb_ext_requise(nom):
    return _glb({"asset": {"version": "2.0"}, "extensionsRequired": [nom],
                 "scenes": [{"nodes": []}], "scene": 0})


# ── A. le lecteur GLB : triangles MONDE, refus motivés ───────────────────────

def test_le_lecteur_glb_sort_les_triangles_en_monde():
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_glb_cube_translate())
    assert len(tris) == 12
    xs = [v[0] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    assert min(xs) == pytest.approx(9.0) and max(xs) == pytest.approx(11.0)
    assert min(zs) == pytest.approx(4.0) and max(zs) == pytest.approx(6.0)


def test_le_lecteur_refuse_parlant_compressions_et_formes_hors_perimetre():
    from app.services import print3d as P3
    with pytest.raises(ValueError, match="meshopt"):
        P3.lire_glb_triangles(_glb_ext_requise("EXT_meshopt_compression"))
    with pytest.raises(ValueError, match="[Dd]raco"):
        P3.lire_glb_triangles(_glb_ext_requise("KHR_draco_mesh_compression"))
    with pytest.raises(ValueError, match="glTF"):
        P3.lire_glb_triangles(b"PAS-UN-GLB")
    # buffer externe (uri) : nos GLB sont monolithiques — refus parlant
    externe = _glb({"asset": {"version": "2.0"}, "scene": 0,
                    "scenes": [{"nodes": [0]}],
                    "nodes": [{"mesh": 0}],
                    "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                                "mode": 4}]}],
                    "accessors": [{"bufferView": 0, "componentType": 5126,
                                   "count": 3, "type": "VEC3"}],
                    "bufferViews": [{"buffer": 0, "byteOffset": 0,
                                     "byteLength": 36}],
                    "buffers": [{"uri": "ailleurs.bin", "byteLength": 36}]})
    with pytest.raises(ValueError, match="externe"):
        P3.lire_glb_triangles(externe)
    # primitives non triangulaires : hors périmètre, dit
    lignes = _glb_cube_translate().replace(b'"mode":4', b'"mode":1')
    with pytest.raises(ValueError, match="TRIANGLES"):
        P3.lire_glb_triangles(lignes)


# ── B. écrivains STL binaire + 3MF, échelle mm et pose au sol ────────────────

def _deux_triangles():
    # un quad z=0 en DEUX triangles qui PARTAGENT une arête : la
    # déduplication de sommets du 3MF se mesure (6 bruts → 4 uniques)
    return [((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            ((1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0))]


def test_l_ecrivain_stl_binaire_est_conforme_aux_octets():
    from app.services import print3d as P3
    data = P3.ecrire_stl(_deux_triangles())
    assert len(data) == 80 + 4 + 2 * 50
    assert struct.unpack("<I", data[80:84])[0] == 2
    # la normale du premier triangle (plan z=0, sens trigonométrique) = +Z
    nx, ny, nz = struct.unpack_from("<3f", data, 84)
    assert (nx, ny, nz) == pytest.approx((0.0, 0.0, 1.0))


def test_l_echelle_cible_la_plus_grande_dimension_et_pose_au_sol():
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_glb_cube_translate())   # cube 2×2×2
    monde = P3.mettre_a_l_echelle(tris, cible_mm=80.0)
    bb = P3.bbox(monde)
    dims = [b[1] - b[0] for b in bb]
    assert max(dims) == pytest.approx(80.0)
    assert bb[2][0] == pytest.approx(0.0)                 # Z posé au sol
    assert bb[0][0] == pytest.approx(-bb[0][1])           # centré en X
    assert bb[1][0] == pytest.approx(-bb[1][1])           # centré en Y
    # « tel quel » : échelle identité, mais centré/posé quand demandé
    brut = P3.mettre_a_l_echelle(tris, cible_mm=None)
    bb2 = P3.bbox(brut)
    assert bb2[2][0] == pytest.approx(0.0)
    assert bb2[0][1] - bb2[0][0] == pytest.approx(2.0)
    with pytest.raises(ValueError, match="cible"):
        P3.mettre_a_l_echelle(tris, cible_mm=-5)


def test_le_3mf_est_un_zip_xml_en_millimetres():
    import io
    import xml.etree.ElementTree as ET
    import zipfile
    from app.services import print3d as P3
    data = P3.ecrire_3mf(_deux_triangles(), nom="Banc")
    z = zipfile.ZipFile(io.BytesIO(data))
    assert "[Content_Types].xml" in z.namelist()
    assert "_rels/.rels" in z.namelist()
    xml = z.read("3D/3dmodel.model").decode("utf-8")
    root = ET.fromstring(xml)                              # XML valide
    assert root.get("unit") == "millimeter"
    ns = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
    sommets = root.findall(f".//{ns}vertex")
    faces = root.findall(f".//{ns}triangle")
    assert len(faces) == 2
    assert len(sommets) == 4                # 6 bruts → 4 : dédup MESURÉE
    assert root.find(f".//{ns}build/{ns}item") is not None


def test_le_lecteur_lit_un_glb_du_producteur_maison():
    # le GLB que l'app produit ELLE-MÊME (Material Forge) se lit tel quel
    from app.services import print3d as P3
    from app.services.gltf_builder import build_glb
    glb = build_glb({}, {}, mesh="cube")
    tris = P3.lire_glb_triangles(glb)
    assert len(tris) >= 12
    xs = [v[0] for t in tris for v in t]
    assert max(xs) > min(xs)              # un volume, pas un point


# ── C. dossiers d'export + routes + ouverture slicer GARDÉE ──────────────────

def test_les_routes_print3d_exportent_et_ouvrent():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services import print3d as P3
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        base = pathlib.Path(_tmp, "print3d")
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            # un job assets3d de banc : SEUL model.glb existe (lisible)
            job = pathlib.Path(_tmp, "outputs", "assets3d", "job_banc")
            job.mkdir(parents=True)
            (job / "model.glb").write_bytes(_glb_cube_translate())
            r = await c.post("/api/print3d/from-assets3d/job_banc",
                             json={"cible_mm": 80, "nom": "Banc figurine"})
            assert r.status_code == 200, r.text
            d = r.json()
            dossier = base / d["dossier"]
            assert (dossier / d["stl"]).is_file()
            assert (dossier / d["mf3"]).is_file()
            meta = _json.loads((dossier / "impression.json")
                               .read_text("utf-8"))
            assert meta["cible_mm"] == 80
            assert meta["etancheite"] == "inconnue"
            assert meta["source"] == "assets3d:job_banc"
            # le STL écrit est à l'échelle : plus grande dimension = 80
            stl = (dossier / d["stl"]).read_bytes()
            tris = P3.lire_stl(stl)
            dims = [b[1] - b[0] for b in P3.bbox(tris)]
            assert max(dims) == pytest.approx(80.0, abs=1e-3)
            # job inconnu → 404 ; opt.glb SEUL → 409 parlant
            r = await c.post("/api/print3d/from-assets3d/fantome",
                             json={"cible_mm": 80})
            assert r.status_code == 404
            job2 = pathlib.Path(_tmp, "outputs", "assets3d", "job_opt")
            job2.mkdir(parents=True)
            (job2 / "model.opt.glb").write_bytes(b"meshopt-optimise")
            r = await c.post("/api/print3d/from-assets3d/job_opt",
                             json={"cible_mm": 80})
            assert r.status_code == 409 and "model.glb" in r.json()["detail"]
            # la voie STL directe (Forge 3D cartes, Vectorlab) : corps binaire
            stl_brut = P3.ecrire_stl([
                ((0, 0, 0), (10, 0, 0), (0, 10, 0)),
                ((10, 0, 0), (10, 10, 0), (0, 10, 0))])
            r = await c.post("/api/print3d/from-stl?nom=Plaque banc"
                             "&source=vectorlab&etanche=garantie",
                             content=stl_brut,
                             headers={"Content-Type":
                                      "application/octet-stream"})
            assert r.status_code == 200, r.text
            d2 = r.json()
            meta2 = _json.loads((base / d2["dossier"] / "impression.json")
                                .read_text("utf-8"))
            assert meta2["etancheite"] == "garantie"
            assert meta2["cible_mm"] is None          # « tel quel »
            # pas un STL → 400 sans dossier créé
            n_avant = len(list(base.iterdir()))
            r = await c.post("/api/print3d/from-stl?nom=X",
                             content=b"pas un stl du tout")
            assert r.status_code == 400
            assert len(list(base.iterdir())) == n_avant
            # la liste datée
            r = await c.get("/api/print3d/exports")
            noms = [e["dossier"] for e in r.json()["exports"]]
            assert d["dossier"] in noms and d2["dossier"] in noms
            # OUVERTURE GARDÉE : l'ouvreur est mocké — le banc n'ouvre RIEN
            appels = []
            vrai = P3._lancer_startfile
            P3._lancer_startfile = lambda chemin: appels.append(chemin)
            try:
                r = await c.post("/api/print3d/open",
                                 json={"dossier": d["dossier"]})
                assert r.status_code == 200, r.text
                assert r.json()["mode"] == "association"
                assert len(appels) == 1 and appels[0].endswith(".3mf")
                # dossier inconnu → 404 ; traversée → 400, JAMAIS d'appel
                r = await c.post("/api/print3d/open",
                                 json={"dossier": "n-existe-pas"})
                assert r.status_code == 404
                r = await c.post("/api/print3d/open",
                                 json={"dossier": "../images"})
                assert r.status_code == 400
                assert len(appels) == 1
            finally:
                P3._lancer_startfile = vrai

    asyncio.run(scenario())
