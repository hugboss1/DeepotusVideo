// palettes.js — lot 4 (19/09/2026) : UNE liste de palettes nommées pour le
// Spritelab, le Tilelab et le persona Pixel du Vectorlab. Les cinq palettes
// « backend » portent les MÊMES identifiants et les MÊMES hex que
// `backend/app/services/pixel_ops.py` (la pixelisation du Spritelab et du
// Tilelab s'y fait par nom) — le banc `qa/palettes.test.mjs` lit le fichier
// Python et refuse toute dérive. Les deux autres sont locales (JS seul).
// PUR : aucun DOM ; `options_palettes` rend une chaîne HTML.
const _pal = (hexes) => [...new Set(hexes.map((h) => "#" + h.toUpperCase()))];

export const PALETTES = [
  { id: "pico8", nom: "PICO-8", backend: true, couleurs: _pal(["000000", "1D2B53", "7E2553", "008751", "AB5236", "5F574F",
    "C2C3C7", "FFF1E8", "FF004D", "FFA300", "FFEC27", "00E436", "29ADFF", "83769C", "FF77A8", "FFCCAA"]) },
  { id: "gameboy", nom: "Game Boy", backend: true, couleurs: _pal(["0F380F", "306230", "8BAC0F", "9BBC0F"]) },
  { id: "nes", nom: "NES", backend: true, couleurs: _pal(["7C7C7C", "0000FC", "0000BC", "4428BC", "940084", "A80020",
    "A81000", "881400", "503000", "007800", "006800", "005800", "004058", "000000",
    "BCBCBC", "0078F8", "0058F8", "6844FC", "D800CC", "E40058", "F83800", "E45C10", "AC7C00", "00B800", "00A800", "00A844", "008888",
    "F8F8F8", "3CBCFC", "6888FC", "9878F8", "F878F8", "F85898", "F87858", "FCA044", "F8B800", "B8F818", "58D854", "58F898", "00E8D8", "787878",
    "FCFCFC", "A4E4FC", "B8B8F8", "D8B8F8", "F8B8F8", "F8A4C0", "F0D0B0", "FCE0A8", "F8D878", "D8F878", "B8F8B8", "B8F8D8", "00FCFC", "F8D8F8"]) },
  { id: "sweetie16", nom: "Sweetie 16", backend: true, couleurs: _pal(["1A1C2C", "5D275D", "B13E53", "EF7D57", "FFCD75",
    "A7F070", "38B764", "257179", "29366F", "3B5DC9", "41A6F6", "73EFF7", "F4F4F4", "94B0C2", "566C86", "333C57"]) },
  { id: "onebit", nom: "1-bit", backend: true, couleurs: _pal(["000000", "FFFFFF"]) },
  // locales (Sprite Editor de Sorceress : Grayscale 16, Handheld 4) — pas de pixelisation backend par nom
  { id: "gray16", nom: "Grayscale 16", backend: false, couleurs: _pal(Array.from({ length: 16 }, (_, i) => Math.round(i * 255 / 15).toString(16).padStart(2, "0").repeat(3))) },
  { id: "handheld4", nom: "Handheld 4", backend: false, couleurs: _pal(["2B2B26", "706B66", "A8A398", "E0DBCD"]) },
];

export function palette_de(id) {
  return PALETTES.find((p) => p.id === id) || null;
}

const _esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
export function options_palettes({ backendSeulement = false, courante = "" } = {}) {
  const liste = backendSeulement ? PALETTES.filter((p) => p.backend) : PALETTES;
  return `<option value=""${courante === "" ? " selected" : ""}>Adaptative (N couleurs)</option>`
    + liste.map((p) => `<option value="${p.id}"${p.id === courante ? " selected" : ""}>${_esc(p.nom)} (${p.couleurs.length})</option>`).join("");
}
