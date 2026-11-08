// mod-importpdf.js — lot D4 « Interop », T3 (t471 ; plan 2026-11-09-vectorlab-d4-import.md) : LIRE la première page
// d'un PDF en chemins du Vectorlab. Pur, sauf la décompression (DecompressionStream, navigateur et node ≥ 18), d'où
// une lecture asynchrone : pdf_vers_objets(octets) → Promise<{ objets, taille, stats }>.
//
// STRUCTURE. La table xref classique et les flux xref (prédicteurs PNG), les chaînes /Prev, les flux d'objets
// (ObjStm) ; un index illisible est RECONSTRUIT en parcourant le fichier (« N G obj »). Filtres : Flate, ASCIIHex,
// ASCII85 ; un autre est refusé en le nommant. Un PDF chiffré est refusé.
// PAGE. La première feuille de Pages › Kids, avec ses attributs hérités (Resources, MediaBox, CropBox, Rotate) ;
// la boîte visible (CropBox, sinon MediaBox) devient la page du document, en px (1 pt = 96 / 72 px), y vers le bas.
// OPÉRATEURS. État (q Q cm gs), tracés (m l c v y h re), peintures (f F f* S s B B* b b* n), couleurs (g rg k et leurs
// majuscules, cs sc scn : Gray, RGB, CMYK, ICCBased, Cal*, Separation, Indexed), trait (w d j). Un `sh` dans un
// écrêtage remplit la forme écrêtée de la PREMIÈRE couleur du dégradé (l'écart est compté) ; un motif devient gris.
// Les Form XObjects sont parcourus ; les images, les textes (BT … ET) et les écrêtages seuls sont comptés et ignorés.
import { T } from "./mod-i18n.js";

const OBJETS_MAX = 50000;
const K = 96 / 72;
const nb = (x) => String(Math.round(x * 1e4) / 1e4 + 0);
const refus = (cle, v) => new Error(T(cle, v));
const invalide = () => refus("vectorlab.importer.pdf_invalide");

/* ── valeurs PDF ── */
class Nom { constructor(n) { this.n = n; } }
class Ref { constructor(n, g) { this.n = n; this.g = g; } }
class Dict { constructor() { this.v = Object.create(null); } get(k) { return this.v[k]; } }
class Mot { constructor(m) { this.m = m; } }
const nom = (v) => (v instanceof Nom ? v.n : null);

const BLANC = new Set([0, 9, 10, 12, 13, 32]);
const DELIM = new Set([40, 41, 60, 62, 91, 93, 123, 125, 47, 37]);

