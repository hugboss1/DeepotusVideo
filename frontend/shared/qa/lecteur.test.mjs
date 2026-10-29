// t372 (29/10/2026, lot A « Finitions esthétiques ») — dz-lecteur.js : le lecteur commun à la charte, joué sur un DOM
// simulé. Séries : temps (m:ss, h:mm:ss, inconnu), amélioration d'un <audio controls> (controls retiré, barre posée
// JUSTE APRÈS le média, rien n'est déplacé), idempotence, « natif » respecté, média sans controls ignoré, lecture /
// pause, progression (glisser = currentTime, rempli par la règle commune t373, aria-valuetext), son coupé / volume,
// vidéo (surimpression, parent rendu positionné, plein écran par le média), observateur (média ajouté, controls
// remis par l'hôte, média retiré = barre retirée), aucun innerHTML, textes FR puis EN.
// Lancer : node frontend/shared/qa/lecteur.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-lecteur.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };

class Noeud {
  constructor(tag, ns) {
    this.tagName = String(tag).toUpperCase(); this.ns = ns || null; this.nodeType = 1;
    this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = "";
    const props = {};
    this.style = { setProperty(k, v) { props[k] = String(v); }, getPropertyValue(k) { return props[k] || ""; } };
    this.position = "static"; this.offsetLeft = 10; this.offsetTop = 20; this.offsetWidth = 360; this.offsetHeight = 640;
  }
  get parentNode() { return this.parent; }
  get isConnected() { let x = this; while (x.parent) x = x.parent; return x === DOC.racine; }
  get offsetParent() { return this.isConnected && this.style.display !== "none" ? this.parent : null; }
  get nextSibling() { if (!this.parent) return null; const s = this.parent.children; return s[s.indexOf(this) + 1] || null; }
  appendChild(c) { return this.insertBefore(c, null); }
  insertBefore(c, ref) {
    if (c.parent) c.parent.removeChild(c);
    c.parent = this; const i = ref ? this.children.indexOf(ref) : -1;
    if (i >= 0) this.children.splice(i, 0, c); else this.children.push(c);
    DOC.muter({ type: "childList", addedNodes: [c], removedNodes: [] }); return c;
  }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; DOC.muter({ type: "childList", addedNodes: [], removedNodes: [c] }); return c; }
  remove() { if (this.parent) this.parent.removeChild(this); }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "type") this.type = String(v); if (k === "value") this.value = String(v); DOC.muter({ type: "attributes", target: this, attributeName: k }); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; DOC.muter({ type: "attributes", target: this, attributeName: k }); }
  get controls() { return this.hasAttribute("controls"); }
  set controls(v) { if (v) this.setAttribute("controls", ""); else this.removeAttribute("controls"); }
  get hidden() { return this.hasAttribute("hidden"); }
  set hidden(v) { if (v) this.setAttribute("hidden", ""); else this.removeAttribute("hidden"); }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(v) { throw new Error("innerHTML interdit"); }
  get innerHTML() { throw new Error("innerHTML interdit"); }
  insertAdjacentHTML() { throw new Error("insertAdjacentHTML interdit"); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); }
  fire(t, extra = {}) { const ev = Object.assign({ type: t, target: this, preventDefault() {}, stopPropagation() {} }, extra); (this.ec[t] || []).forEach((f) => f(ev)); return ev; }
  click() { return this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
  querySelectorAll(sel) {
    if (sel !== "audio[controls],video[controls]") throw new Error("sélecteur non simulé : " + sel);
    return [...this.tous()].filter((x) => x !== this && (x.tagName === "AUDIO" || x.tagName === "VIDEO") && x.hasAttribute("controls"));
  }
}
class Media extends Noeud {
  constructor(tag) { super(tag); this.paused = true; this.currentTime = 0; this.duration = NaN; this.volume = 1; this.muted = false; this.plein = 0; }
  play() { this.paused = false; this.fire("play"); return Promise.resolve(); }
  pause() { this.paused = true; this.fire("pause"); }
  requestFullscreen() { this.plein++; return Promise.resolve(); }
}

