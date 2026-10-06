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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
