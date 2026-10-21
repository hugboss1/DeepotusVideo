/* sonvfx-voix.js — t273 (21/10/2026) : la page « Voix off » de Son & VFX, repensée. Elle remplace la vue Voix off de
   l'écran d'origine (DzSonVfx, couche L4 non touchée, gardée montée et masquée par le hub) et son encart de
   post-traitement, qui n'avait rien à faire dans une vue audio.
   Trois zones : à gauche la bibliothèque de voix (recherche, filtres langue / genre / âge / style, écoute, favoris
   gardés dans ce navigateur, « Cloner une voix ») ; au centre le script (champ IA, balises Eleven v3 groupées en
   puces repliables insérées au curseur, compteur de caractères, coût affiché AVANT) ; à droite les réglages (modèle,
   stabilité, similarité, vitesse, langue). Sous le script, le résultat : forme d'onde, versions successives et les
   retouches rapides (couper, fondu, normaliser, de-ess par le moteur de graphe t270 ; ducking ; améliorer ; isoler).
   Payant (synthèse ElevenLabs, isolation) : armé au premier clic avec le devis du serveur, envoyé au second. Voicebox
   (local) : un seul clic, gratuit. Un modèle sans clé reste choisissable : le serveur refuse au lancement (503).
   SOURCE du maillon de queue dzsonvfx, posée APLATIE (mêmes règles d'écriture que sonvfx-pistes.js : une
   instruction par ligne terminée par « ; », aucune ligne qui commence par « ( » ou « [ », aucun « // »,
   commentaires sur des lignes entières seulement). Symboles du bundle : r, x, dzT, __dzGl ; de la page Pistes :
   dzSvpJson, dzSvpDuree, dzSvpVersAtelier. Aucun arrondi (angles vifs, règle du hub).
   Routes : GET /api/voices, /api/voice-tags, /api/voice-models, /api/audio, /api/audio/meta ;
   POST /api/cost/estimate {kind: elevenlabs | isolate}, /api/audio/voiceover, /api/audio/graph/rendre,
   /api/audio/duck, /api/audio/enhance, /api/audio/isolate, /api/voices/clone. */
