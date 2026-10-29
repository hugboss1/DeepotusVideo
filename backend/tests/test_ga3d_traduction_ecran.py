# -*- coding: utf-8 -*-
"""t376 (29/10/2026) — l'écran Game Assets 3D en français ET en anglais (maillon de queue dzga3d).

Ce que le banc prouve :
  1. le bundle : plus aucun des anciens textes en dur dans DzGameAssets, DzOptimize, DzLod, DzTex et __dzPrint3d ;
     chaque clé ga3d.* employée existe avec son FR et son EN ; le français de la rangée Optimiser / LOD / Textures et
     de la boîte d'impression est repris À L'IDENTIQUE ;
  2. DzGameAssets JOUÉ sous node (faux React, faux fetch), en FR puis en EN : formulaire, cartes (état, Renommer,
     Supprimer, Vues, Ranger dans la Bibliothèque), dialogues de renommage et de suppression, refus de génération,
     graphe (Entrée, Vue n, Réponse, Chaîne · moteur, Nouvel asset) ; aucun ancien texte dans le rendu FR ;
  3. DzOptimize et __dzPrint3d JOUÉS en anglais : préréglages, Optimize, Original / Optimized ; taille, titre,
     Continue, confirmation du slicer ;
  4. le maillon : appliqué, inverse avant_dzga3d exact, appelé EN TÊTE de avant_dzpose, hors couche, sonde de dzpose,
     aucun .bak laissé, aucun état React ni confirmation neufs.
Run : & $PY tests/test_ga3d_traduction_ecran.py   (depuis backend/)
"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))
import _i18n_l1_aide as AIDE                                         # noqa: E402
import patch_bundle_dzga3d as M                                      # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUN = BUNDLE.read_bytes().decode("utf-8")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "ga3d.json").read_text(encoding="utf-8"))
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzga3d_"))


def fonction(nom, avec_async=False):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    if avec_async and BUN[k - 6:k] == "async ":
        k -= 6
    i, prof, ch, vu = BUN.find("{", BUN.find(")", k)), 0, None, False
    while i < len(BUN):
        c_ = BUN[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k:i + 1]
        i += 1
    return ""


GA, OPT, LOD, TEX = fonction("DzGameAssets"), fonction("DzOptimize"), fonction("DzLod"), fonction("DzTex")
PRINT = fonction("__dzPrint3d", avec_async=True)

print("\n[1] le bundle")
ANCIENS = ["Source image", "Engine", "Subject (optional)", "e.g. a knight character", "Multi-view boost", "Views: ",
           "Export formats (GLB always)", "Generating…", "Generate 3D", "Generation 3D refusee", "erreur serveur",
           "Shot enregistré", 'fail?"failed"', 'done?"done"', '?"failed":"…"', '"generating…"', "Renommer ce rendu", "Supprimer définitivement",
           "▣ Poster", "▶ Rotate", "Dossier d'impression STL", '"Shots"', "Download shot", "Save to Library", '"Input"',
           '"View "', '"Response"', "…generating", '"waiting"', '"Download"', "← New asset", '"Pipeline · "',
           "Each view shot", "No 3D assets yet", '"Universal"', '"3D printing"']
reste = [a for a in ANCIENS if a in GA]
check("1.1 DzGameAssets : plus aucun ancien texte en dur", not reste, str(reste))
reste = [a for a in ('"Optimize"', '"Micro (500)"', '"Game Ready (10k)"', '"échec optimisation"', '"Optimisation…"',
                     '"⚙ Optimiser"', '"↓ GLB optimisé"', '"▣ Simple"', '"Original · "', '"Optimisé · "') if a in OPT]
check("1.2 DzOptimize : plus aucun texte en dur", not reste, str(reste))
reste = [a for a in ('"échec de la chaîne LOD"', '"Chaîne de LOD locale', '"Chaîne…"', '"Les GLB _LODx', '"↓ Archive LOD"',
                     '"IoU : silhouettes', '" · agressif"', '" non tenue"') if a in LOD]
check("1.3 DzLod : plus aucun texte en dur", not reste, str(reste))
reste = [a for a in ('"échec de l’export"', '"Textures : "', '"Convention de nommage', '"Ce maillage ne porte',
                     '"Archive des textures', '"Export…"', '"cuites : "', '"Dérivées de la basecolor') if a in TEX]
check("1.4 DzTex : plus aucun texte en dur", not reste, str(reste))
reste = [a for a in ('"Taille cible en mm', '"Continuer"', '"taille en mm invalide"', '"export impossible"',
                     '"Dossier d\'impression écrit', '"ouverture impossible"', '"Impression 3D : "') if a in PRINT]
check("1.5 __dzPrint3d : plus aucun texte en dur", PRINT and not reste, str(reste))
employees = set(re.findall(r'dzT\("(ga3d\.[a-z0-9_.]+)"', GA + OPT + LOD + TEX + PRINT))
check("1.6 chaque clé employée existe, FR et EN non vides", employees and all(
    k in DICO and DICO[k]["fr"] and DICO[k]["en"] for k in employees), str(sorted(k for k in employees if k not in DICO)))
check("1.7 toutes les clés du dictionnaire servent (aucune orpheline)", set(DICO) == employees, str(set(DICO) ^ employees))
IDEM = {"ga3d.opt.echec": "échec optimisation", "ga3d.opt.en_cours": "Optimisation…", "ga3d.lod.echec": "échec de la chaîne LOD",
        "ga3d.lod.en_cours": "Chaîne…", "ga3d.lod.archive": "Archive LOD", "ga3d.tex.cuites": "cuites : {liste}",
        "ga3d.tex.inventaire_refus": "Textures : {detail}", "ga3d.tex.en_cours": "Export…",
        "ga3d.impr.continuer": "Continuer", "ga3d.impr.titre": "Impression 3D", "ga3d.impr.erreur": "Impression 3D : {detail}",
        "ga3d.opt.original": "Original · {n} tris", "ga3d.opt.optimise": "Optimisé · {n} tris"}
check("1.8 le français déjà à l'écran est repris à l'identique", all(DICO[k]["fr"] == v for k, v in IDEM.items()),
      str({k: DICO[k]["fr"] for k, v in IDEM.items() if DICO[k]["fr"] != v}))
check("1.9 aucun état React ni confirmation neufs", BUN.count("x.useState(") == 731
      and BUN.count("await window.__dzDialogue.confirmer(") == 30)

print("\n[2] DzGameAssets joué sous node")
DICO_JS = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes().decode("utf-8")
PRELUDE = ("var window={};\n" + DICO_JS + "\nvar LANG='fr';function dzT(k,v){var e=window.DZ_I18N[k];var s=e?e[LANG]:k;"
           "if(v)s=s.replace(/\\{(\\w+)\\}/g,function(m,n){return v[n]!=null?String(v[n]):m});return s}\n"
           + AIDE.PRELUDE_DZGLYPH)
HARNAIS = PRELUDE + r"""
var H=[],hi=0,EFF=[],CALLS=[],REP={},ALERTES=[],DIAL=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}},useRef:function(v){return {current:v}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};
function O(p){return el("champ",p)}function Ze(p){return el("bascule",p)}function le(p){return el("saisie",p)}function re(p){return el("liste",p)}
var D={imageUrl:function(f){return "/img/"+f},renameJob:function(){return Promise.resolve()},deleteJob:function(){return Promise.resolve()}};
function dzEngOpts(c){return [{value:"tripo",label:"Tripo"}]}function dzEngTrouve(){return {usd_texture:.3,usd_brouillon:.2}}function dzEngCharger(){}
var __dzManif3d={};function DzOptimize(p){return el("DzOptimize",p)}function __dzPrint3d(){}
function setInterval(){return 1}function clearInterval(){}function alert(m){ALERTES.push(m)}
window.__dzDialogue={saisir:function(m,o){DIAL.push(["saisir",m,o]);return Promise.resolve(null)},
  confirmer:function(m,o){DIAL.push(["confirmer",m,o]);return Promise.resolve(false)}};
