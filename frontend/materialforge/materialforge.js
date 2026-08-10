/* ═══════════════════════════════════════════════════════════════════════════
   Material Forge — lab vanilla, même origine que l’app (aucune dépendance
   externe : la visionneuse 3D vient de /assets/model-viewer.min.js).

   Contrat : SPEC.md §3 (routes /api/materials…). Le lab reste utilisable même
   si une route manque encore : bandeau d’erreur lisible + états vides soignés
   (le catch-all SPA renvoie du HTML en 200 sur une route absente — c’est
   détecté explicitement, voir api.get()).

   Ce que la barre (Sorceress Material Forge) n’a pas et qu’on affiche ici :
     · 8 maps (height + ORM en plus des 6 habituelles),
     · le score de raccord MESURÉ avant → après (elle promet, on prouve),
     · le coût ET la durée estimés AVANT lancement (repris de Meshy),
     · la re-dérivation locale gratuite (elle facture chaque ajustement).

   Poignée QA : window.__mf (état + actions), comme window.__tl du Tile Lab.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

/* ───────────────────────── utilitaires ───────────────────────── */
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

function num(v, d) { const n = Number(v); return isFinite(n) ? n : d; }
function fmt(v, dec) { return num(v, 0).toFixed(dec == null ? 2 : dec); }

let toastTimer = null;
function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.toggle("err", !!err);
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 4600);
}

/* Une route absente tombe sur le catch-all SPA : HTTP 200 + du HTML.
   Sans ce garde, le lab planterait sur un JSON.parse illisible. */
class ApiMissing extends Error {
  constructor(path) {
    super("route absente sur ce backend : /api" + path);
    this.missing = true;
    this.path = path;
  }
}

const api = {
  async raw(method, path, body, headers) {
    const opt = { method, headers: Object.assign({}, headers || {}) };
    if (body !== undefined && body !== null) {
      if (body instanceof Blob || body instanceof FormData) opt.body = body;
      else { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    }
    return fetch("/api" + path, opt);
  },
  async json(method, path, body, headers) {
    let r;
    try { r = await this.raw(method, path, body, headers); }
    catch (e) { throw new Error("backend injoignable (" + e.message + ")"); }
    const ct = (r.headers.get("content-type") || "").toLowerCase();
    if (r.status === 404 || (r.ok && ct.indexOf("json") < 0)) throw new ApiMissing(path);
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) throw new Error((d && (d.detail || d.error)) || (r.status + " " + r.statusText));
    return d || {};
  },
  get(p) { return this.json("GET", p); },
  post(p, b) { return this.json("POST", p, b || {}); },
  patch(p, b) { return this.json("PATCH", p, b || {}); },
  del(p) { return this.json("DELETE", p); },
};

/* ───────────────────────── référentiels ───────────────────────── */

const MESHES = [
  { id: "sphere", label: "Sphère" }, { id: "cube", label: "Cube" },
  { id: "torus", label: "Tore" }, { id: "cylinder", label: "Cylindre" },
  { id: "plane", label: "Plan" }, { id: "tiled", label: "Pavage 3×3" },
];

/* repli local si GET /materials/envs manque encore : mêmes 7 noms que la spec.
   [ciel haut, horizon, sol, position du soleil u/v, éclat] */
const ENV_FALLBACK = [
  { name: "unlit", label: "Sans éclairage", sky: "#8a8a90", hor: "#8a8a90", grd: "#8a8a90", sun: null },
  { name: "daylight", label: "Plein jour", sky: "#2b5f9e", hor: "#bcd6ef", grd: "#6b6f74", sun: [0.30, 0.24, 1.0] },
  { name: "studio", label: "Studio", sky: "#2a2a2f", hor: "#e8e6e2", grd: "#1a1a1d", sun: [0.68, 0.30, 0.9] },
  { name: "sunset", label: "Coucher de soleil", sky: "#1d2450", hor: "#f0913f", grd: "#2a1c18", sun: [0.52, 0.47, 1.2] },
  { name: "overcast", label: "Ciel couvert", sky: "#9aa3ad", hor: "#cfd6dd", grd: "#5c6067", sun: null },
  { name: "night", label: "Nuit", sky: "#05060d", hor: "#141c33", grd: "#08090e", sun: [0.20, 0.18, 0.55] },
  { name: "dramatic", label: "Dramatique", sky: "#07070a", hor: "#3a2c1c", grd: "#050507", sun: [0.74, 0.22, 1.5] },
];

/* Mot court porte par une vignette de map UNIFORME. La note complete de l'API
   (« metallicite nulle - cette matiere est dielectrique ») ne tient pas sur une
   vignette de 90 px : elle s'y coupait en plein milieu, et une phrase tronquee
   vaut moins qu'un mot juste. Le mot est sur l'image, la phrase dans l'infobulle. */
/* Étiquette courte d'une map CONSTANTE. Elle nomme le FAIT PHYSIQUE, pas le
   manque : une map de métal uniforme ne « manque » pas, elle dit que la
   matière est entièrement diélectrique — ou entièrement métallique.
   L'étiquette « diélectrique » était écrite en dur : « or martelé », dont la
   métallicité vaut 1.00 partout, s'affichait donc « diélectrique » sur un
   métal plein. La valeur mesurée décide maintenant. */
const FLAT_SHORT = {
  metallic: "diélectrique", emissive: "éteinte", roughness: "uniforme",
  ao: "sans cavité", height: "plate", normal: "plane", basecolor: "unie",
  orm: "uniforme",
};
function flatShort(k, st) {
  if (k === "metallic" && st && num(st.mean, 0) > 127) return "métal plein";
  if (k === "roughness" && st) {
    const v = num(st.mean, 0);
    if (v > 235) return "mate partout";
    if (v < 20) return "miroir partout";
  }
  return FLAT_SHORT[k] || "uniforme";
}

const MAPS = [
  { k: "basecolor", label: "Base Color" }, { k: "normal", label: "Normal" },
  { k: "roughness", label: "Roughness" }, { k: "metallic", label: "Metallic" },
  { k: "ao", label: "AO" }, { k: "height", label: "Height" },
  { k: "emissive", label: "Emissive" }, { k: "orm", label: "ORM" },
];

/* crédits et secondes indicatives par modèle (l’estimation est annoncée comme
   telle : « ≈ »). Le tarif réel du provider prime, on n’invente pas de facture. */
const MODEL_COST = {
  "flux": 4, "nano-banana": 9, "gpt-image-2": 12,
  "gpt-image-1": 8, "gpt-image-1-mini": 3,
};
const MODEL_SEC = {
  "flux": 6, "nano-banana": 15, "gpt-image-2": 24,
  "gpt-image-1": 17, "gpt-image-1-mini": 9,
};
const DERIVE_SEC = { 1024: 3, 2048: 8, 4096: 24 };

const DEFAULT_PROPS = {
  color: "#ffffff", metallic: 0.0, roughness: 1.0, opacity: 1.0,
  emissive: "#000000", emissive_strength: 0.0,
  clearcoat: 0.0, clearcoat_roughness: 0.0,
  sheen: 0.0, sheen_color: "#ffffff",
  transmission: 0.0, ior: 1.5, thickness: 0.0,
  normal_scale: 1.0, ao_strength: 1.0, displacement: 0.0,
  tiling: 1.0, rotation: 0.0,
};
const DEFAULT_DERIVE = {
  normal_strength: 0.8, normal_invert_y: false,
  roughness_bias: 0.5, roughness_contrast: 0.5, roughness_invert: false,
  ao_strength: 1.0, ao_radius: 4.0,
  metallic_mode: "auto", metallic_threshold: 0.5,
  emissive_threshold: 0.85, height_detail: 0.5,
};

/* Les groupes de l’inspecteur. `live` = applicable instantanément à la
   visionneuse (API scene-graph de model-viewer) ; sinon on recharge le GLB
   après le PATCH. `h` = l’aide « ? » de la propriété. */
const GROUPS = [
  { id: "base", label: "Base", open: true, rows: [
    { k: "color", t: "color", l: "Couleur", live: 1,
      h: "Teinte multipliée par la map Base Color. Blanc = la texture telle qu’elle a été générée." },
    { k: "metallic", t: "range", min: 0, max: 1, step: 0.01, l: "Métallique", live: 1,
      h: "0 = diélectrique (bois, plastique, pierre), 1 = métal pur. Les demi-valeurs n’existent pas dans la nature : réserve-les aux zones mixtes (peinture écaillée sur acier)." },
    { k: "roughness", t: "range", min: 0, max: 1, step: 0.01, l: "Rugosité", live: 1,
      h: "0 = miroir, 1 = parfaitement mat. La rugosité étale l’éclat spéculaire au lieu de l’éteindre." },
    { k: "opacity", t: "range", min: 0, max: 1, step: 0.01, l: "Opacité", live: 1,
      h: "Sous 1, la matière passe en mélange alpha. Pour du verre physique (réfraction, épaisseur), utilise plutôt la Transmission." },
  ] },
  { id: "surface", label: "Détail de surface", rows: [
    { k: "normal_scale", t: "range", min: 0, max: 3, step: 0.05, l: "Échelle du relief",
      h: "Amplifie la map Normal. Au-delà de 2, le relief devient caricatural et scintille en mouvement." },
    { k: "ao_strength", t: "range", min: 0, max: 2, step: 0.05, l: "Occlusion ambiante",
      h: "Dose l’assombrissement des creux calculé par la map AO. 1 = valeur physique." },
    { k: "displacement", t: "range", min: 0, max: 1, step: 0.01, l: "Déplacement",
      h: "Déforme réellement le maillage avec la map Height (silhouette comprise), contrairement à la normale qui ne fait qu’imiter le relief. La barre n’a ni height ni déplacement." },
    { k: "tiling", t: "range", min: 0.25, max: 8, step: 0.25, l: "Répétition de la matière",
      h: "Multiplie les coordonnées de texture de la MATIÈRE (KHR_texture_transform) : c’est une propriété exportée, elle suit le ZIP et le GLB. À ne pas confondre avec « UV du maillage », affiché en bas du viewport, qui décrit combien de fois l’aperçu déroule la tuile sur la sphère ou le tore et ne quitte jamais l’écran. Le raccord mesuré garantit qu’aucune répétition ne montre de couture." },
    { k: "rotation", t: "range", min: 0, max: 360, step: 1, l: "Rotation UV", dec: 0, u: "°",
      h: "Fait tourner les coordonnées de texture, en degrés. Utile pour casser la lecture d’un motif directionnel (bois, brossage)." },
  ] },
  { id: "emission", label: "Émission", rows: [
    { k: "emissive", t: "color", l: "Couleur émise", live: 1,
      h: "Couleur de la lumière émise par la matière. Noir = aucune émission." },
    { k: "emissive_strength", t: "range", min: 0, max: 5, step: 0.05, l: "Intensité", live: 1,
      h: "Multiplie la map Emissive. Au-delà de 1, la matière déborde en bloom dans les moteurs qui le gèrent." },
  ] },
  { id: "clearcoat", label: "Vernis", rows: [
    { k: "clearcoat", t: "range", min: 0, max: 1, step: 0.01, l: "Vernis",
      h: "Couche transparente par-dessus la matière (carrosserie, bois verni). Elle a son propre reflet, indépendant de la rugosité en dessous." },
    { k: "clearcoat_roughness", t: "range", min: 0, max: 1, step: 0.01, l: "Rugosité du vernis",
      h: "Rugosité de cette seule couche : un vernis satiné garde une base mate en dessous." },
  ] },
  { id: "sheen", label: "Tissu", rows: [
    { k: "sheen", t: "range", min: 0, max: 1, step: 0.01, l: "Duvet",
      h: "Rétro-diffusion des fibres : le halo clair au bord des velours, laines et satins." },
    { k: "sheen_color", t: "color", l: "Couleur du duvet",
      h: "Teinte de ce halo. Un velours rouge a souvent un duvet plus clair et légèrement désaturé." },
  ] },
  { id: "transmission", label: "Transmission (verre)", rows: [
    { k: "transmission", t: "range", min: 0, max: 1, step: 0.01, l: "Transmission",
      h: "Part de lumière traversant la matière avec réfraction. 1 = verre clair. Contrairement à l’opacité, les reflets sont conservés." },
    { k: "ior", t: "range", min: 1, max: 2.5, step: 0.01, l: "Réfraction (IOR)",
      h: "1.0 air · 1.33 eau · 1.5 verre · 1.76 saphir · 2.42 diamant." },
    { k: "thickness", t: "range", min: 0, max: 5, step: 0.05, l: "Épaisseur",
      h: "Épaisseur du volume traversé, en unités du modèle. À 0, la matière se comporte comme une vitre infiniment fine." },
  ] },
];

const DERIVE_ROWS = [
  { k: "normal_strength", t: "range", min: 0, max: 2, step: 0.05, l: "Normal · force",
    h: "Amplitude des pentes lues dans la hauteur. Les convolutions sont cycliques : le relief reste raccordable bord à bord." },
  { k: "normal_invert_y", t: "check", l: "Normal · inverser Y",
    h: "Bascule OpenGL (+Y vers le haut, Blender, Godot) ↔ DirectX (Unreal, Unity par défaut). Un relief qui semble creusé au lieu d’être bombé = ce réglage." },
  { k: "roughness_bias", t: "range", min: 0, max: 1, step: 0.01, l: "Rugosité · biais",
    h: "Décale la rugosité moyenne calculée depuis la luminance. Au-dessus de 0.5, la matière devient globalement plus mate." },
  { k: "roughness_contrast", t: "range", min: 0, max: 1, step: 0.01, l: "Rugosité · contraste",
    h: "Écarte les valeurs autour du biais : sépare nettement les zones polies des zones abîmées." },
  { k: "roughness_invert", t: "check", l: "Rugosité · inverser",
    h: "Par défaut le clair est lisse. À inverser pour les matières où les parties claires sont les plus usées (poussière, calcaire)." },
  { k: "ao_strength", t: "range", min: 0, max: 2, step: 0.05, l: "AO · force",
    h: "Profondeur de l’occlusion déduite de la hauteur." },
  { k: "ao_radius", t: "range", min: 1, max: 16, step: 0.5, l: "AO · rayon", dec: 1, u: "px",
    h: "Portée du flou cyclique servant à détecter les creux, en pixels. Grand rayon = ombres larges et douces." },
  { k: "metallic_mode", t: "select", l: "Métallique · mode",
    opts: [["auto", "Auto (saturation + luminance)"], ["none", "Aucun (noir)"], ["luminance", "Luminance seuillée"]],
    h: "Auto suppose que le métal est peu saturé et clair. Aucun convient à toute matière non métallique et évite les faux positifs." },
  { k: "metallic_threshold", t: "range", min: 0, max: 1, step: 0.01, l: "Métallique · seuil",
    h: "Point de bascule de la rampe métal/non-métal." },
  { k: "emissive_threshold", t: "range", min: 0, max: 1, step: 0.01, l: "Émissif · seuil",
    h: "Au-dessus de ce niveau de luminance, le pixel est considéré comme lumineux (lave, néons, braises)." },
  { k: "height_detail", t: "range", min: 0, max: 1, step: 0.01, l: "Hauteur · détail",
    h: "0 = hauteur très lissée (formes générales), 1 = chaque grain compte. Le résultat conditionne la normale et l’AO." },
];

/* ───────────────────────── état ───────────────────────── */
const state = {
  materials: [],
  sel: null,          // id de la matière ouverte/sélectionnée
  view: "gallery",    // "gallery" | "editor"
  mesh: "sphere",
  env: "studio",
  envs: ENV_FALLBACK.slice(),
  pointLight: false,
  lightUV: { u: 0.7, v: 0.24 },
  lightPow: 1.4,
  cols: 3,
  spin: false,
  varied: true,     // un maillage différent par carte dans la galerie
  live3d: true,     // 3D montée à la demande sur les cartes visibles
  sort: "recent",
  scroll: 0,        // position de la galerie, restaurée au retour de l'éditeur
  models: [],
  model: "",
  res: 2048,
  ref: null,          // filename de l’image de référence
  busy: false,
  job: null,
  apiOk: null,
  presets: [],
  filter: "",
  propQ: "",          // filtre de l'inspecteur (libellés + textes d'aide)
  helpAll: false,     // aide de toutes les propriétés dépliée d'un coup
  seamScale: null,    // barème du raccord publié par l'API (/materials/seam-scale)
};

let envUrl = null;           // blob URL de l’environnement composé (éclairage)
let skyUrl = null;           // le même, assombri, pour le décor visible
let patchTimer = null;
let patchPending = { props: {}, derive: {}, name: undefined };
let reloadNeeded = false;

/* ───────────────────────── environnement + lumière ─────────────────────────
   La lumière ponctuelle déplaçable est un vrai éclairage : on compose
   l’équirectangulaire (récupéré de l’API, ou dessiné localement si la route
   manque) avec un lobe lumineux à la position du disque, et on le donne comme
   environment-image à la visionneuse. Déplacer le disque déplace l’éclat. */
function envDef(name) {
  return ENV_FALLBACK.find((e) => e.name === name) || ENV_FALLBACK[2];
}

function drawLocalEnv(ctx, w, h, name) {
  const d = envDef(name);
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, d.sky); g.addColorStop(0.48, d.hor);
  g.addColorStop(0.52, d.grd); g.addColorStop(1, d.grd);
  ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  if (d.sun) {
    const [u, v, p] = d.sun;
    const r = h * 0.42 * p;
    const rg = ctx.createRadialGradient(u * w, v * h, 0, u * w, v * h, r);
    rg.addColorStop(0, "rgba(255,248,225," + clamp(0.95 * p, 0, 1) + ")");
    rg.addColorStop(0.25, "rgba(255,232,180,.42)");
    rg.addColorStop(1, "rgba(255,220,160,0)");
    ctx.fillStyle = rg; ctx.fillRect(0, 0, w, h);
  }
}

function loadImg(src) {
  return new Promise((res, rej) => {
    const im = new Image();
    im.crossOrigin = "anonymous";
    im.onload = () => res(im);
    im.onerror = () => rej(new Error("image illisible"));
    im.src = src;
  });
}

let envBuilding = false, envAgain = false;
async function buildEnv() {
  if (envBuilding) { envAgain = true; return; }
  envBuilding = true;
  const W = 1024, H = 512;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const ctx = cv.getContext("2d");
  let base = null;
  if (state.apiOk) {
    base = await loadImg("/api/materials/envs/" + encodeURIComponent(state.env) + ".jpg")
      .catch(() => null);
  }
  if (base) ctx.drawImage(base, 0, 0, W, H);
  else drawLocalEnv(ctx, W, H, state.env);

  /* Lumière ponctuelle : DEUX lobes et non un seul. Un lobe large tout seul
     donne une tache molle qui ne produit aucun éclat sur une matière lisse ;
     un noyau serré et très chaud produit le reflet net qu'on attend d'une
     source, le halo large fournissant l'ambiance autour. Les deux lobes sont
     redessinés en x -W et x +W : une source qui déborde du bord de
     l'équirectangulaire doit rester continue une fois la sphère refermée,
     sinon le reflet se coupe net en tournant autour de l'objet. */
  if (state.pointLight) {
    const u = state.lightUV.u, v = state.lightUV.v, p = clamp(state.lightPow, 0, 3);
    const cy = v * H;
    ctx.globalCompositeOperation = "lighter";
    for (const dx of [-W, 0, W]) {
      const cx = u * W + dx;
      const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, H * 0.055 * (0.7 + p * 0.35));
      core.addColorStop(0, "rgba(255,253,246,1)");
      core.addColorStop(0.55, "rgba(255,247,226,.72)");
      core.addColorStop(1, "rgba(255,240,205,0)");
      ctx.fillStyle = core; ctx.fillRect(0, 0, W, H);
      const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, H * 0.34 * (0.55 + p * 0.5));
      halo.addColorStop(0, "rgba(255,246,224," + clamp(0.30 + p * 0.22, 0, 1) + ")");
      halo.addColorStop(0.22, "rgba(255,241,210,.34)");
      halo.addColorStop(1, "rgba(255,234,188,0)");
      ctx.fillStyle = halo; ctx.fillRect(0, 0, W, H);
    }
    ctx.globalCompositeOperation = "source-over";
  }

  /* ── plancher d'ambiance : rendre une matière SOMBRE lisible ────────────────
     Trois aperçus sur six (obsidienne, tissu tactique, cuivre patiné) étaient
     noir sur noir : l'albédo de ces matières est déjà très bas, et un
     équirectangulaire LDR dont la moitié basse est sombre ne renvoie presque
     rien vers la face non éclairée. Résultat : la moitié de la sphère tombait
     en dessous du fond de la carte, et il n'y avait plus de surface à lire.

     La correction est photographique, pas cosmétique : on ajoute un plancher
     d'ambiance CONSTANT dans toutes les directions (un additif blanc léger sur
     l'équirectangulaire d'ÉCLAIRAGE, avant le voile qui n'affecte que le décor
     visible). Aucune direction ne renvoie plus zéro, donc le relief se lit
     partout sur l'objet ; les hautes lumières, elles, ne bougent pas — la
     courbe « neutral » les compresse déjà. Le plancher est dosé par ambiance :
     fort là où le ciel est noir (nuit, dramatique), faible en plein jour. */
  const fill = ENV_FILL[state.env] != null ? ENV_FILL[state.env] : 0.12;
  if (fill > 0) {
    ctx.globalCompositeOperation = "lighter";
    ctx.fillStyle = "rgba(255,255,255," + fill + ")";
    ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = "source-over";
  }

  const url = await new Promise((res) => cv.toBlob((b) => res(URL.createObjectURL(b)), "image/png"));

  /* Le décor visible est le MÊME environnement, rabattu : l'éclairage reste
     physique (environment-image en pleine intensité) mais le fond ne mange pas
     l'écran — un ciel plein cadre écrase la matière et jure avec l'app sombre.
     Le voile est un dégradé et non un aplat : on garde une bande claire au
     ras de l'horizon, donc une VRAIE ligne d'horizon derrière l'objet, et on
     écrase le zénith et le nadir qui ne servent qu'à remplir. */
  const veil = ctx.createLinearGradient(0, 0, 0, H);
  veil.addColorStop(0.00, "rgba(4,5,7,.968)");
  veil.addColorStop(0.38, "rgba(5,6,9,.945)");
  veil.addColorStop(0.475, "rgba(8,9,13,.700)");
  veil.addColorStop(0.525, "rgba(6,6,9,.880)");
  veil.addColorStop(0.72, "rgba(4,4,6,.955)");
  veil.addColorStop(1.00, "rgba(3,3,4,.970)");
  ctx.fillStyle = veil;
  ctx.fillRect(0, 0, W, H);
  const skyU = await new Promise((res) => cv.toBlob((b) => res(URL.createObjectURL(b)), "image/png"));

  const old = envUrl, oldSky = skyUrl;
  envUrl = url; skyUrl = skyU;
  applyEnvToViewers();
  if (old) setTimeout(() => URL.revokeObjectURL(old), 1500);
  if (oldSky) setTimeout(() => URL.revokeObjectURL(oldSky), 1500);
  envBuilding = false;
  if (envAgain) { envAgain = false; buildEnv(); }
}

