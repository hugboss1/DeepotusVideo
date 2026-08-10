# -*- coding: utf-8 -*-
# scripts/patch_bundle_subs.py
"""Patcher assert-gardé : PISTE DE SOUS-TITRES (S1) du Montage.

BASELINE : bundle POST-patch vfxrack (dernier patch en date).
Backup dédié : .js.bak_subs (état juste avant CE patch).
Position dans la chaîne : EN QUEUE, après `vfxrack`.

AVERTISSEMENT DE CHAÎNE — lire avant de toucher quoi que ce soit : une passe
qualité a déjà effacé neuf éditions du rack VFX parce que ses sections vivaient
À L'INTÉRIEUR d'un bloc injecté en amont et qu'un patcher amont a été relancé
seul. Ici : tag NEUF (`subs`), .bak dédié, EN QUEUE. Ne JAMAIS relancer un
patcher amont seul — `python scripts/repatch_all.py --from <tag>` rejoue la
chaîne, et `--list` la montre.

Ce que le patch fait, en une phrase : donner au Montage une VRAIE piste de
sous-titres — segments posés sur la timeline (déplaçables, redimensionnables),
éditeur de lignes avec bornes 00:00.000 calables sur la tête de lecture, panneau
de style complet, karaoké du mot actif dans le lecteur, et les avertissements de
qualité affichés là où on peut agir.

Sections :
  S1  injecte frontend/patches/subs.js (window.DzSubs) juste après le bloc
      vfxrack — même scope module, alias r/x du bundle disponibles ;
  S2  lie /shared/subs.css dans dist/index.html (idempotent) ;
  S3  état du tiroir « Sous-titres » + mémo des avertissements ;
  S4  SVM_TRACKS : la piste `s1`, sous les pistes audio ;
  S5  trackKind : `s1` devient un TROISIÈME genre (« subs ») — tout ce qui
      teste « audio » ou « video » refuse déjà ce qu'il faut — puis toutes les
      fonctions de la couche dans le composant Montage ;
  S6  renderPayload : clé `subtitles` (hors du tableau `clips`) ;
  S7  svmSavePayload : `subs_style` joint à l'autosave ;
  S8  svmApplyProject : restauration du style (serveur puis dz_subs_style) ;
  S9  le tiroir monté à côté des tiroirs Sons et Narration ;
  S10 le lecteur : overlay karaoké, et la légende de maquette qui s'efface ;
  S11 barre d'outils : chip « sous-titres » avec compteur et alerte ;
  S12 en-tête de piste : le « + » de S1 écrit un sous-titre ;
  S13 inspecteur : les propriétés In/Out/Vitesse n'ont pas de sens sur S1 ;
  S14 inspecteur : section « Sous-titre » (texte, bornes, avertissements) ;
  S15 inspecteur : la pile d'effets ne s'affiche pas sur un clip S1 ;
  S16 timeline : pastille d'alerte et opacité des segments masqués ;
  S17 timeline : la piste S1 est marquée (`data-sub`) pour la feuille de style.

Mécanique identique à patch_bundle_vfxrack.py : restauration du .bak dédié
puis ré-application, chaque ancre devant apparaître EXACTEMENT une fois,
sinon abandon sans rien écrire.

Run :
    python scripts/patch_bundle_subs.py              # dépôt
    python scripts/patch_bundle_subs.py --root <dir> # app installée
    python scripts/patch_bundle_subs.py --check      # n'écrit rien
    python scripts/patch_bundle_subs.py --strip      # retire le patch

Compatible scripts/repatch_all.py : `--force-unchained` est accepté et ignoré.
"""
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
REL_HTML = pathlib.Path("frontend/dist/index.html")
PATCH_SRC = REPO / "frontend" / "patches" / "subs.js"
TAG = "subs"

BEGIN = "/*__DZ_SUBS_BEGIN__*/"
END = "/*__DZ_SUBS_END__*/"
ANCHOR_INJECT = "/*__DZ_VFXRACK_END__*/"

CSS_ANCHOR = '<link rel="stylesheet" href="/shared/vfxrack.css">'
CSS_INSERT = '\n    <link rel="stylesheet" href="/shared/subs.css">'


