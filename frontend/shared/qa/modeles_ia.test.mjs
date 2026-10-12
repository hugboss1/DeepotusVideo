// t183 (G1) — DzModelesIA : groupes par voie, prix (règle unique), options sans clé VISIBLES ET CHOISISSABLES
// (décision de l'utilisateur, 11/10/2026), modèles vectoriels hors des sélecteurs raster, replis.
// Lancer : node frontend/shared/qa/modeles_ia.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("../dz-modeles-ia.js", import.meta.url), "utf8");
const J = (x) => JSON.parse(JSON.stringify(x));   // valeurs nées dans le contexte vm : autre royaume
const MODS = [
  { id: "gpt-image-2", label: "GPT Image 2", voie: "openai", cle: "OPENAI_API_KEY", dispo: false, usd: 0.12, unite: "image", sortie: "raster" },
  { id: "gpt-image-2-fal", label: "GPT Image 2 (via fal)", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0.145, unite: "image", sortie: "raster" },
  { id: "ideogram-4.5", label: "Ideogram 4.5", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0, unite: "image", note: "a_mesurer", sortie: "raster" },
  { id: "inconnu-x", label: "Modèle X", voie: "nouvelle-voie", cle: "X_KEY", dispo: true, usd: 0.04, unite: "image", sortie: "raster" },
  { id: "recraft-4.1-vecteur", label: "Recraft 4.1 (SVG)", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0.08, unite: "image", sortie: "svg" },
];
function monde(dzT, fetchImpl) {
  const ctx = { window: { fetch: fetchImpl } };
  if (dzT) ctx.window.dzT = dzT;
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return ctx.window.DzModelesIA;
}
const APPELS = [];
const ok = (url) => { APPELS.push(String(url)); return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ modeles: MODS }) }); };
// dictionnaire présent : un dzT qui TRADUIT (préfixe « EN: » pour le voir)
const EN = (k, v) => "EN:" + k + (v ? JSON.stringify(v) : "");
const M = monde(EN, ok);
assert.ok(M, "window.DzModelesIA posé");

// [1] groupes : fal d'abord, l'ordre ORDRE, une voie inconnue en DERNIER
const g = M.grouper(MODS.slice(0, 4));
assert.deepEqual(J(g.map((x) => x.voie)), ["fal", "openai", "nouvelle-voie"]);
assert.equal(g[0].titre, "EN:ia.voie.fal");
assert.equal(M.rang("fal"), 0); assert.equal(M.rang("nouvelle-voie"), 99); assert.equal(M.rang(undefined), 99);
// [2] clé absente : visible ET choisissable, avec la mention
assert.equal(g.every((x) => x.options.every((o) => o.desactive === false)), true, "aucune option désactivée");
assert.match(g[1].options[0].texte, /EN:ia\.cle\.a_ajouter\{"cle":"OPENAI_API_KEY"\}/);
assert.doesNotMatch(g[0].options[0].texte, /a_ajouter/, "TÉMOIN : une option servie n'a pas la mention");
// [3] la règle de prix UNIQUE : $, millième, zéros de fin retirés mais deux décimales, unité, sans langue
assert.equal(M.prixUsd(0.145, "image"), "$0.145/image");
assert.equal(M.prixUsd(0.04, "image"), "$0.04/image");
assert.equal(M.prixUsd(0.003, "image"), "$0.003/image");
assert.equal(M.prixUsd(0.22, "image"), "$0.22/image");
assert.equal(M.prixUsd(0.6, "min"), "$0.60/min");
assert.equal(M.prixUsd(0.0475, "s"), "$0.048/s");
assert.equal(M.prixUsd(0.24, "1k"), "$0.24/1k");
assert.equal(M.prixUsd(1.5), "$1.50");
for (const nul of [0, null, undefined, "x", -1, NaN]) assert.equal(M.prixUsd(nul, "image"), "", String(nul));
assert.equal(M.prix(0, "image"), "EN:ia.prix.a_mesurer");
assert.match(g[0].options[0].texte, /\$0\.145\/image/);
assert.match(g[0].options[1].texte, /EN:ia\.prix\.a_mesurer/);
assert.doesNotMatch(JSON.stringify(J(g)), /gratuit|free/i);
// [4] filtre raster
assert.deepEqual(J(M.filtrer(MODS).map((m) => m.id)), ["gpt-image-2", "gpt-image-2-fal", "ideogram-4.5", "inconnu-x"]);
assert.equal(M.filtrer(MODS, { vectoriel: true }).length, 5);
// [5] valeur initiale
const r = M.filtrer(MODS);
assert.equal(M.valeurInitiale(r, "gpt-image-2"), "gpt-image-2");
assert.equal(M.valeurInitiale(r, "absent"), "gpt-image-2-fal");
assert.equal(M.valeurInitiale([], "x"), "");

