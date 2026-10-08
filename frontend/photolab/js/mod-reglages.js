// mod-reglages.js — calques de réglage (t138 B5) : onglet « Ajustements » de #grpProprietes (16 boutons qui créent un
// calque de réglage), éditeur du calque de réglage actif dans l'onglet « Propriétés », icône du kind dans la liste des
// calques et petit menu du bouton du pied. Chaque relâchement envoie `layer.setAdjustment {layer, ...difference}` : le
// moteur FUSIONNE (les clés absentes gardent leur valeur) et son rendu EST l'aperçu (le calque est dans le document).
// L'état du calque se relit dans doc.inspect, où il est rangé sous sa structure INTERNE (relevé A4 sur le vrai moteur,
// fixture qa/fixtures/reglages-inspect.json) : depuisInspect la ramène aux paramètres de commande.
// Fonctions PURES exportées (qa/reglages.test.mjs ; qa/outils/reglages.mjs les rejoue devant la liste blanche du pont).

import { champsVisibles, coercer } from "./mod-champs.js";
import { trouverCalque } from "./mod-calques.js";
import { normaliserPoints, estCourbeIdentite, normaliserNiveaux, estNiveauxNeutres, etatDepuisParams, construireEditeurTon,
  paramsCourbes, paramsNiveaux } from "./mod-courbes.js";
import { fabriquerControle } from "./mod-dialogue-reglage.js";
import { indexRegistre } from "./mod-menus.js";
import { brut } from "./mod-cycle.js";

/* ───────────── fonctions PURES ───────────── */

// Les 16 kinds dans l'ordre du menu de photocraft (Calque › Nouveau calque de réglage). `variante` = nom rendu par
// doc.inspect (clé de `adjustment`, ou la chaîne "Invert"). Icônes : Lucide déjà livrées dans icones/ (aucune copie).
const k = (kind, variante, icone) => Object.freeze({ kind, variante, icone, cle: "photolab.kind." + kind.toLowerCase() });
export const KINDS = Object.freeze([
  k("brightnessContrast", "BrightnessContrast", "sun"),
  k("levels", "Levels", "sliders-horizontal"),
  k("curves", "Curves", "pen-tool"),
  k("exposure", "Exposure", "flame"),
  k("vibrance", "Vibrance", "droplet"),
  k("hueSaturation", "HueSaturation", "palette"),
  k("colorBalance", "ColorBalance", "blend"),
  k("blackWhite", "BlackWhite", "circle"),
  k("photoFilter", "PhotoFilter", "scan"),
  k("channelMixer", "ChannelMixer", "sliders"),
  k("colorLookup", "ColorLookup", "hash"),
  k("invert", "Invert", "diamond"),
  k("posterize", "Posterize", "grid-3x3"),
  k("threshold", "Threshold", "triangle"),
  k("gradientMap", "GradientMap", "paint-bucket"),
  k("selectiveColor", "SelectiveColor", "wand"),
]);
const PAR_KIND = new Map(KINDS.map((x) => [x.kind, x]));
const PAR_VARIANTE = new Map(KINDS.map((x) => [x.variante, x.kind]));
export function infoKind(kind) { return PAR_KIND.get(kind) || null; }
// t140 : l'id DOM du bouton d'un réglage (onglet Ajustements), pour les fiches didactiques.
export function idReglage(kind) { return "pl-aj-" + kind; }

// Le kind d'un calque de doc.inspect : la variante de `adjustment` (objet à une clé, ou la chaîne "Invert") ; null pour
// tout autre calque, ou une variante qu'un moteur plus récent aurait ajoutée (l'écran ne saurait pas l'éditer).
export function kindDe(calque) {
  const a = calque && calque.adjustment;
  if (typeof a === "string") return PAR_VARIANTE.get(a) || null;
  if (a && typeof a === "object" && !Array.isArray(a)) {
    const cles = Object.keys(a);
    return cles.length === 1 ? PAR_VARIANTE.get(cles[0]) || null : null;
  }
  return null;
}

// Gammes et tons, dans l'ordre du moteur (ranges[0..5], adjustments[0..8]).
export const GAMMES_TEINTE = Object.freeze(["reds", "yellows", "greens", "cyans", "blues", "magentas"]);
// Bornes par défaut des gammes de Teinte/Saturation (en degrés, relevées sur le moteur) : une gamme absente de l'état
// se recrée avec elles, pour ne jamais envoyer un `range` inventé.
export const BORNES_GAMMES = Object.freeze({ reds: [-45, -15, 15, 45], yellows: [15, 45, 75, 105], greens: [75, 105, 135, 165],
  cyans: [135, 165, 195, 225], blues: [195, 225, 255, 285], magentas: [255, 285, 315, 345] });
