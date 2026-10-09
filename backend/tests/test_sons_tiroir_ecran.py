# -*- coding: utf-8 -*-
"""T101 (plan-son-vfx T4-T5, P3/P3b) — le tiroir Sons de RÉFÉRENCE, dans le bundle LIVRÉ : le bloc SFXSTUDIO est
extrait et EXÉCUTÉ sous node (moteur de hooks minimal, fetch / Audio / minuteries / localStorage en doublures qui
notent tout). Ce qui est vérifié : tags affichés et édités (PUT), recherche par tag, filtre Mes sons / Catalogue,
tri « Plus anciens », stems de T100 classés (vocals = Voix), mère affichée, actions par son — PAYANTES armées par le
devis du BACKEND au premier clic et tirées au second, Échap désarme, GRATUITE en un clic —, pré-écoute au survol
(coupée par défaut, persistée), et le mode `inline` (toujours ouvert, sans « Fermer », sans voler le focus).
Puis le maillon libsons : la puce Audio de la Bibliothèque monte le tiroir, une fois, avant la zone d'import.
Témoin positif : le bundle de la base (31969216) n'a ni les tags du tiroir ni le montage dans la Bibliothèque.
Run (depuis backend/) : & $PY tests/test_sons_tiroir_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
# t144 : la couche passe par dzT (traduction L4) ; le banc exécute/lit son texte français d'avant la traduction
# (test_i18n_l4 garantit qu'elle se défait exactement)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402
BUN = AIDE.avant_i18n_l4((RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8"))
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzsons_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "31969216"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base a le tiroir mais ni ses tags ni son montage dans la Bibliothèque",
      r0.returncode == 0 and b"const SvxDrawer=" in r0.stdout and b"svx-itags" not in r0.stdout and b"dz-libsons" not in r0.stdout)

DEB, FIN = "/*__DZ_SFXSTUDIO_BEGIN__*/", "/*__DZ_SFXSTUDIO_END__*/"
check("T1 un seul bloc SFXSTUDIO", BUN.count(DEB) == 1 and BUN.count(FIN) == 1)
BLOC = BUN.split(DEB, 1)[1].split(FIN, 1)[0].replace("\r\n", "\n")

print("\n[libsons] la puce Audio de la Bibliothèque")
ANCRE = 'o==="Audio"&&r.jsxs("div",{style:{marginBottom:14,display:"grid",gap:10},children:['
INSERT = ('window.DzSfx&&window.DzSfx.ready&&r.jsx("div",{className:"dzsvm dz-libsons",'
          'children:r.jsx(window.DzSfx.Drawer,{open:!0,inline:!0,defaultTab:"tous"})}),')
check("L1 le tiroir est monté UNE fois, premier enfant de la grille de l'onglet Audio (avant la zone d'import)",
      BUN.count(INSERT) == 1 and BUN.count(ANCRE + INSERT + 'r.jsxs("div",{onClick:()=>') == 1 and BUN.count("dz-libsons") == 1)
check("L1b la chaîne figée par le maillon montage (P9lib6 : DzMetaChips + ouverture du bloc Audio) n'est pas coupée",
      BUN.count(',r.jsx(DzMetaChips,{o:o,T:T,f:dzMF,setF:dzMFs}),' + ANCRE) == 1)
k = BUN.find(INSERT)
check("L2 dans l'écran Bibliothèque, après les chips de provenance et de méta",
      0 < BUN.rfind("r.jsx(DzMetaChips,", 0, k) > k - 400 and BUN.rfind("__dzSrcChips(o,T,dzSF,dzSFs)", 0, k) > k - 500)
check("L3 feature-detect : rien sans la couche (false dans la grille)", INSERT.startswith('window.DzSfx&&window.DzSfx.ready&&'))
css = (RACINE / "frontend" / "dist" / "shared" / "sfxstudio.css").read_bytes()
check("L4 l'hôte de la Bibliothèque n'est plus absolu (la racine .dzsvm l'est) et a une hauteur",
      b".dzsvm.dz-libsons{position:relative;inset:auto;height:" in css and b"margin-bottom:14px;border-radius:8px}" not in css and css.count(b"\r\n") == css.count(b"\n"))

HARNAIS = r"""
var H=[],hi=0,PEND=[],CALLS=[],AUDIOS=[],TIMERS=[],LS={},FOCUS=0,REP={};
function same(a,b){if(!a||!b||a.length!==b.length)return false;for(var i=0;i<a.length;i++)if(a[i]!==b[i])return false;return true}
var x={
  useState:function(v){var i=hi++;if(!(i in H))H[i]=typeof v==="function"?v():v;
    return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]},
  useMemo:function(f,d){var i=hi++,o=H[i];if(!o||!same(o.d,d))H[i]={v:f(),d:d};return H[i].v},
  useCallback:function(f,d){return x.useMemo(function(){return f},d)},
  useEffect:function(f,d){var i=hi++,o=H[i];if(!o||!d||!same(o.d,d)){H[i]={d:d,c:o&&o.c};PEND.push([i,f])}}};
