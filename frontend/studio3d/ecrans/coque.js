/* t388 (31/10/2026) — la COQUE du 3D Studio à écrans.

   Le graphe Meshy cesse d'être l'entrée du 3D Studio (D2) : une barre d'onglets à trois groupes, un bandeau
   « Ouvert » commun à tous les écrans, puis l'écran choisi. Le graphe d'hier (#studio, studio3d.js généré par L9 :
   on n'y touche pas) devient l'écran « Graphe », masqué quand un autre écran est actif.

   Chaque écran est un module à part, chargé à la première visite, qui exporte `monter(section, ctx)` et, s'il suit
   le modèle ouvert, `ouvrir(fiche)`. Un écran pas encore livré montre ce qu'il fera et les outils d'aujourd'hui qui
   le remplacent en attendant — jamais un bouton mort. Le calcul (écrans, adresse, bandeau) vit dans coque_calc.js. */
"use strict";
import { T, ECRANS, SUIVANT, ECRAN_DU_NOEUD, permis, lireAdresse, ecrireAdresse, bandeau } from "./coque_calc.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ico = (cle) => `<svg class="dzi dzi--16" aria-hidden="true" focusable="false"><use href="/shared/icons/dz-icons.svg#${cle}"></use></svg>`;

/* les écrans livrés ; les autres passent par l'écran d'attente (bientot) */
const MODULES = { ouvrir: "./ouvrir.js", importer: "./importer.js", preparer: "./preparer.js", decor: "./decor.js", rig: "./rig.js" };

const E = { ouvert: null, ecran: "ouvrir", sale: false, sections: {}, modules: {}, chargement: null };

async function jget(p) {
  const r = await fetch(p);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error((j && typeof j.detail === "string" && j.detail) || String(r.status)), { status: r.status });
  return j;
}

/* ── le contexte passé aux écrans ─────────────────────────────────────────── */
const ctx = {
  T, ico, esc, jget,
  fiche: () => E.ouvert,
  ouvrir: (job, version, ecran) => ouvrirModele(job, version, ecran),
  aller: (ecran) => aller(ecran),
  rafraichir: () => (E.ouvert ? ouvrirModele(E.ouvert.job, null, E.ecran) : null),
  marquerSale: (b) => { E.sale = !!b; peindreBandeau(); },
  suivant: (ecran) => SUIVANT[ecran] || null,
};
window.__dzStudio3dEcrans = ctx;

/* ── construction ─────────────────────────────────────────────────────────── */
function construire() {
  document.body.classList.add("ec-actif");
  const studio = $("#studio");
  const barre = document.createElement("nav");
  barre.className = "ec-barre";
  barre.setAttribute("role", "tablist");
  barre.setAttribute("aria-label", T("barre.titre"));
  let g = 0, h = "";
  for (const e of ECRANS) {
    if (g && e.groupe !== g) h += `<span class="ec-filet" aria-hidden="true"></span>`;
    g = e.groupe;
    h += `<button class="ec-onglet" role="tab" data-ecran="${e.id}" title="${esc(T("aide." + e.id))}">${ico(e.icone)}`
      + `<span>${esc(T("onglet." + e.id))}</span></button>`;
  }
  barre.innerHTML = h;
  const band = document.createElement("div");
  band.className = "ec-bandeau";
  band.id = "ecBandeau";
  const zone = document.createElement("div");
  zone.className = "ec-zone";
  zone.id = "ecZone";
  studio.before(barre, band, zone);
  for (const e of ECRANS) {
    if (e.id === "graphe") { E.sections.graphe = studio; continue; }
    const s = document.createElement("section");
    s.className = "ec-ecran hidden";
    s.dataset.ecran = e.id;
    s.setAttribute("role", "tabpanel");
    zone.append(s);
    E.sections[e.id] = s;
  }
  barre.addEventListener("click", (ev) => {
    const b = ev.target.closest(".ec-onglet");
    if (b && !b.disabled) aller(b.dataset.ecran);
  });
  band.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-aller]");
    if (b) aller(b.dataset.aller);
    if (ev.target.closest("[data-fermer]")) fermerModele();
  });
  monterLiensDuGraphe(studio);
  window.addEventListener("popstate", () => appliquerAdresse(location.search, false));
}

/* le graphe garde ses nœuds ; un bandeau au-dessus dit où chaque fonction vit désormais */
function monterLiensDuGraphe(studio) {
  const centre = $(".center", studio);
  if (!centre) return;
  const D = window.__dzStudio3d;
  const noeuds = (D && D.NODES) || Object.keys(ECRAN_DU_NOEUD).map((id) => ({ id, kicker: id }));
  const div = document.createElement("div");
  div.className = "ec-graphe-liens";
  div.innerHTML = `<span class="ec-graphe-titre">${esc(T("graphe.liens"))}</span>`
    + noeuds.filter((n) => ECRAN_DU_NOEUD[n.id]).map((n) =>
      `<button class="ec-puce" data-aller="${ECRAN_DU_NOEUD[n.id]}">${esc(n.kicker || n.id)} → ${esc(T("onglet." + ECRAN_DU_NOEUD[n.id]))}</button>`).join("");
  div.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-aller]");
    if (b) aller(b.dataset.aller);
  });
  centre.prepend(div);
}

