// t312 (28/10/2026, tâche 6) — dz-scan.js : la boîte « Scanner une page », jouée sur un DOM simulé avec la VRAIE
// enveloppe dz-plafonds.js (402) et les vrais FormData / File / Response / AbortController de node.
// Séries : depot_lecture_apercu, incertains_navigables, astral, ocr_indisponible, claude_devis_confirmation,
// claude_refus, cout_change_409, plafond_402 (accord, refus), partiel_tronque, sans_cache, decoupage_puis_creation,
// manuscrit_court, onze_fichiers, refus_type, coller, perimee, delai_135s, inserer, echap, anglais ; revue finale t312 :
// délai Claude du devis (delai_s + 30 s), « Relire » par GET /vision d'abord (gardée / en cours / rien), deja_payee et
// « Payer une nouvelle lecture » (nouvelle: true), 409 vision_en_cours, 502/504, « Lire » après Claude confirmé,
// premiere_page_non_lue, lecture locale partielle, note « relis quand même », découpage par le texte exact.
// Lancer : node frontend/shared/qa/scan.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-scan.js", import.meta.url), "utf8");
const PLAFONDS = readFileSync(new URL("../dz-plafonds.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const tick = () => new Promise((r) => setTimeout(r, 5));
const ticks = async (k = 6) => { for (let i = 0; i < k; i++) await tick(); };

const ACTIF = { el: null };
class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; this.files = []; this.scrollTop = 0; }
  get firstChild() { return this.children[0] || null; }
  get parentNode() { return this.parent; }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(v) { throw new Error("innerHTML interdit"); }
  get innerHTML() { throw new Error("innerHTML interdit"); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); }
  focus() { this.focusee = true; ACTIF.el = this; }
  setSelectionRange(a, b) { this.selectionStart = a; this.selectionEnd = b; }
  fire(t, extra = {}) { (this.ec[t] || []).forEach((f) => f(Object.assign({ type: t, target: this, preventDefault() { this.defaultPrevented = true; } }, extra))); }
  click() { this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tous = (r, p) => [...r.tous()].filter(p);
const marque = (r, v) => tous(r, (x) => x.attrs["data-dz-scan"] === v)[0];
const visible = (x) => !!x && !x.hasAttribute("hidden");

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const dzTde = (lang) => (cle, vars) => {
  const e = D[cle];
  if (!e) return cle;
  let s = e[lang] || e.fr;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
  return s;
};
const FR = dzTde("fr"), EN = dzTde("en");
const rep = (status, json) => new Response(JSON.stringify(json === undefined ? {} : json), { status, headers: { "Content-Type": "application/json" } });
const img = (nom) => new File([new Uint8Array([137, 80, 78, 71])], nom, { type: "image/png" });

/* un monde : window === global du contexte (comme un navigateur), fetch simulé par routes "MÉTHODE /chemin" */
function monde({ lang = "fr", routes = {}, plafonds = false, dialogue = null } = {}) {
  const appels = [], minuteries = [], dialogues = [];
  const doc = { createElement: (t) => new Noeud(t), body: new Noeud("body"), documentElement: new Noeud("html"), ec: {},
    get activeElement() { return ACTIF.el; },
    addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); },
    removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); } };
  const ctx = {
    document: doc, console, Response, Headers, Request, FormData, File, Blob, AbortController, URL, Promise, JSON, Array, Object,
    location: { href: "http://127.0.0.1:8899/atelier/" }, Event: class { constructor(t) { this.type = t; } },
    dispatchEvent() {}, dzT: dzTde(lang), dzLang: () => lang,
    setTimeout: (f, ms) => { minuteries.push({ f, ms }); return minuteries.length; },
    clearTimeout: (i) => { if (minuteries[i - 1]) minuteries[i - 1].annulee = true; },
    fetch: async (url, init = {}) => {
      const u = typeof url === "string" ? url : url.url;
      const m = (init.method || (typeof url === "object" && url.method) || "GET").toUpperCase();
      const h = new Headers(init.headers || (typeof url === "object" ? url.headers : undefined));
      const a = { url: u, methode: m, corps: init.body, entetes: h, signal: init.signal };
      appels.push(a);
      const f = routes[m + " " + u];
      return f ? f(a) : rep(404, { detail: "absent : " + u });
    },
    __dzDialogue: { confirmer: async (msg, o) => { dialogues.push({ msg, o: o || {} }); return dialogue ? dialogue(msg, o || {}, dialogues.length) : true; } },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  if (plafonds) vm.runInContext(PLAFONDS, ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, doc, appels, minuteries, dialogues, Scan: ctx.__dzScan, corps: () => doc.body };
}

const TEXTE = "Il était une fois un vi1lage au bord de l'eau.\n\nLes gens y vivaient XIVe heureux, m@lgré tout.";
const pyPos = (texte, mot) => { const cp = Array.from(texte); const i = cp.join("").indexOf(mot); const debut = Array.from(texte.slice(0, i)).length; return { debut, fin: debut + Array.from(mot).length }; };
const LU = { scan_id: "s1", en_cache: true, moteur: "windows", langue: "fr", pages: 2, texte: TEXTE,
  incertains: [pyPos(TEXTE, "vi1lage"), pyPos(TEXTE, "m@lgré")],
  stats: { pages: 2, mots: 18, incertains: 2, colonnes: 2, folios_retires: 1, titres_retires: 0, cesures: 1, pages_texte: 0 }, duree_ms: 420 };
const DEVIS = { usd: 0.0123, moteur: "claude", nom: "Claude Sonnet", disponible: true, raison: "", pages: 2 };
const deposer = (m, fichiers) => marque(m.corps(), "depot").fire("drop", { dataTransfer: { files: fichiers } });

async function lu(opts = {}, lang = "fr", extra = {}) {
  const m = monde({ lang, routes: Object.assign({ "POST /api/scan/lire": () => rep(200, LU), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS) }, extra.routes || {}),
    plafonds: extra.plafonds, dialogue: extra.dialogue });
  const p = m.Scan.ouvrir(Object.assign({ hote: "atelier", serie: "Lost Abyss" }, opts));
  deposer(m, [img("p1.png"), img("p2.png")]);
  marque(m.corps(), "lire").click();
  await ticks();
  return { m, p };
}

