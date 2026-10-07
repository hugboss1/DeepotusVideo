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
let voices11 = null;        // voix ElevenLabs du compte (lazy)
let voiceAudio = null;      // pré-écoute en cours (un seul lecteur)
let shotcraft = null;       // {status, cards} — pont video-shotcraft (W-d)

const SHOT_TYPES = ["establishing", "wide", "medium", "close-up",
  "extreme close-up", "over-shoulder", "POV", "insert"];
const CAMERA_MOVES = ["slow push-in", "slow pull-out", "360-degree orbit",
  "tracking shot", "handheld with subtle shake", "static, locked-off",
  "low angle dramatic", "rack focus reveal", "dolly zoom (vertigo effect)",
  "whip pan transition", "crane shot descending"];
const ENERGY_LABELS = { 1: "1 · calme", 2: "2 · posé", 3: "3 · moyen",
                        4: "4 · intense", 5: "5 · pic" };

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
  await loadVectorDocs();
  await majEmporte();
}

/* ═════════ tâche #59 (02/10/2026) : un chapitre EMPORTÉ par le téléphone ═════════
   Tant qu'il l'écrit hors ligne, le PC le laisse en lecture seule (le serveur répond 423 à toute écriture).
   « Reprendre sur le PC » force la libération ; tout texte refusé (retour du téléphone, ré-import) est au journal,
   d'où on peut le copier ou le reprendre. */
let emporte = null;         // {appareil:{nom}, pris_le} si le chapitre ouvert est emporté
const MOTIF_LABEL = { verrou_perdu: "retour refusé (le téléphone ne l'avait plus)", base_differente: "retour sur une autre version",
                      reimport: "ré-import du manuscrit", repris_pc: "repris sur le PC", revoque: "appareil révoqué" };

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
    (emporte ? `<p>📱 Emporté par le téléphone « ${esc(emporte.appareil.nom)} » depuis le ${quand(emporte.pris_le)} : il l'écrit
       hors ligne. Lecture seule ici, pour que rien ne soit écrasé.</p>
       <button class="btn" id="btnReprendre" title="Libère le chapitre : son retour du téléphone sera gardé au journal, jamais perdu">Reprendre sur le PC</button>` : "")
    + (journal.length ? `<div class="journal"><p>Textes gardés au journal (${journal.length}) :</p>` + journal.map(c =>
      `<div class="journal-ligne"><span>${quand(c.quand)} · ${esc(MOTIF_LABEL[c.motif] || c.motif)}${c.appareil ? " · " + esc(c.appareil) : ""}
       · ${c.texte.length} caractères</span>
       <button class="btn" data-copier="${c.id}" title="Copie ce texte dans le presse-papiers">Copier</button>
       <button class="btn" data-remplacer="${c.id}" ${emporte ? "disabled" : ""}
         title="Remplace le texte du chapitre par celui-ci (l'actuel est perdu s'il n'est pas copié)">Remplacer le texte</button></div>`).join("") + `</div>` : "");
  box.classList.remove("hidden");
  const r = $("#btnReprendre");
  if (r) r.onclick = async () => {
    if (!await window.__dzDialogue.confirmer(`Reprendre « ${chapter.title} » sur le PC ? Le téléphone « ${emporte.appareil.nom} » ne pourra plus le rendre : son texte ira au journal.`, { ok: "Reprendre" })) return;
    try { await api.send("POST", `/chapters/${chapter.id}/reprendre`); toast("Chapitre repris sur le PC."); }
    catch (e) { toast("Reprise impossible : " + e.message, true); }
    await majEmporte();
  };
  box.querySelectorAll("[data-copier]").forEach(b => b.onclick = async () => {
    const c = journal.find(x => String(x.id) === b.dataset.copier);
    try { await navigator.clipboard.writeText(c.texte); toast("Texte copié."); } catch (e) { toast("Copie impossible : " + e.message, true); }
  });
  box.querySelectorAll("[data-remplacer]").forEach(b => b.onclick = async () => {
    const c = journal.find(x => String(x.id) === b.dataset.remplacer);
    if (!await window.__dzDialogue.confirmer("Remplacer le texte actuel du chapitre par ce texte du journal ?", { ok: "Remplacer" })) return;
    $("#script").value = c.texte; renderScript(); scheduleSave();
  });
}

function scheduleSave() {
  if (!chapter) return;
  if (emporte) { $("#saveState").textContent = "emporté"; $("#saveState").className = "savestate"; return; }
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
  if (!v) return `<span class="cast-chip cast-none" title="Pas de voix castée — 🎙 Suggérer ou 🧬 Cloner sur sa fiche de bible">${esc(name)} · sans voix</span>`;
  const t = ((v.style && v.style.tags) || []).join(" ");
  return `<span class="cast-chip" title="Voix ${esc(v.voice_id)}${t ? " · tempérament " + esc(t) : ""}">${esc(name)} · ${esc(v.name)}${t ? " " + esc(t) : ""}</span>`;
}
function temperRow(e) {
  const vt = voiceTags || { groups: {}, providers: {} };
  const on = (e.voice_style && e.voice_style.tags) || [];
  if (!vt.providers || !vt.providers.elevenlabs) {
    return `<div class="voice-temper"><span class="temper-note">Tempérament : ${vt.providers && vt.providers.voicebox
      ? "Voicebox ne lit pas les balises Eleven v3" : "clé ElevenLabs requise"}${on.length ? " — gardé : " + on.map(esc).join(" ") : ""}</span></div>`;
  }
  // l'émotion et la voix seulement : les bruitages (« sons ») n'ont rien à faire sur une fiche de personnage
  const tags = [].concat(vt.groups.emotion || [], vt.groups.voix || []);
  return `<div class="voice-temper" title="Tempérament : ces balises Eleven v3 sont posées devant chaque réplique de ce personnage (4 au plus)">
    <span class="temper-note">Tempérament :</span>
    ${tags.map(t => `<button class="btn ghost act-temper${on.includes(t) ? " on" : ""}" data-t="${esc(t)}" aria-pressed="${on.includes(t)}">${esc(t)}</button>`).join("")}
  </div>`;
}

