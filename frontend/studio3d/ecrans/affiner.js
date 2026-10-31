/* t396 + t397 (31/10/2026) — écran AFFINER du 3D Studio : la peinture des poids de peau et les corrections
   automatiques.

   Relevé de Sorceress (§6 de l'inventaire, « Refine ») :
   - à gauche le TEST DE POSE (jouer un clip enregistré, peindre sur la pose déformée, revenir à la pose de liaison)
     et les CORRECTIONS : correctif en un clic, 1 orphelins (tout / l'os), 2 confinement (force 70 %, tous les membres /
     cet os, reconstruire l'épaule), 3 coutures (N anneaux, seulement les déformées, tout / cet os), 4 guérison ;
   - en haut Annuler / Rétablir, les vues Poids / Texturé / Ombré / Fil, les outils Choisir l'os (1), Peindre (2),
     Lasso (3, Alt = orbite), Pose (P), le Miroir (M) ;
   - à droite POIDS : Os (4) / Isoler (5), sommets sans poids (clic droit pour assigner), taille, force, atténuation,
     les cinq opérations (Fixer R · Ajouter A · Retirer S · Lisser D · Flouter F), la liste des os ;
   - la barre d'état : modèle chargé, raccourcis `[ ]`, Ctrl + molette (rayon), Maj + molette (force).

   Chez nous : les POIDS sont lus dans le GLB par three.js (skinIndex / skinWeight, quatre par sommet) et repeints sur
   place ; « Enregistrer » envoie les seuls sommets touchés à POST /api/studio3d/affiner/enregistrer (une VERSION de
   plus). Le pinceau vise la pose COURANTE : les positions sont celles de la peau déformée (SkinnedMesh.getVertexPosition
   applique applyBoneTransform), le rayon est en unités du modèle. Les corrections passent par POST …/corriger
   (poids_corrections.py, Python pur) : chacune écrit une version, sauf le « Scan » des orphelins (aperçu). Le test de
   pose joue les clips du GLB et ceux du job (AnimationMixer), ou des POSES D'ESSAI d'amplitude (bras levés, coudes,
   hanches, genoux, cou) — un modèle qui sort du Rig n'a pas encore de clip. La guérison et « seulement les déformées »
   reçoivent la pose courante (quaternions locaux relatifs au repos), ou quelques images du clip.
   L'outil Pose tourne un os (gizmo de rotation) : pas de cinématique inverse (les poignées IK de Sorceress).
   Le calcul vit dans poids_calc.js (banc node). */
"use strict";
import * as THREE from "three";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { creerCanevas, charger, vider, cadrer } from "/lib3d/viewer.js";
import { poserSquelette, retirerSquelette, surlignerChaine } from "/lib3d/rig.js";
import { appliquerRendu } from "../rendu3d.js";
import { T, nb } from "./coque_calc.js";
import { listeGeneres } from "./animer_calc.js";
import * as PC from "./poids_calc.js";

const A = {
  s: null, ctx: null, fiche: null, api: null, resume: null, maillages: [], noms: [], os: null,
  outil: "peindre", mode: "ajouter", miroir: true, isoler: false, panneau: "os", vue: "poids",
  taille: 0.05, force: 0.15, attenuation: "douce", hauteur: 1, hist: new PC.Historique(),
  trait: null, peint: false, lasso: null, libres: null, curseur: null, tc: null, matPoids: null,
  mixer: null, action: null, clips: new Map(), clip: null, pose: null, joue: false, repos: new Map(), version: 0,
  generes: [], occupe: false, avis: "", erreur: "", anneaux: 3, deformees: false, forceConf: 0.7, rapport: null,
  charge: null, appui: null,
};
const $ = (sel) => A.s.querySelector(sel);
let _loader = null;
const loader = () => (_loader = _loader || new GLTFLoader());

async function lireJson(r) {
  const t = await r.text();
  let j = {};
  try { j = t ? JSON.parse(t) : {}; } catch { j = { detail: t }; }
  if (!r.ok) {
    const d = j && j.detail;
    throw Object.assign(new Error(typeof d === "string" ? d : (d && d.message) || String(r.status)), { status: r.status });
  }
  return j;
}
const poster = async (url, corps) => lireJson(await fetch(url, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) }));

/* ── montage ──────────────────────────────────────────────────────────────── */

