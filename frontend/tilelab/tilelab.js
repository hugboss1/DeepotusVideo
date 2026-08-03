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

/* poignée QA (harnais Puppeteer de la recette) */
window.__tl = {
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
};

(function init() {
  wire();
  loadImages();
})();
