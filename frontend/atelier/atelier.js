/* Atelier Chapitre P1 — script → entités → bible.
   Vanilla JS, même API que l'app (même origine). Aucune dépendance. */
"use strict";

const $ = (s) => document.querySelector(s);
/* t148 : la surcouche de traduction n'entre pas dans les <select> — les <option> fixes de la page sont traduites ici, une fois (window.__dzI18n.traduire ne rend rien en français). */
for (const o of document.querySelectorAll("select option")) { const t = window.__dzI18n && window.__dzI18n.traduire(o.textContent); if (t) o.textContent = t; }
/* t148 : deux textes de la page à double sens (la surcouche ignore les entrées « contexte ») */
{ const o = document.querySelector('#vbRole option[value="libre"]'); if (o) o.textContent = dzT("atelier.ath_vec.libre");
  const b = document.querySelector("#animGo");
  if (b && b.lastChild && b.lastChild.nodeType === 3) b.lastChild.textContent = " " + dzT("atelier.ath_anim.monter"); }
/* Deepotus Glyph (G6) : une icône de la suite, décorative — le sens est porté par le bouton (libellé, title, aria-label) */
const ico = (cle, t = 16) => (typeof dzIcone === "function" ? dzIcone(cle, { taille: t, classe: "dzi--" + t }) : "");
const api = {
  async get(p) { const r = await fetch("/api" + p); if (!r.ok) throw new Error(await r.text()); return r.json(); },
  async send(m, p, body) {
    const r = await fetch("/api" + p, { method: m, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    return d;
  },
};

const KIND_LABEL = { character: dzT("atelier.at1_kind.personnage"), place: dzT("atelier.at1_kind.lieu"), object: dzT("atelier.at1_kind.objet"),
                     date: dzT("atelier.at1_kind.date"), ambiance: dzT("atelier.at1_kind.ambiance"), decor: dzT("atelier.at1_kind.decor") };

/* ───────── état ───────── */
let chapters = [];          // [{id,title,series}]
let chapter = null;         // chapitre ouvert {id,title,series,script_text,spans}
let entities = [];          // toute la bible
let curKind = "character";  // onglet bible actif
let saveTimer = null;
let libTarget = null;       // entité en attente d'une image d'inspiration
let shots = [];             // storyboard du chapitre ouvert
let scenes = [];            // scénario (scènes) du chapitre ouvert
let mode = "script";        // "script" | "screenplay" | "board"
let voices11 = null;        // voix ElevenLabs du compte (lazy)
let voiceAudio = null;      // pré-écoute en cours (un seul lecteur)
let shotcraft = null;       // {status, cards} — pont video-shotcraft (W-d)

const SHOT_TYPES = ["establishing", "wide", "medium", "close-up",
  "extreme close-up", "over-shoulder", "POV", "insert"];
const CAMERA_MOVES = ["slow push-in", "slow pull-out", "360-degree orbit",
  "tracking shot", "handheld with subtle shake", "static, locked-off",
  "low angle dramatic", "rack focus reveal", "dolly zoom (vertigo effect)",
  "whip pan transition", "crane shot descending"];
const ENERGY_LABELS = { 1: dzT("atelier.at1_energie.e1"), 2: dzT("atelier.at1_energie.e2"), 3: dzT("atelier.at1_energie.e3"),
                        4: dzT("atelier.at1_energie.e4"), 5: dzT("atelier.at1_energie.e5") };

/* ───────── toast ───────── */
let toastTimer = null;
function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg; t.classList.toggle("err", !!err); t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 3200);
}

/* ═════════ chapitres ═════════ */
async function loadChapters(selectId) {
  chapters = (await api.get("/chapters")).chapters;
  const sel = $("#chapterSelect");
  sel.innerHTML = chapters.map(c =>
    `<option value="${c.id}">${esc(c.title)}${c.series ? " · " + esc(c.series) : ""}</option>`).join("")
    || `<option value="">${dzT("atelier.at1_chap.aucun")}</option>`;
  if (selectId) sel.value = selectId;
  const id = sel.value;
  if (id) await openChapter(id); else renderScript();
}

async function openChapter(id) {
  chapter = await api.get("/chapters/" + id);
  $("#chapterTitle").value = chapter.title || "";
  $("#chapterSeries").value = chapter.series || "";
  $("#script").value = chapter.script_text || "";
  renderScript();
  shots = []; scenes = [];
  if (mode === "board") await loadShots(true);
  if (mode === "screenplay") await loadScenes(true);
  await loadVectorDocs();
  await majEmporte();
}

/* ═════════ tâche #59 (02/10/2026) : un chapitre EMPORTÉ par le téléphone ═════════
   Tant qu'il l'écrit hors ligne, le PC le laisse en lecture seule (le serveur répond 423 à toute écriture).
   « Reprendre sur le PC » force la libération ; tout texte refusé (retour du téléphone, ré-import) est au journal,
   d'où on peut le copier ou le reprendre. */
let emporte = null;         // {appareil:{nom}, pris_le} si le chapitre ouvert est emporté
const MOTIF_LABEL = { verrou_perdu: dzT("atelier.at1_emp.motif_verrou"), base_differente: dzT("atelier.at1_emp.motif_base"),
                      reimport: dzT("atelier.at1_emp.motif_reimport"), repris_pc: dzT("atelier.at1_emp.motif_repris"), revoque: dzT("atelier.at1_emp.motif_revoque") };

async function majEmporte() {
  const box = $("#emporte");
  if (!chapter || !box) return;
  let verrous = [], journal = [];
  try {
    verrous = (await api.get("/sync/verrous")).verrous || [];
    journal = ((await api.get("/sync/conflits")).conflits || []).filter(c => c.chapitre === chapter.id && c.texte);
  } catch (e) { return; }
  emporte = verrous.find(v => v.chapitre === chapter.id) || null;
  $("#script").readOnly = !!emporte;
  if (!emporte && !journal.length) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  const quand = (iso) => iso ? new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "";
  box.innerHTML =
    (emporte ? `<p>${ico("dz-etat-mobile")} ${dzT("atelier.at1_emp.emporte", { nom: esc(emporte.appareil.nom), quand: quand(emporte.pris_le) })}</p>
       <button class="btn" id="btnReprendre" title="${dzT("atelier.at1_emp.reprendre_titre")}">${dzT("atelier.at1_emp.reprendre_pc")}</button>` : "")
    + (journal.length ? `<div class="journal"><p>${dzT("atelier.at1_emp.journal", { n: journal.length })}</p>` + journal.map(c =>
      `<div class="journal-ligne"><span>${quand(c.quand)} · ${esc(MOTIF_LABEL[c.motif] || c.motif)}${c.appareil ? " · " + esc(c.appareil) : ""}
       · ${dzT("atelier.at1_emp.n_car", { n: c.texte.length })}</span>
       <button class="btn" data-copier="${c.id}" title="${dzT("atelier.at1_emp.copier_titre")}">${dzT("atelier.at1_emp.copier")}</button>
       <button class="btn" data-remplacer="${c.id}" ${emporte ? "disabled" : ""}
         title="${dzT("atelier.at1_emp.remplacer_titre")}">${dzT("atelier.at1_emp.remplacer_texte")}</button></div>`).join("") + `</div>` : "");
  box.classList.remove("hidden");
  const r = $("#btnReprendre");
  if (r) r.onclick = async () => {
    if (!await window.__dzDialogue.confirmer(dzT("atelier.at1_emp.confirmer", { titre: chapter.title, nom: emporte.appareil.nom }), { ok: dzT("atelier.at1_emp.reprendre") })) return;
    try { await api.send("POST", `/chapters/${chapter.id}/reprendre`); toast(dzT("atelier.at1_emp.repris")); }
    catch (e) { toast(dzT("atelier.at1_emp.reprise_ko", { msg: e.message }), true); }
    await majEmporte();
  };
  box.querySelectorAll("[data-copier]").forEach(b => b.onclick = async () => {
    const c = journal.find(x => String(x.id) === b.dataset.copier);
    try { await navigator.clipboard.writeText(c.texte); toast(dzT("atelier.at1_emp.copie")); } catch (e) { toast(dzT("atelier.at1_emp.copie_ko", { msg: e.message }), true); }
  });
  box.querySelectorAll("[data-remplacer]").forEach(b => b.onclick = async () => {
    const c = journal.find(x => String(x.id) === b.dataset.remplacer);
    if (!await window.__dzDialogue.confirmer(dzT("atelier.at1_emp.remplacer_q"), { ok: dzT("atelier.at1_emp.remplacer") })) return;
    $("#script").value = c.texte; renderScript(); scheduleSave();
  });
}

function scheduleSave() {
  if (!chapter) return;
  if (emporte) { $("#saveState").textContent = dzT("atelier.at1_save.emporte"); $("#saveState").className = "savestate"; return; }
  $("#saveState").textContent = "…"; $("#saveState").className = "savestate saving";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try {
      chapter.script_text = $("#script").value;
      chapter.title = $("#chapterTitle").value || chapter.title;
      chapter.series = $("#chapterSeries").value;
      await api.send("PUT", "/chapters/" + chapter.id, {
        title: chapter.title, series: chapter.series,
        script_text: chapter.script_text, spans: chapter.spans,
      });
      $("#saveState").innerHTML = dzT("atelier.at1_save.enregistre") + ico("dz-etat-enregistre"); $("#saveState").className = "savestate saved";
      const c = chapters.find(x => x.id === chapter.id);
      if (c) { c.title = chapter.title; c.series = chapter.series; }
    } catch (e) {
      // Le chapitre n'existe plus côté serveur (session périmée / base
      // changée) : on le re-crée avec le contenu courant — AUCUNE perte.
      if (/Chapter not found/i.test(e.message)) {
        try {
          const fresh = await api.send("POST", "/chapters", {
            title: chapter.title, series: chapter.series,
            script_text: $("#script").value, spans: chapter.spans || [],
          });
          toast(dzT("atelier.at1_save.recree", { titre: fresh.title }));
          await loadChapters(fresh.id);
          return;
        } catch (e2) { e = e2; }
      }
      $("#saveState").textContent = dzT("atelier.at1_save.echec"); toast(dzT("atelier.at1_save.ko", { msg: e.message }), true);
      if (/emporté par le téléphone/i.test(e.message)) await majEmporte();   // emporté entre-temps : lecture seule
    }
  }, 800);
}

