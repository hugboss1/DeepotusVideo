/* t400 (31/10/2026) — écran EXPORTER du 3D Studio : tout ce qui sort de la version ouverte, en local et sans dépense.

   Relevé de Sorceress (Animate › Export) : FILE NAME, collection de clips, GAME ENGINE (« Skeletal Mesh Only », « Pose »,
   « Animation » en .glb) et WEB / THREE.JS (paquet .zip avec runtime et AGENT_INSTRUCTIONS.md). Chez nous :
     gauche  = ce qui part : la version, le nom du fichier, les clips du GLB (cochés pour l'animation, un choisi pour
               la pose), et les exports déjà écrits pour ce modèle ;
     centre  = la version ouverte dans le viewport (/lib3d/viewer.js + rendu3d.js, comme Préparer), clip rejouable ;
     droite  = MOTEUR DE JEU (GLB ×3, FBX par Blender, Godot .tscn avec hitboxes, Unreal / Unity / Blender de l'Établi),
               WEB / THREE.JS, OPTIMISATION (LOD, conventions de textures), IMPRESSION 3D, FORMATS locaux, BIBLIOTHÈQUE.
   Chaque action rend un lien de téléchargement dans la liste « Fichiers prêts ». Les routes réutilisées restent celles
   de l'Établi, de l'Atelier fal et de l'impression ; les seules neuves sont /api/studio3d/exporter/*. Le calcul (sections,
   disponibilités, hitboxes par défaut, noms) vit dans exporter_calc.js. */
"use strict";
import * as THREE from "three";
import { creerCanevas, charger, vider } from "/lib3d/viewer.js";
import { appliquerRendu } from "../rendu3d.js";
import { nb, langue } from "./coque_calc.js";
import { T, SECTIONS, CIBLES_ETABLI, USAGES_LOD, NOMMAGES, nomExport, nomSur, hitboxesParDefaut, disponibilite,
  nomDeReponse, octets, formatsLocaux, corpsGlb } from "./exporter_calc.js";

const X = { s: null, ctx: null, fiche: null, etat: null, vue: null, rendu: "texture", nom: "", coches: new Set(),
  clipPose: null, capacites: null, mixer: null, horloge: null, boucle: 0, occupe: false, prets: [], dernierGlb: null,
  usage: "pc", nommage: "standard" };

const enc = encodeURIComponent;
const $ = (s) => X.s.querySelector(s);

export async function monter(section, ctx) {
  X.s = section;
  X.ctx = ctx;
  const { esc, ico } = ctx;
  section.innerHTML = `<div class="ec-trois ex-ecran">
    <aside class="ec-gauche">
      <div class="ec-label">${esc(T("exp.titre"))}</div>
      <div class="ec-label">${esc(T("exp.version"))}</div>
      <div class="ec-versions" id="exVersions"></div>
      <label class="ec-champ">${esc(T("exp.nom_fichier"))}
        <input type="text" id="exNom" maxlength="64" spellcheck="false" autocomplete="off"></label>
      <div class="ec-note" id="exApercuNom"></div>
      <div class="ec-label">${esc(T("exp.clips"))}</div>
      <div class="ex-clips" id="exClips"></div>
      <div class="ec-note">${esc(T("exp.clips_aide"))}</div>
      <div class="ec-label">${esc(T("exp.deja"))}</div>
      <div class="ex-deja" id="exDeja"></div>
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue">
        <span class="ec-mesure" id="exMesure"></span>
        <div class="ec-segments" id="exRendu">${["texture", "argile", "fil"].map((r) =>
          `<button data-rendu="${r}">${esc(T("rendu." + r))}</button>`).join("")}</div>
      </div>
      <div class="ec-vues"><figure class="ec-vue"><canvas id="exCanevas"></canvas><figcaption id="exCap"></figcaption></figure></div>
      <div class="ex-prets">
        <div class="ec-label">${esc(T("exp.prets"))}</div>
        <div class="ec-avis" id="exAvis" role="status" aria-live="polite"></div>
        <ul class="ex-liste" id="exPrets"></ul>
      </div>
    </main>
    <aside class="ec-droite" id="exDroite"></aside>
  </div>`;
  X.vue = creerCanevas($("#exCanevas"));
  $("#exRendu").addEventListener("click", (e) => {
    const b = e.target.closest("[data-rendu]");
    if (!b) return;
    X.rendu = b.dataset.rendu;
    if (X.vue.racine) appliquerRendu(X.vue.racine, X.rendu);
    peindreRendu();
  });
  $("#exVersions").addEventListener("click", (e) => {
    const b = e.target.closest("[data-version]");
    if (b && X.fiche) ctx.ouvrir(X.fiche.job, +b.dataset.version, "exporter");
  });
  $("#exNom").addEventListener("input", (e) => { X.nom = e.target.value; peindreNom(); });
  $("#exClips").addEventListener("change", (e) => {
    const c = e.target.closest("[data-coche]");
    if (c) { c.checked ? X.coches.add(c.dataset.coche) : X.coches.delete(c.dataset.coche); return; }
    const p = e.target.closest("[data-pose]");
    if (p) X.clipPose = p.dataset.pose;
  });
  $("#exClips").addEventListener("click", (e) => {
    const b = e.target.closest("[data-jouer]");
    if (b) jouer(b.dataset.jouer);
  });
  $("#exDroite").addEventListener("click", (e) => {
    const b = e.target.closest("[data-action]");
    if (b && !b.disabled) agir(b.dataset.action, b.dataset.arg || null);
  });
  $("#exDroite").addEventListener("change", (e) => {
    if (e.target.id === "exUsage") X.usage = e.target.value;
    if (e.target.id === "exNommage") X.nommage = e.target.value;
  });
  peindreDroite();
}

