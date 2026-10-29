/* t343 (lot Scenario B8, 29/10/2026) — UN MOUVEMENT SUR LE RIG, et les HITBOXES sur les os pour Godot.

   Module À PART d'etabli.js (régénéré par la traduction L8 : toute retouche à la main ferait rougir son --check),
   comme jeu.js (t342). Il lit l'état exporté (S.a : le job et la version affichés), rouvre une version par
   `ouvrirPrincipale`, et pose #panMouvement SOUS le panneau Rig (montré avec l'onglet Rig) :
   - les SOURCES d'un mouvement : un fichier BVH / GLB importé, une vidéo captée par Uthana (payant : devis sur le
     bouton, confirmation, puis plafonds par dz-plafonds), un clip Meshy du job, ou un clip de la version (retimer) ;
   - le RETIMAGE (nom du clip, rognage, vitesse, boucle, sur place, alignement des poses de repos) et « Appliquer au
     rig » : Python recible, écrit une version de plus, la page l'ouvre et JOUE le clip dans la visionneuse ;
   - l'export GODOT : os cochés → BoneAttachment3D + Area3D + CollisionShape3D, téléchargés en ZIP.
   Rien n'est écrit par le navigateur : Python écrit, versionne et fiche (spec §2.1 de l'Établi). */
"use strict";
import { S, ouvrirPrincipale } from "./etabli.js";

const $ = (s) => document.querySelector(s);
const T = (k, v) => dzT("mouvement3d." + k, v);
const langue = () => (typeof dzLang === "function" && dzLang() === "en" ? "en" : "fr");
const ico = (cle) => `<svg class="dzi dzi--16" aria-hidden="true" focusable="false"><use href="/shared/icons/dz-icons.svg#${cle}"></use></svg>`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const usd = (v) => (langue() === "en" ? `$${Number(v).toFixed(2)}` : `${Number(v).toFixed(2).replace(".", ",")} $`);
const sec = (v) => (v == null ? "—" : `${Number(v).toLocaleString(langue() === "en" ? "en-US" : "fr-FR", { maximumFractionDigits: 2 })} s`);

/* L'état du module. */
const M = {
  cle: "", etat: null, source: null, occupe: false, avis: "", erreur: "", rapport: null,
  rt: { nom: "", debut: "", fin: "", vitesse: 1, boucle: false, fondu: 0.25, en_place: false, aligner: true },
  videos: null, video: null, vDebut: "", vFin: "", devis: null, tache: null, suivi: null, vOuvert: false,
  hb: {},                      // os → {forme, rayon, role}
  aJouer: null,
};

function cible() {
  const a = S.a;
  if (!a) return null;
  return { job: a.job || null, version: Number(a.version) || 1 };
}

async function lireJson(r) {
  const t = await r.text();
  let j = {};
  try { j = t ? JSON.parse(t) : {}; } catch { j = { detail: t }; }
  if (!r.ok) {
    const d = j && j.detail;
    const msg = typeof d === "string" ? d : (d && d.message) || `${r.status}`;
    const e = new Error(msg); e.status = r.status; e.detail = d; throw e;
  }
  return j;
}

async function ouvrirNeuve(job, version) {
  const url = `/api/assets/3d/${job}/version/${version}`;
  const libelle = `version ${version}`;
  const bloc = [...document.querySelectorAll("#chrono .job")].find((s) => s.dataset.job === job);
  const etapes = bloc && bloc.querySelector(".job-etapes");
  if (etapes && ![...etapes.querySelectorAll(".etape")].some((b) => b.dataset.version === String(version))) {
    const b = document.createElement("button");
    b.className = "etape";
    Object.assign(b.dataset, { job, version: String(version), url, libelle });
    b.innerHTML = `<b>${esc(libelle)}</b><span>${esc(T("chrono.neuve"))}</span>`;
    b.addEventListener("click", () => ouvrirPrincipale({ job, meshy: null, version, url, libelle }));
    etapes.appendChild(b);
  }
  await ouvrirPrincipale({ job, meshy: null, version, url, libelle });
}

