// mod-peinture.js — t155 (parité L5) : les 18 outils de peinture et de retouche. Chaque geste validé = UNE commande
// paint.* du moteur (D1 : le moteur peint, l'écran ne dessine qu'un contour d'aperçu pendant le geste).
// Unités relevées sur le vrai moteur (banc test_photolab_peinture) : paint.stroke (Pinceau, Gomme) prend dureté,
// opacité, flux et lissage en 0..1 ; Crayon et Gomme d'arrière-plan aussi pour ce qu'ils ont ; les outils de retouche
// (tampon, correcteurs, densité, flou…) prennent dureté, opacité et flux en 0..100. L'écran garde partout des %
// entiers 0..100 et convertit ici.
// Barres d'options : relevé de l'application de référence + inventaire photocraft B §2.3 ; écarts dans le plan
// docs/superpowers/plans/2026-10-08-photolab-parite-l5-peinture.md. Fonctions PURES exportées (qa/peinture.test.mjs).
import { MODES_FUSION } from "./mod-calques.js";

export const TAILLE_MIN = 1, TAILLE_MAX = 5000;     // amont B §3.9 et §8 (taille de pointe 1..5000 px)

// outil -> {commande, sorte : trait | clic | degrade}
export const OUTILS_PEINTURE = {
  brush: { commande: "paint.stroke", sorte: "trait" },
  pencil: { commande: "paint.pencil", sorte: "trait" },
  mixerBrush: { commande: "paint.mixerBrush", sorte: "trait" },
  eraser: { commande: "paint.stroke", sorte: "trait" },              // ou paint.pencil / paint.historyBrush selon les options
  backgroundEraser: { commande: "paint.backgroundEraser", sorte: "trait" },
  magicEraser: { commande: "paint.magicEraser", sorte: "clic" },
  cloneStamp: { commande: "paint.cloneStamp", sorte: "trait" },
  historyBrush: { commande: "paint.historyBrush", sorte: "trait" },
  spotHealing: { commande: "paint.spotHealing", sorte: "trait" },
  healing: { commande: "paint.healingBrush", sorte: "trait" },
  gradient: { commande: "paint.gradient", sorte: "degrade" },
  paintBucket: { commande: "paint.bucket", sorte: "clic" },
  blur: { commande: "paint.blur", sorte: "trait" },
  sharpen: { commande: "paint.sharpen", sorte: "trait" },
  smudge: { commande: "paint.smudge", sorte: "trait" },
  dodge: { commande: "paint.dodge", sorte: "trait" },
  burn: { commande: "paint.burn", sorte: "trait" },
  sponge: { commande: "paint.sponge", sorte: "trait" },
};

const snake = (s) => s.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
// type : nombre | case | choix (boutons exclusifs) | liste (sélecteur). libelle = clé du dictionnaire ; une valeur v
// d'un choix ou d'une liste a pour libellé libelle + "." + snake(v), sauf la fusion (clés photolab.fusion.* des calques).
const opt = (type, cle, extra = {}) => ({ type, cle, libelle: "photolab.peinture." + snake(cle), ...extra });
const pct = (cle, min = 0) => opt("nombre", cle, { min, max: 100, pas: 1, unite: "%" });
const TAILLE = opt("nombre", "taille", { min: TAILLE_MIN, max: TAILLE_MAX, pas: 1, unite: "px" });
const DURETE = pct("durete");
const FUSION = opt("liste", "fusion", { valeurs: MODES_FUSION.map((m) => m.id), fusion: true });
const OPAC0 = pct("opacite"), OPAC1 = pct("opacite", 1), FLUX = pct("flux", 1);
// « Lissage du tracé » (smoothing) des pinceaux ; la case « Lissage » de la gomme magique et du pot = anticrénelage.
const LISSAGE = pct("lissageTrait");
const CASE = (cle) => opt("case", cle);
const TOUS = CASE("tousCalques");
const ECHANTILLON = opt("liste", "echantillon", { valeurs: ["current", "currentAndBelow", "all"] });
const RETOUCHE = [TAILLE, DURETE, pct("intensite", 1), TOUS];
const DENSITE = [TAILLE, DURETE, opt("liste", "gamme", { valeurs: ["shadows", "midtones", "highlights"] }), pct("exposition", 1), CASE("protegerTons")];

