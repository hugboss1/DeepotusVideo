// mod-selection.js — les outils de sélection (C3) : rectangle, ellipse, lasso, lasso polygonal, baguette magique,
// sélection rapide, et Ctrl+A / Ctrl+D / Ctrl+Maj+I (par les raccourcis du catalogue et de l'écran). Chaque geste
// validé = UNE commande select.* (paramètres relevés sur le vrai moteur, plan « Faits établis »).
// Fonctions PURES exportées (qa/gestes.test.mjs).

// Rectangle {x, y, width, height} entier, jamais négatif. carre (Maj) : le plus grand côté ; centre (Alt) : depuis
// le point d'appui. Les bords sont arrondis séparément (pas la largeur) : le rectangle colle à la grille des pixels.
export function rectDepuisGlisser(x0, y0, x1, y1, { carre = false, centre = false } = {}) {
  let dx = x1 - x0, dy = y1 - y0;
  if (carre) {
    const s = Math.max(Math.abs(dx), Math.abs(dy));
    dx = (dx < 0 ? -1 : 1) * s; dy = (dy < 0 ? -1 : 1) * s;
  }
  let gauche, haut, droite, bas;
  if (centre) { gauche = x0 - Math.abs(dx); droite = x0 + Math.abs(dx); haut = y0 - Math.abs(dy); bas = y0 + Math.abs(dy); }
  else { gauche = Math.min(x0, x0 + dx); droite = Math.max(x0, x0 + dx); haut = Math.min(y0, y0 + dy); bas = Math.max(y0, y0 + dy); }
  const x = Math.round(gauche), y = Math.round(haut);
  return { x, y, width: Math.max(0, Math.round(droite) - x), height: Math.max(0, Math.round(bas) - y) };
}

// Règle « fresh » de photocraft (B §8) : un modificateur tenu À L'APPUI choisit le mode (Maj ajouter, Alt soustraire,
// les deux intersection) ; enfoncé pendant le glisser, il contraint la forme et le mode reste celui de la barre.
export function modeSelection(barre, maj, alt, aLAppui) {
  if (!aLAppui) return barre;
  if (maj && alt) return "intersect";
  if (maj) return "add";
  if (alt) return "subtract";
  return barre;
}

// Le lasso polygonal se ferme près du premier sommet : 8 px ÉCRAN (le zoom compte), avec au moins 3 sommets.
export function fermeturePolygone(points, x, y, z, seuil = 8) {
  if (!points || points.length < 3) return false;
  return Math.hypot((x - points[0][0]) * z, (y - points[0][1]) * z) < seuil;
}

// Trace à main levée : un point n'est gardé qu'à `pas` px écran du précédent (des milliers de points identiques
// alourdiraient la commande sans rien changer à la forme) ; coordonnées entières.
export function ajouterPoint(points, x, y, z, pas = 2) {
  const p = [Math.round(x), Math.round(y)];
  const der = points[points.length - 1];
  if (der && Math.hypot((p[0] - der[0]) * z, (p[1] - der[1]) * z) < pas) return points;
  return [...points, p];
}

const DESELECTION = { command: "select.deselect", params: {} };

// Rectangle ou ellipse. Moins de 2 px en mode « nouvelle » = un clic : désélectionner (photocraft) ; dans les autres
// modes, un clic ne change rien.
export function commandeRect(r, opts, mode, ellipse) {
  if (r.width < 2 || r.height < 2) return mode === "replace" ? DESELECTION : null;
  return { command: "select.rect", params: { x: r.x, y: r.y, width: r.width, height: r.height, mode, ellipse: !!ellipse,
    antiAlias: !!opts.antiAlias, feather: opts.feather || 0 } };
}
export function commandeLasso(points, opts, mode) {
  if (!points || points.length < 3) return mode === "replace" ? DESELECTION : null;
  return { command: "select.lasso", params: { points, mode, antiAlias: !!opts.antiAlias, feather: opts.feather || 0 } };
}
export function commandeBaguette(x, y, opts, mode, doc) {
  const px = Math.floor(x), py = Math.floor(y);
  if (!doc || px < 0 || py < 0 || px >= doc.width || py >= doc.height) return null;
  return { command: "select.magicWand", params: { x: px, y: py, tolerance: opts.tolerance, contiguous: !!opts.contiguous,
    antiAlias: !!opts.antiAlias, sampleAllLayers: !!opts.sampleAllLayers, mode } };
}
export function commandeRapide(points, opts, mode) {
  if (!points || !points.length) return null;
  return { command: "select.quick", params: { points, size: opts.size, mode, sampleAllLayers: !!opts.sampleAllLayers } };
}

/* ───────────── côté DOM ───────────── */

