/* Tile Lab — « Décor en parallaxe » (t341, lot Scenario B5, 29/10/2026).
   Une peinture LARGE (Bibliothèque ou fichier du PC) découpée en 4 ou 5 calques transparents nommés (ciel, lointain,
   milieu, proche, premier plan), réordonnables, un facteur de parallaxe par calque réglé sous un APERÇU qui défile,
   puis l'export Godot 4 ParallaxBackground (.tscn + PNG) ou les PNG en ZIP. Les calques entrent dans la Bibliothèque.

   MODULE À PART, comme jeu.js de l'Établi : tilelab.js est régénéré par la traduction L9 (i18n_l9_generer.py) ; ce
   module n'y touche pas. Il pose son onglet, ses deux panneaux, et suit la bascule de tilelab.js (évènement
   « tl-mode », poignée window.__tl.feuille.mode). Textes : dzT, dictionnaire frontend/shared/i18n/parallaxe.json.
   RÈGLE de la voie IA : le devis est affiché AVANT le clic, le dialogue le redit, `confirme_cout` part seulement
   après ; un 402 du plafond est repris par dz-plafonds.js. */

const MODE = "parallaxe";
const T = (k, v) => (typeof window.dzT === "function" ? window.dzT(k, v) : k);
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ico = (k, t = 16) => (typeof window.dzIcone === "function" ? window.dzIcone(k, { taille: t }) : "");
const usd = (v) => (v > 0 ? "≈ $" + (+v).toFixed(2) : T("parallaxe.cout.gratuit"));

const E = {
  images: [], charge: false, image: null,          // la peinture choisie : { nom, w, h, url }
  n: 5, modele: "local", modeles: [], boucler: true, busy: false,
  decor: null, imgs: {}, decors: [],
  lecture: true, vitesse: 120, camX: 0, t0: 0, raf: 0, sauve: 0,
};

async function api(m, p, corps) {
  const r = await fetch("/api" + p, m === "GET" ? {} : { method: m, headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps || {}) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = d && d.detail;
    const e = new Error((det && (det.message || det)) || r.statusText);
    e.status = r.status; e.detail = det;
    throw e;
  }
  return d;
}

function toast(msg, err) {
  if (typeof window.toast === "function") return window.toast(msg, err);
  const el = $("#toast"); if (!el) return;
  el.textContent = msg; el.classList.remove("hidden"); el.classList.toggle("err", !!err);
  setTimeout(() => el.classList.add("hidden"), 3500);
}

