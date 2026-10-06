# -*- coding: utf-8 -*-
"""T105 C (plan-moteurs-3d T5, P4) — la conversion et l'import dans l'Atelier fal de /studio3d : fal.js IMPORTÉ sous
node (faux DOM ; fetch, URL, FormData et dialogue en doublures qui notent tout). Vérifié : les formats viennent du
SERVEUR (locaux puis Meshy avec leur prix) et la raison « pas local » est dite ; un format local se télécharge sous
le nom que le serveur donne, avec la taille en mm pour STL/3MF seulement ; un refus est remonté ; un format Meshy se
CONFIRME (refus = aucun POST) puis part en file ; les fichiers déjà convertis sont listés en liens ; un import crée un
job, le sélectionne et le dit. Les éléments lus existent dans index.html.
Run (depuis backend/) : & $PY tests/test_studio3d_conversion.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
S3D = RACINE / "frontend" / "studio3d"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzcvs_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FAL = (S3D / "fal.js").read_text(encoding="utf-8")
HTML = (S3D / "index.html").read_text(encoding="utf-8")
ids = sorted(set(re.findall(r'\$\("#([A-Za-z]+)"\)', FAL)) | {"cvEtat"})
check("H1 chaque élément lu par fal.js existe dans index.html", not [i for i in ids if f'id="{i}"' not in HTML],
      str([i for i in ids if f'id="{i}"' not in HTML]))
check("H2 aucun format codé en dur dans fal.js", '"fbx"' not in FAL and "'fbx'" not in FAL and '"usdz"' not in FAL)
check("H3 l'import n'accepte que les formats lus en local", 'accept=".obj,.stl,.gltf,.glb"' in HTML)

HARNAIS = r"""
const EL = {};
function el(id){ if(!EL[id]) EL[id] = {id, textContent:"", innerHTML:"", value:"", disabled:false, title:"", dataset:{},
  _cls:new Set(), classList:{ add(c){EL[id]._cls.add(c)}, remove(c){EL[id]._cls.delete(c)}, toggle(c,on){ if(on) EL[id]._cls.add(c); else EL[id]._cls.delete(c)} },
  querySelector(){ return null }, querySelectorAll(){ return [] }, appendChild(){}, addEventListener(){}, selectedOptions:[] };
  return EL[id] }
