// zip.js — lot 5 (19/09/2026) : un écrivain ZIP « store » (méthode 0, sans
// compression) en pur JS pour livrer plusieurs PNG en UN fichier (les tuiles
// séparées du Tilelab). PUR : entrées {nom, data: Uint8Array} → Uint8Array.
// Dates fixées au 1er janvier 1980 (reproductible). Banc : qa/zip.test.mjs.
const _TABLE = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
export function crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = _TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
export function zip_store(entrees) {
  if (!entrees || !entrees.length) throw new Error("zip : aucune entrée");
  const enc = new TextEncoder(), locaux = [], centraux = [];
  let offset = 0;
  for (const e of entrees) {
    const nom = enc.encode(String(e.nom || ""));
    if (!nom.length) throw new Error("zip : nom d'entrée vide");
    const data = e.data instanceof Uint8Array ? e.data : new Uint8Array(e.data || []);
    const crc = crc32(data);
    const loc = new Uint8Array(30 + nom.length + data.length), dv = new DataView(loc.buffer);
    dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true); dv.setUint16(6, 0x0800, true); dv.setUint16(8, 0, true);
    dv.setUint16(10, 0, true); dv.setUint16(12, 0x0021, true); dv.setUint32(14, crc, true); dv.setUint32(18, data.length, true); dv.setUint32(22, data.length, true);
    dv.setUint16(26, nom.length, true); dv.setUint16(28, 0, true);
    loc.set(nom, 30); loc.set(data, 30 + nom.length);
    const cen = new Uint8Array(46 + nom.length), cv = new DataView(cen.buffer);
    cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true); cv.setUint16(8, 0x0800, true); cv.setUint16(10, 0, true);
    cv.setUint16(12, 0, true); cv.setUint16(14, 0x0021, true); cv.setUint32(16, crc, true); cv.setUint32(20, data.length, true); cv.setUint32(24, data.length, true);
    cv.setUint16(28, nom.length, true); cv.setUint16(30, 0, true); cv.setUint16(32, 0, true); cv.setUint16(34, 0, true); cv.setUint16(36, 0, true);
    cv.setUint32(38, 0, true); cv.setUint32(42, offset, true);
    cen.set(nom, 46);
    locaux.push(loc); centraux.push(cen); offset += loc.length;
  }
  const tailleCentral = centraux.reduce((s, c) => s + c.length, 0);
  const fin = new Uint8Array(22), fv = new DataView(fin.buffer);
  fv.setUint32(0, 0x06054b50, true); fv.setUint16(4, 0, true); fv.setUint16(6, 0, true); fv.setUint16(8, entrees.length, true); fv.setUint16(10, entrees.length, true);
  fv.setUint32(12, tailleCentral, true); fv.setUint32(16, offset, true); fv.setUint16(20, 0, true);
  const out = new Uint8Array(offset + tailleCentral + 22);
  let p = 0;
  for (const b of [...locaux, ...centraux, fin]) { out.set(b, p); p += b.length; }
  return out;
}