/* Exposition par environnement. Un équirectangulaire LDR ne porte pas la
   dynamique d'un vrai HDR : sans correction, la nuit est illisible et le plein
   jour délave. Ces sept valeurs ramènent les ambiances à une luminosité
   comparable — changer de ciel change alors l'ALLURE, pas le niveau. */
const ENV_EXPOSURE = {
  unlit: 1.12, daylight: 0.94, studio: 1.06, sunset: 1.18,
  overcast: 1.00, night: 1.95, dramatic: 1.42,
};

/* Plancher d'ambiance ajouté à l'équirectangulaire d'éclairage (0..1). Voir le
   commentaire dans buildEnv : c'est ce qui empêche la face non éclairée d'une
   matière sombre de tomber à zéro. Nul pour « sans éclairage », qui est déjà un
   dôme uniforme quasi blanc. */
const ENV_FILL = {
  unlit: 0, daylight: 0.08, studio: 0.13, sunset: 0.12,
  overcast: 0.09, night: 0.15, dramatic: 0.14,
};

/* Les VIGNETTES de galerie sont jugées en tant qu'images, à 250 px de côté et
   sur un fond de panneau sombre : elles ont besoin d'un poil plus de lumière
   que le viewport, où l'on peut orbiter pour aller chercher un reflet. Un
   surcroît d'exposition uniforme (et non un éclairage différent) garde la
   galerie et l'éditeur cohérents : la même matière, un cran plus lisible. */
const CARD_EXPOSURE = 1.22;
function cardExposure() {
  const base = ENV_EXPOSURE[state.env] != null ? ENV_EXPOSURE[state.env] : 1;
  return String(Math.round(base * CARD_EXPOSURE * 100) / 100);
}

function applyEnvToViewers() {
  if (!envUrl) return;
  $$("model-viewer").forEach((mv) => {
    mv.setAttribute("environment-image", envUrl);
    /* Les cartes de la galerie s'éclairent avec l'environnement mais gardent
       NOTRE fond (data-nosky) : un ciel plein cadre par carte écrase la matière
       et fait une planche-contact bruyante. Le décor visible reste au viewport,
       là où on regarde vraiment la matière. */
    if (mv.dataset.nosky === "1" || state.env === "unlit" || !skyUrl) mv.removeAttribute("skybox-image");
    else mv.setAttribute("skybox-image", skyUrl);
    // « neutral » (Khronos PBR Neutral) et non ACES : la courbe compresse les
    // hautes lumières SANS désaturer, donc la couleur à l'écran reste celle de
    // la matière. Dans une forge de matières, c'est la seule courbe défendable.
    mv.setAttribute("tone-mapping", "neutral");
    // Le viewport porte sa flaque de contact cuite dans le sol ; l'ombre
    // dynamique de model-viewer se poserait sous le sol et non sous l'objet.
    if (mv.id === "mv") mv.setAttribute("shadow-intensity", "0");
    mv.setAttribute("exposure", mv.dataset.nosky === "1"
      ? cardExposure()
      : (ENV_EXPOSURE[state.env] != null
          ? String(ENV_EXPOSURE[state.env])
          : state.env === "night" ? "1.6"
          : state.env === "unlit" ? "1.25" : "1"));
  });
  updateVpTag();
}

/* ───────────────────────── chargement ───────────────────────── */
function apiFail(e, what) {
  const bar = $("#apiBar");
  bar.classList.remove("hidden");
  $("#apiBarTitle").textContent = e && e.missing ? "API Matières absente" : "API en erreur";
  $("#apiBarMsg").textContent = (what ? what + " — " : "") +
    (e && e.missing
      ? "GET /api" + e.path + " n’existe pas encore sur ce backend. Le lab reste ouvert : la galerie et la forge s’activeront dès que la route répondra."
      : (e && e.message) || "erreur inconnue");
  const chip = $("#apiChip");
  chip.textContent = "API matières : indisponible";
  chip.classList.remove("ok"); chip.classList.add("ko");
  state.apiOk = false;
}
function apiOk(n) {
  $("#apiBar").classList.add("hidden");
  const chip = $("#apiChip");
  // le nombre de matières est écrit UNE fois, sur le compteur de la galerie :
  // ici on ne dit que ce que le compteur ne dit pas — que l'API répond.
  chip.textContent = "API matières : ok";
  chip.classList.add("ok"); chip.classList.remove("ko");
  state.apiOk = true;
}

async function loadMaterials() {
  try {
    const d = await api.get("/materials");
    state.materials = (d && d.materials) || [];
    apiOk(state.materials.length);
    renderGallery();
    if (state.sel) {
      const m = matById(state.sel);
      if (m) fillInspector(m); else closeEditor();
    }
  } catch (e) {
    state.materials = [];
    apiFail(e, "galerie");
    renderGallery();
  }
}

async function loadEnvs() {
  try {
    const d = await api.get("/materials/envs");
    const list = (d && d.envs) || [];
    if (list.length) {
      // on garde les couleurs de repli pour les noms connus (rendu local)
      state.envs = list.map((e) => {
        const f = ENV_FALLBACK.find((x) => x.name === e.name);
        return Object.assign({}, f || {}, { name: e.name, label: e.label || (f && f.label) || e.name });
      });
    }
  } catch (e) { /* repli déjà en place */ }
  renderEnvChips();
}

async function loadPresets() {
  try {
    const d = await api.get("/materials/presets");
    state.presets = (d && d.presets) || [];
  } catch (e) { state.presets = []; }
  const sel = $("#presetSel");
  sel.innerHTML = '<option value="">Appliquer un préréglage…</option>' +
    state.presets.map((p) => `<option value="${esc(p.id)}">${esc(p.label || p.id)}</option>`).join("");
  sel.disabled = !state.presets.length;
}

async function loadModels() {
  let models = [];
  try {
    const d = await api.get("/image-models");
    models = (d && d.models) || [];
    state.model = d.default || (models[0] && models[0].id) || "";
  } catch (e) { models = []; }
  if (!models.length) {
    models = [{ id: "flux", label: "FLUX schnell", note: "clé fal absente ?" }];
    state.model = "flux";
  }
  state.models = models;
  const saved = localStorage.getItem("mf_model");
  if (saved && models.some((m) => m.id === saved)) state.model = saved;
  $("#model").innerHTML = models.map((m) =>
    `<option value="${esc(m.id)}"${m.id === state.model ? " selected" : ""}>${esc(m.label || m.id)}</option>`).join("");
  updateEstimate();
}

async function loadLibrary() {
  try {
    const d = await api.get("/images");
    window.__mfImages = (d && d.images) || [];
  } catch (e) { window.__mfImages = []; }
  renderLibrary();
}

function renderLibrary() {
  const q = ($("#libSearch").value || "").toLowerCase();
  const list = (window.__mfImages || []).filter((i) => !q || i.filename.toLowerCase().includes(q));
  const g = $("#libGrid");
  if (!list.length) {
    g.innerHTML = '<div class="empty-note sm">Aucune image' + (q ? " pour « " + esc(q) + " »" : " dans la Library") + ".</div>";
    return;
  }
  g.innerHTML = list.slice(0, 90).map((i) =>
    `<img loading="lazy" data-fn="${esc(i.filename)}" title="${esc(i.filename)}"
      class="${i.filename === state.ref ? "sel" : ""}"
      src="/api/images/${encodeURIComponent(i.filename)}">`).join("");
  g.querySelectorAll("img").forEach((el) => { el.onclick = () => setRef(el.dataset.fn); });
}

function setRef(fn) {
  state.ref = fn || null;
  const box = $("#refPicked");
  if (!fn) { box.classList.add("hidden"); }
  else {
    box.classList.remove("hidden");
    $("#refThumb").src = "/api/images/" + encodeURIComponent(fn);
    $("#refName").textContent = fn;
  }
  renderLibrary();
  updateEstimate();
}

/* ═══════════ estimation coût + durée + PARCOURS de génération ═══════════

   La barre (Sorceress) affiche « ESTIMATED 10 credits » : un chiffre, sans
   durée ni ventilation. Meshy affiche « 1 min · 20 » avant de lancer. Ici on
   va plus loin : le parcours est détaillé étape par étape AVANT le lancement
   (chaque étape porte son coût et sa durée), puis LA MÊME liste devient la
   progression réelle pendant la forge. C'est aussi la preuve visuelle de la
   promesse : une seule ligne est facturée, les trois autres sont locales.
   ═════════════════════════════════════════════════════════════════════════ */

/* poids réellement mesuré sur disque des 8 maps + source (Mo, arrondi) */
const OUT_MB = { 1024: 5, 2048: 18, 4096: 48 };

function estimate() {
  const m = state.model || "flux";
  const fromLib = !!state.ref;                       // référence = aucune image à payer
  let cr = fromLib ? 0 : (MODEL_COST[m] != null ? MODEL_COST[m] : 6);
  let sec = fromLib ? 1 : (MODEL_SEC[m] != null ? MODEL_SEC[m] : 12);
  // l'enrichissement est un ajout de gabarit côté backend : 0 crédit
  // (la barre le facture +1 — voir material_store.PROMPT_ENHANCE).
  const enh = $("#enhance").checked && !fromLib;
  if (enh) sec += 2;
  const derive = DERIVE_SEC[state.res] || 8;
  const write = state.res >= 4096 ? 4 : state.res >= 2048 ? 2 : 1;
  let seam = 0;
  if ($("#seamless").checked) seam = state.res >= 4096 ? 4 : state.res >= 2048 ? 2 : 1;
  seam += 1;                                          // le score est mesuré 2x
  return { cr, sec: Math.round(sec + derive + seam + write), img: sec, derive, seam, write, fromLib, enh };
}

/* le plan : 4 étapes, dans l'ordre réel du job backend (voir _run_material_job).
   Les étapes ne portent PLUS ni prix ni durée : le prix et la durée totale sont
   sur le bouton, une fois chacun. Une étape dit ce qui se passe, pas ce que ça
   coûte — la ventilation « une seule ligne est facturée » tient en un mot,
   « facturée », posé sur la seule étape concernée. */
function planSteps() {
  const e = estimate();
  return [
    { key: "img", label: "Image de base", paid: e.cr > 0 },
    { key: "seam", label: $("#seamless").checked ? "Raccord + score mesuré" : "Score de raccord" },
    { key: "derive", label: "Dérivation des maps", paid: false },
    { key: "write", label: "Écriture + aperçu 3D", paid: false },
  ];
}

/* état d'affichage du parcours :
   -1 = plan (rien n'a tourné) · 0..3 = étape en cours · -2 = terminé.
   `t[i]` = horodatage de début de l'étape i, `done[i]` = sa durée réelle. */
let planRun = { active: -1, done: [], t: [] };

function renderPlan() {
  const steps = planSteps();
  const ol = $("#steps");
  if (!ol) return;
  ol.innerHTML = steps.map((s, i) => {
    const done = planRun.done[i] != null;
    const run = planRun.active === i;
    const cls = "step" + (done ? " ok" : run ? " run" : "") + (s.paid ? " paid" : "");
    const dot = done ? "✓" : String(i + 1);
    // à droite : RIEN avant le lancement (le prix et la durée sont sur le
    // bouton), la durée RÉELLE une fois l'étape franchie.
    const right = done
      ? `<span class="step-r">${planRun.done[i] ? planRun.done[i] + " s" : "fait"}</span>`
      : (s.paid ? '<span class="step-tag">facturée</span>' : "");
    return `<li class="${cls}"><span class="step-dot">${dot}</span>` +
      `<span class="step-l">${esc(s.label)}</span>${right}</li>`;
  }).join("");
}

function updateEstimate() {
  const e = estimate();
  $("#estCost").textContent = e.cr > 0 ? e.cr + " cr" : "0 cr";
  $("#estTime").textContent = "≈ " + e.sec + " s";
  const mb = OUT_MB[state.res] || 18;
  /* La définition ne se répète PAS ici : elle est écrite sur le segment choisi.
     En revanche il faut dire À QUOI elle s'applique — le rail affichait « 2K »
     pendant que les cartes portaient « 1024² », sans que rien à l'écran ne
     réconcilie les deux. Ce sont deux objets différents : la définition de la
     PROCHAINE forge, et celle de chaque matière DÉJÀ forgée. */
  $("#resNote").textContent = "S'applique à la prochaine forge ; chaque carte " +
    "porte la sienne. ≈ " + mb + " Mo · dérivation ≈ " + e.derive +
    " s · c'est aussi la taille maximale utile à l'export.";
  $("#modelNote").textContent = e.fromLib
    ? "Référence fournie : le modèle n'est pas appelé, la forge est entièrement gratuite."
    : "Seule cette étape est facturée. Les maps sont dérivées en local, hors ligne, re-calculables à volonté.";
  updateFullPrompt();
  renderPlan();
}

/* Invite exacte envoyée au modèle : le même gabarit que le backend
   (material_store.PROMPT_TEMPLATE / PROMPT_ENHANCE). La barre injecte le sien
   en silence ; ici il est lisible avant de dépenser un crédit. */
const PROMPT_TPL = ["PBR texture, flat surface, ", ", top-down view, full frame, no objects, no 3D render, no diagram"];
const PROMPT_ENH = ", seamless tileable, even diffuse lighting, no baked shadows, no specular highlights, high micro-detail, physically plausible albedo";

function updateFullPrompt() {
  const el = $("#fullPrompt");
  if (!el) return;
  if (state.ref) {
    el.innerHTML = "aucune invite : l'image de base vient de la référence <em>" + esc(state.ref) + "</em>.";
    return;
  }
  const d = ($("#prompt").value || "").trim();
  el.innerHTML = esc(PROMPT_TPL[0]) + "<em>" + esc(d || "…") + "</em>" + esc(PROMPT_TPL[1]) +
    ($("#enhance").checked ? esc(PROMPT_ENH) : "");
}

/* amorces d'invite cliquables (la barre les écrit en prose, on les rend jouables) */
const SEEDS = ["fer rouillé", "verre givré", "cristal alien",
               "pierre moussue", "or martelé", "béton brut"];
function renderSeeds() {
  const box = $("#seedChips");
  if (!box) return;
  box.innerHTML = SEEDS.map((s) => `<button class="chip" data-seed="${esc(s)}">${esc(s)}</button>`).join("");
  box.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => { $("#prompt").value = b.dataset.seed; setRef(null); updateEstimate(); $("#prompt").focus(); };
  });
}

/* ───────────────────────── génération ───────────────────────── */
async function generate() {
  if (state.busy) return;
  const prompt = ($("#prompt").value || "").trim();
  if (!prompt && !state.ref) { toast("Décris une matière ou choisis une image de référence.", true); return; }
  state.busy = true; setBusy(true);
  planRun = { active: 0, done: [], t: [Date.now()] };
  renderPlan();
  const st = $("#genStatus");
  st.classList.remove("hidden", "err");
  st.textContent = "Envoi…";
  setProgress(2);
  try {
    const body = {
      prompt: prompt, model: state.model, res: state.res,
      seamless: $("#seamless").checked, seam_method: $("#seamMethod").value,
      enhance: $("#enhance").checked,
    };
    if (state.ref) body.filename = state.ref;
    const d = await api.post("/materials/generate", body);
    const jid = d && d.job_id;
    if (!jid) throw new Error("réponse sans job_id");
    state.job = jid;
    await pollJob(jid, st);
  } catch (e) {
    st.classList.add("err");
    st.textContent = "Échec : " + (e.missing ? "POST /api/materials/generate n’existe pas encore." : e.message);
    if (e.missing) apiFail(e, "forge");
    toast("Forge impossible : " + e.message, true);
    setProgress(0);
    planRun = { active: -1, done: [], t: [] };
    renderPlan();
  }
  state.busy = false; state.job = null; setBusy(false);
}

function setProgress(pct) {
  const w = $("#progWrap"), b = $("#progBar");
  if (!pct) { w.classList.add("hidden"); b.style.width = "0%"; return; }
  w.classList.remove("hidden");
  b.style.width = clamp(pct, 0, 100) + "%";
}
function setBusy(b) {
  $("#genBtn").disabled = b;
  $("#genLabel").textContent = b ? "⚒ Forge en cours…" : "⚒ Forger la matière";
}

/* pct renvoyé par le backend -> index d'étape du parcours affiché.
   Les seuils suivent _run_material_job : 5 image · 40 préparation ·
   55 raccord · 70 dérivation · 90 écriture · 100 terminé. */
function stepIndexFromPct(pct) {
  if (pct >= 90) return 3;
  if (pct >= 70) return 2;
  if (pct >= 55) return 1;
  return 0;
}
/* fait avancer le parcours : les étapes franchies se figent avec leur durée
   RÉELLE (le plan annonçait une estimation, la progression rend des comptes). */
