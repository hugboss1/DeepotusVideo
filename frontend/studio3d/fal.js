/* Atelier fal du 3D Studio — T104 (plan-moteurs-3d T2, R10e P1) : rig et animations Meshy d'un job Game Assets 3D.
   Aucun état partagé avec le graphe Meshy de studio3d.js : ce module parle aux routes /api/assets/3d/* et montre le
   résultat dans SON aperçu (le <model-viewer> du rail droit appartient au graphe, qui le réécrit à chaque rendu).
   Le prix vient du devis du backend (GET …/rig/devis, le même que la garde des plafonds) ; le bouton se grise et
   DIT pourquoi tant qu'une porte est fermée (clé, approbation, texture) ; un tir payant se confirme. */
"use strict";
const $ = (s) => document.querySelector(s);
/* Deepotus Glyph (G6) : une icône de la suite, décorative — le sens est porté par le bouton (libellé, title,
   aria-label). libeller() écrit le libellé en textContent PUIS pose l'icône devant : le texte du bouton reste
   exactement le libellé (et, sans runtime d'icônes — un banc sous node —, le bouton n'a que son texte). */
export function ico(cle, t = 16) {
  return typeof dzIcone === "function" ? dzIcone(cle, { taille: t, classe: "dzi--" + t }) : "";
}
export function libeller(el, cle, texte) {
  el.textContent = texte;
  const i = ico(cle);
  if (i && typeof el.insertAdjacentHTML === "function") el.insertAdjacentHTML("afterbegin", i);
}

export const F = { jobs: [], job: null, devis: null, poll: null, actions: new Set() };

export async function jget(p) {
  const r = await fetch(p);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `${p} → ${r.status}`);
  return j;
}

export async function jpost(p, b) {
  const r = await fetch(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j.detail && j.detail.message) || j.detail || `${p} → ${r.status}`);
  return j;
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* la raison pour laquelle le rig ne peut pas partir, ou "" */
export function refus(d) {
  if (!d) return __dzT9("studio3d.s3b_fal.devis_indispo", "devis indisponible");
  if (!d.meshy) return __dzT9("studio3d.s3b_fal.cle_meshy", "clé Meshy absente — Réglages → « Meshy 6 (3D) »");
  if (!d.fal) return __dzT9("studio3d.s3b_fal.cle_fal", "clé fal absente — Réglages : le maillage passe par le stockage fal pour que Meshy le lise");
  if (!d.approuve) return __dzT9("studio3d.s3b_fal.non_approuve", "géométrie non approuvée — valide le volume dans Game Assets 3D d'abord");
  if (!d.texture) return __dzT9("studio3d.s3b_fal.sans_texture", "maillage sans texture — Meshy ne rigge que des modèles texturés");
  return "";
}

export async function chargerJobs(choix) {
  const s = await jget("/api/etabli/sources");
  F.jobs = (s.jobs || []).filter((j) => j.source === "assets3d" && j.etapes && j.etapes.length)
    .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
  const sel = $("#falJob");
  sel.innerHTML = F.jobs.length
    ? F.jobs.map((j) => `<option value="${esc(j.id)}">${esc(j.nom)} · ${esc(j.moteur || "?")} · v${esc(j.etapes[j.etapes.length - 1].version || "?")}</option>`).join("")
    : `<option value="">${__dzT9("studio3d.s3b_fal.aucun_job", "aucun job Game Assets 3D")}</option>`;
  F.job = choix && F.jobs.some((j) => j.id === choix) ? choix : (F.jobs[0] ? F.jobs[0].id : null);
  if (F.job) sel.value = F.job;
  await rafraichirDevis();
  await montrerAnimations();
  await rafraichirConversion();
}

/* ── T105 C : conversion et import ──────────────────────────────────────────
   Le serveur est la SEULE source de la liste des formats : coder « fbx » en dur ici promettrait un format le jour
   où gltfpack change. Local = téléchargement immédiat ; Meshy = confirmé (1 crédit), suivi dans la file. */
export async function rafraichirConversion() {
  const fmt = $("#cvFmt"), go = $("#cvGo");
  if (!F.job) { go.disabled = true; $("#cvConvertis").textContent = ""; return; }
  const c = await jget(`/api/assets/3d/${encodeURIComponent(F.job)}/convert`).catch(() => null);
  if (!c) { go.disabled = true; return; }
  F.caps = c;
  if (!fmt.dataset.pret) {
    fmt.dataset.pret = "1";
    fmt.innerHTML = c.local_export.map((f) => `<option value="${esc(f)}">${esc(f)} · ${__dzT9("studio3d.s3b_fal.local_gratuit", "local, gratuit")}</option>`).join("")
      + c.meshy.map((f) => `<option value="${esc(f)}">${esc(f)} · Meshy, ${esc(c.credits_meshy)} cr</option>`).join("");
    $("#cvNote").textContent = c.pourquoi_pas_local;
  }
  go.disabled = false;
  $("#cvConvertis").innerHTML = (c.convertis || []).length
    ? __dzT9("studio3d.s3b_fal.deja_convertis", "déjà convertis : ") + c.convertis.map((f) => `<a href="/api/assets/3d/${encodeURIComponent(F.job)}/convert/${encodeURIComponent(f)}" download>${esc(f)}</a>`).join(" · ")
    : "";
}

