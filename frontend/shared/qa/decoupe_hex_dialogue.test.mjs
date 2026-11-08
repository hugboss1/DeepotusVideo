// Plateau hexagonal, lot 1, tâche 5 — le dialogue partagé « Découper en hexagones » (frontend/shared/dz-decoupe-hex.js),
// joué devant un DOM simulé (voile, champs, canvas d'aperçu) avec un réseau, un window.open et un fournirImage en
// doublures pilotées. Le traducteur T est le VRAI dictionnaire (frontend/shared/i18n, français).
// Lancer : node frontend/shared/qa/decoupe_hex_dialogue.test.mjs
import { readFileSync, readdirSync } from "node:fs";
import { cadrageCouvrant, pppEffectif, grille, FORMATS_HEX, PIXELS_MAX } from "../dz-decoupe-hex-logique.js";

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };
const proche = (a, b, e = 1e-6) => Math.abs(a - b) <= e;

/* ── le dictionnaire réel (français) ── */
const DICO = {};
const dossier = new URL("../i18n/", import.meta.url);
for (const f of readdirSync(dossier).filter((x) => x.endsWith(".json"))) Object.assign(DICO, JSON.parse(readFileSync(new URL(f, dossier), "utf8")));
const T = (cle, vars) => {
  const e = DICO[cle];
  if (!e) return "??" + cle;
  return vars ? e.fr.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m)) : e.fr;
};

/* ── un DOM minimal ── */
const CTX = { appels: [], reset() { this.appels = []; } };
for (const m of ["clearRect", "drawImage", "beginPath", "moveTo", "lineTo", "closePath", "stroke", "save", "restore", "setLineDash", "fillRect"]) {
  CTX[m] = (...a) => { CTX.appels.push([m, ...a]); };
}
class FE {
  constructor(tag) {
    this.tag = tag; this.className = ""; this.children = []; this.attrs = {}; this.listeners = {}; this._text = "";
    this.value = ""; this.disabled = false; this.hidden = false; this.parentNode = null; this.width = 0; this.height = 0;
    this.href = ""; this.type = ""; this.id = ""; this.style = {};
  }
  set textContent(t) { this._text = String(t); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; return c; }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  removeEventListener(t, f) { this.listeners[t] = (this.listeners[t] || []).filter((x) => x !== f); }
  focus() { globalThis.document.activeElement = this; }
  querySelectorAll() { return tous(this, (e) => e !== this && (e.tag === "input" || e.tag === "select" || e.tag === "button" || e.tag === "a" || (e.tag === "canvas" && e.attrs.tabindex != null))); }
  setPointerCapture() {}
  releasePointerCapture() {}
  getBoundingClientRect() { return { width: this.width, height: this.height, left: 0, top: 0 }; }
  getContext() { return CTX; }
  emet(type, ev = {}) {
    const e = { type, target: this, preventDefault() { this.vu = true; }, ...ev };
    (this.listeners[type] || []).slice().forEach((f) => f(e));
    return e;
  }
}
const tous = (e, f, out = []) => { if (f(e)) out.push(e); e.children.forEach((c) => tous(c, f, out)); return out; };

const docListeners = {};
const racine = new FE("body");
const entete = new FE("head");
globalThis.document = {
  body: racine, head: entete,
  createElement: (t) => new FE(t),
  getElementById: (id) => tous(entete, (e) => e.id === id)[0] || null,
  addEventListener: (t, f) => { (docListeners[t] = docListeners[t] || []).push(f); },
  removeEventListener: (t, f) => { docListeners[t] = (docListeners[t] || []).filter((x) => x !== f); },
};
let ouvertures = [];
let retourOpen = {};
globalThis.window = { open: (...a) => { ouvertures.push(a); return retourOpen; }, fetch: () => { throw new Error("fetch non injecté"); } };
const touche = (key, extra = {}) => { const e = { key, preventDefault() { this.vu = true; }, ...extra }; (docListeners.keydown || []).slice().forEach((f) => f(e)); return e; };

const { ouvrirDecoupeHex } = await import("../dz-decoupe-hex.js");

const champ = (nom) => tous(racine, (e) => e.attrs["data-dh"] === nom)[0];
const estVoile = (e) => e.className.split(" ").includes("dz-dh");
const voile = () => tous(racine, estVoile)[0];

