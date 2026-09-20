// mod-theme.js — les jetons du thème Affinity (R4) : la table des
// couleurs, le bloc :root qu'elle produit, et la liste des hex de
// l'ancienne palette bleu-nuit que le banc-garde refuse dans
// vectorlab.css (hors commentaires). Feuille pure.
export const TOKENS = Object.freeze({
  fond: "#2b2b2b", barre: "#232323", canevas: "#262626", bord: "#3a3a3a",
  texte: "#d0d0d0", muet: "#9a9a9a", sel: "#2b6fd6", cyan: "#22c3d8",
  violet: "#cf6fe3", menu: "#1e1e1e", champ: "#1f1f1f",
});
export const theme_css = () => `:root { ${Object.entries(TOKENS).map(([k, v]) => `--aff-${k}: ${v};`).join(" ")} }`;
export const LEGACY = Object.freeze([
  "#171a20", "#232833", "#313847", "#2c4a75", "#191d23", "#14171d", "#14171c", "#8b93a0", "#d6d9de", "#101216",
  "#262b34", "#20242d", "#1c2028", "#3a4150", "#1b2028", "#333b49", "#5b82b8", "#3c5f92", "#20293a", "#eef1f5",
  "#9db4d6", "#2b3140", "#35588a", "#1f2530", "#0d1015", "#12161a", "#1a1e26", "#2c323d", "#9aa3b2", "#e2e6ec",
  "#97a0ae", "#cfd6e2", "#1c2129", "#222731", "#2a303b", "#16191f", "#5f6873", "#9aa4ae", "#b6bec9", "#e6e9ee",
  "#f2f4f7", "#cfe0f5",
]);
export function hex_herites(css) {
  if (!css) return [];
  const sans = String(css).replace(/\/\*[\s\S]*?\*\//g, "");
  const trouves = (sans.match(/#[0-9a-fA-F]{6}\b/g) || []).map((h) => h.toLowerCase());
  return trouves.filter((h) => LEGACY.includes(h));
}
