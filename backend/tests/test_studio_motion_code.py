# -*- coding: utf-8 -*-
"""Studio : Animation, t238 (19/10/2026) — le nœud « Rendu motion code » (option B validée par l'utilisateur), famille C
du maillon de queue `dzmotion` (scripts/patch_bundle_dzmotion.py). Le serveur et le bac à sable sont gardés par
test_motion_code.py ; ici, l'écran :
  [A] câblage dans le livré : nœud MotionCode (motion, entrées direction / script, sortie av), palette « Animations »,
      encart, inspecteur, appels de /api/motion/code/ecrire, /api/motion/code/{id} et /api/motion/code/rendre ;
  [F] sous node, avec les VRAIES fonctions extraites du livré (catalogue `Me`, `Wt`, le bloc du maillon, la compilation
      `Mh` entière ; React et le réseau simulés) :
        - le corps d'« Écrire la page » = celui de t234 (direction reliée, script relié ou champ, format du Rendu,
          durée) + la cadence bornée 12-60, sans `images` ;
        - la base de l'Animation reliée à un MotionCode → {source_kind:"motion_code", page_id, aspect, fps, duree_s} de
          l'Animation, portée jusqu'à POST /api/animate ; sans page écrite : la compilation le dit ;
        - MotionCode relié à l'entrée `in` du Rendu → POST /api/motion/code/rendre (format du Rendu, cadence, durée,
          titre, graphe) ; sans page : refus traduit ;
        - l'inspecteur : direction reliée ou absente, champ Script (ou script relié), Durée, Images par seconde,
          « Écrire la page » → bilan (moteur, taille, coût / repli et sa raison, motifs du refus) → pageId posé, bouton
          « Réécrire », page en LECTURE SEULE (zone de saisie, jamais un document) ; script vide → aucun appel ;
          erreur 402 → son message ;
  [S] sûreté de l'écran : le code de la page n'entre jamais dans le DOM comme document (ni dangerouslySetInnerHTML,
      ni iframe / srcdoc, ni eval / Function, ni Blob / createObjectURL dans la famille C) ;
  [D] chaîne dzmotion : sans le maillon = la base octet pour octet ; aller-retour ; comptes (x.useState( 731, dzMoUS
      2 → 3 = HOOKS : un état neuf, celui de DzMotionCode ; dzMoUE 3 ; v2.8.0 ×4 ; DzTracks 181 ; G1 ; littéral Fu ;
      confirmations hors couche inchangées) ;
  [K] textes : toute clé dzT de la famille est dans motion.json en FR ET EN, mêmes variables ;
  [R] le miroir du registre des nœuds (38 types) porte MotionCode.
Run (depuis backend/) : & $PY tests/test_studio_motion_code.py"""
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
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
BASE = "8fbde2ed"            # origin/main (t231-t237, t239-t241 installés), dzmotion en queue

print("[A] câblage dans le livré")
check("A1 nœud MotionCode : catégorie motion, titre dzT, entrées direction / script, sortie av",
      'MotionCode:{cat:"motion",title:dzT("studio.motion.code_titre"),desc:dzT("studio.motion.code_desc"),'
      'inPorts:[{id:"direction",type:"direction"},{id:"script",type:"text"}],outPorts:[{id:"out",type:"av"}],'
      'props:{script:"",durationS:8,fps:30,pageId:""}}' in BUNDLE)
check("A2 palette : rangé dans Animations après Direction motion",
      '{cat:"motion",types:["Animation","MotionDirection","MotionCode"]}' in BUNDLE)
check("A3 encart et inspecteur", 'n==="MotionCode"?dzMotionCodeEncart(o):n==="MotionDirection"?' in BUNDLE
      and 'e.type==="MotionCode"?r.jsx(DzMotionCode,{node:e,graph:g,set:o}):e.type==="MotionDirection"?' in BUNDLE)
