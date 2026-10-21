# -*- coding: utf-8 -*-
"""Son & VFX › Voix off, page repensée (t273, 21/10/2026) — `DzSvVoix`, posée par le maillon de queue `dzsonvfx`
depuis sa source frontend/patches/sonvfx-voix.js. Le hub la rend sur le sous-onglet « voiceover » et masque la vue
d'origine : l'encart de post-traitement (`postCard`) ne fait plus partie de la vue Voix.
Sections :
  [S] source et livré : source APLATIE à l'octet, règles d'écriture, routes, hooks par alias, aucun texte en dur,
      aucune trace du post-traitement, aucun arrondi ;
  [H] le hub : la Voix off rend la page, la vue d'origine reste montée mais masquée ;
  [P] sous node, la VRAIE fonction du livré, un mini-moteur de hooks et un faux serveur : bibliothèque (filtres,
      recherche, favoris gardés, écoute), balises repliables insérées au curseur, compteur, coût affiché avant,
      réglages par modèle, génération armée puis envoyée, versions et retouches (graphe, ducking, améliorer,
      isoler armé), clonage armé, Voicebox (un clic, gratuit), erreurs du serveur ;
  [K] textes FR / EN de la page.
Run (depuis backend/) : & $PY tests/test_sonvfx_voix.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
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
        print(f"  FAIL  {label} {str(detail)[:700]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
SRC_P = RACINE / "frontend" / "patches" / "sonvfx-voix.js"
SRC = SRC_P.read_bytes().decode("utf-8")
_i, _j = BUNDLE.find("/*__dzsvatelier*/"), BUNDLE.find("/*__dzsvvoix*/")
PAGE = BUNDLE[_i + len("/*__dzsvatelier*/"):_j] if 0 <= _i < _j else ""
_h0, _h1 = BUNDLE.find("var __dzSvHue="), BUNDLE.find("/*__dzsonvfx*/")
HUB = BUNDLE[_h0:_h1] if 0 <= _h0 < _h1 else ""

# ── [S] source et livré ───────────────────────────────────────────────────────────────────────────────────────────
print("[S] source et livré")
import patch_bundle_dzsonvfx as PS  # noqa: E402
check("S1 le livré porte la source aplatie, à l'octet", PAGE and PAGE == PS.aplatir(SRC), (len(PAGE), len(PS.aplatir(SRC))))
check("S2 la page est posée une fois, après l'Atelier et avant `const Te=`",
      BUNDLE.count("function DzSvVoix(") == 1 and 0 < _i < _j < BUNDLE.find('const Te="/api";'))
_lignes, _dans = [], False
for _l in (l.strip() for l in SRC.splitlines()):
    if _dans or _l.startswith("/*"):
        _dans = not _l.endswith("*/")
        continue
    _lignes.append(_l)
check("S3 règles d'écriture : ni « // », ni ligne qui commence par ( ou [",
      not any(l.startswith(("//", "(", "[")) for l in _lignes))
check("S4 aucun texte en dur : libellés par dzT, aucun aria-label/placeholder/title littéral",
      not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', PAGE) and not re.search(r'"aria-label":"|placeholder:"|title:"', PAGE))
check("S5 clés dzT littérales seulement (aucune clé construite)", not re.search(r'dzT\("[a-z0-9_.]+"\s*\+', PAGE))
_ROUTES = ('"/api/voices"', '"/api/voice-tags"', '"/api/voice-models"', '"/api/audio"', '"/api/audio/meta"',
           '"/api/cost/estimate"', '"/api/audio/voiceover"', '"/api/audio/graph/rendre"', '"/api/audio/duck"',
           '"/api/audio/enhance"', '"/api/audio/isolate"', '"/api/voices/clone"')
check("S6 routes : voix, balises, modèles, Bibliothèque, devis, synthèse, graphe, ducking, améliorer, isoler, cloner",
      all(u in PAGE for u in _ROUTES), [u for u in _ROUTES if u not in PAGE])
_rt = (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8") + \
      (RACINE / "backend" / "app" / "api" / "audio_graph_routes.py").read_text(encoding="utf-8")
check("S7 chaque route POST appelée existe côté serveur",
      all(('@router.post("%s")' % u.strip('"').replace("/api", "", 1)) in _rt or u.endswith('/graph/rendre"')
          and '@router.post("/rendre")' in _rt for u in _ROUTES[5:]))
check("S8 hooks par alias dans la fonction (x.useState( absent de la page)",
      "var US=x.useState,UE=x.useEffect,UR=x.useRef;" in PAGE and "x.useState(" not in PAGE)
check("S9 aucune trace du post-traitement dans la page (postCard, presets VFX, textes son.post)",
      "postCard" not in PAGE and "svm-vfx" not in PAGE and "son.post" not in PAGE and "SVM_VFX" not in PAGE)
check("S10 aucun arrondi : la page ne pose aucun border-radius (règle unique du hub)",
      "border-radius" not in PAGE and "borderRadius" not in PAGE and "border-radius" not in PS.CSS_VOIX)
check("S11 le script est un champ IA posé à la main (data-dz-ia) et borné par le modèle (maxLength)",
      '"data-dz-ia":"voix"' in PAGE and "maxLength:maxc" in PAGE)

# ── [H] le hub ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[H] le hub")
# t274 : les Particules s'ajoutent au même style (voix||parti)
check("H1 la Voix off rend DzSvVoix (go transmis), la vue d'origine masquée par le même style que Pistes/Atelier",
      'voix=sub==="voiceover"' in HUB and re.search(r'style:pistes\|\|atelier\|\|voix(\|\|\w+)*\?\{display:"none"\}:void 0', HUB)
      and 'voix?r.jsx(DzSvVoix,{go:p.go},"voix"):null' in HUB)
check("H2 la feuille de la page est injectée avec celle du hub", ".dzsvv{" in HUB and ".dzsvv-onde{" in HUB)

# ── [P] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("/*__dzsvatelier*/"),j=S.indexOf("/*__dzsvvoix*/");if(i<0||j<i)throw new Error("page introuvable");
const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[];
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p[q]))EFF.push(f);H[k]=d||[]},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const r={jsx:(t,p)=>({t,p}),jsxs:(t,p)=>({t,p}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
function dzSvpJson(res){return res.json().catch(()=>({})).then(d=>{if(!res.ok){const m=d&&d.detail;throw new Error((typeof m==="string"&&m)||("code "+res.status))}return d})}
function dzSvpDuree(s){s=Math.max(0,Math.round(Number(s)||0));const m=Math.floor(s/60),r2=s-m*60;return m+":"+(r2<10?"0":"")+r2}
let VERS_ATELIER=[];function dzSvpVersAtelier(f){VERS_ATELIER.push(f)}
const STOCK={};const localStorage={getItem:k=>k in STOCK?STOCK[k]:null,setItem:(k,v)=>{STOCK[k]=String(v)}};
const window={};
let AUDIOS=[];class Audio{constructor(u){this.src=u;this.joue=0;AUDIOS.push(this)}play(){this.joue++;return Promise.resolve()}pause(){this.joue=0}}
let APPELS=[],VOICES={},TAGS={},MODELS={},AUDIO=[],META={},REP={},NV=0;
function json(d,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(d)})}
function fetch(u,o){o=o||{};const corps=o.body?JSON.parse(o.body):null;APPELS.push([u,o.method||"GET",corps]);
 if(u==="/api/voices")return json(VOICES);
 if(u==="/api/voice-tags")return json(TAGS);
 if(u==="/api/voice-models")return json(MODELS);
 if(u==="/api/audio")return json({audio:AUDIO.slice()});
 if(u==="/api/audio/meta")return json({meta:Object.assign({},META)});
 if(u==="/api/cost/estimate")return json({total_usd:corps.kind==="isolate"?0.0484:corps.chars*0.00024,breakdown:[]});
 if(REP[u])return json(REP[u].d,REP[u].st);
 if(u==="/api/audio/voiceover"){NV++;return json({ok:true,filename:"sonvfx_voix-"+NV+".mp3",url:"/api/audio/sonvfx_voix-"+NV+".mp3",notes:[]})}
 if(u==="/api/audio/graph/rendre")return json({ok:true,filename:"atelier_"+corps.nom+".mp3",url:"/api/audio/atelier_"+corps.nom+".mp3",dur:9.5});
 if(u==="/api/audio/duck")return json({filename:"mix_voix.mp3",url:"/api/audio/mix_voix.mp3",dur:12});
 if(u==="/api/audio/enhance")return json({filename:"clean_voix.mp3",url:"/api/audio/clean_voix.mp3"});
 if(u==="/api/audio/isolate")return json({filename:"iso_voix.mp3",url:"/api/audio/iso_voix.mp3"});
 if(u==="/api/voices/clone"){VOICES.voices.push({voice_id:"vx_new",name:corps.nom,category:"cloned",labels:{}});return json({voice_id:"vx_new",voice_name:corps.nom,requires_verification:true})}
 return json({},404)}
eval(CODE);
let ALLER=[];const LECTEUR={currentTime:0,joue:0,play(){this.joue++;return Promise.resolve()},pause(){this.joue=0}};
const CHAMP={selectionStart:null,selectionEnd:null};
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null||n===false)return "";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join("");if(n.t==="glyph")return "";return n.p?texte(n.p.children):""}
let A=null;
function rendre(){HI=0;EFF=[];A=DzSvVoix({go:v=>ALLER.push(v)});
 tout(A,n=>n.p&&n.p.ref,[]).forEach(n=>{n.p.ref.current=n.t==="audio"?LECTEUR:CHAMP});
 const e=EFF;EFF=[];e.forEach(f=>f());return A}
async function calme(){for(let k=0;k<8;k++){await new Promise(r0=>setImmediate(r0));rendre()}}
function un(f){return tout(A,f,[])[0]}
function btn(a){return un(n=>n.t==="button"&&n.p["data-sv-voix"]===a)}
function cls(c){return n=>n.p&&typeof n.p.className==="string"&&n.p.className.split(" ").indexOf(c)>=0}
function etat(){const zone=un(cls("dzsvv"));
 return {zones:zone?tout(zone.p.children,n=>n.p&&/^dzsvv-(biblio|centre|reglages)$/.test(n.p.className),[]).map(n=>n.p.className):[],
  voix:tout(A,cls("dzsvv-voix"),[]).map(n=>[n.p["data-voix"],n.p["data-sel"]==="",texte(un(m=>m===n)&&tout(n,cls("dzsvv-vn"),[])[0])]),
  filtres:tout(A,n=>n.t==="select"&&n.p["data-filtre"],[]).map(n=>[n.p["data-filtre"],tout(n,m=>m.t==="option",[]).map(o=>o.p.value)]),
  groupes:tout(A,cls("dzsvv-groupe"),[]).map(n=>[n.p["data-groupe"],tout(n,cls("dzsvv-gtete"),[])[0].p["aria-expanded"],tout(n,cls("dzsvv-puce"),[]).length]),
  horsV3:!!btn("hors-v3")||!!un(n=>n.p&&n.p["data-sv-voix"]==="hors-v3"),
  texte:(un(cls("dzsvv-texte"))||{p:{}}).p.value,maxlen:(un(cls("dzsvv-texte"))||{p:{}}).p.maxLength,
  compteur:texte(un(n=>n.p&&n.p["data-sv-voix"]==="compteur")),cout:texte(un(n=>n.p&&n.p["data-sv-voix"]==="cout")),
  generer:btn("generer")?texte(btn("generer").p.children).trim():null,arme:btn("generer")?btn("generer").p["data-arme"]==="":null,
  regles:tout(A,n=>n.p&&n.p["data-regle"],[]).map(n=>n.p["data-regle"]),
  segs:tout(A,cls("dzsvv-seg"),[]).map(n=>[n.p["data-stab"],n.p["aria-pressed"]]),
  modele:(un(n=>n.t==="select"&&n.p["data-sv-voix"]==="modele")||{p:{}}).p.value,modeles:tout(A,n=>n.t==="select"&&n.p["data-sv-voix"]==="modele",[]).flatMap(s=>tout(s,n=>n.t==="option",[]).map(o=>o.p.value)),
  cle:!!un(cls("dzsvv-cle")),
  versions:tout(A,cls("dzsvv-version"),[]).map(n=>[n.p["data-version"],n.p["aria-pressed"]]),
  cur:texte(un(cls("dzsvv-curn"))),lecteur:(un(n=>n.t==="audio")||{p:{}}).p.src||null,
  outils:tout(A,cls("dzsvv-outil"),[]).map(n=>n.p["data-outil"]),
  iso:btn("outil-isole")?[texte(btn("outil-isole").p.children),btn("outil-isole").p["data-arme"]===""]:null,
  cloner:btn("cloner")?[texte(btn("cloner").p.children),btn("cloner").p.disabled,btn("cloner").p["data-arme"]===""]:null,
  note:texte(un(cls("dzsvv-note"))),aides:tout(A,cls("dzsvv-aide"),[]).map(texte),
  postcard:tout(A,n=>n.p&&typeof n.p.className==="string"&&/svm-vfx|svm-card/.test(n.p.className),[]).length,
  barres:tout(A,cls("dzsvv-barre"),[]).length,
  appels:APPELS.slice()}}
function voixBtn(id,k){const L=un(n=>cls("dzsvv-voix")(n)&&n.p["data-voix"]===id);return k==="nom"?L.p.children[0]:tout(L,n=>n.t==="button"&&n.p["data-sv-voix"]===k,[])[0]}
function regler(sel,v){const n=un(sel);n.p.onChange({target:{value:v,checked:v}});rendre()}
function appels(u){return APPELS.filter(c=>c[0]===u)}
(async()=>{const R={};
 VOICES={enabled:true,provider:"elevenlabs",voices:[
  {voice_id:"a1",name:"Adam",category:"premade",labels:{gender:"male",age:"middle_aged",accent:"american",use_case:"narration"},language:"en",preview_url:"/p/a1.mp3"},
  {voice_id:"c1",name:"Prophète",category:"cloned",labels:{gender:"male",age:"old",use_case:"narration"},language:"fr",preview_url:null},
  {voice_id:"s1",name:"Sarah",category:"premade",labels:{gender:"female",age:"young",use_case:"social_media"},language:"en",preview_url:"/p/s1.mp3"}]};
 TAGS={groups:{emotion:["[excited]","[curious]"],voix:["[whispers]"],sons:["[applause]"],special:["[sings]"]},experimental:["[sings]"],max_tags:4,providers:{elevenlabs:true,voicebox:false}};
 MODELS={default:"eleven_multilingual_v2",models:[
  {id:"eleven_multilingual_v2",label:"Multilingual v2",max_chars:10000,settings:["stability","similarity_boost","style","speed"],available:true},
  {id:"eleven_v3",label:"Eleven v3",max_chars:5000,settings:["stability"],available:true}]};
 AUDIO=[{name:"prise_voix.mp3",url:"/api/audio/prise_voix.mp3"},{name:"musique_a.mp3",url:"/api/audio/musique_a.mp3"},{name:"stem_a_vocals.mp3",url:"/api/audio/stem_a_vocals.mp3"}];
 META={"prise_voix.mp3":{kind:"voix"},"musique_a.mp3":{kind:"musique"},"stem_a_vocals.mp3":{kind:"stem"}};
 rendre();R.charge0=etat();await calme();R.charge=etat();
 regler(n=>n.t==="select"&&n.p["data-filtre"]==="genre","female");R.f_genre=etat();
 regler(n=>n.t==="select"&&n.p["data-filtre"]==="genre","");
 regler(n=>n.t==="select"&&n.p["data-filtre"]==="langue","fr");R.f_langue=etat();
 regler(n=>n.t==="select"&&n.p["data-filtre"]==="langue","");
 regler(n=>n.t==="input"&&n.p["data-sv-voix"]==="chercher","SAR");R.recherche=etat();
 regler(n=>n.t==="input"&&n.p["data-sv-voix"]==="chercher","");
 voixBtn("a1","favori").p.onClick();rendre();R.fav_stock=STOCK.dz_sv_voix_favoris;
 btn("seul-fav").p.onClick();rendre();R.seul_fav=etat();btn("seul-fav").p.onClick();rendre();
 voixBtn("a1","ecouter").p.onClick();rendre();R.ecoute={src:AUDIOS.length?AUDIOS[AUDIOS.length-1].src:null,joue:AUDIOS.length?AUDIOS[AUDIOS.length-1].joue:0,
  pressed:voixBtn("a1","ecouter").p["aria-pressed"]};
 voixBtn("c1","ecouter").p.onClick();rendre();R.ecoute_sans=etat();
 voixBtn("s1","nom").p.onClick();rendre();R.choix=etat();
 APPELS=[];regler(cls("dzsvv-texte"),"Bonjour le monde");await calme();R.texte=etat();
 tout(A,cls("dzsvv-gtete"),[])[0].p.onClick();rendre();R.ouvert=etat();
 CHAMP.selectionStart=8;CHAMP.selectionEnd=8;tout(A,n=>cls("dzsvv-puce")(n)&&n.p["data-balise"]==="[excited]",[])[0].p.onClick();await calme();R.balise=etat();
 R.regles_v2=etat().regles;
 regler(n=>n.t==="select"&&n.p["data-sv-voix"]==="modele","eleven_v3");await calme();R.v3=etat();
 tout(A,n=>cls("dzsvv-seg")(n)&&n.p["data-stab"]==="1",[])[0].p.onClick();rendre();R.stab1=etat().segs;
 APPELS=[];btn("generer").p.onClick();await calme();R.arme=etat();
 btn("generer").p.onClick();await calme();R.genere=etat();
 btn("generer").p.onClick();await calme();regler(cls("dzsvv-texte"),"Bonjour [excited] le monde !");await calme();R.desarme=etat();
 btn("generer").p.onClick();await calme();btn("annuler").p.onClick();rendre();R.annule=etat();
 regler(n=>n.t==="select"&&n.p["data-sv-voix"]==="langue","en");APPELS=[];btn("generer").p.onClick();await calme();btn("generer").p.onClick();await calme();R.genere_en=etat();
 un(n=>n.t==="audio").p.onLoadedMetadata({target:{duration:12}});rendre();R.meta=etat();
 APPELS=[];regler(n=>n.t==="input"&&n.p["data-out"]==="debut","1");regler(n=>n.t==="input"&&n.p["data-out"]==="fin","4");
 btn("outil-coupe").p.onClick();await calme();R.coupe=etat();
 btn("outil-fondu").p.onClick();await calme();R.fondu=etat();
 btn("outil-normalise").p.onClick();await calme();btn("outil-deess").p.onClick();await calme();R.normdeess=etat();
 APPELS=[];btn("outil-ducking").p.onClick();await calme();R.duck_sans=etat();
 regler(n=>n.t==="select"&&n.p["data-out"]==="musique","musique_a.mp3");btn("outil-ducking").p.onClick();await calme();R.duck=etat();
 btn("outil-ameliore").p.onClick();await calme();R.ameliore=etat();
 un(n=>n.t==="audio").p.onLoadedMetadata({target:{duration:12}});rendre();APPELS=[];btn("outil-isole").p.onClick();await calme();R.iso_arme=etat();btn("outil-isole").p.onClick();await calme();R.iso=etat();
 const premiere=tout(A,cls("dzsvv-version"),[])[0];premiere.p.onClick();rendre();R.v_premiere=etat();
 un(n=>n.t==="audio").p.onLoadedMetadata({target:{duration:12}});rendre();un(n=>n.p&&n.p["data-sv-voix"]==="onde").p.onClick({currentTarget:{getBoundingClientRect:()=>({left:0,width:200})},clientX:50});rendre();R.seek=LECTEUR.currentTime;
 btn("lire").p.onClick();rendre();R.lire=LECTEUR.joue;
 btn("montage").p.onClick();btn("atelier").p.onClick();R.aller=[ALLER.slice(),VERS_ATELIER.slice(),LECTEUR.joue];
 btn("cloner-ouvrir").p.onClick();rendre();R.clone0=etat();
 regler(n=>n.t==="input"&&n.p["data-sv-voix"]==="clone-nom","Ma voix");
 R.prises=tout(A,cls("dzsvv-prise"),[]).map(n=>n.p["data-prise"]);
 tout(A,cls("dzsvv-prise"),[])[0].p.onClick();rendre();
 regler(n=>n.t==="input"&&n.p["data-sv-voix"]==="clone-droit",true);R.clone1=etat();
 APPELS=[];btn("cloner").p.onClick();await calme();R.clone_arme=etat();btn("cloner").p.onClick();await calme();R.clone=etat();
 REP["/api/audio/voiceover"]={st:503,d:{detail:"Aucune voix disponible — configure la clé ElevenLabs ou lance Voicebox (Réglages)."}};
 btn("generer").p.onClick();await calme();btn("generer").p.onClick();await calme();R.refus=etat();delete REP["/api/audio/voiceover"];
 R.memo=window.__dzSvVoix?{n:window.__dzSvVoix.versions.length,cur:window.__dzSvVoix.cur,texte:window.__dzSvVoix.texte}:null;
 H=[];rendre();await calme();R.retour=etat();
 TAGS={groups:{},providers:{elevenlabs:false,voicebox:true}};VOICES={enabled:true,provider:"voicebox",voices:[{voice_id:"vb1",name:"Profil local",labels:{}}]};
 H=[];APPELS=[];rendre();await calme();R.vbox=etat();btn("generer").p.onClick();await calme();R.vbox_gen=etat();
 VOICES={enabled:false,voices:[]};MODELS.models.forEach(m=>m.available=false);TAGS={groups:TAGS.groups,providers:{elevenlabs:false,voicebox:false}};
 try{delete window.__dzSvVoix}catch(e){};H=[];APPELS=[];rendre();await calme();R.sans_cle=etat();
 process.stdout.write(JSON.stringify(R));})().catch(e=>process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)})));
"""


