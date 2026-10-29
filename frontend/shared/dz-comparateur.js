/* dz-comparateur.js — le COMPARATEUR commun (t337, C4 du lot Scenario, 29/10/2026, spec
   docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne C4). SOURCE : frontend/shared/dz-comparateur.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-comparateur.js, servie à /shared/dz-comparateur.js. Bancs :
   frontend/shared/qa/comparateur.test.mjs (comportement, DOM simulé) et backend/tests/test_revue_plan_ecran.py
   (copie, balises, textes FR/EN).

   Deux médias côte à côte sous un RIDEAU glissant (wipe) : A à gauche (l'original : avant, previs, référence…), B à
   droite (le résultat : après, rendu, autre moteur…). Images ET vidéos (deux vidéos restent synchronisées).
     window.__dzComparateur.ouvrir({a: {src, type?, libelle?}, b: {…}, titre?, fps?, position?}) -> Promise (fermé)
     window.__dzComparateur.monter(hote, opts) -> {detruire(), mode(m?), position(p?), pas(n), etat()}
   `type` : "image" | "video" (déduit de l'extension sinon) ; `fps` : la cadence du pas à pas (24 par défaut) ;
   `position` : la place du rideau, de 0 à 100 (50).
   CLAVIER (dans la boîte, hors champ de saisie) : O = l'original (A seul, plein cadre), C = comparer (le rideau
   revient), ← / → = une image en arrière / en avant (vidéo, lecture en pause), Maj + ← / → = rideau de 5 %,
   Espace = lecture / pause (vidéo), Échap = fermer. Le curseur du rideau est un <input type="range"> : il se règle
   aussi aux flèches quand il a le focus. Glisser sur l'image déplace le rideau (pointeur capturé).
   CHARTE : celle de dialogue.js / dz-previs-plan.js (aucun arrondi, en-tête IBM Plex Mono en capitales, jetons
   --srf-* / --brd-* / --txt-* avec replis). Textes : clés comparateur.* (frontend/shared/i18n/comparateur.json).
   Vanilla DOM, aucun innerHTML. */