function telecharger(blob, nom) {
  const u = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = u; a.download = nom; a.click();
  setTimeout(() => URL.revokeObjectURL(u), 4000);
}

export async function convertir(confirmer, toast) {
  const fmt = $("#cvFmt").value, c = F.caps;
  if (!F.job || !c || !fmt) return;
  if (c.meshy.includes(fmt)) {
    if (!await confirmer(__dzT9("studio3d.s3b_fal.confirmer_conv", "Convertir « {job} » en {fmt} chez Meshy : {cr} crédit pour la tâche.", { job: F.job, fmt: fmt, cr: c.credits_meshy }) + "\n" + c.pourquoi_pas_local,
      { titre: __dzT9("studio3d.s3b_fal.conv_titre", "Conversion Meshy"), ok: __dzT9("studio3d.s3b.payer_cr", "Payer {cr} cr", { cr: c.credits_meshy }) })) return;
    const r = await jpost(`/api/assets/3d/${encodeURIComponent(F.job)}/convert`, { format: fmt });
    $("#cvEtat").textContent = __dzT9("studio3d.s3b_fal.en_file", "en file…");
    suivre(r.job_id, async (j) => {
      $("#cvEtat").textContent = j.status === "done" ? __dzT9("studio3d.s3b_fal.fmt_pret", "{fmt} prêt", { fmt: fmt }) : __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" });
      await rafraichirConversion();
    }, "#cvEtat");
    return;
  }
  const mm = Number($("#cvMm").value) || null;
  const r = await fetch(`/api/assets/3d/${encodeURIComponent(F.job)}/convert`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format: fmt, cible_mm: (fmt === "stl" || fmt === "3mf") ? mm : null }) });
  if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(j.detail || __dzT9("studio3d.s3b_fal.conv_statut", "conversion {fmt} → {st}", { fmt: fmt, st: r.status })); }
  const cd = r.headers.get("content-disposition") || "";
  const m = /filename="([^"]+)"/.exec(cd);
  telecharger(await r.blob(), m ? m[1] : `${F.job}.${fmt}`);
  $("#cvEtat").textContent = __dzT9("studio3d.s3b_fal.fmt_telecharge", "{fmt} téléchargé", { fmt: fmt });
}

export async function importer(fichier, toast) {
  if (!fichier) return;
  const fd = new FormData();
  fd.append("file", fichier);
  $("#cvEtat").textContent = __dzT9("studio3d.s3b_fal.import_de", "import de {nom}…", { nom: fichier.name });
  const r = await fetch("/api/assets/3d/importer", { method: "POST", body: fd });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `import → ${r.status}`);
  $("#cvEtat").textContent = `${fichier.name} → job ${j.job} (${Number(j.triangles).toLocaleString("fr-FR")} tris)`;
  await chargerJobs(j.job);
  toast(__dzT9("studio3d.s3b_fal.importe", "Modèle importé : {job}", { job: j.job }));
}

export function dessinerActions(connues) {
  const box = $("#rigActions");
  if (box.dataset.pret) return;
  box.dataset.pret = "1";
  box.innerHTML = Object.entries(connues || {}).map(([id, nom]) =>
    `<label class="rig-act" title="${__dzT9("studio3d.s3b_fal.action_title", "Action {id} de la bibliothèque Meshy · 3 cr", { id: esc(id) })}"><input type="checkbox" value="${esc(id)}"> ${esc(nom)}</label>`).join("");
  box.querySelectorAll("input").forEach((i) => i.addEventListener("change", () => {
    if (i.checked) F.actions.add(Number(i.value)); else F.actions.delete(Number(i.value));
    rafraichirDevis();
  }));
}

