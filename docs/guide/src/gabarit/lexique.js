/* Lexique des icônes : recherche et filtre par famille. On imprime ce qui est affiché (une famille seule, ou tout). */
(function () {
  "use strict";
  var doc = document, html = doc.documentElement;
  function $$(s) { return Array.prototype.slice.call(doc.querySelectorAll(s)); }
  function plat(s) { return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  try { var t = localStorage.getItem("dz_guide_theme"); if (t === "light" || t === "dark") html.setAttribute("data-theme", t); } catch (e) {}
  var bTheme = doc.getElementById("g-theme");
  if (bTheme) bTheme.addEventListener("click", function () {
    var cur = html.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var n = cur === "dark" ? "light" : "dark"; html.setAttribute("data-theme", n);
    try { localStorage.setItem("dz_guide_theme", n); } catch (e) {}
  });
  var cartes = $$(".lx-ic"), familles = $$(".lx-fam"), boutons = $$(".lx-familles button");
  cartes.forEach(function (c) { c._t = plat(c.textContent); });
  var champ = doc.getElementById("g-q"), vide = doc.querySelector(".lx-vide"), fam = "*";
  function filtrer() {
    var mots = plat((champ && champ.value) || "").trim().split(/\s+/).filter(Boolean), n = 0;
    familles.forEach(function (f) {
      var vus = 0, okFam = fam === "*" || f.dataset.famille === fam;
      $$("#" + f.id + " .lx-ic").forEach(function (c) {
        var ok = okFam && mots.every(function (m) { return c._t.indexOf(m) >= 0; });
        c.hidden = !ok; if (ok) vus++;
      });
      f.hidden = !vus; n += vus;
    });
    if (vide) vide.hidden = n > 0;
  }
  boutons.forEach(function (b) {
    b.addEventListener("click", function () {
      fam = b.dataset.famille;
      boutons.forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      filtrer();
    });
  });
  if (champ) champ.addEventListener("input", filtrer);
  doc.addEventListener("keydown", function (ev) {
    if (ev.key === "/" && doc.activeElement !== champ) { ev.preventDefault(); champ.focus(); }
  });
})();
