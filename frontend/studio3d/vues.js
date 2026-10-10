/* Vues d'abord — T106 (plan-moteurs-3d T6, R10e P5) : les vues d'un maillage se regardent, se rejouent une à une et
   se détourent AVANT de payer le moteur. Une vue ratée (bras coupé, fond sale, profil de trois quarts) ne coûte plus
   deux fois : la vue, puis le maillage qu'elle abîme.
   Le prix de chaque geste payant vient du devis du backend (POST /api/cost/estimate, le même calcul que la garde des
   plafonds) et se CONFIRME ; le détourage local est gratuit et part sans question. Le bouton « Tirer » se grise et
   DIT pourquoi (déjà tiré, aucune vue, une opération en cours). */
"use strict";
import { jget, jpost, ico, libeller } from "./fal.js";

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
  if (!info) return __dzT9("studio3d.s3b_vues.refus_aucun", "aucun jeu de vues choisi");
  if (info.etat === "tire") return __dzT9("studio3d.s3b_vues.refus_tire", "déjà tiré : le maillage existe — prépare un nouveau jeu pour retirer");
  if (occupe) return __dzT9("studio3d.s3b_vues.refus_occupe", "une opération tourne sur ce jeu — attends qu'elle finisse");
  if (!(info.vues || []).some((v) => v.file)) return __dzT9("studio3d.s3b_vues.refus_vide", "aucune vue exploitable : rejoue-en au moins une");
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
    ? V.entites.map((e) => `<option value="${esc(e.id)}"${e.id === ent ? " selected" : ""}>${esc(e.name)} · ${e.kind === "character" ? __dzT9("studio3d.s3b_vues.personnage", "personnage") : __dzT9("studio3d.s3b_vues.objet", "objet")}${e.model3d_job ? __dzT9("studio3d.s3b_vues.a_maillage", " · a déjà un maillage") : ""}</option>`).join("")
    : `<option value="">${__dzT9("studio3d.s3b_vues.aucune_entite", "aucune entité avec planche")}</option>`;
  $("#btnVuesBible").disabled = !V.entites.length;
  /* T107 (T11) : des photos réelles — celles du téléphone (source « mobile », déposées par la synchro) EN TÊTE ; la
     face est exigée, les autres vues sont facultatives ; recharger garde les choix */
  const toutes = im.images || [];   // pas V.images : il n'est rempli qu'après ce bloc (vu au banc)
  /* icônes (10/10) : une <option> ne peut pas porter d'icône dessinée — l'origine « téléphone » est dite par un
     groupe <optgroup> en tête (et par l'icône dz-etat-mobile de la légende), plus par un emoji collé au nom */
  const tel = toutes.filter((x) => x.source === "mobile"), bib = toutes.filter((x) => x.source !== "mobile");
  for (const [id, facultatif] of [["photoFront", false], ["photoBack", true], ["photoLeft", true], ["photoRight", true]]) {
    const garde = $("#" + id).value;
    const opt = (x) => `<option value="${esc(x.filename)}"${x.filename === garde ? " selected" : ""}>${esc(x.filename)}</option>`;
    $("#" + id).innerHTML = (facultatif ? `<option value="">—</option>` : "")
      + (tel.length ? `<optgroup label="${__dzT9("studio3d.s3b_vues.telephone", "Téléphone")}">${tel.map(opt).join("")}</optgroup>` : "")
      + (tel.length && bib.length ? `<optgroup label="${__dzT9("studio3d.s3b_vues.bibliotheque", "Bibliothèque")}">${bib.map(opt).join("")}</optgroup>` : bib.map(opt).join(""));
  }
  V.images = im.images || [];
  V.moteurs = en.engines || [];
  V.jeux = je.jeux || [];
  /* recharger GARDE le choix de l'utilisateur (vu à l'écran le 06/10 : il revenait au premier) */
  const img = $("#vuesImg").value, mot = $("#vuesMoteur").value || en.default || "tripo";
  $("#vuesImg").innerHTML = V.images.length
    ? V.images.map((x) => `<option value="${esc(x.filename)}"${x.filename === img ? " selected" : ""}>${esc(x.filename)}</option>`).join("")
    : `<option value="">${__dzT9("studio3d.s3b_vues.biblio_vide", "Bibliothèque vide")}</option>`;
  /* T107 : un moteur indisponible est grisé avec SA raison (service local absent / clé fal absente), et jamais
     présélectionné : le choix retombe sur le premier disponible */
  const dispo = (m) => m.available !== false;
  const choisi = (V.moteurs.find((m) => m.id === mot && dispo(m)) || V.moteurs.find(dispo) || {}).id;
  $("#vuesMoteur").innerHTML = V.moteurs.map((m) =>
    `<option value="${esc(m.id)}"${m.id === choisi ? " selected" : ""}${dispo(m) ? "" : " disabled"}>${esc(m.label || m.id)} · `
    + `${dispo(m) ? usd(m.usd_texture) : (m.local ? __dzT9("studio3d.s3b_vues.local_absent", "service local absent") : __dzT9("studio3d.s3b_vues.cle_fal_absente", "clé fal absente"))}</option>`).join("");
  dessinerJeux();
  await prixPreparer();
  if (V.jeu || V.jeux[0]) await ouvrirJeu(V.jeu || V.jeux[0].job);
  else montrer(null);
}

