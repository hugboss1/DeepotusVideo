/* Atelier Chapitre P1 — script → entités → bible.
   Vanilla JS, même API que l'app (même origine). Aucune dépendance. */
"use strict";

const $ = (s) => document.querySelector(s);
const api = {
  async get(p) { const r = await fetch("/api" + p); if (!r.ok) throw new Error(await r.text()); return r.json(); },
  async send(m, p, body) {
    const r = await fetch("/api" + p, { method: m, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    return d;
  },
};

const KIND_LABEL = { character: "Personnage", place: "Lieu", object: "Objet",
                     date: "Date", ambiance: "Ambiance", decor: "Décor" };

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

const SHOT_TYPES = ["establishing", "wide", "medium", "close-up",
  "extreme close-up", "over-shoulder", "POV", "insert"];
const CAMERA_MOVES = ["slow push-in", "slow pull-out", "360-degree orbit",
  "tracking shot", "handheld with subtle shake", "static, locked-off",
  "low angle dramatic", "rack focus reveal", "dolly zoom (vertigo effect)",
  "whip pan transition", "crane shot descending"];

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
    || `<option value="">(aucun chapitre)</option>`;
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
}

function scheduleSave() {
  if (!chapter) return;
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
      $("#saveState").textContent = "enregistré ✓"; $("#saveState").className = "savestate saved";
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
          toast(`Chapitre re-créé côté serveur (« ${fresh.title} ») — contenu préservé.`);
          await loadChapters(fresh.id);
          return;
        } catch (e2) { e = e2; }
      }
      $("#saveState").textContent = "échec !"; toast("Sauvegarde échouée : " + e.message, true);
    }
  }, 800);
}

/* ═════════ script : surlignage + spans ═════════ */
function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

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
  $("#selText").textContent = "« " + (sel.text.length > 60 ? sel.text.slice(0, 60) + "…" : sel.text) + " »";
  const link = $("#linkSelect");
  link.innerHTML = `<option value="">🔗 Lier à…</option>` + entities.map(e =>
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
    toast(`${KIND_LABEL[kind]} « ${ent.name} » créé — décris-le puis génère sa référence.`);
  } catch (e) { toast("Création échouée : " + e.message, true); }
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
}

