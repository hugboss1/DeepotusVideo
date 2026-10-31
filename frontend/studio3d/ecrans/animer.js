/* t398 + t399 (31/10/2026) — écran ANIMER du 3D Studio : bibliothèque, lecture sur le modèle ouvert, texte → mouvement.

   Relevé de Sorceress (§7 Animate) : à gauche Générés / Favoris, des collections, la bibliothèque ; au centre le
   viewport (vues P/F/B/L/R/T, pose de liaison, mode conduite au clavier) et le lecteur ; à droite « Générer »
   (prompt, modèles, durée, intensité, devis). Chez nous :
   - la BIBLIOTHÈQUE est le catalogue Meshy relevé en t387 (680 animations), servi par /api/studio3d/animer/catalogue :
     recherche, catégories, pages, favoris et collections rangés dans le dossier de données ;
   - APPLIQUER une animation du catalogue : 3 crédits sur un rig Meshy (POST /api/studio3d/animer/appliquer) ; sur un
     autre rig, la route du rig existante (re-rig Meshy + l'action) — devis, dialogue maison, `confirme_cout` ;
   - les clips JOUENT sur le modèle ouvert (AnimationMixer de three.js) : ceux de la version, et les clips Meshy du
     job (même rig, chargés depuis leur GLB) ; les mouvements rangés (BVH/GLB) s'appliquent d'abord ;
   - TEXTE → MOUVEMENT (t399) : Meshy Text to Motion « swift » (BVH, 3 crédits), reciblé par mouvement_rig en une
     version de plus ; HY-Motion, Kimodo, GVHMR et « prime » (FBX) sont montrés grisés, avec leur raison ;
   - IMPORTER UN MOUVEMENT : les routes du mouvement de l'Établi (/api/etabli/mouvement/*, t343) — BVH/GLB importé,
     reciblé, retimé ; la vidéo → mouvement Uthana reste dans l'Établi (lien), on ne recopie pas sa logique ;
   - MODE CONDUITE : ZQSD (AZERTY) / WASD (QWERTY) / flèches promènent le personnage sur le sol pendant qu'un clip de
     marche boucle ; la physique des os à ressort suit (t405). Le calcul vit dans animer_calc.js (banc node).
   t405 : HY-MOTION (fal, 0,08 / 0,06 $) en second modèle texte → mouvement, éteint tant que la case de sa licence
   (qui exclut l'UE et le Royaume-Uni) n'est pas cochée ; Kimodo et GVHMR grisés avec leur raison exacte ;
   PHYSIQUE dans le viewport (Jiggle, Hair, Cloth : os à ressort, réglages, physics-config.json), MAINS et IK
   (Gun / Hand / Sword G-D, repères déplaçables, pieds verrouillés), affichage des os et des repères. Les gestes
   three.js de la pose vivante sont dans animer_pose.js. */
"use strict";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { creerCanevas, charger, vider, orienter } from "/lib3d/viewer.js";
import { T, listeGeneres, choisirMarche, cleCategorie, cleSous, pagesVisibles, requeteCatalogue, VUES, vueCamera, miroir,
  curseurVersTemps, tempsVersCurseur, horloge, VITESSES, actionDeTouche, pasConduite, bornerDuree, prix,
  blocageTexte, lienEtabli, estHy, bornesDuree, corpsTexte, FAMILLES, PHYSIQUE_DEFAUT, PHYSIQUE_BORNES, configPhysique,
  prise, ORDRE_PRISES } from "./animer_calc.js";
import { analyser, cliche, restaurer, resoudreMembre, courberDoigts, pasPhysique, remettreRessorts, positionMonde } from "./animer_pose.js";

const A = {
  s: null, ctx: null, fiche: null, api: null, mixer: null, action: null, courant: null, clips: new Map(),
  joue: false, vitesse: 1, boucle: true, etat: null, animer: null, chargeLe: null,
  gauche: "generes", collection: "", q: "", categorie: "", sous: "", page: 1, catalogue: null, collections: [],
  choisie: null, devisChoisie: null, droite: "generer", prompt: "", duree: 3, mode: "swift", occupe: false,
  suivi: null, avis: "", erreur: "", conduite: false, touches: new Set(), pos: { x: 0, z: 0, cap: 0 }, base: null,
  taille: 1.7, source: null, rt: { nom: "", vitesse: 1, boucle: true, en_place: false, aligner: true }, aJouer: null,
  /* t405 */
  modele: "meshy", guidance: 5, squ: null, cliche: null, sol: [0, 0, 0], ancre: null, aides: null, squelette: null, tc: null,
  physique: { actifs: { jiggle: false, hair: false, cloth: false }, mains: true, reglages: { ...PHYSIQUE_DEFAUT } },
  ik: { g: null, d: null, pieds: null }, voir: { os: false, reperes: true },
};
let _loader = null;
const loader = () => (_loader = _loader || new GLTFLoader());
const $ = (sel) => A.s.querySelector(sel);

