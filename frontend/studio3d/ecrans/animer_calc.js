/* t398 + t399 (31/10/2026) — le CALCUL de l'écran Animer du 3D Studio, sans DOM ni three.js : il tourne sous node
   (banc qa/animer.test.mjs). animer.js ne fait que traduire ces décisions en éléments et en gestes three.js.

   - la liste « Générés » : clips de la version ouverte (jouables tels quels), clips Meshy rapatriés (jouables en
     chargeant leur GLB, le rig étant le même), mouvements rangés dans le job (BVH/GLB : à appliquer d'abord) ;
   - le catalogue : pagination compacte, clés des catégories et sous-catégories ;
   - les vues P/F/B/L/R/T sur les orientations de /lib3d/viewer.js (libre, face, profil, dessus) + un miroir ;
   - le MODE CONDUITE : touches PHYSIQUES (`event.code`) — KeyW/KeyA/KeyS/KeyD sont Z/Q/S/D sur un clavier AZERTY —
     et flèches ; avancer et tourner sur le sol, sans physique ;
   - la saisie du texte → mouvement : durée bornée au pas de 0,5 s, devis lisible. */
"use strict";

export const T = (k, v) => (typeof globalThis.dzT === "function" ? globalThis.dzT("studio3decrans." + k, v) : k);
export const langue = () => (typeof globalThis.dzLang === "function" && globalThis.dzLang() === "en" ? "en" : "fr");

/* ── la liste « Générés » ─────────────────────────────────────────────────── */

/* les origines d'un mouvement, telles que mouvement_rig les range (fiche `origine`) */
export const ORIGINES = ["clip", "meshy", "meshy-motion", "hy-motion", "uthana", "import"];

/* Fusionne l'état de /api/etabli/mouvement (clips de la version, sources du job) en une liste unique.
   `jouable` : le clip vit dans la version (ou dans un GLB Meshy du même rig) ; sinon il faut l'appliquer (reciblage). */
export function listeGeneres(etat, job) {
  if (!etat) return [];
  const out = [];
  const vus = new Set();
  for (const c of etat.clips || []) {
    const cle = "clip:" + c.nom;
    if (vus.has(cle)) continue;
    vus.add(cle);
    out.push({ cle, type: "clip", nom: c.nom, origine: "clip", jouable: true, url: null });
  }
  for (const s of etat.sources || []) {
    const cle = s.type + ":" + s.nom;
    if (vus.has(cle)) continue;
    vus.add(cle);
    const meshy = s.type === "meshy";
    out.push({
      cle, type: s.type, nom: s.nom, origine: ORIGINES.includes(s.origine) ? s.origine : "import",
      jouable: meshy, secondes: s.secondes ?? null, format: s.format || null,
      url: meshy && job ? `/api/assets/3d/${encodeURIComponent(job)}/animation/${encodeURIComponent(s.nom)}` : null,
    });
  }
  return out;
}

/* le clip de marche à boucler en mode conduite : un nom qui dit marcher, sinon courir, sinon le premier jouable */
export function choisirMarche(clips) {
  const j = (clips || []).filter((c) => c && c.jouable !== false);
  return j.find((c) => /walk|marche|march/i.test(c.nom)) || j.find((c) => /run|course|cour/i.test(c.nom)) || j[0] || null;
}

/* ── le catalogue ─────────────────────────────────────────────────────────── */

export const cleCategorie = (id) => "anim.cat_" + String(id || "").toLowerCase();
export const cleSous = (id) => "anim.sous_" + String(id || "").toLowerCase();

/* la pagination compacte : 1 … 4 5 6 … 14 (au plus 7 éléments, « … » = null) */
export function pagesVisibles(page, pages) {
  const n = Math.max(1, pages | 0), p = Math.min(n, Math.max(1, page | 0));
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1);
  const out = [1];
  const a = Math.max(2, Math.min(p - 1, n - 4)), b = Math.min(n - 1, Math.max(p + 1, 5));
  if (a > 2) out.push(null);
  for (let i = a; i <= b; i++) out.push(i);
  if (b < n - 1) out.push(null);
  out.push(n);
  return out;
}

