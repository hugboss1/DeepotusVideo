/* Tile Lab — chantier 9e. Vanilla JS, même API que l'app (même origine).
   Chaîne : image Library → op "seamless" (/api/images/process, local,
   gratuit) → op "pixel" optionnelle (9b) → pavage 3×3 + score de raccord
   calculés CÔTÉ CLIENT (aucun fichier parasite en Library : seuls la tuile
   et son éventuelle version pixel-art y atterrissent). */
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

let libImages = [];
let selImage = null;      // filename source choisi
let result = null;        // {filename, before, after}
let busy = false;

let toastTimer = null;
function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg; t.classList.toggle("err", !!err); t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 4200);
}
function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function setStatus(el, msg, err) {
  el.classList.remove("hidden"); el.classList.toggle("err", !!err);
  el.textContent = msg;
}
function clearStatus(el) { el.classList.add("hidden"); el.textContent = ""; }

/* ───────── Library ───────── */
async function loadImages() {
  try {
    libImages = (await api.get("/images")).images || [];
    renderImgGrid(); if (typeof renderFeuilleGrid === "function") renderFeuilleGrid();
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
    const chip = $("#srcChip");
    chip.textContent = "Source : " + selImage;
    chip.classList.add("set");
    updateRunEnabled();
  });
}
function updateRunEnabled() { $("#runBtn").disabled = !(selImage && !busy); }

/* ───────── score de raccord côté client (même métrique que pixel_ops) ─────
   Moyenne des diffs absolues RGB entre bords opposés, normalisée 0-100. */
function seamScoreClient(img) {
  const w = img.naturalWidth, h = img.naturalHeight;
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  const ctx = cv.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0);
  const L = ctx.getImageData(0, 0, 1, h).data, R = ctx.getImageData(w - 1, 0, 1, h).data;
  const T = ctx.getImageData(0, 0, w, 1).data, B = ctx.getImageData(0, h - 1, w, 1).data;
  const mean = (a, b, n) => {
    let s = 0;
    for (let i = 0; i < n; i++) {
      const o = i * 4;
      s += Math.abs(a[o] - b[o]) + Math.abs(a[o + 1] - b[o + 1]) + Math.abs(a[o + 2] - b[o + 2]);
    }
    return s / (n * 3);
  };
  return Math.round((mean(L, R, h) + mean(T, B, w)) / 2 / 255 * 100 * 100) / 100;
}

function pave(img) {
  const cv = $("#paveCv");
  const t = Math.max(1, Math.min(200, Math.round(600 / 3)));
  cv.width = t * 3; cv.height = t * 3;
  const ctx = cv.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  for (let gy = 0; gy < 3; gy++)
    for (let gx = 0; gx < 3; gx++)
      ctx.drawImage(img, gx * t, gy * t, t, t);
}

function loadImg(src) {
  return new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error("image illisible : " + src));
    im.src = src;
  });
}

/* ───────── run ───────── */
function pixelOpts() {
  if (!$("#pixelOn").checked) return null;
  const palette = $("#pixPalette").value;
  const o = { target_px: parseInt($("#pixTarget").value, 10) || 64,
              dither: $("#pixDither").value };
  if (palette) o.palette = palette;
  else o.colors = parseInt($("#pixColors").value, 10) || 16;
  return o;
}

async function run() {
  if (busy || !selImage) return;
  busy = true; updateRunEnabled();
  const st = $("#runStatus");
  try {
    setStatus(st, "Tuile seamless…");
    const body = {
      op: "seamless", filename: selImage,
      method: $("#method").value,
      blend: parseInt($("#blend").value, 10) || 20,
      square: $("#square").value === "1",
      target_px: parseInt($("#targetPx").value, 10) || 0,
    };
    const d = await api.send("POST", "/images/process", body);
    let finalName = d.images[0];

    const px = pixelOpts();
    if (px) {
      setStatus(st, "Pixel-art…");
      const d2 = await api.send("POST", "/images/process",
        Object.assign({ op: "pixel", filename: finalName }, px));
      finalName = d2.images[0];
    }

    setStatus(st, "Pavage + score…");
    const img = await loadImg("/api/images/" + encodeURIComponent(finalName) + "?t=" + Date.now());
    const after = px ? seamScoreClient(img) : d.seam_after;

    $("#scoreBefore").textContent = d.seam_before;
    $("#scoreAfter").textContent = after;
    $("#tileName").textContent = finalName;
    $("#tileImg").src = img.src;
    $("#dlTile").href = img.src;
    $("#dlTile").setAttribute("download", finalName);
    pave(img);
    $("#outInfo").textContent =
      `${img.naturalWidth}×${img.naturalHeight} · ${body.method}` + (px ? " · pixel" : "");
    $("#outEmpty").classList.add("hidden");
    $("#result").classList.remove("hidden");
    result = { filename: finalName, before: d.seam_before, after };
    updateStudioBtn();
    clearStatus(st);
    toast(`Tuile prête : raccord ${d.seam_before} → ${after} ✓ (Library : ${finalName})`);
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
    toast("Tuile échouée : " + e.message, true);
  }
  busy = false; updateRunEnabled();
}

