// Assistant (spec 2026-10-19-agent-aide-design.md) — /shared/dz-agent-logique.js : la logique PURE du tiroir et du
// pointeur (aucun DOM à l'import) : choix de l'élément d'une ancre, composition cadre + intérieur, courbe du
// curseur, étapes d'une action, historique borné.
// Lancer : node frontend/shared/qa/agent_logique.test.mjs
import assert from "node:assert/strict";
import * as L from "../dz-agent-logique.js";

// 1. choisir l'élément parmi les candidats (texte ou title, exact d'abord, visibles seulement)
const C = [
  { texte: "Quick  ", titre: "", visible: true },
  { texte: "Studio nouveau", titre: "", visible: true },
  { texte: "", titre: "Montage", visible: true },
  { texte: "Réglages", titre: "", visible: false },
];
assert.equal(L.choisir(C, { texte: { fr: "Quick", en: "Quick" } }, "fr"), 0);
assert.equal(L.choisir(C, { texte: { fr: "Studio", en: "Studio" } }, "fr"), 1, "contient, à défaut d'exact");
assert.equal(L.choisir(C, { texte: { fr: "Montage", en: "Montage" } }, "en"), 2, "le title compte (rail replié)");
assert.equal(L.choisir(C, { texte: { fr: "Réglages", en: "Settings" } }, "fr"), -1, "invisible : ignoré");
assert.equal(L.choisir(C, {}, "fr"), 0, "sans texte : le premier visible");
assert.equal(L.choisir([], { texte: { fr: "x", en: "x" } }, "fr"), -1);
assert.equal(L.choisir(C, { texte: { fr: "quick", en: "Quick" } }, "fr"), 0, "casse et espaces ignorés");

// 2. composer un rectangle trouvé dans un cadre
assert.deepEqual(L.composer({ x: 100, y: 50 }, { x: 10, y: 20, w: 30, h: 40 }), { x: 110, y: 70, w: 30, h: 40 });
assert.equal(L.composer({ x: 0, y: 0 }, null), null);

// 3. courbe : départ à t=0, arrivée à t=1, et un vrai arc au milieu
const a = { x: 0, y: 0 }, b = { x: 400, y: 0 };
assert.deepEqual(L.courbe(a, b, 0), a);
assert.deepEqual(L.courbe(a, b, 1), b);
const m = L.courbe(a, b, 0.5);
assert.ok(Math.abs(m.x - 200) < 1e-9 && Math.abs(m.y) > 40, "l'arc s'écarte de la ligne droite");
assert.deepEqual(L.courbe(a, a, 0.5), a, "départ = arrivée : aucun NaN");

// 4. étapes d'une action selon l'écran courant
assert.deepEqual(L.etapes({ type: "aller", cible: "montage" }, "quick"), [{ faire: "aller", vue: "montage" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "settings", reglages: "keys" }, "quick"),
  [{ faire: "aller", vue: "settings" }, { faire: "reglages", section: "keys" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "montage", selecteur: "b" }, "montage"), [{ faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "vectorlab", selecteur: "b" }, "quick"),
  [{ faire: "aller", vue: "vectorlab" }, { faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: null, selecteur: "button.dzNavItem" }, "news"), [{ faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "guide", cible: "quick" }, "news"), [{ faire: "guide", chapitre: "quick" }]);
assert.deepEqual(L.etapes({ type: "aller", cible: "../x" }, "news"), [], "vue inconnue : rien");
assert.deepEqual(L.etapes({ type: "guide", cible: "a/b" }, "news"), [], "chapitre au format douteux : rien");

// 5. historique borné aux 10 derniers tours, rôles valides seulement
const h = Array.from({ length: 14 }, (_, i) => ({ role: i % 2 ? "assistant" : "user", texte: "t" + i }));
h.push({ role: "pirate", texte: "x" });
const b2 = L.historiqueBorne(h);
assert.equal(b2.length, 10);
assert.equal(b2[9].texte, "t13");

// 6. le module n'utilise aucun objet du navigateur à l'import
assert.equal(typeof globalThis.document, "undefined");
console.log("agent_logique : OK");