# ── S3 : état du tiroir ──────────────────────────────────────────────────────
A_STATE = '  var stSx=x.useState(!1),sfxOn=stSx[0],setSfxOn=stSx[1];'

R_STATE = '''  var stSx=x.useState(!1),sfxOn=stSx[0],setSfxOn=stSx[1];
  /* ── tiroir « Sous-titres » (S1) — exclusif des tiroirs Sons et Narration.
     Les SEGMENTS sont des clips de la piste s1 : ils vivent dans `clips`,
     donc ils se déplacent, se rognent, s'annulent et se sauvegardent comme
     tout le reste, sans second modèle parallèle. Le STYLE vit dans
     proj.subsStyle (et dans dz_subs_style : la sauvegarde serveur ne connaît
     pas encore la clé, on ne perd pas le réglage en attendant). ── */
  var stSu=x.useState(!1),subsOn=stSu[0],setSubsOn=stSu[1];
  /* mémo des avertissements — recalculés seulement quand les clips ou le
     style changent : la timeline en demande un par segment à chaque rendu */
  var subsWRef=x.useRef({k:null,s:null,m:{}});'''

# ── S4 : la piste ────────────────────────────────────────────────────────────
A_TRACKS = ' {id:"a3",name:"A3",type:"sfx",h:48,c:"--c-3d",mix:13}];'

R_TRACKS = ''' {id:"a3",name:"A3",type:"sfx",h:48,c:"--c-3d",mix:13},
 /* S1 — sous-titres. Sous les pistes audio, comme dans toutes les stations :
    l'image en haut, le son au milieu, le texte en bas. Aucun bus de mixage
    (SVM_TRACK_BUS ne la connaît pas) : son en-tête n'a donc ni M, ni S, ni
    fader — seulement le nom, le type, le « + » et le verrou. */
 {id:"s1",name:"S1",type:"sous-titres",h:44,c:"--c-text",mix:11}];'''

# ── S5 : genre de piste + toute la couche dans le composant ──────────────────
A_KIND = ('  function trackKind(trId){return String(trId||"").charAt(0)==="a"'
          '?"audio":"video"}')

