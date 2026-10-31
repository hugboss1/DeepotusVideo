/* t395 (31/10/2026) — écran RIG du 3D Studio (D3) : le rig semi-automatique LOCAL et gratuit, et l'auto-rig IA.

   Relevé de Sorceress (§5 de l'inventaire) : à gauche les 22 os SMPL et la fiche de l'os choisi (parent,
   coordonnées) ; au centre le modèle, ses articulations et ses os, un squelette de référence À CÔTÉ (décalage réglable),
   « clique un os pour l'ajuster », gizmo de translation, MIROIR, ENFANTS, Maj+clic, Échap, ombrages Fil / Solide /
   Texture / Tex+Fil / Poids (carte de chaleur de l'os choisi), axe de symétrie (guide X, ±1/±5, auto) ; à droite le
   SEMI-AUTOMATIQUE (ajuster, recommencer, os de poitrine, recalculer les poids) et l'AUTO-RIG IA.

   Chez nous : les articulations de départ viennent de GET /api/studio3d/rig/proposition (gabarit calé sur la boîte
   du modèle, ou le squelette déjà posé) ; « Recalculer les poids » envoie les articulations à POST …/appliquer, qui
   écrit une VERSION de plus (rig_local.py, Python pur) — le bandeau la montre riggée au rafraîchissement. L'auto-rig
   IA reprend la route payante existante (/api/assets/3d/{job}/rig) : devis, confirmation, puis suivi du job.
   Le calcul (squelette, miroir, enfants, sélection, corps de requête) vit dans rig_calc.js, testé sous node. */
"use strict";
import * as THREE from "three";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { creerCanevas, charger, vider, cadrer, orienter } from "/lib3d/viewer.js";
import { peindrePoids, retirerPoids } from "/lib3d/rig.js";
import { appliquerRendu, FIL } from "../rendu3d.js";
import { T, nb } from "./coque_calc.js";
import * as RC from "./rig_calc.js";

const R = {
  s: null, ctx: null, api: null, fiche: null, prop: null, joints: null, base: null, poitrine: false,
  sel: [], ajuster: false, miroir: true, avecEnfants: false, ombrage: "solide", vue: "face",
  ref: true, cranRef: 70, axe: 0, guide: true, devis: null, poll: null, occupe: false,
  scene: null, tc: null, pivot: null, dernier: null, glisse: false, appui: null, recouvrements: [],
};
const COUL = { l: 0x5fa8ff, r: 0xff7a5c, c: 0xe8e4dc, sel: 0xf2c14e, ref: 0x7b7f86 };

