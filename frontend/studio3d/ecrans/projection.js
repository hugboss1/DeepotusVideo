/* t394 (31/10/2026) — écran TEXTURE du 3D Studio, volet 2/2 : la TEXTURE AUTO par projection multi-vues, les
   retouches au pinceau et l'enregistrement en version.

   Relevé de Sorceress (§4 de l'inventaire) : AUTO TEXTURE en 4 / 6 / 8 / 10 / 12 / 16 / 18 vues (« capture chaque
   angle, IA en parallèle, projette, fusionne »), « Depuis le maillage ombré » ; outils Gomme (rend l'origine),
   Estomper, Soigner les coutures, Combler depuis les voisins, Tout combler, Débruiter (IA), Annuler / Rétablir ;
   masquer la base d'origine ; atlas UV à plat (peint / GLB d'origine) ; fil de fer ; propriété des vues ;
   visualiseur de fissures.

   Le chemin : chaque vue de la disposition est rendue d'une caméra carrée qui cadre le modèle (cameraDePose), la
   capture part chez le modèle d'image choisi (POST …/generer-lot : un devis pour les N vues, le dialogue maison,
   puis une seule garde des plafonds sur le total) ; chaque image rendue se projette sur l'atlas UV (projection_calc :
   position et normale de chaque texel, test de profondeur, poids max(0, n·v)^k, fusion), et l'atlas peint habille
   aussitôt le modèle. Les retouches travaillent sur l'atlas, au pinceau posé sur le modèle (rayon → UV) ou sur
   l'atlas à plat. « Enregistrer » envoie l'atlas (PNG) : le serveur réécrit le GLB en NOUVELLE version.

   « Projeter les captures (essai, gratuit) » — outil de développement, visible avec ?essai dans l'adresse ou
   localStorage « dz.studio3d.essai » = "1" : les captures elles-mêmes sont
   projetées, sans aucun appel payant ; tout le reste du chemin (atlas, retouches, version) est le vrai. */
"use strict";
import * as THREE from "three";
import { montrerRepere } from "/lib3d/viewer.js";
import { T, langue } from "./coque_calc.js";
import { DISPOSITIONS, poses, devisDisposition, prixImage, usd } from "./texture_calc.js";
import * as C from "./projection_calc.js";

const API = "/api/studio3d/texture";
const CAPTURE = 1024;           // le côté d'une capture (et de l'image demandée au modèle)
const PROFONDEUR = 512;         // le côté de la carte de profondeur d'une vue
const TRANCHE = 120000;         // texels projetés entre deux respirations de l'interface
const OUTILS = ["gomme", "estomper", "combler"];

const S = { h: null, dispo: 8, ombre: true, k: 4, outil: null, taille: 24, force: 0.6, mode: "peint", cacher: false,
  fil: false, atlasMode: "peint", m: null, A: null, E: null, pile: null, coutures: null, sphere: null, original: null,
  canevas: null, cx: null, img: null, origCanevas: null, tex: null, fils: [], occupe: false, trait: null, vues: 0,
  disposition: null, modifie: false, dessin: 0, essai: false };

const $ = (sel) => S.h.section.querySelector(sel);
/* l'essai gratuit est un outil de DÉVELOPPEMENT : `?essai` dans l'adresse (la coque la réécrit vite : lue aussi au
   chargement du module) ou localStorage « dz.studio3d.essai » = "1" */
const ESSAI_ADRESSE = (() => { try { return new URLSearchParams(location.search).has("essai"); } catch { return false; } })();
const essaiPermis = () => {
  if (ESSAI_ADRESSE) return true;
  try { return new URLSearchParams(location.search).has("essai") || localStorage.getItem("dz.studio3d.essai") === "1"; }
  catch { return false; }
};

/* ── le HTML (inséré par texture.js) ──────────────────────────────────────── */
export function htmlAtlas(esc) {
  return `<div class="ec-label">${esc(T("tex.pj_atlas"))}</div>
    <div class="ec-segments ec-plein" id="pjAtlasMode">${["peint", "original"].map((m) =>
      `<button data-atlas="${m}">${esc(T("tex.pj_atlas_" + m))}</button>`).join("")}</div>
    <figure class="pj-atlas" id="pjAtlasFig"><canvas id="pjAtlas" width="512" height="512"></canvas>
      <figcaption id="pjAtlasLegende">${esc(T("tex.pj_atlas_vide"))}</figcaption></figure>`;
}