R_KIND = '''  /* « subs » est un TROISIÈME genre de piste, ni vidéo ni audio. Le déclarer
     ici suffit à ce que tout le reste refuse déjà ce qu'il faut : svmDragOk
     (dépôt d'asset vidéo / de son / d'effet du rack VFX), addAsset, la pile
     d'effets, le mixage par clip — chacun teste un genre et ne trouve pas le
     sien sur S1. */
  function trackKind(trId){var k=String(trId||"").charAt(0);
    return k==="a"?"audio":k==="s"?"subs":"video"}

  /* ── couche sous-titres (frontend/patches/subs.js) — feature-detect : si
     elle est absente, tout ce qui suit rend `null` et le Montage retombe
     EXACTEMENT sur son comportement d'avant. ── */
  function subsLayer(){var d=window.DzSubs;return d&&d.ready?d:null}
  function subsSegsOf(cs){
    return (cs||[]).filter(function(c){return c.tr==="s1"})}
  function subsStyleNow(){
    var d=subsLayer();
    return Object.assign(d?d.defaultStyle():{},proj.subsStyle||{})}
  function subsStyleSet(patch){
    setProj(function(p){
      var d=subsLayer();
      var st=Object.assign(d?d.defaultStyle():{},p.subsStyle||{},patch||{});
      try{localStorage.setItem("dz_subs_style",JSON.stringify(st))}catch(_e){}
      return Object.assign({},p,{subsStyle:st})});
    setDirty(!0)}
  /* un seul point d'écriture des segments : les clips s1 sont REMPLACÉS par
     `next`, les autres pistes ne bougent pas. Même règle d'historique que la
     pile d'effets : une entrée par rafale de 600 ms (taper du texte ne remplit
     pas la pile d'annulation d'une entrée par lettre). */
  function subsCommit(next,heavy){
    if(trackStRef.current.s1&&trackStRef.current.s1.l){
      fireNote("Piste S1 verrouillée — déverrouillez-la pour modifier les sous-titres.");
      return}
    var now=Date.now(),d=subsLayer();
    if(heavy||now-((d&&d.hist.t)||0)>600)pushHistory();
    if(d)d.hist.t=now;
    setClips(clipsRef.current.filter(function(c){return c.tr!=="s1"})
      .concat((next||[]).map(function(s){
        return Object.assign({},s,{tr:"s1"})})));
    setDirty(!0)}
  function subsAddHere(){
    var d=subsLayer();
    if(!d){fireNote("Couche de sous-titres absente — relancez l'application.");return}
    var segs=subsSegsOf(clipsRef.current);
    /* la place libre à partir de la tête : le bouton ne fabrique jamais le
       chevauchement qu'il irait ensuite signaler comme une faute */
    var sl=d.freeSlot(segs,phRef.current,durRef.current);
    var s=d.make(sl.start,sl.end,"");
    subsCommit(segs.concat([s]),!0);
    setSelId(s.id);setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);
    fireNote("Sous-titre ajouté à "+d.tc(sl.start)+" — le texte s'écrit dans le tiroir.")}
  function subsToggle(){
    setSubsOn(function(v){return !v});setSfxOn(!1);setNarrOn(!1)}
  /* avertissements de qualité (vitesse de lecture, segments trop courts,
     chevauchements…) — mémoïsés sur l'identité de `clips` et du style : la
     timeline en demande un par segment à chaque rendu. */
  function subsWarnMap(){
    var d=subsLayer(),cs=clipsRef.current,st=proj.subsStyle||null;
    var c0=subsWRef.current;
    if(c0.k===cs&&c0.s===st)return c0.m;
    var m={};
    if(d)d.warnings(subsSegsOf(cs),subsStyleNow(),proj.dur).forEach(function(w){
      if(!m[w.id]||w.sev==="err")m[w.id]=w.sev});
    subsWRef.current={k:cs,s:st,m:m};
    return m}
  /* ce qui part au rendu : hors du tableau `clips` (un sous-titre n'est pas
     un média), masqués et lignes vides retirés. */
  function subsPayload(){
    var d=subsLayer();
    if(!d)return void 0;
    var segs=d.sort(subsSegsOf(clipsRef.current)).filter(function(s){
      return !s.hidden&&String(s.text||"").trim()});
    if(!segs.length)return void 0;
    return {style:subsStyleNow(),
      segments:segs.map(function(s){
        var o={start:Math.round(s.start*1e3)/1e3,end:Math.round(s.end*1e3)/1e3,
               text:String(s.text||"")};
        if(Array.isArray(s.words)&&s.words.length)o.words=s.words;
        return o})}}
  /* ce que la TRANSCRIPTION reçoit. Deux chemins côté backend, et le gratuit
     passe d'abord : si des clips de narration portent leur texte, il le CALE
     sur les silences réels (exact, hors ligne, 0 $) ; sinon il transcrit le
     média. On envoie donc la timeline réduite à ce qui sert, pas le modèle
     client entier. */
  function subsSrcClips(){
    return (clipsRef.current||[]).filter(function(c){
      return c.tr==="a1"||c.tr==="a3"||c.tr==="v1"})
      .map(function(c){
        var o={id:c.id,tr:c.tr,src:c.src||null,
               start:Math.round(subsNum(c.start)*1e3)/1e3,
               end:Math.round(subsNum(c.end)*1e3)/1e3};
        if(c.text)o.text=String(c.text);
        return o})}
  function subsNum(v){var n=Number(v);return isFinite(n)?n:0}
  function subsSrcRef(){
    var cs=clipsRef.current||[],i;
    for(i=0;i<cs.length;i++)if(cs[i].tr==="a1"&&cs[i].src)return cs[i].src;
    for(i=0;i<cs.length;i++)if(cs[i].tr==="v1"&&cs[i].src)return cs[i].src;
    return null}
  function subsPanel(){
    var d=subsLayer();
    if(!d||!d.Drawer)return null;
    return r.jsx(d.Drawer,{open:subsOn,onClose:function(){setSubsOn(!1)},
      segments:subsSegsOf(clips),style:subsStyleNow(),
      onChange:subsCommit,onStyle:subsStyleSet,
      playhead:ph,dur:proj.dur,selId:selId,
      onSelect:function(id){setSelId(id)},
      onSeek:function(t){seekTo(Math.max(0,Math.min(durRef.current,t)))},
      onNote:fireNote,srcName:proj.name,
      srcRef:subsSrcRef(),srcClips:subsSrcClips()})}
  /* LE karaoké : le mot prononcé se surligne dans le lecteur, à l'échelle
     réelle du canevas de rendu (l'aperçu ne ment pas sur la taille).
     Le tiroir ouvert, le même bloc devient MANIPULABLE : cadre de sélection,
     prise au glisser, poignées de largeur, zones sûres. Ce que l'on déplace
     n'est pas une position libre en pixels — c'est l'ancrage, la marge et la
     largeur que le fichier ASS porte, donc ce que ffmpeg gravera. */
  function subsOverlay(){
    var d=subsLayer();
    if(!d||!d.Overlay)return null;
    var segs=subsSegsOf(clips);
    if(!segs.length&&!subsOn)return null;
    return r.jsx(d.Overlay,{segments:segs,style:subsStyleNow(),t:ph,
      edit:subsOn,onStyle:subsStyleSet,
      canvasW:svmRatioW(proj.ratio)>1?1920:1080})}
  /* inspecteur : le sous-titre sélectionné, son texte, ses bornes, et ses
     avertissements — à côté du geste qui les répare, jamais dans un rapport. */
  function subsInspector(){
    var d=subsLayer();
    if(!d||!sel||sel.tr!=="s1")return null;
    var segs=subsSegsOf(clips);
    var ws=d.warnings(segs,subsStyleNow(),proj.dur).filter(function(w){
      return w.id===sel.id});
    return r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:"Sous-titre"}),
      r.jsx("textarea",{className:"sub-text",value:sel.text||"",rows:3,
        placeholder:"Texte du sous-titre…","aria-label":"Texte du sous-titre",
        onChange:function(e){
          var id=selRef.current,v=e.target.value;
          subsCommit(segs.map(function(s){
            return s.id===id?Object.assign({},s,{text:v,label:d.labelOf(v)}):s}))}}),
      r.jsxs("div",{className:"sub-inspfoot",children:[
        r.jsx("span",{className:"sub-inspt",
          title:"Début et fin — réglables au clip près dans le tiroir",
          children:d.tc(sel.start)+" → "+d.tc(sel.end)},"t"),
        r.jsx("button",{className:"sub-minibtn",
          title:"Ouvrir l'éditeur de sous-titres (liste, découpe, style, export)",
          onClick:function(){setSubsOn(!0);setSfxOn(!1);setNarrOn(!1)},
          children:"éditeur"},"ed")]}),
      ws.length?r.jsx("div",{className:"sub-warns",style:{marginTop:8},
        children:ws.map(function(w,k){
          return r.jsxs("div",{className:"sub-warn","data-sev":w.sev,children:[
            r.jsx("span",{className:"sub-warnicon","aria-hidden":!0,
              children:w.sev==="err"?"!":"·"},"i"),
            r.jsx("span",{className:"sub-warnmsg",children:w.msg},"m")]},"w"+k)})}):null]})}'''

