# -*- coding: utf-8 -*-
"""t218 (Menus : Quick, 15/10/2026) — orbe vocal animé dans l'aperçu de la Voix off.

Retour de l'utilisateur : « sur la version du générateur de voice over, mets dans le display une animation de voice
over professionnelle ». Choix sur maquette : B · orbe vocal (le motif des agents vocaux — états repos / réflexion /
parole, la parole pilotée par le niveau RÉEL de l'audio).
[A] aides pures : `dzOrbeEtat` (repos / gen / lecture), `dzOrbeNiveau` (RMS d'octets temporels, borné 0..1) ;
[B] `DzQuickOrbe` rendu sous node, hooks SIMULÉS à état, faux window / document / audio / AudioContext : repos au départ,
    style injecté une fois, `dz:voix-etat` busy → génération (légende « quick.voix.generation »), le `<audio>` du résultat
    qui joue → lecture, l'AnalyserNode (créé UNE fois par élément) pilote `--dz-orbe-niv`, pause → repos et niveau 0,
    analyse impossible → lecture en pulsation CSS (sans data-analyse), démontage → écouteurs retirés ;
[C] le style : trois états, reduced-motion fige tout, aucune position fixe ;
[D] câblage : l'aperçu de `um` rend l'orbe sur Voix off (DzQuickStage intact), DzQuickVoice publie busy/res par un
    useEffect, aucune clé de traduction neuve, aucun useState, maillon dzquick à l'aller-retour exact.
Run (depuis backend/) : & $PY tests/test_quick_orbe.py"""
import json, pathlib, re, subprocess, sys, tempfile
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

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const H={slots:[],i:0,sale:false,effets:[]};
const x={useReducer(f,arg,init){const i=H.i++;if(!(i in H.slots))H.slots[i]=init?init(arg):arg;
  return[H.slots[i],a=>{const n=f(H.slots[i],a);if(n!==H.slots[i]){H.slots[i]=n;H.sale=true}}]},
 useRef(v){const i=H.i++;if(!(i in H.slots))H.slots[i]={current:v===undefined?null:v};return H.slots[i]},
 useEffect(f,deps){const i=H.i++;const av=H.slots[i];const ch=!av||!deps||deps.length!==av.deps.length||deps.some((d,j)=>d!==av.deps[j]);
  if(ch)H.effets.push(()=>{if(av&&av.nett)av.nett();H.slots[i]={deps:deps||[],nett:f()}});else H.slots[i]=av},
 useState(){throw new Error("useState interdit (compte figé)")}};
const el=(t,p,k)=>({t:typeof t==="string"?t:(t&&t.name)||"?",p:p||{},k});const r={jsx:el,jsxs:el,Fragment:"Fragment"};
const dzT=k=>"⟦"+k+"⟧";
// faux window / document
const ECW={};const win={addEventListener(n,f){(ECW[n]=ECW[n]||[]).push(f)},removeEventListener(n,f){ECW[n]=(ECW[n]||[]).filter(g=>g!==f)},
 dispatchEvent(ev){(ECW[ev.type]||[]).slice().forEach(f=>f(ev));return true}};
class CustomEvent{constructor(t,o){this.type=t;this.detail=o&&o.detail}}
const STYLES=[];const AUDIO={ecoute:{},paused:true,addEventListener(n,f){this.ecoute[n]=f},removeEventListener(n,f){if(this.ecoute[n]===f)delete this.ecoute[n]}};
let AUDIO_PRESENT=false;
const document={head:{appendChild(s){STYLES.push(s)}},getElementById(id){return STYLES.find(s=>s.id===id)||null},
 createElement(t){return{tagName:t,id:"",textContent:""}},querySelector(q){return AUDIO_PRESENT&&q==='[data-dzvores="ok"] audio'?AUDIO:null}};
