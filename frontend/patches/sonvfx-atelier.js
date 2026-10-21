/* sonvfx-atelier.js — t271 (21/10/2026) : l'Atelier sonore de Son & VFX › Musique (troisième mode de la page).
   Canevas de nœuds au-dessus du moteur serveur t270 (/api/audio/graph : noeuds, valider, apercu, rendre) : palette
   par catégorie, nœuds déplaçables, liens tirés d'une sortie vers une entrée, zoom et déplacement de la vue,
   inspecteur borné par le catalogue du serveur, préréglages de chaîne, annuler / rétablir, graphe gardé dans ce
   navigateur ; frise de plages sous le canevas (forme d'onde, région ↔ nœud Plage, position de l'aperçu) ;
   aperçu de 10 s et bascule A/B (source brute / traitée), rendu dans la Bibliothèque, Montage.
   SOURCE du maillon de queue dzsonvfx, posée APLATIE (mêmes règles d'écriture que sonvfx-pistes.js : une
   instruction par ligne terminée par « ; », aucune ligne qui commence par « ( » ou « [ », aucun « // »,
   commentaires sur des lignes entières seulement). Symboles du bundle : r, x, dzT, __dzGl ; de la page Pistes :
   dzSvpJson, dzSvpDuree ; du rack SFX (couche SFXSTUDIO) : SVX_FX_DEFS (libellés, pas, unités des effets).
   Aucun arrondi (angles vifs, règle du hub).
   t272 (21/10/2026) : catégorie « IA » (prolonger, régénérer une plage, variation, SFX sur la plage) ; l'inspecteur
   choisit le modèle (prix, clé absente dite mais choisissable) et la description ; le devis du serveur
   (/api/audio/graph/devis, même op que la garde) est affiché AVANT ; Écouter et Rendre qui feraient générer s'arment
   au premier clic et envoient `generer: true` au second ; la frise trace aussi la plage d'un nœud IA. */
