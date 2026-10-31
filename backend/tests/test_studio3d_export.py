# -*- coding: utf-8 -*-
"""t400 (31/10/2026) — écran EXPORTER du 3D Studio : les trois GLB (maillage seul, pose, animation), les clips au
format three.js, le paquet three.js, le FBX par Blender (faux Blender au banc), les routes et leurs refus.

Jobs SYNTHÉTIQUES (aucun réseau, aucune dépense) : le personnage riggé de `_squelette_synthetique.glb_cible` auquel le
banc ajoute deux clips (« Marche » linéaire, « Saut » en STEP), et une boîte sans rig ni clip.
Run : python tests/test_studio3d_export.py (depuis backend/)"""
import asyncio, io, json, math, os, pathlib, shutil, struct, subprocess, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3x_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import mesh_edit as ME, print3d, studio3d_export as SE   # noqa: E402
import _squelette_synthetique as SQ                               # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = settings.outputs_path / "assets3d"
R90Z = [0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5)]


def boite():
    P = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return print3d.glb_de_pieces([("m", [(P[a], P[b], P[c]) for a, b, c in F])])


def anime() -> bytes:
    """Le personnage riggé + deux clips : « Marche » (os 2 : rotation 90° Z → repos, LINEAR, 0..1 s ; os 1 :
    translation) et « Saut » (os 1 : translation en STEP, 0,5..1,5 s)."""
    doc, binc = ME.lire_glb(SQ.glb_cible())
    binc = bytearray(binc)

    def acc(valeurs, type_, n):
        binc.extend(b"\x00" * (-len(binc) % 4))
        d = len(binc)
        binc.extend(struct.pack(f"<{len(valeurs)}f", *valeurs))
        doc["bufferViews"].append({"buffer": 0, "byteOffset": d, "byteLength": len(binc) - d})
        a = {"bufferView": len(doc["bufferViews"]) - 1, "componentType": 5126, "count": n, "type": type_}
        if type_ == "SCALAR":
            a["min"], a["max"] = [min(valeurs)], [max(valeurs)]
        doc["accessors"].append(a)
        return len(doc["accessors"]) - 1
    t01 = acc([0.0, 1.0], "SCALAR", 2)
    rot = acc(R90Z + [0, 0, 0, 1], "VEC4", 2)
    tr = acc([0.1, 0.2, 0.3, 0.0, 0.0, 0.0], "VEC3", 2)
    t2 = acc([0.5, 1.5], "SCALAR", 2)
    tr2 = acc([0.0, 0.7, 0.0, 0.0, 0.0, 0.0], "VEC3", 2)
    doc["animations"] = [
        {"name": "Marche", "samplers": [{"input": t01, "output": rot}, {"input": t01, "output": tr}],
         "channels": [{"sampler": 0, "target": {"node": 2, "path": "rotation"}},
                      {"sampler": 1, "target": {"node": 1, "path": "translation"}}]},
        {"name": "Saut", "samplers": [{"input": t2, "output": tr2, "interpolation": "STEP"}],
         "channels": [{"sampler": 0, "target": {"node": 1, "path": "translation"}}]},
    ]
    doc["buffers"] = [{"byteLength": len(binc)}]
    return ME.ecrire_glb(doc, bytes(binc))


ANIME = anime()


