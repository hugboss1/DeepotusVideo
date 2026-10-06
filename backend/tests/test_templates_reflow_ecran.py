# -*- coding: utf-8 -*-
"""Plan-templates T2 (tache #73 du suivi, PR B, 03/10/2026) — « Rejouer en … » dans la galerie Templates, dans le bundle
LIVRE : le composant (couche du maillon montage) est extrait et EXECUTE sous node, fetch et dessin du schema (gm)
remplaces par des doublures qui notent tout.
DECISIONS DE L'UTILISATEUR (03/10) : copie par format depuis la galerie ; APERCU (avant / apres) et AVERTISSEMENTS avant
d'enregistrer ; le gabarit d'origine ne change pas.
Temoin positif : le bundle de la base (f689d4e2) n'a pas la rangee « Rejouer en ».
Run (depuis backend/) : & $PY tests/test_templates_reflow_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzrfe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "f689d4e2"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la galerie et son groupe « New: » mais pas « Rejouer en »", r0.returncode == 0
      and b'children:"New:"' in r0.stdout and b"DzReflowBar" not in r0.stdout)
APPEL = ('onClick:()=>l(A),children:A},A))]}),r.jsx(DzReflowBar,{tpl:u,onSaved:function(id){a(function(w){return w+1});'
         'setTimeout(function(){n(id)},200)}}),')   # #76 PR H : l'import Figma suit, dans la meme rangee
k = BUN.find('children:"New:"')
check("T2 la rangee est posee dans la barre de la galerie, juste apres « New: » ; une copie recharge la liste et se selectionne",
      BUN.count(APPEL) == 1 and 0 <= k < BUN.find(APPEL) < k + 400 and BUN.count("r.jsx(DzReflowBar,") == 1)


def fonction(nom):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = BUN.find("){", k) + 1, 0, None, False
    while i < len(BUN):
        c_ = BUN[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k - 6 if BUN[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


COUCHE = fonction("dzFormatDe") + "\n" + fonction("DzReflowBar")
check("T3 la couche livree a le composant et la lecture du format (une fois chacun)", BUN.count("function DzReflowBar(") == 1
      and BUN.count("function dzFormatDe(") == 1 and "function DzReflowBar(" in COUCHE)

HARNAIS = r"""
var H=[],hi=0,J=[],REP={},SAUVE=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};var K="K";var gm="Schema";
globalThis.fetch=async function(u,o){var m=String(o&&o.method||"GET"),b=o&&o.body?JSON.parse(o.body):null;J.push(["fetch",m,u,b]);
  var r=REP[m+" "+u]||{s:404,d:{detail:"inconnu"}};return {ok:r.s<300,status:r.s,json:async function(){return r.d}}};
var TPL={id:"tpl_hstack",name:"Dialogue",canvas:{width:1080,height:1920},regions:[{id:"g"},{id:"d"}]};
var APRES={canvas:{width:1920,height:1080},regions:[{id:"g2"},{id:"d2"}]};
var T=null;function rendre(t){hi=0;T=DzReflowBar({tpl:t===undefined?TPL:t,onSaved:function(id){SAUVE.push(id)}});return T}
async function attendre(){for(var i=0;i<15;i++)await new Promise(function(r){setImmediate(r)})}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;
  if(Array.isArray(c))c.forEach(function(z){trouver(z,f,acc)});else if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function boutons(){return trouver(T,function(n){return n.t==="K"})}
