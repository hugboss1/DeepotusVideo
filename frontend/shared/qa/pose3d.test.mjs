// t376 (29/10/2026, lot « Game Assets : finitions ») — dz-pose3d.js : le choix Aucune / T-pose / A-pose, joué avec un
// fetch et un DOM simulés. Séries : état (attente de 250 ms, une seule requête, cache, dernier état du moteur pendant
// le chargement), textes FR puis EN (raison, avertissement, précision Rodin / vues), corps envoyé (pose coupée quand
// le choix est inactif, tpose retiré), classement vision (devis, confirmation avec le montant, refus = rien
// d'envoyé, accord = POST {confirme_cout, max_usd}, état mis en cache ; indisponible = information sans POST),
// 3D Studio (liste grisée et mise à « libre », raison posée après, bouton de vérification), aucun innerHTML.
// Lancer : node frontend/shared/qa/pose3d.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-pose3d.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const dort = (ms) => new Promise((r) => setTimeout(r, ms));

class Noeud {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.attrs = {}; this.style = {}; this.ec = {};
                     this.parent = null; this.textContent = ""; this.disabled = false; this.value = "a-pose"; this.title = ""; }
  get firstChild() { return this.children[0] || null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  removeChild(c) { this.children.splice(this.children.indexOf(c), 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener(t, f) { this.ec[t] = f; }
  insertAdjacentElement(pos, el) { this.apres = el; el.parent = this.parent; return el; }
  set innerHTML(_v) { INNER.push(this.tagName); }
}
const INNER = [];

function monde(lang, reponses) {
  const appels = [];
  const dialogues = [];
  const w = {
    navigator: { language: lang }, localStorage: { getItem: () => lang, setItem() {} },
    document: { documentElement: { lang }, createElement: (t) => new Noeud(t), addEventListener() {} },
    fetch: async (url, o) => {
      appels.push({ url, o });
      const r = reponses(url, o);
      return { ok: r.ok !== false, status: r.status || 200, json: async () => r.corps };
    },
    __dzDialogue: {
      confirmer: async (m, o) => { dialogues.push({ genre: "confirmer", m, o }); return w.__oui; },
      informer: async (m, o) => { dialogues.push({ genre: "informer", m, o }); },
    },
    __oui: true, setTimeout, clearTimeout, console,
  };
  w.window = w;
  w.globalThis = w;
  vm.createContext(w);
  vm.runInContext(DICO, w);
  w.dzT = (k, v) => {
    const e = w.DZ_I18N[k]; if (!e) return k;
    return String(e[lang]).replace(/\{(\w+)\}/g, (m, x) => (v && v[x] != null ? String(v[x]) : m));
  };
  vm.runInContext(SRC, w);
  return { w, P: w.__dzPose3d, appels, dialogues };
}

const ETAT = (o) => Object.assign({ actif: true, sujet: "personnage", texte: "personnage", vision: null, mode: "moteur",
                                     raison: "", avertissement: "", vision_proposee: false }, o);

// ── état ─────────────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { P, appels } = monde("fr", (url) => ({ corps: url.includes("subject=a%20sword") ? ETAT({ actif: false, raison: "objet", sujet: "objet" }) : ETAT({}) }));
  let rappels = 0;
  const q = { engine: "rodin", multiview: false, subject: "a knight", image: "k.png" };
  ok("1.1 rien de connu au premier appel", P.etat(q, () => rappels++) === null);
  P.etat(q, () => rappels++);
  ok("1.2 aucune requête avant 250 ms de calme", appels.length === 0);
  await dort(320);
  ok("1.3 une seule requête, GET /api/assets3d/pose avec moteur, vues, sujet et image",
     appels.length === 1 && appels[0].url === "/api/assets3d/pose?engine=rodin&multiview=false&subject=a%20knight&image_filename=k.png"
     && !appels[0].o, appels.map((a) => a.url).join(" ; "));
  ok("1.4 le rappel est appelé à la réponse", rappels === 1, rappels);
  ok("1.5 l'état est ensuite servi par le cache, sans requête", P.etat(q, () => {}).actif === true && appels.length === 1);
  const q2 = { engine: "rodin", multiview: false, subject: "a sword", image: "" };
  ok("1.6 pendant le chargement d'un autre sujet : le dernier état connu du moteur", P.etat(q2, () => {}).actif === true);
  await dort(320);
  ok("1.7 puis le sien (objet, grisé)", P.etat(q2, () => {}).raison === "objet" && appels.length === 2);
  ok("1.8 sujet rogné dans la clé (même requête)", P._cle({ engine: "x", subject: " a " }) === P._cle({ engine: "x", subject: "a" }));
}

// ── textes ───────────────────────────────────────────────────────────────────────────────────────────────────────
for (const [lang, attendu] of [["fr", { moteur: "trellis ne sait pas poser le sujet", objet: "n'est pas un personnage",
                                         vues: "Active les vues multiples", doute: "Sujet incertain", rodin: "Rodin demande" }],
                                ["en", { moteur: "trellis cannot pose the subject", objet: "is not a character",
                                         vues: "Turn on multi-view", doute: "Uncertain subject", rodin: "Rodin asks" }]]) {
  const { P } = monde(lang, () => ({ corps: {} }));
  const x = (e, m) => P.textes(e, m);
  ok(`2.1 ${lang} raison moteur nomme le moteur`, x(ETAT({ actif: false, raison: "moteur", mode: null }), "trellis").raison.includes(attendu.moteur), x(ETAT({ actif: false, raison: "moteur" }), "trellis").raison);
  ok(`2.2 ${lang} raison objet`, x(ETAT({ actif: false, raison: "objet" }), "rodin").raison.includes(attendu.objet));
  ok(`2.3 ${lang} raison vues`, x(ETAT({ actif: false, raison: "vues", mode: "vues" }), "tripo").raison.includes(attendu.vues));
  ok(`2.4 ${lang} avertissement doute`, x(ETAT({ avertissement: "doute", sujet: "doute" }), "rodin").avertissement.includes(attendu.doute));
  ok(`2.5 ${lang} précision Rodin (T/A sans dire laquelle)`, x(ETAT({}), "rodin").precision.includes(attendu.rodin));
  ok(`2.6 ${lang} rien à dire pour un état nul`, JSON.stringify(x(null, "rodin")) === JSON.stringify({ raison: "", avertissement: "", precision: "" }));
  ok(`2.7 ${lang} aucune clé brute affichée`, !Object.values(x(ETAT({ actif: false, raison: "vues", mode: "vues" }), "tripo")).some((s) => s.startsWith("pose3d.")));
}

// ── corps envoyé ────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { P } = monde("fr", (url) => ({ corps: url.includes("barrel") ? ETAT({ actif: false, raison: "objet" }) : ETAT({}) }));
  const p = { engine: "rodin", multiview: false, subject: "a knight", image_filename: "k.png", pose: "a-pose", tpose: true };
  ok("3.1 état inconnu : la pose ne part pas", P.corps(p).pose === "" && !("tpose" in P.corps(p)));
  P.etat({ engine: "rodin", multiview: false, subject: "a knight", image: "k.png" }, () => {});
  await dort(320);
  ok("3.2 choix actif : la pose part telle quelle", P.corps(p).pose === "a-pose");
  ok("3.3 l'ancien tpose n'est jamais envoyé, le reste du corps est intact",
     !("tpose" in P.corps(p)) && P.corps(p).engine === "rodin" && P.corps(p).image_filename === "k.png" && p.tpose === true);
  const p2 = { ...p, subject: "a barrel" };
  P.etat({ engine: "rodin", multiview: false, subject: "a barrel", image: "k.png" }, () => {});
  await dort(320);
  ok("3.4 choix inactif (objet) : pose vidée", P.corps(p2).pose === "");
}

