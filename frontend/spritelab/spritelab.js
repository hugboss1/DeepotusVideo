/* Sprite Lab — Game Assets 2D (chantier 9c).
   Vanilla JS, même API que l'app (même origine), même gabarit que /atelier.
   Chaîne : source (image animée Seedance / render / upload) → sonde
   d'extraction (extract_only, locale et gratuite) → filmstrip à toggles →
   génération du sheet (keep = frames gardées) → préviz animée + exports. */
"use strict";

const $ = (s) => document.querySelector(s);
/* t149 (traduction L9) : passe unique au chargement, en anglais seulement — (1) les <option> fixes de la page
   (la surcouche n'entre pas dans <select>) ; (2) les textes de la page saisis en « contexte » (sens propre au
   lab, la surcouche les ignore) : texte exact d'un nœud ou d'un title/placeholder -> dzT(clé), clés de cette
   page seulement. */
(function () {
  if (typeof document === "undefined" || typeof dzLang !== "function" || dzLang() !== "en") return;
  const tr = window.__dzI18n && window.__dzI18n.traduire;
  if (tr) for (const o of document.querySelectorAll("select option")) { const t = tr(o.textContent); if (t) o.textContent = t; }
  if (tr) for (const im of document.querySelectorAll("img[alt]")) { const t = tr(im.alt); if (t) im.alt = t; }   // alt : hors surcouche
  const D = window.DZ_I18N || {}, idx = {}, nrm = (s) => String(s).replace(/\s+/g, " ").trim();
  for (const k in D) if (k.startsWith("sprites.sph_") && D[k] && D[k].contexte) idx[nrm(D[k].fr)] = k;
  // la surcouche a pu passer AVANT : le texte qu'elle a posé (« Plateau » -> Board du Vectorlab) est reconnu aussi
  if (tr) for (const f of Object.keys(idx)) { const e = tr(f); if (e && !idx[nrm(e)]) idx[nrm(e)] = idx[f]; }
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let x = w.nextNode(); x; x = w.nextNode()) {
    const k = idx[nrm(x.nodeValue)];
    if (k) x.nodeValue = x.nodeValue.match(/^\s*/)[0] + dzT(k) + x.nodeValue.match(/\s*$/)[0];
  }
  for (const el of document.querySelectorAll("[title],[placeholder]")) for (const a of ["title", "placeholder"]) {
    const v = el.getAttribute(a), k = v && idx[nrm(v)];
    if (k) el.setAttribute(a, dzT(k));
  }
})();
const $$ = (s) => [...document.querySelectorAll(s)];
const api = {
  async get(p) { const r = await fetch("/api" + p); if (!r.ok) throw new Error(await r.text()); return r.json(); },
  async send(m, p, body) {
    const r = await fetch("/api" + p, { method: m, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    return d;
  },
};

/* t111 : directions.js (module pur, sourceBody compris) arrive APRÈS ce script — ce qui lit la source l'attend */
const SLD_PRET = window.SLD ? Promise.resolve() : new Promise((r) => document.addEventListener("sld-pret", r, { once: true }));

/* Preset sprite (spec 9c) : caméra fixe + fond uni -> détourage propre. */
const SPRITE_SUFFIX = "static camera, character animation loop, plain solid green background, full body visible";
const VIDEO_RE = /\.(mp4|mov|webm|m4v|avi|mkv|gif)$/i;

/* ───────── état ───────── */
let source = null;         // {kind:"job", job_id, label}
let libImages = [];        // Library images [{filename,...}]
let selImage = null;       // filename choisi (onglet Image)
let renders = [];          // jobs vidéo terminés
let extractJob = null;     // uuid du job-sonde d'extraction courant
let extractShort = null;   // 8 hex -> /api/assets/sprite/{short}/frame/{i}
let extractedAt = null;    // {fps, max} au moment de la sonde
let stripN = 0;            // frames extraites
let stripState = [];       // true = frame gardée
let lastClicked = 0;       // ancre du shift-clic
let busyExtract = false, busyGen = false, busyAnim = false;
let sheet = null;          // {short, manifest} du dernier sheet
let sheetRev = 0;          // T110 : le réassemblage réécrit frames/NNN.png sous la MÊME URL — la révision casse le cache
let savedSheet = null;     // {short, filename} du dernier Save to Library
let prefsTimer = null, extractTimer = null;

/* ───────── toast ───────── */
let toastTimer = null;
function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg; t.classList.toggle("err", !!err); t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 4200);
}
/* icônes G5 : une réussite = le texte, l'icône dz-etat-succes (ancienne coche), puis la suite du message */
function toastOk(avant, apres) {
  toast("");
  $("#toast").innerHTML = esc(avant) + " " + dzIcone("dz-etat-succes", { taille: 16 }) + esc(apres || "");
}
/* icônes G5 : le bouton lecture / pause montre l'action disponible */
function playIcone() {
  $("#playBtn").innerHTML = player.playing ? dzIcone("dz-media-pause", { taille: 16 }) : dzIcone("dz-media-lecture", { taille: 16 });
}
function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

/* ───────── statuts + progression ───────── */
function setStatus(el, msg, err, pct) {
  el.classList.remove("hidden"); el.classList.toggle("err", !!err);
  el.innerHTML = esc(msg) + (pct != null
    ? `<div class="progress"><i style="width:${Math.max(2, pct)}%"></i></div>` : "");
}
function clearStatus(el) { el.classList.add("hidden"); el.innerHTML = ""; }

/* Poll d'un job jusqu'à done/failed. cb(j) à chaque tick. */
async function pollJob(uuid, cb, timeoutMs) {
  const t0 = Date.now();
  for (;;) {
    const j = await api.get("/jobs/" + uuid);
    if (cb) cb(j);
    if (j.status === "done" || j.status === "failed") return j;
    if (Date.now() - t0 > (timeoutMs || 15 * 60 * 1000)) throw new Error(__dzT9("sprites.sp1_x.delai", "délai dépassé"));
    await new Promise(r => setTimeout(r, 1200));
  }
}

/* ───────── préférences (atelier_settings.spritelab_prefs) ───────── */
const PREF_IDS = ["fps", "maxFrames", "removeBg", "trim", "cellSize", "cellAlign",
  "columns", "pixTarget", "pixPalette", "pixColors", "pixDither",
  "animDur", "animRatio", "pfps", "pzoom", "pbg", "animMs",
  "poWidth", "poColor", "poDx", "poDy", "poOpacity"];
function collectPrefs() {
  const p = { pixelOn: $("#pixelOn").checked,
              postOn: $("#postOn").checked, poOrphans: $("#poOrphans").checked, poSmooth: $("#poSmooth").checked };
  for (const id of PREF_IDS) p[id] = $("#" + id).value;
  p.tagRows = JSON.stringify(tagRows);
  return p;
}
function applyPrefs(p) {
  if (!p || typeof p !== "object") return;
  for (const id of PREF_IDS) if (p[id] != null && $("#" + id)) $("#" + id).value = p[id];
  if (p.pixelOn != null) $("#pixelOn").checked = !!p.pixelOn;
  for (const k of ["postOn", "poOrphans", "poSmooth"]) if (p[k] != null) $("#" + k).checked = !!p[k];
  if (p.tagRows) { try { tagRows = JSON.parse(p.tagRows) || []; } catch (e) { tagRows = []; } }
  if (!Array.isArray(tagRows)) tagRows = [];
  renderTags();
  syncPixelSet(); syncPostSet(); $("#pfpsVal").textContent = $("#pfps").value;
}
function savePrefs() {
  clearTimeout(prefsTimer);
  prefsTimer = setTimeout(() => {
    api.send("PUT", "/atelier/settings",
      { spritelab_prefs: JSON.stringify(collectPrefs()) }).catch(() => {});
  }, 900);
}
async function loadPrefs() {
  try {
    const d = await api.get("/atelier/settings");
    const raw = d.settings && d.settings.spritelab_prefs;
    if (raw) applyPrefs(JSON.parse(raw));
  } catch (e) { /* défauts du HTML */ }
}

/* ───────── source ───────── */
function setSource(src) {
  source = src;
  const chip = $("#srcChip");
  chip.textContent = src ? __dzT9("sprites.sp1_src.source", "Source : {label}", { label: src.label }) : __dzT9("sprites.sp1_src.aucune", "aucune source");
  chip.classList.toggle("set", !!src);
  updateGenEnabled();
  if (src) extract();                     // sonde locale gratuite -> filmstrip
}

/* — onglet Image : Library + Animer — */
async function loadImages() {
  try {
    libImages = (await api.get("/images")).images || [];
    renderImgGrid(); renderFeuilleGrid();
  } catch (e) {
    $("#imgGrid").innerHTML = `<div class="empty-note">${__dzT9("sprites.sp1_img.lib_indispo", "Library indisponible : {err}", { err: esc(e.message) })}</div>`;
  }
}
function renderImgGrid() {
  const q = ($("#imgSearch").value || "").toLowerCase();
  const list = libImages.filter(im => !q || im.filename.toLowerCase().includes(q));
  const g = $("#imgGrid");
  g.innerHTML = list.slice(0, 120).map(im =>
    `<img loading="lazy" data-fn="${esc(im.filename)}" title="${esc(im.filename)}"
          src="/api/images/${encodeURIComponent(im.filename)}"
          class="${im.filename === selImage ? "sel" : ""}">`).join("")
    || `<div class="empty-note">${q ? __dzT9("sprites.sp1_img.aucune_q", "Aucune image pour « {q} ».", { q: esc(q) }) : __dzT9("sprites.sp1_img.aucune_lib", "Aucune image dans la Library.")}</div>`;
  g.querySelectorAll("img").forEach(el => el.onclick = () => {
    selImage = el.dataset.fn;
    g.querySelectorAll("img").forEach(x => x.classList.toggle("sel", x === el));
  });
}