async function renderBible() {
  if (curKind === "character") await loadVoiceTags();
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
        ? `<a href="/api/images/${encodeURIComponent(e.ref_image)}" target="_blank" title="Turnaround — ouvrir en grand">
             <img class="refimg board-ref" src="/api/images/${encodeURIComponent(e.ref_image)}" alt="turnaround"></a>`
        : `<div class="refimg empty">Pas encore de planche<br>— Générer ⤵</div>`}
      ${e.face_image
        ? `<a href="/api/images/${encodeURIComponent(e.face_image)}" target="_blank" title="Gros plans visage — ouvrir en grand">
             <img class="refimg board-ref" src="/api/images/${encodeURIComponent(e.face_image)}" alt="visages"></a>`
        : ""}
      <div class="seedrow">
        ${e.seed != null ? `<span class="seedbadge" title="Seed verrouillé de la planche">🔒 ${e.seed}</span>` : `<span class="seedbadge" style="opacity:.5">seed —</span>`}
        ${e.model3d_job
          ? `<a class="seedbadge" href="/api/assets/3d/${encodeURIComponent(e.model3d_job)}/version/1" title="Maillage verrouillé — télécharger le GLB (Blender, Unity, Unreal, three.js)">🧊 GLB</a>`
          : ""}
      </div>
      <div class="entity-actions">
        <button class="btn primary act-gen" title="Génère la planche de référence multi-vues (personnage: face + profils + dos + gros plans visage — un seul seed pour tous les angles)">🎨 Planche</button>
        <button class="btn act-roll" title="Nouvelle planche, seed aléatoire">🎲</button>
        ${e.has_recipe ? `<button class="btn act-recipe" title="Rejoue la recette verrouillée (prompt exact + seed) — image identique garantie">🔁</button>` : ""}
        ${BESOIN_3D_PAR_KIND[e.kind]
          ? `<button class="btn act-3d" title="Verrouille l'entité EN 3D : une vue unique → maillage GLB réutilisable par tous les chapitres, et exportable vers Blender / Unity / Unreal. Le moteur et son coût sont annoncés avant de lancer.">🧊 3D</button>`
          : ""}
      </div>
    </div>
    <div class="entity-main">
      <div class="row1">
        <span class="kinddot k-${e.kind}"></span>
        <input class="entity-name" value="${esc(e.name)}" title="Nom">
        <button class="btn ghost act-apps" title="Où cette entité apparaît : mentions, plans, scènes, chapitre par chapitre">⛓ Apparitions</button>
        <button class="btn ghost act-del" title="Supprimer l'entité">🗑</button>
      </div>
      <textarea class="entity-desc" placeholder="Description physique / visuelle (sert de prompt de référence)">${esc(e.description)}</textarea>
      <input class="entity-style" placeholder="Style spécifique (vide = style global du projet)" title="Override ponctuel : si renseigné, cette entité est générée dans CE style au lieu du style global du projet" value="${esc(e.style_notes)}">
      <div class="entity-apps hidden"></div>
      ${e.kind === "character" ? `
      <div class="voice-row">
        🎙 <span class="voice-name">${e.voice_name ? esc(e.voice_name) : "<i style='opacity:.55'>pas de voix</i>"}</span>
        ${e.voice_prev ? `<button class="btn ghost act-voice-play" title="Pré-écouter la voix">▶</button>` : ""}
        <button class="btn act-voice-suggest" title="L'agent croise la fiche du personnage (genre, âge, ton) avec les voix ElevenLabs de ton compte et propose la meilleure + des alternatives du même profil">🎙 Suggérer</button>
        <button class="btn ghost act-voice-all" title="Choisir manuellement parmi toutes les voix du compte">⌄ Toutes</button>
        <button class="btn ghost act-voice-clone" title="Cloner une voix pour CE personnage à partir de prises du dossier audio (1 à 2 min d'audio propre) — ElevenLabs, occupe un emplacement de voix du compte">🧬 Cloner</button>
      </div>
      ${temperRow(e)}
      <div class="voice-alts hidden"></div>` : ""}
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
    const rbtn = card.querySelector(".act-recipe");
    if (rbtn) rbtn.addEventListener("click", () => generateRef(id, null, true));
    const btn3d = card.querySelector(".act-3d");
    if (btn3d) btn3d.addEventListener("click", () => entityTo3D(id));
    card.querySelector(".act-apps").addEventListener("click", () => showApparitions(id, card));
    card.querySelector(".act-del").addEventListener("click", async () => {
      if (!await window.__dzDialogue.confirmer(`Supprimer « ${ent().name} » de la bible ?`)) return;
      try {
        await api.send("DELETE", "/bible/entities/" + id);
        entities = entities.filter(x => x.id !== id);
        (chapter && chapter.spans || []).forEach(sp => { if (sp.entity_id === id) sp.orphan = true; });
        await renderBible(); renderScript(); scheduleSave();
      } catch (e) { toast("Suppression échouée : " + e.message, true); }
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
      const raw = await window.__dzDialogue.saisir("Prises du dossier audio, séparées par des virgules "
        + "(1 à 2 min d'audio propre de ce personnage) :", { titre: "Cloner une voix", ok: "Suivant" });
      const files = String(raw || "").split(",").map(s => s.trim()).filter(Boolean);
      if (!files.length) return;
      if (!await window.__dzDialogue.confirmer(`Cloner la voix de « ${ent().name} » depuis ${files.length} prise(s) ? `
        + "ElevenLabs crée une voix dans ton compte (un emplacement de voix, selon ton plan).", { ok: "Cloner" })) return;
      try {
        const d = await api.send("POST", `/bible/entities/${id}/voice-clone`, { files });
        Object.assign(ent(), d.entity);
        toast(`Voix clonée : ${d.voice_id}` + (d.requires_verification ? " — vérification demandée par ElevenLabs" : ""));
        await loadVoiceCast();
        await renderBible();
      } catch (e) { toast("Clonage échoué : " + e.message, true); }
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
      } catch (e) { toast("Tempérament : " + e.message, true); }
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
  if (!useRecipe && !(ent.description || "").trim()) { toast("Ajoute une description avant de générer.", true); return; }
  toast(useRecipe ? `🔁 Recette exacte de « ${ent.name} »… (~3 s)`
                  : `Planche de « ${ent.name} »… (~3 s)`);
  try {
    const body = useRecipe ? { use_recipe: true } : (seed != null ? { seed } : {});
    const up = await api.send("POST", `/bible/entities/${id}/generate`, body);
    Object.assign(ent, up);
    await renderBible();
    toast(`Planche de « ${ent.name} » ${useRecipe ? "rejouée à l'identique" : "générée"} — seed ${up.seed} 🔒 (recette enregistrée 🔁).`);
  } catch (e) { toast("Génération échouée : " + e.message, true); }
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
    el.textContent = `🎬 shotcraft · ${shotcraft.status.cards} fiches · ` +
      (shotcraft.status.installed ? "skill installé" : "catalogue embarqué");
    el.title = "Recettes motion video-shotcraft — l'IA de découpage les " +
      "utilise (doctrine + catalogue), et chaque plan peut en porter une." +
      (shotcraft.status.path ? "\n" + shotcraft.status.path : "");
  }
}

function recipeOptions(cur) {
  const cards = (shotcraft && shotcraft.cards) || [];
  const opt = (c) => `<option value="${c.slug}"` +
    `${c.slug === cur ? " selected" : ""} title="${esc(c.gloss)}">` +
    `${c.slug}</option>`;
  const anim = cards.filter(c => c.anim), other = cards.filter(c => !c.anim);
  return `<option value=""${!cur ? " selected" : ""}>— recette motion —</option>` +
    (anim.length ? `<optgroup label="Animation / récit">${anim.map(opt).join("")}</optgroup>` : "") +
    (other.length ? `<optgroup label="Motion UI (promo)">${other.map(opt).join("")}</optgroup>` : "");
}