export const TONS = Object.freeze(["shadows", "midtones", "highlights"]);
export const GAMMES_SELECTIVE = Object.freeze(["reds", "yellows", "greens", "cyans", "blues", "magentas", "whites", "neutrals", "blacks"]);
// Lignes du mélangeur de couches à leur neutre (100 % de la couche elle-même ; gris : 40/40/20, le défaut du moteur).
export const LIGNES_MIXEUR = Object.freeze({ red: [100, 0, 0, 0], green: [0, 100, 0, 0], blue: [0, 0, 100, 0], gray: [40, 40, 20, 0] });
export const DEGRADE_DEFAUT = Object.freeze([[0, "#000000"], [1, "#ffffff"]]);

const borne = (v, a, b) => Math.min(b, Math.max(a, v));
const nombre = (v, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v : d);
// Les flottants de l'état sont des f32 (0.3 -> 0.30000001192…) : arrondis à 4 décimales, jamais -0.
const arrondi = (v, dec = 4) => { const r = Number(nombre(v).toFixed(dec)); return r === 0 ? 0 : r; };
const de01 = (v) => borne(Math.round(arrondi(v, 6) * 255), 0, 255);
const hexDe = (rgb) => (Array.isArray(rgb) && rgb.length >= 3
  ? "#" + rgb.slice(0, 3).map((c) => de01(c).toString(16).padStart(2, "0")).join("") : null);
const objet = (x) => (x && typeof x === "object" && !Array.isArray(x) ? x : {});
const tableau = (v, n, f) => Array.from({ length: n }, (_, i) => f(Array.isArray(v) ? v[i] : undefined));

function canalNiveaux(o) {
  const s = objet(o);
  return normaliserNiveaux({ inBlack: de01(s.in_black), gamma: arrondi(nombre(s.gamma, 1)), inWhite: de01(nombre(s.in_white, 1)),
    outBlack: de01(s.out_black), outWhite: de01(nombre(s.out_white, 1)) });
}
function points(liste) {
  const l = Array.isArray(liste) ? liste : [];
  return normaliserPoints(l.map((p) => [Math.round(arrondi(objet(p).input, 6) * 255), Math.round(arrondi(objet(p).output, 6) * 255)]));
}