export async function ouvrir(fiche) {
  if (!X.s) return;
  const autre = !X.fiche || !fiche || X.fiche.job !== fiche.job;
  X.fiche = fiche;
  X.etat = null;
  if (autre) { X.nom = ""; X.prets = []; X.dernierGlb = null; }
  arreter();
  peindre();
  if (!fiche) { vider(X.vue); return; }
  try {
    X.etat = await X.ctx.jget(`/api/studio3d/exporter/${enc(fiche.job)}?version=${fiche.version}`);
    if (!X.capacites) X.capacites = await X.ctx.jget(`/api/assets/3d/${enc(fiche.job)}/convert`).catch(() => null);
  } catch (e) {
    avis(T("exp.erreur", { m: e.message }));
  }
  const noms = new Set(((X.etat && X.etat.clips) || []).map((c) => c.nom));
  X.coches = new Set([...X.coches].filter((n) => noms.has(n)));
  if (!noms.has(X.clipPose)) X.clipPose = noms.size ? [...noms][0] : null;
  peindre();
  try {
    const r = await charger(X.vue, fiche.url);
    appliquerRendu(X.vue.racine, X.rendu);
    $("#exMesure").textContent = T("exp.mesure", { n: nb(r.tris) });
  } catch { $("#exMesure").textContent = ""; }
}

export function montre() { peindreRendu(); }

/* ── peinture ─────────────────────────────────────────────────────────── */
function peindre() {
  const { esc } = X.ctx;
  const f = X.fiche;
  $("#exVersions").innerHTML = f ? (f.versions || []).map((v) =>
    `<button class="ec-version ${v.version === f.version ? "on" : ""}" data-version="${v.version}">v${v.version}`
    + `<span>${esc(v.triangles != null ? T("bandeau.triangles", { n: nb(v.triangles) }) : v.libelle || "")}</span></button>`).join("") : "";
  $("#exNom").value = X.nom;
  $("#exNom").placeholder = (X.etat && X.etat.nom_fichier) || (f ? nomSur(f.nom, f.job) : "");
  $("#exCap").textContent = f ? T("exp.cap", { nom: f.nom || f.job, v: f.version }) : T("bandeau.vide");
  peindreNom();
  peindreClips();
  peindreDeja();
  peindreDroite();
  peindrePrets();
  peindreRendu();
}

function peindreRendu() {
  for (const b of X.s.querySelectorAll("#exRendu [data-rendu]")) b.classList.toggle("on", b.dataset.rendu === X.rendu);
}