/* ═════════ script : surlignage + spans ═════════ */
function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
/* tâche #60 : pour une valeur d'ATTRIBUT (title, data-*), les guillemets aussi — `esc` ne suffit pas */
function escA(s) { return esc(String(s ?? "")).replace(/"/g, "&quot;").replace(/'/g, "&#39;"); }

/* Ré-ancre les spans après édition : on recherche le texte de la zone au plus
   près de son ancien offset ; introuvable -> orpheline (à re-lier). */
function reanchorSpans(text) {
  for (const sp of chapter.spans || []) {
    if (text.substring(sp.start, sp.end) === sp.text) { sp.orphan = false; continue; }
    let best = -1, bestDist = 1e12, from = 0;
    while (true) {
      const i = text.indexOf(sp.text, from);
      if (i < 0) break;
      const d = Math.abs(i - sp.start);
      if (d < bestDist) { bestDist = d; best = i; }
      from = i + 1;
    }
    if (best >= 0) { sp.start = best; sp.end = best + sp.text.length; sp.orphan = false; }
    else sp.orphan = true;
  }
}

function renderScript() {
  const text = $("#script").value;
  if (chapter) reanchorSpans(text);
  const spans = (chapter && chapter.spans || [])
    .filter(sp => !sp.orphan)
    .slice().sort((a, b) => a.start - b.start);
  let html = "", pos = 0;
  for (const sp of spans) {
    if (sp.start < pos) continue; // chevauchement: on garde la première
    const ent = entities.find(e => e.id === sp.entity_id);
    const cls = ent ? "k-" + ent.kind : "orphan"; // entité supprimée -> rouge
    html += esc(text.substring(pos, sp.start));
    html += `<mark class="${cls}">${esc(text.substring(sp.start, sp.end))}</mark>`;
    pos = sp.end;
  }
  html += esc(text.substring(pos));
  // les orphelines: affichées dans la légende seulement (pas d'offset fiable)
  $("#hl").innerHTML = html + "\n";
}

function syncScroll() { $("#hl").scrollTop = $("#script").scrollTop; }

/* ───── sélection → barre d'action ───── */
function currentSelection() {
  const ta = $("#script");
  const a = ta.selectionStart, b = ta.selectionEnd;
  if (a == null || b == null || a === b) return null;
  const t = ta.value.substring(a, b).trim();
  if (!t) return null;
  // resserre la sélection sur le texte trimé
  const lead = ta.value.substring(a, b).indexOf(t);
  return { start: a + lead, end: a + lead + t.length, text: t };
}

function refreshSelBar() {
  const sel = currentSelection();
  const bar = $("#selBar");
  if (!sel || !chapter) { bar.classList.add("hidden"); return; }
  $("#selText").textContent = dzT("atelier.at1_sel.guil_ouv") + (sel.text.length > 60 ? sel.text.slice(0, 60) + "…" : sel.text) + dzT("atelier.at1_sel.guil_ferm");
  const link = $("#linkSelect");
  link.innerHTML = `<option value="">${dzT("atelier.at1_sel.lier")}</option>` + entities.map(e =>
    `<option value="${e.id}">${KIND_LABEL[e.kind]} · ${esc(e.name)}</option>`).join("");
  bar.classList.remove("hidden");
}

async function createEntityFromSelection(kind) {
  const sel = currentSelection();
  if (!sel) return;
  try {
    const ent = await api.send("POST", "/bible/entities", { kind, name: sel.text });
    entities.push(ent);
    addSpan(sel, ent.id);
    curKind = kind; setTab(kind);
    await renderBible();
    toast(dzT("atelier.at1_sel.cree", { kind: KIND_LABEL[kind], nom: ent.name }));
  } catch (e) { toast(dzT("atelier.at1_sel.cree_ko", { msg: e.message }), true); }
}

function addSpan(sel, entityId) {
  chapter.spans = chapter.spans || [];
  chapter.spans.push({ start: sel.start, end: sel.end, text: sel.text, entity_id: entityId });
  renderScript(); scheduleSave(); refreshSelBar();
}

/* ═════════ bible ═════════ */
function setTab(kind) {
  curKind = kind;
  document.querySelectorAll(".bible-pane .tab").forEach(t =>
    t.classList.toggle("active", t.dataset.kind === kind));
}

async function loadEntities() {
  entities = (await api.get("/bible/entities")).entities;
  await loadVoiceCast();
}

// T103 (plan-son-vfx T14-T15, D4) — le casting VOIX + TEMPÉRAMENT, servi par le backend : qui parlera avec quelle
// voix (GET /voice-cast, rechargé avec la bible), et la palette des balises Eleven v3 (GET /voice-tags, registre
// relu côté serveur — jamais recopié ici : une balise que le modèle ne lit pas ne doit pas être proposée).
let voiceCast = { narrator: null, cast: {}, uncast: [] };
let voiceTags = null;
async function loadVoiceCast() {
  try { voiceCast = await api.get("/voice-cast"); } catch (_e) { /* casting muet : les puces le diront */ }
}
async function loadVoiceTags() {
  if (voiceTags) return voiceTags;
  try { voiceTags = await api.get("/voice-tags"); } catch (_e) { voiceTags = { groups: {}, providers: {} }; }
  return voiceTags;
}
function foldName(s) {
  return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}
function castChip(name) {
  const v = voiceCast.cast[foldName(name)];
  if (!v) return `<span class="cast-chip cast-none" title="${dzT("atelier.at1_cast.sans_titre")}">${esc(name)} · ${dzT("atelier.at1_cast.sans_voix")}</span>`;
  const t = ((v.style && v.style.tags) || []).join(" ");
  return `<span class="cast-chip" title="${dzT("atelier.at1_cast.voix", { id: esc(v.voice_id) })}${t ? " · " + dzT("atelier.at1_cast.temperament", { t: esc(t) }) : ""}">${esc(name)} · ${esc(v.name)}${t ? " " + esc(t) : ""}</span>`;
}
function temperRow(e) {
  const vt = voiceTags || { groups: {}, providers: {} };
  const on = (e.voice_style && e.voice_style.tags) || [];
  if (!vt.providers || !vt.providers.elevenlabs) {
    return `<div class="voice-temper"><span class="temper-note">${dzT("atelier.at1_cast.temper")} ${vt.providers && vt.providers.voicebox
      ? dzT("atelier.at1_cast.voicebox") : dzT("atelier.at1_cast.cle")}${on.length ? dzT("atelier.at1_cast.garde") + on.map(esc).join(" ") : ""}</span></div>`;
  }
  // l'émotion et la voix seulement : les bruitages (« sons ») n'ont rien à faire sur une fiche de personnage
  const tags = [].concat(vt.groups.emotion || [], vt.groups.voix || []);
  return `<div class="voice-temper" title="${dzT("atelier.at1_cast.temper_titre")}">
    <span class="temper-note">${dzT("atelier.at1_cast.temper")}</span>
    ${tags.map(t => `<button class="btn ghost act-temper${on.includes(t) ? " on" : ""}" data-t="${esc(t)}" aria-pressed="${on.includes(t)}">${esc(t)}</button>`).join("")}
  </div>`;
}

async function renderBible() {
  if (curKind === "character") await loadVoiceTags();
  const list = $("#entityList");
  const items = entities.filter(e => e.kind === curKind);
  if (!items.length) {
    list.innerHTML = `<div class="empty-note">${dzT("atelier.at1_bib.aucun", { kind: KIND_LABEL[curKind].toLowerCase() })}<br>
      ${dzT("atelier.at1_bib.aucun_aide")}</div>`;
    return;
  }
  list.innerHTML = items.map(e => `
  <div class="entity-card" data-id="${e.id}">
    <div class="refbox">
      ${e.ref_image
        ? `<a href="/api/images/${encodeURIComponent(e.ref_image)}" target="_blank" title="${dzT("atelier.at1_bib.turn_titre")}">
             <img class="refimg board-ref" src="/api/images/${encodeURIComponent(e.ref_image)}" alt="turnaround"></a>`
        : `<div class="refimg empty">${dzT("atelier.at1_bib.pas_planche")}<br>${dzT("atelier.at1_bib.generer_bas")}</div>`}
      ${e.face_image
        ? `<a href="/api/images/${encodeURIComponent(e.face_image)}" target="_blank" title="${dzT("atelier.at1_bib.visage_titre")}">
             <img class="refimg board-ref" src="/api/images/${encodeURIComponent(e.face_image)}" alt="${dzT("atelier.at1_bib.visages")}"></a>`
        : ""}
      <div class="seedrow">
        ${e.seed != null ? `<span class="seedbadge" title="${dzT("atelier.at1_bib.seed_titre")}">${ico("dz-etat-verrouille")} ${e.seed}</span>` : `<span class="seedbadge" style="opacity:.5">seed —</span>`}
        ${e.model3d_job
          ? `<a class="seedbadge" href="/api/assets/3d/${encodeURIComponent(e.model3d_job)}/version/1" title="${dzT("atelier.at1_bib.glb_titre")}">${ico("dz-action-telecharger")} GLB</a>`
          : ""}
      </div>
      <div class="entity-actions">
        <button class="btn primary act-gen" title="${dzT("atelier.at1_bib.gen_titre")}">${ico("dz-media-generer-image")} ${dzT("atelier.at1_bib.planche")}</button>
        <button class="btn act-roll" title="${dzT("atelier.at1_bib.roll")}" aria-label="${dzT("atelier.at1_bib.roll")}">${ico("dz-action-aleatoire")}</button>
        ${e.has_recipe ? `<button class="btn act-recipe" title="${dzT("atelier.at1_bib.recette_titre")}" aria-label="${dzT("atelier.at1_bib.recette")}">${ico("dz-action-lancer-recette")}</button>` : ""}
        ${BESOIN_3D_PAR_KIND[e.kind]
          ? `<button class="btn act-3d" title="${dzT("atelier.at1_bib.titre_3d")}">${ico("dz-lab3d-generer-modele")} 3D</button>`
          : ""}
      </div>
    </div>
    <div class="entity-main">
      <div class="row1">
        <span class="kinddot k-${e.kind}"></span>
        <input class="entity-name" value="${esc(e.name)}" title="${dzT("atelier.at1_bib.nom")}">
        <button class="btn ghost act-apps" title="${dzT("atelier.at1_bib.apps_titre")}">${ico("dz-media-apparitions")} ${dzT("atelier.at1_bib.apps")}</button>
        <button class="btn ghost act-del" title="${dzT("atelier.at1_bib.suppr")}" aria-label="${dzT("atelier.at1_bib.suppr")}">${ico("dz-action-supprimer")}</button>
      </div>
      <textarea class="entity-desc" placeholder="${dzT("atelier.at1_bib.desc")}">${esc(e.description)}</textarea>
      <input class="entity-style" placeholder="${dzT("atelier.at1_bib.style")}" title="${dzT("atelier.at1_bib.style_titre")}" value="${esc(e.style_notes)}">
      <div class="entity-apps hidden"></div>
      ${e.kind === "character" ? `
      <div class="voice-row">
        ${ico("dz-media-voix")} <span class="voice-name">${e.voice_name ? esc(e.voice_name) : "<i style='opacity:.55'>" + dzT("atelier.at1_voix.pas") + "</i>"}</span>
        ${e.voice_prev ? `<button class="btn ghost act-voice-play" title="${dzT("atelier.at1_voix.ecouter")}" aria-label="${dzT("atelier.at1_voix.ecouter")}">${ico("dz-media-lecture")}</button>` : ""}
        <button class="btn act-voice-suggest" title="${dzT("atelier.at1_voix.suggerer_titre")}">${ico("dz-action-suggerer")} ${dzT("atelier.at1_voix.suggerer")}</button>
        <button class="btn ghost act-voice-all" title="${dzT("atelier.at1_voix.toutes_titre")}">${ico("dz-action-deplier")} ${dzT("atelier.at1_voix.toutes")}</button>
        <button class="btn ghost act-voice-clone" title="${dzT("atelier.at1_voix.cloner_titre")}">${ico("dz-media-cloner-voix")} ${dzT("atelier.at1_voix.cloner")}</button>
      </div>
      ${temperRow(e)}
      <div class="voice-alts hidden"></div>` : ""}
      ${(e.aliases && e.aliases.length)
        ? `<div class="entity-aliases">${dzT("atelier.at1_bib.alias")} ${e.aliases.map(esc).join(" · ")}</div>` : ""}
      ${(e.evidence && e.evidence.length)
        ? `<details class="entity-evidence"><summary>${dzT("atelier.at1_bib.citations", { n: e.evidence.length })}</summary>
           ${e.evidence.slice(0, 8).map(v =>
             `<blockquote>${dzT("atelier.at1_bib.citation", { q: esc(v.quote) })}${v.chapter ? ` — <i>${esc(v.chapter)}</i>` : ""}</blockquote>`).join("")}
           </details>` : ""}
      <div class="insp-row">
        <span style="font-size:11px;color:var(--ink-soft)">${dzT("atelier.at1_bib.inspirations")}</span>
        ${(e.inspiration_images || []).map(f =>
          `<img src="/api/images/${encodeURIComponent(f)}" data-f="${esc(f)}" class="act-rm-insp" title="${dzT("atelier.at1_bib.retirer", { f: esc(f) })}">`).join("")}
        <button class="btn ghost act-add-insp" title="${dzT("atelier.at1_bib.ajouter_lib")}" aria-label="${dzT("atelier.at1_bib.ajouter_lib")}">${ico("dz-action-choisir-bibliotheque")}</button>
      </div>
    </div>
  </div>`).join("");

  // wiring des cartes
  list.querySelectorAll(".entity-card").forEach(card => {
    const id = card.dataset.id;
    const ent = () => entities.find(x => x.id === id);
    const saveField = debounce(async () => {
      try {
        const up = await api.send("PUT", "/bible/entities/" + id, {
          name: card.querySelector(".entity-name").value,
          description: card.querySelector(".entity-desc").value,
          style_notes: card.querySelector(".entity-style").value,
        });
        Object.assign(ent(), up); renderScript();
      } catch (e) { toast(dzT("atelier.at1_bib.save_ko", { msg: e.message }), true); }
    }, 700);
    ["input"].forEach(ev => {
      card.querySelector(".entity-name").addEventListener(ev, saveField);
      card.querySelector(".entity-desc").addEventListener(ev, saveField);
      card.querySelector(".entity-style").addEventListener(ev, saveField);
    });
    card.querySelector(".act-gen").addEventListener("click", () => generateRef(id, ent().seed));
    card.querySelector(".act-roll").addEventListener("click", () => generateRef(id, null));
    const rbtn = card.querySelector(".act-recipe");
    if (rbtn) rbtn.addEventListener("click", () => generateRef(id, null, true));
    const btn3d = card.querySelector(".act-3d");
    if (btn3d) btn3d.addEventListener("click", () => entityTo3D(id));
    card.querySelector(".act-apps").addEventListener("click", () => showApparitions(id, card));
    card.querySelector(".act-del").addEventListener("click", async () => {
      if (!await window.__dzDialogue.confirmer(dzT("atelier.at1_bib.suppr_q", { nom: ent().name }))) return;
      try {
        await api.send("DELETE", "/bible/entities/" + id);
        entities = entities.filter(x => x.id !== id);
        (chapter && chapter.spans || []).forEach(sp => { if (sp.entity_id === id) sp.orphan = true; });
        await renderBible(); renderScript(); scheduleSave();
      } catch (e) { toast(dzT("atelier.at1_bib.suppr_ko", { msg: e.message }), true); }
    });
    // ── casting voix (personnages) ──
    const vplay = card.querySelector(".act-voice-play");
    if (vplay) vplay.addEventListener("click", () => playVoicePrev(ent().voice_prev));
    const vsug = card.querySelector(".act-voice-suggest");
    if (vsug) vsug.addEventListener("click", () => suggestVoice(id, card));
    const vall = card.querySelector(".act-voice-all");
    if (vall) vall.addEventListener("click", () => showAllVoices(id, card));
    // T103 (D4a) — cloner une voix pour CE personnage : prises du dossier audio, confirmation (un clone occupe
    // un emplacement de voix du compte ElevenLabs), puis la voix est écrite sur l'entité par le serveur.
    const vclone = card.querySelector(".act-voice-clone");
    if (vclone) vclone.addEventListener("click", async () => {
      const raw = await window.__dzDialogue.saisir(dzT("atelier.at1_voix.prises"), { titre: dzT("atelier.at1_voix.cloner_dlg"), ok: dzT("atelier.at1_voix.suivant") });
      const files = String(raw || "").split(",").map(s => s.trim()).filter(Boolean);
      if (!files.length) return;
      if (!await window.__dzDialogue.confirmer(dzT("atelier.at1_voix.cloner_q", { nom: ent().name, n: files.length }), { ok: dzT("atelier.at1_voix.cloner") })) return;
      try {
        const d = await api.send("POST", `/bible/entities/${id}/voice-clone`, { files });
        Object.assign(ent(), d.entity);
        toast(dzT("atelier.at1_voix.clonee", { id: d.voice_id }) + (d.requires_verification ? dzT("atelier.at1_voix.verif") : ""));
        await loadVoiceCast();
        await renderBible();
      } catch (e) { toast(dzT("atelier.at1_voix.clone_ko", { msg: e.message }), true); }
    });
    // T103 (D4a) — le tempérament : une balise s'allume ou s'éteint ; le SERVEUR clampe (≤ 4, connues seulement)
    card.querySelectorAll(".act-temper").forEach(b => b.addEventListener("click", async () => {
      const t = b.dataset.t;
      const cur = (ent().voice_style && ent().voice_style.tags) || [];
      const next = cur.includes(t) ? cur.filter(x => x !== t) : cur.concat([t]).slice(-4);
      try {
        const up = await api.send("PUT", "/bible/entities/" + id, {
          voice_style: { tags: next, stability: (ent().voice_style || {}).stability },
        });
        Object.assign(ent(), up);
        await loadVoiceCast();
        await renderBible();
      } catch (e) { toast(dzT("atelier.at1_cast.temper_ko", { msg: e.message }), true); }
    }));
    card.querySelector(".act-add-insp").addEventListener("click", () => openLibrary(id));
    card.querySelectorAll(".act-rm-insp").forEach(img => img.addEventListener("click", async () => {
      const f = img.dataset.f;
      const insp = (ent().inspiration_images || []).filter(x => x !== f);
      const up = await api.send("PUT", "/bible/entities/" + id, { inspiration_images: insp });
      Object.assign(ent(), up); renderBible();
    }));
  });
}

async function generateRef(id, seed, useRecipe) {
  const ent = entities.find(x => x.id === id);
  if (!ent) return;
  if (!useRecipe && !(ent.description || "").trim()) { toast(dzT("atelier.at1_gen.sans_desc"), true); return; }
  toast(useRecipe ? dzT("atelier.at1_gen.recette", { nom: ent.name })
                  : dzT("atelier.at1_gen.planche", { nom: ent.name }));
  try {
    const body = useRecipe ? { use_recipe: true } : (seed != null ? { seed } : {});
    const up = await api.send("POST", `/bible/entities/${id}/generate`, body);
    Object.assign(ent, up);
    await renderBible();
    toast((useRecipe ? dzT("atelier.at1_gen.rejouee", { nom: ent.name, seed: up.seed }) : dzT("atelier.at1_gen.generee", { nom: ent.name, seed: up.seed })));
  } catch (e) { toast(dzT("atelier.at1_gen.ko", { msg: e.message }), true); }
}

/* ═════════ storyboard ═════════ */
/* Pont video-shotcraft (W-d) : catalogue des recettes motion (fiches du
   skill installé, sinon catalogue embarqué) + badge d'état. */
async function loadShotcraft() {
  if (shotcraft) return;
  try { shotcraft = await api.get("/atelier/shotcraft"); }
  catch (e) { shotcraft = { status: null, cards: [] }; }
  const el = $("#shotcraftStatus");
  if (el && shotcraft.status) {
    el.innerHTML = ico("dz-etat-information") + ` shotcraft · ${dzT("atelier.at1_sc.fiches", { n: shotcraft.status.cards })} · ` +
      (shotcraft.status.installed ? dzT("atelier.at1_sc.installe") : dzT("atelier.at1_sc.embarque"));
    el.title = dzT("atelier.at1_sc.titre") +
      (shotcraft.status.path ? "\n" + shotcraft.status.path : "");
  }
}

function recipeOptions(cur) {
  const cards = (shotcraft && shotcraft.cards) || [];
  const opt = (c) => `<option value="${c.slug}"` +
    `${c.slug === cur ? " selected" : ""} title="${esc(c.gloss)}">` +
    `${c.slug}</option>`;
  const anim = cards.filter(c => c.anim), other = cards.filter(c => !c.anim);
  return `<option value=""${!cur ? " selected" : ""}>${dzT("atelier.at1_sc.recette")}</option>` +
    (anim.length ? `<optgroup label="${dzT("atelier.at1_sc.anim")}">${anim.map(opt).join("")}</optgroup>` : "") +
    (other.length ? `<optgroup label="Motion UI (promo)">${other.map(opt).join("")}</optgroup>` : "");
}

function energyOptions(cur) {
  return `<option value=""${cur == null ? " selected" : ""}>—</option>` +
    [1, 2, 3, 4, 5].map(v => `<option value="${v}"` +
      `${v === cur ? " selected" : ""}>${ENERGY_LABELS[v]}</option>`).join("");
}

function setMode(m) {
  mode = m;
  document.querySelectorAll("#modeTabs .tab").forEach(t =>
    t.classList.toggle("active", t.dataset.mode === m));
  const board = m === "board", sp = m === "screenplay";
  document.querySelector(".editor-wrap").classList.toggle("hidden", board || sp);
  $("#scriptLegend").classList.toggle("hidden", board || sp);
  $("#selBar").classList.add("hidden");
  $("#board").classList.toggle("hidden", !board);
  $("#boardTotal").classList.toggle("hidden", !board);
  $("#screenplay").classList.toggle("hidden", !sp);
  if (board) loadShotcraft().then(() => loadShots(true));
  if (sp) loadScenes(true);
}

/* ═════════ scénario (adaptation) ═════════ */
const TIMES_OF_DAY = ["JOUR", "NUIT", "AUBE", "CRÉPUSCULE", "MATIN", "SOIR"];

async function loadScenes(render) {
  if (!chapter) { scenes = []; if (render) renderScreenplay(); return; }
  scenes = (await api.get(`/chapters/${chapter.id}/scenes`)).scenes;
  $("#fountainDl").href = chapter
    ? `/api/chapters/${chapter.id}/screenplay?format=fountain` : "#";
  if (render) renderScreenplay();
}

function renderScreenplay() {
  const list = $("#sceneList");
  if (!chapter) { list.innerHTML = `<div class="empty-note">${dzT("atelier.at1_scn.sans_chap")}</div>`; return; }
  if (!scenes.length) {
    list.innerHTML = `<div class="empty-note">${dzT("atelier.at1_scn.vide")}<br>
      🎭 <b>${dzT("atelier.at1_scn.adapter")}</b> ${dzT("atelier.at1_scn.vide_aide")}</div>`;
    return;
  }
  const totVo = scenes.reduce((a, s) => a + (s.duration_s || 0), 0);
  const nVo = scenes.filter(s => s.vo_audio).length;
  $("#voTotal").textContent = nVo
    ? `Σ VO ${fmtDur(totVo)} (${nVo}/${scenes.length})` : "Σ VO —";
  list.innerHTML = scenes.map((s, i) => `
  <div class="scene-card" data-id="${s.id}">
    <div class="scene-slug">${dzT("atelier.at1_scn.scene", { n: i + 1 })} · ${esc(s.slugline)}
      <span class="scene-vo">
        ${s.duration_s ? `<span class="seedbadge" title="${dzT("atelier.at1_scn.duree_titre")}">${ico("dz-media-duree")} ${fmtDur(s.duration_s)}</span>` : ""}
        ${s.vo_audio ? `<button class="btn ghost sc-vo-play" title="${dzT("atelier.at1_scn.ecouter")}" aria-label="${dzT("atelier.at1_scn.ecouter")}">${ico("dz-media-lecture")}</button>` : ""}
        <button class="btn sc-vo-gen" title="${dzT("atelier.at1_scn.gen_vo_titre")}" aria-label="${dzT("atelier.at1_scn.gen_vo")}">${ico("dz-media-generer-voix")}${s.vo_audio ? " ↻" : ""}</button>
      </span>
    </div>
    <div class="scene-meta">
      <select class="sc-ie" title="INT/EXT">
        ${["INT", "EXT", "INT/EXT"].map(v => `<option ${v === s.int_ext ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <select class="sc-tod" title="${dzT("atelier.at1_scn.moment")}">
        ${TIMES_OF_DAY.map(v => `<option ${v === s.time_of_day ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <input class="sc-light" value="${esc(s.lighting)}" placeholder="${dzT("atelier.at1_scn.eclairage")}" title="${dzT("atelier.at1_scn.eclairage_titre")}">
      <input class="sc-mood" value="${esc(s.mood)}" placeholder="mood" title="${dzT("atelier.at1_scn.mood_titre")}">
    </div>
    <div class="scene-cam">${ico("dz-lab3d-camera")} <input class="sc-cam" value="${esc(s.camera_notes)}" placeholder="${dzT("atelier.at1_scn.camera")}"></div>
    <textarea class="scene-fountain" spellcheck="false">${esc(s.fountain_text)}</textarea>
    <div class="scene-ents">${entChips(s.entities)}</div>
    ${s.source_text ? `<div class="scene-src">${dzT("atelier.at1_scn.source", { t: esc(s.source_text) })}</div>` : ""}
  </div>`).join("");

  list.querySelectorAll(".scene-card").forEach(card => {
    const id = card.dataset.id;
    const save = debounce(async () => {
      try {
        const up = await api.send("PUT", "/scenes/" + id, {
          int_ext: card.querySelector(".sc-ie").value,
          time_of_day: card.querySelector(".sc-tod").value,
          lighting: card.querySelector(".sc-light").value,
          mood: card.querySelector(".sc-mood").value,
          camera_notes: card.querySelector(".sc-cam").value,
          fountain_text: card.querySelector(".scene-fountain").value,
        });
        const sc = scenes.find(x => x.id === id);
        Object.assign(sc, up);
        card.querySelector(".scene-slug").textContent =
          `${dzT("atelier.at1_scn.scene", { n: sc.idx + 1 })} · ${up.slugline}`;
      } catch (e) { toast(dzT("atelier.at1_scn.save_ko", { msg: e.message }), true); }
    }, 700);
    card.querySelectorAll("select,input,textarea").forEach(el =>
      ["input", "change"].forEach(ev => el.addEventListener(ev, save)));
    // voice-over de la scène
    const vp = card.querySelector(".sc-vo-play");
    if (vp) vp.addEventListener("click", () => {
      const sc = scenes.find(x => x.id === id);
      if (sc && sc.vo_audio) playVoicePrev("/api/audio/" + encodeURIComponent(sc.vo_audio));
    });
    card.querySelector(".sc-vo-gen").addEventListener("click", () => sceneVo(id));
  });
}

async function sceneVo(sceneId) {
  const sc = scenes.find(x => x.id === sceneId);
  if (!sc) return;
  toast(dzT("atelier.at1_vo.scene", { n: sc.idx + 1 }));
  try {
    const r = await api.send("POST", `/scenes/${sceneId}/voiceover`,
                             { language: "fr" });
    Object.assign(sc, r.scene);
    renderScreenplay();
    const who = [...new Set((r.segments || []).map(x => x.speaker).filter(Boolean))];
    toast(dzT("atelier.at1_vo.minutee", { n: sc.idx + 1, d: fmtDur(r.duration_s) }) +
          (who.length ? dzT("atelier.at1_vo.voix", { v: who.join(", ") }) : "") + ".");
  } catch (e) { toast(dzT("atelier.at1_vo.ko", { msg: e.message }), true); }
}

async function chapterVo() {
  if (!chapter) { toast(dzT("atelier.at1_chap.ouvre"), true); return; }
  if (!scenes.length) { toast(dzT("atelier.at1_vo.sans_scn"), true); return; }
  const missing = scenes.filter(s => !s.vo_audio).length;
  const force = missing === 0 &&
    await window.__dzDialogue.confirmer(dzT("atelier.at1_vo.tout_q"), { ok: dzT("atelier.at1_vo.tout") });
  if (missing === 0 && !force) return;
  toast(dzT("atelier.at1_vo.chapitre", { n: force ? scenes.length : missing }));
  try {
    const r = await api.send("POST", `/chapters/${chapter.id}/voiceover`,
                             { language: "fr", force });
    const poll = setInterval(async () => {
      try {
        const st = await api.get("/atelier/manuscript/" + r.job_id);
        if (!st.done) {
          $("#voTotal").textContent = `🔊 ${st.chapter_i}/${st.chapter_n}…`;
          await loadScenes(true);   // les durées apparaissent au fil de l'eau
          return;
        }
        clearInterval(poll);
        if (st.error) { toast(dzT("atelier.at1_vo.erreur", { msg: st.error }), true); await loadScenes(true); return; }
        await loadScenes(true);
        toast(dzT("atelier.at1_vo.chap_minute", { d: fmtDur(st.stats.duree_totale_s || 0), g: st.stats.scenes_generees, c: st.stats.scenes_conservees }));
      } catch (e) { /* poll silencieux */ }
    }, 2500);
  } catch (e) { toast(dzT("atelier.at1_vo.erreur", { msg: e.message }), true); }
}

/* ═════════ tâche #64 (plan chapitres T13) — importer un scénario Fountain / Final Draft ═════════
   Remplacer (défaut) : le dialogue NOMME les scènes et les voix-off perdues, et le scénario entier est sauvegardé
   avant (tiroir des versions, « scénario importé ») ; sinon ajouter à la suite ; Échap deux fois = rien. */
async function importerScenario(f) {
  if (!f || !chapter) { if (!chapter) toast(dzT("atelier.at1_chap.ouvre"), true); return; }
  let mode = "remplacer";
  if (scenes.length) {
    const vo = scenes.filter(s => s.vo_audio).length;
    const remplacer = await window.__dzDialogue.confirmer(
      (vo ? dzT("atelier.at1_imp.remplacera_vo", { f: f.name, n: scenes.length, vo })
          : dzT("atelier.at1_imp.remplacera", { f: f.name, n: scenes.length })),
      { ok: dzT("atelier.at1_emp.remplacer"), annuler: dzT("atelier.at1_imp.ne_pas") });
    if (!remplacer) {
      if (!await window.__dzDialogue.confirmer(dzT("atelier.at1_imp.ajouter_q", { f: f.name, n: scenes.length }),
          { ok: dzT("atelier.at1_imp.ajouter") })) return;
      mode = "ajouter";
    }
  }
  const fd = new FormData(); fd.append("file", f); fd.append("mode", mode);
  toast(dzT("atelier.at1_imp.import", { f: f.name }));
  try {
    const r = await fetch(`/api/chapters/${encodeURIComponent(chapter.id)}/screenplay/import`, { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail && d.detail.message ? d.detail.message : (d.detail || r.statusText));
    await loadScenes(true);
    const ign = Object.entries(d.ignores || {}).map(([k, n]) => `${n} ${k.replace(/_/g, " ")}`).join(", ");
    toast((mode === "ajouter" ? dzT("atelier.at1_imp.ajoutees", { fmt: d.format === "fdx" ? "Final Draft" : "Fountain", n: d.scenes })
          : dzT("atelier.at1_imp.importees", { fmt: d.format === "fdx" ? "Final Draft" : "Fountain", n: d.scenes })) +
          (d.lieux_crees ? dzT("atelier.at1_imp.lieux", { n: d.lieux_crees }) : "") +
          (d.personnages_lies ? dzT("atelier.at1_imp.persos", { n: d.personnages_lies }) : "") +
          (d.prologue ? dzT("atelier.at1_imp.prologue") : "") +
          (ign ? dzT("atelier.at1_imp.ecartes", { ign }) : "") + ".");
  } catch (e) { toast(dzT("atelier.at1_imp.ko", { msg: e.message }), true); }
}

/* ═════════ tâche #65 (plan chapitres T16) — les exports : téléchargés par fetch, erreurs DITES ═════════
   Un lien <a download> nu rendrait une erreur 400 en fichier JSON : ici l'erreur passe par le dialogue maison, et les
   caractères remplacés dans un PDF (hors police standard) sont annoncés. */
async function telechargerExport(chemin) {
  if (!chapter) { toast(dzT("atelier.at1_chap.ouvre"), true); return; }
  toast(dzT("atelier.at1_exp.encours"));
  try {
    const r = await fetch(`/api/chapters/${encodeURIComponent(chapter.id)}/${chemin}`);
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      await window.__dzDialogue.informer(dzT("atelier.at1_exp.impossible", { msg: d.detail || r.statusText }), { titre: "Export" });
      return;
    }
    const cd = r.headers.get("Content-Disposition") || "";
    const m = cd.match(/filename\*=UTF-8''([^;]+)/i);
    const nom = m ? decodeURIComponent(m[1]) : (chapter.title || "export");
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url; a.download = nom; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    const n = parseInt(r.headers.get("X-DZ-Remplacements") || "0", 10);
    toast(dzT("atelier.at1_exp.exporte", { nom }) + (n ? dzT("atelier.at1_exp.remplaces", { n }) : "."));
  } catch (e) { toast(dzT("atelier.at1_exp.ko", { msg: e.message }), true); }
}

/* ═════════ tâche #66 (plan chapitres T17) — réécrire dans le ton de la bible ═════════
   Trois temps : DEVIS (gratuit) -> dialogue qui DIT le coût -> proposition (payée, plafonds) ; appliquer est gratuit,
   sauvegardé (version « réécriture ») et refusé si le passage a changé entre-temps (409). L'action est gardée ICI :
   le sélecteur, lui, revient à « Réécrire… ». */
let reeEnCours = null;      // {start, end, action, mode, attendu, langue}
const REE_LANGUES = { fr: dzT("atelier.at2_ree.lang_fr"), en: dzT("atelier.at2_ree.lang_en"), es: dzT("atelier.at2_ree.lang_es"), de: dzT("atelier.at2_ree.lang_de"), it: dzT("atelier.at2_ree.lang_it"), pt: dzT("atelier.at2_ree.lang_pt") };

async function sauverMaintenant() {
  if (!chapter || emporte) return;
  clearTimeout(saveTimer);
  chapter.script_text = $("#script").value;
  await api.send("PUT", "/chapters/" + chapter.id, { title: chapter.title, series: chapter.series,
    script_text: chapter.script_text, spans: chapter.spans });
}

async function reecrire(action) {
  const sel = currentSelection();
  if (!chapter || !sel) { toast(dzT("atelier.at2_ree.selection"), true); return; }
  let langue = "fr";
  if (action === "traduire") {
    const l = await window.__dzDialogue.saisir(`${dzT("atelier.at2_ree.langue_cible")} ${Object.entries(REE_LANGUES).map(([k, v]) => `${k} (${v})`).join(", ")}`,
      { valeur: "en", ok: dzT("atelier.at2_ree.chiffrer"), titre: dzT("atelier.at2_ree.traduire") });
    if (l == null) return;
    langue = l.trim().toLowerCase().slice(0, 2);
    if (!REE_LANGUES[langue]) { toast(dzT("atelier.at2_ree.langue_inconnue", { l }), true); return; }
  }
  try {
    await sauverMaintenant();                               // le serveur chiffre et propose sur le texte À JOUR
    const corps = { start: sel.start, end: sel.end, action, language: langue };
    const dv = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/reecrire`, { ...corps, devis: true });
    const usd = `${(dv.usd || 0).toFixed(3).replace(".", ",")} $`;
    if (!await window.__dzDialogue.confirmer(
        dzT("atelier.at2_ree.devis", { action: $("#reeAction").querySelector(`option[value="${action}"]`).textContent.replace("…", ""),
          fournisseur: dv.fournisseur, jetons: dv.jetons.entree + dv.jetons.sortie, usd }),
        { ok: dzT("atelier.at2_ree.proposer") })) return;
    toast(dzT("atelier.at2_ree.relit"));
    const d = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/reecrire`, corps);
    reeEnCours = { start: d.start, end: d.end, action, mode: d.mode, attendu: d.attendu, langue };
    $("#reeTitre").textContent = d.mode === "remplace" ? dzT("atelier.at2_ree.titre_remplace") : dzT("atelier.at2_ree.titre_insere");
    $("#reeNote").textContent = `${action}${action === "traduire" ? " → " + REE_LANGUES[langue] : ""} · ${d.provider}`;
    $("#reeTexte").value = d.proposition;
    $("#reeModal").classList.remove("hidden");
  } catch (e) { toast(dzT("atelier.at2_ree.err", { msg: e.message }), true); }
}

async function reecrireAppliquer() {
  if (!reeEnCours || !chapter) return;
  try {
    clearTimeout(saveTimer);                                // une sauvegarde en attente n'écrasera pas le texte appliqué
    await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/reecrire`, {
      start: reeEnCours.start, end: reeEnCours.end, action: reeEnCours.action, language: reeEnCours.langue,
      appliquer: true, texte: $("#reeTexte").value, attendu: reeEnCours.attendu });
    $("#reeModal").classList.add("hidden");
    reeEnCours = null;
    await openChapter(chapter.id);                          // texte ET surlignage recalculés par le serveur
    toast(dzT("atelier.at2_ree.applique"));
  } catch (e) { toast(dzT("atelier.at2_ree.err_appliquer", { msg: e.message }), true); }
}

async function adaptChapter() {
  if (!chapter) { toast(dzT("atelier.at2_chap.ouvrir_dabord"), true); return; }
  if (scenes.length && !await window.__dzDialogue.confirmer(dzT("atelier.at2_adapt.confirmer"), { ok: dzT("atelier.at2_adapt.readapter") })) return;
  toast(dzT("atelier.at2_adapt.en_cours"));
  try {
    const r = await api.send("POST", `/chapters/${chapter.id}/screenplay/adapt`,
                             { language: "fr" });
    const poll = setInterval(async () => {
      try {
        const st = await api.get("/atelier/manuscript/" + r.job_id);
        if (!st.done) return;
        clearInterval(poll);
        if (st.error) { toast(dzT("atelier.at2_adapt.echec", { msg: st.error }), true); return; }
        await loadEntities();
        await loadScenes(true);
        await renderBible();
        toast((st.stats.entites_creees ? dzT("atelier.at2_adapt.fin_lieux", { n: st.stats.scenes, m: st.stats.entites_creees })
              : dzT("atelier.at2_adapt.fin_bible", { n: st.stats.scenes })));
      } catch (e) { /* poll silencieux */ }
    }, 2000);
  } catch (e) { toast(dzT("atelier.at2_adapt.err", { msg: e.message }), true); }
}

async function loadShots(render) {
  if (!chapter) { shots = []; if (render) renderBoard(); return; }
  shots = (await api.get(`/chapters/${chapter.id}/shots`)).shots;
  if (render) renderBoard();
}

function fmtDur(s) {
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}

function entChips(ids) {
  return (ids || []).map(id => {
    const e = entities.find(x => x.id === id);
    return e ? `<span class="chip k-${e.kind}">${esc(e.name.length > 22 ? e.name.slice(0, 22) + "…" : e.name)}</span>` : "";
  }).join("");
}

function renderBoard() {
  $("#boardTotal").textContent = "Σ " + fmtDur(shots.reduce((a, s) => a + (s.duration_s || 0), 0));
  const list = $("#shotList");
  if (!chapter) { list.innerHTML = `<div class="empty-note">${dzT("atelier.at2_sb.vide_chap")}</div>`; return; }
  if (!shots.length) {
    list.innerHTML = `<div class="empty-note">${dzT("atelier.at2_sb.vide")}<br>
      ${dzT("atelier.at2_sb.vide_ia")}<br>
      ${dzT("atelier.at2_sb.vide_para")}</div>`;
    return;
  }
  list.innerHTML = shots.map((s, i) => `
  <div class="shot-card" data-id="${s.id}">
    <div class="thumb">
      ${s.sketch_image
        ? `<img src="/api/images/${encodeURIComponent(s.sketch_image)}" alt="${dzT("atelier.at2_sb.croquis")}">`
        : `<div class="noimg">${dzT("atelier.at2_sb.pas_croquis")}<br>— 🎨 ⤵</div>`}
      ${s.sketch_seed != null ? `<div class="seedtag">${ico("dz-etat-verrouille")} ${s.sketch_seed}</div>` : ""}
      <div class="entity-actions">
        <button class="btn primary act-sketch" title="${dzT("atelier.at2_sb.gen_croquis_t")}" aria-label="${dzT("atelier.at2_sb.gen_croquis")}">${ico("dz-media-generer-image")}</button>
        <button class="btn act-resketch" title="${dzT("atelier.at2_sb.nouveau_croquis")}" aria-label="${dzT("atelier.at2_sb.nouveau_croquis")}">${ico("dz-action-aleatoire")}</button>
        <button class="btn ghost act-prod" title="${dzT("atelier.at2_sb.prod_t")}" aria-label="${dzT("atelier.at2_sb.prod")}">${ico("dz-media-generer-image")}</button>
        <button class="btn ghost act-plateau" title="${dzT("atelier.at2_sb.plateau_t")}" aria-label="${dzT("atelier.at2_sb.plateau")}">${ico("dz-nav-plateau")}</button>
      </div>
      ${s.image ? `<div class="shot-prod"><img src="/api/images/${encodeURIComponent(s.image)}" alt="${dzT("atelier.at2_sb.prod_alt")}"
        title="${dzT("atelier.at2_sb.prod_refs", { n: s.image_refs || 0 })}"><span>${ico("dz-media-image")} ${s.image_refs || 0} ${dzT("atelier.at2_sb.ref_abr")}</span>
        <button class="btn ghost act-derive" title="${dzT("atelier.at2_sb.derive_t")}" aria-label="${dzT("atelier.at2_sb.derive")}">${ico("dz-action-mesurer")}</button></div>
        <div class="shot-derive"></div>` : ""}
    </div>
    <div class="shot-main">
      <div class="rowhead">
        <span class="shot-no">${dzT("atelier.at2_sb.plan_no", { i: i + 1, n: shots.length })}</span>
        <div class="shot-actions">
          <button class="btn ghost act-up" title="${dzT("atelier.at2_sb.monter")}" aria-label="${dzT("atelier.at2_sb.monter")}" ${i === 0 ? "disabled" : ""}>${ico("dz-edit-monter")}</button>
          <button class="btn ghost act-down" title="${dzT("atelier.at2_sb.descendre")}" aria-label="${dzT("atelier.at2_sb.descendre")}" ${i === shots.length - 1 ? "disabled" : ""}>${ico("dz-edit-descendre")}</button>
          <button class="btn ghost act-insert" title="${dzT("atelier.at2_sb.inserer")}" aria-label="${dzT("atelier.at2_sb.inserer")}">${ico("dz-action-ajouter")}</button>
          <button class="btn ghost act-delshot" title="${dzT("atelier.at2_sb.supprimer")}" aria-label="${dzT("atelier.at2_sb.supprimer")}">${ico("dz-action-supprimer")}</button>
        </div>
      </div>
      <textarea class="shot-action" placeholder="${dzT("atelier.at2_sb.action_ph")}">${esc(s.action)}</textarea>
      <div class="shot-params">
        <select class="shot-type" title="${dzT("atelier.at2_sb.type")}">
          ${SHOT_TYPES.map(t => `<option ${t === s.shot_type ? "selected" : ""}>${t}</option>`).join("")}
        </select>
        <select class="shot-cam" title="${dzT("atelier.at2_sb.camera")}">
          ${CAMERA_MOVES.map(t => `<option ${t === s.camera_move ? "selected" : ""}>${t}</option>`).join("")}
        </select>
        <input class="shot-dur" type="number" min="0.5" max="60" step="0.5" value="${s.duration_s}" title="${dzT("atelier.at2_sb.duree")}">
      </div>
      <div class="shot-params shot-craft">
        <select class="shot-recipe" title="${dzT("atelier.at2_sb.recette")}">${recipeOptions(s.motion_recipe)}</select>
        <span class="sel-ico" aria-hidden="true">${ico("dz-edit-energie")}</span><select class="shot-energy" title="${dzT("atelier.at2_sb.energie")}">${energyOptions(s.energy)}</select>
      </div>
      <div class="shot-ents">${entChips(s.entities) || `<span style='opacity:.5'>${dzT("atelier.at2_sb.aucune_ent_det")}</span>`}</div>
      <div class="shot-cast" title="${dzT("atelier.at2_sb.cast_t")}">${(s.entities || []).map(eid => {
        const en = entities.find(x => x.id === eid);
        return en && en.kind === "character" ? castChip(en.name) : "";
      }).join("") || `<span style='opacity:.5'>${dzT("atelier.at2_sb.aucun_perso")}</span>`}</div>
      ${entPicker(s.entities)}
      ${s.source_text ? `<details class="shot-src"><summary>${dzT("atelier.at2_sb.texte_source")}</summary><blockquote>${esc(s.source_text)}</blockquote></details>` : ""}
    </div>
  </div>`).join("");

  list.querySelectorAll(".shot-card").forEach(card => {
    const id = card.dataset.id;
    const sh = () => shots.find(x => x.id === id);
    const save = debounce(async (fields) => {
      try {
        const up = await api.send("PUT", "/shots/" + id, fields());
        Object.assign(sh(), up);
        $("#boardTotal").textContent = "Σ " + fmtDur(shots.reduce((a, s) => a + (s.duration_s || 0), 0));
      } catch (e) { toast(dzT("atelier.at2_sb.err_sauver", { msg: e.message }), true); }
    }, 600);
    const fields = () => ({
      action: card.querySelector(".shot-action").value,
      shot_type: card.querySelector(".shot-type").value,
      camera_move: card.querySelector(".shot-cam").value,
      duration_s: parseFloat(card.querySelector(".shot-dur").value) || sh().duration_s,
      motion_recipe: card.querySelector(".shot-recipe").value || null,
      energy: card.querySelector(".shot-energy").value
        ? parseInt(card.querySelector(".shot-energy").value, 10) : null,
    });
    ["input", "change"].forEach(ev => {
      card.querySelector(".shot-action").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-type").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-cam").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-dur").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-recipe").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-energy").addEventListener(ev, () => save(fields));
    });
    card.querySelector(".act-sketch").addEventListener("click", () => sketchShot(id, sh().sketch_seed));
    card.querySelector(".act-prod").addEventListener("click", () => imageProduction(id));
    // t127 : le Plateau 3D du plan (la scène du plan est retrouvée, ou créée, par la page ; « ← Atelier » y ramène)
    card.querySelector(".act-plateau").addEventListener("click", () => { location.href = "/plateau/?shot=" + encodeURIComponent(id); });
    card.querySelector(".act-derive")?.addEventListener("click", () => deriveProduction(id, card));
    card.querySelector(".act-resketch").addEventListener("click", () => sketchShot(id, null));
    card.querySelector(".act-insert").addEventListener("click", async () => {
      await api.send("POST", `/chapters/${chapter.id}/shots`, { after_id: id });
      await loadShots(true);
    });
    card.querySelector(".act-delshot").addEventListener("click", async () => {
      if (!await window.__dzDialogue.confirmer(dzT("atelier.at2_sb.supprimer_n", { i: sh().idx + 1 }))) return;
      await api.send("DELETE", "/shots/" + id);
      await loadShots(true);
    });
    card.querySelector(".act-up").addEventListener("click", () => moveShot(id, -1));
    card.querySelector(".act-down").addEventListener("click", () => moveShot(id, +1));
    card.querySelectorAll(".shot-ents-edit input").forEach(cb => cb.addEventListener("change", async () => {
      const ids = [...card.querySelectorAll(".shot-ents-edit input:checked")].map(x => x.value);
      try {
        const up = await api.send("PUT", "/shots/" + id, { entities: ids });
        Object.assign(sh(), up);
        card.querySelector(".shot-ents").innerHTML = entChips(up.entities) || `<span style='opacity:.5'>${dzT("atelier.at2_sb.aucune_ent")}</span>`;
      } catch (e) { toast(dzT("atelier.at2_sb.err_ents", { msg: e.message }), true); }
    }));
  });
}

async function moveShot(id, delta) {
  const ids = shots.map(s => s.id);
  const i = ids.indexOf(id), j = i + delta;
  if (j < 0 || j >= ids.length) return;
  [ids[i], ids[j]] = [ids[j], ids[i]];
  const r = await api.send("POST", `/chapters/${chapter.id}/storyboard/reorder`, { ids });
  shots = r.shots;
  renderBoard();
}

async function sketchShot(id, seed) {
  const s = shots.find(x => x.id === id);
  if (!s) return;
  if (!(s.action || s.source_text || "").trim()) { toast(dzT("atelier.at2_cq.action_dabord"), true); return; }
  toast(dzT("atelier.at2_cq.en_cours", { i: s.idx + 1 }));
  try {
    const up = await api.send("POST", `/shots/${id}/sketch`,
                              seed != null ? { seed } : {});
    Object.assign(s, up);
    renderBoard();
    toast(dzT("atelier.at2_cq.fait", { i: s.idx + 1, seed: up.sketch_seed }));
  } catch (e) { toast(dzT("atelier.at2_cq.echec", { msg: e.message }), true); }
}

/* ═════════ tâche #62 (plan chapitres T8) — l'image de PRODUCTION d'un plan ═════════
   Nano Banana reçoit les vues des entités du plan. Dépense réelle : le coût (grille du PC) est DIT et CONFIRMÉ avant ;
   au-delà d'un plafond mensuel, dz-plafonds.js montre le dialogue 402 et rejoue sur confirmation. */
async function imageProduction(id) {
  const s = shots.find(x => x.id === id);
  if (!s) return;
  if (!(s.entities || []).length) { toast(dzT("atelier.at2_prod.lier"), true); return; }
  let provider = "nano-banana-pro", usd = null;
  try {
    provider = (await api.get("/atelier/settings")).settings.image_provider || provider;
    const grille = await api.get("/cost/pricing");
    usd = grille[provider === "nano-banana" ? "nano_banana_usd" : "nano_banana_pro_usd"];
  } catch (e) { /* le coût reste inconnu : on le dit */ }
  if (provider !== "nano-banana" && provider !== "nano-banana-pro") {
    toast(dzT("atelier.at2_prod.multi_refs", { provider }), true);
    return;
  }
  const cout = typeof usd === "number" ? `${usd.toFixed(3).replace(".", ",")} $` : dzT("atelier.at2_prod.cout_inconnu");
  if (!await window.__dzDialogue.confirmer(
      dzT("atelier.at2_prod.confirmer", { i: s.idx + 1, modele: provider === "nano-banana" ? "Nano Banana" : "Nano Banana Pro", cout }),
      { ok: dzT("atelier.at2_prod.generer") })) return;
  toast(dzT("atelier.at2_prod.en_cours", { i: s.idx + 1 }));
  try {
    const up = await api.send("POST", `/shots/${encodeURIComponent(id)}/image`, {});
    Object.assign(s, up);
    renderBoard();
    toast(dzT("atelier.at2_prod.fait", { i: s.idx + 1, n: up.image_refs }));
  } catch (e) { toast(dzT("atelier.at2_prod.err", { msg: e.message }), true); }
}

/* ═════════ tâche #62 (plan chapitres T6) — la DÉRIVE de l'image de production, en lecture ═════════
   Gratuit, rien n'est décidé : l'écart de couleur (ΔE) et de silhouette avec la vue de chaque entité, et l'angle mort. */
async function deriveProduction(id, card) {
  const box = card.querySelector(".shot-derive");
  if (!box) return;
  box.textContent = dzT("atelier.at2_drv.mesure");
  try {
    const d = await api.get(`/shots/${encodeURIComponent(id)}/derive`);
    const lignes = (d.entites || []).map(e => e.vue == null
      ? `<div class="drv-l"><b>${esc(e.name)}</b> — ${dzT("atelier.at2_drv.sans_vue")}</div>`
      : `<div class="drv-l drv-${e.verdict === "stable" ? "ok" : "ko"}"><b>${esc(e.name)}</b> ${e.verdict === "stable" ? dzT("atelier.at2_drv.stable") : dzT("atelier.at2_drv.derive")}
         · ${dzT("atelier.at2_drv.couleur", { e: e.ecart_couleur.toFixed(1).replace(".", ","), s: d.seuils.couleur })}
         · ${dzT("atelier.at2_drv.silhouette", { e: e.ecart_silhouette.toFixed(2).replace(".", ","), s: String(d.seuils.silhouette).replace(".", ",") })}
         <span class="drv-vue" title="${dzT("atelier.at2_drv.vue_t", { f: escA(e.fichier), s: escA(e.source) })}">vs ${esc(e.vue)}</span></div>`);
    box.innerHTML = (lignes.join("") || `<div class="drv-l">${dzT("atelier.at2_drv.aucune")}</div>`)
      + `<div class="drv-mort" title="${dzT("atelier.at2_drv.mort_t")}">${dzT("atelier.at2_drv.mort", { t: esc(d.angle_mort) })}</div>`;
  } catch (e) { box.textContent = dzT("atelier.at2_drv.err", { msg: e.message }); }
}

/* ═════════ tâche #63 (plan chapitres T11) — l'animatique : devis, progression, lecteur ═════════
   Muette et gratuite par défaut (décision du 02/10) ; la voix témoin (Narrateur de la bible) est cochée à la main,
   son coût — seulement les voix PAS encore en cache — est dit et confirmé avant ; au-delà d'un plafond, dz-plafonds.js
   montre le dialogue 402 et rejoue sur confirmation. */
let animDevis = null;

async function animatiqueEtat() {
  if (!chapter) return null;
  $("#animDevis").textContent = dzT("atelier.at2_anim.devis");      // la sonde de Voicebox local peut prendre quelques secondes
  const e = await api.get(`/chapters/${encodeURIComponent(chapter.id)}/animatique`);
  animDevis = e.voix || {};
  const v = animDevis, box = $("#animVoix");
  let dit = "", ok = true;
  if (!v.fournisseur) { dit = dzT("atelier.at2_anim.sans_voix"); ok = false; }
  else if (!v.narrateur) { dit = dzT("atelier.at2_anim.sans_narrateur"); ok = false; }
  else if (!v.a_generer) dit = dzT("atelier.at2_anim.cache", { nom: v.narrateur });
  else if (v.fournisseur === "elevenlabs") dit = dzT("atelier.at2_anim.devis_11", { nom: v.narrateur, n: v.a_generer, car: v.caracteres, usd: v.usd.toFixed(3).replace(".", ",") });
  else dit = dzT("atelier.at2_anim.devis_vb", { nom: v.narrateur, n: v.a_generer });
  box.disabled = !ok;
  if (!ok) box.checked = false;
  $("#animDevis").textContent = dit;
  $("#animVideo").classList.toggle("hidden", !e.existe);
  $("#animVide").classList.toggle("hidden", !!e.existe);
  if (e.existe) $("#animVideo").src = `${e.url}?t=${Math.round(e.maj || 0)}`;
  await sortiesEtat();                                       // tâche #66 : film / reel vers le Montage
  $("#animNote").textContent = dzT("atelier.at2_anim.n_plans", { n: e.storyboard }) + (e.existe ? " · " + dzT("atelier.at2_anim.dernier", { n: e.plans }) : "");
  return e;
}

async function ouvrirAnimatique() {
  if (!chapter) { toast(dzT("atelier.at2_chap.ouvrir_dabord"), true); return; }
  $("#animProgress").classList.add("hidden");
  $("#animModal").classList.remove("hidden");
  try { await animatiqueEtat(); } catch (e) { toast(dzT("atelier.at2_anim.err", { msg: e.message }), true); }
}

function animProgres(st) {
  const n = st.chapter_n || 0, i = st.chapter_i || 0;
  const pct = st.done ? 100 : n ? Math.round(100 * i / n) : 0;
  $("#animBar").style.width = pct + "%";
  $("#animStatus").textContent = st.error ? dzT("atelier.at2_anim.echec", { msg: st.error }) : (st.message || "…");
}

async function monterAnimatique() {
  if (!chapter) return;
  if (!shots.length) { toast(dzT("atelier.at2_anim.decoupe_dabord"), true); return; }
  const voix = $("#animVoix").checked;
  if (voix) {
    try { await animatiqueEtat(); } catch (_) { /* le devis d'avant reste affiché */ }
    const v = animDevis || {};
    if (v.fournisseur === "elevenlabs" && v.a_generer > 0 && !await window.__dzDialogue.confirmer(
        dzT("atelier.at2_anim.confirmer_voix", { n: v.a_generer, car: v.caracteres, nom: v.narrateur, usd: v.usd.toFixed(3).replace(".", ",") }),
        { ok: dzT("atelier.at2_anim.generer_voix") })) return;
  }
  $("#animGo").disabled = true;
  $("#animProgress").classList.remove("hidden");
  animProgres({ message: dzT("atelier.at2_anim.en_cours") });
  try {
    const r = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/animatique`, { voix, language: "fr" });
    let st = {};
    while (!st.done) {
      await new Promise(res => setTimeout(res, 700));
      st = await api.get(`/atelier/manuscript/${r.job_id}`);
      animProgres(st);
    }
    if (st.error) { toast(dzT("atelier.at2_anim.echouee", { msg: st.error }), true); return; }
    await animatiqueEtat();
    const s = st.stats || {};
    toast(dzT("atelier.at2_anim.fait", { plans: s.plans, voix: s.voix, duree: fmtDur(s.duree_s || 0) }));
  } catch (e) {
    toast(dzT("atelier.at2_anim.err", { msg: e.message }), true);
  } finally { $("#animGo").disabled = false; }
}

/* ═════════ tâche #66 PR B — l'animatique sort vers le Montage (film / reel), en NOUVEAU projet ═════════ */
/* ═════════ tâche #66 PR C — la sortie « épisode », sans rendu ═════════ */
async function versEpisode() {
  if (!chapter) { toast(dzT("atelier.at2_chap.ouvrir_dabord"), true); return; }
  try {
    const r = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/episode`, { language: "fr" });
    if (await window.__dzDialogue.confirmer(
        dzT("atelier.at2_sortie.episode", { titre: r.title, scenes: r.scenes, images: r.images }),
        { ok: dzT("atelier.at2_sortie.aller_episodes"), annuler: dzT("atelier.at2_sortie.rester"), titre: dzT("atelier.at2_sortie.episode_titre") }))
      window.open(r.vue, "_blank");
  } catch (e) { toast(dzT("atelier.at2_sortie.err_episode", { msg: e.message }), true); }
}

async function sortiesEtat() {
  if (!chapter) return;
  try {
    const s = await api.get(`/chapters/${encodeURIComponent(chapter.id)}/sorties`);
    $("#animSorties").classList.toggle("hidden", !s.animatique);
    ["film", "reel"].forEach(n => { const b = $(`[data-sortie="${n}"]`), v = (s.natures || {})[n];
      b.disabled = !s.a_jour;
      if (v) b.innerHTML = `${ico(n === "film" ? "dz-media-film" : "dz-media-reel")} ${n === "film" ? "Film" : "Reel"} · ${dzT("atelier.at2_sortie.bouton", { n: v.plans, d: esc(fmtDur(v.duree_s)) })}`; });
    $("#animSortieNote").textContent = s.animatique && !s.a_jour ? dzT("atelier.at2_sortie.perime") : "";
  } catch (_) { $("#animSorties").classList.add("hidden"); }
}

async function sortieMontage(nature) {
  if (!chapter) return;
  try {
    const r = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/sortie/${nature}`, {});
    if (await window.__dzDialogue.confirmer(
        dzT("atelier.at2_sortie.montage", { nom: r.name, plans: r.plans, duree: fmtDur(r.duree_s), voix: r.voix }),
        { ok: dzT("atelier.at2_sortie.aller_montage"), annuler: dzT("atelier.at2_sortie.rester"), titre: dzT("atelier.at2_sortie.montage_titre") }))
      window.open(r.montage, "_blank");
  } catch (e) { toast(dzT("atelier.at2_sortie.err_montage", { msg: e.message }), true); }
}

async function decoupe(method) {
  if (!chapter) { toast(dzT("atelier.at2_chap.ouvrir_dabord"), true); return; }
  if (!$("#script").value.trim()) { toast(dzT("atelier.at2_dec.vide"), true); return; }
  if (shots.length && !await window.__dzDialogue.confirmer(dzT("atelier.at2_dec.confirmer"), { ok: dzT("atelier.at2_dec.redecouper") })) return;
  toast(method === "ai" ? dzT("atelier.at2_dec.ia") : dzT("atelier.at2_dec.para"));
  try {
    const r = await api.send("POST", `/chapters/${chapter.id}/storyboard/decoupe`,
                             { method, language: "fr" });
    if (r.error) { toast(r.error, true); return; }
    shots = r.shots;
    renderBoard();
    toast(dzT("atelier.at2_dec.fait", { n: shots.length }));
  } catch (e) { toast(dzT("atelier.at2_dec.echec", { msg: e.message }), true); }
}

/* ═════════ Library modal (générique: callback au choix d'une image) ═════════ */
let libOnPick = null;   // (filename) => void — posé par openLibrary

async function attachInspiration(filename) {
  const ent = entities.find(x => x.id === libTarget);
  if (!ent || !filename) return;
  const insp = [...(ent.inspiration_images || [])];
  if (!insp.includes(filename)) insp.push(filename);
  const up = await api.send("PUT", "/bible/entities/" + libTarget, { inspiration_images: insp });
  Object.assign(ent, up);
  renderBible();
  toast(dzT("atelier.at2_lib.inspiration", { filename }));
}

async function openLibrary(entityId, onPick) {
  libTarget = entityId;
  libOnPick = onPick || attachInspiration;
  const grid = $("#libGrid");
  grid.innerHTML = `<div class="empty-note">${dzT("atelier.at2_lib.chargement")}</div>`;
  $("#libModal").classList.remove("hidden");
  try {
    const d = await api.get("/images");
    const files = (d.images || []).map(x => typeof x === "string" ? x : x.filename).filter(Boolean);
    grid.innerHTML = files.length
      ? files.map(f => `<img src="/api/images/${encodeURIComponent(f)}" data-f="${esc(f)}" title="${esc(f)}">`).join("")
      : `<div class="empty-note">${dzT("atelier.at2_lib.vide")}</div>`;
    grid.querySelectorAll("img").forEach(img =>
      img.addEventListener("click", async () => {
        $("#libModal").classList.add("hidden");
        await libOnPick(img.dataset.f);
      }));
  } catch (e) { grid.innerHTML = `<div class="empty-note">${dzT("atelier.at2_lib.erreur", { msg: esc(e.message) })}</div>`; }
}

/* ═════════ ancrage 3D d'une entité (spec Magnific §9.1) ═════════
   « Employer le flux image → 3D lorsque l'application a besoin de verrouiller
   un produit, accessoire, véhicule, élément de décor ou personnage stylisé. »
   La bible verrouillait en 2D (planche + seed) ; ici elle gagne un maillage.
   Deux garde-fous portés par l'UI : on choisit UNE vue (jamais la planche
   composite, que la route refuserait), et le moteur + son coût sont annoncés
   AVANT de lancer. */

const BESOIN_3D_PAR_KIND = {
  character: "hero", object: "prop", place: "decor", decor: "decor",
};
let engines3d = null;

async function catalogue3d() {
  if (engines3d) return engines3d;
  try { engines3d = await api.get("/assets3d/engines"); }
  catch { engines3d = { engines: [], besoins: [] }; }
  return engines3d;
}

async function entityTo3D(id) {
  const ent = entities.find(x => x.id === id);
  if (!ent) return;
  const besoin = BESOIN_3D_PAR_KIND[ent.kind];
  if (!besoin) { toast(dzT("atelier.at2_3d.kinds"), true); return; }

  const cat = await catalogue3d();
  const b = (cat.besoins || []).find(x => x.id === besoin) || {};
  const eng = (cat.engines || []).find(x => x.id === b.engine) || {};
  if (eng.available === false) {
    toast(dzT("atelier.at2_3d.cle_fal"), true);
    return;
  }
  toast(dzT("atelier.at2_3d.une_vue"));
  openLibrary(id, async (f) => {
    const cout = eng.usd_texture != null ? `≈ ${eng.usd_texture} $` : dzT("atelier.at2_3d.inconnu");
    const ok = await window.__dzDialogue.confirmer(
      dzT("atelier.at2_3d.confirmer", { nom: ent.name, moteur: eng.label || b.engine || "?", why: b.why || "—", vue: f, cout }));
    if (!ok) return;
    try {
      const r = await api.send("POST", `/bible/entities/${id}/model3d`,
                               { image_filename: f, besoin });
      toast(dzT("atelier.at2_3d.en_cours", { engine: r.engine }));
      const poll = setInterval(async () => {
        try {
          const st = await api.get("/jobs/" + r.job_id);
          if (st.status !== "done" && st.status !== "failed") return;
          clearInterval(poll);
          if (st.status === "failed") { toast(dzT("atelier.at2_3d.err", { msg: st.error || dzT("atelier.at2_3d.echec") }), true); return; }
          await loadEntities();
          await renderBible();
          toast(dzT("atelier.at2_3d.fait", { nom: ent.name }));
        } catch (e) { /* poll silencieux */ }
      }, 3000);
    } catch (e) { toast(dzT("atelier.at2_3d.err", { msg: e.message }), true); }
  });
}

/* ═════════ casting voix (B) ═════════ */
function playVoicePrev(url) {
  if (!url) return;
  try {
    if (voiceAudio) { voiceAudio.pause(); voiceAudio = null; }
    voiceAudio = new Audio(url);
    voiceAudio.play().catch(() => toast(dzT("atelier.at2_voix.preecoute_ko"), true));
  } catch (e) { /* silencieux */ }
}

async function loadVoices11() {
  if (voices11) return voices11;
  const d = await api.get("/voices");
  if (!d.enabled) throw new Error(dzT("atelier.at2_voix.cle_11"));
  voices11 = d.voices || [];
  return voices11;
}

function voiceChip(v, entityId) {
  const lbl = v.labels || {};
  const meta = [lbl.gender, lbl.age, lbl.accent].filter(Boolean).join(" · ");
  return `<span class="voice-chip" data-vid="${v.voice_id}">
    <b>${esc(v.name)}</b>${meta ? ` <i>${esc(meta)}</i>` : ""}
    ${v.preview_url ? `<button class="btn ghost vc-play" data-prev="${esc(v.preview_url)}" title="${dzT("atelier.at2_voix.preecouter")}" aria-label="${dzT("atelier.at2_voix.preecouter")}">${ico("dz-media-lecture")}</button>` : ""}
    <button class="btn vc-pick" title="${dzT("atelier.at2_voix.attribuer")}" aria-label="${dzT("atelier.at2_voix.attribuer")}">${ico("dz-action-valider")}</button>
  </span>`;
}

function wireVoiceChips(container, entityId) {
  container.querySelectorAll(".vc-play").forEach(b =>
    b.addEventListener("click", () => playVoicePrev(b.dataset.prev)));
  container.querySelectorAll(".vc-pick").forEach(b =>
    b.addEventListener("click", async () => {
      const chip = b.closest(".voice-chip");
      const vid = chip.dataset.vid;
      const v = (voices11 || []).find(x => x.voice_id === vid);
      const ent = entities.find(x => x.id === entityId);
      const up = await api.send("PUT", "/bible/entities/" + entityId, {
        voice_id: vid, voice_name: v ? v.name : vid,
        voice_prev: v ? v.preview_url : null,
      });
      Object.assign(ent, up);
      toast(dzT("atelier.at2_voix.attribuee", { voix: up.voice_name, nom: ent.name }));
      renderBible();
    }));
}

async function suggestVoice(entityId, card) {
  const ent = entities.find(x => x.id === entityId);
  if (!ent) return;
  if (!(ent.description || "").trim()) {
    toast(dzT("atelier.at2_voix.decrire"), true); return;
  }
  toast(dzT("atelier.at2_voix.casting", { nom: ent.name }));
  try {
    await loadVoices11();
    const d = await api.send("POST", `/bible/entities/${entityId}/suggest-voice`, {});
    Object.assign(ent, d.entity);
    await renderBible();
    // ré-afficher les alternatives sur la carte re-rendue
    const fresh = document.querySelector(`.entity-card[data-id="${entityId}"] .voice-alts`);
    if (fresh) {
      fresh.classList.remove("hidden");
      fresh.innerHTML = `<div class="voice-why">${esc(d.why || "")}</div>` +
        `<div class="voice-chiplist">${(d.alternates || []).map(v => voiceChip(v, entityId)).join("")}</div>`;
      wireVoiceChips(fresh, entityId);
    }
    toast(dzT("atelier.at2_voix.suggeree", { voix: d.suggested.name, nom: ent.name }) +
          ((d.alternates || []).length ? " " + dzT("atelier.at2_voix.alternatives", { n: d.alternates.length }) : "") + ".");
  } catch (e) { toast(dzT("atelier.at2_voix.echec", { msg: e.message }), true); }
}

async function showAllVoices(entityId, card) {
  try {
    const vs = await loadVoices11();
    const alts = card.querySelector(".voice-alts");
    alts.classList.toggle("hidden");
    if (alts.classList.contains("hidden")) return;
    alts.innerHTML = `<div class="voice-chiplist">${vs.map(v => voiceChip(v, entityId)).join("")}</div>`;
    wireVoiceChips(alts, entityId);
  } catch (e) { toast(e.message, true); }
}

/* ═════════ direction artistique (DA) ═════════ */
const STYLE_PRESETS = [
  { label: dzT("atelier.at2_da.p_bd"), canon: "ligne_claire", sp: "European comic book art (bande dessinée), clean ink outlines, flat cel colors, ligne claire influence, expressive faces, detailed backgrounds" },
  { label: dzT("atelier.at2_da.p_manga"), canon: "manga_shonen", sp: "anime manga art style, sharp linework, cel shading, dramatic lighting, detailed eyes, cinematic anime composition" },
  { label: dzT("atelier.at2_da.p_comics"), canon: "comics_heroic", sp: "American comic book style, bold inks, dynamic shading, halftone textures, dramatic panel lighting" },
  { label: dzT("atelier.at2_da.p_photo"), canon: "davinci", sp: "photorealistic, natural skin textures, realistic lighting, 85mm lens look, shallow depth of field" },
  { label: dzT("atelier.at2_da.p_cine"), canon: "cine", sp: "cinematic film still, anamorphic framing, filmic color grading, volumetric light, high production value" },
  { label: dzT("atelier.at2_da.p_sf"), canon: "bd_realiste", sp: "retro-futuristic science-fiction concept art, neon accents, brutalist megastructures, atmospheric haze" },
  { label: dzT("atelier.at2_da.p_aquarelle"), canon: "davinci", sp: "watercolor illustration, soft washes, visible paper grain, delicate ink lines, muted palette" },
  { label: dzT("atelier.at2_da.p_noir"), canon: "davinci", sp: "high-contrast black and white ink illustration, film noir shadows, dramatic chiaroscuro, crosshatching" },
  // Miroir du preset backend "vitrail" — le sp est LE bloc de la fiche épinglée
  // style_vitrail.json (test_style_vitrail.py vérifie l'égalité, zéro dérive).
  { label: dzT("atelier.at2_da.vitrail"), canon: "vitrail", sp: "monumental Art Nouveau stained-glass window design, Central European modernism of about 1900: bold sinuous dark leadlines #1F1512, thick supple contours enclosing every shape and covering about a tenth of the canvas, irregular fragments of intensely saturated glass in 3 to 5 major colours - cobalt blue #0047AB, ruby red #9B111E, emerald green #046307, golden amber #DAA520, deep violet #4A235A - light transmitted from within the image as through a window, frontal ascending composition in a vertical or ogival bay, one central figure filling roughly two thirds of the height, simple hierarchy of figure then radiating halo then ornamental border of stylized flowers on the outer edge of the frame, flat decorative space with no deep linear perspective, high readability at distance" },
];
// Miroir de PROPORTION_CANONS (backend) — canons de proportions issus des
// grandes écoles: De Vinci, manga japonais, ligne claire belge, école
// gros-nez franco-belge, Moebius, comics héroïques DC/Marvel…
const PROPORTION_CANONS = [
  { id: "auto", label: dzT("atelier.at2_da.c_auto"), hint: dzT("atelier.at2_da.c_auto_h") },
  { id: "davinci", label: dzT("atelier.at2_da.c_davinci"), hint: dzT("atelier.at2_da.c_davinci_h") },
  { id: "cine", label: dzT("atelier.at2_da.c_cine"), hint: dzT("atelier.at2_da.c_cine_h") },
  { id: "manga_shonen", label: dzT("atelier.at2_da.c_shonen"), hint: dzT("atelier.at2_da.c_shonen_h") },
  { id: "manga_shojo", label: dzT("atelier.at2_da.c_shojo"), hint: dzT("atelier.at2_da.c_shojo_h") },
  { id: "chibi", label: "Chibi / SD", hint: dzT("atelier.at2_da.c_chibi_h") },
  { id: "ligne_claire", label: dzT("atelier.at2_da.c_ligne"), hint: dzT("atelier.at2_da.c_ligne_h") },
  { id: "gros_nez", label: dzT("atelier.at2_da.c_gros_nez"), hint: dzT("atelier.at2_da.c_gros_nez_h") },
  { id: "bd_realiste", label: dzT("atelier.at2_da.c_bd_real"), hint: dzT("atelier.at2_da.c_bd_real_h") },
  { id: "comics_heroic", label: dzT("atelier.at2_da.c_heroic"), hint: dzT("atelier.at2_da.c_heroic_h") },
  { id: "vitrail", label: dzT("atelier.at2_da.vitrail"), hint: dzT("atelier.at2_da.c_vitrail_h") },
];
let daSettings = {};

function daSetCanon(id) {
  const sel = $("#daCanon");
  if (sel && [...sel.options].some(o => o.value === id)) sel.value = id;
  daCanonNote();
}
function daCanonNote() {
  const c = PROPORTION_CANONS.find(c => c.id === $("#daCanon").value);
  $("#daCanonNote").textContent = c ? c.hint : "";
}

function daRenderProposals(props) {
  const box = $("#daProposals");
  if (!props || !props.length) {
    box.innerHTML = `<div class="empty-note">${dzT("atelier.at2_da.vide")}</div>`;
    return;
  }
  box.innerHTML = props.map((p, i) => `
    <div class="da-card" data-sp="${esc(p.style_prompt)}" data-canon="${esc(p.canon || "")}">
      <b>${esc(p.label)}</b>
      <div class="da-sp">${esc(p.style_prompt)}</div>
      ${p.rationale ? `<div class="da-why">${esc(p.rationale)}</div>` : ""}
    </div>`).join("");
  box.querySelectorAll(".da-card").forEach(card =>
    card.addEventListener("click", () => {
      box.querySelectorAll(".da-card").forEach(c => c.classList.remove("sel"));
      card.classList.add("sel");
      $("#daStyle").value = card.dataset.sp;
      if (card.dataset.canon) daSetCanon(card.dataset.canon);
    }));
}

async function openDA() {
  try {
    const st = await api.get("/atelier/settings");
    daSettings = st.settings || {};
  } catch (e) { daSettings = {}; }
  $("#daStyle").value = daSettings.global_style || $("#globalStyle").value || "";
  let props = [];
  try { props = JSON.parse(daSettings.style_proposals || "[]"); } catch (e) { }
  daRenderProposals(props);
  $("#daPresets").innerHTML = STYLE_PRESETS.map(p =>
    `<span class="voice-chip da-preset" data-sp="${esc(p.sp)}" data-canon="${esc(p.canon)}" style="cursor:pointer"><b>${esc(p.label)}</b></span>`).join("");
  document.querySelectorAll(".da-preset").forEach(chip =>
    chip.addEventListener("click", () => {
      $("#daStyle").value = chip.dataset.sp;
      daSetCanon(chip.dataset.canon);
    }));
  // canon de proportions (De Vinci, manga, ligne claire, gros nez, DC…)
  $("#daCanon").innerHTML = PROPORTION_CANONS.map(c =>
    `<option value="${c.id}" title="${esc(c.hint)}">${esc(c.label)}</option>`).join("");
  $("#daCanon").value = daSettings.style_canon || "auto";
  if ($("#daCanon").selectedIndex < 0) $("#daCanon").value = "auto";
  $("#daCanon").onchange = daCanonNote;
  daCanonNote();
  // générateurs disponibles
  try {
    const pv = await api.get("/atelier/providers");
    const cur = daSettings.image_provider || "flux";
    $("#daProvider").innerHTML = pv.providers.map(p =>
      `<option value="${p.id}" ${p.id === cur ? "selected" : ""}>${esc(p.label)}</option>`).join("");
    const upd = () => {
      const sel = pv.providers.find(p => p.id === $("#daProvider").value);
      $("#daProviderNote").textContent = sel && !sel.seeds
        ? dzT("atelier.at3_da.sans_seeds")
        : dzT("atelier.at3_da.seeds_ok");
    };
    $("#daProvider").addEventListener("change", upd); upd();
  } catch (e) { $("#daProvider").innerHTML = `<option value="flux">FLUX (fal)</option>`; }
  $("#daRefName").textContent = daSettings.style_ref_image || dzT("atelier.at3_da.aucune");
  $("#daModal").classList.remove("hidden");
}

async function daApply() {
  try {
    await api.send("PUT", "/atelier/settings", {
      global_style: $("#daStyle").value.trim(),
      image_provider: $("#daProvider").value,
      style_canon: $("#daCanon").value,
      style_ref_image: $("#daRefName").textContent === dzT("atelier.at3_da.aucune")
        ? "" : $("#daRefName").textContent,
    });
    $("#globalStyle").value = $("#daStyle").value.trim();
    $("#daModal").classList.add("hidden");
    toast(dzT("atelier.at3_da.appliquee"));
  } catch (e) { toast(dzT("atelier.at3_da.err", { msg: e.message }), true); }
}

async function daPropose() {
  toast(dzT("atelier.at3_da.relit"));
  try {
    const d = await api.send("POST", "/atelier/style/propose", {});
    daRenderProposals(d.proposals);
    toast(dzT("atelier.at3_da.proposees", { n: d.proposals.length }));
  } catch (e) { toast(dzT("atelier.at3_da.err_prop", { msg: e.message }), true); }
}

/* ═════════ éléments vectoriels du chapitre (Vectorlab, phases 0+6) ═════════ */
const VECTOR_ROLES = { decor: dzT("atelier.at3_vec.decor"), lumiere: dzT("atelier.at3_vec.lumiere"),
                       personnage: dzT("atelier.at3_vec.personnage"), libre: dzT("atelier.at3_vec.libre") };

function docVectorielVierge(nom) {
  return { v: 1, nom, taille: { w: 1280, h: 1920 }, fond: "#F8F4E3",
           calques: [{ id: "c1", nom: "fond", visible: true, verrou: false,
                       objets: [] }] };
}

let vectorDocsChapitre = [];   // la liste FUSIONNÉE servie (propres + liés)

function vectorVignette(d) {
  // la vignette naît au Sauver de l'éditeur ; ?v= suit la version (cache)
  return d.vignette
    ? `<img class="vector-vignette" alt=""
         src="/api/vector/docs/${encodeURIComponent(d.id)}/vignette.png?v=${d.version}">`
    : `<span class="vector-vignette vide"></span>`;
}

async function loadVectorDocs() {
  const panel = $("#vectorPanel");
  if (!panel) return;
  if (!chapter) { panel.classList.add("hidden"); return; }
  panel.classList.remove("hidden");
  let docs = [];
  try {
    docs = (await api.get(`/vector/docs?chapter_id=${chapter.id}`)).docs || [];
  } catch (e) {
    $("#vectorList").innerHTML =
      `<div class="empty-note">${dzT("atelier.at3_vec.injoignable", { msg: esc(e.message) })}</div>`;
    return;
  }
  vectorDocsChapitre = docs;
  $("#vectorList").innerHTML = docs.length ? docs.map(d => `
    <div class="vector-row">
      ${vectorVignette(d)}
      <span class="vector-role">${esc(VECTOR_ROLES[d.role] || d.role)}</span>
      <b>${esc(d.name)}</b> <span class="vector-v">v${d.version}</span>
      ${d.liaison ? `<span class="vector-ref" title="${dzT("atelier.at3_vec.ref_titre")}">${dzT("atelier.at3_vec.ref")}</span>` : ""}
      <span class="vector-actions">
        <a class="btn" href="/vectorlab/?doc=${encodeURIComponent(d.id)}"
           target="_blank" title="${dzT("atelier.at3_vec.ouvrir_titre")}">${dzT("atelier.at3_vec.ouvrir")}</a>
        ${d.liaison ? `
        <button class="btn" data-vdup="${d.id}"
          title="${dzT("atelier.at3_vec.dupliquer_titre")}">${dzT("atelier.at3_vec.dupliquer")}</button>
        <button class="btn" data-vret="${d.id}"
          title="${dzT("atelier.at3_vec.retirer_titre")}">${dzT("atelier.at3_vec.retirer")}</button>` : ""}
      </span>
    </div>`).join("")
    : `<div class="empty-note">${dzT("atelier.at3_vec.vide")}</div>`;
  loadVectorBiblio();          // le tiroir, s'il est ouvert, suit
}

async function vectorCreer(role) {
  if (!chapter) { toast(dzT("atelier.at3_vec.ouvre_chapitre"), true); return; }
  const nom = await window.__dzDialogue.saisir(dzT("atelier.at3_vec.nom_nouveau", { role: VECTOR_ROLES[role] }),
                     { valeur: `${VECTOR_ROLES[role]} — ${chapter.title || dzT("atelier.at3_vec.chapitre")}`, ok: dzT("atelier.at3_vec.creer") });
  if (!nom) return;
  try {
    const d = await api.send("POST", "/vector/docs", {
      name: nom, role, chapter_id: chapter.id,
      doc: docVectorielVierge(nom) });
    await loadVectorDocs();
    window.open(`/vectorlab/?doc=${encodeURIComponent(d.id)}`, "_blank");
  } catch (e) { toast(dzT("atelier.at3_vec.err", { msg: e.message }), true); }
}

/* ── la bibliothèque (phase 6) : instancier par référence, sans copie ── */

async function loadVectorBiblio() {
  const tiroir = $("#vectorBiblio");
  if (!tiroir || tiroir.classList.contains("hidden") || !chapter) return;
  const q = $("#vbRecherche").value.trim();
  const role = $("#vbRole").value;
  let docs = [];
  try {
    const ps = new URLSearchParams();
    if (q) ps.set("q", q);
    if (role) ps.set("role", role);
    docs = (await api.get(`/vector/docs?${ps.toString()}`)).docs || [];
  } catch (e) {
    $("#vbListe").innerHTML =
      `<div class="empty-note">${dzT("atelier.at3_vb.injoignable", { msg: esc(e.message) })}</div>`;
    return;
  }
  // hors du chapitre courant : ni propres, ni déjà instanciés
  const deja = new Set(vectorDocsChapitre.map(d => d.id));
  docs = docs.filter(d => !deja.has(d.id));
  $("#vbListe").innerHTML = docs.length ? docs.map(d => `
    <div class="vector-row">
      ${vectorVignette(d)}
      <span class="vector-orig" title="${d.chapter_id
        ? dzT("atelier.at3_vb.propre")
        : dzT("atelier.at3_vb.globale")}">${
        d.chapter_id ? ico("dz-etat-origine") : ico("dz-nav-bibliotheque")}</span>
      <span class="vector-role">${esc(VECTOR_ROLES[d.role] || d.role)}</span>
      <b>${esc(d.name)}</b> <span class="vector-v">v${d.version}</span>
      <span class="vector-actions">
        <button class="btn" data-vinst="${d.id}"
          title="${dzT("atelier.at3_vb.instancier_titre")}">${dzT("atelier.at3_vb.instancier")}</button>
        <a class="btn" href="/vectorlab/?doc=${encodeURIComponent(d.id)}"
           target="_blank" title="${dzT("atelier.at3_vec.ouvrir_titre")}">${dzT("atelier.at3_vec.ouvrir")}</a>
      </span>
    </div>`).join("")
    : `<div class="empty-note">${q || role ? dzT("atelier.at3_vb.rien_filtres") : dzT("atelier.at3_vb.rien")}</div>`;
}

async function vectorInstancier(docId) {
  try {
    await api.send("POST", "/vector/links",
                   { chapter_id: chapter.id, doc_id: docId });
    await loadVectorDocs();
    toast(dzT("atelier.at3_vb.instancie"));
  } catch (e) { toast(dzT("atelier.at3_vb.err_inst", { msg: e.message }), true); }
}

async function vectorRetirer(docId) {
  try {
    await api.send("DELETE", "/vector/links?chapter_id="
      + encodeURIComponent(chapter.id)
      + "&doc_id=" + encodeURIComponent(docId));
    await loadVectorDocs();
    toast(dzT("atelier.at3_vb.retiree"));
  } catch (e) { toast(dzT("atelier.at3_vb.err_ret", { msg: e.message }), true); }
}

async function vectorDupliquer(docId) {
  const src = vectorDocsChapitre.find(d => d.id === docId);
  const nom = await window.__dzDialogue.saisir(dzT("atelier.at3_vb.nom_copie"),
                     { valeur: dzT("atelier.at3_vb.copie_de", { nom: (src && src.name) || dzT("atelier.at3_vb.element") }), ok: dzT("atelier.at3_vec.dupliquer") });
  if (!nom) return;
  try {
    await api.send("POST",
      `/vector/docs/${encodeURIComponent(docId)}/duplicate`,
      { chapter_id: chapter.id, name: nom });
    await loadVectorDocs();
    toast(dzT("atelier.at3_vb.copie_creee"));
  } catch (e) { toast(dzT("atelier.at3_vb.err_dup", { msg: e.message }), true); }
}

/* ═════════ style global du projet ═════════ */
async function loadGlobalStyle() {
  try {
    const d = await api.get("/atelier/settings");
    $("#globalStyle").value = (d.settings && d.settings.global_style) || "";
  } catch (e) { /* silencieux */ }
}

const saveGlobalStyle = debounce(async () => {
  try {
    $("#styleSaved").textContent = "…"; $("#styleSaved").className = "savestate saving";
    await api.send("PUT", "/atelier/settings",
                   { global_style: $("#globalStyle").value });
    $("#styleSaved").innerHTML = ico("dz-etat-enregistre"); $("#styleSaved").className = "savestate saved";
  } catch (e) { $("#styleSaved").textContent = "!"; toast(dzT("atelier.at3_style.err", { msg: e.message }), true); }
}, 700);

/* ═════════ agent manuscrit ═════════ */
let msPolling = null;

function msSetProgress(st) {
  const phases = { "segmentation": 5, "extraction": 10, "consolidation": 75,
                   "liens": 90, "terminé": 100, "échec": 100 };
  let pct = phases[st.phase] ?? 0;
  if (st.phase === "extraction" && st.chapter_n) {
    pct = 10 + Math.round(60 * (st.chapter_i || 0) / st.chapter_n);
  }
  $("#msBarFill").style.width = pct + "%";
  const where = st.phase === "extraction" && st.chapter_n
    ? dzT("atelier.at3_ms.ou", { i: st.chapter_i, n: st.chapter_n }) : "";
  $("#msStatus").textContent = `${st.phase}${where} — ${st.message || ""}`;
}

async function msRun() {
  const f = $("#msFile").files && $("#msFile").files[0];
  if (!f) { toast(dzT("atelier.at3_ms.choisis"), true); return; }
  const fd = new FormData();
  fd.append("manuscript", f);
  const comp = $("#msCompanion").files && $("#msCompanion").files[0];
  if (comp) fd.append("companion", comp);
  fd.append("series", $("#msSeries").value.trim());
  $("#msRun").disabled = true;
  $("#msProgress").classList.remove("hidden");
  $("#msStatus").textContent = dzT("atelier.at3_ms.envoi");
  try {
    const r = await fetch("/api/atelier/manuscript", { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || dzT("atelier.at3_ms.envoi_echoue"));
    toast(dzT("atelier.at3_ms.lance", { serie: d.series, k: Math.round(d.chars / 1000) }));
    msPolling = setInterval(async () => {
      try {
        const st = await api.get("/atelier/manuscript/" + d.job_id);
        msSetProgress(st);
        if (st.done) {
          clearInterval(msPolling); msPolling = null;
          $("#msRun").disabled = false;
          if (st.error) { toast(dzT("atelier.at3_ms.echec", { msg: st.error }), true); return; }
          const s = st.stats || {};
          toast(dzT("atelier.at3_ms.termine", {
                ch: s.chapitres_crees || 0,
                maj: s.chapitres_mis_a_jour ? dzT("atelier.at3_ms.termine_maj", { n: s.chapitres_mis_a_jour }) : "",
                ent: s.entites_creees || 0,
                enr: s.entites_enrichies ? dzT("atelier.at3_ms.termine_enr", { n: s.entites_enrichies }) : "",
                zones: s.zones_surlignees || 0 }));
          await loadEntities();
          await loadChapters();
          await renderBible();
          setTimeout(() => $("#msModal").classList.add("hidden"), 1200);
        }
      } catch (e) { /* poll silencieux */ }
    }, 2000);
  } catch (e) {
    $("#msRun").disabled = false;
    toast(dzT("atelier.at3_ms.err", { msg: e.message }), true);
  }
}

/* ═════════ utilitaires ═════════ */
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

/* ═════════ tâche #61 (plan chapitres P2) — versions du texte ═════════
   Le tiroir liste les instantanés du chapitre, de son scénario et de ses scènes ; le côte à côte compare l'instantané
   au texte courant ; « Restaurer » garde d'abord le courant (côté serveur) ; un scénario se copie (ses scènes ont été
   supprimées : il ne se restaure pas en scènes). */
const PASSE_LABEL = { manuelle: dzT("atelier.at3_ver.p_manuelle"), adaptation: dzT("atelier.at3_ver.p_adaptation"), suppression: dzT("atelier.at3_ver.p_suppression"), import: dzT("atelier.at3_ver.p_import"),
                      telephone: dzT("atelier.at3_ver.p_telephone"), reecriture: dzT("atelier.at3_ver.p_reecriture"), restauration: dzT("atelier.at3_ver.p_restauration"),
                      import_scenario: dzT("atelier.at3_ver.p_import_scenario") };
const KIND_VER = { chapter: dzT("atelier.at3_ver.k_chapter"), scenario: dzT("atelier.at3_ver.k_scenario"), scene: dzT("atelier.at3_ver.k_scene") };

function openVersions() {
  if (!chapter) { toast(dzT("atelier.at3_ver.ouvre_chapitre"), true); return; }
  $("#verModal").classList.remove("hidden");
  $("#verDiff").innerHTML = `<div class="empty-note">${dzT("atelier.at3_ver.choisis")}</div>`;
  const list = $("#verList");
  list.innerHTML = "…";
  api.get(`/chapters/${encodeURIComponent(chapter.id)}/versions`).then(({ versions }) => {
    $("#verNote").textContent = dzT("atelier.at3_ver.note", { n: versions.length, titre: chapter.title });
    if (!versions.length) {
      list.innerHTML = `<div class="empty-note">${dzT("atelier.at3_ver.aucun")}</div>`;
      return;
    }
    list.innerHTML = versions.map(v => `
      <div class="ver-item" data-id="${escA(v.id)}" title="${dzT("atelier.at3_ver.comparer")}">
        <div class="ver-line"><b>${KIND_VER[v.kind] || v.kind} v${v.n}</b> · ${esc(PASSE_LABEL[v.passe] || v.passe)}
          <span class="ver-size">${dzT("atelier.at3_ver.car", { n: v.taille })}</span></div>
        ${v.slugline ? `<div class="ver-when">${esc(v.slugline)}</div>` : ""}
        <div class="ver-when">${new Date(v.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</div>
        <div class="ver-prev">${esc(v.apercu)}…</div>
      </div>`).join("");
    list.querySelectorAll(".ver-item").forEach(el => el.addEventListener("click", () => {
      list.querySelectorAll(".ver-item").forEach(x => x.classList.remove("sel"));
      el.classList.add("sel");
      renderDiff(el.dataset.id);
    }));
  }).catch(e => { list.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; });
}

async function renderDiff(vid) {
  const box = $("#verDiff");
  box.innerHTML = "…";
  try {
    const d = await api.get(`/versions/${encodeURIComponent(vid)}/diff`);
    const cls = { "=": "ver-same", "~": "ver-mod", "+": "ver-add", "-": "ver-del" };
    const col = (k) => d.lignes.map(l => `<div class="ver-l ${cls[l.op]}">${l[k] === null ? "" : (esc(l[k]) || "&nbsp;")}</div>`).join("");
    const action = d.version.restaurable
      ? `<button id="verRestore" class="btn primary" title="${dzT("atelier.at3_ver.restaurer_titre")}">${ico("dz-action-restaurer")} ${dzT("atelier.at3_ver.restaurer")}</button>`
      : `<button id="verCopier" class="btn" title="${dzT("atelier.at3_ver.copier_titre")}">${ico("dz-action-copier")} ${dzT("atelier.at3_ver.copier")}</button>`;
    box.innerHTML = `
      <div class="ver-diff-head">
        <span>${KIND_VER[d.version.kind] || ""} v${d.version.n} · ${esc(PASSE_LABEL[d.version.passe] || d.version.passe)}</span>
        <span class="ver-counts">+${d.ajoutees} / −${d.supprimees} · ${dzT("atelier.at3_ver.inchangees", { n: d.identiques })}</span>
        ${action}
      </div>
      <div class="ver-cols">
        <div class="ver-col"><header>${dzT("atelier.at3_ver.col_instantane")}</header>${col("a")}</div>
        <div class="ver-col"><header>${dzT("atelier.at3_ver.col_courant")}</header>${col("b")}</div>
      </div>`;
    const copier = $("#verCopier");
    if (copier) copier.addEventListener("click", async () => {
      try { const v = await api.get(`/versions/${encodeURIComponent(vid)}`); await navigator.clipboard.writeText(v.text); toast(dzT("atelier.at3_ver.copie")); }
      catch (e) { toast(dzT("atelier.at3_ver.err_copie", { msg: e.message }), true); }
    });
    const rest = $("#verRestore");
    if (rest) rest.addEventListener("click", async () => {
      if (!await window.__dzDialogue.confirmer(dzT("atelier.at3_ver.confirmer"), { ok: dzT("atelier.at3_ver.restaurer") })) return;
      clearTimeout(saveTimer);                       // une sauvegarde en attente n'écrasera pas le texte restauré
      try {
        await api.send("POST", `/versions/${encodeURIComponent(vid)}/restore`);
        $("#verModal").classList.add("hidden");
        await openChapter(chapter.id);               // texte ET surlignage recalculés par le serveur
        if (mode === "screenplay") await loadScenes(true);
        toast(dzT("atelier.at3_ver.restauree"));
      } catch (e) { toast(dzT("atelier.at3_ver.err_rest", { msg: e.message }), true); }
    });
  } catch (e) { box.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; }
}

/* ═════════ tâche #60 (plan chapitres P1) — plan ↔ entités, apparitions ═════════ */
function entPicker(selected) {
  const sel = new Set(selected || []);
  return `<details class="shot-ents-edit"><summary title="${dzT("atelier.at3_app.cocher")}">${ico("dz-edit-lier")} ${dzT("atelier.at3_app.entites_plan")}</summary>
    ${entities.map(e => `<label class="chip k-${e.kind}"><input type="checkbox" value="${escA(e.id)}" ${sel.has(e.id) ? "checked" : ""}> ${esc(e.name)}</label>`).join("")}
  </details>`;
}

async function showApparitions(id, card) {
  const box = card.querySelector(".entity-apps");
  if (!box.classList.contains("hidden")) { box.classList.add("hidden"); return; }
  box.innerHTML = "…"; box.classList.remove("hidden");
  try {
    const a = await api.get(`/bible/entities/${encodeURIComponent(id)}/apparitions`);
    const t = a.totals;
    box.innerHTML = `<div class="apps-total">${dzT("atelier.at3_app.totaux", { ch: t.chapters, m: t.mentions, p: t.shots, s: t.scenes })}</div>` +
      (a.chapters.map(c => `<div class="apps-ch"><b>${esc(c.title)}</b> — ${dzT("atelier.at3_app.mentions", { n: c.mentions })}
        ${c.shots.map(s => `<button class="btn ghost apps-shot" data-ch="${escA(c.chapter_id)}" data-shot="${escA(s.id)}" title="${escA(s.action)}">${dzT("atelier.at3_app.plan", { n: s.idx + 1 })}</button>`).join("")}
        ${c.scenes.map(s => `<button class="btn ghost apps-scene" data-ch="${escA(c.chapter_id)}" title="${escA(s.slugline)}">${dzT("atelier.at3_app.sc", { n: s.idx + 1 })}</button>`).join("")}</div>`).join("")
       || `<div class="empty-note">${dzT("atelier.at3_app.aucune")}</div>`);
    box.querySelectorAll(".apps-shot").forEach(b => b.addEventListener("click", async () => {
      $("#chapterSelect").value = b.dataset.ch; await openChapter(b.dataset.ch); setMode("board");
      setTimeout(() => { const el = document.querySelector(`.shot-card[data-id="${b.dataset.shot}"]`); if (el) el.scrollIntoView({ block: "center" }); }, 400);
    }));
    box.querySelectorAll(".apps-scene").forEach(b => b.addEventListener("click", async () => {
      $("#chapterSelect").value = b.dataset.ch; await openChapter(b.dataset.ch); setMode("screenplay");
    }));
  } catch (e) { box.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; }
}

/* ═════════ wiring global ═════════ */
window.addEventListener("DOMContentLoaded", async () => {
  // chapitres
  $("#newChapter").addEventListener("click", async () => {
    const ch = await api.send("POST", "/chapters", { title: dzT("atelier.int_chap.nouveau"), series: $("#chapterSeries").value });
    await loadChapters(ch.id);
  });
  $("#chapterSelect").addEventListener("change", e => e.target.value && openChapter(e.target.value));
  $("#deleteChapter").addEventListener("click", async () => {
    if (!chapter || !await window.__dzDialogue.confirmer(dzT("atelier.at3_w.suppr_chapitre", { titre: chapter.title }))) return;
    await api.send("DELETE", "/chapters/" + chapter.id);
    chapter = null; $("#script").value = "";
    await loadChapters();
  });
  ["#chapterTitle", "#chapterSeries"].forEach(s => $(s).addEventListener("input", scheduleSave));
  $("#verBtn").addEventListener("click", openVersions);
  $("#verClose").addEventListener("click", () => $("#verModal").classList.add("hidden"));

  // éditeur
  const ta = $("#script");
  ta.addEventListener("input", () => { renderScript(); scheduleSave(); refreshSelBar(); });
  ta.addEventListener("scroll", syncScroll);
  ["mouseup", "keyup"].forEach(ev => ta.addEventListener(ev, refreshSelBar));

  // import fichier (réutilise la mécanique Épisodes)
  $("#importFile").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f || !chapter) { if (!chapter) toast(dzT("atelier.at3_w.cree_chapitre"), true); return; }
    const fd = new FormData(); fd.append("file", f);
    toast(dzT("atelier.at3_w.extraction"));
    try {
      const r = await fetch("/api/episodes/extract-text", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || !d.text) throw new Error(d.detail || d.error || dzT("atelier.at3_w.extraction_vide"));
      ta.value = d.text;
      if ([dzT("atelier.int_chap.nouveau"), "Nouveau chapitre"].includes(chapter.title) && d.title) $("#chapterTitle").value = d.title;
      renderScript(); scheduleSave();
      toast(dzT("atelier.at3_w.importe", { nom: f.name, n: (d.text || "").length }));
    } catch (err) { toast(dzT("atelier.at3_w.import_echoue", { msg: err.message }), true); }
    e.target.value = "";
  });

  // barre de sélection
  document.querySelectorAll("#selBar [data-kind]").forEach(b =>
    b.addEventListener("click", () => createEntityFromSelection(b.dataset.kind)));
  $("#reeAction").addEventListener("change", (e) => {
    const a = e.target.value; e.target.value = "";
    if (a) reecrire(a);
  });
  $("#reeAppliquer").addEventListener("click", reecrireAppliquer);
  ["#reeClose", "#reeAnnuler"].forEach(s => $(s).addEventListener("click", () => { $("#reeModal").classList.add("hidden"); reeEnCours = null; }));
  $("#linkSelect").addEventListener("change", (e) => {
    const id = e.target.value; if (!id) return;
    const sel = currentSelection(); if (sel) addSpan(sel, id);
    e.target.value = "";
  });

  // storyboard
  document.querySelectorAll("#modeTabs .tab").forEach(t =>
    t.addEventListener("click", () => setMode(t.dataset.mode)));
  $("#adaptBtn").addEventListener("click", adaptChapter);
  $("#voAll").addEventListener("click", chapterVo);
  $("#cutAI").addEventListener("click", () => decoupe("ai"));
  $("#cutPara").addEventListener("click", () => decoupe("paragraph"));
  $("#animBtn").addEventListener("click", ouvrirAnimatique);
  $("#versEpisode").addEventListener("click", versEpisode);
  $("#animGo").addEventListener("click", monterAnimatique);
  document.querySelectorAll("[data-sortie]").forEach(b => b.addEventListener("click", () => sortieMontage(b.dataset.sortie)));
  $("#animClose").addEventListener("click", () => {
    $("#animVideo").pause(); $("#animVideo").removeAttribute("src");
    $("#animModal").classList.add("hidden");
  });
  $("#addShot").addEventListener("click", async () => {
    if (!chapter) { toast(dzT("atelier.at3_ver.ouvre_chapitre"), true); return; }
    await api.send("POST", `/chapters/${chapter.id}/shots`, {});
    await loadShots(true);
  });

  // bible
  document.querySelectorAll(".bible-pane .tab").forEach(t =>
    t.addEventListener("click", () => { setTab(t.dataset.kind); renderBible(); }));
  $("#addEntity").addEventListener("click", async () => {
    const name = await window.__dzDialogue.saisir(dzT("atelier.at3_w.nom_entite", { kind: KIND_LABEL[curKind].toLowerCase() }), { ok: dzT("atelier.at3_vec.creer") });
    if (!name || !name.trim()) return;
    const ent = await api.send("POST", "/bible/entities", { kind: curKind, name: name.trim() });
    entities.push(ent); renderBible();
  });

  // style global du projet
  $("#globalStyle").addEventListener("input", saveGlobalStyle);

  // direction artistique
  $("#daBtn").addEventListener("click", openDA);
  $("#daClose").addEventListener("click", () => $("#daModal").classList.add("hidden"));
  $("#daModal").addEventListener("click", (e) => { if (e.target.id === "daModal") $("#daModal").classList.add("hidden"); });
  $("#daApply").addEventListener("click", daApply);
  $("#daPropose").addEventListener("click", daPropose);
  $("#daRefPick").addEventListener("click", () =>
    openLibrary(null, async (f) => { $("#daRefName").textContent = f; $("#daModal").classList.remove("hidden"); }));
  $("#daRefClear").addEventListener("click", () => { $("#daRefName").textContent = dzT("atelier.at3_da.aucune"); });

  // resets (storyboard + scénario)
  $("#boardReset").addEventListener("click", async () => {
    if (!chapter || !shots.length) { toast(dzT("atelier.at3_w.rien_reinit"), true); return; }
    if (!await window.__dzDialogue.confirmer(dzT("atelier.at3_w.suppr_plans", { n: shots.length }))) return;
    await api.send("DELETE", `/chapters/${chapter.id}/shots`);
    await loadShots(true);
    toast(dzT("atelier.at3_w.board_reinit"));
  });
  document.querySelectorAll("[data-export]").forEach(b => b.addEventListener("click", () => telechargerExport(b.dataset.export)));
  $("#spImportFile").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    await importerScenario(f);
  });
  $("#spReset").addEventListener("click", async () => {
    if (!chapter || !scenes.length) { toast(dzT("atelier.at3_w.rien_reinit"), true); return; }
    if (!await window.__dzDialogue.confirmer(dzT("atelier.at3_w.suppr_scenes", { n: scenes.length }))) return;
    await api.send("DELETE", `/chapters/${chapter.id}/scenes`);
    await loadScenes(true);
    toast(dzT("atelier.at3_w.sp_reinit"));
  });

  // lecture du scénario assemblé (le .fountain est un simple fichier texte —
  // ce viewer intégré évite d'avoir besoin d'un logiciel externe)
  $("#spPreview").addEventListener("click", async () => {
    if (!chapter) { toast(dzT("atelier.at3_ver.ouvre_chapitre"), true); return; }
    try {
      const d = await api.get(`/chapters/${chapter.id}/screenplay`);
      if (!d.scene_count) { toast(dzT("atelier.at3_w.pas_scenario"), true); return; }
      $("#spTitle").textContent = dzT("atelier.at3_w.sp_titre", { titre: d.title, n: d.scene_count });
      $("#spText").textContent = d.fountain;
      $("#spModal").classList.remove("hidden");
    } catch (e) { toast(dzT("atelier.at3_w.err_lecture", { msg: e.message }), true); }
  });
  $("#spClose").addEventListener("click", () => $("#spModal").classList.add("hidden"));
  $("#spModal").addEventListener("click", (e) => { if (e.target.id === "spModal") $("#spModal").classList.add("hidden"); });

  // agent manuscrit
  $("#msBtn").addEventListener("click", () => $("#msModal").classList.remove("hidden"));
  $("#msClose").addEventListener("click", () => $("#msModal").classList.add("hidden"));
  $("#msModal").addEventListener("click", (e) => { if (e.target.id === "msModal") $("#msModal").classList.add("hidden"); });
  $("#msRun").addEventListener("click", msRun);

  $("#vpAddDecor").addEventListener("click", () => vectorCreer("decor"));
  $("#vpAddLumiere").addEventListener("click", () => vectorCreer("lumiere"));
  $("#vpAddPerso").addEventListener("click", () => vectorCreer("personnage"));
  $("#vpBiblio").addEventListener("click", () => {
    $("#vectorBiblio").classList.toggle("hidden");
    loadVectorBiblio();
  });
  $("#vbRecherche").addEventListener("input", debounce(loadVectorBiblio, 300));
  $("#vbRole").addEventListener("change", () => loadVectorBiblio());
  $("#vbListe").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-vinst]");
    if (b) vectorInstancier(b.dataset.vinst);
  });
  $("#vectorList").addEventListener("click", (ev) => {
    const dup = ev.target.closest("[data-vdup]");
    if (dup) { vectorDupliquer(dup.dataset.vdup); return; }
    const ret = ev.target.closest("[data-vret]");
    if (ret) vectorRetirer(ret.dataset.vret);
  });

  // modal
  $("#libClose").addEventListener("click", () => $("#libModal").classList.add("hidden"));
  $("#libModal").addEventListener("click", (e) => { if (e.target.id === "libModal") $("#libModal").classList.add("hidden"); });

  // import externe → Library → callback du picker (inspiration OU réf de style)
  $("#libUpload").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f || !libOnPick) return;
    toast(dzT("atelier.at3_w.import_fichier"));
    try {
      const fd = new FormData(); fd.append("file", f);
      const r = await fetch("/api/images/upload", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || !d.filename) throw new Error(d.detail || dzT("atelier.at3_w.upload_echoue"));
      $("#libModal").classList.add("hidden");
      await libOnPick(d.filename);
    } catch (err) { toast(dzT("atelier.at3_w.import_echoue", { msg: err.message }), true); }
    e.target.value = "";
  });
  $("#libUrl").addEventListener("click", async () => {
    if (!libOnPick) return;
    const url = await window.__dzDialogue.saisir(dzT("atelier.at3_w.url_image"), { placeholder: "https://…", ok: dzT("atelier.at3_w.telecharger") });
    if (!url || !url.trim()) return;
    toast(dzT("atelier.at3_w.telechargement"));
    try {
      const d = await api.send("POST", "/images/fetch", { url: url.trim() });
      if (!d.filename) throw new Error(dzT("atelier.at3_w.sans_fichier"));
      $("#libModal").classList.add("hidden");
      await libOnPick(d.filename);
    } catch (err) { toast(dzT("atelier.at3_w.import_url_echoue", { msg: err.message }), true); }
  });

  // boot
  try {
    await loadGlobalStyle();
    await loadEntities();
    // t127 : `?chapter=<id>` rouvre ce chapitre (le retour du Plateau 3D) ; inconnu → le premier, comme avant
    await loadChapters(new URLSearchParams(location.search).get("chapter") || undefined);
    await renderBible();
  } catch (e) { toast(dzT("atelier.at3_w.chargement_echoue", { msg: e.message }), true); }
});