/* ───────── « → Studio » (même mécanisme que le Sprite Lab 9d) ───────── */
function updateStudioBtn() {
  const ok = !!(result && result.filename && window.parent !== window);
  $("#toStudio").classList.toggle("hidden", !ok);
}
function toStudio() {
  if (!(result && result.filename)) return;
  const p = window.parent;
  if (!p || p === window) return;
  try {
    p.__dzRenderGraph = {
      name: "tile.graph",
      nodes: [{ id: "timg1", type: "Image", x: 320, y: 220,
                props: { filename: result.filename } }],
      edges: [],
    };
    p.dispatchEvent(new p.CustomEvent("deepotus:navigate",
                                      { detail: { view: "studio" } }));
  } catch (e) { toast("Ouverture du Studio impossible : " + e.message, true); }
}

/* ───────── wiring ───────── */
function wire() {
  $("#imgSearch").oninput = renderImgGrid;
  $("#runBtn").onclick = run;
  $("#toStudio").onclick = toStudio;
  $("#method").onchange = () => {
    $("#blend").disabled = $("#method").value === "mirror";
  };
  $("#pixelOn").onchange = () => {
    document.querySelector(".pixelset").classList.toggle("off", !$("#pixelOn").checked);
  };
  document.querySelector(".pixelset").classList.add("off");
}


/* ───────── lot 4 : palettes unifiées — le select se remplit depuis palettes.js ─────────
   (les cinq palettes « backend » = pixel_ops.py, envoyées par nom) */
function remplirPalettes() {
  const sel = $("#pixPalette"); if (!sel || !window.DZ_PALETTES) return;
  const courante = sel.value || "sweetie16";
  sel.innerHTML = DZ_PALETTES.options_palettes({ backendSeulement: true, courante });
}
if (window.DZ_PALETTES) remplirPalettes(); else document.addEventListener("dz-palettes", remplirPalettes, { once: true });


/* ───────── lot 4 : Feuille de tuiles — module pur feuille_tuiles.js (window.TLF), raccords de mod-pixelart (window.PXA) ─────────
   La planche est un tampon lu une fois ; les tuiles, la grille et les placements vivent dans F. */
