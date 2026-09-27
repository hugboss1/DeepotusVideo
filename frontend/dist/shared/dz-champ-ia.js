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
   « IA » + emplacements vides `data-dzia-slot="modele"` (T9) et `"micro"`
   (T10)) est un frère ABSOLU posé juste après le champ, recalé sur son coin
   droit ; une réserve de padding (champs border-box seulement) empêche le
   texte de passer dessous. Le parent statique devient `position:relative`
   seulement s'il n'a aucun descendant absolu (sinon la barre se recale au
   défilement). */
(function () {
  "use strict";
  var W = window, D = document;
  if (W.DzChampIA) return;

  var VERSION = "1.0.0";
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
    "@media (prefers-reduced-motion:reduce){" +
      ".dzia-lis.dzia-lis,.dzia-lis.dzia-lis:focus-within{animation:none!important;--dzia-ang:200deg;transition:none}" +
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
    D.addEventListener("focusout", planifierSync, true);
    D.addEventListener("scroll", planifierSync, true);
    W.setInterval(function () { if (!D.hidden) synchroniser(); }, 800);
  }

  W.DzChampIA = {
    version: VERSION,
    genres: GENRES.slice(),
    regles: REGLES,
    exclus: ZONES.concat(EXCLUS),
    marquer: marquer,
    synchroniser: synchroniser
  };
  if (D.body) demarrer();
  else D.addEventListener("DOMContentLoaded", demarrer);
})();
