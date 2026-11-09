// t476 (lot F1 « Fiches modèle ») — DzFicheModele : rendu markdown ÉCHAPPÉ, index chargé une fois, « ? » montré
// seulement quand le modèle choisi a une fiche, panneau (titre, erreur, Échap), et le branchement de DzModelesIA.
// Lancer : node frontend/shared/qa/fiche_modele.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-fiche-modele.js", import.meta.url), "utf8");
const SRC_MI = readFileSync(new URL("../dz-modeles-ia.js", import.meta.url), "utf8");
const attendre = () => new Promise((r) => setTimeout(r, 0));

/* ---- un faux DOM, juste ce que le script touche ---- */
function el(tag) {
  const e = {
    tagName: tag, children: [], parentNode: null, attrs: {}, ecoute: {}, hidden: false, textContent: "", innerHTML: "",
    className: "", style: {},
    setAttribute(k, v) { this.attrs[k] = String(v); }, getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    addEventListener(t, f) { (this.ecoute[t] = this.ecoute[t] || []).push(f); },
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    insertBefore(c, ref) { c.parentNode = this; const i = ref ? this.children.indexOf(ref) : -1; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; },
    removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; return c; },
    get nextSibling() { const p = this.parentNode; if (!p) return null; const i = p.children.indexOf(this); return p.children[i + 1] || null; },
    focus() { doc.focused = this; },
    declencher(t, ev = {}) { (this.ecoute[t] || []).forEach((f) => f({ preventDefault() {}, stopPropagation() {}, ...ev })); },
  };
  return e;
}
const doc = {
  focused: null, ecoute: {}, head: el("head"), body: el("body"),
  createElement: (t) => el(t),
  getElementById(id) { return this.head.children.find((c) => c.id === id) || null; },
  addEventListener(t, f) { (this.ecoute[t] = this.ecoute[t] || []).push(f); },
  removeEventListener(t, f) { this.ecoute[t] = (this.ecoute[t] || []).filter((x) => x !== f); },
};
const APPELS = [];
let ficheRep = { ok: true, status: 200, json: () => Promise.resolve({ famille: "essai", releve: "2026-11-09",
  texte: "## Aperçu\n\nTexte.\n\n## Membres\n\n| id | prix |\n|---|---|\n| seedance-2 | $0.3/s |", commun: "## Aperçu\n\n- Règle." }) };
function fetchStub(url) {
  APPELS.push(String(url));
  if (String(url).startsWith("/api/modeles/index")) {
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ familles: [], ids: { "seedance-2": "essai" } }) });
  }
  return Promise.resolve(ficheRep);
}
const W = { document: doc, fetch: fetchStub, dzLang: () => "en" };
const ctx = { window: W };
vm.createContext(ctx);
vm.runInContext(SRC, ctx);
const F = W.DzFicheModele;
assert.ok(F, "window.DzFicheModele posé");

// [1] rendu : titres, puces, tableau, code, gras — et TOUT texte échappé
const h = F.rendre("## Titre <i>\n\n- a `x`\n- **b** <script>alert(1)</script>\n  suite\n\n| id | p |\n|---|---|\n| s | <b>1</b> |\n\nPara & <img src=x>");
assert.match(h, /<h3>Titre &lt;i&gt;<\/h3>/);
assert.match(h, /<ul><li>a <code>x<\/code><\/li><li><strong>b<\/strong> &lt;script&gt;alert\(1\)&lt;\/script&gt; suite<\/li><\/ul>/);
assert.match(h, /<table><thead><tr><th>id<\/th><th>p<\/th><\/tr><\/thead><tbody><tr><td>s<\/td><td>&lt;b&gt;1&lt;\/b&gt;<\/td><\/tr><\/tbody><\/table>/);
assert.match(h, /<p>Para &amp; &lt;img src=x&gt;<\/p>/);
assert.doesNotMatch(h, /<script|<img|<b>|<i>/, "aucune balise venue du texte");
assert.equal(F.rendre(""), "");

// [2] index : chargé UNE fois, dans la langue de l'interface ; famille d'un id
assert.equal(await F.familleDe("seedance-2"), "essai");
assert.equal(await F.familleDe("autre"), null);
assert.deepEqual(APPELS.filter((u) => u.startsWith("/api/modeles/index")), ["/api/modeles/index?langue=en"]);

