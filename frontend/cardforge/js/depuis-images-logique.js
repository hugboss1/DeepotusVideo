/* ═══════════════════════════════════════════════════════════════════════════
   js/depuis-images-logique.js — t421 (cartes hexagonales, 07/11/2026, tâche 5)
   La LOGIQUE PURE du dialogue « Nouveau jeu depuis des images »
   (js/depuis-images.js) : aucun DOM, aucun réseau, aucune variable du CORE.
   Publiée sous `window.CFImages` ; le banc la charge sous node dans un `vm`
   (frontend/cardforge/qa/depuis_images.test.mjs).

   Règles de la conception (docs/superpowers/specs/2026-11-07-cartes-
   hexagonales-design.md, « Fond perdu », « L'écran de création ») :
   - ordre des cartes : tri NATUREL des noms de fichiers ;
   - appariement : `<nom>_verso.<ext>` est le verso de `<nom>_recto.<ext>` ou
     de `<nom>.<ext>` ; `_back` et `_front` valent de même. Même extension
     exigée (la spec écrit la même `<ext>` des deux côtés). Un recto sans verso
     est signalé, sans blocage ; un verso sans recto est orphelin ;
   - nom de carte : le fichier sans extension, `_` remplacé par une espace
     (miroir de `_titre` de backend/app/services/cards/depuis_images.py) ;
   - « Mon fichier inclut le fond perdu » : vrai si le rapport de l'image est
     celui de la TOILE (coupe + 2 × fond perdu, comme geomOf) à 0,5 % près ;
   - format proposé : le rapport MÉDIAN des images, comparé à la coupe et à la
     toile de chaque format ; à égalité, l'ordre des formats décide.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (g) {
  "use strict";

  /* tolérance relative d'un rapport largeur / hauteur */
  const TOLERANCE = 0.005;
  /* deux formats plus proches que ceci l'un de l'autre sont À ÉGALITÉ : les
     quatre hexagones « pointe » ont le même rapport, au millième de mm de
     leur table près (0,866034 / 0,866031 / 0,866021 / 0,866026). */
  const EGALITE = 1e-4;

  /* tri naturel : chiffres comparés comme des nombres, casse et accents
     ignorés (« é » range avec « e ») ; un départage stable ensuite, pour que
     deux noms qui ne diffèrent que par la casse sortent toujours pareil. */
  const COLL = (typeof Intl !== "undefined" && Intl.Collator)
    ? new Intl.Collator("fr", { numeric: true, sensitivity: "base" }) : null;
  /* le nom sans extension d'abord : « carte_1.png » avant « carte_1_verso.png » */
  const separer = (s) => { const k = s.lastIndexOf("."); return k > 0 ? [s.slice(0, k), s.slice(k)] : [s, ""]; };
  const comp = (x, y) => (COLL ? COLL.compare(x, y)
    : (x.toLowerCase() < y.toLowerCase() ? -1 : x.toLowerCase() > y.toLowerCase() ? 1 : 0));
  function comparer(a, b) {
    const x = String(a), y = String(b), tx = separer(x), ty = separer(y);
    const c = comp(tx[0], ty[0]) || comp(tx[1], ty[1]);
    if (c) return c;
    return x < y ? -1 : x > y ? 1 : 0;
  }
  function triNaturel(noms) {
    return (Array.isArray(noms) ? noms.slice() : []).map(String).sort(comparer);
  }

  /* « a_verso.png » -> {base: "a", ext: ".png", role: "verso"} ; le rôle est
     "verso", "recto" (suffixe _recto / _front) ou "" (aucun suffixe). */
  const SUFFIXE = /^(.*)_(recto|front|verso|back)$/i;
  function decouper(nom) {
    const s = String(nom);
    const k = s.lastIndexOf(".");
    const tige = k > 0 ? s.slice(0, k) : s, ext = k > 0 ? s.slice(k) : "";
    const m = SUFFIXE.exec(tige);
    if (!m) return { base: tige, ext: ext, role: "" };
    const v = m[2].toLowerCase();
    return { base: m[1], ext: ext, role: (v === "verso" || v === "back") ? "verso" : "recto" };
  }
  const cle = (d) => (d.base + d.ext).toLowerCase();

  function apparier(noms) {
    const tries = triNaturel(noms);
    const versos = {};                       /* clé -> [noms de verso], dans l'ordre */
    const rectos = [];
    tries.forEach((n) => {
      const d = decouper(n);
      if (d.role === "verso") (versos[cle(d)] = versos[cle(d)] || []).push(n);
      else rectos.push({ nom: n, cle: cle(d) });
    });
    const cartes = [], sansVerso = [];
    rectos.forEach((r) => {
      const l = versos[r.cle];
      const v = l && l.length ? l.shift() : null;
      cartes.push({ recto: r.nom, verso: v });
      if (!v) sansVerso.push(r.nom);
    });
    const orphelins = triNaturel(Object.keys(versos).reduce((a, k) => a.concat(versos[k]), []));
    return { cartes: cartes, sansVerso: sansVerso, orphelins: orphelins };
  }

  function nomCarte(fichier) {
    const s = String(fichier == null ? "" : fichier);
    const k = s.lastIndexOf(".");
    const t = (k > 0 ? s.slice(0, k) : s).replace(/_/g, " ").trim();
    return t || s;
  }

  /* ── les rapports ───────────────────────────────────────────────────────── */
  const rapport = (w, h) => (Number(w) > 0 && Number(h) > 0 ? Number(w) / Number(h) : null);
  const ecart = (r, cible) => Math.abs(r / cible - 1);
  function rapportCoupe(fmt) { return rapport(fmt.trim_mm[0], fmt.trim_mm[1]); }
  function rapportToile(fmt, bleed) {
    const b = Math.max(0, Number(bleed) || 0);
    return rapport(fmt.trim_mm[0] + 2 * b, fmt.trim_mm[1] + 2 * b);
  }

  function inclutFondPerdu(wImg, hImg, fmt, bleed) {
    const r = rapport(wImg, hImg);
    if (r == null || !fmt || !(Number(bleed) > 0)) return false;
    return ecart(r, rapportToile(fmt, bleed)) <= TOLERANCE;
  }

  /* le rapport médian des images dont les dimensions sont connues ; null sinon */
  function rapportMedian(dims) {
    const rs = (Array.isArray(dims) ? dims : []).map((d) => rapport(d && d.w, d && d.h))
      .filter((r) => r != null).sort((a, b) => a - b);
    if (!rs.length) return null;
    const m = rs.length >> 1;
    return rs.length % 2 ? rs[m] : (rs[m - 1] + rs[m]) / 2;
  }

  /* formats : [{id, trim_mm, bleed_mm?}] ; la toile n'est comparée que si le
     format porte son fond perdu. */
  function formatPropose(dims, formats) {
    const r = rapportMedian(dims);
    if (r == null) return null;
    let meilleur = null, dist = Infinity;
    (Array.isArray(formats) ? formats : []).forEach((f) => {
      if (!f || !Array.isArray(f.trim_mm)) return;
      let d = ecart(r, rapportCoupe(f));
      if (Number(f.bleed_mm) > 0) d = Math.min(d, ecart(r, rapportToile(f, f.bleed_mm)));
      if (d < dist - EGALITE) { dist = d; meilleur = f.id; }
    });
    return meilleur;
  }

  /* les images qui seront RECADRÉES : leur rapport s'écarte de plus de 0,5 %
     de celui de la toile du deck (avec fond perdu si `inclut`, à la coupe
     sinon : le deck naît alors à fond perdu 0). Dimensions inconnues : on ne
     peut rien dire, l'image n'est pas nommée. */
  function ecarts(dims, fmt, inclut) {
    if (!fmt) return [];
    const cible = inclut ? rapportToile(fmt, fmt.bleed_mm) : rapportCoupe(fmt);
    return (Array.isArray(dims) ? dims : []).filter((d) => {
      const r = rapport(d && d.w, d && d.h);
      return r != null && ecart(r, cible) > TOLERANCE;
    }).map((d) => String(d.nom));
  }

  const API = Object.freeze({
    TOLERANCE: TOLERANCE,
    triNaturel: triNaturel, apparier: apparier, nomCarte: nomCarte,
    inclutFondPerdu: inclutFondPerdu, rapportMedian: rapportMedian,
    formatPropose: formatPropose, ecarts: ecarts,
  });
  g.CFImages = API;
})(typeof window !== "undefined" ? window : globalThis);