async function renderBible() {
  const list = $("#entityList");
  const items = entities.filter(e => e.kind === curKind);
  if (!items.length) {
    list.innerHTML = `<div class="empty-note">Aucun ${KIND_LABEL[curKind].toLowerCase()} pour l'instant.<br>
      Sélectionne un nom dans le script (ou ＋ Nouveau) pour le créer.</div>`;
    return;
  }
  list.innerHTML = items.map(e => `
  <div class="entity-card" data-id="${e.id}">
    <div class="refbox">
      ${e.ref_image
        ? `<img class="refimg" src="/api/images/${encodeURIComponent(e.ref_image)}" alt="ref">`
        : `<div class="refimg empty">Pas encore de référence<br>— Générer ⤵</div>`}
      <div class="seedrow">
        ${e.seed != null ? `<span class="seedbadge" title="Seed verrouillé de la référence">🔒 ${e.seed}</span>` : `<span class="seedbadge" style="opacity:.5">seed —</span>`}
      </div>
      <div class="entity-actions">
        <button class="btn primary act-gen" title="Génère l'image de référence (FLUX). Re-générer avec le même seed reproduit la même image.">🎨 Générer</button>
        <button class="btn act-roll" title="Re-génère avec un nouveau seed aléatoire">🎲</button>
      </div>
    </div>
    <div class="entity-main">
      <div class="row1">
        <span class="kinddot k-${e.kind}"></span>
        <input class="entity-name" value="${esc(e.name)}" title="Nom">
        <button class="btn ghost act-del" title="Supprimer l'entité">🗑</button>
      </div>
      <textarea class="entity-desc" placeholder="Description physique / visuelle (sert de prompt de référence)">${esc(e.description)}</textarea>
      <input class="entity-style" placeholder="Notes de style (ex: style anime sombre, palette abyssale)" value="${esc(e.style_notes)}">
      ${(e.aliases && e.aliases.length)
        ? `<div class="entity-aliases">alias : ${e.aliases.map(esc).join(" · ")}</div>` : ""}
      ${(e.evidence && e.evidence.length)
        ? `<details class="entity-evidence"><summary>citations du manuscrit (${e.evidence.length})</summary>
           ${e.evidence.slice(0, 8).map(v =>
             `<blockquote>« ${esc(v.quote)} »${v.chapter ? ` — <i>${esc(v.chapter)}</i>` : ""}</blockquote>`).join("")}
           </details>` : ""}
      <div class="insp-row">
        <span style="font-size:11px;color:var(--ink-soft)">Inspirations :</span>
        ${(e.inspiration_images || []).map(f =>
          `<img src="/api/images/${encodeURIComponent(f)}" data-f="${esc(f)}" class="act-rm-insp" title="Retirer ${esc(f)}">`).join("")}
        <button class="btn ghost act-add-insp" title="Ajouter depuis la Library">＋</button>
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
      } catch (e) { toast("Sauvegarde entité échouée : " + e.message, true); }
    }, 700);
    ["input"].forEach(ev => {
      card.querySelector(".entity-name").addEventListener(ev, saveField);
      card.querySelector(".entity-desc").addEventListener(ev, saveField);
      card.querySelector(".entity-style").addEventListener(ev, saveField);
    });
    card.querySelector(".act-gen").addEventListener("click", () => generateRef(id, ent().seed));
    card.querySelector(".act-roll").addEventListener("click", () => generateRef(id, null));
    card.querySelector(".act-del").addEventListener("click", async () => {
      if (!confirm(`Supprimer « ${ent().name} » de la bible ?`)) return;
      try {
        await api.send("DELETE", "/bible/entities/" + id);
        entities = entities.filter(x => x.id !== id);
        (chapter && chapter.spans || []).forEach(sp => { if (sp.entity_id === id) sp.orphan = true; });
        await renderBible(); renderScript(); scheduleSave();
      } catch (e) { toast("Suppression échouée : " + e.message, true); }
    });
    card.querySelector(".act-add-insp").addEventListener("click", () => openLibrary(id));
    card.querySelectorAll(".act-rm-insp").forEach(img => img.addEventListener("click", async () => {
      const f = img.dataset.f;
      const insp = (ent().inspiration_images || []).filter(x => x !== f);
      const up = await api.send("PUT", "/bible/entities/" + id, { inspiration_images: insp });
      Object.assign(ent(), up); renderBible();
    }));
  });
}

async function generateRef(id, seed) {
  const ent = entities.find(x => x.id === id);
  if (!ent) return;
  if (!(ent.description || "").trim()) { toast("Ajoute une description avant de générer.", true); return; }
  toast(`Génération de la référence de « ${ent.name} »… (~3 s)`);
  try {
    const up = await api.send("POST", `/bible/entities/${id}/generate`,
                              seed != null ? { seed } : {});
    Object.assign(ent, up);
    await renderBible();
    toast(`Référence de « ${ent.name} » générée — seed ${up.seed} 🔒 (🎲 pour varier).`);
  } catch (e) { toast("Génération échouée : " + e.message, true); }
}

/* ═════════ storyboard ═════════ */
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
  if (board) loadShots(true);
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
  if (!chapter) { list.innerHTML = `<div class="empty-note">Crée ou ouvre un chapitre d'abord.</div>`; return; }
  if (!scenes.length) {
    list.innerHTML = `<div class="empty-note">Pas encore de scénario pour ce chapitre.<br>
      🎭 <b>Adapter (IA)</b> transforme le roman en script de film (scènes, sluglines,
      éclairages, caméra) — sans toucher au manuscrit.</div>`;
    return;
  }
  list.innerHTML = scenes.map((s, i) => `
  <div class="scene-card" data-id="${s.id}">
    <div class="scene-slug">SCÈNE ${i + 1} · ${esc(s.slugline)}</div>
    <div class="scene-meta">
      <select class="sc-ie" title="INT/EXT">
        ${["INT", "EXT", "INT/EXT"].map(v => `<option ${v === s.int_ext ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <select class="sc-tod" title="Moment">
        ${TIMES_OF_DAY.map(v => `<option ${v === s.time_of_day ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <input class="sc-light" value="${esc(s.lighting)}" placeholder="éclairage" title="Type d'éclairage">
      <input class="sc-mood" value="${esc(s.mood)}" placeholder="mood" title="Ambiance émotionnelle">
    </div>
    <div class="scene-cam">🎥 <input class="sc-cam" value="${esc(s.camera_notes)}" placeholder="intention caméra + pourquoi"></div>
    <textarea class="scene-fountain" spellcheck="false">${esc(s.fountain_text)}</textarea>
    <div class="scene-ents">${entChips(s.entities)}</div>
    ${s.source_text ? `<div class="scene-src">source : « ${esc(s.source_text)}… »</div>` : ""}
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
          `SCÈNE ${sc.idx + 1} · ${up.slugline}`;
      } catch (e) { toast("Sauvegarde de la scène échouée : " + e.message, true); }
    }, 700);
    card.querySelectorAll("select,input,textarea").forEach(el =>
      ["input", "change"].forEach(ev => el.addEventListener(ev, save)));
  });
}

async function adaptChapter() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (scenes.length && !confirm("Ré-adapter remplacera le scénario actuel de ce chapitre. Continuer ?")) return;
  toast("🎭 Adaptation en scénario… (30-90 s)");
  try {
    const r = await api.send("POST", `/chapters/${chapter.id}/screenplay/adapt`,
                             { language: "fr" });
    const poll = setInterval(async () => {
      try {
        const st = await api.get("/atelier/manuscript/" + r.job_id);
        if (!st.done) return;
        clearInterval(poll);
        if (st.error) { toast("Adaptation échouée : " + st.error, true); return; }
        await loadEntities();
        await loadScenes(true);
        await renderBible();
        toast(`🎭 ${st.stats.scenes} scènes — ` +
              (st.stats.entites_creees ? `${st.stats.entites_creees} lieux/décors ajoutés à la bible.` : "bible réutilisée."));
      } catch (e) { /* poll silencieux */ }
    }, 2000);
  } catch (e) { toast("Adaptation : " + e.message, true); }
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
  if (!chapter) { list.innerHTML = `<div class="empty-note">Crée ou ouvre un chapitre d'abord.</div>`; return; }
  if (!shots.length) {
    list.innerHTML = `<div class="empty-note">Pas encore de storyboard.<br>
      🎬 <b>Découper (IA)</b> lit le chapitre + la bible et propose les plans<br>
      (ou ¶ Paragraphes pour un découpage simple sans IA).</div>`;
    return;
  }
  list.innerHTML = shots.map((s, i) => `
  <div class="shot-card" data-id="${s.id}">
    <div class="thumb">
      ${s.sketch_image
        ? `<img src="/api/images/${encodeURIComponent(s.sketch_image)}" alt="croquis">`
        : `<div class="noimg">pas de croquis<br>— 🎨 ⤵</div>`}
      ${s.sketch_seed != null ? `<div class="seedtag">🔒 ${s.sketch_seed}</div>` : ""}
      <div class="entity-actions">
        <button class="btn primary act-sketch" title="Générer le croquis (même seed si déjà généré)">🎨</button>
        <button class="btn act-resketch" title="Nouveau croquis (seed aléatoire)">🎲</button>
      </div>
    </div>
    <div class="shot-main">
      <div class="rowhead">
        <span class="shot-no">PLAN ${i + 1}/${shots.length}</span>
        <div class="shot-actions">
          <button class="btn ghost act-up" title="Monter" ${i === 0 ? "disabled" : ""}>↑</button>
          <button class="btn ghost act-down" title="Descendre" ${i === shots.length - 1 ? "disabled" : ""}>↓</button>
          <button class="btn ghost act-insert" title="Insérer un plan après">＋</button>
          <button class="btn ghost act-delshot" title="Supprimer le plan">🗑</button>
        </div>
      </div>
      <textarea class="shot-action" placeholder="Action : ce que l'on VOIT dans ce plan">${esc(s.action)}</textarea>
      <div class="shot-params">
        <select class="shot-type" title="Type de plan">
          ${SHOT_TYPES.map(t => `<option ${t === s.shot_type ? "selected" : ""}>${t}</option>`).join("")}
        </select>
        <select class="shot-cam" title="Mouvement de caméra">
          ${CAMERA_MOVES.map(t => `<option ${t === s.camera_move ? "selected" : ""}>${t}</option>`).join("")}
        </select>
        <input class="shot-dur" type="number" min="0.5" max="60" step="0.5" value="${s.duration_s}" title="Durée (s)">
      </div>
      <div class="shot-ents">${entChips(s.entities) || "<span style='opacity:.5'>aucune entité détectée</span>"}</div>
      ${s.source_text ? `<details class="shot-src"><summary>texte source</summary><blockquote>${esc(s.source_text)}</blockquote></details>` : ""}
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
      } catch (e) { toast("Sauvegarde du plan échouée : " + e.message, true); }
    }, 600);
    const fields = () => ({
      action: card.querySelector(".shot-action").value,
      shot_type: card.querySelector(".shot-type").value,
      camera_move: card.querySelector(".shot-cam").value,
      duration_s: parseFloat(card.querySelector(".shot-dur").value) || sh().duration_s,
    });
    ["input", "change"].forEach(ev => {
      card.querySelector(".shot-action").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-type").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-cam").addEventListener(ev, () => save(fields));
      card.querySelector(".shot-dur").addEventListener(ev, () => save(fields));
    });
    card.querySelector(".act-sketch").addEventListener("click", () => sketchShot(id, sh().sketch_seed));
    card.querySelector(".act-resketch").addEventListener("click", () => sketchShot(id, null));
    card.querySelector(".act-insert").addEventListener("click", async () => {
      await api.send("POST", `/chapters/${chapter.id}/shots`, { after_id: id });
      await loadShots(true);
    });
    card.querySelector(".act-delshot").addEventListener("click", async () => {
      if (!confirm(`Supprimer le plan ${sh().idx + 1} ?`)) return;
      await api.send("DELETE", "/shots/" + id);
      await loadShots(true);
    });
    card.querySelector(".act-up").addEventListener("click", () => moveShot(id, -1));
    card.querySelector(".act-down").addEventListener("click", () => moveShot(id, +1));
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
  if (!(s.action || s.source_text || "").trim()) { toast("Décris l'action du plan d'abord.", true); return; }
  toast(`Croquis du plan ${s.idx + 1}… (~3 s)`);
  try {
    const up = await api.send("POST", `/shots/${id}/sketch`,
                              seed != null ? { seed } : {});
    Object.assign(s, up);
    renderBoard();
    toast(`Croquis du plan ${s.idx + 1} généré (seed ${up.sketch_seed}).`);
  } catch (e) { toast("Croquis échoué : " + e.message, true); }
}

async function decoupe(method) {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (!$("#script").value.trim()) { toast("Le chapitre est vide.", true); return; }
  if (shots.length && !confirm("Re-découper remplacera le storyboard actuel. Continuer ?")) return;
  toast(method === "ai" ? "Découpage IA en cours… (10-30 s)" : "Découpage par paragraphes…");
  try {
    const r = await api.send("POST", `/chapters/${chapter.id}/storyboard/decoupe`,
                             { method, language: "fr" });
    if (r.error) { toast(r.error, true); return; }
    shots = r.shots;
    renderBoard();
    toast(`${shots.length} plans créés — ajuste, puis génère les croquis 🎨.`);
  } catch (e) { toast("Découpage échoué : " + e.message, true); }
}

/* ═════════ Library modal ═════════ */
async function attachInspiration(filename) {
  const ent = entities.find(x => x.id === libTarget);
  if (!ent || !filename) return;
  const insp = [...(ent.inspiration_images || [])];
  if (!insp.includes(filename)) insp.push(filename);
  const up = await api.send("PUT", "/bible/entities/" + libTarget, { inspiration_images: insp });
  Object.assign(ent, up);
  $("#libModal").classList.add("hidden");
  renderBible();
  toast(`Inspiration « ${filename} » ajoutée (elle est aussi dans la Library).`);
}

async function openLibrary(entityId) {
  libTarget = entityId;
  const grid = $("#libGrid");
  grid.innerHTML = `<div class="empty-note">Chargement…</div>`;
  $("#libModal").classList.remove("hidden");
  try {
    const d = await api.get("/images");
    const files = (d.images || []).map(x => typeof x === "string" ? x : x.filename).filter(Boolean);
    grid.innerHTML = files.length
      ? files.map(f => `<img src="/api/images/${encodeURIComponent(f)}" data-f="${esc(f)}" title="${esc(f)}">`).join("")
      : `<div class="empty-note">Library vide.</div>`;
    grid.querySelectorAll("img").forEach(img =>
      img.addEventListener("click", () => attachInspiration(img.dataset.f)));
  } catch (e) { grid.innerHTML = `<div class="empty-note">Erreur : ${esc(e.message)}</div>`; }
}

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
    ? ` (chapitre ${st.chapter_i}/${st.chapter_n})` : "";
  $("#msStatus").textContent = `${st.phase}${where} — ${st.message || ""}`;
}

async function msRun() {
  const f = $("#msFile").files && $("#msFile").files[0];
  if (!f) { toast("Choisis le fichier du manuscrit.", true); return; }
  const fd = new FormData();
  fd.append("manuscript", f);
  const comp = $("#msCompanion").files && $("#msCompanion").files[0];
  if (comp) fd.append("companion", comp);
  fd.append("series", $("#msSeries").value.trim());
  $("#msRun").disabled = true;
  $("#msProgress").classList.remove("hidden");
  $("#msStatus").textContent = "Envoi du manuscrit…";
  try {
    const r = await fetch("/api/atelier/manuscript", { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "envoi échoué");
    toast(`Agent lancé sur « ${d.series} » (${Math.round(d.chars / 1000)}k caractères).`);
    msPolling = setInterval(async () => {
      try {
        const st = await api.get("/atelier/manuscript/" + d.job_id);
        msSetProgress(st);
        if (st.done) {
          clearInterval(msPolling); msPolling = null;
          $("#msRun").disabled = false;
          if (st.error) { toast("Agent en échec : " + st.error, true); return; }
          const s = st.stats || {};
          toast(`📚 Terminé : ${s.chapitres_crees || 0} chapitres créés` +
                (s.chapitres_mis_a_jour ? ` (+${s.chapitres_mis_a_jour} mis à jour)` : "") +
                `, ${s.entites_creees || 0} entités` +
                (s.entites_enrichies ? ` (+${s.entites_enrichies} enrichies)` : "") +
                `, ${s.zones_surlignees || 0} zones surlignées.`);
          await loadEntities();
          await loadChapters();
          await renderBible();
          setTimeout(() => $("#msModal").classList.add("hidden"), 1200);
        }
      } catch (e) { /* poll silencieux */ }
    }, 2000);
  } catch (e) {
    $("#msRun").disabled = false;
    toast("Agent manuscrit : " + e.message, true);
  }
}

/* ═════════ utilitaires ═════════ */
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

/* ═════════ wiring global ═════════ */
window.addEventListener("DOMContentLoaded", async () => {
  // chapitres
  $("#newChapter").addEventListener("click", async () => {
    const ch = await api.send("POST", "/chapters", { title: "Nouveau chapitre", series: $("#chapterSeries").value });
    await loadChapters(ch.id);
  });
  $("#chapterSelect").addEventListener("change", e => e.target.value && openChapter(e.target.value));
  $("#deleteChapter").addEventListener("click", async () => {
    if (!chapter || !confirm(`Supprimer le chapitre « ${chapter.title} » ?`)) return;
    await api.send("DELETE", "/chapters/" + chapter.id);
    chapter = null; $("#script").value = "";
    await loadChapters();
  });
  ["#chapterTitle", "#chapterSeries"].forEach(s => $(s).addEventListener("input", scheduleSave));

  // éditeur
  const ta = $("#script");
  ta.addEventListener("input", () => { renderScript(); scheduleSave(); refreshSelBar(); });
  ta.addEventListener("scroll", syncScroll);
  ["mouseup", "keyup"].forEach(ev => ta.addEventListener(ev, refreshSelBar));

  // import fichier (réutilise la mécanique Épisodes)
  $("#importFile").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f || !chapter) { if (!chapter) toast("Crée d'abord un chapitre.", true); return; }
    const fd = new FormData(); fd.append("file", f);
    toast("Extraction du texte…");
    try {
      const r = await fetch("/api/episodes/extract-text", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || !d.text) throw new Error(d.detail || d.error || "extraction vide");
      ta.value = d.text;
      if (chapter.title === "Nouveau chapitre" && d.title) $("#chapterTitle").value = d.title;
      renderScript(); scheduleSave();
      toast(`Importé : ${f.name} (${(d.text || "").length} caractères).`);
    } catch (err) { toast("Import échoué : " + err.message, true); }
    e.target.value = "";
  });

  // barre de sélection
  document.querySelectorAll("#selBar [data-kind]").forEach(b =>
    b.addEventListener("click", () => createEntityFromSelection(b.dataset.kind)));
  $("#linkSelect").addEventListener("change", (e) => {
    const id = e.target.value; if (!id) return;
    const sel = currentSelection(); if (sel) addSpan(sel, id);
    e.target.value = "";
  });

  // storyboard
  document.querySelectorAll("#modeTabs .tab").forEach(t =>
    t.addEventListener("click", () => setMode(t.dataset.mode)));
  $("#adaptBtn").addEventListener("click", adaptChapter);
  $("#cutAI").addEventListener("click", () => decoupe("ai"));
  $("#cutPara").addEventListener("click", () => decoupe("paragraph"));
  $("#addShot").addEventListener("click", async () => {
    if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
    await api.send("POST", `/chapters/${chapter.id}/shots`, {});
    await loadShots(true);
  });

  // bible
  document.querySelectorAll(".bible-pane .tab").forEach(t =>
    t.addEventListener("click", () => { setTab(t.dataset.kind); renderBible(); }));
  $("#addEntity").addEventListener("click", async () => {
    const name = prompt(`Nom du nouveau ${KIND_LABEL[curKind].toLowerCase()} :`);
    if (!name || !name.trim()) return;
    const ent = await api.send("POST", "/bible/entities", { kind: curKind, name: name.trim() });
    entities.push(ent); renderBible();
  });

  // agent manuscrit
  $("#msBtn").addEventListener("click", () => $("#msModal").classList.remove("hidden"));
  $("#msClose").addEventListener("click", () => $("#msModal").classList.add("hidden"));
  $("#msModal").addEventListener("click", (e) => { if (e.target.id === "msModal") $("#msModal").classList.add("hidden"); });
  $("#msRun").addEventListener("click", msRun);

  // modal
  $("#libClose").addEventListener("click", () => $("#libModal").classList.add("hidden"));
  $("#libModal").addEventListener("click", (e) => { if (e.target.id === "libModal") $("#libModal").classList.add("hidden"); });

  // import externe → Library → inspiration (fichier local ou URL web)
  $("#libUpload").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f || !libTarget) return;
    toast("Import du fichier…");
    try {
      const fd = new FormData(); fd.append("file", f);
      const r = await fetch("/api/images/upload", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || !d.filename) throw new Error(d.detail || "upload échoué");
      await attachInspiration(d.filename);
    } catch (err) { toast("Import échoué : " + err.message, true); }
    e.target.value = "";
  });
  $("#libUrl").addEventListener("click", async () => {
    if (!libTarget) return;
    const url = prompt("URL de l'image (http…) :");
    if (!url || !url.trim()) return;
    toast("Téléchargement de l'image…");
    try {
      const d = await api.send("POST", "/images/fetch", { url: url.trim() });
      if (!d.filename) throw new Error("réponse sans fichier");
      await attachInspiration(d.filename);
    } catch (err) { toast("Import URL échoué : " + err.message, true); }
  });

  // boot
  try {
    await loadEntities();
    await loadChapters();
    await renderBible();
  } catch (e) { toast("Chargement initial échoué : " + e.message, true); }
});