// ---- depot_lecture_apercu ---------------------------------------------------------------------------------------------
{
  const { m } = await lu({ inserer: () => true, creerChapitres: () => true, importerManuscrit: () => true });
  const c = m.corps();
  ok("1.1 la boîte est montée dans le body, titre FR", !!marque(c, "voile") && tous(c, (x) => x.textContent === FR("scan.boite.titre")).length > 0);
  ok("1.2 deux pages déposées listées", tous(c, (x) => x.attrs["data-dz-scan"] === "page").length === 2);
  const lire = m.appels.find((a) => a.url === "/api/scan/lire");
  ok("1.3 POST /api/scan/lire multipart : 2 pages + langue fr", lire && lire.methode === "POST" && lire.corps instanceof FormData
    && lire.corps.getAll("pages").length === 2 && lire.corps.get("langue") === "fr", lire && lire.corps);
  ok("1.4 aperçu : textarea = texte lu", marque(c, "texte").value === TEXTE && visible(marque(c, "resultat")));
  const st = marque(c, "stats").textContent;
  ok("1.5 statistiques : pages, mots, colonnes, folios, césures, incertains, moteur", [FR("scan.stats.pages", { n: 2 }), FR("scan.stats.mots", { n: 18 }),
    FR("scan.stats.colonnes", { n: 2 }), FR("scan.stats.folios", { n: 1 }), FR("scan.stats.cesures", { n: 1 }),
    FR("scan.stats.incertains", { n: 2 }), FR("scan.moteur.windows")].every((s) => st.includes(s)) && !st.includes(FR("scan.stats.titres", { n: 0 })), st);
  ok("1.6 devis lu après la lecture", m.appels.some((a) => a.url === "/api/scan/s1/devis-vision" && a.methode === "GET"));
  const b = marque(c, "claude");
  ok("1.7 bouton Claude avec le montant, pas mis en avant", visible(b) && b.textContent === FR("scan.claude.bouton", { usd: "0,0123 $" }) && !b.hasAttribute("data-mis-en-avant"), b.textContent);
  ok("1.8 trois actions d'envoi visibles", ["inserer", "chapitres", "manuscrit"].every((k) => visible(marque(c, k))));
  ok("1.9 délai de 135 s armé pour la lecture (le serveur s'arrête à 120 s)", m.minuteries.some((t) => t.ms === 135000));
}

// ---- incertains_navigables ----------------------------------------------------------------------------------------------
{
  const { m } = await lu();
  const c = m.corps();
  const marks = () => tous(marque(c, "miroir"), (x) => x.attrs["data-dz-scan"] === "incertain");
  ok("2.1 deux mots surlignés, textes exacts", marks().map((x) => x.textContent).join("|") === "vi1lage|m@lgré", marks().map((x) => x.textContent));
  ok("2.2 le miroir reproduit le texte (plus la fin de ligne)", marque(c, "miroir").textContent === TEXTE + "\n");
  ok("2.3 compteur initial", marque(c, "compteur").textContent === FR("scan.incertains.compteur", { i: 0, n: 2 }));
  const ta = marque(c, "texte");
  marque(c, "suiv").click();
  ok("2.4 suivant : le 1er mot sélectionné dans le champ", TEXTE.slice(ta.selectionStart, ta.selectionEnd) === "vi1lage" && ta.focusee);
  ok("2.5 marque courante distincte", marks()[0].attrs.style !== marks()[1].attrs.style && marque(c, "compteur").textContent === FR("scan.incertains.compteur", { i: 1, n: 2 }));
  marque(c, "suiv").click();
  ok("2.6 suivant : le 2e", TEXTE.slice(ta.selectionStart, ta.selectionEnd) === "m@lgré");
  marque(c, "suiv").click();
  ok("2.7 suivant au bout : retour au 1er", TEXTE.slice(ta.selectionStart, ta.selectionEnd) === "vi1lage");
  marque(c, "prec").click();
  ok("2.8 précédent depuis le 1er : le dernier", TEXTE.slice(ta.selectionStart, ta.selectionEnd) === "m@lgré");
  // corriger le 1er mot : sa marque disparaît, la suivante se décale
  ta.value = TEXTE.replace("vi1lage", "village");
  ta.fire("input");
  ok("2.9 mot corrigé : une seule marque, toujours sur m@lgré", marks().length === 1 && marks()[0].textContent === "m@lgré", marks().map((x) => x.textContent));
  ta.value = "Préambule. " + ta.value;
  ta.fire("input");
  ok("2.10 texte ajouté avant : la marque suit", marks().length === 1 && marks()[0].textContent === "m@lgré");
}

// ---- astral : un caractère hors du plan de base AVANT le mot incertain --------------------------------------------------
{
  const texte = "𝒜𝒷 Le ch@t 😀 dort.";
  const pos = [pyPos(texte, "ch@t"), pyPos(texte, "dort")];
  ok("3.0 la position Python diffère de l'indice JS (garde du banc)", pos[0].debut !== texte.indexOf("ch@t"));
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, Object.assign({}, LU, { texte, incertains: pos })), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click();
  await ticks();
  const marks = tous(marque(m.corps(), "miroir"), (x) => x.attrs["data-dz-scan"] === "incertain").map((x) => x.textContent);
  ok("3.1 surlignage juste malgré les caractères astraux", marks.join("|") === "ch@t|dort", marks);
  marque(m.corps(), "suiv").click(); marque(m.corps(), "suiv").click();
  const ta = marque(m.corps(), "texte");
  ok("3.2 sélection juste (indices UTF-16)", texte.slice(ta.selectionStart, ta.selectionEnd) === "dort");
  ok("3.3 versU16 exposé", m.Scan.versU16("😀ab", [{ debut: 1, fin: 3 }])[0].debut === 2);
}

// ---- ocr_indisponible ---------------------------------------------------------------------------------------------------
const INDISPO = { detail: { message: "La lecture de texte de Windows est indisponible.", code: "ocr_indisponible", scan_id: "s2", en_cache: true,
  secours_vision: { usd: 0.02, moteur: "claude", nom: "Claude Sonnet", disponible: true, raison: "", pages: 1 } } };
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO) } });
  m.Scan.ouvrir({ inserer: () => true });
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click();
  await ticks();
  const c = m.corps();
  ok("4.1 message clair en erreur", marque(c, "etat").hasAttribute("data-erreur")
    && marque(c, "etat").textContent === FR("scan.ocr.indisponible", { msg: INDISPO.detail.message }), marque(c, "etat").textContent);
  ok("4.2 bouton Claude MIS EN AVANT avec le devis du 503", visible(marque(c, "claude")) && marque(c, "claude").hasAttribute("data-mis-en-avant")
    && marque(c, "claude").textContent === FR("scan.claude.bouton", { usd: "0,02 $" }), marque(c, "claude").textContent);
  ok("4.3 aucun devis relu (déjà dans le 503)", !m.appels.some((a) => a.url.includes("devis-vision")));
}

