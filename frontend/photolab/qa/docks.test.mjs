// qa/docks.test.mjs — t371 (29/10/2026) : docks lisibles et marges du Photolab.
// Onglets des groupes de panneaux sur UNE ligne (ellipse + bulle, défilement horizontal discret, menu « ⋯ » au-delà),
// marges internes au jeton --pad-2 de la charte (frontend/shared/dz-charte.css), en-têtes alignés, plus de carré
// blanc de redimensionnement (coin d'ascenseur, poignée de zone de texte) : la poignée de la charte.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { deborde, defilementPour, defilementRoue, entreesMenu, RESERVE_PLUS } from "../js/mod-docks.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const css = readFileSync(join(racine, "photolab.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
const html = readFileSync(join(racine, "index.html"), "utf8");
const core = readFileSync(join(racine, "js/core.js"), "utf8");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));

// Déclarations d'une règle CSS dont le sélecteur est EXACTEMENT `sel` (toutes les règles de ce sélecteur, fusionnées).
function regle(sel) {
  const out = {};
  for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const sels = m[1].split(",").map((s) => s.trim().replace(/\s+/g, " "));
    if (!sels.includes(sel)) continue;
    for (const d of m[2].split(";")) {
      const i = d.indexOf(":"); if (i < 0) continue;
      out[d.slice(0, i).trim()] = d.slice(i + 1).trim();
    }
  }
  return out;
}

// ── 1. fonctions pures ───────────────────────────────────────────────────────────────────────────────────────────
check("1.1 déborde : contenu plus large que la vue", deborde(320, 278) === true);
check("1.2 ne déborde pas : égal ou à 1 px près (arrondis du navigateur)", deborde(278, 278) === false && deborde(279, 278) === false);
check("1.3 entrées absentes → pas de débord", deborde(undefined, 0) === false);
// onglet [gauche, gauche+largeur] dans une vue de 200 px qui garde RESERVE_PLUS à droite pour le bouton « ⋯ »
check("1.4 onglet déjà visible : on ne bouge pas", defilementPour(10, 60, 0, 200, 24) === 0);
check("1.5 onglet caché à droite : on avance juste assez (réserve du « ⋯ » comprise)",
  defilementPour(250, 80, 0, 200, 24) === 250 + 80 - (200 - 24), defilementPour(250, 80, 0, 200, 24));
check("1.6 onglet caché à gauche : on recule jusqu'à son bord", defilementPour(30, 60, 120, 200, 24) === 30);
check("1.7 onglet plus large que la vue : son bord gauche gagne", defilementPour(300, 400, 0, 200, 24) === 300);
check("1.8 réserve absente = 0", defilementPour(250, 80, 0, 200) === 130);
check("1.9 molette verticale → défilement horizontal", defilementRoue(0, 0, 40, 100) === 40);
check("1.10 molette horizontale (pavé) prioritaire quand elle domine", defilementRoue(50, -30, 5, 100) === 20);
check("1.11 borné à [0, max]", defilementRoue(90, 0, 40, 100) === 100 && defilementRoue(10, 0, -40, 100) === 0);
check("1.12 la réserve du « ⋯ » couvre le bouton (≥ 20 px)", RESERVE_PLUS >= 20);
const menu = entreesMenu([{ texte: " Pinceaux ", actif: true }, { texte: "Paramètres de pinceau", actif: false }, { texte: "", actif: false }]);
check("1.13 menu « ⋯ » : un item par onglet, libellé nettoyé, actif repéré, index d'origine",
  JSON.stringify(menu) === JSON.stringify([{ texte: "Pinceaux", actif: true, index: 0 }, { texte: "Paramètres de pinceau", actif: false, index: 1 }]),
  JSON.stringify(menu));

// ── 2. onglets sur une ligne ──────────────────────────────────────────────────────────────────────────────────────
const tete = regle(".groupe-tete");
check("2.1 en-tête : défilement horizontal seulement (jamais d'ascenseur vertical)",
  tete["overflow-x"] === "auto" && tete["overflow-y"] === "hidden", JSON.stringify(tete));
