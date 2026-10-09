// mod-affichage.js — t152 (parité L2) : le menu Affichage. Zooms, symétrie de la vue, modes d'écran, extras (grille,
// repères, grille de pixels, contours), règles, aimantation, verrou des repères, aperçu pixel art.
// Tout est de l'écran SAUF les repères : ils vivent dans le document du moteur (view.newGuide / moveGuide / deleteGuide,
// avec historique) et se relisent par GET /api/photolab/reperes (doc.inspect ne les rend pas).
// Défauts et valeurs de photocraft : view_cmds.rs (Show, SnapTo, ViewOptions), state.rs (Extras), prefs.rs
// (GuidesGridAndSlices : grille d'un pouce en 4 subdivisions, repères #4affff, grille #8c8c8c), snap_ui.rs (8 px).
// Les options sont des préférences d'écran, gardées par navigateur (localStorage). Fonctions PURES exportées
// (qa/affichage.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";

export const SEUIL_AIMANT_PX = 8;
export const COULEUR_REPERE = "#4affff";
export const COULEUR_GRILLE = "#8c8c8c";
export const ECRANS = ["standard", "menus", "plein"];
const ID_ECRAN = { "view.screenMode.standard": "standard", "view.screenMode.fullScreenWithMenuBar": "menus", "view.screenMode.fullScreen": "plein" };

export const OPTIONS_DEFAUT = {
  extras: true, regles: false, grille: false, reperes: true, aimanter: true, verrouReperes: false,
  ecran: "standard", miroir: false, pixelArt: false,
  afficher: { contoursCalque: false, contoursSelection: true, grillePixels: true, apercuPinceau: true, reperesCanevas: true,
    compteur: true, notes: true, tranches: true },                                  // t160
  aimanterA: { reperes: true, grille: true, calques: true, document: true, tranches: true },
};
export const IDS_ZOOM = ["view.zoomIn", "view.zoomOut", "view.fitOnScreen", "view.fitLayersOnScreen", "view.actualPixels", "view.twoHundredPercent", "view.printSize"];
// Entrée -> où vit son interrupteur : [chemin dans les options]. Les zooms et les modes d'écran sont à part.
const BASCULES = {
  "view.extras": ["extras"], "view.show.grid": ["grille"], "view.show.guides": ["reperes"], "view.rulers": ["regles"],
  "view.snap": ["aimanter"], "view.lockGuides": ["verrouReperes"], "view.flipHorizontal": ["miroir"], "view.pixelArtPreview": ["pixelArt"],
  "view.show.layerEdges": ["afficher", "contoursCalque"], "view.show.selectionEdges": ["afficher", "contoursSelection"],
  "view.show.pixelGrid": ["afficher", "grillePixels"], "view.show.brushPreview": ["afficher", "apercuPinceau"],
  "view.show.canvasGuides": ["afficher", "reperesCanevas"],
  "view.snapTo.guides": ["aimanterA", "reperes"], "view.snapTo.grid": ["aimanterA", "grille"], "view.snapTo.layers": ["aimanterA", "calques"],
  "view.snapTo.documentBounds": ["aimanterA", "document"],
  // t160 : comptage, notes, tranches (surcouche de mod-mesure) ; aimantation aux bords des tranches
  "view.show.count": ["afficher", "compteur"], "view.show.notes": ["afficher", "notes"], "view.show.slices": ["afficher", "tranches"],
  "view.snapTo.slices": ["aimanterA", "tranches"],
};
export const IDS_AFFICHAGE = [...IDS_ZOOM, ...Object.keys(ID_ECRAN), ...Object.keys(BASCULES), "view.show.all", "view.show.showExtrasOptions", "view.snapTo.all"];

const copie = (o) => JSON.parse(JSON.stringify(o));
// Stockage lu tel quel (autre version, valeur abîmée) -> options complètes, chaque valeur du bon type.
export function normaliserOptions(brut) {
  const o = copie(OPTIONS_DEFAUT);
  if (!brut || typeof brut !== "object") return o;
  for (const k of Object.keys(o)) {
    if (k === "afficher" || k === "aimanterA") {
      for (const s of Object.keys(o[k])) if (brut[k] && typeof brut[k][s] === "boolean") o[k][s] = brut[k][s];
    } else if (k === "ecran") { if (ECRANS.includes(brut.ecran)) o.ecran = brut.ecran; }
    else if (typeof brut[k] === "boolean") o[k] = brut[k];
  }
  return o;
}

