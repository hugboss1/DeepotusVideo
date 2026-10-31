/* t391 (31/10/2026) — écran IMPORTER du 3D Studio : un modèle venu d'ailleurs devient un job, puis s'ouvre.

   Formats lus aujourd'hui par le serveur (POST /api/assets/3d/importer, `mesh_convert.importer_job`, local et
   gratuit) : OBJ, STL, glTF, GLB ; FBX (Mixamo…) converti par Blender en arrière-plan et VRM (un GLB) depuis t391
   (POST /api/studio3d/importer, service studio3d_import).
   t405 : Daz Genesis 8 / 8.1 — deux zones, le FBX de la figure et le dossier de textures (`webkitdirectory`, ou un
   dossier glissé, lu récursivement) ; les cartes partent avec leur chemin relatif (`Genesis 8 Female.images/…`) dans
   le nom de fichier, `type=daz`, et le serveur les pose à côté du FBX pour Blender. */
"use strict";
import { T } from "./coque_calc.js";

const ACCEPTE = ".obj,.stl,.gltf,.glb,.fbx,.vrm";
const IMAGES = ["tif", "tiff", "png", "jpg", "jpeg", "bmp", "tga", "exr", "hdr", "webp"];
const TEXTURES_MAX = 400;       // même borne que studio3d_import.TEXTURES_NB_MAX
const I = { s: null, ctx: null, occupe: false };
const D = { fbx: null, textures: [], dossier: "", job: null };

const extension = (nom) => (String(nom).split(".").pop() || "").toLowerCase();

export async function monter(section, ctx) {
  I.s = section;
  I.ctx = ctx;
  const { esc, ico } = ctx;
  section.innerHTML = `<div class="ec-importer">
    <label class="ec-depot" id="imDepot">
      ${ico("dz-action-importer")}
      <b>${esc(T("importer.deposer"))}</b>
      <span>${esc(T("importer.formats"))}</span>
      <input type="file" id="imFichier" accept="${ACCEPTE}" hidden>
    </label>
    <div class="ec-avis" id="imAvis"></div>
    <div class="ec-label">${esc(T("importer.daz_titre"))}</div>
    <div class="ec-note">${esc(T("importer.daz_dossier_aide"))}</div>
    <label class="ec-depot petit" id="imDazFbxZone">
      ${ico("dz-action-importer")}
      <b id="imDazFbxNom">${esc(T("importer.daz_fbx"))}</b>
      <input type="file" id="imDazFbx" accept=".fbx" hidden>
    </label>
    <label class="ec-depot petit" id="imDazDossierZone">
      ${ico("dz-action-importer")}
      <b id="imDazDossierNom">${esc(T("importer.daz_dossier"))}</b>
      <input type="file" id="imDazDossier" webkitdirectory multiple hidden>
    </label>
    <button type="button" class="ec-bouton bloc" id="imDazLancer" disabled>${esc(T("importer.daz_lancer"))}</button>
    <div class="ec-avis" id="imDazAvis"></div>
    <button type="button" class="ec-bouton bloc" id="imDazOuvrir" hidden>${esc(T("importer.daz_ouvrir"))}</button>
    <div class="ec-label">${esc(T("importer.types"))}</div>
    <div class="ec-types">
      ${["gltf", "obj", "stl", "fbx", "vrm", "daz"].map((t) => `<div class="ec-type"><b>${esc(T("type." + t))}</b><span>${esc(T("type." + t + "_aide"))}</span></div>`).join("")}
    </div>
  </div>`;
  const depot = section.querySelector("#imDepot");
  section.querySelector("#imFichier").addEventListener("change", (e) => e.target.files[0] && envoyer(e.target.files[0]));
  survol(depot, (e) => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) envoyer(f);
  });
  monterDaz(section);
}

function survol(zone, deposer) {
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("survol"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("survol"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("survol");
    deposer(e);
  });
}

