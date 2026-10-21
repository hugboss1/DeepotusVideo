# -*- coding: utf-8 -*-
"""Son & VFX › Musique › Atelier sonore (t271, 21/10/2026) — le canevas `DzSvAtelier` posé par le maillon de queue
`dzsonvfx` depuis sa source frontend/patches/sonvfx-atelier.js, au-dessus du moteur /api/audio/graph (t270).
Sections :
  [S] source et livré : source aplatie à l'octet, règles d'écriture, routes du moteur, libellés des effets lus dans le
      rack (SVX_FX_DEFS), aucun texte en dur, aucun arrondi ;
  [F] opérations PURES du graphe sous node (vraies fonctions du livré, VRAI catalogue du serveur) : ajouter, relier
      (remplacement, boucle refusée), délier, supprimer, régler (bornes, entiers, entrées du mix), insérer une plage,
      remonter à la source, graphe envoyé au serveur ;
  [X] croisé client → serveur : les quatre préréglages produits par le canevas sont VALIDÉS puis RENDUS par le moteur ;
  [P] le composant sous node (mini-moteur de hooks, faux serveur) : chargement, palette, inspecteur, annuler /
      rétablir, Suppr, lien tiré d'une sortie vers une entrée, validation, aperçu et A/B, rendu, Montage, préréglage,
      frise (région → nœud Plage), « Ouvrir dans l'Atelier », graphe gardé dans le navigateur.
Run (depuis backend/) : & $PY tests/test_sonvfx_atelier.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzatelier_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir()
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
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
        print(f"  FAIL  {label} {str(detail)[:600]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
SRC = (RACINE / "frontend" / "patches" / "sonvfx-atelier.js").read_bytes().decode("utf-8")
_i, _j = BUNDLE.find("/*__dzsvpistes*/"), BUNDLE.find("/*__dzsvatelier*/")
PAGE = BUNDLE[_i + len("/*__dzsvpistes*/"):_j] if 0 <= _i < _j else ""

from app.services import audio_graph as AG  # noqa: E402
from app.services import sfx_service as SX  # noqa: E402
import patch_bundle_dzsonvfx as PS  # noqa: E402

CAT = AG.catalogue()
AUDIO = SX._audio_dir()
for nom, f in (("musique_a.mp3", 220), ("voix_b.mp3", 660)):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={f}:duration=2", "-ac", "2",
                    "-c:a", "libmp3lame", str(AUDIO / nom)], check=True)

# ── [S] ───────────────────────────────────────────────────────────────────────────────────────────────────────────
print("[S] source et livré")
check("S1 le livré porte la source aplatie, à l'octet, après la page Pistes et avant `const Te=`",
      PAGE and PAGE == PS.aplatir(SRC) and BUNDLE.count("function DzSvAtelier(") == 1
      and _j < BUNDLE.find('const Te="/api";'))
_dans, _lignes = False, []
for _l in (l.strip() for l in SRC.splitlines()):
    if _dans or _l.startswith("/*"):
        _dans = not _l.endswith("*/")
        continue
    _lignes.append(_l)
check("S2 règles d'écriture : ni « // », ni ligne qui commence par ( ou [",
      not any(l.startswith(("//", "(", "[")) for l in _lignes))
check("S3 aucun texte en dur : libellés par dzT ou le rack, aucun aria-label/placeholder/title littéral",
      not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', PAGE) and not re.search(r'"aria-label":"|placeholder:"|title:"', PAGE))
check("S4 routes du moteur : catalogue, valider, aperçu, rendre (et les pistes, le sidecar)",
      all(u in PAGE for u in ('"/api/audio/graph/noeuds"', '"/api/audio/graph/valider"', '"/api/audio/graph/apercu"',
                              '"/api/audio/graph/rendre"', '"/api/audio")', '"/api/audio/meta"')))
check("S5 les effets prennent libellés, pas et unités du rack SFX (SVX_FX_DEFS), avec garde si la couche manque",
      'typeof SVX_FX_DEFS!=="undefined"?SVX_FX_DEFS:[]' in PAGE)
check("S6 hooks par alias dans la fonction (x.useState( absent)", "var US=x.useState,UE=x.useEffect,UR=x.useRef;" in PAGE
      and "x.useState(" not in PAGE)
check("S7 la palette couvre tous les types du serveur et tout le vocabulaire FX",
      set(re.findall(r'\{t:"(\w+)"\}', PAGE)) | {"effet"} >= {t["type"] for t in CAT["noeuds"]}
      and set(re.search(r'items:\[("filter"[^\]]*)\]\.map', PAGE).group(1).replace('"', "").split(",")) == set(CAT["effets"]))

# ── harnais node commun ───────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const CAT=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const i=S.indexOf("/*__dzsvpistes*/"),j=S.indexOf("/*__dzsvatelier*/");const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[],MINUT=[];
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p[q]))EFF.push({k,f});if(d)H[k]=d;else H[k]=null},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const NETT={};
const r={jsx:(t,p)=>({t,p}),jsxs:(t,p)=>({t,p}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
var SVX_FX_DEFS=[{type:"reverb",label:"LBL-reverb",params:[{k:"mix",label:"Mix",unit:"%",step:1},{k:"decay_s",label:"LBL-decay",unit:"s",step:0.1}]},
 {type:"filter",label:"LBL-filter",params:[{k:"mode",kind:"seg",opts:[["low","bas"],["high","haut"]],d:"low"},{k:"freq",label:"LBL-freq",unit:"Hz",step:1},{k:"q",label:"Q",step:0.1}]}];
function dzSvpJson(res){return res.json().then(d=>{if(!res.ok)throw new Error(d.detail||"err");return d})}
function dzSvpDuree(s){s=Math.round(Number(s)||0);return Math.floor(s/60)+":"+String(s%60).padStart(2,"0")}
let APPELS=[],REP={},STOCK={},EV={};
const window={addEventListener:(n,f)=>{(EV[n]=EV[n]||[]).push(f)},removeEventListener:(n,f)=>{EV[n]=(EV[n]||[]).filter(g=>g!==f)},
 AudioContext:function(){this.decodeAudioData=()=>Promise.resolve({duration:10,getChannelData:()=>new Float32Array(3000).fill(0.5)});this.close=()=>{}}};
const localStorage={getItem:k=>k in STOCK?STOCK[k]:null,setItem:(k,v)=>{STOCK[k]=String(v)}};
let PORT=null;const document={elementFromPoint:()=>PORT?{closest:()=>PORT}:null};
const URL={createObjectURL:()=>"blob:apercu",revokeObjectURL:()=>{}};
function setTimeout(f){MINUT.push(f);return MINUT.length}function clearTimeout(){}
function rep(d,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(d),blob:()=>Promise.resolve({taille:1}),arrayBuffer:()=>Promise.resolve(new ArrayBuffer(8))})}
function fetch(u,o){o=o||{};APPELS.push([u,o.method||"GET",o.body?JSON.parse(o.body):null]);
 if(u==="/api/audio/graph/noeuds")return rep(CAT);
 if(u==="/api/audio")return rep({audio:[{name:"musique_a.mp3",url:"/api/audio/musique_a.mp3"},{name:"voix_b.mp3",url:"/api/audio/voix_b.mp3"}]});
 if(u==="/api/audio/meta")return rep({meta:{"musique_a.mp3":{kind:"musique"}}});
 if(u==="/api/audio/graph/valider")return REP.valider||rep({ok:true,ignores:[],sources:["musique_a.mp3"]});
 if(u==="/api/audio/graph/apercu")return rep({});
 if(u==="/api/audio/graph/devis")return REP.devis||rep({ok:true,usd:0.0442,deja:[],a_generer:[{id:"ia_regenerer1",op:"regenerer",modele:"sa3-regenerer",label:"Stable Audio 3 Medium",usd:0.0442}]});
 if(u==="/api/audio/graph/rendre")return rep({ok:true,filename:"atelier_essai.mp3",dur:2,parent:"musique_a.mp3",relation:"atelier",usd:0});
 if(u.startsWith("/api/audio/"))return rep({});
 return rep({},404)}
eval(CODE);
module.exports={x,r,H,dzT,setRep:(k,v)=>{REP[k]=v}};
const TOILE={clientWidth:800,clientHeight:400,getBoundingClientRect:()=>({left:0,top:0})};
const LECT={src:"",currentTime:0,joue:0,play(){this.joue++;return Promise.resolve()},pause(){}};
let A=null,ALLER=[];
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null||n===false)return "";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join("");if(n.t==="glyph")return "";return n.p?texte(n.p.children):""}
function rendre(){HI=0;EFF=[];A=DzSvAtelier({go:v=>ALLER.push(v)});
 tout(A,n=>n.p&&n.p.ref,[]).forEach(n=>{if(n.p.className==="dzsva-toile")n.p.ref.current=TOILE;else if(n.t==="audio")n.p.ref.current=LECT});
 const e=EFF;EFF=[];e.forEach(o=>{const c=o.f();if(typeof c==="function")NETT[o.k]=c});return A}
async function calme(){for(let k=0;k<10;k++){await new Promise(r0=>setImmediate(r0));rendre()}}
async function minuteries(){const m=MINUT;MINUT=[];m.forEach(f=>f());await calme()}
function un(f){return tout(A,f,[])[0]}
function sva(a){return un(n=>n.p&&n.p["data-sva"]===a)}
function G(){return H[2]}
function etat(){return {g:G()&&{noeuds:G().noeuds.map(n=>[n.id,n.type,n.params]),liens:G().liens.map(l=>[l.de,l.vers,l.entree])},
 attente:texte(un(n=>n.p&&n.p.className==="dzsva-attente")),sel:H[3],note:texte(un(n=>n.p&&n.p.className==="dzsva-note")),etat:texte(un(n=>n.p&&n.p.className==="dzsva-etat")),
 palette:tout(A,n=>n.p&&n.p["data-sva-ajout"],[]).map(n=>n.p["data-sva-ajout"]),
 params:tout(A,n=>n.p&&n.p.className==="dzsva-param",[]).map(n=>texte(n.p.children[0])),
 noeuds:tout(A,n=>n.p&&n.p.className==="dzsva-noeud",[]).map(n=>[n.p["data-sva-id"],texte(n.p.children[0])]),
 annuler:sva("annuler")&&sva("annuler").p.disabled,retablir:sva("retablir")&&sva("retablir").p.disabled,
 ecouter:sva("ecouter")&&sva("ecouter").p.disabled,ab:sva("ab")&&texte(sva("ab").p.children),
 montage:!!sva("montage"),stock:STOCK.dz_sva_graphe?JSON.parse(STOCK.dz_sva_graphe).noeuds.length:null,appels:APPELS.slice()}}
function pointeur(cx,cy){return {button:0,clientX:cx,clientY:cy,stopPropagation(){},preventDefault(){}}}
function relacher(cx,cy){(EV.pointerup||[]).slice().forEach(f=>f(pointeur(cx,cy)))}
function bouger(cx,cy){(EV.pointermove||[]).slice().forEach(f=>f(pointeur(cx,cy)))}
module.exports.lancer=async function(){
 const R={};
 if(process.argv[4]==="pur"){
  const g0=dzSvaVide();
  const a=dzSvaAjouter(g0,CAT,"source",0,0,{params:{fichier:"musique_a.mp3"}});
  const b=dzSvaAjouter(a.g,CAT,"effet",200,0,{fx:"reverb"});
  const c=dzSvaAjouter(b.g,CAT,"sortie",400,0);
  let g=dzSvaRelier(c.g,a.id,b.id,0).g;g=dzSvaRelier(g,b.id,c.id,0).g;
  R.ajout={ids:[a.id,b.id,c.id],reverb:b.g.noeuds[1].params,src:a.g.noeuds[0].params,mix:dzSvaAjouter(g0,CAT,"mix",0,0).g.noeuds[0].params};
  R.boucle=dzSvaRelier(g,c.id,a.id,0).refus||null;R.soi=dzSvaRelier(g,b.id,b.id,0).refus||null;
  const s2=dzSvaAjouter(g,CAT,"source",0,100,{params:{fichier:"voix_b.mp3"}});
  R.remplace=dzSvaRelier(s2.g,s2.id,b.id,0).g.liens;
  R.delier=dzSvaDelier(g,c.id,0).liens;R.supprime=dzSvaSupprimer(g,b.id);
  R.borne=dzSvaRegler(g,CAT,b.id,"mix",999).noeuds[1].params.mix;R.illisible=dzSvaRegler(g,CAT,b.id,"mix","abc").noeuds[1].params.mix;
  const m=dzSvaAjouter(g,CAT,"mix",300,200);let gm=dzSvaRelier(m.g,a.id,m.id,0).g;gm=dzSvaRegler(gm,CAT,m.id,"entrees",4.6);
  gm=dzSvaRelier(gm,s2.id||a.id,m.id,3).g;R.mix4=gm.noeuds.find(n=>n.id===m.id).params.entrees;
  R.mix2=dzSvaRegler(gm,CAT,m.id,"entrees",2).liens.filter(l=>l.vers===m.id).map(l=>l.entree);
  const ins=dzSvaInserer(g,CAT,a.id,"plage",{debut:1,fin:3});R.inserer={id:ins.id,liens:ins.g.liens,params:ins.g.noeuds.find(n=>n.id===ins.id).params};
  R.sourceDe=dzSvaSourceDe(ins.g,c.id).id;R.serveur=dzSvaServeur(g);
  R.pre={};["radio","lofi","hall","voix"].forEach(k=>{R.pre[k]=dzSvaServeur(dzSvaPrereglage(CAT,k,"musique_a.mp3","voix_b.mp3"))});
  return R}
 rendre();R.chargement=etat();await calme();R.charge=etat();
 await minuteries();R.valide=etat();
 un(n=>n.p&&n.p["data-sva-ajout"]==="reverb").p.onClick();rendre();R.ajout=etat();
 sva("annuler").p.onClick();rendre();R.annule=etat();
 sva("retablir").p.onClick();rendre();R.retabli=etat();
 const rev=G().noeuds.find(n=>n.params.fx==="reverb");
 un(n=>n.p&&n.p["data-sva-out"]===G().noeuds[0].id).p.onPointerDown(pointeur(10,10));
 PORT={getAttribute:k=>k==="data-sva-noeud"?rev.id:"0"};relacher(10,10);PORT=null;rendre();R.lien=etat();
 const out=G().noeuds.find(n=>n.type==="sortie");
 un(n=>n.p&&n.p["data-sva-out"]===rev.id).p.onPointerDown(pointeur(10,10));
 PORT={getAttribute:k=>k==="data-sva-noeud"?out.id:"0"};relacher(10,10);PORT=null;rendre();R.lien2=etat();
 un(n=>n.p&&n.p["data-sva-out"]===out.id);
 un(n=>n.p&&n.p["data-sva-out"]===rev.id).p.onPointerDown(pointeur(10,10));
 PORT={getAttribute:k=>k==="data-sva-noeud"?G().noeuds[0].id:"0"};relacher(10,10);PORT=null;rendre();R.boucle=etat();
 un(n=>n.p&&n.p["data-sva-id"]===rev.id).p.onPointerDown(pointeur(100,100));bouger(150,130);relacher(150,130);rendre();R.deplace=etat();
 R.pos=G().noeuds.find(n=>n.id===rev.id);
 await minuteries();
 APPELS=[];sva("ecouter").p.onClick();await calme();R.ecoute=etat();R.lect={src:LECT.src,joue:LECT.joue};
 sva("ab").p.onClick();rendre();R.ab=etat();R.lectA={src:LECT.src};
 un(n=>n.p&&n.p.className==="dzsva-nom").p.onChange({target:{value:"essai"}});rendre();
 APPELS=[];sva("rendre").p.onClick();await calme();R.rendu=etat();
 sva("montage").p.onClick();R.aller=ALLER.slice();
 un(n=>n.p&&n.p.className==="dzsva-toile").p.onKeyDown({key:"Delete",target:{tagName:"DIV"},preventDefault(){}});rendre();R.suppr=etat();
 un(n=>n.p&&n.p["data-sva-pre"]==="voix").p.onClick();rendre();R.pre=etat();R.vue=Object.assign({},H[5]);
 sva("annuler").p.onClick();rendre();R.pre_annule=etat();
 H[3]=G().noeuds[0].id;rendre();await calme();
 const onde=un(n=>n.p&&n.p["data-sva"]==="frise");
 onde.p.onPointerDown({button:0,clientX:30,currentTarget:{getBoundingClientRect:()=>({left:0,width:300})}});bouger(90,0);relacher(90,0);rendre();R.frise=etat();
 onde.p.onPointerDown({button:0,clientX:150,currentTarget:{getBoundingClientRect:()=>({left:0,width:300})}});relacher(151,0);rendre();R.curseur=H[13];
 REP.valider=rep({detail:"graphe : une sortie et une seule"},400);G().noeuds.length;
 sva("supprimer")&&0;
 const sortie=G().noeuds.find(n=>n.type==="sortie");H[3]=sortie.id;rendre();sva("supprimer").p.onClick();rendre();await minuteries();R.invalide=etat();
 global.__ajout=true;
 return R};
module.exports.lancerIa=async function(){
 const R={};
 rendre();await calme();await minuteries();R.base=etat();
 un(n=>n.p&&n.p["data-sva-ajout"]==="ia_regenerer").p.onClick();rendre();R.ajout=etat();
 R.noeud=G().noeuds.find(n=>n.type==="ia_regenerer");
 R.options=tout(A,n=>n.t==="option"&&n.p.value&&String(n.p.value).indexOf("-regenerer")>0,[]).map(n=>[n.p.value,texte(n.p.children)]);
 const ta=un(n=>n.t==="textarea");R.placeholder=ta&&ta.p.placeholder;ta.p.onFocus();ta.p.onChange({target:{value:"warm piano"}});rendre();
 R.prompt=G().noeuds.find(n=>n.type==="ia_regenerer").params.prompt;
 APPELS=[];await minuteries();R.devis=etat();R.prix=texte(sva("ia-prix"));R.prixNoeud=texte(un(n=>n.p&&n.p["data-sva"]==="ia-noeud"));
 APPELS=[];sva("rendre").p.onClick();rendre();R.arme=etat();R.armeLbl=texte(sva("rendre").p.children);R.armeAttr=sva("rendre").p["data-arme"];R.armeEtat=H[18];
 sva("rendre").p.onClick();await calme();R.envoi=etat();R.apres=H[18];
 sva("ecouter").p.onClick();rendre();R.armeE={arme:H[18],lbl:texte(sva("ecouter").p.children),appels:APPELS.filter(a=>a[0]==="/api/audio/graph/apercu").length};
 sva("desarmer").p.onClick();rendre();R.desarme={arme:H[18],bouton:!!sva("desarmer")};
 sva("ecouter").p.onClick();rendre();
 const id=G().noeuds.find(n=>n.type==="ia_regenerer").id;
 H[2]=dzSvaRelier(G(),"source1",id,0).g;rendre();await calme();R.armeApresChangement=H[18];
 H[3]=id;rendre();await calme();
 const onde=un(n=>n.p&&n.p["data-sva"]==="frise");
 onde.p.onPointerDown({button:0,clientX:60,currentTarget:{getBoundingClientRect:()=>({left:0,width:300})}});bouger(150,0);relacher(150,0);rendre();
 R.frise=G().noeuds.find(n=>n.id===id).params;R.regionIa=tout(A,n=>n.p&&n.p.className==="dzsva-region"&&n.p["data-ia"]==="",[]).length;
 REP.devis=rep({ok:true,usd:0,deja:[id],a_generer:[]});APPELS=[];await minuteries();
 R.deja=texte(sva("ia-prix"));sva("ecouter").p.onClick();await calme();
 R.ecouteDeja=APPELS.filter(a=>a[0]==="/api/audio/graph/apercu").map(a=>a[2].generer);
 return R};
"""

