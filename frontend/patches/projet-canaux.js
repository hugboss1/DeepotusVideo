/* t307 tâche 4 (25/10/2026) — les CANAUX d'un projet dans la barre « Projet » de la Bibliothèque (plan
   docs/superpowers/plans/2026-10-25-t307-projets-canaux.md). Source du maillon de queue scripts/patch_bundle_dzcanaux.py,
   injectée APLATIE (une ligne) devant `function DzProjetsBar({f,setF}){` (le composant vient du maillon libsons, qu'on
   ne modifie pas : le maillon de queue réécrit sa sortie dans le bundle final). Règles d'écriture : chaque instruction
   finit par « ; » ou « } », aucune ligne ne commence par « ( » « [ » ou « // », commentaires « /* » sur des lignes
   entières seulement.
   - DzProjetCanauxIcones({projet}) : les glyphes Deepotus des canaux du projet regardé (dz-reseau-*, jamais d'emoji),
     posés juste après la liste des projets, avec un titre au survol qui nomme les comptes (« Canaux : X @a, … »). Les
     comptes viennent de window.__dzProjetCanaux.comptes(espace) (frontend/shared/dz-projet-canaux.js, en cache) ;
     tant qu'ils ne sont pas lus, l'identifiant tient lieu de nom. Aucun canal : rien.
   Hooks par alias (le compte figé des appels directs à useState ne bouge pas). Le bouton « Canaux » et l'écoute de
   « dz-projet-canaux » sont des paires du maillon, dans DzProjetsBar. Textes : clés dzT projets.canaux.*
   (frontend/shared/i18n/projets.json). */
function DzProjetCanauxIcones({projet}){/*__dzcanaux*/
  var US=x.useState,UE=x.useEffect,st=US(0),maj=st[1];
  var P=typeof window!=="undefined"?window.__dzProjetCanaux:null;
  var esp=(projet&&projet.espace_id)||"deepotus",ids=(projet&&projet.canaux)||[],cle=ids.join(",");
  UE(function(){
    if(!P||!ids.length)return;
    var vivant=true;
    P.comptes(esp).then(function(){if(vivant)maj(function(n){return n+1;});}).catch(function(){});
    return function(){vivant=false;};},[esp,cle]);
  if(!ids.length)return null;
  var liste=(P&&P.connus(esp))||[];
  var vus=ids.map(function(i){return liste.find(function(c){return c.id===i;})||{id:i,plateforme:"",libelle:i,handle:""};});
  var noms=vus.map(function(c){return c.libelle+(c.handle?" "+c.handle:"");}).join(", ");
  return r.jsx("span",{"data-dz-projet-canaux":projet.id,title:dzT("projets.canaux.survol",{noms:noms}),
    style:{display:"inline-flex",alignItems:"center",gap:5,height:24,padding:"0 6px",border:"1px solid var(--stroke)",color:"var(--ink-strong)"},
    children:vus.map(function(c){return r.jsx("span",{"data-dz-canal":c.id,style:{display:"inline-flex"},children:__dzGl(P?P.glyphe(c.plateforme):"dz-action-publier",14)},c.id);})});}
