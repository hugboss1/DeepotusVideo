// mod-importsvg.js — lot D4 « Interop », T1 (t469 ; plan 2026-11-09-vectorlab-d4-import.md) : LIRE un SVG en objets
// du Vectorlab (rect, ellipse, path, texte, image data:, groupe). Pur : les bancs tournent sous node, sans DOMParser,
// d'où un lecteur XML minimal. Les chemins sont normalisés en absolu M L C Q Z (relatifs, H V, S T et arcs convertis) ;
// les styles viennent des attributs, de style="" et des règles simples d'une balise <style>, avec l'héritage ; les
// transforms SVG restent des chaînes (le modèle les lit, cf. _matriceDe de mod-bool). Ce qui n'entre pas est COMPTÉ
// par raison dans `stats.ignores` : l'interface le dit (T2).
import { T } from "./mod-i18n.js";
import { op_ajouter } from "./mod-doc.js";

const ELEMENTS_MAX = 50000;
const nb = (x) => String(Math.round(x * 1e4) / 1e4 + 0);

/* ── lecteur XML ── */
const ENTITES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
function _entites(s) {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|\w+);/g, (m, e) => {
    if (e[0] === "#") {
      const n = e[1] === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(n) && n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : m;
    }
    return ENTITES[e] !== undefined ? ENTITES[e] : m;
  });
}

/* xml_lire(texte) → { nom, attrs, enfants (éléments), noeuds (textes et éléments, dans l'ordre), texte (textes directs) } */
export function xml_lire(texte) {
  const s = String(texte || "");
  const refus = () => new Error(T("vectorlab.importer.xml_invalide"));
  let i = 0, racine = null, compte = 0;
  const pile = [];
  const nouveauTexte = (t) => {
    if (!pile.length) { if (t.trim()) throw refus(); return; }
    const p = pile[pile.length - 1];
    p.noeuds.push(t);
    p.texte += t;
  };
  while (i < s.length) {
    const lt = s.indexOf("<", i);
    if (lt < 0) { nouveauTexte(_entites(s.slice(i))); break; }
    if (lt > i) nouveauTexte(_entites(s.slice(i, lt)));
    if (s.startsWith("<!--", lt)) {
      const f = s.indexOf("-->", lt + 4);
      if (f < 0) throw refus();
      i = f + 3;
    } else if (s.startsWith("<![CDATA[", lt)) {
      const f = s.indexOf("]]>", lt + 9);
      if (f < 0) throw refus();
      nouveauTexte(s.slice(lt + 9, f));
      i = f + 3;
    } else if (s.startsWith("<?", lt)) {
      const f = s.indexOf("?>", lt + 2);
      if (f < 0) throw refus();
      i = f + 2;
    } else if (s.startsWith("<!", lt)) {                        // DOCTYPE, avec son sous-ensemble [ … ]
      let j = lt + 2, prof = 0;
      for (; j < s.length; j++) {
        if (s[j] === "[") prof++;
        else if (s[j] === "]") prof--;
        else if (s[j] === ">" && prof <= 0) break;
      }
      if (j >= s.length) throw refus();
      i = j + 1;
    } else if (s[lt + 1] === "/") {
      const f = s.indexOf(">", lt);
      if (f < 0) throw refus();
      const nom = s.slice(lt + 2, f).trim();
      const el = pile.pop();
      if (!el || el.nom !== nom) throw refus();
      i = f + 1;
    } else {
      const m = /^<([A-Za-z_][\w.:-]*)/.exec(s.slice(lt, lt + 200));
      if (!m) throw refus();
      const el = { nom: m[1], attrs: {}, enfants: [], noeuds: [], texte: "" };
      if (++compte > ELEMENTS_MAX) throw new Error(T("vectorlab.importer.trop_grand", { n: ELEMENTS_MAX }));
      let j = lt + m[0].length, vide = false;
      for (;;) {
        while (j < s.length && /\s/.test(s[j])) j++;
        if (j >= s.length) throw refus();
        if (s[j] === ">") { j++; break; }
        if (s[j] === "/" && s[j + 1] === ">") { j += 2; vide = true; break; }
        const a = /^([A-Za-z_][\w.:-]*)\s*=\s*("([^"]*)"|'([^']*)')/.exec(s.slice(j, j + 100000));
        if (!a) throw refus();
        el.attrs[a[1]] = _entites(a[3] !== undefined ? a[3] : a[4]);
        j += a[0].length;
      }
      if (pile.length) {
        const p = pile[pile.length - 1];
        p.enfants.push(el);
        p.noeuds.push(el);
      } else if (racine) throw refus();
      else racine = el;
      if (!vide) pile.push(el);
      i = j;
    }
  }
  if (!racine || pile.length) throw refus();
  return racine;
}