/* la requête du catalogue pour une vue de la colonne gauche : tous, favoris, ou une collection */
export function requeteCatalogue({ vue = "tous", collection = "", q = "", categorie = "", sous = "", page = 1, parPage = 40 } = {}) {
  const p = new URLSearchParams();
  if (vue === "favoris") p.set("vue", "favoris");
  else if (vue === "collection" && collection) { p.set("vue", "collection"); p.set("collection", collection); }
  if (q.trim()) p.set("q", q.trim());
  if (categorie) p.set("categorie", categorie);
  if (categorie && sous) p.set("sous_categorie", sous);
  p.set("page", String(Math.max(1, page | 0)));
  p.set("par_page", String(parPage));
  return "/api/studio3d/animer/catalogue?" + p.toString();
}

/* ── les vues de caméra ───────────────────────────────────────────────────── */

/* P perspective (libre), F face, B dos, L gauche, R droite, T dessus. Un personnage regarde +Z (glTF) : sa gauche est
   en +X, donc la vue « profil » du viewer (caméra en +X) montre son flanc GAUCHE ; B et R sont les miroirs. */
export const VUES = ["P", "F", "B", "L", "R", "T"];
export function vueCamera(id) {
  switch (id) {
    case "F": return { orientation: "face", miroir: false };
    case "B": return { orientation: "face", miroir: true };
    case "L": return { orientation: "profil", miroir: false };
    case "R": return { orientation: "profil", miroir: true };
    case "T": return { orientation: "dessus", miroir: false };
    default: return { orientation: "libre", miroir: false };
  }
}

/* le point miroir d'une caméra autour de sa cible (même distance, côté opposé) */
export function miroir(pos, cible) {
  return { x: 2 * cible.x - pos.x, y: pos.y, z: 2 * cible.z - pos.z };
}

/* ── le lecteur ───────────────────────────────────────────────────────────── */

export const VITESSES = [0.25, 0.5, 1, 1.5, 2];

/* le curseur 0..1000 ↔ secondes */
export const curseurVersTemps = (pos, duree) => (duree > 0 ? Math.min(duree, Math.max(0, (Number(pos) || 0) / 1000 * duree)) : 0);
export const tempsVersCurseur = (t, duree) => (duree > 0 ? Math.round(1000 * Math.min(1, Math.max(0, t / duree))) : 0);

/* « 1,25 s / 3,00 s » à la française, « 1.25 s / 3.00 s » à l'anglaise */
export function horloge(t, duree, lg = langue()) {
  const f = (x) => (Number.isFinite(x) ? x : 0).toFixed(2);
  const s = `${f(t)} s / ${f(duree)} s`;
  return lg === "en" ? s : s.replace(/\./g, ",");
}

/* ── le mode conduite ─────────────────────────────────────────────────────── */

/* touches PHYSIQUES : la rangée WASD du QWERTY est la rangée ZQSD de l'AZERTY ; les flèches aussi */
const TOUCHES = {
  KeyW: "avant", ArrowUp: "avant", KeyS: "arriere", ArrowDown: "arriere",
  KeyA: "gauche", ArrowLeft: "gauche", KeyD: "droite", ArrowRight: "droite",
};
export const actionDeTouche = (code) => TOUCHES[code] || null;

export const CONDUITE = { vitesse: 1.4, recul: 0.7, rotation: Math.PI * 0.9 };   // m/s, m/s, rad/s

/* Un pas de conduite : `etat` {x, z, cap} (cap en radians, 0 = regarde +Z), `actions` un Set d'actions enfoncées,
   `dt` en secondes, `echelle` = taille du personnage en mètres (1,7 pour un humain : la vitesse suit sa taille).
   Rend le nouvel état et `bouge` (pour boucler la marche ou s'arrêter). Sans physique : ni gravité ni collision. */
