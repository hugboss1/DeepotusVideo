// mod-plumeui.js — la Plume de classe Affinity (R8). REMPLACE la plume de
// mod-tools : écouteurs en CAPTURE sur #stage avec stopPropagation quand
// l'outil est « plume ». Quatre modes (plume, intelligent, polygone,
// ligne), clic = nœud vif, glisser = nœud lisse (Maj : tangente à 45°),
// clic droit = droite, Alt = sans magnétisme, Retour arrière = retirer,
// clic sur le premier nœud = fermer, Entrée / Échap / double-clic = finir,
// clic sur l'extrémité d'une courbe ouverte sélectionnée = la prolonger ;
// actions Vif / Lisse / Fractionner / Ouvrir / Fermer / Lisser / Relier /
// Inverser sur VL.actions.plume. Géométrie : mod-plume (pure).
import { trace_debut, trace_ajouter, trace_poignee, trace_retirer, trace_finir, elastique, contraindre_angle, lisser_catmull, chemin_ouvrir, chemin_lisser, chemin_fractionner, trace_depuis_chemin, extremite_proche, types_ancres } from "./mod-plume.js";
import { op_ajouter, op_chemin_fermer, op_noeud_convertir, chemin_ancres, chemin_parser } from "./mod-doc.js";
import { op_chemin_inverser, op_chemins_joindre } from "./mod-noeuds.js";

export const MODES_PLUME = [{ id: "plume", nom: "Plume" }, { id: "intelligent", nom: "Intelligent" }, { id: "polygone", nom: "Polygone" }, { id: "ligne", nom: "Ligne" }];
export const HINT_PLUME = "cliquer ou glisser pour prolonger une courbe depuis sa fin · clic droit pour créer une ligne droite · glisser + Maj pour contraindre la tangente d'un nœud · Alt pour ignorer le magnétisme · Retour arrière retire le dernier nœud · Entrée ou Échap finit";
const SNS = "http://www.w3.org/2000/svg";