// adjustment de doc.inspect -> paramètres de commande (règles relevées sur le VRAI moteur, scratchpad/t138/
// conversion-inspect.md). Un canal de Niveaux / Courbes à l'identité est ABSENT (indiscernable d'un canal non envoyé) ;
// les autres états sont COMPLETS (6 gammes, 9 gammes, 3 tons…) : l'éditeur part de valeurs connues et la difference
// n'envoie que ce qui a changé. Un état illisible donne {} (le moteur garde le sien), jamais une exception.
export function depuisInspect(kind, adjustment, lutList) {
  const info = infoKind(kind);
  if (!info) return {};
  if (kind === "invert") return {};
  const o = adjustment && typeof adjustment === "object" ? adjustment[info.variante] : null;
  if (!o || typeof o !== "object") return {};
  switch (kind) {
    case "brightnessContrast":
      return { brightness: arrondi(o.brightness), contrast: arrondi(o.contrast), legacy: o.legacy === true };
    case "levels": {
      const p = { ...canalNiveaux(o.master) };
      ["red", "green", "blue"].forEach((c, i) => {
        const n = canalNiveaux(Array.isArray(o.per_channel) ? o.per_channel[i] : null);
        if (!estNiveauxNeutres(n)) p[c] = n;
      });
      return p;
    }
    case "curves": {
      const p = { points: points(o.master) };
      ["red", "green", "blue"].forEach((c, i) => {
        const l = Array.isArray(o.per_channel) ? o.per_channel[i] : null;
        if (Array.isArray(l) && l.length) { const pts = points(l); if (!estCourbeIdentite(pts)) p[c] = pts; }
      });
      return p;
    }
    case "exposure": return { exposure: arrondi(o.exposure), offset: arrondi(o.offset), gamma: arrondi(nombre(o.gamma, 1)) };
    case "vibrance": return { vibrance: arrondi(o.vibrance), saturation: arrondi(o.saturation) };
    case "hueSaturation": {
      const p = { hue: arrondi(o.hue), saturation: arrondi(o.saturation), lightness: arrondi(o.lightness), colorize: o.colorize === true };
      GAMMES_TEINTE.forEach((g, i) => {
        const r = objet(Array.isArray(o.ranges) ? o.ranges[i] : null);
        const range = Array.isArray(r.bounds) && r.bounds.length === 4 ? r.bounds.map((x) => arrondi(x)) : BORNES_GAMMES[g].slice();
        p[g] = { hue: arrondi(r.hue), saturation: arrondi(r.saturation), lightness: arrondi(r.lightness), range };
      });
      return p;
    }
    case "colorBalance": {
      const p = {};
      for (const t of TONS) p[t] = tableau(o[t], 3, (x) => arrondi(x));
      p.preserveLuminosity = o.preserve_luminosity !== false;
      return p;
    }
    case "blackWhite": {
      const p = {};
      GAMMES_TEINTE.forEach((g, i) => { p[g] = arrondi(Array.isArray(o.weights) ? o.weights[i] : 0); });
      const teinte = hexDe(o.tint);
      p.tint = teinte !== null;                         // `tint: true` se DÉDUIT d'une teinte présente
      if (teinte) p.tintColor = teinte;                 // sans teinte, sa couleur est perdue par le moteur
      return p;
    }
    case "photoFilter": {
      // Le nom du préréglage (`filter`) est perdu par le moteur : on garde la couleur qu'il a posée.
      const p = { density: borne(Math.round(arrondi(o.density, 6) * 100), 0, 100), preserveLuminosity: o.preserve_luminosity !== false };
      const c = hexDe(o.color);
      if (c) p.color = c;
      return p;
    }
    case "channelMixer": {
      const m = Array.isArray(o.matrix) ? o.matrix : [];
      const ligne = (i) => tableau(m[i], 4, (x) => arrondi(nombre(x) * 100, 2));
      // Monochrome : la ligne 0 EST le gris (les deux autres restent l'identité) ; jamais `red` à sa place.
      if (o.monochrome === true) return { gray: ligne(0), monochrome: true };
      return { red: ligne(0), green: ligne(1), blue: ligne(2), monochrome: false };
    }
    case "posterize": return { levels: borne(Math.round(nombre(o.levels, 4)), 2, 255) };
    case "threshold": return { level: borne(Math.round(arrondi(nombre(o.level, 0.5), 6) * 255), 1, 255) };
    case "gradientMap": {
      const p = { reverse: o.reverse === true, dither: o.dither === true };
      const stops = (Array.isArray(o.stops) ? o.stops : [])
        .map((s) => (Array.isArray(s) && s.length >= 2 && hexDe(s[1]) ? [borne(arrondi(s[0]), 0, 1), hexDe(s[1])] : null))
        .filter(Boolean);
      if (stops.length >= 2) p.stops = stops.slice(0, 64);
      return p;
    }
    case "selectiveColor": {
      const p = { method: o.relative === false ? "absolute" : "relative" };
      const a = Array.isArray(o.adjustments) ? o.adjustments : [];
      GAMMES_SELECTIVE.forEach((g, i) => { p[g] = tableau(a[i], 4, (x) => arrondi(x)); });
      return p;
    }
    case "colorLookup": {
      const p = { interpolation: o.tetrahedral === true ? "tetrahedral" : "trilinear", dither: o.dither === true };
      // L'id du LUT est perdu : seul son libellé (« Warm Filter ») reste ; on le retrouve dans image.adjustments.
      // colorLookup.list. Liste pas encore chargée ou libellé inconnu : `lut` absent, jamais une valeur inventée.
      if (!o.name) p.lut = "none";
      else {
        const l = Array.isArray(lutList) ? lutList.find((x) => x && x.label === o.name) : null;
        if (l) p.lut = l.id;
      }
      return p;
    }
    default: return {};
  }
}

// Égalité profonde (ordre des clés indifférent, ordre des tableaux significatif).
export function egalProfond(a, b) {
  if (a === b) return true;
  if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((x, i) => egalProfond(x, b[i]));
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every((x) => Object.prototype.hasOwnProperty.call(b, x) && egalProfond(a[x], b[x]));
}
const cloner = (v) => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));

// Ce qu'envoie layer.setAdjustment : les clés de `apres` dont la valeur a changé (une gamme ou un ton changé part
// ENTIER : le moteur remplace la valeur d'une clé, il ne fusionne pas dans un tableau). Une clé disparue est ignorée :
// le moteur n'a pas de « retirer », il garde la sienne.
export function difference(avant, apres) {
  const a = objet(avant), b = objet(apres);
  const d = {};
  for (const x of Object.keys(b)) if (!egalProfond(a[x], b[x])) d[x] = cloner(b[x]);
  return d;
}

// Lecture et écriture IMMUABLES par chemin (["midtones", 0], ["reds", "hue"], ["stops", 2, 1]). Un conteneur de
// premier niveau absent est recréé depuis `defaut` (ton à zéro, ligne neutre du mélangeur, dégradé noir -> blanc).
export function lireChemin(etat, chemin) {
  let v = etat;
  for (const c of chemin) { if (v === null || v === undefined || typeof v !== "object") return undefined; v = v[c]; }
  return v;
}
function poserDans(cont, chemin, v) {
  const [c, ...reste] = chemin;
  const copie = Array.isArray(cont) ? cont.slice() : cont && typeof cont === "object" ? { ...cont } : typeof c === "number" ? [] : {};
  copie[c] = reste.length ? poserDans(copie[c], reste, v) : v;
  return copie;
}
export function avecValeur(etat, chemin, v, defaut) {
  const base = objet(etat);
  const [c, ...reste] = chemin;
  if (!reste.length) return { ...base, [c]: v };
  const sous = base[c] !== undefined && base[c] !== null ? base[c] : cloner(defaut);
  return { ...base, [c]: poserDans(sous, reste, v) };
}

