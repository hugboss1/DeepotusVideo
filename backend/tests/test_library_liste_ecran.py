# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR B (plan-library T15 + decision du 04/10/2026) — la LISTE triable, les tris REPARES,
l'ETAT d'un projet et les VERROUS des panneaux, a l'ecran, dans le bundle LIVRE (composants executes sous node).
DECISION DE L'UTILISATEUR (04/10) : « les deux » — une vue liste des assets ET l'etat du projet regarde.
Trouves en route et gardes ici : « Most recent » ne triait rien ; « Size » comparait des chaines formatees ; un double
clic sur un meme rendu passait deux fois dans Rejouer, Restaurer, Vider et Jeter (verrou d'etat lu dans la fermeture).
Temoin positif : le bundle de la base (db3cf49b) trie la taille par parseFloat et n'a ni liste ni etat.
Run (depuis backend/) : & $PY tests/test_library_liste_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzlie_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "db3cf49b"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
TRI_AVANT = 'else if(Lsort==="size")a2.sort((p,q2)=>(parseFloat(q2&&q2.size)||0)-(parseFloat(p&&p.size)||0));return a2;'
check("T1 temoin : la base trie la taille par parseFloat et n'a ni liste ni etat de projet",
      r0.returncode == 0 and TRI_AVANT.encode() in r0.stdout and b"DzListe" not in r0.stdout and b"DzEtatProjet" not in r0.stdout)
check("T2 la grille devient une liste quand la bascule le dit ; les tris taille et recent sont branches ; l'etat de la vue est memorise ; la liste porte le brut",
      BUN.count('dzVue==="liste"?r.jsx(DzListe,{items:q,ouvrir:function(C){C.url&&y(C)}}):r.jsx("div",{style:{display:"grid"') == 1
      and BUN.count('else if(Lsort==="size")a2.sort(dzCmpTaille);else if(Lsort==="recent")a2.sort(dzCmpRecent);return a2;') == 1 and TRI_AVANT not in BUN
      and BUN.count("[dzVue,dzVues]=x.useState(dzVueLue()),") == 1 and BUN.count("r.jsx(DzOutilsBiblio,{vue:dzVue,setVue:dzVues})") == 1
      and BUN.count('octets:S.size_kb!=null?S.size_kb*1024:null,mtime:S.mtime||0,larg:S.width||null,haut:S.height||null,licence:S.licence||""}));') == 1
      # la barre Projet : le bouton « ▦ État » bascule le panneau d'etat du projet regarde
      and BUN.count('if(f&&f.id&&etatOn)ch.push(r.jsx(DzEtatProjet,{pid:f.id},"etat"));') == 1
      and BUN.count('ch.push(bouton("▦ État","Ce qui, dans ce projet, est monté, publié, imprimé — ou inutilisé",function(){setEtatOn(!etatOn)},etatOn));') == 1)


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


NOMS = ("dzOctets", "dzDuree", "dzOctetsDe", "dzCmpTaille", "dzCmpRecent", "dzListeVal", "dzListeTri", "DzListe", "DzEtatProjet", "dzVueLue", "dzVueEcrite",
        "DzOutilsBiblio", "dzCorbVue", "DzCorbeille", "dzNettVue", "dzNettAuto", "DzNettoyage", "dzFicheLignes", "DzFiche")
k = BUN.find("var DZ_LISTE_COLS=")
COLS = BUN[k:BUN.find("]];", k) + 3] if k >= 0 else ""
COUCHE = COLS + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a ses fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS) and COLS != "")

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={},DIAL=[],DREP=true,STO={};
var localStorage={getItem:function(k){return k in STO?STO[k]:null},setItem:function(k,v){STO[k]=String(v)}};
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f){EFF.push(f)},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{confirmer:async function(m,o){DIAL.push([m,o]);return DREP}}};
async function fetch(u,o){var m=o&&o.method||"GET";FETCH.push([u,m,o&&o.body?JSON.parse(o.body):null]);var q=REP[m+" "+u];
  await new Promise(function(s){setTimeout(s,5)});if(typeof q==="function")q=q();
  return {ok:!!q&&!q.__ko,status:q&&q.__ko?q.__ko:(q?200:404),json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
function boutons(T,txt){return trouver(T,function(n){return n.t==="K"&&n.p.children===txt})}
async function attendre(){await new Promise(function(s){setTimeout(s,50)})}
function monteur(F){return {rendu:function(p){hi=0;EFF=[];return F(p||{})},monter:async function(p){hi=0;EFF=[];F(p||{});var e=EFF.slice();e.forEach(function(f){f()});
  await attendre();hi=0;EFF=[];return F(p||{})}}}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-600:])
        return None