function peindreNom() {
  const f = X.fiche;
  $("#exApercuNom").textContent = f ? T("exp.apercu_nom", { f: nomExport(X.nom, f.nom || f.job, f.version, "maillage") }) : "";
}

function peindreClips() {
  const { esc, ico } = X.ctx;
  const clips = (X.etat && X.etat.clips) || [];
  if (!clips.length) {
    $("#exClips").innerHTML = `<div class="ec-note">${esc(X.etat ? T("exp.sans_clip") : T("exp.chargement"))}</div>`;
    return;
  }
  $("#exClips").innerHTML = clips.map((c) => `<div class="ex-clip">
      <input type="checkbox" data-coche="${esc(c.nom)}" ${X.coches.has(c.nom) ? "checked" : ""} aria-label="${esc(T("exp.cocher", { c: c.nom }))}">
      <span class="ex-clip-nom" title="${esc(c.nom)}">${esc(c.nom)}</span>
      <span class="ex-clip-duree">${esc(T("exp.duree", { s: (Math.round(c.duree * 100) / 100).toLocaleString(langue()) }))}</span>
      <label class="ex-clip-pose" title="${esc(T("exp.pose_aide"))}"><input type="radio" name="exPose" data-pose="${esc(c.nom)}"
        ${X.clipPose === c.nom ? "checked" : ""}> ${esc(T("exp.pose"))}</label>
      <button class="ex-jouer" data-jouer="${esc(c.nom)}" title="${esc(T("exp.jouer"))}" aria-label="${esc(T("exp.jouer"))}">${ico("dz-media-lecture")}</button>
    </div>`).join("");
}

function peindreDeja() {
  const { esc } = X.ctx;
  const d = (X.etat && X.etat.exports) || [];
  $("#exDeja").innerHTML = d.length
    ? d.map((x) => `<a class="ex-fichier" href="${esc(x.url)}" download>${esc(x.fichier)}</a>`).join("")
    : `<div class="ec-note">${esc(T("exp.aucun"))}</div>`;
}

function bouton(action, libelle, icone, arg) {
  const { esc, ico } = X.ctx;
  const d = disponibilite(action, X.etat);
  const titre = d.ok ? T("exp.aide_" + action) : T(d.raison);
  return `<button class="ec-bouton bloc" data-action="${action}" ${arg ? `data-arg="${esc(arg)}"` : ""}
    ${d.ok && !X.occupe ? "" : "disabled"} title="${esc(titre)}">${ico(icone)} ${esc(libelle)}</button>`;
}

function peindreDroite() {
  const { esc } = X.ctx;
  const e = X.etat;
  const bl = e && e.blender;
  const formats = formatsLocaux(X.capacites);
  const blocs = {
    moteur: [
      bouton("glb_maillage", T("exp.glb_maillage"), "dz-lab3d-maillage"),
      bouton("glb_pose", T("exp.glb_pose"), "dz-lab3d-rig"),
      bouton("glb_animation", T("exp.glb_animation"), "dz-cat-animation"),
      bouton("fbx", bl && bl.dispo ? T("exp.fbx_blender", { v: bl.version }) : T("exp.fbx"), "dz-action-exporter"),
      bouton("godot", T("exp.godot"), "dz-action-exporter"),
      ...CIBLES_ETABLI.map((c) => bouton(c, T("exp." + c), "dz-action-exporter")),
      `<div class="ec-note">${esc(T("exp.moteur_aide"))}</div>`,
    ],
    web: [bouton("threejs", T("exp.threejs"), "dz-action-telecharger"),
      `<div class="ec-note">${esc(T("exp.threejs_aide"))}</div>`],
    optimisation: [
      `<label class="ec-champ">${esc(T("exp.usage"))}<select id="exUsage" class="ex-select">${USAGES_LOD.map((u) =>
        `<option value="${u}" ${u === X.usage ? "selected" : ""}>${esc(T("exp.usage_" + u))}</option>`).join("")}</select></label>`,
      bouton("lod", T("exp.lod"), "dz-lab3d-optimiser"),
      `<label class="ec-champ">${esc(T("exp.nommage"))}<select id="exNommage" class="ex-select">${NOMMAGES.map((n) =>
        `<option value="${n}" ${n === X.nommage ? "selected" : ""}>${esc(T("exp.nommage_" + n))}</option>`).join("")}</select></label>`,
      bouton("textures", T("exp.textures"), "dz-lab3d-materiau"),
      `<div class="ec-note">${esc(T("exp.optimisation_aide"))}</div>`,
    ],
    impression: [bouton("impression", T("exp.impression"), "dz-action-exporter"),
      `<div class="ec-note">${esc(T("exp.impression_aide"))}</div>`],
    formats: [
      formats.length ? `<div class="ex-formats">${formats.map((f) => bouton("formats", "." + f, "dz-action-telecharger", f)).join("")}</div>`
        : `<div class="ec-note">${esc(T("exp.formats_vide"))}</div>`,
      `<div class="ec-note">${esc(T("exp.formats_aide"))}</div>`,
    ],
    bibliotheque: [bouton("ranger", T("exp.ranger"), "dz-action-envoyer-vers"),
      `<div class="ec-note">${esc(T("exp.ranger_aide"))}</div>`],
  };
  $("#exDroite").innerHTML = SECTIONS.map((s) =>
    `<section class="ex-section" data-section="${s.id}"><div class="ec-label">${esc(T("exp.section_" + s.id))}</div>${blocs[s.id].join("")}</section>`).join("");
}

