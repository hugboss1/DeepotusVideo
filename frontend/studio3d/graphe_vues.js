/* t344 (29/10/2026, demande de l'utilisateur) — le graphe Meshy MONTRE ce que chaque nœud a produit, et l'aperçu
   s'agrandit sur le canevas.

   1. Vignettes : chaque nœud (image de départ, prompt, maillage, texture, topologie, squelette, animation, export,
      Établi) porte une vignette de SON résultat — l'image de départ, un INSTANTANÉ du GLB de la phase, l'image
      d'aperçu du fournisseur, ou un état vide « en attente ». PAS un contexte WebGL par nœud : un seul moteur de
      rendu hors écran fabrique des PNG, mis en cache par URL pour la vie de la page, une file à la fois.
   2. Aperçu : cliquer un nœud charge SON modèle dans l'aperçu de droite (crochet `window.__dzApercuNoeud`, lu par
      renderPreview) ; le bouton « Agrandir » (ou un double-clic sur l'aperçu) l'ouvre en grand sur le canevas avec
      le canevas partagé /lib3d/viewer.js : orbite, panoramique, zoom, vues nommées, perspective / orthographique,
      trame, Texturé / Argile / Fil de fer ; Échap ou « Revenir au graphe » le referme.

   Module À PART : studio3d.js est régénéré par la traduction L9 (scripts/i18n_l9/t344.py n'y pose que deux
   crochets : l'état exposé et l'évènement « studio3d:peint »). Textes : dictionnaire studio3dvues.json. */
"use strict";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { creerCanevas, charger, cadrer, orienter, projeter, montrerRepere } from "/lib3d/viewer.js";
import { appliquerRendu, normaliser } from "./rendu3d.js";
import { resultatNoeud, rendable } from "./graphe_vues_calc.js";

const T = (k, v) => (typeof dzT === "function" ? dzT("studio3dvues." + k, v) : k);
const $ = (s) => document.querySelector(s);
const ico = (cle) => (typeof dzIcone === "function" ? dzIcone(cle, { taille: 16, classe: "dzi--16" }) : "");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* l'état de ce module — déclaré ICI */
const V = { noeud: null, etabli: null, cache: new Map(), file: [], occupe: false, grand: null, rendu: "texture",
  vue: "libre", projection: "perspective", trame: true, urlGrand: null };

/* ── 1. les instantanés : UN moteur de rendu hors écran pour toutes les vignettes ───────────────────────────────── */

let _r = null;
function moteur() {
  if (_r) return _r;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 192;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  const scene = new THREE.Scene();
  /* les MÊMES lumières que le canevas partagé : une vignette ressemble à ce que montrera l'aperçu */
  scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 2.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.4);
  key.position.set(3, 5, 2);
  scene.add(key);
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  _r = { renderer, scene, camera, loader };
  return _r;
}

async function instantane(url) {
  const r = moteur();
  const gltf = await r.loader.loadAsync(url);
  const racine = gltf.scene;
  normaliser(racine);
  r.scene.add(racine);
  r.camera.position.set(1.35, 1.15, 2.0);
  r.camera.lookAt(0, 0.45, 0);
  r.renderer.setClearColor(0x000000, 0);
  r.renderer.render(r.scene, r.camera);
  const png = r.renderer.domElement.toDataURL("image/png");
  r.scene.remove(racine);
  racine.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    for (const m of [].concat(o.material || [])) {
      for (const k of Object.keys(m)) if (m[k] && m[k].isTexture) m[k].dispose();
      m.dispose();
    }
  });
  return png;
}

/* la vignette d'un GLB : en cache, sinon en file (un rendu à la fois) ; rend une promesse du data URL ou null */
function vignetteDe(url) {
  if (V.cache.has(url)) return V.cache.get(url);
  const p = new Promise((ok) => V.file.push({ url, ok }));
  V.cache.set(url, p);
  pomper();
  return p;
}
async function pomper() {
  if (V.occupe) return;
  V.occupe = true;
  while (V.file.length) {
    const { url, ok } = V.file.shift();
    try { ok(await instantane(url)); } catch { ok(null); V.cache.delete(url); }
  }
  V.occupe = false;
}

/* ── les vignettes dans les nœuds ───────────────────────────────────────────────────────────────────────────────── */

