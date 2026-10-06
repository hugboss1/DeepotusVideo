/* Vues d'abord — T106 (plan-moteurs-3d T6, R10e P5) : les vues d'un maillage se regardent, se rejouent une à une et
   se détourent AVANT de payer le moteur. Une vue ratée (bras coupé, fond sale, profil de trois quarts) ne coûte plus
   deux fois : la vue, puis le maillage qu'elle abîme.
   Le prix de chaque geste payant vient du devis du backend (POST /api/cost/estimate, le même calcul que la garde des
   plafonds) et se CONFIRME ; le détourage local est gratuit et part sans question. Le bouton « Tirer » se grise et
   DIT pourquoi (déjà tiré, aucune vue, une opération en cours). */
"use strict";
import { jget, jpost } from "./fal.js";

const $ = (s) => document.querySelector(s);

export const V = { images: [], moteurs: [], jeux: [], entites: [], jeu: null, info: null, poll: null, occupe: false };

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const usd = (x) => `$${Number(x || 0).toFixed(2)}`;

export async function devis(op) {
  return jpost("/api/cost/estimate", op);
}

/* la raison pour laquelle le jeu ne peut pas être tiré, ou "" */
export function refusTir(info, occupe) {
  if (!info) return "aucun jeu de vues choisi";
  if (info.etat === "tire") return "déjà tiré : le maillage existe — prépare un nouveau jeu pour retirer";
  if (occupe) return "une opération tourne sur ce jeu — attends qu'elle finisse";
  if (!(info.vues || []).some((v) => v.file)) return "aucune vue exploitable : rejoue-en au moins une";
  return "";
}

export async function charger() {
  const [im, en, je, bi] = await Promise.all([
    jget("/api/images").catch(() => ({ images: [] })),
    jget("/api/assets3d/engines").catch(() => ({ engines: [] })),
    jget("/api/assets/3d/views").catch(() => ({ jeux: [] })),
    jget("/api/bible/entities").catch(() => ({ entities: [] })),
  ]);
  /* T7 : seules les entités dont la planche porte une vue de face — personnage (front, left, right, back) et objet
     (front, back) — et qui ONT une planche ou une recette */
  V.entites = (bi.entities || []).filter((e) => (e.kind === "character" || e.kind === "object") && (e.ref_image || e.has_recipe));
  const ent = $("#vuesEntite").value;
  $("#vuesEntite").innerHTML = V.entites.length
    ? V.entites.map((e) => `<option value="${esc(e.id)}"${e.id === ent ? " selected" : ""}>${esc(e.name)} · ${e.kind === "character" ? "personnage" : "objet"}${e.model3d_job ? " · a déjà un maillage" : ""}</option>`).join("")
    : `<option value="">aucune entité avec planche</option>`;
  $("#btnVuesBible").disabled = !V.entites.length;
  V.images = im.images || [];
  V.moteurs = en.engines || [];
  V.jeux = je.jeux || [];
  /* recharger GARDE le choix de l'utilisateur (vu à l'écran le 06/10 : il revenait au premier) */
  const img = $("#vuesImg").value, mot = $("#vuesMoteur").value || en.default || "tripo";
  $("#vuesImg").innerHTML = V.images.length
    ? V.images.map((x) => `<option value="${esc(x.filename)}"${x.filename === img ? " selected" : ""}>${esc(x.filename)}</option>`).join("")
    : `<option value="">Bibliothèque vide</option>`;
  $("#vuesMoteur").innerHTML = V.moteurs.map((m) =>
    `<option value="${esc(m.id)}"${m.id === mot ? " selected" : ""}>${esc(m.label || m.id)} · ${usd(m.usd_texture)}</option>`).join("");
  dessinerJeux();
  await prixPreparer();
  if (V.jeu || V.jeux[0]) await ouvrirJeu(V.jeu || V.jeux[0].job);
  else montrer(null);
}

function dessinerJeux() {
  const sel = $("#vuesJeu");
  sel.innerHTML = V.jeux.length
    ? V.jeux.map((j) => `<option value="${esc(j.job)}"${j.job === V.jeu ? " selected" : ""}>${esc(j.image_filename)} · ${esc(j.engine)} · ${j.etat === "tire" ? "tiré" : "en attente"}${j.ratees ? ` · ${j.ratees} ratée(s)` : ""}</option>`).join("")
    : `<option value="">aucun jeu de vues</option>`;
}

export async function prixPreparer() {
  const n = Math.max(1, Math.min(4, Number($("#vuesN").value) || 4));
  const btn = $("#btnVues");
  try {
    const d = await devis({ kind: "asset3d_views", views: n });
    btn.textContent = `Préparer ${n} vue${n > 1 ? "s" : ""} · ${usd(d.total_usd)}`;
    btn.dataset.usd = d.total_usd;
  } catch (e) { btn.textContent = `Préparer ${n} vues`; delete btn.dataset.usd; }
  btn.disabled = !$("#vuesImg").value;
}

