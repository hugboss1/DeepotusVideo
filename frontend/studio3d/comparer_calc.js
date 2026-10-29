/* t344 (lot Scenario B9, 29/10/2026) — le CALCUL de l'écran « Comparer les moteurs », sans DOM ni three.js : il tourne
   sous node (banc qa/comparer.test.mjs). Les mesures viennent du serveur (fiche de maillage) : ce module les TRIE, les
   met en forme et dit, colonne par colonne, quelle ligne est la meilleure — il n'invente aucune valeur. */
"use strict";

export const T = (k, v) => (typeof globalThis.dzT === "function" ? globalThis.dzT("comparatif3d." + k, v) : k);
export const langue = () => (typeof globalThis.dzLang === "function" && globalThis.dzLang() === "en" ? "en" : "fr");

/* les colonnes du tableau, dans l'ordre ; `mieux` : le sens qui gagne (null = colonne sans « meilleur ») */
export const COLONNES = [
  { cle: "moteur", titre: () => T("col.moteur"), mieux: null },
  { cle: "tris", titre: () => T("col.tris"), mieux: "bas" },
  { cle: "aretes_bord", titre: () => T("col.bord"), mieux: "bas" },
  { cle: "aretes_non_manifold", titre: () => T("col.nonmanifold"), mieux: "bas" },
  { cle: "octets", titre: () => T("col.taille"), mieux: "bas" },
  { cle: "duree_s", titre: () => T("col.temps"), mieux: "bas" },
  { cle: "usd_estime", titre: () => T("col.estime"), mieux: "bas" },
  { cle: "usd_reel", titre: () => T("col.reel"), mieux: "bas" },
];

/* tri stable ; une valeur inconnue (null) va TOUJOURS en dernier, dans les deux sens — comme le serveur */
export function trier(lignes, cle, desc = false) {
  const val = (l) => (cle === "moteur" ? String(l.label || l.moteur || "") : l[cle]);
  const connus = lignes.filter((l) => val(l) != null), inconnus = lignes.filter((l) => val(l) == null);
  const cmp = (a, b) => {
    const x = val(a), y = val(b);
    const r = typeof x === "string" ? x.localeCompare(y) : x - y;
    return desc ? -r : r;
  };
  return connus.map((l, i) => [l, i]).sort((a, b) => cmp(a[0], b[0]) || a[1] - b[1]).map((p) => p[0]).concat(inconnus);
}

/* la meilleure valeur d'une colonne parmi les lignes TERMINÉES — null s'il y en a moins de deux à comparer */
export function meilleur(lignes, cle) {
  const col = COLONNES.find((c) => c.cle === cle);
  if (!col || !col.mieux) return null;
  const v = lignes.filter((l) => l.statut === "termine" && l[cle] != null).map((l) => l[cle]);
  if (v.length < 2) return null;
  const m = col.mieux === "bas" ? Math.min(...v) : Math.max(...v);
  return v.every((x) => x === m) ? null : m;
}

export function nb(n) { return n == null ? "—" : Number(n).toLocaleString(langue() === "en" ? "en-US" : "fr-FR"); }
export function usd(v) {
  if (v == null) return "—";
  const s = Number(v).toFixed(2);
  return langue() === "en" ? `$${s}` : `${s.replace(".", ",")} $`;
}
export function taille(o) {
  if (o == null) return "—";
  return o >= 1048576 ? `${(o / 1048576).toFixed(1)} ${T("unite.mo")}` : `${Math.max(1, Math.round(o / 1024))} ${T("unite.ko")}`;
}
export function duree(s) {
  if (s == null) return "—";
  return s >= 60 ? `${Math.floor(s / 60)} min ${String(Math.round(s % 60)).padStart(2, "0")} s` : `${Math.round(s)} s`;
}

/* le texte d'une cellule */
export function cellule(l, cle) {
  if (cle === "moteur") return l.label || l.moteur;
  if (cle === "octets") return taille(l.octets);
  if (cle === "duree_s") return duree(l.duree_s);
  if (cle === "usd_estime") return usd(l.usd_estime);
  if (cle === "usd_reel") return l.usd_reel == null ? T("reel.non_rapproche") : usd(l.usd_reel);
  return nb(l[cle]);
}

/* le total à payer AVANT le tir : celui du devis du serveur pour les moteurs cochés (jamais recalculé ici) */
export function totalCoches(devis, coches) {
  const s = new Set(coches);
  return Math.round((devis.lignes || []).filter((l) => s.has(l.moteur)).reduce((a, l) => a + Number(l.usd || 0), 0) * 1e4) / 1e4;
}

/* la phrase de clé d'un moteur : « clé fal à ajouter dans Réglages » ; il reste choisissable */
export function avisCle(l) {
  if (l.cle_ok !== false) return "";
  return l.cle === "local" ? T("cle.local") : T("cle.fal");
}

/* les modèles existants regroupés par image source (le plus utile : même image, moteurs différents) */
export function grouperParImage(modeles) {
  const g = new Map();
  for (const m of modeles) {
    const k = m.image_filename || "";
    if (!g.has(k)) g.set(k, []);
    g.get(k).push(m);
  }
  return [...g.entries()].sort((a, b) => (b[1].length - a[1].length) || a[0].localeCompare(b[0]));
}
