# -*- coding: utf-8 -*-
"""T106 (plan-moteurs-3d T6, P5) — « Vues d'abord » de /studio3d : le module vues.js est IMPORTÉ sous node (faux DOM,
fetch et dialogues en doublures qui notent tout). Vérifié : chaque élément que vues.js lit existe dans index.html ;
studio3d.js importe le module et le branche avec les dialogues maison ; le prix de chaque geste payant est celui du
devis du backend et se CONFIRME (refus = aucun POST) ; le tir est chiffré comme un moteur SEUL ; « Tirer » se grise et
dit pourquoi (déjà tiré, aucune vue, opération en cours) ; le détourage local part sans question.
Témoin positif : la base (208a7295) n'a pas vues.js.
Run (depuis backend/) : & $PY tests/test_studio3d_vues.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
S3D = RACINE / "frontend" / "studio3d"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzvues_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "208a7295:frontend/studio3d/vues.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas « Vues d'abord »", r0.returncode != 0)

VJS = (S3D / "vues.js").read_text(encoding="utf-8")
HTML = (S3D / "index.html").read_text(encoding="utf-8")
JS = (S3D / "studio3d.js").read_text(encoding="utf-8")
ids = sorted(set(re.findall(r'\$\("#([A-Za-z]+)"\)', VJS)))
manquent = [i for i in ids if f'id="{i}"' not in HTML]
check(f"H1 les {len(ids)} éléments lus par vues.js existent dans index.html", ids and not manquent, str(manquent))
check("H2 la section est cachée tant qu'on ne l'ouvre pas ; Préparer et Tirer grisés par défaut",
      '<section id="vuesPanel" class="hidden">' in HTML and '<button id="btnVues" class="btn-run" disabled>' in HTML
      and '<button id="btnTirer" class="btn-run" disabled>' in HTML)
check("H3 studio3d.js importe vues.js et le branche avec les dialogues maison (jamais alert/confirm/prompt)",
      'import * as VUES from "./vues.js";' in JS and "saisir: (m, o) => window.__dzDialogue.saisir(m, o)" in JS
      and "VUES.brancher(" in JS and not re.search(r"\b(alert|confirm|prompt)\(", VJS))
check("H4 le bouton du moteur fal ouvre aussi « Vues d'abord » et le charge",
      re.search(r'\$\("#vuesPanel"\)\.classList\.remove\("hidden"\);\s*VUES\.charger\(\)', JS) is not None)

HARNAIS = r"""
const EL = {};
function el(id){ if(!EL[id]) EL[id] = {id, textContent:"", innerHTML:"", value:"", disabled:false, title:"", dataset:{},
  classList:{ add(){}, remove(){}, toggle(){}, contains(){ return false } }, addEventListener(){}, closest(){ return null } };
  return EL[id] }
