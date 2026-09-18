// theme.test.mjs — mod-theme : les jetons du thème Affinity, le bloc :root,
// et le BANC-GARDE : vectorlab.css ne contient plus aucun hex de l'ancienne
// palette bleu-nuit hors commentaire, ni de damier sur #stage. Feuille.
import { TOKENS, theme_css, LEGACY, hex_herites } from "../js/mod-theme.js";
import { readFileSync } from "node:fs";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 300) : "")); };
{
  ok("jetons : fond, barre, canevas, bord, texte, muet, sel, cyan, violet, menu, champ — des hex", ["fond", "barre", "canevas", "bord", "texte", "muet", "sel", "cyan", "violet", "menu", "champ"].every((k) => /^#[0-9a-f]{6}$/i.test(TOKENS[k])), JSON.stringify(TOKENS));
  ok("theme_css : un bloc :root avec une variable --aff-<jeton> par jeton", theme_css().startsWith(":root {") && Object.keys(TOKENS).every((k) => theme_css().includes(`--aff-${k}: ${TOKENS[k]}`)), theme_css());
  ok("LEGACY : au moins 30 hex hérités, tous en minuscules", LEGACY.length >= 30 && LEGACY.every((h) => /^#[0-9a-f]{6}$/.test(h)));
  ok("hex_herites : trouve les hex de LEGACY hors commentaires, insensible à la casse, ignore les commentaires", hex_herites("a { color: #171A20; } /* #232833 */ b { c: #313847 }").join() === "#171a20,#313847" && hex_herites("").length === 0 && hex_herites(null).length === 0);
  const css = readFileSync(new URL("../vectorlab.css", import.meta.url), "utf8");
  const restes = [...new Set(hex_herites(css))];
  ok("vectorlab.css : plus aucun hex hérité actif", restes.length === 0, restes.join(","));
  ok("vectorlab.css : plus de damier (linear-gradient) sur #stage", !/#stage\s*\{[^}]*linear-gradient/.test(css));
  ok("vectorlab.css : le bloc :root des jetons y est (les valeurs de mod-theme)", css.includes(`--aff-fond: ${TOKENS.fond}`) && css.includes(`--aff-canevas: ${TOKENS.canevas}`));
}
if (echecs.length) { console.error("ECHECS theme :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA theme : PASS (7 controles)");