// ---- claude_devis_confirmation, claude_refus ---------------------------------------------------------------------------
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": () => rep(200, { scan_id: "s2", pages: 1, moteur: "claude", langue: "fr", texte: "Texte relu par Claude.", incertains: [], stats: { mots: 4 }, usd: 0.018 }) } });
  m.Scan.ouvrir({ inserer: () => true });
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  const c = m.corps();
  ok("5.1 confirmation maison avec le montant avant l'appel", m.dialogues.length === 1
    && m.dialogues[0].msg === FR("scan.claude.confirmer", { n: 1, nom: "Claude Sonnet", usd: "0,02 $" }) && m.dialogues[0].o.ok === FR("scan.claude.ok"), m.dialogues[0] && m.dialogues[0].msg);
  const v = m.appels.find((a) => a.url === "/api/scan/s2/vision");
  ok("5.2 POST vision avec max_usd = devis", v && JSON.parse(v.corps).max_usd === 0.02, v && v.corps);
  ok("5.3 texte Claude dans l'aperçu, moteur dit", marque(c, "texte").value === "Texte relu par Claude." && marque(c, "stats").textContent.includes(FR("scan.moteur.claude")));
  ok("5.4 le bouton Claude se retire après la lecture", !visible(marque(c, "claude")));
}
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO) }, dialogue: () => false });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  ok("5.5 refus : aucun appel payant, rien n'a été envoyé", !m.appels.some((a) => a.url.endsWith("/vision"))
    && marque(m.corps(), "etat").textContent === FR("scan.claude.annule"));
}

// ---- cout_change_409 ----------------------------------------------------------------------------------------------------
{
  let k = 0;
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": (a) => { k++; return k === 1 ? rep(409, { detail: { message: "Le coût a changé.", usd: 0.05 } })
      : rep(200, { moteur: "claude", texte: "Relu.", incertains: [], stats: {}, usd: 0.05 }); } } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks(10);
  const v = m.appels.filter((a) => a.url === "/api/scan/s2/vision").map((a) => JSON.parse(a.corps).max_usd);
  ok("6.1 409 : le nouveau montant est proposé", m.dialogues.length === 2 && m.dialogues[1].msg === FR("scan.claude.cout_change", { usd: "0,05 $" }), m.dialogues.map((d) => d.msg));
  ok("6.2 accord : relance avec max_usd = nouveau devis", v.join(",") === "0.02,0.05", v);
  ok("6.3 lu", marque(m.corps(), "texte").value === "Relu.");
}
{
  let k = 0;
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": () => { k++; return rep(409, { detail: { message: "x", usd: 0.07 } }); } }, dialogue: (msg, o, i) => i === 1 });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks(10);
  ok("6.4 409 puis refus : un seul appel, bouton relibellé au nouveau montant", k === 1 && marque(m.corps(), "claude").textContent === FR("scan.claude.bouton", { usd: "0,07 $" }));
}

// ---- plafond_402 (la vraie enveloppe dz-plafonds.js) --------------------------------------------------------------------
const PLAF = { detail: { dz_plafond: { motif: "categorie", moteur: "claude", categorie: "atelier", deja_usd: 4.99, devis_usd: 0.02, plafond_usd: 5,
  message: "Plafond « atelier » atteint (4,99 $ sur 5,00 $). Confirmez pour tirer quand même, ou relevez le plafond." } } };
for (const accord of [true, false]) {
  const m = monde({ plafonds: true, dialogue: (msg, o) => (o.titre === "Plafond de dépense mensuel" ? accord : true),
    routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
      "POST /api/scan/s2/vision": (a) => (a.entetes.get("X-DZ-Plafond") === "confirme"
        ? rep(200, { moteur: "claude", texte: "Après plafond.", incertains: [], stats: {}, usd: 0.02 }) : rep(402, PLAF)) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks(14);
  const plaf = m.dialogues.find((d) => d.o.titre === "Plafond de dépense mensuel");
  ok(`7.${accord ? 1 : 3} 402 : le dialogue du plafond (dz-plafonds) est montré`, !!plaf && plaf.msg.includes("Plafond « atelier » atteint"), m.dialogues.map((d) => d.o.titre));
  if (accord) {
    ok("7.2 accord : la même requête rejouée avec X-DZ-Plafond, texte lu", m.appels.filter((a) => a.url.endsWith("/vision")).length === 2
      && marque(m.corps(), "texte").value === "Après plafond.");
  } else {
    ok("7.4 refus : message du plafond affiché en erreur, rien de lu", marque(m.corps(), "etat").hasAttribute("data-erreur")
      && marque(m.corps(), "etat").textContent.includes("Plafond « atelier » atteint") && !visible(marque(m.corps(), "resultat")), marque(m.corps(), "etat").textContent);
  }
}

// ---- partiel_tronque ----------------------------------------------------------------------------------------------------
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": () => rep(200, { moteur: "claude", texte: "Quatre pages.", incertains: [], usd: 0.04, partiel: true, pages_lues: 4, erreur: "plafond",
      stats: { tronque: true, lots_tronques: [[1, 4], [7, 7]] } }) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  const b = marque(m.corps(), "bandeau");
  ok("8.1 partiel : « pages 5 et suivantes non lues »", visible(b) && b.textContent.includes(FR("scan.bandeau.partiel", { de: 5, raison: FR("scan.partiel.plafond"), usd: "0,04 $" })), b.textContent);
  ok("8.2 tronqué : les lots coupés sont dits", b.textContent.includes(FR("scan.bandeau.tronque", { lots: "1–4, 7" })), b.textContent);
}

// ---- sans_cache ---------------------------------------------------------------------------------------------------------
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, Object.assign({}, LU, { scan_id: null, en_cache: false })) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  ok("9.1 scan non gardé : pas de bouton Claude, la raison est dite", !visible(marque(m.corps(), "claude"))
    && marque(m.corps(), "note-claude").textContent === FR("scan.claude.sans_cache") && !m.appels.some((a) => a.url.includes("devis")));
}
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, LU), "GET /api/scan/s1/devis-vision": () => rep(200, { usd: 0, disponible: false, raison: "Aucune clé Claude.", pages: 2 }) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  ok("9.2 Claude indisponible : la raison du devis", !visible(marque(m.corps(), "claude"))
    && marque(m.corps(), "note-claude").textContent === FR("scan.claude.indisponible", { raison: "Aucune clé Claude." }));
}

