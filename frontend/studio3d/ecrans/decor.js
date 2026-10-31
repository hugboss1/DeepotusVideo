/* t401 (31/10/2026) — écran DÉCOR du 3D Studio, volet Végétation : arbres, arbustes et couvre-sol procéduraux,
   dans le navigateur, gratuits et reproductibles (graine + recette). Générateur : ez-tree 1.1.0 (MIT), vendorisé
   dans /lib3d/eztree (D6). Relevé : TreeGen de Sorceress (espèces, taille, feuillage réel ou cartes, saisons, écorce,
   teintes, graine, vent, ciel, fiche, export GLB + recette, import de recette).

   Le calcul (espèces → options d'ez-tree, vent, recette) vit dans decor_calc.js, testé sous node. Ici : l'interface,
   le canevas (/lib3d/viewer.js), l'animation du vent (uniformes du shader de feuilles d'ez-tree) et les exports.
   « Ranger comme modèle 3D » envoie le GLB à POST /api/assets/3d/importer : l'arbre devient un job, que Préparer
   (budget de triangles) et Exporter reprennent comme n'importe quel modèle.

   Volet Accessoire (t402) : un élément généré dans l'onglet 3D, ouvert ici. Gauche : la fiche et les VARIANTES
   (graine → échelle, rotation Y, teinte ; chacune un job neuf `<job>_var<k>`). Droite : sol et hauteur réelle, rôle →
   budget, MASQUE DE VENT (aperçu du balancement dans le canevas, calculé ici avec la même courbe que le serveur, puis
   écrit comme version), LOD (routes /api/assets/3d/{job}/lod) et CARTES (huit vues rendues ici → atlas → imposteur
   écrit par le serveur), ENVOI AU PLATEAU 3D (une scène existante ou neuve), Préparer et Exporter. */
"use strict";
import * as THREE from "three";
import { creerCanevas, cadrer, charger } from "/lib3d/viewer.js";
import { Tree } from "/lib3d/eztree/index.js";
import * as PRESETS_DONNEES from "/lib3d/eztree/presets/donnees.js";
import { TreePreset } from "/lib3d/eztree/presets/index.js";
import { T, nb } from "./coque_calc.js";
import { ESPECES, ONGLETS, FEUILLES, ECORCES, SAISONS, REGLAGES_DEFAUT, optionsPour, echelleVers, vent, recette,
  lireRecette, nomFichier, especeDe, VARIANTES_DEFAUT, corpsVariantes, VENT_ACC_DEFAUT, valeurMasque, profilMasque,
  cadreCartes, vueCarte, ATLAS, USAGES_LOD, niveauxLod } from "./decor_calc.js";
import { ajouterVent } from "./decor_runtime.js";

const D = { s: null, ctx: null, api: null, arbre: null, groupe: null, r: { ...REGLAGES_DEFAUT }, onglet: "arbres",
  volet: "vegetation", nom: "", horloge: new THREE.Clock(), sol: null, minuterie: null,
  /* t402 : l'état du volet Accessoire (réglages, résultats du modèle ouvert, aperçu du vent, cartes posées à côté) */
  acc: { ...VARIANTES_DEFAUT, ...VENT_ACC_DEFAUT, plans: 2, usage: "pc", scene: "", apercu: true },
  accJob: null, accRes: {}, scenes: null, ventAcc: null, masqueFichier: false, cartes: null };
void PRESETS_DONNEES;

export async function monter(section, ctx) {
  D.s = section;
  D.ctx = ctx;
  const { esc, ico } = ctx;
  section.innerHTML = `<div class="ec-trois">
    <aside class="ec-gauche ec-defile">
      <div class="ec-segments ec-volets" id="dcVolets">
        <button data-volet="vegetation">${esc(T("decor.vegetation"))}</button>
        <button data-volet="accessoire">${esc(T("decor.accessoire"))}</button>
      </div>
      <div id="dcGauche"></div>
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue"><span class="ec-mesure" id="dcMesure"></span>
        <button class="ec-bouton" id="dcCadrer">${ico("dz-lab3d-camera")} ${esc(T("decor.cadrer"))}</button></div>
      <div class="ec-vues"><figure class="ec-vue"><canvas id="dcCanevas"></canvas>
        <figcaption>${esc(T("decor.gestes"))}</figcaption></figure></div>
    </main>
    <aside class="ec-droite ec-defile" id="dcDroite"></aside>
  </div>`;
  D.api = creerCanevas(section.querySelector("#dcCanevas"));
  D.sol = new THREE.Mesh(new THREE.CircleGeometry(40, 64), new THREE.MeshStandardMaterial({ color: 0x6f8f4e, roughness: 1 }));
  D.sol.rotation.x = -Math.PI / 2;
  D.api.scene.add(D.sol);
  section.querySelector("#dcVolets").addEventListener("click", (e) => {
    const b = e.target.closest("[data-volet]");
    if (b) { D.volet = b.dataset.volet; peindre(); montrerAccessoire(); }
  });
  section.querySelector("#dcCadrer").addEventListener("click", () => cadrer(D.api));
  section.addEventListener("input", surSaisie);
  section.addEventListener("change", surSaisie);
  section.addEventListener("click", surClic);
  boucleVent();
  peindre();
  generer(true);
}

