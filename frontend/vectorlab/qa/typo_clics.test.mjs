// typo_clics.test.mjs — l'éditeur de texte en place (mod-typo, VL.editerTexte : textarea.tx-editeur posé DANS #stage)
// garde ses clics. Le gestionnaire de l'outil Sélection (mod-tools) écoute #stage en BULLE : un clic dans le champ,
// sans garde, y arrivait, ne touchait aucun objet, vidait la sélection — et surSelection FERMAIT l'éditeur au lieu de
// laisser le curseur se placer (vu à la preuve 8799). initTypo tourne ici pour de vrai sur un mini-DOM à propagation
// réelle (capture de la racine vers la cible, puis bulle). L'outil témoin rejoue le geste de mod-tools : clic hors
// objet → setSelection([]). La MUTATION (la même source sans la boucle de garde, importée en mémoire) doit rougir le
// banc : elle est rejouée à chaque série.
import { readFileSync } from "node:fs";
import { initTypo } from "../js/mod-typo.js";

const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};

class Noeud {
  constructor(parent, tag = "div") { this.parent = parent; this.tag = tag; this.ec = []; this.style = {}; this.dataset = {}; this.value = ""; this.retire = false; }
  appendChild(e) { e.parent = this; return e; }
  remove() { this.retire = true; this.parent = null; }
  focus() {} select() {}
  addEventListener(type, fn, o) { this.ec.push({ type, fn, capture: o === true || !!(o && o.capture) }); }
  removeEventListener(type, fn) { this.ec = this.ec.filter((e) => !(e.type === type && e.fn === fn)); }
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

// monte l'éditeur par le VRAI initTypo + VL.editerTexte, puis l'outil Sélection témoin sur #stage
function scenario(init) {
  const stage = new Noeud(null);
  const avant = { document: globalThis.document, window: globalThis.window };
  let ta = null;
  globalThis.document = { createElement: (tag) => { const e = new Noeud(null, tag); if (tag === "textarea") ta = e; return e; },
    head: new Noeud(null) };
  globalThis.window = {};
  const texte = { id: "t1", type: "texte", x: 10, y: 60, contenu: "Bonjour", style: { corps: 48 } };
  const doc = { calques: [{ id: "c1", objets: [texte] }] };
  const executes = [];
  const VL = {
    etat: { doc, selection: ["t1"], zoom: 1, outil: "select", styleCourant: {}, calqueActif: "c1" },
    $: (s) => (s === "#stage" ? stage : null),
    api: { get: () => Promise.reject(new Error("hors ligne")) },
    objetDe: (id) => (id === "t1" ? { objet: texte } : null),
    ecranPt: (x, y) => [x, y],
    executer: (fn, ...a) => { executes.push(fn.name || "anonyme"); if (typeof fn === "function" && !fn.name) fn(doc); return null; },
    setSelection: (ids) => { VL.etat.selection = ids; VL.surSelection(); },
    setOutil: () => {}, toast: () => {},
    surRendu: () => {}, surSelection: () => {}, surOutil: () => {},
  };
  init(VL);
  VL.editerTexte("t1");
  const vus = [];
  // l'outil Sélection de mod-tools : en BULLE sur #stage ; un clic qui ne touche aucun objet vide la sélection
  stage.addEventListener("pointerdown", (ev) => { vus.push("pointerdown:" + (ev.target === ta ? "champ" : "scene")); VL.setSelection([]); });
  for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) stage.addEventListener(t, () => vus.push(t));
  const res = { ta, vus, executes };
  if (!ta) { globalThis.document = avant.document; globalThis.window = avant.window; return res; }
  res.posee = ta.parent === stage && ta.className === "tx-editeur";
  // les autres gestes d'abord (un champ déjà retiré ne propagerait plus rien), puis le clic
  for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) ta.dispatch(t);
  res.autres = [...vus];
  res.ouvertApresGestes = !ta.retire;
  res.natif = ta.dispatch("pointerdown", { clientX: 30, clientY: 20 });
  res.geste = vus.slice(res.autres.length);
  res.ouvertApresClic = !ta.retire && VL.etat.selection.includes("t1");
  // la saisie continue, puis Entrée valide toujours (keydown garde déjà son propre stopPropagation)
  ta.value = "Bonjour monde";
  const k = ta.dispatch("keydown", { key: "Enter", shiftKey: false });
  res.entree = { arrete: k.arrete, empeche: k.empeche, retire: ta.retire, contenu: texte.contenu };
  // un nouvel éditeur : un clic sur la scène hors champ atteint toujours l'outil et le referme
  VL.etat.selection = ["t1"];
  const ta2 = VL.editerTexte("t1");
  const avantScene = vus.length;
  const hors = stage.dispatch("pointerdown");
  res.hors = { arrete: hors.arrete, atteint: vus.slice(avantScene).includes("pointerdown:scene"), ferme: !!(ta2 && ta2.retire) };
  globalThis.document = avant.document; globalThis.window = avant.window;
  return res;
}