function fetch(u,o){o=o||{};CALLS.push({u:u,m:o.method||"GET"});var rep=REP[(o.method||"GET")+" "+u]||{st:404,js:{detail:"?"}};
  return Promise.resolve({ok:rep.st<400,status:rep.st,json:function(){return Promise.resolve(rep.js)}})}
"""
MOTEUR = r"""
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
function textes(arbre){var o=[];tout(arbre).forEach(function(n){["label","title","placeholder"].forEach(function(a){if(typeof n.p[a]==="string")o.push(n.p[a])});
  kids(n).forEach(function(k){if(typeof k==="string"||typeof k==="number")o.push(String(k))})});return o}
async function tick(){for(var i=0;i<10;i++)await new Promise(function(res){setImmediate(res)})}
function rend(){hi=0;return DzGameAssets({variant:"x"})}
async function jouer(lang){
  LANG=lang;H=[];EFF=[];hi=0;CALLS=[];ALERTES=[];DIAL=[];
  REP["GET /api/jobs"]={st:200,js:[{job_id:"aaaa1111-x",provider:"asset3d",status:"done",title:"3D · a"},
                                    {job_id:"bbbb2222-x",provider:"asset3d",status:"failed",title:"3D · b"}]};
  REP["GET /api/images"]={st:200,js:{images:[{filename:"k.png"}]}};
  REP["GET /api/assets/3d/aaaa1111/manifest"]={st:200,js:{formats:["glb"],shots:[0,1]}};
  rend();EFF.forEach(function(f){f()});await tick();var t=rend();
  var o={form:textes(t)};
  var boutons=tout(t).filter(function(n){return n.t==="button"});
  var ren=boutons.filter(function(b){return b.p.title===dzT("ga3d.carte.renommer")})[0];await ren.p.onClick();
  var sup=boutons.filter(function(b){return b.p.title===dzT("ga3d.carte.supprimer")})[0];await sup.p.onClick();
  o.dial=DIAL.map(function(d){return [d[0],d[1],d[2]?(d[2].titre||"")+"|"+(d[2].ok||""):""]});
  tout(t).filter(function(n){return n.t==="img"&&n.p.title==="k.png"})[0].p.onClick();t=rend();
  var gen=tout(t).filter(function(n){return n.t==="button"&&txt(n)===dzT("ga3d.form.generer")})[0];
  REP["POST /api/assets/3d"]={st:400,js:{detail:"MOTIF"}};gen.p.onClick();await tick();o.alertes=ALERTES.slice();
  REP["POST /api/assets/3d"]={st:200,js:{job_id:"cccc3333-x"}};t=rend();
  tout(t).filter(function(n){return n.t==="button"&&txt(n)===dzT("ga3d.form.generer")})[0].p.onClick();await tick();
  o.graphe=textes(rend());
  return o}
