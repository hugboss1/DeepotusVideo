// mod-gestes.js — le répartiteur des gestes du canevas (C3) et le calque d'aperçu #fourmis : chaque outil du canevas
// (sélections, déplacement, recadrage, pipette) s'inscrit dans PL.gestes[id] ; ce module reçoit les événements du
// pointeur sur #toile, les convertit en coordonnées document (versDoc) et les passe à l'outil courant. L'aperçu ne
// dessine que des contours (forme en cours, cadre de recadrage, bornes de la sélection) : jamais de pixels.
// La main (outil, Espace, bouton du milieu) et l'outil Zoom restent à mod-vue.

// Bornes de sélection du moteur [x, y, w, h] -> rectangle écran calé sur le demi-pixel (trait net d'un pixel).
export function formeFourmis(bornes, v) {
  if (!Array.isArray(bornes) || bornes.length < 4) return null;
  return { x: Math.round(bornes[0] * v.z + v.ox) + 0.5, y: Math.round(bornes[1] * v.z + v.oy) + 0.5,
    w: Math.round(bornes[2] * v.z), h: Math.round(bornes[3] * v.z) };
}

const NS = "http://www.w3.org/2000/svg";

export function initGestes(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const toile = PL.$("#toile");
  const svg = PL.$("#fourmis");
  PL.gestes = {};            // id d'outil -> {appui, bouger, relacher, survol?, double?, touche?, quitter?, annuler?}
  PL.apercu = null;          // forme en cours, coordonnées DOCUMENT : {type, …}
  let enCours = null;        // outil dont un geste est en cours (bouton tenu)

  const point = (ev) => {
    const s = PL.vue.pointeur(ev);
    const d = PL.vue.versDoc(s.x, s.y);
    return { x: d.x, y: d.y, sx: s.x, sy: s.y };
  };
  const outil = () => (PL.etat.doc && !PL.vue.mainActive() ? PL.gestes[PL.etat.outil] || null : null);

  toile.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    const g = outil();
    if (!g) return;
    ev.preventDefault();
    enCours = g;
    try { toile.setPointerCapture(ev.pointerId); } catch (e) { /* pointeur déjà relâché */ }
    g.appui(point(ev), ev);
  });
  toile.addEventListener("pointermove", (ev) => {
    if (enCours) {
      if (!(ev.buttons & 1)) { const g = enCours; enCours = null; g.relacher(point(ev), ev); return; }   // relâché hors de la page
      enCours.bouger(point(ev), ev);
      return;
    }
    const g = outil();
    if (g && g.survol) g.survol(point(ev), ev);
  });
  toile.addEventListener("pointerup", (ev) => {
    if (!enCours) return;
    const g = enCours; enCours = null;
    try { toile.releasePointerCapture(ev.pointerId); } catch (e) { /* capture déjà perdue */ }
    g.relacher(point(ev), ev);
  });
  toile.addEventListener("pointercancel", () => { if (enCours) { const g = enCours; enCours = null; if (g.annuler) g.annuler(); } });
  toile.addEventListener("dblclick", (ev) => { const g = outil(); if (g && g.double) { ev.preventDefault(); g.double(point(ev), ev); } });

  // Touches propres à l'outil (Entrée, Échap, flèches, Retour arrière) — hors champ de saisie, menu ou dialogue ouverts.
  const enSaisie = (ev) => ev.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || "") || ev.target.isContentEditable);
  document.addEventListener("keydown", (ev) => {
    if (ev.defaultPrevented || enSaisie(ev) || ev.ctrlKey || ev.metaKey) return;
    if (document.querySelector(".pl-voile, .dz-dialogue, .menu-panneau, .flyout")) return;
    const g = outil();
    if (g && g.touche && g.touche(ev)) ev.preventDefault();
  });

  // Changer d'outil abandonne le geste en cours de l'outil quitté (polygone non fermé, cadre de recadrage…).
  PL.surOutil.push(() => {
    for (const g of Object.values(PL.gestes)) if (g.quitter) g.quitter();
    enCours = null; PL.apercu = null; dessiner();
  });

  /* ── aperçu ── */
  const el = (tag, attrs, classe) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (classe) e.setAttribute("class", classe);
    return e;
  };
  const ecran = (x, y) => PL.vue.versEcran(x, y);
  const chemin = (pts, fermer) => {
    const d = pts.map((p, i) => { const s = ecran(p[0], p[1]); return (i ? "L" : "M") + s.x + " " + s.y; }).join(" ");
    return fermer ? d + "Z" : d;
  };
  // Deux traits superposés (sombre plein + clair pointillé animé) : lisible sur toute image, sans couleur en dur.
  const fourmis = (forme) => [forme.cloneNode(), forme].map((f, i) => { f.setAttribute("class", i ? "fourmis-clair" : "fourmis-sombre"); return f; });

  function dessiner() {
    svg.textContent = "";
    const doc = PL.etat.doc;
    const st = PL.$("#stSelection");
    if (!doc) { if (st) { st.textContent = ""; st.title = ""; } return; }
    const v = PL.vue.v;
    const f = doc.hasSelection ? formeFourmis(doc.selectionBounds, v) : null;
    if (f) for (const n of fourmis(el("rect", { x: f.x, y: f.y, width: f.w, height: f.h }))) svg.appendChild(n);
    if (st) {
      // Le moteur ne donne que les bornes de la sélection en P2 : le contour affiché est un rectangle, on le dit.
      const b = doc.hasSelection && Array.isArray(doc.selectionBounds) ? doc.selectionBounds : null;
      st.textContent = b ? T("photolab.selection.bornes", { w: b[2], h: b[3] }) : "";
      st.title = b ? T("photolab.selection.approx") : "";
    }
    const a = PL.apercu;
    if (!a) return;
    if (a.type === "rect" || a.type === "ellipse") {
      const p0 = ecran(a.x, a.y), p1 = ecran(a.x + a.width, a.y + a.height);
      const forme = a.type === "rect"
        ? el("rect", { x: Math.round(p0.x) + 0.5, y: Math.round(p0.y) + 0.5, width: Math.round(p1.x - p0.x), height: Math.round(p1.y - p0.y) })
        : el("ellipse", { cx: (p0.x + p1.x) / 2, cy: (p0.y + p1.y) / 2, rx: Math.abs(p1.x - p0.x) / 2, ry: Math.abs(p1.y - p0.y) / 2 });
      for (const n of fourmis(forme)) svg.appendChild(n);
    } else if ((a.type === "lasso" || a.type === "poly" || a.type === "trace") && a.points.length) {
      const pts = a.type === "poly" && a.curseur ? [...a.points, a.curseur] : a.points;
      for (const n of fourmis(el("path", { d: chemin(pts, a.type === "lasso"), fill: "none" }))) svg.appendChild(n);
      if (a.type === "poly") {
        const s = ecran(a.points[0][0], a.points[0][1]);
        svg.appendChild(el("circle", { cx: s.x, cy: s.y, r: 4 }, a.fermable ? "poignee actif" : "poignee"));
      }
    } else if (a.type === "recadrage" && a.cadre) {
      const c = a.cadre;
      const p0 = ecran(c.x, c.y), p1 = ecran(c.x + c.width, c.y + c.height);
      const d0 = ecran(0, 0), d1 = ecran(doc.width, doc.height);
      // Hors du cadre, le document est voilé (evenodd : rectangle du document moins le cadre).
      svg.appendChild(el("path", { d: `M${d0.x} ${d0.y}H${d1.x}V${d1.y}H${d0.x}Z M${p0.x} ${p0.y}V${p1.y}H${p1.x}V${p0.y}Z`, "fill-rule": "evenodd" }, "voile-recadrage"));
      svg.appendChild(el("rect", { x: p0.x, y: p0.y, width: p1.x - p0.x, height: p1.y - p0.y }, "cadre-recadrage"));
      for (const [x, y] of [[p0.x, p0.y], [p1.x, p0.y], [p0.x, p1.y], [p1.x, p1.y]]) svg.appendChild(el("rect", { x: x - 4, y: y - 4, width: 8, height: 8 }, "poignee"));
    }
  }
  PL.dessinerFourmis = dessiner;
  PL.surVue.push(dessiner);
  PL.surDoc.push(dessiner);
}