function peindrePrets() {
  const { esc, ico } = X.ctx;
  $("#exPrets").innerHTML = X.prets.map((p) => `<li>
      <a class="ec-bouton" href="${esc(p.url)}" download="${esc(p.fichier)}">${ico("dz-action-telecharger")} ${esc(p.fichier)}</a>
      <span class="ex-detail">${esc(p.detail || "")}</span></li>`).join("")
    || `<li class="ec-note">${esc(T("exp.prets_vide"))}</li>`;
}

function avis(t) { $("#exAvis").textContent = t || ""; }

function pret(fichier, url, detail) {
  X.prets = [{ fichier, url, detail }, ...X.prets.filter((p) => p.fichier !== fichier)].slice(0, 30);
  peindrePrets();
}

/* ── aperçu d'un clip dans le viewport ─────────────────────────────────── */
function arreter() {
  if (X.mixer) X.mixer.stopAllAction();
  X.mixer = null;
  cancelAnimationFrame(X.boucle);
}

function jouer(nom) {
  const g = X.vue && X.vue.gltf;
  const clip = g && (g.animations || []).find((c) => c.name === nom);
  arreter();
  if (!clip) { avis(T("exp.clip_absent", { c: nom })); return; }
  X.mixer = new THREE.AnimationMixer(X.vue.racine);
  X.mixer.clipAction(clip).play();
  X.horloge = new THREE.Clock();
  const pas = () => {
    if (!X.mixer) return;
    X.mixer.update(X.horloge.getDelta());
    X.boucle = requestAnimationFrame(pas);
  };
  pas();
}

/* ── actions ──────────────────────────────────────────────────────────── */
async function poster(url, corps) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps || {}) });
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
  }
  return r;
}

async function blobPret(r, defaut, detail) {
  const fichier = nomDeReponse(r.headers.get("Content-Disposition"), defaut);
  const b = await r.blob();
  pret(fichier, URL.createObjectURL(b), detail || octets(b.size, langue()));
}