function energyOptions(cur) {
  return `<option value=""${cur == null ? " selected" : ""}>⚡ —</option>` +
    [1, 2, 3, 4, 5].map(v => `<option value="${v}"` +
      `${v === cur ? " selected" : ""}>⚡ ${ENERGY_LABELS[v]}</option>`).join("");
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
  if (!chapter) { list.innerHTML = `<div class="empty-note">Crée ou ouvre un chapitre d'abord.</div>`; return; }
  if (!scenes.length) {
    list.innerHTML = `<div class="empty-note">Pas encore de scénario pour ce chapitre.<br>
      🎭 <b>Adapter (IA)</b> transforme le roman en script de film (scènes, sluglines,
      éclairages, caméra) — sans toucher au manuscrit.</div>`;
    return;
  }
  const totVo = scenes.reduce((a, s) => a + (s.duration_s || 0), 0);
  const nVo = scenes.filter(s => s.vo_audio).length;
  $("#voTotal").textContent = nVo
    ? `Σ VO ${fmtDur(totVo)} (${nVo}/${scenes.length})` : "Σ VO —";
  list.innerHTML = scenes.map((s, i) => `
  <div class="scene-card" data-id="${s.id}">
    <div class="scene-slug">SCÈNE ${i + 1} · ${esc(s.slugline)}
      <span class="scene-vo">
        ${s.duration_s ? `<span class="seedbadge" title="Durée réelle du voice-over — c'est la durée de la scène">⏱ ${fmtDur(s.duration_s)}</span>` : ""}
        ${s.vo_audio ? `<button class="btn ghost sc-vo-play" title="Écouter le voice-over de la scène">▶</button>` : ""}
        <button class="btn sc-vo-gen" title="Génère le voice-over de la scène : narration lue par le Narrateur, répliques par les voix castées des personnages. La durée réelle minute la scène.">🔊${s.vo_audio ? " ↻" : ""}</button>
      </span>
    </div>
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
  toast(`🔊 Voice-over de la scène ${sc.idx + 1}… (~10-30 s)`);
  try {
    const r = await api.send("POST", `/scenes/${sceneId}/voiceover`,
                             { language: "fr" });
    Object.assign(sc, r.scene);
    renderScreenplay();
    const who = [...new Set((r.segments || []).map(x => x.speaker).filter(Boolean))];
    toast(`⏱ Scène ${sc.idx + 1} minutée : ${fmtDur(r.duration_s)}` +
          (who.length ? ` — voix : ${who.join(", ")}` : "") + ".");
  } catch (e) { toast("Voice-over échoué : " + e.message, true); }
}

async function chapterVo() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (!scenes.length) { toast("Pas de scénario — 🎭 Adapter d'abord.", true); return; }
  const missing = scenes.filter(s => !s.vo_audio).length;
  const force = missing === 0 &&
    await window.__dzDialogue.confirmer("Toutes les scènes ont déjà un voice-over. Tout régénérer ?", { ok: "Tout régénérer" });
  if (missing === 0 && !force) return;
  toast(`🔊 Voice-over du chapitre (${force ? scenes.length : missing} scènes)…`);
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
        if (st.error) { toast("Voice-over : " + st.error, true); await loadScenes(true); return; }
        await loadScenes(true);
        toast(`⏱ Chapitre minuté : ${fmtDur(st.stats.duree_totale_s || 0)} ` +
              `(${st.stats.scenes_generees} générées, ${st.stats.scenes_conservees} conservées).`);
      } catch (e) { /* poll silencieux */ }
    }, 2500);
  } catch (e) { toast("Voice-over : " + e.message, true); }
}

/* ═════════ tâche #64 (plan chapitres T13) — importer un scénario Fountain / Final Draft ═════════
   Remplacer (défaut) : le dialogue NOMME les scènes et les voix-off perdues, et le scénario entier est sauvegardé
   avant (tiroir des versions, « scénario importé ») ; sinon ajouter à la suite ; Échap deux fois = rien. */
async function importerScenario(f) {
  if (!f || !chapter) { if (!chapter) toast("Ouvre un chapitre d'abord.", true); return; }
  let mode = "remplacer";
  if (scenes.length) {
    const vo = scenes.filter(s => s.vo_audio).length;
    const remplacer = await window.__dzDialogue.confirmer(
      `« ${f.name} » remplacera les ${scenes.length} scène(s) de ce chapitre` +
      (vo ? `, dont ${vo} avec une voix-off (elle sera perdue)` : "") +
      ". Le scénario actuel est sauvegardé avant (tiroir des versions).",
      { ok: "Remplacer", annuler: "Ne pas remplacer" });
    if (!remplacer) {
      if (!await window.__dzDialogue.confirmer(`Ajouter les scènes de « ${f.name} » à la suite des ${scenes.length} existantes ?`,
          { ok: "Ajouter à la suite" })) return;
      mode = "ajouter";
    }
  }
  const fd = new FormData(); fd.append("file", f); fd.append("mode", mode);
  toast(`Import de « ${f.name} »…`);
  try {
    const r = await fetch(`/api/chapters/${encodeURIComponent(chapter.id)}/screenplay/import`, { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail && d.detail.message ? d.detail.message : (d.detail || r.statusText));
    await loadScenes(true);
    const ign = Object.entries(d.ignores || {}).map(([k, n]) => `${n} ${k.replace(/_/g, " ")}`).join(", ");
    toast(`${d.format === "fdx" ? "Final Draft" : "Fountain"} : ${d.scenes} scène(s) ${mode === "ajouter" ? "ajoutée(s)" : "importée(s)"}` +
          (d.lieux_crees ? `, ${d.lieux_crees} lieu(x) créé(s) dans la bible` : "") +
          (d.personnages_lies ? `, ${d.personnages_lies} lien(s) personnage` : "") +
          (d.prologue ? " — le texte avant la 1re scène est rattaché à la scène 1" : "") +
          (ign ? ` — écartés : ${ign}` : "") + ".");
  } catch (e) { toast("Import du scénario : " + e.message, true); }
}

/* ═════════ tâche #65 (plan chapitres T16) — les exports : téléchargés par fetch, erreurs DITES ═════════
   Un lien <a download> nu rendrait une erreur 400 en fichier JSON : ici l'erreur passe par le dialogue maison, et les
   caractères remplacés dans un PDF (hors police standard) sont annoncés. */
async function telechargerExport(chemin) {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  toast("Export…");
  try {
    const r = await fetch(`/api/chapters/${encodeURIComponent(chapter.id)}/${chemin}`);
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      await window.__dzDialogue.informer("Export impossible : " + (d.detail || r.statusText), { titre: "Export" });
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
    toast(`« ${nom} » exporté` + (n ? ` — ${n} caractère(s) hors de la police standard remplacé(s) dans le PDF (le .docx les garde).` : "."));
  } catch (e) { toast("Export : " + e.message, true); }
}

/* ═════════ tâche #66 (plan chapitres T17) — réécrire dans le ton de la bible ═════════
   Trois temps : DEVIS (gratuit) -> dialogue qui DIT le coût -> proposition (payée, plafonds) ; appliquer est gratuit,
   sauvegardé (version « réécriture ») et refusé si le passage a changé entre-temps (409). L'action est gardée ICI :
   le sélecteur, lui, revient à « Réécrire… ». */
let reeEnCours = null;      // {start, end, action, mode, attendu, langue}
const REE_LANGUES = { fr: "français", en: "anglais", es: "espagnol", de: "allemand", it: "italien", pt: "portugais" };

async function sauverMaintenant() {
  if (!chapter || emporte) return;
  clearTimeout(saveTimer);
  chapter.script_text = $("#script").value;
  await api.send("PUT", "/chapters/" + chapter.id, { title: chapter.title, series: chapter.series,
    script_text: chapter.script_text, spans: chapter.spans });
}

async function reecrire(action) {
  const sel = currentSelection();
  if (!chapter || !sel) { toast("Sélectionne un passage d'abord.", true); return; }
  let langue = "fr";
  if (action === "traduire") {
    const l = await window.__dzDialogue.saisir(`Langue cible : ${Object.entries(REE_LANGUES).map(([k, v]) => `${k} (${v})`).join(", ")}`,
      { valeur: "en", ok: "Chiffrer", titre: "Traduire" });
    if (l == null) return;
    langue = l.trim().toLowerCase().slice(0, 2);
    if (!REE_LANGUES[langue]) { toast(`Langue « ${l} » inconnue.`, true); return; }
  }
  try {
    await sauverMaintenant();                               // le serveur chiffre et propose sur le texte À JOUR
    const corps = { start: sel.start, end: sel.end, action, language: langue };
    const dv = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/reecrire`, { ...corps, devis: true });
    const usd = `${(dv.usd || 0).toFixed(3).replace(".", ",")} $`;
    if (!await window.__dzDialogue.confirmer(
        `${$("#reeAction").querySelector(`option[value="${action}"]`).textContent.replace("…", "")} — ${dv.fournisseur}, ` +
        `≈ ${dv.jetons.entree + dv.jetons.sortie} jetons. Coût estimé : ${usd}. La proposition s'affichera ; rien n'est écrit sans votre accord.`,
        { ok: "Proposer" })) return;
    toast("Le modèle relit la bible… (5-20 s)");
    const d = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/reecrire`, corps);
    reeEnCours = { start: d.start, end: d.end, action, mode: d.mode, attendu: d.attendu, langue };
    $("#reeTitre").textContent = d.mode === "remplace" ? "Proposition — remplacera la sélection" : "Proposition — sera insérée après la sélection";
    $("#reeNote").textContent = `${action}${action === "traduire" ? " → " + REE_LANGUES[langue] : ""} · ${d.provider}`;
    $("#reeTexte").value = d.proposition;
    $("#reeModal").classList.remove("hidden");
  } catch (e) { toast("Réécriture : " + e.message, true); }
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
    toast("Appliqué — l'état d'avant est dans 🕘 Versions.");
  } catch (e) { toast("Application impossible : " + e.message, true); }
}

async function adaptChapter() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (scenes.length && !await window.__dzDialogue.confirmer("Ré-adapter remplacera le scénario actuel de ce chapitre. Continuer ?", { ok: "Ré-adapter" })) return;
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
        <button class="btn ghost act-prod" title="Image de production : Nano Banana avec les vues des entités du plan en référence — coût affiché et confirmé avant">🖼</button>
        <button class="btn ghost act-plateau" title="Plateau 3D : composer ce plan en 3D (gratuit), mesurer son cadre et son mouvement, capturer ses images de début et de fin">🎥</button>
      </div>
      ${s.image ? `<div class="shot-prod"><img src="/api/images/${encodeURIComponent(s.image)}" alt="image de production"
        title="Image de production — ${s.image_refs || 0} vue(s) en référence"><span>🖼 ${s.image_refs || 0} réf.</span>
        <button class="btn ghost act-derive" title="Mesurer la dérive (gratuit, lecture seule) : couleur et silhouette comparées à la vue de chaque entité">📏</button></div>
        <div class="shot-derive"></div>` : ""}
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
      <div class="shot-params shot-craft">
        <select class="shot-recipe" title="Recette motion video-shotcraft (colore le croquis, et la production ensuite)">${recipeOptions(s.motion_recipe)}</select>
        <select class="shot-energy" title="Énergie du plan (1 calme → 5 pic) — la courbe doit respirer">${energyOptions(s.energy)}</select>
      </div>
      <div class="shot-ents">${entChips(s.entities) || "<span style='opacity:.5'>aucune entité détectée</span>"}</div>
      <div class="shot-cast" title="Qui parlera, avec quelle voix et quel tempérament (T103)">${(s.entities || []).map(eid => {
        const en = entities.find(x => x.id === eid);
        return en && en.kind === "character" ? castChip(en.name) : "";
      }).join("") || "<span style='opacity:.5'>aucun personnage dans ce plan</span>"}</div>
      ${entPicker(s.entities)}
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
      if (!await window.__dzDialogue.confirmer(`Supprimer le plan ${sh().idx + 1} ?`)) return;
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
        card.querySelector(".shot-ents").innerHTML = entChips(up.entities) || "<span style='opacity:.5'>aucune entité</span>";
      } catch (e) { toast("Entités du plan : " + e.message, true); }
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

/* ═════════ tâche #62 (plan chapitres T8) — l'image de PRODUCTION d'un plan ═════════
   Nano Banana reçoit les vues des entités du plan. Dépense réelle : le coût (grille du PC) est DIT et CONFIRMÉ avant ;
   au-delà d'un plafond mensuel, dz-plafonds.js montre le dialogue 402 et rejoue sur confirmation. */
async function imageProduction(id) {
  const s = shots.find(x => x.id === id);
  if (!s) return;
  if (!(s.entities || []).length) { toast("Liez d'abord une entité à ce plan (⛓ entités du plan).", true); return; }
  let provider = "nano-banana-pro", usd = null;
  try {
    provider = (await api.get("/atelier/settings")).settings.image_provider || provider;
    const grille = await api.get("/cost/pricing");
    usd = grille[provider === "nano-banana" ? "nano_banana_usd" : "nano_banana_pro_usd"];
  } catch (e) { /* le coût reste inconnu : on le dit */ }
  if (provider !== "nano-banana" && provider !== "nano-banana-pro") {
    toast(`« ${provider} » ne prend pas plusieurs références : choisissez Nano Banana (Pro) dans la direction artistique.`, true);
    return;
  }
  const cout = typeof usd === "number" ? `${usd.toFixed(3).replace(".", ",")} $` : "coût inconnu";
  if (!await window.__dzDialogue.confirmer(
      `Image de production du plan ${s.idx + 1} — ${provider === "nano-banana" ? "Nano Banana" : "Nano Banana Pro"}, avec les vues de ses entités en référence. Coût : ${cout}.`,
      { ok: "Générer" })) return;
  toast(`Image de production du plan ${s.idx + 1}…`);
  try {
    const up = await api.send("POST", `/shots/${encodeURIComponent(id)}/image`, {});
    Object.assign(s, up);
    renderBoard();
    toast(`Image de production du plan ${s.idx + 1} : ${up.image_refs} vue(s) en référence.`);
  } catch (e) { toast("Image de production : " + e.message, true); }
}

/* ═════════ tâche #62 (plan chapitres T6) — la DÉRIVE de l'image de production, en lecture ═════════
   Gratuit, rien n'est décidé : l'écart de couleur (ΔE) et de silhouette avec la vue de chaque entité, et l'angle mort. */
async function deriveProduction(id, card) {
  const box = card.querySelector(".shot-derive");
  if (!box) return;
  box.textContent = "Mesure…";
  try {
    const d = await api.get(`/shots/${encodeURIComponent(id)}/derive`);
    const lignes = (d.entites || []).map(e => e.vue == null
      ? `<div class="drv-l"><b>${esc(e.name)}</b> — aucune vue de référence</div>`
      : `<div class="drv-l drv-${e.verdict === "stable" ? "ok" : "ko"}"><b>${esc(e.name)}</b> ${e.verdict === "stable" ? "stable" : "dérive"}
         · couleur ΔE ${e.ecart_couleur.toFixed(1).replace(".", ",")} (seuil ${d.seuils.couleur})
         · silhouette ${e.ecart_silhouette.toFixed(2).replace(".", ",")} (seuil ${String(d.seuils.silhouette).replace(".", ",")})
         <span class="drv-vue" title="Vue de référence : ${escA(e.fichier)} (${escA(e.source)})">vs ${esc(e.vue)}</span></div>`);
    box.innerHTML = (lignes.join("") || "<div class=\"drv-l\">Aucune entité liée.</div>")
      + `<div class="drv-mort" title="Ce que la mesure ne voit pas">Angle mort : ${esc(d.angle_mort)}.</div>`;
  } catch (e) { box.textContent = "Dérive : " + e.message; }
}

/* ═════════ tâche #63 (plan chapitres T11) — l'animatique : devis, progression, lecteur ═════════
   Muette et gratuite par défaut (décision du 02/10) ; la voix témoin (Narrateur de la bible) est cochée à la main,
   son coût — seulement les voix PAS encore en cache — est dit et confirmé avant ; au-delà d'un plafond, dz-plafonds.js
   montre le dialogue 402 et rejoue sur confirmation. */
let animDevis = null;

async function animatiqueEtat() {
  if (!chapter) return null;
  $("#animDevis").textContent = "devis…";      // la sonde de Voicebox local peut prendre quelques secondes
  const e = await api.get(`/chapters/${encodeURIComponent(chapter.id)}/animatique`);
  animDevis = e.voix || {};
  const v = animDevis, box = $("#animVoix");
  let dit = "", ok = true;
  if (!v.fournisseur) { dit = "aucune voix configurée (Réglages)"; ok = false; }
  else if (!v.narrateur) { dit = "créez un « Narrateur » dans la bible et castez sa voix"; ok = false; }
  else if (!v.a_generer) dit = `${v.narrateur} · tout est en cache : gratuit`;
  else if (v.fournisseur === "elevenlabs") dit = `${v.narrateur} · ${v.a_generer} voix à générer, ${v.caracteres} car. ≈ ${v.usd.toFixed(3).replace(".", ",")} $`;
  else dit = `${v.narrateur} · ${v.a_generer} voix (Voicebox, local, gratuit)`;
  box.disabled = !ok;
  if (!ok) box.checked = false;
  $("#animDevis").textContent = dit;
  $("#animVideo").classList.toggle("hidden", !e.existe);
  $("#animVide").classList.toggle("hidden", !!e.existe);
  if (e.existe) $("#animVideo").src = `${e.url}?t=${Math.round(e.maj || 0)}`;
  await sortiesEtat();                                       // tâche #66 : film / reel vers le Montage
  $("#animNote").textContent = `${e.storyboard} plan(s)` + (e.existe ? ` · dernier montage : ${e.plans} plan(s)` : "");
  return e;
}

async function ouvrirAnimatique() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  $("#animProgress").classList.add("hidden");
  $("#animModal").classList.remove("hidden");
  try { await animatiqueEtat(); } catch (e) { toast("Animatique : " + e.message, true); }
}

function animProgres(st) {
  const n = st.chapter_n || 0, i = st.chapter_i || 0;
  const pct = st.done ? 100 : n ? Math.round(100 * i / n) : 0;
  $("#animBar").style.width = pct + "%";
  $("#animStatus").textContent = st.error ? "Échec : " + st.error : (st.message || "…");
}

async function monterAnimatique() {
  if (!chapter) return;
  if (!shots.length) { toast("Découpe le chapitre en plans d'abord (🎬 ou ¶).", true); return; }
  const voix = $("#animVoix").checked;
  if (voix) {
    try { await animatiqueEtat(); } catch (_) { /* le devis d'avant reste affiché */ }
    const v = animDevis || {};
    if (v.fournisseur === "elevenlabs" && v.a_generer > 0 && !await window.__dzDialogue.confirmer(
        `Voix témoin ElevenLabs : ${v.a_generer} voix à générer (${v.caracteres} caractères), lues par ${v.narrateur}. Coût estimé : ${v.usd.toFixed(3).replace(".", ",")} $. Les voix déjà faites restent en cache.`,
        { ok: "Générer les voix" })) return;
  }
  $("#animGo").disabled = true;
  $("#animProgress").classList.remove("hidden");
  animProgres({ message: "Animatique…" });
  try {
    const r = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/animatique`, { voix, language: "fr" });
    let st = {};
    while (!st.done) {
      await new Promise(res => setTimeout(res, 700));
      st = await api.get(`/atelier/manuscript/${r.job_id}`);
      animProgres(st);
    }
    if (st.error) { toast("Animatique échouée : " + st.error, true); return; }
    await animatiqueEtat();
    const s = st.stats || {};
    toast(`Animatique montée : ${s.plans} plans, ${s.voix} voix témoin, ${fmtDur(s.duree_s || 0)}.`);
  } catch (e) {
    toast("Animatique : " + e.message, true);
  } finally { $("#animGo").disabled = false; }
}