function dessinerJeux() {
  const sel = $("#vuesJeu");
  sel.innerHTML = V.jeux.length
    ? V.jeux.map((j) => `<option value="${esc(j.job)}"${j.job === V.jeu ? " selected" : ""}>${esc(j.image_filename)} · ${esc(j.engine)} · ${j.etat === "tire" ? __dzT9("studio3d.s3b_vues.tire", "tiré") : __dzT9("studio3d.s3b_vues.en_attente", "en attente")}${j.ratees ? ` · ${__dzT9("studio3d.s3b_vues.ratees", "{n} ratée(s)", { n: j.ratees })}` : ""}</option>`).join("")
    : `<option value="">${__dzT9("studio3d.s3b_vues.aucun_jeu", "aucun jeu de vues")}</option>`;
}

export async function prixPreparer() {
  const n = Math.max(1, Math.min(4, Number($("#vuesN").value) || 4));
  const btn = $("#btnVues");
  try {
    const d = await devis({ kind: "asset3d_views", views: n });
    libeller(btn, "dz-lab3d-generer-modele", n > 1 ? __dzT9("studio3d.s3b_vues.preparer.plusieurs", "Préparer {n} vues · {prix}", { n: n, prix: usd(d.total_usd) }) : __dzT9("studio3d.s3b_vues.preparer.un", "Préparer {n} vue · {prix}", { n: n, prix: usd(d.total_usd) }));
    btn.dataset.usd = d.total_usd;
  } catch (e) { libeller(btn, "dz-lab3d-generer-modele", __dzT9("studio3d.s3b_vues.preparer_sans_prix", "Préparer {n} vues", { n: n })); delete btn.dataset.usd; }
  btn.disabled = !$("#vuesImg").value;
}

export async function preparer(confirmer, toast) {
  const fn = $("#vuesImg").value;
  if (!fn) { toast(__dzT9("studio3d.s3b_vues.choisis_image", "choisis une image de la Bibliothèque")); return; }
  const n = Math.max(1, Math.min(4, Number($("#vuesN").value) || 4));
  const moteur = $("#vuesMoteur").value || "tripo";
  const prix = usd($("#btnVues").dataset.usd);
  if (!await confirmer(__dzT9("studio3d.s3b_vues.confirmer_preparer", "Générer {n} vue(s) de « {fn} » (Seedream) : {prix}.\nAucun moteur 3D ne tourne à cette étape : tu regardes, rejoues ou détoures les vues, PUIS tu tires.", { n: n, fn: fn, prix: prix }), { titre: __dzT9("studio3d.s3b_vues.titre", "Vues d'abord"), ok: __dzT9("studio3d.s3b.payer", "Payer {prix}", { prix: prix }) })) return;
  const r = await jpost("/api/assets/3d/views", { image_filename: fn, engine: moteur, views: n,
    subject: $("#vuesSujet").value.trim() || undefined });
  V.jeu = r.job;
  suivre(r.job_id, __dzT9("studio3d.s3b_vues.en_preparation", "vues en préparation…"), async (j) => {
    await charger();
    if (j.status !== "done") $("#vuesEtat").textContent = __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" });
  });
}

