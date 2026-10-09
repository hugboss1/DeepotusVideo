// mod-trace.js — t156 (parité L6) : outils Plume (P) et Sélection de tracé (A), panneau Tracés.
// Plume (amont vector_ui.rs) : clic = sommet d'angle, glisser = sommet lisse (poignées symétriques), clic sur le premier
// sommet = fermer, Entrée = terminer, Échap = abandonner, Ctrl+Entrée = sélection ; rien n'est envoyé avant la fin :
// mode Tracé -> path.set {name: "work"} (« Work Path »), mode Forme -> shape.create {kind: "path"}. Sélection de tracé :
// glisser = déplacer le tracé cible (calque de forme : shape.edit {move} ; sinon le tracé de travail). Tracés : lignes
// lues par path.list (enregistrés, de travail, du calque) ; clic = montrer le tracé sur la toile ; pied : remplir,
// contour, sélection, tracé depuis la sélection, nouveau, supprimer. Fonctions PURES exportées (qa/trace.test.mjs).
import { demanderNom } from "./mod-nommer.js";

export const TOLERANCE_FERMER = 6;            // px écran (amont)
const arr = (v) => Math.round(v * 100) / 100;
const pt = (p) => [arr(p[0]), arr(p[1])];

/* ── plume ── */
export const noeudAngle = (p) => ({ anchor: [p[0], p[1]], in: [p[0], p[1]], out: [p[0], p[1]], smooth: false });
// Glisser depuis le dernier sommet : poignée de sortie sous le pointeur, poignée d'entrée symétrique (sommet lisse).
export function tirerPoignee(noeuds, p) {
  if (!noeuds.length) return noeuds;
  const n = noeuds[noeuds.length - 1], a = n.anchor;
  const out = [p[0], p[1]], inn = [2 * a[0] - p[0], 2 * a[1] - p[1]];
  return [...noeuds.slice(0, -1), { anchor: a, in: inn, out, smooth: Math.hypot(p[0] - a[0], p[1] - a[1]) > 0.5 }];
}
// Le point écran s ferme-t-il le tracé (au moins deux sommets, près du premier) ?
export function fermeLeTrace(noeuds, s, ecran, tol = TOLERANCE_FERMER) {
  if (noeuds.length < 2) return false;
  const e = ecran(noeuds[0].anchor[0], noeuds[0].anchor[1]);
  return Math.hypot(e.x - s.x, e.y - s.y) <= tol;
}
export function chemin(noeuds, ferme) {
  return { subpaths: [{ closed: !!ferme, op: "combine", knots: noeuds.map((n) => ({ anchor: pt(n.anchor), in: pt(n.in), out: pt(n.out), smooth: !!n.smooth })) }],
    fillRule: "nonzero" };
}
// La commande de fin de tracé, ou null (moins de deux sommets).
export function commandePlume(mode, noeuds, ferme, fg = "#000000") {
  if (noeuds.length < 2) return null;
  const path = chemin(noeuds, ferme);
  if (mode === "forme") {
    return { command: "shape.create", params: { kind: "path", path, fill: ferme ? fg : null, stroke: ferme ? null : { width: 1, color: fg } } };
  }
  return { command: "path.set", params: { name: "work", path } };
}
export const MODES_PLUME = ["trace", "forme"];