/* ── un banc de dialogue : réseau, image, ouverture ── */
function banc(opts = {}) {
  const b = { posts: [], images: [], apercu: { width: 700, height: 400, tag: "apercu" } };
  b.fetch = async (url, init) => {
    b.posts.push({ url, init, corps: JSON.parse(init.body) });
    const r = b.reponse ? b.reponse(b.posts.length) : { ok: true, status: 200, json: async () => ({ deck: { id: "deck_00000042", name: "Plateau" }, tuiles: ["t1.png", "t2.png"], ppp: 301 }) };
    return r;
  };
  b.fournirImage = async (etendue) => { b.images.push(etendue); if (b.refus) throw new Error(b.refus); return "fond_" + b.images.length + ".png"; };
  b.args = { largeur: opts.largeur || 6958, hauteur: opts.hauteur || 20000, apercu: b.apercu, nomImage: "fond", fournirImage: b.fournirImage, T, fetch: b.fetch, depart: opts.depart };
  b.ouvrir = () => { b.promesse = ouvrirDecoupeHex(b.args); return b.promesse; };
  return b;
}
const attendre = () => new Promise((r) => setTimeout(r, 0));
const fermerTout = async () => { if (voile()) { touche("Escape"); await attendre(); } ouvertures = []; retourOpen = {}; CTX.reset(); };
const saisir = (nom, valeur) => { const c = champ(nom); c.value = String(valeur); c.emet("input"); c.emet("change"); return c; };
const creer = () => champ("creer");

// 1 le corps POSTé, exactement
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 1.4, x: 0.2, y: 0.5 } });
  b.ouvrir();
  await attendre();
  ok("1.1 le dialogue est ouvert sous .dz-dh", !!voile());
  ok("1.2 titre traduit", tous(voile(), (e) => e.textContent === T("decoupehex.dialogue.titre")).length >= 1);
  ok("1.3 fournirImage pas encore appelé", b.images.length === 0);
  ok("1.4 compteur : 24 tuiles", champ("tuiles").textContent === "Tuiles : 24", champ("tuiles").textContent);
  ok("1.5 « Créer » actif", creer().disabled === false);
  creer().emet("click");
  creer().emet("click");                                     // un second clic pendant la création est sans effet
  await attendre(); await attendre();
  ok("1.6 fournirImage appelé UNE fois, au clic", b.images.length === 1, b.images.length);
  const g = grille("hex_p90", 6, 4);
  ok("1.7 l'étendue passée à fournirImage", b.images[0] && proche(b.images[0].largeurMm, g.largeurMm) && proche(b.images[0].hauteurMm, g.hauteurMm), JSON.stringify(b.images[0]));
  ok("1.8 un seul POST", b.posts.length === 1, b.posts.length);
  ok("1.9 route et verbe", b.posts[0].url === "/api/cards/decks/plateau" && b.posts[0].init.method === "POST", b.posts[0].url);
  ok("1.10 corps exact", JSON.stringify(b.posts[0].corps) === JSON.stringify({ image: "fond_1.png", format: "hex_p90", colonnes: 6, rangees: 4, cadrage: { zoom: 1.4, x: 0.2, y: 0.5 }, name: "Plateau — fond" }), JSON.stringify(b.posts[0].corps));
  ok("1.11 ouverture du Card Forge", ouvertures.length === 1 && ouvertures[0][0] === "/cardforge/?deck=deck_00000042", JSON.stringify(ouvertures));
  const r = await b.promesse;
  ok("1.12 retour {deck, tuiles}", r && r.deck.id === "deck_00000042" && r.tuiles.length === 2, JSON.stringify(r));
  ok("1.13 dialogue fermé", !voile());
}