LANCEUR = r"""
const M=require(process.argv[5]);
(process.argv[4]==="ia"?M.lancerIa():M.lancer()).then(R=>process.stdout.write(JSON.stringify(R))).catch(e=>process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)})));
"""

AJOUT = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const CAT=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const i=S.indexOf("/*__dzsvpistes*/"),j=S.indexOf("/*__dzsvatelier*/");
let H=[],HI=0,EFF=[];
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p[q]))EFF.push(f);H[k]=d||null},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const r={jsx:(t,p)=>({t,p}),jsxs:(t,p)=>({t,p}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
function dzSvpJson(res){return res.json()}function dzSvpDuree(){return "0:02"}
const STOCK={dz_sva_graphe:JSON.stringify({noeuds:[{id:"source1",type:"source",params:{fichier:"musique_a.mp3"},x:0,y:0},{id:"sortie1",type:"sortie",params:{},x:300,y:0}],liens:[]})};
const localStorage={getItem:k=>STOCK[k]||null,setItem:(k,v)=>{STOCK[k]=v}};
const window={__dzSvAtelierAjout:{fichier:"voix_b.mp3"},addEventListener(){},removeEventListener(){}};
function setTimeout(){return 0}function clearTimeout(){}
function fetch(u){const d=u==="/api/audio/graph/noeuds"?CAT:u==="/api/audio"?{audio:[{name:"musique_a.mp3"},{name:"voix_b.mp3"}]}:{meta:{}};
 return Promise.resolve({ok:true,json:()=>Promise.resolve(d),arrayBuffer:()=>Promise.resolve(new ArrayBuffer(0))})}
eval(S.slice(i,j));
function rendre(){HI=0;EFF=[];const A=DzSvAtelier({});const e=EFF;EFF=[];e.forEach(f=>f());return A}
(async()=>{rendre();for(let k=0;k<6;k++){await new Promise(r0=>setImmediate(r0));rendre()}
 process.stdout.write(JSON.stringify({noeuds:H[2].noeuds.map(n=>[n.id,n.type,n.params.fichier||""]),liens:H[2].liens,sel:H[3],
  note:H[8],consomme:window.__dzSvAtelierAjout===null}))})().catch(e=>process.stdout.write(JSON.stringify({erreur:String(e.stack||e)})));
"""


def _node(code, *extra):
    with tempfile.TemporaryDirectory() as dd:
        h = pathlib.Path(dd) / "h.js"
        h.write_text(code, encoding="utf-8")
        c = pathlib.Path(dd) / "cat.json"
        c.write_text(json.dumps(CAT), encoding="utf-8")
        args = ["node", str(h), str(BUN_P), str(c), *extra]
        if extra and extra[0] == "composant":
            l = pathlib.Path(dd) / "l.js"
            l.write_text(LANCEUR, encoding="utf-8")
            args = ["node", str(l), str(BUN_P), str(c), "composant", str(h)]
        elif extra and extra[0] in ("pur", "ia"):
            l = pathlib.Path(dd) / "l.js"
            l.write_text(LANCEUR, encoding="utf-8")
            args = ["node", str(l), str(BUN_P), str(c), extra[0], str(h)]
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"erreur": (p.stdout + p.stderr)[:900]}


# ── [F] opérations pures ──────────────────────────────────────────────────────────────────────────────────────────
print("[F] opérations pures du graphe (vraies fonctions, vrai catalogue)")
F = _node(HARNAIS, "pur")
check("F0 harnais exécuté", "ajout" in F, F)
a = F.get("ajout", {})
check("F1 ajouter : ids par type, défauts du catalogue (effet = fx + bornes du vocabulaire, mix = 2 entrées)",
      a.get("ids") == ["source1", "effet1", "sortie1"]
      and a.get("reverb") == {"fx": "reverb", **{k: v[2] for k, v in CAT["effets"]["reverb"].items()}}
      and a.get("src") == {"fichier": "musique_a.mp3"} and a.get("mix") == {"entrees": 2}, a)
check("F2 relier : une boucle et un lien vers soi sont refusés", F.get("boucle") == "boucle" and F.get("soi") == "boucle", F)
check("F3 relier sur une entrée déjà prise : le lien précédent est remplacé",
      F.get("remplace") == [{"de": "effet1", "vers": "sortie1", "entree": 0}, {"de": "source2", "vers": "effet1", "entree": 0}],
      F.get("remplace"))
check("F4 délier / supprimer (un nœud emporte ses liens)",
      F.get("delier") == [{"de": "source1", "vers": "effet1", "entree": 0}]
      and [n["id"] for n in F.get("supprime", {}).get("noeuds", [])] == ["source1", "sortie1"]
      and F.get("supprime", {}).get("liens") == [], [F.get("delier"), F.get("supprime")])
check("F5 régler : borné au catalogue, illisible = défaut", F.get("borne") == 100 and F.get("illisible") == CAT["effets"]["reverb"]["mix"][2],
      (F.get("borne"), F.get("illisible")))
check("F6 mix : entrées arrondies ; en perdre retire les liens des entrées disparues",
      F.get("mix4") == 5 and F.get("mix2") == [0], (F.get("mix4"), F.get("mix2")))
ins = F.get("inserer", {})
check("F7 insérer une plage après la source : elle prend la place du lien sortant",
      ins.get("id") == "plage1" and ins.get("params", {}).get("debut") == 1 and ins.get("params", {}).get("fin") == 3
      and {"de": "source1", "vers": "plage1", "entree": 0} in ins.get("liens", [])
      and {"de": "plage1", "vers": "effet1", "entree": 0} in ins.get("liens", [])
      and {"de": "source1", "vers": "effet1", "entree": 0} not in ins.get("liens", []), ins)
check("F8 remonter à la source depuis la sortie", F.get("sourceDe") == "source1", F.get("sourceDe"))
check("F9 graphe envoyé au serveur : positions retirées", F.get("serveur", {}).get("noeuds", [{}])[0] == {
    "id": "source1", "type": "source", "params": {"fichier": "musique_a.mp3"}}, F.get("serveur"))

# ── [X] croisé client → serveur ───────────────────────────────────────────────────────────────────────────────────
print("[X] préréglages du canevas validés et rendus par le moteur")
for nom, g in (F.get("pre") or {}).items():
    try:
        v = AG.valider(g)
        r = AG.rendre(g, nom=f"pre {nom}")
        check(f"X {nom} : valide (rien d'ignoré) et rendu réel", v["ignores"] == [] and (AUDIO / r["filename"]).is_file(),
              (v["ignores"], r))
    except Exception as e:  # noqa: BLE001
        check(f"X {nom} : valide et rendu réel", False, e)
check("X0 quatre préréglages", sorted(F.get("pre") or {}) == ["hall", "lofi", "radio", "voix"], F.get("pre"))

# ── [P] composant ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[P] le composant sous node")
P = _node(HARNAIS, "composant")
check("P0 harnais exécuté", "charge" in P, P)
c = P.get("charge", {})
check("P1 chargement : attente, puis source (la musique) → sortie relié, graphe gardé dans le navigateur",
      P.get("chargement", {}).get("attente") == "⟦sonvfx.atelier.chargement⟧"
      and c.get("g", {}).get("noeuds") == [["source1", "source", {"fichier": "musique_a.mp3"}], ["sortie1", "sortie", {}]]
      and c.get("g", {}).get("liens") == [["source1", "sortie1", 0]], c)
check("P2 palette : les 29 entrées (types + vocabulaire FX + 4 nœuds IA, t272)", len(c.get("palette", [])) == 29,
      c.get("palette"))
v = P.get("valide", {})
check("P3 validation par le serveur après le délai : « Graphe valide », écoute permise",
      v.get("etat") == "⟦sonvfx.atelier.valide⟧" and v.get("ecouter") is False
      and any(a[0] == "/api/audio/graph/valider" for a in v.get("appels", [])), v)
a = P.get("ajout", {})
check("P4 palette → nœud ajouté et choisi ; l'inspecteur prend les libellés du rack",
      a.get("sel") == "effet1" and ["effet1", "LBL-reverb"] in a.get("noeuds", [])
      and a.get("params") == ["⟦sonvfx.atelier.effet⟧", "Mix", "LBL-decay"] and a.get("annuler") is False
      and a.get("stock") == 3, a)
check("P5 annuler / rétablir", len(P.get("annule", {}).get("g", {}).get("noeuds", [])) == 2
      and len(P.get("retabli", {}).get("g", {}).get("noeuds", [])) == 3 and P.get("annule", {}).get("retablir") is False,
      [P.get("annule"), P.get("retabli")])
check("P6 lien tiré d'une sortie vers une entrée (remplace le lien de cette entrée)",
      ["source1", "effet1", 0] in P.get("lien", {}).get("g", {}).get("liens", [])
      and P.get("lien2", {}).get("g", {}).get("liens") == [["source1", "effet1", 0], ["effet1", "sortie1", 0]],
      [P.get("lien"), P.get("lien2")])
check("P7 lien qui ferait une boucle : refusé, message", P.get("boucle", {}).get("g", {}).get("liens") ==
      [["source1", "effet1", 0], ["effet1", "sortie1", 0]] and P.get("boucle", {}).get("note") == "⟦sonvfx.atelier.boucle_refusee⟧",
      P.get("boucle"))
pos = P.get("pos", {})
check("P8 glisser un nœud le déplace (de l'écart du pointeur)", pos.get("x") - 0 >= 40 and pos.get("y") >= 20, pos)
e = P.get("ecoute", {})
ap = [x for x in e.get("appels", []) if x[0] == "/api/audio/graph/apercu"]
check("P9 Écouter : l'aperçu du graphe, depuis le curseur, joué (B)",
      len(ap) == 1 and ap[0][2]["depuis"] == 0 and ap[0][2]["graphe"]["liens"] == [
          {"de": "source1", "vers": "effet1", "entree": 0}, {"de": "effet1", "vers": "sortie1", "entree": 0}]
      and "x" not in ap[0][2]["graphe"]["noeuds"][0] and P.get("lect", {}).get("src") == "blob:apercu"
      and e.get("ab") == "⟦sonvfx.atelier.ab_traite⟧", (ap, P.get("lect"), e.get("ab")))
check("P10 A/B : la source brute de la référence", P.get("ab", {}).get("ab") == "⟦sonvfx.atelier.ab_source⟧"
      and P.get("lectA", {}).get("src") == "/api/audio/musique_a.mp3", (P.get("ab"), P.get("lectA")))
rd = P.get("rendu", {})
rr = [x for x in rd.get("appels", []) if x[0] == "/api/audio/graph/rendre"]
check("P11 Rendre : le graphe et le nom, note, bouton Montage", len(rr) == 1 and rr[0][2]["nom"] == "essai"
      and rd.get("note", "").startswith("⟦sonvfx.atelier.rendu_fait⟧") and rd.get("montage") and P.get("aller") == ["montage"],
      (rr, rd.get("note"), P.get("aller")))
s = P.get("suppr", {})
check("P12 Suppr retire le nœud choisi et ses liens", ["effet1", "LBL-reverb"] not in s.get("noeuds", [])
      and all("effet1" not in l for l in s.get("g", {}).get("liens", [])), s)
pr = P.get("pre", {})
check("P13 préréglage « Voix sur musique » : 7 nœuds, deux sources, ducking ; annulable",
      [n[1] for n in pr.get("g", {}).get("noeuds", [])] == ["source", "source", "gain", "duck", "mix", "limiteur", "sortie"]
      and pr.get("note") == "⟦sonvfx.atelier.prereglage_pose⟧"
      and len(P.get("pre_annule", {}).get("g", {}).get("noeuds", [])) == 2, (pr, P.get("pre_annule")))
_vu = P.get("vue", {})
_xs = [n[2] for n in []]
check("P13b le préréglage est cadré : vue dézoomée, tous les nœuds (x 40 → 1316) tiennent dans le canevas (800 px)",
      0.3 <= _vu.get("z", 9) < 1 and _vu.get("x", -1) + 40 * _vu.get("z", 0) >= 0
      and _vu.get("x", 0) + (1140 + 176) * _vu.get("z", 9) <= 800, _vu)
fr = P.get("frise", {})
pl = [n for n in fr.get("g", {}).get("noeuds", []) if n[1] == "plage"]
check("P14 frise : glisser de 1 s à 3 s pose une Plage après la source (10 s décodées), choisie et reliée",
      len(pl) == 1 and pl[0][2]["debut"] == 1 and pl[0][2]["fin"] == 3 and fr.get("sel") == pl[0][0]
      and ["source1", pl[0][0], 0] in fr.get("g", {}).get("liens", []), fr)
check("P15 frise : un clic place la position de l'aperçu", P.get("curseur") == 5, P.get("curseur"))
iv = P.get("invalide", {})
check("P16 graphe refusé par le serveur : son message, écoute interdite",
      iv.get("etat") == "graphe : une sortie et une seule" and iv.get("ecouter") is True, iv)
A = _node(AJOUT)
check("P17 « Ouvrir dans l'Atelier » : la piste envoyée devient une source du graphe gardé, consommée une fois, choisie",
      ["source2", "source", "voix_b.mp3"] in A.get("noeuds", []) and A.get("consomme") is True and A.get("sel") == "source2"
      and A.get("note") == '⟦sonvfx.atelier.source_ajoutee⟧{"nom":"voix_b.mp3"}', A)

# ── [Q] t272 : nœuds IA ───────────────────────────────────────────────────────────────────────────────────────────
print("[Q] t272 : nœuds IA (palette, inspecteur, devis avant, armer puis envoyer)")
Q = _node(HARNAIS, "ia")
check("Q0 harnais exécuté", "ajout" in Q, Q)
check("Q1 sans nœud IA : aucun devis demandé",
      not any(a[0] == "/api/audio/graph/devis" for a in Q.get("base", {}).get("appels", [])), Q.get("base", {}).get("appels"))
check("Q2 palette « IA » : prolonger, régénérer, variation, SFX",
      all(t in Q.get("base", {}).get("palette", []) for t in ("ia_prolonger", "ia_regenerer", "ia_variation", "ia_sfx")))
nq = Q.get("noeud") or {}
check("Q3 nœud IA ajouté : défauts du catalogue, modèle par défaut de l'opération, description vide",
      nq.get("params") == {"debut": 0, "fin": 5, "prise": 1, "modele": CAT["ia"]["regenerer"]["defaut"], "prompt": ""}, nq)
check("Q4 inspecteur : modèles de l'opération avec leur prix ; sans clé, dit « clé à ajouter » mais choisissable",
      [o[0] for o in Q.get("options", [])] == [m["id"] for m in CAT["ia"]["regenerer"]["modeles"]]
      and all("~$" in o[1] and "⟦sonvfx.atelier.sans_cle⟧" in o[1] for o in Q.get("options", []))
      and Q.get("placeholder") == "⟦sonvfx.atelier.ia_prompt_aide⟧" and Q.get("prompt") == "warm piano", Q.get("options"))
dvq = [a for a in Q.get("devis", {}).get("appels", []) if a[0] == "/api/audio/graph/devis"]
check("Q5 devis demandé après la validation ; prix affiché AVANT (barre et inspecteur)",
      dvq and dvq[-1][2]["graphe"]["noeuds"][-1]["params"]["prompt"] == "warm piano"
      and Q.get("prix") == '⟦sonvfx.atelier.ia_payant⟧{"n":1,"prix":"~$0.0442"}'
      and Q.get("prixNoeud") == '⟦sonvfx.atelier.ia_prix⟧{"prix":"~$0.0442"}', (dvq, Q.get("prix"), Q.get("prixNoeud")))
check("Q6 premier clic sur Rendre : armé (prix dit), RIEN d'envoyé",
      Q.get("armeEtat") == "rendre" and Q.get("armeAttr") == ""
      and Q.get("armeLbl") == '⟦sonvfx.atelier.confirmer_ia⟧{"prix":"~$0.0442"}'
      and not any(a[0] == "/api/audio/graph/rendre" for a in Q.get("arme", {}).get("appels", []))
      and Q.get("arme", {}).get("note") == '⟦sonvfx.atelier.ia_confirmer_aide⟧{"prix":"~$0.0442"}', Q.get("arme"))
rq = [a for a in Q.get("envoi", {}).get("appels", []) if a[0] == "/api/audio/graph/rendre"]
check("Q7 second clic : le rendu part avec generer:true, l'armement retombe",
      len(rq) == 1 and rq[0][2].get("generer") is True and Q.get("apres") == "", (rq, Q.get("apres")))
check("Q8 Écouter s'arme aussi (aucun aperçu au premier clic) ; « Annuler » désarme",
      Q.get("armeE", {}).get("arme") == "ecouter" and Q.get("armeE", {}).get("appels") == 0
      and Q.get("desarme") == {"arme": "", "bouton": False}, (Q.get("armeE"), Q.get("desarme")))
check("Q9 un changement du graphe désarme", Q.get("armeApresChangement") == "", Q.get("armeApresChangement"))
check("Q10 frise : avec un nœud IA choisi, glisser règle SA plage (2 s → 5 s) ; région IA dessinée",
      Q.get("frise", {}).get("debut") == 2 and Q.get("frise", {}).get("fin") == 5 and Q.get("regionIa") == 1, Q.get("frise"))
check("Q11 segment déjà généré : « gratuit », Écouter part au premier clic, generer:false",
      Q.get("deja") == "⟦sonvfx.atelier.ia_deja⟧" and Q.get("ecouteDeja") == [False], (Q.get("deja"), Q.get("ecouteDeja")))


def _defauts_acceptes(t):
    prm = {k: v[2] for k, v in next(x for x in CAT["noeuds"] if x["type"] == t)["params"].items()}
    prm.update(modele=CAT["ia"][t[3:]]["defaut"], prompt="warm piano")
    gg = {"noeuds": [{"id": "s", "type": "source", "params": {"fichier": "musique_a.mp3"}}, {"id": "i", "type": t, "params": prm},
                     {"id": "o", "type": "sortie", "params": {}}],
          "liens": [{"de": "s", "vers": "i", "entree": 0}, {"de": "i", "vers": "o", "entree": 0}]}
    return AG.valider(gg)["ok"]


for _t in ("ia_prolonger", "ia_regenerer", "ia_variation", "ia_sfx"):
    check(f"QX {_t} : les défauts du canevas (+ une description) sont acceptés par le serveur", lambda: _defauts_acceptes(_t))

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_atelier():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
