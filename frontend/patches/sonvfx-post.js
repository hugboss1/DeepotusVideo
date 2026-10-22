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
   POST /api/post/apercu, /api/post/rendre, /api/post/presets, /api/post/lut ; DELETE /api/post/presets/{id}.
   t277 (22/10/2026) : section « Générer avec l'IA » (GET /api/post/generateurs) — les générateurs vidéo → vidéo du
   catalogue_ia par fournisseur (fal, Decart, ElevenLabs), chacun avec son prix et, sans clé, la pastille « clé X à
   ajouter dans Réglages » : jamais désactivé, le refus arrive au lancement (503). Un générateur devient un maillon IA
   PAYANT de la même pile ({ia, prompt, options, masque} ; data-preset « ia », data-ia = son id), appliqué au rendu
   seulement : l'aperçu n'envoie que les maillons locaux. Une pile payante demande son devis (POST /api/post/devis)
   et le rendu s'ARME au premier clic (coût affiché), part au second avec confirme_cout. « Décrire le look »
   (POST /api/post/decrire) : une phrase devient une pile de presets locaux PROPOSÉE, que l'utilisateur remplace,
   ajoute ou écarte ; rien n'est appliqué sans lui (décision Q5). Textes : clés sonvfx.postia.*. */
var DZSVO_FAMILLES=["rendus","vfx","particules"];
var DZSVO_LARGEUR=960;
var DZSVO_DELAI=250;
var DZSVO_FOURN={fal:"fal",decart:"Decart",elevenlabs:"ElevenLabs"};
var DZSVO_FOURNS=["fal","decart","elevenlabs"];
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
function dzSvoTextesIa(){
return {generer:dzT("sonvfx.postia.generer"),generer_aide:dzT("sonvfx.postia.generer_aide"),payant:dzT("sonvfx.postia.payant"),
prompt:dzT("sonvfx.postia.prompt"),devis_calcul:dzT("sonvfx.postia.devis_calcul"),apercu_ia:dzT("sonvfx.postia.apercu_ia"),
u:{s:dzT("sonvfx.postia.u_s"),mp:dzT("sonvfx.postia.u_mp"),video:dzT("sonvfx.postia.u_video"),tranche10s:dzT("sonvfx.postia.u_tranche10s"),
son:dzT("sonvfx.postia.u_son"),effet:dzT("sonvfx.postia.u_effet")},a_mesurer:dzT("ia.prix.a_mesurer"),
look_titre:dzT("sonvfx.postia.look_titre"),look_aide:dzT("sonvfx.postia.look_aide"),look_phrase:dzT("sonvfx.postia.look_phrase"),
look_moteur:dzT("sonvfx.postia.look_moteur"),look_auto:dzT("sonvfx.postia.look_auto"),look_proposer:dzT("sonvfx.postia.look_proposer"),
look_calcul:dzT("sonvfx.postia.look_calcul"),look_prop:dzT("sonvfx.postia.look_prop"),look_remplacer:dzT("sonvfx.postia.look_remplacer"),
look_ajouter:dzT("sonvfx.postia.look_ajouter"),look_ecarter:dzT("sonvfx.postia.look_ecarter")};
}
/* t279 : noms des générateurs et de leurs réglages dans la langue de l'interface (le serveur sert le libellé
   de registre, en français) ; un nom propre (Hunyuan, ThinkSound, ElevenLabs, Decart) garde le libellé servi */
