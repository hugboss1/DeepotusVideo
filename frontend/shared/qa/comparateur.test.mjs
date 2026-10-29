// t337 (29/10/2026, C4 du lot Scenario) — dz-comparateur.js : le comparateur commun, joué sur un DOM simulé, puis
// dz-revue-plan.js (la revue du plan) contre des routes simulées, avec la VRAIE enveloppe dz-plafonds.js.
// Séries : rideau (curseur, glisser, Maj+flèches, bornes), O / C, vidéo (pas à pas ← →, synchro, lecture, bornes),
// image (← → sans effet), saisie ignorée, Échap ferme et rend le focus, aucun innerHTML ; revue : état vide (400),
// mesures (dérive, structure, profondeur dite non mesurée, identité), devis, avis confirmé (confirme_cout + max_usd),
// refus de confirmation (rien ne part), 409 (nouveau devis), 503 (clé dite), comparer → comparateur ; anglais.
// Lancer : node frontend/shared/qa/comparateur.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const CMP = readFileSync(new URL("../dz-comparateur.js", import.meta.url), "utf8");
const REV = readFileSync(new URL("../dz-revue-plan.js", import.meta.url), "utf8");
const PLAFONDS = readFileSync(new URL("../dz-plafonds.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const tick = () => new Promise((r) => setTimeout(r, 5));
const ticks = async (k = 8) => { for (let i = 0; i < k; i++) await tick(); };

const ACTIF = { el: null };
class Noeud {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {};
    this._t = ""; this.value = ""; this.style = {}; this.currentTime = 0; this.duration = NaN; this.joue = false;
  }
  get firstChild() { return this.children[0] || null; }
  get lastChild() { return this.children[this.children.length - 1] || null; }
  get parentNode() { return this.parent; }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "value") this.value = String(v); if (k === "type") this.type = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(v) { throw new Error("innerHTML interdit"); }
  get innerHTML() { throw new Error("innerHTML interdit"); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); }
  focus() { ACTIF.el = this; }
  getBoundingClientRect() { return { left: 100, top: 0, width: 400, height: 300 }; }
  setPointerCapture() { this.capture = true; }
  play() { this.joue = true; return Promise.resolve(); }
  pause() { this.joue = false; }
  fire(t, extra = {}) {
    const ev = Object.assign({ type: t, target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, stopPropagation() {} }, extra);
    (this.ec[t] || []).forEach((f) => f(ev));
    return ev;
  }
  click() { this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tous = (r, p) => [...r.tous()].filter(p);
const cmpM = (r, v) => tous(r, (x) => x.attrs["data-dz-cmp"] === v)[0];
const revM = (r, v) => tous(r, (x) => x.attrs["data-dz-revue"] === v)[0];
const revTous = (r, v) => tous(r, (x) => x.attrs["data-dz-revue"] === v);
const visible = (x) => !!x && !x.hasAttribute("hidden");

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const dzTde = (lang) => (cle, vars) => {
  const e = D[cle];
  if (!e) return "«" + cle + "»";
  let s = e[lang] || e.fr;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
  return s;
};
const rep = (status, json) => new Response(JSON.stringify(json === undefined ? {} : json), { status, headers: { "Content-Type": "application/json" } });

function monde({ lang = "fr", routes = {}, confirmer = true } = {}) {
  const appels = [], dialogues = [], toasts = [];
  const doc = {
    createElement: (t) => new Noeud(t), createElementNS: (ns, t) => new Noeud(t), body: new Noeud("body"), ec: {},
    get activeElement() { return ACTIF.el; },
    addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); },
    removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((g) => g !== f); },
    touche(key, extra = {}) {
      const ev = Object.assign({ type: "keydown", key, target: extra.target || ACTIF.el || doc.body, defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; }, stopPropagation() {} }, extra);
      (this.ec.keydown || []).slice().forEach((f) => f(ev));
      // puis la bulle jusqu'à la racine du comparateur (le gestionnaire de la racine)
      let x = ev.target; while (x) { (x.ec.keydown || []).forEach((f) => f(ev)); x = x.parent; }
      return ev;
    }
  };
  const ctx = {
    document: doc, console, setTimeout, clearTimeout, Promise, JSON, Response, Headers, Request, URL,
    fetch: async (url, init = {}) => {
      const m = (init.method || "GET").toUpperCase();
      const cle = m + " " + String(url);
      appels.push({ cle, corps: init.body ? JSON.parse(init.body) : null });
      const f = routes[cle];
      if (!f) return rep(404, { detail: "route absente " + cle });
      return f(init.body ? JSON.parse(init.body) : null, appels);
    }
  };
  ctx.window = ctx;
  ctx.dzT = dzTde(lang);
  ctx.dzLang = () => lang;
  ctx.__dzDialogue = { confirmer: async (msg, o) => { dialogues.push({ msg, o }); return confirmer; } };
  vm.createContext(ctx);
  vm.runInContext(PLAFONDS, ctx);
  vm.runInContext(CMP, ctx);
  vm.runInContext(REV, ctx);
  return { ctx, doc, appels, dialogues, toasts, toast: (m, e) => toasts.push({ m, e }) };
}

