# -*- coding: utf-8 -*-
"""T102 (plan-son-vfx T6-T8) — l'écran Son & VFX, dans le bundle LIVRÉ : la moitié Son & VFX du bloc SONVFX
(tout ce qui précède « Écran 07 · Montage ») est extraite et EXÉCUTÉE sous node — moteur de hooks minimal par
composant, fetch / Audio / dialogue maison en doublures qui notent tout. Vérifié :
  · Musique : prix à la seconde (ACE-Step) ou à la génération, éditeur de paroles structurées (sections, squelette
    persona par le DIALOGUE MAISON — jamais window.prompt), paroles VISIBLES pour un modèle sans interrupteur
    instrumental (Music 2.0 : le défaut « instrumental » les cachait), refus local < 10 caractères, graine envoyée,
    `onGenerated` remonté ;
  · Voix off dirigée : palette servie par /api/voice-tags, 4 balises au plus, aperçu = ce qui part (miroir
    d'apply_style), génération PAYANTE armée par le devis du backend au 1er clic et tirée au 2e, désarmée par une
    frappe ; sous Voicebox, pas de palette et un seul clic (gratuit) ;
  · Mix : la carte paraît dès une voix ou une musique, le bouton attend les deux, POST /api/audio/duck avec le
    réglage nommé, le mix est joué.
Témoin positif : le bundle de la base (2bcc0e4c) n'a ni l'éditeur de paroles, ni la voix dirigée, ni le mix.
Run (depuis backend/) : & $PY tests/test_son_vfx_t102_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzt102_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "2bcc0e4c"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base a Son & VFX mais ni l'éditeur de paroles, ni la voix dirigée, ni le mix",
      r0.returncode == 0 and b"function DzSonVfx(" in r0.stdout and b"SvmLyricsEditor" not in r0.stdout
      and b"/api/voice-tags" not in r0.stdout and b"/api/audio/duck" not in r0.stdout)

DEB, FIN = "/*__DZ_SONVFX_BEGIN__*/", "/*__DZ_SONVFX_END__*/"
check("T1 un seul bloc SONVFX", BUN.count(DEB) == 1 and BUN.count(FIN) == 1)
BLOC = BUN.split(DEB, 1)[1].split(FIN, 1)[0].replace("\r\n", "\n")
COUPE = "/* ═════════════════════ Écran 07 · Montage"
check("T2 la moitié Son & VFX se découpe (marqueur de l'écran 07 présent une fois)", BLOC.count(COUPE) == 1)
SONVFX = BLOC.split(COUPE, 1)[0]
lyr = SONVFX.split("function SvmLyricsEditor(", 1)[1].split("\nfunction ", 1)[0] if "function SvmLyricsEditor(" in SONVFX else ""
check("T3 le squelette passe par le dialogue maison, jamais window.prompt",
      "__dzDialogue.saisir(" in lyr and "prompt(" not in lyr.replace("saisir(", ""), lyr[:200])

HARNAIS = r"""
var CALLS=[],AUDIOS=[],LS={},REP={},DIALOG=[];
var CUR=null;
function same(a,b){if(!a||!b||a.length!==b.length)return false;for(var i=0;i<a.length;i++)if(a[i]!==b[i])return false;return true}
var x={
  useState:function(v){var I=CUR,i=I.hi++;if(!(i in I.H))I.H[i]=typeof v==="function"?v():v;
    return [I.H[i],function(n){I.H[i]=typeof n==="function"?n(I.H[i]):n}]},
  useRef:function(v){var I=CUR,i=I.hi++;if(!(i in I.H))I.H[i]={current:v};return I.H[i]},
  useMemo:function(f,d){var I=CUR,i=I.hi++,o=I.H[i];if(!o||!same(o.d,d))I.H[i]={v:f(),d:d};return I.H[i].v},
  useCallback:function(f,d){return x.useMemo(function(){return f},d)},
  useEffect:function(f,d){var I=CUR,i=I.hi++,o=I.H[i];if(!o||!d||!same(o.d,d)){I.H[i]={d:d,c:o&&o.c};I.PEND.push([i,f])}},
  useLayoutEffect:function(f,d){return x.useEffect(f,d)}};
