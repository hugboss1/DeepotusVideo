/* t403 (31/10/2026) — écran ÉTABLI du 3D Studio : l'Établi (réparer, décimer, couper, booléens, pièces, plaque,
   impression) devient un écran de la coque, sur le modèle ouvert, au lieu d'une page qui PRENAIT LA PLACE du 3D Studio
   (ancien `#goEtabli` / nœud « 07 · établi »).

   L'Établi reste sa page (`/etabli/`, etabli.js généré par la traduction L8 : on n'y touche pas), chargée dans un
   cadre avec `?job=` : elle marque le modèle visé dans sa chronologie. Son bouton « ← 3D Studio » navigue le cadre
   vers /studio3d/ — la coque l'intercepte : elle remet l'Établi, relit le modèle (l'Établi a pu écrire des versions)
   et revient à Préparer. Les versions écrites ici apparaissent dans le bandeau et dans Préparer. */
"use strict";
import { T } from "./coque_calc.js";

const B = { s: null, ctx: null, cadre: null, job: null };

export async function monter(section, ctx) {
  B.s = section;
  B.ctx = ctx;
  section.innerHTML = `<div class="ec-etabli">
    <div class="ec-etabli-barre"><span class="ec-note">${ctx.esc(T("etabli.aide"))}</span>
      <button class="ec-bouton" id="ebRelire">${ctx.ico("dz-action-reinitialiser")} ${ctx.esc(T("etabli.relire"))}</button></div>
    <iframe class="ec-etabli-cadre" title="${ctx.esc(T("onglet.etabli"))}"></iframe></div>`;
  B.cadre = section.querySelector("iframe");
  B.cadre.addEventListener("load", surChargement);
  section.querySelector("#ebRelire").addEventListener("click", () => ctx.rafraichir());
}

export function ouvrir(fiche) {
  if (!B.cadre) return;
  const job = fiche ? fiche.job : null;
  if (job === B.job) return;
  B.job = job;
  B.cadre.src = job ? `/etabli/?job=${encodeURIComponent(job)}` : "about:blank";
}

function surChargement() {
  let chemin = "";
  try { chemin = B.cadre.contentWindow.location.pathname; } catch { return; }
  if (chemin.startsWith("/studio3d")) {
    // « ← 3D Studio » de l'Établi : pas de 3D Studio dans le 3D Studio — on revient à Préparer, modèle relu
    B.cadre.src = B.job ? `/etabli/?job=${encodeURIComponent(B.job)}` : "about:blank";
    B.ctx.rafraichir().then(() => B.ctx.aller("preparer"));
  }
}
