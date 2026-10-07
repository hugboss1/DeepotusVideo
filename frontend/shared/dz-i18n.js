/* dz-i18n.js — LA LANGUE DE L'INTERFACE (t134, traduction lot 0, 07/10/2026).
   SOURCE : frontend/shared/dz-i18n.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-i18n.js, servie à
   /shared/dz-i18n.js, chargée par une balise classique APRÈS /shared/dz-i18n-dico.js (le dictionnaire assemblé,
   window.DZ_I18N) et AVANT le bundle et les modules des labs, dans la SPA et les huit pages à part.
   Banc : backend/tests/test_i18n_l0.py.

   Le français est la langue de RÉFÉRENCE (décision de l'utilisateur, 07/10) : chaque clé a son texte français, et
   l'anglais en est la traduction. Langue affichée, dans l'ordre : la bascule des Réglages (localStorage dz_lang),
   puis le choix fait à l'INSTALLATION (UI_LANG du .env, lu par /api/health et recopié dans dz_lang_install pour être
   lu sans attendre le réseau au chargement suivant), puis fr. Le premier lancement d'une installation anglaise
   recharge donc la page UNE fois — ensuite la valeur est connue avant le premier rendu.

   Deux temps : les écrans migrés appellent dzT("zone.objet.role") ; les autres, encore écrits en dur, passent par
   la SURCOUCHE, qui remplace à l'affichage un texte français dont le texte EXACT (espaces normalisés) est connu du
   dictionnaire — jamais une phrase à moitié, jamais dans un champ saisi, un bloc de code ou un [data-dz-brut].
   Aucun état React : une bascule recharge la page (les compteurs figés du bundle, x.useState, ne bougent pas). */