def _node():
    with tempfile.TemporaryDirectory() as dd:
        h = pathlib.Path(dd) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"erreur": (p.stdout + p.stderr)[:900]}


print("[P] sous node (vraie fonction du livré)")
R = _node() if PAGE else {"erreur": "page absente du livré"}
check("P0 harnais exécuté", "charge" in R, R.get("erreur", R))
c = R.get("charge", {})
check("P1 trois zones (bibliothèque, centre, réglages), aucun encart de post-traitement",
      c.get("zones") == ["dzsvv-biblio", "dzsvv-centre", "dzsvv-reglages"] and c.get("postcard") == 0, c)
check("P2 au chargement : « chargement », puis les voix, la clonée d'abord et choisie",
      "⟦sonvfx.voix.chargement⟧" in R.get("charge0", {}).get("aides", [])
      and [v[0] for v in c.get("voix", [])] == ["c1", "a1", "s1"] and c.get("voix", [[0, 0]])[0][1] is True, c.get("voix"))
check("P3 filtres langue / genre / âge / style tirés des étiquettes des voix",
      c.get("filtres") == [["langue", ["", "en", "fr"]], ["genre", ["", "female", "male"]],
                           ["age", ["", "middle_aged", "old", "young"]], ["style", ["", "narration", "social_media"]]],
      c.get("filtres"))