// [3] le « ? » : posé APRÈS le <select>, caché sans fiche, montré avec, suit le change ; une seule fois
const boite = el("div");
const sel = el("select"); sel.value = "autre";
boite.appendChild(sel);
const apres = el("span"); boite.appendChild(apres);       // un frère APRÈS le select : le « ? » se glisse entre
const b = F.bouton(sel);
assert.equal(boite.children[1], b, "juste après le select");
assert.equal(b.hidden, true);
await attendre(); await attendre();
assert.equal(b.hidden, true, "« autre » n'a pas de fiche : caché");
sel.value = "seedance-2"; sel.declencher("change");
await attendre(); await attendre();
assert.equal(b.hidden, false, "seedance-2 a une fiche : montré");
assert.equal(F.bouton(sel), b, "pas de second bouton");
assert.equal(boite.children.length, 3);
assert.equal(boite.children[2], apres);
assert.equal(b.getAttribute("aria-label"), "Fiche du modèle", "repli français sans dictionnaire");

// [4] le panneau : dialogue, titre, rendu, tronc commun replié, Échap ferme et rend le focus
b.declencher("click");
const p = doc.body.children.find((c) => c.className === "dz-fiche-modele");
assert.ok(p, "panneau posé");
assert.equal(p.getAttribute("role"), "dialog");
await attendre(); await attendre(); await attendre();
assert.ok(APPELS.includes("/api/modeles/fiche?cle=seedance-2&langue=en"));
const corps = p.children.find((c) => c.className === "dz-fm-corps");
assert.match(corps.innerHTML, /<h3>Membres<\/h3>/);
assert.match(corps.innerHTML, /<details><summary>Règles communes<\/summary><h3>Aperçu<\/h3><ul><li>Règle\.<\/li><\/ul><\/details>/);
assert.equal(p.children[0].children[0].textContent, "Fiche : essai");
assert.equal(p.children[0].children[1].textContent, "Relevé du 2026-11-09");
assert.ok(doc.getElementById("dz-fiche-modele-css"), "feuille posée une fois");
(doc.ecoute.keydown || []).forEach((f) => f({ key: "Escape", stopPropagation() {} }));
assert.equal(doc.body.children.includes(p), false, "Échap ferme");
assert.equal(doc.focused, b, "le focus revient au « ? »");
assert.equal((doc.ecoute.keydown || []).length, 0, "écouteur clavier retiré");

// [5] fiche indisponible : message, jamais d'exception
ficheRep = { ok: false, status: 404, json: () => Promise.resolve({}) };
await F.ouvrir("licorne");
const p2 = doc.body.children.find((c) => c.className === "dz-fiche-modele");
assert.equal(p2.children[1].textContent, "Fiche indisponible");
F.fermer();
assert.equal(doc.body.children.includes(p2), false);

// [6] DzModelesIA : le « ? » est posé par select(), sauf { fiche: false } ; un select sans parent est laissé
const MODS = [{ id: "seedance-2", label: "S", voie: "fal", dispo: true, usd: 0.3, unite: "s" }];
const W2 = { document: doc, fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({ modeles: MODS }) }),
             DzFicheModele: { poses: [], bouton(e) { this.poses.push(e); return "b"; } } };
const c2 = { window: W2 }; vm.createContext(c2); vm.runInContext(SRC_MI, c2);
const fauxSel = () => { const s = el("select"); s.ownerDocument = doc; s.value = ""; boite.appendChild(s); return s; };
const s1 = fauxSel();
await W2.DzModelesIA.select(s1, "video_i2v", {});
assert.equal(W2.DzFicheModele.poses.length, 1);
await W2.DzModelesIA.select(fauxSel(), "video_i2v", { fiche: false });
assert.equal(W2.DzFicheModele.poses.length, 1, "fiche:false : rien");
const orphelin = el("select"); orphelin.ownerDocument = doc;
assert.equal(W2.DzModelesIA.ficheModele(orphelin), null, "sans parent : rien");
console.log("fiche_modele.test.mjs : OK");
