// mod-couleur.js — éditeur complet (E4) : conversions de couleur
// hex/RGB/HSV/CMJN (naïf, SANS profil ICC — assumé et dit dans l'UI),
// palette par défaut générée, ops de palette du document (annulables).
// La partie PURE est en tête (bancable node) ; le nuancier DOM
// (initCouleur) ne touche le document qu'à l'appel.

/* ── pur : conversions ── */
export function hexVersRgb(hex) {
  const m = /^#([0-9A-Fa-f]{6})$/.exec(String(hex || ""));
  if (!m) throw new Error(`couleur attendue en #RRGGBB : ${hex}`);
  const v = parseInt(m[1], 16);
  return { r: (v >> 16) & 255, g: (v >> 8) & 255, b: v & 255 };
}

export function rgbVersHex({ r, g, b }) {
  const c = (x) => Math.max(0, Math.min(255, Math.round(x)))
    .toString(16).padStart(2, "0");
  return ("#" + c(r) + c(g) + c(b)).toUpperCase();
}

export function rgbVersHsv({ r, g, b }) {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  const d = max - min;
  let h = 0;
  if (d > 0) {
    if (max === rn) h = ((gn - bn) / d) % 6;
    else if (max === gn) h = (bn - rn) / d + 2;
    else h = (rn - gn) / d + 4;
    h = Math.round(h * 60);
    if (h < 0) h += 360;
  }
  return { h, s: Math.round(max ? (d / max) * 100 : 0),
           v: Math.round(max * 100) };
}

export function hsvVersRgb({ h, s, v }) {
  const sn = s / 100, vn = v / 100;
  const c = vn * sn, hp = (((h % 360) + 360) % 360) / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));
  let [r, g, b] = hp < 1 ? [c, x, 0] : hp < 2 ? [x, c, 0]
    : hp < 3 ? [0, c, x] : hp < 4 ? [0, x, c]
    : hp < 5 ? [x, 0, c] : [c, 0, x];
  const m = vn - c;
  return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255),
           b: Math.round((b + m) * 255) };
}

export function rgbVersCmjn({ r, g, b }) {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const n = 1 - Math.max(rn, gn, bn);
  if (n >= 1) return { c: 0, m: 0, j: 0, n: 100 };
  const c = (1 - rn - n) / (1 - n), m = (1 - gn - n) / (1 - n),
        j = (1 - bn - n) / (1 - n);
  const p = (x) => Math.round(x * 100);
  return { c: p(c), m: p(m), j: p(j), n: p(n) };
}

export function cmjnVersRgb({ c, m, j, n }) {
  const f = (x) => Math.max(0, Math.min(100, +x || 0)) / 100;
  const nn = f(n);
  const v = (k) => Math.round(255 * (1 - f(k)) * (1 - nn));
  return { r: v(c), g: v(m), b: v(j) };
}

/* ── pur : la palette étendue par défaut — 12 teintes × 3 clartés + 12
   neutres, générée (jamais recopiée à la main) ── */
export function palette_defaut() {
  const out = [];
  for (let h = 0; h < 360; h += 30) {
    out.push(rgbVersHex(hsvVersRgb({ h, s: 88, v: 92 })));
    out.push(rgbVersHex(hsvVersRgb({ h, s: 62, v: 72 })));
    out.push(rgbVersHex(hsvVersRgb({ h, s: 38, v: 46 })));
  }
  for (let i = 0; i < 12; i++) {
    out.push(rgbVersHex(hsvVersRgb({ h: 0, s: 0, v: Math.round(100 - i * (100 / 11)) })));
  }
  return out;
}

/* ── pur : la palette DU DOCUMENT (sauvée avec lui, annulable) ── */
function _hexNorme(hex) {
  return rgbVersHex(hexVersRgb(hex));       // valide ET normalise la casse
}

export function op_palette_ajouter(doc, hex) {
  const h = _hexNorme(hex);
  if (!Array.isArray(doc.palette)) doc.palette = [];
  if (doc.palette.some((x) => String(x).toUpperCase() === h)) {
    throw new Error(`déjà dans la palette : ${h}`);
  }
  doc.palette.push(h);
  return h;
}

export function op_palette_retirer(doc, hex) {
  const h = _hexNorme(hex);
  const p = Array.isArray(doc.palette) ? doc.palette : [];
  const i = p.findIndex((x) => String(x).toUpperCase() === h);
  if (i < 0) throw new Error(`absente de la palette : ${h}`);
  p.splice(i, 1);
}