check("P4 filtre genre « femme » : Sarah seule ; langue « fr » : Prophète seul",
      [v[0] for v in R.get("f_genre", {}).get("voix", [])] == ["s1"]
      and [v[0] for v in R.get("f_langue", {}).get("voix", [])] == ["c1"], [R.get("f_genre", {}).get("voix"), R.get("f_langue", {}).get("voix")])
check("P5 recherche sans casse", [v[0] for v in R.get("recherche", {}).get("voix", [])] == ["s1"], R.get("recherche", {}).get("voix"))
check("P6 favori gardé dans ce navigateur, filtre « favoris seulement »",
      R.get("fav_stock") == '["a1"]' and [v[0] for v in R.get("seul_fav", {}).get("voix", [])] == ["a1"],
      [R.get("fav_stock"), R.get("seul_fav", {}).get("voix")])
check("P7 écouter : l'aperçu de la voix joue, le bouton est pressé",
      R.get("ecoute") == {"src": "/p/a1.mp3", "joue": 1, "pressed": "true"}, R.get("ecoute"))
check("P8 voix sans aperçu : la note le dit, rien ne joue",
      R.get("ecoute_sans", {}).get("note") == '⟦sonvfx.voix.apercu_absent⟧{"nom":"Prophète"}', R.get("ecoute_sans", {}).get("note"))