async function animer() {
  if (busyAnim) return;
  if (!selImage) return toast(__dzT9("sprites.sp1_anim.choisis_image", "Choisis d'abord une image de la Library."), true);
  const action = ($("#animPrompt").value || "").trim();
  if (!action) return toast(__dzT9("sprites.sp1_anim.decris", "Décris l'action à animer (ex : walks in place)."), true);
  busyAnim = true; $("#animerBtn").disabled = true;
  const st = $("#animStatus");
  try {
    setStatus(st, __dzT9("sprites.sp1_anim.lancement", "Lancement Seedance…"), false, 3);
    const before = new Set((await api.get("/jobs?limit=15")).map(j => j.job_id));
    await api.send("POST", "/generate", {
      image_filename: selImage,
      custom_prompt: action + ", " + SPRITE_SUFFIX,
      prompt_source: "custom",
      voiceover_enabled: false,
      duration_s: parseInt($("#animDur").value, 10) || 5,
      aspect_ratio: $("#animRatio").value,
      resolution: "720p",
    });
    /* /generate répond "pending" : on repère le nouveau job dans la file. */
    let job = null;
    for (let i = 0; i < 20 && !job; i++) {
      await new Promise(r => setTimeout(r, 1500));
      const js = await api.get("/jobs?limit=15");
      const fresh = js.filter(j => !before.has(j.job_id) && j.provider !== "sprite2d");
      job = fresh.find(j => j.image_filename === selImage) || fresh[0] || null;
    }
    if (!job) throw new Error(__dzT9("sprites.sp1_anim.job_introuvable", "job Seedance introuvable dans la file"));
    const j = await pollJob(job.job_id, jj => setStatus(st,
      __dzT9("sprites.sp1_anim.etape", "Seedance : {etape}…", { etape: jj.current_step || jj.status }), false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || __dzT9("sprites.sp1_x.gen_echouee", "génération échouée"));
    clearStatus(st);
    toast(__dzT9("sprites.sp1_anim.prete", "Animation prête — extraction des frames…"));
    setSource({ kind: "job", job_id: j.job_id, label: j.title || ("render " + j.job_id.slice(0, 8)) });
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp1_x.echec", "Échec : {err}", { err: e.message }), true);
    toast(__dzT9("sprites.sp1_anim.echoue", "Animer a échoué : {err}", { err: e.message }), true);
  }
  busyAnim = false; $("#animerBtn").disabled = false;
}

/* — onglet Render : jobs vidéo existants — */
async function loadRenders() {
  try {
    const js = await api.get("/jobs?limit=100");
    renders = js.filter(j => j.status === "done"
      && j.provider !== "sprite2d" && j.provider !== "asset3d"
      && VIDEO_RE.test(j.final_video_path || j.video_path || ""));
    renderRenderList();
  } catch (e) {
    $("#renderList").innerHTML = `<div class="empty-note">${__dzT9("sprites.sp1_rd.indispo", "Renders indisponibles : {err}", { err: esc(e.message) })}</div>`;
  }
}
function renderRenderList() {
  const q = ($("#renderSearch").value || "").toLowerCase();
  const list = renders.filter(j =>
    !q || (j.title || "").toLowerCase().includes(q) || j.job_id.startsWith(q));
  $("#renderList").innerHTML = list.slice(0, 80).map(j => {
    const d = (j.created_at || "").slice(0, 16).replace("T", " ");
    return `<div class="render-item ${source && source.job_id === j.job_id ? "sel" : ""}" data-id="${j.job_id}">
      <div class="rt">${esc(j.title || j.image_filename || j.job_id.slice(0, 8))}</div>
      <div class="rm">${d}${j.duration_s ? " · " + j.duration_s + " s" : ""}${j.provider ? " · " + esc(j.provider) : ""}</div>
    </div>`;
  }).join("") || `<div class="empty-note">${__dzT9("sprites.sp1_rd.aucun", "Aucun render vidéo terminé.")}</div>`;
  $$("#renderList .render-item").forEach(el => el.onclick = () => {
    const j = renders.find(x => x.job_id === el.dataset.id);
    if (!j) return;
    $$("#renderList .render-item").forEach(x => x.classList.toggle("sel", x === el));
    setSource({ kind: "job", job_id: j.job_id, label: j.title || ("render " + j.job_id.slice(0, 8)) });
  });
}

/* — onglet Vidéo : upload — */
async function uploadVideo(file) {
  const st = $("#upStatus");
  try {
    setStatus(st, __dzT9("sprites.sp1_vid.envoi", "Envoi de {nom}…", { nom: file.name }), false, 30);
    const fd = new FormData(); fd.append("file", file);
    const r = await fetch("/api/videos/upload", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    setStatus(st, __dzT9("sprites.sp1_vid.importee", "Importée : {nom} ({d} s)", { nom: d.filename, d: d.duration_s || "?" }));
    setSource({ kind: "job", job_id: d.job_id, label: d.filename });
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp1_x.echec", "Échec : {err}", { err: e.message }), true);
    toast(__dzT9("sprites.sp1_vid.echoue", "Upload échoué : {err}", { err: e.message }), true);
  }
}

/* ───────── filmstrip (sonde extract_only) ───────── */
function stripSettings() {
  return { fps: parseInt($("#fps").value, 10) || 8,
           max: parseInt($("#maxFrames").value, 10) || 16 };
}
function stripStale() {
  const s = stripSettings();
  return !extractedAt || extractedAt.fps !== s.fps || extractedAt.max !== s.max;
}

async function extract() {
  if (!source || busyExtract) return;
  busyExtract = true; $("#extractBtn").disabled = true; updateGenEnabled();
  const { fps, max } = stripSettings();
  $("#strip").innerHTML = `<div class="empty-note">${__dzT9("sprites.sp1_strip.extraction", "Extraction des frames… (locale, gratuite)")}</div>`;
  $("#stripCount").textContent = "…";
  try {
    await SLD_PRET;
    const d = await api.send("POST", "/assets/sprite", {
      source: window.SLD.sourceBody(source),
      fps_sample: fps, max_frames: max,
      remove_bg: "none", extract_only: true,
      title: "Sprites · extraction " + (source.label || ""),
    });
    const j = await pollJob(d.job_id, null, 5 * 60 * 1000);
    if (j.status !== "done") throw new Error(j.error || __dzT9("sprites.sp1_strip.extr_echouee", "extraction échouée"));
    if (extractJob && extractJob !== d.job_id)      // la sonde précédente + ses
      api.send("DELETE", "/jobs/" + extractJob).catch(() => {}); // fichiers
    extractJob = d.job_id; extractShort = d.job_id.slice(0, 8);
    extractedAt = { fps, max };
    const m = await api.get("/assets/sprite/" + extractShort + "/manifest");
    stripN = m.frames.length;
    stripState = m.frames.map(() => true); lastClicked = 0;
    renderStrip();
  } catch (e) {
    $("#strip").innerHTML = `<div class="empty-note">${__dzT9("sprites.sp1_strip.echec_extr", "Extraction échouée : {err}", { err: esc(e.message) })}</div>`;
    $("#stripCount").textContent = "—";
    toast(__dzT9("sprites.sp1_strip.echec_extr", "Extraction échouée : {err}", { err: e.message }), true);
  }
  busyExtract = false; $("#extractBtn").disabled = false; updateGenEnabled();
}

function renderStrip() {
  $("#strip").innerHTML = Array.from({ length: stripN }, (_, i) =>
    `<div class="frame ${stripState[i] ? "" : "off"}" data-i="${i}" title="${__dzT9("sprites.sp1_strip.frame_titre", "frame {i} — clic : garder/enlever, Shift-clic : plage", { i })}">
       <img loading="lazy" src="/api/assets/sprite/${extractShort}/frame/${i}"><span class="fno">${i}</span><span class="frame-x">${dzIcone("dz-etat-exclu", { taille: 24 })}</span>
     </div>`).join("");
  $$("#strip .frame").forEach(el => el.onclick = (ev) => {
    const i = parseInt(el.dataset.i, 10);
    if (ev.shiftKey) {
      const [a, b] = [Math.min(lastClicked, i), Math.max(lastClicked, i)];
      const v = stripState[lastClicked];               // la plage suit l'ancre
      for (let k = a; k <= b; k++) stripState[k] = v;
    } else { stripState[i] = !stripState[i]; lastClicked = i; }
    $$("#strip .frame").forEach(f =>
      f.classList.toggle("off", !stripState[parseInt(f.dataset.i, 10)]));
    updateStripCount();
  });
  updateStripCount();
}
function keptIndices() { return stripState.flatMap((v, i) => v ? [i] : []); }
function updateStripCount() {
  $("#stripCount").textContent = stripN ? __dzT9("sprites.sp1_strip.gardees", "{n}/{total} gardées", { n: keptIndices().length, total: stripN }) : "—";
  updateCost(); updateGenEnabled();
}

/* ───────── coût estimé (détourage API × frames gardées) ───────── */
async function updateCost() {
  const el = $("#costHint");
  if ($("#removeBg").value !== "api" || !stripN) { el.textContent = ""; return; }
  try {
    const d = await api.send("POST", "/cost/estimate",
      { kind: "sprite2d", frames: keptIndices().length, remove_bg: "api" });
    el.innerHTML = d && d.total_usd != null ? `${dzIcone("dz-action-cout", { taille: 16 })} $${(+d.total_usd).toFixed(3)}` : "";
  } catch (e) { el.textContent = ""; }
}

/* ───────── génération du sheet ───────── */
function updateGenEnabled() {
  $("#genBtn").disabled = !(source && extractShort && !busyGen && !busyExtract);
}

function cellOpts() {
  return { size: $("#cellSize").value === "native" ? "native" : parseInt($("#cellSize").value, 10),
           align: $("#cellAlign").value };
}

function pixelOpts() {
  if (!$("#pixelOn").checked) return undefined;
  const palette = $("#pixPalette").value;
  const o = { target_px: parseInt($("#pixTarget").value, 10) || 64,
              dither: $("#pixDither").value };
  if (palette) o.palette = palette;
  else o.colors = parseInt($("#pixColors").value, 10) || 16;
  return o;
}

/* T110 (plan-sprites T2) — tags d'animation. Les lignes sont l'état ; le corps de la requête est construit à la
   volée, jamais mémorisé en double. Les numéros sont ceux des frames GARDÉES (le serveur renumérote après `keep`). */
let tagRows = [];
const escA = (s) => esc(String(s == null ? "" : s)).replace(/"/g, "&quot;");
function renderTags() {
  const box = $("#tagRows");
  if (!box) return;
  const DIRS = ["forward", "reverse", "pingpong", "pingpong_reverse"];
  box.innerHTML = tagRows.map((t, i) => `
    <div class="tagrow" data-i="${i}">
      <input class="tname" value="${escA(t.name)}" placeholder="idle" maxlength="32" title="${__dzT9("sprites.sp1_tag.nom", "Nom de l'animation (lettres, chiffres, espace, _ ou -)")}">
      <input class="tfrom" type="number" min="0" max="63" value="${parseInt(t.from, 10) || 0}" title="${__dzT9("sprites.sp1_tag.premiere", "Première frame gardée")}">
      <input class="tto" type="number" min="0" max="63" value="${parseInt(t.to, 10) || 0}" title="${__dzT9("sprites.sp1_tag.derniere", "Dernière frame gardée")}">
      <select class="tdir" title="${__dzT9("sprites.sp1_tag.sens", "Sens de lecture")}">
        ${DIRS.map(d => `<option value="${d}"${d === t.direction ? " selected" : ""}>${d}</option>`).join("")}
      </select>
      <button class="del" type="button" title="${__dzT9("sprites.sp1_tag.retirer", "Retirer ce tag")}" aria-label="${__dzT9("sprites.sp1_tag.retirer", "Retirer ce tag")}">${dzIcone("dz-action-retirer", { taille: 16 })}</button>
    </div>`).join("");
  box.querySelectorAll(".tagrow").forEach(row => {
    const i = parseInt(row.dataset.i, 10);
    row.querySelector(".tname").oninput = (e) => { tagRows[i].name = e.target.value; savePrefs(); };
    row.querySelector(".tfrom").onchange = (e) => { tagRows[i].from = parseInt(e.target.value, 10) || 0; savePrefs(); };
    row.querySelector(".tto").onchange = (e) => { tagRows[i].to = parseInt(e.target.value, 10) || 0; savePrefs(); };
    row.querySelector(".tdir").onchange = (e) => { tagRows[i].direction = e.target.value; savePrefs(); };
    row.querySelector(".del").onclick = () => { tagRows.splice(i, 1); renderTags(); savePrefs(); };
  });
}
function animOpts(nFrames) {
  const ms = Math.max(10, Math.min(10000, parseInt($("#animMs").value, 10) || 125));
  const tags = tagRows
    .filter(t => (t.name || "").trim())
    .map(t => ({ name: t.name.trim(), from: t.from, to: t.to, direction: t.direction || "forward" }));
  return { tags, durations: new Array(nFrames).fill(ms) };
}

async function generate() {
  if (busyGen || !source || !extractShort) return;
  if (stripStale()) {
    toast(__dzT9("sprites.sp1_gen.reextraites", "Réglages fps/max modifiés — frames ré-extraites. Vérifie ta sélection puis relance."), true);
    return extract();
  }
  const kept = keptIndices();
  if (!kept.length) return toast(__dzT9("sprites.sp1_gen.au_moins_une", "Garde au moins une frame dans le filmstrip."), true);
  busyGen = true; updateGenEnabled();
  const st = $("#genStatus");
  try {
    const s = stripSettings();
    const body = {
      source: window.SLD.sourceBody(source),
      fps_sample: s.fps, max_frames: s.max,
      remove_bg: $("#removeBg").value,
      trim: $("#trim").value,
      cell: cellOpts(),
      columns: $("#columns").value === "auto" ? "auto" : parseInt($("#columns").value, 10),
      title: "Sprites · " + (source.label || ""),
    };
    if (kept.length < stripN) body.keep = kept;
    body.anim = animOpts(kept.length);
    const px = pixelOpts(); if (px) body.pixel = px;
    const po = postOpts(); if (po) body.post = po;

    setStatus(st, __dzT9("sprites.sp1_gen.lance", "Job lancé…"), false, 3);
    const d = await api.send("POST", "/assets/sprite", body);
    const j = await pollJob(d.job_id, jj => setStatus(st,
      `${jj.current_step || jj.status}…`, false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || __dzT9("sprites.sp1_x.gen_echouee", "génération échouée"));
    const short = d.job_id.slice(0, 8);
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    clearStatus(st);
    showResult(short, m);
    toastOk(__dzT9("sprites.sp1_gen.genere", "Sprite sheet généré"));
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp1_x.echec", "Échec : {err}", { err: e.message }), true);
    toast(__dzT9("sprites.sp1_gen.echouee", "Génération échouée : {err}", { err: e.message }), true);
  }
  busyGen = false; updateGenEnabled();
}

/* ───────── préviz + exports ───────── */
const player = { imgs: [], n: 0, playing: true, raf: 0, last: 0, acc: 0, i: 0, dx: 0, dy: 0, flip: false, speed: 1 };   // lot 5 : Playground

function showResult(short, m) {
  sheet = { short, manifest: m };
  sheetRev++;
  $("#outEmpty").classList.add("hidden");
  $("#player").classList.remove("hidden");
  $("#exports").classList.remove("hidden");
  $("#sheetWrap").classList.remove("hidden");
  const g = m.grid || {};
  $("#outInfo").textContent =
    `${g.cols}×${g.rows} · ${g.cell_w}px · ${m.frames.length} frames` +
    (m.pixel ? ` · ${m.pixel.palette || __dzT9("sprites.sp1_out.coul", "{n} coul.", { n: m.pixel.colors })}` : "");
  $("#dlSheet").href = `/api/assets/sprite/${short}/sheet`;
  $("#dlSheet").setAttribute("download", `sprites_${short}.png`);
  $("#dlZip").href = `/api/assets/sprite/${short}/zip`;
  $("#dlZip").setAttribute("download", `sprites_${short}.zip`);
  $("#dlGif").href = `/api/assets/sprite/${short}/preview`;
  $("#dlGif").setAttribute("download", `sprites_${short}.gif`);
  /* T109 : les quatre exports moteur — masqués quand le manifeste dit qu'ils manquent (feuille d'avant T109) */
  $("#dlGodot").href = `/api/assets/sprite/${short}/godot`;
  $("#dlGodot").setAttribute("download", `sprites_${short}.tres`);
  $("#dlAtlas").href = `/api/assets/sprite/${short}/atlas`;
  $("#dlAtlas").setAttribute("download", `sprites_${short}.atlas.json`);
  $("#dlAse").href = `/api/assets/sprite/${short}/aseprite`;
  $("#dlAse").setAttribute("download", `sprites_${short}.ase`);
  $("#dlP2d").href = `/api/assets/sprite/${short}/paper2d`;
  $("#dlP2d").setAttribute("download", `sprites_${short}.paper2dsprites`);
  for (const [id, ok] of [["dlGodot", m.files && m.files.godot],
                          ["dlAtlas", m.files && m.files.atlas],
                          ["dlAse", m.files && m.files.aseprite],
                          ["dlP2d", m.files && m.files.paper2d]])
    $("#" + id).classList.toggle("hidden", !ok);
  $("#sheetImg").src = `/api/assets/sprite/${short}/sheet?t=${Date.now()}`;
  updateStudioBtn();                    // masque « → Studio » si sheet non sauvé
  buildPlayer(short, m);
  editOrder = m.frames.map(f => f.index);
  $("#editor").classList.toggle("hidden", !m.grid);
  $("#editStatus").classList.add("hidden");
  renderEditor();
  hbCharger(short, m);
  skCharger(short, m);
}

/* ───────── T110 (plan-sprites T7) : ordre des images ─────────
   `editOrder` est un tableau d'INDEX de la feuille actuelle : dupliquer, c'est répéter un index ; supprimer, c'est
   l'ôter. Le serveur refait la feuille depuis ses propres cases — la page ne fabrique aucun PNG, rien n'est repayé. */
let editOrder = [];

function renderEditor() {
  if (!sheet) return;
  const short = sheet.short, n = editOrder.length;
  $("#editInfo").textContent = __dzT9("sprites.sp1_ed.images", "{n} image(s)", { n });
  $("#editStrip").innerHTML = editOrder.map((src, k) => `
    <div class="editcell" data-k="${k}">
      <img src="/api/assets/sprite/${short}/frame/${src}?r=${sheetRev}" alt="">
      <div class="no">${k} ← #${src}</div>
      <div class="ops">
        <button data-op="left" title="${__dzT9("sprites.sp1_ed.gauche", "Vers la gauche")}" aria-label="${__dzT9("sprites.sp1_ed.gauche", "Vers la gauche")}"${k === 0 ? " disabled" : ""}>${dzIcone("dz-edit-monter", { taille: 16 })}</button>
        <button data-op="dup" title="${__dzT9("sprites.sp1_ed.dupliquer", "Dupliquer")}" aria-label="${__dzT9("sprites.sp1_ed.dupliquer", "Dupliquer")}"${n >= 64 ? " disabled" : ""}>${dzIcone("dz-action-dupliquer", { taille: 16 })}</button>
        <button data-op="del" title="${__dzT9("sprites.sp1_ed.supprimer", "Supprimer")}" aria-label="${__dzT9("sprites.sp1_ed.supprimer", "Supprimer")}"${n <= 1 ? " disabled" : ""}>${dzIcone("dz-action-retirer", { taille: 16 })}</button>
        <button data-op="right" title="${__dzT9("sprites.sp1_ed.droite", "Vers la droite")}" aria-label="${__dzT9("sprites.sp1_ed.droite", "Vers la droite")}"${k === n - 1 ? " disabled" : ""}>${dzIcone("dz-edit-descendre", { taille: 16 })}</button>
      </div>
    </div>`).join("");
  $("#editStrip").querySelectorAll(".ops button").forEach(b => b.onclick = () => {
    const k = parseInt(b.closest(".editcell").dataset.k, 10);
    const op = b.dataset.op;
    if (op === "left" && k > 0) editOrder.splice(k - 1, 0, editOrder.splice(k, 1)[0]);
    else if (op === "right" && k < editOrder.length - 1) editOrder.splice(k + 1, 0, editOrder.splice(k, 1)[0]);
    else if (op === "dup" && editOrder.length < 64) editOrder.splice(k, 0, editOrder[k]);
    else if (op === "del" && editOrder.length > 1) editOrder.splice(k, 1);
    renderEditor();
  });
}

/* ───────── T112 (spec sorceress, lot « Combat ») : hitboxes par frame ─────────
   L'état et ses gestes vivent dans hitbox.js (pur, banc qa/hitbox.test.mjs) ; ici, le dessin et le câblage. Chaque
   geste s'enregistre tout seul (POST …/hitboxes, local et gratuit) une demi-seconde après : rien ne se perd avant un
   réassemblage, qui les fait suivre leur frame côté serveur. */
let hb = null, hbShort = null, hbImg = null, hbTimer = 0, hbGlisse = null, hbActif = false;

function hbCharger(short, m) {
  if (!window.SLH || !m.grid || !(m.frames || []).length) { $("#hitboxes").classList.add("hidden"); hb = null; return; }
  hb = window.SLH.charger(m);
  hbShort = short;
  const cv = $("#hbCanvas");
  cv.width = hb.cw; cv.height = hb.ch;
  $("#hbFrame").innerHTML = m.frames.map((f, i) => `<option value="${i}">frame ${i}</option>`).join("");
  $("#hitboxes").classList.remove("hidden");
  hbFrame(0);
}

function hbFrame(i) {
  if (!hb) return;
  window.SLH.allerA(hb, i);
  $("#hbFrame").value = String(hb.frame);
  hbImg = new Image();
  hbImg.onload = () => hbDessiner();
  hbImg.src = `/api/assets/sprite/${hbShort}/frame/${hb.frame}?r=${sheetRev}`;
  hbDessiner();
}

function hbDessiner(apercu) {
  if (!hb) return;
  const cv = $("#hbCanvas"), x = cv.getContext("2d");
  x.clearRect(0, 0, cv.width, cv.height);
  if (hbImg && hbImg.complete && hbImg.naturalWidth) x.drawImage(hbImg, 0, 0, cv.width, cv.height);
  const liste = hb.rects[hb.frame].concat(apercu ? [apercu] : []);
  liste.forEach((r, k) => {
    const choisi = k === hb.sel && r !== apercu;
    const coul = r.type === "hurt" ? "rgba(70,170,255," : "rgba(255,70,70,";
    x.fillStyle = coul + "0.25)"; x.fillRect(r.x, r.y, r.w, r.h);
    x.strokeStyle = coul + (choisi ? "1)" : "0.85)");
    x.lineWidth = choisi ? 2 : 1;
    x.strokeRect(r.x + 0.5, r.y + 0.5, r.w - 1, r.h - 1);
  });
  const n = hb.rects.reduce((a, l) => a + l.length, 0);
  $("#hbInfo").textContent = __dzT9("sprites.sp1_hb.info", "frame {f} · {r} rect. · {n} au total", { f: hb.frame, r: hb.rects[hb.frame].length, n });
  hbInspecteur();
}

function hbInspecteur() {
  const r = hb && hb.sel >= 0 ? hb.rects[hb.frame][hb.sel] : null;
  for (const [id, k] of [["hbX", "x"], ["hbY", "y"], ["hbW", "w"], ["hbH", "h"]]) {
    $("#" + id).value = r ? r[k] : ""; $("#" + id).disabled = !r;
  }
  $("#hbSelType").value = r ? r.type : "hit"; $("#hbSelType").disabled = !r; $("#hbDel").disabled = !r;
}

function hbPoint(ev) {
  const cv = $("#hbCanvas"), b = cv.getBoundingClientRect();
  return { x: (ev.clientX - b.left) * cv.width / b.width, y: (ev.clientY - b.top) * cv.height / b.height };
}

function hbChange() {
  hbDessiner();
  clearTimeout(hbTimer);
  hbTimer = setTimeout(hbEnregistrer, 500);
}

async function hbEnregistrer() {
  if (!hb || !hb.sale || !hbShort) return;
  const short = hbShort;
  try {
    const r = await api.send("POST", `/assets/sprite/${short}/hitboxes`, window.SLH.corps(hb));
    if (hbShort === short) hb.sale = false;
    setStatus($("#hbStatus"), __dzT9("sprites.sp1_hb.enregistre", "enregistré · {n} rectangle(s)", { n: r.rectangles }));
  } catch (e) { setStatus($("#hbStatus"), e.message, true); }
}

function hbWire() {
  const cv = $("#hbCanvas");
  cv.addEventListener("pointerdown", (ev) => {
    if (!hb) return;
    hbActif = true;
    const p = hbPoint(ev);
    if (window.SLH.selectionnerSous(hb, p.x, p.y) >= 0) { hbGlisse = null; hbDessiner(); return; }
    hbGlisse = p; cv.setPointerCapture(ev.pointerId);
  });
  cv.addEventListener("pointermove", (ev) => {
    if (!hb || !hbGlisse) return;
    hbDessiner(window.SLH.rectDepuisGlisser(hbGlisse, hbPoint(ev), hb.cw, hb.ch, $("#hbType").value));
  });
  cv.addEventListener("pointerup", (ev) => {
    if (!hb || !hbGlisse) return;
    const r = window.SLH.rectDepuisGlisser(hbGlisse, hbPoint(ev), hb.cw, hb.ch, $("#hbType").value);
    hbGlisse = null;
    if (r && window.SLH.ajouter(hb, r) < 0) toast(__dzT9("sprites.sp1_hb.max", "{n} rectangles au plus par frame", { n: window.SLH.MAX_PAR_FRAME }), true);
    hbChange();
  });
  $("#hbFrame").onchange = () => hbFrame(parseInt($("#hbFrame").value, 10) || 0);
  $("#hbPrev").onclick = () => hb && hbFrame(hb.frame - 1);
  $("#hbNext").onclick = () => hb && hbFrame(hb.frame + 1);
  $("#hbCopy").onclick = () => { if (hb) toast(__dzT9("sprites.sp1_hb.copies", "{n} rectangle(s) copié(s)", { n: window.SLH.copier(hb) })); };
  $("#hbPaste").onclick = () => { if (hb && window.SLH.coller(hb)) hbChange(); };
  $("#hbDel").onclick = () => { if (hb && window.SLH.supprimer(hb)) hbChange(); };
  for (const [id, k] of [["hbX", "x"], ["hbY", "y"], ["hbW", "w"], ["hbH", "h"]])
    $("#" + id).onchange = () => { if (hb && window.SLH.modifier(hb, { [k]: Number($("#" + id).value) })) hbChange(); };
  $("#hbSelType").onchange = () => { if (hb && window.SLH.modifier(hb, { type: $("#hbSelType").value })) hbChange(); };
  /* Ctrl+C / Ctrl+V / Suppr : seulement quand on vient de travailler sur la case, jamais dans un champ — le
     Playground (WASD, flèches, Espace) n'écoute pas ces touches */
  document.addEventListener("pointerdown", (ev) => { if (!ev.target.closest || !ev.target.closest("#hitboxes")) hbActif = false; });
  document.addEventListener("keydown", (ev) => {
    if (!hb || !hbActif || $("#hitboxes").classList.contains("hidden")) return;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || "")) return;
    const k = ev.key.toLowerCase();
    if ((ev.ctrlKey || ev.metaKey) && k === "c") toast(__dzT9("sprites.sp1_hb.copies", "{n} rectangle(s) copié(s)", { n: window.SLH.copier(hb) }));
    else if ((ev.ctrlKey || ev.metaKey) && k === "v") { if (window.SLH.coller(hb)) hbChange(); }
    else if (k === "delete" || k === "backspace") { if (window.SLH.supprimer(hb)) hbChange(); }
    else return;
    ev.preventDefault();
  });
}

/* ───────── t111 (plan-sprites T12) : squelette Spine ─────────
   L'état et ses gestes vivent dans skeleton.js (pur, banc qa/skeleton.test.mjs) ; ici, le dessin et le câblage. La
   page DESSINE os et boîtes en pixels de case ; Python découpe les pièces et écrit skeleton.json (repères locaux de
   Spine). Aucun PNG ni JSON n'est fabriqué ici. Les noms se saisissent dans la liste : aucun dialogue natif. */
let sk = null, skShort = null, skImg = null, skGlisse = null;

function skCharger(short, m) {
  if (!window.SLK || !m.grid || !(m.frames || []).length) { $("#squelette").classList.add("hidden"); sk = null; return; }
  sk = window.SLK.charger(m);
  skShort = short;
  const cv = $("#skCanvas");
  cv.width = sk.cw; cv.height = sk.ch;
  $("#skFrame").innerHTML = m.frames.map((f, i) => `<option value="${i}">frame ${i}</option>`).join("");
  $("#dlSpine").href = `/api/assets/sprite/${short}/skeleton`;
  $("#dlSpine").setAttribute("download", `sprites_${short}.spine.json`);
  $("#dlSpine").classList.toggle("hidden", !(m.files && m.files.spine));
  $("#squelette").classList.remove("hidden");
  $("#skStatus").classList.add("hidden");
  skFrame(0);
}

function skFrame(i) {
  if (!sk) return;
  window.SLK.allerA(sk, i);
  $("#skFrame").value = String(sk.frame);
  skImg = new Image();
  skImg.onload = () => skDessiner();
  skImg.src = `/api/assets/sprite/${skShort}/frame/${sk.frame}?r=${sheetRev}`;
  skDessiner();
}

function skDessiner(apercu) {
  if (!sk) return;
  const cv = $("#skCanvas"), x = cv.getContext("2d");
  x.clearRect(0, 0, cv.width, cv.height);
  if (skImg && skImg.complete && skImg.naturalWidth) { x.imageSmoothingEnabled = false; x.drawImage(skImg, 0, 0, cv.width, cv.height); }
  x.lineWidth = 1;
  for (const p of sk.pieces) {
    x.strokeStyle = p.bone === sk.sel ? "rgba(77,216,230,1)" : "rgba(77,216,230,.55)";
    x.strokeRect(p.x + 0.5, p.y + 0.5, p.w - 1, p.h - 1);
  }
  for (const b of sk.bones) {
    const a = b.rotation * Math.PI / 180, l = Math.max(b.length, 4);
    x.strokeStyle = x.fillStyle = b.name === sk.sel ? "#f0b429" : "rgba(240,180,41,.6)";
    x.lineWidth = b.name === sk.sel ? 2 : 1;
    x.beginPath(); x.moveTo(b.x, b.y); x.lineTo(b.x + Math.cos(a) * l, b.y - Math.sin(a) * l); x.stroke();
    x.fillRect(b.x - 1.5, b.y - 1.5, 3, 3);
  }
  if (apercu) {
    x.strokeStyle = "#ffffff"; x.lineWidth = 1; x.setLineDash([3, 2]);
    if (sk.outil === "os") { x.beginPath(); x.moveTo(apercu.a.x, apercu.a.y); x.lineTo(apercu.b.x, apercu.b.y); x.stroke(); }
    else x.strokeRect(Math.min(apercu.a.x, apercu.b.x) + 0.5, Math.min(apercu.a.y, apercu.b.y) + 0.5,
                      Math.abs(apercu.b.x - apercu.a.x), Math.abs(apercu.b.y - apercu.a.y));
    x.setLineDash([]);
  }
  $("#skInfo").textContent = __dzT9("sprites.sp1_sk.info", "{os} os · {pieces} pièce(s)", { os: sk.bones.length, pieces: sk.pieces.length });
  $("#skSave").disabled = !window.SLK.pret(sk);
  skListe();
}

function skListe() {
  const ligneOs = (b) => `<div class="sk-row${b.name === sk.sel ? " on" : ""}" data-os="${escA(b.name)}">
      <span class="sk-ico" title="${__dzT9("sprites.sp1_sk.choisir_os", "Choisir cet os : les prochains os et pièces s'y accrochent")}">${dzIcone("dz-lab3d-os", { taille: 16 })}</span>
      <input class="sk-nom" value="${escA(b.name)}" maxlength="32" title="${__dzT9("sprites.sp1_sk.nom_os", "Nom de l'os (lettres, chiffres, _ ou -)")}">
      <span class="unit">← ${esc(b.parent)} · ${Math.round(b.rotation)}°</span>
      <button class="sk-del" title="${__dzT9("sprites.sp1_sk.suppr_os", "Supprimer cet os, ses enfants et leurs pièces")}" aria-label="${__dzT9("sprites.sp1_sk.suppr_os", "Supprimer cet os, ses enfants et leurs pièces")}">${dzIcone("dz-action-supprimer", { taille: 16 })}</button></div>`;
  const lignePiece = (p) => `<div class="sk-row" data-piece="${escA(p.name)}">
      <span class="sk-ico">${dzIcone("dz-lab3d-piece", { taille: 16 })}</span>
      <input class="sk-nom" value="${escA(p.name)}" maxlength="32" title="${__dzT9("sprites.sp1_sk.nom_piece", "Nom de la pièce — c'est aussi le nom de son PNG")}">
      <span class="unit">→ ${esc(p.bone)} · ${p.w}×${p.h}</span>
      <button class="sk-del" title="${__dzT9("sprites.sp1_sk.suppr_piece", "Supprimer cette pièce")}" aria-label="${__dzT9("sprites.sp1_sk.suppr_piece", "Supprimer cette pièce")}">${dzIcone("dz-action-supprimer", { taille: 16 })}</button></div>`;
  $("#skList").innerHTML = (sk.bones.map(ligneOs).join("") + sk.pieces.map(lignePiece).join(""))
    || `<div class="hint">${__dzT9("sprites.sp1_sk.aucun_os", "aucun os — glisse sur la case avec l'outil")} ${dzIcone("dz-lab3d-os", { taille: 16 })} ${__dzT9("sprites.sp1_sk.outil_os", "Os")}</div>`;
  $$("#skList .sk-row").forEach((row) => {
    const os = row.dataset.os, piece = row.dataset.piece;
    const champ = row.querySelector(".sk-nom");
    champ.onchange = () => {
      const fait = os ? window.SLK.renommerOs(sk, os, champ.value) : window.SLK.renommerPiece(sk, piece, champ.value);
      if (!fait) toast((os ? __dzT9("sprites.sp1_sk.nom_refuse_os", "Nom refusé : 1 à 32 caractères (lettres, chiffres, _ ou -), unique, et pas « root »") : __dzT9("sprites.sp1_sk.nom_refuse", "Nom refusé : 1 à 32 caractères (lettres, chiffres, _ ou -), unique")), true);
      skDessiner();
    };
    row.querySelector(".sk-del").onclick = () => {
      if (os) {
        const r = window.SLK.supprimerOs(sk, os);
        if (r.os > 1 || r.pieces) toast(__dzT9("sprites.sp1_sk.retires", "{os} os et {pieces} pièce(s) retirés", { os: r.os, pieces: r.pieces }));
      } else window.SLK.supprimerPiece(sk, piece);
      skDessiner();
    };
    if (os) row.querySelector(".sk-ico").onclick = () => { sk.sel = sk.sel === os ? "" : os; skDessiner(); };
  });
}

function skOutil(o) {
  if (!sk) return;
  sk.outil = o;
  $$("#squelette .sk-outil").forEach((b) => b.classList.toggle("on", b.dataset.outil === o));
}

async function skEcrire() {
  if (!sk || !window.SLK.pret(sk)) return;
  const st = $("#skStatus"), short = skShort;
  $("#skSave").disabled = true;
  try {
    setStatus(st, __dzT9("sprites.sp2_sk.ecriture", "Découpe des pièces et écriture du rig…"), false, 30);
    const d = await api.send("POST", `/assets/sprite/${short}/skeleton`, window.SLK.corps(sk));
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    if (sheet && sheet.short === short) sheet.manifest = m;
    $("#dlSpine").classList.toggle("hidden", !(m.files && m.files.spine));
    setStatus(st, __dzT9("sprites.sp2_sk.ecrit", "rig écrit · {os} os (racine comprise) · {pieces} pièce(s) · hash {hash} — le ZIP emporte spine/", { os: d.bones, pieces: d.slots, hash: d.hash }));
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + e.message, true);
  } finally {
    if (sk) $("#skSave").disabled = !window.SLK.pret(sk);
  }
}

function skWire() {
  const cv = $("#skCanvas");
  const point = (ev) => { const b = cv.getBoundingClientRect(); return { x: (ev.clientX - b.left) * cv.width / b.width, y: (ev.clientY - b.top) * cv.height / b.height }; };
  cv.addEventListener("pointerdown", (ev) => { if (!sk) return; skGlisse = point(ev); try { cv.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ } });
  cv.addEventListener("pointermove", (ev) => { if (sk && skGlisse) skDessiner({ a: skGlisse, b: point(ev) }); });
  cv.addEventListener("pointerup", (ev) => {
    if (!sk || !skGlisse) return;
    const a = skGlisse, b = point(ev);
    skGlisse = null;
    try {
      if (sk.outil === "os") window.SLK.ajouterOs(sk, a, b);
      else if (!window.SLK.ajouterPiece(sk, a, b)) toast(__dzT9("sprites.sp2_sk.boite_petite", "Boîte trop petite : glisse sur au moins 2 px"), true);
    } catch (e) { toast(e.message, true); }
    skDessiner();
  });
  $("#skFrame").onchange = () => skFrame(parseInt($("#skFrame").value, 10) || 0);
  $$("#squelette .sk-outil").forEach((b) => b.onclick = () => skOutil(b.dataset.outil));
  $("#skSave").onclick = skEcrire;
}

async function applyEditor() {
  if (!sheet || !editOrder.length) return;
  const st = $("#editStatus");
  const btn = $("#editApply");
  btn.disabled = true;
  try {
    setStatus(st, __dzT9("sprites.sp2_ed.reassemblage", "Réassemblage…"), false, 20);
    await api.send("POST", `/assets/sprite/${sheet.short}/reassemble`,
      { order: editOrder,
        columns: $("#columns").value === "auto" ? "auto" : parseInt($("#columns").value, 10),
        anim: animOpts(editOrder.length) });
    const m = await api.get("/assets/sprite/" + sheet.short + "/manifest");
    showResult(sheet.short, m);
    toastOk(__dzT9("sprites.sp2_ed.reassemblee", "Feuille réassemblée"), __dzT9("sprites.sp2_com.local_gratuit", " — local, gratuit"));
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

function buildPlayer(short, m) {
  cancelAnimationFrame(player.raf);
  const cv = $("#cv"), g = m.grid;
  cv.width = g.cell_w; cv.height = g.cell_h;
  player.imgs = m.frames.map(f => {
    const im = new Image();
    im.src = `/api/assets/sprite/${short}/frame/${f.index}?r=${sheetRev}`;
    return im;
  });
  player.n = m.frames.length; player.i = 0; player.acc = 0; player.last = 0;
  player.playing = true; playIcone();
  if (m.fps) { $("#pfps").value = m.fps; $("#pfpsVal").textContent = m.fps; }
  applyZoom(); applyBg();
  const ctx = cv.getContext("2d");
  const tick = (t) => {
    const fps = parseInt($("#pfps").value, 10) || 8;
    if (!player.last) player.last = t;
    if (player.playing) {
      player.acc += t - player.last;
      const step = 1000 / (fps * (player.speed || 1));
      while (player.acc >= step) { player.acc -= step; player.i = (player.i + 1) % player.n; }
    }
    player.last = t;
    const im = player.imgs[player.i];
    if (im && im.complete && im.naturalWidth) {
      ctx.clearRect(0, 0, cv.width, cv.height);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(im, 0, 0, cv.width, cv.height);
    }
    player.raf = requestAnimationFrame(tick);
  };
  player.raf = requestAnimationFrame(tick);
}

function applyZoom() {
  const cv = $("#cv"), z = $("#pzoom").value;
  const pix = !!(sheet && sheet.manifest && sheet.manifest.pixel);
  cv.classList.toggle("fit", z === "fit");
  cv.style.width = z === "fit" ? "" : (cv.width * parseInt(z, 10)) + "px";
  cv.style.height = "";
  cv.classList.toggle("pix", pix || (z !== "fit" && parseInt(z, 10) >= 2));
}
function applyBg() {
  const v = $("#pbg").value, stage = $("#stage");
  stage.className = "stage" + (v === "checker" ? " bg-checker" : v.startsWith("sc-") ? " " + v : "");   // lot 5 : fonds de scène
  stage.style.background = (v === "checker" || v.startsWith("sc-")) ? "" : v;
}
/* lot 5 : Playground — miroir, déplacement au clavier, vitesse */
function applyPose() { const cv = $("#cv"); cv.style.transform = `translate(${player.dx}px, ${player.dy}px) scaleX(${player.flip ? -1 : 1})`; }
function playgroundWire() {
  $("#pflip").onclick = () => { player.flip = !player.flip; $("#pflip").classList.toggle("actif", player.flip); applyPose(); };
  $("#pspeed").onchange = () => { player.speed = parseFloat($("#pspeed").value) || 1; };
  document.addEventListener("keydown", (ev) => {
    if (/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || "")) return;
    if ($("#player").classList.contains("hidden")) return;
    const k = ev.key.toLowerCase(), pas = 4, borne = 200;
    if (k === "a" || k === "arrowleft") player.dx = Math.max(-borne, player.dx - pas);
    else if (k === "d" || k === "arrowright") player.dx = Math.min(borne, player.dx + pas);
    else if (k === "w" || k === "arrowup") player.dy = Math.max(-borne, player.dy - pas);
    else if (k === "s" || k === "arrowdown") player.dy = Math.min(borne, player.dy + pas);
    else if (k === " ") { player.playing = !player.playing; playIcone(); }
    else return;
    ev.preventDefault(); applyPose();
  });
}

async function saveToLibrary() {
  if (!sheet) return;
  try {
    const d = await api.send("POST", `/assets/sprite/${sheet.short}/save`);
    savedSheet = { short: sheet.short, filename: (d && d.filename) || null };
    updateStudioBtn();
    toastOk(`${__dzT9("sprites.sp2_lib.copie", "Sheet copié dans la Library")}${d && d.filename ? " : " + d.filename : ""}`, __dzT9("sprites.sp2_lib.reutilisable", " — réutilisable dans le Studio (nœud Image)."));
  } catch (e) { toast(__dzT9("sprites.sp2_lib.save_echoue", "Save to Library échoué : ") + e.message, true); }
}

/* ───────── hand-off « → Studio » (9d) ─────────
   Après Save to Library, le sheet est une image gen_*.png : on ouvre le
   Studio du parent avec un graphe d'un seul nœud Image (même mécanisme
   que « Rouvrir dans Studio » : window.__dzRenderGraph est lu au montage
   du Studio). Bouton visible uniquement dans l'iframe du hub. */
function updateStudioBtn() {
  const ok = !!(savedSheet && savedSheet.filename && sheet
                && savedSheet.short === sheet.short
                && window.parent !== window);
  $("#toStudio").classList.toggle("hidden", !ok);
}
function toStudio() {
  if (!(savedSheet && savedSheet.filename)) return;
  const p = window.parent;
  if (!p || p === window) return;
  try {
    p.__dzRenderGraph = {
      name: "spritesheet.graph",
      nodes: [{ id: "simg1", type: "Image", x: 320, y: 220,
                props: { filename: savedSheet.filename } }],
      edges: [],
    };
    p.dispatchEvent(new p.CustomEvent("deepotus:navigate",
                                      { detail: { view: "studio" } }));
  } catch (e) { toast(__dzT9("sprites.sp2_lib.studio_impossible", "Ouverture du Studio impossible : ") + e.message, true); }
}

/* ───────── hand-off entrant (Library → Sprite Lab, 9d) ───────── */
window.addEventListener("message", (ev) => {
  const d = ev && ev.data;
  if (!d || d.type !== "spritelab:source" || !d.source) return;
  if (d.source.kind === "job" && d.source.job_id) {
    switchSrcTab("render");
    setSource({ kind: "job", job_id: d.source.job_id,
                label: d.source.label || ("render " + d.source.job_id.slice(0, 8)) });
    renderRenderList();                 // surligne le render si la liste est là
  } else if (d.source.kind === "image" && d.source.filename) {
    selImage = d.source.filename;
    switchSrcTab("image"); renderImgGrid();
  }
});

/* ───────── t111 (plan-sprites T9-T11) : onglets Bible et Prompt ─────────
   Le module pur directions.js porte les tables et les corps ; ici, le DOM, `<model-viewer>` et les appels. Les routes
   sont celles de #237 (from-board : la planche découpée ; capture : une vue déposée, alpha MESURÉ) et
   /images/generate pour le prompt. Le navigateur voit et capture, Python écrit : aucune feuille n'est faite ici. */
let entities = null, selEntity = null, busyBible = false;
let persona = null, busyPrompt = false, imageModel = "";
const pucesOn = new Set();

const selEnt = () => (entities || []).find((e) => e.id === selEntity) || null;

async function loadEntities() {
  await SLD_PRET;
  if (!entities) {
    try { entities = (await api.get("/bible/entities")).entities || []; }
    catch (e) { $("#entList").innerHTML = `<div class="empty-note">${__dzT9("sprites.sp2_bible.indispo", "Bible indisponible : {msg}", { msg: esc(e.message) })}</div>`; return; }
  }
  renderEntities();
}
function renderEntities() {
  if (!entities) return;
  const l = window.SLD.entitesDecoupables(entities, $("#entSearch").value);
  $("#entList").innerHTML = l.map((e) => `
    <div class="render-item${e.id === selEntity ? " sel" : ""}" data-id="${escA(e.id)}">
      <div class="rt">${esc(e.name)}</div>
      <div class="rm">${__dzT9("sprites.sp2_bible.planche", "planche")}${e.model3d_job ? ' · <span class="ent-3d">' + __dzT9("sprites.sp2_bible.modele3d", "modèle 3D") + '</span>' : ""}</div>
    </div>`).join("")
    || `<div class="empty-note">${__dzT9("sprites.sp2_bible.aucun", "Aucun personnage avec une planche — génère-la dans l'Atelier (Planche).")}</div>`;
  $$("#entList .render-item").forEach((el) => el.onclick = () => { selEntity = el.dataset.id; renderEntities(); });
  majBible();
}
function majBible() {
  const e = selEnt();
  $("#bibleCut").disabled = !e || busyBible;
  $("#bible3d").disabled = !e || !e.model3d_job || busyBible;
  $("#bible3d").title = e && !e.model3d_job
    ? __dzT9("sprites.sp2_bible.pas_3d", "Ce personnage n'a pas de modèle 3D — génère-le dans Assets 3D, ou découpe la planche (4 directions)")
    : __dzT9("sprites.sp2_bible.rend_3d", "Rend le modèle 3D sous 8 angles et en fait une feuille de 8 directions (local, gratuit)");
}

/* la feuille d'un job lancé : suivi, manifeste, préviz — commun à la planche et aux orbites */
async function finirFeuille(jobId, st, msg) {
  const j = await pollJob(jobId, (jj) => setStatus(st, `${jj.current_step || jj.status}…`, false, jj.progress || 5));
  if (j.status !== "done") throw new Error(j.error || __dzT9("sprites.sp2_bible.assemblage_echoue", "assemblage échoué"));
  const short = jobId.slice(0, 8);
  const m = await api.get("/assets/sprite/" + short + "/manifest");
  clearStatus(st);
  showResult(short, m);
  toastOk(msg[0], msg[1]);
}

async function cutFromBible() {
  const e = selEnt();
  if (!e || busyBible) return;
  busyBible = true; majBible();
  const st = $("#bibleStatus");
  try {
    setStatus(st, __dzT9("sprites.sp2_bible.decoupe", "Découpe de la planche…"), false, 5);
    const body = { entity_id: e.id, cell: cellOpts(), trim: $("#trim").value };
    const px = pixelOpts(); if (px) body.pixel = px;
    const po = postOpts(); if (po) body.post = po;
    const d = await api.send("POST", "/assets/sprite/from-board", body);
    await finirFeuille(d.job_id, st, [__dzT9("sprites.sp2_bible.quatre_dir", "4 directions depuis la planche"), __dzT9("sprites.sp2_com.gratuit_local", " — gratuit, local")]);
  } catch (err) {
    setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + err.message, true);
  }
  busyBible = false; majBible();
}

/* charge le GLB dans le viewport (une fois par modèle) — `load` ou `error`, borné à une minute */
function chargerModele(mv, url) {
  if (mv.getAttribute("src") === url && mv.loaded) return Promise.resolve();
  return new Promise((ok, ko) => {
    const fin = (f) => (ev) => { clearTimeout(t); mv.removeEventListener("load", bon); mv.removeEventListener("error", mal); f(ev); };
    const bon = fin(() => ok()), mal = fin(() => ko(new Error(__dzT9("sprites.sp2_bible.illisible", "modèle 3D illisible"))));
    const t = setTimeout(fin(() => ko(new Error(__dzT9("sprites.sp2_bible.delai", "délai dépassé au chargement du modèle 3D")))), 60000);
    mv.addEventListener("load", bon); mv.addEventListener("error", mal);
    mv.setAttribute("src", url);
  });
}
/* deux images d'affichage après un déplacement de caméra ; repli par minuterie (requestAnimationFrame dort quand
   l'onglet est caché) */
const deuxImages = () => new Promise((r) => {
  let fait = false; const f = () => { if (!fait) { fait = true; r(); } };
  requestAnimationFrame(() => requestAnimationFrame(f)); setTimeout(f, 250);
});

async function captureOrbites() {
  const e = selEnt();
  if (!e || !e.model3d_job || busyBible) return;
  busyBible = true; majBible();
  const st = $("#bibleStatus"), mv = $("#mv3d"), prefix = window.SLD.hex8();
  try {
    if (!window.customElements || !customElements.get("model-viewer")) throw new Error(__dzT9("sprites.sp2_bible.mv_absent", "model-viewer n'est pas chargé"));
    setStatus(st, __dzT9("sprites.sp2_bible.chargement", "Chargement du modèle 3D…"), false, 3);
    await chargerModele(mv, `/api/assets/3d/${encodeURIComponent(e.model3d_job)}/glb`);
    const noms = [], sansAlpha = [];
    for (let k = 0; k < window.SLD.ORBITES.length; k++) {
      const [nom, theta] = window.SLD.ORBITES[k];
      mv.setAttribute("camera-orbit", window.SLD.orbite(theta));
      if (mv.jumpCameraToGoal) mv.jumpCameraToGoal();
      await deuxImages();
      const blob = await mv.toBlob({ idealAspect: false });
      const r = await fetch(`/api/assets/sprite/capture?dir=${nom}&prefix=${prefix}`,
        { method: "POST", headers: { "Content-Type": "image/png" }, body: blob });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || __dzT9("sprites.sp2_bible.vue_refusee", "vue {nom} refusée ({statut})", { nom, statut: r.status }));
      noms.push(d.filename);
      if (!d.alpha) sansAlpha.push(nom);
      setStatus(st, __dzT9("sprites.sp2_bible.capture", "Capture {k}/8 ({nom})…", { k: k + 1, nom }), false, 8 + k * 10);
    }
    const body = window.SLD.corpsOrbites(noms, sansAlpha, { cell: cellOpts(), pixel: pixelOpts(), post: postOpts(), titre: e.name });
    setStatus(st, __dzT9("sprites.sp2_bible.assemblage", "Assemblage de la feuille…"), false, 90);
    const d = await api.send("POST", "/assets/sprite", body);
    await finirFeuille(d.job_id, st, sansAlpha.length
      ? [__dzT9("sprites.sp2_bible.huit_dir", "8 directions"), __dzT9("sprites.sp2_bible.opaque", " — rendu opaque, clé chroma locale appliquée")] : [__dzT9("sprites.sp2_bible.huit_dir", "8 directions"), __dzT9("sprites.sp2_bible.detoure", " — rendu déjà détouré")]);
  } catch (err) {
    setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + err.message, true);
  }
  busyBible = false; majBible();
}

