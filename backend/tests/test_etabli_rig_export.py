"""L'Établi P4+P5 — le rig REGARDÉ, et la pièce emmenée dans un moteur (tâche T093, plan
2026-08-29-etabli-p4-p5-rig-export).

LE RIG EST EXÉCUTÉ, PAS LU : `lib3d/rig.js` tourne sous node avec le VRAI three.js vendorisé (r185) et le VRAI
GLTFLoader, sur un GLB riggé fabriqué par `fabrique_rig.py` (aucune donnée de l'utilisateur n'a de squelette, relevé
du 06/10). Les bancs du plan ne cherchaient que des chaînes (« SkeletonHelper » in js) : un module cassé les passait.
Aucun lancement d'application : le crochet `_lancer` de l'export est remplacé au banc.

Run : cd backend ; & $PY -m pytest tests/test_etabli_rig_export.py -q
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY"):
    os.environ[_k] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(__file__).resolve().parents[2]
FRONT = RACINE / "frontend"
THREE = FRONT / "dist" / "assets" / "three"


def _lire(rel: str) -> str:
    return (FRONT / rel).read_text(encoding="utf-8")


def _code(rel: str) -> str:
    import re
    return re.sub(r"/\*.*?\*/", "", _lire(rel), flags=re.S)


def _fonction_etabli_async(nom: str) -> str:
    js = _lire("etabli/etabli.js")
    i = js.find("\nasync function " + nom + "(")
    assert i >= 0, nom
    return js[i:js.index("\n}\n", i) + 2]


_BAC = None


def _bac() -> pathlib.Path:
    """Un dossier jetable où node trouve `three` par son nom nu (node_modules), le GLTFLoader et rig.js."""
    global _BAC
    if _BAC is None:
        if not shutil.which("node"):
            pytest.skip("node absent : le rig ne peut pas être EXÉCUTÉ ici")
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "node_modules" / "three").mkdir(parents=True)
        for f in ("three.module.min.js", "three.core.min.js"):
            shutil.copy(THREE / f, d / "node_modules" / "three" / f)
        (d / "node_modules" / "three" / "package.json").write_text(json.dumps(
            {"name": "three", "type": "module", "exports": {".": "./three.module.min.js"}}), "utf-8")
        for rel in ("loaders/GLTFLoader.js", "utils/BufferGeometryUtils.js", "utils/SkeletonUtils.js"):
            (d / "addons" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(THREE / "addons" / rel, d / "addons" / rel)
        from fabrique_rig import glb_rigge
        (d / "rig.glb").write_bytes(glb_rigge())
        _BAC = d
    shutil.copy(FRONT / "lib3d" / "rig.js", _BAC / "rig.mjs")       # la version COURANTE (les mutants la changent)
    return _BAC


def _rig(corps: str) -> dict:
    d = _bac()
    src = """
import * as THREE from "three";
import { GLTFLoader } from "./addons/loaders/GLTFLoader.js";
import * as R from "./rig.mjs";
import { readFileSync } from "node:fs";
let RAF = 0;
globalThis.requestAnimationFrame = () => { RAF++; return RAF; };
const buf = readFileSync(new URL("./rig.glb", import.meta.url));
const gltf = await new GLTFLoader().parseAsync(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), "");
const api = { scene: new THREE.Scene(), racine: gltf.scene, gltf };
api.scene.add(gltf.scene);
const peau = () => { let p = null; api.racine.traverse((o) => { if (o.isSkinnedMesh && !p) p = o; }); return p; };
const os = (n) => { let b = null; api.racine.traverse((o) => { if (o.isBone && o.name === n) b = o; }); return b; };
const sommet = (i) => { const p = peau(); api.racine.updateMatrixWorld(true); p.skeleton.update();
  const v = new THREE.Vector3(); p.getVertexPosition(i, v); return [v.x, v.y, v.z].map((x) => Math.round(x * 1e6) / 1e6); };
const sortie = {};
""" + corps + """
console.log("@@" + JSON.stringify(sortie));
"""
    (d / "banc.mjs").write_text(src, "utf-8")
    r = subprocess.run(["node", str(d / "banc.mjs")], capture_output=True, timeout=60)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:1500]
    return json.loads(out.split("@@", 1)[1])


# ── A. le squelette ──────────────────────────────────────────────────────────
def test_l_arbre_des_os_fait_une_RACINE_d_un_parent_absent_et_survit_a_un_cycle_EXECUTEE():
    o = _rig("""