R = node("""
var L=[{name:"b.png",kind:"image",size:"512.0 KB",mtime:100,url:"/i/b"},{name:"a.png",kind:"image",octets:2.4*1048576,size:"2.4 MB",mtime:300,url:"/i/a"},
  {name:"c.png",kind:"image",size:"9 B",mtime:200,url:"/i/c"},{name:"rendu",kind:"render",size:"",url:"/v/r"}];
R.taille=L.slice().sort(dzCmpTaille).map(function(z){return z.name});R.recent=L.slice().sort(dzCmpRecent).map(function(z){return z.name});
R.octets=[dzOctetsDe({size:"1.5 MB"}),dzOctetsDe({size:"3 Ko"}),dzOctetsDe({size:"x"}),dzOctetsDe({octets:7,size:"1 MB"})];
R.tri=[dzListeTri(L,{col:"nom"}).map(function(z){return z.name}),dzListeTri(L,{col:"octets",desc:true}).map(function(z){return z.name}),dzListeTri(L,{col:""})===L];
var OUV=[];var M=monteur(DzListe);var T=M.rendu({items:L,ouvrir:function(z){OUV.push(z.name)}});
var th=trouver(T,function(n){return n.t==="th"&&n.p.title});R.cols=th.map(function(h){return h.p.children});R.titres=th.every(function(h){return!!h.p.title});
th[2].p.onClick();var T2=M.rendu({items:L,ouvrir:function(){}});R.ordre=trouver(T2,function(n){return n.t==="tr"&&n.p.onClick}).map(function(t){return trouver(t,function(n){return n.t==="td"})[1].p.children});
R.fleche=trouver(T2,function(n){return n.t==="th"&&n.p.title})[2].p.children;
trouver(T2,function(n){return n.t==="th"&&n.p.title})[2].p.onClick();var T3=M.rendu({items:L,ouvrir:function(){}});
R.ordre2=trouver(T3,function(n){return n.t==="tr"&&n.p.onClick}).map(function(t){return trouver(t,function(n){return n.t==="td"})[1].p.children});
trouver(T3,function(n){return n.t==="tr"&&n.p.onClick})[0].p.onClick();
var T4=M.rendu({items:L,ouvrir:function(z){OUV.push(z.name)}});trouver(T4,function(n){return n.t==="tr"&&n.p.onClick})[0].p.onClick();R.ouv=OUV;
R.img=trouver(T4,function(n){return n.t==="img"}).length;
// la bascule grille / liste
var POSE=[];var Tb=monteur(DzOutilsBiblio).rendu({vue:"grille",setVue:function(v){POSE.push(v)}});
var bl=trouver(Tb,function(n){return n.t==="button"&&n.p.children==="☰ Liste"})[0];R.blTitre=bl.p.title;bl.p.onClick();R.pose=POSE;R.sto=STO.dz_biblio_vue;R.lue=dzVueLue();
R.sansBascule=trouver(monteur(DzOutilsBiblio).rendu({}),function(n){return n.t==="button"&&n.p.children==="☰ Liste"}).length;
""")
check("L0 sous node : la liste s'execute", R is not None)
if R:
    check("L1 tri TAILLE par octets reels (2.4 MB avant 512 KB, plus d'ordre de chaine) ; tri RECENT par date brute ; dzOctetsDe lit B / Ko / MB et prefere l'octet brut",
          R["taille"] == ["a.png", "b.png", "c.png", "rendu"] and R["recent"] == ["a.png", "c.png", "b.png", "rendu"]
          and R["octets"] == [1.5 * 1048576, 3072, 0, 7], str(R["taille"]) + str(R["recent"]) + str(R["octets"]))
    check("L2 la liste : dix colonnes avec un title, un clic trie (taille DECROISSANTE d'abord, fleche), un second clic inverse ; une ligne ouvre la fiche ; vignette pour une image",
          R["cols"] == ["Nom", "Source", "Taille", "Date", "Dimensions", "Tags", "Note", "Favori", "Licence", "Teinte"] and R["titres"]
          and R["ordre"] == ["a.png", "b.png", "c.png", "rendu"] and R["fleche"] == "Taille ▾" and R["ordre2"] == ["rendu", "c.png", "b.png", "a.png"]
          and R["ouv"] == ["rendu"] and R["img"] == 3 and R["tri"][0] == ["a.png", "b.png", "c.png", "rendu"] and R["tri"][2] is True, str(R))
    check("L3 la bascule « ☰ Liste » (title) pose la vue et la MEMORISE ; sans setVue (ancien appel), pas de bascule",
          "liste triable" in R["blTitre"] and R["pose"] == ["liste"] and R["sto"] == "liste" and R["lue"] == "liste" and R["sansBascule"] == 0, str(R))

