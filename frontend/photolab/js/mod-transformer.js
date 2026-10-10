// mod-transformer.js — t154 (parité L4) : Édition › Transformation libre (Ctrl+T) et Transformation › Mise à l'échelle,
// Rotation, Inclinaison, Déformation, Perspective. Une SESSION à l'écran : cadre = contenu du calque actif ∩ sélection
// (amont transform_cmds.rs transform_bounds), quadrilatère + point de référence, 8 poignées ; gestes de l'amont
// (transform_tool.rs apply_drag) ; les sous-modes contraignent le geste comme dans l'application de référence (l'amont
// ne contraint rien). L'image montrée pendant la session vient du MOTEUR (/apercu : edit.transform joué sur une copie) ;
// valider = edit.transform {layer, rect, quad, interpolation} (historique « Free Transform »). Fonctions PURES exportées
// (qa/transformation.test.mjs).

export const MODES = { "edit.freeTransform": "libre", "edit.transform.scale": "echelle", "edit.transform.rotate": "rotation",
  "edit.transform.skew": "inclinaison", "edit.transform.distort": "deformation", "edit.transform.perspective": "perspective" };
export const TOLERANCE_PX = 12;                  // amont HANDLE_PX
export const PAS_ROTATION = 15;                  // Maj : pas de 15°
export const INTERPOLATIONS = ["bicubic", "bilinear", "nearest"];
// Libellés (clés écrites en entier : le banc des textes les vérifie).
export const LIB_MODES = { libre: "photolab.transformation.mode_libre", echelle: "photolab.transformation.mode_echelle",
  rotation: "photolab.transformation.mode_rotation", inclinaison: "photolab.transformation.mode_inclinaison",
  deformation: "photolab.transformation.mode_deformation", perspective: "photolab.transformation.mode_perspective" };
export const LIB_INTERP = { bicubic: "photolab.transformation.interp_bicubic", bilinear: "photolab.transformation.interp_bilinear",
  nearest: "photolab.transformation.interp_nearest" };
const RAD = Math.PI / 180;

/* ── géométrie ── */
export const coins = ([x0, y0, x1, y1]) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
// Carré unité -> quadrilatère (HG, HD, BD, BG) : homographie 3 × 3 en ligne [a, b, c, d, e, f, g, h, 1] (Heckbert ;
// affine quand le quadrilatère est un parallélogramme). (u, v) -> ((a u + b v + c) / w, (d u + e v + f) / w), w = g u + h v + 1.
export function carreVersQuad(q) {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = q;
  const sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3;
  if (Math.abs(sx) < 1e-12 && Math.abs(sy) < 1e-12) return [x1 - x0, x3 - x0, x0, y1 - y0, y3 - y0, y0, 0, 0, 1];
  const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2;
  const den = dx1 * dy2 - dx2 * dy1;
  const g = (sx * dy2 - dx2 * sy) / den, h = (dx1 * sy - sx * dy1) / den;
  return [x1 - x0 + g * x1, x3 - x0 + h * x3, x0, y1 - y0 + g * y1, y3 - y0 + h * y3, y0, g, h, 1];
}
export function appliquer(H, [u, v]) {
  const w = H[6] * u + H[7] * v + H[8];
  return [(H[0] * u + H[1] * v + H[2]) / w, (H[3] * u + H[4] * v + H[5]) / w];
}
export function inverse(H) {
  const [a, b, c, d, e, f, g, h, i] = H;
  const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B + c * C;
  if (Math.abs(det) < 1e-12) return null;
  return [A / det, -(b * i - c * h) / det, (b * f - c * e) / det, B / det, (a * i - c * g) / det, -(a * f - c * d) / det,
    C / det, -(a * h - b * g) / det, (a * e - b * d) / det];
}
const sub = (p, q) => [p[0] - q[0], p[1] - q[1]];
const add = (p, q) => [p[0] + q[0], p[1] + q[1]];
const dist = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]);
const tourner = (p, c, a) => { const s = Math.sin(a), k = Math.cos(a), x = p[0] - c[0], y = p[1] - c[1]; return [c[0] + x * k - y * s, c[1] + x * s + y * k]; };
const copie = (e) => ({ ...e, quad: e.quad.map((p) => [p[0], p[1]]), pivot: [e.pivot[0], e.pivot[1]] });

