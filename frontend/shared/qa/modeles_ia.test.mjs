// t183 (G1) — DzModelesIA : groupes par voie, prix, options sans clé VISIBLES ET CHOISISSABLES
// (décision de l'utilisateur, 11/10/2026), modèles vectoriels hors des sélecteurs raster.
// Lancer : node frontend/shared/qa/modeles_ia.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("../dz-modeles-ia.js", import.meta.url), "utf8");
let LANG = "fr";
const APPELS = [];
const ctx = { window: { dzT: (k, v) => k + (v ? JSON.stringify(v) : ""), dzLang: () => LANG } };
ctx.window.fetch = (url) => {
  APPELS.push(String(url));
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ modeles: MODS }) });
};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const M = ctx.window.DzModelesIA;
const J = (x) => JSON.parse(JSON.stringify(x));   // valeurs nées dans le contexte vm : autre royaume
assert.ok(M, "window.DzModelesIA posé");

const MODS = [
  { id: "gpt-image-2", label: "GPT Image 2", voie: "openai", cle: "OPENAI_API_KEY", dispo: false, usd: 0.12, unite: "image", jumeau: "gpt-image-2-fal", sortie: "raster" },
  { id: "gpt-image-2-fal", label: "GPT Image 2 (via fal)", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0.145, unite: "image", jumeau: "gpt-image-2", sortie: "raster" },
  { id: "ideogram-4.5", label: "Ideogram 4.5", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0, unite: "image", jumeau: null, note: "a_mesurer", sortie: "raster" },
  { id: "recraft-4.1-vecteur", label: "Recraft 4.1 (SVG)", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0.08, unite: "image", sortie: "svg" },
];

// [1] groupes : fal d'abord, puis l'ordre ORDRE
const g = M.grouper(MODS.slice(0, 3));
assert.deepEqual(J(g.map((x) => x.voie)), ["fal", "openai"]);
assert.equal(g[0].titre, "ia.voie.fal");
// [2] clé absente : visible ET choisissable, avec la mention
assert.equal(g[1].options[0].desactive, false);
assert.equal(g.every((x) => x.options.every((o) => o.desactive === false)), true, "aucune option désactivée");
assert.match(g[1].options[0].texte, /ia\.cle\.a_ajouter\{"cle":"OPENAI_API_KEY"\}/);
assert.doesNotMatch(g[0].options[0].texte, /a_ajouter/, "TÉMOIN : une option servie n'a pas la mention");
// [3] prix : format FR, inconnu = « à mesurer », jamais « gratuit »
assert.match(g[0].options[0].texte, /0,145 \$/);
assert.match(g[0].options[1].texte, /ia\.prix\.a_mesurer/);
assert.doesNotMatch(JSON.stringify(g), /gratuit|free/i);
assert.equal(M.prix(0.0475, "s"), "0,048 $/s");
assert.equal(M.prix(0.6, "min"), "0,6 $/min");
LANG = "en";
assert.equal(M.prix(0.145, "image"), "$0.145");
LANG = "fr";
// [4] filtre raster : le vectoriel n'est jamais dans un sélecteur raster (exception gardée de t182)
assert.deepEqual(J(M.filtrer(MODS).map((m) => m.id)), ["gpt-image-2", "gpt-image-2-fal", "ideogram-4.5"]);
assert.equal(M.filtrer(MODS, { vectoriel: true }).length, 4);
// [5] valeur initiale : la demandée même sans clé, sinon la première disponible
const r = M.filtrer(MODS);
assert.equal(M.valeurInitiale(r, "gpt-image-2"), "gpt-image-2");
assert.equal(M.valeurInitiale(r, "absent"), "gpt-image-2-fal");
assert.equal(M.valeurInitiale(r, ""), "gpt-image-2-fal");
assert.equal(M.valeurInitiale([], "x"), "");

// [6] select() sur un faux <select> : optgroups, options jamais disabled, lecture du catalogue
class Noeud {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.attrs = {}; this.disabled = false; this.ecoute = {}; this.ownerDocument = DOC; }
  set textContent(v) { if (v === "") this.children = []; this._t = v; }
  get textContent() { return this._t || ""; }
  appendChild(c) { this.children.push(c); return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener(t, f) { (this.ecoute[t] = this.ecoute[t] || []).push(f); }
  options() { return this.children.flatMap((og) => og.children); }
  set value(v) { this._v = this.tagName !== "SELECT" || this.options().some((o) => o.value === v) ? v : ""; }
  get value() { return this._v || ""; }
}
const DOC = { createElement: (t) => new Noeud(t) };
const sel = new Noeud("select");
let vu = null;
const rendus = await M.select(sel, "image", { valeur: "gpt-image-2", onChange: (v, m) => { vu = [v, m && m.id]; } });
assert.deepEqual(J(APPELS), ["/api/ia/catalogue?nature=image"]);
assert.equal(rendus.length, 3, "le vectoriel est écarté");
assert.deepEqual(J(sel.children.map((og) => og.label)), ["ia.voie.fal", "ia.voie.openai"]);
assert.equal(sel.options().length, 3);
assert.equal(sel.options().some((o) => o.disabled), false, "NÉGATIF : aucune <option> disabled");
assert.equal(sel.options().find((o) => o.value === "gpt-image-2").attrs["data-sans-cle"], "1");
assert.equal(sel.value, "gpt-image-2", "un modèle sans clé reste la valeur choisie");
sel.value = "ideogram-4.5";
sel.ecoute.change.forEach((f) => f());
assert.deepEqual(J(vu), ["ideogram-4.5", "ideogram-4.5"]);

console.log("modeles_ia ok");