/* ── la page : onglet + panneaux ─────────────────────────────────────────── */
function poser() {
  const tabs = $("#tlTabs");
  if (!tabs || $("#tlTabParallaxe")) return;
  const b = document.createElement("button");
  b.className = "tab"; b.id = "tlTabParallaxe"; b.dataset.m = MODE;
  b.title = T("parallaxe.onglet.aide");
  b.innerHTML = ico("dz-nav-panneau-calques") + " " + esc(T("parallaxe.onglet.titre"));
  b.addEventListener("click", () => ouvrirMode());
  tabs.appendChild(b);

  const src = document.createElement("div");
  src.id = "tlParallaxeSrc"; src.className = "src-body hidden";
  src.innerHTML = `
    <div class="upload-box">
      <p class="hint">${esc(T("parallaxe.source.aide"))}</p>
      <label class="btn" for="plxFichier">${ico("dz-action-ouvrir")} ${esc(T("parallaxe.source.fichier"))}</label>
      <input type="file" id="plxFichier" accept="image/png,image/jpeg,image/webp" hidden>
    </div>
    <div class="search-wrap">${ico("dz-action-chercher")}<input id="plxRecherche" class="search" placeholder="${esc(T("parallaxe.source.filtrer"))}"></div>
    <div id="plxGrille" class="img-grid tall"><div class="empty-note">${esc(T("parallaxe.source.chargement"))}</div></div>
    <div class="tl-sec">${esc(T("parallaxe.decors.titre"))}</div>
    <div id="plxDecors" class="plx-decors"></div>`;
  const pane = $(".src-pane");
  pane.insertBefore(src, pane.querySelector(":scope > .hint"));

  const out = document.createElement("div");
  out.id = "parallaxeOut"; out.className = "tl-feuille hidden";
  out.innerHTML = `
    <div id="plxVide" class="empty-note plx-vide">
      <b>${esc(T("parallaxe.vide.titre"))}</b>
      <ol>
        <li>${esc(T("parallaxe.vide.etape1"))}</li>
        <li>${esc(T("parallaxe.vide.etape2"))}</li>
        <li>${esc(T("parallaxe.vide.etape3"))}</li>
      </ol>
    </div>
    <div id="plxReglages" class="hidden">
      <div class="plx-source"><img id="plxApercuSrc" alt=""><div><b id="plxSrcNom">—</b><div id="plxSrcInfo" class="hint"></div></div></div>
      <div class="grid2">
        <div class="fld">${esc(T("parallaxe.reglages.calques"))}
          <div class="dir-seg" id="plxN" role="group">
            <button class="seg" data-n="4" aria-pressed="false">4</button><button class="seg on" data-n="5" aria-pressed="true">5</button>
          </div></div>
        <label class="fld">${esc(T("parallaxe.reglages.voie"))}<select id="plxModele"></select></label>
      </div>
      <p id="plxVoieAide" class="hint"></p>
      <label class="fld inline"><input type="checkbox" id="plxBoucler" checked> ${esc(T("parallaxe.reglages.boucler"))}</label>
      <div class="genrow">
        <button id="plxLancer" class="btn primary big">${ico("dz-nav-panneau-calques", 18)} ${esc(T("parallaxe.reglages.lancer"))}</button>
        <span id="plxCout" class="cost">—</span>
      </div>
      <div id="plxStatut" class="status hidden"></div>
    </div>
    <div id="plxResultat" class="hidden">
      <div class="tl-sec">${esc(T("parallaxe.apercu.titre"))} <span class="hint">${esc(T("parallaxe.apercu.aide"))}</span></div>
      <canvas id="plxCanvas" class="plx-canvas" width="960" height="320"></canvas>
      <div class="row">
        <button id="plxLecture" class="btn ghost"></button>
        <label class="fld inline">${esc(T("parallaxe.apercu.vitesse"))} <input id="plxVitesse" type="range" min="0" max="600" step="10" value="120"></label>
        <label class="fld inline" title="${esc(T("parallaxe.apercu.repeter_aide"))}"><input type="checkbox" id="plxRepeter" checked> ${esc(T("parallaxe.apercu.repeter"))}</label>
      </div>
      <div class="tl-sec">${esc(T("parallaxe.calques.titre"))} <span class="hint">${esc(T("parallaxe.calques.aide"))}</span></div>
      <div id="plxCalques" class="plx-calques"></div>
      <div class="tl-sec">${esc(T("parallaxe.export.titre"))} <span class="hint">${esc(T("parallaxe.export.aide"))}</span></div>
      <div class="row">
        <a id="plxGodot" class="btn primary" download title="${esc(T("parallaxe.export.godot_aide"))}">${ico("dz-action-exporter")} ${esc(T("parallaxe.export.godot"))}</a>
        <a id="plxPng" class="btn" download title="${esc(T("parallaxe.export.png_aide"))}">${ico("dz-action-telecharger")} ${esc(T("parallaxe.export.png"))}</a>
        <span class="hint">${ico("dz-action-ajouter-bibliotheque")} ${esc(T("parallaxe.export.biblio"))}</span>
      </div>
    </div>`;
  $(".out-pane").appendChild(out);
  cabler();
}

function cabler() {
  $("#plxFichier").onchange = (e) => { const f = e.target.files[0]; if (f) deposer(f); e.target.value = ""; };
  $("#plxRecherche").oninput = grille;
  for (const b of document.querySelectorAll("#plxN .seg")) b.onclick = () => { E.n = +b.dataset.n; majN(); devis(); };
  $("#plxModele").onchange = () => { E.modele = $("#plxModele").value; majVoie(); };
  $("#plxBoucler").onchange = () => { E.boucler = $("#plxBoucler").checked; };
  $("#plxLancer").onclick = lancer;
  $("#plxLecture").onclick = () => { E.lecture = !E.lecture; majLecture(); };
  $("#plxVitesse").oninput = () => { E.vitesse = +$("#plxVitesse").value; };
  $("#plxRepeter").onchange = () => { if (E.decor) { E.decor.repeter = $("#plxRepeter").checked; sauver(); } };
  majLecture();
}