// ---- decoupage_puis_creation --------------------------------------------------------------------------------------------
{
  const texte = "Prologue 😀.\n\nChapitre 1\nLe début.\n\nChapitre 2\nLa suite 𝒜.";
  const d1 = pyPos(texte, "Chapitre 1").debut, d2 = pyPos(texte, "Chapitre 2").debut;
  let recu = null, corpsDecoupage = null;
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, Object.assign({}, LU, { texte, incertains: [] })), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS),
    "POST /api/scan/decoupage": (a) => { corpsDecoupage = JSON.parse(a.corps); return rep(200, { chapitres: [{ titre: "Chapitre 1", texte: "Prologue 😀.\n\nLe début.", caracteres: 22, debut: d1 }, { titre: "", texte: "La suite 𝒜.", caracteres: 23, debut: d2 }] }); } } });
  const p = m.Scan.ouvrir({ creerChapitres: (l) => { recu = l; return true; } });
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "chapitres").click(); await ticks();
  const c = m.corps();
  ok("10.1 POST /api/scan/decoupage avec le texte de l'aperçu", corpsDecoupage && corpsDecoupage.texte === texte);
  const lis = tous(c, (x) => x.attrs["data-dz-scan"] === "chapitre-propose").map((x) => x.textContent);
  ok("10.2 découpage montré AVANT création : titres et tailles", visible(marque(c, "decoupage")) && recu === null
    && lis.join("|") === [FR("scan.decoupage.ligne", { titre: "Chapitre 1", n: 22 }), FR("scan.decoupage.ligne", { titre: FR("scan.decoupage.sans_titre", { n: 2 }), n: 23 })].join("|"), lis);
  ok("10.5 sans série : dit dans l'aperçu du découpage", marque(c, "serie").textContent === FR("scan.decoupage.sans_serie"));
  marque(c, "creer-chapitres").click(); await ticks();
  ok("10.3 creerChapitres : titres et texte EXACT rendu par le serveur (I2 : jamais le titre du suivant)", recu && recu.length === 2
    && recu[0].titre === "Chapitre 1" && recu[0].texte === "Prologue 😀.\n\nLe début." && recu[1].texte === "La suite 𝒜."
    && !recu[0].texte.includes("Chapitre 2"), JSON.stringify(recu));
  ok("10.4 la boîte se ferme, promesse {action: chapitres}", (await p).action === "chapitres" && !marque(m.corps(), "voile"));
}

// ---- manuscrit_court ----------------------------------------------------------------------------------------------------
{
  let recu = null;
  const { m, p } = await lu({ importerManuscrit: (t) => { recu = t; return true; } });
  marque(m.corps(), "manuscrit").click(); await ticks();
  const n = Array.from(TEXTE.trim()).length;
  ok("11.1 manuscrit < 200 caractères : refusé à l'écran avec la raison", recu === null && marque(m.corps(), "etat").hasAttribute("data-erreur")
    && marque(m.corps(), "etat").textContent === FR("scan.manuscrit.trop_court", { n }), marque(m.corps(), "etat").textContent);
  const ta = marque(m.corps(), "texte");
  ta.value = TEXTE + "\n\n" + "Une longue suite de phrases. ".repeat(8);
  ta.fire("input");
  marque(m.corps(), "manuscrit").click(); await ticks();
  ok("11.2 ≥ 200 caractères : importerManuscrit reçoit le texte modifié", recu === ta.value && (await p).action === "manuscrit");
}

// ---- onze_fichiers, refus_type ------------------------------------------------------------------------------------------
{
  const m = monde();
  m.Scan.ouvrir({});
  deposer(m, Array.from({ length: 11 }, (_, i) => img(`p${i}.png`)));
  ok("12.1 11 fichiers : message, aucun ajouté", marque(m.corps(), "etat").textContent === FR("scan.fichiers.trop", { n: 11 })
    && tous(m.corps(), (x) => x.attrs["data-dz-scan"] === "page").length === 0);
  const ent = marque(m.corps(), "fichiers");
  ok("12.2 sélecteur : multiple, images et PDF", ent.hasAttribute("multiple") && ent.getAttribute("accept") === "image/*,application/pdf");
  ent.files = [img("a.png"), new File(["%PDF"], "b.pdf", { type: "application/pdf" })];
  ent.fire("change");
  ok("12.3 choix de fichiers : image + PDF acceptés", tous(m.corps(), (x) => x.attrs["data-dz-scan"] === "page").length === 2);
  deposer(m, [new File(["x"], "notes.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" })]);
  ok("12.4 type refusé : message", marque(m.corps(), "etat").textContent === FR("scan.fichiers.refuse", { nom: "notes.docx" }));
  deposer(m, Array.from({ length: 9 }, (_, i) => img(`q${i}.png`)));
  ok("12.5 2 + 9 > 10 : refusé", marque(m.corps(), "etat").textContent === FR("scan.fichiers.trop", { n: 11 }));
  marque(m.corps(), "retirer").click();
  ok("12.6 retirer une page", tous(m.corps(), (x) => x.attrs["data-dz-scan"] === "page").length === 1);
  marque(m.corps(), "lire").click();
  const sans = monde(); sans.Scan.ouvrir({}); marque(sans.corps(), "lire").click();
  ok("12.7 lire sans page : message, aucune requête", marque(sans.corps(), "etat").textContent === FR("scan.fichiers.aucun") && !sans.appels.length);
}

// ---- coller (Ctrl+V d'une image) ----------------------------------------------------------------------------------------
{
  const m = monde();
  m.Scan.ouvrir({});
  let empeche = false;
  const ev = { clipboardData: { items: [{ kind: "string", type: "text/plain" }, { kind: "file", type: "image/png", getAsFile: () => img("image.png") }] }, preventDefault() { empeche = true; } };
  (m.doc.ec.paste || []).forEach((f) => f(ev));
  ok("13.1 coller une image : page ajoutée, collage empêché", tous(m.corps(), (x) => x.attrs["data-dz-scan"] === "page").length === 1 && empeche);
  let empeche2 = false;
  (m.doc.ec.paste || []).forEach((f) => f({ clipboardData: { items: [{ kind: "string", type: "text/plain" }] }, preventDefault() { empeche2 = true; } }));
  ok("13.2 coller du texte : laissé au champ", !empeche2);
  m.Scan.fermer();
  ok("13.3 fermée : l'écoute du collage est retirée", !(m.doc.ec.paste || []).length);
}