// [6] select() sur un faux <select>
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
assert.equal(rendus.length, 4, "le vectoriel est écarté");
assert.deepEqual(J(sel.children.map((og) => og.label)), ["EN:ia.voie.fal", "EN:ia.voie.openai", "EN:ia.voie.nouvelle-voie"]);
assert.equal(sel.options().some((o) => o.disabled), false, "NÉGATIF : aucune <option> disabled");
assert.equal(sel.options().find((o) => o.value === "gpt-image-2").attrs["data-sans-cle"], "1");
assert.equal(sel.value, "gpt-image-2", "un modèle sans clé reste la valeur choisie");
// M9 : l'écouteur relit la liste COURANTE (posée sur l'élément) — un second remplir la remplace
const nouvelle = [{ id: "seul", label: "Seul", voie: "fal", dispo: true, usd: 0.01, unite: "image" }];
assert.equal(M.remplir(sel, nouvelle, { valeur: "absent" }), "seul", "remplir rend la valeur retenue");
sel.ecoute.change.forEach((f) => f());
assert.deepEqual(J(vu), ["seul", "seul"]);
assert.equal(sel.ecoute.change.length, 1, "un seul écouteur, même après plusieurs select()");

// [7] M8 : un catalogue injoignable (ok:false) REJETTE et laisse le <select> intact
const Mko = monde(EN, () => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }));
const sel2 = new Noeud("select");
sel2.appendChild(new Noeud("option"));
let rejet = null;
try { await Mko.select(sel2, "image", {}); } catch (e) { rejet = String(e.message); }
assert.match(rejet || "", /catalogue image : 500/);
assert.equal(sel2.children.length, 1, "le <select> n'est pas vidé");

// [8] M4 : sans dictionnaire (ni dzT, ni clé assemblée) : les replis français
const Mfr = monde(null, ok);
assert.equal(Mfr.prix(0, "image"), "prix à mesurer");
assert.equal(Mfr.grouper(MODS.slice(0, 2))[0].titre, "via la clé fal");
assert.match(Mfr.texte(MODS[0]), /clé OPENAI_API_KEY à ajouter dans Réglages/);
const Mcle = monde((k) => k, ok);                 // dzT présent mais clé absente : il rend la clé
assert.equal(Mcle.prix(null, "image"), "prix à mesurer");
assert.equal(Mcle.grouper(MODS.slice(0, 1))[0].titre, "avec votre clé OpenAI");
// et aucune dépendance à dzLang : le prix ne change pas de forme selon la langue
assert.equal(Mfr.prixUsd(0.145, "image"), M.prixUsd(0.145, "image"));
// [9] t186 (G4) : unités du détourage vidéo par tranche d'images ; une option LOCALE sans prix est gratuite pour de
// vrai (son groupe le dit) : ni prix ni « à mesurer » — une voie fal à 0 garde « à mesurer »
assert.equal(M.prixUsd(0.012, "30 images"), "$0.012/30 images");
assert.equal(M.prixUsd(0.01, "16 images"), "$0.01/16 images");
assert.equal(Mfr.texte({ id: "local-rembg", label: "rembg", voie: "local", usd: 0, unite: "image", dispo: true }), "rembg");
assert.equal(Mfr.texte({ id: "pixelcut", label: "Pixelcut", voie: "fal", usd: 0, unite: "image", dispo: true }), "Pixelcut · prix à mesurer");
assert.equal(Mfr.texte({ id: "veed", label: "VEED", voie: "fal", usd: 0.012, unite: "30 images", dispo: false, cle: "FAL_KEY" }),
  "VEED · $0.012/30 images · clé FAL_KEY à ajouter dans Réglages");

// [10] t186 : le nom traduit par detour.modele.<id> quand le dictionnaire de la page la porte, sinon le libellé servi
const Mdico = (() => { const ctx = { window: { fetch: ok, dzT: (k) => "EN:" + k, DZ_I18N: { "detour.modele.sam3_sujet": {} } } };
  vm.createContext(ctx); vm.runInContext(src, ctx); return ctx.window.DzModelesIA; })();
assert.equal(Mdico.libelle({ id: "sam3-sujet", label: "SAM 3 — garder un sujet nommé" }), "EN:detour.modele.sam3_sujet");
assert.equal(Mdico.libelle({ id: "pixelcut", label: "Pixelcut" }), "Pixelcut");
console.log("modeles_ia ok");
