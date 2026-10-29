/* dz-lecteur.js — le LECTEUR audio/vidéo commun, à la charte (t372, 29/10/2026, lot A « Finitions esthétiques »,
   plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md). SOURCE :
   frontend/shared/dz-lecteur.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-lecteur.js, servie à
   /shared/dz-lecteur.js. Bancs : frontend/shared/qa/lecteur.test.mjs (comportement, DOM simulé) et
   backend/tests/test_lecteur_ecran.py (branchements, copie, jetons, textes).

   Ce qu'il fait : à l'exécution, tout <audio controls> / <video controls> de la page perd ses contrôles natifs (blancs,
   arrondis) au profit d'une barre à la charte — fond --bg-panel, angles vifs (var(--radius)), bouton lecture --amber,
   temps en mono, progression et volume en curseur façon fader (décision D1 ; t373 unifiera tous les curseurs).
   Le média reste EN PLACE : on lui retire seulement l'attribut controls et la barre se pose JUSTE APRÈS lui. React
   garde donc son nœud, ses ref et ses évènements (onLoadedMetadata, onError…), et le bundle prébâti n'est pas touché
   (aucun maillon) : ses 16 lecteurs natifs relevés (Chapitres › aperçu de voix, Quick et Studio › voix, Son & VFX ›
   pistes et atelier, Bibliothèque, Planificateur, Studio, Montage) passent par l'observateur ci-dessous, comme ceux des
   labs (Atelier, Avatar live) et des tutoriels. Audio : barre dans le flux, à la place du lecteur natif. Vidéo : barre
   en surimpression du bas de l'image (le parent statique devient le repère), visible en pause, au survol ou au focus.
   Un média marqué data-dz-lecteur="natif" garde ses contrôles. Textes : clés lecteur.* (frontend/shared/i18n/lecteur.json). */
