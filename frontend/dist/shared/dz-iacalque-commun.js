// dz-iacalque-commun.js — t197 : la logique PURE commune aux deux panneaux « Image IA sur le calque » — celui du
// Vectorlab (frontend/vectorlab/js/mod-iacalque.js, t190) et celui du Photolab (frontend/photolab/js/mod-iacalque.js,
// t191). Les deux copies avaient déjà divergé (prix partiel, devis vide « gratuit », clavier gardé) ; une seule source
// désormais, que chaque lab adapte à son document et à ses clés de traduction.
//
// Module ES sans DOM ni window à l'import (bancs node des deux labs + frontend/shared/qa/iacalque_commun.test.mjs).
// Servi à l'identique depuis frontend/dist/shared/ (/shared/…), importé par « ../../shared/dz-iacalque-commun.js ».
//
// Les textes : chaque fonction qui parle reçoit `tr(role, vars)` — le lab y préfixe sa zone (« vectorlab.iacalque. »,
// « photolab.iacalque. ») et peut renommer un rôle. Rôles employés : prix_inconnu, prix_a_mesurer, prix_gratuit, prix,
// prix_partiel_image, prix_partiel, cle_absente, detour_modele, detour_cle, detour_cle_image, sujet_requis.

/* ── formats ── */
// les formats que /images/generate (et /api/photolab/calque/ia) accepte ; OpenAI et Nano Banana les traduisent
export const TAILLES = ["portrait_16_9", "portrait_4_3", "square_hd", "landscape_4_3", "landscape_16_9"];
// le rapport largeur / hauteur de chaque format
export const RAPPORTS = { portrait_16_9: 9 / 16, portrait_4_3: 3 / 4, square_hd: 1, landscape_4_3: 4 / 3, landscape_16_9: 16 / 9 };

// le format au rapport le plus PROCHE de w × h, en écart LOGARITHMIQUE |ln(r) − ln(rf)| : un portrait et le paysage
// symétrique sont à égale distance du carré (2:3 → portrait_4_3, 9:16 → portrait_16_9) ; dimensions illisibles → carré
export function formatPour(w, h) {
  w = +w; h = +h;
  if (!(w > 0 && h > 0)) return "square_hd";
  const lr = Math.log(w / h);
  let mieux = "square_hd", ecart = Infinity;
  for (const f of TAILLES) {
    const e = Math.abs(lr - Math.log(RAPPORTS[f]));
    if (e < ecart - 1e-12) { ecart = e; mieux = f; }
  }
  return mieux;
}

/* ── prix ── */
// le corps du devis serveur (POST /api/cost/estimate) : une campagne image (si `image`) + détourage (si demandé et
// choisi). Sans modèle d'image (quand une image est à générer) ou sans aucune ligne, AUCUN devis plutôt qu'un prix
// faux : null → « Prix estimé : … ».
export function devisCorps({ image = true, modele = "", detourer = false, modeleDetour = "" } = {}) {
  const ops = [];
  if (image) {
    if (!modele) return null;
    ops.push({ kind: "image", model: String(modele), n: 1 });
  }
  if (detourer && modeleDetour) ops.push({ kind: "detourage", modele: String(modeleDetour), images: 1 });
  return ops.length ? { kind: "campaign", ops } : null;
}

// le montant en dollars : DzModelesIA.prixUsd (/shared/dz-modeles-ia.js, chargé par les deux pages — la même ligne
// de code que les listes de modèles) ; sans le script (banc nu), la même règle : arrondi au millième, au moins deux
// décimales (le banc commun vérifie l'égalité des deux)
export function dollars(v) {
  const M = globalThis.DzModelesIA;
  const p = M && typeof M.prixUsd === "function" ? M.prixUsd(v) : "";
  if (p) return p;
  let s = (Math.round(v * 1000) / 1000).toFixed(3);
  while (/\.\d{3,}$/.test(s) && s.endsWith("0")) s = s.slice(0, -1);
  return "$" + s;
}

