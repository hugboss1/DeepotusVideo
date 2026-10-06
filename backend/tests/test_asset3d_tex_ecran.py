# -*- coding: utf-8 -*-
"""T105 B (plan-moteurs-3d T4, P3) — l'export des textures dans la carte 3D du hub, dans le bundle LIVRÉ : DzTex est
extrait et EXÉCUTÉ sous node (hooks minimaux ; fetch, URL et document en doublures qui notent tout). Vérifié : la
greffe suit DzLod dans DzOptimize ; conventions et résolutions viennent de l'inventaire du SERVEUR ; un maillage nu
grise le bouton et dit pourquoi ; un refus d'inventaire (GLB compressé) est DIT ; le POST porte la convention et la
résolution ; un refus d'export est dit ; un succès télécharge `<job>_<convention>.zip` ; les cartes qui seront cuites
sont annoncées. Témoin positif : le bundle de la base (c2a1f7f3) n'a pas DzTex.
Run (depuis backend/) : & $PY tests/test_asset3d_tex_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dztexe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "c2a1f7f3:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas DzTex", r0.returncode == 0 and b"function DzTex(" not in r0.stdout)


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


check("L1 DzTex défini une fois, greffé une fois, juste après DzLod dans DzOptimize",
      BUN.count("function DzTex(") == 1 and 'r.jsx(DzLod,{sh:sh},"lod"+sh),r.jsx(DzTex,{sh:sh},"tex"+sh),' in fonction("DzOptimize"))
check("L2 aucune convention recopiée dans le bundle", "unity_urp" not in fonction("DzTex") and "T_" not in fonction("DzTex"))

HARNAIS = r"""
var H=[],hi=0,EFF=[],CALLS=[],REP={},DL=[],TIM=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};
var URL={createObjectURL:function(b){return "blob:"+b.taille},revokeObjectURL:function(){}};
var document={createElement:function(){var a={click:function(){DL.push({href:a.href,download:a.download})}};return a}};
function setTimeout(f){TIM.push(f)}
function fetch(u,o){o=o||{};CALLS.push({u:u,m:o.method||"GET",b:o.body?JSON.parse(o.body):null});
  var rep=REP[(o.method||"GET")+" "+u]||{st:404,js:{detail:"?"}};
  return Promise.resolve({ok:rep.st<400,status:rep.st,json:function(){return Promise.resolve(rep.js)},
    blob:function(){return Promise.resolve({taille:rep.taille||0})}})}
"""
MOTEUR = r"""
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
async function tick(){for(var i=0;i<10;i++)await new Promise(function(res){setImmediate(res)})}
async function monter(sh){H=[];EFF=[];hi=0;var t=DzTex({sh:sh});EFF.forEach(function(f){f()});await tick();hi=0;return DzTex({sh:sh})}
function rend(sh){hi=0;return DzTex({sh:sh})}
var INV={file:"model.v2.glb",materiaux:[{index:0,nom:"peau",canaux:{basecolor:{px:[64,64]}}}],manquants:["ao","emissive","orm"],
  resolutions:[512,1024,2048,4096],conventions:["standard","blender","unity_urp","unreal","godot"]};
var OUT={};
(async function(){
  REP["GET /api/assets/3d/j1/textures"]={st:200,js:INV};
  var t=await monter("j1");
  var sels=tout(t).filter(function(n){return n.t==="select"});
  OUT.conv=kids(sels[0]).map(function(o){return o.p.value});OUT.res=kids(sels[1]).map(function(o){return txt(o)});OUT.resVal=sels[1].p.value;
  var go=tout(t).filter(function(n){return n.t==="button"})[0];OUT.go=[txt(go),go.p.disabled,go.p.title];
  OUT.cuites=txt(t).indexOf("cuites : ao, emissive, orm")>=0;
  sels[0].p.onChange({target:{value:"unreal"}});sels[1].p.onChange({target:{value:"1024"}});t=rend("j1");
  REP["POST /api/assets/3d/j1/textures"]={st:400,js:{detail:"model.v2.glb ne porte aucune texture : rien à exporter."}};
  tout(t).filter(function(n){return n.t==="button"})[0].p.onClick();await tick();t=rend("j1");
  OUT.post=CALLS.filter(function(c){return c.m==="POST"}).map(function(c){return JSON.stringify(c.b)});
  OUT.errExport=txt(t);OUT.dlApresRefus=DL.length;
  REP["POST /api/assets/3d/j1/textures"]={st:200,taille:1234};
  tout(t).filter(function(n){return n.t==="button"})[0].p.onClick();await tick();
  OUT.dl=DL.slice();
  REP["GET /api/assets/3d/nu/textures"]={st:200,js:Object.assign({},INV,{materiaux:[{index:0,nom:"x",canaux:{}}]})};
  var tn=await monter("nu");var gn=tout(tn).filter(function(n){return n.t==="button"})[0];
  OUT.nu=[gn.p.disabled,gn.p.title,txt(tn).indexOf("cuites")>=0];
  REP["GET /api/assets/3d/dr/textures"]={st:400,js:{detail:"model.glb exige l'extension KHR_draco_mesh_compression"}};
  OUT.draco=txt(await monter("dr"));
  REP["GET /api/assets/3d/vide/textures"]={st:404,js:{detail:""}};
  OUT.vide=await monter("vide");
  console.log(JSON.stringify(OUT));
})().catch(function(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
p = _TMP / "tex.js"
p.write_text(HARNAIS + fonction("DzTex") + MOTEUR, encoding="utf-8")
r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:
    o = {"erreur": r.stdout[-400:] + r.stderr[-800:]}
check("U0 DzTex livré s'exécute sous node", "erreur" not in o and "conv" in o, str(o)[:700])
if "conv" in o:
    check("U1 conventions et résolutions de l'inventaire du SERVEUR, 2048 par défaut",
          o["conv"] == ["standard", "blender", "unity_urp", "unreal", "godot"] and o["res"][0] == "512 px" and o["resVal"] == "2048", str(o))
    check("U2 bouton actif, son infobulle dit quel fichier part", o["go"][0] == "↓ Textures" and not o["go"][1]
          and "model.v2.glb" in o["go"][2], str(o["go"]))
    check("U3 les cartes qui seront cuites sont annoncées", o["cuites"] is True)
    check("U4 le POST porte la convention et la résolution choisies", o["post"][:1] == ['{"naming":"unreal","resolution":1024}'], str(o["post"]))
    check("U5 un refus d'export est DIT, rien n'est téléchargé", "ne porte aucune texture" in o["errExport"] and o["dlApresRefus"] == 0, o["errExport"][-160:])
    check("U6 un succès télécharge <job>_<convention>.zip", o["dl"] == [{"href": "blob:1234", "download": "j1_unreal.zip"}], str(o["dl"]))
    check("U7 maillage nu : bouton grisé, la raison en infobulle, rien d'annoncé comme cuit",
          o["nu"][0] is True and "aucune texture" in o["nu"][1] and o["nu"][2] is False, str(o["nu"]))
    check("U8 un refus d'inventaire (GLB compressé) est DIT", "Textures : " in o["draco"] and "KHR_draco_mesh_compression" in o["draco"], o["draco"])
    check("U9 rien du tout quand l'inventaire est vide de sens (404 sans détail)", o["vide"] is None, str(o["vide"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