export const OPTIONS_PEINTURE = {
  brush: [TAILLE, DURETE, FUSION, OPAC0, FLUX, LISSAGE],
  pencil: [TAILLE, FUSION, OPAC0, CASE("effacementAuto")],
  mixerBrush: [TAILLE, pct("humidite"), pct("charge"), pct("melange"), FLUX, TOUS],
  eraser: [opt("choix", "modeGomme", { valeurs: ["pinceau", "crayon"] }), TAILLE, DURETE, OPAC0, FLUX, LISSAGE, CASE("historique")],
  backgroundEraser: [TAILLE, DURETE, opt("choix", "echantillonnage", { valeurs: ["continuous", "once", "backgroundSwatch"] }),
    opt("liste", "limites", { valeurs: ["discontiguous", "contiguous", "findEdges"] }), pct("tolerance"), CASE("protegerPremierPlan")],
  magicEraser: [opt("nombre", "tolerance", { min: 0, max: 255, pas: 1 }), CASE("lissage"), CASE("contigu"), TOUS, OPAC1],
  cloneStamp: [TAILLE, DURETE, FUSION, OPAC1, FLUX, CASE("aligne"), ECHANTILLON],
  historyBrush: [TAILLE, DURETE, OPAC1, FLUX],
  spotHealing: [TAILLE, DURETE, opt("choix", "type", { valeurs: ["contentAware", "createTexture", "proximityMatch"] })],
  healing: [TAILLE, DURETE, FUSION, CASE("aligne"), ECHANTILLON],
  gradient: [opt("choix", "style", { valeurs: ["linear", "radial", "angle", "reflected", "diamond"] }), FUSION, OPAC1, CASE("inverser"), CASE("tramage")],
  paintBucket: [opt("nombre", "tolerance", { min: 0, max: 255, pas: 1 }), OPAC1, CASE("lissage"), CASE("contigu")],
  blur: RETOUCHE,
  sharpen: [...RETOUCHE, CASE("protegerDetails")],
  smudge: [...RETOUCHE, CASE("peintureDoigt")],
  dodge: DENSITE,
  burn: DENSITE,
  sponge: [TAILLE, DURETE, opt("liste", "modeEponge", { valeurs: ["desaturate", "saturate"] }), FLUX, CASE("vibrance")],
};

// Défauts : ceux de l'application de référence quand elle en montre (tailles 13 / 19 / 21 / 65, tolérance 32 ou 50 %,
// exposition 50 %, flux de l'éponge 50 %, lissage 10 %), sinon ceux du moteur.
const DEFAUTS = {
  brush: { taille: 13, durete: 100, fusion: "normal", opacite: 100, flux: 100, lissageTrait: 10 },
  pencil: { taille: 1, fusion: "normal", opacite: 100, effacementAuto: false },
  mixerBrush: { taille: 13, humidite: 50, charge: 50, melange: 50, flux: 100, tousCalques: false },
  eraser: { modeGomme: "pinceau", taille: 13, durete: 100, opacite: 100, flux: 100, lissageTrait: 0, historique: false },
  backgroundEraser: { taille: 13, durete: 100, echantillonnage: "continuous", limites: "contiguous", tolerance: 50, protegerPremierPlan: false },
  magicEraser: { tolerance: 32, lissage: true, contigu: true, tousCalques: false, opacite: 100 },
  cloneStamp: { taille: 21, durete: 0, fusion: "normal", opacite: 100, flux: 100, aligne: true, echantillon: "current" },
  historyBrush: { taille: 21, durete: 0, opacite: 100, flux: 100 },
  spotHealing: { taille: 19, durete: 100, type: "contentAware" },
  healing: { taille: 19, durete: 100, fusion: "normal", aligne: true, echantillon: "current" },
  gradient: { style: "linear", fusion: "normal", opacite: 100, inverser: false, tramage: true },
  paintBucket: { tolerance: 32, opacite: 100, lissage: true, contigu: true },
  blur: { taille: 13, durete: 0, intensite: 50, tousCalques: false },
  sharpen: { taille: 13, durete: 0, intensite: 50, tousCalques: false, protegerDetails: true },
  smudge: { taille: 13, durete: 0, intensite: 50, tousCalques: false, peintureDoigt: false },
  dodge: { taille: 65, durete: 0, gamme: "midtones", exposition: 50, protegerTons: true },
  burn: { taille: 65, durete: 0, gamme: "midtones", exposition: 50, protegerTons: true },
  sponge: { taille: 65, durete: 0, modeEponge: "desaturate", flux: 50, vibrance: true },
};

