# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzstudio.py
"""Maillon de queue : le STUDIO (menus Studio, t225-t229, 16/10/2026).

t225 — chaque lien atterrit au MILIEU du rond du port, à l'entrée comme à la sortie. Défaut relevé sur 02f8162c
(docs/superpowers/specs/2026-10-16-releve-menus-studio.md) : `qi` (géométrie des liens) et `ud` (rendu des ports)
calculaient chacun leur position. `qi` donnait x = 0 / bi et y = Ru+12+i·Mu (48+22i) ; le rond est rendu à x+1 / x+219
(bordure du nœud) et y = 1 + Ru + 10 + 8 (55+22i) ; un libellé long passait sur deux lignes (`alignItems:center`) et
le rond descendait encore de 7. Ce qu'il pose (ancres uniques, relevées le 16/10 sur 02f8162c) :
  - A0 : `dzPortGeo` = {b bordure, oy origine des lignes sous l'en-tête, p pas (Mu), lh hauteur de ligne, r rond},
    posé devant `qi` après les constantes du Studio : LA source unique de géométrie des ports ;
  - A1 : `qi` rend le centre du rond : x = b (entrée) / bi − b (sortie), y = b + Ru + oy + i·p + r/2 ;
  - A2 : `ud` pose la ligne à `oy + i·p`, de hauteur fixe `lh`, rond (`r`) ancré en HAUT (`alignItems:"flex-start"`),
    débordant de r/2 hors du nœud ;
  - A3 : l'étiquette tient sur UNE ligne (nowrap, ellipse, interligne lh) ; son `title` donne le libellé complet.

t226 — le port `brand` de Composition spatiale. Relevé du 16/10 : `dzSpatialSlots` ne créait de port image que pour
les `image_slot` ; la région `r_brand` de tpl_news_reel est un `brand_strip` → pas de port `brand`, alors que le graphe
de départ relie Bandeau de marque → `brand` ; `qi` rendait {x:0,y:0} (coin du nœud). `dzCompose` sautait la région et
le backend la dessine d'après ses `items` : le nœud relié n'était lu par personne. Décision de l'utilisateur, (a) :
  - B1 : `dzSpatialSlots` expose `brand` (type image, slot = id de la région) pour la PREMIÈRE région brand_strip,
    APRÈS les ports existants, si aucune image_slot n'a déjà pris `brand` ; libellé = celui de la région, sinon
    « brand » (aucun texte neuf) ;
  - B2 : `qi` d'un port introuvable rend le bord du nœud à la ligne SOUS le dernier port, jamais plus (0,0) ;
  - B3 : `dzCompose` mappe la région brand_strip à son port (carte région → port de dzSpatialSlots) : si un Bandeau
    de marque y est relié, son texte (ou celui du catalogue, l'espace actif) remplace le 1er item texte ; le logo PNG
    du modèle reste, l'emoji du nœud est ignoré ; texte vide ou identique → région intacte ;
  - B4 : le gabarit modifié part au rendu quand le bandeau a changé (`hasMods`).
Sans lien, rendu identique.

t227 — de l'air au-dessus de l'encart, même mise en page sur tous les nœuds (défaut 2 du relevé). Le corps des ports
avait une hauteur FIXE (`minHeight:16`+`padding:"8px 0"` = 16) et l'encart se posait 4 plus bas : la 1re ligne
débordait de 6 dans l'encart, les suivantes s'imprimaient dessus. Valeurs validées sur maquette par l'utilisateur
(variante B, docs/superpowers/specs/assets/2026-10-16-studio/t227-maquette.png) : oy 8, lh 16, Mu 22, air 10 MESURÉ
sous le bas de la dernière ligne.
  - C1 : `dzPortGeo` passe à oy 8 et gagne `air` ; `dzPortBodyH(nIn,nOut)` = oy + (n − 1)·p + lh + air (n = max,
    oy + air sans port) et `dzVisInPorts(e,u)` (ports d'entrée VISIBLES : Concatenate tronqué à sourceCount 2..6,
    `dzNodeInPorts` pour Composition spatiale, sinon le catalogue) posés devant `qi` ;
  - C2 : le corps des ports de `Th` prend la hauteur `dzPortBodyH(visibles, sorties)` et rend les lignes d'entrée
    depuis `dzVisInPorts` (une seule source pour la hauteur et les lignes) ;
  - C3 : l'encart perd sa marge haute (`margin:"0 10px"`) : l'air est dans le corps, donc identique pour l'encart
    (variante reef) et pour le pied (variante classique).
L'aperçu de composition de l'inspecteur (dzPvCell) n'est pas touché par les C*. t228-t229 ajoutent leurs familles (D*, E*).

Suite de t227 (17/10) — l'aperçu de composition montre le VRAI bandeau. Relevé sur 55893568 : `dzPreviewModel` ne
gardait de la région brand_strip que son fond, et `dzPvCell` écrivait « 🐙 DEEPOTUS » / « $DEEP » en dur, quels que
soient le modèle et le Bandeau relié ; le rendu réel pose le logo PNG du modèle (item `mark`) et le 1er item texte,
remplacé depuis B3 par le texte du Bandeau de marque relié au port de la région.
  - F1 : `dzPreviewModel` calcule pour la région le texte EFFECTIF avec la règle de B3 (port de la région via
    `dzSpatialSlots`, nœud BrandStrip relié, texte du nœud ou du catalogue, vide → texte du modèle ; aucun item texte →
    aucun texte), sa couleur, et la présence d'un logo ;
  - F2 : `dzPvCell` affiche ce texte (ellipse + `title`, à droite) et le pictogramme du logo seulement si le modèle a
    un `mark` ; plus de « $DEEP » en dur. Aucun texte visible neuf.
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 », aucun texte visible neuf (le
`title` réutilise le libellé et le type déjà affichés).

t228 (17/10) — A1 : la barre du graphe passe sur deux ou trois lignes (107 px à 1500 px, inspecteur ouvert) mais le
canevas restait à `top:48` : le haut des nœuds passait sous la barre et l'encart des raccourcis (`top:60`) recouvrait
Avatar HeyGen. Décision de l'utilisateur sur maquette (t228-maquette.png) : option B, pastille, pas de « Recadrer ».
  - D0 : `dzRaccRef(el)` devant `__dzGbarRef` : si un nœud chevauche l'encart PLEIN (taille mémorisée tant qu'il est
    plein, donc pas d'oscillation), l'encart se replie en pastille « ⌘ » dont l'infobulle est le texte complet (lu
    dans l'encart, donc dans la langue active) ; un ResizeObserver sur le canevas relance le test ;
  - D1 : le canevas commence sous la barre, `top:"var(--dz-gbar-h, 48px)"`, et suit sa hauteur en direct ;
  - D2 : l'encart à `top:12` du canevas, `ref` en ligne (rappelée à chaque rendu : pan, zoom, glisser), texte complet
    dans `data-dz-racc-plein` (mêmes clés dzT), pastille `data-dz-racc-pastille`. Aucun texte visible neuf.

t229 (17/10) — A2 : les boutons de zoom ± ne changeaient que le zoom (`b(R=>…)`) : la vue pivotait autour du coin
(0,0) du canevas et partait en haut à gauche, alors que la molette pivote autour du curseur.
  - E0 : `dzZoomCentre(cv,h,J,z,b)` devant `dzRaccRef` : même formule que la molette, pivot = centre du rectangle du
    canevas ; rien à la borne (J===h) ; sans canevas, le zoom change seul ;
  - E1 / E2 : les boutons − / + l'appellent avec `N.current` (mêmes bornes .3 / 1.5, même pas .1). Aucun texte neuf.

Animation (17/10) — le champ « Preset » de l'inspecteur Animation n'agissait pas. Relevé sur 39241c15 : `mk(t)` crée
chaque élément avec deux `keyframes`, que l'aperçu (`dzKfs`) et le rendu backend (`animation_service.kfs_of`) lisent
en priorité ; `applyPreset` n'écrivait que `from`/`to` → preset enregistré mais ignoré, et le menu montrant le nom
enregistré, re-choisir le même ne déclenchait rien.
  - G1 : `applyPreset` écrit deux keyframes (t 0 = from + easing du preset, t 1 = to), retire from/to, ramène la
    keyframe active à 0 ; `dzPresetDe(el)` rend le nom du preset si les keyframes sont exactement les siennes, sinon "" ;
  - G2 : le menu Preset affiche `dzPresetDe(cur)` (périmé ou retouché → « — », re-choisissable). Aucun texte neuf.

Maillon de QUEUE, APRÈS dzlogo (dont il sonde le marqueur) ; il garde un .js.bak_dzstudio le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzstudio` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzlogo`. Lecture et écriture
en OCTETS. Bancs : backend/tests/test_studio_ancrage.py (t225), test_studio_ports_spatial.py (t226),
test_studio_entetes.py (t227), test_studio_apercu_bandeau.py (suite de t227), test_studio_canevas_barre.py (t228),
test_studio_zoom_boutons.py (t229), test_studio_animation_preset.py (Preset).
Run : python scripts/patch_bundle_dzstudio.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzstudio")
TAG = "dzstudio"
MARKER = "var dzPortGeo={"
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzlogo", "function DzLogoMarque(", 1),
    ("dzreglages", "function dzOuvrirReglages(", 1),
    ("spatialports", "function dzNodeInPorts(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

PAIRES_AB = [
    ('Eh=30;function qi(',                                                                                  # A0
     'Eh=30;var dzPortGeo={b:1,oy:10,p:Mu,lh:16,r:16};function qi('),
    ('const l=t==="in"?0:bi,d=Ru+12+a*Mu;return{x:l,y:d}',                                                  # A1
     'const l=t==="in"?dzPortGeo.b:bi-dzPortGeo.b,d=dzPortGeo.b+Ru+dzPortGeo.oy+a*dzPortGeo.p+dzPortGeo.r/2;'
     'return{x:l,y:d}'),
    ('top:8+n*Mu+2,left:e==="in"?-8:"auto",right:e==="out"?-8:"auto",display:"flex",alignItems:"center",gap:6,'  # A2
     'flexDirection:e==="in"?"row":"row-reverse",width:130},children:[r.jsx("span",{"data-port-side":e,'
     '"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)},'
     'style:{width:16,height:16,',
     'top:dzPortGeo.oy+n*dzPortGeo.p,left:e==="in"?-dzPortGeo.r/2:"auto",right:e==="out"?-dzPortGeo.r/2:"auto",'
     'display:"flex",alignItems:"flex-start",height:dzPortGeo.lh,gap:6,'
     'flexDirection:e==="in"?"row":"row-reverse",width:130},children:[r.jsx("span",{"data-port-side":e,'
     '"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)},'
     'style:{width:dzPortGeo.r,height:dzPortGeo.r,'),
    ('r.jsxs("span",{style:{fontSize:10.5,color:"var(--ink-soft)",textAlign:e==="in"?"left":"right",'       # A3
     'padding:e==="in"?"0 0 0 4px":"0 4px 0 0"},children:[t.label||t.id,',
     'r.jsxs("span",{title:(t.label||t.id)+" · "+t.type,style:{fontSize:10.5,lineHeight:dzPortGeo.lh+"px",'
     'whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",minWidth:0,color:"var(--ink-soft)",'
     'textAlign:e==="in"?"left":"right",padding:e==="in"?"0 0 0 4px":"0 4px 0 0"},children:[t.label||t.id,'),
    ('ports.push({id:ipool[i1],type:"image",label:imgs[i1].slot_label||imgs[i1].slot_name,slot:imgs[i1].slot_name});'  # B1
     'return{ports:ports,seq:seq,maxN:maxN,n:n}}',
     'ports.push({id:ipool[i1],type:"image",label:imgs[i1].slot_label||imgs[i1].slot_name,slot:imgs[i1].slot_name});'
     'var dzBs=null;for(i1=0;i1<regs.length&&!dzBs;i1++)regs[i1].type==="brand_strip"&&(dzBs=regs[i1]);'
     'dzBs&&!ports.some(function(q){return q.id==="brand"})&&ports.push({id:"brand",type:"image",'
     'label:dzBs.slot_label||dzBs.label||"brand",slot:dzBs.slot_name||dzBs.id});'
     'return{ports:ports,seq:seq,maxN:maxN,n:n}}'),
    ('const a=_lst.findIndex(u=>u.id===n);if(a<0)return{x:0,y:0};',                                         # B2
     'let a=_lst.findIndex(u=>u.id===n);if(a<0)a=_lst.length;'),
    ('var regions=tpl.regions.slice(),zi=60,ovc={};var __trMod=!1;',                                        # B3
     'var regions=tpl.regions.slice(),zi=60,ovc={};var __trMod=!1;'
     'var __brMod=!1;regions=regions.map(function(rg5){var p5=rg5.type==="brand_strip"&&__regionPort[rg5.slot_name||rg5.id],'
     'b5=p5&&Wt(e,l.id,p5);if(!b5||b5.type!=="BrandStrip")return rg5;'
     'var P5=Object.assign({},(Me.BrandStrip&&Me.BrandStrip.props)||{},b5.props||{}),'
     't5=String(P5.text==null?"":P5.text).trim(),k5=-1;if(!t5)return rg5;'
     'var it5=(rg5.items||[]).map(function(it,j){if(k5<0&&it&&it.type==="text"){k5=j;'
     'if(it.text===t5)return it;__brMod=!0;return Object.assign({},it,{text:t5})}return it});'
     'return k5<0?rg5:Object.assign({},rg5,{items:it5})});'),
    ('var hasMods=regions.length!==tpl.regions.length||loud!=null||!!music||__trMod;',                     # B4
     'var hasMods=regions.length!==tpl.regions.length||loud!=null||!!music||__trMod||__brMod;'),
]

PAIRES_C = [
    ('var dzPortGeo={b:1,oy:10,p:Mu,lh:16,r:16};function qi(',                                              # C1
     'var dzPortGeo={b:1,oy:8,p:Mu,lh:16,r:16,air:10};'
     'function dzPortBodyH(nIn,nOut){var n=Math.max(nIn,nOut);'
     'return dzPortGeo.oy+(n>0?(n-1)*dzPortGeo.p+dzPortGeo.lh:0)+dzPortGeo.air}'
     'function dzVisInPorts(e,u){return e.type==="Concatenate"?u.inPorts.slice(0,Math.max(2,Math.min(6,'
     '(e.props&&e.props.sourceCount)||3))):(typeof dzNodeInPorts==="function"&&dzNodeInPorts(e))||u.inPorts}'
     'function qi('),
    ('r.jsxs("div",{style:{position:"relative",minHeight:16,padding:"8px 0"},children:[(e.type==="Concatenate"?'  # C2
     'u.inPorts.slice(0,Math.max(2,Math.min(6,(e.props&&e.props.sourceCount)||3))):(typeof dzNodeInPorts==="function"'
     '&&dzNodeInPorts(e))||u.inPorts).map(',
     'r.jsxs("div",{style:{position:"relative",height:dzPortBodyH(dzVisInPorts(e,u).length,u.outPorts.length)},'
     'children:[dzVisInPorts(e,u).map('),
    ('m&&r.jsx("div",{style:{height:zh,margin:"4px 10px 0",',                                               # C3
     'm&&r.jsx("div",{style:{height:zh,margin:"0 10px",'),
]

PAIRES_F = [
    ('else if(r.type==="brand_strip")items.push(Object.assign(b,{kind:"brand",bg:r.background_color||"#02060d"}));',  # F1
     'else if(r.type==="brand_strip"){var it6=r.items||[],tx6=null,k6;'
     'for(k6=0;k6<it6.length&&!tx6;k6++)it6[k6]&&it6[k6].type==="text"&&(tx6=it6[k6]);'
     'var sl6=r.slot_name||r.id,pt6=null,ps6=dzSpatialSlots(tpl,l.props||{}).ports;'
     'for(k6=0;k6<ps6.length&&!pt6;k6++)ps6[k6].slot===sl6&&(pt6=ps6[k6].id);'
     'var bn6=pt6&&Wt(e,l.id,pt6),P6=bn6&&bn6.type==="BrandStrip"?'
     'Object.assign({},(Me.BrandStrip&&Me.BrandStrip.props)||{},bn6.props||{}):null,'
     't6=P6?String(P6.text==null?"":P6.text).trim():"";'
     'items.push(Object.assign(b,{kind:"brand",bg:r.background_color||"#02060d",'
     'mark:it6.some(function(z){return z&&z.type==="mark"}),text:tx6?(t6||String(tx6.text||"")):"",'
     'color:tx6&&tx6.color||"#00e5ff"}))}'),
    ('children:[r.jsx("span",{children:"🐙 DEEPOTUS"},"a"),r.jsx("span",{children:"$DEEP"},"b")]},ix);',       # F2
     'children:[it.mark!==!1&&r.jsx("span",{children:"🐙 DEEPOTUS"},"a"),it.text?r.jsx("span",{title:it.text,'
     'style:{color:it.color||"#00e5ff",marginLeft:"auto",minWidth:0,overflow:"hidden",textOverflow:"ellipsis",'
     'whiteSpace:"nowrap"},children:it.text},"b"):null]},ix);'),
]

PAIRES_D = [
    ('function __dzGbarRef(el){',                                                                             # D0
     'function dzRaccRef(el){if(!el)return;var cv=el.parentNode;if(!cv)return;'
     'function f(){var pl=el.querySelector("[data-dz-racc-plein]"),pa=el.querySelector("[data-dz-racc-pastille]");'
     'if(!pl||!pa)return;var e=el.getBoundingClientRect();'
     'if(el.getAttribute("data-dz-pli")!=="1"){el.__dzW=e.width;el.__dzH=e.height}'
     'var R=e.right,T=e.top,L=R-(el.__dzW||0),B=T+(el.__dzH||0),hit=!1,ns=cv.querySelectorAll("[data-node-id]"),i,n;'
     'for(i=0;i<ns.length&&!hit;i++){n=ns[i].getBoundingClientRect();hit=n.left<R&&n.right>L&&n.top<B&&n.bottom>T}'
     'el.setAttribute("data-dz-pli",hit?"1":"0");pl.style.display=hit?"none":"flex";'
     'pa.style.display=hit?"inline-flex":"none";el.style.padding=hit?"4px 6px":"6px 10px";'
     'el.style.borderRadius=hit?"999px":"var(--r-sm)";el.title=hit?Array.prototype.map.call(pl.childNodes,'
     'function(z){return String(z.textContent||"").trim()}).join(" "):""}'
     'f();if(!el.__dzRo){try{el.__dzRo=new ResizeObserver(f);el.__dzRo.observe(cv)}catch(_e){}}}'
     'function __dzGbarRef(el){'),
    ('onDrop:Q,style:{position:"absolute",inset:0,top:48,backgroundColor:"#02060d"',                         # D1
     'onDrop:Q,style:{position:"absolute",inset:0,top:"var(--dz-gbar-h, 48px)",backgroundColor:"#02060d"'),
    ('r.jsxs("div",{style:{position:"absolute",right:12,top:60,zIndex:4,display:"flex",alignItems:"center",gap:8,'  # D2
     'padding:"6px 10px",background:"var(--bg-panel)",border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",'
     'fontSize:11,color:"var(--ink-soft)"},children:[r.jsx("kbd",{style:ns,children:"/"}),'
     'dzT("studio.graphe.raccourci_noeuds"),r.jsx("kbd",{style:ns,children:"⌘K"})," palette",'
     'r.jsx("kbd",{style:ns,children:"⌘⏎"}),dzT("studio.graphe.raccourci_executer")]})',
     'r.jsxs("div",{ref:function(e_){dzRaccRef(e_)},"data-dz-racc":"1",style:{position:"absolute",right:12,top:12,'
     'zIndex:4,display:"flex",alignItems:"center",gap:8,padding:"6px 10px",background:"var(--bg-panel)",'
     'border:"1px solid var(--stroke)",borderRadius:"var(--r-sm)",fontSize:11,color:"var(--ink-soft)"},'
     'children:[r.jsxs("span",{"data-dz-racc-plein":"1",style:{display:"flex",alignItems:"center",gap:8,'
     'whiteSpace:"nowrap"},children:[r.jsx("kbd",{style:ns,children:"/"}),'
     'dzT("studio.graphe.raccourci_noeuds"),r.jsx("kbd",{style:ns,children:"⌘K"})," palette",'
     'r.jsx("kbd",{style:ns,children:"⌘⏎"}),dzT("studio.graphe.raccourci_executer")]}),'
     'r.jsx("span",{"data-dz-racc-pastille":"1",style:{display:"none"},children:r.jsx("kbd",{style:ns,children:"⌘"})})]})'),
]

PAIRES_E = [
    ('function dzRaccRef(el){',                                                                               # E0
     'function dzZoomCentre(cv,h,J,z,b){if(J===h)return;var W=cv&&cv.getBoundingClientRect?cv.getBoundingClientRect():null;'
     'if(W){var S=W.width/2,L=W.height/2;z(function(ce){return{x:S-(S-ce.x)*(J/h),y:L-(L-ce.y)*(J/h)}})}b(J)}'
     'function dzRaccRef(el){'),
    ('r.jsx(se,{name:"dz-action-zoom-arriere",size:26,onClick:()=>b(R=>Math.max(.3,R-.1))})',                 # E1
     'r.jsx(se,{name:"dz-action-zoom-arriere",size:26,onClick:()=>dzZoomCentre(N.current,h,Math.max(.3,h-.1),z,b)})'),
    ('r.jsx(se,{name:"dz-action-zoom-avant",size:26,onClick:()=>b(R=>Math.min(1.5,R+.1))})',                  # E2
     'r.jsx(se,{name:"dz-action-zoom-avant",size:26,onClick:()=>dzZoomCentre(N.current,h,Math.min(1.5,h+.1),z,b)})'),
]

PAIRES_G = [
    ('function applyPreset(name){var p=PRESETS[name];if(!p||!cur)return;var a=els.slice();'                  # G1
     'a[sel]=Object.assign({},a[sel],{from:Object.assign({},p.from),to:Object.assign({},p.to),'
     'easing:p.easing||a[sel].easing,preset:name});setEls(a)}',
     'function applyPreset(name){var p=PRESETS[name];if(!p||!cur)return;var a=els.slice();'
     'var ne=Object.assign({},a[sel],{keyframes:[Object.assign({t:0},p.from,{easing:p.easing}),'
     'Object.assign({t:1},p.to)],easing:p.easing||a[sel].easing,preset:name});delete ne.from;delete ne.to;'
     'a[sel]=ne;setEls(a);setAk(0)}'
     'function dzPresetDe(el){var n=el&&el.preset,p=n&&PRESETS[n];if(!p)return "";var k=dzKfs(el);'
     'if(k.length!==2)return "";var ok=Object.keys(p.from).every(function(c){return k[0][c]===p.from[c]})'
     '&&Object.keys(p.to).every(function(c){return k[1][c]===p.to[c]});return ok?n:""}'),
    ('r.jsx(O,{label:"Preset",children:r.jsx(re,{value:cur.preset||"",',                                    # G2
     'r.jsx(O,{label:"Preset",children:r.jsx(re,{value:dzPresetDe(cur),'),
]

PAIRES = PAIRES_AB + PAIRES_C + PAIRES_F + PAIRES_D + PAIRES_E + PAIRES_G     # C1 réécrit la sortie de A0 : l'ordre compte (défaire à rebours)


def lire(p):
    b = p.read_bytes()
    bom = b.startswith(b"\xef\xbb\xbf")
    return b.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, texte, bom):
    p.write_bytes((("﻿" if bom else "") + texte).encode("utf-8"))


def appliquer(s: str) -> str:
    for ancre, remplace in PAIRES:
        n = s.count(ancre)
        if n != 1:
            raise SystemExit(f"[{TAG}] ancre x{n} (attendu 1) : {ancre[:80]!r}")
        s = s.replace(ancre, remplace, 1)
    return s


def defaire(s: str) -> str:
    """L'inverse exact (lu par avant_dzstudio dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def partiel(s: str) -> bool:
    """Marqueur présent mais le défaire complet échoue : une famille de paires manque (bundle d'une tâche antérieure).
    t227 : C1 réécrit la sortie de A0, on ne peut plus compter chaque remplacement isolément."""
    if MARKER not in s:
        return False
    try:
        defaire(s)
    except AssertionError:
        return True
    return False


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):                                  # t226 : une famille ajoutée après coup (ex. A*+B* sans C*)
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzstudio "
                             f"(défaire avec le maillon d'avant l'ajout, puis appliquer)")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paires)")
        return
    shutil.copyfile(BUNDLE, BAK)
    try:
        ecrire(BUNDLE, neuf, bom)
    except BaseException:
        shutil.copyfile(BAK, BUNDLE)                    # jamais un bundle à moitié écrit
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