// ── classement vision ───────────────────────────────────────────────────────────────────────────────────────────
{
  const { w, P, appels, dialogues } = monde("fr", (url, o) => {
    if (url === "/api/assets3d/pose/devis") return { corps: { usd: 0.0123, disponible: true, raison: "" } };
    if (url === "/api/assets3d/pose/classer") return { corps: { classe: "personnage", deja: false, usd: 0.0123, etat: ETAT({ vision: "personnage" }) } };
    return { corps: ETAT({ sujet: "doute", avertissement: "doute", vision_proposee: true }) };
  });
  const q = { engine: "rodin", multiview: false, subject: "", image: "k.png" };
  w.__oui = false;
  await P.classer(q, () => {});
  ok("4.1 confirmation demandée avec le montant, en français", dialogues.length === 1 && dialogues[0].genre === "confirmer"
     && dialogues[0].m.includes("0.0123") && dialogues[0].m.includes("Claude"), dialogues[0] && dialogues[0].m);
  ok("4.2 refus : seul le devis est demandé, aucun POST", appels.length === 1 && appels[0].url.endsWith("/devis"));
  w.__oui = true;
  let rappels = 0;
  const e = await P.classer(q, () => rappels++);
  const post = appels.find((a) => a.url === "/api/assets3d/pose/classer");
  const corps = post && JSON.parse(post.o.body);
  ok("4.3 accord : POST /classer {image, confirme_cout, max_usd = devis}", post && post.o.method === "POST"
     && corps.image_filename === "k.png" && corps.confirme_cout === true && corps.max_usd === 0.0123, post && post.o.body);
  ok("4.4 l'état rendu est mis en cache et le rappel appelé", e.vision === "personnage" && rappels === 1
     && P.etat(q, () => {}).vision === "personnage");
}
{
  const { P, appels, dialogues } = monde("en", (url) => (url.endsWith("/devis") ? { corps: { usd: 0, disponible: false, raison: "cle" } } : { corps: {} }));
  await P.classer({ engine: "rodin", image: "k.png" }, () => {});
  ok("4.5 indisponible : information traduite, aucun POST", appels.length === 1 && dialogues.length === 1
     && dialogues[0].genre === "informer" && dialogues[0].m.includes("Anthropic engine is not configured"), dialogues[0] && dialogues[0].m);
}
{
  const { w, P, dialogues } = monde("fr", (url) => (url.endsWith("/devis") ? { corps: { usd: 0.01, disponible: true } }
    : { ok: false, status: 409, corps: { detail: { message: "Le coût a changé : il dépasse le montant accepté.", usd: 0.02 } } }));
  w.__oui = true;
  await P.classer({ engine: "rodin", image: "k.png" }, () => {});
  ok("4.6 refus du serveur : son message est montré", dialogues.length === 2 && dialogues[1].m.startsWith("Le coût a changé"));
}

