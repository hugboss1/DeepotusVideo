# -*- coding: utf-8 -*-
"""Bibliotheque, tache #81 PR C (plan-library T9-T11, 03/10/2026) — CORBEILLE, NETTOYAGE et TEINTE a l'ecran, dans le
bundle LIVRE : les composants de la couche sont extraits et EXECUTES sous node (fetch et dialogue maison simules).
DECISIONS DE L'UTILISATEUR (03/10) : la Corbeille restaure, vide a la MAIN (dialogue maison) et SIGNALE ce qui a plus
de 30 jours sans le purger ; le Nettoyage montre poids et doublons exacts, l'utilisateur coche, les copies utilisees sont
grisees, un groupe garde au moins une copie ; la puce « Teinte » filtre ; la fiche montre la pastille ; les Delete disent
la corbeille. Corbeille et Nettoyage sont des PANNEAUX (barre d'outils) : la liste des onglets est epinglee par l'Etabli.
Temoin positif : le bundle de la base (68f50397) n'a ni corbeille ni nettoyage a l'ecran.
Run (depuis backend/) : & $PY tests/test_library_corbeille_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzcoe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "68f50397"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la fiche mais ni corbeille ni nettoyage a l'ecran ; ses Delete disent « Delete »",
      r0.returncode == 0 and b"DzFiche" in r0.stdout and b"DzCorbeille" not in r0.stdout and 'confirmer("Delete cette image ?")'.encode() in r0.stdout)
check("T2 la barre Corbeille / Nettoyage suit la barre des projets ; les trois Delete disent la corbeille ; la grille porte teinte et couleur",
      BUN.count("r.jsx(DzProjetsBar,{f:dzPF,setF:dzPFs}),r.jsx(DzOutilsBiblio,{vue:dzVue,setVue:dzVues}),__dzSrcChips(o,T,dzSF,dzSFs)") == 1
      and BUN.count("à la corbeille ? (restaurable depuis la Corbeille de la Bibliothèque)") == 3 and "Delete cette image ?" not in BUN and "Delete ce son ?" not in BUN
      and BUN.count('fav:!!S.fav,teinte:S.teinte||"",couleur:S.couleur||"",') == 1)


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


NOMS = ("dzOctets", "dzDuree", "dzCorbVue", "DzCorbeille", "dzNettVue", "dzNettAuto", "DzNettoyage", "DzOutilsBiblio",
        "dzMetaFiltre", "dzMetaComptes", "DzMetaChips", "dzFicheLignes", "DzFiche")
COUCHE = "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a ses fonctions (une fois chacune)", all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={},DIAL=[],DREP=true;
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f){EFF.push(f)},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{confirmer:async function(m,o){DIAL.push([m,o]);return DREP}}};
async function fetch(u,o){var m=o&&o.method||"GET";FETCH.push([u,m,o&&o.body?JSON.parse(o.body):null]);var q=REP[m+" "+u];
  await new Promise(function(s){setTimeout(s,3)});if(typeof q==="function")q=q(o&&o.body?JSON.parse(o.body):null);
  return {ok:!!q&&!q.__ko,status:q&&q.__ko?q.__ko:(q?200:404),json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
function boutons(T,txt){return trouver(T,function(n){return n.t==="K"&&n.p.children===txt})}
async function attendre(){await new Promise(function(s){setTimeout(s,40)})}
function monteur(F){return {rendu:function(p){hi=0;EFF=[];return F(p||{})},monter:async function(p){hi=0;EFF=[];F(p||{});var e=EFF.slice();e.forEach(function(f){f()});
  await attendre();hi=0;EFF=[];return F(p||{})}}}
var AUJ=new Date().toISOString(),VIEUX=new Date(Date.now()-40*864e5).toISOString();
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
var C={elements:[{id:"e1",type:"image",nom:"x.png",jete_le:AUJ,octets:2048,ancien:false,restaurable:true},
  {id:"e2",type:"rendu",nom:"Mon rendu",jete_le:VIEUX,octets:5*1048576,ancien:true,restaurable:true},{id:"e3",type:"illisible",nom:"e3",octets:10,ancien:false,restaurable:false}],
  octets:5*1048576+2058,anciens:1,jours:30};
REP["GET /api/library/corbeille"]=C;var M=monteur(DzCorbeille);var T=await M.monter();R.txt=texte(T);
R.restBt=boutons(T,"Restaurer").map(function(b){return [b.p.disabled,b.p.title]});R.anc=trouver(T,function(n){return n.p["data-ancien"]==="1"}).length;
REP["POST /api/library/corbeille/restaurer"]={restaure:"x_restaure.png",type:"image",renomme:true};FETCH=[];
var C2=JSON.parse(JSON.stringify(C));C2.elements.shift();REP["GET /api/library/corbeille"]=C2;
var p1=boutons(M.rendu(),"Restaurer")[0].p.onClick(),p2=boutons(M.rendu(),"Restaurer")[0].p.onClick();await p1;await p2;await attendre();
R.rest=FETCH.slice();R.restMsg=texte(M.rendu());
REP["POST /api/library/corbeille/restaurer"]={__ko:409,detail:"Un rendu porte déjà l’identifiant j"};await boutons(M.rendu(),"Restaurer")[0].p.onClick();await attendre();R.r409=texte(M.rendu());
DREP=false;FETCH=[];DIAL=[];await boutons(M.rendu(),"Vider les anciens (1)")[0].p.onClick();await attendre();R.annule=[DIAL.length,FETCH.length];R.dialAnc=DIAL[0];
DREP=true;REP["POST /api/library/corbeille/vider"]={vides:1,octets:5*1048576};FETCH=[];await boutons(M.rendu(),"Vider les anciens (1)")[0].p.onClick();await attendre();R.viderAnc=FETCH[0];R.vMsg=texte(M.rendu());
FETCH=[];DIAL=[];await boutons(M.rendu(),"Vider la corbeille")[0].p.onClick();await attendre();R.viderTout=FETCH[0];R.dialTout=DIAL[0][0];
REP["GET /api/library/corbeille"]={elements:[],octets:0,anciens:0,jours:30};var V=await monteur(DzCorbeille).monter();R.vide=texte(V);R.videBt=boutons(V,"Vider la corbeille").length;
R.duree=[dzDuree(AUJ),dzDuree(new Date(Date.now()-864e5-1000).toISOString()),dzDuree(VIEUX),dzDuree(null)];
""")
check("C0 sous node : la corbeille s'execute", R is not None)
if R:
    check("C1 la liste : nombre, poids, anciens (« 1 de plus de 30 jours ») ; chaque ligne dit son nom, sa date, son poids ; l'ancienne est SIGNALEE (bordure, « plus de 30 j »)",
          "3 éléments · 5.0 Mo · 1 de plus de 30 jours" in R["txt"] and "x.png" in R["txt"] and "aujourd’hui · 2.0 Ko" in R["txt"]
          and "il y a 40 jours · 5.0 Mo" in R["txt"] and "plus de 30 j" in R["txt"] and R["anc"] == 1, R["txt"])
    check("C2 « Restaurer » a un title, est INACTIF pour une entree illisible ; restaurer : UN appel au double clic, avec l'id ; le nom voisin est DIT ; la liste est relue",
          R["restBt"][2][0] is True and R["restBt"][0][0] is False and "index, tags, projets" in R["restBt"][0][1]
          and R["rest"][0] == ["/api/library/corbeille/restaurer", "POST", {"id": "e1"}] and len([f for f in R["rest"] if f[1] == "POST"]) == 1
          and R["rest"][-1][0] == "/api/library/corbeille" and "« x.png » restauré sous le nom « x_restaure.png » (le sien était repris)." in R["restMsg"], str(R["rest"]) + R["restMsg"])
    check("C3 un refus (409) est DIT", "Non restauré : Un rendu porte déjà l’identifiant j" in R["r409"], R["r409"])
    check("C4 « Vider les anciens » : le dialogue maison dit DEFINITIF ; annule = rien ; confirme = ces ids seulement ; le resultat est dit",
          R["annule"] == [1, 0] and "DÉFINITIF" in R["dialAnc"][0] and R["dialAnc"][1]["ok"] == "Effacer définitivement"
          and R["viderAnc"] == ["/api/library/corbeille/vider", "POST", {"ids": ["e2"]}] and "1 élément effacé (5.0 Mo)." in R["vMsg"], str(R["viderAnc"]) + R["vMsg"])
    check("C5 « Vider la corbeille » envoie {tout:true} apres le dialogue ; une corbeille vide le dit et n'a pas de bouton « Vider »",
          R["viderTout"] == ["/api/library/corbeille/vider", "POST", {"tout": True}] and "TOUT" in R["dialTout"] and "La corbeille est vide." in R["vide"] and R["videBt"] == 0)
    check("C6 les durees : aujourd'hui, hier, il y a N jours, rien", R["duree"] == ["aujourd’hui", "hier", "il y a 40 jours", ""], str(R["duree"]))