/* ═════════ tâche #66 PR B — l'animatique sort vers le Montage (film / reel), en NOUVEAU projet ═════════ */
/* ═════════ tâche #66 PR C — la sortie « épisode », sans rendu ═════════ */
async function versEpisode() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  try {
    const r = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/episode`, { language: "fr" });
    if (await window.__dzDialogue.confirmer(
        `Épisode « ${r.title} » créé : ${r.scenes} scène(s), ${r.images} avec image. Rien n'a été narré ni rendu — ` +
        `la narration et le rendu (payants) se lancent depuis la vue Épisodes, avec leur devis. Pour l'ouvrir : vue Chapitres → « Flux d'origine » → « Ouvrir ▾ ».`,
        { ok: "Aller aux Épisodes", annuler: "Rester ici", titre: "Épisode" }))
      window.open(r.vue, "_blank");
  } catch (e) { toast("Épisode : " + e.message, true); }
}

async function sortiesEtat() {
  if (!chapter) return;
  try {
    const s = await api.get(`/chapters/${encodeURIComponent(chapter.id)}/sorties`);
    $("#animSorties").classList.toggle("hidden", !s.animatique);
    ["film", "reel"].forEach(n => { const b = $(`[data-sortie="${n}"]`), v = (s.natures || {})[n];
      b.disabled = !s.a_jour;
      if (v) b.textContent = `${n === "film" ? "🎬 Film" : "⚡ Reel"} · ${v.plans} plan(s), ${fmtDur(v.duree_s)}`; });
    $("#animSortieNote").textContent = s.animatique && !s.a_jour ? "le storyboard a changé : remontez l'animatique" : "";
  } catch (_) { $("#animSorties").classList.add("hidden"); }
}