export function htmlPanneau(esc, ico) {
  return `<div class="ec-label">${esc(T("tex.pj_auto_titre"))}</div>
    <div class="pj-dispos" id="pjDispos" role="group" aria-label="${esc(T("tex.pj_disposition"))}">${DISPOSITIONS.map((n) =>
      `<button data-dispo="${n}" title="${esc(T("tex.pj_dispo_" + n))}"><b>${n}</b><span data-prix="${n}"></span></button>`).join("")}</div>
    <div class="ec-note" id="pjDispoAide"></div>
    <label class="ec-bascule"><input type="checkbox" id="pjOmbre" checked> ${esc(T("tex.pj_ombre"))}</label>
    <div class="ec-note">${esc(T("tex.pj_ombre_aide"))}</div>
    <label class="tx-curseur pj-curseur">${esc(T("tex.pj_nettete"))}<input type="range" min="1" max="12" step="1" id="pjK" value="4"><output id="pjKVal">4</output></label>
    <label class="ec-champ">${esc(T("tex.prompt"))}
      <textarea id="pjPrompt" rows="3" maxlength="1000" placeholder="${esc(T("tex.prompt_vide"))}"></textarea></label>
    <button class="ec-principal" id="pjAuto">${ico("dz-media-generer-image")} <span id="pjAutoTexte">${esc(T("tex.pj_lancer"))}</span></button>
    <div class="ec-note">${esc(T("tex.pj_auto_aide"))}</div>
    <button class="ec-bouton bloc pj-essai" id="pjEssai" hidden>${ico("dz-lab3d-camera")} ${esc(T("tex.pj_essai"))}</button>
    <div class="ec-label">${esc(T("tex.pj_retouches"))}</div>
    <div class="ec-segments ec-plein" id="pjOutils">${["", ...OUTILS].map((o) =>
      `<button data-outil="${o}" title="${esc(T("tex.pj_outila_" + (o || "orbite")))}">${esc(T("tex.pj_outil_" + (o || "orbite")))}</button>`).join("")}</div>
    <div class="ec-note" id="pjOutilAide">${esc(T("tex.pj_outila_orbite"))}</div>
    <label class="tx-curseur pj-curseur">${esc(T("tex.pj_taille"))}<input type="range" min="2" max="256" step="1" id="pjTaille" value="24"><output id="pjTailleVal">24</output></label>
    <label class="tx-curseur pj-curseur">${esc(T("tex.pj_force"))}<input type="range" min="0.05" max="1" step="0.05" id="pjForce" value="0.6"></label>
    <div class="pj-grille">
      <button class="ec-bouton" id="pjToutCombler" title="${esc(T("tex.pj_tout_combler_aide"))}">${ico("dz-outil-px-pot")} ${esc(T("tex.pj_tout_combler"))}</button>
      <button class="ec-bouton" id="pjSoigner" title="${esc(T("tex.pj_soigner_aide"))}">${ico("dz-outil-vec-lisser")} ${esc(T("tex.pj_soigner"))}</button>
      <button class="ec-bouton" id="pjAnnuler" title="Ctrl+Z">${ico("dz-action-annuler")} ${esc(T("tex.pj_annuler"))}</button>
      <button class="ec-bouton" id="pjRetablir" title="Ctrl+Y">${ico("dz-action-retablir")} ${esc(T("tex.pj_retablir"))}</button>
    </div>
    <button class="ec-bouton bloc" id="pjDebruiter" title="${esc(T("tex.pj_debruiter_aide"))}">${ico("dz-media-generer-image")} <span id="pjDebruiterTexte">${esc(T("tex.pj_debruiter"))}</span></button>
    <div class="ec-label">${esc(T("tex.pj_affichage"))}</div>
    <div class="ec-segments ec-plein" id="pjModes">${C.MODES.map((m) =>
      `<button data-mode="${m}" title="${esc(T("tex.pj_modea_" + m))}">${esc(T("tex.pj_mode_" + m))}</button>`).join("")}</div>
    <label class="ec-bascule"><input type="checkbox" id="pjFil"> ${esc(T("tex.pj_fil"))}</label>
    <label class="ec-bascule"><input type="checkbox" id="pjCacher"> ${esc(T("tex.pj_cacher"))}</label>
    <div class="pj-legende" id="pjLegende"></div>
    <div class="ec-note pj-stats" id="pjStats"></div>
    <button class="ec-principal" id="pjEnregistrer">${ico("dz-action-enregistrer")} ${esc(T("tex.pj_enregistrer"))}</button>
    <div class="ec-note">${esc(T("tex.pj_enregistrer_aide"))}</div>`;
}

/* ── montage : `hote` vient de texture.js ─────────────────────────────────────
   { section, ctx, api, avis(t), envoyer(url, corps), confirmer(texte, ok), modele(), resolution(), fiche(), reg(),
     eclairage(), lumieresPour(pose|null), reappliquer(), ajouterReference(ref) } */
export function monter(hote) {
  S.h = hote;
  S.essai = essaiPermis();
  $("#pjEssai").hidden = !S.essai;
  hote.section.addEventListener("click", surClic);
  $("#pjOmbre").addEventListener("change", (e) => { S.ombre = e.target.checked; });
  $("#pjK").addEventListener("input", (e) => { S.k = +e.target.value; $("#pjKVal").textContent = e.target.value; });
  $("#pjTaille").addEventListener("input", (e) => { S.taille = +e.target.value; $("#pjTailleVal").textContent = e.target.value; });
  $("#pjForce").addEventListener("input", (e) => { S.force = +e.target.value; });
  $("#pjFil").addEventListener("change", (e) => { S.fil = e.target.checked; montrerFils(); dessinerAtlas(); });
  $("#pjCacher").addEventListener("change", (e) => { S.cacher = e.target.checked; rafraichir(); });
  // les pinceaux : en CAPTURE sur la figure, avant qu'OrbitControls ne prenne le geste sur le canevas
  const fig = hote.api.renderer.domElement.parentElement;
  fig.addEventListener("pointerdown", surAppui, true);
  fig.addEventListener("pointermove", surGlisse, true);
  fig.addEventListener("pointerup", surLache, true);
  fig.addEventListener("pointercancel", surLache, true);
  const at = $("#pjAtlas");
  at.addEventListener("pointerdown", surAppuiAtlas);
  at.addEventListener("pointermove", surGlisseAtlas);
  at.addEventListener("pointerup", surLache);
  document.addEventListener("keydown", surTouche);
  peindre();
}

