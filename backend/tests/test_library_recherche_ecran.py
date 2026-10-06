# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR C (plan-library T12-T13, 04/10/2026) — la RECHERCHE et les LEGENDES a l'ecran, dans le
bundle LIVRE : DzRecherche est extrait et EXECUTE sous node (fetch et dialogue maison simules : aucun appel payant).
DECISIONS DE L'UTILISATEUR (04/10) : un SELECTEUR de moteur (texte ; CLIP grise jusqu'a la PR D) ; les legendes sont
PAYANTES : le prix est annonce par le dialogue maison avant tout appel, qui dit que les images partent chez Google.
Temoin positif : le bundle de la base (258d5724) n'a pas la recherche.
Run (depuis backend/) : & $PY tests/test_library_recherche_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzrce_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "258d5724"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a la barre de la Bibliotheque mais pas la recherche", r0.returncode == 0 and b"DzOutilsBiblio" in r0.stdout and b"DzRecherche" not in r0.stdout)
check("T2 la barre recoit la liste chargee et l'ouverture d'une fiche ; un bouton « 🔎 Recherche » ouvre le panneau ; la fiche dit la legende",
      BUN.count("r.jsx(DzOutilsBiblio,{vue:dzVue,setVue:dzVues,liste:l,ouvrir:y})") == 1
      and BUN.count('vue==="recherche"?r.jsx(DzRecherche,{liste:P&&P.liste,ouvrir:P&&P.ouvrir||function(){}}):null') == 1
      and BUN.count('f.legende?ligne("Légende",f.legende.texte,') == 1)


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


NOMS = ("dzUsdLeg", "dzMo", "DzClipBloc", "DzRecherche")
k = BUN.find("var DZ_MOTEURS=")
MOT = BUN[k:BUN.find("]];", k) + 3] if k >= 0 else ""
COUCHE = MOT + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a ses fonctions (une fois chacune) ; dzUsdLeg ne heurte pas le dzUsd du bundle", all(BUN.count("function " + n + "(") == 1 for n in NOMS)
      and BUN.count("function dzUsd(") == 1 and MOT != "")

HARNAIS = r"""
var H=[],hi=0,EFF=[],FETCH=[],REP={},DIAL=[],DREP=true;
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useEffect:function(f){EFF.push(f)},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{confirmer:async function(m,o){DIAL.push([m,o]);return DREP}}};
async function fetch(u,o){var m=o&&o.method||"GET";FETCH.push([u,m,o&&o.body?JSON.parse(o.body):null]);var q=REP[m+" "+u];
  await new Promise(function(s){setTimeout(s,3)});if(typeof q==="function")q=q();
  return {ok:!!q&&!q.__ko,status:q&&q.__ko?q.__ko:(q?200:404),json:async function(){return q}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
function boutons(T,debut){return trouver(T,function(n){return n.t==="K"&&String(n.p.children).indexOf(debut)===0})}
async function attendre(){await new Promise(function(s){setTimeout(s,40)})}
function rendu(p){hi=0;EFF=[];return DzRecherche(p)}
async function monter(p){rendu(p);var e=EFF.slice();e.forEach(function(f){f()});await attendre();return rendu(p)}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R));process.exit(0)})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-600:])
        return None


R = node("""
REP["GET /api/library/legendes/devis"]={n:1009,usd:0.0634,modele:"gemini-2.5-flash-lite",cle:true,etat:{en_cours:false,total:0,faits:0,n_erreurs:0,arret:""}};
var LISTE=[{name:"b.png",kind:"image"},{name:"c.png",kind:"image"}],OUV=[];var P={liste:LISTE,ouvrir:function(z){OUV.push(z.name)}};
var T=await monter(P);R.txt=texte(T);
var sel=trouver(T,function(n){return n.t==="select"})[0];R.sel=[sel.p.title,trouver(sel,function(n){return n.t==="option"}).map(function(o){return [o.p.value,!!o.p.disabled]})];
R.chercherInactif=boutons(T,"Chercher")[0].p.disabled;
trouver(T,function(n){return n.t==="input"})[0].p.onChange({target:{value:"tempête bleue"}});
REP["GET /api/library/recherche?q=temp%C3%AAte%20bleue&moteur=texte"]={n:3,resultats:[{filename:"b.png",score:6,champs:["legende"],extrait:"Un phare sous la tempête"},
  {filename:"absent.png",score:3,champs:["tags"],extrait:""}]};
