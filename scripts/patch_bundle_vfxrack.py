# -*- coding: utf-8 -*-
# scripts/patch_bundle_vfxrack.py
"""Patcher assert-gardé : RACK VFX (panneau d'effets + pile par clip).

BASELINE : bundle POST-patch materialforge (dernier patch en date).
Backup dédié : .js.bak_vfxrack (état juste avant CE patch).
Position dans la chaîne : EN QUEUE, après `materialforge`.

Ce que le patch fait, en une phrase : remplacer le choix d'effet « à
l'aveugle sur un nom » par un vrai rack — catégories, recherche, favoris,
VIGNETTE D'APERÇU rendue sur le clip réellement sélectionné, pose par clic
ET par glisser, pile réordonnable/contournable avec bornes t0/t1 et rampe.

Sections :
  V1  injecte frontend/patches/vfxrack.js (window.DzVfx) juste après le bloc
      sfxstudio — même scope module, alias r/x du bundle disponibles ;
  V2  lie /shared/vfxrack.css dans dist/index.html (idempotent) ;
  V3  svmDragOk : le mime « dz-vfx » est accepté sur les pistes VIDÉO ;
  V4  dropOnTrack : un effet déposé est routé vers le clip sous le curseur ;
  V5  vfxAddTo / vfxDropEffect : pose d'un effet dans le composant Montage ;
  V6  fxPicker : DzVfx.Panel quand la couche est là, sélecteur historique
      sinon (fxPickerLegacy, code d'origine conservé mot pour mot) ;
  V7  vfxStackSection / vfxLegacySection : la section « Effets sur ce clip » ;
  V8  l'inspecteur appelle vfxStackSection() ;
  V9  renderPayload : les effets contournés (`off`) sortent du rendu ;
  V10 nœud Effects du Studio : la grille d'effets devient DzVfx.Panel inline ;
  V11 nœud Effects du Studio : rangée « Bornes » (DzVfx.Bounds).

Mécanique identique à patch_bundle_materialforge.py : restauration du .bak
dédié puis ré-application, chaque ancre devant apparaître EXACTEMENT une
fois, sinon abandon sans rien écrire.

Run :
    python scripts/patch_bundle_vfxrack.py              # dépôt
    python scripts/patch_bundle_vfxrack.py --root <dir> # app installée
    python scripts/patch_bundle_vfxrack.py --check      # n'écrit rien
    python scripts/patch_bundle_vfxrack.py --strip      # retire le patch

Compatible scripts/repatch_all.py : `--force-unchained` est accepté et ignoré.
"""
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
REL_HTML = pathlib.Path("frontend/dist/index.html")
PATCH_SRC = REPO / "frontend" / "patches" / "vfxrack.js"
TAG = "vfxrack"

BEGIN = "/*__DZ_VFXRACK_BEGIN__*/"
END = "/*__DZ_VFXRACK_END__*/"
ANCHOR_INJECT = "/*__DZ_SFXSTUDIO_END__*/"

CSS_ANCHOR = '<link rel="stylesheet" href="/shared/sfxstudio.css">'
CSS_INSERT = '\n    <link rel="stylesheet" href="/shared/vfxrack.css">'


# ── V3 ───────────────────────────────────────────────────────────────────────
A_DRAGOK = '''    if(Array.prototype.indexOf.call(ts,DZ_MIME)>=0)return !0;
    return Array.prototype.indexOf.call(ts,"dz-audio")>=0&&!!trId&&trackKind(trId)==="audio"}'''

R_DRAGOK = '''    if(Array.prototype.indexOf.call(ts,DZ_MIME)>=0)return !0;
    /* effet du rack VFX (mime « dz-vfx ») : pistes VIDÉO seulement — ailleurs
       le survol reste refusé (curseur no-drop, aucun faux espoir) */
    if(Array.prototype.indexOf.call(ts,"dz-vfx")>=0)
      return !!trId&&trackKind(trId)==="video";
    return Array.prototype.indexOf.call(ts,"dz-audio")>=0&&!!trId&&trackKind(trId)==="audio"}'''