/* ── [clics] le vrai éditeur : un clic dedans place le curseur, il ne ferme rien ── */
{
  const r = scenario(initTypo);
  ok("[clics] editerTexte pose textarea.tx-editeur dans #stage", r.posee);
  ok("[clics] un pointerdown dans le champ n'atteint pas l'outil témoin de #stage", r.geste && r.geste.length === 0, (r.geste || []).join(","));
  ok("[clics] l'éditeur reste ouvert et le texte sélectionné après le clic", r.ouvertApresClic);
  ok("[clics] ni preventDefault : le champ garde son geste natif (curseur, sélection du texte)", r.natif && !r.natif.empeche);
  ok("[clics] mousedown, double-clic, molette et menu contextuel restent au champ", r.autres && r.autres.length === 0, (r.autres || []).join(","));
  ok("[clics] l'éditeur reste ouvert après ces gestes", r.ouvertApresGestes);
  ok("[clics] Entrée valide toujours : champ retiré, contenu écrit", r.entree && r.entree.retire && r.entree.contenu === "Bonjour monde", JSON.stringify(r.entree));
  ok("[clics] un pointerdown sur la scène hors champ atteint toujours l'outil et referme l'éditeur",
     r.hors && r.hors.atteint && !r.hors.arrete && r.hors.ferme, JSON.stringify(r.hors));
}

/* ── [mutation] la même source SANS la boucle de garde : le banc doit la voir ── */
{
  const src = readFileSync(new URL("../js/mod-typo.js", import.meta.url), "utf8");
  const boucle = /\n[ \t]*for \(const t of \["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel"\]\) \{\r?\n[^\n]*ta\.addEventListener\(t, \(ev\) => ev\.stopPropagation\(\)[^\n]*\r?\n[ \t]*\}/;
  ok("[mutation] la boucle de garde est bien dans la source", boucle.test(src));
  const mutant = src.replace(boucle, "")
    .replace(/from "\.\/([\w-]+\.js)"/g, (_, f) => `from "${new URL("../js/" + f, import.meta.url).href}"`);
  ok("[mutation] la source mutée diffère", mutant !== src && !boucle.test(mutant));
  const mod = await import("data:text/javascript;base64," + Buffer.from(mutant, "utf8").toString("base64"));
  const r = scenario(mod.initTypo);
  ok("[mutation] sans garde, le pointerdown du champ atteint #stage (le défaut vu à la preuve)",
     r.geste && r.geste.includes("pointerdown:champ"), (r.geste || []).join(","));
  ok("[mutation] sans garde, l'éditeur se FERME au clic", r.ouvertApresClic === false);
  ok("[mutation] sans garde, mousedown/molette/double-clic/menu remontent aussi", r.autres && r.autres.length === 4, (r.autres || []).join(","));
}

if (echecs.length) {
  console.error("ECHECS typo_clics :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA typo_clics : PASS (${n} controles)`);