// ---- perimee ------------------------------------------------------------------------------------------------------------
{
  const attente = [];
  const m = monde({ routes: { "POST /api/scan/lire": () => new Promise((r) => attente.push(r)), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await tick();
  marque(m.corps(), "lire").click(); await tick();
  attente[1](rep(200, Object.assign({}, LU, { texte: "Seconde lecture.", incertains: [] }))); await ticks();
  attente[0](rep(200, Object.assign({}, LU, { texte: "Première lecture, périmée.", incertains: [] }))); await ticks();
  ok("14.1 réponse périmée ignorée", marque(m.corps(), "texte").value === "Seconde lecture.", marque(m.corps(), "texte").value);
  ok("14.2 la première requête a été abandonnée (signal)", m.appels[0].signal && m.appels[0].signal.aborted);
}

// ---- delai_135s ---------------------------------------------------------------------------------------------------------
{
  const m = monde({ routes: { "POST /api/scan/lire": (a) => new Promise((_, rej) => a.signal.addEventListener("abort", () => rej(new Error("aborted")))) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await tick();
  m.minuteries.filter((t) => t.ms === 135000 && !t.annulee).pop().f(); await ticks();
  ok("15.1 délai de 135 s : message clair", marque(m.corps(), "etat").textContent === FR("scan.lecture.delai") && marque(m.corps(), "etat").hasAttribute("data-erreur"));
}
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(415, { detail: "Format non pris en charge." }) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  ok("15.2 erreur serveur : son message", marque(m.corps(), "etat").textContent === FR("scan.lecture.echec", { msg: "Format non pris en charge." }));
}

// ---- inserer, echap -----------------------------------------------------------------------------------------------------
{
  let recu = null;
  const { m, p } = await lu({ inserer: (t) => { recu = t; return true; } });
  const ta = marque(m.corps(), "texte");
  ta.value = "Texte corrigé."; ta.fire("input");
  marque(m.corps(), "inserer").click(); await ticks();
  ok("16.1 insérer : la fonction de l'hôte reçoit le texte de l'aperçu", recu === "Texte corrigé." && (await p).action === "inserer");
}
{
  let essais = 0;
  const { m } = await lu({ inserer: () => { essais++; return false; } });
  marque(m.corps(), "inserer").click(); await ticks();
  ok("16.2 l'hôte rend false : la boîte reste ouverte", essais === 1 && !!marque(m.corps(), "voile"));
  const { m: m2 } = await lu({ inserer: () => { throw new Error("aucun chapitre ouvert"); } });
  marque(m2.corps(), "inserer").click(); await ticks();
  ok("16.3 l'hôte échoue : message, boîte ouverte", marque(m2.corps(), "etat").textContent === FR("scan.envoi.echec", { msg: "aucun chapitre ouvert" }) && !!marque(m2.corps(), "voile"));
  const m3 = monde(); m3.Scan.ouvrir({});
  ok("16.4 fonctions absentes : aucun bouton d'envoi", !marque(m3.corps(), "inserer") && !marque(m3.corps(), "chapitres") && !marque(m3.corps(), "manuscrit"));
}
{
  const m = monde();
  const p = m.Scan.ouvrir({});
  marque(m.corps(), "voile").fire("keydown", { key: "Escape" });
  ok("17.1 Échap : fermée, null", (await p) === null && !marque(m.corps(), "voile"));
}

// ---- anglais ------------------------------------------------------------------------------------------------------------
{
  const { m } = await lu({ importerManuscrit: () => true, inserer: () => true, creerChapitres: () => true }, "en");
  const c = m.corps();
  ok("18.1 EN : titre et boutons", tous(c, (x) => x.textContent === EN("scan.boite.titre")).length > 0 && marque(c, "lire").textContent === "Read"
    && marque(c, "inserer").textContent === EN("scan.envoi.inserer") && EN("scan.envoi.inserer") !== FR("scan.envoi.inserer"));
  ok("18.2 EN : langue par défaut en", m.appels.find((a) => a.url === "/api/scan/lire").corps.get("langue") === "en");
  ok("18.3 EN : montant au format anglais", marque(c, "claude").textContent === EN("scan.claude.bouton", { usd: "$0.0123" }), marque(c, "claude").textContent);
  ok("18.4 EN : statistiques", marque(c, "stats").textContent.includes(EN("scan.stats.colonnes", { n: 2 })) && marque(c, "stats").textContent.includes(EN("scan.moteur.windows")));
  marque(c, "manuscrit").click(); await ticks();
  ok("18.5 EN : manuscrit court, raison en anglais", marque(c, "etat").textContent === EN("scan.manuscrit.trop_court", { n: Array.from(TEXTE.trim()).length }));
  const m2 = monde({ lang: "en" }); m2.Scan.ouvrir({});
  deposer(m2, Array.from({ length: 11 }, (_, i) => img(`p${i}.png`)));
  ok("18.6 EN : 11 fichiers", marque(m2.corps(), "etat").textContent === EN("scan.fichiers.trop", { n: 11 }));
  const keys = Object.keys(D).filter((k) => k.startsWith("scan."));
  ok("18.7 chaque clé scan.* utilisée existe en fr et en", [...SRC.matchAll(/T\("(scan\.[a-z0-9_.]*[a-z0-9_])"/g)].every((x) => D[x[1]] && D[x[1]].fr && D[x[1]].en) && keys.length >= 50, keys.length);
  ok("18.8 aucune clé scan.* sans usage", keys.every((k) => SRC.includes('"' + k + '"') || (k.startsWith("scan.moteur.") && SRC.includes('"scan.moteur." +'))), keys.filter((k) => !SRC.includes('"' + k + '"')));
}

// ---- revue t312 tâche 6 : verrou de la lecture payante ------------------------------------------------------------------
{
  const attente = [];
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO), "POST /api/scan/s2/vision": () => new Promise((r) => attente.push(r)) } });
  const p = m.Scan.ouvrir({ inserer: () => true, creerChapitres: () => true, importerManuscrit: () => true });
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  const c = m.corps();
  const gris = (k) => marque(c, k) && marque(c, k).hasAttribute("disabled");
  ok("20.1 pendant /vision : voile « lecture en cours » visible", visible(marque(c, "occupe")) && marque(c, "occupe").textContent === FR("scan.claude.en_cours"));
  ok("20.2 pendant /vision : Lire, Choisir, Claude, Fermer et retrait grisés", ["lire", "choisir", "claude", "fermer", "retirer"].every(gris),
    ["lire", "choisir", "claude", "fermer", "retirer"].filter((k) => !gris(k)));
  const nLire = m.appels.filter((a) => a.url === "/api/scan/lire").length;
  marque(c, "lire").fire("click"); await ticks();
  ok("20.3 Lire cliqué quand même : aucune nouvelle lecture", m.appels.filter((a) => a.url === "/api/scan/lire").length === nLire);
  deposer(m, [img("b.png")]);
  ok("20.4 dépôt bloqué avec un message", tous(c, (x) => x.attrs["data-dz-scan"] === "page").length === 1 && marque(c, "etat").textContent === FR("scan.depot.occupe"));
  (m.doc.ec.paste || []).forEach((f) => f({ clipboardData: { items: [{ kind: "file", type: "image/png", getAsFile: () => img("c.png") }] }, preventDefault() {} }));
  ok("20.5 collage bloqué", tous(c, (x) => x.attrs["data-dz-scan"] === "page").length === 1);
  marque(c, "retirer").fire("click");
  ok("20.6 retrait bloqué", tous(c, (x) => x.attrs["data-dz-scan"] === "page").length === 1);
  marque(c, "voile").fire("keydown", { key: "Escape" }); marque(c, "fermer").fire("click"); m.Scan.fermer();
  ok("20.7 Échap / Fermer : la boîte reste ouverte", !!marque(m.corps(), "voile"));
  ok("20.8 les envois sont grisés", ["inserer", "chapitres", "manuscrit"].every(gris));
  marque(c, "chapitres").fire("click"); marque(c, "claude").fire("click"); await ticks();
  ok("20.9 découpage et second clic Claude : rien ne part", !m.appels.some((a) => a.url === "/api/scan/decoupage")
    && m.appels.filter((a) => a.url.endsWith("/vision")).length === 1 && m.dialogues.length === 1);
  attente[0](rep(200, { moteur: "claude", texte: "Payé, donc gardé.", incertains: [], stats: {}, usd: 0.02 })); await ticks();
  ok("20.10 la réponse facturée est gardée et affichée", marque(c, "texte").value === "Payé, donc gardé.");
  ok("20.11 déverrouillé : voile caché, Lire et envois actifs", !visible(marque(c, "occupe")) && !gris("lire") && !gris("inserer") && !gris("fermer"));
  marque(c, "fermer").click();
  ok("20.12 puis fermable", (await p) === null);
}
{
  const attente = [];
  const m = monde({ routes: { "POST /api/scan/lire": () => new Promise((r) => attente.push(r)), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await tick();
  attente[0](rep(200, LU)); await ticks();
  ok("20.13 bouton Claude visible après lecture", visible(marque(m.corps(), "claude")));
  marque(m.corps(), "lire").click(); await tick();
  ok("20.14 une relecture retire le devis de la lecture précédente", !visible(marque(m.corps(), "claude")));
}

// ---- délai de 180 s du secours Claude -----------------------------------------------------------------------------------
{
  let k = 0;
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": (a) => { k++; return k === 1 ? new Promise((_, rej) => a.signal.addEventListener("abort", () => rej(new Error("aborted"))))
      : rep(200, { moteur: "claude", texte: "Relu après délai.", incertains: [], stats: {}, usd: 0.02 }); } } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  const t = m.minuteries.filter((x) => x.ms === 180000 && !x.annulee);
  ok("21.1 délai de 180 s armé pour /vision", t.length === 1);
  t[0].f(); await ticks();
  const c = m.corps();
  ok("21.2 délai : message clair (peut-être facturé), en erreur", marque(c, "etat").textContent === FR("scan.claude.delai") && marque(c, "etat").hasAttribute("data-erreur"));
  ok("21.3 « Relire » proposé, déverrouillé", visible(marque(c, "relire")) && marque(c, "relire").textContent === FR("scan.claude.relire")
    && !marque(c, "relire").hasAttribute("disabled") && !visible(marque(c, "occupe")) && !marque(c, "lire").hasAttribute("disabled"));
  marque(c, "relire").click(); await ticks();
  ok("21.4 Relire : nouvelle confirmation puis lecture", m.dialogues.length === 2 && k === 2 && marque(c, "texte").value === "Relu après délai.");
}

// ---- double envoi -------------------------------------------------------------------------------------------------------
{
  const appels = { inserer: 0, chapitres: 0, manuscrit: 0 };
  const fins = [];
  const attendre = (k) => () => { appels[k]++; return new Promise((r) => fins.push(r)); };
  const { m, p } = await lu({ inserer: attendre("inserer"), creerChapitres: attendre("chapitres"), importerManuscrit: attendre("manuscrit") });
  const c = m.corps();
  marque(c, "inserer").click(); marque(c, "inserer").fire("click"); await ticks();
  ok("22.1 insérer double clic : une seule action, boutons grisés", appels.inserer === 1 && marque(c, "inserer").hasAttribute("disabled") && marque(c, "manuscrit").hasAttribute("disabled"));
  marque(c, "manuscrit").fire("click"); await ticks();
  ok("22.2 un autre envoi pendant le premier : rien", appels.manuscrit === 0);
  fins[0](false); await ticks();
  ok("22.3 l'hôte rend false : boutons rendus", !marque(c, "inserer").hasAttribute("disabled"));
  const ta = marque(c, "texte"); ta.value = TEXTE + "\n" + "Encore du texte pour le manuscrit. ".repeat(8); ta.fire("input");
  marque(c, "manuscrit").click(); marque(c, "manuscrit").fire("click"); await ticks();
  ok("22.4 manuscrit double clic : une seule action", appels.manuscrit === 1);
  fins[1](true); await ticks();
  ok("22.5 fermé après l'envoi", (await p).action === "manuscrit");
}
{
  let n = 0; const fins = [];
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, LU), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS),
    "POST /api/scan/decoupage": () => rep(200, { chapitres: [{ titre: "A", caracteres: 5, debut: 0 }] }) } });
  m.Scan.ouvrir({ serie: "Lost Abyss", creerChapitres: () => { n++; return new Promise((r) => fins.push(r)); } });
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "chapitres").click(); marque(m.corps(), "chapitres").fire("click"); await ticks();
  ok("22.6 découpage double clic : un seul POST", m.appels.filter((a) => a.url === "/api/scan/decoupage").length === 1);
  ok("22.7 la série cible est dite dans l'aperçu du découpage", marque(m.corps(), "serie").textContent === FR("scan.decoupage.serie", { serie: "Lost Abyss" }));
  marque(m.corps(), "creer-chapitres").click(); marque(m.corps(), "creer-chapitres").fire("click"); await ticks();
  ok("22.8 « Créer ces chapitres » double clic : une seule création", n === 1 && marque(m.corps(), "creer-chapitres").hasAttribute("disabled"));
  fins[0](true); await ticks();
}