# ── V4 ───────────────────────────────────────────────────────────────────────
A_DROP = '''  function dropOnTrack(e,trId,laneEl){
    var p=readPayload(e);'''

R_DROP = '''  function dropOnTrack(e,trId,laneEl){
    /* effet du rack VFX déposé sur une bande vidéo → pile du clip visé */
    var _vfx=null;
    try{var _rv=e.dataTransfer.getData("dz-vfx");_vfx=_rv?JSON.parse(_rv):null}
    catch(_e){_vfx=null}
    if(_vfx&&_vfx.type){e.preventDefault();vfxDropEffect(_vfx,trId,laneEl,e);return}
    var p=readPayload(e);'''

# ── V5 ───────────────────────────────────────────────────────────────────────
A_MIME = '  var DZ_MIME="application/dz-asset";'

R_MIME = '''  /* ── rack VFX : pose d'un effet sur un clip vidéo (clic du panneau ou
     dépôt sur la bande). Même moteur que les autres mutations de clip :
     historique, sélection, note. ── */
  function vfxAddTo(id,eff){
    var cs=clipsRef.current,c=null;
    for(var i=0;i<cs.length;i++){if(cs[i].id===id){c=cs[i];break}}
    if(!c)return !1;
    if(!c.src){fireNote("Effets par clip : disponibles sur les clips réels (Bibliothèque) — la démo reste une maquette.");return !1}
    if(trackKind(c.tr)!=="video"){fireNote("Un effet vidéo se pose sur un clip V1 ou V2.");return !1}
    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){
      fireNote("Piste "+c.tr.toUpperCase()+" verrouillée — déverrouillez-la pour poser un effet.");return !1}
    var e2={};
    Object.keys(eff||{}).forEach(function(k){if(k!=="label")e2[k]=eff[k]});
    pushHistory();
    setClips(clipsRef.current.map(function(k){
      return k.id===id?Object.assign({},k,{effects:(k.effects||[]).concat([e2])}):k}));
    setSelId(id);setDirty(!0);
    return !0}
  function vfxDropEffect(eff,trId,laneEl,e){
    if(proj.demo){fireNote("Dépôt d'effet : disponible sur un projet réel — la démo reste une maquette.");return}
    var t=null;
    if(laneEl){var rc=laneEl.getBoundingClientRect();
      if(rc.width>0)t=Math.max(0,(e.clientX-rc.left)/rc.width*durRef.current)}
    var cs=clipsRef.current,hit=null;
    for(var i=0;i<cs.length;i++){var c=cs[i];
      if(c.tr!==trId||!c.src)continue;
      if(t==null||(t>=c.start-.001&&t<=c.end+.001)){hit=c;break}}
    if(!hit){fireNote("Aucun clip sous le curseur — déposez l'effet sur un clip.");return}
    if(vfxAddTo(hit.id,eff))
      fireNote("Effet « "+(eff.label||eff.type)+" » posé sur « "+hit.label+" » — réglable dans la pile.")}
  var DZ_MIME="application/dz-asset";'''

# ── V6 ───────────────────────────────────────────────────────────────────────
A_PICKER = '''  /* sélecteur d'effets — catalogue réel du moteur Effects / Mask */
  function fxPicker(){
    if(!fxPick||!fxCat)return null;'''

R_PICKER = '''  /* couche rack VFX (frontend/patches/vfxrack.js) — feature-detect : absente,
     tout retombe sur le sélecteur historique, rien ne casse */
  function vfxLayer(){var d=window.DzVfx;return d&&d.ready?d:null}
  /* sélecteur d'effets — panneau du rack VFX (catégories, recherche, favoris,
     vignettes d'aperçu rendues sur CE plan, pose par clic ou par glisser) */
  function fxPicker(){
    if(!fxPick)return null;
    var d=vfxLayer();
    if(d&&d.Panel)
      return r.jsx(d.Panel,{open:!0,clip:sel,stack:(sel&&sel.effects)||[],
        onClose:function(){setFxPick(!1)},
        onAdd:function(eff,meta){
          var id=selRef.current;
          if(vfxAddTo(id,eff))
            fireNote("Effet « "+((meta&&meta.label)||eff.type)+" » posé — réglable dans la pile.")}});
    return fxPickerLegacy()}
  /* sélecteur historique — conservé mot pour mot comme repli */
  function fxPickerLegacy(){
    if(!fxPick||!fxCat)return null;'''

