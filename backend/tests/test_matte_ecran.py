# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T10, D2b) — le sujet détouré À L'ÉCRAN, dans le bundle LIVRÉ :
  · le rack VFX (bloc VFXRACK exécuté sous node, moteur de hooks minimal, fetch / CustomEvent en doublures) :
    rangée « Sujet » sur un vrai plan (job), modèles SERVIS par /api/matte-models (aucun libellé recopié),
    détourage PAYANT armé par le devis du backend au 1er clic (aucun POST /matte), tiré au 2e, résultat envoyé
    au Montage par `dz-matte` {id, matte} ; « retirer » envoie matte null ; rien sur un plan sans job ;
    bascule derrière / devant par effet (absence = derrière) ; la vignette d'un effet « derrière » demande le
    matte, celle d'un effet « devant » non ;
  · le Montage (bloc SONVFX, lu) : l'écouteur `dz-matte` est posé et retiré, il passe par pushHistory ; le
    payload de rendu joint `matte` seulement sur un vrai plan V1, SANS toucher la ligne `effects:` (ancre V9).
Témoin positif : le bundle de la base (2246fdae) n'a ni la rangée Sujet ni l'écouteur.
Run (depuis backend/) : & $PY tests/test_matte_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
# t144 : la couche passe par dzT (traduction L4) ; le banc exécute/lit son texte français d'avant la traduction
# (test_i18n_l4 garantit qu'elle se défait exactement)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402
BUN = AIDE.avant_i18n_l4((RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8"))
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzmatte_ecran_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "2246fdae"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base a le rack mais ni la rangée Sujet ni l'écouteur dz-matte",
      r0.returncode == 0 and b"const VfxStack=" in r0.stdout and b"vfx-matte" not in r0.stdout and b"dz-matte" not in r0.stdout)

def bloc(tag):
    d, f = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    return BUN.count(d), BUN.split(d, 1)[1].split(f, 1)[0].replace("\r\n", "\n")
n, VFX = bloc("VFXRACK")
check("T1 un seul bloc VFXRACK", n == 1)

print("\n[montage, lu dans le bloc livré]")
n2, SON = bloc("SONVFX")
ec = SON.split('window.addEventListener("dz-matte",onMatte)', 1)
check("M1 l'écouteur dz-matte est posé une fois et retiré au démontage",
      SON.count('window.addEventListener("dz-matte",onMatte)') == 1 and SON.count('window.removeEventListener("dz-matte",onMatte)') == 1)
corps = SON.split("function onMatte(ev){", 1)[1].split("window.addEventListener", 1)[0] if "function onMatte(ev){" in SON else ""
check("M2 il passe par pushHistory (annulable), pose matte sur LE plan (id), marque le projet modifié",
      "pushHistory();" in corps and "k.id===d.id" in corps and "matte:d.matte||void 0" in corps and "setDirty(!0)" in corps, corps[:200])
ligne = 'if(c.tr==="v1"&&c.matte&&c.src&&c.src.job_id)o.matte=c.matte;'
check("M3 le payload joint matte seulement sur un vrai plan V1, une fois", SON.count(ligne) == 1)
k = SON.find(ligne)
check("M4 juste après `opacity:c.opacity};` — la ligne `effects:` (ancre V9) est intacte avant",
      SON.rfind("opacity:c.opacity};", 0, k) > k - 200
      and "effects:(function(){\n            var _fx=(c.effects||[]).filter(function(_f){return !_f.off});" in SON)

HARNAIS = r"""
var CALLS=[],EVTS=[],LS={},REP={},TIMERS=[];
var CUR=null;
function same(a,b){if(!a||!b||a.length!==b.length)return false;for(var i=0;i<a.length;i++)if(a[i]!==b[i])return false;return true}
var x={
  useState:function(v){var I=CUR,i=I.hi++;if(!(i in I.H))I.H[i]=typeof v==="function"?v():v;
    return [I.H[i],function(n){I.H[i]=typeof n==="function"?n(I.H[i]):n}]},
  useRef:function(v){var I=CUR,i=I.hi++;if(!(i in I.H))I.H[i]={current:v};return I.H[i]},
  useMemo:function(f,d){var I=CUR,i=I.hi++,o=I.H[i];if(!o||!same(o.d,d))I.H[i]={v:f(),d:d};return I.H[i].v},
  useCallback:function(f,d){return x.useMemo(function(){return f},d)},
  useEffect:function(f,d){var I=CUR,i=I.hi++,o=I.H[i];if(!o||!d||!same(o.d,d)){I.H[i]={d:d,c:o&&o.c};I.PEND.push([i,f])}},
  useLayoutEffect:function(f,d){return x.useEffect(f,d)},
  useSyncExternalStore:function(sub,get){return get()}};
function el(t,p){return {t:t,p:p||{}}}
var r={jsx:el,jsxs:el,Fragment:"Fragment"};
var localStorage={getItem:function(k){return k in LS?LS[k]:null},setItem:function(k,v){LS[k]=String(v)},removeItem:function(k){delete LS[k]}};
function CustomEvent(t,o){this.type=t;this.detail=o&&o.detail}
var window={localStorage:localStorage,addEventListener:function(){},removeEventListener:function(){},
  dispatchEvent:function(e){EVTS.push({type:e.type,detail:e.detail});return true},
  matchMedia:function(){return {matches:false,addEventListener:function(){},removeEventListener:function(){}}}};
var document={createElement:function(){return {setAttribute:function(){},style:{}}},body:{appendChild:function(){}},
  addEventListener:function(){},removeEventListener:function(){},activeElement:null,visibilityState:"visible"};
var navigator={};
function setTimeout(f,ms){TIMERS.push(f);return TIMERS.length}function clearTimeout(){}
function setInterval(){return 0}function clearInterval(){}
function requestAnimationFrame(){return 0}function cancelAnimationFrame(){}
function Image(){}
function rep(o){return Promise.resolve({ok:o.st<400,status:o.st,headers:{get:function(){return "application/json"}},
  json:function(){return Promise.resolve(o.js)}})}
function fetch(u,o){o=o||{};CALLS.push({u:u,m:o.method||"GET",b:o.body?JSON.parse(o.body):null});
  var k=(o.method||"GET")+" "+String(u).split("?")[0];
  if(REP[k])return rep(REP[k]);
  return rep({st:404,js:{detail:"inconnu "+k}})}
"""

MOTEUR = r"""
function inst(C,props){return {C:C,props:props||{},H:[],hi:0,PEND:[]}}
function render(I){var prev=CUR;CUR=I;I.hi=0;I.PEND=[];var t=I.C(I.props);
  I.PEND.forEach(function(pe){var o=I.H[pe[0]];if(o.c)o.c();var c=pe[1]();o.c=typeof c==="function"?c:null});CUR=prev;return t}
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false||n===true)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
function cls(t,c){return tout(t).filter(function(n){return typeof n.p.className==="string"&&(" "+n.p.className+" ").indexOf(" "+c+" ")>=0})}
function btn(t,label){return tout(t).filter(function(n){return n.t==="button"&&txt(n).trim()===label})[0]}
async function tick(){for(var i=0;i<14;i++)await new Promise(function(res){setImmediate(res)})}
async function stable(I){var t;for(var i=0;i<4;i++){t=render(I);await tick()}return render(I)}
function posts(chemin){return CALLS.filter(function(c){return c.m==="POST"&&c.u===chemin})}
var OUT={};
(async function(){
  REP["GET /api/matte-models"]={st:200,js:{models:[{id:"general",label:"Général (léger)"},{id:"matting",label:"Matting — cheveux, transparences"},
    {id:"portrait",label:"Portrait"}],default:"general"}};
  REP["POST /api/cost/estimate"]={st:200,js:{total_usd:0,breakdown:[{label:"Détourage vidéo (BiRefNet) — prix à mesurer"}]}};
  REP["POST /api/matte"]={st:200,js:{ok:true,matte_id:"m1",usd_note:"prix à mesurer"}};
  REP["GET /api/matte/m1"]={st:200,js:{status:"done",file:"clip_ab12cd34.mov",usd_note:"prix à mesurer"}};
  var CHG=[];
  var clip={id:"c7",tr:"v1",src:{job_id:"j1"},start:2,end:6,srcIn:0};
  var props={effects:[{type:"invert"},{type:"blur",behind:false}],clip:clip,onChange:function(n,h){CHG.push(n)}};
  var DzVfx=window.DzVfx;var S=inst(DzVfx.Stack,props);
  var t=await stable(S);
  var row=function(){return cls(t,"vfx-matte")[0]};
  OUT.ligne=txt(row());
  OUT.options=tout(row()).filter(function(n){return n.t==="option"}).map(function(n){return [n.p.value,txt(n)]});
  OUT.togs=cls(t,"vfx-tog").length;
  // 1er clic : devis, aucun détourage
  CALLS.length=0;btn(row(),"Détourer (fal)").p.onClick();await tick();t=render(S);
  OUT.arme={calls:CALLS.map(function(c){return c.m+" "+c.u+" "+JSON.stringify(c.b)}),btn:!!btn(row(),"Confirmer le détourage"),
    devis:txt(row()).indexOf("prix à mesurer")>=0};
  // le modèle choisi part dans le POST
  tout(row()).filter(function(n){return n.t==="select"})[0].p.onChange({target:{value:"matting"}});t=render(S);
  OUT.desarme_par_modele=!!btn(row(),"Détourer (fal)");
  btn(row(),"Détourer (fal)").p.onClick();await tick();t=render(S);
  CALLS.length=0;EVTS.length=0;btn(row(),"Confirmer le détourage").p.onClick();await tick();await tick();t=render(S);
  OUT.tir={posts:posts("/api/matte").map(function(c){return c.b}),evts:EVTS.slice()};
  // plan détouré : bascules et « retirer »
  props.clip=Object.assign({},clip,{matte:"clip_ab12cd34.mov"});t=render(S);
  OUT.togs2=cls(t,"vfx-tog").map(txt);
  cls(t,"vfx-tog")[0].p.onClick();cls(t,"vfx-tog")[1].p.onClick();
  OUT.patches=CHG.slice(-2).map(function(n){return n.map(function(e){return e.behind===undefined?"absent":e.behind})});
  EVTS.length=0;btn(row(),"retirer").p.onClick();OUT.retire=EVTS.slice();
  OUT.url_derriere=DzVfx.previewUrl(props.clip,{type:"invert"},120);
  OUT.url_devant=DzVfx.previewUrl(props.clip,{type:"blur",behind:false},120);
  OUT.url_sans=DzVfx.previewUrl(clip,{type:"invert"},120);
  // plan sans job (image) : pas de rangée
  var I2=inst(DzVfx.Stack,{effects:[],clip:{id:"c8",tr:"v1",src:{image:"x.png"},start:0,end:2}});
  OUT.sans_job=cls(await stable(I2),"vfx-matte").length;
  console.log(JSON.stringify(OUT));
})().catch(function(e){console.log(JSON.stringify({ERREUR:String(e&&e.stack||e)}))});
"""

js = _TMP / "banc_matte.js"
js.write_text(HARNAIS + VFX + MOTEUR, encoding="utf-8")
p = subprocess.run(["node", str(js)], capture_output=True, text=True, encoding="utf-8", timeout=120)
lignes = [l for l in (p.stdout or "").splitlines() if l.startswith("{")]
OUT = json.loads(lignes[-1]) if lignes else {"ERREUR": (p.stderr or "")[-1500:]}
check("T2 le bloc VFXRACK s'exécute sous node", "ERREUR" not in OUT and p.returncode == 0, str(OUT.get("ERREUR", ""))[:1500])

if "ERREUR" not in OUT:
    print("\n[rack]")
    check("R1 rangée Sujet sur un vrai plan, plan non détouré", "Sujet non détouré" in OUT["ligne"], OUT["ligne"])
    check("R2 modèles SERVIS par /api/matte-models", OUT["options"] == [["general", "Général (léger)"],
          ["matting", "Matting — cheveux, transparences"], ["portrait", "Portrait"]], str(OUT["options"]))
    check("R3 pas de bascule derrière/devant tant que le plan n'est pas détouré", OUT["togs"] == 0)
    a = OUT["arme"]
    check("R4 1er clic : devis du backend (kind matte, durée du plan), AUCUN POST /matte",
          a["calls"] == ['POST /api/cost/estimate {"kind":"matte","duration_s":4}'] and a["btn"] and a["devis"], str(a))
    check("R5 changer de modèle désarme", OUT["desarme_par_modele"])
    check("R6 2e clic : POST /matte avec le job et le modèle choisi",
          OUT["tir"]["posts"] == [{"job_id": "j1", "model": "matting"}], str(OUT["tir"]))
    check("R7 le résultat part au Montage : dz-matte {id du plan, nom du .mov}",
          OUT["tir"]["evts"] == [{"type": "dz-matte", "detail": {"id": "c7", "matte": "clip_ab12cd34.mov"}}], str(OUT["tir"]["evts"]))
    check("R8 plan détouré : une bascule par effet, absence = derrière", OUT["togs2"] == ["derrière", "devant"], str(OUT["togs2"]))
    check("R9 basculer : derrière -> devant (false), devant -> derrière (clé RETIRÉE)",
          OUT["patches"] == [[False, False], ["absent", "absent"]], str(OUT["patches"]))
    check("R10 « retirer » envoie matte null", OUT["retire"] == [{"type": "dz-matte", "detail": {"id": "c7", "matte": None}}],
          str(OUT["retire"]))
    check("R11 la vignette d'un effet « derrière » demande le matte",
          "matte=clip_ab12cd34.mov" in OUT["url_derriere"] and "behind" not in OUT["url_derriere"], OUT["url_derriere"])
    check("R12 … celle d'un effet « devant » non, ni celle d'un plan non détouré",
          "matte=" not in OUT["url_devant"] and "matte=" not in OUT["url_sans"] and "behind" not in OUT["url_devant"],
          OUT["url_devant"] + " | " + OUT["url_sans"])
    check("R13 plan sans job (image) : pas de rangée Sujet", OUT["sans_job"] == 0)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