export function initSelection(PL) {
  const o = () => PL.etat.options;
  const lancer = (c) => { if (c) PL.executer(c.command, c.params); };
  const redessiner = () => PL.dessinerFourmis && PL.dessinerFourmis();

  // Rectangle et ellipse : aperçu pendant le glisser, commande au relâchement.
  function marquee(ellipse) {
    let g = null;
    return {
      appui(p, ev) { g = { x0: p.x, y0: p.y, maj: ev.shiftKey, alt: ev.altKey, mode: modeSelection(o().mode, ev.shiftKey, ev.altKey, true) }; },
      bouger(p, ev) {
        if (!g) return;
        // Un modificateur déjà tenu à l'appui a choisi le mode : il ne contraint pas en plus la forme.
        const r = rectDepuisGlisser(g.x0, g.y0, p.x, p.y, { carre: ev.shiftKey && !g.maj, centre: ev.altKey && !g.alt });
        PL.apercu = { type: ellipse ? "ellipse" : "rect", ...r };
        redessiner();
      },
      relacher(p, ev) {
        if (!g) return;
        const r = rectDepuisGlisser(g.x0, g.y0, p.x, p.y, { carre: ev.shiftKey && !g.maj, centre: ev.altKey && !g.alt });
        const mode = g.mode; g = null; PL.apercu = null; redessiner();
        lancer(commandeRect(r, o(), mode, ellipse));
      },
      annuler() { g = null; PL.apercu = null; redessiner(); },
      // Échap pendant le glisser : abandon, le relâchement qui suit ne sélectionne rien.
      touche(ev) { if (ev.key !== "Escape" || !g) return false; g = null; PL.apercu = null; redessiner(); return true; },
      quitter() { g = null; },
    };
  }
  PL.gestes.rectMarquee = marquee(false);
  PL.gestes.ellipseMarquee = marquee(true);

  // Lasso à main levée.
  let lasso = null;
  PL.gestes.lasso = {
    appui(p, ev) { lasso = { points: ajouterPoint([], p.x, p.y, PL.vue.v.z), mode: modeSelection(o().mode, ev.shiftKey, ev.altKey, true) }; },
    bouger(p) {
      if (!lasso) return;
      lasso.points = ajouterPoint(lasso.points, p.x, p.y, PL.vue.v.z);
      PL.apercu = { type: "lasso", points: lasso.points }; redessiner();
    },
    relacher() {
      if (!lasso) return;
      const { points, mode } = lasso; lasso = null; PL.apercu = null; redessiner();
      lancer(commandeLasso(points, o(), mode));
    },
    annuler() { lasso = null; PL.apercu = null; redessiner(); },
    touche(ev) { if (ev.key !== "Escape" || !lasso) return false; lasso = null; PL.apercu = null; redessiner(); return true; },
    quitter() { lasso = null; },
  };

  // Lasso polygonal : clic = sommet ; double-clic, clic sur le premier sommet ou Entrée = fermer ; Échap = abandonner ;
  // Retour arrière = retirer le dernier sommet.
  let poly = null;
  const majPoly = (curseur) => {
    PL.apercu = poly ? { type: "poly", points: poly.points, curseur, fermable: curseur && fermeturePolygone(poly.points, curseur[0], curseur[1], PL.vue.v.z) } : null;
    redessiner();
  };
  const fermerPoly = () => {
    if (!poly) return;
    const { points, mode } = poly; poly = null; PL.apercu = null; redessiner();
    lancer(commandeLasso(points, o(), mode));
  };
  PL.gestes.polygonLasso = {
    appui(p, ev) {
      if (!poly) poly = { points: [], mode: modeSelection(o().mode, ev.shiftKey, ev.altKey, true) };
      else if (fermeturePolygone(poly.points, p.x, p.y, PL.vue.v.z)) { fermerPoly(); return; }
      poly.points.push([Math.round(p.x), Math.round(p.y)]);
      majPoly([p.x, p.y]);
    },
    bouger(p) { if (poly) majPoly([p.x, p.y]); },
    survol(p) { if (poly) majPoly([p.x, p.y]); },
    relacher() {},
    // Le double-clic arrive après deux appuis : le second a déjà posé un sommet en double, on le retire.
    double() { if (poly && poly.points.length > 1) poly.points.pop(); fermerPoly(); },
    touche(ev) {
      if (!poly) return false;
      if (ev.key === "Enter") { fermerPoly(); return true; }
      if (ev.key === "Escape") { poly = null; majPoly(null); return true; }
      if (ev.key === "Backspace") { poly.points.pop(); if (!poly.points.length) poly = null; majPoly(null); return true; }
      return false;
    },
    quitter() { poly = null; },
  };

  // Baguette magique : un clic.
  PL.gestes.magicWand = {
    appui(p, ev) { lancer(commandeBaguette(p.x, p.y, o(), modeSelection(o().mode, ev.shiftKey, ev.altKey, true), PL.etat.doc)); },
    bouger() {}, relacher() {},
  };

  // Sélection rapide : la trace du glisser part au moteur au relâchement.
  let rapide = null;
  PL.gestes.quickSelection = {
    appui(p, ev) { rapide = { points: ajouterPoint([], p.x, p.y, PL.vue.v.z), mode: modeSelection(o().mode, ev.shiftKey, ev.altKey, true) }; },
    bouger(p) {
      if (!rapide) return;
      rapide.points = ajouterPoint(rapide.points, p.x, p.y, PL.vue.v.z);
      PL.apercu = { type: "trace", points: rapide.points }; redessiner();
    },
    relacher() {
      if (!rapide) return;
      const { points, mode } = rapide; rapide = null; PL.apercu = null; redessiner();
      lancer(commandeRapide(points, o(), mode));
    },
    annuler() { rapide = null; PL.apercu = null; redessiner(); },
    touche(ev) { if (ev.key !== "Escape" || !rapide) return false; rapide = null; PL.apercu = null; redessiner(); return true; },
    quitter() { rapide = null; },
  };
}
