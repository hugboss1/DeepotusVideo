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
let savedSheet = null;     // {short, filename} du dernier Save to Library
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
    renderImgGrid(); renderFeuilleGrid();
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
const player = { imgs: [], n: 0, playing: true, raf: 0, last: 0, acc: 0, i: 0, dx: 0, dy: 0, flip: false, speed: 1 };   // lot 5 : Playground

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
  updateStudioBtn();                    // masque « → Studio » si sheet non sauvé
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
    else if (k === " ") { player.playing = !player.playing; $("#playBtn").textContent = player.playing ? "⏸" : "▶"; }
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
    toast(`Sheet copié dans la Library${d && d.filename ? " : " + d.filename : ""} ✓ — réutilisable dans le Studio (nœud Image).`);
  } catch (e) { toast("Save to Library échoué : " + e.message, true); }
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
  } catch (e) { toast("Ouverture du Studio impossible : " + e.message, true); }
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

/* ───────── wiring ───────── */
function switchSrcTab(which) {
  $$("#srcTabs .tab").forEach(t => t.classList.toggle("active", t.dataset.src === which));
  $("#srcStarter").classList.toggle("hidden", which !== "starter");
  $("#srcImage").classList.toggle("hidden", which !== "image");
  $("#srcRender").classList.toggle("hidden", which !== "render");
  $("#srcUpload").classList.toggle("hidden", which !== "upload");
  $("#srcFeuille").classList.toggle("hidden", which !== "feuille");
  // lot 1 : en mode Feuille la colonne du milieu montre la planche, pas le filmstrip
  const feuille = which === "feuille" && !!F.tampon;
  $("#feuillePane").classList.toggle("hidden", !feuille);
  $("#strip").classList.toggle("hidden", feuille);
  $("#feuilleOut").classList.toggle("hidden", !feuille);
  if (which === "starter") loadStarter();
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
      `<div class="empty-note">Catalogue indisponible : ${esc(e.message)}</div>`;
    return;
  }
  renderStarter();
}

function starterTile(item, kind) {
  const sub = kind === "preset" ? item.type : item.frames + " images";
  return `<button class="starter-tile" data-kind="${kind}" data-id="${esc(item.id)}"
    title="${esc(item.desc || item.name)}">
    <span class="starter-thumb"${item.thumb ? ` style="background-image:url(${esc(item.thumb)})"` : ""}></span>
    <span class="starter-name">${esc(item.name)}</span>
    <span class="starter-sub">${esc(sub)}</span></button>`;
}

