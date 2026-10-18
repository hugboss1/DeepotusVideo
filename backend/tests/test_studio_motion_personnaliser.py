# -*- coding: utf-8 -*-
"""Studio : Animation, t241 (18/10/2026) — rubrique « Personnaliser » du nœud Direction motion (spec
docs/superpowers/specs/2026-10-18-studio-animation-personnalisation.md § P1-P5, P7, P8), dans le maillon de queue
`dzmotion` (scripts/patch_bundle_dzmotion.py). Consomme les contrats de t239 (efforts par moteur et par modèle) et de
t240 (champs des fiches, GET /api/motion/personnalisation, corps de POST /api/motion/choregraphier).

Ce que ce banc garde, sous node avec les VRAIES fonctions extraites du livré (catalogue `Me`, `Wt`, bloc du maillon,
`DzAnimation` entier ; React et le réseau simulés ; les données de personnalisation = le VRAI fichier du dépôt) :
  [P] le corps envoyé à t234 : champs (vides retirés = défaut), précisions (prompt / skill seulement), curseurs
      (0-4, 2 par défaut), tempo_bpm (40-220, absent si vide), effort (« auto » si le modèle ne l'accepte pas),
      remplacements du format, de la durée, de la police et de la palette (absents = graphe et kit de marque) ;
  [U] l'inspecteur : rubrique générée depuis les `champs` de la fiche (libellé, aide, défaut en texte d'exemple, liste
      avec « défaut »), précisions + aperçu de la règle + « Reprendre mes précisions », trois curseurs à 5 crans (état,
      phrase ajoutée ou effet de la finition, FR puis EN), tempo, remplacements, Effort à côté du modèle (Auto + défaut
      du modèle, puis les niveaux de CE modèle ; Auto seul sinon), bulle de coût qui dit l'effort ;
  [C] « Chorégraphier » envoie ce corps complet ;
  [D] comptes du maillon (hooks toujours par dzMoUS : 2 ; dzMoUE : 3 ; x.useState( 731) et route lue ;
  [K] chaque clé studio.motion.* neuve a son FR et son EN.
Run (depuis backend/) : & $PY tests/test_studio_motion_personnaliser.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
PERSO_P = RACINE / "backend" / "app" / "motion" / "personnalisation.json"
PERSO = json.loads(PERSO_P.read_bytes().decode("utf-8"))

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const PERSO=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
function objet(debut){const i=S.indexOf(debut);if(i<0)throw new Error("introuvable : "+debut);let k=i+debut.indexOf("{"),n=0,q=null;
 for(let j=k;j<S.length;j++){const c=S[j];if(q){if(c==="\\"){j++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")n++;else if(c==="}"){n--;if(!n)return S.slice(k,j+1)}}
 throw new Error("objet non fermé")}
let LANG="fr",H=[],hi=0,EFF=[],CALLS=[],SETS=[],LIS={},ROUTES={};
const x={useState(init){const i=hi++;if(!(i in H))H[i]=typeof init==="function"?init():init;
  return [H[i],function(v){H[i]=typeof v==="function"?v(H[i]):v}]},useEffect(f){EFF.push(f)},useRef(){return{current:null}}};
const r={jsx(t,p){return{t,p:p||{}}},jsxs(t,p){return{t,p:p||{}}}};
const window={dzLang(){return LANG},addEventListener(t,f){LIS[t]=f},removeEventListener(t,f){if(LIS[t]===f)delete LIS[t]},
 __dzDialogue:{confirmer:async function(){return true},saisir:async function(){return null}}};
async function fetch(u,o){CALLS.push({u,o:o||null});const f=ROUTES[u.split("?")[0]]||ROUTES["*"];const v=f?f(u,o):{status:404,j:{detail:"x"}};
 return{ok:(v.status||200)<400,status:v.status||200,json:async function(){return v.j}}}
const dzT=function(k,v){return k+(v?JSON.stringify(v):"")},dzMq=function(k){return"MQ:"+k};
const STUB={x,r,window,fetch,dzT,dzMq,localStorage:{getItem(){return null},setItem(){}},DZ_FONTS:["Anton","Inter","Bungee"],
 ie:"ie",O:"O",le:"le",re:"re",Ze:"Ze",DzColorPicker:"DzColorPicker",__dzGl(n){return"gl:"+n},__dzGlT(n,t){return t}};
const ENV=new Proxy(STUB,{has(t,k){return typeof k==="string"},get(t,k){if(k===Symbol.unscopables)return undefined;
 if(k in t)return t[k];if(k in globalThis)return globalThis[k];return function(){return null}}});
function arbre(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>arbre(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)arbre(n.p.children,f,acc);return acc}
function par(t,nom){return arbre(t,n=>n.p&&n.p["data-dz-motion"]===nom)[0]||null}
function champ(t,label){return arbre(t,n=>n.t==="O"&&n.p.label===label)[0]||null}
function texte(n){if(n==null||n===false)return"";if(typeof n!=="object")return String(n);if(Array.isArray(n))return n.map(texte).join("");
 return texte(n.p&&n.p.children)}
async function vider(){for(let k=0;k<6;k++){const e=EFF;EFF=[];e.forEach(f=>f());await new Promise(s=>setTimeout(s,0))}}
function poseur(nd){return function(k,v){nd.props=Object.assign({},nd.props,{[k]:v});SETS.push([k,v])}}
function rendre(C,nd,g){hi=0;EFF=[];return C({node:nd,graph:g,set:poseur(nd)})}
const KIN={id:"style-kinetic-type",nature:"style",titre:{fr:"Typographie cinétique",en:"Kinetic type"},champs:[
 {id:"mots_max",type:"nombre",libelle:{fr:"Mots à l'écran",en:"Words on screen"},aide:{fr:"Combien de mots.",en:"How many words."},defaut:3,min:1,max:6},
 {id:"fond",type:"texte",libelle:{fr:"Fond",en:"Background"},aide:{fr:"Derrière les mots.",en:"Behind the words."},defaut:{fr:"un fond uni",en:"a flat background"},max:80},
 {id:"fin",type:"texte",libelle:{fr:"Dernier mot",en:"Last word"},aide:{fr:"La fin.",en:"The end."},defaut:{fr:"la marque",en:"the brand"},max:80}]};
const DIA={id:"style-diagrams",nature:"style",titre:{fr:"Schémas",en:"Diagrams"},champs:[
 {id:"sens",type:"liste",libelle:{fr:"Sens du flux",en:"Flow direction"},aide:{fr:"Sens de lecture.",en:"Reading way."},defaut:"libre",
  options:[{valeur:"libre",libelle:{fr:"au choix",en:"either way"}},{valeur:"horizontal",libelle:{fr:"de gauche à droite",en:"left to right"}}]}]};
const OPUS={modele:"claude-opus-5-5",niveaux:["low","medium","high","xhigh","max"],defaut:"medium",source:"table"};
const HAIKU={modele:"claude-haiku-4-5-20251001",niveaux:[],defaut:"",source:"table"};
(async function(){try{
 const SRC="var Me="+objet("Me={Image:")+";"+tranche("function Wt(","function dzFinImg(")+";"
  +tranche("var dzMoUS=","function DzAnimation(")+tranche("function DzAnimation(","var __dzManif3d=")
  +";return{Me,Wt,dzMotionPayload,dzMotionBulle,dzMoCache,DzMotionDirection,DzAnimation}";
 const M=new Function("ENV","with(ENV){"+SRC+"}")(ENV);
 ROUTES["/api/motion/biblio"]=()=>({j:{entrees:[KIN,DIA,{id:"prompt-x",nature:"prompt",titre:"P1"},{id:"skill-y",nature:"skill",titre:"S1"}]}});
 ROUTES["/api/motion/moteurs"]=()=>({j:{moteurs:[{moteur:"anthropic",configure:true,modele:"claude-opus-5-5",cout:"payant",efforts:OPUS},
  {moteur:"ollama",configure:true,modele:"llama3",cout:"gratuit",efforts:{modele:"llama3",niveaux:[],defaut:"",source:"aucune"}}]}});
 ROUTES["/api/settings/provider-defaults/modeles"]=(u)=>({j:u.indexOf("anthropic")>0?{moteur:"anthropic",configure:true,
  modeles:["claude-opus-5-5","claude-haiku-4-5-20251001"],defaut:"claude-opus-5-5",efforts:{"claude-opus-5-5":OPUS,"claude-haiku-4-5-20251001":HAIKU}}:
  {moteur:"ollama",configure:true,modeles:["llama3"],defaut:"llama3",efforts:{llama3:{modele:"llama3",niveaux:[],defaut:"",source:"aucune"}}}});
 ROUTES["/api/motion/personnalisation"]=()=>({j:{neutre:PERSO.neutre,curseurs:PERSO.curseurs,precisions:PERSO.precisions,tempo:PERSO.tempo}});
 ROUTES["/api/motion/biblio/skill-y"]=()=>({j:{id:"skill-y",nature:"skill",titre:"S1",consigne:"COPIE",original:"ORIGINAL"}});
 ROUTES["/api/motion/biblio/prompt-x"]=()=>({j:{id:"prompt-x",nature:"prompt",titre:"P1",texte:"TXT",url:"https://exemple.org/p/1",auteur:"A"}});
 // ── [P] le corps ──
 const full={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"skill-y",consigne:"MA CONSIGNE",moteur:"anthropic",modele:"",
  champs:{fond:"un ciel violet",mots_max:"2",fin:"  ",inconnu:""},precisions:{usage:"Teaser",couleurs:"",autre:"Pas de rouge"},
  curseurs:{creativite:4,rythme:3,finition:0},tempo:"120",effort:"max",aspect:"1:1",duree:"6",police:"Bungee",couleur:"#112233",couleur_marque:"#445566"}};
 const an={id:"a",type:"Animation",props:{durationS:8,elements:[]}};
 const gF={nodes:[{id:"t",type:"Text",props:{value:"Un\nDeux"}},full,{id:"R",type:"Render",props:{format:"9:16"}},an],
  edges:[{from:"t",fromPort:"out",to:"a",toPort:"script"},{from:"d",fromPort:"direction",to:"a",toPort:"direction"}]};
 OUT.p0=M.dzMotionPayload(gF,an);                                     // cache vide : l'effort part tel quel
 H=[];let t=rendre(M.DzMotionDirection,full,gF);await vider();t=rendre(M.DzMotionDirection,full,gF);await vider();
 OUT.pFull=M.dzMotionPayload(gF,an);
 const nu={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"",consigne:"",moteur:"",modele:""}};
 const gN={nodes:[nu,an],edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"}]};an.props.script="S";
 OUT.pNu=M.dzMotionPayload(gN,an);
 const pr={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"prompt-x",precisions:{usage:"U"},champs:{fond:"F"},tempo:"300",
  duree:"0",aspect:"7:3",police:"",couleur:"rouge",couleur_marque:"#ABCDEF",effort:"max",moteur:"anthropic",modele:"claude-haiku-4-5-20251001"}};
 const gP={nodes:[pr,an],edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"}]};OUT.pPrompt=M.dzMotionPayload(gP,an);
 const sp={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"",precisions:{usage:"NE PART PAS"},tempo:"abc",curseurs:{creativite:7,rythme:"x",finition:1.5}}};
 const gS={nodes:[sp,an],edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"}]};OUT.pSans=M.dzMotionPayload(gS,an);
 const t39={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",tempo:"39,6",duree:"500"}};
 const g39={nodes:[t39,an],edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"}]};OUT.p39=M.dzMotionPayload(g39,an);t39.props.tempo="12";OUT.p12=M.dzMotionPayload(g39,an).tempo_bpm;
 // ── [U] l'inspecteur (FR) ──
 const opt=(tr,l)=>{const s=champ(tr,l);return s&&s.p.children&&s.p.children.p.options};
 const val=(tr,l)=>{const s=champ(tr,l);return s&&s.p.children&&s.p.children.p.value};
 t=rendre(M.DzMotionDirection,full,gF);
 OUT.perso=!!par(t,"perso");OUT.persoLabel=arbre(t,n=>n.t==="ie"&&n.p.label==="studio.motion.personnaliser").map(n=>n.p.defaultOpen)[0];
 const cm=par(t,"champ-mots_max"),cf=par(t,"champ-fond"),cn=par(t,"champ-fin");
 OUT.champs={mots:cm&&{type:cm.p.type,min:cm.p.min,max:cm.p.max,ph:cm.p.placeholder,v:cm.p.value},fond:cf&&{type:cf.p.type,ph:cf.p.placeholder,v:cf.p.value,ml:cf.p.maxLength},
  fin:cn&&{ph:cn.p.placeholder,v:cn.p.value},hint:(champ(t,"Fond")||{p:{}}).p.hint,lib:!!champ(t,"Mots à l'écran")};
 SETS=[];cf.p.onChange("un ciel orange");OUT.setChamp=SETS.slice();
 // précisions (skill)
 OUT.prec=["usage","duree","couleurs","police","autre"].map(k=>{const q=par(t,"precision-"+k);return q&&{ph:q.p.placeholder,v:q.p.value,ml:q.p.maxLength}});
 OUT.precTitre=texte(par(t,"precisions")).indexOf(PERSO.precisions.titre.fr)>=0;
 OUT.apercu=texte(par(t,"apercu"));
 OUT.reprendre0=par(t,"reprendre")&&par(t,"reprendre").p.disabled;
 // curseurs
 OUT.curs=["creativite","rythme","finition"].map(k=>{const c=par(t,"cran-"+k);return c&&{type:c.p.type,min:c.p.min,max:c.p.max,step:c.p.step,v:c.p.value,
  etat:texte(par(t,"etat-"+k)),phrase:texte(par(t,"phrase-"+k)),bloc:texte(par(t,"curseur-"+k))}});
 SETS=[];par(t,"cran-rythme").p.onChange({target:{value:"2"}});OUT.setCran=SETS.slice();
 t=rendre(M.DzMotionDirection,full,gF);OUT.rythme2={etat:texte(par(t,"etat-rythme")),phrase:texte(par(t,"phrase-rythme"))};
 // tempo, remplacements
 const tp=par(t,"tempo");OUT.tempo=tp&&{type:tp.p.type,min:tp.p.min,max:tp.p.max,v:tp.p.value,ph:tp.p.placeholder};
 OUT.formats=opt(t,"studio.motion.format");OUT.formatVal=val(t,"studio.motion.format");
 OUT.polices=opt(t,"studio.motion.police");OUT.duree=par(t,"duree")&&{v:par(t,"duree").p.value,ph:par(t,"duree").p.placeholder,min:par(t,"duree").p.min,max:par(t,"duree").p.max};
 OUT.couleur={v:par(t,"couleur")&&par(t,"couleur").p.value,type:par(t,"couleur")&&par(t,"couleur").p.type,kit:!!par(t,"couleur-kit")};
 SETS=[];par(t,"couleur-kit").p.onClick();OUT.setKit=SETS.slice();
 // effort
 OUT.efforts=opt(t,"studio.motion.effort");OUT.effortVal=val(t,"studio.motion.effort");OUT.effortHint=(champ(t,"studio.motion.effort")||{p:{}}).p.hint;
 OUT.bulle=par(t,"bulle")&&par(t,"bulle").p.title;
 SETS=[];champ(t,"studio.motion.effort").p.children.p.onChange("high");OUT.setEffort=SETS.slice();
 const nbMods=CALLS.filter(c=>c.u.indexOf("/api/settings/provider-defaults/modeles")===0).length;
 SETS=[];champ(t,"studio.motion.modele").p.children.p.onChange("claude-haiku-4-5-20251001");t=rendre(M.DzMotionDirection,full,gF);await vider();
 t=rendre(M.DzMotionDirection,full,gF);
 OUT.effortsHaiku=opt(t,"studio.motion.effort");OUT.effortHaikuVal=val(t,"studio.motion.effort");
 OUT.effortHaikuHint=(champ(t,"studio.motion.effort")||{p:{}}).p.hint;OUT.bulleHaiku=par(t,"bulle").p.title;
 OUT.pHaiku=M.dzMotionPayload(gF,an).effort;
 OUT.appelsMods=CALLS.filter(c=>c.u.indexOf("/api/settings/provider-defaults/modeles")===0).length-nbMods;
 full.props.modele="claude-opus-5-5";full.props.effort="xhigh";OUT.pOpus=M.dzMotionPayload(gF,an).effort;
 full.props.effort="auto";t=rendre(M.DzMotionDirection,full,gF);OUT.bulleAuto=par(t,"bulle").p.title;
 // Ollama : aucun niveau → Auto seul
 const ol={id:"o",type:"MotionDirection",props:{style:"style-kinetic-type",source:"",moteur:"ollama",modele:"",effort:"high"}},gO={nodes:[ol],edges:[]};
 H=[];t=rendre(M.DzMotionDirection,ol,gO);await vider();t=rendre(M.DzMotionDirection,ol,gO);
 OUT.effortsOllama=opt(t,"studio.motion.effort");OUT.bulleOllama=par(t,"bulle").p.title;OUT.precOllama=!!par(t,"precisions");
 OUT.pOllama=M.dzMotionPayload({nodes:[ol,an],edges:[{from:"o",fromPort:"direction",to:"a",toPort:"direction"}]},an).effort;
 // sans moteur : pas d'effort
 H=[];t=rendre(M.DzMotionDirection,nu,gN);await vider();t=rendre(M.DzMotionDirection,nu,gN);OUT.effortSans=!champ(t,"studio.motion.effort");
 OUT.champsVides={mots:par(t,"champ-mots_max").p.value,ph:par(t,"champ-mots_max").p.placeholder};
 // liste et changement de style
 SETS=[];champ(t,"studio.motion.style").p.children.p.onChange("style-diagrams");OUT.setStyle=SETS.slice();
 t=rendre(M.DzMotionDirection,nu,gN);OUT.liste=opt(t,"Sens du flux");OUT.listeVal=val(t,"Sens du flux");
 // reprendre mes précisions : le DERNIER autre nœud Direction motion qui en a
 const a1={id:"a1",type:"MotionDirection",props:{source:"skill-y",precisions:{usage:"PREMIER"}}},
  a2={id:"a2",type:"MotionDirection",props:{source:"prompt-x",precisions:{usage:"DERNIER",police:"Inter",autre:""}}},
  a3={id:"a3",type:"MotionDirection",props:{source:"prompt-x",precisions:{}}},
  me={id:"me",type:"MotionDirection",props:{style:"style-kinetic-type",source:"prompt-x",precisions:{usage:"moi"}}};
 const gR={nodes:[a1,me,a2,a3],edges:[]};H=[];t=rendre(M.DzMotionDirection,me,gR);await vider();t=rendre(M.DzMotionDirection,me,gR);
 OUT.rep={dis:par(t,"reprendre").p.disabled};SETS=[];par(t,"reprendre").p.onClick();OUT.rep.sets=SETS.slice();
 t=rendre(M.DzMotionDirection,me,gR);OUT.apercu2=texte(par(t,"apercu"));
 SETS=[];par(t,"precision-autre").p.onChange("Fond noir");OUT.setPrec=SETS.slice();
 // ── EN ──
 LANG="en";t=rendre(M.DzMotionDirection,full,gF);
 OUT.en={fond:par(t,"champ-fond").p.placeholder,lib:!!champ(t,"Background"),etat:texte(par(t,"etat-creativite")),phrase:texte(par(t,"phrase-creativite")),
  fin:texte(par(t,"phrase-finition")),prec:par(t,"precision-usage").p.placeholder,apercu:texte(par(t,"apercu"))};LANG="fr";
 // ── [C] Chorégraphier ──
 full.props.effort="max";full.props.modele="";
 ROUTES["/api/motion/choregraphier"]=(u,o)=>({j:{elements:[],moteur:"anthropic",modele:"claude-opus-5-5",repli:false,cout:{nature:"payant",estime_usd:0.01}}});
 H=[];CALLS=[];an.props.elements=[];t=rendre(M.DzAnimation,an,gF);await par(t,"choregraphier").p.onClick();
 const c1=CALLS.filter(c=>c.u==="/api/motion/choregraphier");OUT.appel=c1[0]&&JSON.parse(c1[0].o.body);OUT.appelAttendu=M.dzMotionPayload(gF,an);
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[P/U/C] sous node, vraies fonctions du livré")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzmotion_perso_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js"), str(PERSO_P)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=120)
try:
    F = json.loads(rn.stdout or "{}")
except ValueError:
    F = {"err": (rn.stdout or "")[-300:] + (rn.stderr or "")[-300:]}
check("P0 bloc du maillon extrait et exécuté", "err" not in F, str(F.get("err", ""))[:400])
C_ = PERSO["curseurs"]
check("P1 corps complet : champs non vides, précisions du skill, curseurs, tempo, effort, format, durée, police, palette",
      F.get("pFull") == {"script": "Un\nDeux", "direction": {
          "style": "style-kinetic-type", "source": "skill-y", "consigne": "MA CONSIGNE",
          "champs": {"fond": "un ciel violet", "mots_max": "2"},
          "curseurs": {"creativite": 4, "rythme": 3, "finition": 0},
          "precisions": {"usage": "Teaser", "autre": "Pas de rouge"}},
          "moteur": "anthropic", "modele": "", "effort": "max", "aspect": "1:1", "duree_s": 6, "images": [],
          "tempo_bpm": 120, "marque": {"couleur": "#112233", "marque": "#445566", "police": "Bungee"}}, str(F.get("pFull")))
check("P2 cache des efforts vide : l'effort part tel quel (le serveur tranche, effort_applique)", (F.get("p0") or {}).get("effort") == "max",
      str((F.get("p0") or {}).get("effort")))
check("P3 rien de personnalisé : champs {}, curseurs neutres, effort auto, pas de tempo ni de marque, format et durée du graphe",
      F.get("pNu") == {"script": "S", "direction": {"style": "style-kinetic-type", "source": None, "consigne": "", "champs": {},
                                                    "curseurs": {"creativite": 2, "rythme": 2, "finition": 2}},
                       "moteur": "", "modele": "", "effort": "auto", "aspect": "9:16", "duree_s": 8, "images": []}, str(F.get("pNu")))
pp = F.get("pPrompt") or {}
check("P4 prompt : précisions envoyées ; tempo 300 → 220 ; format inconnu → graphe ; durée 0 → graphe ; couleur fautive ignorée",
      (pp.get("direction") or {}).get("precisions") == {"usage": "U"} and pp.get("tempo_bpm") == 220 and pp.get("aspect") == "9:16"
      and pp.get("duree_s") == 8 and pp.get("marque") == {"marque": "#ABCDEF"} and (pp.get("direction") or {}).get("consigne") == "", str(pp))
check("P5 modèle connu qui n'accepte pas l'effort (Haiku 4.5, cache des Réglages) : « auto »", pp.get("effort") == "auto", str(pp.get("effort")))
ps = F.get("pSans") or {}
check("P6 sans source : AUCUNE précision ne part ; tempo « abc » absent ; curseurs hors bornes / non entiers → 2",
      "precisions" not in (ps.get("direction") or {}) and "tempo_bpm" not in ps
      and (ps.get("direction") or {}).get("curseurs") == {"creativite": 2, "rythme": 2, "finition": 2}, str(ps))
check("P7 tempo « 39,6 » → 40 (virgule acceptée), « 12 » → 40 (borné) ; durée 500 → 120", (F.get("p39") or {}).get("tempo_bpm") == 40
      and F.get("p12") == 40
      and (F.get("p39") or {}).get("duree_s") == 120, str(F.get("p39")))

print("[U] l'inspecteur")
check("U1 rubrique « Personnaliser » ouverte", F.get("perso") is True and F.get("persoLabel") is True)
ch = F.get("champs") or {}
check("U2 champs générés depuis la fiche : nombre (bornes, défaut en exemple), texte (défaut FR en exemple, max), valeur du nœud ; aide en ligne",
      ch.get("mots") == {"type": "number", "min": 1, "max": 6, "ph": "3", "v": "2"}
      and ch.get("fond") == {"type": "text", "ph": "un fond uni", "v": "un ciel violet", "ml": 80}
      and ch.get("fin") == {"ph": "la marque", "v": "  "} and ch.get("hint") == "Derrière les mots." and ch.get("lib") is True, str(ch))
check("U3 saisir un champ l'écrit dans `champs` du nœud (les autres valeurs gardées)",
      F.get("setChamp") == [["champs", {"fond": "un ciel orange", "mots_max": "2", "fin": "  ", "inconnu": ""}]], str(F.get("setChamp")))
pc = PERSO["precisions"]["champs"]
check("U4 précisions (skill) : cinq champs, aide en exemple, 300 caractères, valeurs du nœud ; titre du bloc",
      F.get("prec") == [{"ph": c["aide"]["fr"], "v": {"usage": "Teaser", "autre": "Pas de rouge"}.get(c["id"], ""), "ml": 300} for c in pc]
      and F.get("precTitre") is True, str(F.get("prec")))
regle = PERSO["precisions"]["titre"]["fr"], PERSO["precisions"]["regle"]["fr"]
check("U5 aperçu : la règle « mes précisions priment », puis une ligne par précision remplie",
      F.get("apercu", "").count("studio.motion.apercu_regle") == 1 and regle[1] in F.get("apercu", "")
      and 'studio.motion.apercu_ligne{"libelle":"' + pc[0]["libelle"]["fr"] + '","valeur":"Teaser"}' in F.get("apercu", "")
      and 'studio.motion.apercu_ligne{"libelle":"' + pc[4]["libelle"]["fr"] + '","valeur":"Pas de rouge"}' in F.get("apercu", "")
      and pc[2]["libelle"]["fr"] not in F.get("apercu", ""), F.get("apercu", "")[:300])
check("U6 « Reprendre mes précisions » éteint sans autre Direction motion", F.get("reprendre0") is True)
cu = F.get("curs") or [None] * 3
check("U7 trois curseurs à 5 crans (range 0-4, pas 1) à la valeur du nœud",
      all(c and c["type"] == "range" and c["min"] == 0 and c["max"] == 4 and c["step"] == 1 for c in cu)
      and [c and c["v"] for c in cu] == [4, 3, 0], str(cu))
check("U8 état et phrase ajoutée lus sur /personnalisation (Créativité 4, Rythme 3) ; Finition : son effet ; pôles et libellé",
      cu[0] and cu[0]["etat"] == C_["creativite"]["crans"][4]["etat"]["fr"]
      and cu[0]["phrase"] == 'studio.motion.curseur_phrase{"phrase":"' + C_["creativite"]["crans"][4]["phrase"]["fr"] + '"}'
      and cu[1]["etat"] == C_["rythme"]["crans"][3]["etat"]["fr"]
      and cu[2]["etat"] == C_["finition"]["crans"][0]["etat"]["fr"] and cu[2]["phrase"] == C_["finition"]["crans"][0]["effet"]["fr"]
      and C_["creativite"]["poles"]["fr"][0] in cu[0]["bloc"] and C_["creativite"]["poles"]["fr"][1] in cu[0]["bloc"]
      and C_["creativite"]["libelle"]["fr"] in cu[0]["bloc"], str(cu)[:400])
check("U9 déplacer un curseur écrit les trois (entiers) ; au neutre : « rien n'est ajouté »",
      F.get("setCran") == [["curseurs", {"creativite": 4, "rythme": 2, "finition": 0}]]
      and (F.get("rythme2") or {}).get("etat") == C_["rythme"]["crans"][2]["etat"]["fr"]
      and (F.get("rythme2") or {}).get("phrase") == "studio.motion.curseur_neutre", str(F.get("rythme2")))
check("U10 tempo : nombre 40-220, vide = « aucun tempo »", F.get("tempo") == {"type": "number", "min": 40, "max": 220, "v": "120",
                                                                             "ph": "studio.motion.tempo_aucun"}, str(F.get("tempo")))
check("U11 format : « celui du graphe (9:16) » puis les 4 formats ; valeur du nœud",
      F.get("formats") == [{"value": "", "label": 'studio.motion.format_graphe{"format":"9:16"}'}] + [{"value": f, "label": f} for f in ("16:9", "9:16", "1:1", "4:5")]
      and F.get("formatVal") == "1:1", str(F.get("formats")))
check("U12 police : « kit de marque » puis les polices livrées ; durée 1-120, vide = celle de l'Animation",
      F.get("polices") == [{"value": "", "label": "studio.motion.kit"}] + [{"value": f, "label": f} for f in ("Anton", "Inter", "Bungee")]
      and F.get("duree") == {"v": "6", "ph": "studio.motion.duree_graphe", "min": 1, "max": 120}, str(F.get("duree")))
check("U13 palette : couleur choisie, bouton « kit de marque » qui la vide", (F.get("couleur") or {}) == {"v": "#112233", "type": "color", "kit": True}
      and F.get("setKit") == [["couleur", ""]], str(F.get("couleur")))
check("U14 Effort à côté du modèle : « Auto (défaut du modèle : medium) » puis les niveaux de CE modèle ; valeur max ; pas d'aide « Auto seul »",
      F.get("efforts") == [{"value": "auto", "label": 'studio.motion.effort_auto_defaut{"defaut":"medium"}'}]
      + [{"value": n, "label": n} for n in ("low", "medium", "high", "xhigh", "max")]
      and F.get("effortVal") == "max" and not F.get("effortHint"), str(F.get("efforts")))
check("U15 la bulle de coût dit l'effort choisi",
      F.get("bulle") == 'studio.motion.cout_payant{"moteur":"anthropic · claude-opus-5-5"} · studio.motion.effort_bulle{"effort":"max"}', str(F.get("bulle")))
check("U16 choisir un niveau l'écrit dans le nœud", F.get("setEffort") == [["effort", "high"]], str(F.get("setEffort")))
check("U17 modèle qui n'accepte pas l'effort (Haiku 4.5) : Auto SEUL, aide et bulle le disent, rien d'autre proposé ; corps « auto »",
      F.get("effortsHaiku") == [{"value": "auto", "label": "studio.motion.effort_auto"}] and F.get("effortHaikuVal") == "auto"
      and F.get("effortHaikuHint") == "studio.motion.effort_seul" and str(F.get("bulleHaiku")).endswith(" · studio.motion.effort_bulle_seul")
      and F.get("pHaiku") == "auto", str(F.get("effortsHaiku")) + str(F.get("bulleHaiku")))
check("U18 les efforts suivent le modèle sans autre appel (efforts de provider-defaults/modeles déjà lus)", F.get("appelsMods") == 0,
      str(F.get("appelsMods")))
check("U19 retour sur Opus : xhigh accepté part tel quel ; Auto → la bulle dit le défaut du modèle", F.get("pOpus") == "xhigh"
      and str(F.get("bulleAuto")).endswith(' · studio.motion.effort_bulle_auto{"defaut":"medium"}'), str(F.get("bulleAuto")))
check("U20 Ollama sans niveau : Auto seul, corps « auto » ; sans source : pas de bloc de précisions",
      F.get("effortsOllama") == [{"value": "auto", "label": "studio.motion.effort_auto"}] and F.get("pOllama") == "auto"
      and str(F.get("bulleOllama")).endswith(" · studio.motion.effort_bulle_seul") and F.get("precOllama") is False, str(F.get("effortsOllama")))
check("U21 sans moteur : pas de sélecteur d'effort ; champ vide = défaut en texte d'exemple",
      F.get("effortSans") is True and F.get("champsVides") == {"mots": "", "ph": "3"}, str(F.get("champsVides")))
check("U22 changer de style vide les champs (pas de reste d'une autre fiche)",
      F.get("setStyle") == [["style", "style-diagrams"], ["champs", {}]], str(F.get("setStyle")))
check("U23 champ liste : « par défaut : <option> » puis les options (libellés FR) ; vide = défaut",
      F.get("liste") == [{"value": "", "label": 'studio.motion.champ_defaut{"valeur":"au choix"}'}, {"value": "libre", "label": "au choix"},
                         {"value": "horizontal", "label": "de gauche à droite"}] and F.get("listeVal") == "", str(F.get("liste")))
rp = F.get("rep") or {}
check("U24 « Reprendre mes précisions » copie celles du DERNIER autre nœud Direction motion qui en a (vides retirées)",
      rp.get("dis") is False and rp.get("sets") == [["precisions", {"usage": "DERNIER", "police": "Inter"}]]
      and '"valeur":"DERNIER"' in F.get("apercu2", ""), str(rp))
check("U25 saisir une précision l'écrit dans `precisions` du nœud", F.get("setPrec") == [["precisions", {"usage": "DERNIER", "police": "Inter",
                                                                                                      "autre": "Fond noir"}]], str(F.get("setPrec")))
en = F.get("en") or {}
check("U26 EN : défaut, libellé, état, phrase, effet, aide des précisions et règle en anglais",
      en.get("fond") == "a flat background" and en.get("lib") is True and en.get("etat") == C_["creativite"]["crans"][4]["etat"]["en"]
      and C_["creativite"]["crans"][4]["phrase"]["en"] in en.get("phrase", "") and en.get("fin") == C_["finition"]["crans"][0]["effet"]["en"]
      and en.get("prec") == pc[0]["aide"]["en"] and PERSO["precisions"]["regle"]["en"] in en.get("apercu", ""), str(en)[:300])
check("C1 « Chorégraphier » envoie le corps complet (champs, précisions, curseurs, tempo, effort, remplacements)",
      bool(F.get("appel")) and F.get("appel") == F.get("appelAttendu") and (F.get("appel") or {}).get("effort") == "max"
      and (F.get("appel") or {}).get("tempo_bpm") == 120 and ((F.get("appel") or {}).get("direction") or {}).get("curseurs", {}).get("finition") == 0,
      str(F.get("appel"))[:300])

print("[D] comptes du maillon")
check("D1 route de personnalisation lue ; efforts des modèles retenus", '"/api/motion/personnalisation"' in BUNDLE and "dzMoCache.effs[" in BUNDLE)
check("D2 hooks : toujours DEUX appels dzMoUS, TROIS dzMoUE ; x.useState( 731", BUNDLE.count("dzMoUS(") == 2
      and BUNDLE.count("dzMoUE(") == 3 and BUNDLE.count("x.useState(") == 731)

print("[K] textes")
dico = {}
for f_ in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    dico.update(json.loads(f_.read_bytes().decode("utf-8")))
NEUVES = ["personnaliser", "champ_defaut", "apercu_regle", "apercu_ligne", "precisions_vides", "reprendre", "reprendre_aide",
          "curseur_phrase", "curseur_neutre", "tempo", "tempo_aide", "tempo_aucun", "format", "format_graphe", "duree",
          "duree_graphe", "police", "kit", "kit_revenir", "couleur", "couleur_marque", "effort", "effort_auto", "effort_auto_defaut",
          "effort_seul", "effort_bulle", "effort_bulle_auto", "effort_bulle_auto_nu", "effort_bulle_seul", "perso_fiche",
          "perso_curseurs", "perso_remplacements", "remplacements_aide", "perso_chargement"]
manq = [k for k in NEUVES if not (dico.get("studio.motion." + k, {}).get("fr", "").strip() and dico.get("studio.motion." + k, {}).get("en", "").strip())]
check("K1 clés neuves FR ET EN", not manq, str(manq))
check("K2 employées dans le livré", all(f'dzT("studio.motion.{k}"' in BUNDLE for k in NEUVES),
      str([k for k in NEUVES if f'dzT("studio.motion.{k}"' not in BUNDLE]))
check("K3 aucune phrase des données (/personnalisation, fiches) recopiée dans le livré : elles viennent du serveur",
      all((c.get("phrase") or c.get("effet"))["fr"] not in BUNDLE for cu_ in C_.values() for c in cu_["crans"] if c.get("phrase") or c.get("effet"))
      and PERSO["precisions"]["regle"]["fr"] not in BUNDLE)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
