# -*- coding: utf-8 -*-
"""Assert-guarded patcher : chantier CR-3 — les ancres du nœud Spatial compose
reflètent les slots exacts du template sélectionné, et les templates
séquentiels (Montage Film) gagnent un compteur de scènes + transitions par
jonction dans le panneau droit.

BASELINE : bundle POST-patch concatthumbs.
Backup dédié : .js.bak_spatialports (état juste avant CE patch).

Constat (cause racine) : le nœud exposait 4 ports statiques (reel/avatar/
brand/bg) et dzCompose mappait TOUTES les régions vidéo non-heygen sur le
seul port « reel » — pour tpl_montage_film, les 5 clips lisaient la même
source ; impossible de chaîner des clips différents.

Architecture :
- Me.SpatialCompose garde des ports STATIQUES (superset reel/avatar/s3..s6 av
  + brand/bg image) pour rester compatible avec les graphes existants ;
- dzNodeInPorts(node) calcule le SOUS-ENSEMBLE visible, ordonné et relabelisé
  d'après template.regions (via cache __dzTplList) : n-ième région vidéo →
  reel, s3, s4, s5, s6 (la région default_provider=heygen prend « avatar »),
  n-ième région image → brand, bg ; slot_label affiché sur le port ;
- qi() (géométrie des arêtes) accepte le nœud en 4e argument (déjà présent
  mais inutilisé) et suit le sous-ensemble visible ;
- dzCompose mappe région→port par la MÊME fonction (dzSpatialSlots) — fini le
  « tout sur reel » ; erreur claire si un montage a < 2 clips branchés ;
- panneau Layout : pour render_mode=sequential, compteur « Scènes » (2..maxN)
  + un sélecteur de transition par jonction (cut/crossfade/dissolve/
  fade to black/glitch/slide/flash — noms acceptés par _XFADE backend),
  stockés dans props.scenes / props.transitions et appliqués via le template
  inline de dzCompose.

Run : python scripts/patch_bundle_spatialports.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_spatialports")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ── S1 : superset de ports + props scenes/transitions ──────────────────────
A1 = ('SpatialCompose:{cat:"compose",title:"Spatial compose",'
      'desc:"layout 9:16 regions",inPorts:[{id:"reel",type:"av"},'
      '{id:"avatar",type:"av"},{id:"brand",type:"image"},'
      '{id:"bg",type:"image"}],outPorts:[{id:"out",type:"av"}],'
      'props:{templateId:"tpl_news_reel",useAsMaster:!1,tailPadS:.4}}')
R1 = ('SpatialCompose:{cat:"compose",title:"Spatial compose",'
      'desc:"layout 9:16 regions",inPorts:[{id:"reel",type:"av"},'
      '{id:"avatar",type:"av"},{id:"s3",type:"av"},{id:"s4",type:"av"},'
      '{id:"s5",type:"av"},{id:"s6",type:"av"},{id:"brand",type:"image"},'
      '{id:"bg",type:"image"}],outPorts:[{id:"out",type:"av"}],'
      'props:{templateId:"tpl_news_reel",useAsMaster:!1,tailPadS:.4,'
      'scenes:0,transitions:[]}}')

# ── S2 : helpers module-scope (cache templates + calcul des ports) ─────────
HELPERS = (
    'var __dzTplList=null,__dzTplFetch=0;'
    'function __dzTplGet(id){'
    'if(!__dzTplList&&!__dzTplFetch){__dzTplFetch=1;'
    'try{D.listLayoutTemplates().then(function(L1){'
    '__dzTplList=Array.isArray(L1)?L1:(L1&&L1.templates)||[]})'
    '.catch(function(){__dzTplFetch=0})}catch(_e){__dzTplFetch=0}}'
    'return(__dzTplList||[]).find(function(t1){return t1&&t1.id===id})||null}'
    'function dzSpatialSlots(tpl,props){'
    'var regs=(tpl&&tpl.regions)||[],vids=[],imgs=[],i1;'
    'for(i1=0;i1<regs.length;i1++){var rg=regs[i1];'
    'rg.type==="video_slot"?vids.push(rg):rg.type==="image_slot"&&imgs.push(rg)}'
    'var seq=!!(tpl&&tpl.render_mode==="sequential"),maxN=vids.length,'
    'n=maxN;'
    'if(seq){n=Math.max(2,Math.min(maxN||2,Number(props&&props.scenes)||2));'
    'vids=vids.slice(0,n)}'
    'var pool=["reel","s3","s4","s5","s6"],ports=[],hey=null;'
    'for(i1=0;i1<vids.length;i1++)'
    'if(vids[i1].default_provider==="heygen"&&!hey)hey=vids[i1];'
    'for(i1=0;i1<vids.length;i1++){var rg2=vids[i1],'
    'pid=rg2===hey?"avatar":pool.shift();'
    'pid&&ports.push({id:pid,type:"av",'
    'label:rg2.slot_label||rg2.slot_name,slot:rg2.slot_name})}'
    'var ipool=["brand","bg"];'
    'for(i1=0;i1<imgs.length&&i1<2;i1++)'
    'ports.push({id:ipool[i1],type:"image",'
    'label:imgs[i1].slot_label||imgs[i1].slot_name,slot:imgs[i1].slot_name});'
    'return{ports:ports,seq:seq,maxN:maxN,n:n}}'
    'function dzNodeInPorts(nd){'
    'if(!nd||nd.type!=="SpatialCompose")return null;'
    'var tpl=__dzTplGet((nd.props&&nd.props.templateId)||"tpl_news_reel");'
    'if(!tpl)return null;'
    'var ps=dzSpatialSlots(tpl,nd.props||{}).ports;'
    'return ps.length?ps:null}'
)
A2 = 'function ud({side:e,port:t,index:n,onPress:o,onRelease:i}){'
R2 = HELPERS + A2

# ── S3 : le port affiche son label de slot ─────────────────────────────────
A3 = 'children:[t.id,r.jsxs("span",{style:{color:s,opacity:.6},children:[" · ",t.type]})]'
R3 = 'children:[t.label||t.id,r.jsxs("span",{style:{color:s,opacity:.6},children:[" · ",t.type]})]'

# ── S4 : la carte rend le sous-ensemble template-driven ────────────────────
A4 = ('(e.type==="Concatenate"?u.inPorts.slice(0,Math.max(2,Math.min(6,'
      '(e.props&&e.props.sourceCount)||3))):u.inPorts).map((g,k)=>'
      'r.jsx(ud,{side:"in",port:g,index:k,onPress:c=>s(e.id,"in",g,c),'
      'onRelease:c=>a(e.id,"in",g,c)},g.id))')
R4 = ('(e.type==="Concatenate"?u.inPorts.slice(0,Math.max(2,Math.min(6,'
      '(e.props&&e.props.sourceCount)||3))):'
      '(typeof dzNodeInPorts==="function"&&dzNodeInPorts(e))||u.inPorts)'
      '.map((g,k)=>'
      'r.jsx(ud,{side:"in",port:g,index:k,onPress:c=>s(e.id,"in",g,c),'
      'onRelease:c=>a(e.id,"in",g,c)},g.id))')

# ── S5 : qi devient node-aware (4e argument déjà libre) ────────────────────
A5 = ('function qi(e,t,n,o){const i=Me[e],a=(t==="in"?i.inPorts:i.outPorts)'
      '.findIndex(u=>u.id===n);')
R5 = ('function qi(e,t,n,o){const i=Me[e];var _lst=t==="in"?i.inPorts:'
      'i.outPorts;if(o&&t==="in"&&typeof dzNodeInPorts==="function"){'
      'var _dl=dzNodeInPorts(o);_dl&&(_lst=_dl)}'
      'const a=_lst.findIndex(u=>u.id===n);')

# ── S6/S7 : les appels passent le nœud ─────────────────────────────────────
A6 = 'const L=qi(W.type,"out",R.fromPort),J=qi(S.type,"in",R.toPort)'
R6 = 'const L=qi(W.type,"out",R.fromPort,W),J=qi(S.type,"in",R.toPort,S)'
A7 = 'const W=qi(R.type,P.side,P.fromPort.id),'
R7 = 'const W=qi(R.type,P.side,P.fromPort.id,R),'

# ── S8 : dzCompose — mapping région→port positionnel ───────────────────────
A8 = '''  var hgSlot=null;
  for(var ri=0;ri<tpl.regions.length;ri++){
    var r=tpl.regions[ri];
    if(r.type==="video_slot"){
      var port=r.default_provider==="heygen"?"avatar":"reel",nd=Wt(e,l.id,port),sp=nd&&srcFor(nd);
      if(sp&&sp.__hg)hgSlot={name:r.slot_name,node:sp.__hg};
      else if(sp)slots[r.slot_name]=sp
    }else if(r.type==="image_slot"){
      for(var pp=0,pl=["brand","bg"];pp<pl.length;pp++){var nd2=Wt(e,l.id,pl[pp]),s2=nd2&&srcFor(nd2);if(s2&&!s2.__hg){slots[r.slot_name]=s2;break}}
    }
  }'''
R8 = '''  var hgSlot=null,__sp=dzSpatialSlots(tpl,l.props||{}),__regionPort={},__filled=0;
  for(var __pi=0;__pi<__sp.ports.length;__pi++)__regionPort[__sp.ports[__pi].slot]=__sp.ports[__pi].id;
  for(var ri=0;ri<tpl.regions.length;ri++){
    var r=tpl.regions[ri];
    if(r.type!=="video_slot"&&r.type!=="image_slot")continue;
    var port=__regionPort[r.slot_name];
    if(!port)continue;
    var nd=Wt(e,l.id,port),sp=nd&&srcFor(nd);
    if(sp&&sp.__hg)hgSlot={name:r.slot_name,node:sp.__hg};
    else if(sp){slots[r.slot_name]=sp;if(r.type==="video_slot")__filled++}
  }
  if(__sp.seq&&__filled+(hgSlot?1:0)<2)errs.push("Montage : branche au moins 2 clips sur les ancres Clip (actuellement "+(__filled+(hgSlot?1:0))+").");'''

# ── S9 : transitions par jonction appliquées au template inline ────────────
A9 = 'var regions=tpl.regions.slice(),zi=60,ovc={};'
R9 = ('var regions=tpl.regions.slice(),zi=60,ovc={};'
      'var __trMod=!1;'
      'if(__sp.seq){var __trs=(l.props&&l.props.transitions)||[],__vi=0;'
      'regions=regions.map(function(rg3){'
      'if(rg3.type!=="video_slot")return rg3;'
      'var k4=__vi++;'
      'if(k4>0&&__trs[k4-1]&&__trs[k4-1].type){__trMod=!0;'
      'return Object.assign({},rg3,{transition:{type:__trs[k4-1].type,'
      'duration_s:Number(__trs[k4-1].duration_s)||.5}})}'
      'return rg3})}')

A10 = 'var hasMods=regions.length!==tpl.regions.length||loud!=null||!!music;'
R10 = ('var hasMods=regions.length!==tpl.regions.length||loud!=null||'
       '!!music||__trMod;')

# ── S11 : panneau Layout — compteur de scènes + transitions ────────────────
A11 = ('r.jsx(O,{children:r.jsx(Ze,{checked:e.useAsMaster,'
       'onChange:m=>t("useAsMaster",m),'
       'label:"Avatar slot is duration master"})})')
R11 = ('(i&&i.render_mode==="sequential"?(()=>{'
       'const vN=l.filter(m2=>m2.type==="video_slot").length||5,'
       'sc=Math.max(2,Math.min(vN,Number(e.scenes)||2)),'
       'trs=e.transitions||[],'
       'opts=[{value:"cut",label:"cut"},{value:"crossfade",label:"crossfade"},'
       '{value:"dissolve",label:"dissolve"},'
       '{value:"fadeblack",label:"fade to black"},'
       '{value:"glitch",label:"glitch"},{value:"slide",label:"slide"},'
       '{value:"flash",label:"flash"}];'
       'return r.jsxs(r.Fragment,{children:['
       'r.jsx(O,{children:r.jsx(Oe,{label:"Scènes",value:sc,min:2,max:vN,'
       'step:1,onChange:m=>t("scenes",m)})},"dzsc"),'
       '...Array.from({length:sc-1},(_,ti)=>r.jsx(O,'
       '{label:"Transition "+(ti+1)+" → "+(ti+2),'
       'children:r.jsx(re,{value:(trs[ti]&&trs[ti].type)||"crossfade",'
       'onChange:m=>{const a2=(e.transitions||[]).slice();'
       'a2[ti]={type:m,duration_s:.5};t("transitions",a2)},'
       'options:opts})},"dztr"+ti))]})})():null),'
       'r.jsx(O,{children:r.jsx(Ze,{checked:e.useAsMaster,'
       'onChange:m=>t("useAsMaster",m),'
       'label:"Avatar slot is duration master"})})')

# ── S12 : préchargement du cache templates au montage du Studio ────────────
A12 = '__dzG=o;return r.jsxs("div",{className:"dz-studio-grid"'
R12 = ('__dzG=o;try{__dzTplGet("tpl_news_reel")}catch(_e){}'
       'return r.jsxs("div",{className:"dz-studio-grid"')


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")
    s = apply(s, A1, R1, "S1-ports-superset")
    s = apply(s, A2, R2, "S2-helpers")
    s = apply(s, A3, R3, "S3-port-label")
    s = apply(s, A4, R4, "S4-card-subset")
    s = apply(s, A5, R5, "S5-qi-node-aware")
    s = apply(s, A6, R6, "S6-qi-edges")
    s = apply(s, A7, R7, "S7-qi-drag")
    s = apply(s, A8, R8, "S8-dzcompose-mapping")
    s = apply(s, A9, R9, "S9-transitions-inline")
    s = apply(s, A10, R10, "S10-hasmods")
    s = apply(s, A11, R11, "S11-panel-scenes")
    s = apply(s, A12, R12, "S12-prefetch")
    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK (spatialports)")


if __name__ == "__main__":
    main()
