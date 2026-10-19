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

// 7. renforts (mutations survivantes)
assert.equal(L.choisir([{ texte: "Studio nouveau", visible: true }, { texte: "Studio", visible: true }], { texte: { fr: "Studio" } }, "fr"), 1, "exact avant tout");
assert.equal(L.choisir([{ texte: "Mon Studio", visible: true }, { texte: "Studio 3D", visible: true }], { texte: { fr: "Studio" } }, "fr"), 1, "commence par avant inclusion");
const loin = L.courbe({ x: 0, y: 0 }, { x: 2000, y: 0 }, 0.5);
assert.ok(Math.abs(loin.y) <= 80 + 1e-9, "plafond de 160 px sur l'écart");
assert.equal(L.courbe({ x: 0, y: 0 }, { x: 400, y: 0 }, 0.5).y, 60, "sens de l'arc figé");
const vert = L.courbe({ x: 0, y: 0 }, { x: 0, y: 400 }, 0.5);
assert.ok(Math.abs(vert.x + 60) < 1e-9 && Math.abs(vert.y - 200) < 1e-9, "arc vertical");
assert.deepEqual(L.etapes({ type: "point", ecran: "inconnu", selecteur: "b" }, "quick"), [{ faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "montage", partout: true, selecteur: "button.dzNavItem" }, "quick"), [{ faire: "pointer" }], "ancre du rail : jamais de navigation");
assert.equal(L.choisir(C, { texte: { fr: "Quick" } }, "en"), 0, "repli sur le français");
assert.equal(L.choisir([{ texte: "Son  &\nVFX", visible: true }], { texte: { fr: "Son & VFX" } }, "fr"), 0, "blancs normalisés");
assert.equal(L.choisir([{ texte: "", titre: "Bibliothèque", visible: true }], { texte: { fr: "Bibliothèque" } }, "fr"), 0, "title seul");
assert.deepEqual(L.historiqueBorne(null), []);
assert.deepEqual(L.historiqueBorne([{ role: "user", texte: 5 }, { role: "user", texte: "ok" }]), [{ role: "user", texte: "ok" }]);

// 5 bis. candidats : un faux document minimal (querySelectorAll, faux nœuds)
const nd = (texte, titre, w, sous) => ({ textContent: texte, getAttribute: (k) => (k === "title" ? titre : null),
  getBoundingClientRect: () => ({ width: w, height: w }),
  querySelector: (q) => { if (q === "!") throw new Error("sélecteur invalide"); return q === ".lbl" ? sous || null : null; } });
const n1 = nd("🎬 Studio 3", "", 10, { textContent: "Studio" }), n2 = nd("Caché", "Montage", 0);
const faux = { querySelectorAll: (q) => { if (q === "!!") throw new Error("invalide"); return q === "b" ? [n1, n2] : []; } };
assert.deepEqual(L.candidats(faux, "b", ".lbl").map(({ texte, titre, visible }) => ({ texte, titre, visible })),
  [{ texte: "Studio", titre: "", visible: true }, { texte: "Caché", titre: "Montage", visible: false }], "libellé lu dans le sous-élément");
assert.equal(L.candidats(faux, "b", "").at(0).texte, "🎬 Studio 3", "sans libelle : le texte entier");
assert.equal(L.candidats(faux, "b", "!").at(0).texte, "🎬 Studio 3", "libelle invalide : repli sur l'élément");
assert.equal(L.candidats(faux, "b").at(0).noeud, n1);
assert.deepEqual(L.candidats(faux, "!!"), [], "sélecteur invalide : aucun candidat");
assert.equal(L.choisir(L.candidats(faux, "b", ".lbl"), { texte: { fr: "Studio" } }, "fr"), 0);