/* un autre modèle (ou une nouvelle version) est chargé : tout l'état de la projection repart de zéro */
export function reinitialiser() {
  const sale = S.modifie;
  for (const f of S.fils) f.removeFromParent();
  Object.assign(S, { m: null, A: null, E: null, pile: null, coutures: null, sphere: null, original: null, canevas: null,
    cx: null, img: null, origCanevas: null, tex: null, fils: [], trait: null, vues: 0, disposition: null, modifie: false });
  if (S.h) { if (sale) S.h.ctx.marquerSale(false); peindre(); peindreStats(); dessinerAtlas(); }
}

/* ── le maillage : positions et normales dans le MONDE, UV glTF, et la texture de base ─────────────────────── */
const matBase = (o) => o.userData.dzTexMatBase || o.userData.dzMatOrigine || o.material;
const premier = (m) => (Array.isArray(m) ? m[0] : m);

function extraire(racine) {
  racine.updateMatrixWorld(true);
  const tous = [];
  racine.traverse((o) => { if (o.isMesh && o.geometry && o.geometry.attributes.position && o.visible) tous.push(o); });
  const avecUV = tous.filter((o) => o.geometry.attributes.uv);
  if (!avecUV.length) throw new Error(T("tex.pj_sans_uv"));
  const cartes = new Set(avecUV.map((o) => (premier(matBase(o)) || {}).map).filter(Boolean));
  if (cartes.size > 1) throw new Error(T("tex.pj_plusieurs", { n: cartes.size }));
  const carte = [...cartes][0] || null;
  const maillages = carte ? avecUV.filter((o) => (premier(matBase(o)) || {}).map === carte) : avecUV;
  const empiler = (liste, avecAttributs) => {
    let nv = 0, ni = 0;
    for (const o of liste) { nv += o.geometry.attributes.position.count; ni += o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count; }
    const positions = new Float32Array(3 * nv), indices = new Uint32Array(ni);
    const normales = avecAttributs ? new Float32Array(3 * nv) : null, uvs = avecAttributs ? new Float32Array(2 * nv) : null;
    let bv = 0, bi = 0;
    const v = new THREE.Vector3(), nm = new THREE.Matrix3();
    for (const o of liste) {
      const g = o.geometry, P = g.attributes.position, N = g.attributes.normal, U = g.attributes.uv;
      nm.getNormalMatrix(o.matrixWorld);
      for (let i = 0; i < P.count; i++) {
        v.fromBufferAttribute(P, i).applyMatrix4(o.matrixWorld);
        positions.set([v.x, v.y, v.z], 3 * (bv + i));
        if (avecAttributs) {
          if (N) { v.fromBufferAttribute(N, i).applyMatrix3(nm).normalize(); normales.set([v.x, v.y, v.z], 3 * (bv + i)); }
          uvs[2 * (bv + i)] = U.getX(i); uvs[2 * (bv + i) + 1] = U.getY(i);
        }
      }
      if (g.index) for (let i = 0; i < g.index.count; i++) indices[bi + i] = bv + g.index.getX(i);
      else for (let i = 0; i < P.count; i++) indices[bi + i] = bv + i;
      bi += g.index ? g.index.count : P.count;
      bv += P.count;
    }
    // sans normales dans le GLB : celles des faces (rasteriserUV les calcule si `normales` est nul)
    const sansNormales = avecAttributs && liste.some((o) => !o.geometry.attributes.normal);
    return { positions, indices, normales: sansNormales ? null : normales, uvs };
  };
  const atlas = empiler(maillages, true);
  const tout = empiler(tous, false);
  const m0 = premier(matBase(maillages[0]));
  return { maillages, carte, atlas, tout, couleur: m0 && m0.color ? m0.color.clone() : new THREE.Color(1, 1, 1) };
}

/* l'atlas d'origine, à la taille de l'atlas peint : la texture de base × la couleur de base (en linéaire, comme
   le moteur) ; sans texture, la couleur de base seule */
function lireOriginal(carte, couleur, W, H) {
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const cx = cv.getContext("2d", { willReadFrequently: true });
  const f = couleur.clone().convertLinearToSRGB();
  if (carte && carte.image) {
    cx.drawImage(carte.image, 0, 0, W, H);
  } else {
    cx.fillStyle = `rgb(${Math.round(f.r * 255)},${Math.round(f.g * 255)},${Math.round(f.b * 255)})`;
    cx.fillRect(0, 0, W, H);
    return { cv, data: cx.getImageData(0, 0, W, H).data };
  }
  const d = cx.getImageData(0, 0, W, H);
  const lin = couleur;
  if (Math.abs(lin.r - 1) + Math.abs(lin.g - 1) + Math.abs(lin.b - 1) > 1e-3) {
    const dec = Float32Array.from({ length: 256 }, (_, i) => versLineaire(i / 255));
    const enc = (x) => Math.round(versSRGB(Math.max(0, Math.min(1, x))) * 255);
    for (let k = 0; k < d.data.length; k += 4) {
      d.data[k] = enc(dec[d.data[k]] * lin.r); d.data[k + 1] = enc(dec[d.data[k + 1]] * lin.g); d.data[k + 2] = enc(dec[d.data[k + 2]] * lin.b);
    }
    cx.putImageData(d, 0, 0);
  }
  return { cv, data: d.data };
}