globalThis.document = { querySelector(s){ return el(s.replace(/^#/, "")) } };
const CALLS = [];
const JEU = {job:"ab12cd34", etat:"en_attente", engine:"tripo-h3.1", image_filename:"poulpe.png",
  payload:{textures:true, quality:"hd", formats:["glb"]},
  vues:[{index:0, cle:"source", role:"source", file:"shot_0.png", url:"u0", prompt:null, rejeux:0, detoure:null},
        {index:1, cle:"front", role:"vue", file:"shot_1.png", url:"u1", prompt:"front view", rejeux:2, detoure:"local"},
        {index:2, cle:"back", role:"vue", file:null, url:null, prompt:"back view", rejeux:0, detoure:null, erreur:"seedream KO"}]};
let INFO = JEU;
globalThis.fetch = async (u, o) => { o = o || {}; const b = o.body ? JSON.parse(o.body) : null; CALLS.push({u, m: o.method || "GET", b});
  const rep = (st, js) => ({ ok: st < 400, status: st, json: async () => js });
  if (u === "/api/images") return rep(200, {images: [{filename:"poulpe.png"}, {filename:"autre.png"}]});
  if (u === "/api/assets3d/engines") return rep(200, {engines: [{id:"tripo", label:"Tripo", usd_texture:0.3}, {id:"tripo-h3.1", label:"Tripo H3.1", usd_texture:0.4, max_images:1}], default:"tripo"});
  if (u === "/api/assets/3d/views" && (o.method || "GET") === "GET") return rep(200, {jeux: [{job:"ab12cd34", etat:"en_attente", engine:"tripo-h3.1", image_filename:"poulpe.png", ratees:1}]});
  if (u === "/api/assets/3d/ab12cd34/views") return rep(200, INFO);
  if (u === "/api/cost/estimate") return rep(200, {total_usd: b.kind === "asset3d_views" ? 0.03 * b.views : 0.40, kind: b.kind});
  if (u === "/api/assets/3d/views") return rep(200, {job_id:"jv", job:"nouveau", status:"queued"});
  if (u.endsWith("/rejouer")) return rep(200, {job_id:"jr", status:"queued"});
  if (u.endsWith("/detourer")) return rep(200, {via:"local", usd:0, methode:"coins"});
  if (u.endsWith("/tirer")) return rep(200, {job_id:"jt", status:"queued"});
  return rep(404, {detail: "inconnu " + u}); };
globalThis.setInterval = () => 1; globalThis.clearInterval = () => {};
const M = await import(process.argv[2]);
const OUT = {};
const ouvert = (x) => ({...JEU, ...x});
OUT.refus = [M.refusTir(null), M.refusTir(ouvert({etat:"tire"})), M.refusTir(JEU, true),
  M.refusTir(ouvert({vues:[{...JEU.vues[2]}]})), M.refusTir(JEU)];
el("vuesN").value = "3";
await M.charger();
OUT.charge = {img: EL.vuesImg.innerHTML, moteur: EL.vuesMoteur.innerHTML, jeu: EL.vuesJeu.innerHTML, prep: EL.btnVues.textContent,
  prepDis: EL.btnVues.disabled, grille: EL.vuesGrille.innerHTML, tir: EL.btnTirer.textContent, tirDis: EL.btnTirer.disabled};
el("vuesImg").value = "poulpe.png"; el("vuesMoteur").value = "tripo-h3.1"; el("vuesSujet").value = "  un poulpe  ";
await M.prixPreparer();
await M.charger();   // vu à l'écran le 06/10 : le rechargement après la préparation remettait l'image et le moteur au 1er choix
OUT.garde = {img: EL.vuesImg.innerHTML, moteur: EL.vuesMoteur.innerHTML};
CALLS.length = 0; let msg = null;
await M.preparer(async (m) => { msg = m; return false; }, () => {});
OUT.prepRefus = {posts: CALLS.filter(c => c.m === "POST" && c.u !== "/api/cost/estimate").length, msg};
await M.preparer(async () => true, () => {});
OUT.prep = CALLS.filter(c => c.u === "/api/assets/3d/views" && c.m === "POST").map(c => c.b);
M.V.occupe = false; M.V.jeu = "ab12cd34"; await M.ouvrirJeu("ab12cd34");
CALLS.length = 0; let q = null;
await M.rejouer(1, async (m, o) => { q = {m, o}; return null; }, () => {});
OUT.rejRefus = {posts: CALLS.filter(c => c.u.endsWith("/rejouer")).length, q};
await M.rejouer(1, async () => "  front view, arms visible  ", () => {});
OUT.rej = CALLS.filter(c => c.u.endsWith("/rejouer")).map(c => c.u + " " + JSON.stringify(c.b));
M.V.occupe = false;
CALLS.length = 0; let t = null;
await M.detourer(1, (m) => { t = m; });
OUT.det = {calls: CALLS.filter(c => c.m === "POST").map(c => c.u + " " + JSON.stringify(c.b)), toast: t};
M.V.occupe = false; INFO = JEU; await M.ouvrirJeu("ab12cd34");
CALLS.length = 0; msg = null;
await M.tirer(async (m) => { msg = m; return false; }, () => {});
OUT.tirRefus = {posts: CALLS.filter(c => c.u.endsWith("/tirer")).length, msg,
  devis: CALLS.filter(c => c.u === "/api/cost/estimate").map(c => c.b)};
await M.tirer(async () => true, () => {});
OUT.tir = CALLS.filter(c => c.u.endsWith("/tirer")).map(c => c.u);
OUT.occupe = {dis: EL.btnTirer.disabled, refus: EL.tirRefus.textContent};
M.V.occupe = false; INFO = ouvert({etat:"tire"}); await M.ouvrirJeu("ab12cd34");
OUT.tire = {dis: EL.btnTirer.disabled, txt: EL.btnTirer.textContent, grille: EL.vuesGrille.innerHTML};
CALLS.length = 0; t = null;
await M.tirer(async () => true, (m) => { t = m; });
OUT.tireTir = {posts: CALLS.filter(c => c.u.endsWith("/tirer")).length, toast: t};
console.log(JSON.stringify(OUT));
"""

p = _TMP / "h.mjs"
p.write_text(HARNAIS, encoding="utf-8")
# vues.js importe fal.js (jget/jpost) : on importe la copie du DÉPÔT, chemins relatifs intacts
r = subprocess.run(["node", str(p), (S3D / "vues.js").as_uri()], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-500:] + r.stderr[-900:]}
check("U0 vues.js s'importe et s'exécute sous node", "erreur" not in o and "refus" in o, str(o)[:900])
if "refus" in o:
    rf = o["refus"]
    check("U1 refusTir : aucun jeu, déjà tiré, opération en cours, aucune vue ; rien quand tout est ouvert",
          "aucun jeu" in rf[0] and "déjà tiré" in rf[1] and "en cours" not in rf[1] and "attends" in rf[2]
          and "aucune vue" in rf[3] and rf[4] == "", str(rf))
    c = o["charge"]
    check("U2 chargement : images de la Bibliothèque, moteurs avec leur prix, le jeu le plus récent ouvert",
          "poulpe.png" in c["img"] and "Tripo H3.1 · $0.40" in c["moteur"] and "1 ratée(s)" in c["jeu"], str(c)[:400])
    check("U3 le prix de « Préparer » vient du devis (3 vues → $0.09)", c["prep"] == "Préparer 3 vues · $0.09", c["prep"])
    g = c["grille"]
    check("U4 la grille : la source sans bouton, la vue détourée et rejouée le dit, la vue ratée le dit et ne se détoure pas",
          g.count('class="v-rej"') == 2 and "2↻" in g and "✂ local" in g and "ratée" in g
          and re.search(r'class="v-det" data-i="2" disabled', g) is not None and 'data-i="0"' in g
          and "vue absente" in g, g[:900])
    check("U4b chaque vue s'ouvre en grand dans un nouvel onglet (une vignette de rail ne suffit pas à juger)",
          g.count('target="_blank"') == 2 and "/api/assets/3d/ab12cd34/shot/1?" in g, g[:400])
    ga = o["garde"]
    check("U4c recharger garde l'image et le moteur choisis (vu à l'écran : ils revenaient au premier choix)",
          '<option value="poulpe.png" selected>' in ga["img"] and '<option value="tripo-h3.1" selected>' in ga["moteur"]
          and '<option value="tripo" selected>' not in ga["moteur"], str(ga))
    check("U5 Tirer actif et nommé par le moteur quand tout est ouvert", c["tirDis"] is False and c["tir"] == "Tirer · tripo-h3.1", str(c))
    pr = o["prepRefus"]
    check("U6 préparation refusée au dialogue : AUCUN POST, le message dit le prix et qu'aucun moteur ne tourne",
          pr["posts"] == 0 and "$0.09" in pr["msg"] and "Aucun moteur" in pr["msg"], str(pr))
    check("U7 préparation confirmée : POST avec l'image, le moteur, le nombre de vues et le sujet nettoyé",
          o["prep"] == [{"image_filename": "poulpe.png", "engine": "tripo-h3.1", "views": 3, "subject": "un poulpe"}], str(o["prep"]))
    rr = o["rejRefus"]
    check("U8 rejouer : le dialogue de saisie porte le prompt d'origine et le prix ; annulé = AUCUN POST",
          rr["posts"] == 0 and rr["q"]["o"]["valeur"] == "front view" and "$0.03" in rr["q"]["m"]
          and "$0.03" in rr["q"]["o"]["ok"], str(rr))
    check("U9 rejouer confirmé : POST de CETTE vue avec le prompt corrigé",
          o["rej"] == ['/api/assets/3d/ab12cd34/views/1/rejouer {"prompt":"front view, arms visible"}'], str(o["rej"]))
    d = o["det"]
    check("U10 détourer : local, sans dialogue, un seul POST, gratuit dit en toast",
          d["calls"] == ['/api/assets/3d/ab12cd34/views/1/detourer {"via":"local"}'] and "gratuit" in (d["toast"] or ""), str(d))
    tr = o["tirRefus"]
    check("U11 tir : chiffré comme un MOTEUR seul (kind asset3d, sans vues), avec les options du jeu ; refusé = aucun POST",
          tr["posts"] == 0 and tr["devis"] and tr["devis"][0]["kind"] == "asset3d" and "views" not in tr["devis"][0]
          and "multiview" not in tr["devis"][0] and tr["devis"][0]["engine"] == "tripo-h3.1" and tr["devis"][0]["quality"] == "hd"
          and "$0.40" in tr["msg"] and "déjà payées" in tr["msg"], str(tr))
    check("U11b le message dit ce qui part VRAIMENT : le moteur plafonne ses images (vu à l'écran : « 5 » pour 4 envoyées)",
          "1 des 2 images" in tr["msg"] and "au plus 1" in tr["msg"], tr["msg"])
    check("U12 tir confirmé : un POST tirer", o["tir"] == ["/api/assets/3d/ab12cd34/tirer"], str(o["tir"]))
    check("U13 pendant le suivi, Tirer se grise et dit pourquoi", o["occupe"]["dis"] is True and "attends" in o["occupe"]["refus"], str(o["occupe"]))
    te = o["tire"]
    check("U14 jeu déjà tiré : bouton « Déjà tiré » grisé, plus aucun bouton de vue", te["dis"] is True and te["txt"] == "Déjà tiré"
          and "v-rej" not in te["grille"] and "v-det" not in te["grille"], str(te)[:300])
    check("U15 un clic sur un jeu tiré : aucun POST, la raison en toast",
          o["tireTir"]["posts"] == 0 and "déjà tiré" in (o["tireTir"]["toast"] or ""), str(o["tireTir"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
