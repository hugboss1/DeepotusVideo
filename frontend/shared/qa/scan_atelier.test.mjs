// t312 (28/10/2026, tâche 6, revue) — les trois fonctions d'hôte de l'Atelier pour la boîte Scan, JOUÉES : msRun et le bloc
// t312 sont extraits tels quels de frontend/atelier/atelier.js et exécutés sur un faux DOM (aucune correspondance de texte).
// Séries : inserer (sans chapitre, emporté, au curseur sans remplacer la sélection, rafraîchissements), chapitres (un POST
// par chapitre dans la série courante, liste relue ; échec en route -> e.crees et liste relue), manuscrit (scan.txt par
// msRun, série reprise, modale ouverte ; second envoi refusé pendant un job ; une sonde précédente toujours arrêtée),
// boutons (posés après #importFile et #msBtn, libellés dzT, ouverture de window.__dzScan).
// Lancer : node frontend/shared/qa/scan_atelier.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const AT = readFileSync(new URL("../../atelier/atelier.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");
const i0 = AT.indexOf("async function msRun(");
const i1 = AT.indexOf("/* ═════════ utilitaires ═════════ */");
if (i0 < 0 || i1 < i0 || AT.indexOf("/* ═════════ t312 (C1 Scan)") < i0) { console.log("FAIL extraction de msRun et du bloc t312"); process.exit(1); }
const CODE = AT.slice(i0, i1);

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const tick = () => new Promise((r) => setTimeout(r, 5));
const ticks = async (k = 6) => { for (let i = 0; i < k; i++) await tick(); };

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const FR = (cle, vars) => { let s = (D[cle] || {}).fr || cle; if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m)); return s; };

class El {
  constructor(id, tag = "div") { this.id = id; this.tagName = tag.toUpperCase(); this.value = ""; this.files = []; this.disabled = false; this.readOnly = false;
    this.style = {}; this.textContent = ""; this.attrs = {}; this.ec = {}; this.apres = null; this.enfants = [];
    const cl = new Set(); this.classList = { add: (c) => cl.add(c), remove: (c) => cl.delete(c), contains: (c) => cl.has(c) }; }
  setRangeText(t, a, b, mode) { this.value = this.value.slice(0, a) + t + this.value.slice(b); if (mode === "end") { this.selectionStart = this.selectionEnd = a + t.length; } }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  insertAdjacentElement(pos, e) { this.apres = e; e.voisin = this; }
  appendChild(c) { this.enfants.push(c); return c; }
  click() { (this.ec.click || []).forEach((f) => f({})); }
}

function monde({ routes = {} } = {}) {
  const els = {};
  for (const id of ["script", "chapterSeries", "msSeries", "msModal", "msRun", "msFile", "msCompanion", "msProgress", "msStatus", "msBarFill", "importFile", "msBtn"]) els["#" + id] = new El(id);
  els["#msModal"].classList.add("hidden");
  const journal = [], appels = [], intervalles = [], effaces = [];
  let nId = 0;
  const ctx = {
    console, FormData, File, Blob, JSON, Promise, Error, Array, Object, String, Number,
    $: (s) => els[s], dzT: FR, ico: () => "<svg></svg>",
    chapter: null, chapters: [], msPolling: null,
    toast: (m, err) => journal.push(["toast", m, !!err]),
    renderScript: () => journal.push(["renderScript"]), scheduleSave: () => journal.push(["scheduleSave"]),
    refreshSelBar: () => journal.push(["refreshSelBar"]), loadChapters: async (id) => journal.push(["loadChapters", id]),
    loadEntities: async () => {}, renderBible: async () => {}, msSetProgress: () => {},
    setInterval: (f, ms) => { intervalles.push({ f, ms }); return 100 + intervalles.length; },
    clearInterval: (i) => effaces.push(i), setTimeout: () => 0,
    fetch: async (url, init = {}) => { appels.push({ url, init }); const f = routes[(init.method || "GET") + " " + url]; return f ? f(init) : new Response("{}", { status: 404 }); },
    document: { getElementById: (id) => Object.values(els).find((e) => e.id === id) || null, createElement: (t) => new El("", t),
                createTextNode: (t) => ({ texte: t }) },
  };
  ctx.window = ctx;
  ctx.api = {
    async get(p) { const R = await ctx.fetch("/api" + p); return R.json(); },
    async send(m, p, body) { const R = await ctx.fetch("/api" + p, { method: m, body: JSON.stringify(body) }); const d = await R.json(); if (!R.ok) throw new Error(d.detail || "HTTP"); return d; },
  };
  vm.createContext(ctx);
  vm.runInContext(CODE + "\n;this.__f = { msRun, scanInserer, scanCreerChapitres, scanManuscrit, scanBoutons, scanOuvrir };", ctx);
  return { ctx, els, journal, appels, intervalles, effaces, f: ctx.__f };
}
const leve = async (fn) => { try { await fn(); return null; } catch (e) { return e; } };