/* ── lexique ── */
class Lex {
  constructor(o, p = 0) { this.o = o; this.p = p; }
  blancs() {
    const o = this.o;
    for (;;) {
      while (this.p < o.length && BLANC.has(o[this.p])) this.p++;
      if (o[this.p] === 37) { while (this.p < o.length && o[this.p] !== 10 && o[this.p] !== 13) this.p++; continue; }
      return;
    }
  }
  jeton() {
    this.blancs();
    const o = this.o;
    if (this.p >= o.length) return null;
    const c = o[this.p];
    if (c === 47) {                                            // /Nom, avec #xx
      let s = "";
      this.p++;
      while (this.p < o.length && !BLANC.has(o[this.p]) && !DELIM.has(o[this.p])) {
        if (o[this.p] === 35 && this.p + 2 < o.length) { s += String.fromCharCode(parseInt(String.fromCharCode(o[this.p + 1], o[this.p + 2]), 16) || 0); this.p += 3; }
        else s += String.fromCharCode(o[this.p++]);
      }
      return new Nom(s);
    }
    if (c === 40) return { chaine: this.chaine() };
    if (c === 60) {
      if (o[this.p + 1] === 60) { this.p += 2; return "<<"; }
      let h = "";
      this.p++;
      while (this.p < o.length && o[this.p] !== 62) { const x = o[this.p++]; if (!BLANC.has(x)) h += String.fromCharCode(x); }
      this.p++;
      if (h.length % 2) h += "0";
      let s = "";
      for (let k = 0; k < h.length; k += 2) s += String.fromCharCode(parseInt(h.slice(k, k + 2), 16) || 0);
      return { chaine: s };
    }
    if (c === 62) { this.p += o[this.p + 1] === 62 ? 2 : 1; return ">>"; }
    if (c === 91 || c === 93 || c === 123 || c === 125) { this.p++; return String.fromCharCode(c); }
    if (c === 41) { this.p++; return this.jeton(); }
    let s = "";
    while (this.p < o.length && !BLANC.has(o[this.p]) && !DELIM.has(o[this.p])) s += String.fromCharCode(o[this.p++]);
    if (/^[+-]?(\d+\.?\d*|\.\d+)$/.test(s)) return Number(s);
    return new Mot(s);
  }
  chaine() {
    const o = this.o;
    let s = "", prof = 1;
    this.p++;
    while (this.p < o.length) {
      const c = o[this.p++];
      if (c === 92) {
        const d = o[this.p++];
        const E = { 110: "\n", 114: "\r", 116: "\t", 98: "\b", 102: "\f" };
        if (E[d]) s += E[d];
        else if (d >= 48 && d <= 55) {
          let v = d - 48;
          for (let k = 0; k < 2 && o[this.p] >= 48 && o[this.p] <= 55; k++) v = v * 8 + o[this.p++] - 48;
          s += String.fromCharCode(v & 255);
        } else if (d === 13) { if (o[this.p] === 10) this.p++; }
        else if (d !== 10) s += String.fromCharCode(d);
      } else if (c === 40) { prof++; s += "("; }
      else if (c === 41) { if (--prof === 0) break; s += ")"; }
      else s += String.fromCharCode(c);
    }
    return s;
  }
  // une valeur ; `refs` : « N G R » reconnu (jamais dans un flux de contenu)
  valeur(refs = true, t = this.jeton()) {
    if (t === "<<") {
      const d = new Dict();
      for (;;) {
        const k = this.jeton();
        if (k === ">>" || k === null) return d;
        if (!(k instanceof Nom)) continue;
        d.v[k.n] = this.valeur(refs);
      }
    }
    if (t === "[") {
      const a = [];
      for (;;) {
        const j = this.jeton();
        if (j === "]" || j === null) return a;
        a.push(this.valeur(refs, j));
      }
    }
    if (refs && typeof t === "number" && Number.isInteger(t)) {
      const garde = this.p, g = this.jeton();
      if (typeof g === "number" && Number.isInteger(g)) {
        const r = this.jeton();
        if (r instanceof Mot && r.m === "R") return new Ref(t, g);
      }
      this.p = garde;
    }
    if (t instanceof Mot) {
      if (t.m === "true") return true;
      if (t.m === "false") return false;
      if (t.m === "null") return null;
    }
    return t;
  }
}