/* ───────── 1. le comparateur : images ───────── */
{
  const W = monde();
  const hote = new Noeud("div");
  const c = W.ctx.__dzComparateur.monter(hote, { a: { src: "/api/images/ref.png", libelle: "Référence" }, b: { src: "/api/images/prod.png" } });
  const r = c.racine, b = cmpM(r, "b"), cur = cmpM(r, "curseur");
  ok("img1 deux images, A dessous, B dessus rognée à 50 %, curseur range accessible", cmpM(r, "a").tagName === "IMG"
     && b.tagName === "IMG" && b.style.clipPath === "inset(0 0 0 50%)" && cur.attrs.type === "range"
     && cur.attrs["aria-label"] === "Position du rideau" && cmpM(r, "etiquette-a").textContent === "Référence"
     && cmpM(r, "etiquette-b").textContent === "Résultat", b.style.clipPath);
  ok("img2 pas de commandes vidéo pour deux images", !cmpM(r, "precedente") && !cmpM(r, "lecture") && c.etat().video === false);
  cur.value = "30"; cur.fire("input");
  ok("img3 le curseur déplace le rideau et la ligne", b.style.clipPath === "inset(0 0 0 30%)" && cmpM(r, "ligne").style.left === "30%"
     && cur.attrs["aria-valuetext"] === "30 % d'original à gauche");
  const sc = cmpM(r, "scene");
  sc.fire("pointerdown", { clientX: 400, pointerId: 1 }); sc.fire("pointermove", { clientX: 200 }); sc.fire("pointerup");
  sc.fire("pointermove", { clientX: 480 });
  ok("img4 glisser sur l'image : 75 % puis 25 %, plus rien après le relâché, pointeur capturé",
     c.position() === 25 && sc.capture === true, c.position());
  c.position(-40); const p0 = c.position(); c.position(140);
  ok("img5 rideau borné à 0-100", p0 === 0 && c.position() === 100);
  c.position(50);
  const evO = c.touche({ key: "o", target: r, preventDefault() { this.defaultPrevented = true; } });
  ok("img6 O : l'original seul (B caché, curseur inactif, bouton pressé)", c.mode() === "original" && b.hasAttribute("hidden")
     && cmpM(r, "curseur").hasAttribute("disabled") && cmpM(r, "original").attrs["aria-pressed"] === "true" && evO !== null);
  c.touche({ key: "C", target: r, preventDefault() {} });
  ok("img7 C : retour au rideau", c.mode() === "comparer" && !b.hasAttribute("hidden") && cmpM(r, "comparer").attrs["aria-pressed"] === "true");
  c.touche({ key: "ArrowRight", shiftKey: true, target: r, preventDefault() {} });
  ok("img8 Maj+→ : rideau +5 %", c.position() === 55);
  c.touche({ key: "ArrowLeft", target: r, preventDefault() {} });
  ok("img9 ← sans vidéo : sans effet", c.position() === 55 && c.mode() === "comparer");
  const champ = new Noeud("input"); champ.setAttribute("type", "text");
  c.touche({ key: "o", target: champ, preventDefault() {} });
  ok("img10 une touche tapée dans un champ de saisie est ignorée", c.mode() === "comparer");
  cmpM(r, "original").click();
  ok("img11 les boutons Original / Comparer valent les touches", c.mode() === "original");
  cmpM(r, "scene").fire("pointerdown", { clientX: 300, pointerId: 2 });
  ok("img12 glisser en mode original revient au rideau", c.mode() === "comparer" && c.position() === 50);
  c.detruire();
  ok("img13 detruire retire le comparateur", hote.children.length === 0);
}