/* — Prompt : les puces de la persona, le devis, le tir — */
async function loadPersona() {
  await SLD_PRET;
  if (persona) return majDevisPrompt();
  try { persona = await api.get("/persona"); } catch (e) { persona = {}; }
  try { imageModel = ((await api.get("/atelier/settings")).settings || {}).image_model_default || ""; } catch (e) { imageModel = ""; }
  const coul = (c) => /^#[0-9a-f]{3,8}$/i.test(c) ? `<i style="background:${c}"></i>` : "";
  $("#pmChips").innerHTML = window.SLD.puces(persona).map((p) =>
    `<button type="button" class="chip${p.couleur ? " col" : ""}" data-v="${escA(p.v)}" title="${__dzT9("sprites.sp2_pm.ajouter", "Ajouter « {v} » au prompt", { v: escA(p.v) })}">${p.couleur ? coul(p.libelle) : ""}${esc(p.libelle)}</button>`).join("")
    || `<span class="hint">${__dzT9("sprites.sp2_pm.aucun_mot", "aucun mot-clé dans la persona")}</span>`;
  $$("#pmChips .chip").forEach((el) => el.onclick = () => {
    const v = el.dataset.v;
    if (pucesOn.has(v)) pucesOn.delete(v); else pucesOn.add(v);
    el.classList.toggle("on", pucesOn.has(v));
  });
  majDevisPrompt();
}
async function majDevisPrompt() {
  const el = $("#pmCost");
  try {
    const d = await api.send("POST", "/cost/estimate",
      { kind: "image", n: parseInt($("#pmN").value, 10) || 1, model: imageModel || "flux" });
    el.innerHTML = d && d.total_usd != null ? `${dzIcone("dz-action-cout", { taille: 16 })} $${(+d.total_usd).toFixed(3)}` : "";
  } catch (e) { el.textContent = ""; }
}