R = node("""
var N={poids:{images:{fichiers:10,octets:3*1048576},sons:{fichiers:2,octets:2048},rendus:{fichiers:5,octets:0},corbeille:{fichiers:1,octets:10}},
  copies_en_trop:3,octets_recuperables:3*4096,doublons:[
  {sha256:"h1",octets:4096,en_trop:2,fichiers:[{filename:"a.png",protege:false},{filename:"b.png",protege:false},
    {filename:"c.png",protege:true,fav:true,usages:[{libelle:"Rendu D",role:"image de départ"}],projets:["Campagne"]}]},
  {sha256:"h2",octets:4096,en_trop:1,fichiers:[{filename:"f.png",protege:false},{filename:"g.png",protege:false,garder:true}]}]};
REP["GET /api/library/nettoyage"]=N;var M=monteur(DzNettoyage);var T=await M.monter();R.txt=texte(T);
var cases=trouver(T,function(n){return n.t==="input"});R.cases=cases.map(function(c){return [c.p.checked,c.p.disabled]});
R.titres=trouver(T,function(n){return n.t==="label"}).map(function(l){return l.p.title});R.btJeter=boutons(T,"Mettre 0 à la corbeille")[0].p.disabled;
R.auto=dzNettAuto(N);R.auto2=dzNettAuto({doublons:[{fichiers:[{filename:"p1",protege:true},{filename:"p2",protege:true},{filename:"l",protege:false}]}]});boutons(T,"Cocher les copies en trop")[0].p.onClick();var T2=M.rendu();R.cases2=trouver(T2,function(n){return n.t==="input"}).map(function(c){return c.p.checked});
// cocher les DEUX copies de h2 : bloque
trouver(T2,function(n){return n.t==="input"})[4].p.onChange({target:{checked:true}});var T3=M.rendu();
R.bloque=[texte(T3).indexOf("Un groupe n’aurait plus aucune copie")>=0,boutons(T3,"Mettre 4 à la corbeille")[0].p.disabled];
DIAL=[];FETCH=[];await boutons(T3,"Mettre 4 à la corbeille")[0].p.onClick();await attendre();R.force=[DIAL.length,FETCH.length];
trouver(T3,function(n){return n.t==="input"})[4].p.onChange({target:{checked:false}});var T4=M.rendu();
DREP=false;DIAL=[];FETCH=[];await boutons(T4,"Mettre 3 à la corbeille")[0].p.onClick();await attendre();R.annule=[DIAL.length,FETCH.length];
DREP=true;REP["POST /api/library/nettoyage/jeter"]={jetes:[{filename:"a.png"},{filename:"b.png"},{filename:"f.png"}]};FETCH=[];
await boutons(M.rendu(),"Mettre 3 à la corbeille")[0].p.onClick();await attendre();await attendre();R.jeter=FETCH[0];R.relu=FETCH[1]&&FETCH[1][0];R.jMsg=texte(M.rendu());
REP["POST /api/library/nettoyage/jeter"]={__ko:409,detail:"« c.png » est utilisé"};setTimeout(function(){},0);
M.rendu();var t5=M.rendu();trouver(t5,function(n){return n.t==="input"})[0].p.onChange({target:{checked:true}});
await boutons(M.rendu(),"Mettre 1 à la corbeille")[0].p.onClick();await attendre();R.refus=texte(M.rendu());
REP["GET /api/library/nettoyage"]={poids:N.poids,doublons:[],copies_en_trop:0,octets_recuperables:0};R.aucun=texte(await monteur(DzNettoyage).monter());
""")
check("N0 sous node : le nettoyage s'execute", R is not None)
if R:
    check("N1 le poids par sorte, le resume (groupes, copies en trop, octets recuperables), les fichiers de chaque groupe",
          "Images : 10 · 3.0 Mo" in R["txt"] and "Corbeille : 1 · 10 o" in R["txt"] and "2 groupe(s) de doublons · 3 copie(s) en trop · 12.0 Ko récupérables" in R["txt"]
          and "3 copies identiques · 4.0 Ko chacune" in R["txt"] and "protégée" in R["txt"] and "à garder" in R["txt"], R["txt"])
    check("N2 rien n'est coche d'office ; la copie PROTEGEE est grisee et dit pourquoi (favori, usage, projet) ; la plus ancienne est proposee a garder ; « Mettre 0 » inactif",
          R["cases"] == [[False, False], [False, False], [False, True], [False, False], [False, False]] and R["btJeter"] is True
          and "Protégée — favori · utilisé : Rendu D (image de départ) · projet : Campagne" in R["titres"][2] and "proposée à garder" in R["titres"][4], str(R["titres"]))
    check("N3 « Cocher les copies en trop » garde la copie protegee (ou la plus ancienne) de chaque groupe",
          R["auto"] == {"a.png": True, "b.png": True, "f.png": True} and R["auto2"] == {"l": True} and R["cases2"] == [True, True, False, True, False], str(R["auto"]) + str(R["cases2"]))
    check("N4 cocher TOUTES les copies d'un groupe est BLOQUE (dit, bouton inactif, et un clic force ne part pas)", R["bloque"] == [True, True] and R["force"] == [0, 0], str(R["bloque"]) + str(R.get("force")))
    check("N5 mettre a la corbeille : dialogue maison (annule = rien) ; confirme = les noms coches ; l'analyse est relancee ; le resultat est dit ; un refus est dit",
          R["annule"] == [1, 0] and R["jeter"] == ["/api/library/nettoyage/jeter", "POST", {"fichiers": ["a.png", "b.png", "f.png"]}]
          and R["relu"] == "/api/library/nettoyage" and "3 copie(s) à la corbeille." in R["jMsg"] and "Refusé : « c.png » est utilisé" in R["refus"], str(R["jeter"]) + R["refus"])
    check("N6 sans doublon : « Aucun doublon. »", "Aucun doublon." in R["aucun"])