const cleSource = (s) => (s ? `${s.type}:${s.nom}` : "");
const ORIGINES = { import: "origine.import", uthana: "origine.video", meshy: "origine.meshy", clip: "origine.clip" };

function toutesSources() {
  const e = M.etat;
  if (!e) return [];
  return [...(e.sources || []), ...(e.clips || []).map((c) => ({ type: "clip", nom: c.nom, origine: "clip" }))];
}

/* ── le panneau ─────────────────────────────────────────────────────────── */

function rendre() {
  const box = $("#panMouvement");
  if (!box) return;
  const c = cible();
  let h = `<div class="dt-label">${ico("dz-lab3d-rig")} ${esc(T("panneau.titre"))}</div>`
    + `<div class="mv-note">${esc(T("panneau.intro"))}</div>`;
  if (!c) { box.innerHTML = h + `<div class="vide">${esc(T("panneau.vide"))}</div>`; return; }
  if (!c.job) { box.innerHTML = h + `<div class="vide">${esc(T("panneau.meshy"))}</div>`; return; }
  const e = M.etat;
  if (!e) { box.innerHTML = h + `<div class="vide">${esc(M.erreur || T("panneau.lecture"))}</div>`; return; }
  if (!e.a_squelette) { box.innerHTML = h + `<div class="vide">${esc(T("panneau.sans_squelette"))}</div>`; return; }

  /* 1. la source */
  const srcs = toutesSources();
  h += `<div class="mv-etape">${esc(T("etape.source"))}</div>`;
  h += srcs.length
    ? `<div class="mv-sources" role="radiogroup" aria-label="${esc(T("etape.source"))}">` + srcs.map((s) => `
      <label class="mv-source"><input type="radio" name="mvSource" value="${esc(cleSource(s))}" ${cleSource(s) === cleSource(M.source) ? "checked" : ""}>
        <span class="mv-nom">${esc(s.nom)}</span>
        <span class="mv-badge">${esc(T(ORIGINES[s.origine] || "origine.import"))}</span>
        <span class="mv-duree">${s.secondes != null ? esc(sec(s.secondes)) : ""}</span></label>`).join("") + `</div>`
    : `<div class="vide">${esc(T("sources.vide"))}</div>`;
  h += `<input id="mvFichier" type="file" accept=".bvh,.glb" hidden>`
    + `<div class="mv-actions"><button id="mvImporter" ${M.occupe ? "disabled" : ""}>${ico("dz-action-importer")} ${esc(T("panneau.importer"))}</button>`
    + `<button id="mvVideoOuvrir" class="${M.vOuvert ? "actif" : ""}" aria-expanded="${M.vOuvert}">${ico("dz-media-video")} ${esc(T("video.ouvrir"))}</button></div>`;
  if (M.vOuvert) h += rendreVideo();

  /* 2. le retimage */
  const rt = M.rt;
  h += `<div class="mv-etape">${esc(T("etape.retimage"))}</div>`
    + `<label class="mv-champ mv-large"><span>${esc(T("rt.nom"))}</span><input id="mvNom" type="text" maxlength="48" value="${esc(rt.nom)}" placeholder="${esc(T("rt.nom_exemple"))}"></label>`
    + `<div class="mv-grille">`
    + `<label class="mv-champ"><span>${esc(T("rt.debut"))}</span><input id="mvDebut" type="number" min="0" step="0.05" value="${esc(rt.debut)}" placeholder="0"></label>`
    + `<label class="mv-champ"><span>${esc(T("rt.fin"))}</span><input id="mvFin" type="number" min="0" step="0.05" value="${esc(rt.fin)}" placeholder="${esc(T("rt.fin_vide"))}"></label></div>`
    + `<label class="mv-champ mv-large"><span>${esc(T("rt.vitesse"))} <b id="mvVitesseVal">× ${esc(rt.vitesse)}</b></span>`
    + `<input id="mvVitesse" type="range" min="0.1" max="4" step="0.05" value="${esc(rt.vitesse)}"></label>`
    + `<label class="mv-case"><input id="mvBoucle" type="checkbox" ${rt.boucle ? "checked" : ""}> ${esc(T("rt.boucle"))}</label>`
    + `<label class="mv-case"><input id="mvSurPlace" type="checkbox" ${rt.en_place ? "checked" : ""}> ${esc(T("rt.sur_place"))}</label>`
    + `<label class="mv-case" title="${esc(T("rt.aligner_aide"))}"><input id="mvAligner" type="checkbox" ${rt.aligner ? "checked" : ""}> ${esc(T("rt.aligner"))}</label>`
    + `<div class="mv-actions"><button class="mv-principal" id="mvAppliquer" ${M.occupe || !M.source ? "disabled" : ""}>${ico("dz-lab3d-rig")} ${esc(M.occupe ? T("appliquer.en_cours") : T("panneau.appliquer", { v: c.version }))}</button></div>`;
  if (M.rapport) {
    const r = M.rapport;
    h += `<div class="mv-ok">${esc(T("panneau.rapport", { n: r.relies, t: r.os_cible, p: r.porteur, i: r.images, f: r.fps, c: r.clip }))}</div>`
      + (r.non_relies && r.non_relies.length ? `<div class="mv-avis">${esc(T("rapport.non_relies", { l: r.non_relies.join(", ") }))}</div>` : "");
  }
  if (M.erreur) h += `<div class="mv-erreur" role="alert">${esc(M.erreur)}</div>`;
  if (M.avis) h += `<div class="mv-ok">${esc(M.avis)}</div>`;

  /* 3. Godot */
  h += rendreGodot(e);
  box.innerHTML = h;
  brancher(box);
}