def _job(nom, fichiers, manifeste):
    d = J / nom
    d.mkdir(parents=True, exist_ok=True)
    for f, octets in fichiers.items():
        (d / f).write_bytes(octets)
    (d / "asset.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return d


_job("heros", {"model.glb": boite(), "model.v2.glb": ANIME},
     {"name": "Héros vert", "engine": "tripo", "created_at": "2026-10-30T10:00:00+00:00"})
_job("caisse", {"model.glb": boite()}, {"name": "caisse", "engine": "trellis", "created_at": "2026-10-29T10:00:00+00:00"})


def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _valide(octets: bytes):
    """Un GLB relu sans erreur dont chaque accesseur se lit dans le tampon (aucune vue hors bornes)."""
    doc, binc = ME.lire_glb(octets)
    for v in doc.get("bufferViews") or []:
        assert v.get("byteOffset", 0) + v["byteLength"] <= len(binc), v
    for i in range(len(doc.get("accessors") or [])):
        ME.lire_accesseur(doc, binc, i)
    return doc, binc


# ── les variantes ────────────────────────────────────────────────────────────

def test_le_maillage_seul_perd_les_clips_garde_la_peau_et_compacte_le_tampon():
    src, sbin = ME.lire_glb(ANIME)
    out = SE.glb_maillage(ANIME)
    doc, binc = _valide(out)
    assert "animations" not in doc
    assert len(doc["skins"]) == 1 and len(doc["skins"][0]["joints"]) == len(src["skins"][0]["joints"])
    assert [n.get("name") for n in doc["nodes"]] == [n.get("name") for n in src["nodes"]]
    # les cinq accesseurs des clips sont partis avec leurs octets (recopie, pas ré-encodage)
    assert len(doc["accessors"]) == len(src["accessors"]) - 5
    assert len(binc) < len(sbin)
    p = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    p0 = src["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    assert ME.lire_accesseur(doc, binc, p) == ME.lire_accesseur(src, sbin, p0)
    # une boîte sans rig : le même maillage, sans peau inventée
    d2, _ = _valide(SE.glb_maillage(boite()))
    assert "animations" not in d2 and not d2.get("skins") and SE._triangles(d2) == 12


def test_la_pose_fige_la_premiere_image_du_clip_choisi():
    out, info = SE.glb_pose(ANIME)
    doc, _ = _valide(out)
    assert info == {"pose": "premiere_image", "clip": "Marche"}
    assert "animations" not in doc and len(doc["skins"]) == 1
    assert all(abs(a - b) < 1e-6 for a, b in zip(doc["nodes"][2]["rotation"], R90Z))
    assert all(abs(a - b) < 1e-6 for a, b in zip(doc["nodes"][1]["translation"], [0.1, 0.2, 0.3]))
    out2, info2 = SE.glb_pose(ANIME, "Saut")
    d2, _ = _valide(out2)
    assert info2["clip"] == "Saut" and abs(d2["nodes"][1]["translation"][1] - 0.7) < 1e-6
    assert "rotation" not in d2["nodes"][2] or d2["nodes"][2]["rotation"] != R90Z
    _o, info3 = SE.glb_pose(boite())
    assert info3 == {"pose": "repos", "clip": None}
    for mauvais in ("Course", 7, True):
        try:
            SE.glb_pose(ANIME, mauvais)
            raise AssertionError(mauvais)
        except SE.RefusExport:
            pass


def test_l_animation_part_telle_quelle_ou_reduite_aux_clips_coches():
    assert SE.glb_animation(ANIME) == ANIME
    doc, _ = _valide(SE.glb_animation(ANIME, ["Saut"]))
    assert [a["name"] for a in doc["animations"]] == ["Saut"] and len(doc["skins"]) == 1
    doc, _ = _valide(SE.glb_animation(ANIME, [1, 0]))
    assert [a["name"] for a in doc["animations"]] == ["Marche", "Saut"]
    for args in ((boite(), None), (ANIME, ["Course"]), (ANIME, "Saut")):
        try:
            SE.glb_animation(*args)
            raise AssertionError(args)
        except SE.RefusExport:
            pass


def test_les_clips_au_format_three_js():
    assert SE.clips(ANIME) == [{"index": 0, "nom": "Marche", "pistes": 2, "duree": 1.0},
                               {"index": 1, "nom": "Saut", "pistes": 1, "duree": 1.5}]
    doc, binc = ME.lire_glb(ANIME)
    noms = SE.noms_three(doc)
    c = SE.clip_three(doc, binc, 0)
    assert c["name"] == "Marche" and c["duration"] == 1.0 and c["blendMode"] == 2500
    pistes = {p["name"]: p for p in c["tracks"]}
    q = pistes[f"{noms[2]}.quaternion"]
    assert q["type"] == "quaternion" and q["times"] == [0.0, 1.0] and len(q["values"]) == 8
    assert q["interpolation"] == 2301 and abs(q["values"][2] - R90Z[2]) < 1e-6
    assert pistes[f"{noms[1]}.position"]["type"] == "vector"
    s = SE.clip_three(doc, binc, 1)
    assert s["tracks"][0]["interpolation"] == 2300 and s["duration"] == 1.5
    # l'assainissement de PropertyBinding et l'unicité de GLTFParser
    assert SE.nom_three("mixamorig:Left Arm.001") == "mixamorigLeft_Arm001"
    assert SE.noms_three({"nodes": [{"name": "a b"}, {"name": "a.b"}, {"name": "a_b"}, {}]}) == ["a_b", "ab", "a_b_1", ""]


def test_le_paquet_three_js():
    octets, man = SE.paquet_threejs(ANIME, nom="Heros", job="heros", version=2)
    z = zipfile.ZipFile(io.BytesIO(octets))
    assert sorted(z.namelist()) == sorted([
        "characters/Heros/character.glb", "characters/Heros/manifest.json",
        "characters/Heros/clips/Marche.clip.json", "characters/Heros/clips/Saut.clip.json",
        "runtime/deepotus-personnage.js", "AGENT_INSTRUCTIONS.md"])
    m = json.loads(z.read("characters/Heros/manifest.json"))
    assert m == man
    assert m["source"] == {"job": "heros", "version": 2, "outil": "DeepotusVideo 3D Studio"}
    assert m["glb"] == "character.glb" and m["rigge"] is True and m["triangles"] == SE._triangles(ME.lire_glb(ANIME)[0])
    assert len(m["os"]) == len(ME.rig_inventory(ANIME)["os"]) and m["physique"] is None
    assert [(c["nom"], c["fichier"]) for c in m["clips"]] == [("Marche", "clips/Marche.clip.json"),
                                                              ("Saut", "clips/Saut.clip.json")]
    assert z.read("characters/Heros/character.glb") == ANIME
    cj = json.loads(z.read("characters/Heros/clips/Saut.clip.json"))
    assert cj["name"] == "Saut" and cj["tracks"]
    rt = z.read("runtime/deepotus-personnage.js").decode("utf-8")
    assert "© DeepotusVideo" in rt and "AnimationMixer" in rt and "AnimationClip.parse" in rt
    assert "characters/Heros/" in z.read("AGENT_INSTRUCTIONS.md").decode("utf-8")
    # réduit aux clips cochés : le GLB ET les .clip.json
    o2, m2 = SE.paquet_threejs(ANIME, nom="Heros", job="heros", version=2, voulus=["Marche"])
    z2 = zipfile.ZipFile(io.BytesIO(o2))
    assert [c["nom"] for c in m2["clips"]] == ["Marche"]
    assert "characters/Heros/clips/Saut.clip.json" not in z2.namelist()
    assert [a["name"] for a in ME.lire_glb(z2.read("characters/Heros/character.glb"))[0]["animations"]] == ["Marche"]


def test_les_noms_de_fichier_sont_surs():
    assert SE.nom_sur("Héros vert/../x", "d") == "Heros_vert_x"
    assert SE.nom_sur("", "job 1") == "job_1" and SE.nom_sur("///", "") == "modele"
    for mauvais in ("..", "a/b", "", ".", "a\\b"):
        try:
            SE.job_nu(mauvais)
            raise AssertionError(mauvais)
        except SE.RefusExport:
            pass


# ── le FBX par un FAUX Blender ───────────────────────────────────────────────

def test_le_fbx_passe_par_blender_avec_un_script_fixe():
    vus = []

    def faux(argv, delai):
        vus.append(argv)
        p = json.loads(argv[argv.index("--") + 1])
        assert pathlib.Path(p["source"]).is_file() and argv[1:4] == ["-b", "--factory-startup", "--python"]
        pathlib.Path(p["sortie"]).write_bytes(b"Kaydara FBX Binary  \x00" + (b"A" if p["animation"] else b"M"))
        return 0, "DZFBX fin"
    ancien_b, ancien_x = SE._blender, SE._executer
    try:
        SE._blender = lambda: {"dispo": True, "exe": "C:/faux/blender.exe", "version": "5.2.2", "raison": None}
        SE._executer = faux
        r = SE.exporter_fbx("heros", 2, variante="animation", nom="Heros")
        assert r["fichier"] == "Heros_v2_animation.fbx" and r["blender"] == "5.2.2"
        assert SE.chemin_fichier("heros", r["fichier"]).read_bytes().endswith(b"A")
        assert SE.exporter_fbx("caisse", None)["variante"] == "maillage"       # rien à cuire
        assert not [p for p in SE.dossier_exports("heros").iterdir() if p.name.startswith("_blender_")]
        SE._executer = lambda argv, d: (1, "Error: boom\n")
        try:
            SE.exporter_fbx("heros", 2)
            raise AssertionError("échec non vu")
        except RuntimeError as e:
            assert "boom" in str(e)
        SE._blender = lambda: {"dispo": False, "exe": None, "version": None, "raison": "absent"}
        try:
            SE.exporter_fbx("heros", 2)
            raise AssertionError("Blender absent non vu")
        except SE.BlenderIndisponible:
            pass
    finally:
        SE._blender, SE._executer = ancien_b, ancien_x


# ── les routes ───────────────────────────────────────────────────────────────

def test_les_routes_ecrivent_sous_exports_et_servent_par_get():
    async def go():
        async with _client() as c:
            e = await c.get("/api/studio3d/exporter/heros")
            assert e.status_code == 200, e.text
            ej = e.json()
            assert ej["version"] == 2 and [k["nom"] for k in ej["clips"]] == ["Marche", "Saut"]
            assert ej["a_squelette"] and any(o["role"] for o in ej["os"]) and "dispo" in ej["blender"]
            r = await c.post("/api/studio3d/exporter/heros/glb", json={"variante": "maillage", "nom": "Héros"})
            assert r.status_code == 200, r.text
            rj = r.json()
            assert rj["fichier"] == "Heros_v2_maillage.glb" and rj["clips"] == [] and rj["peaux"] == 1
            g = await c.get(rj["url"])
            assert g.status_code == 200 and g.content == (J / "heros" / "exports" / rj["fichier"]).read_bytes()
            r = await c.post("/api/studio3d/exporter/heros/glb", json={"variante": "pose", "clip": "Saut", "version": 2})
            assert r.status_code == 200 and r.json()["clip"] == "Saut"
            r = await c.post("/api/studio3d/exporter/heros/threejs", json={"clips": ["Saut"]})
            assert r.status_code == 200, r.text
            assert "runtime/deepotus-personnage.js" in r.json()["entrees"]
            z = await c.get(r.json()["url"])
            assert z.status_code == 200 and zipfile.ZipFile(io.BytesIO(z.content)).testzip() is None
            e2 = (await c.get("/api/studio3d/exporter/heros")).json()
            assert {"Heros_v2_maillage.glb", "Heros_vert_v2_pose.glb", "Heros_vert_v2_threejs.zip"} <= {
                x["fichier"] for x in e2["exports"]}
    asyncio.run(go())


def test_les_refus():
    async def go():
        async with _client() as c:
            for chemin, corps, code in [
                ("/api/studio3d/exporter/heros/glb", {"variante": "nuage"}, 400),
                ("/api/studio3d/exporter/heros/glb", {"variante": "maillage", "version": 0}, 400),
                ("/api/studio3d/exporter/heros/glb", {"variante": "maillage", "version": "2"}, 400),
                ("/api/studio3d/exporter/heros/glb", {"variante": "maillage", "version": 9}, 404),
                ("/api/studio3d/exporter/inconnu/glb", {"variante": "maillage"}, 404),
                ("/api/studio3d/exporter/caisse/glb", {"variante": "animation"}, 400),
                ("/api/studio3d/exporter/heros/glb", {"variante": "pose", "clip": "Course"}, 400),
                ("/api/studio3d/exporter/heros/threejs", {"clips": ["Course"]}, 400),
                ("/api/studio3d/exporter/heros/fbx", {"variante": "pose"}, 400),
            ]:
                r = await c.post(chemin, json=corps)
                assert r.status_code == code, (chemin, corps, r.status_code, r.text)
            for url, code in [("/api/studio3d/exporter/heros/fichier/absent.glb", 404),
                              ("/api/studio3d/exporter/heros/fichier/model.exe", 400),
                              ("/api/studio3d/exporter/heros/fichier/..%5Cmodel.glb", 400),
                              ("/api/studio3d/exporter/inconnu", 404),
                              ("/api/studio3d/exporter/impression/x/y.exe", 400),
                              ("/api/studio3d/exporter/impression/x/y.stl", 404)]:
                r = await c.get(url)
                assert r.status_code == code, (url, r.status_code, r.text)
            ancien = SE._blender
            SE._blender = lambda: {"dispo": False, "exe": None, "version": None, "raison": "absent"}
            try:
                r = await c.post("/api/studio3d/exporter/heros/fbx", json={})
                assert r.status_code == 503 and "blender.org" in r.json()["detail"]
            finally:
                SE._blender = ancien
    asyncio.run(go())


# ── la page ─────────────────────────────────────────────────────────────────

def test_la_page_branche_l_ecran_et_ses_cles():
    coque = (RACINE / "frontend/studio3d/ecrans/coque.js").read_text(encoding="utf-8")
    assert 'exporter: "./exporter.js"' in coque
    html = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert html.count('href="ecrans/exporter.css"') == 1
    dico = json.loads((RACINE / "frontend/shared/i18n/studio3decrans_exporter.json").read_text(encoding="utf-8"))
    import re
    src = (RACINE / "frontend/studio3d/ecrans/exporter.js").read_text(encoding="utf-8") \
        + (RACINE / "frontend/studio3d/ecrans/exporter_calc.js").read_text(encoding="utf-8")
    cles = {k for k in re.findall(r'\bT\("(exp\.[a-z0-9_]+)"', src) if not k.endswith("_")}   # familles : banc node
    assert len(cles) > 30, len(cles)
    for k in cles:
        assert "studio3decrans." + k in dico, k
    for k, v in dico.items():
        assert k.startswith("studio3decrans.exp.") and len(k.split(".")) == 3 and v.get("contexte") is True, k
        assert v["fr"] and v["en"], k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    css = (RACINE / "frontend/studio3d/ecrans/exporter.css").read_text(encoding="utf-8")
    assert "border-radius" not in css and "border-radius" not in src
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.exp.titre"' in assembled, "relancer scripts/i18n_assembler.py"


def test_le_calcul_de_l_ecran_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/exporter.test.mjs")], capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr


def lancer_tous():
    rouges = []
    for nom, fn in list(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (3D Studio · Exporter)")
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
