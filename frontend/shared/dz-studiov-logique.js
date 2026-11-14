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
export const TYPES = ["bureau", "table", "table_ronde", "pupitre", "etabli", "bureau_angle", "table_basse",
  "console", "comptoir", "chaise", "fauteuil", "canape", "banc", "chaise_bureau", "chaise_gaming", "tabouret",
  "pouf", "etagere", "bibliotheque", "vitrine", "casier", "etagere_murale", "cube_rangement", "meuble_tv",
  "ecran_bureau", "micro_bras", "micro_table", "casque", "softbox", "projecteur", "camera_pied",
  "panneau_acoustique", "enceinte", "table_mixage", "anneau_lumineux", "ordinateur_portable", "clavier", "tour_pc",
  "appareil_photo", "lampe", "lampadaire", "neon_barre", "neon_anneau", "guirlande", "tube_lumineux", "ruban_led",
  "ruban_led_sol", "panneau_hexa", "barre_led", "suspension", "applique", "lampe_coucher", "lampe_lave", "bougie",
  "neon_texte", "lettres_retro", "caisson_lumineux", "panneau_direct", "cadre", "horloge", "fenetre", "affiche",
  "miroir", "vinyle_mural", "mur_lattes", "panneau_perfore", "rideau", "plante", "cactus", "plante_tombante", "vase",
  "livres", "globe", "sablier", "cadre_photo", "tasse", "sculpture", "tapis", "colonne", "arche", "caisse",
  "paravent", "estrade", "imprimante3d", "bobine", "figurine", "boite_jeu", "plateau_jeu", "pion", "de", "manette",
  "borne_arcade", "console_jeu", "casque_vr", "guitare", "platine", "clap", "console_scifi", "hublot", "hologramme",
  "nuage", "arbre_cartoon", "champignon", "etoile", "but_foot", "ballon_foot", "gradin", "tableau_tactique",
  "fanion", "maillot", "echarpe", "crampons", "plot", "panier_basket", "ballon_basket", "ballon_ovale", "batte",
  "casque_foot_us", "raquette", "balle_tennis", "haltere", "gant_boxe", "skateboard", "trophee", "coupe", "medaille",
  "plaque_createur", "modele", "tableau", "logo_mural", "kakemono"];

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

// ── SVH : l'habillage (le décorateur). Tout est PUR : une recette entre, une recette NEUVE sort ; le serveur
// (studiov.normaliser) reste seul juge de ce qui s'enregistre. ──
export const USAGES = ["sol", "mur", "plafond", "bois", "tissu", "cuir", "metal", "pierre", "plastique", "autre"];
const copie = (x) => JSON.parse(JSON.stringify(x));

// l'usage d'une matière de la recette : sa place dans la pièce d'abord, puis ce qu'elle déclare, puis ce que son
// motif ou son nom laissent deviner (recettes d'avant le lot SVH)
export function usageDe(decor, cle) {
  const P = (decor && decor.piece) || {}, m = (decor && decor.matieres && decor.matieres[cle]) || {};
  if (cle === P.sol) return "sol";
  if (cle === P.mur || cle === P.fond || cle === P.gauche || cle === P.droite) return "mur";
  if (cle === P.plafond) return "plafond";
  if (m.usage && m.usage !== "autre") return m.usage;
  if (m.motif === "bois" || m.motif === "parquet" || m.motif === "lattes" || /bois|chene|noyer/.test(cle)) return "bois";
  if (/cuir/.test(cle)) return "cuir";
  if (m.motif === "tissu" || /tissu|feutre|mousse|velours|laine/.test(cle)) return "tissu";
  if (m.motif === "metal" || m.metal >= 0.5 || /acier|alu|metal|coque|casier|chrome/.test(cle)) return "metal";
  return "autre";
}

// la répétition d'une texture : `taille` mètres par carreau, multipliés par l'échelle choisie
export const repetition = (taille, echelle) => 1 / (borne(Number(taille) || 1, 0.05, 50) * borne(Number(echelle) || 1, 0.1, 10));

