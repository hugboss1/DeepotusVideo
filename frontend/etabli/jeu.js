/* t342 (lot Scenario B6 + B7, 29/10/2026) — PIÈCES MOBILES et BUDGETS DE TRIANGLES dans l'Établi.

   Module À PART d'etabli.js, et c'est voulu : etabli.js est régénéré par la traduction L8
   (scripts/i18n_l8_generer.py --check le compare à sa base) ; toute retouche à la main le ferait rougir. Ce module
   lit l'état exporté (S.a : le job et la version affichés) et rouvre une version par `ouvrirPrincipale`, comme
   ecrireVersion le fait. Il pose deux blocs :
   - #panPieces, SOUS le panneau Parties (montré quand l'onglet Parties est actif) : analyser les îlots (gratuit),
     renommer, « Séparer en N pièces » (une version de plus), ou la segmentation IA Tripo (payante, devis affiché
     sur le bouton, confirmation, puis plafonds par dz-plafonds) ;
   - #panDensites, dans l'onglet Export : un rôle (budgets motivés par le serveur), trois densités, le tableau
     mesuré (triangles, cible, taille, IoU) et les téléchargements.
   Rien n'est écrit par le navigateur : Python écrit, versionne et fiche (spec §2.1 de l'Établi). */
"use strict";
import { S, ouvrirPrincipale } from "./etabli.js";

const $ = (s) => document.querySelector(s);
const T = (k, v) => dzT("pieces3d." + k, v);
const langue = () => (typeof dzLang === "function" && dzLang() === "en" ? "en" : "fr");
const ico = (cle) => `<svg class="dzi dzi--16" aria-hidden="true" focusable="false"><use href="/shared/icons/dz-icons.svg#${cle}"></use></svg>`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nb = (n) => Number(n || 0).toLocaleString(langue() === "en" ? "en-US" : "fr-FR");
const usd = (v) => (langue() === "en" ? `$${Number(v).toFixed(2)}` : `${Number(v).toFixed(2).replace(".", ",")} $`);
const ko = (o) => (o >= 1048576 ? `${(o / 1048576).toFixed(1)} Mo` : `${Math.max(1, Math.round(o / 1024))} Ko`);
const kTri = (n) => (n >= 1000 ? `${(n / 1000).toLocaleString(langue() === "en" ? "en-US" : "fr-FR")} k` : String(n));

/* L'état de ce module — déclaré ICI, comme S et SEL dans etabli.js. */
const P = { analyse: null, cle: "", occupe: false, avis: "", erreur: "" };
const D = { roles: [], role: "heros", resultat: null, occupe: false, erreur: "", job: "" };