// 2 les bornes
{
  const b = banc(); b.ouvrir(); await attendre();
  saisir("colonnes", 31);
  ok("2.1 colonnes = 31 : « Créer » désactivé", creer().disabled === true);
  ok("2.2 phrase de borne", champ("borne").textContent === T("decoupehex.grille.borne", { max: 30 }), champ("borne").textContent);
  creer().emet("click"); await attendre();
  ok("2.3 aucun appel sur un clic refusé", b.images.length === 0 && b.posts.length === 0);
  saisir("colonnes", 30); saisir("rangees", 17);
  ok("2.4 510 tuiles : désactivé, phrase du plafond", creer().disabled === true && champ("borne").textContent === T("decoupehex.grille.tuiles_max", { n: 510, max: 500 }), champ("borne").textContent);
  saisir("colonnes", 2.5);
  ok("2.5 colonnes non entier : désactivé", creer().disabled === true);
  saisir("colonnes", "");
  ok("2.6 colonnes vide : désactivé", creer().disabled === true);
  saisir("colonnes", 3); saisir("rangees", 2);
  ok("2.7 retour dans les bornes : actif, phrase effacée", creer().disabled === false && champ("borne").textContent === "", champ("borne").textContent);
  await fermerTout();
}

// 3 le plafond de pixels (même formule que le serveur, à 300 dpi)
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 30, rangees: 16 } }); b.ouvrir(); await attendre();
  const g = grille("hex_p90", 30, 16);
  const px = Math.round(g.largeurMm / 25.4 * 300) * Math.round(g.hauteurMm / 25.4 * 300);
  ok("3.0 le cas dépasse bien PIXELS_MAX", px > PIXELS_MAX, px);
  ok("3.1 30 x 16 : désactivé", creer().disabled === true);
  ok("3.2 phrase des pixels", champ("borne").textContent === T("decoupehex.grille.pixels_max", { mpx: Math.ceil(px / 1e6), max: 150 }), champ("borne").textContent);
  saisir("colonnes", 6); saisir("rangees", 4);
  ok("3.3 6 x 4 : actif", creer().disabled === false);
  await fermerTout();
}

// 4 erreur serveur : dialogue ouvert, phrase affichée, pas de nouvelle image au second essai
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  b.reponse = (k) => (k === 1
    ? { ok: false, status: 400, json: async () => ({ detail: "image illisible : fond_1.png" }) }
    : { ok: true, status: 200, json: async () => ({ deck: { id: "deck_00000007" }, tuiles: [] }) });
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("4.1 dialogue resté ouvert", !!voile());
  ok("4.2 phrase du serveur dans le dialogue", champ("message").textContent === "image illisible : fond_1.png", champ("message").textContent);
  ok("4.3 « Créer » de nouveau actif", creer().disabled === false);
  ok("4.4 pas d'ouverture", ouvertures.length === 0);
  creer().emet("click"); await attendre(); await attendre();
  ok("4.5 même grille : l'image de la Bibliothèque est réutilisée", b.images.length === 1 && b.posts[1].corps.image === "fond_1.png", b.images.length);
  const r = await b.promesse;
  ok("4.6 le second essai réussit", r && r.deck.id === "deck_00000007");
  await fermerTout();
}
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  b.reponse = (k) => (k === 1 ? { ok: false, status: 400, json: async () => ({ detail: "non" }) } : { ok: true, status: 200, json: async () => ({ deck: { id: "deck_00000008" }, tuiles: [] }) });
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  saisir("colonnes", 5);
  creer().emet("click"); await attendre(); await attendre();
  ok("4.7 grille changée : nouvelle étendue, nouvelle image", b.images.length === 2 && b.posts[1].corps.image === "fond_2.png", b.images.length);
  await b.promesse;
  await fermerTout();
}
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  b.reponse = () => ({ ok: false, status: 502, json: async () => { throw new Error("pas du JSON"); } });
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("4.8 corps non JSON : phrase générique avec le code", champ("message").textContent === T("decoupehex.erreur.http", { code: 502 }), champ("message").textContent);
  await fermerTout();
}
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  b.refus = "Export impossible";
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("4.9 fournirImage refuse : sa phrase, aucun POST", champ("message").textContent === "Export impossible" && b.posts.length === 0 && !!voile(), champ("message").textContent);
  await fermerTout();
}