const versLineaire = (c) => (c < 0.04045 ? c * 0.0773993808 : Math.pow(c * 0.9478672986 + 0.0521327014, 2.4));
const versSRGB = (c) => (c < 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 0.41666) - 0.055);

const souffler = () => new Promise((ok) => setTimeout(ok, 0));

/* la préparation, une fois par modèle chargé : maillage, sphère, atlas rastérisé, original, coutures, affichage */
async function preparer() {
  if (S.A) return;
  const api = S.h.api;
  if (!api.racine) throw new Error(T("tex.pj_sans_modele"));
  S.h.avis(T("tex.pj_preparation"));
  await souffler();
  const m = extraire(api.racine);
  const img = m.carte && m.carte.image;
  const { W, H } = C.tailleAtlas(img && (img.width || img.naturalWidth), img && (img.height || img.naturalHeight));
  const A = C.rasteriserUV(m.atlas, W, H);
  if (!A.n) throw new Error(T("tex.pj_sans_uv"));
  const orig = lireOriginal(m.carte, m.couleur, W, H);
  S.m = m;
  S.A = A;
  S.sphere = C.sphereDe(m.tout.positions);
  S.original = new Uint8ClampedArray(orig.data);
  S.origCanevas = orig.cv;
  S.E = C.nouvelEtat(W, H, S.original, A.masque);
  S.pile = C.nouvellePile();
  S.coutures = C.coutures(m.atlas, W, H);
  S.canevas = document.createElement("canvas");
  S.canevas.width = W; S.canevas.height = H;
  S.cx = S.canevas.getContext("2d");
  S.img = S.cx.createImageData(W, H);
  S.tex = new THREE.CanvasTexture(S.canevas);
  S.tex.flipY = false;
  S.tex.colorSpace = THREE.SRGBColorSpace;
  if (m.carte) { S.tex.wrapS = m.carte.wrapS; S.tex.wrapT = m.carte.wrapT; }
  S.tex.anisotropy = api.renderer.capabilities.getMaxAnisotropy ? api.renderer.capabilities.getMaxAnisotropy() : 1;
  habiller();
  rafraichir();
}

/* le modèle porte l'atlas peint : chaque maillage de l'atlas reçoit une copie de sa matière d'origine avec la
   texture peinte et une couleur de base blanche (la projection a cuit la teinte) ; le mode d'éclairage de l'écran
   la reprend (dzMatOrigine) */
function habiller() {
  for (const o of S.m.maillages) {
    if (!o.userData.dzTexMatBase) o.userData.dzTexMatBase = o.userData.dzMatOrigine || o.material;
    const cl = (mt) => { const c = mt.clone(); c.map = S.tex; if (c.color) c.color.set(0xffffff); c.needsUpdate = true; return c; };
    const b = o.userData.dzTexMatBase;
    o.userData.dzMatOrigine = Array.isArray(b) ? b.map(cl) : cl(b);
    delete o.userData.dzMatAlbedo;
    o.material = o.userData.dzMatOrigine;
  }
  S.h.reappliquer();
  montrerFils();
}

function montrerFils() {
  if (!S.m) return;
  if (S.fil && !S.fils.length) {
    for (const o of S.m.maillages) {
      const l = new THREE.LineSegments(new THREE.WireframeGeometry(o.geometry),
        new THREE.LineBasicMaterial({ color: 0x9fd8ff, transparent: true, opacity: 0.28, depthWrite: false }));
      l.userData.dzFil = true;
      l.raycast = () => {};
      o.add(l);
      S.fils.push(l);
    }
  }
  for (const f of S.fils) f.visible = S.fil;
}

/* ── les captures : une caméra carrée par vue, la grille cachée, les lumières tournées avec la caméra ─────── */
function rendreVue(cam, pose, ombre) {
  const api = S.h.api, r = api.renderer, cv = r.domElement;
  const c3 = new THREE.PerspectiveCamera(cam.fov, 1, cam.pres, cam.loin);
  c3.position.set(...cam.oeil);
  c3.up.set(0, 1, 0);
  c3.lookAt(...cam.cible);
  c3.updateMatrixWorld(true);
  c3.updateProjectionMatrix();
  const L = cv.clientWidth || 1, Hh = cv.clientHeight || 1, pr = r.getPixelRatio();
  r.setPixelRatio(1);
  r.setSize(CAPTURE, CAPTURE, false);
  const repere = montrerRepere(api, false);
  const fils = S.fils.map((f) => f.visible);
  for (const f of S.fils) f.visible = false;
  const remis = [];
  if (ombre) {
    const gris = new THREE.MeshStandardMaterial({ color: 0xc8c8c8, roughness: 0.85, metalness: 0 });
    api.racine.traverse((o) => { if (o.isMesh) { remis.push([o, o.material]); o.material = gris; } });
  }
  S.h.lumieresPour(pose);
  r.render(api.scene, c3);
  const out = document.createElement("canvas");
  out.width = out.height = CAPTURE;
  out.getContext("2d").drawImage(cv, 0, 0);
  for (const [o, m] of remis) o.material = m;
  S.fils.forEach((f, i) => { f.visible = fils[i]; });
  S.h.lumieresPour(null);
  montrerRepere(api, repere);
  r.setPixelRatio(pr);
  r.setSize(L, Hh, false);
  r.render(api.scene, api.camera);
  const M = Array.from(new THREE.Matrix4().multiplyMatrices(c3.projectionMatrix, c3.matrixWorldInverse).elements);
  return { canevas: out, M, oeil: cam.oeil };
}