async function generateFromPrompt() {
  if (busyPrompt) return;
  const sujet = ($("#pmPrompt").value || "").trim();
  if (!sujet) return toast(__dzT9("sprites.sp2_pm.decris", "Décris d'abord le sprite."), true);
  busyPrompt = true; $("#pmGen").disabled = true;
  const st = $("#pmStatus");
  try {
    setStatus(st, __dzT9("sprites.sp2_pm.generation", "Génération des images…"), false, 10);
    const d = await api.send("POST", "/images/generate", window.SLD.corpsPrompt(sujet, [...pucesOn], $("#pmN").value, $("#pmSize").value));
    const noms = (d && d.images) || [];
    if (!noms.length) throw new Error(__dzT9("sprites.sp2_pm.aucune_rendue", "aucune image rendue"));
    clearStatus(st);
    loadImages();                                   // la Library a changé
    // le suffixe demande un fond vert uni : la clé chroma locale (gratuite) le retire — jamais l'API payante par défaut
    if ($("#removeBg").value === "api") { $("#removeBg").value = "chroma"; savePrefs(); updateCost(); }
    setSource({ kind: "images", filenames: noms, label: __dzT9("sprites.sp2_pm.images_prompt", "{n} image(s) du prompt", { n: noms.length }) });
    toastOk(__dzT9("sprites.sp2_pm.generees", "{n} image(s) générée(s)", { n: noms.length }), __dzT9("sprites.sp2_pm.detourage", " — détourage en clé chroma (local) ; choisis tes frames puis génère le sheet"));
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + e.message, true);
  }
  busyPrompt = false; $("#pmGen").disabled = false;
}

