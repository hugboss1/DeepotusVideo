/* Illustrations des gestes VFX IA (t275, lot « Menus : Son & VFX », 22/10/2026).
   Les cartes du rail VFX IA de Son & VFX (button[data-dzvfxia="<geste>"], couche son-vfx-montage) reçoivent l'affiche
   de leur geste, en tête de carte ; l'animation (WebM de 4 s en boucle) n'est chargée qu'au premier survol ou focus,
   joue tant que la carte est survolée ou a le focus, puis revient à l'affiche. Avec prefers-reduced-motion, l'affiche
   reste fixe. Les fichiers sont des statiques rendus au développement (scripts/sonvfx_illustrations.py) ; le
   manifeste /sonvfx/illus/index.json dit quels gestes en ont une.
   Script posé à côté du bundle, sans le toucher : un MutationObserver décore les cartes quand l'écran les rend. Décor
   seulement (aria-hidden), aucun texte. Angles vifs, comme tout Son & VFX. */
(function(){
  "use strict";
  var BASE="/sonvfx/illus/",GESTES=null,attente=0;
  function reduit(){try{return !!(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches)}catch(_e){return !1}}
  function style(){
    if(!document.head||document.getElementById("dz-vfx-illus-css"))return;
    var s=document.createElement("style");s.id="dz-vfx-illus-css";
    s.appendChild(document.createTextNode(
      ".dzvi{position:relative;display:block;width:100%;aspect-ratio:16/9;margin:0 0 8px;overflow:hidden;background:#0a0a0c;pointer-events:none}"+
      ".dzvi img,.dzvi video{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;display:block}"+
      ".dzvi video{opacity:0;transition:opacity .15s}.dzvi[data-joue] video{opacity:1}"+
      "@media (prefers-reduced-motion: reduce){.dzvi video{display:none}}"));
    document.head.appendChild(s)}
  function jouer(f){
    if(reduit())return;
    var v=f.querySelector("video");if(!v)return;
    if(!v.getAttribute("src")){v.setAttribute("src",BASE+f.getAttribute("data-geste")+".webm")}
    f.setAttribute("data-joue","1");
    try{var p=v.play();if(p&&p.catch)p.catch(function(){})}catch(_e){}}
  function arreter(f){
    var v=f.querySelector("video");f.removeAttribute("data-joue");
    if(!v)return;try{v.pause();v.currentTime=0}catch(_e){}}
  function decorer(carte){
    var id=carte.getAttribute("data-dzvfxia");
    if(!GESTES||!id||!GESTES[id]||carte.querySelector(".dzvi"))return;
    var f=document.createElement("span");f.className="dzvi";f.setAttribute("aria-hidden","true");f.setAttribute("data-geste",id);
    var img=document.createElement("img");img.setAttribute("src",BASE+(GESTES[id].affiche||id+".webp"));img.setAttribute("alt","");
    img.setAttribute("decoding","async");img.setAttribute("draggable","false");
    var v=document.createElement("video");v.muted=!0;v.loop=!0;v.setAttribute("muted","");v.setAttribute("loop","");
    v.setAttribute("playsinline","");v.setAttribute("preload","none");v.setAttribute("tabindex","-1");
    f.appendChild(img);f.appendChild(v);
    carte.insertBefore(f,carte.firstChild);
    carte.addEventListener("mouseenter",function(){jouer(f)});
    carte.addEventListener("focusin",function(){jouer(f)});
    carte.addEventListener("mouseleave",function(){arreter(f)});
    carte.addEventListener("focusout",function(){arreter(f)})}
  function balayer(){
    attente=0;if(!GESTES)return;
    var l=document.querySelectorAll("[data-dzvfxia]");for(var i=0;i<l.length;i++)decorer(l[i])}
  function bientot(){if(!attente){attente=1;setTimeout(balayer,60)}}
  function demarrer(){
    style();
    fetch(BASE+"index.json").then(function(r){return r.ok?r.json():null}).then(function(d){
      GESTES=(d&&d.gestes)||{};balayer();
      try{new MutationObserver(bientot).observe(document.body,{childList:!0,subtree:!0})}catch(_e){}
    }).catch(function(){})}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",demarrer);else demarrer();
})();