function advancePlan(idx) {
  if (planRun.active === idx) return;
  const now = Date.now();
  // une étape franchie entre deux sondages n'a pas de début connu : on la coche
  // sans lui inventer une durée (0 = « fait », pas « 1 s »).
  for (let i = planRun.active; i >= 0 && i < idx; i++) {
    const t0 = planRun.t[i];
    planRun.done[i] = t0 ? Math.max(1, Math.round((now - t0) / 1000)) : 0;
  }
  planRun.active = idx;
  planRun.t[idx] = now;
  renderPlan();
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pollJob(jid, st) {
  const t0 = Date.now();
  for (;;) {
    await sleep(900);
    let j;
    try { j = await api.get("/materials/jobs/" + encodeURIComponent(jid)); }
    catch (e) { throw e; }
    const pct = num(j.pct, 0);
    setProgress(Math.max(4, pct));
    const secs = Math.round((Date.now() - t0) / 1000);
    if (j.status === "running" || j.status === "done") advancePlan(stepIndexFromPct(pct));
    st.textContent = (j.step || j.status || "…") + " · " + Math.round(pct) + " % · " + secs + " s";
    if (j.status === "done") {
      setProgress(100);
      advancePlan(4);
      planRun.active = -2;                 // -2 : tout est fait, rien ne tourne
      renderPlan();
      const mat = j.material;
      if (mat) {
        upsert(mat);
        renderGallery();
        openMaterial(mat.id);
        const s = mat.seam || {};
        toast("Matière forgée : " + (mat.name || mat.id) +
          (s.ratio != null ? " · raccord " + fmt(s.ratio, 2) +
            (seamGrade(s) ? " (" + seamGrade(s) + ")" : "") : ""));
      } else { await loadMaterials(); }
      st.textContent = "Terminé en " + secs + " s.";
      setTimeout(() => setProgress(0), 1200);
      return;
    }
    if (j.status === "failed") throw new Error(j.error || "tâche échouée");
  }
}

/* ───────────────────────── galerie ───────────────────────── */
function matById(id) { return state.materials.find((m) => m.id === id) || null; }
function upsert(mat) {
  const i = state.materials.findIndex((m) => m.id === mat.id);
  if (i >= 0) state.materials[i] = mat; else state.materials.unshift(mat);
}

/* ── LE RACCORD, D'APRÈS LA MESURE QUI DÉCIDE ────────────────────────────────
   Cet écran affichait « AVANT 5.9 → APRÈS 0.0 ». Les deux termes étaient
   étiquetés, lisibles, honnêtes en apparence — et le second ne mesurait rien :
   la passe seamless se termine par une fermeture de boucle qui rend la colonne
   0 identique à la colonne w-1, exactement ce que l'ancien score compare. Un
   0.0 obtenu par construction, affiché en vert, sur les seize matières du
   disque : ce n'est pas une mesure, c'est une tautologie mise en avant.

   Le backend publie désormais le rapport qui décide, `seam.ratio` (marche à la
   jonction ÷ marche interne médiane, pire des trois échelles), son palier
   `seam.grade`, et le barème lui-même sur `/materials/seam-scale` — seuils
   compris. C'est CE nombre qu'on montre, avec son mot. Le vieux score de bord
   reste dans l'infobulle, dit pour ce qu'il est. */
function seamScale() {
  return state.seamScale || { visible_from: 2.0, grades: [] };
}
async function loadSeamScale() {
  try { state.seamScale = await api.get("/materials/seam-scale"); }
  catch (e) { /* repli : le 2.0 du contrat, écrit dans seamScale() */ }
}

/* Le mot du palier vient du barème publié quand le backend n'a pas déjà
   tranché : l'écran ne redécoupe pas l'échelle dans son coin. */
function seamGrade(s) {
  if (s.grade) return s.grade;
  const r = num(s.ratio, -1);
  if (r < 0) return "";
  const g = (seamScale().grades || []).find((x) => x.max == null || r <= x.max);
  return g ? g.grade : "";
}

/* ── LA COULEUR SUIT LE PALIER, LA LONGUEUR SUIT L'ÉCART ─────────────────────
   La pastille n'avait que DEUX couleurs pour QUATRE paliers : « passe » ou
   « échoue », de part et d'autre du seuil 2.0. Résultat : 0.33 « invisible » et
   1.66 « discret » sortaient rigoureusement du même vert — même texte, même
   filet, octet pour octet — alors que la légende de la pastille définit 1.00
   comme le point où la jonction cesse d'être contenue par le grain de la
   matière. Sur une galerie de seize cartes on balaie la couleur, pas le mot :
   une matière aux deux tiers du seuil se lisait « propre ».

   Deux corrections, pas une :
     1. une couleur PAR PALIER du barème publié (invisible · discret · visible ·
        cassé) — le mot et la couleur ne peuvent plus se contredire ;
     2. une jauge dont la longueur est proportionnelle au rapport RÉEL, avec les
        seuils 1.00 et 2.00 marqués dessus. 0.33 est un huitième de barre, 1.66
        en fait cinq — l'écart de 3× se voit, l'écart de 4 % (0.98 → 1.02) se
        voit comme ce qu'il est : deux cheveux d'écart de part et d'autre d'un
        trait. Le lecteur presse ne dépend plus du franchissement d'un mot. */
const SEAM_TIERS = ["invisible", "discret", "visible", "casse"];
const slugFr = (s) => String(s == null ? "" : s).toLowerCase().trim()
  .replace(/[éèêë]/g, "e").replace(/[àâä]/g, "a").replace(/[îï]/g, "i")
  .replace(/[ôö]/g, "o").replace(/[ùûü]/g, "u").replace(/ç/g, "c");

function seamTier(s) {
  const g = slugFr(seamGrade(s));
  if (!g) return "";
  if (SEAM_TIERS.indexOf(g) >= 0) return g;
  /* mot hors des quatre connus : on le classe par sa POSITION dans le barème
     publié plutôt que de le laisser sans couleur. */
  const grades = seamScale().grades || [];
  const i = grades.findIndex((x) => slugFr(x.grade) === g);
  if (i >= 0) return SEAM_TIERS[Math.min(i, SEAM_TIERS.length - 1)];
  return "";
}

/* échelle de la jauge : le dernier seuil FINI du barème (4.0 aujourd'hui), pour
   que la barre ne soit jamais recalibrée dans son coin par cet écran. */
function seamAxis() {
  const g = (seamScale().grades || []).map((x) => num(x.max, NaN)).filter((v) => isFinite(v));
  const top = g.length ? Math.max.apply(null, g) : 4;
  const t1 = num(seamScale().grades && seamScale().grades[0] && seamScale().grades[0].max, 1);
  const t2 = num(seamScale().visible_from, 2);
  return { top: top > 0 ? top : 4, t1: t1, t2: t2 };
}

function seamHtml(m, cls) {
  const s = m.seam || {};
  const hasRatio = s.ratio != null;
  if (!hasRatio && s.before == null) return "";
  const tier = hasRatio ? seamTier(s) : "";
  const sc = seamScale();
  const ax = seamAxis();
  const pct = (v) => clamp((num(v, 0) / ax.top) * 100, 0, 100).toFixed(1) + "%";
  const t = hasRatio
    ? "Raccord : " + fmt(s.ratio, 2) + " — " +
      (sc.note || "1.00 = la jonction ne dépasse pas la variation interne du motif.") +
      " Paliers : ≤ " + fmt(ax.t1, 2) + " invisible, ≤ " + fmt(ax.t2, 2) + " discret, ≤ " +
      fmt(ax.top, 2) + " visible, au-delà cassé — la jauge situe ce rapport sur cette " +
      "échelle, les deux traits sont les seuils." +
      (s.before != null ? " (Ancien score de bord avant la passe : " + fmt(s.before, 1) +
        " ; l'après vaut 0.00 par construction, il ne mesure rien.)" : "")
    : "Score de bord avant la passe : " + fmt(s.before, 1) +
      ". Rapport de jonction pas encore calculé pour cette matière.";
  const gauge = hasRatio
    ? '<i class="sm-bar" aria-hidden="true" style="--p:' + pct(s.ratio) +
      ";--t1:" + pct(ax.t1) + ";--t2:" + pct(ax.t2) + '"></i>'
    : "";
  const body = hasRatio
    ? '<i class="sm-l raw">raccord</i><b class="sm-v res">' + fmt(s.ratio, 2) + "</b>" +
      gauge + '<i class="sm-g">' + esc(seamGrade(s)) + "</i>"
    : '<i class="sm-l raw">avant</i><b class="sm-v">' + fmt(s.before, 1) + "</b>";
  return '<span class="' + cls + " seamv" + (tier ? " t-" + tier : "") + '" title="' +
    esc(t) + '">' + body + "</span>";
}

/* id des ressources : normalement l'id de la matière. Le harnais de charge
   (__mf.__stress) clone des cartes en gardant la source réelle — les URL
   restent de vraies URL, la mesure reste honnête. */
function srcId(m) { return m._src || m.id; }

/* `stage` = le sol d'aperçu (grille + flaque de contact) : dans le viewport
   plein, jamais dans les vignettes de carte où il mangerait la matière.
   `scale` = l'échelle de matière par maillage (une tuile ~ une unité monde) :
   partout, une sphère habillée d'un seul enroulement se lit comme un globe. */
function glbUrl(m, res, mesh, stage) {
  return "/api/materials/" + encodeURIComponent(srcId(m)) + "/preview.glb?mesh=" +
    encodeURIComponent(mesh || state.mesh) + "&res=" + (res || 1024) +
    "&scale=1&stage=" + (stage ? 1 : 0) + "&v=" + (m._v || 0);
}

/* ───────────────────────── cadrage du viewport ─────────────────────────
   Le cadrage automatique de <model-viewer> colle le maillage aux quatre bords :
   l'objet est à l'étroit et le sol n'a plus de place pour exister. On impose
   donc une orbite, une cible et un champ par maillage — un 35 mm plutôt qu'un
   grand angle : moins de déformation, davantage l'allure d'une photo produit.
   [azimut, polaire, rayon, cible y] */
/* Le plan et le pavage sont des quads VERTICAUX (gltf_builder._mesh_grid,
   normale +Z). Les cadrer en biais — azimut 10°, polaire 76° — revenait à
   choisir l'angle où une couture ne se voit pas, sur l'écran dont c'est
   précisément la raison d'être. Ils sont maintenant PLEIN CADRE, face à
   l'objectif : azimut 0, polaire 90. La caméra reste libre : on peut toujours
   basculer à la main pour juger le relief. */
const FRAME = {
  sphere: [28, 68, 5.30, 0], cube: [32, 66, 6.20, 0],
  torus: [28, 60, 5.00, 0.05], cylinder: [30, 68, 5.60, 0],
  plane: [0, 90, 4.35, 0], tiled: [0, 90, 4.35, 0],
};
/* Même règle sur les vignettes de carte : une carte « Plan » ou « Pavage 3×3 »
   montre la tuile de face, pas de trois quarts. */
const CARD_ORBIT = { plane: "0deg 90deg 100%", tiled: "0deg 90deg 100%" };
const CARD_ORBIT_DEF = "32deg 72deg 102%";
const FOV = 32;

/* Topologie et échelle de matière par maillage : les mêmes chiffres que le
   GLB servi (gltf_builder.MESH_UV / mesh_stats). Meshy affiche la topologie de
   ce qu'il montre, Material Forge non — c'est une information gratuite qui
   dit au regard ce qu'il est en train de juger. [triangles, ru, rv]
   Les répétitions sont ENTIÈRES depuis la correction du pavage : voir
   gltf_builder.MESH_UV. */
const MESH_INFO = {
  sphere: [6240, 4, 2], cube: [12, 2, 2], torus: [2304, 6, 3],
  cylinder: [192, 3, 1], plane: [2, 1, 1], tiled: [18, 3, 3],
};

/* L'étiquette du viewport ne redit ni le maillage ni l'environnement : ils
   sont surlignés dans la rangée de puces juste au-dessus. Elle ne porte que ce
   qu'aucune commande ne montre — la topologie et l'enroulement UV réellement
   servis.

   Elle disait « tuile 4×2 » pendant que l'inspecteur disait « pavage ×1 » :
   deux nombres, deux mots, une seule notion apparente. Ce sont pourtant deux
   choses distinctes — combien de fois l'APERÇU déroule la tuile sur ce
   maillage-ci (ici, jamais exporté), et le facteur de répétition de la MATIÈRE
   (propriété exportée). Elles portent maintenant deux noms qui ne se
   confondent pas : « UV du maillage » et « Répétition de la matière ». */
function updateVpTag() {
  const t = $("#vpTag");
  if (!t) return;
  const inf = MESH_INFO[state.mesh] || MESH_INFO.sphere;
  t.textContent = inf[0].toLocaleString("fr-FR") + " tris · UV du maillage " +
    inf[1] + "×" + inf[2];
}

function frameViewport(mesh, animate) {
  const mv = $("#mv");
  if (!mv) return;
  const f = FRAME[mesh || state.mesh] || FRAME.sphere;
  if (!animate) mv.setAttribute("interpolation-decay", "0");
  mv.setAttribute("field-of-view", FOV + "deg");
  mv.setAttribute("min-field-of-view", "12deg");
  mv.setAttribute("max-field-of-view", "48deg");
  mv.setAttribute("camera-target", "0m " + f[3] + "m 0m");
  mv.setAttribute("camera-orbit", f[0] + "deg " + f[1] + "deg " + f[2] + "m");
  // sous l'horizon on verrait le dessous du sol : l'orbite s'arrête juste avant.
  mv.setAttribute("min-camera-orbit", "auto 12deg 2.2m");
  mv.setAttribute("max-camera-orbit", "auto 91deg 14m");
  if (!animate) setTimeout(() => mv.setAttribute("interpolation-decay", "120"), 60);
  updateVpTag();
}

/* Poster de carte : la vignette si elle existe, sinon la base color réduite.
   Une carte n'est JAMAIS un rectangle gris en attente — l'image arrive tout de
   suite, la 3D se pose par-dessus quand son tour vient. */
function posterUrl(m, res) {
  const id = encodeURIComponent(srcId(m));
  return m.thumb
    ? "/api/materials/" + id + "/thumb.png?v=" + (m._v || 0)
    : "/api/materials/" + id + "/map/basecolor.png?res=" + (res || 256) + "&v=" + (m._v || 0);
}

/* Maillage d’une carte : le maillage courant, ou un maillage différent par
   carte (« variés ») pour que la galerie montre la matière sur plusieurs
   formes — une sphère ne dit rien du comportement sur une arête. */
function cardMesh(i) {
  if (!state.varied) return state.mesh;
  const start = Math.max(0, MESHES.findIndex((x) => x.id === state.mesh));
  return MESHES[(start + i) % MESHES.length].id;
}

/* Le GLB du viewport reste en 1024 : au-delà, les maps embarquées pèsent une
   dizaine de Mo pour un gain nul à l'écran (mesuré : 3,5 Mo en 1024 contre
   9,9 Mo en 2048). L'export, lui, sort la pleine résolution. */
function setViewportSrc(m) {
  const mv = $("#mv"), ld = $("#vpLoad");
  if (!mv || !m) return;
  ld.classList.remove("hidden", "err");
  ld.textContent = "chargement de l’aperçu 3D…";
  mv.addEventListener("load", () => {
    ld.classList.add("hidden");
    frameViewport(state.mesh, false);
  }, { once: true });
  mv.addEventListener("error", () => {
    ld.classList.remove("hidden");
    ld.classList.add("err");
    ld.textContent = "aperçu 3D indisponible (GET /api/materials/" + m.id + "/preview.glb)";
  }, { once: true });
  frameViewport(state.mesh, false);
  mv.src = glbUrl(m, 1024, state.mesh, true);
}

/* source lisible d'une carte : le modèle payant, ou l'origine locale */
function sourceLabel(m) {
  const s = m.source || {};
  if (s.model) return s.model;
  if (s.kind === "library") return "library · " + (s.filename || "—");
  if (s.kind === "upload") return "import · " + (s.filename || "—");
  return s.kind || "—";
}
function cardSub(m) {
  const s = m.source || {};
  if (m.full_prompt) return m.full_prompt;
  if (s.kind && s.kind !== "prompt" && s.filename) return "d’après " + s.filename;
  return m.prompt || "";
}

/* Il n'y a plus de « carte de statistiques » : sur quinze matières elle
   imprimait le compte (déjà dans le compteur), le nombre de maps (= compte × 8),
   un raccord médian constamment à 0.00 et un diagnostic d'aperçus 3D. Trois
   lignes sur quatre étaient dérivées ou constantes. Ce qui restait d'utile — le
   budget d'aperçus — vit sous « Affichage », près de l'interrupteur qui le
   gouverne. */
function updateStats() { updateLiveNote(); }

/* Le badge de titre annonçait « 8 MAPS PBR » en dur, c'est-à-dire une promesse
   écrite dans le HTML. Il compte maintenant ce que l'API DÉCLARE réellement sur
   la matière la mieux fournie : si le backend n'en livre que six, le badge dit
   six. Sans matière, il ne promet rien. */
function updateMapsBadge() {
  const b = $("#mapsBadge");
  if (!b) return;
  let k = 0, best = null;
  state.materials.forEach((m) => {
    const n = (m.maps || []).length;
    if (n > k) { k = n; best = m; }
  });
  /* « LIVRÉES » et non « PBR » : le mot dit ce que le chiffre compte, et c'est
     le MÊME chiffre que celui des cartes. Le bandeau annonçait 8 pendant que
     douze cartes lisaient « 6/8 » ; les deux racontent maintenant l'histoire
     du jeu livré, les cartes ajoutant seulement combien de ces huit sont des
     champs constants sur LEUR matière. */
  b.textContent = k ? k + " MAPS LIVRÉES" : "MAPS PBR";
  /* Un badge qui annonce un compte sans donner à le vérifier reste une
     promesse : il ouvre la preuve de la matière la mieux fournie, et chaque
     carte porte la sienne. */
  b.disabled = !k;
  b.dataset.mid = best ? best.id : "";
  b.title = k
    ? "Chaque matière livre ces " + k + " fichiers, sans exception — c'est le " +
      "compte que portent aussi les cartes. Certains d'entre eux sont des " +
      "champs constants quand la matière est diélectrique ou n'émet pas : une " +
      "propriété de la matière, pas une map manquante ; la carte dit lesquels. " +
      "Cliquer : la preuve sur « " + (best.name || best.id) + " » — images, " +
      "mesures, corrélations, contenu du ZIP."
    : "Le compte s'affichera dès la première matière.";
}

/* ───────────────────────── tri de la galerie ───────────────────────── */
const SORTS = [
  { id: "recent", label: "Plus récentes" },
  { id: "name", label: "Nom (A → Z)" },
  { id: "seam", label: "Meilleur raccord" },
  { id: "res", label: "Résolution ↓" },
];
function sortList(list) {
  const l = list.slice();
  if (state.sort === "name") {
    l.sort((a, b) => String(a.name || a.prompt || a.id)
      .localeCompare(String(b.name || b.prompt || b.id), "fr", { numeric: true }));
  } else if (state.sort === "seam") {
    /* trier sur `after` revenait à trier seize zéros : l'ordre ne bougeait
       jamais. On trie sur le rapport de jonction, le seul terme qui varie. */
    const s = (m) => (m.seam && m.seam.ratio != null ? num(m.seam.ratio, 99) : 99);
    l.sort((a, b) => s(a) - s(b));
  } else if (state.sort === "res") {
    l.sort((a, b) => num(b.res, 0) - num(a.res, 0));
  }
  return l;                                    // "recent" = ordre de l'API
}

/* ─────────────────── aperçus 3D montés à la demande ───────────────────
   Un <model-viewer> par carte, c'est une scène WebGL + un GLB : à 60 matières
   la page rame, la mémoire grimpe et le backend reconstruit 60 GLB. Ici chaque
   carte affiche d'abord son poster (immédiat), et la 3D n'est montée que pour
   les cartes VISIBLES, dans la limite d'un budget ; une carte qui sort de
   l'écran rend sa scène et redevient une image. Le compteur « aperçus 3D
   actifs » de l'inspecteur montre le budget en action. */
const live = {
  io: null,
  visible: new Set(),
  mounted: new Map(),      // id -> model-viewer
  loading: 0,
  budget() { return clamp(state.cols * 3 + 2, 6, 14); },

  reset() {
    if (this.io) this.io.disconnect();
    this.mounted.forEach((mv) => { try { mv.remove(); } catch (e) { /* noop */ } });
    this.mounted.clear();
    this.visible.clear();
    this.loading = 0;
    this.io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        const id = en.target.dataset.id;
        if (!id) return;
        if (en.isIntersecting) this.visible.add(id); else this.visible.delete(id);
      });
      this.pump();
    }, { root: $("#gallery"), rootMargin: "300px 0px", threshold: 0.01 });
    $$("#gallery .card").forEach((c) => this.io.observe(c));
    this.pump();
  },

  pump() {
    if (!state.live3d) { this.sweep(0); updateLiveNote(); return; }
    this.sweep(this.budget());
    let free = this.budget() - this.mounted.size;
    for (const id of this.visible) {
      if (free <= 0 || this.loading >= 2) break;
      if (this.mounted.has(id)) continue;
      if (this.mount(id)) { free--; }
    }
    updateLiveNote();
  },

  /* rend les scènes des cartes hors écran jusqu'à retomber sous le budget */
  sweep(budget) {
    if (this.mounted.size <= budget) return;
    const doomed = [];
    this.mounted.forEach((mv, id) => { if (!this.visible.has(id)) doomed.push(id); });
    for (const id of doomed) {
      if (this.mounted.size <= budget) break;
      this.unmount(id);
    }
  },

  mount(id) {
    const card = $(`#gallery .card[data-id="${CSS.escape(id)}"]`);
    const m = matById(id);
    if (!card || !m) return false;
    const slot = card.querySelector(".mv-slot");
    if (!slot || slot.firstChild) return false;
    const cmesh = card.dataset.mesh || state.mesh;
    const mv = document.createElement("model-viewer");
    mv.setAttribute("interaction-prompt", "none");
    mv.setAttribute("camera-orbit", CARD_ORBIT[cmesh] || CARD_ORBIT_DEF);
    mv.setAttribute("shadow-intensity", "0.9");
    mv.setAttribute("shadow-softness", "0.85");
    mv.dataset.nosky = "1";          // les cartes gardent NOTRE fond, pas le ciel
    mv.setAttribute("exposure", cardExposure());
    mv.setAttribute("tone-mapping", "neutral");
    mv.setAttribute("disable-zoom", "");
    if (state.spin) { mv.setAttribute("auto-rotate", ""); mv.setAttribute("rotation-per-second", "16deg"); }
    if (envUrl) mv.setAttribute("environment-image", envUrl);
    this.loading++;
    const done = () => { this.loading = Math.max(0, this.loading - 1); this.pump(); };
    mv.addEventListener("load", () => { card.classList.add("live"); done(); }, { once: true });
    mv.addEventListener("error", () => {
      card.classList.add("noglb");
      mv.remove();
      this.mounted.delete(id);
      done();
    }, { once: true });
    mv.src = glbUrl(m, 256, cmesh);
    slot.appendChild(mv);
    this.mounted.set(id, mv);
    return true;
  },

  unmount(id) {
    const mv = this.mounted.get(id);
    if (!mv) return;
    const card = mv.closest(".card");
    if (card) card.classList.remove("live");
    try { mv.src = ""; } catch (e) { /* noop */ }
    mv.remove();
    this.mounted.delete(id);
  },
};

/* « 8 scène(s) sur un budget de 11 » était de la télémétrie de moteur : deux
   nombres qui bougent tout seuls, qu'aucune décision n'utilise et qu'aucune
   commande ne règle. L'interrupteur reste, sa conséquence est dite en clair ;
   le compteur vit en console (__mf.live) pour le diagnostic. */
function updateLiveNote() {
  const n = $("#liveNote");
  if (!n) return;
  n.textContent = state.live3d
    ? "La 3D n'est montée que pour les cartes visibles à l'écran ; les autres restent des vignettes."
    : "Aperçus figés : seules les vignettes sont chargées.";
}

/* ── la définition : une donnée, ou une constante ? ─────────────────────────
   La pastille « 1024² » était imprimée sur les neuf cartes visibles avec la
   même valeur : zéro information, neuf fois. Elle n'est plus portée par une
   carte que lorsqu'elle la DISTINGUE des autres. La valeur courante de la
   galerie est écrite une seule fois, sur le compteur ; les cartes qui s'en
   écartent — et elles seules — gardent leur pastille. */
function resCommon(list) {
  const tally = new Map();
  list.forEach((m) => {
    const r = num(m.res, 0);
    if (r) tally.set(r, (tally.get(r) || 0) + 1);
  });
  if (!tally.size) return { base: 0, uniform: true, n: 0 };
  let base = 0, best = -1;
  tally.forEach((c, r) => { if (c > best || (c === best && r > base)) { best = c; base = r; } });
  return { base: base, uniform: tally.size === 1, n: list.length - best };
}
let resView = { base: 0, uniform: true, n: 0 };

function renderGallery() {
  const g = $("#gallery");
  const q = state.filter.toLowerCase();
  const list = sortList(state.materials.filter((m) => !q ||
    (m.name || "").toLowerCase().includes(q) ||
    (m.prompt || "").toLowerCase().includes(q) ||
    ((m.source || {}).filename || "").toLowerCase().includes(q)));
  const n = state.materials.length;
  resView = resCommon(list);
  const head = n + " matière" + (n > 1 ? "s" : "") +
    (q ? " · " + list.length + " affichée" + (list.length > 1 ? "s" : "") : "");
  let rtxt = "", rtit = "";
  /* en mode éditeur, la définition de la matière ouverte est déjà écrite à
     droite du score : on ne la met pas deux fois dans la même barre */
  if (resView.base && state.view === "gallery") {
    if (resView.uniform) {
      rtxt = "toutes en " + resView.base + "²";
      rtit = "Toutes les matières affichées ont la même définition : aucune carte n'a besoin de la répéter.";
    } else {
      rtxt = resView.base + "² sauf indication";
      rtit = "Définition de la plupart des matières affichées. Les " + resView.n +
        " qui s'en écartent portent la leur sur leur carte.";
    }
  }
  $("#count").innerHTML = esc(head) +
    (rtxt ? ' <i class="cnt-res" title="' + esc(rtit) + '">' + esc(rtxt) + "</i>" : "");
  updateMapsBadge();
  g.style.setProperty("--cols", state.cols);
  const empty = $("#galEmpty");
  if (state.view !== "gallery") {
    g.classList.add("hidden"); empty.classList.add("hidden");
    if (live.io) live.io.disconnect();
    live.mounted.forEach((mv, id) => live.unmount(id));
    updateStats();
    return;
  }
  g.classList.remove("hidden");
  if (!list.length) {
    g.innerHTML = "";
    g.classList.add("hidden");
    empty.classList.remove("hidden");
    empty.innerHTML = emptyHtml(q);
    wireEmpty();
    updateStats();
    return;
  }
  empty.classList.add("hidden");
  g.innerHTML = list.map((m, i) => cardHtml(m, i)).join("");
  list.forEach((m) => wireCard(m));
  live.reset();
  updateStats();
}

