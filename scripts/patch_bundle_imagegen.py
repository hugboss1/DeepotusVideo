# scripts/patch_bundle_imagegen.py
"""Assert-guarded patcher: nœuds de génération d'images du Studio (T2).

BASELINE: bundle POST-patch T1 (image_model_default / DzImageModel serveur).
Backup dédié: .js.bak_imagegen (état juste avant CE patch).

Ajoute au Studio:
- ImageGen    (gen)  : prompt → N images ; sélecteur de générateur
                       (/api/image-models), N générations → N nœuds Image
                       créés sur le canvas.
- ImageEdit   (gen)  : image + instruction → image (gpt-image / banana /
                       FLUX Kontext via /api/images/process).
- Variations  (gen)  : image → N variantes → N nœuds Image.
- RemoveBG    (edit) : détourage — méthode API cloud (fal) OU locale (rembg).
- Upscale     (edit) : IA (fal esrgan) ou simple (PIL local).
- CropFormat  (edit) : recadrage centré au ratio (local, gratuit).

Le compilateur de graphe (Mh) + la composition spatiale acceptent désormais
ces nœuds comme source d'image (Seedance, Animation, Compose, Montage).

Run: python scripts/patch_bundle_imagegen.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_imagegen")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ─────────────────────────── nouveaux nœuds (Me) ───────────────────────────
NEW_DEFS = (
    ',ImageGen:{cat:"gen",title:"Image gen",desc:"prompt → N images",'
    'inPorts:[{id:"prompt",type:"text"}],outPorts:[{id:"out",type:"image"}],'
    'props:{model:"",count:2,size:"portrait_16_9",prompt:"",filename:""}}'
    ',ImageEdit:{cat:"gen",title:"Image edit",desc:"image + instruction → image",'
    'inPorts:[{id:"in",type:"image"},{id:"prompt",type:"text"}],'
    'outPorts:[{id:"out",type:"image"}],'
    'props:{model:"",instruction:"",filename:""}}'
    ',Variations:{cat:"gen",title:"Variations",desc:"image → N variantes",'
    'inPorts:[{id:"in",type:"image"}],outPorts:[{id:"out",type:"image"}],'
    'props:{model:"",count:3,filename:""}}'
    ',RemoveBG:{cat:"edit",title:"Remove BG",desc:"détourage arrière-plan",'
    'inPorts:[{id:"in",type:"image"}],outPorts:[{id:"out",type:"image"}],'
    'props:{method:"api",filename:""}}'
    ',Upscale:{cat:"edit",title:"Upscale",desc:"agrandir ×2/×4",'
    'inPorts:[{id:"in",type:"image"}],outPorts:[{id:"out",type:"image"}],'
    'props:{mode:"ai",scale:2,filename:""}}'
    ',CropFormat:{cat:"edit",title:"Crop / format",desc:"recadrer au ratio",'
    'inPorts:[{id:"in",type:"image"}],outPorts:[{id:"out",type:"image"}],'
    'props:{ratio:"9:16",filename:""}}'
)

# ──────────────── helpers + panneaux d'inspecteur (module scope) ────────────
TEXTAREA_STYLE = (
    'style:{width:"100%",padding:8,background:"var(--bg-base)",'
    'border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",'
    'color:"var(--ink-strong)",fontFamily:"var(--f-ui)",fontSize:12,'
    'resize:"vertical"}'
)

HELPERS = (
    'function dzIsImgNode(n){return!!(n&&["Image","NewsIllustration","ImageGen",'
    '"RemoveBG","Upscale","CropFormat","ImageEdit","Variations"]'
    '.indexOf(n.type)>=0)}'
    'function dzInImg(g,id,port){var n=Wt(g,id,port||"in");'
    'return n&&dzIsImgNode(n)&&n.props&&n.props.filename?n.props.filename:null}'
    'function DzImgModelSel({value,onChange}){var ms=x.useState(null),mm=ms[0],'
    'setMM=ms[1];x.useEffect(function(){var on=!0;fetch("/api/image-models")'
    '.then(function(r2){return r2.ok?r2.json():null})'
    '.then(function(d){on&&setMM(d||{models:[]})})'
    '.catch(function(){setMM({models:[]})});return function(){on=!1}},[]);'
    'if(!mm)return null;'
    'var opts=[{value:"",label:"Défaut ("+(mm.default||"flux")+")"}]'
    '.concat((mm.models||[]).map(function(m){return{value:m.id,label:m.label}}));'
    'return r.jsx(re,{value:value||"",onChange:onChange,options:opts})}'
    'function DzImgPrev({fn,checker}){if(!fn)return null;'
    'return r.jsx("div",{style:{marginTop:6,aspectRatio:"9 / 16",'
    'background:checker?"repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 0 0/16px 16px":"#02060d",'
    'border:"1px solid var(--stroke)",borderRadius:8,overflow:"hidden"},'
    'children:r.jsx("img",{src:D.imageUrl(fn),alt:fn,'
    'style:{width:"100%",height:"100%",objectFit:"contain"}})})}'
    'function dzSpawnImages(node,files,spawn){if(!spawn||!files.length)return;'
    'var base=Date.now().toString(36);'
    'spawn(files.map(function(f,ix){return{id:"gimg"+base+ix,type:"Image",'
    'x:node.x+250,y:node.y+ix*150,props:{filename:f}}}))}'

    # ---- panneau ImageGen -------------------------------------------------
    'function DzImageGenPanel({node,p,set,graph,spawn}){'
    'var bs=x.useState(!1),busy=bs[0],setB=bs[1],'
    'es=x.useState(""),msg=es[0],setMsg=es[1];'
    'var pn=Wt(graph,node.id,"prompt"),'
    'ptext=((pn&&pn.props&&pn.props.value)||"").trim(),'
    'eff=ptext||(p.prompt||"").trim();'
    'async function run(){if(busy)return;'
    'if(!eff){setMsg("Branche un nœud Prompt/Text, ou écris un prompt ci-dessous.");return}'
    'var total=Math.max(1,Math.min(8,Number(p.count)||1));'
    'setB(!0);setMsg("Génération de "+total+" image(s)…");'
    'var files=[];'
    'try{while(files.length<total){var take=Math.min(4,total-files.length);'
    'var d=await D.generateImage(eff,take,p.size||"portrait_16_9",p.model||"");'
    'if(!(d&&d.images&&d.images.length))throw new Error(String((d&&d.error)||"génération échouée").slice(0,160));'
    'files=files.concat(d.images)}}'
    'catch(err){setB(!1);setMsg("Échec: "+String(err&&err.message||err).slice(0,160));return}'
    'setB(!1);set("filename",files[0]);dzSpawnImages(node,files,spawn);'
    'setMsg(files.length+" image(s) générée(s) → nœuds Image créés sur le canvas.")}'
    'return r.jsxs(ie,{label:"Image gen",children:['
    'r.jsx(O,{label:"Générateur",hint:"Modèles selon les clés API des Réglages.",'
    'children:r.jsx(DzImgModelSel,{value:p.model,onChange:function(v){set("model",v)}})},"g"),'
    'r.jsx(O,{children:r.jsx(Oe,{label:"Générations",value:Number(p.count)||1,'
    'min:1,max:8,step:1,onChange:function(v){set("count",v)}})},"n"),'
    'r.jsx(O,{label:"Cadre",children:r.jsx(re,{value:p.size||"portrait_16_9",'
    'onChange:function(v){set("size",v)},options:['
    '{value:"portrait_16_9",label:"Portrait 9:16"},'
    '{value:"square_hd",label:"Carré 1:1"},'
    '{value:"landscape_16_9",label:"Paysage 16:9"}]})},"s"),'
    'ptext?r.jsx(O,{label:"Prompt (nœud connecté)",'
    'children:r.jsx("div",{style:{fontSize:11,color:"var(--ink-soft)",'
    'lineHeight:1.4,maxHeight:72,overflow:"hidden"},children:ptext})},"p")'
    ':r.jsx(O,{label:"Prompt",hint:"Ou branche un nœud Prompt/Text sur l\'entrée.",'
    'children:r.jsx("textarea",{value:p.prompt||"",'
    'onChange:function(ev){set("prompt",ev.target.value)},rows:3,' + TEXTAREA_STYLE + '})},"p"),'
    'r.jsx(K,{variant:"primary",size:"sm",icon:"sparkle",glow:!0,disabled:busy,'
    'onClick:run,style:{width:"100%",marginTop:4},'
    'children:busy?"Génération…":"Générer"},"b"),'
    'msg?r.jsx("div",{style:{fontSize:10.5,'
    'color:msg.indexOf("Échec")===0?"var(--red)":"var(--ink-soft)",'
    'marginTop:6},children:msg},"m"):null,'
    'r.jsx(DzImgPrev,{fn:p.filename},"v")]})}'

    # ---- panneau générique post-traitements -------------------------------
    'function DzImgProcPanel({node,p,set,graph,spawn,kind}){'
    'var bs=x.useState(!1),busy=bs[0],setB=bs[1],'
    'es=x.useState(""),msg=es[0],setMsg=es[1];'
    'var src=dzInImg(graph,node.id,"in");'
    'function run(){if(busy)return;'
    'if(!src){setMsg("Branche une image en entrée (nœud Image, Image gen…).");return}'
    'var body={filename:src},spawnMany=!1;'
    'if(kind==="removebg"){body.op="remove-bg";body.method=p.method||"api"}'
    'else if(kind==="upscale"){body.op="upscale";body.mode=p.mode||"ai";body.scale=Number(p.scale)||2}'
    'else if(kind==="crop"){body.op="crop";body.ratio=p.ratio||"9:16"}'
    'else if(kind==="edit"){var tn=Wt(graph,node.id,"prompt");'
    'var ins=((tn&&tn.props&&tn.props.value)||p.instruction||"").trim();'
    'if(!ins){setMsg("Écris une instruction (ou branche un nœud Prompt).");return}'
    'body.op="edit";body.prompt=ins;body.model=p.model||""}'
    'else if(kind==="variations"){body.op="variations";'
    'body.n=Math.max(1,Math.min(4,Number(p.count)||3));body.model=p.model||"";spawnMany=!0}'
    'setB(!0);setMsg("Traitement…");'
    'D.postJson("/images/process",body).then(function(d){setB(!1);'
    'var im=(d&&d.images)||[];'
    'if(!im.length){setMsg("Échec: "+String((d&&d.error)||"").slice(0,160));return}'
    'set("filename",im[0]);if(spawnMany)dzSpawnImages(node,im,spawn);'
    'setMsg(spawnMany?im.length+" variante(s) → nœuds Image créés.":"OK → "+im[0])})'
    '.catch(function(e2){setB(!1);setMsg("Échec: "+String(e2&&e2.message||e2).slice(0,160))})}'
    'var rows=[];'
    'if(kind==="removebg")rows.push(r.jsx(O,{label:"Méthode",'
    'hint:"API = fal.ai (qualité, coût léger). Local = rembg si installé dans le runtime.",'
    'children:r.jsx(re,{value:p.method||"api",onChange:function(v){set("method",v)},'
    'options:[{value:"api",label:"API cloud (fal)"},{value:"local",label:"Local (rembg)"}]})},"m"));'
    'if(kind==="upscale"){rows.push(r.jsx(O,{label:"Mode",'
    'hint:"IA = fal esrgan. Simple = redimensionnement local gratuit.",'
    'children:r.jsx(re,{value:p.mode||"ai",onChange:function(v){set("mode",v)},'
    'options:[{value:"ai",label:"IA (esrgan)"},{value:"simple",label:"Simple (local)"}]})},"mo"));'
    'rows.push(r.jsx(O,{children:r.jsx(Oe,{label:"Facteur",value:Number(p.scale)||2,'
    'min:2,max:4,step:1,unit:"×",onChange:function(v){set("scale",v)}})},"sc"))}'
    'if(kind==="crop")rows.push(r.jsx(O,{label:"Ratio cible",'
    'children:r.jsx(re,{value:p.ratio||"9:16",onChange:function(v){set("ratio",v)},'
    'options:["9:16","1:1","16:9","4:5","3:4"]})},"ra"));'
    'if(kind==="edit"){rows.push(r.jsx(O,{label:"Générateur",'
    'children:r.jsx(DzImgModelSel,{value:p.model,onChange:function(v){set("model",v)}})},"md"));'
    'rows.push(r.jsx(O,{label:"Instruction",hint:"Ou branche un nœud Prompt sur l\'entrée prompt.",'
    'children:r.jsx("textarea",{value:p.instruction||"",'
    'onChange:function(ev){set("instruction",ev.target.value)},rows:3,' + TEXTAREA_STYLE + '})},"in"))}'
    'if(kind==="variations"){rows.push(r.jsx(O,{label:"Générateur",'
    'children:r.jsx(DzImgModelSel,{value:p.model,onChange:function(v){set("model",v)}})},"md"));'
    'rows.push(r.jsx(O,{children:r.jsx(Oe,{label:"Variantes",value:Number(p.count)||3,'
    'min:1,max:4,step:1,onChange:function(v){set("count",v)}})},"ct"))}'
    'var titles={removebg:"Retirer l\'arrière-plan",upscale:"Upscale",'
    'crop:"Recadrage / format",edit:"Édition par prompt",variations:"Variations"};'
    'return r.jsxs(ie,{label:titles[kind]||kind,children:['
    'r.jsx(O,{label:"Image d\'entrée",children:r.jsx("div",{className:"mono",'
    'style:{fontSize:10.5,color:src?"var(--ink-strong)":"var(--amber)"},'
    'children:src||"— rien de branché sur l\'entrée —"})},"i")]'
    '.concat(rows).concat(['
    'r.jsx(K,{variant:"primary",size:"sm",icon:"sparkle",glow:!0,disabled:busy,'
    'onClick:run,style:{width:"100%",marginTop:4},'
    'children:busy?"Traitement…":kind==="variations"?"Générer les variantes":"Appliquer"},"bt"),'
    'msg?r.jsx("div",{style:{fontSize:10.5,'
    'color:msg.indexOf("Échec")===0?"var(--red)":"var(--ink-soft)",'
    'marginTop:6},children:msg},"ms"):null,'
    'r.jsx(DzImgPrev,{fn:p.filename,checker:kind==="removebg"},"pv")])})}'
)

YH_BRANCHES = (
    'return e.type==="ImageGen"?r.jsx(DzImageGenPanel,{node:e,p:n,set:o,graph:g,spawn:sp})'
    ':e.type==="RemoveBG"?r.jsx(DzImgProcPanel,{node:e,p:n,set:o,graph:g,spawn:sp,kind:"removebg"})'
    ':e.type==="Upscale"?r.jsx(DzImgProcPanel,{node:e,p:n,set:o,graph:g,spawn:sp,kind:"upscale"})'
    ':e.type==="CropFormat"?r.jsx(DzImgProcPanel,{node:e,p:n,set:o,graph:g,spawn:sp,kind:"crop"})'
    ':e.type==="ImageEdit"?r.jsx(DzImgProcPanel,{node:e,p:n,set:o,graph:g,spawn:sp,kind:"edit"})'
    ':e.type==="Variations"?r.jsx(DzImgProcPanel,{node:e,p:n,set:o,graph:g,spawn:sp,kind:"variations"})'
    ':e.type==="MusicTrack"?'
)


def main():
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # G-1: nouveaux nœuds dans le registre Me (juste avant _h).
    a = 'name:"tweet_2026-05-20",voiceMode:"passthrough"}}},_h=['
    r = ('name:"tweet_2026-05-20",voiceMode:"passthrough"}}' + NEW_DEFS
         + '},_h=[')
    s = apply(s, a, r, "G1-node-defs")

    # G-2: palette — catégorie Generator.
    a = '{cat:"gen",types:["Seedance","HeyGenAvatar","NewsScript","NewsIllustration"]}'
    r = ('{cat:"gen",types:["Seedance","HeyGenAvatar","NewsScript",'
         '"NewsIllustration","ImageGen","ImageEdit","Variations"]}')
    s = apply(s, a, r, "G2-palette-gen")

    # G-3: palette — catégorie Edit.
    a = '{cat:"edit",types:["Trim","Extend","Concatenate","Split","Speed"]}'
    r = ('{cat:"edit",types:["Trim","Extend","Concatenate","Split","Speed",'
         '"RemoveBG","Upscale","CropFormat"]}')
    s = apply(s, a, r, "G3-palette-edit")

    # G-4: helpers + panneaux d'inspecteur (module scope, avant Bh).
    a = 'function Bh({p:e,set:t})'
    s = apply(s, a, HELPERS + a, "G4-helpers-panels")

    # G-5: Yh — signature + branches d'inspecteur des nouveaux nœuds.
    a = ('function Yh({node:e,onUpdate:t,graph:g,onUpdateNode:U})'
         '{const n=e.props||{},o=(i,s)=>t({[i]:s});return e.type==="MusicTrack"?')
    r = ('function Yh({node:e,onUpdate:t,graph:g,onUpdateNode:U,onSpawnNodes:sp})'
         '{const n=e.props||{},o=(i,s)=>t({[i]:s});' + YH_BRANCHES)
    s = apply(s, a, r, "G5-inspector-branches")

    # G-6: $h — accepte et propage onSpawnNodes.
    a = 'onRenameGraph:i,variant:s,onScheduleRender:a})'
    r = 'onRenameGraph:i,variant:s,onScheduleRender:a,onSpawnNodes:sp})'
    s = apply(s, a, r, "G6-sidebar-sig")
    a = 'r.jsx(Yh,{node:e,onUpdate:o,graph:t,onUpdateNode:U})'
    r = 'r.jsx(Yh,{node:e,onUpdate:o,graph:t,onUpdateNode:U,onSpawnNodes:sp})'
    s = apply(s, a, r, "G7-sidebar-pass")

    # G-8: Studio — fournit onSpawnNodes (ajout de nœuds au graphe).
    a = 'jsx($h,{node:ne,graph:o,lastJob:g,onUpdate:'
    r = ('jsx($h,{node:ne,graph:o,lastJob:g,'
         'onSpawnNodes:function(LL){i(function(W){return Object.assign({},W,'
         '{nodes:W.nodes.concat(LL)})})},onUpdate:')
    s = apply(s, a, r, "G8-studio-spawn")

    # G-9..12: le compilateur Mh accepte les nouveaux nœuds comme source image.
    a = '(H.type!=="Image"&&H.type!=="NewsIllustration")||!((w=H.props)!=null&&w.filename)'
    r = '!dzIsImgNode(H)||!((w=H.props)!=null&&w.filename)'
    s = apply(s, a, r, "G9-mh-ugc")
    a = '(H.type!=="Image"&&H.type!=="NewsIllustration")||!(H.props&&H.props.filename)'
    r = '!dzIsImgNode(H)||!(H.props&&H.props.filename)'
    s = apply(s, a, r, "G10-mh-concat")
    a = '(b.type!=="Image"&&b.type!=="NewsIllustration")||!((c=b.props)!=null&&c.filename)'
    r = '!dzIsImgNode(b)||!((c=b.props)!=null&&c.filename)'
    s = apply(s, a, r, "G11-mh-solo")
    a = 'if(b3.type==="Image"||b3.type==="NewsIllustration")return b3.props&&b3.props.filename?{source_kind:"upload",upload_filename:b3.props.filename}:null'
    r = 'if(dzIsImgNode(b3))return b3.props&&b3.props.filename?{source_kind:"upload",upload_filename:b3.props.filename}:null'
    s = apply(s, a, r, "G12-mh-animbase")

    # G-13..15: composition spatiale + aperçus acceptent les nouveaux nœuds.
    a = 'if(g.type==="Image")return g.props&&g.props.filename?{source_kind:"upload",upload_filename:g.props.filename}:null'
    r = 'if(dzIsImgNode(g)&&g.type!=="NewsIllustration")return g.props&&g.props.filename?{source_kind:"upload",upload_filename:g.props.filename}:null'
    s = apply(s, a, r, "G13-compose-fill")
    a = 'img.type==="Image"&&img.props&&img.props.filename'
    r = 'dzIsImgNode(img)&&img.props&&img.props.filename'
    s = apply(s, a, r, "G14-preview-reel")
    a = 'if(g.type==="Image")return g.props&&g.props.filename?{kind:"img",url:D.imageUrl(g.props.filename),tag:"Image"}:null'
    r = 'if(dzIsImgNode(g)&&g.type!=="NewsIllustration")return g.props&&g.props.filename?{kind:"img",url:D.imageUrl(g.props.filename),tag:"Image"}:null'
    s = apply(s, a, r, "G15-preview-image")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (imagegen nodes). Size:",
          BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