export function ouvrir() { if (D.s && D.volet === "accessoire") { peindre(); montrerAccessoire(); } }
export function montre() { if (D.api) cadrer(D.api); }

/* ── panneaux ─────────────────────────────────────────────────────────────── */
function peindre() {
  for (const b of D.s.querySelectorAll("#dcVolets [data-volet]")) b.classList.toggle("on", b.dataset.volet === D.volet);
  if (D.volet === "accessoire") return peindreAccessoire();
  peindreGauche();
  peindreDroite();
}

const seg = (nom, valeurs, actif, libelle) => `<div class="ec-segments ec-plein" data-champ="${nom}">${valeurs.map((v) =>
  `<button data-valeur="${v}" class="${String(v) === String(actif) ? "on" : ""}">${D.ctx.esc(libelle(v))}</button>`).join("")}</div>`;
const curseur = (nom, min, max, pas, val, unite = "") => `<label class="ec-champ">${D.ctx.esc(T("decor." + nom.toLowerCase()))}
  <span class="ec-valeur">${D.ctx.esc(String(val))}${D.ctx.esc(unite)}</span>
  <input type="range" data-champ="${nom}" min="${min}" max="${max}" step="${pas}" value="${val}"></label>`;
const bascule = (nom, val) => `<label class="ec-bascule"><input type="checkbox" data-champ="${nom}" ${val ? "checked" : ""}>
  ${D.ctx.esc(T("decor." + nom.toLowerCase()))}</label>`;

function peindreGauche() {
  const { esc } = D.ctx;
  const r = D.r;
  const groupes = ONGLETS[D.onglet];
  D.s.querySelector("#dcGauche").innerHTML = `
    <div class="ec-label">${esc(T("decor.especes"))}</div>
    <div class="ec-segments ec-plein" id="dcOnglets">${Object.keys(ONGLETS).map((o) =>
      `<button data-onglet="${o}" class="${o === D.onglet ? "on" : ""}">${esc(T("decor.onglet_" + o))}</button>`).join("")}</div>
    ${groupes.map((g) => `<div class="ec-sous">${esc(T("groupe." + g))}</div><div class="ec-especes">${ESPECES.filter((e) => e.groupe === g).map((e) =>
      `<button data-espece="${e.id}" class="${e.id === r.espece ? "on" : ""}">${esc(T("espece." + e.id))}</button>`).join("")}</div>`).join("")}
    <div class="ec-label">${esc(T("decor.taille"))}</div>
    ${seg("taille", ["petit", "moyen", "grand"], r.taille, (v) => T("decor.taille_" + v))}
    <div class="ec-label">${esc(T("decor.forme_arbre"))}</div>
    ${curseur("echelle", 0.25, 3, 0.05, r.echelle, "×")}
    ${curseur("niveaux", 0, 3, 1, r.niveaux)}
    <div class="ec-note">${esc(T("decor.approche"))}</div>
    <div class="ec-label">${esc(T("decor.feuillage"))}</div>
    ${seg("feuillage", ["reel", "cartes"], r.feuillage, (v) => T("decor.feuillage_" + v))}
    ${bascule("feuilles", r.feuilles)}
    <div class="ec-sous">${esc(T("decor.forme"))}</div>
    ${seg("forme", FEUILLES, r.forme, (v) => T("feuille." + v))}
    <div class="ec-sous">${esc(T("decor.saison"))}</div>
    ${seg("saison", SAISONS, r.saison, (v) => T("saison." + v))}
    ${curseur("densite", 0, 100, 1, r.densite)}
    ${curseur("tailleFeuille", 0.3, 2.5, 0.05, r.tailleFeuille, "×")}
    ${curseur("retombee", 0, 1, 0.01, r.retombee)}
    ${bascule("rameaux", r.rameaux)}
    <div class="ec-label">${esc(T("decor.couleur"))}</div>
    <div class="ec-sous">${esc(T("decor.ecorce"))}</div>
    ${seg("ecorce", ECORCES, r.ecorce, (v) => T("ecorce." + v))}
    <label class="ec-champ">${esc(T("decor.teinteecorce"))}<input type="color" data-champ="teinteEcorce" value="${esc(r.teinteEcorce)}"></label>
    <label class="ec-champ">${esc(T("decor.teintefeuille"))}<input type="color" data-champ="teinteFeuille" value="${esc(r.teinteFeuille)}"></label>
    <div class="ec-note">${esc(T("decor.teinte_aide"))}</div>
    <div class="ec-label">${esc(T("decor.variation"))}</div>
    <div class="ec-ligne"><label class="ec-champ">${esc(T("decor.graine"))}<input type="number" min="0" step="1" data-champ="graine" value="${r.graine}"></label>
      <button class="ec-bouton" data-action="variante">${D.ctx.ico("dz-action-reinitialiser")} ${esc(T("decor.variante"))}</button></div>
    <div class="ec-note">${esc(T("decor.graine_aide"))}</div>`;
}