export function pasConduite(etat, actions, dt, echelle = 1.7, reglages = CONDUITE) {
  const a = actions instanceof Set ? actions : new Set(actions || []);
  const d = Math.min(0.1, Math.max(0, Number(dt) || 0));
  let { x = 0, z = 0, cap = 0 } = etat || {};
  const tourne = (a.has("gauche") ? 1 : 0) - (a.has("droite") ? 1 : 0);
  cap += tourne * reglages.rotation * d;
  const k = (Number(echelle) > 0 ? Number(echelle) : 1.7) / 1.7;
  const v = a.has("avant") && !a.has("arriere") ? reglages.vitesse * k : a.has("arriere") && !a.has("avant") ? -reglages.recul * k : 0;
  x += Math.sin(cap) * v * d;
  z += Math.cos(cap) * v * d;
  return { x, z, cap, bouge: v !== 0 || tourne !== 0, avance: v };
}

/* ── texte → mouvement ────────────────────────────────────────────────────── */

export const DUREE = { min: 2, max: 10, pas: 0.5 };

/* la durée ramenée dans les bornes et au pas de Meshy (2 à 10 s, par 0,5 s) */
export function bornerDuree(d, b = DUREE) {
  const n = Number(d);
  if (!Number.isFinite(n)) return b.min;
  return Math.min(b.max, Math.max(b.min, Math.round(n / b.pas) * b.pas));
}

/* le prix lisible d'un devis serveur (pricing.estimate) : « 3 crédits Meshy · ≈ 0,06 $ » */
export function prix(devis, lg = langue()) {
  if (!devis) return "";
  const cr = devis.credits && devis.credits.meshy != null ? Number(devis.credits.meshy) : null;
  const usd = Number(devis.total_usd || 0);
  const u = lg === "en" ? `$${usd.toFixed(2)}` : `${usd.toFixed(2).replace(".", ",")} $`;
  return cr != null ? T("anim.prix", { n: String(cr).replace(".", lg === "en" ? "." : ","), u }) : u;
}

/* t405 — HY-Motion (fal) : 0,5 à 12 s, guidance 1 à 10, derrière la case de licence */
export const DUREE_HY = { min: 0.5, max: 12, pas: 0.5 };
export const MODELES_HY = ["hy-motion", "hy-motion-fast"];
export const estHy = (m) => MODELES_HY.includes(m);
export const bornesDuree = (modele) => (estHy(modele) ? DUREE_HY : DUREE);

/* ce qui empêche « Générer » : null si tout va bien, sinon la clé du message. `modele` « meshy » (défaut) ou
   « hy-motion » / « hy-motion-fast » : alors la LICENCE puis la clé fal, à la place de la clé et du mode Meshy. */
export function blocageTexte({ fiche, meshy, fal, prompt, mode, modele = "meshy", licence, occupe }) {
  if (!fiche || !fiche.job) return "anim.bloc_modele";
  if (!(fiche.rig && fiche.rig.rigge)) return "anim.bloc_rig";
  if (estHy(modele)) {
    if (!licence) return "anim.bloc_licence";
    if (!fal) return "anim.bloc_cle_fal";
  } else {
    if (!meshy) return "anim.bloc_cle";
    if (mode !== "swift") return "anim.bloc_mode";
  }
  if (!String(prompt || "").trim()) return "anim.bloc_prompt";
  if (String(prompt).length > 400) return "anim.bloc_long";
  if (occupe) return "anim.bloc_occupe";
  return null;
}

/* l'adresse de l'Établi, ouvert sur la même version (vidéo → mouvement Uthana, Godot, retouches) */
export const lienEtabli = (job, version) =>
  `/etabli/?job=${encodeURIComponent(job || "")}` + (version ? `&version=${encodeURIComponent(version)}` : "");

/* le corps de POST /api/studio3d/animer/texte pour le modèle choisi (confirme_cout posé APRÈS le dialogue maison) */
export function corpsTexte({ fiche, modele = "meshy", mode = "swift", prompt = "", duree = 3, guidance = 5, licence = false }) {
  const base = { job: fiche && fiche.job, version: fiche && fiche.version, prompt: String(prompt).trim(),
    duree: bornerDuree(duree, bornesDuree(modele)) };
  if (estHy(modele)) return { ...base, modele, guidance: Math.min(10, Math.max(1, Number(guidance) || 5)), licence_acceptee: licence === true };
  return { ...base, modele: "meshy", mode };
}