function bibleWire() {
  $("#entSearch").oninput = renderEntities;
  $("#bibleCut").onclick = cutFromBible;
  $("#bible3d").onclick = captureOrbites;
  $("#pmGen").onclick = generateFromPrompt;
  $("#pmN").onchange = majDevisPrompt;
}

/* ───────── wiring ───────── */
function switchSrcTab(which) {
  $$("#srcTabs .tab").forEach(t => t.classList.toggle("active", t.dataset.src === which));
  $("#srcStarter").classList.toggle("hidden", which !== "starter");
  $("#srcImage").classList.toggle("hidden", which !== "image");
  $("#srcRender").classList.toggle("hidden", which !== "render");
  $("#srcUpload").classList.toggle("hidden", which !== "upload");
  $("#srcFeuille").classList.toggle("hidden", which !== "feuille");
  $("#srcBible").classList.toggle("hidden", which !== "bible");
  $("#srcPrompt").classList.toggle("hidden", which !== "prompt");
  // lot 1 : en mode Feuille la colonne du milieu montre la planche, pas le filmstrip
  const feuille = which === "feuille" && !!F.tampon;
  $("#feuillePane").classList.toggle("hidden", !feuille);
  $("#strip").classList.toggle("hidden", feuille);
  $("#feuilleOut").classList.toggle("hidden", !feuille);
  if (which === "starter") loadStarter();
  if (which === "bible") loadEntities();
  if (which === "prompt") loadPersona();
}