export async function monter(section, ctx) {
  A.s = section;
  A.ctx = ctx;
  const { esc, ico } = ctx;
  const seg = (id, liste, cle, attr) => `<div class="ec-segments" id="${id}" role="group">${liste.map((x) =>
    `<button data-${attr}="${x}" title="${esc(T(`aff.${cle}_${x}_aide`))}">${esc(T(`aff.${cle}_${x}`))}</button>`).join("")}</div>`;
  section.innerHTML = `<div class="ec-trois af">
    <aside class="ec-gauche af-gauche">
      <div class="ec-label">${esc(T("aff.pose_titre"))}</div>
      <div class="ec-note">${esc(T("aff.pose_aide"))}</div>
      <div class="af-clips" id="afClips"></div>
      <div class="af-ligne">
        <button class="ec-bouton" id="afJouer">${ico("dz-media-lecture")} <span id="afJouerTexte">${esc(T("aff.jouer"))}</span></button>
        <button class="ec-bouton" id="afLiaison" title="${esc(T("aff.liaison_aide"))}">${ico("dz-action-reinitialiser")} ${esc(T("aff.liaison"))}</button>
      </div>
      <div class="ec-label af-entete">${esc(T("aff.corr_titre"))} <span class="ec-badge">${esc(T("aff.gratuit"))}</span></div>
      <button class="ec-principal" id="afTout" title="${esc(T("aff.tout_aide"))}">${ico("dz-lab3d-rig")} ${esc(T("aff.tout"))}</button>
      <div class="ec-note">${esc(T("aff.tout_note"))}</div>
      <div class="af-etape"><b>1</b> ${esc(T("aff.op_orphelins"))}</div>
      <div class="af-ligne">
        <button class="ec-bouton" data-corr="orphelins" data-apercu="1">${esc(T("aff.scan_tout"))}</button>
        <button class="ec-bouton" data-corr="orphelins" data-apercu="1" data-cet-os="1">${esc(T("aff.scan_os"))}</button>
        <button class="ec-bouton" data-corr="orphelins">${esc(T("aff.retirer_ilots"))}</button>
      </div>
      <div class="af-etape"><b>2</b> ${esc(T("aff.op_confinement"))}</div>
      <label class="af-curseur">${esc(T("aff.force_rognage"))}
        <input type="range" id="afForceConf" min="0" max="100" step="5" value="70"><span id="afForceConfVal">70 %</span></label>
      <div class="af-ligne">
        <button class="ec-bouton" data-corr="confinement">${esc(T("aff.contenir_tout"))}</button>
        <button class="ec-bouton" data-corr="confinement" data-cet-os="1">${esc(T("aff.contenir_os"))}</button>
      </div>
      <button class="ec-bouton bloc" data-corr="epaules">${esc(T("aff.op_epaules"))}</button>
      <div class="af-etape"><b>3</b> ${esc(T("aff.op_coutures"))}</div>
      <label class="af-curseur">${esc(T("aff.anneaux"))}
        <input type="range" id="afAnneaux" min="1" max="8" step="1" value="3"><span id="afAnneauxVal">3</span></label>
      <label class="ec-bascule"><input type="checkbox" id="afDeformees"> ${esc(T("aff.deformees"))}</label>
      <div class="af-ligne">
        <button class="ec-bouton" data-corr="coutures">${esc(T("aff.adoucir_tout"))}</button>
        <button class="ec-bouton" data-corr="coutures" data-cet-os="1">${esc(T("aff.adoucir_os"))}</button>
      </div>
      <div class="af-etape"><b>4</b> ${esc(T("aff.op_guerison"))}</div>
      <button class="ec-bouton bloc" data-corr="guerison"><span id="afGuerirTexte">${esc(T("aff.guerir_batterie"))}</span></button>
      <div class="ec-avis" id="afRapport" role="status"></div>
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue af-barre">
        <button class="ec-bouton" id="afAnnuler" title="${esc(T("aff.annuler_aide"))}">${ico("dz-action-annuler")} ${esc(T("aff.annuler"))}</button>
        <button class="ec-bouton" id="afRetablir" title="${esc(T("aff.retablir_aide"))}">${ico("dz-action-retablir")} ${esc(T("aff.retablir"))}</button>
        <span class="af-filet" aria-hidden="true"></span>
        ${seg("afVues", PC.VUES, "vue", "vue")}
        <span class="af-filet" aria-hidden="true"></span>
        ${seg("afOutils", PC.OUTILS, "outil", "outil")}
        <label class="ec-bascule" title="${esc(T("aff.miroir_aide"))}"><input type="checkbox" id="afMiroir" checked> ${esc(T("aff.miroir"))}</label>
      </div>
      <div class="ec-vues"><figure class="ec-vue af-vue" id="afFigure"><canvas id="afCanevas" tabindex="0"></canvas>
        <svg class="af-lasso" id="afLasso" aria-hidden="true"><polyline id="afLassoTrace" points=""></polyline></svg>
        <div class="af-sans-rig hidden" id="afSansRig"><p id="afSansRigTexte"></p>
          <button class="ec-principal" id="afAllerRig">${ico("dz-lab3d-rig")} ${esc(T("aff.aller_rig"))}</button></div>
        <figcaption id="afCap"></figcaption></figure></div>
      <div class="af-etat" id="afEtat"></div>
    </main>
    <aside class="ec-droite af-droite">
      <div class="ec-label">${esc(T("aff.poids_titre"))}</div>
      <div class="ec-segments ec-plein" id="afPanneau" role="group">
        <button data-panneau="os">${esc(T("aff.panneau_os"))}</button><button data-panneau="isoler">${esc(T("aff.panneau_isoler"))}</button></div>
      <button class="ec-bouton bloc" id="afLibres">${ico("dz-action-tout-selectionner")} <span id="afLibresTexte">${esc(T("aff.libres"))}</span></button>
      <div class="ec-note" id="afLibresNote">${esc(T("aff.libres_aide"))}</div>
      <label class="af-curseur">${esc(T("aff.taille"))}
        <input type="range" id="afTaille" min="0.5" max="50" step="0.5" value="5"><span id="afTailleVal"></span></label>
      <label class="af-curseur">${esc(T("aff.force"))}
        <input type="range" id="afForce" min="1" max="100" step="1" value="15"><span id="afForceVal"></span></label>
      <div class="ec-label">${esc(T("aff.attenuation"))}</div>
      ${seg("afAttenuation", PC.ATTENUATIONS, "attenuation", "attenuation").replace('class="ec-segments"', 'class="ec-segments ec-plein"')}
      <div class="ec-label">${esc(T("aff.operations"))}</div>
      ${seg("afModes", PC.MODES, "mode", "mode").replace('class="ec-segments"', 'class="ec-segments ec-plein af-modes"')}
      <div class="ec-label" id="afOsTitre"></div>
      <div class="af-os" id="afOs" role="listbox" aria-label="${esc(T("aff.os_titre"))}"></div>
      <button class="ec-principal" id="afEnregistrer">${ico("dz-action-enregistrer")} <span id="afEnregistrerTexte">${esc(T("aff.enregistrer"))}</span></button>
      <div class="ec-avis" id="afAvis" role="status"></div>
    </aside>
  </div>`;

  A.api = creerCanevas($("#afCanevas"));
  A.matPoids = new THREE.MeshLambertMaterial({ vertexColors: true });
  A.curseur = new THREE.Mesh(new THREE.RingGeometry(0.92, 1, 48),
    new THREE.MeshBasicMaterial({ color: 0xf2c14e, depthTest: false, transparent: true, opacity: 0.9, side: THREE.DoubleSide }));
  A.curseur.renderOrder = 1001;
  A.curseur.visible = false;
  A.api.scene.add(A.curseur);
  A.tc = new TransformControls(A.api.camera, A.api.renderer.domElement);
  A.tc.setMode("rotate");
  A.tc.setSize(0.7);
  A.api.scene.add(A.tc.getHelper());
  A.tc.addEventListener("dragging-changed", (e) => { A.api.controls.enabled = !e.value; });
  A.tc.addEventListener("objectChange", () => { A.version++; A.pose = A.pose || "libre"; majPoseUI(); });

  const fig = $("#afFigure");
  fig.addEventListener("pointerdown", surAppui, true);
  fig.addEventListener("pointermove", surDeplacement, true);
  fig.addEventListener("pointerup", surRelache, true);
  fig.addEventListener("pointerleave", () => { A.curseur.visible = false; });
  fig.addEventListener("wheel", surMolette, { capture: true, passive: false });
  fig.addEventListener("contextmenu", surClicDroit);
  document.addEventListener("keydown", surTouche);

  section.addEventListener("click", surClic);
  section.addEventListener("input", surSaisie);
  section.addEventListener("change", surSaisie);
  boucle();
  peindre();
}

