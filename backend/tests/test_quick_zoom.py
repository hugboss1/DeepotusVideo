# -*- coding: utf-8 -*-
"""t216 (Menus : Quick, 15/10/2026) — zoom à la molette sur l'aperçu de Quick.

Comme le Vectorlab et le Photolab : la molette zoome AUTOUR DU CURSEUR (`z*1.0015^-deltaY`, bornes 0,25 à 8), le glisser
déplace l'image quand elle est agrandie, le double-clic ou la touche 0 recadre, un badge « 100 % » cliquable recadre
aussi. L'écouteur de molette est NATIF avec `{passive:false}` (le `onWheel` de React est passif : impossible d'empêcher le
défilement de la page). La vue revient à 100 % à chaque nouvelle image ou changement d'onglet (clé du composant).

Ce que ce banc garde :
  [A] `dzVueZoom` (pure, sous node) : le point sous le curseur reste FIXE après un zoom, bornes 0,25 et 8 respectées,
      le glisser ne bouge rien à 100 %, « neutre » remet {z:1,x:0,y:0} ;
  [B] `DzQuickZoom` rendu sous node avec des hooks SIMULÉS à état et un faux élément : écouteur de molette natif
      `{passive:false}` qui appelle preventDefault, transform `translate() scale()` ancrée en 0 0, badge « 200 % » après
      zoom, double-clic / touche 0 / badge recadrent, glisser déplace (agrandi seulement), le glisser natif de l'<img>
      est bloqué (sinon un vrai glisser à la souris ne déplaçait rien : pointercancel), `off` (Voix off) rend les
      enfants tels quels, écouteur retiré au démontage ;
  [C] câblage dans Quick : l'appel `DzQuickStage(…)||repli` est enveloppé par `DzQuickZoom`, clé par onglet + image +
      avatar (remise à 100 %), `off` sur l'onglet Voix off ; `DzQuickStage` reste APPELÉ comme une fonction ;
  [D] clé FR/EN `quick.zoom.recadrer` dans menus.json, catalogue assemblé à jour ;
  [E] maillon de queue `dzquick` : paires t216 ×1, aucune avec « aria-label », inverse exact, `avant_dzquick` rend
      l'aperçu d'avant, comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181), aucun .bak.
t217 (retour de l'utilisateur, 15/10) : ce n'est plus l'image mais la CARTE d'aperçu entière qui zoome — DzQuickZoom
est le calque de la zone (carte dans le flux), molette partout pour agrandir ET réduire, glisser dès que la vue n'est
pas à 100 %, badge au coin de la zone, tous les onglets (plus d'option off) ; [C] vise la carte, plus le contenu.
Run (depuis backend/) : & $PY tests/test_quick_zoom.py"""
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
BASE = "d3cd9d16"
APPEL = 'DzQuickStage({tab:o,img:w,layout:We,avatarUrl:'

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
// React simulé : un composant, hooks par position, effets après rendu, démontage
const H={slots:[],i:0,sale:false,effets:[]};
const x={useReducer(f,arg,init){const i=H.i++;if(!(i in H.slots))H.slots[i]=init?init(arg):arg;
  return[H.slots[i],a=>{const n=f(H.slots[i],a);if(n!==H.slots[i]){H.slots[i]=n;H.sale=true}}]},
 useRef(v){const i=H.i++;if(!(i in H.slots))H.slots[i]={current:v===undefined?null:v};return H.slots[i]},
 useEffect(f,deps){const i=H.i++;const av=H.slots[i];const ch=!av||!deps||deps.length!==av.deps.length||deps.some((d,j)=>d!==av.deps[j]);
  if(ch)H.effets.push(()=>{if(av&&av.nett)av.nett();H.slots[i]={deps:deps||[],nett:f()}});else H.slots[i]=av},
 useState(){throw new Error("useState interdit (compte figé)")}};
