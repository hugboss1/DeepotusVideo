/* t392 (31/10/2026) — écran PRÉPARER du 3D Studio : la fiche du modèle, l'original et l'optimisé côte à côte, et
   l'optimisation par préréglages (Micro prop 500 → Max detail 200 k) ou par curseur.

   Relevé de Sorceress (vue détail d'un job) : Original / Les deux / Optimisé, specs, préréglages, « Target
   triangles », Re-Optimize, téléchargements. Chez nous, l'optimisation s'écrit DANS LA LIGNÉE : POST /api/etabli/decimer
   sur la version ouverte écrit une version de plus (gltfpack garde les nœuds nommés, la fiche porte avant/après) —
   jamais un écrasement. L'original reste la version d'où l'on est parti ; « revenir à l'original » rouvre la v1.

   Ce module reprend ce qu'offraient `DzOptimize` sous chaque carte de l'onglet 3D (D1) et le nœud « 03 · topologie »
   du graphe. La réparation et les outils de maillage restent dans l'Établi, ouvert sur la même version. */
"use strict";
import { creerCanevas, charger, vider } from "/lib3d/viewer.js";
import { appliquerRendu } from "../rendu3d.js";
import { T, nb, reduction, presetProche, curseurVersTris, trisVersCurseur, cibleBornee } from "./coque_calc.js";

const P = { s: null, ctx: null, fiche: null, source: null, cibles: [], cible: 10000, vue: "les_deux", rendu: "texture",
  gauche: null, droite: null, occupe: false };
const MINI = 500;

export async function monter(section, ctx) {
  P.s = section;
  P.ctx = ctx;
  const { esc, ico } = ctx;
  section.innerHTML = `<div class="ec-trois">
    <aside class="ec-gauche">
      <div class="ec-label">${esc(T("preparer.fiche"))}</div>
      <dl class="ec-fiche" id="prFiche"></dl>
      <div class="ec-label">${esc(T("preparer.versions"))}</div>
      <div class="ec-versions" id="prVersions"></div>
      <div class="ec-label">${esc(T("preparer.atelier"))}</div>
      <button class="ec-bouton bloc" id="prEtabli">${ico("dz-lab3d-maillage")} ${esc(T("preparer.etabli"))}</button>
      <div class="ec-note">${esc(T("preparer.etabli_aide"))}</div>
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue">
        <div class="ec-segments" id="prVue">${["original", "les_deux", "optimise"].map((v) =>
          `<button data-vue="${v}">${esc(T("preparer.vue_" + v))}</button>`).join("")}</div>
        <div class="ec-segments" id="prRendu">${["texture", "argile", "fil"].map((r) =>
          `<button data-rendu="${r}">${esc(T("rendu." + r))}</button>`).join("")}</div>
      </div>
      <div class="ec-vues" id="prVues">
        <figure class="ec-vue" data-cote="gauche"><canvas></canvas><figcaption id="prCapG"></figcaption></figure>
        <figure class="ec-vue" data-cote="droite"><canvas></canvas><figcaption id="prCapD"></figcaption></figure>
      </div>
    </main>
    <aside class="ec-droite">
      <div class="ec-label">${esc(T("preparer.optimiser"))}</div>
      <div class="ec-resume" id="prResume"></div>
      <div class="ec-presets" id="prPresets"></div>
      <label class="ec-champ">${esc(T("preparer.cible"))}
        <span class="ec-cible"><input type="range" min="0" max="1000" step="1" id="prCurseur" aria-label="${esc(T("preparer.cible"))}">
        <input type="number" id="prCibleNb" min="${MINI}" step="1" aria-label="${esc(T("preparer.cible"))}"></span></label>
      <div class="ec-bornes"><span id="prMin"></span><span id="prMax"></span></div>
      <button class="ec-principal" id="prGo">${ico("dz-lab3d-optimiser")} ${esc(T("preparer.reoptimiser"))}</button>
      <div class="ec-note">${esc(T("preparer.gratuit"))}</div>
      <div class="ec-avis" id="prAvis"></div>
      <div class="ec-label">${esc(T("preparer.telecharger"))}</div>
      <div class="ec-telechargements" id="prDl"></div>
      <button class="ec-bouton bloc" id="prOriginal">${ico("dz-action-reinitialiser")} ${esc(T("preparer.revenir"))}</button>
    </aside>
  </div>`;
  P.gauche = creerCanevas(section.querySelector('[data-cote="gauche"] canvas'));
  P.droite = creerCanevas(section.querySelector('[data-cote="droite"] canvas'));
  section.querySelector("#prVue").addEventListener("click", (e) => {
    const b = e.target.closest("[data-vue]");
    if (b) { P.vue = b.dataset.vue; peindreVues(); }
  });
  section.querySelector("#prRendu").addEventListener("click", (e) => {
    const b = e.target.closest("[data-rendu]");
    if (!b) return;
    P.rendu = b.dataset.rendu;
    for (const a of [P.gauche, P.droite]) appliquerRendu(a.racine, P.rendu);
    peindreVues();
  });
  section.querySelector("#prPresets").addEventListener("click", (e) => {
    const b = e.target.closest("[data-preset]");
    if (b) { P.cible = +b.dataset.tris; peindreCible(); }
  });
  section.querySelector("#prCurseur").addEventListener("input", (e) => {
    P.cible = curseurVersTris(+e.target.value, MINI, maxi());
    peindreCible(false);
  });
  section.querySelector("#prCibleNb").addEventListener("change", (e) => {
    P.cible = Math.max(MINI, Math.min(maxi(), parseInt(e.target.value, 10) || MINI));
    peindreCible();
  });
  section.querySelector("#prGo").addEventListener("click", optimiser);
  section.querySelector("#prEtabli").addEventListener("click", () => ctx.aller("etabli"));   // t403 : un écran, plus une page
  section.querySelector("#prOriginal").addEventListener("click", () => P.fiche && ctx.ouvrir(P.fiche.job, 1, "preparer"));
  section.querySelector("#prVersions").addEventListener("click", (e) => {
    const b = e.target.closest("[data-version]");
    if (b) ctx.ouvrir(P.fiche.job, +b.dataset.version, "preparer");
  });
  try { P.cibles = (await ctx.jget("/api/studio3d/preparer/cibles")).cibles || []; } catch { P.cibles = []; }
}