# ── S6 : payload de rendu ────────────────────────────────────────────────────
A_PAYLOAD = '    return {name:proj.name,ratio:proj.ratio,preview:preview,'

R_PAYLOAD = '''    return {name:proj.name,ratio:proj.ratio,preview:preview,
      /* piste S1 — HORS du tableau `clips` (ce ne sont pas des médias) :
         {style, segments:[{start,end,text,words?}]}. Absente quand la piste
         est vide ; un backend qui ne connaît pas encore la clé l'ignore et
         le rendu reste exactement celui d'avant. */
      subtitles:subsPayload(),'''

# ── S7 : autosave ────────────────────────────────────────────────────────────
A_SAVE = '      duration_master:durMaster,ducking:ducking,clips:clips};'

R_SAVE = '''      duration_master:durMaster,ducking:ducking,clips:clips,
      /* style des sous-titres : envoyé pour le jour où la sauvegarde serveur
         le connaîtra (les segments, eux, sont déjà dans `clips` et sont
         stockés tels quels) ; en attendant c'est dz_subs_style qui le retient */
      subs_style:proj.subsStyle||void 0};'''

# ── S8 : restauration du style ───────────────────────────────────────────────
A_APPLY = '    setProj(np);'

R_APPLY = '''    /* style des sous-titres : la sauvegarde serveur d'abord si elle le porte,
       le réglage local (dz_subs_style) sinon — jamais le défaut par surprise */
    var _ss=d&&d.subs_style&&typeof d.subs_style==="object"?d.subs_style:null;
    if(!_ss)try{_ss=JSON.parse(localStorage.getItem("dz_subs_style")||"null")}
      catch(_e){_ss=null}
    if(_ss&&typeof _ss==="object")np.subsStyle=_ss;
    setProj(np);'''