function el(t,p){return {t:t,p:p||{}}}
var r={jsx:el,jsxs:el,Fragment:"Fragment"};
var localStorage={getItem:function(k){return k in LS?LS[k]:null},setItem:function(k,v){LS[k]=String(v)},removeItem:function(k){delete LS[k]}};
var window={localStorage:localStorage,addEventListener:function(){},removeEventListener:function(){},
  matchMedia:function(){return {matches:false,addEventListener:function(){},removeEventListener:function(){}}},
  __dzDialogue:{saisir:function(m,o){DIALOG.push(m);return Promise.resolve(window.__REPONSE)}},__REPONSE:"abysses"};
var document={createElement:function(){return {setAttribute:function(){},style:{}}},body:{appendChild:function(){}},
  activeElement:null,addEventListener:function(){},removeEventListener:function(){},documentElement:{dataset:{},getAttribute:function(){return null}}};
var performance={now:function(){return 0}};
function requestAnimationFrame(){return 0}function cancelAnimationFrame(){}
function setTimeout(f,ms){return 0}function clearTimeout(){}function setInterval(){return 0}function clearInterval(){}
function Audio(u){this.url=u;this.currentTime=0;AUDIOS.push(this)}
Audio.prototype.play=function(){return Promise.resolve()};Audio.prototype.pause=function(){};
function rep(o){return Promise.resolve({ok:o.st<400,status:o.st,json:function(){return Promise.resolve(o.js)},
  arrayBuffer:function(){return Promise.resolve(new ArrayBuffer(0))}})}
function fetch(u,o){o=o||{};CALLS.push({u:u,m:o.method||"GET",b:o.body?JSON.parse(o.body):null});
  var k=(o.method||"GET")+" "+String(u).split("?")[0];
  if(REP[k])return rep(REP[k]);
  return rep({st:404,js:{detail:"inconnu "+k}})}
"""

MOTEUR = r"""
function inst(C,props){return {C:C,props:props||{},H:[],hi:0,PEND:[]}}
// les composants SANS hooks sont déroulés en place (l'éditeur de paroles, les libellés) ; ceux qui ont un état
// (SvmMusic dans DzSonVfx) restent des éléments — le banc les instancie à part
var DEROULE=[SvmLyricsEditor,SvmLabel];
function deroule(n){if(!n||typeof n!=="object")return n;if(Array.isArray(n))return n.map(deroule);
  if(DEROULE.indexOf(n.t)>=0)return deroule(n.t(n.p));
  if(n.p&&n.p.children!=null)n.p.children=deroule(n.p.children);return n}