sortie.arbre = R.arbreDesOs([{ index: 2, nom: "racine", parent: 1 }, { index: 3, nom: "coude", parent: 2 },
                             { index: 4, nom: "main", parent: 3 }, { index: 7, nom: "queue", parent: 2 }]);
sortie.cycle = R.arbreDesOs([{ index: 0, nom: "a", parent: 1 }, { index: 1, nom: "b", parent: 0 }]);
""")
    assert [(x["nom"], x["profondeur"]) for x in o["arbre"]] == [("racine", 0), ("coude", 1), ("main", 2), ("queue", 1)]
    assert sorted(x["nom"] for x in o["cycle"]) == ["a", "b"], "un cycle ne boucle pas et ne perd personne"


def test_le_squelette_se_dessine_DANS_la_scene_et_la_chaine_d_un_os_se_surligne_EXECUTEE():
    o = _rig("""
const avant = api.scene.children.length;
const vu = R.poserSquelette(api);
sortie.a = vu.aSquelette; sortie.aides = api.scene.children.length - avant;
sortie.culling = peau().frustumCulled;
sortie.chaine = R.surlignerChaine(api, "coude");
sortie.apresChaine = api.scene.children.length - avant;
R.rangerRig(api);
sortie.apresRanger = api.scene.children.length - avant;
""")
    assert o["a"] is True and o["aides"] == 1 and o["culling"] is False
    assert o["chaine"] == ["coude", "main"] and o["apresChaine"] == 2
    assert o["apresRanger"] == 0, "les aides vivent dans la SCÈNE : vider() ne les retirerait pas"


# ── B. les poids d'influence ─────────────────────────────────────────────────
def test_la_couleur_d_un_poids_SOMME_les_citations_et_se_borne_EXECUTEE():
    o = _rig("""
sortie.c = Array.from(R.couleursDePoids([3, 3, 0, 0,  1, 0, 0, 0,  3, 2, 0, 0], [0.7, 0.6, 0, 0,  1, 0, 0, 0,  0.25, 0.75, 0, 0], 3, 3));
""")
    c = [round(x, 6) for x in o["c"]]
    assert c[0:3] == [1.0, 0.15, 0.0], "0,7 + 0,6 sur le même os : bornée à 1"
    assert c[3:6] == [0.0, 0.15, 1.0] and c[6:9] == [0.25, 0.15, 0.75]


def test_la_heatmap_peint_sur_un_materiau_CLONE_et_se_retire_EXECUTEE():
    o = _rig("""
R.poserSquelette(api);
const origine = peau().material;
sortie.touches = R.peindrePoids(api, "coude");
sortie.clone = peau().material !== origine && peau().material.vertexColors === true && origine.vertexColors !== true;
const col = peau().geometry.attributes.color.array;
sortie.anneau1 = [col[4 * 3], col[4 * 3 + 2]];          // sommet 4 : anneau y = 1, 0,5 sur le coude
sortie.anneau0 = [col[0], col[2]];
R.retirerPoids(api);
sortie.rendu = peau().material === origine && !peau().geometry.attributes.color;
""")
    assert o["touches"] == 8, "les anneaux y = 1 et y = 2 portent le coude"
    assert o["clone"] is True and o["rendu"] is True
    assert o["anneau1"] == [0.5, 0.5] and o["anneau0"] == [0, 1]


# ── C. pose d'essai et clips ─────────────────────────────────────────────────
def test_tourner_un_os_PLIE_la_peau_relativement_au_repos_et_le_repos_revient_EXECUTEE():
    o = _rig("""