var DZSVV_FAV="dz_sv_voix_favoris";
var DZSVV_FILTRES=["langue","genre","age","style"];
var DZSVV_GROUPES=["emotion","voix","sons","special"];
var DZSVV_PLAT=[30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30];
var DZSVV_STAB=[0,0.5,1];
function dzSvvLireFav(){try{var t=localStorage.getItem(DZSVV_FAV);var a=t?JSON.parse(t):[];return Array.isArray(a)?a.filter(function(v){return typeof v==="string";}):[];}catch(e){return [];}}
function dzSvvGarderFav(a){try{localStorage.setItem(DZSVV_FAV,JSON.stringify(a));}catch(e){}}
/* une voix du serveur → {id, nom, clonee, apercu, langue, genre, age, style} (étiquettes ElevenLabs ; Voicebox n'en a pas) */
function dzSvvVoix(v){
var lb=v.labels||{};
return {id:v.voice_id,nom:v.name||v.voice_id,clonee:v.category==="cloned",apercu:v.preview_url||null,
langue:String(v.language||lb.language||lb.accent||"").toLowerCase(),genre:String(lb.gender||"").toLowerCase(),
age:String(lb.age||"").toLowerCase(),style:String(lb.use_case||lb.descriptive||"").toLowerCase()};
}
function dzSvvValeurs(liste,cle){
var vu={},out=[];
liste.forEach(function(v){var k=v[cle];if(k&&!vu[k]){vu[k]=1;out.push(k);}});
return out.sort();
}
function dzSvvEtiq(cle,v){
var T={genre:{male:dzT("sonvfx.voix.genre_homme"),female:dzT("sonvfx.voix.genre_femme"),neutral:dzT("sonvfx.voix.genre_neutre")},
age:{young:dzT("sonvfx.voix.age_jeune"),middle_aged:dzT("sonvfx.voix.age_moyen"),old:dzT("sonvfx.voix.age_age")}};
var t=T[cle]&&T[cle][v];
return t||String(v).replace(/_/g," ");
}
function dzSvvPrix(u){return u==null?"":"~$"+Number(u).toFixed(Number(u)<0.1?4:2);}
function dzSvvDevis(op){
return fetch("/api/cost/estimate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(op)}).then(function(res){return res.ok?res.json():null;}).then(function(D){return D&&typeof D.total_usd==="number"?D.total_usd:null;}).catch(function(){return null;});
}
function dzSvvPost(u,corps){
return fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)}).then(dzSvpJson);
}
/* une retouche locale = un graphe de trois nœuds (source → traitement → sortie) rendu par /api/audio/graph/rendre */
function dzSvvGraphe(fichier,noeud){
return {noeuds:[{id:"src",type:"source",params:{fichier:fichier}},Object.assign({id:"fx"},noeud),{id:"out",type:"sortie",params:{}}],
liens:[{de:"src",vers:"fx",entree:0},{de:"fx",vers:"out",entree:0}]};
}
function dzSvvTextes(){
return {filtre:{langue:dzT("sonvfx.voix.filtre_langue"),genre:dzT("sonvfx.voix.filtre_genre"),age:dzT("sonvfx.voix.filtre_age"),style:dzT("sonvfx.voix.filtre_style")},
grp:{emotion:dzT("sonvfx.voix.grp_emotion"),voix:dzT("sonvfx.voix.grp_voix"),sons:dzT("sonvfx.voix.grp_sons"),special:dzT("sonvfx.voix.grp_special")},
r:{stability:dzT("sonvfx.voix.r_stability"),similarity_boost:dzT("sonvfx.voix.r_similarity_boost"),speed:dzT("sonvfx.voix.r_speed")},
stab:{"0":dzT("sonvfx.voix.stab_0"),"0.5":dzT("sonvfx.voix.stab_0_5"),"1":dzT("sonvfx.voix.stab_1")},
o:{generee:dzT("sonvfx.voix.o_generee"),coupe:dzT("sonvfx.voix.o_coupe"),fondu:dzT("sonvfx.voix.o_fondu"),normalise:dzT("sonvfx.voix.o_normalise"),
deess:dzT("sonvfx.voix.o_deess"),ducking:dzT("sonvfx.voix.o_ducking"),ameliore:dzT("sonvfx.voix.o_ameliore"),isole:dzT("sonvfx.voix.o_isole")}};
}
function dzSvvMemo(){try{return window.__dzSvVoix||{};}catch(e){return {};}}
function DzSvVoix(p){
var US=x.useState,UE=x.useEffect,UR=x.useRef;
var memo=dzSvvMemo(),T=dzSvvTextes();
var s1=US(null),voix=s1[0],setVoix=s1[1];
var s2=US(""),q=s2[0],setQ=s2[1];
var s3=US({langue:"",genre:"",age:"",style:""}),filtres=s3[0],setFiltres=s3[1];
var s4=US(dzSvvLireFav),favoris=s4[0],setFavoris=s4[1];
var s5=US(!1),seulFav=s5[0],setSeulFav=s5[1];
var s6=US(memo.voix||""),sel=s6[0],setSel=s6[1];
var s7=US(""),ecoute=s7[0],setEcoute=s7[1];
var s8=US(null),balises=s8[0],setBalises=s8[1];
var s9=US({}),ouverts=s9[0],setOuverts=s9[1];
var s10=US(memo.texte||""),texte=s10[0],setTexte=s10[1];
var s11=US(null),modeles=s11[0],setModeles=s11[1];
var s12=US(memo.modele||""),modele=s12[0],setModele=s12[1];
var s13=US({stability:0.5,similarity_boost:0.75,speed:1}),regl=s13[0],setRegl=s13[1];
var s14=US(memo.langue||"fr"),langue=s14[0],setLangue=s14[1];
var s15=US(null),cout=s15[0],setCout=s15[1];
var s16=US(null),arme=s16[0],setArme=s16[1];
var s17=US(""),occupe=s17[0],setOccupe=s17[1];
var s18=US(""),note=s18[0],setNote=s18[1];
var s19=US(memo.versions||[]),versions=s19[0],setVersions=s19[1];
var s20=US(memo.cur||""),cur=s20[0],setCur=s20[1];
var s21=US({}),pics=s21[0],setPics=s21[1];
var s22=US({pos:0,dur:0,joue:!1}),lect=s22[0],setLect=s22[1];
var s23=US({debut:0,fin:0,fondu_entree:0.5,fondu_sortie:1,lufs:-16,deess:50,musique:"",music_db:-14}),out=s23[0],setOut=s23[1];
var s24=US(null),armeIso=s24[0],setArmeIso=s24[1];
var s25=US({ouvert:!1,nom:"",fichiers:[],droit:!1,arme:!1}),clone=s25[0],setClone=s25[1];
var s26=US({liste:[],meta:{}}),biblio=s26[0],setBiblio=s26[1];
var apercu=UR(null),champ=UR(null),lecteur=UR(null),tour=UR(0);
function chargerVoix(choisir){
return fetch("/api/voices").then(dzSvpJson).then(function(D){
var L=(D.voices||[]).map(dzSvvVoix);
L.sort(function(a,b){return (b.clonee?1:0)-(a.clonee?1:0);});
setVoix({enabled:!!D.enabled,provider:D.provider||"",liste:L});
setSel(function(c0){
if(choisir)return choisir;
if(c0&&L.some(function(v){return v.id===c0;}))return c0;
return (L[0]||{}).id||"";
});
}).catch(function(){setVoix({enabled:!1,provider:"",liste:[]});});
}
function chargerBiblio(){
return Promise.all([fetch("/api/audio").then(dzSvpJson),fetch("/api/audio/meta").then(dzSvpJson)]).then(function(R){setBiblio({liste:R[0].audio||[],meta:R[1].meta||{}});}).catch(function(){});
}
UE(function(){
chargerVoix();
chargerBiblio();
fetch("/api/voice-tags").then(dzSvpJson).then(function(D){setBalises(D&&D.groups?D:{groups:{},providers:{}});}).catch(function(){setBalises({groups:{},providers:{}});});
fetch("/api/voice-models").then(dzSvpJson).then(function(D){setModeles(D);setModele(function(m0){return m0&&(D.models||[]).some(function(m){return m.id===m0;})?m0:D["default"]||((D.models||[])[0]||{}).id||"";});}).catch(function(){setModeles({models:[]});});
return function(){if(apercu.current){apercu.current.pause();apercu.current=null;}};
},[]);
/* la page est démontée à chaque changement de sous-onglet : voix, texte, modèle, langue et versions sont gardés */
UE(function(){try{window.__dzSvVoix={voix:sel,texte:texte,modele:modele,langue:langue,versions:versions,cur:cur};}catch(e){}});
var eleven=!!(balises&&balises.providers&&balises.providers.elevenlabs);
var vbox=!!(balises&&balises.providers&&balises.providers.voicebox);
var mlist=(modeles&&modeles.models)||[];
var mod=mlist.find(function(m){return m.id===modele;})||null;
var maxc=mod&&mod.max_chars||5000;
var v3=modele==="eleven_v3";
/* coût affiché AVANT, relu au serveur à chaque changement du texte ou du modèle (le même chiffre que la garde) */
UE(function(){
if(balises===null||vbox||!texte.trim()){setCout(null);return;}
var k=++tour.current;
dzSvvDevis({kind:"elevenlabs",chars:texte.length,model:modele||void 0}).then(function(u){if(k===tour.current)setCout(u);});
},[texte.length,modele,vbox,balises===null]);
UE(function(){setArme(null);},[texte,modele,sel,langue,regl.stability,regl.similarity_boost,regl.speed]);
UE(function(){setArmeIso(null);},[cur]);
/* forme d'onde de la version écoutée (WebAudio) ; sans WebAudio, une ligne plate */
UE(function(){
var v=versions.find(function(t){return t.nom===cur;});
if(!v||pics[v.nom])return;
var AC=window.AudioContext||window.webkitAudioContext;
if(!AC)return;
fetch(v.url).then(function(res){return res.arrayBuffer();}).then(function(buf){
var ctx=new AC();
return ctx.decodeAudioData(buf).then(function(ab){
var ch=ab.getChannelData(0),n=DZSVV_PLAT.length,bl=Math.max(1,Math.floor(ch.length/n)),P=[],mx=0;
for(var i=0;i<n;i++){var m=0;for(var j=i*bl;j<(i+1)*bl;j+=64){var a=Math.abs(ch[j]||0);if(a>m)m=a;}P.push(m);if(m>mx)mx=m;}
setPics(function(P0){var o=Object.assign({},P0);o[v.nom]=P.map(function(m){return Math.round(8+88*(mx?m/mx:0));});return o;});
if(ctx.close)ctx.close();
});
}).catch(function(){});
},[cur]);
var liste=(voix&&voix.liste)||[];
var qq=q.trim().toLowerCase();
var visibles=liste.filter(function(v){
if(seulFav&&favoris.indexOf(v.id)<0)return !1;
if(qq&&(v.nom+" "+v.langue+" "+v.style).toLowerCase().indexOf(qq)<0)return !1;
return DZSVV_FILTRES.every(function(f){return !filtres[f]||v[f]===filtres[f];});
});
function filtrer(f,val){setFiltres(function(F){var o=Object.assign({},F);o[f]=val;return o;});}
function basculerFav(id){
var a=favoris.indexOf(id)>=0?favoris.filter(function(v){return v!==id;}):favoris.concat([id]);
setFavoris(a);
dzSvvGarderFav(a);
}
function ecouter(v){
if(apercu.current){apercu.current.pause();apercu.current=null;}
if(ecoute===v.id){setEcoute("");return;}
if(!v.apercu){setEcoute("");setNote(dzT("sonvfx.voix.apercu_absent",{nom:v.nom}));return;}
var a=new Audio(v.apercu);
apercu.current=a;
setEcoute(v.id);
a.onended=function(){setEcoute("");};
var pr=a.play();
if(pr&&pr.catch)pr.catch(function(){setEcoute("");setNote(dzT("sonvfx.voix.lecture_bloquee"));});
}
function ligneVoix(v){
var fav=favoris.indexOf(v.id)>=0,bits=[v.langue,v.genre?dzSvvEtiq("genre",v.genre):"",v.age?dzSvvEtiq("age",v.age):"",v.style?dzSvvEtiq("style",v.style):""].filter(Boolean);
return r.jsxs("div",{className:"dzsvv-voix","data-sel":v.id===sel?"":void 0,"data-voix":v.id,children:[
r.jsxs("button",{type:"button",className:"dzsvv-vnom","aria-pressed":v.id===sel?"true":"false",onClick:function(){setSel(v.id);},children:[
r.jsx("span",{className:"dzsvv-vn",children:v.nom}),
v.clonee?r.jsx("span",{className:"dzsvv-pastille",children:dzT("sonvfx.voix.clonee")}):null,
r.jsx("span",{className:"dzsvv-vmeta",children:bits.join(" · ")})]}),
r.jsx("button",{type:"button",className:"dzsvv-mini","data-sv-voix":"ecouter","aria-pressed":ecoute===v.id?"true":"false",title:dzT("sonvfx.voix.ecouter_nom",{nom:v.nom}),"aria-label":dzT("sonvfx.voix.ecouter_nom",{nom:v.nom}),onClick:function(){ecouter(v);},children:__dzGl(ecoute===v.id?"dz-media-pause":"dz-media-lecture",14)}),
r.jsx("button",{type:"button",className:"dzsvv-mini","data-sv-voix":"favori","aria-pressed":fav?"true":"false",title:!fav?dzT("sonvfx.voix.favori_ajouter"):dzT("sonvfx.voix.favori_retirer"),"aria-label":(!fav?dzT("sonvfx.voix.favori_ajouter"):dzT("sonvfx.voix.favori_retirer"))+" : "+v.nom,onClick:function(){basculerFav(v.id);},children:__dzGl("dz-action-favori",14)})]},v.id);
}
function choixFiltre(f){
var vals=dzSvvValeurs(liste,f);
return r.jsxs("select",{className:"dzsvv-sel","data-filtre":f,value:filtres[f],"aria-label":T.filtre[f],onChange:function(e){filtrer(f,e.target.value);},children:[
r.jsx("option",{value:"",children:T.filtre[f]}),
vals.map(function(v){return r.jsx("option",{value:v,children:f==="langue"?v:dzSvvEtiq(f,v)},v);})]},f);
}
/* clonage : nom, prises du dossier audio, droit attesté ; un clone occupe un emplacement de voix du compte : armé puis envoyé */
var prises=biblio.liste.filter(function(it){var k=(biblio.meta[it.name]||{}).kind;return k!=="stem"&&k!=="musique"&&k!=="sfx";}).slice(0,60);
function majClone(o){setClone(function(C){return Object.assign({},C,o,{arme:!1});});}
function basculerPrise(n){majClone({fichiers:clone.fichiers.indexOf(n)>=0?clone.fichiers.filter(function(f){return f!==n;}):clone.fichiers.concat([n])});}
var clonable=!!clone.nom.trim()&&clone.fichiers.length>0&&clone.droit&&occupe!=="cloner";
function cloner(){
if(!clonable)return;
if(!clone.arme){setClone(function(C){return Object.assign({},C,{arme:!0});});return;}
setOccupe("cloner");
setNote("");
dzSvvPost("/api/voices/clone",{nom:clone.nom.trim(),fichiers:clone.fichiers,description:"",droit:!0}).then(function(D){
setOccupe("");
setClone({ouvert:!1,nom:"",fichiers:[],droit:!1,arme:!1});
setNote(dzT("sonvfx.voix.clone_fait",{nom:D.voice_name})+(D.requires_verification?" "+dzT("sonvfx.voix.clone_verif"):""));
return chargerVoix(D.voice_id);
}).catch(function(err){setOccupe("");setClone(function(C){return Object.assign({},C,{arme:!1});});setNote(String(err&&err.message||err));});
}
var panneauClone=clone.ouvert?r.jsxs("div",{className:"dzsvv-clone",children:[
r.jsx("input",{className:"dzsvv-champ","data-sv-voix":"clone-nom",type:"text",maxLength:100,value:clone.nom,placeholder:dzT("sonvfx.voix.clone_nom"),"aria-label":dzT("sonvfx.voix.clone_nom"),onChange:function(e){majClone({nom:e.target.value});}}),
r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.clone_prises")}),
r.jsx("div",{className:"dzsvv-prises",children:prises.length?prises.map(function(it){var on=clone.fichiers.indexOf(it.name)>=0;return r.jsx("button",{type:"button",className:"dzsvv-prise","aria-pressed":on?"true":"false","data-prise":it.name,onClick:function(){basculerPrise(it.name);},children:it.name},it.name);}):r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.clone_sans_prise")})}),
r.jsxs("label",{className:"dzsvv-droit",children:[
r.jsx("input",{type:"checkbox","data-sv-voix":"clone-droit",checked:clone.droit,onChange:function(e){majClone({droit:!!e.target.checked});}}),
r.jsx("span",{children:dzT("sonvfx.voix.clone_droit")})]}),
r.jsx("button",{type:"button",className:"dzsvv-btn prim","data-sv-voix":"cloner","data-arme":clone.arme?"":void 0,disabled:!clonable,onClick:cloner,
children:occupe!=="cloner"&&!clone.arme?dzT("sonvfx.voix.cloner"):occupe==="cloner"?dzT("sonvfx.voix.clone_en_cours"):dzT("sonvfx.voix.clone_confirmer")})]}):null;
var bibliotheque=r.jsxs("aside",{className:"dzsvv-biblio",children:[
r.jsx("div",{className:"dzsvv-titre",children:dzT("sonvfx.voix.biblio")}),
r.jsx("input",{className:"dzsvv-champ","data-sv-voix":"chercher",type:"search",value:q,placeholder:dzT("sonvfx.voix.chercher"),"aria-label":dzT("sonvfx.voix.chercher"),onChange:function(e){setQ(e.target.value);}}),
r.jsx("div",{className:"dzsvv-filtres",children:DZSVV_FILTRES.map(choixFiltre)}),
r.jsxs("button",{type:"button",className:"dzsvv-btn","data-sv-voix":"seul-fav","aria-pressed":seulFav?"true":"false",onClick:function(){setSeulFav(!seulFav);},children:[__dzGl("dz-action-favori",14)," ",dzT("sonvfx.voix.seul_favoris")]}),
r.jsx("div",{className:"dzsvv-liste",children:voix===null?r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.chargement")}):!liste.length?r.jsx("div",{className:"dzsvv-aide dzsvv-cle",children:dzT("sonvfx.voix.sans_voix")}):visibles.length?visibles.map(ligneVoix):r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.aucune")})}),
r.jsxs("button",{type:"button",className:"dzsvv-btn","data-sv-voix":"cloner-ouvrir","aria-expanded":clone.ouvert?"true":"false",onClick:function(){setClone(function(C){return Object.assign({},C,{ouvert:!C.ouvert,arme:!1});});},children:[__dzGl("dz-media-cloner-voix",14)," ",dzT("sonvfx.voix.cloner_ouvrir")]}),
panneauClone]});
/* une balise s'insère AU CURSEUR, suivie d'une espace */
function inserer(t){
var el=champ.current,a=el&&typeof el.selectionStart==="number"?el.selectionStart:texte.length,b=el&&typeof el.selectionEnd==="number"?el.selectionEnd:a;
setTexte((texte.slice(0,a)+t+" "+texte.slice(b)).slice(0,maxc));
}
function groupe(g){
var tags=(balises.groups||{})[g]||[],on=!!ouverts[g];
if(!tags.length)return null;
return r.jsxs("div",{className:"dzsvv-groupe","data-groupe":g,children:[
r.jsx("button",{type:"button",className:"dzsvv-gtete","aria-expanded":on?"true":"false",onClick:function(){setOuverts(function(O){var o=Object.assign({},O);o[g]=!O[g];return o;});},children:T.grp[g]||g}),
on?r.jsx("div",{className:"dzsvv-puces",children:tags.map(function(t){return r.jsx("button",{type:"button",className:"dzsvv-puce","data-balise":t,title:dzT("sonvfx.voix.balise_inserer"),onClick:function(){inserer(t);},children:t},t);})}):null]},g);
}
var palette=balises===null?r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.chargement")}):vbox?r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.vbox_balises")}):r.jsxs("div",{className:"dzsvv-palette",children:[
DZSVV_GROUPES.concat(Object.keys(balises.groups||{}).filter(function(g){return DZSVV_GROUPES.indexOf(g)<0;})).map(groupe),
v3?null:r.jsx("div",{className:"dzsvv-aide","data-sv-voix":"hors-v3",children:dzT("sonvfx.voix.balises_v3_seul")})]});
/* payant : premier clic = devis du serveur (même chiffre que la garde), second clic = synthèse ; Voicebox : un clic */
function corps(){
var o={script:texte,language:langue,name:"sonvfx_voix",model:vbox?void 0:modele||void 0};
if(sel&&voix&&voix.enabled)o.voice_id=sel;
if(!vbox&&mod){var st={};(mod.settings||[]).forEach(function(k){if(k in regl)st[k]=regl[k];});o.settings=st;}
return o;
}
function ajouterVersion(D,origine){
var v={nom:D.filename,url:D.url||"/api/audio/"+D.filename,origine:origine,dur:Number(D.dur)||0};
setVersions(function(V){return V.filter(function(t){return t.nom!==v.nom;}).concat([v]);});
setCur(v.nom);
setLect({pos:0,dur:v.dur,joue:!1});
chargerBiblio();
}
function synthese(){
setArme(null);
setOccupe("generer");
setNote("");
dzSvvPost("/api/audio/voiceover",corps()).then(function(D){
setOccupe("");
ajouterVersion(D,"generee");
setNote(dzT("sonvfx.voix.generee",{nom:D.filename})+((D.notes||[]).length?" — "+D.notes.join(" · "):""));
}).catch(function(err){setOccupe("");setNote(String(err&&err.message||err));});
}
function generer(){
if(occupe||!texte.trim())return;
if(vbox||arme){synthese();return;}
setArme({usd:null});
dzSvvDevis({kind:"elevenlabs",chars:texte.length,model:modele||void 0}).then(function(u){setArme(function(A){return A?{usd:u}:A;});});
}
var prixCout=vbox?dzT("sonvfx.voix.gratuit_vbox"):!texte.trim()?"":cout==null?dzT("sonvfx.voix.cout_attente"):dzT("sonvfx.voix.cout",{prix:dzSvvPrix(cout)});
var prixArme=arme?(arme.usd==null?dzT("sonvfx.voix.cout_attente"):dzSvvPrix(arme.usd)):"";
var script=r.jsxs("section",{className:"dzsvv-script",children:[
r.jsx("div",{className:"dzsvv-titre",children:dzT("sonvfx.voix.script")}),
r.jsx("textarea",{ref:champ,className:"dzsvv-texte","data-dz-ia":"voix",rows:7,maxLength:maxc,value:texte,placeholder:dzT("sonvfx.voix.script_exemple"),"aria-label":dzT("sonvfx.voix.script"),onChange:function(e){setTexte(e.target.value);}}),
r.jsxs("div",{className:"dzsvv-compte",children:[
r.jsx("span",{"data-sv-voix":"compteur",children:dzT("sonvfx.voix.compteur",{n:texte.length,max:maxc})}),
r.jsx("span",{className:"dzsvv-cout","data-sv-voix":"cout",children:prixCout})]}),
palette,
r.jsxs("div",{className:"dzsvv-actions",children:[
r.jsxs("button",{type:"button",className:"dzsvv-btn prim","data-sv-voix":"generer","data-arme":arme?"":void 0,disabled:!!occupe||!texte.trim(),onClick:generer,
children:[__dzGl("dz-media-generer-voix",14)," ",occupe!=="generer"&&!arme?dzT("sonvfx.voix.generer"):occupe==="generer"?dzT("sonvfx.voix.synthese"):dzT("sonvfx.voix.confirmer",{prix:prixArme})]}),
arme?r.jsx("button",{type:"button",className:"dzsvv-btn","data-sv-voix":"annuler",onClick:function(){setArme(null);},children:dzT("sonvfx.voix.annuler")}):null]})]});
function regle(k,v){setRegl(function(R0){var o=Object.assign({},R0);o[k]=v;return o;});}
function curseur(k,lo,hi,pas){
var v=regl[k];
return r.jsxs("label",{className:"dzsvv-regle","data-regle":k,children:[
r.jsx("span",{className:"dzsvv-rnom",children:T.r[k]}),
r.jsx("input",{type:"range",min:lo,max:hi,step:pas,value:v,"aria-label":T.r[k],onChange:function(e){regle(k,Number(e.target.value));}}),
r.jsx("span",{className:"dzsvv-rval",children:String(Math.round(v*100)/100)})]},k);
}
var reglables=(mod&&mod.settings)||[];
var reglages=r.jsxs("aside",{className:"dzsvv-reglages",children:[
r.jsx("div",{className:"dzsvv-titre",children:dzT("sonvfx.voix.reglages")}),
r.jsxs("label",{className:"dzsvv-regle dzsvv-col",children:[
r.jsx("span",{className:"dzsvv-rnom",children:dzT("sonvfx.voix.modele")}),
r.jsx("select",{className:"dzsvv-sel","data-sv-voix":"modele",value:modele,disabled:vbox,"aria-label":dzT("sonvfx.voix.modele"),onChange:function(e){setModele(e.target.value);},children:mlist.map(function(m){return r.jsx("option",{value:m.id,children:m.label},m.id);})})]}),
vbox?r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.vbox_modele")}):mod&&!mod.available?r.jsx("div",{className:"dzsvv-aide dzsvv-cle",children:dzT("sonvfx.voix.sans_cle")}):null,
!vbox&&reglables.indexOf("stability")>=0?v3?r.jsxs("label",{className:"dzsvv-regle dzsvv-col","data-regle":"stability",children:[
r.jsx("span",{className:"dzsvv-rnom",children:dzT("sonvfx.voix.r_stability")}),
r.jsx("div",{className:"dzsvv-segs",role:"group","aria-label":dzT("sonvfx.voix.r_stability"),children:DZSVV_STAB.map(function(s){return r.jsx("button",{type:"button",className:"dzsvv-seg","aria-pressed":regl.stability===s?"true":"false","data-stab":String(s),onClick:function(){regle("stability",s);},children:T.stab[String(s)]},s);})})]}):curseur("stability",0,1,0.05):null,
!vbox&&reglables.indexOf("similarity_boost")>=0?curseur("similarity_boost",0,1,0.05):null,
!vbox&&reglables.indexOf("speed")>=0?curseur("speed",0.7,1.2,0.05):null,
!vbox&&v3?r.jsx("div",{className:"dzsvv-aide","data-sv-voix":"v3-stab",children:dzT("sonvfx.voix.v3_reglages")}):null,
r.jsxs("label",{className:"dzsvv-regle dzsvv-col",children:[
r.jsx("span",{className:"dzsvv-rnom",children:dzT("sonvfx.voix.langue")}),
r.jsxs("select",{className:"dzsvv-sel","data-sv-voix":"langue",value:langue,"aria-label":dzT("sonvfx.voix.langue"),onChange:function(e){setLangue(e.target.value);},children:[
r.jsx("option",{value:"fr",children:dzT("sonvfx.voix.langue_fr")}),
r.jsx("option",{value:"en",children:dzT("sonvfx.voix.langue_en")})]})]})]});
/* le résultat : la version écoutée, sa forme d'onde, les versions, les retouches (chaque retouche = une version neuve) */
var vcur=versions.find(function(t){return t.nom===cur;})||null;
var dur=lect.dur||(vcur&&vcur.dur)||0;
function majOut(k,v){setOut(function(O){var o=Object.assign({},O);o[k]=v;return o;});}
function retouche(op){
if(!vcur||occupe)return;
var f=vcur.nom,pr=null;
if(op==="coupe")pr=dzSvvPost("/api/audio/graph/rendre",{graphe:dzSvvGraphe(f,{type:"plage",params:{debut:out.debut,fin:out.fin}}),nom:"voix_coupe"});
else if(op==="fondu")pr=dzSvvPost("/api/audio/graph/rendre",{graphe:dzSvvGraphe(f,{type:"plage",params:{debut:0,fin:dur,fondu_entree:out.fondu_entree,fondu_sortie:out.fondu_sortie}}),nom:"voix_fondu"});
else if(op==="normalise")pr=dzSvvPost("/api/audio/graph/rendre",{graphe:dzSvvGraphe(f,{type:"effet",params:{fx:"normalize",target_lufs:out.lufs}}),nom:"voix_normalisee"});
else if(op==="deess")pr=dzSvvPost("/api/audio/graph/rendre",{graphe:dzSvvGraphe(f,{type:"effet",params:{fx:"deesser",intensity:out.deess}}),nom:"voix_deess"});
else if(op==="ducking")pr=out.musique?dzSvvPost("/api/audio/duck",{voice:f,music:out.musique,music_db:out.music_db}):null;
else if(op==="ameliore")pr=dzSvvPost("/api/audio/enhance",{filename:f});
else if(op==="isole")pr=dzSvvPost("/api/audio/isolate",{filename:f});
if(!pr){setNote(dzT("sonvfx.voix.musique_choisir"));return;}
setOccupe("outil:"+op);
setNote("");
setArmeIso(null);
pr.then(function(D){setOccupe("");ajouterVersion(D,op);setNote(dzT("sonvfx.voix.retouche_faite",{nom:D.filename}));}).catch(function(err){setOccupe("");setNote(String(err&&err.message||err));});
}
function isoler(){
if(!vcur||occupe)return;
if(armeIso){retouche("isole");return;}
setArmeIso({usd:null});
dzSvvDevis({kind:"isolate",duration_s:dur}).then(function(u){setArmeIso(function(A){return A?{usd:u}:A;});});
}
function nombre(k,lo,hi,pas,lbl){
return r.jsxs("label",{className:"dzsvv-num",children:[
r.jsx("span",{children:lbl}),
r.jsx("input",{type:"number",min:lo,max:hi,step:pas,value:out[k],"data-out":k,"aria-label":lbl,onChange:function(e){var v=Number(e.target.value);if(isFinite(v))majOut(k,Math.max(lo,Math.min(hi,v)));}})]},k);
}
function outil(op,lbl,ico,champs,action){
var busy=occupe==="outil:"+op;
return r.jsxs("div",{className:"dzsvv-outil","data-outil":op,children:[
r.jsxs("span",{className:"dzsvv-onom",children:[__dzGl(ico,14)," ",lbl]}),
champs,
r.jsx("button",{type:"button",className:"dzsvv-btn","data-sv-voix":"outil-"+op,"data-arme":op==="isole"&&armeIso?"":void 0,disabled:!!occupe&&!busy,onClick:action||function(){retouche(op);},
children:!busy&&!(op==="isole"&&armeIso)?dzT("sonvfx.voix.appliquer"):busy?dzT("sonvfx.voix.en_cours"):dzT("sonvfx.voix.confirmer",{prix:armeIso.usd==null?dzT("sonvfx.voix.cout_attente"):dzSvvPrix(armeIso.usd)})})]},op);
}
var musiques=biblio.liste.filter(function(it){return (biblio.meta[it.name]||{}).kind==="musique";});
var barres=(vcur&&pics[vcur.nom])||DZSVV_PLAT;
function chercher(e){
var el=e.currentTarget,rc=el.getBoundingClientRect?el.getBoundingClientRect():{left:0,width:0},f=rc.width?Math.min(1,Math.max(0,(e.clientX-rc.left)/rc.width)):0;
if(lecteur.current&&dur){try{lecteur.current.currentTime=f*dur;}catch(er){}}
setLect(function(L){return Object.assign({},L,{pos:f*dur});});
}
function lire(){
var el=lecteur.current;
if(!el)return;
if(lect.joue){el.pause();setLect(function(L){return Object.assign({},L,{joue:!1});});return;}
var pr=el.play();
setLect(function(L){return Object.assign({},L,{joue:!0});});
if(pr&&pr.catch)pr.catch(function(){setLect(function(L){return Object.assign({},L,{joue:!1});});setNote(dzT("sonvfx.voix.lecture_bloquee"));});
}
var resultat=r.jsxs("section",{className:"dzsvv-resultat",children:[
r.jsx("div",{className:"dzsvv-titre",children:dzT("sonvfx.voix.resultat")}),
vcur?r.jsxs(r.Fragment,{children:[
r.jsxs("div",{className:"dzsvv-rtete",children:[
r.jsx("button",{type:"button",className:"dzsvv-mini","data-sv-voix":"lire","aria-label":!lect.joue?dzT("sonvfx.voix.lire"):dzT("sonvfx.voix.pause"),title:!lect.joue?dzT("sonvfx.voix.lire"):dzT("sonvfx.voix.pause"),onClick:lire,children:__dzGl(lect.joue?"dz-media-pause":"dz-media-lecture",15)}),
r.jsx("span",{className:"dzsvv-curn",children:vcur.nom}),
r.jsx("span",{className:"dzsvv-pastille",children:T.o[vcur.origine]||vcur.origine}),
r.jsx("span",{className:"dzsvv-temps",children:dzSvpDuree(lect.pos)+" / "+dzSvpDuree(dur)}),
r.jsx("button",{type:"button",className:"dzsvv-btn","data-sv-voix":"atelier",onClick:function(){if(lecteur.current)lecteur.current.pause();dzSvpVersAtelier(vcur.nom);},children:dzT("sonvfx.voix.vers_atelier")}),
r.jsx("button",{type:"button",className:"dzsvv-btn prim","data-sv-voix":"montage",onClick:function(){if(lecteur.current)lecteur.current.pause();if(p.go)p.go("montage");},children:dzT("sonvfx.voix.vers_montage")})]}),
r.jsx("audio",{ref:lecteur,src:vcur.url,preload:"metadata",onLoadedMetadata:function(e){var d=e.target.duration||0;setLect(function(L){return Object.assign({},L,{dur:d});});setOut(function(O){return O.fin?O:Object.assign({},O,{fin:Math.round(d*10)/10});});},onTimeUpdate:function(e){var t0=e.target.currentTime||0;setLect(function(L){return Object.assign({},L,{pos:t0});});},onEnded:function(){setLect(function(L){return Object.assign({},L,{joue:!1,pos:0});});}}),
r.jsxs("div",{className:"dzsvv-onde","data-sv-voix":"onde",title:dzT("sonvfx.voix.onde_aide"),onClick:chercher,children:[
barres.map(function(h,i){return r.jsx("span",{className:"dzsvv-barre",style:{height:h+"%"}},i);}),
r.jsx("span",{className:"dzsvv-tete",style:{left:(dur?Math.min(100,lect.pos/dur*100):0)+"%"}})]}),
r.jsx("div",{className:"dzsvv-versions",role:"group","aria-label":dzT("sonvfx.voix.versions"),children:versions.map(function(t,i){return r.jsx("button",{type:"button",className:"dzsvv-version","aria-pressed":t.nom===cur?"true":"false","data-version":t.nom,title:t.nom,onClick:function(){if(lecteur.current)lecteur.current.pause();setCur(t.nom);setLect({pos:0,dur:t.dur||0,joue:!1});},children:dzT("sonvfx.voix.version_n",{n:i+1})+" · "+(T.o[t.origine]||t.origine)},t.nom);})}),
r.jsxs("div",{className:"dzsvv-outils",children:[
outil("coupe",dzT("sonvfx.voix.couper"),"dz-edit-couper",[nombre("debut",0,3600,0.1,dzT("sonvfx.voix.debut")),nombre("fin",0,3600,0.1,dzT("sonvfx.voix.fin"))]),
outil("fondu",dzT("sonvfx.voix.fondu"),"dz-media-forme-onde",[nombre("fondu_entree",0,30,0.1,dzT("sonvfx.voix.fondu_entree")),nombre("fondu_sortie",0,30,0.1,dzT("sonvfx.voix.fondu_sortie"))]),
outil("normalise",dzT("sonvfx.voix.normaliser"),"dz-media-forme-onde",[nombre("lufs",-30,-10,1,dzT("sonvfx.voix.lufs"))]),
outil("deess",dzT("sonvfx.voix.deess"),"dz-media-voix",[nombre("deess",0,100,5,dzT("sonvfx.voix.intensite"))]),
outil("ducking",dzT("sonvfx.voix.ducking"),"dz-cat-audio",[
r.jsxs("select",{className:"dzsvv-sel","data-out":"musique",value:out.musique,"aria-label":dzT("sonvfx.voix.musique"),onChange:function(e){majOut("musique",e.target.value);},children:[
r.jsx("option",{value:"",children:dzT("sonvfx.voix.musique")}),
musiques.map(function(it){return r.jsx("option",{value:it.name,children:it.name},it.name);})]},"m"),
nombre("music_db",-30,0,1,dzT("sonvfx.voix.niveau_musique"))]),
outil("ameliore",dzT("sonvfx.voix.ameliorer"),"dz-media-ameliorer",[r.jsx("span",{className:"dzsvv-aide",children:dzT("sonvfx.voix.ameliorer_aide")},"a")]),
outil("isole",dzT("sonvfx.voix.isoler"),"dz-media-isoler-voix",[r.jsx("span",{className:"dzsvv-aide",children:dzT("sonvfx.voix.isoler_aide")},"a")],isoler)]})]}):r.jsx("div",{className:"dzsvv-aide",children:dzT("sonvfx.voix.resultat_vide")})]});
return r.jsxs("div",{className:"dzsvv",children:[
bibliotheque,
r.jsxs("div",{className:"dzsvv-centre",children:[script,resultat,note?r.jsx("div",{className:"dzsvv-note",role:"status",children:note}):null]}),
reglages]});
}
