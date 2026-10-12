// noms_bruts.test.mjs — un nom donné par l'utilisateur n'est JAMAIS traduit par la surcouche de /shared/dz-i18n.js.
// Défaut vu aux captures du guide (12/10, dz_lang = "en") : un calque nommé « Fond » s'affichait « Fill », parce
// que « Fond » est aussi le français d'une entrée du dictionnaire. Le VRAI runtime (dictionnaire compris) tourne
// sous node avec un observateur factice ; chaque libellé de nom est rebâti avec les attributs que la SOURCE du
// module lui donne (balise ouvrante relevée dans le fichier), puis reçoit « Fond » : il doit rester « Fond ».
// Le témoin, même balise SANS data-dz-brut, devient « Fill » : le défaut est bien reproduit.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { flyout_symboles } from "../js/mod-flyout.js";

const ici = dirname(fileURLToPath(import.meta.url));
const lab = join(ici, "..");
const partage = join(lab, "..", "shared");
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };

// ── le runtime réel, en anglais, avec un MutationObserver factice dont on garde le rappel ──
let rappel = null;
function MO(cb) { rappel = cb; }
MO.prototype.observe = function () {};
const fenetre = { location: { reload() {} },
  localStorage: { getItem: (k) => (k === "dz_lang" ? "en" : null), setItem() {} },
  fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({ ui_lang: "en" }) }) };
const doc = { documentElement: { lang: "en" }, readyState: "loading", addEventListener() {} };
new Function("window", "document", "localStorage", "MutationObserver", "Node",
  readFileSync(join(partage, "dz-i18n-dico.js"), "utf8") + "\n" + readFileSync(join(partage, "dz-i18n.js"), "utf8")
  + "\n;return window;")(fenetre, doc, fenetre.localStorage, MO, { TEXT_NODE: 3, ELEMENT_NODE: 1 });
ok("le runtime pose sa surcouche en anglais", typeof rappel === "function");

// un élément factice aux attributs donnés, un nœud texte dedans ; la surcouche voit un characterData
function afficher(nodeName, attrs, texte) {
  const el = { nodeType: 1, nodeName, parentNode: null, isContentEditable: false, attrs: { ...attrs },
    hasAttribute(k) { return k in this.attrs; }, getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = v; } };
  const n = { nodeType: 3, data: texte, parentNode: el };
  if (rappel) rappel([{ type: "characterData", target: n }]);
  return n.data;
}
const attrsDe = (balise) => {
  const out = {};
  for (const m of balise.matchAll(/([\w-]+)="/g)) out[m[1]] = "";
  return out;
};
const source = (f) => readFileSync(join(lab, f), "utf8");

// témoin : le défaut existe bien (sinon ce banc ne prouverait rien)
ok("témoin : « Fond » sans data-dz-brut devient « Fill »", afficher("SPAN", { class: "" }, "Fond") === "Fill",
   afficher("SPAN", { class: "" }, "Fond"));

// ── les libellés en gabarit HTML : [fichier, motif de la balise ouvrante qui porte le nom, nombre attendu] ──
const GABARITS = [
  ["js/mod-layers.js", /<span class="nom"[^>]*>(?=\$\{esc\(r\.nom\)\}<\/span>)/g, 2, "calque / objet du panneau Calques"],
  ["js/mod-planches.js", /<span class="nom"[^>]*>(?=\$\{esc\(p\.nom\)\}<\/span>)/g, 1, "planche"],
  ["js/mod-apparence2.js", /<b style="flex:1"[^>]*>(?=\$\{esc\(n\)\}<\/b>)/g, 2, "couleur globale / style"],
  ["js/mod-biblio.js", /<div class="bib-nom"[^>]*>(?=\$\{esc\(d\.name\)\}<\/div>)/g, 1, "document"],
  ["js/mod-outils2.js", /<span class="nom"[^>]*>(?=\$\{n\}<\/span>)/g, 1, "instantané"],
];
for (const [f, motif, attendu, quoi] of GABARITS) {
  const balises = source(f).match(motif) || [];
  ok(`${f} : ${attendu} libellé(s) de nom (${quoi})`, balises.length === attendu, balises.length);
  for (const b of balises) {
    const nom = /^<(\w+)/.exec(b)[1].toUpperCase();
    ok(`${f} : « Fond » reste « Fond » (${quoi}) — ${b}`, afficher(nom, attrsDe(b), "Fond") === "Fond");
  }
}

// ── les étiquettes posées par setAttribute / ov({…}) sur la page ──
const core = source("js/core.js");
for (const cls of ["planche-nom", "page-nom"]) {
  const m = new RegExp(`ov\\("text", \\{[^}]*class: "${cls}"[^}]*\\}`).exec(core);
  const attrs = {};
  if (m) for (const a of m[0].matchAll(/"?([\w-]+)"?: /g)) attrs[a[1]] = "";
  ok(`core.js : étiquette ${cls} — « Fond » reste « Fond »`, !!m && afficher("text", attrs, "Fond") === "Fond", m && m[0]);
}
ok("mod-exportplus.js : étiquette d'une tranche marquée data-dz-brut avant son texte",
   /l\.setAttribute\("data-dz-brut", "1"\); l\.textContent = t\.nom;/.test(source("js/mod-exportplus.js")));

// ── le menu Symboles : l'entrée porte `brut`, le menu le rend sur .fo-lib ──
const ent = flyout_symboles({ s1: { nom: "Fond", objets: [] } });
ok("flyout_symboles : un symbole nommé est une entrée brute", ent[0] && ent[0].libelle === "Fond" && ent[0].brut === true, JSON.stringify(ent[0]));
ok("flyout_symboles : « Créer depuis la sélection » reste traduisible", ent.some((e) => e.action === "creer" && !e.brut));
const fo = /<span class="fo-lib"\$\{e\.brut \? ' data-dz-brut="1"' : ""\}>/.test(source("js/mod-flyout.js"));
ok("mod-flyout.js : .fo-lib porte data-dz-brut quand l'entrée est brute", fo);
ok("menu : « Fond » d'une entrée brute reste « Fond »", afficher("SPAN", { class: "", "data-dz-brut": "1" }, "Fond") === "Fond");

if (echecs.length) {
  console.error("noms_bruts : " + echecs.length + " échec(s)\n  " + echecs.join("\n  "));
  process.exit(1);
}
console.log("noms_bruts : ok");
