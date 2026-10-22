/* Illustrations des presets de post-traitement (t278, lot « Menus : Son & VFX », 22/10/2026).
   Page Post-traitement de Son & VFX (DzSvPost, t276) : chaque bouton du catalogue (button[data-sv-post="ajout-<id>"])
   et chaque maillon de la pile (div[data-sv-post="maillon"][data-preset="<id>"], vignette en tête de son en-tête
   .dzsvo-mtete) reçoit l'affiche de son preset ; l'animation (WebM de 4 s en boucle) n'est chargée qu'au premier
   survol ou focus, joue tant que l'élément est survolé ou a le focus, puis revient à l'affiche. Avec
   prefers-reduced-motion, l'affiche reste fixe. Les fichiers sont des statiques rendus au développement
   (scripts/sonvfx_illustrations.py --jeu post) ; le manifeste /sonvfx/illus-post/index.json dit quels presets en ont une.
   Script posé à côté du bundle, sans toucher la page ni le maillon dzsonvfx : un MutationObserver décore les éléments
   quand l'écran les rend, et suit le preset d'un maillon s'il change. Décor seulement (aria-hidden), aucun texte.
   Angles vifs, comme tout Son & VFX. */
(function(){
  "use strict";
  var BASE="/sonvfx/illus-post/",PRESETS=null,attente=0;
  var CIBLES='[data-sv-post^="ajout-"],[data-sv-post="maillon"][data-preset]';
  function reduit(){try{return !!(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches)}catch(_e){return !1}}
  function style(){
    if(!document.head||document.getElementById("dz-post-illus-css"))return;
    var s=document.createElement("style");s.id="dz-post-illus-css";
    s.appendChild(document.createTextNode(
      ".dzpi{position:relative;display:block;flex:0 0 auto;width:48px;height:27px;overflow:hidden;background:#0a0a0c;pointer-events:none}"+
      ".dzsvo-mtete>.dzpi{width:40px;height:22.5px;margin-right:3px}"+
      ".dzpi img,.dzpi video{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;display:block}"+
      ".dzpi video{opacity:0;transition:opacity .15s}.dzpi[data-joue] video{opacity:1}"+
      "@media (prefers-reduced-motion: reduce){.dzpi video{display:none}}"));
    document.head.appendChild(s)}
  function idDe(el){
    var a=el.getAttribute("data-sv-post")||"";
    return a==="maillon"?el.getAttribute("data-preset"):a.indexOf("ajout-")===0?a.slice(6):null}
  function vignette(el){var l=el.querySelectorAll(".dzpi");return l.length?l[0]:null}
  function jouer(el){
    var f=vignette(el);if(!f||reduit())return;
    var v=f.querySelector("video");if(!v)return;
    if(!v.getAttribute("src")){v.setAttribute("src",BASE+f.getAttribute("data-preset")+".webm")}
    f.setAttribute("data-joue","1");
    try{var p=v.play();if(p&&p.catch)p.catch(function(){})}catch(_e){}}
  function arreter(el){
    var f=vignette(el);if(!f)return;
    var v=f.querySelector("video");f.removeAttribute("data-joue");
    if(!v)return;try{v.pause();v.currentTime=0}catch(_e){}}
  function remplir(f,id){
    f.setAttribute("data-preset",id);
    var img=f.querySelector("img"),v=f.querySelector("video");
    img.setAttribute("src",BASE+(PRESETS[id].affiche||id+".webp"));
    if(v){try{v.pause()}catch(_e){}v.removeAttribute("src");f.removeAttribute("data-joue")}}
  function decorer(el){
    var id=idDe(el),f=vignette(el);
    if(!PRESETS||!id||!PRESETS[id])return;
    if(f){if(f.getAttribute("data-preset")!==id)remplir(f,id);return}
    var hote=el.getAttribute("data-sv-post")==="maillon"?(el.querySelector(".dzsvo-mtete")||el):el;
    f=document.createElement("span");f.className="dzpi";f.setAttribute("aria-hidden","true");
    var img=document.createElement("img");img.setAttribute("alt","");img.setAttribute("decoding","async");img.setAttribute("draggable","false");
    var v=document.createElement("video");v.muted=!0;v.loop=!0;v.setAttribute("muted","");v.setAttribute("loop","");
    v.setAttribute("playsinline","");v.setAttribute("preload","none");v.setAttribute("tabindex","-1");
    f.appendChild(img);f.appendChild(v);remplir(f,id);
    hote.insertBefore(f,hote.firstChild);
    if(!el.__dzpi){el.__dzpi=1;
      el.addEventListener("mouseenter",function(){jouer(el)});
      el.addEventListener("focusin",function(){jouer(el)});
      el.addEventListener("mouseleave",function(){arreter(el)});
      el.addEventListener("focusout",function(){arreter(el)})}}
  function balayer(){
    attente=0;if(!PRESETS)return;
    var l=document.querySelectorAll(CIBLES);for(var i=0;i<l.length;i++)decorer(l[i])}
  function bientot(){if(!attente){attente=1;setTimeout(balayer,60)}}
  function demarrer(){
    style();
    fetch(BASE+"index.json").then(function(r){return r.ok?r.json():null}).then(function(d){
      PRESETS=(d&&d.presets)||{};balayer();
      try{new MutationObserver(bientot).observe(document.body,{childList:!0,subtree:!0,attributes:!0,attributeFilter:["data-preset"]})}catch(_e){}
    }).catch(function(){})}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",demarrer);else demarrer();
})();