async function lireJson(r) {
  const t = await r.text();
  let j = {};
  try { j = t ? JSON.parse(t) : {}; } catch { j = { detail: t }; }
  if (!r.ok) {
    const d = j && j.detail;
    const e = new Error(typeof d === "string" ? d : (d && d.message) || String(r.status));
    e.status = r.status; e.detail = d; throw e;
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
  section.innerHTML = `<div class="ec-trois an-trois">
    <aside class="ec-gauche an-gauche">
      <div class="ec-segments ec-plein" id="anGauche" role="tablist" aria-label="${esc(T("anim.titre_biblio"))}">
        ${["generes", "favoris", "tous"].map((v) => `<button data-gauche="${v}" role="tab">${esc(T("anim.onglet_" + v))}</button>`).join("")}
      </div>
      <div class="an-tete"><span class="ec-label">${esc(T("anim.collections"))}</span>
        <button class="an-mini" id="anNouvelle" title="${esc(T("anim.collection_nouvelle"))}">${ico("dz-action-ajouter")} ${esc(T("anim.collection_nouvelle_court"))}</button></div>
      <div class="an-collections" id="anCollections"></div>
      <div id="anFiltres">
        <input class="ec-recherche an-recherche" id="anQ" type="search" placeholder="${esc(T("anim.recherche"))}" aria-label="${esc(T("anim.recherche"))}">
        <div class="an-puces" id="anCats"></div>
        <div class="an-puces an-sous" id="anSous"></div>
      </div>
      <div class="an-compte" id="anCompte"></div>
      <div class="an-liste" id="anListe"></div>
      <div class="an-pages" id="anPages"></div>
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue an-barre">
        <div class="ec-segments" id="anVues">${VUES.map((v) =>
          `<button data-vue="${v}" title="${esc(T("anim.vue_" + v.toLowerCase() + "_aide"))}">${esc(T("anim.vue_" + v.toLowerCase()))}</button>`).join("")}</div>
        <button class="ec-bouton" id="anRepos" title="${esc(T("anim.repos_aide"))}">${ico("dz-lab3d-os")} ${esc(T("anim.repos"))}</button>
        <button class="ec-bouton" id="anConduite" aria-pressed="false" title="${esc(T("anim.conduite_aide"))}">${ico("dz-outil-photo-deplacer")} ${esc(T("anim.conduite"))}</button>
      </div>
      <div class="ec-barre-vue an-outils" id="anOutils"></div>
      <div class="ec-vues">
        <figure class="ec-vue an-vue"><canvas tabindex="0" aria-label="${esc(T("anim.viewport"))}"></canvas>
          <figcaption id="anCap"></figcaption>
          <div class="an-calque hidden" id="anSansRig"></div>
          <div class="an-clavier hidden" id="anClavier">${esc(T("anim.conduite_touches"))}</div>
        </figure>
      </div>
      <div class="an-transport">
        <button class="an-jouer" id="anJouer" aria-label="${esc(T("anim.jouer"))}" title="${esc(T("anim.jouer"))}">${ico("dz-media-lecture")}</button>
        <input type="range" id="anTemps" min="0" max="1000" step="1" value="0" aria-label="${esc(T("anim.temps"))}">
        <span class="an-horloge" id="anHorloge">—</span>
        <label class="an-vitesse">${esc(T("anim.vitesse"))}
          <select id="anVitesse">${VITESSES.map((v) => `<option value="${v}" ${v === 1 ? "selected" : ""}>× ${v}</option>`).join("")}</select></label>
        <label class="ec-bascule"><input type="checkbox" id="anBoucle" checked> ${esc(T("anim.boucle"))}</label>
      </div>
    </main>
    <aside class="ec-droite an-droite">
      <div id="anChoisie"></div>
      <div class="ec-segments ec-plein" id="anDroite" role="tablist">
        <button data-droite="generer" role="tab">${esc(T("anim.onglet_generer"))}</button>
        <button data-droite="importer" role="tab">${esc(T("anim.onglet_importer"))}</button>
        <button data-droite="physique" role="tab">${esc(T("anim.onglet_physique"))}</button>
      </div>
      <div id="anGenerer"></div>
      <div id="anImporter" class="hidden"></div>
      <div id="anPhysique" class="hidden"></div>
    </aside>
  </div>`;
  A.api = creerCanevas(section.querySelector(".an-vue canvas"));
  monterAides();
  brancher();
  boucle();
  await Promise.all([lireAnimer(), lireCollections()]);
  await lireCatalogue();
  peindre();
}

export async function ouvrir(fiche) {
  if (!A.s) return;
  const meme = A.fiche && fiche && A.fiche.job === fiche.job && A.fiche.version === fiche.version;
  A.fiche = fiche;
  if (!meme) { A.etat = null; A.choisie = A.choisie && fiche ? A.choisie : null; A.source = null; A.suivi = null; }
  quitterConduite();
  peindre();
  if (!fiche) { arreter(); oublierPose(); vider(A.api); A.clips.clear(); A.chargeLe = null; peindre(); return; }
  await Promise.all([chargerModele(fiche), lireEtat(), lireAnimer()]);
  peindre();
  if (A.aJouer) {
    const it = generes().find((c) => c.nom === A.aJouer && c.jouable);
    A.aJouer = null;
    if (it) jouer(it);
  }
}

export function montre() { peindre(); }

/* ── lectures serveur ─────────────────────────────────────────────────────── */

async function lireAnimer() {
  try {
    const q = A.fiche ? `?job=${encodeURIComponent(A.fiche.job)}` : "";
    A.animer = await lireJson(await fetch("/api/studio3d/animer/etat" + q));
  } catch { A.animer = A.animer || null; }
}

async function lireEtat() {
  const f = A.fiche;
  if (!f || !(f.rig && f.rig.rigge)) { A.etat = null; return; }
  try {
    A.etat = await lireJson(await fetch(`/api/etabli/mouvement?job=${encodeURIComponent(f.job)}&version=${f.version}`));
  } catch (e) { A.etat = null; A.erreur = T("anim.erreur", { m: e.message }); }
}

async function lireCollections() {
  try { A.collections = (await lireJson(await fetch("/api/studio3d/animer/collections"))).collections || []; } catch { A.collections = []; }
}

let _catN = 0;
async function lireCatalogue() {
  if (A.gauche === "generes") return;
  const n = ++_catN;
  try {
    const r = await lireJson(await fetch(requeteCatalogue({ vue: A.gauche, collection: A.collection, q: A.q,
      categorie: A.categorie, sous: A.sous, page: A.page })));
    if (n === _catN) { A.catalogue = r; A.page = r.page; }
  } catch (e) { if (n === _catN) { A.catalogue = null; A.erreur = T("anim.erreur", { m: e.message }); } }
}

const generes = () => listeGeneres(A.etat, A.fiche && A.fiche.job);
const rigge = () => !!(A.fiche && A.fiche.rig && A.fiche.rig.rigge);

/* ── peinture ─────────────────────────────────────────────────────────────── */

function peindre() {
  if (!A.s) return;
  peindreGauche();
  peindreCentre();
  peindreChoisie();
  peindreDroite();
}

function peindreGauche() {
  const { esc, ico } = A.ctx;
  for (const b of A.s.querySelectorAll("#anGauche [data-gauche]")) {
    const on = b.dataset.gauche === A.gauche;
    b.classList.toggle("on", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  }
  $("#anCollections").innerHTML = A.collections.length
    ? A.collections.map((c) => `<div class="an-col ${A.gauche === "collection" && A.collection === c.id ? "on" : ""}">
        <button class="an-col-nom" data-collection="${esc(c.id)}">${esc(c.nom)} <span>${(c.ids || []).length}</span></button>
        <button class="an-mini" data-suppr-col="${esc(c.id)}" title="${esc(T("anim.collection_supprimer"))}" aria-label="${esc(T("anim.collection_supprimer"))}">${ico("dz-action-fermer")}</button></div>`).join("")
    : `<div class="ec-note">${esc(T("anim.collections_vide"))}</div>`;
  const cat = A.gauche !== "generes";
  $("#anFiltres").classList.toggle("hidden", !cat);
  const liste = $("#anListe"), pages = $("#anPages"), compte = $("#anCompte");
  if (!cat) {
    pages.innerHTML = "";
    compte.textContent = "";
    if (!A.fiche) { liste.innerHTML = `<div class="ec-note">${esc(T("anim.sans_modele"))}</div>`; return; }
    if (!rigge()) { liste.innerHTML = `<div class="ec-note">${esc(T("anim.generes_sans_rig"))}</div>`; return; }
    const l = generes();
    liste.innerHTML = l.length ? l.map((c) => `<div class="an-ligne ${A.courant && A.courant.cle === c.cle ? "on" : ""}">
        <button class="an-ligne-nom" data-clip="${esc(c.cle)}" ${c.jouable ? "" : 'data-appliquer="1"'}>
          <b>${esc(c.nom)}</b><span>${esc(T("anim.origine_" + c.origine.replace("-", "_")))}${c.secondes != null ? " · " + esc(horloge(c.secondes, c.secondes).split(" / ")[0]) : ""}</span></button>
        ${c.jouable
          ? `<button class="an-mini" data-clip="${esc(c.cle)}" title="${esc(T("anim.jouer"))}" aria-label="${esc(T("anim.jouer"))}">${ico("dz-media-lecture")}</button>`
          : `<button class="an-mini" data-source="${esc(c.cle)}" title="${esc(T("anim.a_appliquer"))}">${esc(T("anim.appliquer_court"))}</button>`}</div>`).join("")
      : `<div class="ec-note">${esc(T("anim.generes_vide"))}</div>`;
    return;
  }
  const c = A.catalogue;
  const cats = (c && c.categories) || [];
  $("#anCats").innerHTML = `<button class="an-puce ${A.categorie ? "" : "on"}" data-cat="">${esc(T("anim.toutes"))}</button>`
    + cats.map((x) => `<button class="an-puce ${A.categorie === x.id ? "on" : ""}" data-cat="${esc(x.id)}">${esc(T(cleCategorie(x.id)))} <span>${x.nombre}</span></button>`).join("");
  const sous = (cats.find((x) => x.id === A.categorie) || {}).sous || [];
  $("#anSous").innerHTML = sous.length > 1
    ? `<button class="an-puce ${A.sous ? "" : "on"}" data-sous="">${esc(T("anim.toutes"))}</button>`
      + sous.map((x) => `<button class="an-puce ${A.sous === x.id ? "on" : ""}" data-sous="${esc(x.id)}">${esc(T(cleSous(x.id)))} <span>${x.nombre}</span></button>`).join("")
    : "";
  if (!c) { liste.innerHTML = `<div class="ec-note">${esc(A.erreur || T("anim.chargement"))}</div>`; pages.innerHTML = ""; return; }
  compte.textContent = T("anim.compte", { n: c.total, t: c.nombre });
  const enCol = A.gauche === "collection";
  const ajout = A.collections.filter((x) => !enCol || x.id !== A.collection);
  liste.innerHTML = c.entrees.length ? c.entrees.map((e) => `<div class="an-ligne ${A.choisie && A.choisie.id === e.id ? "on" : ""}">
      <button class="an-etoile ${e.favori ? "on" : ""}" data-favori="${e.id}" aria-pressed="${e.favori ? "true" : "false"}"
        title="${esc(T(e.favori ? "anim.favori_retirer" : "anim.favori_ajouter"))}" aria-label="${esc(T(e.favori ? "anim.favori_retirer" : "anim.favori_ajouter"))}">${ico("dz-action-favori")}</button>
      <button class="an-ligne-nom" data-choisir="${e.id}"><b>${esc(e.nom)}</b><span>#${e.id} · ${esc(T(cleSous(e.sous_categorie || e.categorie)))}</span></button>
      ${enCol ? `<button class="an-mini" data-retirer="${e.id}" title="${esc(T("anim.collection_retirer"))}" aria-label="${esc(T("anim.collection_retirer"))}">${A.ctx.ico("dz-action-retirer")}</button>` : ""}
      ${ajout.length ? `<select class="an-ajout" data-ajout="${e.id}" aria-label="${esc(T("anim.collection_ajouter"))}" title="${esc(T("anim.collection_ajouter"))}">
        <option value="">＋</option>${ajout.map((x) => `<option value="${esc(x.id)}">${esc(x.nom)}</option>`).join("")}</select>` : ""}
    </div>`).join("")
    : `<div class="ec-note">${esc(T(A.gauche === "favoris" ? "anim.favoris_vide" : "anim.catalogue_vide"))}</div>`;
  pages.innerHTML = c.pages > 1 ? pagesVisibles(c.page, c.pages).map((p) => p == null ? `<span>…</span>`
    : `<button class="an-page ${p === c.page ? "on" : ""}" data-page="${p}">${p}</button>`).join("") : "";
}

function peindreCentre() {
  const { esc, ico } = A.ctx;
  const calque = $("#anSansRig");
  if (A.fiche && !rigge()) {
    calque.innerHTML = `<b>${esc(T("anim.sans_rig_titre"))}</b><span>${esc(T("anim.sans_rig"))}</span>
      <button class="ec-principal" data-aller-rig="1">${ico("dz-lab3d-rig")} ${esc(T("anim.aller_rig"))}</button>`;
    calque.classList.remove("hidden");
  } else if (!A.fiche) {
    calque.innerHTML = `<span>${esc(T("anim.sans_modele"))}</span>`;
    calque.classList.remove("hidden");
  } else calque.classList.add("hidden");
  $("#anCap").textContent = A.courant ? T("anim.cap", { c: A.courant.nom }) : (rigge() ? T("anim.cap_aucun") : "");
  const b = $("#anConduite");
  b.classList.toggle("on", A.conduite);
  b.setAttribute("aria-pressed", A.conduite ? "true" : "false");
  b.disabled = !rigge();
  $("#anRepos").disabled = !rigge();
  $("#anClavier").classList.toggle("hidden", !A.conduite);
  $("#anClavier").textContent = A.conduite && !choisirMarche(generes()) ? T("anim.conduite_sans_marche") : T("anim.conduite_touches");
  peindreOutils();
  peindreJouer();
}

function peindreJouer() {
  const { ico, esc } = A.ctx;
  const b = $("#anJouer");
  b.innerHTML = ico(A.joue ? "dz-media-pause" : "dz-media-lecture");
  b.title = T(A.joue ? "anim.pause" : "anim.jouer");
  b.setAttribute("aria-label", b.title);
  b.disabled = !A.action;
  $("#anTemps").disabled = !A.action;
  void esc;
}

function peindreChoisie() {
  const { esc, ico } = A.ctx;
  const el = $("#anChoisie");
  const e = A.choisie;
  if (!e) { el.innerHTML = ""; return; }
  const d = A.devisChoisie;
  let h = `<div class="an-choisie"><div class="ec-label">${esc(T("anim.choisie"))}</div>
    <b>${esc(e.nom)}</b><span>#${e.id} · ${esc(T(cleCategorie(e.categorie)))} › ${esc(T(cleSous(e.sous_categorie || e.categorie)))}</span>`;
  if (!e.applicable) h += `<div class="ec-note">${esc(T("anim.choisie_base"))}</div>`;
  else if (!A.fiche) h += `<div class="ec-note">${esc(T("anim.sans_modele"))}</div>`;
  else if (!rigge()) h += `<div class="ec-note">${esc(T("anim.sans_rig"))}</div>`;
  else if (!d) h += `<div class="ec-note">${esc(T("anim.devis_en_cours"))}</div>`;
  else if (d.erreur) h += `<div class="ec-avis">${esc(d.erreur)}</div>`;
  else {
    const p = d.voie === "animation" ? prix(d.devis) : prix(d.devis);
    h += `<div class="ec-note">${esc(T(d.voie === "animation" ? "anim.voie_animation" : "anim.voie_rig"))}</div>`
      + (!d.meshy ? `<div class="ec-avis">${esc(T("anim.bloc_cle"))}</div>` : "")
      + `<button class="ec-principal" id="anAppliquer" ${!d.meshy || A.occupe ? "disabled" : ""}>${ico("dz-cat-animation")} ${esc(T("anim.appliquer", { p }))}</button>`;
  }
  el.innerHTML = h + `</div>`;
}

function peindreDroite() {
  for (const b of A.s.querySelectorAll("#anDroite [data-droite]")) {
    const on = b.dataset.droite === A.droite;
    b.classList.toggle("on", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  }
  $("#anGenerer").classList.toggle("hidden", A.droite !== "generer");
  $("#anImporter").classList.toggle("hidden", A.droite !== "importer");
  $("#anPhysique").classList.toggle("hidden", A.droite !== "physique");
  if (A.droite === "generer") peindreGenerer();
  else if (A.droite === "importer") peindreImporter();
  else peindrePhysique();
}

function blocage() {
  const lic = licenceHy();
  return blocageTexte({ fiche: A.fiche, meshy: A.animer && A.animer.meshy, fal: A.animer && A.animer.fal, prompt: A.prompt,
    mode: A.mode, modele: A.modele, licence: lic && lic.acceptee,
    occupe: A.occupe || (!!A.suivi && !["fini", "echec", "interrompu"].includes(A.suivi.etat)) });
}
const licenceHy = () => (A.animer && A.animer.texte && A.animer.texte.hy && A.animer.texte.hy.licence) || null;
const devisHy = (id) => (((A.animer && A.animer.texte && A.animer.texte.hy && A.animer.texte.hy.modeles) || []).find((m) => m.id === id) || {}).devis;

/* le prix du modèle choisi, pour le bouton et le dialogue */
function prixChoisi() {
  if (estHy(A.modele)) return prix(devisHy(A.modele));
  const m = ((A.animer && A.animer.texte && A.animer.texte.modes) || []).find((x) => x.id === A.mode);
  return m ? prix(m.devis) : "";
}

function peindreGenerer() {
  const { esc, ico } = A.ctx;
  const t = (A.animer && A.animer.texte) || null;
  const modes = (t && t.modes) || [];
  const hy = (t && t.hy) || null;
  const lic = licenceHy();
  const bloc = blocage();
  /* les raisons EXACTES des modèles du relevé que l'on ne branche pas (Sorceress les montre) */
  const raisons = { kimodo: "anim.raison_kimodo", gvhmr: "anim.raison_gvhmr" };
  const choisi = (id, mode) => (id === "meshy" ? A.modele === "meshy" && A.mode === mode : A.modele === id);
  let h = `<div class="ec-label">${esc(T("anim.modeles"))}</div><div class="an-modeles">`
    + modes.map((m) => `<label class="an-modele ${m.lisible ? "" : "off"}"><input type="checkbox" data-modele="meshy" data-mode="${m.id}" ${choisi("meshy", m.id) ? "checked" : ""} ${m.lisible ? "" : "disabled"}>
        <span><b>${esc(T("anim.modele_" + m.id))}</b><i>${esc(m.lisible ? prix(m.devis) : T("anim.raison_fbx"))}</i></span></label>`).join("")
    + ((hy && hy.modeles) || []).map((m) => {
      const ok = !!(lic && lic.acceptee);
      return `<label class="an-modele ${ok ? "" : "off"}"><input type="checkbox" data-modele="${esc(m.id)}" ${choisi(m.id) ? "checked" : ""} ${ok ? "" : "disabled"}>
        <span><b>${esc(T("anim.modele_" + m.id.replace(/-/g, "_")))}</b><i>${esc(ok ? prix(m.devis) + " · fal" : T("anim.raison_licence"))}</i></span></label>`;
    }).join("")
    + ((t && t.autres) || []).map((m) => `<label class="an-modele off"><input type="checkbox" disabled>
        <span><b>${esc(T("anim.modele_" + m.id.replace(/-/g, "_")))}</b><i>${esc(T(raisons[m.id] || "anim.raison_sans_api"))}</i></span></label>`).join("")
    + `</div>`;
  if (lic) {
    h += `<div class="an-licence ${lic.acceptee ? "on" : ""}">
      <b>${esc(T("anim.licence_titre"))}</b>
      <span>${esc(T("anim.licence_texte", { n: lic.nom }))}</span>
      <span>${esc(T("anim.licence_avis"))}</span>
      <a href="${esc(lic.url)}" target="_blank" rel="noopener noreferrer">${ico("dz-action-ouvrir-externe")} ${esc(T("anim.licence_lire"))}</a>
      <label class="ec-bascule"><input type="checkbox" id="anLicence" ${lic.acceptee ? "checked" : ""}> ${esc(T("anim.licence_case"))}</label>
    </div>`;
  }
  const b = bornesDuree(A.modele);
  h += `<label class="ec-champ">${esc(T("anim.prompt"))}<textarea id="anPrompt" rows="4" maxlength="400" placeholder="${esc(T("anim.prompt_exemple"))}">${esc(A.prompt)}</textarea></label>`
    + `<div class="an-compteur">${A.prompt.length} / 400</div>`
    + `<label class="ec-champ">${esc(T("anim.duree"))} <b class="an-val" id="anDureeVal">${esc(String(A.duree).replace(".", ","))} s</b>
        <input type="range" id="anDuree" min="${b.min}" max="${b.max}" step="${b.pas}" value="${A.duree}"></label>`;
  if (estHy(A.modele)) {
    h += `<label class="ec-champ" title="${esc(T("anim.guidance_aide"))}">${esc(T("anim.guidance"))} <b class="an-val" id="anGuidanceVal">${esc(String(A.guidance).replace(".", ","))}</b>
        <input type="range" id="anGuidance" min="1" max="10" step="0.5" value="${A.guidance}"></label>`;
  } else {
    h += `<label class="ec-champ off">${esc(T("anim.intensite"))}<input type="range" min="0" max="100" value="60" disabled></label>`
      + `<div class="ec-note">${esc(T("anim.intensite_non"))}</div>`;
  }
  h += `<button class="ec-principal" id="anGenererGo" ${bloc ? "disabled" : ""}>${ico("dz-etat-ia")} ${esc(T("anim.generer", { p: prixChoisi() }))}</button>`
    + (bloc && bloc !== "anim.bloc_prompt" ? `<div class="ec-avis">${esc(T(bloc))}</div>` : "")
    + (!rigge() && A.fiche ? `<button class="ec-bouton bloc" data-aller-rig="1">${ico("dz-lab3d-rig")} ${esc(T("anim.aller_rig"))}</button>` : "")
    + `<div class="ec-note">${esc(T(estHy(A.modele) ? "anim.texte_note_hy" : "anim.texte_note"))}</div>`;
  h += peindreSuivi();
  $("#anGenerer").innerHTML = h;
}

function peindreSuivi() {
  const { esc } = A.ctx;
  let h = "";
  if (A.suivi) {
    const s = A.suivi;
    const cle = { prepare: "anim.suivi_prepare", genere: "anim.suivi_genere", recible: "anim.suivi_recible", fini: "anim.suivi_fini",
      echec: "anim.suivi_echec", interrompu: "anim.suivi_interrompu" }[s.etat] || "anim.suivi_prepare";
    h += `<div class="an-suivi ${s.etat}" role="status">${esc(T(cle, { m: s.erreur || "", v: s.version || "", c: s.clip || s.nom || "" }))}</div>`;
  }
  if (A.erreur) h += `<div class="an-erreur" role="alert">${esc(A.erreur)}</div>`;
  if (A.avis) h += `<div class="an-ok">${esc(A.avis)}</div>`;
  return h;
}

function peindreImporter() {
  const { esc, ico } = A.ctx;
  const f = A.fiche;
  let h = `<div class="ec-note">${esc(T("anim.importer_intro"))}</div>`;
  if (!f) { $("#anImporter").innerHTML = h + `<div class="ec-note">${esc(T("anim.sans_modele"))}</div>`; return; }
  if (!rigge()) {
    $("#anImporter").innerHTML = h + `<div class="ec-note">${esc(T("anim.sans_rig"))}</div>`
      + `<button class="ec-bouton bloc" data-aller-rig="1">${ico("dz-lab3d-rig")} ${esc(T("anim.aller_rig"))}</button>`;
    return;
  }
  const srcs = generes();
  h += `<input id="anFichier" type="file" accept=".bvh,.glb" hidden>`
    + `<button class="ec-bouton bloc" id="anImporterFichier" ${A.occupe ? "disabled" : ""}>${ico("dz-action-importer")} ${esc(T("anim.importer_fichier"))}</button>`
    + `<div class="ec-label">${esc(T("anim.source"))}</div>`
    + (srcs.length ? `<div class="an-sources">` + srcs.map((s) => `<label class="an-source"><input type="radio" name="anSource" value="${esc(s.cle)}" ${A.source === s.cle ? "checked" : ""}>
        <span>${esc(s.nom)}</span><i>${esc(T("anim.origine_" + s.origine.replace("-", "_")))}</i></label>`).join("") + `</div>`
      : `<div class="ec-note">${esc(T("anim.generes_vide"))}</div>`)
    + `<label class="ec-champ">${esc(T("anim.rt_nom"))}<input type="text" id="anRtNom" maxlength="48" value="${esc(A.rt.nom)}" placeholder="${esc(T("anim.rt_nom_exemple"))}"></label>`
    + `<label class="ec-champ">${esc(T("anim.vitesse"))} <b class="an-val" id="anRtVitVal">× ${A.rt.vitesse}</b><input type="range" id="anRtVit" min="0.1" max="4" step="0.05" value="${A.rt.vitesse}"></label>`
    + `<label class="ec-bascule"><input type="checkbox" id="anRtBoucle" ${A.rt.boucle ? "checked" : ""}> ${esc(T("anim.rt_boucle"))}</label>`
    + `<label class="ec-bascule"><input type="checkbox" id="anRtPlace" ${A.rt.en_place ? "checked" : ""}> ${esc(T("anim.rt_sur_place"))}</label>`
    + `<label class="ec-bascule" title="${esc(T("anim.rt_aligner_aide"))}"><input type="checkbox" id="anRtAligner" ${A.rt.aligner ? "checked" : ""}> ${esc(T("anim.rt_aligner"))}</label>`
    + `<button class="ec-principal" id="anRtGo" ${A.source && !A.occupe ? "" : "disabled"}>${ico("dz-lab3d-rig")} ${esc(T("anim.rt_appliquer", { v: f.version }))}</button>`
    + `<div class="ec-label">${esc(T("anim.video_titre"))}</div>`
    + `<div class="ec-note">${esc(T("anim.video_note"))}</div>`
    + `<a class="ec-bouton bloc" href="${esc(lienEtabli(f.job, f.version))}">${ico("dz-media-video")} ${esc(T("anim.video_etabli"))}</a>`
    + peindreSuivi();
  $("#anImporter").innerHTML = h;
}

/* ── gestes ───────────────────────────────────────────────────────────────── */

function brancher() {
  const s = A.s;
  s.addEventListener("click", async (ev) => {
    const el = (sel) => ev.target.closest(sel);
    let b;
    if ((b = el("[data-gauche]"))) { A.gauche = b.dataset.gauche; A.collection = ""; A.page = 1; A.catalogue = null; peindre(); await lireCatalogue(); peindreGauche(); }
    else if ((b = el("[data-collection]"))) { A.gauche = "collection"; A.collection = b.dataset.collection; A.page = 1; A.catalogue = null; peindreGauche(); await lireCatalogue(); peindreGauche(); }
    else if ((b = el("[data-suppr-col]"))) await supprimerCollection(b.dataset.supprCol);
    else if ((b = el("#anNouvelle"))) await nouvelleCollection();
    else if ((b = el("[data-cat]"))) { A.categorie = b.dataset.cat; A.sous = ""; A.page = 1; await lireCatalogue(); peindreGauche(); }
    else if ((b = el("[data-sous]"))) { A.sous = b.dataset.sous; A.page = 1; await lireCatalogue(); peindreGauche(); }
    else if ((b = el("[data-page]"))) { A.page = +b.dataset.page; await lireCatalogue(); peindreGauche(); $("#anListe").scrollTop = 0; }
    else if ((b = el("[data-favori]"))) await basculerFavori(+b.dataset.favori, !b.classList.contains("on"));
    else if ((b = el("[data-retirer]"))) await modifierCollection(A.collection, { retirer: [+b.dataset.retirer] });
    else if ((b = el("[data-choisir]"))) await choisir(+b.dataset.choisir);
    else if ((b = el("[data-clip]"))) {
      const it = generes().find((c) => c.cle === b.dataset.clip);
      if (it && it.jouable) jouer(it);
      else if (it) { A.droite = "importer"; A.source = it.cle; A.rt.nom = A.rt.nom || it.nom.replace(/\.(bvh|glb)$/i, ""); peindreDroite(); }
    }
    else if ((b = el("[data-source]"))) { A.droite = "importer"; A.source = b.dataset.source; const it = generes().find((c) => c.cle === A.source); if (it && !A.rt.nom) A.rt.nom = it.nom.replace(/\.(bvh|glb)$/i, ""); peindreDroite(); }
    else if ((b = el("[data-aller-rig]"))) A.ctx.aller("rig");
    else if ((b = el("[data-vue]"))) vue(b.dataset.vue);
    else if ((b = el("#anRepos"))) poseDeLiaison();
    else if ((b = el("#anConduite"))) { A.conduite ? quitterConduite() : entrerConduite(); peindreCentre(); }
    else if ((b = el("#anJouer"))) basculerLecture();
    else if ((b = el("[data-droite]"))) { A.droite = b.dataset.droite; peindreDroite(); }
    else if ((b = el("#anGenererGo"))) await generer();
    else if ((b = el("#anAppliquer"))) await appliquerChoisie();
    else if ((b = el("#anImporterFichier"))) $("#anFichier").click();
    else if ((b = el("#anRtGo"))) await appliquerSource();
    else if ((b = el("[data-famille]"))) basculerFamille(b.dataset.famille);
    else if ((b = el("[data-prise]"))) appliquerPrise(b.dataset.prise);
    else if ((b = el("[data-voir]"))) basculerVoir(b.dataset.voir);
    else if ((b = el("#anPieds"))) basculerPieds();
    else if ((b = el("[data-deplacer]"))) attacher(b.dataset.deplacer);
    else if ((b = el("[data-retirer-ik]"))) retirerIK(b.dataset.retirerIk);
    else if ((b = el("#anPhysDefaut"))) { A.physique.reglages = { ...PHYSIQUE_DEFAUT }; remettreRessorts(A.squ); peindrePhysique(); }
    else if ((b = el("#anPhysConfig"))) telechargerConfig();
  });
  s.addEventListener("change", async (ev) => {
    const t = ev.target;
    if (t.matches("[data-ajout]") && t.value) { const c = t.value; t.value = ""; await modifierCollection(c, { ajouter: [+t.dataset.ajout] }); }
    else if (t.matches("[data-modele]")) {
      if (t.checked) {
        A.modele = t.dataset.modele;
        if (t.dataset.mode) A.mode = t.dataset.mode;
        A.duree = bornerDuree(A.duree, bornesDuree(A.modele));
      }
      peindreGenerer();
    }
    else if (t.id === "anLicence") await poserLicence(t.checked);
    else if (t.id === "anFichier") await importerFichier(t.files && t.files[0]);
    else if (t.name === "anSource") { A.source = t.value; const it = generes().find((c) => c.cle === A.source); if (it) A.rt.nom = it.nom.replace(/\.(bvh|glb)$/i, ""); peindreImporter(); }
    else if (t.id === "anVitesse") { A.vitesse = Number(t.value) || 1; if (A.mixer) A.mixer.timeScale = A.vitesse; }
    else if (t.id === "anBoucle") { A.boucle = t.checked; if (A.action) A.action.setLoop(A.boucle ? THREE.LoopRepeat : THREE.LoopOnce, Infinity); }
    else if (t.id === "anRtBoucle") A.rt.boucle = t.checked;
    else if (t.id === "anRtPlace") A.rt.en_place = t.checked;
    else if (t.id === "anRtAligner") A.rt.aligner = t.checked;
    else if (t.id === "anRtNom") A.rt.nom = t.value;
  });
  s.addEventListener("input", (ev) => {
    const t = ev.target;
    if (t.id === "anQ") { A.q = t.value; A.page = 1; clearTimeout(A._q); A._q = setTimeout(async () => { await lireCatalogue(); peindreGauche(); }, 220); }
    else if (t.id === "anPrompt") {
      A.prompt = t.value;
      const c = A.s.querySelector(".an-compteur");
      if (c) c.textContent = `${A.prompt.length} / 400`;
      const go = $("#anGenererGo");
      if (go) go.disabled = !!blocage();
    }
    else if (t.id === "anDuree") { A.duree = bornerDuree(t.value, bornesDuree(A.modele)); $("#anDureeVal").textContent = String(A.duree).replace(".", ",") + " s"; }
    else if (t.id === "anGuidance") { A.guidance = Number(t.value) || 5; $("#anGuidanceVal").textContent = String(A.guidance).replace(".", ","); }
    else if (t.matches("[data-reglage]")) {
      A.physique.reglages[t.dataset.reglage] = Number(t.value);
      const v = A.s.querySelector(`[data-reglage-val="${t.dataset.reglage}"]`);
      if (v) v.textContent = String(Number(t.value)).replace(".", ",");
    }
    else if (t.id === "anRtVit") { A.rt.vitesse = Number(t.value); $("#anRtVitVal").textContent = `× ${A.rt.vitesse}`; }
    else if (t.id === "anTemps" && A.action) {
      A.joue = false;
      A.action.paused = true;
      A.action.time = curseurVersTemps(t.value, A.action.getClip().duration);
      A.mixer.update(0);
      if (A.squ) A.cliche = cliche(A.squ);
      peindreJouer();
      majHorloge();
    }
  });
  window.addEventListener("keydown", (ev) => clavier(ev, true));
  window.addEventListener("keyup", (ev) => clavier(ev, false));
  window.addEventListener("blur", () => A.touches.clear());
}

/* ── catalogue : choix, favoris, collections ──────────────────────────────── */

async function choisir(id) {
  const e = A.catalogue && A.catalogue.entrees.find((x) => x.id === id);
  if (!e) return;
  A.choisie = e;
  A.devisChoisie = null;
  peindreGauche();
  peindreChoisie();
  if (!A.fiche || !rigge() || !e.applicable) return;
  try {
    A.devisChoisie = await lireJson(await fetch(`/api/studio3d/animer/appliquer/devis?job=${encodeURIComponent(A.fiche.job)}&action_id=${id}`));
  } catch (err) { A.devisChoisie = { erreur: err.message }; }
  if (A.choisie && A.choisie.id === id) peindreChoisie();
}

async function basculerFavori(id, favori) {
  try {
    await poster("/api/studio3d/animer/favoris", { id, favori });
    await lireCatalogue();
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  peindreGauche();
}

async function nouvelleCollection() {
  const D = window.__dzDialogue;
  const nom = D && D.saisir ? await D.saisir(T("anim.collection_nom"), { titre: T("anim.collection_nouvelle") }) : null;
  if (!nom || !nom.trim()) return;
  try {
    const r = await poster("/api/studio3d/animer/collections", { nom: nom.trim(), ids: A.choisie ? [A.choisie.id] : [] });
    A.collections = r.collections;
    A.gauche = "collection"; A.collection = r.collection.id; A.page = 1;
    await lireCatalogue();
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  peindreGauche();
}

async function modifierCollection(cid, champs) {
  try {
    const r = await poster("/api/studio3d/animer/collections", { id: cid, ...champs });
    A.collections = r.collections;
    if (A.gauche === "collection") await lireCatalogue();
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  peindreGauche();
}

async function supprimerCollection(cid) {
  const c = A.collections.find((x) => x.id === cid);
  const D = window.__dzDialogue;
  if (!c || !D || !(await D.confirmer(T("anim.collection_supprimer_q", { n: c.nom }), { titre: T("anim.collection_supprimer") }))) return;
  try {
    A.collections = (await lireJson(await fetch(`/api/studio3d/animer/collections/${encodeURIComponent(cid)}`, { method: "DELETE" }))).collections;
    if (A.collection === cid) { A.gauche = "tous"; A.collection = ""; await lireCatalogue(); }
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  peindreGauche();
}

/* ── dépenses : appliquer une animation, texte → mouvement ───────────────── */

async function appliquerChoisie() {
  const e = A.choisie, d = A.devisChoisie, f = A.fiche;
  if (!e || !d || d.erreur || !f || A.occupe) return;
  const p = prix(d.devis);
  const D = window.__dzDialogue;
  /* le devis AVANT l'envoi, par le dialogue maison : refus par défaut (le sens sûr, comme dz-plafonds) */
  if (!D || !(await D.confirmer(T(d.voie === "animation" ? "anim.confirmer_animation" : "anim.confirmer_rig", { n: e.nom, p }),
    { titre: T("anim.choisie"), ok: T("anim.confirmer_ok", { p }) }))) return;
  A.occupe = true; A.erreur = A.avis = ""; peindreChoisie();
  try {
    if (d.voie === "animation") {
      const r = await poster("/api/studio3d/animer/appliquer", { job: f.job, action_id: e.id, confirme_cout: true });
      A.suivi = { etat: "prepare" };
      suivre(f.job, r.tache, async (fin) => {
        if (fin.etat !== "fini") return;
        await lireEtat();
        peindre();
        const it = generes().find((c) => c.type === "meshy" && c.nom === fin.nom);
        if (it) jouer(it);
      });
    } else {
      await poster(`/api/assets/3d/${encodeURIComponent(f.job)}/rig`, { actions: [e.id], confirme_cout: true });
      A.avis = T("anim.rig_lance");
    }
  } catch (err) {
    A.erreur = err.status === 503 ? T("anim.bloc_cle") : T("anim.erreur", { m: err.message });
  } finally {
    A.occupe = false; peindre();
  }
}

async function generer() {
  const f = A.fiche;
  if (blocage()) return;
  const p = prixChoisi();
  const D = window.__dzDialogue;
  const hy = estHy(A.modele);
  const q = hy ? T("anim.confirmer_hy", { p, s: String(A.duree).replace(".", ","), v: f.version, m: T("anim.modele_" + A.modele.replace(/-/g, "_")) })
    : T("anim.confirmer_texte", { p, s: String(A.duree).replace(".", ","), v: f.version });
  if (!D || !(await D.confirmer(q, { titre: T("anim.onglet_generer"), ok: T("anim.confirmer_ok", { p }) }))) return;
  A.occupe = true; A.erreur = A.avis = ""; A.suivi = { etat: "prepare" }; peindreGenerer();
  try {
    const lic = licenceHy();
    const corps = corpsTexte({ fiche: f, modele: A.modele, mode: A.mode, prompt: A.prompt, duree: A.duree, guidance: A.guidance,
      licence: !!(lic && lic.acceptee) });
    const r = await poster("/api/studio3d/animer/texte", { ...corps, confirme_cout: true });
    suivre(f.job, r.tache, async (fin) => {
      if (fin.etat === "fini" && fin.version) { A.aJouer = fin.clip; await A.ctx.ouvrir(f.job, fin.version, "animer"); }
    });
  } catch (err) {
    A.suivi = null;
    A.erreur = err.status === 503 ? T(hy ? "anim.bloc_cle_fal" : "anim.bloc_cle") : T("anim.erreur", { m: err.message });
  } finally {
    A.occupe = false; peindreDroite();
  }
}

/* la case « J'ai lu la licence » de HY-Motion : rangée par le serveur dans le dossier de données de l'utilisateur */
async function poserLicence(acceptee) {
  try {
    const r = await poster("/api/studio3d/animer/licence", { acceptee });
    if (A.animer && A.animer.texte && A.animer.texte.hy) A.animer.texte.hy.licence = r.licence;
    if (!r.licence.acceptee && estHy(A.modele)) { A.modele = "meshy"; A.mode = "swift"; A.duree = bornerDuree(A.duree); }
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  peindreGenerer();
}

function suivre(job, tache, quandFini) {
  const t = setInterval(async () => {
    try {
      const e = await lireJson(await fetch(`/api/studio3d/animer/tache?job=${encodeURIComponent(job)}&tache=${tache}`));
      A.suivi = e;
      if (["fini", "echec", "interrompu"].includes(e.etat)) { clearInterval(t); await quandFini(e); }
    } catch (err) {
      clearInterval(t); A.suivi = { etat: "echec", erreur: err.message };
    }
    peindreDroite();
  }, 2000);
}

/* ── importer un mouvement : les routes de l'Établi (t343), sans recopier leur logique ── */

async function importerFichier(fichier) {
  const f = A.fiche;
  if (!fichier || !f || A.occupe) return;
  A.occupe = true; A.erreur = A.avis = ""; peindreImporter();
  try {
    const fd = new FormData();
    fd.append("job", f.job); fd.append("fichier", fichier);
    const r = await lireJson(await fetch("/api/etabli/mouvement/importer", { method: "POST", body: fd }));
    A.source = `${r.source.type}:${r.source.nom}`;
    A.rt.nom = r.source.nom.replace(/\.(bvh|glb)$/i, "");
    A.avis = T("anim.importe", { n: r.source.nom });
    await lireEtat();
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  A.occupe = false;
  peindre();
}

async function appliquerSource() {
  const f = A.fiche;
  const it = generes().find((c) => c.cle === A.source);
  if (!f || !it || A.occupe) return;
  const nom = (A.rt.nom || "").trim() || it.nom.replace(/\.(bvh|glb)$/i, "");
  A.occupe = true; A.erreur = A.avis = ""; peindreImporter();
  try {
    const r = await poster("/api/etabli/mouvement/appliquer", { job: f.job, version: f.version,
      source: { type: it.type, nom: it.nom }, nom, aligner: A.rt.aligner,
      retimage: { vitesse: A.rt.vitesse, boucle: A.rt.boucle, en_place: A.rt.en_place } });
    A.avis = T("anim.rt_fait", { v: r.version, c: nom });
    A.aJouer = nom;
    A.occupe = false;
    await A.ctx.ouvrir(f.job, r.version, "animer");
  } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  A.occupe = false;
  peindre();
}

/* ── t405 : physique, mains et IK dans le viewport (aperçu gratuit) ─────────── */

const CLES_FAMILLE = { jiggle: "anim.phys_jiggle", hair: "anim.phys_hair", cloth: "anim.phys_cloth" };
const CLES_FAMILLE_SANS = { jiggle: "anim.phys_sans_jiggle", hair: "anim.phys_sans_hair", cloth: "anim.phys_sans_cloth" };
const CLES_PRISE = { gun_g: "anim.prise_gun_g", gun_d: "anim.prise_gun_d", main_g: "anim.prise_main_g", main_d: "anim.prise_main_d",
  epee_g: "anim.prise_epee_g", epee_d: "anim.prise_epee_d" };
const CLES_REGLAGE = { raideur: "anim.phys_raideur", amortissement: "anim.phys_amortissement", gravite: "anim.phys_gravite" };
const CLES_REGLAGE_AIDE = { raideur: "anim.phys_raideur_aide", amortissement: "anim.phys_amortissement_aide", gravite: "anim.phys_gravite_aide" };
const CLES_CIBLE = { g: "anim.ik_main_g", d: "anim.ik_main_d", pieds: "anim.ik_pieds" };

/* les aides du viewport : l'ancre (repère du personnage : pieds, cap), les repères IK, le gizmo, le squelette */
function monterAides() {
  A.aides = new THREE.Group();
  A.aides.name = "dzAnimerAides";
  A.api.scene.add(A.aides);
  A.ancre = new THREE.Object3D();
  A.ancre.name = "dzAnimerAncre";
  A.aides.add(A.ancre);
  A.tc = new TransformControls(A.api.camera, A.api.renderer.domElement);
  A.tc.setMode("translate");
  A.tc.setSize(0.7);
  A.api.scene.add(A.tc.getHelper());
  A.tc.addEventListener("dragging-changed", (e) => { A.api.controls.enabled = !e.value; A.glisse = e.value; });
  const cv = A.s.querySelector(".an-vue canvas");
  cv.addEventListener("pointerdown", (e) => { A.appui = [e.clientX, e.clientY]; }, true);
  cv.addEventListener("pointerup", (e) => {
    if (!A.appui || Math.hypot(e.clientX - A.appui[0], e.clientY - A.appui[1]) > 4 || A.glisse) return;
    pointerRepere(e, cv);
  });
}

/* un clic sur un repère IK l'attrape avec le gizmo */
function pointerRepere(e, cv) {
  if (!A.voir.reperes) return;
  const r = cv.getBoundingClientRect();
  const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(ndc, A.api.camera);
  const marques = ["g", "d"].map((c) => A.ik[c] && A.ik[c].marqueur).filter(Boolean)
    .concat(A.ik.pieds ? A.ik.pieds.map((p) => p.marqueur) : []);
  const hit = ray.intersectObjects(marques, false)[0];
  if (hit) A.tc.attach(hit.object);
}

function marqueur(couleur) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.01, A.taille * 0.022), 16, 12),
    new THREE.MeshBasicMaterial({ color: couleur, depthTest: false, transparent: true, opacity: 0.9 }));
  m.renderOrder = 999;
  m.visible = A.voir.reperes;
  A.ancre.add(m);
  return m;
}

function oterMarqueur(m) {
  if (!m) return;
  if (A.tc.object === m) A.tc.detach();
  A.ancre.remove(m);
  m.geometry.dispose(); m.material.dispose();
}

/* tout ce qui décrit le modèle précédent s'en va avec lui */
function oublierPose() {
  for (const c of ["g", "d"]) { if (A.ik[c]) oterMarqueur(A.ik[c].marqueur); A.ik[c] = null; }
  if (A.ik.pieds) for (const p of A.ik.pieds) oterMarqueur(p.marqueur);
  A.ik.pieds = null;
  if (A.squelette) { A.aides.remove(A.squelette); A.squelette.dispose(); A.squelette = null; }
  A.squ = null; A.cliche = null;
}

/* le repère du personnage : sa racine (déplacée en mode conduite), son cap, ses pieds */
function majAncre() {
  const r = A.api.racine;
  if (!r || !A.base) return;
  A.ancre.position.copy(r.position);
  A.ancre.rotation.set(0, r.rotation.y - A.base.rot, 0);
  A.ancre.updateMatrixWorld(true);
}

function peindreOutils() {
  const { esc, ico } = A.ctx;
  const squ = A.squ;
  const ok = rigge() && !!squ;
  const bouton = (attrs, on, actif, titre, html) =>
    `<button class="ec-bouton an-outil ${on ? "on" : ""}" ${attrs} aria-pressed="${on ? "true" : "false"}" ${actif ? "" : "disabled"} title="${esc(titre)}">${html}</button>`;
  let h = `<span class="an-groupe" role="group" aria-label="${esc(T("anim.phys_titre"))}"><span class="an-groupe-nom">${esc(T("anim.phys_titre"))}</span>`;
  for (const f of FAMILLES) {
    const n = ok ? squ.familles[f].length : 0;
    h += bouton(`data-famille="${f}"`, A.physique.actifs[f] && n > 0, n > 0,
      n > 0 ? T("anim.phys_aide", { n, f: T(CLES_FAMILLE[f]) }) : T(ok ? CLES_FAMILLE_SANS[f] : "anim.sans_rig"), esc(T(CLES_FAMILLE[f])));
  }
  const doigts = ok ? squ.doigts.g.length + squ.doigts.d.length : 0;
  h += bouton(`data-famille="mains"`, A.physique.mains && doigts > 0, doigts > 0,
    doigts > 0 ? T("anim.phys_mains_aide", { n: doigts }) : T(ok ? "anim.phys_sans_mains" : "anim.sans_rig"),
    `${ico("dz-outil-vec-main")} ${esc(T("anim.phys_mains"))}`);
  h += `</span><span class="an-groupe" role="group" aria-label="${esc(T("anim.ik_titre"))}"><span class="an-groupe-nom">${esc(T("anim.ik_titre"))}</span>`;
  for (const id of ORDRE_PRISES) {
    const cote = id.slice(-1);
    const bras = ok && squ.chaines["bras_" + cote];
    h += bouton(`data-prise="${id}"`, !!(A.ik[cote] && A.ik[cote].prise === id), !!bras,
      bras ? T(id.startsWith("main") ? "anim.prise_main_aide" : "anim.prise_aide", { p: T(CLES_PRISE[id]) }) : T(ok ? "anim.ik_sans_bras" : "anim.sans_rig"),
      esc(T(CLES_PRISE[id])));
  }
  const jambes = ok && squ.chaines.jambe_g && squ.chaines.jambe_d;
  h += `</span><span class="an-groupe" role="group" aria-label="${esc(T("anim.voir_titre"))}"><span class="an-groupe-nom">${esc(T("anim.voir_titre"))}</span>`
    + bouton(`data-voir="os"`, A.voir.os, ok, T("anim.voir_os_aide"), `${ico("dz-lab3d-os")} ${esc(T("anim.voir_os"))}`)
    + bouton(`data-voir="reperes"`, A.voir.reperes, ok, T("anim.voir_reperes_aide"), esc(T("anim.voir_reperes")))
    + bouton(`id="anPieds"`, !!A.ik.pieds, !!jambes, jambes ? T("anim.pieds_aide") : T(ok ? "anim.ik_sans_jambes" : "anim.sans_rig"),
      `${ico("dz-etat-verrouille")} ${esc(T("anim.pieds"))}`)
    + `</span>`;
  $("#anOutils").innerHTML = h;
}

function peindrePhysique() {
  const { esc, ico } = A.ctx;
  const squ = A.squ;
  const r = A.physique.reglages;
  let h = `<div class="ec-note">${esc(T("anim.phys_intro"))}</div>`;
  if (!A.fiche || !rigge() || !squ) {
    $("#anPhysique").innerHTML = h + `<div class="ec-note">${esc(T(A.fiche ? "anim.sans_rig" : "anim.sans_modele"))}</div>`;
    return;
  }
  h += `<div class="an-familles">` + FAMILLES.map((f) => {
    const n = squ.familles[f].length;
    return `<div class="an-famille ${n ? "" : "off"}"><b>${esc(T(CLES_FAMILLE[f]))}</b><i>${n ? esc(T("anim.phys_os", { n })) : esc(T(CLES_FAMILLE_SANS[f]))}</i></div>`;
  }).join("") + `</div>`;
  for (const k of ["raideur", "amortissement", "gravite"]) {
    const [mi, ma, pas] = PHYSIQUE_BORNES[k];
    h += `<label class="ec-champ" title="${esc(T(CLES_REGLAGE_AIDE[k]))}">${esc(T(CLES_REGLAGE[k]))} <b class="an-val" data-reglage-val="${k}">${esc(String(r[k]).replace(".", ","))}</b>
      <input type="range" data-reglage="${k}" min="${mi}" max="${ma}" step="${pas}" value="${r[k]}"></label>`;
  }
  h += `<div class="an-rangee"><button class="ec-bouton" id="anPhysDefaut">${ico("dz-action-reinitialiser")} ${esc(T("anim.phys_defaut"))}</button>
      <button class="ec-bouton" id="anPhysConfig" title="${esc(T("anim.phys_config_aide"))}">${ico("dz-action-telecharger")} physics-config.json</button></div>`
    + `<div class="ec-note">${esc(T("anim.phys_conduite"))}</div>`;
  h += `<div class="ec-label">${esc(T("anim.ik_cibles"))}</div>`;
  const lignes = [];
  for (const c of ["g", "d"]) {
    const x = A.ik[c];
    if (!x) continue;
    const sans = x.p.courbure > 0 && !squ.doigts[c].length;
    lignes.push(`<div class="an-cible"><span><b>${esc(T(CLES_CIBLE[c]))}</b><i>${esc(T(CLES_PRISE[x.prise]))}${x.atteint === false ? " · " + esc(T("anim.ik_hors_portee")) : ""}</i>
        ${sans ? `<i class="an-note-doigts">${esc(T("anim.prise_sans_doigts"))}</i>` : ""}</span>
      <button class="an-mini" data-deplacer="${c}" title="${esc(T("anim.ik_deplacer"))}">${ico("dz-outil-photo-deplacer")}</button>
      <button class="an-mini" data-retirer-ik="${c}" title="${esc(T("anim.ik_retirer"))}" aria-label="${esc(T("anim.ik_retirer"))}">${ico("dz-action-fermer")}</button></div>`);
  }
  if (A.ik.pieds) {
    lignes.push(`<div class="an-cible"><span><b>${esc(T(CLES_CIBLE.pieds))}</b><i>${esc(T("anim.pieds_note"))}</i></span>
      <button class="an-mini" data-deplacer="pieds" title="${esc(T("anim.ik_deplacer"))}">${ico("dz-outil-photo-deplacer")}</button>
      <button class="an-mini" data-retirer-ik="pieds" title="${esc(T("anim.ik_retirer"))}" aria-label="${esc(T("anim.ik_retirer"))}">${ico("dz-action-fermer")}</button></div>`);
  }
  h += lignes.length ? lignes.join("") : `<div class="ec-note">${esc(T("anim.ik_aucune"))}</div>`;
  h += `<div class="ec-note">${esc(T("anim.ik_note"))}</div>`;
  $("#anPhysique").innerHTML = h;
}

function basculerFamille(f) {
  if (!A.squ) return;
  if (f === "mains") A.physique.mains = !A.physique.mains;
  else if (A.squ.familles[f] && A.squ.familles[f].length) { A.physique.actifs[f] = !A.physique.actifs[f]; remettreRessorts(A.squ); }
  peindreOutils();
  if (A.droite === "physique") peindrePhysique();
}

function basculerVoir(k) {
  A.voir[k] = !A.voir[k];
  if (k === "os" && A.squelette) A.squelette.visible = A.voir.os;
  if (k === "reperes") {
    for (const m of tousLesReperes()) m.visible = A.voir.reperes;
    if (!A.voir.reperes) A.tc.detach();
  }
  peindreOutils();
}

const tousLesReperes = () => ["g", "d"].map((c) => A.ik[c] && A.ik[c].marqueur).filter(Boolean)
  .concat(A.ik.pieds ? A.ik.pieds.map((p) => p.marqueur) : []);

/* Gun / Hand / Sword : la cible de la main (repère du personnage) + la courbure des doigts ; un second clic l'ôte */
function appliquerPrise(id) {
  const p = prise(id, A.taille);
  if (!p || !A.squ || !A.squ.chaines["bras_" + p.cote]) return;
  const c = p.cote;
  if (A.ik[c] && A.ik[c].prise === id) { retirerIK(c); return; }
  if (A.ik[c]) oterMarqueur(A.ik[c].marqueur);
  const m = marqueur(c === "g" ? 0xf2a33a : 0x3ab0f2);
  majAncre();
  if (p.cible) m.position.set(p.cible[0] + A.sol[0], p.cible[1] + A.sol[1], p.cible[2] + A.sol[2]);
  else m.position.copy(A.ancre.worldToLocal(positionMonde(A.squ.chaines["bras_" + c][2])));
  A.ik[c] = { prise: id, p, marqueur: m, atteint: true };
  if (A.voir.reperes) A.tc.attach(m);
  peindreOutils();
  if (A.droite !== "physique") { A.droite = "physique"; peindreDroite(); } else peindrePhysique();
}

function retirerIK(c) {
  if (c === "pieds") { if (A.ik.pieds) for (const p of A.ik.pieds) oterMarqueur(p.marqueur); A.ik.pieds = null; }
  else if (A.ik[c]) { oterMarqueur(A.ik[c].marqueur); A.ik[c] = null; }
  peindreOutils();
  if (A.droite === "physique") peindrePhysique();
}

function attacher(c) {
  const m = c === "pieds" ? A.ik.pieds && A.ik.pieds[0].marqueur : A.ik[c] && A.ik[c].marqueur;
  if (!m) return;
  if (!A.voir.reperes) basculerVoir("reperes");
  A.tc.attach(m);
}

/* Lock Ends : les pieds restent là où ils sont à l'instant du clic (repère du personnage), l'IK des jambes les y tient */
function basculerPieds() {
  if (A.ik.pieds) { retirerIK("pieds"); return; }
  if (!A.squ || !A.squ.chaines.jambe_g || !A.squ.chaines.jambe_d) return;
  majAncre();
  A.ik.pieds = ["g", "d"].map((c) => {
    const m = marqueur(0x5ad19a);
    m.position.copy(A.ancre.worldToLocal(positionMonde(A.squ.chaines["jambe_" + c][2])));
    return { cote: c, marqueur: m };
  });
  peindreOutils();
  if (A.droite === "physique") peindrePhysique();
}

function telechargerConfig() {
  const f = A.fiche;
  const cfg = configPhysique({ job: f && f.job, version: f && f.version, actifs: A.physique.actifs, reglages: A.physique.reglages,
    os: A.squ ? A.squ.familles : {} });
  const url = URL.createObjectURL(new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url; a.download = "physics-config.json";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* la pose vivante, chaque image, APRÈS le mixer : pieds verrouillés, mains (IK + doigts), physique */
function poseVivante(dt) {
  const squ = A.squ, r = A.api.racine;
  if (!squ || !r) return;
  majAncre();
  r.updateMatrixWorld(true);
  const q = A.ancre.quaternion;
  if (A.ik.pieds) {
    for (const p of A.ik.pieds) {
      const ch = squ.chaines["jambe_" + p.cote];
      if (ch) resoudreMembre(ch, p.marqueur.getWorldPosition(new THREE.Vector3()), new THREE.Vector3(0, 0, 1).applyQuaternion(q));
    }
  }
  let change = false;
  for (const c of ["g", "d"]) {
    const x = A.ik[c];
    if (!x) continue;
    const ch = squ.chaines["bras_" + c];
    if (!ch) continue;
    const res = resoudreMembre(ch, x.marqueur.getWorldPosition(new THREE.Vector3()), new THREE.Vector3(0, -0.3, -1).normalize().applyQuaternion(q));
    if (res.atteint !== x.atteint) { x.atteint = res.atteint; change = true; }
    if (A.physique.mains && x.p.courbure > 0) courberDoigts(squ, c, x.p);
  }
  if (FAMILLES.some((f) => A.physique.actifs[f])) pasPhysique(squ, A.physique.actifs, A.physique.reglages, dt);
  if (change && A.droite === "physique") peindrePhysique();
}

/* ── le viewport : modèle, clips, lecteur ─────────────────────────────────── */

async function chargerModele(fiche) {
  const cle = `${fiche.job}#${fiche.version}`;
  if (A.chargeLe === cle && A.api.racine) return;
  arreter();
  A.clips.clear();
  A.courant = null;
  oublierPose();
  try {
    await charger(A.api, fiche.url);
  } catch { A.chargeLe = null; return; }
  A.chargeLe = cle;
  const r = A.api.racine;
  A.mixer = new THREE.AnimationMixer(r);
  A.mixer.timeScale = A.vitesse;
  A.base = { x: r.position.x, y: r.position.y, z: r.position.z, rot: r.rotation.y };
  A.pos = { x: 0, z: 0, cap: 0 };
  const boite = new THREE.Box3().setFromObject(r);
  A.taille = Math.max(0.2, boite.max.y - boite.min.y) || 1.7;
  /* les pieds du personnage dans son repère (centre de la boîte au sol, depuis la racine) : l'origine des prises */
  A.sol = [(boite.min.x + boite.max.x) / 2 - r.position.x, boite.min.y - r.position.y, (boite.min.z + boite.max.z) / 2 - r.position.z];
  memoriserRepos();
  A.squ = analyser(r);
  A.cliche = cliche(A.squ);
  A.squelette = new THREE.SkeletonHelper(r);
  A.squelette.material.depthTest = false;
  A.squelette.renderOrder = 998;
  A.squelette.visible = A.voir.os;
  A.aides.add(A.squelette);
  for (const c of (A.api.gltf && A.api.gltf.animations) || []) A.clips.set("clip:" + c.name, c);
}

async function clipDe(it) {
  if (A.clips.has(it.cle)) return A.clips.get(it.cle);
  if (!it.url) return null;
  const g = await loader().loadAsync(it.url);
  const c = (g.animations || [])[0] || null;
  if (c) A.clips.set(it.cle, c);
  return c;
}

async function jouer(it) {
  if (!A.mixer) return;
  let clip;
  try { clip = await clipDe(it); } catch (e) { A.erreur = T("anim.erreur", { m: e.message }); }
  if (!clip) { A.erreur = A.erreur || T("anim.clip_illisible", { c: it.nom }); peindreDroite(); return; }
  A.mixer.stopAllAction();
  A.action = A.mixer.clipAction(clip);
  A.action.setLoop(A.boucle ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  A.action.clampWhenFinished = true;
  A.action.reset().play();
  A.courant = it;
  A.joue = true;
  peindreGauche();
  peindreCentre();
}

function basculerLecture() {
  if (!A.action) return;
  A.joue = !A.joue;
  if (A.joue && !A.action.isRunning() && A.action.time >= A.action.getClip().duration - 1e-3) A.action.reset();
  A.action.paused = !A.joue;
  if (A.joue) A.action.play();
  peindreJouer();
}

function arreter() {
  if (A.mixer) A.mixer.stopAllAction();
  A.action = null; A.joue = false;
}

/* la pose de LIAISON (bind pose) : les transformations des os telles que le GLB les pose au chargement (la pose de
   repos de l'export). PAS `skeleton.pose()` : mesuré sur 8804, il recopie la matrice monde dans la matrice LOCALE de
   l'os racine et ignore l'armature parente (×0,01, −90° en X chez Blender, Mixamo, Meshy) — le modèle sortait du cadre. */
function memoriserRepos() {
  A.repos = new Map();
  A.api.racine.traverse((o) => {
    if (o.isBone) A.repos.set(o, { p: o.position.clone(), q: o.quaternion.clone(), s: o.scale.clone() });
  });
}

function poseDeLiaison() {
  if (!A.api.racine) return;
  arreter();
  A.courant = null;
  for (const [o, r] of A.repos || []) { o.position.copy(r.p); o.quaternion.copy(r.q); o.scale.copy(r.s); }
  if (A.squ) { A.cliche = cliche(A.squ); remettreRessorts(A.squ); }
  peindreCentre();
  peindreGauche();
}

function vue(id) {
  const v = vueCamera(id);
  orienter(A.api, v.orientation);
  if (v.miroir) {
    const c = A.api.controls.target, p = A.api.camera.position;
    const m = miroir(p, c);
    p.set(m.x, m.y, m.z);
    A.api.controls.update();
  }
  for (const b of A.s.querySelectorAll("#anVues [data-vue]")) b.classList.toggle("on", b.dataset.vue === id);
}

/* ── le mode conduite ─────────────────────────────────────────────────────── */

function entrerConduite() {
  if (!rigge() || !A.api.racine) return;
  A.conduite = true;
  A.touches.clear();
  A.s.querySelector(".an-vue canvas").focus();
}

function quitterConduite() {
  A.conduite = false;
  A.touches.clear();
  if (A.api && A.api.racine && A.base) {
    A.api.racine.position.set(A.base.x, A.base.y, A.base.z);
    A.api.racine.rotation.y = A.base.rot;
  }
  A.pos = { x: 0, z: 0, cap: 0 };
  if (A.s) peindreCentre();
}

function clavier(ev, bas) {
  if (!A.conduite || !A.s || A.s.classList.contains("hidden")) return;
  if (ev.target && ev.target.closest && ev.target.closest("input, textarea, select")) return;
  const a = actionDeTouche(ev.code);
  if (!a) { if (bas && ev.code === "Escape") { quitterConduite(); } return; }
  ev.preventDefault();
  if (bas) A.touches.add(a); else A.touches.delete(a);
}

let _marche = null;
function pasDeConduite(dt) {
  const r = A.api.racine;
  if (!r || !A.base) return;
  const avant = { x: r.position.x, z: r.position.z };
  const p = pasConduite(A.pos, A.touches, dt, A.taille);
  A.pos = { x: p.x, z: p.z, cap: p.cap };
  r.position.set(A.base.x + p.x, A.base.y, A.base.z + p.z);
  r.rotation.y = A.base.rot + p.cap;
  /* la caméra SUIT : même décalage pour elle et pour sa cible (l'orbite reste libre) */
  const dx = r.position.x - avant.x, dz = r.position.z - avant.z;
  if (dx || dz) {
    A.api.camera.position.x += dx; A.api.camera.position.z += dz;
    A.api.controls.target.x += dx; A.api.controls.target.z += dz;
  }
  /* la marche boucle tant qu'on avance ; à l'arrêt, elle se fige */
  const m = choisirMarche(generes());
  if (p.avance !== 0) {
    if (m && (!A.courant || A.courant.cle !== m.cle) && _marche !== m.cle) { _marche = m.cle; jouer(m).finally(() => { _marche = null; }); }
    else if (A.action && !A.joue) { A.joue = true; A.action.paused = false; peindreJouer(); }
  } else if (A.action && A.joue && m && A.courant && A.courant.cle === m.cle) {
    A.joue = false; A.action.paused = true; peindreJouer();
  }
}

function majHorloge() {
  if (!A.action) { $("#anHorloge").textContent = "—"; return; }
  const d = A.action.getClip().duration;
  const t = A.action.time % (d || 1);
  $("#anHorloge").textContent = horloge(t, d);
  const c = $("#anTemps");
  if (document.activeElement !== c) c.value = tempsVersCurseur(t, d);
}

function boucle() {
  let avant = performance.now(), dernier = 0;
  const tic = () => {
    requestAnimationFrame(tic);
    const t = performance.now(), dt = Math.min(0.1, (t - avant) / 1000);
    avant = t;
    if (!A.s || A.s.classList.contains("hidden")) return;
    if (A.conduite) pasDeConduite(dt);
    /* la pose ANIMÉE (mixer) est photographiée ; à l'arrêt elle est rendue chaque image, puis IK, doigts et physique
       se posent dessus — jamais les uns sur les autres */
    if (A.mixer && A.joue) { A.mixer.update(dt); if (A.squ) A.cliche = cliche(A.squ); }
    else if (A.squ && A.cliche) restaurer(A.squ, A.cliche);
    if (A.squ) poseVivante(dt);
    if (t - dernier > 100) { dernier = t; majHorloge(); }
  };
  requestAnimationFrame(tic);
}