check("A4 routes : écrire (POST), lire, rendre (POST)", 'fetch("/api/motion/code/ecrire",{method:"POST"' in BUNDLE
      and '"/api/motion/code/"+encodeURIComponent(pid)' in BUNDLE and 'fetch("/api/motion/code/rendre",{method:"POST"' in BUNDLE)

# ── [F] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
function objet(debut){const i=S.indexOf(debut);if(i<0)throw new Error("introuvable : "+debut);let k=i+debut.indexOf("{"),n=0,q=null;
 for(let j=k;j<S.length;j++){const c=S[j];if(q){if(c==="\\"){j++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")n++;else if(c==="}"){n--;if(!n)return S.slice(k,j+1)}}
 throw new Error("objet non fermé")}
let LANG="fr",H=[],hi=0,EFF=[],CALLS=[],SETS=[],ROUTES={};
const x={useState(init){const i=hi++;if(!(i in H))H[i]=typeof init==="function"?init():init;
  return [H[i],function(v){H[i]=typeof v==="function"?v(H[i]):v}]},useEffect(f){EFF.push(f)},useRef(){return{current:null}}};
const r={jsx(t,p){return{t,p:p||{}}},jsxs(t,p){return{t,p:p||{}}}};
const window={dzLang(){return LANG},addEventListener(){},removeEventListener(){},
 __dzDialogue:{confirmer:async function(){return true}}};
async function fetch(u,o){CALLS.push({u,o:o||null});const f=ROUTES[u.split("?")[0]]||ROUTES["*"];const v=f?f(u,o):{status:404,j:{detail:"x"}};
 return{ok:(v.status||200)<400,status:v.status||200,json:async function(){return v.j}}}
const dzT=function(k,v){return k+(v?JSON.stringify(v):"")},dzMq=function(k){return"MQ:"+k};
const STUB={x,r,window,fetch,dzT,dzMq,localStorage:{getItem(){return null},setItem(){}},
 ie:"ie",O:"O",le:"le",re:"re",Ze:"Ze",X:"X",DzColorPicker:"DzColorPicker",__dzGl(n){return"gl:"+n}};
const ENV=new Proxy(STUB,{has(t,k){return typeof k==="string"},get(t,k){if(k===Symbol.unscopables)return undefined;
 if(k in t)return t[k];if(k in globalThis)return globalThis[k];return function(){return null}}});
function arbre(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>arbre(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)arbre(n.p.children,f,acc);return acc}
function par(t,nom){return arbre(t,n=>n.p&&n.p["data-dz-motion"]===nom)[0]||null}
function champ(t,label){return arbre(t,n=>n.t==="O"&&n.p.label===label).map(n=>n.p.children)[0]||null}
function texte(n){if(n==null||n===false)return"";if(typeof n!=="object")return String(n);if(Array.isArray(n))return n.map(texte).join("");
 return texte(n.p&&n.p.children)}
async function vider(){for(let k=0;k<8;k++)await new Promise(s=>setTimeout(s,0))}
function poseur(nd){return function(k,v){nd.props=Object.assign({},nd.props,{[k]:v});SETS.push([k,v])}}
function rendre(C,nd,g){hi=0;return C({node:nd,graph:g,set:poseur(nd)})}
(async function(){try{
 const SRC="var Me="+objet("Me={Image:")+";"+tranche("function Wt(","function dzFinImg(")+";"
  +tranche("var dzMoUS=","function DzAnimation(")+tranche("function Mh(","const Zi=")
  +";return{Me,Wt,Mh,dzMotionCodePayload,dzMotionCodeBase,dzMotionCodeRendu,dzMotionCodeBilan,dzMotionCodeEncart,DzMotionCode,dzMoCache,dzMoCode}";
 const M=new Function("ENV","with(ENV){"+SRC+"}")(ENV);
 M.dzMoCache.lst=[{id:"style-charts",nature:"style",titre:{fr:"Graphiques",en:"Charts"}}];
 OUT.me=M.Me.MotionCode;
 // F2 : corps d'« Écrire la page »
 const g1={nodes:[{id:"t",type:"Text",props:{value:"Ligne 1\nLigne 2"}},
  {id:"d",type:"MotionDirection",props:{style:"style-charts",source:"skill-a-b",consigne:"EDIT",moteur:"ollama",modele:"llama3",effort:"auto"}},
  {id:"R",type:"Render",props:{format:"1:1"}},{id:"c",type:"MotionCode",props:{durationS:5,fps:99}}],
  edges:[{from:"t",fromPort:"out",to:"c",toPort:"script"},{from:"d",fromPort:"direction",to:"c",toPort:"direction"},{from:"c",fromPort:"out",to:"R",toPort:"in"}]};
 OUT.p1=M.dzMotionCodePayload(g1,g1.nodes[3]);
 const g2={nodes:[{id:"c",type:"MotionCode",props:{script:"Champ du nœud",fps:5}}],edges:[]};
 OUT.p2=M.dzMotionCodePayload(g2,g2.nodes[0]);
 // F3 : base de l'Animation
 const anim={id:"a",type:"Animation",props:{durationS:6,fps:24,elements:[{id:"el",type:"text",text:"T",keyframes:[],start:0,dur:1,hold:1}]}};
 OUT.b1=M.dzMotionCodeBase({id:"c",type:"MotionCode",props:{pageId:"mc-0123456789abcdef"}},anim,"16:9");
 OUT.b2=M.dzMotionCodeBase({id:"c",type:"MotionCode",props:{}},anim,"16:9");
 // F4 : compilation, Animation sur base motion code
 const g3={nodes:[{id:"c",type:"MotionCode",props:{pageId:"mc-0123456789abcdef"}},anim,{id:"R",type:"Render",props:{format:"16:9",name:"essai"}}],
  edges:[{from:"c",fromPort:"out",to:"a",toPort:"base"},{from:"a",fromPort:"out",to:"R",toPort:"in"}]};
 const k3=M.Mh(g3);OUT.c3={ok:k3.ok,summary:k3.summary,error:k3.error};
 ROUTES["/api/animate"]=function(u,o){return{status:200,j:{job_id:"J-anim"}}};
 ROUTES["/api/motion/code/rendre"]=function(u,o){return{status:200,j:{job_id:"J-code"}}};
 CALLS=[];OUT.c3run=k3.ok?await k3.run():null;OUT.c3call=CALLS.map(c=>({u:c.u,m:c.o&&c.o.method,b:c.o&&JSON.parse(c.o.body)}));
 const g4=JSON.parse(JSON.stringify(g3));g4.nodes[0].props={};
 const k4=M.Mh(g4);OUT.c4={ok:k4.ok,error:k4.error};
 // F5 : MotionCode → Rendu
 const g5={nodes:[{id:"c",type:"MotionCode",props:{pageId:"mc-fedcba9876543210",fps:25,durationS:3}},{id:"R",type:"Render",props:{format:"9:16",name:"Film"}}],
  edges:[{from:"c",fromPort:"out",to:"R",toPort:"in"}]};
 const k5=M.Mh(g5);OUT.c5={ok:k5.ok,summary:k5.summary};CALLS=[];OUT.c5run=k5.ok?await k5.run():null;
 OUT.c5call=CALLS.map(c=>({u:c.u,m:c.o&&c.o.method,b:c.o&&JSON.parse(c.o.body)}));
 const g6=JSON.parse(JSON.stringify(g5));g6.nodes[0].props={};OUT.c6=M.Mh(g6);
 ROUTES["/api/motion/code/rendre"]=function(){return{status:500,j:null}};
 const k7=M.Mh(g5);OUT.c7=k7.ok?await k7.run():null;
 // F6 : l'inspecteur
 const nd={id:"c",type:"MotionCode",props:{script:"",durationS:4,fps:24}};
 const gI={nodes:[{id:"d",type:"MotionDirection",props:{style:"style-charts",moteur:"ollama",modele:"llama3"}},nd,{id:"R",type:"Render",props:{format:"4:5"}}],
  edges:[{from:"d",fromPort:"direction",to:"c",toPort:"direction"}]};
 H=[];let t1=rendre(M.DzMotionCode,nd,gI);
 OUT.i1={direction:texte(par(t1,"code-direction")),script:!!par(t1,"code-script"),duree:!!champ(t1,'studio.motion.duree'),
  fps:!!champ(t1,'studio.motion.code_fps'),bouton:texte(par(t1,"code-ecrire")),page:texte(par(t1,"code-page")),
  bac:texte(par(t1,"code-bac")),html:!!par(t1,"code-html")};
 CALLS=[];await par(t1,"code-ecrire").p.onClick();OUT.i2={calls:CALLS.length,msg:H[0]&&H[0].msg,err:H[0]&&H[0].err};
 nd.props.script="Une ligne\nDeux lignes";
 const PAGE='<!doctype html><html><body><script>window.dzFrame=function(t){}</script></body></html>';
 ROUTES["/api/motion/code/ecrire"]=function(u,o){return{status:200,j:{page_id:"mc-aaaaaaaaaaaaaaaa",taille:2048,repli:false,moteur:"ollama",modele:"llama3",cout:{nature:"gratuit"}}}};
 ROUTES["/api/motion/code/mc-aaaaaaaaaaaaaaaa"]=function(){return{status:200,j:{page_id:"mc-aaaaaaaaaaaaaaaa",taille:2048,html:PAGE,refus:[]}}};
 H=[];t1=rendre(M.DzMotionCode,nd,gI);CALLS=[];await par(t1,"code-ecrire").p.onClick();
 OUT.i3={calls:CALLS.map(c=>({u:c.u,m:c.o&&c.o.method,b:c.o&&JSON.parse(c.o.body)})),pid:nd.props.pageId,msg:H[0]&&H[0].msg,err:!!(H[0]&&H[0].err)};
 t1=rendre(M.DzMotionCode,nd,gI);await vider();t1=rendre(M.DzMotionCode,nd,gI);
 const hz=par(t1,"code-html");
 OUT.i4={bouton:texte(par(t1,"code-ecrire")),page:texte(par(t1,"code-page")),lu:CALLS.some(c=>c.u==="/api/motion/code/mc-aaaaaaaaaaaaaaaa"),
  html:hz&&hz.t,lecture:hz&&hz.p.readOnly,valeur:hz&&hz.p.value,sect:arbre(t1,n=>n.t==="ie"&&n.p.label==="studio.motion.code_lecture").length};
 ROUTES["/api/motion/code/ecrire"]=function(){return{status:200,j:{page_id:"mc-bbbbbbbbbbbbbbbb",taille:512,repli:true,raison:"page_refusee",refus:["reseau"],refus_texte:"appel réseau",moteur:"ollama",cout:{nature:"gratuit"}}}};
 H=[];t1=rendre(M.DzMotionCode,nd,gI);await par(t1,"code-ecrire").p.onClick();OUT.i5=H[0]&&H[0].msg;
 ROUTES["/api/motion/code/ecrire"]=function(){return{status:200,j:{page_id:"mc-cccccccccccccccc",taille:100,repli:true,raison:"sans_moteur",cout:{nature:"gratuit"}}}};
 H=[];t1=rendre(M.DzMotionCode,nd,gI);await par(t1,"code-ecrire").p.onClick();OUT.i6=H[0]&&H[0].msg;
 ROUTES["/api/motion/code/ecrire"]=function(){return{status:402,j:{detail:{message:"Plafond du mois atteint"}}}};
 H=[];t1=rendre(M.DzMotionCode,nd,gI);await par(t1,"code-ecrire").p.onClick();OUT.i7={msg:H[0]&&H[0].msg,err:!!(H[0]&&H[0].err)};
 // script relié, direction absente
 const gJ={nodes:[{id:"t",type:"Text",props:{value:"x"}},{id:"c2",type:"MotionCode",props:{}}],edges:[{from:"t",fromPort:"out",to:"c2",toPort:"script"}]};
 H=[];const t2=rendre(M.DzMotionCode,gJ.nodes[1],gJ);
 OUT.i8={direction:texte(par(t2,"code-direction")),relie:texte(par(t2,"code-script-relie")),champ:!!par(t2,"code-script")};
 // F8 : encart
 OUT.e1=texte(M.dzMotionCodeEncart({pageId:"mc-aaaaaaaaaaaaaaaa"}));OUT.e2=texte(M.dzMotionCodeEncart({}));
 LANG="en";OUT.en=M.dzMotionCodeBilan({repli:false,moteur:"ollama",taille:1536,cout:{nature:"gratuit"}});
 console.log(JSON.stringify(OUT));
}catch(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))}})();
"""
F = None
with tempfile.TemporaryDirectory() as d:
    h = pathlib.Path(d) / "h.js"
    h.write_text(HARNAIS, encoding="utf-8")
    p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        F = json.loads((p.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        F = {"erreur": (p.stdout or "")[-500:] + (p.stderr or "")[-500:]}
print("[F] sous node (vraies fonctions du livré)")
check("F0 le harnais tourne", "erreur" not in F, F.get("erreur"))
F = F if "erreur" not in F else {}
me = F.get("me") or {}
check("F1 catalogue : MotionCode (motion), entrées direction / script, sortie av, défauts 8 s / 30 i/s",
      me.get("cat") == "motion" and [p_["id"] for p_ in me.get("inPorts", [])] == ["direction", "script"]
      and me.get("outPorts") == [{"id": "out", "type": "av"}] and me.get("props", {}).get("fps") == 30
      and me.get("props", {}).get("durationS") == 8, me)
p1 = F.get("p1") or {}
check("F2 corps d'« Écrire la page » : script relié, direction (style, skill, consigne éditée), moteur, format du Rendu, "
      "durée du nœud, cadence bornée à 60, sans images",
      p1.get("script") == "Ligne 1\nLigne 2" and p1.get("direction", {}).get("style") == "style-charts"
      and p1.get("direction", {}).get("consigne") == "EDIT" and p1.get("moteur") == "ollama" and p1.get("modele") == "llama3"
      and p1.get("aspect") == "1:1" and p1.get("duree_s") == 5 and p1.get("fps") == 60 and "images" not in p1, p1)
p2 = F.get("p2") or {}
check("F2b sans liens : le champ du nœud, 9:16, 8 s, cadence plancher 12", p2.get("script") == "Champ du nœud"
      and p2.get("aspect") == "9:16" and p2.get("duree_s") == 8 and p2.get("fps") == 12 and p2.get("moteur") == "", p2)
check("F3 base de l'Animation : {source_kind:motion_code, page_id, aspect, fps et durée de l'Animation} ; sans page → null",
      F.get("b1") == {"source_kind": "motion_code", "page_id": "mc-0123456789abcdef", "aspect": "16:9", "fps": 24,
                      "duree_s": 6} and F.get("b2") is None, (F.get("b1"), F.get("b2")))
c3, cc = F.get("c3") or {}, F.get("c3call") or []
check("F4 compilation : Animation sur base motion code → POST /api/animate avec la base motion code",
      c3.get("ok") is True and len(cc) == 1 and cc[0]["u"] == "/api/animate" and cc[0]["m"] == "POST"
      and cc[0]["b"].get("base") == F.get("b1") and F.get("c3run") == {"job_id": "J-anim"}, (c3, cc))
check("F4b sans page écrite : la compilation refuse avec le message traduit (pas un fond uni muet)",
      (F.get("c4") or {}).get("ok") is False and (F.get("c4") or {}).get("error") == "studio.motion.code_sans_page", F.get("c4"))
c5, cc5 = F.get("c5") or {}, F.get("c5call") or []
check("F5 MotionCode → Rendu : POST /api/motion/code/rendre (format du Rendu, cadence, durée, titre, graphe)",
      c5.get("ok") is True and c5.get("summary") == 'studio.motion.code_resume{"id":"mc-fedcba9876543210"}' and len(cc5) == 1
      and cc5[0]["u"] == "/api/motion/code/rendre" and cc5[0]["m"] == "POST"
      and {k: cc5[0]["b"].get(k) for k in ("page_id", "aspect", "fps", "duree_s", "title")}
      == {"page_id": "mc-fedcba9876543210", "aspect": "9:16", "fps": 25, "duree_s": 3, "title": "Film"}
      and (cc5[0]["b"].get("source_graph") or {}).get("nodes") and F.get("c5run") == {"job_id": "J-code"}, (c5, cc5))
check("F5b sans page : refus traduit ; échec du serveur : message traduit",
      (F.get("c6") or {}).get("ok") is False and (F.get("c6") or {}).get("error") == "studio.motion.code_sans_page"
      and F.get("c7") == {"ok": False, "error": "studio.motion.code_rendre_echec"}, (F.get("c6"), F.get("c7")))
i1 = F.get("i1") or {}
check("F6 inspecteur : direction reliée (résumé), champ Script, Durée, Images par seconde, « Écrire la page », "
      "aucune page, ligne du bac à sable, pas de code",
      i1.get("direction", "").startswith("studio.motion.direction_reliee") and "Graphiques" in i1.get("direction", "")
      and i1.get("script") and i1.get("duree") and i1.get("fps") and i1.get("bouton") == "studio.motion.code_ecrire"
      and i1.get("page") == "studio.motion.code_sans_page" and i1.get("bac") == "studio.motion.code_bac"
      and i1.get("html") is False, i1)
check("F7 script vide → message, AUCUN appel", (F.get("i2") or {}).get("calls") == 0
      and (F.get("i2") or {}).get("msg") == "studio.motion.script_vide" and (F.get("i2") or {}).get("err") is True, F.get("i2"))
i3 = F.get("i3") or {}
ec = [c for c in i3.get("calls", []) if c["u"] == "/api/motion/code/ecrire"]
check("F8 « Écrire la page » : POST du corps compilé (format 4:5 du Rendu, 4 s, 24 i/s), pageId posé, bilan",
      len(ec) == 1 and ec[0]["m"] == "POST" and ec[0]["b"].get("script") == "Une ligne\nDeux lignes"
      and ec[0]["b"].get("aspect") == "4:5" and ec[0]["b"].get("duree_s") == 4 and ec[0]["b"].get("fps") == 24
      and ec[0]["b"].get("direction", {}).get("style") == "style-charts" and i3.get("pid") == "mc-aaaaaaaaaaaaaaaa"
      and i3.get("err") is False and i3.get("msg", "").startswith("studio.motion.code_bilan{")
      and '"moteur":"ollama · llama3"' in i3.get("msg", "") and "studio.motion.code_ko" in i3.get("msg", "")
      and "2.0" in i3.get("msg", "")
      and "studio.motion.cout_bilan_gratuit" in i3.get("msg", ""), i3)
i4 = F.get("i4") or {}
check("F9 après écriture : « Réécrire », page et taille, code relu par GET et montré en LECTURE SEULE (zone de saisie)",
      i4.get("bouton") == "studio.motion.code_reecrire" and i4.get("page", "").startswith("studio.motion.code_page")
      and "mc-aaaaaaaaaaaaaaaa" in i4.get("page", "") and "2.0" in i4.get("page", "") and i4.get("lu")
      and i4.get("html") == "textarea" and i4.get("lecture") is True and "window.dzFrame" in (i4.get("valeur") or "")
      and i4.get("sect") == 1, i4)
check("F10 repli après refus : la raison et les motifs du bac à sable sont dits", "studio.motion.code_bilan_repli" in
      (F.get("i5") or "") and "studio.motion.code_raison_refusee" in (F.get("i5") or "") and "appel réseau" in (F.get("i5") or ""),
      F.get("i5"))
check("F11 repli sans moteur : la raison de t234", "studio.motion.raison_sans_moteur" in (F.get("i6") or ""), F.get("i6"))
check("F12 plafond (402) : le message du serveur, en erreur", (F.get("i7") or {}).get("msg") == "Plafond du mois atteint"
      and (F.get("i7") or {}).get("err") is True, F.get("i7"))
i8 = F.get("i8") or {}
check("F13 direction absente dite ; script relié : pas de champ Script", i8.get("direction") == "studio.motion.direction_absente"
      and i8.get("relie", "").startswith("studio.motion.script_relie") and i8.get("champ") is False, i8)
check("F14 encart : page écrite / aucune page", F.get("e1") == 'studio.motion.code_encart{"id":"mc-aaaaaaaaaaaaaaaa"}'
      and F.get("e2") == "studio.motion.code_encart_vide", (F.get("e1"), F.get("e2")))

# ── [D] chaîne, [S] sûreté, [K] textes ────────────────────────────────────────────────────────────────────────────
print("[D] chaîne dzmotion")
import patch_bundle_dzmotion as M                                    # noqa: E402
import _i18n_l1_aide as AIDE                                         # noqa: E402


CODE = getattr(M, "CODE", "")                                       # la famille C (absente sur la base)


def git_bundle(rev):
    r_ = subprocess.run(["git", "show", f"{rev}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
    return r_.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n") if r_.returncode == 0 else None


def maillon_de(rev):
    """Le maillon dzmotion tel qu'il était à `rev` (pour défaire la base avec SON maillon)."""
    import importlib.util
    r_ = subprocess.run(["git", "show", f"{rev}:scripts/patch_bundle_dzmotion.py"], capture_output=True, cwd=str(RACINE))
    f_ = pathlib.Path(tempfile.mkdtemp()) / "maillon_base.py"
    f_.write_bytes(r_.stdout)
    spec = importlib.util.spec_from_file_location("maillon_base", f_)
    m_ = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m_)
    return m_


