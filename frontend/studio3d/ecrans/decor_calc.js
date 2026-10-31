/* t401 (31/10/2026) — le CALCUL de l'écran Décor › Végétation, sans DOM ni three.js : il tourne sous node
   (banc qa/ecrans.test.mjs). Le générateur est ez-tree 1.1.0 (MIT, vendorisé dans /lib3d/eztree, D6) ; ce module
   traduit les réglages de l'écran en OPTIONS d'ez-tree et lit / écrit la recette `.decor.json`.

   Espèces : le relevé de TreeGen (Sorceress) en compte 23. ez-tree en apporte 16 préréglages (frêne, tremble, chêne,
   pin en trois tailles, trois buissons, une treille). Chaque espèce part du préréglage le plus proche et ne change
   que ce que l'espèce exige (écorce, teinte, port, nombre de niveaux) : c'est une APPROCHE, dite comme telle dans
   l'aide de l'écran, pas une botanique. Même graine + même recette = même arbre (le générateur est déterministe). */
"use strict";

const TAILLES = ["petit", "moyen", "grand"];
const SUFFIXE = { petit: "Small", moyen: "Medium", grand: "Large" };

/* groupe, préréglage d'ez-tree (sans taille quand il en existe trois), retouches */
export const ESPECES = [
  { id: "chene", groupe: "feuillus", hauteur: 15, base: "Oak", feuille: "oak", ecorce: "oak" },
  { id: "frene", groupe: "feuillus", hauteur: 14, base: "Ash", feuille: "ash", ecorce: "oak" },
  { id: "tremble", groupe: "feuillus", hauteur: 13, base: "Aspen", feuille: "aspen", ecorce: "birch" },
  { id: "bouleau", groupe: "feuillus", hauteur: 12, base: "Aspen", feuille: "aspen", ecorce: "birch", teinteFeuille: 0xd8f0a0 },
  { id: "erable", groupe: "feuillus", hauteur: 12, base: "Ash", feuille: "oak", ecorce: "oak", teinteFeuille: 0xf2b8a0 },
  { id: "cerisier", groupe: "feuillus", hauteur: 7, base: "Oak", feuille: "aspen", ecorce: "willow", teinteFeuille: 0xffc6dc, enFleurs: true },
  { id: "saule", groupe: "feuillus", hauteur: 10, base: "Ash", feuille: "ash", ecorce: "willow", pleureur: true },
  { id: "pin", groupe: "coniferes", hauteur: 18, base: "Pine", feuille: "pine", ecorce: "pine", persistant: true },
  { id: "epicea", groupe: "coniferes", hauteur: 20, base: "Pine", feuille: "pine", ecorce: "pine", persistant: true, enfants: 1.3 },
  { id: "sapin", groupe: "coniferes", hauteur: 16, base: "Pine", feuille: "pine", ecorce: "pine", persistant: true, teinteFeuille: 0xb8d8c0 },
  { id: "palmier", groupe: "tropicaux", hauteur: 10, base: "Ash", feuille: "ash", ecorce: "willow", persistant: true, palme: true },
  { id: "cocotier", groupe: "tropicaux", hauteur: 14, base: "Ash", feuille: "ash", ecorce: "willow", persistant: true, palme: true, courbe: 0.35 },
  { id: "arbre_nu", groupe: "exotiques", hauteur: 12, base: "Oak", feuille: "oak", ecorce: "oak", sansFeuilles: true },
  { id: "bonsai", groupe: "exotiques", hauteur: 0.4, base: "Oak", feuille: "oak", ecorce: "oak", courbe: 0.6, taillesFixes: "petit" },
  { id: "treille", groupe: "exotiques", hauteur: 2.5, fixe: "Trellis", feuille: "oak", ecorce: "oak" },
  { id: "buisson_bas", groupe: "arbustes", hauteur: 0.6, fixe: "Bush 1", feuille: "oak", ecorce: "oak" },
  { id: "buisson", groupe: "arbustes", hauteur: 1.5, fixe: "Bush 2", feuille: "oak", ecorce: "oak" },
  { id: "grand_arbuste", groupe: "arbustes", hauteur: 3, fixe: "Bush 3", feuille: "ash", ecorce: "oak" },
  { id: "buisson_fleuri", groupe: "arbustes", hauteur: 1.5, fixe: "Bush 2", feuille: "aspen", ecorce: "oak", teinteFeuille: 0xffb0d0, enFleurs: true },
  { id: "arbuste_mort", groupe: "arbustes", hauteur: 1, fixe: "Bush 1", feuille: "oak", ecorce: "willow", sansFeuilles: true },
  { id: "baies", groupe: "couvre_sol", hauteur: 1, fixe: "Bush 1", feuille: "aspen", ecorce: "oak", teinteFeuille: 0x8fb070 },
  { id: "bruyere", groupe: "couvre_sol", hauteur: 0.4, fixe: "Bush 3", feuille: "pine", ecorce: "oak", teinteFeuille: 0xc79ad8, persistant: true },
  { id: "oyat", groupe: "couvre_sol", hauteur: 0.8, fixe: "Bush 1", feuille: "pine", ecorce: "willow", teinteFeuille: 0xd8d0a0, persistant: true, herbe: true },
];
export const GROUPES = ["feuillus", "coniferes", "tropicaux", "exotiques", "arbustes", "couvre_sol"];
export const ONGLETS = { arbres: ["feuillus", "coniferes", "tropicaux", "exotiques"], sol: ["arbustes", "couvre_sol"] };
export const FEUILLES = ["auto", "oak", "ash", "aspen", "pine"];
export const ECORCES = ["auto", "oak", "birch", "pine", "willow"];
export const SAISONS = ["ete", "automne", "hiver"];