function cadreDe(n) {
  const el = document.getElementById(`node-${n.id}`);
  if (!el) return null;
  let v = el.querySelector(".dz-vign");
  if (!v) {
    v = document.createElement("div");
    v.className = "dz-vign";
    el.appendChild(v);
    el.classList.add("a-vign");
  }
  return v;
}

function peindre() {
  const D = window.__dzStudio3d;
  if (!D) return;
  for (const n of D.NODES) {
    const v = cadreDe(n);
    if (!v) continue;
    const r = resultatNoeud(n, D.S, V.etabli);
    const cle = JSON.stringify([r.etat, r.img, r.glb, r.texte && r.texte.slice(0, 60)]);
    v.classList.toggle("choisi", V.noeud === n.id);
    if (v.dataset.cle === cle) continue;
    v.dataset.cle = cle;
    v.dataset.etat = r.etat;
    v.title = T("etat." + r.etat);
    if (r.texte) { v.innerHTML = `<span class="dz-vign-texte">${esc(r.texte.slice(0, 60))}</span>`; continue; }
    if (r.glb && rendable(r.glb)) {
      v.innerHTML = `<span class="dz-vign-vide">${ico("dz-etat-attente")}</span>`;
      vignetteDe(r.glb).then((png) => {
        if (v.dataset.cle !== cle) return;           // le nœud a changé entre-temps
        v.innerHTML = png ? `<img alt="" src="${png}">` : (r.img ? `<img alt="" src="${esc(r.img)}">`
          : `<span class="dz-vign-vide">${ico("dz-etat-sans-apercu")}</span>`);
      });
      continue;
    }
    if (r.img) { v.innerHTML = `<img alt="" src="${esc(r.img)}">`; continue; }
    v.innerHTML = `<span class="dz-vign-vide">${ico(r.etat === "en_cours" ? "dz-etat-attente"
      : r.etat === "echec" ? "dz-etat-erreur" : r.etat === "saute" ? "dz-etat-exclu" : "dz-etat-vide")}</span>`;
  }
  const ap = $("#previewBox");
  if (ap) ap.classList.toggle("a-noeud", !!glbChoisi());
  if (V.grand) majGrand();
}

/* ── 2. l'aperçu suit le nœud cliqué ──────────────────────────────────────────────────────────────────────────────── */

function glbChoisi() {
  const D = window.__dzStudio3d;
  if (!D || !V.noeud) return null;
  const n = D.NODES.find((x) => x.id === V.noeud);
  return n ? resultatNoeud(n, D.S, V.etabli).glb : null;
}
/* lu par renderPreview (crochet de t344.py) : le modèle du nœud cliqué, sinon null — le dernier modèle, comme avant */
window.__dzApercuNoeud = glbChoisi;

function urlApercu() {
  const mv = $("#previewBox model-viewer");
  return glbChoisi() || (mv && mv.getAttribute("src")) || null;
}

/* ── l'aperçu agrandi sur le canevas ──────────────────────────────────────────────────────────────────────────────── */

function ouvrirGrand() {
  const hote = $("#canvas");
  if (!hote) return;
  if (!V.grand) {
    const el = document.createElement("section");
    el.className = "dz-grand";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", T("grand.titre"));
    el.innerHTML = `<div class="dz-grand-barre"></div><div class="dz-grand-vue"><canvas></canvas>
      <div class="dz-grand-vide"></div></div>`;
    hote.appendChild(el);
    V.grand = { el, api: creerCanevas(el.querySelector("canvas")), url: null };
  }
  V.grand.el.classList.remove("hidden");
  rendreBarre();
  majGrand(true);
}

function fermerGrand() {
  if (V.grand) V.grand.el.classList.add("hidden");
}