export function montre() { if (A.api && A.api.racine) peindre(); }

/* ── le modèle ouvert ─────────────────────────────────────────────────────── */

export async function ouvrir(fiche) {
  if (!A.s) return;
  A.fiche = fiche;
  A.rapport = null;
  A.avis = ""; A.erreur = "";
  const cle = fiche ? `${fiche.job}#${fiche.version}` : null;
  if (cle && cle === A.charge && A.api.racine) { peindre(); return; }
  A.charge = cle;
  arreter();
  A.tc.detach();
  A.maillages = []; A.noms = []; A.os = null; A.resume = null; A.libres = null; A.pose = null; A.clip = null;
  A.hist.vider();
  A.clips.clear();
  retirerSquelette(A.api);
  vider(A.api);
  A.ctx.marquerSale(false);
  if (!fiche) { peindre(); return; }
  const rigge = !!(fiche.rig && fiche.rig.rigge);
  const q = `?version=${encodeURIComponent(fiche.version)}`;
  const [res] = await Promise.all([
    rigge ? lireJson(await fetch(`/api/studio3d/affiner/poids/${encodeURIComponent(fiche.job)}${q}`)).catch((e) => {
      A.erreur = T("aff.erreur", { m: e.message }); return null; }) : null,
    charger(A.api, fiche.url).catch((e) => { A.erreur = T("aff.erreur", { m: e.message }); return null; }),
  ]);
  if (A.fiche !== fiche) return;
  A.resume = res;
  preparerMaillages();
  if (A.maillages.length) {
    poserSquelette(A.api);
    cadrer(A.api, 1.3);
    A.mixer = new THREE.AnimationMixer(A.api.racine);
    for (const c of (A.api.gltf && A.api.gltf.animations) || []) A.clips.set("clip:" + c.name, { cle: "clip:" + c.name, nom: c.name, clip: c, origine: "clip" });
    chargerGeneres(fiche);
    const pelvis = A.noms.find((n) => PC.role(n) === "bassin") || A.noms[0];
    choisirOs(pelvis, false);
  }
  vue();
  peindre();
}

function preparerMaillages() {
  const r = A.api.racine;
  if (!r) return;
  const assoc = A.api.gltf && A.api.gltf.parser && A.api.gltf.parser.associations;
  const parGeo = new Map();
  r.updateMatrixWorld(true);
  r.traverse((o) => {
    if (!o.isSkinnedMesh || !o.geometry.attributes.skinIndex || !o.geometry.attributes.skinWeight) return;
    const g = o.geometry;
    const a = assoc && assoc.get(o);
    let m = parGeo.get(g.uuid);
    if (!m) {
      const si = g.attributes.skinIndex, sw = g.attributes.skinWeight, n = si.count;
      const j = new Uint16Array(n * 4), w = new Float32Array(n * 4);
      for (let v = 0; v < n; v++) for (let k = 0; k < 4; k++) { j[v * 4 + k] = si.getComponent(v, k); w[v * 4 + k] = sw.getComponent(v, k); }
      const P = { n, j, w };
      /* les poids repeints sont ceux que le nuanceur lit : les tableaux de P DEVIENNENT les attributs */
      g.setAttribute("skinIndex", new THREE.BufferAttribute(P.j, 4));
      g.setAttribute("skinWeight", new THREE.BufferAttribute(P.w, 4));
      g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
      const pos = g.attributes.position.array;
      const canon = PC.souder(pos, n);
      g.computeBoundingBox();
      const bb = g.boundingBox;
      const taille = Math.max(bb.max.x - bb.min.x, bb.max.y - bb.min.y, bb.max.z - bb.min.z) || 1;
      const adj = PC.adjacence(g.index ? g.index.array : null, n, canon);
      /* un modèle généré n'est pas exactement symétrique : le reflet d'un sommet est le sommet le plus proche à moins
         d'une arête et demie (ou de 1 % de la taille) */
      const tol = Math.max(taille * 0.01, 1.5 * PC.areteMoyenne(pos, adj));
      m = { obj: o, mi: a && a.meshes, pi: a && a.primitives, P, n, sales: new Set(), monde: null, versionMonde: -1,
        adj, miroir: PC.carteMiroir(pos, n, (bb.min.x + bb.max.x) / 2, tol), noms: o.skeleton.bones.map((b) => b.name) };
      m.osM = PC.osMiroir(m.noms);
      parGeo.set(g.uuid, m);
      A.maillages.push(m);
    }
    o.frustumCulled = false;
  });
  A.noms = [...new Set(A.maillages.flatMap((m) => m.noms))];
  const boite = new THREE.Box3().setFromObject(r);
  A.hauteur = Math.max(1e-3, boite.max.y - boite.min.y, (boite.max.x - boite.min.x) * 0.5);
  A.taille = 0.05 * A.hauteur;
  A.repos = new Map();
  r.traverse((o) => { if (o.isBone) A.repos.set(o, { p: o.position.clone(), q: o.quaternion.clone(), s: o.scale.clone() }); });
}