/* ─────────────── états vides : jamais un cul-de-sac ─────────────── */
const SEED_PROMPTS = ["fer rouillé", "verre givré", "cristal alien",
  "écorce de bouleau", "or martelé", "béton usé"];

function emptyHtml(q) {
  if (state.apiOk === false) {
    return `<div class="empty-card">
      <div class="empty-ic">⚠</div>
      <h3>L’API Matières ne répond pas</h3>
      <p>Le lab reste ouvert. Dès que <code>GET /api/materials</code> répond, la galerie se remplit ici.</p>
      <button class="btn sm" data-empty="retry">Réessayer</button>
    </div>`;
  }
  if (q) {
    return `<div class="empty-card">
      <div class="empty-ic">🔎</div>
      <h3>Aucune matière pour « ${esc(state.filter)} »</h3>
      <p>${state.materials.length} matière${state.materials.length > 1 ? "s" : ""} en stock — le filtre porte sur le nom, l’invite et l’image d’origine.</p>
      <button class="btn sm" data-empty="clear">Effacer le filtre</button>
    </div>`;
  }
  return `<div class="empty-card">
    <div class="empty-ic">⚒</div>
    <h3>La galerie est vide</h3>
    <p>Décris une matière à gauche, ou pars d’une image de la Library.
       Chaque forge dépose ici une carte en aperçu 3D réel, avec ses
       <b>maps PBR</b> et son <b>score de raccord mesuré</b>.</p>
    <div class="empty-chips">
      ${SEED_PROMPTS.map((p) => `<button class="chip" data-empty="seed" data-p="${esc(p)}">${esc(p)}</button>`).join("")}
    </div>
    <p class="empty-foot">Rouvrir une matière plus tard : un clic sur sa carte la rouvre
      dans l’éditeur, propriétés et maps intactes.</p>
  </div>`;
}

function wireEmpty() {
  $$("#galEmpty [data-empty]").forEach((b) => {
    b.onclick = () => {
      const a = b.dataset.empty;
      if (a === "retry") boot(true);
      else if (a === "clear") { state.filter = ""; $("#galSearch").value = ""; renderGallery(); }
      else if (a === "seed") {
        $("#prompt").value = b.dataset.p || "";
        updateEstimate();
        $("#prompt").focus();
      }
    };
  });
}

/* ── carte de galerie : ne garder que ce qui VARIE d'une carte à l'autre ─────
   Quatre mentions ont sauté, toutes constantes ou dupliquées :
     · la ligne mono « library · X.png · seamless » redisait le nom de fichier
       déjà écrit juste au-dessus (« d'après X.png »), plus un « seamless »
       identique sur les quinze cartes ;
     · « 8 maps » vaut 8 partout et figure déjà dans le bandeau de titre ;
     · le second terme du score de raccord vaut 0.0 partout (voir seamHtml).
   Ce qui reste et qui varie vraiment : le modèle payant quand il y en a un
   (une matière issue d'une image de la Library n'en a pas), l'invite ou
   l'image d'origine, la définition, la couture rattrapée.
   Le destructif quitte la rangée des actions courantes : il vit dans un coin
   de l'aperçu, et s'arme avant d'agir. */
/* ── LE COMPTE DE MAPS RACONTE UNE SEULE HISTOIRE ───────────────────────────
   Le bandeau affirmait « 8 MAPS PBR » pendant que les douze cartes lisaient
   toutes « 6/8 maps ». Deux chiffres, deux sens, jamais réconciliés : le
   compte de la une n'était atteint nulle part, « 6/8 » était identique partout
   donc n'apprenait rien, et un artiste technique en concluait qu'il recevrait
   six fichiers sur huit promis.

   Notre convention d'honnêteté s'était retournée contre nous. Le fait est
   pourtant simple, et il est bon : LE JEU LIVRÉ EST TOUJOURS DE HUIT
   FICHIERS. Certains sont des champs constants — métal uniforme parce que la
   matière est entièrement diélectrique (ou entièrement métallique), émissive
   noire parce qu'elle n'émet pas. C'est une propriété de LA MATIÈRE, pas une
   map manquante : un moteur attend les huit fichiers, il les reçoit, et il ne
   ferait rien de plus d'un bruit inventé dans le canal métal.

   Le jeton mène donc avec 8 — le même 8 que le bandeau — et qualifie ce qui
   varie d'une matière à l'autre : combien de ces huit sont constantes, et
   lesquelles. « or martelé » en a une (métal plein), la plupart en ont deux. */
function proofCount(m) {
  const st = m.map_stats || {};
  const n = (m.maps || []).length;
  const inf = m.maps_informative != null ? num(m.maps_informative, n)
    : (Object.keys(st).length
        ? Object.keys(st).filter((k) => st[k] && st[k].informative).length : n);
  const audited = Object.keys(st).length > 0 || m.maps_informative != null;
  const flat = Object.keys(st).filter((k) => st[k] && st[k].informative === false);
  return { n: n, inf: inf, flat: flat, cst: Math.max(0, n - inf), audited: audited };
}
/* Le jeton mène avec le compte LIVRÉ, en mono parce que c'est un chiffre
   mesuré — le MÊME 8 que le bandeau — puis NOMME, en graisse discrète, celles
   de ces maps qui sont des champs unis sur cette matière-là. « 6/8 » ne disait
   ni lesquelles ni pourquoi et valait pareil sur les douze cartes ; « 8 maps ·
   2 unies : métal, émission » dit le jeu livré, ce qui varie, et de quoi il
   s'agit. Il prend toute la largeur du pied de carte, au-dessus des actions :
   une ligne de fait, une ligne de commandes. */
const MAP_COURT = { basecolor: "couleur", normal: "normale", roughness: "rugosité",
  metallic: "métal", ao: "occlusion", height: "hauteur", emissive: "émission",
  orm: "ORM", maskmap: "MaskMap" };
function proofChip(m) {
  const c = proofCount(m);
  if (!c.n) return "◧ maps";
  const tete = "◧ " + c.n + " maps";
  if (!c.audited) return tete;
  const noms = c.flat.map((k) => MAP_COURT[k] || mapFr(k)).join(", ");
  return tete + '<i class="cst">' + (c.cst
    ? c.cst + (c.cst > 1 ? " unies : " : " unie : ") + esc(noms)
    : "toutes porteuses") + "</i>";
}
/* La raison de chaque map constante, dans les mots de la mesure : le backend
   écrit déjà « uniforme — métallicité 1.00 partout » ou « éteinte — cette
   matière n'émet pas de lumière ». On les cite plutôt que de les paraphraser. */
function flatReasons(m) {
  const st = m.map_stats || {};
  return proofCount(m).flat.map((k) =>
    mapFr(k) + (st[k] && st[k].note ? " (" + st[k].note + ")" : ""));
}
function proofTitle(m) {
  const c = proofCount(m);
  if (!c.audited) {
    return "Ouvrir la preuve des maps : les images, leurs statistiques et le " +
      "contenu exact du ZIP.";
  }
  const why = flatReasons(m);
  return "Les " + c.n + " maps du jeu sont livrées, toujours." +
    (c.cst
      ? " " + c.cst + " d'entre elles sont des champs constants : " +
        why.join(" ; ") + ". C'est un fait sur CETTE matière, pas une map " +
        "manquante — un moteur attend les " + c.n + " fichiers et les reçoit."
      : " Les " + c.n + " portent de l'information : aucun champ constant.") +
    " Ouvrir la preuve : les images, leurs statistiques, la corrélation entre " +
    "maps et le contenu exact du ZIP.";
}

function cardHtml(m, i) {
  const nm = m.name || m.prompt || m.id;
  const model = ((m.source || {}).model || "").trim();
  const mesh = cardMesh(i || 0);
  /* Le nom du maillage n'est écrit sur la carte que s'il la DISTINGUE des
     autres : quand toutes les cartes portent le même, la rangée de puces du
     rail le dit déjà, une fois. */
  const meshLabel = (MESHES.find((x) => x.id === mesh) || {}).label || mesh;
  const sub = cardSub(m);
  return `<article class="card${m.id === state.sel ? " sel" : ""}" data-id="${esc(m.id)}"
   data-mesh="${esc(mesh)}" tabindex="0" role="button" aria-label="Ouvrir ${esc(nm)}">
  <div class="card-view" data-act="open" title="Ouvrir « ${esc(nm)} » dans l’éditeur">
    <img class="poster" alt="" loading="lazy" decoding="async" src="${esc(posterUrl(m, 256))}">
    <div class="mv-slot"></div>
    ${seamHtml(m, "card-seam")}
    ${(m.res && !resView.uniform && num(m.res, 0) !== resView.base)
      ? `<span class="card-res" title="Cette matière s'écarte de la définition courante de la galerie (${resView.base}²) : elle a été forgée en ${m.res}².">${m.res}²</span>`
      : ""}
    ${state.varied ? `<span class="card-mesh">${esc(meshLabel)}</span>` : ""}
    <button class="card-del" data-act="del" data-arm="0" type="button"
            aria-label="Supprimer ${esc(nm)}"
            title="Supprimer la matière et ses maps — un second clic confirme">✕</button>
    <span class="card-open">Ouvrir</span>
  </div>
  <div class="card-meta">
    <div class="card-top">
      <div class="card-name" title="${esc(nm)}">${esc(nm)}</div>
      ${model ? `<span class="card-model" title="Modèle payant appelé pour l’image de base">${esc(model)}</span>` : ""}
    </div>
    <div class="card-prompt" title="${esc(sub)}">${esc(sub) || "&nbsp;"}</div>
    <div class="card-foot">
      <button class="iact pchip" data-act="proof" title="${esc(proofTitle(m))}">${proofChip(m)}</button>
      <button class="iact" data-act="dup" title="Copie locale et gratuite de cette matière">⧉ Dupliquer</button>
      <button class="iact" data-act="dl" title="Télécharger l’archive ZIP des maps de cette matière — son contenu exact est listé dans la preuve">ZIP</button>
      <button class="iact" data-act="reuse" title="Recharger son invite et ses réglages dans le rail de gauche">↺ Invite</button>
    </div>
  </div>
</article>`;
}

/* Suppression : confirmation EN PLACE, sur le bouton lui-même. Un premier clic
   l'arme (« Confirmer ? », en rouge plein), un second supprime ; il se désarme
   tout seul au bout de quatre secondes ou dès qu'on clique ailleurs. Une boîte
   window.confirm dans une iframe est un objet étranger à l'app, et un simple
   ✕ sans libellé ne prévenait de rien. */
let armTimer = null;
function disarmAll() {
  clearTimeout(armTimer);
  $$('#gallery [data-act="del"][data-arm="1"]').forEach((b) => {
    b.dataset.arm = "0";
    b.textContent = "✕";
  });
}
function armDelete(btn, id) {
  if (btn.dataset.arm === "1") { disarmAll(); remove(id); return; }
  disarmAll();
  btn.dataset.arm = "1";
  btn.textContent = "Supprimer ?";
  armTimer = setTimeout(disarmAll, 4000);
}

function wireCard(m) {
  const el = $(`#gallery .card[data-id="${CSS.escape(m.id)}"]`);
  if (!el) return;
  el.querySelectorAll("[data-act]").forEach((b) => {
    b.onclick = (ev) => {
      ev.stopPropagation();
      ev.preventDefault();
      const a = b.dataset.act;
      if (a !== "del") disarmAll();
      if (a === "open") openMaterial(m.id);
      else if (a === "dup") duplicate(m.id);
      else if (a === "dl") doExport(m.id, true);
      else if (a === "reuse") reusePrompt(m);
      else if (a === "proof") openProof(m.id);
      else if (a === "del") armDelete(b, m.id);
    };
  });
  el.onkeydown = (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); openMaterial(m.id); }
    else if (ev.key === "Delete") {
      ev.preventDefault();
      const b = el.querySelector('[data-act="del"]');
      if (b) armDelete(b, m.id);
    }
  };
  /* poster illisible (map absente) : on laisse le fond de carte, pas de croix
     cassée — la 3D, elle, a son propre repli. */
  const po = el.querySelector("img.poster");
  if (po) po.onerror = () => { po.style.display = "none"; };
}

/* ═══════════════════ PREUVE DES MAPS (au niveau galerie) ═══════════════════
   La revendication « 8 MAPS PBR » et le bouton « ZIP » de chaque carte étaient
   deux affirmations sans pièce jointe : un compte non audité et une archive
   opaque. Et la charge nommée par la critique n'était pas acquittée : rien ne
   permettait de vérifier que les maps 5 à 8 ne sont pas trois réglages de gain
   de plus sur le même champ de hauteur.

   Ce panneau l'acquitte en un geste, sans rien ajouter en permanence sur la
   carte (un seul jeton « n/8 maps » dans le pied de carte l'ouvre) :

     1. les huit PNG RÉELS, servis par /api/materials/<id>/map/<k>.png — on les
        voit côte à côte, à la même taille ;
     2. la mesure de l'API par map (médiane, min–max, 1er centile, et la raison
        écrite quand une map est uniforme) ;
     3. l'AUDIT D'INDÉPENDANCE, calculé ici, dans la page, sur ces mêmes PNG.

   Comment l'audit répond exactement à la charge. « Un réglage de gain de plus
   sur le même champ » veut dire : map = a × hauteur + b. On teste donc cette
   égalité-là, et rien d'autre. Chaque PNG est ramené à sa luminance en 64×64,
   puis on cherche le MEILLEUR couple (a, b) au sens des moindres carrés et on
   mesure ce qu'il RESTE — l'écart résiduel, en niveaux sur 255. Une map qui
   serait la hauteur re-réglée laisserait zéro (au bruit de quantification
   près, moins d'un niveau), quel que soit le gain choisi : c'est précisément
   ce que le résidu ne peut pas maquiller. Le coefficient r est affiché à côté
   parce qu'il situe la parenté, mais le verdict porte sur le résidu.

   Les parentés ATTENDUES sont déclarées, pas dissimulées : la hauteur est la
   luminance lissée de la couleur de base, l'ORM range l'occlusion, la rugosité
   et la métallicité dans ses trois canaux, etc. Chaque ligne porte son lien
   déclaré à côté de sa mesure — un lecteur peut confronter les deux.

   Rien n'est recopié d'une promesse : les images viennent du backend, les
   nombres de l'API ou d'un calcul fait sous les yeux du lecteur. */
const PROOF_N = 64;                       // côté de l'échantillon lu au canvas
const PROOF_GAIN = 0.02;                  // part résiduelle sous laquelle c'est un gain
const proofCache = new Map();             // id/v -> audit
const maniCache = new Map();              // clé de réglages -> bordereau

/* les liens de dérivation que le lab DÉCLARE — écrits à côté de la mesure, pour
   qu'une corrélation élevée ne passe pas pour un aveu et qu'une corrélation
   attendue mais absente saute aux yeux. */
const MAP_KIN = {
  basecolor: "image de base — c'est la source payante, tout en dérive",
  height: "luminance de la couleur de base, lissée",
  normal: "gradient (Sobel cyclique) de la hauteur",
  ao: "écart entre la hauteur et sa version floue",
  roughness: "luminance inversée, biaisée et contrastée",
  metallic: "seuil sur la saturation et la luminance",
  emissive: "couleur de base masquée par un seuil de luminance",
  orm: "empilement : R occlusion, V rugosité, B métal",
};

let proofId = null, proofSeq = 0;

/* luminance ITU-R 601 d'une map, lue dans un canvas — même origine, donc
   canvas non teinté : la mesure porte sur le PNG que le backend sert vraiment. */
function mapLuma(id, kind, v) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      try {
        const c = document.createElement("canvas");
        c.width = PROOF_N; c.height = PROOF_N;
        const g = c.getContext("2d", { willReadFrequently: true });
        g.drawImage(img, 0, 0, PROOF_N, PROOF_N);
        const d = g.getImageData(0, 0, PROOF_N, PROOF_N).data;
        const out = new Float64Array(PROOF_N * PROOF_N);
        for (let i = 0, j = 0; i < d.length; i += 4, j++) {
          out[j] = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
        }
        resolve(out);
      } catch (e) { resolve(null); }
    };
    img.onerror = () => resolve(null);
    img.src = "/api/materials/" + encodeURIComponent(id) + "/map/" +
      encodeURIComponent(kind) + ".png?res=" + PROOF_N + "&v=" + (v || 0);
  });
}

function meanOf(a) {
  let s = 0; for (let i = 0; i < a.length; i++) s += a[i];
  return s / a.length;
}
function sdev(a) {
  const m = meanOf(a);
  let q = 0; for (let i = 0; i < a.length; i++) { const d = a[i] - m; q += d * d; }
  return Math.sqrt(q / a.length);
}
/* r de Pearson : invariant par gain et par décalage — il situe la parenté. */
function pearson(a, b) {
  const ma = meanOf(a), mb = meanOf(b);
  let saa = 0, sbb = 0, sab = 0;
  for (let i = 0; i < a.length; i++) {
    const x = a[i] - ma, y = b[i] - mb;
    saa += x * x; sbb += y * y; sab += x * y;
  }
  if (saa <= 1e-9 || sbb <= 1e-9) return null;      // champ constant : pas de r
  return sab / Math.sqrt(saa * sbb);
}

/* L'AUDIT : pour chaque map, le meilleur ajustement affine sur la référence
   (la hauteur — le champ que la critique soupçonne d'être re-réglé), et ce
   qu'il en reste. Résidu = écart-type de la map × racine(1 - r²), en niveaux
   0–255. Un gain pur donne 0 ; il n'y a pas de valeur de gain qui sauve. */
async function proofAudit(m) {
  const key = m.id + "/" + (m._v || 0);
  if (proofCache.has(key)) return proofCache.get(key);
  const kinds = (m.maps || []).slice();
  const lum = {};
  await Promise.all(kinds.map(async (k) => { lum[k] = await mapLuma(m.id, k, m._v); }));
  const sd = {}, flat = {};
  kinds.forEach((k) => {
    sd[k] = lum[k] ? sdev(lum[k]) : 0;
    flat[k] = !lum[k] || sd[k] < 0.5;         // champ constant : rien à ajuster
  });
  /* référence = la hauteur ; à défaut (map absente ou plate) la couleur de
     base, et le panneau le dit en toutes lettres. */
  let ref = kinds.indexOf("height") >= 0 && !flat.height ? "height"
          : (kinds.indexOf("basecolor") >= 0 && !flat.basecolor ? "basecolor" : null);
  const rows = kinds.map((k) => {
    const row = { k: k, flat: flat[k], sd: sd[k], r: null, resid: null, self: k === ref };
    if (!ref || flat[k] || k === ref) return row;
    const r = pearson(lum[k], lum[ref]);
    if (r == null) return row;
    row.r = Math.abs(r);
    /* `share` = la part de sa PROPRE variation qu'aucun (a, b) n'explique.
       Le résidu en niveaux seul favoriserait les maps presque plates : une map
       quasi noire laisse peu de niveaux quoi qu'il arrive. La part relative,
       elle, ne dépend pas de l'amplitude — et un gain la met à zéro. */
    row.share = Math.sqrt(Math.max(0, 1 - r * r));
    row.resid = sd[k] * row.share;
    return row;
  });
  const tested = rows.filter((x) => x.share != null);
  /* La map la plus proche de la référence est, trivialement, l'image SOURCE
     dont la hauteur est tirée. La citer comme « la plus proche » répondrait à
     côté : la charge portait sur les maps DÉRIVÉES. On sépare donc les deux —
     la plus proche des dérivées d'un côté, la source de l'autre, chacune avec
     son nombre. */
  const derived = tested.filter((x) => x.k !== "basecolor");
  const worst = (derived.length ? derived : tested).length
    ? (derived.length ? derived : tested).reduce((a, b) => (a.share <= b.share ? a : b))
    : null;
  const src = tested.find((x) => x.k === "basecolor") || null;
  const out = { ref: ref, rows: rows, worst: worst, src: src, n: kinds.length,
                tested: tested.length,
                flatN: kinds.filter((k) => flat[k]).length };
  proofCache.set(key, out);
  return out;
}

/* bordereau « tel qu'il partirait si on cliquait ZIP sur cette carte » :
   convention standard, définition native, 8 bits — exactement ce que
   `cardExportUrl` demande. */
function cardManifestQuery(m) {
  return { format: "zip", naming: "standard", res: String(num(m.res, 2048)),
           bits: "8", mesh: state.mesh || "sphere" };
}
function cardExportUrl(m, manifest) {
  const q = new URLSearchParams(cardManifestQuery(m));
  return "/materials/" + encodeURIComponent(m.id) +
    (manifest ? "/export/manifest?" : "/export?") + q.toString();
}
async function cardManifest(m) {
  const key = m.id + "?" + new URLSearchParams(cardManifestQuery(m)).toString();
  if (maniCache.has(key)) return maniCache.get(key);
  const d = await api.get(cardExportUrl(m, true));
  maniCache.set(key, d);
  return d;
}

/* La corrélation avec la luminance de la couleur de base est LE critère : au
   delà de |r| = 0,90, la map ne fait que redire l'image source. Le backend la
   publie pour les huit maps (`map_stats[k].corr_lum` / `.dependent`) mais
   l'écran ne la montrait que sur les maps déjà signalées — c'est-à-dire qu'il
   ne disait rien là où le lecteur doit pouvoir vérifier que c'est BAS. Chaque
   vignette porte donc maintenant son r et son verdict. */
