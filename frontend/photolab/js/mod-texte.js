// mod-texte.js — t156 (parité L6) : outil Texte (T), panneaux Caractère, Paragraphe, Glyphes, Styles de caractère et
// Styles de paragraphe, menu Texte (Panneaux, Taille de l'aperçu des polices, Options de langue).
// Outil (amont type_tool.rs) : clic = texte de point (ligne de base au point), glisser ≥ 4 px = texte de paragraphe, clic
// sur un calque de texte = l'éditer. La saisie se fait dans un ÉDITEUR posé sur la toile (zone de texte à la police et à
// la taille du calque) ; Ctrl+Entrée, Échap (comme la référence et l'amont), un clic ailleurs ou un autre outil valident ;
// le bouton Annuler abandonne. Valider = type.create (« New Type Layer ») ou type.edit {text} (« Edit Type ») : le
// moteur rend le texte (D1). Caractère / Paragraphe appliquent type.setStyle à la sélection de l'éditeur (range) ou au
// calque. Fonctions PURES exportées (qa/texte.test.mjs).
import { demanderNom } from "./mod-nommer.js";

export const DEFAUT_TEXTE = { font: "Inter", weight: 400, italic: false, size: 48, align: "left", antialias: "sharp", orientation: "horizontal" };
export const SEUIL_BOITE_PX = 4;
export const ANTICRENELAGES = ["none", "sharp", "crisp", "strong", "smooth"];
export const ALIGNS = ["left", "center", "right", "justifyLeft", "justifyCenter", "justifyRight", "justifyAll"];
// Le moteur nomme « justify » la justification dont la dernière ligne est à gauche.
export const alignMoteur = (a) => (a === "justifyLeft" ? "justify" : a);
// Noms des poids (amont styles()) — clés écrites en entier.
export const NOMS_POIDS = { 100: "photolab.texte.poids_100", 200: "photolab.texte.poids_200", 300: "photolab.texte.poids_300",
  400: "photolab.texte.poids_400", 500: "photolab.texte.poids_500", 600: "photolab.texte.poids_600", 700: "photolab.texte.poids_700",
  800: "photolab.texte.poids_800", 900: "photolab.texte.poids_900" };
export const LIB_AA = { none: "photolab.texte.aa_none", sharp: "photolab.texte.aa_sharp", crisp: "photolab.texte.aa_crisp",
  strong: "photolab.texte.aa_strong", smooth: "photolab.texte.aa_smooth" };
export const LIB_ALIGNS = { left: "photolab.texte.align_left", center: "photolab.texte.align_center", right: "photolab.texte.align_right",
  justifyLeft: "photolab.texte.align_justify_left", justifyCenter: "photolab.texte.align_justify_center",
  justifyRight: "photolab.texte.align_justify_right", justifyAll: "photolab.texte.align_justify_all" };
// G4 : icône de chaque alignement (suite Deepotus Glyph), barre d'options et panneau Paragraphe.
export const ICONES_ALIGN = { left: "dz-edit-texte-aligner-gauche", center: "dz-edit-texte-aligner-centre", right: "dz-edit-texte-aligner-droite",
  justifyLeft: "dz-edit-justifier-gauche", justifyCenter: "dz-edit-justifier-centre", justifyRight: "dz-edit-justifier-droite",
  justifyAll: "dz-edit-justifier" };

// Taille de l'aperçu des polices (menu Texte) : px des noms dans la liste des polices.
export const APERCUS = { "type.fontPreviewSize.small": 11, "type.fontPreviewSize.medium": 14, "type.fontPreviewSize.large": 18,
  "type.fontPreviewSize.extraLarge": 24, "type.fontPreviewSize.huge": 32 };
export const LANGUES = ["type.languageOptions.defaultFeatures", "type.languageOptions.eastAsianFeatures", "type.languageOptions.middleEasternFeatures"];
export const COMPOSEUR = "type.languageOptions.middleEasternAndSouthAsianComposer";
// t159 : valeur de Préférences › Texte › Aperçu des polices -> entrée du menu Texte › Taille de l'aperçu.
export const APERCU_PREF = { small: "type.fontPreviewSize.small", medium: "type.fontPreviewSize.medium", large: "type.fontPreviewSize.large",
  extraLarge: "type.fontPreviewSize.extraLarge", huge: "type.fontPreviewSize.huge" };
export const PREFS_DEFAUT = { apercu: "type.fontPreviewSize.medium", langue: "type.languageOptions.defaultFeatures", composeur: false };
// Texte › Panneaux › et Fenêtre › -> onglet du groupe Texte.
export const PANNEAUX_TEXTE = { "type.panels.character": "caractere", "type.panels.paragraph": "paragraphe", "type.panels.glyphs": "glyphes",
  "type.panels.characterStyles": "stylesCar", "type.panels.paragraphStyles": "stylesPar" };

/* ── polices ── */
const roundW = (w) => Math.min(900, Math.max(100, Math.round(w / 100) * 100));
export function stylesDe(faces) {
  const vus = new Map();
  for (const f of faces || []) { const w = roundW(Number(f.weight) || 400), it = !!f.italic; vus.set(w + (it ? "i" : ""), { weight: w, italic: it }); }
  return [...vus.values()].sort((a, b) => a.weight - b.weight || Number(a.italic) - Number(b.italic));
}
export const nomStyle = (s, t) => t(NOMS_POIDS[roundW(s.weight)]) + (s.italic ? " " + t("photolab.texte.italique") : "");