/* ───────── packs de démarrage CC0 ─────────
   Même source que l'écran Son & VFX (/api/particles/presets) : un preset
   choisi ici et un preset choisi là-bas produisent le même sprite. Une seule
   liste, deux surfaces — sinon les deux dérivent et l'utilisateur ne sait plus
   laquelle fait foi. */
let starterData = null, busyStarter = false;

async function loadStarter() {
  if (starterData) return;
  try {
    starterData = await api.get("/particles/presets");
  } catch (e) {
    $("#starterGrid").innerHTML =
      `<div class="empty-note">${__dzT9("sprites.sp2_st.indispo", "Catalogue indisponible : {msg}", { msg: esc(e.message) })}</div>`;
    return;
  }
  renderStarter();
}

function starterTile(item, kind) {
  const sub = kind === "preset" ? item.type : __dzT9("sprites.sp2_st.n_images", "{n} images", { n: item.frames });
  return `<button class="starter-tile" data-kind="${kind}" data-id="${esc(item.id)}"
    title="${esc(item.desc || item.name)}">
    <span class="starter-thumb"${item.thumb ? ` style="background-image:url(${esc(item.thumb)})"` : ""}></span>
    <span class="starter-name">${esc(item.name)}</span>
    <span class="starter-sub">${esc(sub)}</span></button>`;
}

function renderStarter() {
  const d = starterData || { presets: [], anims: [] };
  if (!d.presets.length && !d.anims.length) {
    $("#starterGrid").innerHTML = `<div class="empty-note">${__dzT9("sprites.sp2_st.absent", "Catalogue de démarrage absent — lance {cmd} puis relance l'app.", { cmd: "<code>python scripts/build_starter_catalog.py --fetch</code>" })}</div>`;
    return;
  }
  $("#starterCount").textContent = __dzT9("sprites.sp2_st.n_effets", "{n} effets", { n: d.presets.length });
  $("#starterGrid").innerHTML = d.presets.map(p => starterTile(p, "preset")).join("");
  $("#starterAnims").innerHTML = d.anims.map(a => starterTile(a, "anim")).join("");
  $$("#srcStarter .starter-tile").forEach(b => {
    b.onclick = () => runStarter(b.dataset.kind, b.dataset.id, b);
  });
}