const el=(t,p,k)=>({t:typeof t==="string"?t:(t&&t.name)||"?",p:p||{},k});const r={jsx:el,jsxs:el,Fragment:"Fragment"};
const dzT=k=>"⟦"+k+"⟧";
const ENVB={x,r,dzT,Math,console};
const SRC=tranche("var dzVueZoom=","var dzQpPers={};");
const M=new Function("ENV","with(ENV){"+SRC+";return{dzVueZoom,DzQuickZoom}}")(ENVB);
const Z=M.dzVueZoom;
// [A] pur
try{const A={};const v0=Z.neutre();A.neutre=v0;
 const px=100,py=60,v1=Z.autour(v0,px,py,-462.1);A.z1=v1.z;
 A.fixe=Math.abs((px-v1.x)/v1.z-(px-v0.x)/v0.z)<1e-9&&Math.abs((py-v1.y)/v1.z-(py-v0.y)/v0.z)<1e-9;
 const v2=Z.autour(v1,30,200,120);A.fixe2=Math.abs((30-v2.x)/v2.z-(30-v1.x)/v1.z)<1e-9&&Math.abs((200-v2.y)/v2.z-(200-v1.y)/v1.z)<1e-9;
 A.max=Z.autour(v0,0,0,-1e6).z;A.min=Z.autour(v0,0,0,1e6).z;A.borne=[Z.borner(.1),Z.borner(9),Z.borner(2)];
 A.formule=Math.abs(Z.autour(v0,0,0,100).z-Math.pow(1.0015,-100))<1e-12;
 A.glis100=Z.glisser(v0,10,5);A.glis2=Z.glisser({z:2,x:0,y:0},10,5);A.glisDemi=Z.glisser({z:.5,x:0,y:0},10,5);
 A.red=[Z.reduire({z:3,x:4,y:5},{t:"neutre"}),Z.reduire(v0,{t:"glisser",dx:3,dy:4})];
 OUT.A=A}catch(e){OUT.A={err:String(e&&e.stack||e)}}