const DL = [];
globalThis.document = { querySelector(s){ return el(s.replace(/^#/, "")) },
  createElement(){ const a = {setAttribute(){}, removeAttribute(){}, click(){ DL.push({href:a.href, download:a.download}) }}; return a } };
globalThis.URL = { createObjectURL(b){ return "blob:" + b.n }, revokeObjectURL(){} };
globalThis.FormData = class { constructor(){ this.e = [] } append(k, v){ this.e.push([k, v.name]) } };
globalThis.setTimeout = () => 0; globalThis.setInterval = (f) => { globalThis.TIC = f; return 1 }; globalThis.clearInterval = () => {};
const CALLS = [];
const REP = {};
globalThis.fetch = async (u, o) => { o = o || {};
  CALLS.push({u, m: o.method || "GET", b: o.body && typeof o.body === "string" ? JSON.parse(o.body) : (o.body && o.body.e) || null});
  const r = REP[(o.method || "GET") + " " + u] || {st: 404, js: {detail: "inconnu " + u}};
  return { ok: r.st < 400, status: r.st, json: async () => r.js, blob: async () => ({n: r.n || 0}),
           headers: { get: (k) => (r.h || {})[k.toLowerCase()] || null } }; };
const F = await import(process.argv[2]);
const CAPS = {local_export:["obj","stl","3mf","gltf"], local_import:["obj","stl","glb","gltf"], meshy:["fbx","usdz","blend"],
  credits_meshy:1, pourquoi_pas_local:"gltfpack n'écrit que gltf et glb.", convertis:["model.fbx"]};
const OUT = {};
REP["GET /api/etabli/sources"] = {st:200, js:{jobs:[{source:"assets3d", id:"perso", nom:"perso", created_at:"2026-10-05", etapes:[{version:1}]},
  {source:"assets3d", id:"import_statue_ab12", nom:"statue", created_at:"2026-10-01", etapes:[{version:1}]}]}};
REP["GET /api/assets/3d/perso/convert"] = {st:200, js:CAPS};
REP["GET /api/assets/3d/import_statue_ab12/convert"] = {st:200, js:{...CAPS, convertis:[]}};
await F.chargerJobs();
OUT.options = EL.cvFmt.innerHTML; OUT.note = EL.cvNote.textContent; OUT.convertis = EL.cvConvertis.innerHTML; OUT.go = EL.cvGo.disabled;
// local : STL avec taille, nom du serveur
EL.cvFmt.value = "stl"; el("cvMm").value = "120";
REP["POST /api/assets/3d/perso/convert"] = {st:200, n:777, h:{"content-disposition":'attachment; filename="perso.stl"'}};
CALLS.length = 0; await F.convertir(async () => true, () => {});
OUT.stl = {post: CALLS.filter(c => c.m === "POST").map(c => JSON.stringify(c.b)), dl: DL.slice(-1)[0], etat: EL.cvEtat.textContent};
// local : OBJ — la taille n'est PAS envoyée
EL.cvFmt.value = "obj";
REP["POST /api/assets/3d/perso/convert"] = {st:200, n:888, h:{"content-disposition":'attachment; filename="perso_obj.zip"'}};
CALLS.length = 0; await F.convertir(async () => true, () => {});
OUT.obj = {post: CALLS.filter(c => c.m === "POST").map(c => JSON.stringify(c.b)), dl: DL.slice(-1)[0]};
// local : refus remonté
REP["POST /api/assets/3d/perso/convert"] = {st:400, js:{detail:"cible_mm : entre 0,1 et 10 000 mm"}};
EL.cvFmt.value = "stl"; let err = null;
try { await F.convertir(async () => true, () => {}) } catch (e) { err = String(e.message) }
OUT.refus = err;
// Meshy : confirmation refusée = aucun POST ; acceptée = file
EL.cvFmt.value = "fbx"; let msg = null; CALLS.length = 0;
await F.convertir(async (m, o) => { msg = [m, o.ok]; return false }, () => {});
OUT.meshyRefus = {posts: CALLS.filter(c => c.m === "POST").length, msg};
REP["POST /api/assets/3d/perso/convert"] = {st:200, js:{job_id:"jc1", status:"queued"}};
REP["GET /api/jobs/jc1"] = {st:200, js:{status:"done", current_step:"Complete", progress:100}};
CALLS.length = 0; await F.convertir(async () => true, () => {});
OUT.meshyPost = CALLS.filter(c => c.m === "POST").map(c => JSON.stringify(c.b));
await globalThis.TIC(); await new Promise(r => setImmediate(r));
OUT.meshyFin = EL.cvEtat.textContent;
// import : crée un job, le sélectionne, le dit
REP["POST /api/assets/3d/importer"] = {st:200, js:{ok:true, job:"import_statue_ab12", triangles:1234}};
let t = null; CALLS.length = 0;
await F.importer({name:"statue.stl"}, (m) => { t = m });
OUT.import = {post: CALLS.filter(c => c.m === "POST").map(c => c.u + " " + JSON.stringify(c.b)), job: F.F.job, sel: EL.falJob.value, toast: t, etat: EL.cvEtat.textContent};
REP["POST /api/assets/3d/importer"] = {st:400, js:{detail:"import fbx impossible en local"}};
let e2 = null; try { await F.importer({name:"x.fbx"}, () => {}) } catch (e) { e2 = String(e.message) }
OUT.importRefus = e2;
console.log(JSON.stringify(OUT));
"""
p = _TMP / "cv.mjs"
p.write_text(HARNAIS, encoding="utf-8")
r = subprocess.run(["node", str(p), (S3D / "fal.js").as_uri()], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-500:] + r.stderr[-900:]}
check("U0 fal.js s'importe et s'exécute sous node", "options" in o, str(o)[:900])
if "options" in o:
    check("U1 les formats du SERVEUR : locaux « gratuit » d'abord, puis Meshy avec leur prix",
          o["options"].index('value="obj"') < o["options"].index('value="fbx"') and "stl · local, gratuit" in o["options"]
          and "blend · Meshy, 1 cr" in o["options"], o["options"][:300])
    check("U2 la raison du « pas local » est dite ; le bouton est actif", o["note"].startswith("gltfpack") and o["go"] is False, o["note"])
    check("U3 les fichiers déjà convertis sont des liens de téléchargement",
          'href="/api/assets/3d/perso/convert/model.fbx" download' in o["convertis"], o["convertis"])
    check("U4 STL : la taille en mm part, le fichier prend le nom du SERVEUR",
          o["stl"]["post"] == ['{"format":"stl","cible_mm":120}'] and o["stl"]["dl"] == {"href": "blob:777", "download": "perso.stl"}
          and o["stl"]["etat"] == "stl téléchargé", str(o["stl"]))
    check("U5 OBJ : la taille n'est pas envoyée (elle ne vaut que pour l'impression)",
          o["obj"]["post"] == ['{"format":"obj","cible_mm":null}'] and o["obj"]["dl"]["download"] == "perso_obj.zip", str(o["obj"]))
    check("U6 un refus local est remonté tel quel", o["refus"] == "cible_mm : entre 0,1 et 10 000 mm", str(o["refus"]))
    mr = o["meshyRefus"]
    check("U7 Meshy : confirmation refusée = AUCUN POST, le message dit le crédit et la raison",
          mr["posts"] == 0 and "1 crédit" in mr["msg"][0] and "gltfpack" in mr["msg"][0] and mr["msg"][1] == "Payer 1 cr", str(mr))
    check("U8 Meshy confirmé : POST du format, suivi jusqu'à « prêt »", o["meshyPost"] == ['{"format":"fbx"}'] and o["meshyFin"] == "fbx prêt",
          f"{o['meshyPost']} {o['meshyFin']}")
    im = o["import"]
    check("U9 import : le fichier part en multipart, le job neuf est SÉLECTIONNÉ et dit",
          im["post"] == ['/api/assets/3d/importer [["file","statue.stl"]]'] and im["job"] == "import_statue_ab12"
          and im["sel"] == "import_statue_ab12" and "import_statue_ab12" in im["toast"] and "1 234 tris" in im["etat"].replace(" ", " "),
          str(im))
    check("U10 un import refusé remonte la raison", o["importRefus"] == "import fbx impossible en local", str(o["importRefus"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
