// mod-courbes.js — Courbes et Niveaux sur mesure (t138 B4). Deux éditeurs réutilisables (dialogue non modal ici ;
// panneau Propriétés d'un calque de réglage en B5) et leurs fonctions PURES (qa/courbes.test.mjs).
// Le moteur fait foi : pendant un glisser, l'aperçu est une table de correspondance (LUT) appliquée en JS à une copie
// du dernier rendu RÉEL ; au relâchement, l'aperçu est recalculé par le moteur (POST /apercu) sur une copie du document.
// Tout ce que ces fonctions produisent doit passer la liste blanche du pont : points entiers 0..255, x strictement
// croissants, 2..19 points ; niveaux bornés comme le registre (inBlack 0..253, gamma 0.01..9.99, inWhite 2..255…).

import { coquilleReglage, derniereGagne, identiteDocument, titreDialogue, DELAI_APERCU, chargerImage } from "./mod-dialogue-reglage.js";
import { libelleParam } from "./mod-champs.js";
import { maxSideRequete } from "./mod-cycle.js";

/* ───────────── fonctions PURES ───────────── */

export const MIN_POINTS = 2;
export const MAX_POINTS = 19;            // borne du registre (« 2..19 points »)
export const ECART_MIN = 4;              // un clic à moins de 4 niveaux d'un point existant ne crée pas de doublon
export const IDENTITE = Object.freeze([[0, 0], [255, 255]]);
export const NIVEAUX_DEFAUT = Object.freeze({ inBlack: 0, gamma: 1, inWhite: 255, outBlack: 0, outWhite: 255 });

// Canaux de l'écran -> clés des paramètres de commande et de l'histogramme (GET /histogramme : r, g, b, l).
export const CANAUX = Object.freeze([
  { id: "rvb", cle: "photolab.canal.rvb", courbe: "points", niveaux: null, histo: "l", lut: null },
  { id: "rouge", cle: "photolab.canal.rouge", courbe: "red", niveaux: "red", histo: "r", lut: "r" },
  { id: "vert", cle: "photolab.canal.vert", courbe: "green", niveaux: "green", histo: "g", lut: "g" },
  { id: "bleu", cle: "photolab.canal.bleu", courbe: "blue", niveaux: "blue", histo: "b", lut: "b" },
]);

const borne = (v, a, b) => Math.min(b, Math.max(a, v));
const entier255 = (v) => borne(Math.round(Number(v) || 0), 0, 255);

