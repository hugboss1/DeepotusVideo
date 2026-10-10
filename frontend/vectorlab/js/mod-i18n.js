// mod-i18n.js — t146 (traduction L6) : T(clé, vars), le texte du Vectorlab dans la langue de l'interface.
// Dans la page, c'est le dzT du runtime /shared/dz-i18n.js (chargé AVANT les modules, langue choisie à
// l'installation ou dans les Réglages). Sous node (bancs qa/, aucun runtime), T rend le FRANÇAIS des
// dictionnaires frontend/shared/i18n/*.json : le français est la langue de référence, les attentes des bancs
// restent vraies. Une clé inconnue rend la clé elle-même (visible, comme dzT).
let DICO = null;
const RUNTIME = typeof window !== "undefined" && typeof window.dzT === "function";
if (!RUNTIME && typeof process !== "undefined" && process.versions && process.versions.node) {
  const fs = await import("node:fs");
  const dossier = new URL("../../shared/i18n/", import.meta.url);
  DICO = {};
  for (const f of fs.readdirSync(dossier).filter((n) => n.endsWith(".json")).sort()) {
    Object.assign(DICO, JSON.parse(fs.readFileSync(new URL(f, dossier), "utf8")));
  }
}

function remplir(s, vars) {
  return vars ? s.replace(/\{(\w+)\}/g, (m, n) => (vars[n] != null ? String(vars[n]) : m)) : s;
}

export function T(cle, vars) {
  if (typeof window !== "undefined" && typeof window.dzT === "function") return window.dzT(cle, vars);
  const e = DICO && DICO[cle];
  return e ? remplir(e.fr, vars) : cle;
}