function el(t,p){return {t:t,p:p||{}}}
var r={jsx:el,jsxs:el,Fragment:"Fragment"};
var localStorage={getItem:function(k){return k in LS?LS[k]:null},setItem:function(k,v){LS[k]=String(v)}};
var window={localStorage:localStorage};
var document={createElement:function(){return {setAttribute:function(){},style:{}}},body:{appendChild:function(){}},activeElement:null};
function setTimeout(f,ms){TIMERS.push({f:f,ms:ms,on:true});return TIMERS.length}
function clearTimeout(id){if(id&&TIMERS[id-1])TIMERS[id-1].on=false}
function Audio(u){this.url=u;this.currentTime=0;this.duration=NaN;AUDIOS.push(this)}
Audio.prototype.play=function(){return Promise.resolve()};Audio.prototype.pause=function(){};
function rep(o){return Promise.resolve({ok:o.st<400,status:o.st,json:function(){return Promise.resolve(o.js)}})}
function fetch(u,o){o=o||{};CALLS.push({u:u,m:o.method||"GET",b:o.body?JSON.parse(o.body):null});
  var k=(o.method||"GET")+" "+u.split("?")[0];
  if(REP[k])return rep(REP[k]);
  if(k.indexOf("PUT /api/audio/meta/")===0)return rep({st:200,js:{ok:true}});
  return rep({st:404,js:{detail:"inconnu "+k}})}