R = node("""
REP["GET /api/library/projets/pj%201/etat"]={id:"pj 1",n:3,monte:[{ref:"a.png",kind:"image"}],publie:[{ref:"r1",kind:"render"}],imprime:[],
  inutilise:[{ref:"b.png",kind:"image"},{ref:"c.mp3",kind:"audio"}]};
var T=await monteur(DzEtatProjet).monter({pid:"pj 1"});R.txt=texte(T);R.fetch=FETCH.slice();
R.cols=trouver(T,function(n){return n.p&&n.p.title&&n.t==="div"}).map(function(d){return d.p.title});
var gros={id:"g",n:15,monte:[],publie:[],imprime:[],inutilise:Array.from({length:15},function(_,i){return{ref:"f"+i,kind:"image"}})};
REP["GET /api/library/projets/g/etat"]=gros;var TG=await monteur(DzEtatProjet).monter({pid:"g"});R.gros=texte(TG);
R.lignes=trouver(TG,function(n){return n.t==="div"&&/^f\d+$/.test(String(n.p.children))}).length;
R.panne=texte(await monteur(DzEtatProjet).monter({pid:"absent"}));
""")
check("P0 sous node : l'etat du projet s'execute", R is not None)
if R:
    check("P1 quatre colonnes avec compteurs (Monte, Publie, Imprime, Inutilise), un title chacune ; UNE requete au projet encode ; rendu 🎬, son 🔊",
          R["fetch"] == [["/api/library/projets/pj%201/etat", "GET", None]] and "Monté (1)" in R["txt"] and "Publié (1)" in R["txt"] and "Imprimé (0)" in R["txt"]
          and "Inutilisé (2)" in R["txt"] and "🎬 r1" in R["txt"] and "🔊 c.mp3" in R["txt"] and len(R["cols"]) == 4, R["txt"])
    check("P2 au-dela de 12 : « … et 3 autre(s) » ; une panne est DITE", "… et 3 autre(s)" in R["gros"] and R["lignes"] == 12 and "État indisponible : HTTP 404" in R["panne"], R["panne"])

R = node("""
// les VERROUS : un double clic sur un MEME rendu ne passe qu'une fois
var C={elements:[{id:"e1",type:"image",nom:"x.png",jete_le:new Date().toISOString(),octets:10,ancien:false,restaurable:true}],octets:10,anciens:0,jours:30};
REP["GET /api/library/corbeille"]=C;REP["POST /api/library/corbeille/restaurer"]={restaure:"x.png",renomme:false};REP["POST /api/library/corbeille/vider"]={vides:1,octets:10};
var M=monteur(DzCorbeille);var T=await M.monter();var b=boutons(T,"Restaurer")[0];FETCH=[];var p1=b.p.onClick(),p2=b.p.onClick();await attendre();await attendre();
R.rest=FETCH.filter(function(f){return f[1]==="POST"}).length;
var T2=M.rendu();var v=boutons(T2,"Vider la corbeille")[0];FETCH=[];DIAL=[];v.p.onClick();v.p.onClick();await attendre();await attendre();
R.vid=[FETCH.filter(function(f){return f[1]==="POST"}).length,DIAL.length];
var N={poids:{},doublons:[{sha256:"h",octets:4,en_trop:1,fichiers:[{filename:"a.png",protege:false},{filename:"b.png",protege:false}]}]};
REP["GET /api/library/nettoyage"]=N;REP["POST /api/library/nettoyage/jeter"]={jetes:[{filename:"a.png"}]};var MN=monteur(DzNettoyage);var TN=await MN.monter();
trouver(TN,function(n){return n.t==="input"})[0].p.onChange({target:{checked:true}});var TN2=MN.rendu();var j=boutons(TN2,"Mettre 1 à la corbeille")[0];
FETCH=[];DIAL=[];j.p.onClick();j.p.onClick();await attendre();await attendre();R.jet=[FETCH.filter(function(f){return f[1]==="POST"}).length,DIAL.length];
var F={filename:"g.png",kind:"image",droits:{licence:"x",alerte:false,licences:[]},fichier:{},recette:{origine:"generation",prompt:"p"},
  rejouer:{route:"/api/images/generate",corps:{prompt:"p",n:1},usd:0.003},usages:[]};
REP["GET /api/library/fiche/g.png"]=F;REP["POST /api/images/generate"]={images:["n.png"]};var MF=monteur(DzFiche);var TF=await MF.monter({m:{name:"g.png",kind:"image"}});
var rj=boutons(TF,"Rejouer la recette")[0];FETCH=[];DIAL=[];rj.p.onClick();rj.p.onClick();await attendre();await attendre();
R.rej=[FETCH.filter(function(f){return f[1]==="POST"}).length,DIAL.length];
""")
check("V0 sous node : les verrous s'executent", R is not None)
if R:
    check("V1 un double clic sur un MEME rendu ne passe qu'UNE fois : Restaurer, Vider (un seul dialogue), Jeter des doublons, Rejouer la recette",
          R["rest"] == 1 and R["vid"] == [1, 1] and R["jet"] == [1, 1] and R["rej"] == [1, 1], str(R))
check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 178
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