// 8. A5 : capture réduite, point de la capture → écran, même onglet, élément cliquable, prix, étapes
assert.deepEqual(L.reduire(2560, 1440), { l: 1280, h: 720 });
assert.deepEqual(L.reduire(800, 600), { l: 800, h: 600 }, "jamais agrandie");
assert.deepEqual(L.reduire(1000, 3000), { l: 427, h: 1280 });
assert.equal(L.reduire(0, 10), null);
assert.equal(L.COTE_MAX, 1280);
const p5 = { x: 640, y: 360, largeur: 1280, hauteur: 720 };
assert.deepEqual(L.versEcran(p5, { l: 1920, h: 1080 }), { x: 960, y: 540 });
assert.deepEqual(L.versEcran({ ...p5, x: 5000, y: -3 }, { l: 1920, h: 1080 }), { x: 1920, y: 0 }, "borné");
assert.equal(L.versEcran({ x: 1, y: 1, largeur: 0, hauteur: 0 }, { l: 10, h: 10 }), null);
assert.equal(L.versEcran(p5, null), null);
assert.equal(L.versEcran({ ...p5, x: "a" }, { l: 10, h: 10 }), null);
assert.ok(L.memeOnglet(2560, 1314, { l: 1280, h: 657 }));
assert.ok(!L.memeOnglet(1920, 1080, { l: 1280, h: 657 }), "écran entier 16:9 contre un onglet plus bas : refusé");
assert.ok(!L.memeOnglet(0, 0, { l: 1, h: 1 }));
const nn = (tag, role, parent) => ({ tagName: tag, getAttribute: (k) => (k === "role" ? role : null), parentElement: parent || null });
const bt = nn("BUTTON", null), sp = nn("SPAN", null, bt);
assert.equal(L.cliquable(sp), bt, "remonte au bouton");
const onglet = nn("DIV", "tab");
assert.equal(L.cliquable(nn("I", null, onglet)), onglet, "rôle d'onglet");
assert.equal(L.cliquable(nn("DIV", null, nn("DIV", null))), null, "rien de cliquable : null");
assert.equal(L.cliquable(null), null);
let profond = bt;
for (let i = 0; i < 7; i++) profond = nn("SPAN", null, profond);
assert.equal(L.cliquable(profond), null, "6 niveaux au plus");
assert.equal(L.prix(0.01234, "fr"), "0,0123");
assert.equal(L.prix(0.01234, "en"), "0.0123");
assert.equal(L.prix("x", "fr"), "0,0000");
assert.deepEqual(L.etapes({ type: "voir", cible: "ecran" }, "quick"), [{ faire: "voir" }]);
assert.deepEqual(L.etapes({ type: "point_xy", x: 1, y: 2, largeur: 10, hauteur: 10 }, "quick"), [{ faire: "pointer_xy" }]);
assert.deepEqual(L.etapes({ type: "point_xy", x: "a", y: 2 }, "quick"), [], "coordonnées douteuses : rien");

// C4 — relevé des éléments visibles (faux document) : libellés des contrôles seulement, jamais le contenu
const fauxDoc = (els) => ({ querySelectorAll: () => els });
const n = (t, title, w = 10, vis = true, o = {}) => {
  const attrs = { title, role: o.role, href: o.href, placeholder: o.placeholder, "aria-label": o.aria };
  return {
    tagName: o.tag || "BUTTON", textContent: t, innerText: o.innerText, isContentEditable: !!o.editable,
    getAttribute: (a) => (attrs[a] == null ? null : attrs[a]),
    closest: (q) => ((q === "nav" && o.nav) || (q === "[data-dz-agent-ignorer]" && o.ignorer) ? {} : null),
    getBoundingClientRect: () => {
      const x = o.x ?? 0, y = o.y ?? 0, l = vis ? w : 0, h = vis ? 10 : 0;
      return { width: l, height: h, left: x, top: y, right: x + l, bottom: y + h };
    },
    style: o.style || {},
  };
};
const rel = L.releverVisibles(fauxDoc([n("Rendre", "Rendu final"), n("Rendre", "Rendu final"), n("caché", "", 10, false),
  n("  a\n b  ", ""), n("", ""), n("x".repeat(200), "")]));
assert.deepEqual(rel, [{ t: "Rendre", i: "Rendu final" }, { t: "a", i: "" }],
  "doublon, invisible, vide et texte long écartés ; première ligne non vide");
assert.equal(L.releverVisibles(fauxDoc(Array.from({ length: 300 }, (_, k) => n("b" + k, "")))).length, L.MAX_VISIBLES);
assert.deepEqual(L.releverVisibles(fauxDoc([n("moi", "")]), () => true), [], "exclure() écarte le tiroir");
// vie privée : un champ ne donne jamais son texte, seulement son infobulle / aria-label / placeholder
assert.deepEqual(L.releverVisibles(fauxDoc([n("secret de l'utilisateur", "Narration", 10, true, { tag: "TEXTAREA" })])),
  [{ t: "", i: "Narration" }]);