function rendreVideo() {
  const e = M.etat;
  const v = e.video || {};
  let h = `<div class="mv-video"><div class="mv-ia-tete">${ico("dz-etat-ia")} ${esc(T("video.titre"))}</div>`
    + `<div class="mv-note">${esc(T("video.intro", { p: usd(v.usd_seconde || 0), a: v.duree_min || 2, b: v.duree_max || 60 }))}</div>`;
  if (!v.cle) {
    h += `<div class="mv-avis">${esc(T("video.sans_cle"))}</div>`
      + `<div class="mv-cle"><input id="mvCle" type="password" autocomplete="off" spellcheck="false" placeholder="${esc(T("video.cle_place"))}" aria-label="${esc(T("video.cle_place"))}">`
      + `<button id="mvCleOk">${esc(T("video.cle_poser"))}</button></div>`;
  }
  if (M.videos === null) h += `<div class="vide">${esc(T("video.chargement"))}</div>`;
  else {
    h += `<label class="mv-champ mv-large"><span>${esc(T("video.choisir"))}</span><select id="mvVideo"><option value="">${esc(T("video.aucune"))}</option>`
      + M.videos.map((x) => `<option value="${esc(x.job_id)}" ${M.video === x.job_id ? "selected" : ""}>${esc(x.titre)} · ${esc(sec(x.secondes))} · ${esc(T("video.origine." + x.origine))}</option>`).join("")
      + `</select></label>`
      + `<input id="mvVideoFichier" type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm,.m4v,.avi" hidden>`
      + `<div class="mv-actions"><button id="mvVideoImporter">${ico("dz-action-importer")} ${esc(T("video.importer"))}</button></div>`;
  }
  if (M.video) {
    h += `<div class="mv-grille"><label class="mv-champ"><span>${esc(T("rt.debut"))}</span><input id="mvVDebut" type="number" min="0" step="0.1" value="${esc(M.vDebut)}" placeholder="0"></label>`
      + `<label class="mv-champ"><span>${esc(T("rt.fin"))}</span><input id="mvVFin" type="number" min="0" step="0.1" value="${esc(M.vFin)}" placeholder="${esc(T("rt.fin_vide"))}"></label></div>`;
    const d = M.devis;
    if (d && d.refus) h += `<div class="mv-avis">${esc(d.refus)}</div>`;
    const prix = d && d.devis ? d.devis.usd : null;
    const ok = d && !d.refus && v.cle && !M.tache;
    h += `<div class="mv-actions"><button class="mv-principal" id="mvVideoLancer" ${ok ? "" : "disabled"}>${ico("dz-etat-ia")} ${esc(prix == null ? T("video.devis_en_cours") : T("video.lancer", { p: usd(prix), s: d.devis.secondes }))}</button></div>`;
  }
  if (M.suivi) {
    const s = M.suivi;
    const cle = s.etat === "fini" ? "video.fini" : s.etat === "echec" ? "video.echec" : s.etat === "interrompu" ? "video.interrompu" : "video.en_cours";
    h += `<div class="${s.etat === "echec" || s.etat === "interrompu" ? "mv-erreur" : s.etat === "fini" ? "mv-ok" : "mv-note"}" role="status">${esc(T(cle, { m: s.erreur || "", n: (s.source && s.source.nom) || "" }))}</div>`;
  }
  return h + `</div>`;
}