// 5 ppp affiché et avertissement
{
  const b = banc({ largeur: 6958, hauteur: 20000, depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 1, x: 0.5, y: 0.5 } });
  b.ouvrir(); await attendre();
  const g = grille("hex_p90", 6, 4);
  const r = cadrageCouvrant(6958, 20000, g.largeurMm, g.hauteurMm, 1, 0.5, 0.5);
  const attendu = Math.round(pppEffectif(r.w, g.largeurMm));
  ok("5.1 ppp = pppEffectif du cadrage courant", attendu === 299 && champ("ppp").textContent === T("decoupehex.cadrage.ppp", { ppp: attendu }), champ("ppp").textContent);
  ok("5.2 299 ppp : avertissement", champ("alerte").textContent === T("decoupehex.cadrage.ppp_faible", { min: 300 }) && champ("alerte").hidden === false, champ("alerte").textContent);
  ok("5.3 l'avertissement ne bloque pas « Créer »", creer().disabled === false);
  saisir("zoom", 1.5);
  ok("5.4 zoomer baisse les ppp", champ("ppp").textContent === T("decoupehex.cadrage.ppp", { ppp: Math.round(attendu / 1.5) }), champ("ppp").textContent);
  await fermerTout();
  const c = banc({ largeur: 6981, hauteur: 20000, depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  c.ouvrir(); await attendre();
  ok("5.5 300 ppp : pas d'avertissement", champ("ppp").textContent === T("decoupehex.cadrage.ppp", { ppp: 300 }) && champ("alerte").textContent === "" && champ("alerte").hidden === true, champ("alerte").textContent);
  await fermerTout();
}

// 6 glisser, molette, curseur
{
  const b = banc({ largeur: 8000, hauteur: 8000, depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 2, x: 0.5, y: 0.5 } });
  b.ouvrir(); await attendre();
  const cv = champ("apercu");
  cv.width = 400; cv.height = 300;
  const g = grille("hex_p90", 6, 4);
  const r0 = cadrageCouvrant(8000, 8000, g.largeurMm, g.hauteurMm, 2, 0.5, 0.5);
  cv.emet("pointerdown", { clientX: 100, clientY: 100, pointerId: 1 });
  cv.emet("pointermove", { clientX: 60, clientY: 100, pointerId: 1 });     // 40 px vers la gauche : l'image suit, le cadre va à droite
  cv.emet("pointerup", { pointerId: 1 });
  creer().emet("click"); await attendre(); await attendre();
  const c = b.posts[0].corps.cadrage;
  const attenduX = (r0.x + 40 * r0.w / 400) / (8000 - r0.w);
  ok("6.1 glisser vers la gauche avance x de la distance voulue", proche(c.x, attenduX, 1e-9) && c.x > 0.5, JSON.stringify(c) + " attendu " + attenduX);
  ok("6.2 un glissement horizontal ne touche pas y ni le zoom", c.y === 0.5 && c.zoom === 2, JSON.stringify(c));
  await b.promesse;
  await fermerTout();

  const d = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 1.2 } });
  d.ouvrir(); await attendre();
  const cv2 = champ("apercu");
  const e1 = cv2.emet("wheel", { deltaY: 100 });                // vers l'utilisateur : dézoomer
  ok("6.3 molette : défilement retenu", e1.vu === true);
  ok("6.4 jamais sous 1 (curseur synchronisé)", Number(champ("zoom").value) === 1, champ("zoom").value);
  cv2.emet("wheel", { deltaY: -100 });
  ok("6.5 molette vers l'avant : zoom > 1", Number(champ("zoom").value) > 1, champ("zoom").value);
  saisir("zoom", 0.2);
  ok("6.6 curseur hors borne ramené à 1", Number(champ("zoom").value) === 1, champ("zoom").value);
  ok("6.7 le curseur est borné 1..8", champ("zoom").attrs.min === "1" && champ("zoom").attrs.max === "8");
  await fermerTout();
}