/* ── lecture de type.info ── */
const h2 = (v) => Math.round(Math.max(0, Math.min(1, Number(v) || 0)) * 255).toString(16).padStart(2, "0");
export function couleurHex(c) {
  const v = c && (Array.isArray(c) ? c : c.c);
  return Array.isArray(v) && v.length >= 3 ? "#" + h2(v[0]) + h2(v[1]) + h2(v[2]) : "#000000";
}
const dans = (r, i) => i >= r.start && (i < r.end || (r.start === r.end && i === r.start));
// Valeurs des panneaux Caractère et Paragraphe à la position `i` (début de la sélection) — amont styles_at.
export function lecture(info, i = 0) {
  if (!info || !Array.isArray(info.runs) || !info.runs.length) return null;
  const run = info.runs.find((r) => dans(r, i)) || info.runs[0];
  const par = (info.paragraphs || []).find((p) => dans(p, i)) || (info.paragraphs || [])[0] || { style: {} };
  const s = run.style || {}, p = par.style || {};
  const auto = s.leading_pt == null;
  return {
    font: s.font_family || DEFAUT_TEXTE.font, weight: roundW(Number(s.weight) || 400), italic: !!s.italic, size: Number(s.size_pt) || 12,
    leading: auto ? "auto" : s.leading_pt, autoLeading: Number(p.auto_leading) || 1.2,
    kerning: typeof s.kerning === "string" ? s.kerning.toLowerCase() : s.kerning, tracking: Number(s.tracking) || 0,
    verticalScale: Math.round((Number(s.vertical_scale) || 1) * 1000) / 10, horizontalScale: Math.round((Number(s.horizontal_scale) || 1) * 1000) / 10,
    baselineShift: Number(s.baseline_shift_pt) || 0, color: couleurHex(s.color),
    fauxBold: !!s.faux_bold, fauxItalic: !!s.faux_italic, caps: String(s.caps || "Normal").toLowerCase(), underline: !!s.underline,
    strikethrough: !!s.strikethrough,
    align: alignDe(p.align), startIndent: Number(p.start_indent_pt) || 0, endIndent: Number(p.end_indent_pt) || 0,
    firstLineIndent: Number(p.first_line_indent_pt) || 0, spaceBefore: Number(p.space_before_pt) || 0, spaceAfter: Number(p.space_after_pt) || 0,
    hyphenate: !!p.hyphenate, direction: String(p.direction || "Auto").toLowerCase(),
    antialias: String(info.antialias || "Smooth").toLowerCase(), orientation: String(info.orientation || "Horizontal").toLowerCase(),
    texte: info.text || "", boite: info.shape === "Box" || (info.shape && info.shape.Box) ? true : false,
  };
}
export function alignDe(a) {
  const s = String(a || "Left");
  const m = { Left: "left", Center: "center", Right: "right", JustifyLeft: "justifyLeft", Justify: "justifyLeft", JustifyCenter: "justifyCenter",
    JustifyRight: "justifyRight", JustifyAll: "justifyAll" };
  return m[s] || (ALIGNS.includes(s) ? s : "left");
}

/* ── création et édition ── */
// Calque de texte sous le point DOCUMENT p (le plus haut d'abord, marge `slop` px) — amont hit_layer.
export function calqueTexteSous(doc, p, slop = 6) {
  const plats = [];
  const voir = (ls) => { for (const l of ls || []) { plats.push(l); voir(l.children); } };
  voir(doc && doc.layers);
  return plats.find((l) => l.kind === "Type" && l.visible !== false && Array.isArray(l.bounds)
    && p[0] >= l.bounds[0] - slop && p[0] <= l.bounds[0] + l.bounds[2] + slop && p[1] >= l.bounds[1] - slop && p[1] <= l.bounds[1] + l.bounds[3] + slop) || null;
}
// Glisser de a à b (points DOCUMENT), z = zoom : boîte de paragraphe si le glisser dépasse 4 px écran sur les deux axes.
export function placement(a, b, z = 1) {
  const w = Math.abs(b[0] - a[0]), h = Math.abs(b[1] - a[1]);
  if (w * z >= SEUIL_BOITE_PX && h * z >= SEUIL_BOITE_PX) return { box: [Math.min(a[0], b[0]), Math.min(a[1], b[1]), w, h].map((v) => Math.round(v * 100) / 100) };
  return { x: Math.round(a[0] * 100) / 100, y: Math.round(a[1] * 100) / 100 };
}
// type.create pour un texte neuf (vide -> null : aucun calque).
export function paramsCreation(pl, texte, opts, couleur) {
  if (!String(texte || "").trim()) return null;
  const p = { ...pl, text: String(texte), font: opts.font, weight: opts.weight, italic: !!opts.italic, size: opts.size, color: couleur };
  if (opts.align && opts.align !== "left") p.align = alignMoteur(opts.align);
  return p;
}
// type.edit pour un calque existant (inchangé -> null).
export const paramsEdition = (calque, avant, apres) => (String(apres) === String(avant) ? null : { layer: calque, text: String(apres) });

// Champ d'un panneau -> clés de type.setStyle.
export function paramsStyle(champ, valeur) {
  switch (champ) {
    case "style": return { weight: valeur.weight, italic: !!valeur.italic };
    case "leading": return { leading: valeur === "auto" ? "auto" : Number(valeur) };
    case "kerning": return { kerning: ["metrics", "optical", "off"].includes(valeur) ? valeur : Number(valeur) };
    case "caps": return { caps: valeur };
    case "align": return { align: alignMoteur(valeur) };
    default: return { [champ]: valeur };
  }
}

/* ── glyphes ── */
// Catégories de l'amont (text/src/glyphs.rs), sans lecture de la table de la police : tous les points de code du bloc.
export const CATEGORIES = [
  { id: "latinBase", cle: "photolab.glyphes.latin_base", plages: [[0x21, 0x7e]] },
  { id: "latin1", cle: "photolab.glyphes.latin1", plages: [[0xa1, 0xff]] },
  { id: "latinA", cle: "photolab.glyphes.latin_a", plages: [[0x100, 0x17f]] },
  { id: "latinB", cle: "photolab.glyphes.latin_b", plages: [[0x180, 0x24f]] },
  { id: "grec", cle: "photolab.glyphes.grec", plages: [[0x370, 0x3ff]] },
  { id: "cyrillique", cle: "photolab.glyphes.cyrillique", plages: [[0x400, 0x4ff]] },
  { id: "ponctuation", cle: "photolab.glyphes.ponctuation", plages: [[0x2010, 0x2027], [0x2030, 0x205e]] },
  { id: "monnaies", cle: "photolab.glyphes.monnaies", plages: [[0x20a0, 0x20c0]] },
  { id: "symboles", cle: "photolab.glyphes.symboles", plages: [[0x2100, 0x214f], [0x2190, 0x21ff]] },
  { id: "maths", cle: "photolab.glyphes.maths", plages: [[0x2200, 0x22ff]] },
  { id: "ornements", cle: "photolab.glyphes.ornements", plages: [[0x2600, 0x26ff], [0x2700, 0x27bf]] },
];
export function caracteres(cat) {
  const c = CATEGORIES.find((x) => x.id === cat) || CATEGORIES[0];
  const out = [];
  for (const [a, b] of c.plages) for (let i = a; i <= b; i++) if (!(i >= 0x7f && i <= 0x9f)) out.push(String.fromCodePoint(i));
  return out;
}
export const recents = (liste, ch, max = 12) => [ch, ...(liste || []).filter((x) => x !== ch)].slice(0, max);
export const pointDeCode = (ch) => "U+" + ch.codePointAt(0).toString(16).toUpperCase().padStart(4, "0");

