// mod-mesure.js — t160 (parité L10) : outils Règle, Comptage, Note, Tranche, Sélection de tranche ; panneaux Journal des
// mesures et Notes ; Affichage › Afficher › Compteur, Notes, Tranches ; Fichier › Importer › Notes.
// Tout ce qui s'enregistre passe par le moteur (image.analysis.rulerTool, count.*, notes.*, slice.*,
// image.analysis.recordMeasurements, measurementLog.*) ; l'écran ne dessine qu'une SURCOUCHE (ligne de la règle, marques,
// icônes de notes, contours de tranches) d'après GET /api/photolab/analyse, relu après chaque cycle quand il sert.
// L'export du journal (désactivé par le moteur) est composé par le pont (GET /mesures.csv) ; l'import de notes copie
// celles d'un autre document ouvert (POST /notes/importer). Fonctions PURES exportées (qa/mesure.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";
import { poigneeSous, redimensionner } from "./mod-recadrer.js";

export const OUTILS_MESURE = ["ruler", "count", "note", "slice", "sliceSelect"];
const NS = "http://www.w3.org/2000/svg";
export const TOL_ECRAN = 7;              // px d'écran pour attraper une extrémité, une marque, une icône
export const TAILLE_NOTE = 14;           // côté de l'icône de note (px d'écran)

// Couleur du moteur (composantes 0..1) -> "#rrggbb".
export function hexDe(c) {
  if (typeof c === "string") return c;
  const v = Array.isArray(c) ? c : [1, 1, 0.51];
  return "#" + v.slice(0, 3).map((x) => Math.max(0, Math.min(255, Math.round(x * 255))).toString(16).padStart(2, "0")).join("");
}

// Règle : Maj contraint l'angle par pas de 45°, longueur gardée.
export function contraindre(x0, y0, x1, y1) {
  const dx = x1 - x0, dy = y1 - y0, l = Math.hypot(dx, dy);
  if (!l) return [x1, y1];
  const a = Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) * (Math.PI / 4);
  return [x0 + l * Math.cos(a), y0 + l * Math.sin(a)];
}
// Lecture de la règle pour la barre d'options : [clé, texte]. Angle en degrés, longueurs dans l'unité de l'échelle.
export function lectureRegle(info) {
  const f = (v, n = 2) => (v == null || !Number.isFinite(v) ? "" : (Math.round(v * 10 ** n) / 10 ** n).toString());
  if (!info) return [["x", ""], ["y", ""], ["w", ""], ["h", ""], ["a", ""], ["l1", ""], ["l2", ""]];
  return [["x", f(info.x, 1)], ["y", f(info.y, 1)], ["w", f(info.w, 1)], ["h", f(info.h, 1)], ["a", f(info.angle, 1) + "°"],
    ["l1", f(info.protractor ? info.l1 : info.length) + (info.protractor ? "" : " " + (info.units || ""))], ["l2", info.protractor ? f(info.l2) : ""]];
}
// Extrémité de la règle sous un point (pixels DOCUMENT, tolérance en document) : "start" | "end" | "protractor" | null.
export function extremiteSous(regle, p, tol) {
  if (!regle) return null;
  let best = null, d = tol;
  for (const k of ["start", "end", "protractor"]) {
    const q = regle[k];
    if (!q) continue;
    const e = Math.hypot(q[0] - p.x, q[1] - p.y);
    if (e <= d) { d = e; best = k; }
  }
  return best;
}
// Marque de comptage la plus proche (groupes visibles) -> {group, index} | null.
export function marqueSous(count, p, tol) {
  let best = null, d = tol;
  (count && count.groups || []).forEach((g, gi) => {
    if (g.visible === false) return;
    (g.points || []).forEach((q, i) => { const e = Math.hypot(q[0] - p.x, q[1] - p.y); if (e <= d) { d = e; best = { group: gi, index: i }; } });
  });
  return best;
}
// Note dont l'icône (carré de `tol` document depuis sa position, coin haut gauche) contient le point -> index | null.
export function noteSous(notes, p, tol) {
  for (let i = (notes || []).length - 1; i >= 0; i--) {
    const [x, y] = notes[i].position || [0, 0];
    if (p.x >= x - 1 && p.x <= x + tol && p.y >= y - 1 && p.y <= y + tol) return notes[i].index ?? i;
  }
  return null;
}
// Tranches à dessiner : les automatiques seulement s'il existe une tranche utilisateur (ou d'après un calque), ou si
// un outil de tranche est actif ; `masquerAuto` les retire toujours.
export function tranchesVisibles(slices, outilTranche, masquerAuto = false) {
  const L = slices || [];
  const reelles = L.some((s) => s.origin !== "auto");
  return L.filter((s) => s.origin !== "auto" || (!masquerAuto && (reelles || outilTranche)));
}
// Tranche sous le point : une tranche utilisateur ou d'après un calque passe avant une automatique, la plus petite d'abord.
export function trancheSous(slices, p) {
  const dedans = (slices || []).filter((s) => { const [x, y, w, h] = s.rect; return p.x >= x && p.x < x + w && p.y >= y && p.y < y + h; });
  dedans.sort((a, b) => (a.origin === "auto") - (b.origin === "auto") || a.rect[2] * a.rect[3] - b.rect[2] * b.rect[3]);
  return dedans[0] || null;
}
// Cible d'une commande slice.* : l'id d'une tranche utilisateur, le numéro d'une automatique (le moteur la promeut).
export const cibleTranche = (s) => (s && s.id != null ? { slice: s.id } : { number: s.number });
// Rectangle d'un glisser de tranche, en pixels entiers bornés au document ; Maj = carré.
export function rectTranche(x0, y0, x1, y1, carre, doc) {
  let w = x1 - x0, h = y1 - y0;
  if (carre) { const c = Math.max(Math.abs(w), Math.abs(h)); w = Math.sign(w || 1) * c; h = Math.sign(h || 1) * c; }
  const ax = Math.round(Math.max(0, Math.min(x0, x0 + w))), ay = Math.round(Math.max(0, Math.min(y0, y0 + h)));
  const bx = Math.round(Math.min(doc.width, Math.max(x0, x0 + w))), by = Math.round(Math.min(doc.height, Math.max(y0, y0 + h)));
  return { x: ax, y: ay, width: Math.max(0, bx - ax), height: Math.max(0, by - ay) };
}
export const rectVersTableau = (r) => [r.x, r.y, r.width, r.height];
// Glisser d'une icône ou d'une tranche : toujours depuis la position d'ORIGINE du geste (jamais cumulé pas à pas : la
// surcouche peut être relue pendant le glisser).
export const positionNote = (g) => [g.origine[0] + g.a[0] - g.de[0], g.origine[1] + g.a[1] - g.de[1]];
export const rectChange = (a, b) => !a || !b || a.x !== b.x || a.y !== b.y || a.width !== b.width || a.height !== b.height;
export const deplacerRect = (r0, de, a) => ({ ...r0, x: Math.round(r0.x + a[0] - de[0]), y: Math.round(r0.y + a[1] - de[1]) });
// Point de la règle arrondi au centième de pixel (le moteur rend 99.99999… pour 100).
export const arrondirPoint = (q) => (q ? q.map((v) => Math.round(v * 100) / 100) : q);
export const tableauVersRect = (t) => ({ x: t[0], y: t[1], width: t[2], height: t[3] });
// Journal : colonnes choisies (selectDataPoints) qui ont au moins une valeur, dans l'ordre du moteur.
export function colonnesJournal(journal, points) {
  const choisies = points && points.dataPoints ? new Set(Object.values(points.dataPoints).flat()) : null;
  const lignes = (journal && journal.rows) || [];
  const cols = (points && points.columns) || ((journal && journal.columns) || []).map((k) => ({ key: k, name: k }));
  return cols.filter((c) => c.key !== "histogram" && (!choisies || choisies.has(c.key)) && lignes.some((r) => r.values && r.values[c.key] != null));
}
export function cellule(v) {
  if (v == null) return "";
  if (typeof v === "number") return v === 0 ? "0" : Number.isInteger(v) ? String(v) : String(Math.round(v * 10000) / 10000);
  return String(v);
}
// Valeurs de la colonne Source que le moteur écrit en anglais : le nom de l'outil de l'écran.
export const SOURCES = { "Ruler Tool": "photolab.outil.ruler", "Count Tool": "photolab.outil.count" };
export const cleColonne = (k) => "photolab.mesure.col." + String(k).replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
// Faut-il relire l'analyse ? Un outil de mesure est actif, un interrupteur d'affichage montre quelque chose, un
// panneau Notes ou Mesures est ouvert.
export const analyseUtile = (outil, voir, panneaux) => OUTILS_MESURE.includes(outil) || voir.compteur || voir.notes || voir.tranches || panneaux;

