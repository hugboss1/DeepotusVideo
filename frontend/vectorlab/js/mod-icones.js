// mod-icones.js — les icônes du Vectorlab : la suite « Deepotus Glyph »
// (frontend/shared/icons, G3 du 10/10/2026) remplace l'ancien sprite fin.
// Une icône = une fonction : chaque outil, action de la barre contextuelle
// et type de rangée du panneau Calques pointe sur SA clé `dz-*` (liste de
// travail docs/icones/suite-finale/implementation.json). Feuille pure :
// `dzi` rend par `window.dzIcone` (runtime /shared/icons/dz-icons.js) et,
// hors navigateur ou avant le runtime, par une référence au sprite servi ;
// l'inconnu reçoit la clé de repli dz-etat-inconnu plutôt qu'une exception.
export const REPLI = "dz-etat-inconnu";
const TAILLES = [16, 18, 20, 24];
export function dzi(cle, taille = 16, classe = "") {
  const cl = [classe, TAILLES.includes(taille) ? `dzi--${taille}` : ""].filter(Boolean).join(" ");
  const f = typeof globalThis !== "undefined" && globalThis.dzIcone;
  if (typeof f === "function") return f(cle, { taille, classe: cl });
  return `<svg class="dzi${cl ? " " + cl : ""}" width="${taille}" height="${taille}" aria-hidden="true" focusable="false"><use href="/shared/icons/dz-icons.svg#${cle}"></use></svg>`;
}
// outils de la colonne (posés par mod-barreoutils) et actions de la barre contextuelle (mod-barrecontexte)
export const ICONES = {
  select: "dz-outil-vec-selection",
  plume: "dz-outil-vec-plume",
  crayon: "dz-outil-vec-crayon",
  pinceauv: "dz-outil-vec-pinceau",
  rect: "dz-outil-vec-rectangle",
  ellipse: "dz-outil-vec-ellipse",
  ligne: "dz-outil-vec-ligne",
  forme: "dz-outil-vec-forme",
  noeuds: "dz-outil-vec-noeud",
  coin: "dz-outil-vec-coin",
  mesure: "dz-outil-vec-mesure",
  pipette: "dz-outil-vec-pipette",
  texte: "dz-outil-vec-texte",
  couteau: "dz-outil-vec-couteau",
  gomme: "dz-outil-vec-gomme",
  constructeur: "dz-outil-vec-constructeur",
  tuiles: "dz-outil-vec-tuiles",
  ia: "dz-media-generer-image",
  image: "dz-media-image",
  apparence: "dz-outil-vec-apparence",
  symbole: "dz-edit-symbole",
  tranche: "dz-outil-vec-tranche",
  "px-pinceau": "dz-outil-px-pinceau",
  "px-gomme": "dz-outil-px-gomme",
  "px-seau": "dz-outil-px-pot",
  "px-crayon": "dz-outil-px-crayon",
  "px-ligne": "dz-outil-px-ligne",
  "px-rectpx": "dz-outil-px-rectangle",
  "px-selrect": "dz-outil-px-selection",
  "px-lasso": "dz-outil-px-lasso",
  "px-baguette": "dz-outil-px-baguette",
  "px-cloner": "dz-outil-photo-tampon",
  main: "dz-outil-vec-main",
  loupe: "dz-outil-vec-loupe",
  planche: "dz-outil-vec-plan-de-travail",
  degrade: "dz-outil-px-degrade",
  transparence: "dz-outil-vec-transparence",
  cadre: "dz-outil-vec-cadre-texte",
  recadrer: "dz-outil-photo-recadrer",
  "px-flou": "dz-outil-photo-flou",
  "px-eclaircir": "dz-outil-photo-densite-moins",
  "px-assombrir": "dz-outil-photo-densite-plus",
  // les actions de la barre contextuelle (Nœuds / Plume) et les alignements de nœuds
  vif: "dz-outil-vec-noeud-vif",
  lisse: "dz-outil-vec-noeud-lisse",
  intelligent: "dz-outil-vec-noeud-intelligent",
  fractionner: "dz-outil-vec-fractionner",
  ouvrir: "dz-outil-vec-ouvrir-chemin",
  fermer: "dz-outil-vec-fermer-chemin",
  lisserCourbe: "dz-outil-vec-lisser",
  relier: "dz-outil-vec-relier",
  inverser: "dz-edit-inverser-sens",
  "al-gauche": "dz-edit-aligner-gauche",
  "al-centreH": "dz-edit-aligner-centre-h",
  "al-droite": "dz-edit-aligner-droite",
  "al-haut": "dz-edit-aligner-haut",
  "al-centreV": "dz-edit-aligner-centre-v",
  "al-bas": "dz-edit-aligner-bas",
  configDoc: "dz-action-reglages",
  parametres: "dz-action-reglages",
};
// les types de rangées d'objet du panneau Calques (mod-layers : arbre_calques → r.icone) ;
// la rangée de CALQUE montre une vignette, jamais d'icône
export const RANGEES = {
  path: "dz-calque-vectoriel",
  rect: "dz-outil-vec-rectangle",
  ellipse: "dz-outil-vec-ellipse",
  forme: "dz-outil-vec-forme",
  texte: "dz-calque-texte",
  cadre: "dz-calque-texte",
  image: "dz-media-image",
  groupe: "dz-calque-groupe",
  instance: "dz-edit-symbole",
  tuiles: "dz-outil-vec-tuiles",
  ecretage: "dz-calque-ecretage",
  masque: "dz-calque-masque",
  effet: "dz-edit-effet",
};
export const cle_de = (id) => ICONES[id] || REPLI;
export function icone_svg(id, taille = 18) { return dzi(cle_de(id), taille, "ic"); }
export function icone_rangee(id, taille = 14) { return dzi(RANGEES[id] || REPLI, taille, "ic"); }
export const outils_sans_icone = (liste) => (Array.isArray(liste) ? liste : []).filter((id) => !ICONES[id]);
