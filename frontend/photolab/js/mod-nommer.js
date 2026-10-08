// mod-nommer.js — t153 : le petit dialogue « nom » commun aux panneaux Nuancier, Dégradés, Motifs, Couches et
// Compositions (nouveau groupe, renommer). Aucun window.prompt : la coquille de dialogue de mod-fichier.
import { ouvrirDialogue } from "./mod-fichier.js";

// -> Promise<string|null> : le nom saisi (sans espaces autour, 1..max caractères, une ligne) ou null (annulé).
export function demanderNom(PL, titre, valeur = "", max = 64) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  let champ;
  return ouvrirDialogue(PL, {
    titre, classe: "pl-dlg-nom",
    construire: ({ corps }) => {
      champ = document.createElement("input");
      champ.type = "text"; champ.maxLength = max; champ.value = valeur; champ.className = "pl-nom";
      champ.setAttribute("aria-label", titre); champ.setAttribute("data-dz-brut", "");
      corps.appendChild(champ);
      setTimeout(() => { champ.focus(); champ.select(); }, 0);
      return () => nomValide(champ.value, max) !== null;
    },
    boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
  }).then((role) => (role === "ok" ? nomValide(champ.value, max) : null));
}

// Fonction PURE : le nom propre ou null.
export function nomValide(brut, max = 64) {
  const n = String(brut == null ? "" : brut).trim();
  return n && n.length <= max && ![...n].some((c) => c.charCodeAt(0) < 32) ? n : null;
}