// ---- création partielle -------------------------------------------------------------------------------------------------
{
  const recus = [];
  const texte = "Chapitre 1\nUn.\n\nChapitre 2\nDeux.\n\nChapitre 3\nTrois.";
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, Object.assign({}, LU, { texte, incertains: [] })), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS),
    "POST /api/scan/decoupage": () => rep(200, { chapitres: [{ titre: "Chapitre 1", caracteres: 14, debut: 0 }, { titre: "Chapitre 2", caracteres: 16, debut: pyPos(texte, "Chapitre 2").debut },
      { titre: "Chapitre 3", caracteres: 17, debut: pyPos(texte, "Chapitre 3").debut }] }) } });
  const p = m.Scan.ouvrir({ creerChapitres: (l) => {
    recus.push(l.map((x) => x.titre));
    if (recus.length === 1) { const e = new Error("serveur indisponible"); e.crees = 1; throw e; }
    return true;
  } });
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "chapitres").click(); await ticks();
  marque(m.corps(), "creer-chapitres").click(); await ticks();
  const c = m.corps();
  ok("23.1 échec en route : « 1 créé sur 3 » dans la boîte", marque(c, "etat").textContent === FR("scan.decoupage.partiel", { k: 1, n: 3, msg: "serveur indisponible" }), marque(c, "etat").textContent);
  ok("23.2 le bouton devient « Créer les chapitres restants »", marque(c, "creer-chapitres").textContent === FR("scan.decoupage.restants") && !marque(c, "creer-chapitres").hasAttribute("disabled"));
  marque(c, "creer-chapitres").click(); await ticks();
  ok("23.3 seuls les restants sont créés", JSON.stringify(recus) === JSON.stringify([["Chapitre 1", "Chapitre 2", "Chapitre 3"], ["Chapitre 2", "Chapitre 3"]]), JSON.stringify(recus));
  ok("23.4 puis fermé", (await p).action === "chapitres");
}