check("2.2 en-tête : ascenseur invisible (défilement discret)", tete["scrollbar-width"] === "none");
check("2.3 ascenseur WebKit masqué aussi", (regle(".groupe-tete::-webkit-scrollbar").display || "") === "none");
check("2.4 en-tête : pas de retour à la ligne", (tete["flex-wrap"] || "nowrap") === "nowrap" && !/wrap\b(?!-)/.test(tete["flex-flow"] || ""));
check("2.5 en-tête collé aux bords : l'onglet porte la marge (alignée sur le corps)", tete.padding === "0");
const onglet = regle(".groupe-tete .onglet");
check("2.6 onglet : une ligne", onglet["white-space"] === "nowrap", JSON.stringify(onglet));
check("2.7 onglet : ne rétrécit pas sous son texte, ellipse au-delà de sa largeur maximale",
  /^0 0 auto$|^none$/.test(onglet.flex || "") && onglet["text-overflow"] === "ellipsis" && onglet.overflow === "hidden"
  && !!onglet["max-width"], JSON.stringify(onglet));
check("2.8 onglet : marge horizontale --pad-2 (le texte tombe sur la marge du corps)", onglet.padding === "0 var(--pad-2)", onglet.padding);
// plus aucun réglage d'en-tête par groupe : un seul modèle, donc des en-têtes alignés
const parGroupe = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].filter((m) => /#grp\w+ \.groupe-tete/.test(m[1]));
check("2.9 aucun en-tête ni onglet retouché groupe par groupe (#grpX .groupe-tete…)", parGroupe.length === 0,
  parGroupe.map((m) => m[1].trim()).join(" | "));
check("2.10 bouton « ⋯ » : collé à droite pendant le défilement, à la charte",
  regle(".groupe-plus").position === "sticky" && regle(".groupe-plus").right === "0", JSON.stringify(regle(".groupe-plus")));
check("2.11 « ⋯ » caché tant que rien ne déborde", (regle(".groupe-tete:not(.deborde) .groupe-plus").display || "") === "none");
check("2.12 menu « ⋯ » : angles vifs, marges de la charte",
  regle(".groupe-menu")["border-radius"] === "var(--radius)" && /var\(--pad-1\)/.test(regle(".groupe-menu").padding || ""),
  JSON.stringify(regle(".groupe-menu")));

// ── 3. marges internes --pad-2 ────────────────────────────────────────────────────────────────────────────────────
check("3.1 corps des panneaux : --pad-2", regle(".groupe-corps").padding === "var(--pad-2)", regle(".groupe-corps").padding);
const corpsLitteraux = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  .filter((m) => m[1].split(",").some((s) => /^(#grp\w+ )?(#corps\w+|\.groupe-corps)$/.test(s.trim().replace(/\s+/g, " ")))
    && /(^|;)\s*padding\s*:(?!\s*(0\s*(;|$)|var\(--pad-\d\)\s*(;|$)))/.test(m[2]));
check("3.2 aucun corps de panneau à marge littérale (0 ou un jeton --pad-*)", corpsLitteraux.length === 0,
  corpsLitteraux.map((m) => m[1].trim()).join(" | "));
check("3.3 Calques (pleine largeur) : la tête du panneau garde --pad-2",
  regle(".cq-tete").padding === "var(--pad-2)", regle(".cq-tete").padding);

// ── 4. poignée de la charte à la place des carrés blancs ──────────────────────────────────────────────────────────
check("4.1 coin d'ascenseur transparent (le carré blanc entre deux ascenseurs)",
  /transparent/.test(regle("::-webkit-scrollbar-corner").background || ""), JSON.stringify(regle("::-webkit-scrollbar-corner")));
const poignee = regle("::-webkit-resizer");
check("4.2 poignée de redimensionnement : traits de la charte, aucun blanc",
  /var\(--stroke-strong\)/.test(poignee.background || "") && !/#fff|white/i.test(poignee.background || ""), JSON.stringify(poignee));

// ── 5. branchement ───────────────────────────────────────────────────────────────────────────────────────────────
check("5.1 core.js importe et lance initDocks", /import \{ initDocks \} from "\.\/mod-docks\.js"/.test(core) && /initDocks\(PL\)/.test(core));
check("5.2 initDocks après les espaces (une disposition rejouée change les onglets montrés)",
  core.indexOf("initDocks(PL)") > core.indexOf("initEspaces(PL)"));
const cle = dico["photolab.docks.plus"] || {};
check("5.3 libellé du « ⋯ » en FR et EN", !!cle.fr && !!cle.en && cle.fr !== cle.en, JSON.stringify(cle));
check("5.4 tous les groupes ont leur en-tête d'onglets", (html.match(/class="groupe-tete" role="tablist"/g) || []).length >= 6);

console.log(`docks : ${ok} OK, ${ko} échec(s)`);
if (ko) process.exit(1);