function rendreGodot(e) {
  const os = e.os || [];
  const choisis = Object.keys(M.hb).filter((n) => os.some((o) => o.nom === n));
  let h = `<div class="mv-etape mv-godot-tete">${esc(T("godot.titre"))}</div>`
    + `<div class="mv-note">${esc(T("godot.intro"))}</div>`
    + `<div class="mv-actions"><button id="mvHbMembres">${ico("dz-lab3d-os")} ${esc(T("godot.membres"))}</button>`
    + `<button id="mvHbAucun" ${choisis.length ? "" : "disabled"}>${esc(T("godot.aucun"))}</button></div>`
    + `<div class="mv-os">` + os.map((o) => {
      const c = M.hb[o.nom];
      return `<div class="mv-os-ligne ${c ? "on" : ""}"><label><input type="checkbox" data-os="${esc(o.nom)}" ${c ? "checked" : ""}> <span>${esc(o.nom)}</span></label>`
        + (c ? `<select data-os="${esc(o.nom)}" data-champ="role" aria-label="${esc(T("godot.role"))}">${["hurt", "hit"].map((r) => `<option value="${r}" ${c.role === r ? "selected" : ""}>${esc(T("godot.role." + r))}</option>`).join("")}</select>`
          + `<select data-os="${esc(o.nom)}" data-champ="forme" aria-label="${esc(T("godot.forme"))}">${["capsule", "boite"].map((f) => `<option value="${f}" ${c.forme === f ? "selected" : ""}>${esc(T("godot.forme." + f))}</option>`).join("")}</select>`
          + `<input type="number" min="0.05" max="1" step="0.05" value="${esc(c.rayon)}" data-os="${esc(o.nom)}" data-champ="rayon" title="${esc(T("godot.rayon"))}" aria-label="${esc(T("godot.rayon"))}">`
          : "") + `</div>`;
    }).join("") + `</div>`
    + `<div class="mv-actions"><button class="mv-principal" id="mvGodot" ${choisis.length && !M.occupe ? "" : "disabled"}>${ico("dz-action-telecharger")} ${esc(T("godot.exporter", { n: choisis.length }))}</button></div>`;
  return h;
}