// ---- focus et clavier ---------------------------------------------------------------------------------------------------
{
  const m = monde();
  m.Scan.ouvrir({ inserer: () => true });
  const c = m.corps();
  ok("24.1 à l'ouverture, le focus est dans la boîte (Choisir)", ACTIF.el === marque(c, "choisir"));
  const v = marque(c, "voile");
  let empeche = false;
  v.fire("keydown", { key: "Tab", shiftKey: true, preventDefault() { empeche = true; } });
  ok("24.2 Maj+Tab sur le premier : le dernier (Fermer)", empeche && ACTIF.el === marque(c, "fermer"));
  empeche = false;
  v.fire("keydown", { key: "Tab", preventDefault() { empeche = true; } });
  ok("24.3 Tab sur le dernier : retour au premier", empeche && ACTIF.el === marque(c, "choisir"));
  empeche = false;
  v.fire("keydown", { key: "Tab", preventDefault() { empeche = true; } });
  ok("24.4 Tab au milieu : laissé au navigateur", !empeche);
  ACTIF.el = new Noeud("button");
  v.fire("keydown", { key: "Tab", preventDefault() {} });
  ok("24.5 focus hors de la boîte : ramené dedans", ACTIF.el === marque(c, "choisir"));
}

// ---- revue finale t312 --------------------------------------------------------------------------------------------------
const INDISPO_480 = { detail: Object.assign({}, INDISPO.detail, { secours_vision: Object.assign({}, INDISPO.detail.secours_vision, { delai_s: 480, pages: 10 }) }) };
const RELU = { scan_id: "s2", pages: 1, moteur: "claude", langue: "fr", texte: "Transcription payée gardée.", incertains: [], stats: {}, usd: 0.02 };
async function claudeQuiTraine(routes, dialogue) {
  const m = monde({ routes: Object.assign({ "POST /api/scan/lire": () => rep(503, INDISPO_480),
    "POST /api/scan/s2/vision": (a) => new Promise((_, rej) => a.signal.addEventListener("abort", () => rej(new Error("aborted")))) }, routes), dialogue });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  return m;
}
{
  let posts = 0;
  const m = await claudeQuiTraine({ "GET /api/scan/s2/vision": () => rep(200, Object.assign({}, RELU, { deja_payee: true })) });
  const t = m.minuteries.filter((x) => x.ms === 480000 + 30000 && !x.annulee);
  ok("30.1 I1a : délai Claude = delai_s du devis + 30 s (510 s pour 10 pages)", t.length === 1, m.minuteries.map((x) => x.ms));
  t[0].f(); await ticks();
  const c = m.corps();
  ok("30.2 délai : « Relire » proposé", visible(marque(c, "relire")) && marque(c, "etat").textContent === FR("scan.claude.delai"));
  m.ctx.fetch = ((f) => async (u, i) => { if (String(u).endsWith("/vision") && (i || {}).method === "POST") posts++; return f(u, i); })(m.ctx.fetch);
  marque(c, "relire").click(); await ticks();
  ok("30.3 I1c : Relire demande d'abord GET /vision (gratuit) : texte gardé, AUCUNE confirmation ni POST", m.appels.some((a) => a.url === "/api/scan/s2/vision" && a.methode === "GET")
    && m.dialogues.length === 1 && posts === 0 && marque(c, "texte").value === RELU.texte, m.dialogues.length + " " + posts);
  ok("30.4 « déjà payée » dit, bouton « Payer une nouvelle lecture » offert", marque(c, "etat").textContent === FR("scan.claude.deja_payee")
    && visible(marque(c, "nouvelle")) && marque(c, "nouvelle").textContent === FR("scan.claude.nouvelle", { usd: "0,02 $" }) && !visible(marque(c, "relire")));
}
{
  let corpsNouvelle = null;
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": (a) => { const b = JSON.parse(a.corps); if (b.nouvelle) { corpsNouvelle = b; return rep(200, Object.assign({}, RELU, { texte: "Nouvelle lecture." })); }
      return rep(200, Object.assign({}, RELU, { deja_payee: true })); } }, dialogue: (msg, o, k) => k !== 2 || !!m2.oui });
  const m2 = { oui: false };
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  const c = m.corps();
  ok("30.5 I1d : POST qui rend une lecture déjà payée : montrée, « déjà payée » dit", marque(c, "texte").value === RELU.texte && visible(marque(c, "nouvelle")));
  marque(c, "nouvelle").click(); await ticks();
  ok("30.6 « Payer une nouvelle lecture » : confirmation dédiée ; refusée -> rien n'est envoyé", m.dialogues.length === 2
    && m.dialogues[1].msg === FR("scan.claude.nouvelle_confirmer", { n: 1, nom: "Claude Sonnet", usd: "0,02 $" }) && corpsNouvelle === null);
  m2.oui = true;
  marque(c, "nouvelle").click(); await ticks();
  ok("30.7 … acceptée : POST avec nouvelle: true", corpsNouvelle && corpsNouvelle.nouvelle === true && marque(c, "texte").value === "Nouvelle lecture.", JSON.stringify(corpsNouvelle));
}
{
  const m = await claudeQuiTraine({ "GET /api/scan/s2/vision": () => rep(409, { detail: { code: "vision_en_cours", message: "en cours" } }) });
  m.minuteries.filter((x) => x.ms === 510000 && !x.annulee)[0].f(); await ticks();
  marque(m.corps(), "relire").click(); await ticks();
  ok("30.8 Relire pendant que le serveur lit encore : « tourne encore », Relire reste, aucun POST de plus",
    marque(m.corps(), "etat").textContent === FR("scan.claude.encore") && visible(marque(m.corps(), "relire")) && m.dialogues.length === 1
    && m.appels.filter((a) => a.url === "/api/scan/s2/vision" && a.methode === "POST").length === 1);
}
{
  let k = 0;
  const m = await claudeQuiTraine({ "GET /api/scan/s2/vision": () => rep(404, { detail: "rien" }),
    "POST /api/scan/s2/vision": (a) => { k++; return k === 1 ? new Promise((_, rej) => a.signal.addEventListener("abort", () => rej(new Error("aborted")))) : rep(200, RELU); } });
  m.minuteries.filter((x) => x.ms === 510000 && !x.annulee)[0].f(); await ticks();
  marque(m.corps(), "relire").click(); await ticks();
  ok("30.9 Relire sans rien de gardé (404) : nouvelle lecture PAYANTE seulement après confirmation", m.dialogues.length === 2 && k === 2
    && marque(m.corps(), "texte").value === RELU.texte);
}
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": () => rep(409, { detail: { code: "vision_en_cours", message: "Une lecture par Claude de ce scan est déjà en cours : attends sa réponse." } }) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  ok("30.10 I1b : 409 vision_en_cours (autre onglet) : dit, « Relire » proposé, pas de boucle de devis", marque(m.corps(), "etat").textContent === FR("scan.claude.encore")
    && visible(marque(m.corps(), "relire")) && m.dialogues.length === 1);
}
for (const code of [504, 502]) {
  const msg = code === 504 ? "La lecture par Claude n'a pas répondu à temps : elle a peut-être été facturée." : "La lecture par Claude a échoué (réseau) : elle a peut-être été facturée.";
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO), "POST /api/scan/s2/vision": () => rep(code, { detail: msg }) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  ok(`30.11 m2 : ${code} : son message (peut-être facturée), « Relire » proposé`, marque(m.corps(), "etat").textContent === FR("scan.claude.echec", { msg })
    && visible(marque(m.corps(), "relire")) && !visible(marque(m.corps(), "claude")));
}
{
  let lectures = 0;
  const m = monde({ routes: { "POST /api/scan/lire": () => { lectures++; return rep(200, LU); }, "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS),
    "POST /api/scan/s1/vision": () => rep(200, Object.assign({}, RELU, { scan_id: "s1" })) }, dialogue: (msg) => msg !== FR("scan.lire.ecraser") || !!etat.oui });
  const etat = { oui: false };
  m.Scan.ouvrir({});
  deposer(m, [img("a.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  marque(m.corps(), "lire").click(); await ticks();
  ok("30.12 m3 : « Lire » après une lecture Claude : confirmation ; refusée -> texte payé gardé, aucune lecture", lectures === 1
    && m.dialogues[m.dialogues.length - 1].msg === FR("scan.lire.ecraser") && marque(m.corps(), "texte").value === RELU.texte
    && marque(m.corps(), "etat").textContent === FR("scan.lire.garde"));
  etat.oui = true;
  marque(m.corps(), "lire").click(); await ticks();
  ok("30.13 … acceptée : la lecture locale remplace", lectures === 2 && marque(m.corps(), "texte").value === TEXTE);
  marque(m.corps(), "lire").click(); await ticks();
  ok("30.14 après une lecture locale : plus de confirmation", lectures === 3 && m.dialogues.filter((d) => d.msg === FR("scan.lire.ecraser")).length === 2);
}
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(503, INDISPO),
    "POST /api/scan/s2/vision": () => rep(200, { moteur: "claude", texte: "Quatre pages.", incertains: [], usd: 0.04, partiel: true, pages_lues: 4, premiere_page_non_lue: 6, erreur: "appel", stats: {} }) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.pdf")]);
  marque(m.corps(), "lire").click(); await ticks();
  marque(m.corps(), "claude").click(); await ticks();
  ok("30.15 m5 : bandeau partiel au numéro du dépôt (premiere_page_non_lue)", marque(m.corps(), "bandeau").textContent.includes(FR("scan.bandeau.partiel", { de: 6, raison: FR("scan.partiel.appel"), usd: "0,04 $" })),
    marque(m.corps(), "bandeau").textContent);
}
{
  const m = monde({ routes: { "POST /api/scan/lire": () => rep(200, Object.assign({}, LU, { incertains: [], partiel: true, pages_lues: 2 })), "GET /api/scan/s1/devis-vision": () => rep(200, DEVIS) } });
  m.Scan.ouvrir({});
  deposer(m, [img("a.png"), img("b.png"), img("c.png")]);
  marque(m.corps(), "lire").click(); await ticks();
  const c = m.corps();
  ok("30.16 m1 : lecture locale arrêtée par le serveur : bandeau « pages 3 et suivantes »", visible(marque(c, "bandeau"))
    && marque(c, "bandeau").textContent === FR("scan.bandeau.lecture_partielle", { de: 3 }), marque(c, "bandeau").textContent);
  ok("30.17 I5 : aucun mot étrange : « relis quand même », jamais « aucun mot incertain »", marque(c, "compteur").textContent === FR("scan.incertains.aucun")
    && /relis quand même/.test(FR("scan.incertains.aucun")) && !/incertain/i.test(FR("scan.incertains.aucun")));
  ok("30.18 I5 : note TOUJOURS visible sous l'aperçu : les mots faux plausibles ne sont pas surlignés", visible(marque(c, "note-relire"))
    && marque(c, "note-relire").textContent === FR("scan.apercu.relire_note") && /relis/.test(FR("scan.apercu.relire_note")));
  ok("30.19 I5 : statistique « mot(s) étrange(s) à vérifier » en FR et EN", FR("scan.stats.incertains", { n: 0 }).includes("étrange") && EN("scan.stats.incertains", { n: 0 }).includes("odd")
    && EN("scan.incertains.aucun") === "No odd word spotted — proofread anyway.");
}

// ---- garde-fous de source -----------------------------------------------------------------------------------------------
ok("19.1 jamais innerHTML", !/innerHTML/.test(SRC));
ok("19.2 jamais de confirm / alert natifs", !/(^|[^.\w])(confirm|alert|prompt)\(/m.test(SRC));
ok("19.3 la confirmation passe par __dzDialogue.confirmer", SRC.includes("D.confirmer(") && SRC.includes("window.__dzDialogue"));

if (echecs.length) { console.log(echecs.map((e) => "FAIL " + e).join("\n")); console.log(`\n=== ${n - echecs.length} passed, ${echecs.length} failed ===`); process.exit(1); }
console.log(`=== ${n} passed, 0 failed ===`);
