"""G (retours IA, tâche 8, 27/09/2026) — COUCHE DES CHAMPS IA.

`frontend/shared/dz-champ-ia.js` (copie OCTET POUR OCTET dans
`frontend/dist/shared/`) marque les champs de saisie des générations média
d'après une TABLE DE RÈGLES déclarative, et les habille (liseré conic-gradient
violet → bleu → orange, halo, reflet holographique au focus, variante B de la
maquette validée le 26/09) SANS déplacer le champ : aucun re-parentage (un
champ React déplacé dans un conteneur étranger fait lever `removeChild` /
`insertBefore` à React au prochain rendu conditionnel), une barre absolue posée
en frère du champ (badge « IA » + emplacements vides pour la pastille de modèle
T9 et le micro T10).

Le banc charge la couche sous Node dans un DOM MINIMAL SIMULÉ (aucun shim DOM
réutilisable dans le dépôt : les bancs Cardforge/Établi posent des bouchons
ad hoc — mesuré le 27/09) : faux `document`, sélecteurs (balise, #id, .classe,
[attr], [attr="v"], [attr^="v"], descendant, listes), `MutationObserver`
qui notifie les ajouts, `matchMedia`, `getComputedStyle`.

ASSERTIONS NÉGATIVES avec TÉMOIN POSITIF dans la même passe : le Prompt du
Studio (`.dz-studio-grid`) n'est jamais marqué pendant que celui du Quick
l'est ; chaque exclusion (Voice Over, Narration, brief du Scheduler, Persona,
`#script` de l'Atelier, fountain, textes narrés des Chapitres, générateur de
prompt) a son témoin jamais marqué ; `#prompt` hors Material Forge n'est pas
marqué pendant qu'il l'est sur `/materialforge/`. ÉTAT VIDE : une page vide ne
reçoit aucune barre et aucune exception. Faute n°6 : aucun `detail` n'indexe
une clé absente (`.get`).

Un processus, `check`, `=== N passed, M failed ===`, code de sortie.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "shared" / "dz-champ-ia.js"
DIST = ROOT / "frontend" / "dist" / "shared" / "dz-champ-ia.js"
PAGES = [
    ROOT / "frontend" / "dist" / "index.html",
    ROOT / "frontend" / "atelier" / "index.html",
    ROOT / "frontend" / "cardforge" / "index.html",
    ROOT / "frontend" / "materialforge" / "index.html",
    ROOT / "frontend" / "spritelab" / "index.html",
    ROOT / "frontend" / "vectorlab" / "index.html",
]
BALISE = '<script src="/shared/dz-champ-ia.js"></script>'

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


# Le périmètre VALIDÉ (conception §G, relevé du 26/09) : sélecteurs attendus
# dans la table, et le genre de génération de chacun.
ATTENDUS_SEL = {
    'textarea[placeholder^="ex: sourit"]': "video",
    "input[placeholder=\"Prompt d'illustration…\"]": "image",
    "#globalStyle": "image",
    "#daStyle": "image",
    ".entity-desc": "image",
    ".entity-style": "image",
    ".shot-action": "image",
    "textarea.svm-musicprompt": "musique",
    'textarea[aria-label="Paroles"]': "musique",
    "input.svm-sfxprompt": "sfx",
    "textarea.svx-gprompt": "sfx",
    '[placeholder^="AI prompt"]': "image",
    '[placeholder^="Describe an image to create"]': "image",
    '[placeholder^="e.g. a knight character"]': "3d",
    "#animPrompt": "anim",
    "#prompt": "image",
    "#cf-face-prompt": "image",
    "textarea.cff-prompt": "image",
    'input[data-field="texture_prompt"]': "3d",
    "#iaTexte": "image",
    "#vitIaPrompt": "image",
}
ATTENDUS_LIB = {"Prompt": "video", "Script (": "video"}
GENRES = {"video", "image", "anim", "sfx", "musique", "3d"}

HARNAIS = r"""
"use strict";
const fs = require("fs");
const COUCHE = process.argv[2];

