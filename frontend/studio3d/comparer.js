/* t344 (lot Scenario B9, 29/10/2026) — « Comparer les moteurs » : une image, N moteurs image → 3D, le même éclairage,
   une caméra synchronisée, Texturé / Argile / Fil de fer, et le tableau MESURÉ par le serveur (fiche de maillage).

   Page à part du 3D Studio (studio3d.js est régénéré par la traduction L9 : on n'y touche pas). Deux façons de remplir
   un comparatif : « Nouvelle image » (N tirs en UN clic, payants : devis du serveur affiché sur le bouton, dialogue
   maison, `confirme_cout`, puis la couche dz-plafonds pour un 402) ; « Modèles existants » (des GLB déjà générés,
   gratuit). « Garder celui-ci » envoie une vue capturée du canevas : PYTHON l'écrit dans la Bibliothèque.

   Les viewers sont ceux de /lib3d/viewer.js (mêmes lumières pour tous) ; chaque modèle est ramené à une boîte de 1
   posée au sol, si bien qu'une SEULE pose de caméra vaut pour toutes les cases : la case que l'on tourne pilote les
   autres. Comparateur commun (dz-comparateur, t337) : pas encore là, cette grille est propre au banc. */
"use strict";
import * as THREE from "three";
import { creerCanevas, charger, cadrer, orienter } from "/lib3d/viewer.js";
import { T, COLONNES, trier, meilleur, cellule, totalCoches, avisCle, grouperParImage, usd, nb } from "./comparer_calc.js";

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ico = (cle) => (typeof dzIcone === "function" ? dzIcone(cle, { taille: 16, classe: "dzi--16" }) : "");

/* l'état de la page — déclaré ICI */
const E = {
  mode: "tir", images: [], image: "", textures: true, devis: null, coches: new Set(),
  modeles: [], choisis: new Set(), historique: [], tab: null, tri: { cle: "tris", desc: false },
  rendu: "texture", vue: "libre", cases: new Map(), pilote: null, sondage: null, occupe: false,
};

async function jget(p) {
  const r = await fetch(p);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(msgDe(j, r.status)), { status: r.status });
  return j;
}
async function jpost(p, b) {
  const r = await fetch(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(msgDe(j, r.status)), { status: r.status, detail: j.detail });
  return j;
}
function msgDe(j, st) {
  const d = j && j.detail;
  return typeof d === "string" ? d : (d && d.message) || String(st);
}

function avis(texte, erreur = false) {
  const el = $("#cmpAvis");
  el.textContent = texte || "";
  el.className = "cmp-avis" + (erreur ? " erreur" : "") + (texte ? "" : " hidden");
}

/* ── le rail : nouvelle image ───────────────────────────────────────────── */