(async function(){var fr=await jouer("fr");var en=await jouer("en");console.log(JSON.stringify({fr:fr,en:en}))})()
  .catch(function(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
p = _TMP / "ga.js"
p.write_text(HARNAIS + fonction("dzPoseChoix") + "\n" + GA + MOTEUR, encoding="utf-8")
r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    J = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:                                                    # noqa: BLE001
    J = {"erreur": r.stdout[-400:] + r.stderr[-800:]}
check("2.0 DzGameAssets s'exécute sous node", "erreur" not in J and "fr" in J, str(J)[:800])
if "fr" in J:
    for lang, att in (("fr", ["Image source", "Moteur", "Sujet (facultatif)", "ex. un chevalier", "Textures", "Vues multiples",
                              "Vues : 4", "Formats d'export (GLB toujours)", "Générer la 3D", "terminé", "échec", "Vues",
                              "Renommer", "Supprimer", "Télécharger la vue", "Ranger dans la Bibliothèque",
                              DICO["ga3d.ecran.intro"]["fr"], "Universel", "Impression 3D"]),
                      ("en", ["Source image", "Engine", "Subject (optional)", "e.g. a knight character", "Multi-view boost",
                              "Views: 4", "Export formats (GLB always)", "Generate 3D", "done", "failed", "Shots", "Rename",
                              "Delete", "Download shot", "Save to Library", DICO["ga3d.ecran.intro"]["en"], "Universal",
                              "3D printing"])):
        vus = J[lang]["form"]
        manque = [a for a in att if not any(a == v or a in v for v in vus)]
        check(f"2.1 {lang} formulaire et cartes traduits", not manque, str(manque))
    anciens_fr = [a for a in ("Source image", "Engine", "Subject (optional)", "Generate 3D", "Multi-view boost", "Shots",
                              "Download shot", "Save to Library", "No 3D assets yet") if any(a in v for v in J["fr"]["form"])]
    check("2.2 fr : aucun ancien texte anglais dans le rendu", not anciens_fr, str(anciens_fr))
    check("2.3 fr : dialogues de renommage et de suppression", J["fr"]["dial"] == [
        ["saisir", "Renommer ce rendu 3D :", "Renommer|Renommer"], ["confirmer", "Supprimer définitivement ce rendu 3D ?", ""]],
        str(J["fr"]["dial"]))
    check("2.4 en : dialogues de renommage et de suppression", J["en"]["dial"] == [
        ["saisir", "Rename this 3D render:", "Rename|Rename"], ["confirmer", "Permanently delete this 3D render?", ""]],
        str(J["en"]["dial"]))
    check("2.5 refus de génération dit dans la langue, motif du serveur gardé",
          J["fr"]["alertes"] == ["Génération 3D refusée : MOTIF"] and J["en"]["alertes"] == ["3D generation refused: MOTIF"],
          str([J["fr"]["alertes"], J["en"]["alertes"]]))
    for lang, att in (("fr", ["Entrée", "Vue 1", "Vue 4", "Réponse", "Chaîne · tripo", "Nouvel asset", "…génération"]),
                      ("en", ["Input", "View 1", "View 4", "Response", "Pipeline · tripo", "New asset", "…generating"])):
        g = J[lang]["graphe"]
        manque = [a for a in att if not any(a == v or a in v for v in g)]
        check(f"2.6 {lang} graphe traduit", not manque, str(manque))

print("\n[3] DzOptimize et __dzPrint3d joués en anglais")
JEU = PRELUDE + r"""
LANG="en";var H=[],hi=0,EFF=[],DIAL=[],ALERTES=[],CALLS=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};function DzLod(){return null}function DzTex(){return null}
function fetch(u,o){o=o||{};CALLS.push(u);var js=u.indexOf("/optimize")>=0?{before:{tris:12000},after:{tris:3000},reduction_pct:75,preset:"game",created_at:"t"}
  :u.indexOf("from-assets3d")>=0?{dossier:"C:/p",triangles:3000}:{};return Promise.resolve({ok:true,json:function(){return Promise.resolve(js)}})}
window.__dzDialogue={saisir:function(m,o){DIAL.push(["saisir",m,o.titre,o.ok]);return Promise.resolve("80")},
  confirmer:function(m){DIAL.push(["confirmer",m]);return Promise.resolve(false)}};window.alert=function(m){ALERTES.push(m)};
""" + fonction("DzOptFmt") + "\n" + OPT + "\n" + PRINT + r"""
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
(async function(){hi=0;DzOptimize({sh:"j"});EFF.forEach(function(f){f()});for(var i=0;i<10;i++)await new Promise(function(r2){setImmediate(r2)});
  H[2]=true;hi=0;var t=DzOptimize({sh:"j"});
  var o={opts:tout(t).filter(function(n){return n.t==="option"}).map(function(n){return n.p.children}),texte:txt(t)};
  await __dzPrint3d("j");for(var i=0;i<10;i++)await new Promise(function(r2){setImmediate(r2)});o.dial=DIAL;o.alertes=ALERTES;
  console.log(JSON.stringify(o))})().catch(function(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
p = _TMP / "opt.js"
p.write_text(JEU, encoding="utf-8")
r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    K = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:                                                    # noqa: BLE001
    K = {"erreur": r.stdout[-400:] + r.stderr[-800:]}
check("3.0 DzOptimize et __dzPrint3d s'exécutent sous node", "erreur" not in K and "opts" in K, str(K)[:800])
if "opts" in K:
    check("3.1 en : les huit préréglages traduits", K["opts"] == ["Micro (500)", "Small (1k)", "Prop (2.5k)", "Detailed (5k)",
          "Game Ready (10k)", "Balanced (25k)", "High (50k)", "Ultra (100k)"], str(K["opts"]))
    check("3.2 en : Optimize, Compare/Single, Original / Optimized", all(a in K["texte"] for a in (
        "Optimize", "Optimized GLB", "Single", "Original · 12.0k tris", "Optimized · 3.0k tris")), K["texte"][:400])
    check("3.3 en : la boîte d'impression (taille, titre, Continue, ouverture du slicer)",
          K["dial"][0][0] == "saisir" and K["dial"][0][1].startswith("Target size in mm?") and K["dial"][0][2:] == ["3D printing", "Continue"]
          and K["dial"][1] == ["confirmer", "Print folder written: C:/p (3000 triangles) — open the .3mf in the slicer?"]
          and not K["alertes"], str(K["dial"]) + str(K["alertes"]))

print("\n[4] le maillon de queue")
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzga3d.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("4.1 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout, (r.stdout + r.stderr)[-300:])
avant = AIDE.avant_dzga3d(BUN)
check("4.2 l'inverse avant_dzga3d défait le maillon, et le rejouer redonne le bundle à l'octet",
      M.MARKER not in avant and '"Generate 3D"' in avant and M.appliquer(avant) == BUN)
src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
_po = src_aide[src_aide.index("def avant_dzpose("):]
_po = _po[:_po.index("\ndef ", 5)]
check("4.3 avant_dzpose défait d'abord dzga3d (maillon posé après lui)",
      "bundle = avant_dzga3d(bundle)" in _po and _po.index("avant_dzga3d(") < _po.index("_m.defaire("))
check("4.4 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(BUN, z) for _a, z in M.PAIRES))
check("4.5 le maillon suit dzpose (sonde de son marqueur)", any(j == "/*dzpose*/" for _t, j, _n in M.SONDE_AMONT))
check("4.6 aucun .bak_dzga3d laissé, un seul marqueur", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzga3d")).exists()
      and BUN.count(M.MARKER) == 1)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("4.7 dictionnaire assemblé à jour", r.returncode == 0)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