let IV=[];const setInterval=(f,ms)=>{IV.push({f,ms,on:true});return IV.length};const clearInterval=id=>{if(IV[id-1])IV[id-1].on=false};
let RAF=[];const requestAnimationFrame=f=>{RAF.push(f);return RAF.length};const cancelAnimationFrame=id=>{RAF[id-1]=null};
const AC={n:0,src:0,connect:[],casse:false,resume:0};
class FauxAC{constructor(){if(AC.casse)throw new Error("pas d'audio");AC.n++;this.destination={nom:"dest"}}
 resume(){AC.resume++;return Promise.resolve()}
 createMediaElementSource(a){AC.src++;return{connect:n=>AC.connect.push(["src",n.nom])}}
 createAnalyser(){return{nom:"analyseur",fftSize:2048,connect:d=>AC.connect.push(["an",d.nom]),
  getByteTimeDomainData(b){for(let i=0;i<b.length;i++)b[i]=i%2?255:0}}}}
win.AudioContext=FauxAC;
const ENVB={x,r,dzT,Math,console,window:win,document,CustomEvent,setInterval,clearInterval,requestAnimationFrame,cancelAnimationFrame,Uint8Array,Object,String,Number};
const SRC=tranche("var dzVoixEtat=","var dzQpPers={};");
const M=new Function("ENV","with(ENV){"+SRC+";return{dzOrbeEtat,dzOrbeNiveau,DzQuickOrbe,dzVoixEtatPoser,DZ_ORBE_CSS}}")(ENVB);
try{const A={};
 A.etat=[M.dzOrbeEtat({busy:true},false),M.dzOrbeEtat({busy:true,url:"u"},true),M.dzOrbeEtat({busy:false,url:"u"},false),M.dzOrbeEtat(null,false)];
 const sil=new Uint8Array(64).fill(128),fort=new Uint8Array(64).map((_,i)=>i%2?255:0),moyen=new Uint8Array(64).map((_,i)=>i%2?150:106);
 A.niv=[M.dzOrbeNiveau(sil),M.dzOrbeNiveau(fort),M.dzOrbeNiveau(moyen),M.dzOrbeNiveau(new Uint8Array(0)),M.dzOrbeNiveau(null)];
 OUT.A=A}catch(e){OUT.A={err:String(e&&e.stack||e)}}