async function envoyer(fichier) {
  if (I.occupe) return;
  const avis = I.s.querySelector("#imAvis");
  const ext = extension(fichier.name);
  if (!ACCEPTE.split(",").includes("." + ext)) {
    avis.textContent = T("importer.refus_format", { f: ext || "?" });
    return;
  }
  I.occupe = true;
  avis.textContent = T("importer.envoi", { f: fichier.name });
  try {
    const fd = new FormData();
    fd.append("file", fichier, fichier.name);
    const r = await fetch("/api/studio3d/importer", { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
    avis.textContent = T("importer.fait", { n: j.triangles });
    await I.ctx.ouvrir(j.job, null, "preparer");
  } catch (e) {
    avis.textContent = T("erreur.importer", { m: e.message });
  } finally {
    I.occupe = false;
    I.s.querySelector("#imFichier").value = "";
  }
}

// ── t405 : Daz Genesis 8 / 8.1 ──────────────────────────────────────────────────────────────────────────────────────

function monterDaz(section) {
  const q = (id) => section.querySelector(id);
  q("#imDazFbx").addEventListener("change", (e) => e.target.files[0] && choisirFbx(e.target.files[0]));
  q("#imDazDossier").addEventListener("change", (e) => {
    const liste = [...(e.target.files || [])].map((f) => ({ f, chemin: f.webkitRelativePath || f.name }));
    choisirTextures(liste);
  });
  survol(q("#imDazFbxZone"), (e) => {
    const f = [...(e.dataTransfer.files || [])].find((x) => extension(x.name) === "fbx");
    if (f) choisirFbx(f);
  });
  survol(q("#imDazDossierZone"), async (e) => {
    const entrees = [...(e.dataTransfer.items || [])].map((it) => it.webkitGetAsEntry && it.webkitGetAsEntry()).filter(Boolean);
    const liste = [];
    for (const en of entrees) await lireEntree(en, liste);
    choisirTextures(liste);
  });
  q("#imDazLancer").addEventListener("click", envoyerDaz);
  q("#imDazOuvrir").addEventListener("click", async () => {
    if (D.job) await I.ctx.ouvrir(D.job, null, "preparer");
  });
}

// un dossier glissé : on descend dedans (readEntries rend les entrées par paquets, on relit jusqu'au vide)
async function lireEntree(entree, liste) {
  if (entree.isFile) {
    const f = await new Promise((ok, ko) => entree.file(ok, ko));
    liste.push({ f, chemin: String(entree.fullPath || f.name).replace(/^\/+/, "") });
    return;
  }
  if (!entree.isDirectory) return;
  const lecteur = entree.createReader();
  for (;;) {
    const lot = await new Promise((ok, ko) => lecteur.readEntries(ok, ko));
    if (!lot.length) break;
    for (const en of lot) await lireEntree(en, liste);
  }
}

function choisirFbx(f) {
  const avis = I.s.querySelector("#imDazAvis");
  if (extension(f.name) !== "fbx") {
    avis.textContent = T("importer.refus_format", { f: extension(f.name) || "?" });
    return;
  }
  D.fbx = f;
  I.s.querySelector("#imDazFbxNom").textContent = T("importer.daz_fbx_choisi", { f: f.name });
  I.s.querySelector("#imDazLancer").disabled = false;
  avis.textContent = "";
}

function choisirTextures(liste) {
  const avis = I.s.querySelector("#imDazAvis");
  const images = liste.filter((x) => IMAGES.includes(extension(x.f.name)));
  if (images.length > TEXTURES_MAX) {
    avis.textContent = T("importer.daz_trop", { n: images.length, max: TEXTURES_MAX });
    return;
  }
  D.textures = images;
  D.dossier = images.length ? images[0].chemin.split("/")[0] : "";
  I.s.querySelector("#imDazDossierNom").textContent = images.length
    ? T("importer.daz_dossier_choisi", { n: images.length, d: D.dossier })
    : T("importer.daz_dossier");
  avis.textContent = "";
}

async function envoyerDaz() {
  if (I.occupe) return;
  const avis = I.s.querySelector("#imDazAvis");
  const ouvrir = I.s.querySelector("#imDazOuvrir");
  if (!D.fbx) {
    avis.textContent = T("importer.daz_sans_fbx");
    return;
  }
  I.occupe = true;
  ouvrir.hidden = true;
  avis.textContent = T("importer.envoi", { f: D.fbx.name });
  try {
    const fd = new FormData();
    fd.append("type", "daz");
    fd.append("file", D.fbx, D.fbx.name);
    for (const t of D.textures) fd.append("textures", t.f, t.chemin);
    const r = await fetch("/api/studio3d/importer", { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || String(r.status));
    const tx = j.textures || { envoyees: 0, trouvees: [], manquantes: [] };
    let texte = T("importer.daz_fait", { n: j.triangles, os: j.os, t: tx.trouvees.length, e: tx.envoyees });
    if (tx.manquantes.length) {
      const l = tx.manquantes.slice(0, 6).join(", ") + (tx.manquantes.length > 6 ? "…" : "");
      texte += " " + T("importer.daz_manquantes", { l });
    }
    avis.textContent = texte;
    D.job = j.job;
    if (tx.manquantes.length) ouvrir.hidden = false;      // l'avis reste lisible : on ouvre à la demande
    else await I.ctx.ouvrir(j.job, null, "preparer");
  } catch (e) {
    avis.textContent = T("erreur.importer", { m: e.message });
  } finally {
    I.occupe = false;
  }
}