export async function rafraichirDevis() {
  const btn = $("#btnRig");
  if (!F.job) { libeller(btn, "dz-lab3d-rig", __dzT9("studio3d.s3b_fal.rig_aucun", "Rig Meshy · aucun job")); btn.disabled = true; btn.title = __dzT9("studio3d.s3b_fal.aucun_job", "aucun job Game Assets 3D"); return; }
  try {
    const acts = [...F.actions].sort((a, b) => a - b).join(",");
    const d = await jget(`/api/assets/3d/${encodeURIComponent(F.job)}/rig/devis?actions=${encodeURIComponent(acts)}`);
    F.devis = d;
    dessinerActions(d.actions_connues);
    $("#falJobNote").textContent = `${d.fichier} · ${Number(d.tris).toLocaleString("fr-FR")} tris`
      + (d.remesh_requis ? __dzT9("studio3d.s3b_fal.remesh", " · remesh requis (> 300 000 faces)") : "");
    const cr = (d.credits && d.credits.meshy) || 0;
    const non = refus(d);
    libeller(btn, "dz-lab3d-rig", `Rig Meshy · ${cr} cr`);
    btn.disabled = !!non;
    btn.title = non || (d.breakdown || []).map((l) => `${l.label} : ${l.units} cr`).join("\n");
    $("#rigRefus").textContent = non;
  } catch (e) {
    F.devis = null;
    btn.disabled = true;
    $("#falJobNote").textContent = String(e.message || e);
  }
}

/* un clip se joue par `autoplay` seul : sans `animation-name`, <model-viewer> joue le PREMIER clip du fichier — le
   nom des clips d'un GLB Meshy réel n'est pas documenté, le deviner serait faux */
export function montrerGlb(url, jouer) {
  const box = $("#falPreview");
  box.classList.remove("hidden");
  let mv = box.querySelector("model-viewer");
  if (!mv) {
    mv = document.createElement("model-viewer");
    mv.setAttribute("camera-controls", "");
    mv.setAttribute("interaction-prompt", "none");
    box.appendChild(mv);
  }
  mv.setAttribute("src", url);
  if (jouer) mv.setAttribute("autoplay", ""); else mv.removeAttribute("autoplay");
}

export async function montrerAnimations() {
  const pick = $("#animPick");
  if (!F.job) { pick.classList.add("hidden"); return; }
  const a = await jget(`/api/assets/3d/${encodeURIComponent(F.job)}/animations`).catch(() => ({ animations: [] }));
  const anims = a.animations || [];
  pick.classList.toggle("hidden", !anims.length);
  $("#falPreview").classList.toggle("hidden", !anims.length);
  pick.innerHTML = anims.map((x) => `<option value="${esc(x.url)}">${esc(x.nom)}</option>`).join("");
  if (anims[0]) montrerGlb(anims[0].url, true);
}

export function suivre(jobId, onDone, cible = "#rigEtat") {
  clearInterval(F.poll);
  F.poll = setInterval(async () => {
    const j = await jget(`/api/jobs/${jobId}`).catch(() => null);
    if (!j) return;
    $(cible).textContent = `${j.current_step || ""} ${j.progress || 0} %`;
    if (j.status === "done" || j.status === "failed") { clearInterval(F.poll); onDone(j); }
  }, 2500);
}

export async function lancerRig(confirmer, toast) {
  const d = F.devis;
  const non = refus(d);
  if (non) { toast(non); return; }
  const cr = (d.credits && d.credits.meshy) || 0;
  const detail = (d.breakdown || []).map((l) => `· ${l.label} : ${l.units} cr`).join("\n");
  if (!await confirmer(__dzT9("studio3d.s3b_fal.confirmer_rig", "Rigger « {job} » chez Meshy : {cr} crédits (~${usd}).", { job: F.job, cr: cr, usd: Number(d.total_usd || 0).toFixed(2) }) + "\n" + detail,
    { titre: "Rig Meshy", ok: __dzT9("studio3d.s3b.payer_cr", "Payer {cr} cr", { cr: cr }) })) return;
  const btn = $("#btnRig");
  btn.disabled = true;
  const h = Number($("#rigH").value) || 1.7;
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(F.job)}/rig`, { height_m: h, actions: [...F.actions] });
  $("#rigEtat").textContent = __dzT9("studio3d.s3b_fal.en_file", "en file…");
  suivre(r.job_id, async (j) => {
    await rafraichirDevis();
    if (j.status !== "done") { $("#rigEtat").textContent = __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" }); return; }
    $("#rigEtat").textContent = __dzT9("studio3d.s3b_fal.rigge", "riggé · clips rapatriés");
    await montrerAnimations();
  });
}

export function brancher({ confirmer, toast }) {
  $("#btnRig").addEventListener("click", () => lancerRig(confirmer, toast).catch((e) => {
    $("#btnRig").disabled = false; toast(String(e.message || e));
  }));
  $("#falJob").addEventListener("change", (ev) => {
    F.job = ev.target.value || null; rafraichirDevis(); montrerAnimations(); rafraichirConversion();
  });
  $("#animPick").addEventListener("change", (ev) => montrerGlb(ev.target.value, true));
  $("#cvGo").addEventListener("click", () => convertir(confirmer, toast).catch((e) => toast(String(e.message || e))));
  $("#cvImport").addEventListener("change", (ev) => {
    const f = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    importer(f, toast).catch((e) => { $("#cvEtat").textContent = ""; toast(String(e.message || e)); });
  });
}
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