// pose une matière du catalogue (ou une finition) sur une clé de la recette, sans toucher à son usage ni à sa lueur
export function poserMatiere(decor, cle, spec) {
  const d = copie(decor), m = d.matieres[cle], S = spec || {};
  if (!m) return d;
  const texture = typeof S.texture === "string" ? S.texture : "";
  d.matieres[cle] = { ...m, texture, teinte: !!S.teinte && !!texture,
    couleur: S.couleur != null ? S.couleur : m.couleur,
    rugosite: S.rugosite != null ? S.rugosite : (texture ? 0.8 : m.rugosite),
    metal: S.metal != null ? S.metal : (texture ? 0 : m.metal),
    motif: texture ? "uni" : (S.motif || (S.couleur != null ? "uni" : m.motif)), echelle: S.echelle != null ? S.echelle : 1 };
  return d;
}

// une ambiance lumineuse : la clé, l'appoint et le premier contre prennent leur couleur ; les autres contres, les
// néons et les objets lumineux se partagent les couleurs de `neons` à tour de rôle ; l'enseigne prend la première
export function appliquerAmbiance(decor, A, lumineux) {
  const d = copie(decor), N = (A && Array.isArray(A.neons) && A.neons.length ? A.neons : ["principale", "accent"]);
  if (!A) return d;
  let k = 0, contres = 0;
  for (const l of d.lumieres) {
    if (l.type === "cle" || l.type === "fenetre") l.couleur = A.cle || l.couleur;
    else if (l.type === "appoint") l.couleur = A.appoint || l.couleur;
    else if (l.type === "ambiance") l.couleur = A.ambiance || l.couleur;
    else if (l.type === "contre") l.couleur = contres++ === 0 ? (A.contre || N[0]) : N[k++ % N.length];
    else if (l.type === "neon") l.couleur = N[k++ % N.length];
  }
  const L = new Set(lumineux || []);
  for (const o of d.objets) if (L.has(o.type)) o.couleur = N[k++ % N.length];
  if (d.enseigne && d.enseigne.style !== "panneau") d.enseigne.couleur = N[0];
  return d;
}

// un style complet : une matière par usage, puis son ambiance. Une matière lumineuse (émission) garde sa lueur.
export function appliquerStyle(decor, style, ambiances, lumineux) {
  let d = copie(decor);
  const M = (style && style.matieres) || {};
  for (const cle of Object.keys(d.matieres)) {
    const spec = M[usageDe(d, cle)];
    if (!spec || d.matieres[cle].emission > 0) continue;
    d = poserMatiere(d, cle, { rugosite: 0.8, metal: 0, ...spec });
  }
  const A = (ambiances || []).find((a) => a.id === (style && style.ambiance));
  return A ? appliquerAmbiance(d, A, lumineux) : d;
}

// un objet neuf du catalogue, posé devant le présentateur (au sol) ou sur le mur du fond (objets muraux)
export const MURAUX = ["cadre", "horloge", "fenetre", "affiche", "miroir", "vinyle_mural", "mur_lattes", "panneau_perfore",
  "panneau_acoustique", "neon_barre", "neon_anneau", "guirlande", "ruban_led", "panneau_hexa", "applique", "lampe_coucher",
  "neon_texte", "lettres_retro", "caisson_lumineux", "panneau_direct", "etagere_murale", "guitare", "echarpe", "medaille",
  "plaque_createur", "maillot", "raquette", "skateboard", "hublot", "nuage", "etoile", "tableau", "logo_mural"];