const DOC = {
  file: [], obs: [],
  muter(m) { if (DOC.obs.length) DOC.file.push(m); },
  vider() { const f = DOC.file; DOC.file = []; if (f.length) DOC.obs.forEach((cb) => cb(f)); },
};

function monde(langue) {
  DOC.racine = new Noeud("html"); DOC.obs = []; DOC.file = [];
  const head = new Noeud("head"), body = new Noeud("body");
  DOC.racine.appendChild(head); DOC.racine.appendChild(body);
  const fs = { el: null };
  const document = {
    documentElement: DOC.racine, head, body,
    get fullscreenElement() { return fs.el; },
    createElement: (t) => (t === "audio" || t === "video" ? new Media(t) : new Noeud(t)),
    createElementNS: (ns, t) => new Noeud(t, ns),
    getElementById: (id) => [...DOC.racine.tous()].find((x) => x.attrs.id === id) || null,
    addEventListener() {}, exitFullscreen() { fs.el = null; return Promise.resolve(); },
  };
  class MutationObserver { constructor(cb) { this.cb = cb; } observe(cible, o) { this.o = o; DOC.obs.push(this.cb); } disconnect() {} }
  class ResizeObserver { constructor(cb) { this.cb = cb; } observe() {} disconnect() {} }
  const ctx = { console, document, MutationObserver, ResizeObserver, setTimeout, clearTimeout, Promise,
    getComputedStyle: (e) => ({ position: e.position }), addEventListener() {} };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(DICO, ctx);
  vm.runInContext(`window.dzT=function(k,p){var e=window.DZ_I18N[k];if(!e)return "⟦"+k+"⟧";var s=e["${langue}"]||e.fr;
    if(p)Object.keys(p).forEach(function(c){s=s.split("{"+c+"}").join(p[c])});return s}`, ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, document, body, fs };
}
const L = (racine, v) => [...racine.tous()].find((x) => x.attrs["data-dz-lecteur"] === v);
const usage = (bouton) => { const u = [...bouton.tous()].find((x) => x.tagName === "USE"); return u ? u.attrs.href : ""; };

// ── 1. temps ─────────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { ctx } = monde("fr");
  const t = ctx.__dzLecteur.temps;
  ok("1.1 0 s → 0:00", t(0) === "0:00", t(0));
  ok("1.2 83,9 s → 1:23 (tronqué)", t(83.9) === "1:23", t(83.9));
  ok("1.3 3725 s → 1:02:05", t(3725) === "1:02:05", t(3725));
  ok("1.4 inconnu (NaN, Infinity, négatif) → --:--", t(NaN) === "--:--" && t(Infinity) === "--:--" && t(-1) === "--:--", [t(NaN), t(Infinity), t(-1)]);
  ok("1.5 l'API est posée une seule fois (rechargement sans effet)", (() => { const a = ctx.__dzLecteur; vm.runInContext(SRC, ctx); return ctx.__dzLecteur === a; })());
}