var DZSVA_LARG=176,DZSVA_TETE=26,DZSVA_PORT=22,DZSVA_CLE="dz_sva_graphe";
var DZSVA_CACHE={pics:{}};
/* catégories de la palette : couleur, entrées */
function dzSvaCats(){
return [
{id:"source",lbl:dzT("sonvfx.atelier.cat_sources"),c:"oklch(.72 .13 145)",items:[{t:"source"}]},
{id:"effets",lbl:dzT("sonvfx.atelier.cat_effets"),c:"oklch(.72 .13 200)",items:["filter","eq3","eq6","dehum","denoise","deesser","compressor","distortion","echo","reverb","stereo","normalize"].map(function(f){return {t:"effet",fx:f};})},
{id:"dynamique",lbl:dzT("sonvfx.atelier.cat_dynamique"),c:"oklch(.76 .12 80)",items:[{t:"gain"},{t:"limiteur"},{t:"duck"}]},
{id:"modulation",lbl:dzT("sonvfx.atelier.cat_modulation"),c:"oklch(.72 .13 300)",items:[{t:"chorus"},{t:"flanger"},{t:"tempo"},{t:"hauteur"}]},
{id:"temps",lbl:dzT("sonvfx.atelier.cat_temps"),c:"oklch(.72 .13 25)",items:[{t:"plage"},{t:"decalage"}]},
{id:"routage",lbl:dzT("sonvfx.atelier.cat_routage"),c:"oklch(.72 .13 340)",items:[{t:"mix"},{t:"pan"}]},
{id:"ia",lbl:dzT("sonvfx.atelier.cat_ia"),c:"oklch(.78 .14 60)",items:[{t:"ia_prolonger"},{t:"ia_regenerer"},{t:"ia_variation"},{t:"ia_sfx"}]},
{id:"sortie",lbl:dzT("sonvfx.atelier.cat_sortie"),c:"oklch(.80 .03 250)",items:[{t:"sortie"}]}];
}
function dzSvaCatDe(n){
var C=dzSvaCats();
for(var i=0;i<C.length;i++){if(C[i].items.some(function(it){return it.t===n.type;}))return C[i];}
return C[0];
}
function dzSvaNomType(t){
var N={source:dzT("sonvfx.atelier.t_source"),effet:dzT("sonvfx.atelier.t_effet"),gain:dzT("sonvfx.atelier.t_gain"),
pan:dzT("sonvfx.atelier.t_pan"),tempo:dzT("sonvfx.atelier.t_tempo"),hauteur:dzT("sonvfx.atelier.t_hauteur"),
plage:dzT("sonvfx.atelier.t_plage"),decalage:dzT("sonvfx.atelier.t_decalage"),mix:dzT("sonvfx.atelier.t_mix"),
duck:dzT("sonvfx.atelier.t_duck"),sortie:dzT("sonvfx.atelier.t_sortie"),limiteur:dzT("sonvfx.atelier.t_limiteur"),
chorus:dzT("sonvfx.atelier.t_chorus"),flanger:dzT("sonvfx.atelier.t_flanger"),
ia_prolonger:dzT("sonvfx.atelier.t_ia_prolonger"),ia_regenerer:dzT("sonvfx.atelier.t_ia_regenerer"),
ia_variation:dzT("sonvfx.atelier.t_ia_variation"),ia_sfx:dzT("sonvfx.atelier.t_ia_sfx")};
return N[t]||t;
}
/* t272 : nœuds IA */
function dzSvaEstIa(t){return String(t||"").indexOf("ia_")===0;}
function dzSvaAPlage(n){return !!n&&(n.type==="plage"||(dzSvaEstIa(n.type)&&n.type!=="ia_prolonger"));}
function dzSvaIaOp(cat,t){return (cat&&cat.ia&&cat.ia[String(t).slice(3)])||{defaut:"",modeles:[]};}
function dzSvaIaModele(cat,n){var o=dzSvaIaOp(cat,n.type);return o.modeles.find(function(m){return m.id===n.params.modele;})||null;}
function dzSvaPrix(usd){var u=Number(usd)||0;return "~$"+u.toFixed(u<0.1?4:2);}
function dzSvaPrixModele(m){if(!m.usd)return dzT("sonvfx.atelier.prix_a_mesurer");return dzSvaPrix(m.usd)+(m.unite==="s"?"/s":"");}
/* libellé et unité des paramètres propres à l'Atelier (les effets prennent ceux du rack SFX) */
function dzSvaParamLib(k){
var P={db:[dzT("sonvfx.atelier.p_gain"),"dB"],pan:[dzT("sonvfx.atelier.p_pan"),""],facteur:[dzT("sonvfx.atelier.p_facteur"),"×"],
demi_tons:[dzT("sonvfx.atelier.p_demi_tons"),""],debut:[dzT("sonvfx.atelier.p_debut"),"s"],fin:[dzT("sonvfx.atelier.p_fin"),"s"],
boucles:[dzT("sonvfx.atelier.p_boucles"),"×"],fondu_entree:[dzT("sonvfx.atelier.p_fondu_entree"),"s"],
fondu_sortie:[dzT("sonvfx.atelier.p_fondu_sortie"),"s"],secondes:[dzT("sonvfx.atelier.p_secondes"),"s"],
entrees:[dzT("sonvfx.atelier.p_entrees"),""],ratio:[dzT("sonvfx.atelier.p_ratio"),":1"],attack_ms:[dzT("sonvfx.atelier.p_attaque"),"ms"],
release_ms:[dzT("sonvfx.atelier.p_relache"),"ms"],threshold:[dzT("sonvfx.atelier.p_seuil"),""],
plafond_db:[dzT("sonvfx.atelier.p_plafond"),"dB"],attaque_ms:[dzT("sonvfx.atelier.p_attaque"),"ms"],
relache_ms:[dzT("sonvfx.atelier.p_relache"),"ms"],retard_ms:[dzT("sonvfx.atelier.p_retard"),"ms"],
vitesse_hz:[dzT("sonvfx.atelier.p_vitesse"),"Hz"],profondeur_ms:[dzT("sonvfx.atelier.p_profondeur"),"ms"],
melange:[dzT("sonvfx.atelier.p_melange"),"%"],retour:[dzT("sonvfx.atelier.p_retour"),"%"],
force:[dzT("sonvfx.atelier.p_force"),""],niveau_db:[dzT("sonvfx.atelier.p_niveau"),"dB"],prise:[dzT("sonvfx.atelier.p_prise"),""]};
return P[k]||[k,""];
}
function dzSvaFxDef(fx){
var D=typeof SVX_FX_DEFS!=="undefined"?SVX_FX_DEFS:[];
return D.find(function(d){return d.type===fx;})||null;
}
function dzSvaFxNom(fx){var d=dzSvaFxDef(fx);return d?d.label:fx;}
/* ── opérations PURES sur le graphe {noeuds:[{id,type,params,x,y}], liens:[{de,vers,entree}]} ── */
function dzSvaVide(){return {noeuds:[],liens:[]};}
function dzSvaDefauts(cat,t,fx){
var p={};
if(t==="effet"){var e=(cat&&cat.effets&&cat.effets[fx])||{};p.fx=fx;Object.keys(e).forEach(function(k){p[k]=e[k][2];});if(fx==="filter")p.mode="low";return p;}
var n=((cat&&cat.noeuds)||[]).find(function(q){return q.type===t;});
if(n)Object.keys(n.params).forEach(function(k){p[k]=n.params[k][2];});
if(dzSvaEstIa(t)){p.modele=dzSvaIaOp(cat,t).defaut||"";p.prompt="";}
return p;
}
function dzSvaEntrees(cat,n){
if(n.type==="mix")return Math.max(2,Math.min(8,Math.round(Number(n.params.entrees)||2)));
var d=((cat&&cat.noeuds)||[]).find(function(q){return q.type===n.type;});
return d?d.entrees:1;
}
function dzSvaId(g,t){var k=1;while(g.noeuds.some(function(n){return n.id===t+k;}))k++;return t+k;}
function dzSvaAjouter(g,cat,t,x,y,extra){
var n={id:dzSvaId(g,t),type:t,params:Object.assign(dzSvaDefauts(cat,t,extra&&extra.fx),(extra&&extra.params)||{}),x:Math.round(x),y:Math.round(y)};
return {g:{noeuds:g.noeuds.concat([n]),liens:g.liens.slice()},id:n.id};
}
function dzSvaAncetre(g,a,b){
var vu={},pile=[a];
while(pile.length){var c=pile.pop();if(c===b)return !0;if(vu[c])continue;vu[c]=1;g.liens.forEach(function(l){if(l.vers===c)pile.push(l.de);});}
return !1;
}
/* relie la sortie de `de` à l'entrée `e` de `vers` (remplace le lien déjà posé sur cette entrée) ; refus : boucle */
function dzSvaRelier(g,de,vers,e){
if(de===vers||dzSvaAncetre(g,de,vers))return {g:g,refus:"boucle"};
var L=g.liens.filter(function(l){return !(l.vers===vers&&l.entree===e);});
L.push({de:de,vers:vers,entree:e});
return {g:{noeuds:g.noeuds,liens:L}};
}
function dzSvaDelier(g,vers,e){return {noeuds:g.noeuds,liens:g.liens.filter(function(l){return !(l.vers===vers&&l.entree===e);})};}
function dzSvaSupprimer(g,id){
return {noeuds:g.noeuds.filter(function(n){return n.id!==id;}),liens:g.liens.filter(function(l){return l.de!==id&&l.vers!==id;})};
}
function dzSvaBornes(cat,n,k){
if(n.type==="effet"){var e=(cat&&cat.effets&&cat.effets[n.params.fx])||{};return e[k]||null;}
var d=((cat&&cat.noeuds)||[]).find(function(q){return q.type===n.type;});
return d&&d.params[k]||null;
}
/* règle un paramètre, ramené dans ses bornes ; « mix » qui perd des entrées perd aussi leurs liens */
function dzSvaRegler(g,cat,id,k,v){
var N=g.noeuds.map(function(n){
if(n.id!==id)return n;
var b=dzSvaBornes(cat,n,k),p=Object.assign({},n.params);
if(b){var f=Number(v);if(!isFinite(f))f=b[2];p[k]=Math.max(b[0],Math.min(b[1],f));if((n.type==="mix"&&k==="entrees")||(n.type==="plage"&&k==="boucles")||k==="prise")p[k]=Math.round(p[k]);}
else p[k]=v;
return Object.assign({},n,{params:p});
});
var L=g.liens;
var m=N.find(function(n){return n.id===id;});
if(m&&m.type==="mix")L=L.filter(function(l){return l.vers!==id||l.entree<m.params.entrees;});
return {noeuds:N,liens:L};
}
function dzSvaDeplacer(g,id,x,y){return {noeuds:g.noeuds.map(function(n){return n.id===id?Object.assign({},n,{x:Math.round(x),y:Math.round(y)}):n;}),liens:g.liens};}
/* insère un nœud juste après `apres` : il prend la place de son premier lien sortant */
function dzSvaInserer(g,cat,apres,t,params){
var a=g.noeuds.find(function(n){return n.id===apres;});
if(!a)return {g:g,id:null};
var R=dzSvaAjouter(g,cat,t,a.x+DZSVA_LARG+40,a.y+60,{params:params});
var sortant=R.g.liens.find(function(l){return l.de===apres;});
var L=R.g.liens.filter(function(l){return l!==sortant;});
L.push({de:apres,vers:R.id,entree:0});
if(sortant)L.push({de:R.id,vers:sortant.vers,entree:sortant.entree});
return {g:{noeuds:R.g.noeuds,liens:L},id:R.id};
}
/* le graphe tel que le serveur le lit (positions retirées) */
function dzSvaServeur(g){
return {noeuds:g.noeuds.map(function(n){return {id:n.id,type:n.type,params:n.params};}),liens:g.liens.map(function(l){return {de:l.de,vers:l.vers,entree:l.entree};})};
}
/* la source en amont d'un nœud (première entrée, en remontant) */
function dzSvaSourceDe(g,id){
var vu={},c=id;
while(c&&!vu[c]){
vu[c]=1;
var n=g.noeuds.find(function(q){return q.id===c;});
if(!n)return null;
if(n.type==="source")return n;
var l=g.liens.find(function(q){return q.vers===c&&q.entree===0;});
c=l?l.de:null;
}
return null;
}
function dzSvaChaine(cat,etapes,f1,f2){
var g=dzSvaVide(),ids=[],x=40;
etapes.forEach(function(e){var R=dzSvaAjouter(g,cat,e.t,e.x!=null?e.x:x,e.y!=null?e.y:80,{fx:e.fx,params:e.params});g=R.g;ids.push(R.id);if(e.x==null)x+=DZSVA_LARG+44;});
return {g:g,ids:ids};
}
/* préréglages de chaîne ; f1 = la piste choisie, f2 = une voix (Voix sur musique) */
function dzSvaPrereglage(cat,nom,f1,f2){
var S={t:"source",params:{fichier:f1||""}},O={t:"sortie"};
var E=function(fx,p){return {t:"effet",fx:fx,params:p};};
var lin=function(etapes){var C=dzSvaChaine(cat,etapes);for(var i=0;i+1<C.ids.length;i++)C.g=dzSvaRelier(C.g,C.ids[i],C.ids[i+1],0).g;return C.g;};
if(nom==="radio")return lin([S,E("filter",{mode:"band",freq:1800,q:0.8}),E("compressor",{threshold_db:-24,ratio:6}),E("distortion",{drive:12}),{t:"limiteur",params:{plafond_db:-1}},O]);
if(nom==="lofi")return lin([S,E("filter",{mode:"low",freq:3200,q:0.7}),E("distortion",{drive:8}),{t:"chorus",params:{melange:25}},{t:"gain",params:{db:-2}},O]);
if(nom==="hall")return lin([S,E("eq3",{bass_db:-2,treble_db:2}),E("reverb",{mix:45,decay_s:4.5}),{t:"limiteur",params:{plafond_db:-1}},O]);
var C=dzSvaChaine(cat,[{t:"source",params:{fichier:f1||""},x:40,y:60},{t:"source",params:{fichier:f2||f1||""},x:40,y:240},{t:"gain",params:{db:-10},x:260,y:60},{t:"duck",x:480,y:60},{t:"mix",x:700,y:140},{t:"limiteur",params:{plafond_db:-1},x:920,y:140},{t:"sortie",x:1140,y:140}]);
var I=C.ids,g=C.g;
g=dzSvaRelier(g,I[0],I[2],0).g;
g=dzSvaRelier(g,I[2],I[3],0).g;
g=dzSvaRelier(g,I[1],I[3],1).g;
g=dzSvaRelier(g,I[3],I[4],0).g;
g=dzSvaRelier(g,I[1],I[4],1).g;
g=dzSvaRelier(g,I[4],I[5],0).g;
g=dzSvaRelier(g,I[5],I[6],0).g;
return g;
}
function dzSvaPortIn(n,e){return {x:n.x,y:n.y+DZSVA_TETE+DZSVA_PORT/2+e*DZSVA_PORT};}
function dzSvaPortOut(n){return {x:n.x+DZSVA_LARG,y:n.y+DZSVA_TETE+DZSVA_PORT/2};}
function dzSvaCourbe(a,b){var d=Math.max(40,Math.abs(b.x-a.x)/2);return "M"+a.x+" "+a.y+"C"+(a.x+d)+" "+a.y+" "+(b.x-d)+" "+b.y+" "+b.x+" "+b.y;}
function dzSvaLire(){try{var t=localStorage.getItem(DZSVA_CLE);var g=t?JSON.parse(t):null;return g&&Array.isArray(g.noeuds)&&Array.isArray(g.liens)?g:null;}catch(e){return null;}}
function dzSvaGarder(g){try{localStorage.setItem(DZSVA_CLE,JSON.stringify(g));}catch(e){}}
function dzSvaPas(b,entier){if(entier)return 1;var s=(b[1]-b[0])/200;var p=Math.pow(10,Math.floor(Math.log10(s)));return Math.max(p,0.001);}
function dzSvaFmt(v){var f=Number(v);return Math.abs(f)>=100?String(Math.round(f)):String(Math.round(f*100)/100);}
function DzSvAtelier(p){
var US=x.useState,UE=x.useEffect,UR=x.useRef;
var s1=US(null),cat=s1[0],setCat=s1[1];
var s2=US(null),audios=s2[0],setAudios=s2[1];
var s3=US(null),g=s3[0],setG=s3[1];
var s4=US(""),sel=s4[0],setSel=s4[1];
var s5=US({passe:[],futur:[]}),hist=s5[0],setHist=s5[1];
var s6=US({x:0,y:0,z:1}),vue=s6[0],setVue=s6[1];
var s7=US(null),lienTemp=s7[0],setLienTemp=s7[1];
var s8=US(null),valid=s8[0],setValid=s8[1];
var s9=US(""),note=s9[0],setNote=s9[1];
var s10=US(null),apercu=s10[0],setApercu=s10[1];
var s11=US("B"),ab=s11[0],setAb=s11[1];
var s12=US(!1),occupe=s12[0],setOccupe=s12[1];
var s13=US(""),nom=s13[0],setNom=s13[1];
var s14=US(0),curseur=s14[0],setCurseur=s14[1];
var s15=US(null),frise=s15[0],setFrise=s15[1];
var s16=US(null),region=s16[0],setRegion=s16[1];
var s17=US(null),rendu=s17[0],setRendu=s17[1];
var s18=US(null),devis=s18[0],setDevis=s18[1];
var s19=US(""),arme=s19[0],setArme=s19[1];
var toile=UR(null),gRef=UR(null),vueRef=UR(vue),lecteur=UR(null);
gRef.current=g;
vueRef.current=vue;
/* chargement : catalogue du serveur, pistes, graphe gardé (sinon source → sortie) */
UE(function(){
Promise.all([fetch("/api/audio/graph/noeuds").then(dzSvpJson),fetch("/api/audio").then(dzSvpJson),fetch("/api/audio/meta").then(dzSvpJson)]).then(function(R){
var C=R[0],L=R[1].audio||[],M=R[2].meta||{};
setCat(C);
setAudios(L);
var mus=L.find(function(a){return (M[a.name]||{}).kind==="musique";})||L[0];
var G0=dzSvaLire();
if(!G0){var A=dzSvaAjouter(dzSvaVide(),C,"source",60,120,{params:{fichier:mus?mus.name:""}});var B=dzSvaAjouter(A.g,C,"sortie",420,120);G0=dzSvaRelier(B.g,A.id,B.id,0).g;}
setG(ajoutEnAttente(G0,C));
}).catch(function(err){setNote(String(err&&err.message||err));setG(dzSvaVide());});
function ev(){setG(function(G1){return G1?ajoutEnAttente(G1,gCat()):G1;});}
window.addEventListener("deepotus:sva-ajout",ev);
return function(){window.removeEventListener("deepotus:sva-ajout",ev);};
},[]);
var catRef=UR(null);
catRef.current=cat;
function gCat(){return catRef.current;}
/* « Ouvrir dans l'Atelier » (page Importer et séparer) : window.__dzSvAtelierAjout = {fichier} */
function ajoutEnAttente(G1,C){
var a=null;
try{a=window.__dzSvAtelierAjout;window.__dzSvAtelierAjout=null;}catch(e){a=null;}
if(!a||!a.fichier||!C)return G1;
var y=40+G1.noeuds.filter(function(n){return n.type==="source";}).length*120;
var R=dzSvaAjouter(G1,C,"source",40,y,{params:{fichier:a.fichier}});
var o=R.g.noeuds.find(function(n){return n.type==="sortie";});
var G2=R.g;
if(o&&!G2.liens.some(function(l){return l.vers===o.id;}))G2=dzSvaRelier(G2,R.id,o.id,0).g;
setSel(R.id);
setNote(dzT("sonvfx.atelier.source_ajoutee",{nom:a.fichier}));
return G2;
}
function changer(G1,sansHist){
if(!G1)return;
if(!sansHist){var avant=gRef.current;setHist(function(H){return {passe:H.passe.concat([avant]).slice(-50),futur:[]};});}
setG(G1);
dzSvaGarder(G1);
}
function pousser(){var avant=gRef.current;setHist(function(H){return {passe:H.passe.concat([avant]).slice(-50),futur:[]};});}
function annuler(){
if(!hist.passe.length)return;
var prec=hist.passe[hist.passe.length-1];
setHist({passe:hist.passe.slice(0,-1),futur:[g].concat(hist.futur)});
setG(prec);
dzSvaGarder(prec);
}
function retablir(){
if(!hist.futur.length)return;
var suiv=hist.futur[0];
setHist({passe:hist.passe.concat([g]),futur:hist.futur.slice(1)});
setG(suiv);
dzSvaGarder(suiv);
}
/* validation par le serveur, 350 ms après le dernier changement */
UE(function(){
if(!g)return;
var t=setTimeout(function(){
fetch("/api/audio/graph/valider",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(dzSvaServeur(g))}).then(dzSvpJson).then(function(D){setValid({ok:!0,ignores:D.ignores||[]});chiffrer(g);}).catch(function(err){setValid({ok:!1,msg:String(err&&err.message||err)});setDevis(null);});
},350);
setArme("");
return function(){clearTimeout(t);};
},[g]);
/* t272 : le devis des nœuds IA (gratuit), affiché AVANT ; rien à chiffrer sans nœud IA */
function chiffrer(G1){
if(!G1||!G1.noeuds.some(function(n){return dzSvaEstIa(n.type);})){setDevis(null);return;}
fetch("/api/audio/graph/devis",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({graphe:dzSvaServeur(G1)})}).then(dzSvpJson).then(function(D){setDevis(D);}).catch(function(){setDevis(null);});
}
var aPayer=devis&&devis.a_generer&&devis.a_generer.length?devis:null;
/* une action qui ferait générer s'arme au premier clic (le prix est dit), part au second avec generer:true */
function armer(action){
if(!aPayer)return !0;
if(arme===action){setArme("");return !0;}
setArme(action);
setNote(dzT("sonvfx.atelier.ia_confirmer_aide",{prix:dzSvaPrix(aPayer.usd)}));
return !1;
}
/* la frise suit la source de référence : celle du nœud choisi, sinon la première */
var nSel=g?g.noeuds.find(function(n){return n.id===sel;})||null:null;
var ref=g?(nSel?dzSvaSourceDe(g,nSel.id):null)||g.noeuds.find(function(n){return n.type==="source";})||null:null;
var refFichier=ref&&ref.params.fichier||"";
UE(function(){
if(!refFichier){setFrise(null);return;}
var c=DZSVA_CACHE.pics[refFichier];
if(c){setFrise(c);return;}
var AC=window.AudioContext||window.webkitAudioContext;
if(!AC){setFrise({fichier:refFichier,dur:0,pics:[]});return;}
var actif=!0;
fetch("/api/audio/"+encodeURIComponent(refFichier)).then(function(res){return res.arrayBuffer();}).then(function(buf){var ctx=new AC();return ctx.decodeAudioData(buf).then(function(a){try{ctx.close();}catch(e){}return a;});}).then(function(a){
var d=a.getChannelData(0),n=300,pas=Math.max(1,Math.floor(d.length/n)),P=[];
for(var i=0;i<n;i++){var m=0;for(var j=i*pas;j<Math.min(d.length,(i+1)*pas);j+=8){var v=Math.abs(d[j]);if(v>m)m=v;}P.push(m);}
var F={fichier:refFichier,dur:a.duration,pics:P};
DZSVA_CACHE.pics[refFichier]=F;
if(actif)setFrise(F);
}).catch(function(){if(actif)setFrise({fichier:refFichier,dur:0,pics:[]});});
return function(){actif=!1;};
},[refFichier]);
/* cadre tous les nœuds dans la vue (zoom 30 % à 100 %) */
function cadrer(G1){
var el=toile.current,w=el?el.clientWidth:800,h=el?el.clientHeight:400;
if(!G1||!G1.noeuds.length)return {x:0,y:0,z:1};
var x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
G1.noeuds.forEach(function(n){x0=Math.min(x0,n.x);y0=Math.min(y0,n.y);x1=Math.max(x1,n.x+DZSVA_LARG);y1=Math.max(y1,n.y+DZSVA_TETE+3*DZSVA_PORT);});
var z=Math.max(0.3,Math.min(1,(w-60)/(x1-x0),(h-60)/(y1-y0)));
return {x:(w-(x1-x0)*z)/2-x0*z,y:(h-(y1-y0)*z)/2-y0*z,z:z};
}
function centre(){var el=toile.current,w=el?el.clientWidth:800,h=el?el.clientHeight:400;return {x:(w/2-vue.x)/vue.z-DZSVA_LARG/2,y:(h/2-vue.y)/vue.z-40};}
function ajouter(it){
if(!g||!cat)return;
var c=centre();
var R=dzSvaAjouter(g,cat,it.t,c.x+(g.noeuds.length%5)*14,c.y+(g.noeuds.length%5)*14,{fx:it.fx,params:it.t==="source"&&audios&&audios[0]?{fichier:audios[0].name}:null});
changer(R.g);
setSel(R.id);
}
function supprimer(id){if(!g||!id)return;changer(dzSvaSupprimer(g,id));setSel("");}
function preregler(nomP){
if(!cat)return;
var f1=refFichier||(audios&&audios[0]&&audios[0].name)||"";
var autre=(audios||[]).find(function(a){return a.name!==f1;});
var G2=dzSvaPrereglage(cat,nomP,f1,autre?autre.name:f1);
changer(G2);
setSel("");
setVue(cadrer(G2));
setNote(dzT("sonvfx.atelier.prereglage_pose"));
}
/* coordonnées du monde depuis un événement pointeur */
function monde(e){var el=toile.current,rc=el?el.getBoundingClientRect():{left:0,top:0},v=vueRef.current;return {x:(e.clientX-rc.left-v.x)/v.z,y:(e.clientY-rc.top-v.y)/v.z};}
function suivre(bouge,fin){
function m(e){bouge(e);}
function u(e){window.removeEventListener("pointermove",m);window.removeEventListener("pointerup",u);fin(e);}
window.addEventListener("pointermove",m);
window.addEventListener("pointerup",u);
}
function saisirNoeud(e,n){
if(e.button!==0)return;
e.stopPropagation();
setSel(n.id);
var w=monde(e),dx=w.x-n.x,dy=w.y-n.y,depart=gRef.current,bouge=!1;
suivre(function(ev){var q=monde(ev);bouge=!0;setG(function(G1){return dzSvaDeplacer(G1,n.id,q.x-dx,q.y-dy);});},function(){if(bouge){setHist(function(H){return {passe:H.passe.concat([depart]).slice(-50),futur:[]};});dzSvaGarder(gRef.current);}});
}
function tirerLien(e,n){
if(e.button!==0)return;
e.stopPropagation();
var a=dzSvaPortOut(n);
setLienTemp({a:a,b:a});
suivre(function(ev){setLienTemp({a:a,b:monde(ev)});},function(ev){
setLienTemp(null);
var cible=document.elementFromPoint?document.elementFromPoint(ev.clientX,ev.clientY):null;
var port=cible&&cible.closest?cible.closest("[data-sva-in]"):null;
if(!port)return;
relier(n.id,port.getAttribute("data-sva-noeud"),Number(port.getAttribute("data-sva-in")));
});
}
function relier(de,vers,e){
var R=dzSvaRelier(gRef.current,de,vers,e);
if(R.refus){setNote(dzT("sonvfx.atelier.boucle_refusee"));return;}
changer(R.g);
}
function saisirFond(e){
if(e.button!==0)return;
setSel("");
var v0=vueRef.current,x0=e.clientX,y0=e.clientY;
suivre(function(ev){setVue({x:v0.x+ev.clientX-x0,y:v0.y+ev.clientY-y0,z:v0.z});},function(){});
}
function zoomer(f,cx,cy){
var v=vueRef.current,el=toile.current,w=el?el.clientWidth:800,h=el?el.clientHeight:400;
if(cx==null){cx=w/2;cy=h/2;}
var z=Math.max(0.3,Math.min(2.5,v.z*f));
setVue({x:cx-(cx-v.x)*z/v.z,y:cy-(cy-v.y)*z/v.z,z:z});
}
function molette(e){var el=toile.current,rc=el.getBoundingClientRect();zoomer(e.deltaY<0?1.1:1/1.1,e.clientX-rc.left,e.clientY-rc.top);}
function clavier(e){
var t=e.target&&e.target.tagName;
if(t==="INPUT"||t==="SELECT"||t==="TEXTAREA")return;
if((e.key==="Delete"||e.key==="Backspace")&&sel){e.preventDefault();supprimer(sel);}
else if((e.ctrlKey||e.metaKey)&&(e.key==="z"||e.key==="Z")&&!e.shiftKey){e.preventDefault();annuler();}
else if((e.ctrlKey||e.metaKey)&&(e.key==="y"||e.key==="Y"||((e.key==="z"||e.key==="Z")&&e.shiftKey))){e.preventDefault();retablir();}
}
/* aperçu et A/B */
function ecouter(){
if(!g||occupe)return;
if(!armer("ecouter"))return;
var payant=!!aPayer;
setOccupe(!0);
setNote("");
fetch("/api/audio/graph/apercu",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({graphe:dzSvaServeur(g),depuis:curseur,generer:payant})}).then(function(res){
if(!res.ok)return dzSvpJson(res);
return res.blob().then(function(b){
if(apercu&&apercu.url)try{URL.revokeObjectURL(apercu.url);}catch(e){}
var u=URL.createObjectURL(b);
setApercu({url:u,depuis:curseur});
setAb("B");
jouer(u,0);
});
}).then(function(){setOccupe(!1);if(payant)chiffrer(gRef.current);}).catch(function(err){setOccupe(!1);setNote(String(err&&err.message||err));});
}
function jouer(src,t){var el=lecteur.current;if(!el)return;el.src=src;try{el.currentTime=t||0;}catch(e){}var pr=el.play();if(pr&&pr.catch)pr.catch(function(){});}
function basculer(){
if(!apercu)return;
var el=lecteur.current,t=el?el.currentTime||0:0;
if(ab==="B"){if(!refFichier)return;setAb("A");jouer("/api/audio/"+encodeURIComponent(refFichier),apercu.depuis+t);}
else{setAb("B");jouer(apercu.url,Math.max(0,t-apercu.depuis));}
}
function rendre(){
if(!g||occupe)return;
if(!armer("rendre"))return;
var payant=!!aPayer;
setOccupe(!0);
setNote("");
fetch("/api/audio/graph/rendre",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({graphe:dzSvaServeur(g),nom:nom,generer:payant})}).then(dzSvpJson).then(function(D){setOccupe(!1);setRendu(D);setNote(dzT("sonvfx.atelier.rendu_fait",{nom:D.filename,duree:dzSvpDuree(D.dur)})+(D.usd?" "+dzT("sonvfx.atelier.ia_paye",{prix:dzSvaPrix(D.usd)}):""));if(payant)chiffrer(gRef.current);}).catch(function(err){setOccupe(!1);setNote(String(err&&err.message||err));});
}
/* frise : un clic place l'aperçu, un glisser trace une région → nœud Plage */
function saisirFrise(e){
if(!frise||!frise.dur)return;
var el=e.currentTarget,rc=el.getBoundingClientRect();
var t=function(ev){return Math.max(0,Math.min(frise.dur,(ev.clientX-rc.left)/rc.width*frise.dur));};
var a=t(e),b=a;
setRegion({a:a,b:a});
suivre(function(ev){b=t(ev);setRegion({a:Math.min(a,b),b:Math.max(a,b)});},function(){
setRegion(null);
var lo=Math.round(Math.min(a,b)*100)/100,hi=Math.round(Math.max(a,b)*100)/100;
if(hi-lo<0.05){setCurseur(lo);return;}
var G1=gRef.current,n=G1.noeuds.find(function(q){return q.id===sel;});
if(dzSvaAPlage(n)){var G2=dzSvaRegler(G1,catRef.current,n.id,"debut",lo);changer(dzSvaRegler(G2,catRef.current,n.id,"fin",hi));return;}
if(!ref)return;
var R=dzSvaInserer(G1,catRef.current,ref.id,"plage",{debut:lo,fin:hi});
if(R.id){changer(R.g);setSel(R.id);}
});
}
if(!g||!cat)return r.jsx("div",{className:"dzsva",children:r.jsx("div",{className:"dzsva-attente",children:note||dzT("sonvfx.atelier.chargement")})});
/* ── rendu ── */
var palette=r.jsxs("aside",{className:"dzsva-palette",children:[
r.jsx("div",{className:"dzsva-titre",children:dzT("sonvfx.atelier.prereglages")}),
r.jsx("div",{className:"dzsva-pres",children:[["radio",dzT("sonvfx.atelier.pre_radio")],["lofi",dzT("sonvfx.atelier.pre_lofi")],["hall",dzT("sonvfx.atelier.pre_hall")],["voix",dzT("sonvfx.atelier.pre_voix")]].map(function(q){return r.jsx("button",{type:"button",className:"dzsva-btn","data-sva-pre":q[0],onClick:function(){preregler(q[0]);},children:q[1]},q[0]);})}),
dzSvaCats().map(function(C){return r.jsxs("div",{className:"dzsva-cat",style:{"--sva-c":C.c},children:[
r.jsx("div",{className:"dzsva-titre",children:C.lbl}),
r.jsx("div",{className:"dzsva-items",children:C.items.map(function(it){var lbl=it.t==="effet"?dzSvaFxNom(it.fx):dzSvaNomType(it.t);return r.jsx("button",{type:"button",className:"dzsva-item","data-sva-ajout":it.fx||it.t,onClick:function(){ajouter(it);},children:lbl},it.fx||it.t);})})]},C.id);})]});
function noeud(n){
var C=dzSvaCatDe(n),k=dzSvaEntrees(cat,n),h=DZSVA_TETE+Math.max(1,k)*DZSVA_PORT+8;
var titre=n.type==="effet"?dzSvaFxNom(n.params.fx):dzSvaNomType(n.type);
var mIa=dzSvaEstIa(n.type)?dzSvaIaModele(cat,n):null;
var sous=n.type==="source"?(n.params.fichier||dzT("sonvfx.atelier.sans_fichier")):mIa?mIa.label:"";
var ins=[];
for(var e=0;e<k;e++)ins.push(r.jsx("span",{className:"dzsva-in","data-sva-in":String(e),"data-sva-noeud":n.id,style:{top:DZSVA_TETE+e*DZSVA_PORT+DZSVA_PORT/2-6},title:n.type==="duck"?(e?dzT("sonvfx.atelier.port_declencheur"):dzT("sonvfx.atelier.port_principal")):dzT("sonvfx.atelier.port_entree")},"i"+e));
return r.jsxs("div",{className:"dzsva-noeud","data-sva-id":n.id,"data-sel":n.id===sel?"":void 0,"data-ignore":valid&&valid.ignores&&valid.ignores.indexOf(n.id)>=0?"":void 0,style:{left:n.x,top:n.y,width:DZSVA_LARG,height:h,"--sva-c":C.c},onPointerDown:function(ev){saisirNoeud(ev,n);},children:[
r.jsx("div",{className:"dzsva-ntete",children:titre}),
sous?r.jsx("div",{className:"dzsva-nsous",children:sous}):null,
ins,
n.type!=="sortie"?r.jsx("span",{className:"dzsva-out","data-sva-out":n.id,title:dzT("sonvfx.atelier.port_sortie"),style:{top:DZSVA_TETE+DZSVA_PORT/2-6},onPointerDown:function(ev){tirerLien(ev,n);}}):null]},n.id);
}
var liens=g.liens.map(function(l){
var a=g.noeuds.find(function(n){return n.id===l.de;}),b=g.noeuds.find(function(n){return n.id===l.vers;});
if(!a||!b)return null;
return r.jsx("path",{className:"dzsva-lien",d:dzSvaCourbe(dzSvaPortOut(a),dzSvaPortIn(b,l.entree)),onDoubleClick:function(){changer(dzSvaDelier(g,l.vers,l.entree));}},l.de+">"+l.vers+":"+l.entree);
});
var toileEl=r.jsxs("div",{ref:toile,className:"dzsva-toile",tabIndex:0,"aria-label":dzT("sonvfx.atelier.toile"),onPointerDown:saisirFond,onWheel:molette,onKeyDown:clavier,children:[
r.jsxs("div",{className:"dzsva-monde",style:{transform:"translate("+vue.x+"px,"+vue.y+"px) scale("+vue.z+")"},children:[
r.jsxs("svg",{className:"dzsva-svg",width:4000,height:3000,children:[liens,lienTemp?r.jsx("path",{className:"dzsva-lien dzsva-temp",d:dzSvaCourbe(lienTemp.a,lienTemp.b)}):null]}),
g.noeuds.map(noeud)]}),
r.jsxs("div",{className:"dzsva-outils",children:[
r.jsx("button",{type:"button",className:"dzsva-mini",title:dzT("sonvfx.atelier.zoom_moins"),"aria-label":dzT("sonvfx.atelier.zoom_moins"),onPointerDown:function(e){e.stopPropagation();},onClick:function(){zoomer(1/1.2);},children:__dzGl("dz-action-zoom-arriere",14)}),
r.jsx("span",{className:"dzsva-z",children:Math.round(vue.z*100)+" %"}),
r.jsx("button",{type:"button",className:"dzsva-mini",title:dzT("sonvfx.atelier.zoom_plus"),"aria-label":dzT("sonvfx.atelier.zoom_plus"),onPointerDown:function(e){e.stopPropagation();},onClick:function(){zoomer(1.2);},children:__dzGl("dz-action-zoom-avant",14)}),
r.jsx("button",{type:"button",className:"dzsva-mini",title:dzT("sonvfx.atelier.recentrer"),"aria-label":dzT("sonvfx.atelier.recentrer"),onPointerDown:function(e){e.stopPropagation();},onClick:function(){setVue(cadrer(g));},children:__dzGl("dz-action-recentrer",14)}),
r.jsx("button",{type:"button",className:"dzsva-mini","data-sva":"annuler",disabled:!hist.passe.length,title:dzT("sonvfx.atelier.annuler"),"aria-label":dzT("sonvfx.atelier.annuler"),onPointerDown:function(e){e.stopPropagation();},onClick:annuler,children:__dzGl("dz-action-annuler",14)}),
r.jsx("button",{type:"button",className:"dzsva-mini","data-sva":"retablir",disabled:!hist.futur.length,title:dzT("sonvfx.atelier.retablir"),"aria-label":dzT("sonvfx.atelier.retablir"),onPointerDown:function(e){e.stopPropagation();},onClick:retablir,children:__dzGl("dz-action-retablir",14)})]})]});
function curseurParam(n,k,b,lib,unite,step){
var v=n.params[k];
var entier=(n.type==="mix"&&k==="entrees")||(n.type==="plage"&&k==="boucles")||k==="prise";
return r.jsxs("label",{className:"dzsva-param","data-sva-param":k,children:[
r.jsx("span",{className:"dzsva-plib",children:lib}),
r.jsx("input",{type:"range",min:b[0],max:b[1],step:step||dzSvaPas(b,entier),value:v==null?b[2]:v,onPointerDown:pousser,onKeyDown:pousser,onChange:function(e){changer(dzSvaRegler(gRef.current,cat,n.id,k,Number(e.target.value)),!0);}}),
r.jsx("span",{className:"dzsva-pval",children:dzSvaFmt(v==null?b[2]:v)+(unite?" "+unite:"")})]},k);
}
function inspecteur(){
if(!nSel)return r.jsxs(r.Fragment,{children:[
r.jsx("div",{className:"dzsva-titre",children:dzT("sonvfx.atelier.inspecteur")}),
r.jsx("div",{className:"dzsva-aide",children:dzT("sonvfx.atelier.aide_vide")})]});
var n=nSel,champs=[];
if(n.type==="source"){
champs.push(r.jsxs("label",{className:"dzsva-param",children:[r.jsx("span",{className:"dzsva-plib",children:dzT("sonvfx.atelier.fichier")}),
r.jsx("select",{value:n.params.fichier||"",onChange:function(e){changer(dzSvaRegler(g,cat,n.id,"fichier",String(e.target.value)));},children:(audios||[]).map(function(a){return r.jsx("option",{value:a.name,children:a.name},a.name);})})]},"fichier"));
}
else if(n.type==="effet"){
var def=dzSvaFxDef(n.params.fx),bornes=(cat.effets||{})[n.params.fx]||{};
champs.push(r.jsxs("label",{className:"dzsva-param",children:[r.jsx("span",{className:"dzsva-plib",children:dzT("sonvfx.atelier.effet")}),
r.jsx("select",{value:n.params.fx,onChange:function(e){var fx=String(e.target.value);changer({noeuds:g.noeuds.map(function(q){return q.id===n.id?Object.assign({},q,{params:dzSvaDefauts(cat,"effet",fx)}):q;}),liens:g.liens});},children:Object.keys(cat.effets||{}).map(function(fx){return r.jsx("option",{value:fx,children:dzSvaFxNom(fx)},fx);})})]},"fx"));
var P=def?def.params:Object.keys(bornes).map(function(k){return {k:k,label:k};});
P.forEach(function(pd){
if(pd.hide)return;
if(pd.kind==="seg"){champs.push(r.jsxs("label",{className:"dzsva-param",children:[r.jsx("span",{className:"dzsva-plib",children:dzT("sonvfx.atelier.mode")}),r.jsx("select",{value:n.params[pd.k]||pd.d,onChange:function(e){changer(dzSvaRegler(g,cat,n.id,pd.k,String(e.target.value)));},children:pd.opts.map(function(o){return r.jsx("option",{value:o[0],children:o[1]},o[0]);})})]},pd.k));return;}
var b=bornes[pd.k];
if(b)champs.push(curseurParam(n,pd.k,b,pd.label||pd.k,pd.unit||"",pd.step));
});
}
else if(dzSvaEstIa(n.type)){
var opIa=dzSvaIaOp(cat,n.type);
champs.push(r.jsxs("label",{className:"dzsva-param","data-sva-param":"modele",children:[r.jsx("span",{className:"dzsva-plib",children:dzT("sonvfx.atelier.p_modele")}),
r.jsx("select",{value:n.params.modele||opIa.defaut,onChange:function(e){changer(dzSvaRegler(g,cat,n.id,"modele",String(e.target.value)));},children:opIa.modeles.map(function(m){return r.jsx("option",{value:m.id,children:m.label+" · "+dzSvaPrixModele(m)+(m.dispo?"":" · "+dzT("sonvfx.atelier.sans_cle",{cle:m.cle}))},m.id);})})]},"modele"));
champs.push(r.jsxs("label",{className:"dzsva-param dzsva-texte","data-sva-param":"prompt",children:[r.jsx("span",{className:"dzsva-plib",children:dzT("sonvfx.atelier.p_description")}),
r.jsx("textarea",{rows:3,value:n.params.prompt||"",placeholder:dzT("sonvfx.atelier.ia_prompt_aide"),"aria-label":dzT("sonvfx.atelier.p_description"),onFocus:pousser,onChange:function(e){changer(dzSvaRegler(gRef.current,cat,n.id,"prompt",String(e.target.value)),!0);}})]},"prompt"));
var dIa=(cat.noeuds||[]).find(function(q){return q.type===n.type;});
Object.keys((dIa&&dIa.params)||{}).forEach(function(k){var L=k==="fin"?[dzT("sonvfx.atelier.p_fin_ia"),"s"]:k==="debut"?[dzT("sonvfx.atelier.p_debut_ia"),"s"]:dzSvaParamLib(k);champs.push(curseurParam(n,k,dIa.params[k],L[0],L[1]));});
var aGen=devis&&(devis.a_generer||[]).find(function(q){return q.id===n.id;});
var dejaFait=devis&&(devis.deja||[]).indexOf(n.id)>=0;
var mSel=dzSvaIaModele(cat,n);
champs.push(r.jsx("div",{className:"dzsva-ia","data-sva":"ia-noeud",children:aGen?dzT("sonvfx.atelier.ia_prix",{prix:dzSvaPrix(aGen.usd)}):dejaFait?dzT("sonvfx.atelier.ia_deja"):mSel?dzT("sonvfx.atelier.ia_prix",{prix:dzSvaPrixModele(mSel)}):""},"prix"));
champs.push(r.jsx("div",{className:"dzsva-aide",children:dzT("sonvfx.atelier.ia_aide")},"aide"));
}
else{
var d=(cat.noeuds||[]).find(function(q){return q.type===n.type;});
Object.keys((d&&d.params)||{}).forEach(function(k){var L=dzSvaParamLib(k);champs.push(curseurParam(n,k,d.params[k],L[0],L[1]));});
}
return r.jsxs(r.Fragment,{children:[
r.jsx("div",{className:"dzsva-titre",children:n.type==="effet"?dzSvaFxNom(n.params.fx):dzSvaNomType(n.type)}),
r.jsx("div",{className:"dzsva-aide",children:n.id}),
champs.length?champs:r.jsx("div",{className:"dzsva-aide",children:dzT("sonvfx.atelier.sans_reglage")}),
r.jsx("button",{type:"button",className:"dzsva-btn","data-sva":"supprimer",onClick:function(){supprimer(n.id);},children:dzT("sonvfx.atelier.supprimer_noeud")})]});
}
var plages=frise&&frise.dur?g.noeuds.filter(function(n){if(!dzSvaAPlage(n))return !1;var s=dzSvaSourceDe(g,n.id);return s&&s.params.fichier===frise.fichier;}):[];
var friseEl=r.jsxs("div",{className:"dzsva-frise",children:[
r.jsx("div",{className:"dzsva-ftete",children:frise&&frise.fichier?dzT("sonvfx.atelier.frise_de",{nom:frise.fichier,duree:dzSvpDuree(frise.dur)}):dzT("sonvfx.atelier.frise_vide")}),
r.jsxs("div",{className:"dzsva-onde","data-sva":"frise",onPointerDown:saisirFrise,children:[
frise&&frise.pics?r.jsx("svg",{viewBox:"0 0 300 100",preserveAspectRatio:"none",children:frise.pics.map(function(v,i){var h=Math.max(1,v*96);return r.jsx("rect",{x:i,y:50-h/2,width:0.7,height:h},i);})}):null,
frise&&frise.dur?plages.map(function(n){var a=n.params.debut/frise.dur*100,b=(n.params.fin||frise.dur)/frise.dur*100;return r.jsx("div",{className:"dzsva-region","data-ia":dzSvaEstIa(n.type)?"":void 0,"data-sel":n.id===sel?"":void 0,style:{left:a+"%",width:Math.max(0.3,b-a)+"%"},title:n.id},n.id);}):null,
region&&frise&&frise.dur?r.jsx("div",{className:"dzsva-region dzsva-trace",style:{left:region.a/frise.dur*100+"%",width:Math.max(0.3,(region.b-region.a)/frise.dur*100)+"%"}}):null,
frise&&frise.dur?r.jsx("div",{className:"dzsva-curseur",style:{left:curseur/frise.dur*100+"%"}}):null]}),
r.jsx("div",{className:"dzsva-aide",children:dzT("sonvfx.atelier.frise_aide")})]});
var barre=r.jsxs("div",{className:"dzsva-barre",children:[
r.jsx("span",{className:"dzsva-etat","data-ok":valid&&valid.ok?"":void 0,children:valid?(valid.ok?(valid.ignores.length?dzT("sonvfx.atelier.valide_ignores",{n:valid.ignores.length}):dzT("sonvfx.atelier.valide")):valid.msg):dzT("sonvfx.atelier.verification")}),
devis&&(aPayer||(devis.deja||[]).length)?r.jsx("span",{className:"dzsva-ia","data-sva":"ia-prix","data-payant":aPayer?"":void 0,children:aPayer?dzT("sonvfx.atelier.ia_payant",{n:aPayer.a_generer.length,prix:dzSvaPrix(aPayer.usd)}):dzT("sonvfx.atelier.ia_deja")}):null,
r.jsxs("button",{type:"button",className:"dzsva-btn","data-sva":"ecouter","data-arme":arme==="ecouter"?"":void 0,disabled:occupe||!(valid&&valid.ok),onClick:ecouter,children:[__dzGl("dz-media-preecoute",14)," ",arme!=="ecouter"?dzT("sonvfx.atelier.ecouter",{t:dzSvpDuree(curseur)}):dzT("sonvfx.atelier.confirmer_ia",{prix:dzSvaPrix(aPayer?aPayer.usd:0)})]}),
r.jsx("button",{type:"button",className:"dzsva-btn","data-sva":"ab",disabled:!apercu,"aria-pressed":ab==="A"?"true":"false",title:dzT("sonvfx.atelier.ab_aide"),onClick:basculer,children:ab==="A"?dzT("sonvfx.atelier.ab_source"):dzT("sonvfx.atelier.ab_traite")}),
r.jsx("audio",{ref:lecteur,className:"dzsva-lecteur",controls:!0}),
r.jsx("input",{className:"dzsva-nom",value:nom,placeholder:dzT("sonvfx.atelier.nom"),"aria-label":dzT("sonvfx.atelier.nom"),onChange:function(e){setNom(e.target.value);}}),
r.jsx("button",{type:"button",className:"dzsva-btn prim","data-sva":"rendre","data-arme":arme==="rendre"?"":void 0,disabled:occupe||!(valid&&valid.ok),onClick:rendre,children:occupe?dzT("sonvfx.atelier.en_cours"):arme!=="rendre"?dzT("sonvfx.atelier.rendre"):dzT("sonvfx.atelier.confirmer_ia",{prix:dzSvaPrix(aPayer?aPayer.usd:0)})}),
arme?r.jsx("button",{type:"button",className:"dzsva-btn","data-sva":"desarmer",onClick:function(){setArme("");setNote("");},children:dzT("sonvfx.pistes.annuler")}):null,
rendu?r.jsx("button",{type:"button",className:"dzsva-btn","data-sva":"montage",onClick:function(){if(p.go)p.go("montage");},children:dzT("sonvfx.atelier.vers_montage")}):null]});
return r.jsxs("div",{className:"dzsva",children:[
palette,
r.jsxs("section",{className:"dzsva-centre",children:[toileEl,friseEl,barre,note?r.jsx("div",{className:"dzsva-note",role:"status",children:note}):null]}),
r.jsx("aside",{className:"dzsva-inspecteur",children:inspecteur()})]});
}