/* ── chemins ── */
function _lecteur(d) {
  let i = 0;
  const refus = () => new Error(T("vectorlab.importer.chemin_invalide"));
  const blancs = () => { while (i < d.length && /[\s,]/.test(d[i])) i++; };
  return {
    fin() { blancs(); return i >= d.length; },
    commande() {
      blancs();
      if (/[MmZzLlHhVvCcSsQqTtAa]/.test(d[i] || "")) return d[i++];
      return null;
    },
    nombreSuit() { blancs(); return /[-+.\d]/.test(d[i] || ""); },
    nombre() {
      blancs();
      const m = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/.exec(d.slice(i, i + 64));
      if (!m) throw refus();
      i += m[0].length;
      return Number(m[0]);
    },
    drapeau() {
      blancs();
      if (d[i] === "0" || d[i] === "1") return d[i++] === "1";
      throw refus();
    },
    refus,
  };
}

/* un arc SVG (point courant → x, y) en cubiques, chaque morceau ≤ 90° (SVG 1.1, annexe F.6) */
function _arc_cubiques(x0, y0, rx, ry, phi, grand, balayage, x, y) {
  if (x0 === x && y0 === y) return [];
  rx = Math.abs(rx); ry = Math.abs(ry);
  if (!rx || !ry) return null;                                 // rayon nul : une ligne
  const cp = Math.cos(phi), sp = Math.sin(phi);
  const dx = (x0 - x) / 2, dy = (y0 - y) / 2;
  const x1 = cp * dx + sp * dy, y1 = -sp * dx + cp * dy;
  const l = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
  if (l > 1) { rx *= Math.sqrt(l); ry *= Math.sqrt(l); }       // trop petit : rayons agrandis
  const num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
  let k = Math.sqrt(Math.max(0, num / (rx * rx * y1 * y1 + ry * ry * x1 * x1)));
  if (grand === balayage) k = -k;
  const cx1 = k * rx * y1 / ry, cy1 = -k * ry * x1 / rx;
  const cx = cp * cx1 - sp * cy1 + (x0 + x) / 2, cy = sp * cx1 + cp * cy1 + (y0 + y) / 2;
  const angle = (ux, uy, vx, vy) => {
    const a = Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
    return a;
  };
  const t1 = angle(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry);
  let dt = angle((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry);
  if (!balayage && dt > 0) dt -= 2 * Math.PI;
  else if (balayage && dt < 0) dt += 2 * Math.PI;
  const n = Math.max(1, Math.ceil(Math.abs(dt) / (Math.PI / 2) - 1e-9));
  const pas = dt / n, a = 4 / 3 * Math.tan(pas / 4);
  const pt = (t) => [cx + rx * Math.cos(t) * cp - ry * Math.sin(t) * sp, cy + rx * Math.cos(t) * sp + ry * Math.sin(t) * cp];
  const de = (t) => [-rx * Math.sin(t) * cp - ry * Math.cos(t) * sp, -rx * Math.sin(t) * sp + ry * Math.cos(t) * cp];
  const out = [];
  for (let s = 0; s < n; s++) {
    const ta = t1 + s * pas, tb = ta + pas;
    const pa = pt(ta), pb = pt(tb), da = de(ta), db = de(tb);
    out.push([pa[0] + a * da[0], pa[1] + a * da[1], pb[0] - a * db[0], pb[1] - a * db[1], pb[0], pb[1]]);
  }
  return out;
}

/* chemin_normaliser(d) → d absolu en M L C Q Z seulement */
export function chemin_normaliser(d) {
  const L = _lecteur(String(d || ""));
  const out = [];
  let cx = 0, cy = 0, sx = 0, sy = 0, cmd = null, prec = null, ctrl = null;
  while (!L.fin()) {
    const c = L.commande();
    if (c) cmd = c;
    else if (!cmd || !L.nombreSuit()) throw L.refus();
    const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase();
    const ox = rel ? cx : 0, oy = rel ? cy : 0;
    if (C === "Z") {
      out.push("Z"); cx = sx; cy = sy; prec = "Z"; ctrl = null;
      if (!c) throw L.refus();
      continue;
    }
    if (C === "M") {
      const x = ox + L.nombre(), y = oy + L.nombre();
      out.push(`M${nb(x)} ${nb(y)}`);
      cx = sx = x; cy = sy = y; prec = "M"; ctrl = null;
      cmd = rel ? "l" : "L";                                   // paires suivantes : des lignes
      continue;
    }
    if (C === "L" || C === "H" || C === "V") {
      const x = C === "V" ? cx : ox + L.nombre();
      const y = C === "H" ? cy : (C === "V" ? oy : oy) + L.nombre();
      out.push(`L${nb(x)} ${nb(y)}`);
      cx = x; cy = y; prec = "L"; ctrl = null;
    } else if (C === "C" || C === "S") {
      let x1, y1;
      if (C === "S") {
        [x1, y1] = prec === "C" && ctrl ? [2 * cx - ctrl[0], 2 * cy - ctrl[1]] : [cx, cy];
      } else { x1 = ox + L.nombre(); y1 = oy + L.nombre(); }
      const x2 = ox + L.nombre(), y2 = oy + L.nombre(), x = ox + L.nombre(), y = oy + L.nombre();
      out.push(`C${nb(x1)} ${nb(y1)} ${nb(x2)} ${nb(y2)} ${nb(x)} ${nb(y)}`);
      cx = x; cy = y; prec = "C"; ctrl = [x2, y2];
    } else if (C === "Q" || C === "T") {
      let x1, y1;
      if (C === "T") {
        [x1, y1] = prec === "Q" && ctrl ? [2 * cx - ctrl[0], 2 * cy - ctrl[1]] : [cx, cy];
      } else { x1 = ox + L.nombre(); y1 = oy + L.nombre(); }
      const x = ox + L.nombre(), y = oy + L.nombre();
      out.push(`Q${nb(x1)} ${nb(y1)} ${nb(x)} ${nb(y)}`);
      cx = x; cy = y; prec = "Q"; ctrl = [x1, y1];
    } else {                                                   // A
      const rx = L.nombre(), ry = L.nombre(), rot = L.nombre(), grand = L.drapeau(), bal = L.drapeau();
      const x = ox + L.nombre(), y = oy + L.nombre();
      const morceaux = _arc_cubiques(cx, cy, rx, ry, rot * Math.PI / 180, grand, bal, x, y);
      if (morceaux === null) out.push(`L${nb(x)} ${nb(y)}`);
      else for (const m of morceaux) out.push("C" + m.map(nb).join(" "));
      cx = x; cy = y; prec = "A"; ctrl = null;
    }
  }
  return out.join(" ");
}

/* ── couleurs ── */
const NOMS = {
  black: "#000000", white: "#ffffff", red: "#ff0000", green: "#008000", blue: "#0000ff", yellow: "#ffff00",
  cyan: "#00ffff", aqua: "#00ffff", magenta: "#ff00ff", fuchsia: "#ff00ff", gray: "#808080", grey: "#808080",
  silver: "#c0c0c0", maroon: "#800000", olive: "#808000", lime: "#00ff00", teal: "#008080", navy: "#000080",
  purple: "#800080", orange: "#ffa500", pink: "#ffc0cb", brown: "#a52a2a", gold: "#ffd700", indigo: "#4b0082",
  violet: "#ee82ee", coral: "#ff7f50", salmon: "#fa8072", tomato: "#ff6347", crimson: "#dc143c", khaki: "#f0e68c",
  beige: "#f5f5dc", ivory: "#fffff0", lavender: "#e6e6fa", turquoise: "#40e0d0", tan: "#d2b48c", chocolate: "#d2691e",
  darkgray: "#a9a9a9", darkgrey: "#a9a9a9", lightgray: "#d3d3d3", lightgrey: "#d3d3d3", darkblue: "#00008b",
  darkred: "#8b0000", darkgreen: "#006400", lightblue: "#add8e6", skyblue: "#87ceeb", steelblue: "#4682b4",
};
const hex2 = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0");

/* → { c: "#rrggbb" | "none" | "currentColor" | "url(#id)", a: alpha } ou null (illisible) */
function _couleur(v) {
  v = String(v).trim();
  const bas = v.toLowerCase();
  if (bas === "none" || bas === "transparent") return { c: "none", a: 1 };
  if (bas === "currentcolor") return { c: "currentColor", a: 1 };
  if (bas.startsWith("url(")) return { c: v, a: 1 };
  let m = /^#([0-9a-f]{3,8})$/i.exec(v);
  if (m) {
    let h = m[1].toLowerCase();
    if (h.length === 3 || h.length === 4) h = h.split("").map((x) => x + x).join("");
    if (h.length === 6) return { c: "#" + h, a: 1 };
    if (h.length === 8) return { c: "#" + h.slice(0, 6), a: parseInt(h.slice(6), 16) / 255 };
    return null;
  }
  m = /^rgba?\(([^)]*)\)$/i.exec(v);
  if (m) {
    const p = m[1].split(/[\s,/]+/).filter(Boolean);
    if (p.length < 3) return null;
    const val = (x) => (x.endsWith("%") ? parseFloat(x) * 2.55 : parseFloat(x));
    const a = p[3] === undefined ? 1 : (p[3].endsWith("%") ? parseFloat(p[3]) / 100 : parseFloat(p[3]));
    if ([0, 1, 2].some((k) => !Number.isFinite(val(p[k])))) return null;
    return { c: "#" + hex2(val(p[0])) + hex2(val(p[1])) + hex2(val(p[2])), a: Number.isFinite(a) ? a : 1 };
  }
  return NOMS[bas] ? { c: NOMS[bas], a: 1 } : null;
}