async function runStarter(kind, id, btn) {
  if (busyStarter) return;
  busyStarter = true;
  $$("#srcStarter .starter-tile").forEach(b => b.classList.toggle("busy", b === btn));
  const st = $("#starterStatus");
  try {
    const cell = parseInt($("#cellSize").value, 10) || 512;   // T108 : « native » -> NaN -> 512, les particules gardent leur canevas
    const body = kind === "anim" ? { anim: id, cell } : { preset: id };
    setStatus(st, __dzT9("sprites.sp2_st.lance", "Job lancé…"), false, 3);
    const path = kind === "anim" ? "/assets/starter-anim" : "/assets/particles";
    const d = await api.send("POST", path, body);
    const j = await pollJob(d.job_id, jj => setStatus(st,
      `${jj.current_step || jj.status}…`, false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || __dzT9("sprites.sp2_com.gen_echouee", "génération échouée"));
    const short = d.job_id.slice(0, 8);
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    clearStatus(st);
    showResult(short, m);
    toastOk(__dzT9("sprites.sp2_st.pret", "Sprite prêt"), __dzT9("sprites.sp2_st.gratuit_local", " — gratuit, généré en local"));
  } catch (e) {
    setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + e.message, true);
    toast(__dzT9("sprites.sp2_st.gen_echouee", "Génération échouée : ") + e.message, true);
  }
  busyStarter = false;
  $$("#srcStarter .starter-tile").forEach(b => b.classList.remove("busy"));
}
function syncPixelSet() {
  $(".pixelset").classList.toggle("off", !$("#pixelOn").checked);
}
/* T110 (plan-sprites T6) — post-traitement : rien n'est envoyé quand rien n'est demandé (le serveur sauterait la passe
   de toute façon, mais le manifeste dirait alors `post: null`, ce qui est la vérité) */
function syncPostSet() {
  $(".postset").classList.toggle("off", !$("#postOn").checked);
}
function postOpts() {
  if (!$("#postOn").checked) return undefined;
  const o = {};
  const w = parseInt($("#poWidth").value, 10) || 0;
  if (w > 0) o.outline = { width: w, color: $("#poColor").value };
  const dx = parseInt($("#poDx").value, 10) || 0;
  const dy = parseInt($("#poDy").value, 10) || 0;
  const op = parseInt($("#poOpacity").value, 10);
  if (dx || dy) o.shadow = { dx, dy, opacity: Number.isFinite(op) ? Math.max(0, Math.min(255, op)) : 110 };
  if ($("#poOrphans").checked || $("#poSmooth").checked)
    o.clean = { orphans: $("#poOrphans").checked, smooth: $("#poSmooth").checked };
  return Object.keys(o).length ? o : undefined;
}

function wire() {
  $$("#srcTabs .tab").forEach(t => t.onclick = () => switchSrcTab(t.dataset.src));
  $("#imgSearch").oninput = renderImgGrid;
  $("#renderSearch").oninput = renderRenderList;
  $("#animerBtn").onclick = animer;
  $("#vidFile").onchange = (e) => { if (e.target.files[0]) uploadVideo(e.target.files[0]); };
  $("#extractBtn").onclick = extract;
  $("#stripAll").onclick = () => {
    const allOn = stripState.every(Boolean);
    stripState = stripState.map(() => !allOn);
    renderStrip();
  };
  $("#genBtn").onclick = generate;
  $("#tagAdd").onclick = () => {
    const n = Math.max(0, keptIndices().length - 1);
    tagRows.push({ name: "anim" + (tagRows.length + 1), from: 0, to: n, direction: "forward" });
    renderTags(); savePrefs();
  };
  $("#animMs").onchange = savePrefs;
  $("#editApply").onclick = applyEditor;
  $("#editReset").onclick = () => {
    if (sheet) { editOrder = sheet.manifest.frames.map(f => f.index); renderEditor(); }
  };

  /* fps/max : la sonde est locale et gratuite -> ré-extraction auto (debounce) */
  for (const id of ["fps", "maxFrames"]) $("#" + id).onchange = () => {
    savePrefs();
    clearTimeout(extractTimer);
    if (source) extractTimer = setTimeout(extract, 700);
  };
  for (const id of ["removeBg", "trim", "cellSize", "cellAlign", "columns",
                    "pixTarget", "pixPalette", "pixColors", "pixDither",
                    "animDur", "animRatio"])
    $("#" + id).onchange = () => { savePrefs(); updateCost(); };
  $("#pixelOn").onchange = () => { syncPixelSet(); savePrefs(); };
  $("#postOn").onchange = () => { syncPostSet(); savePrefs(); };
  for (const id of ["poWidth", "poColor", "poDx", "poDy", "poOpacity", "poOrphans", "poSmooth"])
    $("#" + id).onchange = savePrefs;

  $("#playBtn").onclick = () => {
    player.playing = !player.playing;
    playIcone();
  };
  $("#pfps").oninput = () => { $("#pfpsVal").textContent = $("#pfps").value; savePrefs(); };
  $("#pzoom").onchange = () => { applyZoom(); savePrefs(); };
  $("#pbg").onchange = () => { applyBg(); savePrefs(); };
  $("#saveLib").onclick = saveToLibrary;
  $("#toStudio").onclick = toStudio;
  playgroundWire();   // lot 5
  hbWire();           // T112 : hitboxes par frame
  bibleWire();        // t111 : onglets Bible et Prompt
  skWire();           // t111 (T12) : squelette Spine
  document.addEventListener("slk-pret", () => { if (sheet) skCharger(sheet.short, sheet.manifest); });   // skeleton.js arrive APRÈS ce script
  document.addEventListener("slh-pret", () => { if (sheet) hbCharger(sheet.short, sheet.manifest); });   // hitbox.js (module) arrive APRÈS ce script
  // lot 1 : l'onglet Feuille se câble quand le module pur est chargé
  if (window.SLF) feuilleWire(); else document.addEventListener("slf-pret", feuilleWire, { once: true });
}


/* ───────── lot 1 : Feuille existante (19/09) — tout en local, module pur feuille.js ─────────
   La planche est un tampon {w, h, data} lu une fois ; la grille, la sélection,
   les décalages et les sections vivent dans F ; le canvas de la colonne du
   milieu redessine la planche RECOMPOSÉE (décalages appliqués) avec la grille
   et la sélection ; le lecteur de droite lit les cases sélectionnées. */
