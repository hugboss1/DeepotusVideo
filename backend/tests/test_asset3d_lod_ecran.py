# -*- coding: utf-8 -*-
"""T105 (plan-moteurs-3d T3, P2) — la zone LOD de la carte 3D du hub, dans le bundle LIVRÉ : DzLod est extrait et
EXÉCUTÉ sous node (hooks minimaux, fetch en doublure qui note tout). Vérifié : la greffe est DANS DzOptimize, juste
après sa rangée de boutons ; les budgets viennent du serveur (select + pourquoi en infobulle) ; le bouton POSTe
l'usage choisi ; l'erreur du serveur est dite ; chaque niveau dit ses triangles, son IoU, son écart de normales,
« non mesuré » quand il ne l'est pas, « agressif » quand gltfpack a dû forcer ; l'archive n'apparaît qu'avec une
chaîne. Témoin positif : le bundle de la base (c2a1f7f3) n'a pas DzLod.
Run (depuis backend/) : & $PY tests/test_asset3d_lod_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzlode_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "c2a1f7f3:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base a DzOptimize mais pas DzLod", r0.returncode == 0 and b"function DzOptimize(" in r0.stdout
      and b"function DzLod(" not in r0.stdout)


def fonction(nom):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
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


OPT = fonction("DzOptimize")
check("L1 DzLod défini une fois, greffé une fois", BUN.count("function DzLod(") == 1 and BUN.count("r.jsx(DzLod,") == 1)
check("L2 la greffe est DANS DzOptimize, juste après sa rangée de boutons",
      'children:cmp?"▣ Simple":"⇆ Comparer"},"cp"):null]},"row"),r.jsx(DzLod,{sh:sh},"lod"+sh),' in OPT)
check("L3 les budgets ne sont pas recopiés dans le bundle (ils viennent du serveur)",
      "60000" not in fonction("DzLod") and "Mobile / WebGL" not in fonction("DzLod"))

COUCHE = fonction("DzOptFmt") + "\n" + fonction("DzLodNum") + "\n" + fonction("DzLod")

HARNAIS = r"""
var H=[],hi=0,EFF=[],CALLS=[],REP={};
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};
function fetch(u,o){o=o||{};CALLS.push({u:u,m:o.method||"GET",b:o.body?JSON.parse(o.body):null});
  var k=(o.method||"GET")+" "+u;var rep=REP[k]||{st:404,js:{detail:"?"}};
  return Promise.resolve({ok:rep.st<400,status:rep.st,json:function(){return Promise.resolve(rep.js)}})}
"""
MOTEUR = r"""
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
function render(){hi=0;return DzLod({sh:"job1"})}
async function tick(){for(var i=0;i<10;i++)await new Promise(function(res){setImmediate(res)})}
var BUD=[{id:"mobile",label:"Mobile / WebGL",niveaux:[10000,4000,1500],pourquoi:"premier plan sur téléphone"},
         {id:"pc",label:"PC / console",niveaux:[60000,20000,6000],pourquoi:"gros plan"}];
var CH={niveaux:[{niveau:0,file:"lod0.glb",tris:120000,cible:null,perte:{mesure:true,iou_min:1,ecart_normales:0}},
  {niveau:1,file:"lod1.glb",tris:60000,cible:60000,aggressive:false,perte:{mesure:true,iou_min:0.9871,ecart_normales:0.0123}},
  {niveau:2,file:"lod2.glb",tris:9000,cible:6000,aggressive:true,cible_tenue:false,perte:{mesure:false,raison:"glb compressé"}}]};