function bouton(txt){return boutons().find(function(b){return b.p.children===txt})}
function apercu(){return trouver(T,function(n){return n.p&&n.p.className==="dz-reflow-apercu"})[0]||null}
function msg(){var s=trouver(T,function(n){return n.t==="span"});return s.length>1?s[1].p.children:null}
"""


def node(corps):
    f = _TMP / f"r{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    try:
        p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except subprocess.TimeoutExpired:
        print("   (node) suspendu plus de 60 s")
        return None
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


R = node("""
R.fmt=[dzFormatDe({width:1080,height:1920}),dzFormatDe({width:1920,height:1080}),dzFormatDe({width:1080,height:1350}),dzFormatDe({width:720,height:1280}),dzFormatDe(null)];
rendre();R.lbl=T.p.children[0].p.children;R.btn=boutons().map(function(b){return [b.p.children,b.p.title]});
R.vide=[rendre(null),rendre({id:"x",name:"x"})];
var ATYP={width:720,height:1280};rendre({id:"y",name:"y",canvas:ATYP,regions:[]});R.atyp=boutons().map(function(b){return b.p.children});
REP["GET /api/layout-templates/tpl_hstack/reflow?format=16%3A9"]={s:200,d:{template:APRES,warnings:["L'avatar « Avatar A » passe de 9:16 à 1:1 : ses rendus épinglés seront régénérés (payants)."]}};
H=[];J=[];rendre();bouton("16:9").p.onClick();await attendre();rendre();var A=apercu();
R.get=J.slice();var schemas=trouver(A,function(n){return n.t==="Schema"});R.schemas=schemas.map(function(s){return s.p.canvas.width+"x"+s.p.canvas.height});
var titres=trouver(A,function(n){return n.p&&typeof n.p.children==="string"&&/^(Avant|Après) /.test(n.p.children)}).map(function(n){return n.p.children});R.titres=titres;
R.avert=trouver(A,function(n){return n.p&&n.p.className==="dz-reflow-avert"})[0].p.children.map(function(z){return z.p.children});
R.titreA=trouver(A,function(n){return n.p&&typeof n.p.children==="string"&&n.p.children.indexOf("Réagencer")===0})[0].p.children;
R.ab=[bouton("Annuler").p.title,bouton("Enregistrer la copie").p.title];
bouton("Annuler").p.onClick();rendre();R.ferme={ap:apercu(),post:J.filter(function(z){return z[1]==="POST"}).length};
bouton("16:9").p.onClick();await attendre();rendre();
REP["POST /api/layout-templates/tpl_hstack/reflow"]={s:200,d:{template_id:"tpl_user_ab12cd34",name:"Dialogue (16:9)"}};
J=[];bouton("Enregistrer la copie").p.onClick();await attendre();rendre();R.post={j:J.slice(),sauve:SAUVE.slice(),ap:apercu(),msg:msg()};
""")
check("E0 sous node : la rangee s'execute", R is not None)
if R:
    check("E1 le format du gabarit se lit sur sa toile (les quatre formats de l'app ; une toile atypique : aucun)",
          R["fmt"] == ["9:16", "16:9", "4:5", None, None], str(R["fmt"]))
    check("E2 « Rejouer en : » propose les TROIS autres formats, chacun avec un title qui dit qu'une COPIE est faite et que l'origine ne change pas",
          R["lbl"] == "Rejouer en :" and [b[0] for b in R["btn"]] == ["16:9", "1:1", "4:5"]
          and all("COPIE" in b[1] and "« Dialogue »" in b[1] and "ne change pas" in b[1] for b in R["btn"]), str(R["btn"]))
    check("E3 sans gabarit choisi (ou sans toile) : rien ; toile atypique : les quatre formats", R["vide"] == [None, None]
          and R["atyp"] == ["9:16", "16:9", "1:1", "4:5"], f"{R['vide']} {R['atyp']}")
    check("E4 l'APERCU est demande au serveur (GET, format encode) — rien n'est enregistre a ce stade",
          R["get"] == [["fetch", "GET", "/api/layout-templates/tpl_hstack/reflow?format=16%3A9", None]], str(R["get"]))
    check("E5 AVANT / APRES en schema (le dessin de la galerie), titres avec les formats", R["schemas"] == ["1080x1920", "1920x1080"]
          and R["titres"] == ["Avant (9:16)", "Après (16:9)"] and R["titreA"] == "Réagencer « Dialogue » en 16:9", f"{R['schemas']} {R['titres']}")
    check("E6 les AVERTISSEMENTS du serveur sont affiches, un par ligne (avatar HeyGen : rendus repayes)",
          R["avert"] == ["⚠ L'avatar « Avatar A » passe de 9:16 à 1:1 : ses rendus épinglés seront régénérés (payants)."], str(R["avert"]))
    check("E7 « Annuler » et « Enregistrer la copie » ont un title ; Annuler ferme SANS rien enregistrer",
          "sans rien enregistrer" in R["ab"][0] and "NOUVEAU gabarit" in R["ab"][1] and R["ferme"] == {"ap": None, "post": 0}, f"{R['ab']} {R['ferme']}")
    check("E8 « Enregistrer la copie » : POST {format}, la galerie recharge et selectionne la copie, l'apercu se ferme, message",
          R["post"]["j"] == [["fetch", "POST", "/api/layout-templates/tpl_hstack/reflow", {"format": "16:9"}]] and R["post"]["sauve"] == ["tpl_user_ab12cd34"]
          and R["post"]["ap"] is None and R["post"]["msg"] == "Copie « Dialogue (16:9) » créée.", str(R["post"]))

R = node("""
REP["GET /api/layout-templates/tpl_hstack/reflow?format=1%3A1"]={s:400,d:{detail:"Toile illisible (canvas.width / canvas.height)."}};
rendre();bouton("1:1").p.onClick();await attendre();rendre();R.refus={ap:apercu(),msg:msg()};
REP["GET /api/layout-templates/tpl_hstack/reflow?format=4%3A5"]={s:200,d:{template:APRES,warnings:[]}};
H=[];rendre();bouton("4:5").p.onClick();await attendre();rendre();
R.sans=trouver(apercu(),function(n){return n.p&&n.p.className==="dz-reflow-avert"})[0].p.children;
REP["POST /api/layout-templates/tpl_hstack/reflow"]={s:400,d:{detail:"Template missing required field: name"}};
bouton("Enregistrer la copie").p.onClick();await attendre();rendre();R.postKo={ap:!!apercu(),msg:msg(),sauve:SAUVE.length};
H=[];J=[];REP["GET /api/layout-templates/tpl_hstack/reflow?format=16%3A9"]={s:200,d:{template:APRES,warnings:[]}};rendre();
var b=bouton("16:9");var p1=b.p.onClick(),p2=b.p.onClick();await p1;await p2;await attendre();R.double=J.length;
H=[];rendre();bouton("16:9").p.onClick();await attendre();rendre();var A=apercu();A.p.onClick({target:A,currentTarget:A});rendre();R.fond=apercu();
H=[];rendre();bouton("16:9").p.onClick();await attendre();rendre();A=apercu();A.p.onClick({target:{},currentTarget:A});rendre();R.dedans=!!apercu();
""")
check("E9 sous node : les cas limites s'executent", R is not None)
if R:
    check("E10 refus du serveur a l'apercu : SA phrase, pas d'apercu", R["refus"] == {"ap": None, "msg": "Toile illisible (canvas.width / canvas.height)."}, str(R["refus"]))
    check("E11 sans avertissement : c'est DIT (les cases suivent la toile, les elements gardent leurs proportions)",
          isinstance(R["sans"], str) and "Aucun avertissement" in R["sans"], str(R["sans"]))
    check("E12 enregistrement refuse : SA phrase, l'apercu reste ouvert, rien n'est selectionne", R["postKo"] == {"ap": True,
          "msg": "Template missing required field: name", "sauve": 0}, str(R["postKo"]))
    check("E13 deux clics d'affilee : un seul apercu demande ; un clic sur le FOND ferme l'apercu, un clic DEDANS non",
          R["double"] == 1 and R["fond"] is None and R["dedans"] is True, f"{R['double']} {R['fond']} {R['dedans']}")

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 180, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 180
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
