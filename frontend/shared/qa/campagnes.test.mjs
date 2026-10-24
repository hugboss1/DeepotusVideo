// t285 (T8) — dz-campagnes.js : le composant partagé de conversation de l'agent Campagnes, joué sur un DOM simulé.
// Séries : devis_affiche_avant_envoi, carte_devis_appelle_la_route_puis_carte, aucun_bouton_publier,
// espace_non_modifiable (+ portes, continuer, erreurs HTTP, flux SSE, démontage, anglais).
// Lancer : node frontend/shared/qa/campagnes.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = process.env.DZ_CAMPAGNES_SRC
  ? readFileSync(process.env.DZ_CAMPAGNES_SRC, "utf8")
  : readFileSync(new URL("../dz-campagnes.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const J = (x) => JSON.parse(JSON.stringify(x));
const attendre = async (cond, ms = 3000) => {
  const fin = Date.now() + ms;
  while (Date.now() < fin) { if (cond()) return true; await new Promise((r) => setTimeout(r, 5)); }
  return !!cond();
};
const tick = () => new Promise((r) => setTimeout(r, 15));

// ---- le DOM simulé -------------------------------------------------------------------------------------------------
class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; this.scrollTop = 0; this.scrollHeight = 0; }
  get firstChild() { return this.children[0] || null; }
  get parentNode() { return this.parent; }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  focus() { Noeud.focus = this; }
  fire(t, ev = {}) { const e = { type: t, target: this, preventDefault() { this.empeche = true; }, ...ev }; (this.ec[t] || []).forEach((f) => f(e)); return e; }
  click() { return this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tousLes = (racine, pred) => [...racine.tous()].filter(pred);
const boutons = (racine) => tousLes(racine, (x) => x.tagName === "BUTTON" || x.tagName === "A");
const parTexte = (racine, re) => boutons(racine).filter((b) => re.test(b.textContent));
const marque = (racine, v) => tousLes(racine, (x) => x.attrs["data-dz-camp"] === v)[0];

// ---- le monde : window, document, fetch scripté, dzT du vrai dictionnaire ----------------------------------------------
function dictionnaire() {
  const ctx = { window: {} };
  vm.createContext(ctx);
  vm.runInContext(DICO, ctx);
  return ctx.window.DZ_I18N;
}
const D = dictionnaire();
function dzTde(lang) {
  return (cle, vars) => {
    const e = D[cle];
    if (!e) return cle;
    let s = e[lang] || e.fr;
    if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
    return s;
  };
}
const enc = new TextEncoder();
function reponse(status, json, extra = {}) {
  return { ok: status >= 200 && status < 300, status, headers: { get: (k) => (extra.headers || {})[k.toLowerCase()] || null },
    json: async () => (json === undefined ? {} : J(json)), text: async () => JSON.stringify(json), body: extra.body || null };
}
// un flux SSE coupé en morceaux de `taille` octets : une ligne `data:` peut tomber à cheval
function flux(evts, taille = 17) {
  const octets = enc.encode(evts.map((e) => "data: " + JSON.stringify(e) + "\n\n").join(""));
  let i = 0;
  return reponse(200, undefined, { body: { getReader: () => ({ read: async () => (i >= octets.length ? { done: true } : (() => { const v = octets.slice(i, i + taille); i += taille; return { done: false, value: v }; })()) }) } });
}

function monde({ lang = "fr", routes = {} } = {}) {
  const appels = [];
  const events = [];
  const win = {
    dzT: dzTde(lang), dzLang: () => lang,
    dispatchEvent: (e) => { events.push({ type: e.type, detail: e.detail }); return true; },
    fetch: async (url, init = {}) => {
      const corps = init.body ? JSON.parse(init.body) : undefined;
      appels.push({ url: String(url), methode: init.method || "GET", corps, signal: init.signal });
      if (win.coupe) throw new Error("réseau coupé");
      for (const [motif, f] of Object.entries(routes)) {
        const [m, u] = motif.split(" ");
        if (m === (init.method || "GET") && (u === String(url) || (u.endsWith("*") && String(url).startsWith(u.slice(0, -1))))) return await f(corps, String(url));
      }
      return reponse(404, { detail: "route absente du banc : " + url });
    }
  };
  const doc = { createElement: (t) => new Noeud(t), head: new Noeud("head"), documentElement: new Noeud("html") };
  const ctx = { window: win, document: doc, setTimeout, clearTimeout, TextDecoder, CustomEvent, AbortController, console };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { win, doc, appels, events, DzCampagnes: win.DzCampagnes };
}

// ---- des conversations types ---------------------------------------------------------------------------------------------
const msg = (role, blocs, id) => ({ v: 1, id: id || role + Math.random(), role, quand: "2026-10-24T10:00:00Z", origine: "pc", appareil: null, blocs, cout_paye: 0 });
const carte = (genre, extra = {}) => ({ type: "carte", genre, libelle: "LIBELLE SERVEUR FR", etat: "proposee", ...extra });
const conv = (messages, extra = {}) => ({ id: "c1", espace_id: "e1", role: "campagnes", titre: "", etat_porte: "aucune", cout_usd: 0.5, messages, ...extra });
const CORPS_VIDEO = { image_filename: "a.png", prompt: "p", duration_s: 5, resolution: "1080p", espace_id: "e1" };
const DEVIS_VIDEO = carte("devis", { devis: 0.8, action: "generer", arguments: { genre: "video", route: "/api/generate", corps: CORPS_VIDEO, usd: 0.8, espace_id: "e1", ops: [] } });
const DEVIS_IMAGE = carte("devis", { devis: 0.04, action: "generer", arguments: { genre: "image", route: "/api/images/generate", corps: { prompt: "x", n: 1, model: "flux", espace_id: "e1" }, usd: 0.04, espace_id: "e1", ops: [] } });
const DEVIS_VOIX = carte("devis", { devis: 0.05, action: "generer", arguments: { genre: "voix", route: "/api/audio/voiceover", corps: { script: "salut", espace_id: "e1" }, usd: 0.05, espace_id: "e1", ops: [] } });
const PORTE = carte("porte", { action: "valider_porte", arguments: { numero: 1, resume: "Ligne 1\nLigne 2", calendrier: [{ quand: "2026-11-02", canal: "x", sujet: "Lancement" }] } });
const ESPACE = carte("espace", { action: "choisir_espace", arguments: { espaces: [{ id: "e1", nom: "Marque A" }, { id: "e2", nom: "Marque B" }] } });
const CONTINUER = carte("continuer", { devis: 1.234, action: "continuer", arguments: { motif: "plafond", devis: { plafond_usd: 1.234, in_tok: 1, out_tok: 1 }, depense_usd: 0.3, texte: "Continue là où tu t'es arrêté." } });
const BROUILLONS = carte("brouillons", { action: "ouvrir_planificateur", arguments: { ids: ["p1", "p2"], espace_id: "e1" } });

const ESPACES = { "GET /api/espaces*": async () => reponse(200, { espaces: [{ id: "e1", nom: "Marque A" }, { id: "e2", nom: "Marque B" }], actif: "e1" }) };
const avec = (lire, extra = {}) => ({ "GET /api/agent/campagnes/c1": async () => reponse(200, typeof lire === "function" ? lire() : lire), ...ESPACES, ...extra });

async function monterAvec(routes, opts = {}, lang = "fr") {
  const m = monde({ lang, routes });
  const hote = new Noeud("div");
  const c = m.DzCampagnes.monter(hote, { cid: "c1", role: "campagnes", contexte: "planificateur", ...opts });
  await attendre(() => m.appels.some((a) => a.methode === "GET" && a.url === "/api/agent/campagnes/c1"));
  await tick(); await tick();
  return { ...m, hote, c, racine: hote.children[0] };
}
const saisir = (racine, texte) => { const ch = marque(racine, "champ"); ch.value = texte; ch.fire("input"); return ch; };
const bEnvoyer = (racine) => marque(racine, "envoyer");
const texte = (racine) => racine.textContent;

// ===== 1. devis_affiche_avant_envoi ===============================================================================
{
  const DEVIS = { plafond_usd: 0.4123, in_tok: 1000, out_tok: 16000, modele: "claude-opus-4" };
  let relu = 0;
  const routes = avec(() => conv(relu ? [msg("utilisateur", [{ type: "texte", texte: "Lance la campagne" }]), msg("agent", [{ type: "texte", texte: "Bonjour, voici le plan." }])] : [], { cout_usd: relu ? 0.77 : 0.5 }), {
    "POST /api/agent/campagnes/c1/devis": async () => reponse(200, DEVIS),
    "POST /api/agent/campagnes/c1/message": async () => { relu = 1; return flux([{ type: "texte", texte: "Bonjour, voici le plan." }, { type: "outil", nom: "lire_espace", ok: true, resume: "ok" }, { type: "fin", motif: "reponse", cout_usd: 0.27 }]); }
  });
  const w = await monterAvec(routes);
  ok("1.0 l'espace est écrit en clair (son nom, pas l'identifiant)", /Marque A/.test(texte(marque(w.racine, "espace"))) && !/e1/.test(texte(marque(w.racine, "espace"))), texte(marque(w.racine, "espace")));
  ok("1.1 le coût cumulé est affiché", /0,50 \$/.test(texte(marque(w.racine, "cout"))), texte(marque(w.racine, "cout")));
  saisir(w.racine, "Lance la campagne");
  ok("1.2 le champ et le bouton ne sont jamais grisés", !("disabled" in marque(w.racine, "champ").attrs) && !("disabled" in bEnvoyer(w.racine).attrs));
  ok("1.3 rien ne part avant la pause de saisie", !w.appels.some((a) => a.url.endsWith("/devis")));
  await attendre(() => w.appels.some((a) => a.url.endsWith("/devis")));
  await tick();
  const iDevis = w.appels.findIndex((a) => a.url.endsWith("/devis"));
  ok("1.4 le devis est demandé AVANT l'envoi, avec le texte", iDevis >= 0 && w.appels[iDevis].corps.texte === "Lance la campagne", JSON.stringify(w.appels));
  ok("1.5 aucun /message n'est parti", !w.appels.some((a) => a.url.endsWith("/message")));
  ok("1.6 « ≤ 0,42 $ » est affiché (le plafond arrondi vers le haut)", /≤ 0,42 \$/.test(texte(marque(w.racine, "devis"))), texte(marque(w.racine, "devis")));
  let vuParLEnveloppe = 0; // dz-plafonds.js enveloppe window.fetch APRÈS le montage : le 402 du premier tour doit le traverser
  const brut = w.win.fetch; w.win.fetch = (u, i) => { if (String(u).endsWith("/message")) vuParLEnveloppe++; return brut(u, i); };
  bEnvoyer(w.racine).click();
  await attendre(() => w.appels.some((a) => a.url.endsWith("/message")));
  const iMsg = w.appels.findIndex((a) => a.url.endsWith("/message"));
  ok("1.7 l'envoi vient après le devis", iMsg > iDevis);
  ok("1.7b l'envoi traverse le window.fetch enveloppé après coup (402 -> dialogue des plafonds)", vuParLEnveloppe === 1);
  ok("1.8 l'envoi porte le plafond EXACT du devis et le texte", w.appels[iMsg].corps.plafond_usd === 0.4123 && w.appels[iMsg].corps.texte === "Lance la campagne", JSON.stringify(w.appels[iMsg]));
  await attendre(() => /voici le plan/.test(texte(marque(w.racine, "fil"))) && !marque(w.racine, "travail"));
  await tick();
  ok("1.9 la réponse en flux (coupée en morceaux) arrive dans le fil", /Bonjour, voici le plan\./.test(texte(marque(w.racine, "fil"))));
  ok("1.10 la conversation est relue (GET) et le coût cumulé suit", /0,77 \$/.test(texte(marque(w.racine, "cout"))), texte(marque(w.racine, "cout")));
  ok("1.11 le champ est vidé après l'envoi", marque(w.racine, "champ").value === "");
  w.c.demonter();
}
{ // un clic AVANT que le devis soit là : il ne fait que l'afficher (l'envoi vaut accord, il faut l'avoir vu)
  const routes = avec(() => conv([]), {
    "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 1.5, in_tok: 1, out_tok: 1, modele: "m" }),
    "POST /api/agent/campagnes/c1/message": async () => flux([{ type: "texte", texte: "ok" }, { type: "fin", motif: "reponse", cout_usd: 0.1 }])
  });
  const w = await monterAvec(routes);
  saisir(w.racine, "Vite");
  bEnvoyer(w.racine).click();
  await attendre(() => /≤ 1,50 \$/.test(texte(marque(w.racine, "devis"))));
  await tick();
  ok("1.12 clic sans devis : le devis s'affiche", /≤ 1,50 \$/.test(texte(marque(w.racine, "devis"))));
  ok("1.13 …et RIEN n'est envoyé", !w.appels.some((a) => a.url.endsWith("/message")), JSON.stringify(w.appels.map((a) => a.url)));
  bEnvoyer(w.racine).click();
  await attendre(() => w.appels.some((a) => a.url.endsWith("/message")));
  ok("1.14 le second clic envoie, au plafond vu", w.appels.find((a) => a.url.endsWith("/message")).corps.plafond_usd === 1.5);
  await tick();
  w.c.demonter();
}
{ // modifier le texte invalide le devis : l'ancien plafond ne vaut plus accord pour un autre texte
  const routes = avec(() => conv([]), {
    "POST /api/agent/campagnes/c1/devis": async (c) => reponse(200, { plafond_usd: c.texte.length / 10, in_tok: 1, out_tok: 1, modele: "m" }),
    "POST /api/agent/campagnes/c1/message": async () => flux([{ type: "fin", motif: "reponse", cout_usd: 0 }])
  });
  const w = await monterAvec(routes);
  saisir(w.racine, "aaaaaaaaaa");
  await attendre(() => /≤ 1,00 \$/.test(texte(marque(w.racine, "devis"))));
  saisir(w.racine, "aaaaaaaaaaaaaaaaaaaa");
  ok("1.15 le texte change : l'ancien plafond disparaît tout de suite", !/≤/.test(texte(marque(w.racine, "devis"))), texte(marque(w.racine, "devis")));
  bEnvoyer(w.racine).click();
  await tick();
  ok("1.16 …et n'envoie pas avec l'ancien plafond", !w.appels.some((a) => a.url.endsWith("/message")));
  w.c.demonter();
}
{ // le brief posé au montage : dans le champ, devis demandé, jamais envoyé tout seul
  const routes = avec(() => conv([]), { "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 2, in_tok: 1, out_tok: 1, modele: "m" }) });
  const w = await monterAvec(routes, { brief: "Brief du lancement" });
  await attendre(() => /≤ 2,00 \$/.test(texte(marque(w.racine, "devis"))));
  ok("1.17 le brief est dans le champ, son devis affiché", marque(w.racine, "champ").value === "Brief du lancement" && /≤ 2,00 \$/.test(texte(marque(w.racine, "devis"))));
  ok("1.18 le brief n'est jamais envoyé tout seul", !w.appels.some((a) => a.url.endsWith("/message")));
  w.c.demonter();
}
{ // sans cid : la conversation naît au premier besoin, dans l'espace demandé
  let surCid = null;
  const routes = { ...ESPACES,
    "POST /api/agent/campagnes/": async (c) => reponse(200, conv([], { id: "neuf", espace_id: c.espace_id, cout_usd: 0 })),
    "POST /api/agent/campagnes/neuf/devis": async () => reponse(200, { plafond_usd: 0.1, in_tok: 1, out_tok: 1, modele: "m" }) };
  const m = monde({ routes });
  const hote = new Noeud("div");
  const c = m.DzCampagnes.monter(hote, { role: "campagnes", espace_id: "e2", contexte: "f1", surCid: (id) => { surCid = id; } });
  await tick();
  ok("1.19 avant tout besoin, aucune conversation n'est créée", !m.appels.some((a) => a.methode === "POST"));
  ok("1.20 l'espace demandé est écrit en clair dès le montage", /Marque B/.test(texte(hote)), texte(hote));
  saisir(hote.children[0], "Salut");
  await attendre(() => m.appels.some((a) => a.url.endsWith("/neuf/devis")));
  const cree = m.appels.find((a) => a.methode === "POST" && a.url === "/api/agent/campagnes/");
  ok("1.21 la création porte rôle et espace", cree && cree.corps.role === "campagnes" && cree.corps.espace_id === "e2", JSON.stringify(cree));
  ok("1.22 surCid reçoit l'identifiant, cid() le rend", surCid === "neuf" && c.cid() === "neuf");
  ok("1.23 le contexte est posé sur la racine", hote.children[0].attrs["data-contexte"] === "f1");
  c.demonter();
}

// ===== 2. carte_devis_appelle_la_route_puis_carte ==============================================================================
{
  const faits = [];
  const routes = avec(() => conv([msg("agent", [{ type: "texte", texte: "Voici un devis." }, DEVIS_VIDEO])]), {
    "POST /api/generate": async () => reponse(200, { job_id: "J-42", status: "queued", message: "ok" }),
    "POST /api/agent/campagnes/c1/carte/0": async (c) => { faits.push(c); return reponse(200, conv([msg("agent", [DEVIS_VIDEO])])); }
  });
  const w = await monterAvec(routes);
  const lib = texte(w.racine);
  ok("2.0 le libellé est celui de l'écran (dzT), pas celui du serveur", /Devis vidéo : 0,80 \$/.test(lib) && !/LIBELLE SERVEUR/.test(lib), lib);
  const [gen] = parTexte(w.racine, /Générer/);
  ok("2.1 le bouton de génération montre le montant", gen && /0,80 \$/.test(gen.textContent), gen && gen.textContent);
  gen.click(); gen.click();
  await attendre(() => w.appels.some((a) => a.url.endsWith("/carte/0")));
  const iGen = w.appels.findIndex((a) => a.url === "/api/generate");
  const iCarte = w.appels.findIndex((a) => a.url.endsWith("/carte/0"));
  ok("2.2 LA route de génération est appelée d'abord, avec le corps de la carte", iGen >= 0 && JSON.stringify(w.appels[iGen].corps) === JSON.stringify(CORPS_VIDEO), JSON.stringify(w.appels[iGen]));
  ok("2.3 puis /carte/0 avec le job_id", iCarte > iGen && faits[0].decision === "acceptee" && faits[0].job_id === "J-42", JSON.stringify(faits));
  ok("2.4 un double clic ne génère (et ne paie) qu'UNE fois", w.appels.filter((a) => a.url === "/api/generate").length === 1);
  w.c.demonter();
}
{ // image : le nom du fichier est images[0] ; voix : filename
  for (const [c, route, rep, attendu] of [[DEVIS_IMAGE, "/api/images/generate", { images: ["img-1.png"], model: "flux" }, { fichier: "img-1.png" }],
    [DEVIS_VOIX, "/api/audio/voiceover", { ok: true, filename: "narration-123456.mp3", url: "/api/audio/x" }, { fichier: "narration-123456.mp3" }]]) {
    const faits = [];
    const routes = avec(() => conv([msg("agent", [c])]), {
      ["POST " + route]: async () => reponse(200, rep),
      "POST /api/agent/campagnes/c1/carte/0": async (b) => { faits.push(b); return reponse(200, conv([msg("agent", [c])])); }
    });
    const w = await monterAvec(routes);
    parTexte(w.racine, /Générer/)[0].click();
    await attendre(() => faits.length);
    ok("2.5 " + c.arguments.genre + " : /carte reçoit le nom du fichier produit", JSON.stringify(faits[0]) === JSON.stringify({ decision: "acceptee", ...attendu }), JSON.stringify(faits));
    w.c.demonter();
  }
}
{ // la génération échoue : AUCUN /carte, l'erreur est dite, le bouton reste utilisable
  const routes = avec(() => conv([msg("agent", [DEVIS_VIDEO])]), { "POST /api/generate": async () => reponse(502, { detail: "fal est en panne" }) });
  const w = await monterAvec(routes);
  parTexte(w.racine, /Générer/)[0].click();
  await attendre(() => /fal est en panne/.test(texte(marque(w.racine, "statut"))));
  ok("2.6 échec : l'erreur du serveur est affichée", /La génération n'a pas abouti : fal est en panne/.test(texte(marque(w.racine, "statut"))), texte(marque(w.racine, "statut")));
  ok("2.7 échec : aucun /carte", !w.appels.some((a) => a.url.includes("/carte/")));
  ok("2.8 échec : le bouton reste là", parTexte(w.racine, /Générer/).length === 1);
  w.c.demonter();
}
{ // une carte qui désigne une AUTRE route que celle de son genre : rien ne part
  const louche = carte("devis", { devis: 1, arguments: { genre: "video", route: "/api/reglages/cles", corps: {}, usd: 1, ops: [] } });
  const w = await monterAvec(avec(() => conv([msg("agent", [louche])])));
  parTexte(w.racine, /Générer/)[0].click();
  await tick();
  ok("2.9 route hors liste : aucun appel", !w.appels.some((a) => a.url === "/api/reglages/cles" || a.url.includes("/carte/")));
  w.c.demonter();
}
{ // un 402 est le travail de dz-plafonds.js : le composant lit window.fetch À CHAQUE APPEL (enveloppe posée après le montage)
  let envoyes = 0;
  const routes = avec(() => conv([msg("agent", [DEVIS_IMAGE])]), {
    "POST /api/images/generate": async () => reponse(200, { images: ["z.png"] }),
    "POST /api/agent/campagnes/c1/carte/0": async () => reponse(200, conv([msg("agent", [DEVIS_IMAGE])]))
  });
  const w = await monterAvec(routes);
  const brut = w.win.fetch;
  w.win.fetch = async (u, i) => { if (u === "/api/images/generate") envoyes++; return brut(u, i); };
  parTexte(w.racine, /Générer/)[0].click();
  await attendre(() => envoyes);
  ok("2.10 la génération passe par le window.fetch enveloppé après coup (dz-plafonds)", envoyes === 1);
  await tick();
  w.c.demonter();
}
{ // l'état de la carte vient des messages « fait » : lancée, puis terminée (avec l'action continuer) ; échec dit
  const fait = (etat, args) => msg("fait", [{ ...DEVIS_VIDEO, etat, arguments: { carte: 0, ...args } }]);
  const lancee = await monterAvec(avec(() => conv([msg("agent", [DEVIS_VIDEO]), fait("acceptee", { job_id: "J1" })])));
  ok("2.11 acceptée : « Génération lancée », plus de bouton Générer", /Génération lancée/.test(texte(lancee.racine)) && !parTexte(lancee.racine, /Générer/).length);
  lancee.c.demonter();
  const finie = await monterAvec(avec(() => conv([msg("agent", [DEVIS_VIDEO]), fait("acceptee", { job_id: "J1" }), fait("terminee", { job_id: "J1", statut: "done" })])));
  ok("2.12 terminée : « Rendu terminé » et un bouton pour continuer", /Rendu terminé/.test(texte(finie.racine)) && parTexte(finie.racine, /Continuer la campagne/).length === 1);
  parTexte(finie.racine, /Continuer la campagne/)[0].click();
  ok("2.13 « Continuer » pose le texte dans le champ, sans rien envoyer", /Continue là où tu t'es arrêté\./.test(marque(finie.racine, "champ").value) && !finie.appels.some((a) => a.url.endsWith("/message")));
  finie.c.demonter();
  const ratee = await monterAvec(avec(() => conv([msg("agent", [DEVIS_VIDEO]), fait("acceptee", { job_id: "J1" }), fait("terminee", { job_id: "J1", statut: "failed" })])));
  ok("2.14 échec du rendu : dit", /Le rendu a échoué/.test(texte(ratee.racine)));
  ratee.c.demonter();
}

// ===== 3. aucun_bouton_publier =================================================================================================
for (const lang of ["fr", "en"]) {
  const base = conv([
    msg("utilisateur", [{ type: "texte", texte: "Go" }]),
    msg("agent", [{ type: "texte", texte: "Plan." }, PORTE, DEVIS_VIDEO, CONTINUER, BROUILLONS]),
    msg("agent", [ESPACE])
  ], { espace_id: null });
  const w = await monterAvec(avec(base), {}, lang);
  const liste = boutons(w.racine).map((b) => b.textContent);
  ok("3.1 [" + lang + "] des boutons existent (le test regarde bien)", liste.length >= 6, liste.join(" | "));
  ok("3.2 [" + lang + "] AUCUN bouton ni lien « publier » (ni post / programmer / fire)", !liste.some((t) => /publi|\bpost|\bfire\b|tweet|programm/i.test(t)), liste.join(" | "));
  ok("3.3 [" + lang + "] le seul lien mène au calendrier du Planificateur", boutons(w.racine).filter((b) => b.tagName === "A").length === 1);
  w.c.demonter();
}

// ===== 4. espace_non_modifiable =====================================================================================================
{
  const base = conv([msg("agent", [{ type: "texte", texte: "Je travaille pour Marque A." }, ESPACE])], { espace_id: "e1" });
  const w = await monterAvec(avec(base));
  const tete = marque(w.racine, "tete");
  ok("4.1 l'en-tête est du texte seul : aucun bouton, lien, champ ni liste", tousLes(tete, (x) => ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA"].includes(x.tagName)).length === 0);
  ok("4.2 aucun contrôle de saisie en dehors du champ de message (pas de select/input)", tousLes(w.racine, (x) => ["SELECT", "INPUT"].includes(x.tagName)).length === 0
    && tousLes(w.racine, (x) => x.tagName === "TEXTAREA").length === 1);
  ok("4.3 l'espace a déjà été fixé : la carte « espace » ne propose plus aucun choix", !parTexte(w.racine, /Marque (A|B)/).length, boutons(w.racine).map((b) => b.textContent).join("|"));
  const avant = w.appels.length;
  tete.click(); marque(w.racine, "espace").click();
  await tick();
  ok("4.4 cliquer l'espace ne déclenche rien", w.appels.length === avant);
  w.c.demonter();
}
{ // espace pas encore choisi : la carte liste les espaces ; le choix part avec espace_id et fixe le nom
  const faits = [];
  let choisi = false;
  const routes = avec(() => conv([msg("agent", [ESPACE])], { espace_id: choisi ? "e2" : null }), {
    "POST /api/agent/campagnes/c1/carte/0": async (c) => { faits.push(c); choisi = true; return reponse(200, conv([msg("agent", [ESPACE]), msg("fait", [{ ...ESPACE, etat: "acceptee", arguments: { carte: 0, espace_id: "e2" } }])], { espace_id: "e2" })); }
  });
  const w = await monterAvec(routes);
  ok("4.5 sans espace : l'en-tête le dit", /Aucun espace choisi/.test(texte(marque(w.racine, "espace"))));
  ok("4.6 la carte liste les espaces", parTexte(w.racine, /Marque A/).length === 1 && parTexte(w.racine, /Marque B/).length === 1);
  parTexte(w.racine, /Marque B/)[0].click();
  await attendre(() => faits.length);
  await tick();
  ok("4.7 le choix part en acceptee + espace_id", JSON.stringify(faits[0]) === JSON.stringify({ decision: "acceptee", espace_id: "e2" }), JSON.stringify(faits));
  ok("4.8 puis l'espace est écrit en clair et la liste a disparu", /Marque B/.test(texte(marque(w.racine, "espace"))) && !parTexte(w.racine, /Marque/).length, texte(w.racine));
  w.c.demonter();
}

// ===== 5. portes ===============================================================================================================
{
  const faits = [];
  const routes = avec(() => conv([msg("agent", [PORTE])]), {
    "POST /api/agent/campagnes/c1/carte/0": async (c) => { faits.push(c); return reponse(200, conv([msg("agent", [PORTE]), msg("fait", [{ ...PORTE, etat: c.decision, arguments: { carte: 0 } }])])); }
  });
  const w = await monterAvec(routes);
  ok("5.1 la porte affiche le résumé et le calendrier", /Ligne 1\nLigne 2/.test(texte(w.racine)) && /2026-11-02 · x · Lancement/.test(texte(w.racine)));
  ok("5.2 Valider et Modifier", parTexte(w.racine, /^Valider$/).length === 1 && parTexte(w.racine, /^Modifier$/).length === 1);
  parTexte(w.racine, /^Modifier$/)[0].click();
  await attendre(() => faits.length);
  await tick();
  ok("5.3 Modifier = refusee", faits[0].decision === "refusee");
  ok("5.4 …puis le champ attend la correction", /correction/.test(marque(w.racine, "champ").attrs.placeholder), marque(w.racine, "champ").attrs.placeholder);
  ok("5.5 …et le focus y va", Noeud.focus === marque(w.racine, "champ"));
  ok("5.6 la porte décidée n'a plus de boutons", !parTexte(w.racine, /^(Valider|Modifier)$/).length && /À corriger/.test(texte(w.racine)));
  w.c.demonter();
  const v = await monterAvec(routes);
  parTexte(v.racine, /^Valider$/)[0].click();
  await attendre(() => faits.length > 1);
  ok("5.7 Valider = acceptee", faits[1].decision === "acceptee");
  v.c.demonter();
}
{ // seule la DERNIÈRE porte se décide
  const w = await monterAvec(avec(() => conv([msg("agent", [PORTE]), msg("agent", [PORTE])])));
  ok("5.8 deux portes : un seul jeu de boutons (la dernière)", parTexte(w.racine, /^Valider$/).length === 1);
  w.c.demonter();
}

// ===== 6. continuer, brouillons ===================================================================================================
{
  const msgs = [];
  const faits = [];
  const routes = avec(() => conv([msg("agent", [CONTINUER])]), {
    "POST /api/agent/campagnes/c1/message": async (c) => { msgs.push(c); return flux([{ type: "texte", texte: "Je reprends." }, { type: "fin", motif: "reponse", cout_usd: 0.2 }]); },
    "POST /api/agent/campagnes/c1/carte/0": async (c) => { faits.push(c); return reponse(200, conv([msg("agent", [CONTINUER])])); }
  });
  const w = await monterAvec(routes);
  const [b] = parTexte(w.racine, /Continuer/);
  ok("6.1 la carte continuer affiche son montant (≤ 1,24 $, arrondi vers le haut)", /≤ 1,24 \$/.test(b.textContent), b.textContent);
  b.click();
  await attendre(() => faits.length);
  ok("6.2 le nouveau message porte le texte et le devis DE LA CARTE", msgs[0].texte === "Continue là où tu t'es arrêté." && msgs[0].plafond_usd === 1.234, JSON.stringify(msgs));
  ok("6.3 puis la carte est marquée acceptée", faits[0].decision === "acceptee");
  w.c.demonter();
}
{ // la carte « continuer » d'un plafond atteint AVANT toute écriture n'est pas dans le fil : elle reste affichée
  const transitoire = { ...CONTINUER, arguments: { ...CONTINUER.arguments, texte: "Mon texte non parti" } };
  const msgs = [];
  const routes = avec(() => conv([]), {
    "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 0.01, in_tok: 1, out_tok: 1, modele: "m" }),
    "POST /api/agent/campagnes/c1/message": async (c) => { msgs.push(c); return msgs.length === 1 ? flux([{ type: "carte", carte: transitoire }, { type: "fin", motif: "plafond", cout_usd: 0 }]) : flux([{ type: "fin", motif: "reponse", cout_usd: 0 }]); }
  });
  const w = await monterAvec(routes);
  saisir(w.racine, "Mon texte non parti");
  await attendre(() => /≤ 0,01 \$/.test(texte(marque(w.racine, "devis"))));
  bEnvoyer(w.racine).click();
  await attendre(() => parTexte(w.racine, /Continuer/).length);
  await tick();
  const [b] = parTexte(w.racine, /Continuer/);
  ok("6.4 la carte non écrite reste à l'écran après la relecture", !!b);
  b.click();
  await attendre(() => msgs.length === 2);
  ok("6.5 elle renvoie le texte d'origine, au devis de la carte", msgs[1].texte === "Mon texte non parti" && msgs[1].plafond_usd === 1.234, JSON.stringify(msgs[1]));
  ok("6.6 elle n'appelle pas /carte (aucun rang n'existe)", !w.appels.some((a) => a.url.includes("/carte/")));
  w.c.demonter();
}
{
  const w = await monterAvec(avec(() => conv([msg("agent", [BROUILLONS])])));
  ok("6.7 les brouillons : « 2 brouillon(s) au Planificateur » (compté sur les données)", /2 brouillon\(s\) au Planificateur/.test(texte(w.racine)));
  const lien = parTexte(w.racine, /Planificateur/).find((x) => x.tagName === "A");
  const e = lien.click();
  ok("6.8 le lien mène au Planificateur par l'évènement de navigation existant", w.events.some((x) => x.type === "deepotus:navigate" && x.detail.view === "scheduler") && e.empeche === true, JSON.stringify(w.events));
  ok("6.9 …et annonce les brouillons à l'écran qui les montre", w.events.some((x) => x.type === "dz-campagnes-brouillons" && x.detail.ids.length === 2));
  ok("6.10 aucun appel réseau pour ouvrir le calendrier", !w.appels.some((a) => a.methode === "POST"));
  w.c.demonter();
}

// ===== 7. erreurs HTTP et du flux ========================================================================================================
{
  const cas = [[503, { detail: "Aucune clé" }, /Aucune clé Anthropic/], [409, { detail: "occupée" }, /déjà en cours/], [402, { detail: "Plafond mensuel atteint." }, /plafond de dépense a refusé.*Plafond mensuel atteint\./], [500, { detail: "boum" }, /boum/]];
  for (const [statut, corps, motif] of cas) {
    const routes = avec(() => conv([]), {
      "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 1, in_tok: 1, out_tok: 1, modele: "m" }),
      "POST /api/agent/campagnes/c1/message": async () => reponse(statut, corps)
    });
    const w = await monterAvec(routes);
    saisir(w.racine, "Bonjour");
    await attendre(() => /≤/.test(texte(marque(w.racine, "devis"))));
    bEnvoyer(w.racine).click();
    await attendre(() => marque(w.racine, "statut").textContent.length);
    await tick();
    ok("7." + statut + " message clair", motif.test(texte(marque(w.racine, "statut"))), texte(marque(w.racine, "statut")));
    ok("7." + statut + " champ et bouton JAMAIS grisés", !("disabled" in marque(w.racine, "champ").attrs) && !("disabled" in bEnvoyer(w.racine).attrs) && !bEnvoyer(w.racine).attrs["aria-busy"]);
    ok("7." + statut + " le texte revient dans le champ (rien n'est parti)", marque(w.racine, "champ").value === "Bonjour");
    w.c.demonter();
  }
}
{ // un évènement `erreur` du flux
  const routes = avec(() => conv([]), {
    "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 1, in_tok: 1, out_tok: 1, modele: "m" }),
    "POST /api/agent/campagnes/c1/message": async () => flux([{ type: "texte", texte: "Début" }, { type: "erreur", code: "moteur", message: "délai dépassé" }])
  });
  const w = await monterAvec(routes);
  saisir(w.racine, "Bonjour");
  await attendre(() => /≤/.test(texte(marque(w.racine, "devis"))));
  bEnvoyer(w.racine).click();
  await attendre(() => /délai dépassé/.test(texte(marque(w.racine, "statut"))));
  await tick();
  ok("7.5 l'erreur du flux est affichée", /L'agent n'a pas pu répondre : délai dépassé/.test(texte(marque(w.racine, "statut"))), texte(marque(w.racine, "statut")));
  w.c.demonter();
}

// ===== 8. anglais, démontage ===========================================================================================================
{
  const w = await monterAvec(avec(() => conv([msg("agent", [PORTE, DEVIS_VIDEO])], { cout_usd: 1.5 })), {}, "en");
  ok("8.1 EN : « Total cost: $1.50 »", /Total cost: \$1\.50/.test(texte(marque(w.racine, "cout"))), texte(marque(w.racine, "cout")));
  ok("8.2 EN : libellés traduits", /Gate 1: approve/.test(texte(w.racine)) && /video quote: \$0\.80/.test(texte(w.racine)) && parTexte(w.racine, /Generate \(\$0\.80\)/).length === 1, texte(w.racine));
  ok("8.3 EN : le libellé français du serveur n'apparaît pas", !/LIBELLE SERVEUR/.test(texte(w.racine)));
  w.c.demonter();
}
{
  const w = await monterAvec(avec(() => conv([])));
  const hote = w.hote;
  ok("9.1 monté : la racine est dans l'hôte", hote.children.length === 1);
  saisir(w.racine, "Texte"); // une minuterie de devis est armée
  w.c.demonter();
  const avant = w.appels.length;
  await new Promise((r) => setTimeout(r, 600));
  ok("9.2 démonté : la racine est retirée", hote.children.length === 0);
  ok("9.3 démonté : la minuterie du devis est coupée (aucun appel)", w.appels.length === avant);
  ok("9.4 un second montage ne duplique pas le style", w.doc.head.children.length === 1);
}

// ===== 10. correctifs de relecture =====================================================================================================
{ // IMPORTANT 1 : rendu payé, /carte en 500 : un nouveau clic ne repaie JAMAIS
  let cartes = 0;
  const routes = avec(() => conv([msg("agent", [DEVIS_VIDEO])]), {
    "POST /api/generate": async () => reponse(200, { job_id: "J-7", status: "queued", message: "ok" }),
    "POST /api/agent/campagnes/c1/carte/0": async () => (++cartes === 1 ? reponse(500, { detail: "disque plein" }) : reponse(200, conv([msg("agent", [DEVIS_VIDEO])])))
  });
  const w = await monterAvec(routes);
  parTexte(w.racine, /Générer/)[0].click();
  await attendre(() => cartes === 1);
  await tick(); await tick();
  ok("10.1 /carte en échec : l'erreur est dite", /disque plein/.test(texte(marque(w.racine, "statut"))), texte(marque(w.racine, "statut")));
  ok("10.2 …et la conversation est relue", w.appels.filter((a) => a.methode === "GET" && a.url === "/api/agent/campagnes/c1").length >= 2);
  const [b] = parTexte(w.racine, /Rendu payé/);
  ok("10.3 le bouton devient « enregistrer la décision » (plus « Générer »)", !!b && !parTexte(w.racine, /Générer/).length, boutons(w.racine).map((x) => x.textContent).join("|"));
  b.click();
  await attendre(() => cartes === 2);
  ok("10.4 la route payante n'a été appelée QU'UNE fois", w.appels.filter((a) => a.url === "/api/generate").length === 1);
  ok("10.5 le second /carte porte le même job_id", w.appels.filter((a) => a.url.endsWith("/carte/0"))[1].corps.job_id === "J-7");
  w.c.demonter();
}
{ // M1 : le réseau tombe avant le départ -> le texte revient dans le champ
  const routes = avec(() => conv([]), { "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 1, in_tok: 1, out_tok: 1, modele: "m" }) });
  const w = await monterAvec(routes);
  saisir(w.racine, "Texte perdu ?");
  await attendre(() => /≤/.test(texte(marque(w.racine, "devis"))));
  w.win.coupe = true;
  bEnvoyer(w.racine).click();
  await attendre(() => /réseau coupé/.test(texte(marque(w.racine, "statut"))));
  await tick();
  ok("10.6 M1 : fetch lève -> le texte revient dans le champ", marque(w.racine, "champ").value === "Texte perdu ?");
  w.win.coupe = false;
  w.c.demonter();
}
{ // M2 : un 409 « illisible » montre son détail ; l'occupation reste « occupée »
  for (const [detail, motif] of [["Conversation illisible : son fichier est mis de côté, rien n'a été écrit.", /illisible : son fichier/], ["Conversation occupée : une réponse est déjà en cours.", /déjà en cours pour cette conversation/]]) {
    const routes = avec(() => conv([]), {
      "POST /api/agent/campagnes/c1/devis": async () => reponse(200, { plafond_usd: 1, in_tok: 1, out_tok: 1, modele: "m" }),
      "POST /api/agent/campagnes/c1/message": async () => reponse(409, { detail })
    });
    const w = await monterAvec(routes);
    saisir(w.racine, "x");
    await attendre(() => /≤/.test(texte(marque(w.racine, "devis"))));
    bEnvoyer(w.racine).click();
    await attendre(() => marque(w.racine, "statut").textContent.length);
    ok("10.7 M2 : 409 « " + detail.slice(0, 22) + "… »", motif.test(texte(marque(w.racine, "statut"))), texte(marque(w.racine, "statut")));
    w.c.demonter();
  }
}
{ // M3 : démonter coupe le flux en cours et plus aucun POST ne part
  let signal = null, lib = null;
  const routes = avec(() => conv([msg("agent", [CONTINUER])]), {
    "POST /api/agent/campagnes/c1/message": async () => { lib = null; return reponse(200, undefined, { body: { getReader: () => ({ read: () => new Promise((_, rej) => { signal.addEventListener("abort", () => rej(new Error("abort"))); }) }) } }); },
    "POST /api/agent/campagnes/c1/carte/0": async () => reponse(200, conv([]))
  });
  const w = await monterAvec(routes);
  const brut = w.win.fetch; w.win.fetch = (u, i) => { if (String(u).endsWith("/message")) signal = i.signal; return brut(u, i); };
  // l'écouteur du faux signal : AbortSignal natif
  parTexte(w.racine, /Continuer/)[0].click();
  await attendre(() => signal);
  ok("10.8 M3 : le /message porte un signal d'annulation", !!signal && signal.aborted === false);
  w.c.demonter();
  await new Promise((r) => setTimeout(r, 60));
  ok("10.9 M3 : démonter l'annule", signal.aborted === true);
  ok("10.10 M3 : aucun POST /carte après le démontage", !w.appels.some((a) => a.url.endsWith("/carte/0")), JSON.stringify(w.appels.map((a) => a.url)));
}
{ // M4/M6 : plus de ponctuation collée hors dzT, plus de chaîne nue
  const w = await monterAvec(avec(() => conv([])), {}, "en");
  ok("10.11 M4 : l'en-tête EN est « Campaign space: Marque A » (ponctuation du gabarit)", /Campaign space: Marque A/.test(texte(marque(w.racine, "espace"))), texte(marque(w.racine, "espace")));
  w.c.demonter();
  const src = SRC.replace(/\/\*[\s\S]*?\*\//g, "");
  ok("10.12 M4/M6 : aucun « : » / « — » / « HTTP » / « ? » collé hors dzT", !/\)\s*\+\s*"[ :—]|"[ :—]+"\s*\+|"HTTP |Error\("\?"\)/.test(src));
}

if (echecs.length) {
  console.error(echecs.length + " ÉCHEC(S) sur " + n + " vérifications :\n - " + echecs.join("\n - "));
  process.exit(1);
}
console.log("OK : " + n + " vérifications");
process.exit(0);