function rendreTir() {
  const box = $("#panTir");
  const d = E.devis;
  const n = E.coches.size, total = d ? totalCoches(d, [...E.coches]) : 0;
  const pret = n >= 2 && !!E.image && !E.occupe;
  let h = `<div class="cmp-label">${esc(T("tir.image"))}</div>`;
  if (!E.images.length) h += `<div class="cmp-vide">${esc(T("tir.sans_image"))}</div>`;
  else {
    h += `<select id="cmpImage" class="cmp-sel" aria-label="${esc(T("tir.image"))}">`
      + E.images.map((f) => `<option value="${esc(f)}" ${f === E.image ? "selected" : ""}>${esc(f)}</option>`).join("") + `</select>`;
    if (E.image) h += `<img class="cmp-source" alt="" src="/api/images/${encodeURIComponent(E.image)}">`;
  }
  h += `<label class="cmp-case"><input type="checkbox" id="cmpTex" ${E.textures ? "checked" : ""}> ${esc(T("tir.textures"))}</label>`
    + `<div class="cmp-note">${esc(T("tir.meme_entree"))}</div>`
    + `<div class="cmp-label">${esc(T("tir.moteurs"))}</div><div class="cmp-moteurs">`;
  for (const l of (d && d.lignes) || []) {
    const a = avisCle(l);
    h += `<label class="cmp-moteur ${E.coches.has(l.moteur) ? "on" : ""}" title="${esc(l.note)}">`
      + `<input type="checkbox" data-moteur="${esc(l.moteur)}" ${E.coches.has(l.moteur) ? "checked" : ""}>`
      + `<span class="nom">${esc(l.label)}</span><span class="prix">${esc(l.usd > 0 ? usd(l.usd) : T("tir.gratuit"))}</span>`
      + (a ? `<span class="cle">${esc(a)}</span>` : "") + `</label>`;
  }
  h += `</div><div class="cmp-total">${esc(T("tir.total", { n, p: usd(total) }))}</div>`
    + `<button class="cmp-principal" id="cmpLancer" ${pret ? "" : "disabled"}>${ico("dz-action-comparer")} `
    + `${esc(n >= 2 ? T("tir.lancer", { n, p: usd(total) }) : T("tir.deux_au_moins"))}</button>`
    + `<div class="cmp-note">${esc(T("tir.devis_avant"))}</div>`;
  box.innerHTML = h;
  const sel = box.querySelector("#cmpImage");
  if (sel) sel.addEventListener("change", () => { E.image = sel.value; rendreTir(); });
  box.querySelector("#cmpTex").addEventListener("change", async (ev) => { E.textures = ev.target.checked; await chargerDevis(); });
  box.querySelectorAll("input[data-moteur]").forEach((c) => c.addEventListener("change", () => {
    if (c.checked) E.coches.add(c.dataset.moteur); else E.coches.delete(c.dataset.moteur);
    rendreTir();
  }));
  box.querySelector("#cmpLancer").addEventListener("click", lancer);
}

async function chargerDevis() {
  try { E.devis = await jget(`/api/comparatif3d/moteurs?textures=${E.textures ? "true" : "false"}`); }
  catch (e) { avis(T("erreur.charger", { m: e.message }), true); }
  rendreTir();
}

async function lancer() {
  const d = E.devis;
  const choisis = (d.lignes || []).filter((l) => E.coches.has(l.moteur));
  const total = totalCoches(d, [...E.coches]);
  const D_ = window.__dzDialogue;
  const detail = choisis.map((l) => `${l.label} · ${l.usd > 0 ? usd(l.usd) : T("tir.gratuit")}`).join("\n");
  /* le devis AVANT l'envoi ; sans dialogue maison : refus (le sens sûr) */
  if (!D_ || !(await D_.confirmer(T("tir.confirmer", { n: choisis.length, p: usd(total), detail, image: E.image }),
    { titre: T("tir.titre_dialogue"), ok: T("tir.ok", { p: usd(total) }) }))) return;
  E.occupe = true; rendreTir(); avis(T("tir.en_route", { n: choisis.length }));
  try {
    const r = await jpost("/api/comparatif3d", { image_filename: E.image, moteurs: choisis.map((l) => l.moteur),
      textures: E.textures, confirme_cout: true });
    await ouvrirComparatif(r.id);
    await chargerHistorique();
  } catch (e) {
    avis(e.status === 503 ? T("erreur.cle", { m: e.message }) : T("erreur.lancer", { m: e.message }), true);
  } finally {
    E.occupe = false; rendreTir();
  }
}

/* ── le rail : modèles existants (gratuit) ──────────────────────────────── */