// ---- inserer ------------------------------------------------------------------------------------------------------------
{
  const m = monde();
  const e1 = await leve(() => m.f.scanInserer("X"));
  ok("1.1 sans chapitre : erreur levée (montrée DANS la boîte), aucun toast", e1 && e1.message === FR("atelier.at3_w.cree_chapitre") && !m.journal.length);
  m.ctx.chapter = { id: "c1" };
  m.els["#script"].readOnly = true;
  const e2 = await leve(() => m.f.scanInserer("X"));
  ok("1.2 chapitre emporté : erreur levée, texte intact", e2 && e2.message === FR("atelier.t312_scan.lecture_seule") && m.els["#script"].value === "");
  const ta = m.els["#script"];
  ta.readOnly = false; ta.value = "abcdefghij"; ta.selectionStart = 3; ta.selectionEnd = 7;
  const r = m.f.scanInserer("[SCAN]");
  ok("1.3 au curseur SANS remplacer la sélection : après sa fin", ta.value === "abcdefg[SCAN]hij" && r === true, ta.value);
  ok("1.4 curseur après le texte inséré", ta.selectionStart === 13 && ta.selectionEnd === 13);
  const faits = m.journal.map((x) => x[0]);
  ok("1.5 renderScript, scheduleSave, refreshSelBar puis toast", ["renderScript", "scheduleSave", "refreshSelBar", "toast"].every((k) => faits.includes(k))
    && faits.indexOf("renderScript") < faits.indexOf("scheduleSave"), faits);
  ta.value = "fin"; delete ta.selectionStart; delete ta.selectionEnd;
  m.f.scanInserer("+");
  ok("1.6 sans curseur connu : à la fin", ta.value === "fin+");
}

// ---- chapitres ----------------------------------------------------------------------------------------------------------
{
  const corps = [];
  let k = 0;
  const m = monde({ routes: { "POST /api/chapters": (init) => { corps.push(JSON.parse(init.body)); k++; return new Response(JSON.stringify({ id: "n" + k }), { status: 200 }); } } });
  m.els["#chapterSeries"].value = "Lost Abyss";
  const r = await m.f.scanCreerChapitres([{ titre: "Un", texte: "T1" }, { titre: "Deux", texte: "T2" }]);
  ok("2.1 un POST /chapters par chapitre, série courante, texte, spans vides", r === true && corps.length === 2
    && corps.every((c) => c.series === "Lost Abyss" && Array.isArray(c.spans) && !c.spans.length) && corps[1].title === "Deux" && corps[1].script_text === "T2", JSON.stringify(corps));
  ok("2.2 la liste relue sur le premier créé", m.journal.some((x) => x[0] === "loadChapters" && x[1] === "n1"));
}
{
  let k = 0;
  const m = monde({ routes: { "POST /api/chapters": () => { k++; return k === 2 ? new Response(JSON.stringify({ detail: "disque plein" }), { status: 500 }) : new Response(JSON.stringify({ id: "n" + k }), { status: 200 }); } } });
  const e = await leve(() => m.f.scanCreerChapitres([{ titre: "A", texte: "a" }, { titre: "B", texte: "b" }, { titre: "C", texte: "c" }]));
  ok("2.3 échec au 2e : erreur avec crees = 1 et son message", e && e.crees === 1 && e.message === "disque plein", e && [e.crees, e.message]);
  ok("2.4 arrêt au premier échec (pas de 3e POST), liste relue quand même", k === 2 && m.journal.some((x) => x[0] === "loadChapters" && x[1] === "n1"));
}

