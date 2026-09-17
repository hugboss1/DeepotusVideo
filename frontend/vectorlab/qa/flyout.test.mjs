// flyout.test.mjs — mod-flyout : les menus détachés de la barre d'outils —
// entrées du menu Forme (la courante marquée, un glyphe par forme), du menu
// Symboles (état vide dit), position à droite du bouton bornée à la fenêtre.
import { flyout_formes, flyout_symboles, flyout_position } from "../js/mod-flyout.js";
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
if (echecs.length) {
  console.error("ECHECS flyout :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA flyout : PASS (7 controles)");
