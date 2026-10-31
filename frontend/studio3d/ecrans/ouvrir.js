/* t388 / t391 (31/10/2026) — écran OUVRIR du 3D Studio : la galerie des modèles générés dans l'onglet 3D (et des
   productions de l'Établi, qui sont des versions des mêmes jobs).

   Relevé de Sorceress : filtres Tous / Riggés / Non riggés (plus Personnages / Décor chez nous), recherche, curseur
   « cartes par ligne », et sur chaque carte les écrans où l'ouvrir. La liste vient de GET /api/studio3d/modeles, qui
   ne lit que le JSON de chaque GLB : ouvrir la galerie ne charge aucun maillage. */
"use strict";
import { T, FILTRES, filtrer, compter, nb, estDecor } from "./coque_calc.js";

const G = { modeles: [], filtre: "tous", recherche: "", colonnes: 4, s: null, ctx: null };
const CLE_COLONNES = "deepotus.studio3d.colonnes";

export async function monter(section, ctx) {
  G.s = section;
  G.ctx = ctx;
  try { G.colonnes = Math.min(6, Math.max(2, parseInt(localStorage.getItem(CLE_COLONNES), 10) || 4)); } catch { /* stockage fermé */ }
  section.innerHTML = `<div class="ec-ouvrir">
    <div class="ec-outils">
      <div class="ec-filtres" role="group" aria-label="${ctx.esc(T("ouvrir.filtres"))}"></div>
      <label class="ec-grille">${ctx.esc(T("ouvrir.grille"))}
        <input type="range" min="2" max="6" step="1" value="${G.colonnes}" id="ecColonnes" aria-label="${ctx.esc(T("ouvrir.grille"))}"></label>
      <input type="search" class="ec-recherche" id="ecRecherche" placeholder="${ctx.esc(T("ouvrir.recherche"))}" aria-label="${ctx.esc(T("ouvrir.recherche"))}">
      <button class="ec-bouton" id="ecRafraichir">${ctx.ico("dz-action-reinitialiser")} ${ctx.esc(T("ouvrir.rafraichir"))}</button>
    </div>
    <div class="ec-avis" id="ecOuvrirAvis"></div>
    <div class="ec-cartes" id="ecCartes"></div>
  </div>`;
  section.querySelector("#ecColonnes").addEventListener("input", (e) => {
    G.colonnes = +e.target.value;
    try { localStorage.setItem(CLE_COLONNES, String(G.colonnes)); } catch { /* stockage fermé */ }
    peindre();
  });
  section.querySelector("#ecRecherche").addEventListener("input", (e) => { G.recherche = e.target.value; peindre(); });
  section.querySelector("#ecRafraichir").addEventListener("click", charger);
  section.querySelector(".ec-filtres").addEventListener("click", (e) => {
    const b = e.target.closest("[data-filtre]");
    if (b) { G.filtre = b.dataset.filtre; peindre(); }
  });
  section.querySelector("#ecCartes").addEventListener("click", (e) => {
    const b = e.target.closest("[data-ouvrir]");
    if (b) G.ctx.ouvrir(b.dataset.ouvrir, null, b.dataset.ecran || "preparer");
  });
  await charger();
}

export function montre() { charger(); }

async function charger() {
  const avis = G.s.querySelector("#ecOuvrirAvis");
  avis.textContent = T("ouvrir.chargement");
  try {
    G.modeles = (await G.ctx.jget("/api/studio3d/modeles")).modeles || [];
    avis.textContent = "";
  } catch (e) {
    avis.textContent = T("erreur.charger", { m: e.message });
  }
  peindre();
}

function peindre() {
  const { esc, ico } = G.ctx;
  const c = compter(G.modeles);
  G.s.querySelector(".ec-filtres").innerHTML = FILTRES.map((f) =>
    `<button class="ec-filtre ${f === G.filtre ? "on" : ""}" data-filtre="${f}">${esc(T("filtre." + f))} <b>${c[f]}</b></button>`).join("");
  const liste = filtrer(G.modeles, G.filtre, G.recherche);
  const box = G.s.querySelector("#ecCartes");
  box.style.setProperty("--ec-colonnes", G.colonnes);
  if (!G.modeles.length) {
    box.innerHTML = `<div class="ec-vide">${esc(T("ouvrir.vide"))}</div>`;
    return;
  }
  if (!liste.length) {
    box.innerHTML = `<div class="ec-vide">${esc(T("ouvrir.aucun"))}</div>`;
    return;
  }
  const ouvert = G.ctx.fiche();
  box.innerHTML = liste.map((m) => {
    const rig = m.rig || {};
    const decor = estDecor(m);
    const detail = m.illisible ? T("ouvrir.illisible")
      : [rig.rigge ? T("bandeau.os", { n: nb(rig.os) }) : null, T("bandeau.triangles", { n: nb(m.triangles) })].filter(Boolean).join(" · ");
    const actions = decor
      ? [["preparer", "dz-lab3d-optimiser"], ["decor", "dz-cat-decor"], ["exporter", "dz-action-exporter"]]
      : [["texture", "dz-lab3d-materiau"], ["rig", "dz-lab3d-rig"], ["animer", "dz-cat-animation"]];
    return `<article class="ec-carte ${ouvert && ouvert.job === m.job ? "on" : ""}">
      <button class="ec-carte-image" data-ouvrir="${esc(m.job)}" data-ecran="preparer" title="${esc(T("ouvrir.ouvrir"))}">
        ${m.vignette ? `<img alt="" loading="lazy" src="${esc(m.vignette)}" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ec-sans-image'}))">`
          : `<span class="ec-sans-image">${ico("dz-lab3d-cube")}</span>`}
        <span class="ec-pastilles">${rig.rigge ? `<span class="ec-badge">${esc(T("bandeau.rigge"))}</span>` : ""}`
      + `<span class="ec-badge discret">v${esc(m.version)}</span></span>
      </button>
      <div class="ec-carte-texte"><b title="${esc(m.nom)}">${esc(m.nom)}</b>
        <span>${esc(m.moteur || T("ouvrir.moteur_inconnu"))} · ${esc(detail)}</span></div>
      <div class="ec-carte-actions">${actions.map(([e, i]) =>
        `<button class="ec-bouton" data-ouvrir="${esc(m.job)}" data-ecran="${e}">${ico(i)} ${esc(T("onglet." + e))}</button>`).join("")}</div>
    </article>`;
  }).join("");
}
