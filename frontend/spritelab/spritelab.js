/* Sprite Lab — Game Assets 2D (chantier 9c).
   Vanilla JS, même API que l'app (même origine), même gabarit que /atelier.
   Chaîne : source (image animée Seedance / render / upload) → sonde
   d'extraction (extract_only, locale et gratuite) → filmstrip à toggles →
   génération du sheet (keep = frames gardées) → préviz animée + exports. */
"use strict";

const $ = (s) => document.querySelector(s);
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
let prefsTimer = null, extractTimer = null;

/* ───────── toast ───────── */
let toastTimer = null;
function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg; t.classList.toggle("err", !!err); t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 4200);
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
    if (Date.now() - t0 > (timeoutMs || 15 * 60 * 1000)) throw new Error("délai dépassé");
    await new Promise(r => setTimeout(r, 1200));
  }
}

/* ───────── préférences (atelier_settings.spritelab_prefs) ───────── */
const PREF_IDS = ["fps", "maxFrames", "removeBg", "trim", "cellSize", "cellAlign",
  "columns", "pixTarget", "pixPalette", "pixColors", "pixDither",
  "animDur", "animRatio", "pfps", "pzoom", "pbg"];
function collectPrefs() {
  const p = { pixelOn: $("#pixelOn").checked };
  for (const id of PREF_IDS) p[id] = $("#" + id).value;
  return p;
}
function applyPrefs(p) {
  if (!p || typeof p !== "object") return;
  for (const id of PREF_IDS) if (p[id] != null && $("#" + id)) $("#" + id).value = p[id];
  if (p.pixelOn != null) $("#pixelOn").checked = !!p.pixelOn;
  syncPixelSet(); $("#pfpsVal").textContent = $("#pfps").value;
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
  chip.textContent = src ? "Source : " + src.label : "aucune source";
  chip.classList.toggle("set", !!src);
  updateGenEnabled();
  if (src) extract();                     // sonde locale gratuite -> filmstrip
}