# ── V7 ───────────────────────────────────────────────────────────────────────
A_STACKDEF = "  function fxEditRow(){"

R_STACKDEF = '''  /* ── section « Effets sur ce clip » de l'inspecteur ─────────────────────
     rack VFX (pile complète : ordre, contournement, paramètres, bornes t0/t1
     et rampe, bascule avant / après) sur un clip VIDÉO réel ; chips
     historiques partout ailleurs (démo, clips audio, couche absente). */
  function vfxStackSection(){
    var d=vfxLayer();
    if(d&&d.Stack&&sel&&sel.src&&trackKind(sel.tr)==="video")
      return r.jsx(d.Stack,{effects:sel.effects||[],clip:sel,
        dur:Math.max(.1,sel.end-sel.start),
        onOpenPanel:function(){setFxPick(!fxPick)},
        onChange:function(next,heavy){
          /* une entrée d'historique par rafale de 600 ms — même règle que
             l'opacité d'overlay et le mixage par clip */
          var id=selRef.current,now=Date.now();
          if(heavy||now-(d.hist.t||0)>600)pushHistory();
          d.hist.t=now;
          setClips(clipsRef.current.map(function(k){
            return k.id===id?Object.assign({},k,{effects:next}):k}));
          setDirty(!0)}});
    return vfxLegacySection()}
  function vfxLegacySection(){
    return r.jsxs(r.Fragment,{children:[
      r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:"Effets sur ce clip"}),
      r.jsxs("div",{className:"svm-fxchips",children:[
        /* chips fx de la maquette (clips VIDÉO) — le rack AUDIO (clé fx du
           contrat) s'édite dans l'inspecteur « Clip audio », pas ici */
        (sel&&sel.fx&&trackKind(sel.tr)!=="audio"?sel.fx:[]).map(function(f){
          return r.jsx("span",{className:"svm-fxchip","data-c":f.c,children:f.n},f.n)}),
        (sel&&sel.effects?sel.effects:[]).map(function(f,fi){
          var lbl=(fxCat&&fxCat[f.type]&&fxCat[f.type].label)||f.type;
          var editing=fxEdit&&fxEdit.id===sel.id&&fxEdit.i===fi;
          return r.jsx("button",{className:"svm-fxchip","data-c":"c3d",
            title:"Régler / retirer l'effet",
            style:{cursor:"pointer",borderColor:editing?"var(--accent)":void 0},
            onClick:function(){setFxEdit(editing?null:{id:selRef.current,i:fi})},
            children:lbl},f.type+fi)}),
        r.jsx("button",{className:"svm-fxadd",
          onClick:function(){
            if(!sel||!sel.src){fireNote("Effets par clip : disponibles sur les clips réels (Bibliothèque) — la démo reste une maquette.");return}
            if(!vfxLayer()&&!fxCat){fireNote("Catalogue d'effets indisponible — backend à relancer ?");return}
            setFxPick(!fxPick)},
          children:"+ effet"})]}),
      fxEditRow()]})}
  function fxEditRow(){'''