/* ── montage ──────────────────────────────────────────────────────────────── */
export async function monter(section, ctx) {
  R.s = section;
  R.ctx = ctx;
  const { esc, ico } = ctx;
  section.innerHTML = `<div class="ec-trois rg">
    <aside class="ec-gauche">
      <div class="ec-label" id="rgTitreOs"></div>
      <div class="rg-os" id="rgOs" role="listbox" aria-label="${esc(T("rigx.os_titre"))}"></div>
      <div class="ec-label">${esc(T("rigx.fiche_titre"))}</div>
      <div class="rg-fiche" id="rgFiche"></div>
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue rg-barre">
        <div class="ec-segments" id="rgOmbrage" role="group" aria-label="${esc(T("rigx.ombrage"))}">${RC.OMBRAGES.map((o) =>
          `<button data-ombrage="${o}">${esc(T("rigx.ombrage_" + o))}</button>`).join("")}</div>
        <div class="ec-segments" id="rgVues" role="group" aria-label="${esc(T("rigx.vue"))}">${RC.VUES.map((v) =>
          `<button data-vue="${v}">${esc(T("rigx.vue_" + v))}</button>`).join("")}</div>
      </div>
      <div class="ec-barre-vue rg-barre">
        <label class="ec-bascule"><input type="checkbox" id="rgRef" checked> ${esc(T("rigx.reference"))}</label>
        <label class="rg-curseur">${esc(T("rigx.decalage"))}
          <input type="range" id="rgDecalage" min="0" max="200" step="1" value="70" aria-label="${esc(T("rigx.decalage"))}">
          <span id="rgDecalageVal">70</span></label>
        <span class="rg-filet" aria-hidden="true"></span>
        <label class="ec-bascule" title="${esc(T("rigx.axe_aide"))}"><input type="checkbox" id="rgGuide" checked> ${esc(T("rigx.axe"))}</label>
        <div class="ec-segments" id="rgNudge">${[-5, -1, 1, 5].map((n) =>
          `<button data-nudge="${n}" title="${esc(T("rigx.nudge_aide"))}">${n > 0 ? "+" + n : n}</button>`).join("")}
          <button data-nudge="auto">${esc(T("rigx.axe_auto"))}</button></div>
        <span class="rg-axe" id="rgAxe"></span>
      </div>
      <div class="ec-vues"><figure class="ec-vue rg-vue"><canvas id="rgCanevas"></canvas>
        <div class="rg-ajuste hidden" id="rgAjuste">
          <span id="rgAjusteTexte"></span>
          <label class="ec-bascule"><input type="checkbox" id="rgMiroir" checked> ${esc(T("rigx.miroir"))}</label>
          <label class="ec-bascule"><input type="checkbox" id="rgEnfants"> ${esc(T("rigx.enfants"))}</label>
        </div>
        <figcaption id="rgCap"></figcaption></figure></div>
    </main>
    <aside class="ec-droite">
      <div class="ec-label rg-entete">${esc(T("rigx.semi_titre"))} <span class="ec-badge">${esc(T("rigx.gratuit"))}</span></div>
      <div class="ec-resume" id="rgResume"></div>
      <button class="ec-bouton bloc" id="rgAjuster">${ico("dz-lab3d-rig")} <span id="rgAjusterTexte"></span></button>
      <button class="ec-bouton bloc" id="rgRecommencer">${ico("dz-action-reinitialiser")} ${esc(T("rigx.recommencer"))}</button>
      <div class="ec-label">${esc(T("rigx.poitrine"))}</div>
      <div class="ec-segments ec-plein" id="rgPoitrine">
        <button data-poitrine="0">${esc(T("rigx.non"))}</button><button data-poitrine="1">${esc(T("rigx.oui"))}</button></div>
      <div class="ec-label">${esc(T("rigx.poids"))}</div>
      <button class="ec-principal" id="rgAppliquer">${ico("dz-lab3d-rig")} ${esc(T("rigx.recalculer"))}</button>
      <div class="ec-note">${esc(T("rigx.recalculer_aide"))}</div>
      <div class="ec-avis" id="rgAvis" role="status"></div>
      <div class="ec-label rg-entete">${esc(T("rigx.ia_titre"))} <span class="ec-badge discret">${esc(T("rigx.payant"))}</span></div>
      <div class="ec-note">${esc(T("rigx.ia_aide"))}</div>
      <label class="ec-champ">${esc(T("rigx.ia_hauteur"))}
        <input type="number" id="rgHauteur" min="0.2" max="20" step="0.05" value="1.7"></label>
      <button class="ec-bouton bloc" id="rgIA">${ico("dz-lab3d-rig")} <span id="rgIATexte">${esc(T("rigx.ia_bouton_sans"))}</span></button>
      <div class="ec-note" id="rgIARefus"></div>
      <div class="ec-avis" id="rgIAEtat" role="status"></div>
    </aside>
  </div>`;
  R.api = creerCanevas(section.querySelector("#rgCanevas"));
  R.scene = new THREE.Group();
  R.scene.name = "dzRig";
  R.api.scene.add(R.scene);
  R.pivot = new THREE.Object3D();
  R.api.scene.add(R.pivot);
  R.tc = new TransformControls(R.api.camera, R.api.renderer.domElement);
  R.tc.setMode("translate");
  R.tc.setSize(0.8);
  R.api.scene.add(R.tc.getHelper());
  R.tc.addEventListener("dragging-changed", (e) => {
    R.api.controls.enabled = !e.value;
    if (e.value) { R.glisse = true; R.dernier = R.pivot.position.clone(); }
  });
  R.tc.addEventListener("objectChange", surGizmo);

  const cv = section.querySelector("#rgCanevas");
  cv.addEventListener("pointerdown", (e) => { R.appui = [e.clientX, e.clientY]; R.glisse = false; }, true);
  cv.addEventListener("pointerup", surClicCanevas);
  document.addEventListener("keydown", surTouche);

  section.querySelector("#rgOmbrage").addEventListener("click", (e) => {
    const b = e.target.closest("[data-ombrage]");
    if (b) { R.ombrage = b.dataset.ombrage; ombrer(); peindreBarres(); }
  });
  section.querySelector("#rgVues").addEventListener("click", (e) => {
    const b = e.target.closest("[data-vue]");
    if (b) { R.vue = b.dataset.vue; cadrerTout(); peindreBarres(); }
  });
  section.querySelector("#rgRef").addEventListener("change", (e) => { R.ref = e.target.checked; dessiner(); });
  section.querySelector("#rgDecalage").addEventListener("input", (e) => {
    R.cranRef = +e.target.value;
    section.querySelector("#rgDecalageVal").textContent = String(R.cranRef);
    dessiner();
  });
  section.querySelector("#rgGuide").addEventListener("change", (e) => { R.guide = e.target.checked; dessiner(); });
  section.querySelector("#rgNudge").addEventListener("click", (e) => {
    const b = e.target.closest("[data-nudge]");
    if (!b || !R.prop) return;
    R.axe = b.dataset.nudge === "auto" ? RC.axeAuto(R.joints, R.prop.boite) : R.axe + RC.pasAxe(R.prop.hauteur, +b.dataset.nudge);
    dessiner();
  });
  section.querySelector("#rgMiroir").addEventListener("change", (e) => { R.miroir = e.target.checked; });
  section.querySelector("#rgEnfants").addEventListener("change", (e) => { R.avecEnfants = e.target.checked; });
  section.querySelector("#rgOs").addEventListener("click", (e) => {
    const b = e.target.closest("[data-os]");
    if (b) choisir(b.dataset.os, e.shiftKey);
  });
  section.querySelector("#rgFiche").addEventListener("change", surCoordonnee);
  section.querySelector("#rgAjuster").addEventListener("click", () => { R.ajuster = !R.ajuster; if (!R.ajuster) R.sel = []; peindre(); });
  section.querySelector("#rgRecommencer").addEventListener("click", recommencer);
  section.querySelector("#rgPoitrine").addEventListener("click", (e) => {
    const b = e.target.closest("[data-poitrine]");
    if (!b) return;
    R.poitrine = b.dataset.poitrine === "1";
    if (R.poitrine && R.prop) for (const i of RC.ordre(true)) if (!R.joints[i]) R.joints[i] = [...R.prop.poitrine[i]];
    R.sel = R.sel.filter((i) => RC.ordre(R.poitrine).includes(i));
    sale();
    peindre();
  });
  section.querySelector("#rgAppliquer").addEventListener("click", appliquer);
  section.querySelector("#rgIA").addEventListener("click", () => autoRigIA().catch((e) => avisIA(T("rigx.erreur", { m: e.message }))));
  peindre();
}