function capturerTout(n) {
  const ps = poses(n);
  return ps.map((p) => ({ pose: p, ...rendreVue(C.cameraDePose(p, S.sphere), p, S.ombre) }));
}

const chargerImage = (url) => new Promise((ok, ko) => {
  const im = new Image();
  im.onload = () => ok(im);
  im.onerror = () => ko(new Error(T("tex.pj_image_illisible")));
  im.src = url;
});

function pixels(source, largeurMax = 2048) {
  const w0 = source.naturalWidth || source.width, h0 = source.naturalHeight || source.height;
  const k = Math.min(1, largeurMax / Math.max(w0, h0));
  const w = Math.max(1, Math.round(w0 * k)), h = Math.max(1, Math.round(h0 * k));
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  const cx = cv.getContext("2d", { willReadFrequently: true });
  cx.drawImage(source, 0, 0, w, h);
  return cx.getImageData(0, 0, w, h);
}

/* ── la projection : chaque vue sur l'atlas, puis la fusion ─────────────────── */
async function projeter(vues, disposition) {
  const A = S.A, E = S.E;
  C.memoriser(S.pile, E, C.rectTout(E));                      // une projection s'annule comme un geste
  E.couleur.set(E.original);
  E.peint.fill(0);
  E.proprio.fill(-1);
  const acc = C.nouvelAccumulateur(A);
  const biais = S.sphere.rayon * 0.015;
  for (let i = 0; i < vues.length; i++) {
    const v = vues[i];
    S.h.avis(T("tex.pj_projection", { i: i + 1, n: vues.length }));
    await souffler();
    const profondeur = C.carteProfondeur(S.m.tout, v.M, PROFONDEUR, PROFONDEUR);
    const vue = { M: v.M, oeil: v.oeil, profondeur, pw: PROFONDEUR, ph: PROFONDEUR, image: v.image };
    for (let de = 0; de < A.n; de += TRANCHE) {
      C.accumulerVue(A, vue, acc, v.index, { k: S.k, biais, de, a: de + TRANCHE });
      await souffler();
    }
  }
  C.finaliser(A, acc, E);
  S.vues = vues.length;
  S.disposition = disposition;
  S.modifie = true;
  S.h.ctx.marquerSale(true);
  rafraichir();
}

/* la texture auto (payante) : devis du lot → dialogue → captures → modèle d'image → projection */
async function texturerAuto() {
  const m = S.h.modele(), f = S.h.fiche();
  if (!m || !f || S.occupe || !S.h.api.racine) return;
  const res = S.h.resolution(), n = S.dispo;
  let d;
  try { d = await S.h.envoyer(`${API}/devis`, { action: "lot", modele: m.id, resolution: res, vues: n }); }
  catch (e) { return S.h.avis(T("tex.erreur", { m: e.message })); }
  const lg = langue();
  if (!await S.h.confirmer(T("tex.pj_confirmer", { n, modele: m.label, res, usd: usd(d.usd, lg), vue: usd(d.usd_vue, lg) }), T("tex.pj_lancer"))) return;
  occuper(true);
  try {
    await preparer();
    const caps = capturerTout(n);
    S.h.avis(T("tex.pj_en_cours", { n, modele: m.label }));
    const j = await S.h.envoyer(`${API}/${encodeURIComponent(f.job)}/generer-lot`, {
      captures: caps.map((c) => ({ capture: c.canevas.toDataURL("image/png"), pose: c.pose })), disposition: n,
      modele: m.id, resolution: res, prompt: $("#pjPrompt").value.trim(), eclairage: S.h.eclairage(),
      confirme_cout: true, max_usd: d.usd });
    for (const r of j.references) S.h.ajouterReference(r);
    const vues = [];
    for (const r of j.references) {
      const c = caps[r.index];
      vues.push({ index: r.index, M: c.M, oeil: c.oeil, image: pixels(await chargerImage(r.url)) });
    }
    await projeter(vues, String(n));
    S.h.avis(j.erreurs && j.erreurs.length ? T("tex.pj_fait_partiel", { ok: vues.length, n, ko: j.erreurs.length })
      : T("tex.pj_fait", { n }));
  } catch (e) {
    S.h.avis(T("tex.erreur", { m: e.message }));
  } finally { occuper(false); }
}