function rendreExistants() {
  const box = $("#panEx");
  let h = `<div class="cmp-note">${esc(T("ex.intro"))}</div>`;
  if (!E.modeles.length) h += `<div class="cmp-vide">${esc(T("ex.vide"))}</div>`;
  for (const [img, liste] of grouperParImage(E.modeles)) {
    h += `<div class="cmp-groupe"><div class="cmp-groupe-tete">${esc(img || T("ex.sans_image"))}</div>`
      + liste.map((m) => `<label class="cmp-modele ${E.choisis.has(m.job) ? "on" : ""}">`
        + `<input type="checkbox" data-job="${esc(m.job)}" ${E.choisis.has(m.job) ? "checked" : ""}>`
        + `<span class="nom">${esc(m.moteur)}</span><span class="meta">${esc(m.job)} · v${esc(m.version)}`
        + `${m.tris ? " · " + esc(T("ex.tris", { n: nb(m.tris) })) : ""}</span></label>`).join("") + `</div>`;
  }
  const n = E.choisis.size;
  h += `<button class="cmp-principal" id="cmpEx" ${n >= 2 && !E.occupe ? "" : "disabled"}>${ico("dz-action-comparer")} `
    + `${esc(n >= 2 ? T("ex.lancer", { n }) : T("ex.deux_au_moins"))}</button>`;
  box.innerHTML = h;
  box.querySelectorAll("input[data-job]").forEach((c) => c.addEventListener("change", () => {
    if (c.checked) E.choisis.add(c.dataset.job); else E.choisis.delete(c.dataset.job);
    rendreExistants();
  }));
  box.querySelector("#cmpEx").addEventListener("click", comparerExistants);
}

async function comparerExistants() {
  E.occupe = true; rendreExistants(); avis("");
  try {
    const tab = await jpost("/api/comparatif3d/existants", { modeles: [...E.choisis].map((job) => ({ job })) });
    await ouvrirComparatif(tab.id, tab);
    await chargerHistorique();
  } catch (e) {
    avis(T("erreur.lancer", { m: e.message }), true);
  } finally {
    E.occupe = false; rendreExistants();
  }
}

/* ── l'historique ───────────────────────────────────────────────────────── */

async function chargerHistorique() {
  try { E.historique = (await jget("/api/comparatif3d")).comparatifs || []; } catch { E.historique = []; }
  const sel = $("#cmpHist");
  sel.innerHTML = `<option value="">${esc(T("hist.choisir", { n: E.historique.length }))}</option>`
    + E.historique.map((c) => `<option value="${esc(c.id)}" ${E.tab && E.tab.id === c.id ? "selected" : ""}>`
      + `${esc((c.created_at || "").slice(0, 16).replace("T", " "))} · ${esc(c.titre || T("mode." + c.mode))} · `
      + `${esc(T("hist.moteurs", { n: (c.moteurs || []).length }))}</option>`).join("");
}

/* ── la grille : un viewer par moteur, caméra synchronisée ─────────────── */

const ARGILE = new THREE.MeshStandardMaterial({ color: 0xb9b2a6, roughness: 0.9, metalness: 0 });
const FIL = new THREE.MeshBasicMaterial({ color: 0x9fc3e8, wireframe: true });

function appliquerRendu(api) {
  if (!api.racine) return;
  api.racine.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.userData.dzMatOrigine) o.userData.dzMatOrigine = o.material;
    o.material = E.rendu === "argile" ? ARGILE : E.rendu === "fil" ? FIL : o.userData.dzMatOrigine;
  });
}

/* ramène le modèle à une boîte de 1 posée au sol, centrée : la même pose de caméra vaut pour toutes les cases */
function normaliser(api) {
  const r = api.racine;
  r.scale.setScalar(1);
  r.position.set(0, 0, 0);
  r.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(r), t = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3());
  const s = 1 / (Math.max(t.x, t.y, t.z) || 1);
  r.scale.setScalar(s);
  r.position.set(-c.x * s, -b.min.y * s, -c.z * s);
  r.updateMatrixWorld(true);
}

function synchroniser(source) {
  for (const k of E.cases.values()) {
    const a = k.api;
    if (!a || a === source.api) continue;
    a.camera.position.copy(source.api.camera.position);
    a.camera.quaternion.copy(source.api.camera.quaternion);
    a.camera.zoom = source.api.camera.zoom;
    a.camera.updateProjectionMatrix();
    a.controls.target.copy(source.api.controls.target);
  }
}

