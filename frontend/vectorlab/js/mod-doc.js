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

/* ── chemins (T1.1) : le d de path, parsé, structuré, canonisé ──
   Segments {c:"M"|"L"|"C"|"Q"|"Z", p:[nombres]} en ABSOLU seulement (v1) ;
   lecture tolérante (virgules, implicites SVG), écriture canonique stable
   à l'octet — les opérations de nœuds et les booléens s'appuient dessus. */
const ARITE = { M: 2, L: 2, C: 6, Q: 4, Z: 0 };

// arrondi 2 décimales SANS le piège flottant (1.005 → 1.01, 3.10 → 3.1)
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);

export function chemin_parser(d) {
  const src = String(d ?? "").replace(/,/g, " ").trim();
  const jetons = src.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?/g) || [];
  const segs = [];
  let i = 0, cmd = null;
  while (i < jetons.length) {
    const t = jetons[i];
    if (/^[A-Za-z]$/.test(t)) {
      if (!(t in ARITE)) {
        if (t.toUpperCase() in ARITE) {
          throw new Error(`chemin: commande relative '${t}' non supportée `
                          + "(v1: M/L/C/Q/Z absolus)");
        }
        throw new Error(`chemin: commande inconnue '${t}'`);
      }
      cmd = t;
      i++;
      if (cmd === "Z") { segs.push({ c: "Z", p: [] }); cmd = null; }
      continue;
    }
    if (cmd === null) throw new Error("chemin: nombre sans commande");
    const p = [];
    for (let k = 0; k < ARITE[cmd]; k++, i++) {
      if (i >= jetons.length || /^[A-Za-z]$/.test(jetons[i])) {
        throw new Error(`chemin: arité de ${cmd} incomplète`);
      }
      p.push(Number(jetons[i]));
    }
    segs.push({ c: cmd, p });
    if (cmd === "M") cmd = "L";     // implicite SVG : paires après M = L
  }
  return segs;
}

export function chemin_serialiser(segs) {
  return segs.map((s) => s.c === "Z" ? "Z"
                       : s.c + " " + s.p.map(nbc).join(" ")).join(" ");
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
