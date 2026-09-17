// mod-pinceauvec.js — le pinceau vectoriel à profil (lot F) : un trait
// (liste de points) devient un CHEMIN FERMÉ rempli dont la demi-largeur
// suit un profil le long du trait — plat (constante), fuseau (nulle aux
// bouts, pleine au milieu), calligraphie (plume d'angle FIXE : l'offset ne
// suit pas la normale mais la direction de la plume). Module FEUILLE.

export const PROFILS = [
  { id: "plat", libelle: "Plat" },
  { id: "fuseau", libelle: "Fuseau" },
  { id: "calligraphie", libelle: "Calligraphie" },
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
  if (!Array.isArray(points) || points.length < 2) throw new Error("trait : deux points au moins");
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