function ouvrirMode() {
  if (window.__tl && window.__tl.feuille && window.__tl.feuille.mode) window.__tl.feuille.mode(MODE);
  else document.dispatchEvent(new CustomEvent("tl-mode", { detail: MODE }));
}

function suivreMode(m) {
  const on = m === MODE;
  $("#tlParallaxeSrc").classList.toggle("hidden", !on);
  $("#parallaxeOut").classList.toggle("hidden", !on);
  $("#tlTabParallaxe").classList.toggle("active", on);
  if (!on) { cancelAnimationFrame(E.raf); E.raf = 0; return; }
  $(".out-pane .pane-head h2").textContent = T("parallaxe.onglet.titre");
  if (!E.charge) charger();
  if (E.decor) demarrer();
}

/* ── la source : Bibliothèque ou fichier ─────────────────────────────────── */
async function charger() {
  E.charge = true;
  // les calques déjà découpés (tile_plx_…) ne sont pas des peintures : ils restent hors de la grille
  try { E.images = ((await api("GET", "/images")).images || []).map((i) => i.filename).filter((f) => !/^tile_plx_/.test(f)); }
  catch (e) { E.images = []; }
  grille();
  decors();
}

function grille() {
  const q = ($("#plxRecherche").value || "").toLowerCase(), g = $("#plxGrille");
  const liste = E.images.filter((f) => !q || f.toLowerCase().includes(q)).slice(0, 160);
  g.innerHTML = liste.map((f) => `<img loading="lazy" data-fn="${esc(f)}" title="${esc(f)}" class="${E.image && E.image.nom === f ? "sel" : ""}" src="/api/images/${encodeURIComponent(f)}">`).join("")
    || `<div class="empty-note">${esc(T("parallaxe.source.aucune"))}</div>`;
  for (const el of g.querySelectorAll("img")) el.onclick = () => choisir(el.dataset.fn);
}

async function decors() {
  try { E.decors = (await api("GET", "/parallaxe")).decors || []; } catch (e) { E.decors = []; }
  const el = $("#plxDecors");
  el.innerHTML = E.decors.length ? E.decors.slice(0, 30).map((d) => `<button class="plx-decor${E.decor && E.decor.pid === d.pid ? " on" : ""}" data-pid="${esc(d.pid)}" title="${esc(d.source)}">
      <img src="/api/parallaxe/${encodeURIComponent(d.pid)}/source" alt="" loading="lazy"><span>${esc(d.nom)}</span><i>${esc(T("parallaxe.decors.n", { n: d.n }))}</i></button>`).join("")
    : `<div class="hint">${esc(T("parallaxe.decors.aucun"))}</div>`;
  for (const b of el.querySelectorAll("button")) b.onclick = () => rouvrir(b.dataset.pid);
}

async function deposer(f) {
  statut(T("parallaxe.source.envoi"));
  try {
    const fd = new FormData(); fd.append("file", f, f.name);
    const r = await fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    E.images.unshift(d.filename);
    grille();
    await choisir(d.filename);
  } catch (e) { statut(T("parallaxe.source.echec", { msg: e.message }), true); }
}

function choisir(nom) {
  return new Promise((res) => {
    const im = new Image();
    im.onload = () => {
      E.image = { nom, w: im.naturalWidth, h: im.naturalHeight, url: im.src };
      $("#srcChip").textContent = T("parallaxe.source.puce", { fn: nom }); $("#srcChip").classList.add("set");
      $("#plxApercuSrc").src = im.src; $("#plxSrcNom").textContent = nom;
      const large = E.image.w >= 2 * E.image.h;
      $("#plxSrcInfo").textContent = T("parallaxe.source.taille", { w: E.image.w, h: E.image.h }) + " · "
        + (large ? T("parallaxe.source.large") : T("parallaxe.source.etroite"));
      $("#plxSrcInfo").classList.toggle("warn", !large);
      $("#plxVide").classList.add("hidden"); $("#plxReglages").classList.remove("hidden");
      grille(); devis(); statut("");
      res();
    };
    im.onerror = () => { statut(T("parallaxe.source.illisible"), true); res(); };
    im.src = `/api/images/${encodeURIComponent(nom)}`;
  });
}