assert.deepEqual(L.releverVisibles(fauxDoc([n("secret", null, 10, true, { tag: "TEXTAREA", placeholder: "Ton texte" })])),
  [{ t: "", i: "Ton texte" }]);
assert.deepEqual(L.releverVisibles(fauxDoc([n("secret de l'utilisateur", null, 10, true, { tag: "INPUT" }),
  n("secret", null, 10, true, { tag: "SELECT" }), n("secret", null, 10, true, { tag: "DIV", editable: true })])), [],
  "champ sans infobulle : rien");
// libellé collé : la première ligne de innerText
assert.deepEqual(L.releverVisibles(fauxDoc([n("QuickGénérateurs en un clic", "", 10, true,
  { innerText: "Quick\nGénérateurs en un clic" })])), [{ t: "Quick", i: "" }]);
// plus de 40 caractères : du contenu, pas un libellé (l'infobulle reste)
assert.deepEqual(L.releverVisibles(fauxDoc([n("y".repeat(60), "Bloc 3", 10, true, { innerText: "y".repeat(60) })])),
  [{ t: "", i: "Bloc 3" }]);
// pas un contrôle (div [title]) : jamais de texte
assert.deepEqual(L.releverVisibles(fauxDoc([n("Sous la surface", "Piste voix", 10, true,
  { tag: "DIV", innerText: "Sous la surface" })])), [{ t: "", i: "Piste voix" }]);
// contrôles par rôle et liens : le texte est gardé
assert.deepEqual(L.releverVisibles(fauxDoc([n("Onglet", "", 10, true, { tag: "DIV", role: "tab", innerText: "Onglet" }),
  n("Lien", "", 10, true, { tag: "A", href: "#x", innerText: "Lien" }),
  n("Ancre", "", 10, true, { tag: "A", innerText: "Ancre" })])).map((x) => x.t), ["Onglet", "Lien"]);
// le rail (nav) est exclu
assert.deepEqual(L.releverVisibles(fauxDoc([n("Quick", "", 10, true, { nav: true })])), [], "rail exclu");
// vie privée : une zone marquée [data-dz-agent-ignorer] (grille de fichiers…) est exclue
assert.deepEqual(L.releverVisibles(fauxDoc([n("photo_vacances.png", "", 10, true, { ignorer: true }), n("Ok", "")])),
  [{ t: "Ok", i: "" }], "zone ignorée exclue");
// M4 : seulement ce qui est DANS la fenêtre, et pas visibility:hidden (faux defaultView)
const vueDoc = (els, style = () => ({ visibility: "visible" })) =>
  ({ querySelectorAll: () => els, defaultView: { innerWidth: 800, innerHeight: 600, getComputedStyle: style } });
assert.deepEqual(L.releverVisibles(vueDoc([n("Dedans", "", 10, true, { x: 100, y: 100 }),
  n("Dessous", "", 10, true, { x: 100, y: 900 }), n("Dessus", "", 10, true, { x: 100, y: -50 }),
  n("Droite", "", 10, true, { x: 850, y: 100 }), n("Gauche", "", 10, true, { x: -30, y: 100 }),
  n("Bord", "", 10, true, { x: 795, y: 595 })])).map((x) => x.t), ["Dedans", "Bord"], "hors fenêtre écartés");
assert.deepEqual(L.releverVisibles(vueDoc([n("Caché", "", 10, true, { style: { visibility: "hidden" } }), n("Vu", "")],
  (x) => x.style)).map((x) => x.t), ["Vu"], "visibility:hidden écarté");
assert.deepEqual(L.releverVisibles(fauxDoc([n("Loin", "", 10, true, { x: 5000, y: 5000 })])).map((x) => x.t), ["Loin"],
  "sans defaultView : pas de filtre de fenêtre");
assert.deepEqual(L.releverVisibles({ querySelectorAll: () => { throw new Error("x"); } }), []);

// 6. le module n'utilise aucun objet du navigateur à l'import
assert.equal(typeof globalThis.document, "undefined");
console.log("agent_logique : OK");