export function montre() { if (R.api && R.api.racine) cadrerTout(); }

/* ── le modèle ouvert ─────────────────────────────────────────────────────── */
export async function ouvrir(fiche) {
  if (!R.s) return;
  R.fiche = fiche;
  R.sel = [];
  R.prop = null;
  R.joints = null;
  clearInterval(R.poll);
  avis("");
  if (!fiche) { vider(R.api); dessiner(); peindre(); return; }
  const q = `?version=${encodeURIComponent(fiche.version)}`;
  const [prop] = await Promise.all([
    R.ctx.jget(`/api/studio3d/rig/proposition/${encodeURIComponent(fiche.job)}${q}`).catch((e) => {
      avis(T("rigx.erreur_proposition", { m: e.message }));
      return null;
    }),
    charger(R.api, fiche.url).catch(() => null),
  ]);
  if (R.fiche !== fiche) return;     // un autre modèle a été ouvert pendant le chargement
  R.prop = prop;
  if (prop) {
    R.poitrine = !!prop.avec_poitrine;
    R.joints = { ...prop.joints, ...prop.poitrine };
    for (const k of Object.keys(R.joints)) R.joints[k] = [...R.joints[k]];
    R.base = JSON.parse(JSON.stringify(R.joints));
    R.axe = prop.axe_x;
    R.ajuster = prop.source !== "rig";
    const dec = RC.decimales(prop.hauteur);
    R.pas = Math.pow(10, -dec);
  }
  ombrer();
  cadrerTout();
  peindre();
  devisIA();
}