check("P9 choisir une voix", [v[0] for v in R.get("choix", {}).get("voix", []) if v[1]] == ["s1"], R.get("choix", {}).get("voix"))
c = R.get("texte", {})
check("P10 compteur borné par le modèle (Multilingual v2 : 10 000), coût relu au serveur et affiché AVANT",
      c.get("compteur") == '⟦sonvfx.voix.compteur⟧{"n":16,"max":10000}' and c.get("maxlen") == 10000
      and ["/api/cost/estimate", "POST", {"kind": "elevenlabs", "chars": 16, "model": "eleven_multilingual_v2"}] in c.get("appels", [])
      and c.get("cout") == '⟦sonvfx.voix.cout⟧{"prix":"~$0.0038"}'
      and not any(a[0] == "/api/audio/voiceover" for a in c.get("appels", [])), c)
check("P11 balises : quatre groupes repliés ; un clic déplie le premier (ses puces)",
      c.get("groupes") == [["emotion", "false", 0], ["voix", "false", 0], ["sons", "false", 0], ["special", "false", 0]]
      and R.get("ouvert", {}).get("groupes", [[0, 0, 0]])[0] == ["emotion", "true", 2], [c.get("groupes"), R.get("ouvert", {}).get("groupes")])
check("P12 hors Eleven v3, la palette dit que seules v3 lit les balises", c.get("horsV3") is True, c)
check("P13 une balise s'insère AU CURSEUR, suivie d'une espace",
      R.get("balise", {}).get("texte") == "Bonjour [excited] le monde", R.get("balise", {}).get("texte"))
