// t381 (30/10/2026, lot « News : fils suivis ») — dz-fils.js : les fils sociaux suivis de News › Sources, joués avec un
// fetch et un DOM simulés. Séries : liste en FR et en EN (pastilles, lecture, état, dernière lecture, coût, origine,
// fréquence), aucune chaîne de l'autre langue ; ajout à la main (corps envoyé, aide selon la plateforme) ; erreur du
// serveur affichée (texte et détail structuré) ; devis d'un fil payant puis accord (confirme_cout, plafond) ; devis sans
// clé ; lecture, pause, fréquence ; retrait derrière la confirmation ; suggestions (seules les proposées, origine,
// accepter, écarter) ; aucun innerHTML.
// Lancer : node frontend/shared/qa/fils.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-fils.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };
const dort = (ms) => new Promise((r) => setTimeout(r, ms));
const INNER = [];

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.children = []; this.attrs = {}; this.ec = {};
                     this.parent = null; this.textContent = ""; this.disabled = false; this.value = ""; }
  get firstChild() { return this.children[0] || null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  removeChild(c) { this.children.splice(this.children.indexOf(c), 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { this.ec[t] = f; }
  set innerHTML(_v) { INNER.push(this.tagName); }
}
const tous = (n, acc = []) => { acc.push(n); n.children.forEach((c) => tous(c, acc)); return acc; };
const texte = (n) => tous(n).map((x) => x.textContent).filter(Boolean).join(" | ");
const parAttr = (n, k, v) => tous(n).filter((x) => x.attrs && (v === undefined ? k in x.attrs : x.attrs[k] === v));
const un = (n, k, v) => parAttr(n, k, v)[0];

const RD = { id: "fil_rd", plateforme: "reddit", identifiant: "r/videoediting", nom: "r/videoediting", frequence_h: 6, max: 20,
             origine: { type: "main" }, pause: false, accord: null, derniere_lecture: "2026-10-30T10:00:00+00:00",
             dernier_nombre: 25, dernier_cout_usd: 0, cout_cumule_usd: 0, etat: "ok", lecture: "rss",
             lien: "https://www.reddit.com/r/videoediting/", prochaine: "2026-10-30T16:00:00+00:00" };
const XF = { id: "fil_x", plateforme: "x", identifiant: "runwayml", nom: "@runwayml", frequence_h: 24, max: 20,
             origine: { type: "agent", agent: "campagnes", cadre: "veille", conversation: "c1" }, pause: false, accord: null,
             derniere_lecture: null, dernier_nombre: 0, dernier_cout_usd: 0, cout_cumule_usd: 0, etat: "devis_a_accepter",
             lecture: "apify", lien: "https://x.com/runwayml", prochaine: null };
const XA = Object.assign({}, XF, { id: "fil_xa", nom: "@pika", accord: { plafond_usd: 0.4, devis_usd: 0.12 }, etat: "ok",
             derniere_lecture: "2026-10-30T09:00:00+00:00", dernier_nombre: 20, dernier_cout_usd: 0.05, cout_cumule_usd: 0.15,
             pause: true });
const SUG = [{ id: "sug_ig", plateforme: "instagram", identifiant: "runwayapp", nom: "@runwayapp",
               raison: "le concurrent y annonce ses sorties", origine: { type: "agent", agent: "campagnes", cadre: "veille" },
               cree: "2026-10-30T08:00:00+00:00", etat: "proposee" },
             { id: "sug_tt", plateforme: "tiktok", identifiant: "vieux", nom: "@vieux", raison: "x", origine: {},
               cree: "2026-10-29T08:00:00+00:00", etat: "ecartee" }];
const PLATS = { x: { libelle: "X", lecture: "apify" }, instagram: { libelle: "Instagram", lecture: "apify" },
                tiktok: { libelle: "TikTok", lecture: "apify" }, youtube: { libelle: "YouTube", lecture: "rss" },
                reddit: { libelle: "Reddit", lecture: "rss" } };
const LISTE = (fils, sug = SUG) => ({ fils, suggestions: sug, plateformes: PLATS, frequences_h: [1, 3, 6, 12, 24, 72, 168],
                                      frequence_defaut_h: 24, apify: { configure: true } });

function monde(lang, reponses) {
  const appels = [];
  const dialogues = [];
  const w = {
    navigator: { language: lang }, localStorage: { getItem: () => lang, setItem() {} },
    document: { documentElement: { lang }, createElement: (t) => new Noeud(t), addEventListener() {} },
    fetch: async (url, o) => {
      appels.push({ url, methode: (o && o.method) || "GET", corps: o && o.body ? JSON.parse(o.body) : undefined });
      const r = reponses(url, o || {});
      return { ok: r.ok !== false, status: r.status || 200, json: async () => r.corps };
    },
    __dzDialogue: { confirmer: async (m) => { dialogues.push(m); return w.__oui; } },
    __oui: false, setTimeout, clearTimeout, console, Promise, JSON, Date, Object, Math, Number, String,
  };
  w.window = w;
  w.globalThis = w;
  vm.createContext(w);
  vm.runInContext(DICO, w);
  w.dzLang = () => lang;
  w.dzT = (k, v) => {
    const e = w.DZ_I18N[k]; if (!e) return "⟦" + k + "⟧";
    return String(e[lang]).replace(/\{(\w+)\}/g, (m, x) => (v && v[x] != null ? String(v[x]) : m));
  };
  vm.runInContext(SRC, w);
  return { w, F: w.__dzFils, appels, dialogues };
}

function serveur(etat, extra = () => null) {
  return (url, o) => {
    const x = extra(url, o);
    if (x) return x;
    if (url === "/api/news/fils" && (!o.method || o.method === "GET")) return { corps: etat() };
    return { corps: {} };
  };
}

async function monte(lang, rep) {
  const m = monde(lang, rep);
  const h = new Noeud("div");
  m.F.monter(h);
  await dort(5);
  return Object.assign(m, { h });
}

// ── 1. la liste, en FR puis en EN ──
for (const lang of ["fr", "en"]) {
  const { h, appels } = await monte(lang, serveur(() => LISTE([RD, XF, XA])));
  const t = texte(h);
  const L = (fr, en) => (lang === "fr" ? fr : en);
  ok(`1.${lang} titre et aide`, t.includes(L("Fils suivis", "Followed feeds")) && t.includes(L("Suggérés par les agents", "Suggested by agents")), t);
  ok(`1.${lang} aucune clé brute`, !t.includes("⟦"), t);
  ok(`1.${lang} aucune chaîne de l'autre langue`, lang === "fr" ? !/Followed|Read now|Suggested/.test(t) : !/Fils suivis|Lire maintenant|Suggérés|Mettre en pause/.test(t), t);
  ok(`1.${lang} un appel GET`, appels.length === 1 && appels[0].url === "/api/news/fils");
  const lr = un(h, "data-dz-fil-id", "fil_rd"), lx = un(h, "data-dz-fil-id", "fil_x"), la = un(h, "data-dz-fil-id", "fil_xa");
  ok(`1.${lang} pastilles de plateforme`, un(lr, "data-dz-fils-plateforme", "reddit").textContent === "RD"
     && un(lx, "data-dz-fils-plateforme", "x").textContent === "X" && un(lx, "data-dz-fils-plateforme", "x").attrs.title === "X");
  ok(`1.${lang} flux gratuit : lecture, état, dernière lecture, nombre`, texte(lr).includes(L("Gratuit (flux)", "Free (feed)"))
     && texte(lr).includes(L("À jour", "Up to date")) && texte(lr).includes(L("25 au dernier relevé", "25 on the last fetch"))
     && texte(lr).includes(L("Lu le", "Read on")), texte(lr));
  ok(`1.${lang} fil payant sans accord : devis à accepter, « Voir le devis », pas de lecture`,
     texte(lx).includes(L("Devis à accepter", "Quote to accept")) && un(lx, "data-dz-fils-action", "devis")
     && !un(lx, "data-dz-fils-action", "lire"), texte(lx));
  ok(`1.${lang} origine : à la main / suggéré par l'agent (travail)`, texte(un(lr, "data-dz-fils", "origine")) === L("Ajouté à la main", "Added by hand")
     && texte(un(lx, "data-dz-fils", "origine")) === L("Suggéré par l'agent (Veille)", "Suggested by the agent (Watch)"));
  ok(`1.${lang} fil payant avec accord : plafond, coût, « Retirer l'accord », en pause → reprendre`,
     texte(un(la, "data-dz-fils", "accord")) === L("Plafond 0,40 $ par relevé", "Cap $0.40 per fetch")
     && texte(un(la, "data-dz-fils", "lecture")).includes(L("dernier relevé 0,05 $ · total 0,15 $", "last fetch $0.05 · total $0.15"))
     && un(la, "data-dz-fils-action", "retirer-accord") && un(la, "data-dz-fils-action", "reprendre")
     && texte(la).includes(L("En pause", "Paused")), texte(la));
  const sel = un(lr, "data-dz-fils-action", "frequence");
  ok(`1.${lang} fréquence en ligne, valeur du fil`, sel && sel.value === "6" && sel.children.length === 7
     && sel.children[0].textContent === L("toutes les 1 h", "every 1 h"));
  const sg = un(h, "data-dz-fils", "suggestions");
  ok(`1.${lang} suggestions : la seule proposée, son compte, sa raison et son origine`,
     parAttr(sg, "data-dz-suggestion-id").length === 1 && texte(sg).includes(L("Suggérés par les agents (1)", "Suggested by agents (1)"))
     && texte(un(sg, "data-dz-fils", "raison")) === "le concurrent y annonce ses sorties"
     && texte(un(sg, "data-dz-fils", "origine")).startsWith(L("Agent Campagnes · Veille · ", "Campaigns agent · Watch · ")), texte(sg));
}

// ── 2. ajout à la main ──
{
  let fils = [];
  const { h, appels } = await monte("fr", serveur(() => LISTE(fils, []), (url, o) => {
    if (url === "/api/news/fils" && o.method === "POST") {
      const c = JSON.parse(o.body);
      if (c.plateforme === "youtube") return { ok: false, status: 400, corps: { detail: "chaîne YouTube : collez l'identifiant UC…" } };
      fils = [RD]; return { corps: { fil: RD } };
    }
    return null;
  }));
  ok("2.1 vide : le dit", texte(h).includes("Aucun fil suivi.") && texte(h).includes("Aucune suggestion en attente."));
  un(h, "data-dz-fils-action", "ajouter").ec.click();
  let f = un(h, "data-dz-fils", "formulaire");
  ok("2.2 le formulaire s'ouvre (YouTube par défaut, aide UC…)", f && un(f, "data-dz-fils-champ", "plateforme").value === "youtube"
     && un(f, "data-dz-fils-champ", "identifiant").attrs.placeholder === "Identifiant de chaîne UC… ou adresse /channel/UC…", texte(h));
  const id = un(f, "data-dz-fils-champ", "identifiant"); id.value = "@chaine"; id.ec.input();
  un(f, "data-dz-fils-action", "valider").ec.click();
  await dort(5);
  ok("2.3 refus du serveur affiché, formulaire gardé", texte(un(h, "data-dz-fils", "message")) === "chaîne YouTube : collez l'identifiant UC…"
     && un(h, "data-dz-fils", "formulaire"), texte(h));
  f = un(h, "data-dz-fils", "formulaire");
  const sp = un(f, "data-dz-fils-champ", "plateforme"); sp.value = "reddit"; sp.ec.change();
  f = un(h, "data-dz-fils", "formulaire");
  ok("2.4 aide selon la plateforme (Reddit), saisie gardée", un(f, "data-dz-fils-champ", "identifiant").attrs.placeholder === "r/communauté, u/compte ou leur adresse"
     && un(f, "data-dz-fils-champ", "identifiant").value === "@chaine");
  const id2 = un(f, "data-dz-fils-champ", "identifiant"); id2.value = "r/videoediting"; id2.ec.input();
  const fq = un(f, "data-dz-fils-action", "frequence-form"); fq.value = "6"; fq.ec.change();
  un(f, "data-dz-fils-action", "valider").ec.click();
  await dort(5);
  const post = appels.filter((a) => a.methode === "POST").pop();
  ok("2.5 corps envoyé : plateforme, identifiant, nom nul, fréquence", JSON.stringify(post.corps)
     === JSON.stringify({ plateforme: "reddit", identifiant: "r/videoediting", nom: null, frequence_h: 6 }), JSON.stringify(post.corps));
  ok("2.6 formulaire refermé, liste rechargée", !un(h, "data-dz-fils", "formulaire") && un(h, "data-dz-fil-id", "fil_rd"));
}

// ── 3. devis puis accord d'un fil payant ──
for (const cle of [true, false]) {
  let fils = [XF];
  const { h, appels } = await monte("fr", serveur(() => LISTE(fils, []), (url, o) => {
    if (url === "/api/news/fils/fil_x/devis") return { corps: { gratuit: false, devis_usd: 0.12, max: 20, plafond_max_usd: 2, configure: cle } };
    if (url === "/api/news/fils/fil_x/accord") { fils = [Object.assign({}, XF, { accord: { plafond_usd: 0.5 }, etat: "jamais_lu" })]; return { corps: {} }; }
    return null;
  }));
  un(h, "data-dz-fils-action", "devis").ec.click();
  await dort(5);
  const c = un(h, "data-dz-fils", "devis");
  ok(`3.${cle} la carte de devis : montant, nombre, plafond proposé, borne`, c && texte(c).includes("Chaque relevé coûte au plus 0,12 $ pour 20 publications (Apify).")
     && texte(c).includes("au plus 2,00 $") && un(c, "data-dz-fils-champ", "plafond").value === "0.18", c && texte(c));
  if (cle) {
    const pl = un(c, "data-dz-fils-champ", "plafond"); pl.value = "0.5"; pl.ec.input();
    un(c, "data-dz-fils-action", "accepter-devis").ec.click();
    await dort(5);
    const a = appels.find((x) => x.url === "/api/news/fils/fil_x/accord");
    ok("3.1 accepter : confirme_cout et le plafond choisi", a && a.methode === "POST" && a.corps.confirme_cout === true && a.corps.plafond_usd === 0.5, JSON.stringify(a));
    const l = un(h, "data-dz-fil-id", "fil_x");
    ok("3.2 après l'accord : plafond affiché, « Lire maintenant », plus de carte", !un(h, "data-dz-fils", "devis")
       && texte(un(l, "data-dz-fils", "accord")) === "Plafond 0,50 $ par relevé" && un(l, "data-dz-fils-action", "lire"), texte(l));
  } else {
    ok("3.3 sans clé Apify : dit, « Accepter le devis » désactivé", texte(un(c, "data-dz-fils", "sans-cle")) === "Posez d'abord la clé Apify dans Réglages › Clés d'API."
       && un(c, "data-dz-fils-action", "accepter-devis").disabled === true);
    un(c, "data-dz-fils-action", "annuler-devis").ec.click();
    ok("3.4 annuler ferme la carte sans appel", !un(h, "data-dz-fils", "devis") && !appels.some((x) => x.url.endsWith("/accord")));
  }
}

// ── 4. lecture, pause, fréquence, retrait ──
{
  let fils = [RD];
  const { w, h, appels, dialogues } = await monte("en", serveur(() => LISTE(fils, []), (url, o) => {
    if (url === "/api/news/fils/fil_rd/lire") return { corps: { lus: 3, cout_usd: 0, fil: RD } };
    if (url === "/api/news/fils/fil_rd" && o.method === "PATCH") return { corps: { fil: RD } };
    if (url === "/api/news/fils/fil_rd" && o.method === "DELETE") { fils = []; return { corps: {} }; }
    return null;
  }));
  un(h, "data-dz-fils-action", "lire").ec.click();
  ok("4.1 pendant la lecture : bouton désactivé", un(h, "data-dz-fils-action", "lire").disabled === true
     && un(h, "data-dz-fils-action", "lire").textContent === "Reading…");
  await dort(10);
  ok("4.2 lecture : POST, message traduit", appels.some((a) => a.url === "/api/news/fils/fil_rd/lire" && a.methode === "POST")
     && texte(un(h, "data-dz-fils", "message")) === "3 post(s) read", texte(h));
  un(h, "data-dz-fils-action", "pause").ec.click();
  await dort(5);
  ok("4.3 pause : PATCH {pause: true}", appels.some((a) => a.methode === "PATCH" && a.corps.pause === true));
  const s = un(h, "data-dz-fils-action", "frequence"); s.value = "12"; s.ec.change();
  await dort(5);
  ok("4.4 fréquence : PATCH {frequence_h: 12}", appels.some((a) => a.methode === "PATCH" && a.corps.frequence_h === 12));
  un(h, "data-dz-fils-action", "retirer").ec.click();
  await dort(5);
  ok("4.5 retrait refusé à la confirmation : aucun DELETE", dialogues.length === 1 && dialogues[0] === "Stop following r/videoediting? Its posts leave News."
     && !appels.some((a) => a.methode === "DELETE"), dialogues);
  w.__oui = true;
  un(h, "data-dz-fils-action", "retirer").ec.click();
  await dort(10);
  ok("4.6 retrait confirmé : DELETE puis liste vide", appels.some((a) => a.methode === "DELETE" && a.url === "/api/news/fils/fil_rd")
     && texte(h).includes("No followed feeds."));
}

// ── 5. erreur structurée (409) d'une lecture ──
{
  const XA2 = Object.assign({}, XA, { pause: false });
  const { h } = await monte("fr", serveur(() => LISTE([XA2], []), (url) => url.endsWith("/lire")
    ? { ok: false, status: 409, corps: { detail: { code: "devis_depasse", message: "le devis du relevé (0.80 $) dépasse le plafond du fil (0.40 $)" } } } : null));
  un(h, "data-dz-fils-action", "lire").ec.click();
  await dort(10);
  ok("5.1 le message d'un détail structuré est affiché", texte(un(h, "data-dz-fils", "message")) === "le devis du relevé (0.80 $) dépasse le plafond du fil (0.40 $)", texte(h));
}

// ── 6. suggestions : accepter, écarter ──
{
  let sug = [SUG[0], Object.assign({}, SUG[0], { id: "sug_b", nom: "@b" })];
  const { h, appels } = await monte("fr", serveur(() => LISTE([], sug), (url) => {
    if (url.endsWith("/accepter")) { sug = sug.filter((s) => s.id !== "sug_ig"); return { corps: { fil: RD } }; }
    if (url.endsWith("/ecarter")) { sug = sug.filter((s) => s.id !== "sug_b"); return { corps: {} }; }
    return null;
  }));
  un(un(h, "data-dz-suggestion-id", "sug_ig"), "data-dz-fils-action", "accepter").ec.click();
  await dort(5);
  ok("6.1 accepter : POST …/suggestions/sug_ig/accepter, la suggestion quitte la file",
     appels.some((a) => a.methode === "POST" && a.url === "/api/news/fils/suggestions/sug_ig/accepter")
     && !un(h, "data-dz-suggestion-id", "sug_ig"));
  un(un(h, "data-dz-suggestion-id", "sug_b"), "data-dz-fils-action", "ecarter").ec.click();
  await dort(5);
  ok("6.2 écarter : POST …/suggestions/sug_b/ecarter", appels.some((a) => a.url === "/api/news/fils/suggestions/sug_b/ecarter")
     && texte(h).includes("Aucune suggestion en attente."));
}

// ── 7. serveur absent, montage unique, aucun innerHTML ──
{
  const { h, F } = await monte("fr", () => ({ ok: false, status: 500, corps: { detail: "panne" } }));
  ok("7.1 serveur en panne : dit, sans bouton d'ajout", texte(h).includes("Fils indisponibles : panne") && !un(h, "data-dz-fils-action", "ajouter"));
  ok("7.2 monter deux fois le même hôte : un seul panneau", F.monter(h) === h.__dzFils);
}
ok("7.3 aucun innerHTML", INNER.length === 0, INNER);

if (echecs.length) { console.log(echecs.join("\n")); console.log(`${n - echecs.length}/${n} ok`); process.exit(1); }
console.log(`${n}/${n} ok`);