/* ── longueurs ── */
const UNITES = { px: 1, mm: 96 / 25.4, cm: 96 / 2.54, in: 96, pt: 96 / 72, pc: 16, em: 16, ex: 8 };
function _longueur(v, ref = 0) {
  if (v === undefined || v === null) return null;
  const m = /^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-z%]*)\s*$/i.exec(String(v));
  if (!m) return null;
  const n = Number(m[1]), u = m[2].toLowerCase();
  if (u === "%") return ref ? n * ref / 100 : null;
  return u === "" ? n : (UNITES[u] ? n * UNITES[u] : null);
}
const _nombres = (s) => (String(s || "").match(/[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/g) || []).map(Number);

/* ── styles ── */
const HERITES = new Set(["fill", "stroke", "stroke-width", "stroke-dasharray", "fill-opacity", "stroke-opacity", "color",
  "font-family", "font-size", "font-weight", "font-style", "text-anchor", "visibility", "letter-spacing", "fill-rule",
  "stroke-linejoin"]);
const PROPRIETES = new Set([...HERITES, "opacity", "display", "filter", "clip-path", "mask", "stop-color"]);

function _declarations(txt) {
  const out = {};
  for (const d of String(txt || "").split(";")) {
    const k = d.indexOf(":");
    if (k < 0) continue;
    const nom = d.slice(0, k).trim().toLowerCase();
    const val = d.slice(k + 1).replace(/!important/i, "").trim();
    if (nom && val) out[nom] = val;
  }
  return out;
}

/* règles simples d'une feuille : sélecteurs « tag », « .classe », « #id », « tag.classe » (les autres sont ignorés) */
function _regles(css) {
  const regles = [];
  const propre = String(css || "").replace(/\/\*[\s\S]*?\*\//g, "");
  const re = /([^{}]+)\{([^{}]*)\}/g;
  let m, ordre = 0;
  while ((m = re.exec(propre))) {
    const decl = _declarations(m[2]);
    for (const sel of m[1].split(",")) {
      const s = sel.trim();
      const p = /^([A-Za-z][\w-]*)?(?:([.#])([\w-]+))?$/.exec(s);
      if (!s || !p || (!p[1] && !p[2])) continue;
      const spec = p[2] === "#" ? 100 : (p[2] ? 10 : 0) + (p[1] ? 1 : 0);
      regles.push({ tag: p[1] || null, classe: p[2] === "." ? p[3] : null, id: p[2] === "#" ? p[3] : null, spec, ordre: ordre++, decl });
    }
  }
  return regles.sort((a, b) => a.spec - b.spec || a.ordre - b.ordre);
}

function _propres(el, regles) {
  const p = {};
  for (const k of PROPRIETES) if (el.attrs[k] !== undefined) p[k] = el.attrs[k].trim();
  const classes = String(el.attrs.class || "").split(/\s+/).filter(Boolean);
  for (const r of regles) {
    if (r.tag && r.tag !== el.nom) continue;
    if (r.classe && !classes.includes(r.classe)) continue;
    if (r.id && r.id !== el.attrs.id) continue;
    Object.assign(p, r.decl);
  }
  Object.assign(p, _declarations(el.attrs.style));
  return p;
}

function _calculer(el, parent, regles) {
  const propres = _propres(el, regles);
  const c = {};
  for (const k of HERITES) if (parent[k] !== undefined) c[k] = parent[k];
  for (const [k, v] of Object.entries(propres)) c[k] = v === "inherit" ? parent[k] : v;
  return c;
}

/* ── conversion ── */
const NON_DESSINES = new Set(["defs", "symbol", "clipPath", "mask", "filter", "style", "linearGradient", "radialGradient",
  "pattern", "marker", "title", "desc", "metadata", "script"]);
const RAISONS = ["cache", "image", "inconnu", "filtre", "decoupe", "masque", "degrade", "use", "chemin"];

function _transform_vue(vb, w, h, par) {
  const [vx, vy, vw, vh] = vb;
  let sx = w / vw, sy = h / vh;
  const pa = String(par || "xMidYMid meet").trim().split(/\s+/);
  if (pa[0] !== "none") {
    const s = pa[1] === "slice" ? Math.max(sx, sy) : Math.min(sx, sy);
    sx = sy = s;
  }
  const al = pa[0] === "none" ? "xMinYMin" : pa[0];
  const fx = /xMid/.test(al) ? 0.5 : (/xMax/.test(al) ? 1 : 0), fy = /YMid/.test(al) ? 0.5 : (/YMax/.test(al) ? 1 : 0);
  const tx = -vx * sx + (w - vw * sx) * fx, ty = -vy * sy + (h - vh * sy) * fy;
  if (sx === 1 && sy === 1 && tx === 0 && ty === 0) return null;
  return `matrix(${nb(sx)} 0 0 ${nb(sy)} ${nb(tx)} ${nb(ty)})`;
}

export function svg_vers_objets(texte) {
  const racine = xml_lire(texte);
  const trouver = (el) => {
    if (el.nom === "svg") return el;
    for (const e of el.enfants) { const r = trouver(e); if (r) return r; }
    return null;
  };
  const svg = trouver(racine);
  if (!svg) throw new Error(T("vectorlab.importer.svg_invalide"));

  // index des ids et feuilles de style (où qu'elles soient)
  const ids = new Map();
  let css = "";
  (function parcourir(el) {
    if (el.attrs.id && !ids.has(el.attrs.id)) ids.set(el.attrs.id, el);
    if (el.nom === "style") css += el.texte + "\n";
    el.enfants.forEach(parcourir);
  })(svg);
  const regles = _regles(css);

  const vb = _nombres(svg.attrs.viewBox);
  const vbOk = vb.length === 4 && vb[2] > 0 && vb[3] > 0;
  let w = _longueur(svg.attrs.width), h = _longueur(svg.attrs.height);
  if (!(w > 0)) w = vbOk ? (h > 0 ? h * vb[2] / vb[3] : vb[2]) : 300;
  if (!(h > 0)) h = vbOk ? w * vb[3] / vb[2] : 150;
  const taille = { w, h };
  const ref = vbOk ? { w: vb[2], h: vb[3] } : taille;

  const ignores = Object.fromEntries(RAISONS.map((r) => [r, 0]));
  let n = 0, importes = 0;
  const nouvelId = () => "i" + (++n);
  const lg = (v, r = 0) => _longueur(v, r) || 0;

  const peinture = (val, c, ref2) => {
    if (val === undefined) return null;
    const col = _couleur(val);
    if (!col) return null;
    if (col.c === "currentColor") return _couleur(c.color || "#000000") || { c: "#000000", a: 1 };
    if (col.c.startsWith("url(")) {
      ignores.degrade++;
      const m = /url\(\s*['"]?#([^'")\s]+)['"]?\s*\)\s*(.*)$/.exec(col.c);
      let g = m && ids.get(m[1]), garde = 0;
      while (g && !g.enfants.some((e) => e.nom === "stop") && garde++ < 8) {
        const h2 = g.attrs.href || g.attrs["xlink:href"];
        g = h2 && h2[0] === "#" ? ids.get(h2.slice(1)) : null;
      }
      const stop = g && g.enfants.find((e) => e.nom === "stop");
      if (stop) {
        const p = _propres(stop, regles);
        return _couleur(p["stop-color"] || "#000000") || { c: "#000000", a: 1 };
      }
      return (m && m[2] && _couleur(m[2])) || { c: "none", a: 1 };
    }
    return col;
  };

  const style = (c, propres, sansFond) => {
    const f = sansFond ? { c: "none", a: 1 } : (peinture(c.fill, c) || { c: "#000000", a: 1 });
    const s = peinture(c.stroke, c) || { c: "none", a: 1 };
    const st = { fond: f.c, contour: s.c, epaisseur: _longueur(c["stroke-width"]) ?? 1 };
    if (c["fill-rule"] === "evenodd") st.regle = "evenodd";
    if (s.c !== "none") st.joint = ["miter", "round", "bevel"].includes(c["stroke-linejoin"]) ? c["stroke-linejoin"] : "miter";   // défaut SVG : en onglet
    const num = (v) => { const x = parseFloat(v); return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : 1; };
    let op = num(propres.opacity ?? 1);
    op *= f.c !== "none" ? num(c["fill-opacity"] ?? 1) * f.a : num(c["stroke-opacity"] ?? 1) * s.a;
    if (op !== 1) st.opacite = Math.round(op * 1e4) / 1e4;
    const da = c["stroke-dasharray"];
    if (da && da !== "none") {
      const v = _nombres(da);
      if (v.length && v.some((x) => x > 0)) st.pointilles = v.map(nb).join(" ");
    }
    return st;
  };

  const effets = (p) => {
    if (p.filter && p.filter !== "none") ignores.filtre++;
    if (p["clip-path"] && p["clip-path"] !== "none") ignores.decoupe++;
    if (p.mask && p.mask !== "none") ignores.masque++;
  };

  const texteDe = (el) => {
    let s = "";
    for (const nd of el.noeuds) s += typeof nd === "string" ? nd : (nd.nom === "tspan" || nd.nom === "a" ? texteDe(nd) : "");
    return s;
  };

  const usage = new Set();
  const convertir = (el, parent) => {
    if (el.nom.includes(":") || NON_DESSINES.has(el.nom)) return null;
    const propres = _propres(el, regles);
    const c = _calculer(el, parent, regles);
    if (propres.display === "none" || c.visibility === "hidden" || c.visibility === "collapse") { ignores.cache++; return null; }
    const tr = el.attrs.transform ? el.attrs.transform.trim() : "";
    const avec = (o) => { if (tr) o.transform = tr; return o; };
    const feuille = (o) => { effets(propres); importes++; return avec(o); };
    switch (el.nom) {
      case "g": case "a": case "switch": case "svg": {
        const enfants = el.enfants.map((e) => convertir(e, c)).filter(Boolean);
        if (!enfants.length) return null;
        effets(propres);
        const g = { id: nouvelId(), type: "groupe", style: {}, enfants };
        const op = parseFloat(propres.opacity);
        if (Number.isFinite(op) && op < 1) g.style.opacite = Math.max(0, op);
        if (el.nom === "svg") {                                 // <svg> imbriqué : position et viewBox
          const vb2 = _nombres(el.attrs.viewBox);
          const parts = [];
          const x = lg(el.attrs.x, ref.w), y = lg(el.attrs.y, ref.h);
          if (x || y) parts.push(`translate(${nb(x)} ${nb(y)})`);
          if (vb2.length === 4 && vb2[2] > 0 && vb2[3] > 0) {
            const m = _transform_vue(vb2, lg(el.attrs.width, ref.w) || vb2[2], lg(el.attrs.height, ref.h) || vb2[3], el.attrs.preserveAspectRatio);
            if (m) parts.push(m);
          }
          if (parts.length) g.transform = parts.join(" ");
          return g;
        }
        return avec(g);
      }
      case "use": {
        const href = el.attrs.href || el.attrs["xlink:href"] || "";
        const cible = href[0] === "#" ? ids.get(href.slice(1)) : null;
        if (!cible || usage.has(cible)) { ignores.use++; return null; }
        usage.add(cible);
        const cibles = cible.nom === "symbol" ? cible.enfants : [cible];
        const enfants = cibles.map((e) => convertir(e, c)).filter(Boolean);
        usage.delete(cible);
        if (!enfants.length) return null;
        const x = lg(el.attrs.x, ref.w), y = lg(el.attrs.y, ref.h);
        const parts = [tr, x || y ? `translate(${nb(x)} ${nb(y)})` : ""].filter(Boolean);
        const g = { id: nouvelId(), type: "groupe", style: {}, enfants };
        if (parts.length) g.transform = parts.join(" ");
        effets(propres);
        return g;
      }
      case "rect": {
        const x = lg(el.attrs.x, ref.w), y = lg(el.attrs.y, ref.h), w2 = lg(el.attrs.width, ref.w), h2 = lg(el.attrs.height, ref.h);
        if (!(w2 > 0 && h2 > 0)) return null;
        let rx = _longueur(el.attrs.rx, ref.w), ry = _longueur(el.attrs.ry, ref.h);
        if (rx === null) rx = ry; if (ry === null) ry = rx;
        rx = Math.min(Math.max(rx || 0, 0), w2 / 2); ry = Math.min(Math.max(ry || 0, 0), h2 / 2);
        if (rx > 0 && ry > 0) {
          const d = `M${x + rx} ${y} H${x + w2 - rx} A${rx} ${ry} 0 0 1 ${x + w2} ${y + ry} V${y + h2 - ry}`
            + ` A${rx} ${ry} 0 0 1 ${x + w2 - rx} ${y + h2} H${x + rx} A${rx} ${ry} 0 0 1 ${x} ${y + h2 - ry}`
            + ` V${y + ry} A${rx} ${ry} 0 0 1 ${x + rx} ${y} Z`;
          return feuille({ id: nouvelId(), type: "path", d: chemin_normaliser(d), style: style(c, propres) });
        }
        return feuille({ id: nouvelId(), type: "rect", x, y, w: w2, h: h2, style: style(c, propres) });
      }
      case "circle": case "ellipse": {
        const cx = lg(el.attrs.cx, ref.w), cy = lg(el.attrs.cy, ref.h);
        const rx = el.nom === "circle" ? lg(el.attrs.r) : lg(el.attrs.rx, ref.w);
        const ry = el.nom === "circle" ? rx : lg(el.attrs.ry, ref.h);
        if (!(rx > 0 && ry > 0)) return null;
        return feuille({ id: nouvelId(), type: "ellipse", cx, cy, rx, ry, style: style(c, propres) });
      }
      case "line": {
        const d = `M${nb(lg(el.attrs.x1, ref.w))} ${nb(lg(el.attrs.y1, ref.h))} L${nb(lg(el.attrs.x2, ref.w))} ${nb(lg(el.attrs.y2, ref.h))}`;
        return feuille({ id: nouvelId(), type: "path", d, style: style(c, propres, true) });
      }
      case "polyline": case "polygon": {
        const v = _nombres(el.attrs.points);
        if (v.length < 4) return null;
        const pts = [];
        for (let k = 0; k + 1 < v.length; k += 2) pts.push(`${k ? "L" : "M"}${nb(v[k])} ${nb(v[k + 1])}`);
        return feuille({ id: nouvelId(), type: "path", d: pts.join(" ") + (el.nom === "polygon" ? " Z" : ""), style: style(c, propres) });
      }
      case "path": {
        if (!String(el.attrs.d || "").trim()) return null;
        let d;
        try { d = chemin_normaliser(el.attrs.d); } catch { ignores.chemin++; return null; }
        return feuille({ id: nouvelId(), type: "path", d, style: style(c, propres) });
      }
      case "text": {
        const contenu = texteDe(el).replace(/\s+/g, " ").trim();
        if (!contenu) return null;
        const st = style(c, propres);
        const fam = String(c["font-family"] || "").split(",")[0].trim().replace(/^['"]|['"]$/g, "");
        if (fam) st.police = fam;
        st.corps = _longueur(c["font-size"]) || 16;
        if (c["font-weight"] && c["font-weight"] !== "normal" && c["font-weight"] !== "400") st.graisse = c["font-weight"];
        if (c["font-style"] === "italic") st.italique = true;
        if (c["text-anchor"] === "middle" || c["text-anchor"] === "end") st.ancre = c["text-anchor"];
        const x = _nombres(el.attrs.x)[0] || 0, y = _nombres(el.attrs.y)[0] || 0;
        return feuille({ id: nouvelId(), type: "texte", x, y, contenu, style: st });
      }
      case "image": {
        const href = el.attrs.href || el.attrs["xlink:href"] || "";
        const w2 = lg(el.attrs.width, ref.w), h2 = lg(el.attrs.height, ref.h);
        if (!/^data:image\//i.test(href) || !(w2 > 0 && h2 > 0)) { ignores.image++; return null; }
        return feuille({ id: nouvelId(), type: "image", x: lg(el.attrs.x, ref.w), y: lg(el.attrs.y, ref.h), w: w2, h: h2,
          href, nat: { w: w2, h: h2 }, nat_provisoire: true, style: {} });
      }
      default:
        ignores.inconnu++;
        return null;
    }
  };

  const base = _calculer(svg, {}, regles);
  const objets = svg.enfants.map((e) => convertir(e, base)).filter(Boolean);
  const vue = vbOk ? _transform_vue(vb, w, h, svg.attrs.preserveAspectRatio) : null;
  return {
    objets: vue && objets.length ? [{ id: nouvelId(), type: "groupe", style: {}, transform: vue, enfants: objets }] : objets,
    taille,
    stats: { importes, ignores },
  };
}

/* ── T2 (t470) : importer dans le document ── */
// op_importer_svg(doc, analyse, { calque, x, y }) → id du groupe. Tout entre dans UN groupe dont la boîte du SVG
// (analyse.taille) est centrée sur (x, y), par défaut le centre de la page ; les ids provisoires sont retirés pour
// qu'op_ajouter donne des o<n> neufs, sans collision. L'analyse n'est pas modifiée : elle se réimporte.
export function op_importer_svg(doc, analyse, opts = {}) {
  const objets = (analyse && analyse.objets) || [];
  if (!objets.length) throw new Error(T("vectorlab.importer.vide"));
  const nettoyer = (o) => {
    const c = { ...o };
    delete c.id; delete c.nat_provisoire;
    if (Array.isArray(c.enfants)) c.enfants = c.enfants.map(nettoyer);
    return JSON.parse(JSON.stringify(c));
  };
  const t = analyse.taille || { w: 0, h: 0 };
  const x = opts.x === undefined ? doc.taille.w / 2 : +opts.x, y = opts.y === undefined ? doc.taille.h / 2 : +opts.y;
  const g = { type: "groupe", style: {}, transform: `translate(${nb(x - t.w / 2)} ${nb(y - t.h / 2)})`, enfants: objets.map(nettoyer) };
  return op_ajouter(doc, opts.calque || doc.calques[0].id, g);
}
