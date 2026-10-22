/* sonvfx-post.js — t276 (22/10/2026) : la page « Post-traitement » de Son & VFX. Elle remplace la vue d'origine
   (DzSonVfx, couche L4 non touchée, gardée montée et masquée par le hub), dont les trois presets étaient décoratifs.
   Trois zones : à gauche la SOURCE (Rendus de la Bibliothèque, résultats VFX IA, particules) ; au centre l'aperçu
   AVANT / APRÈS à curseur, sur l'image de l'instant choisi ; à droite le catalogue des 15 presets, la PILE ordonnée
   (glisser ou Monter / Descendre, intensité 0-100 %, masquer, dupliquer, supprimer, réglages dépliés, LUT .cube
   choisie ou importée), les piles enregistrées et le rendu. Le rendu passe en job ffmpeg local, gratuit et sans clé,
   puis entre dans la Bibliothèque › Rendus (relation « post »). L'aperçu et le rendu partagent le même graphe
   (services/post_pile.py) : l'image d'après à l'instant t est celle du rendu à t.
   SOURCE du maillon de queue dzsonvfx, posée APLATIE (mêmes règles d'écriture que sonvfx-pistes.js : une
   instruction par ligne terminée par « ; », aucune ligne qui commence par « ( » ou « [ », aucun « // »,
   commentaires sur des lignes entières seulement). Symboles du bundle : r, x, dzT, __dzGl ; de la page Pistes :
   dzSvpJson. Aucun arrondi (angles vifs, règle du hub).
   Routes : GET /api/post/catalogue, /api/post/sources, /api/post/presets, /api/jobs/{id} ;
   POST /api/post/apercu, /api/post/rendre, /api/post/presets, /api/post/lut ; DELETE /api/post/presets/{id}. */
