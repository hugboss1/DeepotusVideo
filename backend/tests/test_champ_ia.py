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

T9 (27/09) — PASTILLE DE MODÈLE, miroir du sélecteur de la vue : chaque
règle porte un adaptateur `modele` ; le harnais simule le select CUSTOM du
bundle (`re` : bouton [data-dzselect] qui ouvre une liste de boutons au rendu
suivant), un <select> natif (valeur + `change` natif), les cartes de modèle du
Son & VFX, et un faux `fetch` (routes de modèles, `/api/cost/estimate`) qui
ESPIONNE : aucun appel de génération. Les modèles sans clé sont grisés avec
« clé X absente » ; les vues sans choix sont en lecture seule « choisi par la
vue ». Le registre des modèles d'image de la couche est confronté à
`routes.list_image_models` et à `pricing._IMAGE_MODELS` (AST, sans import).

Un processus, `check`, `=== N passed, M failed ===`, code de sortie.
"""
import ast
import json
import warnings
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
  addEventListener(t, f, c) { (this._ev || (this._ev = [])).push({ t, f, c: !!(c === true || (c && c.capture)) }); }
  removeEventListener(t, f) { this._ev = (this._ev || []).filter(x => !(x.t === t && x.f === f)); }
  dispatchEvent(ev) {                    // capture (document → parent), cible, bouillonnement
    if (!ev.target) ev.target = this;
    const ch = []; let n = this.parentNode; while (n) { ch.push(n); n = n.parentNode; }
    const appel = (nd, cap) => { for (const x of (nd._ev || []).slice()) if (x.t === ev.type && (cap === null || x.c === cap)) x.f.call(nd, ev); };
    for (let i = ch.length - 1; i >= 0; i--) appel(ch[i], true);
    appel(this, null);
    if (ev.bubbles) for (const nd of ch) { if (ev._stop) break; appel(nd, false); }
    return !ev.defaultPrevented;
  }
  click() { this.dispatchEvent(new Event("click", { bubbles: true })); }
}
class Event { constructor(t, o) { this.type = t; this.bubbles = !!(o && o.bubbles); this.target = null; this.defaultPrevented = false; }
  preventDefault() { this.defaultPrevented = true; } stopPropagation() { this._stop = true; } }
global.Event = Event;
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
  get options() { return this.children.filter(c => c.tagName === "OPTION"); }
  get text() { return this.textContent; }
  get disabled() { return this.hasAttribute("disabled"); }
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
  get offsetWidth() { return ((this._rect || {}).width || 0) + (this._grandit && this.style.paddingRight ? 14 : 0)
    + (this._granditBord && this.classList.contains("dzia-bord") ? 2 : 0); }
  get offsetHeight() { return (this._rect || {}).height || 0; }
  get clientHeight() { return this.offsetHeight; }
  get offsetParent() { return this._cache ? null : (this.parentNode || null); }
  focus() { document.activeElement = this; } blur() {}
  setSelectionRange(a, b) { this.selectionStart = a; this.selectionEnd = b; }
}
class Texte extends Noeud { constructor(d) { super(3); this.data = d; } }
class Doc extends Noeud {
  constructor() { super(9); }
  createElement(t) { const e = new Element(t); e._rect = { left: 0, top: 0, width: 20, height: 16 }; return e; }
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
const RO_LOG = [];
class MO { constructor(cb) { this.cb = cb; this.file = []; this.cible = null; this.opts = null; OBS.push(this); }
  observe(c, o) { this.cible = c; this.opts = o || null; } disconnect() { this.cible = null; }
  _vider() { const f = this.file; this.file = []; if (f.length) this.cb(f, this); } }
/* faux fetch ESPION : routes de modèles simulées, estimation de coût, rien d'autre */
const APPELS = [];
const VIDEO = { default: "seedance-2.5", models: [
  { id: "seedance-v1-pro", label: "Seedance 1.0 Pro", provider: "fal", available: true, usd_per_s: { "720p": 0.054, "1080p": 0.124 } },
  { id: "seedance-2", label: "Seedance 2.0", provider: "fal", available: true, usd_per_s: { "720p": 0.3034, "1080p": 0.682 } },
  { id: "seedance-2.5", label: "Seedance 2.5", provider: "fal", available: true, usd_per_s: { "480p": 0.2205, "720p": 0.473 } },
  { id: "veo-3", label: "Veo 3 (Google)", provider: "google", available: false, usd_per_s: { "*": 0.4 } } ] };
const IMG = { configured: "", default: "flux", models: [
  { id: "flux", label: "FLUX schnell", provider: "fal" }, { id: "nano-banana", label: "Nano Banana (Gemini)", provider: "fal" },
  { id: "nano-banana-pro", label: "Nano Banana Pro (Gemini 3)", provider: "fal" }, { id: "gpt-image-2-fal", label: "GPT Image 2 (via fal)", provider: "fal" },
  { id: "gpt-image-2.5-flare-fal", label: "GPT Image 2.5 Flare (via fal)", provider: "fal" },
  { id: "gpt-image-2.5-sunburst-fal", label: "GPT Image 2.5 Sunburst (via fal)", provider: "fal" } ] };
const MUS = { enabled: true, default: "lyria3", models: [
  { id: "lyria3", label: "Lyria 3 (Google)", usd: 0.1 }, { id: "stable-audio-25", label: "Stable Audio 2.5", usd: 0.06 },
  { id: "minimax-music-26", label: "MiniMax Music 2.6", usd: 0.14 } ] };
const PRIX = { "flux": 0.003, "nano-banana": 0.039, "gpt-image-2.5-flare-fal": 0.053, "gpt-image-2": 0.21 };
const REP = { "/api/video-models": () => VIDEO, "/api/image-models": () => IMG, "/api/music-models": () => MUS,
  "/api/atelier/settings": () => ({ settings: { image_provider: "nano-banana" } }) };
function reponse(j) { return { ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(j))) }; }
function fetchEspion(url, o) {
  const m = (o && o.method) || "GET"; APPELS.push([m, String(url), (o && o.body) || null]);
  if (url === "/api/cost/estimate" && m === "POST") {
    const b = JSON.parse(o.body); return Promise.resolve(reponse({ breakdown: (b.ops || []).map(x => ({ usd: PRIX[x.model] != null ? PRIX[x.model] : 0.02 })) }));
  }
  if (DICT[url] && m === "POST") {
    const [st, j] = DICT[url](o && o.body);
    return Promise.resolve({ ok: st < 300, status: st, json: () => Promise.resolve(JSON.parse(JSON.stringify(j))) });
  }
  const f = REP[url]; return Promise.resolve(f ? reponse(f()) : { ok: false, status: 404, json: () => Promise.resolve({}) });
}
/* T10 : faux services de la dictée — rien ne part vers un fournisseur */
const DICT = {};                           // url → (corps) → [statut, json]
const DLG = [];                            // dialogues demandés
const SETTER = [];                         // valeurs posées par le setter du PROTOTYPE (React)
function protoValeur() {
  const p = {}; Object.defineProperty(p, "value", { configurable: true, get() { return this._v; },
    set(v) { SETTER.push([this.tagName, v]); this.value = v; } }); return { prototype: p };
}
const SRI = [];
class FauxSR { constructor() { SRI.push(this); this.started = 0; this.stopped = 0; this.aborted = 0; }
  start() { this.started++; } stop() { this.stopped++; } abort() { this.aborted++; } }
function resultat(liste, idx) {
  return { resultIndex: idx || 0, results: liste.map(([t, fin]) => { const r = [{ transcript: t }]; r.isFinal = fin; return r; }) };
}
const TRACKS = { stops: 0 };
const REC = { inst: [], gum: [], gumMode: "ok", taille: 1234 };
const NAV = { mediaDevices: { getUserMedia(c) {
  REC.gum.push(c);
  if (REC.gumMode === "refus") return Promise.reject(Object.assign(new Error("Permission denied"), { name: "NotAllowedError" }));
  return Promise.resolve({ getTracks: () => [{ stop() { TRACKS.stops++; } }] });
} } };
class FauxBlob { constructor(parts, o) { this.parts = parts || []; this.type = (o && o.type) || "";
  this.size = this.parts.reduce((s, p) => s + (typeof p === "number" ? p : (p && p.size) || 0), 0); } }
class FauxMR { constructor(flux, o) { this.flux = flux; this.o = o || null; this.state = "inactive"; REC.inst.push(this); }
  static isTypeSupported(t) { return t === "audio/webm;codecs=opus"; }
  start(ms) { this.state = "recording"; this.tranche = ms; }
  stop() { this.state = "inactive"; setTimeout(() => {
    if (this.ondataavailable) this.ondataavailable({ data: new FauxBlob(REC.taille ? [REC.taille] : [], { type: "audio/webm" }) });
    if (this.onstop) this.onstop(); }, 5); } }
class FauxFD { constructor() { this.e = []; } append(k, v, n) { this.e.push([k, v, n]); } }
const LS_ = {}; const localStorage = { getItem: k => (k in LS_ ? LS_[k] : null), setItem: (k, v) => { LS_[k] = String(v); }, removeItem: k => { delete LS_[k]; } };
const window = {
  document, location: { pathname: "/" }, fetch: fetchEspion, localStorage, Event, innerWidth: 1400, innerHeight: 900,
  getComputedStyle(el) { const o = Object.assign({}, DEFAUT_CS, el._cs || {}); o.getPropertyValue = k => o[k] || ""; return o; },
  matchMedia(q) { return { matches: /reduce/.test(q) ? REDUIT : false, addEventListener() {}, addListener() {} }; },
  MutationObserver: MO,
  ResizeObserver: class { observe(t) { RO_LOG.push(["o", t]); } unobserve(t) { RO_LOG.push(["u", t]); } disconnect() {} },
  addEventListener(t, f, c) { Noeud.prototype.addEventListener.call(this, t, f, c); }, removeEventListener() {},
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
global.fetch = fetchEspion; global.localStorage = localStorage;

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
/* le select CUSTOM du bundle (`re`) : bouton [data-dzselect] > span ; la liste
   (boutons > span) n'arrive qu'au rendu SUIVANT, comme sous React */
function fauxRe(parent, options, valeur, onChange) {
  const racine = el("div", {}, parent), btn = el("button", { "data-dzselect": "1" }, racine), sp = el("span", {}, btn);
  const lab = v => (options.find(o => o.value === v) || {}).label || "—";
  sp.textContent = lab(valeur); let liste = null; const o = { racine, btn, sp, clics: 0 };
  btn.addEventListener("click", () => { o.clics++; setTimeout(() => {
    if (liste) { racine.removeChild(liste); liste = null; return; }
    liste = el("div", {}, racine);
    options.forEach(op => { const b = el("button", {}, liste); el("span", {}, b).textContent = op.label;
      b.addEventListener("click", () => { valeur = op.value; sp.textContent = lab(valeur); onChange(op.value); racine.removeChild(liste); liste = null; }); });
  }, 5); });
  Object.defineProperty(o, "valeur", { get: () => valeur });
  o.poser = v => { valeur = v; sp.textContent = lab(v); };
  return o;
}
function lblVue(m) {                      // la formule de DzVideoModelSel (bundle)
  const rr = m.usd_per_s || {}; let v = rr["1080p"] != null ? rr["1080p"] : rr["*"];
  if (v == null) for (const k in rr) { const n = Number(rr[k]); if (isFinite(n) && (v == null || n > v)) v = n; }
  const px = v != null ? " · $" + (Number(v) >= .1 ? Number(v).toFixed(2) : Number(v).toFixed(3)) + "/s" : "";
  return m.label + px + (m.available ? "" : " · clé manquante");
}
function pastille(e) { const b = e && e.nextSibling; return b && b.querySelector ? b.querySelector(".dzia-modele") : null; }
function vuP(e) { const p = pastille(e); return p ? { tag: p.tagName, txt: p.textContent, title: p.getAttribute("title"), dis: p.getAttribute("aria-disabled"),
  id: p.getAttribute("data-dzia-id"), mini: p.classList.contains("dzia-mini") } : null; }
function listeOuverte() { const l = body.querySelectorAll(".dzia-liste"); return l.length ? l[l.length - 1] : null; }
function vuListe() { const l = listeOuverte(); return l ? l.querySelectorAll(".dzia-opt").map(o => ({ id: o.getAttribute("data-id"), txt: o.textContent,
  title: o.getAttribute("title"), dis: o.getAttribute("aria-disabled"), sel: o.getAttribute("aria-selected") })) : null; }
function opt(id) { const l = listeOuverte(); return l ? l.querySelectorAll(".dzia-opt").find(o => o.getAttribute("data-id") === id) : null; }

(async function () {
  // état vide : avant la couche, aucune API
  R.avant = typeof window.DzChampIA;
  // ÉTAT VIDE : une page vide (la couche se charge sur un body vide)
  eval(fs.readFileSync(COUCHE, "utf8"));
  const A = window.DzChampIA;
  R.api = { type: typeof A, regles: Array.isArray(A && A.regles), marquer: typeof (A && A.marquer), version: typeof (A && A.version),
    exclus: Array.isArray(A && A.exclus) };
  R.regles = (A && A.regles || []).map(r => ({ id: r.id, vue: r.vue, sel: r.sel || null, libelle: r.libelle || null, genre: r.genre, page: r.page || null,
    modele: r.modele ? { liste: r.modele.liste === undefined ? "absente" : r.modele.liste, fixe: r.modele.fixe || null, lire: typeof r.modele.lire,
      ecrire: typeof r.modele.ecrire, texte: typeof r.modele.texte } : null }));
  R.catalogue = (A && A.modeles && A.modeles.catalogueImage) || null;
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
  // revue T9 : plusieurs pastilles d'image sur UNE page → UNE seule estimation de prix (déduplication)
  R.nImgT8 = body.querySelectorAll(".dzia-modele").filter(p => ["chapitres-illus", "library-image", "templates-ia"].includes(p.getAttribute("data-dzia-modele"))).length;
  R.estT8 = APPELS.filter(a => a[1] === "/api/cost/estimate").length;

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

  // ---------- revue T8, correctif 1 : détaché puis RATTACHÉ → ré-habillé ----------
  const fR = el("input", { placeholder: "Describe an image to create… (rattaché)" }, body);
  const fRm = el("textarea", { "data-dz-ia": "sfx" }, body);                 // manuel : l'attribut survit
  A.marquer(document.body);
  R.rattAvant = etat(fR);
  body.removeChild(fR); body.removeChild(fRm); A.synchroniser();
  R.detache = { dz: fR.getAttribute("data-dz-ia"), champ: fR.classList.contains("dzia-champ"), lis: fR.classList.contains("dzia-lis"),
    st: !!fR.__dzia, pr: fR.style.paddingRight, man: fRm.getAttribute("data-dz-ia"), manSt: !!fRm.__dzia };
  body.appendChild(fR); body.appendChild(fRm); OBS.forEach(o => o._vider()); await pause(120); A.synchroniser();
  R.rattache = { r: etat(fR), m: etat(fRm), barres: [fR, fRm].map(e => body.querySelectorAll(".dzia-barre").filter(b => b.previousSibling === e).length) };

  // ---------- revue T8, correctif 2 : repeint à chaud (thème, disabled) ----------
  R.fondAvant = fSons.style.getPropertyValue("--dzia-fond");
  fSons._cs = { backgroundColor: "rgb(250, 250, 250)" }; A.synchroniser();
  R.fondApres = fSons.style.getPropertyValue("--dzia-fond");
  R.moTheme = OBS.some(o => o.cible === document.documentElement && o.opts && o.opts.attributes
    && (o.opts.attributeFilter || []).includes("data-theme") && (o.opts.attributeFilter || []).includes("class"));

  // ---------- revue T8, correctif 3 : liseré qui ferait grandir le champ → halo seul, paddings rendus ----------
  const fGb = el("input", { placeholder: "AI prompt (grandit au bord)" }, body); fGb._cs = { borderTopWidth: "0px" }; fGb._granditBord = true;
  A.marquer(document.body);
  R.granditBord = { halo: fGb.classList.contains("dzia-halo"), lis: fGb.classList.contains("dzia-lis"), bord: fGb.classList.contains("dzia-bord"),
    pt: fGb.style.paddingTop, pl: fGb.style.paddingLeft, larg: fGb.offsetWidth, dz: fGb.getAttribute("data-dz-ia") };

  // ---------- revue T8, correctif 4 : le parent n'est plus observé quand plus aucun champ n'y vit ----------
  const boite = el("div", { class: "boite" }, body);
  const fB1 = el("input", { placeholder: "AI prompt (b1)" }, boite), fB2 = el("input", { placeholder: "AI prompt (b2)" }, boite);
  A.marquer(document.body);
  const obsB = () => RO_LOG.filter(x => x[1] === boite).map(x => x[0]).join("");
  R.ro = { avant: obsB() };
  boite.removeChild(fB1); A.synchroniser(); R.ro.un = obsB();
  boite.removeChild(fB2); A.synchroniser(); R.ro.deux = obsB();

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

  // ---------- T9 : pastille de modèle, miroir du sélecteur de la vue ----------
  body.textContent = ""; window.location.pathname = "/"; if (A.modeles) if (A.modeles) A.modeles.fermer();
  const q = el("div", { class: "quick" }, body), tq = ie(q, "Prompt", "textarea");
  const vmBox = el("div", { "data-dzvmsel": "1" }, q);
  const reQ = fauxRe(vmBox, [{ value: "", label: "Défaut (seedance-2.5)" }].concat(VIDEO.models.map(m => ({ value: m.id, label: lblVue(m) }))), "",
    v => localStorage.setItem("dz_video_model", v));
  const lib = el("div", {}, body), tl = el("input", { placeholder: "Describe an image to create…" }, lib), libBox = el("div", {}, lib);
  const reL = fauxRe(libBox, IMG.models.map(m => ({ value: m.id, label: m.label })), "flux", v => localStorage.setItem("dz_image_model", v));
  const tsfx = el("input", { class: "svm-sfxprompt", type: "text" }, body);
  const son = el("div", {}, body), c1 = el("div", { class: "svm-card" }, son), tm = el("textarea", { class: "svm-musicprompt" }, c1);
  const ml = el("div", { class: "svm-modellist" }, el("div", { class: "svm-card" }, son));
  const cartes = MUS.models.map(m => { const b = el("button", { class: "svm-model" }, ml); el("span", { class: "svm-genname" }, el("div", {}, b)).textContent = m.label;
    b.addEventListener("click", () => { cartes.forEach(x => x.removeAttribute("data-sel")); b.setAttribute("data-sel", ""); }); return b; });
  cartes[2].setAttribute("data-sel", "");
  const ttpl = el("input", { placeholder: "AI prompt (mascot…)" }, body);
  A.marquer(document.body); await pause(80); A.synchroniser();
  const T = R.t9 = {};
  try {
  T.slots = etat(tq).slots;
  T.quick = vuP(tq); T.lib = vuP(tl); T.sfx = vuP(tsfx); T.mus = vuP(tm); T.tpl = vuP(ttpl);
  const pQ = pastille(tq);
  // la liste du Quick : prix comme la vue, Google sans clé grisé
  pQ && pQ.click(); T.listeQ = vuListe(); T.expQ = pQ.getAttribute("aria-expanded");
  // un modèle grisé ne s'écrit pas
  if (opt("veo-3")) opt("veo-3").click(); await pause(150);
  T.apresGris = { valeur: reQ.valeur, clics: reQ.clics, ouverte: !!listeOuverte() };
  document.dispatchEvent(Object.assign(new Event("keydown", { bubbles: true }), { key: "Escape" }));
  T.echap = !listeOuverte();
  // choisir dans la pastille → le select custom de la vue est rejoué (clic, option), la vue écrit localStorage
  pQ && pQ.click(); if (opt("seedance-v1-pro")) opt("seedance-v1-pro").click(); await pause(250);
  T.choixQ = { valeur: reQ.valeur, ls: localStorage.getItem("dz_video_model"), vue: reQ.sp.textContent, clics: reQ.clics,
    p: vuP(tq), meme: pastille(tq) === pQ, ouverte: !!listeOuverte(), resteOuverte: reQ.racine.children.length };
  // la vue change → la pastille suit (synchronisation)
  reQ.poser("seedance-2"); A.synchroniser(); T.vueQ = vuP(tq);
  // revue T9 — clavier : flèches (aria-activedescendant), Entrée (jamais une option grisée), Échap/Tab rendent le focus
  // à la pastille ; l'hôte (dialogue IA du Vectorlab) ne voit ni Échap ni Entrée tant que la liste est ouverte
  const hote = { esc: 0, ent: 0 }; q.addEventListener("keydown", ev => { if (ev.key === "Escape") hote.esc++; if (ev.key === "Enter") hote.ent++; });
  const touche = k => tq.dispatchEvent(Object.assign(new Event("keydown", { bubbles: true }), { key: k }));
  touche("Escape"); T.hoteTemoin = hote.esc;
  const actif = () => { const l = listeOuverte(), id = l && l.getAttribute("aria-activedescendant");
    const o = id && l.querySelectorAll(".dzia-opt").find(x => x.getAttribute("id") === id); return o ? o.getAttribute("data-id") : null; };
  pQ.click(); await pause(5);
  T.clav = { bouton: pQ.tagName === "BUTTON" && pQ.getAttribute("tabindex") !== "-1", a0: actif(), pDesc: !!pQ.getAttribute("aria-activedescendant") };
  touche("ArrowDown"); T.clav.a1 = actif();
  touche("ArrowDown"); T.clav.a2 = actif();
  touche("Enter"); await pause(60); T.clav.grise = { valeur: reQ.valeur, ouverte: !!listeOuverte(), clics: reQ.clics };
  touche("ArrowUp"); T.clav.a3 = actif();
  touche("Enter"); await pause(250);
  T.clav.choix = { valeur: reQ.valeur, ouverte: !!listeOuverte(), focus: document.activeElement === pQ, txt: vuP(tq).txt };
  document.activeElement = tq; pQ.click(); await pause(5); touche("Tab");
  T.clav.tab = { ouverte: !!listeOuverte(), focus: document.activeElement === pQ };
  document.activeElement = tq; pQ.click(); await pause(5); touche("Escape");
  T.clav.esc = { ouverte: !!listeOuverte(), focus: document.activeElement === pQ };
  T.clav.hote = { esc: hote.esc, ent: hote.ent };
  // Library : select custom d'image, prix par image, OpenAI sans clé grisé
  (pastille(tl) || {click(){}}).click(); T.listeL = vuListe();
  if (opt("nano-banana")) opt("nano-banana").click(); await pause(250);
  T.choixL = { valeur: reL.valeur, ls: localStorage.getItem("dz_image_model"), p: vuP(tl) };
  A.synchroniser(); T.tpl2 = vuP(ttpl);                     // Templates lit le modèle global : suit
  // fixe : grisée, ne s'ouvre pas
  (pastille(tsfx) || {click(){}}).click(); T.sfxOuvre = !!listeOuverte();
  // Son & VFX : cartes
  (pastille(tm) || {click(){}}).click(); T.listeM = vuListe();
  if (opt("stable-audio-25")) opt("stable-audio-25").click(); await pause(60);
  T.choixM = { sel: cartes.map(c => c.hasAttribute("data-sel")), p: vuP(tm) };
  // E-12 : tout bouton de la barre et de la liste porte un title
  (pastille(tq) || {click(){}}).click(); await pause(10);
  T.sansTitre = body.querySelectorAll(".dzia-barre button, .dzia-liste button").filter(b => !(b.getAttribute("title") || "").trim()).length;
  T.nBoutons = body.querySelectorAll(".dzia-barre button, .dzia-liste button").length;
  if (A.modeles) A.modeles.fermer();
  // revue T9 : liste ouverte → champ détaché → synchronisation → la liste disparaît
  (pastille(tl) || {click(){}}).click(); T.detListe = { avant: !!listeOuverte() };
  body.removeChild(lib); A.synchroniser(); T.detListe.apres = !!listeOuverte();

  // pages à part : <select> natif (Material Forge), lecture seule (Atelier, Spritelab), champ étroit (Vitrail)
  body.textContent = ""; window.location.pathname = "/materialforge/";
  const sel = el("select", { id: "model" }, body); let nChange = 0, bulle = null;
  ["flux", "nano-banana", "nano-banana-pro", "gpt-image-2.5-flare-fal", "gpt-image-2.5-sunburst-fal"].forEach(id => {
    const o = el("option", { value: id }, sel); o.value = id; o.textContent = (IMG.models.find(m => m.id === id) || {}).label; });
  sel.value = "flux"; sel.addEventListener("change", ev => { nChange++; bulle = ev.bubbles; });
  const tmf = el("textarea", { id: "prompt" }, body);
  A.marquer(document.body); await pause(40); A.synchroniser();
  T.mf = vuP(tmf); (pastille(tmf) || {click(){}}).click(); T.listeMF = vuListe();
  if (opt("gpt-image-2.5-flare-fal")) opt("gpt-image-2.5-flare-fal").click(); await pause(40);
  T.choixMF = { valeur: sel.value, nChange, bulle, p: vuP(tmf) };
  sel.value = "nano-banana-pro"; sel.dispatchEvent(new Event("change", { bubbles: true })); await pause(30);
  T.vueMF = vuP(tmf);
  // revue T9 : ecrire natif d'un id ABSENT du <select> → false, aucun change
  { const rMF = (A.regles || []).find(r => r.id === "materialforge"), c0 = nChange, v0 = sel.value;
    const res = rMF && rMF.modele && rMF.modele.ecrire ? await rMF.modele.ecrire(tmf, "id-absent") : null;
    T.ecrireAbsent = { res, dChange: nChange - c0, meme: sel.value === v0 }; }
  body.textContent = ""; window.location.pathname = "/atelier/";
  const tat = el("input", { id: "globalStyle" }, body); A.marquer(document.body); await pause(60); A.synchroniser(); T.atelier = vuP(tat);
  body.textContent = ""; window.location.pathname = "/spritelab/";
  const tsp = el("textarea", { id: "animPrompt" }, body); A.marquer(document.body); await pause(30); A.synchroniser(); T.sprite = vuP(tsp);
  body.textContent = ""; window.location.pathname = "/vectorlab/";
  const tvit = el("input", { id: "vitIaPrompt", type: "text" }, body, { left: 10, top: 10, width: 88, height: 30 });
  A.marquer(document.body); await pause(30); A.synchroniser(); T.vitrail = vuP(tvit);
  // revue T9 : <select> natif DÉSACTIVÉ (Vectorlab sans clé : <option>—</option>) → pastille figée, title explicite
  const selV = el("select", { id: "iaModele", disabled: "" }, body), ov = el("option", {}, selV); ov.value = "—"; ov.textContent = "—";
  const tia = el("textarea", { id: "iaTexte" }, body);
  A.marquer(document.body); await pause(30); A.synchroniser();
  T.vlSans = vuP(tia); (pastille(tia) || {click(){}}).click(); T.vlSansOuvre = !!listeOuverte();
  { const rV = (A.regles || []).find(r => r.id === "vectorlab-ia"); T.vlSansEcrit = rV && rV.modele.ecrire ? await rV.modele.ecrire(tia, "—") : null; }
  // témoin : le même sélecteur ACTIF avec un vrai modèle → pilotable
  selV.removeAttribute("disabled"); selV.removeChild(ov);
  const ov2 = el("option", { value: "m1" }, selV); ov2.value = "m1"; ov2.textContent = "Modèle 1"; selV.value = "m1";
  A.synchroniser(); T.vlAvec = vuP(tia);
  // <select> natif VIDE (Cardforge sans modèle) → figée
  body.textContent = ""; window.location.pathname = "/cardforge/";
  el("select", { id: "cf-face-model" }, body); const tcf = el("textarea", { id: "cf-face-prompt" }, body);
  A.marquer(document.body); await pause(30); A.synchroniser(); T.cfVide = vuP(tcf);

  // SANS CLÉ : tout grisé, la raison dit la clé qui manque
  VIDEO.models.forEach(m => { m.available = false; }); IMG.models = []; IMG.default = ""; MUS.enabled = false;
  body.textContent = ""; window.location.pathname = "/";
  const q2 = el("div", {}, body), tq2 = ie(q2, "Prompt", "textarea"), vm2 = el("div", { "data-dzvmsel": "1" }, q2);
  fauxRe(vm2, [{ value: "", label: "Défaut (seedance-2.5)" }], "", () => {});
  const tl2 = el("input", { placeholder: "Describe an image to create…" }, body);
  A.marquer(document.body);
  await Promise.all(["video", "image", "musique"].map(l => A.modeles && A.modeles.charger(l, true))); A.synchroniser();
  T.sansCle = { quick: vuP(tq2), lib: vuP(tl2) };
  const pQ2 = pastille(tq2); pQ2 && pQ2.click(); T.sansCle.ouvre = !!listeOuverte();
  } catch (e) { R.t9err = String(e && e.stack || e).slice(0, 500); }
  T.appels = APPELS.map(a => [a[0], a[1], a[1] === "/api/cost/estimate" ? JSON.parse(a[2] || "{}") : null]);

  // ---------- T10 : DICTÉE (faux SpeechRecognition, faux MediaRecorder, faux fetch : aucune transcription réelle) ----------
  const D10 = R.t10 = {};
  try {
  if (A.modeles) A.modeles.fermer();
  body.textContent = ""; window.location.pathname = "/"; html.lang = "";
  const n0 = APPELS.length;
  const dicts = () => APPELS.slice(n0).filter(a => /^\/api\/dictation/.test(a[1]));
  const fd = a => a && a[2] && a[2].e ? a[2].e.map(x => [x[0], x[1] && x[1].size != null ? "blob:" + x[1].size + ":" + x[1].type : x[1], x[2] || null]) : null;
  const boite10 = el("div", {}, body);
  const ta = el("textarea", { placeholder: "Describe an image to create… (dictée)" }, boite10);
  let nInput = 0; boite10.addEventListener("input", ev => { if (ev.target === ta) nInput++; });
  const hote10 = { esc: 0 }; boite10.addEventListener("keydown", ev => { if (ev.key === "Escape") hote10.esc++; });
  ta.dispatchEvent(Object.assign(new Event("keydown", { bubbles: true }), { key: "Escape" })); D10.hoteTemoin = hote10.esc;
  // ÉTAT VIDE : ni reconnaissance, ni micro → bouton grisé, titré, sans exception au clic
  A.marquer(document.body); await pause(30); A.synchroniser();
  const micro = () => { const b = ta.nextSibling; return b && b.querySelector ? b.querySelector(".dzia-micro") : null; };
  const vuM = () => { const m = micro(); return m ? { tag: m.tagName, txt: m.textContent, title: m.getAttribute("title"), dis: m.getAttribute("aria-disabled"),
    etat: m.getAttribute("data-dzia-etat"), ecoute: ta.nextSibling.classList.contains("dzia-ecoute") } : null; };
  const note = () => { const n = body.querySelector(".dzia-note"); return n ? n.textContent : ""; };
  D10.slots = etat(ta).slots; D10.rien = vuM(); const m0 = micro();
  D10.clavier = m0 ? { tag: m0.tagName, type: m0.getAttribute("type"), tab: m0.getAttribute("tabindex") } : null;
  m0 && m0.click(); await pause(20); D10.rienNote = note(); D10.rienApp = dicts().length;
  // voie 2 seule (micro, pas de reconnaissance) : titre de la voie 2
  window.navigator = NAV; window.MediaRecorder = FauxMR; window.Blob = FauxBlob; window.FormData = FauxFD;
  window.HTMLTextAreaElement = protoValeur(); window.HTMLInputElement = protoValeur();
  A.synchroniser(); D10.v2seule = vuM();
  // voie 1 : faux SpeechRecognition
  window.webkitSpeechRecognition = FauxSR; A.synchroniser(); D10.v1 = vuM();
  ta.value = "Bonjour monde"; ta.selectionStart = ta.selectionEnd = 7;
  micro().click(); await pause(20);
  const s1 = SRI[SRI.length - 1];
  D10.sr = s1 ? { n: SRI.length, lang: s1.lang, interim: s1.interimResults, cont: s1.continuous, start: s1.started } : null;
  D10.ecoute = vuM(); D10.meme = micro() === m0; D10.noteEcoute = note();
  s1 && s1.onresult && s1.onresult(resultat([["jo", false]])); await pause(5);
  D10.interim = { val: ta.value, note: note(), set: SETTER.length };
  s1 && s1.onresult && s1.onresult(resultat([["joli", true]])); await pause(5);
  D10.final = { val: ta.value, set: SETTER.slice(-1)[0] || null, nInput, sel: [ta.selectionStart, ta.selectionEnd] };
  ta.dispatchEvent(Object.assign(new Event("keydown", { bubbles: true }), { key: "Escape" }));
  D10.echap = { stop: s1 ? s1.stopped : -1, hote: hote10.esc };
  s1 && s1.onend && s1.onend(); await pause(5);
  D10.apresFin = vuM();
  // 2e dictée : lang du document, clic = arrêt, insertion en fin après ponctuation
  html.lang = "en-US"; ta.value = "Fin."; ta.selectionStart = ta.selectionEnd = 4;
  micro().click(); await pause(10);
  const s2 = SRI[SRI.length - 1];
  D10.lang2 = s2 && s2 !== s1 ? s2.lang : null;
  s2.onresult(resultat([["ignoré", true], ["suite", true]], 1)); await pause(5);
  D10.fin2 = ta.value;
  micro().click(); await pause(5); D10.clicStop = s2.stopped; s2.onend(); await pause(5);
  // voie 1 → erreur network → voie 2 enregistre aussitôt
  micro().click(); await pause(10);
  const s3 = SRI[SRI.length - 1];
  s3.onerror({ error: "network" }); s3.onend && s3.onend(); await pause(30);
  D10.bascule = { gum: REC.gum.length, rec: REC.inst.length, mime: REC.inst.length ? (REC.inst[REC.inst.length - 1].o || {}).mimeType : null,
    etat: vuM(), note: note(), abort: s3.aborted };
  // arrêt → estimation → dialogue MAISON (ni __dzDialogue, ni VL.dialogue) → Non
  ta.value = "Avant"; ta.selectionStart = ta.selectionEnd = 5;
  DICT["/api/dictation/estimate"] = () => [200, { duration_s: 11.6, provider: "elevenlabs", label: "ElevenLabs Scribe", usd: 0.0013, available: true, eta_s: 2 }];
  DICT["/api/dictation"] = () => [200, { text: "bonjour tout le monde", usd: 0.0013, provider: "elevenlabs" }];
  micro().click(); await pause(60);
  const dlg = body.querySelector(".dzia-dlg");
  D10.maison = dlg ? { txt: dlg.textContent, boutons: dlg.querySelectorAll("button").map(b => [b.getAttribute("data-role"), b.textContent, b.getAttribute("title")]) } : null;
  D10.estimeAppels = dicts().map(a => [a[0], a[1], fd(a)]);
  D10.pistes = TRACKS.stops;
  D10.enAccord = vuM();
  const bNon = dlg ? dlg.querySelectorAll("button").find(b => b.getAttribute("data-role") === "non") : null;
  bNon && bNon.click(); await pause(40);
  D10.non = { appels: dicts().map(a => a[1]), val: ta.value, note: note(), etat: vuM(), dlg: !!body.querySelector(".dzia-dlg") };
  // __dzDialogue présent (SPA et pages à part) → Oui → POST /api/dictation avec max_usd = le montant affiché
  window.__dzDialogue = { confirmer: (m, o) => { DLG.push(["dz", m, o]); return Promise.resolve(true); } };
  const nA = dicts().length;
  micro().click(); await pause(20); micro().click(); await pause(80);
  D10.oui = { appels: dicts().slice(nA).map(a => [a[0], a[1], fd(a)]), dlg: DLG.slice(-1)[0] || null, val: ta.value, note: note(), etat: vuM(),
    sel: [ta.selectionStart, ta.selectionEnd] };
  // VL.dialogue (Vectorlab) : utilisé à défaut de __dzDialogue ; Non → rien
  delete window.__dzDialogue;
  window.VL = { dialogue: { confirmer: (m, o) => { DLG.push(["vl", m, o]); return Promise.resolve(false); } } };
  const nB = dicts().length;
  micro().click(); await pause(20); micro().click(); await pause(60);
  D10.vl = { dlg: DLG.slice(-1)[0] || null, appels: dicts().slice(nB).map(a => a[1]) };
  delete window.VL;
  // 402 du serveur : message lisible, champ intact
  window.__dzDialogue = { confirmer: (m, o) => { DLG.push(["dz", m, o]); return Promise.resolve(true); } };
  DICT["/api/dictation"] = () => [402, { detail: "Coût recalculé 0.0020 $ au-delà du plafond accepté 0.0013 $ : rien n'a été envoyé." }];
  const v402 = ta.value;
  micro().click(); await pause(20); micro().click(); await pause(80);
  D10.e402 = { val: ta.value === v402, note: note(), etat: vuM() };
  // prise vide : rien n'est envoyé
  REC.taille = 0; const nV = dicts().length;
  micro().click(); await pause(20); micro().click(); await pause(60);
  D10.vide = { appels: dicts().length - nV, note: note(), etat: vuM() }; REC.taille = 1234;
  // getUserMedia refusé : note lisible, pas d'exception
  REC.gumMode = "refus"; const nG = dicts().length;
  micro().click(); await pause(40);
  D10.refus = { note: note(), etat: vuM(), appels: dicts().length - nG }; REC.gumMode = "ok";
  // champ retiré pendant la prise : enregistreur arrêté, pistes coupées, rien n'est envoyé
  const pistesAvant = TRACKS.stops, nR = dicts().length;
  micro().click(); await pause(20);
  boite10.removeChild(ta); A.synchroniser(); await pause(60);
  D10.retire = { appels: dicts().length - nR, pistes: TRACKS.stops - pistesAvant };
  boite10.appendChild(ta); OBS.forEach(o => o._vider()); await pause(120); A.synchroniser();
  // available:false : aucun dialogue, aucune transcription, micro grisé (voie 2) avec la raison
  DICT["/api/dictation/estimate"] = () => [200, { duration_s: 5, provider: null, usd: 0, available: false, reason: "Aucune clé de transcription (ELEVENLABS_API_KEY ou OPENAI_API_KEY)." }];
  const nI = dicts().length, nD = DLG.length;
  micro().click(); await pause(20); micro().click(); await pause(60);
  D10.indispo = { appels: dicts().slice(nI).map(a => a[1]), dlg: DLG.length - nD, etat: vuM(), note: note() };
  const gA = REC.gum.length; micro().click(); await pause(20); D10.indispoClic = { dg: REC.gum.length - gA, etat: vuM() };
  // E-12 : tout bouton de la barre porte un title
  D10.sansTitre = body.querySelectorAll(".dzia-barre button").filter(b => !(b.getAttribute("title") || "").trim()).length;
  } catch (e) { R.t10err = String(e && e.stack || e).slice(0, 600); }
  R.t10.tout = APPELS.slice(0).filter(a => /^\/api\/dictation/.test(a[1])).map(a => a[1]);

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
    check("barre : emplacement modele occupé par la pastille (T9), micro occupé par le bouton de dictée (T10)",
          st("quick").get("slots") == ["modele:1", "micro:1"], str(st("quick").get("slots")))
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

    # ---------- correctifs de la revue T8 ----------
    ra, de, rt = R.get("rattAvant") or {}, R.get("detache") or {}, R.get("rattache") or {}
    check("TÉMOIN : le champ à rattacher était marqué avec sa barre", ra.get("dz") == "image" and ra.get("barre"), str(ra))
    check("détaché → habillage défait (ni __dzia, ni classes, ni marque de règle, ni réserve de padding)",
          de.get("dz") is None and not de.get("champ") and not de.get("lis") and not de.get("st") and de.get("pr") in ("", None), str(de))
    check("détaché : un data-dz-ia MANUEL survit (l'intention reste)", de.get("man") == "sfx" and not de.get("manSt"), str(de))
    rr, rm = rt.get("r") or {}, rt.get("m") or {}
    check("rattaché → re-marqué, barre revenue (une seule)",
          rr.get("dz") == "image" and rr.get("barre") and rr.get("classe") and (rt.get("barres") or [0])[0] == 1, str(rt))
    check("rattaché : les emplacements de la barre reviennent (badge, modele, micro)",
          rr.get("badge") == "IA" and [x.split(":")[0] for x in (rr.get("slots") or [])] == ["modele", "micro"], str(rr))
    check("rattaché : le manuel aussi (genre gardé, barre)", rm.get("dz") == "sfx" and rm.get("barre"), str(rm))
    check("TÉMOIN : fond peint au marquage", R.get("fondAvant") == "rgb(20, 22, 28)", str(R.get("fondAvant")))
    check("fond du champ changé à chaud (thème clair) → --dzia-fond repeint à la synchronisation",
          R.get("fondApres") == "rgb(250, 250, 250)", str(R.get("fondApres")))
    check("data-theme / class de <html> observés (bascule de thème du Cardforge)", R.get("moTheme") is True, str(R.get("moTheme")))
    gb = R.get("granditBord") or {}
    check("liseré qui ferait grandir le champ → halo seul, sans dzia-lis ni dzia-bord, paddings inline rendus, taille intacte",
          gb.get("halo") and not gb.get("lis") and not gb.get("bord") and gb.get("pt") in ("", None) and gb.get("pl") in ("", None)
          and gb.get("larg") == 300 and gb.get("dz") == "image", str(gb))
    ro = R.get("ro") or {}
    check("TÉMOIN : le parent des champs est observé (ResizeObserver)", "o" in (ro.get("avant") or ""), str(ro))
    check("un champ retiré sur deux : le parent reste observé (pas d'unobserve)", "u" not in (ro.get("un") or "x"), str(ro))
    check("dernier champ retiré : unobserve du parent", (ro.get("deux") or "").endswith("u"), str(ro))

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

    # ---------- T9 : pastille de modèle ----------
    PILOTES = {"quick-prompt", "chapitres-illus", "library-image", "son-paroles", "son-musique", "atelier-da",
               "materialforge", "cardforge-face", "cardforge-decor", "cardforge-texture", "vectorlab-ia"}
    FIXES = {"quick-script": "HeyGen", "quick-motion": "HeyGen", "son-sfx": "ElevenLabs", "montage-sons": "ElevenLabs",
             "vectorlab-vitrail": "Réglages"}
    sans_mod = [r.get("id") for r in regles if not r.get("modele")]
    check("chaque règle porte un adaptateur modele", bool(regles) and not sans_mod, str(sans_mod))
    mauvais = [r.get("id") for r in regles if r.get("modele") and not (
        r["modele"].get("liste") in ("video", "image", "musique", None)
        and (r["modele"].get("fixe") or r["modele"].get("lire") == "function" or r["modele"].get("texte") == "function"))]
    check("adaptateur : liste video|image|musique|null, et fixe ou lire(champ)", not mauvais, str(mauvais))
    pil = {r.get("id") for r in regles if (r.get("modele") or {}).get("ecrire") == "function"}
    check("pilotables (ecrire) = les vues dont le sélecteur se pilote sans patch (mesuré à l'écran)", pil == PILOTES,
          str(sorted(pil ^ PILOTES)))
    fx = {r.get("id"): (r.get("modele") or {}).get("fixe") or "" for r in regles}
    check("vues sans choix : libellé fixe du modèle réellement utilisé",
          all(frag in fx.get(k, "") for k, frag in FIXES.items()), str({k: fx.get(k) for k in FIXES}))
    check("NÉGATIF : aucune règle pilotable n'est aussi « fixe »", not any(fx.get(k) for k in PILOTES), str({k: fx.get(k) for k in PILOTES if fx.get(k)}))

    # registre des modèles d'image : pas de dérive avec routes.list_image_models et pricing._IMAGE_MODELS
    routes_src = (ROOT / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        arbre = ast.parse(routes_src)
    fn = next((n for n in ast.walk(arbre) if isinstance(n, ast.AsyncFunctionDef) and n.name == "list_image_models"), None)
    srv = {}
    for n in ast.walk(fn) if fn else []:
        if isinstance(n, ast.Dict) and all(isinstance(k, ast.Constant) for k in n.keys):
            d = {k.value: (v.value if isinstance(v, ast.Constant) else None) for k, v in zip(n.keys, n.values)}
            if d.get("id") and d.get("provider"):
                srv[d["id"]] = (d.get("label"), d["provider"])
    pr_src = (ROOT / "backend" / "app" / "services" / "pricing.py").read_text(encoding="utf-8")
    pim = {}
    for n in ast.parse(pr_src).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_IMAGE_MODELS" for t in n.targets):
            pim = ast.literal_eval(n.value)
    cat = R.get("catalogue") or []
    check("TÉMOIN : routes.list_image_models et pricing._IMAGE_MODELS lus (≥ 11 modèles)", len(srv) >= 11 and len(pim) >= 11,
          f"{len(srv)} {len(pim)}")
    cid = {c[0] for c in cat}
    check("registre de la couche = ids de list_image_models = ids de pricing._IMAGE_MODELS",
          bool(cat) and cid == set(srv) == set(pim), str(sorted(cid ^ set(srv))) + " " + str(sorted(cid ^ set(pim))))
    lab_ko = [c[0] for c in cat if (srv.get(c[0]) or ("",))[0] != c[1]]
    check("registre : libellés = ceux de list_image_models", bool(cat) and not lab_ko, str(lab_ko))
    cle_ko = [c[0] for c in cat if c[2] != {"fal": "FAL_KEY", "openai": "OPENAI_API_KEY"}.get((pim.get(c[0]) or ("", ""))[1])]
    check("registre : clé = fournisseur de facturation de pricing (fal → FAL_KEY, openai → OPENAI_API_KEY)", bool(cat) and not cle_ko, str(cle_ko))

    T = R.get("t9") or {}
    check("section T9 du harnais sans exception", not R.get("t9err"), str(R.get("t9err")))

    def tp(k):
        return T.get(k) or {}
    check("barre du Quick : badge, pastille, micro", T.get("slots") == ["modele:1", "micro:1"], str(T.get("slots")))
    q = tp("quick")
    check("pastille = un BOUTON titré, pilotable (aria-disabled=false)", q.get("tag") == "BUTTON" and q.get("dis") == "false"
          and (q.get("title") or "").startswith("Modèle : "), str(q))
    check("Quick : « Défaut (seedance-2.5) » de la vue → Seedance 2.5, prix comme la vue ($0.47/s : 720p faute de 1080p)",
          q.get("id") == "seedance-2.5" and q.get("txt") == "Seedance 2.5" and "$0.47/s" in (q.get("title") or ""), str(q))
    lq = T.get("listeQ") or []
    byq = {o.get("id"): o for o in lq}
    check("liste du Quick : les modèles de /api/video-models, aria-expanded", set(byq) == {"seedance-v1-pro", "seedance-2", "seedance-2.5", "veo-3"}
          and T.get("expQ") == "true", str(list(byq)))
    check("liste : prix au format de la vue (Seedance 1.0 Pro · $0.12/s)", "$0.12/s" in (byq.get("seedance-v1-pro") or {}).get("txt", ""),
          str(byq.get("seedance-v1-pro")))
    check("available:false (Google) → grisé, title « clé GEMINI_API_KEY absente »",
          (byq.get("veo-3") or {}).get("dis") == "true" and ((byq.get("veo-3") or {}).get("title") or "").startswith("clé GEMINI_API_KEY absente"),
          str(byq.get("veo-3")))
    check("TÉMOIN : un modèle disponible n'est pas grisé et porte un title", (byq.get("seedance-2") or {}).get("dis") is None
          and (byq.get("seedance-2") or {}).get("title"), str(byq.get("seedance-2")))
    check("modèle actuel marqué aria-selected", (byq.get("seedance-2.5") or {}).get("sel") == "true", str(byq.get("seedance-2.5")))
    ag = T.get("apresGris") or {}
    check("NÉGATIF : clic sur un modèle grisé → rien n'est écrit dans la vue (aucun clic rejoué)",
          ag.get("valeur") == "" and ag.get("clics") == 0 and ag.get("ouverte"), str(ag))
    check("Échap ferme la liste", T.get("echap") is True)
    cq = T.get("choixQ") or {}
    check("pastille → vue : le select custom est REJOUÉ (clic, option) et la vue écrit localStorage.dz_video_model",
          cq.get("valeur") == "seedance-v1-pro" and cq.get("ls") == "seedance-v1-pro" and cq.get("clics") == 1
          and (cq.get("vue") or "").startswith("Seedance 1.0 Pro"), str(cq))
    check("après le choix : pastille à jour, liste fermée, liste de la vue refermée, MÊME nœud (pas d'échange de boutons)",
          (cq.get("p") or {}).get("txt") == "Seedance 1.0 Pro" and not cq.get("ouverte") and cq.get("meme") and cq.get("resteOuverte") == 1, str(cq))
    check("vue → pastille : la vue change (Seedance 2.0) → la pastille suit", tp("vueQ").get("txt") == "Seedance 2.0", str(T.get("vueQ")))
    lb = tp("lib")
    check("Library : select custom d'image lu (FLUX schnell), prix par image via /api/cost/estimate",
          lb.get("id") == "flux" and lb.get("txt") == "FLUX schnell" and "$0.003/image" in (lb.get("title") or ""), str(lb))
    ll = {o.get("id"): o for o in (T.get("listeL") or [])}
    check("liste image = le registre COMPLET (11), pas seulement /api/image-models", len(ll) == 11, str(len(ll)))
    check("modèle d'image sans clé (absent de /api/image-models) → grisé « clé OPENAI_API_KEY absente »",
          all((ll.get(k) or {}).get("dis") == "true" and ((ll.get(k) or {}).get("title") or "").startswith("clé OPENAI_API_KEY absente")
              for k in ("gpt-image-2", "gpt-image-2.5-flare", "gpt-image-1-mini")), str(ll.get("gpt-image-2")))
    check("TÉMOIN : un modèle fal servi n'est pas grisé et affiche son prix ($0.053/image)",
          (ll.get("gpt-image-2.5-flare-fal") or {}).get("dis") is None and "$0.053/image" in (ll.get("gpt-image-2.5-flare-fal") or {}).get("txt", ""),
          str(ll.get("gpt-image-2.5-flare-fal")))
    cl = T.get("choixL") or {}
    check("Library : pastille → select de la vue → localStorage.dz_image_model", cl.get("valeur") == "nano-banana"
          and cl.get("ls") == "nano-banana" and (cl.get("p") or {}).get("txt") == "Nano Banana (Gemini)", str(cl))
    sf = tp("sfx")
    check("vue sans choix (SFX) : pastille grisée, libellé ElevenLabs SFX, title « choisi par la vue »",
          sf.get("dis") == "true" and sf.get("txt") == "ElevenLabs SFX" and "choisi par la vue" in (sf.get("title") or ""), str(sf))
    check("NÉGATIF : une pastille grisée n'ouvre aucune liste", T.get("sfxOuvre") is False, str(T.get("sfxOuvre")))
    t1, t2 = tp("tpl"), tp("tpl2")
    check("Templates (lecture seule) : le modèle d'image global, grisé « choisi par la vue », suit le choix de la Library",
          t1.get("dis") == "true" and "choisi par la vue" in (t1.get("title") or "") and t2.get("txt") == "Nano Banana (Gemini)", f"{t1} {t2}")
    mu = tp("mus")
    check("Son & VFX : la carte sélectionnée est lue (MiniMax Music 2.6, ~$0.14)", mu.get("txt") == "MiniMax Music 2.6"
          and "~$0.14" in (mu.get("title") or "") and mu.get("dis") == "false", str(mu))
    cm = T.get("choixM") or {}
    check("Son & VFX : pastille → clic sur la carte de la vue", cm.get("sel") == [False, True, False]
          and (cm.get("p") or {}).get("txt") == "Stable Audio 2.5", str(cm))
    check("E-12 : tout bouton de la barre et de la liste a un title", (T.get("nBoutons") or 0) >= 6 and T.get("sansTitre") == 0,
          f"{T.get('sansTitre')}/{T.get('nBoutons')}")
    mf, lmf = tp("mf"), {o.get("id"): o for o in (T.get("listeMF") or [])}
    check("Material Forge : <select> natif lu (FLUX schnell), pilotable", mf.get("txt") == "FLUX schnell" and mf.get("dis") == "false", str(mf))
    check("servi mais absent du <select> de la vue → grisé « absent du sélecteur de la vue »",
          (lmf.get("gpt-image-2-fal") or {}).get("dis") == "true" and "absent du sélecteur" in ((lmf.get("gpt-image-2-fal") or {}).get("title") or ""),
          str(lmf.get("gpt-image-2-fal")))
    cmf = T.get("choixMF") or {}
    check("pastille → <select> natif : valeur posée + UN événement change natif qui bouillonne",
          cmf.get("valeur") == "gpt-image-2.5-flare-fal" and cmf.get("nChange") == 1 and cmf.get("bulle") is True
          and (cmf.get("p") or {}).get("txt") == "GPT Image 2.5 Flare (via fal)", str(cmf))
    check("<select> natif changé (change) → la pastille suit", tp("vueMF").get("txt") == "Nano Banana Pro (Gemini 3)", str(T.get("vueMF")))
    at = tp("atelier")
    check("Atelier : lecture seule, le générateur de 🎨 DA (atelier_settings.image_provider)",
          at.get("txt") == "Nano Banana (Gemini)" and at.get("dis") == "true" and "DA" in (at.get("title") or ""), str(at))
    sp = tp("sprite")
    check("Spritelab : lecture seule, le modèle vidéo par défaut du serveur (Seedance 2.5)",
          sp.get("txt") == "Seedance 2.5" and sp.get("dis") == "true" and "choisi par la vue" in (sp.get("title") or ""), str(sp))
    vi = tp("vitrail")
    check("champ étroit (Vitrail, 88 px) : pastille réduite à une icône titrée (dzia-mini)",
          vi.get("mini") is True and (vi.get("title") or "").startswith("Modèle : "), str(vi))
    check("TÉMOIN : un champ large n'est pas réduit", tp("quick").get("mini") is False, str(tp("quick").get("mini")))
    sc = T.get("sansCle") or {}
    sq, sl = sc.get("quick") or {}, sc.get("lib") or {}
    check("SANS CLÉ : Quick grisé « aucun modèle », title nomme FAL_KEY et GEMINI_API_KEY",
          sq.get("dis") == "true" and sq.get("txt") == "aucun modèle" and "clé FAL_KEY absente" in (sq.get("title") or "")
          and "clé GEMINI_API_KEY absente" in (sq.get("title") or ""), str(sq))
    check("SANS CLÉ : Library grisée, title nomme FAL_KEY et OPENAI_API_KEY",
          sl.get("dis") == "true" and "clé FAL_KEY absente" in (sl.get("title") or "") and "clé OPENAI_API_KEY absente" in (sl.get("title") or ""), str(sl))
    check("SANS CLÉ : la pastille grisée n'ouvre pas de liste", sc.get("ouvre") is False, str(sc.get("ouvre")))
    ap = T.get("appels") or []
    est = [a for a in ap if a[1] == "/api/cost/estimate"]
    check("prix d'image : estimation POST (campaign, un op image par modèle du registre)",
          bool(est) and all(a[0] == "POST" and (a[2] or {}).get("kind") == "campaign" and len((a[2] or {}).get("ops") or []) == 11 for a in est), str(est[:1])[:300])
    check("TÉMOIN (revue T9) : plusieurs pastilles d'image sur la page SPA (Chapitres, Library, Templates…)",
          (R.get("nImgT8") or 0) >= 3, str(R.get("nImgT8")))
    check("déduplication : ces pastilles d'image → UNE seule estimation sur la page",
          R.get("estT8") == 1, str(R.get("estT8")))
    check("compte exact : 2 estimations sur tout le banc (la page SPA, puis la relecture forcée « sans clé »)",
          len(est) == 2, str(len(est)))
    ck = T.get("clav") or {}
    check("clavier : la pastille est un bouton focusable (pas de tabindex=-1)", ck.get("bouton") is True, str(ck))
    check("TÉMOIN : liste fermée, Échap atteint l'hôte", T.get("hoteTemoin") == 1, str(T.get("hoteTemoin")))
    check("clavier : à l'ouverture, l'option active (aria-activedescendant) est le modèle actuel",
          ck.get("a0") == "seedance-2" and ck.get("pDesc") is True, str(ck))
    check("clavier : ↓ ↓ parcourt les options (seedance-2.5 puis veo-3)", ck.get("a1") == "seedance-2.5" and ck.get("a2") == "veo-3", str(ck))
    gr9 = ck.get("grise") or {}
    check("NÉGATIF : Entrée sur une option GRISÉE → rien n'est écrit, la liste reste ouverte",
          gr9.get("valeur") == "seedance-2" and gr9.get("ouverte") is True, str(gr9))
    check("clavier : ↑ revient (seedance-2.5)", ck.get("a3") == "seedance-2.5", str(ck.get("a3")))
    ch9 = ck.get("choix") or {}
    check("clavier : Entrée choisit (la vue est rejouée), liste fermée, focus rendu à la pastille",
          ch9.get("valeur") == "seedance-2.5" and ch9.get("ouverte") is False and ch9.get("focus") is True and ch9.get("txt") == "Seedance 2.5", str(ch9))
    check("clavier : Tab ferme la liste et rend le focus à la pastille",
          (ck.get("tab") or {}).get("ouverte") is False and (ck.get("tab") or {}).get("focus") is True, str(ck.get("tab")))
    check("clavier : Échap ferme la liste et rend le focus à la pastille",
          (ck.get("esc") or {}).get("ouverte") is False and (ck.get("esc") or {}).get("focus") is True, str(ck.get("esc")))
    check("NÉGATIF : liste ouverte → ni Échap ni Entrée n'atteignent l'hôte (stopPropagation : le dialogue IA du Vectorlab reste ouvert)",
          (ck.get("hote") or {}).get("esc") == 1 and (ck.get("hote") or {}).get("ent") == 0, str(ck.get("hote")))
    dl = T.get("detListe") or {}
    check("liste ouverte → champ détaché → synchronisation : la liste disparaît (TÉMOIN : elle était ouverte)",
          dl.get("avant") is True and dl.get("apres") is False, str(dl))
    ea9 = T.get("ecrireAbsent") or {}
    check("ecrire natif d'un id ABSENT du <select> → false, aucun change, valeur intacte",
          ea9.get("res") is False and ea9.get("dChange") == 0 and ea9.get("meme") is True, str(ea9))
    vs = T.get("vlSans") or {}
    check("<select> natif DÉSACTIVÉ (Vectorlab sans clé) → pastille figée, title « désactivé »",
          vs.get("dis") == "true" and "désactivé" in (vs.get("title") or "") and T.get("vlSansOuvre") is False, f"{vs} {T.get('vlSansOuvre')}")
    check("<select> natif désactivé : ecrire refuse (false)", T.get("vlSansEcrit") is False, str(T.get("vlSansEcrit")))
    va = T.get("vlAvec") or {}
    check("TÉMOIN : le même <select> actif avec un modèle → pastille pilotable (Modèle 1)",
          va.get("dis") == "false" and va.get("txt") == "Modèle 1", str(va))
    cv = T.get("cfVide") or {}
    check("<select> natif VIDE (Cardforge) → pastille figée, title « vide »",
          cv.get("dis") == "true" and "vide" in (cv.get("title") or ""), str(cv))
    autres = [a[:2] for a in ap if a[1] != "/api/cost/estimate" and not (a[0] == "GET" and a[1] in
              ("/api/video-models", "/api/image-models", "/api/music-models", "/api/atelier/settings"))]
    check("AUCUNE DÉPENSE : le faux fetch ne voit que des lectures de modèles et l'estimation", bool(ap) and not autres, str(autres))

    # ---------- T10 : dictée ----------
    D = R.get("t10") or {}
    check("section T10 du harnais sans exception", not R.get("t10err"), str(R.get("t10err")))

    def dd(k):
        return D.get(k) or {}
    TITRE_V1 = "Dicter — reconnaissance vocale du navigateur (l'audio part au service du navigateur)"
    check("barre : le micro occupe son emplacement", D.get("slots") == ["modele:1", "micro:1"], str(D.get("slots")))
    rien = dd("rien")
    check("ÉTAT VIDE : ni reconnaissance ni enregistreur → micro = BOUTON grisé, titré « indisponible »",
          rien.get("tag") == "BUTTON" and rien.get("dis") == "true" and "indisponible" in (rien.get("title") or ""), str(rien))
    check("ÉTAT VIDE : clic sur le micro grisé → note lisible, aucun appel de dictée",
          "indisponible" in (D.get("rienNote") or "") and D.get("rienApp") == 0, f"{D.get('rienNote')!r} {D.get('rienApp')}")
    v2 = dd("v2seule")
    check("voie 2 seule (enregistreur, pas de reconnaissance) : titre de la voie 2 (coût et accord annoncés)",
          v2.get("dis") == "false" and (v2.get("title") or "").startswith("Dicter — enregistrement") and "accord" in (v2.get("title") or ""), str(v2))
    check("voie 1 : title exact du plan", dd("v1").get("title") == TITRE_V1, str(dd("v1").get("title")))
    sr = dd("sr")
    check("voie 1 : SpeechRecognition — lang = documentElement.lang || fr-FR, interimResults, continuous, start()",
          sr.get("n") == 1 and sr.get("lang") == "fr-FR" and sr.get("interim") is True and sr.get("cont") is True and sr.get("start") == 1, str(sr))
    ec = dd("ecoute")
    check("pendant l'écoute : MÊME bouton, « ■ » titré « Arrêter la dictée », classe .dzia-ecoute",
          ec.get("txt") == "■" and ec.get("title") == "Arrêter la dictée" and ec.get("ecoute") is True and D.get("meme") is True, f"{ec} {D.get('meme')}")
    check("pendant l'écoute : « À l'écoute… (clic ou Échap pour arrêter) »",
          "À l'écoute… (clic ou Échap pour arrêter)" in (D.get("noteEcoute") or ""), str(D.get("noteEcoute")))
    it = dd("interim")
    check("résultat provisoire : montré dans la note, le champ n'est PAS touché",
          it.get("val") == "Bonjour monde" and "jo" in (it.get("note") or "") and it.get("set") == 0, str(it))
    fi = dd("final")
    check("résultat final inséré AU CURSEUR avec un espace de séparation (« Bonjour joli monde »)",
          fi.get("val") == "Bonjour joli monde", str(fi))
    check("valeur posée par le setter du PROTOTYPE (React) + UN événement input qui bouillonne, curseur après le texte",
          fi.get("set") == ["TEXTAREA", "Bonjour joli monde"] and fi.get("nInput") == 1 and fi.get("sel") == [12, 12], str(fi))
    check("TÉMOIN : au repos, Échap atteint l'hôte", D.get("hoteTemoin") == 1, str(D.get("hoteTemoin")))
    check("Échap arrête l'écoute (stop()) SANS atteindre l'hôte", dd("echap").get("stop") == 1 and dd("echap").get("hote") == 1, str(D.get("echap")))
    mk = D.get("clavier") or {}
    check("micro atteignable au clavier : <button type=button> sans tabindex=-1 (Entrée/Espace natifs)",
          mk.get("tag") == "BUTTON" and mk.get("type") == "button" and mk.get("tab") != "-1", str(mk))
    af = dd("apresFin")
    check("fin d'écoute : le bouton revient au repos (titre voie 1, plus de .dzia-ecoute)",
          af.get("title") == TITRE_V1 and af.get("ecoute") is False and af.get("etat") == "repos" and af.get("txt") != "■", str(af))
    check("lang du document (en-US) transmis à la reconnaissance", D.get("lang2") == "en-US", str(D.get("lang2")))
    check("resultIndex respecté, insertion en fin après ponctuation (« Fin. suite »)", D.get("fin2") == "Fin. suite", str(D.get("fin2")))
    check("clic sur « ■ » arrête l'écoute", D.get("clicStop") == 1, str(D.get("clicStop")))
    ba = dd("bascule")
    check("erreur network de la voie 1 → voie 2 aussitôt : getUserMedia, MediaRecorder (webm/opus), prise en cours, raison dite",
          (ba.get("gum") or 0) >= 1 and (ba.get("rec") or 0) >= 1 and ba.get("mime") == "audio/webm;codecs=opus"
          and (ba.get("etat") or {}).get("etat") == "prise" and (ba.get("etat") or {}).get("txt") == "■" and "network" in (ba.get("note") or ""), str(ba))
    ea = D.get("estimeAppels") or []
    check("arrêt → UNE estimation POST /api/dictation/estimate {file} (la prise, son type, dictee.webm)",
          ea == [["POST", "/api/dictation/estimate", [["file", "blob:1234:audio/webm;codecs=opus", "dictee.webm"]]]], str(ea))
    check("les pistes du micro sont coupées après la prise", (D.get("pistes") or 0) >= 1, str(D.get("pistes")))
    check("en attente de l'accord : bouton occupé (état accord)", dd("enAccord").get("etat") == "accord", str(D.get("enAccord")))
    ma = dd("maison")
    check("dialogue MAISON (ni __dzDialogue ni VL.dialogue) : « Transcrire 12 s par ElevenLabs Scribe ≈ 0,0013 $ ? »",
          "Transcrire 12 s par ElevenLabs Scribe ≈ 0,0013 $ ?" in (ma.get("txt") or ""), str(ma))
    check("dialogue maison : Non et Oui, chacun titré (E-12)",
          sorted(b[0] for b in (ma.get("boutons") or [])) == ["non", "oui"] and all((b[2] or "").strip() for b in (ma.get("boutons") or [])), str(ma.get("boutons")))
    no = dd("non")
    check("NÉGATIF : Non → AUCUN POST /api/dictation (seule l'estimation), champ intact, dialogue fermé",
          no.get("appels") == ["/api/dictation/estimate"] and no.get("val") == "Avant" and no.get("dlg") is False, str(no))
    check("Non → « rien n'a été envoyé », bouton au repos",
          "rien n'a été envoyé" in (no.get("note") or "") and (no.get("etat") or {}).get("etat") == "repos", str(no))
    ou = dd("oui")
    ap = ou.get("appels") or []
    check("TÉMOIN : Oui → estimation puis POST /api/dictation", [a[1] for a in ap] == ["/api/dictation/estimate", "/api/dictation"], str(ap))
    corps = (ap[1][2] if len(ap) > 1 else None) or []
    check("POST /api/dictation : {file, max_usd = le montant AFFICHÉ (0.0013), language}",
          ["file", "blob:1234:audio/webm;codecs=opus", "dictee.webm"] in corps and ["max_usd", "0.0013", None] in corps
          and ["language", "en-US", None] in corps, str(corps))
    dz = ou.get("dlg") or []
    check("window.__dzDialogue.confirmer utilisé quand il existe (titre « Dictée », même message)",
          dz[:1] == ["dz"] and "Transcrire 12 s par ElevenLabs Scribe ≈ 0,0013 $ ?" in (dz[1] if len(dz) > 1 else "")
          and ((dz[2] if len(dz) > 2 else None) or {}).get("titre") == "Dictée", str(dz))
    check("texte transcrit inséré au curseur (« Avant bonjour tout le monde »), curseur après",
          ou.get("val") == "Avant bonjour tout le monde" and ou.get("sel") == [27, 27], str(ou))
    check("après transcription : note « Transcrit » avec le coût, bouton au repos",
          "Transcrit" in (ou.get("note") or "") and "0,0013" in (ou.get("note") or "") and (ou.get("etat") or {}).get("etat") == "repos", str(ou))
    vl = dd("vl")
    check("Vectorlab : VL.dialogue.confirmer utilisé à défaut de __dzDialogue ; Non → aucune transcription",
          (vl.get("dlg") or [None])[0] == "vl" and vl.get("appels") == ["/api/dictation/estimate"], str(vl))
    e4 = dd("e402")
    check("402 du serveur : champ intact, message du serveur lisible, bouton au repos",
          e4.get("val") is True and "plafond" in (e4.get("note") or "") and (e4.get("etat") or {}).get("etat") == "repos", str(e4))
    vi = dd("vide")
    check("prise vide : rien n'est envoyé, note « vide »", vi.get("appels") == 0 and "vide" in (vi.get("note") or "").lower(), str(vi))
    rf = dd("refus")
    check("getUserMedia refusé : note « accès au micro refusé », pas d'exception, aucun appel, repos",
          "accès au micro refusé" in (rf.get("note") or "") and rf.get("appels") == 0 and (rf.get("etat") or {}).get("etat") == "repos", str(rf))
    rt = dd("retire")
    check("champ retiré pendant la prise : rien n'est envoyé, pistes du micro coupées",
          rt.get("appels") == 0 and (rt.get("pistes") or 0) >= 1, str(rt))
    ind = dd("indispo")
    check("available:false : aucun dialogue, aucune transcription (seule l'estimation)",
          ind.get("appels") == ["/api/dictation/estimate"] and ind.get("dlg") == 0, str(ind))
    check("available:false : micro GRISÉ en voie 2, title = la raison du serveur ; la note la dit",
          (ind.get("etat") or {}).get("dis") == "true" and "ELEVENLABS_API_KEY" in ((ind.get("etat") or {}).get("title") or "")
          and "ELEVENLABS_API_KEY" in (ind.get("note") or ""), str(ind))
    ic = dd("indispoClic")
    check("micro grisé : un clic n'ouvre pas le micro", ic.get("dg") == 0 and (ic.get("etat") or {}).get("dis") == "true", str(ic))
    check("E-12 : tout bouton de la barre a un title (micro compris)", D.get("sansTitre") == 0, str(D.get("sansTitre")))
    tout = D.get("tout") or []
    check("AUCUNE DÉPENSE hors accord : /api/dictation n'est appelé que pour les deux « Oui » (accord, 402)",
          tout.count("/api/dictation") == 2, str(tout))

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
