# -*- coding: utf-8 -*-
"""Assert-guarded patcher : chantier CR-2 — vraies vignettes dans le nœud
Concatenate (une par entrée connectée, dans l'ordre des slots).

BASELINE : bundle POST-patch navrail (dernier patch en date).
Backup dédié : .js.bak_concatthumbs (état juste avant CE patch).

Constat : le build d'origine contient déjà __dzConcatStrip/__dzThumbUrl, mais
__dzThumbUrl ne résout que Seedance→image, Image.filename et HeyGen.avatarImg.
Les Existing render (props.jobId) et tous les nœuds image du patch imagegen
(ImageGen, RemoveBG, Upscale, CropFormat, ImageEdit, Variations, plus
NewsIllustration) tombent sur une tuile unie sombre — invisibles sur le
canvas, d'où « les emplacements ne se peuplent pas ».

Le patch :
- __dzThumbUrl : branche générique dzIsImgNode (tout nœud image avec
  filename) en plus des branches existantes ;
- __dzConcatStrip : grille (≤3 colonnes, 2 rangées à partir de 4 sources),
  tuiles numérotées 1..N (ordre de montage = ordre des ports a..f),
  <video preload=metadata> pour les sources à jobId (Existing render),
  placeholder pellicule pour les sources encore vides (ex. Seedance sans
  image) ; data-dzslot pour la QA.

Run : python scripts/patch_bundle_concatthumbs.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_concatthumbs")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ---------------------------------------------------------------------------
# T1 : __dzThumbUrl — résolution élargie (nœuds image du patch imagegen).
# ---------------------------------------------------------------------------
A1 = ('function __dzThumbUrl(g){if(!g)return null;var k=0;'
      'while(g&&g.type==="AvatarMaster"&&k++<6)g=Wt(__dzG,g.id,"in");'
      'if(!g)return null;'
      'if(g.type==="Seedance"){var img=Wt(__dzG,g.id,"image");'
      'return img&&img.props&&img.props.filename?'
      'D.imageUrl(img.props.filename):null}'
      'if(g.type==="Image")return g.props&&g.props.filename?'
      'D.imageUrl(g.props.filename):null;'
      'if(g.type==="HeyGenAvatar")return g.props&&g.props.avatarImg||null;'
      'return null}')
R1 = ('function __dzThumbUrl(g){if(!g)return null;var k=0;'
      'while(g&&g.type==="AvatarMaster"&&k++<6)g=Wt(__dzG,g.id,"in");'
      'if(!g)return null;'
      'if(g.type==="Seedance"){var img=Wt(__dzG,g.id,"image");'
      'return img&&img.props&&img.props.filename?'
      'D.imageUrl(img.props.filename):null}'
      'if(typeof dzIsImgNode==="function"&&dzIsImgNode(g)||g.type==="Image"||'
      'g.type==="NewsIllustration")return g.props&&g.props.filename?'
      'D.imageUrl(g.props.filename):null;'
      'if(g.type==="HeyGenAvatar")return g.props&&g.props.avatarImg||null;'
      'return null}')

# ---------------------------------------------------------------------------
# T2 : __dzConcatStrip — grille numérotée, vidéos jobId, placeholders.
# ---------------------------------------------------------------------------
A2 = ('function __dzConcatStrip(e){var g=__dzG;if(!g)return r.jsx("div",'
      '{style:{width:"100%",height:"100%",background:'
      '"linear-gradient(135deg,#053040,#02060d)"}});'
      'var srcs=["a","b","c","d","e","f"].map(function(pt){'
      'return Wt(g,e.id,pt)}).filter(Boolean);'
      'if(!srcs.length)return r.jsx("div",{style:{width:"100%",height:"100%",'
      'background:"linear-gradient(135deg,#053040 0%,#02060d 100%)",'
      'display:"flex",alignItems:"center",justifyContent:"center",'
      'color:"#00e5ff",opacity:.5},children:r.jsx(X,{name:"film",size:24})});'
      'return r.jsx("div",{style:{width:"100%",height:"100%",display:"flex",'
      'gap:1,background:"#000"},children:srcs.map(function(nd,ix){'
      'var u=__dzThumbUrl(nd);return r.jsx("div",{style:{flex:1,minWidth:0,'
      'backgroundImage:u?"url("+u+")":"none",backgroundSize:"cover",'
      'backgroundPosition:"center",backgroundColor:u?"#000":"#0b1a26"}},ix)'
      '})})}')
R2 = ('function __dzConcatStrip(e){var g=__dzG;if(!g)return r.jsx("div",'
      '{style:{width:"100%",height:"100%",background:'
      '"linear-gradient(135deg,#053040,#02060d)"}});'
      'var srcs=["a","b","c","d","e","f"].map(function(pt){'
      'return Wt(g,e.id,pt)}).filter(Boolean);'
      'if(!srcs.length)return r.jsx("div",{style:{width:"100%",height:"100%",'
      'background:"linear-gradient(135deg,#053040 0%,#02060d 100%)",'
      'display:"flex",alignItems:"center",justifyContent:"center",'
      'color:"#00e5ff",opacity:.5},children:r.jsx(X,{name:"film",size:24})});'
      'var cols=Math.min(srcs.length,3);'
      'return r.jsx("div",{style:{width:"100%",height:"100%",display:"grid",'
      'gridTemplateColumns:"repeat("+cols+",1fr)",gridAutoRows:"1fr",gap:2,'
      'background:"#000",padding:2},children:srcs.map(function(nd,ix){'
      'var u=__dzThumbUrl(nd);var jid=nd.props&&nd.props.jobId;var inner;'
      'if(u)inner=r.jsx("div",{style:{position:"absolute",inset:0,'
      'backgroundImage:"url("+u+")",backgroundSize:"cover",'
      'backgroundPosition:"center"}});'
      'else if(jid)inner=r.jsx("video",{src:D.jobVideoUrl(jid),muted:!0,'
      'preload:"metadata",playsInline:!0,'
      'onError:function(ev){ev.currentTarget.style.display="none"},'
      'style:{position:"absolute",inset:0,width:"100%",height:"100%",'
      'objectFit:"cover",background:"#000"}});'
      'else inner=r.jsx("div",{style:{position:"absolute",inset:0,'
      'background:"linear-gradient(135deg,#053040,#02060d)",display:"flex",'
      'alignItems:"center",justifyContent:"center",color:"#00e5ff",'
      'opacity:.55},children:r.jsx(X,{name:"film",size:12})});'
      'return r.jsxs("div",{"data-dzslot":ix+1,style:{position:"relative",'
      'minWidth:0,minHeight:0,borderRadius:3,overflow:"hidden",'
      'backgroundColor:"#0b1a26"},children:[inner,'
      'r.jsx("span",{className:"mono",style:{position:"absolute",top:2,'
      'left:2,minWidth:12,padding:"0 3px",borderRadius:3,fontSize:8,'
      'lineHeight:"12px",textAlign:"center",background:"#02060dcc",'
      'color:"var(--cyan)",fontWeight:700,pointerEvents:"none"},'
      'children:ix+1})]},ix)})})}')


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")
    s = apply(s, A1, R1, "T1-thumburl")
    s = apply(s, A2, R2, "T2-strip")
    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK (concatthumbs)")


if __name__ == "__main__":
    main()