// ── 2. audio ─────────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { ctx, document, body } = monde("fr");
  const hote = document.createElement("div"); body.appendChild(hote);
  const apres = document.createElement("span"); const a = document.createElement("audio");
  a.setAttribute("src", "/x.mp3"); a.setAttribute("controls", ""); a.style.width = "60vw"; a.style.maxWidth = "520px";
  hote.appendChild(a); hote.appendChild(apres);
  const barre = ctx.__dzLecteur.ameliorer(a);
  ok("2.1 la barre est rendue", !!barre && barre.attrs["data-dz-lecteur"] === "barre");
  ok("2.2 controls est RETIRÉ du média (plus de lecteur natif blanc)", !a.hasAttribute("controls"));
  ok("2.3 le média reste EN PLACE (React garde son nœud) et la barre vient JUSTE APRÈS lui",
    a.parent === hote && hote.children.indexOf(barre) === hote.children.indexOf(a) + 1 && hote.children.indexOf(apres) === hote.children.indexOf(barre) + 1,
    hote.children.map((c) => c.tagName));
  ok("2.4 genre audio, rôle group, libellé traduit", barre.attrs["data-dz-genre"] === "audio" && barre.attrs.role === "group" && barre.attrs["aria-label"] === "Lecteur");
  ok("2.5 la barre reprend la largeur posée sur le média", barre.style.width === "60vw" && barre.style.maxWidth === "520px", [barre.style.width, barre.style.maxWidth]);
  ok("2.6 le média est marqué « ameliore »", a.attrs["data-dz-lecteur"] === "ameliore");
  ok("2.7 idempotent : une seconde amélioration rend la même barre, aucune barre de plus",
    ctx.__dzLecteur.ameliorer(a) === barre && [...body.tous()].filter((x) => x.attrs["data-dz-lecteur"] === "barre").length === 1);
  const lire = L(barre, "lire"), cur = L(barre, "position"), tps = L(barre, "temps"), dur = L(barre, "duree");
  ok("2.8 bouton lecture : type button, « Lire », icône dz-media-lecture", lire.tagName === "BUTTON" && lire.attrs.type === "button" && lire.attrs["aria-label"] === "Lancer la lecture" && usage(lire).endsWith("#dz-media-lecture"), usage(lire));
  ok("2.9 temps et durée en mono : 0:00 / --:-- avant les métadonnées", tps.textContent === "0:00" && dur.textContent === "--:--", [tps.textContent, dur.textContent]);
  ok("2.10 aucune vidéo : pas de bouton plein écran", !L(barre, "plein-ecran"));
  a.duration = 83; a.fire("loadedmetadata");
  ok("2.11 durée lue : 1:23", dur.textContent === "1:23", dur.textContent);
  lire.click();
  ok("2.12 clic Lire → play, l'état passe à « lecture », libellé Pause, icône pause",
    a.paused === false && barre.attrs["data-etat"] === "lecture" && lire.attrs["aria-label"] === "Pause" && usage(lire).endsWith("#dz-media-pause"), [barre.attrs["data-etat"], usage(lire)]);
  lire.click();
  ok("2.13 second clic → pause", a.paused === true && barre.attrs["data-etat"] === "pause" && lire.attrs["aria-label"] === "Lancer la lecture");
  a.currentTime = 41.5; a.fire("timeupdate");
  ok("2.14 timeupdate : temps 0:41, curseur à 500/1000 (le rempli suit la valeur : règle commune dz-curseur.css, t373)",
    tps.textContent === "0:41" && cur.value === "500" && cur.style.getPropertyValue("--dz-lecteur-pos") === "", [tps.textContent, cur.value]);
  ok("2.15 curseur de position : range 0..1000, libellé et valeur parlée", cur.attrs.type === "range" && cur.attrs.min === "0" && cur.attrs.max === "1000"
    && cur.attrs["aria-label"] === "Position de lecture" && cur.attrs["aria-valuetext"] === "0:41 sur 1:23", cur.attrs["aria-valuetext"]);
  cur.value = "250"; cur.fire("input");
  ok("2.16 glisser le curseur déplace la lecture (250/1000 de 83 s)", Math.abs(a.currentTime - 20.75) < 1e-9 && tps.textContent === "0:20", [a.currentTime, tps.textContent]);
  cur.fire("pointerdown"); a.currentTime = 70; a.fire("timeupdate");
  ok("2.17 pendant le glisser, timeupdate ne reprend pas le curseur", cur.value === "250", cur.value);
  cur.fire("change"); a.fire("timeupdate");
  ok("2.18 relâché : le curseur suit de nouveau", cur.value === String(Math.round(70 / 83 * 1000)), cur.value);
  const son = L(barre, "son"), vol = L(barre, "volume");
  ok("2.19 son : « Couper le son », icône dz-media-audio ; volume 0..100 à 100", son.attrs["aria-label"] === "Couper le son" && usage(son).endsWith("#dz-media-audio")
    && vol.attrs.type === "range" && vol.value === "100" && vol.attrs["aria-label"] === "Volume");
  son.click();
  ok("2.20 clic son → muted, « Rétablir le son », icône dz-media-muet", a.muted === true && (a.fire("volumechange"), son.attrs["aria-label"] === "Rétablir le son") && usage(son).endsWith("#dz-media-muet"));
  vol.value = "40"; vol.fire("input");
  ok("2.21 le curseur de volume règle le média et rétablit le son", a.volume === 0.4 && a.muted === false, [a.volume, a.muted]);
  a.volume = 0.7; a.fire("volumechange");
  ok("2.22 un volume posé par l'hôte (Son & VFX) remonte au curseur", vol.value === "70", vol.value);
  a.fire("ended");
  ok("2.23 fin de lecture → état pause", barre.attrs["data-etat"] === "pause");
  a.fire("error");
  ok("2.24 erreur du média → état erreur, durée --:--, bouton désactivé, titre traduit", barre.attrs["data-etat"] === "erreur" && dur.textContent === "--:--" && lire.hasAttribute("disabled") && barre.attrs.title === "Lecture impossible");
  a.fire("loadstart"); a.duration = 10; a.fire("durationchange");
  ok("2.25 nouvelle source → l'erreur s'efface", barre.attrs["data-etat"] === "pause" && !lire.hasAttribute("disabled") && dur.textContent === "0:10");
  ok("2.26 aucun innerHTML (le DOM simulé lève sinon) et une seule feuille injectée", [...document.head.tous()].filter((x) => x.attrs.id === "dz-lecteur-css").length === 1);
  const css = document.getElementById("dz-lecteur-css").textContent;
  ok("2.27 feuille : fond --bg-panel, lecture --amber, temps --font-mono, angles var(--radius), marges --pad-*",
    /background:var\(--bg-panel\)/.test(css) && /var\(--amber\)/.test(css) && /font-family:var\(--font-mono\)/.test(css) && /border-radius:var\(--radius\)/.test(css) && /var\(--pad-[1-4]\)/.test(css));
  ok("2.28 feuille : AUCUN rayon littéral, aucune couleur en dur (#, rgb)", !/border-radius:\s*[0-9.]+(px|%|em)/.test(css) && !/#[0-9a-fA-F]{3,8}\b/.test(css) && !/rgba?\(/.test(css), css.match(/border-radius:[^;}]*/g));
}