/* ── cadre source ── */
const aPlat = (ls) => (ls || []).flatMap((l) => [l, ...aPlat(l.children)]);
// Le calque actif de doc.inspect et son cadre [x0, y0, x1, y1] (contenu ∩ sélection), ou {erreur: reglage|fond|vide|calque}.
export function cadreSource(doc) {
  if (!doc) return { erreur: "calque" };
  const ls = aPlat(doc.layers);
  const l = ls.find((x) => x.id === doc.activeLayer);
  if (!l) return { erreur: "calque" };
  if (l.kind === "Adjustment" && !l.hasMask) return { erreur: "reglage" };
  const haut = doc.layers || [];
  const fond = haut.length && haut[haut.length - 1] === l && l.name === "Background";
  if (fond && !doc.hasSelection) return { erreur: "fond" };
  const b = Array.isArray(l.bounds) ? l.bounds : null;
  if (!b || b[2] <= 0 || b[3] <= 0) return { erreur: "vide" };
  let [x0, y0, x1, y1] = [b[0], b[1], b[0] + b[2], b[1] + b[3]];
  const s = doc.hasSelection && Array.isArray(doc.selectionBounds) ? doc.selectionBounds : null;
  if (s) { x0 = Math.max(x0, s[0]); y0 = Math.max(y0, s[1]); x1 = Math.min(x1, s[0] + s[2]); y1 = Math.min(y1, s[1] + s[3]); }
  if (x1 - x0 <= 0 || y1 - y0 <= 0) return { erreur: "vide" };
  return { calque: l.id, rect: [x0, y0, x1, y1] };
}
export function etatInitial(rect) {
  return { quad: coins(rect), pivot: [(rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2], inclH: 0, inclV: 0 };
}

/* ── prise ── */
// Point ÉCRAN s, `ecran(x, y)` = document -> écran : {type: coin|bord, i} | {type: pivot|dedans|dehors}. La poignée la
// plus proche dans la tolérance gagne (amont `hit`) ; sinon dedans / dehors (pair-impair dans le quadrilatère écran).
export function prise(etat, s, ecran, tol = TOLERANCE_PX) {
  const q = etat.quad.map((p) => ecran(p[0], p[1]));
  const cands = [];
  q.forEach((p, i) => cands.push({ type: "coin", i, p }));
  q.forEach((p, i) => { const n = q[(i + 1) % 4]; cands.push({ type: "bord", i, p: [(p.x + n.x) / 2, (p.y + n.y) / 2] }); });
  const pv = ecran(etat.pivot[0], etat.pivot[1]);
  cands.push({ type: "pivot", p: pv });
  let best = null, bd = tol;
  for (const c of cands) {
    const P = Array.isArray(c.p) ? { x: c.p[0], y: c.p[1] } : c.p;
    const d = Math.hypot(P.x - s.x, P.y - s.y);
    if (d <= bd) { bd = d; best = c; }
  }
  if (best) return best.type === "pivot" ? { type: "pivot" } : { type: best.type, i: best.i };
  let dedans = false;
  for (let i = 0, j = 3; i < 4; j = i++) {
    if ((q[i].y > s.y) !== (q[j].y > s.y) && s.x < ((q[j].x - q[i].x) * (s.y - q[i].y)) / (q[j].y - q[i].y) + q[i].x) dedans = !dedans;
  }
  return { type: dedans ? "dedans" : "dehors" };
}

// Ce que fait le geste : selon la prise, le mode (sous-menu) et les modificateurs (Ctrl = coin libre / inclinaison,
// Ctrl+Alt+Maj = perspective — amont apply_drag).
export function sorteGeste(p, mode, mods = {}) {
  if (!p) return "rien";
  if (p.type === "pivot") return "pivot";
  if (mode === "rotation") return "rotation";
  if (p.type === "dedans") return "deplacer";
  if (p.type === "dehors") return mode === "libre" ? "rotation" : "rien";
  if (p.type === "coin") {
    if (mode === "perspective" || (mode === "libre" && mods.ctrl && mods.alt && mods.maj)) return "perspective";
    if (mode === "deformation" || (mode === "libre" && mods.ctrl)) return "deformation";
    if (mode === "inclinaison") return "coinAxe";
    return "echelle";
  }
  if (p.type === "bord") {
    if (mode === "inclinaison" || mode === "deformation" || mode === "perspective" || (mode === "libre" && mods.ctrl)) return "inclinaison";
    return "echelle";
  }
  return "rien";
}

const COINS_UNITE = [[0, 0], [1, 0], [1, 1], [0, 1]];
// Le geste de d0 à d1 (points DOCUMENT) appliqué à l'état de départ e0 -> nouvel état (e0 jamais modifié).
export function geste(e0, p, d0, d1, mode, mods = {}) {
  const e = copie(e0);
  const sorte = sorteGeste(p, mode, mods);
  let dx = d1[0] - d0[0], dy = d1[1] - d0[1];
  if (sorte === "pivot") { e.pivot = [d1[0], d1[1]]; return e; }
  if (sorte === "deplacer") {
    if (mods.maj) {           // 8 directions
      const a = Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) * (Math.PI / 4), l = Math.hypot(dx, dy) * Math.cos(Math.atan2(dy, dx) - a);
      dx = l * Math.cos(a); dy = l * Math.sin(a);
    }
    e.quad = e0.quad.map((q) => [q[0] + dx, q[1] + dy]); e.pivot = [e0.pivot[0] + dx, e0.pivot[1] + dy];
    return e;
  }
  if (sorte === "rotation") {
    let da = Math.atan2(d1[1] - e0.pivot[1], d1[0] - e0.pivot[0]) - Math.atan2(d0[1] - e0.pivot[1], d0[0] - e0.pivot[0]);
    if (mods.maj) {
      const base = Math.atan2(e0.quad[1][1] - e0.quad[0][1], e0.quad[1][0] - e0.quad[0][0]);
      const pas = PAS_ROTATION * RAD;
      da = Math.round((base + da) / pas) * pas - base;
    }
    e.quad = e0.quad.map((q) => tourner(q, e0.pivot, da));
    return e;
  }
  if (sorte === "perspective" || sorte === "coinAxe") {
    const horiz = Math.abs(dx) >= Math.abs(dy);
    const m = horiz ? [dx, 0] : [0, dy];
    e.quad[p.i] = add(e0.quad[p.i], m);
    if (sorte === "perspective") {
      const paire = horiz ? [1, 0, 3, 2][p.i] : [3, 2, 1, 0][p.i];
      e.quad[paire] = sub(e0.quad[paire], m);
    }
    return e;
  }
  if (sorte === "deformation") { e.quad[p.i] = [e0.quad[p.i][0] + dx, e0.quad[p.i][1] + dy]; return e; }
  if (sorte === "inclinaison") {
    const i = p.i, j = (i + 1) % 4;
    let m = [dx, dy];
    if (mods.maj) {            // le long du bord
      const b = sub(e0.quad[j], e0.quad[i]), l = Math.hypot(b[0], b[1]) || 1, k = (dx * b[0] + dy * b[1]) / (l * l);
      m = [b[0] * k, b[1] * k];
    }
    e.quad[i] = add(e0.quad[i], m); e.quad[j] = add(e0.quad[j], m);
    if (mods.alt) { const o = (i + 2) % 4, o2 = (i + 3) % 4; e.quad[o] = sub(e0.quad[o], m); e.quad[o2] = sub(e0.quad[o2], m); }
    return e;
  }
  if (sorte === "echelle") {
    const H = carreVersQuad(e0.quad), Hi = inverse(H);
    if (!Hi) return e;
    const u0 = appliquer(Hi, d0), u1 = appliquer(Hi, d1), du = [u1[0] - u0[0], u1[1] - u0[1]];
    const pu = appliquer(Hi, e0.pivot);
    let kx = 1, ky = 1, f;
    if (p.type === "coin") {
      const c = COINS_UNITE[p.i];
      f = mods.alt ? pu : [1 - c[0], 1 - c[1]];
      const m = [c[0] + du[0], c[1] + du[1]];
      kx = (c[0] - f[0]) ? (m[0] - f[0]) / (c[0] - f[0]) : 1;
      ky = (c[1] - f[1]) ? (m[1] - f[1]) / (c[1] - f[1]) : 1;
      if (!mods.maj) { const k = Math.abs(kx) >= Math.abs(ky) ? kx : ky; kx = Math.sign(kx || 1) * Math.abs(k); ky = Math.sign(ky || 1) * Math.abs(k); }
    } else {
      // bord 0 = haut (v = 0), 1 = droite (u = 1), 2 = bas (v = 1), 3 = gauche (u = 0)
      const axeU = p.i === 1 || p.i === 3, c = p.i === 0 || p.i === 3 ? 0 : 1;
      if (axeU) { f = mods.alt ? pu : [1 - c, 0]; const den = c - f[0]; kx = den ? (c + du[0] - f[0]) / den : 1; f = [f[0], 0]; }
      else { f = mods.alt ? pu : [0, 1 - c]; const den = c - f[1]; ky = den ? (c + du[1] - f[1]) / den : 1; f = [0, f[1]]; }
    }
    const k = (uv) => [f[0] + kx * (uv[0] - f[0]), f[1] + ky * (uv[1] - f[1])];
    e.quad = COINS_UNITE.map((uv) => appliquer(H, k(uv)));
    e.pivot = appliquer(H, k(pu));
    return e;
  }
  return e;
}