check("P14 Multilingual v2 : stabilité, similarité, vitesse", R.get("regles_v2") == ["stability", "similarity_boost", "speed"],
      R.get("regles_v2"))
c = R.get("v3", {})
check("P15 Eleven v3 : stabilité en trois valeurs (0 / 0,5 / 1), aucun autre curseur, compteur à 5 000, note",
      c.get("regles") == ["stability"] and c.get("segs") == [["0", "false"], ["0.5", "true"], ["1", "false"]]
      and c.get("compteur", "").endswith('"max":5000}') and not c.get("horsV3")
      and "⟦sonvfx.voix.v3_reglages⟧" in c.get("aides", []), c)
check("P16 stabilité « Robuste » choisie", R.get("stab1") == [["0", "false"], ["0.5", "false"], ["1", "true"]], R.get("stab1"))
c = R.get("arme", {})
check("P17 premier clic : devis du serveur, AUCUNE synthèse, bouton armé « Confirmer »",
      c.get("appels") == [["/api/cost/estimate", "POST", {"kind": "elevenlabs", "chars": 26, "model": "eleven_v3"}]]
      and c.get("arme") and c.get("generer") == '⟦sonvfx.voix.confirmer⟧{"prix":"~$0.0062"}', c)
c = R.get("genere", {})
_vo = [a[2] for a in c.get("appels", []) if a[0] == "/api/audio/voiceover"]
check("P18 second clic : UNE synthèse avec le texte, la langue, la voix, le modèle et SES seuls réglages",
      _vo == [{"script": "Bonjour [excited] le monde", "language": "fr", "name": "sonvfx_voix", "model": "eleven_v3",
               "voice_id": "s1", "settings": {"stability": 1}}], _vo)