function brancher(box) {
  const on = (id, ev, f) => { const b = box.querySelector("#" + id); if (b) b.addEventListener(ev, f); };
  box.querySelectorAll('input[name="mvSource"]').forEach((r) => r.addEventListener("change", () => {
    M.source = toutesSources().find((s) => cleSource(s) === r.value) || null;
    if (M.source && !M.rt.nom) M.rt.nom = M.source.nom.replace(/\.(bvh|glb)$/i, "");
    M.rapport = null; rendre();
  }));
  on("mvImporter", "click", () => box.querySelector("#mvFichier").click());
  on("mvFichier", "change", (ev) => importer(ev.target.files && ev.target.files[0]));
  on("mvVideoOuvrir", "click", () => { M.vOuvert = !M.vOuvert; if (M.vOuvert) lireVideos(); rendre();   /* relue à chaque ouverture : une prise du téléphone a pu arriver */ });
  const lire = () => {
    const g = (id) => box.querySelector("#" + id);
    M.rt.nom = g("mvNom").value; M.rt.debut = g("mvDebut").value; M.rt.fin = g("mvFin").value;
    M.rt.vitesse = Number(g("mvVitesse").value); M.rt.boucle = g("mvBoucle").checked;
    M.rt.en_place = g("mvSurPlace").checked; M.rt.aligner = g("mvAligner").checked;
  };
  ["mvNom", "mvDebut", "mvFin", "mvBoucle", "mvSurPlace", "mvAligner"].forEach((id) => on(id, "change", lire));
  on("mvVitesse", "input", () => { lire(); const b = box.querySelector("#mvVitesseVal"); if (b) b.textContent = `× ${M.rt.vitesse}`; });
  on("mvAppliquer", "click", () => { lire(); appliquer(); });
  on("mvCleOk", "click", poserCle);
  on("mvVideo", "change", (ev) => { M.video = ev.target.value || null; M.vDebut = M.vFin = ""; M.devis = null; M.suivi = null; rendre(); deviser(); });
  on("mvVideoImporter", "click", () => box.querySelector("#mvVideoFichier").click());
  on("mvVideoFichier", "change", (ev) => importerVideo(ev.target.files && ev.target.files[0]));
  const bornes = () => { M.vDebut = box.querySelector("#mvVDebut").value; M.vFin = box.querySelector("#mvVFin").value; deviser(); };
  on("mvVDebut", "change", bornes);
  on("mvVFin", "change", bornes);
  on("mvVideoLancer", "click", capterVideo);
  on("mvHbMembres", "click", () => {
    for (const o of (M.etat.os || [])) if (o.role && !/orteil|epaule/.test(o.role)) M.hb[o.nom] = M.hb[o.nom] || { forme: "capsule", rayon: 0.25, role: /main|pied/.test(o.role) ? "hit" : "hurt" };
    rendre();
  });
  on("mvHbAucun", "click", () => { M.hb = {}; rendre(); });
  box.querySelectorAll('.mv-os input[type="checkbox"]').forEach((cb) => cb.addEventListener("change", () => {
    if (cb.checked) M.hb[cb.dataset.os] = { forme: "capsule", rayon: 0.25, role: "hurt" }; else delete M.hb[cb.dataset.os];
    rendre();
  }));
  box.querySelectorAll(".mv-os [data-champ]").forEach((el) => el.addEventListener("change", () => {
    const c = M.hb[el.dataset.os];
    if (c) c[el.dataset.champ] = el.dataset.champ === "rayon" ? Number(el.value) : el.value;
  }));
  on("mvGodot", "click", exporterGodot);
}

/* ── les actions ────────────────────────────────────────────────────────── */

async function lireEtat() {
  const c = cible();
  if (!c || !c.job) { M.etat = null; rendre(); return; }
  try {
    M.etat = await lireJson(await fetch(`/api/etabli/mouvement?job=${encodeURIComponent(c.job)}&version=${c.version}`));
    M.erreur = "";
    if (M.source && !toutesSources().some((s) => cleSource(s) === cleSource(M.source))) M.source = null;
  } catch (e) {
    M.etat = null; M.erreur = T("panneau.echec", { m: e.message });
  }
  rendre();
  jouerEnAttente();
}

async function importer(f) {
  const c = cible();
  if (!f || !c || !c.job || M.occupe) return;
  M.occupe = true; M.erreur = M.avis = ""; rendre();
  try {
    const fd = new FormData();
    fd.append("job", c.job); fd.append("fichier", f);
    const r = await lireJson(await fetch("/api/etabli/mouvement/importer", { method: "POST", body: fd }));
    M.source = { ...r.source, origine: "import" };
    M.rt.nom = M.rt.nom || r.source.nom.replace(/\.(bvh|glb)$/i, "");
    M.avis = T("panneau.importe", { n: r.source.nom, i: r.fiche.images, s: sec(r.fiche.secondes) });
  } catch (e) {
    M.erreur = T("panneau.echec", { m: e.message });
  } finally {
    M.occupe = false;
  }
  await lireEtat();
}

