# scripts/patch_bundle_libsprites.py
"""Assert-guarded patcher: Library « Sprites » + hand-off Sprite Lab (chantier 9d).

BASELINE: bundle POST-patch spritelab (dernier patch en date).
Backup dédié: .js.bak_libsprites (état juste avant CE patch).

Ce patch ajoute :
- l'onglet « Sprites » de la Library : jobs sprite2d terminés AVEC sheet
  (final_video_path — les sondes extract_only n'en ont pas), vignette
  frame/0 statique → preview.gif au survol, Sheet PNG + ZIP pack Unity,
  favoris (dz_fav_renders, comme les renders/3D), rename (renameJob),
  delete (deleteJob supprime déjà les fichiers), viewer GIF sur damier ;
- l'exclusion des jobs sprite2d des listes de « renders » (Library +
  pickers Existing render) : leur final_video_path est un PNG, pas une
  vidéo ;
- le hand-off « → Sprite Lab » sur les renders ET les images de la
  Library : __dzToSpriteLab pose window.__dzSpriteSource puis dispatch
  deepotus:navigate {view:"assets3d", subtab:"sprites", source} (le
  subtab est déjà géré par le patch spritelab 9c) ;
- le relais de la source vers l'iframe /spritelab via postMessage
  {type:"spritelab:source", source} : le hub poste quand l'iframe est
  chargée (onLoad) ou déjà ouverte (event assets-subtab), et ne consomme
  window.__dzSpriteSource qu'après un postMessage effectif.

Run: python scripts/patch_bundle_libsprites.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_libsprites")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ── items Sprites (même gabarit que T3, l'onglet 3D) ─────────────────────────
TS_ITEMS = (
    ',TS=u.filter(C=>C.provider==="sprite2d"&&C.status==="done"'
    '&&C.final_video_path).map(C=>{const sh=(C.job_id||"").slice(0,8);'
    'return{name:C.title||"sprites_"+sh,kind:"sprite2d",size:"",'
    'date:mo(C.created_at),provider:"Sprites",jobId:C.job_id,short:sh,'
    'url:"/api/assets/sprite/"+sh+"/sheet",'
    'gif:"/api/assets/sprite/"+sh+"/preview",'
    'zip:"/api/assets/sprite/"+sh+"/zip",'
    'frame0:"/api/assets/sprite/"+sh+"/frame/0"}})'
)

# ── vignette de grille : frame/0 statique, preview.gif au survol ─────────────
GRID_SPRITE = (
    ':C.url&&C.kind==="sprite2d"?r.jsxs("div",{style:{width:"100%",height:120,'
    'background:"#02060d",position:"relative",overflow:"hidden"},'
    'children:[r.jsx("img",{src:C.frame0,alt:C.name,loading:"lazy",'
    'onMouseEnter:ee=>{ee.currentTarget.src=C.gif},'
    'onMouseLeave:ee=>{ee.currentTarget.src=C.frame0},'
    'style:{width:"100%",height:"100%",objectFit:"contain",display:"block"}}),'
    'r.jsx("div",{style:{position:"absolute",bottom:4,right:4,'
    'padding:"2px 5px",fontSize:9,fontWeight:600,fontFamily:"var(--f-mono)",'
    'color:"var(--cyan)",background:"#02060daa",borderRadius:3},'
    'children:"▶ hover"})]})'
)

# ── viewer du modal : preview.gif en grand sur damier ────────────────────────
VIEWER_SPRITE = (
    'm.kind==="sprite2d"?r.jsx("img",{src:m.gif,alt:m.name,'
    'style:{maxWidth:"70vw",maxHeight:"65vh",borderRadius:"var(--r)",'
    'background:"repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) '
    '0 0/18px 18px"}}):'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # L-1: vo — la clé Sprites donne son onglet à la barre (ordre des clés).
    a = '],"3D":[],Audio:[],Favoris:[]};function __dzFavGet()'
    r = '],"3D":[],Sprites:[],Audio:[],Favoris:[]};function __dzFavGet()'
    s = apply(s, a, r, "L1-vo-tab")

    # L-2: Renders de la Library — un sheet PNG n'est pas un render vidéo.
    a = ('const H=u.filter(C=>C.status==="done"&&C.final_video_path'
         '&&C.provider!=="asset3d")')
    r = ('const H=u.filter(C=>C.status==="done"&&C.final_video_path'
         '&&C.provider!=="asset3d"&&C.provider!=="sprite2d")')
    s = apply(s, a, r, "L2-renders-excl")

    # L-3/L-4: pickers « Existing render » — même exclusion.
    a = ('(Array.isArray(a)?a:[]).filter(l=>l.status==="done"'
         '&&l.final_video_path&&l.provider!=="asset3d")')
    r = ('(Array.isArray(a)?a:[]).filter(l=>l.status==="done"'
         '&&l.final_video_path&&l.provider!=="asset3d"'
         '&&l.provider!=="sprite2d")')
    s = apply(s, a, r, "L3-picker-excl")
    a = ('(Array.isArray(Y)?Y:[]).filter(q=>q.status==="done"'
         '&&q.final_video_path&&q.provider!=="asset3d")')
    r = ('(Array.isArray(Y)?Y:[]).filter(q=>q.status==="done"'
         '&&q.final_video_path&&q.provider!=="asset3d"'
         '&&q.provider!=="sprite2d")')
    s = apply(s, a, r, "L4-picker2-excl")

    # L-5: items TS + entrée Sprites dans T + favoris sprites.
    a = (',T={Images:[...t,...l],Renders:H,"3D":T3,Audio:F,'
         'Favoris:H.filter(z=>__dzFavHas(z.jobId))'
         '.concat(T3.filter(z=>__dzFavHas(z.jobId)))'
         '.concat([...t,...l].filter(z=>z&&z.name&&__dzFavImgHas(z.name)))}')
    r = (TS_ITEMS +
         ',T={Images:[...t,...l],Renders:H,"3D":T3,Sprites:TS,Audio:F,'
         'Favoris:H.filter(z=>__dzFavHas(z.jobId))'
         '.concat(T3.filter(z=>__dzFavHas(z.jobId)))'
         '.concat(TS.filter(z=>__dzFavHas(z.jobId)))'
         '.concat([...t,...l].filter(z=>z&&z.name&&__dzFavImgHas(z.name)))}')
    s = apply(s, a, r, "L5-items-tab")

    # L-6: branche de vignette sprite2d, insérée avant celle des 3D.
    a = (':C.url&&C.kind==="asset3d"?r.jsxs("div",{style:{width:"100%",'
         'height:120,background:"#02060d",position:"relative",'
         'overflow:"hidden"},children:[r.jsx("img",{src:C.thumb,alt:C.name,'
         'onError:')
    s = apply(s, a, GRID_SPRITE + a, "L6-grid-sprite")

    # L-7: actions du modal — Sheet PNG nommé, ZIP pack Unity,
    #      « → Sprite Lab » sur renders et images.
    a = ('r.jsx("a",{href:m.url,download:m.kind==="asset3d"?m.name+".glb"'
         ':m.name,style:{textDecoration:"none"},children:r.jsx(K,'
         '{variant:"outline",size:"sm",icon:"download",'
         'children:"Download"})}),')
    r = ('r.jsx("a",{href:m.url,download:m.kind==="asset3d"?m.name+".glb"'
         ':m.kind==="sprite2d"?m.name+".png":m.name,'
         'style:{textDecoration:"none"},children:r.jsx(K,'
         '{variant:"outline",size:"sm",icon:"download",'
         'children:m.kind==="sprite2d"?"Sheet PNG":"Download"})}),'
         'm.kind==="sprite2d"&&r.jsx("a",{href:m.zip,download:m.name+".zip",'
         'style:{textDecoration:"none"},children:r.jsx(K,'
         '{variant:"outline",size:"sm",icon:"download",'
         'children:"ZIP + Unity"})}),'
         'm.kind==="render"&&m.jobId&&r.jsx(K,{variant:"ghost",size:"sm",'
         'onClick:()=>{y(null);__dzToSpriteLab({kind:"job",job_id:m.jobId,'
         'label:m.name})},children:"→ Sprite Lab"}),'
         'm.kind==="image"&&r.jsx(K,{variant:"ghost",size:"sm",'
         'onClick:()=>{y(null);__dzToSpriteLab({kind:"image",'
         'filename:m.name})},children:"→ Sprite Lab"}),')
    s = apply(s, a, r, "L7-modal-actions")

    # L-8: « Rouvrir dans Studio » n'a pas de sens pour un sheet.
    a = ('m.jobId&&m.kind!=="asset3d"&&r.jsx(K,{variant:"ghost",size:"sm",'
         'icon:"flow",onClick:()=>__dzReopenStudio(m.jobId),'
         'children:"Rouvrir dans Studio"})')
    r = ('m.jobId&&m.kind!=="asset3d"&&m.kind!=="sprite2d"&&r.jsx(K,'
         '{variant:"ghost",size:"sm",icon:"flow",'
         'onClick:()=>__dzReopenStudio(m.jobId),'
         'children:"Rouvrir dans Studio"})')
    s = apply(s, a, r, "L8-no-reopen")

    # L-9: rename des sprites via renameJob (comme les 3D).
    a = ('m.jobId&&m.kind==="asset3d"&&r.jsx(K,{variant:"ghost",size:"sm",'
         'onClick:()=>{var nn=window.prompt("Rename asset:",m.name);')
    r = ('m.jobId&&(m.kind==="asset3d"||m.kind==="sprite2d")&&r.jsx(K,'
         '{variant:"ghost",size:"sm",'
         'onClick:()=>{var nn=window.prompt("Rename asset:",m.name);')
    s = apply(s, a, r, "L9-rename")

    # L-10: viewer du modal.
    a = 'm.kind==="asset3d"?r.jsx("model-viewer",{'
    r = VIEWER_SPRITE + a
    s = apply(s, a, r, "L10-viewer")

    # L-11: helper de hand-off (module scope, à côté de __dzReopenStudio).
    a = 'function __dzReopenStudio(id){'
    r = ('function __dzToSpriteLab(src){try{window.__dzSpriteSource=src}'
         'catch(e){}window.dispatchEvent(new CustomEvent("deepotus:navigate",'
         '{detail:{view:"assets3d",subtab:"sprites",source:src}}))}'
         'function __dzReopenStudio(id){')
    s = apply(s, a, r, "L11-handoff-helper")

    # L-12: hub — refs + postSrc + relais sur l'event assets-subtab.
    a = ('function DzGameAssetsHub({variant:e}){var ts=x.useState(function()'
         '{var t=null;try{t=window.__dzSubtab;delete window.__dzSubtab}'
         'catch(err){}return t==="sprites"?"sprites":"3d"}),tab=ts[0],'
         'setTab=ts[1];x.useEffect(function(){function h(ev){var d='
         '(ev&&ev.detail)||{};if(d.subtab==="sprites"||d.subtab==="3d")'
         'setTab(d.subtab)}')
    r = ('function DzGameAssetsHub({variant:e}){var ts=x.useState(function()'
         '{var t=null;try{t=window.__dzSubtab;delete window.__dzSubtab}'
         'catch(err){}return t==="sprites"?"sprites":"3d"}),tab=ts[0],'
         'setTab=ts[1];'
         'var ifr=x.useRef(null),ifrOk=x.useRef(!1);'
         'function postSrc(){var s2=null;'
         'try{s2=window.__dzSpriteSource}catch(e9){}'
         'if(!s2)return;'
         'if(ifrOk.current&&ifr.current&&ifr.current.contentWindow){'
         'try{ifr.current.contentWindow.postMessage('
         '{type:"spritelab:source",source:s2},"*");'
         'window.__dzSpriteSource=null}catch(e8){}}}'
         'x.useEffect(function(){function h(ev){var d=(ev&&ev.detail)||{};'
         'if(d.subtab==="sprites"||d.subtab==="3d")setTab(d.subtab);'
         'if(d.subtab==="sprites")setTimeout(postSrc,0)}')
    s = apply(s, a, r, "L12-hub-postsrc")

    # L-13: iframe — ref + onLoad (poste la source en attente une fois
    #       la page chargée ; reset du flag quand l'iframe est démontée).
    a = (':r.jsx("iframe",{src:"/spritelab/",title:"Sprite Lab",'
         'style:{flex:1,width:"100%",minHeight:"calc(100vh - 110px)",'
         'border:"0",marginTop:10,background:"var(--bg-base)"}},"p2d")]})}')
    r = (':r.jsx("iframe",{src:"/spritelab/",title:"Sprite Lab",'
         'ref:function(el){ifr.current=el;if(!el)ifrOk.current=!1},'
         'onLoad:function(){ifrOk.current=!0;postSrc()},'
         'style:{flex:1,width:"100%",minHeight:"calc(100vh - 110px)",'
         'border:"0",marginTop:10,background:"var(--bg-base)"}},"p2d")]})}')
    s = apply(s, a, r, "L13-iframe-onload")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (Library Sprites + hand-off). Size:",
          BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