/* ───────── 2. le comparateur : vidéos ───────── */
{
  const W = monde();
  const hote = new Noeud("div");
  const c = W.ctx.__dzComparateur.monter(hote, { a: { src: "/api/jobs/p/video" , type: "video" }, b: { src: "/rendu.mp4" }, fps: 24 });
  const r = c.racine, va = cmpM(r, "a"), vb = cmpM(r, "b");
  va.duration = 2.5; vb.duration = 2.5;
  ok("vid1 deux vidéos muettes (type explicite et extension), commandes image par image", va.tagName === "VIDEO" && vb.tagName === "VIDEO"
     && va.muted === true && !!cmpM(r, "precedente") && !!cmpM(r, "suivante") && c.etat().video === true);
  c.touche({ key: "ArrowRight", target: r, preventDefault() {} });
  ok("vid2 → : une image en avant, les DEUX vidéos au milieu de l'image 1", Math.abs(va.currentTime - 1.5 / 24) < 1e-9
     && va.currentTime === vb.currentTime && c.etat().image === 1, va.currentTime);
  cmpM(r, "suivante").click(); cmpM(r, "suivante").click();
  ok("vid3 le bouton « image suivante » vaut →, le compteur suit (image 4 / 60)", c.etat().image === 3
     && cmpM(r, "compteur").textContent === "image 4 / 60", cmpM(r, "compteur").textContent);
  c.touche({ key: "ArrowLeft", target: r, preventDefault() {} });
  ok("vid4 ← : une image en arrière", c.etat().image === 2);
  for (let i = 0; i < 5; i++) c.pas(-1);
  ok("vid5 borné à la première image", c.etat().image === 0);
  va.currentTime = 2.49; vb.currentTime = 2.49;
  c.pas(1);
  ok("vid6 borné à la dernière image (59)", c.etat().image === 59, c.etat().image);
  c.touche({ key: " ", target: r, preventDefault() {} });
  ok("vid7 Espace : les deux vidéos jouent ensemble, le bouton dit « Pause »", va.joue && vb.joue
     && cmpM(r, "lecture").textContent === "Pause");
  va.currentTime = 1.0; vb.currentTime = 0.5; va.fire("timeupdate");
  ok("vid8 B rattrape A à plus d'une demi-image d'écart", vb.currentTime === 1.0);
  c.pas(1);
  ok("vid9 le pas à pas met la lecture en pause", !va.joue && !vb.joue && cmpM(r, "lecture").textContent === "Lire");
  const cur = cmpM(r, "curseur");
  const t0 = va.currentTime;
  c.touche({ key: "ArrowRight", target: cur, preventDefault() {} });
  ok("vid10 → sur le curseur du rideau : laissé au curseur (pas d'image sautée)", va.currentTime === t0);
  ok("vid11 l'aide dit les raccourcis vidéo", cmpM(r, "aide").textContent.includes("← → : une image"));
}