/* — onglet Image : Library + Animer — */
async function loadImages() {
  try {
    libImages = (await api.get("/images")).images || [];
    renderImgGrid();
  } catch (e) {
    $("#imgGrid").innerHTML = `<div class="empty-note">Library indisponible : ${esc(e.message)}</div>`;
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
    || `<div class="empty-note">Aucune image${q ? " pour « " + esc(q) + " »" : " dans la Library"}.</div>`;
  g.querySelectorAll("img").forEach(el => el.onclick = () => {
    selImage = el.dataset.fn;
    g.querySelectorAll("img").forEach(x => x.classList.toggle("sel", x === el));
  });
}

async function animer() {
  if (busyAnim) return;
  if (!selImage) return toast("Choisis d'abord une image de la Library.", true);
  const action = ($("#animPrompt").value || "").trim();
  if (!action) return toast("Décris l'action à animer (ex : walks in place).", true);
  busyAnim = true; $("#animerBtn").disabled = true;
  const st = $("#animStatus");
  try {
    setStatus(st, "Lancement Seedance…", false, 3);
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
    if (!job) throw new Error("job Seedance introuvable dans la file");
    const j = await pollJob(job.job_id, jj => setStatus(st,
      `Seedance : ${jj.current_step || jj.status}…`, false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || "génération échouée");
    clearStatus(st);
    toast("Animation prête — extraction des frames…");
    setSource({ kind: "job", job_id: j.job_id, label: j.title || ("render " + j.job_id.slice(0, 8)) });
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
    toast("Animer a échoué : " + e.message, true);
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
    $("#renderList").innerHTML = `<div class="empty-note">Renders indisponibles : ${esc(e.message)}</div>`;
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
  }).join("") || `<div class="empty-note">Aucun render vidéo terminé.</div>`;
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
    setStatus(st, `Envoi de ${file.name}…`, false, 30);
    const fd = new FormData(); fd.append("file", file);
    const r = await fetch("/api/videos/upload", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    setStatus(st, `Importée : ${d.filename} (${d.duration_s || "?"} s)`);
    setSource({ kind: "job", job_id: d.job_id, label: d.filename });
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
    toast("Upload échoué : " + e.message, true);
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
  $("#strip").innerHTML = `<div class="empty-note">Extraction des frames… (locale, gratuite)</div>`;
  $("#stripCount").textContent = "…";
  try {
    const d = await api.send("POST", "/assets/sprite", {
      source: { kind: source.kind, job_id: source.job_id },
      fps_sample: fps, max_frames: max,
      remove_bg: "none", extract_only: true,
      title: "Sprites · extraction " + (source.label || ""),
    });
    const j = await pollJob(d.job_id, null, 5 * 60 * 1000);
    if (j.status !== "done") throw new Error(j.error || "extraction échouée");
    if (extractJob && extractJob !== d.job_id)      // la sonde précédente + ses
      api.send("DELETE", "/jobs/" + extractJob).catch(() => {}); // fichiers
    extractJob = d.job_id; extractShort = d.job_id.slice(0, 8);
    extractedAt = { fps, max };
    const m = await api.get("/assets/sprite/" + extractShort + "/manifest");
    stripN = m.frames.length;
    stripState = m.frames.map(() => true); lastClicked = 0;
    renderStrip();
  } catch (e) {
    $("#strip").innerHTML = `<div class="empty-note">Extraction échouée : ${esc(e.message)}</div>`;
    $("#stripCount").textContent = "—";
    toast("Extraction échouée : " + e.message, true);
  }
  busyExtract = false; $("#extractBtn").disabled = false; updateGenEnabled();
}

function renderStrip() {
  $("#strip").innerHTML = Array.from({ length: stripN }, (_, i) =>
    `<div class="frame ${stripState[i] ? "" : "off"}" data-i="${i}" title="frame ${i} — clic : garder/enlever, Shift-clic : plage">
       <img loading="lazy" src="/api/assets/sprite/${extractShort}/frame/${i}"><span class="fno">${i}</span>
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
  $("#stripCount").textContent = stripN ? `${keptIndices().length}/${stripN} gardées` : "—";
  updateCost(); updateGenEnabled();
}

/* ───────── coût estimé (détourage API × frames gardées) ───────── */
async function updateCost() {
  const el = $("#costHint");
  if ($("#removeBg").value !== "api" || !stripN) { el.textContent = ""; return; }
  try {
    const d = await api.send("POST", "/cost/estimate",
      { kind: "sprite2d", frames: keptIndices().length, remove_bg: "api" });
    el.textContent = d && d.total_usd != null ? `≈ $${(+d.total_usd).toFixed(3)}` : "";
  } catch (e) { el.textContent = ""; }
}

/* ───────── génération du sheet ───────── */
function updateGenEnabled() {
  $("#genBtn").disabled = !(source && extractShort && !busyGen && !busyExtract);
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

async function generate() {
  if (busyGen || !source || !extractShort) return;
  if (stripStale()) {
    toast("Réglages fps/max modifiés — frames ré-extraites. Vérifie ta sélection puis relance.", true);
    return extract();
  }
  const kept = keptIndices();
  if (!kept.length) return toast("Garde au moins une frame dans le filmstrip.", true);
  busyGen = true; updateGenEnabled();
  const st = $("#genStatus");
  try {
    const s = stripSettings();
    const body = {
      source: { kind: source.kind, job_id: source.job_id },
      fps_sample: s.fps, max_frames: s.max,
      remove_bg: $("#removeBg").value,
      trim: $("#trim").value,
      cell: { size: parseInt($("#cellSize").value, 10),
              align: $("#cellAlign").value },
      columns: $("#columns").value === "auto" ? "auto" : parseInt($("#columns").value, 10),
      title: "Sprites · " + (source.label || ""),
    };
    if (kept.length < stripN) body.keep = kept;
    const px = pixelOpts(); if (px) body.pixel = px;

    setStatus(st, "Job lancé…", false, 3);
    const d = await api.send("POST", "/assets/sprite", body);
    const j = await pollJob(d.job_id, jj => setStatus(st,
      `${jj.current_step || jj.status}…`, false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || "génération échouée");
    const short = d.job_id.slice(0, 8);
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    clearStatus(st);
    showResult(short, m);
    toast("Sprite sheet généré ✓");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
    toast("Génération échouée : " + e.message, true);
  }
  busyGen = false; updateGenEnabled();
}

/* ───────── préviz + exports ───────── */
const player = { imgs: [], n: 0, playing: true, raf: 0, last: 0, acc: 0, i: 0 };

function showResult(short, m) {
  sheet = { short, manifest: m };
  $("#outEmpty").classList.add("hidden");
  $("#player").classList.remove("hidden");
  $("#exports").classList.remove("hidden");
  $("#sheetWrap").classList.remove("hidden");
  const g = m.grid || {};
  $("#outInfo").textContent =
    `${g.cols}×${g.rows} · ${g.cell_w}px · ${m.frames.length} frames` +
    (m.pixel ? ` · ${m.pixel.palette || (m.pixel.colors + " coul.")}` : "");
  $("#dlSheet").href = `/api/assets/sprite/${short}/sheet`;
  $("#dlSheet").setAttribute("download", `sprites_${short}.png`);
  $("#dlZip").href = `/api/assets/sprite/${short}/zip`;
  $("#dlZip").setAttribute("download", `sprites_${short}.zip`);
  $("#dlGif").href = `/api/assets/sprite/${short}/preview`;
  $("#dlGif").setAttribute("download", `sprites_${short}.gif`);
  $("#sheetImg").src = `/api/assets/sprite/${short}/sheet?t=${Date.now()}`;
  buildPlayer(short, m);
}

function buildPlayer(short, m) {
  cancelAnimationFrame(player.raf);
  const cv = $("#cv"), g = m.grid;
  cv.width = g.cell_w; cv.height = g.cell_h;
  player.imgs = m.frames.map(f => {
    const im = new Image();
    im.src = `/api/assets/sprite/${short}/frame/${f.index}`;
    return im;
  });
  player.n = m.frames.length; player.i = 0; player.acc = 0; player.last = 0;
  player.playing = true; $("#playBtn").textContent = "⏸";
  if (m.fps) { $("#pfps").value = m.fps; $("#pfpsVal").textContent = m.fps; }
  applyZoom(); applyBg();
  const ctx = cv.getContext("2d");
  const tick = (t) => {
    const fps = parseInt($("#pfps").value, 10) || 8;
    if (!player.last) player.last = t;
    if (player.playing) {
      player.acc += t - player.last;
      const step = 1000 / fps;
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
  stage.classList.toggle("bg-checker", v === "checker");
  stage.style.background = v === "checker" ? "" : v;
}

async function saveToLibrary() {
  if (!sheet) return;
  try {
    const d = await api.send("POST", `/assets/sprite/${sheet.short}/save`);
    toast(`Sheet copié dans la Library${d && d.filename ? " : " + d.filename : ""} ✓ — réutilisable dans le Studio (nœud Image).`);
  } catch (e) { toast("Save to Library échoué : " + e.message, true); }
}

/* ───────── hand-off (préparé pour 9d) ───────── */
window.addEventListener("message", (ev) => {
  const d = ev && ev.data;
  if (!d || d.type !== "spritelab:source" || !d.source) return;
  if (d.source.kind === "job" && d.source.job_id) {
    setSource({ kind: "job", job_id: d.source.job_id,
                label: d.source.label || ("render " + d.source.job_id.slice(0, 8)) });
  } else if (d.source.kind === "image" && d.source.filename) {
    selImage = d.source.filename;
    switchSrcTab("image"); renderImgGrid();
  }
});

/* ───────── wiring ───────── */
function switchSrcTab(which) {
  $$("#srcTabs .tab").forEach(t => t.classList.toggle("active", t.dataset.src === which));
  $("#srcImage").classList.toggle("hidden", which !== "image");
  $("#srcRender").classList.toggle("hidden", which !== "render");
  $("#srcUpload").classList.toggle("hidden", which !== "upload");
}
function syncPixelSet() {
  $(".pixelset").classList.toggle("off", !$("#pixelOn").checked);
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

  $("#playBtn").onclick = () => {
    player.playing = !player.playing;
    $("#playBtn").textContent = player.playing ? "⏸" : "▶";
  };
  $("#pfps").oninput = () => { $("#pfpsVal").textContent = $("#pfps").value; savePrefs(); };
  $("#pzoom").onchange = () => { applyZoom(); savePrefs(); };
  $("#pbg").onchange = () => { applyBg(); savePrefs(); };
  $("#saveLib").onclick = saveToLibrary;
}

/* poignée de debug / QA (harnais Puppeteer de la recette) */
window.__sl = {
  get state() {
    return { source, extractShort, stripN, kept: keptIndices().length,
             sheet: sheet && sheet.short, busyExtract, busyGen };
  },
  setSource,
};

(async function init() {
  wire();
  await loadPrefs();
  syncPixelSet();
  loadImages(); loadRenders();
})();