async function agir(action, arg) {
  const f = X.fiche;
  if (!f || X.occupe) return;
  X.occupe = true;
  peindreDroite();
  avis(T("exp.en_cours"));
  const job = enc(f.job), v = f.version, nom = X.nom.trim() || undefined;
  const lg = langue();
  try {
    if (action.startsWith("glb_")) {
      const variante = action.slice(4);
      const corps = corpsGlb(variante, { version: v, nom, clipPose: X.clipPose, coches: [...X.coches], clips: X.etat && X.etat.clips });
      const j = await (await poster(`/api/studio3d/exporter/${job}/glb`, corps)).json();
      X.dernierGlb = j;
      pret(j.fichier, j.url, variante === "pose" && j.pose === "repos" ? T("exp.pose_repos") : octets(j.octets, lg));
    } else if (action === "fbx") {
      const j = await (await poster(`/api/studio3d/exporter/${job}/fbx`, { version: v, nom,
        variante: (X.etat.clips || []).length ? "animation" : "maillage" })).json();
      pret(j.fichier, j.url, T("exp.fbx_detail", { v: j.blender || "?", o: octets(j.octets, lg) }));
    } else if (action === "threejs") {
      const coches = [...X.coches];
      const j = await (await poster(`/api/studio3d/exporter/${job}/threejs`, { version: v, nom,
        clips: coches.length ? coches : undefined })).json();
      pret(j.fichier, j.url, T("exp.threejs_detail", { n: j.entrees.length, c: j.manifeste.clips.length }));
    } else if (action === "godot") {
      const hb = hitboxesParDefaut(X.etat.os);
      const r = await poster("/api/etabli/mouvement/godot", { job: f.job, version: v, hitboxes: hb, nom: nomSur(nom, "Personnage") });
      await blobPret(r, `${f.job}_v${v}_godot.zip`, T("exp.godot_detail", { n: r.headers.get("X-DZ-Hitboxes") || hb.length }));
    } else if (CIBLES_ETABLI.includes(action)) {
      const j = await (await poster("/api/etabli/export", { job: f.job, version: v, cible: action })).json();
      pret(j.fichier, j.url, T("exp.etabli_detail", { o: octets(j.bytes, lg) }));
    } else if (action === "lod") {
      const j = await (await poster(`/api/assets/3d/${job}/lod`, { usage: X.usage })).json();
      const n = (j.niveaux || j.lods || []).length;
      pret(`${f.job}_lod.zip`, `/api/assets/3d/${job}/lod-zip`, n ? T("exp.lod_detail", { n }) : "");
    } else if (action === "textures") {
      const r = await poster(`/api/assets/3d/${job}/textures`, { naming: X.nommage, version: v });
      await blobPret(r, `${f.job}_textures.zip`);
    } else if (action === "formats" && arg) {
      const r = await poster(`/api/assets/3d/${job}/convert`, { format: arg, version: v });
      await blobPret(r, `${f.job}.${arg}`);
    } else if (action === "impression") {
      const j = await (await poster(`/api/print3d/from-assets3d/${job}`, { version: v, nom: nomSur(nom, f.nom || f.job) })).json();
      const base = `/api/studio3d/exporter/impression/${enc(j.dossier)}/`;
      pret(j.mf3, base + enc(j.mf3), T("exp.impression_detail", { n: nb(j.triangles) }));
      pret(j.stl, base + enc(j.stl), T("exp.impression_detail", { n: nb(j.triangles) }));
    } else if (action === "ranger") {
      await ranger();
    }
    avis(T("exp.fait"));
    try { X.etat = await X.ctx.jget(`/api/studio3d/exporter/${job}?version=${v}`); } catch { /* garde l'ancien */ }
    peindreDeja();
  } catch (e) {
    avis(T("exp.erreur", { m: e.message }));
  } finally {
    X.occupe = false;
    peindreDroite();
  }
}

/* « Ranger en Bibliothèque » : le dernier GLB exporté (sinon le maillage seul, écrit pour l'occasion) devient un modèle
   de plus par la route d'import existante — la Bibliothèque et l'Atelier le voient comme un autre (import_…). */
async function ranger() {
  const f = X.fiche;
  let g = X.dernierGlb;
  if (!g || g.job !== f.job || g.version !== f.version) {
    g = await (await poster(`/api/studio3d/exporter/${enc(f.job)}/glb`, { variante: "maillage", version: f.version,
      nom: X.nom.trim() || undefined })).json();
  }
  const b = await (await fetch(g.url)).blob();
  const fd = new FormData();
  fd.append("file", b, g.fichier);
  const r = await fetch("/api/assets/3d/importer", { method: "POST", body: fd });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
  pret(g.fichier, g.url, T("exp.range", { job: j.job }));
}