base = git_bundle(BASE)
avant = M.defaire(BUNDLE)
base_s = base.decode("utf-8") if base else ""
MB_ = maillon_de(BASE)
avant_base = MB_.defaire(base_s) if base else None
check("D1 marqueur ×1 ; sans le maillon = la base sans SON maillon, octet pour octet (le reste du bundle est intouché)",
      BUNDLE.count(M.MARKER) == 1 and base is not None and avant == avant_base, "base introuvable" if base is None else "")
check("D2 aller-retour exact, avant_dzmotion = défaire", M.appliquer(avant) == BUNDLE and AIDE.avant_dzmotion(BUNDLE) == avant)
check("D3 la famille C garde les ancres M0-M7 de la base et ajoute trois paires (M8 base, M9 sans page, M10 Rendu)",
      base is not None and [a_ for a_, _r in M.PAIRES[:len(MB_.PAIRES)]] == [a_ for a_, _r in MB_.PAIRES]
      and len(MB_.PAIRES) == 8 and len(M.PAIRES) == 11)
check("D4 x.useState( 731 ; dzMoUS 2 → 3 = HOOKS (un état neuf : DzMotionCode) ; dzMoUE 3 inchangé",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("dzMoUS(") == 3 == M.HOOKS and base_s.count("dzMoUS(") == 2
      and BUNDLE.count("dzMoUE(") == 3 == base_s.count("dzMoUE(")
      and len(re.findall(r"dzMoUS\(", CODE)) == 1)