# ── S9 : montage du tiroir ───────────────────────────────────────────────────
A_NARR = '      narrPanel(),'

R_NARR = '''      /* tiroir Sous-titres (DzSubs.Drawer) — même emplacement que Sons et
         Narration, les trois exclusifs */
      subsPanel(),
      narrPanel(),'''

# ── S10 : lecteur (karaoké + légende de maquette) ────────────────────────────
A_CAPTION = '''          r.jsx("div",{className:"svm-caption",children:
            r.jsx("div",{className:"svm-captiontext",children:proj.demo?"« La marée ne demande pas la permission. »":proj.name})}),'''

R_CAPTION = '''          /* sous-titres du projet, mot actif surligné pendant la lecture */
          subsOverlay(),
          /* légende de la maquette : elle s'efface dès qu'une vraie piste S1
             existe, ou pendant le placement — deux textes empilés au même
             endroit ne veulent rien dire */
          subsSegsOf(clips).length||subsOn?null
          :r.jsx("div",{className:"svm-caption",children:
            r.jsx("div",{className:"svm-captiontext",children:proj.demo?"« La marée ne demande pas la permission. »":proj.name})}),'''

# ── S11 : chip de la barre d'outils ──────────────────────────────────────────
A_RIPPLE = '''          r.jsx("button",{className:"svm-toolchip","data-on":ripple?"":void 0,
            title:"refermer les trous — suppression et rognage droit sur V1 ("+svmKeyLabel("ripple")+")",onClick:function(){setRipple(!ripple)},children:"ripple"})]}),'''

R_RIPPLE = '''          r.jsx("button",{className:"svm-toolchip","data-on":ripple?"":void 0,
            title:"refermer les trous — suppression et rognage droit sur V1 ("+svmKeyLabel("ripple")+")",onClick:function(){setRipple(!ripple)},children:"ripple"}),
          /* sous-titres : la chip dit combien de lignes porte la piste et
             combien clochent — le problème se voit à l'endroit où l'on
             clique, pas dans un rapport que personne n'ouvre */
          (function(){
            if(!subsLayer())return null;
            var n=subsSegsOf(clips).length,wm=subsWarnMap(),bad=0;
            Object.keys(wm).forEach(function(k){if(wm[k]==="err")bad++});
            return r.jsxs("button",{className:"svm-toolchip","data-on":subsOn?"":void 0,
              "aria-pressed":subsOn,
              title:"Piste de sous-titres S1 — lignes, calage, style et karaoké"+
                (n?" ("+n+" lignes)":" (piste vide)"),
              onClick:subsToggle,children:[
              "sous-titres",
              n?r.jsx("span",{className:"sub-chipn",children:String(n)},"n"):null,
              bad?r.jsx("span",{className:"sub-chipbad",
                title:bad+" sous-titre(s) à corriger",
                children:String(bad)},"b"):null]})})()]}),'''

# ── S12 : « + » de l'en-tête de piste ────────────────────────────────────────
A_THADD = '''            var thAdd=r.jsx("button",{className:"svm-ovadd",
              title:trackKind(tr.id)==="audio"
                ?"Ajouter un son de la Bibliothèque à la tête de lecture"
                :"Ajouter une image ou un rendu à la tête de lecture",
              onClick:function(){openPicker(tr.id)},children:"+"},"add");'''

