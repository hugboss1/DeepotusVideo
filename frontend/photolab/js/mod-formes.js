// mod-formes.js — t156 (parité L6) : outils Rectangle, Ellipse, Triangle, Polygone, Trait et Forme personnalisée (U).
// Glisser = la forme (Maj : carré / proportions / trait à 45° ; Alt : depuis le centre — amont vector_ui.rs
// shape_geometry) ; un aperçu du contour suit le geste ; au relâchement, UN calque de forme : shape.create (triangle =
// polygone à 3 côtés) ou shape.presets.place (forme personnalisée), « New Shape Layer ». Barre d'options : remplissage
// (couleur de premier plan), contour (épaisseur, couleur, alignement), rayon des angles, côtés, épaisseur du trait,
// forme personnalisée. Fonctions PURES exportées (qa/formes.test.mjs).

export const OUTILS_FORME = ["rectangle", "ellipseShape", "triangle", "polygon", "line", "customShape"];
export const FORMES_DEFAUT = { remplir: true, contour: 0, couleurContour: "#000000", alignContour: "center", rayon: 0, cotes: 5, epaisseur: 3 };
export const ALIGNEMENTS_CONTOUR = ["inside", "center", "outside"];
export const LIB_ALIGNEMENTS = { inside: "photolab.formes.align_inside", center: "photolab.formes.align_center", outside: "photolab.formes.align_outside" };
const PAS45 = Math.PI / 4;

// Points DOCUMENT a (appui) et b (pointeur) -> géométrie : {rect: {x, y, w, h}} ou, pour le trait, {de, a}.
export function geometrie(outil, a, b, mods = {}) {
  if (outil === "line") {
    let dx = b[0] - a[0], dy = b[1] - a[1];
    if (mods.maj) {
      const ang = Math.round(Math.atan2(dy, dx) / PAS45) * PAS45, l = Math.hypot(dx, dy);
      dx = l * Math.cos(ang); dy = l * Math.sin(ang);
    }
    return { de: [a[0], a[1]], a: [a[0] + dx, a[1] + dy] };
  }
  let dx = b[0] - a[0], dy = b[1] - a[1];
  if (mods.maj) { const m = Math.max(Math.abs(dx), Math.abs(dy)); dx = Math.sign(dx || 1) * m; dy = Math.sign(dy || 1) * m; }
  let x0 = a[0], y0 = a[1], x1 = a[0] + dx, y1 = a[1] + dy;
  if (mods.alt) { x0 = a[0] - dx; y0 = a[1] - dy; }
  return { rect: { x: Math.min(x0, x1), y: Math.min(y0, y1), w: Math.abs(x1 - x0), h: Math.abs(y1 - y0) } };
}
export const tropPetite = (g) => (g.rect ? g.rect.w < 1 || g.rect.h < 1 : Math.hypot(g.a[0] - g.de[0], g.a[1] - g.de[1]) < 1);

// Polygone régulier (premier sommet en haut) ajusté au cadre : rayon horizontal = demi-largeur, hauteur ajustée au cadre.
export function sommetsPolygone(r, n) {
  const pts = [];
  for (let i = 0; i < n; i++) { const t = -Math.PI / 2 + (i * 2 * Math.PI) / n; pts.push([Math.cos(t), Math.sin(t)]); }
  const ys = pts.map((p) => p[1]), y0 = Math.min(...ys), y1 = Math.max(...ys);
  return pts.map(([u, v]) => [r.x + r.w / 2 + (r.w / 2) * u, r.y + ((v - y0) / (y1 - y0 || 1)) * r.h]);
}
// Contour d'aperçu (points DOCUMENT, fermé) ; null pour le trait (aperçu « ligne »).
export function apercuForme(outil, g, opts = FORMES_DEFAUT) {
  if (outil === "line" || !g.rect) return null;
  const r = g.rect;
  if (outil === "ellipseShape") {
    const pts = [];
    for (let i = 0; i < 48; i++) { const t = (i / 48) * 2 * Math.PI; pts.push([r.x + r.w / 2 + (r.w / 2) * Math.cos(t), r.y + r.h / 2 + (r.h / 2) * Math.sin(t)]); }
    return pts;
  }
  if (outil === "triangle") return sommetsPolygone(r, 3);
  if (outil === "polygon") return sommetsPolygone(r, Math.max(3, Math.min(100, Math.round(opts.cotes) || 5)));
  return [[r.x, r.y], [r.x + r.w, r.y], [r.x + r.w, r.y + r.h], [r.x, r.y + r.h]];
}