check("P19 la voix générée devient la version 1, choisie, écoutable ; la note le dit",
      c.get("versions") == [["sonvfx_voix-1.mp3", "true"]] and c.get("lecteur") == "/api/audio/sonvfx_voix-1.mp3"
      and c.get("note") == '⟦sonvfx.voix.generee⟧{"nom":"sonvfx_voix-1.mp3"}' and not c.get("arme"), c)
check("P20 changer le texte désarme", not R.get("desarme", {}).get("arme"), R.get("desarme", {}).get("generer"))
check("P21 armer puis Annuler : rien ne part",
      not R.get("annule", {}).get("arme") and len([a for a in R.get("annule", {}).get("appels", []) if a[0] == "/api/audio/voiceover"]) == 1,
      R.get("annule", {}).get("generer"))
_vo = [a[2] for a in R.get("genere_en", {}).get("appels", []) if a[0] == "/api/audio/voiceover"]
check("P22 langue anglaise : la synthèse part en « en »", len(_vo) == 1 and _vo[0]["language"] == "en", _vo)
check("P23 sept retouches sous le résultat", R.get("meta", {}).get("outils") == ["coupe", "fondu", "normalise", "deess", "ducking", "ameliore", "isole"],
      R.get("meta", {}).get("outils"))


def _graphe(appels):
    return [a[2] for a in appels if a[0] == "/api/audio/graph/rendre"]