// [B] composant
try{
 const ECOUTE={};let retire=0;const boite={getBoundingClientRect:()=>({left:50,top:20,width:300,height:500}),
  addEventListener(n,f,o){ECOUTE[n]={f,o}},removeEventListener(n,f){if(ECOUTE[n]&&ECOUTE[n].f===f){delete ECOUTE[n];retire++}}};
 const enfant=el("img",{src:"a.png"});let PROPS={off:false,children:enfant},VUE=null;
 function rendre(){for(let n=0;n<20;n++){H.i=0;H.sale=false;VUE=M.DzQuickZoom(PROPS);
  if(VUE&&VUE.p&&VUE.p.ref&&!VUE.p.ref.current)VUE.p.ref.current=boite;const ef=H.effets;H.effets=[];ef.forEach(f=>f());if(!H.sale&&!ef.length)return}}
 function tous(n,pred,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tous(c,pred,acc));return acc}
  if(pred(n))acc.push(n);tous(n.p&&n.p.children,pred,acc);return acc}
 const vue=()=>tous(VUE,n=>n.p&&n.p["data-dz-qz-vue"])[0],badge=()=>tous(VUE,n=>n.p&&n.p["data-dz-qz-badge"])[0];
 rendre();const B={};
 B.ecoute=!!ECOUTE.wheel&&ECOUTE.wheel.o&&ECOUTE.wheel.o.passive===false;
 B.t0=vue().p.style.transform;B.origine=vue().p.style.transformOrigin;B.badge0=badge().p.children;B.enfant=vue().p.children===enfant;
 // t217 : le calque occupe la zone (étiré, relatif) ; la vue garde la CARTE dans le flux (pas d'absolu), centrée
 B.calque=VUE.p.style;B.vueStyle=vue().p.style;B.badgeStyle=badge().p.style;
 let pd=0;ECOUTE.wheel.f({clientX:150,clientY:120,deltaY:-462.1,preventDefault(){pd++}});rendre();
 B.pd=pd;B.badge1=badge().p.children;B.t1=vue().p.style.transform;B.curseur=VUE.p.style.cursor;
 // glisser
 const cap=[];VUE.p.onPointerDown({button:0,clientX:10,clientY:10,pointerId:7,currentTarget:{setPointerCapture:i=>cap.push(i)}});
 VUE.p.onPointerMove({clientX:30,clientY:15});rendre();VUE.p.onPointerUp({});VUE.p.onPointerMove({clientX:90,clientY:90});rendre();
 B.t2=vue().p.style.transform;B.cap=cap;
 VUE.p.onDoubleClick({});rendre();B.dbl=vue().p.style.transform;
 ECOUTE.wheel.f({clientX:150,clientY:120,deltaY:-462.1,preventDefault(){}});rendre();
 VUE.p.onKeyDown({key:"0",preventDefault(){}});rendre();B.cle0=badge().p.children;
 ECOUTE.wheel.f({clientX:150,clientY:120,deltaY:-462.1,preventDefault(){}});rendre();
 let sp=0;badge().p.onClick({stopPropagation(){sp++}});rendre();B.badgeClic=badge().p.children;B.sp=sp;
 // à 100 % : le glisser ne bouge rien
 VUE.p.onPointerDown({button:0,clientX:0,clientY:0,pointerId:1,currentTarget:{setPointerCapture(){}}});VUE.p.onPointerMove({clientX:40,clientY:40});rendre();
 B.glis100=vue().p.style.transform;
 // t217 : RÉDUIRE (molette vers le bas) puis glisser : la carte réduite se déplace aussi
 ECOUTE.wheel.f({clientX:150,clientY:120,deltaY:462.1,preventDefault(){}});rendre();B.reduit=badge().p.children;B.curseurReduit=VUE.p.style.cursor;
 const tr0=vue().p.style.transform;VUE.p.onPointerDown({button:0,clientX:0,clientY:0,pointerId:2,currentTarget:{setPointerCapture(){}}});
 VUE.p.onPointerMove({clientX:12,clientY:-8});rendre();VUE.p.onPointerUp({});B.trReduit=[tr0,vue().p.style.transform];
 VUE.p.onDoubleClick({});rendre();
 // le glisser natif de l'<img> est bloqué (sinon pointercancel : un vrai glisser ne déplace rien)
 let dsp=0;VUE.p.onDragStart&&VUE.p.onDragStart({preventDefault(){dsp++}});B.dragstart=dsp;B.select=VUE.p.style.userSelect;
 // t217 : plus d'option « off » — la Voix off zoome aussi (la carte entière)
 PROPS={off:true,children:enfant};rendre();B.off=!!(VUE&&VUE.p&&VUE.p["data-dz-qz"])&&B.ecoute;B.retire=retire;
 OUT.B=B}catch(e){OUT.B={err:String(e&&e.stack||e)}}
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
        return {"err": (rn.stdout + rn.stderr)[-600:]}


OUT = node(BUNDLE)
print("[A] dzVueZoom, pure")
A = OUT.get("A") or {}
check("A0 le harnais charge dzVueZoom et DzQuickZoom", "err" not in OUT and "err" not in A, str(OUT.get("err") or A.get("err"))[:400])
check("A1 neutre = {z:1,x:0,y:0}", A.get("neutre") == {"z": 1, "x": 0, "y": 0})
check("A2 le point sous le curseur reste fixe (zoom avant puis arrière)", A.get("fixe") is True and A.get("fixe2") is True)
check("A3 facteur z*1.0015^-deltaY (deltaY -462 ≈ ×2)", A.get("formule") is True and abs((A.get("z1") or 0) - 2) < 0.01,
      repr(A.get("z1")))
check("A4 bornes 0,25 et 8", A.get("max") == 8 and A.get("min") == 0.25 and A.get("borne") == [0.25, 8, 2])
check("A5 glisser : rien à 100 %, déplacement une fois agrandi OU réduit (t217)",
      A.get("glis100") == {"z": 1, "x": 0, "y": 0} and A.get("glis2") == {"z": 2, "x": 10, "y": 5}
      and A.get("glisDemi") == {"z": 0.5, "x": 10, "y": 5}, str(A.get("glisDemi")))