function caseDe(l) {
  let k = E.cases.get(l.job);
  if (k) return k;
  const el = document.createElement("figure");
  el.className = "cmp-case3d";
  el.dataset.job = l.job;
  el.innerHTML = `<div class="cmp-vue"><canvas></canvas><div class="cmp-etat"></div></div><figcaption></figcaption>`;
  $("#grille").appendChild(el);
  k = { el, api: null, url: null, tris: null };
  E.cases.set(l.job, k);
  return k;
}

async function montrer(k, l) {
  if (!l.glb || k.url === l.glb) return;
  k.url = l.glb;
  const cv = k.el.querySelector("canvas");
  if (!k.api) {
    k.api = creerCanevas(cv);
    k.api.controls.enableDamping = false;                 // une pose exacte, recopiée telle quelle aux autres
    cv.addEventListener("pointerdown", () => { E.pilote = k; });
    cv.addEventListener("wheel", () => { E.pilote = k; }, { passive: true });
    k.api.controls.addEventListener("change", () => { if (E.pilote === k) synchroniser(k); });
  }
  try {
    const r = await charger(k.api, l.glb);
    k.tris = r.tris;
    normaliser(k.api);
    appliquerRendu(k.api);
    orienter(k.api, E.vue);
    cadrer(k.api);
    const autre = [...E.cases.values()].find((x) => x !== k && x.api && x.api.racine);
    if (autre) { E.pilote = autre; synchroniser(autre); }
  } catch (e) {
    k.el.querySelector(".cmp-etat").textContent = T("grille.illisible", { m: e.message });
  }
}

function rendreGrille() {
  const tab = E.tab;
  const g = $("#grille");
  if (!tab) {
    g.innerHTML = `<div class="cmp-vide grand">${esc(T("grille.vide"))}</div>`;
    E.cases.clear();
    return;
  }
  const vide = g.querySelector(".cmp-vide");
  if (vide) vide.remove();
  for (const l of tab.lignes) {
    const k = caseDe(l);
    const etat = k.el.querySelector(".cmp-etat");
    etat.textContent = l.statut === "en_cours" ? T("statut.en_cours", { p: l.progression || 0 })
      : l.statut === "echec" ? T("statut.echec", { m: l.erreur || "" }) : l.statut === "absent" ? T("statut.absent") : "";
    etat.classList.toggle("hidden", !etat.textContent);
    k.el.classList.toggle("gagnant", !!l.gagnant);
    const ferme = l.ferme == null ? "" : l.ferme ? T("grille.etanche") : T("grille.ouvert", { n: nb(l.aretes_bord) });
    k.el.querySelector("figcaption").innerHTML = `<b>${esc(l.label)}</b>`
      + `<span>${esc(l.tris == null ? "—" : T("ex.tris", { n: nb(l.tris) }))}${ferme ? " · " + esc(ferme) : ""}</span>`
      + (l.gagnant ? `<span class="badge">${ico("dz-etat-meilleur")} ${esc(T("grille.garde"))}</span>`
        : l.statut === "termine" ? `<button class="cmp-garder" data-job="${esc(l.job)}" title="${esc(T("grille.garder_aide"))}">`
          + `${ico("dz-action-ajouter-bibliotheque")} ${esc(T("grille.garder"))}</button>` : "");
    const b = k.el.querySelector(".cmp-garder");
    if (b) b.addEventListener("click", () => garder(l.job));
    montrer(k, l);
  }
}