function renderStarter() {
  const d = starterData || { presets: [], anims: [] };
  if (!d.presets.length && !d.anims.length) {
    $("#starterGrid").innerHTML = `<div class="empty-note">Catalogue de démarrage absent —
      lance <code>python scripts/build_starter_catalog.py --fetch</code> puis relance l'app.</div>`;
    return;
  }
  $("#starterCount").textContent = d.presets.length + " effets";
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
    const cell = parseInt($("#cellSize").value, 10) || 512;
    const body = kind === "anim" ? { anim: id, cell } : { preset: id };
    setStatus(st, "Job lancé…", false, 3);
    const path = kind === "anim" ? "/assets/starter-anim" : "/assets/particles";
    const d = await api.send("POST", path, body);
    const j = await pollJob(d.job_id, jj => setStatus(st,
      `${jj.current_step || jj.status}…`, false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || "génération échouée");
    const short = d.job_id.slice(0, 8);
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    clearStatus(st);
    showResult(short, m);
    toast("Sprite prêt ✓ — gratuit, généré en local");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
    toast("Génération échouée : " + e.message, true);
  }
  busyStarter = false;
  $$("#srcStarter .starter-tile").forEach(b => b.classList.remove("busy"));
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
  $("#toStudio").onclick = toStudio;
  playgroundWire();   // lot 5
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
  await new Promise((res, rej) => { im.onload = () => res(); im.onerror = () => rej(new Error("image illisible : " + String(src).slice(0, 60))); im.src = src; });
  F.img = im; F.filename = filename; F.tampon = fTampon(); F.off = []; F.sections = []; F.dernier = null; F.courant = 0;
  source = null;                                            // pas une source de génération : la chaîne Seedance reste à part
  const chip = $("#srcChip"); chip.textContent = "Feuille : " + filename; chip.classList.add("set");
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
  $("#fDims").textContent = `${F.tampon.w}×${F.tampon.h} · cases ${F.g.cell_w}×${F.g.cell_h}`;
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
  $("#fSections").innerHTML = F.sections.map((s) => `<div class="section-row"><span class="nom">${esc(s.nom)}</span><span>${s.debut}–${s.fin}</span><span>${esc(s.mode)}</span><button class="btn ghost fSecDel" data-nom="${esc(s.nom)}" title="Retirer">✕</button></div>`).join("") || `<div class="hint">aucune section — sélectionne des cases puis « + depuis la sélection »</div>`;
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
  player.imgs = []; player.n = idx.length; player.i = 0; player.acc = 0; player.last = 0; player.playing = true; $("#playBtn").textContent = "⏸";
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
  $("#fSecAdd").onclick = () => { const idx = F.sel.map((v, i) => v ? i : -1).filter((i) => i >= 0); if (!idx.length) return toast("sélectionne des cases d'abord", true);
    try { F.sections = window.SLF.section_definir(F.sections, { nom: $("#fSecNom").value, debut: 0, fin: idx.length - 1, mode: $("#fSecMode").value }, idx.length); $("#fSecNom").value = ""; feuilleDessiner(); } catch (e) { toast(e.message, true); } };
  $("#fCopyJson").onclick = async () => { try { await navigator.clipboard.writeText(JSON.stringify(feuilleManifest(), null, 2)); toast("manifest copié"); } catch (e) { toast("presse-papiers refusé : " + e.message, true); } };
  $("#fDlJson").onclick = () => fTelecharger(new Blob([JSON.stringify(feuilleManifest(), null, 2)], { type: "application/json" }), fBase() + ".json");
  $("#fDlPng").onclick = async () => fTelecharger(await feuillePngBlob(), fBase() + "_alignee.png");
  $("#fSaveLib").onclick = async () => { try { const fd = new FormData(); fd.append("file", await feuillePngBlob(), `sprites_feuille_${Date.now()}.png`); const r = await fetch("/api/images/upload", { method: "POST", body: fd }); const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || r.statusText); toast(`sauvé en Library : ${d.filename} — « Envoyer vers » le Vectorlab depuis la Library`); loadImages(); } catch (e) { toast(e.message, true); } };
  feuilleGestes();
}
function renderFeuilleGrid() {
  const q = ($("#feuilleSearch").value || "").toLowerCase();
  const list = libImages.filter((im) => !q || im.filename.toLowerCase().includes(q));
  const g = $("#feuilleGrid");
  g.innerHTML = list.slice(0, 120).map((im) => `<img loading="lazy" data-fn="${esc(im.filename)}" title="${esc(im.filename)}" src="/api/images/${encodeURIComponent(im.filename)}">`).join("")
    || `<div class="empty-note">Aucune image${q ? " pour « " + esc(q) + " »" : " dans la Library"}.</div>`;
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
        setStatus(st, "Génération en cours retrouvée…", false, 5);
        const j = await pollJob(run.job_id, jj => setStatus(st,
          `${jj.current_step || jj.status}…`, false, jj.progress || 5));
        if (j.status !== "done") throw new Error(j.error || "génération échouée");
        clearStatus(st);
        if (await showShort(run.job_id.slice(0, 8))) toast("Sprite sheet généré ✓");
      } catch (e) {
        setStatus(st, "Échec : " + e.message, true);
      }
      busyGen = false; updateGenEnabled();
      return;
    }
    const done = mine
      .filter(j => j.status === "done" && j.final_video_path)
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))[0];
    if (done && await showShort(done.job_id.slice(0, 8)))
      toast("Dernier sheet rechargé ✓");
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
  loadImages(); loadRenders();
  restoreLast();               // préviz : survit au remontage de l'iframe
})();