export const optionsPeinture = (id) => OPTIONS_PEINTURE[id] || [];
export const defautsPeinture = (id) => ({ ...(DEFAUTS[id] || {}) });

const taillePx = (t) => Math.min(TAILLE_MAX, Math.max(TAILLE_MIN, Math.round(Number(t) || TAILLE_MIN)));
const un = (v) => Math.min(100, Math.max(0, Number(v) || 0)) / 100;          // % -> 0..1
const cent = (v) => Math.min(100, Math.max(0, Math.round(Number(v) || 0)));   // % entier

// Un trait (glisser) -> {command, params} ; null sans point ou pour un outil qui n'est pas un outil de trait.
export function commandeTrait(outil, points, o, couleurs) {
  const def = OUTILS_PEINTURE[outil];
  if (!def || def.sorte !== "trait" || !Array.isArray(points) || !points.length) return null;
  const size = taillePx(o.taille);
  const fg = couleurs && couleurs.fg;
  const retouche = (extra) => ({ points, size, hardness: cent(o.durete), ...extra });
  switch (outil) {
    case "brush":
      return { command: def.commande, params: { points, size, hardness: un(o.durete), opacity: un(o.opacite), flow: un(o.flux),
        smoothing: un(o.lissageTrait), mode: o.fusion, color: fg } };
    case "pencil":
      return { command: def.commande, params: { points, size, opacity: un(o.opacite), mode: o.fusion, autoErase: !!o.effacementAuto, color: fg } };
    case "mixerBrush":
      return { command: def.commande, params: { points, size, wet: cent(o.humidite), load: cent(o.charge), mix: cent(o.melange),
        flow: cent(o.flux), sampleAllLayers: !!o.tousCalques, color: fg } };
    case "eraser":
      // « Effacer d'après l'historique » = Forme d'historique (référence) ; mode Crayon = bords nets ; sinon pinceau effaceur.
      if (o.historique) return { command: "paint.historyBrush", params: retouche({ opacity: cent(o.opacite), flow: cent(o.flux) }) };
      if (o.modeGomme === "crayon") return { command: "paint.pencil", params: { points, size, opacity: un(o.opacite), erase: true } };
      return { command: "paint.stroke", params: { points, size, hardness: un(o.durete), opacity: un(o.opacite), flow: un(o.flux),
        smoothing: un(o.lissageTrait), erase: true } };
    case "backgroundEraser":
      return { command: def.commande, params: { points, size, hardness: un(o.durete), sampling: o.echantillonnage, limits: o.limites,
        tolerance: cent(o.tolerance), protectForegroundColor: !!o.protegerPremierPlan } };
    case "cloneStamp":
      return { command: def.commande, params: retouche({ opacity: cent(o.opacite), flow: cent(o.flux), aligned: !!o.aligne,
        sampleLayer: o.echantillon, mode: o.fusion }) };
    case "healing":
      return { command: def.commande, params: retouche({ aligned: !!o.aligne, sampleLayer: o.echantillon, mode: o.fusion }) };
    case "spotHealing":
      return { command: def.commande, params: retouche({ type: o.type }) };
    case "historyBrush":
      return { command: def.commande, params: retouche({ opacity: cent(o.opacite), flow: cent(o.flux) }) };
    case "blur":
      return { command: def.commande, params: retouche({ strength: cent(o.intensite), sampleAllLayers: !!o.tousCalques }) };
    case "sharpen":
      return { command: def.commande, params: retouche({ strength: cent(o.intensite), sampleAllLayers: !!o.tousCalques, protectDetail: !!o.protegerDetails }) };
    case "smudge":
      return { command: def.commande, params: retouche({ strength: cent(o.intensite), sampleAllLayers: !!o.tousCalques, fingerPainting: !!o.peintureDoigt }) };
    case "dodge":
    case "burn":
      return { command: def.commande, params: retouche({ range: o.gamme, exposure: cent(o.exposition), protectTones: !!o.protegerTons }) };
    case "sponge":
      return { command: def.commande, params: retouche({ mode: o.modeEponge, vibrance: !!o.vibrance, flow: cent(o.flux) }) };
    default:
      return null;
  }
}