function peindreDroite() {
  const { esc, ico } = D.ctx;
  const r = D.r;
  D.s.querySelector("#dcDroite").innerHTML = `
    <div class="ec-label">${esc(T("decor.vent"))}</div>
    ${bascule("vent", r.vent)}
    ${curseur("ventForce", 0, 3, 0.05, r.ventForce, " m")}
    ${curseur("ventVitesse", 0, 3, 0.05, r.ventVitesse, "×")}
    ${curseur("ventDirection", 0, 359, 1, r.ventDirection, "°")}
    ${curseur("frisson", 0, 20, 1, r.frisson, " cm")}
    <div class="ec-label">${esc(T("decor.scene"))}</div>
    ${bascule("ciel", r.ciel)}
    <div class="ec-label">${esc(T("decor.fiche"))}</div>
    <dl class="ec-fiche" id="dcFiche"></dl>
    <div class="ec-label">${esc(T("decor.export"))}</div>
    <label class="ec-champ">${esc(T("decor.nom"))}<input type="text" id="dcNom" maxlength="80" value="${esc(D.nom)}"
      placeholder="${esc(recette(r).nom)}"></label>
    <button class="ec-principal" data-action="ranger">${ico("dz-action-envoyer-vers")} ${esc(T("decor.ranger"))}</button>
    <div class="ec-note">${esc(T("decor.ranger_aide"))}</div>
    <button class="ec-bouton bloc" data-action="glb">${ico("dz-action-telecharger")} ${esc(T("decor.glb"))}</button>
    <button class="ec-bouton bloc" data-action="recette">${ico("dz-action-exporter")} ${esc(T("decor.recette"))}</button>
    <button class="ec-bouton bloc" data-action="runtime">${ico("dz-action-exporter")} ${esc(T("decor.runtime"))}</button>
    <div class="ec-label">${esc(T("decor.importer"))}</div>
    <label class="ec-depot petit">${ico("dz-action-importer")} <span>${esc(T("decor.importer_aide"))}</span>
      <input type="file" accept=".json" id="dcRecette" hidden></label>
    <div class="ec-avis" id="dcAvis"></div>`;
  peindreFiche();
}

/* t402 : un curseur du volet Accessoire (data-acc, valeur affichée à côté du libellé) */
const curseurAcc = (nom, min, max, pas, unite = "") => `<label class="ec-champ">${D.ctx.esc(T("decor.acc_" + nom))}
  <span class="ec-valeur">${D.ctx.esc(String(D.acc[nom]))}${D.ctx.esc(unite)}</span>
  <input type="range" data-acc="${nom}" min="${min}" max="${max}" step="${pas}" value="${D.acc[nom]}"></label>`;