/* ---------- DOM minimal ---------- */
function decouper(s, sep) {            // découpe hors [] et guillemets
  const out = []; let cur = "", q = null, b = 0;
  for (const ch of s) {
    if (q) { cur += ch; if (ch === q) q = null; continue; }
    if (ch === '"' || ch === "'") { q = ch; cur += ch; continue; }
    if (ch === "[") b++; if (ch === "]") b--;
    if (b === 0 && sep.test(ch)) { if (cur.trim()) out.push(cur.trim()); cur = ""; continue; }
    cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}
function compose(c) {                  // "tag#id.cl[a^=\"v\"]"
  const r = { tag: null, id: null, cls: [], attrs: [] };
  const m = c.match(/^[a-zA-Z][\w-]*/); let i = 0;
  if (m) { r.tag = m[0].toLowerCase(); i = m[0].length; }
  while (i < c.length) {
    const ch = c[i];
    if (ch === "#" || ch === ".") {
      const mm = c.slice(i + 1).match(/^[\w-]+/); if (!mm) throw new Error("sel " + c);
      if (ch === "#") r.id = mm[0]; else r.cls.push(mm[0]); i += 1 + mm[0].length;
    } else if (ch === "[") {
      let j = i + 1, q = null;
      while (j < c.length) { const x = c[j]; if (q) { if (x === q) q = null; } else if (x === '"' || x === "'") q = x; else if (x === "]") break; j++; }
      const corps = c.slice(i + 1, j);
      const mm = corps.match(/^([\w-]+)\s*(?:(\^?=)\s*(?:"([^"]*)"|'([^']*)'|([^\]]*)))?$/);
      if (!mm) throw new Error("attr " + corps);
      r.attrs.push({ n: mm[1], op: mm[2] || null, v: mm[3] ?? mm[4] ?? mm[5] ?? null });
      i = j + 1;
    } else throw new Error("sel non géré : " + c);
  }
  return r;
}
function correspond(el, cp) {
  if (!el || el.nodeType !== 1) return false;
  if (cp.tag && el.tagName.toLowerCase() !== cp.tag) return false;
  if (cp.id && el.getAttribute("id") !== cp.id) return false;
  for (const c of cp.cls) if (!el.classList.contains(c)) return false;
  for (const a of cp.attrs) {
    if (!el.hasAttribute(a.n)) return false;
    const v = el.getAttribute(a.n);
    if (a.op === "=" && v !== a.v) return false;
    if (a.op === "^=" && !(a.v && v.startsWith(a.v))) return false;
  }
  return true;
}
function matchSel(el, sel) {
  return decouper(sel, /,/).some(function (cx) {
    const parts = decouper(cx, /\s/).map(compose);
    if (!correspond(el, parts[parts.length - 1])) return false;
    let k = parts.length - 2, cur = el.parentNode;
    while (k >= 0 && cur) { if (correspond(cur, parts[k])) k--; cur = cur.parentNode; }
    return k < 0;
  });
}
let OBS = [];
class Noeud {
  constructor(t) { this.nodeType = t; this.childNodes = []; this.parentNode = null; }
  get parentElement() { return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null; }
  get isConnected() { let n = this; while (n) { if (n === document) return true; n = n.parentNode; } return false; }
  get nextSibling() { const p = this.parentNode; if (!p) return null; return p.childNodes[p.childNodes.indexOf(this) + 1] || null; }
  get previousSibling() { const p = this.parentNode; if (!p) return null; return p.childNodes[p.childNodes.indexOf(this) - 1] || null; }
  get firstElementChild() { return this.childNodes.find(n => n.nodeType === 1) || null; }
  get children() { return this.childNodes.filter(n => n.nodeType === 1); }
  get textContent() { return this.nodeType === 3 ? this.data : this.childNodes.map(n => n.textContent).join(""); }
  set textContent(v) { this.childNodes.forEach(n => n.parentNode = null); this.childNodes = []; if (v) this.appendChild(document.createTextNode(String(v))); }
  insertBefore(n, ref) {
    if (n.parentNode) n.parentNode.removeChild(n);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (ref && i < 0) throw new Error("NotFoundError insertBefore");
    if (i < 0) this.childNodes.push(n); else this.childNodes.splice(i, 0, n);
    n.parentNode = this; notifier(this, [n], []); return n;
  }
  appendChild(n) { return this.insertBefore(n, null); }
  removeChild(n) {
    const i = this.childNodes.indexOf(n); if (i < 0) throw new Error("NotFoundError removeChild");
    this.childNodes.splice(i, 1); n.parentNode = null; notifier(this, [], [n]); return n;
  }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  contains(n) { while (n) { if (n === this) return true; n = n.parentNode; } return false; }
  _tous(out) { for (const c of this.childNodes) if (c.nodeType === 1) { out.push(c); c._tous(out); } return out; }
  getElementsByTagName(t) { t = t.toLowerCase(); return this._tous([]).filter(e => t === "*" || e.tagName.toLowerCase() === t); }
  querySelectorAll(s) { return this._tous([]).filter(e => matchSel(e, s)); }
  querySelector(s) { return this.querySelectorAll(s)[0] || null; }
  addEventListener() {} removeEventListener() {}
}
function notifier(cible, aj, rm) {
  for (const o of OBS) if (o.cible && (o.cible === cible || o.cible.contains(cible)))
    o.file.push({ type: "childList", target: cible, addedNodes: aj, removedNodes: rm });
}
class ListeClasses {
  constructor(el) { this.el = el; }
  _l() { return (this.el.getAttribute("class") || "").split(/\s+/).filter(Boolean); }
  contains(c) { return this._l().includes(c); }
  add(...c) { const l = this._l(); c.forEach(x => { if (!l.includes(x)) l.push(x); }); this.el.setAttribute("class", l.join(" ")); }
  remove(...c) { this.el.setAttribute("class", this._l().filter(x => !c.includes(x)).join(" ")); }
  toggle(c, f) { const a = f === undefined ? !this.contains(c) : f; a ? this.add(c) : this.remove(c); return a; }
}
class Style {
  constructor() { this._p = {}; }
  setProperty(k, v) { this._p[k] = String(v); }
  getPropertyValue(k) { return this._p[k] || ""; }
  removeProperty(k) { delete this._p[k]; }
}
const STYLE_PROXY = { get(t, k) { if (k in t) return t[k]; return t._p[k] || ""; }, set(t, k, v) { t._p[k] = String(v); return true; } };
class Element extends Noeud {
  constructor(tag) { super(1); this.tagName = tag.toUpperCase(); this._a = {}; this.classList = new ListeClasses(this); this.style = new Proxy(new Style(), STYLE_PROXY); this._rect = null; this._cs = {}; this.value = ""; }
  getAttribute(n) { return n in this._a ? this._a[n] : null; }
  setAttribute(n, v) { this._a[n] = String(v); }
  hasAttribute(n) { return n in this._a; }
  removeAttribute(n) { delete this._a[n]; }
  get id() { return this.getAttribute("id") || ""; }
  get className() { return this.getAttribute("class") || ""; }
  set className(v) { this.setAttribute("class", v); }
  get type() { return (this.getAttribute("type") || (this.tagName === "INPUT" ? "text" : "")).toLowerCase(); }
  get placeholder() { return this.getAttribute("placeholder") || ""; }
  matches(s) { return matchSel(this, s); }
  closest(s) { let n = this; while (n && n.nodeType === 1) { if (matchSel(n, s)) return n; n = n.parentNode; } return null; }
  getBoundingClientRect() {
    const r = this._rect || { left: 0, top: 0, width: 0, height: 0 };
    // une barre absolue : left/top de son style s'ajoutent à l'origine de son parent
    if (this.classList.contains("dzia-barre")) {
      const p = this.parentNode && this.parentNode._rect || { left: 0, top: 0 };
      const l = parseFloat(this.style.left) || 0, t = parseFloat(this.style.top) || 0;
      return { left: p.left + l, top: p.top + t, width: 30, height: 16, right: p.left + l + 30, bottom: p.top + t + 16 };
    }
    return { left: r.left, top: r.top, width: r.width, height: r.height, right: r.left + r.width, bottom: r.top + r.height };
  }
  get offsetWidth() { return ((this._rect || {}).width || 0) + (this._grandit && this.style.paddingRight ? 14 : 0); }
  get offsetHeight() { return (this._rect || {}).height || 0; }
  get clientHeight() { return this.offsetHeight; }
  get offsetParent() { return this._cache ? null : (this.parentNode || null); }
  focus() {} blur() {}
}
class Texte extends Noeud { constructor(d) { super(3); this.data = d; } }
class Doc extends Noeud {
  constructor() { super(9); }
  createElement(t) { return new Element(t); }
  createTextNode(d) { return new Texte(d); }
  getElementById(i) { return this._tous([]).find(e => e.getAttribute("id") === i) || null; }
}
const document = new Doc();
const html = document.createElement("html"); document.appendChild(html);
const head = document.createElement("head"); html.appendChild(head);
const body = document.createElement("body"); html.appendChild(body);
document.documentElement = html; document.head = head; document.body = body; document.readyState = "complete";
let REDUIT = false;
const DEFAUT_CS = { backgroundColor: "rgb(20, 22, 28)", borderTopWidth: "1px", boxSizing: "border-box",
  position: "static", paddingTop: "8px", paddingRight: "8px", paddingBottom: "8px", paddingLeft: "8px", display: "block" };
class MO { constructor(cb) { this.cb = cb; this.file = []; this.cible = null; OBS.push(this); }
  observe(c) { this.cible = c; } disconnect() { this.cible = null; }
  _vider() { const f = this.file; this.file = []; if (f.length) this.cb(f, this); } }
const window = {
  document, location: { pathname: "/" },
  getComputedStyle(el) { const o = Object.assign({}, DEFAUT_CS, el._cs || {}); o.getPropertyValue = k => o[k] || ""; return o; },
  matchMedia(q) { return { matches: /reduce/.test(q) ? REDUIT : false, addEventListener() {}, addListener() {} }; },
  MutationObserver: MO,
  ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
  addEventListener() {}, removeEventListener() {},
  setTimeout: (f, ms) => setTimeout(f, ms), clearTimeout: t => clearTimeout(t),
  setInterval: () => 0, clearInterval: () => {},
  requestAnimationFrame: f => setTimeout(f, 0),
};
window.window = window;
global.window = window; global.document = document; global.location = window.location;
global.getComputedStyle = window.getComputedStyle; global.matchMedia = window.matchMedia;
global.MutationObserver = MO; global.ResizeObserver = window.ResizeObserver;
global.requestAnimationFrame = window.requestAnimationFrame;
global.setInterval = window.setInterval; global.clearInterval = window.clearInterval;

/* ---------- fabriques ---------- */
function el(tag, attrs, parent, rect) {
  const e = document.createElement(tag);
  for (const k in (attrs || {})) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  e._rect = rect || { left: 10, top: 10, width: 300, height: tag === "input" ? 30 : 90 };
  return e;
}
function ie(parent, libelle, tag, attrs) {           // composant `ie` du bundle
  const d = el("div", {}, parent); const b = el("button", {}, d);
  const s = el("span", { class: "upper" }, b); s.textContent = libelle;
  const c = el("div", {}, d); return el(tag || "textarea", attrs || {}, c);
}
const R = {};
function etat(e) {
  const b = e && e.nextSibling;
  return { dz: e ? e.getAttribute("data-dz-ia") : null, regle: e ? e.getAttribute("data-dz-ia-regle") : null,
    barre: !!(b && b.nodeType === 1 && b.classList.contains("dzia-barre")),
    badge: b && b.querySelector ? (b.querySelector(".dzia-badge") || { textContent: "" }).textContent : "",
    slots: b && b.querySelectorAll ? b.querySelectorAll("[data-dzia-slot]").map(x => x.getAttribute("data-dzia-slot") + ":" + x.childNodes.length) : [],
    fond: e ? e.style.getPropertyValue("--dzia-fond") : "", classe: e ? e.classList.contains("dzia-champ") : false };
}
function pause(ms) { return new Promise(r => setTimeout(r, ms)); }

(async function () {
  // état vide : avant la couche, aucune API
  R.avant = typeof window.DzChampIA;
  // ÉTAT VIDE : une page vide (la couche se charge sur un body vide)
  eval(fs.readFileSync(COUCHE, "utf8"));
  const A = window.DzChampIA;
  R.api = { type: typeof A, regles: Array.isArray(A && A.regles), marquer: typeof (A && A.marquer), version: typeof (A && A.version),
    exclus: Array.isArray(A && A.exclus) };
  R.regles = (A && A.regles || []).map(r => ({ id: r.id, vue: r.vue, sel: r.sel || null, libelle: r.libelle || null, genre: r.genre, page: r.page || null }));
  R.vide = { barres: body.querySelectorAll(".dzia-barre").length, marques: body.querySelectorAll("[data-dz-ia]").length };
  const styles = head.querySelectorAll("style").filter(s => s.getAttribute("id") === "dzia-style");
  R.style = styles.length ? styles[0].textContent : "";

  // ---------- la page SPA (pathname "/") ----------
  const quick = el("div", { class: "quick" }, body);
  const fQuick = ie(quick, "Prompt", "textarea");
  const fScript = ie(quick, "Script (12/4900 chars)", "textarea");
  const fMotion = el("textarea", { placeholder: "ex: sourit, hoche la tête, gestes calmes de la main" }, quick);
  const grid = el("div", { class: "dz-studio-grid" }, body);
  const fStudio = ie(grid, "Prompt", "textarea");                          // témoin : jamais
  const fStudioLib = el("input", { placeholder: "Describe an image to create…" }, grid); // témoin : zone exclue même si sélecteur
  const voice = el("div", { "data-dzquickvoice": "1" }, body);
  const fVoice = ie(voice, "Script (0/5000)", "textarea", { "data-dztext": "1" }); // témoin : exclu
  const fChap1 = el("input", { placeholder: "Prompt d'illustration…" }, body);
  const fChap2 = el("input", { placeholder: "Prompt d'illustration…" }, body);
  const fNarr = el("textarea", { placeholder: "Narrated scene text…" }, body);
  const fProf = el("textarea", { placeholder: "Dans les profondeurs, quelque chose s'éveille…" }, body);
  const fNb = el("textarea", { class: "svm-nbtext" }, body);
  const fAc = el("textarea", { class: "dzm-actext" }, body);
  const fPers = el("input", { class: "dzm-acpersona", placeholder: "Persona (facultatif)" }, body);
  const fBrief = ie(body, "Brief (what should this week say?)", "textarea", { placeholder: "e.g. Week around the $DEEPOTUS staking launch." });
  const fGen = el("input", { placeholder: "e.g. fits the $DEEPOTUS Pyth-feed announcement" }, body);
  const fMus = el("textarea", { class: "svm-musicprompt" }, body);
  const fPar = el("textarea", { class: "svm-musicprompt", "aria-label": "Paroles" }, body);
  const fSfx = el("input", { class: "svm-sfxprompt", type: "text" }, body);
  const fSons = el("textarea", { class: "svx-gprompt" }, body);
  const fTpl = el("input", { placeholder: "AI prompt (mascot…)" }, body);
  const fLib = el("input", { placeholder: "Describe an image to create…" }, body);
  const fGa = el("input", { placeholder: "e.g. a knight character" }, body);
  const fPromptSpa = el("textarea", { id: "prompt" }, body);               // témoin : #prompt hors Material Forge
  const fScriptSpa = el("textarea", { id: "script" }, body);
  const fCheck = el("input", { type: "checkbox", class: "svm-sfxprompt" }, body); // pas un champ de texte
  const fTransp = el("textarea", { placeholder: "Describe an image to create… (fond transparent)" }, body);
  fTransp._cs = { backgroundColor: "rgba(0, 0, 0, 0)" }; quick._cs = { backgroundColor: "rgb(1, 2, 3)" };
  body.removeChild(fTransp); quick.appendChild(fTransp);
  const fBord0 = el("input", { placeholder: "AI prompt (sans bord)" }, body); fBord0._cs = { borderTopWidth: "0px" };
  const fBord0Pad0 = el("input", { placeholder: "AI prompt (sans bord ni padding)" }, body); fBord0Pad0._cs = { borderTopWidth: "0px", paddingTop: "0px" };
  const le = el("div", { class: "le" }, body, { left: 10, top: 10, width: 320, height: 30 }); le._cs = { backgroundColor: "rgb(9, 9, 9)" };
  const fLe = el("input", { placeholder: "e.g. a knight character" }, le, { left: 20, top: 16, width: 290, height: 18 }); fLe._cs = { borderTopWidth: "0px" };
  const carte = el("div", { class: "svm-card" }, body, { left: 10, top: 10, width: 840, height: 300 });
  const fCarte = el("textarea", { class: "svm-musicprompt" }, carte, { left: 20, top: 200, width: 820, height: 54 }); fCarte._cs = { borderTopWidth: "0px" };
  const fGrand = el("input", { placeholder: "AI prompt (largeur de contenu)" }, body); fGrand._grandit = true;
  const fMain = el("textarea", { "data-dz-ia": "musique" }, body);       // posé à la main
  const fMainStudio = el("textarea", { "data-dz-ia": "image" }, grid);   // posé à la main, même dans le Studio
  const parentAvant = fQuick.parentNode, precAvant = fQuick.previousSibling, idxAvant = parentAvant.childNodes.indexOf(fQuick);

  A.marquer(document.body);
  const nb1 = body.querySelectorAll(".dzia-barre").length;
  A.marquer(document.body);                      // idempotence
  const nb2 = body.querySelectorAll(".dzia-barre").length;
  R.spa = { quick: etat(fQuick), script: etat(fScript), motion: etat(fMotion), studio: etat(fStudio), studioLib: etat(fStudioLib),
    voice: etat(fVoice), chap1: etat(fChap1), chap2: etat(fChap2), narr: etat(fNarr), prof: etat(fProf), nb: etat(fNb),
    ac: etat(fAc), pers: etat(fPers), brief: etat(fBrief), gen: etat(fGen), mus: etat(fMus), par: etat(fPar), sfx: etat(fSfx),
    sons: etat(fSons), tpl: etat(fTpl), lib: etat(fLib), ga: etat(fGa), promptSpa: etat(fPromptSpa), scriptSpa: etat(fScriptSpa),
    check: etat(fCheck), transp: etat(fTransp), bord0: etat(fBord0), main: etat(fMain), mainStudio: etat(fMainStudio) };
  R.bord0Classe = fBord0.classList.contains("dzia-bord") && fBord0.classList.contains("dzia-lis");
  R.bord0Pad = [fBord0.style.paddingTop, fBord0.style.paddingLeft, fBord0.style.paddingBottom];
  R.pad0 = { lis: fBord0Pad0.classList.contains("dzia-lis"), bord: fBord0Pad0.classList.contains("dzia-bord"), halo: fBord0Pad0.classList.contains("dzia-halo"), dz: fBord0Pad0.getAttribute("data-dz-ia") };
  R.le = { parentLis: le.classList.contains("dzia-lis"), champLis: fLe.classList.contains("dzia-lis"), champ: fLe.classList.contains("dzia-champ"),
    fond: le.style.getPropertyValue("--dzia-fond"), barre: etat(fLe).barre };
  R.carte = { carteLis: carte.classList.contains("dzia-lis"), champLis: fCarte.classList.contains("dzia-lis"), bord: fCarte.classList.contains("dzia-bord") };
  { const b = fGrand.nextSibling, rb = b.getBoundingClientRect(); R.grand = { largeur: fGrand.offsetWidth, pad: fGrand.style.paddingRight, haut: Math.round(rb.top - fGrand._rect.top), h: rb.height }; }
  R.reserve = fLib.style.paddingRight;
  R.deplace = { parent: fQuick.parentNode === parentAvant, prec: fQuick.previousSibling === precAvant,
    idx: parentAvant.childNodes.indexOf(fQuick) === idxAvant };
  R.idem = { nb1, nb2, marques: body.querySelectorAll(".dzia-champ").length,
    styles: head.querySelectorAll("style").filter(s => s.getAttribute("id") === "dzia-style").length };

  // ---------- observation des ajouts ----------
  const tard = el("input", { placeholder: "Describe an image to create… (tard)" }, null);
  body.appendChild(tard);
  const tardStudio = el("textarea", { class: "svx-gprompt" }, null); grid.appendChild(tardStudio);
  OBS.forEach(o => o._vider());
  await pause(120);
  R.obs = { tard: etat(tard), tardStudio: etat(tardStudio), nObs: OBS.filter(o => o.cible).length };

  // ---------- barre recalée sur le champ, puis nettoyée au retrait ----------
  fLib._rect = { left: 40, top: 200, width: 400, height: 30 };
  if (A.synchroniser) A.synchroniser();
  const bl = fLib.nextSibling, rb = bl.getBoundingClientRect();
  R.pos = { droite: Math.round(fLib._rect.left + fLib._rect.width - rb.right), haut: Math.round(rb.top - fLib._rect.top),
    bas: Math.round(fLib._rect.top + fLib._rect.height - rb.bottom) };
  fLib._cache = true; if (A.synchroniser) A.synchroniser();
  R.cache = bl.style.display;
  fLib._cache = false; if (A.synchroniser) A.synchroniser();
  R.revu = bl.style.display;
  body.removeChild(fLib); if (A.synchroniser) A.synchroniser();
  R.nettoye = !bl.isConnected;

  // ---------- pages à part : la même table, bornée par la page ----------
  function page(chemin, fabrique) {
    body.textContent = ""; window.location.pathname = chemin;
    const champs = fabrique(); A.marquer(document.body);
    const o = {}; for (const k in champs) o[k] = etat(champs[k]); return o;
  }
  R.pages = {
    atelier: page("/atelier/", () => ({ gs: el("input", { id: "globalStyle" }, body), da: el("textarea", { id: "daStyle" }, body),
      ed: el("textarea", { class: "entity-desc" }, body), es: el("input", { class: "entity-style" }, body),
      sa: el("textarea", { class: "shot-action" }, body), sas: el("div", { class: "shot-actions" }, body),
      script: el("textarea", { id: "script" }, body), fountain: el("textarea", { class: "scene-fountain" }, body) })),
    materialforge: page("/materialforge/", () => ({ prompt: el("textarea", { id: "prompt" }, body) })),
    spritelab: page("/spritelab/", () => ({ anim: el("textarea", { id: "animPrompt" }, body), prompt: el("textarea", { id: "prompt" }, body) })),
    cardforge: page("/cardforge/", () => ({ face: el("textarea", { id: "cf-face-prompt" }, body), decor: el("textarea", { class: "cff-prompt" }, body),
      tex: el("input", { "data-field": "texture_prompt" }, body) })),
    vectorlab: page("/vectorlab/", () => ({ ia: el("textarea", { id: "iaTexte" }, body), vit: el("input", { id: "vitIaPrompt", type: "text" }, body) })),
  };

  // ---------- reduced-motion : la règle du média est présente (la cascade est celle du navigateur) ----------
  process.stdout.write(JSON.stringify(R));
})().catch(e => { process.stdout.write(JSON.stringify({ erreur: String(e && e.stack || e) })); });
"""


def main():
    for p in (SRC, DIST):
        check(f"présent : {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}", p.is_file())
    if not SRC.is_file():
        print(f"\n=== {ok} passed, {fail} failed ===")
        return 1
    # ---------- non-dérive des deux copies ----------
    check("les deux copies sont identiques à l'octet (shared = dist/shared)",
          DIST.is_file() and SRC.read_bytes() == DIST.read_bytes())
    # ---------- balise dans chaque index.html visé ----------
    for p in PAGES:
        t = p.read_text(encoding="utf-8") if p.is_file() else ""
        check(f"balise {BALISE} ×1 dans {p.relative_to(ROOT)}", t.count(BALISE) == 1, str(t.count(BALISE)))
    # témoin : une page NON visée (Studio 3D, graphe de nœuds) ne la charge pas
    s3d = ROOT / "frontend" / "studio3d" / "index.html"
    t3d = s3d.read_text(encoding="utf-8") if s3d.is_file() else ""
    check("témoin : le Studio 3D (graphe de nœuds) ne charge pas la couche",
          s3d.is_file() and "dz-champ-ia.js" not in t3d)

    node = shutil.which("node")
    check("node présent", bool(node))
    if not node:
        print(f"\n=== {ok} passed, {fail} failed ===")
        return 1
    with tempfile.TemporaryDirectory() as d:
        h = pathlib.Path(d) / "harnais.js"
        h.write_text(HARNAIS, encoding="utf-8")
        pr = subprocess.run([node, str(h), str(SRC)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        R = json.loads(pr.stdout or "{}")
    except ValueError:
        R = {"erreur": "sortie illisible : " + (pr.stdout or "")[:400] + (pr.stderr or "")[:400]}
    check("le harnais Node tourne sans exception", "erreur" not in R, str(R.get("erreur", ""))[:600])

    # ---------- API ----------
    check("avant la couche : window.DzChampIA absent (état vide)", R.get("avant") == "undefined", str(R.get("avant")))
    api = R.get("api") or {}
    check("window.DzChampIA expose regles, marquer, version, exclus",
          api.get("type") == "object" and api.get("regles") and api.get("marquer") == "function"
          and api.get("version") == "string" and api.get("exclus"), str(api))
    vide = R.get("vide") or {}
    check("ÉTAT VIDE : page vide → 0 barre, 0 marque, aucune exception",
          vide.get("barres") == 0 and vide.get("marques") == 0, str(vide))

    # ---------- table des règles ----------
    regles = R.get("regles") or []
    ids = [r.get("id") for r in regles]
    check("chaque règle porte id, vue, sel | libelle, genre valide",
          bool(regles) and all(r.get("id") and r.get("vue") and (r.get("sel") or r.get("libelle"))
                               and r.get("genre") in GENRES for r in regles),
          str([r for r in regles if not (r.get("id") and r.get("vue") and r.get("genre") in GENRES)][:3]))
    check("ids de règle uniques", len(ids) == len(set(ids)), str(ids))
    par_sel = {r.get("sel"): r.get("genre") for r in regles if r.get("sel")}
    for sel, genre in ATTENDUS_SEL.items():
        check(f"périmètre : {sel} → {genre}", par_sel.get(sel) == genre, str(par_sel.get(sel)))
    par_lib = {r.get("libelle"): r.get("genre") for r in regles if r.get("libelle")}
    for lib, genre in ATTENDUS_LIB.items():
        check(f"périmètre (libellé) : « {lib} » → {genre}", par_lib.get(lib) == genre, str(par_lib.get(lib)))
    check("table close : aucune règle hors périmètre validé",
          set(par_sel) == set(ATTENDUS_SEL) and set(par_lib) == set(ATTENDUS_LIB),
          str(sorted(set(par_sel) ^ set(ATTENDUS_SEL))))
    check("#prompt borné à la page Material Forge",
          any(r.get("sel") == "#prompt" and (r.get("page") or "").startswith("/materialforge") for r in regles))

    # ---------- SPA : marquage, témoins ----------
    S = R.get("spa") or {}

    def st(k):
        return S.get(k) or {}

    for k, g in (("quick", "video"), ("script", "video"), ("motion", "video"), ("chap1", "image"), ("chap2", "image"),
                 ("mus", "musique"), ("par", "musique"), ("sfx", "sfx"), ("sons", "sfx"), ("tpl", "image"),
                 ("lib", "image"), ("ga", "3d")):
        check(f"SPA marqué : {k} → data-dz-ia={g}, classe, barre",
              st(k).get("dz") == g and st(k).get("classe") and st(k).get("barre"), str(st(k)))
    check("TÉMOIN POSITIF : le Prompt du Quick (libellé) est marqué", st("quick").get("dz") == "video", str(st("quick")))
    check("NÉGATIF : le Prompt du Studio (.dz-studio-grid) n'est JAMAIS marqué",
          st("studio").get("dz") is None and not st("studio").get("barre"), str(st("studio")))
    check("NÉGATIF : même un sélecteur du périmètre n'est pas marqué sous .dz-studio-grid",
          st("studioLib").get("dz") is None, str(st("studioLib")))
    for k, nom in (("voice", "Voice Over (libellé « Script ( » piégé)"), ("narr", "Chapitres « Narrated scene text »"),
                   ("prof", "Chapitres « Dans les profondeurs »"), ("nb", "Narration svm-nbtext"),
                   ("ac", "auto-clips dzm-actext"), ("pers", "Persona dzm-acpersona"),
                   ("brief", "brief du Scheduler"), ("gen", "générateur de prompt"),
                   ("scriptSpa", "#script"), ("promptSpa", "#prompt hors Material Forge"),
                   ("check", "case à cocher portant une classe du périmètre")):
        check(f"NÉGATIF : {nom} jamais marqué", st(k).get("dz") is None and not st(k).get("barre"), str(st(k)))
    check("posé à la main : data-dz-ia=musique honoré (classe + barre, genre gardé)",
          st("main").get("dz") == "musique" and st("main").get("classe") and st("main").get("barre"), str(st("main")))
    check("posé à la main : honoré même sous .dz-studio-grid (intention explicite)",
          st("mainStudio").get("dz") == "image" and st("mainStudio").get("barre"), str(st("mainStudio")))
    check("fond transparent : --dzia-fond remonte au premier ancêtre opaque",
          st("transp").get("fond") == "rgb(1, 2, 3)", str(st("transp").get("fond")))
    check("fond opaque : --dzia-fond = fond calculé du champ",
          st("lib").get("fond") == "rgb(20, 22, 28)", str(st("lib").get("fond")))
    check("bord 0 en border-box, padding ≥ 1 : dzia-bord + liseré, 1 px repris sur chaque padding",
          R.get("bord0Classe") is True and R.get("bord0Pad") == ["7px", "7px", "7px"], f"{R.get('bord0Classe')} {R.get('bord0Pad')}")
    pad0 = R.get("pad0") or {}
    check("bord 0 et padding 0 : halo seul (ni dzia-bord ni liseré), mais marqué",
          pad0.get("halo") and not pad0.get("bord") and not pad0.get("lis") and pad0.get("dz") == "image", str(pad0))
    le = R.get("le") or {}
    check("input nu dans un parent bordé (composant `le`) : le liseré est peint par le PARENT",
          le.get("parentLis") and not le.get("champLis") and le.get("champ") and le.get("barre")
          and le.get("fond") == "rgb(9, 9, 9)", str(le))
    ca = R.get("carte") or {}
    check("NÉGATIF : un parent bordé qui ne SERRE pas le champ (une carte entière) n'est jamais peint",
          not ca.get("carteLis") and ca.get("champLis") and ca.get("bord"), str(ca))
    gr = R.get("grand") or {}
    check("réserve qui ferait grandir le champ : retirée (taille intacte), barre à cheval sur le bord haut",
          gr.get("largeur") == 300 and gr.get("pad") in ("", None) and gr.get("haut") == -8, str(gr))
    check("TÉMOIN : champ border-box ordinaire → réserve de padding à droite (8 + 30 + 10)",
          R.get("reserve") == "48px", str(R.get("reserve")))
    check("barre : badge « IA »", st("quick").get("badge") == "IA", str(st("quick").get("badge")))
    check("barre : emplacements VIDES modele puis micro (T9, T10)",
          st("quick").get("slots") == ["modele:0", "micro:0"], str(st("quick").get("slots")))
    dep = R.get("deplace") or {}
    check("le champ n'est PAS déplacé (même parent, même frère précédent, même rang)",
          dep.get("parent") and dep.get("prec") and dep.get("idx"), str(dep))
    idem = R.get("idem") or {}
    check("idempotent : deux passes, un seul habillage par champ",
          idem.get("nb1") == idem.get("nb2") == idem.get("marques") and (idem.get("nb1") or 0) >= 14, str(idem))
    check("<style id=dzia-style> injecté une seule fois", idem.get("styles") == 1, str(idem.get("styles")))

    # ---------- observation ----------
    ob = R.get("obs") or {}
    check("observe les ajouts : un champ ajouté après coup est marqué",
          (ob.get("tard") or {}).get("dz") == "image" and (ob.get("tard") or {}).get("barre"), str(ob))
    check("NÉGATIF : un champ ajouté sous .dz-studio-grid ne l'est pas",
          (ob.get("tardStudio") or {}).get("dz") is None, str(ob.get("tardStudio")))

    # ---------- barre : recalage, masquage, nettoyage ----------
    pos = R.get("pos") or {}
    check("barre recalée dans le coin droit du champ (4–8 px du bord droit, dedans)",
          4 <= (pos.get("droite") if pos.get("droite") is not None else -99) <= 8
          and (pos.get("haut") or -1) >= 0 and (pos.get("bas") or -1) >= 0, str(pos))
    check("champ masqué (offsetParent null) → barre masquée, puis réaffichée",
          R.get("cache") == "none" and R.get("revu") == "", f"{R.get('cache')!r} {R.get('revu')!r}")
    check("champ retiré du DOM → barre retirée", R.get("nettoye") is True, str(R.get("nettoye")))

    # ---------- pages à part ----------
    P = R.get("pages") or {}

    def pg(p, k):
        return ((P.get(p) or {}).get(k)) or {}

    for p, k, g in (("atelier", "gs", "image"), ("atelier", "da", "image"), ("atelier", "ed", "image"),
                    ("atelier", "es", "image"), ("atelier", "sa", "image"), ("materialforge", "prompt", "image"),
                    ("spritelab", "anim", "anim"), ("cardforge", "face", "image"), ("cardforge", "decor", "image"),
                    ("cardforge", "tex", "3d"), ("vectorlab", "ia", "image"), ("vectorlab", "vit", "image")):
        check(f"{p} : {k} → {g}", pg(p, k).get("dz") == g and pg(p, k).get("barre"), str(pg(p, k)))
    for p, k, nom in (("atelier", "script", "#script de l'Atelier"), ("atelier", "fountain", "fountain de l'Atelier"),
                      ("atelier", "sas", ".shot-actions (classe voisine)"), ("spritelab", "prompt", "#prompt hors Material Forge")):
        check(f"NÉGATIF : {nom} jamais marqué", pg(p, k).get("dz") is None, str(pg(p, k)))

    # ---------- le style ----------
    css = R.get("style") or ""
    check("style : @property --dzia-ang", "@property --dzia-ang" in css)
    check("style : conic-gradient avec #8b5cf6, #3b82f6, #f97316",
          "conic-gradient(" in css and all(c in css for c in ("#8b5cf6", "#3b82f6", "#f97316")))
    check("style : reflet holographique (screen) et trame",
          "screen" in css and "repeating-linear-gradient(" in css)
    regles_css = [(sel.strip(), corps) for sel, corps in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]
    run = [s for s, c in regles_css if "running" in c]
    check("animation seulement au :focus-within (toute règle « running » est au :focus-within)",
          bool(run) and all(":focus-within" in s for s in run), str(run))
    hors_media = re.sub(r"@media[^{]*\{.*?\}\s*\}", "", css, flags=re.S)
    base = [c for s, c in re.findall(r"([^{}]+)\{([^{}]*)\}", hors_media)
            if s.strip().startswith(".dzia-lis") and ":focus" not in s and "animation" in c]
    check("au repos : animations en pause (variante B)", bool(base) and all("paused" in c for c in base), str(base)[:300])
    m = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\}\s*\}", css, re.S)
    check("reduced-motion : @media qui coupe toute animation (animation:none)",
          bool(m) and "animation:none" in m.group(1).replace(" ", "") and ".dzia-lis" in m.group(1), str(m and m.group(1))[:300])
    check("barre absolue et sans capture des clics (le champ reste cliquable)",
          re.search(r"\.dzia-barre\{[^}]*position:absolute", css) is not None
          and re.search(r"\.dzia-barre\{[^}]*pointer-events:none", css) is not None)
    check("le texte garde son contraste : aucune règle ne change color du champ",
          not any(re.match(r"\.dzia-(champ|lis|bord|halo)", s) and re.search(r"(^|;)\s*color:", c) for s, c in regles_css))

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())


def test_champ_ia():
    assert main() == 0