(function () {
  if (window.__dzI18n) return;
  var LANGUES = ["fr", "en"];
  var D = window.DZ_I18N || {};

  function lire(k) {
    try { return window.localStorage.getItem(k); } catch (e) { return null; }
  }
  function ecrire(k, v) {
    try { window.localStorage.setItem(k, v); } catch (e) { /* stockage indisponible : la langue reviendra au défaut */ }
  }
  function borne(l) { return LANGUES.indexOf(l) >= 0 ? l : null; }

  var choisie = borne(lire("dz_lang"));
  var lang = choisie || borne(lire("dz_lang_install")) || "fr";
  try { document.documentElement.lang = lang; } catch (e) { /* pas de document : rien à poser */ }

  var averties = {};
  function dzT(cle, vars) {
    var e = D[cle];
    var s = e ? (e[lang] || e.fr) : null;
    if (s == null) {
      if (!averties[cle]) {
        averties[cle] = 1;
        try { console.warn("dzT : clé absente du dictionnaire : " + cle); } catch (x) { /* console absente */ }
      }
      return cle;
    }
    if (vars) s = s.replace(/\{(\w+)\}/g, function (m, n) { return vars[n] != null ? String(vars[n]) : m; });
    return s;
  }

  // ── la surcouche : français exact -> anglais ──
  function norm(s) { return String(s).replace(/\s+/g, " ").trim(); }
  var INDEX = null;
  function index() {
    if (INDEX) return INDEX;
    INDEX = {};
    for (var k in D) {
      if (Object.prototype.hasOwnProperty.call(D, k) && D[k] && D[k].fr && D[k].en) INDEX[norm(D[k].fr)] = D[k].en;
    }
    return INDEX;
  }
  function traduire(s) {
    if (lang !== "en" || s == null) return null;
    var n = norm(s);
    if (!n || !Object.prototype.hasOwnProperty.call(index(), n)) return null;
    return /^\s*/.exec(s)[0] + index()[n] + /\s*$/.exec(s)[0];
  }

  var TEXTE_EXCLU = /^(INPUT|TEXTAREA|SELECT|OPTION|SCRIPT|STYLE|CODE|PRE|NOSCRIPT|KBD|SAMP)$/;
  var ATTRS = ["title", "placeholder", "aria-label"];
  function brut(el) {
    for (var e = el; e && e.nodeType === 1; e = e.parentNode) {
      if (e.isContentEditable || (e.hasAttribute && e.hasAttribute("data-dz-brut"))) return true;
    }
    return false;
  }
  function texteExclu(el) {
    for (var e = el; e && e.nodeType === 1; e = e.parentNode) {
      if (TEXTE_EXCLU.test(e.nodeName)) return true;
    }
    return brut(el);
  }
  var ecrits = typeof WeakMap === "function" ? new WeakMap() : null;
  function surTexte(n) {
    var v = n.data;
    if (ecrits && ecrits.get(n) === v) return;
    var t = traduire(v);
    if (t == null || texteExclu(n.parentNode)) return;
    if (ecrits) ecrits.set(n, t);
    n.data = t;
  }
  function surAttrs(el) {
    if (!el.getAttribute || brut(el)) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var v = el.getAttribute(ATTRS[i]);
      if (v == null) continue;
      var t = traduire(v);
      if (t != null) el.setAttribute(ATTRS[i], t);
    }
  }
  function parcourir(racine) {
    if (!racine) return;
    if (racine.nodeType === 3) { surTexte(racine); return; }
    if (racine.nodeType !== 1) return;
    surAttrs(racine);
    var w = document.createTreeWalker(racine, 5 /* SHOW_ELEMENT | SHOW_TEXT */);
    for (var n = w.nextNode(); n; n = w.nextNode()) {
      if (n.nodeType === 3) surTexte(n); else surAttrs(n);
    }
  }
  function dzI18nSurcouche() {
    if (lang !== "en" || typeof MutationObserver !== "function") return false;
    new MutationObserver(function (ms) {
      for (var i = 0; i < ms.length; i++) {
        var m = ms[i];
        if (m.type === "childList") {
          for (var j = 0; j < m.addedNodes.length; j++) parcourir(m.addedNodes[j]);
        } else if (m.type === "characterData") {
          surTexte(m.target);
        } else if (m.type === "attributes") {
          surAttrs(m.target);
        }
      }
    }).observe(document.documentElement, { subtree: true, childList: true, characterData: true,
                                            attributes: true, attributeFilter: ATTRS });
    var tout = function () { parcourir(document.body); parcourir(document.head && document.querySelector("title")); };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", tout);
    else tout();
    return true;
  }

  // ── la langue part avec chaque requête /api/ (messages d'erreur du serveur), sans écraser un en-tête posé ──
  var f0 = window.fetch;
  function versApi(u) {
    var o = (window.location && window.location.origin) || "";
    return u.indexOf("/api/") === 0 || (o && u.indexOf(o + "/api/") === 0);
  }
  if (typeof f0 === "function") {
    window.fetch = function (entree, init) {
      try {
        var u = typeof entree === "string" ? entree : (entree && entree.url) || "";
        if (typeof entree === "string" && versApi(u)) {
          init = init ? Object.assign({}, init) : {};
          var h = init.headers;
          if (h && typeof h.has === "function") {
            if (!h.has("Accept-Language")) { h = new Headers(h); h.set("Accept-Language", lang); }
          } else {
            h = Object.assign({}, h || {});
            var deja = false;
            for (var k in h) if (k.toLowerCase() === "accept-language") deja = true;
            if (!deja) h["Accept-Language"] = lang;
          }
          init.headers = h;
        }
      } catch (e) { /* jamais de requête perdue pour un en-tête */ }
      return f0.call(this, entree, init);
    };
  }

  function dzSetLang(l) {
    l = borne(l);
    if (!l) return;
    ecrire("dz_lang", l);
    try { window.location.reload(); } catch (e) { /* rien à recharger */ }
  }

  // ── le choix de l'installation : relu à chaque chargement tant que la bascule n'a rien dit ──
  if (!choisie && typeof f0 === "function") {
    try {
      f0.call(window, "/api/health").then(function (r) { return r && r.ok ? r.json() : null; }).then(function (d) {
        var l = borne(d && d.ui_lang);
        if (!l) return;
        var avant = borne(lire("dz_lang_install"));
        ecrire("dz_lang_install", l);
        if (l !== lang && l !== avant) { try { window.location.reload(); } catch (e) { /* rien */ } }
      }).catch(function () { /* serveur pas prêt : la valeur connue reste */ });
    } catch (e) { /* rien */ }
  }

  window.dzT = dzT;
  window.dzLang = function () { return lang; };
  window.dzSetLang = dzSetLang;
  window.dzI18nSurcouche = dzI18nSurcouche;
  window.__dzI18n = { traduire: traduire, langue: lang, surcouche: dzI18nSurcouche() };
})();
