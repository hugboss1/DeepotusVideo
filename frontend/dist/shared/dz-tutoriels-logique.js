// dz-tutoriels-logique.js — t319 (28/10/2026, lot D5) : la logique PURE (sans DOM) des tutoriels et des parcours
// partagés (plan docs/superpowers/plans/2026-10-28-t319-tutoriels.md). Jouée sous node par
// backend/tests/test_tutoriels_ecran.py. SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared.

export const MAX_MOTS = 25;
export const MAX_TITRE = 80;
export const MAX_PHRASE = 200;
const ECRAN = /^[a-z0-9_-]{1,40}$/;
const CADRE = /^\/(vectorlab|photolab|spritelab|tilelab|whatsapp)\/$/;
const SECTION = /^[a-z0-9_-]{1,40}$/;

// le nombre de mots d'une phrase (la fiche didactique en garde 25)
export function compterMots(s) {
  return typeof s === "string" ? s.split(/\s+/).filter(Boolean).length : 0;
}

// un texte saisi : borné, sans retour à la ligne (le serveur relit de toute façon)
export function borner(s, n) {
  return (typeof s === "string" ? s : "").replace(/\s+/g, " ").slice(0, n);
}

// l'étape en cours à l'instant t (ms) de la vidéo : la première dont l'intervalle [t0, t1] contient t ; sinon la
// dernière dont le geste (e.t) est passé ; sinon la première. Les t0 ne sont pas forcément croissants (import).
export function etapeA(etapes, t) {
  const l = etapes || [];
  const dans = l.findIndex((e) => e && Number.isFinite(e.t0) && Number.isFinite(e.t1) && e.t0 <= t && t <= e.t1);
  if (dans >= 0) return dans;
  let i = 0;
  l.forEach((e, k) => { if (e && Number.isFinite(e.t) && e.t <= t) i = k; });
  return i;
}

// le texte d'un objet {fr, en} dans la langue (repli sur l'autre langue)
export function dansLangue(v, lang) {
  if (!v || typeof v !== "object") return "";
  const a = typeof v[lang] === "string" ? v[lang] : "";
  const b = typeof v[lang === "en" ? "fr" : "en"] === "string" ? v[lang === "en" ? "fr" : "en"] : "";
  return a || b;
}

// L'action « Montrer » d'une étape, relue par LISTE BLANCHE avant d'aller au pointeur. Le serveur la construit déjà
// depuis le catalogue LOCAL (jamais depuis le fichier importé) ; ceci est une seconde garde : type « point » seulement,
// sélecteur et textes bornés, écran / cadre / section au gabarit. Tout le reste est retiré ; null si inutilisable.
export function actionSure(a) {
  if (!a || typeof a !== "object" || a.type !== "point") return null;
  if (typeof a.selecteur !== "string" || !a.selecteur || a.selecteur.length > 200) return null;
  const txt = (v, n) => (typeof v === "string" ? v.slice(0, n) : "");
  const texte = a.texte && typeof a.texte === "object" ? { fr: txt(a.texte.fr, 120), en: txt(a.texte.en, 120) } : null;
  return {
    type: "point",
    cible: txt(a.cible, 80),
    selecteur: a.selecteur,
    texte: texte && (texte.fr || texte.en) ? texte : null,
    libelle: typeof a.libelle === "string" && a.libelle.length <= 80 ? a.libelle : null,
    ecran: typeof a.ecran === "string" && ECRAN.test(a.ecran) ? a.ecran : null,
    cadre: typeof a.cadre === "string" && CADRE.test(a.cadre) ? a.cadre : null,
    reglages: typeof a.reglages === "string" && SECTION.test(a.reglages) ? a.reglages : null,
    partout: a.partout === true,
    fr: txt(a.fr, 60), en: txt(a.en, 60),
  };
}

// la fenêtre de lecture d'une étape dans la vidéo (secondes) : de t0 à t1 (+ 0,3 s), jamais vide
export function fenetreEtape(e) {
  const t0 = Math.max(0, (e && Number.isFinite(e.t0) ? e.t0 : 0) / 1000);
  const t1 = Math.max(t0 + 0.5, (e && Number.isFinite(e.t1) ? e.t1 : 0) / 1000 + 0.3);
  return { debut: t0, fin: t1 };
}

// « 1:05 » pour 65 000 ms
export function horloge(ms) {
  const s = Math.max(0, Math.floor((ms || 0) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
