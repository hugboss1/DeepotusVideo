// ia_clics.test.mjs — le dialogue IA du canevas (mod-ia, posé DANS #stage) garde ses clics. Le gestionnaire de
// l'outil Sélection (mod-tools) écoute #stage en BULLE et pose setPointerCapture(#stage) dès le clic gauche : sans
// garde, le click d'un contrôle du dialogue part sur #stage (la croix ne ferme pas, « Générer » ne part pas — vu à
// la preuve 8799 ; el.click() par script, lui, marchait). initIA tourne ici pour de vrai sur un mini-DOM à
// propagation réelle (capture de la racine vers la cible, puis bulle), comme le navigateur. La MUTATION (la même
// source sans la boucle de garde, importée en mémoire) doit rougir le banc : elle est rejouée à chaque série.
import { readFileSync } from "node:fs";
import { initIA } from "../js/mod-ia.js";

const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};

class Noeud {
  constructor(parent, attrs = {}) { this.parent = parent; this.attrs = attrs; this.ec = []; this.style = {}; this.dataset = {}; }
  appendChild(e) { e.parent = this; return e; }
  addEventListener(type, fn, o) { this.ec.push({ type, fn, capture: o === true || !!(o && o.capture) }); }
  removeEventListener(type, fn) { this.ec = this.ec.filter((e) => !(e.type === type && e.fn === fn)); }
  closest(sel) {
    for (let x = this; x; x = x.parent) if (sel === "[data-poigne]" && x.attrs.poigne) return x;
    return null;
  }
  getBoundingClientRect() { return this.attrs.rect || { left: 0, top: 0, width: 0, height: 0 }; }
  dispatch(type, extra = {}) {
    const ev = { type, target: this, button: 0, arrete: false, empeche: false, ...extra,
      stopPropagation() { this.arrete = true; }, preventDefault() { this.empeche = true; } };
    const chemin = [];
    for (let x = this; x; x = x.parent) chemin.unshift(x);
    for (const x of chemin.slice(0, -1)) { for (const e of x.ec.filter((y) => y.type === type && y.capture)) e.fn(ev); if (ev.arrete) return ev; }
    for (const x of [...chemin].reverse()) {
      for (const e of x.ec.filter((y) => y.type === type && (x === this || !y.capture))) e.fn(ev);
      if (ev.arrete) return ev;
    }
    return ev;
  }
}

// monte le dialogue par le VRAI initIA (hote() le crée et le pose dans #stage), puis l'outil Sélection témoin
function monter(init) {
  const stage = new Noeud(null, { rect: { left: 0, top: 0, width: 1000, height: 800 } });
  const win = new Noeud(null);
  const avant = { document: globalThis.document, window: globalThis.window };
  globalThis.document = { createElement: () => new Noeud(null, { rect: { left: 700, top: 20, width: 280, height: 400 } }) };
  globalThis.window = win;
  let el = null;
  // hote() pose le dialogue par stage.appendChild : on le retient au passage
  stage.appendChild = (e) => { e.parent = stage; el = e; return e; };
  const VL = { etat: { outil: "ia", doc: {} }, surOutil: () => {}, setOutil: () => {}, toast: () => {},
    $: (s) => (s === "#stage" ? stage : s === "#iaDialogue" ? el : null) };
  init(VL);
  const remettre = () => { globalThis.document = avant.document; globalThis.window = avant.window; };
  return { stage, win, el, remettre };
}

function scenario(init) {
  const m = monter(init);
  const el = m.el;
  const vus = [];
  if (!el) { m.remettre(); return { el, vus }; }
  const tete = new Noeud(el, { poigne: true }), croix = new Noeud(el), go = new Noeud(el), texte = new Noeud(el);
  croix.dataset.act = "fermer"; go.id = "iaGo"; texte.id = "iaTexte";
  // l'outil Sélection de mod-tools : en BULLE sur #stage, setPointerCapture + geste
  m.stage.addEventListener("pointerdown", (ev) => vus.push("pointerdown:" + (ev.target === croix ? "croix" : ev.target === go ? "go" : ev.target === texte ? "texte" : ev.target === m.stage ? "scene" : "autre")));
  for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) m.stage.addEventListener(t, () => vus.push(t));
  const e1 = croix.dispatch("pointerdown", { clientX: 960, clientY: 30 });
  const e2 = go.dispatch("pointerdown", { clientX: 760, clientY: 300 });
  const e3 = texte.dispatch("pointerdown", { clientX: 760, clientY: 250 });
  const geste = [...vus];
  for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) texte.dispatch(t);
  const autres = vus.slice(geste.length);
  // t190-bis : le CLAVIER — une lettre tapée sur la liste des moteurs ne remonte plus au raccourci global (core.js)
  const vusK = [];
  m.stage.addEventListener("keydown", (ev) => vusK.push(ev.key));
  const moteur = new Noeud(el); moteur.id = "iaMoteur";
  const k1 = moteur.dispatch("keydown", { key: "p" });
  const hors = m.stage.dispatch("pointerdown");
  const g = tete.dispatch("pointerdown", { clientX: 710, clientY: 30 });
  m.win.dispatch("pointermove", { clientX: 410, clientY: 130 });
  const glisse = { ...el.style };
  m.win.dispatch("pointerup");
  m.win.dispatch("pointermove", { clientX: 10, clientY: 10 });
  const apres = el.style.left;
  m.remettre();
  return { el, vus, geste, autres, hors, g, glisse, apres, natifs: [e1, e2, e3], vusK, k1 };
}