/* ───────────── côté DOM ───────────── */

export function initMesure(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const scene = PL.$("#scene"), toile = PL.$("#toile");
  const lireLS = (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } };
  const ecrireLS = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* facultatif */ } };
  let a = { ruler: null, rulerInfo: null, count: { groups: [], activeGroup: 0 }, notes: [], slices: [], locked: false, scale: null };
  let tranche = null;        // tranche choisie (Sélection de tranche) : {id, number}
  let noteChoisie = 0;
  let masquerAuto = false;
  let apercu = null;         // geste en cours : {type, …}
  let lecture = null;

  const svg = document.createElementNS(NS, "svg");
  svg.id = "mesures"; svg.setAttribute("aria-hidden", "true");
  scene.insertBefore(svg, PL.$("#fourmis"));
  const el = (tag, attrs, classe) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (classe) e.setAttribute("class", classe);
    return e;
  };
  const ecran = (x, y) => PL.vue.versEcran(x, y);
  const voir = (k) => !PL.affichage || PL.affichage.voir(k);
  const tolDoc = () => TOL_ECRAN / PL.vue.v.z;
  const panneauOuvert = () => { const g = PL.$("#grpInfos"); const o = PL.ongletDevant && PL.ongletDevant("#grpInfos", "data-onglet-in"); return !!g && !g.hidden && (o === "mesures" || o === "notes"); };

  async function relire() {
    if (!PL.etat.doc) { a = { ...a, ruler: null, rulerInfo: null, count: { groups: [] }, notes: [], slices: [] }; dessiner(); majPanneaux(); return; }
    const ma = PL.get("/analyse", true).catch(() => null);
    lecture = ma;
    const r = await ma;
    if (ma !== lecture || !r) return;
    a = r;
    dessiner(); majBarre(); majPanneaux();
  }
  function relireSiUtile() {
    if (analyseUtile(PL.etat.outil, { compteur: voir("compteur"), notes: voir("notes"), tranches: voir("tranches") }, panneauOuvert())) relire();
    else { svg.textContent = ""; }
  }
  PL.surDoc.push(() => relireSiUtile());
  if (PL.surOutil) PL.surOutil.push(() => { tranche = null; apercu = null; relireSiUtile(); });
  PL.surVue.push(() => dessiner());

  // une commande qui fait une étape : par la file de mod-cycle (historique, rendu), l'analyse est relue au cycle
  const executer = (cid, params) => PL.executer(cid, params);
  // une lecture ou une commande sans étape (règle, journal) : direct, puis relecture
  async function direct(cid, params) {
    let r;
    try { r = await PL.post("/executer", { command: cid, params }); } catch (e) { return null; }
    await relire();
    return r;
  }

  /* surcouche */
  function dessiner() {
    svg.textContent = "";
    const d = PL.etat.doc;
    if (!d) return;
    const outil = PL.etat.outil;
    // tranches
    if (voir("tranches") || outil === "slice" || outil === "sliceSelect") {
      for (const s of tranchesVisibles(a.slices, outil === "slice" || outil === "sliceSelect", masquerAuto)) {
        const [x, y, w, h] = s.rect;
        const p0 = ecran(x, y), p1 = ecran(x + w, y + h);
        const choisie = tranche && (tranche.id != null ? s.id === tranche.id : s.number === tranche.number);
        const r = { x: Math.round(Math.min(p0.x, p1.x)) + 0.5, y: Math.round(Math.min(p0.y, p1.y)) + 0.5, width: Math.round(Math.abs(p1.x - p0.x)), height: Math.round(Math.abs(p1.y - p0.y)) };
        svg.appendChild(el("rect", r, "tranche " + (s.origin === "auto" ? "auto" : "utilisateur") + (choisie ? " choisie" : "")));
        const g = el("g", {}, "tranche-badge" + (s.origin === "auto" ? " auto" : ""));
        g.appendChild(el("rect", { x: r.x + 2, y: r.y + 2, width: 22, height: 13 }));
        const t = el("text", { x: r.x + 13, y: r.y + 12 }); t.textContent = String(s.number).padStart(2, "0"); g.appendChild(t);
        svg.appendChild(g);
        if (choisie && outil === "sliceSelect" && s.origin !== "auto") {
          for (const [px, py] of [[r.x, r.y], [r.x + r.width, r.y], [r.x, r.y + r.height], [r.x + r.width, r.y + r.height]]) svg.appendChild(el("rect", { x: px - 4, y: py - 4, width: 8, height: 8 }, "poignee"));
        }
      }
    }
    if (apercu && apercu.type === "tranche" && apercu.rect) {
      const rr = apercu.rect, p0 = ecran(rr.x, rr.y), p1 = ecran(rr.x + rr.width, rr.y + rr.height);
      svg.appendChild(el("rect", { x: Math.min(p0.x, p1.x), y: Math.min(p0.y, p1.y), width: Math.abs(p1.x - p0.x), height: Math.abs(p1.y - p0.y) }, "tranche utilisateur choisie"));
    }
    // marques de comptage
    if (voir("compteur") || outil === "count") {
      (a.count && a.count.groups || []).forEach((g) => {
        if (g.visible === false) return;
        const couleur = hexDe(g.color), r = 2 + (g.markerSize || 1) * 1.5;
        (g.points || []).forEach((q, i) => {
          const s = ecran(q[0], q[1]);
          svg.appendChild(el("circle", { cx: s.x, cy: s.y, r, fill: couleur, stroke: "#ffffff", "stroke-width": 1 }, "marque"));
          const t = el("text", { x: s.x + r + 2, y: s.y - r, fill: couleur, "font-size": g.labelSize || 8 }, "marque-num"); t.textContent = String(i + 1); svg.appendChild(t);
        });
      });
    }
    // notes
    if (voir("notes") || outil === "note") {
      (a.notes || []).forEach((n, i) => {
        const [x, y] = n.position || [0, 0];
        const s = ecran(x, y);
        const g = el("g", {}, "note-icone" + ((n.index ?? i) === noteChoisie ? " choisie" : ""));
        g.appendChild(el("path", { d: `M${s.x} ${s.y}h${TAILLE_NOTE - 4}l4 4v${TAILLE_NOTE - 4}h-${TAILLE_NOTE}z`, fill: hexDe(n.color) }));
        svg.appendChild(g);
      });
    }
    // règle
    const regle = apercu && apercu.type === "regle" ? apercu.regle : a.ruler;
    if (regle && regle.start && regle.end && (outil === "ruler" || (apercu && apercu.type === "regle"))) {
      const s0 = ecran(...regle.start), s1 = ecran(...regle.end);
      svg.appendChild(el("line", { x1: s0.x, y1: s0.y, x2: s1.x, y2: s1.y }, "regle-ligne"));
      if (regle.protractor) { const s2 = ecran(...regle.protractor); svg.appendChild(el("line", { x1: s0.x, y1: s0.y, x2: s2.x, y2: s2.y }, "regle-ligne")); }
      for (const q of [regle.start, regle.end, regle.protractor].filter(Boolean)) {
        const s = ecran(...q);
        svg.appendChild(el("path", { d: `M${s.x - 4} ${s.y}H${s.x + 4}M${s.x} ${s.y - 4}V${s.y + 4}` }, "regle-croix"));
      }
    }
  }

  /* outils */
  PL.gestes.ruler = {
    appui(p, ev) {
      if (!PL.etat.doc) return;
      const ext = extremiteSous(a.ruler, p, tolDoc());
      if (ev.altKey && a.ruler && ext === "start") apercu = { type: "regle", prise: "protractor", regle: { ...a.ruler, protractor: [p.x, p.y] } };
      else if (ext) apercu = { type: "regle", prise: ext, regle: { ...a.ruler } };
      else apercu = { type: "regle", prise: "end", regle: { start: [p.x, p.y], end: [p.x, p.y], protractor: null } };
      dessiner();
    },
    bouger(p, ev) {
      if (!apercu) return;
      const r = apercu.regle, base = apercu.prise === "start" ? r.end : r.start;
      apercu.regle = { ...r, [apercu.prise]: ev.shiftKey ? contraindre(base[0], base[1], p.x, p.y) : [p.x, p.y] };
      dessiner();
    },
    async relacher() {
      if (!apercu) return;
      const r = apercu.regle; apercu = null;
      if (Math.hypot(r.end[0] - r.start[0], r.end[1] - r.start[1]) < 0.5) { await direct("image.analysis.rulerTool", { clear: true }); return; }
      const params = { start: arrondirPoint(r.start), end: arrondirPoint(r.end) };
      if (r.protractor) params.protractor = arrondirPoint(r.protractor);
      await direct("image.analysis.rulerTool", params);
    },
    survol(p) { toile.style.cursor = extremiteSous(a.ruler, p, tolDoc()) ? "move" : "crosshair"; },
    annuler() { apercu = null; dessiner(); },
  };

  PL.gestes.count = {
    appui(p, ev) {
      if (!PL.etat.doc) return;
      const m = marqueSous(a.count, p, tolDoc());
      if (m && ev.altKey) { apercu = null; executer("count.remove", { index: m.index, group: m.group }); return; }
      if (m) { apercu = { type: "marque", m, de: [p.x, p.y], a: [p.x, p.y] }; return; }
      if (!ev.altKey) executer("count.add", { x: Math.round(p.x * 10) / 10, y: Math.round(p.y * 10) / 10 });
    },
    bouger(p) { if (apercu && apercu.type === "marque") { apercu.a = [p.x, p.y]; const g = a.count.groups[apercu.m.group]; g.points[apercu.m.index] = [p.x, p.y]; dessiner(); } },
    relacher() {
      if (!apercu || apercu.type !== "marque") return;
      const { m, de, a: fin } = apercu; apercu = null;
      if (Math.hypot(fin[0] - de[0], fin[1] - de[1]) * PL.vue.v.z < 2) return;
      executer("count.move", { index: m.index, group: m.group, to: fin });
    },
    survol(p) { toile.style.cursor = marqueSous(a.count, p, tolDoc()) ? "move" : "crosshair"; },
    annuler() { apercu = null; relire(); },
  };

  let focusNote = false;
  const auteur = () => lireLS("dz-photolab-note-auteur", "");
  const couleurNote = () => lireLS("dz-photolab-note-couleur", "#ffff82");
  PL.gestes.note = {
    appui(p) {
      if (!PL.etat.doc) return;
      const i = noteSous(a.notes, p, TAILLE_NOTE / PL.vue.v.z);
      if (i != null) {
        const n = a.notes.find((x, k) => (x.index ?? k) === i);
        noteChoisie = i; apercu = { type: "note", index: i, de: [p.x, p.y], a: [p.x, p.y], origine: n ? [...n.position] : [p.x, p.y] };
        dessiner(); montrerPanneau("notes"); return;
      }
      apercu = null;
      executer("notes.add", { x: Math.round(p.x), y: Math.round(p.y), text: "", author: auteur(), color: couleurNote() }).then((res) => {
        // la note posée devient la note du panneau (index rendu par le moteur), son texte reçoit le focus
        if (res && res.ok && res.r && Number.isInteger(res.r.index)) noteChoisie = res.r.index;
        focusNote = true; montrerPanneau("notes");
      });
    },
    bouger(p) {
      if (!apercu || apercu.type !== "note") return;
      apercu.a = [p.x, p.y];
      const n = a.notes.find((x, k) => (x.index ?? k) === apercu.index);
      if (n) { n.position = positionNote(apercu); dessiner(); }
    },
    relacher() {
      if (!apercu || apercu.type !== "note") return;
      const g = apercu; apercu = null;
      if (Math.hypot(g.a[0] - g.de[0], g.a[1] - g.de[1]) * PL.vue.v.z < 2) return;
      const [x, y] = positionNote(g);
      executer("notes.set", { index: g.index, x: Math.round(x), y: Math.round(y) });
    },
    survol(p) { toile.style.cursor = noteSous(a.notes, p, TAILLE_NOTE / PL.vue.v.z) != null ? "move" : "crosshair"; },
    annuler() { apercu = null; relire(); },
  };

  PL.gestes.slice = {
    appui(p, ev) { if (PL.etat.doc) apercu = { type: "tranche", x0: p.x, y0: p.y, maj: ev.shiftKey, rect: null }; },
    bouger(p, ev) { if (apercu) { apercu.rect = rectTranche(apercu.x0, apercu.y0, p.x, p.y, ev.shiftKey, PL.etat.doc); dessiner(); } },
    relacher() {
      if (!apercu) return;
      const r = apercu.rect; apercu = null; dessiner();
      if (!r || r.width < 1 || r.height < 1) return;
      if (a.locked) { PL.signaler(T("photolab.tranche.verrouillees"), true); return; }
      executer("slice.new", { rect: rectVersTableau(r) });
    },
    annuler() { apercu = null; dessiner(); },
  };

  const tranchesDessinees = () => tranchesVisibles(a.slices, true, masquerAuto);
  const trancheChoisie = () => (tranche ? a.slices.find((s) => (tranche.id != null ? s.id === tranche.id : s.number === tranche.number)) || null : null);
  PL.gestes.sliceSelect = {
    appui(p) {
      if (!PL.etat.doc) return;
      const c = trancheChoisie();
      const h = c && c.origin !== "auto" ? poigneeSous(tableauVersRect(c.rect), p.sx, p.sy, PL.vue.v) : null;
      if (h) { apercu = { type: "poignee", poignee: h, rect0: tableauVersRect(c.rect), rect: tableauVersRect(c.rect), s: c }; return; }
      const s = trancheSous(tranchesDessinees(), p);
      tranche = s ? { id: s.id, number: s.number } : null;
      apercu = s && s.origin !== "auto" ? { type: "deplacer", s, de: [p.x, p.y], rect0: tableauVersRect(s.rect), rect: tableauVersRect(s.rect) } : null;
      dessiner(); majBarre();
    },
    bouger(p) {
      if (!apercu) return;
      const d = PL.etat.doc;
      if (apercu.type === "poignee") apercu.rect = redimensionner(apercu.rect0, apercu.poignee, p.x, p.y, d);
      else if (apercu.type === "deplacer") apercu.rect = deplacerRect(apercu.rect0, apercu.de, [p.x, p.y]);
      // l'analyse a pu être relue pendant le glisser : la tranche affichée est retrouvée par son id
      const s = a.slices.find((x) => x.id === apercu.s.id && x.number === apercu.s.number) || a.slices.find((x) => x.id != null && x.id === apercu.s.id);
      if (s) s.rect = rectVersTableau(apercu.rect);
      dessiner();
    },
    relacher() {
      if (!apercu) return;
      const { s, rect, rect0 } = apercu; apercu = null;
      const r = { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.max(1, Math.round(rect.width)), height: Math.max(1, Math.round(rect.height)) };
      if (!rectChange(rect0, r)) return;                    // un clic qui choisit sans bouger : aucune étape
      if (a.locked) { PL.signaler(T("photolab.tranche.verrouillees"), true); relire(); return; }
      executer("slice.set", { ...cibleTranche(s), rect: rectVersTableau(r) });
    },
    survol(p) {
      const c = trancheChoisie();
      const h = c && c.origin !== "auto" ? poigneeSous(tableauVersRect(c.rect), p.sx, p.sy, PL.vue.v) : null;
      toile.style.cursor = h ? (h === "nw" || h === "se" ? "nwse-resize" : "nesw-resize") : "default";
    },
    double() { if (trancheChoisie()) optionsTranche(); },
    touche(ev) {
      if ((ev.key === "Delete" || ev.key === "Backspace") && trancheChoisie() && trancheChoisie().origin !== "auto") {
        executer("slice.delete", cibleTranche(trancheChoisie())); tranche = null; return true;
      }
      if (ev.key === "Escape" && tranche) { tranche = null; dessiner(); majBarre(); return true; }
      return false;
    },
    annuler() { apercu = null; relire(); },
  };

  /* barres d'options */
  const bouton = (cle, f, titre) => { const b = document.createElement("button"); b.type = "button"; b.className = "pl-bouton opt-action"; b.textContent = T(cle); if (titre) b.title = T(titre); b.addEventListener("click", f); return b; };
  const etiquette = (cle, input) => { const l = document.createElement("label"); l.className = "opt"; const s = document.createElement("span"); s.textContent = T(cle); l.append(s, input); return l; };
  let barreCourante = null;
  function majBarre() { if (barreCourante && OUTILS_MESURE.includes(PL.etat.outil) && PL.reconstruireOptions) PL.reconstruireOptions(); }
  PL.barresOutils = PL.barresOutils || {};
  PL.barresOutils.ruler = (barre) => {
    barreCourante = barre;
    const z = document.createElement("span"); z.className = "opt-lecture";
    for (const [k, v] of lectureRegle(a.ruler ? a.rulerInfo : null)) {
      const c = document.createElement("span"); c.className = "opt-lecture-champ"; c.dataset.cle = k;
      const n = document.createElement("b"); n.textContent = T("photolab.regle." + k); c.append(n, document.createTextNode(" " + v));
      z.appendChild(c);
    }
    barre.append(z,
      bouton("photolab.regle.redresser", () => { if (a.ruler) executer("image.analysis.straightenLayer", {}); }, "photolab.regle.redresser_aide"),
      bouton("photolab.regle.effacer", () => direct("image.analysis.rulerTool", { clear: true })),
      bouton("photolab.mesure.enregistrer", () => enregistrerMesures("ruler")));
  };
  PL.barresOutils.count = (barre) => {
    barreCourante = barre;
    const c = a.count || { groups: [], activeGroup: 0 };
    const g = c.groups[c.activeGroup];
    const liste = document.createElement("select"); liste.setAttribute("data-dz-brut", "");
    c.groups.forEach((x, i) => { const o = document.createElement("option"); o.value = String(i); o.textContent = `${x.name} (${x.count})`; liste.appendChild(o); });
    liste.value = String(c.activeGroup || 0);
    liste.addEventListener("change", () => executer("count.setGroup", { group: Number(liste.value), active: true }));
    const vis = document.createElement("input"); vis.type = "checkbox"; vis.checked = !g || g.visible !== false; vis.disabled = !g;
    vis.addEventListener("change", () => executer("count.setGroup", { group: c.activeGroup, visible: vis.checked }));
    const coul = document.createElement("input"); coul.type = "color"; coul.value = g ? hexDe(g.color) : "#ff0000"; coul.disabled = !g;
    coul.addEventListener("change", () => executer("count.setGroup", { group: c.activeGroup, color: coul.value }));
    const nombre = (val, min, max, cle) => { const i = document.createElement("input"); i.type = "number"; i.min = min; i.max = max; i.value = val; i.disabled = !g;
      i.addEventListener("change", () => { const n = Math.round(Number(i.value)); if (n >= min && n <= max) executer("count.setGroup", { group: c.activeGroup, [cle]: n }); }); return i; };
    barre.append(etiquette("photolab.comptage.groupe", liste), etiquette("photolab.comptage.visible", vis), etiquette("photolab.comptage.couleur", coul),
      etiquette("photolab.comptage.taille_marque", nombre(g ? g.markerSize : 1, 1, 10, "markerSize")),
      etiquette("photolab.comptage.taille_numero", nombre(g ? g.labelSize : 8, 8, 72, "labelSize")),
      bouton("photolab.comptage.nouveau", () => executer("count.newGroup", { name: T("photolab.comptage.nom_groupe", { n: c.groups.length + 1 }) })),
      bouton("photolab.comptage.supprimer", async () => { if (g && (await confirmer(T("photolab.comptage.supprimer_q", { nom: g.name })))) executer("count.deleteGroup", { group: c.activeGroup }); }),
      bouton("photolab.comptage.effacer", () => { if (g) executer("count.clear", { group: c.activeGroup }); }),
      bouton("photolab.mesure.enregistrer", () => enregistrerMesures("count")));
  };
  PL.barresOutils.note = (barre) => {
    barreCourante = barre;
    const aut = document.createElement("input"); aut.type = "text"; aut.maxLength = 128; aut.value = auteur(); aut.setAttribute("data-dz-brut", "");
    aut.addEventListener("change", () => ecrireLS("dz-photolab-note-auteur", aut.value));
    const coul = document.createElement("input"); coul.type = "color"; coul.value = couleurNote();
    coul.addEventListener("change", () => ecrireLS("dz-photolab-note-couleur", coul.value));
    barre.append(etiquette("photolab.note.auteur", aut), etiquette("photolab.note.couleur", coul),
      bouton("photolab.note.tout_effacer", async () => { if (a.notes.length && (await confirmer(T("photolab.note.tout_effacer_q")))) executer("notes.delete", { all: true }); }),
      bouton("photolab.note.panneau", () => montrerPanneau("notes")));
  };
  PL.barresOutils.slice = (barre) => {
    barreCourante = barre;
    barre.append(bouton("photolab.tranche.depuis_reperes", () => executer("slice.fromGuides", {})));
  };
  PL.barresOutils.sliceSelect = (barre) => {
    barreCourante = barre;
    const s = trancheChoisie();
    const promouvoir = bouton("photolab.tranche.promouvoir", () => { if (s) executer("slice.promote", cibleTranche(s)); });
    promouvoir.disabled = !s || s.origin === "user";
    const diviser = bouton("photolab.tranche.diviser", () => { if (s) diviserTranche(s); }); diviser.disabled = !s;
    const options = bouton("photolab.tranche.options", () => optionsTranche()); options.disabled = !s;
    const auto = document.createElement("input"); auto.type = "checkbox"; auto.checked = masquerAuto;
    auto.addEventListener("change", () => { masquerAuto = auto.checked; dessiner(); });
    barre.append(promouvoir, diviser, options, etiquette("photolab.tranche.masquer_auto", auto));
  };

  async function confirmer(question) {
    const d = window.__dzDialogue;
    if (d) return d.confirmer(question, {});
    return (await ouvrirDialogue(PL, {
      titre: T("commun.action.supprimer"), construire({ corps }) { const p = document.createElement("p"); p.textContent = question; corps.appendChild(p); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
    })) === "ok";
  }
  const champ = (cle, input) => { const l = document.createElement("label"); l.className = "pl-champ"; const s = document.createElement("span"); s.textContent = T(cle); l.append(s, input); return l; };

  async function optionsTranche() {
    const s = trancheChoisie();
    if (!s) return;
    let params = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.tranche.options_titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const texte = (v, max) => { const i = document.createElement("input"); i.type = "text"; i.maxLength = max; i.value = v || ""; i.setAttribute("data-dz-brut", ""); return i; };
        const type = document.createElement("select");
        for (const k of ["image", "noImage", "table"]) { const o = document.createElement("option"); o.value = k; o.textContent = T("photolab.tranche.type." + k.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase())); type.appendChild(o); }
        type.value = s.kind || "image";
        const nom = texte(s.name, 128), url = texte(s.url, 2048), cible = texte(s.target, 128), message = texte(s.message, 512), alt = texte(s.alt, 512);
        const fond = document.createElement("input"); fond.type = "color"; fond.value = s.background && s.background !== "none" ? s.background : "#ffffff";
        const sansFond = document.createElement("input"); sansFond.type = "checkbox"; sansFond.checked = !s.background || s.background === "none";
        corps.append(champ("photolab.tranche.type", type), champ("photolab.tranche.nom", nom), champ("photolab.tranche.url", url), champ("photolab.tranche.cible", cible),
          champ("photolab.tranche.message", message), champ("photolab.tranche.alt", alt), champ("photolab.tranche.fond", fond), champ("photolab.tranche.sans_fond", sansFond));
        return () => {
          params = { ...cibleTranche(s), kind: type.value, name: nom.value, url: url.value, target: cible.value, message: message.value, alt: alt.value,
            background: sansFond.checked ? "none" : fond.value };
          return true;
        };
      },
    });
    if (params) executer("slice.set", params);
  }
  async function diviserTranche(s) {
    let params = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.tranche.diviser_titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const n = (v) => { const i = document.createElement("input"); i.type = "number"; i.min = "1"; i.max = "100"; i.value = String(v); return i; };
        const h = n(2), v = n(1);
        const err = document.createElement("p"); err.className = "pl-erreur";
        corps.append(champ("photolab.tranche.horizontal", h), champ("photolab.tranche.vertical", v), err);
        return () => {
          const a1 = Math.round(Number(h.value)), b1 = Math.round(Number(v.value));
          if (!(a1 >= 1 && a1 <= 100 && b1 >= 1 && b1 <= 100)) { err.textContent = T("photolab.tranche.diviser_erreur"); return false; }
          params = { ...cibleTranche(s), horizontal: a1, vertical: b1 };
          return true;
        };
      },
    });
    if (params) executer("slice.divide", params);
  }

  /* panneaux Journal des mesures et Notes (groupe Infos) */
  const corpsMesures = PL.$("#corpsMesures"), corpsNotes = PL.$("#corpsNotes");
  // « Notes » est aussi « Release notes » ailleurs dans l'application : l'onglet a sa clé propre (contexte), posée ici
  const ongletNotes = PL.$('#grpInfos .onglet[data-onglet-in="notes"]');
  if (ongletNotes) { ongletNotes.setAttribute("data-dz-brut", ""); ongletNotes.textContent = T("photolab.panneau.notes"); }
  let journal = null, points = null, choisies = new Set();
  function montrerPanneau(nom) {
    const grp = PL.$("#grpInfos");
    if (!grp) return;
    grp.hidden = false;
    const o = grp.querySelector(`.onglet[data-onglet-in="${nom}"]`);
    if (o) o.click();
    if (PL.majRail) PL.majRail();
  }
  async function relireJournal() {
    try {
      journal = await PL.post("/executer", { command: "measurementLog.list", params: {} });
      points = await PL.post("/executer", { command: "image.analysis.selectDataPoints", params: {} });
    } catch (e) { journal = null; }
    dessinerJournal();
  }
  async function enregistrerMesures(source = "auto") {
    if (!PL.etat.doc) return;
    try { await PL.post("/executer", { command: "image.analysis.recordMeasurements", params: { source } }); } catch (e) { return; }
    montrerPanneau("mesures");
    await relireJournal();
  }
  function dessinerJournal() {
    if (!corpsMesures) return;
    corpsMesures.textContent = "";
    const barre = document.createElement("div"); barre.className = "ms-barre";
    const exp = bouton("photolab.mesure.exporter", () => {
      const a1 = document.createElement("a");
      a1.href = "/api/photolab/mesures.csv" + (choisies.size ? "?lignes=" + [...choisies].join(",") : "");
      a1.download = T("photolab.mesure.fichier") + ".csv";
      document.body.appendChild(a1); a1.click(); a1.remove();
    });
    const suppr = bouton("photolab.mesure.supprimer", async () => {
      if (!choisies.size) return;
      try { await PL.post("/executer", { command: "measurementLog.delete", params: { rows: [...choisies] } }); } catch (e) { return; }
      choisies = new Set(); relireJournal();
    });
    const tout = bouton("photolab.mesure.tout_effacer", async () => {
      if (!(journal && journal.rows && journal.rows.length) || !(await confirmer(T("photolab.mesure.tout_effacer_q")))) return;
      try { await PL.post("/executer", { command: "measurementLog.delete", params: { all: true } }); } catch (e) { return; }
      choisies = new Set(); relireJournal();
    });
    const rec = bouton("photolab.mesure.enregistrer", () => enregistrerMesures("auto"));
    rec.disabled = !PL.etat.doc;
    const lignes = (journal && journal.rows) || [];
    exp.disabled = !lignes.length; suppr.disabled = !choisies.size; tout.disabled = !lignes.length;
    barre.append(rec, exp, suppr, tout);
    corpsMesures.appendChild(barre);
    if (!lignes.length) { const p = document.createElement("p"); p.className = "pf-note"; p.textContent = T("photolab.mesure.vide"); corpsMesures.appendChild(p); return; }
    const cols = colonnesJournal(journal, points);
    const table = document.createElement("table"); table.className = "ms-table";
    const tete = document.createElement("tr");
    for (const c of cols) { const th = document.createElement("th"); th.textContent = T(cleColonne(c.key)); tete.appendChild(th); }
    table.appendChild(tete);
    for (const r of lignes) {
      const tr = document.createElement("tr"); tr.dataset.id = String(r.id);
      tr.classList.toggle("actif", choisies.has(r.id));
      for (const c of cols) { const td = document.createElement("td"); const v = r.values && r.values[c.key]; td.textContent = c.key === "source" && SOURCES[v] ? T(SOURCES[v]) : cellule(v); if (c.key === "document" || c.key === "label") td.setAttribute("data-dz-brut", ""); tr.appendChild(td); }
      tr.addEventListener("click", (ev) => {
        if (!(ev.ctrlKey || ev.metaKey || ev.shiftKey)) choisies = new Set();
        if (choisies.has(r.id)) choisies.delete(r.id); else choisies.add(r.id);
        dessinerJournal();
      });
      table.appendChild(tr);
    }
    const zone = document.createElement("div"); zone.className = "ms-zone"; zone.appendChild(table);
    corpsMesures.appendChild(zone);
  }
  function dessinerNotes() {
    if (!corpsNotes) return;
    corpsNotes.textContent = "";
    const notes = a.notes || [];
    if (!PL.etat.doc || !notes.length) { const p = document.createElement("p"); p.className = "pf-note"; p.textContent = T("photolab.note.vide"); corpsNotes.appendChild(p); return; }
    // l'index choisi n'est PAS ramené ici : une note qui vient d'être posée peut manquer encore à l'analyse
    const i = Math.max(0, Math.min(noteChoisie, notes.length - 1));
    const n = notes[i];
    const tete = document.createElement("div"); tete.className = "ms-barre";
    const titre = document.createElement("span"); titre.className = "nt-titre";
    titre.textContent = T("photolab.note.titre", { n: i + 1, total: notes.length });
    const auteurEl = document.createElement("span"); auteurEl.className = "nt-auteur"; auteurEl.setAttribute("data-dz-brut", ""); auteurEl.textContent = n.author || "";
    const prec = bouton("photolab.note.precedente", () => { noteChoisie = (i - 1 + notes.length) % notes.length; dessiner(); dessinerNotes(); });
    const suiv = bouton("photolab.note.suivante", () => { noteChoisie = (i + 1) % notes.length; dessiner(); dessinerNotes(); });
    const suppr = bouton("commun.action.supprimer", () => executer("notes.delete", { index: n.index ?? i }));
    tete.append(titre, auteurEl, prec, suiv, suppr);
    const zone = document.createElement("textarea"); zone.className = "nt-texte"; zone.value = n.text || ""; zone.maxLength = 4000; zone.setAttribute("data-dz-brut", "");
    zone.addEventListener("keydown", (ev) => ev.stopPropagation());
    zone.addEventListener("change", () => { if (zone.value !== (n.text || "")) executer("notes.set", { index: n.index ?? i, text: zone.value }); });
    corpsNotes.append(tete, zone);
    if (focusNote) { focusNote = false; zone.focus(); }
  }
  function majPanneaux() {
    const o = PL.ongletDevant ? PL.ongletDevant("#grpInfos", "data-onglet-in") : null;
    if (o === "notes") dessinerNotes();
  }
  PL.mesure = {
    relire, relireJournal, enregistrerMesures,
    surOnglet: (nom) => { if (nom === "mesures") relireJournal(); else if (nom === "notes") relire().then(dessinerNotes); },
    get tranches() { return a.slices; },
    get analyse() { return a; },
    choisirTranche: (t) => { tranche = t; dessiner(); majBarre(); },
  };

  /* Fichier › Importer › Notes : celles d'un autre document ouvert */
  async function importerNotes() {
    const s = PL.etat.session;
    const docs = s && Array.isArray(s.documents) ? s.documents.filter((d) => d.index !== s.active) : [];
    if (!PL.etat.doc || !docs.length) { PL.signaler(T("photolab.note.import_aucun"), true); return; }
    let choix = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.note.import_titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.importer"), principal: true }],
      construire({ corps }) {
        const l = document.createElement("select"); l.setAttribute("data-dz-brut", "");
        const compte = {};
        for (const d of docs) compte[d.name] = (compte[d.name] || 0) + 1;
        for (const d of docs) { const o = document.createElement("option"); o.value = String(d.index); o.textContent = compte[d.name] > 1 ? `${d.name} (${d.index + 1})` : d.name; l.appendChild(o); }
        corps.append(champ("photolab.note.import_source", l));
        const p = document.createElement("p"); p.className = "pf-note"; p.textContent = T("photolab.note.import_aide"); corps.appendChild(p);
        return () => { choix = Number(l.value); return true; };
      },
    });
    if (choix == null) return;
    let r;
    try { r = await PL.file(() => PL.post("/notes/importer", { document: choix })); } catch (e) { return; }
    await PL.cycle();
    PL.signaler(T("photolab.note.importees", { n: r.imported || 0 }));
    montrerPanneau("notes");
  }
  PL.actions = PL.actions || {};
  PL.actions["file.import.notes"] = importerNotes;
  // Fenêtre › Journal des mesures et Fenêtre › Notes : mod-espaces (PANNEAUX), comme les autres panneaux ; l'onglet
  // montré relit ce qu'il affiche (PL.surOngletMontre -> PL.mesure.surOnglet).
}