/* ── chemins (affichage, déplacement) ── */
// Chemin du moteur -> attribut d SVG, par `ecran(x, y)` -> {x, y} (courbes de Bézier entre sommets).
export function dChemin(path, ecran) {
  if (!path || !Array.isArray(path.subpaths)) return "";
  const k = (n) => (Array.isArray(n) ? { anchor: n, in: n, out: n } : n);
  const P = (p) => { const e = ecran(p[0], p[1]); return arr(e.x) + " " + arr(e.y); };
  return path.subpaths.map((sp) => {
    const ns = (sp.knots || []).map(k);
    if (!ns.length) return "";
    let d = "M" + P(ns[0].anchor);
    const seg = (a, b) => " C" + P(a.out) + " " + P(b.in) + " " + P(b.anchor);
    for (let i = 1; i < ns.length; i++) d += seg(ns[i - 1], ns[i]);
    if (sp.closed && ns.length > 1) d += seg(ns[ns.length - 1], ns[0]) + " Z";
    return d;
  }).join(" ");
}
export function deplacerChemin(path, dx, dy) {
  const m = (p) => [arr(p[0] + dx), arr(p[1] + dy)];
  return { ...path, subpaths: (path.subpaths || []).map((sp) => ({ ...sp, knots: (sp.knots || []).map((n) => (Array.isArray(n) ? m(n)
    : { ...n, anchor: m(n.anchor), in: m(n.in || n.anchor), out: m(n.out || n.anchor) })) })) };
}
// Bornes [x0, y0, x1, y1] des ancres et poignées (vignettes).
export function bornes(path) {
  const xs = [], ys = [];
  for (const sp of (path && path.subpaths) || []) for (const n of sp.knots || []) {
    for (const p of Array.isArray(n) ? [n] : [n.anchor, n.in || n.anchor, n.out || n.anchor]) { xs.push(p[0]); ys.push(p[1]); }
  }
  return xs.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : null;
}
// Lignes du panneau Tracés depuis path.list : enregistrés, puis de travail, puis celui du calque.
export function lignesTraces(liste) {
  if (!liste) return [];
  const l = (liste.paths || []).map((p) => ({ nom: p.name, cle: p.name, type: "enregistre" }));
  if (liste.workPath) l.push({ nom: null, cle: "work", type: "travail" });
  if (liste.layerPath) l.push({ nom: liste.layerPath.name, cle: "layer", type: "calque", calque: liste.layerPath.layer });
  return l;
}
// Cible de la Sélection de tracé : le calque de forme actif, sinon le tracé de travail.
export function cibleSelection(doc, liste) {
  const actif = doc && (doc.layers || []).find((x) => x.id === doc.activeLayer);
  if (actif && actif.kind === "Shape") return { type: "forme", calque: actif.id };
  if (liste && liste.workPath) return { type: "travail" };
  return null;
}
export function commandeDeplacement(cible, dx, dy, pathTravail) {
  if (!cible || (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5)) return null;
  if (cible.type === "forme") return { command: "shape.edit", params: { layer: cible.calque, move: [arr(dx), arr(dy)] } };
  if (cible.type === "travail" && pathTravail) return { command: "path.set", params: { name: "work", path: deplacerChemin(pathTravail, dx, dy) } };
  return null;
}
// Prochain nom libre « <base> n » parmi les tracés enregistrés.
export function nomLibre(liste, base) {
  const pris = new Set(((liste && liste.paths) || []).map((p) => p.name));
  let n = 1;
  while (pris.has(base + " " + n)) n++;
  return base + " " + n;
}

/* ───────────── côté DOM ───────────── */