async function sortieMontage(nature) {
  if (!chapter) return;
  try {
    const r = await api.send("POST", `/chapters/${encodeURIComponent(chapter.id)}/sortie/${nature}`, {});
    if (await window.__dzDialogue.confirmer(
        `Projet « ${r.name} » créé au Montage : ${r.plans} plan(s), ${fmtDur(r.duree_s)}, ${r.voix} voix témoin. ` +
        `La timeline en cours n'est pas touchée — ouvrez ce projet depuis la liste des projets du Montage.`,
        { ok: "Aller au Montage", annuler: "Rester ici", titre: "Montage" }))
      window.open(r.montage, "_blank");
  } catch (e) { toast("Sortie vers le Montage : " + e.message, true); }
}

async function decoupe(method) {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (!$("#script").value.trim()) { toast("Le chapitre est vide.", true); return; }
  if (shots.length && !await window.__dzDialogue.confirmer("Re-découper remplacera le storyboard actuel. Continuer ?", { ok: "Re-découper" })) return;
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
  toast(`Inspiration « ${filename} » ajoutée (elle est aussi dans la Library).`);
}

async function openLibrary(entityId, onPick) {
  libTarget = entityId;
  libOnPick = onPick || attachInspiration;
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
      img.addEventListener("click", async () => {
        $("#libModal").classList.add("hidden");
        await libOnPick(img.dataset.f);
      }));
  } catch (e) { grid.innerHTML = `<div class="empty-note">Erreur : ${esc(e.message)}</div>`; }
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
  if (!besoin) { toast("Seuls personnages, objets, lieux et décors se verrouillent en 3D.", true); return; }

  const cat = await catalogue3d();
  const b = (cat.besoins || []).find(x => x.id === besoin) || {};
  const eng = (cat.engines || []).find(x => x.id === b.engine) || {};
  if (eng.available === false) {
    toast("Clé fal absente — ajoute-la dans les Réglages avant de générer un maillage.", true);
    return;
  }
  toast("Choisis UNE vue — un moteur image→3D veut un seul angle, pas une planche.");
  openLibrary(id, async (f) => {
    const cout = eng.usd_texture != null ? `≈ ${eng.usd_texture} $` : "inconnu";
    const ok = await window.__dzDialogue.confirmer(
      `Verrouiller « ${ent.name} » en 3D ?\n\n` +
      `Moteur : ${eng.label || b.engine || "?"}\n` +
      `Pourquoi ce moteur : ${b.why || "—"}\n` +
      `Vue de départ : ${f}\n` +
      `Coût estimé : ${cout}`);
    if (!ok) return;
    try {
      const r = await api.send("POST", `/bible/entities/${id}/model3d`,
                               { image_filename: f, besoin });
      toast(`🧊 Maillage en cours (${r.engine}) — 1 à 3 min…`);
      const poll = setInterval(async () => {
        try {
          const st = await api.get("/jobs/" + r.job_id);
          if (st.status !== "done" && st.status !== "failed") return;
          clearInterval(poll);
          if (st.status === "failed") { toast("3D : " + (st.error || "échec"), true); return; }
          await loadEntities();
          await renderBible();
          toast(`🧊 « ${ent.name} » verrouillé en 3D — le GLB est sur sa fiche.`);
        } catch (e) { /* poll silencieux */ }
      }, 3000);
    } catch (e) { toast("3D : " + e.message, true); }
  });
}