/* l'essai GRATUIT : les captures elles-mêmes sont projetées (aucun appel payant) */
async function essayer() {
  if (!S.h.fiche() || S.occupe || !S.h.api.racine) return;
  occuper(true);
  try {
    await preparer();
    const caps = capturerTout(S.dispo);
    const vues = caps.map((c, i) => ({ index: i, M: c.M, oeil: c.oeil, image: pixels(c.canevas) }));
    await projeter(vues, `${S.dispo}-essai`);
    S.h.avis(T("tex.pj_essai_fait", { n: S.dispo }));
  } catch (e) {
    S.h.avis(T("tex.erreur", { m: e.message }));
  } finally { occuper(false); }
}

/* « Débruiter » (IA, sur devis) : l'atlas peint part comme image source du modèle d'image, par la route d'une
   génération seule (…/generer, le même devis et le même dialogue) ; l'image rendue revient sur les texels PEINTS */
async function debruiter() {
  const m = S.h.modele(), f = S.h.fiche(), E = S.E;
  if (!m || !f || !E || S.occupe) return;
  const res = S.h.resolution();
  let d;
  try { d = await S.h.envoyer(`${API}/devis`, { action: "generer", modele: m.id, resolution: res }); }
  catch (e) { return S.h.avis(T("tex.erreur", { m: e.message })); }
  if (!await S.h.confirmer(T("tex.pj_confirmer_debruiter", { modele: m.label, usd: usd(d.usd, langue()) }), T("tex.pj_debruiter"))) return;
  occuper(true);
  S.h.avis(T("tex.pj_debruitage", { modele: m.label }));
  try {
    const cote = Math.min(2048, E.W);
    const cv = document.createElement("canvas");
    cv.width = cv.height = cote;
    cv.getContext("2d").drawImage(versCanevas(E.couleur, E.W, E.H), 0, 0, cote, cote);
    const j = await S.h.envoyer(`${API}/${encodeURIComponent(f.job)}/generer`, {
      capture: cv.toDataURL("image/png"), modele: m.id, resolution: res, ratio: "1:1",
      prompt: (S.h.reg() && S.h.reg().prompt_debruiter) || "", vue: "libre", eclairage: "sans", style: null,
      confirme_cout: true, max_usd: d.usd });
    S.h.ajouterReference(j.reference);
    const im = await chargerImage(j.reference.url);
    const big = document.createElement("canvas");
    big.width = E.W; big.height = E.H;
    const bx = big.getContext("2d", { willReadFrequently: true });
    bx.drawImage(im, 0, 0, E.W, E.H);
    const net = bx.getImageData(0, 0, E.W, E.H).data;
    C.memoriser(S.pile, E, C.rectTout(E));
    for (let k = 0; k < E.peint.length; k++) if (E.peint[k]) for (let q = 0; q < 3; q++) E.couleur[4 * k + q] = net[4 * k + q];
    marquer();
    rafraichir();
    S.h.avis(T("tex.pj_debruite"));
  } catch (e) {
    S.h.avis(T("tex.erreur", { m: e.message }));
  } finally { occuper(false); }
}

function versCanevas(rgba, W, H) {
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  cv.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(rgba), W, H), 0, 0);
  return cv;
}

/* « Enregistrer » : l'atlas (débordé de 4 px hors des îlots) en PNG → une NOUVELLE version du GLB, gratuite */
async function enregistrer() {
  const f = S.h.fiche(), E = S.E;
  if (!f || !E || S.occupe) return;
  occuper(true);
  S.h.avis(T("tex.pj_enregistrement"));
  try {
    const out = C.deborder(new Uint8ClampedArray(E.couleur), S.A.masque, E.W, E.H, 4);
    const blob = await new Promise((ok) => versCanevas(out, E.W, E.H).toBlob(ok, "image/png"));
    const atlas = await new Promise((ok, ko) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => ko(r.error); r.readAsDataURL(blob); });
    const j = await S.h.envoyer(`${API}/${encodeURIComponent(f.job)}/projection`, {
      version: f.version, atlas, disposition: S.disposition, vues: S.vues });
    S.modifie = false;
    S.h.ctx.marquerSale(false);
    occuper(false);
    S.h.avis(T("tex.pj_enregistre", { v: j.version }));
    await S.h.ctx.rafraichir();
  } catch (e) {
    S.h.avis(T("tex.erreur", { m: e.message }));
    occuper(false);
  }
}

/* ── les pinceaux ─────────────────────────────────────────────────────────── */
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
function toucherModele(e) {
  if (!S.m) return null;
  const cv = S.h.api.renderer.domElement, r = cv.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, S.h.api.camera);
  const hit = ray.intersectObjects(S.m.maillages, false).find((h) => h.uv);
  return hit ? { x: hit.uv.x * S.E.W, y: hit.uv.y * S.E.H } : null;
}

function tamponner(p) {
  const E = S.E, r = S.taille / 2;
  let rect;
  if (S.outil === "combler") {
    if (S.trait.suite) return;                                  // combler : une poche par appui, pas de trait
    const po = C.poche(E, p.x, p.y, r);
    C.memoriser(S.pile, E, po.rect);
    rect = C.combler(E, { x: p.x, y: p.y, r }).rect;
  } else {
    C.memoriser(S.pile, E, C.rectPinceau(E, p.x, p.y, r), S.trait.suite);
    rect = S.outil === "gomme" ? C.gommer(E, p.x, p.y, r) : C.estomper(E, p.x, p.y, r, S.force);
  }
  S.trait.suite = true;
  marquer();
  rafraichir(C.unionRect(rect, C.rectPinceau(E, p.x, p.y, r)));
}

