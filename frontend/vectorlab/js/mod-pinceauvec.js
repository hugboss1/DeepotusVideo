// mod-pinceauvec.js — le pinceau vectoriel à profil (lot F) : un trait
// (liste de points) devient un CHEMIN FERMÉ rempli dont la demi-largeur
// suit un profil le long du trait — plat (constante), fuseau (nulle aux
// bouts, pleine au milieu), calligraphie (plume d'angle FIXE : l'offset ne
// suit pas la normale mais la direction de la plume). Module FEUILLE.

// t146 (traduction L6) : T(clé, vars) de cette feuille — dzT du runtime dans la page ; sous node, le français des dictionnaires (frontend/shared/i18n)
const T = (cle, vars) => { const g = globalThis, w = g.window; if (w && typeof w.dzT === "function") return w.dzT(cle, vars); if (typeof g.dzT === "function") return g.dzT(cle, vars); if (!g.__vlFr && g.process && g.process.getBuiltinModule) { const fs = g.process.getBuiltinModule("fs"), u = new URL("../../shared/i18n/", import.meta.url); g.__vlFr = {}; for (const n of fs.readdirSync(u).filter((x) => x.endsWith(".json")).sort()) Object.assign(g.__vlFr, JSON.parse(fs.readFileSync(new URL(n, u), "utf8"))); } const e = g.__vlFr && g.__vlFr[cle]; if (!e) return cle; return vars ? e.fr.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m)) : e.fr; };
export const PROFILS = [
  { id: "plat", libelle: T("vectorlab.divers.profil_plat") },
  { id: "fuseau", libelle: T("vectorlab.divers.profil_fuseau") },
  { id: "calligraphie", libelle: T("vectorlab.divers.profil_calligraphie") },
];
export function profil(nom, t) {
  switch (nom) {
    case "plat": case "calligraphie": return 1;
    case "fuseau": return Math.sin(Math.PI * Math.min(1, Math.max(0, t)));
    default: throw new Error(`profil inconnu : ${nom}`);
  }
}
const _n = (v) => String(Math.round(v * 100) / 100 + 0);   // « -0 » → 0

export function trait_profil(points, { largeur = 8, profil: nomProfil = "fuseau", angle = 45 } = {}) {
  if (!Array.isArray(points) || points.length < 2) throw new Error(T("vectorlab.divers.err_trait"));
  profil(nomProfil, 0);
  const pts = points.map(([x, y]) => [+x, +y]);
  // abscisse curviligne normalisée
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const L = cum[cum.length - 1] || 1;
  const plume = [Math.cos(angle * Math.PI / 180), Math.sin(angle * Math.PI / 180)];
  const gauche = [], droite = [];
  for (let i = 0; i < pts.length; i++) {
    // tangente : vers le voisin suivant, sinon le précédent ; doublon → on cherche plus loin
    let j = i + 1;
    while (j < pts.length && pts[j][0] === pts[i][0] && pts[j][1] === pts[i][1]) j++;
    let tx, ty;
    if (j < pts.length) { tx = pts[j][0] - pts[i][0]; ty = pts[j][1] - pts[i][1]; }
    else {
      let k = i - 1;
      while (k >= 0 && pts[k][0] === pts[i][0] && pts[k][1] === pts[i][1]) k--;
      if (k < 0) { tx = 1; ty = 0; } else { tx = pts[i][0] - pts[k][0]; ty = pts[i][1] - pts[k][1]; }
    }
    const n = Math.hypot(tx, ty) || 1;
    const hw = largeur / 2 * profil(nomProfil, cum[i] / L);
    const [ox, oy] = nomProfil === "calligraphie" ? plume : [-ty / n, tx / n];
    gauche.push([pts[i][0] + ox * hw, pts[i][1] + oy * hw]);
    droite.push([pts[i][0] - ox * hw, pts[i][1] - oy * hw]);
  }
  const tour = gauche.concat(droite.reverse());
  return "M " + tour.map(([x, y]) => `${_n(x)} ${_n(y)}`).join(" L ") + " Z";
}
