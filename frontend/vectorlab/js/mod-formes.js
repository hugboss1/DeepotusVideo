// mod-formes.js — les FORMES PARAMÉTRIQUES du lot B (D2) : polygone (dont
// l'hexagone), étoile, engrenage, flèche, donut, spirale. L'objet garde ses
// paramètres ; le `d` se RECALCULE à la compilation (jamais stocké) ;
// `sx/sy` portent un redimensionnement non uniforme. Poignées de
// paramètres pour l'écran. Module FEUILLE : aucun import, aucun DOM ; le d
// sort déjà canonique (2 décimales, M/L/C/Z absolus).
export const FORMES = [
  { id: "polygone", nom: "Polygone" },
  { id: "hexagone", nom: "Hexagone" },
  { id: "etoile", nom: "Étoile" },
  { id: "engrenage", nom: "Engrenage" },
  { id: "fleche", nom: "Flèche" },
  { id: "donut", nom: "Donut" },
  { id: "spirale", nom: "Spirale" },
];
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);
const K = 0.5522847498;                       // cercle en 4 cubiques
const PHI = (1 + Math.sqrt(5)) / 2;

export function forme_defaut(nom, cx, cy, r) {
  const style = { fond: "#9DB4D6", contour: "#1F1512", epaisseur: 2 };
  const base = { type: "forme", forme: nom, cx: +cx, cy: +cy, r: +r, style };
  switch (nom) {
    case "hexagone": return { ...base, forme: "polygone", params: { n: 6 } };
    case "polygone": return { ...base, params: { n: 6 } };
    case "etoile": return { ...base, params: { n: 5, ratio: 0.5 } };
    case "engrenage": return { ...base, params: { dents: 12, profondeur: Math.max(1, r * 0.2) } };
    case "fleche": return { ...base, params: { longueur: 2 * r, largeur: r * 0.4, tete: r * 0.8 } };
    case "donut": return { ...base, params: { ratio: 0.5 }, style: { ...style, regle: "evenodd" } };
    case "spirale": return { ...base, params: { tours: 3, type: "lineaire" },
                             style: { fond: "none", contour: "#1F1512", epaisseur: 2 } };
    default: throw new Error(`forme inconnue : ${nom}`);
  }
}

export function forme_params_valider(nom, p) {
  if (!p || typeof p !== "object") throw new Error("forme : params requis");
  const ent = (v, min) => Number.isInteger(v) && v >= min;
  switch (nom) {
    case "polygone": if (!ent(p.n, 3)) throw new Error("polygone : n entier ≥ 3"); break;
    case "etoile":
      if (!ent(p.n, 3)) throw new Error("étoile : n entier ≥ 3");
      if (!(p.ratio > 0 && p.ratio < 1)) throw new Error("étoile : ratio dans ]0, 1[");
      break;
    case "engrenage":
      if (!ent(p.dents, 3)) throw new Error("engrenage : dents entier ≥ 3");
      if (!(p.profondeur > 0)) throw new Error("engrenage : profondeur > 0");
      break;
    case "fleche":
      if (!(p.longueur > 0 && p.largeur > 0 && p.tete > 0)) throw new Error("flèche : longueur, largeur, tête > 0");
      break;
    case "donut": if (!(p.ratio > 0 && p.ratio < 1)) throw new Error("donut : ratio dans ]0, 1["); break;
    case "spirale":
      if (!(p.tours > 0)) throw new Error("spirale : tours > 0");
      if (p.type !== undefined && !["lineaire", "fibonacci"].includes(p.type)) throw new Error("spirale : type lineaire|fibonacci");
      break;
    default: throw new Error(`forme inconnue : ${nom}`);
  }
  return p;
}

function _cercle(cx, cy, rx, ry) {
  const kx = rx * K, ky = ry * K;
  return `M ${nbc(cx)} ${nbc(cy - ry)}`
    + ` C ${nbc(cx + kx)} ${nbc(cy - ry)} ${nbc(cx + rx)} ${nbc(cy - ky)} ${nbc(cx + rx)} ${nbc(cy)}`
    + ` C ${nbc(cx + rx)} ${nbc(cy + ky)} ${nbc(cx + kx)} ${nbc(cy + ry)} ${nbc(cx)} ${nbc(cy + ry)}`
    + ` C ${nbc(cx - kx)} ${nbc(cy + ry)} ${nbc(cx - rx)} ${nbc(cy + ky)} ${nbc(cx - rx)} ${nbc(cy)}`
    + ` C ${nbc(cx - rx)} ${nbc(cy - ky)} ${nbc(cx - kx)} ${nbc(cy - ry)} ${nbc(cx)} ${nbc(cy - ry)} Z`;
}