// Une liste de points quelconque (inspect, saisie) -> liste admise : entiers bornés, triée, x strictement croissants
// (un doublon de x garde le dernier), 2..19 points ; illisible ou trop courte -> identité.
export function normaliserPoints(points) {
  if (!Array.isArray(points)) return IDENTITE.map((p) => p.slice());
  const parX = new Map();
  for (const p of points) {
    if (!Array.isArray(p) || p.length < 2) continue;
    const x = Number(p[0]), y = Number(p[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    parX.set(entier255(x), entier255(y));
  }
  let r = [...parX].sort((a, b) => a[0] - b[0]).map(([x, y]) => [x, y]);
  if (r.length < MIN_POINTS) return IDENTITE.map((p) => p.slice());
  // Au-delà de 19 points : on garde les extrémités et on retire les points intérieurs les plus serrés.
  while (r.length > MAX_POINTS) {
    let k = 1, ecart = Infinity;
    for (let i = 1; i < r.length - 1; i++) { const e = r[i + 1][0] - r[i - 1][0]; if (e < ecart) { ecart = e; k = i; } }
    r.splice(k, 1);
  }
  return r;
}

// Spline cubique naturelle du MOTEUR (photocraft compose/adjust.rs curve_lut) : peut déborder entre deux points comme
// celle de Photoshop, bornée à 0..1, constante hors des extrémités ; échantillonnée sur `n` cases de 0 à 1.
// C'est la SEULE courbe de l'écran (tracé, LUT de l'aperçu pendant un glisser, test d'identité) : le plan demandait une
// monotone de Fritsch-Carlson, mais elle ne déborde jamais là où photocraft déborde — l'aperçu JS et le tracé auraient
// montré une autre image que le rendu du moteur. Identité avec photocraft d'abord.
function splineNaturelle(points, n) {
  const p = normaliserPoints(points);
  const np = p.length;
  const x = p.map((q) => q[0] / 255), y = p.map((q) => q[1] / 255);
  const m2 = new Array(np).fill(0);
  if (np > 2) {
    const c = new Array(np).fill(0), dd = new Array(np).fill(0);
    for (let i = 1; i < np - 1; i++) {
      const h0 = x[i] - x[i - 1], h1 = x[i + 1] - x[i];
      const a = h0 / 6, b = (h0 + h1) / 3, cc = h1 / 6;
      const r = (y[i + 1] - y[i]) / h1 - (y[i] - y[i - 1]) / h0;
      const den = b - a * c[i - 1];
      c[i] = cc / den; dd[i] = (r - a * dd[i - 1]) / den;
    }
    for (let i = np - 2; i >= 1; i--) m2[i] = dd[i] - c[i] * m2[i + 1];
  }
  const out = new Float64Array(n);
  let i = 0;
  for (let k = 0; k < n; k++) {
    const t = k / (n - 1);
    let v;
    if (t <= x[0]) v = y[0];
    else if (t >= x[np - 1]) v = y[np - 1];
    else {
      while (i < np - 2 && t > x[i + 1]) i++;
      const h = x[i + 1] - x[i], a = (x[i + 1] - t) / h, b = (t - x[i]) / h;
      v = a * y[i] + b * y[i + 1] + ((a * a * a - a) * m2[i] + (b * b * b - b) * m2[i + 1]) * h * h / 6;
    }
    out[k] = borne(v, 0, 1);
  }
  return out;
}

// Courbe du moteur en 256 valeurs 0..255 : c'est elle que l'écran DESSINE (ce qu'on voit est ce que le moteur rendra).
export function courbeMoteur(points) {
  const s = splineNaturelle(points, 256);
  for (let k = 0; k < 256; k++) s[k] *= 255;
  return s;
}

// Le moteur applique Courbes et Niveaux par des tables de TAILLE_LUT cases sur 0..1, lues avec interpolation linéaire
// (adjust.rs : LUT_SIZE = 4096, fn lut). L'aperçu JS refait exactement ce chemin, puis arrondit en 8 bits.
export const TAILLE_LUT = 4096;
export function lireTable(table, v) {
  const x = borne(v, 0, 1) * (table.length - 1);
  const i = Math.floor(x), j = Math.min(i + 1, table.length - 1), f = x - i;
  return table[i] * (1 - f) + table[j] * f;
}
const versLut8 = (table) => { const l = new Uint8ClampedArray(256); for (let i = 0; i < 256; i++) l[i] = Math.round(lireTable(table, i / 255) * 255); return l; };

// LUT 8 bits de la courbe, par le chemin exact du moteur (spline naturelle sur TAILLE_LUT cases, lecture interpolée).
export function lutCourbe(points) { return versLut8(splineNaturelle(points, TAILLE_LUT)); }

// Niveaux d'un canal selon le MOTEUR (adjust.rs levels_q), valeurs en 0..1. ch = {inBlack, gamma, inWhite, outBlack,
// outWhite} en niveaux 0..255 (comme les paramètres de commande). quantum = 255 en 8 bits : l'entrée est un niveau
// entier et l'étirement d'entrée est arrondi demi vers le haut AVANT le gamma (Photoshop travaille en niveaux entiers).
// gamma > 1 : pied d'ombre (minimum doux p = 10 entre u^(1/g) et la droite 0.93·2^g·u), sinon u^(1/g) exact.
export function niveauxMoteur(ch, v, quantum = 255) {
  const n = normaliserNiveaux(ch);
  const noir = n.inBlack / 255, blanc = n.inWhite / 255;
  const etendue = Math.max(blanc - noir, 1e-6);
  let u;
  if (Number.isFinite(quantum) && quantum >= 1) {
    const vq = Math.round(v * quantum) / quantum;
    u = Math.floor(borne((vq - noir) / etendue, 0, 1) * quantum + 0.5 + 1e-3) / quantum;
  } else u = borne((v - noir) / etendue, 0, 1);
  const g = Math.max(n.gamma, 0.01);
  let t;
  if (g > 1) {
    const puissance = u ** (1 / g), droite = 0.93 * 2 ** g * u;
    if (puissance <= 1e-6 || droite <= 1e-6) t = Math.min(puissance, droite);
    else { const p = 10; t = (puissance ** -p + droite ** -p) ** (-1 / p); }
  } else t = u ** (1 / g);
  return n.outBlack / 255 + t * (n.outWhite / 255 - n.outBlack / 255);
}
function tableNiveaux(composite, canal) {
  const t = new Float64Array(TAILLE_LUT);
  for (let k = 0; k < TAILLE_LUT; k++) t[k] = niveauxMoteur(canal, niveauxMoteur(composite, k / (TAILLE_LUT - 1)));
  return t;
}
// LUT 8 bits d'un canal de Niveaux (composite neutre), chemin exact du moteur.
export function lutNiveaux(v) { return versLut8(tableNiveaux(NIVEAUX_DEFAUT, v)); }

export function estLutIdentite(l) {
  for (let i = 0; i < 256; i++) if (l[i] !== i) return false;
  return true;
}
// Une courbe neutre ne s'envoie pas (le moteur garde l'identité par défaut).
export function estCourbeIdentite(points) { return estLutIdentite(lutCourbe(points)); }

// Ajout d'un point (clic dans la grille) -> {points, index} ; null si refusé (déjà 19 points, ou à moins de
// ECART_MIN d'un x existant : on n'empile pas deux points au même endroit).
export function ajouterPoint(points, x, y) {
  const p = normaliserPoints(points);
  const xi = entier255(x), yi = entier255(y);
  if (p.length >= MAX_POINTS) return null;
  if (p.some((q) => Math.abs(q[0] - xi) < ECART_MIN)) return null;
  const r = p.map((q) => q.slice());
  let i = r.findIndex((q) => q[0] > xi);
  if (i < 0) i = r.length;
  r.splice(i, 0, [xi, yi]);
  return { points: r, index: i };
}

// Index du point le plus proche à moins de `rayon` (unités de niveaux), sinon -1.
export function pointProche(points, x, y, rayon) {
  let k = -1, best = Infinity;
  (points || []).forEach((q, i) => {
    const d = Math.hypot(q[0] - x, q[1] - y);
    if (d <= rayon && d < best) { best = d; k = i; }
  });
  return k;
}

// Déplacement du point i : x strictement entre ses voisins, les extrémités gardent leur x ; y borné 0..255.
// -> nouvelle liste (null si i invalide).
export function deplacerPoint(points, i, x, y) {
  const p = normaliserPoints(points);
  if (!Number.isInteger(i) || i < 0 || i >= p.length) return null;
  const r = p.map((q) => q.slice());
  let nx;
  if (i === 0 || i === r.length - 1) nx = r[i][0];
  else nx = borne(Math.round(Number(x) || 0), r[i - 1][0] + 1, r[i + 1][0] - 1);
  r[i] = [nx, entier255(y)];
  return r;
}

// Retrait du point i : jamais une extrémité, jamais sous 2 points. -> nouvelle liste, ou null si refusé.
export function retirerPoint(points, i) {
  const p = normaliserPoints(points);
  if (!Number.isInteger(i) || i <= 0 || i >= p.length - 1 || p.length <= MIN_POINTS) return null;
  const r = p.map((q) => q.slice());
  r.splice(i, 1);
  return r;
}

// Niveaux d'un canal bornés comme le registre : entiers, inBlack 0..253, inWhite 2..255 avec inBlack <= inWhite - 2,
// gamma 0.01..9.99 (deux décimales), sorties 0..255. Une valeur absente ou illisible prend le défaut.
export function normaliserNiveaux(v) {
  const s = v && typeof v === "object" ? v : {};
  const nb = (k, def) => { const n = Number(s[k]); return Number.isFinite(n) ? n : def; };
  let inBlack = borne(Math.round(nb("inBlack", 0)), 0, 253);
  let inWhite = borne(Math.round(nb("inWhite", 255)), 2, 255);
  if (inWhite < inBlack + 2) {
    // le curseur qui vient de bouger n'est pas connu ici : on écarte le blanc, sinon on recule le noir
    if (inBlack + 2 <= 255) inWhite = inBlack + 2; else { inWhite = 255; inBlack = 253; }
  }
  const gamma = Math.round(borne(nb("gamma", 1), 0.01, 9.99) * 100) / 100;
  return {
    inBlack, gamma, inWhite,
    outBlack: borne(Math.round(nb("outBlack", 0)), 0, 255),
    outWhite: borne(Math.round(nb("outWhite", 255)), 0, 255),
  };
}
export function estNiveauxNeutres(v) {
  const n = normaliserNiveaux(v);
  return Object.keys(NIVEAUX_DEFAUT).every((k) => n[k] === NIVEAUX_DEFAUT[k]);
}

// Curseur gris des Niveaux (photocraft gamma_pos / gamma_from_pos) : sa position est l'entrée qui sort en gris 50 %.
export function curseurDepuisGamma(gamma, noir, blanc) {
  const g = borne(Number(gamma) || 1, 0.01, 9.99);
  return noir + (blanc - noir) * 0.5 ** g;
}
export function gammaDepuisCurseur(pos, noir, blanc) {
  const t = borne((pos - noir) / Math.max(1, blanc - noir), 0.01, 0.99);
  return Math.round(borne(Math.log(t) / Math.log(0.5), 0.01, 9.99) * 100) / 100;
}

// Applique trois LUT à une COPIE de pixels RGBA ({data, width, height}) ; alpha intact ; une LUT absente = identité.
// `sortie` (facultatif) : tampon de même taille réutilisé d'un geste à l'autre (pas d'allocation par trame).
export function appliquerLuts(donnees, luts, sortie) {
  const src = donnees.data;
  const out = sortie && sortie.length === src.length ? sortie : new Uint8ClampedArray(src.length);
  const { r, g, b } = luts || {};
  for (let i = 0; i < src.length; i += 4) {
    out[i] = r ? r[src[i]] : src[i];
    out[i + 1] = g ? g[src[i + 1]] : src[i + 1];
    out[i + 2] = b ? b[src[i + 2]] : src[i + 2];
    out[i + 3] = src[i + 3];
  }
  return { data: out, width: donnees.width, height: donnees.height };
}

// Composition comme le moteur (tone_luts_q) : Courbes = composite(canal(x)), Niveaux = canal(composite(x)), chaque
// rangée en table de 4096 cases lue par interpolation. etat = {rvb, rouge, vert, bleu} -> {r, g, b} (LUT 8 bits).
export function lutsCourbes(etat) {
  const m = splineNaturelle(etat && etat.rvb, TAILLE_LUT);
  const un = (pts) => {
    const c = splineNaturelle(pts, TAILLE_LUT);
    for (let k = 0; k < TAILLE_LUT; k++) c[k] = lireTable(m, c[k]);
    return versLut8(c);
  };
  return { r: un(etat && etat.rouge), g: un(etat && etat.vert), b: un(etat && etat.bleu) };
}
export function lutsNiveaux(etat) {
  const m = etat && etat.rvb;
  return { r: versLut8(tableNiveaux(m, etat && etat.rouge)), g: versLut8(tableNiveaux(m, etat && etat.vert)), b: versLut8(tableNiveaux(m, etat && etat.bleu)) };
}

// Histogramme (256 comptes) -> chaîne `d` d'un <path> plein, échelle racine carrée (un pic de blanc pur n'écrase pas
// le reste). Coordonnées SVG : x de 0 à largeur, base en bas (y = hauteur).
export function cheminHistogramme(h, largeur, hauteur) {
  const v = Array.isArray(h) || ArrayBuffer.isView(h) ? Array.from(h).slice(0, 256) : [];
  while (v.length < 256) v.push(0);
  const max = Math.sqrt(Math.max(0, ...v.map((x) => Number(x) || 0)));
  const f = (n) => Math.round(n * 100) / 100;
  const parts = ["M0 " + f(hauteur)];
  for (let i = 0; i < 256; i++) {
    const c = Math.max(0, Number(v[i]) || 0);
    const y = max > 0 ? hauteur - (Math.sqrt(c) / max) * hauteur : hauteur;
    parts.push("L" + f((i / 256) * largeur) + " " + f(y), "L" + f(((i + 1) / 256) * largeur) + " " + f(y));
  }
  parts.push("L" + f(largeur) + " " + f(hauteur), "Z");
  return parts.join(" ");
}

// État de l'éditeur -> paramètres de commande. Courbes : `points` (RVB) ou `red/green/blue` ; un canal neutre n'est
// JAMAIS envoyé (le moteur le garde à l'identité). {complet: true} (calque de réglage, B5) envoie aussi les canaux
// neutres, pour qu'un canal remis à plat le soit aussi dans le calque (setAdjustment FUSIONNE).
export function paramsCourbes(etat, { complet = false } = {}) {
  const p = {};
  for (const c of CANAUX) {
    const pts = normaliserPoints(etat && etat[c.id]);
    if (complet || !estCourbeIdentite(pts)) p[c.courbe] = pts;
  }
  return p;
}
// Niveaux : le composite aux clés du haut, chaque canal sous red/green/blue ; neutre = absent (sauf complet).
export function paramsNiveaux(etat, { complet = false } = {}) {
  const p = {};
  for (const c of CANAUX) {
    const n = normaliserNiveaux(etat && etat[c.id]);
    if (!complet && estNiveauxNeutres(n)) continue;
    if (c.niveaux) p[c.niveaux] = n; else Object.assign(p, n);
  }
  return p;
}
// Inverse (valeurs initiales d'un calque de réglage : depuisInspect de B5 rend des paramètres de commande).
export function etatDepuisParams(sorte, params) {
  const s = params && typeof params === "object" ? params : {};
  const etat = {};
  for (const c of CANAUX) {
    if (sorte === "courbes") etat[c.id] = normaliserPoints(s[c.courbe]);
    else etat[c.id] = normaliserNiveaux(c.niveaux ? s[c.niveaux] : s);
  }
  return etat;
}
export function etatNeutre(sorte) { return etatDepuisParams(sorte, {}); }

// Conversions grille <-> niveaux : la grille est un carré de `taille` px, sortie 255 en haut.
export function versGrille(v, taille) { return { x: (v[0] / 255) * taille, y: taille - (v[1] / 255) * taille }; }
export function depuisGrille(px, py, taille) {
  return [borne((px / taille) * 255, 0, 255), borne(((taille - py) / taille) * 255, 0, 255)];
}
// Glisser un point HORS de la grille (au-delà de `marge` px) le retire, comme photocraft (DRAG_OFF = 12).
export const MARGE_RETRAIT = 12;
export function horsGrille(px, py, taille, marge = MARGE_RETRAIT) {
  return px < -marge || py < -marge || px > taille + marge || py > taille + marge;
}

// Commande destructive de chaque éditeur.
export const COMMANDES = Object.freeze({ courbes: "image.adjustments.curves", niveaux: "image.adjustments.levels" });

/* ───────────── côté DOM : éditeurs réutilisables ───────────── */

const SVG = "http://www.w3.org/2000/svg";
const svgEl = (nom, attrs = {}) => {
  const e = document.createElementNS(SVG, nom);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  return e;
};
const TAILLE = 256;                     // côté de la grille des Courbes en unités SVG (une unité = un niveau)
const COTE_POINT = 7;
const RAYON_PRISE = 9;                  // px écran, comme photocraft (HIT_RADIUS)

// Une saisie au clavier est en cours dans l'éditeur (champ numérique qui a le focus) : un état relu ne doit pas
// l'écraser sous les doigts (t138 B5, relecture). Le focus de la grille seule n'en est pas une : après un clic sur la
// courbe elle le garde, et un Ctrl+Z doit pouvoir se voir sans cliquer ailleurs.
function saisieActive(racine) {
  const a = typeof document !== "undefined" ? document.activeElement : null;
  return !!a && a !== racine && racine.contains(a) && a.tagName === "INPUT";
}

function selecteurCanal(T, cleLibelle, surChoix) {
  const ligne = document.createElement("div"); ligne.className = "pl-ton-canal";
  const lib = document.createElement("label"); lib.textContent = T(cleLibelle);
  const sel = document.createElement("select"); sel.className = "pl-rg-choix";
  const LIBELLES = { rvb: T("photolab.canal.rvb"), rouge: T("photolab.canal.rouge"), vert: T("photolab.canal.vert"), bleu: T("photolab.canal.bleu") };
  for (const c of CANAUX) { const o = document.createElement("option"); o.value = c.id; o.textContent = LIBELLES[c.id]; sel.appendChild(o); }
  sel.id = "pl-ton-canal-" + Math.random().toString(36).slice(2, 8); lib.htmlFor = sel.id;
  sel.addEventListener("change", () => surChoix(sel.value));
  ligne.append(lib, sel);
  return { el: ligne, sel };
}

function champNombre(libelle, { min, max, pas = 1 }, surSaisie) {
  const l = document.createElement("label"); l.className = "pl-ton-num";
  const s = document.createElement("span"); s.textContent = libelle;
  const n = document.createElement("input"); n.type = "number"; n.className = "pl-rg-nombre";
  n.min = String(min); n.max = String(max); n.step = String(pas);
  n.addEventListener("change", () => surSaisie(n.value));
  l.append(s, n);
  return {
    el: l, n,
    ecrire(v) { n.value = v; n.dataset.ecrit = n.value; },
    // OK / Entrée pendant une saisie (sans « change ») : la valeur tapée compte, comme dans le dialogue générique.
    lire() { if (!n.disabled && n.value !== (n.dataset.ecrit || "")) surSaisie(n.value); },
  };
}

// Éditeur de Courbes dans `conteneur`. options : {etat?, histogramme?: {r,g,b,l}, surChangement(params, {fin, luts,
// etat}), complet?: bool, cible?: bool, T?}.
//  - sans cible (dialogue destructif) : surChangement est appelé pendant un glisser (fin: false, luts pour l'aperçu JS)
//    et à chaque geste terminé (fin: true) ; params ne contient que les canaux non neutres.
//  - cible: true (calque de réglage, B5) : le rendu CONTIENT déjà le calque, une LUT JS doublerait l'effet. Seules la
//    courbe / les poignées bougent pendant le glisser ; surChangement n'est appelé qu'au relâchement (fin: true, luts
//    null), avec les quatre canaux (complet) : B5 en fait un `layer.setAdjustment {layer, ...difference}`.
// -> {el, etat(), params(), luts(), lireSaisies(), poserEtat(e), poserHistogramme(h), detruire()}.
export function construireEditeurCourbes(conteneur, opts = {}) {
  const T = opts.T || ((cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle));
  let etat = opts.etat ? etatDepuisParams("courbes", paramsCourbes(opts.etat, { complet: true })) : etatNeutre("courbes");
  let histo = opts.histogramme || null;
  let canal = "rvb";
  let sel = -1;                          // point actif
  let glisse = null;                     // {pointerId}
  let geste = false;                     // un appui commencé sur la grille, pas encore relâché

  const racine = document.createElement("div"); racine.className = "pl-ton pl-courbes";
  const choix = selecteurCanal(T, "photolab.courbes.canal", (c) => { canal = c; sel = -1; dessiner(); });
  const svg = svgEl("svg", { viewBox: `0 0 ${TAILLE} ${TAILLE}`, class: "pl-ton-grille", tabindex: "0", role: "application" });
  svg.setAttribute("aria-label", T("photolab.courbes.titre"));
  svg.setAttribute("aria-description", T("photolab.courbes.aide"));
  const fond = svgEl("rect", { x: 0, y: 0, width: TAILLE, height: TAILLE, class: "pl-ton-fond" });
  const gHisto = svgEl("path", { class: "pl-ton-histo" });
  const gGrille = svgEl("g", { class: "pl-ton-quadrillage" });
  for (const q of [64, 128, 192]) {
    gGrille.append(svgEl("line", { x1: q, y1: 0, x2: q, y2: TAILLE }), svgEl("line", { x1: 0, y1: q, x2: TAILLE, y2: q }));
  }
  const diag = svgEl("line", { x1: 0, y1: TAILLE, x2: TAILLE, y2: 0, class: "pl-ton-diagonale" });
  const gAutres = svgEl("g", { class: "pl-ton-autres" });
  const courbe = svgEl("path", { class: "pl-ton-courbe" });
  const gPoints = svgEl("g", { class: "pl-ton-points" });
  svg.append(fond, gHisto, gGrille, diag, gAutres, courbe, gPoints);

  const ligneNum = document.createElement("div"); ligneNum.className = "pl-ton-nums";
  const fEntree = champNombre(T("photolab.courbes.entree"), { min: 0, max: 255 }, (v) => saisir(v, null));
  const fSortie = champNombre(T("photolab.courbes.sortie"), { min: 0, max: 255 }, (v) => saisir(null, v));
  ligneNum.append(fEntree.el, fSortie.el);
  racine.append(choix.el, svg, ligneNum);
  conteneur.appendChild(racine);

  const points = () => etat[canal];
  const tracer = (f) => { let d = ""; for (let x = 0; x < 256; x++) d += (x ? "L" : "M") + x + " " + Math.round((255 - f[x]) * 100) / 100 + " "; return d.trim(); };
  const classeCanal = (id) => "canal-" + id;

  function dessiner() {
    choix.sel.value = canal;
    const c = CANAUX.find((x) => x.id === canal);
    gHisto.setAttribute("d", histo && histo[c.histo] ? cheminHistogramme(histo[c.histo], TAILLE, TAILLE) : "");
    gHisto.setAttribute("class", "pl-ton-histo " + classeCanal(canal));
    // Comme Photoshop : sur le composite, les courbes des canaux modifiés restent visibles en filigrane.
    gAutres.replaceChildren();
    if (canal === "rvb") {
      for (const k of CANAUX.slice(1)) {
        if (estCourbeIdentite(etat[k.id])) continue;
        gAutres.appendChild(svgEl("path", { d: tracer(courbeMoteur(etat[k.id])), class: "pl-ton-courbe-autre " + classeCanal(k.id) }));
      }
    }
    courbe.setAttribute("d", tracer(courbeMoteur(points())));
    courbe.setAttribute("class", "pl-ton-courbe " + classeCanal(canal));
    gPoints.replaceChildren();
    points().forEach((q, i) => {
      const r = svgEl("rect", { x: q[0] - COTE_POINT / 2, y: 255 - q[1] - COTE_POINT / 2, width: COTE_POINT, height: COTE_POINT,
        class: "pl-ton-point" + (i === sel ? " actif" : "") });
      gPoints.appendChild(r);
    });
    const p = points()[sel];
    fEntree.n.disabled = fSortie.n.disabled = !p;
    fEntree.ecrire(p ? String(p[0]) : ""); fSortie.ecrire(p ? String(p[1]) : "");
  }

  const complet = !!(opts.complet || opts.cible);
  function signaler(fin) {
    if (!opts.surChangement || (opts.cible && !fin)) return;
    opts.surChangement(paramsCourbes(etat, { complet }), { fin, luts: opts.cible ? null : lutsCourbes(etat), etat: copie() });
  }
  const copie = () => Object.fromEntries(CANAUX.map((c) => [c.id, etat[c.id].map((q) => q.slice())]));
  function poser(pts) { etat = { ...etat, [canal]: pts }; }

  function saisir(x, y) {
    const p = points()[sel];
    if (!p) return;
    const r = deplacerPoint(points(), sel, x == null ? p[0] : x, y == null ? p[1] : y);
    if (r) { poser(r); dessiner(); signaler(true); }
  }

  // Pointeur -> coordonnées dans la grille (unités SVG, une unité = un niveau).
  function local(ev) {
    const r = svg.getBoundingClientRect();
    const k = TAILLE / Math.max(1, r.width);
    return { px: (ev.clientX - r.left) * k, py: (ev.clientY - r.top) * k, k };
  }

  svg.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    const { px, py, k } = local(ev);
    const [vx, vy] = depuisGrille(px, py, TAILLE);
    let i = pointProche(points(), vx, vy, RAYON_PRISE * k);
    if (i < 0) {
      const a = ajouterPoint(points(), vx, vy);
      // Refusé : trop près d'un x existant -> on prend ce point-là ; 19 points -> rien (photocraft : courbe pleine).
      if (a) { poser(a.points); i = a.index; }
      else i = points().findIndex((q) => Math.abs(q[0] - Math.round(vx)) < ECART_MIN);
    }
    if (i < 0) return;
    sel = i;
    glisse = { pointerId: ev.pointerId };
    geste = true;
    svg.setPointerCapture(ev.pointerId);
    svg.focus();
    ev.preventDefault();
    dessiner();
    signaler(false);
  });
  svg.addEventListener("pointermove", (ev) => {
    if (!glisse || sel < 0) return;
    const { px, py } = local(ev);
    if (horsGrille(px, py, TAILLE)) {
      const r = retirerPoint(points(), sel);
      if (r) { poser(r); sel = -1; glisse = null; dessiner(); signaler(false); return; }
    }
    const [vx, vy] = depuisGrille(px, py, TAILLE);
    const r = deplacerPoint(points(), sel, vx, vy);
    if (r) { poser(r); dessiner(); signaler(false); }
  });
  const fin = (ev) => {
    if (!geste) return;                   // relâchement sans geste commencé ici (fin d'un double-clic…)
    geste = false;
    try { svg.releasePointerCapture(ev.pointerId); } catch (e) { /* capture perdue */ }
    glisse = null;
    signaler(true);                       // relâchement (y compris après un retrait par glisser hors grille)
  };
  svg.addEventListener("pointerup", fin);
  // Annulation (geste système, capture perdue) : le point garde sa dernière position et la prise se termine.
  svg.addEventListener("pointercancel", fin);
  svg.addEventListener("lostpointercapture", fin);
  svg.addEventListener("dblclick", (ev) => {
    const { px, py, k } = local(ev);
    const [vx, vy] = depuisGrille(px, py, TAILLE);
    const i = pointProche(points(), vx, vy, RAYON_PRISE * k);
    const r = i >= 0 ? retirerPoint(points(), i) : null;
    if (r) { poser(r); sel = -1; dessiner(); signaler(true); }
  });
  // Clavier (la grille a le focus) : flèches = déplacer le point actif (Maj = 10 niveaux), Suppr = le retirer.
  svg.addEventListener("keydown", (ev) => {
    const p = points()[sel];
    if (!p) return;
    const pas = ev.shiftKey ? 10 : 1;
    const d = { ArrowLeft: [-pas, 0], ArrowRight: [pas, 0], ArrowUp: [0, pas], ArrowDown: [0, -pas] }[ev.key];
    if (d) { ev.preventDefault(); saisir(p[0] + d[0], p[1] + d[1]); return; }
    if (ev.key === "Delete" || ev.key === "Backspace") {
      ev.preventDefault();
      const r = retirerPoint(points(), sel);
      if (r) { poser(r); sel = -1; dessiner(); signaler(true); }
    }
  });

  dessiner();
  return {
    el: racine,
    etat: copie,
    params: () => paramsCourbes(etat, { complet }),
    luts: () => lutsCourbes(etat),
    lireSaisies() { fEntree.lire(); fSortie.lire(); },
    // Le point actif reste choisi s'il existe encore (un état relu après un relâchement ne doit pas le désélectionner).
    poserEtat(e) {
      etat = etatDepuisParams("courbes", paramsCourbes(e || {}, { complet: true }));
      if (!(sel >= 0 && sel < points().length)) sel = -1;
      dessiner();
    },
    // Glisser en cours ou saisie au clavier : B5 diffère alors l'état relu (poserEtat) jusqu'à la fin du geste.
    enGeste: () => geste || !!glisse || saisieActive(racine),
    poserHistogramme(h) { histo = h || null; dessiner(); },
    detruire() { racine.remove(); },
  };
}