R.poserSquelette(api); R.memoriserRepos(api);
sortie.avant = sommet(12);                               // anneau du haut, tenu par « main »
R.tournerOs(api, "coude", 0, 0, 90);
sortie.plie = sommet(12);
R.tournerOs(api, "coude", 0, 0, 90);                     // RELATIF au repos : deux fois 90 restent 90
sortie.encore = sommet(12);
R.remettreRepos(api);
sortie.repos = sommet(12);
sortie.inconnu = R.tournerOs(api, "absent", 0, 0, 10);
""")
    assert o["avant"] == [-0.25, 3.0, -0.25]
    # le coude (y = 1) tourne de 90° autour de z : le sommet (−0,25 ; 3) passe à (−2 ; 0,75) — x = −(3 − 1), y = 1 − 0,25
    assert o["plie"] == [-2.0, 0.75, -0.25], o["plie"]
    assert o["encore"] == o["plie"] and o["repos"] == o["avant"] and o["inconnu"] is False


def test_les_clips_se_jouent_a_la_VITESSE_demandee_avec_UNE_seule_boucle_EXECUTEE():
    o = _rig("""
sortie.clips = R.lecteurClips(api);
R.lecteurClips(api);                                     // un second rendu du panneau
sortie.raf = RAF;
R.jouerClip(api, 0, 2);                                  // « plier » à ×2
api._mixeur.update(0.5);                                 // 0,5 s réelle = 1 s de clip : le coude à 60°
const q = os("coude").quaternion;
sortie.angle = Math.round(2 * Math.atan2(q.z, q.w) * 180 / Math.PI * 1000) / 1000;
R.arreterClip(api);
sortie.horsBorne = R.jouerClip(api, 9, 1);
""")
    assert [(c["nom"], c["duree"]) for c in o["clips"]] == [("plier", 2), ("tourner", 1)]
    assert o["raf"] == 1, "une seule boucle d'animation pour le module, pas une par rendu du panneau"
    assert abs(o["angle"] - 60.0) < 1e-3 and o["horsBorne"] is False


# ── la page ──────────────────────────────────────────────────────────────────
def test_le_module_rig_n_ecrit_RIEN_et_ne_parle_a_aucune_route():
    js = _code("lib3d/rig.js")
    assert "fetch" not in js and "/api/" not in js and "jpost" not in js


def test_le_panneau_rig_echappe_les_NOMS_du_fichier_et_se_range_au_chargement():
    f = _fonction_etabli_async("rendreRig")
    assert "/api/etabli/rig?job=" in f and "numero !== RIG.rendu" in f
    assert "${esc(o.nom)}" in f and "${o.nom}" not in f and "${esc(c.nom)}" in f
    assert "04 · squelette" in f and "05 · animation" in f, "les vrais libellés du 3D Studio"
    js = _lire("etabli/etabli.js")
    assert "const RIG = { os: null, rendu: 0 };" in js
    assert "  rangerRig(S.vueA);\n  RIG.os = null;" in js.replace("\r\n", "\n")
    assert "  rendreFiche();\n  rendreRig();" in js.replace("\r\n", "\n")


def test_la_route_rig_dit_le_squelette_du_fichier_fabrique():
    from fastapi.testclient import TestClient
    from app.config import settings
    from app.main import app
    from fabrique_rig import glb_rigge
    d = settings.outputs_path / "assets3d" / "job_rig"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(glb_rigge())
    with TestClient(app) as c:
        r = c.get("/api/etabli/rig?job=job_rig&version=1").json()
    assert r["a_squelette"] is True and [o["nom"] for o in r["os"]] == ["racine", "coude", "main"]
    assert r["os"][0]["parent"] == 1 and [c["nom"] for c in r["clips"]] == ["plier", "tourner"]



# ── D. les cibles moteur, et l'export ────────────────────────────────────────
def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _job(nom: str, data: bytes = None) -> pathlib.Path:
    from app.config import settings
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(data or _cube())
    return d


def test_les_quatre_cibles_livrent_du_GLTF_standard_sans_rotation_precuite():
    """Blender, Unreal, Godot et glTFast convertissent EUX-MÊMES : pré-cuire l'axe tournerait le modèle deux fois."""
    from app.services import mesh_export
    assert set(mesh_export.CIBLES) == {"blender", "godot", "unreal", "unity"}
    for nom, c in mesh_export.CIBLES.items():
        assert c["format"] == "glb" and c["axe_haut"] == "Y" and c["echelle"] == 1.0, nom
    assert "glTFast" in mesh_export.CIBLES["unity"]["note"]