check("D5 v2.8.0 ×4, DzTracks 181", BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
try:
    _g1 = [p_["remplace"] for p_ in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("D6 aucun remplacement G1 ne bouge ; littéral Fu intouché", bool(_g1) and all(BUNDLE.count(x_) == base_s.count(x_) for x_ in _g1)
      and BUNDLE.count("Fu") == base_s.count("Fu") and "Fu" not in CODE)
check("D7 confirmations hors couche inchangées (aucune neuve)", BUNDLE.count("__dzDialogue.confirmer") == base_s.count("__dzDialogue.confirmer"))
check("D8 octets : CRLF préservés, aucun LF nu ; aucun .bak_dzmotion", RAW.count(b"\r\n") > 15000
      and RAW.count(b"\n") == RAW.count(b"\r\n") and not (BUN_P.parent / (BUN_P.name + ".bak_dzmotion")).exists())
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzmotion.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D9 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)
r_ = subprocess.run(["node", "--check", str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
check("D10 node --check du livré", r_.returncode == 0, (r_.stderr or "")[-300:])

print("[S] sûreté de l'écran")
FAM = CODE + "".join(r_ for a_, r_ in M.PAIRES if "MotionCode" in r_)
check("S1 la page n'entre jamais dans le DOM comme document : ni dangerouslySetInnerHTML, innerHTML, iframe, srcdoc, "
      "eval, Function, Blob, createObjectURL, document.write",
      not any(t in FAM for t in ("dangerouslySetInnerHTML", "innerHTML", "iframe", "srcdoc", "eval(", "Function(", "Blob",
                                 "createObjectURL", "document.write")))
check("S2 la page n'est montrée que dans une zone de saisie en lecture seule", 'readOnly:!0,"data-dz-motion":"code-html"' in CODE)

print("[K] textes")
dico = {}
for f_ in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    dico.update(json.loads(f_.read_bytes().decode("utf-8")))
cles = sorted(set(re.findall(r'dzT\("([a-z0-9_.]+)"', FAM)))
manq = [k for k in cles if not (dico.get(k, {}).get("fr", "").strip() and dico.get(k, {}).get("en", "").strip())]
check("K1 chaque clé dzT de la famille C a son FR ET son EN", bool(cles) and not manq, manq)
MO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "motion.json").read_bytes().decode("utf-8"))
neuves = sorted(k for k in MO if k.startswith("studio.motion.code_"))
check("K2 les clés studio.motion.code_* de motion.json = celles employées (aucune orpheline)",
      neuves == sorted(k for k in cles if k.startswith("studio.motion.code_")) and len(neuves) == 18, neuves)
check("K3 mêmes {variables} en FR et en EN", all(sorted(re.findall(r"\{(\w+)\}", MO[k]["fr"]))
                                                == sorted(re.findall(r"\{(\w+)\}", MO[k]["en"])) for k in neuves))
check("K4 bilan en anglais : passe par dzT (langue de l'écran)", (F.get("en") or "").startswith("studio.motion.code_bilan"))
lits = [s_ for s_ in re.findall(r'children:"([^"]*)"', CODE) if s_.strip()]
check("K5 aucun texte visible en dur dans la famille C", not lits, lits)

print("[R] miroir du registre")
MIR = json.loads((RACINE / "backend" / "app" / "assets" / "studio_nodes.json").read_bytes().decode("utf-8"))
T = MIR.get("types", {})
mc = T.get("MotionCode") or {}
check("R1 38 types ; MotionCode (motion, entrées direction / script, sortie av)", MIR.get("count") == 38 == len(T)
      and mc.get("cat") == "motion" and mc.get("in") == ["direction", "script"]
      and mc.get("in_types") == {"direction": "direction", "script": "text"}, mc)
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "qa" / "dump_studio_registry.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
check("R2 le miroir suit le livré (dump --check)", rc.returncode == 0, rc.stdout + rc.stderr)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
