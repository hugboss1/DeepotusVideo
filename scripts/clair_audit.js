/* scripts/clair_audit.js — AUDIT du thème clair, écran par écran (t383, 30/10/2026, lot « Réglages : chemins &
   apparence »). À coller dans la page (outil javascript du navigateur, backend de preuve 8809) une fois le préréglage
   « Clair » choisi dans Réglages › Apparence (t382) : il parcourt la coque ET chaque cadre de même origine (labs) et
   rend, regroupés par signature (balise.classes) :
     • texte : un texte visible dont le contraste avec son fond EFFECTIF (premier ancêtre opaque) est sous l'AA
       (4,5:1 ; 3:1 pour un grand texte : ≥ 24 px, ou ≥ 18,66 px gras) ;
     • ilot : une surface visible de plus de 2 000 px² restée SOMBRE (luminance < 0,05) alors que le fond de la page
       est clair — un panneau, une barre ou un menu qui n'a pas suivi la palette ;
   Exclus d'office : <canvas>, <video>, <img>, <svg> et leur contenu (ce qu'ils montrent est une ŒUVRE, pas
   l'interface), les éléments [data-dz-clair="garde"] (sombres à dessein : un aperçu vidéo, un écran de capture).
   Rend {ecran, cadres, texte: [{sig, n, ratio, exemple, couleur, fond}], ilot: [{sig, n, fond, taille}]} ; trié par n.
   Usage : copier le fichier dans l'outil javascript ; (await window.__dzClairAudit()) ou laisser la dernière ligne. */
(function () {
  "use strict";
  function rgba(s) {
    var m = /rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)/.exec(s || "");
    if (!m) return null;
    var a = m[4] == null ? 1 : (/%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
    return [+m[1], +m[2], +m[3], a];
  }
  function lum(c) {
    var x = c.slice(0, 3).map(function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * x[0] + 0.7152 * x[1] + 0.0722 * x[2];
  }
  function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function sur(haut, bas) {                       // haut posé sur bas (alpha)
    var a = haut[3];
    return [0, 1, 2].map(function (i) { return haut[i] * a + bas[i] * (1 - a); }).concat(1);
  }
  function sig(el) {
    var c = (typeof el.className === "string" ? el.className : "").trim().split(/\s+/).filter(Boolean).slice(0, 3);
    return el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (c.length ? "." + c.join(".") : "");
  }
  var EXCLUS = { CANVAS: 1, VIDEO: 1, IMG: 1, SVG: 1, IFRAME: 1, PICTURE: 1, OBJECT: 1 };
  function exclu(el) {
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      if (EXCLUS[n.tagName.toUpperCase()] || (n.getAttribute && n.getAttribute("data-dz-clair") === "garde")) return true;
    }
    return false;
  }
  function fondEffectif(el, win) {
    var pile = [];
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      var cs = win.getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== "none" && /gradient|url/.test(cs.backgroundImage)) return null;
      var c = rgba(cs.backgroundColor);
      if (c && c[3] > 0) { pile.push(c); if (c[3] >= 0.99) break; }
    }
    var f = [255, 255, 255, 1];
    for (var i = pile.length - 1; i >= 0; i--) f = sur(pile[i], f);
    return f;
  }
  function visible(el, win) {
    var r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.right < 0) return null;
    var cs = win.getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity) < 0.1) return null;
    return r;
  }
  function auditDoc(doc, nom, acc) {
    var win = doc.defaultView;
    if (!win || !doc.body) return;
    acc.cadres.push(nom);
    var tous = doc.body.querySelectorAll("*");
    for (var i = 0; i < tous.length; i++) {
      var el = tous[i];
      if (el.tagName === "IFRAME") {
        try { if (el.contentDocument) auditDoc(el.contentDocument, el.getAttribute("src") || "iframe", acc); } catch (e) { /* autre origine */ }
        continue;
      }
      if (exclu(el)) continue;
      var r = visible(el, win);
      if (!r) continue;
      var cs = win.getComputedStyle(el);
      // îlot sombre
      var bg = rgba(cs.backgroundColor);
      if (bg && bg[3] >= 0.9 && r.width * r.height > 2000 && lum(bg) < 0.05) {
        acc.ilots.push({ sig: nom + " " + sig(el), fond: cs.backgroundColor, taille: Math.round(r.width) + "x" + Math.round(r.height) });
      }
      // texte propre de l'élément
      var txt = "";
      for (var k = 0; k < el.childNodes.length; k++) if (el.childNodes[k].nodeType === 3) txt += el.childNodes[k].nodeValue;
      txt = txt.trim();
      if (!txt) continue;
      var c = rgba(cs.color), f = fondEffectif(el, win);
      if (!c || !f) continue;
      var vu = sur(c, f), q = ratio(vu, f);
      var px = parseFloat(cs.fontSize), gras = parseInt(cs.fontWeight, 10) >= 700;
      var seuil = (px >= 24 || (px >= 18.66 && gras)) ? 3 : 4.5;
      if (q < seuil) acc.textes.push({ sig: nom + " " + sig(el), ratio: Math.round(q * 100) / 100, exemple: txt.slice(0, 40),
                                       couleur: cs.color, fond: "rgb(" + f.slice(0, 3).map(Math.round).join(",") + ")" });
    }
  }
  function grouper(liste, cle) {
    var m = {};
    liste.forEach(function (x) {
      var g = m[x.sig] || (m[x.sig] = Object.assign({ n: 0 }, x));
      g.n++;
      if (cle && x[cle] < g[cle]) g[cle] = x[cle];
    });
    return Object.keys(m).map(function (k) { return m[k]; }).sort(function (a, b) { return b.n - a.n; });
  }
  window.__dzClairAudit = function () {
    var acc = { cadres: [], textes: [], ilots: [] };
    auditDoc(document, "coque", acc);
    return { ecran: location.pathname + location.hash, theme: document.documentElement.getAttribute("data-theme"),
             cadres: acc.cadres, texte: grouper(acc.textes, "ratio"), ilot: grouper(acc.ilots) };
  };
})();
window.__dzClairAudit();
