// panneaux_flottants.test.mjs — t190-bis (I1) : les panneaux flottants posés DANS #stage (dialogue IA #iaDialogue
// de mod-ia, panneau « Image IA sur le calque » #iaCalqueDlg, éditeur de texte en place .tx-editeur) gardent leurs
// gestes QUEL QUE SOIT L'OUTIL. Les outils écoutent #stage EN CAPTURE (Plume, Texte, Nœud, Pipette, Main/Loupe…,
// Pixel, pinceau vectoriel, tranches, Alt+glisser, formes) : ils jouent AVANT le panneau, et sans garde leur
// stopPropagation + preventDefault + setPointerCapture envoyait le click sur #stage — le panneau redevenait inerte
// dès qu'on changeait d'outil. garderClics (en bulle) arrive trop tard : chaque gestionnaire sort par VL.dansPanneau.
//
// Le VRAI code de chaque module tourne ici (init(VL) importé) sur un mini-DOM à propagation réelle (capture de la
// racine vers la cible, puis bulle) ; le setPointerCapture d'un outil redirige le click suivant sur #stage, comme le
// navigateur. Jamais de el.click() qui contournerait la capture. Un geste venu du panneau ne doit RIEN faire lire
// à l'outil (ni l'événement au-delà de sa cible, ni l'état, ni le cœur) ; le même geste sur la scène, outil actif,
// le fait réagir (témoin : la garde ne coupe pas l'outil). Le panoramique et la molette de core.js (script de page,
// non importable) sont exercés sur LEUR texte extrait de core.js. La MUTATION (mod-plumeui sans sa garde, importé
// en mémoire) doit rougir le banc : elle est rejouée à chaque série.
import { readFileSync } from "node:fs";
import { dansPanneau, garderClics, PANNEAUX_FLOTTANTS } from "../js/mod-flottant.js";
import { initPlume } from "../js/mod-plumeui.js";
import { initTexteUI } from "../js/mod-texteui.js";
import { initNoeudUI } from "../js/mod-noeudui.js";
import { initPipetteUI } from "../js/mod-pipetteui.js";
import { initOutils3 } from "../js/mod-outils3ui.js";
import { initPixelUI } from "../js/mod-pixelui.js";
import { initSelectionUI } from "../js/mod-selectionui.js";
import { initApparence2 } from "../js/mod-apparence2.js";
import { initExportPlus } from "../js/mod-exportplus.js";
import { initOutils2 } from "../js/mod-outils2.js";
import { initOutils } from "../js/mod-tools.js";

const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};

/* ── le mini-DOM ── */
let compteur = null;                       // pendant un geste : ce que l'outil a lu ou fait
let courant = null;                        // le nœud dont les écouteurs jouent (ceux du panneau ne comptent pas)
const note = (quoi) => { if (compteur && !(courant && courant.panneau)) compteur.push(quoi); };

