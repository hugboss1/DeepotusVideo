/* dz-champ-ia.js — la couche des CHAMPS IA de toute l'application (retours
   du 26/09, tâche 8, 27/09/2026). SOURCE : frontend/shared/dz-champ-ia.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-champ-ia.js, servie à
   /shared/dz-champ-ia.js et chargée par une balise dans frontend/dist/index.html
   (la SPA) et dans les pages à part (Atelier, Cardforge, Material Forge,
   Spritelab, Vectorlab). Le banc backend/tests/test_champ_ia.py refuse toute
   dérive entre les deux copies. Aucun patch du bundle : la couche injecte son
   propre <style>.

   MARQUAGE. Une table de règles déclarative (REGLES) désigne les champs de
   saisie des GÉNÉRATIONS MÉDIA (périmètre validé le 26/09, conception §G) par
   sélecteur, ou par libellé pour le Prompt et le Script (HeyGen) du Quick
   (composant `ie` du bundle : champ → div → div dont le premier enfant est le
   bouton-libellé). Un MutationObserver marque les champs ajoutés. Jamais sous
   `.dz-studio-grid` (l'éditeur de nœuds du Studio) ni sur les exclusions
   (EXCLUS : voix TTS, consignes LLM, textes narrés). Un `data-dz-ia` posé à la
   main est honoré partout.

   HABILLAGE (variante B de la maquette) : liseré conic-gradient violet
   #8b5cf6 → bleu #3b82f6 → orange #f97316 et halo faible au repos, FIXES ;
   au :focus-within, rotation (6 s) et reflet holographique (screen, 5,5 s)
   avec une trame fine ; prefers-reduced-motion fige tout. Le champ n'est
   JAMAIS déplacé : un champ React re-parenté dans un conteneur étranger fait
   lever `removeChild`/`insertBefore` à React au prochain rendu conditionnel.
   Le liseré est peint PAR LE CHAMP LUI-MÊME (couches de fond : son propre fond
   en padding-box au-dessus du dégradé en border-box, bordure transparente de
   même épaisseur) : ni sa taille ni sa place ne changent. La BARRE (badge
   « IA » + emplacement `data-dzia-slot="modele"` qui porte la PASTILLE DE
   MODÈLE (T9, voir plus bas) et emplacement `"micro"` (T10)) est un frère ABSOLU posé juste après le champ, recalé sur son coin
   droit ; une réserve de padding (champs border-box seulement) empêche le
   texte de passer dessous. Le parent statique devient `position:relative`
   seulement s'il n'a aucun descendant absolu (sinon la barre se recale au
   défilement).

   DICTÉE (T10, voir plus bas) : l'emplacement `"micro"` porte UN bouton dont
   on change l'état (repos → écoute/prise « ■ » → estimation → accord →
   envoi). Voie 1 : SpeechRecognition du navigateur. Voie 2 (absente, ou
   erreur network / service-not-allowed) : MediaRecorder, POST
   /api/dictation/estimate, dialogue « Transcrire N s par X ≈ Y $ ? », et
   SEULEMENT sur Oui POST /api/dictation avec max_usd = le montant affiché. */