_SRC = lambda f: {"id": "src", "type": "source", "params": {"fichier": f}}   # noqa: E731
_LIENS = [{"de": "src", "vers": "fx", "entree": 0}, {"de": "fx", "vers": "out", "entree": 0}]
_OUT = {"id": "out", "type": "sortie", "params": {}}
c = R.get("coupe", {})
check("P24 couper : un graphe source → plage (début, fin) → sortie, sur la version écoutée ; version neuve choisie",
      _graphe(c.get("appels", [])) == [{"graphe": {"noeuds": [_SRC("sonvfx_voix-2.mp3"), {"id": "fx", "type": "plage", "params": {"debut": 1, "fin": 4}}, _OUT],
                                                   "liens": _LIENS}, "nom": "voix_coupe"}]
      and c.get("versions", [])[-1] == ["atelier_voix_coupe.mp3", "true"], [_graphe(c.get("appels", [])), c.get("versions")])
c = R.get("fondu", {})
check("P25 fondu : plage entière (fin = durée de la version), fondus d'entrée et de sortie",
      (_graphe(c.get("appels", [])) or [{}])[-1].get("graphe", {}).get("noeuds", [{}, {}])[1]
      == {"id": "fx", "type": "plage", "params": {"debut": 0, "fin": 9.5, "fondu_entree": 0.5, "fondu_sortie": 1}},
      _graphe(c.get("appels", []))[-1:])
c = R.get("normdeess", {})
_n = [g["graphe"]["noeuds"][1] for g in _graphe(c.get("appels", []))[-2:]]
check("P26 normaliser (−16 LUFS) puis de-ess (50) : des effets du moteur, chacun sur la version d'avant",
      _n == [{"id": "fx", "type": "effet", "params": {"fx": "normalize", "target_lufs": -16}},
             {"id": "fx", "type": "effet", "params": {"fx": "deesser", "intensity": 50}}]
      and _graphe(c.get("appels", []))[-1]["graphe"]["noeuds"][0]["params"]["fichier"] == "atelier_voix_normalisee.mp3", _n)
c = R.get("duck_sans", {})
check("P27 ducking sans musique : la note le demande, rien ne part",
      c.get("note") == "⟦sonvfx.voix.musique_choisir⟧" and not any(a[0] == "/api/audio/duck" for a in c.get("appels", [])), c.get("note"))
c = R.get("duck", {})
check("P28 ducking : la voix et la musique choisie (Bibliothèque, kind musique) partent au mix ducké",
      [a[2] for a in c.get("appels", []) if a[0] == "/api/audio/duck"] == [{"voice": "atelier_voix_deess.mp3", "music": "musique_a.mp3", "music_db": -14}],
      [a for a in c.get("appels", []) if a[0] == "/api/audio/duck"])
c = R.get("ameliore", {})
check("P29 améliorer : la version écoutée part, la version « améliorée » arrive",
      [a[2] for a in c.get("appels", []) if a[0] == "/api/audio/enhance"] == [{"filename": "mix_voix.mp3"}]
      and c.get("versions", [])[-1] == ["clean_voix.mp3", "true"], c.get("versions"))
c = R.get("iso_arme", {})
check("P30 isoler (payant) : premier clic = devis à la durée, AUCUN envoi, bouton armé",
      c.get("appels") == [["/api/cost/estimate", "POST", {"kind": "isolate", "duration_s": 12}]]
      and c.get("iso") == ['⟦sonvfx.voix.confirmer⟧{"prix":"~$0.0484"}', True], c)
c = R.get("iso", {})
check("P31 second clic : l'isolation part, la version « isolée » arrive",
      [a[2] for a in c.get("appels", []) if a[0] == "/api/audio/isolate"] == [{"filename": "clean_voix.mp3"}]
      and c.get("versions", [])[-1] == ["iso_voix.mp3", "true"] and c.get("iso") == ["⟦sonvfx.voix.appliquer⟧", False], c)
c = R.get("v_premiere", {})
check("P32 versions : revenir à la première la remet à l'écoute",
      c.get("lecteur") == "/api/audio/sonvfx_voix-1.mp3" and c.get("versions", [[0, 0]])[0][1] == "true"
      and len(c.get("versions", [])) == 9, c.get("versions"))
check("P33 forme d'onde : un clic place la tête de lecture ; « Lire » joue",
      R.get("seek") == 3 and R.get("lire") == 1, [R.get("seek"), R.get("lire")])
check("P34 « Envoyer au Montage » et « Ouvrir dans l'Atelier » (la version écoutée)",
      R.get("aller") == [["montage"], ["sonvfx_voix-1.mp3"], 0], R.get("aller"))
