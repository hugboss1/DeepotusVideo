// flyout.test.mjs — mod-flyout : les menus détachés de la barre d'outils —
// entrées du menu Forme (la courante marquée, un glyphe par forme), du menu
// Symboles (état vide dit), position à droite du bouton bornée à la fenêtre.
import { flyout_formes, flyout_symboles, flyout_position, flyout_choix, flyout_presets, flyout_terrains, flyout_polices, flyout_actions, flyout_reglages, MENUS } from "../js/mod-flyout.js";
import { FORMES } from "../js/mod-formes.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
{
  const f = flyout_formes(FORMES, "etoile");
  ok("formes : une entrée par forme, id/libellé/glyphe, la courante marquée", f.length === FORMES.length && f.every((x) => x.id && x.libelle && x.glyphe) && f.find((x) => x.id === "etoile").actif === true && f.filter((x) => x.actif).length === 1, JSON.stringify(f[2]));
  ok("courante inconnue : aucune marquée", flyout_formes(FORMES, "zz").every((x) => !x.actif));
  const s = flyout_symboles({ s1: { nom: "pion", objets: [1, 2] }, s2: { nom: "tour", objets: [1] } });
  ok("symboles : une entrée par symbole avec le nombre d'objets, puis « créer depuis la sélection »", s.length === 3 && s[0].id === "s1" && s[0].libelle.includes("pion") && s[0].detail === "2 objets" && s[2].action === "creer", JSON.stringify(s));
  ok("état vide : sans symbole → l'entrée « aucun symbole » désactivée puis « créer »", (() => { const v = flyout_symboles({}); return v.length === 2 && v[0].desactive === true && v[1].action === "creer"; })() && flyout_symboles(undefined).length === 2);
  const p = flyout_position({ x: 8, y: 100, w: 38, h: 38 }, { w: 160, h: 220 }, { w: 1400, h: 900 }, 6);
  ok("position : à droite du bouton, aligné en haut", p.x === 8 + 38 + 6 && p.y === 100, JSON.stringify(p));
  const b = flyout_position({ x: 8, y: 800, w: 38, h: 38 }, { w: 160, h: 220 }, { w: 1400, h: 900 }, 6);
  ok("borné en bas : le menu remonte pour tenir dans la fenêtre", b.y === 900 - 6 - 220, JSON.stringify(b));
  ok("borné à droite : passe à gauche du bouton s'il ne tient pas", flyout_position({ x: 1300, y: 100, w: 38, h: 38 }, { w: 160, h: 100 }, { w: 1400, h: 900 }, 6).x === 1300 - 6 - 160);
}
/* ── les autres sections ── */
{
  const c = flyout_choix([{ id: "a", nom: "Alpha" }, { id: "b", nom: "Beta" }], "b", { glyphes: { a: "①" } });
  ok("choix : une entrée par valeur, la courante marquée, glyphe optionnel", c.length === 2 && c[1].actif === true && c[0].glyphe === "①" && c[1].glyphe === "" && c[0].libelle === "Alpha" && c[0].id === "a", JSON.stringify(c));
  const p = flyout_presets([4, 8, 16], 8, "px");
  ok("presets : valeurs avec unité, la courante marquée, ids numériques", p.length === 3 && p[1].actif === true && p[1].libelle === "8 px" && p[2].valeur === 16, JSON.stringify(p));
  ok("presets : courante hors liste → ajoutée en tête marquée", (() => { const q = flyout_presets([4, 8], 5, "px"); return q.length === 3 && q[0].valeur === 5 && q[0].actif; })());
  const t = flyout_terrains({ mer: { nom: "Mer", couleur: "#2B5F9E", hauteur_mm: 0 }, plaine: { nom: "Plaine", couleur: "#7FB069", hauteur_mm: 2 } }, "plaine");
  ok("terrains : pastille de couleur, nom, hauteur en détail, le courant marqué", t.length === 2 && t[1].actif && t[0].couleur === "#2B5F9E" && t[1].detail === "2 mm" && t[0].id === "mer", JSON.stringify(t));
  ok("état vide : sans terrain → []", flyout_terrains({}, "x").length === 0);
  const f = flyout_polices([{ id: "lib:a", famille: "Anton", source: "lib" }, { id: "user:b.ttf", famille: "B", source: "user" }], "Anton");
  ok("polices : une entrée par police rendue dans sa famille, la courante marquée, source en détail", f.length === 2 && f[0].actif && f[0].famille === "Anton" && f[1].detail === "déposée" && f[0].detail === "bibliothèque", JSON.stringify(f));
  const a = flyout_actions([{ id: "x", libelle: "X", cible: "#x" }, { id: "y", libelle: "Y", cible: "#y" }], (cible) => cible === "#x");
  ok("actions : disponible = la cible existe, sinon désactivée", a[0].desactive === false && a[1].desactive === true && a[1].action === "cible");
  ok("registre : un bâtisseur par outil à menu, les 18 outils attendus", ["select", "noeuds", "texte", "crayon", "pinceauv", "gomme", "coin", "tuiles", "forme", "symbole", "px-pinceau", "px-gomme", "px-seau", "px-baguette", "px-selrect", "px-lasso", "tranche"].every((k) => typeof MENUS[k] === "function"), Object.keys(MENUS).join(","));
}
/* ── Image et Apparence ── */
{
  const r = flyout_reglages([1, 2, 4, 8], 2, "epaisseur", "px");
  ok("réglages : une entrée par valeur avec son patch de style, la courante marquée", r.length === 4 && r[1].actif && JSON.stringify(r[2].patch) === '{"epaisseur":4}' && r[0].libelle === "1 px" && r[0].action === "style", JSON.stringify(r));
  ok("réglages : opacité en pourcentage → patch en fraction", (() => { const o = flyout_reglages([100, 50], 100, "opacite", "%", (v) => v / 100); return o[1].patch.opacite === 0.5 && o[0].actif; })());
  ok("registre : menus image et apparence", typeof MENUS.image === "function" && typeof MENUS.apparence === "function");
}
if (echecs.length) {
  console.error("ECHECS flyout :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA flyout : PASS (18 controles)");