function rendreBarre() {
  const seg = (id, liste, actif) => `<div class="dz-seg" role="group" id="${id}">` + liste.map(([v, cle, ic]) =>
    `<button data-v="${v}" class="${v === actif ? "on" : ""}" aria-pressed="${v === actif}">${ico(ic)} ${esc(T(cle))}</button>`).join("") + `</div>`;
  const b = V.grand.el.querySelector(".dz-grand-barre");
  b.innerHTML = `<b class="dz-grand-titre">${esc(T("grand.titre"))}</b>`
    + seg("dzgRendu", [["texture", "rendu.texture", "dz-lab3d-materiau"], ["argile", "rendu.argile", "dz-lab3d-sphere"],
      ["fil", "rendu.fil", "dz-lab3d-filaire"]], V.rendu)
    + seg("dzgVue", [["libre", "vue.libre", "dz-lab3d-rotation"], ["iso", "vue.iso", "dz-lab3d-cube"],
      ["face", "vue.face", "dz-lab3d-camera"], ["profil", "vue.profil", "dz-lab3d-orienter"], ["dessus", "vue.dessus", "dz-lab3d-plan"]], V.vue)
    + seg("dzgProj", [["perspective", "proj.perspective", "dz-lab3d-camera"], ["orthographique", "proj.ortho", "dz-lab3d-plan"]], V.projection)
    + `<label class="dz-grand-case"><input type="checkbox" id="dzgTrame" ${V.trame ? "checked" : ""}> ${esc(T("grand.trame"))}</label>`
    + `<span class="dz-grand-aide">${esc(T("grand.aide"))}</span>`
    + `<button class="dz-grand-fermer" id="dzgFermer" title="${esc(T("grand.fermer_aide"))}">${ico("dz-action-retour")} ${esc(T("grand.fermer"))}</button>`;
  const api = V.grand.api;
  b.querySelectorAll("#dzgRendu button").forEach((x) => x.addEventListener("click", () => {
    V.rendu = x.dataset.v; appliquerRendu(api.racine, V.rendu); rendreBarre();
  }));
  b.querySelectorAll("#dzgVue button").forEach((x) => x.addEventListener("click", () => {
    V.vue = x.dataset.v; orienter(api, V.vue); rendreBarre();
  }));
  b.querySelectorAll("#dzgProj button").forEach((x) => x.addEventListener("click", () => {
    V.projection = x.dataset.v; projeter(api, V.projection); orienter(api, V.vue); rendreBarre();
  }));
  b.querySelector("#dzgTrame").addEventListener("change", (e) => { V.trame = e.target.checked; montrerRepere(api, V.trame); });
  b.querySelector("#dzgFermer").addEventListener("click", fermerGrand);
}

async function majGrand(force) {
  const g = V.grand;
  if (!g || g.el.classList.contains("hidden")) return;
  const url = urlApercu();
  const vide = g.el.querySelector(".dz-grand-vide");
  vide.textContent = url ? "" : T("grand.vide");
  vide.classList.toggle("hidden", !!url);
  if (!url || (url === g.url && !force)) return;
  if (url === g.url) return;
  g.url = url;
  try {
    await charger(g.api, url);
    normaliser(g.api.racine);
    appliquerRendu(g.api.racine, V.rendu);
    montrerRepere(g.api, V.trame);
    orienter(g.api, V.vue);
    cadrer(g.api);
  } catch (e) {
    vide.textContent = T("grand.illisible", { m: e.message });
    vide.classList.remove("hidden");
  }
}

/* ── branchements ───────────────────────────────────────────────────────────────────────────────────────────────── */

function brancher() {
  const graph = $("#graph");
  if (graph) {
    graph.addEventListener("click", (ev) => {
      const el = ev.target.closest(".node");
      if (!el) return;
      const id = el.id.replace(/^node-/, "");
      V.noeud = V.noeud === id ? null : id;           // re-cliquer le nœud choisi rend l'aperçu au dernier modèle
      peindre();
    });
  }
  const ap = $("#previewBox");
  if (ap) {
    const b = document.createElement("button");
    b.className = "dz-agrandir";
    b.id = "btnAgrandir";
    b.title = T("agrandir.aide");
    b.setAttribute("aria-label", T("agrandir.libelle"));
    b.innerHTML = `${ico("dz-action-ajuster-vue")}<span>${esc(T("agrandir.libelle"))}</span>`;
    b.addEventListener("click", (ev) => { ev.stopPropagation(); ouvrirGrand(); });
    ap.appendChild(b);
    ap.addEventListener("dblclick", ouvrirGrand);
  }
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && V.grand && !V.grand.el.classList.contains("hidden")) { ev.preventDefault(); fermerGrand(); }
  });
  document.addEventListener("studio3d:peint", peindre);
  fetch("/api/etabli/productions").then((r) => r.json()).then((j) => {
    const it = (j.items || []).find((x) => x.thumb);
    V.etabli = it ? it.thumb : null;
    peindre();
  }).catch(() => {});
  peindre();
}

brancher();

export { V, peindre, ouvrirGrand, fermerGrand };