/* ── le devis AVANT le clic ──────────────────────────────────────────────── */
function majN() {
  for (const b of document.querySelectorAll("#plxN .seg")) { const on = +b.dataset.n === E.n; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); }
}

async function devis() {
  if (!E.image) return;
  try {
    const d = await api("GET", `/parallaxe/modeles?w=${E.image.w}&h=${E.image.h}&n=${E.n}`);
    E.modeles = d.modeles || [];
  } catch (e) { E.modeles = []; }
  const sel = $("#plxModele");
  sel.innerHTML = E.modeles.map((m) => {
    const prix = m.voie === "local" ? T("parallaxe.cout.gratuit") : (m.id === "seedream-layerize" ? T("parallaxe.cout.jusqua", { usd: (+m.devis.usd).toFixed(2) }) : usd(m.devis.usd));
    const cle = m.cle_ok ? "" : " — " + T("parallaxe.cout.cle", { cle: m.cle });
    return `<option value="${esc(m.id)}">${esc(T("parallaxe.voie." + m.id.replace(/-/g, "_")))} · ${esc(prix)}${esc(cle)}</option>`;
  }).join("");
  if (!E.modeles.some((m) => m.id === E.modele)) E.modele = "local";
  sel.value = E.modele;
  majVoie();
}

function modeleCourant() { return E.modeles.find((m) => m.id === E.modele) || null; }

function majVoie() {
  const m = modeleCourant();
  $("#plxVoieAide").textContent = T("parallaxe.voie." + E.modele.replace(/-/g, "_") + "_aide");
  if (!m) { $("#plxCout").textContent = "—"; return; }
  let txt = m.voie === "local" ? T("parallaxe.cout.local") : (m.id === "seedream-layerize"
    ? T("parallaxe.cout.devis_max", { usd: (+m.devis.usd).toFixed(2) }) : T("parallaxe.cout.devis", { usd: (+m.devis.usd).toFixed(2) }));
  if (m.borne) txt += " · " + m.borne;
  $("#plxCout").textContent = txt;
  $("#plxLancer").disabled = !!m.borne || E.busy;
}

function statut(msg, err) {
  const el = $("#plxStatut"); if (!el) return;
  el.classList.toggle("hidden", !msg); el.classList.toggle("err", !!err); el.textContent = msg || "";
}

async function lancer() {
  if (!E.image || E.busy) return;
  const m = modeleCourant();
  if (!m) return statut(T("parallaxe.cout.sans_devis"), true);
  const corps = { image: E.image.nom, n: E.n, modele: E.modele, boucler: E.boucler };
  if (m.voie !== "local") {
    const ok = window.__dzDialogue && await window.__dzDialogue.confirmer(
      T(m.id === "seedream-layerize" ? "parallaxe.confirmer.msg_max" : "parallaxe.confirmer.msg",
        { modele: T("parallaxe.voie." + m.id.replace(/-/g, "_")), n: E.n, usd: (+m.devis.usd).toFixed(2) }),
      { ok: T("parallaxe.confirmer.ok") });
    if (!ok) return;
    corps.confirme_cout = true;
  }
  E.busy = true; $("#plxLancer").disabled = true;
  statut(m.voie === "local" ? T("parallaxe.statut.local") : T("parallaxe.statut.ia"));
  try {
    const d = await api("POST", "/parallaxe/decouper", corps);
    await afficher(d);
    statut(T("parallaxe.statut.ok", { n: d.calques.length }));
    decors();
  } catch (e) {
    statut(T("parallaxe.statut.echec", { msg: e.message }), true);
  } finally { E.busy = false; majVoie(); }
}