def test_exporter_ecrit_le_fichier_ET_sa_fiche_par_cible_et_laisse_la_source_intacte():
    from app.services import mesh_export
    d = _job("job_exp")
    avant = (d / "model.glb").read_bytes()
    g = mesh_export.exporter("job_exp", 1, "godot")
    u = mesh_export.exporter("job_exp", 1, "unity")
    for r, mot in ((g, "Godot"), (u, "Unity")):
        sortie = pathlib.Path(r["chemin"])
        assert sortie.is_file() and sortie.suffix == ".glb" and sortie.parent == d / "exports"
        assert mot in pathlib.Path(r["fiche"]).read_text("utf-8")
    assert g["fiche"] != u["fiche"], "une fiche PAR cible : la seconde n'écrase pas la première"
    assert (d / "model.glb").read_bytes() == avant
    assert mesh_export.chemin_export("job_exp", 1, "godot") == pathlib.Path(g["chemin"])


def test_une_surcharge_d_axe_et_d_echelle_passe_par_mesh_edit_reparer_et_se_dit():
    from app.services import mesh_export, print3d
    _job("job_axe")
    r = mesh_export.exporter("job_axe", 1, "unreal", axe_haut="Z", echelle=100.0)
    (x0, x1), _y, _z = print3d.bbox(print3d.lire_glb_triangles(pathlib.Path(r["chemin"]).read_bytes()))
    assert abs(x1 - 100.0) < 1e-3 and abs(x0 + 100.0) < 1e-3       # le cube d'arête 2 fait 200 au facteur 100
    assert "Surcharge" in pathlib.Path(r["fiche"]).read_text("utf-8")


def test_exporter_refuse_ce_qui_n_a_pas_de_sens():
    from app.services import mesh_export
    _job("job_ko")
    for args, mot in ((("job_ko", 1, "cryengine"), "cible inconnue"), (("job_ko", 1, "godot", "W"), "axe"),
                      (("job_ko", 1, "godot", None, 0.0), "échelle"), (("job_ko", 1, "godot", None, -2.0), "échelle")):
        with pytest.raises(ValueError, match=mot):
            mesh_export.exporter(*args[:3], axe_haut=args[3] if len(args) > 3 else None,
                                 echelle=args[4] if len(args) > 4 else None)
    with pytest.raises(FileNotFoundError):
        mesh_export.exporter("job_ko", 5, "godot")


def test_le_fbx_n_est_propose_que_s_il_existe_deja():
    from app.services import mesh_export
    d = _job("job_fbx")
    assert mesh_export.fbx_disponible("job_fbx") is False
    (d / "model.fbx").write_bytes(b"faux fbx du banc")
    assert mesh_export.fbx_disponible("job_fbx") is True


# ── E. ouvrir et déposer : le CHEMIN est celui du serveur, jamais celui de la page ──
def test_blender_s_ouvre_sur_le_fichier_EXPORTE_avec_un_chemin_qui_ne_peut_pas_s_echapper(monkeypatch):
    """Le plan prenait le chemin du CORPS et le collait dans du Python (`--python-expr`) : une apostrophe dans le
    chemin et la page faisait exécuter ce qu'elle voulait à Blender. Le chemin est recalculé ici, et passé par
    repr() — qui échappe tout."""
    from app.services import mesh_export
    _job("job_o'ouvrir")
    mesh_export.exporter("job_o'ouvrir", 1, "blender")
    vus = {}
    monkeypatch.setattr(mesh_export, "_lancer", lambda argv: vus.setdefault("argv", argv))
    monkeypatch.setenv("BLENDER_PATH", "C:/faux/blender.exe")
    r = mesh_export.ouvrir("job_o'ouvrir", 1, "blender")
    argv = vus["argv"]
    assert argv[0] == "C:/faux/blender.exe" and argv[1] == "--python-expr" and r["geste"] == "fichier"
    attendu = str(mesh_export.chemin_export("job_o'ouvrir", 1, "blender"))
    assert f"bpy.ops.import_scene.gltf(filepath={attendu!r})" in argv[2]
    compile(argv[2], "<python-expr>", "exec")                     # du Python valide, apostrophe comprise


