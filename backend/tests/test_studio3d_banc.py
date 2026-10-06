# -*- coding: utf-8 -*-
"""T107 (plan-moteurs-3d T8, D2) — le banc de référence dans /studio3d : le module banc.js est IMPORTÉ sous node (faux
DOM, fetch en doublure qui note tout). Vérifié : chaque élément lu existe dans index.html ; studio3d.js importe et
branche le module ; le tableau cite les médianes du backend et dit « jamais mesuré chez nous » pour un moteur sans
ligne (jamais la note du fournisseur) ; ranger le job choisi de l'atelier est un POST gratuit, sans dialogue de
paiement, puis le tableau se relit ; sans job, aucun POST.
Témoin positif : la base (301e168a) n'a pas banc.js.
Run (depuis backend/) : & $PY tests/test_studio3d_banc.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
S3D = RACINE / "frontend" / "studio3d"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzbanc_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "301e168a:frontend/studio3d/banc.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas le banc dans /studio3d", r0.returncode != 0)

BJS = (S3D / "banc.js").read_text(encoding="utf-8")
HTML = (S3D / "index.html").read_text(encoding="utf-8")
JS = (S3D / "studio3d.js").read_text(encoding="utf-8")
ids = sorted(set(re.findall(r'\$\("#([A-Za-z]+)"\)', BJS)))
manquent = [i for i in ids if f'id="{i}"' not in HTML]
check(f"H1 les {len(ids)} éléments lus par banc.js existent dans index.html", ids and not manquent, str(manquent))
check("H2 studio3d.js importe banc.js, le charge à l'ouverture de l'atelier et le branche",
      'import * as BANC from "./banc.js";' in JS and "BANC.charger()" in JS and "BANC.brancher(" in JS
      and not re.search(r"\b(alert|confirm|prompt)\(", BJS))

HARNAIS = r"""
const EL = {};
function el(id){ if(!EL[id]) EL[id] = {id, textContent:"", innerHTML:"", value:"", disabled:false, title:"", dataset:{},
  classList:{ add(){}, remove(){}, toggle(){} }, addEventListener(){} }; return EL[id] }
globalThis.document = { querySelector(s){ return el(s.replace(/^#/, "")) } };
const CALLS = [];
let BANC = {tripo: {sujets: 2, tris_median: 123456, bytes_median: 3145728, usd_median: 0.42, ferme_sur: 1, mesures: 2}};
globalThis.fetch = async (u, o) => { o = o || {}; CALLS.push({u, m: o.method || "GET", b: o.body ? JSON.parse(o.body) : null});
  const rep = (st, js) => ({ ok: st < 400, status: st, json: async () => js });
  if (u === "/api/assets3d/engines") return rep(200, {engines: [
      {id: "rodin", label: "Rodin", banc: BANC.rodin || null}, {id: "tripo", label: "Tripo v2.5", banc: BANC.tripo || null}],
    sujets_banc: [{id: "personnage", label: "Personnage"}, {id: "objet", label: "Objet / accessoire"}, {id: "vehicule", label: "Véhicule"}]});
  if (u === "/api/assets3d/banc") {
    if (o.body && JSON.parse(o.body).job === "sans_fiche") return rep(404, {detail: "sans_fiche : aucune fiche pour ce job"});
    BANC.rodin = {sujets: 1, tris_median: 900, bytes_median: 1048576, usd_median: 0.52, ferme_sur: 0, mesures: 1};
    return rep(200, {sujet: "vehicule", moteur: "rodin", tris: 900, usd_estime: 0.52});
  }
  return rep(404, {detail: "inconnu " + u}); };
const FAL = await import(process.argv[3]);
const M = await import(process.argv[2]);
const OUT = {};
await M.charger();
OUT.table = EL.falBanc.innerHTML; OUT.sujets = EL.bancSujet.innerHTML;
FAL.F.job = null; CALLS.length = 0; let t = null;
await M.ranger((m) => { t = m; });
OUT.sansJob = {posts: CALLS.filter(c => c.m === "POST").length, toast: t};
FAL.F.job = "a1b2c3d4"; el("bancSujet").value = "vehicule"; CALLS.length = 0; t = null;
await M.ranger((m) => { t = m; });
OUT.range = {posts: CALLS.filter(c => c.m === "POST").map(c => c.u + " " + JSON.stringify(c.b)), toast: t,
  relu: CALLS.filter(c => c.u === "/api/assets3d/engines").length, table: EL.falBanc.innerHTML};
FAL.F.job = "sans_fiche"; t = null;
await M.ranger((m) => { t = m; }).catch((e) => { t = "EXC " + e.message; });
OUT.refus = t;
console.log(JSON.stringify(OUT));
"""

p = _TMP / "h.mjs"
p.write_text(HARNAIS, encoding="utf-8")
r = subprocess.run(["node", str(p), (S3D / "banc.js").as_uri(), (S3D / "fal.js").as_uri()],
                   capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-500:] + r.stderr[-900:]}
check("U0 banc.js s'importe et s'exécute sous node", "erreur" not in o and "table" in o, str(o)[:900])
if "table" in o:
    tb = o["table"]
    check("U1 le tableau cite les médianes du backend (tris, poids, $, étanche)",
          "123" in tb and "3.0 Mo" in tb and "0.42" in tb and "1/2" in tb, tb[:500])
    check("U2 un moteur sans ligne dit « jamais mesuré chez nous » — pas un chiffre inventé",
          "Rodin" in tb and "jamais mesuré chez nous" in tb, tb[:500])
    check("U2b une ligne par moteur, pas un tableau : six colonnes ne tiennent pas dans le rail (vu à l'écran le 06/10)",
          "<table" not in tb and tb.count('class="banc-ligne"') == 2, tb[:300])
    check("U3 les sujets types viennent du backend", "Personnage" in o["sujets"] and 'value="vehicule"' in o["sujets"], o["sujets"])
    check("U4 sans job choisi dans l'atelier : aucun POST, la raison dite", o["sansJob"]["posts"] == 0 and "job" in (o["sansJob"]["toast"] or ""),
          str(o["sansJob"]))
    rg = o["range"]
    check("U5 ranger : UN POST {job, sujet} sans dialogue (gratuit), le toast le dit, puis le tableau se relit",
          rg["posts"] == ['/api/assets3d/banc {"job":"a1b2c3d4","sujet":"vehicule"}'] and "gratuit" in (rg["toast"] or "")
          and rg["relu"] == 1 and "jamais mesuré" not in rg["table"], str(rg)[:500])
    check("U6 un refus du backend (job sans fiche) remonte tel quel", "aucune fiche" in (o["refus"] or ""), str(o["refus"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