// Éditeur de Niveaux : histogramme, curseurs d'entrée (noir, gris = gamma, blanc) et de sortie (noir, blanc), champs
// numériques liés. Même contrat que construireEditeurCourbes (options cible / complet comprises).
export function construireEditeurNiveaux(conteneur, opts = {}) {
  const T = opts.T || ((cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle));
  let etat = opts.etat ? etatDepuisParams("niveaux", paramsNiveaux(opts.etat, { complet: true })) : etatNeutre("niveaux");
  let histo = opts.histogramme || null;
  let canal = "rvb";

  const racine = document.createElement("div"); racine.className = "pl-ton pl-niveaux";
  const choix = selecteurCanal(T, "photolab.niveaux.canal", (c) => { canal = c; dessiner(); });
  const titreE = document.createElement("div"); titreE.className = "pl-ton-sous"; titreE.textContent = T("photolab.niveaux.entree");
  const HH = 100;
  // Même repère horizontal que les glissières (-6..262) : la poignée noire tombe pile sous la case 0 de l'histogramme.
  const svgH = svgEl("svg", { viewBox: `-6 0 ${TAILLE + 12} ${HH}`, preserveAspectRatio: "none", class: "pl-ton-histo-niv", role: "img" });
  svgH.setAttribute("aria-label", T("photolab.niveaux.titre"));
  const histoPath = svgEl("path", { class: "pl-ton-histo" });
  svgH.append(svgEl("rect", { x: -6, y: 0, width: TAILLE + 12, height: HH, class: "pl-ton-fond" }), histoPath);

  // Une glissière = un SVG fin de 256 unités de large, des triangles comme photocraft (handle()).
  function glissiere(poignees, surGlisse) {
    const s = svgEl("svg", { viewBox: `-6 0 ${TAILLE + 12} 12`, preserveAspectRatio: "none", class: "pl-ton-glissiere" });
    s.appendChild(svgEl("line", { x1: 0, y1: 1, x2: TAILLE - 1, y2: 1, class: "pl-ton-piste" }));
    const tri = poignees.map((p) => { const t = svgEl("polygon", { class: "pl-ton-poignee " + p }); s.appendChild(t); return t; });
    let prise = -1, dernierX = 0;
    const valeur = (ev) => {
      const r = s.getBoundingClientRect();
      return ((ev.clientX - r.left) / Math.max(1, r.width)) * (TAILLE + 12) - 6;
    };
    s.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      const x = valeur(ev);
      // la poignée la plus proche (à égalité, la dernière posée : le blanc sur le noir quand ils se touchent à droite)
      let best = Infinity;
      tri.forEach((t, i) => { const d = Math.abs(Number(t.dataset.x) - x); if (d <= best) { best = d; prise = i; } });
      s.setPointerCapture(ev.pointerId);
      ev.preventDefault();
      dernierX = x;
      surGlisse(prise, x, false);
    });
    s.addEventListener("pointermove", (ev) => { if (prise >= 0) { dernierX = valeur(ev); surGlisse(prise, dernierX, false); } });
    // prise remise à -1 AVANT de relâcher la capture : lostpointercapture, qui peut suivre aussitôt, ne termine pas deux fois.
    const fin = (ev, garder) => {
      if (prise < 0) return;
      const k = prise; prise = -1;
      const x = garder ? dernierX : valeur(ev);
      try { s.releasePointerCapture(ev.pointerId); } catch (e) { /* capture perdue */ }
      surGlisse(k, x, true);
    };
    s.addEventListener("pointerup", (ev) => fin(ev, false));
    // Annulation ou capture perdue : la poignée garde sa dernière valeur (les coordonnées de l'événement sont sans objet).
    s.addEventListener("pointercancel", (ev) => fin(ev, true));
    s.addEventListener("lostpointercapture", (ev) => fin(ev, true));
    return {
      el: s,
      tenu: () => prise >= 0,
      poser(xs) { tri.forEach((t, i) => { const x = xs[i]; t.dataset.x = String(x); t.setAttribute("points", `${x},2 ${x + 5.5},11 ${x - 5.5},11`); }); },
    };
  }

  const cour = () => etat[canal];
  function poser(n) { etat = { ...etat, [canal]: normaliserNiveaux(n) }; }

  const gEntree = glissiere(["noir", "gris", "blanc"], (i, x, fin) => {
    const n = { ...cour() };
    if (i === 0) n.inBlack = Math.min(Math.round(x), n.inWhite - 2);
    else if (i === 2) n.inWhite = Math.max(Math.round(x), n.inBlack + 2);
    else n.gamma = gammaDepuisCurseur(x, n.inBlack, n.inWhite);
    poser(n); dessiner(); signaler(fin);
  });
  const ligneE = document.createElement("div"); ligneE.className = "pl-ton-nums";
  const fNoir = champNombre(libelleParam("inBlack", T), { min: 0, max: 253 }, (v) => saisir("inBlack", v));
  const fGamma = champNombre(libelleParam("gamma", T), { min: 0.01, max: 9.99, pas: 0.01 }, (v) => saisir("gamma", v));
  const fBlanc = champNombre(libelleParam("inWhite", T), { min: 2, max: 255 }, (v) => saisir("inWhite", v));
  ligneE.append(fNoir.el, fGamma.el, fBlanc.el);

  const titreS = document.createElement("div"); titreS.className = "pl-ton-sous"; titreS.textContent = T("photolab.niveaux.sortie");
  const gSortie = glissiere(["noir", "blanc"], (i, x, fin) => {
    const n = { ...cour() };
    n[i === 0 ? "outBlack" : "outWhite"] = Math.round(x);
    poser(n); dessiner(); signaler(fin);
  });
  const ligneS = document.createElement("div"); ligneS.className = "pl-ton-nums";
  const fOutNoir = champNombre(libelleParam("outBlack", T), { min: 0, max: 255 }, (v) => saisir("outBlack", v));
  const fOutBlanc = champNombre(libelleParam("outWhite", T), { min: 0, max: 255 }, (v) => saisir("outWhite", v));
  ligneS.append(fOutNoir.el, fOutBlanc.el);

  gEntree.el.setAttribute("aria-label", T("photolab.niveaux.entree"));
  gSortie.el.setAttribute("aria-label", T("photolab.niveaux.sortie"));
  racine.append(choix.el, titreE, svgH, gEntree.el, ligneE, titreS, gSortie.el, ligneS);
  conteneur.appendChild(racine);

  function saisir(cle, v) {
    // Une saisie de noir au-delà du blanc pousse le blanc (normaliserNiveaux), pas l'inverse : c'est le champ touché qui gagne.
    const n = { ...cour(), [cle]: Number(String(v).replace(",", ".")) };
    if (cle === "inBlack" && Number.isFinite(n.inBlack)) n.inBlack = borne(Math.round(n.inBlack), 0, 253);
    if (cle === "inWhite" && Number.isFinite(n.inWhite) && n.inWhite < n.inBlack + 2) n.inBlack = Math.max(0, Math.round(n.inWhite) - 2);
    poser(n); dessiner(); signaler(true);
  }

  function dessiner() {
    choix.sel.value = canal;
    const c = CANAUX.find((x) => x.id === canal);
    histoPath.setAttribute("d", histo && histo[c.histo] ? cheminHistogramme(histo[c.histo], TAILLE, HH) : "");
    histoPath.setAttribute("class", "pl-ton-histo canal-" + canal);
    const n = cour();
    gEntree.poser([n.inBlack, curseurDepuisGamma(n.gamma, n.inBlack, n.inWhite), n.inWhite]);
    gSortie.poser([n.outBlack, n.outWhite]);
    fNoir.ecrire(String(n.inBlack)); fGamma.ecrire(n.gamma.toFixed(2)); fBlanc.ecrire(String(n.inWhite));
    fOutNoir.ecrire(String(n.outBlack)); fOutBlanc.ecrire(String(n.outWhite));
  }
  const copie = () => Object.fromEntries(CANAUX.map((c) => [c.id, { ...etat[c.id] }]));
  const complet = !!(opts.complet || opts.cible);
  function signaler(fin) {
    if (!opts.surChangement || (opts.cible && !fin)) return;
    opts.surChangement(paramsNiveaux(etat, { complet }), { fin, luts: opts.cible ? null : lutsNiveaux(etat), etat: copie() });
  }

  dessiner();
  return {
    el: racine,
    etat: copie,
    params: () => paramsNiveaux(etat, { complet }),
    luts: () => lutsNiveaux(etat),
    lireSaisies() { [fNoir, fGamma, fBlanc, fOutNoir, fOutBlanc].forEach((f) => f.lire()); },
    poserEtat(e) { etat = etatDepuisParams("niveaux", paramsNiveaux(e || {}, { complet: true })); dessiner(); },
    enGeste: () => gEntree.tenu() || gSortie.tenu() || saisieActive(racine),
    poserHistogramme(h) { histo = h || null; dessiner(); },
    detruire() { racine.remove(); },
  };
}