/* ═════════ casting voix (B) ═════════ */
function playVoicePrev(url) {
  if (!url) return;
  try {
    if (voiceAudio) { voiceAudio.pause(); voiceAudio = null; }
    voiceAudio = new Audio(url);
    voiceAudio.play().catch(() => toast("Pré-écoute impossible.", true));
  } catch (e) { /* silencieux */ }
}

async function loadVoices11() {
  if (voices11) return voices11;
  const d = await api.get("/voices");
  if (!d.enabled) throw new Error("Clé ElevenLabs non configurée (Réglages).");
  voices11 = d.voices || [];
  return voices11;
}

function voiceChip(v, entityId) {
  const lbl = v.labels || {};
  const meta = [lbl.gender, lbl.age, lbl.accent].filter(Boolean).join(" · ");
  return `<span class="voice-chip" data-vid="${v.voice_id}">
    <b>${esc(v.name)}</b>${meta ? ` <i>${esc(meta)}</i>` : ""}
    ${v.preview_url ? `<button class="btn ghost vc-play" data-prev="${esc(v.preview_url)}" title="Pré-écouter">▶</button>` : ""}
    <button class="btn vc-pick" title="Attribuer cette voix">✓</button>
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
      toast(`Voix « ${up.voice_name} » attribuée à ${ent.name}.`);
      renderBible();
    }));
}

async function suggestVoice(entityId, card) {
  const ent = entities.find(x => x.id === entityId);
  if (!ent) return;
  if (!(ent.description || "").trim()) {
    toast("Décris le personnage d'abord (genre, âge, ton…).", true); return;
  }
  toast(`Casting de « ${ent.name} »… (~5 s)`);
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
    toast(`🎙 « ${d.suggested.name} » suggérée pour ${ent.name}` +
          ((d.alternates || []).length ? ` (+${d.alternates.length} alternatives du même profil)` : "") + ".");
  } catch (e) { toast("Casting échoué : " + e.message, true); }
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
  { label: "BD franco-belge", canon: "ligne_claire", sp: "European comic book art (bande dessinée), clean ink outlines, flat cel colors, ligne claire influence, expressive faces, detailed backgrounds" },
  { label: "Manga / Anime", canon: "manga_shonen", sp: "anime manga art style, sharp linework, cel shading, dramatic lighting, detailed eyes, cinematic anime composition" },
  { label: "Comics US", canon: "comics_heroic", sp: "American comic book style, bold inks, dynamic shading, halftone textures, dramatic panel lighting" },
  { label: "Réaliste photo", canon: "davinci", sp: "photorealistic, natural skin textures, realistic lighting, 85mm lens look, shallow depth of field" },
  { label: "Cinématographique", canon: "cine", sp: "cinematic film still, anamorphic framing, filmic color grading, volumetric light, high production value" },
  { label: "SF rétro-futuriste", canon: "bd_realiste", sp: "retro-futuristic science-fiction concept art, neon accents, brutalist megastructures, atmospheric haze" },
  { label: "Aquarelle", canon: "davinci", sp: "watercolor illustration, soft washes, visible paper grain, delicate ink lines, muted palette" },
  { label: "Noir encré", canon: "davinci", sp: "high-contrast black and white ink illustration, film noir shadows, dramatic chiaroscuro, crosshatching" },
  // Miroir du preset backend "vitrail" — le sp est LE bloc de la fiche épinglée
  // style_vitrail.json (test_style_vitrail.py vérifie l'égalité, zéro dérive).
  { label: "Vitrail Młoda Polska", canon: "vitrail", sp: "monumental Art Nouveau stained-glass window design, Central European modernism of about 1900: bold sinuous dark leadlines #1F1512, thick supple contours enclosing every shape and covering about a tenth of the canvas, irregular fragments of intensely saturated glass in 3 to 5 major colours - cobalt blue #0047AB, ruby red #9B111E, emerald green #046307, golden amber #DAA520, deep violet #4A235A - light transmitted from within the image as through a window, frontal ascending composition in a vertical or ogival bay, one central figure filling roughly two thirds of the height, simple hierarchy of figure then radiating halo then ornamental border of stylized flowers on the outer edge of the frame, flat decorative space with no deep linear perspective, high readability at distance" },
];
// Miroir de PROPORTION_CANONS (backend) — canons de proportions issus des
// grandes écoles: De Vinci, manga japonais, ligne claire belge, école
// gros-nez franco-belge, Moebius, comics héroïques DC/Marvel…
const PROPORTION_CANONS = [
  { id: "auto", label: "Auto (déduit du style)", hint: "Le canon est détecté depuis le texte du style — manga → shōnen, tintin → ligne claire, etc." },
  { id: "davinci", label: "Académique (De Vinci)", hint: "7,5–8 têtes, canon de Vitruve : envergure = taille, visage en tiers égaux." },
  { id: "cine", label: "Cinéma réaliste", hint: "≈7,5 têtes, anatomie naturelle, visages de casting réel." },
  { id: "manga_shonen", label: "Manga shōnen", hint: "6,5–7 têtes (ados ≈6), grands yeux placés bas, petit nez, menton pointu." },
  { id: "manga_shojo", label: "Manga shōjo (élancé)", hint: "7–8 têtes très élancées, yeux immenses et lumineux, membres fins." },
  { id: "chibi", label: "Chibi / SD", hint: "2,5–3 têtes, tête et yeux surdimensionnés, mains minuscules." },
  { id: "ligne_claire", label: "Ligne claire (Hergé/Schuiten)", hint: "Corps RÉALISTES ≈7 têtes sous un visage simplifié : yeux-points, trait uniforme, aplats." },
  { id: "gros_nez", label: "Comique franco-belge (gros nez)", hint: "4–5,5 têtes (Astérix, Gaston, Gotlib) : gros nez rond, membres élastiques, gros souliers." },
  { id: "bd_realiste", label: "BD réaliste (Moebius)", hint: "≈8 têtes élégantes et élancées (Moebius/Jodorowsky), trait fin, hachures." },
  { id: "comics_heroic", label: "Comics héroïque (DC/Marvel)", hint: "8,5–9 têtes, épaules de 3 têtes de large, torse en V, musculature dessinée." },
  { id: "vitrail", label: "Vitrail Młoda Polska", hint: "Figure monumentale frontale 7–8 têtes, visage aux contours forts et sereins, espace décoratif APLATI (plomb + verre, pas de perspective profonde)." },
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
    box.innerHTML = `<div class="empty-note">Importe un manuscrit (📚) ou clique ✨ — l'agent proposera 4 directions motivées par le texte.</div>`;
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
        ? "⚠ Ce générateur n'a pas de seeds : la recette 🔁 conserve les prompts et le chaînage d'image, mais pas la réplique au pixel (FLUX seul le garantit)."
        : "Seeds disponibles — recettes 🔁 rejouables à l'identique.";
    };
    $("#daProvider").addEventListener("change", upd); upd();
  } catch (e) { $("#daProvider").innerHTML = `<option value="flux">FLUX (fal)</option>`; }
  $("#daRefName").textContent = daSettings.style_ref_image || "aucune";
  $("#daModal").classList.remove("hidden");
}

