// core.js — le cœur du Vectorlab (phase 1) : état unique, exécution de
// COMMANDES pures (mod-doc) sous historique d'instantanés, io API, vue
// (zoom/pan), overlay (sélection, poignées, ancres, guides), règles,
// raccourcis. Les outils et le panneau calques reçoivent ce cœur par
// injection (initOutils/initCalques) — aucun cycle d'import.
import { compilerSVG, chemin_parser, chemin_ancres, aimanter, Historique,
         sommetDe } from "./mod-doc.js";
import { initOutils } from "./mod-tools.js";
import { initCalques } from "./mod-layers.js";
import { initStyle } from "./mod-style.js";
import { initExport } from "./mod-export.js";
import { initVitrail } from "./mod-vitrail.js";
import { initBiblio } from "./mod-biblio.js";

const $ = (s) => document.querySelector(s);
const api = {
  async get(p) {
    const r = await fetch("/api" + p);
    if (!r.ok) throw new Error((await r.text()).slice(0, 300));
    return r.json();
  },
  async put(p, body) {
    const r = await fetch("/api" + p, { method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    return d;
  },
};

const etat = {
  docId: null, meta: null, doc: null,
  sale: false,
  outil: "select",
  selection: [],                 // ids d'objets
  ancreSel: null,                // index d'ancre (mode nœuds)
  calqueActif: null,
  zoom: 1, tx: 40, ty: 40,
  grille: { active: true, pas: 8 },
  histo: new Historique(100),
  // le style des NOUVEAUX objets — nourri par le panneau et la pipette
  styleCourant: { fond: "#9DB4D6", contour: "#1F1512", epaisseur: 2 },
};

/* ── conversions écran ↔ document ── */
function stageRect() { return $("#stage").getBoundingClientRect(); }
function docPt(clientX, clientY) {
  const r = stageRect();
  return [(clientX - r.left - etat.tx) / etat.zoom,
          (clientY - r.top - etat.ty) / etat.zoom];
}
function ecranPt(x, y) {
  return [x * etat.zoom + etat.tx, y * etat.zoom + etat.ty];
}
function tolDoc() { return 6 / etat.zoom; }
function aimantePt(x, y) {
  const g = etat.doc.guides || { v: [], h: [] };
  const pas = etat.grille.active ? etat.grille.pas : 0;
  return [aimanter(x, { pas, guides: g.v || [] }, tolDoc()),
          aimanter(y, { pas, guides: g.h || [] }, tolDoc())];
}

/* ── commandes ── */
function executer(fn, ...args) {
  // la commande s'essaie sur un CLONE : un échec ne laisse aucune trace
  // (ni document à moitié muté, ni pile d'annulation polluée)
  const essai = JSON.parse(JSON.stringify(etat.doc));
  try {
    const out = fn(essai, ...args);
    etat.histo.capturer(etat.doc);
    etat.doc = essai;
    etat.sale = true;
    rendre();
    return out;
  } catch (e) {
    toast(e.message, true);
    return undefined;
  }
}
function annuler() {
  if (!etat.histo.peutAnnuler()) return;
  etat.doc = etat.histo.annuler(etat.doc);
  etat.sale = true;
  purgerSelection();
  rendre();
}
function refaire() {
  if (!etat.histo.peutRefaire()) return;
  etat.doc = etat.histo.refaire(etat.doc);
  etat.sale = true;
  purgerSelection();
  rendre();
}
function purgerSelection() {
  const vivants = new Set();
  for (const c of etat.doc.calques) for (const o of c.objets) vivants.add(o.id);
  etat.selection = etat.selection.filter((id) => vivants.has(id));
  if (etat.ancreSel !== null && etat.selection.length !== 1) etat.ancreSel = null;
}

/* ── sélection ── */
function setSelection(ids) {
  etat.selection = [...new Set(ids)];
  etat.ancreSel = null;
  rendreOverlay();
  VL.surSelection();
}
function objetDe(id) {
  for (const c of etat.doc.calques) {
    const o = c.objets.find((x) => x.id === id);
    if (o) return { calque: c, objet: o };
  }
  return null;
}
function selectionElems() {
  return etat.selection
    .map((id) => document.querySelector(`#canvasHost [data-objet="${id}"]`))
    .filter(Boolean);
}
function bboxSelectionEcran() {
  const els = selectionElems();
  if (!els.length) return null;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  const r0 = stageRect();
  for (const el of els) {
    const r = el.getBoundingClientRect();
    x0 = Math.min(x0, r.left - r0.left); y0 = Math.min(y0, r.top - r0.top);
    x1 = Math.max(x1, r.right - r0.left); y1 = Math.max(y1, r.bottom - r0.top);
  }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}
function bboxSelectionDoc() {
  const b = bboxSelectionEcran();
  if (!b) return null;
  const [x, y] = [(b.x - etat.tx) / etat.zoom, (b.y - etat.ty) / etat.zoom];
  return { x, y, w: b.w / etat.zoom, h: b.h / etat.zoom };
}
function pathSelectionne() {
  if (etat.selection.length !== 1) return null;
  for (const c of etat.doc.calques) {
    const o = c.objets.find((x) => x.id === etat.selection[0]);
    if (o) return o.type === "path" && !c.verrou ? o : null;
  }
  return null;
}

/* ── rendu ── */
function appliquerVue() {
  const svg = $("#canvasHost svg");
  if (svg) {
    svg.style.transform =
      `translate(${etat.tx}px, ${etat.ty}px) scale(${etat.zoom})`;
  }
  $("#zoomLabel").textContent = Math.round(etat.zoom * 100) + " %";
  dessinerRegles();
  rendreOverlay();
}
function rendre() {
  $("#canvasHost").innerHTML = etat.doc ? compilerSVG(etat.doc) : "";
  $("#temoin").textContent = etat.sale ? "●" : "✓";
  $("#temoin").classList.toggle("sale", etat.sale);
  VL.surRendu();                     // calques et outils se resynchronisent
  appliquerVue();
}

const SNS = "http://www.w3.org/2000/svg";
function ov(nom, attrs) {
  const el = document.createElementNS(SNS, nom);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}
function rendreOverlay() {
  const o = $("#overlay");
  if (!o) return;
  o.innerHTML = "";
  if (!etat.doc) return;
  // guides (persistés dans le document) — poignées de drag comprises
  const r0 = stageRect();
  const g = etat.doc.guides || { v: [], h: [] };
  (g.v || []).forEach((x, i) => {
    const [ex] = ecranPt(x, 0);
    o.appendChild(ov("line", { x1: ex, y1: 0, x2: ex, y2: r0.height,
      stroke: "#39b3d0", "stroke-width": 1, class: "guide",
      "data-guide": "v:" + i, "stroke-dasharray": "5 4" }));
  });
  (g.h || []).forEach((y, i) => {
    const [, ey] = ecranPt(0, y);
    o.appendChild(ov("line", { x1: 0, y1: ey, x2: r0.width, y2: ey,
      stroke: "#39b3d0", "stroke-width": 1, class: "guide",
      "data-guide": "h:" + i, "stroke-dasharray": "5 4" }));
  });
  // cadre + poignées de la sélection (outil sélection)
  const b = bboxSelectionEcran();
  if (b && etat.outil === "select") {
    o.appendChild(ov("rect", { x: b.x, y: b.y, width: b.w, height: b.h,
      fill: "none", stroke: "#5b82b8", "stroke-width": 1,
      "stroke-dasharray": "4 3" }));
    const pts = [[b.x, b.y], [b.x + b.w / 2, b.y], [b.x + b.w, b.y],
                 [b.x + b.w, b.y + b.h / 2], [b.x + b.w, b.y + b.h],
                 [b.x + b.w / 2, b.y + b.h], [b.x, b.y + b.h],
                 [b.x, b.y + b.h / 2]];
    pts.forEach(([px, py], k) => o.appendChild(ov("rect", {
      x: px - 4, y: py - 4, width: 8, height: 8, fill: "#eef1f5",
      stroke: "#2c4a75", class: "poignee", "data-poignee": k })));
    o.appendChild(ov("line", { x1: b.x + b.w / 2, y1: b.y,
      x2: b.x + b.w / 2, y2: b.y - 22, stroke: "#5b82b8" }));
    o.appendChild(ov("circle", { cx: b.x + b.w / 2, cy: b.y - 26, r: 5,
      fill: "#eef1f5", stroke: "#2c4a75", class: "poignee-rot",
      "data-poignee": "rot" }));
  }
  // ancres du mode nœuds
  const p = etat.outil === "noeuds" ? pathSelectionne() : null;
  if (p) {
    const ancres = chemin_ancres(chemin_parser(p.d));
    for (const a of ancres) {
      const [ax, ay] = ecranPt(a.x, a.y);
      for (const pg of [a.entrante, a.sortante]) {
        if (!pg) continue;
        const [px, py] = ecranPt(pg.x, pg.y);
        o.appendChild(ov("line", { x1: ax, y1: ay, x2: px, y2: py,
          stroke: "#8b93a0", "stroke-width": 1 }));
        o.appendChild(ov("circle", { cx: px, cy: py, r: 3, fill: "#8b93a0" }));
      }
      o.appendChild(ov("rect", { x: ax - 4, y: ay - 4, width: 8, height: 8,
        fill: etat.ancreSel === a.i ? "#e0b34a" : "#eef1f5",
        stroke: "#2c4a75", class: "ancre", "data-ancre": a.i,
        transform: `rotate(45 ${ax} ${ay})` }));
    }
  }
  // poignées du dégradé de fond (sélection unique, outil sélection)
  if (etat.outil === "select" && etat.selection.length === 1) {
    const t = objetDe(etat.selection[0]);
    const f = t && t.objet.style && t.objet.style.fond;
    const gid = (typeof f === "string" && f.startsWith("grad:"))
      ? f.slice(5) : null;
    const gr = gid && etat.doc.degrades ? etat.doc.degrades[gid] : null;
    if (gr) {
      const pg = (x, y, role) => {
        const [ex, ey] = ecranPt(x, y);
        o.appendChild(ov("circle", { cx: ex, cy: ey, r: 6, fill: "#39b3d0",
          stroke: "#eef1f5", class: "poignee-grad",
          "data-grad": `${gid}:${role}` }));
        return [ex, ey];
      };
      if (gr.type === "lineaire") {
        const [ax, ay] = ecranPt(gr.x1, gr.y1);
        const [bx, by] = ecranPt(gr.x2, gr.y2);
        o.appendChild(ov("line", { x1: ax, y1: ay, x2: bx, y2: by,
          stroke: "#39b3d0", "stroke-width": 1.5 }));
        pg(gr.x1, gr.y1, "p1");
        pg(gr.x2, gr.y2, "p2");
      } else {
        const [cx, cy] = ecranPt(gr.cx, gr.cy);
        o.appendChild(ov("circle", { cx, cy, r: gr.r * etat.zoom,
          fill: "none", stroke: "#39b3d0", "stroke-dasharray": "5 4" }));
        pg(gr.cx, gr.cy, "centre");
        pg(gr.cx + gr.r, gr.cy, "rayon");
      }
    }
  }
  // le groupe temporaire des outils (lasso, aperçus) — toujours en dernier
  o.appendChild(ov("g", { id: "ovTmp" }));
}

/* ── règles ── */
function dessinerRegles() {
  const rh = $("#regleH"), rv = $("#regleV");
  const r0 = stageRect();
  rh.width = r0.width; rv.height = r0.height;
  const pas = etat.zoom >= 4 ? 10 : etat.zoom >= 1 ? 50 : 100;
  for (const [cv, horiz] of [[rh, true], [rv, false]]) {
    const c = cv.getContext("2d");
    c.clearRect(0, 0, cv.width, cv.height);
    c.fillStyle = "#8b93a0";
    c.strokeStyle = "#3a4150";
    c.font = "9px system-ui";
    const long = horiz ? r0.width : r0.height;
    const dep = horiz ? etat.tx : etat.ty;
    const d0 = Math.floor((-dep / etat.zoom) / pas) * pas;
    for (let v = d0; v * etat.zoom + dep < long; v += pas) {
      const e = v * etat.zoom + dep;
      c.beginPath();
      if (horiz) { c.moveTo(e, 24); c.lineTo(e, v % (pas * 5) ? 18 : 12); }
      else { c.moveTo(24, e); c.lineTo(v % (pas * 5) ? 18 : 12, e); }
      c.stroke();
      if (v % (pas * 5) === 0) {
        if (horiz) c.fillText(String(v), e + 2, 10);
        else { c.save(); c.translate(10, e + 2); c.rotate(-Math.PI / 2);
               c.fillText(String(v), 0, 0); c.restore(); }
      }
    }
  }
}

/* ── io ── */
async function charger() {
  const id = new URLSearchParams(location.search).get("doc");
  if (!id) {
    // sans ?doc : la page d'accueil BIBLIOTHÈQUE (chantier 27/08) — liste,
    // recherche, création ; l'éditeur reste caché (body.mode-biblio)
    VL.ouvrirBiblio();
    return;
  }
  try {
    const d = await api.get("/vector/docs/" + encodeURIComponent(id));
    etat.docId = id; etat.meta = d.meta; etat.doc = d.doc;
    etat.sale = false;
    etat.histo = new Historique(100);
    etat.calqueActif = etat.doc.calques[etat.doc.calques.length - 1].id;
    majTete();
    rendre();
    // centrer le document dans la scène
    const r = stageRect();
    etat.tx = Math.max(20, (r.width - etat.doc.taille.w * etat.zoom) / 2);
    etat.ty = Math.max(20, (r.height - etat.doc.taille.h * etat.zoom) / 2);
    appliquerVue();
  } catch (e) {
    $("#docMeta").classList.add("erreur");
    $("#docMeta").textContent = "erreur : " + e.message;
  }
}
function majTete() {
  $("#docTitle").textContent = etat.meta.name;
  $("#docMeta").classList.remove("erreur");
  $("#docMeta").textContent = `${etat.meta.role} · v${etat.meta.version}`
    + (etat.meta.chapter_id ? ` · chapitre ${etat.meta.chapter_id}` : "");
}
async function sauver() {
  if (!etat.docId || !etat.doc) return;
  try {
    const r = await api.put("/vector/docs/" + encodeURIComponent(etat.docId),
                            { doc: etat.doc });
    etat.meta.version = r.version;
    etat.sale = false;
    majTete();
    $("#temoin").textContent = "✓";
    $("#temoin").classList.remove("sale");
    // phase 6 : la vignette suit la sauvegarde — jamais bloquante, son
    // échec ne casse pas un save
    if (VL.vignette) VL.vignette().catch(() => {});
  } catch (e) { toast("sauvegarde : " + e.message, true); }
}

function toast(msg, erreur) {
  $("#docMeta").classList.toggle("erreur", !!erreur);
  $("#docMeta").textContent = msg;
  setTimeout(() => { if (etat.meta) majTete(); }, 2600);
}

/* ── vue : zoom molette (au curseur) + pan (bouton milieu ou espace) ── */
const stage = $("#stage");
let espace = false;
stage.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const r = stageRect();
  const mx = ev.clientX - r.left, my = ev.clientY - r.top;
  const z2 = Math.max(0.1, Math.min(16, etat.zoom * Math.pow(1.0015, -ev.deltaY)));
  etat.tx = mx - (mx - etat.tx) * (z2 / etat.zoom);
  etat.ty = my - (my - etat.ty) * (z2 / etat.zoom);
  etat.zoom = z2;
  appliquerVue();
}, { passive: false });