// Quel éditeur pour quel kind : l'éditeur de B4 (Courbes, Niveaux), rien (Inverser), un éditeur sur mesure (gammes,
// tons, couches, dégradé — des champs `json` que le formulaire générique ne sait pas montrer), le formulaire généré.
const SUR_MESURE = new Set(["hueSaturation", "colorBalance", "channelMixer", "selectiveColor", "gradientMap"]);
export function sorteEditeur(kind) {
  if (!infoKind(kind)) return null;
  if (kind === "curves" || kind === "levels") return "ton";
  if (kind === "invert") return "aucun";
  return SUR_MESURE.has(kind) ? "surmesure" : "formulaire";
}

// Champs fabriqués par l'écran (aucune clé de registre ne les décrit) : libellé par `cleLibelle`.
const curseur = (cle, min, max, cleLibelle) => ({ cle, type: "number", min, max, entier: true, defaut: 0, optionnel: true, ...(cleLibelle ? { cleLibelle } : {}) });
const LIB_CANAL = { red: "photolab.canal.rouge", green: "photolab.canal.vert", blue: "photolab.canal.bleu", gray: "photolab.canal.gris" };
const LIB_TONS = { shadows: "photolab.reglages.ombres", midtones: "photolab.reglages.tons_moyens", highlights: "photolab.reglages.tons_clairs" };
const AXES_BALANCE = [["cyan_rouge", "photolab.reglages.cyan_rouge"], ["magenta_vert", "photolab.reglages.magenta_vert"], ["jaune_bleu", "photolab.reglages.jaune_bleu"]];
const COLONNES_MIXEUR = [["rouge", "photolab.canal.rouge"], ["vert", "photolab.canal.vert"], ["bleu", "photolab.canal.bleu"], ["constante", "photolab.reglages.constante"]];

// La VUE d'un éditeur : un sélecteur facultatif (gamme, ton, couche de sortie) et la liste des contrôles, chacun
// {c : champ (registre ou fabriqué), chemin : où il écrit dans l'état, valeur, conteneur : défaut du conteneur}.
// `choix` = valeur voulue du sélecteur (repli sur la première permise). `champs` = champs du registre de
// layer.newAdjustmentLayer.<kind>.
export function vueReglage(kind, etat, choix, champs) {
  const e = objet(etat);
  const reg = (cle, repli) => (Array.isArray(champs) ? champs.find((c) => c && c.cle === cle) : null) || repli;
  const el = (c, chemin, conteneur, defaut) => {
    const v = lireChemin(e, chemin);
    return { c, chemin, conteneur, valeur: v === undefined ? defaut : v };
  };
  const sel = (cle, options, voulu) => ({ cle, options, valeur: options.some((o) => o.valeur === voulu) ? voulu : options[0].valeur });
  const sorte = sorteEditeur(kind);
  if (sorte === "ton" || sorte === "aucun" || !sorte) return { selecteur: null, champs: [] };
  if (sorte === "formulaire") {
    return { selecteur: null, champs: champsVisibles(champs).map((c) => el(c, [c.cle], undefined, undefined)) };
  }
  const colorize = reg("colorize", { cle: "colorize", type: "bool", defaut: false });
  switch (kind) {
    case "hueSaturation": {
      // Teinte, saturation, clarté globales : champs du registre (bornes de la colorisation par bornesEffectives).
      const maitre = () => [...["hue", "saturation", "lightness"].map((cle) => el(reg(cle, curseur(cle, cle === "hue" ? -180 : -100, cle === "hue" ? 180 : 100)), [cle], undefined, 0)),
        el(colorize, ["colorize"])];
      // Colorisation : une seule teinte pour toute l'image, les gammes n'ont plus de sens (comme Photoshop).
      if (e.colorize === true) {
        return { selecteur: null, champs: maitre() };
      }
      const s = sel("photolab.reglages.gamme", [{ valeur: "master", cle: "photolab.reglages.global" },
        ...GAMMES_TEINTE.map((g) => ({ valeur: g, cle: "photolab.valeur." + g }))], choix);
      if (s.valeur === "master") {
        return { selecteur: s, champs: maitre() };
      }
      const g = s.valeur;
      const vide = { hue: 0, saturation: 0, lightness: 0, range: BORNES_GAMMES[g].slice() };
      const f = (cle, min, max) => ({ ...curseur(cle, min, max), cleLibelle: "photolab.param." + cle });
      return { selecteur: s, champs: [el(f("hue", -180, 180), [g, "hue"], vide, 0), el(f("saturation", -100, 100), [g, "saturation"], vide, 0),
        el(f("lightness", -100, 100), [g, "lightness"], vide, 0), el(colorize, ["colorize"])] };
    }
    case "colorBalance": {
      const s = sel("photolab.reglages.tons", TONS.map((t) => ({ valeur: t, cle: LIB_TONS[t] })), choix || "midtones");
      return { selecteur: s, champs: [...AXES_BALANCE.map(([cle, lib], i) => el(curseur(cle, -100, 100, lib), [s.valeur, i], [0, 0, 0], 0)),
        el(reg("preserveLuminosity", { cle: "preserveLuminosity", type: "bool", defaut: true }), ["preserveLuminosity"])] };
    }
    case "channelMixer": {
      const sorties = e.monochrome === true ? ["gray"] : ["red", "green", "blue"];
      const s = sel("photolab.reglages.sortie", sorties.map((x) => ({ valeur: x, cle: LIB_CANAL[x] })), choix);
      const neutre = LIGNES_MIXEUR[s.valeur];
      return { selecteur: s, champs: [...COLONNES_MIXEUR.map(([cle, lib], i) => el(curseur(cle, -200, 200, lib), [s.valeur, i], neutre, neutre[i])),
        el(reg("monochrome", { cle: "monochrome", type: "bool", defaut: false }), ["monochrome"])] };
    }
    case "selectiveColor": {
      const s = sel("photolab.param.colors", GAMMES_SELECTIVE.map((g) => ({ valeur: g, cle: "photolab.valeur." + g })), choix);
      return { selecteur: s, champs: [...["cyan", "magenta", "yellow", "black"].map((cle, i) => el({ ...reg(cle, curseur(cle, -100, 100)), optionnel: true }, [s.valeur, i], [0, 0, 0, 0], 0)),
        el(reg("method", { cle: "method", type: "enum", valeurs: ["relative", "absolute"], defaut: "relative" }), ["method"])] };
    }
    case "gradientMap": {
      // Les deux couleurs extrêmes s'éditent ; les arrêts intermédiaires sont gardés tels quels (le tableau part entier).
      const stops = Array.isArray(e.stops) && e.stops.length >= 2 ? e.stops : DEGRADE_DEFAUT;
      const couleur = (cle, lib) => ({ cle, type: "color", formes: ["hex"], optionnel: true, cleLibelle: lib });
      return { selecteur: null, champs: [
        el(couleur("debut", "photolab.reglages.couleur_debut"), ["stops", 0, 1], DEGRADE_DEFAUT, stops[0][1]),
        el(couleur("fin", "photolab.reglages.couleur_fin"), ["stops", stops.length - 1, 1], DEGRADE_DEFAUT, stops[stops.length - 1][1]),
        el(reg("reverse", { cle: "reverse", type: "bool", defaut: false }), ["reverse"]),
        el(reg("dither", { cle: "dither", type: "bool", defaut: false }), ["dither"])] };
    }
    default: return { selecteur: null, champs: [] };
  }
}