function peindreAccessoire() {
  const { esc, ico } = D.ctx;
  const f = D.ctx.fiche();
  const roles = D.roles || [];
  const a = D.acc, res = D.accRes;
  D.s.querySelector("#dcGauche").innerHTML = `<div class="ec-label">${esc(T("decor.accessoire"))}</div>
    <div class="ec-note">${esc(T("decor.accessoire_aide"))}</div>
    ${f ? `<div class="ec-fiche-courte"><b>${esc(f.nom)}</b><span>${esc(T("bandeau.triangles", { n: nb(f.triangles) }))} · v${esc(f.version)}</span></div>
    <div class="ec-label">${esc(T("decor.acc_variantes"))}</div>
    ${curseurAcc("nombre", 2, 8, 1)}
    <div class="ec-ligne"><label class="ec-champ">${esc(T("decor.graine"))}<input type="number" min="0" step="1" data-acc="graine" value="${a.graine}"></label>
      <button class="ec-bouton" data-action="acc-de">${ico("dz-action-reinitialiser")} ${esc(T("decor.acc_de"))}</button></div>
    ${curseurAcc("echelle_pct", 0, 50, 1, " %")}
    ${curseurAcc("teinte", 0, 1, 0.05)}
    ${curseurAcc("luminosite", 0, 0.6, 0.05)}
    <label class="ec-bascule"><input type="checkbox" data-acc="rotation" ${a.rotation ? "checked" : ""}> ${esc(T("decor.acc_rotation"))}</label>
    <button class="ec-principal" data-action="acc-variantes">${ico("dz-action-dupliquer")} ${esc(T("decor.acc_var_creer"))}</button>
    <div class="ec-note">${esc(T("decor.acc_var_aide"))}</div>
    <ul class="dc-resultats" id="dcVariantes">${(res.variantes || []).map((v) => `<li>
      <span class="dc-teinte" style="background:${esc(v.tirage.teinte)}"></span>
      <span class="dc-res-nom">${esc(v.nom || v.job)}<small>×${esc(v.tirage.echelle.toFixed(2))} · ${esc(String(Math.round(v.tirage.rotation_y)))}°</small></span>
      <button class="ec-bouton" data-ouvrir-job="${esc(v.job)}">${esc(T("decor.acc_var_ouvrir"))}</button></li>`).join("")}</ul>`
    : `<button class="ec-bouton bloc" data-aller="ouvrir">${ico("dz-action-ouvrir")} ${esc(T("decor.acc_ouvrir"))}</button>`}`;
  /* t402 : la droite — sol et hauteur réelle, rôle et budget, vent, LOD et cartes, Plateau, puis Préparer / Exporter */
  const lod = niveauxLod(res.lod);
  D.s.querySelector("#dcDroite").innerHTML = f ? `<div class="ec-label">${esc(T("decor.acc_sol"))}</div>
    <label class="ec-champ">${esc(T("decor.acc_hauteur"))}<input type="number" id="dcHauteur" min="0.01" max="500" step="0.01"
      placeholder="${esc(T("decor.acc_hauteur_vide"))}"></label>
    <button class="ec-principal" data-action="poser">${ico("dz-lab3d-orienter")} ${esc(T("decor.acc_poser"))}</button>
    <div class="ec-note">${esc(T("decor.acc_poser_aide"))}</div>
    <div class="ec-label">${esc(T("decor.acc_role"))}</div>
    <div class="ec-especes">${roles.map((r) => `<button data-role="${esc(r.role)}" class="${D.role === r.role ? "on" : ""}">${esc(T("role." + r.role))}</button>`).join("")}</div>
    <div class="ec-note" id="dcBudget">${esc(budgetTexte(f))}</div>
    <div class="ec-label">${esc(T("decor.acc_vent"))}</div>
    <div class="ec-note">${esc(T(D.masqueFichier ? "decor.acc_vent_present" : "decor.acc_vent_absent"))}</div>
    ${curseurAcc("courbe", 0.2, 5, 0.1)}
    ${curseurAcc("seuil", 0, 0.9, 0.05)}
    <svg class="dc-profil" viewBox="-2 -2 124 44" aria-hidden="true"><polyline id="dcProfil" points="${profilMasque(a.courbe, a.seuil)}"/></svg>
    <label class="ec-bascule"><input type="checkbox" data-acc="apercu" ${a.apercu ? "checked" : ""}> ${esc(T("decor.acc_apercu"))}</label>
    ${curseurAcc("amplitude", 0, 1, 0.01, " m")}
    <button class="ec-principal" data-action="acc-vent">${ico("dz-action-enregistrer")} ${esc(T("decor.acc_vent_ecrire"))}</button>
    <div class="ec-note">${esc(T("decor.acc_vent_aide"))}</div>
    <div class="ec-label">${esc(T("decor.acc_lod"))}</div>
    <div class="ec-segments ec-plein">${USAGES_LOD.map((u) => `<button data-usage="${u}" class="${u === a.usage ? "on" : ""}">${esc(T("decor.acc_lod_" + u))}</button>`).join("")}</div>
    <button class="ec-bouton bloc" data-action="acc-lod">${ico("dz-lab3d-optimiser")} ${esc(T("decor.acc_lod_construire"))}</button>
    ${lod.length ? `<ul class="dc-resultats">${lod.map((n) => `<li><span class="dc-res-nom">${esc(T("decor.acc_lod_niveau", { n: n.niveau, t: nb(n.triangles) }))}</span>
      <a class="ec-bouton" href="/api/assets/3d/${encodeURIComponent(f.job)}/lod/${n.niveau}" download>${ico("dz-action-telecharger")}</a></li>`).join("")}</ul>
      <a class="ec-bouton bloc" href="/api/assets/3d/${encodeURIComponent(f.job)}/lod-zip" download>${ico("dz-action-telecharger")} ${esc(T("decor.acc_lod_zip"))}</a>` : ""}
    <div class="ec-note">${esc(T("decor.acc_lod_aide"))}</div>
    <div class="ec-sous">${esc(T("decor.acc_cartes"))}</div>
    <div class="ec-segments ec-plein">${[2, 3].map((p) => `<button data-plans="${p}" class="${p === a.plans ? "on" : ""}">${esc(T("decor.acc_plans", { n: p }))}</button>`).join("")}</div>
    <button class="ec-bouton bloc" data-action="acc-cartes">${ico("dz-lab3d-camera")} ${esc(T("decor.acc_cartes_construire"))}</button>
    ${res.cartes ? `<a class="ec-bouton bloc" href="${esc(res.cartes.url)}" download>${ico("dz-action-telecharger")} ${esc(T("decor.acc_cartes_glb"))}</a>` : ""}
    <div class="ec-note">${esc(T("decor.acc_cartes_aide"))}</div>
    <div class="ec-label">${esc(T("decor.acc_plateau"))}</div>
    <label class="ec-champ">${esc(T("decor.acc_scene"))}<select id="dcScene">
      <option value="">${esc(T("decor.acc_scene_neuve"))}</option>
      ${(D.scenes || []).map((s) => `<option value="${esc(s.id)}" ${s.id === a.scene ? "selected" : ""}>${esc(s.nom)} · ${esc(T("decor.acc_objets", { n: s.instances }))}</option>`).join("")}
    </select></label>
    <button class="ec-principal" data-action="acc-plateau">${ico("dz-action-envoyer-vers")} ${esc(T("decor.acc_plateau_envoyer"))}</button>
    ${res.plateau ? `<a class="ec-bouton bloc" href="${esc(res.plateau.url)}" target="_blank" rel="noopener">${ico("dz-action-ouvrir")} ${esc(T("decor.acc_plateau_ouvrir"))}</a>` : ""}
    <div class="ec-note">${esc(T("decor.acc_plateau_aide"))}</div>
    <div class="ec-label">${esc(T("decor.export"))}</div>
    <button class="ec-bouton bloc" data-aller="preparer">${ico("dz-lab3d-optimiser")} ${esc(T("decor.acc_budget"))}</button>
    <button class="ec-bouton bloc" data-aller="exporter">${ico("dz-action-exporter")} ${esc(T("decor.acc_exporter"))}</button>
    <div class="ec-avis" id="dcAvis">${esc(D.accAvis || "")}</div>` : "";
}