/* ── petits vecteurs [x, y, z] (sans three.js : le banc node les éprouve) ── */

const sous = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const plus = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const fois = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const scal = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const longueur = (a) => Math.hypot(a[0], a[1], a[2]);
export const vectoriel = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export function unitaire(a) {
  const n = longueur(a);
  return n > 1e-12 ? fois(a, 1 / n) : [0, 0, 0];
}
export const distance = (a, b) => longueur(sous(a, b));

/* ── rôles des os (le même découpage que mouvement_rig.py, fonctions decouper et role) ── */

const PARASITES = new Set(["mixamorig", "bip01", "bip001", "bip", "def", "org", "mch", "jnt", "joint", "bone", "b", "j", "c",
  "armature", "ctrl", "bn"]);
const ALIAS = {
  bassin: ["hips", "hip", "pelvis"], cou: ["neck", "neck0", "neck1", "neck01", "neck2", "neck02"], tete: ["head"],
  epaule: ["shoulder", "clavicle", "collar", "collarbone"], bras: ["arm", "upperarm", "uparm", "humerus"],
  avantbras: ["forearm", "lowerarm", "lowarm", "elbow"], main: ["hand", "wrist"],
  cuisse: ["upleg", "thigh", "upperleg", "femur", "hip"], jambe: ["leg", "shin", "calf", "lowerleg", "lowleg", "knee"],
  pied: ["foot", "ankle"], orteil: ["toe", "toebase", "toes", "ball", "toe0", "toe01"],
};
const COLONNE = ["spine", "chest", "upperchest", "lowerback", "back", "torso", "abdomen"];

/* [côté « g » / « d » / null, base normalisée] d'un nom d'os */
export function decouperNom(nom) {
  let s = String(nom).replace(/^.*[:|]/, "");
  s = s.replace(/^([LR])([A-Z][a-z])/, "$1_$2").replace(/([a-z0-9])([A-Z])/g, "$1_$2");
  let cote = null;
  const reste = [];
  for (const t of s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)) {
    if (["left", "l", "lft"].includes(t)) cote = "g";
    else if (["right", "r", "rgt"].includes(t)) cote = "d";
    else if (!PARASITES.has(t)) reste.push(t);
  }
  let base = reste.join("");
  for (const [pre, c] of [["left", "g"], ["right", "d"]]) {
    if (base.startsWith(pre) && base.length > pre.length) { cote = c; base = base.slice(pre.length); }
  }
  return [cote, base];
}

export function roleOs(nom) {
  const [cote, base] = decouperNom(nom);
  if (cote === null && base === "hip") return "bassin";
  for (const [r, alias] of Object.entries(ALIAS)) {
    if (alias.includes(base)) {
      if (["bassin", "cou", "tete"].includes(r)) return cote === null ? r : null;
      return cote ? `${r}_${cote}` : null;
    }
  }
  if (cote === null && COLONNE.some((c) => base.startsWith(c))) return "colonne";
  return null;
}

/* {rôle → index} : pour chaque rôle, l'os le MOINS profond (liste de {nom, profondeur}) */
export function osParRole(os) {
  const out = {};
  (os || []).forEach((o, i) => {
    const r = roleOs(o.nom);
    if (r && (out[r] === undefined || (o.profondeur ?? 0) < (os[out[r]].profondeur ?? 0))) out[r] = i;
  });
  return out;
}

/* les chaînes que l'IK pilote : bras (bras → avant-bras → main) et jambes (cuisse → jambe → pied), ou null */
export function chaineIK(roles, membre, cote) {
  const [a, b, c] = membre === "bras" ? ["bras", "avantbras", "main"] : ["cuisse", "jambe", "pied"];
  const ids = [roles[`${a}_${cote}`], roles[`${b}_${cote}`], roles[`${c}_${cote}`]];
  return ids.every((x) => x !== undefined) ? ids : null;
}