function surAppui(e) {
  if (!S.outil || !S.E || e.button !== 0 || S.occupe || e.target !== S.h.api.renderer.domElement) return;
  const p = toucherModele(e);
  if (!p) return;                                               // à côté du modèle : l'orbite reste possible
  e.preventDefault();
  e.stopPropagation();
  S.h.api.controls.enabled = false;
  S.trait = { suite: false, cible: e.target, id: e.pointerId, x: e.clientX, y: e.clientY };
  try { e.target.setPointerCapture(e.pointerId); } catch { /* le navigateur refuse : le trait suit quand même */ }
  tamponner(p);
}
/* entre deux événements, des touches tous les 6 px d'ÉCRAN (chacune relancée sur le modèle) : un geste rapide reste
   un trait continu, et il ne saute jamais d'un îlot UV à l'autre en ligne droite dans l'atlas */
function surGlisse(e) {
  if (!S.trait || S.trait.atlas) return;
  const { x, y } = S.trait, d = Math.hypot(e.clientX - x, e.clientY - y), n = Math.max(1, Math.ceil(d / 6));
  for (let i = 1; i <= n; i++) {
    const p = toucherModele({ clientX: x + ((e.clientX - x) * i) / n, clientY: y + ((e.clientY - y) * i) / n });
    if (p) tamponner(p);
  }
  S.trait.x = e.clientX; S.trait.y = e.clientY;
}
function surLache() {
  if (!S.trait) return;
  S.trait = null;
  S.h.api.controls.enabled = true;
  peindreStats();
}
const pointAtlas = (e) => {
  const c = e.currentTarget, r = c.getBoundingClientRect();
  return { x: ((e.clientX - r.left) / r.width) * S.E.W, y: ((e.clientY - r.top) / r.height) * S.E.H };
};
function surAppuiAtlas(e) {
  if (!S.outil || !S.E || e.button !== 0 || S.occupe) return;
  S.trait = { suite: false, atlas: true };
  try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* idem */ }
  tamponner(pointAtlas(e));
}
function surGlisseAtlas(e) { if (S.trait && S.trait.atlas) tamponner(pointAtlas(e)); }

function surTouche(e) {
  if (!S.E || !S.h.section.offsetParent || /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || "")) return;
  if (!(e.ctrlKey || e.metaKey)) return;
  const k = e.key.toLowerCase();
  if (k === "z" && !e.shiftKey) { e.preventDefault(); defaire(false); }
  else if (k === "y" || (k === "z" && e.shiftKey)) { e.preventDefault(); defaire(true); }
}

function defaire(refaire) {
  const r = refaire ? C.retablir(S.pile, S.E) : C.annuler(S.pile, S.E);
  if (!r) return;
  marquer();
  rafraichir(r);
  peindreStats();
}

function marquer() { S.modifie = true; S.h.ctx.marquerSale(true); }

/* ── l'affichage ──────────────────────────────────────────────────────────── */
function rafraichir(rect) {
  if (S.E && S.img) {
    const R = rect || C.rectTout(S.E);
    C.composer(S.E, S.mode, S.cacher, S.img.data, R);
    S.cx.putImageData(S.img, 0, 0, R.x, R.y, R.w, R.h);
    S.tex.needsUpdate = true;
  }
  if (!S.dessin) S.dessin = setTimeout(() => { S.dessin = 0; dessinerAtlas(); }, 40);   // pas de rAF : un volet caché le gèlerait
  if (!rect) peindreStats();
  peindre();
}

function dessinerAtlas() {
  const c = S.h && $("#pjAtlas");
  if (!c) return;
  const cx = c.getContext("2d");
  cx.fillStyle = "#1e2025";
  cx.fillRect(0, 0, c.width, c.height);
  const src = S.atlasMode === "original" ? S.origCanevas : S.canevas;
  if (src) cx.drawImage(src, 0, 0, c.width, c.height);
  if (S.fil && S.m) {
    const { uvs, indices } = S.m.atlas;
    cx.strokeStyle = "rgba(159,216,255,.45)";
    cx.lineWidth = 0.6;
    cx.beginPath();
    const n = Math.min(indices.length, 3 * 60000);
    for (let t = 0; t < n; t += 3) {
      const a = indices[t], b = indices[t + 1], d = indices[t + 2];
      cx.moveTo(uvs[2 * a] * c.width, uvs[2 * a + 1] * c.height);
      cx.lineTo(uvs[2 * b] * c.width, uvs[2 * b + 1] * c.height);
      cx.lineTo(uvs[2 * d] * c.width, uvs[2 * d + 1] * c.height);
      cx.closePath();
    }
    cx.stroke();
  }
  const leg = $("#pjAtlasLegende");
  if (leg) leg.textContent = S.E ? T("tex.pj_atlas_legende", { l: S.E.W, h: S.E.H, sorte: T("tex.pj_atlas_" + S.atlasMode) }) : T("tex.pj_atlas_vide");
}

