// mod-statut.js — la barre d'état d'Affinity : phrase d'aide (verbes en
// gras, selon l'outil et la sélection), onglet de document, pagination.
// Feuille pure (bancable node) ; l'UI ne fait que poser le HTML.
const VERBES = ["glisser", "cliquer", "double-cliquer", "clic droit", "maj", "alt", "ctrl", "entrée", "échap", "suppr", "entree"];
export function phrase_statut(outil, nSel, hints) {
  if (outil === "select") {
    if (!nSel) return "**Glisser** pour utiliser un cadre de sélection. **Cliquer** sur un objet pour le sélectionner. **Clic droit** pendant la sélection pour activer/désactiver le mode Intersection.";
    return `${nSel} objet${nSel > 1 ? "s" : ""} sélectionné${nSel > 1 ? "s" : ""}. **Glisser** pour déplacer la sélection. **Cliquer** sur un autre objet pour le sélectionner. **Cliquer** sur une zone vide pour annuler la sélection. **Suppr** pour retirer.`;
  }
  const h = (hints || {})[outil];
  if (!h) return "";
  return verbes_gras(h);
}
// les verbes connus en tête de segment (début, après « · », « , » ou « = »)
// passent en gras avec majuscule — la barre d'état ET les bulles riches (R6)
export function verbes_gras(texte) {
  if (!texte) return "";
  return String(texte).replace(/(^|·\s*|,\s*|=\s*)([a-zéè-]+(?: droit)?)/gi, (m, sep, mot) => VERBES.includes(mot.toLowerCase()) ? `${sep}**${mot[0].toUpperCase()}${mot.slice(1)}**` : m);
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
export const statut_html = (s) => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
export function onglet_document(meta, zoom, sale) {
  if (!meta) return "…";
  return `${meta.name} @ ${Math.round((+zoom || 1) * 100)}%${sale ? "*" : ""}`;
}
export function pagination(planches, courante) {
  const liste = Array.isArray(planches) ? planches : [];
  const n = Math.max(1, liste.length);
  const i = liste.findIndex((p) => p && p.id === courante);
  return `${i >= 0 ? i + 1 : 1} sur ${n}`;
}