async function chargerGeneres(fiche) {
  try {
    const etat = await lireJson(await fetch(`/api/etabli/mouvement?job=${encodeURIComponent(fiche.job)}&version=${fiche.version}`));
    if (A.fiche !== fiche) return;
    A.generes = listeGeneres(etat, fiche.job).filter((c) => c.jouable && c.url);
  } catch { A.generes = []; }
  peindreClips();
}

/* ── peinture des panneaux ────────────────────────────────────────────────── */

function rigge() { return !!(A.fiche && A.fiche.rig && A.fiche.rig.rigge && A.maillages.length); }

function peindre() {
  if (!A.s) return;
  const sans = $("#afSansRig");
  const montrerSans = !!A.fiche && !rigge();
  sans.classList.toggle("hidden", !montrerSans);
  $("#afSansRigTexte").textContent = !A.fiche ? "" : (A.erreur && A.fiche.rig && A.fiche.rig.rigge ? A.erreur : T("aff.sans_rig"));
  for (const b of A.s.querySelectorAll("[data-vue]")) b.classList.toggle("on", b.dataset.vue === A.vue);
  for (const b of A.s.querySelectorAll("[data-outil]")) b.classList.toggle("on", b.dataset.outil === A.outil);
  for (const b of A.s.querySelectorAll("[data-mode]")) b.classList.toggle("on", b.dataset.mode === A.mode);
  for (const b of A.s.querySelectorAll("[data-attenuation]")) b.classList.toggle("on", b.dataset.attenuation === A.attenuation);
  for (const b of A.s.querySelectorAll("[data-panneau]")) b.classList.toggle("on", b.dataset.panneau === (A.isoler ? "isoler" : "os"));
  $("#afMiroir").checked = A.miroir;
  $("#afTaille").value = String(Math.round((A.taille / A.hauteur) * 200) / 2);
  $("#afTailleVal").textContent = (Math.round((A.taille / A.hauteur) * 1000) / 10).toFixed(1);
  $("#afForce").value = String(Math.round(A.force * 100));
  $("#afForceVal").textContent = `${Math.round(A.force * 100)} %`;
  const actif = rigge() && !A.occupe;
  for (const b of A.s.querySelectorAll("[data-corr], #afTout")) b.disabled = !actif || (b.dataset.cetOs && !A.os);
  $("#afAnnuler").disabled = !A.hist.peutAnnuler;
  $("#afRetablir").disabled = !A.hist.peutRetablir;
  const n = A.maillages.reduce((s, m) => s + m.sales.size, 0);
  $("#afEnregistrer").disabled = !actif || !n;
  $("#afEnregistrerTexte").textContent = n ? T("aff.enregistrer_n", { n: nb(n) }) : T("aff.enregistrer");
  const libres = A.libres ? A.libres.reduce((s, x) => s + x.sommets.length, 0) : null;
  $("#afLibresTexte").textContent = libres == null ? T("aff.libres") : T("aff.libres_n", { n: nb(libres) });
  $("#afLibres").disabled = !rigge();
  $("#afGuerirTexte").textContent = T(A.clip ? "aff.guerir_clip" : A.pose ? "aff.guerir_pose" : "aff.guerir_batterie", { c: A.clip ? A.clip.nom : "" });
  $("#afAvis").textContent = A.erreur && rigge() ? A.erreur : A.avis;
  peindreRapport();
  peindreOs();
  peindreClips();
  peindreEtat();
}

function peindreOs() {
  const { esc } = A.ctx;
  $("#afOsTitre").textContent = T("aff.os_n", { n: A.noms.length });
  $("#afOs").innerHTML = A.noms.map((n) => {
    const r = PC.role(n) || "";
    const c = r.endsWith("_g") ? "l" : r.endsWith("_d") ? "r" : "c";
    return `<button class="af-os-ligne ${n === A.os ? "on" : ""}" data-os="${esc(n)}" role="option" aria-selected="${n === A.os}">`
      + `<span class="af-pastille af-${c}" aria-hidden="true"></span>${esc(n)}</button>`;
  }).join("");
}

function peindreClips() {
  if (!A.s) return;
  const { esc, ico } = A.ctx;
  const essais = Object.keys(PC.POSES).filter((p) => Object.keys(PC.rotationsDePose(p, A.noms)).length);
  const clips = [...A.clips.values(), ...A.generes.map((g) => ({ cle: g.cle, nom: g.nom, url: g.url, origine: g.origine }))];
  const vus = new Set();
  const uniques = clips.filter((c) => !vus.has(c.cle) && vus.add(c.cle));
  $("#afClips").innerHTML = (rigge() ? `<div class="ec-sous">${esc(T("aff.poses_essai"))}</div><div class="af-puces">`
    + essais.map((p) => `<button class="ec-puce ${A.pose === p ? "on" : ""}" data-essai="${p}">${esc(T("aff.essai_" + p))}</button>`).join("") + "</div>"
    + `<div class="ec-sous">${esc(T("aff.clips"))}</div>`
    + (uniques.length ? uniques.map((c) => `<button class="af-clip ${A.clip && A.clip.cle === c.cle ? "on" : ""}" data-clip="${esc(c.cle)}">${ico("dz-media-lecture")} ${esc(c.nom)}</button>`).join("")
      : `<div class="ec-note">${esc(T("aff.sans_clip"))}</div>`) : "");
  A._clips = uniques;
  majPoseUI();
}