/* ── barre d'options ── */
const norm180 = (a) => { let x = a; while (x > 180) x -= 360; while (x <= -180) x += 360; return x; };
const arr = (v, n = 2) => Math.round(v * 10 ** n) / 10 ** n;
// Valeurs affichées : X / Y du point de référence (relatifs à son départ si `relatif`), L % / H % (bords haut et gauche
// rapportés au cadre source), angle du bord haut, inclinaisons cumulées par les champs.
export function lecture(etat, rect, pivot0, relatif = false) {
  const q = etat.quad, w = rect[2] - rect[0], h = rect[3] - rect[1];
  return {
    x: arr(relatif ? etat.pivot[0] - pivot0[0] : etat.pivot[0], 1), y: arr(relatif ? etat.pivot[1] - pivot0[1] : etat.pivot[1], 1),
    l: arr((dist(q[0], q[1]) / w) * 100, 1), h: arr((dist(q[0], q[3]) / h) * 100, 1),
    angle: arr(norm180(Math.atan2(q[1][1] - q[0][1], q[1][0] - q[0][0]) / RAD), 1),
    inclH: arr(etat.inclH, 1), inclV: arr(etat.inclV, 1),
  };
}
export function placerPivot(etat, x, y) {
  const e = copie(etat), dx = x - etat.pivot[0], dy = y - etat.pivot[1];
  e.quad = etat.quad.map((q) => [q[0] + dx, q[1] + dy]); e.pivot = [x, y];
  return e;
}
// Échelle (kx, ky) dans le repère propre du cadre, autour du point de référence (amont scale_about_pivot).
export function echelleAutour(etat, kx, ky) {
  const H = carreVersQuad(etat.quad), Hi = inverse(H);
  if (!Hi || !isFinite(kx) || !isFinite(ky) || kx === 0 || ky === 0) return etat;
  const f = appliquer(Hi, etat.pivot), e = copie(etat);
  e.quad = COINS_UNITE.map((uv) => appliquer(H, [f[0] + kx * (uv[0] - f[0]), f[1] + ky * (uv[1] - f[1])]));
  return e;
}
export function rotationAutour(etat, degres) {
  const e = copie(etat);
  e.quad = etat.quad.map((q) => tourner(q, etat.pivot, degres * RAD));
  return e;
}
// Inclinaison de `degres` le long du bord haut (axe "h") ou du bord gauche (axe "v"), autour du point de référence.
export function inclinerAutour(etat, axe, degres) {
  const e = copie(etat), t = Math.tan(degres * RAD);
  const a = Math.atan2(etat.quad[1][1] - etat.quad[0][1], etat.quad[1][0] - etat.quad[0][0]);
  const e1 = [Math.cos(a), Math.sin(a)], e2 = [-Math.sin(a), Math.cos(a)];
  e.quad = etat.quad.map((q) => {
    const r = sub(q, etat.pivot), s1 = r[0] * e1[0] + r[1] * e1[1], s2 = r[0] * e2[0] + r[1] * e2[1];
    return axe === "h" ? add(q, [e1[0] * t * s2, e1[1] * t * s2]) : add(q, [e2[0] * t * s1, e2[1] * t * s1]);
  });
  if (axe === "h") e.inclH = etat.inclH + degres; else e.inclV = etat.inclV + degres;
  return e;
}
// Point de référence de la grille 3 × 3 (0 = haut gauche … 4 = centre … 8 = bas droite), dans le repère du cadre.
export function pointReference(etat, i) {
  const H = carreVersQuad(etat.quad);
  return { ...copie(etat), pivot: appliquer(H, [(i % 3) / 2, Math.floor(i / 3) / 2]) };
}