class Noeud {
  constructor(parent, { tag = "div", id = "", classes = [], data = {} } = {}) {
    this.parent = parent; this.tagName = tag.toUpperCase(); this.id = id; this.classes = new Set(classes);
    this.dataset = { ...data }; this.ec = []; this.style = {}; this.captures = 0; this.isConnected = true;
  }
  addEventListener(type, fn, o) { this.ec.push({ type, fn, capture: o === true || !!(o && o.capture) }); }
  removeEventListener(type, fn) { this.ec = this.ec.filter((e) => !(e.type === type && e.fn === fn)); }
  setPointerCapture() { this.captures++; note("setPointerCapture"); }
  releasePointerCapture() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: 1000, height: 800, right: 1000, bottom: 800 }; }
  appendChild(e) { e.parent = this; return e; }
  // les sélecteurs simples (tag, .classe, #id, [data-x]) et leurs listes « a, b » ; un descendant (« a b ») : rien
  correspond(sel) {
    return sel.split(",").map((s) => s.trim()).some((s) => {
      if (!s || /\s/.test(s)) return false;
      const m = s.match(/^([a-z]*)((?:[.#][\w-]+|\[[\w-]+\])*)$/i);
      if (!m) return false;
      if (m[1] && m[1].toUpperCase() !== this.tagName) return false;
      for (const p of m[2].match(/[.#][\w-]+|\[[\w-]+\]/g) || []) {
        if (p[0] === "." && !this.classes.has(p.slice(1))) return false;
        if (p[0] === "#" && this.id !== p.slice(1)) return false;
        if (p[0] === "[") {
          const a = p.slice(1, -1).replace(/^data-/, "").replace(/-(\w)/g, (_, c) => c.toUpperCase());
          if (!(a in this.dataset)) return false;
        }
      }
      return true;
    });
  }
  closest(sel) { for (let x = this; x; x = x.parent) if (x.correspond(sel)) return x; return null; }
  // la propagation du navigateur : capture de la racine vers la cible, la cible, puis bulle
  dispatch(type, extra = {}) {
    const etats = { arrete: false, immediat: false, empeche: false };
    const brut = { type, target: this, button: 0, buttons: 1, clientX: 500, clientY: 400, pointerId: 1,
      altKey: false, ctrlKey: false, shiftKey: false, metaKey: false, detail: 1, ...extra };
    const ev = new Proxy(brut, {
      get: (o, k) => {
        if (k === "stopPropagation") return () => { note("stopPropagation"); etats.arrete = true; };
        if (k === "stopImmediatePropagation") return () => { note("stopImmediatePropagation"); etats.arrete = etats.immediat = true; };
        if (k === "preventDefault") return () => { note("preventDefault"); etats.empeche = true; };
        if (k !== "target" && k !== "type" && typeof k === "string") note("ev." + k);
        return o[k];
      },
    });
    const chemin = [];
    for (let x = this; x; x = x.parent) chemin.unshift(x);
    const jouer = (x, filtre) => {
      courant = x;
      for (const e of x.ec.filter(filtre)) {
        try { e.fn(ev); } catch (err) { note("exception:" + err.message); }
        if (etats.immediat) break;
      }
      courant = null;
    };
    for (const x of chemin.slice(0, -1)) { jouer(x, (y) => y.type === type && y.capture); if (etats.arrete) return etats; }
    for (const x of [...chemin].reverse()) {
      jouer(x, (y) => y.type === type && (x === this || !y.capture));
      if (etats.arrete) return etats;
    }
    return etats;
  }
}

// un objet « fantôme » : toute propriété, tout appel, toute itération répondent sans rien faire (les panneaux des
// modules sont construits à l'init sur ce faux document — seul #stage compte ici)
function fantome() {
  const cache = new Map();
  const f = new Proxy(function () {}, {
    get: (t, k) => {
      if (k === "then") return undefined;
      if (k === Symbol.iterator) return function* () {};
      if (k === Symbol.toPrimitive) return () => 0;
      if (k === "length") return 0;
      if (!cache.has(k)) cache.set(k, fantome());
      return cache.get(k);
    },
    set: (t, k, v) => { cache.set(k, v); return true; },
    apply: () => fantome(),
    construct: () => fantome(),
    has: () => true,
  });
  return f;
}

// l'état et le cœur : toute lecture PENDANT un geste est notée (dansPanneau excepté — c'est la garde)
function traceur(base, nom) {
  return new Proxy(base, {
    get: (o, k) => {
      if (typeof k === "string" && k !== "dansPanneau") note(nom + "." + k);
      if (k in o) return o[k];
      if (typeof k === "symbol") return undefined;
      o[k] = fantome();
      return o[k];
    },
    set: (o, k, v) => { o[k] = v; return true; },
  });
}

// monte UN module sur sa scène : le vrai init(VL), l'outil voulu actif
function monter(init, etatOutil) {
  const racine = new Noeud(null, { tag: "html" });
  const stage = new Noeud(racine, { tag: "main", id: "stage" });
  const scene = new Noeud(stage, { tag: "rect", data: { objet: "o1" } });
  const etatBrut = { outil: "select", persona: "vecteur", doc: { calques: [{ id: "c1", objets: [] }], taille: { w: 800, h: 600 } },
    selection: [], zoom: 1, tx: 0, ty: 0, calqueActif: "c1", styleCourant: {}, typo: {}, grille: {}, ...etatOutil };
  const etat = traceur(etatBrut, "etat");
  const dollar = (s) => { note("$" + s); return s === "#stage" ? stage : fantome(); };
  const VL = traceur({ etat, $: dollar, dansPanneau, docPt: () => [0, 0], ecranPt: () => [0, 0], aimantePt: (x, y) => [x, y],
    surOutil: () => {}, surTouche: () => {}, surRendu: () => {}, surSelection: () => {}, surOverlay: () => {},
    surVue: () => {}, surHistorique: () => {}, surCharge: () => {}, toast: () => {} }, "VL");
  const avant = { document: globalThis.document, window: globalThis.window, localStorage: globalThis.localStorage };
  globalThis.document = fantome();
  globalThis.window = fantome();
  globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
  let erreurInit = "";
  try { init(VL); } catch (e) { erreurInit = e.message; }
  const remettre = () => Object.assign(globalThis, avant);
  return { racine, stage, scene, etat, VL, erreurInit, remettre };
}

// les trois panneaux flottants, posés dans #stage comme dans la page (garderClics en bulle, comme les modules)
function poserPanneau(stage, sorte) {
  const spec = sorte === "iacalque" ? { id: "iaCalqueDlg", classes: ["ia-dlg", "iac-dlg"] }
    : sorte === "ia" ? { id: "iaDialogue", classes: ["ia-dlg"] }
      : { tag: "textarea", classes: ["tx-editeur"] };
  const el = new Noeud(stage, spec);
  const bouton = sorte === "editeur" ? el : new Noeud(el, { tag: "button", id: "iacGo" });
  el.panneau = bouton.panneau = true;      // les écouteurs du panneau lui-même (garderClics…) ne sont pas l'outil
  const vus = [];
  el.addEventListener("pointerdown", (ev) => vus.push("pointerdown"));
  el.addEventListener("click", (ev) => vus.push("click:" + (ev.target === bouton ? "bouton" : "autre")));
  garderClics(el);
  return { el, bouton, vus };
}

// UN clic réel sur le bouton du panneau : pointerdown (à travers la capture des outils) puis click — sur #stage si
// un outil a capturé le pointeur, sinon sur le bouton
function cliquer(stage, cible) {
  const avant = stage.captures;
  compteur = [];
  const down = cible.dispatch("pointerdown");
  const traces = compteur;
  compteur = null;
  const capture = stage.captures > avant;
  const clic = (capture ? stage : cible).dispatch("click");
  return { traces, capture, down, clic };
}

function geste(cible, type, extra) {
  compteur = [];
  const r = cible.dispatch(type, extra);
  const traces = compteur;
  compteur = null;
  return { traces, r };
}

const MODULES = [
  { nom: "Plume (mod-plumeui)", init: initPlume, etat: { outil: "plume" }, gestes: ["pointerdown", "contextmenu", "dblclick"] },
  { nom: "Texte (mod-texteui)", init: initTexteUI, etat: { outil: "texte" }, gestes: ["pointerdown"] },
  { nom: "Nœud (mod-noeudui)", init: initNoeudUI, etat: { outil: "noeuds" }, gestes: ["pointerdown", "dblclick"] },
  { nom: "Pipette (mod-pipetteui)", init: initPipetteUI, etat: { outil: "pipette" }, gestes: ["pointerdown", "contextmenu"] },
  { nom: "Main / Recadrer (mod-outils3ui)", init: initOutils3, etat: { outil: "main" }, gestes: ["pointerdown"] },
  { nom: "Recadrer, double-clic (mod-outils3ui)", init: initOutils3, etat: { outil: "recadrer" }, gestes: ["dblclick"] },
  { nom: "Pixel (mod-pixelui)", init: initPixelUI, etat: { outil: "px-pinceau", persona: "pixel" }, gestes: ["pointerdown", "contextmenu"] },
  { nom: "Alt+glisser, double-clic (mod-selectionui)", init: initSelectionUI, etat: { outil: "select" }, gestes: ["pointerdown", "dblclick"], extra: { altKey: true } },
  { nom: "Pinceau vectoriel (mod-apparence2)", init: initApparence2, etat: { outil: "pinceauv" }, gestes: ["pointerdown"] },
  { nom: "Tranche (mod-exportplus)", init: initExportPlus, etat: { outil: "tranche" }, gestes: ["pointerdown"] },
  { nom: "Formes, crayon… (mod-outils2)", init: initOutils2, etat: { outil: "forme" }, gestes: ["pointerdown"] },
  { nom: "Sélection (mod-tools, en bulle)", init: initOutils, etat: { outil: "select" }, gestes: ["pointerdown", "dblclick"] },
];

function scenario(m) {
  const s = monter(m.init, m.etat);
  const res = { erreurInit: s.erreurInit, panneaux: {}, temoin: {} };
  const ecouteurs = s.stage.ec.filter((e) => m.gestes.includes(e.type)).length;
  res.ecouteurs = ecouteurs;
  for (const sorte of ["iacalque", "ia", "editeur"]) {
    const p = poserPanneau(s.stage, sorte);
    const c = cliquer(s.stage, p.bouton);
    const autres = m.gestes.filter((t) => t !== "pointerdown").map((t) => ({ t, ...geste(p.bouton, t, m.extra) }));
    const alt = m.extra ? geste(p.bouton, "pointerdown", m.extra) : null;
    res.panneaux[sorte] = {
      tracesClic: c.traces, capture: c.capture, vus: p.vus.slice(),
      autres: autres.filter((a) => a.traces.length).map((a) => `${a.t}:${a.traces.slice(0, 3).join("+")}`),
      alt: alt ? alt.traces : [],
    };
    p.el.parent = null;                   // retiré de la scène
  }
  // témoin : le même geste sur la SCÈNE, outil actif → l'outil réagit (la garde ne le coupe pas)
  for (const t of m.gestes) res.temoin[t] = geste(s.scene, t, m.extra).traces.length;
  s.remettre();
  return res;
}

/* ── [garde] l'utilitaire ── */
{
  const st = new Noeud(null, { id: "stage" });
  const dlg = new Noeud(st, { classes: ["ia-dlg"] }), b = new Noeud(dlg, { tag: "button" });
  const ta = new Noeud(st, { tag: "textarea", classes: ["tx-editeur"] });
  const marque = new Noeud(st); garderClics(marque); const dedans = new Noeud(marque);
  const sc = new Noeud(st, { tag: "rect" });
  ok("[garde] un geste d'un bouton du dialogue (.ia-dlg) vient d'un panneau", dansPanneau({ target: b }));
  ok("[garde] l'éditeur en place (.tx-editeur) est un panneau", dansPanneau({ target: ta }));
  ok("[garde] un élément gardé par garderClics est reconnu (data-vl-flottant)", dansPanneau({ target: dedans }) && marque.dataset.vlFlottant === "1");
  ok("[garde] la scène n'en est pas un", !dansPanneau({ target: sc }) && !dansPanneau({ target: st }));
  ok("[garde] sans cible (ou sans closest) : non", !dansPanneau({}) && !dansPanneau(null) && !dansPanneau({ target: {} }));
  ok("[garde] le sélecteur nomme les deux dialogues et l'éditeur", [".ia-dlg", ".tx-editeur"].every((x) => PANNEAUX_FLOTTANTS.includes(x)));
}

/* ── [outils] chaque outil en capture ignore le panneau, et le clic atteint le bouton ── */
for (const m of MODULES) {
  const r = scenario(m);
  ok(`[outils] ${m.nom} : init sans erreur sur le mini-DOM`, !r.erreurInit, r.erreurInit);
  ok(`[outils] ${m.nom} : écoute bien #stage (${m.gestes.join(", ")})`, r.ecouteurs >= m.gestes.length, r.ecouteurs);
  for (const [sorte, p] of Object.entries(r.panneaux)) {
    ok(`[outils] ${m.nom} / ${sorte} : le pointerdown du panneau ne fait RIEN lire ni faire à l'outil`,
       !p.tracesClic.length, p.tracesClic.slice(0, 6).join(","));
    ok(`[outils] ${m.nom} / ${sorte} : aucun setPointerCapture, le pointerdown arrive au panneau`,
       !p.capture && p.vus.includes("pointerdown"), JSON.stringify(p.vus));
    ok(`[outils] ${m.nom} / ${sorte} : le click atteint le BOUTON du panneau`, p.vus.includes("click:bouton"), JSON.stringify(p.vus));
    ok(`[outils] ${m.nom} / ${sorte} : ${m.gestes.filter((t) => t !== "pointerdown").join(", ") || "—"} du panneau ignorés`,
       !p.autres.length, p.autres.join(" | "));
    if (m.extra) ok(`[outils] ${m.nom} / ${sorte} : Alt + clic dans le panneau ignoré`, !p.alt.length, p.alt.slice(0, 4).join(","));
  }
  for (const [t, nb] of Object.entries(r.temoin)) {
    ok(`[témoin] ${m.nom} : ${t} sur la scène, outil actif → l'outil réagit`, nb > 0, nb);
  }
}

/* ── [core] le panoramique (Espace + clic, clic du milieu) et la molette : LEUR texte, extrait de core.js ── */
{
  const src = readFileSync(new URL("../js/core.js", import.meta.url), "utf8");
  const i0 = src.indexOf("let pan = null;"), i1 = src.indexOf('stage.addEventListener("pointerup", () => { pan = null; }, true);');
  const w0 = src.indexOf('stage.addEventListener("wheel"'), w1 = src.indexOf("}, { passive: false });", w0);
  ok("[core] le bloc du panoramique et celui de la molette sont trouvés dans core.js", i0 > 0 && i1 > i0 && w0 > 0 && w1 > w0);
  ok("[core] core.js importe dansPanneau et le pose dans VL", /import \{ dansPanneau \} from "\.\/mod-flottant\.js";/.test(src) && /etat, api, \$, dansPanneau,/.test(src));
  const bloc = src.slice(w0, w1 + "}, { passive: false });".length) + "\n" + src.slice(i0, i1);
  const fabrique = new Function("stage", "etat", "dansPanneau", "appliquerVue", "stageRect",
    `let espace = true;\n${bloc}\nreturn () => pan;`);
  const essai = (cible, type, extra) => {
    const racine = new Noeud(null), stage = new Noeud(racine, { id: "stage" });
    const etat = traceur({ zoom: 1, tx: 0, ty: 0 }, "etat");
    const pan = fabrique(stage, etat, dansPanneau, () => note("appliquerVue"), () => ({ left: 0, top: 0 }));
    const p = poserPanneau(stage, "iacalque");
    const t = cible === "panneau" ? p.bouton : new Noeud(stage, { tag: "rect" });
    const avant = stage.captures;
    const g = geste(t, type, extra);
    const capture = stage.captures > avant;
    const clic = cible === "panneau" && type === "pointerdown" ? (capture ? stage : t).dispatch("click") : null;
    return { traces: g.traces, pan: pan(), capture, vus: p.vus };
  };
  const a = essai("panneau", "pointerdown", { button: 0 });
  ok("[core] Espace + clic sur le panneau : pas de panoramique, rien de lu", !a.pan && !a.capture && !a.traces.length, a.traces.join(","));
  ok("[core] … et le click atteint le bouton du panneau", a.vus.includes("click:bouton"), JSON.stringify(a.vus));
  const b = essai("panneau", "pointerdown", { button: 1 });
  ok("[core] clic du milieu sur le panneau : pas de panoramique", !b.pan && !b.capture, b.traces.join(","));
  const w = essai("panneau", "wheel", { deltaY: -100 });
  ok("[core] la molette sur le panneau ne zoome pas", !w.traces.length, w.traces.join(","));
  const ta = essai("scene", "pointerdown", { button: 0 });
  ok("[témoin] core : Espace + clic sur la scène lance le panoramique (capture du pointeur)", !!ta.pan && ta.capture);
  const tw = essai("scene", "wheel", { deltaY: -100 });
  ok("[témoin] core : la molette sur la scène zoome", tw.traces.includes("appliquerVue"), tw.traces.join(","));
}

/* ── [mutation] mod-plumeui SANS sa garde : le banc doit la voir ── */
{
  const src = readFileSync(new URL("../js/mod-plumeui.js", import.meta.url), "utf8");
  const garde = /if \(VL\.dansPanneau\(ev\)\) return;/g;
  ok("[mutation] les trois gardes de la Plume sont dans la source", (src.match(garde) || []).length === 3, (src.match(garde) || []).length);
  const mutant = src.replace(garde, "")
    .replace(/from "\.\/([\w-]+\.js)"/g, (_, f) => `from "${new URL("../js/" + f, import.meta.url).href}"`);
  ok("[mutation] la source mutée diffère", mutant !== src && !garde.test(mutant));
  const mod = await import("data:text/javascript;base64," + Buffer.from(mutant, "utf8").toString("base64"));
  const r = scenario({ ...MODULES[0], init: mod.initPlume });
  const p = r.panneaux.iacalque;
  ok("[mutation] sans garde, la Plume capture le pointeur sur un clic du panneau (le défaut I1)", p.capture, JSON.stringify(p.tracesClic.slice(0, 6)));
  ok("[mutation] sans garde, le click part sur #stage : le bouton du panneau ne le reçoit pas", !p.vus.includes("click:bouton"), JSON.stringify(p.vus));
  ok("[mutation] sans garde, le pointerdown n'arrive même pas au panneau (stopPropagation de l'outil)", !p.vus.includes("pointerdown"), JSON.stringify(p.vus));
}

if (echecs.length) {
  console.error("ECHECS panneaux_flottants :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA panneaux_flottants : PASS (${n} controles)`);