(function () {
  "use strict";
  var W = window, D = document;
  if (W.DzChampIA) return;

  var VERSION = "1.2.0";
  var GENRES = ["video", "image", "anim", "sfx", "musique", "3d"];

  /* La table. `page` borne une règle à une page à part (préfixe du chemin). */
  var REGLES = [
    { id: "quick-prompt", vue: "Quick", libelle: "Prompt", mode: "egal", genre: "video" },
    { id: "quick-script", vue: "Quick (HeyGen)", libelle: "Script (", mode: "debut", genre: "video" },
    { id: "quick-motion", vue: "Quick (HeyGen)", sel: 'textarea[placeholder^="ex: sourit"]', genre: "video" },
    { id: "chapitres-illus", vue: "Chapitres", sel: "input[placeholder=\"Prompt d'illustration…\"]", genre: "image" },
    { id: "son-paroles", vue: "Son & VFX", sel: 'textarea[aria-label="Paroles"]', genre: "musique" },
    { id: "son-musique", vue: "Son & VFX", sel: "textarea.svm-musicprompt", genre: "musique" },
    { id: "son-sfx", vue: "Son & VFX", sel: "input.svm-sfxprompt", genre: "sfx" },
    { id: "montage-sons", vue: "Montage (Sons)", sel: "textarea.svx-gprompt", genre: "sfx" },
    { id: "templates-ia", vue: "Templates", sel: '[placeholder^="AI prompt"]', genre: "image" },
    { id: "library-image", vue: "Library", sel: '[placeholder^="Describe an image to create"]', genre: "image" },
    { id: "game-assets-3d", vue: "Game Assets", sel: '[placeholder^="e.g. a knight character"]', genre: "3d" },
    { id: "atelier-style", vue: "Atelier", page: "/atelier", sel: "#globalStyle", genre: "image" },
    { id: "atelier-da", vue: "Atelier", page: "/atelier", sel: "#daStyle", genre: "image" },
    { id: "atelier-entite", vue: "Atelier", page: "/atelier", sel: ".entity-desc", genre: "image" },
    { id: "atelier-entite-style", vue: "Atelier", page: "/atelier", sel: ".entity-style", genre: "image" },
    { id: "atelier-plan", vue: "Atelier", page: "/atelier", sel: ".shot-action", genre: "image" },
    { id: "spritelab-anim", vue: "Spritelab", page: "/spritelab", sel: "#animPrompt", genre: "anim" },
    { id: "materialforge", vue: "Material Forge", page: "/materialforge", sel: "#prompt", genre: "image" },
    { id: "cardforge-face", vue: "Cardforge", page: "/cardforge", sel: "#cf-face-prompt", genre: "image" },
    { id: "cardforge-decor", vue: "Cardforge", page: "/cardforge", sel: "textarea.cff-prompt", genre: "image" },
    { id: "cardforge-texture", vue: "Cardforge", page: "/cardforge", sel: 'input[data-field="texture_prompt"]', genre: "3d" },
    { id: "vectorlab-ia", vue: "Vectorlab", page: "/vectorlab", sel: "#iaTexte", genre: "image" },
    { id: "vectorlab-vitrail", vue: "Vectorlab", page: "/vectorlab", sel: "#vitIaPrompt", genre: "image" }
  ];
  /* Zones jamais marquées (graphes de nœuds) et exclusions nommées (témoins
     du banc) : elles priment sur la table, pas sur un data-dz-ia manuel. */
  var ZONES = [".dz-studio-grid"];
  var EXCLUS = [
    "[data-dzquickvoice] textarea",
    "textarea.svm-nbtext",
    "textarea.dzm-actext",
    "input.dzm-acpersona",
    "#script",
    ".scene-fountain",
    '[placeholder^="Narrated scene text"]',
    '[placeholder^="Dans les profondeurs"]',
    '[placeholder^="e.g. fits the $DEEPOTUS"]',
    '[placeholder^="e.g. Week around the $DEEPOTUS"]'
  ];

  /* l'icône du micro, dessinée par masque (couleur = currentColor) */
  var MICRO_SVG = "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>" +
    "<path d='M12 15a3.5 3.5 0 0 0 3.5-3.5v-6a3.5 3.5 0 0 0-7 0v6A3.5 3.5 0 0 0 12 15zm6-3.5h-2a4 4 0 0 1-8 0H6a6 6 0 0 0 5 5.9V21h2v-3.6a6 6 0 0 0 5-5.9z'/></svg>\")";
  var CSS = [
    "@property --dzia-ang{syntax:'<angle>';inherits:false;initial-value:0deg}",
    "@property --dzia-holo{syntax:'<number>';inherits:false;initial-value:0}",
    /* repos : liseré fixe, halo faible, reflet éteint (--dzia-holo 0), animations en pause */
    ".dzia-lis.dzia-lis{border-color:transparent!important;" +
      "background-image:" +
        "linear-gradient(115deg,transparent 30%,rgba(139,92,246,calc(.10*var(--dzia-holo,0))) 42%,rgba(59,130,246,calc(.14*var(--dzia-holo,0))) 50%,rgba(249,115,22,calc(.10*var(--dzia-holo,0))) 58%,transparent 70%)," +
        "repeating-linear-gradient(0deg,rgba(255,255,255,.018) 0 1px,transparent 1px 3px)," +
        "linear-gradient(var(--dzia-fond,#16181d),var(--dzia-fond,#16181d))," +
        "linear-gradient(var(--dzia-sous,#16181d),var(--dzia-sous,#16181d))," +
        "conic-gradient(from var(--dzia-ang,0deg),#8b5cf6,#3b82f6,#f97316,#8b5cf6)!important;" +
      "background-origin:padding-box,padding-box,padding-box,padding-box,border-box!important;" +
      "background-clip:padding-box,padding-box,padding-box,padding-box,border-box!important;" +
      "background-size:250% 100%,auto,auto,auto,auto!important;" +
      "background-repeat:no-repeat,repeat,no-repeat,no-repeat,no-repeat!important;" +
      "background-blend-mode:screen,normal,normal,normal,normal!important;" +
      "box-shadow:0 0 10px -3px rgba(139,92,246,.30),0 0 12px -5px rgba(249,115,22,.24)!important;" +
      "animation:dzia-tour 6s linear infinite,dzia-balai 5.5s ease-in-out infinite;" +
      "animation-play-state:paused,paused;" +
      "transition:box-shadow .3s ease,--dzia-holo .4s ease}",
    ".dzia-bord.dzia-bord{border-style:solid!important;border-width:1px!important}",
    /* champ sans liseré possible (ni bord, ni parent bordé, ni padding à rendre) : halo seul */
    ".dzia-halo.dzia-halo{box-shadow:0 0 10px -3px rgba(139,92,246,.30),0 0 12px -5px rgba(249,115,22,.24)!important;transition:box-shadow .3s ease}",
    ".dzia-halo.dzia-halo:focus-within{box-shadow:0 0 14px -2px rgba(139,92,246,.55),0 0 18px -4px rgba(59,130,246,.42),0 0 16px -5px rgba(249,115,22,.40)!important}",
    /* focus : le liseré tourne, le reflet holographique balaie */
    ".dzia-lis.dzia-lis:focus-within{animation-play-state:running,running;--dzia-holo:1;outline:none;" +
      "box-shadow:0 0 14px -2px rgba(139,92,246,.55),0 0 18px -4px rgba(59,130,246,.42),0 0 16px -5px rgba(249,115,22,.40)!important}",
    /* parent peint (composant `le`) : l'anneau de focus du champ nu ferait un second cadre dedans */
    ".dzia-lis>.dzia-champ:focus,.dzia-lis>.dzia-champ:focus-visible{outline:none!important;box-shadow:none!important}",
    "@keyframes dzia-tour{to{--dzia-ang:360deg}}",
    "@keyframes dzia-balai{0%{background-position:120% 0,0 0,0 0,0 0,0 0}100%{background-position:-120% 0,0 0,0 0,0 0,0 0}}",
    /* la barre : frère absolu, ne capture pas les clics hors de ses boutons */
    ".dzia-barre{position:absolute;left:0;top:0;z-index:3;display:flex;align-items:center;gap:4px;margin:0;padding:0;" +
      "pointer-events:none;line-height:1;white-space:nowrap;box-sizing:border-box}",
    ".dzia-badge{display:inline-block;font:700 9px/1 system-ui,-apple-system,'Segoe UI',sans-serif;letter-spacing:.06em;" +
      "padding:3px 6px;border-radius:999px;background:linear-gradient(90deg,#8b5cf6,#3b82f6,#f97316);color:#fff;" +
      "opacity:.6;transition:opacity .3s ease;user-select:none;pointer-events:auto;cursor:text}",
    ".dzia-champ:focus-within+.dzia-barre .dzia-badge{opacity:1}",
    ".dzia-emp{display:inline-flex;align-items:center;gap:4px;pointer-events:auto}",
    ".dzia-emp:empty{display:none}",
    /* T9 : la pastille de modèle (un seul bouton, grisé par aria-disabled) et sa liste */
    ".dzia-modele{display:inline-flex;align-items:center;gap:3px;max-width:118px;height:18px;margin:0;padding:0 6px 0 7px;" +
      "border-radius:999px;border:1px solid rgba(139,92,246,.55);background:rgba(18,20,26,.92);color:#e5e7eb;" +
      "font:600 10px/1 system-ui,-apple-system,'Segoe UI',sans-serif;cursor:pointer;pointer-events:auto;white-space:nowrap;box-sizing:border-box}",
    ".dzia-modele .dzia-mtxt{overflow:hidden;text-overflow:ellipsis}",
    ".dzia-modele::after{content:'\\25BE';font-size:9px;opacity:.75}",
    ".dzia-modele:hover{border-color:#3b82f6}",
    ".dzia-modele[aria-disabled=true]{cursor:default;opacity:.62;border-color:rgba(148,163,184,.35);border-style:dashed}",
    ".dzia-modele[aria-disabled=true]::after{content:none}",
    /* champ étroit (< 200 px, ex. #vitIaPrompt) : la pastille se réduit à une icône titrée */
    ".dzia-modele.dzia-mini{width:18px;padding:0;justify-content:center}",
    ".dzia-modele.dzia-mini .dzia-mtxt{display:none}",
    ".dzia-modele.dzia-mini::after{content:'\\25C6';font-size:8px}",
    ".dzia-liste{position:fixed;z-index:2147483000;min-width:230px;max-width:360px;max-height:320px;overflow:auto;padding:4px;" +
      "border-radius:10px;background:#15171c;border:1px solid rgba(139,92,246,.5);" +
      "box-shadow:0 12px 32px rgba(0,0,0,.5),0 0 14px -4px rgba(59,130,246,.45);box-sizing:border-box}",
    ".dzia-opt{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;margin:0;padding:6px 8px;border:0;" +
      "border-radius:6px;background:transparent;color:#e5e7eb;font:12px/1.25 system-ui,-apple-system,'Segoe UI',sans-serif;text-align:left;cursor:pointer}",
    ".dzia-opt:hover{background:rgba(59,130,246,.18)}",
    ".dzia-opt[aria-selected=true]{background:rgba(139,92,246,.24);color:#fff}",
    ".dzia-opt[aria-disabled=true]{opacity:.42;cursor:not-allowed;background:transparent}",
    ".dzia-oprix{opacity:.72;font-variant-numeric:tabular-nums;flex-shrink:0}",
    ".dzia-ovide{padding:8px;color:#9ca3af;font:12px system-ui,sans-serif}",
    /* T10 : le micro (un seul bouton dont l'état change), la note d'état, le dialogue maison de repli */
    ".dzia-micro{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;margin:0;padding:0;" +
      "border-radius:999px;border:1px solid rgba(139,92,246,.55);background:rgba(18,20,26,.92);color:#e5e7eb;" +
      "font:700 9px/1 system-ui,-apple-system,'Segoe UI',sans-serif;cursor:pointer;pointer-events:auto;box-sizing:border-box;flex-shrink:0}",
    ".dzia-micro:hover{border-color:#3b82f6}",
    ".dzia-micro[aria-disabled=true]{cursor:default;opacity:.62;border-style:dashed;border-color:rgba(148,163,184,.35)}",
    ".dzia-micro[aria-busy=true]{cursor:progress}",
    ".dzia-mico{display:block;width:8px;height:11px;background:currentColor;" +
      "-webkit-mask:" + MICRO_SVG + " center/contain no-repeat;mask:" + MICRO_SVG + " center/contain no-repeat}",
    ".dzia-ecoute .dzia-micro{border-color:#ef4444;background:#b91c1c;color:#fff;animation:dzia-pouls 1.2s ease-in-out infinite}",
    "@keyframes dzia-pouls{50%{box-shadow:0 0 0 4px rgba(239,68,68,.28)}}",
    ".dzia-note{position:fixed;z-index:2147483000;max-width:360px;padding:5px 9px;border-radius:8px;background:#15171c;" +
      "border:1px solid rgba(139,92,246,.5);color:#e5e7eb;font:11px/1.35 system-ui,-apple-system,'Segoe UI',sans-serif;" +
      "box-shadow:0 8px 22px rgba(0,0,0,.45);pointer-events:none;box-sizing:border-box}",
    ".dzia-dlg{position:fixed;inset:0;z-index:2147483600;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center}",
    ".dzia-dlg-boite{width:420px;max-width:92vw;background:#13171c;border:1px solid #2a3138;color:#e6e9ee;box-shadow:0 18px 50px rgba(0,0,0,.5);" +
      "font:13px/1.45 system-ui,sans-serif}",
    ".dzia-dlg-tete{padding:9px 14px;border-bottom:1px solid #222830;font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#9aa4ae}",
    ".dzia-dlg-corps{padding:14px;white-space:pre-wrap;color:#cfd6e2}",
    ".dzia-dlg-pied{display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid #222830}",
    ".dzia-dlg-pied button{min-width:88px;height:28px;padding:0 12px;background:#1b2028;border:1px solid #2a3138;color:#e6e9ee;cursor:pointer;font:inherit}",
    ".dzia-dlg-pied button[data-role=oui]{background:#2b6fd6;border-color:#2b6fd6;color:#fff}",
    "@media (prefers-reduced-motion:reduce){" +
      ".dzia-lis.dzia-lis,.dzia-lis.dzia-lis:focus-within{animation:none!important;--dzia-ang:200deg;transition:none}" +
      ".dzia-ecoute .dzia-micro{animation:none}" +
      ".dzia-badge{transition:none}}"
  ].join("\n");

  function injecterStyle() {
    if (D.getElementById("dzia-style")) return;
    var s = D.createElement("style");
    s.setAttribute("id", "dzia-style");
    s.textContent = CSS;
    (D.head || D.documentElement).appendChild(s);
  }

  function cs(el) { return W.getComputedStyle(el); }
  function correspond(el, sel) { try { return el.matches(sel); } catch (e) { return false; } }
  function dansZone(el) {
    for (var i = 0; i < ZONES.length; i++) { try { if (el.closest(ZONES[i])) return true; } catch (e) {} }
    return false;
  }
  function exclu(el) {
    if (dansZone(el)) return true;
    for (var i = 0; i < EXCLUS.length; i++) if (correspond(el, EXCLUS[i])) return true;
    return false;
  }
  function champTexte(el) {
    var t = el.tagName;
    if (t === "TEXTAREA") return true;
    if (t !== "INPUT") return false;
    var ty = (el.type || "text").toLowerCase();
    return ty === "text" || ty === "search" || ty === "";
  }
  function libelleDe(el) {
    var p = el.parentElement, pp = p && p.parentElement, f = pp && pp.firstElementChild;
    if (!f || f === p) return "";
    return String(f.textContent || "").trim();
  }
  function chemin() { return String((W.location && W.location.pathname) || "/"); }
  function regleDe(el) {
    var ch = chemin();
    for (var i = 0; i < REGLES.length; i++) {
      var r = REGLES[i];
      if (r.page && ch.indexOf(r.page) !== 0) continue;
      if (r.sel) { if (correspond(el, r.sel)) return r; continue; }
      if (el.tagName !== "TEXTAREA") continue;
      var lab = libelleDe(el);
      if (r.mode === "debut" ? lab.indexOf(r.libelle) === 0 : lab === r.libelle) return r;
    }
    return null;
  }

  function alpha(c) {
    c = String(c || "").trim();
    if (!c || c === "transparent") return 0;
    var m = c.match(/^rgba?\(([^)]*)\)$/);
    if (!m) return 1;
    var p = m[1].split(/[\s,\/]+/).filter(Boolean);
    return p.length >= 4 ? parseFloat(p[3]) : 1;
  }
  function fondOpaque(n) {
    while (n && n.nodeType === 1) {
      var b = cs(n).backgroundColor;
      if (alpha(b) >= 1) return b;
      n = n.parentElement;
    }
    return "#16181d";
  }
  function aDesAbsolus(p) {
    var t = p.getElementsByTagName("*"), n = Math.min(t.length, 400);
    for (var i = 0; i < n; i++) {
      var e = t[i];
      if (e.classList && e.classList.contains("dzia-barre")) continue;
      if (cs(e).position === "absolute") return true;
    }
    return false;
  }

  var suivis = [];
  var ro = W.ResizeObserver ? new W.ResizeObserver(function () { planifierSync(); }) : null;

  function creerBarre(el) {
    var b = D.createElement("span");
    b.className = "dzia-barre";
    var g = D.createElement("span");
    g.className = "dzia-badge";
    g.setAttribute("title", "Champ de génération IA");
    g.textContent = "IA";
    g.addEventListener("mousedown", function (ev) { ev.preventDefault(); try { el.focus(); } catch (e) {} });
    var m = D.createElement("span");
    m.className = "dzia-emp";
    m.setAttribute("data-dzia-slot", "modele");
    var mic = D.createElement("span");
    mic.className = "dzia-emp";
    mic.setAttribute("data-dzia-slot", "micro");
    b.appendChild(g); b.appendChild(m); b.appendChild(mic);
    b.__modele = m; b.__micro = mic;
    return b;
  }

  function taille(e) { return e ? e.offsetWidth + "x" + e.offsetHeight : ""; }
  function pads(c) {
    return { t: parseFloat(c.paddingTop) || 0, r: parseFloat(c.paddingRight) || 0,
             b: parseFloat(c.paddingBottom) || 0, l: parseFloat(c.paddingLeft) || 0 };
  }
  function poserPads(el, q) {
    el.style.paddingTop = px(q.t); el.style.paddingRight = px(q.r);
    el.style.paddingBottom = px(q.b); el.style.paddingLeft = px(q.l);
  }
  function seulChamp(p) {
    var l = candidats(p), n = 0;
    for (var i = 0; i < l.length; i++) if (champTexte(l[i])) n++;
    return n === 1;
  }
  /* le parent n'est l'habit du champ que s'il le serre (le composant `le` :
     30 px autour d'un input de 18) — jamais une carte entière */
  function serre(p, el) {
    return p.offsetHeight - el.offsetHeight <= 16 && p.offsetWidth - el.offsetWidth <= 80;
  }
  /* Les teintes sous le liseré sont RELUES à chaque synchronisation (revue
     T8) : le Cardforge bascule clair/sombre à chaud (data-theme de <html>) et
     un champ peut devenir disabled — une teinte figée au marquage peindrait
     l'ancien fond. Posées seulement si elles changent. */
  function teindre(cible) {
    var c = cs(cible), sous = fondOpaque(cible.parentElement);
    var fond = alpha(c.backgroundColor) > 0 ? c.backgroundColor : sous;
    if (cible.style.getPropertyValue("--dzia-fond") !== fond) cible.style.setProperty("--dzia-fond", fond);
    if (cible.style.getPropertyValue("--dzia-sous") !== sous) cible.style.setProperty("--dzia-sous", sous);
  }
  function peindre(cible) {
    teindre(cible);
    cible.classList.add("dzia-lis");
  }

  /* Où peindre le liseré, SANS changer aucune taille (mesuré, sinon repli) :
     1. le champ a une bordure → le champ lui-même ;
     2. champ sans bordure dans un parent bordé qui le SERRE et dont il est le
        seul champ (le composant `le` du bundle : div bordée + input nu) → le
        parent ;
     3. champ sans bordure, border-box, padding ≥ 1 px partout → bordure de
        1 px prise sur le padding (dzia-bord) ;
     4. sinon, ou si une taille a bougé → halo seul (dzia-halo). */
  function habiller(el, genre, regle) {
    var c = cs(el), p = el.parentElement;
    el.setAttribute("data-dz-ia", genre);
    if (regle) el.setAttribute("data-dz-ia-regle", regle.id);
    el.classList.add("dzia-champ");
    var st = {
      genre: genre, regle: regle ? regle.id : null, manuel: !regle, parent: p,
      boite: c.boxSizing === "border-box", pad: pads(c), padInline: null,
      inline0: [el.style.paddingTop, el.style.paddingRight, el.style.paddingBottom, el.style.paddingLeft],
      reserve: null, coin: false, cible: null, barre: null
    };
    var t0 = taille(el), tp0 = taille(p), cible = null;
    if ((parseFloat(c.borderTopWidth) || 0) > 0) cible = el;
    else if (p && (parseFloat(cs(p).borderTopWidth) || 0) > 0 && seulChamp(p) && serre(p, el)) cible = p;
    else if (st.boite && Math.min(st.pad.t, st.pad.r, st.pad.b, st.pad.l) >= 1) {
      st.padInline = [el.style.paddingTop, el.style.paddingRight, el.style.paddingBottom, el.style.paddingLeft];
      st.pad = { t: st.pad.t - 1, r: st.pad.r - 1, b: st.pad.b - 1, l: st.pad.l - 1 };
      el.classList.add("dzia-bord");
      poserPads(el, st.pad);
      cible = el;
    }
    if (cible) peindre(cible);
    if (cible && (taille(el) !== t0 || taille(p) !== tp0)) {
      cible.classList.remove("dzia-lis");
      el.classList.remove("dzia-bord");
      if (st.padInline) {
        el.style.paddingTop = st.padInline[0]; el.style.paddingRight = st.padInline[1];
        el.style.paddingBottom = st.padInline[2]; el.style.paddingLeft = st.padInline[3];
        st.pad = pads(cs(el));
      }
      cible = null;
    }
    if (!cible) el.classList.add("dzia-halo");
    st.cible = cible;
    st.barre = creerBarre(el);
    st.modele = (regle && regle.modele) || null;
    st.pastille = st.modele ? poserPastille(el, st.barre.__modele, regle) : null;
    st.micro = poserMicro(el, st.barre.__micro);
    if (p) {
      if (cs(p).position === "static" && !aDesAbsolus(p)) {
        p.style.position = "relative";
        p.setAttribute("data-dzia-pos", "1");
      }
      p.insertBefore(st.barre, el.nextSibling);
    }
    el.__dzia = st;
    suivis.push(el);
    if (ro) { try { ro.observe(el); if (p) ro.observe(p); } catch (e) {} }
    synchroniserUn(el);
  }

  /* Champ DÉTACHÉ (onglet caché, rendu conditionnel) : l'habillage est défait
     en entier — barre, classes, teintes, paddings, marque de règle, __dzia —
     pour qu'un rattachement du MÊME nœud soit re-marqué comme neuf (revue T8 :
     un __dzia resté posé faisait sauter le champ par `marquer`, barre perdue
     pour toujours). Un data-dz-ia MANUEL reste : c'est une intention. */
  function defaire(el) {
    var st = el.__dzia;
    if (!st) return;
    var b = st.barre;
    if (ouverte && ouverte.b === st.pastille) fermerListe();
    abandonnerDictee(el);
    if (b && b.parentNode) b.parentNode.removeChild(b);
    var k = suivis.indexOf(el);
    if (k >= 0) suivis.splice(k, 1);
    var cibles = [el];
    if (st.cible && st.cible !== el) cibles.push(st.cible);
    for (var i = 0; i < cibles.length; i++) {
      cibles[i].classList.remove("dzia-lis");
      cibles[i].style.removeProperty("--dzia-fond");
      cibles[i].style.removeProperty("--dzia-sous");
    }
    el.classList.remove("dzia-champ", "dzia-bord", "dzia-halo");
    el.style.paddingTop = st.inline0[0]; el.style.paddingRight = st.inline0[1];
    el.style.paddingBottom = st.inline0[2]; el.style.paddingLeft = st.inline0[3];
    if (!st.manuel) el.removeAttribute("data-dz-ia");
    el.removeAttribute("data-dz-ia-regle");
    var p = st.parent, reste = false;
    for (var j = 0; j < suivis.length; j++) if (suivis[j].__dzia && suivis[j].__dzia.parent === p) { reste = true; break; }
    if (ro) {
      try { ro.unobserve(el); } catch (e) {}
      if (p && !reste) { try { ro.unobserve(p); } catch (e) {} }
    }
    if (p && !reste && p.getAttribute && p.getAttribute("data-dzia-pos")) {
      p.style.position = "";
      p.removeAttribute("data-dzia-pos");
    }
    delete el.__dzia;
  }

  function candidats(racine) {
    var out = [];
    if (!racine) return out;
    if (racine.nodeType === 1 && (racine.tagName === "TEXTAREA" || racine.tagName === "INPUT")) out.push(racine);
    if (racine.getElementsByTagName) {
      var a = racine.getElementsByTagName("textarea"), b = racine.getElementsByTagName("input"), i;
      for (i = 0; i < a.length; i++) out.push(a[i]);
      for (i = 0; i < b.length; i++) out.push(b[i]);
    }
    return out;
  }

  function marquer(racine) {
    injecterStyle();
    var l = candidats(racine || D.body), n = 0;
    for (var i = 0; i < l.length; i++) {
      var el = l[i];
      if (el.__dzia || !champTexte(el)) continue;
      var manuel = el.getAttribute("data-dz-ia");
      if (manuel) { habiller(el, manuel, null); n++; continue; }
      if (exclu(el)) continue;
      var r = regleDe(el);
      if (r) { habiller(el, r.genre, r); n++; }
    }
    return n;
  }

  function px(v) { return Math.round(v) + "px"; }
  function synchroniserUn(el) {
    var st = el.__dzia, b = st && st.barre;
    if (!b) return;
    if (!el.isConnected) { defaire(el); return; }
    if (!b.isConnected && el.parentNode) el.parentNode.insertBefore(b, el.nextSibling);
    if (el.offsetParent === null && cs(el).position !== "fixed") {
      if (b.style.display !== "none") b.style.display = "none";
      return;
    }
    if (b.style.display === "none") b.style.display = "";
    if (st.cible) teindre(st.cible);
    if (st.pastille) rafraichirPastille(el);
    if (st.micro) rafraichirMicro(el);
    if (noteEl && noteEl.__el === el) placerNote();
    var rb = b.getBoundingClientRect(), r = el.getBoundingClientRect();
    var mono = el.tagName === "INPUT" || r.height < 44;
    reserver(el, st, rb, mono);
    r = el.getBoundingClientRect();
    var gl = parseFloat(b.style.left) || 0, gt = parseFloat(b.style.top) || 0;
    // une textarea redimensionnable garde sa poignée du coin bas droit libre
    var droite = !mono && el.tagName === "TEXTAREA" && cs(el).resize !== "none" ? 16 : 6;
    var wl = r.right - rb.width - droite, wt;
    if (st.coin) wt = r.top - rb.height / 2;                 // à cheval sur le bord haut
    else if (mono) wt = r.top + (r.height - rb.height) / 2;  // centrée, dans le champ
    else wt = r.bottom - rb.height - 5;                       // coin bas droit, dans le champ
    var nl = px(gl + wl - rb.left), nt = px(gt + wt - rb.top);
    if (b.style.left !== nl) b.style.left = nl;
    if (b.style.top !== nt) b.style.top = nt;
  }
  /* Réserve de padding sous la barre, pour que le texte ne passe pas dessous :
     à droite tant que la barre est étroite, en bas pour une barre large sur un
     champ multiligne (T9/T10). MESURÉE : si la taille du champ bouge (champ
     content-box, input à largeur de contenu, textarea auto-extensible), la
     réserve est retirée et la barre passe « à cheval » sur le bord haut. */
  function reserver(el, st, rb, mono) {
    if (st.coin || !rb.width) return;
    if (!st.boite) { st.coin = true; return; }
    var bas = !mono && rb.width > 60;
    var cle = (bas ? "b" : "r") + Math.round(bas ? rb.height : rb.width);
    if (st.reserve === cle) return;
    var t0 = taille(el), avant = [el.style.paddingRight, el.style.paddingBottom];
    if (bas) {
      el.style.paddingRight = px(st.pad.r);
      el.style.paddingBottom = px(st.pad.b + rb.height + 6);
    } else {
      el.style.paddingBottom = px(st.pad.b);
      el.style.paddingRight = px(st.pad.r + rb.width + 10);
    }
    if (taille(el) !== t0) {
      el.style.paddingRight = avant[0]; el.style.paddingBottom = avant[1];
      st.coin = true;
      return;
    }
    st.reserve = cle;
  }
  function synchroniser() {
    var l = suivis.slice();
    for (var i = 0; i < l.length; i++) { try { synchroniserUn(l[i]); } catch (e) {} }
  }

  var tSync = 0, tMarq = 0, aMarquer = [];
  function planifierSync() {
    if (tSync) return;
    tSync = W.setTimeout(function () { tSync = 0; synchroniser(); }, 16);
  }
  function planifierMarquage() {
    if (tMarq) return;
    tMarq = W.setTimeout(function () {
      tMarq = 0;
      var l = aMarquer; aMarquer = [];
      for (var i = 0; i < l.length; i++) if (l[i].isConnected) { try { marquer(l[i]); } catch (e) {} }
      synchroniser();
    }, 40);
  }

  function demarrer() {
    injecterStyle();
    marquer(D.body || D.documentElement);
    if (W.MutationObserver) {
      new W.MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
          var a = muts[i].addedNodes || [];
          for (var j = 0; j < a.length; j++) {
            var n = a[j];
            if (n.nodeType !== 1 || (n.classList && n.classList.contains("dzia-barre"))) continue;
            aMarquer.push(n);
          }
          if ((muts[i].removedNodes || []).length) planifierSync();
        }
        if (aMarquer.length) planifierMarquage();
      }).observe(D.documentElement, { childList: true, subtree: true });
      /* bascule de thème (data-theme / class de <html>) : repeindre, et une
         seconde fois après les transitions de fond de l'hôte */
      new W.MutationObserver(function () {
        planifierSync();
        W.setTimeout(synchroniser, 450);
      }).observe(D.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
    }
    W.addEventListener("resize", planifierSync);
    D.addEventListener("focusin", planifierSync, true);
    /* la vue changée met la pastille à jour : <select> natif (change) et
       select custom / cartes du bundle (clic, après le rendu de React) */
    D.addEventListener("change", function () { W.setTimeout(rafraichirPastilles, 0); }, true);
    D.addEventListener("click", function () { W.setTimeout(rafraichirPastilles, 80); });
    D.addEventListener("mousedown", horsListe, true);
    D.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && ouverte) fermerListe(); }, true);
    /* Échap arrête la dictée en cours (écoute ou prise) ; l'hôte ne le voit pas */
    D.addEventListener("keydown", function (ev) {
      var a = dic.active;
      if (ev.key !== "Escape" || !a || (a.etat !== "ecoute" && a.etat !== "prise")) return;
      ev.preventDefault(); ev.stopPropagation();
      arreterDictee();
    }, true);
    D.addEventListener("scroll", function (ev) {
      if (ouverte && !(ev.target && ev.target.nodeType === 1 && ouverte.node.contains(ev.target))) placerListe();
    }, true);
    W.addEventListener("resize", placerListe);
    D.addEventListener("focusin", function (ev) {       // le réglage de l'Atelier a pu changer dans 🎨 DA
      var st = ev.target && ev.target.__dzia;
      if (st && st.modele && st.modele.charge && st.modele.charge.indexOf("atelier") >= 0) charger("atelier", true);
    }, true);
    D.addEventListener("focusout", planifierSync, true);
    D.addEventListener("scroll", planifierSync, true);
    W.setInterval(function () { if (!D.hidden) synchroniser(); }, 800);
  }

  /* ─────────── T9 (27/09) : PASTILLE DE MODÈLE, miroir du sélecteur de la vue ───────────
     Chaque règle porte un ADAPTATEUR `modele` : { liste: "video" | "image" |
     "musique" | null, lire(champ) → id, ecrire(champ, id) → Promise, fixe? }.
     La pastille ne décide RIEN : elle lit le choix de la vue et, quand on la
     change, rejoue le geste dans le sélecteur de la vue (clic sur le select
     custom du bundle — ce ne sont pas des <select> natifs —, clic sur la
     carte de modèle du Son & VFX, ou valeur + événement `change` natif sur un
     <select> des pages à part). La vue reste la seule source de vérité : le
     modèle réellement envoyé est celui qu'elle affiche.
     Vues sans choix, ou dont le choix ne se pilote pas sans patcher le bundle :
     pastille GRISÉE (aria-disabled), libellé du modèle réellement utilisé,
     `title` « choisi par la vue ». Un modèle dont la clé manque est grisé dans
     la liste avec le `title` « clé FAL_KEY absente » (ou OPENAI_API_KEY,
     GEMINI_API_KEY). E-12 : tout bouton a un title ; on grise, on n'échange
     jamais deux boutons (la pastille est UN nœud dont on change l'état). */
  var CLE_ABSENTE = function (cle) { return "clé " + cle + " absente"; };
  /* Le registre COMPLET des modèles d'image : /api/image-models ne rend que
     les DISPONIBLES (un modèle sans clé y est absent). Miroir de
     routes.list_image_models (id, libellé) et de pricing._IMAGE_MODELS
     (fournisseur → clé) : le banc refuse toute dérive. */
  var CATALOGUE_IMAGE = [
    ["flux", "FLUX schnell", "FAL_KEY"],
    ["nano-banana", "Nano Banana (Gemini)", "FAL_KEY"],
    ["nano-banana-pro", "Nano Banana Pro (Gemini 3)", "FAL_KEY"],
    ["gpt-image-2-fal", "GPT Image 2 (via fal)", "FAL_KEY"],
    ["gpt-image-2.5-flare-fal", "GPT Image 2.5 Flare (via fal)", "FAL_KEY"],
    ["gpt-image-2.5-sunburst-fal", "GPT Image 2.5 Sunburst (via fal)", "FAL_KEY"],
    ["gpt-image-2", "GPT Image 2", "OPENAI_API_KEY"],
    ["gpt-image-2.5-flare", "GPT Image 2.5 Flare (OpenAI)", "OPENAI_API_KEY"],
    ["gpt-image-2.5-sunburst", "GPT Image 2.5 Sunburst (OpenAI)", "OPENAI_API_KEY"],
    ["gpt-image-1", "GPT Image 1", "OPENAI_API_KEY"],
    ["gpt-image-1-mini", "GPT Image 1 mini", "OPENAI_API_KEY"]
  ];
  function lsGet(k) { try { return W.localStorage ? W.localStorage.getItem(k) : null; } catch (e) { return null; } }
  function jget(url) {
    return W.fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  function prixTxt(v, unite) {
    v = Number(v);
    if (!isFinite(v)) return "";
    return "$" + (v >= 0.1 ? v.toFixed(2) : v.toFixed(3)) + unite;
  }
  /* la formule du sélecteur du Quick (DzVideoModelSel du bundle) : le prix
     1080p, sinon « * », sinon le plus cher des tarifs connus */
  function prixVideo(m) {
    var rr = m.usd_per_s || {}, v = rr["1080p"] != null ? rr["1080p"] : rr["*"];
    if (v == null) for (var k in rr) { var n = Number(rr[k]); if (isFinite(n) && (v == null || n > v)) v = n; }
    return v != null ? prixTxt(v, "/s") : "";
  }
  var CHARGEURS = {
    video: function () {
      return jget("/api/video-models").then(function (d) {
        return { defaut: d.default || "", modeles: (d.models || []).map(function (m) {
          var px = prixVideo(m);
          return { id: m.id, label: m.label || m.id, dispo: !!m.available,
                   cle: m.provider === "google" ? "GEMINI_API_KEY" : "FAL_KEY", prix: px,
                   vue: (m.label || m.id) + (px ? " · " + px : "") + (m.available ? "" : " · clé manquante") };
        }) };
      });
    },
    image: function () {
      return jget("/api/image-models").then(function (d) {
        var srv = {}, i;
        (d.models || []).forEach(function (m) { srv[m.id] = m; });
        var mods = CATALOGUE_IMAGE.map(function (c) {
          var s = srv[c[0]], lab = (s && s.label) || c[1];
          return { id: c[0], label: lab, dispo: !!s, cle: c[2], prix: "", vue: lab };
        });
        var n = mods.length;
        for (i = 0; i < (d.models || []).length; i++) {   // un id servi hors registre : montré tel quel, sans prix inventé
          var m = d.models[i];
          if (!CATALOGUE_IMAGE.some(function (c) { return c[0] === m.id; }))
            mods.push({ id: m.id, label: m.label || m.id, dispo: true, cle: "", prix: "", vue: m.label || m.id });
        }
        var o = { defaut: d.default || "", modeles: mods };
        /* le prix par image : UNE estimation (rien n'est dépensé), la table
           des lignes de coût des vues (pricing._IMAGE_MODELS) */
        return W.fetch("/api/cost/estimate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind: "campaign", ops: mods.slice(0, n).map(function (x) { return { kind: "image", model: x.id }; }) })
        }).then(function (r) { return r.ok ? r.json() : null; }).then(function (e) {
          var l = (e && e.breakdown) || [];
          if (l.length === n) for (var k = 0; k < n; k++) mods[k].prix = prixTxt(l[k].usd, "/image");
          return o;
        }, function () { return o; });
      });
    },
    musique: function () {
      return jget("/api/music-models").then(function (d) {
        return { defaut: d.default || "", modeles: (d.models || []).map(function (m) {
          return { id: m.id, label: m.label || m.id, dispo: !!d.enabled, cle: "FAL_KEY",
                   prix: m.usd != null ? "~$" + Number(m.usd).toFixed(2) : "", vue: m.label || m.id };
        }) };
      });
    },
    /* le générateur de l'Atelier se choisit dans 🎨 DA (atelier_settings) */
    atelier: function () {
      return jget("/api/atelier/settings").then(function (d) {
        var s = (d && d.settings) || {};
        return { defaut: s.image_provider || "flux", modeles: [] };
      });
    }
  };
  var donnees = {}, enCours = {};
  function charger(liste, force) {
    if (!CHARGEURS[liste] || !W.fetch) return null;
    if (enCours[liste] && !force) return enCours[liste];
    enCours[liste] = CHARGEURS[liste]().then(function (o) {
      donnees[liste] = o; rafraichirPastilles(); return o;
    }, function () {
      donnees[liste] = donnees[liste] || { defaut: "", modeles: [], erreur: true };
      rafraichirPastilles(); return donnees[liste];
    });
    return enCours[liste];
  }

  function visible(e) { return !!e && e.offsetParent !== null && !dansZone(e); }
  /* le sélecteur de la vue le plus PROCHE du champ (ancêtre par ancêtre) */
  function proche(el, sel, filtre, max) {
    var n = el.parentElement;
    for (var i = 0; n && i < (max || 8); i++, n = n.parentElement) {
      var l = n.querySelectorAll(sel);
      for (var j = 0; j < l.length; j++) if (visible(l[j]) && (!filtre || filtre(l[j]))) return l[j];
    }
    return null;
  }
  function texteDe(b) {
    var s = b && b.querySelector ? b.querySelector("span") : null;
    return String(((s || b) || {}).textContent || "").trim();
  }
  function modeleDe(liste, id) {
    var d = donnees[liste], l = (d && d.modeles) || [];
    for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i];
    return null;
  }
  /* texte affiché par la vue → id (« Défaut (x) » = x, le défaut du serveur) */
  function parTexte(liste, t) {
    var d = donnees[liste];
    if (!d || !t) return null;
    var m = /^Défaut \((.+)\)$/.exec(t);
    if (m) return m[1];
    var l = d.modeles, i;
    for (i = 0; i < l.length; i++) if (l[i].vue === t || l[i].label === t) return l[i].id;
    for (i = 0; i < l.length; i++) if (t.indexOf(l[i].label + " · ") === 0) return l[i].id;
    return null;
  }
  /* le select CUSTOM du bundle (`re`) : un bouton [data-dzselect] ouvre une
     liste de boutons dans le même conteneur. On rejoue le geste : clic pour
     ouvrir, clic sur l'option dont le texte est celui de la vue. */
  function choisirRe(btn, cible) {
    return new Promise(function (ok) {
      var racine = btn.parentElement, n = 0;
      btn.click();
      (function essai() {
        var opts = racine ? racine.querySelectorAll("button") : [];
        for (var i = 0; i < opts.length; i++) {
          if (opts[i] !== btn && texteDe(opts[i]) === cible) { opts[i].click(); ok(true); return; }
        }
        if (++n > 20) {
          if (opts.length > 1) btn.click();            // refermer la liste restée ouverte
          ok(false); return;
        }
        W.setTimeout(essai, 25);
      })();
    });
  }
  function poserValeur(s, v) {
    var P = W.HTMLSelectElement && W.HTMLSelectElement.prototype;
    var d = P && Object.getOwnPropertyDescriptor(P, "value");
    if (d && d.set) d.set.call(s, v); else s.value = v;
    var E = W.Event;
    s.dispatchEvent(new E("input", { bubbles: true }));
    s.dispatchEvent(new E("change", { bubbles: true }));
  }
  function optionsDe(s) {
    var o = (s && s.options) || [], out = [];
    for (var i = 0; i < o.length; i++) {
      if (o[i].value === "") continue;
      var t = String(o[i].text || o[i].textContent || o[i].value).trim();
      out.push({ id: o[i].value, label: t, dispo: !o[i].disabled, cle: "", prix: "", vue: t });
    }
    return out;
  }

  /* ---- les fabriques d'adaptateurs ---- */
  function A_re(liste, sel, o) {       // select custom du bundle, piloté par clics
    o = o || {};
    function trouver(el) {
      // parListe : seul un select dont le texte est un modèle DE LA LISTE est le bon (Chapitres : « Ken Burns » est plus près)
      return proche(el, sel, o.parListe ? function (b) { return !!modeleDe(liste, parTexte(liste, texteDe(b))); } : null);
    }
    return { liste: liste, vue: "select custom de la vue", trouver: trouver,
      lire: function (el) {
        var b = trouver(el);
        if (b) return parTexte(liste, texteDe(b));
        return o.secours ? o.secours() : null;
      },
      ecrire: function (el, id) {
        var b = trouver(el), m = modeleDe(liste, id);
        if (!b || !m) return Promise.resolve(false);
        return choisirRe(b, m.vue);
      } };
  }
  function A_natif(liste, sel, o) {    // <select> natif : valeur + événement change natif
    o = o || {};
    function trouver(el) {
      if (o.proche) return proche(el, sel, o.filtre, 6);
      var l = D.querySelectorAll(sel);
      for (var i = 0; i < l.length; i++) if (!dansZone(l[i])) return l[i];
      return null;
    }
    return { liste: liste, vue: "sélecteur de la vue", trouver: trouver, natif: true,
      lire: function (el) { var s = trouver(el); return s && s.value ? s.value : null; },
      ecrire: function (el, id) {
        var s = trouver(el);
        if (!s || !optionsDe(s).some(function (x) { return x.id === id; })) return Promise.resolve(false);
        poserValeur(s, id);
        return Promise.resolve(true);
      } };
  }
  function A_cartes(liste) {           // les cartes de modèle du Son & VFX (.svm-model)
    function cartes(el) {
      var b = proche(el, ".svm-model", null, 6);
      return b && b.parentElement ? b.parentElement.querySelectorAll(".svm-model") : [];
    }
    function nom(c) { var n = c.querySelector(".svm-genname"); return String((n || c).textContent || "").trim(); }
    return { liste: liste, vue: "cartes de modèle de la vue",
      trouver: function (el) { return cartes(el)[0] || null; },
      lire: function (el) {
        var l = cartes(el);
        for (var i = 0; i < l.length; i++) if (l[i].hasAttribute("data-sel")) return parTexte(liste, nom(l[i]));
        return null;
      },
      ecrire: function (el, id) {
        var l = cartes(el), m = modeleDe(liste, id);
        for (var i = 0; m && i < l.length; i++) if (nom(l[i]) === m.label) { l[i].click(); return Promise.resolve(true); }
        return Promise.resolve(false);
      } };
  }
  function A_fixe(libelle) { return { liste: null, fixe: libelle }; }
  function A_defaut(liste, lire, pourquoi, charge) {   // lecture seule : ce que la vue enverra
    return { liste: liste, lire: lire, pourquoi: pourquoi, charge: charge };
  }
  function A_texte(sel, filtre, pourquoi) {           // lecture seule : le texte d'un select custom
    return { liste: null, pourquoi: pourquoi, texte: function (el) {
      var b = proche(el, sel, function (x) { return filtre.test(texteDe(x)); });
      return b ? texteDe(b) : "";
    } };
  }
  var imageGlobale = function () { return lsGet("dz_image_model") || (donnees.image && donnees.image.defaut) || null; };
  var atelierLire = function () { return donnees.atelier ? donnees.atelier.defaut : null; };
  var videoDefaut = function () { return donnees.video ? donnees.video.defaut : null; };
  function imageSel(s) {
    return optionsDe(s).some(function (x) { return CATALOGUE_IMAGE.some(function (c) { return c[0] === x.id; }); })
      || /aucun modèle/.test(String(s.textContent || ""));
  }
  var DA = "le générateur se choisit dans 🎨 DA";
  var MODELES = {
    "quick-prompt": A_re("video", "[data-dzvmsel] [data-dzselect]", { secours: function () { return lsGet("dz_video_model") || videoDefaut(); } }),
    "quick-script": A_fixe("HeyGen (avatar)"),
    "quick-motion": A_fixe("HeyGen (photo animée)"),
    "chapitres-illus": A_re("image", "[data-dzselect]", { parListe: true, secours: imageGlobale }),
    "son-paroles": A_cartes("musique"),
    "son-musique": A_cartes("musique"),
    "son-sfx": A_fixe("ElevenLabs SFX"),
    "montage-sons": A_fixe("ElevenLabs SFX"),
    "templates-ia": A_defaut("image", imageGlobale, "le modèle d'image global : Library, Chapitres, Réglages"),
    "library-image": A_re("image", "[data-dzselect]", { parListe: true, secours: imageGlobale }),
    "game-assets-3d": A_texte("[data-dzselect]", /~\$/, "le moteur 3D se choisit dans la vue"),
    "atelier-style": A_defaut("image", atelierLire, DA, ["image", "atelier"]),
    "atelier-da": A_natif("image", "#daProvider"),
    "atelier-entite": A_defaut("image", atelierLire, DA, ["image", "atelier"]),
    "atelier-entite-style": A_defaut("image", atelierLire, DA, ["image", "atelier"]),
    "atelier-plan": A_defaut("image", atelierLire, DA, ["image", "atelier"]),
    "spritelab-anim": A_defaut("video", videoDefaut, "le Spritelab anime avec le modèle vidéo par défaut du serveur"),
    "materialforge": A_natif("image", "#model"),
    "cardforge-face": A_natif("image", "#cf-face-model"),
    "cardforge-decor": A_natif("image", "select.cff-sel", { proche: true, filtre: imageSel }),
    "cardforge-texture": A_natif(null, 'select[data-field="engine"]', { proche: true }),
    "vectorlab-ia": A_natif(null, "#iaModele"),
    "vectorlab-vitrail": A_fixe("moteur de langage des Réglages")
  };
  for (var iM = 0; iM < REGLES.length; iM++) REGLES[iM].modele = MODELES[REGLES[iM].id] || null;

  /* la liste des modèles d'un adaptateur, telle que la pastille la montre */
  function modelesDe(el, m) {
    if (!m.liste) return m.natif ? optionsDe(m.trouver(el)) : [];
    var l = ((donnees[m.liste] || {}).modeles || []).map(function (x) {
      return { id: x.id, label: x.label, dispo: x.dispo, cle: x.cle, prix: x.prix, vue: x.vue, horsVue: false };
    });
    if (m.natif) {                     // un modèle disponible absent du <select> de la vue ne s'y écrit pas
      var ids = optionsDe(m.trouver(el)).map(function (x) { return x.id; });
      l.forEach(function (x) { if (x.dispo && ids.indexOf(x.id) < 0) x.horsVue = true; });
    }
    return l;
  }
  function clesManquantes(l) {
    var c = [];
    l.forEach(function (x) { if (!x.dispo && x.cle && c.indexOf(x.cle) < 0) c.push(x.cle); });
    return c;
  }
  function poserPastille(el, slot, regle) {
    var m = regle && regle.modele;
    if (!m) return null;
    var b = D.createElement("button");
    b.setAttribute("type", "button");
    b.className = "dzia-modele";
    b.setAttribute("data-dzia-modele", regle.id);
    b.setAttribute("aria-haspopup", "listbox");
    b.setAttribute("aria-expanded", "false");
    b.setAttribute("title", "Modèle de génération");
    var t = D.createElement("span");
    t.className = "dzia-mtxt";
    t.textContent = "…";
    b.appendChild(t);
    b.addEventListener("mousedown", function (ev) { ev.preventDefault(); });   // le champ garde le focus
    /* un contrôle étranger à l'hôte : son pointerdown ne remonte pas (le
       Vectorlab traite tout pointerdown de #stage comme un geste d'outil, qui
       re-rendait le dialogue IA et détruisait la pastille avant le clic) */
    b.addEventListener("pointerdown", function (ev) { ev.stopPropagation(); });
    b.addEventListener("click", function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      if (b.getAttribute("aria-disabled") === "true") return;
      ouvrirListe(el, b);
    });
    slot.appendChild(b);
    var ch = m.charge || (m.liste ? [m.liste] : []);
    for (var i = 0; i < ch.length; i++) charger(ch[i]);
    return b;
  }
  function poserAttr(e, k, v) { if (e.getAttribute(k) !== v) e.setAttribute(k, v); }
  function rafraichirPastille(el) {
    var st = el.__dzia, b = st && st.pastille, m = st && st.modele;
    if (!b || !m) return;
    var label, titre, fige = true, id = null, mini = el.offsetWidth > 0 && el.offsetWidth < 200;
    if (m.fixe) {
      label = m.fixe;
      titre = "Modèle : " + m.fixe + " — choisi par la vue (pas de choix de modèle ici)";
    } else if (m.texte) {
      var tx = m.texte(el);
      label = tx ? tx.split(" — ")[0] : "—";
      titre = "Modèle : " + (tx || "—") + " — choisi par la vue (" + m.pourquoi + ")";
    } else {
      id = m.lire(el);
      var mod = id != null && m.liste ? modeleDe(m.liste, id) : null;
      if (!mod && id != null && m.natif) mod = optionsDe(m.trouver(el)).filter(function (x) { return x.id === id; })[0] || null;
      label = mod ? mod.label : (id || "—");
      var prix = mod && mod.prix ? " · " + mod.prix : "";
      if (!m.ecrire) {
        titre = "Modèle : " + label + prix + " — choisi par la vue (" + m.pourquoi + ")";
      } else {
        var l = modelesDe(el, m), dispo = l.filter(function (x) { return x.dispo && !x.horsVue; });
        if (m.liste && donnees[m.liste] && !dispo.length) {
          var cm = clesManquantes(l);
          label = "aucun modèle";
          titre = "Aucun modèle disponible" + (cm.length ? " — " + cm.map(CLE_ABSENTE).join(", ") : "")
            + (l.some(function (x) { return x.horsVue; }) ? " — le sélecteur de la vue n'en propose aucun" : "");
        } else if (!m.trouver(el)) {
          titre = "Modèle : " + label + prix + " — choisi par la vue (sélecteur de la vue introuvable ici)";
        } else {
          fige = false;
          titre = "Modèle : " + label + prix + (mod && !mod.dispo && mod.cle ? " (" + CLE_ABSENTE(mod.cle) + ")" : "")
            + " — cliquer pour changer (écrit dans le sélecteur de la vue)";
        }
      }
    }
    var t = b.firstElementChild;
    if (t && t.textContent !== label) t.textContent = label;
    poserAttr(b, "title", titre);
    poserAttr(b, "aria-label", titre);
    poserAttr(b, "aria-disabled", fige ? "true" : "false");
    poserAttr(b, "data-dzia-id", id == null ? "" : String(id));
    if (b.classList.contains("dzia-mini") !== mini) b.classList.toggle("dzia-mini", mini);
    if (fige && ouverte && ouverte.b === b) fermerListe();
  }
  function rafraichirPastilles() {
    for (var i = 0; i < suivis.length; i++) { try { rafraichirPastille(suivis[i]); } catch (e) {} }
  }

  var ouverte = null;
  function fermerListe() {
    if (!ouverte) return;
    if (ouverte.node.parentNode) ouverte.node.parentNode.removeChild(ouverte.node);
    ouverte.b.setAttribute("aria-expanded", "false");
    ouverte = null;
  }
  function ouvrirListe(el, b) {
    if (ouverte && ouverte.b === b) { fermerListe(); return; }
    fermerListe();
    var st = el.__dzia, m = st.modele, l = modelesDe(el, m), cour = m.lire(el);
    var L = D.createElement("div");
    L.className = "dzia-liste";
    L.setAttribute("role", "listbox");
    L.setAttribute("aria-label", "Modèles");
    l.forEach(function (x) {
      var o = D.createElement("button");
      o.setAttribute("type", "button");
      o.className = "dzia-opt";
      o.setAttribute("role", "option");
      o.setAttribute("data-id", x.id);
      o.setAttribute("aria-selected", x.id === cour ? "true" : "false");
      var nm = D.createElement("span");
      nm.className = "dzia-onom";
      nm.textContent = x.label;
      o.appendChild(nm);
      if (x.prix) {
        var p = D.createElement("span");
        p.className = "dzia-oprix";
        p.textContent = x.prix;
        o.appendChild(p);
      }
      var off = !x.dispo ? (x.cle ? CLE_ABSENTE(x.cle) : "indisponible") : (x.horsVue ? "absent du sélecteur de la vue" : "");
      if (off) {
        o.setAttribute("aria-disabled", "true");
        o.classList.add("dzia-off");
        o.setAttribute("title", off + " — " + x.label);
      } else {
        o.setAttribute("title", x.label + (x.prix ? " · " + x.prix : "")
          + (x.id === cour ? " — modèle actuel de la vue" : " — choisir ce modèle (écrit dans le sélecteur de la vue)"));
      }
      o.addEventListener("mousedown", function (ev) { ev.preventDefault(); });
      o.addEventListener("click", function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        if (o.getAttribute("aria-disabled") === "true") return;
        fermerListe();
        Promise.resolve(m.ecrire(el, x.id)).then(function () {
          rafraichirPastille(el);
          W.setTimeout(function () { rafraichirPastille(el); }, 150);
        });
      });
      L.appendChild(o);
    });
    if (!l.length) {
      var v = D.createElement("div");
      v.className = "dzia-ovide";
      v.textContent = "aucun modèle";
      L.appendChild(v);
    }
    (D.body || D.documentElement).appendChild(L);
    b.setAttribute("aria-expanded", "true");
    ouverte = { node: L, b: b };
    placerListe();
  }
  /* la liste suit la pastille (défilement de l'hôte) ; elle se ferme si la
     pastille sort de l'écran ou disparaît */
  function placerListe() {
    if (!ouverte) return;
    var L = ouverte.node, b = ouverte.b;
    if (!b.isConnected) { fermerListe(); return; }
    var r = b.getBoundingClientRect(), iw = W.innerWidth || 1400, ih = W.innerHeight || 900;
    if (r.bottom < 0 || r.top > ih || (!r.width && !r.height)) { fermerListe(); return; }
    var lw = L.offsetWidth || 260, lh = L.offsetHeight || 200;
    var x0 = Math.max(4, Math.min(r.right - lw, iw - lw - 4));
    var y0 = r.bottom + 4 + lh > ih - 4 ? Math.max(4, r.top - 4 - lh) : r.bottom + 4;
    L.style.left = px(x0); L.style.top = px(y0);
  }
  function horsListe(ev) {
    if (!ouverte) return;
    var t = ev.target;
    if (t && t.nodeType === 1 && (ouverte.node.contains(t) || ouverte.b.contains(t))) return;
    fermerListe();
  }

  /* ─────────── T10 (27/09) : DICTÉE ───────────
     Voie 1 — `SpeechRecognition || webkitSpeechRecognition` : lang =
     documentElement.lang || fr-FR, résultats provisoires montrés dans la note,
     texte FINAL inséré au curseur (setter du prototype + événement `input`
     qui bouillonne : React voit la valeur). L'audio part au service du
     navigateur (Google pour Chrome), d'où le title du bouton.
     Voie 2 — si la voie 1 manque, ou sur l'erreur `network` /
     `service-not-allowed` (retenue pour la session) : MediaRecorder (patron
     D-26 du Montage), POST /api/dictation/estimate (gratuit), dialogue
     « Transcrire N s par X ≈ Y $ ? » (window.__dzDialogue de dialogue.js, sinon
     VL.dialogue du Vectorlab, sinon un dialogue maison titré) ; SEULEMENT sur
     Oui, POST /api/dictation avec max_usd = le montant affiché (le serveur
     refuse en 402 un coût recalculé au-delà). Sur Non : rien n'est envoyé.
     `available:false` → micro grisé en voie 2, title = la raison du serveur.
     Une seule dictée à la fois ; un champ retiré l'abandonne (rien n'est
     envoyé tant que l'accord n'est pas donné). */
  var TITRE_V1 = "Dicter — reconnaissance vocale du navigateur (l'audio part au service du navigateur)";
  var TITRE_V2 = "Dicter — enregistrement au micro, puis transcription par le serveur : durée et coût affichés, rien n'est envoyé sans votre accord";
  var TITRE_STOP = "Arrêter la dictée";
  var MIMES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/mp4"];
  var PRISE_MAX_S = 590;                         // le serveur refuse au-delà de 10 min
  var dic = { voie1Ko: "", indispo: "", active: null };
  var noteEl = null, tNote = 0;

  function ctorSR() { return W.SpeechRecognition || W.webkitSpeechRecognition || null; }
  function enregistreur() {
    var n = W.navigator;
    return !!(n && n.mediaDevices && typeof n.mediaDevices.getUserMedia === "function" && typeof W.MediaRecorder === "function");
  }
  function voieDictee() { return ctorSR() && !dic.voie1Ko ? 1 : enregistreur() ? 2 : 0; }
  function langue() {
    var h = D.documentElement;
    return String((h && (h.lang || (h.getAttribute && h.getAttribute("lang")))) || "") || "fr-FR";
  }
  function errMedia(e) {                         // dzmVoErr du Montage
    var n = e && typeof e === "object" ? String(e.name || "") : "";
    if (n === "NotAllowedError" || n === "SecurityError" || n === "PermissionDeniedError") return "accès au micro refusé";
    if (n === "NotFoundError" || n === "DevicesNotFoundError" || n === "OverconstrainedError") return "aucun micro détecté";
    if (n === "NotReadableError" || n === "TrackStartError") return "micro occupé par une autre application";
    var m = e && typeof e === "object" && e.message ? String(e.message) : typeof e === "string" ? e : "";
    return m || "erreur inconnue";
  }
  function errSR(code) {
    if (code === "not-allowed") return "Dictée : accès au micro refusé";
    if (code === "no-speech") return "Dictée : aucune parole entendue";
    if (code === "audio-capture") return "Dictée : aucun micro détecté";
    if (code === "aborted") return "";
    return "Dictée interrompue (" + (code || "erreur inconnue") + ")";
  }
  function usdTxt(v) { return (Number(v) || 0).toFixed(4).replace(".", ","); }

  /* la note d'état : une bulle fixe au-dessus du champ (une seule à la fois) */
  function placerNote() {
    var n = noteEl, el = n && n.__el;
    if (!n || !el) return;
    var r = el.getBoundingClientRect(), iw = W.innerWidth || 1400;
    var w = n.offsetWidth || 240, h = n.offsetHeight || 24;
    var x = Math.max(4, Math.min(r.right - w, iw - w - 4));
    var y = r.top - h - 6 < 4 ? r.bottom + 6 : r.top - h - 6;
    n.style.left = px(x); n.style.top = px(y);
  }
  function note(el, texte, tenue) {
    if (tNote) { W.clearTimeout(tNote); tNote = 0; }
    if (!texte) { if (noteEl && noteEl.parentNode) noteEl.parentNode.removeChild(noteEl); return; }
    if (!noteEl) {
      noteEl = D.createElement("div");
      noteEl.className = "dzia-note";
      noteEl.setAttribute("role", "status");
      noteEl.setAttribute("aria-live", "polite");
    }
    if (!noteEl.isConnected) (D.body || D.documentElement).appendChild(noteEl);
    noteEl.__el = el;
    noteEl.textContent = texte;
    placerNote();
    if (!tenue) tNote = W.setTimeout(function () { tNote = 0; if (noteEl && noteEl.parentNode) noteEl.parentNode.removeChild(noteEl); }, 7000);
  }

  function poserMicro(el, slot) {
    if (!slot) return null;
    var b = D.createElement("button");
    b.setAttribute("type", "button");
    b.className = "dzia-micro";
    b.setAttribute("data-dzia-micro", "1");
    b.setAttribute("title", TITRE_V1);
    var i = D.createElement("span");
    i.className = "dzia-mico";
    b.appendChild(i);
    b.addEventListener("mousedown", function (ev) { ev.preventDefault(); });   // le champ garde le focus et son curseur
    b.addEventListener("pointerdown", function (ev) { ev.stopPropagation(); }); // Vectorlab : pas un geste d'outil
    b.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); basculerDictee(el); });
    slot.appendChild(b);
    return b;
  }
  function rafraichirMicro(el) {
    var st = el.__dzia, b = st && st.micro;
    if (!b) return;
    var a = dic.active && dic.active.el === el ? dic.active : null;
    var e = a ? a.etat : "repos", v = voieDictee(), titre, txt = "", cls = "dzia-mico", dis = false, occupe = false;
    if (e === "ecoute" || e === "prise") { txt = "■"; cls = "dzia-mstop"; titre = TITRE_STOP; }
    else if (e !== "repos") {
      txt = "…"; cls = "dzia-mbusy"; occupe = true;
      titre = e === "micro" ? "Accès au micro en cours — autorisez-le dans le navigateur"
        : e === "estime" ? "Estimation de la durée et du coût de la transcription…"
        : e === "accord" ? "En attente de votre accord pour transcrire"
        : e === "envoi" ? "Transcription en cours…" : "Fin de la dictée…";
    }
    else if (v === 1) titre = TITRE_V1;
    else if (v === 2 && dic.indispo) { dis = true; titre = "Dictée indisponible — " + dic.indispo; }
    else if (v === 2) titre = TITRE_V2 + (dic.voie1Ko ? " (reconnaissance du navigateur indisponible : " + dic.voie1Ko + ")" : "");
    else { dis = true; titre = "Dictée indisponible : ce navigateur n'a ni reconnaissance vocale ni enregistreur audio ici (page non sûre ?)"; }
    var s = b.firstElementChild;
    if (s) {
      if (s.className !== cls) s.className = cls;
      if (s.textContent !== txt) s.textContent = txt;
    }
    poserAttr(b, "title", titre);
    poserAttr(b, "aria-label", titre);
    poserAttr(b, "aria-disabled", dis ? "true" : "false");
    poserAttr(b, "aria-busy", occupe ? "true" : "false");
    poserAttr(b, "aria-pressed", txt === "■" ? "true" : "false");
    poserAttr(b, "data-dzia-etat", e);
    poserAttr(b, "data-dzia-voie", String(a ? a.voie : v));
    var br = st.barre, on = e === "ecoute" || e === "prise";
    if (br && br.classList.contains("dzia-ecoute") !== on) br.classList.toggle("dzia-ecoute", on);
  }
  function rafraichirMicros() {
    for (var i = 0; i < suivis.length; i++) { try { rafraichirMicro(suivis[i]); } catch (e) {} }
  }

  /* le texte au CURSEUR, avec un espace de séparation si besoin, par le
     setter du prototype (React garde sinon son ancienne valeur) */
  function inserer(el, texte) {
    texte = String(texte || "").trim();
    if (!texte) return true;
    if (!el.isConnected) return false;
    var v = String(el.value == null ? "" : el.value), n = v.length;
    var s = typeof el.selectionStart === "number" ? el.selectionStart : n;
    var f = typeof el.selectionEnd === "number" ? el.selectionEnd : s;
    s = Math.max(0, Math.min(s, n)); f = Math.max(s, Math.min(f, n));
    var av = v.slice(0, s), ap = v.slice(f);
    var pre = av && !/\s$/.test(av) ? " " : "";
    var post = ap && !/^[\s.,;:!?…)\]]/.test(ap) ? " " : "";
    var nv = av + pre + texte + post + ap, pos = (av + pre + texte).length;
    var C = el.tagName === "TEXTAREA" ? W.HTMLTextAreaElement : W.HTMLInputElement;
    var d = C && C.prototype && Object.getOwnPropertyDescriptor(C.prototype, "value");
    if (d && d.set) d.set.call(el, nv); else el.value = nv;
    try { el.setSelectionRange(pos, pos); } catch (e) {}
    el.dispatchEvent(new W.Event("input", { bubbles: true }));
    return true;
  }

  function couperFlux(flux) {
    try { var t = flux && flux.getTracks ? flux.getTracks() : []; for (var i = 0; i < t.length; i++) { try { t[i].stop(); } catch (e) {} } } catch (e) {}
  }
  function finirDictee(a, message) {
    if (a.plafond) { W.clearTimeout(a.plafond); a.plafond = 0; }
    if (a.flux) { couperFlux(a.flux); a.flux = null; }
    if (dic.active === a) dic.active = null;
    a.etat = "fini";
    rafraichirMicro(a.el);
    note(a.el, message || "");
  }
  /* champ détaché : on abandonne SANS rien envoyer (sauf une transcription
     déjà acceptée, dont le texte sera dit dans la note) */
  function abandonnerDictee(el) {
    var a = dic.active;
    if (!a || a.el !== el || a.etat === "envoi") return;
    dic.active = null;
    if (a.sr) { try { a.sr.abort(); } catch (e) {} }
    if (a.rec) { try { a.rec.stop(); } catch (e) {} }
    finirDictee(a, "");
  }
  function arreterDictee() {
    var a = dic.active;
    if (!a) return;
    if (a.etat === "ecoute") {
      a.etat = "fin";
      rafraichirMicro(a.el);
      try { a.sr.stop(); } catch (e) { finirDictee(a, ""); return; }
      W.setTimeout(function () { if (dic.active === a) finirDictee(a, ""); }, 2500);   // onend manquant
    } else if (a.etat === "prise") {
      a.etat = "estime";
      rafraichirMicro(a.el);
      try { a.rec.stop(); } catch (e) { finirDictee(a, "Arrêt impossible : " + errMedia(e) + " — rien n'a été envoyé"); }
    }
  }
  function basculerDictee(el) {
    var a = dic.active, b = el.__dzia && el.__dzia.micro;
    if (a && a.el === el) {
      if (a.etat === "ecoute" || a.etat === "prise") arreterDictee();
      return;
    }
    if (a) { note(el, "Une dictée est déjà en cours dans un autre champ."); return; }
    if (b && b.getAttribute("aria-disabled") === "true") { note(el, b.getAttribute("title") || "Dictée indisponible"); return; }
    var v = voieDictee();
    if (v === 1) ecouter(el);
    else if (v === 2) enregistrer(el);
    else { rafraichirMicro(el); note(el, "Dictée indisponible : ni reconnaissance vocale ni enregistreur audio ici."); }
  }

  function ecouter(el) {
    var SR = ctorSR(), r;
    try { r = new SR(); } catch (e) { dic.voie1Ko = "reconnaissance refusée"; enregistrer(el); return; }
    r.lang = langue(); r.interimResults = true; r.continuous = true;
    var a = dic.active = { el: el, voie: 1, etat: "ecoute", sr: r };
    var ATTENTE = "À l'écoute… (clic ou Échap pour arrêter)";
    r.onresult = function (ev) {
      if (dic.active !== a) return;
      var fin = "", prov = "", l = (ev && ev.results) || [];
      for (var i = (ev && ev.resultIndex) || 0; i < l.length; i++) {
        var res = l[i], t = res && res[0] ? String(res[0].transcript || "") : "";
        if (res && res.isFinal) fin += (fin && t && !/^\s/.test(t) ? " " : "") + t; else prov += t;
      }
      if (fin.trim() && !inserer(el, fin)) { finirDictee(a, "Le champ a disparu — texte dicté : « " + fin.trim() + " »"); return; }
      if (a.etat === "ecoute") note(el, ATTENTE + (prov.trim() ? " — « " + prov.trim() + " »" : ""), true);
    };
    r.onerror = function (ev) {
      if (dic.active !== a) return;
      var code = String((ev && ev.error) || "");
      if (code === "network" || code === "service-not-allowed") {
        dic.voie1Ko = code;
        dic.active = null;
        try { r.abort(); } catch (e) {}
        enregistrer(el, "Reconnaissance du navigateur indisponible (" + code + ") — enregistrement local : ");
        return;
      }
      finirDictee(a, errSR(code));
    };
    r.onend = function () { if (dic.active === a) finirDictee(a, ""); };
    try { r.start(); } catch (e) { finirDictee(a, "Reconnaissance vocale impossible : " + errMedia(e)); return; }
    rafraichirMicro(el);
    note(el, ATTENTE, true);
  }

  function enregistrer(el, prefixe) {
    prefixe = prefixe || "";
    if (!enregistreur()) { rafraichirMicro(el); note(el, prefixe + "Micro indisponible : ce navigateur n'enregistre pas le son ici (page non sûre ou fonction absente)"); return; }
    if (dic.indispo) { rafraichirMicro(el); note(el, "Dictée indisponible — " + dic.indispo); return; }
    var a = dic.active = { el: el, voie: 2, etat: "micro" };
    rafraichirMicro(el);
    note(el, prefixe + "accès au micro…", true);
    var p;
    try { p = Promise.resolve(W.navigator.mediaDevices.getUserMedia({ audio: true })); } catch (e) { p = Promise.reject(e); }
    p.then(function (flux) {
      if (dic.active !== a) { couperFlux(flux); return; }
      a.flux = flux;
      var R = W.MediaRecorder, mime = "", i, rc, morceaux = [];
      if (typeof R.isTypeSupported === "function")
        for (i = 0; i < MIMES.length; i++) { try { if (R.isTypeSupported(MIMES[i])) { mime = MIMES[i]; break; } } catch (e) {} }
      try { rc = mime ? new R(flux, { mimeType: mime }) : new R(flux); }
      catch (e) { finirDictee(a, "Micro indisponible : " + errMedia(e)); return; }
      rc.ondataavailable = function (ev) { if (ev && ev.data && ev.data.size > 0) morceaux.push(ev.data); };
      rc.onstop = function () {
        if (a.flux) { couperFlux(a.flux); a.flux = null; }
        if (dic.active !== a) return;
        var type = mime || (morceaux[0] && morceaux[0].type) || "audio/webm";
        estimer(a, new W.Blob(morceaux, { type: type }), type);
      };
      rc.onerror = function (ev) { if (dic.active === a) finirDictee(a, "Enregistreur arrêté : " + errMedia(ev && ev.error ? ev.error : ev) + " — rien n'a été envoyé"); };
      a.rec = rc;
      try { rc.start(1000); }
      catch (e) { finirDictee(a, "Enregistrement impossible : " + errMedia(e)); return; }
      a.etat = "prise";
      a.plafond = W.setTimeout(function () { if (dic.active === a && a.etat === "prise") arreterDictee(); }, PRISE_MAX_S * 1000);
      rafraichirMicro(el);
      note(el, prefixe + "Enregistrement… (clic ou Échap pour arrêter) — la transcription vous sera proposée avec son coût", true);
    }, function (e) { if (dic.active === a) finirDictee(a, prefixe + "Micro indisponible : " + errMedia(e)); });
  }

  function lireReponse(r) {
    return Promise.resolve(r.json()).then(null, function () { return null; }).then(function (j) {
      if (r.ok && j) return j;
      var d = j && j.detail, m = typeof d === "string" ? d : d ? JSON.stringify(d) : "";
      throw new Error((m || "réponse illisible") + " (HTTP " + r.status + ")");
    });
  }
  function demanderAccord(message) {
    var o = { titre: "Dictée", ok: "Oui, transcrire", annuler: "Non" };
    try {
      var dz = W.__dzDialogue;
      if (dz && typeof dz.confirmer === "function") return Promise.resolve(dz.confirmer(message, o)).then(function (x) { return x === true; });
      var vl = W.VL && W.VL.dialogue;
      if (vl && typeof vl.confirmer === "function") return Promise.resolve(vl.confirmer(message, o)).then(function (x) { return x === true; });
    } catch (e) {}
    return dialogueMaison(message, o);
  }
  function dialogueMaison(message, o) {
    return new Promise(function (resoudre) {
      var v = D.createElement("div");
      v.className = "dzia-dlg";
      v.setAttribute("role", "dialog");
      v.setAttribute("aria-modal", "true");
      v.setAttribute("aria-label", o.titre);
      var bt = D.createElement("div"); bt.className = "dzia-dlg-boite";
      var te = D.createElement("div"); te.className = "dzia-dlg-tete"; te.textContent = o.titre;
      var co = D.createElement("div"); co.className = "dzia-dlg-corps"; co.textContent = message;
      var pi = D.createElement("div"); pi.className = "dzia-dlg-pied";
      var fini = false, clavier;
      function fin(oui) {
        if (fini) return;
        fini = true;
        D.removeEventListener("keydown", clavier, true);
        if (v.parentNode) v.parentNode.removeChild(v);
        resoudre(oui);
      }
      clavier = function (ev) {
        if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(false); }
        else if (ev.key === "Enter") { ev.preventDefault(); ev.stopPropagation(); fin(true); }
      };
      [["non", o.annuler, "Ne rien envoyer : la prise est abandonnée"],
       ["oui", o.ok, "Envoyer la prise au service de transcription, au coût affiché"]].forEach(function (x) {
        var b = D.createElement("button");
        b.setAttribute("type", "button");
        b.setAttribute("data-role", x[0]);
        b.setAttribute("title", x[2]);
        b.textContent = x[1];
        b.addEventListener("click", function () { fin(x[0] === "oui"); });
        pi.appendChild(b);
      });
      bt.appendChild(te); bt.appendChild(co); bt.appendChild(pi); v.appendChild(bt);
      v.addEventListener("click", function (ev) { if (ev.target === v) fin(false); });
      (D.body || D.documentElement).appendChild(v);
      D.addEventListener("keydown", clavier, true);
      var oui = pi.querySelector ? pi.querySelector('[data-role="oui"]') : null;
      try { if (oui) oui.focus(); } catch (e) {}
    });
  }
  function estimer(a, blob, type) {
    var el = a.el;
    if (!blob || !blob.size) { finirDictee(a, "Prise vide : aucun son enregistré — rien n'a été envoyé"); return; }
    a.etat = "estime";
    rafraichirMicro(el);
    note(el, "Estimation de la durée et du coût…", true);
    var nom = "dictee." + (/ogg/.test(type) ? "ogg" : /mp4/.test(type) ? "m4a" : "webm");
    var f1 = new W.FormData();
    f1.append("file", blob, nom);
    W.fetch("/api/dictation/estimate", { method: "POST", body: f1 }).then(lireReponse).then(function (d) {
      if (dic.active !== a) return null;
      if (!d.available) {
        dic.indispo = String(d.reason || "transcription indisponible");
        finirDictee(a, "Dictée indisponible — " + dic.indispo);
        rafraichirMicros();
        return null;
      }
      var usd = Number(d.usd) || 0;
      var msg = "Transcrire " + Math.max(1, Math.round(Number(d.duration_s) || 0)) + " s par " + (d.label || d.provider || "le service")
        + " ≈ " + usdTxt(usd) + " $ ?";
      a.etat = "accord";
      rafraichirMicro(el);
      note(el, "", false);
      return demanderAccord(msg).then(function (oui) {
        if (dic.active !== a) return null;
        if (!oui) { finirDictee(a, "Dictée abandonnée : rien n'a été envoyé."); return null; }
        a.etat = "envoi";
        rafraichirMicro(el);
        note(el, "Transcription en cours (" + usdTxt(usd) + " $ au plus)…", true);
        var f2 = new W.FormData();
        f2.append("file", blob, nom);
        f2.append("max_usd", String(usd));
        f2.append("language", langue());
        return W.fetch("/api/dictation", { method: "POST", body: f2 }).then(lireReponse).then(function (r) {
          var t = String((r && r.text) || "").trim(), cout = usdTxt(r && r.usd != null ? r.usd : usd);
          if (!t) { finirDictee(a, "Transcription vide : aucun mot reconnu (" + cout + " $)."); return null; }
          finirDictee(a, inserer(el, t) ? "Transcrit — " + cout + " $ (" + (d.label || r.provider || "") + ")."
            : "Le champ a disparu — texte transcrit : « " + t + " »");
          return null;
        });
      });
    }).then(null, function (e) {
      if (dic.active === a) finirDictee(a, "Dictée : " + (e && e.message ? e.message : String(e)));
    });
  }

  W.DzChampIA = {
    version: VERSION,
    genres: GENRES.slice(),
    regles: REGLES,
    exclus: ZONES.concat(EXCLUS),
    marquer: marquer,
    synchroniser: synchroniser,
    modeles: { catalogueImage: CATALOGUE_IMAGE, charger: charger, rafraichir: rafraichirPastilles, fermer: fermerListe },
    dictee: {
      voie: voieDictee,
      etat: function () { var a = dic.active; return { etat: a ? a.etat : "repos", voie: a ? a.voie : voieDictee(), voie1Ko: dic.voie1Ko, indispo: dic.indispo }; },
      arreter: arreterDictee
    }
  };
  if (D.body) demarrer();
  else D.addEventListener("DOMContentLoaded", demarrer);
})();
