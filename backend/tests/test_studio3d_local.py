# -*- coding: utf-8 -*-
"""T107 (plan-moteurs-3d T10, D4) — le service GPU local dans /studio3d : local.js IMPORTÉ sous node (faux DOM, fetch
en doublure), et le sélecteur de moteur de vues.js. Vérifié : le service absent est DIT (adresse, carte mesurée, ce que
la VRAM permet, l'avertissement Win32 s'il y en a un) au lieu d'un gris muet ; prêt, il dit forme seule ou texture ;
dans « Vues d'abord », un moteur indisponible est grisé avec SA raison (service local absent / clé fal absente) et
n'est jamais présélectionné.
Témoin positif : la base (301e168a) n'a pas local.js.
Run (depuis backend/) : & $PY tests/test_studio3d_local.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
S3D = RACINE / "frontend" / "studio3d"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzlocal_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "301e168a:frontend/studio3d/local.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas local.js", r0.returncode != 0)
LJS = (S3D / "local.js").read_text(encoding="utf-8")
HTML = (S3D / "index.html").read_text(encoding="utf-8")
JS = (S3D / "studio3d.js").read_text(encoding="utf-8")
ids = sorted(set(re.findall(r'\$\("#([A-Za-z]+)"\)', LJS)))
check(f"H1 les {len(ids)} éléments lus par local.js existent dans index.html",
      ids and all(f'id="{i}"' in HTML for i in ids), str(ids))
check("H2 studio3d.js importe local.js et le charge à l'ouverture de l'atelier",
      'import * as LOCAL from "./local.js";' in JS and "LOCAL.charger()" in JS)

HARNAIS = r"""
const EL = {};
function el(id){ if(!EL[id]) EL[id] = {id, textContent:"", innerHTML:"", value:"", disabled:false, dataset:{},
  classList:{ add(){}, remove(){}, toggle(){} }, addEventListener(){} }; return EL[id] }
globalThis.document = { querySelector(s){ return el(s.replace(/^#/, "")) } };
let ETAT = null;
globalThis.fetch = async (u) => {
  const rep = (st, js) => ({ ok: st < 400, status: st, json: async () => js });
  if (u === "/api/assets3d/local") return rep(200, ETAT);
  if (u === "/api/assets3d/engines") return rep(200, {default: "tripo", engines: [
    {id: "hunyuan-local", label: "Hunyuan3D 2.1 (local)", local: true, available: false, usd_texture: 0},
    {id: "tripo", label: "Tripo v2.5", available: false, usd_texture: 0.3},
    {id: "trellis", label: "Trellis", available: true, usd_texture: 0.35}]});
  if (u === "/api/images") return rep(200, {images: [{filename: "a.png"}]});
  if (u === "/api/assets/3d/views") return rep(200, {jeux: []});
  if (u === "/api/bible/entities") return rep(200, {entities: []});
  if (u === "/api/cost/estimate") return rep(200, {total_usd: 0.12});
  return rep(404, {detail: u}); };
globalThis.setInterval = () => 1; globalThis.clearInterval = () => {};
const L = await import(process.argv[2]);
const V = await import(process.argv[3]);
const OUT = {};
const carte = {nom: "NVIDIA GeForce RTX 2080 Ti", vram_mo: 11264, source: "nvidia-smi", avertissement: null};
const dec = {moteur: "hunyuan-2.1", texture: false, pourquoi: "11264 Mo ≥ 10 Go : la FORME tient."};
ETAT = {url: "http://127.0.0.1:8081", providers: [{id: "fal", ready: true}, {id: "local3d", ready: false, carte, decision: dec}]};
await L.charger(); OUT.absent = EL.falLocal.innerHTML;
ETAT.providers[1].carte = {nom: "GPU", vram_mo: 4095, source: "win32", avertissement: "AdapterRAM est un uint32 : il plafonne à 4 Gio."};
await L.charger(); OUT.win32 = EL.falLocal.innerHTML;
ETAT.providers[1] = {id: "local3d", ready: true, carte, decision: dec};
await L.charger(); OUT.pret = EL.falLocal.innerHTML;
await V.charger(); OUT.moteurs = EL.vuesMoteur.innerHTML;
console.log(JSON.stringify(OUT));
"""
p = _TMP / "h.mjs"
p.write_text(HARNAIS, encoding="utf-8")
r = subprocess.run(["node", str(p), (S3D / "local.js").as_uri(), (S3D / "vues.js").as_uri()],
                   capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-500:] + r.stderr[-900:]}
check("U0 local.js et vues.js s'importent et s'exécutent sous node", "erreur" not in o and "absent" in o, str(o)[:900])
if "absent" in o:
    a = o["absent"]
    check("U1 service absent : DIT, avec l'adresse, la carte mesurée et ce que la VRAM permet",
          "absent" in a and "127.0.0.1:8081" in a and "RTX 2080 Ti" in a and "11264" in a and "FORME" in a
          and "LOCAL3D_URL" in a, a)
    check("U2 la mesure Win32 porte son avertissement (uint32, 4 Gio)", "uint32" in o["win32"] and "win32" in o["win32"], o["win32"])
    check("U3 service prêt : forme seule, dit", "prêt" in o["pret"] and "forme seule" in o["pret"], o["pret"])
    m = o["moteurs"]
    check("U4 moteur local sans service : grisé, avec SA raison", re.search(r'value="hunyuan-local"[^>]*disabled[^>]*>[^<]*service local absent', m) is not None, m)
    check("U5 moteur fal sans clé : grisé, avec SA raison", re.search(r'value="tripo"[^>]*disabled[^>]*>[^<]*clé fal absente', m) is not None, m)
    check("U6 jamais un moteur grisé présélectionné : le premier disponible l'est (le défaut tripo est indisponible)",
          re.search(r'value="trellis"[^>]*selected', m) is not None and not re.search(r'disabled[^>]*selected|selected[^>]*disabled', m), m)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