// ---- manuscrit ----------------------------------------------------------------------------------------------------------
{
  let recu = null;
  const m = monde({ routes: { "POST /api/atelier/manuscript": (init) => { recu = init.body; return new Response(JSON.stringify({ job_id: "j1", series: "S", chars: 900 }), { status: 200 }); } } });
  m.els["#chapterSeries"].value = "Lost Abyss";
  const texte = "Texte scanné. ".repeat(20);
  const r = await m.f.scanManuscrit(texte);
  await ticks();
  const f = recu && recu.get("manuscript");
  ok("3.1 msRun envoie un File « scan.txt » du texte à /atelier/manuscript", r === true && f && f.name === "scan.txt" && (await f.text()) === texte);
  ok("3.2 série reprise du chapitre courant, modale ouverte", recu.get("series") === "Lost Abyss" && !m.els["#msModal"].classList.contains("hidden"));
  ok("3.3 une sonde de suivi lancée", m.intervalles.length === 1 && m.intervalles[0].ms === 2000);
  m.ctx.msPolling = 101;
  const e = await leve(() => m.f.scanManuscrit(texte));
  ok("3.4 job en cours : second envoi refusé avec la raison, aucun POST", e && e.message === FR("atelier.t312_scan.ms_en_cours")
    && m.appels.filter((a) => a.url === "/api/atelier/manuscript").length === 1);
  m.ctx.msPolling = null; m.els["#msRun"].disabled = true;
  const e2 = await leve(() => m.f.scanManuscrit(texte));
  ok("3.5 bouton « Lancer » occupé : refusé aussi", e2 && e2.message === FR("atelier.t312_scan.ms_en_cours"));
}
{
  const m = monde({ routes: { "POST /api/atelier/manuscript": () => new Response(JSON.stringify({ job_id: "j2", series: "S", chars: 900 }), { status: 200 }) } });
  m.ctx.msPolling = 77;                          // une sonde restée d'un envoi précédent
  await m.f.msRun(new File(["x".repeat(300)], "scan.txt", { type: "text/plain" }));
  ok("3.6 msRun arrête toujours la sonde précédente avant d'en lancer une", m.effaces.includes(77) && m.ctx.msPolling === 101);
  await m.f.msRun({ type: "click" });
  ok("3.7 msRun appelé par son bouton (évènement) lit #msFile : rien choisi -> toast, aucun POST",
    m.journal.some((x) => x[0] === "toast" && x[1] === FR("atelier.at3_ms.choisis")) && m.appels.length === 1);
}

{
  // revue finale t312 (I3) : un envoi refusé (POST 400) laisse la boîte ouverte avec le texte et la raison
  const m = monde({ routes: { "POST /api/atelier/manuscript": () => new Response(JSON.stringify({ detail: "manuscrit refusé" }), { status: 400 }) } });
  const e = await leve(() => m.f.scanManuscrit("Texte scanné. ".repeat(20)));
  ok("3.8 POST 400 : scanManuscrit lève l'erreur avec son message (la boîte reste ouverte)", e && e.message === "manuscrit refusé", e && e.message);
  ok("3.9 … modale manuscrit refermée, bouton « Lancer » rendu, aucune sonde", m.els["#msModal"].classList.contains("hidden")
    && m.els["#msRun"].disabled === false && m.intervalles.length === 0);
  const r = await m.f.msRun(new File(["x".repeat(300)], "scan.txt", { type: "text/plain" }));
  ok("3.10 msRun rend false sur échec", r === false && m.ctx.msRun.erreur === "manuscrit refusé");
}
{
  const m = monde({ routes: { "POST /api/atelier/manuscript": () => { throw new TypeError("Failed to fetch"); } } });
  const e = await leve(() => m.f.scanManuscrit("Texte scanné. ".repeat(20)));
  ok("3.11 réseau tombé : erreur levée avec la raison", e && e.message === "Failed to fetch", e && e.message);
  const m2 = monde({ routes: { "POST /api/atelier/manuscript": () => new Response(JSON.stringify({ job_id: "j3", series: "S", chars: 900 }), { status: 200 }) } });
  ok("3.12 msRun rend true quand le job est lancé", (await m2.f.msRun(new File(["x".repeat(300)], "scan.txt", { type: "text/plain" }))) === true);
}

// ---- boutons ------------------------------------------------------------------------------------------------------------
{
  const m = monde();
  let opts = null;
  m.ctx.__dzScan = { ouvrir: (o) => { opts = o; return Promise.resolve(null); } };
  m.f.scanBoutons();
  const b1 = m.els["#importFile"].apres, b2 = m.els["#msBtn"].apres;
  ok("4.1 #scanBtn après #importFile, #scanChapBtn après #msBtn", b1 && b1.id === "scanBtn" && b2 && b2.id === "scanChapBtn");
  ok("4.2 libellé et titres par dzT", b1.enfants[0].texte === " " + FR("atelier.t312_scan.bouton") && b1.title === FR("atelier.t312_scan.bouton_t") && b2.title === FR("atelier.t312_scan.chap_t"));
  m.els["#chapterSeries"].value = "Lost Abyss";
  b2.click();
  ok("4.3 clic : la boîte s'ouvre avec la série et les trois envois", opts && opts.hote === "atelier" && opts.serie === "Lost Abyss"
    && opts.inserer === m.f.scanInserer && opts.creerChapitres === m.f.scanCreerChapitres && opts.importerManuscrit === m.f.scanManuscrit);
}

if (echecs.length) { console.log(echecs.map((e) => "FAIL " + e).join("\n")); console.log(`\n=== ${n - echecs.length} passed, ${echecs.length} failed ===`); process.exit(1); }
console.log(`=== ${n} passed, 0 failed ===`);