function rendreBarre() {
  const seg = (id, liste, actif) => `<div class="cmp-seg" role="group" id="${id}">` + liste.map(([v, cle, ic]) =>
    `<button data-v="${v}" class="${v === actif ? "on" : ""}" aria-pressed="${v === actif}">${ico(ic)} ${esc(T(cle))}</button>`).join("") + `</div>`;
  $("#barre").innerHTML = seg("cmpRendu", [["texture", "rendu.texture", "dz-lab3d-materiau"], ["argile", "rendu.argile", "dz-lab3d-sphere"],
    ["fil", "rendu.fil", "dz-lab3d-filaire"]], E.rendu)
    + seg("cmpVue", [["libre", "vue.libre", "dz-lab3d-rotation"], ["iso", "vue.iso", "dz-lab3d-cube"], ["face", "vue.face", "dz-lab3d-camera"],
      ["profil", "vue.profil", "dz-lab3d-orienter"], ["dessus", "vue.dessus", "dz-lab3d-plan"]], E.vue)
    + `<span class="cmp-note">${esc(T("barre.sync"))}</span>`;
  $("#cmpRendu").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    E.rendu = b.dataset.v; rendreBarre();
    for (const k of E.cases.values()) if (k.api) appliquerRendu(k.api);
  }));
  $("#cmpVue").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    E.vue = b.dataset.v; rendreBarre();
    for (const k of E.cases.values()) if (k.api) orienter(k.api, E.vue);
  }));
}

/* ── le tableau mesuré, triable ─────────────────────────────────────────── */

function rendreTableau() {
  const box = $("#tableau");
  const tab = E.tab;
  if (!tab) { box.innerHTML = ""; return; }
  const lignes = trier(tab.lignes, E.tri.cle, E.tri.desc);
  const meilleurs = Object.fromEntries(COLONNES.map((c) => [c.cle, meilleur(tab.lignes, c.cle)]));
  let h = `<table class="cmp-table"><thead><tr>` + COLONNES.map((c) => {
    const actif = E.tri.cle === c.cle;
    return `<th><button data-cle="${c.cle}" class="${actif ? "on" : ""}" aria-sort="${actif ? (E.tri.desc ? "descending" : "ascending") : "none"}">`
      + `${esc(c.titre())}</button></th>`;
  }).join("") + `</tr></thead><tbody>`;
  for (const l of lignes) {
    h += `<tr class="${l.gagnant ? "gagnant" : ""} ${l.statut !== "termine" ? "attente" : ""}">` + COLONNES.map((c) => {
      const best = meilleurs[c.cle] != null && l[c.cle] === meilleurs[c.cle] && l.statut === "termine";
      let txt = esc(cellule(l, c.cle));
      if (c.cle === "moteur") {
        txt = `<b>${txt}</b>` + (l.statut !== "termine" ? ` <small>${esc(T("statut." + l.statut, { p: l.progression || 0, m: "" }))}</small>`
          : l.ferme ? ` <small class="ok">${esc(T("grille.etanche"))}</small>` : "");
      }
      return `<td class="${best ? "best" : ""}" ${best ? `title="${esc(T("tableau.meilleur"))}"` : ""}>${txt}</td>`;
    }).join("") + `</tr>`;
  }
  h += `</tbody></table><div class="cmp-note">${esc(T("tableau.legende"))}</div>`;
  if (tab.mode === "tir") h += `<div class="cmp-note">${esc(T("tableau.total", { p: usd(tab.total_estime_usd) }))}</div>`;
  box.innerHTML = h;
  box.querySelectorAll("th button").forEach((b) => b.addEventListener("click", () => {
    const cle = b.dataset.cle;
    E.tri = { cle, desc: E.tri.cle === cle ? !E.tri.desc : false };
    rendreTableau();
  }));
}

/* ── ouvrir, suivre, garder ─────────────────────────────────────────────── */