var DZSVO_FAMILLES=["rendus","vfx","particules"];
var DZSVO_LARGEUR=960;
var DZSVO_DELAI=250;
function dzSvoTextes(){
return {fam:{rendus:dzT("sonvfx.post.f_rendus"),vfx:dzT("sonvfx.post.f_vfx"),particules:dzT("sonvfx.post.f_particules")},
p:{grain16:dzT("sonvfx.post.p_grain16"),bloom:dzT("sonvfx.post.p_bloom"),glitch_rgb:dzT("sonvfx.post.p_glitch_rgb"),
aberration:dzT("sonvfx.post.p_aberration"),vignette:dzT("sonvfx.post.p_vignette"),halation:dzT("sonvfx.post.p_halation"),
lut:dzT("sonvfx.post.p_lut"),vhs:dzT("sonvfx.post.p_vhs"),flou_mouvement:dzT("sonvfx.post.p_flou_mouvement"),
nettete:dzT("sonvfx.post.p_nettete"),bandes:dzT("sonvfx.post.p_bandes"),tremblement:dzT("sonvfx.post.p_tremblement"),
fuite:dzT("sonvfx.post.p_fuite"),nb_argentique:dzT("sonvfx.post.p_nb_argentique"),duotone:dzT("sonvfx.post.p_duotone")},
src_titre:dzT("sonvfx.post.src_titre"),src_vide:dzT("sonvfx.post.src_vide"),src_choisir:dzT("sonvfx.post.src_choisir"),
chargement:dzT("sonvfx.post.chargement"),avant:dzT("sonvfx.post.avant"),apres:dzT("sonvfx.post.apres"),
curseur:dzT("sonvfx.post.curseur"),instant:dzT("sonvfx.post.instant"),calcul:dzT("sonvfx.post.calcul"),
catalogue:dzT("sonvfx.post.catalogue"),pile:dzT("sonvfx.post.pile"),pile_vide:dzT("sonvfx.post.pile_vide"),
vider:dzT("sonvfx.post.vider"),intensite:dzT("sonvfx.post.intensite"),masquer:dzT("sonvfx.post.masquer"),
afficher:dzT("sonvfx.post.afficher"),dupliquer:dzT("sonvfx.post.dupliquer"),supprimer:dzT("sonvfx.post.supprimer"),
monter:dzT("sonvfx.post.monter"),descendre:dzT("sonvfx.post.descendre"),glisser:dzT("sonvfx.post.glisser"),
lut_integree:dzT("sonvfx.post.lut_integree"),lut_importer:dzT("sonvfx.post.lut_importer"),
presets:dzT("sonvfx.post.presets"),preset_choix:dzT("sonvfx.post.preset_choix"),preset_nom:dzT("sonvfx.post.preset_nom"),
preset_enreg:dzT("sonvfx.post.preset_enreg"),preset_suppr:dzT("sonvfx.post.preset_suppr"),
preset_confirmer:dzT("sonvfx.post.preset_confirmer"),rendu:dzT("sonvfx.post.rendu"),rendu_titre:dzT("sonvfx.post.rendu_titre"),
rendre:dzT("sonvfx.post.rendre"),local:dzT("sonvfx.post.local"),rendu_ok:dzT("sonvfx.post.rendu_ok"),
vers_montage:dzT("sonvfx.post.vers_montage")};
}
function dzSvoTemps(s){s=Math.max(0,Number(s)||0);var m=Math.floor(s/60),r2=s-m*60;return m+":"+(r2<10?"0":"")+r2.toFixed(2);}
function dzSvoPost(u,corps){return fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)});}
/* l'image d'un aperçu (PNG du serveur) en URL d'objet ; une réponse en erreur lève avec le message du serveur */
function dzSvoImage(corps){
return dzSvoPost("/api/post/apercu",corps).then(function(res){return res.ok?res.blob():dzSvpJson(res);}).then(function(b){return URL.createObjectURL(b);});
}
function dzSvoLiberer(lst){lst.forEach(function(u){try{URL.revokeObjectURL(u);}catch(e){}});}
/* un maillon neuf : réglages au défaut du preset, intensité de départ de l'effet (100 % pour un mélange) */
function dzSvoMaillon(c,n){
var params={};
Object.keys(c.bounds||{}).forEach(function(k){var d=c.bounds[k].default;if(d!==void 0&&d!=="")params[k]=d;});
return {id:"m"+n,preset:c.id,intensite:c.intensite?c.defaut:100,masque:false,params:params};
}
function dzSvoDeplacer(pile,de,vers){
if(de===vers||de<0||vers<0||de>=pile.length||vers>=pile.length)return pile;
var a=pile.slice();var m=a.splice(de,1)[0];a.splice(vers,0,m);return a;
}
function dzSvoEnvoi(pile){return pile.map(function(m){return {preset:m.preset,intensite:m.intensite,masque:m.masque,params:m.params};});}
function DzSvPost(p){
var US=x.useState,UE=x.useEffect,UR=x.useRef;
var T=dzSvoTextes();
var c0=US(null),cat=c0[0],setCat=c0[1];
var s0=US(null),srcs=s0[0],setSrcs=s0[1];
var f0=US("rendus"),fam=f0[0],setFam=f0[1];
var so=US(null),src=so[0],setSrc=so[1];
var pl=US([]),pile=pl[0],setPile=pl[1];
var ou=US(null),ouvert=ou[0],setOuvert=ou[1];
var ti=US(0),t=ti[0],setT=ti[1];
var cm=US(50),cmp=cm[0],setCmp=cm[1];
var im=US({avant:null,apres:null}),imgs=im[0],setImgs=im[1];
var ca=US(false),calc=ca[0],setCalc=ca[1];
var er=US(""),err=er[0],setErr=er[1];
var pr=US([]),presets=pr[0],setPresets=pr[1];
var pn=US(""),pnom=pn[0],setPnom=pn[1];
var ps=US(""),psel=ps[0],setPsel=ps[1];
var ar=US(false),arme=ar[0],setArme=ar[1];
var rt=US(""),rtitre=rt[0],setRtitre=rt[1];
var jb=US(null),job=jb[0],setJob=jb[1];
var n=UR(0),req=UR(0),glisse=UR(-1),urls=UR([]);
function chargerSources(){return fetch("/api/post/sources").then(dzSvpJson).then(function(d){setSrcs(d);}).catch(function(e){setErr(e.message);});}
UE(function(){
fetch("/api/post/catalogue").then(dzSvpJson).then(function(d){setCat(d);}).catch(function(e){setErr(e.message);});
fetch("/api/post/presets").then(dzSvpJson).then(function(d){setPresets(d.presets||[]);}).catch(function(){});
chargerSources();
return function(){dzSvoLiberer(urls.current);};
},[]);
/* l'aperçu suit la source, l'instant et la pile, après un court délai ; une réponse dépassée est jetée */
var cle=src?JSON.stringify([src.job_id,t,dzSvoEnvoi(pile)]):"";
UE(function(){
if(!src)return;
var k=++req.current;
setCalc(true);
var h=setTimeout(function(){
var base={source:src.job_id,t:t,largeur:DZSVO_LARGEUR};
Promise.all([dzSvoImage(Object.assign({pile:[]},base)),dzSvoImage(Object.assign({pile:dzSvoEnvoi(pile)},base))]).then(function(res){
if(k!==req.current){dzSvoLiberer(res);return;}
dzSvoLiberer(urls.current);urls.current=res;setImgs({avant:res[0],apres:res[1]});setCalc(false);setErr("");
}).catch(function(e){if(k===req.current){setCalc(false);setErr(e.message);}});
},DZSVO_DELAI);
return function(){clearTimeout(h);};
},[cle]);
/* le job de rendu est suivi chaque seconde jusqu'à sa fin */
UE(function(){
if(!job||job.status==="done"||job.status==="failed")return;
var h=setTimeout(function(){
fetch("/api/jobs/"+encodeURIComponent(job.id)).then(dzSvpJson).then(function(d){
setJob({id:job.id,status:d.status,progress:d.progress||0,error:d.error||""});
if(d.status==="done")chargerSources();
}).catch(function(e){setJob({id:job.id,status:"failed",progress:0,error:e.message});});
},1000);
return function(){clearTimeout(h);};
},[job]);
var pmax=cat&&cat.pile_max||24;
var actifs=pile.filter(function(m){return !m.masque&&m.intensite>0;}).length;
var enCours=!!job&&job.status!=="done"&&job.status!=="failed";
var cpres=cat&&cat.presets||[],cdict={};
cpres.forEach(function(q){cdict[q.id]=q;});
function choisirSource(f){setSrc(f);setT(0);setImgs({avant:null,apres:null});setJob(null);}
function ajouter(q){
n.current++;
var m=dzSvoMaillon(q,n.current);
setPile(function(a){return a.length>=pmax?a:a.concat([m]);});
setOuvert(m.id);
}
function maj(id,f){setPile(function(a){return a.map(function(m){return m.id===id?Object.assign({},m,f(m)):m;});});}
function majParam(id,k,v){maj(id,function(m){var q={};q[k]=v;return {params:Object.assign({},m.params,q)};});}
function dupliquer(id){
n.current++;
var nid="m"+n.current;
setPile(function(a){var i=a.findIndex(function(m){return m.id===id;});if(i<0||a.length>=pmax)return a;
var b=a.slice();b.splice(i+1,0,Object.assign({},a[i],{id:nid,params:Object.assign({},a[i].params)}));return b;});
}
function supprimer(id){setPile(function(a){return a.filter(function(m){return m.id!==id;});});}
function deplacer(de,vers){setPile(function(a){return dzSvoDeplacer(a,de,vers);});}
function enregistrer(){
var nom=pnom.trim();
if(!nom||!pile.length)return;
dzSvoPost("/api/post/presets",{nom:nom,pile:dzSvoEnvoi(pile)}).then(dzSvpJson).then(function(e){
setPresets(function(a){return [e].concat(a);});setPnom("");setPsel(e.id);setArme(false);
}).catch(function(e){setErr(e.message);});
}
function charger(id){
setPsel(id);setArme(false);
var e=presets.find(function(q){return q.id===id;});
if(!e)return;
setPile(e.pile.filter(function(m){return cdict[m.preset];}).map(function(m){n.current++;return Object.assign({},m,{id:"m"+n.current,params:Object.assign({},m.params)});}));
setOuvert(null);
}
/* supprimer une pile enregistrée : le premier clic arme, le second supprime */
function supprPreset(){
if(!psel)return;
if(!arme){setArme(true);return;}
var id=psel;
fetch("/api/post/presets/"+encodeURIComponent(id),{method:"DELETE"}).then(dzSvpJson).then(function(){
setPresets(function(a){return a.filter(function(q){return q.id!==id;});});setPsel("");setArme(false);
}).catch(function(e){setErr(e.message);setArme(false);});
}
function importerLut(id,fichier){
if(!fichier)return;
var fd=new FormData();
fd.append("fichier",fichier);
fetch("/api/post/lut",{method:"POST",body:fd}).then(dzSvpJson).then(function(d){
setCat(function(c){return Object.assign({},c,{luts:d.luts||c.luts});});majParam(id,"file",d.nom);
}).catch(function(e){setErr(e.message);});
}
function rendre(){
if(!src||!actifs||enCours)return;
setErr("");
dzSvoPost("/api/post/rendre",{source:src.job_id,pile:dzSvoEnvoi(pile),titre:rtitre.trim()}).then(dzSvpJson).then(function(d){
setJob({id:d.job_id,status:"queued",progress:0,error:""});
}).catch(function(e){setErr(e.message);});
}
function mini(action,lbl,glyphe,props){
return r.jsx("button",Object.assign({type:"button",className:"dzsvo-mini","data-sv-post":action,"aria-label":lbl,title:lbl,children:__dzGl(glyphe,14)},props),action);
}
function reglage(m,k,b){
var v=m.params[k]!==void 0?m.params[k]:b.default;
var lbl=r.jsx("span",{className:"dzsvo-rnom",children:b.label},"n");
if(b.type==="range")return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("input",{type:"range",min:b.min,max:b.max,step:b.step||1,value:v,"data-sv-post":"param-"+k,onChange:function(e){majParam(m.id,k,Number(e.target.value));}},"i"),
r.jsx("span",{className:"dzsvo-rval",children:String(v)+(b.unit||"")},"v")]},k);
if(b.type==="color")return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("input",{type:"color",value:v,"data-sv-post":"param-"+k,onChange:function(e){majParam(m.id,k,e.target.value);}},"i")]},k);
if(b.type==="lut")return r.jsxs("div",{className:"dzsvo-regle",children:[lbl,
r.jsxs("select",{className:"dzsvo-sel",value:v||"","data-sv-post":"param-"+k,"aria-label":b.label,onChange:function(e){majParam(m.id,k,e.target.value);},
children:[r.jsx("option",{value:"",children:T.lut_integree},""),(cat&&cat.luts||[]).map(function(l){return r.jsx("option",{value:l,children:l},l);})]},"s"),
r.jsxs("label",{className:"dzsvo-mini dzsvo-fichier",title:T.lut_importer,children:[__dzGl("dz-action-importer",14),
r.jsx("input",{type:"file",accept:".cube","data-sv-post":"lut-import","aria-label":T.lut_importer,onChange:function(e){importerLut(m.id,e.target.files&&e.target.files[0]);e.target.value="";}},"f")]},"f")]},k);
return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("select",{className:"dzsvo-sel",value:String(v),"data-sv-post":"param-"+k,onChange:function(e){majParam(m.id,k,e.target.value);},
children:(b.choices||[]).map(function(c){return r.jsx("option",{value:String(c),children:String(c).replace(/_/g," ")},String(c));})},"s")]},k);
}
function ligne(m,i){
var q=cdict[m.preset]||{bounds:{},params:[]};
var dep=ouvert===m.id;
return r.jsxs("div",{className:"dzsvo-maillon","data-sv-post":"maillon","data-preset":m.preset,"data-masque":m.masque?"true":"false",draggable:true,
onDragStart:function(e){glisse.current=i;try{e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",String(i));}catch(e2){}},
onDragOver:function(e){e.preventDefault();},
onDrop:function(e){e.preventDefault();var de=glisse.current;glisse.current=-1;deplacer(de,i);},
children:[r.jsxs("div",{className:"dzsvo-mtete",children:[
r.jsx("span",{className:"dzsvo-poignee",title:T.glisser,children:__dzGl("dz-action-poignee",14)},"g"),
r.jsx("button",{type:"button",className:"dzsvo-mnom","aria-expanded":dep?"true":"false","data-sv-post":"deplier",onClick:function(){setOuvert(dep?null:m.id);},children:(i+1)+". "+(T.p[m.preset]||m.preset)},"n"),
mini("masquer",m.masque?T.afficher:T.masquer,m.masque?"dz-calque-masque":"dz-etat-visible",{"aria-pressed":m.masque?"true":"false",onClick:function(){maj(m.id,function(a){return {masque:!a.masque};});}}),
mini("monter",T.monter,"dz-edit-monter",{disabled:i===0,onClick:function(){deplacer(i,i-1);}}),
mini("descendre",T.descendre,"dz-edit-descendre",{disabled:i===pile.length-1,onClick:function(){deplacer(i,i+1);}}),
mini("dupliquer",T.dupliquer,"dz-action-dupliquer",{disabled:pile.length>=pmax,onClick:function(){dupliquer(m.id);}}),
mini("supprimer",T.supprimer,"dz-action-supprimer",{onClick:function(){supprimer(m.id);}})]},"t"),
r.jsxs("label",{className:"dzsvo-regle",children:[r.jsx("span",{className:"dzsvo-rnom",children:T.intensite},"n"),
r.jsx("input",{type:"range",min:0,max:100,step:1,value:m.intensite,"data-sv-post":"intensite","aria-label":T.intensite,onChange:function(e){var v=Number(e.target.value);maj(m.id,function(){return {intensite:v};});}},"i"),
r.jsx("span",{className:"dzsvo-rval",children:m.intensite+" %"},"v")]},"r"),
dep&&q.params.length?r.jsx("div",{className:"dzsvo-reglages",children:q.params.map(function(k){return reglage(m,k,q.bounds[k]);})},"p"):null]},m.id);
}
if(!cat&&!err)return r.jsx("div",{className:"dzsvo",children:r.jsx("div",{className:"dzsvo-attente",children:T.chargement})});
var liste=srcs?srcs[fam]||[]:null;
var dur=src?Math.max(0,Number(src.dur)||0):0;
var colSrc=r.jsxs("div",{className:"dzsvo-sources",children:[
r.jsx("div",{className:"dzsvo-titre",children:T.src_titre},"t"),
r.jsx("div",{className:"dzsvo-familles",role:"group","aria-label":T.src_titre,children:DZSVO_FAMILLES.map(function(f){
return r.jsx("button",{type:"button",className:"dzsvo-famille","aria-pressed":fam===f?"true":"false","data-sv-post":"famille-"+f,onClick:function(){setFam(f);},children:T.fam[f]+(srcs?" · "+(srcs[f]||[]).length:"")},f);})},"f"),
r.jsx("div",{className:"dzsvo-liste",children:liste===null?r.jsx("div",{className:"dzsvo-aide",children:T.chargement}):liste.length?liste.map(function(f){
var on=!!src&&src.job_id===f.job_id;
return r.jsxs("button",{type:"button",className:"dzsvo-src","aria-pressed":on?"true":"false","data-sv-post":"src-"+f.job_id,onClick:function(){choisirSource(f);},
children:[r.jsx("span",{className:"dzsvo-snom",children:f.titre},"n"),r.jsx("span",{className:"dzsvo-smeta",children:dzSvoTemps(f.dur)+" · "+f.w+"×"+f.h},"m")]},f.job_id);
}):r.jsx("div",{className:"dzsvo-aide","data-sv-post":"src-vide",children:T.src_vide})},"l")]},"sources");
var vue=r.jsxs("div",{className:"dzsvo-vue",children:[
!src?r.jsx("div",{className:"dzsvo-attente","data-sv-post":"attente",children:T.src_choisir},"a"):r.jsxs("div",{className:"dzsvo-comparer",style:{aspectRatio:(src.w||16)+"/"+(src.h||9)},children:[
imgs.avant?r.jsx("img",{className:"dzsvo-img","data-sv-post":"avant",src:imgs.avant,alt:T.avant},"av"):null,
imgs.apres?r.jsx("img",{className:"dzsvo-img","data-sv-post":"apres",src:imgs.apres,alt:T.apres,style:{clipPath:"inset(0 0 0 "+cmp+"%)"}},"ap"):null,
r.jsx("span",{className:"dzsvo-ligne","aria-hidden":"true",style:{left:cmp+"%"}},"l"),
r.jsx("span",{className:"dzsvo-etiq g",children:T.avant},"eg"),
r.jsx("span",{className:"dzsvo-etiq d",children:T.apres},"ed"),
r.jsx("input",{type:"range",className:"dzsvo-curseur",min:0,max:100,step:1,value:cmp,"aria-label":T.curseur,"data-sv-post":"curseur",onChange:function(e){setCmp(Number(e.target.value));}},"c"),
calc?r.jsx("span",{className:"dzsvo-calc","data-sv-post":"calcul",children:T.calcul},"k"):null]},"cmp"),
src?r.jsxs("div",{className:"dzsvo-temps",children:[
r.jsx("input",{type:"range",min:0,max:Math.max(0,dur-0.04),step:0.04,value:t,"aria-label":T.instant,"data-sv-post":"instant",onChange:function(e){setT(Number(e.target.value));}},"i"),
r.jsx("span",{className:"dzsvo-t",children:dzSvoTemps(t)+" / "+dzSvoTemps(dur)},"t")]},"tps"):null,
err?r.jsx("div",{className:"dzsvo-note dzsvo-erreur",role:"alert","data-sv-post":"erreur",children:err},"e"):null]},"vue");
var colPile=r.jsxs("div",{className:"dzsvo-pile",children:[
r.jsx("div",{className:"dzsvo-titre",children:T.catalogue},"ct"),
r.jsx("div",{className:"dzsvo-catalogue",children:cpres.map(function(q){
return r.jsxs("button",{type:"button",className:"dzsvo-ajout","data-sv-post":"ajout-"+q.id,"aria-label":dzT("sonvfx.post.ajouter",{nom:T.p[q.id]||q.id}),disabled:pile.length>=pmax,onClick:function(){ajouter(q);},
children:[__dzGl("dz-action-ajouter",12),r.jsx("span",{children:T.p[q.id]||q.id},"n")]},q.id);})},"cat"),
r.jsxs("div",{className:"dzsvo-ptete",children:[r.jsx("div",{className:"dzsvo-titre",children:T.pile+" · "+pile.length+"/"+pmax},"t"),
r.jsx("button",{type:"button",className:"dzsvo-lien","data-sv-post":"vider",disabled:!pile.length,onClick:function(){setPile([]);setOuvert(null);},children:T.vider},"v")]},"pt"),
r.jsx("div",{className:"dzsvo-maillons",children:pile.length?pile.map(ligne):r.jsx("div",{className:"dzsvo-aide","data-sv-post":"pile-vide",children:T.pile_vide})},"pile"),
r.jsxs("div",{className:"dzsvo-section",children:[r.jsx("div",{className:"dzsvo-titre",children:T.presets},"t"),
r.jsxs("div",{className:"dzsvo-ctl",children:[
r.jsxs("select",{className:"dzsvo-sel","data-sv-post":"preset-choix","aria-label":T.presets,value:psel,onChange:function(e){charger(e.target.value);},
children:[r.jsx("option",{value:"",children:T.preset_choix},""),presets.map(function(q){return r.jsx("option",{value:q.id,children:q.nom},q.id);})]},"s"),
mini("preset-suppr",arme?T.preset_confirmer:T.preset_suppr,"dz-action-supprimer",{disabled:!psel,"data-arme":arme?"":void 0,onClick:supprPreset})]},"c1"),
r.jsxs("div",{className:"dzsvo-ctl",children:[
r.jsx("input",{className:"dzsvo-champ",type:"text",maxLength:60,value:pnom,"data-sv-post":"preset-nom","aria-label":T.preset_nom,placeholder:T.preset_nom,onChange:function(e){setPnom(e.target.value);}},"n"),
r.jsx("button",{type:"button",className:"dzsvo-btn","data-sv-post":"preset-enreg",disabled:!pnom.trim()||!pile.length,onClick:enregistrer,children:T.preset_enreg},"b")]},"c2")]},"presets"),
r.jsxs("div",{className:"dzsvo-export",children:[r.jsx("div",{className:"dzsvo-titre",children:T.rendu},"t"),
r.jsx("input",{className:"dzsvo-champ",type:"text",maxLength:120,value:rtitre,"data-sv-post":"rendu-titre","aria-label":T.rendu_titre,placeholder:src?src.titre+" · post":T.rendu_titre,onChange:function(e){setRtitre(e.target.value);}},"n"),
r.jsxs("button",{type:"button",className:"dzsvo-btn prim","data-sv-post":"rendre",disabled:!src||!actifs||enCours,onClick:rendre,children:[__dzGl("dz-edit-effet",14),r.jsx("span",{children:T.rendre},"l")]},"b"),
r.jsx("div",{className:"dzsvo-aide",children:T.local},"a"),
job?r.jsx("div",{className:"dzsvo-note"+(job.status==="failed"?" dzsvo-erreur":""),"data-sv-post":"job",role:"status",
children:job.status==="done"?T.rendu_ok:job.status==="failed"?dzT("sonvfx.post.rendu_ko",{err:job.error}):dzT("sonvfx.post.rendu_cours",{pct:job.progress})},"j"):null,
job&&job.status==="done"?r.jsx("button",{type:"button",className:"dzsvo-btn","data-sv-post":"montage",onClick:function(){p.go&&p.go("montage");},children:T.vers_montage},"m"):null]},"export")]},"pile");
return r.jsxs("div",{className:"dzsvo","data-sv-post":"page",children:[colSrc,vue,colPile]});
}