function proofStatLine(st, k) {
  if (!st) return "mesure non publiée par l'API";
  const s = "médiane " + num(st.median, 0) + " · min–max " + num(st.min, 0) + "–" +
    num(st.max, 0) + " · 1 % à " + num(st.p1, 0);
  if (k === "basecolor") return s + " · référence de la corrélation";
  // une constante ne corrèle avec rien : annoncer « r +0.000 — indépendante »
  // sur un champ uni serait un compliment vide.
  if (st.informative === false) return s + " · champ constant";
  if (st.corr_lum == null) return s;
  const r = num(st.corr_lum, 0);
  return s + " · r(couleur de base) " + (r >= 0 ? "+" : "") + fmt(r, 3) +
    (st.dependent ? " — dépendante, pas d'information indépendante"
                  : " — indépendante");
}
function mapLabel(k) { return (MAPS.find((x) => x.k === k) || {}).label || k; }
/* les vignettes portent le nom d'usage des maps (Base Color, Height…), qui est
   anglais parce que c'est celui des moteurs ; la PROSE, elle, est française :
   « la hauteur », pas « la height ». */
const MAP_FR = { basecolor: "couleur de base", normal: "normale", roughness: "rugosité",
  metallic: "métallicité", ao: "occlusion", height: "hauteur", emissive: "émission",
  orm: "ORM", maskmap: "MaskMap", smoothness: "lissage", opacity: "opacité",
  displacement: "déplacement" };
function mapFr(k) { return MAP_FR[k] || mapLabel(k); }

async function openProof(id) {
  const m = matById(id);
  if (!m) return;
  proofId = id;
  const seq = ++proofSeq;
  $("#proofBack").classList.remove("hidden");
  $("#proof").classList.remove("hidden");
  $("#proofTitle").textContent = "Preuve des maps — " + (m.name || m.id);
  $("#proofBody").innerHTML = '<p class="proof-wait">Lecture des PNG servis par le backend, ' +
    "ajustement affine sur la hauteur…</p>";
  $("#proofClose").focus();

  const mstats = m.map_stats || {};
  let au = null, mani = null, maniErr = "";
  try { au = await proofAudit(m); } catch (e) { au = null; }
  try { mani = await cardManifest(m); } catch (e) { maniErr = e.message; }
  if (seq !== proofSeq) return;

  const kinds = (m.maps || []).slice();
  const ninf = m.maps_informative != null ? num(m.maps_informative, kinds.length)
    : Object.keys(mstats).filter((k) => mstats[k] && mstats[k].informative).length;

  // ── 1. les huit images réelles, avec la mesure de l'API dessous ──
  const cells = kinds.map((k) => {
    const st = mstats[k] || null;
    const row = au ? au.rows.find((x) => x.k === k) : null;
    const url = "/api/materials/" + encodeURIComponent(m.id) + "/map/" +
      encodeURIComponent(k) + ".png?res=192&v=" + (m._v || 0);
    return '<figure class="pcell' + (row && row.flat ? " flat" : "") + '">' +
      '<img src="' + esc(url) + '" alt="' + esc(mapLabel(k)) + '" loading="lazy">' +
      "<figcaption><b>" + esc(mapLabel(k)) + "</b>" +
      '<i class="pst">' + esc(proofStatLine(st, k)) + "</i>" +
      (st && st.note ? '<i class="pnote">' + esc(st.note) + "</i>" : "") +
      "</figcaption></figure>";
  }).join("");

  // ── 2. l'audit d'indépendance, ligne par ligne ──
  const refFr = au && au.ref ? mapFr(au.ref) : "";
  const tab = au && au.ref
    ? '<table class="ptab audit"><thead><tr><th>Map</th><th>Lien déclaré</th>' +
      "<th>r avec la " + esc(refFr) + "</th>" +
      "<th>Part inexpliquée</th></tr></thead><tbody>" +
      au.rows.map((row) => {
        const gain = row.share != null && row.share < PROOF_GAIN;
        const val = row.self ? "référence"
          : row.flat ? "champ constant"
          : row.share == null ? "—"
          : fmt(row.share * 100, 1) + " % · " + fmt(row.resid, 1) + " niv.";
        return "<tr" + (gain ? ' class="bad"' : "") + "><td>" + esc(mapLabel(row.k)) + "</td>" +
          '<td class="kin">' + esc(MAP_KIN[row.k] || "dérivée localement") + "</td>" +
          '<td class="num">' + (row.r == null ? "—" : fmt(row.r, 3)) + "</td>" +
          '<td class="num' + (gain ? " bad" : "") + '">' + esc(val) + "</td></tr>";
      }).join("") + "</tbody></table>"
    : "";

  const gains = au ? au.rows.filter((x) => x.share != null && x.share < PROOF_GAIN) : [];
  const testedTxt = au
    ? au.tested + " des " + au.n + " maps sont passées au test ; la " + esc(refFr) +
      " est la référence" +
      (au.flatN ? ", et " + au.flatN + " sont des champs constants (la raison est écrite " +
        "sous leur image)" : "") + "."
    : "";
  const verdict = !au || !au.ref
    ? "Audit impossible : la hauteur n'a pas pu être lue dans cette page."
    : gains.length
      ? "⚠ " + gains.map((x) => mapLabel(x.k)).join(", ") + " : le meilleur ajustement " +
        "affine sur la " + esc(refFr) + " ne laisse rien — ces maps SONT la même image " +
        "re-réglée. " + testedTxt
      : "Aucune map n'est la " + esc(refFr) + " re-réglée. La plus proche des maps " +
        "dérivées, " + esc(mapLabel(au.worst.k)) + ", garde " +
        fmt(au.worst.share * 100, 1) + " % de sa propre variation qu'aucun couple (a, b) " +
        "n'explique — " + fmt(au.worst.resid, 1) + " niveaux sur 255. Un simple gain, lui, " +
        "tomberait à 0,0 %, quel que soit le facteur." +
        (au.src ? " La couleur de base est le seul cas serré (" +
          fmt(au.src.share * 100, 1) + " %), et c'est attendu : c'est l'image source dont " +
          "la " + esc(refFr) + " est tirée — le lien est déclaré sur sa ligne." : "") +
        " " + testedTxt;

  // ── 3. le contenu exact de l'archive ──
  const zip = mani
    ? '<table class="ptab"><tbody>' +
      (mani.entries || []).map((e) =>
        '<tr' + (e.selected === false ? ' class="off"' : "") + "><td>" + esc(e.name) + "</td>" +
        "<td>" + esc(e.channels) + " " + num(e.bits, 8) + " bits</td>" +
        '<td class="num">' + (e.exact ? "" : "≈ ") + fmtBytes(e.bytes) + "</td>" +
        "<td>" + esc(manifestRole(e)) +
          '<i class="mch">' + esc(chanOrder(e)) + "</i>" +
          // la raison du « ≈ » voyage AVEC le chiffre, ici comme dans le
          // bordereau de l'inspecteur : même règle, même mot, deux écrans.
          (e.exact || !e.weigh_tag ? ""
            : '<i class="wtag" title="' + esc(e.weigh || "") + '">≈ ' +
              esc(e.weigh_tag) + "</i>") +
          "</td></tr>").join("") +
      (mani.extras || []).map((e) =>
        "<tr><td>" + esc(e.name) + "</td><td>—</td>" +
        '<td class="num">' + (e.exact ? "" : "≈ ") + fmtBytes(e.bytes) + "</td>" +
        "<td>" + esc(extraRole(e.name)) + "</td></tr>").join("") +
      "</tbody></table>" +
      '<p class="proof-note">' + esc(mani.weigh_rule || WEIGH_RULE_FALLBACK) + "</p>" +
      '<p class="proof-note">Archive <b>' + esc(mani.archive) + "</b> — " +
      ((mani.entries || []).filter((e) => e.selected !== false).length + (mani.extras || []).length) +
      " fichiers cochés par défaut, " + (mani.exact ? "" : "≈ ") + fmtBytes(mani.total_bytes) +
      ". Les lignes grisées ne partent pas par défaut ; le bloc Export de " +
      "l'inspecteur permet de les cocher, et de changer de convention, de " +
      "définition et de profondeur.</p>"
    : '<p class="proof-note">Bordereau indisponible : ' + esc(maniErr || "—") + "</p>";

  if (seq !== proofSeq) return;
  $("#proofBody").innerHTML =
    '<p class="proof-lead"><b>Les ' + kinds.length + " maps du jeu sont " +
      "livrées</b> — c'est le compte du bandeau, et il ne bouge pas d'une " +
      "matière à l'autre. " +
      (kinds.length - ninf
        ? "Sur celle-ci, " + (kinds.length - ninf) + " sont des champs " +
          "constants : " + esc(flatReasons(m).join(" ; ")) + ". Fait sur la " +
          "matière, pas map manquante — la mesure est sous chaque image."
        : "Les " + kinds.length + " portent de l'information : aucun champ " +
          "constant sur celle-ci.") +
      " Les images ci-dessous sont les PNG servis par le backend, pas des " +
      "aperçus reconstitués.</p>" +
    '<div class="pgrid">' + cells + "</div>" +
    '<h4 class="proof-h">Ces maps sont-elles la même, re-réglée ? — le test</h4>' +
    '<p class="proof-sub">« Un réglage de gain de plus sur le même champ » s’écrit ' +
      "<b>map = a × " + esc(refFr) + " + b</b>. On cherche donc le meilleur couple " +
      "(a, b) au sens des moindres carrés, sur la luminance de chaque PNG en " +
      PROOF_N + "×" + PROOF_N + ", et on mesure ce qu'il RESTE — en part de la variation " +
      "propre de la map, pour qu'une map de faible amplitude ne passe pas le test par " +
      "sa seule platitude. Un gain, quel qu'il soit, ne laisse rien.</p>" +
    tab +
    '<p class="proof-verdict' + (gains.length ? " bad" : "") + '">' + verdict + "</p>" +
    '<h4 class="proof-h">Ce que contient le ZIP de cette carte</h4>' +
    '<p class="proof-sub">Convention standard · ' + num(m.res, 2048) + "² · 8 bits — " +
      "les réglages qu'applique le bouton ZIP de la carte.</p>" + zip;

  const dl = document.createElement("button");
  dl.className = "btn strong wide";
  dl.textContent = "⬇ Télécharger ce ZIP";
  dl.onclick = () => doExport(m.id, true);
  $("#proofBody").appendChild(dl);
}

function closeProof() {
  proofSeq++;
  proofId = null;
  $("#proofBack").classList.add("hidden");
  $("#proof").classList.add("hidden");
}

function reusePrompt(m) {
  $("#prompt").value = m.prompt || "";
  if (m.res) setRes(m.res);
  const sm = m.source && m.source.model;
  if (sm && state.models.some((x) => x.id === sm)) { state.model = sm; $("#model").value = sm; }
  $("#seamless").checked = !!m.seamless;
  updateEstimate();
  $("#prompt").focus();
  toast("Invite réutilisée : « " + (m.prompt || "") + " »");
}

async function duplicate(id) {
  try {
    const d = await api.post("/materials/" + encodeURIComponent(id) + "/duplicate");
    if (d && d.material) {
      upsert(d.material);
      renderGallery();
      flashCard(d.material.id);
      toast("Matière dupliquée (gratuit, local) : « " + (d.material.name || d.material.id) + " ».");
    } else await loadMaterials();
  } catch (e) { toast("Duplication impossible : " + e.message, true); }
}

/* amène une carte sous les yeux et la signale — une copie qui apparaît hors
   écran, c'est une action qui n'a l'air de rien faire. */
function flashCard(id) {
  const card = $(`#gallery .card[data-id="${CSS.escape(id)}"]`);
  if (!card) return;
  card.scrollIntoView({ block: "nearest" });
  card.classList.add("just");
  setTimeout(() => card.classList.remove("just"), 1400);
}

async function remove(id) {
  try {
    await api.del("/materials/" + encodeURIComponent(id));
    state.materials = state.materials.filter((x) => x.id !== id);
    if (state.sel === id) closeEditor();
    renderGallery();
    toast("Matière supprimée.");
  } catch (e) { toast("Suppression impossible : " + e.message, true); }
}

/* ───────────────────────── éditeur ─────────────────────────
   Ouvrir une matière n'est pas un aller simple : la position de défilement de
   la galerie est mémorisée, l'URL porte la matière ouverte (#m/mat_xxxx — un
   rechargement ou un partage de lien rouvre la même), et le retour remet la
   carte sous les yeux, surlignée. */
function openMaterial(id, opts) {
  const m = matById(id);
  if (!m) return;
  if (state.view === "gallery") state.scroll = $("#gallery").scrollTop || 0;
  state.sel = id;
  state.view = "editor";
  $("#gallery").classList.add("hidden");
  $("#galEmpty").classList.add("hidden");
  $("#viewport").classList.remove("hidden");
  $("#backGal").classList.remove("hidden");
  $("#colsWrap").classList.add("hidden");
  $("#galSort").classList.add("hidden");
  $("#galSearch").classList.add("hidden");
  /* Les commandes d'aperçu déménagent DANS le viewport : elles ne restent pas
     en double dans le rail, et la place du rail revient aux propriétés. */
  $("#grpView").classList.add("hidden");
  renderGallery();                    // libère les scènes 3D des cartes
  setViewportSrc(m);
  applyEnvToViewers();
  $("#puck").classList.toggle("hidden", !state.pointLight);
  fillInspector(m);
  updateEditorHead(m);
  if (!(opts && opts.silent)) setHash("m/" + id);
}