// Un clic (Pot de peinture, Gomme magique) -> commande sur le pixel entier visé ; null hors du document.
export function commandeClic(outil, x, y, o, couleurs, doc) {
  const def = OUTILS_PEINTURE[outil];
  if (!def || def.sorte !== "clic" || !doc) return null;
  const px = Math.floor(x), py = Math.floor(y);
  if (!(px >= 0 && py >= 0 && px < doc.width && py < doc.height)) return null;
  if (outil === "paintBucket") {
    return { command: def.commande, params: { x: px, y: py, tolerance: Math.round(o.tolerance), contiguous: !!o.contigu, antiAlias: !!o.lissage,
      contents: "foreground", opacity: cent(o.opacite), color: couleurs && couleurs.fg } };
  }
  return { command: def.commande, params: { x: px, y: py, tolerance: Math.round(o.tolerance), antiAlias: !!o.lissage, contiguous: !!o.contigu,
    sampleAllLayers: !!o.tousCalques, opacity: cent(o.opacite) } };
}

// Les huit directions à 45° en vecteurs EXACTS (pas de cos/sin : 90° donnerait 6e-17 au lieu de 0).
const R = Math.SQRT1_2;
const DIRECTIONS = [[1, 0], [R, R], [0, 1], [-R, R], [-1, 0], [-R, -R], [0, -1], [R, -R]];
// Point b ramené sur la direction à 45° la plus proche depuis a (longueur = projection sur cette direction).
function caler(a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  let meilleur = DIRECTIONS[0], proj = -Infinity;
  for (const d of DIRECTIONS) { const p = dx * d[0] + dy * d[1]; if (p > proj) { proj = p; meilleur = d; } }
  return [a[0] + meilleur[0] * proj, a[1] + meilleur[1] * proj];
}

// Dégradé (glisser de -> a) ; Maj cale par 45° ; null si le glisser fait moins d'un pixel.
export function commandeDegrade(de, a, o, maj) {
  if (!de || !a) return null;
  const fin = maj ? caler(de, a) : [a[0], a[1]];
  if (Math.hypot(fin[0] - de[0], fin[1] - de[1]) < 1) return null;
  return { command: "paint.gradient", params: { from: [de[0], de[1]], to: fin, style: o.style, mode: o.fusion, opacity: cent(o.opacite),
    reverse: !!o.inverser, dither: !!o.tramage } };
}

// Maj tenu pendant un trait : une ligne droite depuis le point d'appui, calée à 0 / 45 / 90°.
export const contraindreTrait = (depart, p) => [[depart[0], depart[1]], caler(depart, p)];
// Maj-clic : une ligne depuis la fin du trait précédent (null s'il n'y en a pas).
export const ligneDepuis = (dernier, p) => (dernier ? [[dernier[0], dernier[1]], [p[0], p[1]]] : null);