var SVM_WAVES=new Map();function svmSrcKey(s){return "a:"+(s&&s.audio)}
function svmShort(s){return String(Math.round(s*10)/10)+"s"}
function SvmLabel(p){return el("div",p)}
function svmSharedAC(){return null}function svmAudioDur(){return 0}function svmWavePeaks(){return Promise.resolve(null)}
function svmUseNote(){var st=x.useState(""),n=st[0],set=st[1];return [n,function(m){set(m)}]}
"""

MOTEUR = r"""
var PROPS={open:true};
function render(){hi=0;PEND=[];var t=window.DzSfx.Drawer(PROPS);
  PEND.forEach(function(pe){var o=H[pe[0]];if(o.c)o.c();var c=pe[1]();o.c=typeof c==="function"?c:null});return t}
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
function cls(t,c){return tout(t).filter(function(n){return typeof n.p.className==="string"&&(" "+n.p.className+" ").indexOf(" "+c+" ")>=0})}
function rangees(t){return tout(t).filter(function(n){return n.p["data-svx-item"]})}
function rangee(t,nom){return rangees(t).filter(function(n){return n.p["data-svx-item"]===nom})[0]}
function stop(){return {stopPropagation:function(){},preventDefault:function(){},defaultPrevented:false}}
async function tick(){for(var i=0;i<12;i++)await new Promise(function(res){setImmediate(res)})}
async function stable(){var t;for(var i=0;i<4;i++){t=render();await tick()}return render()}
function bouton(t,nom,act){var rg=rangee(t,nom);return rg&&tout(rg).filter(function(n){return n.p["data-act"]===act})[0]}
var OUT={};
(async function(){
  REP["GET /api/audio"]={st:200,js:{audio:[
    {name:"theme.mp3",url:"/api/audio/theme.mp3",size_kb:900,mtime:300},
    {name:"stem_theme_vocals.mp3",url:"/api/audio/stem_theme_vocals.mp3",size_kb:400,mtime:250},
    {name:"prise.mp3",url:"/api/audio/prise.mp3",size_kb:200,mtime:200},
    {name:"porte.mp3",url:"/api/audio/porte.mp3",size_kb:50,mtime:100}]}};
  REP["GET /api/audio/meta"]={st:200,js:{meta:{
    "theme.mp3":{kind:"musique"},
    "stem_theme_vocals.mp3":{kind:"stem",stem:"vocals",parent:"theme.mp3"},
    "prise.mp3":{kind:"voix",tags:["brut","studio"]},
    "porte.mp3":{kind:"sfx",starter_id:"kenney-door",tags:["bois"]}}}};
  REP["POST /api/cost/estimate"]={st:200,js:{total_usd:0.042,breakdown:[]}};
  REP["POST /api/audio/stems"]={st:200,js:{items:[{filename:"stem_theme_drums.mp3"},{filename:"stem_theme_bass.mp3"}],missing:["piano"],usd:0.042}};
  REP["POST /api/audio/enhance"]={st:200,js:{filename:"clean_prise.mp3",usd:0}};
  REP["POST /api/audio/isolate"]={st:200,js:{filename:"iso_prise.mp3",usd:0.016}};
  [["theme.mp3",60],["stem_theme_vocals.mp3",60],["prise.mp3",4],["porte.mp3",1]].forEach(function(p){
    SVM_WAVES.set("a:"+p[0],{st:"ok",dur:p[1],peaks:[0.5]})});
  var t=await stable();
  OUT.noms=rangees(t).map(function(n){return n.p["data-svx-item"]});
  OUT.badges=rangees(t).map(function(n){return txt(cls(n,"svx-ibadge")[0])});
  OUT.tags=rangees(t).map(function(n){return cls(n,"svx-itag").map(txt)});
  OUT.boutons=rangees(t).map(function(n){return tout(n).filter(function(b){return b.p["data-act"]}).map(function(b){return b.p["data-act"]})});
  OUT.close=cls(t,"svx-dclose").length;OUT.inlineCls=t.p.className;
  var search=tout(t).filter(function(n){return n.p.className==="svx-searchin"})[0];
  search.p.onChange({target:{value:"BOIS"}});t=render();OUT.parTag=rangees(t).map(function(n){return n.p["data-svx-item"]});
  search.p.onChange({target:{value:""}});t=render();
  var seg=cls(t,"svx-segbtn");OUT.segs=seg.map(txt);
  seg[2].p.onClick();t=render();OUT.catalogue=rangees(t).map(function(n){return n.p["data-svx-item"]});
  cls(t,"svx-segbtn")[1].p.onClick();t=render();OUT.miens=rangees(t).map(function(n){return n.p["data-svx-item"]});
  cls(t,"svx-segbtn")[0].p.onClick();t=render();
  var sel=tout(t).filter(function(n){return n.p.className==="svx-select"})[0];
  OUT.options=kids(sel).map(function(o){return o.p.value});
  sel.p.onChange({target:{value:"ancien"}});t=render();OUT.anciens=rangees(t).map(function(n){return n.p["data-svx-item"]});
  sel.p.onChange({target:{value:"recent"}});t=render();
  // stems : premier clic = devis, AUCUN tir ; second clic = tir
  CALLS.length=0;
  bouton(t,"theme.mp3","stems").p.onClick(stop());t=render();await tick();t=render();
  OUT.arme={calls:CALLS.map(function(c){return c.m+" "+c.u+" "+JSON.stringify(c.b)}),txt:txt(bouton(t,"theme.mp3","stems")),
    cls:bouton(t,"theme.mp3","stems").p.className};
  bouton(t,"theme.mp3","stems").p.onClick(stop());t=render();await tick();t=await stable();
  OUT.tire={calls:CALLS.map(function(c){return c.m+" "+c.u+" "+JSON.stringify(c.b)}),note:txt(cls(t,"svx-note")[0])};
  // Échap désarme une action armée
  CALLS.length=0;
  bouton(t,"prise.mp3","isolate").p.onClick(stop());t=render();await tick();t=render();
  OUT.armeIso=bouton(t,"prise.mp3","isolate").p.className;
  t.p.onKeyDown({key:"Escape",target:{tagName:"ASIDE"},preventDefault:function(){},stopPropagation:function(){}});t=render();
  OUT.desarme=bouton(t,"prise.mp3","isolate").p.className;
  OUT.isoAppels=CALLS.filter(function(c){return c.u==="/api/audio/isolate"}).length;
  // gratuite : un clic
  CALLS.length=0;
  bouton(t,"prise.mp3","enhance").p.onClick(stop());await tick();t=await stable();
  OUT.enhance=CALLS.filter(function(c){return c.m==="POST"}).map(function(c){return c.u+" "+JSON.stringify(c.b)});
  // tags : + tag -> champ -> Entrée -> PUT
  CALLS.length=0;
  var add=tout(rangee(t,"porte.mp3")).filter(function(n){return n.p.className==="svx-itag svx-itag-add"})[0];
  add.p.onClick(stop());t=render();
  var champ=tout(rangee(t,"porte.mp3")).filter(function(n){return n.p.className==="svx-tagin"})[0];
  OUT.champVal=champ.p.value;
  champ.p.onChange({target:{value:"bois, porte ; grince,"}});t=render();
  champ=tout(rangee(t,"porte.mp3")).filter(function(n){return n.p.className==="svx-tagin"})[0];
  champ.p.onKeyDown({key:"Enter",preventDefault:function(){},stopPropagation:function(){}});await tick();t=await stable();
  OUT.put=CALLS.filter(function(c){return c.m==="PUT"}).map(function(c){return c.u+" "+JSON.stringify(c.b)});
  OUT.champFerme=tout(rangee(t,"porte.mp3")).filter(function(n){return n.p.className==="svx-tagin"}).length;
  // survol : coupé par défaut ; activé -> persisté, et 350 ms plus tard la pré-écoute part
  TIMERS.length=0;AUDIOS.length=0;
  rangee(t,"porte.mp3").p.onMouseEnter();OUT.survolCoupe={timers:TIMERS.length,audios:AUDIOS.length,ls:LS.dz_sfx_hover};
  var hb=cls(t,"svx-hoverbtn")[0];hb.p.onClick();t=render();
  OUT.lsHover=LS.dz_sfx_hover;
  rangee(t,"porte.mp3").p.onMouseEnter();OUT.timerMs=TIMERS.length?TIMERS[TIMERS.length-1].ms:null;
  rangee(t,"porte.mp3").p.onMouseLeave();OUT.annule=TIMERS[TIMERS.length-1].on;
  rangee(t,"porte.mp3").p.onMouseEnter();TIMERS[TIMERS.length-1].f();t=render();
  OUT.joue=AUDIOS.map(function(a){return a.url});
  console.log(JSON.stringify(OUT));
})().catch(function(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""

INLINE = r"""
var PROPS={open:false,inline:true};
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
REP["GET /api/audio"]={st:200,js:{audio:[]}};REP["GET /api/audio/meta"]={st:200,js:{meta:{}}};
hi=0;PEND=[];var t=window.DzSfx.Drawer(PROPS);
var focus=0;PEND.forEach(function(pe){pe[1]()});
var ferme=(function(){H=[];hi=0;PEND=[];return window.DzSfx.Drawer({open:false})})();
console.log(JSON.stringify({cls:t&&t.p.className,close:tout(t).filter(function(n){return /svx-dclose/.test(n.p.className||"")}).length,
  hintB:JSON.stringify(t).indexOf('" fermer"')>=0,ferme:ferme===null}));
"""


def node(js, nom):
    p = _TMP / nom
    p.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    ligne = (r.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        return json.loads(ligne)
    except Exception:
        return {"erreur": r.stdout[-400:] + r.stderr[-800:]}


print("\n[tiroir] exécuté sous node")
o = node(HARNAIS + BLOC + MOTEUR, "tiroir.js")
check("U0 le tiroir livré s'exécute", "erreur" not in o, str(o.get("erreur", ""))[:600])
if "erreur" not in o:
    check("U1 quatre sons, ordre servi (récents)", o["noms"] == ["theme.mp3", "stem_theme_vocals.mp3", "prise.mp3", "porte.mp3"], str(o["noms"]))
    check("U2 le stem « vocals » de T100 est une VOIX (badge), la piste une musique",
          o["badges"] == ["MUS", "VOIX", "VOIX", "SFX"], str(o["badges"]))
    check("U3 tags du sidecar, chip catalogue pour le son de démarrage, mère pour le stem",
          o["tags"][2][:2] == ["brut", "studio"] and "catalogue" in o["tags"][3] and "bois" in o["tags"][3]
          and "← theme.mp3" in o["tags"][1] and all(tg[-1] == "+ tag" for tg in o["tags"]), str(o["tags"]))
    check("U4 actions : stems sur la musique seule ; isoler + améliorer sur les voix ; rien sur un SFX",
          o["boutons"] == [["stems"], ["isolate", "enhance"], ["isolate", "enhance"], []], str(o["boutons"]))
    check("U5 recherche par TAG, sans casse", o["parTag"] == ["porte.mp3"], str(o["parTag"]))
    check("U6 origine : Tous / Mes sons / Catalogue", o["segs"] == ["Tous", "Mes sons", "Catalogue"]
          and o["catalogue"] == ["porte.mp3"] and o["miens"] == ["theme.mp3", "stem_theme_vocals.mp3", "prise.mp3"],
          f"{o['segs']} {o['catalogue']} {o['miens']}")
    check("U7 tri « Plus anciens » (l'inverse de Récents, qui est déjà l'ordre par date)",
          "ancien" in o["options"] and o["anciens"] == ["porte.mp3", "prise.mp3", "stem_theme_vocals.mp3", "theme.mp3"], str(o["anciens"]))
    a = o["arme"]
    check("U8 stems, PREMIER clic : seul le devis du backend part (kind stems, durée du son), rien n'est tiré",
          a["calls"] == ['POST /api/cost/estimate {"kind":"stems","duration_s":60}'], str(a["calls"]))
    check("U9 le bouton armé affiche le prix du devis", "svx-armed" in a["cls"] and a["txt"] == "~$0.042 ✓", f"{a['cls']} {a['txt']!r}")
    tr = o["tire"]
    check("U10 SECOND clic : le tir part, sur ce fichier", tr["calls"][-1:] and tr["calls"][1] == 'POST /api/audio/stems {"filename":"theme.mp3"}', str(tr["calls"]))
    check("U11 la note dit le nombre de stems, les manquants et le coût", "2 stems posés en Bibliothèque" in tr["note"]
          and "manquants : piano" in tr["note"] and "~$0.042" in tr["note"], tr["note"])
    check("U12 Échap désarme une action armée, sans tir", "svx-armed" in o["armeIso"] and "svx-armed" not in o["desarme"]
          and o["isoAppels"] == 0, f"{o['armeIso']} {o['desarme']} {o['isoAppels']}")
    check("U13 améliorer (gratuit) : UN clic, aucun devis", o["enhance"] == ['/api/audio/enhance {"filename":"prise.mp3"}'], str(o["enhance"]))
    check("U14 + tag : le champ s'ouvre avec les tags actuels", o["champVal"] == "bois", o["champVal"])
    check("U15 Entrée : PUT des tags découpés (virgule ou point-virgule, vides ôtés), champ refermé",
          o["put"] == ['/api/audio/meta/porte.mp3 {"tags":["bois","porte","grince"]}'] and o["champFerme"] == 0, str(o["put"]))
    check("U16 survol COUPÉ par défaut : rien ne joue", o["survolCoupe"] == {"timers": 0, "audios": 0, "ls": "0"}, str(o["survolCoupe"]))
    check("U17 survol activé : persisté (dz_sfx_hover=1), 350 ms, annulé en sortant, puis joue CE son",
          o["lsHover"] == "1" and o["timerMs"] == 350 and o["annule"] is False and o["joue"] == ["/api/audio/porte.mp3"],
          f"{o['lsHover']} {o['timerMs']} {o['annule']} {o['joue']}")
    check("U18 tiroir du Montage : bouton Fermer présent, pas de classe inline", o["close"] == 1 and o["inlineCls"] == "svx-drawer", f"{o['close']} {o['inlineCls']}")

print("\n[inline] le mode Bibliothèque")
i = node(HARNAIS + BLOC + INLINE, "inline.js")
check("I1 inline : rendu même sans `open`, classe svx-inline, ni « Fermer » ni raccourci B",
      i.get("cls") == "svx-drawer svx-inline" and i.get("close") == 0 and i.get("hintB") is False, str(i))
check("I2 hors inline, fermé : rien", i.get("ferme") is True, str(i))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