# ── V8 ───────────────────────────────────────────────────────────────────────
A_INSPECTOR = '''        r.jsx(SvmLabel,{style:{margin:"20px 0 10px"},children:"Effets sur ce clip"}),
        r.jsxs("div",{className:"svm-fxchips",children:[
          /* chips fx de la maquette (clips VIDÉO) — le rack AUDIO (clé fx du
             contrat) s'édite dans l'inspecteur « Clip audio », pas ici */
          (sel&&sel.fx&&trackKind(sel.tr)!=="audio"?sel.fx:[]).map(function(f){
            return r.jsx("span",{className:"svm-fxchip","data-c":f.c,children:f.n},f.n)}),
          (sel&&sel.effects?sel.effects:[]).map(function(f,fi){
            var lbl=(fxCat&&fxCat[f.type]&&fxCat[f.type].label)||f.type;
            var editing=fxEdit&&fxEdit.id===sel.id&&fxEdit.i===fi;
            return r.jsx("button",{className:"svm-fxchip","data-c":"c3d",
              title:"Régler / retirer l'effet",
              style:{cursor:"pointer",borderColor:editing?"var(--accent)":void 0},
              onClick:function(){
                setFxEdit(editing?null:{id:selRef.current,i:fi})},
              children:lbl},f.type+fi)}),
          r.jsx("button",{className:"svm-fxadd",
            onClick:function(){
              if(!sel||!sel.src){fireNote("Effets par clip : disponibles sur les clips réels (Bibliothèque) — la démo reste une maquette.");return}
              if(!fxCat){fireNote("Catalogue d'effets indisponible — backend à relancer ?");return}
              setFxPick(!fxPick)},
            children:"+ effet"})]}),
        fxEditRow()]})]}),'''

R_INSPECTOR = '''        vfxStackSection()]})]}),'''

# ── V9 ───────────────────────────────────────────────────────────────────────
A_PAYLOAD = "          effects:c.effects&&c.effects.length?c.effects:void 0,"

R_PAYLOAD = '''          /* contournés (bypass du rack VFX) : retirés du RENDU, gardés dans
             le projet — la clé `off` ne quitte jamais le client */
          effects:(function(){
            var _fx=(c.effects||[]).filter(function(_f){return !_f.off});
            return _fx.length?_fx:void 0})(),'''

# ── V10 ──────────────────────────────────────────────────────────────────────
A_STUDIO_GRID = (
    'rows.push(r.jsx(O,{label:"Effet",children:r.jsx("div",'
    '{style:Object.assign({},grid,{maxHeight:250,overflowY:"auto"}),'
    'children:TYPES.map(function(t){return thumb(t[0],"/effect-thumbs/"+t[0]+".jpg",'
    'cur.type===t[0],function(){setE({type:t[0]})},t[1])})})}));'
)

R_STUDIO_GRID = (
    'var _vl=window.DzVfx&&window.DzVfx.ready?window.DzVfx:null;'
    'rows.push(r.jsx(O,{label:"Effet",children:_vl&&_vl.Panel'
    '?r.jsx(_vl.Panel,{inline:!0,title:"Effets",stack:n.effects||[],'
    'onPick:function(ty,eff){'
    'var keep={};'
    '["t0","t1","fade_in","fade_out","ease_in","ease_out"].forEach(function(k){'
    'if(cur[k]!=null)keep[k]=cur[k]});'
    'o("effects",[Object.assign({},eff,keep)])}})'
    ':r.jsx("div",{style:Object.assign({},grid,{maxHeight:250,overflowY:"auto"}),'
    'children:TYPES.map(function(t){return thumb(t[0],"/effect-thumbs/"+t[0]+".jpg",'
    'cur.type===t[0],function(){setE({type:t[0]})},t[1])})})}));'
)

# ── V11 ──────────────────────────────────────────────────────────────────────
A_STUDIO_SRCT = (
    'var srcT={Upload:1,Image:1,Seedance:1,ExistingRender:1,'
    'NewsIllustration:1,SpatialCompose:1,HeyGenAvatar:1,Animation:1};'
)

R_STUDIO_SRCT = (
    'if(_vl&&_vl.Bounds)rows.push(r.jsx(O,{label:"Bornes",'
    'hint:"Limiter l\'effet a un intervalle du plan, avec rampe de Bezier.",'
    'children:r.jsx(_vl.Bounds,{eff:cur,dur:Number(n.durationS)||0,'
    'onChange:function(p){setE(p)}})}));'
) + A_STUDIO_SRCT


