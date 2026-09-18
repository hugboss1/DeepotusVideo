// mod-texte.js — l'outil Texte de classe Affinity (R11) : le corps tiré au
// glisser, les champs de style d'un texte pour la barre contextuelle, le
// patch de style borné depuis un champ, le cycle Tab de la sélection.
// Feuille pure ; mod-texteui et mod-barrecontexte traduisent.
export const GRAISSES = [{ id: "normal", nom: "Normal" }, { id: "bold", nom: "Gras" }, { id: "300", nom: "Léger (300)" }, { id: "600", nom: "Demi-gras (600)" }, { id: "800", nom: "Extra-gras (800)" }];
export const ANCRES = [{ id: "start", nom: "Gauche" }, { id: "middle", nom: "Centre" }, { id: "end", nom: "Droite" }];
const borne = (v, min, max, def) => { const n = +v; return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : def; };
// un simple clic (moins de 6 px) garde le corps courant ; un glisser donne le corps par sa hauteur (≥ 8)
export function corps_de_glisser(x0, y0, x1, y1, corpsCourant) {
  const h = Math.abs(y1 - y0), w = Math.abs(x1 - x0);
  if (Math.hypot(w, h) < 6) return corpsCourant;
  return Math.max(8, Math.round(h));
}
export function champs_texte(style, polices) {
  const s = style || {}, liste = Array.isArray(polices) ? polices : [];
  const p = liste.find((x) => x.famille === s.police) || liste[0] || null;
  return [
    { id: "txPolice", type: "select", libelle: "Police", valeur: p ? p.id : "", options: liste.map((x) => ({ id: x.id, libelle: x.famille })) },
    { id: "txCorps", type: "number", libelle: "Corps", valeur: borne(s.corps, 1, 500, 16), min: 1, max: 500, pas: 1 },
    { id: "txGraisse", type: "select", libelle: "Graisse", valeur: GRAISSES.some((g) => g.id === String(s.graisse)) ? String(s.graisse) : "normal", options: GRAISSES.map((g) => ({ id: g.id, libelle: g.nom })) },
    { id: "txItalique", type: "bascule", libelle: "Italique", valeur: s.italique === true },
    { id: "txSouligne", type: "bascule", libelle: "Souligné", valeur: s.souligne === true },
    { id: "txAncre", type: "select", libelle: "Alignement", valeur: ANCRES.some((a) => a.id === s.ancre) ? s.ancre : "start", options: ANCRES.map((a) => ({ id: a.id, libelle: a.nom })) },
    { id: "txInterligne", type: "number", libelle: "Interligne", valeur: borne(s.interligne, 0.5, 4, 1.2), min: 0.5, max: 4, pas: 0.1 },
    { id: "txInterlettrage", type: "number", libelle: "Approche", valeur: borne(s.interlettrage, -20, 100, 0), min: -20, max: 100, pas: 0.5 },
  ];
}
const bool = (v) => v === true || v === "true" || v === 1;
export function patch_texte(id, valeur, polices) {
  switch (id) {
    case "txPolice": { const p = (polices || []).find((x) => x.id === valeur); return p ? { police: p.famille } : {}; }
    case "txCorps": return { corps: borne(valeur, 1, 500, 16) };
    case "txGraisse": return { graisse: GRAISSES.some((g) => g.id === String(valeur)) ? String(valeur) : "normal" };
    case "txItalique": return { italique: bool(valeur) };
    case "txSouligne": return { souligne: bool(valeur) };
    case "txAncre": return { ancre: ANCRES.some((a) => a.id === valeur) ? valeur : "start" };
    case "txInterligne": return { interligne: borne(valeur, 0.5, 4, 1.2) };
    case "txInterlettrage": return { interlettrage: borne(valeur, -20, 100, 0) };
    default: return {};
  }
}
export function cycle_suivant(ids, courant, sens = 1) {
  if (!Array.isArray(ids) || !ids.length) return null;
  const i = ids.indexOf(courant);
  if (i < 0) return sens >= 0 ? ids[0] : ids[ids.length - 1];
  return ids[(i + (sens >= 0 ? 1 : -1) + ids.length) % ids.length];
}