export async function preparer(confirmer, toast) {
  const fn = $("#vuesImg").value;
  if (!fn) { toast("choisis une image de la Bibliothèque"); return; }
  const n = Math.max(1, Math.min(4, Number($("#vuesN").value) || 4));
  const moteur = $("#vuesMoteur").value || "tripo";
  const prix = usd($("#btnVues").dataset.usd);
  if (!await confirmer(`Générer ${n} vue(s) de « ${fn} » (Seedream) : ${prix}.\nAucun moteur 3D ne tourne à cette étape : tu `
    + `regardes, rejoues ou détoures les vues, PUIS tu tires.`, { titre: "Vues d'abord", ok: `Payer ${prix}` })) return;
  const r = await jpost("/api/assets/3d/views", { image_filename: fn, engine: moteur, views: n,
    subject: $("#vuesSujet").value.trim() || undefined });
  V.jeu = r.job;
  suivre(r.job_id, "vues en préparation…", async (j) => {
    await charger();
    if (j.status !== "done") $("#vuesEtat").textContent = `échec : ${j.error || "?"}`;
  });
}

/* T7 : les vues viennent de la planche de la bible — aucune génération, donc aucun dialogue de paiement */
export async function depuisBible(confirmer, toast) {
  const id = $("#vuesEntite").value;
  if (!id) { toast("aucune entité de la bible avec planche"); return; }
  const r = await jpost(`/api/bible/entities/${encodeURIComponent(id)}/model3d`,
    { from_board: true, engine: $("#vuesMoteur").value || "tripo-h3.1" });
  V.jeu = r.job;
  toast(`vues reprises de la planche (${r.source === "recette" ? "panneaux d'origine" : "découpe"}) — gratuit`);
  suivre(r.job_id, "vues de la planche…", async (j) => {
    await charger();
    if (j.status !== "done") $("#vuesEtat").textContent = `échec : ${j.error || "?"}`;
  });
}

export async function ouvrirJeu(job) {
  V.jeu = job || null;
  if (!V.jeu) { montrer(null); return; }
  try { montrer(await jget(`/api/assets/3d/${encodeURIComponent(V.jeu)}/views`)); }
  catch (e) { montrer(null); $("#vuesEtat").textContent = String(e.message || e); }
}

export function montrer(info) {
  V.info = info;
  const grille = $("#vuesGrille");
  const btn = $("#btnTirer");
  if (!info) { grille.innerHTML = ""; btn.disabled = true; btn.textContent = "Tirer · —"; $("#tirRefus").textContent = refusTir(null); return; }
  const fige = info.etat === "tire";
  const t = Date.now();
  grille.innerHTML = info.vues.map((v) => `
    <figure class="vue${v.file ? "" : " vide"}" data-i="${v.index}">
      ${v.file ? `<a href="/api/assets/3d/${encodeURIComponent(info.job)}/shot/${v.index}?t=${t}" target="_blank" rel="noopener" title="Ouvrir la vue en grand"><img src="/api/assets/3d/${encodeURIComponent(info.job)}/shot/${v.index}?t=${t}" alt="vue ${v.index}" loading="lazy"></a>` : `<div class="vue-trou">vue absente</div>`}
      <figcaption title="${esc(v.origine || "")}">${v.role === "source" ? "source" : esc(v.cle || `vue ${v.index}`)}${v.role === "planche" ? " · planche" : ""}${v.rejeux ? ` · ${v.rejeux}↻` : ""}${v.detoure ? ` · ✂ ${esc(v.detoure)}` : ""}${v.erreur ? ` · <b class="fal-refus" title="${esc(v.erreur)}">ratée</b>` : ""}</figcaption>
      ${v.role === "source" || fige ? "" : `<div class="vue-actions">
        ${v.role === "planche" ? "" : `<button class="v-rej" data-i="${v.index}" title="Régénérer CETTE vue seulement, avec un prompt corrigé">↻</button>`}
        <button class="v-det" data-i="${v.index}" ${v.file ? "" : "disabled"} title="Retirer le fond — local, gratuit">✂</button></div>`}
    </figure>`).join("");
  const non = refusTir(info, V.occupe);
  btn.disabled = !!non;
  btn.textContent = fige ? "Déjà tiré" : `Tirer · ${info.engine}`;
  btn.title = non || "Lancer le moteur 3D sur ces vues";
  $("#tirRefus").textContent = non;
}