function majPoseUI() {
  if (!A.s) return;
  $("#afJouer").disabled = !A.action;
  $("#afJouerTexte").textContent = T(A.joue ? "aff.pause" : "aff.jouer");
  $("#afLiaison").disabled = !(A.clip || A.pose);
  $("#afCap").textContent = !A.fiche ? "" : T(A.clip ? "aff.legende_clip" : A.pose ? "aff.legende_pose" : "aff.legende_liaison",
    { v: A.fiche.version, c: A.clip ? A.clip.nom : "" });
}

function peindreRapport() {
  const el = $("#afRapport");
  const r = A.rapport;
  if (!r) { el.textContent = ""; return; }
  const s = PC.resumeRapport(r);
  let t = s ? T(s.cle, s.v) : "";
  if (r.correction === "orphelins" && r.orphelins && r.orphelins.length) {
    t += " — " + r.orphelins.slice(0, 6).map((x) => `${x.os} ×${x.ilots.length}`).join(", ");
  }
  if (r.version) t += " · " + T("aff.ecrit_v", { v: r.version });
  el.textContent = t;
}

function peindreEtat() {
  const f = A.fiche;
  const n = A.maillages.reduce((s, m) => s + m.n, 0);
  $("#afEtat").innerHTML = `<span>${A.ctx.esc(!f ? T("aff.etat_vide") : rigge()
    ? T("aff.etat_charge", { n: nb(n), os: nb(A.noms.length) }) : T("aff.etat_sans_rig"))}</span>`
    + `<span class="af-raccourcis">${A.ctx.esc(T("aff.raccourcis"))}</span>`;
}

/* ── la vue ───────────────────────────────────────────────────────────────── */

function vue() {
  const r = A.api.racine;
  if (!r) return;
  if (A.vue === "poids" && rigge()) {
    for (const m of A.maillages) {
      const o = m.obj;
      if (!o.userData.dzMatOrigine) o.userData.dzMatOrigine = o.material;
      o.material = A.matPoids;
    }
    recolorer();
  } else {
    appliquerRendu(r, A.vue === "ombre" ? "argile" : A.vue === "fil" ? "fil" : "texture");
  }
}

function indexOs(m, nom) { return m.noms.indexOf(nom); }

function recolorer(m = null, sommets = null) {
  if (A.vue !== "poids") return;
  for (const x of m ? [m] : A.maillages) {
    const k = indexOs(x, A.os);
    const attr = x.obj.geometry.attributes.color;
    if (!sommets) PC.couleurs(x.P, k, { isoler: A.isoler, sortie: attr.array });
    else {
      for (const v of sommets) {
        const sous = { n: 1, j: x.P.j.subarray(v * 4, v * 4 + 4), w: x.P.w.subarray(v * 4, v * 4 + 4) };
        attr.array.set(PC.couleurs(sous, k, { isoler: A.isoler }), v * 3);
      }
    }
    attr.needsUpdate = true;
  }
}

function choisirOs(nom, rafraichir = true) {
  if (!nom) return;
  A.os = nom;
  surlignerChaine(A.api, nom);
  recolorer();
  if (rafraichir) peindre();
}

/* ── le pinceau ───────────────────────────────────────────────────────────── */

function ndc(e) {
  const r = $("#afCanevas").getBoundingClientRect();
  return { x: ((e.clientX - r.left) / r.width) * 2 - 1, y: -((e.clientY - r.top) / r.height) * 2 + 1, px: e.clientX - r.left, py: e.clientY - r.top };
}

function viser(e) {
  if (!A.maillages.length) return null;
  /* le raycast d'une peau passe d'abord par sa sphère englobante : posée, elle doit être recalculée (positionsMonde
     le fait, une fois par pose) — sinon un bras levé sort de la sphère du repos et le pinceau le manque */
  if (!A.joue) for (const m of A.maillages) positionsMonde(m);
  const p = ndc(e);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(new THREE.Vector2(p.x, p.y), A.api.camera);
  return ray.intersectObjects(A.maillages.map((m) => m.obj), false)[0] || null;
}

/* les positions monde de la peau DÉFORMÉE, recalculées quand la pose a changé */
function positionsMonde(m) {
  if (m.monde && m.versionMonde === A.version) return m.monde;
  const o = m.obj, v3 = new THREE.Vector3();
  o.updateMatrixWorld(true);
  o.skeleton.update();
  const out = m.monde && m.monde.length === m.n * 3 ? m.monde : new Float32Array(m.n * 3);
  for (let v = 0; v < m.n; v++) {
    o.getVertexPosition(v, v3).applyMatrix4(o.matrixWorld);    // getVertexPosition → applyBoneTransform
    out[v * 3] = v3.x; out[v * 3 + 1] = v3.y; out[v * 3 + 2] = v3.z;
  }
  m.monde = out;
  m.versionMonde = A.version;
  o.computeBoundingSphere();
  o.computeBoundingBox();
  return out;
}

function optsPour(m) {
  const k = indexOs(m, A.os);
  const bone = m.obj.skeleton.bones[k];
  const parent = bone && bone.parent && bone.parent.isBone ? indexOs(m, bone.parent.name) : -1;
  return { mode: A.mode, os: k, force: A.force, repli: parent >= 0 ? parent : null, adj: m.adj,
    miroir: A.miroir ? m.miroir : null, osM: A.miroir ? m.osM : null, verrou: A.isoler ? PC.horsDomaine(m.P, k) : null };
}