/* lien profond : #m/mat_xxxx ouvre la matière, # (vide) revient à la galerie */
let hashLock = false;
function setHash(h) {
  hashLock = true;
  try { location.hash = h; } catch (e) { /* noop */ }
  setTimeout(() => { hashLock = false; }, 0);
}
function onHashChange() {
  if (hashLock) return;
  const h = (location.hash || "").replace(/^#\/?/, "");
  const mm = /^m\/(mat_[0-9a-f]{8})$/.exec(h);
  if (mm) { if (state.sel !== mm[1]) openMaterial(mm[1], { silent: true }); }
  else if (state.view === "editor") closeEditor({ silent: true });
}

function updateEditorHead(m) {
  const seam = $("#edSeam"), meta = $("#edMeta");
  if (state.view !== "editor" || !m) { seam.classList.add("hidden"); meta.classList.add("hidden"); return; }
  /* la même lecture qu'en galerie, au mot près : avant / après étiquetés */
  const h = seamHtml(m, "edseam");
  seam.classList.toggle("hidden", !h);
  seam.innerHTML = h;
  /* Une seule notation pour les dimensions (2048², comme sur les cartes et sur
     le segment de définition), et AUCUN emplacement vide : une matière issue de
     la Library n'a pas de modèle, la mention disparaît au lieu de laisser
     traîner un « · — ». Le compte de maps n'est pas répété ici : il est écrit
     sur le groupe « Maps de texture » de l'inspecteur. */
  const parts = [m.res ? m.res + "²" : null, sourceLabel(m)].filter(
    (x) => x && x !== "—");
  meta.classList.toggle("hidden", !parts.length);
  meta.textContent = parts.join(" · ");
  meta.title = "Définition de cette matière, fixée à sa forge. Le segment " +
    "« Définition source » du rail gauche règle la prochaine ; « Taille à " +
    "l'export », dans l'inspecteur, ne touche qu'au livrable.";
}

function closeEditor(opts) {
  const back = state.sel;
  state.view = "gallery";
  state.sel = null;
  const mv = $("#mv");
  if (mv) { try { mv.src = ""; } catch (e) { /* noop */ } }
  $("#viewport").classList.add("hidden");
  $("#backGal").classList.add("hidden");
  $("#colsWrap").classList.remove("hidden");
  $("#galSort").classList.remove("hidden");
  $("#galSearch").classList.remove("hidden");
  $("#grpView").classList.remove("hidden");
  $("#inspMat").classList.add("hidden");
  $("#inspEmpty").classList.remove("hidden");
  $("#inspTitle").textContent = "Aperçu";
  $("#edSeam").classList.add("hidden");
  $("#edMeta").classList.add("hidden");
  renderGallery();
  /* on retrouve la galerie là où on l'avait laissée, et la carte qui revient
     de l'éditeur se signale une seconde — sinon on la cherche des yeux. */
  const g = $("#gallery");
  g.scrollTop = state.scroll || 0;
  if (back) {
    const card = $(`#gallery .card[data-id="${CSS.escape(back)}"]`);
    if (card) {
      const r = card.getBoundingClientRect(), gr = g.getBoundingClientRect();
      if (r.top < gr.top || r.bottom > gr.bottom) card.scrollIntoView({ block: "center" });
      card.classList.add("just");
      setTimeout(() => card.classList.remove("just"), 1400);
    }
  }
  if (!(opts && opts.silent)) setHash("");
}

/* ───────────────────────── inspecteur ─────────────────────────
   Une propriété = UNE ligne, quatre colonnes fixes et partagées par tous les
   groupes : « ? » · libellé · curseur · valeur. Les nombres tombent donc dans
   une colonne unique, en chiffres tabulaires ; la valeur est un champ, pas une
   étiquette (on tape 0.37 au lieu de viser au pixel) ; la piste porte un repère
   au défaut et un double-clic sur le libellé y revient. Une valeur qui a quitté
   son défaut passe en doré, à la ligne comme dans le résumé du groupe replié. */

/* résumés affichés sur les groupes REPLIÉS : un groupe fermé reste lisible */
/* ── résumés des groupes repliés : ne dire QUE ce qui porte quelque chose ────
   Quatre résumés sur cinq disaient la même chose en quatre mots différents —
   « aucun », « aucun », « éteinte », « opaque » : quatre lectures pour
   apprendre quatre fois rien. Un groupe resté à sa valeur neutre ne mérite pas
   une phrase à lui : il reçoit UN traitement commun et discret (titre en gris,
   un seul tiret), qui se saute d'un seul coup d'oeil pour les quatre. Le détail
   chiffré est réservé aux groupes qui portent réellement une valeur. */
const DIGEST = {
  base: (p) => fmt(p.metallic) + " mét · " + fmt(p.roughness) + " rug",
  surface: (p) => "relief ×" + fmt(p.normal_scale, 1) + " · répétition ×" + trim0(fmt(p.tiling, 2)),
  emission: (p) => "×" + fmt(p.emissive_strength),
  clearcoat: (p) => fmt(p.clearcoat) + " · rug " + fmt(p.clearcoat_roughness),
  sheen: (p) => "duvet " + fmt(p.sheen),
  transmission: (p) => fmt(p.transmission) + " · IOR " + fmt(p.ior),
};

/* pose sur un <details> le résumé qui convient.
     texte  → le résumé chiffré (le groupe porte quelque chose)
     null   → le tiret commun + classe `off` (groupe resté neutre)
     ""     → aucun résumé, mais le groupe reste allumé (il porte déjà une
              pastille de modifications qui dirait la même chose)          */
function setGrpDigest(d, dig) {
  const neutral = dig === null || dig === undefined;
  d.classList.toggle("off", neutral);
  let b = d.querySelector(".grp-dig");
  if (!neutral && !dig) { if (b) b.remove(); return; }
  if (!b) {
    b = document.createElement("b");
    b.className = "grp-dig";
    const sum = d.querySelector("summary");
    sum.insertBefore(b, sum.querySelector(".grp-mod") || null);
  }
  b.textContent = neutral ? "—" : dig;
  b.title = neutral ? "Groupe resté à ses valeurs par défaut." : "";
}
function trim0(s) { return String(s).indexOf(".") < 0 ? s : String(s).replace(/\.?0+$/, ""); }

function sameVal(v, d) {
  if (typeof d === "number") return Math.abs(num(v, d) - d) < 1e-6;
  if (typeof d === "boolean") return !!v === d;
  return String(v == null ? d : v).toLowerCase() === String(d).toLowerCase();
}
/* nombre de valeurs qui ont quitté leur défaut, sur un jeu de lignes donné */
function modCount(rows, vals, defs) {
  return rows.reduce((n, r) => n + (sameVal(vals[r.k], defs[r.k]) ? 0 : 1), 0);
}

function propRow(row, val, def, onChange) {
  const dec = row.dec == null ? 2 : row.dec;
  const wrap = document.createElement("div");
  wrap.className = "prop t-" + row.t;
  wrap.dataset.k = row.k;
  wrap.dataset.q = ((row.l || "") + " " + row.k + " " + (row.h || "")).toLowerCase();

  const line = document.createElement("div");
  line.className = "prop-line";
  line.innerHTML =
    '<button class="qmark" type="button" aria-label="Aide">?</button>' +
    '<span class="prop-l"></span>' +
    '<span class="prop-ctl"></span>';
  wrap.appendChild(line);

  const lab = line.querySelector(".prop-l");
  lab.textContent = row.l;
  const ctl = line.querySelector(".prop-ctl");

  // aide contextuelle : une par propriété, sans exception
  const help = document.createElement("div");
  help.className = "prop-help hidden";
  help.textContent = row.h || "";
  wrap.appendChild(help);
  const q = line.querySelector(".qmark");
  q.title = "Ce que fait « " + row.l + " »";
  q.onclick = (e) => {
    e.preventDefault();
    const on = !help.classList.toggle("hidden");
    q.classList.toggle("on", on);
  };

  const mark = (v) => wrap.classList.toggle("mod", !sameVal(v, def));

  if (row.t === "range") {
    ctl.classList.add("rng");
    const span = (row.max - row.min) || 1;
    ctl.style.setProperty("--dp", clamp((num(def, row.min) - row.min) / span, 0, 1));
    const input = document.createElement("input");
    input.type = "range"; input.min = row.min; input.max = row.max; input.step = row.step;
    input.value = num(val, def);
    input.title = "défaut " + fmt(def, dec) + " — double-clic sur le libellé pour y revenir";
    ctl.appendChild(input);

    const cell = document.createElement("span");
    cell.className = "prop-num";
    const numv = document.createElement("input");
    numv.className = "numv"; numv.type = "text"; numv.spellcheck = false;
    numv.value = fmt(input.value, dec);
    numv.title = "Valeur exacte : tape-la, ou règle-la avec ↑ ↓";
    cell.appendChild(numv);
    // la colonne d'unite est TOUJOURS reservee, meme vide : sans cela les
    // lignes qui portent « px » ou « ° » decalaient leurs chiffres d'un cran
    // et la colonne de nombres cessait d'etre une colonne.
    const u = document.createElement("i");
    u.className = "unit"; u.textContent = row.u || "";
    cell.appendChild(u);
    line.appendChild(cell);

    const set = (v, live) => {
      const n = clamp(num(v, def), row.min, row.max);
      input.value = n;
      numv.value = fmt(n, dec);
      mark(n);
      onChange(Number(n), !!live);
    };
    input.oninput = () => { numv.value = fmt(input.value, dec); mark(input.value); onChange(Number(input.value), true); };
    input.onchange = () => set(input.value, false);
    numv.onchange = () => set(numv.value.replace(",", "."), false);
    numv.onkeydown = (e) => {
      if (e.key === "Enter") { numv.blur(); return; }
      const d = e.key === "ArrowUp" ? 1 : e.key === "ArrowDown" ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      set(num(numv.value.replace(",", "."), def) + d * row.step * (e.shiftKey ? 10 : 1), false);
    };
    lab.title = row.l + " — double-clic : retour au défaut (" + fmt(def, dec) + (row.u || "") + ")";
    lab.ondblclick = () => set(def, false);
    mark(input.value);
    return wrap;
  }

  if (row.t === "color") {
    const sw = document.createElement("input");
    sw.type = "color"; sw.className = "swatch";
    sw.value = /^#[0-9a-f]{6}$/i.test(String(val)) ? String(val) : String(def);
    ctl.appendChild(sw);
    const hex = document.createElement("input");
    hex.className = "hexv"; hex.type = "text"; hex.spellcheck = false;
    hex.value = sw.value.toLowerCase();
    hex.title = "Hexadécimal — collable depuis n’importe quelle charte";
    line.appendChild(hex);
    const set = (v, live) => {
      if (!/^#[0-9a-f]{6}$/i.test(String(v))) return;
      sw.value = v; hex.value = String(v).toLowerCase();
      mark(v);
      onChange(String(v), !!live);
    };
    sw.oninput = () => { hex.value = sw.value.toLowerCase(); mark(sw.value); onChange(sw.value, true); };
    sw.onchange = () => set(sw.value, false);
    hex.onchange = () => set(hex.value.trim().replace(/^#?/, "#"), false);
    lab.title = row.l + " — double-clic : retour au défaut (" + def + ")";
    lab.ondblclick = () => set(def, false);
    mark(sw.value);
    return wrap;
  }

  if (row.t === "check") {
    const sw = document.createElement("label");
    sw.className = "sw";
    const input = document.createElement("input");
    input.type = "checkbox"; input.checked = !!val;
    sw.appendChild(input);
    sw.appendChild(document.createElement("i"));
    ctl.appendChild(sw);
    input.onchange = () => { mark(input.checked); onChange(input.checked, false); };
    lab.title = row.l;
    mark(input.checked);
    return wrap;
  }

  const sel = document.createElement("select");
  sel.innerHTML = (row.opts || []).map(([v, l]) =>
    `<option value="${esc(v)}"${String(val) === v ? " selected" : ""}>${esc(l)}</option>`).join("");
  sel.onchange = () => { mark(sel.value); onChange(sel.value, false); };
  ctl.appendChild(sel);
  lab.title = row.l;
  mark(sel.value);
  return wrap;
}

/* en-tête d'un groupe : chevron + titre + résumé (replié) + pastille de
   modifications. `dig` peut être nul (Maps, Dérivation portent leur compte). */
function grpSummary(title, dig, mods) {
  return '<summary><i class="chev"></i><span class="grp-t">' + esc(title) + "</span>" +
    (dig ? '<b class="grp-dig">' + esc(dig) + "</b>" : "") +
    (mods ? '<em class="grp-mod" title="' + mods + ' réglage(s) hors défaut">' + mods + "</em>" : "") +
    "</summary>";
}

function fillInspector(m) {
  $("#inspEmpty").classList.add("hidden");
  $("#inspMat").classList.remove("hidden");
  $("#inspTitle").textContent = "Inspecteur";
  $("#matName").value = m.name || "";

  const props = Object.assign({}, DEFAULT_PROPS, m.props || {});
  const derive = Object.assign({}, DEFAULT_DERIVE, m.derive || {});
  const host = $("#groups");
  const openState = {};
  host.querySelectorAll("details.grp").forEach((d) => { openState[d.dataset.g] = d.open; });
  host.innerHTML = "";

  GROUPS.forEach((g) => {
    const d = document.createElement("details");
    d.className = "grp"; d.dataset.g = g.id;
    d.open = openState[g.id] != null ? openState[g.id] : !!g.open;
    const mods = modCount(g.rows, props, DEFAULT_PROPS);
    d.innerHTML = grpSummary(g.label, "", mods);
    setGrpDigest(d, mods ? (DIGEST[g.id] ? DIGEST[g.id](props) : "") : null);
    const body = document.createElement("div");
    body.className = "grp-body";
    g.rows.forEach((row) => {
      body.appendChild(propRow(row, props[row.k], DEFAULT_PROPS[row.k],
        (v, livePass) => setProp(row, v, livePass)));
    });
    d.appendChild(body);
    host.appendChild(d);
  });

  // ── maps de texture ──
  const nmaps = (m.maps || []).length;
  /* « 8/8 remplies » était vrai au sens du fichier et faux au sens de l'usage :
     sur une matière diélectrique, metallic est un PNG noir uni et emissive un
     PNG noir uni — deux fichiers qui ne portent aucune information. L'API les
     compte pour nous (`map_stats[k].informative`, `maps_informative`) ; le
     résumé annonce donc les maps PORTEUSES, et chaque vignette éteinte dit en
     toutes lettres pourquoi elle est uniforme. */
  const mstats = m.map_stats || {};
  const ninf = m.maps_informative != null ? num(m.maps_informative, nmaps)
    : Object.keys(mstats).filter((k) => mstats[k] && mstats[k].informative).length;
  const dm = document.createElement("details");
  dm.className = "grp"; dm.dataset.g = "maps";
  dm.open = openState.maps != null ? openState.maps : true;
  /* MÊME HISTOIRE QUE LE BANDEAU ET QUE LES CARTES : le compte mène avec le
     jeu LIVRÉ (le 8 du bandeau), et ce qui varie d'une matière à l'autre —
     combien de ces maps sont des champs constants — vient après, qualifié.
     « 6/8 porteuses » se lisait comme un échec permanent : deux fichiers
     semblaient manquer alors que les huit partent toujours. */
  const ncst = Math.max(0, nmaps - ninf);
  dm.innerHTML = grpSummary("Maps de texture",
    (Object.keys(mstats).length
      ? nmaps + " livrées" + (ncst ? " · " + ncst + " constante" +
        (ncst > 1 ? "s" : "") : "")
      : nmaps + " générées"), 0);
  const mb = document.createElement("div");
  mb.className = "grp-body";
  const grid = document.createElement("div");
  grid.className = "mapgrid";
  grid.innerHTML = MAPS.map((mp) => {
    const has = (m.maps || []).indexOf(mp.k) >= 0;
    const st = mstats[mp.k] || null;
    const flat = has && st && st.informative === false;
    const url = "/api/materials/" + encodeURIComponent(m.id) + "/map/" + mp.k + ".png?res=256&v=" + (m._v || 0);
    const tip = esc(mp.label) + (has
      ? (st ? " — moyenne " + fmt(st.mean, 1) + "/255" +
              (st.channel ? " (" + st.channel + ")" : "") +
              ", min " + num(st.min, 0) + ", max " + num(st.max, 0) +
              (st.note ? " · " + st.note : "") + ". " : " — ") +
        "Cliquer pour télécharger cette map en pleine résolution"
      : " — non générée");
    return `<a class="mapcell${has ? "" : " off"}${flat ? " flat" : ""}" href="${has ? esc(url.replace("res=256", "res=" + (m.res || 2048))) : "#"}"
      ${has ? 'download="' + esc((m.name || m.id).replace(/[^\w.-]+/g, "_")) + "_" + mp.k + '.png"' : ""}
      title="${esc(tip)}">
      <img src="${has ? esc(url) : ""}" alt="${esc(mp.label)}"><b>${esc(mp.label)}</b>
      ${flat ? '<i class="mapflat">' + esc(flatShort(mp.k, st)) + "</i>" : ""}</a>`;
  }).join("");
  mb.appendChild(grid);
  const note = document.createElement("p");
  note.className = "grp-note";
  // l'ORM est jaune vif parce que c'est une map PACKÉE : on le dit, pour que la
  // couleur se lise comme un encodage de canaux et non comme un accent d'écran.
  const cstWhy = flatReasons(m);
  note.innerHTML = "height et ORM en plus des six usuelles ; les <b>" + nmaps +
    "</b> partent dans l'archive, toujours. " +
    (cstWhy.length
      ? "Sur cette matière, " + (cstWhy.length > 1 ? "les " + cstWhy.length +
          " maps suivantes sont des champs constants" : "une map est un champ " +
          "constant") + " : " + esc(cstWhy.join(" ; ")) + ". Un moteur attend " +
        "ces fichiers et les reçoit — c'est la matière qui est unie là, pas la " +
        "map qui manque. "
      : "Les " + nmaps + " portent de l'information sur cette matière. ") +
    "L'ORM empile trois maps dans un seul fichier — <b>R</b> occlusion, " +
    "<b>V</b> rugosité, <b>B</b> métal — d'où sa couleur. Clique une map : son " +
    "PNG pleine résolution se télécharge.";
  mb.appendChild(note);
  dm.appendChild(mb);
  host.appendChild(dm);

  // ── réglages de dérivation ──
  const dmod = modCount(DERIVE_ROWS, derive, DEFAULT_DERIVE);
  const dd = document.createElement("details");
  dd.className = "grp"; dd.dataset.g = "derive";
  dd.open = openState.derive != null ? openState.derive : false;
  /* « local · gratuit » était imprimé là en permanence, identique sur toutes
     les matières : une constante déguisée en résumé. La promesse est tenue par
     la note du corps du groupe ; l'en-tête ne garde que ce qui varie. */
  dd.innerHTML = grpSummary("Réglages de dérivation", "", dmod);
  setGrpDigest(dd, dmod ? "" : null);
  const db = document.createElement("div");
  db.className = "grp-body";
  const dnote = document.createElement("p");
  dnote.className = "grp-note";
  dnote.innerHTML = "Calcul des maps secondaires depuis la couleur de base, en convolutions " +
    "<b>cycliques</b> : le raccord mesuré reste intact. Recalcul local et <b>gratuit</b>.";
  db.appendChild(dnote);
  DERIVE_ROWS.forEach((row) => {
    db.appendChild(propRow(row, derive[row.k], DEFAULT_DERIVE[row.k], (v) => setDerive(row, v)));
  });
  const rb = document.createElement("button");
  rb.className = "btn primary wide";
  rb.id = "btnDerive";
  rb.textContent = "↻ Re-dériver les maps";
  rb.onclick = rederive;
  db.appendChild(rb);
  dd.appendChild(db);
  host.appendChild(dd);

  applyPropFilter();
  refreshMods();
  renderExportMaps(m);
  applyAllLive(m);
}

/* ── barre d'outils : filtre, aide globale, plier/déplier, compte modifié ── */
function applyPropFilter() {
  const host = $("#groups");
  const q = (state.propQ || "").trim().toLowerCase();
  if (q && host.dataset.filtering !== "1") {
    host.dataset.filtering = "1";
    host.querySelectorAll("details.grp").forEach((d) => { d.dataset.prev = d.open ? "1" : "0"; });
  }
  host.querySelectorAll("details.grp").forEach((d) => {
    let n = 0;
    d.querySelectorAll(".prop").forEach((p) => {
      const hit = !q || (p.dataset.q || "").indexOf(q) >= 0;
      p.classList.toggle("hidden", !hit);
      if (hit) n++;
    });
    if (!q) { d.classList.remove("hidden"); return; }
    d.classList.toggle("hidden", n === 0);
    if (n) d.open = true;
  });
  if (!q && host.dataset.filtering === "1") {
    host.dataset.filtering = "0";
    host.querySelectorAll("details.grp").forEach((d) => {
      if (d.dataset.prev != null) d.open = d.dataset.prev === "1";
    });
  }
  const none = q && !host.querySelector("details.grp:not(.hidden)");
  let em = $("#propNone");
  if (none && !em) {
    em = document.createElement("div");
    em.id = "propNone"; em.className = "prop-empty";
    host.appendChild(em);
  }
  if (em) {
    em.classList.toggle("hidden", !none);
    if (none) em.textContent = "Aucun réglage pour « " + state.propQ + " ».";
  }
}

/* Le compte GLOBAL de réglages modifiés a disparu : c'était la somme des
   pastilles déjà portées par chaque groupe, et il occupait une quatrième rangée
   de commandes avant la première propriété. Le bouton « ↺ Défauts » de l'en-tête
   fait ce que faisait son lien « rétablir ». */
function refreshMods() { /* rien à faire : les pastilles de groupe suffisent */ }

/* rafraîchit uniquement les en-têtes (résumé + pastille) sans reconstruire */
function refreshGroupHeads() {
  const m = matById(state.sel);
  if (!m) return;
  const props = Object.assign({}, DEFAULT_PROPS, m.props || {});
  const derive = Object.assign({}, DEFAULT_DERIVE, m.derive || {});
  const host = $("#groups");
  GROUPS.forEach((g) => {
    const d = host.querySelector('details.grp[data-g="' + g.id + '"]');
    if (!d) return;
    const mods = modCount(g.rows, props, DEFAULT_PROPS);
    setGrpMod(d, mods);
    setGrpDigest(d, mods ? (DIGEST[g.id] ? DIGEST[g.id](props) : "") : null);
  });
  const dd = host.querySelector('details.grp[data-g="derive"]');
  if (dd) {
    const dmod = modCount(DERIVE_ROWS, derive, DEFAULT_DERIVE);
    setGrpMod(dd, dmod);
    setGrpDigest(dd, dmod ? "" : null);
  }
  refreshMods();
}
function setGrpMod(d, n) {
  let b = d.querySelector(".grp-mod");
  if (!n) { if (b) b.remove(); return; }
  if (!b) {
    b = document.createElement("em");
    b.className = "grp-mod";
    d.querySelector("summary").appendChild(b);
  }
  b.textContent = n;
  b.title = n + " réglage(s) hors défaut";
}

function renderExportMaps(m) {
  exSelectRes(m.res);
  ex.off = {};
  refreshManifest();
}

/* ── écriture des propriétés : live dans la visionneuse + PATCH groupé ── */
function setProp(row, v, livePass) {
  const m = matById(state.sel);
  if (!m) return;
  m.props = Object.assign({}, DEFAULT_PROPS, m.props || {}, { [row.k]: v });
  if (row.live) applyLive(m);
  else reloadNeeded = true;
  refreshGroupHeads();
  if (!livePass) queuePatch({ props: { [row.k]: v } });
}
function setDerive(row, v) {
  const m = matById(state.sel);
  if (!m) return;
  m.derive = Object.assign({}, DEFAULT_DERIVE, m.derive || {}, { [row.k]: v });
  refreshGroupHeads();
  queuePatch({ derive: { [row.k]: v } });
}

function queuePatch(part) {
  if (part.props) Object.assign(patchPending.props, part.props);
  if (part.derive) Object.assign(patchPending.derive, part.derive);
  if (part.name !== undefined) patchPending.name = part.name;
  clearTimeout(patchTimer);
  patchTimer = setTimeout(flushPatch, 420);
}

async function flushPatch() {
  const id = state.sel;
  if (!id) return;
  const body = {};
  if (Object.keys(patchPending.props).length) body.props = patchPending.props;
  if (Object.keys(patchPending.derive).length) body.derive = patchPending.derive;
  if (patchPending.name !== undefined) body.name = patchPending.name;
  patchPending = { props: {}, derive: {}, name: undefined };
  if (!Object.keys(body).length) return;
  try {
    const d = await api.patch("/materials/" + encodeURIComponent(id), body);
    if (d && d.material) {
      d.material._v = (matById(id) || {})._v || 0;
      upsert(d.material);
      updateEditorHead(d.material);
    }
    if (reloadNeeded) {
      reloadNeeded = false;
      const m = matById(id);
      if (m && state.view === "editor") {
        m._v = (m._v || 0) + 1;
        setViewportSrc(m);
      }
    }
  } catch (e) {
    toast("Enregistrement impossible : " + e.message, true);
  }
}

/* Application immédiate dans la visionneuse (API scene-graph de model-viewer).
   Tout est gardé : une version sans cette API se contente du rechargement. */
function hexRgb(h) {
  const s = String(h || "#ffffff").replace("#", "");
  return [parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255,
          parseInt(s.slice(4, 6), 16) / 255].map((x) => (isFinite(x) ? x : 1));
}
function applyLive(m) {
  const mv = $("#mv");
  const mat = mv && mv.model && mv.model.materials && mv.model.materials[0];
  if (!mat) return false;
  const p = Object.assign({}, DEFAULT_PROPS, m.props || {});
  try {
    const c = hexRgb(p.color);
    mat.pbrMetallicRoughness.setBaseColorFactor([c[0], c[1], c[2], clamp(num(p.opacity, 1), 0, 1)]);
    mat.pbrMetallicRoughness.setMetallicFactor(clamp(num(p.metallic, 0), 0, 1));
    mat.pbrMetallicRoughness.setRoughnessFactor(clamp(num(p.roughness, 1), 0, 1));
    const e = hexRgb(p.emissive), s = clamp(num(p.emissive_strength, 0), 0, 5);
    mat.setEmissiveFactor([e[0] * s, e[1] * s, e[2] * s]);
    if (typeof mat.setAlphaMode === "function") {
      mat.setAlphaMode(num(p.opacity, 1) < 0.999 ? "BLEND" : "OPAQUE");
    }
  } catch (err) { return false; }
  return true;
}
function applyAllLive(m) {
  const mv = $("#mv");
  if (!mv) return;
  if (mv.model) applyLive(m);
  else mv.addEventListener("load", () => applyLive(m), { once: true });
}

/* ── actions de l’inspecteur ── */
async function resetProps() {
  const id = state.sel;
  if (!id) return;
  try {
    const d = await api.patch("/materials/" + encodeURIComponent(id), { props: DEFAULT_PROPS });
    const m = (d && d.material) || Object.assign(matById(id) || {}, { props: Object.assign({}, DEFAULT_PROPS) });
    m._v = ((matById(id) || {})._v || 0) + 1;
    upsert(m);
    fillInspector(m);
    if (state.view === "editor") setViewportSrc(m);
    toast("Propriétés réinitialisées.");
  } catch (e) { toast("Réinitialisation impossible : " + e.message, true); }
}

async function rederive() {
  const id = state.sel;
  if (!id) return;
  const m = matById(id);
  const btn = $("#btnDerive");
  if (btn) { btn.disabled = true; btn.textContent = "↻ Dérivation…"; }
  try {
    await flushPatch();
    const d = await api.post("/materials/" + encodeURIComponent(id) + "/derive",
      { derive: (m && m.derive) || DEFAULT_DERIVE, res: m && m.res });
    const nm = (d && d.material) || m;
    nm._v = ((m && m._v) || 0) + 1;
    upsert(nm);
    fillInspector(nm);
    // Même chemin que partout ailleurs : 1024 + voyant de chargement + gestion
    // d'erreur. Recharger directement en 2048 ici faisait tomber 10 Mo sur une
    // matière 4K sans le moindre retour visuel pendant la seconde et demie.
    if (state.view === "editor") setViewportSrc(nm);
    renderGallery();
    /* le compte vient de ce que l'API RENVOIE, pas d'un 8 écrit en dur :
       une revendication chiffrée doit venir de la mesure. */
    toast(((nm.maps || []).length || "les") + " maps re-dérivées localement — 0 crédit.");
  } catch (e) { toast("Dérivation impossible : " + e.message, true); }
  if (btn) { btn.disabled = false; btn.textContent = "↻ Re-dériver les maps"; }
}

async function captureThumb() {
  const id = state.sel;
  if (!id) return;
  const mv = $("#mv");
  if (!mv || typeof mv.toBlob !== "function") { toast("Visionneuse indisponible.", true); return; }
  try {
    const blob = await mv.toBlob({ mimeType: "image/png", idealAspect: true });
    const r = await api.raw("PUT", "/materials/" + encodeURIComponent(id) + "/thumb", blob,
      { "Content-Type": "image/png" });
    if (!r.ok) throw new Error(r.status + " " + r.statusText);
    const m = matById(id);
    if (m) { m.thumb = true; m._v = (m._v || 0) + 1; }
    toast("Vignette de la carte mise à jour depuis le rendu 3D.");
  } catch (e) { toast("Vignette de la carte impossible : " + e.message, true); }
}

async function applyPreset() {
  const id = state.sel, pid = $("#presetSel").value;
  if (!id || !pid) return;
  const p = state.presets.find((x) => x.id === pid);
  if (!p) return;
  try {
    const d = await api.patch("/materials/" + encodeURIComponent(id), { props: p.props || {} });
    const m = (d && d.material) || matById(id);
    m._v = ((matById(id) || {})._v || 0) + 1;
    upsert(m);
    fillInspector(m);
    if (state.view === "editor") setViewportSrc(m);
    toast("Préréglage appliqué : " + (p.label || p.id));
  } catch (e) { toast("Préréglage impossible : " + e.message, true); }
}

/* ═══════════════════════════ EXPORT ═══════════════════════════
   La barre de référence propose « Download GLB » et rien d'autre : on ne sait
   ni ce qu'on emporte, ni pour quel moteur, ni combien ça pèse. Ici le bloc
   répond aux trois questions dans l'ordre de la décision — quel livrable, pour
   quel moteur, à quelle définition — puis affiche le BORDEREAU : la liste des
   fichiers réellement produits, avec leur nom moteur, leurs canaux, leur
   profondeur et leur poids, total compris. Le bouton répète le nom de
   l'archive et son poids : plus rien à deviner avant de cliquer.

   Le bordereau vient du backend (/materials/<id>/export/manifest) : ce sont des
   tailles lues sur disque. « = » quand c'est mesuré, « ≈ » quand la résolution
   ou la profondeur demandée oblige à extrapoler — on ne maquille jamais une
   estimation en mesure. */

/* ── AUCUNE LIGNE SANS DESCRIPTION, ET L'ORDRE DES CANAUX POUR CHACUNE ───────
   `braise_MaskMap.png` sortait en orphelin : « · RGBA 8 bits » et rien d'autre,
   deux lignes sous un ORM correctement documenté « R=AO V=rugosité B=métal » —
   alors que le MaskMap est précisément le fichier dont TOUT le sens est l'ordre
   de ses canaux. La cause : un dictionnaire local indexé par `kind`, muet dès
   que le backend livrait une sorte qu'il ne connaissait pas.

   Correction en deux temps. D'abord la description ne peut plus être vide :
   `manifestRole()` prend celle du backend, sinon la nôtre, sinon une phrase
   construite à partir des canaux — et signale l'angle mort en console plutôt
   que de rendre un blanc. Ensuite l'ordre des canaux est écrit sur CHAQUE
   ligne, y compris les maps à un seul canal : `CHAN_ORDER` le donne pour les
   sortes connues, et pour une sorte inconnue on le relit dans le rôle du
   backend (« R=métal V=occlusion… ») ou, en dernier recours, on énumère les
   canaux du fichier. Un fichier empaqueté sans ordre de canaux est illisible :
   cet écran ne peut plus en produire un. */
const MAP_ROLE = {
  basecolor: "Couleur diffuse, sRGB",
  normal: "Relief tangent-space, OpenGL +Y",
  roughness: "Rugosité · 0 miroir, 1 mat",
  metallic: "Métallicité · 0 diélectrique, 1 métal",
  ao: "Occlusion ambiante, assombrit les creux",
  height: "Déplacement / parallaxe",
  emissive: "Zones qui émettent de la lumière",
  orm: "Packée pour glTF / Unreal",
  maskmap: "Packée pour le Lit URP / HDRP d'Unity",
  smoothness: "Lissage · inverse de la rugosité",
  opacity: "Opacité · 0 transparent, 1 opaque",
  displacement: "Déplacement géométrique",
};
const CHAN_ORDER = {
  basecolor: "R V B = couleur",
  normal: "R = pente X · V = pente Y · B = Z",
  roughness: "L = rugosité",
  metallic: "L = métallicité",
  ao: "L = occlusion",
  height: "L = hauteur",
  emissive: "R V B = lumière émise",
  orm: "R = occlusion · V = rugosité · B = métal",
  maskmap: "R = métal · V = occlusion · B = détail · A = lissage",
  smoothness: "L = lissage",
  opacity: "L = opacité",
  displacement: "L = déplacement",
};
const EXTRA_ROLE = {
  "material.json": "Toutes les valeurs PBR, relisibles par un script",
  "LISEZMOI.txt": "Score de raccord, contenu de l'ORM, convention utilisée",
  "thumb.png": "Vignette de la carte, capturée dans le rendu 3D",
};

/* Le rôle du backend est parfois DÉJÀ une énumération de canaux (« Packée R=AO
   V=rugosité B=métal… »). Comme l'ordre des canaux a maintenant sa propre ligne,
   canonique et en mono, on retire l'énumération de la phrase : deux fois la même
   information sur deux lignes n'apprend rien de plus que la première. */
function stripChannels(txt) {
  return String(txt)
    .replace(/[RVGB]\s*=\s*[^\s,;·]+(?:\s*[·,;]?\s*[RVGBA]\s*=\s*[^\s,;·]+)+/g, " ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([—:,;.])/g, "$1")
    .replace(/[\s:—-]+$/, "")
    .trim();
}

/* description d'une ligne de bordereau — jamais vide, jamais devinée à tort */
function manifestRole(e) {
  const raw = String((e && e.role) || "").trim();
  const k = (e && e.kind) || "";
  if (raw) {
    const r = CHAN_ORDER[k] ? stripChannels(raw) : raw;
    if (r) return r;
  }
  if (MAP_ROLE[k]) return MAP_ROLE[k];
  if (typeof console !== "undefined" && console.warn) {
    console.warn("[materialforge] sorte de fichier sans description : " + (k || "?"));
  }
  const ch = String((e && e.channels) || "").toUpperCase();
  return ch.length > 1
    ? "Fichier de données packé sur " + ch.length + " canaux, livré dans l'archive"
    : "Fichier de données à un canal, livré dans l'archive";
}

/* ordre des canaux — écrit pour chaque fichier empaqueté, sans exception */
function chanOrder(e) {
  const k = (e && e.kind) || "";
  if (CHAN_ORDER[k]) return CHAN_ORDER[k];
  /* sorte inconnue de cet écran : on relit l'ordre dans le rôle du backend
     (« R=métal V=occlusion B=détail A=smoothness ») avant d'improviser. */
  const r = String((e && e.role) || "");
  const found = [];
  const re = /([RVGBA])\s*=\s*([^\s,;·]+)/g;
  let mm;
  while ((mm = re.exec(r))) found.push(mm[1].replace("G", "V") + " = " + mm[2]);
  if (found.length) return found.join(" · ");
  const ch = String((e && e.channels) || "").toUpperCase().replace("G", "V");
  if (!ch) return "canaux non déclarés par le backend";
  if (ch === "L") return "L = niveau de gris";
  return ch.split("").join(" ") + " — rôle des canaux non déclaré";
}

function extraRole(name) {
  const n = String(name || "");
  if (EXTRA_ROLE[n]) return EXTRA_ROLE[n];
  if (/\.(glb|gltf|bin)$/i.test(n)) return "Géométrie du maillage exporté, textures comprises";
  if (/\.(txt|md)$/i.test(n)) return "Note jointe à l'archive";
  if (/\.json$/i.test(n)) return "Données de la matière, relisibles par un script";
  if (/\.(png|jpg|jpeg)$/i.test(n)) return "Image jointe à l'archive";
  return "Fichier joint à l'archive";
}
/* LA PHRASE QUE CECI REMPLACE : « Slots URP / HDRP : BaseMap, MaskMap,
   Occlusion. Dépose le dossier dans Assets/, Unity branche les textures seul. »
   Trois erreurs en une ligne — URP Lit n'a AUCUNE propriété Mask Map, HDRP n'a
   pas d'emplacement Occlusion séparé (il est dans le canal V du Mask Map), et
   Unity ne branche rien tout seul : les textures se déposent à la main dans les
   emplacements du matériau. La vérité moteur vit au backend, vérifiée dans la
   documentation Unity, et se lit sur `GET /api/materials/namings` (ainsi que
   sur le bordereau, champ `naming_note`). Cette table n'est plus qu'un cache. */
const NAMING_NOTE = {};
async function loadNamings() {
  try {
    const d = await api.get("/materials/namings");
    (d.namings || []).forEach((n) => { if (n && n.id) NAMING_NOTE[n.id] = n.note || ""; });
    const cur = $("#exNamingNote");
    if (cur && !cur.textContent) cur.textContent = NAMING_NOTE[ex.naming] || "";
  } catch (e) { /* le bordereau porte déjà la note : rien à inventer ici */ }
}
const FORMAT_NOTE = {
  zip: "Un dossier de PNG, relisible par tout moteur — et le seul livrable qui emporte la height (donc le displacement) et la profondeur 16 bits.",
  glb: "Fichier unique, textures embarquées : Blender, Unity, Godot, la visionneuse Windows. La height n'existe pas en glTF cœur — prends le ZIP pour le displacement.",
  gltf: "Même scène en JSON lisible (buffer base64) : plus lourd que le GLB, mais versionnable et inspectable à la main.",
};
const BITS_NOTE = {
  8: "8 bits partout : poids minimal, et c'est tout ce que voient la couleur, la rugosité et l'AO.",
  16: "16 bits appliqué à height et normal uniquement — les deux maps où les paliers se voient (bandes sur le displacement). Les autres restent en 8 bits, l'archive ne double pas.",
};

/* `kinds` = l'univers RÉEL des fichiers livrables, tel que le bordereau du
   backend le déclare pour la convention courante. Il n'est pas égal à `MAPS` :
   en convention Unity le backend ajoute un `maskmap` (R=métal V=occlusion
   B=détail A=smoothness) que cet écran ne connaissait pas. `exSelectedMaps()`
   repartait de `MAPS`, donc dès que l'utilisateur touchait une case, la
   requête d'export listait huit noms SANS le maskmap : l'archive Unity
   repartait sans le seul fichier que le Lit URP/HDRP lit vraiment.
   `sync` = « laisse le backend choisir » : à l'ouverture et à chaque
   changement de convention, on n'envoie pas de liste, on ADOPTE `default_maps`
   du bordereau. Après quoi le choix de l'utilisateur est envoyé en toutes
   lettres — y compris « tout », qui sans cela retombait sur les défauts. */
const ex = { format: "zip", naming: "standard", res: 2048, bits: 8, off: {},
             mani: null, kinds: null, sync: true };
let maniTimer = null, maniSeq = 0;

function fmtBytes(n) {
  n = num(n, 0);
  if (n < 1024) return n + " o";
  if (n < 1024 * 1024) return (n / 1024).toFixed(n < 10240 ? 1 : 0).replace(".", ",") + " ko";
  return (n / 1048576).toFixed(1).replace(".", ",") + " Mo";
}
function exSelectRes(res) {
  const want = String(num(res, 2048));
  const btns = $$("#exRes .seg-b");
  if (btns.some((b) => b.dataset.v === want)) ex.res = Number(want);
  btns.forEach((b) => b.classList.toggle("active", b.dataset.v === String(ex.res)));
}
function exSetSeg(host, v) {
  $$(host + " .seg-b").forEach((b) => b.classList.toggle("active", b.dataset.v === String(v)));
}
function exKinds() {
  return (ex.kinds && ex.kinds.length) ? ex.kinds : MAPS.map((m) => m.k);
}
function exSelectedMaps() {
  delete ex.off.basecolor;              // jamais retirable, quel que soit le chemin
  return exKinds().filter((k) => !ex.off[k]);
}
function exportUrl(id, manifest) {
  const q = new URLSearchParams({
    format: ex.format, naming: ex.naming,
    res: String(ex.res), bits: String(ex.bits),
  });
  if (!ex.sync && ex.kinds) {
    const sel = exSelectedMaps();
    if (sel.length) q.set("maps", sel.join(","));
  }
  /* le maillage part AUSSI sur l'export reel, pas seulement sur le bordereau :
     sinon le bordereau chiffrait un tore et l'archive livrait une sphere. */
  q.set("mesh", state.mesh || "sphere");
  return "/api/materials/" + encodeURIComponent(id)
       + (manifest ? "/export/manifest?" : "/export?") + q.toString();
}

/* Le bordereau est demandé au backend à chaque changement de réglage — c'est
   une lecture de tailles, aucune image n'est ré-encodée. */
function refreshManifest() {
  clearTimeout(maniTimer);
  maniTimer = setTimeout(fetchManifest, 90);
}
async function fetchManifest() {
  const id = state.sel;
  if (!id) return;
  const seq = ++maniSeq;
  const glbLike = ex.format !== "zip";
  $("#exNamingFld").classList.toggle("off", glbLike);
  $("#exBitsFld").classList.toggle("off", glbLike);
  try {
    const d = await api.get(exportUrl(id, true).replace(/^\/api/, ""));
    if (seq !== maniSeq) return;
    ex.mani = d;
    renderMani(d);
  } catch (e) {
    if (seq !== maniSeq) return;
    ex.mani = null;
    $("#exMani").innerHTML = '<div class="mani-empty">Bordereau indisponible : ' + esc(e.message) + "</div>";
    $("#exTot").textContent = "—";
    $("#exWeigh").textContent = "";
    $("#btnExport").innerHTML = "⬇ Télécharger";
  }
}

function renderMani(d) {
  const host = $("#exMani");
  const rows = [];
  /* l'univers des fichiers vient du bordereau, jamais de la liste locale */
  ex.kinds = (d.entries || []).map((e) => e.kind).filter(Boolean);
  if (ex.sync) {
    // adoption des défauts du moteur : ce que le backend a coché fait foi
    ex.off = {};
    const def = d.default_maps || null;
    (d.entries || []).forEach((e) => {
      const on = def ? def.indexOf(e.kind) >= 0 : e.selected !== false;
      if (!on) ex.off[e.kind] = true;
    });
    ex.sync = false;
  }
  const approx = (e) => (e.exact ? "" : "≈ ");
  /* LE « ≈ » NE PEUT PLUS ÊTRE MUET. Il est désormais suivi, SUR LA LIGNE,
     de la raison courte qui le justifie (« niveau cuit à l'export »,
     « fabriqué à l'export », « rééchantillonné », « 16 bits »). Une infobulle
     ne suffisait pas : on lisait trois fichiers 8 bits marqués ≈ à côté d'un
     quatrième, 8 bits lui aussi, donné comme exact, sans rien qui les sépare
     à l'écran. */
  const wtag = (e) => (e.exact || !e.weigh_tag ? ""
    : ' <i class="wtag" title="' + esc(e.weigh || "") + '">≈ ' +
      esc(e.weigh_tag) + "</i>");
  (d.entries || []).forEach((e) => {
    const on = !ex.off[e.kind];         // ex.off vient d'être aligné sur le bordereau
    // La couleur de base ne se décoche pas : une archive sans elle n'est pas
    // une matière, c'est un jeu de masques. La case reste VISIBLE et cochée,
    // verrouillée, avec la raison en infobulle — plutôt qu'absente, ce qui
    // ferait croire à un oubli.
    const lock = e.kind === "basecolor";
    rows.push(
      '<label class="mrow' + (on ? "" : " off") + (lock ? " lock" : "") +
        '" title="' + esc(e.name) + " — " + esc(manifestRole(e)) + " · " +
          esc(e.channels) + " " + num(e.bits, 8) + " bits · " + esc(chanOrder(e)) +
        (e.weigh ? " · Poids " + (e.exact ? "mesuré" : "estimé") + " : " +
                   esc(e.weigh) : "") +
        (lock ? " — obligatoire : sans couleur de base, la matière livrée est inutilisable" : "") + '">' +
        '<input type="checkbox" value="' + esc(e.kind) + '"' + (on ? " checked" : "") +
          (lock ? " disabled" : "") + ">" +
        '<span class="mn">' + esc(e.name) +
          (lock ? ' <i class="req">requise</i>' : "") + "</span>" +
        '<span class="msz">' + approx(e) + fmtBytes(e.bytes) + "</span>" +
        '<span class="mr"><span class="rl">' + esc(manifestRole(e)) +
          ' · <b>' + esc(e.channels) + " " + num(e.bits, 8) + " bits</b></span>" +
          // l'ordre des canaux est tronqué à la largeur de la colonne ; la
          // RAISON du « ≈ », elle, ne peut pas l'être — elle a sa propre ligne.
          '<i class="mch">' + esc(chanOrder(e)) + "</i>" + wtag(e) + "</span>" +
      "</label>");
  });
  (d.extras || []).forEach((e) => {
    rows.push(
      '<div class="mrow extra" title="' + esc(e.name) +
        (e.weigh ? " — poids " + (e.exact ? "mesuré" : "estimé") + " : " +
                   esc(e.weigh) : "") + '">' +
        '<span class="plus">+</span>' +
        '<span class="mn">' + esc(e.name) + "</span>" +
        '<span class="msz">' + approx(e) + fmtBytes(e.bytes) + "</span>" +
        '<span class="mr">' + esc(extraRole(e.name)) + wtag(e) + "</span>" +
      "</div>");
  });
  // Pas de ligne « total » dans le bordereau : elle répétait le nom de
  // l'archive et son poids, déjà portés par le bouton juste dessous (et par la
  // pastille de l'en-tête quand le bloc est replié). Un total est la somme des
  // lignes au-dessus : le lire deux fois n'apprend rien.
  const tot = (d.exact ? "" : "≈ ") + fmtBytes(d.total_bytes);
  host.innerHTML = rows.join("");
  $$("#exMani input").forEach((c) => {
    c.onchange = () => {
      if (!c.checked) ex.off[c.value] = true; else delete ex.off[c.value];
      if (!exSelectedMaps().length) { c.checked = true; delete ex.off[c.value]; return; }
      refreshManifest();
    };
  });
  const nsel = (d.entries || []).filter((e) => !ex.off[e.kind]).length;
  $("#exCount").textContent = "· " + (nsel + (d.extras || []).length) + " fichiers";
  $("#exTot").textContent = tot;
  // le poids de l'archive n'est pas un COÛT : il ne porte plus le jeton ambre
  // réservé aux crédits (« 4 cr » du bouton de forge).
  $("#btnExport").innerHTML = "⬇ " + esc(d.archive) + ' <b class="est-size">' + tot + "</b>";
  $("#exFoot").textContent = FORMAT_NOTE[d.format] || "";
  // le bordereau porte la note VERIFIEE de la convention qu'il decrit
  $("#exNamingNote").textContent = d.naming_note || NAMING_NOTE[d.naming] || "";
  $("#exBitsNote").textContent = BITS_NOTE[d.bits] || "";
  exResNote(d);
  exWeighNote(d);
  markNativeRes(d.native_res);
}

/* ── ce que « Taille à l'export » fait VRAIMENT ──────────────────────────────
   L'écran affirmait deux choses incompatibles : un sélecteur 512/1K/2K/4K, et
   juste dessous « les PNG partent tels qu'ils ont été calculés, sans
   rééchantillonnage, poids extrapolé ». Vérification faite dans le code
   (routes.export_material -> material_store.resize_maps) PUIS par des exports
   de contrôle dont on a mesuré les dimensions DANS l'archive : depuis une
   matière native 2048², demander 512 rend huit PNG 512×512, demander 4096 rend
   huit PNG 4096×4096. Le sélecteur rééchantillonne, point.

   La légende dit donc désormais l'opération réellement appliquée au choix
   courant — et le backend l'accompagne (`resample`), pour que l'écran n'ait
   pas à la déduire. Le caractère estimé ou mesuré du POIDS est une autre
   question : il a sa propre ligne, sous le bordereau. Deux faits, deux
   phrases ; l'ancienne les cousait en une seule et devenait fausse. */
function exResNote(d) {
  const el = $("#exResNote");
  if (!el) return;
  const t = num(d && d.res, 0), n = num(d && d.native_res, 0);
  const mode = (d && d.resample) || (!n || t === n ? "none" : (t > n ? "up" : "down"));
  /* « les huit PNG » était écrit en dur : en convention Unity l'archive en
     emporte sept, dont un MaskMap que ce compte ignorait. Le nombre vient du
     bordereau, donc de ce qui part vraiment. */
  const k = d && d.entries
    ? d.entries.filter((e) => !ex.off[e.kind]).length : 0;   // même source que #exCount
  const png = k ? "les " + k + " PNG" : "les PNG";
  let s;
  if (mode === "none") {
    s = "Livraison à la définition native (" + (n || t) + "²) : aucun " +
        "rééchantillonnage, " + png + " partent tels qu'ils ont été calculés.";
  } else if (mode === "up") {
    s = "Agrandissement à la livraison : " + n + "² → " + t + "², " + png + " sont " +
        "interpolés. Le fichier grossit, le détail non — pour de vrais pixels en " +
        t + "², reforge la matière à cette définition.";
  } else {
    s = "Réduction à la livraison : " + n + "² → " + t + "², " + png + " sont " +
        "rééchantillonnés (Lanczos pour la couleur, bicubique pour les données, " +
        "normale renormalisée). Micro-détail perdu ; la matière rangée sur " +
        "disque, elle, ne bouge pas.";
  }
  el.textContent = s;
}

/* ── LA RÈGLE DU « ≈ », ÉCRITE ET APPLIQUÉE SANS EXCEPTION ─────────────────
   Le marqueur était une légende qui contredisait son application : la seule
   justification visible parlait de profondeur 16 bits, or « ≈ » était posé sur
   trois fichiers 8 bits (Roughness L 8, ORM RGB 8, MaskMap RGBA 8) pendant
   qu'Occlusion — L 8 elle aussi — était donnée comme exacte. Rien à l'écran ne
   les séparait, donc le marqueur ne voulait rien dire.

   La règle réelle ne dépend ni du nombre de canaux ni de la profondeur :

     =  le fichier qui part existe déjà, encodé, sur le disque — on LIT sa taille ;
     ≈  l'export doit FABRIQUER un fichier qui n'existe pas encore.

   Quatre fabrications, une seule suffit : niveau cuit dans la map (rugosité,
   métal, ORM — les trois seules que `bake_levels` transforme), fichier empilé
   à la volée (MaskMap), rééchantillonnage, 16 bits ou base64 glTF.

   Cette note énonce la règle telle que le backend la publie (`weigh_rule`),
   puis dit, POUR CETTE ARCHIVE, quelles lignes elle touche et pourquoi — les
   raisons sont regroupées, jamais recopiées ligne à ligne. Chaque ligne du
   bordereau porte en plus son étiquette courte à côté du « ≈ ».

   Le même « ≈ » gouverne le coût et la durée annoncés avant la forge : eux non
   plus ne peuvent pas être lus sur un fichier existant. Une seule règle. */
const WEIGH_RULE_FALLBACK =
  "Un poids est mesuré quand le fichier qui part existe déjà, encodé, sur le " +
  "disque. Il est estimé — « ≈ » — dès que l'export doit en fabriquer un.";

function exWeighNote(d) {
  const el = $("#exWeigh");
  if (!el) return;
  // seules les lignes COCHÉES sont concernées : ce sont les seules qui partent
  // (et les seules que le total additionne).
  const maps = (d && d.entries || []).filter((e) => !ex.off[e.kind]);
  const ann = d && d.extras || [];
  const est = maps.filter((e) => !e.exact).concat(ann.filter((e) => !e.exact));
  const mes = maps.filter((e) => e.exact);
  const noms = (l) => l.map((e) => (e.kind ? mapFr(e.kind) : e.name)).join(", ");
  if (!est.length) {
    el.innerHTML = "<b>Poids mesurés.</b> Les " + (mes.length + ann.length) +
      " fichiers de cette archive sont comptés octet par octet — les " +
      mes.length + " PNG partent tels qu'ils sont sur le disque, rien n'est " +
      "fabriqué à l'export.";
    el.classList.remove("est");
    return;
  }
  // regroupement par raison : « rugosité, métal, ORM ≈ niveau cuit à l'export »
  const par = new Map();
  est.forEach((e) => {
    const k = e.weigh_tag || "fabriqué à l'export";
    if (!par.has(k)) par.set(k, []);
    par.get(k).push(e);
  });
  const groupes = [...par.entries()].map(([tag, l]) =>
    "<b>" + esc(noms(l)) + "</b> ≈ " + esc(tag)).join(" · ");
  /* L'ECART ANNONCE EST CELUI QU'ON A MESURE, pas celui qu'on espere. Sur 28
     exports de controle (4 matieres x 7 reglages), bordereau confronte a
     l'archive telechargee : +/- 7 % a definition native, jusqu'a +23 % quand
     l'export reechantillonne (le PNG redimensionne se compresse mieux que le
     modele ne le prevoit, et cela depend du motif). */
  const down = d && d.resample && d.resample !== "none";
  el.innerHTML =
    "<b>La règle du ≈ :</b> " + esc(d && d.weigh_rule || WEIGH_RULE_FALLBACK) +
    "<br><b>Ici :</b> " + groupes +
    (mes.length ? " — <b>" + esc(noms(mes)) + "</b> partent inchangées, poids " +
      "lus sur le disque." : "") +
    " Le modèle est calibré sur de vraies archives ; écart mesuré sur 28 " +
    "exports de contrôle : " +
    (down ? "jusqu'à +23 % en rééchantillonnant" : "±7 %") +
    ". Le poids exact reste celui du fichier téléchargé.";
  el.classList.add("est");
}

/* le segment qui correspond à la définition source est signalé : on voit du
   premier coup d'œil laquelle des deux commandes est « à l'identique » */
function markNativeRes(native) {
  $$("#exRes .seg-b").forEach((b) => {
    const nat = Number(b.dataset.v) === num(native, 0);
    b.classList.toggle("nat", nat);
    b.title = nat ? "Définition source de cette matière — aucun rééchantillonnage"
                  : (Number(b.dataset.v) > num(native, 0)
                      ? "Agrandissement par interpolation depuis " + native + "²"
                      : "Réduction depuis " + native + "²");
  });
}

function wireExport() {
  $$("#exFormat .fmt").forEach((b) => {
    b.onclick = () => {
      ex.format = b.dataset.v;
      $$("#exFormat .fmt").forEach((x) => x.classList.toggle("active", x === b));
      refreshManifest();
    };
  });
  $$("#exNaming .seg-b").forEach((b) => {
    b.onclick = () => {
      /* Unity, Unreal et Godot ne livrent pas les memes fichiers : changer de
         convention remet la selection sur les defauts du moteur visE. */
      ex.naming = b.dataset.v; ex.sync = true; ex.kinds = null;
      exSetSeg("#exNaming", ex.naming); refreshManifest();
    };
  });
  $$("#exRes .seg-b").forEach((b) => {
    b.onclick = () => { ex.res = Number(b.dataset.v); exSetSeg("#exRes", ex.res); refreshManifest(); };
  });
  $$("#exBits .seg-b").forEach((b) => {
    b.onclick = () => { ex.bits = Number(b.dataset.v); exSetSeg("#exBits", ex.bits); refreshManifest(); };
  });
  $("#exAll").onclick = () => { ex.off = {}; ex.sync = false; refreshManifest(); };
  $("#exNone").onclick = () => {
    // on garde toujours la base color : un export vide n'a pas de sens
    ex.off = {}; ex.sync = false;
    exKinds().forEach((k) => { if (k !== "basecolor") ex.off[k] = true; });
    refreshManifest();
  };
  loadNamings();                       // la note vient du backend, pas d'ici
  $("#exBitsNote").textContent = BITS_NOTE[8];
  $("#exFoot").textContent = FORMAT_NOTE.zip;
  $("#exResNote").textContent = "";
  $("#exWeigh").textContent = "";
}

/* Le bloc Export règle LA MATIÈRE SÉLECTIONNÉE. Le bouton ZIP d'une carte de
   la galerie partait pourtant avec ces réglages-là — y compris la liste de
   maps cochée sur une AUTRE matière, et jusqu'au nom d'archive de l'autre.
   Une carte s'exporte donc avec les réglages annoncés pour elle : convention
   standard, sa définition native, 8 bits — exactement ce que le panneau de
   preuve liste, fichier par fichier. */
function doExport(id, fromCard) {
  const mid = id || state.sel;
  if (!mid) return;
  const m = matById(mid);
  /* Une carte s'exporte TOUJOURS avec les réglages annoncés pour elle, même
     quand c'est elle qui est ouverte dans l'éditeur : sans quoi le panneau de
     preuve, qui liste « les réglages qu'applique le bouton ZIP de la carte »,
     deviendrait faux dès qu'on aurait touché la convention. Le bouton du bloc
     Export, lui, applique le bloc Export. */
  const own = !fromCard && mid === state.sel;
  const a = document.createElement("a");
  a.href = own || !m ? exportUrl(mid) : "/api" + cardExportUrl(m, false);
  let mani = own ? ex.mani : null;
  if (!own && m) {
    const key = m.id + "?" + new URLSearchParams(cardManifestQuery(m)).toString();
    mani = maniCache.get(key) || null;
  }
  /* nom du fichier : celui du bordereau de CETTE matière quand on l'a, sinon on
     laisse le serveur nommer (Content-Disposition) plutôt que d'inventer. */
  if (mani && mani.archive) a.download = mani.archive;
  else if (own) a.download = ((m && (m.name || m.id)) || mid).replace(/[^\w.-]+/g, "_");
  document.body.appendChild(a);
  a.click();
  a.remove();
  const w = mani ? " · " + (mani.exact ? "" : "≈ ") + fmtBytes(mani.total_bytes) : "";
  toast("Téléchargement : " + (a.download || (mani && mani.archive) ||
    ((m && (m.name || m.id)) || mid)) + w);
}

/* ───────────────────────── jetons maillage / environnement ─────────────────
   Les six maillages et les sept environnements sont de VRAIES puces cliquables,
   avec l'état courant en plein. En mode éditeur elles sont ancrées dans le
   viewport (on règle l'aperçu là où on le regarde) ; en mode galerie, faute de
   viewport, elles vivent dans le rail. Jamais les deux à la fois. */
function chipsHtml(list, key, cur) {
  return list.map((x) => {
    const id = x[key];
    return `<button class="chip${id === cur ? " active" : ""}" type="button"` +
      ` data-v="${esc(id)}">${esc(x.label || id)}</button>`;
  }).join("");
}
function wireChips(sel, fn) {
  $$(sel + " .chip").forEach((b) => { b.onclick = () => fn(b.dataset.v); });
}
/* « Variés » n'est pas une case à cocher posée à côté d'une rangée de puces :
   c'était le pire cas possible — cochée, elle neutralisait la sélection de
   maillage, et « Sphère » restait allumée en plein sans plus rien gouverner.
   C'est désormais la septième option de la MÊME rangée, donc un seul état actif
   à l'écran, et il est toujours vrai. */
const VARIED = "__varied";

function renderMeshChips() {
  const vp = $("#vpMeshChips");
  if (vp) { vp.innerHTML = chipsHtml(MESHES, "id", state.mesh); wireChips("#vpMeshChips", setMesh); }
  const gl = $("#meshChips");
  if (gl) {
    const list = [{ id: VARIED, label: "Variés" }].concat(MESHES);
    gl.innerHTML = chipsHtml(list, "id", state.varied ? VARIED : state.mesh);
    const first = gl.querySelector('.chip[data-v="' + VARIED + '"]');
    if (first) first.title = "Les six maillages à tour de rôle, une carte après l'autre.";
    wireChips("#meshChips", pickCardMesh);
  }
  updateMeshNote();
}

function updateMeshNote() {
  const n = $("#meshNote");
  if (!n) return;
  n.textContent = state.varied
    ? "Les six maillages à tour de rôle, une carte après l'autre : une matière ne se juge pas que sur une sphère."
    : "Toutes les cartes sont rendues sur ce maillage.";
}

function pickCardMesh(v) {
  if (v === VARIED) {
    state.varied = true;
    localStorage.setItem("mf_varied", "1");
    renderMeshChips();
    renderGallery();
    return;
  }
  state.varied = false;
  localStorage.setItem("mf_varied", "0");
  setMesh(v);                       // re-rend les puces ET la galerie
}

function setMesh(id) {
  if (!MESHES.some((m) => m.id === id)) return;
  state.mesh = id;
  localStorage.setItem("mf_mesh", id);
  renderMeshChips();
  updateVpTag();
  if (state.view === "editor" && state.sel) {
    const m = matById(state.sel);
    if (m) setViewportSrc(m);
  }
  renderGallery();
}
/* En galerie l'environnement reste une rangée de puces (le rail a la place).
   Dans l'éditeur il passe en menu : c'est ce qui permet à la barre d'outils du
   rendu de tenir sur UNE rangée au lieu de deux empilées par-dessus l'image. */
function renderEnvChips() {
  const el = $("#envChips");
  if (el) { el.innerHTML = chipsHtml(state.envs, "name", state.env); wireChips("#envChips", setEnv); }
  const sel = $("#vpEnv");
  if (sel) {
    sel.innerHTML = state.envs.map((e) =>
      `<option value="${esc(e.name)}">${esc(e.label || e.name)}</option>`).join("");
    sel.value = state.env;
  }
}
function setEnv(name) {
  state.env = name;
  localStorage.setItem("mf_env", name);
  renderEnvChips();
  buildEnv();
}
/* l'interrupteur de lumière existe aux deux endroits : la case du rail et la
   puce du viewport disent toujours la même chose */
function setLightOn(on) {
  state.pointLight = !!on;
  const cb = $("#pointLight");
  if (cb) cb.checked = state.pointLight;
  const lc = $("#vpLight");
  if (lc) lc.classList.toggle("active", state.pointLight);
  $("#lightBox").classList.toggle("hidden", !state.pointLight);
  $("#puck").classList.toggle("hidden", !(state.pointLight && state.view === "editor"));
  updateVpTag();
  return buildEnv();
}

/* ── disque de lumière déplaçable ── */
function wirePuck() {
  /* le disque vit dans la ZONE DE RENDU, pas dans le bloc entier : les barres
     d'outils ne font plus partie de son repère. */
  const puck = $("#puck"), vp = $("#vpStage");
  let drag = false;
  const place = () => {
    puck.style.left = (state.lightUV.u * 100) + "%";
    puck.style.top = (clamp(state.lightUV.v, 0, 1) * 100) + "%";
  };
  place();
  const move = (ev) => {
    if (!drag) return;
    const r = vp.getBoundingClientRect();
    const cx = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
    const cy = (ev.touches ? ev.touches[0].clientY : ev.clientY) - r.top;
    state.lightUV.u = clamp(cx / Math.max(1, r.width), 0, 1);
    state.lightUV.v = clamp(cy / Math.max(1, r.height), 0.02, 0.85);
    place();
    buildEnv();
    ev.preventDefault();
  };
  const up = () => { drag = false; };
  puck.addEventListener("mousedown", (e) => { drag = true; e.preventDefault(); });
  puck.addEventListener("touchstart", (e) => { drag = true; e.preventDefault(); }, { passive: false });
  window.addEventListener("mousemove", move);
  window.addEventListener("touchmove", move, { passive: false });
  window.addEventListener("mouseup", up);
  window.addEventListener("touchend", up);
}

/* ───────────────────────── câblage ───────────────────────── */
function setRes(r) {
  state.res = num(r, 2048);
  $$("#resSeg .seg-b").forEach((b) => b.classList.toggle("active", Number(b.dataset.res) === state.res));
  updateEstimate();
}

async function uploadFile(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file, file.name || "reference.png");
  try {
    const d = await api.json("POST", "/images/upload", fd);
    await loadLibrary();
    setRef(d.filename);
    toast("Référence téléversée : " + d.filename);
  } catch (e) { toast("Téléversement impossible : " + e.message, true); }
}

function wire() {
  $("#model").onchange = () => {
    state.model = $("#model").value;
    localStorage.setItem("mf_model", state.model);
    updateEstimate();
  };
  $$("#resSeg .seg-b").forEach((b) => { b.onclick = () => setRes(Number(b.dataset.res)); });
  $("#enhance").onchange = updateEstimate;
  $("#seamless").onchange = () => {
    $("#seamMethod").disabled = !$("#seamless").checked;
    updateEstimate();
  };
  $("#genBtn").onclick = generate;
  $("#prompt").onkeydown = (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) generate();
  };
  $("#prompt").oninput = updateFullPrompt;
  renderSeeds();

  $("#libToggle").onclick = () => {
    const b = $("#libBox");
    b.classList.toggle("hidden");
    if (!b.classList.contains("hidden") && !(window.__mfImages || []).length) loadLibrary();
  };
  $("#libSearch").oninput = renderLibrary;
  $("#refClear").onclick = () => setRef(null);
  $("#drop").onclick = () => $("#fileInput").click();
  $("#fileInput").onchange = (e) => { uploadFile(e.target.files && e.target.files[0]); e.target.value = ""; };
  ["dragenter", "dragover"].forEach((ev) => $("#drop").addEventListener(ev, (e) => {
    e.preventDefault(); $("#drop").classList.add("over");
  }));
  ["dragleave", "drop"].forEach((ev) => $("#drop").addEventListener(ev, (e) => {
    e.preventDefault(); $("#drop").classList.remove("over");
  }));
  $("#drop").addEventListener("drop", (e) => {
    const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) uploadFile(f);
  });

  $("#cols").oninput = () => {
    state.cols = Number($("#cols").value);
    $("#colsVal").textContent = state.cols;
    localStorage.setItem("mf_cols", state.cols);
    $("#gallery").style.setProperty("--cols", state.cols);
    live.pump();                       // le budget d'aperçus suit la densité
  };
  $("#galSearch").oninput = () => { state.filter = $("#galSearch").value || ""; renderGallery(); };
  $("#galSort").innerHTML = SORTS.map((s) =>
    `<option value="${s.id}"${s.id === state.sort ? " selected" : ""}>${esc(s.label)}</option>`).join("");
  $("#galSort").onchange = () => {
    state.sort = $("#galSort").value;
    localStorage.setItem("mf_sort", state.sort);
    renderGallery();
  };
  $("#spin").onchange = () => { state.spin = $("#spin").checked; renderGallery(); };
  /* « Maillages variés » n'a plus de case à cocher : c'est la puce « Variés »
     de la rangée des maillages (pickCardMesh). */
  $("#live3d").onchange = () => {
    state.live3d = $("#live3d").checked;
    localStorage.setItem("mf_live3d", state.live3d ? "1" : "0");
    if (!state.live3d) { live.mounted.forEach((mv, id) => live.unmount(id)); }
    live.pump();
  };
  /* Le menu déroulant « Affichage » a disparu : ses trois interrupteurs sont
     posés à découvert dans le panneau « Aperçu », sous les puces qu'ils
     complètent. Une commande cachée derrière un bouton est une commande qu'on
     ne trouve pas. */
  $("#backGal").onclick = () => closeEditor();
  $("#apiRetry").onclick = () => { boot(true); };

  window.addEventListener("hashchange", onHashChange);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      disarmAll();
      /* la preuve se ferme avant tout le reste : c'est la couche du dessus */
      if (proofId) { closeProof(); return; }
      if (state.view === "editor") closeEditor();
    }
  });

  // preuve des maps : jeton de carte, badge de titre, fermeture
  $("#proofClose").onclick = closeProof;
  $("#proofBack").onclick = closeProof;
  $("#mapsBadge").onclick = () => {
    const id = $("#mapsBadge").dataset.mid;
    if (id) openProof(id);
  };
  /* la position de défilement est mémorisée en continu : on peut ouvrir une
     carte au clavier ou par lien profond, le retour reste juste. */
  $("#gallery").addEventListener("scroll", () => {
    if (state.view === "gallery") state.scroll = $("#gallery").scrollTop;
  }, { passive: true });

  $("#pointLight").onchange = () => setLightOn($("#pointLight").checked);
  $("#vpLight").onclick = () => setLightOn(!state.pointLight);
  $("#vpEnv").onchange = () => setEnv($("#vpEnv").value);
  $("#lightPow").oninput = () => { state.lightPow = Number($("#lightPow").value); buildEnv(); };

  $("#matName").onchange = () => {
    const m = matById(state.sel);
    if (!m) return;
    m.name = $("#matName").value;
    queuePatch({ name: m.name });
    renderGallery();
  };
  $("#btnReset").onclick = resetProps;
  $("#btnThumb").onclick = captureThumb;

  // barre d'outils de l'inspecteur : un préréglage, un filtre, une aide.
  // Le préréglage s'applique au choix — plus de bouton « OK » à côté.
  $("#propSearch").oninput = () => { state.propQ = $("#propSearch").value || ""; applyPropFilter(); };
  $("#allHelp").onclick = () => {
    state.helpAll = !state.helpAll;
    $("#groups").classList.toggle("showhelp", state.helpAll);
    $("#allHelp").classList.toggle("on", state.helpAll);
    $("#allHelp").title = state.helpAll
      ? "Masquer l'aide de toutes les propriétés"
      : "Afficher l'aide de toutes les propriétés d'un coup";
  };
  $("#presetSel").onchange = () => { if ($("#presetSel").value) applyPreset(); };
  $("#btnExport").onclick = () => doExport(state.sel);
  wireExport();

  wirePuck();
}

