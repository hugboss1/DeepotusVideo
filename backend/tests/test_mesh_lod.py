# -*- coding: utf-8 -*-
"""T105 (plan-moteurs-3d T3, R10e P2) — chaîne de LOD, perte mesurée, budget par usage. Le banc relit les GLB
ÉCRITS (compteurs, noms de mesh et de nœud), les PNG de silhouette écrits et lod.json ; gltfpack est le vrai binaire
embarqué. Puis les routes, par de vrais appels HTTP (ASGI) : lecture avec budgets, construction, refus parlants,
fichiers servis par NUMÉRO, archive.
Run : python tests/test_mesh_lod.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzlod_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import gltf_builder, mesh_edit, mesh_lod, mesh_optimize  # noqa: E402


def _job(nom: str, forme: str = "sphere") -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb({}, None, forme, nom))
    return d


def test_les_budgets_par_usage_sont_decroissants_et_motives():
    b = {x["id"]: x for x in mesh_lod.budgets()}
    assert set(b) == {"mobile", "pc", "impression"}, sorted(b)
    for x in b.values():
        assert x["label"] and x["pourquoi"], x
        n = x["niveaux"]
        assert n == sorted(n, reverse=True) and len(set(n)) == len(n), x


def test_un_budget_plus_lourd_que_la_source_ou_croissant_est_refuse_en_le_disant():
    _job("lod_refus")
    src = mesh_optimize.glb_stats(settings.outputs_path / "assets3d" / "lod_refus" / "model.glb")["tris"]
    for niveaux, mot in (([10_000_000], "n'allègerait rien"), ([src], "n'allègerait rien"), ([2000, 3000], "DÉCROÎTRE"),
                         ([300, 300], "DÉCROÎTRE"), (["x"], "entiers"),
                         ([], "au moins un"), (list(range(900, 100, -100)), "8 au plus")):
        try:
            mesh_lod.chaine("lod_refus", niveaux=niveaux)
            raise AssertionError(f"aurait dû refuser {niveaux}")
        except ValueError as e:
            assert mot in str(e), (niveaux, e)
    try:
        mesh_lod.chaine("lod_refus", usage="console_portable")
        raise AssertionError("usage inconnu accepté")
    except ValueError as e:
        assert "usage inconnu" in str(e), e
    assert not (settings.outputs_path / "assets3d" / "lod_refus" / "lod").exists(), "un refus n'écrit RIEN"


def test_la_chaine_ecrit_quatre_glb_nommes_pour_unity():
    d = _job("lod_ok")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    info = mesh_lod.chaine("lod_ok", niveaux=[src // 2, src // 6, src // 20])
    assert [n["niveau"] for n in info["niveaux"]] == [0, 1, 2, 3], info
    precedent = None
    for n in info["niveaux"]:
        p = d / "lod" / n["file"]
        assert p.is_file(), n
        lus = mesh_optimize.glb_stats(p)                 # on RELIT le fichier
        assert lus["tris"] == n["tris"], (n, lus)
        if precedent is not None:
            assert lus["tris"] < precedent, (n, precedent)
            assert lus["tris"] <= n["cible"] * 1.15, ("cible non tenue", n)
        precedent = lus["tris"]
        doc, _ = mesh_edit.lire_glb(p.read_bytes())
        noms = [m.get("name") or "" for m in doc["meshes"]]
        assert noms and all(x.endswith(f"_LOD{n['niveau']}") for x in noms), (n, noms)
        assert not any(x.count("_LOD") > 1 for x in noms), noms          # jamais _LOD0_LOD1
        noeuds = [q.get("name") or "" for q in doc["nodes"] if "mesh" in q]
        assert noeuds and all(x.endswith(f"_LOD{n['niveau']}") for x in noeuds), (n, noeuds)
    assert info["niveaux"][0]["tris"] == src, "le LOD0 EST la source"
    assert all(n["cible_tenue"] is True for n in info["niveaux"][1:]), info["niveaux"]


def test_une_cible_hors_d_atteinte_est_dite_non_tenue():
    """Mesuré sur 8799 : gltfpack protège la topologie et s'arrête au-dessus d'une cible trop basse, même en -sa."""
    d = _job("lod_plancher")
    info = mesh_lod.chaine("lod_plancher", niveaux=[100])
    n1 = info["niveaux"][1]
    assert n1["tris"] > 115 and n1["cible_tenue"] is False and n1["aggressive"] is True, n1
    nom, octets = mesh_lod.archive("lod_plancher")
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        assert "cible non tenue" in z.read("LISEZMOI.txt").decode("utf-8")


def test_une_source_deja_suffixee_ne_double_jamais_le_suffixe():
    d = _job("lod_suffixe")
    doc, binc = mesh_edit.lire_glb((d / "model.glb").read_bytes())
    for m in doc["meshes"]:
        m["name"] = "statue_LOD0"
    for q in doc["nodes"]:
        if "mesh" in q:
            q["name"] = "statue_LOD0"
    (d / "model.glb").write_bytes(mesh_edit.ecrire_glb(doc, binc))
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    mesh_lod.chaine("lod_suffixe", niveaux=[src // 2])
    doc1, _ = mesh_edit.lire_glb((d / "lod" / "lod1.glb").read_bytes())
    assert [m["name"] for m in doc1["meshes"]] == ["statue_LOD1"], [m["name"] for m in doc1["meshes"]]


def test_la_perte_est_mesuree_contre_le_LOD0_et_croit_avec_la_decimation():
    d = _job("lod_perte")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    info = mesh_lod.chaine("lod_perte", niveaux=[src // 2, src // 20])
    n0, n1, n2 = info["niveaux"]
    assert n0["perte"]["iou_min"] == 1.0 and n0["perte"]["ecart_normales"] == 0.0
    for n in (n1, n2):
        assert n["perte"]["mesure"] is True, n
        assert set(n["perte"]["iou"]) == {"face", "profil", "dessus"}, n
        assert 0.0 < n["perte"]["iou_min"] <= 1.0, n
        assert 0.0 <= n["perte"]["ecart_normales"] <= 1.0, n
        for vue in ("face", "profil", "dessus"):
            assert (d / "lod" / f"sil_lod{n['niveau']}" / f"silhouette_{vue}.png").is_file(), n

    assert all("signature" not in n["perte"] for n in (n0, n1, n2)), "la signature brute ne quitte pas le calcul"
    assert n2["perte"]["ecart_normales"] > n1["perte"]["ecart_normales"], (n1, n2)
    assert n2["perte"]["iou_min"] <= n1["perte"]["iou_min"] + 1e-9, (n1, n2)
    # la silhouette SEULE ne suffit pas : c'est pourquoi l'écart de normales existe
    assert n1["perte"]["iou_min"] > 0.9 and n1["perte"]["ecart_normales"] > 0.0, n1
    relu = json.loads((d / "lod" / "lod.json").read_text("utf-8"))
    assert relu == info, "lod.json doit être exactement ce qui est rendu"


def test_une_chaine_neuve_efface_les_niveaux_de_la_precedente():
    d = _job("lod_rejeu")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    avant = (d / "model.glb").read_bytes()
    mesh_lod.chaine("lod_rejeu", niveaux=[src // 2, src // 6, src // 20])
    assert (d / "lod" / "lod3.glb").is_file()
    mesh_lod.chaine("lod_rejeu", niveaux=[src // 3])
    assert not (d / "lod" / "lod3.glb").exists(), "LOD3 orphelin de la chaîne d'avant"
    assert not (d / "lod" / "sil_lod3").exists(), "silhouettes orphelines"
    assert (d / "model.glb").read_bytes() == avant, "la source n'est JAMAIS touchée"


def test_la_source_est_le_glb_courant_du_registre():
    from app.services import mesh_report
    d = _job("lod_courant")
    (d / "model.v2.glb").write_bytes(gltf_builder.build_glb({}, None, "torus", "v2"))
    mesh_report.write_report("lod_courant", "model.v2.glb", version=2, avec_silhouettes=False)
    src = mesh_optimize.glb_stats(d / "model.v2.glb")["tris"]
    info = mesh_lod.chaine("lod_courant", niveaux=[src // 2])
    assert info["source"] == "model.v2.glb" and info["niveaux"][0]["tris"] == src, info


def test_l_archive_porte_les_glb_le_json_et_le_lisezmoi():
    d = _job("lod_zip")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    mesh_lod.chaine("lod_zip", niveaux=[src // 2, src // 8])
    nom, octets = mesh_lod.archive("lod_zip")
    assert nom == "lod_zip_LOD.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert noms == ["LISEZMOI.txt", "lod.json", "lod0.glb", "lod1.glb", "lod2.glb"], noms
        txt = z.read("LISEZMOI.txt").decode("utf-8")
        assert "_LOD" in txt and "Godot" in txt and "IoU" in txt and "NON vérifiée" in txt, txt[:400]
        assert mesh_edit.lire_glb(z.read("lod1.glb"))[0]["meshes"], "GLB illisible"


def test_la_signature_de_normales_distingue_un_cube_d_une_sphere():
    from app.services import print3d
    cube = print3d.lire_glb_triangles(gltf_builder.build_glb({}, None, "cube", "c"))
    sph = print3d.lire_glb_triangles(gltf_builder.build_glb({}, None, "sphere", "s"))
    sc, ss = mesh_lod.signature_normales(cube), mesh_lod.signature_normales(sph)
    assert abs(sum(sc) - 1.0) < 1e-3 and abs(sum(ss) - 1.0) < 1e-3
    assert mesh_lod.ecart_normales(sc, sc) == 0.0
    assert mesh_lod.ecart_normales(sc, ss) > 0.4, mesh_lod.ecart_normales(sc, ss)
    haut = ((0, 0, 0), (2, 0, 0), (0, 2, 0))            # aire 2, normale +z
    bas = ((0, 0, 0), (0, 1, 0), (1, 0, 0))             # aire 0,5, normale -z
    sig = mesh_lod.signature_normales([haut, bas])
    assert sorted(v for v in sig if v) == [0.2, 0.8], [v for v in sig if v]          # PONDÉRÉ par l'aire
    assert mesh_lod.ecart_normales(mesh_lod.signature_normales([haut]), mesh_lod.signature_normales([bas])) == 1.0
    try:
        mesh_lod.signature_normales([((0, 0, 0), (1, 0, 0), (2, 0, 0))])
        raise AssertionError("un maillage sans aire n'a pas de signature")
    except ValueError:
        pass


def test_les_routes_lod_sont_declarees_avant_le_catch_all():
    """Le catch-all `/assets/3d/{job}/{fmt}` avalerait `/lod` : FastAPI sert la PREMIÈRE route déclarée qui
    apparie. On lit l'ordre réel du routeur."""
    from app.api.routes import router
    chemins = [r.path for r in router.routes if hasattr(r, "path")]
    fmt = chemins.index("/assets/3d/{job}/{fmt}")
    for p in ("/assets/3d/{job}/lod", "/assets/3d/{job}/lod/{niveau}", "/assets/3d/{job}/lod-zip"):
        assert p in chemins, p
        assert chemins.index(p) < fmt, f"{p} déclarée APRÈS le catch-all"


