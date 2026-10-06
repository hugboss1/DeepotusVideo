# -*- coding: utf-8 -*-
"""T104 (plan-moteurs-3d T2, P1) — l'Atelier fal de /studio3d : le module fal.js est IMPORTÉ sous node (faux DOM,
fetch et dialogue en doublures qui notent tout). Vérifié : chaque élément que fal.js lit existe dans index.html ;
studio3d.js importe le module et le branche (le bouton du moteur fal ouvre l'atelier, le hub reste à un clic) ;
le bouton se grise et DIT pourquoi (clé, approbation, texture) ; le prix est celui du devis du backend ; un tir
payant se CONFIRME (refus = aucun POST) ; le POST porte la taille et les actions cochées.
Témoin positif : la base (fd6cfe8a) n'a pas fal.js.
Run (depuis backend/) : & $PY tests/test_studio3d_atelier_fal.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
S3D = RACINE / "frontend" / "studio3d"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzfal_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "fd6cfe8a:frontend/studio3d/fal.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas l'Atelier fal", r0.returncode != 0)

FAL = (S3D / "fal.js").read_text(encoding="utf-8")
HTML = (S3D / "index.html").read_text(encoding="utf-8")
JS = (S3D / "studio3d.js").read_text(encoding="utf-8")
ids = sorted(set(re.findall(r'\$\("#([A-Za-z]+)"\)', FAL)))
manquent = [i for i in ids if f'id="{i}"' not in HTML]
check(f"H1 les {len(ids)} éléments lus par fal.js existent dans index.html", ids and not manquent, str(manquent))
check("H2 la section de l'atelier est cachée tant qu'on ne l'ouvre pas, le bouton Rig grisé par défaut",
      '<section id="falPanel" class="hidden">' in HTML and '<button id="btnRig" class="btn-run" disabled>' in HTML)
check("H3 studio3d.js importe fal.js et le branche avec le dialogue maison (jamais alert/confirm)",
      'import * as FAL from "./fal.js";' in JS and "FAL.brancher({ confirmer: (m, o) => window.__dzDialogue.confirmer(m, o), toast });" in JS
      and "alert(" not in FAL and "confirm(" not in FAL.replace("confirmer(", ""))
check("H4 le bouton du moteur fal ouvre l'atelier ; le hub reste à un clic (falHub)",
      re.search(r'\$\("#engineGoto"\)\.addEventListener\("click", \(\) => \{\s*\$\("#falPanel"\)\.classList\.remove\("hidden"\);', JS) is not None
      and '$("#falHub").addEventListener("click", () => gotoSubtab("3d"));' in JS)

HARNAIS = r"""
const EL = {};
function el(id){ if(!EL[id]) EL[id] = {id, textContent:"", innerHTML:"", value:"", disabled:false, title:"", dataset:{},
  _cls:new Set(), classList:{ add(c){EL[id]._cls.add(c)}, remove(c){EL[id]._cls.delete(c)}, toggle(c,on){ if(on) EL[id]._cls.add(c); else EL[id]._cls.delete(c)} },
  querySelector(){ return null }, querySelectorAll(){ return [] }, appendChild(){}, addEventListener(){}, selectedOptions:[] };
  return EL[id] }