function budgetTexte(f) {
  const r = (D.roles || []).find((x) => x.role === D.role);
  if (!r) return T("decor.acc_role_aide");
  return T("decor.acc_budget_texte", { n: nb(r.triangles), m: nb(f ? f.triangles : 0) });
}

/* le volet Accessoire montre le modèle ouvert à la place de l'arbre (l'arbre reste en mémoire pour le retour) */
async function montrerAccessoire() {
  const f = D.ctx.fiche();
  if (D.groupe) D.groupe.visible = D.volet !== "accessoire";
  if (D.modele) { D.api.scene.remove(D.modele); D.modele = null; }
  D.ventAcc = null;
  oterCartes();
  if (D.volet !== "accessoire") { D.api.racine = D.groupe; peindreFiche(); return; }
  /* un autre modèle (ou une autre version) : les résultats du précédent ne valent plus */
  const cle = f ? f.job + "@" + f.version : null;
  if (cle !== D.accJob) { D.accJob = cle; D.accRes = {}; D.accAvis = ""; }
  if (!D.roles) {
    try { D.roles = (await D.ctx.jget("/api/studio3d/decor/roles")).roles; } catch { D.roles = []; }
  }
  if (f) await Promise.all([lireLod(f), lireScenes()]);
  peindreAccessoire();
  if (!f) return;
  try {
    D.api.racine = null;
    await charger(D.api, f.url);
    D.modele = D.api.racine;
    cadrer(D.api);
    D.s.querySelector("#dcMesure").textContent = T("bandeau.triangles", { n: nb(f.triangles) }) + " · v" + f.version;
    D.masqueFichier = false;
    D.modele.traverse((o) => { if (o.isMesh && o.geometry.getAttribute("_wind")) D.masqueFichier = true; });
    preparerVent();
    peindreAccessoire();
  } catch (e) { echec(e); }
}

/* ── t402 : appels du volet Accessoire ────────────────────────────────────── */
async function poster(url, corps) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
  return j;
}

function avisAcc(texte) {
  D.accAvis = texte;
  const el = D.s.querySelector("#dcAvis");
  if (el) el.textContent = texte;
}

async function poser() {
  const f = D.ctx.fiche();
  if (!f) return;
  const h = parseFloat(D.s.querySelector("#dcHauteur").value);
  const corps = { job: f.job, version: f.version };
  if (Number.isFinite(h)) corps.hauteur_m = h;
  avisAcc(T("decor.acc_en_cours"));
  try {
    await poster("/api/studio3d/decor/poser", corps);
    await D.ctx.ouvrir(f.job, null, "decor");
  } catch (e) { avisAcc(T("erreur.decor", { m: e.message })); }
}

async function creerVariantes() {
  const f = D.ctx.fiche();
  if (!f) return;
  avisAcc(T("decor.acc_travail"));
  try {
    const j = await poster("/api/studio3d/decor/variantes", corpsVariantes(f.job, f.version, D.acc));
    D.accRes.variantes = j.variantes;
    const m = j.variantes.filter((v) => v.nouveau).length;
    D.accAvis = T("decor.acc_var_faites", { n: j.variantes.length, m, d: j.variantes.length - m });
    peindreAccessoire();
  } catch (e) { avisAcc(T("erreur.decor", { m: e.message })); }
}

/* l'aperçu du vent : le masque calculé ICI sur la hauteur monde (même courbe que le serveur), puis le runtime */
function preparerVent(recalculer = !D.masqueFichier) {
  if (!D.modele) return;
  if (recalculer) {                   // le masque du fichier est montré tel quel tant que courbe et seuil n'ont pas bougé
    D.modele.updateMatrixWorld(true);
    const boite = new THREE.Box3().setFromObject(D.modele);
    const y0 = boite.min.y, h = Math.max(1e-9, boite.max.y - boite.min.y), v = new THREE.Vector3();
    D.modele.traverse((o) => {
      if (!o.isMesh) return;
      const pos = o.geometry.getAttribute("position");
      const m = o.geometry.getAttribute("_wind") || new THREE.BufferAttribute(new Float32Array(pos.count), 1);
      for (let i = 0; i < pos.count; i++) {
        v.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
        m.setX(i, valeurMasque((v.y - y0) / h, D.acc.courbe, D.acc.seuil));
      }
      m.needsUpdate = true;
      if (!o.geometry.getAttribute("_wind")) o.geometry.setAttribute("_wind", m);
    });
  }
  if (!D.ventAcc) D.ventAcc = ajouterVent(D.modele, recetteAcc());
  else D.ventAcc.regler(recetteAcc());
}

