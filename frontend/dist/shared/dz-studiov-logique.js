// dz-studiov-logique.js — SV1 (14/11/2026, studio virtuel 3D), la LOGIQUE PURE du studio : couleurs résolues (kit de
// l'espace), pose d'une caméra à l'instant t (mouvements doux), fondu entre deux caméras, champ de vision, budget de
// lumières selon la qualité, recadrage « couvrir ». Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared (banc backend/tests/test_studiov_ecran.py,
// qui joue ce module sous node). Aucun accès au DOM ni à three.js : tout arrive en paramètre.
//
// Un décor est la recette normalisée par le serveur (backend/app/services/studiov.py). Mètres, y vers le haut, le
// présentateur regarde vers +z. Le `contexte` est celui des skins : {espace, kit: {brand_color, accent_color}, logo_espace}.

export const Z_STUDIO = 30;                    // sous le fond du skin (40) et sous l'écran (100)
export const Z_VIGNETTE = 35;
export const FONDU_CAMERA = 900;               // ms : passage d'une caméra à l'autre
const HEX = /^#[0-9a-fA-F]{6}$/;
export const borne = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// le CATALOGUE du niveau « direct » : égal à studiov.TYPES_OBJET (banc) ; chaque type a son constructeur dans le moteur
export const TYPES = ["bureau", "table", "table_ronde", "chaise", "fauteuil", "canape", "etagere", "bibliotheque", "tapis",
  "pupitre", "vitrine", "etabli", "casier", "banc", "ecran_bureau", "micro_bras", "micro_table", "casque", "softbox",
  "projecteur", "camera_pied", "panneau_acoustique", "lampe", "lampadaire", "neon_barre", "neon_anneau", "guirlande",
  "plante", "cadre", "colonne", "arche", "caisse", "horloge", "fenetre", "imprimante3d", "bobine", "figurine",
  "boite_jeu", "plateau_jeu", "pion", "de", "console_scifi", "hublot", "tube_lumineux", "hologramme", "nuage",
  "arbre_cartoon", "champignon", "etoile", "but_foot", "ballon_foot", "gradin", "panier_basket", "ballon_basket",
  "ballon_ovale", "batte", "trophee", "tableau_tactique", "fanion", "maillot"];

// ── couleurs : un rôle (principale, accent, texte, fond) ou un #rrggbb ──
export function palette(contexte) {
  const kit = (contexte && contexte.kit) || {};
  const sur = (v, d) => (typeof v === "string" && HEX.test(v) ? v : d);
  return { principale: sur(kit.brand_color, "#f0b429"), accent: sur(kit.accent_color, "#00e5ff"), texte: "#ffffff", fond: "#0b0f14" };
}
export function couleur(ref, pal, defaut) {
  if (typeof ref === "string" && HEX.test(ref)) return ref.toLowerCase();
  return (pal && typeof ref === "string" && pal[ref]) || defaut || (pal && pal.principale) || "#f0b429";
}
export const entier = (hex) => parseInt((HEX.test(hex) ? hex : "#000000").slice(1), 16);

// ── caméras ──
// champ de vision vertical (degrés) d'une focale en mm, capteur plein format (24 mm de haut)
export const champ = (focale) => (2 * Math.atan(12 / borne(Number(focale) || 35, 14, 135)) * 180) / Math.PI;