// 7 l'aperçu : image selon cadrageCouvrant, contours des tuiles, fond perdu non dessiné
{
  const b = banc({ largeur: 700, hauteur: 400, depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 1.4, x: 0.2, y: 0.8 } });
  b.apercu.width = 350; b.apercu.height = 200;
  b.ouvrir(); await attendre();
  const g = grille("hex_p90", 6, 4);
  const cv = champ("apercu");
  const r = cadrageCouvrant(700, 400, g.largeurMm, g.hauteurMm, 1.4, 0.2, 0.8);
  const dessin = CTX.appels.filter((a) => a[0] === "drawImage").pop();
  ok("7.1 drawImage du cadrage couvrant (échelle de l'aperçu)", !!dessin && dessin[1] === b.apercu
    && proche(dessin[2], r.x * 0.5, 1e-6) && proche(dessin[3], r.y * 0.5, 1e-6) && proche(dessin[4], r.w * 0.5, 1e-6) && proche(dessin[5], r.h * 0.5, 1e-6)
    && dessin[6] === 0 && dessin[7] === 0 && dessin[8] === cv.width && dessin[9] === cv.height, JSON.stringify(dessin && dessin.slice(2)));
  ok("7.2 le canvas a le rapport de l'étendue", proche(cv.width / cv.height, g.largeurMm / g.hauteurMm, 0.01), cv.width + "x" + cv.height);
  const derniere = CTX.appels.map((a) => a[0]);
  const depuis = derniere.lastIndexOf("clearRect");
  const passe = CTX.appels.slice(depuis);
  const fermes = passe.filter((a) => a[0] === "closePath").length;
  ok("7.3 un contour fermé par tuile", fermes === 24, fermes);
  // un hexagone = 6 sommets : un moveTo + 5 lineTo
  ok("7.4 six sommets par contour", passe.filter((a) => a[0] === "moveTo").length === 24 && passe.filter((a) => a[0] === "lineTo").length === 24 * 5);
  // le premier contour est dans l'étendue, au bon endroit : pointe en haut → un sommet au-dessus du centre
  const k = cv.width / g.largeurMm;
  const mv = passe.find((a) => a[0] === "moveTo");
  const c0 = g.centres[0];
  const R = FORMATS_HEX.hex_p90.p / Math.sqrt(3);
  ok("7.5 premier sommet en haut du premier centre (pointe en haut)", proche(mv[1], c0.x * k, 1e-6) && proche(mv[2], (c0.y - R) * k, 1e-6), JSON.stringify(mv));
  ok("7.6 tous les sommets dans le cadre (fond perdu hors des contours)", passe.filter((a) => a[0] === "moveTo" || a[0] === "lineTo").every((a) => a[1] >= 0 && a[1] <= cv.width && a[2] >= 0 && a[2] <= cv.height));
  // format à côté plat : le premier sommet est à droite du centre
  saisir("format", "hex_f90");
  const g2 = grille("hex_f90", 6, 4);
  const k2 = champ("apercu").width / g2.largeurMm;
  const passe2 = CTX.appels.slice(CTX.appels.map((a) => a[0]).lastIndexOf("clearRect"));
  const mv2 = passe2.find((a) => a[0] === "moveTo");
  const R2 = FORMATS_HEX.hex_f90.p / Math.sqrt(3);
  ok("7.7 côté plat en haut : premier sommet à droite du centre", proche(mv2[1], (g2.centres[0].x + R2) * k2, 1e-6) && proche(mv2[2], g2.centres[0].y * k2, 1e-6), JSON.stringify(mv2));
  ok("7.8 le compteur suit", champ("tuiles").textContent === T("decoupehex.grille.tuiles", { n: 24 }));
  await fermerTout();
}

// 8 les huit formats, le nom, le verso
{
  const b = banc({ depart: { colonnes: 2, rangees: 2 } }); b.ouvrir(); await attendre();
  const opts = champ("format").children;
  ok("8.1 huit formats", opts.length === 8 && opts.map((o) => o.value).join() === Object.keys(FORMATS_HEX).join(), opts.map((o) => o.value).join());
  ok("8.2 libellé « 90 mm, pointe en haut »", opts.find((o) => o.value === "hex_p90").textContent === "90 mm, pointe en haut");
  ok("8.3 format de départ 90 mm pointe", champ("format").value === "hex_p90");
  ok("8.4 nom proposé « Plateau — fond »", champ("nom").value === "Plateau — fond", champ("nom").value);
  saisir("nom", "  Mon plateau ");
  saisir("verso", " dos.png ");
  saisir("format", "hex_f635");
  creer().emet("click"); await attendre(); await attendre();
  const c = b.posts[0].corps;
  ok("8.5 nom rogné, verso_commun rogné, format choisi", c.name === "Mon plateau" && c.verso_commun === "dos.png" && c.format === "hex_f635" && c.colonnes === 2, JSON.stringify(c));
  ok("8.6 cadrage par défaut centré, zoom 1", JSON.stringify(c.cadrage) === JSON.stringify({ zoom: 1, x: 0.5, y: 0.5 }), JSON.stringify(c.cadrage));
  await b.promesse;
  await fermerTout();
  const d = banc({ depart: { colonnes: 2, rangees: 2 } }); d.ouvrir(); await attendre();
  saisir("nom", "   ");
  creer().emet("click"); await attendre(); await attendre();
  ok("8.7 nom vide : omis (le serveur propose le sien) ; verso vide : omis", !("name" in d.posts[0].corps) && !("verso_commun" in d.posts[0].corps), JSON.stringify(d.posts[0].corps));
  await d.promesse;
  await fermerTout();
}