// Une entrée du menu -> nouvelles options (l'original ne change pas) ; un zoom ou une entrée inconnue -> copie inchangée.
export function basculer(o, id) {
  const c = copie(o);
  if (ID_ECRAN[id]) { c.ecran = ID_ECRAN[id]; return c; }
  if (id === "view.show.all") {
    c.grille = true; c.reperes = true;
    for (const k of Object.keys(c.afficher)) c.afficher[k] = true;
    return c;
  }
  if (id === "view.snapTo.all") { for (const k of Object.keys(c.aimanterA)) c.aimanterA[k] = true; return c; }
  const ch = BASCULES[id];
  if (!ch) return c;
  if (ch.length === 1) c[ch[0]] = !c[ch[0]]; else c[ch[0]][ch[1]] = !c[ch[0]][ch[1]];
  return c;
}
export function coche(o, id) {
  if (ID_ECRAN[id]) return o.ecran === ID_ECRAN[id];
  const ch = BASCULES[id];
  if (!ch) return undefined;
  return !!(ch.length === 1 ? o[ch[0]] : o[ch[0]][ch[1]]);
}
// Un extra se voit si Extras est allumé ET son interrupteur aussi (ViewOptions::shows). Les repères ont deux interrupteurs.
export function visible(o, cle) {
  if (!o.extras) return false;
  if (cle === "grille") return o.grille;
  if (cle === "reperes") return o.reperes && o.afficher.reperesCanevas;
  return !!o.afficher[cle];
}
export const grillePixelsVisible = (o, z) => visible(o, "grillePixels") && z > 5;
export const ecranSuivant = (e) => ECRANS[(ECRANS.indexOf(e) + 1) % ECRANS.length];
// Taille d'impression : photocraft suppose un écran à 72 ppi (view_cmds.rs).
export const zoomImpression = (ppi) => (ppi > 0 ? 72 / ppi : 1);

// Grille : un pouce du document (ses ppi), 4 subdivisions.
export function pasGrille(ppi) {
  const p = ppi > 0 ? ppi : 72;
  return { majeur: p, mineur: p / 4 };
}
// Lignes de grille VISIBLES sur un axe ("x" : verticales) : positions document, bornées par la vue, jamais par la taille
// du document ; les subdivisions trop serrées (< 4 px d'écran) sont omises.
export function lignesGrille(v, doc, vue, axe, pas) {
  const z = v.z, o = axe === "x" ? v.ox : v.oy, longueur = axe === "x" ? doc.w : doc.h, ecran = axe === "x" ? vue.w : vue.h;
  const unite = pas.mineur * z >= 4 ? pas.mineur : pas.majeur;
  if (unite * z < 4) return [];
  // en miroir horizontal, la plage visible se calcule sur la vue retournée
  let a = (0 - o) / z, b = (ecran - o) / z;
  if (axe === "x" && v.miroir) { const a2 = v.dw - b, b2 = v.dw - a; a = a2; b = b2; }
  const debut = Math.max(0, Math.ceil(a / unite) * unite), fin = Math.min(longueur, b);
  const L = [];
  for (let p = debut; p <= fin + 1e-9; p += unite) {
    const r = Math.round(p * 1e6) / 1e6;
    L.push({ pos: r, majeure: Math.abs(r / pas.majeur - Math.round(r / pas.majeur)) < 1e-6 });
  }
  return L;
}
// Graduations d'une règle entre deux positions document : premier pas 1-2-5 × 10^n à au moins 50 px d'écran, 5
// graduations mineures par pas.
export function graduations(debut, fin, z) {
  let pas = 1;
  for (let e = -2; e < 7; e++) {
    const trouve = [1, 2, 5].map((m) => m * 10 ** e).find((p) => p * z >= 50);
    if (trouve !== undefined) { pas = trouve; break; }
  }
  pas = Math.round(pas * 1e6) / 1e6;
  const majeurs = [];
  for (let p = Math.floor(debut / pas) * pas; p <= fin + 1e-9; p += pas) majeurs.push(Math.round(p * 1e6) / 1e6);
  return { pas, mineur: pas / 5, majeurs };
}