function coup(point, traits, attenuation = A.attenuation) {
  for (const m of A.maillages) {
    if (indexOs(m, A.os) < 0) continue;
    const touches = PC.dansRayon(positionsMonde(m), m.n, [point.x, point.y, point.z], A.taille, attenuation);
    if (!touches.length) continue;
    if (!traits.has(m)) traits.set(m, PC.debutTrait());
    const opts = optsPour(m);
    const faits = PC.appliquer(m.P, touches, opts, traits.get(m));
    finirModif(m, faits);
  }
}

function finirModif(m, faits) {
  if (!faits.length) return;
  for (const v of faits) m.sales.add(v);
  const g = m.obj.geometry;
  g.attributes.skinIndex.needsUpdate = true;
  g.attributes.skinWeight.needsUpdate = true;
  m.versionMonde = -1;
  recolorer(m, faits);
}

function clore(traits) {
  const parts = [];
  for (const [m, tr] of traits) {
    const d = PC.finTrait(tr, m.P);
    if (d) parts.push({ cle: A.maillages.indexOf(m), d });
  }
  A.hist.pousser({ parts });
  A.ctx.marquerSale(A.maillages.some((m) => m.sales.size));
  peindre();
}

function placerCurseur(hit) {
  if (!hit || A.outil !== "peindre") { A.curseur.visible = false; return; }
  A.curseur.visible = true;
  A.curseur.position.copy(hit.point);
  const n = hit.face ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld) : new THREE.Vector3(0, 0, 1);
  A.curseur.lookAt(hit.point.clone().add(n));
  A.curseur.scale.setScalar(A.taille);
}

function surAppui(e) {
  if (!rigge() || e.button !== 0 || e.altKey) return;              // Alt : l'orbite reste à la caméra
  A.appui = [e.clientX, e.clientY];
  if (A.outil === "pose" && A.tc.axis) return;                     // un geste du gizmo
  if (A.outil === "lasso") {
    e.stopPropagation();
    const p = ndc(e);
    A.lasso = [[p.px, p.py]];
    $("#afFigure").setPointerCapture(e.pointerId);
    return;
  }
  if (A.outil !== "peindre") return;
  const jouait = A.joue;
  if (jouait) basculerLecture();                                    // on peint sur une pose arrêtée
  const hit = viser(e);
  if (!hit) { if (jouait) basculerLecture(); return; }
  e.stopPropagation();
  $("#afFigure").setPointerCapture(e.pointerId);
  A.peint = true;
  A.trait = new Map();
  A.dernier = hit.point.clone();
  coup(hit.point, A.trait);
}

function surDeplacement(e) {
  if (!rigge()) return;
  if (A.lasso) {
    const p = ndc(e);
    A.lasso.push([p.px, p.py]);
    $("#afLassoTrace").setAttribute("points", A.lasso.map((x) => x.join(",")).join(" "));
    return;
  }
  const hit = (A.outil === "peindre") ? viser(e) : null;
  placerCurseur(hit);
  if (A.peint && hit && hit.point.distanceTo(A.dernier) > A.taille * 0.25) {
    A.dernier = hit.point.clone();
    coup(hit.point, A.trait);
  }
}

function surRelache(e) {
  if (A.lasso) {
    const poly = A.lasso;
    A.lasso = null;
    $("#afLassoTrace").setAttribute("points", "");
    appliquerLasso(poly);
    return;
  }
  if (A.peint) {
    A.peint = false;
    clore(A.trait);
    A.trait = null;
    return;
  }
  const a = A.appui;
  A.appui = null;
  if (!a || Math.hypot(e.clientX - a[0], e.clientY - a[1]) > 4 || e.button !== 0) return;
  if (A.outil === "os" || A.outil === "pose") {
    const hit = viser(e);
    if (!hit) return;
    const m = A.maillages.find((x) => x.obj === hit.object);
    const face = hit.face;
    const pos = positionsMonde(m);
    const v = [face.a, face.b, face.c].sort((p, q) => dist(pos, p, hit.point) - dist(pos, q, hit.point))[0];
    const o = PC.lire(m.P, v);
    const k = Number(Object.entries(o).sort((x, y) => y[1] - x[1])[0][0]);
    choisirOs(m.noms[k]);
    if (A.outil === "pose") attacherGizmo();
  }
}

const dist = (pos, v, p) => Math.hypot(pos[v * 3] - p.x, pos[v * 3 + 1] - p.y, pos[v * 3 + 2] - p.z);

function appliquerLasso(poly) {
  if (!poly || poly.length < 3) return;
  const cam = A.api.camera, r = $("#afCanevas").getBoundingClientRect(), v3 = new THREE.Vector3();
  const traits = new Map();
  for (const m of A.maillages) {
    if (indexOs(m, A.os) < 0) continue;
    const pos = positionsMonde(m);
    const ecran = new Float32Array(m.n * 2);
    for (let v = 0; v < m.n; v++) {
      v3.set(pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]).project(cam);
      ecran[v * 2] = (v3.x + 1) / 2 * r.width;
      ecran[v * 2 + 1] = (1 - v3.y) / 2 * r.height;
    }
    const sel = PC.selectionLasso(ecran, m.n, poly);
    if (!sel.length) continue;
    const tr = PC.debutTrait();
    traits.set(m, tr);
    finirModif(m, PC.appliquer(m.P, sel.map((v) => [v, 1]), optsPour(m), tr));
  }
  clore(traits);
}