/* ───────── 3. la boîte : Échap, focus, refus d'ouvrir sans médias ───────── */
{
  const W = monde({ lang: "en" });
  const avant = new Noeud("button"); avant.focus();
  const fini = W.ctx.__dzComparateur.ouvrir({ a: { src: "/a.png" }, b: { src: "/b.png" } });
  const voile = W.doc.body.children[0];
  ok("box1 la boîte s'ouvre (dialogue modal), en anglais", voile && voile.attrs.role === "dialog" && voile.attrs["aria-modal"] === "true"
     && cmpM(voile, "original").textContent === "Original (O)" && cmpM(voile, "etiquette-b").textContent === "Result"
     && W.ctx.__dzComparateur.ouvert() === true);
  W.doc.touche("o");
  ok("box2 O vaut dans toute la boîte, une seule fois", cmpM(voile, "racine").attrs["data-mode"] === "original");
  W.doc.touche("Escape");
  await_(fini);
  ok("box3 Échap ferme et rend le focus", W.doc.body.children.length === 0 && ACTIF.el === avant && W.ctx.__dzComparateur.ouvert() === false);
  const rien = await W.ctx.__dzComparateur.ouvrir({ a: { src: "" }, b: { src: "/b.png" } });
  ok("box4 sans les deux médias : rien ne s'ouvre", rien === null && W.doc.body.children.length === 0);
}
function await_() {}

/* ───────── 4. la revue du plan ───────── */
const MESURES = { date: "2026-10-29T10:00:00+00:00", temporel: { derive_images: 0, fiable: true, recalage: { derive_images: 2, fiable: true } },
  structure: { verdict: "proche", bords: { moyenne: 0.98, min: 0.97, pire_image: 11 }, luminance: { moyenne: 0.99, min: 0.98, pire_image: 3 },
               seuils: { bords: 0.35, luminance: 0.55 } },
  profondeur: { mesuree: false, raison: "…" }, images: 60, fps: "24/1",
  identite: [{ name: "Vane", vue: "front", ecart_couleur: 3.2, ecart_silhouette: 0.05, verdict: "stable" },
             { name: "Rook", vue: null }] };
const NOTE = { criteres: { mouvement: { note: 8, commentaire: "fidèle" }, cadrage: { note: 7, commentaire: "" }, style: { note: 6, commentaire: "" },
  personnages: { note: null, commentaire: "" }, lumiere: { note: 7, commentaire: "" }, artefacts: { note: 4, commentaire: "main" } },
  defauts: [{ gravite: "majeur", moment: "milieu", texte: "main à six doigts" }], synthese: "Fidèle.", moyenne: 6.4, usd: 0.0123,
  date: "2026-10-29T10:01:00+00:00" };
const SRC = (revue) => ({ shot_id: "s1", rendu: { job_id: "r1", url: "/api/jobs/r1/video" }, previs: { job_id: "p1", url: "/api/jobs/p1/video" },
  fps: "24/1", revue, avertissement: "Avis… pas une garantie." });

{
  const W = monde({ routes: { "GET /api/shots/s1/revue": () => rep(400, { detail: "Ce plan n'a pas de rendu « Previs → plan » à revoir." }) } });
  W.ctx.__dzRevuePlan.ouvrir({ shot: { id: "s1" }, numero: 3, toast: W.toast });
  await ticks();
  const v = W.doc.body.children[0];
  ok("rev1 sans rendu previs : un état vide qui explique quoi faire, ni mesures ni avis", visible(revM(v, "vide"))
     && revM(v, "vide").textContent.includes("lancez d'abord Previs → plan") && !visible(revM(v, "sec-mesures"))
     && !visible(revM(v, "sec-avis")) && !W.appels.some((a) => a.cle.includes("/devis")), revM(v, "vide").textContent);
}