/* ── peinture des panneaux ────────────────────────────────────────────────── */
function peindre() {
  peindreListe();
  peindreFiche();
  peindreDroite();
  peindreBarres();
  dessiner();
}

function peindreBarres() {
  const s = R.s;
  for (const b of s.querySelectorAll("#rgOmbrage [data-ombrage]")) b.classList.toggle("on", b.dataset.ombrage === R.ombrage);
  for (const b of s.querySelectorAll("#rgVues [data-vue]")) b.classList.toggle("on", b.dataset.vue === R.vue);
  s.querySelector("#rgAxe").textContent = R.prop ? T("rigx.axe_valeur", { x: R.axe.toFixed(RC.decimales(R.prop.hauteur)) }) : "";
}

function peindreListe() {
  const { esc } = R.ctx;
  const ids = RC.ordre(R.poitrine);
  R.s.querySelector("#rgTitreOs").textContent = T("rigx.os_n", { n: ids.length });
  R.s.querySelector("#rgOs").innerHTML = ids.map((i) => {
    const c = RC.cote(i) || "c";
    return `<button class="rg-ligne ${R.sel.includes(i) ? "on" : ""}" data-os="${i}" role="option" aria-selected="${R.sel.includes(i)}"
      style="--prof:${RC.profondeur(i)}" ${R.joints ? "" : "disabled"}><span class="rg-pastille rg-${c}" aria-hidden="true"></span>${esc(T("rigx.os_" + i))}</button>`;
  }).join("");
}

function peindreFiche() {
  const { esc } = R.ctx;
  const el = R.s.querySelector("#rgFiche");
  const id = R.sel[0];
  if (!id || !R.joints || !R.joints[id]) { el.innerHTML = `<div class="ec-note">${esc(T(R.joints ? "rigx.fiche_vide" : "rigx.sans_modele"))}</div>`; return; }
  const p = R.joints[id], par = RC.parentDe(id);
  const dec = RC.decimales(R.prop && R.prop.hauteur);
  el.innerHTML = `<b class="rg-nom">${esc(T("rigx.os_" + id))}</b> <code>${esc(id)}</code>
    <dl class="ec-fiche"><dt>${esc(T("rigx.parent"))}</dt><dd>${esc(par ? T("rigx.os_" + par) : T("rigx.racine"))}</dd>
    <dt>${esc(T("rigx.enfants_n"))}</dt><dd>${esc(nb(RC.enfants(id, R.poitrine).length))}</dd></dl>
    <div class="rg-xyz">${["x", "y", "z"].map((a, k) => `<label class="ec-champ">${a.toUpperCase()}
      <input type="number" data-axe="${k}" step="${R.pas || 0.001}" value="${p[k].toFixed(dec)}"></label>`).join("")}</div>`
    + (R.sel.length > 1 ? `<div class="ec-note">${esc(T("rigx.selection_n", { n: R.sel.length }))}</div>` : "");
}