{
  const { w, P, appels } = monde("fr", (url) => (url.endsWith("/devis") ? { corps: { usd: 0.01, disponible: true } } : { corps: {} }));
  delete w.__dzDialogue;
  w.confirm = () => { throw new Error("boîte native appelée"); };
  const e = await P.classer({ engine: "rodin", image: "k.png" }, () => {});
  ok("4.7 sans le dialogue de l'app : ni boîte native, ni POST", e === null && appels.length === 1, appels.map((a) => a.url).join(" ; "));
}

// ── 3D Studio ───────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { P, appels } = monde("fr", (url) => ({ corps: url.includes("subject=un%20tonneau")
    ? ETAT({ actif: false, raison: "objet", sujet: "objet" })
    : ETAT({ sujet: "doute", avertissement: "doute", vision_proposee: true }) }));
  const sel = new Noeud("select");
  P.monterSelect(sel, { engine: "meshy", multiview: true, subject: "un tonneau", image: "" });
  await dort(320);
  const note = sel.apres;
  ok("5.1 une note posée juste après la liste", note && note.attrs["data-dz-pose3d"] === "" && appels[0].url.includes("engine=meshy"));
  ok("5.2 objet : liste grisée, mise à « libre », raison affichée et en bulle",
     sel.disabled === true && sel.value === "" && note.children[0].textContent.includes("n'est pas un personnage")
     && sel.title.includes("n'est pas un personnage"), JSON.stringify({ d: sel.disabled, v: sel.value }));
  const sel2 = new Noeud("select");
  P.monterSelect(sel2, { engine: "meshy", multiview: true, subject: "", image: "k.png" });
  await dort(320);
  const n2 = sel2.apres;
  ok("5.3 doute : liste active (valeur gardée), avertissement ambre, bouton de vérification",
     sel2.disabled === false && sel2.value === "a-pose" && n2.children[0].style.color === "var(--amber)"
     && n2.children[1].tagName === "BUTTON" && n2.children[1].textContent === "Vérifier l'image (IA)" && typeof n2.children[1].ec.click === "function");
  ok("5.4 bouton à angles vifs (jeton de la charte)", n2.children[1].style.cssText.includes("border-radius:var(--r)"));
  ok("5.4b un état provisoire d'un AUTRE sujet ne touche pas la liste", P.etat({ engine: "meshy", multiview: true, subject: "zz", image: "" }, () => {}, true) === null);
  ok("5.5 liste absente : rien ne casse", (P.monterSelect(null, {}), true));
}
ok("6.1 aucun innerHTML", INNER.length === 0 && !/\.innerHTML\s*=/.test(SRC));
ok("6.2 aucun rayon littéral dans le module", !/border-radius:\s*\d/.test(SRC));

if (echecs.length) { console.log(echecs.map((e) => "  ÉCHEC " + e).join("\n")); }
console.log(`pose3d.test.mjs : ${n - echecs.length}/${n}`);
process.exit(echecs.length ? 1 : 0);