const maxi = () => Math.max(MINI + 1, (P.source && P.source.triangles) || 200000);

export async function ouvrir(fiche) {
  if (!P.s) return;
  /* une version née d'une décimation se compare à sa source ; sinon les deux côtés montrent la version ouverte */
  P.fiche = fiche;
  P.source = fiche;
  if (fiche && fiche.version > 1) {
    const etape = (fiche.versions || []).find((v) => v.version === fiche.version);
    const src = etape && etape.depuis;
    if (src) {
      try { P.source = await P.ctx.jget(`/api/studio3d/ouvert/${encodeURIComponent(fiche.job)}?version=${src}`); } catch { /* source illisible */ }
    }
  }
  P.cible = cibleBornee(P.cible, P.source && P.source.triangles);
  peindre();
  if (!fiche) { vider(P.gauche); vider(P.droite); return; }
  await Promise.all([
    charger(P.gauche, P.source.url).then(() => appliquerRendu(P.gauche.racine, P.rendu)).catch(() => {}),
    charger(P.droite, fiche.url).then(() => appliquerRendu(P.droite.racine, P.rendu)).catch(() => {}),
  ]);
}

function peindre() {
  const { esc } = P.ctx;
  const f = P.fiche;
  const fiche = P.s.querySelector("#prFiche");
  if (!f) { fiche.innerHTML = `<dd>${esc(T("bandeau.vide"))}</dd>`; return; }
  const lignes = [["sommets", nb(f.sommets)], ["triangles", nb(f.triangles)], ["maillages", nb(f.maillages)],
    ["materiaux", nb(f.materiaux)], ["os", f.rig && f.rig.rigge ? nb(f.rig.os) : "—"],
    ["animations", nb((f.rig && f.rig.animations) || 0)], ["moteur", f.moteur || "—"]];
  fiche.innerHTML = lignes.map(([k, v]) => `<dt>${esc(T("fiche." + k))}</dt><dd>${esc(v)}</dd>`).join("");
  P.s.querySelector("#prVersions").innerHTML = (f.versions || []).map((v) =>
    `<button class="ec-version ${v.version === f.version ? "on" : ""}" data-version="${v.version}">v${v.version}`
    + `<span>${esc(v.triangles != null ? T("bandeau.triangles", { n: nb(v.triangles) }) : v.libelle || "")}</span></button>`).join("");
  const dl = [[T("preparer.dl_ouverte", { v: f.version }), f.url]];
  if (P.source && P.source.version !== f.version) dl.unshift([T("preparer.dl_original", { v: P.source.version }), P.source.url]);
  P.s.querySelector("#prDl").innerHTML = dl.map(([l, u]) =>
    `<a class="ec-bouton bloc" href="${esc(u)}" download>${P.ctx.ico("dz-action-telecharger")} ${esc(l)} · .glb</a>`).join("");
  peindreCible();
  peindreVues();
}