export function initTrace(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const NS = "http://www.w3.org/2000/svg";
  const fg = () => (PL.etat.couleurs && PL.etat.couleurs.fg) || "#000000";
  PL.etat.plume = { mode: "trace" };
  let noeuds = [], tire = false, survol = null;
  let liste = null, choisi = null, cheminChoisi = null, cheminTravail = null, revLue = null;
  let deplace = null;          // Sélection de tracé : {d0, path, cible}

  const redessiner = () => { if (PL.dessinerFourmis) PL.dessinerFourmis(); };
  function finir(versSelection = false) {
    const c = commandePlume(PL.etat.plume.mode, noeuds, false, fg());
    noeuds = []; tire = false; redessiner();
    if (!c) return;
    PL.executer(c.command, c.params).then((r) => { if (versSelection && r && r.ok && c.command === "path.set") PL.executer("path.toSelection", { name: "work" }); });
  }
  PL.gestes.pen = {
    appui(p) {
      if (fermeLeTrace(noeuds, { x: p.sx, y: p.sy }, PL.vue.versEcran)) {
        const c = commandePlume(PL.etat.plume.mode, noeuds, true, fg());
        noeuds = []; redessiner();
        if (c) PL.executer(c.command, c.params);
        return;
      }
      noeuds = [...noeuds, noeudAngle([p.x, p.y])]; tire = true; redessiner();
    },
    bouger(p) { if (tire) { noeuds = tirerPoignee(noeuds, [p.x, p.y]); redessiner(); } },
    relacher() { tire = false; },
    survol(p) { survol = [p.x, p.y]; if (noeuds.length) redessiner(); },
    touche(ev) {
      if (!noeuds.length) return false;
      if (ev.key === "Enter") { finir(false); return true; }
      if (ev.key === "Escape") { noeuds = []; redessiner(); return true; }
      return false;
    },
    quitter() { if (noeuds.length >= 2) finir(false); else { noeuds = []; } },
    annuler() { tire = false; },
  };
  // Ctrl+Entrée : le tracé en cours devient une sélection (le répartiteur ignore les touches avec Ctrl).
  document.addEventListener("keydown", (ev) => {
    if (PL.etat.outil === "pen" && noeuds.length && (ev.ctrlKey || ev.metaKey) && ev.key === "Enter") { ev.preventDefault(); finir(true); }
  });
  PL.gestes.pathSelection = {
    async appui(p) {
      await relireListe();
      const cible = cibleSelection(PL.etat.doc, liste);
      deplace = cible ? { d0: [p.x, p.y], cible, d: [0, 0] } : null;
    },
    bouger(p) { if (deplace) { deplace.d = [p.x - deplace.d0[0], p.y - deplace.d0[1]]; redessiner(); } },
    relacher() {
      if (!deplace) return;
      const c = commandeDeplacement(deplace.cible, deplace.d[0], deplace.d[1], cheminTravail);
      deplace = null; redessiner();
      if (c) PL.executer(c.command, c.params);
    },
    annuler() { deplace = null; redessiner(); },
    quitter() { deplace = null; },
  };

  // Dessins sur la toile : tracé de la plume (et sa ligne élastique), tracé choisi dans le panneau, tracé déplacé.
  PL.dessinsSup = PL.dessinsSup || [];
  PL.dessinsSup.push((svg, el, ecran) => {
    if (PL.etat.outil === "pen" && noeuds.length) {
      svg.appendChild(el("path", { d: dChemin(chemin(noeuds, false), ecran), fill: "none" }, "trace-cours"));
      if (survol && !tire) {
        const a = ecran(noeuds[noeuds.length - 1].anchor[0], noeuds[noeuds.length - 1].anchor[1]), b = ecran(survol[0], survol[1]);
        svg.appendChild(el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y }, "trace-elastique"));
      }
      noeuds.forEach((n, i) => { const e = ecran(n.anchor[0], n.anchor[1]); svg.appendChild(el("rect", { x: e.x - 3, y: e.y - 3, width: 6, height: 6 }, i === noeuds.length - 1 ? "trace-ancre actif" : "trace-ancre")); });
      const n = noeuds[noeuds.length - 1];
      if (n.smooth) for (const h of [n.in, n.out]) {
        const a = ecran(n.anchor[0], n.anchor[1]), e = ecran(h[0], h[1]);
        svg.appendChild(el("line", { x1: a.x, y1: a.y, x2: e.x, y2: e.y }, "trace-poignee"));
        svg.appendChild(el("circle", { cx: e.x, cy: e.y, r: 3 }, "trace-poignee"));
      }
    }
    const montre = deplace && deplace.cible.type === "travail" && cheminTravail ? deplacerChemin(cheminTravail, deplace.d[0], deplace.d[1])
      : PL.etat.outil === "pathSelection" && cheminTravail ? cheminTravail : cheminChoisi;
    if (montre) svg.appendChild(el("path", { d: dChemin(montre, ecran), fill: "none" }, "trace-montre"));
  });

  /* panneau Tracés */
  const corps = PL.$("#corpsTraces");
  async function relireListe() {
    const d = PL.etat.doc;
    if (!d) { liste = null; cheminTravail = null; return; }
    if (revLue === d.revision && liste) return;
    revLue = d.revision;
    try { liste = await PL.post("/executer", { command: "path.list", params: {} }); } catch (e) { liste = null; }
    cheminTravail = null;
    if (liste && liste.workPath) {
      try { const r = await PL.post("/executer", { command: "path.info", params: { name: "work" } }); cheminTravail = r && r.path; } catch (e) { /* facultatif */ }
    }
  }
  if (!corps) return;
  const zone = document.createElement("div"); zone.className = "tra-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  corps.append(zone, pied);
  const bouton = (icone, cle, fn) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  const nomCible = () => (choisi ? choisi.cle : liste && liste.workPath ? "work" : null);
  const bRemplir = bouton("paint-bucket", "photolab.traces.remplir", () => { const n = nomCible(); if (n) PL.executer("path.fill", { name: n, color: fg() }); });
  const bContour = bouton("brush", "photolab.traces.contour", () => { const n = nomCible(); if (n) PL.executer("path.stroke", { name: n, tool: "brush" }); });
  const bSelection = bouton("circle-dashed", "photolab.traces.selection", () => { const n = nomCible(); if (n) PL.executer("path.toSelection", { name: n }); });
  const bDepuisSel = bouton("square-dashed", "photolab.traces.depuis_selection", () => PL.executer("select.toWorkPath", { tolerance: 2 }));
  bouton("plus", "photolab.traces.nouveau", async () => {
    await relireListe();
    PL.executer("path.set", { name: nomLibre(liste, T("photolab.traces.base")), path: { subpaths: [] } });
  });
  const bSuppr = bouton("trash-2", "photolab.traces.supprimer", () => { if (choisi && choisi.type !== "calque") { PL.executer("path.delete", { name: choisi.cle }); choisi = null; cheminChoisi = null; } });
  if (PL.hydraterIcones) PL.hydraterIcones(pied);

  function vignette(path) {
    const svg = document.createElementNS(NS, "svg"); svg.setAttribute("class", "tra-vignette"); svg.setAttribute("viewBox", "0 0 40 30");
    const d = PL.etat.doc;
    if (path && d) {
      const k = Math.min(40 / d.width, 30 / d.height), ox = (40 - d.width * k) / 2, oy = (30 - d.height * k) / 2;
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", dChemin(path, (x, y) => ({ x: ox + x * k, y: oy + y * k })));
      svg.appendChild(p);
    }
    return svg;
  }
  async function cheminDe(l) {
    try { const r = await PL.post("/executer", { command: "path.info", params: { name: l.cle } }); return r && r.path; } catch (e) { return null; }
  }
  let jeton = 0;               // deux dessins peuvent se chevaucher (async) : seul le dernier remplit la liste
  async function dessiner() {
    const n = ++jeton;
    const d = PL.etat.doc;
    if (!d) { zone.textContent = ""; [bRemplir, bContour, bSelection, bDepuisSel, bSuppr].forEach((b) => { b.disabled = true; }); return; }
    await relireListe();
    const frag = document.createDocumentFragment();
    for (const l of lignesTraces(liste)) {
      const row = document.createElement("div"); row.className = "tra-ligne" + (choisi && choisi.cle === l.cle ? " choisi" : "") + (l.type !== "enregistre" ? " italique" : "");
      const nom = document.createElement("span"); nom.className = "tra-nom";
      nom.textContent = l.type === "travail" ? T("photolab.traces.travail") : l.nom;
      if (l.type !== "travail") nom.setAttribute("data-dz-brut", "");
      const p = await cheminDe(l);
      row.append(vignette(p), nom);
      row.addEventListener("click", () => { choisi = l; cheminChoisi = p; dessiner(); redessiner(); });
      row.addEventListener("dblclick", async () => {
        if (l.type === "calque") return;
        if (l.type === "travail") { await relireListe(); PL.executer("path.rename", { name: "work", to: nomLibre(liste, T("photolab.traces.base")) }); return; }
        const n = await demanderNom(PL, T("commun.action.renommer"), l.nom);
        if (n) PL.executer("path.rename", { name: l.cle, to: n });
      });
      frag.appendChild(row);
    }
    if (n !== jeton) return;
    zone.replaceChildren(frag);
    if (choisi && !lignesTraces(liste).some((x) => x.cle === choisi.cle)) { choisi = null; cheminChoisi = null; }
    const aTrace = !!(choisi || (liste && liste.workPath));
    bRemplir.disabled = bContour.disabled = bSelection.disabled = !aTrace;
    bDepuisSel.disabled = !d.hasSelection;
    bSuppr.disabled = !choisi || choisi.type === "calque";
  }
  PL.surDoc.push(() => { revLue = null; if (corps.offsetParent || PL.etat.outil === "pathSelection") dessiner(); });
  PL.traces = { dessiner, liste: () => liste, noeuds: () => noeuds, choisi: () => choisi };

  // Barre d'options de la plume : mode Tracé / Forme.
  PL.barresOutils = PL.barresOutils || {};
  PL.barresOutils.pen = (barre) => {
    const w = document.createElement("label"); w.className = "opt fo-champ";
    const s = document.createElement("span"); s.textContent = T("photolab.plume.mode");
    const sel = document.createElement("select");
    for (const v of MODES_PLUME) { const o = document.createElement("option"); o.value = v; o.textContent = T(v === "trace" ? "photolab.plume.mode_trace" : "photolab.plume.mode_forme"); sel.appendChild(o); }
    sel.value = PL.etat.plume.mode; sel.addEventListener("change", () => { PL.etat.plume.mode = sel.value; });
    const aide = document.createElement("span"); aide.className = "opt-aide"; aide.textContent = T("photolab.plume.aide");
    w.append(s, sel); barre.append(w, aide);
  };
  PL.barresOutils.pathSelection = (barre) => {
    const aide = document.createElement("span"); aide.className = "opt-aide"; aide.textContent = T("photolab.selection_trace.aide"); barre.appendChild(aide);
  };
}