async function ouvrirComparatif(id, deja) {
  if (E.sondage) { clearTimeout(E.sondage); E.sondage = null; }
  if (!E.tab || E.tab.id !== id) {
    for (const k of E.cases.values()) k.el.remove();
    E.cases.clear();
  }
  try {
    E.tab = deja || await jget(`/api/comparatif3d/${encodeURIComponent(id)}`);
  } catch (e) { avis(T("erreur.charger", { m: e.message }), true); return; }
  try { history.replaceState(null, "", `?id=${encodeURIComponent(id)}`); } catch { /* cadre sans historique */ }
  $("#titreTab").textContent = E.tab.mode === "tir" ? T("titre.tir", { image: E.tab.image_filename || "" }) : T("titre.existants");
  rendreGrille(); rendreTableau();
  if (E.tab.en_cours) E.sondage = setTimeout(() => ouvrirComparatif(id), 3000);
  else if ($("#cmpAvis").textContent === T("tir.en_route", { n: E.tab.lignes.length })) avis("");   // les tirs sont rentrés
}

function capturer(api) {
  api.renderer.render(api.scene, api.camera);          // le tampon est valide dans CETTE tâche
  const src = api.renderer.domElement, m = Math.max(src.width, src.height) || 1, k = Math.min(1, 512 / m);
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(src.width * k)); c.height = Math.max(1, Math.round(src.height * k));
  c.getContext("2d").drawImage(src, 0, 0, c.width, c.height);
  return c.toDataURL("image/png");
}

async function garder(job) {
  const k = E.cases.get(job);
  if (!k || !k.api || !k.api.racine || !E.tab) return;
  try {
    const r = await jpost(`/api/comparatif3d/${encodeURIComponent(E.tab.id)}/garder`, { job, poster: capturer(k.api) });
    avis(T("garder.ok", { f: r.filename }));
    await ouvrirComparatif(E.tab.id);
  } catch (e) { avis(T("garder.echec", { m: e.message }), true); }
}

/* ── branchements ───────────────────────────────────────────────────────── */

function choisirMode(m) {
  E.mode = m;
  document.querySelectorAll("#cmpOnglets button").forEach((b) => {
    const on = b.dataset.mode === m;
    b.classList.toggle("on", on); b.setAttribute("aria-selected", on ? "true" : "false");
  });
  $("#panTir").classList.toggle("hidden", m !== "tir");
  $("#panEx").classList.toggle("hidden", m !== "existants");
}

function poserTextes() {
  document.title = T("page.titre");
  $("#cmpRetour").innerHTML = `${ico("dz-action-retour")} ${esc(T("page.retour"))}`;
  $("#cmpTitre").textContent = T("page.titre_court");
  $("#cmpSous").textContent = T("page.sous_titre");
  $("#cmpOnglets").innerHTML = `<button role="tab" data-mode="tir">${esc(T("onglet.tir"))}</button>`
    + `<button role="tab" data-mode="existants">${esc(T("onglet.existants"))}</button>`;
  $("#cmpOnglets").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => choisirMode(b.dataset.mode)));
  $("#cmpHist").setAttribute("aria-label", T("hist.aide"));
  $("#titreTab").textContent = T("titre.aucun");
}

async function demarrer() {
  poserTextes();
  choisirMode("tir");
  rendreBarre();
  rendreGrille();
  const q = new URLSearchParams(location.search);
  try {
    E.images = ((await jget("/api/images")).images || []).sort((a, b) => (b.mtime || 0) - (a.mtime || 0)).map((i) => i.filename)
      .filter((f) => !/^shot_.+_comparatif(_\d+)?\.png$/.test(f));   // une vue gardée n'est pas une image source
  } catch { E.images = []; }
  E.image = q.get("image") && E.images.includes(q.get("image")) ? q.get("image") : (E.images[0] || "");
  await chargerDevis();
  try { E.modeles = (await jget("/api/comparatif3d/modeles")).modeles || []; } catch { E.modeles = []; }
  rendreExistants();
  $("#cmpHist").addEventListener("change", (ev) => { if (ev.target.value) ouvrirComparatif(ev.target.value); });
  await chargerHistorique();
  if (q.get("id")) await ouvrirComparatif(q.get("id"));
}

demarrer();

export { E, ouvrirComparatif };
