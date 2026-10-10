/* Le Plateau 3D (t127, 07/10/2026) — composer un plan en 3D, gratuitement, AVANT tout tir payant.
   Spec docs/superpowers/specs/2026-08-29-plateau-previsualisation-3d-design.md ; plan
   docs/superpowers/plans/2026-10-07-plan-plateau-3d.md. Décision du 07/10 : le canevas three.js PARTAGÉ
   (/lib3d/viewer.js), pas <model-viewer> — la scène se monte objet par objet, le GLB composé est une SORTIE.

   Ce que la page fait elle-même : afficher (proxys three, maillages servis par /api/scenes3d/maillage), lire
   l'orbite, convertir focale ↔ champ, interpoler les keyframes à la lecture (calc.js, recoupé avec le serveur).
   Ce que le SERVEUR décide : h, shot_type, mouvement, prompt, composition, captures, pont vers le plan.
   Aucun dialogue natif : les confirmations sont des boutons armés et des tableaux avant / après. */
"use strict";
import * as THREE from "three";
import { creerCanevas, montrerRepere } from "/lib3d/viewer.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { ASPECTS, EASINGS, fovDeFocale, focaleDeFov, positionCamera, orbitDeCamera, interpoler, cadreDans,
         preset, trianglesProxy } from "./calc.js";

const $ = (s) => document.querySelector(s);
/* Deepotus Glyph (G6) : une icône de la suite, décorative — le sens est porté par le bouton (libellé, title, aria-label) */
const ico = (cle, t = 16) => (typeof dzIcone === "function" ? dzIcone(cle, { taille: t, classe: "dzi--" + t }) : "");
const API = "/api/scenes3d";
const P = { scene: null, plan: null, sel: null, dims: {}, lecture: false, t: 0, captures: { debut: null, fin: null },
            dirty: false, mesh: new Map() };
const COUL_SUJET = "#d8a657";