(function () {
  "use strict";
  if (window.__dzLecteur) return;

  var NS = "http://www.w3.org/2000/svg";
  var SPRITE = "/shared/icons/dz-icons.svg#";
  var ICONES = { lire: "dz-media-lecture", pause: "dz-media-pause", son: "dz-media-audio", muet: "dz-media-muet",
                 plein: "dz-action-ajuster-vue" };
  var PAS = 1000;          // résolution du curseur de position
  var HAUTEUR = 32;        // hauteur de la barre (px), reprise par la feuille
  var SELECTEUR = "audio[controls],video[controls]";
  var suivis = [];

  function T(k, p) { try { if (typeof window.dzT === "function") return window.dzT(k, p); } catch (e) { /* repli */ } return k; }

  function temps(s) {
    s = Number(s);
    if (!isFinite(s) || s < 0) return "--:--";
    s = Math.floor(s);
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    var xx = (x < 10 ? "0" : "") + x;
    return h ? h + ":" + (m < 10 ? "0" : "") + m + ":" + xx : m + ":" + xx;
  }

  /* ── feuille : jetons de dz-charte.css et jetons de base seulement (aucun rayon, aucune couleur en dur) ── */
  var CSS = [
    ".dz-lecteur{display:flex;align-items:center;gap:var(--pad-2);box-sizing:border-box;width:100%;height:" + HAUTEUR + "px;",
    "margin:0;padding:0 var(--pad-2) 0 var(--pad-1);background:var(--bg-panel);border:1px solid var(--stroke);",
    "border-radius:var(--radius);color:var(--fg-2);font-family:var(--font-ui);font-size:var(--fs-2);line-height:1}",
    ".dz-lecteur[hidden]{display:none}",
    ".dz-lecteur button{appearance:none;display:inline-flex;align-items:center;justify-content:center;flex:none;",
    "width:24px;height:24px;margin:0;padding:0;border:1px solid var(--stroke);border-radius:var(--radius);",
    "background:transparent;color:var(--fg-2);cursor:pointer}",
    ".dz-lecteur button:hover{color:var(--fg-1);border-color:var(--fg-4)}",
    ".dz-lecteur button:disabled{opacity:.4;cursor:default}",
    ".dz-lecteur button:focus-visible,.dz-lecteur input:focus-visible{outline:1px solid var(--amber);outline-offset:1px}",
    ".dz-lecteur button[data-dz-lecteur=lire]{background:var(--amber);border-color:var(--amber);color:var(--fg-on-accent)}",
    ".dz-lecteur button[data-dz-lecteur=lire]:hover{color:var(--fg-on-accent);filter:brightness(1.12)}",
    ".dz-lecteur .dzi{width:14px;height:14px}",
    ".dz-lecteur-tps{flex:none;font-family:var(--font-mono);font-size:var(--fs-2);color:var(--fg-3);",
    "font-variant-numeric:tabular-nums;letter-spacing:0}",
    ".dz-lecteur-tps[data-dz-lecteur=temps]{color:var(--fg-1)}",
    /* curseurs façon fader (D1) : rainure fine encastrée, rempli --amber discret, bouton rectangulaire strié */
    ".dz-lecteur input[type=range]{-webkit-appearance:none;appearance:none;flex:1 1 auto;min-width:40px;height:18px;",
    "margin:0;padding:0;background:transparent;cursor:pointer}",
    ".dz-lecteur input[data-dz-lecteur=volume]{flex:0 0 56px;min-width:56px}",
    ".dz-lecteur[data-etroit=\"1\"] input[data-dz-lecteur=volume]{display:none}",
    ".dz-lecteur input[type=range]::-webkit-slider-runnable-track{height:3px;border:0;border-radius:var(--radius);",
    "background:linear-gradient(to right,color-mix(in srgb,var(--amber) 72%,transparent) var(--dz-lecteur-pos,0%),",
    "var(--bg-base) var(--dz-lecteur-pos,0%));box-shadow:inset 0 0 0 1px var(--stroke)}",
    ".dz-lecteur input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:8px;height:14px;",
    "margin-top:-5.5px;border:1px solid var(--stroke-strong,var(--stroke));border-radius:var(--radius);",
    "background:repeating-linear-gradient(to bottom,var(--fg-3) 0 1px,var(--bg-panel) 1px 3px)}",
    ".dz-lecteur input[type=range]:hover::-webkit-slider-thumb,.dz-lecteur input[type=range]:focus-visible::-webkit-slider-thumb",
    "{border-color:var(--amber)}",
    /* vidéo : surimpression du bas de l'image */
    ".dz-lecteur[data-dz-genre=video]{position:absolute;z-index:2;width:auto;border-width:1px 0 0;",
    "background:color-mix(in srgb,var(--bg-panel) 88%,transparent);transition:opacity .15s}",
    ".dz-lecteur[data-dz-genre=video][data-visible=\"0\"]{opacity:0;pointer-events:none}"
  ].join("");

  function feuille() {
    if (!document.head || document.getElementById("dz-lecteur-css")) return;
    var st = document.createElement("style");
    st.setAttribute("id", "dz-lecteur-css");
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function el(tag, attrs) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  function icone(id) {
    var s = document.createElementNS(NS, "svg");
    s.setAttribute("class", "dzi dzi--16");
    s.setAttribute("aria-hidden", "true");
    s.setAttribute("focusable", "false");
    var u = document.createElementNS(NS, "use");
    u.setAttribute("href", SPRITE + id);
    s.appendChild(u);
    return { svg: s, use: u };
  }

  function bouton(marque, id, libelle) {
    var b = el("button", { type: "button", "data-dz-lecteur": marque, "aria-label": libelle, title: libelle });
    var ic = icone(id);
    b.appendChild(ic.svg);
    b.__use = ic.use;
    return b;
  }

  function estMedia(n) {
    var t = n && n.nodeType === 1 && String(n.tagName).toLowerCase();
    return t === "audio" || t === "video";
  }

  /* ── un média amélioré ─────────────────────────────────────────────────────────────────────────────────── */
  function ameliorer(media) {
    if (!estMedia(media)) return null;
    if (media.__dzLecteur) return media.__dzLecteur.barre;
    if (media.getAttribute("data-dz-lecteur") === "natif") return null;
    var parent = media.parentNode;
    if (!parent) return null;
    feuille();
    var video = String(media.tagName).toLowerCase() === "video";
    var L = { media: media, barre: null, glisse: false, survol: false, focus: false, plein: false, ecoute: [], ro: null };

    var barre = L.barre = el("div", { "class": "dz-lecteur", "data-dz-lecteur": "barre", "data-dz-genre": video ? "video" : "audio",
                                      role: "group", "aria-label": T("lecteur.barre.groupe"), "data-etat": "pause" });
    var lire = bouton("lire", ICONES.lire, T("lecteur.action.lire"));
    var tps = el("span", { "class": "dz-lecteur-tps", "data-dz-lecteur": "temps", "aria-hidden": "true" });
    var pos = el("input", { type: "range", min: "0", max: String(PAS), step: "1", value: "0", "data-dz-lecteur": "position",
                            "aria-label": T("lecteur.curseur.position") });
    var dur = el("span", { "class": "dz-lecteur-tps", "data-dz-lecteur": "duree", "aria-hidden": "true" });
    var son = bouton("son", ICONES.son, T("lecteur.action.couper_son"));
    var vol = el("input", { type: "range", min: "0", max: "100", step: "1", value: "100", "data-dz-lecteur": "volume",
                            "aria-label": T("lecteur.curseur.volume") });
    pos.value = "0"; vol.value = "100";
    tps.textContent = temps(0); dur.textContent = temps(NaN);
    [lire, tps, pos, dur, son, vol].forEach(function (x) { barre.appendChild(x); });
    var plein = null;
    if (video) {
      plein = bouton("plein-ecran", ICONES.plein, T("lecteur.action.plein_ecran"));
      barre.appendChild(plein);
    } else {
      if (media.style && media.style.width) barre.style.width = media.style.width;
      if (media.style && media.style.maxWidth) barre.style.maxWidth = media.style.maxWidth;
    }

    function etiqueter(b, id, libelle) {
      b.__use.setAttribute("href", SPRITE + id);
      b.setAttribute("aria-label", libelle);
      b.setAttribute("title", libelle);
    }
    function etat() {
      if (barre.getAttribute("data-etat") === "erreur") return;
      var joue = !media.paused && !media.ended;
      barre.setAttribute("data-etat", joue ? "lecture" : "pause");
      etiqueter(lire, joue ? ICONES.pause : ICONES.lire, T(joue ? "lecteur.action.pause" : "lecteur.action.lire"));
      voir();
    }
    function avancer() {
      var d = media.duration, t = media.currentTime || 0;
      tps.textContent = temps(t);
      dur.textContent = temps(d);
      var ok = isFinite(d) && d > 0;
      if (!L.glisse) pos.value = String(ok ? Math.round(Math.min(1, t / d) * PAS) : 0);
      var pct = ok ? Math.round(Number(pos.value) / PAS * 1000) / 10 : 0;
      pos.style.setProperty("--dz-lecteur-pos", pct + "%");
      pos.setAttribute("aria-valuetext", T("lecteur.curseur.position_valeur", { t: temps(t), d: temps(d) }));
      if (video) placer();
    }
    function niveau() {
      var muet = media.muted || media.volume === 0;
      etiqueter(son, muet ? ICONES.muet : ICONES.son, T(muet ? "lecteur.action.retablir_son" : "lecteur.action.couper_son"));
      vol.value = String(Math.round((media.muted ? 0 : media.volume) * 100));
      vol.style.setProperty("--dz-lecteur-pos", vol.value + "%");
    }
    function erreur() {
      barre.setAttribute("data-etat", "erreur");
      barre.setAttribute("title", T("lecteur.etat.erreur"));
      lire.setAttribute("disabled", "");
      dur.textContent = temps(NaN);
      if (video) placer();
    }
    function reprise() {
      if (barre.getAttribute("data-etat") !== "erreur") return;
      barre.removeAttribute("title");
      lire.removeAttribute("disabled");
      barre.setAttribute("data-etat", "pause");
      etat();
    }
    function voir() {
      if (!video) return;
      var joue = !media.paused && !media.ended;
      barre.setAttribute("data-visible", !joue || L.survol || L.focus ? "1" : "0");
    }
    function placer() {
      if (!media.isConnected || !media.offsetParent || (media.style && media.style.display === "none")) { barre.hidden = true; return; }
      barre.hidden = false;
      barre.style.left = media.offsetLeft + "px";
      barre.style.top = (media.offsetTop + media.offsetHeight - HAUTEUR) + "px";
      barre.style.width = media.offsetWidth + "px";
      barre.setAttribute("data-etroit", media.offsetWidth < 280 ? "1" : "0");
    }
    function basculer() {
      if (barre.getAttribute("data-etat") === "erreur") return;
      if (media.paused || media.ended) {
        var p = media.play();
        if (p && typeof p.catch === "function") p.catch(function () { /* lecture refusée : l'état reste « pause » */ });
      } else media.pause();
    }
    function ecouter(cible, type, f) { cible.addEventListener(type, f); L.ecoute.push([cible, type, f]); }

    ecouter(media, "play", etat); ecouter(media, "playing", etat); ecouter(media, "pause", etat); ecouter(media, "ended", etat);
    ecouter(media, "timeupdate", avancer); ecouter(media, "durationchange", avancer); ecouter(media, "loadedmetadata", avancer);
    ecouter(media, "seeked", avancer); ecouter(media, "volumechange", niveau);
    ecouter(media, "error", erreur); ecouter(media, "loadstart", reprise); ecouter(media, "emptied", reprise);
    lire.addEventListener("click", basculer);
    pos.addEventListener("pointerdown", function () { L.glisse = true; });
    pos.addEventListener("input", function () {
      var d = media.duration;
      if (isFinite(d) && d > 0) media.currentTime = Number(pos.value) / PAS * d;
      var g = L.glisse; L.glisse = true; avancer(); L.glisse = g;
    });
    pos.addEventListener("change", function () { L.glisse = false; });
    son.addEventListener("click", function () { media.muted = !media.muted; if (!media.muted && media.volume === 0) media.volume = 1; });
    vol.addEventListener("input", function () { media.volume = Number(vol.value) / 100; media.muted = false; niveau(); });

    if (video) {
      ecouter(media, "click", basculer);
      ecouter(media, "pointerenter", function () { L.survol = true; voir(); placer(); });
      ecouter(media, "pointerleave", function () { L.survol = false; voir(); });
      barre.addEventListener("pointerenter", function () { L.survol = true; voir(); });
      barre.addEventListener("pointerleave", function () { L.survol = false; voir(); });
      barre.addEventListener("focusin", function () { L.focus = true; voir(); });
      barre.addEventListener("focusout", function () { L.focus = false; voir(); });
      plein.addEventListener("click", function () {
        if (typeof media.requestFullscreen !== "function") return;
        L.plein = true;
        media.setAttribute("controls", "");      // le plein écran garde des contrôles : ceux du navigateur, le temps qu'il dure
        var p = media.requestFullscreen();
        if (p && typeof p.catch === "function") p.catch(function () { sortiePleinEcran(media); });
      });
      try {
        var ps = window.getComputedStyle ? window.getComputedStyle(parent).position : "";
        if (ps === "static") parent.style.position = "relative";
      } catch (e) { /* parent sans style calculé */ }
      if (typeof window.ResizeObserver === "function") {
        L.ro = new window.ResizeObserver(function () { placer(); });
        L.ro.observe(media);
      }
    }

    media.__dzLecteur = L;
    L.detruire = function () {
      L.ecoute.forEach(function (x) { x[0].removeEventListener(x[1], x[2]); });
      L.ecoute = [];
      if (L.ro) L.ro.disconnect();
      if (barre.parentNode) barre.parentNode.removeChild(barre);
      delete media.__dzLecteur;
    };
    suivis.push(L);
    media.removeAttribute("controls");
    media.setAttribute("data-dz-lecteur", "ameliore");
    parent.insertBefore(barre, media.nextSibling);
    if (media.error) erreur();
    etat(); avancer(); niveau();
    if (video) placer();
    return barre;
  }

  function sortiePleinEcran(media) {
    var L = media && media.__dzLecteur;
    if (!L || !L.plein) return;
    L.plein = false;
    media.removeAttribute("controls");
  }

  function traiter(m) {
    if (!estMedia(m)) return;
    var L = m.__dzLecteur;
    if (L) { if (!L.plein && m.hasAttribute("controls")) m.removeAttribute("controls"); return; }
    if (m.hasAttribute("controls")) ameliorer(m);
  }

  function balayer(racine) {
    if (!racine || racine.nodeType !== 1) return;
    traiter(racine);
    if (typeof racine.querySelectorAll === "function") {
      var l = racine.querySelectorAll(SELECTEUR);
      for (var i = 0; i < l.length; i++) traiter(l[i]);
    }
  }

  function nettoyer() {
    suivis = suivis.filter(function (L) {
      if (L.media.isConnected) return true;
      L.detruire();
      return false;
    });
  }

  function observer() {
    if (typeof window.MutationObserver !== "function" || !document.documentElement) return;
    var mo = new window.MutationObserver(function (muts) {
      var retrait = false;
      for (var i = 0; i < muts.length; i++) {
        var m = muts[i];
        if (m.type === "attributes") { traiter(m.target); continue; }
        for (var j = 0; j < m.addedNodes.length; j++) balayer(m.addedNodes[j]);
        if (m.removedNodes.length) retrait = true;
      }
      if (retrait) nettoyer();
    });
    mo.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["controls"] });
    document.addEventListener("fullscreenchange", function () {
      if (document.fullscreenElement) return;
      suivis.forEach(function (L) { sortiePleinEcran(L.media); });
    });
    if (document.body) balayer(document.body);
  }

  window.__dzLecteur = { ameliorer: ameliorer, balayer: balayer, temps: temps, _sortiePleinEcran: sortiePleinEcran };
  observer();
})();