// Point de trait arrondi au dixième de pixel ; ignoré s'il est à moins de `pas` px ÉCRAN du précédent (le zoom compte).
// pression : celle d'un stylet (bornée 0..1) en 3e valeur ; null pour la souris (le moteur prend alors la pleine pression).
export function ajouterPointTrait(points, x, y, z, pression = null, pas = 1) {
  const p = [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
  if (pression !== null && pression !== undefined && Number.isFinite(Number(pression))) p.push(Math.min(1, Math.max(0, Number(pression))));
  const der = points[points.length - 1];
  if (der && Math.hypot((p[0] - der[0]) * z, (p[1] - der[1]) * z) < pas) return points;
  return [...points, p];
}

// [ / ] : taille ÷ / × 1,25 (au moins 1 px de pas), bornée 1..5000 (amont shortcuts.rs : [ ] ÷1,25 / ×1,25).
export function tailleCran(t, sens) {
  const n = sens > 0 ? Math.max(t + 1, Math.round(t * 1.25)) : Math.min(t - 1, Math.round(t / 1.25));
  return Math.min(TAILLE_MAX, Math.max(TAILLE_MIN, n));
}
// Maj+[ / Maj+] : dureté ±25 %, bornée 0..100.
export const dureteCran = (d, sens) => Math.min(100, Math.max(0, d + (sens > 0 ? 25 : -25)));

// Chiffres (amont opacity_keys.rs) : 1 = 10 % … 9 = 90 %, 0 = 100 % ; deux chiffres en moins de 800 ms = la valeur
// exacte (4 puis 5 = 45 %, 0 puis 5 = 5 %) ; un troisième recommence. -> {valeur, etat} (etat à repasser au suivant).
export function valeurChiffres(etat, chiffre, t) {
  if (etat && t - etat.t < 800) return { valeur: etat.premier * 10 + chiffre, etat: null };
  return { valeur: chiffre === 0 ? 100 : chiffre * 10, etat: { premier: chiffre, t } };
}
// Option visée par les chiffres : l'opacité (Maj : le flux) quand l'outil l'a, sinon rien.
export function cibleChiffres(outil, maj) {
  const cle = maj ? "flux" : "opacite";
  return optionsPeinture(outil).some((o) => o.cle === cle) ? cle : null;
}

// Tampon et Correcteur peignent depuis une source (Alt-clic -> cloneSource.set) : le moteur refuse sans elle.
export const sourceRequise = (outil) => outil === "cloneStamp" || outil === "healing";
// cloneSource.list -> la source active est-elle posée ?
export function sourceActive(liste) {
  const s = liste && Array.isArray(liste.sources) ? liste.sources.find((x) => x && x.index === liste.active) : null;
  return !!(s && Array.isArray(s.source));
}
// Alt = pipette temporaire (amont canvas.rs:2172-2194).
export const altPipette = (outil) => outil === "brush" || outil === "pencil" || outil === "gradient" || outil === "paintBucket";

/* ───────────── côté DOM ───────────── */

export function initPeinture(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.etat.peinture = {};
  const opts = (id) => (PL.etat.peinture[id] = PL.etat.peinture[id] || defautsPeinture(id));
  PL.optionsPeintureDe = opts;
  let dernier = null;          // fin du dernier trait (Maj-clic)

  // Alt-clic des outils de pinceau : la pipette (premier plan), même chemin que l'outil Pipette.
  const pipette = (p) => PL.gestes.eyedropper && PL.gestes.eyedropper.appui(p, { altKey: false });
  const pression = (ev) => (ev && ev.pointerType === "pen" ? ev.pressure : null);
  const apercuTrait = (id, points) => {
    const o = opts(id);
    PL.apercu = { type: "trait", points, taille: o.taille || 1, couleur: ["brush", "pencil", "mixerBrush"].includes(id) ? PL.etat.couleurs.fg : null };
    PL.dessinerFourmis();
  };
  const pointe = (id, p) => {
    const o = opts(id);
    // t152 : Affichage › Afficher › Aperçu du pinceau (et Extras)
    const montre = !PL.affichage || PL.affichage.voir("apercuPinceau");
    PL.apercu = o.taille && montre ? { type: "pointe", x: p.x, y: p.y, taille: o.taille } : null;
    PL.dessinerFourmis();
  };

  async function lancerTrait(id, points) {
    const c = commandeTrait(id, points, opts(id), PL.etat.couleurs);
    if (!c) return;
    if (sourceRequise(id)) {
      const l = await PL.executer("cloneSource.list", {}, { cycle: false });
      if (!l.ok) return;
      if (!sourceActive(l.r)) { PL.signaler(T("photolab.peinture.source_requise"), true); return; }
    }
    dernier = points[points.length - 1];
    await PL.executer(c.command, c.params);
  }

  function outilTrait(id) {
    let g = null;
    return {
      async appui(p, ev) {
        if (ev.altKey && altPipette(id)) { pipette(p); return; }
        if (ev.altKey && sourceRequise(id)) {
          const r = await PL.executer("cloneSource.set", { source: [Math.round(p.x), Math.round(p.y)] }, { cycle: false });
          if (r.ok) PL.signaler(T("photolab.peinture.source_definie"));
          return;
        }
        const depart = [Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10];
        const ligne = ev.shiftKey ? ligneDepuis(dernier, depart) : null;
        g = { depart, ligne, points: ligne || ajouterPointTrait([], p.x, p.y, PL.vue.v.z, pression(ev)) };
        apercuTrait(id, g.points);
      },
      bouger(p, ev) {
        if (!g) return;
        g.points = ev.shiftKey ? contraindreTrait(g.depart, [p.x, p.y]) : (g.ligne ? g.ligne : ajouterPointTrait(g.points, p.x, p.y, PL.vue.v.z, pression(ev)));
        apercuTrait(id, g.points);
      },
      relacher() {
        if (!g) return;
        const points = g.points; g = null; PL.apercu = null; PL.dessinerFourmis();
        lancerTrait(id, points);
      },
      survol(p) { if (!g) pointe(id, p); },
      annuler() { g = null; PL.apercu = null; PL.dessinerFourmis(); },
      touche(ev) { if (ev.key !== "Escape" || !g) return false; g = null; PL.apercu = null; PL.dessinerFourmis(); return true; },
      quitter() { g = null; },
    };
  }

  function outilClic(id) {
    return {
      appui(p, ev) {
        if (ev.altKey && altPipette(id)) { pipette(p); return; }
        const c = commandeClic(id, p.x, p.y, opts(id), PL.etat.couleurs, PL.etat.doc);
        if (c) PL.executer(c.command, c.params);
      },
      bouger() {}, relacher() {},
    };
  }

  function outilDegrade() {
    let g = null;
    const fin = (p, ev) => (ev.shiftKey ? contraindreTrait(g.de, [p.x, p.y])[1] : [p.x, p.y]);
    return {
      appui(p, ev) {
        if (ev.altKey) { pipette(p); return; }
        g = { de: [Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10] };
      },
      bouger(p, ev) { if (!g) return; PL.apercu = { type: "ligne", de: g.de, a: fin(p, ev) }; PL.dessinerFourmis(); },
      relacher(p, ev) {
        if (!g) return;
        const c = commandeDegrade(g.de, [p.x, p.y], opts("gradient"), ev.shiftKey);
        g = null; PL.apercu = null; PL.dessinerFourmis();
        if (c) PL.executer(c.command, c.params);
      },
      annuler() { g = null; PL.apercu = null; PL.dessinerFourmis(); },
      touche(ev) { if (ev.key !== "Escape" || !g) return false; g = null; PL.apercu = null; PL.dessinerFourmis(); return true; },
      quitter() { g = null; },
    };
  }

  for (const [id, def] of Object.entries(OUTILS_PEINTURE)) {
    PL.gestes[id] = def.sorte === "trait" ? outilTrait(id) : def.sorte === "clic" ? outilClic(id) : outilDegrade();
  }
  // Quitter le canevas : plus de cercle de pointe.
  PL.$("#toile").addEventListener("pointerleave", () => { if (PL.apercu && PL.apercu.type === "pointe") { PL.apercu = null; PL.dessinerFourmis(); } });

  // Clavier : [ ] taille, Maj+[ ] dureté, chiffres opacité (Maj : flux). Touches physiques acceptées (AZERTY : la
  // touche à droite du P donne « ^ », celle d'après « $ » ; les chiffres demandent Maj).
  let chiffres = null;
  const enSaisie = (ev) => ev.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || "") || ev.target.isContentEditable);
  document.addEventListener("keydown", (ev) => {
    const id = PL.etat.outil;
    if (!OUTILS_PEINTURE[id] || ev.repeat && !/Bracket/.test(ev.code || "") || enSaisie(ev) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (document.querySelector(".pl-voile, .dz-dialogue, .menu-panneau, .flyout")) return;
    const o = opts(id);
    const crochet = ev.code === "BracketLeft" || ev.key === "[" || ev.key === "{" ? -1 : ev.code === "BracketRight" || ev.key === "]" || ev.key === "}" ? 1 : 0;
    if (crochet) {
      if (ev.shiftKey && o.durete !== undefined) o.durete = dureteCran(o.durete, crochet);
      else if (!ev.shiftKey && o.taille !== undefined) o.taille = tailleCran(o.taille, crochet);
      else return;
      ev.preventDefault();
      if (PL.reconstruireOptions) PL.reconstruireOptions();
      if (PL.apercu && PL.apercu.type === "pointe") { PL.apercu.taille = o.taille; PL.dessinerFourmis(); }
      return;
    }
    const m = /^(?:Digit|Numpad)(\d)$/.exec(ev.code || "");
    if (!m) return;
    const cle = cibleChiffres(id, ev.shiftKey);
    if (!cle) return;
    ev.preventDefault();
    const r = valeurChiffres(chiffres, Number(m[1]), performance.now());
    chiffres = r.etat;
    const spec = optionsPeinture(id).find((x) => x.cle === cle);
    o[cle] = Math.min(spec.max, Math.max(spec.min, r.valeur));
    if (PL.reconstruireOptions) PL.reconstruireOptions();
    PL.signaler(T("photolab.peinture." + cle) + " : " + o[cle] + " %");
  });
}