// SVB : les objets qui montrent une image de la Bibliothèque de l'application (champ `image`)
export const TYPES_IMAGE = ["tableau", "logo_mural", "kakemono"];
export function objetNeuf(decor, type, ref) {
  const P = (decor && decor.piece) || { l: 6, p: 5, h: 2.8 }, n = ((decor && decor.objets) || []).length;
  const dx = ((n % 5) - 2) * 0.45;
  if (type === "suspension") return { type, x: dx, y: P.h, z: -0.6, ry: 0, e: 1 };
  if (type === "modele") return { type, x: dx, y: 0, z: 0.9, ry: 0, e: 1, ref };
  if (type === "kakemono") return { type, x: borne(dx * 3 + 1.8, -P.l / 2 + 0.5, P.l / 2 - 0.5), y: 0, z: -P.p / 2 + 0.7, ry: 0, e: 1, image: ref };
  if (TYPES_IMAGE.indexOf(type) >= 0) return { type, x: borne(dx * 2, -P.l / 2 + 0.6, P.l / 2 - 0.6), y: 1.6, z: -P.p / 2 + 0.02, ry: 0, e: 1, image: ref };
  if (MURAUX.indexOf(type) >= 0) return { type, x: borne(dx * 2, -P.l / 2 + 0.6, P.l / 2 - 0.6), y: type === "mur_lattes" ? 1.2 : 1.6, z: -P.p / 2 + 0.02, ry: 0, e: 1 };
  return { type, x: dx, y: 0, z: 0.9, ry: 0, e: 1 };
}

// ── SVA : l'atelier du décor (vue en plan, choix au clic). Tout est PUR, joué sous node par le banc. ──
export const PANS = ["sol", "fond", "gauche", "droite", "plafond"];          // les cinq surfaces de la pièce

// qui emploie une matière de la recette : les pans de la pièce et les objets (matière et piètement)
export function emplois(decor, cle) {
  const P = decor.piece || {}, out = [];
  for (const pan of PANS) if (P[pan] === cle) out.push("pan:" + pan);
  if (P.mur === cle) out.push("pan:mur");
  (decor.objets || []).forEach((o, i) => { if (o.matiere === cle) out.push("objet:" + i + ":1"); if (o.matiere2 === cle) out.push("objet:" + i + ":2"); });
  return out;
}
function cleLibre(decor, base) {
  let cle = base, i = 2;
  while (decor.matieres[cle]) cle = base + i++;
  return cle;
}
const NEUTRE = { couleur: "#808890", rugosite: 0.8, metal: 0, emission: 0, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "autre" };
// la clé qu'on peut modifier SANS toucher au reste : celle du pan si lui seul l'emploie, sinon une copie à son nom.
// MODIFIE `decor` (l'appelant lui passe une copie) et rend la clé.
export function clePan(decor, pan) {
  const P = decor.piece, cle = P[pan] || P.mur, autres = emplois(decor, cle).filter((e) => e !== "pan:" + pan && e !== "pan:mur");
  if (decor.matieres[cle] && !autres.length) return cle;
  const neuve = cleLibre(decor, pan === "sol" || pan === "plafond" ? pan + "_2" : pan);
  decor.matieres[neuve] = { ...(decor.matieres[cle] || NEUTRE) };
  P[pan] = neuve;
  return neuve;
}
// idem pour un objet : sa matière (rang 1) ou son piètement (rang 2)
export function cleObjet(decor, index, rang) {
  const o = decor.objets[index], champ = rang === 2 ? "matiere2" : "matiere";
  if (!o) return null;
  const cle = o[champ], moi = "objet:" + index + ":" + (rang === 2 ? 2 : 1);
  if (cle && decor.matieres[cle] && emplois(decor, cle).every((e) => e === moi)) return cle;
  const neuve = cleLibre(decor, "objet_" + (index + 1) + (rang === 2 ? "b" : ""));
  decor.matieres[neuve] = { ...(decor.matieres[cle] || NEUTRE), usage: (decor.matieres[cle] || {}).usage || "autre" };
  if (!cle && o.couleur) decor.matieres[neuve].couleur = o.couleur;
  o[champ] = neuve;
  return neuve;
}
// ôte les matières que plus rien n'emploie (les trois de base restent : le serveur les recrée de toute façon)
export function nettoyerMatieres(decor) {
  const d = JSON.parse(JSON.stringify(decor));
  for (const cle of Object.keys(d.matieres)) if (["sol", "mur", "plafond"].indexOf(cle) < 0 && !emplois(d, cle).length) delete d.matieres[cle];
  return d;
}