function render(I){var prev=CUR;CUR=I;I.hi=0;I.PEND=[];var t=deroule(I.C(I.props));
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
  REP["GET /api/music-models"]={st:200,js:{enabled:true,default:"lyria3",moods:[{id:"lofi",name:"Lo-fi",prompt:"lofi"}],models:[
    {id:"lyria3",label:"Lyria 3",desc:"",duration:null,fixed_duration:30,lyrics:false,instrumental:false,seed:false,usd:0.1,usd_unit:"gen",lyrics_style:null,lyrics_required:false},
    {id:"ace-step",label:"ACE-Step (paroles)",desc:"",duration:[5,240],fixed_duration:null,lyrics:true,instrumental:true,seed:true,usd:0.0002,usd_unit:"s",lyrics_style:"ace",lyrics_required:false},
    {id:"minimax-music-20",label:"MiniMax Music 2.0",desc:"",duration:null,fixed_duration:null,lyrics:true,instrumental:false,seed:false,usd:0.03,usd_unit:"gen",lyrics_style:"minimax",lyrics_required:true}]}};
  REP["GET /api/music/lyrics-skeleton"]={st:200,js:{lyrics:"[Verse]\nDeepotus — abysses\n\n[Chorus]\nDeepotus, abysses"}};
  REP["POST /api/audio/music"]={st:200,js:{ok:true,item:{filename:"musique_x.mp3",url:"/api/audio/musique_x.mp3",name:"musique_x",dur:60},model_label:"ACE-Step",notes:[]}};

  // ── Musique ──
  var GEN=[];
  var M=inst(SvmMusic,{onNote:function(){},play:function(){},playId:"",onGenerated:function(it){GEN.push(it.filename)}});
  var t=await stable(M);
  OUT.prix=cls(t,"svm-model").map(function(b){return txt(cls(b,"svm-genprice")[0])});
  var choisir=function(id){var b=cls(t,"svm-model").filter(function(n){return txt(cls(n,"svm-genname")[0])===id})[0];b.p.onClick();t=render(M)};
  choisir("MiniMax Music 2.0");
  OUT.m20_editeur=cls(t,"svm-lyrics").length;OUT.m20_oblig=txt(t).indexOf("paroles obligatoires")>=0;
  tout(t).filter(function(n){return n.p["aria-label"]==="Description libre de la musique"})[0].p.onChange({target:{value:"hymne pirate"}});t=render(M);
  btn(t,"+ refrain").p.onClick();t=render(M);
  tout(t).filter(function(n){return n.p["aria-label"]==="Paroles de la section 1"})[0].p.onChange({target:{value:"court"}});t=render(M);
  CALLS.length=0;btn(t,"Générer la musique").p.onClick();t=render(M);await tick();t=render(M);
  OUT.m20_refus={posts:posts("/api/audio/music").length,err:txt(t).indexOf("exige des paroles")>=0};
  tout(t).filter(function(n){return n.p["aria-label"]==="Paroles de la section 1"})[0].p.onChange({target:{value:"yo ho ho et une bouteille"}});t=render(M);
  btn(t,"Générer la musique").p.onClick();await tick();t=await stable(M);
  OUT.m20_post=posts("/api/audio/music").map(function(c){return c.b});
  OUT.gen=GEN.slice();
  // squelette persona : dialogue maison, puis GET, puis sections posées
  CALLS.length=0;btn(t,"squelette persona").p.onClick();await tick();t=await stable(M);
  OUT.squelette={dialog:DIALOG.slice(),get:CALLS.filter(function(c){return c.u.indexOf("/api/music/lyrics-skeleton")===0}).map(function(c){return c.u}),
    tags:tout(t).filter(function(n){return n.p.className==="svm-lyrtag"}).map(function(n){return n.p.value})};
  window.__REPONSE=null;CALLS.length=0;btn(t,"squelette persona").p.onClick();await tick();
  OUT.squelette_annule=CALLS.length;
  // ACE-Step : prix à la seconde qui suit la durée, graine envoyée, instrumental
  choisir("ACE-Step (paroles)");
  OUT.ace={graine:tout(t).filter(function(n){return n.p["aria-label"]==="Graine de génération"}).length,
    editeurInstru:cls(t,"svm-lyrics").length};
  tout(t).filter(function(n){return n.p["aria-label"]==="Durée de la piste en secondes"})[0].p.onChange({target:{value:"120"}});t=render(M);
  OUT.ace.prix=txt(cls(cls(t,"svm-model")[1],"svm-genprice")[0]);
  tout(t).filter(function(n){return n.p["aria-label"]==="Graine de génération"})[0].p.onChange({target:{value:"42"}});t=render(M);
  CALLS.length=0;btn(t,"Générer la musique").p.onClick();await tick();t=await stable(M);
  OUT.ace.post=posts("/api/audio/music").map(function(c){return c.b})[0];

  // ── Voix off dirigée (ElevenLabs) ──
  REP["GET /api/voice-tags"]={st:200,js:{groups:{emotion:["[excited]","[curious]"],voix:["[whispers]","[sighs]","[exhales]"],special:["[sings]"]},
    experimental:["[sings]"],max_tags:4,model:"eleven_v3",providers:{elevenlabs:true,voicebox:false}}};
  REP["GET /api/voices"]={st:200,js:{enabled:true,voices:[{voice_id:"v1",name:"Prophet",category:"cloned"}]}};
  REP["POST /api/cost/estimate"]={st:200,js:{total_usd:0.0123,breakdown:[]}};
  REP["POST /api/audio/voiceover"]={st:200,js:{ok:true,filename:"sonvfx_vo-1.mp3",url:"/api/audio/sonvfx_vo-1.mp3",notes:[]}};
  REP["POST /api/audio/duck"]={st:200,js:{ok:true,filename:"mix_sonvfx_vo-1_musique_x.mp3",url:"/api/audio/mix_sonvfx_vo-1_musique_x.mp3",dur:2,usd:0}};
  var S=inst(DzSonVfx,{go:function(){}});
  t=await stable(S);
  var V=function(){return cls(t,"svm-vodir")[0]};
  OUT.v_palette=cls(V(),"svm-minibtn").map(txt);
  OUT.mix_avant=cls(t,"svm-mix").length;
  tout(V()).filter(function(n){return n.p["aria-label"]==="Texte de la voix off"})[0].p.onChange({target:{value:"Salut le fond"}});t=render(S);
  ["[whispers]","[excited]","[curious]","[sighs]","[exhales]"].forEach(function(tg){btn(V(),tg).p.onClick();t=render(S)});
  OUT.v_on=cls(V(),"svm-minibtn").filter(function(n){return n.p["data-on"]===""}).map(txt);
  OUT.v_apercu=txt(cls(V(),"svm-voapercu")[0]);
  CALLS.length=0;btn(V(),"Générer la voix").p.onClick();await tick();t=render(S);
  OUT.v_arme={calls:CALLS.map(function(c){return c.m+" "+c.u+" "+JSON.stringify(c.b)}),bouton:!!btn(V(),"Confirmer et générer"),
    devis:txt(V()).indexOf("~$0.012")>=0};
  tout(V()).filter(function(n){return n.p["aria-label"]==="Texte de la voix off"})[0].p.onChange({target:{value:"Salut le fond !"}});t=render(S);
  OUT.v_desarme=!!btn(V(),"Générer la voix");
  CALLS.length=0;btn(V(),"Générer la voix").p.onClick();await tick();t=render(S);btn(V(),"Confirmer et générer").p.onClick();await tick();t=await stable(S);
  OUT.v_tir=posts("/api/audio/voiceover").map(function(c){return c.b});
  // balises posées ET texte qui commence déjà par une balise : l'auteur a dirigé, rien n'est préfixé
  tout(V()).filter(function(n){return n.p["aria-label"]==="Texte de la voix off"})[0].p.onChange({target:{value:"[sarcastic] Adieu"}});t=render(S);
  OUT.v_dirige=txt(cls(V(),"svm-voapercu")[0]);
  tout(V()).filter(function(n){return n.p["aria-label"]==="Texte de la voix off"})[0].p.onChange({target:{value:"Salut le fond !"}});t=render(S);
  OUT.mix_voix={n:cls(t,"svm-mix").length,txt:txt(cls(t,"svm-mix")[0]),off:(btn(cls(t,"svm-mix")[0],"Écouter le mix ducké")||{p:{}}).p["data-off"]};
  // la musique arrive par l'écran Musique (onGenerated de SvmMusic)
  cls(t,"svm-gen").filter(function(n){return txt(cls(n,"svm-genname")[0])==="Musique"})[0].p.onClick();t=render(S);
  var musEl=tout(t).filter(function(n){return n.t===SvmMusic})[0];
  musEl.p.onGenerated({filename:"musique_x.mp3"});t=render(S);
  var mix=cls(t,"svm-mix")[0];
  OUT.mix_pret={off:btn(mix,"Écouter le mix ducké").p["data-off"],txt:txt(mix)};
  btn(mix,"fort").p.onClick();t=render(S);mix=cls(t,"svm-mix")[0];
  CALLS.length=0;AUDIOS.length=0;btn(mix,"Écouter le mix ducké").p.onClick();await tick();t=await stable(S);
  OUT.mix_post=posts("/api/audio/duck").map(function(c){return c.b});
  OUT.mix_joue=AUDIOS.map(function(a){return a.url});

  // ── Voicebox : pas de palette, un clic, pas de devis ──
  REP["GET /api/voice-tags"]={st:200,js:{groups:{emotion:["[excited]"]},experimental:[],max_tags:4,model:"eleven_v3",providers:{elevenlabs:false,voicebox:true}}};
  var VB=inst(DzSonVfx,{go:function(){}});t=await stable(VB);
  var V2=cls(t,"svm-vodir")[0];
  OUT.vb={palette:cls(V2,"svm-tagpal").length,note:txt(V2).indexOf("Voicebox n'interprète pas")>=0};
  tout(V2).filter(function(n){return n.p["aria-label"]==="Texte de la voix off"})[0].p.onChange({target:{value:"[sighs] Bonsoir"}});t=render(VB);V2=cls(t,"svm-vodir")[0];
  OUT.vb.apercu=txt(cls(V2,"svm-voapercu")[0]);
  CALLS.length=0;btn(V2,"Générer la voix").p.onClick();await tick();
  OUT.vb.calls=CALLS.map(function(c){return c.m+" "+c.u});
  console.log(JSON.stringify(OUT));
})().catch(function(e){console.log(JSON.stringify({ERREUR:String(e&&e.stack||e)}))});
"""

js = _TMP / "banc_t102.js"
js.write_text(HARNAIS + SONVFX + MOTEUR, encoding="utf-8")
p = subprocess.run(["node", str(js)], capture_output=True, text=True, encoding="utf-8", timeout=120)
lignes = [l for l in (p.stdout or "").splitlines() if l.startswith("{")]
OUT = json.loads(lignes[-1]) if lignes else {"ERREUR": (p.stderr or "")[-1500:]}
check("T4 le bloc s'exécute sous node", "ERREUR" not in OUT and p.returncode == 0, str(OUT.get("ERREUR", ""))[:1500])

if "ERREUR" not in OUT:
    print("\n[musique]")
    check("M1 prix : à la génération (Lyria, Music 2.0), à la seconde sur la durée (ACE-Step 60 s)",
          OUT["prix"] == ["~$0.10", "~$0.012 · 60 s", "~$0.03"], str(OUT["prix"]))
    check("M2 Music 2.0 : l'éditeur de paroles est VISIBLE malgré le défaut « instrumental », et dit l'obligation",
          OUT["m20_editeur"] == 1 and OUT["m20_oblig"], str(OUT))
    check("M3 Music 2.0 : paroles < 10 caractères refusées SUR PLACE (aucun POST)",
          OUT["m20_refus"] == {"posts": 0, "err": True}, str(OUT["m20_refus"]))
    check("M4 Music 2.0 : le POST porte les sections sérialisées en balises, instrumental faux",
          OUT["m20_post"] and OUT["m20_post"][0]["lyrics"] == "[Chorus]\nyo ho ho et une bouteille"
          and OUT["m20_post"][0]["instrumental"] is False and OUT["m20_post"][0]["model"] == "minimax-music-20",
          str(OUT["m20_post"]))
    check("M5 la piste générée remonte (onGenerated) — c'est elle que la carte Mix prend", OUT["gen"] == ["musique_x.mp3"],
          str(OUT["gen"]))
    sq = OUT["squelette"]
    check("M6 squelette : le thème est demandé par le dialogue maison, envoyé, et les sections posées",
          len(sq["dialog"]) == 1 and sq["get"] == ["/api/music/lyrics-skeleton?theme=abysses"]
          and sq["tags"] == ["Verse", "Chorus"], str(sq))
    check("M7 dialogue annulé : aucune requête", OUT["squelette_annule"] == 0, str(OUT["squelette_annule"]))
    a = OUT["ace"]
    check("M8 ACE-Step : champ graine, et instrumental par défaut (pas d'éditeur)", a["graine"] == 1 and a["editeurInstru"] == 0,
          str(a))
    check("M9 ACE-Step : le prix suit la durée (120 s -> 0,024)", a["prix"] == "~$0.024 · 120 s", a["prix"])
    check("M10 ACE-Step : la graine part en entier, la durée choisie aussi",
          a["post"] and a["post"]["seed"] == 42 and a["post"]["duration_s"] == 120 and a["post"]["model"] == "ace-step",
          str(a["post"]))

    print("\n[voix off dirigée]")
    check("V1 la palette vient de /api/voice-tags", OUT["v_palette"] == ["[excited]", "[curious]", "[whispers]", "[sighs]",
                                                                        "[exhales]", "[sings]"], str(OUT["v_palette"]))
    check("V2 quatre balises au plus : la plus ancienne tombe", OUT["v_on"] == ["[excited]", "[curious]", "[sighs]", "[exhales]"],
          str(OUT["v_on"]))
    check("V3 l'aperçu montre CE QUI PART (balises en tête, dans l'ordre posé)",
          OUT["v_apercu"] == "[excited] [curious] [sighs] [exhales] Salut le fond", OUT["v_apercu"])
    va = OUT["v_arme"]
    check("V4 1er clic : devis du BACKEND (chars du texte balisé, eleven_v3), AUCUNE synthèse",
          va["calls"] == ['POST /api/cost/estimate {"kind":"elevenlabs","chars":%d,"model":"eleven_v3"}'
                          % len("[excited] [curious] [sighs] [exhales] Salut le fond")]
          and va["bouton"] and va["devis"], str(va))
    check("V5 une frappe désarme", OUT["v_desarme"])
    check("V6 2e clic : la synthèse part avec le style, eleven_v3 et la voix choisie",
          OUT["v_tir"] == [{"script": "Salut le fond !", "language": "fr", "name": "sonvfx_vo", "voice_id": "v1",
                            "model": "eleven_v3", "style": {"tags": ["[excited]", "[curious]", "[sighs]", "[exhales]"]}}],
          str(OUT["v_tir"]))

    check("V7 balises posées mais texte déjà balisé en tête : aperçu SANS préfixe (miroir d'apply_style)",
          OUT["v_dirige"] == "[sarcastic] Adieu", OUT["v_dirige"])

    print("\n[mix]")
    check("X1 pas de carte Mix avant toute génération", OUT["mix_avant"] == 0)
    mv = OUT["mix_voix"]
    check("X2 après la voix : la carte paraît, nomme la voix, réclame la musique, bouton éteint",
          mv["n"] == 1 and "sonvfx_vo-1.mp3" in mv["txt"] and "génère une musique" in mv["txt"] and mv["off"] == "", str(mv))
    check("X3 la musique générée arme le bouton", OUT["mix_pret"].get("off") is None and "musique_x.mp3" in OUT["mix_pret"]["txt"],
          str(OUT["mix_pret"]))
    check("X4 POST /audio/duck : voix, musique et le réglage « fort »",
          OUT["mix_post"] == [{"voice": "sonvfx_vo-1.mp3", "music": "musique_x.mp3", "ducking": {"ratio": 12, "threshold": 0.03}}],
          str(OUT["mix_post"]))
    check("X5 le mix est joué", OUT["mix_joue"] == ["/api/audio/mix_sonvfx_vo-1_musique_x.mp3"], str(OUT["mix_joue"]))

    print("\n[voicebox]")
    vb = OUT["vb"]
    check("B1 Voicebox : pas de palette, et l'écran dit pourquoi", vb["palette"] == 0 and vb["note"], str(vb))
    check("B2 texte déjà balisé en tête : aucun préfixe (miroir d'apply_style)", vb["apercu"] == "[sighs] Bonsoir", vb["apercu"])
    check("B3 un seul clic, aucun devis (local, gratuit)", vb["calls"] == ["POST /api/audio/voiceover"], str(vb["calls"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