// Valeurs COURANTES de la vue (ce que lit la fabrique de contrôles : valeur affichée, bornes de la colorisation).
export function valeursVue(vue, etat) {
  const e = objet(etat);
  const v = { colorize: e.colorize === true };
  for (const x of (vue && vue.champs) || []) {
    const lu = lireChemin(e, x.chemin);
    v[x.c.cle] = lu === undefined ? x.valeur : lu;
  }
  return v;
}

// Une saisie sur un contrôle de la vue -> nouvel état (coercée comme partout : bornes, entier, #rrggbb).
export function appliquer(etat, element, brutSaisi, valeurs) {
  return avecValeur(etat, element.chemin, coercer(element.c, brutSaisi, valeurs || {}), element.conteneur);
}

// Structure d'une vue (sélecteur, options, contrôles, chemins), SANS les valeurs : tant qu'elle ne change pas, un
// nouvel état se contente de réécrire les contrôles (le focus et le curseur tenu restent en place).
export function signatureVue(vue) {
  const s = vue && vue.selecteur;
  return JSON.stringify({ s: s ? [s.cle, s.options.map((o) => o.valeur), s.valeur] : null,
    c: ((vue && vue.champs) || []).map((x) => [x.c.cle, x.c.type, x.chemin]) });
}

// Réponse de image.adjustments.colorLookup.list -> [{id, label}] (tableau direct, ou enveloppé) ; illisible -> null.
export function lutsDepuisReponse(r) {
  const l = Array.isArray(r) ? r : r && typeof r === "object" ? r.looks || r.list || r.luts : null;
  if (!Array.isArray(l) || !l.length) return null;
  if (!l.every((x) => x && typeof x.id === "string" && x.id && typeof x.label === "string")) return null;
  return l.map((x) => ({ id: x.id, label: x.label }));
}

/* ───────────── côté DOM ───────────── */