/* T7 : les vues viennent de la planche de la bible — aucune génération, donc aucun dialogue de paiement */
export async function depuisBible(confirmer, toast) {
  const id = $("#vuesEntite").value;
  if (!id) { toast(__dzT9("studio3d.s3b_vues.aucune_entite_bible", "aucune entité de la bible avec planche")); return; }
  const r = await jpost(`/api/bible/entities/${encodeURIComponent(id)}/model3d`,
    { from_board: true, engine: $("#vuesMoteur").value || "tripo-h3.1" });
  V.jeu = r.job;
  toast(__dzT9("studio3d.s3b_vues.reprises", "vues reprises de la planche ({src}) — gratuit", { src: r.source === "recette" ? __dzT9("studio3d.s3b_vues.panneaux_origine", "panneaux d'origine") : __dzT9("studio3d.s3b_vues.decoupe", "découpe") }));
  suivre(r.job_id, __dzT9("studio3d.s3b_vues.de_la_planche", "vues de la planche…"), async (j) => {
    await charger();
    if (j.status !== "done") $("#vuesEtat").textContent = __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" });
  });
}

/* T107 (T11) : un jeu de vues depuis des photos — aucune génération, donc aucun dialogue de paiement */
export async function depuisPhotos(confirmer, toast) {
  const vues = {};
  for (const [cle, id] of [["front", "photoFront"], ["back", "photoBack"], ["left", "photoLeft"], ["right", "photoRight"]]) {
    if ($("#" + id).value) vues[cle] = $("#" + id).value;
  }
  if (!vues.front) { toast(__dzT9("studio3d.s3b_vues.choisis_face", "choisis au moins la photo de face")); return; }
  const r = await jpost("/api/assets/3d/views/photos",
    { vues, engine: $("#vuesMoteur").value || "tripo-h3.1", detourer: !!$("#photoDetourer").checked });
  V.jeu = r.job;
  toast(__dzT9("studio3d.s3b_vues.depuis_photos", "jeu de vues depuis {n} photo(s) — gratuit", { n: Object.keys(vues).length }));
  suivre(r.job_id, __dzT9("studio3d.s3b_vues.des_photos", "vues depuis les photos…"), async (j) => {
    await charger();
    if (j.status !== "done") $("#vuesEtat").textContent = __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" });
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
  if (!info) { grille.innerHTML = ""; btn.disabled = true; libeller(btn, "dz-lab3d-generer-modele", __dzT9("studio3d.s3b_vues.tirer_vide", "Tirer · —")); $("#tirRefus").textContent = refusTir(null); return; }
  const fige = info.etat === "tire";
  const t = Date.now();
  grille.innerHTML = info.vues.map((v) => `
    <figure class="vue${v.file ? "" : " vide"}" data-i="${v.index}">
      ${v.file ? `<a href="/api/assets/3d/${encodeURIComponent(info.job)}/shot/${v.index}?t=${t}" target="_blank" rel="noopener" title="${__dzT9("studio3d.s3b_vues.ouvrir_grand", "Ouvrir la vue en grand")}"><img src="/api/assets/3d/${encodeURIComponent(info.job)}/shot/${v.index}?t=${t}" alt="${__dzT9("studio3d.s3b_vues.vue_n", "vue {i}", { i: v.index })}" loading="lazy"></a>` : `<div class="vue-trou">${__dzT9("studio3d.s3b_vues.absente", "vue absente")}</div>`}
      <figcaption title="${esc(v.origine || "")}">${v.role === "source" ? "source" : esc(v.cle || __dzT9("studio3d.s3b_vues.vue_n", "vue {i}", { i: v.index }))}${v.role === "planche" ? __dzT9("studio3d.s3b_vues.o_planche", " · planche") : v.role === "photo" ? __dzT9("studio3d.s3b_vues.o_photo", " · photo") : ""}${v.rejeux ? ` · ${v.rejeux}↻` : ""}${v.detoure ? ` · ✂ ${esc(v.detoure)}` : ""}${v.erreur ? ` · <b class="fal-refus" title="${esc(v.erreur)}">${__dzT9("studio3d.s3b_vues.ratee", "ratée")}</b>` : ""}</figcaption>
      ${v.role === "source" || fige ? "" : `<div class="vue-actions">
        ${v.role === "planche" || v.role === "photo" ? "" : `<button class="v-rej" data-i="${v.index}" title="${__dzT9("studio3d.s3b_vues.rej_title", "Régénérer CETTE vue seulement, avec un prompt corrigé")}" aria-label="${__dzT9("studio3d.s3b_vues.rej_aria", "Régénérer cette vue")}">${ico("dz-action-regenerer")}</button>`}
        <button class="v-det" data-i="${v.index}" ${v.file ? "" : "disabled"} title="${__dzT9("studio3d.s3b_vues.det_title", "Retirer le fond — local, gratuit")}" aria-label="${__dzT9("studio3d.s3b_vues.det_aria", "Retirer le fond")}">${ico("dz-action-detourer")}</button></div>`}
    </figure>`).join("");
  const non = refusTir(info, V.occupe);
  btn.disabled = !!non;
  libeller(btn, "dz-lab3d-generer-modele", fige ? __dzT9("studio3d.s3b_vues.deja_tire", "Déjà tiré") : __dzT9("studio3d.s3b_vues.tirer_moteur", "Tirer · {moteur}", { moteur: info.engine }));
  btn.title = non || __dzT9("studio3d.s3b_vues.tirer_title", "Lancer le moteur 3D sur ces vues");
  $("#tirRefus").textContent = non;
}

export async function rejouer(i, saisir, toast) {
  const v = V.info && V.info.vues[i];
  if (!v) return;
  const d = await devis({ kind: "asset3d_views", views: 1 });
  const prompt = await saisir(__dzT9("studio3d.s3b_vues.prompt_vue", "Prompt de la vue {i} ({cle}) — Seedream, {prix} :", { i: i, cle: v.cle || "", prix: usd(d.total_usd) }),
    { titre: __dzT9("studio3d.s3b_vues.rejouer_titre", "Rejouer la vue {i}", { i: i }), valeur: v.prompt || "", ok: __dzT9("studio3d.s3b.payer", "Payer {prix}", { prix: usd(d.total_usd) }) });
  if (prompt === null) return;
  if (!prompt.trim()) { toast(__dzT9("studio3d.s3b_vues.prompt_vide", "un prompt vide ne se rejoue pas")); return; }
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(V.jeu)}/views/${i}/rejouer`, { prompt: prompt.trim() });
  suivre(r.job_id, __dzT9("studio3d.s3b_vues.vue_en_cours", "vue {i} en cours…", { i: i }), async (j) => {
    await ouvrirJeu(V.jeu);
    if (j.status !== "done") $("#vuesEtat").textContent = __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" });
  });
}

export async function detourer(i, toast) {
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(V.jeu)}/views/${i}/detourer`, { via: "local" });
  toast(__dzT9("studio3d.s3b_vues.detouree", "vue {i} détourée (local, gratuit{m})", { i: i, m: r.methode ? ` · ${r.methode}` : "" }));
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
  const part = max && max < gardees ? __dzT9("studio3d.s3b_vues.part_max", "{max} des {n} images validées ({moteur} en prend au plus {max})", { max: max, n: gardees, moteur: info.engine })
    : __dzT9("studio3d.s3b_vues.part", "{n} image(s) validée(s)", { n: gardees });
  if (!await confirmer(__dzT9("studio3d.s3b_vues.confirmer_tir", "Tirer {moteur} sur {part} : {prix}.", { moteur: info.engine, part: part, prix: usd(d.total_usd) }) + "\n"
    + (info.vues.every((v) => v.role === "planche" || v.role === "photo")
      ? (info.vues.some((v) => v.role === "photo") ? __dzT9("studio3d.s3b_vues.gratuites_photos", "Les vues viennent de photos (aucune génération) : seul le moteur est facturé.") : __dzT9("studio3d.s3b_vues.gratuites_planche", "Les vues viennent de la planche (aucune génération) : seul le moteur est facturé."))
      : __dzT9("studio3d.s3b_vues.deja_payees", "Les vues sont déjà payées : seul le moteur est facturé."))
    + (info.entity_id ? "\n" + __dzT9("studio3d.s3b_vues.rejoindra", "Le maillage rejoindra la fiche de l'entité de la bible.") : ""), { titre: __dzT9("studio3d.s3b_vues.titre_tir", "Tirer le maillage"), ok: __dzT9("studio3d.s3b.payer", "Payer {prix}", { prix: usd(d.total_usd) }) })) return;
  const r = await jpost(`/api/assets/3d/${encodeURIComponent(V.jeu)}/tirer`, {});
  suivre(r.job_id, __dzT9("studio3d.s3b_vues.moteur_en_cours", "moteur en cours…"), async (j) => {
    await charger();
    $("#vuesEtat").textContent = j.status === "done"
      ? __dzT9("studio3d.s3b_vues.maillage_pret", "maillage prêt — dans la liste de l'atelier ci-dessus et dans Game Assets 3D") : __dzT9("studio3d.s3b.echec", "échec : {e}", { e: j.error || "?" });
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
  $("#btnVuesPhotos").addEventListener("click", garde(() => depuisPhotos(confirmer, toast)));
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
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