R_THADD = '''            var thAdd=r.jsx("button",{className:"svm-ovadd",
              title:trackKind(tr.id)==="subs"
                ?"Écrire un sous-titre à la tête de lecture"
                :trackKind(tr.id)==="audio"
                ?"Ajouter un son de la Bibliothèque à la tête de lecture"
                :"Ajouter une image ou un rendu à la tête de lecture",
              onClick:function(){
                if(trackKind(tr.id)==="subs"){subsAddHere();return}
                openPicker(tr.id)},children:"+"},"add");'''

# ── S13 : propriétés In/Out/Vitesse hors sujet sur S1 ────────────────────────
A_PROPS = '          return r.jsx("div",{className:"svm-props",children:kids})})(),'

R_PROPS = '''          /* In / Out / Vitesse : une fenêtre de source, ça ne veut rien dire
             pour une ligne de texte — la section « Sous-titre » prend le relais */
          return sel&&sel.tr==="s1"?null
            :r.jsx("div",{className:"svm-props",children:kids})})(),'''

# ── S14 : section « Sous-titre » de l'inspecteur ─────────────────────────────
A_SECTIONS = '        transInspector(),'

R_SECTIONS = '''        subsInspector(),
        transInspector(),'''

# ── S15 : pas de pile d'effets sur un clip S1 ────────────────────────────────
A_VFXSTACK = '        vfxStackSection()]})]}),'

R_VFXSTACK = '''        (sel&&sel.tr==="s1"?null:vfxStackSection())]})]}),'''

# ── S16 : pastille d'alerte / segment masqué, sur la timeline ────────────────
A_CLIPDIV = ('                    onPointerDown:function(e){clipDown(e,c,'
             'e.currentTarget.parentElement)},')

R_CLIPDIV = '''                    /* le problème se voit SUR la timeline : pastille
                       rouge sur le segment fautif, segment masqué en retrait */
                    "data-warn":tr.id==="s1"&&subsWarnMap()[c.id]==="err"?"":void 0,
                    "data-hidden":tr.id==="s1"&&c.hidden?"":void 0,
                    onPointerDown:function(e){clipDown(e,c,e.currentTarget.parentElement)},'''

# ── S17 : la piste S1 marquée pour la feuille de style ───────────────────────
A_TRACKEL = ('            return r.jsxs("div",{className:"svm-track",'
             '"data-soloexcl":soloExcl?"":void 0,style:{height:tr.h},children:[')

R_TRACKEL = ('            return r.jsxs("div",{className:"svm-track",'
             '"data-sub":tr.id==="s1"?"":void 0,'
             '"data-soloexcl":soloExcl?"":void 0,style:{height:tr.h},children:[')


PATCHES = [
    ("S3-state", A_STATE, R_STATE),
    ("S4-tracks", A_TRACKS, R_TRACKS),
    ("S5-kind", A_KIND, R_KIND),
    ("S6-payload", A_PAYLOAD, R_PAYLOAD),
    ("S7-save", A_SAVE, R_SAVE),
    ("S8-apply", A_APPLY, R_APPLY),
    ("S9-drawer", A_NARR, R_NARR),
    ("S10-caption", A_CAPTION, R_CAPTION),
    ("S11-chip", A_RIPPLE, R_RIPPLE),
    ("S12-thadd", A_THADD, R_THADD),
    ("S13-props", A_PROPS, R_PROPS),
    ("S14-inspector", A_SECTIONS, R_SECTIONS),
    ("S15-vfxstack", A_VFXSTACK, R_VFXSTACK),
    ("S16-clip", A_CLIPDIV, R_CLIPDIV),
    ("S17-trackel", A_TRACKEL, R_TRACKEL),
]


def nl(text, crlf):
    """Aligne les fins de ligne d'un fragment sur celles du fichier cible.

    Le bundle est un mélange : la partie minifiée n'a pas de saut de ligne,
    les blocs injectés (sonvfx, sfxstudio, vfxrack) sont en CRLF — git
    normalise les sources du dépôt à la sortie. Une ancre écrite en LF ne
    matcherait donc jamais : on la convertit avant toute comparaison.
    """
    t = text.replace("\r\n", "\n")
    return t.replace("\n", "\r\n") if crlf else t