// 9 fermer, popup bloquée, un seul dialogue
{
  const b = banc(); const p = b.ouvrir(); await attendre();
  touche("Escape");
  ok("9.1 Échap ferme et rend null", (await p) === null && !voile());
  ok("9.2 écouteur du clavier retiré", (docListeners.keydown || []).length === 0);
  const c = banc(); const p2 = c.ouvrir(); await attendre();
  champ("fermer").emet("click");
  ok("9.3 la croix ferme et rend null", (await p2) === null && !voile());
  const d = banc(); const p3 = d.ouvrir(); await attendre();
  champ("annuler").emet("click");
  ok("9.4 Annuler ferme et rend null", (await p3) === null && !voile());
  const e = banc(); e.ouvrir(); await attendre();
  const f = banc(); f.ouvrir(); await attendre();
  ok("9.5 rouvrir remplace le dialogue (un seul voile)", tous(racine, estVoile).length === 1);
  ok("9.6 l'ancien est résolu à null", (await e.promesse) === null);
  await fermerTout();

  const g = banc({ depart: { colonnes: 2, rangees: 2 } });
  retourOpen = null;
  g.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("9.7 ouverture bloquée : le dialogue reste, avec un lien", !!voile() && champ("message").textContent.includes(T("decoupehex.dialogue.ouvert_bloque")));
  const lien = champ("lien");
  ok("9.8 le lien mène au jeu", !!lien && lien.href === "/cardforge/?deck=deck_00000042" && lien.attrs.target === "_blank" && lien.attrs.rel === "noopener", lien && lien.href);
  const r = await g.promesse;
  ok("9.9 le résultat est rendu malgré tout", r && r.deck.id === "deck_00000042");
  await fermerTout();
}

// 10 la feuille de style est posée une fois
{
  const b = banc(); b.ouvrir(); await attendre();
  const liens = tous(entete, (e) => e.tag === "link");
  ok("10.1 une feuille liée dans l'en-tête", liens.length === 1 && /dz-decoupe-hex\.css$/.test(liens[0].href), liens.map((l) => l.href).join());
  await fermerTout();
  const c = banc(); c.ouvrir(); await attendre();
  ok("10.2 pas de doublon au second dialogue", tous(entete, (e) => e.tag === "link").length === 1);
  await fermerTout();
}

// 11 après une ouverture bloquée, le jeu existe : plus rien ne relance la création
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  retourOpen = null;
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("11.1 « Créer » reste désactivé après la création", creer().disabled === true);
  saisir("zoom", 1.3); saisir("colonnes", 5); saisir("nom", "autre"); saisir("format", "hex_p50");
  ok("11.2 modifier un champ ne le réactive pas", creer().disabled === true);
  creer().emet("click"); await attendre(); await attendre();
  ok("11.3 un clic ne poste pas un second jeu", b.posts.length === 1 && b.images.length === 1, b.posts.length);
  ok("11.4 les réglages sont inertes", ["format", "colonnes", "rangees", "zoom", "nom", "verso"].every((k) => champ(k).disabled === true));
  champ("apercu").emet("wheel", { deltaY: -100 });
  champ("apercu").emet("keydown", { key: "ArrowLeft" });
  ok("11.5 molette et flèches inertes", Number(champ("zoom").value) === 1.3 && creer().disabled === true);
  ok("11.6 le lien reste là", !!champ("lien"));
  await fermerTout();
}

