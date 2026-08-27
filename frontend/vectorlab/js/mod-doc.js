// mod-doc.js — LE modèle-document du Vectorlab : validation + compilation
// JSON -> SVG. PUR (aucune lecture du DOM, aucun état) : la même fonction
// sert l'écran, l'export et le banc qa/ node. Le JSON est la vérité ; le
// SVG n'en est qu'une projection.

const escAttr = (v) => String(v)
  .replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

export function parserDoc(doc) {
  if (!doc || typeof doc !== "object") throw new Error("document: objet requis");
  if (!doc.v) throw new Error("document: champ v requis");
  if (!doc.taille || !(doc.taille.w > 0) || !(doc.taille.h > 0)) {
    throw new Error("document: taille {w,h} positive requise");
  }
  if (!Array.isArray(doc.calques)) throw new Error("document: calques[] requis");
  for (const c of doc.calques) {
    if (!c.id) throw new Error("calque sans id");
    if (!Array.isArray(c.objets)) throw new Error(`calque ${c.id}: objets[] requis`);
  }
  return doc;
}

function styleAttrs(s = {}) {
  const fond = s.fond === undefined ? "none" : s.fond;
  let out = ` fill="${escAttr(fond)}"`;
  if (s.contour && s.contour !== "none") {
    out += ` stroke="${escAttr(s.contour)}"`
        + ` stroke-width="${Number(s.epaisseur || 1)}"`
        + ` stroke-linejoin="round" stroke-linecap="round"`;
  }
  if (s.opacite !== undefined && Number(s.opacite) !== 1) {
    out += ` opacity="${Number(s.opacite)}"`;
  }
  return out;
}

function compilerObjet(o) {
  const t = ` data-objet="${escAttr(o.id)}"`;
  const tr = o.transform ? ` transform="${escAttr(o.transform)}"` : "";
  const st = styleAttrs(o.style);
  switch (o.type) {
    case "rect":
      return `<rect${t} x="${+o.x}" y="${+o.y}" width="${+o.w}"`
           + ` height="${+o.h}"${o.rx ? ` rx="${+o.rx}"` : ""}${st}${tr}/>`;
    case "ellipse":
      return `<ellipse${t} cx="${+o.cx}" cy="${+o.cy}" rx="${+o.rx}"`
           + ` ry="${+o.ry}"${st}${tr}/>`;
    case "path":
      return `<path${t} d="${escAttr(o.d)}"${st}${tr}/>`;
    case "groupe":
      return `<g${t}${st}${tr}>`
           + (o.enfants || []).map(compilerObjet).join("") + `</g>`;
    default:
      // un type inconnu ne casse pas le document : il se voit au commentaire
      return `<!-- objet ${escAttr(o.id)}: type inconnu ${escAttr(o.type)} -->`;
  }
}

export function compilerSVG(doc) {
  parserDoc(doc);
  const w = +doc.taille.w, h = +doc.taille.h;
  const fond = doc.fond
    ? `<rect x="0" y="0" width="${w}" height="${h}"`
      + ` fill="${escAttr(doc.fond)}" data-fond="1"/>`
    : "";
  const calques = doc.calques.map((c) => {
    const cache = c.visible === false ? ` style="display:none"` : "";
    return `<g data-calque="${escAttr(c.id)}"`
         + ` data-nom="${escAttr(c.nom || "")}"${cache}>`
         + c.objets.map(compilerObjet).join("") + `</g>`;
  }).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg"`
       + ` viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">`
       + fond + calques + `</svg>`;
}
