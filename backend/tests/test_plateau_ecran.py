# -*- coding: utf-8 -*-
"""t127 T5-T8 (07/10/2026) — l'écran du Plateau 3D (/plateau) et son pont avec l'Atelier.

  [1] la page : import map identique à /assets/three/importmap.json, module plateau.js, chaque `#id` lu par le
      script existe dans index.html, aucun dialogue natif, le canevas PARTAGÉ /lib3d/viewer.js (décision du 07/10) ;
  [2] calc.js sous node CONTRE scene3d.py (Python) sur des cas TIRÉS (graine fixe) : focale ↔ champ, orbite →
      position, position → orbite (aller-retour, θ prolongé au-delà de 180°), interpolation de keyframes et easing —
      l'écran et le serveur doivent calculer la même chose ; les presets produisent des keyframes que le serveur
      accepte et nomme comme attendu ;
  [3] la letterbox (cadreDans) ;
  [4] le total de triangles affiché : trianglesProxy == les géométries three r185 RÉELLES de l'écran (node importe
      three.module.min.js) ;
  [5] le montage /plateau dans l'app et le bouton 🎥 de la carte de plan dans l'Atelier.
Run : & $PY tests/test_plateau_ecran.py   (depuis backend/)
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
RACINE = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    try:
        return (RACINE / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
    except OSError:
        return ""


HTML, JS, CALC, CSS = (lire("frontend/plateau/" + n) for n in ("index.html", "plateau.js", "calc.js", "plateau.css"))
check("x0_fichiers_lus", all(len(t) > 500 for t in (HTML, JS, CALC, CSS)), [len(t) for t in (HTML, JS, CALC, CSS)])

print("\n[1] la page")
m = re.search(r'<script type="importmap">\s*(\{.*?\})\s*</script>', HTML, re.S)
try:
    carte = json.loads(m.group(1)) if m else None
    ref = json.loads(lire("frontend/dist/assets/three/importmap.json"))
except ValueError:
    carte, ref = None, {}
check("1a_import_map_en_ligne_identique_a_celle_du_dossier_vendorise", carte is not None and carte == ref, (carte, ref))
check("1b_module_et_canevas_partage", '<script type="module" src="plateau.js"></script>' in HTML
      and 'from "/lib3d/viewer.js"' in JS and "creerCanevas(" in JS and "model-viewer.min.js" not in JS + HTML and "<model-viewer" not in HTML)
ids_js = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', JS))
ids_html = set(re.findall(r'id="([A-Za-z0-9_-]+)"', HTML)) | set(re.findall(r'id=\\?"([A-Za-z0-9_-]+)\\?"', JS))
manque = sorted(ids_js - ids_html)
check("1c_chaque_id_lu_par_le_script_existe", len(ids_js) > 20 and not manque, manque)
check("1d_aucun_dialogue_natif", not re.search(r"\b(alert|confirm|prompt)\(", JS + CALC))
check("1e_les_mesures_viennent_du_serveur",
      all(f"/${{P.scene.id}}/{r}" in JS for r in ("mesure", "mouvement", "compose", "capture", "vers-plan")))
check("1f_la_feuille_vient_des_jetons_du_theme", CSS.startswith("/*") and '@import url("/shared/deepotus.tokens.css");' in CSS
      and "var(--accent)" in CSS)

print("\n[2] calc.js contre scene3d.py")
from app.services import scene3d as S  # noqa: E402
random.seed(7102026)
CAS_F = [round(random.uniform(14, 200), 3) for _ in range(12)]
CAS_O = [([round(random.uniform(-400, 400), 3), round(random.uniform(1, 179), 3), round(random.uniform(0.3, 40), 3)],
          [round(random.uniform(-5, 5), 3) for _ in range(3)]) for _ in range(30)]
CAS_K = []
for _ in range(25):
    n = random.randint(1, 4)
    ts = sorted(random.sample(range(0, 120), n))
    kfs = [{"t": t / 10, "orbit": [random.uniform(-200, 200), random.uniform(10, 170), random.uniform(0.5, 20)],
            "target": [random.uniform(-3, 3) for _ in range(3)], "fov": random.uniform(8, 90),
            "easing": random.choice(list(S.EASINGS))} for t in ts]
    CAS_K.append((kfs, [random.uniform(-1, 13) for _ in range(5)]))
PROBE = """
import * as C from "__CALC__";
const F = __F__, O = __O__, K = __K__, out = {f: [], p: [], o: [], k: [], cadre: [], presets: {}};
for (const f of F) out.f.push([C.fovDeFocale(f, 14.2), C.focaleDeFov(C.fovDeFocale(f, 14.2), 14.2)]);
for (const [orb, tgt] of O) { const p = C.positionCamera(orb, tgt); out.p.push(p); out.o.push(C.orbitDeCamera(p, tgt, orb[0])); }
for (const [kfs, ts] of K) out.k.push(ts.map((t) => C.interpoler(kfs, t)));
out.cadre = [C.cadreDans(1000, 500, 16/9), C.cadreDans(1000, 500, 9/16), C.cadreDans(400, 900, 1), C.cadreDans(0, 0, 2.39)];
const cam = {orbit: [10, 90, 6], target: [0, 0.85, 0], fov: 22.94};
for (const n of ["travelling", "orbite90", "grue", "fixe"]) out.presets[n] = C.preset(n, cam, 4);
try { C.preset("zz", cam, 4); out.presetInconnu = "accepte"; } catch { out.presetInconnu = "refuse"; }
out.tris = {boite: C.trianglesProxy("boite"), sphere: C.trianglesProxy("sphere"), cylindre: C.trianglesProxy("cylindre"), capsule: C.trianglesProxy("capsule")};
console.log(JSON.stringify(out));
"""
D = {}
if NODE:
    tmp = Path(tempfile.mkdtemp(prefix="dzplat_"))
    f = tmp / "probe.mjs"
    f.write_text(PROBE.replace("__CALC__", (RACINE / "frontend/plateau/calc.js").as_uri()).replace("__F__", json.dumps(CAS_F))
                 .replace("__O__", json.dumps(CAS_O)).replace("__K__", json.dumps(CAS_K)), encoding="utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    try:
        D = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (r.stderr or r.stdout)[-400:], ")")
    shutil.rmtree(tmp, ignore_errors=True)
check("2a_calc_s_execute_sous_node", bool(D), bool(NODE))
if D:
    check("2b_focale_champ_egaux_a_scene3d",
          all(abs(a - S.fov_de_focale(f, 14.2)) < 1e-9 and abs(b - f) < 1e-9 for f, (a, b) in zip(CAS_F, D["f"])), D["f"][:2])
    check("2c_position_camera_egale_a_scene3d",
          all(max(abs(x - y) for x, y in zip(p, S.position_camera(o, t))) < 1e-9 for (o, t), p in zip(CAS_O, D["p"])))
    check("2d_orbite_relue_aller_retour_theta_prolonge",
          all(max(abs(x - y) for x, y in zip(back, o)) < 1e-6 for (o, _t), back in zip(CAS_O, D["o"])),
          [(o, b) for (o, _t), b in zip(CAS_O, D["o"]) if max(abs(x - y) for x, y in zip(b, o)) >= 1e-6][:2])
    ecarts = []
    for (kfs, ts), res in zip(CAS_K, D["k"]):
        for t, js in zip(ts, res):
            py = S.interpoler(kfs, t)
            e = max(max(abs(a - b) for a, b in zip(js["orbit"], py["orbit"])), max(abs(a - b) for a, b in zip(js["target"], py["target"])),
                    abs(js["fov"] - py["fov"]))
            if e > 1e-9:
                ecarts.append((t, e))
    check("2e_interpolation_et_easing_egaux_a_scene3d_125_points", not ecarts and len(CAS_K) == 25, ecarts[:3])
    SC = {"aspect": "16:9", "instances": [{"role": "sujet", "dims": [0.5, 1.7, 0.4], "transform": {"pos": [0, 0, 0]}}]}
    noms = {n: S.mouvement(SC, S.valider_keyframes(k))["camera_move"] for n, k in D["presets"].items()}
    check("2f_presets_acceptes_par_le_serveur_et_nommes",
          noms == {"travelling": "slow push-in", "orbite90": "static, locked-off", "grue": "crane shot descending",
                   "fixe": "static, locked-off"} and D["presetInconnu"] == "refuse", noms)
    av = S.mouvement(SC, S.valider_keyframes(D["presets"]["orbite90"]))["avertissements"]
    check("2g_orbite_90_hors_vocabulaire_le_dit", any("aucune valeur du vocabulaire" in a for a in av), av)

    print("\n[3] letterbox")
    check("3a_cadre_au_ratio_dans_la_zone",
          D["cadre"][0] == {"w": 889, "h": 500} and D["cadre"][1] == {"w": 281, "h": 500} and D["cadre"][2] == {"w": 400, "h": 400},
          D["cadre"])

print("\n[4] triangles affichés == géométries three réelles")
T = {}
three = RACINE / "frontend/dist/assets/three/three.module.min.js"
if NODE and three.is_file():
    tmp = Path(tempfile.mkdtemp(prefix="dzplat3_"))
    f = tmp / "g.mjs"
    f.write_text(f"""