/* ── le résultat : calques, aperçu, exports ──────────────────────────────── */
async function rouvrir(pid) {
  try {
    const d = await api("GET", `/parallaxe/${encodeURIComponent(pid)}`);
    if (!E.image || E.image.nom !== d.source) {
      E.image = { nom: d.source, w: d.largeur, h: d.hauteur };
      $("#srcChip").textContent = T("parallaxe.source.puce", { fn: d.source }); $("#srcChip").classList.add("set");
      $("#plxApercuSrc").src = `/api/parallaxe/${encodeURIComponent(pid)}/source`;
      $("#plxSrcNom").textContent = d.source;
      $("#plxSrcInfo").textContent = T("parallaxe.source.taille", { w: d.largeur, h: d.hauteur });
      $("#plxVide").classList.add("hidden"); $("#plxReglages").classList.remove("hidden");
      devis();
    }
    await afficher(d);
    decors();
  } catch (e) { toast(e.message, true); }
}

async function afficher(d) {
  E.decor = d; E.imgs = {};
  const v = Date.now();
  await Promise.all(d.calques.map((c) => new Promise((res) => {
    const im = new Image();
    im.onload = im.onerror = () => res();
    im.src = `/api/parallaxe/${encodeURIComponent(d.pid)}/calque/${encodeURIComponent(c.id)}?v=${v}`;
    E.imgs[c.id] = im;
  })));
  $("#plxResultat").classList.remove("hidden");
  $("#plxRepeter").checked = d.repeter !== false;
  $("#plxGodot").href = `/api/parallaxe/${encodeURIComponent(d.pid)}/export?format=godot`;
  $("#plxPng").href = `/api/parallaxe/${encodeURIComponent(d.pid)}/export?format=png`;
  const cv = $("#plxCanvas");
  cv.width = Math.min(1280, d.largeur); cv.height = Math.round(cv.width * d.hauteur / d.largeur);
  liste();
  demarrer();
}

const nomDefaut = (c) => T("parallaxe.calque." + c.id.replace(/_\d+$/, ""));

function liste() {
  const d = E.decor, el = $("#plxCalques");
  // affichée de l'AVANT (en haut) vers le FOND (en bas), comme une pile de calques ; stockée fond → avant
  const ordre = d.calques.map((c, k) => k).reverse();
  el.innerHTML = ordre.map((k) => {
    const c = d.calques[k];
    return `<div class="plx-calque${c.visible === false ? " cache" : ""}" data-k="${k}">
      <div class="plx-ordre">
        <button class="btn ghost" data-act="avant" title="${esc(T("parallaxe.calques.avant"))}" aria-label="${esc(T("parallaxe.calques.avant"))}" ${k === d.calques.length - 1 ? "disabled" : ""}>${ico("dz-edit-monter")}</button>
        <button class="btn ghost" data-act="arriere" title="${esc(T("parallaxe.calques.arriere"))}" aria-label="${esc(T("parallaxe.calques.arriere"))}" ${k === 0 ? "disabled" : ""}>${ico("dz-edit-descendre")}</button>
      </div>
      <button class="btn ghost plx-oeil" data-act="voir" title="${esc(T(c.visible === false ? "parallaxe.calques.montrer" : "parallaxe.calques.cacher"))}" aria-pressed="${c.visible === false ? "false" : "true"}">${ico(c.visible === false ? "dz-etat-cache" : "dz-etat-visible")}</button>
      <img class="plx-vignette" src="${esc(E.imgs[c.id] ? E.imgs[c.id].src : "")}" alt="">
      <div class="plx-champs">
        <input class="plx-nom" data-act="nom" value="${esc(c.nom || "")}" placeholder="${esc(nomDefaut(c))}" maxlength="40" aria-label="${esc(T("parallaxe.calques.nom"))}">
        <label class="plx-facteur" title="${esc(T("parallaxe.calques.facteur_aide"))}">${esc(T("parallaxe.calques.facteur"))}
          <input type="range" data-act="facteur" min="0" max="2" step="0.05" value="${Math.max(0, Math.min(2, c.facteur))}">
          <input type="number" data-act="facteur_n" min="-1" max="3" step="0.05" value="${c.facteur}"></label>
        <label class="plx-devant" title="${esc(T("parallaxe.calques.devant_aide"))}"><input type="checkbox" data-act="devant" ${c.devant ? "checked" : ""}> ${esc(T("parallaxe.calques.devant"))}</label>
      </div>
    </div>`;
  }).join("");
  for (const row of el.querySelectorAll(".plx-calque")) {
    const k = +row.dataset.k;
    row.querySelector('[data-act="avant"]').onclick = () => deplacer(k, 1);
    row.querySelector('[data-act="arriere"]').onclick = () => deplacer(k, -1);
    row.querySelector('[data-act="voir"]').onclick = () => { const c = d.calques[k]; c.visible = c.visible === false; sauver(); liste(); };
    row.querySelector('[data-act="nom"]').oninput = (e) => { d.calques[k].nom = e.target.value; sauver(); };
    const r = row.querySelector('[data-act="facteur"]'), nb = row.querySelector('[data-act="facteur_n"]');
    r.oninput = () => { d.calques[k].facteur = +r.value; nb.value = r.value; sauver(); };
    nb.onchange = () => { const f = Math.max(-1, Math.min(3, +nb.value || 0)); d.calques[k].facteur = f; nb.value = f; r.value = Math.max(0, Math.min(2, f)); sauver(); };
    row.querySelector('[data-act="devant"]').onchange = (e) => { d.calques[k].devant = e.target.checked; sauver(); };
  }
}

