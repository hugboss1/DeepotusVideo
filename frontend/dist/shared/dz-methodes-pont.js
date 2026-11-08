/* dz-methodes-pont.js — le bouton « Méthodes » des écrans de l'application (t435b, lot M2 « Méthodes », 08/11/2026 ;
   conception docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §5 : « dans chaque écran hôte,
   un bouton Méthodes ouvre les fiches de cet écran »).

   Chargé par frontend/dist/index.html (script classique, après le bundle). AUCUN maillon de bundle : la vue courante
   est celle que la coque range dans localStorage « dz_view » (relue toutes les secondes) ; sur un écran qui héberge
   des méthodes (ECRANS), une pastille discrète en bas à droite. Un clic :
     1. ouvre l'écran Méthodes par « deepotus:navigate » {view: "methodes"} (le gestionnaire de la coque) ;
     2. puis pose le filtre dans l'iframe /methodes/ (location.replace(?ecran=<id>)) dès qu'elle existe — même
        origine ; React ne réécrit pas `src`, la prop n'a pas changé.
   Textes : dzT("methodes.pont.…"). Rien n'est envoyé au serveur. */
(function () {
  "use strict";
  if (window.__dzMethodesPont) return;

  // vue de la coque -> écran du catalogue des méthodes (ids de knowledge/methodes.json « ecrans »)
  var ECRANS = { quick: "quick", studio: "studio", episodes: "episodes", sonvfx: "sonvfx", montage: "montage",
                 templates: "templates", library: "library", photolab: "photolab", vectorlab: "vectorlab",
                 avatarlive: "avatarlive", scheduler: "scheduler", news: "news" };
  var PERIODE_MS = 1000;
  var bouton = null, vue = "";

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function vueCourante() {
    try { return String(window.localStorage.getItem("dz_view") || ""); } catch (e) { return ""; }
  }

  function poserFiltre(ecran, essais) {
    var f = document.querySelector('iframe[src^="/methodes/"]');
    if (f && f.contentWindow) {
      try { f.contentWindow.location.replace("/methodes/?ecran=" + encodeURIComponent(ecran)); return true; }
      catch (e) { return false; }
    }
    if (essais > 0) setTimeout(function () { poserFiltre(ecran, essais - 1); }, 150);
    return false;
  }

  function ouvrir() {
    var ecran = ECRANS[vue];
    if (!ecran) return;
    window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: "methodes" } }));
    setTimeout(function () { poserFiltre(ecran, 20); }, 60);
  }

  function creer() {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "dz-methodes-pont";
    b.setAttribute("data-dz-methodes-pont", "");
    b.style.cssText = "position:fixed;right:16px;bottom:64px;z-index:40;height:28px;padding:0 12px;display:none;"
      + "align-items:center;gap:6px;border:1px solid var(--accent,#d4a72c);"
      + "background:var(--bg-panel,#14181d);color:var(--accent,#d4a72c);font:12px var(--f-ui,system-ui);cursor:pointer;";
    if (typeof window.dzIcone === "function") {
      var i = document.createElement("span");
      i.setAttribute("aria-hidden", "true");
      i.style.cssText = "display:inline-flex;line-height:0";
      i.innerHTML = window.dzIcone("dz-action-lancer-recette", { taille: 14 });
      b.appendChild(i);
    }
    var t = document.createElement("span");
    b.appendChild(t);
    b.addEventListener("click", ouvrir);
    document.body.appendChild(b);
    return b;
  }

  function tic() {
    vue = vueCourante();
    var ecran = ECRANS[vue];
    if (!bouton && document.body) bouton = creer();
    if (!bouton) return;
    bouton.style.display = ecran ? "inline-flex" : "none";
    if (ecran) {
      var txt = T("methodes.pont.bouton");
      bouton.lastChild.textContent = txt;
      bouton.title = T("methodes.pont.titre");
    }
  }

  window.__dzMethodesPont = { ECRANS: ECRANS, tic: tic, ouvrir: ouvrir, poserFiltre: poserFiltre };
  tic();
  setInterval(tic, PERIODE_MS);
})();