// le libellé du prix d'après le devis : jamais « gratuit » pour un 0 $ payant (« à mesurer ») — une ligne LOCALE à
// 0 $ l'est ; un devis sans aucune ligne est « à mesurer ». Un total partiel NOMME la ligne à mesurer : l'image (unité
// « image ») ou le détourage (les autres unités)
export function libellePrix(devis, tr) {
  if (!devis || !Array.isArray(devis.breakdown)) return tr("prix_inconnu");
  const total = +devis.total_usd || 0;
  const aMesurer = devis.breakdown.filter((l) => !(+l.usd > 0) && l.provider !== "local");
  if (!(total > 0)) return devis.breakdown.length && !aMesurer.length ? tr("prix_gratuit") : tr("prix_a_mesurer");
  const image = aMesurer.some((l) => l.unit === "image"), detour = aMesurer.some((l) => l.unit !== "image");
  return tr("prix", { prix: dollars(total) }) + (image ? tr("prix_partiel_image") : "") + (detour ? tr("prix_partiel") : "");
}

/* ── refus ── */
// le message d'une réponse en échec : 503 = clé absente (le détail la nomme), un 402 refusé rend le message du
// plafond (detail chaîne ou {dz_plafond: {message}}) ; sans détail, `repli` (statusText) puis le code
export function messageErreur(statut, corps, repli, tr) {
  const det = corps && corps.detail;
  const m = typeof det === "string" ? det
    : det && det.dz_plafond && det.dz_plafond.message ? det.dz_plafond.message
      : det ? JSON.stringify(det) : (repli || String(statut));
  return statut === 503 ? tr("cle_absente", { detail: m }) : m;
}

// le détourage demandé est complet AVANT toute dépense : un modèle, sa clé (l'option sans clé reste CHOISISSABLE,
// seul le lancement est refusé — ici, quand le catalogue dit dispo:false) et le sujet si le modèle l'exige. `info` =
// l'entrée du catalogue detourage_image ({dispo, cle, prompt}), null si inconnue. `sansCase` : un bouton seul (pas de
// case « Retirer le fond » à décocher) — le message ne la propose pas.
export function verifierDetour(o, info, tr, { sansCase = false } = {}) {
  if (!o || !o.detourer) return;
  if (!o.modeleDetour) throw new Error(tr("detour_modele"));
  if (info && info.dispo === false) throw new Error(tr(sansCase ? "detour_cle_image" : "detour_cle", { cle: info.cle || "?" }));
  if (info && info.prompt && !String(o.sujet || "").trim()) throw new Error(tr("sujet_requis"));
}

/* ── tir ── */
// UN SEUL tir à la fois : un second appel pendant le vol ne relance rien (rend null) ; `apres` (facultatif) est
// rappelé une fois le vol fini, réussi ou non — l'appelant y redessine ses boutons (« en cours… » ne reste jamais)
export function unSeulVol(fn, apres) {
  const g = async (...a) => {
    if (g.enVol) return null;
    g.enVol = true;
    try { return await fn(...a); } finally {
      g.enVol = false;
      if (apres) { try { apres(); } catch (e) { /* le redessin n'efface pas l'issue du tir */ } }
    }
  };
  g.enVol = false;
  return g;
}

/* ── gestes ── */
// les gestes qui COMMENCENT quelque chose, arrêtés au panneau (en bulle : ses propres écouteurs ont déjà joué) : le
// clic (un outil ne démarre pas sous le panneau), la molette (pas de zoom), le CLAVIER enfoncé (les raccourcis globaux
// n'ignorent que les champs de saisie — sur un bouton du panneau, une lettre changeait d'outil). JAMAIS un relâchement
// (keyup, pointerup) : Espace enfoncé sur la scène puis relâché sur un bouton du panneau doit rendre la main
// (« espace » de core.js au Vectorlab, relacherMain de mod-vue au Photolab) — gardé, l'outil Main restait collé.
// Rien n'est preventDefault : la case, les listes et le texte gardent leur geste natif.
export const GESTES_GARDES = ["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel", "keydown"];
export function garderGestes(el) {
  for (const t of GESTES_GARDES) el.addEventListener(t, (ev) => ev.stopPropagation(), t === "wheel" ? { passive: true } : false);
}