/* ── validation ── */
export function estIdentite(etat, rect) {
  return coins(rect).every((c, i) => Math.abs(c[0] - etat.quad[i][0]) < 1e-6 && Math.abs(c[1] - etat.quad[i][1]) < 1e-6);
}
export function commande(etat, rect, calque, interpolation = "bicubic") {
  if (estIdentite(etat, rect)) return null;
  const q = etat.quad.map((p) => [arr(p[0], 3), arr(p[1], 3)]);
  return { command: "edit.transform", params: { layer: calque, rect: [...rect], quad: q, interpolation: INTERPOLATIONS.includes(interpolation) ? interpolation : "bicubic" } };
}
export const CURSEURS = { coin: ["nwse-resize", "nesw-resize", "nwse-resize", "nesw-resize"], bord: ["ns-resize", "ew-resize", "ns-resize", "ew-resize"],
  pivot: "crosshair", dedans: "move", dehors: "alias" };
export function curseur(p, mode) {
  if (!p) return "default";
  if (p.type === "coin" || p.type === "bord") return CURSEURS[p.type][p.i];
  if (mode === "rotation" && p.type !== "pivot") return "alias";
  if (p.type === "dehors" && mode !== "libre") return "default";
  return CURSEURS[p.type];
}

/* ───────────── côté DOM ───────────── */