/* les doigts d'une main : noms qui disent pouce, index, majeur, annulaire, auriculaire (ou finger) du côté voulu */
const DOIGTS = /thumb|index|middle|ring|pinky|little|finger|pouce|doigt/i;
export function doigtsDe(noms, cote) {
  const out = [];
  (noms || []).forEach((n, i) => {
    if (!DOIGTS.test(String(n))) return;
    const [c] = decouperNom(n);
    if (c === cote) out.push(i);
  });
  return out;
}
export function typeDoigt(nom) {
  const n = String(nom).toLowerCase();
  if (/thumb|pouce/.test(n)) return "pouce";
  if (/index/.test(n)) return "index";
  return "courbure";
}

/* ── la physique du viewport (aperçu gratuit) : os à ressort ─────────────────
   Jiggle : poitrine (breast, chest_l/r, jiggle) ; Hair : cheveux et queues (hair, ponytail, tail) ; Cloth : cape, jupe,
   tissu (cape, skirt, cloth). Un os n'appartient qu'à une famille (dans cet ordre). */
export const FAMILLES = ["jiggle", "hair", "cloth"];
const RX_FAMILLE = { hair: /hair|ponytail|tail/i, cloth: /cape|skirt|cloth/i };
export function familleOs(nom) {
  const [cote, base] = decouperNom(nom);
  if (/breast|jiggle/i.test(String(nom)) || (cote && base === "chest")) return "jiggle";
  for (const f of ["hair", "cloth"]) if (RX_FAMILLE[f].test(String(nom))) return f;
  return null;
}
export function classerPhysique(noms) {
  const out = { jiggle: [], hair: [], cloth: [] };
  (noms || []).forEach((n, i) => { const f = familleOs(n); if (f) out[f].push(i); });
  return out;
}

export const PHYSIQUE_DEFAUT = { raideur: 1, amortissement: 0.4, gravite: 0.3 };
export const PHYSIQUE_BORNES = { raideur: [0, 4, 0.05], amortissement: [0, 1, 0.01], gravite: [0, 2, 0.05] };
const K_RESSORT = 8;            // la poussée par seconde, en longueurs d'os, pour raideur = 1 (et gravité = 1)

/* Un pas de ressort (verlet amorti, à la manière des « spring bones » VRM) : la QUEUE de l'os garde son élan
   (amorti), est poussée vers sa direction de repos ANIMÉE (`cible` = la queue que l'animation pose) et tirée par la
   gravité (−Y monde), puis remise à la longueur de l'os autour de sa tête. Rend le nouvel état {queue, avant}. */
export function pasRessort(etat, tete, cible, r = PHYSIQUE_DEFAUT, dt = 1 / 60) {
  const L = distance(cible, tete);
  if (!etat || !etat.queue || !(L > 1e-9)) return { queue: cible.slice(), avant: cible.slice() };
  const d = Math.min(1 / 30, Math.max(0, Number(dt) || 0));
  const am = Math.min(1, Math.max(0, Number(r.amortissement) || 0));
  let n = plus(etat.queue, fois(sous(etat.queue, etat.avant), 1 - am));
  n = plus(n, fois(unitaire(sous(cible, tete)), (Number(r.raideur) || 0) * K_RESSORT * d * L));
  n = plus(n, [0, -(Number(r.gravite) || 0) * K_RESSORT * d * L, 0]);
  const dir = sous(n, tete);
  n = longueur(dir) > 1e-12 ? plus(tete, fois(unitaire(dir), L)) : cible.slice();
  return { queue: n, avant: etat.queue.slice() };
}

/* le réglage à télécharger (physics-config.json, comme Sorceress) */
export function configPhysique({ job = null, version = null, actifs = {}, reglages = PHYSIQUE_DEFAUT, os = {} } = {}) {
  return {
    format: "deepotus-physics-config", version_format: 1,
    modele: { job, version },
    methode: "spring-bone verlet: damped tail inertia, push toward the animated rest direction, gravity -Y, length kept",
    unites: { raideur: "bone lengths / s (x8)", amortissement: "0..1 per frame", gravite: "bone lengths / s (x8)" },
    reglages: { raideur: Number(reglages.raideur), amortissement: Number(reglages.amortissement), gravite: Number(reglages.gravite) },
    gravite_direction: [0, -1, 0],
    familles: Object.fromEntries(FAMILLES.map((f) => [f, { actif: !!actifs[f], os: (os[f] || []).slice() }])),
  };
}