/* ── DOM : le nuancier (E4) — un popover unique, ouvert par
   VL.ouvrirNuancier(hexInitial, onChoix, ancre). Rien au chargement. ── */
export function initCouleur(VL) {
  const { $, etat } = VL;
  const recentes = [];                  // session — 10 dernières appliquées
  let hote = null, courant = null;      // courant = { hsv, cb }

  function construire() {
    hote = document.createElement("div");
    hote.id = "nuancier";
    hote.className = "hidden";
    hote.innerHTML = `
      <canvas id="nuSV" width="188" height="132" title="Saturation / valeur"></canvas>
      <input id="nuH" type="range" min="0" max="359" value="0" title="Teinte"/>
      <div class="nu-ligne">
        <span class="nu-bloc" id="nuAvant" title="Couleur d'origine"></span>
        <span class="nu-bloc" id="nuApres" title="Nouvelle couleur"></span>
        <input id="nuHex" type="text" maxlength="7" spellcheck="false"
               title="Hexadécimal #RRGGBB"/>
      </div>
      <div class="nu-ligne nu-champs">
        <label>R<input data-rgb="r" type="number" min="0" max="255"/></label>
        <label>V<input data-rgb="g" type="number" min="0" max="255"/></label>
        <label>B<input data-rgb="b" type="number" min="0" max="255"/></label>
      </div>
      <div class="nu-ligne nu-champs"
           title="CMJN indicatif — conversion naïve, sans profil ICC">
        <label>C<input data-cmjn="c" type="number" min="0" max="100"/></label>
        <label>M<input data-cmjn="m" type="number" min="0" max="100"/></label>
        <label>J<input data-cmjn="j" type="number" min="0" max="100"/></label>
        <label>N<input data-cmjn="n" type="number" min="0" max="100"/></label>
      </div>
      <div class="nu-tete">Palette du document
        <button id="nuPalPlus"
          title="Ajouter la couleur courante à la palette du document (annulable, sauvée avec lui)">＋</button>
      </div>
      <div id="nuPalDoc" class="nu-sw"
           title="Clic : prendre — clic droit : retirer de la palette"></div>
      <div class="nu-tete">Nuances</div>
      <div id="nuPalDef" class="nu-sw"></div>
      <div class="nu-tete">Récentes</div>
      <div id="nuRecentes" class="nu-sw"></div>
      <div class="nu-ligne nu-fin">
        <button id="nuOk" class="primaire">Appliquer</button>
        <button id="nuAnnul">Annuler</button>
      </div>`;
    document.body.appendChild(hote);

    const sv = $("#nuSV"), ctx = sv.getContext("2d");
    const hexCourant = () => rgbVersHex(hsvVersRgb(courant.hsv));

    function peindreSV() {
      const base = rgbVersHex(hsvVersRgb({ h: courant.hsv.h, s: 100, v: 100 }));
      const gx = ctx.createLinearGradient(0, 0, sv.width, 0);
      gx.addColorStop(0, "#FFFFFF"); gx.addColorStop(1, base);
      ctx.fillStyle = gx; ctx.fillRect(0, 0, sv.width, sv.height);
      const gy = ctx.createLinearGradient(0, 0, 0, sv.height);
      gy.addColorStop(0, "rgba(0,0,0,0)"); gy.addColorStop(1, "#000000");
      ctx.fillStyle = gy; ctx.fillRect(0, 0, sv.width, sv.height);
      const x = courant.hsv.s / 100 * sv.width;
      const y = (1 - courant.hsv.v / 100) * sv.height;
      ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.strokeStyle = "#FFFFFF"; ctx.lineWidth = 2; ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, 6.5, 0, Math.PI * 2);
      ctx.strokeStyle = "#101216"; ctx.lineWidth = 1; ctx.stroke();
    }
    function swatches(conteneur, liste, retirables) {
      conteneur.innerHTML = liste.map((h) =>
        `<button class="nu-case" data-hex="${h}"${retirables
          ? ' data-retirable="1"' : ""} style="background:${h}" title="${h}${
          retirables ? " — clic droit : retirer" : ""}"></button>`).join("")
        || '<span class="nu-vide">—</span>';
    }
    function synchroniser() {
      const rgb = hsvVersRgb(courant.hsv);
      const cmjn = rgbVersCmjn(rgb);
      $("#nuApres").style.background = hexCourant();
      $("#nuHex").value = hexCourant();
      for (const i of hote.querySelectorAll("[data-rgb]")) i.value = rgb[i.dataset.rgb];
      for (const i of hote.querySelectorAll("[data-cmjn]")) i.value = cmjn[i.dataset.cmjn];
      $("#nuH").value = courant.hsv.h;
      peindreSV();
      swatches($("#nuPalDoc"), (etat.doc && etat.doc.palette) || [], true);
      swatches($("#nuPalDef"), palette_defaut(), false);
      swatches($("#nuRecentes"), recentes, false);
    }
    function prendre(rgb) {
      courant.hsv = rgbVersHsv(rgb);
      synchroniser();
    }

    let glisse = false;
    const surSV = (ev) => {
      const r = sv.getBoundingClientRect();
      const s = Math.max(0, Math.min(100, (ev.clientX - r.left) / r.width * 100));
      const v = Math.max(0, Math.min(100, 100 - (ev.clientY - r.top) / r.height * 100));
      courant.hsv = { h: courant.hsv.h, s: Math.round(s), v: Math.round(v) };
      synchroniser();
    };
    sv.addEventListener("pointerdown", (ev) => { glisse = true; surSV(ev);
      try { sv.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ } });
    sv.addEventListener("pointermove", (ev) => { if (glisse) surSV(ev); });
    sv.addEventListener("pointerup", () => { glisse = false; });
    $("#nuH").addEventListener("input", (ev) => {
      courant.hsv.h = +ev.target.value; synchroniser();
    });
    $("#nuHex").addEventListener("change", (ev) => {
      try { prendre(hexVersRgb(ev.target.value.trim())); }
      catch (e) { VL.toast(e.message, true); synchroniser(); }
    });
    hote.querySelectorAll("[data-rgb]").forEach((i) =>
      i.addEventListener("change", () => {
        const rgb = hsvVersRgb(courant.hsv);
        rgb[i.dataset.rgb] = Math.max(0, Math.min(255, +i.value || 0));
        prendre(rgb);
      }));
    hote.querySelectorAll("[data-cmjn]").forEach((i) =>
      i.addEventListener("change", () => {
        const cmjn = rgbVersCmjn(hsvVersRgb(courant.hsv));
        cmjn[i.dataset.cmjn] = Math.max(0, Math.min(100, +i.value || 0));
        prendre(cmjnVersRgb(cmjn));
      }));
    hote.addEventListener("click", (ev) => {
      const c = ev.target.closest(".nu-case");
      if (c) prendre(hexVersRgb(c.dataset.hex));
    });
    hote.addEventListener("contextmenu", (ev) => {
      const c = ev.target.closest('.nu-case[data-retirable="1"]');
      if (!c) return;
      ev.preventDefault();
      VL.executer(op_palette_retirer, c.dataset.hex);
      synchroniser();
    });
    $("#nuPalPlus").addEventListener("click", () => {
      VL.executer(op_palette_ajouter, hexCourant());
      synchroniser();
    });
    $("#nuOk").addEventListener("click", () => {
      const h = hexCourant();
      const i = recentes.indexOf(h);
      if (i >= 0) recentes.splice(i, 1);
      recentes.unshift(h);
      if (recentes.length > 10) recentes.pop();
      const cb = courant.cb;
      fermer();
      cb(h);
    });
    $("#nuAnnul").addEventListener("click", fermer);
    document.addEventListener("pointerdown", (ev) => {
      if (courant && !hote.contains(ev.target)
          && !ev.target.closest(".nu-pastille")) fermer();
    }, true);
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && courant) { fermer(); ev.stopPropagation(); }
    }, true);
    VL._synchroniserNuancier = synchroniser;
  }

  function fermer() {
    courant = null;
    if (hote) hote.classList.add("hidden");
  }

  VL.ouvrirNuancier = (hexInitial, onChoix, ancre) => {
    if (!hote) construire();
    let rgb;
    try { rgb = hexVersRgb(hexInitial); }
    catch (e) { rgb = { r: 157, g: 180, b: 214 }; }
    courant = { hsv: rgbVersHsv(rgb), cb: onChoix };
    $("#nuAvant").style.background = rgbVersHex(rgb);
    hote.classList.remove("hidden");
    // près de l'ancre, borné à la fenêtre
    const r = ancre && ancre.getBoundingClientRect
      ? ancre.getBoundingClientRect() : { left: 60, bottom: 60 };
    const w = hote.offsetWidth || 210, h = hote.offsetHeight || 380;
    hote.style.left = Math.max(6, Math.min(window.innerWidth - w - 6, r.left)) + "px";
    hote.style.top = Math.max(6, Math.min(window.innerHeight - h - 6, r.bottom + 6)) + "px";
    VL._synchroniserNuancier();
  };
}