(function () {
  "use strict";
  if (window.__dzComparateur) return;

  var EXT_VIDEO = /\.(mp4|webm|mov|m4v|mkv)(\?|#|$)/i;
  var PAS_RIDEAU = 5;
  var S = {
    voile: "position:fixed;inset:0;z-index:9990;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center",
    boite: "position:relative;width:min(1100px,96vw);max-height:94vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "display:flex;align-items:center;gap:8px;padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    racine: "display:flex;flex-direction:column;gap:8px;min-height:0",
    scene: "position:relative;align-self:center;max-width:100%;max-height:68vh;overflow:hidden;background:#000;cursor:ew-resize;touch-action:none;user-select:none;border:1px solid var(--brd-soft,var(--stroke,#222830))",
    media: "display:block;max-width:100%;max-height:68vh;object-fit:contain;pointer-events:none",
    dessus: "position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none",
    ligne: "position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;background:var(--accent,#2b6fd6);pointer-events:none",
    etiq: "position:absolute;top:6px;padding:2px 6px;background:rgba(0,0,0,.65);color:#e6e9ee;font:10px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase;pointer-events:none",
    barre: "display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:0 14px",
    curseur: "flex:1 1 220px;min-width:160px;accent-color:var(--accent,#2b6fd6)",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    btn: "min-width:0;height:28px;padding:0 10px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;display:inline-flex;align-items:center;gap:6px",
    actif: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    corps: "padding:12px 0;overflow:auto;display:flex;flex-direction:column;gap:8px",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))"
  };
  var courant = null;

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  function glyphe(id) {
    var ns = "http://www.w3.org/2000/svg";
    if (!document.createElementNS) return null;
    var s = document.createElementNS(ns, "svg");
    s.setAttribute("class", "dzi dzi--16"); s.setAttribute("aria-hidden", "true"); s.setAttribute("focusable", "false"); s.setAttribute("width", "16"); s.setAttribute("height", "16");
    var u = document.createElementNS(ns, "use");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + id);
    s.appendChild(u);
    return s;
  }
  function bouton(marque, texte, ico, titre) {
    var b = el("button", { type: "button", "data-dz-cmp": marque, style: S.btn });
    var g = ico ? glyphe(ico) : null;
    if (g) b.appendChild(g);
    b.appendChild(el("span", {}, texte));
    if (titre) { b.setAttribute("title", titre); b.setAttribute("aria-label", titre); }
    return b;
  }
  function borne(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function typeDe(m) { return m && (m.type === "video" || m.type === "image") ? m.type : (EXT_VIDEO.test(String(m && m.src || "")) ? "video" : "image"); }
  function champ(t) {
    var n = t && t.tagName ? String(t.tagName).toUpperCase() : "";
    return n === "TEXTAREA" || n === "SELECT" || (n === "INPUT" && String(t.type || (t.getAttribute && t.getAttribute("type")) || "").toLowerCase() !== "range") || !!(t && t.isContentEditable);
  }

  /* le cœur : monté dans `hote`, sans voile ; ouvrir() l'emballe dans une boîte */
  function monter(hote, opts) {
    opts = opts || {};
    var A = opts.a || {}, Bm = opts.b || {};
    var E = { mode: "comparer", pos: borne(Number(opts.position == null ? 50 : opts.position) || 0, 0, 100),
              fps: Number(opts.fps) > 0 ? Number(opts.fps) : 24, video: typeDe(A) === "video" || typeDe(Bm) === "video",
              glisse: false, morts: [] };
    var racine = E.racine = el("div", { "class": "dz-cmp", style: S.racine, "data-dz-cmp": "racine",
                                        role: "group", "aria-label": T("comparateur.boite.aide") });
    var scene = E.scene = el("div", { style: S.scene, "data-dz-cmp": "scene" });
    function media(m, dessus, marque) {
      var v = typeDe(m) === "video";
      var n = el(v ? "video" : "img", { src: String(m.src || ""), "data-dz-cmp": marque,
                                         style: dessus ? S.dessus : S.media });
      if (v) { n.setAttribute("muted", ""); n.setAttribute("playsinline", ""); n.setAttribute("preload", "auto"); n.muted = true; }
      else n.setAttribute("alt", m.libelle || "");
      return n;
    }
    E.mA = media(A, false, "a");
    E.mB = media(Bm, true, "b");
    E.trait = el("span", { style: S.ligne, "aria-hidden": "true", "data-dz-cmp": "ligne" });
    E.etA = el("span", { style: S.etiq + ";left:6px", "data-dz-cmp": "etiquette-a" }, A.libelle || T("comparateur.boite.original"));
    E.etB = el("span", { style: S.etiq + ";right:6px", "data-dz-cmp": "etiquette-b" }, Bm.libelle || T("comparateur.boite.resultat"));
    [E.mA, E.mB, E.trait, E.etA, E.etB].forEach(function (n) { scene.appendChild(n); });
    racine.appendChild(scene);

    var barre = el("div", { style: S.barre });
    E.curseur = el("input", { type: "range", min: "0", max: "100", step: "1", value: String(E.pos), style: S.curseur,
                              "data-dz-cmp": "curseur", "aria-label": T("comparateur.rideau.libelle") });
    E.curseur.addEventListener("input", function () { poser(E, Number(E.curseur.value)); });
    E.bO = bouton("original", T("comparateur.mode.original"), null, T("comparateur.mode.original_t"));
    E.bC = bouton("comparer", T("comparateur.mode.comparer"), "dz-action-comparer", T("comparateur.mode.comparer_t"));
    E.bO.addEventListener("click", function () { mode(E, "original"); });
    E.bC.addEventListener("click", function () { mode(E, "comparer"); });
    barre.appendChild(E.bO); barre.appendChild(E.bC); barre.appendChild(E.curseur);
    if (E.video) {
      E.bPrec = bouton("precedente", T("comparateur.video.precedente"), "dz-media-image-precedente", T("comparateur.video.precedente_t"));
      E.bLire = bouton("lecture", T("comparateur.video.lire"), "dz-media-lecture", T("comparateur.video.lire_t"));
      E.bSuiv = bouton("suivante", T("comparateur.video.suivante"), "dz-media-image-suivante", T("comparateur.video.suivante_t"));
      E.bPrec.addEventListener("click", function () { pas(E, -1); });
      E.bSuiv.addEventListener("click", function () { pas(E, 1); });
      E.bLire.addEventListener("click", function () { lecture(E); });
      E.compteur = el("span", { style: S.note, "data-dz-cmp": "compteur", "aria-live": "polite" });
      [E.bPrec, E.bLire, E.bSuiv, E.compteur].forEach(function (n) { barre.appendChild(n); });
      // la vidéo B suit A : un écart de plus d'une demi-image se rattrape (lecture), le compteur suit
      E.mA.addEventListener("timeupdate", function () { suivre(E); });
      E.mA.addEventListener("ended", function () { arreter(E); });
    }
    racine.appendChild(barre);
    racine.appendChild(el("div", { style: S.note + ";padding:0 14px", "data-dz-cmp": "aide" },
                          T(E.video ? "comparateur.boite.raccourcis_video" : "comparateur.boite.raccourcis")));

    function deplacer(ev) {
      var r = scene.getBoundingClientRect ? scene.getBoundingClientRect() : null;
      if (!r || !r.width) return;
      if (E.mode !== "comparer") mode(E, "comparer");
      poser(E, (Number(ev.clientX) - r.left) / r.width * 100);
    }
    scene.addEventListener("pointerdown", function (ev) {
      E.glisse = true;
      if (scene.setPointerCapture && ev.pointerId != null) { try { scene.setPointerCapture(ev.pointerId); } catch (e) { /* rien */ } }
      deplacer(ev);
    });
    scene.addEventListener("pointermove", function (ev) { if (E.glisse) deplacer(ev); });
    ["pointerup", "pointercancel"].forEach(function (t) { scene.addEventListener(t, function () { E.glisse = false; }); });

    E.touche = function (ev) { touche(E, ev); };
    racine.addEventListener("keydown", E.touche);
    hote.appendChild(racine);
    poser(E, E.pos);
    mode(E, "comparer");
    majCompteur(E);
    return {
      racine: racine,
      detruire: function () { arreter(E); if (racine.parentNode) racine.parentNode.removeChild(racine); },
      mode: function (m) { if (m) mode(E, m); return E.mode; },
      position: function (p) { if (p != null) poser(E, p); return E.pos; },
      pas: function (n) { pas(E, n); },
      touche: E.touche,
      etat: function () { return { mode: E.mode, position: E.pos, video: E.video, fps: E.fps, image: image(E) }; }
    };
  }

  function poser(E, p) {
    E.pos = Math.round(borne(Number(p) || 0, 0, 100) * 10) / 10;
    E.mB.style.clipPath = "inset(0 0 0 " + E.pos + "%)";
    E.trait.style.left = E.pos + "%";
    E.curseur.value = String(Math.round(E.pos));
    E.curseur.setAttribute("aria-valuetext", T("comparateur.rideau.valeur", { p: Math.round(E.pos) }));
  }

  function mode(E, m) {
    E.mode = m === "original" ? "original" : "comparer";
    var orig = E.mode === "original";
    if (orig) E.mB.setAttribute("hidden", ""); else E.mB.removeAttribute("hidden");
    E.mB.style.visibility = orig ? "hidden" : "";
    E.trait.style.visibility = orig ? "hidden" : "";
    E.etB.style.visibility = orig ? "hidden" : "";
    if (orig) E.curseur.setAttribute("disabled", ""); else E.curseur.removeAttribute("disabled");
    E.bO.setAttribute("aria-pressed", String(orig));
    E.bC.setAttribute("aria-pressed", String(!orig));
    E.bO.setAttribute("style", S.btn + (orig ? ";" + S.actif : ""));
    E.bC.setAttribute("style", S.btn + (orig ? "" : ";" + S.actif));
    E.racine.setAttribute("data-mode", E.mode);
  }

  function videos(E) { return [E.mA, E.mB].filter(function (n) { return String(n.tagName).toUpperCase() === "VIDEO"; }); }
  function image(E) {
    if (!E.video) return null;
    return Math.floor((Number(videos(E)[0].currentTime) || 0) * E.fps + 1e-6);
  }
  function majCompteur(E) {
    if (!E.compteur) return;
    var v = videos(E)[0], n = image(E), tot = Number(v.duration) > 0 ? Math.round(Number(v.duration) * E.fps) : null;
    E.compteur.textContent = tot ? T("comparateur.video.image_sur", { n: n + 1, total: tot }) : T("comparateur.video.image", { n: n + 1 });
  }
  function arreter(E) {
    if (!E.video) return;
    videos(E).forEach(function (v) { try { v.pause(); } catch (e) { /* rien */ } });
    E.lit = false;
    if (E.bLire) E.bLire.lastChild.textContent = T("comparateur.video.lire");
  }
  function lecture(E) {
    if (!E.video) return;
    if (E.lit) { arreter(E); majCompteur(E); return; }
    E.lit = true;
    var t = Number(videos(E)[0].currentTime) || 0;
    videos(E).forEach(function (v) { v.currentTime = t; var p = v.play && v.play(); if (p && p.catch) p.catch(function () {}); });
    if (E.bLire) E.bLire.lastChild.textContent = T("comparateur.video.pause");
  }
  function suivre(E) {
    var vs = videos(E);
    if (vs.length === 2 && Math.abs((Number(vs[1].currentTime) || 0) - (Number(vs[0].currentTime) || 0)) > 0.5 / E.fps) {
      vs[1].currentTime = vs[0].currentTime;
    }
    majCompteur(E);
  }
  /* une image en avant (n = 1) ou en arrière (n = -1) : la lecture s'arrête, les deux vidéos posées au MÊME instant,
     au milieu de l'image visée (un currentTime pile sur une frontière d'image tombe parfois sur la précédente) */
  function pas(E, n) {
    if (!E.video) return;
    arreter(E);
    var vs = videos(E), v = vs[0];
    var dur = Number(v.duration) > 0 ? Number(v.duration) : Infinity;
    var dernier = isFinite(dur) ? Math.max(0, Math.round(dur * E.fps) - 1) : Infinity;
    var cible = borne(image(E) + (n < 0 ? -1 : 1) * Math.max(1, Math.abs(n | 0)), 0, dernier);
    var t = (cible + 0.5) / E.fps;
    vs.forEach(function (x) { x.currentTime = t; });
    majCompteur(E);
  }

  function touche(E, ev) {
    if (!ev || ev.defaultPrevented || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (champ(ev.target)) return;
    var k = ev.key, surCurseur = ev.target === E.curseur;
    var fait = true;
    if (k === "o" || k === "O") mode(E, "original");
    else if (k === "c" || k === "C") mode(E, "comparer");
    else if ((k === "ArrowLeft" || k === "ArrowRight") && ev.shiftKey) { mode(E, "comparer"); poser(E, E.pos + (k === "ArrowLeft" ? -PAS_RIDEAU : PAS_RIDEAU)); }
    else if ((k === "ArrowLeft" || k === "ArrowRight") && E.video && !surCurseur) pas(E, k === "ArrowLeft" ? -1 : 1);
    else if ((k === " " || k === "Spacebar") && E.video && String(ev.target && ev.target.tagName || "").toUpperCase() !== "BUTTON") lecture(E);
    else fait = false;
    if (fait) { ev.preventDefault(); if (ev.stopPropagation) ev.stopPropagation(); }
  }

  function fermer(B, valeur) {
    if (!B || B.ferme) return;
    B.ferme = true;
    document.removeEventListener("keydown", B.clavier, true);
    B.cmp.detruire();
    if (B.voile.parentNode) B.voile.parentNode.removeChild(B.voile);
    if (B.retour && B.retour.focus) { try { B.retour.focus(); } catch (e) { /* rien */ } }
    if (courant === B) courant = null;
    B.resoudre(valeur);
  }

  function ouvrir(opts) {
    opts = opts || {};
    if (!opts.a || !opts.b || !opts.a.src || !opts.b.src) return Promise.resolve(null);
    if (courant) fermer(courant, null);
    return new Promise(function (resoudre) {
      var B = { resoudre: resoudre, ferme: false, retour: document.activeElement || null };
      courant = B;
      var voile = B.voile = el("div", { style: S.voile, role: "dialog", "aria-modal": "true", "class": "dz-comparateur",
                                        "data-dz-cmp": "voile", "aria-label": opts.titre || T("comparateur.boite.titre") });
      voile.appendChild(el("style", {}, ".dz-comparateur [hidden]{display:none!important}"));
      var boite = el("div", { style: S.boite });
      boite.appendChild(el("div", { style: S.tete }, opts.titre || T("comparateur.boite.titre")));
      var corps = el("div", { style: S.corps });
      boite.appendChild(corps);
      B.cmp = monter(corps, opts);
      B.cmp.racine.setAttribute("tabindex", "-1");
      var pied = el("div", { style: S.pied });
      var f = bouton("fermer", T("comparateur.boite.fermer"), "dz-action-fermer");
      f.addEventListener("click", function () { fermer(B, null); });
      pied.appendChild(f);
      boite.appendChild(pied);
      voile.appendChild(boite);
      voile.addEventListener("click", function (ev) { if (ev.target === voile) fermer(B, null); });
      // le clavier de la boîte : Échap ferme ; les raccourcis du comparateur valent partout dans la boîte
      B.clavier = function (ev) {
        if (ev.key === "Escape") { ev.preventDefault(); if (ev.stopPropagation) ev.stopPropagation(); fermer(B, null); return; }
        B.cmp.touche(ev);
      };
      document.addEventListener("keydown", B.clavier, true);
      document.body.appendChild(voile);
      if (B.cmp.racine.focus) { try { B.cmp.racine.focus(); } catch (e) { /* rien */ } }
    });
  }

  window.__dzComparateur = { ouvrir: ouvrir, monter: monter, ouvert: function () { return !!courant; }, fermer: function () { if (courant) fermer(courant, null); } };
})();
