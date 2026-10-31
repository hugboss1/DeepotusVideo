/* t391 (31/10/2026) — écran IMPORTER du 3D Studio : un modèle venu d'ailleurs devient un job, puis s'ouvre.

   Formats lus aujourd'hui par le serveur (POST /api/assets/3d/importer, `mesh_convert.importer_job`, local et
   gratuit) : OBJ, STL, glTF, GLB ; FBX (Mixamo…) converti par Blender en arrière-plan et VRM (un GLB) depuis t391
   (POST /api/studio3d/importer, service studio3d_import). Daz Genesis 8 (FBX + dossier de textures) reste annoncé. */
"use strict";
import { T } from "./coque_calc.js";

const ACCEPTE = ".obj,.stl,.gltf,.glb,.fbx,.vrm";
const I = { s: null, ctx: null, occupe: false };

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
    <div class="ec-label">${esc(T("importer.types"))}</div>
    <div class="ec-types">
      ${["gltf", "obj", "stl", "fbx", "vrm"].map((t) => `<div class="ec-type"><b>${esc(T("type." + t))}</b><span>${esc(T("type." + t + "_aide"))}</span></div>`).join("")}
      ${["daz"].map((t) => `<div class="ec-type bientot"><b>${esc(T("type." + t))} <span class="ec-badge discret">${esc(T("bientot.badge"))}</span></b><span>${esc(T("type." + t + "_aide"))}</span></div>`).join("")}
    </div>
  </div>`;
  const depot = section.querySelector("#imDepot");
  section.querySelector("#imFichier").addEventListener("change", (e) => e.target.files[0] && envoyer(e.target.files[0]));
  depot.addEventListener("dragover", (e) => { e.preventDefault(); depot.classList.add("survol"); });
  depot.addEventListener("dragleave", () => depot.classList.remove("survol"));
  depot.addEventListener("drop", (e) => {
    e.preventDefault();
    depot.classList.remove("survol");
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) envoyer(f);
  });
}

async function envoyer(fichier) {
  if (I.occupe) return;
  const avis = I.s.querySelector("#imAvis");
  const ext = (fichier.name.split(".").pop() || "").toLowerCase();
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