function dzSvoNomGen(g){return ({"vfx:inserer-h3":dzT("vfx.ia.inserer_h3.titre"),"vfx:effacer-perso":dzT("vfx.ia.effacer_perso.titre"),
"vfx:effacer-objet":dzT("vfx.ia.effacer_objet.titre"),"vfx:jour-nuit":dzT("vfx.ia.jour_nuit.titre"),"vfx:eau":dzT("vfx.ia.eau.titre"),
"vfx:coloriser":dzT("vfx.ia.coloriser.titre"),"vfx:retoucher-kling":dzT("vfx.ia.retoucher_kling.titre"),
"vfx:retoucher-flux3":dzT("vfx.ia.retoucher_flux3.titre"),"vfx:recadrer":dzT("vfx.ia.recadrer.titre"),"vfx:agrandir":dzT("vfx.ia.agrandir.titre"),
"video_post:interpoler-film":dzT("sonvfx.postia.g_interpoler_film"),"sfx_video:sonilo-video":dzT("son.sfx.libelle.sonilo_video"),
"sfx_video:mirelo-video":dzT("son.sfx.libelle.mirelo_video"),"sfx_video:kling-v2a":dzT("son.sfx.libelle.kling_v2a")})[g.id]||g.label;}
function dzSvoOptLbl(k){return ({resolution:dzT("vfx.ia.opt.resolution"),aspect_ratio:dzT("vfx.ia.opt.format"),seed:dzT("vfx.ia.opt.graine"),
start_time:dzT("vfx.ia.opt.debut"),resume_time:dzT("vfx.ia.opt.reprise"),duration:dzT("vfx.ia.opt.duree"),color_match:dzT("vfx.ia.opt.couleurs"),
enable_prompt_expansion:dzT("vfx.ia.opt.enrichir"),mask_prompt:dzT("vfx.ia.opt.objet"),enable_pass2_refinement:dzT("vfx.ia.opt.passe2"),
upscale_factor:dzT("vfx.ia.opt.facteur"),num_frames:dzT("sonvfx.postia.opt_images")})[k]||k.replace(/_/g," ");}
function dzSvoUsd(v){v=Number(v)||0;return v>=1?v.toFixed(2):v.toFixed(3);}
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
function dzSvoEnvoi(pile){return pile.map(function(m){return m.ia?{ia:m.ia,prompt:m.prompt,options:m.options,masque:m.masque}:{preset:m.preset,intensite:m.intensite,masque:m.masque,params:m.params};});}
/* t277 : les maillons locaux (ceux que montre l'aperçu) et les maillons IA visibles (ceux qui coûtent) */
function dzSvoLocaux(pile){return pile.filter(function(m){return !m.ia;});}
function dzSvoIaActifs(pile){return pile.filter(function(m){return m.ia&&!m.masque;});}
/* un maillon IA neuf : consigne vide, options au défaut du schéma du générateur */
function dzSvoMaillonIa(g,n){
var options={};
Object.keys(g.options||{}).forEach(function(k){var d=g.options[k].defaut;if(d!==null&&d!==void 0&&d!=="")options[k]=d;});
return {id:"m"+n,ia:g.id,prompt:"",options:options,masque:false};
}
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
var T2=dzSvoTextesIa();
var gn=US(null),gen=gn[0],setGen=gn[1];
var dv=US(null),devis=dv[0],setDevis=dv[1];
var ap=US(false),armeP=ap[0],setArmeP=ap[1];
var lp=US(""),lphrase=lp[0],setLphrase=lp[1];
var lm=US(""),lmoteur=lm[0],setLmoteur=lm[1];
var lo=US(null),lprop=lo[0],setLprop=lo[1];
var lc=US(false),lcalc=lc[0],setLcalc=lc[1];
var dreq=UR(0);
function chargerSources(){return fetch("/api/post/sources").then(dzSvpJson).then(function(d){setSrcs(d);}).catch(function(e){setErr(e.message);});}
UE(function(){
fetch("/api/post/catalogue").then(dzSvpJson).then(function(d){setCat(d);}).catch(function(e){setErr(e.message);});
fetch("/api/post/presets").then(dzSvpJson).then(function(d){setPresets(d.presets||[]);}).catch(function(){});
fetch("/api/post/generateurs").then(dzSvpJson).then(function(d){setGen(d);}).catch(function(){});
chargerSources();
return function(){dzSvoLiberer(urls.current);};
},[]);
/* l'aperçu suit la source, l'instant et la pile, après un court délai ; une réponse dépassée est jetée */
var cle=src?JSON.stringify([src.job_id,t,dzSvoEnvoi(dzSvoLocaux(pile))]):"";
UE(function(){
if(!src)return;
var k=++req.current;
setCalc(true);
var h=setTimeout(function(){
var base={source:src.job_id,t:t,largeur:DZSVO_LARGEUR};
Promise.all([dzSvoImage(Object.assign({pile:[]},base)),dzSvoImage(Object.assign({pile:dzSvoEnvoi(dzSvoLocaux(pile))},base))]).then(function(res){
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
/* t277 : une pile payante demande son devis (après le même court délai) ; tout changement désarme le rendu */
var iaActifs=dzSvoIaActifs(pile);
var cleDevis=src&&iaActifs.length?JSON.stringify([src.job_id,dzSvoEnvoi(pile)]):"";
UE(function(){
setArmeP(false);
if(!cleDevis){setDevis(null);return;}
var k=++dreq.current;
setDevis({calcul:true});
var h=setTimeout(function(){
dzSvoPost("/api/post/devis",{source:src.job_id,pile:dzSvoEnvoi(pile)}).then(dzSvpJson).then(function(d){if(k===dreq.current)setDevis(d);}).catch(function(e){if(k===dreq.current){setDevis(null);setErr(e.message);}});
},DZSVO_DELAI);
return function(){clearTimeout(h);};
},[cleDevis]);
var pmax=cat&&cat.pile_max||24;
var actifs=pile.filter(function(m){return m.ia?!m.masque:!m.masque&&m.intensite>0;}).length;
var gens=gen&&gen.generateurs||[],gdict={};
gens.forEach(function(g){gdict[g.id]=g;});
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
function ajouterIa(g){
n.current++;
var m=dzSvoMaillonIa(g,n.current);
setPile(function(a){return a.length>=pmax?a:a.concat([m]);});
setOuvert(m.id);
}
function majOpt(id,k,v){maj(id,function(m){var q={};q[k]=v;return {options:Object.assign({},m.options,q)};});}
function maj(id,f){setPile(function(a){return a.map(function(m){return m.id===id?Object.assign({},m,f(m)):m;});});}
function majParam(id,k,v){maj(id,function(m){var q={};q[k]=v;return {params:Object.assign({},m.params,q)};});}
function dupliquer(id){
n.current++;
var nid="m"+n.current;
setPile(function(a){var i=a.findIndex(function(m){return m.id===id;});if(i<0||a.length>=pmax)return a;
var b=a.slice();b.splice(i+1,0,Object.assign({},a[i],{id:nid},a[i].ia?{options:Object.assign({},a[i].options)}:{params:Object.assign({},a[i].params)}));return b;});
}
function supprimer(id){setPile(function(a){return a.filter(function(m){return m.id!==id;});});}
function deplacer(de,vers){setPile(function(a){return dzSvoDeplacer(a,de,vers);});}
function enregistrer(){
var nom=pnom.trim();
if(!nom||!pile.length)return;
dzSvoPost("/api/post/presets",{nom:nom,pile:dzSvoEnvoi(dzSvoLocaux(pile))}).then(dzSvpJson).then(function(e){
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
/* une pile payante : le premier clic arme (le coût s'affiche sur le bouton), le second rend avec confirme_cout */
function rendre(){
if(!src||!actifs||enCours)return;
if(iaActifs.length&&!armeP){setArmeP(true);return;}
setErr("");setArmeP(false);
var corps={source:src.job_id,pile:dzSvoEnvoi(pile),titre:rtitre.trim()};
if(iaActifs.length)corps.confirme_cout=true;
dzSvoPost("/api/post/rendre",corps).then(dzSvpJson).then(function(d){
setJob({id:d.job_id,status:"queued",progress:0,error:""});
}).catch(function(e){setErr(e.message);});
}
/* « Décrire le look » : la pile proposée s'affiche ; elle ne remplace ou ne rejoint la pile que sur un clic */
function proposer(){
var ph=lphrase.trim();
if(!ph||lcalc)return;
setLcalc(true);setErr("");
var corps={phrase:ph};
if(lmoteur)corps.moteur=lmoteur;
dzSvoPost("/api/post/decrire",corps).then(dzSvpJson).then(function(d){setLprop(d);setLcalc(false);}).catch(function(e){setErr(e.message);setLcalc(false);});
}
function prendre(remplacer){
if(!lprop)return;
var neufs=(lprop.pile||[]).filter(function(m){return cdict[m.preset];}).map(function(m){n.current++;return Object.assign({},m,{id:"m"+n.current,params:Object.assign({},m.params)});});
setPile(function(a){return remplacer?neufs.slice(0,pmax):a.concat(neufs.slice(0,Math.max(0,pmax-a.length)));});
setLprop(null);setOuvert(null);
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
function optionIa(m,k,o){
var v=m.options[k]!==void 0?m.options[k]:o.defaut;
var lbl=r.jsx("span",{className:"dzsvo-rnom",children:dzSvoOptLbl(k)},"n");
if(o.choix)return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("select",{className:"dzsvo-sel",value:v===null||v===void 0?"":String(v),"data-sv-post":"ia-opt-"+k,onChange:function(e){majOpt(m.id,k,e.target.value);},
children:o.choix.map(function(c){return r.jsx("option",{value:String(c),children:String(c)},String(c));})},"s")]},k);
if(o.bool)return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("input",{type:"checkbox",checked:!!v,"data-sv-post":"ia-opt-"+k,onChange:function(e){majOpt(m.id,k,e.target.checked);}},"i")]},k);
if(o.num)return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("input",{className:"dzsvo-champ",type:"number",min:o.num[0],max:o.num[1],step:o.entier?1:"any",value:v===null||v===void 0?"":v,"data-sv-post":"ia-opt-"+k,onChange:function(e){var x=e.target.value;majOpt(m.id,k,x===""?null:Number(x));}},"i")]},k);
return r.jsxs("label",{className:"dzsvo-regle",children:[lbl,
r.jsx("input",{className:"dzsvo-champ",type:"text",value:v===null||v===void 0?"":String(v),"data-sv-post":"ia-opt-"+k,onChange:function(e){majOpt(m.id,k,e.target.value);}},"i")]},k);
}
function ligneIa(m,i){
var g=gdict[m.ia]||{id:m.ia,label:m.ia,options:{},prompt:null};var gnom=dzSvoNomGen(g);
var dep=ouvert===m.id;
return r.jsxs("div",{className:"dzsvo-maillon dzsvo-mia","data-sv-post":"maillon","data-preset":"ia","data-ia":m.ia,"data-masque":m.masque?"true":"false",draggable:true,
onDragStart:function(e){glisse.current=i;try{e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",String(i));}catch(e2){}},
onDragOver:function(e){e.preventDefault();},
onDrop:function(e){e.preventDefault();var de=glisse.current;glisse.current=-1;deplacer(de,i);},
children:[r.jsxs("div",{className:"dzsvo-mtete",children:[
r.jsx("span",{className:"dzsvo-poignee",title:T.glisser,children:__dzGl("dz-action-poignee",14)},"g"),
r.jsx("button",{type:"button",className:"dzsvo-mnom","aria-expanded":dep?"true":"false","data-sv-post":"deplier",title:gnom,onClick:function(){setOuvert(dep?null:m.id);},children:(i+1)+". "+gnom},"n"),
mini("masquer",m.masque?T.afficher:T.masquer,m.masque?"dz-calque-masque":"dz-etat-visible",{"aria-pressed":m.masque?"true":"false",onClick:function(){maj(m.id,function(a){return {masque:!a.masque};});}}),
mini("monter",T.monter,"dz-edit-monter",{disabled:i===0,onClick:function(){deplacer(i,i-1);}}),
mini("descendre",T.descendre,"dz-edit-descendre",{disabled:i===pile.length-1,onClick:function(){deplacer(i,i+1);}}),
mini("dupliquer",T.dupliquer,"dz-action-dupliquer",{disabled:pile.length>=pmax,onClick:function(){dupliquer(m.id);}}),
mini("supprimer",T.supprimer,"dz-action-supprimer",{onClick:function(){supprimer(m.id);}})]},"t"),
r.jsx("span",{className:"dzsvo-payant",children:T2.payant},"p"),
g.prompt?r.jsx("textarea",{className:"dzsvo-champ dzsvo-consigne",rows:2,maxLength:2000,value:m.prompt,"data-sv-post":"ia-prompt","aria-label":T2.prompt,placeholder:T2.prompt,onChange:function(e){var v=e.target.value;maj(m.id,function(){return {prompt:v};});}},"c"):null,
dep&&Object.keys(g.options||{}).length?r.jsx("div",{className:"dzsvo-reglages",children:Object.keys(g.options).map(function(k){return optionIa(m,k,g.options[k]);})},"o"):null]},m.id);
}
function ligne(m,i){
if(m.ia)return ligneIa(m,i);
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
gens.length?r.jsxs("div",{className:"dzsvo-section","data-sv-post":"generer",children:[
r.jsx("div",{className:"dzsvo-titre",children:T2.generer},"t"),
r.jsx("div",{className:"dzsvo-aide",children:T2.generer_aide},"a"),
DZSVO_FOURNS.filter(function(f){return gens.some(function(g){return g.fournisseur===f;});}).map(function(f){
return r.jsxs("div",{className:"dzsvo-fourn","data-sv-post":"fourn-"+f,children:[r.jsx("div",{className:"dzsvo-fnom",children:DZSVO_FOURN[f]},"n"),
gens.filter(function(g){return g.fournisseur===f;}).map(function(g){
var prix=g.note==="a_mesurer"||!g.usd?T2.a_mesurer:dzT("sonvfx.postia.prix",{usd:dzSvoUsd(g.usd),unite:T2.u[g.unite]||g.unite});
return r.jsxs("button",{type:"button",className:"dzsvo-gen","data-sv-post":"gen-"+g.id,"data-cle":g.dispo?void 0:g.cle,"data-famille":g.famille,
"aria-label":dzT("sonvfx.post.ajouter",{nom:dzSvoNomGen(g)}),disabled:pile.length>=pmax,onClick:function(){ajouterIa(g);},
children:[__dzGl("dz-etat-ia",12),r.jsx("span",{className:"dzsvo-gnom",children:dzSvoNomGen(g)},"n"),r.jsx("span",{className:"dzsvo-gprix",children:prix},"p"),
g.dispo?null:r.jsx("span",{className:"dzsvo-gcle","data-sv-cle":g.cle,children:dzT("ia.cle.a_ajouter",{cle:g.cle})},"k")]},g.id);})]},f);})]},"generer"):null,
r.jsxs("div",{className:"dzsvo-section","data-sv-post":"look",children:[
r.jsx("div",{className:"dzsvo-titre",children:T2.look_titre},"t"),
r.jsx("div",{className:"dzsvo-aide",children:T2.look_aide},"a"),
r.jsx("textarea",{className:"dzsvo-champ dzsvo-consigne",rows:2,maxLength:400,value:lphrase,"data-sv-post":"look-phrase","aria-label":T2.look_titre,placeholder:T2.look_phrase,onChange:function(e){setLphrase(e.target.value);}},"p"),
r.jsxs("div",{className:"dzsvo-ctl",children:[
r.jsxs("select",{className:"dzsvo-sel","data-sv-post":"look-moteur","aria-label":T2.look_moteur,value:lmoteur,onChange:function(e){setLmoteur(e.target.value);},
children:[r.jsx("option",{value:"",children:T2.look_auto},""),(gen&&gen.moteurs_texte||[]).map(function(m){
return r.jsx("option",{value:m.id,children:m.label+(m.dispo||!m.cle?"":" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}))},m.id);})]},"s"),
r.jsx("button",{type:"button",className:"dzsvo-btn","data-sv-post":"look-proposer",disabled:!lphrase.trim()||lcalc,onClick:proposer,children:lcalc?T2.look_calcul:T2.look_proposer},"b")]},"c"),
lprop?r.jsxs("div",{className:"dzsvo-proposition","data-sv-post":"look-proposition",role:"status",children:[
r.jsx("div",{className:"dzsvo-aide",children:T2.look_prop},"t"),
lprop.pile.map(function(m,k){return r.jsx("div",{className:"dzsvo-pitem","data-sv-post":"look-item",children:(k+1)+". "+(T.p[m.preset]||m.preset)+" · "+m.intensite+" %"},k);}),
r.jsxs("div",{className:"dzsvo-ctl",children:[
r.jsx("button",{type:"button",className:"dzsvo-btn prim","data-sv-post":"look-remplacer",onClick:function(){prendre(true);},children:T2.look_remplacer},"r"),
r.jsx("button",{type:"button",className:"dzsvo-btn","data-sv-post":"look-ajouter",onClick:function(){prendre(false);},children:T2.look_ajouter},"a"),
r.jsx("button",{type:"button",className:"dzsvo-lien","data-sv-post":"look-ecarter",onClick:function(){setLprop(null);},children:T2.look_ecarter},"e")]},"c")]},"prop"):null]},"look"),
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
devis?r.jsxs("div",{className:"dzsvo-note","data-sv-post":"devis",role:"status",children:[
r.jsx("div",{children:devis.calcul?T2.devis_calcul:dzT("sonvfx.postia.devis",{usd:dzSvoUsd(devis.usd)})},"u"),
devis.cles&&devis.cles.length?r.jsx("div",{className:"dzsvo-gcle",children:dzT("sonvfx.postia.cles",{cles:devis.cles.join(", ")})},"k"):null]},"dv"):null,
r.jsxs("button",{type:"button",className:"dzsvo-btn prim","data-sv-post":"rendre","data-arme":armeP?"":void 0,"aria-label":!armeP?T.rendre:dzT("sonvfx.postia.confirmer",{usd:dzSvoUsd(devis&&devis.usd)}),disabled:!src||!actifs||enCours||!!(devis&&devis.calcul),onClick:rendre,
children:[__dzGl("dz-edit-effet",14),r.jsx("span",{children:armeP?dzT("sonvfx.postia.confirmer",{usd:dzSvoUsd(devis&&devis.usd)}):T.rendre},"l")]},"b"),
r.jsx("div",{className:"dzsvo-aide",children:iaActifs.length?T2.apercu_ia:T.local},"a"),
job?r.jsx("div",{className:"dzsvo-note"+(job.status==="failed"?" dzsvo-erreur":""),"data-sv-post":"job",role:"status",
children:job.status==="done"?T.rendu_ok:job.status==="failed"?dzT("sonvfx.post.rendu_ko",{err:job.error}):dzT("sonvfx.post.rendu_cours",{pct:job.progress})},"j"):null,
job&&job.status==="done"?r.jsx("button",{type:"button",className:"dzsvo-btn","data-sv-post":"montage",onClick:function(){p.go&&p.go("montage");},children:T.vers_montage},"m"):null]},"export")]},"pile");
return r.jsxs("div",{className:"dzsvo","data-sv-post":"page",children:[colSrc,vue,colPile]});
}