def test_les_trois_autres_ouvrent_le_PROJET_avec_la_ligne_de_commande_de_leur_editeur(monkeypatch, tmp_path):
    from app.services import mesh_export
    _job("job_proj")
    vus = []
    monkeypatch.setattr(mesh_export, "_lancer", lambda argv: vus.append(argv))
    (tmp_path / "u" / "Assets").mkdir(parents=True)
    (tmp_path / "g").mkdir()
    (tmp_path / "g" / "project.godot").write_text("", "utf-8")
    (tmp_path / "e").mkdir()
    (tmp_path / "e" / "Jeu.uproject").write_text("{}", "utf-8")
    for c, exe, projet in (("unity", "U.exe", "u"), ("godot", "G.exe", "g"), ("unreal", "E.exe", "e")):
        monkeypatch.setenv(mesh_export.EXE_ENV[c], exe)
        monkeypatch.setenv(mesh_export.PROJET_ENV[c], str(tmp_path / projet))
        assert mesh_export.geste_ouvrir(c) == "projet"
        assert mesh_export.ouvrir("job_proj", 1, c)["geste"] == "projet"
    assert vus[0] == ["U.exe", "-projectPath", str(tmp_path / "u")]
    assert vus[1] == ["G.exe", "--editor", "--path", str(tmp_path / "g")]
    assert vus[2] == ["E.exe", str(tmp_path / "e" / "Jeu.uproject")]


def test_ouvrir_et_deposer_refusent_en_NOMMANT_la_variable(monkeypatch, tmp_path):
    from app.services import mesh_export
    _job("job_var")
    monkeypatch.setattr(mesh_export, "_lancer", lambda argv: None)
    monkeypatch.delenv("BLENDER_PATH", raising=False)
    with pytest.raises(RuntimeError, match="BLENDER_PATH"):
        mesh_export.ouvrir("job_var", 1, "blender")
    monkeypatch.setenv("BLENDER_PATH", "B.exe")
    with pytest.raises(RuntimeError, match="Préparer"):
        mesh_export.ouvrir("job_var", 1, "blender")               # rien d'exporté pour cette cible
    monkeypatch.delenv("GODOT_PROJECT_DIR", raising=False)
    mesh_export.exporter("job_var", 1, "godot")
    with pytest.raises(RuntimeError, match="GODOT_PROJECT_DIR"):
        mesh_export.deposer("job_var", 1, "godot")
    monkeypatch.setenv("GODOT_PROJECT_DIR", str(tmp_path))              # pas de project.godot : pas un projet
    with pytest.raises(RuntimeError, match="project.godot"):
        mesh_export.deposer("job_var", 1, "godot")