check("A6 réducteur : neutre recadre, glisser à 100 % ne bouge rien",
      A.get("red") == [{"z": 1, "x": 0, "y": 0}, {"z": 1, "x": 0, "y": 0}])

print("[B] DzQuickZoom rendu sous node")
B = OUT.get("B") or {}
check("B0 rendu sans erreur", "err" not in B, str(B.get("err"))[:400])
check("B1 écouteur de molette NATIF {passive:false}", B.get("ecoute") is True)
check("B2 au repos : translate(0px,0px) scale(1), origine 0 0, badge « 100 % », enfants intacts",
      B.get("t0") == "translate(0px,0px) scale(1)" and B.get("origine") == "0 0" and B.get("badge0") == "100 %"
      and B.get("enfant") is True, repr(B)[:300])
import re
def tf(t):
    m = re.fullmatch(r"translate\((-?[\d.e-]+)px,(-?[\d.e-]+)px\) scale\(([\d.e-]+)\)", t or "")
    return tuple(float(g) for g in m.groups()) if m else None
T1 = tf(B.get("t1"))
# curseur à (100, 100) dans la boîte : x = 100 - 100*z, y = 100 - 100*z (le point sous le curseur reste fixe)
check("B3 la molette empêche le défilement et zoome autour du curseur (badge 200 %)", B.get("pd") == 1
      and B.get("badge1") == "200 %" and T1 is not None and abs(T1[2] - 2) < 0.01
      and abs(T1[0] - (100 - 100 * T1[2])) < 1e-6 and abs(T1[1] - (100 - 100 * T1[2])) < 1e-6, repr((B.get("t1"), B.get("badge1"))))
check("B4 agrandi : curseur « grab »", B.get("curseur") == "grab")
T2 = tf(B.get("t2"))
check("B5 le glisser déplace (+20, +5), relâché il ne bouge plus ; capture du pointeur",
      T1 is not None and T2 is not None and abs(T2[0] - T1[0] - 20) < 1e-6 and abs(T2[1] - T1[1] - 5) < 1e-6
      and T2[2] == T1[2] and B.get("cap") == [7], repr((B.get("t1"), B.get("t2"))))
check("B6 double-clic recadre", B.get("dbl") == "translate(0px,0px) scale(1)")
check("B7 touche 0 recadre", B.get("cle0") == "100 %")
check("B8 le badge recadre sans propager le clic", B.get("badgeClic") == "100 %" and B.get("sp") == 1)
check("B9 à 100 % le glisser ne bouge rien", B.get("glis100") == "translate(0px,0px) scale(1)")
check("B11 le glisser natif de l'image est bloqué (onDragStart → preventDefault), pas de sélection",
      B.get("dragstart") == 1 and B.get("select") == "none")
check("B10 t217 : plus d'option off — la Voix off zoome aussi (calque rendu, écouteur gardé)",
      B.get("off") is True and B.get("retire") == 0, str((B.get("off"), B.get("retire"))))
ca, vs, bs = B.get("calque") or {}, B.get("vueStyle") or {}, B.get("badgeStyle") or {}
check("B12 t217 : le calque occupe la zone (flex 1, étiré, relatif, débordement visible)",
      ca.get("flex") == 1 and ca.get("alignSelf") == "stretch" and ca.get("position") == "relative"
      and ca.get("display") == "flex" and ca.get("overflow") == "visible", str(ca))
check("B13 t217 : la vue garde la CARTE dans le flux (pas d'absolu) et la centre",
      vs.get("flex") == 1 and vs.get("display") == "flex" and vs.get("alignItems") == "center"
      and vs.get("justifyContent") == "center" and "position" not in vs and "inset" not in vs, str(vs))
check("B14 t217 : badge au coin de la ZONE (haut droite du calque)", bs.get("position") == "absolute" and bs.get("top") == 0
      and bs.get("right") == 0, str(bs))