function surMolette(e) {
  if (!rigge() || (!e.ctrlKey && !e.shiftKey)) return;
  e.preventDefault();
  e.stopPropagation();
  const sens = (e.deltaY || e.deltaX) < 0 ? 1 : -1;
  if (e.ctrlKey) A.taille = PC.ajusterTaille(A.taille, sens, A.hauteur);
  else A.force = PC.ajusterForce(A.force, sens);
  A.curseur.scale.setScalar(A.taille);
  peindre();
}

/* clic droit : les sommets sans poids sélectionnés vont à l'os choisi */
function surClicDroit(e) {
  if (!A.libres || !A.libres.length || !A.os) return;
  e.preventDefault();
  const traits = new Map();
  for (const { m, sommets } of A.libres) {
    const k = indexOs(m, A.os);
    if (k < 0 || !sommets.length) continue;
    const tr = PC.debutTrait();
    traits.set(m, tr);
    finirModif(m, PC.appliquer(m.P, sommets.map((v) => [v, 1]), { mode: "fixer", os: k, force: 1 }, tr));
  }
  A.libres = null;
  A.avis = T("aff.libres_assignes", { os: A.os });
  clore(traits);
}

function selectionnerLibres() {
  A.libres = A.maillages.map((m) => ({ m, sommets: PC.sansPoids(m.P) }));
  const n = A.libres.reduce((s, x) => s + x.sommets.length, 0);
  A.avis = n ? T("aff.libres_trouves", { n: nb(n) }) : T("aff.libres_aucun");
  if (!n) A.libres = null;
  peindre();
}

/* ── historique ───────────────────────────────────────────────────────────── */

function histoire(sens) {
  const res = sens === "annuler" ? A.hist.annuler((k) => A.maillages[k].P) : A.hist.retablir((k) => A.maillages[k].P);
  for (const { cle, sommets } of res || []) finirModif(A.maillages[cle], sommets);
  A.ctx.marquerSale(A.maillages.some((m) => m.sales.size));
  peindre();
}

/* ── le test de pose ──────────────────────────────────────────────────────── */

function remettreRepos() {
  for (const [o, r] of A.repos) { o.position.copy(r.p); o.quaternion.copy(r.q); o.scale.copy(r.s); }
  A.version++;
}

function arreter() {
  if (A.mixer) A.mixer.stopAllAction();
  A.action = null; A.joue = false;
}

function liaison() {
  arreter();
  A.tc.detach();
  remettreRepos();
  A.clip = null; A.pose = null;
  peindre();
}

function poseEssai(nom) {
  arreter();
  A.clip = null;
  remettreRepos();
  const rot = PC.rotationsDePose(nom, A.noms);
  const d = THREE.MathUtils.degToRad;
  for (const [o, r] of A.repos) {
    const x = rot[o.name];
    if (!x) continue;
    o.quaternion.copy(r.q).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(d(x[0]), d(x[1]), d(x[2]), "XYZ")));
  }
  A.pose = nom;
  A.version++;
  peindre();
}

async function jouerClip(cle) {
  const c = (A._clips || []).find((x) => x.cle === cle);
  if (!c || !A.mixer) return;
  try {
    if (!c.clip && c.url) {
      const g = await loader().loadAsync(c.url);
      c.clip = (g.animations || [])[0] || null;
    }
  } catch (e) { A.erreur = T("aff.erreur", { m: e.message }); }
  if (!c.clip) { A.avis = T("aff.clip_illisible", { c: c.nom }); peindre(); return; }
  arreter();
  remettreRepos();
  A.tc.detach();
  A.action = A.mixer.clipAction(c.clip);
  A.action.setLoop(THREE.LoopRepeat, Infinity);
  A.action.reset().play();
  A.clip = c; A.pose = null; A.joue = true;
  peindre();
}

function basculerLecture() {
  if (!A.action) return;
  A.joue = !A.joue;
  A.action.paused = !A.joue;
  majPoseUI();
}

function attacherGizmo() {
  const b = [...A.repos.keys()].find((o) => o.name === A.os);
  if (!b) return;
  arreter();
  A.clip = null;
  A.tc.attach(b);
}

function boucle() {
  let avant = performance.now();
  const tic = () => {
    requestAnimationFrame(tic);
    const t = performance.now(), dt = Math.min(0.1, (t - avant) / 1000);
    avant = t;
    if (!A.s || A.s.classList.contains("hidden")) return;
    if (A.mixer && A.joue) { A.mixer.update(dt); A.version++; }
  };
  requestAnimationFrame(tic);
}

/* la pose COURANTE en quaternions locaux relatifs au repos ({os: [x, y, z, w]}), les os immobiles omis */
function poseCourante() {
  const out = {};
  for (const [o, r] of A.repos) {
    const q = PC.quatRelatif([r.q.x, r.q.y, r.q.z, r.q.w], [o.quaternion.x, o.quaternion.y, o.quaternion.z, o.quaternion.w]);
    if (Math.abs(q[3]) < 0.99999) out[o.name] = q.map((x) => Math.round(x * 1e6) / 1e6);
  }
  return out;
}

/* quelques images du clip courant (guérison « sur le clip ») ; la lecture reprend où elle était */
function posesDuClip(n = 6) {
  if (!A.action) return [];
  const d = A.action.getClip().duration || 1, t0 = A.action.time, poses = [];
  for (let i = 0; i < n; i++) {
    A.action.time = (d * (i + 0.5)) / n;
    A.mixer.update(0);
    const p = poseCourante();
    if (Object.keys(p).length) poses.push(p);
  }
  A.action.time = t0;
  A.mixer.update(0);
  return poses;
}

/* ── écrire : enregistrer, corriger ───────────────────────────────────────── */