// ── 3. natif, sans controls, retrait ─────────────────────────────────────────────────────────────────────────────
{
  const { ctx, document, body } = monde("fr");
  const n1 = document.createElement("audio"); n1.setAttribute("controls", ""); n1.setAttribute("data-dz-lecteur", "natif"); body.appendChild(n1);
  ok("3.1 data-dz-lecteur=\"natif\" garde ses contrôles", ctx.__dzLecteur.ameliorer(n1) === null && n1.hasAttribute("controls"));
  const n2 = document.createElement("video"); body.appendChild(n2);
  ctx.__dzLecteur.balayer(body);
  ok("3.2 un média SANS controls (aperçus muets, extraction d'images) n'est pas touché", !n2.attrs["data-dz-lecteur"] && body.children.length === 2);
  const d = document.createElement("div");
  ok("3.3 autre balise → null", ctx.__dzLecteur.ameliorer(d) === null);
  const orphelin = document.createElement("audio"); orphelin.setAttribute("controls", "");
  ok("3.4 média sans parent → null (rien à poser)", ctx.__dzLecteur.ameliorer(orphelin) === null && orphelin.hasAttribute("controls"));
}

// ── 4. vidéo ─────────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { ctx, document, body, fs } = monde("en");
  const cadre = document.createElement("div"); body.appendChild(cadre);
  const v = document.createElement("video"); v.setAttribute("controls", ""); cadre.appendChild(v);
  const barre = ctx.__dzLecteur.ameliorer(v);
  ok("4.1 genre vidéo, barre après le média", barre.attrs["data-dz-genre"] === "video" && cadre.children[1] === barre);
  ok("4.2 le parent statique devient le repère (position relative) pour la surimpression", cadre.style.position === "relative", cadre.style.position);
  ok("4.3 barre posée sur le bas de l'image : gauche, haut = haut + hauteur − barre, largeur", barre.style.left === "10px" && barre.style.width === "360px"
    && barre.style.top === (20 + 640 - 32) + "px", [barre.style.left, barre.style.top, barre.style.width]);
  ok("4.4 visible tant que la vidéo est en pause", barre.attrs["data-visible"] === "1");
  v.play();
  ok("4.5 en lecture sans survol : la barre s'efface", barre.attrs["data-visible"] === "0");
  v.fire("pointerenter");
  ok("4.6 survol de l'image : la barre revient", barre.attrs["data-visible"] === "1");
  v.fire("pointerleave");
  ok("4.7 sortie : elle s'efface", barre.attrs["data-visible"] === "0");
  barre.fire("focusin");
  ok("4.8 focus clavier dans la barre : visible", barre.attrs["data-visible"] === "1");
  barre.fire("focusout");
  v.paused = true; v.click();
  ok("4.9 clic sur l'image : lecture / pause comme le lecteur natif", v.paused === false);
  const plein = L(barre, "plein-ecran");
  ok("4.10 bouton plein écran en anglais, icône dz-action-ajuster-vue (quatre coins)", plein && plein.attrs["aria-label"] === "Full screen" && usage(plein).endsWith("#dz-action-ajuster-vue") && L(barre, "lire").attrs["aria-label"] === "Pause", plein && plein.attrs["aria-label"]);
  plein.click();
  ok("4.11 plein écran : demandé au média, contrôles natifs prêtés le temps du plein écran", v.plein === 1 && v.hasAttribute("controls"));
  DOC.vider();
  ok("4.12 l'observateur ne les retire pas pendant le plein écran", v.hasAttribute("controls"));
  fs.el = null; document.fullscreenElement; ctx.__dzLecteur._sortiePleinEcran(v);
  DOC.vider();
  ok("4.13 sortie du plein écran : contrôles natifs rendus à la barre", !v.hasAttribute("controls"));
  v.style.display = "none"; v.fire("timeupdate");
  ok("4.14 vidéo masquée par l'hôte (onError) → barre masquée", barre.hidden === true);
  const autre = document.createElement("div"); autre.position = "absolute"; body.appendChild(autre);
  const v2 = document.createElement("video"); v2.setAttribute("controls", ""); autre.appendChild(v2); ctx.__dzLecteur.ameliorer(v2);
  ok("4.15 un parent déjà positionné n'est pas retouché", autre.style.position === undefined, autre.style.position);
  ok("4.16 plusieurs lecteurs : une seule feuille injectée", [...document.head.tous()].filter((x) => x.attrs.id === "dz-lecteur-css").length === 1);
}