export async function rejouer(i, saisir, toast) {
  const v = V.info && V.info.vues[i];
  if (!v) return;
  const d = await devis({ kind: "asset3d_views", views: 1 });
  const prompt = await saisir(`Prompt de la vue ${i} (${v.cle || ""}) — Seedream, ${usd(d.total_usd)} :`,
    { titre: `Rejouer la vue ${i}`, valeur: v.prompt || "", ok: `Payer ${usd(d.total_usd)}` });
  if (prompt === null) return;
  if (!prompt.trim()) { toast("un prompt vide ne se rejoue pas"); return; }
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(V.jeu)}/views/${i}/rejouer`, { prompt: prompt.trim() });
  suivre(r.job_id, `vue ${i} en cours…`, async (j) => {
    await ouvrirJeu(V.jeu);
    if (j.status !== "done") $("#vuesEtat").textContent = `échec : ${j.error || "?"}`;
  });
}

export async function detourer(i, toast) {
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(V.jeu)}/views/${i}/detourer`, { via: "local" });
  toast(`vue ${i} détourée (local, gratuit${r.methode ? ` · ${r.methode}` : ""})`);
  await ouvrirJeu(V.jeu);
}

export async function tirer(confirmer, toast) {
  const info = V.info;
  const non = refusTir(info, V.occupe);
  if (non) { toast(non); return; }
  const p = info.payload || {};
  const d = await devis({ kind: "asset3d", engine: info.engine, textures: p.textures !== false, quality: p.quality || "",
    formats: p.formats || ["glb"], geometry_detaillee: p.geometry_detaillee, quad: p.quad });
  /* ce qui part VRAIMENT : le moteur plafonne ses images (max_images du registre) — vu à l'écran le 06/10, le
     message annonçait 5 images quand Tripo v2.5 en prend 4 */
  const gardees = info.vues.filter((v) => v.file).length;
  const max = Number((V.moteurs.find((m) => m.id === info.engine) || {}).max_images) || 0;
  const part = max && max < gardees ? `${max} des ${gardees} images validées (${info.engine} en prend au plus ${max})`
    : `${gardees} image(s) validée(s)`;
  if (!await confirmer(`Tirer ${info.engine} sur ${part} : ${usd(d.total_usd)}.\n`
    + (info.vues.every((v) => v.role === "planche")
      ? "Les vues viennent de la planche (aucune génération) : seul le moteur est facturé."
      : "Les vues sont déjà payées : seul le moteur est facturé.")
    + (info.entity_id ? `
Le maillage rejoindra la fiche de l'entité de la bible.` : ""), { titre: "Tirer le maillage", ok: `Payer ${usd(d.total_usd)}` })) return;
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(V.jeu)}/tirer`, {});
  suivre(r.job_id, "moteur en cours…", async (j) => {
    await charger();
    $("#vuesEtat").textContent = j.status === "done"
      ? "maillage prêt — dans la liste de l'atelier ci-dessus et dans Game Assets 3D" : `échec : ${j.error || "?"}`;
    if (j.status === "done" && V.onTire) V.onTire(V.jeu);
  });
}

export function suivre(jobId, libelle, onDone) {
  clearInterval(V.poll);
  V.occupe = true;
  if (V.info) montrer(V.info);
  $("#vuesEtat").textContent = libelle;
  V.poll = setInterval(async () => {
    const j = await jget(`/api/jobs/${jobId}`).catch(() => null);
    if (!j) return;
    $("#vuesEtat").textContent = `${j.current_step || ""} ${j.progress || 0} %`;
    if (j.status === "done" || j.status === "failed") {
      clearInterval(V.poll);
      V.occupe = false;
      await onDone(j);
    }
  }, 2000);
}

export function brancher({ confirmer, saisir, toast, onTire }) {
  V.onTire = onTire;
  const garde = (f) => () => f().catch((e) => toast(String(e.message || e)));
  $("#btnVues").addEventListener("click", garde(() => preparer(confirmer, toast)));
  $("#btnTirer").addEventListener("click", garde(() => tirer(confirmer, toast)));
  $("#btnVuesBible").addEventListener("click", garde(() => depuisBible(confirmer, toast)));
  $("#vuesN").addEventListener("change", garde(prixPreparer));
  $("#vuesImg").addEventListener("change", garde(prixPreparer));
  $("#vuesJeu").addEventListener("change", (ev) => ouvrirJeu(ev.target.value).catch((e) => toast(String(e.message || e))));
  $("#vuesGrille").addEventListener("click", (ev) => {
    const b = ev.target.closest && ev.target.closest("button[data-i]");
    if (!b || b.disabled) return;
    const i = Number(b.dataset.i);
    if (b.classList.contains("v-rej")) garde(() => rejouer(i, saisir, toast))();
    else if (b.classList.contains("v-det")) garde(() => detourer(i, toast))();
  });
}