{
  let devisUsd = 0.0123;
  const routes = {
    "GET /api/shots/s1/revue": () => rep(200, SRC({})),
    "POST /api/shots/s1/revue/devis": () => rep(200, { usd: devisUsd, disponible: true, raison: "", n_images: 4, style: true }),
    "POST /api/shots/s1/revue/mesurer": () => rep(200, SRC({ mesures: MESURES })),
    "POST /api/shots/s1/revue/note": (c) => rep(200, SRC({ mesures: MESURES, note: NOTE }))
  };
  const W = monde({ routes });
  W.ctx.__dzRevuePlan.ouvrir({ shot: { id: "s1" }, numero: 3, toast: W.toast });
  await ticks();
  const v = W.doc.body.children[0];
  ok("rev2 ouverture : rien de rangé, le devis lu (gratuit), le bouton porte le montant, l'avertissement dit",
     !visible(revM(v, "mesures")) && revM(v, "prix").textContent === "Devis : 0,0123 $ (4 images envoyées)"
     && revM(v, "avis-rendu").hasAttribute("hidden") && revM(v, "intro").textContent.includes("pas une garantie")
     && v.attrs["aria-label"] === "Revue du plan 3"
     && tous(v, (x) => x.attrs["data-dz-revue"] === "avis" && x.tagName === "BUTTON")[0].textContent === "Demander l'avis · 0,0123 $");
  revM(v, "mesurer").click();
  await ticks();
  const lignes = revM(v, "mesures").textContent;
  ok("rev3 mesures : dérive restante 0 et recalage +2 rappelé, structure proche chiffrée, profondeur NON mesurée dite, identité et angle mort",
     lignes.includes("Dérive temporelle restante : 0 image.") && lignes.includes("(recalée au rendu : +2 images)")
     && lignes.includes("bords 0,98 (pire 0,97, image 12)") && lignes.includes("Profondeur : non mesurée")
     && lignes.includes("Vane : stable · couleur ΔE 3,2") && lignes.includes("Rook : aucune vue de référence")
     && lignes.includes("Angle mort") && revM(v, "mesurer").textContent === "Mesurer à nouveau", lignes);
  W.ctx.__dzDialogue.confirmer = async (m) => { W.dialogues.push(m); return false; };
  tous(v, (x) => x.attrs["data-dz-revue"] === "avis" && x.tagName === "BUTTON")[0].click();
  await ticks();
  ok("rev4 avis refusé à la confirmation : rien ne part", W.dialogues.length === 1 && !W.appels.some((a) => a.cle.endsWith("/note")));
  W.ctx.__dzDialogue.confirmer = async (m) => { W.dialogues.push(m); return true; };
  tous(v, (x) => x.attrs["data-dz-revue"] === "avis" && x.tagName === "BUTTON")[0].click();
  await ticks();
  const note = W.appels.find((a) => a.cle === "POST /api/shots/s1/revue/note");
  const av = revM(v, "avis-rendu");
  ok("rev5 avis confirmé (montant dit) : confirme_cout + max_usd du devis ; notes /10, défauts, synthèse, avertissement",
     W.dialogues[1].includes("0,0123 $") && W.dialogues[1].includes("pas une garantie")
     && note && note.corps.confirme_cout === true && note.corps.max_usd === 0.0123 && visible(av)
     && av.textContent.includes("Mouvement8 / 10fidèle") && av.textContent.includes("Personnages—")
     && av.textContent.includes("Majeur · milieu — main à six doigts") && av.textContent.includes("Moyenne : 6,4 / 10")
     && av.textContent.includes("pas une garantie") && revTous(v, "a-critere").length === 6, av.textContent);
  revM(v, "comparer").click();
  await ticks();
  const boites = W.doc.body.children;
  const cv = boites[boites.length - 1];
  ok("rev6 « Comparer previs / rendu » ouvre le comparateur commun : previs à gauche, rendu à droite, vidéos",
     cv.attrs["data-dz-cmp"] === "voile" && cmpM(cv, "a").attrs.src === "/api/jobs/p1/video" && cmpM(cv, "b").attrs.src === "/api/jobs/r1/video"
     && cmpM(cv, "etiquette-a").textContent === "Previs" && cmpM(cv, "a").tagName === "VIDEO");
  W.doc.touche("Escape");
  ok("rev7 Échap ferme d'abord le comparateur, la revue reste", W.doc.body.children.length === 1 && W.doc.body.children[0] === v);
  W.doc.touche("Escape");
  ok("rev8 Échap ferme ensuite la revue", W.doc.body.children.length === 0);
}