try{
 const COEUR={props:{},style:{setProperty(k,v){COEUR.props[k]=v}}};let VUE=null;
 function rendre(){for(let n=0;n<20;n++){H.i=0;H.sale=false;VUE=M.DzQuickOrbe({});
   (function poser(nd){if(!nd||typeof nd!=="object")return;if(Array.isArray(nd)){nd.forEach(poser);return}
    if(nd.p&&nd.p.ref&&nd.p.className==="dz-orbe-coeur")nd.p.ref.current=COEUR;poser(nd.p&&nd.p.children)})(VUE);
   const ef=H.effets;H.effets=[];ef.forEach(f=>f());if(!H.sale&&!ef.length)return}}
 function tous(n,pred,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tous(c,pred,acc));return acc}
  if(pred(n))acc.push(n);tous(n.p&&n.p.children,pred,acc);return acc}
 const cls=c=>tous(VUE,n=>n.p&&n.p.className===c);const leg=()=>(cls("dz-orbe-legende")[0]||{p:{}}).p.children;
 const B={};rendre();
 B.repos={etat:VUE.p["data-dz-orbe"],leg:leg(),ondes:cls("dz-orbe-onde").length,coeur:cls("dz-orbe-coeur").length,
  nappe:cls("dz-orbe-nappe").length,reflet:cls("dz-orbe-reflet").length,racine:VUE.p.className};
 B.style=STYLES.filter(s=>s.id==="dz-orbe-style").length;rendre();B.style2=STYLES.filter(s=>s.id==="dz-orbe-style").length;
 B.ecoute=(ECW["dz:voix-etat"]||[]).length;
 M.dzVoixEtatPoser(true,null);rendre();B.gen={etat:VUE.p["data-dz-orbe"],leg:leg(),glob:win.dzVoixEtat||null};
 M.dzVoixEtatPoser(false,{url:"/files/voix.mp3"});rendre();B.fini={etat:VUE.p["data-dz-orbe"],leg:leg()};
 // l'<audio> du résultat apparaît, le balayage le trouve
 B.iv=IV.filter(v=>v.on).map(v=>v.ms);AUDIO_PRESENT=true;IV.filter(v=>v.on).forEach(v=>v.f());
 B.audioEcoute=Object.keys(AUDIO.ecoute).sort();B.ivFin=IV.filter(v=>v.on).length;
 AUDIO.ecoute.play();rendre();
 B.lecture={etat:VUE.p["data-dz-orbe"],analyse:VUE.p["data-analyse"]||null,ac:AC.n,src:AC.src,connect:AC.connect.slice(),resume:AC.resume};
 const f=RAF.filter(Boolean).pop();f&&f();B.niv=COEUR.props["--dz-orbe-niv"];
 AUDIO.ecoute.pause();rendre();B.pause={etat:VUE.p["data-dz-orbe"],niv:COEUR.props["--dz-orbe-niv"]};
 AUDIO.ecoute.play();rendre();B.rejoue={src:AC.src,ac:AC.n,etat:VUE.p["data-dz-orbe"]};
 AUDIO.ecoute.ended();rendre();B.fin=VUE.p["data-dz-orbe"];
 // démontage : écouteurs retirés
 H.slots.forEach(s=>{if(s&&s.nett)s.nett()});B.demonte={win:(ECW["dz:voix-etat"]||[]).length,audio:Object.keys(AUDIO.ecoute).length};
 OUT.B=B}catch(e){OUT.B={err:String(e&&e.stack||e)}}
// analyse impossible : la lecture reste animée (pulsation CSS), sans data-analyse
try{H.slots=[];H.effets=[];AC.casse=true;delete win.__dzOrbeCtx;const A2={ecoute:{},paused:true,addEventListener(n,f){this.ecoute[n]=f},removeEventListener(){}};
 document.querySelector=q=>A2;let V=null;const rd=()=>{for(let n=0;n<20;n++){H.i=0;H.sale=false;V=M.DzQuickOrbe({});const ef=H.effets;H.effets=[];ef.forEach(f=>f());if(!H.sale&&!ef.length)return}};
 rd();M.dzVoixEtatPoser(false,{url:"/files/b.mp3"});rd();IV.filter(v=>v.on).forEach(v=>v.f());A2.ecoute.play();rd();
 OUT.C={etat:V.p["data-dz-orbe"],analyse:V.p["data-analyse"]||null};OUT.stylesApresRemontage=STYLES.filter(s=>s.id==="dz-orbe-style").length}catch(e){OUT.C={err:String(e&&e.stack||e)}}