let pan = null;
stage.addEventListener("pointerdown", (ev) => {
  if (ev.button === 1 || (espace && ev.button === 0)) {
    pan = { x: ev.clientX, y: ev.clientY, tx: etat.tx, ty: etat.ty };
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    ev.preventDefault();
    ev.stopPropagation();
  }
}, true);
stage.addEventListener("pointermove", (ev) => {
  if (!pan) return;
  etat.tx = pan.tx + (ev.clientX - pan.x);
  etat.ty = pan.ty + (ev.clientY - pan.y);
  appliquerVue();
}, true);
stage.addEventListener("pointerup", () => { pan = null; }, true);

/* ── outils : bascule ── */
function setOutil(id) {
  etat.outil = id;
  document.querySelectorAll("#outils button").forEach((b) =>
    b.classList.toggle("actif", b.dataset.outil === id));
  VL.surOutil();
  rendreOverlay();
}
document.querySelectorAll("#outils button").forEach((b) =>
  b.addEventListener("click", () => setOutil(b.dataset.outil)));

/* ── raccourcis ── */
document.addEventListener("keydown", (ev) => {
  if (/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName || "")) return;
  if (ev.key === " ") { espace = true; stage.classList.add("main-panoramique"); ev.preventDefault(); return; }
  if (ev.ctrlKey && ev.key.toLowerCase() === "z" && !ev.shiftKey) { annuler(); ev.preventDefault(); return; }
  if ((ev.ctrlKey && ev.key.toLowerCase() === "y")
      || (ev.ctrlKey && ev.shiftKey && ev.key.toLowerCase() === "z")) { refaire(); ev.preventDefault(); return; }
  if (ev.ctrlKey && ev.key.toLowerCase() === "s") { sauver(); ev.preventDefault(); return; }
  if (ev.ctrlKey) return;
  const outils = { v: "select", p: "plume", r: "rect", e: "ellipse",
                   n: "noeuds", i: "pipette", t: "texte" };
  const k = ev.key.toLowerCase();
  if (outils[k]) { setOutil(outils[k]); return; }
  if (k === "g") {
    etat.grille.active = !etat.grille.active;
    $("#btnGrille").classList.toggle("actif", etat.grille.active);
    return;
  }
  VL.surTouche(ev);
});
document.addEventListener("keyup", (ev) => {
  if (ev.key === " ") { espace = false; stage.classList.remove("main-panoramique"); }
});

$("#btnAnnuler").addEventListener("click", annuler);
$("#btnRefaire").addEventListener("click", refaire);
$("#btnSauver").addEventListener("click", sauver);
$("#btnGrille").classList.add("actif");
$("#btnGrille").addEventListener("click", () => {
  etat.grille.active = !etat.grille.active;
  $("#btnGrille").classList.toggle("actif", etat.grille.active);
});
window.addEventListener("resize", appliquerVue);

/* ── le cœur, injecté dans les modules UI (et exposé pour la preuve) ── */
const VL = {
  etat, api, $,
  docPt, ecranPt, tolDoc, aimantePt,
  executer, annuler, refaire, sauver, charger,
  setSelection, selectionElems, bboxSelectionEcran, bboxSelectionDoc,
  pathSelectionne, purgerSelection, objetDe,
  sommetDe: (id) => sommetDe(etat.doc, id),
  rendre, rendreOverlay, appliquerVue, setOutil, toast,
  surRendu: () => {}, surOutil: () => {}, surTouche: () => {},
  surSelection: () => {},
};
initCalques(VL);
initStyle(VL);
initOutils(VL);
initExport(VL);
initVitrail(VL);
initBiblio(VL);
window.VL = VL;
charger();