/* ── menu Texte ── */
export function decorerTexte(menus, prefs) {
  const p = { ...PREFS_DEFAUT, ...(prefs || {}) };
  const voir = (es) => (es || []).map((e) => {
    if (e.type === "sous-menu") return { ...e, entrees: voir(e.entrees) };
    if (APERCUS[e.id] != null) return { ...e, etat: "actif", coche: p.apercu === e.id };
    if (LANGUES.includes(e.id)) return { ...e, etat: "actif", coche: p.langue === e.id };
    if (e.id === COMPOSEUR) return { ...e, etat: "actif", coche: !!p.composeur };
    if (PANNEAUX_TEXTE[e.id]) return { ...e, etat: "actif" };
    return e;
  });
  return (menus || []).map((m) => ({ ...m, entrees: voir(m.entrees) }));
}
export function basculerPref(prefs, id) {
  const p = { ...PREFS_DEFAUT, ...(prefs || {}) };
  if (APERCUS[id] != null) p.apercu = id;
  else if (LANGUES.includes(id)) p.langue = id;
  else if (id === COMPOSEUR) p.composeur = !p.composeur;
  return p;
}

/* ───────────── côté DOM ───────────── */

export function initTexte(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const CLE_PREFS = "dz-photolab-texte", CLE_RECENTS = "dz-photolab-glyphes";
  const lireLS = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } };
  const ecrireLS = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* facultatif */ } };
  let prefs = { ...PREFS_DEFAUT, ...lireLS(CLE_PREFS, {}) };
  const opts = (PL.etat.texte = { ...DEFAUT_TEXTE });
  let polices = null;                                        // familles du moteur (type.fonts), une fois
  let info = null, infoCalque = null, infoRev = null;        // type.info du calque de texte actif
  let ed = null;                                             // édition : {calque|null, pl, avant, zone, boite}
  let g = null;                                              // geste de l'outil : {a}
  const fg = () => (PL.etat.couleurs && PL.etat.couleurs.fg) || "#000000";
  const scene = PL.$("#scene");

  async function listePolices() {
    if (polices) return polices;
    try { const r = await PL.post("/executer", { command: "type.fonts", params: {} }); polices = (r && r.families) || []; } catch (e) { polices = []; }
    return polices;
  }
  async function facesDe(famille) {
    try { const r = await PL.post("/executer", { command: "type.fonts", params: { family: famille } }); return stylesDe(r && r.faces); } catch (e) { return []; }
  }
  const calqueActifTexte = () => {
    const d = PL.etat.doc;
    if (!d) return null;
    const plats = []; const voir = (ls) => { for (const l of ls || []) { plats.push(l); voir(l.children); } }; voir(d.layers);
    const l = plats.find((x) => x.id === d.activeLayer);
    return l && l.kind === "Type" ? l : null;
  };
  async function relireInfo(force = false) {
    const l = ed && ed.calque ? { id: ed.calque } : calqueActifTexte();
    const d = PL.etat.doc;
    if (!l || !d) { info = null; infoCalque = null; return null; }
    if (!force && infoCalque === l.id && infoRev === d.revision && info) return info;
    try { info = await PL.post("/executer", { command: "type.info", params: { layer: l.id } }); infoCalque = l.id; infoRev = d.revision; } catch (e) { info = null; }
    return info;
  }

  /* éditeur posé sur la toile */
  function ouvrirEditeur(e) {
    fermerEditeurDom();
    const z = PL.vue.v.z, r = PL.$("#toile").getBoundingClientRect(), rs = scene.getBoundingClientRect();
    const zone = document.createElement("textarea");
    zone.className = "tx-editeur"; zone.spellcheck = false; zone.value = e.avant || ""; zone.setAttribute("data-dz-brut", "");
    zone.setAttribute("aria-label", T("photolab.texte.saisie"));
    const px = Math.max(8, e.size * z);
    Object.assign(zone.style, { fontFamily: `"${e.font}", sans-serif`, fontSize: px + "px", fontWeight: String(e.weight), fontStyle: e.italic ? "italic" : "normal",
      color: e.couleur, textAlign: ["center", "right"].includes(e.align) ? e.align : "left", lineHeight: "1.2" });
    let gx, gy, w, h;
    if (e.boite) { const a = PL.vue.versEcran(e.boite[0], e.boite[1]); gx = a.x; gy = a.y; w = e.boite[2] * z; h = e.boite[3] * z; }
    else if (e.bornes) { const a = PL.vue.versEcran(e.bornes[0], e.bornes[1]); gx = a.x; gy = a.y; w = Math.max(e.bornes[2] * z + px, 120); h = Math.max(e.bornes[3] * z, px * 1.3); }
    else { const a = PL.vue.versEcran(e.pl.x, e.pl.y); gx = a.x; gy = a.y - px; w = Math.max(160, px * 6); h = px * 1.3; }
    Object.assign(zone.style, { left: (r.left - rs.left + gx) + "px", top: (r.top - rs.top + gy) + "px", width: w + "px", height: h + "px" });
    zone.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      // t159 : Préférences › Texte › « Échap valide le texte » (décochée : Échap annule la saisie)
      const echapValide = !PL.prefs || PL.prefs.v("type", "useEscToCommit");
      if (ev.key === "Escape" && !echapValide) { ev.preventDefault(); annuler(); return; }
      if ((ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) || ev.key === "Escape") { ev.preventDefault(); valider(); }
    });
    zone.addEventListener("input", () => { if (!e.boite) { zone.style.width = Math.max(160, zone.scrollWidth + 8) + "px"; zone.style.height = "auto"; zone.style.height = zone.scrollHeight + "px"; } });
    scene.appendChild(zone);
    ed = { ...e, zone };
    setTimeout(() => { zone.focus(); if (e.calque) zone.select(); }, 0);
    if (PL.reconstruireOptions) PL.reconstruireOptions();
  }
  function fermerEditeurDom() { const z = scene && scene.querySelector(".tx-editeur"); if (z) z.remove(); }
  async function valider() {
    if (!ed) return;
    const e = ed, texte = e.zone.value;
    ed = null; fermerEditeurDom();
    if (PL.reconstruireOptions) PL.reconstruireOptions();
    if (e.calque) { const p = paramsEdition(e.calque, e.avant, texte); if (p) await PL.executer("type.edit", p); }
    else { const p = paramsCreation(e.pl, texte, opts, opts.couleur || fg()); if (p) await PL.executer("type.create", p); }
  }
  function annuler() { ed = null; fermerEditeurDom(); if (PL.reconstruireOptions) PL.reconstruireOptions(); }
  // Avant de styler une PLAGE pendant l'édition, le texte saisi part au moteur (les positions doivent correspondre).
  async function synchroniser() {
    if (!ed) return null;
    const texte = ed.zone.value;
    if (!ed.calque) {
      const p = paramsCreation(ed.pl, texte, opts, opts.couleur || fg());
      if (!p) return null;
      const r = await PL.executer("type.create", p);
      if (r && r.ok && r.r && r.r.layer != null) { ed.calque = r.r.layer; ed.avant = texte; }
    } else if (texte !== ed.avant) {
      const r = await PL.executer("type.edit", { layer: ed.calque, text: texte });
      if (r && r.ok) ed.avant = texte;
    }
    return ed.calque;
  }
  // Un réglage de Caractère / Paragraphe / barre d'options : nouveaux textes (opts) et calque visé (plage éditée sinon tout).
  async function appliquer(params) {
    Object.assign(opts, { ...(params.font ? { font: params.font } : {}), ...(params.weight ? { weight: params.weight, italic: !!params.italic } : {}),
      ...(params.size ? { size: params.size } : {}), ...(params.align ? { align: params.align === "justify" ? "justifyLeft" : params.align } : {}),
      ...(params.color ? { couleur: params.color } : {}) });
    if (ed) {
      const z = ed.zone, a = z.selectionStart, b = z.selectionEnd;
      if (params.font) z.style.fontFamily = `"${params.font}", sans-serif`;
      if (params.size) z.style.fontSize = Math.max(8, params.size * PL.vue.v.z) + "px";
      if (params.color) z.style.color = params.color;
      const c = await synchroniser();
      if (c == null) return;
      await PL.executer("type.setStyle", { layer: c, ...(a < b ? { range: [a, b] } : {}), ...params });
      z.focus(); z.setSelectionRange(a, b);
      return;
    }
    const l = calqueActifTexte();
    if (l) await PL.executer("type.setStyle", { layer: l.id, ...params });
  }

  PL.gestes.type = {
    appui(p) {
      if (ed) { valider(); return; }                               // amont : un clic ailleurs valide, sans nouveau texte
      const l = calqueTexteSous(PL.etat.doc, [p.x, p.y]);
      if (l) { editerCalque(l); return; }
      g = { a: [p.x, p.y] };
    },
    bouger() {},
    relacher(p) {
      if (!g) return;
      const pl = placement(g.a, [p.x, p.y], PL.vue.v.z); g = null;
      ouvrirEditeur({ calque: null, pl, avant: "", boite: pl.box || null, font: opts.font, weight: opts.weight, italic: opts.italic,
        size: opts.size, couleur: opts.couleur || fg(), align: opts.align });
    },
    survol(p) { PL.$("#toile").style.cursor = calqueTexteSous(PL.etat.doc, [p.x, p.y]) ? "text" : "crosshair"; },
    quitter() { if (ed) valider(); g = null; },
    annuler() { g = null; },
  };
  async function editerCalque(l) {
    if (PL.etat.doc.activeLayer !== l.id) await PL.executer("layer.select", { layer: l.id, mode: "replace" });
    const inf = await (async () => { try { return await PL.post("/executer", { command: "type.info", params: { layer: l.id } }); } catch (e) { return null; } })();
    const v = lecture(inf, 0);
    if (!v) return;
    ouvrirEditeur({ calque: l.id, pl: null, avant: v.texte, boite: null, bornes: l.bounds, font: v.font, weight: v.weight, italic: v.italic,
      size: v.size, couleur: v.color, align: v.align });
  }
  PL.texte = { valider, annuler, editeur: () => (ed ? { calque: ed.calque, texte: ed.zone.value } : null), appliquer, relireInfo, prefs: () => prefs };

  /* barre d'options de l'outil Texte */
  PL.barresOutils = PL.barresOutils || {};
  PL.barresOutils.type = (barre) => {
    const champ = (lib, el) => { const w = document.createElement("label"); w.className = "opt fo-champ"; const s = document.createElement("span"); s.textContent = T(lib); w.append(s, el); barre.appendChild(w); return el; };
    const ori = document.createElement("button"); ori.type = "button"; ori.className = "tr-bascule" + (opts.orientation === "vertical" ? " actif" : ""); ori.innerHTML = PL.icone("dz-edit-orientation-texte");
    ori.title = T("photolab.texte.orientation"); ori.setAttribute("aria-label", ori.title); ori.setAttribute("aria-pressed", String(opts.orientation === "vertical"));
    ori.addEventListener("click", () => {
      opts.orientation = opts.orientation === "vertical" ? "horizontal" : "vertical"; ori.classList.toggle("actif", opts.orientation === "vertical"); ori.setAttribute("aria-pressed", String(opts.orientation === "vertical"));
      const l = calqueActifTexte(); if (l) PL.executer("type.orientation." + (opts.orientation === "vertical" ? "vertical" : "horizontal"), { layer: l.id });
    });
    barre.appendChild(ori);
    barre.appendChild(selecteurPolice(opts.font, (f) => appliquer({ font: f })));
    const st = document.createElement("select"); st.className = "tx-style"; champ("photolab.texte.style", st);
    const remplirStyles = async (f) => {
      const ss = await facesDe(f); st.textContent = "";
      for (const s of ss.length ? ss : [{ weight: 400, italic: false }]) { const o = document.createElement("option"); o.value = s.weight + (s.italic ? "i" : ""); o.textContent = nomStyle(s, T); st.appendChild(o); }
      st.value = opts.weight + (opts.italic ? "i" : "");
    };
    remplirStyles(opts.font);
    st.addEventListener("change", () => { const w = parseInt(st.value, 10), it = st.value.endsWith("i"); appliquer({ weight: w, italic: it }); });
    const taille = Object.assign(document.createElement("input"), { type: "number", min: 1, max: 1296, step: 1, value: opts.size, className: "tx-taille" });
    taille.addEventListener("change", () => { const v = Math.min(1296, Math.max(1, Number(taille.value) || 12)); taille.value = v; appliquer({ size: v }); });
    champ("photolab.texte.taille", taille).insertAdjacentHTML("afterend", '<span class="opt-unite">pt</span>');
    const aa = document.createElement("select");
    for (const v of ANTICRENELAGES) { const o = document.createElement("option"); o.value = v; o.textContent = T(LIB_AA[v]); aa.appendChild(o); }
    aa.value = opts.antialias;
    aa.addEventListener("change", () => { opts.antialias = aa.value; const l = calqueActifTexte(); if (l) PL.executer("type.antiAlias." + aa.value, { layer: l.id }); });
    champ("photolab.texte.anticrenelage", aa);
    for (const v of ["left", "center", "right"]) {
      const b = document.createElement("button"); b.type = "button"; b.className = "tr-bascule tx-align" + (opts.align === v ? " actif" : ""); b.dataset.align = v;
      b.innerHTML = PL.icone(ICONES_ALIGN[v]); b.title = T(LIB_ALIGNS[v]); b.setAttribute("aria-label", b.title);
      b.addEventListener("click", () => { appliquer(paramsStyle("align", v)); barre.querySelectorAll(".tx-align").forEach((x) => x.classList.toggle("actif", x === b)); });
      barre.appendChild(b);
    }
    const coul = Object.assign(document.createElement("input"), { type: "color", value: opts.couleur || fg() });
    coul.addEventListener("change", () => appliquer({ color: coul.value }));
    champ("photolab.texte.couleur", coul);
    if (ed) {
      const ok = document.createElement("button"); ok.type = "button"; ok.className = "tr-valider"; ok.innerHTML = PL.icone("dz-action-valider"); ok.title = T("photolab.texte.valider"); ok.setAttribute("aria-label", ok.title);
      ok.addEventListener("click", valider);
      const ko = document.createElement("button"); ko.type = "button"; ko.className = "tr-annuler"; ko.innerHTML = PL.icone("dz-action-abandonner"); ko.title = T("photolab.texte.annuler"); ko.setAttribute("aria-label", ko.title);
      ko.addEventListener("click", annuler);
      barre.append(ok, ko);
    }
  };
  // Liste des polices : chaque nom dans sa police, à la taille de l'aperçu (Texte › Taille de l'aperçu des polices).
  function selecteurPolice(courante, choisir) {
    const w = document.createElement("div"); w.className = "tx-police";
    const b = document.createElement("button"); b.type = "button"; b.className = "tx-police-btn"; b.textContent = courante;
    b.style.fontFamily = `"${courante}", sans-serif`; b.title = T("photolab.texte.police"); b.setAttribute("data-dz-brut", "");
    const pop = document.createElement("div"); pop.className = "tx-police-liste"; pop.hidden = true;
    const rech = Object.assign(document.createElement("input"), { type: "search", placeholder: T("photolab.texte.chercher_police"), className: "pr-recherche" });
    const ul = document.createElement("div"); ul.className = "tx-police-items";
    pop.append(rech, ul);
    const remplir = async () => {
      const fs = await listePolices(), q = rech.value.trim().toLowerCase(), px = APERCUS[prefs.apercu] || 14;
      ul.textContent = "";
      for (const f of fs.filter((x) => !q || x.toLowerCase().includes(q)).slice(0, 300)) {
        const it = document.createElement("button"); it.type = "button"; it.className = "tx-police-item"; it.textContent = f; it.setAttribute("data-dz-brut", "");
        it.style.fontFamily = `"${f}", sans-serif`; it.style.fontSize = px + "px";
        it.addEventListener("click", () => { pop.hidden = true; b.textContent = f; b.style.fontFamily = `"${f}", sans-serif`; choisir(f); });
        ul.appendChild(it);
      }
    };
    b.addEventListener("click", () => { pop.hidden = !pop.hidden; if (!pop.hidden) { remplir(); rech.focus(); } });
    rech.addEventListener("input", remplir);
    rech.addEventListener("keydown", (ev) => { ev.stopPropagation(); if (ev.key === "Escape") pop.hidden = true; });
    document.addEventListener("pointerdown", (ev) => { if (!w.contains(ev.target)) pop.hidden = true; });
    w.append(b, pop);
    return w;
  }

  /* panneaux Caractère et Paragraphe */
  const cCar = PL.$("#corpsCaractere"), cPar = PL.$("#corpsParagraphe");
  const champsCar = {}, champsPar = {};
  function construireCaractere() {
    if (!cCar) return;
    cCar.textContent = "";
    const ligne = () => { const l = document.createElement("div"); l.className = "tx-ligne"; cCar.appendChild(l); return l; };
    const num = (parent, cle, lib, min, max, pas, unite, champ = cle) => {
      const w = document.createElement("label"); w.className = "tx-champ"; w.title = T(lib);
      const s = document.createElement("span"); s.className = "tx-lib"; s.textContent = T(lib);
      const n = Object.assign(document.createElement("input"), { type: "number", min, max, step: pas });
      n.addEventListener("change", () => { const v = Math.min(max, Math.max(min, Number(n.value))); if (isFinite(v)) appliquer(paramsStyle(champ, v)); });
      w.append(s, n); if (unite) { const u = document.createElement("span"); u.className = "opt-unite"; u.textContent = unite; w.appendChild(u); }
      parent.appendChild(w); champsCar[cle] = n; return n;
    };
    const l1 = ligne(); l1.appendChild(selecteurPolice(opts.font, (f) => appliquer({ font: f })));
    const st = document.createElement("select"); st.className = "tx-style"; l1.appendChild(st); champsCar.style = st;
    st.addEventListener("change", () => { const w = parseInt(st.value, 10); appliquer({ weight: w, italic: st.value.endsWith("i") }); });
    const l2 = ligne(); num(l2, "size", "photolab.texte.taille", 0.1, 1296, 0.1, "pt");
    const lead = Object.assign(document.createElement("input"), { type: "text", className: "tx-interligne" });
    lead.addEventListener("change", () => { const v = lead.value.trim().toLowerCase(); appliquer(paramsStyle("leading", v === "" || v === "auto" ? "auto" : Math.min(5000, Math.max(0.1, Number(v) || 0.1)))); });
    const wl = document.createElement("label"); wl.className = "tx-champ"; const sl = document.createElement("span"); sl.className = "tx-lib"; sl.textContent = T("photolab.texte.interlignage");
    wl.append(sl, lead); l2.appendChild(wl); champsCar.leading = lead;
    const l3 = ligne();
    const kern = document.createElement("select"); kern.className = "tx-crenage";
    for (const v of ["metrics", "optical", "0", "-100", "-50", "-25", "-10", "-5", "5", "10", "25", "50", "100", "200"]) {
      const o = document.createElement("option"); o.value = v; o.textContent = v === "metrics" ? T("photolab.texte.crenage_metrique") : v === "optical" ? T("photolab.texte.crenage_optique") : v; kern.appendChild(o);
    }
    kern.addEventListener("change", () => appliquer(paramsStyle("kerning", kern.value)));
    const wk = document.createElement("label"); wk.className = "tx-champ"; const sk = document.createElement("span"); sk.className = "tx-lib"; sk.textContent = T("photolab.texte.crenage");
    wk.append(sk, kern); l3.appendChild(wk); champsCar.kerning = kern;
    num(l3, "tracking", "photolab.texte.approche", -1000, 10000, 1);
    const l4 = ligne(); num(l4, "verticalScale", "photolab.texte.echelle_v", 0, 1000, 1, "%"); num(l4, "horizontalScale", "photolab.texte.echelle_h", 0, 1000, 1, "%");
    const l5 = ligne(); num(l5, "baselineShift", "photolab.texte.decalage", -1296, 1296, 0.1, "pt");
    const coul = Object.assign(document.createElement("input"), { type: "color" }); coul.addEventListener("change", () => appliquer({ color: coul.value }));
    const wc = document.createElement("label"); wc.className = "tx-champ"; const sc = document.createElement("span"); sc.className = "tx-lib"; sc.textContent = T("photolab.texte.couleur");
    wc.append(sc, coul); l5.appendChild(wc); champsCar.color = coul;
    const l6 = ligne(); l6.classList.add("tx-bascules");
    for (const [cle, ico, lib, val] of [["fauxBold", "dz-edit-texte-gras", "photolab.texte.faux_gras", true], ["fauxItalic", "dz-edit-texte-italique", "photolab.texte.faux_italique", true],
      ["caps:all", "dz-edit-texte-capitales", "photolab.texte.capitales", "all"], ["caps:small", "dz-edit-texte-petites-capitales", "photolab.texte.petites_capitales", "small"],
      ["underline", "dz-edit-texte-souligne", "photolab.texte.souligne", true], ["strikethrough", "dz-edit-texte-barre", "photolab.texte.barre", true]]) {
      const b = document.createElement("button"); b.type = "button"; b.className = "tr-bascule tx-bascule tx-" + cle.replace(":", "-"); b.innerHTML = PL.icone(ico); b.title = T(lib); b.setAttribute("aria-label", b.title);
      b.addEventListener("click", () => {
        const actif = b.classList.contains("actif");
        if (cle.startsWith("caps:")) appliquer(paramsStyle("caps", actif ? "normal" : val));
        else appliquer({ [cle]: !actif });
      });
      l6.appendChild(b); champsCar[cle] = b;
    }
  }
  function construireParagraphe() {
    if (!cPar) return;
    cPar.textContent = "";
    const l1 = document.createElement("div"); l1.className = "tx-ligne tx-bascules"; cPar.appendChild(l1);
    for (const v of ALIGNS) {
      const b = document.createElement("button"); b.type = "button"; b.className = "tr-bascule tx-palign"; b.dataset.align = v; b.title = T(LIB_ALIGNS[v]);
      b.innerHTML = PL.icone(ICONES_ALIGN[v]); b.setAttribute("aria-label", b.title);
      b.addEventListener("click", () => appliquer(paramsStyle("align", v)));
      l1.appendChild(b); champsPar["align:" + v] = b;
    }
    const num = (cle, lib, min, max) => {
      const w = document.createElement("label"); w.className = "tx-champ"; const s = document.createElement("span"); s.className = "tx-lib"; s.textContent = T(lib);
      const n = Object.assign(document.createElement("input"), { type: "number", min, max, step: 0.1 });
      n.addEventListener("change", () => { const v = Math.min(max, Math.max(min, Number(n.value) || 0)); appliquer({ [cle]: v }); });
      const u = document.createElement("span"); u.className = "opt-unite"; u.textContent = "pt";
      w.append(s, n, u); cPar.appendChild(w); champsPar[cle] = n;
    };
    num("startIndent", "photolab.texte.retrait_gauche", -1296, 1296); num("endIndent", "photolab.texte.retrait_droit", -1296, 1296);
    num("firstLineIndent", "photolab.texte.retrait_premiere", -1296, 1296);
    num("spaceBefore", "photolab.texte.espace_avant", 0, 1296); num("spaceAfter", "photolab.texte.espace_apres", 0, 1296);
    const wh = document.createElement("label"); wh.className = "tx-champ tx-case";
    const hy = Object.assign(document.createElement("input"), { type: "checkbox" }); hy.addEventListener("change", () => appliquer({ hyphenate: hy.checked }));
    wh.append(hy, document.createTextNode(" " + T("photolab.texte.cesure"))); cPar.appendChild(wh); champsPar.hyphenate = hy;
    // Options de langue : Moyen-Orient -> direction ; Asie orientale -> orientation verticale (préférence d'écran).
    if (prefs.langue === "type.languageOptions.middleEasternFeatures") {
      const wd = document.createElement("label"); wd.className = "tx-champ"; const sd = document.createElement("span"); sd.className = "tx-lib"; sd.textContent = T("photolab.texte.direction");
      const dir = document.createElement("select");
      for (const [v, k] of [["auto", "photolab.texte.dir_auto"], ["ltr", "photolab.texte.dir_ltr"], ["rtl", "photolab.texte.dir_rtl"]]) { const o = document.createElement("option"); o.value = v; o.textContent = T(k); dir.appendChild(o); }
      dir.addEventListener("change", () => appliquer({ direction: dir.value }));
      wd.append(sd, dir); cPar.appendChild(wd); champsPar.direction = dir;
    }
    if (prefs.langue === "type.languageOptions.eastAsianFeatures") {
      const b = document.createElement("button"); b.type = "button"; b.className = "tr-bascule tx-vertical"; b.innerHTML = PL.icone("dz-edit-orientation-texte"); b.append(" " + T("photolab.texte.vertical"));
      b.addEventListener("click", () => { const l = calqueActifTexte(); if (l) PL.executer("type.orientation.vertical", { layer: l.id }); });
      cPar.appendChild(b); champsPar.vertical = b;
    }
  }
  async function majPanneaux() {
    const visibleC = cCar && cCar.offsetParent, visibleP = cPar && cPar.offsetParent;
    if (!visibleC && !visibleP) return;
    const inf = await relireInfo();
    const i = ed && ed.zone ? ed.zone.selectionStart : 0;
    const v = lecture(inf, i) || { ...DEFAUT_TEXTE, leading: "auto", kerning: "metrics", tracking: 0, verticalScale: 100, horizontalScale: 100, baselineShift: 0, color: fg(),
      fauxBold: false, fauxItalic: false, caps: "normal", underline: false, strikethrough: false, startIndent: 0, endIndent: 0, firstLineIndent: 0, spaceBefore: 0, spaceAfter: 0, hyphenate: false, direction: "auto" };
    if (visibleC) {
      const b = cCar.querySelector(".tx-police-btn"); if (b) { b.textContent = v.font; b.style.fontFamily = `"${v.font}", sans-serif`; }
      const ss = await facesDe(v.font); champsCar.style.textContent = "";
      for (const s of ss.length ? ss : [{ weight: 400, italic: false }]) { const o = document.createElement("option"); o.value = s.weight + (s.italic ? "i" : ""); o.textContent = nomStyle(s, T); champsCar.style.appendChild(o); }
      champsCar.style.value = v.weight + (v.italic ? "i" : "");
      for (const k of ["size", "tracking", "verticalScale", "horizontalScale", "baselineShift"]) if (document.activeElement !== champsCar[k]) champsCar[k].value = String(Math.round(v[k] * 100) / 100);
      if (document.activeElement !== champsCar.leading) champsCar.leading.value = v.leading === "auto" ? T("photolab.texte.auto") : String(v.leading);
      champsCar.kerning.value = typeof v.kerning === "string" ? v.kerning : String(v.kerning);
      champsCar.color.value = v.color;
      champsCar.fauxBold.classList.toggle("actif", v.fauxBold); champsCar.fauxItalic.classList.toggle("actif", v.fauxItalic);
      champsCar["caps:all"].classList.toggle("actif", v.caps === "all"); champsCar["caps:small"].classList.toggle("actif", v.caps === "small");
      champsCar.underline.classList.toggle("actif", v.underline); champsCar.strikethrough.classList.toggle("actif", v.strikethrough);
    }
    if (visibleP) {
      for (const a of ALIGNS) champsPar["align:" + a].classList.toggle("actif", v.align === a);
      for (const k of ["startIndent", "endIndent", "firstLineIndent", "spaceBefore", "spaceAfter"]) if (document.activeElement !== champsPar[k]) champsPar[k].value = String(v[k]);
      champsPar.hyphenate.checked = v.hyphenate;
      if (champsPar.direction) champsPar.direction.value = v.direction;
    }
  }
  construireCaractere(); construireParagraphe();

  /* Glyphes */
  const cGly = PL.$("#corpsGlyphes");
  let recentsGly = lireLS(CLE_RECENTS, []);
  async function insererGlyphe(ch) {
    recentsGly = recents(recentsGly, ch); ecrireLS(CLE_RECENTS, recentsGly);
    if (ed) {                                  // pendant l'édition : à la place de la sélection de l'éditeur
      const z = ed.zone, a = z.selectionStart, b = z.selectionEnd;
      z.setRangeText(ch, a, b, "end"); z.focus(); dessinerGlyphes(); return;
    }
    const l = calqueActifTexte();
    if (l) await PL.executer("type.insertText", { layer: l.id, text: ch });
    else PL.signaler(T("photolab.glyphes.aucun_calque"), true);
    dessinerGlyphes();
  }
  let catGly = CATEGORIES[0].id;
  function dessinerGlyphes() {
    if (!cGly) return;
    cGly.textContent = "";
    const tete = document.createElement("label"); tete.className = "tx-champ";
    const s = document.createElement("span"); s.className = "tx-lib"; s.textContent = T("photolab.glyphes.montrer");
    const sel = document.createElement("select");
    for (const c of CATEGORIES) { const o = document.createElement("option"); o.value = c.id; o.textContent = T(c.cle); sel.appendChild(o); }
    sel.value = catGly; sel.addEventListener("change", () => { catGly = sel.value; dessinerGlyphes(); });
    tete.append(s, sel); cGly.appendChild(tete);
    const police = (ed && ed.font) || (info && lecture(info) && lecture(info).font) || opts.font;
    const cellule = (ch) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "gl-cellule"; b.textContent = ch; b.title = pointDeCode(ch);
      b.style.fontFamily = `"${police}", sans-serif`; b.setAttribute("data-dz-brut", "");
      b.addEventListener("dblclick", () => insererGlyphe(ch));
      return b;
    };
    if (recentsGly.length) {
      const r = document.createElement("div"); r.className = "gl-recents";
      const lr = document.createElement("span"); lr.className = "tx-lib"; lr.textContent = T("photolab.glyphes.recents"); r.appendChild(lr);
      for (const ch of recentsGly) { const b = cellule(ch); b.addEventListener("click", () => insererGlyphe(ch)); r.appendChild(b); }
      cGly.appendChild(r);
    }
    const grille = document.createElement("div"); grille.className = "gl-grille";
    for (const ch of caracteres(catGly)) grille.appendChild(cellule(ch));
    cGly.appendChild(grille);
    const aide = document.createElement("p"); aide.className = "cmp-vide"; aide.textContent = T("photolab.glyphes.aide"); cGly.appendChild(aide);
  }
  dessinerGlyphes();

  /* Styles de caractère / de paragraphe */
  const STYLES = { stylesCar: { corps: "#corpsStylesCar", fam: "characterStyle", aucun: "photolab.styles_texte.aucun_car", cle: "character" },
    stylesPar: { corps: "#corpsStylesPar", fam: "paragraphStyle", aucun: "photolab.styles_texte.base_par", cle: "paragraph" } };
  const etatsStyles = {};
  for (const [id, S] of Object.entries(STYLES)) {
    const corps = PL.$(S.corps);
    if (!corps) continue;
    const zone = document.createElement("div"); zone.className = "cmp-liste"; const pied = document.createElement("div"); pied.className = "pr-pied";
    corps.append(zone, pied);
    const st = (etatsStyles[id] = { liste: null, sel: null });
    const cmd = (suffixe) => "type." + S.fam + "." + suffixe;
    const cible = () => { if (ed && ed.calque) { const z = ed.zone; return { layer: ed.calque, ...(z.selectionStart < z.selectionEnd ? { range: [z.selectionStart, z.selectionEnd] } : {}) }; } return {}; };
    const exec = async (c, p) => { if (!PL.etat.doc) return; await synchroniser(); await PL.executer(c, p); relire(); };
    const bouton = (icone, cle, fn) => { const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone; b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b; };
    const bEffacer = bouton("dz-action-reinitialiser", "photolab.styles_texte.effacer", () => exec(cmd("clearOverride"), cible()));
    const bRedef = bouton("dz-action-redefinir", "photolab.styles_texte.redefinir", () => exec(cmd("redefine"), { ...(st.sel ? { id: st.sel } : {}), ...cible() }));
    bouton("dz-action-ajouter", "photolab.styles_texte.nouveau", () => exec(cmd("new"), { fromSelection: true, ...cible() }));
    const bDup = bouton("dz-action-dupliquer", "photolab.styles_texte.dupliquer", () => { if (st.sel) exec(cmd("duplicate"), { id: st.sel }); });
    const bSup = bouton("dz-action-supprimer", "photolab.styles_texte.supprimer", () => { if (st.sel) { exec(cmd("delete"), { id: st.sel }); st.sel = null; } });
    if (PL.hydraterIcones) PL.hydraterIcones(pied);
    async function relire() {
      if (!PL.etat.doc) { st.liste = null; dessiner(); return; }
      try { st.liste = await PL.post("/executer", { command: cmd("list"), params: cible() }); } catch (e) { st.liste = null; }
      dessiner();
    }
    function dessiner() {
      zone.textContent = "";
      const l = st.liste;
      const cur = l && l.current ? l.current[S.cle] : null, over = l && l.current ? l.current[S.cle + "Override"] : false;
      for (const s of (l && l.styles) || []) {
        const row = document.createElement("div"); row.className = "cmp-ligne" + (st.sel === s.id ? " choisie" : "") + (cur === s.id ? " courant" : "");
        const nom = document.createElement("span"); nom.className = "cmp-nom";
        nom.textContent = (s.id === 0 ? T(S.aucun) : s.name) + (cur === s.id && over ? " +" : "");
        if (s.id !== 0) nom.setAttribute("data-dz-brut", ""); else nom.classList.add("italique");
        row.appendChild(nom);
        row.addEventListener("click", (ev) => { st.sel = s.id; exec(cmd("apply"), { id: s.id, ...(ev.altKey ? { clearOverrides: true } : {}), ...cible() }); });
        row.addEventListener("dblclick", async () => { if (!s.id) return; const n = await demanderNom(PL, T("commun.action.renommer"), s.name); if (n) exec(cmd("rename"), { id: s.id, name: n }); });
        zone.appendChild(row);
      }
      bEffacer.disabled = !over; bRedef.disabled = bDup.disabled = bSup.disabled = !st.sel;
    }
    st.relire = relire;
  }

  /* menu Texte, panneaux, rafraîchissements */
  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => decorerTexte(menus, prefs));
  PL.actions = PL.actions || {};
  for (const id of [...Object.keys(APERCUS), ...LANGUES, COMPOSEUR]) {
    PL.actions[id] = () => {
      prefs = basculerPref(prefs, id); ecrireLS(CLE_PREFS, prefs); construireParagraphe(); majPanneaux(); if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
      // t159 : la même valeur dans les préférences (Préférences › Texte › taille de l'aperçu ; langue, composeur)
      if (PL.prefs) {
        const e = JSON.parse(JSON.stringify(PL.prefs.etat));
        const cle = Object.keys(APERCU_PREF).find((k) => APERCU_PREF[k] === prefs.apercu);
        if (cle) e.prefs.type.fontPreview = cle;
        e.texte = { langue: prefs.langue, composeur: !!prefs.composeur };
        PL.prefs.enregistrer(e).catch(() => {});
      }
    };
  }
  // t159 : préférences chargées ou modifiées (dialogue Préférences, autre machine) -> menu Texte et panneaux
  if (PL.prefs) PL.prefs.surChange.push((e) => {
    const n = { ...prefs, apercu: APERCU_PREF[e.prefs.type.fontPreview] || prefs.apercu, langue: e.texte.langue, composeur: e.texte.composeur };
    if (JSON.stringify(n) === JSON.stringify(prefs)) return;
    prefs = n; ecrireLS(CLE_PREFS, prefs); construireParagraphe(); majPanneaux();
  });
  PL.surOngletTexte = (nom) => {
    if (nom === "caractere" || nom === "paragraphe") majPanneaux();
    else if (nom === "glyphes") dessinerGlyphes();
    else if (etatsStyles[nom]) etatsStyles[nom].relire();
  };
  PL.surDoc.push(() => {
    majPanneaux();
    for (const s of Object.values(etatsStyles)) if (s.relire && PL.$(s === etatsStyles.stylesCar ? "#corpsStylesCar" : "#corpsStylesPar").offsetParent) s.relire();
  });
  if (PL.surOutil) PL.surOutil.push(() => { if (ed && PL.etat.outil !== "type") valider(); });
}