/* ───────────────────────── poignée QA ─────────────────────────
   Miroir de window.__tl du Tile Lab : état lisible + actions scriptables. */
window.__mf = {
  get state() {
    return {
      view: state.view, sel: state.sel, count: state.materials.length,
      mesh: state.mesh, env: state.env, pointLight: state.pointLight,
      lightUV: Object.assign({}, state.lightUV), cols: state.cols, varied: state.varied,
      model: state.model, res: state.res, ref: state.ref, busy: state.busy,
      apiOk: state.apiOk, estimate: estimate(), seamScale: state.seamScale,
      materials: state.materials.map((m) => ({ id: m.id, name: m.name, seam: m.seam, maps: (m.maps || []).length })),
    };
  },
  /* le budget d'aperçus 3D a quitté l'écran (télémétrie moteur) : il reste
     lisible ici, pour le diagnostic et pour le rig de charge. */
  get live() { return { mounted: live.mounted.size, budget: live.budget(), on: state.live3d }; },
  reload: () => boot(true),
  setPrompt(p) { $("#prompt").value = p; updateEstimate(); },
  setRes,
  setModel(id) { state.model = id; $("#model").value = id; updateEstimate(); },
  setRef,
  setMesh, setEnv,
  setLight(on, u, v) {
    if (u != null) state.lightUV.u = clamp(Number(u), 0, 1);
    if (v != null) state.lightUV.v = clamp(Number(v), 0, 1);
    $("#puck").style.left = (state.lightUV.u * 100) + "%";
    $("#puck").style.top = (state.lightUV.v * 100) + "%";
    return setLightOn(on);
  },
  setCols(n) { $("#cols").value = n; $("#cols").oninput(); },
  setSort(s) { $("#galSort").value = s; $("#galSort").onchange(); },
  generate,
  open: openMaterial,
  close: closeEditor,
  duplicate, remove, rederive, resetProps, captureThumb,
  exportUrl: (id) => exportUrl(id || state.sel),
  /* état des aperçus 3D : ce que le budget monte réellement */
  get live() {
    return { on: state.live3d, budget: live.budget(),
      mounted: live.mounted.size, visible: live.visible.size,
      cards: $$("#gallery .card").length };
  },
  /* injection de matières pour le harnais (aucun appel réseau) */
  __inject(list) {
    state.materials = list || [];
    apiOk(state.materials.length);
    renderGallery();
  },
  /* Harnais de charge : n cartes bâties sur les matières RÉELLES (mêmes URL,
     mêmes GLB, même réseau) — c'est la seule façon honnête de vérifier qu'une
     grande galerie ne met pas la page à genoux. */
  __stress(n) {
    const base = state.materials.filter((m) => !m._src);
    if (!base.length) return 0;
    if (!window.__mfBase) window.__mfBase = base.slice();
    const src = window.__mfBase;
    const out = [];
    for (let i = 0; i < n; i++) {
      const b = src[i % src.length];
      const c = Object.assign({}, b);
      c._src = b.id;
      c.id = "mat_" + (0x10000000 + i).toString(16).slice(0, 8);
      c.name = (b.name || "matière") + " " + String(i + 1).padStart(2, "0");
      out.push(c);
    }
    state.materials = out;
    apiOk(out.length);
    renderGallery();
    return out.length;
  },
};