function peindreStats() {
  const el = S.h && $("#pjStats");
  if (!el) return;
  if (!S.E) { el.textContent = ""; return; }
  const trous = C.trous(S.E);
  el.textContent = T("tex.pj_stats", { l: S.E.W, h: S.E.H, vues: S.vues, trous: ((100 * trous) / Math.max(1, S.A.n)).toFixed(1),
    coutures: S.coutures ? S.coutures.length : 0 });
}

function peindreLegende() {
  const el = $("#pjLegende");
  if (S.mode !== "vues" || !S.vues) { el.innerHTML = ""; return; }
  const ps = poses(parseInt(S.disposition, 10) || S.vues);
  el.innerHTML = ps.map((p, i) => {
    const [r, g, b] = C.couleurVue(i);
    return `<span title="${S.h.ctx.esc(T("tex.pj_vue_pose", { a: Math.round(p.azimut), e: Math.round(p.elevation), z: p.zoom }))}"><i style="background:rgb(${r},${g},${b})"></i>${i + 1}</span>`;
  }).join("");
}

function peindre() {
  if (!S.h) return;
  const m = S.h.modele(), res = S.h.resolution(), lg = langue(), f = S.h.fiche();
  for (const b of S.h.section.querySelectorAll("#pjDispos [data-dispo]")) {
    const n = +b.dataset.dispo;
    b.classList.toggle("on", n === S.dispo);
    const d = devisDisposition(n, m, res);
    b.querySelector("[data-prix]").textContent = d ? usd(d.usd, lg) : "—";
  }
  $("#pjDispoAide").textContent = T("tex.pj_dispo_" + S.dispo);
  const d = devisDisposition(S.dispo, m, res);
  $("#pjAutoTexte").textContent = d ? T("tex.pj_lancer_prix", { n: S.dispo, usd: usd(d.usd, lg) }) : T("tex.pj_lancer");
  $("#pjAuto").disabled = !f || !m || S.occupe;
  $("#pjEssai").disabled = !f || S.occupe;
  const p1 = prixImage(m, res);
  $("#pjDebruiterTexte").textContent = p1 != null ? T("tex.pj_debruiter_prix", { usd: usd(p1, lg) }) : T("tex.pj_debruiter");
  const sansAtlas = !S.E || S.occupe;
  for (const id of ["#pjToutCombler", "#pjSoigner", "#pjDebruiter"]) $(id).disabled = sansAtlas || !S.vues;
  $("#pjDebruiter").disabled = $("#pjDebruiter").disabled || !m;
  $("#pjAnnuler").disabled = sansAtlas || !S.pile || !S.pile.passe.length;
  $("#pjRetablir").disabled = sansAtlas || !S.pile || !S.pile.futur.length;
  $("#pjEnregistrer").disabled = sansAtlas || !S.modifie;
  for (const b of S.h.section.querySelectorAll("#pjOutils [data-outil]")) {
    b.classList.toggle("on", (b.dataset.outil || null) === S.outil);
    b.disabled = !!b.dataset.outil && sansAtlas;
  }
  $("#pjOutilAide").textContent = T("tex.pj_outila_" + (S.outil || "orbite"));
  for (const b of S.h.section.querySelectorAll("#pjModes [data-mode]")) { b.classList.toggle("on", b.dataset.mode === S.mode); b.disabled = !S.E; }
  for (const b of S.h.section.querySelectorAll("#pjAtlasMode [data-atlas]")) b.classList.toggle("on", b.dataset.atlas === S.atlasMode);
  S.h.section.querySelector(".tx-vue").classList.toggle("pj-pinceau", !!S.outil && !!S.E);
  peindreLegende();
}

function occuper(b) { S.occupe = b; peindre(); }

function surClic(e) {
  const b = e.target.closest("button");
  if (!b || b.disabled || !S.h) return;
  const d = b.dataset;
  if (d.dispo) { S.dispo = +d.dispo; return peindre(); }
  if (d.outil !== undefined) { S.outil = d.outil || null; return peindre(); }
  if (d.mode) { S.mode = d.mode; return rafraichir(); }
  if (d.atlas) { S.atlasMode = d.atlas; peindre(); return dessinerAtlas(); }
  if (b.id === "pjAuto") return texturerAuto();
  if (b.id === "pjEssai") return essayer();
  if (b.id === "pjDebruiter") return debruiter();
  if (b.id === "pjEnregistrer") return enregistrer();
  if (b.id === "pjAnnuler") return defaire(false);
  if (b.id === "pjRetablir") return defaire(true);
  if (b.id === "pjToutCombler" && S.E) {
    C.memoriser(S.pile, S.E, C.rectTout(S.E));
    const r = C.combler(S.E);
    marquer();
    rafraichir();
    return S.h.avis(T("tex.pj_comble", { n: r.combles }));
  }
  if (b.id === "pjSoigner" && S.E) {
    C.memoriser(S.pile, S.E, C.rectTout(S.E));
    const n = C.soigner(S.E, S.coutures || []);
    marquer();
    rafraichir();
    return S.h.avis(T("tex.pj_soigne", { n, c: (S.coutures || []).length }));
  }
}

/* l'écran 1/2 change de modèle d'image ou de résolution : les prix se repeignent */
export function repeindre() { if (S.h) peindre(); }
