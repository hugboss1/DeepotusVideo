/* Guide Deepotus v3 — comportements de la page (aucune dépendance, marche en file:// comme sous /guide/). */
(function () {
  "use strict";
  var doc = document, html = doc.documentElement;
  var LANG = html.lang === "en" ? "en" : "fr";
  var T = {
    fr: { aucun: "Aucun résultat pour « {q} ».", pause: "Pause", lire: "Lire", sombre: "Thème sombre", clair: "Thème clair" },
    en: { aucun: "No result for “{q}”.", pause: "Pause", lire: "Play", sombre: "Dark theme", clair: "Light theme" }
  }[LANG];
  function $(s, r) { return (r || doc).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || doc).querySelectorAll(s)); }
  function lire(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function ecrire(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* stockage indisponible : sans mémoire */ } }

  /* ── thème ─────────────────────────────────────────────────────────── */
  var theme = lire("dz_guide_theme");
  if (theme === "light" || theme === "dark") html.setAttribute("data-theme", theme);
  function sombre() {
    var t = html.getAttribute("data-theme");
    return t ? t === "dark" : window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
  }
  var bTheme = $("#g-theme");
  function majTheme() { if (bTheme) bTheme.title = sombre() ? T.clair : T.sombre; }
  if (bTheme) bTheme.addEventListener("click", function () {
    var t = sombre() ? "light" : "dark";
    html.setAttribute("data-theme", t); ecrire("dz_guide_theme", t); majTheme();
  });
  majTheme();

  /* ── tiroir du sommaire (étroit) ───────────────────────────────────── */
  var bMenu = $("#g-menu");
  if (bMenu) bMenu.addEventListener("click", function () {
    var o = doc.body.classList.toggle("nav-ouverte"); bMenu.setAttribute("aria-expanded", String(o));
  });
  $$(".g-nav a").forEach(function (a) { a.addEventListener("click", function () { doc.body.classList.remove("nav-ouverte"); }); });

  /* ── la langue suit l'ancre ─────────────────────────────────────────── */
  var bLang = $("#g-lang");
  if (bLang) bLang.addEventListener("click", function () {
    ecrire("dz_lang", LANG === "fr" ? "en" : "fr");
    bLang.href = bLang.getAttribute("href").split("#")[0] + location.hash;
  });

  /* ── chapitre courant + « dans ce chapitre » ───────────────────────── */
  var chapitres = $$("section.chapitre"), toc = $(".g-toc ol"), tocTitre = $(".g-toc b");
  var courant = null;
  function poserToc(sec) {
    if (!toc || sec === courant) return;
    courant = sec;
    $$(".g-nav a").forEach(function (a) { a.setAttribute("aria-current", String(sec && a.getAttribute("href") === "#" + sec.id)); });
    toc.innerHTML = "";
    if (!sec) return;
    if (tocTitre) tocTitre.textContent = $("h2", sec).textContent.replace("#", "").trim();
    $$("h3[id]", sec).forEach(function (h) {
      var li = doc.createElement("li"), a = doc.createElement("a");
      a.href = "#" + h.id; a.textContent = h.textContent.replace("#", "").trim(); a.dataset.cible = h.id;
      li.appendChild(a); toc.appendChild(li);
    });
  }
  function surDefilement() {
    var y = (window.scrollY || 0) + 120, sec = null;
    chapitres.forEach(function (s) { if (s.offsetTop <= y) sec = s; });
    poserToc(sec);
    if (!sec || !toc) return;
    var act = null;
    $$("h3[id]", sec).forEach(function (h) { if (h.getBoundingClientRect().top < 140) act = h.id; });
    $$("a", toc).forEach(function (a) { a.classList.toggle("actif", a.dataset.cible === act); });
  }
  var attente = false;
  window.addEventListener("scroll", function () {
    if (attente) return; attente = true;
    requestAnimationFrame(function () { attente = false; surDefilement(); });
  }, { passive: true });
  surDefilement();

  /* ── recherche plein texte (index embarqué) ────────────────────────── */
  var idx = [];
  try { idx = JSON.parse($("#g-index").textContent); } catch (e) { idx = []; }
  function plat(s) { return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  idx.forEach(function (e) { e.p = plat(e.t + " " + e.x); });
  var champ = $("#g-q"), res = $(".g-res"), sel = -1;
  function echap(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function extrait(x, mots) {
    var p = plat(x), i = p.indexOf(mots[0]); if (i < 0) i = 0;
    var deb = Math.max(0, i - 50), s = (deb ? "…" : "") + x.slice(deb, deb + 140) + (x.length > deb + 140 ? "…" : "");
    var out = echap(s);
    mots.forEach(function (m) {
      if (!m) return;
      var re = new RegExp("(" + m.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }
  function chercher() {
    var q = plat(champ.value.trim());
    if (q.length < 2) { res.classList.remove("ouvert"); return; }
    var mots = q.split(/\s+/);
    var trouves = idx.filter(function (e) { return mots.every(function (m) { return e.p.indexOf(m) >= 0; }); })
      .sort(function (a, b) { return (plat(b.t).indexOf(mots[0]) >= 0) - (plat(a.t).indexOf(mots[0]) >= 0); }).slice(0, 12);
    sel = -1;
    res.innerHTML = trouves.length ? trouves.map(function (e) {
      return '<a href="#' + e.a + '"><b>' + echap(e.c) + (e.t !== e.c ? " › " + echap(e.t) : "") + "</b><span>" + extrait(e.x, mots) + "</span></a>";
    }).join("") : '<div class="vide">' + echap(T.aucun.replace("{q}", champ.value.trim())) + "</div>";
    res.classList.add("ouvert");
  }
  if (champ && res) {
    champ.addEventListener("input", chercher);
    champ.addEventListener("keydown", function (ev) {
      var liens = $$("a", res);
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault(); if (!liens.length) return;
        sel = (sel + (ev.key === "ArrowDown" ? 1 : -1) + liens.length) % liens.length;
        liens.forEach(function (a, i) { a.setAttribute("aria-selected", String(i === sel)); });
      } else if (ev.key === "Enter" && liens.length) { (liens[Math.max(sel, 0)]).click(); champ.blur(); }
      else if (ev.key === "Escape") { res.classList.remove("ouvert"); champ.blur(); }
    });
    res.addEventListener("click", function () { res.classList.remove("ouvert"); });
    doc.addEventListener("click", function (ev) { if (!ev.target.closest(".g-cherche")) res.classList.remove("ouvert"); });
    doc.addEventListener("keydown", function (ev) {
      if (ev.key === "/" && doc.activeElement !== champ && !/INPUT|TEXTAREA/.test(doc.activeElement.tagName)) { ev.preventDefault(); champ.focus(); }
    });
  }

  /* ── scènes animées : curseur, clic, surlignage, bulles ────────────── */
  var reduit = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SVGNS = "http://www.w3.org/2000/svg";
  function el(n, a, p) { var e = doc.createElementNS(SVGNS, n); for (var k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; }
  function Scene(fig) {
    var d = JSON.parse($("script[type='application/json']", fig).textContent);
    var cadre = $(".cadre", fig), imgs = $$(".cadre > img", fig), W = d.taille[0], H = d.taille[1];
    var svg = el("svg", { "class": "reperes", viewBox: "0 0 " + W + " " + H, preserveAspectRatio: "none", "aria-hidden": "true" }, cadre);
    var voile = el("path", { "class": "voile", "fill-rule": "evenodd" }, svg);
    var cadreSurl = el("rect", { "class": "surligne" }, svg);
    var onde = el("circle", { "class": "onde", r: 26 }, svg);
    var curseur = el("g", { "class": "curseur" }, svg);
    var echelle = Math.max(W / 900, 1);
    el("path", { d: "M0 0 L0 26 L7 20 L12 31 L17 29 L12 18 L21 18 Z", fill: "#fff", stroke: "#111", "stroke-width": 1.6,
      transform: "scale(" + echelle + ")" }, curseur);
    var bulle = doc.createElement("div"); bulle.className = "bulle"; cadre.appendChild(bulle);
    var barres = $$(".temps button", fig), pause = $(".pause", fig);
    var i = -1, minuterie = null, actif = false, enPause = false;
    function poser(t) {
      imgs.forEach(function (im, k) { im.classList.toggle("vu", k === t.capture); });
      if (t.curseur) {
        curseur.style.display = "";
        curseur.setAttribute("transform", "translate(" + t.curseur[0] + " " + t.curseur[1] + ")");
        curseur.style.transform = "translate(" + t.curseur[0] + "px," + t.curseur[1] + "px)";
      } else curseur.style.display = "none";
      if (t.surligne) {
        var s = t.surligne, p = 2 * (s[2] + s[3]);
        ["x", "y", "width", "height"].forEach(function (k, j) { cadreSurl.setAttribute(k, s[j]); });
        cadreSurl.style.setProperty("--perim", p);
        cadreSurl.classList.remove("vu"); void cadreSurl.getBoundingClientRect(); cadreSurl.classList.add("vu");
        voile.setAttribute("d", "M0 0H" + W + "V" + H + "H0Z M" + s[0] + " " + s[1] + "h" + s[2] + "v" + s[3] + "h-" + s[2] + "Z");
        voile.classList.toggle("vu", !!t.voile);
        cadreSurl.style.display = "";
      } else { cadreSurl.style.display = "none"; voile.classList.remove("vu"); }
      bulle.classList.remove("vu");
      if (t.bulle) {
        var a = t.ancre || t.curseur || (t.surligne ? [t.surligne[0] + t.surligne[2] / 2, t.surligne[1] + t.surligne[3]] : [W / 2, H / 2]);
        bulle.innerHTML = '<span class="no">' + (i + 1) + "</span>" + t.bulle[LANG];
        bulle.style.left = Math.min(Math.max(a[0] / W * 100 - 10, 2), 58) + "%";
        bulle.style.top = (a[1] / H > .7 ? a[1] / H * 100 - 16 : a[1] / H * 100 + 5) + "%";
        setTimeout(function () { bulle.classList.add("vu"); }, t.curseur ? 650 : 120);
      }
      if (t.clic) setTimeout(function () {
        onde.setAttribute("cx", t.curseur[0] + 2); onde.setAttribute("cy", t.curseur[1] + 2);
        onde.classList.remove("joue"); void onde.getBoundingClientRect(); onde.classList.add("joue");
      }, 620);
    }
    function suivant() {
      clearTimeout(minuterie);
      if (!actif || enPause) return;
      i = (i + 1) % d.temps.length;
      var t = d.temps[i], dur = (t.duree || 1.6) * 1000;
      barres.forEach(function (b, k) {
        b.classList.toggle("fait", k < i); b.classList.remove("cours");
        b.style.setProperty("--d", dur + "ms");
      });
      void fig.offsetWidth; if (barres[i]) barres[i].classList.add("cours");
      poser(t);
      minuterie = setTimeout(suivant, dur + (i === d.temps.length - 1 ? 1500 : 0));
    }
    barres.forEach(function (b, k) { b.addEventListener("click", function () { i = k - 1; enPause = false; suivant(); }); });
    if (pause) pause.addEventListener("click", function () {
      enPause = !enPause; pause.title = enPause ? T.lire : T.pause; pause.setAttribute("aria-pressed", String(enPause));
      if (!enPause) { i--; suivant(); } else clearTimeout(minuterie);
    });
    this.lancer = function () { if (actif) return; actif = true; i = -1; suivant(); };
    this.arreter = function () { actif = false; clearTimeout(minuterie); };
    poser(d.temps[0]);
  }
  var scenes = $$("figure.scene").map(function (f) { var s = new Scene(f); f._s = s; return f; });
  if (!reduit && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) e.target._s.lancer(); else e.target._s.arreter(); });
    }, { threshold: .55 });
    scenes.forEach(function (f) { io.observe(f); });
  }
})();