async function daApply() {
  try {
    await api.send("PUT", "/atelier/settings", {
      global_style: $("#daStyle").value.trim(),
      image_provider: $("#daProvider").value,
      style_canon: $("#daCanon").value,
      style_ref_image: $("#daRefName").textContent === "aucune"
        ? "" : $("#daRefName").textContent,
    });
    $("#globalStyle").value = $("#daStyle").value.trim();
    $("#daModal").classList.add("hidden");
    toast("🎨 Direction artistique appliquée — toutes les prochaines planches l'utilisent.");
  } catch (e) { toast("DA : " + e.message, true); }
}

async function daPropose() {
  toast("✨ L'agent relit le manuscrit… (~15 s)");
  try {
    const d = await api.send("POST", "/atelier/style/propose", {});
    daRenderProposals(d.proposals);
    toast(`✨ ${d.proposals.length} directions proposées — clique pour en choisir une.`);
  } catch (e) { toast("Proposition DA : " + e.message, true); }
}

/* ═════════ éléments vectoriels du chapitre (Vectorlab, phases 0+6) ═════════ */
const VECTOR_ROLES = { decor: "Décor", lumiere: "Lumière",
                       personnage: "Personnage", libre: "Libre" };

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
      `<div class="empty-note">Vectorlab injoignable : ${esc(e.message)}</div>`;
    return;
  }
  vectorDocsChapitre = docs;
  $("#vectorList").innerHTML = docs.length ? docs.map(d => `
    <div class="vector-row">
      ${vectorVignette(d)}
      <span class="vector-role">${esc(VECTOR_ROLES[d.role] || d.role)}</span>
      <b>${esc(d.name)}</b> <span class="vector-v">v${d.version}</span>
      ${d.liaison ? `<span class="vector-ref" title="Instancié par référence —
        l'édition du document se voit dans tous les chapitres qui le
        référencent. Dupliquer pour diverger.">réf</span>` : ""}
      <span class="vector-actions">
        <a class="btn" href="/vectorlab/?doc=${encodeURIComponent(d.id)}"
           target="_blank" title="Ouvrir dans l'éditeur vectoriel">Ouvrir</a>
        ${d.liaison ? `
        <button class="btn" data-vdup="${d.id}"
          title="Créer une copie indépendante pour ce chapitre (remplace la référence)">Dupliquer</button>
        <button class="btn" data-vret="${d.id}"
          title="Retirer la référence de ce chapitre (le document n'est pas supprimé)">Retirer</button>` : ""}
      </span>
    </div>`).join("")
    : `<div class="empty-note">Aucun élément vectoriel — crée un décor, une
       lumière ou un personnage, ou instancie depuis la bibliothèque.</div>`;
  loadVectorBiblio();          // le tiroir, s'il est ouvert, suit
}

async function vectorCreer(role) {
  if (!chapter) { toast("Ouvre d'abord un chapitre.", true); return; }
  const nom = await window.__dzDialogue.saisir(`Nom du nouvel élément (${VECTOR_ROLES[role]}) :`,
                     { valeur: `${VECTOR_ROLES[role]} — ${chapter.title || "chapitre"}`, ok: "Créer" });
  if (!nom) return;
  try {
    const d = await api.send("POST", "/vector/docs", {
      name: nom, role, chapter_id: chapter.id,
      doc: docVectorielVierge(nom) });
    await loadVectorDocs();
    window.open(`/vectorlab/?doc=${encodeURIComponent(d.id)}`, "_blank");
  } catch (e) { toast("Vectorlab : " + e.message, true); }
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
      `<div class="empty-note">Bibliothèque injoignable : ${esc(e.message)}</div>`;
    return;
  }
  // hors du chapitre courant : ni propres, ni déjà instanciés
  const deja = new Set(vectorDocsChapitre.map(d => d.id));
  docs = docs.filter(d => !deja.has(d.id));
  $("#vbListe").innerHTML = docs.length ? docs.map(d => `
    <div class="vector-row">
      ${vectorVignette(d)}
      <span class="vector-orig" title="${d.chapter_id
        ? "Document propre à un autre chapitre"
        : "Document de la bibliothèque globale (sans chapitre)"}">${
        d.chapter_id ? "⚓" : "◇"}</span>
      <span class="vector-role">${esc(VECTOR_ROLES[d.role] || d.role)}</span>
      <b>${esc(d.name)}</b> <span class="vector-v">v${d.version}</span>
      <span class="vector-actions">
        <button class="btn" data-vinst="${d.id}"
          title="Instancier par référence dans ce chapitre — l'édition du document se verra ici aussi">Instancier</button>
        <a class="btn" href="/vectorlab/?doc=${encodeURIComponent(d.id)}"
           target="_blank" title="Ouvrir dans l'éditeur vectoriel">Ouvrir</a>
      </span>
    </div>`).join("")
    : `<div class="empty-note">Rien à instancier${
        q || role ? " avec ces filtres" : ""}.</div>`;
}

async function vectorInstancier(docId) {
  try {
    await api.send("POST", "/vector/links",
                   { chapter_id: chapter.id, doc_id: docId });
    await loadVectorDocs();
    toast("Instancié par référence — l'édition du document se verra ici.");
  } catch (e) { toast("Instancier : " + e.message, true); }
}

async function vectorRetirer(docId) {
  try {
    await api.send("DELETE", "/vector/links?chapter_id="
      + encodeURIComponent(chapter.id)
      + "&doc_id=" + encodeURIComponent(docId));
    await loadVectorDocs();
    toast("Référence retirée — le document existe toujours.");
  } catch (e) { toast("Retirer : " + e.message, true); }
}

async function vectorDupliquer(docId) {
  const src = vectorDocsChapitre.find(d => d.id === docId);
  const nom = await window.__dzDialogue.saisir("Nom de la copie indépendante :",
                     { valeur: `${(src && src.name) || "Élément"} (copie)`, ok: "Dupliquer" });
  if (!nom) return;
  try {
    await api.send("POST",
      `/vector/docs/${encodeURIComponent(docId)}/duplicate`,
      { chapter_id: chapter.id, name: nom });
    await loadVectorDocs();
    toast("Copie indépendante créée — la référence est remplacée.");
  } catch (e) { toast("Dupliquer : " + e.message, true); }
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
    $("#styleSaved").textContent = "✓"; $("#styleSaved").className = "savestate saved";
  } catch (e) { $("#styleSaved").textContent = "!"; toast("Style global : " + e.message, true); }
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

/* ═════════ tâche #61 (plan chapitres P2) — versions du texte ═════════
   Le tiroir liste les instantanés du chapitre, de son scénario et de ses scènes ; le côte à côte compare l'instantané
   au texte courant ; « Restaurer » garde d'abord le courant (côté serveur) ; un scénario se copie (ses scènes ont été
   supprimées : il ne se restaure pas en scènes). */
const PASSE_LABEL = { manuelle: "édition", adaptation: "adaptation", suppression: "scénario supprimé", import: "ré-import",
                      telephone: "retour du téléphone", reecriture: "réécriture", restauration: "retour arrière",
                      import_scenario: "scénario importé" };
const KIND_VER = { chapter: "texte", scenario: "scénario", scene: "scène" };

function openVersions() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  $("#verModal").classList.remove("hidden");
  $("#verDiff").innerHTML = `<div class="empty-note">Choisis une version à gauche.</div>`;
  const list = $("#verList");
  list.innerHTML = "…";
  api.get(`/chapters/${encodeURIComponent(chapter.id)}/versions`).then(({ versions }) => {
    $("#verNote").textContent = `${versions.length} instantané(s) — « ${chapter.title} »`;
    if (!versions.length) {
      list.innerHTML = `<div class="empty-note">Aucun instantané : rien n'a encore été écrasé sur ce chapitre.</div>`;
      return;
    }
    list.innerHTML = versions.map(v => `
      <div class="ver-item" data-id="${escA(v.id)}" title="Comparer cet instantané au texte courant">
        <div class="ver-line"><b>${KIND_VER[v.kind] || v.kind} v${v.n}</b> · ${esc(PASSE_LABEL[v.passe] || v.passe)}
          <span class="ver-size">${v.taille} car.</span></div>
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
      ? `<button id="verRestore" class="btn primary" title="Réécrit avec cette version — le texte courant est gardé en instantané avant">↩ Restaurer</button>`
      : `<button id="verCopier" class="btn" title="Un scénario gardé ne se restaure pas en scènes : copiez son texte">⧉ Copier le texte</button>`;
    box.innerHTML = `
      <div class="ver-diff-head">
        <span>${KIND_VER[d.version.kind] || ""} v${d.version.n} · ${esc(PASSE_LABEL[d.version.passe] || d.version.passe)}</span>
        <span class="ver-counts">+${d.ajoutees} / −${d.supprimees} · ${d.identiques} inchangée(s)</span>
        ${action}
      </div>
      <div class="ver-cols">
        <div class="ver-col"><header>instantané</header>${col("a")}</div>
        <div class="ver-col"><header>texte courant</header>${col("b")}</div>
      </div>`;
    const copier = $("#verCopier");
    if (copier) copier.addEventListener("click", async () => {
      try { const v = await api.get(`/versions/${encodeURIComponent(vid)}`); await navigator.clipboard.writeText(v.text); toast("Texte copié."); }
      catch (e) { toast("Copie impossible : " + e.message, true); }
    });
    const rest = $("#verRestore");
    if (rest) rest.addEventListener("click", async () => {
      if (!await window.__dzDialogue.confirmer("Restaurer cette version ? Le texte courant est gardé en instantané.", { ok: "Restaurer" })) return;
      clearTimeout(saveTimer);                       // une sauvegarde en attente n'écrasera pas le texte restauré
      try {
        await api.send("POST", `/versions/${encodeURIComponent(vid)}/restore`);
        $("#verModal").classList.add("hidden");
        await openChapter(chapter.id);               // texte ET surlignage recalculés par le serveur
        if (mode === "screenplay") await loadScenes(true);
        toast("Version restaurée — le texte précédent est dans l'historique.");
      } catch (e) { toast("Restauration impossible : " + e.message, true); }
    });
  } catch (e) { box.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; }
}

/* ═════════ tâche #60 (plan chapitres P1) — plan ↔ entités, apparitions ═════════ */
function entPicker(selected) {
  const sel = new Set(selected || []);
  return `<details class="shot-ents-edit"><summary title="Cocher les entités présentes dans ce plan">⛓ entités du plan</summary>
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
    box.innerHTML = `<div class="apps-total">${t.chapters} chapitre(s) · ${t.mentions} mention(s) · ${t.shots} plan(s) · ${t.scenes} scène(s)</div>` +
      (a.chapters.map(c => `<div class="apps-ch"><b>${esc(c.title)}</b> — ${c.mentions} mention(s)
        ${c.shots.map(s => `<button class="btn ghost apps-shot" data-ch="${escA(c.chapter_id)}" data-shot="${escA(s.id)}" title="${escA(s.action)}">PLAN ${s.idx + 1}</button>`).join("")}
        ${c.scenes.map(s => `<button class="btn ghost apps-scene" data-ch="${escA(c.chapter_id)}" title="${escA(s.slugline)}">SC. ${s.idx + 1}</button>`).join("")}</div>`).join("")
       || `<div class="empty-note">Aucune apparition — découpe un chapitre (🎬 ou ¶) ou lie l'entité à un plan.</div>`);
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
    const ch = await api.send("POST", "/chapters", { title: "Nouveau chapitre", series: $("#chapterSeries").value });
    await loadChapters(ch.id);
  });
  $("#chapterSelect").addEventListener("change", e => e.target.value && openChapter(e.target.value));
  $("#deleteChapter").addEventListener("click", async () => {
    if (!chapter || !await window.__dzDialogue.confirmer(`Supprimer le chapitre « ${chapter.title} » ?`)) return;
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
    if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
    await api.send("POST", `/chapters/${chapter.id}/shots`, {});
    await loadShots(true);
  });

  // bible
  document.querySelectorAll(".bible-pane .tab").forEach(t =>
    t.addEventListener("click", () => { setTab(t.dataset.kind); renderBible(); }));
  $("#addEntity").addEventListener("click", async () => {
    const name = await window.__dzDialogue.saisir(`Nom du nouveau ${KIND_LABEL[curKind].toLowerCase()} :`, { ok: "Créer" });
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
  $("#daRefClear").addEventListener("click", () => { $("#daRefName").textContent = "aucune"; });

  // resets (storyboard + scénario)
  $("#boardReset").addEventListener("click", async () => {
    if (!chapter || !shots.length) { toast("Rien à réinitialiser.", true); return; }
    if (!await window.__dzDialogue.confirmer(`Supprimer les ${shots.length} plans de ce storyboard ?`)) return;
    await api.send("DELETE", `/chapters/${chapter.id}/shots`);
    await loadShots(true);
    toast("Storyboard réinitialisé — 🎬 Découper pour en régénérer un.");
  });
  document.querySelectorAll("[data-export]").forEach(b => b.addEventListener("click", () => telechargerExport(b.dataset.export)));
  $("#spImportFile").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    await importerScenario(f);
  });
  $("#spReset").addEventListener("click", async () => {
    if (!chapter || !scenes.length) { toast("Rien à réinitialiser.", true); return; }
    if (!await window.__dzDialogue.confirmer(`Supprimer les ${scenes.length} scènes du scénario ? (le manuscrit reste intact)`)) return;
    await api.send("DELETE", `/chapters/${chapter.id}/scenes`);
    await loadScenes(true);
    toast("Scénario réinitialisé — 🎭 Adapter pour en régénérer un.");
  });

  // lecture du scénario assemblé (le .fountain est un simple fichier texte —
  // ce viewer intégré évite d'avoir besoin d'un logiciel externe)
  $("#spPreview").addEventListener("click", async () => {
    if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
    try {
      const d = await api.get(`/chapters/${chapter.id}/screenplay`);
      if (!d.scene_count) { toast("Pas encore de scénario — 🎭 Adapter d'abord.", true); return; }
      $("#spTitle").textContent = `Scénario — ${d.title} (${d.scene_count} scènes)`;
      $("#spText").textContent = d.fountain;
      $("#spModal").classList.remove("hidden");
    } catch (e) { toast("Lecture : " + e.message, true); }
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
    toast("Import du fichier…");
    try {
      const fd = new FormData(); fd.append("file", f);
      const r = await fetch("/api/images/upload", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || !d.filename) throw new Error(d.detail || "upload échoué");
      $("#libModal").classList.add("hidden");
      await libOnPick(d.filename);
    } catch (err) { toast("Import échoué : " + err.message, true); }
    e.target.value = "";
  });
  $("#libUrl").addEventListener("click", async () => {
    if (!libOnPick) return;
    const url = await window.__dzDialogue.saisir("URL de l'image (http…) :", { placeholder: "https://…", ok: "Télécharger" });
    if (!url || !url.trim()) return;
    toast("Téléchargement de l'image…");
    try {
      const d = await api.send("POST", "/images/fetch", { url: url.trim() });
      if (!d.filename) throw new Error("réponse sans fichier");
      $("#libModal").classList.add("hidden");
      await libOnPick(d.filename);
    } catch (err) { toast("Import URL échoué : " + err.message, true); }
  });

  // boot
  try {
    await loadGlobalStyle();
    await loadEntities();
    // t127 : `?chapter=<id>` rouvre ce chapitre (le retour du Plateau 3D) ; inconnu → le premier, comme avant
    await loadChapters(new URLSearchParams(location.search).get("chapter") || undefined);
    await renderBible();
  } catch (e) { toast("Chargement initial échoué : " + e.message, true); }
});