export function forme_d(o) {
  if (!(o.r > 0)) throw new Error("forme : rayon > 0 requis");
  const p = forme_params_valider(o.forme, o.params);
  const sx = o.sx || 1, sy = o.sy || 1;
  const P = (x, y) => `${nbc(o.cx + x * sx)} ${nbc(o.cy + y * sy)}`;
  const polaire = (r, a) => [r * Math.cos(a), r * Math.sin(a)];
  const ferme = (pts) => "M " + pts.map(([x, y]) => P(x, y)).join(" L ") + " Z";
  const a0 = -Math.PI / 2;
  switch (o.forme) {
    case "polygone": {
      const pts = [];
      for (let k = 0; k < p.n; k++) pts.push(polaire(o.r, a0 + 2 * Math.PI * k / p.n));
      return ferme(pts);
    }
    case "etoile": {
      const pts = [];
      for (let k = 0; k < 2 * p.n; k++) pts.push(polaire(k % 2 ? o.r * p.ratio : o.r, a0 + Math.PI * k / p.n));
      return ferme(pts);
    }
    case "engrenage": {
      const pts = [], ri = Math.max(0.5, o.r - p.profondeur), q = 2 * Math.PI / (4 * p.dents);
      for (let k = 0; k < p.dents; k++) {
        const a = a0 + 2 * Math.PI * k / p.dents;
        pts.push(polaire(ri, a), polaire(o.r, a + q), polaire(o.r, a + 2 * q), polaire(ri, a + 3 * q));
      }
      return ferme(pts);
    }
    case "fleche": {
      const L = p.longueur, w = p.largeur, t = p.tete, hd = Math.min(t, L * 0.9);
      return ferme([[-L / 2, -w / 2], [L / 2 - hd, -w / 2], [L / 2 - hd, -t / 2], [L / 2, 0],
                    [L / 2 - hd, t / 2], [L / 2 - hd, w / 2], [-L / 2, w / 2]]);
    }
    case "donut":
      return _cercle(o.cx, o.cy, o.r * sx, o.r * sy) + " " + _cercle(o.cx, o.cy, o.r * p.ratio * sx, o.r * p.ratio * sy);
    case "spirale": {
      const n = Math.max(8, Math.round(p.tours * 36));
      const thetaMax = 2 * Math.PI * p.tours;
      const b = Math.log(PHI) / (Math.PI / 2);
      const pts = [];
      for (let k = 0; k <= n; k++) {
        const t = k / n, theta = thetaMax * t;
        const rad = p.type === "fibonacci" ? o.r * Math.exp(b * (theta - thetaMax)) : o.r * t;
        pts.push(polaire(rad, a0 + theta));
      }
      if (p.type !== "fibonacci") pts[0] = [0, 0];
      return "M " + pts.map(([x, y]) => P(x, y)).join(" L ");
    }
    default: throw new Error(`forme inconnue : ${o.forme}`);
  }
}

/* ── poignées de paramètres : rayon (en haut) + celle propre à la forme ── */
export function forme_poignees(o) {
  const sx = o.sx || 1, sy = o.sy || 1, p = o.params || {};
  const at = (cle, r, a) => ({ cle, x: o.cx + r * Math.cos(a) * sx, y: o.cy + r * Math.sin(a) * sy });
  const out = [at("r", o.r, -Math.PI / 2)];
  if (o.forme === "etoile") out.push(at("ratio", o.r * p.ratio, -Math.PI / 2 + Math.PI / p.n));
  if (o.forme === "donut") out.push(at("ratio", o.r * p.ratio, Math.PI / 2));
  if (o.forme === "engrenage") out.push(at("profondeur", o.r - p.profondeur, Math.PI / 2));
  if (o.forme === "fleche") out.push({ cle: "tete", x: o.cx + (p.longueur / 2 - p.tete) * sx, y: o.cy + p.tete / 2 * sy });
  return out;
}
export function forme_poignee_deplacer(o, cle, x, y) {
  const sx = o.sx || 1, sy = o.sy || 1;
  const dist = Math.hypot((x - o.cx) / sx, (y - o.cy) / sy);
  switch (cle) {
    case "r": return { r: Math.max(1, Math.round(dist * 100) / 100) };
    case "ratio": return { params: { ...o.params, ratio: Math.min(0.95, Math.max(0.05, Math.round(dist / o.r * 1000) / 1000)) } };
    case "profondeur": return { params: { ...o.params, profondeur: Math.min(o.r - 1, Math.max(1, Math.round((o.r - dist) * 100) / 100)) } };
    case "tete": return { params: { ...o.params, tete: Math.max(1, Math.round(2 * Math.abs((y - o.cy) / sy) * 100) / 100) } };
    default: throw new Error(`poignée inconnue : ${cle}`);
  }
}
