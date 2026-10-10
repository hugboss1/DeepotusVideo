// mod-couleur.js — le panneau Couleur (C2) : pastilles de premier plan et d'arrière-plan, sélecteur natif, saisie
// hexadécimale, échanger / par défaut. La couleur vit dans le moteur (tools.setColors, relue par session.list) : le
// panneau ne fait qu'afficher et envoyer. Fonctions PURES exportées (qa/panneaux.test.mjs).
import { rgbaVersHex } from "./mod-outils.js";

// RGBA flottant du moteur -> « #rrggbb » (même conversion que les pastilles de la barre d'outils).
export const versHex = rgbaVersHex;

// Saisie libre -> « #rrggbb » ou null : « #ABC », « abc », « AABBCC » acceptés.
export function hexValide(s) {
  let h = String(s == null ? "" : s).trim().toLowerCase().replace(/^#/, "");
  if (/^[0-9a-f]{3}$/.test(h)) h = h.split("").map((c) => c + c).join("");
  return /^[0-9a-f]{6}$/.test(h) ? "#" + h : null;
}

export function initCouleur(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const corps = PL.$("#corpsCouleur");
  corps.textContent = "";
  const rangs = {};
  for (const [quelle, cle] of [["foreground", "photolab.couleur.avant"], ["background", "photolab.couleur.arriere"]]) {
    const l = document.createElement("div"); l.className = "co-ligne";
    const lib = document.createElement("span"); lib.className = "co-lib"; lib.textContent = T(cle);
    const choix = document.createElement("input"); choix.type = "color"; choix.className = "co-choix"; choix.setAttribute("aria-label", T(cle));
    const hex = document.createElement("input"); hex.type = "text"; hex.className = "co-hex"; hex.maxLength = 7; hex.spellcheck = false;
    hex.setAttribute("aria-label", T(cle) + " (hex)");
    l.append(choix, lib, hex);
    corps.appendChild(l);
    rangs[quelle] = { choix, hex };
    choix.addEventListener("change", () => envoyer(quelle, choix.value));
    const valider = () => {
      const h = hexValide(hex.value);
      if (!h) { hex.classList.add("invalide"); return; }
      hex.classList.remove("invalide");
      envoyer(quelle, h);
    };
    hex.addEventListener("change", valider);
    hex.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); valider(); } });
  }
  const outils = document.createElement("div"); outils.className = "co-outils";
  const bX = document.createElement("button"); bX.type = "button"; bX.className = "co-bouton"; bX.innerHTML = PL.icone("dz-edit-echanger-couleurs"); bX.append(T("photolab.couleur.echanger"));
  const bD = document.createElement("button"); bD.type = "button"; bD.className = "co-bouton"; bD.innerHTML = PL.icone("dz-edit-couleurs-defaut"); bD.append(T("photolab.couleur.defaut"));
  outils.append(bX, bD);
  corps.appendChild(outils);

  // Les couleurs se règlent même sans document (la session du moteur les garde) : /executer direct, pas PL.executer.
  async function commande(command, params = {}) {
    try { await PL.post("/executer", { command, params }); } catch (e) { return; }      // signalé par mod-api
    if (PL.relireCouleurs) PL.relireCouleurs();
  }
  const envoyer = (quelle, hex) => commande("tools.setColors", { [quelle]: hex });
  bX.addEventListener("click", () => commande("tools.swapColors"));
  bD.addEventListener("click", () => commande("tools.defaultColors"));

  function afficher(c) {
    rangs.foreground.choix.value = c.fg; rangs.background.choix.value = c.bg;
    if (document.activeElement !== rangs.foreground.hex) rangs.foreground.hex.value = c.fg;
    if (document.activeElement !== rangs.background.hex) rangs.background.hex.value = c.bg;
  }
  PL.surCouleurs = PL.surCouleurs || [];
  PL.surCouleurs.push(afficher);
  afficher(PL.etat.couleurs);
  // Pas de relecture au chargement : elle lancerait le moteur avant tout document ; mod-cycle relit à l'ouverture.
}