const recetteAcc = (force) => ({ reglages: { vent: D.acc.apercu, ventForce: force ?? D.acc.amplitude,
  ventDirection: D.r.ventDirection, ventVitesse: D.r.ventVitesse, frisson: D.r.frisson } });

async function ecrireVent() {
  const f = D.ctx.fiche();
  if (!f) return;
  avisAcc(T("decor.acc_travail"));
  try {
    const j = await poster("/api/studio3d/decor/vent", { job: f.job, version: f.version, courbe: D.acc.courbe, seuil: D.acc.seuil });
    await D.ctx.ouvrir(f.job, null, "decor");
    avisAcc(T("decor.acc_vent_fait", { v: j.version }));       // après la réouverture, qui remet l'avis à zéro
  } catch (e) { avisAcc(T("erreur.decor", { m: e.message })); }
}

async function lireLod(f) {
  try { D.accRes.lod = (await D.ctx.jget(`/api/assets/3d/${encodeURIComponent(f.job)}/lod`)).chaine; }
  catch { D.accRes.lod = null; }
}

async function construireLod() {
  const f = D.ctx.fiche();
  if (!f) return;
  avisAcc(T("decor.acc_travail"));
  try {
    D.accRes.lod = await poster(`/api/assets/3d/${encodeURIComponent(f.job)}/lod`, { usage: D.acc.usage });
    D.accAvis = T("decor.acc_lod_fait", { n: niveauxLod(D.accRes.lod).length });
    peindreAccessoire();
  } catch (e) { avisAcc(T("erreur.decor", { m: e.message })); }
}

/* les cartes : huit vues orthographiques du modèle, sans sol ni ciel, assemblées en atlas 4 × 2 (fond transparent) */
async function capturerAtlas(taille = 256) {
  const boite = new THREE.Box3().setFromObject(D.modele);
  const cadre = cadreCartes({ min: boite.min.toArray(), max: boite.max.toArray() });
  const rendu = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  rendu.setPixelRatio(1);
  rendu.setSize(taille, taille, false);
  rendu.setClearColor(0x000000, 0);
  /* seul le modèle (et les lumières) entre dans les vues : sol, arbre, grille, axes et cartes déjà posées sortent */
  const sc = D.api.scene, fond = sc.background;
  const caches = sc.children.filter((o) => o !== D.modele && !o.isLight && o.visible);
  sc.background = null;
  for (const o of caches) o.visible = false;
  if (D.ventAcc) D.ventAcc.regler(recetteAcc(0));               // les vues se prennent au repos
  const c = cadre.cote / 2;
  const cam = new THREE.OrthographicCamera(-c, c, c, -c, cadre.cote * 0.01, cadre.cote * 6);
  const atlas = document.createElement("canvas");
  atlas.width = ATLAS.colonnes * taille;
  atlas.height = ATLAS.lignes * taille;
  const g = atlas.getContext("2d");
  try {
    for (let k = 0; k < 8; k++) {
      const v = vueCarte(k, cadre);
      cam.position.set(...v.position);
      cam.up.set(0, 1, 0);
      cam.lookAt(...v.cible);
      cam.updateMatrixWorld();
      rendu.render(sc, cam);
      g.drawImage(rendu.domElement, v.colonne * taille, v.ligne * taille);
    }
  } finally {
    sc.background = fond;
    for (const o of caches) o.visible = true;
    if (D.ventAcc) D.ventAcc.regler(recetteAcc());
    rendu.dispose();
    rendu.forceContextLoss();
  }
  return { atlas: atlas.toDataURL("image/png"), cadre };
}

async function construireCartes() {
  const f = D.ctx.fiche();
  if (!f || !D.modele) return;
  avisAcc(T("decor.acc_cartes_en_cours"));
  try {
    const { atlas, cadre } = await capturerAtlas();
    const j = await poster("/api/studio3d/decor/cartes", { job: f.job, version: f.version, atlas, plans: D.acc.plans });
    D.accRes.cartes = j;
    D.accAvis = T("decor.acc_cartes_fait", { p: j.plans, t: j.triangles });
    peindreAccessoire();
    /* l'imposteur posé à côté du modèle, pour comparer */
    const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
    const gltf = await new GLTFLoader().loadAsync(j.url + "&t=" + Date.now());
    oterCartes();
    D.cartes = gltf.scene;
    D.cartes.position.x = cadre.cote * 1.15;
    D.api.scene.add(D.cartes);
  } catch (e) { avisAcc(T("erreur.decor", { m: e.message })); }
}

function oterCartes() {
  if (!D.cartes) return;
  D.api.scene.remove(D.cartes);
  D.cartes.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
  D.cartes = null;
}

async function lireScenes() {
  try { D.scenes = (await D.ctx.jget("/api/scenes3d")).scenes || []; } catch { D.scenes = []; }
  if (D.acc.scene && !D.scenes.some((s) => s.id === D.acc.scene)) D.acc.scene = "";
}