OUT.css=M.DZ_ORBE_CSS;
process.stdout.write(JSON.stringify(OUT));
"""


def node(bundle_texte):
    with tempfile.TemporaryDirectory() as td:
        b = pathlib.Path(td) / "b.js"; b.write_text(bundle_texte, encoding="utf-8")
        h = pathlib.Path(td) / "h.js"; h.write_text(HARNAIS, encoding="utf-8")
        rn = subprocess.run(["node", str(h), str(b)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(rn.stdout)
    except ValueError:
        return {"err": (rn.stdout + rn.stderr)[-800:]}


OUT = node(BUNDLE)
print("[A] aides pures")
A = OUT.get("A") or {}
check("A0 le harnais charge l'orbe", "err" not in OUT and "err" not in A, str(OUT.get("err") or A.get("err"))[:500])
check("A1 dzOrbeEtat : busy → gen, lecture prime, sinon repos", A.get("etat") == ["gen", "lecture", "repos", "repos"], str(A.get("etat")))
nv = A.get("niv") or []
check("A2 dzOrbeNiveau : silence 0, pleine amplitude bornée à 1, moyen entre les deux, vide ou absent 0",
      len(nv) == 5 and nv[0] == 0 and nv[1] == 1 and 0.2 < nv[2] < 0.9 and nv[3] == 0 and nv[4] == 0, str(nv))

print("[B] DzQuickOrbe rendu sous node")
B = OUT.get("B") or {}
check("B0 rendu sans erreur", "err" not in B, str(B.get("err"))[:500])
rp = B.get("repos") or {}
check("B1 au repos : data-dz-orbe=repos, trois ondes, cœur (nappe + reflet), légende de la voix off",
      rp == {"etat": "repos", "leg": "⟦quick.scene.voix_off⟧", "ondes": 3, "coeur": 1, "nappe": 1, "reflet": 1, "racine": "dz-orbe"}, str(rp))
check("B2 style injecté UNE fois (#dz-orbe-style), même après un second rendu et un second orbe monté",
      B.get("style") == 1 and B.get("style2") == 1 and OUT.get("stylesApresRemontage") == 1, str(OUT.get("stylesApresRemontage")))
check("B3 écoute l'évènement dz:voix-etat", B.get("ecoute") == 1)
g = B.get("gen") or {}
check("B4 génération (busy) → data-dz-orbe=gen, légende « quick.voix.generation », état global publié",
      g.get("etat") == "gen" and g.get("leg") == "⟦quick.voix.generation⟧" and (g.get("glob") or {}).get("busy") is True, str(g))
check("B5 génération finie → repos", (B.get("fini") or {}).get("etat") == "repos")
check("B6 un résultat audio → balayage (300 ms) qui accroche play / pause / ended puis s'arrête",
      B.get("iv") == [300] and B.get("audioEcoute") == ["ended", "pause", "play"] and B.get("ivFin") == 0,
      str((B.get("iv"), B.get("audioEcoute"), B.get("ivFin"))))
lc = B.get("lecture") or {}
check("B7 lecture → data-dz-orbe=lecture, data-analyse, UN AudioContext, source → analyseur → sortie, contexte relancé",
      lc.get("etat") == "lecture" and lc.get("analyse") == "1" and lc.get("ac") == 1 and lc.get("src") == 1
      and lc.get("connect") == [["src", "analyseur"], ["an", "dest"]] and lc.get("resume", 0) >= 1, str(lc))
check("B8 le niveau RÉEL de l'audio pilote --dz-orbe-niv (pleine amplitude → 1.000)", B.get("niv") == "1.000", str(B.get("niv")))
check("B9 pause → repos, niveau remis à 0", B.get("pause") == {"etat": "repos", "niv": "0"}, str(B.get("pause")))
check("B10 relecture : aucune seconde source ni second contexte (createMediaElementSource ne se rappelle pas)",
      B.get("rejoue") == {"src": 1, "ac": 1, "etat": "lecture"}, str(B.get("rejoue")))
check("B11 fin de lecture → repos", B.get("fin") == "repos")
check("B12 démontage : écouteurs de la fenêtre et de l'audio retirés", B.get("demonte") == {"win": 0, "audio": 0}, str(B.get("demonte")))
C = OUT.get("C") or {}
check("B13 analyse impossible : lecture quand même (pulsation CSS), sans data-analyse", C == {"etat": "lecture", "analyse": None}, str(C))

print("[C] le style")
css = OUT.get("css") or ""
check("C1 trois états stylés (gen et lecture plus rapides que le repos)",
      '[data-dz-orbe=gen]' in css and '[data-dz-orbe=lecture]' in css and "dz-orbe-tour 9s" in css)
m = re.search(r"@media \(prefers-reduced-motion:reduce\)\{(.*?)\}\}", css)
fige = re.findall(r"([^{}]+)\{animation:none!important\}", m.group(1)) if m else []
sel = {s.strip() for s in fige[0].split(",")} if len(fige) == 1 else set()
check("C2 prefers-reduced-motion fige nappe, ondes et cœur (une règle animation:none!important sur les trois)",
      sel == {".dz-orbe-nappe", ".dz-orbe-onde", ".dz-orbe-coeur"}, str(fige))
def _duree(selecteur):
    mm = re.search(re.escape(selecteur) + r"\{[^}]*?animation(?:-duration)?:(?:[a-z-]+ )?([\d.]+)s", css)
    return float(mm.group(1)) if mm else None
dr, dg = _duree(".dz-orbe-nappe"), _duree(".dz-orbe[data-dz-orbe=gen] .dz-orbe-nappe")
orp, ogn = _duree(".dz-orbe-onde"), _duree(".dz-orbe[data-dz-orbe=gen] .dz-orbe-onde")
check("C1b la génération tourne et ondule au moins deux fois plus vite que le repos",
      None not in (dr, dg, orp, ogn) and dg * 2 <= dr and ogn * 2 <= orp, str((dr, dg, orp, ogn)))
check("C3 l'échelle du cœur suit --dz-orbe-niv ; en lecture analysée la pulsation CSS se coupe",
      "var(--dz-orbe-niv)" in css and "[data-dz-orbe=lecture][data-analyse] .dz-orbe-coeur{animation:none}" in css)
check("C4 aucune position fixe, l'orbe ne capte pas les clics (zoom de la carte)", "position:fixed" not in css
      and re.search(r"\.dz-orbe\{[^}]*pointer-events:none", css) is not None)

print("[D] câblage")
APPEL = 'DzQuickStage({tab:o,img:w,layout:We,avatarUrl:'
check("D1 l'aperçu de um rend l'orbe sur Voix off, DzQuickStage sinon",
      BUNDLE.count('o==="voice"?r.jsx(DzQuickOrbe,{}):' + APPEL) == 1 and BUNDLE.count(APPEL) == 1)
check("D2 DzQuickStage intact (sa branche voix garde le message, pour tout autre appelant)",
      BUNDLE.count('if(tab==="voice")return msg(dzT("quick.scene.voix_off"));') == 1)
check("D3 DzQuickVoice publie busy et res par un useEffect",
      BUNDLE.count('res=q7[0],setRes=q7[1],dzVoE=x.useEffect(function(){dzVoixEtatPoser(busy,res)},[busy,res])') == 1)
check("D4 une seule définition de l'orbe et de ses aides", BUNDLE.count("function DzQuickOrbe(") == 1
      and BUNDLE.count("var dzVoixEtat=") == 1 and BUNDLE.count("function dzOrbeNiveau(") == 1)
cat = {}
for f in (RACINE / "frontend" / "shared" / "i18n").glob("*.json"):
    try:
        cat.update(json.loads(f.read_text(encoding="utf-8")))
    except ValueError:
        pass
check("D5 aucune clé neuve : les légendes réutilisent quick.scene.voix_off et quick.voix.generation (FR/EN)",
      all(isinstance(cat.get(k), dict) and cat[k].get("fr") and cat[k].get("en") for k in ("quick.scene.voix_off", "quick.voix.generation")))
import patch_bundle_dzquick as DQ                                    # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
orb = [p for p in DQ.PAIRES if "DzQuickOrbe" in p[1] or "dzVoixEtatPoser" in p[1]]
check("D6 paires de l'orbe ×1, sans useState ni aria-label", len(orb) >= 3 and all(BUNDLE.count(p[1]) == 1 for p in orb)
      and all("x.useState" not in p[1] and "aria-label" not in p[1] for p in orb), str(len(orb)))
try:
    avant = DQ.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)
try:
    aller = DQ.appliquer(avant)
except SystemExit as e:
    aller = str(e)
check("D7 maillon dzquick : aller-retour exact, avant_dzquick identique, sans orbe",
      aller == BUNDLE and AIDE.avant_dzquick(BUNDLE) == avant and "DzQuickOrbe" not in avant)
check("D8 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