const F = { img: null, tampon: null, filename: null, tuiles: [], sel: -1, placements: [], grille: { type: "carree", cols: 4, rows: 3, cell_w: 16, cell_h: 16 }, zoom: 1 };
function tlMode(m) {
  document.querySelectorAll("#tlTabs .tab").forEach((t) => t.classList.toggle("active", t.dataset.m === m));
  $("#tlSeamlessSrc").classList.toggle("hidden", m !== "seamless"); $("#tlFeuilleSrc").classList.toggle("hidden", m !== "feuille");
  document.querySelector(".out-pane .settings").classList.toggle("hidden", m === "feuille");
  $("#result").classList.toggle("hidden", m === "feuille" || !result); $("#outEmpty").classList.toggle("hidden", m === "feuille" || !!result);
  $("#feuilleOut").classList.toggle("hidden", m !== "feuille");
}
const tlTampon = (im) => { const c = document.createElement("canvas"); c.width = im.naturalWidth; c.height = im.naturalHeight; const x = c.getContext("2d"); x.drawImage(im, 0, 0); const d = x.getImageData(0, 0, c.width, c.height); return { w: c.width, h: c.height, data: d.data }; };
const tlCanvasDe = (t) => { const c = document.createElement("canvas"); c.width = t.w; c.height = t.h; c.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(t.data), t.w, t.h), 0, 0); return c; };
async function feuilleOuvrir(src, filename) {
  const im = new Image(); im.crossOrigin = "anonymous"; im.src = src; await im.decode();
  F.img = im; F.tampon = tlTampon(im); F.filename = filename; F.placements = []; F.sel = -1;
  $("#srcChip").textContent = "Feuille : " + filename; $("#srcChip").classList.add("set");
  tlMode("feuille"); detecter();
}
function detecter() {
  F.tuiles = TLF.tuiles_detecter(F.tampon, { min: Math.max(1, parseInt($("#tlMin").value, 10) || 2) });
  F.placements = []; F.sel = F.tuiles.length ? 0 : -1;
  const tc = TLF.taille_commune(F.tuiles); if (tc.w) { $("#tlCellW").value = tc.w; $("#tlCellH").value = $("#tlGrilleType").value === "iso" ? Math.max(1, Math.round(tc.w / 2)) : tc.h; }
  lireGrille(); rendreTuiles(); rendrePlacement();
  $("#outInfo").textContent = `${F.tampon.w}×${F.tampon.h} · ${F.tuiles.length} tuiles · commune ${tc.w}×${tc.h}`;
}
function lireGrille() {
  F.grille = { type: $("#tlGrilleType").value, cols: Math.max(1, parseInt($("#tlCols").value, 10) || 1), rows: Math.max(1, parseInt($("#tlRows").value, 10) || 1),
               cell_w: Math.max(1, parseInt($("#tlCellW").value, 10) || 1), cell_h: Math.max(1, parseInt($("#tlCellH").value, 10) || 1) };
}
function rendreTuiles() {
  const h = $("#tlTuiles"); $("#tlTuilesCount").textContent = String(F.tuiles.length);
  if (!F.tuiles.length) { h.innerHTML = `<div class="empty-note">Aucune tuile (planche opaque ? côté min trop grand ?)</div>`; return; }
  const posees = new Set(F.placements.map((p) => p.tuile));
  h.innerHTML = F.tuiles.map((t, i) => `<canvas class="tl-tuile${i === F.sel ? " sel" : ""}${posees.has(i) ? " placee" : ""}" data-i="${i}" width="56" height="56" title="${t.nom} · ${t.w}×${t.h} en (${t.x},${t.y})"></canvas>`).join("");
  h.querySelectorAll(".tl-tuile").forEach((cv) => {
    const t = F.tuiles[+cv.dataset.i], x = cv.getContext("2d"); x.imageSmoothingEnabled = false;
    const k = Math.min(56 / t.w, 56 / t.h, 4); x.drawImage(F.img, t.x, t.y, t.w, t.h, (56 - t.w * k) / 2, (56 - t.h * k) / 2, t.w * k, t.h * k);
    cv.onclick = () => { F.sel = +cv.dataset.i; rendreTuiles(); };
    cv.ondblclick = () => raccord(+cv.dataset.i);
  });
}
function rendrePlacement() {
  const R = TLF.placement_rendre(F.tampon, F.tuiles, F.placements, F.grille), cv = $("#tlPlacement");
  cv.width = R.w; cv.height = R.h; const x = cv.getContext("2d"); x.imageSmoothingEnabled = false;
  x.putImageData(new ImageData(R.data, R.w, R.h), 0, 0);
  // la grille : cases carrées ou losanges
  x.strokeStyle = "rgba(255,209,102,.5)"; x.lineWidth = 1; const g = F.grille;
  for (let r = 0; r < g.rows; r++) for (let c = 0; c < g.cols; c++) {
    const { x: px, y: py } = TLF.position_cellule(c, r, g);
    if (g.type === "iso") { x.beginPath(); x.moveTo(px + g.cell_w / 2, py); x.lineTo(px + g.cell_w, py + g.cell_h / 2); x.lineTo(px + g.cell_w / 2, py + g.cell_h); x.lineTo(px, py + g.cell_h / 2); x.closePath(); x.stroke(); }
    else x.strokeRect(px + .5, py + .5, g.cell_w - 1, g.cell_h - 1);
  }
  F.zoom = Math.max(1, Math.min(8, Math.floor(480 / R.w))); cv.style.width = (R.w * F.zoom) + "px"; cv.style.height = (R.h * F.zoom) + "px";
}
function celluleDe(ev) { const cv = $("#tlPlacement"), r = cv.getBoundingClientRect(); const x = (ev.clientX - r.left) * cv.width / r.width, y = (ev.clientY - r.top) * cv.height / r.height; const c = TLF.cellule_de_point(x, y, F.grille); return (c.c < 0 || c.r < 0 || c.c >= F.grille.cols || c.r >= F.grille.rows) ? null : c; }
function poser(ev) { const c = celluleDe(ev); if (!c || F.sel < 0) return; F.placements = F.placements.filter((p) => !(p.c === c.c && p.r === c.r)); F.placements.push({ c: c.c, r: c.r, tuile: F.sel }); rendrePlacement(); rendreTuiles(); }
function retirer(ev) { ev.preventDefault(); const c = celluleDe(ev); if (!c) return; F.placements = F.placements.filter((p) => !(p.c === c.c && p.r === c.r)); rendrePlacement(); rendreTuiles(); }
function raccord(i) {
  const t = F.tuiles[i]; if (!t) return;
  const tuile = { w: t.w, h: t.h, data: new Uint8ClampedArray(t.w * t.h * 4) };
  for (let y = 0; y < t.h; y++) tuile.data.set(F.tampon.data.subarray(((t.y + y) * F.tampon.w + t.x) * 4, ((t.y + y) * F.tampon.w + t.x + t.w) * 4), y * t.w * 4);
  const r = F.grille.type === "iso" ? PXA.pavage_iso(tuile) : PXA.raccord_3x3(tuile), cv = $("#tlSeamCv");
  cv.hidden = false; cv.width = r.img.w; cv.height = r.img.h; cv.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(r.img.data), r.img.w, r.img.h), 0, 0);
  cv.style.width = Math.min(360, r.img.w * 4) + "px";
  $("#tlSeamScore").textContent = `${t.nom} · score ${r.score} (${F.grille.type})`;
}
const tlTelecharger = (blob, nom) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
const tlPng = (t) => new Promise((r) => tlCanvasDe(t).toBlob(r, "image/png"));
const tlBase = () => (F.filename || "feuille").replace(/\.\w+$/, "");
function feuilleAlignee() { const tc = TLF.taille_commune(F.tuiles); return TLF.feuille_alignee(F.tampon, F.tuiles, { cell_w: tc.w, cell_h: tc.h, cols: parseInt($("#tlExpCols").value, 10) || 8, pad: parseInt($("#tlExpPad").value, 10) || 0 }); }
async function dlFeuille() { if (!F.tuiles.length) return toast("aucune tuile", true); const f = feuilleAlignee(), tc = TLF.taille_commune(F.tuiles); tlTelecharger(await tlPng(f.img), tlBase() + "_alignee.png"); tlTelecharger(new Blob([JSON.stringify({ cellule: tc, pad: parseInt($("#tlExpPad").value, 10) || 0, cols: parseInt($("#tlExpCols").value, 10) || 8, feuille: { w: f.img.w, h: f.img.h }, tuiles: f.index }, null, 2)], { type: "application/json" }), tlBase() + "_alignee.json"); toast(`feuille alignée ${f.img.w}×${f.img.h}, ${f.index.length} tuiles`); }
async function dlTileset() { const R = TLF.placement_rendre(F.tampon, F.tuiles, F.placements, F.grille); tlTelecharger(await tlPng(R), tlBase() + "_tileset.png"); tlTelecharger(new Blob([JSON.stringify({ grille: F.grille, placements: TLF.placement_index(F.placements, F.grille) }, null, 2)], { type: "application/json" }), tlBase() + "_tileset.json"); toast(`tileset ${R.w}×${R.h}, ${F.placements.length} placements`); }
// lot 5 : les tuiles séparées partent en UN zip (store, pur JS) — plus de rafale
async function dlTuiles() {
  if (!F.tuiles.length) return toast("aucune tuile", true);
  const entrees = [];
  for (const t of F.tuiles) { const im = { w: t.w, h: t.h, data: new Uint8ClampedArray(t.w * t.h * 4) }; for (let y = 0; y < t.h; y++) im.data.set(F.tampon.data.subarray(((t.y + y) * F.tampon.w + t.x) * 4, ((t.y + y) * F.tampon.w + t.x + t.w) * 4), y * t.w * 4); entrees.push({ nom: `${t.nom}.png`, data: new Uint8Array(await (await tlPng(im)).arrayBuffer()) }); }
  const zip = DZ_ZIP.zip_store(entrees);
  tlTelecharger(new Blob([zip], { type: "application/zip" }), `${tlBase()}_tuiles.zip`);
  toast(`${entrees.length} tuile(s) dans ${tlBase()}_tuiles.zip`);
}
// lot 5 : réordonnancement — la tuile choisie glisse, les placements suivent
function deplacerTuile(delta) {
  if (F.sel < 0) return toast("choisis une tuile", true);
  const i = F.sel, j = i + delta; if (j < 0 || j >= F.tuiles.length) return;
  F.tuiles = TLF.tuiles_deplacer(F.tuiles, i, delta);
  F.placements = F.placements.map((p) => ({ ...p, tuile: p.tuile === i ? j : p.tuile === j ? i : p.tuile }));
  F.sel = j; rendreTuiles(); rendrePlacement();
}
async function saveLib() { if (!F.tuiles.length) return toast("aucune tuile", true); try { const f = feuilleAlignee(); const fd = new FormData(); fd.append("file", await tlPng(f.img), `tiles_feuille_${Date.now()}.png`); const r = await fetch("/api/images/upload", { method: "POST", body: fd }); const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || r.statusText); toast(`sauvé en Library : ${d.filename}`); loadImages(); } catch (e) { toast(e.message, true); } }
function renderFeuilleGrid() {
  const q = ($("#feuilleSearch").value || "").toLowerCase(), g = $("#feuilleGrid");
  const list = libImages.filter((im) => !q || im.filename.toLowerCase().includes(q));
  g.innerHTML = list.slice(0, 120).map((im) => `<img loading="lazy" data-fn="${esc(im.filename)}" title="${esc(im.filename)}" src="/api/images/${encodeURIComponent(im.filename)}">`).join("") || `<div class="empty-note">Aucune image.</div>`;
  g.querySelectorAll("img").forEach((el) => el.onclick = () => feuilleOuvrir(`/api/images/${encodeURIComponent(el.dataset.fn)}`, el.dataset.fn).catch((e) => toast(e.message, true)));
}
function feuilleWire() {
  document.querySelectorAll("#tlTabs .tab").forEach((t) => t.onclick = () => tlMode(t.dataset.m));
  $("#feuilleFile").onchange = (e) => { const f = e.target.files[0]; if (f) feuilleOuvrir(URL.createObjectURL(f), f.name).catch((err) => toast(err.message, true)); };
  $("#feuilleSearch").oninput = renderFeuilleGrid;
  $("#tlDetecter").onclick = () => { if (F.tampon) detecter(); };
  for (const id of ["tlGrilleType", "tlCols", "tlRows", "tlCellW", "tlCellH"]) $("#" + id).onchange = () => { if ($("#tlGrilleType").value === "iso" && id === "tlGrilleType") $("#tlCellH").value = Math.max(1, Math.round((parseInt($("#tlCellW").value, 10) || 16) / 2)); lireGrille(); if (F.tampon) rendrePlacement(); };
  $("#tlVider").onclick = () => { F.placements = []; if (F.tampon) { rendrePlacement(); rendreTuiles(); } };
  const cv = $("#tlPlacement"); cv.onclick = poser; cv.oncontextmenu = retirer;
  $("#tlDlFeuille").onclick = dlFeuille; $("#tlDlTileset").onclick = dlTileset; $("#tlDlTuiles").onclick = dlTuiles; $("#tlSaveLib").onclick = saveLib;
  $("#tlAvant").onclick = () => deplacerTuile(-1); $("#tlApres").onclick = () => deplacerTuile(1);
}
if (window.TLF) feuilleWire(); else document.addEventListener("tlf-pret", feuilleWire, { once: true });
window.__tl = Object.assign(window.__tl || {}, { feuille: { ouvrir: feuilleOuvrir, etat: () => F, detecter, deplacer: deplacerTuile, dlTuiles, poser: (c, r) => { F.placements = F.placements.filter((p) => !(p.c === c && p.r === r)); F.placements.push({ c, r, tuile: F.sel }); rendrePlacement(); rendreTuiles(); }, raccord, mode: tlMode } });

/* poignée QA (harnais Puppeteer de la recette) */
window.__tl = Object.assign(window.__tl || {}, {   // lot 4 : ne pas écraser la poignée « feuille » posée plus haut
  get state() {
    return { selImage, busy, result };
  },
  select(fn) {
    selImage = fn;
    $("#srcChip").textContent = "Source : " + fn;
    $("#srcChip").classList.add("set");
    updateRunEnabled();
  },
  run,
});

(function init() {
  wire();
  loadImages();
})();