const nombreOuRien = (v) => (v === "" || v == null ? undefined : Number(v));

async function appliquer() {
  const c = cible();
  if (!c || !c.job || !M.source || M.occupe) return;
  const rt = M.rt;
  const nom = (rt.nom || "").trim() || M.source.nom.replace(/\.(bvh|glb)$/i, "");
  M.occupe = true; M.erreur = M.avis = ""; M.rapport = null; rendre();
  try {
    const r = await lireJson(await fetch("/api/etabli/mouvement/appliquer", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job: c.job, version: c.version, source: { type: M.source.type, nom: M.source.nom }, nom, aligner: rt.aligner,
        retimage: { debut: nombreOuRien(rt.debut), fin: nombreOuRien(rt.fin), vitesse: rt.vitesse, boucle: rt.boucle,
          fondu: rt.fondu, en_place: rt.en_place },
      }),
    }));
    M.rapport = r.source || null;          /* la fiche de la version : `source` porte le rapport du reciblage */
    M.avis = T("panneau.ecrit", { v: r.version, c: nom });
    M.aJouer = nom;
    M.occupe = false;
    await ouvrirNeuve(c.job, r.version);
  } catch (e) {
    M.erreur = T("panneau.echec", { m: e.message });
  } finally {
    M.occupe = false; rendre();
  }
}

/* Le clip neuf JOUE dans la visionneuse : le panneau Rig (etabli.js) le liste après le chargement ; on clique son
   bouton (même geste que l'utilisateur), l'onglet Rig étant celui qui est ouvert. */
function jouerEnAttente() {
  if (!M.aJouer) return;
  const nom = M.aJouer;
  let essais = 0;
  const t = setInterval(() => {
    const b = [...document.querySelectorAll("#rigClips .clip")].find((x) => x.firstChild && x.firstChild.textContent.trim() === nom);
    if (b || ++essais > 40) { clearInterval(t); if (b) { b.click(); M.aJouer = null; } }
  }, 150);
}

async function poserCle() {
  const champ = $("#mvCle");
  const v = champ && champ.value.trim();
  if (!v) return;
  try {
    await lireJson(await fetch("/api/etabli/mouvement/cle", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ valeur: v }),
    }));
    champ.value = "";
    M.avis = T("video.cle_ok");
  } catch (e) {
    M.erreur = T("panneau.echec", { m: e.message });
  }
  await lireEtat();
  deviser();
}

async function lireVideos() {
  try {
    M.videos = (await lireJson(await fetch("/api/etabli/mouvement/videos"))).videos || [];
  } catch (e) {
    M.videos = []; M.erreur = T("panneau.echec", { m: e.message });
  }
  rendre();
}

async function importerVideo(f) {
  if (!f) return;
  M.erreur = ""; M.avis = T("video.envoi"); rendre();
  try {
    const fd = new FormData();
    fd.append("file", f);
    const r = await lireJson(await fetch("/api/videos/upload", { method: "POST", body: fd }));
    M.avis = "";
    M.videos = null;
    await lireVideos();
    M.video = r.job_id || r.id || null;
    rendre();
    deviser();
  } catch (e) {
    M.avis = ""; M.erreur = T("panneau.echec", { m: e.message }); rendre();
  }
}

let _devisN = 0;
async function deviser() {
  const c = cible();
  if (!c || !c.job || !M.video) return;
  const n = ++_devisN;
  const q = new URLSearchParams({ job: c.job, clip_id: M.video });
  if (M.vDebut !== "") q.set("debut", M.vDebut);
  if (M.vFin !== "") q.set("fin", M.vFin);
  try {
    const d = await lireJson(await fetch(`/api/etabli/mouvement/video/devis?${q}`));
    if (n === _devisN) M.devis = d;
  } catch (e) {
    if (n === _devisN) M.devis = { refus: e.message, devis: null };
  }
  rendre();
}