function peindreDroite() {
  const { esc } = R.ctx;
  const f = R.fiche, rig = (f && f.rig) || {};
  const n = RC.ordre(R.poitrine).length;
  R.s.querySelector("#rgResume").innerHTML = !f ? esc(T("rigx.sans_modele"))
    : `${esc(T("rigx.squelette_n", { n }))} · ` + (rig.rigge
      ? `<b>${esc(T("rigx.etat_rigge", { v: f.version, n: nb(rig.os) }))}</b>` : `<span>${esc(T("rigx.etat_non_rigge"))}</span>`)
      + (R.prop ? ` · <span>${esc(T("rigx.pose_" + R.prop.pose.toLowerCase()))}</span>` : "");
  R.s.querySelector("#rgAjusterTexte").textContent = T(R.ajuster ? "rigx.quitter_ajuster" : "rigx.ajuster");
  for (const b of R.s.querySelectorAll("#rgPoitrine [data-poitrine]")) b.classList.toggle("on", (b.dataset.poitrine === "1") === R.poitrine);
  const pret = !!(f && R.joints && !RC.manquants(R.joints, R.poitrine).length);
  R.s.querySelector("#rgAppliquer").disabled = !pret || R.occupe;
  R.s.querySelector("#rgAjuster").disabled = !R.joints;
  R.s.querySelector("#rgRecommencer").disabled = !R.prop;
  const aj = R.s.querySelector("#rgAjuste");
  aj.classList.toggle("hidden", !R.ajuster || !R.joints);
  R.s.querySelector("#rgAjusteTexte").textContent = R.sel.length
    ? T("rigx.ajuste_bandeau", { os: R.sel.map((i) => i.toUpperCase()).join(" + ") }) : T("rigx.ajuste_cliquer");
  R.s.querySelector("#rgCap").textContent = !f ? "" : T("rigx.legende", { v: f.version });
}

/* ── la scène : articulations, os, référence, axe ─────────────────────────── */
function vider3d(g) {
  for (const o of [...g.children]) {
    g.remove(o);
    if (o.geometry) o.geometry.dispose();
    if (o.material && o.material.dispose) o.material.dispose();
  }
}

function lignes(segs, couleur, opacite = 1) {
  const pos = new Float32Array(segs.length * 6);
  segs.forEach(([a, b], k) => pos.set([...a, ...b], k * 6));
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const m = new THREE.LineBasicMaterial({ color: couleur, depthTest: false, transparent: true, opacity: opacite });
  const l = new THREE.LineSegments(g, m);
  l.renderOrder = 998;
  return l;
}

/* `garder` : appelé PENDANT un glisser du gizmo — on ne détache rien (détacher couperait le geste en cours) */
function dessiner(garder = false) {
  if (!R.scene) return;
  vider3d(R.scene);
  if (!garder) R.tc.detach();
  if (!R.joints || !R.prop) return;
  const h = R.prop.hauteur;
  const rayon = Math.max(1e-4, h * 0.012);
  const geo = new THREE.SphereGeometry(rayon, 14, 10);
  const ids = RC.ordre(R.poitrine);
  for (const i of ids) {
    const c = R.sel.includes(i) ? COUL.sel : COUL[RC.cote(i) || "c"];
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: c, depthTest: false, transparent: true }));
    m.position.set(...R.joints[i]);
    m.renderOrder = 999;
    m.userData.os = i;
    R.scene.add(m);
  }
  const segs = RC.segmentsOs(R.joints, R.poitrine);
  R.scene.add(lignes(segs.filter((s) => !R.sel.includes(s[2])), 0xd9d4ca, 0.9));
  if (R.sel.length) R.scene.add(lignes(segs.filter((s) => R.sel.includes(s[2])), COUL.sel));
  if (R.ref) {
    const ref = RC.decaler({ ...R.prop.gabarit.joints, ...(R.poitrine ? R.prop.gabarit.poitrine : {}) },
      RC.decalageReference(R.cranRef, h));
    R.scene.add(lignes(RC.segmentsOs(ref, R.poitrine), COUL.ref, 0.85));
    const g2 = new THREE.SphereGeometry(rayon * 0.7, 10, 8);
    for (const p of Object.values(ref)) {
      const m = new THREE.Mesh(g2, new THREE.MeshBasicMaterial({ color: COUL.ref }));
      m.position.set(...p);
      R.scene.add(m);
    }
  }
  if (R.guide) {
    const b = R.prop.boite;
    const z = (b.min[2] + b.max[2]) / 2;
    R.scene.add(lignes([[[R.axe, b.min[1] - 0.05 * h, z], [R.axe, b.max[1] + 0.05 * h, z]]], 0xf2c14e, 0.6));
  }
  if (!garder && R.ajuster && R.sel.length) {
    R.pivot.position.set(...R.joints[R.sel[0]]);
    R.tc.attach(R.pivot);
  }
}