// Aimantation : la cible la plus proche à moins de `seuil` (pixels DOCUMENT : 8 px d'écran / zoom).
export function aimanter(valeur, cibles, seuil) {
  let meilleure = null, d = seuil;
  for (const c of cibles) { const e = Math.abs(c - valeur); if (e <= d) { d = e; meilleure = c; } }
  return { valeur: meilleure === null ? valeur : meilleure, cible: meilleure };
}
export const aimanterPoint = (p, cibles, seuil) => ({ x: aimanter(p.x, cibles.x, seuil).valeur, y: aimanter(p.y, cibles.y, seuil).valeur });
// Déplacement d'un objet de bornes [x, y, w, h] : le bord gauche, le centre ou le bord droit (puis haut / milieu / bas)
// se pose sur la cible la plus proche ; delta corrigé.
export function aimanterDeplacement(bornes, dx, dy, cibles, seuil) {
  const axe = (o, l, d, cs) => {
    let best = null;
    for (const bord of [o, o + l / 2, o + l]) {
      const r = aimanter(bord + d, cs, seuil);
      if (r.cible !== null && (best === null || Math.abs(r.cible - (bord + d)) < best.e)) best = { e: Math.abs(r.cible - (bord + d)), d: d + r.cible - (bord + d) };
    }
    return best ? best.d : d;
  };
  return { dx: axe(bornes[0], bornes[2], dx, cibles.x), dy: axe(bornes[1], bornes[3], dy, cibles.y) };
}
const aplat = (l) => (l || []).flatMap((c) => [c, ...aplat(c.children)]);
// Cibles d'aimantation : repères (visibles), grille (visible), limites et centre du document, bords et centres des calques
// qui NE bougent PAS (ni l'actif ni les sélectionnés).
export function ciblesAimant(o, doc, reperes, tranches = null) {
  const c = { x: [], y: [] };
  if (!o.aimanter || !doc) return c;
  if (o.aimanterA.reperes && visible(o, "reperes") && reperes) { c.x.push(...(reperes.vertical || [])); c.y.push(...(reperes.horizontal || [])); }
  if (o.aimanterA.document) { c.x.push(0, doc.width / 2, doc.width); c.y.push(0, doc.height / 2, doc.height); }
  if (o.aimanterA.calques) {
    const bougent = new Set([doc.activeLayer, ...(doc.selectedLayers || [])]);
    for (const l of aplat(doc.layers)) {
      if (bougent.has(l.id) || !Array.isArray(l.bounds) || l.visible === false) continue;
      const [x, y, w, h] = l.bounds;
      c.x.push(x, x + w / 2, x + w); c.y.push(y, y + h / 2, y + h);
    }
  }
  // t160 : bords des tranches utilisateur et d'après un calque (les automatiques suivent les autres)
  if (o.aimanterA.tranches && tranches) {
    for (const s of tranches) {
      if (s.origin === "auto" || !Array.isArray(s.rect)) continue;
      const [x, y, w, h] = s.rect;
      c.x.push(x, x + w); c.y.push(y, y + h);
    }
  }
  if (o.aimanterA.grille && visible(o, "grille")) {
    const p = pasGrille(doc.resolution).mineur;
    for (let x = 0; x <= doc.width + 1e-9; x += p) c.x.push(Math.round(x * 1e6) / 1e6);
    for (let y = 0; y <= doc.height + 1e-9; y += p) c.y.push(Math.round(y * 1e6) / 1e6);
  }
  return c;
}