// ── la vue en plan : on regarde le décor d'en haut ; x vers la droite, z vers le bas (la caméra est en bas) ──
export const aimanter = (v, pas) => (pas > 0 ? Math.round(v / pas) * pas : v);
// le rectangle de terrain à montrer (mètres) : la pièce, ce qui la filme et ce qui l'éclaire, avec une marge
export function cadrePlan(decor) {
  const P = decor.piece, b = { x0: -P.l / 2, x1: P.l / 2, z0: -P.p / 2, z1: P.p / 2 };
  const voir = (x, z) => { b.x0 = Math.min(b.x0, x); b.x1 = Math.max(b.x1, x); b.z0 = Math.min(b.z0, z); b.z1 = Math.max(b.z1, z); };
  for (const c of decor.cameras || []) voir(c.x, c.z);
  for (const l of decor.lumieres || []) if (l.type !== "ambiance") voir(l.x, l.z);
  for (const o of decor.objets || []) voir(o.x, o.z);
  const m = 0.6;
  return { x0: b.x0 - m, x1: b.x1 + m, z0: b.z0 - m, z1: b.z1 + m };
}
// l'échelle qui fait tenir ce cadre dans une toile de L × H pixels, centré
export function echellePlan(cadre, L, H) {
  const k = Math.min(L / (cadre.x1 - cadre.x0), H / (cadre.z1 - cadre.z0));
  const ox = (L - (cadre.x1 - cadre.x0) * k) / 2 - cadre.x0 * k, oy = (H - (cadre.z1 - cadre.z0) * k) / 2 - cadre.z0 * k;
  return { k, ox, oy, vers: (x, z) => [x * k + ox, z * k + oy], depuis: (px, py) => [(px - ox) / k, (py - oy) / k] };
}
// un point du repère d'un objet (tourné de ry degrés autour de la verticale) dans le repère de la pièce
export function tourner(x, z, ry) {
  const a = ((Number(ry) || 0) * Math.PI) / 180, c = Math.cos(a), s2 = Math.sin(a);
  return [x * c + z * s2, -x * s2 + z * c];
}
const MINI = 0.14;                             // un objet minuscule garde une prise de 14 cm de côté sur le plan
// les quatre coins (mètres, repère de la pièce) de l'emprise d'un objet ; sans emprise connue : un carré de 40 cm
export function coinsObjet(o, emp) {
  let e = emp || { x0: -0.2, x1: 0.2, z0: -0.2, z1: 0.2 };
  if (e.x1 - e.x0 < MINI) { const c = (e.x0 + e.x1) / 2; e = { ...e, x0: c - MINI / 2, x1: c + MINI / 2 }; }
  if (e.z1 - e.z0 < MINI) { const c = (e.z0 + e.z1) / 2; e = { ...e, z0: c - MINI / 2, z1: c + MINI / 2 }; }
  return [[e.x0, e.z0], [e.x1, e.z0], [e.x1, e.z1], [e.x0, e.z1]].map(([x, z]) => { const [rx, rz] = tourner(x, z, o.ry); return [o.x + rx, o.z + rz]; });
}
export function dansPolygone(x, z, coins) {
  let dedans = false;
  for (let i = 0, j = coins.length - 1; i < coins.length; j = i++) {
    const [xi, zi] = coins[i], [xj, zj] = coins[j];
    if ((zi > z) !== (zj > z) && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) dedans = !dedans;
  }
  return dedans;
}
// le cône d'une caméra vu d'en haut : sa pointe et les deux bords de son champ horizontal (image 16:9), à `portee` mètres
export function coneCamera(cam, portee) {
  const demi = Math.atan(Math.tan((champ(cam.focale) * Math.PI) / 360) * (16 / 9));
  const dx = cam.vers[0] - cam.x, dz = cam.vers[2] - cam.z, a = Math.atan2(dx, dz), r = portee || Math.hypot(dx, dz) || 2;
  return [[cam.x, cam.z], [cam.x + Math.sin(a - demi) * r / Math.cos(demi), cam.z + Math.cos(a - demi) * r / Math.cos(demi)],
    [cam.x + Math.sin(a + demi) * r / Math.cos(demi), cam.z + Math.cos(a + demi) * r / Math.cos(demi)]];
}
// un objet mural suit le mur le plus proche : il s'y colle (2 cm) et lui tourne le dos
export function collerAuMur(o, piece) {
  const P = piece, d = [["fond", Math.abs(o.z + P.p / 2)], ["gauche", Math.abs(o.x + P.l / 2)], ["droite", Math.abs(o.x - P.l / 2)]];
  if (P.ouvert) d.length = 1;
  d.sort((p, q) => p[1] - q[1]);
  const mur = d[0][0], out = { ...o };
  if (mur === "fond") { out.z = -P.p / 2 + 0.02; out.ry = 0; out.x = borne(o.x, -P.l / 2 + 0.05, P.l / 2 - 0.05); }
  else if (mur === "gauche") { out.x = -P.l / 2 + 0.02; out.ry = 90; out.z = borne(o.z, -P.p / 2 + 0.05, P.p / 2 + 2); }
  else { out.x = P.l / 2 - 0.02; out.ry = -90; out.z = borne(o.z, -P.p / 2 + 0.05, P.p / 2 + 2); }
  return out;
}
// ce qu'on touche sur le plan au point (x, z), à `tol` mètres près : les repères d'abord (caméras, lumières,
// présentateur), puis l'objet le plus haut dans la liste (le dernier posé), puis un écran
export function toucherPlan(decor, emps, x, z, tol) {
  const pres = (px, pz, r) => Math.hypot(px - x, pz - z) <= r;
  const C = decor.cameras || [], L = decor.lumieres || [], O2 = decor.objets || [], E = decor.ecrans || [];
  for (let i = C.length - 1; i >= 0; i--) if (pres(C[i].x, C[i].z, tol)) return { genre: "camera", index: i };
  for (let i = L.length - 1; i >= 0; i--) if (L[i].type !== "ambiance" && pres(L[i].x, L[i].z, tol)) return { genre: "lumiere", index: i };
  const R = decor.presentateur;
  if (R && pres(R.x, R.z, Math.max(tol, 0.22))) return { genre: "presentateur", index: 0 };
  for (let i = O2.length - 1; i >= 0; i--) if (dansPolygone(x, z, coinsObjet(O2[i], emps && emps[i]))) return { genre: "objet", index: i };
  for (let i = E.length - 1; i >= 0; i--) {
    const [dx, dz] = tourner(x - E[i].x, z - E[i].z, -E[i].ry);
    if (Math.abs(dx) <= E[i].l / 2 && Math.abs(dz) <= Math.max(tol, 0.1)) return { genre: "ecran", index: i };
  }
  const S2 = decor.enseigne;
  if (S2 && S2.actif && pres(S2.x, S2.z, Math.max(tol, 0.15))) return { genre: "enseigne", index: 0 };
  return null;
}
// une caméra de plus (copie décalée de la première) ; une lumière de plus, posée devant le présentateur
export function cameraNeuve(decor) {
  const c = JSON.parse(JSON.stringify((decor.cameras || [])[0] || { x: 0, y: 1.4, z: 3.2, vers: [0, 1.2, 0], focale: 35 }));
  return { ...c, nom: "Caméra " + ((decor.cameras || []).length + 1), x: Math.round((c.x + 1.2) * 100) / 100, mouvement: "fixe", amplitude: 0, periode_s: 10 };
}
export function lumiereNeuve(decor, type) {
  const P = decor.piece;
  if (type === "neon") return { type: "neon", couleur: "principale", intensite: 3, x: 0, y: P.h - 0.25, z: -P.p / 2 + 0.06, vers: [0, 1.2, 0], l: Math.min(4, P.l - 2), h: 0.05, ry: 90 };
  return { type: type === "contre" ? "contre" : "appoint", couleur: "#ffffff", intensite: 1.5, x: type === "contre" ? -1.4 : 1.6, y: Math.min(P.h - 0.2, 2.2),
    z: type === "contre" ? -1.4 : 2.0, vers: [0, 1.2, 0], l: 1, h: 0.05, ry: 0 };
}
