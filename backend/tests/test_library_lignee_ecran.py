# -*- coding: utf-8 -*-
"""Bibliotheque, tache #79 PR B (plan-library T5, 03/10/2026) — la LIGNEE dans la fiche d'une image, dans le bundle
LIVRE : DzLignee (et sa vue pure dzLigneeVue) est extrait et EXECUTE sous node (fetch simule).
DECISIONS DE L'UTILISATEUR (03/10) : bloc « Mere / Filles » dans la fiche ; ni comparaison cote a cote ni repli dans la
grille. La relation est portee par la FILLE.
Temoin positif : le bundle de la base (e39d158f) n'a pas la lignee a l'ecran.
Run (depuis backend/) : & $PY tests/test_library_lignee_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzlge_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "e39d158f"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la fiche (DzMetaEditor) mais pas la lignee a l'ecran", r0.returncode == 0 and b"DzMetaEditor" in r0.stdout and b"DzLignee" not in r0.stdout)
check("T2 la lignee suit la note et les tags dans la fiche d'une image (l = la liste chargee, y = ouvrir une fiche)",
      BUN.count("y(Object.assign({},m,md))}}),r.jsx(DzLignee,{m:m,liste:l,ouvrir:y}),r.jsx(DzFiche,") == 1   # #80 PR B : la fiche suit
      and BUN.count("[l,d]=x.useState([]),[u,f]=x.useState([]),[m,y]=x.useState(null)") == 1)


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
            if vu and prof == 0: return BUN[k:i + 1]
        i += 1
    return ""


NOMS = ("dzLigneeVue", "DzLignee")
COUCHE = "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a les deux fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={};
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f,dep){EFF.push(f)}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
async function fetch(u){FETCH.push(u);var q=REP[u];await new Promise(function(s){setTimeout(s,3)});return {ok:!!q,status:q?200:404,json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
async function rendre(props){hi=0;EFF=[];var T=DzLignee(props);var e=EFF.slice();for(var i=0;i<e.length;i++)e[i]();await new Promise(function(s){setTimeout(s,30)});hi=0;EFF=[];return DzLignee(props)}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


R = node("""
var LISTE=[{name:"mere.png",kind:"image"},{name:"moi.png",kind:"image"},{name:"f1.png",kind:"image"}];
REP["/api/library/lignee/moi%20%231.png"]={filename:"moi #1.png",racine:"grand.png",cycle:false,tronque:false,noeud:{filename:"moi.png",relation:"crop"},
  mere:{filename:"mere.png",relation:"upscale"},filles:[{filename:"f1.png",relation:"remove-bg"},{filename:"f2.png",relation:"edit"}],enfants:[1,2,3,4]};
var OUV=[];var T=await rendre({m:{name:"moi #1.png",kind:"image"},liste:LISTE,ouvrir:function(i){OUV.push(i.name)}});
R.fetch=FETCH.slice();R.txt=texte(T);
var bt=trouver(T,function(n){return n.t==="button"});R.boutons=bt.map(function(b){return [b.p.title,!!b.p.disabled]});
bt.forEach(function(b){b.p.onClick()});R.ouv=OUV;
R.img=trouver(T,function(n){return n.t==="img"}).map(function(n){return n.p.src});
// pas de lignee : rien
REP["/api/library/lignee/seule.png"]={filename:"seule.png",racine:"seule.png",cycle:false,noeud:{},mere:null,filles:[],enfants:[]};
R.seule=await rendre({m:{name:"seule.png",kind:"image"},liste:[],ouvrir:function(){}});
// un rendu, un son : pas de requete
FETCH=[];R.job=await rendre({m:{name:"x",kind:"image",jobId:"j1"},liste:[],ouvrir:function(){}});R.son=await rendre({m:{name:"a.mp3",kind:"audio"},liste:[],ouvrir:function(){}});R.fetch2=FETCH.length;
// la mere est la video d un rendu ; boucle
REP["/api/library/lignee/sp.png"]={filename:"sp.png",racine:"sp.png",cycle:true,tronque:true,noeud:{relation:"sprite"},mere:{filename:"rendu.mp4",externe:true,job_id:"job-9"},filles:[],enfants:[1,2]};
var T2=await rendre({m:{name:"sp.png",kind:"image"},liste:[],ouvrir:function(){}});R.ext=texte(T2);
R.extBt=trouver(T2,function(n){return n.t==="button"}).map(function(b){return [b.p.title,!!b.p.disabled]});R.extImg=trouver(T2,function(n){return n.t==="img"}).length;
// panne : rien
R.panne=await rendre({m:{name:"inconnu.png",kind:"image"},liste:[],ouvrir:function(){}});
// la racine elle-meme, avec ses filles : pas de ligne « Racine », pas de famille dite
REP["/api/library/lignee/rac.png"]={filename:"rac.png",racine:"rac.png",cycle:false,tronque:false,noeud:{},mere:null,filles:[{filename:"k.png",relation:"crop"}],enfants:[1]};
R.rac=texte(await rendre({m:{name:"rac.png",kind:"image"},liste:[],ouvrir:function(){}}));
R.vue=dzLigneeVue(null,[]);
""")
check("N0 sous node : la fiche s'execute", R is not None)
if R:
    check("N1 UNE requete, au nom ENCODE (espace, #), vers la route de lignee", R["fetch"] == ["/api/library/lignee/moi%20%231.png"], str(R["fetch"]))
    check("N2 « Mere » (avec la relation de l'image ouverte : crop) et « Filles (2) » (avec la leur) ; racine et famille dites",
          "Mère" in R["txt"] and "mere.png — crop" in R["txt"] and "Filles (2)" in R["txt"] and "f1.png — remove-bg" in R["txt"]
          and "f2.png — edit" in R["txt"] and "Racine : grand.png · 4 descendants sous la racine" in R["txt"], R["txt"])
    check("N3 une vignette de la liste chargee OUVRE sa fiche ; une absente est desactivee et le DIT ; chaque bouton a un title",
          R["ouv"] == ["mere.png", "f1.png"] and R["boutons"][2][1] is True and "pas dans la liste chargée" in R["boutons"][2][0]
          and all(b[0] for b in R["boutons"]) and R["boutons"][0][1] is False, str(R["boutons"]))
    check("N4 vignettes = l'image servie par /api/images (nom encode)", R["img"] == ["/api/images/mere.png", "/api/images/f1.png", "/api/images/f2.png"], str(R["img"]))
    check("N5 sans mere ni filles : rien ; un rendu ou un son : rien, et AUCUNE requete ; une panne (404) : rien",
          R["seule"] is None and R["job"] is None and R["son"] is None and R["fetch2"] == 0 and R["panne"] is None and R["vue"] is None)
    check("N6 la mere VIDEO d'un rendu : 🎬, non cliquable, le title dit le rendu ; la boucle et la liste tronquee sont DITES",
          "rendu.mp4 — sprite" in R["ext"] and "🎬" in R["ext"] and R["extImg"] == 0 and R["extBt"][0][1] is True and "rendu job-9" in R["extBt"][0][0]
          and "↺ boucle dans la lignée" in R["ext"] and "(liste tronquée)" in R["ext"], R["ext"] + str(R["extBt"]))
    check("N7 la racine elle-meme : ses filles, mais ni ligne « Racine » ni famille (rien a dire)", "Filles (1)" in R["rac"] and "Racine" not in R["rac"] and "descendant" not in R["rac"], R["rac"])
    # (mutant equivalent documente : sans le test R.ok, un corps d'erreur n'a ni mere ni filles -> rien n'est affiche non plus)

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and BUN.count("DzTracks") == 181
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
