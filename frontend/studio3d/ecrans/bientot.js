/* t388 (31/10/2026) — l'écran d'ATTENTE des écrans du 3D Studio pas encore livrés (Texture, Rig, Affiner, Animer,
   Exporter : tâches t393-t400 du suivi). Il dit ce que l'écran fera et mène aux outils qui font déjà une partie du
   travail aujourd'hui (graphe Meshy, Établi) — jamais un bouton mort, jamais une promesse sans chemin.
   Importer est livré à part (importer.js). */
"use strict";
import { T } from "./coque_calc.js";

/* les chemins d'aujourd'hui, par écran : [clé du libellé, cible] ; cible « graphe » = l'écran Graphe, « etabli » =
   l'Établi ouvert sur le modèle, « version » = le GLB de la version ouverte */
const AUJOURDHUI = {
  texture: [["auj.graphe_texture", "graphe"]],
  rig: [["auj.graphe_rig", "graphe"], ["auj.etabli_rig", "etabli"]],
  affiner: [["auj.etabli_poids", "etabli"]],
  animer: [["auj.etabli_mouvement", "etabli"], ["auj.graphe_animer", "graphe"]],
  exporter: [["auj.etabli_export", "etabli"], ["auj.version", "version"]],
};
const PREVU = { texture: 4, rig: 4, affiner: 4, animer: 4, exporter: 4 };

const ECRANS = {};

export async function monter(section, ctx, ecran) {
  ECRANS[ecran] = { section, ctx };
  peindre(ecran);
  section.addEventListener("click", (e) => {
    const b = e.target.closest("[data-aller]");
    if (b) ctx.aller(b.dataset.aller);
  });
}

export function ouvrir() {
  for (const ecran of Object.keys(ECRANS)) peindre(ecran);
}

function peindre(ecran) {
  const { section, ctx } = ECRANS[ecran];
  const { esc, ico } = ctx;
  const f = ctx.fiche();
  const lien = ([cle, cible]) => {
    if (cible === "graphe") return `<button class="ec-bouton bloc" data-aller="graphe">${ico("dz-media-graphe-depart")} ${esc(T(cle))}</button>`;
    if (cible === "etabli") return `<a class="ec-bouton bloc" href="/etabli/${f ? "?job=" + encodeURIComponent(f.job) : ""}">${ico("dz-lab3d-maillage")} ${esc(T(cle))}</a>`;
    if (cible === "version" && f) return `<a class="ec-bouton bloc" href="${esc(f.url)}" download>${ico("dz-action-telecharger")} ${esc(T(cle, { v: f.version }))}</a>`;
    return "";
  };
  const n = PREVU[ecran] || 0;
  section.innerHTML = `<div class="ec-bientot">
    <div class="ec-label">${esc(T("onglet." + ecran))}</div>
    <h2>${esc(T("aide." + ecran))}</h2>
    <div class="ec-label">${esc(T("bientot.prevu"))}</div>
    <ul>${Array.from({ length: n }, (_, i) => `<li>${esc(T(`prevu.${ecran}_${i + 1}`))}</li>`).join("")}</ul>
    <div class="ec-label">${esc(T("bientot.aujourdhui"))}</div>
    <div class="ec-liens">${(AUJOURDHUI[ecran] || []).map(lien).join("")}</div>
  </div>`;
}