/* ── le bandeau « Ouvert » ────────────────────────────────────────────────── */
function peindreBandeau() {
  const b = bandeau(E.ouvert, E.sale);
  const el = $("#ecBandeau");
  if (b.vide) {
    el.innerHTML = `<span class="ec-band-label">${esc(T("bandeau.ouvert"))}</span><span class="ec-band-vide">${esc(b.texte)}</span>`;
  } else {
    const suiv = SUIVANT[E.ecran];
    el.innerHTML = `<span class="ec-band-label">${esc(T("bandeau.ouvert"))}</span>`
      + (b.vignette ? `<img class="ec-band-vignette" alt="" src="${esc(b.vignette)}" onerror="this.remove()">` : "")
      + `<b class="ec-band-nom">${esc(b.nom)}</b>`
      + (b.rigge ? `<span class="ec-badge">${esc(T("bandeau.rigge"))}</span>` : "")
      + `<span class="ec-band-detail">${esc(b.detail)}</span>`
      + (b.sale ? `<span class="ec-band-sale">${esc(T("bandeau.non_enregistre"))}</span>` : "")
      + `<span class="ec-band-droite"><span class="ec-band-version" title="${esc(T("bandeau.version_aide"))}">${esc(b.version)}</span>`
      + (suiv ? `<button class="ec-envoyer" data-aller="${suiv}">${esc(T("bandeau.envoyer", { ecran: T("onglet." + suiv) }))}</button>` : "")
      + `<button class="ec-fermer" data-fermer="1" title="${esc(T("bandeau.fermer"))}" aria-label="${esc(T("bandeau.fermer"))}">×</button></span>`;
  }
  for (const btn of document.querySelectorAll(".ec-onglet")) {
    const id = btn.dataset.ecran;
    btn.disabled = !permis(id, E.ouvert);
    btn.classList.toggle("on", id === E.ecran);
    btn.setAttribute("aria-selected", id === E.ecran ? "true" : "false");
    if (btn.disabled) btn.title = T("barre.sans_modele");
    else btn.title = T("aide." + id);
  }
}

/* ── navigation ───────────────────────────────────────────────────────────── */
function majAdresse(pousser) {
  const q = ecrireAdresse({ job: E.ouvert && E.ouvert.job, version: E.ouvert && E.ouvert.version, ecran: E.ecran });
  const url = location.pathname + q;
  if (url === location.pathname + location.search) return;
  history[pousser ? "pushState" : "replaceState"](null, "", url);
}

async function aller(ecran, pousser = true) {
  if (!permis(ecran, E.ouvert)) ecran = "ouvrir";
  E.ecran = ecran;
  for (const [id, s] of Object.entries(E.sections)) s.classList.toggle("hidden", id !== ecran);
  $("#ecZone").classList.toggle("hidden", ecran === "graphe");
  document.body.classList.toggle("ec-graphe", ecran === "graphe");
  peindreBandeau();
  majAdresse(pousser);
  await monterEcran(ecran);
}

async function monterEcran(ecran) {
  if (ecran === "graphe" || E.modules[ecran]) {
    const m = E.modules[ecran];
    if (m && m.montre) m.montre();
    return;
  }
  const s = E.sections[ecran];
  let m;
  if (MODULES[ecran]) {
    try { m = await import(MODULES[ecran]); } catch (e) {
      s.innerHTML = `<div class="ec-erreur">${esc(T("erreur.module", { m: e.message }))}</div>`;
      return;
    }
  } else {
    m = await import("./bientot.js");
  }
  E.modules[ecran] = m;
  await m.monter(s, ctx, ecran);
  if (E.ouvert && m.ouvrir) await m.ouvrir(E.ouvert);
}

async function ouvrirModele(job, version, ecran) {
  try {
    const q = version ? `?version=${encodeURIComponent(version)}` : "";
    E.ouvert = await jget(`/api/studio3d/ouvert/${encodeURIComponent(job)}${q}`);
    E.sale = false;
  } catch (e) {
    E.ouvert = null;
    alerte(T("erreur.ouvrir", { m: e.message }));
  }
  for (const m of Object.values(E.modules)) if (m.ouvrir) await m.ouvrir(E.ouvert);
  await aller(ecran || (E.ouvert ? (permis(E.ecran, E.ouvert) && E.ecran !== "ouvrir" ? E.ecran : "preparer") : "ouvrir"));
}

function fermerModele() {
  E.ouvert = null;
  E.sale = false;
  for (const m of Object.values(E.modules)) if (m.ouvrir) m.ouvrir(null);
  aller("ouvrir");
}

function alerte(texte) {
  const el = $("#ecBandeau");
  const a = document.createElement("span");
  a.className = "ec-band-erreur";
  a.textContent = texte;
  el.append(a);
}

async function appliquerAdresse(search, pousser) {
  const a = lireAdresse(search);
  if (a.job && (!E.ouvert || E.ouvert.job !== a.job || (a.version && a.version !== E.ouvert.version))) {
    await ouvrirModele(a.job, a.version, a.ecran);
  } else {
    await aller(a.ecran, pousser);
  }
}

construire();
appliquerAdresse(location.search, false);