// L'éditeur d'une sorte ("courbes" | "niveaux") — point d'entrée pour le panneau Propriétés (B5).
export function construireEditeurTon(sorte, conteneur, opts) {
  return sorte === "niveaux" ? construireEditeurNiveaux(conteneur, opts) : construireEditeurCourbes(conteneur, opts);
}

/* ───────────── côté DOM : le dialogue ───────────── */

export function initCourbes(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  // Dernier rendu RÉEL (jamais un aperçu) : la référence de l'aperçu JS. surRendu n'est appelé qu'après un rendu réel.
  let dernierReel = null;
  PL.surRendu.push((rendu) => { if (rendu && !rendu.apercu) dernierReel = rendu; });

  PL.ouvrirCourbes = (entree, cible) => ouvrir("courbes", entree, cible);
  PL.ouvrirNiveaux = (entree, cible) => ouvrir("niveaux", entree, cible);

  // Pixels du rendu de référence, copiés une fois par image (canevas hors écran).
  let cachePixels = null;            // {image, donnees}
  function pixelsDe(rendu) {
    if (!rendu || !rendu.image) return null;
    if (cachePixels && cachePixels.image === rendu.image) return cachePixels.donnees;
    const im = rendu.image;
    const w = im.naturalWidth || im.width, h = im.naturalHeight || im.height;
    if (!w || !h) return null;
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(im, 0, 0);
    let donnees;
    try { donnees = ctx.getImageData(0, 0, w, h); } catch (e) { return null; }   // image d'une autre origine : pas d'aperçu JS
    cachePixels = { image: im, donnees };
    return donnees;
  }

  function ouvrir(sorte, entree, cible) {
    if (!PL.etat.doc) return;
    const id = (entree && entree.id) || COMMANDES[sorte];
    const etatDlg = { identite: identiteDocument(PL.etat.doc, PL.etat.generation) };
    PL.prendreReglage(etatDlg);
    // La référence : le rendu affiché s'il est réel, sinon le dernier rendu réel reçu.
    let reference = PL.vue.rendu && !PL.vue.rendu.apercu ? PL.vue.rendu : dernierReel;
    let apercuPose = false, fini = false, minuterie = null, image = null, imageDonnees = null;
    const demander = derniereGagne((corps) => PL.api("POST", "/apercu", corps, 0, true));
    // Avec une cible (calque de réglage, B5) : aucun aperçu. Le rendu contient déjà le calque (une LUT JS doublerait
    // l'effet) et l'aperçu moteur sur copie ne vise pas le calque (ids renumérotés) ; OK modifie le calque.
    const avecApercu = !cible;

    const titre = titreDialogue((entree && entree.libelle) || T(sorte === "courbes" ? "photolab.courbes.titre" : "photolab.niveaux.titre"));
    const coq = coquilleReglage(PL, {
      titre, classe: "pl-reglage-ton", avecApercu: true,
      valider: () => { editeur.lireSaisies(); fermer("ok"); },
      annuler: () => fermer("annuler"),
      reinitialiser: () => { editeur.poserEtat(initial); coq.montrerErreur(""); apresGeste(editeur.luts(), true); },
      surCaseApercu: (coche) => {
        if (coche) { apresGeste(editeur.luts(), true); return; }
        clearTimeout(minuterie); demander.annuler(); coq.occupe(false); coq.montrerErreur("");
        if (apercuPose) { apercuPose = false; PL.cycle(); }
      },
    });
    const initial = cible && cible.params ? etatDepuisParams(sorte, cible.params) : etatNeutre(sorte);
    const editeur = construireEditeurTon(sorte, coq.corps, {
      T, etat: initial, cible: !!cible,
      surChangement: (params, { fin, luts }) => apresGeste(luts, fin),
    });
    coq.corps.appendChild(coq.erreur);
    const apercuActif = () => coq.caseApercu && coq.caseApercu.checked && !fini && !!PL.etat.doc;

    // Aperçu JS : LUT sur une copie des pixels du rendu réel, posée par poserApercu (une image par trame au plus).
    let trame = 0, lutsAttente = null;
    function apercuJs(luts) {
      lutsAttente = luts;
      if (trame) return;
      trame = requestAnimationFrame(() => {
        trame = 0;
        if (!apercuActif() || !lutsAttente) return;
        const src = pixelsDe(reference);
        if (!src) return;
        // Tampon, ImageData et canevas réutilisés d'une trame à l'autre ; redimensionnés seulement si la taille change.
        if (!imageDonnees || imageDonnees.width !== src.width || imageDonnees.height !== src.height) {
          imageDonnees = new ImageData(src.width, src.height);
        }
        appliquerLuts(src, lutsAttente, imageDonnees.data);
        if (!image) image = document.createElement("canvas");
        if (image.width !== src.width || image.height !== src.height) { image.width = src.width; image.height = src.height; }
        image.getContext("2d").putImageData(imageDonnees, 0, 0);
        PL.vue.poserApercu(image, reference.maxSide);
        apercuPose = true;
      });
    }

    function apresGeste(luts, fin) {
      if (!avecApercu || !apercuActif() || !luts) return;
      // Réglage neutre : rien à calculer (ni copie du document côté moteur) ; un aperçu resté à l'écran cède la place
      // au rendu réel.
      if (estLutIdentite(luts.r) && estLutIdentite(luts.g) && estLutIdentite(luts.b)) {
        clearTimeout(minuterie); demander.annuler(); lutsAttente = null; coq.occupe(false);
        if (apercuPose) { apercuPose = false; PL.cycle(); }
        return;
      }
      if (!fin) {
        // Pendant le glisser : aucun aperçu moteur (demandé ou en vol) ne doit recouvrir l'aperçu JS plus récent.
        clearTimeout(minuterie); demander.annuler(); coq.occupe(false);
        apercuJs(luts);
        return;
      }
      apercuJs(luts);
      clearTimeout(minuterie);
      minuterie = setTimeout(apercuMoteur, DELAI_APERCU);
    }

    // Au relâchement : le moteur fait foi (spline et pied d'ombre exacts, sélection et calque actif respectés).
    async function apercuMoteur() {
      if (!apercuActif()) return;
      const voulu = PL.vue.maxSideVoulu();
      coq.occupe(true);
      const r = await demander({ etapes: [{ command: id, params: editeur.params() }], maxSide: maxSideRequete(voulu, PL.etat.doc) });
      if (r.perime) return;
      coq.occupe(demander.enVol());
      if (fini || !apercuActif()) return;
      if (r.erreur) { coq.montrerErreur(T("photolab.reglage.erreur_apercu") + " " + (r.erreur.message || "")); return; }
      let im;
      try { im = await chargerImage(r.valeur.url); } catch (e) { coq.montrerErreur(T("photolab.reglage.erreur_apercu")); return; }
      if (fini || !apercuActif()) return;
      coq.montrerErreur("");
      PL.vue.poserApercu(im, voulu);
      apercuPose = true;
    }

    etatDlg.surRenduReel = () => {
      // Un rendu réel (zoom, autre commande) vient de recouvrir l'aperçu : il devient la référence, et l'aperçu est
      // redemandé à la nouvelle taille.
      if (PL.vue.rendu && !PL.vue.rendu.apercu) reference = PL.vue.rendu;
      if (!apercuActif()) return;
      apercuPose = false;
      apresGeste(editeur.luts(), true);
    };

    function fermer(role) {
      if (fini) return;
      fini = true;
      clearTimeout(minuterie);
      if (trame) cancelAnimationFrame(trame);
      demander.annuler();
      coq.retirer();
      PL.libererReglage(etatDlg);
      cachePixels = null;                 // une copie de 16 Mo en 2048 px : on ne la garde pas dialogue fermé
      image = null; imageDonnees = null;
      if (role === "ok") {
        // Comme le dialogue générique : par la file FIFO tout de suite (l'aperçu en vol est périmé) ; en échec, un
        // aperçu resté à l'écran ferait croire le réglage appliqué -> rendu réel relu.
        const effacer = apercuPose;
        const fait = cible
          ? PL.executer("layer.setAdjustment", { layer: cible.id, ...editeur.params() })
          : PL.executer(id, editeur.params());
        fait.then((r) => { if (!(r && r.ok) && effacer) PL.cycle(); });
      } else if (apercuPose) {
        PL.cycle();
      }
    }
    etatDlg.fermer = fermer;

    coq.placer();
    // Histogramme d'avant le réglage, une fois à l'ouverture (sans = le calque de réglage édité, B5).
    const q = "/histogramme?maxSide=512" + (cible && cible.id != null ? "&sans=" + encodeURIComponent(cible.id) : "");
    PL.get(q, true).then((h) => { if (!fini && h) editeur.poserHistogramme(h); }).catch(() => { /* histogramme facultatif */ });
    return etatDlg;
  }
}