export function initPlume(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  if (!stage) return;
  etat.plume = { mode: "plume", trace: null, prolonge: null, geste: null, dernier: null };
  VL.hints = Object.assign(VL.hints || {}, { plume: HINT_PLUME });
  const P = etat.plume;
  const actif = () => etat.outil === "plume" && !!etat.doc;
  const pt = (ev) => { const p = VL.docPt(ev.clientX, ev.clientY); return ev.altKey ? p : VL.aimantePt(...p); };
  const ecranProche = (ev, a, tol = 7) => { const [ex, ey] = VL.ecranPt(a[0], a[1]); const r = stage.getBoundingClientRect(); return Math.hypot(ev.clientX - r.left - ex, ev.clientY - r.top - ey) <= tol; };

  /* ── l'aperçu : le tracé, l'élastique, les nœuds (carrés vifs / ronds lisses), le premier en rouge ── */
  function apercu(curseur, ev) {
    const t = $("#ovTmp"); if (!t) return; t.innerHTML = "";
    const tr = P.trace; if (!tr) return;
    const g = document.createElementNS(SNS, "g");
    g.setAttribute("transform", `translate(${etat.tx} ${etat.ty}) scale(${etat.zoom})`);
    const el = (nom, attrs) => { const e = document.createElementNS(SNS, nom); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); g.appendChild(e); return e; };
    const z = etat.zoom;
    const d = trace_finir(tr) || `M ${tr.ancres[0][0]} ${tr.ancres[0][1]}`;
    el("path", { d, fill: "none", stroke: "#4a90e2", "stroke-width": 1.5 / z });
    if (curseur && !P.geste) el("path", { d: elastique(tr, curseur), fill: "none", stroke: "#4a90e2", "stroke-width": 1 / z, "stroke-dasharray": `${4 / z} ${3 / z}` });
    const types = types_ancres(d);
    tr.ancres.forEach((a, i) => {
      const rouge = i === 0 && tr.ancres.length >= 2 && curseur && ev && ecranProche(ev, a);
      if (types[i] === "lisse") el("circle", { cx: a[0], cy: a[1], r: 3.5 / z, fill: rouge ? "#e33" : "#fff", stroke: "#2b6fd6", "stroke-width": 1 / z });
      else el("rect", { x: a[0] - 3 / z, y: a[1] - 3 / z, width: 6 / z, height: 6 / z, fill: rouge ? "#e33" : "#fff", stroke: "#2b6fd6", "stroke-width": 1 / z });
    });
    // les poignées du dernier nœud
    const a = tr.ancres[tr.ancres.length - 1], s = tr.segs[tr.segs.length - 1];
    const poignee = (p) => { el("line", { x1: a[0], y1: a[1], x2: p[0], y2: p[1], stroke: "#2b6fd6", "stroke-width": 1 / z }); el("circle", { cx: p[0], cy: p[1], r: 3 / z, fill: "#2b6fd6" }); };
    if (tr.sortante) poignee(tr.sortante);
    if (s.c === "C" && (s.p[2] !== a[0] || s.p[3] !== a[1])) poignee([s.p[2], s.p[3]]);
    t.appendChild(g);
  }
  function finir(fermer) {
    const tr = P.trace; if (!tr) return;
    let segs = tr.segs;
    if (P.mode === "intelligent" && tr.ancres.length >= 2) segs = lisser_catmull(tr.ancres, fermer);
    const d = trace_finir({ ...tr, segs }, { fermer: fermer && P.mode !== "intelligent" });
    P.trace = null; P.geste = null; $("#ovTmp") && ($("#ovTmp").innerHTML = "");
    if (!d) return;
    if (P.prolonge) {
      const id = P.prolonge; P.prolonge = null;
      VL.executer((doc) => { const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === id); if (!o) throw new Error("chemin prolongé introuvable"); o.d = fermer ? d.replace(/\s*Z?$/, "") + " Z" : d; });
      VL.setSelection([id]); P.dernier = id;
      return;
    }
    const id = VL.executer(op_ajouter, etat.calqueActif, { type: "path", d, style: { fond: fermer ? etat.styleCourant.fond : "none", contour: etat.styleCourant.contour || "#1F1512", epaisseur: etat.styleCourant.epaisseur || 2 } });
    if (id) { VL.setSelection([id]); P.dernier = id; }
  }

  stage.addEventListener("pointerdown", (ev) => {
    if (!actif()) return;
    ev.stopPropagation(); ev.preventDefault();
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    if (ev.button === 2) return;   // le clic droit passe par contextmenu
    const p = pt(ev);
    // fermer au premier nœud
    if (P.trace && P.trace.ancres.length >= 2 && ecranProche(ev, P.trace.ancres[0])) { finir(true); return; }
    // prolonger une courbe ouverte sélectionnée depuis son extrémité
    if (!P.trace && etat.selection.length === 1) {
      const t = VL.objetDe(etat.selection[0]);
      if (t && t.objet.type === "path" && !t.calque.verrou) {
        const ex = extremite_proche(t.objet.d, p, 7 / etat.zoom);
        if (ex) {
          if (ex === "debut") VL.executer(op_chemin_inverser, t.objet.id);
          const d = VL.objetDe(t.objet.id).objet.d;
          P.trace = trace_depuis_chemin(d); P.prolonge = t.objet.id;
          P.geste = { type: "noeud", origine: p, poignee: false };
          apercu(p, ev); return;
        }
      }
    }
    if (!P.trace) { P.trace = trace_debut(p); P.prolonge = null; }
    else P.trace = trace_ajouter(P.trace, p, { droite: P.mode === "polygone" });
    P.geste = { type: "noeud", origine: p, poignee: false };
    apercu(p, ev);
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!actif()) return;
    const p = VL.docPt(ev.clientX, ev.clientY);
    if (P.geste && P.trace) {
      ev.stopPropagation();
      if (P.mode === "polygone" || P.mode === "ligne") return;   // pas de poignée en polygone / ligne
      const a = P.trace.ancres[P.trace.ancres.length - 1];
      if (Math.hypot(p[0] - a[0], p[1] - a[1]) > 2 / etat.zoom) {
        const q = ev.shiftKey ? contraindre_angle(a, p) : p;
        P.trace = trace_poignee(P.trace, q); P.geste.poignee = true;
      }
      apercu(null, ev);
      return;
    }
    if (P.trace) apercu(p, ev);
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!actif() || !P.geste) return;
    ev.stopPropagation();
    P.geste = null;
    if (P.mode === "ligne" && P.trace && P.trace.ancres.length >= 2) { finir(false); return; }
    apercu(VL.docPt(ev.clientX, ev.clientY), ev);
  }, true);
  stage.addEventListener("contextmenu", (ev) => {
    if (!actif()) return;
    ev.preventDefault(); ev.stopPropagation();
    const p = pt(ev);
    if (!P.trace) { P.trace = trace_debut(p); P.prolonge = null; }
    else P.trace = trace_ajouter(P.trace, p, { droite: true });
    apercu(p, ev);
  }, true);
  stage.addEventListener("dblclick", (ev) => { if (!actif()) return; ev.stopPropagation(); ev.preventDefault(); if (P.trace) { if (P.trace.ancres.length >= 2) { const a = P.trace.ancres[P.trace.ancres.length - 1], b = P.trace.ancres[P.trace.ancres.length - 2]; if (Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.5) P.trace = trace_retirer(P.trace); } finir(false); } }, true);

  /* ── clavier : Entrée / Échap finissent, Retour arrière retire ── */
  const sTouche = VL.surTouche;
  VL.surTouche = (ev) => {
    if (actif() && P.trace) {
      if (ev.key === "Enter") { finir(false); ev.preventDefault(); return; }
      if (ev.key === "Escape") { finir(false); return; }
      if (ev.key === "Backspace" || ev.key === "Delete") { P.trace = trace_retirer(P.trace); if (!P.trace) { $("#ovTmp") && ($("#ovTmp").innerHTML = ""); P.prolonge = null; } else apercu(null, null); ev.preventDefault(); return; }
    }
    sTouche(ev);
  };
  const sOutil = VL.surOutil;
  VL.surOutil = () => { if (P.trace && etat.outil !== "plume") { finir(false); } sOutil(); };

  /* ── les actions de la barre contextuelle ── */
  const chemin = () => { const id = etat.selection.length === 1 ? etat.selection[0] : P.dernier; const t = id && VL.objetDe(id); return t && t.objet.type === "path" ? t.objet : null; };
  const ancreCible = () => { const o = chemin(); if (!o) return null; const n = chemin_ancres(chemin_parser(o.d)).length; const i = etat.ancreSel !== null && etat.ancreSel !== undefined ? etat.ancreSel : n - 1; return { o, i, n }; };
  const convertir = (vers) => { const c = ancreCible(); if (!c) { VL.toast("plume : aucun chemin", true); return; } const t = types_ancres(c.o.d)[c.i]; if (t !== vers) VL.executer(op_noeud_convertir, c.o.id, c.i); };
  VL.actions = VL.actions || {};
  VL.actions.plume = {
    mode: (m) => { if (MODES_PLUME.some((x) => x.id === m)) P.mode = m; },
    vif: () => convertir("vif"),
    intelligent: () => { const A = VL.actions.noeuds; if (A && A.intelligent) A.intelligent(); },
    lisse: () => convertir("lisse"),
    fractionner: () => { const c = ancreCible(); if (!c) { VL.toast("plume : aucun chemin", true); return; } const parts = chemin_fractionner(c.o.d, c.i); if (parts.length === 1 && parts[0] === c.o.d) { VL.toast("fractionner : choisir une ancre intérieure (outil Nœuds)", true); return; } VL.executer((doc) => { const o = doc.calques.flatMap((k) => k.objets).find((x) => x.id === c.o.id); o.d = parts[0]; if (parts[1]) { const cal = doc.calques.find((k) => k.objets.includes(o)); op_ajouter(doc, cal.id, { type: "path", d: parts[1], style: { ...(o.style || {}) } }); } }); },
    ouvrir: () => { const o = chemin(); if (!o) return; VL.executer((doc) => { const x = doc.calques.flatMap((k) => k.objets).find((y) => y.id === o.id); x.d = chemin_ouvrir(x.d); }); },
    fermer: () => { const o = chemin(); if (!o) return; VL.executer(op_chemin_fermer, o.id); },
    lisserCourbe: () => { const o = chemin(); if (!o) return; VL.executer((doc) => { const x = doc.calques.flatMap((k) => k.objets).find((y) => y.id === o.id); x.d = chemin_lisser(x.d); }); },
    relier: () => { if (etat.selection.length !== 2) { VL.toast("relier : sélectionner deux chemins ouverts", true); return; } const id = VL.executer(op_chemins_joindre, etat.selection[0], etat.selection[1]); if (id) VL.setSelection([id]); },
    inverser: () => { const o = chemin(); if (!o) return; VL.executer(op_chemin_inverser, o.id); },
    peut: () => ({ chemin: !!chemin(), deux: etat.selection.length === 2, trace: !!P.trace }),
  };
  VL.plume = { etat: P, finir, apercu };   // la preuve
}