function cible() {
  const a = S.a;
  if (!a) return null;
  return { job: a.job || null, version: Number(a.version) || 1, meshy: a.meshy || null };
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

/* La version neuve s'ouvre, et la chronologie l'apprend : un bouton de plus dans le bloc du job, qui rouvre par la
   même porte que les autres (ouvrirPrincipale). Le prochain chargement de la page la redessinera en entier. */
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

/* ── B6 : les pièces mobiles ────────────────────────────────────────────── */

function rendrePieces() {
  const box = $("#panPieces");
  if (!box) return;
  const c = cible();
  let h = `<div class="dt-label">${esc(T("pieces.titre"))}</div>`
    + `<div class="jeu-note">${esc(T("pieces.intro"))}</div>`;
  if (!c) {
    box.innerHTML = h + `<div class="vide">${esc(T("pieces.vide"))}</div>`;
    return;
  }
  if (!c.job) {
    box.innerHTML = h + `<div class="vide">${esc(T("pieces.meshy"))}</div>`;
    return;
  }
  const a = P.analyse;
  if (!a) {
    h += `<div class="jeu-actions"><button id="pcAnalyser" ${P.occupe ? "disabled" : ""}>${ico("dz-lab3d-assemblage")} ${esc(P.occupe ? T("pieces.analyse_en_cours") : T("pieces.analyser"))}</button></div>`;
  } else {
    const n = a.pieces.length;
    h += `<div class="jeu-resume">${esc(T("pieces.resume", { n, t: nb(a.triangles) }))}`
      + (a.regroupees ? ` ${esc(T("pieces.regroupees", { n: a.regroupees }))}` : "") + `</div>`;
    if (n <= 1) {
      h += `<div class="vide">${esc(T("pieces.soude"))}</div>`;
    } else {
      h += `<div class="jeu-pieces">` + a.pieces.map((p, i) => `
        <label class="jeu-piece" title="${esc(T("pieces.pivot", { x: p.pivot[0], y: p.pivot[1], z: p.pivot[2] }))}">
          <input type="text" data-i="${i}" value="${esc(p.nom)}" maxlength="64" spellcheck="false"
                 aria-label="${esc(T("pieces.nom_aria", { n: i + 1 }))}">
          <span class="jeu-forme">${esc(T("forme." + p.forme))}</span>
          <span class="jeu-tris">${esc(nb(p.triangles))}</span>
        </label>`).join("") + `</div>`;
      h += `<div class="jeu-actions"><button class="jeu-principal" id="pcSeparer" ${P.occupe ? "disabled" : ""}>${ico("dz-lab3d-assemblage")} ${esc(T("pieces.separer", { n }))}</button>`
        + `<button id="pcOublier" ${P.occupe ? "disabled" : ""}>${esc(T("pieces.oublier"))}</button></div>`;
    }
    const ia = a.ia || {};
    h += `<div class="jeu-ia"><div class="jeu-ia-tete">${ico("dz-etat-ia")} ${esc(T("ia.titre"))}</div>`
      + `<div class="jeu-note">${esc(T("ia.intro", { p: usd(ia.usd || 0) }))}</div>`
      + (a.cle_fal ? "" : `<div class="jeu-avis">${esc(T("ia.sans_cle"))}</div>`)
      + `<div class="jeu-actions"><button id="pcIa" ${P.occupe ? "disabled" : ""}>${ico("dz-etat-ia")} ${esc(T("ia.lancer", { p: usd(ia.usd || 0) }))}</button></div></div>`;
  }
  if (P.erreur) h += `<div class="jeu-erreur" role="alert">${esc(P.erreur)}</div>`;
  if (P.avis) h += `<div class="jeu-ok">${esc(P.avis)}</div>`;
  box.innerHTML = h;
  const on = (id, f) => { const b = box.querySelector("#" + id); if (b) b.addEventListener("click", f); };
  on("pcAnalyser", analyser);
  on("pcSeparer", separer);
  on("pcOublier", () => { P.analyse = null; P.avis = P.erreur = ""; rendrePieces(); });
  on("pcIa", segmenterIa);
}

async function analyser() {
  const c = cible();
  if (!c || !c.job || P.occupe) return;
  P.occupe = true; P.erreur = P.avis = ""; rendrePieces();
  try {
    const q = new URLSearchParams({ job: c.job, version: String(c.version), langue: langue() });
    P.analyse = await lireJson(await fetch(`/api/etabli/pieces?${q}`));
    P.cle = `${c.job}#${c.version}`;
  } catch (e) {
    P.erreur = T("pieces.echec", { m: e.message });
  } finally {
    P.occupe = false; rendrePieces();
  }
}

function nomsSaisis() {
  return [...document.querySelectorAll("#panPieces .jeu-piece input")].map((i) => i.value);
}

async function separer() {
  const c = cible();
  if (!c || !c.job || !P.analyse || P.occupe) return;
  const noms = nomsSaisis();
  P.occupe = true; P.erreur = P.avis = ""; rendrePieces();
  try {
    const r = await lireJson(await fetch("/api/etabli/pieces", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: c.job, version: c.version, noms, langue: langue() }),
    }));
    P.analyse = null;
    P.avis = T("pieces.ecrit", { v: r.version, n: ((r.source && r.source.pieces) || noms).length });
    await ouvrirNeuve(c.job, r.version);
  } catch (e) {
    P.erreur = T("pieces.echec", { m: e.message });
  } finally {
    P.occupe = false; rendrePieces();
  }
}

async function segmenterIa() {
  const c = cible();
  if (!c || !c.job || !P.analyse || P.occupe) return;
  const ia = P.analyse.ia || {};
  const D_ = window.__dzDialogue;
  /* Le devis AVANT l'envoi, et sans dialogue maison : refus (le sens sûr, comme dz-plafonds). */
  if (!D_ || !(await D_.confirmer(T("ia.confirmer", { p: usd(ia.usd || 0), m: ia.endpoint || "tripo" }),
    { titre: T("ia.titre"), ok: T("ia.ok", { p: usd(ia.usd || 0) }) }))) return;
  P.occupe = true; P.erreur = P.avis = ""; rendrePieces();
  try {
    const r = await lireJson(await fetch("/api/etabli/pieces/ia", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: c.job, version: c.version, confirme_cout: true, langue: langue() }),
    }));
    P.analyse = null;
    P.avis = T("ia.ecrit", { v: r.version });
    await ouvrirNeuve(c.job, r.version);
  } catch (e) {
    P.erreur = e.status === 503 ? T("ia.sans_cle") : T("pieces.echec", { m: e.message });
  } finally {
    P.occupe = false; rendrePieces();
  }
}

/* ── B7 : les budgets de triangles ──────────────────────────────────────── */

