// palettes.test.mjs — lot 4 : UNE liste de palettes nommées pour Spritelab,
// Tilelab et le persona Pixel ; les cinq du backend sont exactement celles
// de pixel_ops.py (lu en texte : une dérive casse le banc).
import { readFileSync } from "node:fs";
import { PALETTES, palette_de, options_palettes } from "../palettes.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
const HEX = /^#[0-9A-F]{6}$/;
ok("sept palettes, identifiants uniques, hex majuscules valides", PALETTES.length === 7 && new Set(PALETTES.map((p) => p.id)).size === 7 && PALETTES.every((p) => p.couleurs.length >= 2 && p.couleurs.every((c) => HEX.test(c))));
const py = readFileSync(new URL("../../../backend/app/services/pixel_ops.py", import.meta.url), "utf-8");
for (const id of ["pico8", "gameboy", "nes", "sweetie16", "onebit", "gray16", "handheld4"]) {   // lot 5 : les sept sont backend
  const bloc = py.slice(py.indexOf(`"${id}": _pal(`)); const fin = bloc.indexOf(")");
  ok(`${id} est défini dans pixel_ops.py`, bloc.length > 0 && py.includes(`"${id}": _pal(`));
  // gray16 est GÉNÉRÉE côté Python (compréhension) : la liste attendue se calcule, les autres se lisent
  const hex = id === "gray16" ? Array.from({ length: 16 }, (_, i) => "#" + Math.round(i * 255 / 15).toString(16).padStart(2, "0").toUpperCase().repeat(3))
    : [...new Set((bloc.slice(0, fin).match(/"([0-9A-Fa-f]{6})"/g) || []).map((h) => "#" + h.slice(1, 7).toUpperCase()))];
  const p = palette_de(id);
  ok(`${id} = pixel_ops (${hex.length} couleurs, backend)`, p && p.backend === true && JSON.stringify(p.couleurs) === JSON.stringify(hex), p && p.couleurs.length + " vs " + hex.length);
}
ok("gray16 et handheld4 : 16 et 4 couleurs, backend depuis le lot 5", palette_de("gray16").backend === true && palette_de("gray16").couleurs.length === 16 && palette_de("handheld4").couleurs.length === 4);
ok("palette_de inconnue → null", palette_de("zz") === null);
const o = options_palettes({ backendSeulement: true, courante: "sweetie16" });
ok("options HTML backend seulement : Adaptative + 7, la courante sélectionnée", (o.match(/<option/g) || []).length === 8 && o.includes('value="sweetie16" selected') && o.includes("gray16"));
ok("options toutes : 7 + Adaptative", (options_palettes({}).match(/<option/g) || []).length === 8);
if (echecs.length) { console.error("ECHECS palettes :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA palettes : PASS (19 controles)");