// 12 le focus : piégé dans le dialogue, rendu à la fermeture
{
  const avant = new FE("button");
  avant.rendu = 0; avant.focus = function () { this.rendu++; globalThis.document.activeElement = this; };
  globalThis.document.activeElement = avant;
  const b = banc(); const p = b.ouvrir(); await attendre();
  const cibles = tous(voile(), (e) => !e.disabled && (e.tag === "input" || e.tag === "select" || e.tag === "button" || e.tag === "a" || (e.tag === "canvas" && e.attrs.tabindex != null)));
  ok("12.1 le focus part dans le dialogue", cibles.includes(globalThis.document.activeElement));
  cibles[cibles.length - 1].focus();
  const t1 = touche("Tab");
  ok("12.2 Tab depuis le dernier revient au premier", t1.vu === true && globalThis.document.activeElement === cibles[0], String(globalThis.document.activeElement && globalThis.document.activeElement.tag));
  const t2 = touche("Tab", { shiftKey: true });
  ok("12.3 Maj+Tab depuis le premier va au dernier", t2.vu === true && globalThis.document.activeElement === cibles[cibles.length - 1]);
  touche("Tab");
  touche("Tab");
  ok("12.4 Tab avance d'un champ", globalThis.document.activeElement === cibles[1]);
  ok("12.5 le canvas est atteignable au clavier", cibles.some((e) => e.tag === "canvas"));
  touche("Escape");
  await p;
  ok("12.6 le focus est rendu à l'élément d'avant", avant.rendu === 1 && globalThis.document.activeElement === avant, avant.rendu);
  globalThis.document.activeElement = null;
}