function rendreDensites() {
  const box = $("#panDensites");
  if (!box) return;
  const c = cible();
  let h = `<div class="dt-label">${ico("dz-lab3d-lod")} ${esc(T("dens.titre"))}</div>`;
  if (!c || !c.job) {
    box.innerHTML = h + `<div class="vide">${esc(T(c ? "pieces.meshy" : "dens.vide_modele"))}</div>`;
    return;
  }
  const role = D.roles.find((r) => r.id === D.role) || D.roles[0];
  h += `<label class="jeu-role"><span>${esc(T("dens.role"))}</span><select id="dnRole">`
    + D.roles.map((r) => `<option value="${esc(r.id)}" ${r.id === D.role ? "selected" : ""}>${esc(T("role." + r.id))}</option>`).join("")
    + `</select></label>`;
  if (role) {
    h += `<div class="jeu-cibles">${role.densites.map((n, i) => `<span>${esc(T("densite." + ["haute", "moyenne", "basse"][i]))} · ${esc(kTri(n))}</span>`).join("")}</div>`
      + `<div class="jeu-note">${esc(T("pourquoi." + role.id))}</div>`;
  }
  h += `<div class="jeu-actions"><button class="jeu-principal" id="dnGo" ${D.occupe ? "disabled" : ""}>${ico("dz-lab3d-lod")} ${esc(D.occupe ? T("dens.en_cours") : T("dens.lancer", { v: c.version }))}</button></div>`;
  const res = D.resultat;
  if (!res) {
    h += `<div class="vide">${esc(T("dens.vide"))}</div>`;
  } else {
    h += `<div class="jeu-resume">${esc(T("dens.source", { f: res.source, t: nb(res.source_tris), r: T("role." + res.role) }))}</div>`
      + `<table class="jeu-table"><thead><tr><th>${esc(T("dens.col_densite"))}</th><th>${esc(T("dens.col_tris"))}</th>`
      + `<th>${esc(T("dens.col_taille"))}</th><th title="${esc(T("dens.iou_aide"))}">IoU</th><th></th></tr></thead><tbody>`
      + res.densites.map((d) => {
        const pe = d.perte || {};
        const iou = pe.iou_min == null ? "—" : Number(pe.iou_min).toFixed(3);
        const note = d.source_gardee ? T("dens.gardee") : d.cible_tenue === false ? T("dens.non_tenue", { c: nb(d.cible) }) : "";
        return `<tr title="${esc(note)}"><td>${esc(T("densite." + d.densite))}${note ? " *" : ""}</td>`
          + `<td>${esc(nb(d.tris))}<small> / ${esc(kTri(d.cible))}</small></td><td>${esc(ko(d.octets))}</td><td>${esc(iou)}</td>`
          + `<td><a href="/api/etabli/densites/fichier?job=${encodeURIComponent(res.job)}&densite=${esc(d.densite)}" download title="${esc(T("dens.telecharger"))}">${ico("dz-action-telecharger")}</a></td></tr>`;
      }).join("") + `</tbody></table>`
      + (res.densites.some((d) => d.source_gardee || d.cible_tenue === false) ? `<div class="jeu-note">${esc(T("dens.legende"))}</div>` : "")
      + `<div class="jeu-actions"><a class="jeu-lien" href="/api/etabli/densites/zip?job=${encodeURIComponent(res.job)}" download>${ico("dz-action-telecharger")} ${esc(T("dens.archive"))}</a></div>`;
  }
  if (D.erreur) h += `<div class="jeu-erreur" role="alert">${esc(D.erreur)}</div>`;
  box.innerHTML = h;
  const sel = box.querySelector("#dnRole");
  if (sel) sel.addEventListener("change", () => { D.role = sel.value; rendreDensites(); });
  const go = box.querySelector("#dnGo");
  if (go) go.addEventListener("click", genererDensites);
}

async function lireDensites(job) {
  try {
    const j = await lireJson(await fetch(`/api/etabli/densites?job=${encodeURIComponent(job)}`));
    D.roles = j.roles || [];
    D.resultat = j.resultat || null;
    if (D.resultat && D.roles.some((r) => r.id === D.resultat.role)) D.role = D.resultat.role;
  } catch (e) {
    D.erreur = T("dens.echec", { m: e.message });
  }
  rendreDensites();
}

async function genererDensites() {
  const c = cible();
  if (!c || !c.job || D.occupe) return;
  D.occupe = true; D.erreur = ""; rendreDensites();
  try {
    D.resultat = await lireJson(await fetch("/api/etabli/densites", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: c.job, version: c.version, role: D.role }),
    }));
  } catch (e) {
    D.erreur = T("dens.echec", { m: e.message });
  } finally {
    D.occupe = false; rendreDensites();
  }
}

/* ── branchements ───────────────────────────────────────────────────────── */

/* #panPieces suit l'onglet Parties : etabli.js ne le connaît pas (sa table PANNEAUX en a quatre), ce module écoute
   donc les MÊMES boutons. */
function suivreOnglets() {
  const pan = $("#panPieces");
  for (const b of document.querySelectorAll(".onglets .on")) {
    b.addEventListener("click", () => pan && pan.classList.toggle("hidden", b.dataset.onglet !== "parties"));
  }
}

/* À chaque modèle chargé : l'analyse d'un autre modèle ne vaut plus rien, les densités se relisent pour ce job. */
document.addEventListener("etabli:charge", () => {
  const c = cible();
  if (!c || `${c.job}#${c.version}` !== P.cle) { P.analyse = null; P.cle = ""; P.erreur = ""; }
  rendrePieces();
  if (c && c.job && c.job !== D.job) { D.job = c.job; D.resultat = null; D.erreur = ""; lireDensites(c.job); }
  else rendreDensites();
});

suivreOnglets();
rendrePieces();
fetch("/api/etabli/densites?job=_").then((r) => r.json()).then((j) => { D.roles = j.roles || []; rendreDensites(); })
  .catch(() => rendreDensites());

export { P, D, rendrePieces, rendreDensites };