// ── 5. observateur ───────────────────────────────────────────────────────────────────────────────────────────────
{
  const { ctx, document, body } = monde("fr");
  ok("5.1 l'observateur est branché au chargement (childList, subtree, attribut controls)", DOC.obs.length === 1);
  const zone = document.createElement("div");
  const a = document.createElement("audio"); a.setAttribute("controls", ""); zone.appendChild(a);
  body.appendChild(zone); DOC.vider();
  const barre = a.nextSibling;
  ok("5.2 un média ajouté plus tard (rendu React, innerHTML d'un lab) est amélioré", barre && barre.attrs["data-dz-lecteur"] === "barre" && !a.hasAttribute("controls"));
  a.setAttribute("controls", ""); DOC.vider();
  ok("5.3 l'hôte remet controls → retiré de nouveau, pas de seconde barre", !a.hasAttribute("controls") && zone.children.filter((x) => x.attrs["data-dz-lecteur"] === "barre").length === 1);
  zone.removeChild(a); DOC.vider();
  ok("5.4 média retiré (React démonte) → sa barre part avec lui", !barre.parent, zone.children.map((x) => x.tagName));
  const v = document.createElement("video"); body.appendChild(v); v.setAttribute("controls", ""); DOC.vider();
  ok("5.5 controls posé APRÈS l'insertion (code d'un lab) → amélioré", v.attrs["data-dz-lecteur"] === "ameliore");
  const muet = document.createElement("video"); body.appendChild(muet); DOC.vider();
  ok("5.6 une vidéo SANS controls ajoutée (vignette, pool du Montage) n'est pas touchée", !muet.attrs["data-dz-lecteur"] && !muet.nextSibling);
}

if (echecs.length) { console.log(`ÉCHEC ${echecs.length}/${n}`); echecs.forEach((e) => console.log("  ✗ " + e)); process.exit(1); }
console.log(`OK ${n}/${n} — dz-lecteur`);