async function enregistrer() {
  const f = A.fiche;
  const corps = PC.corpsEnregistrer(f.version, A.maillages.filter((m) => m.mi != null).map((m) => ({ mesh: m.mi, primitive: m.pi, P: m.P, sales: m.sales })));
  if (!corps.modifs.length) return null;
  const r = await poster(`/api/studio3d/affiner/enregistrer/${encodeURIComponent(f.job)}`, corps);
  for (const m of A.maillages) m.sales.clear();
  A.ctx.marquerSale(false);
  return r;
}

async function sauver() {
  if (A.occupe) return;
  A.occupe = true; A.erreur = ""; A.avis = T("aff.en_cours"); peindre();
  try {
    const r = await enregistrer();
    A.occupe = false;
    if (r) { await A.ctx.rafraichir(); A.avis = T("aff.enregistre", { v: r.version, n: nb(r.rapport.sommets) }); }
  } catch (e) { A.erreur = T("aff.erreur", { m: e.message }); }
  A.occupe = false;
  peindre();
}

async function corriger(op, { apercu = false, cetOs = false } = {}) {
  const f = A.fiche;
  if (!f || A.occupe) return;
  const params = {};
  if (apercu) params.apercu = true;
  if (op === "confinement" || op === "tout") params.force = A.forceConf;   // « Tout corriger » suit aussi le curseur
  if (op === "coutures") {
    params.anneaux = A.anneaux;
    if (A.deformees) {
      const p = poseCourante();
      if (!Object.keys(p).length) { A.avis = T("aff.deformees_sans_pose"); peindre(); return; }
      params.deformees = true;
      params.pose = p;
    }
  }
  if (op === "guerison") {
    const poses = A.clip ? posesDuClip() : A.pose ? [poseCourante()] : null;
    if (poses && poses.length) params.poses = poses;
  }
  A.occupe = true; A.erreur = ""; A.avis = T("aff.correction_en_cours", { op: T("aff.op_" + op) }); peindre();
  try {
    let version = f.version;
    if (!apercu && A.maillages.some((m) => m.sales.size)) {       // les traits non enregistrés passent d'abord
      const r = await enregistrer();
      if (r) version = r.version;
    }
    const r = await poster(`/api/studio3d/affiner/corriger/${encodeURIComponent(f.job)}`,
      PC.corpsCorriger(version, op, { os: cetOs ? A.os : null, parametres: params }));
    A.rapport = { ...r.rapport, version: r.version };
    A.avis = "";
    A.occupe = false;
    if (r.version) await A.ctx.rafraichir();
    A.rapport = { ...r.rapport, version: r.version };
  } catch (e) { A.erreur = T("aff.erreur", { m: e.message }); }
  A.occupe = false;
  peindre();
}

/* ── événements ───────────────────────────────────────────────────────────── */

function surClic(e) {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  if (b.dataset.vue) { A.vue = b.dataset.vue; vue(); peindre(); }
  else if (b.dataset.outil) changerOutil(b.dataset.outil);
  else if (b.dataset.mode) { A.mode = b.dataset.mode; peindre(); }
  else if (b.dataset.attenuation) { A.attenuation = b.dataset.attenuation; peindre(); }
  else if (b.dataset.panneau) { A.isoler = b.dataset.panneau === "isoler"; recolorer(); peindre(); }
  else if (b.dataset.os) choisirOs(b.dataset.os);
  else if (b.dataset.essai) poseEssai(b.dataset.essai);
  else if (b.dataset.clip) jouerClip(b.dataset.clip);
  else if (b.dataset.corr) corriger(b.dataset.corr, { apercu: !!b.dataset.apercu, cetOs: !!b.dataset.cetOs });
  else if (b.id === "afTout") corriger("tout");
  else if (b.id === "afJouer") basculerLecture();
  else if (b.id === "afLiaison") liaison();
  else if (b.id === "afAnnuler") histoire("annuler");
  else if (b.id === "afRetablir") histoire("retablir");
  else if (b.id === "afLibres") selectionnerLibres();
  else if (b.id === "afEnregistrer") sauver();
  else if (b.id === "afAllerRig") A.ctx.aller("rig");
}

function surSaisie(e) {
  const t = e.target;
  if (t.id === "afTaille") { A.taille = (Number(t.value) / 100) * A.hauteur; peindre(); }
  else if (t.id === "afForce") { A.force = Number(t.value) / 100; peindre(); }
  else if (t.id === "afMiroir") { A.miroir = t.checked; }
  else if (t.id === "afForceConf") { A.forceConf = Number(t.value) / 100; $("#afForceConfVal").textContent = `${t.value} %`; }
  else if (t.id === "afAnneaux") { A.anneaux = Number(t.value); $("#afAnneauxVal").textContent = t.value; }
  else if (t.id === "afDeformees") { A.deformees = t.checked; }
}

function changerOutil(o) {
  A.outil = o;
  if (o !== "pose") A.tc.detach();
  else if (A.os) attacherGizmo();
  if (o !== "peindre") A.curseur.visible = false;
  peindre();
}

function surTouche(e) {
  if (!A.s || A.s.classList.contains("hidden") || !rigge()) return;
  if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
  const a = PC.action(e);
  if (!a) return;
  e.preventDefault();
  if (a.outil) changerOutil(a.outil);
  else if (a.mode) { A.mode = a.mode; peindre(); }
  else if (a.bascule === "miroir") { A.miroir = !A.miroir; peindre(); }
  else if (a.bascule === "isoler") { A.isoler = !A.isoler; recolorer(); peindre(); }
  else if (a.panneau) { A.isoler = false; recolorer(); peindre(); }
  else if (a.taille) { A.taille = PC.ajusterTaille(A.taille, a.taille, A.hauteur); A.curseur.scale.setScalar(A.taille); peindre(); }
  else if (a.histoire) histoire(a.histoire);
}