c = R.get("clone0", {})
check("P35 « Cloner une voix » ouvre le panneau ; bouton inactif tant que nom, prise et droit manquent",
      c.get("cloner") == ["⟦sonvfx.voix.cloner⟧", True, False], c.get("cloner"))
check("P36 les prises proposées : les voix de la Bibliothèque, sans musique ni piste séparée",
      R.get("prises") == ["prise_voix.mp3"], R.get("prises"))
check("P37 nom + prise + droit : bouton actif", R.get("clone1", {}).get("cloner") == ["⟦sonvfx.voix.cloner⟧", False, False],
      R.get("clone1", {}).get("cloner"))
c = R.get("clone_arme", {})
check("P38 premier clic : armé, rien ne part", c.get("cloner") == ["⟦sonvfx.voix.clone_confirmer⟧", False, True]
      and not any(a[0] == "/api/voices/clone" for a in c.get("appels", [])), c.get("cloner"))
c = R.get("clone", {})
check("P39 second clic : le clonage part (nom, prise, droit attesté), la liste relue, la voix neuve choisie",
      [a[2] for a in c.get("appels", []) if a[0] == "/api/voices/clone"] == [{"nom": "Ma voix", "fichiers": ["prise_voix.mp3"], "description": "", "droit": True}]
      and [v[0] for v in c.get("voix", []) if v[1]] == ["vx_new"]
      and c.get("note") == '⟦sonvfx.voix.clone_fait⟧{"nom":"Ma voix"} ⟦sonvfx.voix.clone_verif⟧' and c.get("cloner") is None, c)
c = R.get("refus", {})
check("P40 refus du serveur (503 sans clé) : son message tel quel, bouton rendu",
      c.get("note") == "Aucune voix disponible — configure la clé ElevenLabs ou lance Voicebox (Réglages)."
      and c.get("generer") == "⟦sonvfx.voix.generer⟧", c)
check("P41 la page démontée puis remontée garde voix, texte, versions et la version écoutée",
      R.get("memo", {}).get("n") == 9 and R.get("retour", {}).get("texte") == "Bonjour [excited] le monde !"
      and len(R.get("retour", {}).get("versions", [])) == 9 and R.get("retour", {}).get("lecteur") == "/api/audio/sonvfx_voix-1.mp3"
      and [v[0] for v in R.get("retour", {}).get("voix", []) if v[1]] == ["vx_new"], [R.get("memo"), R.get("retour", {}).get("versions")])
c = R.get("vbox", {})
check("P42 Voicebox : pas de palette (la note le dit), gratuit, aucun devis demandé, modèle fixe",
      "⟦sonvfx.voix.vbox_balises⟧" in c.get("aides", []) and c.get("cout") == "⟦sonvfx.voix.gratuit_vbox⟧"
      and not any(a[0] == "/api/cost/estimate" for a in c.get("appels", [])) and c.get("regles") == [], c)
c = R.get("vbox_gen", {})
_vo = [a[2] for a in c.get("appels", []) if a[0] == "/api/audio/voiceover"]
check("P43 Voicebox : UN clic synthétise, sans modèle ni réglages",
      len(_vo) == 1 and "model" not in _vo[0] and "settings" not in _vo[0] and _vo[0]["voice_id"] == "vb1"
      and not any(a[0] == "/api/cost/estimate" for a in c.get("appels", [])), _vo)
c = R.get("sans_cle", {})
check("P44 sans clé : aucune voix (la note le dit), modèles CHOISISSABLES avec la mention de clé, bouton actif",
      "⟦sonvfx.voix.sans_voix⟧" in c.get("aides", []) and c.get("modeles") == ["eleven_multilingual_v2", "eleven_v3"]
      and c.get("cle") and c.get("generer") == "⟦sonvfx.voix.generer⟧", c)
check("P45 sans version : le résultat invite à générer", "⟦sonvfx.voix.resultat_vide⟧" in c.get("aides", []), c.get("aides"))

# ── [K] textes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "sonvfx_hub.json").read_text(encoding="utf-8"))
CLES = sorted(set(re.findall(r'dzT\("(sonvfx\.voix\.[a-z0-9_]+)"', PAGE)))
check("K1 chaque clé de la page : FR et EN, mêmes variables, trois segments",
      CLES and all((DICO.get(k) or {}).get("fr") and (DICO.get(k) or {}).get("en") and len(k.split(".")) == 3
                   and set(re.findall(r"\{(\w+)\}", DICO[k]["fr"])) == set(re.findall(r"\{(\w+)\}", DICO[k]["en"]))
                   for k in CLES), [k for k in CLES if k not in DICO])
check("K2 aucune clé sonvfx.voix.* orpheline dans le dictionnaire",
      sorted(k for k in DICO if k.startswith("sonvfx.voix.")) == CLES,
      sorted(set(k for k in DICO if k.startswith("sonvfx.voix.")) ^ set(CLES)))
_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K3 dictionnaire assemblé (source = copie de dist)", all(k.encode() in _dico for k in CLES)
      and _dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_voix():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