globalThis.document = { querySelector(s){ return el(s.replace(/^#/, "")) }, createElement(){ return {setAttribute(){},removeAttribute(){}} } };
const CALLS = [];
let DEVIS = null;
globalThis.fetch = async (u, o) => { o = o || {}; CALLS.push({u, m: o.method || "GET", b: o.body ? JSON.parse(o.body) : null});
  const rep = (st, js) => ({ ok: st < 400, status: st, json: async () => js });
  if (u === "/api/etabli/sources") return rep(200, {jobs: [
    {source:"assets3d", id:"ancien", nom:"ancien", moteur:"tripo", created_at:"2026-10-01", etapes:[{version:1}]},
    {source:"meshy", id:"m1", nom:"m1", etapes:[{version:null}]},
    {source:"assets3d", id:"vide", nom:"vide", created_at:"2026-10-09", etapes:[]},
    {source:"assets3d", id:"perso", nom:"perso", moteur:"tripo-h3.1", created_at:"2026-10-05", etapes:[{version:1},{version:2}]}]});
  if (u.startsWith("/api/assets/3d/perso/rig/devis")) return rep(200, DEVIS);
  if (u === "/api/assets/3d/perso/animations") return rep(200, {animations: []});
  if (u === "/api/assets/3d/perso/rig") return rep(200, {job_id: "j1", status: "queued"});
  return rep(404, {detail: "inconnu " + u}); };
globalThis.setInterval = () => 1; globalThis.clearInterval = () => {};
const F = await import(process.argv[2]);
const OUT = {};
const base = {fichier:"model.v2.glb", tris:12, remesh_requis:false, credits:{meshy:11}, total_usd:0.22,
  breakdown:[{label:"Auto-rig", units:5},{label:"Animation 0 · Idle", units:3},{label:"Animation 4 · Attack", units:3}],
  actions_connues:{"0":"Idle","4":"Attack"}, approuve:true, texture:true, meshy:true, fal:true};
OUT.refus = [F.refus(null), F.refus({...base, meshy:false}), F.refus({...base, approuve:false}), F.refus({...base, texture:false}), F.refus(base), F.refus({...base, fal:false, approuve:false})];
DEVIS = {...base, approuve:false};
await F.chargerJobs();
OUT.options = EL.falJob.innerHTML; OUT.job = F.F.job;
OUT.gris = {dis: EL.btnRig.disabled, refus: EL.rigRefus.textContent, title: EL.btnRig.title};
DEVIS = base;
await F.rafraichirDevis();
OUT.pret = {dis: EL.btnRig.disabled, txt: EL.btnRig.textContent, title: EL.btnRig.title, refus: EL.rigRefus.textContent,
  note: EL.falJobNote.textContent, actions: EL.rigActions.innerHTML};
F.F.actions.add(4); F.F.actions.add(0);
CALLS.length = 0;
await F.rafraichirDevis();
OUT.devisActions = CALLS.map(c => c.u);
el("rigH").value = "1.8";
CALLS.length = 0; let msg = null;
await F.lancerRig(async (m) => { msg = m; return false; }, () => {});
OUT.refuse = {posts: CALLS.filter(c => c.m === "POST").length, msg};
await F.lancerRig(async () => true, () => {});
OUT.tir = CALLS.filter(c => c.m === "POST").map(c => c.u + " " + JSON.stringify(c.b));
DEVIS = {...base, texture:false}; await F.rafraichirDevis(); CALLS.length = 0; let t = null;
await F.lancerRig(async () => true, (m) => { t = m; });
OUT.ferme = {posts: CALLS.filter(c => c.m === "POST").length, toast: t};
console.log(JSON.stringify(OUT));
"""

p = _TMP / "h.mjs"
p.write_text(HARNAIS, encoding="utf-8")
r = subprocess.run(["node", str(p), (S3D / "fal.js").as_uri()], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-500:] + r.stderr[-900:]}
check("U0 fal.js s'importe et s'exécute sous node", "erreur" not in o and "refus" in o, str(o)[:900])
if "refus" in o:
    rf = o["refus"]
    check("U1 refus() : devis absent, clé Meshy, clé fal, approbation, texture — dans cet ordre ; rien quand tout est ouvert",
          "indisponible" in rf[0] and "clé Meshy" in rf[1] and "approuvée" in rf[2] and "texture" in rf[3] and rf[4] == ""
          and "clé fal" in rf[5], str(rf))
    check("U2 la liste : jobs fal AVEC versions seulement, le plus récent d'abord", o["job"] == "perso"
          and o["options"].index("perso") < o["options"].index("ancien") and "m1" not in o["options"] and ">vide" not in o["options"], o["options"])
    g = o["gris"]
    check("U3 non approuvé : bouton grisé, la raison écrite ET en infobulle", g["dis"] is True and "approuvée" in g["refus"] and "approuvée" in g["title"], str(g))
    pr = o["pret"]
    check("U4 tout ouvert : bouton actif, prix du DEVIS (11 cr), détail par ligne en infobulle, fichier et tris dits",
          pr["dis"] is False and pr["txt"] == "Rig Meshy · 11 cr" and "Animation 4 · Attack : 3 cr" in pr["title"]
          and pr["refus"] == "" and "model.v2.glb · 12 tris" in pr["note"], str(pr))
    check("U5 les actions de la bibliothèque deviennent des cases (du devis, pas d'une liste recopiée)",
          'value="0"' in pr["actions"] and "Attack" in pr["actions"], pr["actions"][:200])
    check("U6 les actions cochées partent au devis, triées", o["devisActions"] == ["/api/assets/3d/perso/rig/devis?actions=0%2C4"], str(o["devisActions"]))
    check("U7 confirmation refusée : AUCUN POST, et le message dit les crédits et le détail",
          o["refuse"]["posts"] == 0 and "11 crédits" in o["refuse"]["msg"] and "Animation 0 · Idle : 3 cr" in o["refuse"]["msg"], str(o["refuse"]))
    check("U8 confirmé : POST avec la taille et les actions", len(o["tir"]) == 1 and o["tir"][0].startswith("/api/assets/3d/perso/rig ")
          and json.loads(o["tir"][0].split(" ", 1)[1]) in ({"height_m": 1.8, "actions": [4, 0]}, {"height_m": 1.8, "actions": [0, 4]}), str(o["tir"]))
    check("U9 porte fermée au moment du clic : aucun POST, la raison en toast", o["ferme"]["posts"] == 0 and "texture" in (o["ferme"]["toast"] or ""), str(o["ferme"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