async function capterVideo() {
  const c = cible();
  const d = M.devis;
  if (!c || !c.job || !M.video || !d || !d.devis || d.refus) return;
  const D_ = window.__dzDialogue;
  /* Le devis AVANT l'envoi, par le dialogue maison : refus par défaut (le sens sûr, comme dz-plafonds). */
  if (!D_ || !(await D_.confirmer(T("video.confirmer", { p: usd(d.devis.usd), s: d.devis.secondes }),
    { titre: T("video.titre"), ok: T("video.ok", { p: usd(d.devis.usd) }) }))) return;
  M.erreur = ""; M.suivi = { etat: "prepare" }; rendre();
  try {
    const corps = { job: c.job, clip_id: M.video, confirme_cout: true, nom: (M.rt.nom || "").trim() || undefined };
    if (M.vDebut !== "") corps.debut = Number(M.vDebut);
    if (M.vFin !== "") corps.fin = Number(M.vFin);
    const r = await lireJson(await fetch("/api/etabli/mouvement/video", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps),
    }));
    M.tache = r.tache;
    suivre(c.job, r.tache);
  } catch (e) {
    M.suivi = null;
    M.erreur = e.status === 503 ? T("video.sans_cle") : T("panneau.echec", { m: e.message });
    rendre();
  }
}

function suivre(job, tache) {
  const t = setInterval(async () => {
    try {
      const e = await lireJson(await fetch(`/api/etabli/mouvement/video/etat?job=${encodeURIComponent(job)}&tache=${tache}`));
      M.suivi = e;
      if (["fini", "echec", "interrompu"].includes(e.etat)) {
        clearInterval(t); M.tache = null;
        if (e.etat === "fini" && e.source) { M.source = { ...e.source, origine: "uthana" }; await lireEtat(); return; }
      }
    } catch (err) {
      clearInterval(t); M.tache = null; M.suivi = { etat: "echec", erreur: err.message };
    }
    rendre();
  }, 3000);
}

async function exporterGodot() {
  const c = cible();
  const hitboxes = Object.entries(M.hb).map(([os, v]) => ({ os, forme: v.forme, rayon: Number(v.rayon) || 0.25, role: v.role }));
  if (!c || !c.job || !hitboxes.length) return;
  M.occupe = true; M.erreur = M.avis = ""; rendre();
  try {
    const r = await fetch("/api/etabli/mouvement/godot", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: c.job, version: c.version, hitboxes, nom: "Personnage" }),
    });
    if (!r.ok) await lireJson(r);
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${c.job}_v${c.version}_godot.zip`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    M.avis = T("godot.ok", { n: r.headers.get("X-DZ-Hitboxes") || hitboxes.length, c: r.headers.get("X-DZ-Clips") || 0 });
  } catch (e) {
    M.erreur = T("panneau.echec", { m: e.message });
  } finally {
    M.occupe = false; rendre();
  }
}

/* ── branchements ───────────────────────────────────────────────────────── */

/* #panMouvement suit l'onglet Rig : etabli.js ne le connaît pas (sa table PANNEAUX en a quatre). */
function suivreOnglets() {
  const pan = $("#panMouvement");
  for (const b of document.querySelectorAll(".onglets .on")) {
    b.addEventListener("click", () => pan && pan.classList.toggle("hidden", b.dataset.onglet !== "rig"));
  }
}

document.addEventListener("etabli:charge", () => {
  const c = cible();
  const cle = c && c.job ? `${c.job}#${c.version}` : "";
  if (cle !== M.cle) {
    const memeJob = c && M.cle.split("#")[0] === c.job;
    M.cle = cle; M.erreur = "";
    if (!memeJob) { M.source = null; M.rapport = null; M.hb = {}; M.video = null; M.devis = null; M.suivi = null; }
  }
  lireEtat();
});

suivreOnglets();
rendre();

export { M, rendre };