import * as THREE from "{three.as_uri()}";
const n = (g) => (g.index ? g.index.count : g.attributes.position.count) / 3;
const r = Math.min(0.5, 0.4) / 2;
const rot = [[30, 20, 10], [-45, 90, 0], [10, -120, 75], [0, 0, 90]].map(([a, b, c]) => {{
  const v = new THREE.Vector3(1, 2, 3).applyEuler(new THREE.Euler(a * Math.PI / 180, b * Math.PI / 180, c * Math.PI / 180, "XYZ"));
  return [v.x, v.y, v.z]; }});
console.log(JSON.stringify({{boite: n(new THREE.BoxGeometry(1, 1, 1)), sphere: n(new THREE.SphereGeometry(0.5, 24, 16)),
  cylindre: n(new THREE.CylinderGeometry(0.5, 0.5, 1, 24)), capsule: n(new THREE.CapsuleGeometry(r, 1.7 - 2 * r, 8, 24)), rot}}));
""", encoding="utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    try:
        T = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node three :", (r.stderr or r.stdout)[-400:], ")")
    shutil.rmtree(tmp, ignore_errors=True)
ROTS = T.pop("rot", None) if T else None
check("4a_trianglesProxy_egale_three_r185", bool(T) and D and T == D["tris"], (T, D.get("tris") if D else None))
attendu = [[sum(S._rotation(r)[i][k] * [1, 2, 3][k] for k in range(3)) for i in range(3)]
           for r in ([30, 20, 10], [-45, 90, 0], [10, -120, 75], [0, 0, 90])]
check("4d_rotation_du_serveur_egale_euler_XYZ_de_three",
      bool(ROTS) and all(max(abs(a - b) for a, b in zip(u, v)) < 1e-9 for u, v in zip(ROTS, attendu)), (ROTS, attendu))
check("4b_les_segments_de_l_ecran_sont_ceux_du_calcul",
      "new THREE.SphereGeometry(0.5, 24, 16)" in JS and "new THREE.CylinderGeometry(0.5, 0.5, 1, 24)" in JS
      and "new THREE.CapsuleGeometry(r, Math.max(0.001, h - 2 * r), 8, 24)" in JS)

check("4c_capture_a_taille_fixe_1280_au_ratio_du_cadre", "const CAPTURE_PX = 1280;" in JS and JS.count("const b64 = rendreA(w, h);") == 1
      and "r.setSize(w, h, false);" in JS and 'toDataURL("image/png")' in JS)

print("\n[5] montage et Atelier")
MAIN = lire("backend/app/main.py")
check("5a_plateau_monte_comme_l_etabli_sans_cache",
      'app.mount("/plateau", _PlateauStatic(directory=str(_PLATEAU_DIR), html=True), name="plateau")' in MAIN
      and '@app.get("/plateau", include_in_schema=False)' in MAIN and "no-cache, must-revalidate" in MAIN[MAIN.find("class _PlateauStatic"):][:900])
AT = lire("frontend/atelier/atelier.js")
check("5b_bouton_plateau_sur_la_carte_de_plan",
      AT.count('class="btn ghost act-plateau"') == 1 and AT.count('querySelector(".act-plateau")') == 1
      and AT.count('"/plateau/?shot=" + encodeURIComponent(id)') == 1)
check("5c_le_retour_rouvre_le_chapitre", 'loadChapters(new URLSearchParams(location.search).get("chapter") || undefined)' in AT
      and "/atelier/?chapter=" in JS)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