function peindreCible(majCurseur = true) {
  const { esc } = P.ctx;
  const orig = P.source && P.source.triangles;
  const proche = presetProche(P.cibles, P.cible);
  P.s.querySelector("#prPresets").innerHTML = P.cibles.map((c) =>
    `<button class="ec-preset ${c.preset === proche ? "on" : ""}" data-preset="${c.preset}" data-tris="${c.triangles}"
      ${orig && c.triangles >= orig ? "disabled" : ""}>${esc(T("preset." + c.preset))} <span>${esc(nb(c.triangles))}</span></button>`).join("");
  if (majCurseur) P.s.querySelector("#prCurseur").value = trisVersCurseur(P.cible, MINI, maxi());
  P.s.querySelector("#prCibleNb").value = P.cible;
  P.s.querySelector("#prCibleNb").max = maxi();
  P.s.querySelector("#prMin").textContent = nb(MINI);
  P.s.querySelector("#prMax").textContent = nb(maxi());
  const f = P.fiche;
  const r = f && P.source && f.version !== P.source.version ? reduction(P.source.triangles, f.triangles) : null;
  P.s.querySelector("#prResume").innerHTML = f
    ? `<b>${esc(nb(f.triangles))}</b> ${esc(T("preparer.tris"))}` + (r != null ? ` <span>${esc(T("preparer.reduction", { p: r }))}</span>` : "")
    : "";
  P.s.querySelector("#prGo").disabled = !f || P.occupe || (orig && P.cible >= orig);
}

function peindreVues() {
  const { esc } = P.ctx;
  for (const b of P.s.querySelectorAll("#prVue [data-vue]")) b.classList.toggle("on", b.dataset.vue === P.vue);
  for (const b of P.s.querySelectorAll("#prRendu [data-rendu]")) b.classList.toggle("on", b.dataset.rendu === P.rendu);
  const g = P.s.querySelector('[data-cote="gauche"]'), d = P.s.querySelector('[data-cote="droite"]');
  g.classList.toggle("hidden", P.vue === "optimise");
  d.classList.toggle("hidden", P.vue === "original");
  const s = P.source, f = P.fiche;
  P.s.querySelector("#prCapG").textContent = s ? T("preparer.cap_original", { v: s.version, n: nb(s.triangles) }) : "";
  P.s.querySelector("#prCapD").textContent = f ? T("preparer.cap_ouverte", { v: f.version, n: nb(f.triangles) }) : "";
  void esc;
}

async function optimiser() {
  const f = P.fiche;
  if (!f || P.occupe) return;
  const avis = P.s.querySelector("#prAvis");
  P.occupe = true;
  peindreCible(false);
  avis.textContent = T("preparer.en_cours");
  try {
    const corps = { job: f.job, version: (P.source || f).version };
    const preset = presetProche(P.cibles, P.cible);
    if (preset) corps.preset = preset; else corps.target_tris = P.cible;
    const r = await fetch("/api/etabli/decimer", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
    avis.textContent = T("preparer.fait");
    P.occupe = false;
    await P.ctx.ouvrir(f.job, null, "preparer");
  } catch (e) {
    avis.textContent = T("erreur.optimiser", { m: e.message });
  } finally {
    P.occupe = false;
    peindreCible(false);
  }
}