export const REGLAGES_DEFAUT = {
  espece: "chene", taille: "moyen", echelle: 1, niveaux: 3, feuillage: "reel", feuilles: true, forme: "auto",
  saison: "ete", densite: 50, tailleFeuille: 1, retombee: 0.3, rameaux: true, ecorce: "auto",
  teinteEcorce: "#ffffff", teinteFeuille: "#ffffff", graine: 1,
  vent: true, ventForce: 0.7, ventVitesse: 1.1, ventDirection: 42, frisson: 5, ciel: true,
};

export const especeDe = (id) => ESPECES.find((e) => e.id === id) || ESPECES[0];

/* le nom du préréglage d'ez-tree pour une espèce et une taille */
export function presetDe(espece, taille) {
  const e = typeof espece === "string" ? especeDe(espece) : espece;
  if (e.fixe) return e.fixe;
  const t = e.taillesFixes || (TAILLES.includes(taille) ? taille : "moyen");
  return `${e.base} ${SUFFIXE[t]}`;
}

const hex = (s, defaut) => {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(s || ""));
  return m ? parseInt(m[1], 16) : defaut;
};

/* multiplie deux teintes (0xRRGGBB) canal par canal : la teinte de l'espèce, puis celle de l'utilisateur */
export function melanger(a, b) {
  const c = (x, s) => (x >> s) & 255;
  const m = (s) => Math.round((c(a, s) * c(b, s)) / 255);
  return (m(16) << 16) | (m(8) << 8) | m(0);
}

const SAISON = { ete: 0xffffff, automne: 0xe8904a, hiver: 0xe6ecf0 };

/* clone profond d'objets JSON (les préréglages et les options d'ez-tree ne portent que des données) */
const clone = (o) => JSON.parse(JSON.stringify(o));

/* les OPTIONS d'ez-tree pour des réglages de l'écran. `presets` = les données des préréglages (presets/donnees.js,
   rangées par nom comme TreePreset). Aucune option inconnue d'ez-tree n'est inventée. */
export function optionsPour(reglages, presets) {
  const r = { ...REGLAGES_DEFAUT, ...(reglages || {}) };
  const e = especeDe(r.espece);
  const base = presets[presetDe(e, r.taille)];
  if (!base) throw new Error("préréglage absent : " + presetDe(e, r.taille));
  const o = clone(base);
  o.seed = Math.max(0, Math.floor(Number(r.graine) || 0));
  /* branches */
  const niveaux = Math.max(0, Math.min(3, Math.round(Number(r.niveaux))));
  if (Number.isFinite(niveaux)) o.branch.levels = Math.min(o.branch.levels, niveaux);
  if (e.enfants) for (const k of Object.keys(o.branch.children)) o.branch.children[k] = Math.round(o.branch.children[k] * e.enfants);
  if (e.courbe) for (const k of Object.keys(o.branch.gnarliness)) o.branch.gnarliness[k] = Math.max(o.branch.gnarliness[k], e.courbe);
  if (e.pleureur) o.branch.force = { direction: { x: 0, y: -1, z: 0 }, strength: 0.03 };
  if (e.palme) {
    o.branch.levels = Math.min(o.branch.levels, 1);
    o.branch.start = { ...o.branch.start, 1: 0.92 };
    o.branch.angle = { ...o.branch.angle, 1: 95 };
    o.branch.length = { ...o.branch.length, 0: o.branch.length[0] * 1.4, 1: o.branch.length[1] * 0.6 };
    o.leaves.size = o.leaves.size * 2.2;
  }
  if (e.herbe) { o.branch.levels = Math.min(o.branch.levels, 1); o.leaves.angle = 5; }
  /* écorce */
  o.bark.type = r.ecorce !== "auto" && ECORCES.includes(r.ecorce) ? r.ecorce : e.ecorce;
  o.bark.tint = hex(r.teinteEcorce, 0xffffff);
  /* feuilles : forme, densité, taille, retombée, saison, teinte */
  o.leaves.type = r.forme !== "auto" && FEUILLES.includes(r.forme) ? r.forme : e.feuille;
  const densite = Math.max(0, Math.min(100, Number(r.densite) || 0)) / 50;     // 50 = le préréglage
  o.leaves.count = Math.round(o.leaves.count * densite);
  o.leaves.size = o.leaves.size * Math.max(0.2, Math.min(3, Number(r.tailleFeuille) || 1));
  o.leaves.angle = Math.round(Math.max(0, Math.min(1, Number(r.retombee) || 0)) * 90);
  o.leaves.billboard = r.feuillage === "cartes" ? "single" : "double";
  if (r.feuillage === "cartes") o.leaves.count = Math.round(o.leaves.count / 2);
  let teinte = melanger(e.teinteFeuille || 0xffffff, hex(r.teinteFeuille, 0xffffff));
  if (r.saison === "automne" && !e.persistant) teinte = melanger(teinte, SAISON.automne);
  if (r.saison === "hiver") teinte = melanger(teinte, SAISON.hiver);
  o.leaves.tint = teinte;
  const sansFeuilles = e.sansFeuilles || !r.feuilles || (r.saison === "hiver" && !e.persistant);
  if (sansFeuilles) o.leaves.count = 0;
  if (!r.rameaux && o.branch.levels > 2) o.branch.levels = 2;     // les rameaux = le dernier niveau de branches
  return o;
}