def apply(s, anchor, replacement, tag):
    """Remplacement assert-gardé : l'ancre doit exister exactement une fois."""
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_text(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def write_text(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def patch_html(html, strip):
    """Lien /shared/subs.css — idempotent, indépendant du bundle."""
    ins = nl(CSS_INSERT, "\r\n" in html)
    if strip:
        if "shared/subs.css" in html:
            return html.replace(ins, "").replace(ins.strip(), ""), "lien css retiré"
        return html, ""
    if "shared/subs.css" in html:
        return html, ""
    if html.count(CSS_ANCHOR) != 1:
        raise SystemExit(f"[{TAG}] ancre css introuvable ou multiple. Aborting.")
    return html.replace(CSS_ANCHOR, CSS_ANCHOR + ins), "lien css ajouté"


def main():
    args = sys.argv[1:]
    root = pathlib.Path(".")
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1]).resolve()
    check = "--check" in args
    strip = "--strip" in args

    bundle = root / REL_BUNDLE
    html_path = root / REL_HTML
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    if not html_path.is_file():
        raise SystemExit(f"[{TAG}] index.html introuvable : {html_path}")
    if not PATCH_SRC.is_file():
        raise SystemExit(f"[{TAG}] source introuvable : {PATCH_SRC}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)

    if check:
        # Contrôle à sec : on valide les ancres sur l'état PRÉ-patch
        # (le .bak s'il existe, sinon le bundle courant), sans rien écrire.
        src = bak if bak.exists() else bundle
        s, _ = read_text(src)
        crlf = "\r\n" in s
        if s.count(ANCHOR_INJECT) != 1:
            raise SystemExit(
                f"[S1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1) "
                f"dans {src.name}. Aborting.")
        for tag, anchor, _repl in PATCHES:
            n = s.count(nl(anchor, crlf))
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {src.name}. Aborting.")
        print(f"[{TAG}] applicable sur {src} ({len(PATCHES) + 1} ancres OK)")
        return

    if strip:
        s, bom = read_text(bundle)
        done = []
        if BEGIN in s:
            head, rest = s.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            s = head.rstrip("\n") + tail.lstrip("\n")
            done.append("bloc retiré")
        if bak.exists():
            shutil.copy2(bak, bundle)
            done.append("bundle restauré depuis le .bak")
        else:
            write_text(bundle, s, bom)
        html, hbom = read_text(html_path)
        html, hmsg = patch_html(html, True)
        if hmsg:
            write_text(html_path, html, hbom)
            done.append(hmsg)
        print(f"[{TAG}] strip — {', '.join(done) or 'rien à faire'}")
        return

    if not bak.exists():
        shutil.copy2(bundle, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, bundle)

    s, bom = read_text(bundle)
    crlf = "\r\n" in s
    # S1 — injection de la couche, juste après le bloc vfxrack
    component = PATCH_SRC.read_bytes().decode("utf-8-sig")
    block = nl("\n" + BEGIN + "\n" + component + "\n" + END, crlf)
    if s.count(ANCHOR_INJECT) != 1:
        raise SystemExit(
            f"[S1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1). Aborting.")
    s = s.replace(ANCHOR_INJECT, ANCHOR_INJECT + block)
    # S3..S17 — ancres du bloc sonvfx (source injectée)
    for tag, anchor, repl in PATCHES:
        s = apply(s, nl(anchor, crlf), nl(repl, crlf), tag)
    write_text(bundle, s, bom)

    # S2 — feuille de style (index.html, hors chaîne des .bak)
    html, hbom = read_text(html_path)
    html, hmsg = patch_html(html, False)
    if hmsg:
        write_text(html_path, html, hbom)

    print("OK — bundle patché (piste de sous-titres S1 : segments, éditeur, "
          "style, karaoké). Size:", bundle.stat().st_size,
          "| index.html:", hmsg or "inchangé")


if __name__ == "__main__":
    main()