const F = { img: null, tampon: null, filename: null, g: null, sel: [], occ: [], off: [], sections: [], dernier: null, peint: null, courant: 0 };
const fTampon = () => { const c = document.createElement("canvas"); c.width = F.img.naturalWidth; c.height = F.img.naturalHeight; const x = c.getContext("2d"); x.drawImage(F.img, 0, 0); const d = x.getImageData(0, 0, c.width, c.height); return { w: c.width, h: c.height, data: d.data }; };
async function feuilleOuvrir(src, filename) {
  const im = new Image(); im.crossOrigin = "anonymous";
  // onload plutôt que decode() : decode() reste SUSPENDU quand l'onglet est caché (mesuré au lot 5)
  await new Promise((res, rej) => { im.onload = () => res(); im.onerror = () => rej(new Error(__dzT9("sprites.sp2_f.illisible", "image illisible : ") + String(src).slice(0, 60))); im.src = src; });
  F.img = im; F.filename = filename; F.tampon = fTampon(); F.off = []; F.sections = []; F.dernier = null; F.courant = 0;
  source = null;                                            // pas une source de génération : la chaîne Seedance reste à part
  const chip = $("#srcChip"); chip.textContent = __dzT9("sprites.sp2_f.chip", "Feuille : ") + filename; chip.classList.add("set");
  switchSrcTab("feuille");
  feuilleDetect();
}
function feuilleDetect() {
  const g = window.SLF.grille_detecter(F.tampon);
  $("#fCols").value = g.cols; $("#fRows").value = g.rows;
  feuilleGrille();
}
function feuilleGrille() {
  const cols = Math.max(1, parseInt($("#fCols").value, 10) || 1), rows = Math.max(1, parseInt($("#fRows").value, 10) || 1);
  F.g = { cols, rows, cell_w: Math.floor(F.tampon.w / cols), cell_h: Math.floor(F.tampon.h / rows) };
  F.occ = window.SLF.cases_occupees(F.tampon, F.g);
  F.sel = F.occ.slice(); F.off = F.occ.map(() => ({ dx: 0, dy: 0 })); F.sections = []; F.dernier = null; F.courant = 0;
  $("#fDims").textContent = `${F.tampon.w}×${F.tampon.h} · ${__dzT9("sprites.sp2_f.cases", "cases")} ${F.g.cell_w}×${F.g.cell_h}`;
  feuilleDessiner(); feuilleJoueur();
}
function feuilleDessiner() {
  const cv = $("#fCanvas"), g = F.g; cv.width = F.tampon.w; cv.height = F.tampon.h;
  const x = cv.getContext("2d"); x.imageSmoothingEnabled = false;
  const rec = window.SLF.feuille_recomposer(F.tampon, g, F.off);
  x.putImageData(new ImageData(rec.data, rec.w, rec.h), 0, 0);
  for (let i = 0; i < g.cols * g.rows; i++) {
    const r = window.SLF.rect_case(g, i);
    if (F.sel[i]) { x.fillStyle = "rgba(58,166,107,.22)"; x.fillRect(r.x, r.y, r.w, r.h); }
    x.strokeStyle = i === F.courant ? "#39b3d0" : (F.sel[i] ? "#3aa66b" : (F.occ[i] ? "#3a3a3a" : "#222")); x.lineWidth = 1; x.strokeRect(r.x + .5, r.y + .5, r.w - 1, r.h - 1);
    x.fillStyle = "#9a9a9a"; x.font = "9px system-ui"; x.fillText(String(i), r.x + 2, r.y + 9);
  }
  const n = F.sel.filter(Boolean).length; $("#fCount").textContent = `${n}/${F.occ.filter(Boolean).length}`;
  $("#fSections").innerHTML = F.sections.map((s) => `<div class="section-row"><span class="nom">${esc(s.nom)}</span><span>${s.debut}–${s.fin}</span><span>${esc(s.mode)}</span><button class="btn ghost fSecDel" data-nom="${esc(s.nom)}" title="${__dzT9("sprites.sp2_f.retirer", "Retirer")}" aria-label="${__dzT9("sprites.sp2_f.retirer", "Retirer")}">${dzIcone("dz-action-retirer", { taille: 16 })}</button></div>`).join("") || `<div class="hint">${__dzT9("sprites.sp2_f.aucune_section", "aucune section — sélectionne des cases puis « + depuis la sélection »")}</div>`;
  $$(".fSecDel").forEach((b) => b.onclick = () => { F.sections = F.sections.filter((s) => s.nom !== b.dataset.nom); feuilleDessiner(); });
}
const fCaseDe = (ev) => { const cv = $("#fCanvas"), r = cv.getBoundingClientRect(); if (!r.width) return -1; const x = (ev.clientX - r.left) * cv.width / r.width, y = (ev.clientY - r.top) * cv.height / r.height; const c = Math.floor(x / F.g.cell_w), l = Math.floor(y / F.g.cell_h); return (c < 0 || l < 0 || c >= F.g.cols || l >= F.g.rows) ? -1 : l * F.g.cols + c; };
function feuilleGestes() {
  const cv = $("#fCanvas");
  cv.onpointerdown = (ev) => { if (!F.g) return; const i = fCaseDe(ev); if (i < 0) return; ev.preventDefault(); try { cv.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    F.sel = window.SLF.selection_clic(F.sel, i, { ctrl: ev.ctrlKey || ev.metaKey, shift: ev.shiftKey, dernier: F.dernier });
    F.peint = F.sel[i]; F.dernier = i; F.courant = i; feuilleDessiner(); };
  cv.onpointermove = (ev) => { if (F.peint === null || !(ev.buttons & 1)) return; const i = fCaseDe(ev); if (i < 0 || F.sel[i] === F.peint) return; F.sel = F.sel.slice(); F.sel[i] = F.peint; F.dernier = i; F.courant = i; feuilleDessiner(); };
  cv.onpointerup = () => { if (F.peint === null) return; F.peint = null; feuilleJoueur(); };
}
function feuilleJoueur() {                      // le lecteur local : les cases sélectionnées, avec leurs décalages
  cancelAnimationFrame(player.raf);
  const rec = window.SLF.feuille_recomposer(F.tampon, F.g, F.off);
  const src = document.createElement("canvas"); src.width = rec.w; src.height = rec.h; src.getContext("2d").putImageData(new ImageData(rec.data, rec.w, rec.h), 0, 0);
  const idx = F.sel.map((v, i) => v ? i : -1).filter((i) => i >= 0);
  const cv = $("#cv"); cv.width = F.g.cell_w; cv.height = F.g.cell_h;
  $("#outEmpty").classList.add("hidden"); $("#player").classList.remove("hidden"); $("#exports").classList.add("hidden"); $("#sheetWrap").classList.add("hidden"); $("#feuilleOut").classList.remove("hidden");
  $("#outInfo").textContent = `${F.g.cols}×${F.g.rows} · ${F.g.cell_w}px · ${idx.length} frames · ${F.filename || ""}`;
  player.imgs = []; player.n = idx.length; player.i = 0; player.acc = 0; player.last = 0; player.playing = true; playIcone();
  applyZoom(); applyBg();
  const ctx = cv.getContext("2d");
  const tick = (t) => { const fps = parseInt($("#pfps").value, 10) || 8; if (!player.last) player.last = t;
    if (player.playing && player.n) { player.acc += t - player.last; const step = 1000 / (fps * (player.speed || 1)); while (player.acc >= step) { player.acc -= step; player.i = (player.i + 1) % player.n; } }
    player.last = t;
    if (player.n) { const r = window.SLF.rect_case(F.g, idx[player.i]); ctx.clearRect(0, 0, cv.width, cv.height); ctx.imageSmoothingEnabled = false; ctx.drawImage(src, r.x, r.y, r.w, r.h, 0, 0, r.w, r.h); }
    player.raf = requestAnimationFrame(tick); };
  player.raf = requestAnimationFrame(tick);
}
function feuilleAligner(mode) { try { F.off = mode ? window.SLF.aligner_frames(F.tampon, F.g, F.sel, mode) : F.occ.map(() => ({ dx: 0, dy: 0 })); feuilleDessiner(); feuilleJoueur(); } catch (e) { toast(e.message, true); } }
function feuilleManifest() { return window.SLF.manifest_feuille({ img: F.tampon, g: F.g, sel: F.sel, offsets: F.off, fps: parseInt($("#pfps").value, 10) || 12, sections: F.sections, filename: F.filename }); }
function feuillePngBlob() { const rec = window.SLF.feuille_recomposer(F.tampon, F.g, F.off); const c = document.createElement("canvas"); c.width = rec.w; c.height = rec.h; c.getContext("2d").putImageData(new ImageData(rec.data, rec.w, rec.h), 0, 0); return new Promise((r) => c.toBlob(r, "image/png")); }
const fTelecharger = (blob, nom) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
const fBase = () => (F.filename || "feuille").replace(/\.\w+$/, "");
function feuilleWire() {
  $("#feuilleFile").onchange = (e) => { const f = e.target.files[0]; if (f) feuilleOuvrir(URL.createObjectURL(f), f.name).catch((err) => toast(err.message, true)); };
  $("#feuilleSearch").oninput = renderFeuilleGrid;
  $("#fDetect").onclick = feuilleDetect; $("#fOk").onclick = feuilleGrille;
  $("#fAll").onclick = () => { F.sel = F.occ.slice(); feuilleDessiner(); feuilleJoueur(); };
  $("#fNone").onclick = () => { F.sel = F.occ.map(() => false); feuilleDessiner(); feuilleJoueur(); };
  $$(".fEvery").forEach((b) => b.onclick = () => { F.sel = window.SLF.selection_une_sur(F.occ, +b.dataset.n); feuilleDessiner(); feuilleJoueur(); });
  $("#fAlDeux").onclick = () => feuilleAligner("deux"); $("#fAlX").onclick = () => feuilleAligner("x"); $("#fAlPieds").onclick = () => feuilleAligner("pieds"); $("#fAlZero").onclick = () => feuilleAligner(null);
  $$(".fNudge").forEach((b) => b.onclick = () => { const o = F.off[F.courant]; if (!o) return; F.off = F.off.slice(); F.off[F.courant] = { dx: o.dx + +b.dataset.dx, dy: o.dy + +b.dataset.dy }; feuilleDessiner(); feuilleJoueur(); });
  $("#fSecAdd").onclick = () => { const idx = F.sel.map((v, i) => v ? i : -1).filter((i) => i >= 0); if (!idx.length) return toast(__dzT9("sprites.sp2_f.selectionne", "sélectionne des cases d'abord"), true);
    try { F.sections = window.SLF.section_definir(F.sections, { nom: $("#fSecNom").value, debut: 0, fin: idx.length - 1, mode: $("#fSecMode").value }, idx.length); $("#fSecNom").value = ""; feuilleDessiner(); } catch (e) { toast(e.message, true); } };
  $("#fCopyJson").onclick = async () => { try { await navigator.clipboard.writeText(JSON.stringify(feuilleManifest(), null, 2)); toast(__dzT9("sprites.sp2_f.copie", "manifest copié")); } catch (e) { toast(__dzT9("sprites.sp2_f.presse_papiers", "presse-papiers refusé : ") + e.message, true); } };
  $("#fDlJson").onclick = () => fTelecharger(new Blob([JSON.stringify(feuilleManifest(), null, 2)], { type: "application/json" }), fBase() + ".json");
  $("#fDlPng").onclick = async () => fTelecharger(await feuillePngBlob(), fBase() + "_alignee.png");
  $("#fSaveLib").onclick = async () => { try { const fd = new FormData(); fd.append("file", await feuillePngBlob(), `sprites_feuille_${Date.now()}.png`); const r = await fetch("/api/images/upload", { method: "POST", body: fd }); const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || r.statusText); toast(__dzT9("sprites.sp2_f.sauve", "sauvé en Library : {f} — « Envoyer vers » le Vectorlab depuis la Library", { f: d.filename })); loadImages(); } catch (e) { toast(e.message, true); } };
  feuilleGestes();
}
function renderFeuilleGrid() {
  const q = ($("#feuilleSearch").value || "").toLowerCase();
  const list = libImages.filter((im) => !q || im.filename.toLowerCase().includes(q));
  const g = $("#feuilleGrid");
  g.innerHTML = list.slice(0, 120).map((im) => `<img loading="lazy" data-fn="${esc(im.filename)}" title="${esc(im.filename)}" src="/api/images/${encodeURIComponent(im.filename)}">`).join("")
    || `<div class="empty-note">${q ? __dzT9("sprites.sp2_f.aucune_q", "Aucune image pour « {q} ».", { q: esc(q) }) : __dzT9("sprites.sp2_f.aucune_lib", "Aucune image dans la Library.")}</div>`;
  g.querySelectorAll("img").forEach((el) => el.onclick = () => feuilleOuvrir(`/api/images/${encodeURIComponent(el.dataset.fn)}`, el.dataset.fn).catch((err) => toast(err.message, true)));
}
window.SL = Object.assign(window.SL || {}, { feuille: { ouvrir: feuilleOuvrir, etat: () => F, manifest: feuilleManifest, aligner: feuilleAligner } });   // la preuve


/* ───────── lot 4 : palettes unifiées — le select se remplit depuis palettes.js ─────────
   (les cinq palettes « backend » = pixel_ops.py, envoyées par nom) */
function remplirPalettes() {
  const sel = $("#pixPalette"); if (!sel || !window.DZ_PALETTES) return;
  const courante = sel.value || "sweetie16";
  sel.innerHTML = DZ_PALETTES.options_palettes({ backendSeulement: true, courante });
}
if (window.DZ_PALETTES) remplirPalettes(); else document.addEventListener("dz-palettes", remplirPalettes, { once: true });

/* ───────── restauration après remontage (fix préviz 20/07) ─────────
   L'iframe du hub est remontée à chaque navigation : sans ceci, un sheet
   généré pendant qu'on a le dos tourné n'est JAMAIS montré (« préviz
   vide ») et une génération en vol est perdue de vue. Au chargement :
   reprendre le poll d'une génération en cours, sinon ré-afficher le
   dernier sheet terminé (les sondes n'ont ni ce titre ni final_video_path). */
const PROBE_TITLE = "Sprites · extraction";

async function showShort(short) {
  const m = await api.get("/assets/sprite/" + short + "/manifest");
  if (!m || !m.grid || !(m.files && m.files.sheet)) return false;
  showResult(short, m);
  return true;
}

async function restoreLast() {
  try {
    const js = await api.get("/jobs?limit=100");
    const mine = js.filter(j => j.provider === "sprite2d"
      && !(j.title || "").startsWith(PROBE_TITLE));
    const run = mine.find(j => j.status === "pending" || j.status === "processing");
    if (run) {                              // génération abandonnée en plein vol
      const st = $("#genStatus");
      busyGen = true; updateGenEnabled();
      try {
        setStatus(st, __dzT9("sprites.sp2_rest.retrouvee", "Génération en cours retrouvée…"), false, 5);
        const j = await pollJob(run.job_id, jj => setStatus(st,
          `${jj.current_step || jj.status}…`, false, jj.progress || 5));
        if (j.status !== "done") throw new Error(j.error || __dzT9("sprites.sp2_com.gen_echouee", "génération échouée"));
        clearStatus(st);
        if (await showShort(run.job_id.slice(0, 8))) toastOk(__dzT9("sprites.sp2_rest.genere", "Sprite sheet généré"));
      } catch (e) {
        setStatus(st, __dzT9("sprites.sp2_com.echec", "Échec : ") + e.message, true);
      }
      busyGen = false; updateGenEnabled();
      return;
    }
    const done = mine
      .filter(j => j.status === "done" && j.final_video_path)
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))[0];
    if (done && await showShort(done.job_id.slice(0, 8)))
      toastOk(__dzT9("sprites.sp2_rest.recharge", "Dernier sheet rechargé"));
  } catch (e) { /* réseau/API indisponible : placeholder d'origine */ }
}

/* poignée de debug / QA (harnais Puppeteer de la recette) */
window.__sl = {
  get state() {
    return { source, extractShort, stripN, kept: keptIndices().length,
             sheet: sheet && sheet.short, busyExtract, busyGen,
             saved: savedSheet && savedSheet.filename };
  },
  setSource,
  showResult,                     // recette 9d : préviz d'un sheet existant
};

(async function init() {
  wire();
  // L'onglet « Démarrer » est celui d'ouverture : sans lui, un nouvel
  // utilisateur tombe sur trois listes vides (pas d'image, pas de render, pas
  // de vidéo) et n'a aucun moyen de voir ce que le Sprite Lab produit.
  switchSrcTab("starter");
  await loadPrefs();
  syncPixelSet();
  syncPostSet();
  loadImages(); loadRenders();
  restoreLast();               // préviz : survit au remontage de l'iframe
})();
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
