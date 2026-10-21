/* sonvfx-pistes.js — t269 (21/10/2026) : page « Importer et séparer » de Son & VFX › Musique.
   SOURCE du maillon de queue dzsonvfx (scripts/patch_bundle_dzsonvfx.py), qui la pose APLATIE dans le bundle : les
   lignes sont rognées puis jointes par une espace. Règles d'écriture : une instruction par ligne terminée par « ; »
   (ou une ligne qui ouvre/continue un bloc ou une liste), aucune ligne qui commence par « ( » ou « [ », aucun
   commentaire « // », commentaires « /* » seulement sur des lignes à part (retirés à la pose).
   Symboles du bundle : r (jsx), x (React), dzT, __dzGl. Routes : GET /api/audio, GET /api/audio/meta,
   POST /api/audio/upload, GET /api/audio/stems-models, POST /api/cost/estimate {kind:"stems"}, POST /api/audio/stems. */
var DZSVP_ORDRE=["vocals","drums","bass","other","guitar","piano"];
function dzSvpLib(){
return {vocals:dzT("sonvfx.pistes.stem_voix"),drums:dzT("sonvfx.pistes.stem_batterie"),bass:dzT("sonvfx.pistes.stem_basse"),
other:dzT("sonvfx.pistes.stem_autres"),guitar:dzT("sonvfx.pistes.stem_guitare"),piano:dzT("sonvfx.pistes.stem_piano")};
}
function dzSvpGenre(k){
var G={musique:dzT("sonvfx.pistes.genre_musique"),"import":dzT("sonvfx.pistes.genre_import"),voix:dzT("sonvfx.pistes.genre_voix"),
sfx:dzT("sonvfx.pistes.genre_sfx"),mix:dzT("sonvfx.pistes.genre_mix")};
return G[k]||"";
}
function dzSvpDuree(s){
s=Math.max(0,Math.round(Number(s)||0));
var m=Math.floor(s/60),r2=s-m*60;
return m+":"+(r2<10?"0":"")+r2;
}
function dzSvpJson(res){
return res.json().catch(function(){return {};}).then(function(d){
if(!res.ok){var m=d&&d.detail;throw new Error((m&&m.message)||(typeof m==="string"&&m)||dzT("sonvfx.pistes.echec_code",{code:res.status}));}
return d;
});
}
/* t271 : ouvre une piste dans l'Atelier sonore (mode « Atelier » de Musique), qui la pose comme source */
function dzSvpVersAtelier(fichier){
try{window.__dzSvAtelierAjout={fichier:fichier};}catch(e){}
window.dispatchEvent(new CustomEvent("deepotus:sonvfx-subtab",{detail:{id:"music",mode:"atelier"}}));
window.dispatchEvent(new CustomEvent("deepotus:sva-ajout"));
}
function DzSvPistes(p){
var US=x.useState,UE=x.useEffect,UR=x.useRef;
var s1=US(null),liste=s1[0],setListe=s1[1];
var s2=US({}),meta=s2[0],setMeta=s2[1];
var s3=US(""),q=s3[0],setQ=s3[1];
var s4=US(""),sel=s4[0],setSel=s4[1];
var s5=US(0),dur=s5[0],setDur=s5[1];
var s6=US(!1),upl=s6[0],setUpl=s6[1];
var s7=US(!1),survol=s7[0],setSurvol=s7[1];
var s8=US(null),mods=s8[0],setMods=s8[1];
var s9=US(""),modele=s9[0],setModele=s9[1];
var s10=US(null),arme=s10[0],setArme=s10[1];
var s11=US(!1),occupe=s11[0],setOccupe=s11[1];
var s12=US(""),note=s12[0],setNote=s12[1];
var s13=US({}),mix=s13[0],setMix=s13[1];
var s14=US(!1),joue=s14[0],setJoue=s14[1];
var fichier=UR(null),lecteurs=UR({});
/* la liste et le sidecar ; `choisir` = la piste à ouvrir (import), sinon la dernière musique générée */
function charger(choisir){
return Promise.all([fetch("/api/audio").then(dzSvpJson),fetch("/api/audio/meta").then(dzSvpJson)]).then(function(R){
var L=R[0].audio||[],M=R[1].meta||{};
setListe(L);
setMeta(M);
setSel(function(cur){
if(choisir)return choisir;
if(cur&&L.some(function(it){return it.name===cur;}))return cur;
var src=L.filter(function(it){return (M[it.name]||{}).kind!=="stem";});
var mus=src.find(function(it){return (M[it.name]||{}).kind==="musique";});
return (mus||src[0]||{}).name||"";
});
}).catch(function(err){setListe([]);setNote(String(err&&err.message||err));});
}
UE(function(){
charger();
fetch("/api/audio/stems-models").then(dzSvpJson).then(function(D){setMods(D);setModele(D["default"]||"");}).catch(function(){setMods({enabled:!1,models:[]});});
},[]);
var stems=(liste||[]).filter(function(it){var mm=meta[it.name]||{};return mm.kind==="stem"&&mm.parent===sel;}).map(function(it){
return {name:it.name,url:it.url,stem:(meta[it.name]||{}).stem||""};
});
stems.sort(function(A,B){return DZSVP_ORDRE.indexOf(A.stem)-DZSVP_ORDRE.indexOf(B.stem);});
var solo=stems.some(function(t){return !!(mix[t.name]||{}).s;});
function els(){return stems.map(function(t){return lecteurs.current[t.name];}).filter(Boolean);}
function lire(){
var E=els();
if(!E.length)return;
var t0=E[0].currentTime||0;
E.forEach(function(el){try{el.currentTime=t0;}catch(er){}var pr=el.play();if(pr&&pr.catch)pr.catch(function(){});});
setJoue(!0);
}
function pause(){els().forEach(function(el){el.pause();});setJoue(!1);}
function arreter(){els().forEach(function(el){el.pause();try{el.currentTime=0;}catch(er){}});setJoue(!1);}
/* muet / solo / volume appliqués aux lecteurs après chaque rendu */
UE(function(){
stems.forEach(function(t){
var el=lecteurs.current[t.name];
if(!el)return;
var c0=mix[t.name]||{};
el.volume=c0.v==null?1:c0.v;
el.muted=!!c0.m||(solo&&!c0.s);
});
});
UE(function(){setArme(null);setDur(0);arreter();},[sel]);
function regle(nom,cle,val){
setMix(function(M0){var o0=Object.assign({},M0[nom]||{});o0[cle]=val;var M1=Object.assign({},M0);M1[nom]=o0;return M1;});
}
function importer(fl){
if(!fl||upl)return;
var fd=new FormData();
fd.append("file",fl);
setUpl(!0);
setNote("");
fetch("/api/audio/upload",{method:"POST",body:fd}).then(dzSvpJson).then(function(D){
setUpl(!1);
setNote(dzT("sonvfx.pistes.importee",{nom:D.filename}));
return charger(D.filename);
}).catch(function(err){setUpl(!1);setNote(dzT("sonvfx.pistes.import_echec",{e:String(err&&err.message||err)}));});
}
/* payant : le premier clic arme avec le devis du serveur (même chiffre que la garde), le second envoie */
function devis(){
if(!dur)return Promise.resolve(null);
return fetch("/api/cost/estimate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind:"stems",duration_s:dur||0})}).then(function(res){return res.ok?res.json():null;}).then(function(D){return D&&typeof D.total_usd==="number"?D.total_usd:null;}).catch(function(){return null;});
}
function separer(){
if(!sel||occupe)return;
if(!arme){
setArme({usd:null});
devis().then(function(u){setArme(function(A){return A?{usd:u}:A;});});
return;
}
setArme(null);
setOccupe(!0);
setNote("");
fetch("/api/audio/stems",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filename:sel,model:modele||void 0})}).then(dzSvpJson).then(function(D){
var lib=dzSvpLib(),manq=D.missing||[];
setOccupe(!1);
setNote(dzT("sonvfx.pistes.separee",{n:(D.items||[]).length,usd:Number(D.usd||0).toFixed(3)})+(manq.length?" "+dzT("sonvfx.pistes.manquants",{liste:manq.map(function(s){return lib[s]||s;}).join(", ")}):""));
return charger(sel);
}).catch(function(err){setOccupe(!1);setNote(String(err&&err.message||err));});
}
var lib=dzSvpLib();
var qq=q.trim().toLowerCase();
var sources=(liste||[]).filter(function(it){return (meta[it.name]||{}).kind!=="stem"&&(!qq||it.name.toLowerCase().indexOf(qq)>=0);}).slice(0,300);
var cur=(liste||[]).find(function(it){return it.name===sel;})||null;
var mlist=(mods&&mods.models)||[];
function ligne(it){
var g=dzSvpGenre((meta[it.name]||{}).kind);
return r.jsxs("button",{type:"button",className:"dzsvp-ligne","data-sel":it.name===sel?"":void 0,"aria-pressed":it.name===sel?"true":"false",onClick:function(){setSel(it.name);},children:[
r.jsx("span",{className:"dzsvp-nomf",children:it.name}),
g?r.jsx("span",{className:"dzsvp-genre",children:g}):null]},it.name);
}
var source=r.jsxs("aside",{className:"dzsvp-src",children:[
r.jsx("div",{className:"dzsvp-titre",children:dzT("sonvfx.pistes.source")}),
r.jsxs("div",{className:"dzsvp-depot","data-survol":survol?"":void 0,
onDragOver:function(e){e.preventDefault();if(!survol)setSurvol(!0);},
onDragLeave:function(){setSurvol(!1);},
onDrop:function(e){e.preventDefault();setSurvol(!1);var F=e.dataTransfer&&e.dataTransfer.files;importer(F&&F[0]);},
children:[
r.jsx("span",{className:"dzsvp-depico","aria-hidden":"true",children:__dzGl("dz-action-importer",22)}),
r.jsx("div",{className:"dzsvp-depmsg",children:upl?dzT("sonvfx.pistes.import_en_cours"):dzT("sonvfx.pistes.deposer")}),
r.jsx("button",{type:"button",className:"dzsvp-btn prim","data-sv-pistes":"importer",disabled:upl,onClick:function(){if(fichier.current)fichier.current.click();},children:dzT("sonvfx.pistes.importer")}),
r.jsx("div",{className:"dzsvp-fmt",children:dzT("sonvfx.pistes.formats")}),
r.jsx("input",{ref:fichier,type:"file",hidden:!0,accept:".mp3,.wav,.flac,.ogg,.m4a,.aac,.opus,audio/*",onChange:function(e){var F=e.target.files;importer(F&&F[0]);e.target.value="";}})]}),
r.jsx("input",{className:"dzsvp-q",type:"search",value:q,placeholder:dzT("sonvfx.pistes.chercher"),"aria-label":dzT("sonvfx.pistes.chercher"),onChange:function(e){setQ(e.target.value);}}),
r.jsx("div",{className:"dzsvp-liste",children:liste===null?r.jsx("div",{className:"dzsvp-aide",children:dzT("sonvfx.pistes.chargement")}):sources.length?sources.map(ligne):r.jsx("div",{className:"dzsvp-aide",children:dzT("sonvfx.pistes.vide")})})]});
function choixModele(mm){
var n=(mm.stems||[]).length;
return r.jsxs("button",{type:"button",className:"dzsvp-modele","aria-pressed":mm.id===modele?"true":"false",onClick:function(){setModele(mm.id);setArme(null);},children:[
r.jsx("span",{className:"dzsvp-modn",children:n>4?dzT("sonvfx.pistes.modele_6"):dzT("sonvfx.pistes.modele_4")}),
r.jsx("span",{className:"dzsvp-mods",children:(mm.stems||[]).map(function(s){return lib[s]||s;}).join(" · ")})]},mm.id);
}
var prix=arme?(arme.usd==null?dzT("sonvfx.pistes.prix_attente"):"~$"+arme.usd.toFixed(arme.usd<0.1?3:2)):"";
var carteSep=r.jsxs("div",{className:"dzsvp-carte",children:[
r.jsx("div",{className:"dzsvp-titre",children:dzT("sonvfx.pistes.separer_titre")}),
r.jsx("div",{className:"dzsvp-aide",children:dzT("sonvfx.pistes.separer_desc")}),
r.jsx("div",{className:"dzsvp-modeles",role:"group","aria-label":dzT("sonvfx.pistes.separer_titre"),children:mlist.map(choixModele)}),
mods&&!mods.enabled?r.jsx("div",{className:"dzsvp-aide dzsvp-cle",children:dzT("sonvfx.pistes.sans_cle")}):null,
r.jsxs("div",{className:"dzsvp-actions",children:[
r.jsx("button",{type:"button",className:"dzsvp-btn prim","data-sv-pistes":"separer","data-arme":arme?"":void 0,disabled:occupe||!cur,onClick:separer,
children:occupe?dzT("sonvfx.pistes.separation_en_cours"):arme?dzT("sonvfx.pistes.confirmer",{prix:prix}):dzT("sonvfx.pistes.separer")}),
arme?r.jsx("button",{type:"button",className:"dzsvp-btn",onClick:function(){setArme(null);},children:dzT("sonvfx.pistes.annuler")}):null]})]});
function ligneStem(t){
var c0=mix[t.name]||{},nom=lib[t.stem]||t.stem||t.name;
return r.jsxs("div",{className:"dzsvp-stem","data-stem":t.stem,children:[
r.jsx("span",{className:"dzsvp-stemn",children:nom}),
r.jsx("audio",{ref:function(el){if(el)lecteurs.current[t.name]=el;else delete lecteurs.current[t.name];},src:t.url,preload:"auto",onEnded:function(){setJoue(!1);}}),
r.jsx("button",{type:"button",className:"dzsvp-mini","aria-pressed":c0.m?"true":"false",title:dzT("sonvfx.pistes.muet"),"aria-label":dzT("sonvfx.pistes.muet")+" : "+nom,onClick:function(){regle(t.name,"m",!c0.m);},children:__dzGl("dz-media-muet",15)}),
r.jsx("button",{type:"button",className:"dzsvp-mini","aria-pressed":c0.s?"true":"false",title:dzT("sonvfx.pistes.solo"),"aria-label":dzT("sonvfx.pistes.solo")+" : "+nom,onClick:function(){regle(t.name,"s",!c0.s);},children:__dzGl("dz-media-solo",15)}),
r.jsx("input",{className:"dzsvp-vol",type:"range",min:0,max:1,step:0.05,value:c0.v==null?1:c0.v,"aria-label":dzT("sonvfx.pistes.volume",{nom:nom}),onChange:function(e){regle(t.name,"v",Number(e.target.value));}}),
r.jsx("button",{type:"button",className:"dzsvp-mini","data-sv-pistes":"atelier-stem",title:dzT("sonvfx.pistes.vers_atelier_nom",{nom:nom}),"aria-label":dzT("sonvfx.pistes.vers_atelier_nom",{nom:nom}),onClick:function(){arreter();dzSvpVersAtelier(t.name);},children:__dzGl("dz-action-envoyer-vers",15)}),
r.jsx("a",{className:"dzsvp-mini",href:t.url,download:t.name,title:dzT("sonvfx.pistes.telecharger",{nom:nom}),"aria-label":dzT("sonvfx.pistes.telecharger",{nom:nom}),children:__dzGl("dz-action-telecharger",15)})]},t.name);
}
var carteStems=stems.length?r.jsxs("div",{className:"dzsvp-carte",children:[
r.jsx("div",{className:"dzsvp-titre",children:dzT("sonvfx.pistes.pistes_titre",{n:stems.length})}),
r.jsxs("div",{className:"dzsvp-actions",children:[
r.jsxs("button",{type:"button",className:"dzsvp-btn","data-sv-pistes":"lire",onClick:joue?pause:lire,children:[__dzGl(joue?"dz-media-pause":"dz-media-lecture",14)," ",joue?dzT("sonvfx.pistes.pause"):dzT("sonvfx.pistes.lire")]}),
r.jsxs("button",{type:"button",className:"dzsvp-btn",onClick:arreter,children:[__dzGl("dz-media-arret",14)," ",dzT("sonvfx.pistes.arreter")]})]}),
r.jsx("div",{className:"dzsvp-stems",children:stems.map(ligneStem)}),
r.jsxs("div",{className:"dzsvp-actions",children:[
r.jsx("button",{type:"button",className:"dzsvp-btn","data-sv-pistes":"montage",onClick:function(){arreter();if(p.go)p.go("montage");},children:dzT("sonvfx.pistes.vers_montage")}),
r.jsx("span",{className:"dzsvp-aide",children:dzT("sonvfx.pistes.montage_aide")})]})]}):null;
var principal=cur?r.jsxs(r.Fragment,{children:[
r.jsxs("div",{className:"dzsvp-carte",children:[
r.jsxs("div",{className:"dzsvp-tete",children:[
r.jsx("span",{className:"dzsvp-curn",children:cur.name}),
dur?r.jsx("span",{className:"dzsvp-genre",children:dzT("sonvfx.pistes.duree",{d:dzSvpDuree(dur)})}):null,
r.jsx("button",{type:"button",className:"dzsvp-btn","data-sv-pistes":"atelier",onClick:function(){arreter();dzSvpVersAtelier(cur.name);},children:dzT("sonvfx.pistes.vers_atelier")})]}),
r.jsx("audio",{className:"dzsvp-lecteur",controls:!0,src:cur.url,preload:"metadata",onLoadedMetadata:function(e){setDur(e.target.duration||0);}})]}),
carteSep,carteStems]}):r.jsx("div",{className:"dzsvp-vide",children:dzT("sonvfx.pistes.choisir")});
return r.jsxs("div",{className:"dzsvp",children:[
source,
r.jsxs("section",{className:"dzsvp-main",children:[
principal,
note?r.jsx("div",{className:"dzsvp-note",role:"status",children:note}):null]})]});
}
