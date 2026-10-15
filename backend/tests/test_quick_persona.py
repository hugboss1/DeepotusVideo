# -*- coding: utf-8 -*-
"""t214 (Menus : Quick, 15/10/2026) — Quick montait une ligne FIGÉE « persona Deepotus prophet ».

Elle devient un MENU DÉROULANT des espaces/personas (`DzQuickPersona`) : `GET /api/espaces` (non archivés), chaque
entrée avec l'avatar, le nom du persona et son mode de voix (AUCUN badge si le persona n'a pas de voiceMode explicite :
le squelette `rs()` du shell en pose « prophet » par défaut, on ne le montre pas). Choisir une entrée appelle
`dzEspActiver(id)` ; l'espace actif reste GLOBAL (décision du lot Espaces), une note le dit sous le menu. L'entrée
« + Nouveau persona… » ouvre Réglages › Espaces.

Ce que ce banc garde :
  [A] le composant, extrait du bundle avec les aides des espaces (dzEspCharger, dzEspActiver, dzCtCharger…) et rendu
      sous node avec des hooks SIMULÉS à état (useReducer, useEffect, useRef) et un faux serveur à DEUX espaces
      (Deepotus actif, Rippled) : déclencheur = persona actif + badge « prophet », menu = 2 entrées + « Nouveau
      persona… », Rippled sans badge, note de l'espace global ;
  [B] un choix déclenche `POST /api/espaces/rippled/activate`, PUIS la relecture de la liste et des contenus
      (`deepotus:espace-refresh` → dzCtCharger) ; le déclencheur montre Rippled sans « prophet » ; « Nouveau persona… »
      navigue vers Réglages › Espaces ; un refus s'affiche en alerte ;
  [C] au changement d'espace : le prompt par défaut n'est remplacé que s'il n'a pas été édité (`dzPromptAuto`), la voix
      suit `dzVoixSuit` ; la galerie (`nm`) et les vibes lisent les contenus de l'espace (dzCtUse) ; une vibe choisie
      absente du nouvel espace retombe sur sa première vibe (P2 : le sélecteur affichait « — ») ;
  [D] câblage : la ligne figée a disparu de Quick, `DzQuickPersona` y est rendu ×1 ; aucune paire t214 ne porte
      « aria-label » (le banc des onglets repère ses paires ainsi) ;
  [E] clés FR/EN `quick.persona.*` dans menus.json (jamais quick.json, générateur L2), catalogue assemblé à jour ;
  [F] maillon de queue `dzquick` : paires t214 ×1, inverse exact, `avant_dzquick` rend la ligne figée d'avant,
      comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181), aucun .bak.
Run (depuis backend/) : & $PY tests/test_quick_persona.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
BASE = "6113d2f7"
LIGNE_FIGEE = 'r.jsx("span",{className:"mono",style:{fontSize:10,color:"var(--ink-muted)"},children:t.voiceMode})'

# ── harnais node : hooks simulés À ÉTAT, faux serveur, fenêtre à événements ─────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
function extraire(debut){const a=S.indexOf(debut);if(a<0)return null;let i=S.indexOf("{",a),d=0,q=null;
 for(;i<S.length;i++){const c=S[i];if(q){if(c==="\\"){i++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")d++;else if(c==="}"){d--;if(!d)break}}
 return S.slice(a,i+1)}
// la fenêtre : de vrais écouteurs (espace-refresh, navigate)
const ECOUTE={},EVTS=[];
const window={addEventListener(n,f){(ECOUTE[n]=ECOUTE[n]||[]).push(f)},removeEventListener(n,f){ECOUTE[n]=(ECOUTE[n]||[]).filter(g=>g!==f)},
 dispatchEvent(e){EVTS.push({type:e.type,detail:e.detail});(ECOUTE[e.type]||[]).slice().forEach(f=>f(e));return true},
 location:{href:"http://l/?view=quick"},history:{replaceState(a,b,u){window.location.href=String(u)}}};
const document={addEventListener(n,f){(ECOUTE["doc:"+n]=ECOUTE["doc:"+n]||[]).push(f)},removeEventListener(n,f){ECOUTE["doc:"+n]=(ECOUTE["doc:"+n]||[]).filter(g=>g!==f)}};
class Event{constructor(t){this.type=t}}class CustomEvent extends Event{constructor(t,o){super(t);this.detail=o&&o.detail}}
// le faux serveur : deux espaces
const SRV={actif:"deepotus",refus:false,espaces:{deepotus:{nom:"Deepotus",couleur:"#ef4444"},rippled:{nom:"Rippled",couleur:"#3b82f6"}},
 persona:{deepotus:{display_name:"Deepotus",ecran:{id:"deepotus",name:"Deepotus",avatar:"dz-marque-poulpe",voiceMode:"prophet"}},
          rippled:{display_name:"Rippled"}},
 contenus:{deepotus:{prompt_templates:[]},rippled:{prompt_templates:[{id:"r1",body:"Rippled ripples across a calm lake."}]}}};
const LOG=[];
function vue(id){const e=SRV.espaces[id];return{id,nom:e.nom,couleur:e.couleur,archive:false,actif:id===SRV.actif}}
function rep(o,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(o)})}
function fetch(u,o){const m=(o&&o.method)||"GET";LOG.push(m+" "+u);let k;
 if(u==="/api/espaces")return rep({espaces:["deepotus","rippled"].map(vue).sort((a,b)=>b.actif-a.actif),actif:SRV.actif});
 if(u==="/api/espaces/actif")return rep(vue(SRV.actif));
 if((k=u.match(/^\/api\/espaces\/([a-z]+)\/activate$/))&&m==="POST"){if(SRV.refus)return rep({detail:"refus du serveur"},400);
  SRV.actif=k[1];return rep({actif:k[1],espace:vue(k[1])})}
 if(k=u.match(/^\/api\/espaces\/([a-z]+)\/persona$/))return SRV.lent?new Promise(()=>{}):rep(SRV.persona[k[1]]);
 if(k=u.match(/^\/api\/espaces\/([a-z]+)\/contenus$/))return rep(SRV.contenus[k[1]]);
 return rep({},404)}
// React simulé : un seul composant monté, hooks par position, rendu relancé quand un état change
const H={slots:[],i:0,sale:false,effets:[]};
const x={useReducer(f,init){const i=H.i++;if(!(i in H.slots))H.slots[i]=init;
  return[H.slots[i],a=>{const n=f(H.slots[i],a);if(n!==H.slots[i]){H.slots[i]=n;H.sale=true}}]},
 useRef(v){const i=H.i++;if(!(i in H.slots))H.slots[i]={current:v===undefined?null:v};return H.slots[i]},
 useEffect(f,deps){const i=H.i++;const av=H.slots[i];const change=!av||!deps||deps.length!==av.deps.length||deps.some((d,j)=>d!==av.deps[j]);
  if(change)H.effets.push(()=>{if(av&&av.nett)av.nett();H.slots[i]={deps:deps||[],nett:f()}});else H.slots[i]=av},
 useState(){throw new Error("useState interdit (compte figé)")},useMemo:f=>f(),useCallback:f=>f};
const el=(t,p,k)=>({t:typeof t==="string"?t:(t&&t.name)||"?",p:p||{},k});const r={jsx:el,jsxs:el,Fragment:"Fragment"};
function X(){}const dzT=(k,v)=>"⟦"+k+(v?":"+JSON.stringify(v):"")+"⟧";
const ENVB={x,r,X,dzT,window,document,fetch,Event,CustomEvent,URL,console:{error(){},warn(){},log(){}},
 localStorage:{getItem:()=>null,setItem(){},removeItem(){}}};
const SRC=[tranche("var dzEspCache=null","function dzEspPersona("),tranche("var dzEspCt=null","function DzContenusBtn("),
 tranche("var dzQpPers=","class DzQuickGarde ")].join(";\n");
const M=new Function("ENV","with(ENV){"+SRC+";return{DzQuickPersona,etat:function(){return{cache:dzEspCache,ct:dzEspCt}}}}")(ENVB);
let PROPS={p:{id:"deepotus",name:"Deepotus",avatar:"dz-marque-poulpe",voiceMode:"prophet"}},VUE=null;
function rendre(){for(let n=0;n<20;n++){H.i=0;H.sale=false;VUE=M.DzQuickPersona(PROPS);const ef=H.effets;H.effets=[];ef.forEach(f=>f());if(!H.sale&&!ef.length)return}}
async function stable(){for(let n=0;n<12;n++){rendre();await new Promise(z=>setTimeout(z,0))}rendre()}
function texte(n){if(n==null||n===false||n===true||typeof n==="function")return"";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join(" ");if(n.p)return" "+texte(n.p.children);return""}
function tous(n,pred,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tous(c,pred,acc));return acc}
 if(pred(n))acc.push(n);tous(n.p&&n.p.children,pred,acc);return acc}
const attr=a=>n=>n.p&&n.p[a]!=null;
(async function(){try{
 await stable();
 const dec=tous(VUE,attr("data-dz-qp-ouvrir"))[0];
 OUT.ferme={texte:texte(dec),aria:dec&&dec.p["aria-expanded"],menu:tous(VUE,n=>n.p&&n.p.role==="listbox").length,
  note:texte(tous(VUE,attr("data-dz-qp-note"))[0])};
 dec.p.onClick();await stable();
 const opts=tous(VUE,n=>n.p&&n.p.role==="option");
 OUT.ouvert={n:opts.length,ids:opts.map(o=>o.p["data-dz-qp-id"]),sel:opts.map(o=>o.p["aria-selected"]),txt:opts.map(texte),
  nouveau:texte(tous(VUE,attr("data-dz-qp-nouveau"))[0]),aria:tous(VUE,attr("data-dz-qp-ouvrir"))[0].p["aria-expanded"],
  persFetch:LOG.filter(l=>/\/persona$/.test(l)).length};
 const avant=LOG.length;
 opts.find(o=>o.p["data-dz-qp-id"]==="rippled").p.onClick();
 PROPS={p:{id:"rippled",name:"Rippled",avatar:"",voiceMode:"prophet"}};                  // le shell : squelette rs()
 await stable();
 OUT.choix={log:LOG.slice(avant),actif:M.etat().cache&&M.etat().cache.actif,ct:M.etat().ct&&M.etat().ct.id,
  refresh:EVTS.filter(e=>e.type==="deepotus:espace-refresh").length,ferme:tous(VUE,n=>n.p&&n.p.role==="listbox").length,
  dec:texte(tous(VUE,attr("data-dz-qp-ouvrir"))[0])};
 // Nouveau persona…
 tous(VUE,attr("data-dz-qp-ouvrir"))[0].p.onClick();await stable();
 tous(VUE,attr("data-dz-qp-nouveau"))[0].p.onClick();await stable();
 const nav=EVTS.filter(e=>e.type==="deepotus:navigate");
 OUT.nouveau={nav:nav.length&&nav[nav.length-1].detail,url:window.location.href,ferme:tous(VUE,n=>n.p&&n.p.role==="listbox").length};
 // un refus du serveur
 SRV.refus=true;tous(VUE,attr("data-dz-qp-ouvrir"))[0].p.onClick();await stable();
 tous(VUE,n=>n.p&&n.p.role==="option"&&n.p["data-dz-qp-id"]==="deepotus")[0].p.onClick();await stable();
 OUT.refus={alerte:texte(tous(VUE,n=>n.p&&n.p.role==="alert")[0]),actif:M.etat().cache.actif};
 // persona de l'espace actif encore en lecture : le déclencheur suit le shell, sans le « prophet » du squelette
 SRV.lent=true;window.dispatchEvent(new Event("deepotus:espace-refresh"));await stable();
 OUT.lent={dec:texte(tous(VUE,attr("data-dz-qp-ouvrir"))[0])};
}catch(e){OUT.err=String(e&&e.stack||e)}
// [C] prompt par défaut et voix
try{
 const DFT="A deep-sea throne lit by bioluminescent currents, slow cinematic push-in, indigo and cyan, particles drifting.";
 const cb=tranche('function(){if(!dzEspCt)return;var dft="A deep-sea throne','},[dzCvQ])')+"}";
 const VOIX=extraire("function dzVoixSuit(");
 const ENVC={x:{useEffect:f=>f()},dzEspCt:null,dzPromptAuto:null,dzVoixAuto:null,I:[],A:"cinematic",V:function(){},
  dzCt:(k,d)=>{const v=ENVC.dzEspCt&&ENVC.dzEspCt.data[k];return v&&v.length?v:d}};
 const effet=new Function("ENV","s","a","with(ENV){("+cb+")()}");
 const cbv=tranche('function(){if(I.length&&!I.some(','},[dzCvQ])')+"}";
 const vibe=new Function("ENV","with(ENV){("+cbv+")()}");
 const voix=new Function("ENV","v","set","with(ENV){"+VOIX+";dzVoixSuit(v,set,1)}");
 const P={};let got;
 ENVC.dzEspCt={id:"rippled",nom:"Rippled",data:{prompt_templates:[{body:"Rippled ripples across a calm lake."}]}};
 got=null;effet(ENVC,DFT,v=>{got=v});P.defautVersRippled=got;
 got=null;effet(ENVC,"mon prompt à moi",v=>{got=v});P.editeGarde=got;
 ENVC.dzEspCt={id:"deepotus",nom:"Deepotus",data:{prompt_templates:[]}};
 got=null;effet(ENVC,"Rippled ripples across a calm lake.",v=>{got=v});P.autoVersDeepotus=got;
 ENVC.dzEspCt={id:"rippled",nom:"Rippled",data:{}};ENVC.dzVoixAuto=null;
 got=null;voix(ENVC,"From the deep, the prophet speaks. The shoal awakens.",v=>{got=v});P.voixDefaut=got;
 got=null;voix(ENVC,"Ma voix off.",v=>{got=v});P.voixEditee=got;
 // vibes : la vibe choisie absente de l'espace retombe sur la première ; présente, elle est gardée
 ENVC.dzEspCt={id:"rippled",nom:"Rippled",data:{prompt_templates:[]}};ENVC.I=[{id:"calme"},{id:"brume"}];
 got=null;ENVC.A="cinematic";ENVC.V=v=>{got=v};vibe(ENVC);P.vibeAbsente=got;
 got=null;ENVC.A="brume";vibe(ENVC);P.vibePresente=got;
 OUT.prompt=P}catch(e){OUT.prompt={err:String(e&&e.message||e)}}
process.stdout.write(JSON.stringify(OUT));
})();
"""


