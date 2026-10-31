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
export const ORIGINES = ["clip", "meshy", "meshy-motion", "uthana", "import"];

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

/* ce qui empêche « Générer » : null si tout va bien, sinon la clé du message */
export function blocageTexte({ fiche, meshy, prompt, mode, occupe }) {
  if (!fiche || !fiche.job) return "anim.bloc_modele";
  if (!(fiche.rig && fiche.rig.rigge)) return "anim.bloc_rig";
  if (!meshy) return "anim.bloc_cle";
  if (mode !== "swift") return "anim.bloc_mode";
  if (!String(prompt || "").trim()) return "anim.bloc_prompt";
  if (String(prompt).length > 400) return "anim.bloc_long";
  if (occupe) return "anim.bloc_occupe";
  return null;
}

/* l'adresse de l'Établi, ouvert sur la même version (vidéo → mouvement Uthana, Godot, retouches) */
export const lienEtabli = (job, version) =>
  `/etabli/?job=${encodeURIComponent(job || "")}` + (version ? `&version=${encodeURIComponent(version)}` : "");