function cadrerTout() {
  if (!R.api || !R.api.racine) return;
  orienter(R.api, R.vue);
  if (R.ref && R.prop) {   // la référence est à droite du modèle : le cadre recule et se centre entre les deux
    const dx = RC.decalageReference(R.cranRef, R.prop.hauteur) / 2;
    cadrer(R.api, 1.35 + dx / Math.max(1e-6, R.prop.hauteur));
    R.api.controls.target.x += dx;
    R.api.camera.position.x += dx;
    R.api.controls.update();
  }
}

/* ── ombrages : Fil, Solide, Texture, Tex+Fil, Poids ─────────────────────── */
function ombrer() {
  const api = R.api;
  for (const o of R.recouvrements) { if (o.parent) o.parent.remove(o); }
  R.recouvrements = [];
  retirerPoids(api);
  if (!api.racine) return;
  const mode = R.ombrage;
  appliquerRendu(api.racine, mode === "fil" ? "fil" : mode === "solide" ? "argile" : "texture");
  if (mode === "texfil") {
    const maillages = [];
    api.racine.traverse((o) => { if (o.isMesh) maillages.push(o); });
    for (const o of maillages) {
      const w = o.clone(false);
      w.material = FIL;
      w.userData = {};
      w.renderOrder = 2;
      o.parent.add(w);
      R.recouvrements.push(w);
    }
  }
  if (mode === "poids") {
    const rigge = !!(R.fiche && R.fiche.rig && R.fiche.rig.rigge);
    if (!rigge) { appliquerRendu(api.racine, "argile"); avis(T("rigx.poids_absents")); return; }
    const touches = peindrePoids(api, R.sel[0] || "pelvis");
    avis(T("rigx.poids_os", { os: T("rigx.os_" + (R.sel[0] || "pelvis")), n: nb(touches) }));
  }
}

/* ── gestes ───────────────────────────────────────────────────────────────── */
function choisir(id, maj) {
  if (!R.joints) return;
  R.sel = RC.selectionner(R.sel, id, maj);
  if (R.sel.length && !R.ajuster) R.ajuster = true;
  peindre();
  if (R.ombrage === "poids") ombrer();
}

function surClicCanevas(e) {
  const a = R.appui;
  R.appui = null;
  if (!a || R.glisse || Math.hypot(e.clientX - a[0], e.clientY - a[1]) > 4 || !R.joints) return;
  const cv = e.currentTarget, r = cv.getBoundingClientRect();
  const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(ndc, R.api.camera);
  const cibles = R.scene.children.filter((o) => o.isMesh && o.userData.os);
  const hit = ray.intersectObjects(cibles, false)[0];
  if (hit) choisir(hit.object.userData.os, e.shiftKey);
}

function surTouche(e) {
  if (e.key !== "Escape" || !R.s || R.s.classList.contains("hidden") || !R.sel.length) return;
  if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
  R.sel = [];
  peindre();
}

function opts() {
  return { miroir: R.miroir, avecEnfants: R.avecEnfants, axe: R.axe, avecPoitrine: R.poitrine };
}

function surGizmo() {
  if (!R.dernier || !R.sel.length) return;
  const p = R.pivot.position;
  const d = [p.x - R.dernier.x, p.y - R.dernier.y, p.z - R.dernier.z];
  R.dernier = p.clone();
  R.joints = RC.deplacer(R.joints, R.sel, d, opts());
  sale();
  dessiner(true);
  peindreFiche();
}

function surCoordonnee(e) {
  const k = e.target.dataset && e.target.dataset.axe;
  const id = R.sel[0];
  if (k == null || !id) return;
  const v = parseFloat(e.target.value);
  if (!Number.isFinite(v)) return;
  const p = [...R.joints[id]];
  p[+k] = v;
  R.joints = RC.poser(R.joints, id, p, opts());
  sale();
  dessiner();
}

function sale() {
  R.ctx.marquerSale(RC.differe(R.joints, R.base, R.poitrine));
}