/* ── [clics] le vrai dialogue : ses gestes n'atteignent pas l'outil de la scène ── */
{
  const r = scenario(initIA);
  ok("[clics] initIA pose le dialogue dans #stage (hote)", r.el && r.el.id === "iaDialogue" && r.el.className === "ia-dlg");
  ok("[clics] un pointerdown sur la croix, « Générer » ou le champ n'atteint pas l'écouteur témoin de #stage",
     r.geste && r.geste.length === 0, (r.geste || []).join(","));
  ok("[clics] ni preventDefault : les contrôles gardent leur geste natif (focus, sélection du texte)",
     r.natifs && r.natifs.every((e) => !e.empeche));
  ok("[clics] la molette, le double-clic, le menu contextuel et mousedown restent au dialogue",
     r.autres && r.autres.length === 0, (r.autres || []).join(","));
  ok("[clics] un pointerdown sur la scène hors dialogue atteint toujours l'outil",
     r.vus.includes("pointerdown:scene") && !r.hors.arrete, r.vus.join(","));
  ok("[clics] la poignée glisse toujours (preventDefault du glisser, dialogue déplacé)",
     r.g && r.g.empeche && r.glisse.left === "400px" && r.glisse.top === "120px" && r.glisse.right === "auto", JSON.stringify(r.glisse));
  ok("[clics] relâché : le dialogue ne suit plus", r.apres === "400px", r.apres);
  ok("[clavier] une lettre sur la liste des moteurs n'atteint pas le raccourci global (garderClics partagé)",
     r.vusK && r.vusK.length === 0 && !r.k1.empeche, (r.vusK || []).join(","));
  ok("[clavier] le dialogue est marqué panneau flottant (VL.dansPanneau le reconnaît)", r.el && r.el.dataset.vlFlottant === "1");
}

/* ── [mutation] la même source SANS la garde (garderClics) : le banc doit la voir ── */
{
  const src = readFileSync(new URL("../js/mod-ia.js", import.meta.url), "utf8");
  // t190-bis : la boucle locale est devenue le garderClics PARTAGÉ (mod-flottant) — la mutation retire son appel
  const boucle = /\n[ \t]*garderClics\(el\);/;
  ok("[mutation] la garde (garderClics(el)) est bien dans la source", boucle.test(src));
  const mutant = src.replace(boucle, "")
    .replace(/from "\.\/([\w-]+\.js)"/g, (_, f) => `from "${new URL("../js/" + f, import.meta.url).href}"`);
  ok("[mutation] la source mutée diffère", mutant !== src && !boucle.test(mutant));
  const mod = await import("data:text/javascript;base64," + Buffer.from(mutant, "utf8").toString("base64"));
  const r = scenario(mod.initIA);
  ok("[mutation] sans garde, le pointerdown de la croix et de « Générer » atteint #stage (le défaut vu à la preuve)",
     r.geste && r.geste.includes("pointerdown:croix") && r.geste.includes("pointerdown:go"), (r.geste || []).join(","));
  ok("[mutation] sans garde, mousedown/molette/double-clic/menu remontent aussi", r.autres && r.autres.length === 4, (r.autres || []).join(","));
  ok("[mutation] sans garde, la poignée glisse encore (le garde n'y est pour rien)", r.glisse.left === "400px");
  ok("[mutation] sans garde, la lettre tapée remonte au raccourci global", r.vusK && r.vusK.includes("p"), (r.vusK || []).join(","));
}

if (echecs.length) {
  console.error("ECHECS ia_clics :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA ia_clics : PASS (${n} controles)`);