var OUT={};
(async function(){
  REP["GET /api/assets/3d/job1/lod"]={st:200,js:{chaine:null,budgets:BUD}};
  var t=render();EFF.forEach(function(f){f()});await tick();t=render();
  var sel=tout(t).filter(function(n){return n.t==="select"})[0];
  OUT.options=kids(sel).map(function(o){return [o.p.value,txt(o)]});OUT.titre=sel.p.title;OUT.valeur=sel.p.value;
  OUT.archiveAvant=tout(t).filter(function(n){return n.t==="a"}).length;
  sel.p.onChange({target:{value:"mobile"}});t=render();
  OUT.titreMobile=tout(t).filter(function(n){return n.t==="select"})[0].p.title;
  REP["POST /api/assets/3d/job1/lod"]={st:400,js:{detail:"le premier niveau vise 10000 triangles pour une source de 800 : la chaîne n'allègerait rien."}};
  var go=tout(t).filter(function(n){return n.t==="button"})[0];OUT.go=txt(go);OUT.goTitle=go.p.title;
  go.p.onClick();await tick();t=render();
  OUT.post=CALLS.filter(function(c){return c.m==="POST"}).map(function(c){return c.u+" "+JSON.stringify(c.b)});
  OUT.err=txt(t);
  REP["POST /api/assets/3d/job1/lod"]={st:200,js:CH};
  tout(t).filter(function(n){return n.t==="button"})[0].p.onClick();await tick();t=render();
  OUT.lignes=tout(t).filter(function(n){return typeof n.p.title==="string"&&n.t==="div"&&/^LOD/.test(txt(n))}).map(function(n){return [txt(n),n.p.title]});
  var a=tout(t).filter(function(n){return n.t==="a"})[0];OUT.archive=a&&[a.p.href,txt(a)];
  console.log(JSON.stringify(OUT));
})().catch(function(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
p = _TMP / "lod.js"
p.write_text(HARNAIS + COUCHE + MOTEUR, encoding="utf-8")
r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-400:] + r.stderr[-800:]}
check("U0 DzLod livré s'exécute sous node", "erreur" not in o and "options" in o, str(o)[:700])
if "options" in o:
    check("U1 le select liste les budgets du SERVEUR, « pc » par défaut", o["options"] == [["mobile", "Mobile / WebGL"], ["pc", "PC / console"]]
          and o["valeur"] == "pc", str(o["options"]))
    check("U2 le pourquoi et les niveaux du budget choisi en infobulle", o["titre"] == "gros plan (60000 / 20000 / 6000 tris)"
          and o["titreMobile"].startswith("premier plan sur téléphone"), f"{o['titre']} | {o['titreMobile']}")
    check("U3 pas d'archive tant qu'aucune chaîne n'existe", o["archiveAvant"] == 0)
    check("U4 le bouton dit ce qu'il fait (local, gratuit, perte mesurée)", o["go"] == "⛰ LOD" and "gratuite" in o["goTitle"] and "LOD0" in o["goTitle"], o["goTitle"])
    check("U5 le POST porte l'usage choisi", o["post"][:1] == ['/api/assets/3d/job1/lod {"usage":"mobile"}'], str(o["post"]))
    check("U6 le refus du serveur est DIT tel quel", "n'allègerait rien" in o["err"], o["err"][-200:])
    lg = {l[0].split(" · ")[0]: l for l in o["lignes"]}
    check("U7 trois lignes : LOD0 « source », LOD1 avec IoU et Δn", set(lg) == {"LOD0", "LOD1", "LOD2"}
          and lg["LOD0"][0] == "LOD0 · 120.0k tris · source"
          and lg["LOD1"][0] == "LOD1 · 60.0k tris · IoU 0.987 · Δn 0.012", str(o["lignes"]))
    check("U8 LOD2 non mesuré : DIT dans la ligne, la raison en infobulle ; « agressif » quand gltfpack a forcé ; la cible "
          "manquée est DITE", "IoU non mesuré · Δn non mesuré · agressif · cible 6.0k non tenue" in lg["LOD2"][0]
          and lg["LOD2"][1] == "glb compressé", str(lg["LOD2"]))
    check("U8b une cible tenue ne dit rien de plus", "non tenue" not in lg["LOD1"][0], str(lg["LOD1"]))
    check("U9 l'archive apparaît avec la chaîne, vers /lod-zip", o["archive"] == ["/api/assets/3d/job1/lod-zip", "↓ Archive LOD"], str(o["archive"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