// Faut-il relire les repères (≈ 130 ms par lecture) ? Nouveau document, autre document, historique raccourci
// (annulation), ou un nouvel état d'une opération qui crée, déplace ou recadre (noms relevés sur le vrai moteur).
const TOUCHE_REPERES = /Guide|Canvas|Image Size|Crop|Trim|Rotat|Flip|Reveal/i;
export function relireReperes(avant, apres) {
  if (!avant) return true;
  if (avant.nom !== apres.nom) return true;
  const a = avant.history || [], b = apres.history || [];
  if (b.length < a.length) return true;
  for (let i = 0; i < b.length; i++) if (a[i] !== b[i]) return i >= a.length ? b.slice(i).some((n) => TOUCHE_REPERES.test(n)) : true;
  return false;
}
// Adapter le(s) calque(s) : union des bornes des calques sélectionnés (sinon l'actif) ; le document s'il n'y a rien.
export function bornesCalques(doc) {
  const ids = new Set(doc.selectedLayers && doc.selectedLayers.length ? doc.selectedLayers : [doc.activeLayer]);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const l of aplat(doc.layers)) {
    if (!ids.has(l.id) || !Array.isArray(l.bounds) || !(l.bounds[2] > 0) || !(l.bounds[3] > 0)) continue;
    x0 = Math.min(x0, l.bounds[0]); y0 = Math.min(y0, l.bounds[1]);
    x1 = Math.max(x1, l.bounds[0] + l.bounds[2]); y1 = Math.max(y1, l.bounds[1] + l.bounds[3]);
  }
  return x0 === Infinity ? { x: 0, y: 0, w: doc.width, h: doc.height } : { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

// Le menu Affichage : entrées servies actives, coches. N'altère pas l'arbre reçu.
export function decorerAffichage(menus, o) {
  const sortie = copie(menus);
  const vue = sortie.find((m) => m.nom === "View");
  if (!vue) return sortie;
  const voir = (l) => l.forEach((e, i) => {
    if (e.type === "sous-menu") voir(e.entrees);
    else if (e.type === "commande" && IDS_AFFICHAGE.includes(e.id)) {
      const c = coche(o, e.id);
      l[i] = { ...e, etat: "actif", ...(c === undefined ? {} : { coche: c }) };
    }
  });
  voir(vue.entrees);
  return sortie;
}

/* ───────────── côté DOM ───────────── */

const NS = "http://www.w3.org/2000/svg";
// Outils dont le point de geste s'aimante (sélections géométriques, recadrage, dégradé).
// t160 : + Tranche (ses bords se posent sur repères, grille, tranches et bords du document)
export const OUTILS_AIMANTES = new Set(["rectMarquee", "ellipseMarquee", "polygonLasso", "crop", "gradient", "slice"]);
const CLE_STOCKAGE = "dz-photolab-affichage";
const REGLE = 18;          // épaisseur des règles (px)
const TOL_REPERE = 4;      // px d'écran pour attraper un repère
const aplatir = (l) => (l || []).flatMap((x) => [x, ...aplatir(x.children)]);

export function initAffichage(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const scene = PL.$("#scene");
  let o;
  try { o = normaliserOptions(JSON.parse(localStorage.getItem(CLE_STOCKAGE) || "null")); } catch (e) { o = normaliserOptions(null); }
  let reperes = { horizontal: [], vertical: [] };
  let dernierDoc = null, lecture = null;
  let glisseRepere = null;   // {orientation, index|null, pos} pendant un glisser de repère

  /* surcouche et règles */
  const svg = document.createElementNS(NS, "svg");
  svg.id = "affichage"; svg.setAttribute("aria-hidden", "true");
  scene.insertBefore(svg, PL.$("#fourmis"));
  const regles = document.createElement("div"); regles.id = "regles"; regles.hidden = true;
  const rH = document.createElement("canvas"); rH.id = "regleH";
  const rV = document.createElement("canvas"); rV.id = "regleV";
  const coin = document.createElement("div"); coin.className = "regle-coin";
  regles.append(rH, rV, coin);
  scene.appendChild(regles);

  const el = (tag, attrs, classe) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (classe) e.setAttribute("class", classe);
    return e;
  };
  const tailleScene = () => ({ w: scene.clientWidth, h: scene.clientHeight });
  const ecranX = (x) => PL.vue.versEcran(x, 0).x;
  const ecranY = (y) => PL.vue.versEcran(0, y).y;
  const rectEcran = (x, y, w, h) => {
    const a = PL.vue.versEcran(x, y), b = PL.vue.versEcran(x + w, y + h);
    return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y) };
  };
  const calqueActif = (d) => aplatir(d.layers).find((l) => l.id === d.activeLayer);
  // t159 : Préférences › Repères, grille et tranches (couleur, style, pas, subdivisions) ; défauts de photocraft sans elles
  const pr = (cle, defaut) => (PL.prefs ? PL.prefs.v("guidesGridAndSlices", cle) : defaut);
  const styleTrait = (style) => { const t = PL.prefs ? PL.prefs.tirets(style) : ""; return t ? { "stroke-dasharray": t } : {}; };
  const pasDe = (d) => (PL.prefs ? PL.prefs.pasGrille(d.resolution, d.width) : pasGrille(d.resolution));

  function dessiner() {
    svg.textContent = "";
    const d = PL.etat.doc;
    const v = PL.vue.v;
    const vue = tailleScene();
    if (d) {
      const dims = { w: d.width, h: d.height };
      const r = rectEcran(0, 0, d.width, d.height);
      if (visible(o, "grille")) {
        const g = el("g", { stroke: pr("gridColor", COULEUR_GRILLE), ...styleTrait(pr("gridStyle", "lines")) }, "grille");
        for (const l of lignesGrille(v, dims, vue, "x", pasDe(d))) {
          const x = Math.round(ecranX(l.pos)) + 0.5;
          g.appendChild(el("line", { x1: x, y1: r.y, x2: x, y2: r.y + r.h }, l.majeure ? "majeure" : "mineure"));
        }
        for (const l of lignesGrille(v, dims, vue, "y", pasDe(d))) {
          const y = Math.round(ecranY(l.pos)) + 0.5;
          g.appendChild(el("line", { x1: r.x, y1: y, x2: r.x + r.w, y2: y }, l.majeure ? "majeure" : "mineure"));
        }
        svg.appendChild(g);
      }
      if (grillePixelsVisible(o, v.z)) {
        const g = el("g", {}, "grille-pixels");
        const un = { majeur: 1, mineur: 1 };
        const y0 = Math.max(0, r.y), y1 = Math.min(vue.h, r.y + r.h), x0 = Math.max(0, r.x), x1 = Math.min(vue.w, r.x + r.w);
        const ligne = (attrs) => g.appendChild(el("line", attrs));
        for (const l of lignesGrille(v, dims, vue, "x", un)) {
          const x = Math.round(ecranX(l.pos)) + 0.5;
          ligne({ x1: x, y1: y0, x2: x, y2: y1 });
        }
        for (const l of lignesGrille(v, dims, vue, "y", un)) {
          const y = Math.round(ecranY(l.pos)) + 0.5;
          ligne({ x1: x0, y1: y, x2: x1, y2: y });
        }
        svg.appendChild(g);
      }
      if (visible(o, "contoursCalque")) {
        const c = calqueActif(d);
        if (c && Array.isArray(c.bounds)) {
          const b = rectEcran(...c.bounds);
          svg.appendChild(el("rect", { x: Math.round(b.x) + 0.5, y: Math.round(b.y) + 0.5, width: Math.round(b.w), height: Math.round(b.h) }, "contour-calque"));
        }
      }
      if (visible(o, "reperes")) {
        const g = el("g", { stroke: pr("guideColor", COULEUR_REPERE), ...styleTrait(pr("guideStyle", "lines")) }, "reperes");
        const vertical = [...reperes.vertical], horizontal = [...reperes.horizontal];
        if (glisseRepere && glisseRepere.index !== null) (glisseRepere.orientation === "vertical" ? vertical : horizontal).splice(glisseRepere.index, 1);
        for (const x of vertical) { const s = Math.round(ecranX(x)) + 0.5; g.appendChild(el("line", { x1: s, y1: 0, x2: s, y2: vue.h })); }
        for (const y of horizontal) { const s = Math.round(ecranY(y)) + 0.5; g.appendChild(el("line", { x1: 0, y1: s, x2: vue.w, y2: s })); }
        svg.appendChild(g);
      }
    }
    if (glisseRepere && glisseRepere.pos !== null) {
      const vert = glisseRepere.orientation === "vertical";
      const s = vert ? ecranX(glisseRepere.pos) : ecranY(glisseRepere.pos);
      const cr = pr("guideColor", COULEUR_REPERE);
      svg.appendChild(vert ? el("line", { x1: s, y1: 0, x2: s, y2: vue.h, stroke: cr }, "repere-glisse") : el("line", { x1: 0, y1: s, x2: vue.w, y2: s, stroke: cr }, "repere-glisse"));
    }
    dessinerRegles();
  }

  function dessinerRegles() {
    regles.hidden = !o.regles;
    if (!o.regles) return;
    const vue = tailleScene(), k = window.devicePixelRatio || 1, d = PL.etat.doc;
    const cs = getComputedStyle(document.documentElement);
    const fond = cs.getPropertyValue("--bg-panel").trim() || "#151519";
    const trait = cs.getPropertyValue("--ink-muted").trim() || "#888888";
    const police = cs.getPropertyValue("--f-mono").trim() || "monospace";
    for (const [c, horiz] of [[rH, true], [rV, false]]) {
      const L = horiz ? vue.w : vue.h;
      c.width = Math.round((horiz ? L : REGLE) * k); c.height = Math.round((horiz ? REGLE : L) * k);
      const g = c.getContext("2d");
      g.setTransform(k, 0, 0, k, 0, 0);
      g.fillStyle = fond; g.fillRect(0, 0, horiz ? L : REGLE, horiz ? REGLE : L);
      if (!d) continue;
      const a = PL.vue.versDoc(0, 0), b = PL.vue.versDoc(vue.w, vue.h);
      // t159 : Préférences › Unités et règles — graduations dans l'unité choisie (px du document par unité)
      const u = PL.prefs ? PL.prefs.pxParUnite(PL.prefs.v("unitsAndRulers", "rulers"), d.resolution, d.width) : 1;
      const debut = (horiz ? Math.min(a.x, b.x) : a.y) / u, fin = (horiz ? Math.max(a.x, b.x) : b.y) / u;
      const gr = graduations(debut, fin, PL.vue.v.z * u);
      g.strokeStyle = trait; g.fillStyle = trait; g.lineWidth = 1; g.font = "9px " + police;
      g.beginPath();
      for (const m of gr.majeurs) {
        for (let i = 0; i < 5; i++) {
          const val = (m + i * gr.mineur) * u;
          const p = Math.round(horiz ? ecranX(val) : ecranY(val)) + 0.5;
          const long = i === 0 ? REGLE : REGLE / 3;
          if (horiz) { g.moveTo(p, REGLE); g.lineTo(p, REGLE - long); } else { g.moveTo(REGLE, p); g.lineTo(REGLE - long, p); }
        }
        const p = Math.round(horiz ? ecranX(m * u) : ecranY(m * u)) + 0.5;
        if (horiz) g.fillText(String(m), p + 2, 9);
        else { g.save(); g.translate(9, p + 2); g.rotate(-Math.PI / 2); g.fillText(String(m), -g.measureText(String(m)).width, 0); g.restore(); }
      }
      g.stroke();
    }
  }

  /* repères : lecture, création, déplacement, suppression */
  const besoinReperes = () => visible(o, "reperes") || (o.aimanter && o.aimanterA.reperes);
  async function relire(force = false) {
    const d = PL.etat.doc;
    if (!d) { reperes = { horizontal: [], vertical: [] }; dernierDoc = null; dessiner(); return; }
    const cle = { nom: d.name + "|" + d.width + "x" + d.height, history: d.history };
    if (!force && !relireReperes(dernierDoc, cle)) return;
    if (!besoinReperes()) { dernierDoc = null; return; }      // relu au prochain besoin
    dernierDoc = cle;
    const ma = PL.get("/reperes", true).catch(() => null);
    lecture = ma;
    const r = await ma;
    if (ma !== lecture || !r) return;
    reperes = { horizontal: r.horizontal || [], vertical: r.vertical || [] };
    dessiner();
  }
  const seuilDoc = () => SEUIL_AIMANT_PX / PL.vue.v.z;
  // un repère glissé s'aimante à tout sauf aux autres repères ; position au demi-pixel
  const positionRepere = (orientation, val) => {
    const c = ciblesAimant({ ...o, aimanterA: { ...o.aimanterA, reperes: false } }, PL.etat.doc, null);
    return Math.round(aimanter(val, orientation === "vertical" ? c.x : c.y, seuilDoc()).valeur * 2) / 2;
  };
  function repereSous(sx, sy) {
    if (!visible(o, "reperes") || o.verrouReperes) return null;
    for (const [orientation, liste] of [["vertical", reperes.vertical], ["horizontal", reperes.horizontal]]) {
      for (let i = 0; i < liste.length; i++) {
        const s = orientation === "vertical" ? ecranX(liste[i]) : ecranY(liste[i]);
        if (Math.abs((orientation === "vertical" ? sx : sy) - s) <= TOL_REPERE) return { orientation, index: i };
      }
    }
    return null;
  }
  const dansDocument = (p) => { const d = PL.etat.doc; return !!d && p.x >= 0 && p.y >= 0 && p.x <= d.width && p.y <= d.height; };
  const pointScene = (ev) => { const r = scene.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };

  // Glisser depuis une règle : un nouveau repère (horizontal depuis la règle du haut) ; relâché hors du document = rien.
  for (const [c, orientation] of [[rH, "horizontal"], [rV, "vertical"]]) {
    c.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0 || !PL.etat.doc || o.verrouReperes) return;
      ev.preventDefault();
      try { c.setPointerCapture(ev.pointerId); } catch (e) { /* pointeur déjà relâché */ }
      if (!visible(o, "reperes")) changer({ ...o, extras: true, reperes: true, afficher: { ...o.afficher, reperesCanevas: true } });
      glisseRepere = { orientation, index: null, pos: null };
    });
    c.addEventListener("pointermove", (ev) => {
      if (!glisseRepere || glisseRepere.index !== null) return;
      const p = PL.vue.versDoc(...pointScene(ev));
      glisseRepere.pos = positionRepere(orientation, orientation === "vertical" ? p.x : p.y);
      dessiner();
    });
    c.addEventListener("pointerup", async (ev) => {
      if (!glisseRepere || glisseRepere.index !== null) return;
      const g = glisseRepere; glisseRepere = null;
      const p = PL.vue.versDoc(...pointScene(ev));
      dessiner();
      if (g.pos === null || !dansDocument(p)) return;
      await PL.executer("view.newGuide", { orientation, position: g.pos });
    });
  }

  // Outil Déplacement : sur un repère, le glisser le déplace (hors du document, il est supprimé) ; ailleurs, l'outil
  // fait son travail habituel.
  const deplacer = PL.gestes.move;
  PL.gestes.move = {
    ...deplacer,
    appui(p, ev) {
      const h = repereSous(p.sx, p.sy);
      if (!h) return deplacer.appui(p, ev);
      glisseRepere = { ...h, pos: (h.orientation === "vertical" ? reperes.vertical : reperes.horizontal)[h.index] };
      dessiner();
      return undefined;
    },
    bouger(p, ev) {
      if (!glisseRepere) return deplacer.bouger(p, ev);
      glisseRepere.pos = positionRepere(glisseRepere.orientation, glisseRepere.orientation === "vertical" ? p.x : p.y);
      dessiner();
      return undefined;
    },
    async relacher(p, ev) {
      if (!glisseRepere) return deplacer.relacher(p, ev);
      const g = glisseRepere; glisseRepere = null;
      dessiner();
      if (!dansDocument(p)) await PL.executer("view.deleteGuide", { orientation: g.orientation, index: g.index });
      else await PL.executer("view.moveGuide", { orientation: g.orientation, index: g.index, position: g.pos });
      return undefined;
    },
    survol(p) {
      const h = repereSous(p.sx, p.sy);
      PL.$("#toile").style.cursor = h ? (h.orientation === "vertical" ? "ew-resize" : "ns-resize") : "default";
    },
    annuler() { if (glisseRepere) { glisseRepere = null; dessiner(); } else if (deplacer.annuler) deplacer.annuler(); },
    touche(ev) {
      if (glisseRepere && ev.key === "Escape") { glisseRepere = null; dessiner(); return true; }
      return deplacer.touche ? deplacer.touche(ev) : false;
    },
  };

  /* modes d'écran */
  function appliquerEcran() {
    document.body.classList.toggle("ecran-menus", o.ecran === "menus");
    document.body.classList.toggle("ecran-plein", o.ecran === "plein");
    try {
      if (o.ecran !== "standard" && !document.fullscreenElement && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
      if (o.ecran === "standard" && document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {});
    } catch (e) { /* cadre sans permission de plein écran : le mode reste celui de la page */ }
  }

  /* état */
  // t159 : les options vont aussi dans les préférences du dossier de données (PL.prefs.affichage), le navigateur garde
  // la copie rapide ; un enregistrement par rafale de bascules.
  let minutPrefs = null;
  function sauver() {
    try { localStorage.setItem(CLE_STOCKAGE, JSON.stringify(o)); } catch (e) { /* navigateur sans stockage */ }
    clearTimeout(minutPrefs);
    if (PL.prefs) minutPrefs = setTimeout(() => { PL.prefs.modifier("affichage", o).catch(() => {}); }, 400);
  }
  function changer(nouv) {
    const avant = o;
    o = nouv;
    sauver();
    PL.vue.v.miroir = o.miroir;
    PL.vue.pixelArt = o.pixelArt;
    if (avant.ecran !== o.ecran) appliquerEcran();
    PL.vue.dessiner();
    if (PL.dessinerFourmis) PL.dessinerFourmis();
    if (PL.dessinerNavigateur) PL.dessinerNavigateur();
    if (besoinReperes()) relire();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  }

  /* zooms */
  const centre = () => { const t = tailleScene(); return [t.w / 2, t.h / 2]; };
  const ZOOMS = {
    "view.zoomIn": () => PL.vue.zoomPalier(+1),
    "view.zoomOut": () => PL.vue.zoomPalier(-1),
    "view.fitOnScreen": () => PL.vue.ajuster(),
    "view.actualPixels": () => PL.vue.cent(),
    "view.twoHundredPercent": () => PL.vue.zoomAutour(2, ...centre()),
    "view.printSize": () => PL.vue.zoomAutour(zoomImpression(PL.etat.doc.resolution), ...centre()),
    "view.fitLayersOnScreen": () => {
      const b = bornesCalques(PL.etat.doc), t = tailleScene(), v = PL.vue.v;
      const z = Math.min(64, Math.max(0.01, Math.min((t.w - 40) / Math.max(1, b.w), (t.h - 40) / Math.max(1, b.h))));
      const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
      PL.vue.allerA({ z, ox: t.w / 2 - (v.miroir ? v.dw - cx : cx) * z, oy: t.h / 2 - cy * z });
    },
  };

  /* Options d'affichage des extras… */
  const CASES = [["contoursCalque", "photolab.affichage.contours_calque"], ["contoursSelection", "photolab.affichage.contours_selection"],
    ["grille", "photolab.affichage.grille"], ["reperes", "photolab.affichage.reperes"], ["reperesCanevas", "photolab.affichage.reperes_canevas"],
    ["grillePixels", "photolab.affichage.grille_pixels"], ["apercuPinceau", "photolab.affichage.apercu_pinceau"]];
  async function optionsExtras() {
    const cases = {};
    const r = await ouvrirDialogue(PL, {
      titre: T("photolab.affichage.options_titre"),
      construire({ corps }) {
        for (const [cle, lib] of CASES) {
          const l = document.createElement("label"); l.className = "dz-case";
          const c = document.createElement("input"); c.type = "checkbox";
          c.checked = cle in o.afficher ? o.afficher[cle] : o[cle];
          const s = document.createElement("span"); s.textContent = T(lib);
          l.append(c, s); corps.appendChild(l); cases[cle] = c;
        }
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.appliquer"), principal: true }],
    });
    if (r !== "ok") return;
    const n = copie(o);
    for (const [cle, c] of Object.entries(cases)) { if (cle in n.afficher) n.afficher[cle] = c.checked; else n[cle] = c.checked; }
    n.extras = true;
    changer(n);
  }

  PL.actions = PL.actions || {};
  for (const id of IDS_AFFICHAGE) {
    if (ZOOMS[id]) PL.actions[id] = () => { if (PL.etat.doc) ZOOMS[id](); };
    else if (id === "view.show.showExtrasOptions") PL.actions[id] = optionsExtras;
    else PL.actions[id] = () => changer(basculer(o, id));
  }

  /* clavier : F fait tourner les modes d'écran ; Échap quitte le plein écran */
  const enSaisie = (ev) => ev.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || "") || ev.target.isContentEditable);
  document.addEventListener("keydown", (ev) => {
    if (ev.defaultPrevented || enSaisie(ev) || ev.ctrlKey || ev.metaKey || ev.altKey || ev.repeat) return;
    if (document.querySelector(".pl-voile, .dz-dialogue, .menu-panneau, .flyout")) return;
    if (ev.code === "KeyF" && !ev.shiftKey) { ev.preventDefault(); changer({ ...o, ecran: ecranSuivant(o.ecran) }); }
    else if (ev.key === "Escape" && o.ecran !== "standard") { ev.preventDefault(); changer({ ...o, ecran: "standard" }); }
  });
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement && o.ecran !== "standard") changer({ ...o, ecran: "standard" });     // sortie par le navigateur
  });

  /* branchements */
  // t159 : les options enregistrées dans les préférences (autre navigateur, autre machine) l'emportent au chargement
  if (PL.prefs) PL.prefs.surChange.push((e) => {
    if (!e.affichage) return;
    const n = normaliserOptions(e.affichage);
    if (JSON.stringify(n) === JSON.stringify(o)) { PL.vue.dessiner(); return; }
    const avant = o;
    o = n;
    try { localStorage.setItem(CLE_STOCKAGE, JSON.stringify(o)); } catch (er) { /* facultatif */ }
    PL.vue.v.miroir = o.miroir; PL.vue.pixelArt = o.pixelArt;
    if (avant.ecran !== o.ecran) appliquerEcran();
    PL.vue.dessiner();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  });
  PL.affichage = {
    get options() { return o; },
    voir: (cle) => visible(o, cle),
    decorer: (menus) => decorerAffichage(menus, o),
    // point de geste aimanté (outils géométriques) ; Ctrl tenu l'interrompt
    aimanterPointDoc(p, ev) {
      if (!OUTILS_AIMANTES.has(PL.etat.outil) || (ev && (ev.ctrlKey || ev.metaKey))) return p;
      const q = aimanterPoint(p, ciblesAimant(o, PL.etat.doc, reperes, PL.mesure ? PL.mesure.tranches : null), seuilDoc());
      return { ...p, x: q.x, y: q.y };
    },
    aimanterDeplacement(dx, dy) {
      const d = PL.etat.doc;
      if (!d) return { dx, dy };
      const c = calqueActif(d);
      const bornes = d.hasSelection && Array.isArray(d.selectionBounds) ? d.selectionBounds : c && Array.isArray(c.bounds) ? c.bounds : null;
      return bornes ? aimanterDeplacement(bornes, dx, dy, ciblesAimant(o, d, reperes, PL.mesure ? PL.mesure.tranches : null), seuilDoc()) : { dx, dy };
    },
    get reperes() { return reperes; },
    relire,
  };
  PL.vue.v.miroir = o.miroir;
  PL.vue.pixelArt = o.pixelArt;
  PL.surVue.push(dessiner);
  PL.surDoc.push(() => { relire(); dessiner(); });
  appliquerEcran();
  if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
}