PATCHES = [
    ("V3-dragok", A_DRAGOK, R_DRAGOK),
    ("V4-drop", A_DROP, R_DROP),
    ("V5-addto", A_MIME, R_MIME),
    ("V6-picker", A_PICKER, R_PICKER),
    ("V7-stackdef", A_STACKDEF, R_STACKDEF),
    ("V8-inspector", A_INSPECTOR, R_INSPECTOR),
    ("V9-payload", A_PAYLOAD, R_PAYLOAD),
    ("V10-studio-grid", A_STUDIO_GRID, R_STUDIO_GRID),
    ("V11-studio-bounds", A_STUDIO_SRCT, R_STUDIO_SRCT),
]


def nl(text, crlf):
    """Aligne les fins de ligne d'un fragment sur celles du fichier cible.

    Le bundle est un mélange : la partie minifiée n'a pas de saut de ligne,
    les blocs injectés (sonvfx, sfxstudio) sont en CRLF — git normalise les
    sources du dépôt à la sortie. Une ancre écrite en LF ne matcherait donc
    jamais : on la convertit avant toute comparaison.
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
    """Lien /shared/vfxrack.css — idempotent, indépendant du bundle."""
    ins = nl(CSS_INSERT, "\r\n" in html)
    if strip:
        if "shared/vfxrack.css" in html:
            return html.replace(ins, "").replace(ins.strip(), ""), "lien css retiré"
        return html, ""
    if "shared/vfxrack.css" in html:
        return html, ""
    if html.count(CSS_ANCHOR) != 1:
        raise SystemExit(f"[{TAG}] ancre css introuvable ou multiple. Aborting.")
    return html.replace(CSS_ANCHOR, CSS_ANCHOR + ins), "lien css ajouté"



def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est deja passe.

    CE MAILLON RESTAURE SON .bak PUIS REAPPLIQUE : sans cette garde, le
    relancer seul remet le bundle a l'etat d'AVANT lui et efface EN SILENCE
    tout ce que les maillons suivants ont ecrit. Mesure sur la chaine du
    2026-08-11 : materialforge seul = 23 couples ancre->remplacement detruits
    (21 in-bloc vfxrack/subs + 2 cardforge), vfxrack seul = 17, subs seul = 8.
    Le bundle reste syntaxiquement valide, tous les marqueurs BEGIN/END
    restent la, `node --check` passe : c'est exactement le mode de panne qui a
    deja coute 22 correctifs a ce depot. `--force-unchained` la desarme —
    c'est ce que passe repatch_all.py quand il rejoue TOUTE la chaine dans
    l'ordre.
    """
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name} (plus "
                f"recent que {bak.name}). Le relancer seul effacerait ce que "
                "les maillons suivants ont ecrit — sans un mot. Rejouer la "
                "chaine entiere (repatch_all) ou forcer avec "
                "--force-unchained en connaissance de cause.")


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

    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        # Contrôle à sec : on valide les ancres sur l'état PRÉ-patch
        # (le .bak s'il existe, sinon le bundle courant), sans rien écrire.
        src = bak if bak.exists() else bundle
        s, _ = read_text(src)
        crlf = "\r\n" in s
        if s.count(ANCHOR_INJECT) != 1:
            raise SystemExit(
                f"[V1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1) "
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
    # V1 — injection de la couche, juste après le bloc sfxstudio
    component = PATCH_SRC.read_bytes().decode("utf-8-sig")
    block = nl("\n" + BEGIN + "\n" + component + "\n" + END, crlf)
    if s.count(ANCHOR_INJECT) != 1:
        raise SystemExit(
            f"[V1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1). Aborting.")
    s = s.replace(ANCHOR_INJECT, ANCHOR_INJECT + block)
    # V3..V11 — ancres du bloc sonvfx (source injectée) et du nœud Studio
    for tag, anchor, repl in PATCHES:
        s = apply(s, nl(anchor, crlf), nl(repl, crlf), tag)
    write_text(bundle, s, bom)

    # V2 — feuille de style (index.html, hors chaîne des .bak)
    html, hbom = read_text(html_path)
    html, hmsg = patch_html(html, False)
    if hmsg:
        write_text(html_path, html, hbom)

    print("OK — bundle patché (rack VFX : panneau d'effets + pile par clip). "
          "Size:", bundle.stat().st_size,
          "| index.html:", hmsg or "inchangé")


if __name__ == "__main__":
    main()