def node(bundle_texte):
    with tempfile.TemporaryDirectory() as td:
        b = pathlib.Path(td) / "b.js"; b.write_text(bundle_texte, encoding="utf-8")
        h = pathlib.Path(td) / "h.js"; h.write_text(HARNAIS, encoding="utf-8")
        rn = subprocess.run(["node", str(h), str(b)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(rn.stdout)
    except ValueError:
        return {"err": (rn.stdout + rn.stderr)[-600:]}


OUT = node(BUNDLE)
print("[A] le menu, rendu depuis un faux /api/espaces à deux espaces")
check("A0 le composant se rend sans erreur", "err" not in OUT, str(OUT.get("err"))[:500])
F = OUT.get("ferme") or {}
check("A1 fermé : le déclencheur montre le persona actif et son mode de voix",
      "Deepotus" in F.get("texte", "") and "prophet" in F.get("texte", "") and "⟦quick.persona.libelle⟧" in F.get("texte", ""),
      repr(F.get("texte")))
check("A2 fermé : aucun menu, aria-expanded faux", F.get("menu") == 0 and F.get("aria") is False)
check("A3 la note « espace actif global » est sous le menu", F.get("note", "").strip() == "⟦quick.persona.note⟧")
O = OUT.get("ouvert") or {}
check("A4 ouvert : deux entrées, Deepotus puis Rippled, Deepotus sélectionné",
      O.get("n") == 2 and O.get("ids") == ["deepotus", "rippled"] and O.get("sel") == [True, False], repr(O)[:300])
txt = O.get("txt") or ["", ""]
check("A5 Deepotus garde son badge « prophet »", "Deepotus" in txt[0] and "prophet" in txt[0])
check("A6 Rippled (persona sans voiceMode) : aucun badge, pas de « prophet »", "Rippled" in txt[1] and "prophet" not in txt[1],
      repr(txt[1:]))
check("A7 l'entrée « + Nouveau persona… » est là, aria-expanded vrai",
      O.get("nouveau", "").strip() == "⟦quick.persona.nouveau⟧" and O.get("aria") is True)
check("A8 un persona lu par espace, une seule fois", O.get("persFetch") == 2, repr(O.get("persFetch")))

print("[B] un choix active l'espace, puis tout se relit")
C = OUT.get("choix") or {}
lg = C.get("log") or []
ip = lg.index("POST /api/espaces/rippled/activate") if "POST /api/espaces/rippled/activate" in lg else -1
check("B1 POST /api/espaces/rippled/activate", ip >= 0, repr(lg))
check("B2 puis relecture de la liste (GET /api/espaces)", ip >= 0 and "GET /api/espaces" in lg[ip + 1:])
check("B3 puis relecture des contenus de Rippled (deepotus:espace-refresh → dzCtCharger)",
      ip >= 0 and "GET /api/espaces/rippled/contenus" in lg[ip + 1:] and C.get("refresh", 0) >= 1 and C.get("ct") == "rippled")
check("B4 l'espace actif (global) est Rippled, le menu se referme", C.get("actif") == "rippled" and C.get("ferme") == 0)
check("B5 le déclencheur montre Rippled sans « prophet » (squelette du shell ignoré)",
      "Rippled" in C.get("dec", "") and "prophet" not in C.get("dec", ""), repr(C.get("dec")))
N = OUT.get("nouveau") or {}
check("B6 « Nouveau persona… » ouvre Réglages › Espaces", isinstance(N.get("nav"), dict) and N["nav"].get("view") == "settings"
      and "section=espaces" in N.get("url", "") and N.get("ferme") == 0, repr(N))
R = OUT.get("refus") or {}
check("B7 un refus du serveur s'affiche en alerte, l'espace ne change pas",
      "refus du serveur" in R.get("alerte", "") and R.get("actif") == "rippled", repr(R))

L = OUT.get("lent") or {}
check("B8 persona encore en lecture : le déclencheur montre Rippled (shell) sans « prophet » du squelette",
      "Rippled" in L.get("dec", "") and "prophet" not in L.get("dec", ""), repr(L))

print("[C] prompt et voix au changement d'espace")
P = OUT.get("prompt") or {}
check("C1 prompt par défaut remplacé par le modèle de Rippled", P.get("defautVersRippled") == "Rippled ripples across a calm lake.",
      repr(P))
check("C2 prompt ÉDITÉ jamais écrasé", "editeGarde" in P and P.get("editeGarde") is None)
check("C3 prompt posé automatiquement : revient au défaut de Deepotus",
      (P.get("autoVersDeepotus") or "").startswith("A deep-sea throne"))
check("C4 voix par défaut : « Meet Rippled. » ; voix éditée gardée",
      P.get("voixDefaut") == "Meet Rippled." and "voixEditee" in P and P.get("voixEditee") is None)
check("C6 vibe absente de l'espace → la première ; vibe présente gardée",
      P.get("vibeAbsente") == "calme" and "vibePresente" in P and P.get("vibePresente") is None, repr(P))
check("C5 la galerie nm et les vibes lisent les contenus de l'espace",
      'function nm({onPick:e}){var dzCv=dzCtUse(),dzFd=dzCt("prompt_templates",fd);' in BUNDLE
      and 'dzCvQ=dzCtUse(),I=dzCt("vibes",' in BUNDLE)

print("[D] câblage dans Quick")
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
B0 = r0.stdout.decode("utf-8") if r0.returncode == 0 else ""
check("D0 témoin : la base 6113d2f7 a la ligne figée", B0.count(LIGNE_FIGEE) == 1)
check("D1 la ligne figée a disparu", LIGNE_FIGEE not in BUNDLE and 'children:"persona"}),r.jsx("span",{style:{fontSize:11.5' not in BUNDLE)
check("D2 DzQuickPersona rendu ×1 dans Quick", BUNDLE.count('r.jsx(DzQuickPersona,{p:t},"dzqpers")') == 1
      and BUNDLE.find('r.jsx(DzQuickPersona,{p:t}') > BUNDLE.find("function um({variant:e,activePersona:t}){")
      and BUNDLE.count("function DzQuickPersona(") == 1)
import patch_bundle_dzquick as DQ                                    # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
t214 = [p for p in DQ.PAIRES if "DzQuickPersona" in p[1] or "V(I[0].id)" in p[1]]
check("D5 la vibe suit l'espace dans un effet à part (paire C5 de dzespace intacte)",
      BUNDLE.count('a(v)}},[dzCvQ]);x.useEffect(function(){if(I.length&&!I.some(function(z){return z.id===A}))V(I[0].id)},[dzCvQ]);function M(){') == 1)
check("D3 aucune paire t214 ne porte « aria-label »", len(t214) == 3 and all("aria-label" not in p[1] for p in t214))
check("D4 aucun useState ajouté (useReducer seul)", "x.useState" not in "".join(p[1] for p in t214))

print("[E] clés de traduction")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
CLES = ["quick.persona.libelle", "quick.persona.choisir", "quick.persona.nouveau", "quick.persona.note"]
check("E1 clés quick.persona.* FR/EN dans menus.json", all(isinstance(cat.get(k), dict) and cat[k].get("fr") and cat[k].get("en")
                                                          for k in CLES))
quick = json.loads((RACINE / "frontend" / "shared" / "i18n" / "quick.json").read_text(encoding="utf-8"))
check("E2 absentes de quick.json (générateur L2)", not any(k in quick for k in CLES))
check("E3 chaque clé utilisée par le composant", all(f'dzT("{k}")' in "".join(p[1] for p in t214) for k in CLES))
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("E4 catalogue assemblé à jour (i18n_assembler --check)", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])

print("[F] maillon de queue dzquick")
check("F1 chaque remplacement t214 ×1 dans le bundle", len(t214) == 3 and all(BUNDLE.count(p[1]) == 1 for p in t214))
try:
    avant = DQ.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)


def _rejoue(s):
    try:
        return DQ.appliquer(s)
    except SystemExit as e:
        return str(e)
check("F2 inverse exact : aller-retour à l'octet", DQ.MARKER not in avant and _rejoue(avant) == BUNDLE)
try:
    avant_aide = AIDE.avant_dzquick(BUNDLE)
except AssertionError as e:
    avant_aide = str(e)
check("F3 avant_dzquick rend la ligne figée d'avant", avant_aide == AIDE.avant_dzreglages(avant) and avant.count(LIGNE_FIGEE) == 1
      and "DzQuickPersona" not in avant)
check("F4 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)
check("F5 aucun .bak_dzquick laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzquick")).exists())

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