R = node("""
var M=monteur(DzOutilsBiblio);REP["GET /api/library/corbeille"]={elements:[],octets:0,anciens:0,jours:30};
var T=M.rendu();R.bt=trouver(T,function(n){return n.t==="button"}).map(function(b){return [b.p.children,b.p.title,b.p["aria-pressed"]]});
trouver(T,function(n){return n.t==="button"})[0].p.onClick();var T2=M.rendu();R.ouvert=trouver(T2,function(n){return n.t===DzCorbeille}).length;
trouver(T2,function(n){return n.t==="button"})[1].p.onClick();var T3=M.rendu();R.nett=trouver(T3,function(n){return n.t===DzNettoyage}).length+trouver(T3,function(n){return n.t===DzCorbeille}).length*10;
trouver(T3,function(n){return n.t==="button"})[1].p.onClick();R.ferme=trouver(M.rendu(),function(n){return n.t===DzNettoyage||n.t===DzCorbeille}).length;
// la teinte : filtre, comptes, puces
var L=[{name:"a",teinte:"bleu",couleur:"#1040e0"},{name:"b",teinte:"bleu",couleur:"#2050f0"},{name:"c",teinte:"rouge",couleur:"#e01010"},{name:"d"}];
R.filtre=dzMetaFiltre(L,{teinte:"bleu"}).map(function(z){return z.name});R.sans=dzMetaFiltre(L,{tag:"",note:0}).length;
R.comptes=dzMetaComptes(L).teintes;var POSE=[];var Tc=DzMetaChips({o:"Images",T:{Images:L},f:{tag:"",note:0},setF:function(g){POSE.push(g)}});
var pc=trouver(Tc,function(n){return n.t==="button"});pc[0].p.onClick();R.pose=POSE[0];
var Ta=DzMetaChips({o:"Images",T:{Images:L},f:{tag:"",note:0,teinte:"bleu"},setF:function(g){POSE.push(g)}});
var ef=trouver(Ta,function(n){return n.t==="button"&&n.p.children==="Effacer"})[0];ef.p.onClick();R.efface=POSE[1];
R.pastille=trouver(pc[0],function(n){return n.p&&n.p.style&&n.p.style.background==="#1040e0"}).length;
var LT=[{name:"t",tags:["mer"],teinte:"bleu"}];var Tt=DzMetaChips({o:"Images",T:{Images:LT},f:{tag:"",note:0,teinte:"bleu"},setF:function(g){POSE.push(g)}});
trouver(Tt,function(n){return n.t==="button"})[0].p.onClick();R.garde=POSE[POSE.length-1];
R.sansTeinte=DzMetaChips({o:"Images",T:{Images:[{name:"z"}]},f:{tag:"",note:0},setF:function(){}});
""")
check("O0 sous node : la barre et la teinte s'executent", R is not None)
if R:
    check("O1 la barre : deux boutons (title) ; un clic OUVRE le panneau, l'autre bouton bascule, un second clic FERME",
          [b[0] for b in R["bt"]] == ["🗑 Corbeille", "🧹 Nettoyage"] and all(b[1] for b in R["bt"]) and R["ouvert"] == 1 and R["nett"] == 1 and R["ferme"] == 0, str(R["bt"]))
    check("O2 la TEINTE filtre la grille (et un filtre sans teinte ne filtre rien) ; comptes par teinte avec la pastille de la premiere couleur",
          R["filtre"] == ["a", "b"] and R["sans"] == 4 and R["comptes"] == [{"t": "bleu", "n": 2, "c": "#1040e0"}, {"t": "rouge", "n": 1, "c": "#e01010"}], str(R["comptes"]))
    check("O3 la puce pose la teinte en gardant tag et note ; « Effacer » remet tout a zero ; la puce montre la pastille ; pas de puce sans teinte",
          R["pose"] == {"tag": "", "note": 0, "teinte": "bleu"} and R["efface"] == {"tag": "", "note": 0, "teinte": ""} and R["pastille"] == 1 and R["sansTeinte"] is None
          and R["garde"] == {"tag": "mer", "note": 0, "teinte": "bleu"},
          str(R["pose"]) + str(R["efface"]))

R = node("""
REP["GET /api/library/fiche/a.png"]={filename:"a.png",kind:"image",source:"generation",source_libelle:"Générateur",droits:{licence:"propriétaire",alerte:false,licences:[]},
  fichier:{largeur:2,hauteur:2,octets:10,format:"png"},couleur:{hex:"#1040e0",teinte:"bleu"},recette:null,rejouer:null,usages:[]};
var T=await monteur(DzFiche).monter({m:{name:"a.png",kind:"image"}});R.txt=texte(T);
R.p=trouver(T,function(n){return n.p&&n.p["data-dz"]==="pastille"}).map(function(n){return n.p.style.background});
""")
check("F1 la fiche montre la PASTILLE de la couleur dominante (teinte · hex)", R is not None and R["p"] == ["#1040e0"] and "bleu · #1040e0" in R["txt"], str(R))
check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 178
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