FETCH=[];boutons(rendu(P),"Chercher")[0].p.onClick();await attendre();R.fetch=FETCH[0];var T2=rendu(P);R.txt2=texte(T2);
var cartes=trouver(T2,function(n){return n.t==="button"&&n.p.title!==undefined});R.cartes=cartes.map(function(c){return [!!c.p.disabled,c.p.title]});
cartes[0].p.onClick();cartes[1].p.onClick();R.ouv=OUV;
REP["GET /api/library/recherche?q=temp%C3%AAte%20bleue&moteur=clip"]={__ko:503,detail:"La recherche CLIP (locale) n'est pas encore installée."};
trouver(rendu(P),function(n){return n.t==="select"})[0].p.onChange({target:{value:"clip"}});boutons(rendu(P),"Chercher")[0].p.onClick();await attendre();R.clip=texte(rendu(P));
R.usd=[dzUsdLeg(0.0634),dzUsdLeg(0.00006),dzUsdLeg(1.5),dzUsdLeg(null)];
""")
check("R0 sous node : la recherche s'execute", R is not None)
if R:
    check("R1 le SELECTEUR (title) : texte actif, CLIP grise « a installer » ; « Chercher » inactif sans requete",
          "moteur" in R["sel"][0] and R["sel"][1] == [["texte", False], ["clip", True]] and R["chercherInactif"] is True, str(R["sel"]))
    check("R2 la requete part ENCODEE avec le moteur ; le nombre dit ; une carte par resultat avec l'extrait",
          R["fetch"] == ["/api/library/recherche?q=temp%C3%AAte%20bleue&moteur=texte", "GET", None] and "3 image(s) (les 2 premières)" in R["txt2"]
          and "Un phare sous la tempête" in R["txt2"], R["txt2"])
    check("R3 une carte de la liste chargee OUVRE sa fiche (title : ou elle a ete trouvee) ; une absente est desactivee et le dit",
          R["cartes"][0][0] is False and "trouvé dans : legende" in R["cartes"][0][1] and R["cartes"][1][0] is True and "pas dans la liste chargée" in R["cartes"][1][1]
          and R["ouv"] == ["b.png"], str(R["cartes"]))
    check("R4 un refus du serveur (CLIP non installe) est DIT", "pas encore installée" in R["clip"], R["clip"])
    check("R5 le prix : ≈ 0.06 $, ≈ 0.0001 $, ≈ 1.50 $, inconnu", R["usd"] == ["≈ 0.06 $", "≈ 0.0001 $", "≈ 1.50 $", "prix inconnu"], str(R["usd"]))

R = node("""
REP["GET /api/library/legendes/devis"]={n:1009,usd:0.0634,modele:"gemini-2.5-flash-lite",cle:true,etat:{en_cours:false,total:0,faits:0,n_erreurs:0,arret:""}};
var P={liste:[],ouvrir:function(){}};var T=await monter(P);R.txt=texte(T);var b=boutons(T,"Légender")[0];R.b=[b.p.children,b.p.title,!!b.p.disabled];
DREP=false;FETCH=[];await b.p.onClick();R.annule=[DIAL.length,FETCH.length];R.dial=DIAL[0];
DREP=true;REP["POST /api/library/legendes"]={lance:1009,n:1009,usd:0.0634};FETCH=[];DIAL=[];var b2=boutons(rendu(P),"Légender")[0];var p1=b2.p.onClick(),p2=b2.p.onClick();await p1;await p2;await attendre();
R.post=FETCH.filter(function(f){return f[1]==="POST"});R.dial2=DIAL.length;var T3=rendu(P);R.suivi=texte(T3);R.bEnCours=boutons(T3,"Légender").length;
// le suivi : l'effet a intervalle relit l'etat, puis le devis a la fin
REP["GET /api/library/legendes/etat"]={en_cours:false,total:1009,faits:1009,n_erreurs:2,arret:""};
REP["GET /api/library/legendes/devis"]={n:0,usd:0,modele:"gemini-2.5-flash-lite",cle:true,etat:{en_cours:false,total:1009,faits:1009,n_erreurs:2,arret:""}};
hi=0;EFF=[];DzRecherche(P);FETCH=[];var ef=EFF[2]();   /* 0 : etat de CLIP (#82 PR D), 1 : devis, 2 : le suivi */await new Promise(function(s){setTimeout(s,2150)});if(typeof ef==="function")ef();await attendre();R.poll=FETCH.map(function(f){return f[0]});R.fin=texte(rendu(P));
// refus du plafond
REP["GET /api/library/legendes/devis"]={n:5,usd:0.0003,modele:"gemini-2.5-flash-lite",cle:true,etat:{en_cours:false,total:0,faits:0,n_erreurs:0,arret:""}};
H=[];var T4=await monter(P);REP["POST /api/library/legendes"]={__ko:402,detail:{message:"Plafond mensuel atteint (gemini)"}};await boutons(T4,"Légender")[0].p.onClick();R.refus=texte(rendu(P));
// sans cle
REP["GET /api/library/legendes/devis"]={n:5,usd:0.0003,modele:"gemini-2.5-flash-lite",cle:false,etat:{en_cours:false}};H=[];var T5=await monter(P);var b5=boutons(T5,"Légender")[0];R.sansCle=[!!b5.p.disabled,b5.p.title];
REP["GET /api/library/legendes/devis"]={n:0,usd:0,modele:"m",cle:true,etat:{en_cours:false,arret:"Gemini HTTP 401 : cle"}};H=[];var T6=await monter(P);R.arret=texte(T6);R.rien=boutons(T6,"Légender").length;
""")
check("G0 sous node : les legendes s'executent", R is not None)
if R:
    check("G1 le devis est DIT : nombre, prix, modele, « les images sont envoyees a Google » ; le bouton porte le prix et dit PAYANT",
          "1009 image(s) sans légende — ≈ 0.06 $ avec gemini-2.5-flash-lite (les images sont envoyées à Google)" in R["txt"]
          and R["b"][0] == "Légender (≈ 0.06 $)" and "PAYANT" in R["b"][1] and R["b"][2] is False, R["txt"] + str(R["b"]))
    check("G2 le dialogue maison ANNONCE prix, modele, plafond et l'envoi a Google ; annule : RIEN ne part",
          R["annule"] == [1, 0] and "≈ 0.06 $" in R["dial"][0] and "Google" in R["dial"][0] and "plafond" in R["dial"][0] and R["dial"][1]["ok"] == "Légender (≈ 0.06 $)", str(R["dial"]))
    check("G3 confirme : UN lancement au double clic ; le suivi s'affiche (faits / total) et le bouton disparait pendant le travail",
          len(R["post"]) == 1 and R["post"][0][0] == "/api/library/legendes" and R["dial2"] == 1 and "Légendage : 0 / 1009" in R["suivi"] and R["bEnCours"] == 0, str(R["post"]) + R["suivi"])
    check("G4 le SUIVI relit l'etat toutes les 2 s puis le devis a la fin : « Toutes les images ont une legende »",
          "/api/library/legendes/etat" in R["poll"] and "/api/library/legendes/devis" in R["poll"] and "Toutes les images ont une légende." in R["fin"], str(R["poll"]) + R["fin"])
    check("G5 un refus du PLAFOND (402) est dit avec son message ; sans cle le bouton est inactif et le dit ; un ARRET (cle refusee) est dit",
          "Refusé : Plafond mensuel atteint (gemini)" in R["refus"] and R["sansCle"][0] is True and "Clé Gemini absente" in R["sansCle"][1]
          and "Arrêté : Gemini HTTP 401 : cle" in R["arret"] and R["rien"] == 0, R["refus"] + str(R["sansCle"]) + R["arret"])
check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 180, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 180
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