/* ───────────────────────── démarrage ───────────────────────── */
async function boot(again) {
  if (!again) {
    const mesh = localStorage.getItem("mf_mesh");
    if (mesh && MESHES.some((m) => m.id === mesh)) state.mesh = mesh;
    const env = localStorage.getItem("mf_env");
    if (env) state.env = env;
    const varied = localStorage.getItem("mf_varied");
    if (varied != null) state.varied = varied === "1";
    const l3 = localStorage.getItem("mf_live3d");
    if (l3 != null) { state.live3d = l3 === "1"; $("#live3d").checked = state.live3d; }
    const so = localStorage.getItem("mf_sort");
    if (so && SORTS.some((s) => s.id === so)) state.sort = so;
    const cols = Number(localStorage.getItem("mf_cols"));
    if (cols >= 2 && cols <= 6) { state.cols = cols; $("#cols").value = cols; $("#colsVal").textContent = cols; }
    $("#gallery").style.setProperty("--cols", state.cols);
    renderMeshChips();
    renderEnvChips();
    wire();
    buildEnv();
  }
  await loadSeamScale();   // le bareme d'abord : la galerie s'en sert pour trancher
  await Promise.all([loadMaterials(), loadModels(), loadEnvs(), loadPresets(), loadLibrary()]);
  buildEnv();
  updateEstimate();
  onHashChange();          // #m/mat_xxxx : on rouvre la matière du lien
}

boot(false);