async function envoyerPlateau() {
  const f = D.ctx.fiche();
  if (!f) return;
  avisAcc(T("decor.acc_travail"));
  try {
    const j = await poster("/api/studio3d/decor/plateau", { job: f.job, version: f.version, scene: D.acc.scene || undefined });
    D.accRes.plateau = j;
    D.acc.scene = j.scene;
    await lireScenes();
    D.accAvis = T("decor.acc_plateau_fait", { s: j.nom, n: j.instances });
    peindreAccessoire();
  } catch (e) { avisAcc(T("erreur.decor", { m: e.message })); }
}

function peindreFiche() {
  const el = D.s.querySelector("#dcFiche");
  if (!el || !D.groupe) return;
  const b = new THREE.Box3().setFromObject(D.groupe), t = b.getSize(new THREE.Vector3());
  const feuilles = D.arbre ? Math.round(D.arbre.leaves.verts.length / 3 / (D.arbre.options.leaves.billboard === "double" ? 8 : 4)) : 0;
  const m = (x) => (Math.round(x * 10) / 10).toLocaleString(D.ctx.T("decor.locale"));
  const lignes = [["hauteur", m(t.y) + " m"], ["envergure", m(Math.max(t.x, t.z)) + " m"],
    ["triangles", nb(D.arbre ? D.arbre.triangleCount : 0)], ["feuilles_n", nb(feuilles)]];
  el.innerHTML = lignes.map(([k, v]) => `<dt>${D.ctx.esc(T("decor." + k))}</dt><dd>${D.ctx.esc(v)}</dd>`).join("");
  D.s.querySelector("#dcMesure").textContent = T("decor.mesure", { h: m(t.y), t: nb(D.arbre ? D.arbre.triangleCount : 0), f: nb(feuilles) });
}

/* ── événements ───────────────────────────────────────────────────────────── */
function surSaisie(e) {
  const el = e.target;
  if (el.id === "dcNom") { D.nom = el.value; return; }
  if (el.id === "dcScene") { D.acc.scene = el.value; return; }
  if (el.dataset && el.dataset.acc) return surSaisieAcc(el);
  if (el.id === "dcRecette" && e.type === "change") { if (el.files[0]) importerRecette(el.files[0]); return; }
  const champ = el.dataset && el.dataset.champ;
  if (!champ) return;
  const d = REGLAGES_DEFAUT[champ];
  D.r[champ] = typeof d === "boolean" ? el.checked : typeof d === "number" ? Number(el.value) : el.value;
  const lab = el.closest("label");
  const val = lab && lab.querySelector(".ec-valeur");
  if (val) val.firstChild ? (val.textContent = String(el.value) + (val.textContent.replace(/^[\d.,-]+/, ""))) : null;
  if (champ.startsWith("vent") || champ === "frisson") return appliquerVent();
  if (champ === "ciel") return appliquerCiel();
  if (champ === "echelle") { D.groupe && D.groupe.scale.setScalar(echelleVers(D.hauteurBrute, D.r)); return peindreFiche(); }
  if (e.type === "input" && el.type === "range") return planifier();
  generer();
}

/* t402 : un réglage du volet Accessoire — l'aperçu du vent suit sans repeindre le panneau */
function surSaisieAcc(el) {
  const k = el.dataset.acc, d = D.acc[k];
  D.acc[k] = typeof d === "boolean" ? el.checked : Number(el.value);
  const val = el.closest("label") && el.closest("label").querySelector(".ec-valeur");
  if (val) val.textContent = String(el.value) + val.textContent.replace(/^[\d.,-]+/, "");
  if (k === "courbe" || k === "seuil") {
    const p = D.s.querySelector("#dcProfil");
    if (p) p.setAttribute("points", profilMasque(D.acc.courbe, D.acc.seuil));
    return preparerVent(true);
  }
  if (k === "amplitude" || k === "apercu") return preparerVent(false);
}

function surClic(e) {
  if (e.target.closest("a[href]")) return;
  const t = e.target.closest("button, [data-aller]");
  if (!t) return;
  if (t.dataset.aller) return D.ctx.aller(t.dataset.aller);
  if (t.dataset.ouvrirJob) return D.ctx.ouvrir(t.dataset.ouvrirJob, null, "decor");
  if (t.dataset.usage) { D.acc.usage = t.dataset.usage; return peindreAccessoire(); }
  if (t.dataset.plans) { D.acc.plans = Number(t.dataset.plans); return peindreAccessoire(); }
  if (t.dataset.onglet) { D.onglet = t.dataset.onglet; return peindreGauche(); }
  if (t.dataset.espece) {
    D.r.espece = t.dataset.espece;
    if (especeDe(D.r.espece).taillesFixes) D.r.taille = especeDe(D.r.espece).taillesFixes;
    peindreGauche();
    return generer(true);
  }
  const seg = t.closest("[data-champ]");
  if (seg && t.dataset.valeur != null) {
    D.r[seg.dataset.champ] = t.dataset.valeur;
    for (const b of seg.querySelectorAll("[data-valeur]")) b.classList.toggle("on", b === t);
    return generer(seg.dataset.champ === "taille");
  }
  if (t.dataset.role) { D.role = t.dataset.role; return peindreAccessoire(); }
  const a = t.dataset.action;
  if (a === "variante") { D.r.graine = Math.floor(Math.random() * 100000); peindreGauche(); return generer(); }
  if (a === "glb") return exporterGlb().then((b) => telecharger(b, nomFichier(nomCourant()) + ".glb")).catch(echec);
  if (a === "recette") return telecharger(new Blob([JSON.stringify(recette(D.r, nomCourant()), null, 1)], { type: "application/json" }),
    nomFichier(nomCourant()) + ".decor.json");
  if (a === "runtime") return fetch(new URL("./decor_runtime.js", import.meta.url)).then((r) => r.blob())
    .then((b) => telecharger(b, "deepotus-decor-vent.js")).catch(echec);
  if (a === "ranger") return ranger();
  if (a === "poser") return poser();
  if (a === "acc-de") { D.acc.graine = Math.floor(Math.random() * 100000); return peindreAccessoire(); }
  if (a === "acc-variantes") return creerVariantes();
  if (a === "acc-vent") return ecrireVent();
  if (a === "acc-lod") return construireLod();
  if (a === "acc-cartes") return construireCartes();
  if (a === "acc-plateau") return envoyerPlateau();
}