function deplacer(k, sens) {
  const c = E.decor.calques, j = k + sens;
  if (j < 0 || j >= c.length) return;
  [c[k], c[j]] = [c[j], c[k]];
  sauver(); liste();
}

function sauver() {
  clearTimeout(E.sauve);
  E.sauve = setTimeout(async () => {
    const d = E.decor; if (!d) return;
    try {
      await api("PUT", `/parallaxe/${encodeURIComponent(d.pid)}`, {
        repeter: d.repeter !== false,
        calques: d.calques.map((c) => ({ id: c.id, nom: c.nom || "", facteur: c.facteur, devant: !!c.devant, visible: c.visible !== false })),
      });
    } catch (e) { toast(T("parallaxe.statut.sauve_echec", { msg: e.message }), true); }
  }, 350);
}

/* l'APERÇU : une caméra avance ; chaque calque glisse de camX × facteur (motion_scale de Godot), répété à sa
   largeur si « répéter » ; les calques « devant le jeu » passent après le repère du joueur */
function majLecture() {
  const b = $("#plxLecture"); if (!b) return;
  b.innerHTML = ico(E.lecture ? "dz-media-pause" : "dz-media-lecture") + " " + esc(T(E.lecture ? "parallaxe.apercu.pause" : "parallaxe.apercu.lire"));
}

function demarrer() {
  if (E.raf || !E.decor) return;
  E.t0 = performance.now();
  const pas = (t) => {
    const dt = Math.min(0.1, (t - E.t0) / 1000); E.t0 = t;
    if (E.lecture) E.camX += E.vitesse * dt;
    dessiner();
    E.raf = requestAnimationFrame(pas);
  };
  E.raf = requestAnimationFrame(pas);
}

function dessiner() {
  const d = E.decor, cv = $("#plxCanvas"); if (!d || !cv) return;
  const x = cv.getContext("2d"), s = cv.width / d.largeur, W = d.largeur * s, H = cv.height;
  x.fillStyle = "#111"; x.fillRect(0, 0, cv.width, H);
  const repeter = d.repeter !== false;
  const un = (c) => {
    const im = E.imgs[c.id]; if (!im || !im.naturalWidth || c.visible === false) return;
    let o = -(E.camX * c.facteur * s);
    if (repeter) { o %= W; if (o > 0) o -= W; for (let p = o; p < cv.width; p += W) x.drawImage(im, p, 0, W, H); }
    else x.drawImage(im, o, 0, W, H);
  };
  d.calques.filter((c) => !c.devant).forEach(un);
  // le repère du joueur (le plan de jeu, facteur 1) : ce qui est « devant » passe par-dessus
  x.fillStyle = "rgba(240,180,41,.9)";
  const pw = Math.max(8, Math.round(H * 0.08));
  x.fillRect(Math.round(cv.width * 0.3), Math.round(H * 0.78) - pw * 1.6, pw, pw * 1.6);
  d.calques.filter((c) => c.devant).forEach(un);
}

/* ── démarrage ───────────────────────────────────────────────────────────── */
function init() {
  poser();
  document.addEventListener("tl-mode", (e) => suivreMode(e.detail));
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();

window.__tlparallaxe = { get etat() { return E; }, choisir, lancer, rouvrir, deplacer, dessiner };