{
  const routes = {
    "GET /api/shots/s1/revue": () => rep(200, SRC({})),
    "POST /api/shots/s1/revue/devis": () => rep(200, { usd: 0.01, disponible: true, raison: "", n_images: 4 }),
    "POST /api/shots/s1/revue/note": () => rep(409, { detail: { message: "Le coût a changé", usd: 0.02, devis: { usd: 0.02, disponible: true, n_images: 4 } } })
  };
  const W = monde({ routes });
  W.ctx.__dzRevuePlan.ouvrir({ shot: { id: "s1" }, numero: 1, toast: W.toast });
  await ticks();
  const v = W.doc.body.children[0];
  tous(v, (x) => x.attrs["data-dz-revue"] === "avis" && x.tagName === "BUTTON")[0].click();
  await ticks();
  ok("rev9 409 : le nouveau devis est montré, rien n'est rendu", revM(v, "prix").textContent.includes("0,02 $")
     && revM(v, "erreur").textContent.includes("Le coût a changé (0,02 $)") && revM(v, "avis-rendu").hasAttribute("hidden"));
}

{
  const routes = {
    "GET /api/shots/s1/revue": () => rep(200, Object.assign(SRC({}), { previs: null })),
    "POST /api/shots/s1/revue/devis": () => rep(200, { usd: 0, disponible: false, raison: "cle", n_images: 3, message: "ajoutez la clé Anthropic" }),
    "POST /api/shots/s1/revue/note": () => rep(503, { detail: "ajoutez la clé Anthropic dans Réglages" })
  };
  const W = monde({ routes, lang: "en" });
  W.ctx.__dzRevuePlan.ouvrir({ shot: { id: "s1" }, numero: 1, toast: W.toast });
  await ticks();
  const v = W.doc.body.children[0];
  const btn = tous(v, (x) => x.attrs["data-dz-revue"] === "avis" && x.tagName === "BUTTON")[0];
  ok("rev10 sans clé (anglais) : devis indisponible, la clé dite, bouton JAMAIS grisé ; sans previs, Comparer grisé et dit",
     revM(v, "prix").textContent === "Quote: unavailable without an Anthropic key" && visible(revM(v, "mention"))
     && !btn.hasAttribute("disabled") && btn.textContent === "Ask for the opinion"
     && revM(v, "comparer").hasAttribute("disabled") && visible(revM(v, "sans-previs")));
  btn.click();
  await ticks();
  ok("rev11 503 au clic : la raison dite, rien d'affiché comme avis", revM(v, "erreur").textContent.includes("Anthropic")
     && revM(v, "avis-rendu").hasAttribute("hidden"));
}

{
  const W = monde({ routes: { "GET /api/shots/s1/revue": () => rep(200, SRC({ mesures: MESURES, note: NOTE })),
                              "POST /api/shots/s1/revue/devis": () => rep(200, { usd: 0.01, disponible: true, n_images: 4 }) } });
  W.ctx.__dzRevuePlan.ouvrir({ shot: { id: "s1" }, numero: 1 });
  await ticks();
  const v = W.doc.body.children[0];
  ok("rev12 une revue rangée s'affiche telle quelle à l'ouverture : aucune mesure ni avis relancé",
     visible(revM(v, "mesures")) && visible(revM(v, "avis-rendu"))
     && !W.appels.some((a) => a.cle.endsWith("/mesurer") || a.cle.endsWith("/note")));
}

const clesJs = new Set([...CMP.matchAll(/T\("((?:comparateur)\.[a-z_.]+)"/g), ...REV.matchAll(/"(revueplan\.[a-z_.]+)"/g)].map((m) => m[1]).filter((k) => !k.endsWith(".")));
const manquantes = [...clesJs].filter((k) => !D[k]);
ok("cles toutes les clés employées existent dans le dictionnaire assemblé", manquantes.length === 0, manquantes.join(", "));

if (echecs.length) { console.log(echecs.map((e) => "  FAIL  " + e).join("\n")); }
console.log(`=== ${n - echecs.length} passed, ${echecs.length} failed ===`);
process.exit(echecs.length ? 1 : 0);
