# -*- coding: utf-8 -*-
"""T107 (plan-moteurs-3d T11, D5) — « depuis des photos » dans /studio3d (vues.js sous node, faux DOM, fetch en
doublure). Vérifié : chaque élément lu existe dans index.html ; les photos du téléphone (source « mobile ») viennent
EN TÊTE des listes et se reconnaissent ; la face est exigée (sinon aucun POST, la raison dite) ; le POST porte les
vues choisies, le moteur et le détourage ; gratuit, donc AUCUN dialogue ; un sélecteur laissé vide n'envoie rien ;
recharger garde les choix.
Run (depuis backend/) : & $PY tests/test_studio3d_photos.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
S3D = RACINE / "frontend" / "studio3d"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzphotos_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


VJS = (S3D / "vues.js").read_text(encoding="utf-8")
HTML = (S3D / "index.html").read_text(encoding="utf-8")
ids = sorted(set(re.findall(r'\$\("#([A-Za-z]+)"\)', VJS)))
check(f"H1 les {len(ids)} éléments lus par vues.js existent dans index.html",
      all(f'id="{i}"' in HTML for i in ids), str([i for i in ids if f'id="{i}"' not in HTML]))
check("H2 les quatre sélecteurs de photos, le détourage et le bouton sont dans la page",
      all(f'id="{i}"' in HTML for i in ("photoFront", "photoBack", "photoLeft", "photoRight", "photoDetourer", "btnVuesPhotos")))

HARNAIS = r"""
const EL = {};
function el(id){ if(!EL[id]) EL[id] = {id, textContent:"", innerHTML:"", value:"", checked:false, disabled:false, dataset:{},
  classList:{ add(){}, remove(){}, toggle(){} }, addEventListener(){}, closest(){ return null } }; return EL[id] }
globalThis.document = { querySelector(s){ return el(s.replace(/^#/, "")) } };
const CALLS = [];
globalThis.fetch = async (u, o) => { o = o || {}; CALLS.push({u, m: o.method || "GET", b: o.body ? JSON.parse(o.body) : null});
  const rep = (st, js) => ({ ok: st < 400, status: st, json: async () => js });
  if (u === "/api/images") return rep(200, {images: [{filename: "plan.png", source: "atelier"},
     {filename: "IMG_2001.jpg", source: "mobile"}, {filename: "IMG_2002.jpg", source: "mobile"}]});
  if (u === "/api/assets3d/engines") return rep(200, {default: "tripo", engines: [{id: "tripo", label: "Tripo", available: true, usd_texture: 0.3}]});
  if (u === "/api/assets/3d/views" && (o.method || "GET") === "GET") return rep(200, {jeux: []});
  if (u === "/api/bible/entities") return rep(200, {entities: []});
  if (u === "/api/cost/estimate") return rep(200, {total_usd: 0.12});
  if (u === "/api/assets/3d/views/photos") return rep(200, {job_id: "jp", job: "ph1", status: "queued", vues: ["front", "left"]});
  return rep(404, {detail: u}); };
globalThis.setInterval = () => 1; globalThis.clearInterval = () => {};
const M = await import(process.argv[2]);
const OUT = {};
await M.charger();
OUT.front = EL.photoFront.innerHTML; OUT.back = EL.photoBack.innerHTML;
let t = null, dlg = 0; const conf = async () => { dlg++; return true; };
CALLS.length = 0;
await M.depuisPhotos(conf, (m) => { t = m; });
OUT.sansFace = {posts: CALLS.filter(c => c.m === "POST" && c.u !== "/api/cost/estimate").length, toast: t};
el("photoFront").value = "IMG_2001.jpg"; el("photoLeft").value = "IMG_2002.jpg"; el("photoBack").value = ""; el("photoRight").value = "";
el("photoDetourer").checked = true; el("vuesMoteur").value = "tripo";
CALLS.length = 0; t = null;
await M.depuisPhotos(conf, (m) => { t = m; });
OUT.lance = {posts: CALLS.filter(c => c.m === "POST").map(c => c.u + " " + JSON.stringify(c.b)), dlg, toast: t};
await M.charger();
OUT.garde = EL.photoFront.innerHTML;
console.log(JSON.stringify(OUT));
"""
p = _TMP / "h.mjs"
p.write_text(HARNAIS, encoding="utf-8")
r = subprocess.run(["node", str(p), (S3D / "vues.js").as_uri()], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-500:] + r.stderr[-900:]}
check("U0 vues.js s'importe et s'exécute sous node", "erreur" not in o and "front" in o, str(o)[:900])
if "front" in o:
    f = o["front"]
    check("U1 les photos du téléphone viennent en tête et se reconnaissent (📱)",
          "IMG_2001.jpg" in f and "plan.png" in f and f.index("IMG_2001.jpg") < f.index("plan.png") and "📱" in f, f)
    check("U2 les vues facultatives ont une option vide « — » (aucune vue)", '<option value="">—</option>' in o["back"], o["back"][:200])
    sf = o["sansFace"]
    check("U3 sans face : aucun POST, la raison dite", sf["posts"] == 0 and "face" in (sf["toast"] or ""), str(sf))
    l = o["lance"]
    check("U4 lancé : UN POST avec les vues CHOISIES seulement (vides écartées), le moteur et le détourage",
          l["posts"] == ['/api/assets/3d/views/photos {"vues":{"front":"IMG_2001.jpg","left":"IMG_2002.jpg"},"engine":"tripo","detourer":true}'],
          str(l["posts"]))
    check("U5 gratuit : AUCUN dialogue de paiement, le toast le dit", l["dlg"] == 0 and "gratuit" in (l["toast"] or ""), str(l))
    check("U6 recharger garde la photo choisie pour la face", '<option value="IMG_2001.jpg" selected>' in o["garde"], o["garde"][:300])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