export function initReglages(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const grp = PL.$("#grpProprietes");
  const corpsProps = PL.$("#corpsProprietes");
  const corpsAj = PL.$("#corpsAjustements");
  let lutList = null, lutsDemandees = false;
  let courant = null;            // éditeur affiché : {cleIdentite, racine, maj(etat), detruire()}
  let menuOuvert = null;

  const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };

  /* onglets Propriétés | Ajustements, DANS #grpProprietes (aucune section ni bouton de rail en plus) */
  function montrer(nom) {
    PL.$$("#grpProprietes .onglet").forEach((o) => {
      const oui = o.dataset.ongletPr === nom;
      o.classList.toggle("actif", oui); o.setAttribute("aria-selected", oui ? "true" : "false");
    });
    PL.$$("#grpProprietes .groupe-corps").forEach((c) => { c.hidden = c.dataset.vuePr !== nom; });
  }
  // Le groupe a pu être replié par le bouton « Ajustements » du rail : on le rouvre avant d'y montrer quelque chose.
  function deplier() {
    if (grp && grp.hidden) { grp.hidden = false; if (PL.majRail) PL.majRail(); }
  }
  // Libellés des onglets par leurs clés (comme les boutons du rail) : justes même si la surcouche ne repasse pas.
  const LIB_ONGLETS = { proprietes: "photolab.reglages.onglet_proprietes", ajustements: "photolab.reglages.onglet_reglages" };
  PL.$$("#grpProprietes .onglet").forEach((o) => {
    if (LIB_ONGLETS[o.dataset.ongletPr]) o.textContent = T(LIB_ONGLETS[o.dataset.ongletPr]);
    o.addEventListener("click", () => montrer(o.dataset.ongletPr));
  });

  /* onglet Ajustements : 16 boutons (icône + infobulle) */
  const grille = el("div", "rg-grille");
  grille.setAttribute("role", "toolbar"); grille.setAttribute("aria-label", T("photolab.reglages.onglet_reglages"));
  const boutons = KINDS.map((x) => {
    const b = el("button", "rg-kind"); b.type = "button"; b.dataset.kind = x.kind; b.dataset.icone = x.icone;
    b.id = idReglage(x.kind);                                  // t140 : id stable (fiches didactiques)
    b.title = T(x.cle); b.setAttribute("aria-label", b.title); b.disabled = true;
    b.addEventListener("click", () => PL.creerReglage(x.kind));
    grille.appendChild(b);
    return b;
  });
  if (corpsAj) { corpsAj.textContent = ""; corpsAj.appendChild(grille); }
  PL.hydraterIcones(grille);

  // Créer = valeurs par défaut du moteur (au-dessus du calque actif, qui devient actif) ; puis l'onglet Propriétés
  // montre son éditeur au cycle suivant.
  PL.creerReglage = function creerReglage(kind) {
    if (!PL.etat.doc || !infoKind(kind)) return Promise.resolve({ ok: false });
    deplier(); montrer("proprietes");
    return PL.executer("layer.newAdjustmentLayer." + kind, {});
  };

  const champsDe = (kind) => {
    const r = PL.menus ? indexRegistre(PL.menus.registre).get("layer.newAdjustmentLayer." + kind) : null;
    return r && Array.isArray(r.champs) ? r.champs : [];
  };

  // La liste des LUT (id <-> libellé) : une fois, hors cycle (aucun rendu à relire).
  function chargerLuts() {
    if (lutsDemandees || !PL.etat.doc) return;
    lutsDemandees = true;
    PL.executer("image.adjustments.colorLookup.list", {}, { cycle: false }).then((r) => {
      const l = r && r.ok ? lutsDepuisReponse(r.r) : null;
      // Échec (déjà signalé) : on pourra redemander au prochain affichage d'un calque Color Lookup.
      if (!l) { lutsDemandees = false; return; }
      lutList = l;
      if (PL.etat.doc) proprietes(corpsProps, PL.etat.doc);
    });
  }

  const envoyer = (id, params) => {
    if (!Object.keys(params).length) return;
    PL.executer("layer.setAdjustment", { layer: id, ...params });
  };

  function entete(racine, calque, info) {
    const tete = el("div", "rg-tete");
    const ico = el("span", "rg-icone"); ico.dataset.icone = info.icone;
    const titre = el("span", "rg-titre", T(info.cle));
    // Le nom du calque (« Levels 1 », donné par le moteur ou l'utilisateur) est une donnée : jamais traduit.
    const nom = brut(el("span", "rg-nom", calque.name || ""));
    tete.append(ico, titre, nom);
    racine.appendChild(tete);
    PL.hydraterIcones(tete);
  }

  function construire(corps, calque, kind, etat) {
    const info = infoKind(kind);
    const id = calque.id;
    const racine = el("div", "rg-editeur");
    entete(racine, calque, info);
    const zone = el("div", "rg-zone");
    racine.appendChild(zone);
    corps.appendChild(racine);
    const sorte = sorteEditeur(kind);

    if (sorte === "ton") {
      // Éditeur de B4 en mode cible : aucun aperçu JS (le rendu contient déjà le calque) ; au relâchement, les QUATRE
      // canaux partent (un canal remis à plat doit l'être aussi dans le calque : le moteur fusionne).
      const s = kind === "curves" ? "courbes" : "niveaux";
      const complets = (e) => (s === "courbes" ? paramsCourbes : paramsNiveaux)(etatDepuisParams(s, e), { complet: true });
      let attente = null;            // état relu pendant un geste : posé à la fin du geste
      const ed = construireEditeurTon(s, zone, { T, etat: etatDepuisParams(s, etat), cible: true,
        surChangement: (params, { fin }) => {
          if (!fin) return;
          attente = null;            // notre envoi périme l'état relu en attente : le cycle qui suit apporte le bon
          envoyer(id, params);
        } });
      function maj(e) {
        // Retour du cycle égal à ce que l'éditeur montre (notre propre envoi) : rien à faire (point actif, canal gardés).
        if (egalProfond(complets(e), ed.params())) { attente = null; return; }
        if (ed.enGeste()) { attente = e; return; }
        attente = null;
        ed.poserEtat(etatDepuisParams(s, e));
      }
      const relacher = () => setTimeout(() => { if (attente && racine.isConnected && !ed.enGeste()) maj(attente); }, 0);
      racine.addEventListener("focusout", relacher);
      // Histogramme de l'image SANS ce calque (ce que le réglage reçoit), une fois.
      PL.get("/histogramme?maxSide=512&sans=" + encodeURIComponent(id), true)
        .then((h) => { if (h && racine.isConnected) ed.poserHistogramme(h); }).catch(() => { /* facultatif */ });
      return { racine, maj, relacher, detruire: () => { ed.detruire(); racine.remove(); } };
    }
    if (sorte === "aucun") {
      zone.appendChild(el("p", "pr-vide", T("photolab.reglages.aucun_parametre")));
      return { racine, maj: () => {}, relacher: () => {}, detruire: () => racine.remove() };
    }

    // Formulaire généré ou éditeur sur mesure : une VUE (vueReglage) rendue par la fabrique de contrôles de B2.
    // avant = dernier état connu du moteur (ou envoyé) ; apres = avant + la saisie en cours (pas encore envoyée).
    let avant = etat, apres = etat, choix = null, vue = null, sig = "", controles = [], tenu = null, rendreEnAttente = false;
    const ctx = { T, valeurs: () => valeursVue(vue, apres), poser };
    function poser(c, saisie, final, depuisLeCurseur = false) {
      const e = vue.champs.find((x) => x.c === c);
      if (!e) return;
      apres = appliquer(apres, e, saisie, valeursVue(vue, apres));
      const ctl = controles.find((x) => x.c === c);
      if (ctl) ctl.ecrire(depuisLeCurseur);
      if (!final) return;
      const d = difference(avant, apres);
      avant = apres;
      envoyer(id, d);
      if (c.cle === "colorize" || c.cle === "monochrome") rendre();     // gammes / couches de sortie en dépendent
    }
    function selecteur(s) {
      const ligne = el("div", "pl-rg-champ sorte-liste");
      const lib = el("label", "pl-rg-lib", T(s.cle));
      const choixEl = el("select", "pl-rg-choix");
      choixEl.id = "rg-sel-" + id + "-" + kind; lib.htmlFor = choixEl.id;
      for (const o of s.options) { const op = el("option", "", T(o.cle)); op.value = o.valeur; choixEl.appendChild(op); }
      choixEl.value = s.valeur;
      choixEl.addEventListener("change", () => { choix = choixEl.value; rendre(); });
      ligne.append(lib, choixEl);
      return ligne;
    }
    function rendre() {
      rendreEnAttente = false;
      vue = vueReglage(kind, apres, choix, champsDe(kind));
      sig = signatureVue(vue);
      if (vue.selecteur) choix = vue.selecteur.valeur;
      zone.textContent = ""; controles = []; tenu = null;
      if (vue.selecteur) zone.appendChild(selecteur(vue.selecteur));
      for (const x of vue.champs) {
        const ctl = fabriquerControle(x.c, ctx);
        if (ctl) { controles.push(ctl); zone.appendChild(ctl.el); }
      }
    }
    // Contrôle sous les doigts : le curseur tenu (pointerdown) ou le champ qui a le focus. Un état relu ne le réécrit pas.
    const sousLesDoigts = (x) => x === tenu || (typeof document !== "undefined" && !!document.activeElement && x.el.contains(document.activeElement));
    zone.addEventListener("pointerdown", (ev) => { tenu = controles.find((x) => x.el.contains(ev.target)) || null; }, true);
    function relacher() {
      tenu = null;
      setTimeout(() => {
        if (!racine.isConnected) return;
        if (rendreEnAttente && !controles.some(sousLesDoigts)) { rendre(); return; }
        controles.forEach((x) => { if (!sousLesDoigts(x)) x.ecrire(); });
      }, 0);
    }
    racine.addEventListener("focusout", relacher);
    rendre();
    return {
      racine, relacher,
      // Nouvel état relu (cycle, annuler). Égal à ce qu'on a envoyé : rien. Sinon la saisie pas encore envoyée est
      // reportée sur le nouvel état ; même structure -> les contrôles se réécrivent en place (sauf celui sous les
      // doigts) ; structure changée -> reconstruction, différée tant qu'un contrôle est tenu ou a le focus.
      maj(e) {
        if (egalProfond(e, avant)) return;
        const enCours = difference(avant, apres);
        avant = e; apres = { ...e, ...enCours };
        if (signatureVue(vueReglage(kind, apres, choix, champsDe(kind))) !== sig) {
          if (controles.some(sousLesDoigts)) rendreEnAttente = true; else rendre();
          return;
        }
        controles.forEach((x) => { if (!sousLesDoigts(x)) x.ecrire(); });
      },
      detruire: () => racine.remove(),
    };
  }

  function oublier() { if (courant) { courant.detruire(); courant = null; } }

  // Appelé par le panneau Propriétés à chaque document relu : vrai si le calque actif est un calque de réglage (son
  // éditeur est alors affiché dans `corps`), faux sinon (le panneau montre ses lignes habituelles).
  function proprietes(corps, doc) {
    const c = doc && doc.activeLayer != null ? trouverCalque(doc.layers, doc.activeLayer) : null;
    const kind = kindDe(c);
    if (!kind) { oublier(); return false; }
    if (kind === "colorLookup" && !lutList) chargerLuts();
    const etat = depuisInspect(kind, c.adjustment, lutList);
    const cle = [doc.index, doc.name, PL.etat.generation, c.id, kind].join("|");
    if (courant && courant.cleIdentite === cle && corps.contains(courant.racine)) { courant.maj(etat); return true; }
    oublier();
    corps.textContent = "";
    courant = { ...construire(corps, c, kind, etat), cleIdentite: cle };
    return true;
  }

  /* petit menu des 16 kinds (bouton du pied du panneau Calques) */
  function fermerMenu() {
    if (!menuOuvert) return;
    menuOuvert.el.remove();
    document.removeEventListener("pointerdown", menuOuvert.dehors, true);
    document.removeEventListener("keydown", menuOuvert.touche, true);
    window.removeEventListener("blur", fermerMenu);
    menuOuvert = null;
  }
  function menu(ancre) {
    if (menuOuvert) { fermerMenu(); return; }
    if (!PL.etat.doc) return;
    const fl = el("div", "flyout rg-menu"); fl.setAttribute("role", "menu");
    for (const x of KINDS) {
      const b = el("button", "flyout-ligne"); b.type = "button"; b.setAttribute("role", "menuitem");
      const ico = el("span", "ico"); ico.dataset.icone = x.icone;
      b.append(ico, el("span", "nom", T(x.cle)));
      b.addEventListener("click", () => { fermerMenu(); PL.creerReglage(x.kind); });
      fl.appendChild(b);
    }
    document.body.appendChild(fl);
    PL.hydraterIcones(fl);
    const r = ancre.getBoundingClientRect();
    const left = Math.max(4, Math.min(r.left, innerWidth - fl.offsetWidth - 4));
    let top = r.top - fl.offsetHeight - 2;
    if (top < 4) top = Math.min(r.bottom + 2, innerHeight - fl.offsetHeight - 4);
    fl.style.left = left + "px"; fl.style.top = Math.max(4, top) + "px";
    const dehors = (ev) => { if (!fl.contains(ev.target) && ev.target !== ancre && !ancre.contains(ev.target)) fermerMenu(); };
    const touche = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fermerMenu(); ancre.focus(); } };
    menuOuvert = { el: fl, dehors, touche };
    document.addEventListener("pointerdown", dehors, true);
    document.addEventListener("keydown", touche, true);
    window.addEventListener("blur", fermerMenu);
    const premier = fl.querySelector("button");
    if (premier) premier.focus();
  }

  // Fin de prise (le pointeur se relâche souvent HORS du panneau) : l'éditeur affiché pose ce qu'il a différé.
  const finPrise = () => { if (courant && courant.relacher) courant.relacher(); };
  document.addEventListener("pointerup", finPrise, true);
  document.addEventListener("pointercancel", finPrise, true);

  PL.reglages = {
    kindDe,
    icone: (kind) => (infoKind(kind) || {}).icone || "circle",
    cle: (kind) => (infoKind(kind) || {}).cle || "photolab.type_calque.adjustment",
    proprietes,
    menu,
    montrer: (nom) => { deplier(); montrer(nom); },
  };

  PL.surDoc.push((doc) => {
    boutons.forEach((b) => { b.disabled = !doc; });
    if (!doc) { fermerMenu(); oublier(); }
  });
  // Le panneau Propriétés a pu se dessiner avant que PL.reglages existe (document déjà ouvert) : on le relit.
  if (PL.etat.doc && corpsProps) proprietes(corpsProps, PL.etat.doc);
}
