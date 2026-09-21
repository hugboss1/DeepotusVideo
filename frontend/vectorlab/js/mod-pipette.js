// mod-pipette.js — le Sélecteur de couleur de classe Affinity (21/09/2026),
// feuille PURE : l'échantillon moyen dans un rayon sur une image RGBA, l'hex,
// les champs de la barre contextuelle (Appliquer à la sélection, Loupe,
// Source, Rayon) et la DÉCISION d'un prélèvement selon les modificateurs :
// Ctrl = le style de l'objet visé (l'ancienne pipette), Alt inverse
// « Appliquer », clic droit = le contour. L'UI (mod-pipetteui) rasterise et
// montre la loupe ; ici rien ne touche le DOM.

export const RAYONS_PIPETTE = Object.freeze([
  { id: "0", libelle: "Point (1×1)" }, { id: "1", libelle: "3 × 3" }, { id: "2", libelle: "5 × 5" }, { id: "4", libelle: "9 × 9" },
]);
export const SOURCES_PIPETTE = Object.freeze([{ id: "global", libelle: "Global" }, { id: "calque", libelle: "Calque courant" }]);
export const PIPETTE_DEFAUT = Object.freeze({ appliquer: true, loupe: true, source: "global", rayon: 0 });

/* moyenne des pixels OPAQUES du carré (2r+1)² centré en (x, y), borné à
   l'image ; rend {r, g, b, a, n} (n = pixels opaques comptés, a = 255 si
   n > 0) ; hors image ou image nulle → null */
export function echantillon_rayon(img, x, y, rayon = 0) {
  if (!img || !img.data || !(img.w > 0) || !(img.h > 0)) return null;
  x = Math.floor(x); y = Math.floor(y);
  if (x < 0 || y < 0 || x >= img.w || y >= img.h) return null;
  const r = Math.max(0, Math.floor(+rayon || 0));
  let sr = 0, sg = 0, sb = 0, n = 0;
  for (let j = Math.max(0, y - r); j <= Math.min(img.h - 1, y + r); j++) {
    for (let i = Math.max(0, x - r); i <= Math.min(img.w - 1, x + r); i++) {
      const k = (j * img.w + i) * 4;
      if (img.data[k + 3] === 0) continue;
      sr += img.data[k]; sg += img.data[k + 1]; sb += img.data[k + 2]; n++;
    }
  }
  if (!n) return { r: 0, g: 0, b: 0, a: 0, n: 0 };
  return { r: Math.round(sr / n), g: Math.round(sg / n), b: Math.round(sb / n), a: 255, n };
}

export function hex_de_rgb(r, g, b) {
  const c = (v) => Math.max(0, Math.min(255, Math.round(+v || 0))).toString(16).padStart(2, "0").toUpperCase();
  return "#" + c(r) + c(g) + c(b);
}

export function champs_pipette(etat) {
  const p = { ...PIPETTE_DEFAUT, ...((etat && etat.pipette) || {}) };
  return [
    { id: "pipAppliquer", type: "bascule", libelle: "Appliquer à la sélection", valeur: !!p.appliquer, titre: "La couleur prélevée va au fond de la sélection (clic droit : au contour) — Alt inverse" },
    { id: "pipLoupe", type: "bascule", libelle: "Agrandissement", valeur: !!p.loupe, titre: "La loupe pendant le prélèvement — Maj inverse" },
    { id: "pipSource", type: "select", libelle: "Source", valeur: SOURCES_PIPETTE.some((s) => s.id === p.source) ? p.source : "global", options: SOURCES_PIPETTE.slice() },
    { id: "pipRayon", type: "select", libelle: "Rayon", valeur: RAYONS_PIPETTE.some((s) => s.id === String(p.rayon)) ? String(p.rayon) : "0", options: RAYONS_PIPETTE.slice() },
  ];
}

/* le patch d'état d'un champ pip* : {pipette: {...}} ; champ inconnu → {} */
export function appliquer_pipette(etat, id, valeur) {
  const p = { ...PIPETTE_DEFAUT, ...((etat && etat.pipette) || {}) };
  switch (id) {
    case "pipAppliquer": return { pipette: { ...p, appliquer: valeur === true || valeur === "true" } };
    case "pipLoupe": return { pipette: { ...p, loupe: valeur === true || valeur === "true" } };
    case "pipSource": return { pipette: { ...p, source: SOURCES_PIPETTE.some((s) => s.id === valeur) ? valeur : "global" } };
    case "pipRayon": return { pipette: { ...p, rayon: RAYONS_PIPETTE.some((s) => s.id === String(valeur)) ? +valeur : 0 } };
    default: return {};
  }
}

/* la décision : {action: "style" | "fond" | "contour" | "courant" | "rien", cible} */
export function pipette_decision({ appliquer, alt, ctrl, droit, selection, cible }) {
  if (ctrl) return cible ? { action: "style", cible } : { action: "rien" };
  const app = alt ? !appliquer : !!appliquer;
  if (app && Array.isArray(selection) && selection.length) return { action: droit ? "contour" : "fond" };
  return { action: "courant" };
}
