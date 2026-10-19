# -*- coding: utf-8 -*-
"""Studio : Animation, t235 (17/10/2026) — le nœud « Direction motion » et les entrées `direction` / `script` de
l'Animation, bouton « Chorégraphier » branché sur t234 (POST /api/motion/choregraphier). Maillon de queue NEUF
`dzmotion` (scripts/patch_bundle_dzmotion.py), posé APRÈS dzstudio.

Ce que ce banc garde :
  [A] câblage dans le livré : type de port `direction`, catalogue (Animation : base / direction / script ; nœud
      MotionDirection, sortie direction), palette « Animations », encart, inspecteur, appel de t234 ;
  [F] sous node, avec les VRAIES fonctions extraites du livré (le catalogue `Me`, `Wt`, le bloc du maillon et
      `DzAnimation` en entier ; React et le réseau simulés) :
        - compilation du graphe → corps de t234 (script relié ou champ du nœud, direction, consigne d'un skill
          seulement, aspect du Rendu, durée, images déjà posées) ;
        - l'inspecteur Direction motion : styles, sources, moteurs (non configuré dit), bulle de coût, consigne du
          skill éditée dans le nœud, « Revenir à l'original », compteur, prompt en lecture seule + lien ;
        - « Chorégraphier » : la consigne éditée part dans l'appel, les éléments sont remplacés, confirmation s'il y
          en a déjà, Ctrl+Z rend l'état d'avant (pas dans un champ de saisie), refus et repli traduits ;
  [G] ancrage (t225-t227) rejoué sur l'Animation et Direction motion : qi = centre du rond rendu par ud, hauteur du
      corps = dzPortBodyH ;
  [D] chaîne dzmotion : sans = base octet pour octet, inverse `avant_dzmotion` EN TÊTE d'`avant_dzstudio`, comptes
      (x.useState( 731 inchangé, deux hooks par l'alias dzMoUS, v2.8.0 ×4, DzTracks 181, G1, littéral Fu), octets ;
  [K] aucune chaîne en dur : tout texte visible passe par une clé dzT `studio.motion.*` présente en FR ET EN ;
  [R] le miroir du registre des nœuds (backend/app/assets/studio_nodes.json) suit le livré.
Run (depuis backend/) : & $PY tests/test_studio_motion_direction.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

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
BASE = "bed401ad"            # origin/main 86c60a02 + t234 (refs/heads/claude/motion-choregraphe-t234-868f68), dzstudio en queue
NEUTRES = {"creativite": 2, "rythme": 2, "finition": 2}   # t241 : curseurs neutres, champs vides, effort « auto » (banc test_studio_motion_personnaliser)

print("[A] câblage dans le livré")
check("A1 type de port `direction` (couleur des Animations)",
      'data:{color:"var(--node-data)",label:"data"},direction:{color:"var(--nd-motion)",label:"direction"}},Qr={' in BUNDLE)
check("A2 Animation : entrées base, direction, script ; propriété script",
      'Animation:{cat:"motion",title:"Animation",desc:dzT("studio.catalogue.animation_desc"),inPorts:[{id:"base",type:"av"},'
      '{id:"direction",type:"direction"},{id:"script",type:"text"}],outPorts:[{id:"out",type:"av"}],'
      'props:{durationS:8,fps:30,elements:[],selected:0,script:""}}' in BUNDLE)
check("A3 nœud MotionDirection : catégorie motion, titre dzT, sortie direction",
      'MotionDirection:{cat:"motion",title:dzT("studio.motion.titre"),desc:dzT("studio.motion.desc"),inPorts:[],'
      'outPorts:[{id:"direction",type:"direction"}],' in BUNDLE)
check("A4 palette : Direction motion rangée dans Animations (t238 : puis Rendu motion code)",
      '{cat:"motion",types:["Animation","MotionDirection","MotionCode"]}' in BUNDLE)
check("A5 encart et inspecteur", 'n==="MotionDirection"?dzMotionEncart(o):n==="Animation"?' in BUNDLE
      and 'e.type==="MotionDirection"?r.jsx(DzMotionDirection,{node:e,graph:g,set:o}):e.type==="Animation"?' in BUNDLE)
check("A6 Chorégraphier appelle t234 en POST JSON", 'fetch("/api/motion/choregraphier",{method:"POST"' in BUNDLE)
check("A7 moteurs, modèles, bibliothèque : les routes t232 / t220 / t233",
      all(u in BUNDLE for u in ('"/api/motion/moteurs"', '"/api/settings/provider-defaults/modeles?moteur="',
                                '"/api/motion/biblio"', '"/api/motion/biblio/"')))

# ── [F] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
function objet(debut){const i=S.indexOf(debut);if(i<0)throw new Error("introuvable : "+debut);let k=i+debut.indexOf("{"),n=0,q=null;
 for(let j=k;j<S.length;j++){const c=S[j];if(q){if(c==="\\"){j++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")n++;else if(c==="}"){n--;if(!n)return S.slice(k,j+1)}}
 throw new Error("objet non fermé")}
let LANG="fr",H=[],hi=0,EFF=[],CALLS=[],SETS=[],LIS={},CONF=true,CONFS=[],ROUTES={};
const x={useState(init){const i=hi++;if(!(i in H))H[i]=typeof init==="function"?init():init;
  return [H[i],function(v){H[i]=typeof v==="function"?v(H[i]):v}]},useEffect(f){EFF.push(f)},useRef(){return{current:null}}};
const r={jsx(t,p){return{t,p:p||{}}},jsxs(t,p){return{t,p:p||{}}}};
const window={dzLang(){return LANG},addEventListener(t,f){LIS[t]=f},removeEventListener(t,f){if(LIS[t]===f)delete LIS[t]},
 __dzDialogue:{confirmer:async function(m,o){CONFS.push([m,o]);return CONF},saisir:async function(){return null}}};
async function fetch(u,o){CALLS.push({u,o:o||null});const f=ROUTES[u.split("?")[0]]||ROUTES["*"];const v=f?f(u,o):{status:404,j:{detail:"x"}};
 return{ok:(v.status||200)<400,status:v.status||200,json:async function(){return v.j}}}
const dzT=function(k,v){return k+(v?JSON.stringify(v):"")},dzMq=function(k){return"MQ:"+k};
const STUB={x,r,window,fetch,dzT,dzMq,localStorage:{getItem(){return null},setItem(){}},
 ie:"ie",O:"O",le:"le",re:"re",Ze:"Ze",DzColorPicker:"DzColorPicker",__dzGl(n){return"gl:"+n},__dzGlT(n,t){return t}};
const ENV=new Proxy(STUB,{has(t,k){return typeof k==="string"},get(t,k){if(k===Symbol.unscopables)return undefined;
 if(k in t)return t[k];if(k in globalThis)return globalThis[k];return function(){return null}}});
function arbre(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>arbre(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)arbre(n.p.children,f,acc);return acc}
function par(t,nom){return arbre(t,n=>n.p&&n.p["data-dz-motion"]===nom)[0]||null}
function champ(t,label){return arbre(t,n=>n.t==="O"&&n.p.label===label).map(n=>n.p.children)[0]||null}
function texte(n){if(n==null||n===false)return"";if(typeof n!=="object")return String(n);if(Array.isArray(n))return n.map(texte).join("");
 return texte(n.p&&n.p.children)}
async function vider(){for(let k=0;k<6;k++){const e=EFF;EFF=[];e.forEach(f=>f());await new Promise(s=>setTimeout(s,0))}}
function poseur(nd){return function(k,v){nd.props=Object.assign({},nd.props,{[k]:v});SETS.push([k,v])}}
function rendre(C,nd,g){hi=0;EFF=[];return C({node:nd,graph:g,set:poseur(nd)})}
(async function(){try{
 const SRC="var Me="+objet("Me={Image:")+";"+tranche("function Wt(","function dzFinImg(")+";"
  +tranche("var dzMoUS=","function DzAnimation(")+tranche("function DzAnimation(","var __dzManif3d=")
  +";return{Me,Wt,dzMotionPayload,dzMotionScript,dzMotionRaison,dzMotionBilan,dzMotionCout,dzMotionResume,dzMotionEncart,"
  +"dzMotionBulle,dzMoCache,dzMoPile,DzMotionDirection,DzAnimation}";
 const M=new Function("ENV","with(ENV){"+SRC+"}")(ENV);
 OUT.me={anim:M.Me.Animation,dir:M.Me.MotionDirection};
 const el=(t,f)=>({id:"el_"+t+(f||""),type:t,text:t==="text"?"T":undefined,filename:f,style:{},keyframes:[{t:0,x:1,y:1,scale:1,rotation:0,opacity:0},{t:1,x:2,y:2,scale:1,rotation:0,opacity:1}],start:0,dur:.8,hold:2});
 // F1 graphe complet
 const g1={nodes:[{id:"t",type:"Text",props:{value:"Ligne 1\nLigne 2"}},
  {id:"d",type:"MotionDirection",props:{style:"style-charts",source:"skill-a-b",consigne:"EDIT",moteur:"ollama",modele:"llama3"}},
  {id:"R",type:"Render",props:{format:"1:1"}},
  {id:"a",type:"Animation",props:{durationS:12,elements:[el("text"),el("image","a.png"),el("image","a.png"),el("sticker","s.png"),el("image","")]}}],
  edges:[{from:"t",fromPort:"out",to:"a",toPort:"script"},{from:"d",fromPort:"direction",to:"a",toPort:"direction"},{from:"a",fromPort:"out",to:"R",toPort:"in"}]};
 OUT.p1=M.dzMotionPayload(g1,g1.nodes[3]);
 const g2={nodes:[{id:"a",type:"Animation",props:{script:"Bonjour\nMonde"}}],edges:[]};
 OUT.p2=M.dzMotionPayload(g2,g2.nodes[0]);
 const g3={nodes:[{id:"d",type:"MotionDirection",props:{source:"prompt-x",consigne:"NE PART PAS"}},{id:"a",type:"Animation",props:{script:"s"}}],
  edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"}]};
 OUT.p3=M.dzMotionPayload(g3,g3.nodes[1]);
 const g4={nodes:[{id:"n",type:"NewsScript",props:{value:"Script des news"}},{id:"a",type:"Animation",props:{script:"ignoré"}}],
  edges:[{from:"n",fromPort:"script",to:"a",toPort:"script"}]};
 OUT.p4=M.dzMotionPayload(g4,g4.nodes[1]);
 const g5={nodes:[{id:"t",type:"Text"},{id:"x",type:"Prompt",props:{style:"style-charts",source:"skill-z",consigne:"C",moteur:"ollama",modele:"m"}},{id:"a",type:"Animation",props:{}}],
  edges:[{from:"t",fromPort:"out",to:"a",toPort:"script"},{from:"x",fromPort:"out",to:"a",toPort:"direction"}]};
 OUT.p5=M.dzMotionPayload(g5,g5.nodes[2]);
 OUT.raisons=["sans_moteur","moteur_inconnu","non_configure","modele_fautif","sortie_invalide","","zz"].map(M.dzMotionRaison);
 OUT.bilans=[M.dzMotionBilan({elements:[1,2],repli:false,moteur:"ollama",modele:"llama3",cout:{nature:"gratuit",estime_usd:0}}),
  M.dzMotionBilan({elements:[1],repli:true,raison:"non_configure",moteur:"anthropic",modele:"",cout:{nature:"payant"}}),
  M.dzMotionCout({nature:"payant",estime_usd:0.0123456}),M.dzMotionCout({nature:"a_mesurer"})];
 // F7 inspecteur Direction motion
 ROUTES["/api/motion/biblio"]=()=>({j:{entrees:[{id:"style-kinetic-type",nature:"style",titre:{fr:"Typographie cinétique",en:"Kinetic type"}},
  {id:"style-charts",nature:"style",titre:{fr:"Graphiques",en:"Charts"}},{id:"prompt-x",nature:"prompt",titre:"P1"},
  {id:"skill-y",nature:"skill",titre:"S1"}]}});
 ROUTES["/api/motion/moteurs"]=()=>({j:{moteurs:[{moteur:"ollama",configure:true,modele:"llama3",cout:"gratuit"},
  {moteur:"anthropic",configure:false,modele:"claude-x",cout:"payant"},{moteur:"fl:deepseek",configure:true,modele:"deepseek-chat",cout:"a_mesurer"}]}});
 ROUTES["/api/settings/provider-defaults/modeles"]=(u)=>({j:{modeles:u.indexOf("fl%3Adeepseek")>0?["deepseek-chat","deepseek-reasoner"]:["llama3"]}});
 ROUTES["/api/motion/biblio/skill-y"]=()=>({j:{id:"skill-y",nature:"skill",titre:"S1",consigne:"COPIE",original:"ORIGINAL"}});
 ROUTES["/api/motion/biblio/prompt-x"]=()=>({j:{id:"prompt-x",nature:"prompt",titre:"P1",texte:"TXT",url:"https://exemple.org/p/1",auteur:"Auteur A"}});
 const nd={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"",consigne:"",moteur:"",modele:""}},gd={nodes:[nd],edges:[]};
 H=[];let t=rendre(M.DzMotionDirection,nd,gd);OUT.d0=texte(t).indexOf("studio.motion.chargement")>=0;await vider();
 t=rendre(M.DzMotionDirection,nd,gd);
 const opt=l=>{const s=champ(t,l);return s&&s.p&&s.p.options};
 OUT.styles=opt("studio.motion.style");OUT.sources=opt("studio.motion.source");OUT.moteurs=opt("studio.motion.moteur");
 OUT.bulle0=par(t,"bulle")&&par(t,"bulle").p.title;OUT.sansModele=!champ(t,"studio.motion.modele");OUT.d1=texte(t).indexOf("studio.motion.chargement")<0;
 LANG="en";t=rendre(M.DzMotionDirection,nd,gd);OUT.stylesEn=opt("studio.motion.style");LANG="fr";
 SETS=[];champ(t,"studio.motion.source").p.onChange("skill-y");OUT.setsSource=SETS.slice();
 t=rendre(M.DzMotionDirection,nd,gd);await vider();t=rendre(M.DzMotionDirection,nd,gd);
 const ta=par(t,"consigne");OUT.cons0={v:ta&&ta.p.value,max:ta&&ta.p.maxLength,cpt:texte(par(t,"compteur")),rev:par(t,"revenir")&&par(t,"revenir").p.disabled};
 OUT.skillPlie=arbre(t,n=>n.t==="ie"&&n.p.label==="studio.motion.consigne_skill").map(n=>n.p.defaultOpen)[0];
 SETS=[];par(t,"revenir").p.onClick();OUT.setsRevenir=SETS.slice();t=rendre(M.DzMotionDirection,nd,gd);
 OUT.cons1={v:par(t,"consigne").p.value,cpt:texte(par(t,"compteur")),rev:par(t,"revenir").p.disabled};
 SETS=[];par(t,"consigne").p.onChange({target:{value:"MA CONSIGNE"}});t=rendre(M.DzMotionDirection,nd,gd);
 OUT.cons2={v:par(t,"consigne").p.value,cpt:texte(par(t,"compteur")),props:nd.props.consigne,prompt:!!par(t,"prompt")};
 SETS=[];champ(t,"studio.motion.moteur").p.onChange("fl:deepseek");OUT.setsMoteur=SETS.slice();
 t=rendre(M.DzMotionDirection,nd,gd);await vider();t=rendre(M.DzMotionDirection,nd,gd);
 OUT.modeles=(champ(t,"studio.motion.modele")||{p:{}}).p.options;OUT.modeleVal=(champ(t,"studio.motion.modele")||{p:{}}).p.value;
 OUT.bulle1=par(t,"bulle").p.title;
 const gdl={nodes:[nd,{id:"tt",type:"Text",props:{value:"Une ligne"}},{id:"a",type:"Animation",props:{elements:[]}}],
  edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"},{from:"tt",fromPort:"out",to:"a",toPort:"script"}]};
 OUT.pEdite=M.dzMotionPayload(gdl,gdl.nodes[2]);
 const np={id:"q",type:"MotionDirection",props:{style:"style-charts",source:"prompt-x",consigne:"",moteur:"ollama",modele:""}},gq={nodes:[np],edges:[]};
 H=[];t=rendre(M.DzMotionDirection,np,gq);await vider();t=rendre(M.DzMotionDirection,np,gq);
 const lien=par(t,"fiche");OUT.prompt={txt:par(t,"prompt-texte")&&par(t,"prompt-texte").p.value,ro:par(t,"prompt-texte")&&par(t,"prompt-texte").p.readOnly,
  href:lien&&lien.p.href,target:lien&&lien.p.target,rel:lien&&lien.p.rel,consigne:!!par(t,"consigne"),bulle:par(t,"bulle").p.title,
  auteur:texte(t).indexOf('studio.motion.prompt_auteur{"auteur":"Auteur A"}')>=0};
 OUT.encart=(function(){const e=M.dzMotionEncart({style:"style-charts",source:"skill-y",moteur:"ollama",modele:"llama3"});
  return{title:e.p.title,txt:texte(e)}})();
 OUT.encartVide=M.dzMotionEncart({style:"style-inconnu",source:"",moteur:"",modele:""}).p.title;
 // F8 DzAnimation : Chorégraphier
 const elsRep=[el("text"),el("text","b")];let REP={j:{elements:elsRep,moteur:"ollama",modele:"llama3",repli:false,raison:"",cout:{nature:"gratuit",estime_usd:0}}};
 ROUTES["/api/motion/choregraphier"]=()=>REP;
 const an={id:"a",type:"Animation",props:{durationS:8,fps:30,elements:[],selected:0}};
 const ga={nodes:[{id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"skill-y",consigne:"MA CONSIGNE",moteur:"ollama",modele:"llama3"}},
  {id:"tt",type:"Text",props:{value:"Un\nDeux"}},an],edges:[{from:"d",fromPort:"direction",to:"a",toPort:"direction"},{from:"tt",fromPort:"out",to:"a",toPort:"script"}]};
 H=[];CALLS=[];CONFS=[];t=rendre(M.DzAnimation,an,ga);
 OUT.bloc={script:!!par(t,"script"),relie:texte(par(t,"script-relie")),dir:texte(par(t,"direction")),btn:texte(par(t,"choregraphier"))};
 SETS=[];await par(t,"choregraphier").p.onClick();
 const c1=CALLS.filter(c=>c.u==="/api/motion/choregraphier");
 OUT.appel1={n:c1.length,methode:c1[0]&&c1[0].o.method,ct:c1[0]&&c1[0].o.headers["Content-Type"],corps:c1[0]&&JSON.parse(c1[0].o.body),
  attendu:M.dzMotionPayload(ga,an),confs:CONFS.length,sets:SETS.map(s=>s[0]),elements:an.props.elements===elsRep,sel:an.props.selected};
 t=rendre(M.DzAnimation,an,ga);OUT.msg1=texte(par(t,"message"));
 // déjà des éléments : confirmation
 CONF=false;CALLS=[];CONFS=[];SETS=[];await par(t,"choregraphier").p.onClick();
 OUT.refus={confs:CONFS.length,msg:CONFS[0]&&CONFS[0][0],ok:CONFS[0]&&CONFS[0][1].ok,appels:CALLS.length,sets:SETS.length};
 an.props.selected=1;CONF=true;CALLS=[];CONFS=[];const elsRep2=[el("sticker","z.png")];REP={j:{elements:elsRep2,moteur:"ollama",modele:"llama3",repli:false,cout:{nature:"gratuit"}}};
 t=rendre(M.DzAnimation,an,ga);await par(t,"choregraphier").p.onClick();
 OUT.remplace={confs:CONFS.length,appels:CALLS.length,elements:an.props.elements===elsRep2,pile:M.dzMoPile.a.length,sel:an.props.selected};
 // Ctrl+Z
 t=rendre(M.DzAnimation,an,ga);await vider();const k=LIS.keydown;let pd=0;
 SETS=[];k&&k({ctrlKey:true,key:"z",target:{tagName:"TEXTAREA"},preventDefault(){pd++}});OUT.zChamp={sets:SETS.length,pd};
 SETS=[];k&&k({ctrlKey:true,shiftKey:true,key:"Z",target:{tagName:"DIV"},preventDefault(){pd++}});OUT.zMaj={sets:SETS.length};
 SETS=[];k&&k({ctrlKey:true,key:"z",target:{tagName:"DIV"},preventDefault(){pd++}});
 OUT.z1={elements:an.props.elements===elsRep,sel:an.props.selected,pd,pile:M.dzMoPile.a.length};
 t=rendre(M.DzAnimation,an,ga);OUT.zMsg=texte(par(t,"message"));
 SETS=[];k&&k({metaKey:true,key:"z",target:{tagName:"DIV"},preventDefault(){}});OUT.z2={elements:Array.isArray(an.props.elements)&&an.props.elements.length===0,pile:M.dzMoPile.a.length};
 SETS=[];k&&k({ctrlKey:true,key:"z",target:{tagName:"DIV"},preventDefault(){}});OUT.z3={sets:SETS.length};
 // repli traduit, refus HTTP, script vide, champ Script
 REP={j:{elements:[el("text")],moteur:"anthropic",modele:"",repli:true,raison:"non_configure",cout:{nature:"payant",estime_usd:0}}};
 an.props.elements=[];t=rendre(M.DzAnimation,an,ga);await par(t,"choregraphier").p.onClick();t=rendre(M.DzAnimation,an,ga);OUT.msgRepli=texte(par(t,"message"));
 REP={status:404,j:{detail:"Entrée inconnue : skill-y"}};const avant404=an.props.elements;
 t=rendre(M.DzAnimation,an,ga);CONF=true;await par(t,"choregraphier").p.onClick();t=rendre(M.DzAnimation,an,ga);
 OUT.err404={msg:texte(par(t,"message")),inchange:an.props.elements===avant404,couleur:par(t,"message").p.style.color};
 const a2={id:"a2",type:"Animation",props:{elements:[],script:"  "}},g6={nodes:[a2],edges:[]};
 H=[];CALLS=[];t=rendre(M.DzAnimation,a2,g6);OUT.vide0={script:!!par(t,"script"),dir:texte(par(t,"direction"))};
 await par(t,"choregraphier").p.onClick();t=rendre(M.DzAnimation,a2,g6);OUT.vide={appels:CALLS.length,msg:texte(par(t,"message"))};
 SETS=[];par(t,"script").p.onChange({target:{value:"Texte du champ"}});OUT.champ={sets:SETS,p:M.dzMotionPayload(g6,a2).script};
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[F] sous node, vraies fonctions du livré")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzmotion_node_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js")], capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120)
try:
    F = json.loads(rn.stdout or "{}")
except ValueError:
    F = {"err": (rn.stdout or "")[-300:] + (rn.stderr or "")[-300:]}
check("F0 catalogue, Wt, bloc du maillon et DzAnimation extraits et exécutés", "err" not in F, str(F.get("err", ""))[:400])
check("F1 graphe complet → corps de t234 (script relié, direction, consigne du skill, Rendu 1:1, durée, images uniques)",
      F.get("p1") == {"script": "Ligne 1\nLigne 2", "direction": {"style": "style-charts", "source": "skill-a-b", "consigne": "EDIT", "champs": {}, "curseurs": NEUTRES, "precisions": {}},
                      "moteur": "ollama", "modele": "llama3", "effort": "auto", "aspect": "1:1", "duree_s": 12, "images": ["a.png", "s.png"]},
      str(F.get("p1")))
check("F2 rien de relié : le champ Script, direction vide, 9:16, durée du catalogue (8 s)",
      F.get("p2") == {"script": "Bonjour\nMonde", "direction": {"style": "", "source": None, "consigne": "", "champs": {}, "curseurs": NEUTRES}, "moteur": "",
                      "modele": "", "effort": "auto", "aspect": "9:16", "duree_s": 8, "images": []}, str(F.get("p2")))
check("F3 source prompt : la consigne ne part pas (le prompt est en lecture seule)",
      (F.get("p3") or {}).get("direction") == {"style": "style-kinetic-type", "source": "prompt-x", "consigne": "", "champs": {}, "curseurs": NEUTRES, "precisions": {}},
      str(F.get("p3")))
check("F4 Script News relié sur `script` : son texte, le champ du nœud ignoré", (F.get("p4") or {}).get("script") == "Script des news")
check("F5 Texte au texte par défaut (dzMq) ; un nœud qui n'est pas Direction motion sur `direction` est ignoré",
      (F.get("p5") or {}).get("script") == "MQ:texte" and (F.get("p5") or {}).get("direction") == {"style": "", "source": None, "consigne": "", "champs": {}, "curseurs": NEUTRES}
      and (F.get("p5") or {}).get("moteur") == "" and (F.get("p5") or {}).get("modele") == "",
      str(F.get("p5")))
check("F6 les cinq codes `raison` de t234 → cinq clés dzT, inconnu → rien",
      F.get("raisons") == ["studio.motion.raison_" + c for c in ("sans_moteur", "moteur_inconnu", "non_configure", "modele_fautif",
                                                                  "sortie_invalide")] + ["", ""], str(F.get("raisons")))
B_ = F.get("bilans") or [""] * 4
check("F7 bilans : moteur · modèle et coût ; repli avec sa raison ; coût payant estimé à 4 décimales ; prix à mesurer",
      B_[0] == 'studio.motion.bilan{"n":2,"moteur":"ollama · llama3","cout":"studio.motion.cout_bilan_gratuit"}'
      and B_[1] == 'studio.motion.bilan_repli{"n":1,"raison":"studio.motion.raison_non_configure"}'
      and B_[2] == 'studio.motion.cout_bilan_payant{"usd":"0.0123"}' and B_[3] == "studio.motion.cout_bilan_a_mesurer", str(B_))
check("F8 Direction motion : « chargement » le temps de la bibliothèque, puis les styles (titres FR, puis EN)",
      F.get("d0") is True and F.get("d1") is True
      and F.get("styles") == [{"value": "style-kinetic-type", "label": "Typographie cinétique"}, {"value": "style-charts", "label": "Graphiques"}]
      and [o["label"] for o in F.get("stylesEn") or []] == ["Kinetic type", "Charts"], str(F.get("styles")))
check("F9 sources : Aucune, puis prompt et skill nommés", F.get("sources") == [
    {"value": "", "label": "studio.motion.source_aucune"}, {"value": "prompt-x", "label": 'studio.motion.source_prompt{"titre":"P1"}'},
    {"value": "skill-y", "label": 'studio.motion.source_skill{"titre":"S1"}'}], str(F.get("sources")))
check("F10 moteurs : Aucun (maison), puis chacun ; un moteur non configuré le dit ; sans moteur : bulle « gratuit, rien n'est envoyé », pas de modèle",
      F.get("moteurs") == [{"value": "", "label": "studio.motion.moteur_aucun"}, {"value": "ollama", "label": "ollama"},
                           {"value": "anthropic", "label": 'studio.motion.moteur_non_configure{"moteur":"anthropic"}'},
                           {"value": "fl:deepseek", "label": "fl:deepseek"}]
      and F.get("bulle0") == "studio.motion.cout_aucun" and F.get("sansModele") is True, str(F.get("moteurs")))
check("F11 choisir une source remet la consigne à vide (pas de reste d'une autre source)",
      F.get("setsSource") == [["source", "skill-y"], ["consigne", ""]], str(F.get("setsSource")))
c0, c1, c2 = F.get("cons0") or {}, F.get("cons1") or {}, F.get("cons2") or {}
check("F12 skill : sa consigne (copie de la bibliothèque) dans une zone repliable ouverte, bornée à 8000, compteur « modifiée »",
      c0.get("v") == "COPIE" and c0.get("max") == 8000 and F.get("skillPlie") is True
      and c0.get("cpt") == 'studio.motion.compteur_modifie{"n":5,"max":8000}' and c0.get("rev") is False, str(c0))
check("F13 « Revenir à l'original » écrit le SKILL.md d'origine ; le bouton s'éteint, le compteur n'est plus « modifiée »",
      F.get("setsRevenir") == [["consigne", "ORIGINAL"]] and c1.get("v") == "ORIGINAL" and c1.get("rev") is True
      and c1.get("cpt") == 'studio.motion.compteur{"n":8,"max":8000}', str(c1))
check("F14 consigne éditée dans le nœud : gardée dans le nœud, compteur à jour, aucun bloc prompt",
      c2.get("v") == "MA CONSIGNE" and c2.get("props") == "MA CONSIGNE" and c2.get("prompt") is False
      and c2.get("cpt") == 'studio.motion.compteur_modifie{"n":11,"max":8000}', str(c2))
check("F15 la consigne éditée part dans le corps de t234", (F.get("pEdite") or {}).get("direction") == {
    "style": "style-kinetic-type", "source": "skill-y", "consigne": "MA CONSIGNE", "champs": {}, "curseurs": NEUTRES, "precisions": {}}, str(F.get("pEdite")))
check("F16 changer de moteur vide le modèle ; ses modèles sont lus ; modèle par défaut = celui des Réglages ; bulle « prix à mesurer »",
      F.get("setsMoteur") == [["moteur", "fl:deepseek"], ["modele", ""]]
      and F.get("modeles") == [{"value": "deepseek-chat", "label": "deepseek-chat"}, {"value": "deepseek-reasoner", "label": "deepseek-reasoner"}]
      and F.get("modeleVal") == "deepseek-chat"
      and F.get("bulle1") == 'studio.motion.cout_a_mesurer{"moteur":"fl:deepseek · deepseek-chat"} · studio.motion.effort_bulle_seul', str(F.get("bulle1")))
P_ = F.get("prompt") or {}
check("F17 prompt : texte en lecture seule, lien vers la fiche d'origine (nouvel onglet, noopener), auteur, pas de consigne éditable ; bulle gratuite d'Ollama",
      P_.get("txt") == "TXT" and P_.get("ro") is True and P_.get("href") == "https://exemple.org/p/1" and P_.get("target") == "_blank"
      and "noopener" in str(P_.get("rel")) and P_.get("consigne") is False and P_.get("auteur") is True
      and P_.get("bulle") == 'studio.motion.cout_gratuit{"moteur":"ollama · llama3"} · studio.motion.effort_bulle_seul', str(P_))
check("F18 encart en une ligne : style · source · moteur · modèle (titres de la bibliothèque), `title` = le texte ; inconnu → id nu, maison",
      (F.get("encart") or {}).get("title") == "Graphiques · S1 · ollama · llama3"
      and "Graphiques · S1 · ollama · llama3" in (F.get("encart") or {}).get("txt", "")
      and F.get("encartVide") == "inconnu · studio.motion.source_aucune · studio.motion.encart_maison", str(F.get("encart")))
bl = F.get("bloc") or {}
check("F19 Animation : direction reliée résumée, script relié nommé (pas de champ), bouton « Chorégraphier »",
      bl.get("script") is False and bl.get("relie") == 'studio.motion.script_relie{"titre":"studio.catalogue.texte_titre"}'
      and bl.get("dir", "").startswith('studio.motion.direction_reliee{"resume":"Typographie cinétique · S1 · ollama · llama3"}')
      and bl.get("btn") == "studio.motion.choregraphier", str(bl))
a1 = F.get("appel1") or {}
check("F20 « Chorégraphier » : un POST JSON à t234, corps = la compilation du graphe, consigne éditée comprise",
      a1.get("n") == 1 and a1.get("methode") == "POST" and a1.get("ct") == "application/json" and a1.get("corps") == a1.get("attendu")
      and (a1.get("corps") or {}).get("direction", {}).get("consigne") == "MA CONSIGNE" and (a1.get("corps") or {}).get("script") == "Un\nDeux",
      str(a1.get("corps")))
check("F21 sans élément : pas de confirmation ; éléments remplacés par la réponse, sélection 0 ; bilan traduit",
      a1.get("confs") == 0 and a1.get("elements") is True and a1.get("sel") == 0 and a1.get("sets") == ["elements", "selected"]
      and F.get("msg1") == 'studio.motion.bilan{"n":2,"moteur":"ollama · llama3","cout":"studio.motion.cout_bilan_gratuit"}', str(F.get("msg1")))
rf = F.get("refus") or {}
check("F22 déjà des éléments : confirmation (nombre d'éléments, bouton Remplacer) ; refusée → aucun appel, rien ne change",
      rf.get("confs") == 1 and rf.get("msg") == 'studio.motion.remplacer{"n":2}' and rf.get("ok") == "studio.motion.remplacer_ok"
      and rf.get("appels") == 0 and rf.get("sets") == 0, str(rf))
rp = F.get("remplace") or {}
check("F23 confirmée → appel, éléments remplacés, sélection 0, l'état d'avant empilé", rp.get("confs") == 1 and rp.get("appels") == 1
      and rp.get("elements") is True and rp.get("pile") == 2 and rp.get("sel") == 0, str(rp))
check("F24 Ctrl+Z dans un champ de saisie, ou Ctrl+Maj+Z : rien", (F.get("zChamp") or {}).get("sets") == 0
      and (F.get("zChamp") or {}).get("pd") == 0 and (F.get("zMaj") or {}).get("sets") == 0, str(F.get("zChamp")))
z1 = F.get("z1") or {}
check("F25 Ctrl+Z : l'état d'avant revient (éléments et sélection 1), touche consommée, message « annulée »",
      z1.get("elements") is True and z1.get("sel") == 1 and z1.get("pd") == 1 and z1.get("pile") == 1
      and F.get("zMsg") == "studio.motion.annule", str(z1))
check("F26 Cmd+Z (Mac) remonte encore d'un cran, jusqu'à l'Animation vide ; pile vide → rien",
      (F.get("z2") or {}).get("elements") is True and (F.get("z2") or {}).get("pile") == 0 and (F.get("z3") or {}).get("sets") == 0,
      str(F.get("z2")))
check("F27 repli de t234 : bilan « chorégraphie maison » avec la raison traduite",
      F.get("msgRepli") == 'studio.motion.bilan_repli{"n":1,"raison":"studio.motion.raison_non_configure"}', str(F.get("msgRepli")))
e4 = F.get("err404") or {}
check("F28 refus HTTP : son message (déjà traduit par le serveur) en rouge, éléments inchangés",
      e4.get("msg") == "Entrée inconnue : skill-y" and e4.get("inchange") is True and e4.get("couleur") == "var(--red)", str(e4))
check("F29 rien de relié : champ Script, « aucune Direction motion » ; script vide → aucun appel, message",
      (F.get("vide0") or {}).get("script") is True and (F.get("vide0") or {}).get("dir") == "studio.motion.direction_absente"
      and (F.get("vide") or {}).get("appels") == 0 and (F.get("vide") or {}).get("msg") == "studio.motion.script_vide", str(F.get("vide")))
check("F30 le champ Script écrit la propriété `script`, que la compilation lit",
      (F.get("champ") or {}).get("sets") == [["script", "Texte du champ"]] and (F.get("champ") or {}).get("p") == "Texte du champ",
      str(F.get("champ")))

# ── [G] ancrage rejoué ────────────────────────────────────────────────────────────────────────────────────────────
ANCRAGE = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);return S.slice(i,j)}
function objet(debut){const i=S.indexOf(debut);let k=i+debut.indexOf("{"),n=0,q=null;
 for(let j=k;j<S.length;j++){const c=S[j];if(q){if(c==="\\"){j++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")n++;else if(c==="}"){n--;if(!n)return S.slice(k,j+1)}}}
try{
 const K=/bi=(\d+),Ru=(\d+),Mu=(\d+)/.exec(S);const bi=+K[1],Ru=+K[2],Mu=+K[3];
 const UR="var Ur="+objet("Ur={image:")+";";
 const SRC=UR+"var Me="+objet("Me={Image:")+";"+tranche("var dzPortGeo=","function Th(")+";"+tranche("function ud(","var __dzG=");
 const r={jsx(t,p){return{t,p}},jsxs(t,p){return{t,p}}};
 const BASE={r,bi,Ru,Mu,dzT:k=>k,dzMq:k=>k};
 const ENV=new Proxy(BASE,{has(t,k){return typeof k==="string"},get(t,k){if(k===Symbol.unscopables)return undefined;
  if(k in t)return t[k];if(k in globalThis)return globalThis[k];return function(){return null}}});
 const M=new Function("ENV","with(ENV){"+SRC+";return{qi,ud,dzPortBodyH,dzVisInPorts,Me,Ur}}")(ENV);
 const L=[];
 for(const ty of ["Animation","MotionDirection"]){const u=M.Me[ty],nd={id:"n",type:ty,props:{}};
  for(const side of ["in","out"]){(side==="in"?M.dzVisInPorts(nd,u):u.outPorts).forEach((pt,i)=>{
   const q=M.qi(ty,side,pt.id,nd),row=M.ud({side,port:pt,index:i,onPress(){},onRelease(){}}),rs=row.p.style,dot=row.p.children[0].p.style;
   const off=side==="in"?rs.left:rs.right;
   L.push({ty,side,id:pt.id,i,qx:q.x,qy:q.y,cx:side==="in"?1+off+dot.width/2:bi-1-off-dot.width/2,cy:1+Ru+rs.top+dot.height/2,
    couleur:M.Ur[pt.type]&&M.Ur[pt.type].color})})}
  OUT[ty]={h:M.dzPortBodyH(M.dzVisInPorts(nd,u).length,u.outPorts.length),nIn:M.dzVisInPorts(nd,u).length,nOut:u.outPorts.length}}
 OUT.L=L;OUT.Ru=Ru;OUT.Mu=Mu;OUT.bi=bi;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));
"""
print("[G] ancrage rejoué sur l'Animation et Direction motion")
(d / "g.js").write_text(ANCRAGE, encoding="utf-8")
rg = subprocess.run(["node", str(d / "g.js"), str(d / "b.js")], capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    G = json.loads(rg.stdout or "{}")
except ValueError:
    G = {"err": (rg.stdout or "")[-300:] + (rg.stderr or "")[-300:]}
check("G0 Ur, Me, qi, ud, dzPortBodyH extraits et exécutés", "err" not in G, str(G.get("err", ""))[:300])
L = G.get("L", [])
check("G1 Animation : entrées base, direction, script dans cet ordre ; Direction motion : sortie direction seule",
      [(p["ty"], p["side"], p["id"]) for p in L] == [("Animation", "in", "base"), ("Animation", "in", "direction"),
                                                     ("Animation", "in", "script"), ("Animation", "out", "out"),
                                                     ("MotionDirection", "out", "direction")], str([(p["ty"], p["id"]) for p in L]))
check("G2 chaque lien atterrit au centre du rond rendu (x et y), pas Mu entre deux entrées",
      bool(L) and all(abs(p["qx"] - p["cx"]) < 1e-9 and abs(p["qy"] - p["cy"]) < 1e-9 for p in L)
      and L[1]["qy"] - L[0]["qy"] == G.get("Mu") and L[2]["qy"] - L[1]["qy"] == G.get("Mu"), str([(p["qx"], p["cx"], p["qy"], p["cy"]) for p in L]))
check("G3 hauteur du corps = dzPortBodyH : 8 + 2·22 + 16 + 10 = 78 (Animation, 3 entrées) ; 8 + 16 + 10 = 34 (Direction motion)",
      (G.get("Animation") or {}).get("h") == 78 and (G.get("MotionDirection") or {}).get("h") == 34, str(G.get("Animation")))
check("G4 le port direction a sa couleur (catégorie Animations) aux deux bouts",
      [p["couleur"] for p in L if p["id"] == "direction"] == ["var(--nd-motion)", "var(--nd-motion)"])

# ── [D] chaîne ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] maillon de queue dzmotion")


def git_bundle(rev):
    r_ = subprocess.run(["git", "show", f"{rev}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
    if r_.returncode != 0:
        return None
    b_ = r_.stdout                                  # blob normalisé LF (autocrlf) → les CRLF du fichier extrait
    return b_ if b"\r\n" in b_ else b_.replace(b"\n", b"\r\n")


try:
    import patch_bundle_dzmotion as M                                # noqa: E402
except ImportError as e:
    M = None
    check("D0 scripts/patch_bundle_dzmotion.py existe", False, str(e))
if M:
    import _i18n_l1_aide as AIDE                                     # noqa: E402
    import patch_bundle_dzstudio as MS                               # noqa: E402
    try:
        avant = M.defaire(BUNDLE)
    except AssertionError as e:
        avant = None
        check("D1 toutes les paires sont dans le livré", False, str(e)[:160])
    base = git_bundle(BASE)
    if avant is not None:
        check("D1 marqueur ×1 dans le livré, absent avant", BUNDLE.count(M.MARKER) == 1 and M.MARKER not in avant)
        check("D2 sans le maillon = la base (origin/main + t234) octet pour octet", base is not None and avant.encode("utf-8") == base)
        check("D3 aller-retour exact", M.appliquer(avant) == BUNDLE)
        check("D4 sonde amont : le marqueur de dzstudio (et sa famille G) tient sur l'avant",
              any(t == "dzstudio" for t, _j, _n in M.SONDE_AMONT) and all(avant.count(j) == n for _t, j, n in M.SONDE_AMONT))
        check("D5 avant_dzmotion = défaire ; sans marqueur : rendu tel quel", hasattr(AIDE, "avant_dzmotion")
              and AIDE.avant_dzmotion(BUNDLE) == avant and AIDE.avant_dzmotion(avant) == avant)
        src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
        j = src_aide.find("def avant_dzstudio(")
        check("D6 avant_dzmotion appelé EN TÊTE d'avant_dzstudio",
              j > 0 and "bundle = avant_dzmotion(bundle)" in src_aide[j:src_aide.find("import patch_bundle_dzstudio as _m", j)])
        check("D7 avant_dzstudio(livré) == avant_dzstudio(avant) == dzstudio défait de l'avant",
              AIDE.avant_dzstudio(BUNDLE) == AIDE.avant_dzstudio(avant) == MS.defaire(avant))
    check("D8 x.useState( reste à 731 (sondé par une cinquantaine de bancs) ; les hooks du maillon passent par l'alias dzMoUS : "
          "TROIS appels (l'état de rafraîchissement de DzMotionDirection, le bilan de DzAnimation ; t238 : l'état de DzMotionCode)",
          BUNDLE.count("x.useState(") == 731 and BUNDLE.count("dzMoUS(") == 3 == M.HOOKS and "var dzMoUS=x.useState," in BUNDLE
          and BUNDLE.count("dzMoUE(") == 3)
    check("D9 v2.8.0 ×4, DzTracks 181", BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
    try:
        _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
    except (OSError, ValueError, KeyError):
        _g1 = []
    check("D10 aucun remplacement G1 (dzglyph_paires.json) ne bouge", bool(_g1) and avant is not None
          and all(BUNDLE.count(x_) == avant.count(x_) for x_ in _g1))
    check("D11 le littéral Fu intouché", avant is not None and BUNDLE.count("Fu") == avant.count("Fu")
          and not any("Fu" in r_ for _a, r_ in M.PAIRES))
    check("D12 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
    check("D13 aucun .bak_dzmotion laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzmotion")).exists())
    src_m = (RACINE / "scripts" / "patch_bundle_dzmotion.py").read_text(encoding="utf-8")
    check("D14 le maillon lit et écrit en octets", "read_bytes" in src_m and "write_bytes" in src_m and "read_text" not in src_m)
    check("D15 garde : un bundle sans une paire est « partiellement appliqué »", avant is not None
          and M.partiel(BUNDLE.replace(M.PAIRES[2][1], M.PAIRES[2][0], 1)) and not M.partiel(BUNDLE) and not M.partiel(avant))
    rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzmotion.py"), "--check"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("D16 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)
    if NODE := next((p for p in ("node",) if subprocess.run([p, "--version"], capture_output=True).returncode == 0), None):
        r_ = subprocess.run([NODE, "--check", str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("D17 node --check du livré", r_.returncode == 0, (r_.stderr or "")[-300:])

    # ── [K] textes ────────────────────────────────────────────────────────────────────────────────────────────────
    print("[K] aucune chaîne en dur, clés FR et EN")
    LIT = re.compile(r'"((?:[^"\\]|\\.)*)"|`([^`]*)`')
    PHRASE = re.compile(r"[A-Za-zÀ-ÿ]{2,}\s+[A-Za-zÀ-ÿ]{2,}")
    LISTE_BLANCHE = {"—", " · "}               # tiret « rien » (option vide, style absent) ; séparateur de l'encart

    def neufs(a, r_):
        la = {x_ or y_ for x_, y_ in LIT.findall(a)}
        return [x_ or y_ for x_, y_ in LIT.findall(r_) if (x_ or y_) not in la]

    NEUFS = [s for a, r_ in M.PAIRES for s in neufs(a, r_)]
    CLES = sorted({s for s in NEUFS if s.startswith("studio.motion.")})
    phrases = [s for s in NEUFS if PHRASE.search(s) and not s.startswith(("var(", "1px solid", "1px dashed", "noopener noreferrer"))]
    check("K1 aucun littéral neuf n'est une phrase", not phrases, str(phrases[:5]))
    non_ascii = sorted({s for s in NEUFS if any(ord(c) > 127 for c in s)} - LISTE_BLANCHE)
    check("K2 aucun littéral neuf non ASCII hors liste blanche (accents = texte français)", not non_ascii, str(non_ascii))
    JETONS = {"direction", "text", "av", "motion", "MotionDirection", "Animation", "Render", "base", "out", "script", "style",
              "source", "consigne", "moteur", "modele", "elements", "selected", "skill", "prompt", "gratuit", "payant",
              "a_mesurer", "sans_moteur", "moteur_inconnu", "non_configure", "modele_fautif", "sortie_invalide", "object",
              "undefined", "string", "en", "fr", "keydown", "z", "input", "textarea", "select", "div", "span", "a", "button", "POST",
              "ollama", "status", "flex", "center", "hidden", "ellipsis", "nowrap", "vertical", "inherit", "none", "pointer",
              "default", "ie", "_blank", "bloc", "encart", "bulle", "fiche", "compteur", "revenir", "message", "choregraphier",
              "inline", "inline-flex", "box", "border-box", "noopener",
              # t241 (rubrique Personnaliser) : propriétés du nœud, types de champ des fiches, types d'input, clés React
              "champs", "precisions", "curseurs", "creativite", "rythme", "finition", "tempo", "aspect", "duree", "police",
              "couleur", "couleur_marque", "effort", "auto", "liste", "nombre", "number", "range", "color", "uppercase",
              "perso", "apercu", "reprendre", "prec", "ra", "format",
              # t236 (bandeau Bibliothèque motion) : méthode HTTP, valeurs CSS, champs et états du magasin dzMoBib
              # (ti/tx/u/au/th/sk/ap/fl, busy = import / lire / installer / suppr), clés React des lignes du bandeau
              "DELETE", "wrap", "biblio", "ti", "tx", "u", "au", "th", "sk", "ap", "fl", "import", "lire", "installer",
              "suppr", "ia", "bt", "bx", "bu", "ba", "bth", "bat", "bap", "bi", "sa", "bs", "bl", "bf", "bli", "bv", "bm",
              "b", "i", "s", "t",
              # t238 (nœud Rendu motion code) : type et propriétés du nœud, port du Rendu, source de base, raison du repli
              "MotionCode", "durationS", "fps", "pageId", "in", "motion_code", "page_refusee",
              # 19/10 (PR #390, délais) : raisons du repli quand le moteur ne répond pas à temps ou renvoie une erreur
              "delai", "erreur_moteur"}
    mots = sorted({s for s in NEUFS if re.fullmatch(r"[A-Za-z_]+", s)} - JETONS)
    check("K3 mots seuls neufs : uniquement des jetons de code connus", not mots, str(mots))
    dico = {}
    for f_ in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        dico.update(json.loads(f_.read_bytes().decode("utf-8")))
    manq = [k for k in CLES if not (dico.get(k, {}).get("fr", "").strip() and dico.get(k, {}).get("en", "").strip())]
    check("K4 chaque clé studio.motion.* des paires a son FR ET son EN", bool(CLES) and not manq, str(manq))
    MO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "motion.json").read_bytes().decode("utf-8")) \
        if (RACINE / "frontend" / "shared" / "i18n" / "motion.json").is_file() else {}
    check("K5 motion.json : uniquement des clés studio.motion.*, toutes employées par le maillon (aucune orpheline)",
          bool(MO) and all(k.startswith("studio.motion.") for k in MO) and sorted(MO) == CLES,
          str(sorted(set(MO) ^ set(CLES))[:6]))
    check("K6 mêmes {variables} en FR et en EN", all(sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
                                                     for v in MO.values()) and bool(MO))
    rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("K7 le dictionnaire assemblé est à jour (motion.json compris)", rc.returncode == 0 and bool(MO), rc.stdout + rc.stderr)
    dzt = re.findall(r'dzT\("([a-z0-9_.]+)"', "".join(r_ for _a, r_ in M.PAIRES))
    check("K8 tout dzT( des paires vise une clé connue", bool(dzt) and all(k in dico for k in dzt), str([k for k in dzt if k not in dico]))

# ── [R] miroir du registre ────────────────────────────────────────────────────────────────────────────────────────
print("[R] miroir du registre des nœuds")
MIR = json.loads((RACINE / "backend" / "app" / "assets" / "studio_nodes.json").read_bytes().decode("utf-8"))
T = MIR.get("types", {})
check("R1 38 types (t238 : + MotionCode) ; MotionDirection (motion, « Motion direction », sortie direction, aucune entrée)",
      MIR.get("count") == 38 == len(T) and (T.get("MotionDirection") or {}).get("cat") == "motion"
      and (T.get("MotionDirection") or {}).get("title") == "Motion direction" and (T.get("MotionDirection") or {}).get("in") == []
      and (T.get("MotionDirection") or {}).get("out_types") == {"direction": "direction"}, str(T.get("MotionDirection")))
check("R2 Animation : entrées base (av), direction (direction), script (text)", (T.get("Animation") or {}).get("in") == ["base", "direction", "script"]
      and (T.get("Animation") or {}).get("in_types") == {"base": "av", "direction": "direction", "script": "text"}, str(T.get("Animation")))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "qa" / "dump_studio_registry.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
check("R3 dump --check : le miroir suit le livré", rc.returncode == 0, (rc.stdout + rc.stderr)[-300:])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