TR = [tf(t) for t in (B.get("trReduit") or [None, None])]
check("B15 t217 : la molette vers le bas RÉDUIT (50 %), curseur « grab », et la carte réduite se glisse (+12, -8)",
      B.get("reduit") == "50 %" and B.get("curseurReduit") == "grab" and None not in TR
      and abs(TR[1][0] - TR[0][0] - 12) < 1e-6 and abs(TR[1][1] - TR[0][1] + 8) < 1e-6, repr((B.get("reduit"), B.get("trReduit"))))

print("[C] câblage dans Quick")
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
B0 = r0.stdout.decode("utf-8") if r0.returncode == 0 else ""
check("C0 témoin : la base d3cd9d16 appelle DzQuickStage sans zoom", B0.count(APPEL) == 1 and "DzQuickZoom" not in B0)
# t217 : c'est la CARTE entière (en-tête, contenu, pied) qui est enveloppée, plus le seul contenu
CARTE = 'r.jsxs("div",{style:{...je,background:"linear-gradient(160deg, #053040 0%, #02060d 80%)"'
ENV = 'r.jsx(DzQuickZoom,{children:' + CARTE
FIN = '," · ",h,"s"]})]})]})}),o!=="voice"&&r.jsxs("div",{style:{position:"absolute",bottom:24'
check("C1 t217 : la carte d'aperçu entière est enveloppée par DzQuickZoom (tous onglets)", BUNDLE.count(ENV) == 1
      and BUNDLE.count(CARTE) == 1 and 'DzQuickZoom,{off' not in BUNDLE)
check("C2 t217 : l'enveloppe se ferme juste après la carte (pied compris), avant la ligne de coût",
      BUNDLE.count(FIN) == 1 and BUNDLE.find(FIN) > BUNDLE.find(ENV) > BUNDLE.find("function um({variant:e,activePersona:t}){"))
check("C2b t217 : le contenu DzQuickStage(…)||repli redevient celui d'avant t216 (ni enveloppe, ni clé dzqz-)",
      BUNDLE.count(APPEL) == 1 and "dzqz-" not in BUNDLE and 'children:' + APPEL not in BUNDLE)
check("C3 une seule définition de DzQuickZoom et de dzVueZoom", BUNDLE.count("function DzQuickZoom(") == 1
      and BUNDLE.count("var dzVueZoom=") == 1)

print("[D] clé de traduction")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
check("D1 quick.zoom.recadrer FR/EN dans menus.json", isinstance(cat.get("quick.zoom.recadrer"), dict)
      and cat["quick.zoom.recadrer"].get("fr") and cat["quick.zoom.recadrer"].get("en"))
quick = json.loads((RACINE / "frontend" / "shared" / "i18n" / "quick.json").read_text(encoding="utf-8"))
check("D2 absente de quick.json (générateur L2)", "quick.zoom.recadrer" not in quick)
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D3 catalogue assemblé à jour (i18n_assembler --check)", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])

print("[E] maillon de queue dzquick")
import patch_bundle_dzquick as DQ                                    # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
t216 = [p for p in DQ.PAIRES if "DzQuickZoom" in p[1] or "dzqz-" in p[1] or p[0].startswith('," · ",h,"s"]})')]
check("E1 trois paires du zoom (Z0, Z1 carte, Z2 fin de carte), chacune ×1 dans le bundle", len(t216) == 3 and all(BUNDLE.count(p[1]) == 1 for p in t216))
check("E2 aucune paire t216 ne porte « aria-label », aucun useState", all("aria-label" not in p[1] and "x.useState" not in p[1]
                                                                          for p in t216))
try:
    avant = DQ.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)


def _rejoue(s):
    try:
        return DQ.appliquer(s)
    except SystemExit as e:
        return str(e)
check("E3 inverse exact : aller-retour à l'octet", DQ.MARKER not in avant and _rejoue(avant) == BUNDLE)
try:
    avant_aide = AIDE.avant_dzquick(BUNDLE)
except AssertionError as e:
    avant_aide = str(e)
check("E4 avant_dzquick rend l'aperçu d'avant", avant_aide == AIDE.avant_dzreglages(avant) and "DzQuickZoom" not in avant and avant.count(APPEL) == 1)
check("E5 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)
check("E6 aucun .bak_dzquick laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzquick")).exists())

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