/* ── filtres ── */
async function _inflate(d) {
  const lire = async (octets, format) => {
    const lecteur = new Blob([octets]).stream().pipeThrough(new DecompressionStream(format)).getReader();
    const morceaux = [];
    try {
      for (;;) { const { done, value } = await lecteur.read(); if (done) break; morceaux.push(value); }
    } catch (e) {
      if (!morceaux.length) throw e;                          // fin abîmée : on garde ce qui est sorti
    }
    const n = morceaux.reduce((s, m) => s + m.length, 0), out = new Uint8Array(n);
    let k = 0;
    for (const m of morceaux) { out.set(m, k); k += m.length; }
    return out;
  };
  try { return await lire(d, "deflate"); } catch {
    try { return await lire(d.subarray(2), "deflate-raw"); } catch { throw invalide(); }
  }
}
function _predicteur(d, p) {
  const pred = (p && p.get("Predictor")) || 1;
  if (pred < 2) return d;
  const couleurs = (p.get("Colors") || 1), bpc = (p.get("BitsPerComponent") || 8), col = (p.get("Columns") || 1);
  const bpp = Math.max(1, Math.ceil(couleurs * bpc / 8)), ligne = Math.ceil(couleurs * bpc * col / 8);
  if (pred === 2) {                                           // TIFF, 8 bits
    const out = d.slice();
    for (let r = 0; r * ligne < out.length; r++) for (let k = bpp; k < ligne; k++) out[r * ligne + k] = (out[r * ligne + k] + out[r * ligne + k - bpp]) & 255;
    return out;
  }
  const n = Math.floor(d.length / (ligne + 1)), out = new Uint8Array(n * ligne);
  for (let r = 0; r < n; r++) {
    const f = d[r * (ligne + 1)], src = r * (ligne + 1) + 1, dst = r * ligne;
    for (let k = 0; k < ligne; k++) {
      const a = k >= bpp ? out[dst + k - bpp] : 0, b = r ? out[dst - ligne + k] : 0, c = r && k >= bpp ? out[dst - ligne + k - bpp] : 0;
      let v = d[src + k];
      if (f === 1) v += a;
      else if (f === 2) v += b;
      else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const q = a + b - c, pa = Math.abs(q - a), pb = Math.abs(q - b), pc = Math.abs(q - c); v += pa <= pb && pa <= pc ? a : (pb <= pc ? b : c); }
      out[dst + k] = v & 255;
    }
  }
  return out;
}
function _ahx(d) {
  let h = "";
  for (const c of d) { if (c === 62) break; if (!BLANC.has(c)) h += String.fromCharCode(c); }
  if (h.length % 2) h += "0";
  const out = new Uint8Array(h.length / 2);
  for (let k = 0; k < out.length; k++) out[k] = parseInt(h.slice(2 * k, 2 * k + 2), 16) || 0;
  return out;
}
function _a85(d) {
  const out = [];
  let g = [];
  for (let i = 0; i < d.length; i++) {
    const c = d[i];
    if (c === 126) break;                                     // ~>
    if (BLANC.has(c)) continue;
    if (c === 122 && !g.length) { out.push(0, 0, 0, 0); continue; }
    g.push(c - 33);
    if (g.length === 5) {
      let v = 0;
      for (const x of g) v = v * 85 + x;
      out.push((v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255);
      g = [];
    }
  }
  if (g.length > 1) {
    const n = g.length;
    while (g.length < 5) g.push(84);
    let v = 0;
    for (const x of g) v = v * 85 + x;
    out.push(...[(v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255].slice(0, n - 1));
  }
  return Uint8Array.from(out);
}

/* ── le document ── */
class Pdf {
  constructor(o) { this.o = o; this.xref = new Map(); this.cache = new Map(); this.stms = new Map(); this.trailer = null; }

  lireXref() {
    const o = this.o;
    const fin = this.latin(Math.max(0, o.length - 2048), o.length);
    const m = /startxref\s+(\d+)/g;
    let off = null, r;
    while ((r = m.exec(fin))) off = +r[1];
    const vus = new Set();
    while (off !== null && off !== undefined && !vus.has(off)) {
      vus.add(off);
      if (!(off >= 0 && off < o.length)) throw invalide();
      const L = new Lex(o, off);
      const t = L.jeton();
      let tr;
      if (t instanceof Mot && t.m === "xref") {
        for (;;) {
          const garde = L.p, a = L.jeton();
          if (a instanceof Mot && a.m === "trailer") break;
          const n = L.jeton();
          if (typeof a !== "number" || typeof n !== "number") { L.p = garde; throw invalide(); }
          for (let k = 0; k < n; k++) {
            const pos = L.jeton(), gen = L.jeton(), f = L.jeton();
            if (!this.xref.has(a + k) && f instanceof Mot && f.m === "n") this.xref.set(a + k, { t: 1, off: pos });
            else if (!this.xref.has(a + k)) this.xref.set(a + k, { t: 0 });
            if (typeof gen !== "number") throw invalide();
          }
        }
        tr = L.valeur();
        if (!(tr instanceof Dict)) throw invalide();
        if (typeof tr.get("XRefStm") === "number") this.xrefFlux(tr.get("XRefStm"));
      } else {
        tr = this.xrefFlux(off);
      }
      if (!this.trailer) this.trailer = tr;
      off = tr.get("Prev");
    }
    if (!this.trailer) throw invalide();
  }
  xrefFlux(off) {
    const s = this.objetA(off);
    if (!s || !s.flux || nom(s.dict.get("Type")) !== "XRef") throw invalide();
    this.attente = this.attente || [];
    this.attente.push(s);                                      // décodé dans preparer() (asynchrone)
    return s.dict;
  }
  async preparer() {
    for (const s of this.attente || []) {
      const d = await this.decoder(s);
      const W = s.dict.get("W"), idx = s.dict.get("Index") || [0, s.dict.get("Size")];
      const lg = W[0] + W[1] + W[2];
      const champ = (p, n) => { let v = 0; for (let k = 0; k < n; k++) v = v * 256 + d[p + k]; return v; };
      let p = 0;
      for (let k = 0; k + 1 < idx.length; k += 2) {
        for (let i = 0; i < idx[k + 1] && p + lg <= d.length; i++, p += lg) {
          const id = idx[k] + i;
          const type = W[0] ? champ(p, W[0]) : 1, a = champ(p + W[0], W[1]), b = champ(p + W[0] + W[1], W[2]);
          if (this.xref.has(id)) continue;
          this.xref.set(id, type === 1 ? { t: 1, off: a } : type === 2 ? { t: 2, stm: a, idx: b } : { t: 0 });
        }
      }
    }
    this.attente = [];
  }
  // index perdu : chaque « N G obj » du fichier, le dernier l'emporte ; le trailer, ou le Catalog trouvé
  reconstruire() {
    this.xref = new Map(); this.cache = new Map(); this.trailer = null;
    const s = this.latin(0, this.o.length);
    const re = /(\d+)\s+(\d+)\s+obj\b/g;
    let m;
    while ((m = re.exec(s))) this.xref.set(+m[1], { t: 1, off: m.index });
    const k = s.lastIndexOf("trailer");
    if (k >= 0) { const tr = new Lex(this.o, k + 7).valeur(); if (tr instanceof Dict) this.trailer = tr; }
    if (!this.trailer || !this.trailer.get("Root")) {
      for (const [id, e] of this.xref) {
        const x = this.objetA(e.off);
        if (x && x.valeur instanceof Dict && nom(x.valeur.get("Type")) === "Catalog") {
          this.trailer = this.trailer || new Dict();
          this.trailer.v.Root = new Ref(id, 0);
        }
      }
    }
    this.reconstruit = true;
  }
  latin(a, b) {
    let s = "";
    for (let i = a; i < b; i += 8192) s += String.fromCharCode.apply(null, this.o.subarray(i, Math.min(b, i + 8192)));
    return s;
  }
  // « N G obj valeur [stream … endstream] » à un décalage
  objetA(off) {
    const L = new Lex(this.o, off);
    const a = L.jeton(), b = L.jeton(), c = L.jeton();
    if (typeof a !== "number" || typeof b !== "number" || !(c instanceof Mot && c.m === "obj")) return null;
    const v = L.valeur();
    const garde = L.p, t = L.jeton();
    if (v instanceof Dict && t instanceof Mot && t.m === "stream") {
      let p = L.p;
      if (this.o[p] === 13) p++;
      if (this.o[p] === 10) p++;
      let lg = v.get("Length");
      if (lg instanceof Ref) { const e = this.xref.get(lg.n); const x = e && e.t === 1 ? this.objetA(e.off) : null; lg = x && x.valeur; }
      const ok = typeof lg === "number" && p + lg <= this.o.length && /^\s*endstream/.test(this.latin(p + lg, Math.min(this.o.length, p + lg + 20)));
      if (!ok) {                                               // longueur fausse : jusqu'à endstream
        const s = this.latin(p, Math.min(this.o.length, p + 50_000_000));
        const e = s.indexOf("endstream");
        lg = e < 0 ? this.o.length - p : e;
        while (lg > 0 && (this.o[p + lg - 1] === 10 || this.o[p + lg - 1] === 13)) lg--;
      }
      return { dict: v, valeur: v, flux: this.o.subarray(p, p + lg) };
    }
    L.p = garde;
    return { valeur: v };
  }
  async objet(n) {
    if (this.cache.has(n)) return this.cache.get(n);
    const e = this.xref.get(n);
    let r = null;
    if (e && e.t === 1) r = this.objetA(e.off);
    else if (e && e.t === 2) r = await this.dansStm(e.stm, e.idx, n);
    this.cache.set(n, r);
    return r;
  }
  async dansStm(stm, idx, n) {
    if (!this.stms.has(stm)) {
      const s = await this.objet(stm);
      if (!s || !s.flux) { this.stms.set(stm, null); return null; }
      const d = await this.decoder(s);
      const L = new Lex(d), N = s.dict.get("N") || 0, premier = s.dict.get("First") || 0, table = [];
      for (let k = 0; k < N; k++) table.push([L.jeton(), L.jeton()]);
      this.stms.set(stm, { d, table, premier });
    }
    const S = this.stms.get(stm);
    if (!S) return null;
    const ent = S.table.find((x) => x[0] === n) || S.table[idx];
    return ent ? { valeur: new Lex(S.d, S.premier + ent[1]).valeur() } : null;
  }
  async res(v) {
    for (let k = 0; v instanceof Ref && k < 32; k++) { const o = await this.objet(v.n); v = o ? (o.flux ? o : o.valeur) : null; }
    return v;
  }
  async dictDe(v) { v = await this.res(v); return v && v.flux ? v.dict : v instanceof Dict ? v : null; }
  async decoder(s) {
    let d = s.flux;
    const f = await this.res(s.dict.get("Filter")), p = await this.res(s.dict.get("DecodeParms"));
    const filtres = Array.isArray(f) ? f : f ? [f] : [];
    const params = Array.isArray(p) ? p : [p];
    for (let i = 0; i < filtres.length; i++) {
      const n = nom(filtres[i]);
      if (n === "FlateDecode" || n === "Fl") d = _predicteur(await _inflate(d), await this.dictDe(params[i]));
      else if (n === "ASCIIHexDecode" || n === "AHx") d = _ahx(d);
      else if (n === "ASCII85Decode" || n === "A85") d = _a85(d);
      else throw refus("vectorlab.importer.pdf_filtre", { filtre: n });
    }
    return d;
  }
}

/* ── matrices [a b c d e f] : x' = a x + c y + e ; mul(m, n) = n d'abord ── */
const mul = (m, n) => [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
  m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
const app = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];

/* ── couleurs ── */
const hex2 = (v) => Math.max(0, Math.min(255, Math.round(v * 255))).toString(16).padStart(2, "0");
const rvb = (r, g, b) => "#" + hex2(r) + hex2(g) + hex2(b);
function _versRvb(esp, c) {
  if (esp.genre === "indexe") {
    const i = Math.max(0, Math.min(esp.max, Math.round(c[0] || 0))), n = esp.base.n, t = esp.table;
    return _versRvb(esp.base, Array.from({ length: n }, (_, k) => (t.charCodeAt(i * n + k) || 0) / 255));
  }
  if (esp.genre === "teinte") return rvb(1 - (c[0] || 0), 1 - (c[0] || 0), 1 - (c[0] || 0));
  if (esp.n === 4) { const [C, M, Y, Kk] = c.map((x) => x || 0); return rvb((1 - C) * (1 - Kk), (1 - M) * (1 - Kk), (1 - Y) * (1 - Kk)); }
  if (esp.n === 3) return rvb(c[0] || 0, c[1] || 0, c[2] || 0);
  return rvb(c[0] || 0, c[0] || 0, c[0] || 0);
}
const GRIS = { genre: "simple", n: 1 }, RVB = { genre: "simple", n: 3 }, CMJN = { genre: "simple", n: 4 }, MOTIF = { genre: "motif", n: 0 };

export async function pdf_vers_objets(octets) {
  const o = octets instanceof Uint8Array ? octets : new Uint8Array(octets || []);
  const pdf = new Pdf(o);
  let racine = null;
  try {
    pdf.lireXref();
    await pdf.preparer();
    racine = await pdf.dictDe(pdf.trailer.get("Root"));
  } catch {
    racine = null;                                             // index illisible : reconstruit ci-dessous
  }
  if (!racine) { pdf.reconstruire(); racine = pdf.trailer && await pdf.dictDe(pdf.trailer.get("Root")); }
  if (pdf.trailer && pdf.trailer.get("Encrypt")) throw refus("vectorlab.importer.pdf_chiffre");
  if (!racine) throw invalide();

  // la première page, avec ses attributs hérités
  const pages = await pdf.dictDe(racine.get("Pages"));
  if (!pages) throw invalide();
  const HERITES = ["Resources", "MediaBox", "CropBox", "Rotate"];
  let page = null;
  const herite = {};
  const vus = new Set();
  async function descendre(noeud, h, prof) {
    if (!noeud || prof > 64) return false;
    const h2 = { ...h };
    for (const k of HERITES) if (noeud.get(k) !== undefined) h2[k] = noeud.get(k);
    const kids = await pdf.res(noeud.get("Kids"));
    if (nom(noeud.get("Type")) === "Page" || (!Array.isArray(kids) && nom(noeud.get("Type")) !== "Pages")) {
      page = noeud; Object.assign(herite, h2); return true;
    }
    for (const k of Array.isArray(kids) ? kids : []) {
      if (k instanceof Ref) { if (vus.has(k.n)) continue; vus.add(k.n); }
      if (await descendre(await pdf.dictDe(k), h2, prof + 1)) return true;
    }
    return false;
  }
  await descendre(pages, {}, 0);
  if (!page) throw invalide();
  const nPages = await pdf.res(pages.get("Count"));

  // la boîte, la rotation, la matrice de base (espace de la page → px du document)
  const boiteDe = async (v) => {
    const a = await pdf.res(v);
    if (!Array.isArray(a) || a.length < 4) return null;
    const n = [];
    for (const x of a) n.push(+(await pdf.res(x)));
    if (n.some((x) => !Number.isFinite(x))) return null;
    return [Math.min(n[0], n[2]), Math.min(n[1], n[3]), Math.max(n[0], n[2]), Math.max(n[1], n[3])];
  };
  const bt = (await boiteDe(herite.CropBox)) || (await boiteDe(herite.MediaBox)) || [0, 0, 612, 792];
  const [x0, y0, x1, y1] = bt;
  const rot = ((Math.round((+(await pdf.res(herite.Rotate)) || 0) / 90) % 4) + 4) % 4;
  const BASE = [
    [K, 0, 0, -K, -K * x0, K * y1],
    [0, K, K, 0, -K * y0, -K * x0],
    [-K, 0, 0, K, K * x1, -K * y0],
    [0, -K, -K, 0, K * y1, K * x1],
  ][rot];
  const taille = rot % 2 ? { w: K * (y1 - y0), h: K * (x1 - x0) } : { w: K * (x1 - x0), h: K * (y1 - y0) };

  const ignores = { texte: 0, image: 0, decoupe: 0, degrade: 0, motif: 0 };
  const objets = [];

  // le contenu de la page : un flux, ou un tableau de flux enchaînés
  const flux = async (v) => {
    v = await pdf.res(v);
    if (v && v.flux) return [await pdf.decoder(v)];
    if (Array.isArray(v)) { const out = []; for (const x of v) out.push(...(await flux(x))); return out; }
    return [];
  };
  const morceaux = await flux(page.get("Contents"));
  const contenu = new Uint8Array(morceaux.reduce((s, m) => s + m.length + 1, 0));
  let p0 = 0;
  for (const m of morceaux) { contenu.set(m, p0); contenu[p0 + m.length] = 10; p0 += m.length + 1; }

  const espaceDe = async (v, ress) => {
    const n = nom(v);
    if (n === "DeviceGray" || n === "G" || n === "CalGray") return GRIS;
    if (n === "DeviceRGB" || n === "RGB" || n === "CalRGB") return RVB;
    if (n === "DeviceCMYK" || n === "CMYK") return CMJN;
    if (n === "Pattern") return MOTIF;
    if (n) {
      const cs = ress && (await pdf.dictDe(ress.get("ColorSpace")));
      const def = cs && cs.get(n);
      return def !== undefined ? espaceDe(await pdf.res(def), null) : GRIS;
    }
    const a = await pdf.res(v);
    if (!Array.isArray(a)) return GRIS;
    const fam = nom(a[0]);
    if (fam === "ICCBased") { const s = await pdf.dictDe(a[1]); const N = s && (await pdf.res(s.get("N"))); return N === 4 ? CMJN : N === 3 ? RVB : GRIS; }
    if (fam === "CalRGB" || fam === "Lab") return RVB;
    if (fam === "CalGray") return GRIS;
    if (fam === "Pattern") return MOTIF;
    if (fam === "Separation" || fam === "DeviceN") return { genre: "teinte", n: 1 };
    if (fam === "Indexed" || fam === "I") {
      const base = await espaceDe(a[1], ress);
      let t = await pdf.res(a[3]);
      if (t && t.flux) t = String.fromCharCode.apply(null, await pdf.decoder(t));
      else t = t && t.chaine !== undefined ? t.chaine : "";
      return { genre: "indexe", n: 1, base, max: +(await pdf.res(a[2])) || 0, table: t };
    }
    return GRIS;
  };
  const couleurShading = async (sh) => {
    const d = await pdf.dictDe(sh);
    if (!d) return null;
    let f = await pdf.dictDe(d.get("Function"));
    const fa = await pdf.res(d.get("Function"));
    if (!f && Array.isArray(fa)) f = await pdf.dictDe(fa[0]);
    for (let k = 0; f && k < 8 && (await pdf.res(f.get("FunctionType"))) === 3; k++) f = await pdf.dictDe((await pdf.res(f.get("Functions")))[0]);
    const esp = await espaceDe(await pdf.res(d.get("ColorSpace")), null);
    const c0 = f ? await pdf.res(f.get("C0")) : null;
    const comps = Array.isArray(c0) ? c0.map(Number) : esp.n === 4 ? [0, 0, 0, 0] : [0];
    return _versRvb(esp, comps);
  };

  // l'interprète
  const echelle = (m) => Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));
  // un Form XObject hérite de l'état de l'appelant ; son opacité (groupe) MULTIPLIE celle de ses objets (mulF, mulS)
  async function interpreter(octetsFlux, ressources, gs0, prof, mulF = 1, mulS = 1) {
    const L = new Lex(octetsFlux);
    let gs = gs0;
    const pile = [];
    let pile2 = [], segs = [], courant = null, debut = null, clipEnAttente = null;
    const M = () => mul(BASE, gs.ctm);
    const pt = (x, y) => app(M(), x, y);
    const fin = () => { segs = []; courant = null; debut = null; };
    const peindre = (remplir, tracer, eo) => {
      if (clipEnAttente) { gs.clip = { d: segs.join(" "), eo: clipEnAttente === "W*", compte: true }; ignores.decoupe++; clipEnAttente = null; }
      if (!segs.some((s) => s[0] !== "M") || (!remplir && !tracer)) { fin(); return; }
      const st = { fond: "none", contour: "none" };
      if (remplir) {
        st.fond = gs.fill.c;
        if (gs.fill.raison) ignores[gs.fill.raison]++;
        if (eo) st.regle = "evenodd";
      }
      const s = echelle(M());
      st.epaisseur = Math.round((gs.lw > 0 ? gs.lw * s : 1) * 1e4) / 1e4;
      if (tracer) {
        st.contour = gs.stroke.c;
        if (gs.stroke.raison) ignores[gs.stroke.raison]++;
        st.joint = ["miter", "round", "bevel"][gs.joint] || "miter";
        if (gs.dash && gs.dash.length && gs.dash.some((v) => v > 0)) st.pointilles = gs.dash.map((v) => nb(v * s)).join(" ");
      }
      const op = remplir ? gs.ca * mulF : gs.CA * mulS;
      if (op < 1) st.opacite = Math.max(0, Math.round(op * 1e4) / 1e4);
      if (objets.length >= OBJETS_MAX) throw refus("vectorlab.importer.trop_grand", { n: OBJETS_MAX });
      objets.push({ id: "p" + (objets.length + 1), type: "path", d: segs.join(" "), style: st });
      fin();
    };
    const fermer = () => { if (courant && debut) { segs.push("Z"); courant = debut.slice(); } };
    const P = (x, y) => { const [a, b] = pt(x, y); return [a, b]; };
    const fmt = (q) => nb(q[0]) + " " + nb(q[1]);
    const couleur = (esp, ops) => {
      if (esp.genre === "motif") return null;
      return { c: _versRvb(esp, ops.filter((v) => typeof v === "number")) };
    };
    const motif = async (n) => {
      const pats = await pdf.dictDe(ressources && ressources.get("Pattern"));
      const pd = pats && (await pdf.dictDe(pats.get(n)));
      if (pd && (await pdf.res(pd.get("PatternType"))) === 2) return { c: (await couleurShading(pd.get("Shading"))) || "#808080", raison: "degrade" };
      return { c: "#808080", raison: "motif" };
    };
    for (;;) {
      const t = L.jeton();
      if (t === null) break;
      if (!(t instanceof Mot)) { pile2.push(L.valeur(false, t)); continue; }
      const a = pile2;
      pile2 = [];
      switch (t.m) {
        case "q": pile.push({ ...gs, dash: gs.dash && gs.dash.slice() }); break;
        case "Q": if (pile.length) gs = pile.pop(); break;
        case "cm": if (a.length >= 6) gs.ctm = mul(gs.ctm, a.slice(-6).map(Number)); break;
        case "m": { const q = P(a[0], a[1]); segs.push("M" + fmt(q)); courant = q; debut = q; break; }
        case "l": { if (!courant) break; const q = P(a[0], a[1]); segs.push("L" + fmt(q)); courant = q; break; }
        case "c": { if (!courant) break; const q1 = P(a[0], a[1]), q2 = P(a[2], a[3]), q = P(a[4], a[5]); segs.push(`C${fmt(q1)} ${fmt(q2)} ${fmt(q)}`); courant = q; break; }
        case "v": { if (!courant) break; const q2 = P(a[0], a[1]), q = P(a[2], a[3]); segs.push(`C${fmt(courant)} ${fmt(q2)} ${fmt(q)}`); courant = q; break; }
        case "y": { if (!courant) break; const q1 = P(a[0], a[1]), q = P(a[2], a[3]); segs.push(`C${fmt(q1)} ${fmt(q)} ${fmt(q)}`); courant = q; break; }
        case "h": fermer(); break;
        case "re": {
          const [x, y, w, h] = a.map(Number);
          const c = [P(x, y), P(x + w, y), P(x + w, y + h), P(x, y + h)];
          segs.push("M" + fmt(c[0]), "L" + fmt(c[1]), "L" + fmt(c[2]), "L" + fmt(c[3]), "Z");
          courant = debut = c[0];
          break;
        }
        case "f": case "F": peindre(true, false, false); break;
        case "f*": peindre(true, false, true); break;
        case "S": peindre(false, true, false); break;
        case "s": fermer(); peindre(false, true, false); break;
        case "B": peindre(true, true, false); break;
        case "B*": peindre(true, true, true); break;
        case "b": fermer(); peindre(true, true, false); break;
        case "b*": fermer(); peindre(true, true, true); break;
        case "n": peindre(false, false, false); break;
        case "W": clipEnAttente = "W"; break;
        case "W*": clipEnAttente = "W*"; break;
        case "g": gs.espF = GRIS; gs.fill = couleur(GRIS, a); break;
        case "G": gs.espS = GRIS; gs.stroke = couleur(GRIS, a); break;
        case "rg": gs.espF = RVB; gs.fill = couleur(RVB, a); break;
        case "RG": gs.espS = RVB; gs.stroke = couleur(RVB, a); break;
        case "k": gs.espF = CMJN; gs.fill = couleur(CMJN, a); break;
        case "K": gs.espS = CMJN; gs.stroke = couleur(CMJN, a); break;
        case "cs": case "CS": {
          const esp = await espaceDe(a[0], ressources);
          const noir = esp.genre === "motif" ? { c: "#808080", raison: "motif" } : { c: _versRvb(esp, esp.n === 4 ? [0, 0, 0, 1] : esp.genre === "teinte" ? [1] : [0, 0, 0]) };
          if (t.m === "cs") { gs.espF = esp; gs.fill = noir; } else { gs.espS = esp; gs.stroke = noir; }
          break;
        }
        case "sc": case "scn": case "SC": case "SCN": {
          const remplir = t.m[0] === "s", esp = remplir ? gs.espF : gs.espS;
          const nm = a.length && a[a.length - 1] instanceof Nom ? a[a.length - 1].n : null;
          const c = nm ? await motif(nm) : couleur(esp, a);
          if (c) { if (remplir) gs.fill = c; else gs.stroke = c; }
          break;
        }
        case "w": if (typeof a[0] === "number") gs.lw = a[0]; break;
        case "d": gs.dash = Array.isArray(a[0]) ? a[0].map(Number) : null; break;
        case "j": if (typeof a[0] === "number") gs.joint = a[0]; break;
        case "gs": {
          const eg = await pdf.dictDe(ressources && ressources.get("ExtGState"));
          const g = eg && a[0] instanceof Nom ? await pdf.dictDe(eg.get(a[0].n)) : null;
          if (g) {
            const ca = await pdf.res(g.get("ca")), CA = await pdf.res(g.get("CA")), lw = await pdf.res(g.get("LW")), D = await pdf.res(g.get("D"));
            if (typeof ca === "number") gs.ca = ca;
            if (typeof CA === "number") gs.CA = CA;
            if (typeof lw === "number") gs.lw = lw;
            if (Array.isArray(D) && Array.isArray(D[0])) gs.dash = D[0].map(Number);
          }
          break;
        }
        case "sh": {
          ignores.degrade++;
          if (!gs.clip) break;                                 // sans écrêtage, il peindrait toute la page
          const shs = await pdf.dictDe(ressources && ressources.get("Shading"));
          const c = (a[0] instanceof Nom && shs && (await couleurShading(shs.get(a[0].n)))) || "#808080";
          if (gs.clip.compte) { ignores.decoupe--; gs.clip.compte = false; }
          const st = { fond: c, contour: "none", epaisseur: 1 };
          if (gs.clip.eo) st.regle = "evenodd";
          if (gs.ca * mulF < 1) st.opacite = Math.round(gs.ca * mulF * 1e4) / 1e4;
          objets.push({ id: "p" + (objets.length + 1), type: "path", d: gs.clip.d, style: st });
          break;
        }
        case "Do": {
          const xo = await pdf.dictDe(ressources && ressources.get("XObject"));
          const x = xo && a[0] instanceof Nom ? await pdf.res(xo.get(a[0].n)) : null;
          if (!x || !x.flux) break;
          const st = nom(x.dict.get("Subtype"));
          if (st === "Image") { ignores.image++; break; }
          if (st === "Form" && prof < 12) {
            const m = await pdf.res(x.dict.get("Matrix"));
            const ctm = Array.isArray(m) && m.length === 6 ? mul(gs.ctm, m.map(Number)) : gs.ctm;
            const r = (await pdf.dictDe(x.dict.get("Resources"))) || ressources;
            await interpreter(await pdf.decoder(x), r, { ...gs, dash: gs.dash && gs.dash.slice(), ctm, ca: 1, CA: 1 }, prof + 1, mulF * gs.ca, mulS * gs.CA);
          }
          break;
        }
        case "BT": ignores.texte++; break;
        case "BI": {
          // image en ligne : son dictionnaire jusqu'à ID, puis les octets jusqu'à « EI » entouré de blancs
          for (let j = L.jeton(); j !== null && !(j instanceof Mot && j.m === "ID"); j = L.jeton()) { /* clés */ }
          let q = L.p + 1;
          const o2 = L.o;
          while (q + 1 < o2.length && !(BLANC.has(o2[q - 1]) && o2[q] === 69 && o2[q + 1] === 73 && (q + 2 >= o2.length || BLANC.has(o2[q + 2])))) q++;
          L.p = q + 2;
          ignores.image++;
          break;
        }
        default: break;                                        // texte, contenu marqué, compatibilité : sans effet
      }
    }
    return objets;
  }

  const ressources = await pdf.dictDe(herite.Resources);
  await interpreter(contenu, ressources, { ctm: [1, 0, 0, 1, 0, 0], fill: { c: "#000000" }, stroke: { c: "#000000" }, espF: GRIS, espS: GRIS,
    lw: 1, dash: null, joint: 0, ca: 1, CA: 1, clip: null }, 0);
  return { objets, taille, stats: { importes: objets.length, pages: typeof nPages === "number" ? nPages : 1, ignores } };
}
