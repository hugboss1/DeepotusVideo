// champs_pastilles.test.mjs — t264 (20/10/2026) : le Vectorlab reprend deux dessins du Photolab (#410, #411).
// 1. Les pastilles fond / contour à la Photoshop : un carré de 54 px, le fond (premier plan, haut gauche) chevauche le
//    contour (arrière-plan, bas droite), échange en haut à droite, couleurs par défaut en bas à gauche — l'échange et
//    le défaut sont des fonctions pures de mod-couleur.
// 2. Les champs des panneaux de la pile au dessin du panneau Couleur du Photolab (.co-ligne / .co-lib / .co-hex) :
//    libellé --ink-soft à gauche, champ --bg-base / --stroke / --ink en chasse fixe, colonne d'unité de 16 px, liseré
//    --accent au focus — tout par les jetons partagés, aucune couleur en dur dans le bloc t264.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { pastilles_echanger, PASTILLES_DEFAUT } from "../js/mod-couleur.js";

const ici = dirname(fileURLToPath(import.meta.url));
const lire = (p) => readFileSync(join(ici, p), "utf-8");
const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };
const eg = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/* ── échange et défaut (purs) ── */
ok("échange : deux couleurs passent l'une à la place de l'autre",
  eg(pastilles_echanger({ fond: "#112233", contour: "#445566" }), { fond: "#445566", contour: "#112233" }));
ok("échange : sans contour → le fond devient « aucun », le contour prend l'ancien fond",
  eg(pastilles_echanger({ fond: "#112233" }), { fond: "none", contour: "#112233" })
  && eg(pastilles_echanger({ fond: "#112233", contour: "none" }), { fond: "none", contour: "#112233" }));
ok("échange : sans fond → le contour est retiré (null), le fond prend l'ancien contour",
  eg(pastilles_echanger({ fond: "none", contour: "#445566" }), { fond: "#445566", contour: null }));
ok("échange : rien des deux côtés → rien à faire (null)", pastilles_echanger({ fond: "none" }) === null && pastilles_echanger({}) === null);
ok("échange : un fond dégradé ne passe pas au contour (null)", pastilles_echanger({ fond: "grad:g1", contour: "#000000" }) === null);
ok("défaut : fond blanc, contour noir (comme le D d'Illustrator)", eg(PASTILLES_DEFAUT, { fond: "#FFFFFF", contour: "#000000" }) && Object.isFrozen(PASTILLES_DEFAUT));

/* ── le panneau : un carré de pastilles, les ids d'origine conservés ── */
const style = lire("../js/mod-style.js");
ok("mod-style : le carré .vl-pastilles porte le fond, le contour, l'échange et le défaut",
  /class="vl-pastilles"/.test(style) && /id="apEchanger"/.test(style) && /id="apDefaut"/.test(style)
  && /vl-pastille-fond[^>]*id="apFond"|id="apFond"[^>]*vl-pastille-fond/.test(style)
  && /vl-pastille-contour[^>]*id="apContour"|id="apContour"[^>]*vl-pastille-contour/.test(style));
ok("mod-style : chaque pastille n'est posée qu'une fois (ids uniques)",
  (style.match(/id="apFond"/g) || []).length === 1 && (style.match(/id="apContour"/g) || []).length === 1);
ok("mod-style : l'échange et le défaut passent par appliquer (une commande annulable)",
  /pastilles_echanger\(/.test(style) && /PASTILLES_DEFAUT/.test(style));

/* ── la feuille : le bloc t264 sous jetons ── */
const css = lire("../vectorlab.css");
const i = css.indexOf("══ t264");
const bloc = i < 0 ? "" : css.slice(css.lastIndexOf("/*", i)).replace(/\/\*[\s\S]*?\*\//g, "");
ok("vectorlab.css : un bloc t264", i > 0);
ok("bloc t264 : aucune couleur en dur (hex, rgb)", !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(bloc), (bloc.match(/#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)/g) || []).join(" "));
for (const j of ["--bg-base", "--stroke", "--ink", "--ink-soft", "--ink-muted", "--accent", "--f-mono", "--f-ui", "--bg-panel"]) {
  ok(`bloc t264 : jeton ${j}`, bloc.includes(`var(${j})`));
}
ok("bloc t264 : carré de 54 px, pastilles de 30 px, liseré du fond du panneau",
  /\.vl-pastilles\s*\{[^}]*width:\s*54px[^}]*height:\s*54px/.test(bloc)
  && /\.vl-pastille-fond\s*\{[^}]*width:\s*30px[^}]*box-shadow:\s*0 0 0 2px var\(--bg-panel\)/.test(bloc)
  && /\.vl-pastille-contour\s*\{[^}]*left:\s*20px;\s*top:\s*20px/.test(bloc));
ok("bloc t264 : sélecteurs des pastilles sous l'id du panneau (#panneauCalques button les écraserait)",
  !/^\s*\.vl-pastille/m.test(bloc) && /#panneauStyle \.vl-pastilles/.test(bloc));
ok("bloc t264 : colonne d'unité de 16 px et focus à l'accent",
  /width:\s*16px/.test(bloc) && /:focus[^{]*\{[^}]*border-color:\s*var\(--accent\)/.test(bloc));

/* ── les fonds du Photolab (demande du 20/10) : colonne d'outils, panneaux, scène, barres ── */
ok("fonds : les jetons --aff-* de fond pointent sur les jetons partagés",
  /--aff-fond:\s*var\(--bg-panel\)/.test(bloc) && /--aff-canevas:\s*var\(--bg-panel-3\)/.test(bloc)
  && /--aff-champ:\s*var\(--bg-base\)/.test(bloc) && /--aff-bord:\s*var\(--stroke\)/.test(bloc));
ok("fonds : outils, panneaux, menus et état sur --bg-panel, options sur --bg-panel-2, scène sur --bg-panel-3",
  /\.mb, \.outils, \.panneau, \.sb \{ background: var\(--bg-panel\)/.test(bloc) && /\.cb \{ background: var\(--bg-panel-2\)/.test(bloc)
  && /#stage \{ background: var\(--bg-panel-3\)/.test(bloc));

/* ── les textes : une clé FR = une clé EN ── */
const dico = JSON.parse(lire("../../shared/i18n/vectorlab.json"));
for (const k of ["vectorlab.style.pastilles_echanger", "vectorlab.style.pastilles_defaut"]) {
  ok(`i18n : ${k} en FR et en EN`, dico[k] && dico[k].fr && dico[k].en, JSON.stringify(dico[k] || null));
}

if (echecs.length) { console.error("ECHECS champs_pastilles :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log(`QA champs_pastilles : PASS (${n} controles)`);