// 13 réseau tombé, flèches, remplacement en cours de création
{
  const b = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  b.args.fetch = async () => { throw new TypeError("Failed to fetch"); };
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("13.1 fetch rejeté : phrase traduite, pas le texte du navigateur", champ("message").textContent === T("decoupehex.erreur.reseau") && !!voile(), champ("message").textContent);
  ok("13.2 « Créer » de nouveau actif", creer().disabled === false);
  await fermerTout();

  const c = banc({ largeur: 8000, hauteur: 8000, depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  c.ouvrir(); await attendre();
  const cv = champ("apercu");
  ok("13.3 l'aria-label annonce les flèches", /fl[eè]ches/.test(cv.attrs["aria-label"]) && cv.attrs["aria-label"] === T("decoupehex.cadrage.apercu"));
  const k1 = cv.emet("keydown", { key: "ArrowDown" });
  cv.emet("keydown", { key: "ArrowRight" });
  cv.emet("keydown", { key: "a" });
  creer().emet("click"); await attendre(); await attendre();
  const cad = c.posts[0].corps.cadrage;
  ok("13.4 flèches : pas de 0,02, l'image suit la flèche", k1.vu === true && proche(cad.y, 0.48, 1e-9) && proche(cad.x, 0.48, 1e-9), JSON.stringify(cad));
  await c.promesse;
  await fermerTout();

  let debloque; const attente = new Promise((rs) => { debloque = rs; });
  const e = banc({ depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  e.args.fournirImage = async () => { await attente; return "fond.png"; };
  const p1 = e.ouvrir(); await attendre();
  creer().emet("click"); await attendre();
  const f = banc(); const p2 = f.ouvrir(); await attendre();
  ok("13.5 pas de second dialogue pendant une création", tous(racine, estVoile).length === 1);
  debloque(); await attendre(); await attendre();
  const [r1, r2] = [await p1, await p2];
  ok("13.6 le dialogue en cours n'est pas résolu à null ; l'appel rend sa promesse", r1 && r1.deck.id === "deck_00000042" && r2 && r2.deck.id === r1.deck.id, JSON.stringify([r1, r2]));
  await fermerTout();
}

// 14 un lab qui rogne lui-même l'image (Vectorlab) : { nom, cadrage } rendu, cadrage posté, cache par cadrage, crochet ppp
{
  const neutre = { zoom: 1, x: 0.5, y: 0.5 };
  const b = banc({ largeur: 1920, hauteur: 1080, depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 2, x: 0.3, y: 0.6 } });
  b.args.fournirImage = async (e) => { b.images.push(e); return { nom: "region_" + b.images.length + ".png", cadrage: neutre }; };
  b.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("14.1 fournirImage reçoit le cadrage courant", b.images.length === 1 && JSON.stringify(b.images[0].cadrage) === JSON.stringify({ zoom: 2, x: 0.3, y: 0.6 }), JSON.stringify(b.images[0]));
  ok("14.2 le POST porte le cadrage NEUTRE rendu par le lab, pas celui du dialogue", b.posts.length === 1 && b.posts[0].corps.image === "region_1.png" && JSON.stringify(b.posts[0].corps.cadrage) === JSON.stringify(neutre), JSON.stringify(b.posts[0] && b.posts[0].corps));
  await b.promesse;
  await fermerTout();

  // le cache est clé sur l'étendue ET le cadrage : même cadrage = même image, autre zoom = nouvelle image
  const c = banc({ largeur: 1920, hauteur: 1080, depart: { format: "hex_p90", colonnes: 6, rangees: 4, zoom: 2, x: 0.3, y: 0.6 } });
  c.args.fournirImage = async (e) => { c.images.push(e); return { nom: "region_" + c.images.length + ".png", cadrage: neutre }; };
  c.reponse = (k) => (k <= 2 ? { ok: false, status: 400, json: async () => ({ detail: "non" }) } : { ok: true, status: 200, json: async () => ({ deck: { id: "deck_00000009" }, tuiles: [] }) });
  c.ouvrir(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  creer().emet("click"); await attendre(); await attendre();
  ok("14.3 même étendue, même cadrage : l'image rangée est réutilisée", c.images.length === 1 && c.posts[1].corps.image === "region_1.png", c.images.length);
  saisir("zoom", 3);
  creer().emet("click"); await attendre(); await attendre();
  ok("14.4 autre zoom : le lab rastérise une autre région (nouvelle image)", c.images.length === 2 && c.posts[2].corps.image === "region_2.png" && c.images[1].cadrage.zoom === 3, JSON.stringify(c.images));
  await c.promesse;
  await fermerTout();

  // le crochet ppp : le chiffre est celui du lab, l'avertissement n'apparaît que sous 300
  const d = banc({ largeur: 1920, hauteur: 1080, depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  let appels = [];
  d.args.ppp = (rect, largeurMm) => { appels.push([rect, largeurMm]); return 300; };
  d.ouvrir(); await attendre();
  const g = grille("hex_p90", 6, 4);
  const r = cadrageCouvrant(1920, 1080, g.largeurMm, g.hauteurMm, 1, 0.5, 0.5);
  ok("14.5 le crochet reçoit le cadre courant {x, y, w, h} et la largeur imprimée", appels.length >= 1 && proche(appels[0][0].w, r.w) && proche(appels[0][0].h, r.h) && proche(appels[0][1], g.largeurMm), JSON.stringify(appels[0]));
  ok("14.6 300 ppp annoncés : pas d'avertissement (le chiffre de l'image du lab, 185, est ignoré)", champ("ppp").textContent === T("decoupehex.cadrage.ppp", { ppp: 300 }) && champ("alerte").hidden === true && champ("alerte").textContent === "", champ("ppp").textContent);
  await fermerTout();
  const e = banc({ largeur: 1920, hauteur: 1080, depart: { format: "hex_p90", colonnes: 6, rangees: 4 } });
  e.args.ppp = () => 74.4;
  e.ouvrir(); await attendre();
  ok("14.7 la borne mord (74 ppp annoncés) : l'avertissement paraît", champ("ppp").textContent === T("decoupehex.cadrage.ppp", { ppp: 74 }) && champ("alerte").hidden === false && champ("alerte").textContent === T("decoupehex.cadrage.ppp_faible", { min: 300 }), champ("alerte").textContent);
  ok("14.8 l'avertissement ne dit plus de dézoomer (impossible : zoom min 1)", !/dézoom/i.test(champ("alerte").textContent) && /moins de tuiles/.test(champ("alerte").textContent), champ("alerte").textContent);
  await fermerTout();
}

if (echecs.length) {
  console.log("ÉCHECS (" + echecs.length + ") :\n- " + echecs.join("\n- "));
  console.log(n - echecs.length + "/" + n + " vérifications");
  process.exit(1);
}
console.log(n + "/" + n + " vérifications\nOK");