function recommencer() {
  if (!R.prop) return;
  R.joints = { ...R.prop.gabarit.joints, ...R.prop.gabarit.poitrine };
  for (const k of Object.keys(R.joints)) R.joints[k] = [...R.joints[k]];
  R.axe = R.prop.gabarit.axe_x;
  R.sel = [];
  R.ajuster = true;
  sale();
  avis(T("rigx.recommence"));
  peindre();
}

/* ── écrire : squelette + poids → version ─────────────────────────────────── */
async function appliquer() {
  const f = R.fiche;
  if (!f || !R.joints || R.occupe) return;
  R.occupe = true;
  peindreDroite();
  avis(T("rigx.en_cours"));
  try {
    const r = await fetch(`/api/studio3d/rig/appliquer/${encodeURIComponent(f.job)}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(RC.corps(R.joints, { version: f.version, avecPoitrine: R.poitrine })) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
    R.occupe = false;
    await R.ctx.rafraichir();
    avis(T("rigx.fait", { v: j.version, os: j.os, n: nb(j.sommets) }));
  } catch (e) {
    avis(T("rigx.erreur", { m: e.message }));
  } finally {
    R.occupe = false;
    peindreDroite();
  }
}

/* ── auto-rig IA (Meshy, payant) : devis, confirmation, route existante ───── */
async function devisIA() {
  const f = R.fiche;
  R.devis = null;
  if (f) {
    try { R.devis = await R.ctx.jget(`/api/assets/3d/${encodeURIComponent(f.job)}/rig/devis`); } catch { R.devis = null; }
  }
  peindreIA();
}

function peindreIA() {
  const d = R.devis, non = RC.refusIA(d);
  const cr = d && d.credits ? Math.round(d.credits.meshy || 0) : 0;
  R.s.querySelector("#rgIATexte").textContent = d ? T("rigx.ia_bouton", { cr, usd: Number(d.total_usd || 0).toFixed(2) })
    : T("rigx.ia_bouton_sans");
  R.s.querySelector("#rgIA").disabled = !!non || !R.fiche;
  R.s.querySelector("#rgIARefus").textContent = non ? T(non) : "";
}

function avisIA(t) { R.s.querySelector("#rgIAEtat").textContent = t; }
function avis(t) { if (R.s) R.s.querySelector("#rgAvis").textContent = t; }

async function autoRigIA() {
  const f = R.fiche, d = R.devis;
  if (!f || RC.refusIA(d)) return;
  const cr = Math.round((d.credits && d.credits.meshy) || 0);
  const dlg = window.__dzDialogue;
  if (!dlg || !dlg.confirmer) return;
  const detail = (d.breakdown || []).map((l) => `· ${l.label} : ${l.units} cr`).join("\n");
  const ok = await dlg.confirmer(T("rigx.ia_confirmer", { nom: f.nom || f.job, cr, usd: Number(d.total_usd || 0).toFixed(2) })
    + (detail ? "\n" + detail : ""), { titre: T("rigx.ia_titre"), ok: T("rigx.ia_payer", { cr }) });
  if (!ok) return;
  const h = Math.min(20, Math.max(0.2, Number(R.s.querySelector("#rgHauteur").value) || 1.7));
  R.s.querySelector("#rgIA").disabled = true;
  const r = await fetch(`/api/assets/3d/${encodeURIComponent(f.job)}/rig`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ height_m: h, actions: [], confirme_cout: true }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) { peindreIA(); throw new Error((j.detail && j.detail.message) || j.detail || String(r.status)); }
  avisIA(T("rigx.ia_file"));
  clearInterval(R.poll);
  R.poll = setInterval(async () => {
    const e = await R.ctx.jget(`/api/jobs/${encodeURIComponent(j.job_id)}`).catch(() => null);
    if (!e) return;
    avisIA(`${e.current_step || ""} ${e.progress || 0} %`);
    if (e.status === "done" || e.status === "failed") {
      clearInterval(R.poll);
      if (e.status === "done") { avisIA(T("rigx.ia_fait")); await R.ctx.rafraichir(); } else avisIA(T("rigx.erreur", { m: e.error || "?" }));
    }
  }, 2500);
}