def test_les_routes_lod_de_bout_en_bout():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    d = _job("lod_route")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            g = (await c.get("/api/assets/3d/lod_route/lod")).json()
            o["avant"] = (g["chaine"], [b["id"] for b in g["budgets"]])
            o["inconnu"] = (await c.post("/api/assets/3d/absent/lod", json={"niveaux": [10]})).status_code
            o["croissant"] = (await c.post("/api/assets/3d/lod_route/lod", json={"niveaux": [100, 200]})).status_code
            o["pas_liste"] = (await c.post("/api/assets/3d/lod_route/lod", json={"niveaux": "9"})).status_code
            o["zip_avant"] = (await c.get("/api/assets/3d/lod_route/lod-zip")).status_code
            p = await c.post("/api/assets/3d/lod_route/lod", json={"niveaux": [src // 2, src // 6]})
            o["post"] = (p.status_code, [n["niveau"] for n in p.json().get("niveaux", [])])
            g2 = (await c.get("/api/assets/3d/lod_route/lod")).json()
            o["apres"] = len(g2["chaine"]["niveaux"])
            f = await c.get("/api/assets/3d/lod_route/lod/1")
            o["lod1"] = (f.status_code, f.headers.get("content-type"), f.content[:4])
            o["lod9"] = (await c.get("/api/assets/3d/lod_route/lod/9")).status_code
            z = await c.get("/api/assets/3d/lod_route/lod-zip")
            o["zip"] = (z.status_code, z.headers.get("content-disposition"), z.content[:2])
        return o
    o = asyncio.run(main())
    assert o["avant"] == (None, ["mobile", "pc", "impression"]), o["avant"]
    assert o["inconnu"] == 404 and o["croissant"] == 400 and o["pas_liste"] == 400, o
    assert o["zip_avant"] == 404, o["zip_avant"]
    assert o["post"] == (200, [0, 1, 2]) and o["apres"] == 3, (o["post"], o["apres"])
    assert o["lod1"] == (200, "model/gltf-binary", b"glTF") and o["lod9"] == 404, (o["lod1"], o["lod9"])
    assert o["zip"][0] == 200 and 'filename="lod_route_LOD.zip"' in o["zip"][1] and o["zip"][2] == b"PK", o["zip"]


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_lod)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