export function initTransformer(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const toile = PL.$("#toile");
  let s = null;            // session : {mode, rect, calque, etat, pivot0, pile, interp, relatif, lie}
  let g = null;            // geste : {prise, d0, e0}
  let minut = null, numero = 0;
  const ERREURS = { reglage: "photolab.transformation.erreur_reglage", fond: "photolab.transformation.erreur_fond",
    vide: "photolab.transformation.erreur_vide", calque: "photolab.transformation.erreur_calque" };

  function demarrer(mode) {
    const d = PL.etat.doc;
    if (!d) return;
    if (s) { s.mode = mode; construireBarre(); redessiner(); return; }
    const c = cadreSource(d);
    if (c.erreur) { PL.signaler(T(ERREURS[c.erreur]), true); return; }
    const e = etatInitial(c.rect);
    s = { mode, rect: c.rect, calque: c.calque, etat: e, pivot0: [...e.pivot], pile: [], interp: "bicubic", relatif: false, lie: true };
    document.body.classList.add("en-transformation");
    construireBarre();
    redessiner();
  }
  function fin() {
    s = null; g = null; clearTimeout(minut);
    document.body.classList.remove("en-transformation");
    if (PL.reconstruireOptions) PL.reconstruireOptions();
    toile.style.cursor = "";
    redessiner();
  }
  function annuler() {
    if (!s) return;
    fin();
    if (PL.rendre) PL.rendre(PL.vue.maxSideVoulu());          // l'image d'avant : le dernier rendu du moteur
  }
  function valider() {
    if (!s) return;
    const c = commande(s.etat, s.rect, s.calque, s.interp);
    fin();
    if (c) PL.executer(c.command, c.params); else if (PL.rendre) PL.rendre(PL.vue.maxSideVoulu());
  }
  function changer(e, empiler = true) {
    if (empiler) { s.pile.push(s.etat); if (s.pile.length > 100) s.pile.shift(); }
    s.etat = e;
    majBarre(); redessiner(); apercu();
  }
  // L'image de la session : edit.transform joué par le moteur sur une COPIE (/apercu), la dernière demande gagne.
  function apercu() {
    clearTimeout(minut);
    minut = setTimeout(async () => {
      if (!s) return;
      const c = commande(s.etat, s.rect, s.calque, s.interp), n = ++numero;
      if (!c) { if (PL.rendre) PL.rendre(PL.vue.maxSideVoulu()); return; }
      const m = PL.vue.maxSideVoulu();
      let r;
      try { r = await PL.post("/apercu", { etapes: [c], maxSide: Math.max(64, Math.min(2048, m || 1024)) }); } catch (e) { return; }
      if (!s || n !== numero || !r || !r.url) return;
      const im = new Image();
      im.onload = () => { if (s && n === numero) PL.vue.poserApercu(im, m); };
      im.src = r.url;
    }, 120);
  }
  function redessiner() { if (PL.dessinerFourmis) PL.dessinerFourmis(); }
  // Contour, 8 poignées, point de référence — appelé par le dessin de #fourmis (mod-gestes).
  PL.dessinerTransformation = (svg, el, ecran) => {
    if (!s) return;
    const q = s.etat.quad.map((p) => ecran(p[0], p[1]));
    svg.appendChild(el("path", { d: "M" + q.map((p) => p.x + " " + p.y).join(" L") + " Z", fill: "none" }, "transfo-cadre"));
    const pts = [...q, ...q.map((p, i) => { const n = q[(i + 1) % 4]; return { x: (p.x + n.x) / 2, y: (p.y + n.y) / 2 }; })];
    for (const p of pts) svg.appendChild(el("rect", { x: p.x - 3.5, y: p.y - 3.5, width: 7, height: 7 }, "transfo-poignee"));
    const pv = ecran(s.etat.pivot[0], s.etat.pivot[1]);
    svg.appendChild(el("circle", { cx: pv.x, cy: pv.y, r: 5 }, "transfo-pivot"));
    svg.appendChild(el("path", { d: `M${pv.x - 8} ${pv.y}H${pv.x + 8}M${pv.x} ${pv.y - 8}V${pv.y + 8}` }, "transfo-croix"));
  };
  const mods = (ev) => ({ ctrl: !!(ev.ctrlKey || ev.metaKey), alt: !!ev.altKey, maj: !!ev.shiftKey });
  const gestes = {
    appui(p, ev) {
      if (!s) return;
      let pr = prise(s.etat, { x: p.sx, y: p.sy }, PL.vue.versEcran);
      if (ev.altKey && (pr.type === "dedans" || pr.type === "dehors")) {      // Alt-clic : le point de référence ici
        s.pile.push(s.etat); s.etat = { ...s.etat, pivot: [p.x, p.y] }; pr = { type: "pivot" };
      }
      g = { prise: pr, d0: [p.x, p.y], e0: s.etat };
    },
    bouger(p, ev) {
      if (!s || !g) return;
      s.etat = geste(g.e0, g.prise, g.d0, [p.x, p.y], s.mode, mods(ev));
      majBarre(); redessiner();
    },
    relacher() {
      if (!s || !g) return;
      const e0 = g.e0; g = null;
      if (s.etat !== e0) { s.pile.push(e0); apercu(); }
    },
    survol(p) { if (s) toile.style.cursor = curseur(prise(s.etat, { x: p.sx, y: p.sy }, PL.vue.versEcran), s.mode); },
    double() { valider(); },
    touche(ev) {
      if (!s) return false;
      if (ev.key === "Enter") { valider(); return true; }
      if (ev.key === "Escape") { annuler(); return true; }
      const fl = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
      if (fl) { const k = ev.shiftKey ? 10 : 1; changer(placerPivot(s.etat, s.etat.pivot[0] + fl[0] * k, s.etat.pivot[1] + fl[1] * k)); return true; }
      return false;
    },
    annuler() { g = null; },
  };
  // Mode prioritaire : tant qu'une session est ouverte, le répartiteur des gestes (mod-gestes) lui passe la main.
  PL.gestesPrioritaires = () => (s ? gestes : null);
  // Ctrl+Z / Ctrl+Maj+Z dans la session : le pas précédent du cadre, pas l'historique du document (amont Steps).
  document.addEventListener("keydown", (ev) => {
    if (!s || !(ev.ctrlKey || ev.metaKey) || (ev.key || "").toLowerCase() !== "z") return;
    ev.preventDefault(); ev.stopPropagation();
    if (!ev.shiftKey && s.pile.length) { s.etat = s.pile.pop(); majBarre(); redessiner(); apercu(); }
  }, true);
  PL.surOutil.push(() => { if (s) annuler(); });
  PL.surDoc.push((doc) => { if (s && (!doc || !cadreSource(doc).rect)) fin(); });

  /* barre d'options de la session */
  let champs = {};
  function construireBarre() {
    const barre = PL.$("#options");
    barre.textContent = "";
    champs = {};
    const nom = document.createElement("span"); nom.className = "opt-nom";
    nom.textContent = T(LIB_MODES[s.mode]);
    barre.appendChild(nom);
    // point de référence : grille 3 × 3
    const grille = document.createElement("div"); grille.className = "tr-grille"; grille.setAttribute("role", "group");
    grille.setAttribute("aria-label", T("photolab.transformation.reference"));
    // G4 : l'icône « point de référence » devant la grille (décor : le groupe porte le libellé)
    const icoRef = document.createElement("span"); icoRef.className = "tr-ref-ico"; icoRef.innerHTML = PL.icone("dz-edit-point-reference");
    barre.appendChild(icoRef);
    for (let i = 0; i < 9; i++) {
      const b = document.createElement("button"); b.type = "button"; b.className = "tr-ref"; b.dataset.ref = String(i);
      b.title = T("photolab.transformation.reference"); b.addEventListener("click", () => changer(pointReference(s.etat, i)));
      grille.appendChild(b);
    }
    barre.appendChild(grille);
    const num = (cle, lib, unite, poser) => {
      const w = document.createElement("label"); w.className = "opt opt-nombre tr-champ";
      const l = document.createElement("span"); l.className = "opt-lib"; l.textContent = T(lib);
      const i = document.createElement("input"); i.type = "number"; i.step = "any"; i.className = "tr-" + cle; i.setAttribute("aria-label", T(lib));
      const u = document.createElement("span"); u.className = "tr-unite"; u.textContent = unite;
      i.addEventListener("change", () => { const v = Number(i.value); if (isFinite(v)) poser(v); });
      i.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); i.dispatchEvent(new Event("change")); } ev.stopPropagation(); });
      w.append(l, i, u); barre.appendChild(w); champs[cle] = i;
    };
    const delta = document.createElement("button"); delta.type = "button"; delta.className = "tr-bascule tr-delta"; delta.innerHTML = PL.icone("dz-edit-relatif");
    delta.title = T("photolab.transformation.relatif"); delta.setAttribute("aria-label", delta.title);
    delta.addEventListener("click", () => { s.relatif = !s.relatif; delta.classList.toggle("actif", s.relatif); majBarre(); });
    barre.appendChild(delta);
    num("x", "photolab.transformation.x", "px", (v) => changer(placerPivot(s.etat, s.relatif ? s.pivot0[0] + v : v, s.etat.pivot[1])));
    num("y", "photolab.transformation.y", "px", (v) => changer(placerPivot(s.etat, s.etat.pivot[0], s.relatif ? s.pivot0[1] + v : v)));
    num("l", "photolab.transformation.l", "%", (v) => { const a = lecture(s.etat, s.rect, s.pivot0); const k = v / a.l; changer(echelleAutour(s.etat, k, s.lie ? k : 1)); });
    const lien = document.createElement("button"); lien.type = "button"; lien.className = "tr-bascule tr-lien actif"; lien.innerHTML = PL.icone("dz-edit-conserver-proportions");
    lien.title = T("photolab.transformation.lier"); lien.setAttribute("aria-label", lien.title); lien.setAttribute("aria-pressed", "true");
    lien.addEventListener("click", () => { s.lie = !s.lie; lien.classList.toggle("actif", s.lie); lien.setAttribute("aria-pressed", String(s.lie)); });
    barre.appendChild(lien);
    num("h", "photolab.transformation.h", "%", (v) => { const a = lecture(s.etat, s.rect, s.pivot0); const k = v / a.h; changer(echelleAutour(s.etat, s.lie ? k : 1, k)); });
    num("angle", "photolab.transformation.angle", "°", (v) => changer(rotationAutour(s.etat, v - lecture(s.etat, s.rect, s.pivot0).angle)));
    num("inclH", "photolab.transformation.incl_h", "°", (v) => changer(inclinerAutour(s.etat, "h", v - s.etat.inclH)));
    num("inclV", "photolab.transformation.incl_v", "°", (v) => changer(inclinerAutour(s.etat, "v", v - s.etat.inclV)));
    const wi = document.createElement("label"); wi.className = "opt opt-liste tr-champ";
    const li = document.createElement("span"); li.className = "opt-lib"; li.textContent = T("photolab.transformation.interpolation");
    const sel = document.createElement("select"); sel.className = "tr-interp";
    for (const v of INTERPOLATIONS) { const o = document.createElement("option"); o.value = v; o.textContent = T(LIB_INTERP[v]); sel.appendChild(o); }
    sel.value = s.interp; sel.addEventListener("change", () => { s.interp = sel.value; apercu(); });
    wi.append(li, sel); barre.appendChild(wi);
    const ok = document.createElement("button"); ok.type = "button"; ok.className = "tr-valider"; ok.innerHTML = PL.icone("dz-action-valider");
    ok.title = T("photolab.transformation.valider"); ok.setAttribute("aria-label", ok.title); ok.addEventListener("click", valider);
    const ko = document.createElement("button"); ko.type = "button"; ko.className = "tr-annuler"; ko.innerHTML = PL.icone("dz-action-abandonner");
    ko.title = T("photolab.transformation.annuler"); ko.setAttribute("aria-label", ko.title); ko.addEventListener("click", annuler);
    barre.append(ok, ko);
    majBarre();
  }
  function majBarre() {
    if (!s) return;
    const a = lecture(s.etat, s.rect, s.pivot0, s.relatif);
    for (const k of Object.keys(champs)) if (document.activeElement !== champs[k]) champs[k].value = String(a[k]);
  }

  PL.actions = PL.actions || {};
  for (const [id, mode] of Object.entries(MODES)) PL.actions[id] = () => demarrer(mode);
  PL.transformation = { demarrer, valider, annuler, etat: () => (s ? { ...s, etat: copie(s.etat) } : null) };
}
