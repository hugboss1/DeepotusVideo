// bulles.test.mjs — les bulles (title) d'index.html disent vrai sur les raccourcis :
// la lettre « (X) » d'un outil est sa touche dans mod-familles (aucune si l'outil n'en a pas,
// ex. l'outil IA : G bascule la grille), et le bouton Rétablir affiche le même raccourci
// que le menu Édition. Feuille : lit le HTML, pas de DOM.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { touche_de } from "../js/mod-familles.js";
import { MENUS_BARRE, menu_trouver, raccourci_de } from "../js/mod-menus.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
const html = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "index.html"), "utf8");
{
  const outils = [...html.matchAll(/<button data-outil="([^"]+)" title="([^"]*)"/g)].map((m) => [m[1], m[2]]);
  ok("des boutons d'outils sont lus", outils.length >= 15, outils.length);
  const faux = outils.filter(([id, t]) => { const l = (/\(([A-Z])\)\s*$/.exec(t) || [])[1] || ""; const k = touche_de(id); return k ? l !== k : l !== ""; });
  ok("chaque « (X) » de bulle = la touche de l'outil, ou rien s'il n'en a pas", faux.length === 0, faux.map(([id, t]) => `${id}: ${t}`).join(" | "));
  const ia = outils.find(([id]) => id === "ia");
  ok("outil IA : aucun raccourci annoncé (G = Grille)", ia && !/\(G\)/.test(ia[1]), ia && ia[1]);
  const ed = menu_trouver(MENUS_BARRE, "Edition");
  const refaire = ed.entrees.find((e) => e !== "-" && e.id === "refaire");
  const b = /<button id="btnRefaire"[^>]*title="([^"]*)"[^>]*aria-label="([^"]*)"/.exec(html);
  const attendu = `${refaire.libelle} (${raccourci_de(refaire)})`;
  ok("bouton Rétablir : libellé et raccourci du menu Édition (title et aria-label)", b && b[1] === attendu && b[2] === attendu, b ? `${b[1]} / ${b[2]} ≠ ${attendu}` : "btnRefaire absent");
  // version EN : le dictionnaire du Vectorlab (lot de traduction) reprend les bulles du HTML mot pour mot
  let dico = null;
  try { dico = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "..", "shared", "i18n", "vectorlab.json"), "utf8")); } catch (e) { /* pas encore traduit */ }
  if (dico) {
    const vals = Object.values(dico);
    const iaFaux = vals.filter((v) => /^(Illustration IA|AI illustration)\b/i.test(v.fr || "") && (/\(G\)/.test(v.fr) || /\(G\)/.test(v.en || "")));
    ok("EN : aucune bulle de l'outil IA n'annonce (G)", iaFaux.length === 0, JSON.stringify(iaFaux));
    const red = vals.filter((v) => /^(Refaire|Rétablir) \(/.test(v.fr || ""));
    ok("EN : la bulle Rétablir dit Ctrl+Maj+Z / Ctrl+Shift+Z", red.every((v) => v.fr === attendu && v.en === "Redo (Ctrl+Shift+Z)"), JSON.stringify(red));
  }
}
if (echecs.length) { console.error("ÉCHECS bulles :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("bulles : OK");