const nomCourant = () => D.nom || recette(D.r).nom;

function planifier() {
  clearTimeout(D.minuterie);
  D.minuterie = setTimeout(() => generer(), 120);
}

/* ── génération ───────────────────────────────────────────────────────────── */
function generer(recadrer = false) {
  let options;
  try { options = optionsPour(D.r, TreePreset); } catch (e) { return echec(e); }
  if (D.groupe) {
    D.api.scene.remove(D.groupe);
    D.groupe.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
  }
  const arbre = new Tree();
  arbre.loadFromJson(options);
  arbre.branchesMesh.name = "dz_ecorce";        // les noms que le runtime de vent exporté reconnaît
  arbre.leavesMesh.name = "dz_feuilles";
  const g = new THREE.Group();
  g.name = nomFichier(nomCourant());
  g.add(arbre);
  /* ez-tree ne travaille pas en mètres : on mesure l'arbre brut, puis on le met à la hauteur réelle de l'espèce */
  D.hauteurBrute = new THREE.Box3().setFromObject(arbre).getSize(new THREE.Vector3()).y;
  g.scale.setScalar(echelleVers(D.hauteurBrute, D.r));
  D.arbre = arbre;
  D.groupe = g;
  D.api.scene.add(g);
  D.api.racine = g;
  appliquerVent();
  appliquerCiel();
  if (recadrer) cadrer(D.api);
  peindreFiche();
}

function appliquerVent() {
  const v = vent(D.r);
  const sh = D.arbre && D.arbre.leavesMesh.material.userData.shader;
  if (!sh) return;
  sh.uniforms.uWindStrength.value.set(v.force[0], v.force[1], v.force[2]);
  sh.uniforms.uWindFrequency.value = v.frequence;
  sh.uniforms.uWindScale.value = v.echelle;
}

function boucleVent() {
  (function tic() {
    requestAnimationFrame(tic);
    if (D.ventAcc) D.ventAcc.maj(D.horloge.getElapsedTime());     // t402 : l'accessoire qui porte un masque
    if (!D.arbre) return;
    D.arbre.update(D.horloge.getElapsedTime());
    if (!D.vu && D.arbre.leavesMesh.material.userData.shader) { D.vu = true; appliquerVent(); }
  })();
}

function appliquerCiel() {
  D.api.scene.background = new THREE.Color(D.r.ciel ? 0x7fa8d8 : 0x14161a);
  D.sol.visible = !!D.r.ciel;
}

/* ── exports ──────────────────────────────────────────────────────────────── */
async function exporterGlb() {
  const { GLTFExporter } = await import("three/addons/exporters/GLTFExporter.js");
  const ex = new GLTFExporter();
  const copie = D.groupe.clone(true);
  const ab = await ex.parseAsync(copie, { binary: true, onlyVisible: true });
  return new Blob([ab], { type: "model/gltf-binary" });
}

function telecharger(blob, nom) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = nom;
  document.body.append(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

async function ranger() {
  const avis = D.s.querySelector("#dcAvis");
  avis.textContent = T("decor.ranger_en_cours");
  try {
    const blob = await exporterGlb();
    const fd = new FormData();
    fd.append("file", blob, nomFichier(nomCourant()) + ".glb");
    const r = await fetch("/api/assets/3d/importer", { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
    avis.textContent = T("decor.range", { n: nb(j.triangles) });
    await D.ctx.ouvrir(j.job, null, "decor");
  } catch (e) { echec(e); }
}

async function importerRecette(fichier) {
  try {
    const { nom, reglages } = lireRecette(await fichier.text());
    D.r = reglages;
    D.nom = nom;
    D.onglet = Object.keys(ONGLETS).find((o) => ONGLETS[o].includes(especeDe(D.r.espece).groupe)) || "arbres";
    peindre();
    generer(true);
  } catch (e) {
    D.s.querySelector("#dcAvis").textContent = T("decor.recette_refus", { m: e.message });
  }
}

function echec(e) {
  const el = D.s && D.s.querySelector("#dcAvis");
  if (el) el.textContent = T("erreur.decor", { m: (e && e.message) || String(e) });
}