// la pose {x, y, z, vers: [x, y, z], champ} d'une caméra à l'instant t (ms) : le mouvement est une oscillation douce,
// nulle en moyenne — la caméra revient toujours à sa place (pas de dérive sur un direct de deux heures)
export function poseCamera(cam, t) {
  const c = cam || {}, v = Array.isArray(c.vers) && c.vers.length === 3 ? c.vers : [0, 1.2, 0];
  const a = Number(c.amplitude) || 0, T = Math.max(2, Number(c.periode_s) || 10) * 1000;
  const ph = (2 * Math.PI * (Number(t) || 0)) / T, s = Math.sin(ph), s2 = Math.sin(ph * 0.5 + 1.3);
  let x = Number(c.x) || 0, y = Number(c.y) || 0, z = Number(c.z) || 0, f = champ(c.focale);
  const dx = v[0] - x, dz = v[2] - z, d = Math.hypot(dx, dz) || 1;
  const lx = -dz / d, lz = dx / d;                // la droite de la caméra, au sol
  switch (c.mouvement) {
    case "respiration": x += lx * a * s; z += lz * a * s; y += a * 0.5 * s2; break;
    case "travelling": x += lx * a * s; z += lz * a * s; break;
    case "poussee": x += (dx / d) * a * s; z += (dz / d) * a * s; break;
    case "orbite": {
      const ang = a * s, ca = Math.cos(ang), sa = Math.sin(ang), rx = x - v[0], rz = z - v[2];
      x = v[0] + rx * ca - rz * sa; z = v[2] + rx * sa + rz * ca; break;
    }
    default: break;
  }
  return { x, y, z, vers: [v[0], v[1], v[2]], champ: f };
}

// le fondu entre deux poses : k 0..1, adouci (accélère puis ralentit)
export function melanger(a, b, k) {
  const u = borne(k, 0, 1), e = u * u * (3 - 2 * u), m = (p, q) => p + (q - p) * e;
  return { x: m(a.x, b.x), y: m(a.y, b.y), z: m(a.z, b.z), champ: m(a.champ, b.champ),
    vers: [m(a.vers[0], b.vers[0]), m(a.vers[1], b.vers[1]), m(a.vers[2], b.vers[2])] };
}

// l'état des caméras d'un direct : la caméra courante, la précédente et l'instant de la bascule
export function regie(nombre) {
  const n = Math.max(1, nombre | 0);
  const r = { courante: 0, precedente: 0, depuis: -1e9 };
  r.basculer = (i, t) => {
    const j = ((i | 0) % n + n) % n;
    if (j === r.courante) return r.courante;
    r.precedente = r.courante; r.courante = j; r.depuis = Number(t) || 0;
    return j;
  };
  r.pose = (cameras, t) => {
    const p = poseCamera(cameras[r.courante], t), k = (t - r.depuis) / FONDU_CAMERA;
    return k >= 1 ? p : melanger(poseCamera(cameras[r.precedente], t), p, k);
  };
  return r;
}

// ── lumières : le budget temps réel selon la qualité (« legere » = carte intégrée) ──
// rend les lumières à allumer VRAIMENT (les autres ne gardent que leur objet lumineux) : toujours la clé, l'appoint et
// le premier contre ; puis les néons les plus forts jusqu'au plafond
export function budgetLumieres(lumieres, qualite) {
  const max = qualite === "haute" ? 10 : 5, L = Array.isArray(lumieres) ? lumieres : [];
  const rang = { cle: 0, appoint: 1, contre: 2, fenetre: 3, neon: 4 };
  const reelles = L.map((l, i) => ({ l, i })).filter((x) => x.l.type !== "ambiance" && x.l.intensite > 0)
    .sort((a, b) => (rang[a.l.type] - rang[b.l.type]) || (b.l.intensite - a.l.intensite) || (a.i - b.i));
  return new Set(reelles.slice(0, max).map((x) => x.i));
}

// ── cadrage : une image (iw × ih) qui COUVRE un cadre (l × h) -> {x, y, l, h} du dessin ──
export function couvrir(iw, ih, l, h) {
  const k = Math.max(l / Math.max(1, iw), h / Math.max(1, ih));
  return { x: (l - iw * k) / 2, y: (h - ih * k) / 2, l: iw * k, h: ih * k };
}

// le nom affiché d'un décor livré : la clé traduite si elle existe, sinon le nom du serveur
export function nomDecor(decor, T) {
  if (!decor) return "";
  if (decor.livre && typeof T === "function") {
    const cle = "studiov.livre." + String(decor.id).replace(/^livre-/, ""), t = T(cle);
    if (t && t !== cle) return t;
  }
  return decor.nom || decor.id || "";
}