/* ── réseau ─────────────────────────────────────────────────────────────── */
async function req(url, opt) {
  const r = await fetch(url, opt);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
  return d;
}
const send = (url, method, body) => req(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
function etat(msg, erreur) { const e = $("#etat"); e.textContent = msg || ""; e.classList.toggle("erreur", !!erreur); }
const f2 = (x) => Number(x).toFixed(2).replace(".", ",");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ── le canevas ─────────────────────────────────────────────────────────── */
const V = creerCanevas($("#canevas"));
try { montrerRepere(V, false); } catch { /* repère absent : rien à cacher */ }
V.racine = new THREE.Group();
V.scene.add(V.racine);
V.scene.add(new THREE.GridHelper(40, 40, 0x6a6f78, 0x2a2e35));   // 1 case = 1 m
V.renderer.domElement.style.background = "transparent";
const chargeur = new GLTFLoader();
chargeur.setMeshoptDecoder(MeshoptDecoder);

function caméraCourante() {
  const c = V.camera, t = V.controls.target;
  const prec = P.scene && P.scene.camera ? P.scene.camera.orbit[0] : undefined;
  return { orbit: orbitDeCamera([c.position.x, c.position.y, c.position.z], [t.x, t.y, t.z], prec), target: [t.x, t.y, t.z], fov: c.fov };
}
function poserCaméra(cam) {
  const p = positionCamera(cam.orbit, cam.target);
  V.controls.target.set(...cam.target);
  V.camera.position.set(...p);
  V.camera.fov = cam.fov;
  V.camera.updateProjectionMatrix();
  V.controls.update();
}

/* le CADRE au ratio du format : la letterbox est le noir de .scene (spec §3.1) */
function majCadre() {
  const z = $("#zone"), a = ASPECTS[P.scene ? P.scene.aspect : "16:9"];
  const { w, h } = cadreDans(z.clientWidth - 24, z.clientHeight - 24, a);
  const c = $("#cadre");
  c.style.width = `${w}px`; c.style.height = `${h}px`;
  majGuides();
}
new ResizeObserver(majCadre).observe($("#zone"));

function majGuides() {
  const g = $("#guides"), out = [];
  if ($("#gTiers").checked) for (const v of [33.333, 66.667]) out.push(`<line x1="${v}" y1="0" x2="${v}" y2="100"/><line x1="0" y1="${v}" x2="100" y2="${v}"/>`);
  if ($("#gCroix").checked) out.push('<line x1="48" y1="50" x2="52" y2="50"/><line x1="50" y1="47" x2="50" y2="53"/>');
  if ($("#gTitre").checked) out.push('<rect class="titre" x="10" y="10" width="80" height="80"/>');
  if ($("#gHorizon").checked) {
    // l'horizon : un point très loin, à la HAUTEUR de la caméra, dans la direction de visée
    const c = V.camera, dir = new THREE.Vector3();
    c.getWorldDirection(dir); dir.y = 0;
    if (dir.lengthSq() > 1e-9) {
      dir.normalize().multiplyScalar(1000);
      const p = c.position.clone().add(dir).project(c);
      const y = (1 - p.y) * 50;
      if (y >= 0 && y <= 100) out.push(`<line class="horizon" x1="0" y1="${y}" x2="100" y2="${y}"/>`);
    }
  }
  g.innerHTML = out.join("");
}
["gTiers", "gCroix", "gTitre", "gHorizon"].forEach((id) => $("#" + id).addEventListener("change", majGuides));

/* ── les instances ──────────────────────────────────────────────────────── */
function géométrie(forme, d) {
  const [w, h, p] = d;
  let g;
  if (forme === "boite") g = new THREE.BoxGeometry(w, h, p);
  else if (forme === "sphere") { g = new THREE.SphereGeometry(0.5, 24, 16); g.scale(w, h, p); }
  else if (forme === "cylindre") { g = new THREE.CylinderGeometry(0.5, 0.5, 1, 24); g.scale(w, h, p); }
  else { const r = Math.min(w, p) / 2; g = new THREE.CapsuleGeometry(r, Math.max(0.001, h - 2 * r), 8, 24); g.scale(w / (2 * r), 1, p / (2 * r)); }
  g.translate(0, h / 2, 0);                         // posée par le pied, comme au serveur
  return g;
}
function appliquerTransform(obj, tr) {
  obj.position.set(...tr.pos);
  obj.rotation.set(...tr.rot.map((a) => a * Math.PI / 180), "XYZ");
  obj.scale.setScalar(tr.scale);
}
async function objetDe(inst) {
  const coul = inst.role === "sujet" ? COUL_SUJET : inst.couleur;
  const mat = new THREE.MeshStandardMaterial({ color: coul, roughness: 0.8, metalness: 0 });
  let o;
  if (inst.source.kind === "proxy") o = new THREE.Mesh(géométrie(inst.source.forme, inst.dims), mat);
  else {
    const q = `job=${encodeURIComponent(inst.source.job)}&file=${encodeURIComponent(inst.source.file)}`;
    const niv = inst.niveau === "plein" ? "plein" : "allege";
    const [gltf, sd] = await Promise.all([chargeur.loadAsync(`${API}/maillage?${q}&niveau=${niv}`), req(`${API}/source-dims?${q}`)]);
    const g = new THREE.Group(), m = gltf.scene;
    m.position.set(...sd.offset);                   // recentré par le pied, comme au serveur
    g.add(m);
    o = g;
    P.dims[inst.id] = sd;
  }
  o.userData.id = inst.id;
  appliquerTransform(o, inst.transform);
  return o;
}
async function monterScène() {
  for (const o of V.racine.children.slice()) V.racine.remove(o);
  P.mesh.clear();
  for (const inst of P.scene.instances) {
    try { const o = await objetDe(inst); V.racine.add(o); P.mesh.set(inst.id, o); }
    catch (e) { etat(`« ${inst.nom} » : ${e.message}`, true); }
  }
  majTris();
}
async function remplacerObjet(inst) {
  const ancien = P.mesh.get(inst.id);
  if (ancien) V.racine.remove(ancien);
  try { const o = await objetDe(inst); V.racine.add(o); P.mesh.set(inst.id, o); } catch (e) { etat(e.message, true); }
  majTris();
}
function majTris() {
  let n = 0;
  for (const i of P.scene.instances) {
    if (i.source.kind === "proxy") n += trianglesProxy(i.source.forme);
    else n += i.niveau === "plein" ? (P.dims[i.id] ? P.dims[i.id].tris : 0) : Math.min(2500, P.dims[i.id] ? P.dims[i.id].tris : 2500);
  }
  $("#tris").textContent = `${n.toLocaleString("fr-FR")} triangles dans la scène`;
}

function listeInstances() {
  $("#instances").innerHTML = P.scene.instances.map((i) => `<li data-id="${esc(i.id)}" aria-selected="${i.id === P.sel}">
    <span class="pastille" style="background:${i.role === "sujet" ? COUL_SUJET : esc(i.couleur)}"></span>${esc(i.nom)}
    <span class="role ${i.role}">${i.role}${i.source.kind === "proxy" ? "" : " · " + i.niveau}</span></li>`).join("");
  $("#instances").querySelectorAll("li").forEach((li) => li.addEventListener("click", () => { P.sel = li.dataset.id; listeInstances(); fiche(); }));
}
function fiche() {
  const i = P.scene.instances.find((x) => x.id === P.sel), f = $("#fiche");
  if (!i) { f.innerHTML = ""; return; }
  const num = (k, j, v) => `<input class="champ num" type="number" step="0.05" data-k="${k}" data-j="${j}" value="${Number(v).toFixed(3)}">`;
  f.innerHTML = `
    <div class="ligne"><input class="champ" data-k="nom" value="${esc(i.nom)}" aria-label="Nom de l'instance"></div>
    <div class="ligne"><span>Rôle</span><select class="champ" data-k="role">${["sujet", "decor", "repere"].map((r) => `<option ${r === i.role ? "selected" : ""}>${r}</option>`).join("")}</select>
      ${i.source.kind === "proxy" ? "" : `<select class="champ" data-k="niveau" title="allégé : 2 500 triangles (gltfpack) ; plein : le maillage tel quel">${["allege", "plein"].map((n) => `<option ${n === i.niveau ? "selected" : ""}>${n}</option>`).join("")}</select>`}</div>
    <div class="xyz"><span>pos m</span>${[0, 1, 2].map((j) => num("pos", j, i.transform.pos[j])).join("")}</div>
    <div class="xyz"><span>rot °</span>${[0, 1, 2].map((j) => num("rot", j, i.transform.rot[j])).join("")}</div>
    <div class="xyz"><span>échelle</span>${num("scale", 0, i.transform.scale)}</div>
    ${i.source.kind === "proxy" ? `<div class="xyz"><span>l h p</span>${[0, 1, 2].map((j) => num("dims", j, i.dims[j])).join("")}</div>`
      : `<div class="sous">${i.dims ? i.dims.map(f2).join(" × ") + " m mesurés" : "dims mesurées à la pose"}</div>`}
    <div class="ligne"><button class="btn" id="btnDup">Dupliquer</button><button class="btn" id="btnSuppr" title="Retirer l'instance (un second clic confirme)">Retirer</button></div>`;
  f.querySelectorAll("[data-k]").forEach((el) => el.addEventListener("change", () => champ(i, el)));
  $("#btnDup").addEventListener("click", () => dupliquer(i));
  const sup = $("#btnSuppr");
  sup.addEventListener("click", () => {
    if (sup.dataset.arm !== "1") { sup.dataset.arm = "1"; sup.textContent = "Retirer ?"; setTimeout(() => { sup.dataset.arm = ""; sup.textContent = "Retirer"; }, 4000); return; }
    P.scene.instances = P.scene.instances.filter((x) => x.id !== i.id);
    const o = P.mesh.get(i.id); if (o) V.racine.remove(o);
    P.sel = null; listeInstances(); fiche(); majTris(); sauver();
  });
}
async function champ(i, el) {
  const k = el.dataset.k, j = Number(el.dataset.j);
  if (k === "nom") i.nom = el.value.trim() || i.nom;
  else if (k === "role") {
    if (el.value === "sujet") for (const x of P.scene.instances) if (x.role === "sujet") x.role = "decor";   // un seul sujet
    i.role = el.value;
  } else if (k === "niveau") { i.niveau = el.value; await remplacerObjet(i); }
  else if (k === "scale") i.transform.scale = Math.max(0.01, Number(el.value) || 1);
  else if (k === "dims") { i.dims[j] = Math.max(0.01, Number(el.value) || 0.01); await remplacerObjet(i); }
  else i.transform[k][j] = Number(el.value) || 0;
  const o = P.mesh.get(i.id);
  if (o) appliquerTransform(o, i.transform);
  if (k === "role") await monterScène();
  listeInstances(); sauver(); mesurerBientôt();
}
function idLibre(base) { let n = 1, id = base; while (P.scene.instances.some((x) => x.id === id)) id = `${base}_${++n}`; return id; }
async function ajouter(inst) {
  P.scene.instances.push(inst);
  P.sel = inst.id;
  await remplacerObjet(inst);
  listeInstances(); fiche(); sauver(); mesurerBientôt();
}
function dupliquer(i) {
  const c = JSON.parse(JSON.stringify(i));
  c.id = idLibre(i.id); c.nom = i.nom + " (copie)"; c.role = c.role === "sujet" ? "decor" : c.role;
  c.transform.pos[0] += 1;
  ajouter(c);
}
const DIMS = { boite: [1, 1, 1], capsule: [0.5, 1.7, 0.4], cylindre: [0.5, 2, 0.5], sphere: [0.6, 0.6, 0.6] };
document.querySelectorAll("[data-forme]").forEach((b) => b.addEventListener("click", () => {
  const f = b.dataset.forme;
  ajouter({ id: idLibre(f), nom: b.textContent.trim(), source: { kind: "proxy", forme: f }, niveau: "proxy",
            dims: DIMS[f].slice(), transform: { pos: [0, 0, 0], rot: [0, 0, 0], scale: 1 }, couleur: "#8a8f98",
            role: P.scene.instances.some((x) => x.role === "sujet") ? "decor" : "sujet" });
}));
async function chargerSources() {
  try {
    const d = await req(`${API}/sources`);
    const opts = [...d.entites.map((e) => ({ v: `${e.job}|${e.file}|${e.id}`, l: `◆ ${e.nom} (bible)` })),
      ...d.jobs.flatMap((j) => j.versions.map((v) => ({ v: `${j.job}|${v.file}|`, l: `${j.nom} · ${v.libelle || v.file}${v.triangles ? " · " + v.triangles + " tris" : ""}` })))];
    $("#selMaillage").innerHTML = `<option value="">maillage… (${opts.length})</option>` + opts.map((o) => `<option value="${esc(o.v)}">${esc(o.l)}</option>`).join("");
  } catch (e) { etat(`maillages : ${e.message}`, true); }
}
$("#btnMaillage").addEventListener("click", async () => {
  const v = $("#selMaillage").value; if (!v) return;
  const [job, file, ent] = v.split("|");
  try {
    const sd = await req(`${API}/source-dims?job=${encodeURIComponent(job)}&file=${encodeURIComponent(file)}`);
    const nom = $("#selMaillage").selectedOptions[0].textContent.replace(/^◆ /, "").split(" · ")[0];
    await ajouter({ id: idLibre(job), nom, source: { kind: "assets3d", job, file }, niveau: "allege", dims: sd.dims,
                    entity_id: ent || null, transform: { pos: [0, 0, 0], rot: [0, 0, 0], scale: 1 }, couleur: "#8a8f98",
                    role: P.scene.instances.some((x) => x.role === "sujet") ? "decor" : "sujet" });
  } catch (e) { etat(e.message, true); }
});

/* ── sauvegarde (débrayée pendant la lecture) ───────────────────────────── */
let tSave = 0;
function sauver() {
  P.dirty = true;
  clearTimeout(tSave);
  tSave = setTimeout(async () => {
    try {
      const d = await send(`${API}/${P.scene.id}`, "PUT", { nom: P.scene.nom, aspect: P.scene.aspect, focale_mm: P.scene.focale_mm,
        instances: P.scene.instances, camera: caméraCourante(), keyframes: P.scene.keyframes });
      P.scene.camera = d.camera; P.dirty = false; etat("enregistré");
    } catch (e) { etat(`enregistrement : ${e.message}`, true); }
  }, 700);
}

/* ── cadre : focale, mesures ────────────────────────────────────────────── */
function majFocale(fromInput) {
  if (fromInput) {
    const f = Math.min(200, Math.max(14, Number($("#focale").value) || 35));
    P.scene.focale_mm = f;
    V.camera.fov = fovDeFocale(f, P.scene.capteur_mm); V.camera.updateProjectionMatrix();
  }
  $("#focale").value = Math.round(focaleDeFov(V.camera.fov, P.scene.capteur_mm));
  $("#fov").textContent = `${f2(V.camera.fov)}° vertical`;
}
$("#focale").addEventListener("change", () => { majFocale(true); sauver(); mesurerBientôt(); });
$("#aspect").addEventListener("change", () => { P.scene.aspect = $("#aspect").value; majCadre(); sauver(); mesurerBientôt(); });
$("#nomScene").addEventListener("change", () => { P.scene.nom = $("#nomScene").value.trim() || "scène"; sauver(); });

let tMes = 0;
function mesurerBientôt() { clearTimeout(tMes); tMes = setTimeout(mesurer, 180); }
function sceneAffichée() { return { instances: P.scene.instances, aspect: P.scene.aspect }; }
async function mesurer() {
  if (!P.scene) return;
  try {
    const m = await send(`${API}/${P.scene.id}/mesure`, "POST", { camera: caméraCourante(), scene: sceneAffichée() });
    $("#lecture").innerHTML = `<span>distance <b>${f2(m.distance_m)} m</b></span><span>${Math.round(m.focale_mm)} mm · ${f2(m.fov)}°</span>
      <span>h <b>${f2(m.h)}</b></span><span>plan <b>${esc(m.shot_type)}</b></span>${m.dans_cadre ? "" : '<span class="ko">sujet hors cadre</span>'}`;
    $("#mesure").innerHTML = `<div><span class="k">mesuré</span> ${esc(m.shot_type)} (h = ${f2(m.h)})</div>
      <div class="k">seuils : ${Object.entries(m.seuils).map(([k, v]) => `${k} &lt; ${String(v).replace(".", ",")}`).join(" · ")}</div>
      ${m.plan ? `<div class="${m.plan.ecart ? "ecart" : ""}">plan écrit : ${esc(m.plan.shot_type)}${m.plan.ecart ? ` — le cadre donne ${esc(m.shot_type)}` : " " + ico("dz-etat-succes")}</div>` : ""}`;
  } catch (e) { $("#lecture").innerHTML = `<span class="ko">${esc(e.message)}</span>`; }
}
V.controls.addEventListener("change", () => { majFocale(false); majGuides(); if (!P.lecture) { mesurerBientôt(); sauverCaméraBientôt(); } });
let tCam = 0;
function sauverCaméraBientôt() { clearTimeout(tCam); tCam = setTimeout(sauver, 1200); }

/* ── mouvement ──────────────────────────────────────────────────────────── */
function durée() { return P.plan ? P.plan.duration_s : Math.max(4, ...P.scene.keyframes.map((k) => k.t)); }
function majTimeline() {
  const d = durée(), tete = $("#tete");
  tete.max = String(d);
  $("#kfs").innerHTML = P.scene.keyframes.map((k, i) => `<button class="losange" style="left:${(k.t / d) * 100}%" data-i="${i}" title="keyframe ${i + 1} — ${f2(k.t)} s"></button>`).join("");
  $("#kfs").querySelectorAll(".losange").forEach((b) => b.addEventListener("click", () => allerA(P.scene.keyframes[+b.dataset.i].t)));
  $("#listeKf").innerHTML = P.scene.keyframes.map((k, i) => `<li><span class="t">${f2(k.t)} s</span>
    <span class="sous">r ${f2(k.orbit[2])} · θ ${Math.round(k.orbit[0])}° · φ ${Math.round(k.orbit[1])}°</span>
    <select data-i="${i}" aria-label="easing du segment">${EASINGS.map((e) => `<option ${e === k.easing ? "selected" : ""}>${e}</option>`).join("")}</select>
    <button class="btn" data-x="${i}" title="Retirer ce keyframe" aria-label="Retirer ce keyframe">${ico("dz-media-image-cle-retirer")}</button></li>`).join("");
  $("#listeKf").querySelectorAll("select").forEach((s) => s.addEventListener("change", () => { P.scene.keyframes[+s.dataset.i].easing = s.value; sauver(); analyser(); }));
  $("#listeKf").querySelectorAll("[data-x]").forEach((b) => b.addEventListener("click", () => { P.scene.keyframes.splice(+b.dataset.x, 1); majTimeline(); sauver(); analyser(); }));
}
function allerA(t) {
  P.t = Math.max(0, Math.min(durée(), t));
  $("#tete").value = String(P.t);
  $("#tc").textContent = `${f2(P.t)} s`;
  if (P.scene.keyframes.length) { poserCaméra(interpoler(P.scene.keyframes, P.t)); majFocale(false); majGuides(); }
}
$("#tete").addEventListener("input", (e) => allerA(Number(e.target.value)));
function poserKeyframe() {
  const cam = caméraCourante(), t = Number(P.t.toFixed(2));
  const k = { t, orbit: cam.orbit.map((v) => Number(v.toFixed(4))), target: cam.target.map((v) => Number(v.toFixed(4))), fov: Number(cam.fov.toFixed(4)), easing: "ease-in-out" };
  P.scene.keyframes = P.scene.keyframes.filter((x) => Math.abs(x.t - t) > 1e-6).concat([k]).sort((a, b) => a.t - b.t);
  majTimeline(); sauver(); analyser();
}
$("#btnKf").addEventListener("click", poserKeyframe);
$("#preset").addEventListener("change", (e) => {
  if (!e.target.value) return;
  P.scene.keyframes = preset(e.target.value, caméraCourante(), durée());
  e.target.value = ""; majTimeline(); allerA(0); sauver(); analyser();
});
let rafLecture = 0, t0 = 0;
function basculerLecture() {
  if (P.scene.keyframes.length < 2) { etat("deux keyframes au moins pour lire un mouvement", true); return; }
  P.lecture = !P.lecture;
  $("#btnPlay").innerHTML = ico(P.lecture ? "dz-media-pause" : "dz-media-lecture");
  if (P.lecture) {
    t0 = performance.now() - P.t * 1000;
    const pas = (now) => {
      if (!P.lecture) return;
      allerA(((now - t0) / 1000) % durée());
      rafLecture = requestAnimationFrame(pas);
    };
    rafLecture = requestAnimationFrame(pas);
  } else { cancelAnimationFrame(rafLecture); mesurerBientôt(); }
}
$("#btnPlay").addEventListener("click", basculerLecture);
document.addEventListener("keydown", (e) => {
  if (/INPUT|SELECT|TEXTAREA/.test((e.target && e.target.tagName) || "")) return;
  if (e.code === "Space") { e.preventDefault(); basculerLecture(); }
  if (e.key === "k" || e.key === "K") poserKeyframe();
});
let dernierMvt = null;
async function analyser() {
  if (!P.scene.keyframes.length) { $("#mouvement").innerHTML = ""; dernierMvt = null; return; }
  try {
    const m = await send(`${API}/${P.scene.id}/mouvement`, "POST", { keyframes: P.scene.keyframes, scene: sceneAffichée() });
    dernierMvt = m;
    $("#mouvement").innerHTML = `<div><span class="k">mesuré</span> ${esc(m.camera_move)}</div>
      ${m.attributs.length ? `<div class="k">attribut proposé : ${m.attributs.map(esc).join(", ")}</div>` : ""}
      ${m.plan ? `<div class="${m.plan.ecart ? "ecart" : ""}">plan écrit : ${esc(m.plan.camera_move)}${m.plan.ecart ? " — écart" : " " + ico("dz-etat-succes")}</div>` : ""}
      <div class="prompt">${esc(m.motion_prompt)}</div>${m.avertissements.map((a) => `<div class="avert">${ico("dz-etat-avertissement")} ${esc(a)}</div>`).join("")}`;
  } catch (e) { $("#mouvement").innerHTML = `<div class="avert">${esc(e.message)}</div>`; }
}

/* ── sorties ────────────────────────────────────────────────────────────── */
$("#btnCompose").addEventListener("click", async () => {
  const b = $("#btnCompose"); b.disabled = true; etat("composition…");
  try {
    clearTimeout(tSave);
    await send(`${API}/${P.scene.id}`, "PUT", { instances: P.scene.instances, keyframes: P.scene.keyframes, camera: caméraCourante() });
    const d = await send(`${API}/${P.scene.id}/compose`, "POST", {});
    const l = $("#lienGlb"); l.href = `${API}/${P.scene.id}/scene.glb?v=${d.version}`; l.setAttribute("aria-disabled", "false");
    etat(`GLB v${d.version} : ${d.rapport.tris_total.toLocaleString("fr-FR")} triangles, ${Math.round(d.bytes / 1024)} Ko`);
  } catch (e) { etat(`composition : ${e.message}`, true); }
  b.disabled = false;
});
/* La capture se rend à une taille FIXE (grand côté 1 280 px, au ratio du cadre) puis le canevas reprend la sienne :
   à la taille d'écran, une image de début pour un modèle vidéo serait trop petite — et MESURÉ à l'écran (07/10), un
   onglet masqué n'exécute pas la boucle rAF du canevas, qui n'a donc jamais pris sa taille : la capture faisait 1 × 1. */
const CAPTURE_PX = 1280;
function rendreA(w, h) {
  const r = V.renderer, c = V.camera, pr = r.getPixelRatio();
  r.setPixelRatio(1); r.setSize(w, h, false);
  c.aspect = w / h; c.updateProjectionMatrix();
  r.render(V.scene, c);                             // rendu forcé : le tampon est lu dans la même tâche
  const url = r.domElement.toDataURL("image/png");
  const el = $("#cadre");
  r.setPixelRatio(pr); r.setSize(Math.max(1, el.clientWidth), Math.max(1, el.clientHeight), false);
  c.aspect = Math.max(1, el.clientWidth) / Math.max(1, el.clientHeight); c.updateProjectionMatrix();
  return url;
}
async function capturer(quand, t) {
  allerA(t);
  const a = ASPECTS[P.scene.aspect];
  const w = a >= 1 ? CAPTURE_PX : Math.round(CAPTURE_PX * a), h = a >= 1 ? Math.round(CAPTURE_PX / a) : CAPTURE_PX;
  const b64 = rendreA(w, h);
  const d = await send(`${API}/${P.scene.id}/capture`, "POST", { quand, image_b64: b64 });
  P.captures[quand] = d.filename;
  return d.filename;
}
$("#btnCapture").addEventListener("click", async () => {
  const ks = P.scene.keyframes;
  if (!ks.length) { etat("posez au moins un keyframe : la capture se fait au premier et au dernier", true); return; }
  if (P.lecture) basculerLecture();
  try {
    const a = await capturer("debut", ks[0].t), z = await capturer("fin", ks[ks.length - 1].t);
    $("#captures").innerHTML = `<div class="k">début</div><img src="/api/images/${encodeURIComponent(a)}" alt="cadre de début">
      <div class="k">fin</div><img src="/api/images/${encodeURIComponent(z)}" alt="cadre de fin">`;
    etat("cadres capturés dans la Bibliothèque (Plateau 3D)");
  } catch (e) { etat(`capture : ${e.message}`, true); }
});
/* Le type de plan proposé est celui du cadrage d'OUVERTURE (premier keyframe) : un travelling avant qui finit en très
   gros plan reste, pour le storyboard, le plan qu'il ouvre — MESURÉ à l'écran (07/10) : lu sur la caméra courante,
   la proposition prenait le cadre de FIN dès qu'une capture venait d'y amener la caméra. Sans keyframe : le cadre
   courant. */
async function propositions() {
  const ap = {}, ks = P.scene.keyframes;
  const cam = ks.length ? interpoler(ks, ks[0].t) : caméraCourante();
  try {
    const m = await send(`${API}/${P.scene.id}/mesure`, "POST", { camera: cam, scene: sceneAffichée() });
    ap.shot_type = m.shot_type;
  } catch { /* sans mesure, pas de proposition de type */ }
  if (dernierMvt) {
    if (dernierMvt.camera_move) ap.camera_move = dernierMvt.camera_move;
    if (dernierMvt.motion_prompt) ap.motion_prompt = dernierMvt.motion_prompt;
  }
  if (P.captures.debut) ap.keyframe_image = P.captures.debut;
  if (P.captures.fin) ap.keyframe_end = P.captures.fin;
  return ap;
}
$("#btnPlan").addEventListener("click", async () => {
  const z = $("#versPlan");
  if (!P.plan) { z.innerHTML = `<div class="avert">Cette scène n'est liée à aucun plan : ouvrez-la depuis le storyboard (${ico("dz-nav-plateau")}).</div>`; return; }
  const ap = await propositions();
  if (!Object.keys(ap).length) { z.innerHTML = `<div class="avert">Rien à proposer : mesurez, posez des keyframes ou capturez d'abord.</div>`; return; }
  try {
    const d = await send(`${API}/${P.scene.id}/vers-plan`, "POST", { appliquer: ap });
    z.innerHTML = `<div class="k">${P.scene.keyframes.length ? "type de plan mesuré au premier keyframe (le cadrage d'ouverture)" : "type de plan mesuré sur le cadre courant"}</div>
      <table>${Object.keys(ap).map((k) => `<tr class="${d.change.includes(k) ? "change" : ""}"><td>${k}</td><td>${esc(d.avant[k] ?? "—")}</td><td>${esc(d.apres[k])}</td></tr>`).join("")}</table>
      ${d.change.length ? `<button class="btn primaire" id="btnConfirmer">Écrire ${d.change.length} champ${d.change.length > 1 ? "s" : ""} dans le plan</button>` : `<div class="k">le plan porte déjà ces valeurs</div>`}`;
    const c = $("#btnConfirmer");
    if (c) c.addEventListener("click", async () => {
      try {
        const r = await send(`${API}/${P.scene.id}/vers-plan`, "POST", { appliquer: ap, confirmer: true });
        z.innerHTML = `<div>Plan mis à jour : ${r.change.join(", ")}.</div>`;
        Object.assign(P.plan, Object.fromEntries(r.change.map((k) => [k, r.apres[k]])));
        majChipPlan(); mesurer(); analyser();
      } catch (e) { z.innerHTML = `<div class="avert">${esc(e.message)}</div>`; }
    });
  } catch (e) { z.innerHTML = `<div class="avert">${esc(e.message)}</div>`; }
});

function majChipPlan() {
  $("#chipPlan").textContent = P.plan ? `plan ${P.plan.idx + 1} · ${P.plan.shot_type} · ${f2(P.plan.duration_s)} s` : "aucun plan lié";
}

/* ── ouverture : ?scene=<id>, ?shot=<id> (la scène du plan, créée au besoin), ou une scène neuve ─────────── */
async function ouvrir() {
  const q = new URLSearchParams(location.search);
  let sid = q.get("scene");
  const shot = q.get("shot");
  try {
    if (!sid && shot) {
      const l = await req(`${API}?shot_id=${encodeURIComponent(shot)}`);
      sid = l.scenes.length ? l.scenes[0].id : (await send(API, "POST", { shot_id: shot })).id;
    }
    if (!sid) sid = (await send(API, "POST", {})).id;
    if (q.get("scene") !== sid) history.replaceState(null, "", `?scene=${sid}`);
    P.scene = await req(`${API}/${sid}`);
    P.plan = P.scene.plan || null;
  } catch (e) { etat(`ouverture : ${e.message}`, true); return; }
  $("#nomScene").value = P.scene.nom;
  $("#aspect").value = P.scene.aspect;
  majChipPlan();
  if (P.scene.chapter_id) $("#lienRetour").href = `/atelier/?chapter=${encodeURIComponent(P.scene.chapter_id)}`;
  poserCaméra(P.scene.camera || { orbit: [0, 90, 6], target: [0, 0.85, 0], fov: fovDeFocale(P.scene.focale_mm, P.scene.capteur_mm) });
  majFocale(false); majCadre();
  P.sel = (P.scene.instances.find((i) => i.role === "sujet") || {}).id || null;
  await monterScène();
  listeInstances(); fiche(); majTimeline(); allerA(0);
  mesurer(); analyser(); chargerSources();
  etat("prêt");
}
ouvrir();
window.__plateau = P;   // inspection (bancs d'écran, preuve) — lecture seule par convention