/* la HAUTEUR visée en mètres réels : celle de l'espèce adulte (relevé de TreeGen : « calibrated to real-world
   metres ») × la taille (petit 0,7 · moyen 1 · grand 1,3, sauf taille fixe) × l'échelle choisie. ez-tree ne travaille
   pas en mètres : l'écran mesure l'arbre généré et le met à cette hauteur (`echelleVers`). */
export const FACTEUR_TAILLE = { petit: 0.7, moyen: 1, grand: 1.3 };
export function hauteurCible(reglages) {
  const r = { ...REGLAGES_DEFAUT, ...(reglages || {}) };
  const e = especeDe(r.espece);
  const f = e.taillesFixes ? 1 : (FACTEUR_TAILLE[r.taille] || 1);
  return Math.round(e.hauteur * f * Math.max(0.1, Math.min(4, Number(r.echelle) || 1)) * 1000) / 1000;
}

/* l'échelle à appliquer à un arbre mesuré `hauteurBrute` (unités d'ez-tree) pour qu'il fasse `hauteurCible` mètres */
export function echelleVers(hauteurBrute, reglages) {
  return hauteurBrute > 0 ? hauteurCible(reglages) / hauteurBrute : 1;
}

/* le vent : vecteur de force (m) dans la direction (degrés, 0 = +X), fréquence, échelle du bruit (frémissement) */
export function vent(reglages) {
  const r = { ...REGLAGES_DEFAUT, ...(reglages || {}) };
  if (!r.vent) return { force: [0, 0, 0], frequence: 0 };
  const a = (Number(r.ventDirection) || 0) * Math.PI / 180, f = Math.max(0, Number(r.ventForce) || 0);
  const k = (x) => Math.round(x * 1e4) / 1e4;
  return { force: [k(Math.cos(a) * f), 0, k(Math.sin(a) * f)], frequence: k(0.5 * Math.max(0, Number(r.ventVitesse) || 0)),
    echelle: Math.round(70 / Math.max(0.2, (Number(r.frisson) || 5) / 5)) };
}

/* ── la recette ─────────────────────────────────────────────────────────── */
export const FORMAT = "deepotus-decor";

export function recette(reglages, nom) {
  const r = { ...REGLAGES_DEFAUT, ...(reglages || {}) };
  return { format: FORMAT, version: 1, nom: String(nom || "").slice(0, 80) || `${r.espece}_${r.taille}_${r.graine}`,
    generateur: "ez-tree 1.1.0", reglages: r };
}

/* lit une recette ; ne garde que les clés connues, refuse ce qui n'en est pas une */
export function lireRecette(texte) {
  let j;
  try { j = typeof texte === "string" ? JSON.parse(texte) : texte; } catch { throw new Error("json"); }
  if (!j || j.format !== FORMAT || typeof j.reglages !== "object") throw new Error("format");
  const r = { ...REGLAGES_DEFAUT };
  for (const k of Object.keys(REGLAGES_DEFAUT)) {
    if (!(k in j.reglages)) continue;
    const v = j.reglages[k], d = REGLAGES_DEFAUT[k];
    if (typeof v === typeof d) r[k] = v;
  }
  if (!ESPECES.some((e) => e.id === r.espece)) r.espece = REGLAGES_DEFAUT.espece;
  return { nom: String(j.nom || ""), reglages: r };
}

/* le nom de fichier d'un export : minuscules, chiffres, tirets bas */
export function nomFichier(nom) {
  const s = String(nom || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 60);
  return s || "decor";
}