def test_deposer_va_dans_le_BON_sous_dossier_du_projet_et_sonde_la_visibilite(monkeypatch, tmp_path):
    """L'incident MSIX : une écriture peut sembler réussir en partant dans un overlay invisible."""
    from app.services import mesh_export
    _job("job_dep")
    mesh_export.exporter("job_dep", 1, "unity")
    (tmp_path / "Assets").mkdir()
    monkeypatch.setenv("UNITY_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(mesh_export, "_sonder", lambda d: False)
    with pytest.raises(RuntimeError, match="invisible"):
        mesh_export.deposer("job_dep", 1, "unity")
    monkeypatch.setattr(mesh_export, "_sonder", lambda d: True)
    out = mesh_export.deposer("job_dep", 1, "unity")
    p = pathlib.Path(out["chemin"])
    assert p.is_file() and p.parent == tmp_path / "Assets" / "Deepotus"
    assert (p.parent / p.name.replace(".glb", ".import.md")).is_file()
    # sans glTFast, Unity laisse le .glb inerte : le dépôt le DIT ; avec le paquet au manifeste, il se tait
    assert "com.unity.cloud.gltfast" in out["avertissement"]
    (tmp_path / "Packages").mkdir()
    (tmp_path / "Packages" / "manifest.json").write_text('{"dependencies": {"com.unity.cloud.gltfast": "6.0.0"}}', "utf-8")
    assert mesh_export.deposer("job_dep", 1, "unity")["avertissement"] is None


# ── F. les routes et le panneau ──────────────────────────────────────────────
def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_les_routes_export_cibles_fichier_et_leurs_refus(monkeypatch):
    from app.services import mesh_export
    _job("job_route")
    with _client() as c:
        cib = c.get("/api/etabli/cibles").json()["cibles"]
        assert cib["blender"]["geste_ouvrir"] == "fichier" and cib["godot"]["geste_ouvrir"] == "projet"
        assert cib["blender"]["variable_exe"] == "BLENDER_PATH" and cib["unity"]["variable_projet"] == "UNITY_PROJECT_DIR"
        r = c.post("/api/etabli/export", json={"job": "job_route", "version": 1, "cible": "godot"})
        assert r.status_code == 200, r.text
        j = r.json()
        assert "chemin" not in j or pathlib.Path(j["chemin"]).is_file()
        f = c.get(j["url"])
        assert f.status_code == 200 and f.content[:4] == b"glTF"
        # `..%2F` : décodé, il tombe sur la page d'accueil de l'application (le piège connu du catch-all) — ce qui
        # compte est qu'AUCUN fichier du job ne sorte par là
        t = c.get("/api/assets/3d/job_route/export/..%2Fmodel.glb")
        assert t.content[:4] != b"glTF" and "glb" not in t.headers.get("content-type", "")
        assert c.get("/api/assets/3d/job_route/export/absent.glb").status_code == 404
        for corps in ({"cible": "cryengine"}, {"cible": "godot", "version": "1"}, {"cible": "godot", "echelle": 0},
                      {"cible": "godot", "axe_haut": "W"}):
            assert c.post("/api/etabli/export", json={"job": "job_route", "version": 1, **corps}).status_code == 400, corps
        assert c.post("/api/etabli/export", json={"job": "..", "version": 1, "cible": "godot"}).status_code == 400
        for route in ("ouvrir", "deposer"):          # une cible inconnue est un 400 nommé, jamais un 500
            r = c.post(f"/api/etabli/{route}", json={"job": "job_route", "version": 1, "cible": "cryengine"})
            assert r.status_code == 400 and "cryengine" in r.json()["detail"], (route, r.status_code)
        monkeypatch.setattr(mesh_export, "_lancer", lambda argv: None)
        monkeypatch.delenv("UNITY_PATH", raising=False)
        r = c.post("/api/etabli/ouvrir", json={"job": "job_route", "version": 1, "cible": "unity"})
        assert r.status_code == 409 and "UNITY_PATH" in r.json()["detail"]
        # le corps ne transporte AUCUN chemin : un `chemin` envoyé est ignoré, jamais lu
        monkeypatch.setenv("GODOT_PATH", "G.exe")
        vus = []
        monkeypatch.setattr(mesh_export, "_lancer", lambda argv: vus.append(argv))
        r = c.post("/api/etabli/ouvrir", json={"job": "job_route", "version": 1, "cible": "godot",
                                              "chemin": "C:/Windows/System32/calc.exe"})
        assert all("calc" not in str(a) for a in (vus[0] if vus else []))


def test_un_refus_du_serveur_se_lit_en_PHRASE_et_non_en_JSON_EXECUTEE():
    """Vu en preuve 8799 le 06/10 : la barre affichait {"detail":"BLENDER_PATH n'est pas renseigné…"} — et c'était
    vrai de tous les refus de l'Établi."""
    js = _lire("etabli/etabli.js")
    i = js.index("\nfunction refusDe(")
    corps = js[i:js.index("\n}\n", i) + 2]
    src = corps + """
console.log(JSON.stringify([refusDe('{"detail":"BLENDER_PATH absent"}'), refusDe("pas du json"),
                            refusDe('{"detail":[{"loc":["body"],"msg":"x"}]}')]));"""
    r = subprocess.run(["node", "-e", src], capture_output=True, timeout=30)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    o = json.loads(r.stdout.decode("utf-8"))
    assert o[0] == "BLENDER_PATH absent" and o[1] == "pas du json" and o[2].startswith('{"detail"')
    assert "throw new Error(refusDe(t) ||" in js


def test_le_panneau_export_montre_les_quatre_cibles_et_dit_la_verite_sur_le_fbx():
    f = _fonction_etabli_async("rendreExportMoteurs")
    assert '"/api/etabli/cibles"' in f and '"/api/etabli/export"' in f
    assert "chemin" not in f.split('"/api/etabli/ouvrir"', 1)[1].split(")", 1)[0] if '"/api/etabli/ouvrir"' in f else True
    assert "esc(c.nom)" in f and "esc(c.note)" in f
    js = _lire("etabli/etabli.js")
    assert "FBX" in js and "crédit" in js
    assert "rendreExportMoteurs();" in js

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