const arr = (v) => Math.round(v * 100) / 100;
// Paramètres de remplissage et de contour (amont : remplissage = premier plan si coché ; contour si épaisseur > 0).
export function peinture(opts, fg) {
  const p = { fill: opts.remplir ? fg : null };
  const w = Number(opts.contour) || 0;
  p.stroke = w > 0 ? { width: Math.min(288, w), color: opts.couleurContour || "#000000",
    align: ALIGNEMENTS_CONTOUR.includes(opts.alignContour) ? opts.alignContour : "center" } : null;
  return p;
}
// La commande du moteur pour la géométrie g, ou null (forme de moins d'un pixel).
export function commandeForme(outil, g, opts = FORMES_DEFAUT, fg = "#000000", preset = null, mods = {}) {
  if (!OUTILS_FORME.includes(outil) || tropPetite(g)) return null;
  const pt = peinture(opts, fg);
  if (outil === "line") {
    return { command: "shape.create", params: { kind: "line", from: g.de.map(arr), to: g.a.map(arr),
      weight: Math.max(1, Math.min(1000, Number(opts.epaisseur) || 3)), fill: pt.fill || fg, stroke: pt.stroke } };
  }
  const r = [arr(g.rect.x), arr(g.rect.y), arr(g.rect.w), arr(g.rect.h)];
  if (outil === "customShape") {
    if (!preset || !preset.preset) return null;
    return { command: "shape.presets.place", params: { preset: preset.preset, ...(preset.group ? { group: preset.group } : {}), rect: r,
      keepAspect: !!mods.maj, fill: pt.fill, stroke: pt.stroke } };
  }
  const p = { rect: r, ...pt };
  if (outil === "rectangle") {
    const rayon = Math.max(0, Number(opts.rayon) || 0);
    return { command: "shape.create", params: rayon > 0 ? { kind: "roundedRect", radii: rayon, ...p } : { kind: "rect", ...p } };
  }
  if (outil === "ellipseShape") return { command: "shape.create", params: { kind: "ellipse", ...p } };
  if (outil === "triangle") return { command: "shape.create", params: { kind: "polygon", sides: 3, ...p } };
  return { command: "shape.create", params: { kind: "polygon", sides: Math.max(3, Math.min(100, Math.round(opts.cotes) || 5)), ...p } };
}

/* ───────────── côté DOM ───────────── */

export function initFormes(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const opts = (PL.etat.formes = { ...FORMES_DEFAUT });
  PL.formePersonnalisee = PL.formePersonnalisee || { preset: "Heart", group: "Symbols" };      // amont : Heart par défaut
  let g = null;
  const fg = () => (PL.etat.couleurs && PL.etat.couleurs.fg) || "#000000";
  const mods = (ev) => ({ maj: !!ev.shiftKey, alt: !!ev.altKey });
  const montrer = (outil, geo) => {
    if (!geo) PL.apercu = null;
    else if (outil === "line") PL.apercu = { type: "ligne", de: geo.de, a: geo.a };
    else PL.apercu = { type: "lasso", points: apercuForme(outil, geo, opts) };
    if (PL.dessinerFourmis) PL.dessinerFourmis();
  };
  for (const outil of OUTILS_FORME) {
    PL.gestes[outil] = {
      appui(p) { g = { a: [p.x, p.y], geo: null }; },
      bouger(p, ev) { if (!g) return; g.geo = geometrie(outil, g.a, [p.x, p.y], mods(ev)); montrer(outil, g.geo); },
      relacher(p, ev) {
        if (!g) return;
        const geo = geometrie(outil, g.a, [p.x, p.y], mods(ev));
        g = null; montrer(outil, null);
        const c = commandeForme(outil, geo, opts, fg(), PL.formePersonnalisee, mods(ev));
        if (c) PL.executer(c.command, c.params);
      },
      annuler() { g = null; montrer(outil, null); },
      quitter() { g = null; },
    };
  }

  // Barre d'options des formes (registre PL.barresOutils, lu par mod-outils).
  PL.barresOutils = PL.barresOutils || {};
  const barreFormes = (outil) => (barre) => {
    const champ = (lib, el) => { const w = document.createElement("label"); w.className = "opt fo-champ"; const s = document.createElement("span"); s.textContent = T(lib); w.append(s, el); barre.appendChild(w); return el; };
    const nombre = (cle, lib, min, max, unite) => {
      const n = Object.assign(document.createElement("input"), { type: "number", min, max, step: 1, value: opts[cle] });
      n.addEventListener("change", () => { const v = Math.min(max, Math.max(min, Math.round(Number(n.value)) || 0)); n.value = v; opts[cle] = v; });
      const el = champ(lib, n);
      if (unite) { const u = document.createElement("span"); u.className = "opt-unite"; u.textContent = unite; el.parentNode.appendChild(u); }
      return n;
    };
    const rem = Object.assign(document.createElement("input"), { type: "checkbox", checked: opts.remplir });
    rem.addEventListener("change", () => { opts.remplir = rem.checked; });
    champ("photolab.formes.remplir", rem);
    nombre("contour", "photolab.formes.contour", 0, 288, "px");
    const cc = Object.assign(document.createElement("input"), { type: "color", value: opts.couleurContour });
    cc.addEventListener("change", () => { opts.couleurContour = cc.value; });
    champ("photolab.formes.couleur_contour", cc);
    const al = document.createElement("select");
    for (const v of ALIGNEMENTS_CONTOUR) { const o = document.createElement("option"); o.value = v; o.textContent = T(LIB_ALIGNEMENTS[v]); al.appendChild(o); }
    al.value = opts.alignContour; al.addEventListener("change", () => { opts.alignContour = al.value; });
    champ("photolab.formes.alignement", al);
    if (outil === "rectangle") nombre("rayon", "photolab.formes.rayon", 0, 10000, "px");
    if (outil === "polygon") nombre("cotes", "photolab.formes.cotes", 3, 100);
    if (outil === "line") nombre("epaisseur", "photolab.formes.epaisseur", 1, 1000, "px");
    if (outil === "customShape") {
      const nom = document.createElement("button"); nom.type = "button"; nom.className = "fo-preset";
      const maj = () => { const f = PL.formePersonnalisee; nom.textContent = f && f.preset ? (PL.nomPreset ? PL.nomPreset(f.preset) : f.preset) : "—"; };
      maj();
      nom.title = T("photolab.formes.choisir_forme");
      nom.addEventListener("click", () => { if (PL.actions && PL.actions["window.panel.shapes"]) PL.actions["window.panel.shapes"](); });
      champ("photolab.formes.forme", nom);
    }
  };
  for (const outil of OUTILS_FORME) PL.barresOutils[outil] = barreFormes(outil);
}