/* ── IK à deux os (bras ou jambe), analytique ──────────────────────────────
   a = tête du premier os (épaule / hanche), b = articulation (coude / genou), c = bout (poignet / cheville), t = cible.
   Les longueurs sont gardées ; le pli reste dans le plan qu'avait le membre (sinon celui de `pole`). Hors de portée,
   le membre s'étend TOUT DROIT vers la cible. Rend {coude, bout, atteint}. */
export function ikDeuxOs(a, b, c, t, pole = [0, 0, -1]) {
  const L1 = distance(b, a), L2 = distance(c, b);
  const v = sous(t, a);
  let dist = longueur(v);
  const dir = dist > 1e-9 ? fois(v, 1 / dist) : unitaire(sous(c, a));
  if (dist >= L1 + L2 - 1e-9) {
    return { coude: plus(a, fois(dir, L1)), bout: plus(a, fois(dir, L1 + L2)), atteint: dist <= L1 + L2 + 1e-9 };
  }
  const mini = Math.abs(L1 - L2);
  const atteint = dist >= mini;
  dist = Math.max(dist, mini + 1e-9);
  const plan = (w) => sous(w, fois(dir, scal(w, dir)));
  let p = plan(sous(b, a));
  if (longueur(p) < 1e-6 * Math.max(L1, 1e-9)) p = plan(pole);
  if (longueur(p) < 1e-9) p = plan(Math.abs(dir[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]);
  p = unitaire(p);
  const cosA = Math.min(1, Math.max(-1, (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist)));
  const sinA = Math.sqrt(Math.max(0, 1 - cosA * cosA));
  return { coude: plus(a, plus(fois(dir, L1 * cosA), fois(p, L1 * sinA))), bout: plus(a, fois(dir, dist)), atteint };
}

/* ── prises (Gun / Sword / Hand) : la cible de la main dans le repère du personnage (pieds à l'origine, +X à sa
   gauche, +Y en haut, +Z devant), en fractions de sa taille, et la courbure des doigts (0 ouvert … 1 fermé) ── */
export const PRISES = {
  gun_g: { cote: "g", cible: [0.07, 0.78, 0.3], courbure: 0.75, index: 0.25, pouce: 0.35 },
  gun_d: { cote: "d", cible: [-0.07, 0.78, 0.3], courbure: 0.75, index: 0.25, pouce: 0.35 },
  main_g: { cote: "g", cible: null, courbure: 0, index: 0, pouce: 0 },
  main_d: { cote: "d", cible: null, courbure: 0, index: 0, pouce: 0 },
  epee_g: { cote: "g", cible: [0.2, 0.6, 0.18], courbure: 0.85, index: 0.85, pouce: 0.6 },
  epee_d: { cote: "d", cible: [-0.2, 0.6, 0.18], courbure: 0.85, index: 0.85, pouce: 0.6 },
};
export const ORDRE_PRISES = ["gun_g", "gun_d", "main_g", "main_d", "epee_g", "epee_d"];
export function prise(id, taille = 1.7) {
  const p = PRISES[id];
  if (!p) return null;
  return { ...p, id, cible: p.cible ? fois(p.cible, Number(taille) > 0 ? Number(taille) : 1.7) : null };
}
export const courbureDoigt = (nom, p) => (!p ? 0 : p[typeDoigt(nom)] ?? p.courbure);
export const ANGLE_DOIGT = 75;          // degrés par phalange à courbure 1

/* l'axe autour duquel une phalange se replie : `haut` (le dessus de la main) × direction du doigt — une rotation
   POSITIVE autour de lui amène le doigt vers le dessous de la main (la paume d'une main en T, paume en bas) */
export const axeCourbure = (doigt, haut) => unitaire(vectoriel(haut, doigt));
